"""3D-schematic building blocks: slabs, particle beds, glows and trails.

The pieces of a layered device schematic — a fuel cell, battery, membrane
or thin-film stack drawn the way papers draw them: electrolyte layers as
shaded **3D slabs / disks**, porous electrodes as beds of **close-packed
lit spheres**, plus the annotation sprites (soft **glow** for a reaction
hot-spot, **active-site** dots, a dotted **ion trail**). Combine with the
Molecules palette (O₂/H₂/H₂O ball models), the Arrows palette (flow and
reaction arrows) and text to reproduce a full PCFC-style figure.

Same `build_specs`/`size_mm` interface as `floorplan`/`electrical`; every
symbol drops as an ordinary editable, resizable group. Spheres reuse the
lit-sphere gradient from `molecules`, so beds match the molecule models.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from .molecules import _mix, atom_specs

#: Sphere/bed palette (light grey, dark grey, blue, green, white).
_SPHERE_COLORS = {
    "grey": "#d8dade", "dark": "#565a61", "blue": "#4046a8",
    "green": "#3faf62", "white": "#f4f4f4",
}
#: Slab palette (electrolyte / substrate blocks).
_SLAB_COLORS = {
    "grey": "#b9bdc4", "orange": "#d59a6e", "blue": "#63b6e0",
}


# ------------------------------------------------------------- 3D blocks
def _slab(w, h, color):
    """A 3D box: front face + right-shifted top face + right side face,
    shaded lighter on top and darker on the side."""
    skew = w * 0.14                     # top-face depth (x offset)
    depth = h * 0.30                    # top-face height (y drop)
    top = _mix(color, "#ffffff", 0.35)
    side = _mix(color, "#000000", 0.25)
    edge = _mix(color, "#000000", 0.55)
    fw = w - skew                       # front face width
    return [
        {"shape": "polygon", "stroke": edge, "width": 1.6, "fill": top,
         "points": [[0, depth], [skew, 0], [w, 0], [fw, depth]]},
        {"shape": "rect", "x": 0, "y": depth, "w": fw, "h": h - depth,
         "stroke": edge, "width": 1.6, "fill": color},
        {"shape": "polygon", "stroke": edge, "width": 1.6, "fill": side,
         "points": [[fw, depth], [w, 0], [w, h - depth], [fw, h]]},
    ]


def build_slab_grey(w, h):
    return _slab(w, h, _SLAB_COLORS["grey"])


def build_slab_orange(w, h):
    return _slab(w, h, _SLAB_COLORS["orange"])


def build_slab_blue(w, h):
    return _slab(w, h, _SLAB_COLORS["blue"])


def build_disk_grey(w, h):
    """A 3D disc (short cylinder seen slightly from above), like the
    electrolyte pellet in a button-cell schematic."""
    color = _SLAB_COLORS["grey"]
    top = _mix(color, "#ffffff", 0.35)
    edge = _mix(color, "#000000", 0.55)
    cap = h * 0.42                      # ellipse height
    return [
        {"shape": "ellipse", "x": 0, "y": h - cap, "w": w, "h": cap,
         "stroke": edge, "width": 1.6, "fill": color},
        {"shape": "rect", "x": 0, "y": cap / 2, "w": w, "h": h - cap,
         "stroke": "none", "fill": color},
        {"shape": "line", "x1": 0, "y1": cap / 2, "x2": 0, "y2": h - cap / 2,
         "stroke": edge, "width": 1.6},
        {"shape": "line", "x1": w, "y1": cap / 2, "x2": w, "y2": h - cap / 2,
         "stroke": edge, "width": 1.6},
        {"shape": "ellipse", "x": 0, "y": 0, "w": w, "h": cap,
         "stroke": edge, "width": 1.6, "fill": top},
    ]


# --------------------------------------------------------- particle beds
def _sphere_row(y, w, r, color, n, offset=0.0):
    specs = []
    for i in range(n):
        cx = r + offset + i * 2 * r * 0.96          # slight overlap
        if cx + r * 0.5 > w + r:
            break
        specs += atom_specs(cx, y, r, "", color=color)
    return specs


def _bed(w, h, color, rows=3):
    """Close-packed staggered sphere rows — a porous electrode layer.
    Drawn bottom row first so upper rows overlap like a real pile."""
    r = h / (1 + (rows - 1) * 0.82) / 2
    specs = []
    for k in range(rows - 1, -1, -1):               # back/bottom rows first
        y = h - r - k * 2 * r * 0.82
        specs += _sphere_row(y, w, r, color, int(w / (2 * r * 0.96)) + 1,
                             offset=(r * 0.96 if k % 2 else 0.0))
    return specs


def _row(w, h, color):
    r = h / 2
    return _sphere_row(r, w, r, color, int(w / (2 * r * 0.96)) + 1)


def _make_bed(color_key):
    return lambda w, h: _bed(w, h, _SPHERE_COLORS[color_key])


def _make_row(color_key):
    return lambda w, h: _row(w, h, _SPHERE_COLORS[color_key])


def _make_sphere(color_key):
    return lambda w, h: atom_specs(w / 2, h / 2, min(w, h) / 2, "",
                                   color=_SPHERE_COLORS[color_key])


# ------------------------------------------------------ reaction details
def _glow(w, h, color):
    """A soft reaction hot-spot: concentric translucent circles."""
    cx, cy = w / 2, h / 2
    specs = []
    for frac, op in ((1.0, 0.22), (0.72, 0.42), (0.45, 0.85)):
        r = min(w, h) / 2 * frac
        specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                      "w": 2 * r, "h": 2 * r, "stroke": "none",
                      "fill": color, "opacity": op})
    return specs


def build_glow_blue(w, h):
    return _glow(w, h, "#3aa5f0")


def build_glow_orange(w, h):
    return _glow(w, h, "#f08a1d")


def build_glow_yellow(w, h):
    return _glow(w, h, "#f4c81f")


def build_active_site(w, h):
    """A pinch of small gold dots marking a catalytic active site."""
    dots = [(0.10, 0.55), (0.28, 0.30), (0.46, 0.62), (0.62, 0.25),
            (0.78, 0.55), (0.92, 0.35)]
    r = min(w, h) * 0.16
    return [{"shape": "circle", "x": fx * w - r, "y": fy * h - r,
             "w": 2 * r, "h": 2 * r, "stroke": "#a67c00", "width": 0.8,
             "fill": "#f2c230"} for fx, fy in dots]


def build_proton_trail(w, h):
    """A dotted ion-conduction trail (vertical, gently wiggling)."""
    n = max(int(h / (w * 0.55)), 6)
    r = w * 0.22
    specs = []
    for i in range(n):
        t = i / max(n - 1, 1)
        fx = 0.5 + 0.30 * (1 if i % 2 else -1) * (0.4 + 0.6 * (1 - t))
        cx, cy = fx * w, h - t * h
        specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                      "w": 2 * r, "h": 2 * r, "stroke": "none",
                      "fill": "#f2a0c0"})
    return specs


# --------------------------------------------------------------- registry
_BUILDERS = {
    "slab_grey": build_slab_grey, "slab_orange": build_slab_orange,
    "slab_blue": build_slab_blue, "disk_grey": build_disk_grey,
    "glow_blue": build_glow_blue, "glow_orange": build_glow_orange,
    "glow_yellow": build_glow_yellow, "active_site": build_active_site,
    "proton_trail": build_proton_trail,
}
for _key in _SPHERE_COLORS:
    _BUILDERS[f"bed_{_key}"] = _make_bed(_key)
    _BUILDERS[f"row_{_key}"] = _make_row(_key)
    _BUILDERS[f"sphere_{_key}"] = _make_sphere(_key)

REFERENCE_MM = 130.0
SIZES = {
    "slab_grey": (100, 30), "slab_orange": (100, 30), "slab_blue": (100, 30),
    "disk_grey": (100, 26),
    "glow_blue": (16, 16), "glow_orange": (16, 16), "glow_yellow": (16, 16),
    "active_site": (14, 8), "proton_trail": (8, 36),
}
for _key in _SPHERE_COLORS:
    SIZES[f"bed_{_key}"] = (96, 26)
    SIZES[f"row_{_key}"] = (96, 10)
    SIZES[f"sphere_{_key}"] = (12, 12)

_COLOR_LABELS = {"grey": "grey", "dark": "dark grey", "blue": "blue",
                 "green": "green", "white": "white"}
LABELS = {
    "slab_grey": "Slab — grey", "slab_orange": "Slab — orange",
    "slab_blue": "Slab — blue", "disk_grey": "Disk (3D)",
    "glow_blue": "Glow — blue", "glow_orange": "Glow — orange",
    "glow_yellow": "Glow — yellow", "active_site": "Active-site dots",
    "proton_trail": "Ion trail (dotted)",
}
for _key, _lab in _COLOR_LABELS.items():
    LABELS[f"bed_{_key}"] = f"Particle bed — {_lab}"
    LABELS[f"row_{_key}"] = f"Particle row — {_lab}"
    LABELS[f"sphere_{_key}"] = f"Sphere — {_lab}"

CATEGORIES = [
    ("3D blocks", ["slab_grey", "slab_orange", "slab_blue", "disk_grey"]),
    ("Particle beds", [f"bed_{k}" for k in _SPHERE_COLORS]
     + [f"row_{k}" for k in _SPHERE_COLORS]),
    ("Spheres", [f"sphere_{k}" for k in _SPHERE_COLORS]),
    ("Reaction details", ["glow_blue", "glow_orange", "glow_yellow",
                          "active_site", "proton_trail"]),
]


def build_specs(name, w, h):
    """Shape specs for *name* drawn into a (w, h) px box."""
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
