'''Annotation arrows, callouts and banners.

Each `build_<name>(w, h)` returns a list of shape-spec dicts (the AI/
example format) drawing a symbol inside the box (0,0)-(w,h). Same
`build_specs`/`size_mm`/`REFERENCE_MM` interface as floorplan/electrical.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
'''

import math  # noqa: F401

OUTLINE = "#333333"
FILL = "#dfe7ee"
ACCENT = "#cfe0f5"


def build_arrow_right(w, h):
    return [{"shape": "arrow_right", "x": 0.0, "y": 0.0, "w": w, "h": h,
             "rotation": 0.0, "stroke": OUTLINE, "fill": FILL, "width": 2}]


def build_arrow_left(w, h):
    return [{"shape": "arrow_right", "x": 0.0, "y": 0.0, "w": w, "h": h,
             "rotation": 180.0, "stroke": OUTLINE, "fill": FILL, "width": 2}]


def build_arrow_up(w, h):
    return [{"shape": "arrow_right", "x": 0.0, "y": 0.0, "w": w, "h": h,
             "rotation": 270.0, "stroke": OUTLINE, "fill": FILL, "width": 2}]


def build_arrow_down(w, h):
    return [{"shape": "arrow_right", "x": 0.0, "y": 0.0, "w": w, "h": h,
             "rotation": 90.0, "stroke": OUTLINE, "fill": FILL, "width": 2}]


def build_double_arrow(w, h):
    head = w * 0.28
    shaft_y = h * 0.3
    shaft_h = h * 0.4
    return [
        {"shape": "rect", "x": head, "y": shaft_y, "w": w - 2 * head,
         "h": shaft_h, "stroke": OUTLINE, "fill": FILL, "width": 2},
        {"shape": "triangle", "x": 0.0, "y": 0.0, "w": head, "h": h,
         "rotation": 270.0, "stroke": OUTLINE, "fill": FILL, "width": 2},
        {"shape": "triangle", "x": w - head, "y": 0.0, "w": head, "h": h,
         "rotation": 90.0, "stroke": OUTLINE, "fill": FILL, "width": 2},
    ]


def build_curved_arrow(w, h):
    arc_w = w * 0.85
    arc_h = h * 0.85
    head = min(w, h) * 0.3
    return [
        {"shape": "quartercircle", "x": w - arc_w, "y": h - arc_h,
         "w": arc_w, "h": arc_h, "stroke": OUTLINE, "fill": "none",
         "width": 2, "rotation": 0.0},
        {"shape": "triangle", "x": (w - arc_w) - head * 0.5, "y": 0.0,
         "w": head, "h": head, "rotation": 0.0,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
    ]


def build_bent_arrow(w, h):
    sw = min(w, h) * 0.16
    head = min(w, h) * 0.3
    vx = w - sw - head * 0.5
    return [
        {"shape": "rect", "x": 0.0, "y": h - sw, "w": vx + sw, "h": sw,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
        {"shape": "rect", "x": vx, "y": head, "w": sw, "h": h - head - sw,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
        {"shape": "triangle", "x": vx + sw / 2 - head / 2, "y": 0.0,
         "w": head, "h": head, "rotation": 0.0,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
    ]


def build_circular_arrow(w, h):
    head = min(w, h) * 0.26
    gap = w * 0.18
    cw = w
    ch = h
    return [
        {"shape": "halfcircle", "x": 0.0, "y": 0.0, "w": cw, "h": ch,
         "stroke": OUTLINE, "fill": "none", "width": 2, "rotation": 90.0},
        {"shape": "halfcircle", "x": gap, "y": 0.0, "w": cw - gap, "h": ch,
         "stroke": OUTLINE, "fill": "none", "width": 2, "rotation": 270.0},
        {"shape": "triangle", "x": gap * 0.4, "y": 0.0,
         "w": head, "h": head, "rotation": 270.0,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
    ]


def build_callout_rect(w, h):
    body_h = h * 0.78
    tail_w = w * 0.18
    tail_x = w * 0.15
    return [
        {"shape": "rect", "x": 0.0, "y": 0.0, "w": w, "h": body_h,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
        {"shape": "triangle", "x": tail_x, "y": body_h, "w": tail_w,
         "h": h - body_h, "rotation": 180.0,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
    ]


def build_callout_round(w, h):
    body_h = h * 0.78
    tail_w = w * 0.18
    tail_x = w * 0.15
    return [
        {"shape": "rounded_rect", "x": 0.0, "y": 0.0, "w": w, "h": body_h,
         "radius": min(w, body_h) * 0.18, "stroke": OUTLINE, "fill": FILL,
         "width": 2},
        {"shape": "triangle", "x": tail_x, "y": body_h, "w": tail_w,
         "h": h - body_h, "rotation": 180.0,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
    ]


def build_banner(w, h):
    notch = w * 0.12
    return [
        {"shape": "rect", "x": notch, "y": 0.0, "w": w - 2 * notch, "h": h,
         "stroke": OUTLINE, "fill": FILL, "width": 2},
        {"shape": "rect", "x": 0.0, "y": h * 0.18, "w": notch,
         "h": h * 0.64, "stroke": OUTLINE, "fill": ACCENT, "width": 2},
        {"shape": "rect", "x": w - notch, "y": h * 0.18, "w": notch,
         "h": h * 0.64, "stroke": OUTLINE, "fill": ACCENT, "width": 2},
        {"shape": "triangle", "x": 0.0, "y": h * 0.18, "w": notch * 0.6,
         "h": h * 0.64, "rotation": 90.0,
         "stroke": OUTLINE, "fill": "none", "width": 1.2},
        {"shape": "triangle", "x": w - notch * 0.6, "y": h * 0.18,
         "w": notch * 0.6, "h": h * 0.64, "rotation": 270.0,
         "stroke": OUTLINE, "fill": "none", "width": 1.2},
    ]


def build_burst(w, h):
    return [
        {"shape": "star", "x": 0.0, "y": 0.0, "w": w, "h": h,
         "rotation": 0.0, "stroke": OUTLINE, "fill": ACCENT, "width": 2},
        {"shape": "text", "text": "NEW!", "x": w * 0.5, "y": h * 0.5,
         "size": h * 0.18, "color": OUTLINE},
    ]


REFERENCE_MM = 1200.0

SIZES = {
    "arrow_right": (200.0, 100.0),
    "arrow_left": (200.0, 100.0),
    "arrow_up": (100.0, 200.0),
    "arrow_down": (100.0, 200.0),
    "double_arrow": (200.0, 100.0),
    "curved_arrow": (160.0, 160.0),
    "bent_arrow": (160.0, 160.0),
    "circular_arrow": (160.0, 160.0),
    "callout_rect": (220.0, 150.0),
    "callout_round": (220.0, 150.0),
    "banner": (260.0, 90.0),
    "burst": (160.0, 160.0),
}

LABELS = {
    "arrow_right": "Arrow right",
    "arrow_left": "Arrow left",
    "arrow_up": "Arrow up",
    "arrow_down": "Arrow down",
    "double_arrow": "Double arrow",
    "curved_arrow": "Curved arrow",
    "bent_arrow": "Bent arrow",
    "circular_arrow": "Circular arrow",
    "callout_rect": "Rectangular callout",
    "callout_round": "Rounded callout",
    "banner": "Ribbon banner",
    "burst": "Starburst badge",
}

CATEGORIES = [
    ("Block arrows",
     ["arrow_right", "arrow_left", "arrow_up", "arrow_down", "double_arrow"]),
    ("Special arrows",
     ["curved_arrow", "bent_arrow", "circular_arrow"]),
    ("Callouts & banners",
     ["callout_rect", "callout_round", "banner", "burst"]),
]


_BUILDERS = {name: globals()["build_" + name] for name in SIZES}


def build_specs(name, w, h):
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
