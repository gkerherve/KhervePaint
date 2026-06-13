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

**Explode** (Ctrl+Shift+E, or the right-click menu) breaks a polygon or
rectangle into its separate edge lines — so you can delete or edit one
side, then select the rest and regroup (Ctrl+G).

Shapes can hold a **centred text label** (set it in the shape's
properties), and images can be **cropped** — right-click an image →
*Crop image*, drag the handles, then Enter to apply (Esc cancels). The
grid control sets the number of **divisions** across the canvas, so a
higher number means a finer grid.

**File ▸ Drawing Size** sets the canvas size: pick a publication preset
(A4, US Letter, journal column widths at 300 dpi, slides), enter a
custom width × height, or **fit to drawing** to shrink the canvas snugly
around your shapes (optionally just the selection). Everything is
undoable with **Ctrl+Z / Ctrl+Y**.

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
