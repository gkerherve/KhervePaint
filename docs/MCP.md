# Using KhervePaint from any AI assistant (MCP)

KhervePaint ships an [MCP](https://modelcontextprotocol.io) server, so
assistants other than the built-in AI chat — Claude Desktop, Claude
Code, Cursor, Zed, Continue, or anything else that speaks the Model
Context Protocol — can draw in an open document directly.

The built-in chat replies with a block of shape specs. An MCP client
gets the **whole application** instead: 26 tools covering the canvas,
the symbol palettes, the molecule and crystal builders, the document,
and — the one that changes how well the rest work — a **picture of the
drawing**.

- **See it** — `render_canvas` returns a real PNG as an MCP image
  block, so the assistant can look at what it drew. Overlaps, shapes
  off the page and bad spacing are obvious in the image and invisible
  in JSON. `get_document_info` gives the page in pixels *and*
  millimetres (a figure headed for a paper is measured in mm);
  `list_items` describes every item with its id, box, colours and
  label.
- **Draw** — `draw` takes a whole figure's worth of shape specs in one
  call: rectangles, ellipses, polygons, stars, lines, arrows, text,
  gradients (including the `sun` lit-sphere fill that makes a circle
  read as a 3-D ball), labels centred inside a shape, rotation and
  opacity.
- **Arrange** — `update_items` moves, resizes and restyles;
  `group_items` / `ungroup_items`, `order_items` (front/back),
  `align_items` (edges, centre lines, even spacing) and `select_items`,
  which highlights what the assistant is talking about in the window.
- **Symbols** — `place_symbol` reaches all fourteen palettes: optics,
  vacuum, electrical, lab glassware, flowchart, network, P&ID, arrows
  and callouts, biology, maths, room layout, 3-D scheme blocks,
  molecules and crystals. `list_symbols` gives the exact names, so a
  client that has never seen KhervePaint looks them up instead of
  guessing.
- **Chemistry** — `place_model` drops a real tagged 3-D model from the
  catalogue; `build_molecule` builds any structure from a heavy-atom
  skeleton (hydrogens and correct geometry filled in);
  `configure_model` changes the view angles, bond spread,
  representation (ball-and-stick, structural, Lewis, condensed),
  per-element colours, supercell size and per-cell tilts. The result
  is an ordinary KhervePaint model: the user can still spin it by
  double-clicking and edit it in the molecule builder.
- **Documents** — `set_canvas`, `new_document`, `open_document`,
  `save_document`, `export_document` (PNG/PDF/SVG at the page's own
  dpi), plus `load_example` and `insert_object` for the built-in
  example figures and the user's own saved-object library.

Everything a tool changes lands on the shared undo stack as **one
macro per call**, so **Ctrl+Z in KhervePaint reverts a remote
assistant's whole figure** just like your own.

## How it fits together

There are two doors into the same bridge:

```
 MCP host  ──stdio──▶  khervepaint.mcp_server  ──loopback TCP──▶  KhervePaint
(Claude Desktop,       (short-lived process                       (your open
 Cline, VS Code, …)     the host owns)                             drawing)

 MCP host  ──HTTP POST──────────────────────────────────────────▶  KhervePaint
(Open WebUI, n8n, …)   http://127.0.0.1:<port>/mcp                (same tools)
```

Same tools, same access level, same undo macros — the HTTP endpoint is
a second skin on the bridge, not a wider one. It binds to 127.0.0.1,
requires the same bearer token, and validates `Origin` so a web page
in your browser cannot drive the drawing (a local HTTP server needs no
CORS preflight, which is the DNS-rebinding hole the MCP spec warns
about). Copy URL and token from **Or configure by hand: URL only**.

Drawing tools have to touch live Qt items, so they run inside the
application's GUI thread. MCP hosts, meanwhile, want to spawn and
restart a subprocess of their own. The stdio server is that
subprocess; it holds no state, imports no Qt, and forwards each call
over a loopback socket to the running application.

Practical consequences:

- **KhervePaint must be running** for tools to work. The host may be
  started first — `initialize` still succeeds, and the connection
  starts working the moment the app comes up. No host restart needed.
- Restarting KhervePaint does not require restarting the host: the
  stdio server reconnects on the next call.
- The tools act on the **document that is open right now**.
- Item ids come from `list_items`. They live as long as the item does,
  but they are not saved in the file, and undo restores the document
  from a snapshot that rebuilds every item — so re-read them after an
  undo, an open, or `load_example`.

## Turning it on

1. **AI ▸ Connect to Claude (Simple)…**
2. Tick **Let assistants connect to this document**. The setting is
   remembered, so the bridge comes back automatically next launch.
3. Leave the access level on **Full** — the recommended setting (see
   **Access levels** below).
4. Pick your application under **Connect an application** and press
   **Connect**.
5. Restart it, then **mention KhervePaint in the chat**.

KhervePaint writes the entry into the host's own settings, so there is
no config file to edit by hand — it knows its own executable path,
which is the part a hand-edit usually gets wrong. Claude Desktop,
Cursor and Windsurf are edited directly; Claude Code goes through the
`claude` CLI, which owns the shape of `~/.claude.json`.

Every write backs the file up first (`.khervepaint-<timestamp>.bak`
beside it), replaces it atomically, and leaves your other servers and
unrelated settings alone. A config file that will not parse is reported
rather than overwritten.

**Zed is the exception.** Its settings file allows comments, which
rewriting would silently discard, so KhervePaint refuses to touch it —
copy the snippet in by hand.

Restart the host afterwards: hosts read their tool list once at
startup, so a newly connected one shows no tools until it reconnects.

The dialog also shows a running log of what connected clients have
actually called.

## Access levels

| Level | A connected client can |
| --- | --- |
| **Read only** | Look at the drawing (including `render_canvas`) and highlight items. No changes. |
| **Edit** | Draw, restyle, arrange, place models and symbols, resize the page — and save over the file already open. |
| **Full** (default, recommended) | Everything, including opening, saving and exporting to paths of its own choosing. |

The line between **Edit** and **Full** is the filesystem. At **Edit** a
client can do anything to the drawing in the window, and the worst case
is a figure you undo. `save_document` with no path is the same act as
Ctrl+S, so it stays there too. Naming a path is different: it reads or
writes a file outside the open document, with your permissions.

**Full is the default**, because the levels below it break the workflow
people came for. An assistant that cannot open the drawing you are
talking about, or write out the diagram it just drew, sends you back to
the File menu between every step — and the trust decision has
already been made by the time a tool runs: the connection is loopback
only, token-authenticated, off until you turn it on, and connected to
one application you chose by name. **Read only** and **Edit** stay for
anyone who wants a narrower grant.

## Then say "KhervePaint" in the chat

This is the step with no visible cue, and the one that makes a correct
setup look broken. Claude does not go looking for a drawing on its own
— the tools are there, but nothing points at them until the
conversation does:

> in KhervePaint, draw a flowchart of the login process

From that first mention it keeps working in the document you have open,
so the rest of the conversation is ordinary — *"move the decision
box down"*, *"show me what it looks like"*. If it answers with a
description instead of drawing anything, it has not connected: check
the box above is ticked and that the host was restarted.

Tools above the current level are withheld from `tools/list` and
refused if called anyway, with an error naming the setting. Hosts cache
the tool list from startup, so *widening* access takes effect on their
next reconnect; *narrowing* it takes effect immediately.

## Which clients work

Any MCP client that runs **on your machine**, whatever model it drives.
That matters more than it sounds: the model is not the constraint, the
client is. Someone using GPT, Mistral or Grok reaches KhervePaint
through Cline, VS Code, LM Studio or any other local client with their
own API key.

Cloud assistants are the exception, and it is a hard one. ChatGPT
connectors, Mistral's custom connectors and Grok's Bring Your Own MCP
all require a **publicly reachable HTTPS URL** and cannot spawn a local
process. KhervePaint drives a live window on your desk, so there is
nothing for them to reach without tunnelling your document to the
internet. That is not supported, on purpose.

### Configuring by hand

The dialog still shows the snippet, for Zed, for a machine you are
setting up remotely, or for a host KhervePaint does not know about.
Paste it into the host's config file (`claude_desktop_config.json` for
Claude Desktop) and restart it:

```json
{
  "mcpServers": {
    "khervepaint": {
      "command": "/path/to/python",
      "args": ["-m", "khervepaint.mcp_server"],
      "env": {"PYTHONPATH": "/path/to/KhervePaint"}
    }
  }
}
```

`PYTHONPATH` — not `cwd` — is what makes `-m khervepaint.mcp_server`
resolve. The host chooses the working directory and is free to ignore a
`cwd` key (Claude Code does), and without an importable checkout the
process exits before it can answer `initialize`, which the host reports
as *Server disconnected*.

An installed (frozen) build serves as its own MCP server, so the entry
is just the executable:

```json
{
  "mcpServers": {
    "khervepaint": {
      "command": "C:\\Program Files\\KhervePaint\\KhervePaint.exe",
      "args": ["--mcp-server"]
    }
  }
}
```

`--mcp-server` is checked before any GUI work happens: the process
speaks protocol on stdout and never opens a window.

### Claude Code

```
claude mcp add khervepaint -e PYTHONPATH="/path/to/KhervePaint" -- /path/to/python -m khervepaint.mcp_server
```

## Security

- The listener binds to **127.0.0.1 only** — nothing on the network
  can reach it.
- Every request must carry a random per-session token, published in an
  endpoint file written user-readable only:
  - Windows: `%LOCALAPPDATA%\KhervePaint\mcp-bridge.json`
  - macOS: `~/Library/Application Support/KhervePaint/mcp-bridge.json`
  - Linux: `$XDG_CONFIG_HOME/KhervePaint/mcp-bridge.json`
- The bridge is **off until you turn it on**, and stops with the
  window (the endpoint file is removed on the way out).

Treat an enabled bridge as giving the connected assistant the same
reach over your drawing as the built-in chat — and, at **Full**, the
same reach over your files as you have.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| "KhervePaint is not reachable" | The app is not running, or Tools ▸ MCP Server is unticked. Fix and retry — no host restart needed. |
| "Invalid bridge token" | A stale endpoint file from a previous run. Toggle the checkbox off and on. |
| Host shows no tools | The host caches `tools/list` from startup; restart the host once with KhervePaint already running. |
| "Refused: … access is set to …" | The access level in Tools ▸ MCP Server is below what the tool needs. |
| "No item with id N" | Ids are rebuilt by undo, open and `load_example`. Call `list_items` again. |
| "still running the previous tool call" | A render or a large supercell is in progress. One call runs at a time; retry when it finishes. |
| "The user has unsaved changes" | `new_document`, `open_document` and `load_example` will not bin unsaved work. Save first, or pass `discard_unsaved_changes`. |
| "Could not open a local port" | Another process is holding the port. Toggle off and on to pick a fresh one. |

Diagnostics from the stdio server go to **stderr**, which MCP hosts
capture in their own logs; stdout carries protocol only.
