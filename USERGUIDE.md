# KhervePaint — User Guide

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
| P | Pencil — freehand vector stroke (paints onto an image's pixels when started over one) |
| X | Eraser — rub out the raster layer (to white); over an inserted image, erases its pixels to transparent |
| K | Colour picker — sample a colour into the stroke (Shift+click: into the fill) |
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

The **Measure** menu gathers the mm measuring tools. **Protractor
(angle)** measures an angle in three clicks — the vertex, then each arm
end — and drops the two arms, an arc and a degree label as an editable
group (Esc cancels mid-measurement). **Scale bar…**
drops a labelled bar (a filled bar + end ticks + caption) whose length
is a real distance you choose — pick a value and unit (nm/µm/mm/cm) and
it's sized from the drawing's DPI; it's an ordinary group you can move,
recolour or edit. **Show rulers (mm)** puts graduated rulers along the
top and left edges that track the zoom and scroll, with a marker
following the cursor. The status bar also shows the **live size** (width
× height, or length for a line, in mm) of whatever you're drawing,
resizing or have selected.

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

**Gradient fills.** Switch the toolbar's fill-style selector to
**Fill: Linear** or **Fill: Radial** and new shapes are filled with a
gradient running from the **fill colour** to the **end colour** swatch
beside it (linear gradients run top-to-bottom by default). **Fill: Sun**
gives the shape a sun-lit look: an off-centre highlight of the end
colour (usually white) towards the top-left, fading into the fill
colour — a circle reads as a lit sphere. To restyle
an existing shape, right-click → *Edit properties…* → Fill and choose
the style, both colours and — for linear — the **angle** (0° =
left→right, 90° = top→bottom). Gradients survive saving (they become
standard SVG gradients, readable by any SVG tool).

The **colour picker** (K) samples the pixel under the cursor — from
anything on the canvas, including an opened or pasted image — into the
**stroke** colour; **Shift+click** samples into the **fill** colour
instead. The last pick is shown in the status bar.

## 4. Selecting, moving, resizing, rotating

- **Select** with the pointer: click an item, or drag a rubber-band box
  around several. **Shift+click** (or Ctrl+click) adds an item to the
  selection; Shift/Ctrl+click a selected item to drop it out again.
  An **unfilled** shape is selected by clicking its **outline** (like in
  other vector editors) — its empty interior lets clicks through to
  whatever is visible behind it, such as a bucket fill. Filled or
  labelled shapes are clickable anywhere inside.
- **Move**: drag the item.
- **Resize**: blue handles appear on a selected item — drag a line's
  endpoints, a polygon's vertices, or a box's corners. A **group** shows
  eight handles: corners resize both ways, while the **side-middle**
  handles stretch it in **X only** or **Y only**. Resizing **snaps to the
  grid** while snapping is on (toggle it in the toolbar / View menu).
- **Bend a line or arrow**: a selected line/arrow shows a **round handle
  at its midpoint** — drag it off the line to curve the line through the
  cursor (an arrow's head follows the curve). Drag the handle back onto
  the straight line to straighten it again. Curves save as standard SVG
  paths.
- **Rotate**: **double-click** the item and drag the green knob; it turns
  about its own centre.

## 5. Right-click: properties & more

Right-click any item for its menu: **Edit properties…**, Duplicate,
Delete, Flip, Bring to front / Send to back, Group / Ungroup, Explode,
and (for images) Crop and Remove background.

**Right-click empty canvas** for a quick menu of every drawing **tool**
and every symbol-**library** palette — picking a library element drops
it right where you clicked.

The **properties dialog** edits everything about an item — position,
rotation, opacity, stroke and fill, the exact geometry, and for text the
content and font. Shapes can also carry a **text label** drawn centred
inside them (set it in the Label section). Use **Apply** to preview
changes live on the canvas without closing the dialog.

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
walled off by shape outlines. By default the fill becomes an **editable
vector path** behind the shapes — a normal object you can click (its
area is clickable even under the unfilled shapes that bound it), move,
restyle and delete. Switch the toolbar selector to **Bucket: Raster**
to paint the fill permanently into the raster layer instead (raster
paint cannot be selected or moved afterwards — undo or the eraser are
the only ways back).

## 8. Images

Paste a screenshot or copied image with **Ctrl+V**, or **drag and drop**
an image file (PNG, JPEG, BMP, GIF, WebP, TIFF — any format Qt can read)
straight onto the canvas — it drops in as a movable picture at the drop
point (drop several at once to cascade them). Dropping a **.svg** or
**.kpaint** file instead opens it as a document. To **crop** an image,
right-click → *Crop image*, drag the frame handles, then **double-click**
(or press **Enter**) to apply — **Esc** cancels.

**Remove background** (right-click an image) makes the image's
background **transparent**: the most common colour along the image edges
is flooded inward and cleared, so whatever is behind the image shows
through. Regions of the same colour *inside* the subject are kept — only
background connected to the edges is removed. Fully undoable, and the
transparency is preserved when you save.

## 9. Grid & snap

The **Grid (mm)** box sets the physical distance between grid lines in
millimetres (using the drawing's DPI) — a smaller value gives a finer
grid. Toggle the grid, snapping and **Infinite paper** from the toolbar
or the View menu. Infinite paper (**on by default**) extends the grid and
a white background across the whole view with no fixed page edge, so you
can draw and scroll freely (the page still bounds what you export).
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

**Organise into folders.** Save into a sub-folder by typing a path like
*Walls/brick*, or use **Template Explorer…** (in the Objects dropdown)
to create folders and rename, move, delete or insert objects. The
Objects dropdown mirrors your folders as nested sub-menus.

All the symbol palettes below — and the Objects library — are also
reachable from the **Library** menu in the menu bar, mirroring the
left-toolbar dropdowns.

## 10a. Chemistry tools

The **Chemistry** dropdown (left toolbar) draws chemical structures as
ordinary editable shapes:

- **Bonds** — drag to draw a **single**, **double** or **triple** bond,
  a solid **wedge** (coming forward), a **hash** bond (going back) or a
  dashed **hydrogen bond** (the dotted connectors between atoms).
- **Chain** — click point-to-point to draw connected single bonds (for
  zig-zag skeletons); click the last point again, right-click, or press
  **Esc** to finish.

Every bond you draw snaps to a **uniform length** and to **30° angle
steps**, so structures stay tidy — you just click the direction.
- **Rings** — click to drop a **benzene** ring (hexagon with the
  aromatic inner circle), **cyclohexane** or **cyclopentane**.
- **Atom / group label** — pick a symbol (C, H, O, N, P, OH, CH₃…) then
  click to place it; it **snaps onto a nearby bond end**, so building a
  **C=O** is just *draw a double bond, then drop an O on its tip* — and
  any element drops cleanly at a bond terminus.

Everything is a normal item — restyle, move, group and save like any
other shape.

## 10b. Room layout (floor plans)

Start a plan with **Room** (top of the Room layout dropdown): drag out
the room and it's drawn with thin **solid walls** and an empty square at
each corner (standard plan style). Then drop in the rest. The **Room layout** dropdown drops ready-made **top-view**
plan symbols where you click. They're scaled so a **whole room fits the
page** — the page width represents about 4.8 m, so a chair is roughly
a tenth of it — keeping all the furniture in proportion:

The symbols are drawn as detailed plan-view blocks (the kind you see on a
professional furniture-symbol sheet): beds with pillows and a turned-down
duvet, U-shaped chairs and sofas, a round dining set, a lamp-topped
nightstand, a wardrobe with clothes on the rail, double-bowl sinks, a
four-burner hob, and so on.

- **Walls & openings** — wall, door (with swing), double door, window,
  opening, stairs.
- **Bedroom** — single/double bed, wardrobe, nightstand, chest of
  drawers, desk.
- **Living & dining** — dining table, round table (with chairs), chair,
  sofa, armchair, coffee table, TV unit, bookshelf.
- **Kitchen** — counter, sink, stove/hob, fridge, island, dishwasher.
- **Bathroom & utility** — toilet, basin, bathtub, shower, washing machine.
- **Decor** — plant, rug.

Each piece is a normal grouped item — move, rotate, resize and recolour
it, ungroup to tweak parts, or save your own arrangements as **objects**
(Section 10) for reuse. Snapping keeps everything aligned to the grid.

To build a **whole house plan**: drag a **Room** for each space (or one
big outline divided by walls), add **doors/windows/openings** along the
walls, then place **furniture** and **electrical** symbols. Group a
finished room and save it as an object to reuse across plans.

## 10c. Electrical symbols

The **Electrical** dropdown drops standard (IEC/ANSI-style) symbols:

- **Components** — resistor, capacitor (incl. polarised), inductor,
  diode, LED, NPN transistor, fuse, switch, lamp.
- **Sources & ground** — battery, DC source, AC source, ground, junction.
- **Installation (plan)** — sockets, light/two-way switches, ceiling &
  wall lights, consumer unit, junction box, ceiling fan, smoke detector.

Two-terminal components have lead stubs so you can wire them together
with the line/chain tools; everything is grouped and editable.

## 10d. Science symbols

Four further dropdowns drop schematic symbols on click — grouped,
editable, and scaled so a whole layout fits the page:

- **Optics** — beam-path elements for Raman/FTIR/UV-Vis: laser, lamp,
  detector, photodiode, camera, flat/curved mirror, beam splitter, beam
  path, convex/concave lens, prism, grating, polarizer, aperture, filter,
  sample, monochromator; plus a **Lighting** group for illuminating
  objects — spotlight, floodlight, light cone, desk lamp, bulb, LED,
  ring light and a shine/glint.
- **Vacuum & pressure** — UHV / surface science (XPS/AES/SIMS), 44
  symbols in five groups:
  - *Chamber & sources* — chamber, hemispherical analyser,
    X-ray/ion/electron guns, manipulator.
  - *Pumps* — turbo, ion, scroll, rotary, cryo, diaphragm, Roots, getter
    (NEG), Ti sublimation.
  - *Gauges & pressure* — Bourdon dial, Pirani, Penning, Bayard-Alpert
    ion gauge, Baratron capacitance manometer, U-tube manometer, pressure
    transducer.
  - *Valves* — gate, angle, leak, butterfly, ball, needle, solenoid,
    manual, relief.
  - *Lines & fittings* — pipe, tee, elbow, reducer, flange, blank flange,
    bellows, viewport, LN2 cold trap, mass-flow controller, regulator,
    gas cylinder.
- **Lab glassware** — beaker, Erlenmeyer, round-bottom & volumetric
  flasks, test tube, graduated cylinder, funnel, separating funnel,
  condenser, Petri dish, watch glass, burette, pipette, dropper, Bunsen
  burner, hotplate, retort stand, tripod, gauze, gas cylinder, balance,
  wash bottle.
- **Flowchart** — process, decision, terminator, data, document,
  predefined process, preparation, manual input, database, stored data,
  connector, display, plus flow arrows/lines. Each node carries an
  editable text label.

## 10e. Diagram & more science symbols

Five further dropdowns cover general diagrams and more science:

- **Network / IT** — desktop, laptop, mobile, user, printer, server,
  database, storage, load balancer, router, switch, firewall, modem,
  Wi-Fi AP, cloud.
- **P&ID** — process-flow equipment: tank, drum, column, reactor, heat
  exchanger, hopper, pump, compressor, blower, valves (gate, globe, ball,
  check, control, 3-way), instrument bubbles, flow meter, gauge.
- **Arrows & callouts** — block arrows (4 directions + double),
  curved/bent/circular arrows, rectangular & rounded callouts, ribbon
  banner, starburst badge, and thin line **connectors** (curved, elbow,
  Z-bend, U-turn) that look like the straight arrow tool but bent.
- **Biology** — animal cell, bacterium, virus, chromosome, neuron,
  DNA/RNA, protein, antibody, Petri dish, well plate, microscope,
  Eppendorf tube, syringe, lab mouse.
- **Math** — 2D/3D axes, number line, grid graph, curve plot, vector,
  angle, right angle, and symbol glyphs (brace, Σ, ∫, π, ∞, Δ, θ).
- **Molecules** — 3D **ball-and-stick** models (next to the Chemistry
  dropdown): atoms are lit spheres in the standard element colours
  (H white, C dark grey, O red, N blue, S yellow, Cl green…) with single/
  double/triple bonds, laid out with correct linear / trigonal /
  tetrahedral geometry. Dozens of ready-made molecules by category —
  simple molecules, **alcohols & ethers**, **acids & carbonyls**,
  **nitrogen compounds** (amines, urea, glycine…), **hydrocarbons**
  (methane→hexane, alkenes, alkynes), **aromatics** (benzene, toluene,
  phenol), **halogenated** (chloroform, CCl₄…), **polymers**
  (polyethylene, PVC, PTFE, polystyrene, **PET**) — and **crystal unit
  cells**: simple cubic, BCC, FCC, HCP, diamond, NaCl, CsCl,
  **perovskite** (ABX₃ octahedron), **zinc blende** and **fluorite**,
  drawn as open **wireframe unit cells** (thick cube edges plus dashed
  diagonals through the centring atoms). Each drops as an editable group.
  Atoms that are the **same element but sit on a hidden lattice site** — a
  BCC body-centre, the FCC/diamond face-centres, the diamond interior — are
  **colour-coded** so they stand out instead of vanishing against identical
  corners.

  A **Lattice systems** category adds the non-cubic crystal systems as
  wireframe unit cells built from their real lattice parameters
  (a, b, c, α, β, γ): **tetragonal**, **orthorhombic**, **hexagonal**
  (γ = 120°), **rhombohedral** (trigonal), **monoclinic** and
  **triclinic**. These stack too — the supercell tiles along the cell's
  own **lattice vectors**, so a hexagonal or monoclinic supercell grows
  skewed, with the cells meeting face-to-face in the crystallographically
  correct orientations rather than on a square grid.

  **Double-click** a placed molecule or crystal to **rotate it in 3D right
  on the canvas** — grab and drag to spin it; press **Esc** (or click off
  it) to finish. The whole spin is a single undo step, and the orientation
  is saved with the drawing.

  **Stack unit cells** — right-click a crystal ▸ **Stack unit cells…** to
  tile the unit cell into an **_a_×_b_×_c_ supercell**. Pick how many times
  to repeat it along each axis (1–6); shared corner and face atoms are
  merged so the lattice stays clean, and **1×1×1** restores the single
  cell. The stacked model is still one rotatable, editable group, and the
  cell counts are saved with the drawing.

  For more control, right-click ▸ **Molecule builder…** opens a window
  with a **view toolbar** (Front / Back / Left / Right / Top / Bottom /
  Isometric — each a little cube with the viewed face shaded), a
  **bond-length** slider, and an **atom palette**:

  - **Click a sphere** to select it — the status line shows how many bonds
    that atom still has free (the builder knows each element's valence:
    carbon 4, nitrogen 3, oxygen 2, hydrogen and the halogens 1…).
  - **Click an element** (H, C, N, O, F, P, S, Cl, Br) to bond a new atom
    onto the selected one, at the chosen **bond order** (single/double/
    triple). A full atom is left alone. Extending a chain grows a straight
    zig-zag, so a pentane chain stays straight instead of curling up.
  - **Drag a sphere** to move that atom and open up a bond angle by hand;
    **drag the background** to rotate the whole model.
  - **Delete atom** removes the selected sphere.
  - **Atom colour** — select a sphere and click **Colour…** to give it any
    colour you like. On a molecule the colour sticks to that one atom; on
    a crystal it recolours **every atom of that element on that lattice
    site** (so you can tint just the body-centres, say). **Reset colours**
    restores the standard CPK / site colours. Custom colours are saved
    with the drawing.

  Bonds are drawn longer by default so the sticks are clear; the slider
  spreads the atoms further.

  **Colour legend** — right-click a placed model ▸ **Add colour legend**
  drops a key beside it: one lit sphere per colour with its element name
  (and lattice site, e.g. "Fe — Iron (body centre)"). The legend is an
  ordinary editable group — double-click a label to reword it, move or
  restyle it like anything else.

  **Representations.** A molecule can be drawn four ways (as in a textbook
  figure): pick from right-click ▸ **Show as**, or the **Insert as** combo
  in the builder — **3D ball-and-stick**, **Structural formula** (element
  letters joined by bond lines), **Lewis structure** (adds lone-pair
  dots), or the **Condensed formula** (e.g. C₂H₆O). Each is a normal
  editable drawing; the choice is saved with the file.

  The **AI Chat** can build these too — ask it for a molecule (by name, or
  describe one) or a crystal, and it places a **real 3D model** you can
  rotate (double-click), edit in the builder, and switch representations
  on — the same as a library model. You only need to name or describe the
  molecule; the hydrogens and 3D geometry are worked out for you.

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

- **Save** writes a standard, **editable SVG** — the native format, fully
  SVG-compatible so it opens in any SVG viewer. Re-opening it brings every
  shape back editable; an imported external SVG is even broken into
  editable items you can ungroup.
- **Open** reads `.svg` or a `.png` image (older `.kpaint`
  files still open via *All files*). Recent files are under **File ▸ Open
  Recent**.
- **Export** (Ctrl+E) writes a flattened **PNG** or single-page **PDF**
  at the drawing's physical size.

## 14. View & themes

Zoom with **Ctrl + mouse wheel**, the **View ▸ Zoom** menu, or the zoom
controls at the **bottom-right of the status bar** — a slider with −/+
buttons and a percentage you can click to snap back to 100% (also
**Ctrl+0**). Pick a colour theme under **View ▸ Theme**.

## 15. AI assistant

Open the chat panel with the **AI Assistant** button on the top toolbar
(or **View ▸ AI Chat**). Use the **arrow on the panel's left edge** to
**collapse it to a thin strip** and click it again to expand — or the
toolbar button to hide/show it entirely.
Choose a provider — **Claude, ChatGPT, Mistral, Ollama** or a **Local**
endpoint — enter its API key (Ollama/Local need only a base URL), and
press **Refresh** to list that provider's models. Then ask in plain
language, e.g. *"draw a blue flowchart box labelled Start with an arrow
down to a circle"*. The shapes it returns become real, editable items on
the canvas, so you can move, restyle and undo them. API keys are stored
locally on your machine.

You can also **paste a screenshot** into the chat box (**Ctrl+V**) to
send it with your message — handy for *"recreate this diagram"*. The
image goes to the model with your next prompt (use a vision-capable model
such as Claude or GPT-4o); click **✕** to drop the attachment.

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

KhervePaint · GPL-3.0 · <https://github.com/gkerherve/KhervePaint>
