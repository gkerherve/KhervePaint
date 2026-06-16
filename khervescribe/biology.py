'''Biology / life-science figure symbols (cells, molecules, lab).

Each `build_<name>(w, h)` returns a list of shape-spec dicts (the AI/
example format) drawing a symbol inside the box (0,0)-(w,h). Same
`build_specs`/`size_mm`/`REFERENCE_MM` interface as floorplan/electrical.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
'''
import math

OUTLINE = "#333333"
CELL = "#eaf3ea"
NUCLEUS = "#cfe0d6"
NUCLEUS2 = "#bcd0c4"
MEMBRANE = "#bcd8c4"
MOL_BLUE = "#cfe0f5"
MOL_RED = "#f3cccc"
LAB = "#dfe7ee"
WHITE = "#ffffff"
W_OUT = 2
W_DET = 1.2


def _circle(cx, cy, r, stroke=OUTLINE, fill="none", width=W_OUT):
    return {"shape": "circle", "x": cx - r, "y": cy - r,
            "w": 2 * r, "h": 2 * r, "stroke": stroke,
            "fill": fill, "width": width}


def _ellipse(cx, cy, rx, ry, stroke=OUTLINE, fill="none", width=W_OUT,
             rotation=0.0):
    d = {"shape": "ellipse", "x": cx - rx, "y": cy - ry,
         "w": 2 * rx, "h": 2 * ry, "stroke": stroke,
         "fill": fill, "width": width}
    if rotation:
        d["rotation"] = rotation
    return d


def _line(x1, y1, x2, y2, stroke=OUTLINE, width=W_DET):
    return {"shape": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": stroke, "width": width}


def _wavy(x1, y1, x2, y2, amp, cycles, stroke=OUTLINE, width=W_DET,
          steps=24):
    """A sinusoidal polyline of short line segments between two points."""
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    pts = []
    for i in range(steps + 1):
        t = i / steps
        off = amp * math.sin(t * cycles * 2 * math.pi)
        bx = x1 + dx * t + px * off
        by = y1 + dy * t + py * off
        pts.append((bx, by))
    segs = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        segs.append(_line(a[0], a[1], b[0], b[1], stroke, width))
    return segs


# ---------------------------------------------------------------------------
# Cells & microbes
# ---------------------------------------------------------------------------
def build_cell(w, h):
    cx, cy = w * 0.5, h * 0.5
    r = min(w, h) * 0.46
    specs = [_circle(cx, cy, r, OUTLINE, CELL, W_OUT)]
    specs.append(_circle(cx, cy, r * 0.94, MEMBRANE, "none", W_DET))
    nr = r * 0.34
    specs.append(_circle(cx - r * 0.12, cy - r * 0.08, nr,
                         OUTLINE, NUCLEUS, W_OUT))
    specs.append(_circle(cx - r * 0.12, cy - r * 0.08, nr * 0.32,
                         OUTLINE, NUCLEUS2, W_DET))
    for ang, dist in ((0.6, 0.62), (2.1, 0.6), (-1.4, 0.6)):
        ox = cx + math.cos(ang) * r * dist
        oy = cy + math.sin(ang) * r * dist
        specs.append(_ellipse(ox, oy, r * 0.16, r * 0.08,
                              OUTLINE, MEMBRANE, W_DET,
                              rotation=math.degrees(ang)))
    return specs


def build_bacterium(w, h):
    cx, cy = w * 0.5, h * 0.5
    bw, bh = w * 0.5, h * 0.34
    x, y = cx - bw / 2, cy - bh / 2
    specs = [{"shape": "rounded_rect", "x": x, "y": y, "w": bw, "h": bh,
              "radius": bh / 2, "stroke": OUTLINE, "fill": CELL,
              "width": W_OUT}]
    for fx in (0.32, 0.5, 0.68):
        specs.append(_circle(x + bw * fx, cy, bh * 0.12,
                             OUTLINE, NUCLEUS2, W_DET))
    specs += _wavy(x, cy, x - w * 0.22, cy - h * 0.05,
                   h * 0.04, 2.5, OUTLINE, W_DET)
    specs += _wavy(x + bw, cy, x + bw + w * 0.22, cy + h * 0.05,
                   h * 0.04, 2.5, OUTLINE, W_DET)
    return specs


def build_virus(w, h):
    cx, cy = w * 0.5, h * 0.5
    r = min(w, h) * 0.32
    specs = [_circle(cx, cy, r, OUTLINE, MOL_RED, W_OUT)]
    specs.append(_circle(cx, cy, r * 0.5, MEMBRANE, "none", W_DET))
    n = 12
    spike = min(w, h) * 0.12
    knob = spike * 0.4
    for i in range(n):
        ang = i / n * 2 * math.pi
        x1 = cx + math.cos(ang) * r
        y1 = cy + math.sin(ang) * r
        x2 = cx + math.cos(ang) * (r + spike)
        y2 = cy + math.sin(ang) * (r + spike)
        specs.append(_line(x1, y1, x2, y2, OUTLINE, W_DET))
        specs.append(_circle(x2, y2, knob, OUTLINE, MOL_RED, W_DET))
    return specs


def build_chromosome(w, h):
    cx, cy = w * 0.5, h * 0.5
    bw, bh = w * 0.18, h * 0.62
    x, y = cx - bw / 2, cy - bh / 2
    specs = []
    for rot in (28.0, -28.0):
        specs.append({"shape": "rounded_rect", "x": x, "y": y,
                      "w": bw, "h": bh, "radius": bw / 2,
                      "stroke": OUTLINE, "fill": MOL_BLUE,
                      "width": W_OUT, "rotation": rot})
    specs.append(_circle(cx, cy, min(w, h) * 0.07, OUTLINE, WHITE, W_DET))
    return specs


def build_neuron(w, h):
    cx, cy = w * 0.42, h * 0.5
    r = min(w, h) * 0.16
    specs = [_circle(cx, cy, r, OUTLINE, CELL, W_OUT)]
    specs.append(_circle(cx, cy, r * 0.4, OUTLINE, NUCLEUS, W_DET))
    for ang in (math.pi * 0.65, math.pi * 0.9, math.pi * 1.15,
                math.pi * 1.4, math.pi * 0.4):
        x2 = cx + math.cos(ang) * r * 2.4
        y2 = cy + math.sin(ang) * r * 2.4
        specs.append(_line(cx + math.cos(ang) * r,
                           cy + math.sin(ang) * r, x2, y2,
                           OUTLINE, W_DET))
        bx = cx + math.cos(ang) * r * 3.0
        by = cy + math.sin(ang) * r * 3.0
        specs.append(_line(x2, y2, bx, by, OUTLINE, W_DET))
    ax = cx + r
    ex = w * 0.84
    specs.append(_line(ax, cy, ex, cy, OUTLINE, W_OUT))
    for dy in (-h * 0.12, 0.0, h * 0.12):
        specs.append(_line(ex, cy, w * 0.95, cy + dy, OUTLINE, W_DET))
    return specs


# ---------------------------------------------------------------------------
# Molecules
# ---------------------------------------------------------------------------
def build_dna(w, h):
    cx = w * 0.5
    amp = w * 0.22
    top, bot = h * 0.06, h * 0.94
    steps = 40
    cycles = 2.0
    specs = []
    strand_a = []
    strand_b = []
    for i in range(steps + 1):
        t = i / steps
        y = top + (bot - top) * t
        ph = t * cycles * 2 * math.pi
        xa = cx + amp * math.sin(ph)
        xb = cx + amp * math.sin(ph + math.pi)
        strand_a.append((xa, y))
        strand_b.append((xb, y))
    for i in range(0, steps + 1, 3):
        a, b = strand_a[i], strand_b[i]
        col = MOL_BLUE if (i // 3) % 2 == 0 else MOL_RED
        specs.append(_line(a[0], a[1], b[0], b[1], col, W_DET))
    for strand in (strand_a, strand_b):
        for i in range(len(strand) - 1):
            p, q = strand[i], strand[i + 1]
            specs.append(_line(p[0], p[1], q[0], q[1], OUTLINE, W_OUT))
    return specs


def build_rna(w, h):
    cx = w * 0.5
    amp = w * 0.2
    top, bot = h * 0.06, h * 0.94
    steps = 40
    cycles = 2.5
    specs = []
    strand = []
    for i in range(steps + 1):
        t = i / steps
        y = top + (bot - top) * t
        ph = t * cycles * 2 * math.pi
        x = cx + amp * math.sin(ph)
        strand.append((x, y))
    for i in range(2, steps, 4):
        p = strand[i]
        nxt = strand[i + 1]
        dx, dy = nxt[0] - p[0], nxt[1] - p[1]
        ln = math.hypot(dx, dy) or 1.0
        px, py = -dy / ln, dx / ln
        tl = w * 0.08
        col = MOL_BLUE if (i // 4) % 2 == 0 else MOL_RED
        specs.append(_line(p[0], p[1],
                           p[0] + px * tl, p[1] + py * tl, col, W_DET))
    for i in range(len(strand) - 1):
        p, q = strand[i], strand[i + 1]
        specs.append(_line(p[0], p[1], q[0], q[1], OUTLINE, W_OUT))
    return specs


def build_protein(w, h):
    cx, cy = w * 0.5, h * 0.5
    specs = []
    blobs = (
        (cx - w * 0.12, cy - h * 0.1, w * 0.24, h * 0.2, 20.0),
        (cx + w * 0.14, cy - h * 0.04, w * 0.2, h * 0.16, -25.0),
        (cx + w * 0.02, cy + h * 0.16, w * 0.22, h * 0.18, 10.0),
        (cx - w * 0.16, cy + h * 0.12, w * 0.16, h * 0.14, -10.0),
    )
    for bx, by, bwr, bhr, rot in blobs:
        specs.append(_ellipse(bx, by, bwr, bhr, OUTLINE, MOL_BLUE,
                              W_OUT, rotation=rot))
    specs += _wavy(cx - w * 0.18, cy + h * 0.02,
                   cx + w * 0.2, cy - h * 0.02,
                   h * 0.06, 2.0, OUTLINE, W_DET)
    return specs


def build_antibody(w, h):
    cx = w * 0.5
    hinge_y = h * 0.55
    arm_w = w * 0.1
    specs = []
    specs.append({"shape": "rounded_rect",
                  "x": cx - arm_w / 2, "y": hinge_y,
                  "w": arm_w, "h": h * 0.4,
                  "radius": arm_w / 2, "stroke": OUTLINE,
                  "fill": MOL_BLUE, "width": W_OUT})
    arm_h = h * 0.5
    for sgn, rot in ((-1, 35.0), (1, -35.0)):
        ax = cx + sgn * w * 0.13
        ay = hinge_y - arm_h * 0.42
        specs.append({"shape": "rounded_rect",
                      "x": ax - arm_w / 2, "y": ay - arm_h / 2,
                      "w": arm_w, "h": arm_h,
                      "radius": arm_w / 2, "stroke": OUTLINE,
                      "fill": MOL_BLUE, "width": W_OUT,
                      "rotation": rot})
    specs.append(_circle(cx, hinge_y, arm_w * 0.5, OUTLINE, WHITE, W_DET))
    return specs


# ---------------------------------------------------------------------------
# Lab
# ---------------------------------------------------------------------------
def build_petri_dish(w, h):
    cx, cy = w * 0.5, h * 0.5
    rx, ry = w * 0.46, h * 0.4
    specs = [_ellipse(cx, cy, rx, ry, OUTLINE, LAB, W_OUT)]
    specs.append(_ellipse(cx, cy, rx * 0.86, ry * 0.86,
                          MEMBRANE, "none", W_DET))
    spots = ((-0.3, -0.2, 0.07), (0.2, -0.25, 0.05), (0.35, 0.1, 0.06),
             (-0.1, 0.25, 0.08), (0.05, -0.05, 0.04), (-0.35, 0.15, 0.05))
    for fx, fy, fr in spots:
        specs.append(_circle(cx + rx * fx, cy + ry * fy,
                             min(w, h) * fr, OUTLINE, NUCLEUS2, W_DET))
    return specs


def build_well_plate(w, h):
    specs = [{"shape": "rounded_rect", "x": w * 0.04, "y": h * 0.1,
              "w": w * 0.92, "h": h * 0.8, "radius": min(w, h) * 0.05,
              "stroke": OUTLINE, "fill": LAB, "width": W_OUT}]
    cols, rows = 6, 4
    x0, y0 = w * 0.12, h * 0.22
    x1, y1 = w * 0.88, h * 0.78
    r = min((x1 - x0) / cols, (y1 - y0) / rows) * 0.32
    for c in range(cols):
        for rw in range(rows):
            cx = x0 + (x1 - x0) * (c + 0.5) / cols
            cy = y0 + (y1 - y0) * (rw + 0.5) / rows
            specs.append(_circle(cx, cy, r, OUTLINE, WHITE, W_DET))
    return specs


def build_microscope(w, h):
    specs = []
    specs.append({"shape": "rounded_rect", "x": w * 0.18, "y": h * 0.82,
                  "w": w * 0.6, "h": h * 0.12, "radius": min(w, h) * 0.03,
                  "stroke": OUTLINE, "fill": LAB, "width": W_OUT})
    specs.append({"shape": "rounded_rect", "x": w * 0.58, "y": h * 0.3,
                  "w": w * 0.1, "h": h * 0.54, "radius": min(w, h) * 0.03,
                  "stroke": OUTLINE, "fill": LAB, "width": W_OUT})
    specs.append({"shape": "rounded_rect", "x": w * 0.4, "y": h * 0.12,
                  "w": w * 0.16, "h": h * 0.4, "radius": min(w, h) * 0.03,
                  "stroke": OUTLINE, "fill": LAB, "width": W_OUT})
    specs.append({"shape": "rounded_rect", "x": w * 0.43, "y": h * 0.04,
                  "w": w * 0.1, "h": h * 0.1, "radius": min(w, h) * 0.02,
                  "stroke": OUTLINE, "fill": LAB, "width": W_DET})
    specs.append({"shape": "trapezoid", "x": w * 0.42, "y": h * 0.52,
                  "w": w * 0.12, "h": h * 0.08, "rotation": 180.0,
                  "stroke": OUTLINE, "fill": LAB, "width": W_DET})
    specs.append({"shape": "rect", "x": w * 0.28, "y": h * 0.62,
                  "w": w * 0.32, "h": h * 0.05, "stroke": OUTLINE,
                  "fill": LAB, "width": W_OUT})
    specs.append({"shape": "rect", "x": w * 0.34, "y": h * 0.6,
                  "w": w * 0.16, "h": h * 0.02, "stroke": OUTLINE,
                  "fill": MOL_BLUE, "width": W_DET})
    return specs


def build_eppendorf(w, h):
    cx = w * 0.5
    tw = w * 0.3
    x = cx - tw / 2
    specs = []
    specs.append({"shape": "rounded_rect", "x": x - tw * 0.05,
                  "y": h * 0.04, "w": tw * 1.1, "h": h * 0.12,
                  "radius": min(w, h) * 0.02, "stroke": OUTLINE,
                  "fill": LAB, "width": W_OUT})
    specs.append({"shape": "rect", "x": x + tw, "y": h * 0.07,
                  "w": tw * 0.12, "h": h * 0.06, "stroke": OUTLINE,
                  "fill": LAB, "width": W_DET})
    specs.append({"shape": "rect", "x": x, "y": h * 0.16,
                  "w": tw, "h": h * 0.46, "stroke": OUTLINE,
                  "fill": LAB, "width": W_OUT})
    specs.append({"shape": "triangle", "x": x, "y": h * 0.62,
                  "w": tw, "h": h * 0.3, "rotation": 180.0,
                  "stroke": OUTLINE, "fill": LAB, "width": W_OUT})
    specs.append(_line(x, h * 0.5, x + tw, h * 0.5, MOL_BLUE, W_DET))
    return specs


def build_syringe(w, h):
    cx = w * 0.5
    bw = w * 0.26
    x = cx - bw / 2
    specs = []
    specs.append(_line(cx, h * 0.02, cx, h * 0.2, OUTLINE, W_OUT))
    specs.append(_line(cx - bw * 0.5, h * 0.02, cx + bw * 0.5, h * 0.02,
                       OUTLINE, W_OUT))
    specs.append({"shape": "rect", "x": x, "y": h * 0.2,
                  "w": bw, "h": h * 0.5, "stroke": OUTLINE,
                  "fill": LAB, "width": W_OUT})
    for i in range(1, 5):
        gy = h * 0.2 + h * 0.5 * i / 5
        specs.append(_line(x, gy, x + bw * 0.4, gy, OUTLINE, W_DET))
    specs.append({"shape": "trapezoid", "x": cx - bw * 0.18, "y": h * 0.7,
                  "w": bw * 0.36, "h": h * 0.06, "rotation": 180.0,
                  "stroke": OUTLINE, "fill": LAB, "width": W_DET})
    specs.append(_line(cx, h * 0.76, cx, h * 0.98, OUTLINE, W_OUT))
    return specs


def build_mouse(w, h):
    cx, cy = w * 0.42, h * 0.5
    brx, bry = w * 0.3, h * 0.22
    specs = [_ellipse(cx, cy, brx, bry, OUTLINE, MOL_RED, W_OUT)]
    hx = cx - brx * 0.9
    specs.append(_ellipse(hx, cy, brx * 0.4, bry * 0.7,
                          OUTLINE, MOL_RED, W_OUT))
    specs.append(_circle(hx - brx * 0.1, cy - bry * 0.5,
                         min(w, h) * 0.06, OUTLINE, MOL_RED, W_DET))
    specs.append(_circle(hx - brx * 0.1, cy + bry * 0.5,
                         min(w, h) * 0.06, OUTLINE, MOL_RED, W_DET))
    specs.append(_circle(hx - brx * 0.25, cy - bry * 0.15,
                         min(w, h) * 0.02, OUTLINE, OUTLINE, W_DET))
    tx = cx + brx
    specs += _wavy(tx, cy, tx + w * 0.24, cy + h * 0.06,
                   h * 0.04, 1.5, OUTLINE, W_DET)
    return specs


# ---------------------------------------------------------------------------
REFERENCE_MM = 1000.0

SIZES = {
    "cell": (150.0, 150.0),
    "bacterium": (180.0, 100.0),
    "virus": (150.0, 150.0),
    "chromosome": (110.0, 160.0),
    "neuron": (200.0, 130.0),
    "dna": (110.0, 200.0),
    "rna": (100.0, 200.0),
    "protein": (150.0, 150.0),
    "antibody": (140.0, 160.0),
    "petri_dish": (170.0, 150.0),
    "well_plate": (200.0, 140.0),
    "microscope": (140.0, 180.0),
    "eppendorf": (100.0, 180.0),
    "syringe": (110.0, 200.0),
    "mouse": (190.0, 110.0),
}

LABELS = {
    "cell": "Animal cell",
    "bacterium": "Bacterium",
    "virus": "Virus",
    "chromosome": "Chromosome",
    "neuron": "Neuron",
    "dna": "DNA double helix",
    "rna": "RNA strand",
    "protein": "Protein",
    "antibody": "Antibody",
    "petri_dish": "Petri dish",
    "well_plate": "Well plate",
    "microscope": "Microscope",
    "eppendorf": "Eppendorf tube",
    "syringe": "Syringe",
    "mouse": "Lab mouse",
}

CATEGORIES = [
    ("Cells & microbes", ["cell", "bacterium", "virus", "chromosome",
                          "neuron"]),
    ("Molecules", ["dna", "rna", "protein", "antibody"]),
    ("Lab", ["petri_dish", "well_plate", "microscope", "eppendorf",
             "syringe", "mouse"]),
]

_BUILDERS = {name: globals()["build_" + name] for name in SIZES}


def build_specs(name, w, h):
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
