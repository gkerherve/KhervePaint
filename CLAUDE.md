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
- `tests/` — pytest suite (offscreen Qt; run `python -m pytest tests/`).
- `requirements.txt`, `LICENSE` (GPL-3.0).

## Architecture

Everything lives in one `QGraphicsScene`:

- The **raster layer** is a `QGraphicsPixmapItem` at z = -10, never
  selectable. "Open PNG" loads into it; the **pencil** tool paints
  directly into its pixmap with a `QPainter` (freehand — pencil does
  NOT snap to grid).
- **Vector tools** create `QGraphicsItem` subclasses defined in
  `canvas.py` that mix in `SnapMixin`, so items snap to the grid both
  on creation and while being moved with the pointer:
  - Two-point tools (`_TWO_POINT_TOOLS`): line and arrow (`ArrowItem`
    extends `LineItem` and draws a filled head).
  - Rect-defined tools (`_RECT_TOOLS`): rect, circle (square ellipse),
    ellipse, rounded rect (`RoundedRectItem`, real `radius`), and the
    parametric polygons (triangle/diamond/pentagon/hexagon/star) via
    one `PolygonItem` whose geometry is always a vertex list — so an
    SVG-imported `<polygon>` and a star behave identically.
  - Text (`TextItem`) edits inline on double-click.
  - `ImageItem` is a movable bitmap on the vector layer (paste).
  A selected line shows `EndpointHandle` children at each end —
  dragging one moves that endpoint (snapping applies); handles are
  implementation details and must never be serialised or counted as
  vector items. Every item also round-trips opacity and rotation.
- **Grid** is drawn in `PaintView.drawForeground` so it never appears
  in PNG exports. Grid size / show / snap live on the scene and
  round-trip through `.kpaint`.
- **Groups** use `QGraphicsItemGroup` via a snap-aware subclass;
  Ctrl+G / Ctrl+Shift+G.
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
  checkable group), top toolbar = file ops + stroke/fill colour,
  line width, grid controls, group/ungroup.
- Pointer tool = rubber-band select + move; other tools draw.
- Right-click an item (pointer tool) for its context menu; double-click
  a non-text item to open its full properties dialog.
- Status bar shows the cursor position in canvas coordinates.
- **Window style**: Fusion as default; themes shared with the family
  (View > Theme).

## Roadmap

- Undo/redo on a shared `QUndoStack` (add/remove/move/geometry/paint
  strokes), mirroring KherveSheet's `undo_commands.py`.
- Resize/rotate handles on selected vector items.
- Eraser, flood fill, colour picker for the raster layer.
- Layers panel; raster layer resize/crop.
- Copy/paste of vector items, including across documents.
- Resize handles on rect/ellipse (lines already have endpoint handles).

## Undo / redo policy

**Every user-visible change should become undoable** as the app
matures: cell-local text undo comes free in text items, but item
add/remove/move/geometry changes and raster strokes must move onto a
shared QUndoStack.

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
