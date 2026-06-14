"""Drawing toolkit for the built-in example schematics.

A small set of spec-building helpers (the same shape-spec format the AI
assistant consumes via `ai_assistant.apply_specs`) that give every
example a consistent, polished look on an A4 page: a coloured header
band, beam ray-paths, lenses, leader-line callouts, framed data plots
with ticks and peak labels, micrograph panels with scale bars, legends
and a wrapped footer caption.

Builders live in `example_sketches.py`; the menu/registry is assembled
in `examples.py`.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

#: A4 portrait at 150 dpi.
PAGE_W, PAGE_H, PAGE_DPI = 1240, 1754, 150

# ---- palette --------------------------------------------------------
INK = "#1f2933"
MUTE = "#6b7a88"
FAINT = "#aab6c0"
PAPER = "#ffffff"

BEAM = "#d24b3e"        # x-rays / primary beam / excitation
SIGNAL = "#1f9d57"      # emitted signal / electrons / detected path
OPTIC = "#2f6fb0"       # lenses / optics / fields
DETC = "#7a45b0"        # detectors / electronics
SAMP = "#e0a52e"        # sample / specimen
COOL = "#3aa0c0"        # gas / cryogen / fluid

#: Category accent colours (header band + rule).
CATEGORY_COLOR = {
    "Spectroscopy": "#1f6fb2",
    "Mass spectrometry": "#c0392b",
    "Diffraction": "#138d8d",
    "Microscopy": "#7a3fb0",
    "Thermal & sorption": "#d98324",
    "Electrochemistry": "#2e8b57",
    "Chromatography": "#8a6d3b",
}

# light tints for housings, keyed loosely by role
TINT_BEAM = "#fbe6e2"
TINT_OPTIC = "#e4eefa"
TINT_SIGNAL = "#e2f5ea"
TINT_DET = "#efe6f8"
TINT_SAMP = "#fbeecb"
TINT_COOL = "#e2f1f7"
TINT_BODY = "#f3f6f9"


# ---- primitives -----------------------------------------------------
def _t(x, y, text, size=20, color=INK, bold=False):
    d = {"shape": "text", "x": x, "y": y, "text": text, "size": size,
         "color": color}
    if bold:
        d["bold"] = True
    return d


def _tc(cx, y, text, size=18, color=INK):
    """Text roughly centred on cx (Segoe UI ~0.52*size per char)."""
    return _t(cx - 0.26 * size * len(text), y, text, size, color)


def _box(x, y, w, h, label="", fill=None, stroke=INK, width=2, shape="rect"):
    d = {"shape": shape, "x": x, "y": y, "w": w, "h": h,
         "stroke": stroke, "width": width}
    if fill:
        d["fill"] = fill
    if label:
        d["label"] = label
    return d


def _round(x, y, w, h, label="", fill=None, stroke=INK, width=2):
    return _box(x, y, w, h, label, fill, stroke, width, shape="rounded_rect")


def _circle(x, y, d, label="", fill=None, stroke=INK, width=2):
    return _box(x, y, d, d, label, fill, stroke, width, shape="circle")


def _ellipse(x, y, w, h, label="", fill=None, stroke=INK, width=2):
    return _box(x, y, w, h, label, fill, stroke, width, shape="ellipse")


def _poly(kind, x, y, w, h, label="", fill=None, stroke=INK, width=2,
          rotation=0):
    d = _box(x, y, w, h, label, fill, stroke, width, shape=kind)
    if rotation:
        d["rotation"] = rotation
    return d


def _arrow(x1, y1, x2, y2, color=BEAM, width=4):
    return {"shape": "arrow", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": color, "width": width}


def _line(x1, y1, x2, y2, color=FAINT, width=2):
    return {"shape": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": color, "width": width}


# ---- composite helpers ---------------------------------------------
def _wrap(text, width):
    """Greedy word-wrap into lines of at most *width* chars."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _callout(comp_x, comp_y, text, side="right", size=17, color=INK,
             length=70):
    """A leader line from a component to a label off to one side."""
    if side == "right":
        lx = comp_x + length
        return [_line(comp_x, comp_y, lx, comp_y, FAINT, 1),
                _circle(comp_x - 3, comp_y - 3, 6, fill=color, stroke=color),
                _t(lx + 8, comp_y - size * 0.7, text, size, color)]
    lx = comp_x - length
    return [_line(lx, comp_y, comp_x, comp_y, FAINT, 1),
            _circle(comp_x - 3, comp_y - 3, 6, fill=color, stroke=color),
            _t(lx - 8 - 0.52 * size * len(text), comp_y - size * 0.7,
               text, size, color)]


def _lens(cx, cy, w, color=OPTIC, fill=TINT_OPTIC, h=26):
    """An electromagnetic / optical lens straddling a vertical beam."""
    return _ellipse(cx - w / 2, cy - h / 2, w, h, fill=fill, stroke=color,
                    width=3)


def _aperture(cx, cy, half_gap=10, arm=34, color=INK):
    """A pair of bars with a central gap (an aperture / slit)."""
    return [_box(cx - half_gap - arm, cy - 4, arm, 8, fill=color,
                 stroke=color, width=0),
            _box(cx + half_gap, cy - 4, arm, 8, fill=color, stroke=color,
                 width=0)]


def _beam(cx, pts, color=SIGNAL, width=2):
    """Two outline rays through (y, half-width) control points — a
    converging/diverging beam envelope down a column."""
    segs = []
    for (y0, h0), (y1, h1) in zip(pts, pts[1:]):
        segs.append(_line(cx - h0, y0, cx - h1, y1, color, width))
        segs.append(_line(cx + h0, y0, cx + h1, y1, color, width))
    return segs


# ---- panels ---------------------------------------------------------
def _plot(x, y, w, h, xlabel, ylabel, curve, peaks=None, color=DETC,
          fill_to_axes=True):
    """A framed plot: border, light gridlines, ticked axes, a trace and
    optional labelled peaks. *curve* is a list of (x_frac, y_frac) with
    y measured up from the bottom axis (0..1)."""
    specs = [_box(x, y, w, h, fill=PAPER, stroke=INK, width=2)]
    for i in range(1, 4):                       # horizontal gridlines
        gy = y + h * i / 4
        specs.append(_line(x + 1, gy, x + w - 1, gy, "#eef2f5", 1))
    for i in range(1, 6):                        # vertical gridlines
        gx = x + w * i / 6
        specs.append(_line(gx, y + 1, gx, y + h - 1, "#f1f4f7", 1))
    specs.append(_line(x, y + h, x + w, y + h, INK, 2))      # x axis
    specs.append(_line(x, y, x, y + h, INK, 2))              # y axis
    for i in range(7):                           # x ticks
        tx = x + w * i / 6
        specs.append(_line(tx, y + h, tx, y + h + 6, INK, 1))
    for i in range(5):                           # y ticks
        ty = y + h * i / 4
        specs.append(_line(x - 6, ty, x, ty, INK, 1))
    for a, b in zip(curve, curve[1:]):           # trace
        specs.append(_line(x + a[0] * w, y + h - a[1] * h,
                           x + b[0] * w, y + h - b[1] * h, color, 3))
    for px, label in (peaks or []):              # peak labels
        lx = x + px * w
        specs.append(_line(lx, y + 8, lx, y + 22, MUTE, 1))
        specs.append(_tc(lx, y + 24, label, 13, MUTE))
    specs.append(_tc(x + w / 2, y + h + 16, xlabel, 15, MUTE))
    specs.append(_t(x + 6, y - 24, ylabel, 15, MUTE))
    return specs


def _micrograph(x, y, w, h, blobs, title="", scale_label="", dark="#0d1014"):
    """A dark image panel with bright blobs, a scale bar and a title."""
    specs = [_box(x, y, w, h, fill=dark, stroke=INK, width=2)]
    for bx, by, bd in blobs:
        specs.append(_circle(x + bx, y + by, bd, fill="#dce8fb",
                             stroke="#c4d6f3", width=1))
    if scale_label:
        specs.append(_box(x + 24, y + h - 28, 90, 7, fill="#ffffff",
                          stroke="#ffffff", width=0))
        specs.append(_t(x + 24, y + h - 24, scale_label, 13, "#e8eef5"))
    if title:
        specs.append(_tc(x + w / 2, y + h + 10, title, 15, MUTE))
    return specs


def _legend(x, y, items, title=""):
    """A small key: coloured swatch + label per row."""
    specs = []
    yy = y
    if title:
        specs.append(_t(x, yy, title, 15, MUTE))
        yy += 26
    for color, label in items:
        specs.append(_box(x, yy, 22, 14, fill=color, stroke=color, width=0))
        specs.append(_t(x + 32, yy - 3, label, 15, INK))
        yy += 26
    return specs


def _stage(cx, cy, w=150, label="sample"):
    """A sample sitting on a small stage/holder."""
    return [_box(cx - w / 2, cy, w, 16, fill="#cdd6de", stroke=MUTE, width=1),
            _box(cx - w / 4, cy - 22, w / 2, 24, label, fill=SAMP,
                 stroke="#9a7b1f", width=2)]


# ---- page frame -----------------------------------------------------
def _page(title, subtitle, accent, body, caption=""):
    specs = [
        _box(36, 36, PAGE_W - 72, PAGE_H - 72, stroke="#d7dee5", width=2),
        _box(36, 36, 14, PAGE_H - 72, fill=accent, stroke=accent, width=0),
        _t(74, 70, title, 34, INK),
        _t(76, 132, subtitle, 20, MUTE),
        _line(74, 176, PAGE_W - 60, 176, accent, 3),
    ]
    specs += body
    if caption:
        lines = _wrap(caption, 72)
        cy = PAGE_H - 66 - 24 * len(lines)
        for i, ln in enumerate(lines):
            specs.append(_t(76, cy + 24 * i, ln, 16, MUTE))
    return specs
