"""About dialog and the in-app User Guide.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QMessageBox,
                             QTextBrowser, QVBoxLayout)

from . import APP_NAME, __version__, icons

REPO_URL = "https://github.com/gkerherve/KhervePaint"


def about_html() -> str:
    return f"""
<div style="font-family:'Segoe UI',sans-serif;">
  <h2 style="margin-bottom:2px;">{APP_NAME}</h2>
  <p style="color:#666;margin-top:0;">Version {__version__}</p>
  <p><b>KhervePaint</b> is a hybrid <b>raster + vector</b> drawing app for
  figures, diagrams and quick image edits — a native desktop tool in the
  Kherve family (KherveFitting, KherveSheet, KhervePDF, KherveBook&nbsp;…).</p>
  <p>Open a photo or PNG and paint on it, or build clean vector artwork
  with shapes, arrows, text and freehand strokes — then save it as
  <b>editable SVG</b> or export a publication-ready figure at the exact
  physical size (ACS column widths, A4, custom inches/mm at any DPI).</p>
  <p style="margin-bottom:2px;"><b>Highlights</b></p>
  <ul style="margin-top:0;">
    <li>19 parametric shapes, all resizable, rotatable and explodable</li>
    <li>Vector pencil, bucket fill (raster or vector), text labels in shapes</li>
    <li>Move / resize / rotate / mirror, group, crop images</li>
    <li>Full undo &amp; redo of everything</li>
    <li>Editable SVG as the native format; PNG &amp; PDF export</li>
  </ul>
  <p style="color:#666;">Created by <b>Gwilherm Kerherve</b> · GPL-3.0<br>
  <a href="{REPO_URL}">{REPO_URL}</a></p>
</div>
"""


def show_about(parent):
    box = QMessageBox(parent)
    box.setWindowTitle(f"About {APP_NAME}")
    box.setIconPixmap(icons.app_icon().pixmap(64, 64))
    box.setTextFormat(Qt.RichText)
    box.setText(about_html())
    box.setStandardButtons(QMessageBox.Ok)
    box.exec_()


# ----------------------------------------------------------------- guide
def _shortcut_rows(pairs):
    rows = "".join(
        f"<tr><td style='padding:2px 14px 2px 0;white-space:nowrap;'>"
        f"<code>{k}</code></td><td style='padding:2px 0;'>{v}</td></tr>"
        for k, v in pairs)
    return f"<table style='border-collapse:collapse;'>{rows}</table>"


def user_guide_html() -> str:
    tools = _shortcut_rows([
        ("V", "Pointer — select, move, resize, rotate"),
        ("P", "Pencil — freehand vector stroke"),
        ("B", "Bucket — fill an enclosed region"),
        ("L", "Line"), ("A", "Arrow"),
        ("R", "Rectangle"), ("C", "Circle"), ("E", "Ellipse"),
        ("T", "Text"),
    ])
    edit_keys = _shortcut_rows([
        ("Ctrl+Z / Ctrl+Y", "Undo / Redo"),
        ("Ctrl+C / Ctrl+V / Ctrl+X", "Copy / Paste / Cut"),
        ("Ctrl+D", "Duplicate"),
        ("Ctrl+A", "Select all"),
        ("Delete", "Delete selection"),
        ("Ctrl+G / Ctrl+Shift+G", "Group / Ungroup"),
        ("Ctrl+Shift+E", "Explode shape into edges"),
        ("Ctrl+Shift+H / Ctrl+Shift+J", "Flip horizontal / vertical"),
    ])
    file_keys = _shortcut_rows([
        ("Ctrl+N / Ctrl+O / Ctrl+S", "New / Open / Save"),
        ("Ctrl+Shift+S", "Save As"),
        ("Ctrl+Shift+P", "Drawing size"),
        ("Ctrl+E", "Export PNG / PDF"),
        ("Ctrl+Q", "Quit"),
    ])
    view_keys = _shortcut_rows([
        ("Ctrl+Mouse wheel", "Zoom in / out"),
        ("Ctrl+0", "Reset zoom"),
        ("Ctrl+'", "Show / hide grid"),
        ("Ctrl+Shift+'", "Snap to grid on / off"),
        ("F1", "This user guide"),
    ])

    return f"""
<div style="font-family:'Segoe UI',sans-serif; line-height:1.45;">
<h1>{APP_NAME} — User Guide</h1>
<p><i>A hybrid raster + vector drawing app. This guide covers everything
from drawing your first shape to exporting a publication-ready figure.</i></p>

<h2>1 · The canvas</h2>
<p>A drawing has two layers in one canvas:</p>
<ul>
  <li><b>Raster layer</b> — a bitmap. <i>Open</i> a PNG to load it here,
      or fill into it with the bucket. It travels inside your document.</li>
  <li><b>Vector layer</b> — shapes, lines, arrows, text, freehand pencil
      strokes and pasted images drawn on top. These stay fully editable.</li>
</ul>
<p>The white rectangle is the drawing area; the faint grid around it is a
guide and never appears in exports.</p>

<h2>2 · Tools</h2>
<p>Pick a tool from the left column. The pointer selects; every other
tool draws. Keyboard shortcuts:</p>
{tools}
<p>Below the basic tools is the full set of <b>shapes</b> — rounded
rectangle, triangle, right triangle, diamond, parallelogram, trapezoid,
pentagon, hexagon, heptagon, octagon, 5- and 6-point stars, cross,
chevron, block arrow, lightning bolt, house, and half / quarter circles.
Click one, then drag on the canvas to draw it.</p>

<h2>3 · Colours, width and fill</h2>
<p>On the top toolbar: click the <b>stroke</b> swatch (outline colour) or
the <b>fill</b> swatch to choose colours, toggle <b>Fill new shapes</b>
to give new shapes a fill, and set the line <b>Width</b>. These apply to
the next thing you draw; to recolour an existing item use its properties
(below).</p>

<h2>4 · Selecting, moving, resizing, rotating</h2>
<ul>
  <li><b>Select</b> with the pointer: click an item, or drag a rubber-band
      box around several.</li>
  <li><b>Move</b>: drag the item.</li>
  <li><b>Resize</b>: blue handles appear on a selected item — drag a
      line's endpoints, a polygon's vertices, or a box's corners.</li>
  <li><b>Rotate</b>: <b>double-click</b> the item and drag the green knob;
      it turns about its own centre.</li>
</ul>

<h2>5 · Right-click: properties &amp; more</h2>
<p>Right-click any item for its menu: <b>Edit properties…</b>,
Duplicate, Delete, Flip, Bring to front / Send to back, Group / Ungroup,
Explode, and (for images) Crop.</p>
<p>The <b>properties dialog</b> edits everything about an item — position,
rotation, opacity, stroke and fill, the exact geometry, and for text the
content and font. Shapes can also carry a <b>text label</b> drawn centred
inside them (set it in the Label section).</p>

<h2>6 · Arrange: group, order, mirror, explode</h2>
<ul>
  <li><b>Group</b> (Ctrl+G) several items so they move/resize/rotate/flip
      as one; <b>Ungroup</b> (Ctrl+Shift+G) to split them.</li>
  <li><b>Flip</b> horizontally / vertically (Ctrl+Shift+H / J).</li>
  <li><b>Explode</b> (Ctrl+Shift+E) breaks a shape's outline into its
      separate edges — delete or edit one side, then regroup the rest.</li>
  <li><b>Bring to front / Send to back</b> from the right-click menu.</li>
</ul>

<h2>7 · Bucket fill</h2>
<p>Choose the bucket (B), set the fill colour, and click inside an area
walled off by shape outlines. The toolbar selector chooses whether the
fill is painted into the raster layer or becomes an <b>editable vector
path</b> behind the shapes.</p>

<h2>8 · Images</h2>
<p>Paste a screenshot or copied image with <b>Ctrl+V</b> — it drops in as
a movable picture. To <b>crop</b> it, right-click → <i>Crop image</i>,
drag the frame handles, then press <b>Enter</b> to apply (or <b>Esc</b>
to cancel).</p>

<h2>9 · Grid &amp; snap</h2>
<p>The <b>Divisions</b> box sets how many grid cells span the canvas — a
higher number gives a finer grid. Toggle the grid and snapping from the
toolbar or the View menu. Snapping keeps shapes aligned as you draw and
move them (the pencil stays freehand).</p>

<h2>10 · Drawing size &amp; publication figures</h2>
<p><b>File ▸ Drawing Size</b> sets the canvas in <b>pixels, inches or
millimetres</b> at a chosen <b>DPI</b>. Presets include <b>ACS single
column (3.25 in)</b> and <b>double column (7.0 in)</b> at 300 dpi, plus
A4, US Letter and slides — or enter a custom size, or <b>Fit to
drawing</b> to shrink the canvas around your artwork. Exports then carry
the true physical size (PNG embeds the DPI, PDF pages are the figure's
inch size, SVG sets its width in inches).</p>

<h2>11 · Undo / redo</h2>
<p><b>Ctrl+Z</b> undoes and <b>Ctrl+Y</b> redoes <i>everything</i> —
drawing, moving, resizing, rotating, properties, grouping, cropping,
fills and canvas resizes.</p>

<h2>12 · Saving, opening &amp; exporting</h2>
<ul>
  <li><b>Save</b> writes <b>editable SVG</b> by default (also offered:
      <code>.kpaint</code>, the lossless native format). Re-opening an SVG
      brings every shape back editable; an imported external SVG is even
      broken into editable items you can ungroup.</li>
  <li><b>Open</b> reads <code>.svg</code>, <code>.kpaint</code> or a
      <code>.png</code> image. Recent files are under <b>File ▸ Open
      Recent</b>.</li>
  <li><b>Export</b> (Ctrl+E) writes a flattened <b>PNG</b> or single-page
      <b>PDF</b> at the drawing's physical size.</li>
</ul>

<h2>13 · View &amp; themes</h2>
<p>Zoom with <b>Ctrl + mouse wheel</b>, reset with <b>Ctrl+0</b>. Pick a
colour theme under <b>View ▸ Theme</b>.</p>

<h2>Keyboard shortcuts</h2>
<p><b>Tools</b></p>{tools}
<p><b>Edit &amp; arrange</b></p>{edit_keys}
<p><b>File</b></p>{file_keys}
<p><b>View</b></p>{view_keys}

<p style="color:#888;margin-top:18px;">KhervePaint {__version__} · GPL-3.0
· <a href="{REPO_URL}">{REPO_URL}</a></p>
</div>
"""


class UserGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} — User Guide")
        self.resize(720, 640)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(user_guide_html())
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


def show_user_guide(parent):
    UserGuideDialog(parent).exec_()
