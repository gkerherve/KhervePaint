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
        ("M", "Dimension — measure &amp; label a distance (mm)"),
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
        ("Ctrl+Shift+N", "New window"),
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
<p>Related <b>shapes</b> are grouped under four dropdown buttons:
<b>Rectangles</b> (rectangle, rounded rectangle), <b>Ellipses &amp;
arcs</b> (circle, ellipse, half &amp; quarter circle), <b>Polygons</b>
(triangle, right triangle, diamond, parallelogram, trapezoid,
pentagon…octagon) and <b>Stars &amp; symbols</b> (5/6-point star, cross,
chevron, block arrow, lightning bolt, house). Click the small arrow to
pick a shape — the button then remembers it — and drag on the canvas to
draw.</p>
<p>The <b>Dimension</b> tool (M) drags out a measured line with
arrowheads at both ends and a label showing the distance in
<b>millimetres</b> (using the drawing's DPI). It is a <b>dropdown</b> in
the left toolbar: choose an <b>orientation</b> — <i>Aligned</i> (free
angle), <i>Horizontal</i> (Δx only) or <i>Vertical</i> (Δy only) — and a
default <b>end-cap</b> style for new rulers. The label updates live as
you drag or move its endpoints, so it doubles as a ruler, and it saves
like any other line. Its <b>style</b> is editable in the properties
dialog (right-click ▸ <i>Edit properties…</i>): end caps
(<b>arrows, ticks, dots or none</b>), optional <b>extension lines</b>,
a <b>dashed</b> line, and the label's <b>unit</b> (mm/cm/in),
<b>decimals</b> and an optional <b>prefix/suffix</b> (e.g. Ø, ±).</p>

<h2>3 · Colours, width and fill</h2>
<p>On the top toolbar: click the <b>stroke</b> swatch (outline colour) or
the <b>fill</b> swatch to choose colours, toggle <b>Fill new shapes</b>
to give new shapes a fill, and pick the <b>line width</b> from the
dropdown — it shows each width as a line, thin to thick, in the current
stroke colour. These apply to the next thing you draw; to recolour an
existing item use its properties (below).</p>

<h2>4 · Selecting, moving, resizing, rotating</h2>
<ul>
  <li><b>Select</b> with the pointer: click an item, or drag a rubber-band
      box around several.</li>
  <li><b>Move</b>: drag the item.</li>
  <li><b>Resize</b>: blue handles appear on a selected item — drag a
      line's endpoints, a polygon's vertices, or a box's corners. A
      <b>group</b> shows eight handles: corners resize both ways, while
      the <b>side-middle</b> handles stretch it in X only or Y only.</li>
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
<p>Paste a screenshot or copied image with <b>Ctrl+V</b>, or <b>drag and
drop</b> an image file (PNG, JPEG, BMP, GIF, WebP, TIFF — any format Qt
can read) onto the canvas; it drops in as a movable picture at the drop
point (drop several to cascade them). Dropping a <b>.svg</b> or
<b>.kpaint</b> file opens it as a document. To <b>crop</b> an image,
right-click → <i>Crop image</i>, drag the frame handles, then
<b>double-click</b> (or press <b>Enter</b>) to apply — <b>Esc</b>
cancels.</p>

<h2>9 · Grid &amp; snap</h2>
<p>The <b>Grid (mm)</b> box sets the physical distance between grid lines
in millimetres (using the drawing's DPI) — a smaller value gives a finer
grid. Toggle the grid, snapping and <b>Infinite paper</b> from the
toolbar or the View menu. Infinite paper extends the grid across the
whole view with no fixed page edge (the page still bounds what you
export). Snapping keeps shapes aligned as you draw and move them (the
pencil stays freehand).</p>

<h2>10 · Object library</h2>
<p>Reuse a drawing across files. Select one or more items and choose
<b>Save selection as object…</b> (in the <b>Objects</b> dropdown at the
bottom of the left toolbar, or <b>Edit ▸ Save Selection as Object…</b>),
then give it a name — for example <i>wall</i>. It is written as a
standalone <b>SVG</b> file in a per-user objects folder. The Objects
dropdown then lists every saved object <b>by its name</b>; pick one to
drop a fresh, fully editable copy into the middle of the view.
<b>Open objects folder</b> reveals the files on disk.</p>

<h2>11 · Drawing size &amp; publication figures</h2>
<p>New documents open at the <b>ACS single-column</b> figure size
(3.25 in ≈ 82.6 mm) at 300 dpi. <b>File ▸ Drawing Size</b> sets the
canvas in <b>pixels, inches or millimetres</b> at a chosen <b>DPI</b>,
with column-width presets (in mm) for many journals — <b>ACS, Nature,
Science, Cell, RSC, Elsevier, IEEE, Wiley and PNAS</b> — plus A4, US
Letter and slides. Or enter a custom size, or <b>Fit to drawing</b> to
shrink the canvas around your artwork. Exports then carry the true
physical size (PNG embeds the DPI, PDF pages are the figure's inch size,
SVG sets its width in inches).</p>

<h2>12 · Undo / redo</h2>
<p><b>Ctrl+Z</b> undoes and <b>Ctrl+Y</b> redoes <i>everything</i> —
drawing, moving, resizing, rotating, properties, grouping, cropping,
fills and canvas resizes.</p>

<h2>13 · Saving, opening &amp; exporting</h2>
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

<h2>14 · View &amp; themes</h2>
<p>Zoom with <b>Ctrl + mouse wheel</b>, the <b>View ▸ Zoom</b> menu, or
the zoom controls at the <b>bottom-right of the status bar</b> — a slider
with −/+ buttons and a percentage you can click to snap back to 100%
(also <b>Ctrl+0</b>). Pick a colour theme under <b>View ▸ Theme</b>.</p>

<h2>15 · AI assistant</h2>
<p>Open <b>View ▸ AI Assistant</b> for a chat panel that can draw for
you. Choose a provider — <b>Claude, ChatGPT, Mistral, Ollama</b> or a
<b>Local</b> endpoint — enter its API key (Ollama/Local need only a base
URL), and press <b>Refresh</b> to list that provider's models. Then ask
in plain language, e.g. <i>“draw a blue flowchart box labelled Start with
an arrow down to a circle”</i>. The shapes it returns are added to the
canvas as real, editable items, so you can move, restyle and undo them
like anything else. While it works, an <i>“Assistant is thinking…”</i>
line shows and the send button becomes a <b>Stop</b> button. The chat is
remembered between sessions; the clear icon wipes it. Keys are stored
locally on your machine.</p>

<h2>16 · Examples</h2>
<p>The <b>Examples</b> menu loads ready-made, fully labelled instrument
schematics onto an A4 page — each with the instrument cross-section, a
realistic data plot and a caption. They are grouped by category:
<b>Spectroscopy</b> (XPS, UPS, AES, FTIR, Raman, UV-Vis, XRF, NMR),
<b>Mass spectrometry</b> (SIMS, ICP-MS, GC-MS), <b>Diffraction</b> (XRD,
LEED), <b>Microscopy</b> (TEM, SEM, AFM, STM), <b>Thermal &amp;
sorption</b> (TGA, DSC, BET) and <b>Chromatography</b> (HPLC). Every
element is a normal editable item, so a schematic is a starting point you
can restyle, relabel and export — or ask the AI assistant to extend.
Loading an example replaces the current drawing (you are asked first if
it has unsaved changes).</p>

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
