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


# ------------------------------------------------------------------ bedroom
def build_single_bed(w, h):
    m = min(w, h)
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": m * 0.05, "stroke": "#333333", "width": 2, "fill": "#eef2f6"},
        {"shape": "line", "x1": 0, "y1": h * 0.28, "x2": w, "y2": h * 0.28,
         "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": 0, "y1": h * 0.32, "x2": w, "y2": h * 0.32,
         "stroke": "#333333", "width": 1.5},
        {"shape": "rounded_rect", "x": w * 0.18, "y": h * 0.05, "w": w * 0.64,
         "h": h * 0.17, "radius": m * 0.04, "stroke": "#333333", "width": 1.5,
         "fill": "#dfe7ee"},
    ]


def build_double_bed(w, h):
    m = min(w, h)
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": m * 0.05, "stroke": "#333333", "width": 2, "fill": "#eef2f6"},
        {"shape": "line", "x1": 0, "y1": h * 0.28, "x2": w, "y2": h * 0.28,
         "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": 0, "y1": h * 0.32, "x2": w, "y2": h * 0.32,
         "stroke": "#333333", "width": 1.5},
        {"shape": "rounded_rect", "x": w * 0.06, "y": h * 0.05, "w": w * 0.40,
         "h": h * 0.17, "radius": m * 0.04, "stroke": "#333333", "width": 1.5,
         "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": w * 0.54, "y": h * 0.05, "w": w * 0.40,
         "h": h * 0.17, "radius": m * 0.04, "stroke": "#333333", "width": 1.5,
         "fill": "#dfe7ee"},
    ]


def build_wardrobe(w, h):
    m = min(w, h)
    specs = [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": "#333333", "width": 2, "fill": "#d9c2a3"},
        {"shape": "line", "x1": w * 0.5, "y1": 0, "x2": w * 0.5, "y2": h,
         "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": 0, "y1": h * 0.18, "x2": w, "y2": h * 0.18,
         "stroke": "#333333", "width": 1.5},
        {"shape": "circle", "x": w * 0.44, "y": h * 0.55, "w": m * 0.05,
         "h": m * 0.05, "stroke": "#333333", "width": 1.5, "fill": "#333333"},
        {"shape": "circle", "x": w * 0.51, "y": h * 0.55, "w": m * 0.05,
         "h": m * 0.05, "stroke": "#333333", "width": 1.5, "fill": "#333333"},
    ]
    for i in range(6):
        x = w * (0.06 + 0.16 * i)
        specs.append({"shape": "line", "x1": x, "y1": h * 0.09,
                      "x2": x + w * 0.10, "y2": h * 0.09,
                      "stroke": "#333333", "width": 1.5})
    return specs


def build_nightstand(w, h):
    m = min(w, h)
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": m * 0.08, "stroke": "#333333", "width": 2, "fill": "#e8dcc8"},
        {"shape": "rounded_rect", "x": w * 0.12, "y": h * 0.18, "w": w * 0.76,
         "h": h * 0.64, "radius": m * 0.05, "stroke": "#333333", "width": 1.5,
         "fill": "none"},
        {"shape": "circle", "x": w * 0.45, "y": h * 0.45, "w": m * 0.1,
         "h": m * 0.1, "stroke": "#333333", "width": 1.5, "fill": "#333333"},
    ]


def build_chest_of_drawers(w, h):
    m = min(w, h)
    specs = [{"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
              "stroke": "#333333", "width": 2, "fill": "#e8dcc8"}]
    for i in range(1, 3):
        y = h * (i / 3.0)
        specs.append({"shape": "line", "x1": 0, "y1": y, "x2": w, "y2": y,
                      "stroke": "#333333", "width": 1.5})
    for i in range(3):
        cy = h * ((i + 0.5) / 3.0)
        specs.append({"shape": "circle", "x": w * 0.5 - m * 0.04,
                      "y": cy - m * 0.04, "w": m * 0.08, "h": m * 0.08,
                      "stroke": "#333333", "width": 1.5, "fill": "#333333"})
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
    m = min(w, h)
    return [
        {"shape": "rounded_rect", "x": w * 0.12, "y": h * 0.22, "w": w * 0.76,
         "h": h * 0.7, "radius": m * 0.08, "stroke": "#333333", "width": 2,
         "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": w * 0.2, "y": h * 0.32, "w": w * 0.6,
         "h": h * 0.5, "radius": m * 0.06, "stroke": "#333333", "width": 1.5,
         "fill": "#eef2f6"},
        {"shape": "rounded_rect", "x": w * 0.1, "y": h * 0.05, "w": w * 0.8,
         "h": h * 0.16, "radius": m * 0.05, "stroke": "#333333", "width": 2,
         "fill": "#dfe7ee"},
    ]


def build_sofa(w, h):
    m = min(w, h)
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": m * 0.12, "stroke": "#333333", "width": 2, "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": w * 0.04, "y": h * 0.06, "w": w * 0.92,
         "h": h * 0.32, "radius": m * 0.08, "stroke": "#333333", "width": 1.5,
         "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": 0, "y": h * 0.32, "w": w * 0.1,
         "h": h * 0.68, "radius": m * 0.06, "stroke": "#333333", "width": 2,
         "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": w * 0.9, "y": h * 0.32, "w": w * 0.1,
         "h": h * 0.68, "radius": m * 0.06, "stroke": "#333333", "width": 2,
         "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": w * 0.115, "y": h * 0.4, "w": w * 0.25,
         "h": h * 0.54, "radius": m * 0.06, "stroke": "#333333", "width": 1.5,
         "fill": "#eef2f6"},
        {"shape": "rounded_rect", "x": w * 0.375, "y": h * 0.4, "w": w * 0.25,
         "h": h * 0.54, "radius": m * 0.06, "stroke": "#333333", "width": 1.5,
         "fill": "#eef2f6"},
        {"shape": "rounded_rect", "x": w * 0.635, "y": h * 0.4, "w": w * 0.25,
         "h": h * 0.54, "radius": m * 0.06, "stroke": "#333333", "width": 1.5,
         "fill": "#eef2f6"},
    ]


def build_armchair(w, h):
    m = min(w, h)
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": m * 0.14, "stroke": "#333333", "width": 2, "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": w * 0.08, "y": h * 0.06, "w": w * 0.84,
         "h": h * 0.3, "radius": m * 0.1, "stroke": "#333333", "width": 1.5,
         "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": 0, "y": h * 0.3, "w": w * 0.16,
         "h": h * 0.7, "radius": m * 0.08, "stroke": "#333333", "width": 2,
         "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": w * 0.84, "y": h * 0.3, "w": w * 0.16,
         "h": h * 0.7, "radius": m * 0.08, "stroke": "#333333", "width": 2,
         "fill": "#dfe7ee"},
        {"shape": "rounded_rect", "x": w * 0.18, "y": h * 0.4, "w": w * 0.64,
         "h": h * 0.54, "radius": m * 0.1, "stroke": "#333333", "width": 1.5,
         "fill": "#eef2f6"},
    ]


def build_coffee_table(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": min(w, h) * 0.1, "stroke": "#333333", "width": 2,
         "fill": "#e8dcc8"},
        {"shape": "rect", "x": w * 0.12, "y": h * 0.18, "w": w * 0.76,
         "h": h * 0.64, "stroke": "#333333", "width": 1.5, "fill": "none"},
    ]


def build_tv_unit(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": "#333333", "width": 2, "fill": "#d9c2a3"},
        {"shape": "line", "x1": w / 3.0, "y1": h * 0.08, "x2": w / 3.0,
         "y2": h * 0.92, "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": w * 2.0 / 3.0, "y1": h * 0.08,
         "x2": w * 2.0 / 3.0, "y2": h * 0.92, "stroke": "#333333", "width": 1.5},
    ]


def build_bookshelf(w, h):
    specs = [{"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
              "stroke": "#333333", "width": 2, "fill": "#e8dcc8"}]
    for i in range(1, 5):
        x = w * 0.2 * i
        specs.append({"shape": "line", "x1": x, "y1": h * 0.1, "x2": x,
                      "y2": h * 0.9, "stroke": "#333333", "width": 1.5})
    return specs


# ------------------------------------------------------------------ kitchen
def build_kitchen_counter(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": "#333333", "fill": "#e9e6e0", "width": 2},
        {"shape": "line", "x1": 0, "y1": h * 0.82, "x2": w, "y2": h * 0.82,
         "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": w * 0.25, "y1": 0, "x2": w * 0.25, "y2": h * 0.82,
         "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": w * 0.50, "y1": 0, "x2": w * 0.50, "y2": h * 0.82,
         "stroke": "#333333", "width": 1.5},
        {"shape": "line", "x1": w * 0.75, "y1": 0, "x2": w * 0.75, "y2": h * 0.82,
         "stroke": "#333333", "width": 1.5},
    ]


def build_kitchen_sink(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": "#333333", "fill": "#e9e6e0", "width": 2},
        {"shape": "rounded_rect", "x": w * 0.08, "y": h * 0.28, "w": w * 0.40,
         "h": h * 0.58, "radius": min(w, h) * 0.05, "stroke": "#333333",
         "fill": "#eef2f6", "width": 1.5},
        {"shape": "rounded_rect", "x": w * 0.52, "y": h * 0.28, "w": w * 0.40,
         "h": h * 0.58, "radius": min(w, h) * 0.05, "stroke": "#333333",
         "fill": "#eef2f6", "width": 1.5},
        {"shape": "circle", "x": w * 0.46, "y": h * 0.08, "w": w * 0.08,
         "h": w * 0.08, "stroke": "#333333", "fill": "#eef2f6", "width": 1.5},
    ]


def build_stove(w, h):
    specs = [{"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
              "stroke": "#555555", "fill": "#f2f4f6", "width": 2}]
    for cx, cy in ((0.12, 0.10), (0.60, 0.10), (0.12, 0.48), (0.60, 0.48)):
        specs.append({"shape": "circle", "x": w * cx, "y": h * cy,
                      "w": w * 0.28, "h": w * 0.28, "stroke": "#555555",
                      "fill": "#ffffff", "width": 1.5})
    specs.append({"shape": "line", "x1": w * 0.08, "y1": h * 0.88,
                  "x2": w * 0.92, "y2": h * 0.88, "stroke": "#555555",
                  "width": 1.5})
    return specs


def build_fridge(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": min(w, h) * 0.08, "stroke": "#555555", "fill": "#ffffff",
         "width": 2},
        {"shape": "line", "x1": w * 0.50, "y1": 0, "x2": w * 0.50, "y2": h,
         "stroke": "#555555", "width": 1.5},
        {"shape": "line", "x1": w * 0.44, "y1": h * 0.35, "x2": w * 0.44,
         "y2": h * 0.65, "stroke": "#555555", "width": 1.5},
    ]


def build_kitchen_island(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": min(w, h) * 0.06, "stroke": "#333333", "fill": "#e9e6e0",
         "width": 2},
        {"shape": "rounded_rect", "x": w * 0.06, "y": h * 0.06, "w": w * 0.88,
         "h": h * 0.88, "radius": min(w, h) * 0.05, "stroke": "#333333",
         "fill": "none", "width": 1.5},
    ]


def build_dishwasher(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": "#555555", "fill": "#f2f4f6", "width": 2},
        {"shape": "line", "x1": 0, "y1": h * 0.18, "x2": w, "y2": h * 0.18,
         "stroke": "#555555", "width": 1.5},
        {"shape": "line", "x1": w * 0.20, "y1": h * 0.34, "x2": w * 0.80,
         "y2": h * 0.34, "stroke": "#555555", "width": 1.5},
    ]


# --------------------------------------------------------- bathroom & utility
def build_toilet(w, h):
    return [
        {"shape": "rounded_rect", "x": w * 0.18, "y": 0, "w": w * 0.64,
         "h": h * 0.26, "radius": w * 0.04, "stroke": "#555555", "width": 2,
         "fill": "#ffffff"},
        {"shape": "ellipse", "x": w * 0.22, "y": h * 0.24, "w": w * 0.56,
         "h": h * 0.7, "stroke": "#555555", "width": 2, "fill": "#ffffff"},
        {"shape": "ellipse", "x": w * 0.31, "y": h * 0.34, "w": w * 0.38,
         "h": h * 0.5, "stroke": "#555555", "width": 1.5, "fill": "#eef2f6"},
    ]


def build_bathroom_sink(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": w * 0.08, "stroke": "#555555", "width": 2, "fill": "#ffffff"},
        {"shape": "circle", "x": w * 0.45, "y": h * 0.08, "w": w * 0.1,
         "h": w * 0.1, "stroke": "#555555", "width": 1.5, "fill": "none"},
        {"shape": "ellipse", "x": w * 0.17, "y": h * 0.24, "w": w * 0.66,
         "h": h * 0.62, "stroke": "#555555", "width": 1.5, "fill": "#eef2f6"},
        {"shape": "circle", "x": w * 0.47, "y": h * 0.52, "w": w * 0.06,
         "h": w * 0.06, "stroke": "#555555", "width": 1.5, "fill": "none"},
    ]


def build_bathtub(w, h):
    return [
        {"shape": "rounded_rect", "x": 0, "y": 0, "w": w, "h": h,
         "radius": h * 0.2, "stroke": "#555555", "width": 2, "fill": "#ffffff"},
        {"shape": "rounded_rect", "x": w * 0.06, "y": h * 0.12, "w": w * 0.78,
         "h": h * 0.76, "radius": h * 0.16, "stroke": "#555555", "width": 1.5,
         "fill": "#eef2f6"},
        {"shape": "circle", "x": w * 0.88, "y": h * 0.46, "w": h * 0.08,
         "h": h * 0.08, "stroke": "#555555", "width": 1.5, "fill": "none"},
    ]


def build_shower(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": "#555555", "width": 2, "fill": "#ffffff"},
        {"shape": "line", "x1": 0, "y1": 0, "x2": w, "y2": h,
         "stroke": "#555555", "width": 1.5},
        {"shape": "line", "x1": w, "y1": 0, "x2": 0, "y2": h,
         "stroke": "#555555", "width": 1.5},
        {"shape": "circle", "x": w * 0.42, "y": h * 0.42, "w": w * 0.16,
         "h": w * 0.16, "stroke": "#555555", "width": 1.5, "fill": "#eef2f6"},
    ]


def build_washing_machine(w, h):
    return [
        {"shape": "rect", "x": 0, "y": 0, "w": w, "h": h,
         "stroke": "#555555", "width": 2, "fill": "#ffffff"},
        {"shape": "line", "x1": 0, "y1": h * 0.16, "x2": w, "y2": h * 0.16,
         "stroke": "#555555", "width": 1.5},
        {"shape": "circle", "x": w * 0.2, "y": h * 0.26, "w": w * 0.6,
         "h": w * 0.6, "stroke": "#555555", "width": 2, "fill": "#eef2f6"},
        {"shape": "circle", "x": w * 0.3, "y": h * 0.36, "w": w * 0.4,
         "h": w * 0.4, "stroke": "#555555", "width": 1.5, "fill": "#ffffff"},
    ]


#: The page width represents this much real space (mm), so a whole room
#: fits the drawing — a 480 mm chair is then ~1/10 of the page.
REFERENCE_MM = 4800.0

#: Real-world plan size (width_mm, depth_mm) for each element.
SIZES = {
    "wall": (2000, 150), "door": (900, 900), "double_door": (1800, 900),
    "window": (1200, 150), "opening": (900, 150), "stairs": (2400, 1000),
    "single_bed": (900, 1900), "double_bed": (1500, 2000),
    "wardrobe": (1000, 600), "nightstand": (450, 400),
    "chest_of_drawers": (800, 450),
    "dining_table": (1600, 900), "chair": (480, 480), "sofa": (2100, 900),
    "armchair": (950, 900), "coffee_table": (1100, 600),
    "tv_unit": (1800, 450), "bookshelf": (900, 300),
    "kitchen_counter": (1200, 600), "kitchen_sink": (800, 600),
    "stove": (600, 600), "fridge": (700, 700), "kitchen_island": (1200, 900),
    "dishwasher": (600, 600),
    "toilet": (380, 680), "bathroom_sink": (600, 450), "bathtub": (1700, 700),
    "shower": (900, 900), "washing_machine": (600, 600),
}

#: Display name per element.
LABELS = {
    "wall": "Wall", "door": "Door", "double_door": "Double door",
    "window": "Window", "opening": "Opening", "stairs": "Stairs",
    "single_bed": "Single bed", "double_bed": "Double bed",
    "wardrobe": "Wardrobe", "nightstand": "Nightstand",
    "chest_of_drawers": "Chest of drawers",
    "dining_table": "Dining table", "chair": "Chair", "sofa": "Sofa",
    "armchair": "Armchair", "coffee_table": "Coffee table",
    "tv_unit": "TV unit", "bookshelf": "Bookshelf",
    "kitchen_counter": "Counter", "kitchen_sink": "Sink",
    "stove": "Stove / hob", "fridge": "Fridge",
    "kitchen_island": "Island", "dishwasher": "Dishwasher",
    "toilet": "Toilet", "bathroom_sink": "Basin", "bathtub": "Bathtub",
    "shower": "Shower", "washing_machine": "Washing machine",
}

#: Menu sections: (section title, [element names]).
CATEGORIES = [
    ("Walls & openings",
     ["wall", "door", "double_door", "window", "opening", "stairs"]),
    ("Bedroom",
     ["single_bed", "double_bed", "wardrobe", "nightstand",
      "chest_of_drawers"]),
    ("Living & dining",
     ["dining_table", "chair", "sofa", "armchair", "coffee_table",
      "tv_unit", "bookshelf"]),
    ("Kitchen",
     ["kitchen_counter", "kitchen_sink", "stove", "fridge",
      "kitchen_island", "dishwasher"]),
    ("Bathroom & utility",
     ["toilet", "bathroom_sink", "bathtub", "shower", "washing_machine"]),
]

_BUILDERS = {name: globals()["build_" + name] for name in SIZES}


def build_specs(name, w, h):
    """Shape specs for *name* drawn into a (w, h) px box."""
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
