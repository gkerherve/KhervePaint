# KherveScribe — User Guide

A hybrid **raster + vector** drawing app for figures, diagrams and quick
image edits. This guide takes you from drawing your first shape to
exporting a publication-ready figure.

> The same guide is built into the app: **Help ▸ User Guide** (or press
> **F1**).

---

## 1. The canvas

A drawing has two layers in one canvas:

- **Raster layer** — a bitmap. *Open* a PNG to load it here, or fill into
  it with the bucket. It is stored inside your document.
- **Vector layer** — shapes, lines, arrows, text, freehand pencil strokes
  and pasted images drawn on top. These stay fully editable.

The white rectangle is the drawing area; the faint grid around it is a
guide and never appears in exports.

## 2. Tools

Pick a tool from the left column. The **pointer** selects; every other
tool draws.

| Key | Tool |
| --- | --- |
| V | Pointer — select, move, resize, rotate |
| P | Pencil — freehand vector stroke |
| B | Bucket — fill an enclosed region |
| L | Line |
| A | Arrow |
| M | Dimension — measure & label a distance |
| R | Rectangle |
| C | Circle |
| E | Ellipse |
| T | Text |

The **Dimension** tool (M) drags out a measured line with arrowheads at
both ends and a label showing the distance in **millimetres** (using the
drawing's DPI). It's a **dropdown** in the left toolbar: pick an
**orientation** — *Aligned* (free angle), *Horizontal* (measures Δx
only) or *Vertical* (measures Δy only) — and a default **end-cap** style
(arrows, ticks, dots or plain) for new rulers. The label updates live as
you drag and whenever you move its endpoints, so it doubles as a ruler.
It is a normal editable, saved item — change its colour/width like any
line. Its **style** is editable
in the properties dialog (right-click ▸ *Edit properties…*): swap the
end caps between **arrows, ticks, dots or none**, add perpendicular
**extension (witness) lines**, make the line **dashed**, and set the
label's **unit** (mm/cm/in), **decimals** and an optional
**prefix/suffix** (e.g. Ø, ±).

Related **shapes** are grouped under four dropdown buttons — click the
small arrow to pick one (the button then remembers it), then drag on the
canvas to draw:

- **Rectangles** — rectangle, rounded rectangle
- **Ellipses & arcs** — circle, ellipse, half circle, quarter circle
- **Polygons** — triangle, right triangle, diamond, parallelogram,
  trapezoid, pentagon, hexagon, heptagon, octagon
- **Stars & symbols** — 5- and 6-point stars, cross, chevron, block
  arrow, lightning bolt, house

## 3. Colours, width and fill

On the top toolbar: click the **stroke** swatch (outline colour) or the
**fill** swatch to choose colours, toggle **Fill new shapes** to give new
shapes a fill, and pick the **line width** from the dropdown — it shows
each width as a line, thin to thick, drawn in the current stroke colour.
These apply to the next thing you draw; to recolour an existing item, use
its properties (below).

## 4. Selecting, moving, resizing, rotating

- **Select** with the pointer: click an item, or drag a rubber-band box
  around several.
- **Move**: drag the item.
- **Resize**: blue handles appear on a selected item — drag a line's
  endpoints, a polygon's vertices, or a box's corners. A **group** shows
  eight handles: corners resize both ways, while the **side-middle**
  handles stretch it in **X only** or **Y only**. Resizing **snaps to the
  grid** while snapping is on (toggle it in the toolbar / View menu).
- **Rotate**: **double-click** the item and drag the green knob; it turns
  about its own centre.

## 5. Right-click: properties & more

Right-click any item for its menu: **Edit properties…**, Duplicate,
Delete, Flip, Bring to front / Send to back, Group / Ungroup, Explode,
and (for images) Crop.

The **properties dialog** edits everything about an item — position,
rotation, opacity, stroke and fill, the exact geometry, and for text the
content and font. Shapes can also carry a **text label** drawn centred
inside them (set it in the Label section).

## 6. Arrange: group, order, mirror, explode

- **Group** (Ctrl+G) several items so they move/resize/rotate/flip as
  one; **Ungroup** (Ctrl+Shift+G) to split them.
- **Flip** horizontally / vertically (Ctrl+Shift+H / Ctrl+Shift+J).
- **Explode** (Ctrl+Shift+E) breaks a shape's outline into its separate
  edges — delete or edit one side, then regroup the rest.
- **Order** an item with **Bring to Front / Bring Forward / Send
  Backward / Send to Back** — from the top toolbar icons, the right-click
  menu, or **Edit ▸ Arrange** (`Ctrl+]` / `Ctrl+[`, add **Shift** for
  front/back).

## 7. Bucket fill

Choose the bucket (B), set the fill colour, and click inside an area
walled off by shape outlines. The toolbar selector chooses whether the
fill is painted into the **raster** layer or becomes an **editable vector
path** behind the shapes.

## 8. Images

Paste a screenshot or copied image with **Ctrl+V**, or **drag and drop**
an image file (PNG, JPEG, BMP, GIF, WebP, TIFF — any format Qt can read)
straight onto the canvas — it drops in as a movable picture at the drop
point (drop several at once to cascade them). Dropping a **.svg** or
**.kscribe** file instead opens it as a document. To **crop** an image,
right-click → *Crop image*, drag the frame handles, then **double-click**
(or press **Enter**) to apply — **Esc** cancels.

## 9. Grid & snap

The **Grid (mm)** box sets the physical distance between grid lines in
millimetres (using the drawing's DPI) — a smaller value gives a finer
grid. Toggle the grid, snapping and **Infinite paper** from the toolbar
or the View menu. Infinite paper extends the grid across the whole view
with no fixed page edge (the page still bounds what you export).
Snapping keeps shapes aligned as you draw and move them (the pencil
stays freehand).

## 10. Object library

Reuse a drawing across files. Select one or more items and choose
**Save selection as object…** (in the **Objects** dropdown at the bottom
of the left toolbar, or **Edit ▸ Save Selection as Object…**), then give
it a name — for example *wall*. It is written as a standalone **SVG**
file in a per-user objects folder. The Objects dropdown then lists every
saved object **by its name**; pick one to drop a fresh, fully editable
copy into the middle of the view. **Open objects folder** reveals the
files on disk (delete or rename them there).

## 11. Drawing size & publication figures

New documents open at the **ACS single-column** figure size (3.25 in ≈
82.6 mm) at 300 dpi. **File ▸ Drawing Size** sets the canvas in
**pixels, inches or millimetres** at a chosen **DPI**, with column-width
presets (in mm) for many journals — **ACS, Nature, Science, Cell, RSC,
Elsevier, IEEE, Wiley and PNAS** — plus A4, US Letter and slides. Or
enter a custom size, or **Fit to drawing** to shrink the canvas around
your artwork. Exports then carry the true physical size (PNG embeds the
DPI, PDF pages are the figure's inch size, SVG sets its width in inches).

## 12. Undo / redo

**Ctrl+Z** undoes and **Ctrl+Y** redoes *everything* — drawing, moving,
resizing, rotating, properties, grouping, cropping, fills and canvas
resizes.

## 13. Saving, opening & exporting

- **Save** writes **editable SVG** by default (also offered: `.kscribe`,
  the lossless native format). Re-opening an SVG brings every shape back
  editable; an imported external SVG is even broken into editable items
  you can ungroup.
- **Open** reads `.svg`, `.kscribe` or a `.png` image. Recent files are
  under **File ▸ Open Recent**.
- **Export** (Ctrl+E) writes a flattened **PNG** or single-page **PDF**
  at the drawing's physical size.

## 14. View & themes

Zoom with **Ctrl + mouse wheel**, the **View ▸ Zoom** menu, or the zoom
controls at the **bottom-right of the status bar** — a slider with −/+
buttons and a percentage you can click to snap back to 100% (also
**Ctrl+0**). Pick a colour theme under **View ▸ Theme**.

## 15. AI assistant

Open **View ▸ AI Assistant** for a chat panel that can draw for you.
Choose a provider — **Claude, ChatGPT, Mistral, Ollama** or a **Local**
endpoint — enter its API key (Ollama/Local need only a base URL), and
press **Refresh** to list that provider's models. Then ask in plain
language, e.g. *"draw a blue flowchart box labelled Start with an arrow
down to a circle"*. The shapes it returns become real, editable items on
the canvas, so you can move, restyle and undo them. API keys are stored
locally on your machine.

## 16. Examples

The **Examples** menu loads ready-made, fully labelled instrument
schematics onto an A4 page — each with the instrument cross-section
(beam paths, lenses, chambers, detectors), a realistic data plot and a
short caption. They are grouped by category:

- **Spectroscopy** — XPS, UPS, AES, FTIR, Raman, UV-Vis, XRF, NMR
- **Mass spectrometry** — SIMS, ICP-MS, GC-MS
- **Diffraction** — XRD, LEED
- **Microscopy** — TEM, SEM, AFM, STM
- **Thermal & sorption** — TGA, DSC, BET
- **Chromatography** — HPLC

Each schematic is built from ordinary editable items, so you can restyle,
relabel, rearrange and export it like any drawing — or ask the AI
assistant to extend it. Loading an example replaces the current document
(you are asked first if it has unsaved changes).

## Keyboard shortcuts

**Tools:** V pointer · P pencil · B bucket · L line · A arrow · R rect ·
C circle · E ellipse · T text

**Edit & arrange:** Ctrl+Z/Y undo/redo · Ctrl+C/V/X copy/paste/cut ·
Ctrl+D duplicate · Ctrl+A select all · Delete · Ctrl+G / Ctrl+Shift+G
group/ungroup · Ctrl+Shift+E explode · Ctrl+Shift+H / Ctrl+Shift+J flip

**File:** Ctrl+N/O/S new/open/save · Ctrl+Shift+S save as ·
Ctrl+Shift+P drawing size · Ctrl+E export · Ctrl+Q quit

**View:** Ctrl+wheel zoom · Ctrl+0 reset zoom · Ctrl+' grid ·
Ctrl+Shift+' snap · F1 user guide

---

KherveScribe · GPL-3.0 · <https://github.com/gkerherve/KherveScribe>
