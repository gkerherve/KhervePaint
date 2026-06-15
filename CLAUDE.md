# KherveScribe — notes for Claude

KherveScribe is a hybrid raster + vector drawing app built on PyQt5 —
a native desktop app in the Kherve family (KherveFitting, KherveSheet,
KhervePDF, KherveDOC, KhervePlot, KherveDraw, KherveBook). One canvas
mixes a raster layer (open a PNG, paint on it with the pencil) and
vector items on top (lines, rectangles, circles, ellipses, text),
edited with a pointer tool, with grid + snap-to-grid and grouping.

## Build / run

- Python 3.12 / 3.13 with PyQt5 (+ qtawesome for icons).
- Run via `python KherveScribe.py` or `python -m khervescribe`.
- Crash log: `%TEMP%/khervescribe_crash.log`.
- **Version string** is derived at runtime in `_version.py` from
  `git rev-list --count HEAD` and `git rev-parse --short HEAD`,
  cached with `lru_cache`. Falls back to `_FALLBACK = "0.1.0"`
  outside a git checkout. Title bar reads `KherveScribe v0.1.N+sha`.
  The version bumps automatically on every commit — never edit a
  version constant by hand.

## File size policy

Every module in `khervescribe/` should stay near **1500 lines**. If a
change would push a file meaningfully past that, split the new code
into a new module and import.

## Project layout

- `KherveScribe.py` — entry script.
- `khervescribe/` — package; `python -m khervescribe` is the alternative entry.
  - `__init__.py`    — `APP_NAME`, version import.
  - `__main__.py`    — module entry point.
  - `_version.py`    — git-based version string.
  - `app.py`         — `main()`, crash log, Fusion style + theme.
  - `style.py`       — token-driven QSS themes (same template family as
                       KherveBook; theme persists via QSettings).
  - `icons.py`       — qtawesome MDI icon wrapper with fallback.
  - `mainwindow.py`  — `MainWindow` shell: menus, tool/option toolbars,
                       open PNG / .kscribe, save, export PNG.
  - `canvas.py`      — `PaintScene` + `PaintView`: raster layer at the
                       bottom (pencil paints into its pixmap), vector
                       items on top, tool state machine in the scene's
                       mouse events, grid overlay in the view, snapping,
                       group/ungroup, zoom.
  - `document.py`    — `.kscribe` JSON (de)serialisation: vector items
                       (recursively through groups), raster layer as
                       base64 PNG; flattened export to PNG and
                       single-page PDF (QPdfWriter, page sized to the
                       canvas at 96 dpi). Owns the path<->command-list
                       helpers used by both .kscribe and svgio.
  - `svgio.py`       — default format: editable SVG writer + parser
                       (breaks groups/paths/transforms into native
                       items). Resolves `<use href="#id">` against a
                       whole-tree id map (so Inkscape/matplotlib exports,
                       which draw ticks/markers/text as `<use>` of
                       `<defs>` glyph paths, import fully). Imports the
                       path helpers from document.
  - `library.py`     — reusable-object/template library: save the current
                       selection as a named standalone SVG in a per-user
                       objects folder (`KHERVESCRIBE_OBJECTS_DIR` override
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
  - `properties.py`  — right-click context menu (edit/duplicate/delete/
                       order/group) + `PropertiesDialog`: edit every
                       property of one item (transform, stroke, fill,
                       geometry, text/font). Double-click a non-text
                       item also opens it.
  - `fill.py`        — bucket flood-fill: renders the scene, scanline-
                       floods the enclosed region from the click, and
                       applies it either as raster paint or an editable
                       vector `PathItem` (behind the bounding shapes).
  - `handles.py`     — `SelectionHandles`: resize handles per item type
                       and a rotate knob (double-click). `Handle`-marked
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
                       `scene.dpi` round-trips (.kscribe/SVG) and drives
                       physical export size (PNG dpi, PDF page, SVG inch
                       width with px viewBox).
  - `undo.py`        — `SnapshotCommand`: whole-document snapshot
                       undo/redo (see Undo / redo policy).
  - `help.py`        — rich About dialog + in-app User Guide
                       (`Help ▸ User Guide`, F1). Keep the guide and the
                       repo `USERGUIDE.md` in sync when features change.
  - `ai_providers.py`— AI back-ends over urllib (no deps): Claude,
                       ChatGPT, Mistral, Ollama, Local. `chat()` and
                       `list_models()`; keys/base URLs in QSettings.
  - `ai_assistant.py`— `AiDock` (View ▸ AI Assistant): chat panel with
                       provider/model combos + Refresh-models button.
                       Parses the model's JSON shape specs and creates
                       real, undoable items (`apply_specs`). Network runs
                       on a `QThread`.
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
- `tests/` — pytest suite (offscreen Qt; run `python -m pytest tests/`).
- `requirements.txt`, `LICENSE` (GPL-3.0).

## Architecture

Everything lives in one `QGraphicsScene`:

- The **raster layer** is a `QGraphicsPixmapItem` at z = -10, never
  selectable. "Open PNG" loads into it; the bucket tool can paint into
  it (raster mode). The **pencil** is a *vector* freehand tool: it
  builds a `QPainterPath` as you drag (`pencil_begin/extend/end`) and
  drops a `PathItem` stroke — selectable, movable, resizable (scale
  handles), rotatable, and saved to .kscribe/SVG like any path. It does
  NOT snap to grid while drawing.
- **Vector tools** create `QGraphicsItem` subclasses defined in
  `canvas.py` that mix in `SnapMixin`, so items snap to the grid both
  on creation and while being moved with the pointer:
  - Two-point tools (`_TWO_POINT_TOOLS`): line, arrow (`ArrowItem`
    extends `LineItem` and draws a filled head) and dimension
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
    turns into `ImageItem`s at the drop point; a dropped `.svg`/`.kscribe`
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
  *multi-*selection visible, which handles alone don't).
- **Selection handles** (`handles.py`) — selecting one item shows
  resize handles (line/arrow endpoints, polygon vertices, rect/ellipse
  bounding box, uniform-scale corners for path/image/text, or — for a
  **group** (`gbox`) — eight corner+side handles that resize it in X
  and/or Y by folding a non-uniform scale into the group's `transform()`
  about the opposite handle; that transform round-trips exactly in
  `.kscribe` via a `"matrix"` field and is baked into children on SVG
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
  round-trip through `.kscribe`.
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
`.kscribe`/`.kpaint` JSON files still *open* (via *All files*) but are no
longer offered for saving.

The JSON serialisation in `document.py` (`scene_to_dict`/`dict_to_scene`)
is still the in-memory snapshot format that powers **undo/redo**, and
remains the on-disk shape of legacy `.kscribe`/`.kpaint` files:
`{"format": "kscribe", "version":
1, "width", "height", "grid": {"size", "show", "snap"}, "raster":
"<base64 PNG>", "items": [...]}`. Each item dict has `"type"`
(`line|arrow|rect|roundrect|ellipse|polygon|path|text|image|group`),
position, geometry, pen/brush, opacity, rotation; groups nest
`"children"`. When an item gains new persisted properties, bump
`FORMAT_VERSION` in `document.py`, keep loading backward compatible,
**and** extend `svgio.py` so the property survives SVG round-trips.

## UI conventions

- Single canvas window; left toolbar column = tools (exclusive
  checkable group). Direct buttons (pointer/pencil/bucket/line/arrow/
  text) plus four shape **dropdown** buttons (`SHAPE_GROUPS`:
  Rectangles, Ellipses & arcs, Polygons, Stars & symbols) — each a
  `QToolButton` menu that remembers the last-picked shape. The
  **ruler/dimension** is its own dropdown (`DIM_ORIENTATIONS` /
  `DIM_CAPS`): pick an **orientation** (aligned/horizontal/vertical —
  horizontal/vertical constrain the drawn line to measure Δx/Δy via
  `scene.dim_orientation` + `PaintScene._dim_constrain`) and a default
  **end-cap** style (`scene.dim_cap`, applied to each new
  `DimensionItem`); either choice activates the tool, as does **M**. A
  **Chemistry** dropdown (`_CHEM_*` tools) holds bond tools (single/
  double/triple/wedge/hash — two-point, built via `chemistry.bond_path`/
  `wedge_polygon` as `PathItem`/`PolygonItem`), click-to-place rings
  (benzene→hexagon+inner circle group, cyclohexane, cyclopentane) and an
  atom-label sub-menu (sets `scene.chem_atom`, places a `TextItem`). The
  column ends with an **Objects** dropdown (the reusable-object/template
  library, see `library.py`): save the selection, open the **Template
  Explorer**, or insert a saved object — folders shown as nested
  sub-menus. Top toolbar = file ops + undo/redo + stroke/fill colour,
  width, grid, arrange (incl. front/forward/backward/back order icons). Grid spacing is set in **mm** (converted via `scene.dpi`);
  an **Infinite paper** toggle fills the view with grid. The line
  **width** is a dropdown of thin-to-thick line swatches
  (`LINE_WIDTHS`, drawn by `icons.line_width_icon` in the current stroke
  colour), not a numeric spinner.
- Pointer tool = rubber-band select + move; other tools draw.
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

## Roadmap

- Eraser and colour picker for the raster layer.
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
