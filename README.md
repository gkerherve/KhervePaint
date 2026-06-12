# KhervePaint

Hybrid raster + vector drawing app in the Kherve family
(KherveFitting, KherveSheet, KhervePDF, KherveBook, ...), built with
Python + PyQt5.

One canvas mixes two worlds:

- **Raster layer** — open a PNG and paint on it freehand with the
  pencil tool; export the flattened result back to PNG.
- **Vector layer** — lines, rectangles, circles, ellipses and text
  drawn on top, selected and moved with the pointer tool, groupable
  (Ctrl+G / Ctrl+Shift+G), with a grid overlay and snap-to-grid.

Documents save as `.kpaint` (JSON: vector items + the raster layer
embedded as base64 PNG) and export as flattened `.png`, `.svg` or
single-page `.pdf` (Ctrl+E). Selected lines show endpoint handles —
drag a handle to move just that end of the line.

## Run

```
pip install -r requirements.txt
python KhervePaint.py
```

## Tools

| Key | Tool |
| --- | --- |
| V | Pointer (select / move / rubber-band) |
| P | Pencil (freehand, paints the raster layer) |
| L | Line |
| R | Rectangle |
| C | Circle |
| E | Ellipse |
| T | Text (click to place, double-click to edit) |

Ctrl+wheel zooms; the grid and snap toggles live in the toolbar and
the View menu, with selectable themes under View > Theme.

## Tests

```
python -m pytest tests/
```

## License

GPL-3.0 — Gwilherm Kerherve.
