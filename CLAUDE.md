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
                       items). Imports the path helpers from document.
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
                       px/in/mm at a DPI, ACS journal + paper presets,
                       custom, or fit-to-drawing. Sets `scene.dpi` and
                       drives `resize_canvas`/`fit_to_content` (undoable).
                       `scene.dpi` round-trips (.kpaint/SVG) and drives
                       physical export size (PNG dpi, PDF page, SVG inch
                       width with px viewBox).
  - `undo.py`        — `SnapshotCommand`: whole-document snapshot
                       undo/redo (see Undo / redo policy).
  - `help.py`        — rich About dialog + in-app User Guide
                       (`Help ▸ User Guide`, F1). Keep the guide and the
                       repo `USERGUIDE.md` in sync when features change.
- `tests/` — pytest suite (offscreen Qt; run `python -m pytest tests/`).
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
  - Two-point tools (`_TWO_POINT_TOOLS`): line and arrow (`ArrowItem`
    extends `LineItem` and draws a filled head).
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
  - `ImageItem` is a movable bitmap on the vector layer (paste); crop
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
  especially for grouped items). Selection feedback is the handles.
- **Selection handles** (`handles.py`) — selecting one item shows
  resize handles (line/arrow endpoints, polygon vertices, rect/ellipse
  bounding box, or uniform-scale corners for path/image/text/group);
  double-clicking enters rotate mode (a knob spins it about its
  centre). The scene owns one `SelectionHandles`; handles are
  `Handle`-marked children of the active item, rebuilt on pointer
  mouse-release, dropped when selection changes, and filtered out of
  all serialisation (`isinstance(c, Handle)`).
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

**SVG is the default save/open format** (`svgio.py`): Save writes
editable, standard SVG (one element per native item, raster embedded
as `<image>`, grid settings + polygon kind under a private `kp:`
namespace) and Open parses SVG back into editable items. Opening an
external SVG breaks it into native items — `<g>` → `GroupItem`
(ungroupable), primitives → their items, `<path>` / scaled-or-sheared
elements → `PathItem`. Save also offers `.kpaint`; Export (Ctrl+E)
writes flattened PNG/PDF.

`.kpaint` is the JSON native format: `{"format": "kpaint", "version":
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
  `QToolButton` menu that remembers the last-picked shape. Top toolbar =
  file ops + undo/redo + stroke/fill colour, width, grid, arrange.
- Pointer tool = rubber-band select + move; other tools draw.
- Select an item to get resize handles; **double-click to rotate** it
  about its centre. Right-click for the context menu (which includes
  Edit properties… for the full per-item editor).
- Status bar shows the cursor position in canvas coordinates.
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

**All item properties must round-trip through `.kpaint`.** When
adding a property, update `item_to_dict()` and `item_from_dict()` in
`document.py` together, and extend the round-trip test in `tests/`.

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
