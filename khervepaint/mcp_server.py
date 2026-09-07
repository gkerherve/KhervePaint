"""MCP (Model Context Protocol) stdio server for KhervePaint.

This module is the *client-facing half* of KhervePaint's MCP support.
It speaks JSON-RPC 2.0 over stdin/stdout — the transport every MCP host
(Claude Desktop, Claude Code, Cursor, Zed, Continue, …) knows how to
launch — and forwards each ``tools/call`` to a running KhervePaint
window over a loopback socket (see ``mcp_bridge.py``).

The split matters: drawing tools have to touch a live QGraphicsScene,
so they must run inside the application's GUI thread.  The MCP host, by
contrast, wants to spawn a short-lived subprocess it owns.  This file
is that subprocess; it deliberately imports **no Qt and no third-party
package**, so it starts in milliseconds and works from any Python.

Run it directly with::

    python -m khervepaint.mcp_server

or, for a frozen build::

    KhervePaint.exe --mcp-server

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import sys
from typing import Any, List, Optional


# ── Protocol constants ─────────────────────────────────────────────

#: Spec revisions we know how to speak.  We echo the client's choice
#: when it is one of these, otherwise we answer with our newest.
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
LATEST_PROTOCOL = SUPPORTED_PROTOCOLS[0]

SERVER_NAME = "khervepaint"

#: Endpoint file written by the in-app bridge; names host, port, token.
ENDPOINT_FILENAME = "mcp-bridge.json"

_CONNECT_TIMEOUT = 5.0    # seconds to establish the bridge socket
_CALL_TIMEOUT = 300.0     # building a big supercell is legitimately slow


# ── Endpoint discovery ─────────────────────────────────────────────

def state_dir() -> str:
    """Directory holding KhervePaint's per-user runtime state.

    Kept free of Qt so both halves of the MCP stack agree on the path
    without the stdio server having to import PyQt5.
    """
    if sys.platform.startswith("win"):
        base = (os.environ.get("LOCALAPPDATA")
                or os.path.expanduser("~\\AppData\\Local"))
        return os.path.join(base, "KhervePaint")
    if sys.platform == "darwin":
        return os.path.expanduser(
            "~/Library/Application Support/KhervePaint")
    base = (os.environ.get("XDG_CONFIG_HOME")
            or os.path.expanduser("~/.config"))
    return os.path.join(base, "KhervePaint")


def endpoint_path() -> str:
    """Full path of the bridge endpoint description file."""
    return os.path.join(state_dir(), ENDPOINT_FILENAME)


def read_endpoint(path: Optional[str] = None) -> Optional[dict]:
    """Load the endpoint file, or None when the app is not serving."""
    try:
        with open(path or endpoint_path(), "r", encoding="utf-8") as fh:
            info = json.load(fh)
    except Exception:
        return None
    if not isinstance(info, dict) or "port" not in info:
        return None
    return info


_NOT_RUNNING = (
    "KhervePaint is not reachable.\n\n"
    "The MCP server drives a live KhervePaint window, so the "
    "application must be running with its bridge enabled:\n"
    "  1. Start KhervePaint.\n"
    "  2. Enable Tools ▸ MCP Server.\n"
    "Then retry — no need to restart this MCP connection."
)


class BridgeError(RuntimeError):
    """Raised when the running application cannot be reached."""


#: Sent to the client on initialize.  The host writes its own system
#: prompt, so everything a model must know before drawing into someone
#: else's open document has to travel with the connection.
_INSTRUCTIONS = """\
These tools drive a LIVE KhervePaint window — a vector + raster drawing \
app for scientific figures, with molecule and crystal builders, symbol \
libraries (optics, vacuum, electrical, lab glassware, P&ID, flowchart, \
biology, room layout) and millimetre-accurate measurement. Everything \
you do appears immediately in the document open in front of the user.

Working rules:
- Call get_document_info FIRST: it gives the canvas size in pixels, the \
dpi, and how big the page is in millimetres. All coordinates are scene \
pixels with (0, 0) at the TOP-LEFT and y growing downwards.
- Call list_items before changing or deleting anything, and never \
assume a layout. Item ids come from list_items; they are stable for as \
long as the item lives, but they are NOT saved in the file, so re-read \
them after the user opens a document.
- render_canvas returns a picture of the drawing. LOOK AT IT after \
drawing something non-trivial: overlaps, off-canvas shapes and bad \
spacing are obvious in the image and invisible in the JSON.
- Change only what was asked for. Leave the user's existing items alone.
- Everything you do is one undoable step per call: the user gets their \
drawing back with a single Ctrl+Z. Their unsaved work is real, so \
new_document and open_document refuse to discard it unless you pass \
discard_unsaved_changes — offer to save instead.
- The user controls what you may do (Tools > MCP Server). A refusal \
naming an access level is their setting, not a bug — tell them what you \
needed rather than working around it.

Drawing — `draw` is the main tool:
- It takes a LIST of shape specs and creates them all in one step, so \
build a whole figure in one call rather than one shape per call.
- Area shapes (rect, rounded_rect, ellipse, circle, triangle, diamond, \
hexagon, star, …) take "x","y" (top-left) and "w","h". Lines and arrows \
take "x1","y1","x2","y2". Text takes "text","x","y" and optional \
"size", plus "anchor":"center" to treat (x,y) as the text centre.
- Style with "stroke" (hex or "none"), "fill" (hex or "none"), "width", \
"opacity", "rotation" (degrees), and "label" (text centred inside a \
shape — better than a separate text item, because it moves with it).
- "fill" may be a gradient object {"kind":"linear"|"radial"|"sun", \
"c1":hex,"c2":hex,"angle":deg}. "sun" is a lit-sphere highlight: it is \
what makes a circle read as a 3D ball.
- Later specs sit on top of earlier ones. Draw backgrounds first.

Molecules and crystals — do NOT draw these by hand out of circles:
- place_model puts a real, tagged 3D model on the canvas from the \
built-in catalogue: molecules (water, methane, benzene, glucose, PET…), \
crystal structures (bcc, fcc, rocksalt, perovskite, diamond…) and the \
seven lattice systems. Call list_models first to get exact names.
- build_molecule builds any structure you can name from a heavy-atom \
skeleton: atoms = element symbols (NO hydrogens), bonds = [i, j, order]. \
Hydrogens and correct 3D geometry are added for you. Give a name too \
when the molecule is a common one, so a curated model is used instead.
- configure_model changes a model already on the canvas without \
rebuilding it: the view angles (az/el), the bond spread, the \
representation ("3d" ball-and-stick, "structural", "lewis", \
"condensed" 2-D formulas), per-element colours, and for crystals the \
supercell size (cells) and coordination polyhedra.
- A unit cell becomes a supercell with configure_model cells=[nx,ny,nz], \
and individual cells inside it can be tilted with tilts to show a \
defect — {"0,0,0": [rx, ry, rz]} in degrees.
- These models stay live: the user can still rotate them in 3D by \
double-clicking, and edit them in the molecule builder.

Symbol libraries:
- place_symbol drops any symbol from the app's palettes (optics, \
vacuum, electrical, labware, flowchart, network, P&ID, arrows, biology, \
maths, room layout, 3D scheme blocks). Call list_symbols for a \
library's exact element names — guessing wastes a call.
- Symbols are scaled relative to the page, so they stay in proportion \
with each other whatever the canvas size.

Layout and finishing:
- update_items restyles and moves existing items; group_items keeps a \
figure together; order_items fixes what is in front.
- Sizes are also available in millimetres, which is what matters for a \
figure headed for a paper: get_document_info reports the page size and \
the pixels-per-mm to convert with.
"""


# ── Bridge client ──────────────────────────────────────────────────

class BridgeClient:
    """Line-delimited JSON client for the in-app bridge.

    Connects lazily and reconnects on demand so that the MCP host may
    start this process before (or after) KhervePaint itself, and so a
    restart of the application does not require a restart of the host.
    """

    def __init__(self, endpoint_file: Optional[str] = None):
        self._endpoint_file = endpoint_file
        self._sock: Optional[socket.socket] = None
        self._buf = b""
        self._token = ""
        self._next_id = 0

    # ── Connection handling ─────────────────────────────────────

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
        self._sock = None
        self._buf = b""

    def _connect(self):
        info = read_endpoint(self._endpoint_file)
        if info is None:
            raise BridgeError(_NOT_RUNNING)
        self._token = str(info.get("token", ""))
        host = str(info.get("host", "127.0.0.1"))
        port = int(info["port"])
        try:
            sock = socket.create_connection(
                (host, port), timeout=_CONNECT_TIMEOUT)
        except OSError as exc:
            # A stale endpoint file (app killed without cleanup) looks
            # exactly like "not running" from here — say so plainly
            # rather than leaking a connection-refused traceback.
            raise BridgeError(f"{_NOT_RUNNING}\n\n(socket error: {exc})")
        sock.settimeout(_CALL_TIMEOUT)
        self._sock = sock
        self._buf = b""

    def _readline(self) -> bytes:
        assert self._sock is not None
        while b"\n" not in self._buf:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise BridgeError(
                    "KhervePaint closed the connection mid-request. "
                    "The application may have quit.")
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\n")
        return line

    def request(self, method: str, params: Optional[dict] = None) -> Any:
        """Send one request, returning its ``result`` payload."""
        for attempt in (0, 1):
            if self._sock is None:
                self._connect()
            self._next_id += 1
            payload = {
                "id": self._next_id,
                "token": self._token,
                "method": method,
                "params": params or {},
            }
            try:
                assert self._sock is not None
                self._sock.sendall(
                    (json.dumps(payload) + "\n").encode("utf-8"))
                line = self._readline()
            except BridgeError:
                self.close()
                if attempt == 0:
                    continue          # app restarted: reconnect once
                raise
            except OSError as exc:
                self.close()
                if attempt == 0:
                    continue
                raise BridgeError(f"Bridge I/O error: {exc}")
            try:
                reply = json.loads(line.decode("utf-8"))
            except Exception:
                self.close()
                raise BridgeError("Malformed reply from KhervePaint.")
            if reply.get("error"):
                raise BridgeError(str(reply["error"]))
            return reply.get("result")
        raise BridgeError(_NOT_RUNNING)


# ── Result shaping ─────────────────────────────────────────────────

#: Key a tool result uses to hand back a rendered picture.  A drawing
#: app that could only describe itself in JSON would be half blind, so
#: this travels to the model as a real MCP image block.
IMAGE_KEY = "image_png_base64"


def tool_content(result: Any) -> List[dict]:
    """MCP content blocks for a bridge tool result.

    A result carrying a PNG becomes an image block (plus the rest of
    the result as text), so the model can actually look at the canvas.
    """
    if isinstance(result, dict) and result.get(IMAGE_KEY):
        data = str(result[IMAGE_KEY])
        rest = {k: v for k, v in result.items() if k != IMAGE_KEY}
        blocks: List[dict] = [{"type": "image", "data": data,
                               "mimeType": "image/png"}]
        if rest:
            blocks.append({"type": "text",
                           "text": json.dumps(rest, indent=2,
                                              default=str)})
        return blocks
    return [{"type": "text",
             "text": json.dumps(result, indent=2, default=str)}]


def valid_png_b64(data: str) -> bool:
    """True when *data* decodes to something with a PNG signature."""
    try:
        raw = base64.b64decode(data, validate=True)
    except Exception:
        return False
    return raw[:8] == b"\x89PNG\r\n\x1a\n"


# ── MCP server ─────────────────────────────────────────────────────

def _log(msg: str):
    """Diagnostics go to stderr — stdout carries the protocol."""
    sys.stderr.write(f"[khervepaint-mcp] {msg}\n")
    sys.stderr.flush()


class McpServer:
    """Minimal, dependency-free MCP server over stdio."""

    def __init__(self, bridge: BridgeClient):
        self._bridge = bridge
        self._tools_cache: Optional[List[dict]] = None

    # ── Dispatch ────────────────────────────────────────────────

    def handle(self, msg: dict) -> Optional[dict]:
        """Handle one JSON-RPC message; None means 'no reply'."""
        method = msg.get("method")
        msg_id = msg.get("id")
        if method is None:                    # a response — ignore
            return None
        try:
            if method == "initialize":
                result = self._initialize(msg.get("params") or {})
            elif method in ("notifications/initialized",
                            "notifications/cancelled",
                            "initialized"):
                return None                   # notifications: no reply
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": self._list_tools()}
            elif method == "tools/call":
                result = self._call_tool(msg.get("params") or {})
            elif method in ("resources/list", "resources/templates/list"):
                # Declared empty rather than unsupported so hosts that
                # probe every capability do not surface an error.
                key = ("resourceTemplates"
                       if method.endswith("templates/list")
                       else "resources")
                result = {key: []}
            elif method == "prompts/list":
                result = {"prompts": []}
            else:
                if msg_id is None:
                    return None
                return _error(msg_id, -32601, f"Unknown method: {method}")
        except BridgeError as exc:
            if msg_id is None:
                return None
            return _error(msg_id, -32000, str(exc))
        except Exception as exc:              # never take the loop down
            if msg_id is None:
                return None
            return _error(msg_id, -32603, f"Internal error: {exc}")
        if msg_id is None:
            return None
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    # ── Methods ─────────────────────────────────────────────────

    def _initialize(self, params: dict) -> dict:
        asked = params.get("protocolVersion")
        version = (asked if asked in SUPPORTED_PROTOCOLS
                   else LATEST_PROTOCOL)
        # Best-effort: the app may not be up yet, and initialize must
        # never fail for that reason.
        app_version = "unknown"
        try:
            status = self._bridge.request("get_status")
            app_version = str((status or {}).get("version", "unknown"))
        except Exception:
            pass
        return {
            "protocolVersion": version,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {},
                "prompts": {},
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "title": "KhervePaint",
                "version": app_version,
            },
            "instructions": _INSTRUCTIONS,
        }

    def _list_tools(self) -> List[dict]:
        if self._tools_cache is None:
            tools = self._bridge.request("list_tools") or []
            self._tools_cache = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "inputSchema": t.get(
                        "input_schema", {"type": "object",
                                         "properties": {}}),
                }
                for t in tools
            ]
        return self._tools_cache

    def _call_tool(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            raise BridgeError("tools/call requires a tool name.")
        args = params.get("arguments") or {}
        result = self._bridge.request(
            "call_tool", {"name": name, "input": args})
        is_error = isinstance(result, dict) and "error" in result
        return {"content": tool_content(result), "isError": bool(is_error)}


def _error(msg_id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id,
            "error": {"code": code, "message": message}}


# ── Entry point ────────────────────────────────────────────────────

def serve(endpoint_file: Optional[str] = None) -> int:
    """Run the stdio loop until stdin closes."""
    bridge = BridgeClient(endpoint_file)
    server = McpServer(bridge)
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer
    _log(f"listening on stdio; endpoint="
         f"{endpoint_file or endpoint_path()}")
    while True:
        line = stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
        except Exception as exc:
            _log(f"bad JSON on stdin: {exc}")
            continue
        # A host may batch messages into a JSON array.
        batch = msg if isinstance(msg, list) else [msg]
        replies = [r for r in (server.handle(m) for m in batch)
                   if r is not None]
        for reply in replies:
            stdout.write((json.dumps(reply) + "\n").encode("utf-8"))
        if replies:
            stdout.flush()
    bridge.close()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    endpoint_file = None
    if "--endpoint" in args:
        i = args.index("--endpoint")
        if i + 1 < len(args):
            endpoint_file = args[i + 1]
    return serve(endpoint_file)


if __name__ == "__main__":
    sys.exit(main())
