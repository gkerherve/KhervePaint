"""Top-view room-layout elements: walls, doors, furniture, fittings.

Each `build_<name>(w, h)` returns a list of shape-spec dicts (the same
format the AI assistant / examples use) drawing a clean plan-view symbol
inside the box (0,0)-(w,h). `SIZES` gives each element's real-world plan
size in mm; the scene builds native, editable items from the specs via
`ai_assistant._spec_to_item` (so no item classes here — no import cycle)
and places them, grouped, where you click. Driven by the left toolbar's
**Room layout** dropdown.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math


def _arc(cx, cy, r, a0_deg, a1_deg, width=1.5, n=20):
    """Quarter/any arc as a polyline of line specs (precise control over
    centre/radius/angles; angles in degrees, screen coords with y down)."""
    out = []
    prev = None
    for i in range(n + 1):
        a = math.radians(a0_deg + (a1_deg - a0_deg) * i / n)
        pt = (cx + r * math.cos(a), cy + r * math.sin(a))
        if prev is not None:
            out.append({"shape": "line", "x1": prev[0], "y1": prev[1],
                        "x2": pt[0], "y2": pt[1], "stroke": "#333333",
                        "width": width})
        prev = pt
    return out


# --------------------------------------------------------- walls & openings
def build_wall(w, h):
    return [{"shape": "rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
             "stroke": "#333333", "width": 2, "fill": "#444444"}]


def build_door(w, h):
    # Single door hinged top-left: open leaf points down, quarter-circle
    # swing of radius = opening width back to the far jamb.
    jamb = min(w, h) * 0.1
    specs = [
        {"shape": "rect", "x": 0.0, "y": 0.0, "w": jamb, "h": jamb,
         "stroke": "#333333", "width": 2, "fill": "#444444"},
        {"shape": "rect", "x": w - jamb, "y": 0.0, "w": jamb, "h": jamb,
         "stroke": "#333333", "width": 2, "fill": "#444444"},
        {"shape": "line", "x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": h,
         "stroke": "#333333", "width": 2},                      # open leaf
    ]
    specs += _arc(0.0, 0.0, w, 0.0, 90.0, width=1.5)            # swing arc
    return specs


def build_double_door(w, h):
    # Two leaves hinged at the outer top jambs; each quarter-circle swing
    # (radius = half the opening) meets the other in a cusp at the bottom
    # centre.  (SIZES keeps width = 2*height so the arcs reach the centre.)
    jamb = min(w, h) * 0.16
    leaf = h * 0.34
    specs = [
        {"shape": "line", "x1": 0.0, "y1": h, "x2": w, "y2": h,
         "stroke": "#333333", "width": 2},                      # threshold
        {"shape": "rect", "x": 0.0, "y": 0.0, "w": jamb, "h": jamb,
         "stroke": "#333333", "width": 2, "fill": "#444444"},
        {"shape": "rect", "x": w - jamb, "y": 0.0, "w": jamb, "h": jamb,
         "stroke": "#333333", "width": 2, "fill": "#444444"},
        {"shape": "line", "x1": 0.0, "y1": 0.0, "x2": 0.0, "y2": leaf,
         "stroke": "#333333", "width": 2},                      # left leaf
        {"shape": "line", "x1": w, "y1": 0.0, "x2": w, "y2": leaf,
         "stroke": "#333333", "width": 2},                      # right leaf
    ]
    specs += _arc(0.0, h, h, -90.0, 0.0, width=1.5)             # left swing
    specs += _arc(w, h, h, -90.0, -180.0, width=1.5)           # right swing
    return specs


def build_window(w, h):
    band = h * 0.30
    return [
        {"shape": "rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
         "stroke": "#333333", "width": 2, "fill": "#444444"},
        {"shape": "rect", "x": 0.0, "y": (h - band) * 0.5, "w": w, "h": band,
         "stroke": "#333333", "width": 1.5, "fill": "#cfe3f2"},
        {"shape": "line", "x1": 0.0, "y1": h * 0.5, "x2": w, "y2": h * 0.5,
         "stroke": "#333333", "width": 1.5},
    ]


def build_opening(w, h):
    stub = w * 0.28
    return [
        {"shape": "rect", "x": 0.0, "y": 0.0, "w": stub, "h": h,
         "stroke": "#333333", "width": 2, "fill": "#444444"},
        {"shape": "rect", "x": w - stub, "y": 0.0, "w": stub, "h": h,
         "stroke": "#333333", "width": 2, "fill": "#444444"},
    ]


def build_stairs(w, h):
    n = 9
    specs = [{"shape": "rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
              "stroke": "#333333", "width": 2, "fill": "none"}]
    for i in range(1, n):
        x = w * i / n
        specs.append({"shape": "line", "x1": x, "y1": 0.0, "x2": x, "y2": h,
                      "stroke": "#333333", "width": 1.5})
    ax0, ax1, cy, head = w * 0.08, w * 0.92, h * 0.5, w * 0.05
    specs += [
        {"shape": "line", "x1": ax0, "y1": cy, "x2": ax1, "y2": cy,
         "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": ax1, "y1": cy, "x2": ax1 - head, "y2": cy - head,
         "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": ax1, "y1": cy, "x2": ax1 - head, "y2": cy + head,
         "stroke": "#333333", "width": 1.5},
    ]
    return specs


# --------------------------------------------------------------------- palette
# Shared colours/weights for the furniture & fixture symbols, refined to
# match a professional top-view plan-symbol sheet (clean line-art).
OUTLINE = _INK = "#333333"          # outlines
WOOD = _WOOD = "#e8dcc8"            # wood / table tops
WOOD_DK = "#d9c2a3"                 # darker wood
BEDDING = _UPH2 = _APP = "#eef2f6"  # bedding / light upholstery / appliances
PILLOW = _UPH = _MET = "#dfe7ee"    # pillows / upholstery / metal
_WTR = "white"                      # water / porcelain
_GRN = "#dfe9dc"                    # plant green
_NONE = "none"
W_OUT = _W_OUT = 2                  # outline width
W_DET = _W_DET = 1.2               # detail width


# ------------------------------------------------------------------ bedroom
def build_single_bed(w, h):
    specs = []
    # mattress
    specs.append({"shape": "rounded_rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
                  "radius": min(w, h) * 0.04, "stroke": OUTLINE, "fill": BEDDING, "width": W_OUT})
    # turned-down duvet band across the head
    band = h * 0.16
    specs.append({"shape": "rect", "x": w * 0.04, "y": band, "w": w * 0.92, "h": h * 0.78,
                  "stroke": OUTLINE, "fill": "none", "width": W_DET})
    # soft fold lines down the bed
    for fx in (0.34, 0.66):
        specs.append({"shape": "line", "x1": w * fx, "y1": band + h * 0.04,
                      "x2": w * fx, "y2": h * 0.92, "stroke": OUTLINE, "width": W_DET})
    # plump pillow at the head
    specs.append({"shape": "rounded_rect", "x": w * 0.14, "y": h * 0.03, "w": w * 0.72, "h": band * 0.78,
                  "radius": band * 0.32, "stroke": OUTLINE, "fill": PILLOW, "width": W_DET})
    return specs


def build_double_bed(w, h):
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
                  "radius": min(w, h) * 0.04, "stroke": OUTLINE, "fill": BEDDING, "width": W_OUT})
    band = h * 0.15
    specs.append({"shape": "rect", "x": w * 0.04, "y": band, "w": w * 0.92, "h": h * 0.80,
                  "stroke": OUTLINE, "fill": "none", "width": W_DET})
    # centre fold line down the duvet
    specs.append({"shape": "line", "x1": w * 0.5, "y1": band + h * 0.04,
                  "x2": w * 0.5, "y2": h * 0.93, "stroke": OUTLINE, "width": W_DET})
    # two pillows side by side at the head
    pw = w * 0.40
    ph = band * 0.78
    specs.append({"shape": "rounded_rect", "x": w * 0.06, "y": h * 0.03, "w": pw, "h": ph,
                  "radius": ph * 0.32, "stroke": OUTLINE, "fill": PILLOW, "width": W_DET})
    specs.append({"shape": "rounded_rect", "x": w * 0.54, "y": h * 0.03, "w": pw, "h": ph,
                  "radius": ph * 0.32, "stroke": OUTLINE, "fill": PILLOW, "width": W_DET})
    return specs


def build_nightstand(w, h):
    specs = []
    specs.append({"shape": "rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
                  "stroke": OUTLINE, "fill": WOOD, "width": W_OUT})
    # round table lamp on top: outer shade + inner base
    cx, cy = w * 0.5, h * 0.5
    r_out = min(w, h) * 0.32
    r_in = min(w, h) * 0.13
    specs.append({"shape": "circle", "x": cx - r_out, "y": cy - r_out, "w": r_out * 2, "h": r_out * 2,
                  "stroke": OUTLINE, "fill": "none", "width": W_DET})
    specs.append({"shape": "circle", "x": cx - r_in, "y": cy - r_in, "w": r_in * 2, "h": r_in * 2,
                  "stroke": OUTLINE, "fill": "none", "width": W_DET})
    return specs


def build_wardrobe(w, h):
    specs = []
    specs.append({"shape": "rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
                  "stroke": OUTLINE, "fill": WOOD, "width": W_OUT})
    # hanging rail line near the back
    rail_y = h * 0.30
    specs.append({"shape": "line", "x1": w * 0.06, "y1": rail_y, "x2": w * 0.94, "y2": rail_y,
                  "stroke": OUTLINE, "width": W_DET})
    # hanger ticks (clothes on the rail)
    n = 6
    tick = h * 0.16
    for i in range(n):
        hx = w * (0.12 + 0.76 * i / (n - 1))
        specs.append({"shape": "line", "x1": hx, "y1": rail_y, "x2": hx, "y2": rail_y + tick,
                      "stroke": OUTLINE, "width": W_DET})
    # centre division line
    specs.append({"shape": "line", "x1": w * 0.5, "y1": 0.0, "x2": w * 0.5, "y2": h,
                  "stroke": OUTLINE, "width": W_DET})
    return specs


def build_chest_of_drawers(w, h):
    specs = []
    specs.append({"shape": "rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
                  "stroke": OUTLINE, "fill": WOOD, "width": W_OUT})
    n = 3
    inset = w * 0.05
    for i in range(n):
        dy = h * (0.08 + 0.84 * i / n)
        dh = h * 0.84 / n
        specs.append({"shape": "rect", "x": inset, "y": dy, "w": w - 2 * inset, "h": dh * 0.86,
                      "stroke": OUTLINE, "fill": "none", "width": W_DET})
        kr = min(dh, w) * 0.06
        kx, ky = w * 0.5, dy + dh * 0.43
        specs.append({"shape": "circle", "x": kx - kr, "y": ky - kr, "w": kr * 2, "h": kr * 2,
                      "stroke": OUTLINE, "fill": OUTLINE, "width": W_DET})
    return specs


def build_desk(w, h):
    specs = []
    specs.append({"shape": "rect", "x": 0.0, "y": 0.0, "w": w, "h": h,
                  "stroke": OUTLINE, "fill": WOOD, "width": W_OUT})
    # laptop: base rect + thin screen line (hinge at the back, small y)
    lw, lh, lx, ly = w * 0.22, h * 0.30, w * 0.20, h * 0.34
    specs.append({"shape": "rect", "x": lx, "y": ly, "w": lw, "h": lh,
                  "stroke": OUTLINE, "fill": "none", "width": W_DET})
    specs.append({"shape": "line", "x1": lx, "y1": ly, "x2": lx + lw, "y2": ly,
                  "stroke": OUTLINE, "width": W_OUT})
    # pen tray line near the front
    specs.append({"shape": "line", "x1": w * 0.60, "y1": h * 0.74, "x2": w * 0.88, "y2": h * 0.74,
                  "stroke": OUTLINE, "width": W_DET})
    return specs


# ---------------------------------------------------------- living & dining
def build_dining_table(w, h):
    m = min(w, h)
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": m * 0.08, "stroke": "#333333", "width": 2, "fill": "#e8dcc8"},
        {"shape": "rounded_rect", "x": w * 0.06, "y": h * 0.08, "w": w * 0.88,
         "h": h * 0.84, "radius": m * 0.05, "stroke": "#333333", "width": 1.5,
         "fill": "#d9c2a3"},
    ]


def build_chair(w, h):
    """Armchair from above: U-shaped back+arms shell open at the bottom,
    square-ish seat cushion inside."""
    s = []
    s.append({"shape": "rounded_rect",
              "x": 0.06 * w, "y": 0.04 * h, "w": 0.88 * w, "h": 0.92 * h,
              "radius": 0.22 * w, "stroke": _INK, "fill": _UPH2, "width": _W_OUT})
    s.append({"shape": "rounded_rect",
              "x": 0.24 * w, "y": 0.30 * h, "w": 0.52 * w, "h": 0.74 * h,
              "radius": 0.10 * w, "stroke": _INK, "fill": _NONE, "width": _W_DET})
    s.append({"shape": "rounded_rect",
              "x": 0.27 * w, "y": 0.40 * h, "w": 0.46 * w, "h": 0.50 * h,
              "radius": 0.08 * w, "stroke": _INK, "fill": _UPH, "width": _W_DET})
    return s


def build_armchair(w, h):
    """Plumper armchair: rounded shell (half-circle back) with arms and a
    soft seat cushion."""
    s = []
    s.append({"shape": "rounded_rect",
              "x": 0.04 * w, "y": 0.03 * h, "w": 0.92 * w, "h": 0.94 * h,
              "radius": 0.30 * w, "stroke": _INK, "fill": _UPH2, "width": _W_OUT})
    s.append({"shape": "halfcircle",
              "x": 0.12 * w, "y": 0.06 * h, "w": 0.76 * w, "h": 0.46 * h,
              "stroke": _INK, "fill": _UPH2, "width": _W_DET, "rotation": 0})
    s.append({"shape": "rounded_rect",
              "x": 0.05 * w, "y": 0.30 * h, "w": 0.17 * w, "h": 0.58 * h,
              "radius": 0.07 * w, "stroke": _INK, "fill": _UPH2, "width": _W_DET})
    s.append({"shape": "rounded_rect",
              "x": 0.78 * w, "y": 0.30 * h, "w": 0.17 * w, "h": 0.58 * h,
              "radius": 0.07 * w, "stroke": _INK, "fill": _UPH2, "width": _W_DET})
    s.append({"shape": "rounded_rect",
              "x": 0.25 * w, "y": 0.42 * h, "w": 0.50 * w, "h": 0.50 * h,
              "radius": 0.14 * w, "stroke": _INK, "fill": _UPH, "width": _W_DET})
    return s


def build_sofa(w, h):
    """Wide 3-seater: rounded back, two arm bolsters at the ends, three seat
    cushions in a row, three back cushions behind them."""
    s = []
    s.append({"shape": "rounded_rect",
              "x": 0.01 * w, "y": 0.04 * h, "w": 0.98 * w, "h": 0.92 * h,
              "radius": 0.10 * h, "stroke": _INK, "fill": _UPH2, "width": _W_OUT})
    s.append({"shape": "rounded_rect",
              "x": 0.015 * w, "y": 0.12 * h, "w": 0.085 * w, "h": 0.80 * h,
              "radius": 0.04 * w, "stroke": _INK, "fill": _UPH2, "width": _W_DET})
    s.append({"shape": "rounded_rect",
              "x": 0.90 * w, "y": 0.12 * h, "w": 0.085 * w, "h": 0.80 * h,
              "radius": 0.04 * w, "stroke": _INK, "fill": _UPH2, "width": _W_DET})
    seat_x0 = 0.115 * w
    seat_w = 0.77 * w
    cw = seat_w / 3.0
    for i in range(3):
        s.append({"shape": "rounded_rect",
                  "x": seat_x0 + i * cw + 0.01 * w, "y": 0.10 * h,
                  "w": cw - 0.02 * w, "h": 0.30 * h,
                  "radius": 0.05 * w / 3.0 + 0.01 * w,
                  "stroke": _INK, "fill": _UPH2, "width": _W_DET})
    for i in range(3):
        s.append({"shape": "rounded_rect",
                  "x": seat_x0 + i * cw + 0.01 * w, "y": 0.42 * h,
                  "w": cw - 0.02 * w, "h": 0.50 * h,
                  "radius": 0.05 * w / 3.0 + 0.01 * w,
                  "stroke": _INK, "fill": _UPH, "width": _W_DET})
    return s


def build_coffee_table(w, h):
    """Rounded-rect table with a thin inner outline."""
    return [
        {"shape": "rounded_rect",
         "x": 0.02 * w, "y": 0.04 * h, "w": 0.96 * w, "h": 0.92 * h,
         "radius": 0.10 * h, "stroke": _INK, "fill": _WOOD, "width": _W_OUT},
        {"shape": "rounded_rect",
         "x": 0.07 * w, "y": 0.12 * h, "w": 0.86 * w, "h": 0.76 * h,
         "radius": 0.08 * h, "stroke": _INK, "fill": _NONE, "width": _W_DET},
    ]


def build_tv_unit(w, h):
    """Long shallow cabinet with door divisions and a small TV slab line."""
    s = [{"shape": "rect",
          "x": 0.01 * w, "y": 0.30 * h, "w": 0.98 * w, "h": 0.66 * h,
          "stroke": _INK, "fill": _WOOD, "width": _W_OUT}]
    for i in (1, 2):
        x = 0.01 * w + i * (0.98 * w) / 3.0
        s.append({"shape": "line", "x1": x, "y1": 0.30 * h, "x2": x, "y2": 0.96 * h,
                  "stroke": _INK, "width": _W_DET})
    for i in range(3):
        cx = 0.01 * w + (i + 0.5) * (0.98 * w) / 3.0
        s.append({"shape": "line", "x1": cx - 0.03 * w, "y1": 0.88 * h,
                  "x2": cx + 0.03 * w, "y2": 0.88 * h, "stroke": _INK, "width": _W_DET})
    s.append({"shape": "rect", "x": 0.28 * w, "y": 0.10 * h, "w": 0.44 * w, "h": 0.10 * h,
              "stroke": _INK, "fill": _UPH2, "width": _W_DET})
    return s


def build_bookshelf(w, h):
    """Long shallow rect with vertical shelf divisions."""
    s = [{"shape": "rect",
          "x": 0.01 * w, "y": 0.10 * h, "w": 0.98 * w, "h": 0.80 * h,
          "stroke": _INK, "fill": _WOOD, "width": _W_OUT}]
    n = 5
    for i in range(1, n):
        x = 0.01 * w + i * (0.98 * w) / n
        s.append({"shape": "line", "x1": x, "y1": 0.10 * h, "x2": x, "y2": 0.90 * h,
                  "stroke": _INK, "width": _W_DET})
    return s


def build_round_table(w, h):
    """Round dining table (circle + inner ring) with 4 U-shaped chairs around
    it (top/bottom/left/right), each facing the table."""
    s = []
    t = 0.20         # margin around the table for the chairs
    s.append({"shape": "circle",
              "x": t * w, "y": t * h, "w": (1 - 2 * t) * w, "h": (1 - 2 * t) * h,
              "stroke": _INK, "fill": _WOOD, "width": _W_OUT})
    s.append({"shape": "circle",
              "x": (t + 0.05) * w, "y": (t + 0.05) * h,
              "w": (1 - 2 * t - 0.10) * w, "h": (1 - 2 * t - 0.10) * h,
              "stroke": _INK, "fill": _NONE, "width": _W_DET})

    cw = 0.26 * w
    ch = 0.16 * h
    rad = 0.06 * w

    def _chair(cx, cy, side):
        out = []
        if side in ("t", "b"):
            sw, sh = cw, ch
        else:
            sw, sh = ch, cw
        x0, y0 = cx - sw / 2.0, cy - sh / 2.0
        out.append({"shape": "rounded_rect", "x": x0, "y": y0, "w": sw, "h": sh,
                    "radius": rad, "stroke": _INK, "fill": _UPH2, "width": _W_DET})
        m = 0.22
        if side == "t":
            out.append({"shape": "rounded_rect", "x": x0 + m * sw, "y": y0 + 0.45 * sh,
                        "w": (1 - 2 * m) * sw, "h": 0.50 * sh,
                        "radius": rad * 0.6, "stroke": _INK, "fill": _UPH, "width": _W_DET})
        elif side == "b":
            out.append({"shape": "rounded_rect", "x": x0 + m * sw, "y": y0 + 0.05 * sh,
                        "w": (1 - 2 * m) * sw, "h": 0.50 * sh,
                        "radius": rad * 0.6, "stroke": _INK, "fill": _UPH, "width": _W_DET})
        elif side == "l":
            out.append({"shape": "rounded_rect", "x": x0 + 0.45 * sw, "y": y0 + m * sh,
                        "w": 0.50 * sw, "h": (1 - 2 * m) * sh,
                        "radius": rad * 0.6, "stroke": _INK, "fill": _UPH, "width": _W_DET})
        else:
            out.append({"shape": "rounded_rect", "x": x0 + 0.05 * sw, "y": y0 + m * sh,
                        "w": 0.50 * sw, "h": (1 - 2 * m) * sh,
                        "radius": rad * 0.6, "stroke": _INK, "fill": _UPH, "width": _W_DET})
        return out

    s += _chair(0.50 * w, 0.085 * h, "t")
    s += _chair(0.50 * w, 0.915 * h, "b")
    s += _chair(0.085 * w, 0.50 * h, "l")
    s += _chair(0.915 * w, 0.50 * h, "r")
    return s


# ------------------------------------------------------------------ kitchen
def build_kitchen_counter(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": _INK, "fill": _APP, "width": 2},
        {"shape": "line", "x1": 0, "y1": h * 0.85, "x2": w, "y2": h * 0.85,
         "stroke": _INK, "width": 1.2},
    ]


def build_kitchen_sink(w, h):
    bw = w * 0.38
    bx0 = w * 0.07
    bx1 = w - bx0 - bw
    by = h * 0.30
    bh = h * 0.56
    r = min(w, h) * 0.04
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": _INK, "fill": _APP, "width": 2},
        {"shape": "rounded_rect", "x": bx0, "y": by, "w": bw, "h": bh,
         "radius": r, "stroke": _INK, "fill": _WTR, "width": 1.2},
        {"shape": "rounded_rect", "x": bx1, "y": by, "w": bw, "h": bh,
         "radius": r, "stroke": _INK, "fill": _WTR, "width": 1.2},
        {"shape": "line", "x1": w * 0.50, "y1": h * 0.10,
         "x2": w * 0.50, "y2": h * 0.24, "stroke": _INK, "width": 1.2},
        {"shape": "circle", "x": w * 0.46, "y": h * 0.06, "w": w * 0.08,
         "h": w * 0.08, "stroke": _INK, "fill": _MET, "width": 1.2},
    ]


def build_stove(w, h):
    specs = [{"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
              "stroke": _INK, "fill": _APP, "width": 2}]
    od = w * 0.30
    for cx, cy in ((0.14, 0.28), (0.56, 0.28), (0.14, 0.60), (0.56, 0.60)):
        ox, oy = w * cx, h * cy
        specs.append({"shape": "circle", "x": ox, "y": oy, "w": od, "h": od,
                      "stroke": _INK, "fill": _WTR, "width": 1.2})
        inset = od * 0.28
        specs.append({"shape": "circle", "x": ox + inset, "y": oy + inset,
                      "w": od - 2 * inset, "h": od - 2 * inset,
                      "stroke": _INK, "fill": _WTR, "width": 1.2})
    kd = w * 0.07
    for kx in (0.18, 0.40, 0.60, 0.82):
        specs.append({"shape": "circle", "x": w * kx - kd * 0.5,
                      "y": h * 0.10 - kd * 0.5, "w": kd, "h": kd,
                      "stroke": _INK, "fill": _MET, "width": 1.2})
    return specs


def build_fridge(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": min(w, h) * 0.05, "stroke": _INK, "fill": _APP, "width": 2},
        {"shape": "line", "x1": w * 0.50, "y1": 0, "x2": w * 0.50, "y2": h,
         "stroke": _INK, "width": 1.2},
        {"shape": "line", "x1": w * 0.42, "y1": h * 0.38,
         "x2": w * 0.42, "y2": h * 0.62, "stroke": _INK, "width": 1.2},
    ]


def build_kitchen_island(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": min(w, h) * 0.05, "stroke": _INK, "fill": _APP, "width": 2},
        {"shape": "line", "x1": w * 0.05, "y1": h * 0.78,
         "x2": w * 0.95, "y2": h * 0.78, "stroke": _INK, "width": 1.2},
        {"shape": "rounded_rect", "x": w * 0.62, "y": h * 0.18, "w": w * 0.26,
         "h": h * 0.40, "radius": min(w, h) * 0.04, "stroke": _INK,
         "fill": _WTR, "width": 1.2},
        {"shape": "circle", "x": w * 0.735, "y": h * 0.05, "w": w * 0.03,
         "h": w * 0.03, "stroke": _INK, "fill": _MET, "width": 1.2},
    ]


def build_dishwasher(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": _INK, "fill": _APP, "width": 2},
        {"shape": "line", "x1": 0, "y1": h * 0.18, "x2": w, "y2": h * 0.18,
         "stroke": _INK, "width": 1.2},
        {"shape": "line", "x1": w * 0.30, "y1": h * 0.42,
         "x2": w * 0.70, "y2": h * 0.42, "stroke": _INK, "width": 1.2},
    ]


# --------------------------------------------------------- bathroom & utility
def build_toilet(w, h):
    return [
        {"shape": "rounded_rect", "x": w * 0.20, "y": 0, "w": w * 0.60,
         "h": h * 0.24, "radius": w * 0.05, "stroke": _INK, "fill": _WTR,
         "width": 2},
        {"shape": "ellipse", "x": w * 0.22, "y": h * 0.22, "w": w * 0.56,
         "h": h * 0.74, "stroke": _INK, "fill": _WTR, "width": 2},
        {"shape": "ellipse", "x": w * 0.30, "y": h * 0.32, "w": w * 0.40,
         "h": h * 0.54, "stroke": _INK, "fill": _WTR, "width": 1.2},
    ]


def build_bathroom_sink(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": min(w, h) * 0.05, "stroke": _INK, "fill": _APP, "width": 2},
        {"shape": "line", "x1": w * 0.50, "y1": h * 0.08,
         "x2": w * 0.50, "y2": h * 0.20, "stroke": _INK, "width": 1.2},
        {"shape": "circle", "x": w * 0.46, "y": h * 0.04, "w": w * 0.08,
         "h": w * 0.08, "stroke": _INK, "fill": _MET, "width": 1.2},
        {"shape": "ellipse", "x": w * 0.18, "y": h * 0.26, "w": w * 0.64,
         "h": h * 0.62, "stroke": _INK, "fill": _WTR, "width": 1.2},
        {"shape": "circle", "x": w * 0.475, "y": h * 0.52, "w": w * 0.05,
         "h": w * 0.05, "stroke": _INK, "fill": _WTR, "width": 1.2},
    ]


def build_bathtub(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": h * 0.20, "stroke": _INK, "fill": _WTR, "width": 2},
        {"shape": "rounded_rect", "x": w * 0.05, "y": h * 0.12, "w": w * 0.80,
         "h": h * 0.76, "radius": h * 0.16, "stroke": _INK, "fill": _WTR,
         "width": 1.2},
        {"shape": "circle", "x": w * 0.89, "y": h * 0.46, "w": h * 0.08,
         "h": h * 0.08, "stroke": _INK, "fill": _MET, "width": 1.2},
    ]


def build_shower(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": _INK, "fill": _APP, "width": 2},
        {"shape": "quartercircle", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": _INK, "fill": "none", "width": 1.2, "rotation": 0},
        {"shape": "circle", "x": w * 0.44, "y": h * 0.44, "w": w * 0.12,
         "h": w * 0.12, "stroke": _INK, "fill": _WTR, "width": 1.2},
        {"shape": "circle", "x": w * 0.47, "y": h * 0.47, "w": w * 0.06,
         "h": w * 0.06, "stroke": _INK, "fill": _WTR, "width": 1.2},
    ]


def build_washing_machine(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": _INK, "fill": _APP, "width": 2},
        {"shape": "line", "x1": 0, "y1": h * 0.18, "x2": w, "y2": h * 0.18,
         "stroke": _INK, "width": 1.2},
        {"shape": "rect", "x": w * 0.10, "y": h * 0.07, "w": w * 0.18,
         "h": h * 0.06, "stroke": _INK, "fill": _MET, "width": 1.2},
        {"shape": "circle", "x": w * 0.22, "y": h * 0.30, "w": w * 0.56,
         "h": w * 0.56, "stroke": _INK, "fill": _WTR, "width": 2},
        {"shape": "circle", "x": w * 0.31, "y": h * 0.39, "w": w * 0.38,
         "h": w * 0.38, "stroke": _INK, "fill": _MET, "width": 1.2},
    ]


# -------------------------------------------------------------------- decor
def build_plant(w, h):
    specs = [
        {"shape": "circle", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": _INK, "fill": _GRN, "width": 2},
        {"shape": "circle", "x": w * 0.30, "y": h * 0.30, "w": w * 0.40,
         "h": h * 0.40, "stroke": _INK, "fill": _GRN, "width": 1.2},
    ]
    cx, cy = w * 0.5, h * 0.5
    r0 = min(w, h) * 0.20
    r1 = min(w, h) * 0.42
    for i in range(10):
        a = math.radians(i * 36.0)
        ca, sa = math.cos(a), math.sin(a)
        specs.append({"shape": "line", "x1": cx + r0 * ca, "y1": cy + r0 * sa,
                      "x2": cx + r1 * ca, "y2": cy + r1 * sa,
                      "stroke": _INK, "width": 1.2})
    lw = min(w, h) * 0.16
    for i in range(5):
        a = i * 72.0
        specs.append({"shape": "triangle", "x": cx - lw * 0.5,
                      "y": cy - lw * 0.9, "w": lw, "h": lw * 0.9,
                      "stroke": _INK, "fill": _GRN, "width": 1.2, "rotation": a})
    return specs


def build_rug(w, h):
    specs = [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": min(w, h) * 0.06, "stroke": _INK, "fill": "none", "width": 2},
        {"shape": "rounded_rect", "x": w * 0.06, "y": h * 0.06, "w": w * 0.88,
         "h": h * 0.88, "radius": min(w, h) * 0.04, "stroke": _INK,
         "fill": "none", "width": 1.2},
    ]
    n = 9
    fr = w * 0.03
    for i in range(n):
        y = h * (i + 0.5) / n
        specs.append({"shape": "line", "x1": -fr, "y1": y, "x2": 0, "y2": y,
                      "stroke": _INK, "width": 1.2})
        specs.append({"shape": "line", "x1": w, "y1": y, "x2": w + fr, "y2": y,
                      "stroke": _INK, "width": 1.2})
    return specs


#: The page width represents this much real space (mm), so a whole room
#: fits the drawing — a 480 mm chair is then ~1/10 of the page.
REFERENCE_MM = 4800.0

#: Real-world plan size (width_mm, depth_mm) for each element.
SIZES = {
    "wall": (2000, 150), "door": (900, 900), "double_door": (1800, 900),
    "window": (1200, 150), "opening": (900, 150), "stairs": (2400, 1000),
    "single_bed": (900, 1900), "double_bed": (1500, 2000),
    "wardrobe": (1000, 600), "nightstand": (450, 400),
    "chest_of_drawers": (800, 450), "desk": (1200, 600),
    "dining_table": (1600, 900), "round_table": (1400, 1400),
    "chair": (550, 550), "sofa": (2100, 950),
    "armchair": (900, 850), "coffee_table": (1100, 600),
    "tv_unit": (1800, 450), "bookshelf": (900, 300),
    "kitchen_counter": (600, 600), "kitchen_sink": (800, 600),
    "stove": (600, 600), "fridge": (700, 700), "kitchen_island": (1800, 900),
    "dishwasher": (600, 600),
    "toilet": (400, 700), "bathroom_sink": (600, 450), "bathtub": (1700, 750),
    "shower": (900, 900), "washing_machine": (600, 600),
    "plant": (500, 500), "rug": (2000, 1400),
}

#: Display name per element.
LABELS = {
    "wall": "Wall", "door": "Door", "double_door": "Double door",
    "window": "Window", "opening": "Opening", "stairs": "Stairs",
    "single_bed": "Single bed", "double_bed": "Double bed",
    "wardrobe": "Wardrobe", "nightstand": "Nightstand",
    "chest_of_drawers": "Chest of drawers", "desk": "Desk",
    "dining_table": "Dining table", "round_table": "Round table",
    "chair": "Chair", "sofa": "Sofa",
    "armchair": "Armchair", "coffee_table": "Coffee table",
    "tv_unit": "TV unit", "bookshelf": "Bookshelf",
    "kitchen_counter": "Counter", "kitchen_sink": "Sink",
    "stove": "Stove / hob", "fridge": "Fridge",
    "kitchen_island": "Island", "dishwasher": "Dishwasher",
    "toilet": "Toilet", "bathroom_sink": "Basin", "bathtub": "Bathtub",
    "shower": "Shower", "washing_machine": "Washing machine",
    "plant": "Plant", "rug": "Rug",
}

#: Menu sections: (section title, [element names]).
CATEGORIES = [
    ("Walls & openings",
     ["wall", "door", "double_door", "window", "opening", "stairs"]),
    ("Bedroom",
     ["single_bed", "double_bed", "wardrobe", "nightstand",
      "chest_of_drawers", "desk"]),
    ("Living & dining",
     ["dining_table", "round_table", "chair", "sofa", "armchair",
      "coffee_table", "tv_unit", "bookshelf"]),
    ("Kitchen",
     ["kitchen_counter", "kitchen_sink", "stove", "fridge",
      "kitchen_island", "dishwasher"]),
    ("Bathroom & utility",
     ["toilet", "bathroom_sink", "bathtub", "shower", "washing_machine"]),
    ("Decor",
     ["plant", "rug"]),
]

_BUILDERS = {name: globals()["build_" + name] for name in SIZES}


def build_specs(name, w, h):
    """Shape specs for *name* drawn into a (w, h) px box."""
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
