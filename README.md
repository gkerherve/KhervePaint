# KhervePaint

Hybrid raster + vector drawing app in the Kherve family
(KherveFitting, KherveSheet, KhervePDF, KherveBook, ...), built with
Python + PyQt5.

One canvas mixes two worlds:

- **Raster layer** — open a PNG, fill regions into it with the bucket
  tool, and export the flattened result back to PNG.
- **Vector layer** — freehand pencil strokes, lines, arrows,
  rectangles, circles, ellipses, polygons and text drawn on top,
  selected/moved/resized/rotated with the pointer tool, groupable
  (Ctrl+G / Ctrl+Shift+G), with a grid overlay and snap-to-grid.

Documents **save and open as editable SVG by default** — an opened SVG
is broken into editable items (groups ungroup; paths and transformed
elements become editable path items). `.kpaint` (lossless JSON) is also
offered, and Export (Ctrl+E) writes flattened `.png` or single-page
`.pdf`. Selected lines show endpoint handles — drag a handle to move
just that end of the line.

## AI assistant

A dockable **AI Assistant** (View ▸ AI Assistant) can draw for you. Pick
a provider — **Claude, ChatGPT, Mistral, Ollama or a Local endpoint** —
enter its API key, hit **Refresh** to list its models, then ask in plain
language ("draw a blue flowchart box labelled Start with an arrow to a
circle below"). The reply's shape specs become real, editable, undoable
items on the canvas. Keys are stored locally via QSettings; no extra
dependencies (it uses `urllib`).

## Examples

The **Examples** menu loads ready-made, fully labelled schematics of
common lab techniques onto an A4 page, grouped by category —
**Spectroscopy** (XPS, FTIR, XRF, SIMS), **Diffraction** (XRD),
**Microscopy** (TEM, AFM) and **Thermal & sorption** (TGA, BET). Each is
built from normal editable items, so it doubles as a starting point you
can restyle, relabel and export.

## Run

```
pip install -r requirements.txt
python KhervePaint.py
```

Recently opened/saved files are listed under **File ▸ Open Recent**.

## Tools

| Key | Tool |
| --- | --- |
| V | Pointer (select / move / rubber-band) |
| P | Pencil (freehand vector stroke — selectable & editable) |
| B | Bucket (flood-fill an enclosed region) |
| L | Line |
| R | Rectangle |
| C | Circle |
| E | Ellipse |
| T | Text (click to place, double-click to edit) |

Select a shape to get **resize handles** — drag the endpoints of a
line, the vertices of a polygon, or the bounding-box corners of a
rectangle/ellipse. **Double-click** a shape to **rotate** it about its
own centre. Right-click for the context menu (edit properties,
duplicate, order, group).

Shapes are grouped into dropdown buttons on the tool column —
**Rectangles**, **Ellipses & arcs** (circle, ellipse, half/quarter
circle), **Polygons** (triangle … octagon) and **Stars & symbols**
(stars, cross, chevron, block arrow, lightning, house). Every shape can
be **exploded** into its edge segments.

**Explode** (Ctrl+Shift+E, or the right-click menu) breaks any shape's
outline into its separate segments — straight edges become lines and
curves (ellipses, rounded corners, arcs) become individual arc pieces —
so you can delete or edit one part, then select the rest and regroup
(Ctrl+G). **Flip horizontal /
vertical** (Ctrl+Shift+H / J, right-click, or toolbar) mirrors the
selected shapes in place.

Shapes can hold a **centred text label** (set it in the shape's
properties), and images can be **cropped** — right-click an image →
*Crop image*, drag the handles, then Enter to apply (Esc cancels). The
grid control sets the number of **divisions** across the canvas, so a
higher number means a finer grid.

**File ▸ Drawing Size** sets the canvas in **px, inches or mm** at a
chosen **DPI** — with publication presets including **ACS single column
(3.25 in)** and **double column (7.0 in)** at 300 dpi, plus A4/Letter
and slides. Exports carry the real physical size: PNG embeds the DPI,
PDF pages are the figure's true inch size, and SVG sets its width/height
in inches (with a pixel `viewBox`). You can also **fit to drawing** to
shrink the canvas snugly around your shapes (optionally just the
selection). Everything is undoable with **Ctrl+Z / Ctrl+Y**.

The **bucket** fills a region enclosed by shape outlines — click inside
the area walled off by two or more shapes and it fills with the current
fill colour. The toolbar selector chooses whether each fill is painted
into the raster layer or becomes an editable vector path behind the
shapes.

Ctrl+wheel zooms; the grid and snap toggles live in the toolbar and
the View menu, with selectable themes under View > Theme.

## Tests

```
python -m pytest tests/
```

## License

GPL-3.0 — Gwilherm Kerherve.
