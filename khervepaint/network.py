'''Network / IT architecture diagram symbols.

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
DEVICE = "#eef2f6"
ACCENT = "#cfe0f5"
DARK = "#5b6b7b"
W_OUT = 2
W_DET = 1.2


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------

def build_desktop(w, h):
    """A monitor (rounded_rect screen) on a small stand."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.08 * w, "y": 0.06 * h,
                  "w": 0.84 * w, "h": 0.58 * h, "radius": 0.05 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "rounded_rect", "x": 0.15 * w, "y": 0.13 * h,
                  "w": 0.70 * w, "h": 0.44 * h, "radius": 0.03 * w,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    specs.append({"shape": "rect", "x": 0.44 * w, "y": 0.64 * h,
                  "w": 0.12 * w, "h": 0.16 * h,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_DET})
    specs.append({"shape": "trapezoid", "x": 0.26 * w, "y": 0.80 * h,
                  "w": 0.48 * w, "h": 0.14 * h, "rotation": 0.0,
                  "stroke": OUTLINE, "fill": DARK, "width": W_OUT})
    return specs


def build_laptop(w, h):
    """A screen rect + a wider keyboard trapezoid base."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.16 * w, "y": 0.08 * h,
                  "w": 0.68 * w, "h": 0.52 * h, "radius": 0.03 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "rect", "x": 0.21 * w, "y": 0.13 * h,
                  "w": 0.58 * w, "h": 0.42 * h,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    specs.append({"shape": "trapezoid", "x": 0.04 * w, "y": 0.62 * h,
                  "w": 0.92 * w, "h": 0.26 * h, "rotation": 180.0,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "line", "x1": 0.30 * w, "y1": 0.70 * h,
                  "x2": 0.70 * w, "y2": 0.70 * h,
                  "stroke": DARK, "width": W_DET})
    return specs


def build_mobile(w, h):
    """A tall rounded_rect phone with a small speaker line and home dot."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.26 * w, "y": 0.04 * h,
                  "w": 0.48 * w, "h": 0.92 * h, "radius": 0.10 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "rect", "x": 0.32 * w, "y": 0.16 * h,
                  "w": 0.36 * w, "h": 0.64 * h,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    specs.append({"shape": "line", "x1": 0.44 * w, "y1": 0.10 * h,
                  "x2": 0.56 * w, "y2": 0.10 * h,
                  "stroke": DARK, "width": W_DET})
    specs.append({"shape": "circle", "x": 0.47 * w, "y": 0.85 * h,
                  "w": 0.06 * w, "h": 0.06 * w,
                  "stroke": OUTLINE, "fill": DARK, "width": W_DET})
    return specs


def build_user(w, h):
    """A person glyph — head circle above a trapezoid torso."""
    specs = []
    specs.append({"shape": "circle", "x": 0.33 * w, "y": 0.06 * h,
                  "w": 0.34 * w, "h": 0.34 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "trapezoid", "x": 0.12 * w, "y": 0.52 * h,
                  "w": 0.76 * w, "h": 0.44 * h, "rotation": 180.0,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_OUT})
    return specs


def build_printer(w, h):
    """A printer body rect with a paper-out slot and a sheet on top."""
    specs = []
    specs.append({"shape": "rect", "x": 0.26 * w, "y": 0.04 * h,
                  "w": 0.48 * w, "h": 0.26 * h,
                  "stroke": OUTLINE, "fill": "#ffffff", "width": W_DET})
    specs.append({"shape": "line", "x1": 0.33 * w, "y1": 0.13 * h,
                  "x2": 0.67 * w, "y2": 0.13 * h,
                  "stroke": DARK, "width": W_DET})
    specs.append({"shape": "line", "x1": 0.33 * w, "y1": 0.21 * h,
                  "x2": 0.67 * w, "y2": 0.21 * h,
                  "stroke": DARK, "width": W_DET})
    specs.append({"shape": "rounded_rect", "x": 0.08 * w, "y": 0.30 * h,
                  "w": 0.84 * w, "h": 0.50 * h, "radius": 0.04 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "rect", "x": 0.20 * w, "y": 0.56 * h,
                  "w": 0.60 * w, "h": 0.08 * h,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    specs.append({"shape": "circle", "x": 0.74 * w, "y": 0.37 * h,
                  "w": 0.06 * w, "h": 0.06 * w,
                  "stroke": OUTLINE, "fill": DARK, "width": W_DET})
    specs.append({"shape": "rect", "x": 0.14 * w, "y": 0.80 * h,
                  "w": 0.72 * w, "h": 0.10 * h,
                  "stroke": OUTLINE, "fill": DARK, "width": W_DET})
    return specs


# --------------------------------------------------------------------------
# Infrastructure
# --------------------------------------------------------------------------

def build_server(w, h):
    """A tall rack box with horizontal unit divisions and status LEDs."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.18 * w, "y": 0.04 * h,
                  "w": 0.64 * w, "h": 0.92 * h, "radius": 0.04 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    units = 4
    top = 0.08 * h
    bot = 0.92 * h
    uh = (bot - top) / units
    for i in range(units):
        uy = top + i * uh
        specs.append({"shape": "rect", "x": 0.24 * w, "y": uy + 0.02 * h,
                      "w": 0.52 * w, "h": uh - 0.04 * h,
                      "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
        specs.append({"shape": "circle", "x": 0.66 * w, "y": uy + 0.06 * h,
                      "w": 0.05 * w, "h": 0.05 * w,
                      "stroke": OUTLINE, "fill": DARK, "width": W_DET})
        specs.append({"shape": "line", "x1": 0.28 * w, "y1": uy + 0.07 * h,
                      "x2": 0.50 * w, "y2": uy + 0.07 * h,
                      "stroke": DARK, "width": W_DET})
    return specs


def build_database(w, h):
    """A cylinder — full ellipse top rim, body, front-half bottom curve,
    plus a couple of platter divider lines."""
    bx, bw = 0.16 * w, 0.68 * w
    rim = 0.20 * h
    top, bot = 0.08 * h, 0.92 * h
    body_top, body_bot = top + rim / 2, bot - rim / 2
    specs = [
        # body fill + side lines
        {"shape": "rect", "x": bx, "y": body_top, "w": bw,
         "h": body_bot - body_top, "stroke": "none", "fill": DEVICE,
         "width": W_DET},
        {"shape": "line", "x1": bx, "y1": body_top, "x2": bx, "y2": body_bot,
         "stroke": OUTLINE, "width": W_OUT},
        {"shape": "line", "x1": bx + bw, "y1": body_top, "x2": bx + bw,
         "y2": body_bot, "stroke": OUTLINE, "width": W_OUT},
        # bottom front-half curve (bulging DOWN): rot180 keeps it round
        {"shape": "halfcircle", "x": bx, "y": body_bot - rim / 2,
         "w": bw, "h": rim, "stroke": OUTLINE, "fill": DEVICE,
         "width": W_OUT, "rotation": 180.0},
        # top rim ellipse
        {"shape": "ellipse", "x": bx, "y": top, "w": bw, "h": rim,
         "stroke": OUTLINE, "fill": ACCENT, "width": W_OUT},
    ]
    # platter divider (one faint ellipse arc near the top third)
    specs.append({"shape": "ellipse", "x": bx, "y": top + (body_bot - top) * 0.34,
                  "w": bw, "h": rim, "stroke": DARK, "fill": "none",
                  "width": W_DET})
    return specs


def build_storage(w, h):
    """A NAS/disk array — a box with several drive-bay slots."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.10 * w, "y": 0.12 * h,
                  "w": 0.80 * w, "h": 0.76 * h, "radius": 0.03 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    bays = 4
    top = 0.18 * h
    bot = 0.82 * h
    bh = (bot - top) / bays
    for i in range(bays):
        by = top + i * bh
        specs.append({"shape": "rect", "x": 0.18 * w, "y": by + 0.015 * h,
                      "w": 0.64 * w, "h": bh - 0.03 * h,
                      "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
        specs.append({"shape": "circle", "x": 0.72 * w,
                      "y": by + bh / 2 - 0.025 * w,
                      "w": 0.05 * w, "h": 0.05 * w,
                      "stroke": OUTLINE, "fill": DARK, "width": W_DET})
    return specs


def build_load_balancer(w, h):
    """A box with one inbound arrow splitting to two outbound arrows."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.22 * w, "y": 0.34 * h,
                  "w": 0.56 * w, "h": 0.32 * h, "radius": 0.05 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "arrow", "x1": 0.02 * w, "y1": 0.50 * h,
                  "x2": 0.22 * w, "y2": 0.50 * h,
                  "stroke": DARK, "width": W_OUT})
    specs.append({"shape": "arrow", "x1": 0.78 * w, "y1": 0.50 * h,
                  "x2": 0.98 * w, "y2": 0.18 * h,
                  "stroke": DARK, "width": W_OUT})
    specs.append({"shape": "arrow", "x1": 0.78 * w, "y1": 0.50 * h,
                  "x2": 0.98 * w, "y2": 0.82 * h,
                  "stroke": DARK, "width": W_OUT})
    specs.append({"shape": "diamond", "x": 0.42 * w, "y": 0.42 * h,
                  "w": 0.16 * w, "h": 0.16 * h, "rotation": 0.0,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    return specs


# --------------------------------------------------------------------------
# Network
# --------------------------------------------------------------------------

def build_router(w, h):
    """A flat box with 4 directional arrows on top (classic router icon)."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.14 * w, "y": 0.40 * h,
                  "w": 0.72 * w, "h": 0.46 * h, "radius": 0.05 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    cx, cy = 0.50 * w, 0.20 * h
    r = 0.16 * w
    rv = 0.16 * h
    specs.append({"shape": "arrow", "x1": cx, "y1": cy, "x2": cx, "y2": cy - rv,
                  "stroke": DARK, "width": W_OUT})
    specs.append({"shape": "arrow", "x1": cx, "y1": cy, "x2": cx, "y2": cy + rv,
                  "stroke": DARK, "width": W_OUT})
    specs.append({"shape": "arrow", "x1": cx, "y1": cy, "x2": cx - r, "y2": cy,
                  "stroke": DARK, "width": W_OUT})
    specs.append({"shape": "arrow", "x1": cx, "y1": cy, "x2": cx + r, "y2": cy,
                  "stroke": DARK, "width": W_OUT})
    specs.append({"shape": "circle", "x": 0.22 * w, "y": 0.50 * h,
                  "w": 0.05 * w, "h": 0.05 * w,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    specs.append({"shape": "circle", "x": 0.32 * w, "y": 0.50 * h,
                  "w": 0.05 * w, "h": 0.05 * w,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    return specs


def build_switch(w, h):
    """A flat box with several bidirectional arrow pairs across the top."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.08 * w, "y": 0.46 * h,
                  "w": 0.84 * w, "h": 0.42 * h, "radius": 0.05 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    ys_up = 0.06 * h
    ys_dn = 0.36 * h
    for fx in (0.22, 0.40, 0.58, 0.76):
        x = fx * w
        ox = 0.04 * w
        specs.append({"shape": "arrow", "x1": x - ox, "y1": ys_dn,
                      "x2": x - ox, "y2": ys_up,
                      "stroke": DARK, "width": W_OUT})
        specs.append({"shape": "arrow", "x1": x + ox, "y1": ys_up,
                      "x2": x + ox, "y2": ys_dn,
                      "stroke": DARK, "width": W_OUT})
    for fx in (0.18, 0.34, 0.50, 0.66, 0.82):
        specs.append({"shape": "rect", "x": fx * w - 0.03 * w, "y": 0.64 * h,
                      "w": 0.06 * w, "h": 0.10 * h,
                      "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    return specs


def build_firewall(w, h):
    """A brick-wall pattern with a small flame."""
    specs = []
    specs.append({"shape": "rect", "x": 0.10 * w, "y": 0.30 * h,
                  "w": 0.80 * w, "h": 0.62 * h,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    left = 0.10 * w
    right = 0.90 * w
    top = 0.30 * h
    bot = 0.92 * h
    rows = 4
    rh = (bot - top) / rows
    for i in range(1, rows):
        y = top + i * rh
        specs.append({"shape": "line", "x1": left, "y1": y,
                      "x2": right, "y2": y, "stroke": DARK, "width": W_DET})
    for i in range(rows):
        y0 = top + i * rh
        y1 = y0 + rh
        offset = 0.20 * (right - left) if i % 2 else 0.0
        x = left + offset
        step = 0.40 * (right - left)
        while x < right:
            if x > left:
                specs.append({"shape": "line", "x1": x, "y1": y0,
                              "x2": x, "y2": y1, "stroke": DARK,
                              "width": W_DET})
            x += step
    specs.append({"shape": "triangle", "x": 0.42 * w, "y": 0.04 * h,
                  "w": 0.16 * w, "h": 0.26 * h, "rotation": 0.0,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    return specs


def build_modem(w, h):
    """A small box with an antenna line and a couple of signal arcs."""
    specs = []
    specs.append({"shape": "rounded_rect", "x": 0.16 * w, "y": 0.50 * h,
                  "w": 0.68 * w, "h": 0.40 * h, "radius": 0.05 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    ax = 0.72 * w
    specs.append({"shape": "line", "x1": ax, "y1": 0.50 * h,
                  "x2": ax, "y2": 0.10 * h, "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "circle", "x": ax - 0.04 * w, "y": 0.04 * h,
                  "w": 0.08 * w, "h": 0.08 * w,
                  "stroke": OUTLINE, "fill": DARK, "width": W_DET})
    specs.append({"shape": "halfcircle", "x": 0.20 * w, "y": 0.18 * h,
                  "w": 0.28 * w, "h": 0.20 * h, "rotation": 0.0,
                  "stroke": DARK, "fill": "none", "width": W_DET})
    specs.append({"shape": "halfcircle", "x": 0.26 * w, "y": 0.26 * h,
                  "w": 0.16 * w, "h": 0.14 * h, "rotation": 0.0,
                  "stroke": DARK, "fill": "none", "width": W_DET})
    specs.append({"shape": "circle", "x": 0.24 * w, "y": 0.64 * h,
                  "w": 0.06 * w, "h": 0.06 * w,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    specs.append({"shape": "circle", "x": 0.36 * w, "y": 0.64 * h,
                  "w": 0.06 * w, "h": 0.06 * w,
                  "stroke": OUTLINE, "fill": ACCENT, "width": W_DET})
    return specs


def build_wifi_ap(w, h):
    """A base dot with 3 concentric expanding arcs — wifi waves."""
    specs = []
    cx = 0.50 * w
    by = 0.86 * h
    specs.append({"shape": "circle", "x": cx - 0.07 * w, "y": by - 0.07 * w,
                  "w": 0.14 * w, "h": 0.14 * w,
                  "stroke": OUTLINE, "fill": DARK, "width": W_OUT})
    for i, rad in enumerate((0.24, 0.40, 0.56)):
        rw = rad * w
        rh = rad * h * 0.9
        specs.append({"shape": "halfcircle", "x": cx - rw, "y": by - rh,
                      "w": 2 * rw, "h": rh, "rotation": 0.0,
                      "stroke": ACCENT if i == 0 else DARK, "fill": "none",
                      "width": W_OUT})
    return specs


def build_cloud(w, h):
    """A cloud outline made of overlapping circles/ellipses, flat bottom."""
    specs = []
    base_y = 0.66 * h
    specs.append({"shape": "ellipse", "x": 0.10 * w, "y": 0.44 * h,
                  "w": 0.80 * w, "h": 0.40 * h,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "circle", "x": 0.08 * w, "y": 0.40 * h,
                  "w": 0.34 * w, "h": 0.34 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "circle", "x": 0.34 * w, "y": 0.22 * h,
                  "w": 0.40 * w, "h": 0.40 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "circle", "x": 0.60 * w, "y": 0.38 * h,
                  "w": 0.32 * w, "h": 0.32 * w,
                  "stroke": OUTLINE, "fill": DEVICE, "width": W_OUT})
    specs.append({"shape": "rect", "x": 0.12 * w, "y": base_y,
                  "w": 0.76 * w, "h": 0.16 * h,
                  "stroke": "none", "fill": DEVICE, "width": W_DET})
    specs.append({"shape": "line", "x1": 0.12 * w, "y1": base_y + 0.16 * h,
                  "x2": 0.88 * w, "y2": base_y + 0.16 * h,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------

REFERENCE_MM = 1600.0

SIZES = {
    "desktop": (160.0, 150.0),
    "laptop": (180.0, 130.0),
    "mobile": (110.0, 200.0),
    "user": (140.0, 160.0),
    "printer": (160.0, 160.0),
    "server": (150.0, 220.0),
    "database": (160.0, 180.0),
    "storage": (170.0, 170.0),
    "load_balancer": (200.0, 150.0),
    "router": (170.0, 150.0),
    "switch": (190.0, 150.0),
    "firewall": (170.0, 170.0),
    "modem": (150.0, 170.0),
    "wifi_ap": (180.0, 150.0),
    "cloud": (220.0, 160.0),
}

LABELS = {
    "desktop": "Desktop",
    "laptop": "Laptop",
    "mobile": "Mobile",
    "user": "User",
    "printer": "Printer",
    "server": "Server",
    "database": "Database",
    "storage": "Storage",
    "load_balancer": "Load balancer",
    "router": "Router",
    "switch": "Switch",
    "firewall": "Firewall",
    "modem": "Modem",
    "wifi_ap": "Wi-Fi AP",
    "cloud": "Cloud",
}

CATEGORIES = [
    ("Endpoints", ["desktop", "laptop", "mobile", "user", "printer"]),
    ("Infrastructure", ["server", "database", "storage", "load_balancer"]),
    ("Network", ["router", "switch", "firewall", "modem", "wifi_ap",
                 "cloud"]),
]


_BUILDERS = {name: globals()["build_" + name] for name in SIZES}


def build_specs(name, w, h):
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
