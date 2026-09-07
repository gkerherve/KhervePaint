# KhervePaint — notes for Claude

KhervePaint is a hybrid raster + vector drawing app built on PyQt5 —
a native desktop app in the Kherve family (KherveFitting, KherveSheet,
KhervePDF, KherveDOC, KhervePlot, KherveDraw, KherveBook). One canvas
mixes a raster layer (open a PNG, paint on it with the pencil) and
vector items on top (lines, rectangles, circles, ellipses, text),
edited with a pointer tool, with grid + snap-to-grid and grouping.

## Build / run

- Python 3.12 / 3.13 with PyQt5 (+ qtawesome for icons).
- Run via `python KhervePaint.py` or `python -m khervepaint`.
- Crash log: `%TEMP%/khervepaint_crash.log`.
- **Version string** is derived at runtime in `_version.py` from
  `git rev-list --count HEAD` and `git rev-parse --short HEAD`,
  cached with `lru_cache`. Falls back to `_FALLBACK = "0.1.0"`
  outside a git checkout. Title bar reads `KhervePaint v0.1.N+sha`.
  The version bumps automatically on every commit — never edit a
  version constant by hand.

## File size policy

Every module in `khervepaint/` should stay near **1500 lines**. If a
change would push a file meaningfully past that, split the new code
into a new module and import.

## Project layout

- `KhervePaint.py` — entry script.
- `khervepaint/` — package; `python -m khervepaint` is the alternative entry.
  - `__init__.py`    — `APP_NAME`, version import.
  - `__main__.py`    — module entry point.
  - `_version.py`    — git-based version string.
  - `app.py`         — `main()`, crash log, Fusion style + theme.
  - `style.py`       — token-driven QSS themes (same template family as
                       KherveBook; theme persists via QSettings).
  - `icons.py`       — qtawesome MDI icon wrapper with fallback.
  - `mainwindow.py`  — `MainWindow` shell: menus, tool/option toolbars,
                       open PNG / .kpaint, save, export PNG.
  - `canvas.py`      — `PaintScene` + `PaintView`: raster layer at the
                       bottom (pencil paints into its pixmap), vector
                       items on top, tool state machine in the scene's
                       mouse events, grid overlay in the view, snapping,
                       group/ungroup, zoom.
  - `document.py`    — `.kpaint` JSON (de)serialisation: vector items
                       (recursively through groups), raster layer as
                       base64 PNG; flattened export to PNG and
                       single-page PDF (QPdfWriter, page sized to the
                       canvas at 96 dpi). Owns the path<->command-list
                       helpers used by both .kpaint and svgio.
  - `svgio.py`       — default format: editable SVG writer + parser
                       (breaks groups/paths/transforms into native
                       items). Resolves `<use href="#id">` against a
                       whole-tree id map (so Inkscape/matplotlib exports,
                       which draw ticks/markers/text as `<use>` of
                       `<defs>` glyph paths, import fully). Imports the
                       path helpers from document.
  - `library.py`     — reusable-object/template library: save the current
                       selection as a named standalone SVG in a per-user
                       objects folder (`KHERVEPAINT_OBJECTS_DIR` override
                       for tests), now **folder-aware** (sub-folders via a
                       `Folder/Name` save path; `iter_objects`/`list_folders`
                       /`create`/`rename`/`move`/`delete`). Driven by the
                       left toolbar's **Objects** dropdown (nested sub-menus
                       per folder) in `mainwindow.py`.
  - `templates.py`   — `TemplateExplorer` dialog (Objects ▸ Template
                       Explorer…): tree of folders + objects with new
                       folder / rename / move / delete / insert.
  - `chemistry.py`   — pure geometry for the chemistry tools: bond paths
                       (single/double/triple/hash), wedge polygon, ring
                       polygons, atom-label list. `canvas` builds native
                       items from these (no item classes here, so no cycle).
  - `floorplan.py`   — top-view room-layout elements: `build_<name>(w,h)`
                       returns shape specs (AI/example format) for walls,
                       doors, windows, furniture, kitchen & bathroom
                       fittings, plus decor (plant, rug); `SIZES` (mm),
                       `LABELS`, `CATEGORIES`. Symbols are drawn as refined
                       plan-view blocks (clean line-art + subtle fills,
                       shared palette constants) modelled on a professional
                       furniture-symbol sheet — detailed beds/sofas/chairs
                       (U-shaped shells), round dining set, lamp-topped
                       nightstand, clothed wardrobe, double-bowl sinks,
                       4-burner hob, etc.
  - `electrical.py`  — same shape: IEC/ANSI circuit components (resistor,
                       capacitor, diode, transistor, sources, ground…) +
                       building-installation symbols (sockets, switches,
                       lights, consumer unit…). Same `build_specs`/`size_mm`
                       interface as `floorplan`.
                       `PaintScene._place_symbol(module, name, center)` builds
                       native items via `ai_assistant._spec_to_item`, grouped,
                       on click — used by both `place_plan_element` and
                       `place_elec_element`. Symbols are sized as a fraction
                       of the **page** (scale = sceneRect width /
                       `module.REFERENCE_MM`), so a whole room/circuit fits
                       the drawing — e.g. a 480 mm chair on floorplan's
                       4800 mm reference is ~1/10 of the page (NOT mm→dpi,
                       which made real furniture far bigger than the page).
  - `optics.py` / `vacuum.py` / `labware.py` / `flowchart.py` — four more
                       spec-library modules with the SAME
                       `build_specs`/`size_mm`/`REFERENCE_MM`/`SIZES`/
                       `LABELS`/`CATEGORIES` shape as `floorplan`/
                       `electrical`, each with its own left-toolbar dropdown
                       and `PLACE` tool (`OPTICS_PLACE`/`VACUUM_PLACE`/
                       `LABWARE_PLACE`/`FLOW_PLACE`, placed via
                       `place_<x>_element` → `_place_symbol`). **optics**:
                       beam-path symbols (laser, mirrors, lenses, prism,
                       grating, detector, monochromator…) plus a **Lighting**
                       section (spotlight, floodlight, light cone, desk lamp,
                       bulb, LED, ring light, shine — for illuminating
                       objects). **vacuum**
                       (44 symbols, 5 sections): UHV/surface-science —
                       chamber & sources; pumps (turbo/ion/scroll/rotary/
                       cryo/diaphragm/Roots/NEG/TSP); gauges & pressure
                       (Bourdon/Pirani/Penning/Bayard-Alpert/Baratron/
                       U-tube manometer/transducer); valves (gate/angle/
                       leak/butterfly/ball/needle/solenoid/manual/relief);
                       lines & fittings (pipe/tee/elbow/reducer/flanges/
                       cold trap/MFC/regulator/gas cylinder). **labware**:
                       front-elevation glassware & apparatus (beakers,
                       flasks, burette, condenser, Bunsen, retort stand…).
                       **flowchart**: ANSI/ISO nodes (process, decision
                       diamond, terminator, data, database, connector…)
                       with centred text labels.
  - `network.py` / `pid.py` / `arrows.py` / `biology.py` / `maths.py` —
                       five more palettes in the same shape (general +
                       science). **network**: IT architecture (server,
                       database, router, switch, firewall, cloud, user…).
                       **pid**: P&ID / process flow (tank, column, reactor,
                       pump, bow-tie valves, instrument bubbles…).
                       **arrows**: annotation block/curved/bent/circular
                       arrows, callouts, banner, burst, plus thin line
                       **connectors** (curved/elbow/Z-bend/U-turn — a
                       polyline + solid arrowhead, matching the arrow tool).
                       **biology**: cells,
                       virus, DNA/RNA helices (sinusoidal polylines),
                       antibody, well-plate, microscope… **maths**: x-y/3D
                       axes, number line, plotted curve, vector, angle
                       marks, and Greek/operator text glyphs (Σ ∫ π ∞ Δ θ).
                       To add another such palette: write the module, then
                       add the tool const + scene element attr + `place_*`
                       + dropdown wiring (search `FLOW_PLACE` for the seam).
  - `molecules.py`   — same palette shape, but 3D **ball-and-stick** models.
                       Atoms are **lit spheres** (a circle with a `sun`
                       gradient in the element's CPK colour, `ATOM_COLORS`/
                       `ATOM_RADII`); bonds are grey sticks (single/double/
                       triple). An atom tuple may carry an optional 5th slot
                       — a per-atom body-colour override (`atom_specs(color=)`,
                       preserved through `_spread`/`_supercell`) — used to
                       tint same-element atoms on a hidden lattice site
                       (`SITE_COLORS`: BCC body-centre, FCC/diamond
                       face-centres, diamond interior) so they don't vanish
                       against identical corners. Crystals regenerate from
                       their builder each draw, so the tints need no
                       persistence. The 3D look comes from an isometric `_proj`
                       + depth-sorted `_model(atoms, bonds, edges)`, so
                       structures read as 3D while staying ordinary editable
                       gradient-filled items. Covers dozens of molecules
                       (alcohols/ethers, acids/carbonyls, amines, alkanes/
                       alkenes/alkynes, aromatics, halogenated), polymer
                       repeat units (→ PET) and crystal unit cells (simple
                       cubic/BCC/FCC/HCP/diamond/NaCl/CsCl/perovskite/
                       zincblende/fluorite — open **wireframe unit cells**:
                       small spheres + thick cube edges + dashed diagonals).
                       Atom placement is **hybridisation-aware**
                       (`_place_direction`: sp/sp2/sp3); `build_molecule(
                       heavy, links)` + `add_hydrogens` build a molecule
                       from a heavy-atom skeleton with correct angles (most
                       acyclic models via `_SKELETONS`; rings via
                       `_aromatic_ring`). Also exports
                       `atom_specs`/`bond_specs` and `expand_specs`, which
                       back the high-level `atom`/`bond` shape specs the AI
                       emits (expanded in `ai_assistant.apply_specs`);
                       `_brush` there accepts a gradient-dict `fill` so a
                       spec circle can be a lit sphere. Gradients already
                       round-trip through document.py/svgio.py, so nothing
                       new to persist — the sphere is just a gradient brush.
                       The isometric `_proj` is parameterised by view angle
                       (az/el); `model_data`/`build_specs_oriented` expose
                       the 3D data + a re-projection at any orientation.
                       Cubic crystals **stack into supercells**: `can_stack`
                       (all crystals but HCP) + `_supercell(atoms,bonds,edges,
                       nx,ny,nz)` tiles a cell face-to-face by its cube-edge
                       extent, de-duplicating shared corner/face atoms &
                       edges; `model_data(name, cells)` / `build_specs_oriented
                       (…, cells=)` return the tiled cell. Driven by
                       `PaintScene.set_cells` (right-click a crystal ▸ Stack
                       unit cells…, `properties.stack_cells_dialog`), which
                       grows `mol_box` by `stack_factor` (max count) so drawn
                       spheres stay a constant size. The `(nx,ny,nz)` counts
                       ride on the model tag as `mol_cells` and round-trip
                       through document.py (`model_cells`) / svgio.py
                       (`kp:model-cells`); `reorient_model(cells=…)` re-tiles.
                       Per-cell **tilts** (`mol_tilts`, `"i,j,k"→(rx,ry,rz)°`)
                       model a **defect, not a detached grain**: `_supercell`
                       lays atoms on ONE de-duplicated node table keyed by the
                       *untilted* position, then displaces each node by the
                       average rotation of the *tilted* cells that own it
                       (untilted owners contribute 0). So a tilted cell drags
                       the corner/face atoms it shares with its neighbours —
                       they deform to follow, no atom is duplicated — while an
                       isolated tilt stays rigid. (Earlier design detached the
                       cell; the tilt tests in `test_lattices.py` were rewritten
                       for the defect behaviour.)
                       The **cubic + lattice crystals** are surfaced through a
                       separate **Crystals** palette (`crystals.py` — just the
                       menu grouping `molecules.CRYSTAL_CATEGORIES`; all model/
                       placement machinery stays in `molecules`), split out of
                       the Molecules dropdown. `mainwindow._insert_library_item`
                       routes both `molecules` and `crystals` to
                       `place_mol_element`.
  - `molview.py`     — `MoleculeViewer` = the **Molecule builder** dialog
                       (right-click a placed model ▸ Molecule builder…).
                       Horizontal **view toolbar** of 3D cube-face icons
                       (`icons.view_cube_icon`, the viewed face shaded), a
                       **bond-length** slider (spreads atoms via
                       `_model`'s `bond_scale`), and an **atom palette** —
                       the `_Preview` is a `QGraphicsView` so spheres
                       hit-test (`tag_atoms` puts an `_atom` index on each
                       sphere spec). Click a sphere to select it (status
                       shows `free_valence` — the builder knows each
                       element's `VALENCE` and refuses to over-bond), click
                       an element to `add_bonded_atom` (single-neighbour
                       anchors extend as a straight trans zig-zag, not a
                       ring), **drag a sphere** to move that atom via
                       `drag_atom` (layout `frozen` by `fit_params` mid-drag
                       so nothing else shifts), drag the background to
                       orbit, or delete. Crystals are not editable (fixed
                       lattice), just rotatable. OK hands
                       `(az, el, bond, atoms, bonds)` back to
                       `PaintScene.reorient_model`.
                       **On-canvas 3D rotation**: double-clicking a placed
                       model (a `GroupItem` tagged `mol_name`/`mol_az`/
                       `mol_el`/`mol_bond`, plus `mol_atoms`/`mol_bonds` when
                       hand-built) enters `PaintScene.enter_orbit_mode` —
                       drag on the canvas spins it live (`_orbit_drag` →
                       `reorient_model(commit=False)`), Esc/click-off exits
                       and emits one `changed_by_user`. `reorient_model`
                       rebuilds the group at the chosen angle/bond
                       (preserving centre + footprint). The model tag
                       round-trips through document.py (`"model"`/
                       `model_az`/`model_el`/`model_bond`/`model_box`/
                       `model_repr`/`model_atoms`/`model_bonds`) and svgio.py
                       (`kp:model*` on the `<g>`), so it survives save/reload
                       and undo. `mol_box` is the stable build box (rebuilds
                       use it, not the margin-shrunk bounding rect, so orbit
                       keeps a constant size). `PaintScene.set_representation`
                       / `reorient_model(mode=…)` switch the drawing between
                       3D and the 2D formulas.
  - `molrepr.py`     — 2D chemical **representations** of a molecule graph:
                       `structural_specs` (element letters + bond lines),
                       `structural_specs(lewis=True)` (adds lone-pair dots
                       from `_VALENCE_E`), `condensed_specs`/
                       `molecular_formula` (Hill notation). `MODES`/
                       `MODE_LABELS` drive the right-click **Show as** menu
                       and the builder's **Insert as** combo. 2D coords come
                       from the orthographic view that spreads the atoms most
                       (`_best_view`).
  - `properties.py`  — right-click context menu (edit/duplicate/delete/
                       order/group) + `PropertiesDialog`: edit every
                       property of one item (transform, stroke, fill,
                       geometry, text/font). Double-click a non-text
                       item also opens it.
  - `fill.py`        — bucket flood-fill: renders the scene, scanline-
                       floods the enclosed region from the click, and
                       applies it either as raster paint or an editable
                       vector `PathItem` (behind the bounding shapes).
                       Vector is the default (`scene.bucket_vector`
                       starts True) — raster paint can't be selected,
                       moved or deleted afterwards.
  - `imageops.py`    — image background removal (right-click an image ▸
                       Remove background): floods the modal border colour
                       inward and clears its alpha, so only edge-connected
                       background goes transparent.
  - `gradient.py`    — two-stop linear/radial/**sun** gradient fills as
                       ObjectBoundingMode brushes; one spec dict
                       (kind/c1/c2/angle) shared by the JSON snapshot,
                       the SVG writer/parser (`<linearGradient>` defs +
                       url(#id) resolution incl. xlink:href stop chains),
                       the toolbar fill-style selector and the properties
                       dialog. "sun" = off-centre radial highlight (the
                       light colour c2 at a top-left focal point, the
                       body colour c1 at the rim) — a sun-lit-sphere
                       look; detected on read by cx/cy ≠ 0.5 and its
                       stops are written light-first.
  - `handles.py`     — `SelectionHandles`: resize handles per item type
                       and a rotate knob (double-click). Lines/arrows
                       (not dimensions) also get a round mid `_BendHandle`
                       that sets `LineItem.set_bend()` — drag off the line
                       to curve it (quadratic through the cursor), drop
                       back on the line to straighten. `Handle`-marked
                       items, excluded from serialisation/picking.
  - `crop.py`        — `CropSession`: interactive image crop overlay
                       (dim mask + frame + handles); Enter applies,
                       Esc cancels. Right-click an image → Crop image.
  - `canvassize.py`  — `CanvasSizeDialog` (File ▸ Drawing Size): size in
                       px/in/mm at a DPI, mm column-width presets for many
                       journals (ACS, Nature, Science, Cell, RSC,
                       Elsevier, IEEE, Wiley, PNAS) + paper/slides, custom,
                       or fit-to-drawing. Also owns `DEFAULT_PRESET` /
                       `default_size()` — new documents open at ACS single
                       column (3.25 in in mm) at 300 dpi. Sets `scene.dpi`
                       and drives `resize_canvas`/`fit_to_content`
                       (undoable).
                       `scene.dpi` round-trips (.kpaint/SVG) and drives
                       physical export size (PNG dpi, PDF page, SVG inch
                       width with px viewBox).
  - `undo.py`        — `SnapshotCommand`: whole-document snapshot
                       undo/redo (see Undo / redo policy).
  - `help.py`        — rich About dialog + in-app User Guide
                       (`Help ▸ User Guide`, F1). Keep the guide and the
                       repo `USERGUIDE.md` in sync when features change.
  - `ai_providers.py`— AI back-ends over urllib (no deps): Claude,
                       ChatGPT, Mistral, Ollama, Local. `chat()` (with an
                       optional pasted `image` — `_with_image` attaches a
                       base64 PNG to the last user msg per provider) and
                       `list_models()`; keys/base URLs in QSettings.
  - `ai_assistant.py`— `AiDock` (toggled from the top toolbar / View ▸ AI
                       Chat): chat panel with provider/model combos +
                       Refresh button. Parses the model's JSON shape specs
                       into real, undoable items (`apply_specs`); hides the
                       code from the chat (`prose_only`). A high-level
                       `molecule` spec (library `name`, or a heavy-atom
                       skeleton `atoms`/`bonds`) becomes a tagged,
                       3D-rotatable model via `_place_ai_molecule` →
                       `PaintScene.place_built_molecule`. Paste a
                       screenshot (Ctrl+V) to send it with the next
                       message. Network runs on a `QThread`. **NB** the
                       system prompt holds literal JSON braces, so the
                       message is built with `str.replace`, never
                       `str.format` (which would read them as fields).
  - `examples.py`    — built-in **Examples** menu assembly: imports the
                       `SKETCHES` registry and exposes `EXAMPLES` (sorted
                       by category order) + the `PAGE_*` constants. The
                       menu loads a builder's shape specs (the AI format)
                       via `apply_specs` onto a fresh A4 page; every
                       element is a normal editable item.
  - `example_kit.py` — drawing toolkit for the schematics: header band,
                       beam ray-paths, lenses, leader-line callouts,
                       framed plots (ticks/peaks), micrographs, legends,
                       wrapped captions. A4 page constants live here.
  - `example_sketches.py` — the `build_*` builders (XPS, UPS, AES, FTIR,
                       Raman, UV-Vis, XRF, NMR, SIMS, ICP-MS, GC-MS, XRD,
                       LEED, TEM, SEM, AFM, STM, TGA, DSC, BET, HPLC …)
                       and the `SKETCHES` list. Split from the toolkit so
                       neither file outgrows ~1500 lines.
  - `mcp_schema.py`  — the **MCP tool table**: 26 JSON-Schema tool
                       definitions and `LIBRARY_KEYS`. Qt-free and
                       import-free — it is the contract, so it can be
                       inspected and tested without a window, and the
                       stdio server never drags PyQt5 into the host's
                       subprocess.
  - `mcp_tools.py`   — `McpToolExecutor`: runs one named tool against
                       the live `MainWindow`. Items are addressed by an
                       int id stamped on the item (`_mcp_id`) and
                       validated against the current scene, so a stale
                       id says "call list_items again" instead of
                       crashing — ids cannot survive undo, which
                       rebuilds every item from a snapshot. Drawing goes
                       through `ai_assistant.apply_specs` (same spec
                       format as the chat and the examples), symbols
                       through `PaintScene._place_symbol`, models through
                       `place_mol_element`/`place_built_molecule`/
                       `reorient_model`. Programmatic moves run with grid
                       snapping off (`_unsnapped`) — a client asks for
                       exact coordinates — and a placed symbol is
                       `_recentre`d on its REAL bounding box (the app
                       centres on the nominal design box, which is right
                       for click-to-place because the user then drags it).
  - `mcp_bridge.py`  — `McpBridge`: loopback JSON server on 127.0.0.1
                       exposing those tools, token-authenticated from the
                       endpoint file, off until Tools ▸ MCP Server. Wraps
                       every mutating call in ONE undo macro (`MCP: <tool>`)
                       so a remote figure is one Ctrl+Z;
                       `_NO_MACRO_TOOLS` are the ones that touch the
                       stack themselves (Qt refuses `clear()`/`setClean()`
                       mid-macro). Access levels read/edit/full — the
                       edit→full line is the **filesystem**
                       (`_names_a_path`: `save_document` with no path is
                       Ctrl+S and stays at edit).
  - `mcp_server.py`  — the half an MCP host launches: JSON-RPC over
                       stdio, no Qt, no third-party imports. Forwards
                       each `tools/call` over the bridge socket and
                       reconnects on its own, so either side may restart.
                       `tool_content` turns a result carrying
                       `IMAGE_KEY` into a real MCP **image block** — a
                       drawing app that could only describe itself in
                       prose would be half blind.
  - `mcp_http.py`    — the same bridge over Streamable HTTP at
                       `http://127.0.0.1:<port>/mcp`, for clients that
                       only take a URL. Same token, same access level,
                       same macros; validates `Origin` (a local server
                       needs no CORS preflight, so a web page could
                       otherwise drive the drawing).
  - `mcp_hosts.py`   — writes KhervePaint's entry into an MCP host's own
                       config (Claude Desktop, Claude Code via its CLI,
                       Cursor, Windsurf, VS Code, Cline, LM Studio). Backs
                       up, writes atomically, touches no other key; Zed is
                       refused because its settings hold comments.
  - `mcp_dialog.py`  — Tools ▸ MCP Server…: enable/disable, access level,
                       one-click host connect, hand-config snippets and a
                       live activity log.
- `docs/MCP.md` — how to connect an assistant, what the 26 tools do,
  access levels, security, troubleshooting.
- `tests/` — pytest suite (offscreen Qt; run `python -m pytest tests/`).
  `conftest.py` isolates QSettings and owns the **single session-wide
  `MainWindow`** (`paint_window` / `win`): a window per test churns
  through QMainWindows, and one collected while its scene still has
  signals in flight raises inside a Qt slot — which PyQt turns into an
  abort of the whole run, not a test failure.
- `requirements.txt`, `LICENSE` (GPL-3.0).

## Architecture

Everything lives in one `QGraphicsScene`:

- The **raster layer** is a `QGraphicsPixmapItem` at z = -10, never
  selectable. "Open PNG" loads into it; the bucket tool can paint into
  it (raster mode). The **pencil** is a *vector* freehand tool: it
  builds a `QPainterPath` as you drag (`pencil_begin/extend/end`) and
  drops a `PathItem` stroke — selectable, movable, resizable (scale
  handles), rotatable, and saved to .kpaint/SVG like any path. It does
  NOT snap to grid while drawing.
- **Vector tools** create `QGraphicsItem` subclasses defined in
  `canvas.py` that mix in `SnapMixin`, so items snap to the grid both
  on creation and while being moved with the pointer:
  - Two-point tools (`_TWO_POINT_TOOLS`): line, arrow (`ArrowItem`
    extends `LineItem` and draws a filled head) and dimension.
    `LineItem` carries an optional **bend** control point (`set_bend`;
    None = straight) that turns it into a quadratic curve — geometry
    via `curve_path()`, arrowheads follow `end_angle()`, serialised as
    `"bend"` in JSON and a `<path>` + `kp:bend` in SVG; dimensions
    never bend
    (`DimensionItem` extends `LineItem`: a live length label plus a
    configurable style — end caps (`cap_style`: arrows/ticks/dots/none),
    optional `extension` witness lines, solid/`dash` line, and label
    `unit` (mm/cm/in)/`decimals`/`prefix`/`suffix`, all edited in the
    properties dialog. Length derives from `scene.dpi`; edited via its
    endpoints like a line, serialised as type `dimension` / SVG
    `kp:kind="dimension"` with `kp:dim-*` style attrs).
  - Rect-defined tools (`_RECT_TOOLS`): rect, circle (square ellipse),
    ellipse, rounded rect (`RoundedRectItem`, real `radius`), a large
    set of parametric polygons via one `PolygonItem` whose geometry is
    always a vertex list — triangle, right triangle, diamond,
    parallelogram, trapezoid, pentagon..octagon, 5/6-point star, plus,
    chevron, block arrow, lightning, house (see `_POLY_FRACTIONS` /
    `_POLY_SIDES`) — and the parametric arcs (`ArcShapeItem`: half/
    quarter circle + flip flags). All are box-resizable; every polygon
    explodes into its edge lines for free.
  - Text (`TextItem`) edits inline on double-click.
  - `ImageItem` is a movable bitmap on the vector layer (paste, or
    drag-and-drop an image file/data onto the canvas — `PaintView`
    accepts drops and emits `content_dropped`, which `MainWindow._on_drop`
    turns into `ImageItem`s at the drop point; a dropped `.svg`/`.kpaint`
    opens as a document instead); crop
    it via the right-click menu (`crop.py`).
  - Rect/ellipse/rounded-rect/polygon also carry an optional centred
    text **label** (`LabelMixin`) edited from their properties dialog.
  Every item also round-trips opacity and rotation, and rotates about
  its own centre via `center_origin()` (transform origin = bounding-
  rect centre) — never the scene origin, or far-from-origin shapes
  swing off-screen.
- **No default selection rectangle**: every item mixes in `NoSelMixin`,
  whose `paint` strips `State_Selected` before the base paint, so Qt's
  dashed selection box is never drawn (it lingered after deselect,
  especially for grouped items). Selection feedback is instead our own:
  the handles, plus a cosmetic **dashed outline** drawn around every
  selected top-level item in `PaintView._draw_selection` (in the
  foreground, so it never lingers or exports — and it makes a
  *multi-*selection visible, which handles alone don't). Lines/arrows
  are the exception: their dash runs along the line's own geometry
  (the curve when bent), not a bounding box — a selected line shows
  endpoint + bend handles, never a rectangle.
- **Selection handles** (`handles.py`) — selecting one item shows
  resize handles (line/arrow endpoints, polygon vertices, rect/ellipse
  bounding box, uniform-scale corners for path/image/text, or — for a
  **group** (`gbox`) — eight corner+side handles that resize it in X
  and/or Y by folding a non-uniform scale into the group's `transform()`
  about the opposite handle; that transform round-trips exactly in
  `.kpaint` via a `"matrix"` field and is baked into children on SVG
  load). Double-clicking enters rotate mode (a knob spins it about its
  centre). The scene owns one `SelectionHandles`; handles are
  `Handle`-marked, rebuilt on pointer mouse-release, dropped when
  selection changes, and filtered out of all serialisation and
  `vector_items` (`isinstance(c, Handle)`). They parent to the active
  item so they follow it — **except for a `GroupItem`**, whose handles
  live at **scene level** (`SelectionHandles._scene_level`): a
  `QGraphicsItemGroup` intercepts its children's mouse events (PyQt can't
  disable that), so child handles on a group would be dead — scene-level
  handles keep groups resizable/rotatable.
- **Grid** is drawn in `PaintView.drawForeground` so it never appears
  in PNG exports. Grid size / show / snap live on the scene and
  round-trip through `.kpaint`.
- **Groups** use `QGraphicsItemGroup` via a snap-aware subclass;
  Ctrl+G / Ctrl+Shift+G.
- **Explode** (`explode_selection`, Ctrl+Shift+E / context menu) breaks
  any shape's outline into its individual segments — straight edges →
  `LineItem`, curved edges (ellipse/rounded-corner/arc/pencil) →
  per-segment `PathItem` — by walking `_outline_path(item)` mapped to
  scene coords. Left selected so a piece can be deleted and the rest
  regrouped. (Lines/text/images/groups have no breakable outline.)
- **Mirror** (`mirror_selection`, Ctrl+Shift+H / J, context menu, toolbar)
  flips selected items in place about their centre by flipping geometry
  (polygon/line/path), the pixmap (image) or the arc flip flags — so the
  flip persists through save rather than relying on a transform. A
  **group** flips by `_mirror_group`: flip each child in place and
  reflect its position about the group centre (the two together equal
  reflecting the whole group), keeping children native. Groups also
  **rotate** (double-click) and **resize** (scale handles) like any item.
- **Bucket fill** (`fill.py`) renders the scene and flood-fills the
  region enclosed by shape outlines from the click point. Output mode
  (raster paint vs editable vector path) is chosen per-fill via the
  toolbar selector; the scene flag is `bucket_vector`. Fills between
  several shapes work whenever their outlines enclose the area.

## Document format

**SVG is the one native save/open format** (`svgio.py`): Save writes a
standard, fully SVG-compatible file (one element per native item, raster
embedded as `<image>`, grid settings + polygon kind + dim style under a
private `kp:` namespace that other viewers ignore) and Open parses SVG
back into editable items. Opening an external SVG breaks it into native
items — `<g>` → `GroupItem` (ungroupable), primitives → their items,
`<path>` / scaled-or-sheared elements → `PathItem`. Export (Ctrl+E)
writes flattened PNG/PDF. Save As offers **only `.svg`**; the older
`.kpaint` JSON files still *open* (via *All files*) but are no
longer offered for saving.

The JSON serialisation in `document.py` (`scene_to_dict`/`dict_to_scene`)
is still the in-memory snapshot format that powers **undo/redo**, and
remains the on-disk shape of legacy `.kpaint` files:
`{"format": "kpaint", "version":
1, "width", "height", "grid": {"size", "show", "snap"}, "raster":
"<base64 PNG>", "items": [...]}`. Each item dict has `"type"`
(`line|arrow|rect|roundrect|ellipse|polygon|path|text|image|group`),
position, geometry, pen/brush, opacity, rotation; groups nest
`"children"`. When an item gains new persisted properties, bump
`FORMAT_VERSION` in `document.py`, keep loading backward compatible,
**and** extend `svgio.py` so the property survives SVG round-trips.

## UI conventions

- Single canvas window; left toolbar column = tools (exclusive
  checkable group). Direct buttons (pointer/pencil/eraser/colour-picker/
  bucket/line/arrow/text — eraser paints the raster white, colour-picker
  samples the rendered pixel into the stroke pen) plus four shape
  **dropdown** buttons (`SHAPE_GROUPS`:
  Rectangles, Ellipses & arcs, Polygons, Stars & symbols) — each a
  `QToolButton` menu that remembers the last-picked shape. The
  **ruler/dimension** is its own dropdown (`DIM_ORIENTATIONS` /
  `DIM_CAPS`): pick an **orientation** (aligned/horizontal/vertical —
  horizontal/vertical constrain the drawn line to measure Δx/Δy via
  `scene.dim_orientation` + `PaintScene._dim_constrain`) and a default
  **end-cap** style (`scene.dim_cap`, applied to each new
  `DimensionItem`); either choice activates the tool, as does **M**. A
  **Chemistry** dropdown (`_CHEM_*` tools) holds bond tools (single/
  double/triple/wedge/hash/hydrogen — two-point, built via
  `chemistry.bond_path`/`wedge_polygon` as `PathItem`/`PolygonItem`; the
  H-bond's dashes are geometry so they survive SVG), a **chain** tool
  (click-to-click connected single bonds; finish with a repeat click /
  right-click / Esc — `PaintScene._chain_click`/`end_chain`),
  click-to-place rings
  (benzene→hexagon+inner circle group, cyclohexane, cyclopentane) and an
  atom-label sub-menu (sets `scene.chem_atom`, places a `TextItem` that
  snaps onto a nearby bond end via `_nearest_bond_end`, so e.g. a C=O is a
  double bond + an O dropped on its tip). Bonds
  snap to a **fixed length + 30° angle** (`scene.chem_fixed` default True,
  `bond_length_mm`, `PaintScene._chem_constrain`). A **Room layout**
  dropdown (`PLAN_PLACE` tool, `floorplan.py`) click-places top-view
  walls/doors/furniture (grouped, real-world mm sizes) by category; its
  first entry is a drag-to-size **Room** (`ROOM` rect tool → on release,
  `_finish_room` builds a grouped wall ring: four thin solid wall bars
  with an empty (hollow) square at each corner where the walls meet). An
  **Electrical** dropdown (`ELEC_PLACE`, `electrical.py`) likewise places
  circuit + installation symbols. The
  column ends with an **Objects** dropdown (the reusable-object/template
  library, see `library.py`): save the selection, open the **Template
  Explorer**, or insert a saved object — folders shown as nested
  sub-menus. Top toolbar = file ops + undo/redo + stroke/fill colour,
  width, grid, arrange (incl. front/forward/backward/back order icons). Grid spacing is set in **mm** (converted via `scene.dpi`);
  an **Infinite paper** toggle fills the view with grid (default **on**;
  `PaintView.apply_scroll_bounds` then also paints the whole canvas white,
  not the themed surround). The line
  **width** is a dropdown of thin-to-thick line swatches
  (`LINE_WIDTHS`, drawn by `icons.line_width_icon` in the current stroke
  colour), not a numeric spinner.
- Pointer tool = rubber-band select + move; other tools draw.
  Shift/Ctrl+click toggles an item in/out of the selection — handled
  in `PaintScene._toggle_select` on *press* (Qt's native Ctrl toggle
  fires on release and aborts on any click jitter, and Qt ignores
  Shift entirely). A modifier-click that lands on empty canvas keeps
  the selection (a missed click must not nuke it).
- **Picking** (`OutlinePickMixin` + `_stroke_only_shape` in canvas.py):
  unfilled, unlabelled shapes hit-test on their **outline only** — Qt's
  default shape() includes the implicit fill region even for hollow
  items, letting a big empty curve/arc/rect swallow every click inside
  it (stealing selection from e.g. a bucket-fill path behind it). The
  pick ribbon is fattened to ≥8 px for easy clicking of thin strokes,
  but `boundingRect()` is overridden to the exact-pen-width value —
  Qt's rect/ellipse/polygon/path items derive boundingRect from
  shape() when the pen is wide, so a fat ribbon would otherwise
  silently inflate geometry, group bounds and exports.
- Select an item to get resize handles; **double-click to rotate** it
  about its centre. Right-click for the context menu (which includes
  Edit properties… for the full per-item editor).
- Status bar shows the cursor position in canvas coordinates (left) and
  zoom controls bottom-right: −/+ buttons, a log-scaled `QSlider` and a
  clickable percentage that resets to 100%. The view exposes
  `set_zoom`/`current_zoom`/`MIN_ZOOM`/`MAX_ZOOM` and a `zoom_changed`
  signal that keeps the slider/label in sync with wheel and menu zoom.
- **Window style**: Fusion as default; themes shared with the family
  (View > Theme).

## MCP (Model Context Protocol)

KhervePaint is drivable by **any local MCP assistant** — Claude
Desktop, Claude Code, Cursor, Cline, VS Code, LM Studio — not just the
built-in chat. The chat replies with shape specs; an MCP client gets
the whole app as **26 tools**: the canvas, `draw`, item editing,
alignment, all fourteen symbol palettes, the molecule/crystal builders,
the document, and `render_canvas`, which hands back a **PNG the model
can actually look at** (overlaps and off-page shapes are obvious in the
picture and invisible in JSON).

Two halves, because they run in different processes:

```
 host ──stdio──▶ khervepaint.mcp_server ──loopback TCP──▶ McpBridge ──▶ window
 host ──HTTP POST────────────────────────────────────────▶ McpHttpServer ──┘
```

The stdio server is the subprocess the host owns (no Qt, no deps, so it
starts instantly and works from any Python); the bridge lives in the
app, where the tools can touch live Qt items on the GUI thread. Either
side may restart without the other noticing. `--mcp-server` on the
frozen executable takes the same path, checked **before** any GUI work.

Load-bearing details:

- **One undo macro per call**, so a remote assistant's whole figure is
  one Ctrl+Z. Tools that manipulate the stack themselves (save/open/
  new/load_example) run outside the macro — Qt refuses `clear()` and
  `setClean()` mid-macro, which would silently leave a saved document
  flagged as modified.
- **Every mutating tool still emits `changed_by_user`**, including the
  post-placement `_recentre` nudge; the snapshot policy below applies
  to MCP exactly as it does to a mouse gesture.
- **Access levels** (Tools ▸ MCP Server, persisted in QSettings):
  read / edit / full. The edit→full line is the filesystem, not the
  drawing — at *edit* a client can do anything to the open document
  (worst case: you undo it), while naming a path to read or write waits
  for *full*.
- **127.0.0.1 only**, random per-session token in the endpoint file
  (`mcp-bridge.json` in the platform state dir), bridge off until the
  user turns it on, endpoint removed when the window closes.

Adding a tool: define it in `mcp_schema.TOOLS`, implement `_t_<name>`
on `McpToolExecutor`, and decide whether it belongs in
`_READ_ONLY_TOOLS` / `_NO_MACRO_TOOLS` / `_FILE_TOOLS`. The two test
modules assert the schema and the implementations stay in step, so a
half-added tool fails the suite.

## Roadmap

- Layers panel.
- Copy/paste of vector items across documents.

## Undo / redo policy

**Every change to the document is undoable** via a full-document
snapshot stack: `undo.py`'s `SnapshotCommand` on a `QUndoStack` owned
by `MainWindow`. The mechanism is driven entirely by the scene's
`changed_by_user` signal — whenever it fires, the window serialises the
whole document (`document.scene_to_dict`, which already captures every
item property, the raster layer and the grid) and pushes a command
that swaps between the before/after snapshots. Undo/redo restore by
calling `document.dict_to_scene`. So anything that round-trips through
the persistence layer is automatically undoable.

**This makes one rule load-bearing: every new user action that changes
the document MUST emit `changed_by_user` exactly once when it
completes** (not per mouse-move — once per finished gesture). If it
doesn't, the action silently won't be undoable.

**Pre-commit check (required): before committing any change, verify
that every new or modified user action that alters the document emits
`changed_by_user`, and that the property it changes is serialised by
`document.py`/`svgio.py` (so the snapshot captures it). If you add a
new persisted property, it must be in `scene_to_dict`/`item_to_dict`
*and* survive `dict_to_scene` — otherwise undo will lose it.** Confirm
this explicitly in the commit, e.g. add a one-line test or note that
the action is undoable.

## Persistence policy

**All item properties must round-trip through both the JSON snapshot
(`document.py`, which powers undo) and the SVG file format (`svgio.py`,
the only on-disk native format).** When adding a property, update
`item_to_dict()`/`item_from_dict()` in `document.py` *and* the
write/read in `svgio.py` together, and extend the round-trip tests in
`tests/` (cover both formats).

## Commit / push policy

**Every change must land as a commit on the `dev` branch and be pushed
immediately.** No batching. No exceptions. No `Co-Authored-By:` trailer.

Commit subjects under 70 chars; body explains *why*, not what.

**Commit message prefix** — every subject line must start with one of:

- `fix:` — bug fix
- `feat:` — new feature or option
- `refactor:` — code restructuring, no behavior change
- `style:` — formatting, UI tweaks
- `docs:` — documentation only
- `perf:` — performance improvement

## Licensing

GPL-3.0. New source files must carry the short GPL notice at the top.
