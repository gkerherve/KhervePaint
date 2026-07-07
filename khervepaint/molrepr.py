"""2D chemical representations of a molecule graph.

The same (atoms, bonds) that back a 3D ball-and-stick model can also be
drawn as flat chemistry diagrams — the styles in a typical textbook figure:

* ``structural`` — a skeletal drawing: element letters joined by bond lines
  (single/double/triple), every atom shown.
* ``lewis`` — the structural drawing plus lone-pair dots on each atom.
* ``condensed`` — the molecular formula in Hill notation (e.g. C₂H₆O).

Each returns a list of shape-spec dicts (the AI/library format), so the
scene turns them into ordinary editable items just like the 3D model. 2D
coordinates come from whichever orthographic view spreads the atoms out
most, so planar molecules read cleanly.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtGui import QColor

from . import molecules

#: The representation modes, in menu order.
MODES = ["3d", "structural", "lewis", "condensed"]
MODE_LABELS = {"3d": "3D ball-and-stick", "structural": "Structural formula",
               "lewis": "Lewis structure", "condensed": "Condensed formula"}

_INK = "#1a1a1a"
#: Valence electrons per element, for counting lone pairs in Lewis mode.
_VALENCE_E = {"H": 1, "B": 3, "C": 4, "N": 5, "O": 6, "F": 7, "Si": 4,
              "P": 5, "S": 6, "Cl": 7, "Br": 7, "I": 7}


def _best_view(atoms):
    """2D atom coords from the orthographic view that spreads them out most
    (so planar molecules are shown face-on)."""
    best = None
    for az, el in [(0.0, 0.0), (math.pi / 2, 0.0), (0.0, math.pi / 2),
                   (math.pi / 4, math.pi / 6), (math.pi / 3, 0.0),
                   (0.0, math.pi / 4), (math.pi / 5, math.pi / 5)]:
        pj = [molecules._proj(a[1], a[2], a[3], az, el) for a in atoms]
        xs = [p[0] for p in pj]
        ys = [p[1] for p in pj]
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if best is None or area > best[0]:
            best = (area, [(p[0], p[1]) for p in pj])
    return best[1]


def _layout(atoms, w, h, margin=0.14):
    """Fit the best-view 2D coords into the (w, h) box; return placed points
    and the scale used."""
    pts = _best_view(atoms)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    spanx = (maxx - minx) or 1.0
    spany = (maxy - miny) or 1.0
    m = margin * min(w, h)
    s = min((w - 2 * m) / spanx, (h - 2 * m) / spany)
    ox = (w - s * spanx) / 2.0 - s * minx
    oy = (h - s * spany) / 2.0 - s * miny
    return [(ox + s * x, oy + s * y) for x, y in pts], s


def _label_color(element):
    """A readable letter colour on a white page: C and H are black (the
    usual convention), heteroatoms keep their CPK colour but pale ones
    (H's white, F's light green…) are darkened so they don't vanish."""
    if element in ("C", "H"):
        return _INK
    cpk = molecules.ATOM_COLORS.get(element, _INK)
    return molecules._mix(cpk, "#000000", 0.45) \
        if QColor(cpk).lightnessF() > 0.5 else cpk


def _lone_pairs(element, order_sum):
    ve = _VALENCE_E.get(element)
    if ve is None:
        return 0
    return max(0, (ve - order_sum) // 2)


def structural_specs(atoms, bonds, w, h, lewis=False):
    """Skeletal structural formula (optionally with Lewis lone-pair dots)."""
    pts, s = _layout(atoms, w, h)
    fs = max(9.0, s * 0.42)                 # label font size
    gap = fs * 0.95                         # bond gap around a label
    lw = max(1.4, s * 0.05)
    dbl = max(2.0, s * 0.10)                # double/triple line separation
    specs = []
    # --- bonds (drawn first, behind the labels) ---
    for i, j, order in bonds:
        (x1, y1), (x2, y2) = pts[i], pts[j]
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        ax, ay = x1 + ux * gap, y1 + uy * gap        # trim to leave room
        bx, by = x2 - ux * gap, y2 - uy * gap
        px, py = -uy, ux
        rows = {1: [0.0], 2: [-1.0, 1.0], 3: [-1.0, 0.0, 1.0]}.get(order, [0.0])
        for o in rows:
            specs.append({"shape": "line", "x1": ax + px * o * dbl,
                          "y1": ay + py * o * dbl, "x2": bx + px * o * dbl,
                          "y2": by + py * o * dbl, "stroke": _INK,
                          "width": lw})
    # --- atom labels (white halo circle + element letter) ---
    order_sum = [0] * len(atoms)
    for i, j, order in bonds:
        order_sum[i] += order
        order_sum[j] += order
    for idx, (cx, cy) in enumerate(pts):
        element = atoms[idx][0]
        r = fs * (0.5 if element == "H" else 0.66)
        specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                      "w": 2 * r, "h": 2 * r, "stroke": "none",
                      "fill": "#ffffff"})
        specs.append({"shape": "text", "text": element, "x": cx, "y": cy,
                      "anchor": "center", "size": int(fs),
                      "color": _label_color(element)})
        if lewis:
            specs += _lewis_dots(idx, pts, bonds, element, order_sum[idx],
                                 r, fs)
    return specs


def _lewis_dots(idx, pts, bonds, element, order_sum, r, fs):
    """Lone-pair dots placed on the sides of an atom not used by a bond."""
    pairs = _lone_pairs(element, order_sum)
    if pairs <= 0:
        return []
    cx, cy = pts[idx]
    used = []
    for i, j, _o in bonds:
        k = j if i == idx else (i if j == idx else None)
        if k is not None:
            used.append(math.atan2(pts[k][1] - cy, pts[k][0] - cx))
    # candidate directions every 45°, farthest from any bond
    cands = [math.radians(a) for a in range(0, 360, 30)]

    def clear(a):
        return min(abs((a - u + math.pi) % (2 * math.pi) - math.pi)
                   for u in used) if used else math.pi
    cands.sort(key=clear, reverse=True)
    dot = max(1.2, fs * 0.09)
    dd = fs * 0.22                          # spacing of the two dots in a pair
    specs = []
    for a in cands[:pairs]:
        bx, by = cx + math.cos(a) * (r + dot * 1.6), cy + math.sin(a) * (r + dot * 1.6)
        tx, ty = -math.sin(a), math.cos(a)
        for sgn in (-1.0, 1.0):
            dx, dy = bx + tx * dd * sgn, by + ty * dd * sgn
            specs.append({"shape": "circle", "x": dx - dot, "y": dy - dot,
                          "w": 2 * dot, "h": 2 * dot, "stroke": "none",
                          "fill": _INK})
    return specs


def molecular_formula(atoms):
    """Hill-notation molecular formula string (C, then H, then alphabetical)."""
    counts = {}
    for a in atoms:
        counts[a[0]] = counts.get(a[0], 0) + 1
    order = []
    if "C" in counts:
        order.append("C")
        if "H" in counts:
            order.append("H")
    for el in sorted(counts):
        if el not in ("C", "H") or "C" not in counts:
            if el not in order:
                order.append(el)
    subs = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    out = ""
    for el in order:
        n = counts[el]
        out += el + (str(n).translate(subs) if n > 1 else "")
    return out


def condensed_specs(atoms, bonds, w, h):
    """The molecular formula as a single large centred text item."""
    formula = molecular_formula(atoms)
    return [{"shape": "text", "text": formula, "x": w / 2.0, "y": h / 2.0,
             "anchor": "center", "size": int(max(18, min(w, h) * 0.22)),
             "color": _INK}]


def representation_specs(mode, atoms, bonds, w, h):
    """Shape specs for *mode* — the 2D chemistry diagrams (the 3D mode is
    handled by molecules._model / specs_from_atoms)."""
    if mode == "structural":
        return structural_specs(atoms, bonds, w, h)
    if mode == "lewis":
        return structural_specs(atoms, bonds, w, h, lewis=True)
    if mode == "condensed":
        return condensed_specs(atoms, bonds, w, h)
    return []
