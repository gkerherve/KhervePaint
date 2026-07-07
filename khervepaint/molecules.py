"""Molecular models: ball-and-stick molecules and crystal unit cells.

Atoms are drawn as sun-lit spheres (a circle with a `sun` gradient in the
element's CPK colour, so they read as 3D balls) and bonds as grey sticks.
Each `build_<name>(w, h)` returns a list of shape-spec dicts (the same
format the AI assistant / examples use); the scene turns them into native,
editable items via `ai_assistant._spec_to_item` and drops them, grouped,
where you click — exactly like `floorplan`/`electrical`.

The "3D look" comes from an isometric projection: a molecule (or crystal)
is described by its atoms' 3D coordinates, projected to the drawing plane
and drawn far-to-near so nearer spheres overlap farther ones. Because the
result is ordinary vector items, everything stays editable, selectable and
savable.

The same `atom_specs`/`bond_specs` helpers back the high-level `atom` and
`bond` shape specs the AI can emit (expanded by `expand_specs`), so the
model can build arbitrary molecules and 3D structures on request.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtGui import QColor

# --------------------------------------------------------------- element data
#: CPK-ish body colour per element (the sphere's mid tone).
ATOM_COLORS = {
    "H": "#f4f4f4", "C": "#3a3a3a", "N": "#3050f8", "O": "#e01f1f",
    "F": "#77d84a", "Cl": "#37c837", "Br": "#a1443c", "I": "#8f2fbf",
    "P": "#ff8000", "S": "#e6c72a", "B": "#f0a0a0", "Si": "#b89078",
    "Na": "#9a54e0", "K": "#7d38cc", "Mg": "#63d84b", "Ca": "#3dc23d",
    "Fe": "#e06633", "Zn": "#7d80b0", "Cu": "#c86a3a", "Al": "#b0b0c0",
    "Ti": "#9aa0a6", "Cs": "#57178f",
}

#: Relative ball radius per element (tuned for a ball-and-stick look, not
#: physically exact — H clearly smaller, halogens/metals larger).
ATOM_RADII = {
    "H": 0.36, "C": 0.58, "N": 0.56, "O": 0.55, "F": 0.52,
    "Cl": 0.74, "Br": 0.82, "I": 0.92, "P": 0.78, "S": 0.76,
    "B": 0.62, "Si": 0.80, "Na": 0.95, "K": 1.05, "Mg": 0.80,
    "Ca": 0.98, "Fe": 0.80, "Zn": 0.80, "Cu": 0.80, "Al": 0.82,
    "Ti": 0.84, "Cs": 1.15,
}

_BOND_COLOR = "#6b6f76"
_FRAME_COLOR = "#202020"         # solid unit-cell cube edges (thick, dark)
_EDGE_COLOR = "#555555"          # dashed body/face diagonals

# ------------------------------------------------------------ colour helpers
def _mix(a, b, t):
    """Blend hex colour *a* toward *b* by fraction *t* (0..1)."""
    ca, cb = QColor(a), QColor(b)
    r = round(ca.red() + (cb.red() - ca.red()) * t)
    g = round(ca.green() + (cb.green() - ca.green()) * t)
    bl = round(ca.blue() + (cb.blue() - ca.blue()) * t)
    return "#%02x%02x%02x" % (r, g, bl)


def atom_specs(cx, cy, r, element, label=False):
    """A single lit-sphere spec for *element* centred at (cx, cy), radius r.

    The sphere is a circle filled with a `sun` gradient: a near-white
    highlight at the top-left fading to a darkened rim, so it reads as a
    3D ball in the element's CPK colour."""
    body = ATOM_COLORS.get(element, "#c8c8c8")
    hi = _mix(body, "#ffffff", 0.62)
    rim = _mix(body, "#000000", 0.40)
    stroke = _mix(body, "#000000", 0.52)
    spec = {"shape": "circle", "x": cx - r, "y": cy - r,
            "w": 2 * r, "h": 2 * r, "stroke": stroke,
            "width": max(0.8, r * 0.10),
            "fill": {"kind": "sun", "c1": rim, "c2": hi}}
    if label:
        spec["label"] = element
    return [spec]


def bond_specs(p1, p2, order=1, width=6.0, color=_BOND_COLOR):
    """Stick spec(s) between 2D points *p1* and *p2*.

    Single/double/triple bonds are one/two/three parallel lines offset
    perpendicular to the bond; multi-bond lines are drawn thinner."""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return []
    px, py = -dy / length, dx / length          # unit perpendicular
    if order <= 1:
        rows, lw, sep = [0.0], width, 0.0
    elif order == 2:
        rows, lw, sep = [-1.0, 1.0], width * 0.62, width * 0.85
    else:
        rows, lw, sep = [-1.0, 0.0, 1.0], width * 0.52, width * 1.0
    out = []
    for o in rows:
        ox, oy = px * o * sep, py * o * sep
        out.append({"shape": "line", "x1": x1 + ox, "y1": y1 + oy,
                    "x2": x2 + ox, "y2": y2 + oy,
                    "stroke": color, "width": lw})
    return out


# ------------------------------------------------------- isometric projection
#: Viewing angles (azimuth about the vertical axis, then elevation tilt).
_AZ = math.radians(28.0)
_EL = math.radians(20.0)
#: Default viewing angles (azimuth about the vertical axis, elevation tilt).
DEFAULT_AZ = _AZ
DEFAULT_EL = _EL


def _proj(x, y, z, az=_AZ, el=_EL):
    """Project a 3D point to (screen_x, screen_y, depth) at view (az, el).

    Rotate about the vertical axis by *az*, tilt by *el*, then project
    orthographically. *depth* grows toward the viewer, so sorting atoms by
    it draws far spheres before near ones."""
    ca, sa = math.cos(az), math.sin(az)
    ce, se = math.cos(el), math.sin(el)
    xr = x * ca - y * sa
    yr = x * sa + y * ca
    sx = xr
    sy = yr * se - z * ce            # screen y (grows downward)
    depth = yr * ce + z * se         # toward the viewer
    return sx, sy, depth


def _dashed_line(p1, p2, color, width, dash=6.0, gap=4.0):
    """A dashed segment as a run of short solid line specs (so the dashes
    are geometry that survives SVG, like the chemistry H-bond)."""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    out = []
    pos = 0.0
    while pos < length:
        end = min(pos + dash, length)
        out.append({"shape": "line", "x1": x1 + ux * pos, "y1": y1 + uy * pos,
                    "x2": x1 + ux * end, "y2": y1 + uy * end,
                    "stroke": color, "width": width})
        pos = end + gap
    return out


def _spread(atoms, edges, factor):
    """Move atoms (and cell edges) apart from their centroid by *factor*,
    lengthening the bonds relative to the spheres. rscale is unchanged, so
    only the ball-to-stick ratio moves — bigger factor = longer bonds."""
    if factor == 1.0 or not atoms:
        return atoms, edges
    cx = sum(a[1] for a in atoms) / len(atoms)
    cy = sum(a[2] for a in atoms) / len(atoms)
    cz = sum(a[3] for a in atoms) / len(atoms)

    def sc(p):
        return (cx + (p[0] - cx) * factor, cy + (p[1] - cy) * factor,
                cz + (p[2] - cz) * factor)
    at = [(a[0], *sc((a[1], a[2], a[3]))) for a in atoms]
    ed = None
    if edges:
        ed = [(sc(e[0]), sc(e[1]), e[2] if len(e) > 2 else "solid")
              for e in edges]
    return at, ed


def _model(atoms, bonds, w, h, edges=None, rscale=1.0, labels=False,
           margin=0.12, az=_AZ, el=_EL, bond_scale=1.0):
    """Lay out a 3D model into the (w, h) box and return its shape specs.

    *atoms* is a list of ``(element, x, y, z)``; *bonds* a list of
    ``(i, j, order)`` index pairs; *edges* an optional list of
    ``(p1, p2)`` or ``(p1, p2, style)`` unit-cell segments where *style*
    is ``"solid"`` (a thick dark cube edge) or ``"dash"`` (a dashed body
    diagonal). *bond_scale* spreads the atoms apart to lengthen the bonds.
    The projected model is scaled uniformly (spheres stay round) to fit the
    box, then drawn back-to-front: edges, bonds, spheres."""
    atoms, edges = _spread(atoms, edges, bond_scale)
    proj = [_proj(a[1], a[2], a[3], az, el) for a in atoms]
    rad = [ATOM_RADII.get(a[0], 0.55) * rscale for a in atoms]

    xs_lo = [proj[i][0] - rad[i] for i in range(len(atoms))]
    xs_hi = [proj[i][0] + rad[i] for i in range(len(atoms))]
    ys_lo = [proj[i][1] - rad[i] for i in range(len(atoms))]
    ys_hi = [proj[i][1] + rad[i] for i in range(len(atoms))]
    pedges = []
    if edges:
        for e in edges:
            style = e[2] if len(e) > 2 else "solid"
            pa = _proj(*e[0], az, el)
            pb = _proj(*e[1], az, el)
            pedges.append((pa, pb, style))
            for px, py, _ in (pa, pb):
                xs_lo.append(px); xs_hi.append(px)
                ys_lo.append(py); ys_hi.append(py)

    minx, maxx = min(xs_lo), max(xs_hi)
    miny, maxy = min(ys_lo), max(ys_hi)
    spanx = (maxx - minx) or 1.0
    spany = (maxy - miny) or 1.0
    m = margin * min(w, h)
    s = min((w - 2 * m) / spanx, (h - 2 * m) / spany)
    ox = (w - s * spanx) / 2.0 - s * minx
    oy = (h - s * spany) / 2.0 - s * miny

    def T(px, py):
        return ox + s * px, oy + s * py

    specs = []
    ew = max(2.2, s * 0.062)
    for pa, pb, style in pedges:
        p1, p2 = T(pa[0], pa[1]), T(pb[0], pb[1])
        if style == "dash":
            specs += _dashed_line(p1, p2, _EDGE_COLOR, max(1.0, s * 0.028),
                                  dash=s * 0.10, gap=s * 0.07)
        else:
            specs.append({"shape": "line", "x1": p1[0], "y1": p1[1],
                          "x2": p2[0], "y2": p2[1], "stroke": _FRAME_COLOR,
                          "width": ew})
    bw = max(2.0, s * 0.11)
    for i, j, order in bonds:
        specs += bond_specs(T(proj[i][0], proj[i][1]),
                            T(proj[j][0], proj[j][1]), order, width=bw)
    for idx in sorted(range(len(atoms)), key=lambda k: proj[k][2]):
        cx, cy = T(proj[idx][0], proj[idx][1])
        specs += atom_specs(cx, cy, rad[idx] * s, atoms[idx][0], label=labels)
    return specs


# ------------------------------------------------------- geometry generators
_INV3 = 1.0 / math.sqrt(3.0)
#: The four sp3 tetrahedral directions (unit vectors).
_TETRA = [(_INV3, _INV3, _INV3), (_INV3, -_INV3, -_INV3),
          (-_INV3, _INV3, -_INV3), (-_INV3, -_INV3, _INV3)]


def _add(atoms, el, p):
    atoms.append((el, p[0], p[1], p[2]))
    return len(atoms) - 1


def _scale(v, k):
    return (v[0] * k, v[1] * k, v[2] * k)


def _plus(p, v):
    return (p[0] + v[0], p[1] + v[1], p[2] + v[2])


# --- small molecules -------------------------------------------------------
def _mol_water():
    a = math.radians(52.25)
    o = (0.0, 0.0, 0.0)
    atoms, bonds = [], []
    i_o = _add(atoms, "O", o)
    for sx in (1, -1):
        h = (0.96 * math.sin(a) * sx, 0.96 * math.cos(a), 0.0)
        bonds.append((i_o, _add(atoms, "H", h), 1))
    return atoms, bonds, None


def _mol_ammonia():
    atoms, bonds = [], []
    i_n = _add(atoms, "N", (0.0, 0.0, 0.0))
    for k in range(3):
        ang = math.radians(90 + k * 120)
        h = (0.82 * math.cos(ang), 0.82 * math.sin(ang), -0.40)
        bonds.append((i_n, _add(atoms, "H", h), 1))
    return atoms, bonds, None


def _mol_methane():
    atoms, bonds = [], []
    i_c = _add(atoms, "C", (0.0, 0.0, 0.0))
    for d in _TETRA:
        bonds.append((i_c, _add(atoms, "H", _scale(d, 1.09)), 1))
    return atoms, bonds, None


def _mol_carbon_dioxide():
    atoms, bonds = [], []
    i_c = _add(atoms, "C", (0.0, 0.0, 0.0))
    for sx in (1, -1):
        bonds.append((i_c, _add(atoms, "O", (1.16 * sx, 0.0, 0.0)), 2))
    return atoms, bonds, None


def _methyl(atoms, bonds, base_i, base_p, skip_dir):
    """Cap carbon *base_i* at *base_p* with 3 H along the tetra dirs that
    are not *skip_dir* (the direction already used by its heavy bond)."""
    best = max(range(4), key=lambda k: (_TETRA[k][0] * skip_dir[0]
                                        + _TETRA[k][1] * skip_dir[1]
                                        + _TETRA[k][2] * skip_dir[2]))
    for k in range(4):
        if k == best:
            continue
        bonds.append((base_i, _add(atoms, "H",
                                   _plus(base_p, _scale(_TETRA[k], 1.09))), 1))


def _mol_methanol():
    atoms, bonds = [], []
    c = (0.0, 0.0, 0.0)
    i_c = _add(atoms, "C", c)
    o = _plus(c, _scale(_TETRA[0], 1.43))
    i_o = _add(atoms, "O", o)
    bonds.append((i_c, i_o, 1))
    bonds.append((i_o, _add(atoms, "H", _plus(o, _scale(_TETRA[1], 0.96))), 1))
    _methyl(atoms, bonds, i_c, c, _TETRA[0])
    return atoms, bonds, None


def _mol_ethanol():
    atoms, bonds = [], []
    c1 = (0.0, 0.0, 0.0)
    i_c1 = _add(atoms, "C", c1)
    c2 = _plus(c1, _scale(_TETRA[0], 1.54))
    i_c2 = _add(atoms, "C", c2)
    bonds.append((i_c1, i_c2, 1))
    o = _plus(c2, _scale(_TETRA[1], 1.43))
    i_o = _add(atoms, "O", o)
    bonds.append((i_c2, i_o, 1))
    bonds.append((i_o, _add(atoms, "H", _plus(o, _scale(_TETRA[2], 0.96))), 1))
    # H on the two carbons (skip the bonds each already has)
    for k in (1, 2, 3):
        bonds.append((i_c1, _add(atoms, "H",
                                 _plus(c1, _scale(_TETRA[k], 1.09))), 1))
    for k in (2, 3):
        bonds.append((i_c2, _add(atoms, "H",
                                 _plus(c2, _scale(_TETRA[k], 1.09))), 1))
    return atoms, bonds, None


def _mol_formaldehyde():
    atoms, bonds = [], []
    c = (0.0, 0.0, 0.0)
    i_c = _add(atoms, "C", c)
    bonds.append((i_c, _add(atoms, "O", (0.0, 1.21, 0.0)), 2))
    for sx in (1, -1):
        bonds.append((i_c, _add(atoms, "H",
                                (1.0 * sx, -0.6, 0.0)), 1))
    return atoms, bonds, None


def _mol_acetic_acid():
    atoms, bonds = [], []
    c1 = (0.0, 0.0, 0.0)                       # methyl carbon
    i_c1 = _add(atoms, "C", c1)
    c2 = _plus(c1, _scale(_TETRA[0], 1.52))    # carboxyl carbon
    i_c2 = _add(atoms, "C", c2)
    bonds.append((i_c1, i_c2, 1))
    o_dbl = _plus(c2, (0.0, 1.22, 0.4))
    bonds.append((i_c2, _add(atoms, "O", o_dbl), 2))
    o_oh = _plus(c2, (1.30, -0.2, -0.2))
    i_o = _add(atoms, "O", o_oh)
    bonds.append((i_c2, i_o, 1))
    bonds.append((i_o, _add(atoms, "H", _plus(o_oh, (0.6, -0.7, 0.0))), 1))
    _methyl(atoms, bonds, i_c1, c1, _TETRA[0])
    return atoms, bonds, None


# --- rings and chains ------------------------------------------------------
def _ring_carbons(n, radius):
    """n carbons on a circle of *radius* in the xy-plane."""
    pts = []
    for k in range(n):
        ang = math.radians(90 + k * 360.0 / n)
        pts.append((radius * math.cos(ang), radius * math.sin(ang), 0.0))
    return pts


def _mol_benzene():
    atoms, bonds = [], []
    ring = _ring_carbons(6, 1.39)
    idx = [_add(atoms, "C", p) for p in ring]
    for k in range(6):
        bonds.append((idx[k], idx[(k + 1) % 6], 2 if k % 2 == 0 else 1))
        # radial H
        p = ring[k]
        d = math.hypot(p[0], p[1]) or 1.0
        hp = (p[0] * (d + 1.09) / d, p[1] * (d + 1.09) / d, 0.0)
        bonds.append((idx[k], _add(atoms, "H", hp), 1))
    return atoms, bonds, None


def _chair_ring(n, radius, pucker):
    pts = []
    for k in range(n):
        ang = math.radians(90 + k * 360.0 / n)
        z = pucker if k % 2 == 0 else -pucker
        pts.append((radius * math.cos(ang), radius * math.sin(ang), z))
    return pts


def _mol_cyclohexane():
    atoms, bonds = [], []
    ring = _chair_ring(6, 1.45, 0.35)
    idx = [_add(atoms, "C", p) for p in ring]
    for k in range(6):
        bonds.append((idx[k], idx[(k + 1) % 6], 1))
        p = ring[k]
        d = math.hypot(p[0], p[1]) or 1.0
        for zc in (0.85, -0.85):
            hp = (p[0] * (d + 0.7) / d, p[1] * (d + 0.7) / d, p[2] + zc)
            bonds.append((idx[k], _add(atoms, "H", hp), 1))
    return atoms, bonds, None


def _mol_glucose():
    """Pyranose ring (5 C + 1 O) with OH groups — a recognisable sugar."""
    atoms, bonds = [], []
    ring = _chair_ring(6, 1.45, 0.30)
    els = ["O", "C", "C", "C", "C", "C"]
    idx = [_add(atoms, els[k], ring[k]) for k in range(6)]
    for k in range(6):
        bonds.append((idx[k], idx[(k + 1) % 6], 1))
    # OH / CH2OH decorations on the carbons
    for k in range(1, 6):
        p = ring[k]
        d = math.hypot(p[0], p[1]) or 1.0
        op = (p[0] * (d + 1.4) / d, p[1] * (d + 1.4) / d, p[2] - 0.4)
        i_o = _add(atoms, "O", op)
        bonds.append((idx[k], i_o, 1))
        bonds.append((i_o, _add(atoms, "H", _plus(op, (0.4, 0.4, 0.6))), 1))
    return atoms, bonds, None


# --- hydrocarbon / polymer backbones --------------------------------------
#: Planar zig-zag spacing for an all-carbon sp3 backbone (~109.5°, 1.54 Å).
_ZA = 1.54 * math.sin(math.radians(54.75))   # step along x
_ZB = 1.54 * math.cos(math.radians(54.75))   # up/down amplitude


def _backbone(n, x0=0.0):
    """*n* sp3 carbons in a planar zig-zag along +x; return their points."""
    return [(x0 + k * _ZA, (_ZB if k % 2 else 0.0), 0.0) for k in range(n)]


def _backbone_hydrogens(atoms, bonds, idx, pts, subs=None):
    """Add the out-of-plane H's on each backbone carbon; *subs* maps a
    carbon index to a substituent (element or ('ring',) etc.) that replaces
    its upper H."""
    subs = subs or {}
    n = len(pts)
    for k in range(n):
        p = pts[k]
        ty = 0.55 if k % 2 == 0 else -0.55
        up = (p[0], p[1] + ty, 0.95)
        dn = (p[0], p[1] + ty, -0.95)
        # terminal carbons get an extra in-line H
        if k == 0 or k == n - 1:
            sign = -1.0 if k == 0 else 1.0
            ext = (p[0] + sign * 0.9, p[1] - (_ZB if k % 2 else 0.0) * 0.6, 0.0)
            bonds.append((idx[k], _add(atoms, "H", ext), 1))
        sub = subs.get(k)
        if sub is None:
            bonds.append((idx[k], _add(atoms, "H", up), 1))
        else:
            _add_substituent(atoms, bonds, idx[k], up, sub)
        bonds.append((idx[k], _add(atoms, "H", dn), 1))


def _add_substituent(atoms, bonds, c_i, at, sub):
    """Attach *sub* to backbone carbon *c_i* at position *at*."""
    if sub in ("F", "Cl", "Br", "OH"):
        if sub == "OH":
            i_o = _add(atoms, "O", at)
            bonds.append((c_i, i_o, 1))
            bonds.append((i_o, _add(atoms, "H", _plus(at, (0.4, 0.5, 0.5))), 1))
        else:
            bonds.append((c_i, _add(atoms, sub, at), 1))
    elif sub == "CH3":
        i_m = _add(atoms, "C", at)
        bonds.append((c_i, i_m, 1))
        for d in (_plus(at, (0.0, 0.7, 0.7)), _plus(at, (0.7, 0.7, -0.4)),
                  _plus(at, (-0.7, 0.7, -0.4))):
            bonds.append((i_m, _add(atoms, "H", d), 1))
    elif sub == "phenyl":
        cx, cy, cz = at[0], at[1] + 1.4, at[2] + 0.6
        idx = []
        for k in range(6):
            ang = math.radians(90 + k * 60)
            idx.append(_add(atoms, "C", (cx + 1.2 * math.cos(ang),
                                         cy + 1.2 * math.sin(ang), cz)))
        for k in range(6):
            bonds.append((idx[k], idx[(k + 1) % 6], 2 if k % 2 == 0 else 1))
        bonds.append((c_i, idx[0], 1))


def _mol_ethane():
    return _polymer_atoms(2, lambda k: None)


def _mol_propane():
    return _polymer_atoms(3, lambda k: None)


def _polymer_atoms(n, pattern):
    atoms, bonds = [], []
    pts = _backbone(n)
    idx = [_add(atoms, "C", p) for p in pts]
    for k in range(n - 1):
        bonds.append((idx[k], idx[k + 1], 1))
    subs = {k: pattern(k) for k in range(n) if pattern(k) is not None}
    _backbone_hydrogens(atoms, bonds, idx, pts, subs)
    return atoms, bonds, None


def _mol_ethene():
    atoms, bonds = [], []
    c1, c2 = (-0.67, 0.0, 0.0), (0.67, 0.0, 0.0)
    i1, i2 = _add(atoms, "C", c1), _add(atoms, "C", c2)
    bonds.append((i1, i2, 2))
    for (ci, cp, sx) in ((i1, c1, -1), (i2, c2, 1)):
        for sy in (1, -1):
            bonds.append((ci, _add(atoms, "H",
                                   (cp[0] + sx * 0.6, sy * 0.94, 0.0)), 1))
    return atoms, bonds, None


def _mol_ethyne():
    atoms, bonds = [], []
    c1, c2 = (-0.60, 0.0, 0.0), (0.60, 0.0, 0.0)
    i1, i2 = _add(atoms, "C", c1), _add(atoms, "C", c2)
    bonds.append((i1, i2, 3))
    bonds.append((i1, _add(atoms, "H", (-1.66, 0.0, 0.0)), 1))
    bonds.append((i2, _add(atoms, "H", (1.66, 0.0, 0.0)), 1))
    return atoms, bonds, None


# --- PET repeat unit --------------------------------------------------------
def _mol_pet():
    """Poly(ethylene terephthalate) repeat unit: a benzene ring with two
    ester groups (para), then the -O-CH2-CH2-O- glycol link."""
    atoms, bonds = [], []
    ring = _ring_carbons(6, 1.39)
    ridx = [_add(atoms, "C", p) for p in ring]
    for k in range(6):
        bonds.append((ridx[k], ridx[(k + 1) % 6], 2 if k % 2 == 0 else 1))
    # H on the 4 unsubstituted ring carbons (positions 1,2,4,5)
    for k in (1, 2, 4, 5):
        p = ring[k]
        d = math.hypot(p[0], p[1]) or 1.0
        bonds.append((ridx[k], _add(atoms, "H",
                     (p[0] * (d + 1.0) / d, p[1] * (d + 1.0) / d, 0.0)), 1))

    def _ester(anchor_i, base, direction):
        bx, by = base
        c = (bx + direction * 1.3, by, 0.0)
        i_c = _add(atoms, "C", c)
        bonds.append((anchor_i, i_c, 1))
        bonds.append((i_c, _add(atoms, "O", (c[0], c[1] + 1.15, 0.5)), 2))
        o1 = (c[0] + direction * 1.2, c[1] - 0.4, 0.0)
        i_o1 = _add(atoms, "O", o1)
        bonds.append((i_c, i_o1, 1))
        ch = (o1[0] + direction * 1.2, o1[1] - 0.6, 0.4)
        i_ch = _add(atoms, "C", ch)
        bonds.append((i_o1, i_ch, 1))
        for hy in (0.7, -0.7):
            bonds.append((i_ch, _add(atoms, "H",
                                     (ch[0], ch[1] + 0.4, hy + 0.4)), 1))
        return i_ch

    top = ridx[0]        # top ring carbon
    bot = ridx[3]        # bottom ring carbon (para)
    ch_a = _ester(top, (ring[0][0], ring[0][1]), 1)
    ch_b = _ester(bot, (ring[3][0], ring[3][1]), -1)
    # glycol CH2-CH2 link between the two ester oxygens' carbons
    bonds.append((ch_a, ch_b, 1))
    return atoms, bonds, None


# ------------------------------------------------------------ crystal cells
# Unit cells are drawn as open wireframe boxes (thick solid cube edges +
# dashed body/face diagonals to the centring atoms) with small spheres, so
# the cell geometry stays visible — the classic textbook unit-cell look.
_CORNERS = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
_CUBE_PAIRS = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
               (0, 4), (1, 5), (2, 6), (3, 7)]


def _cube_edges(a):
    c = [(x * a, y * a, z * a) for x, y, z in _CORNERS]
    return [(c[i], c[j], "solid") for i, j in _CUBE_PAIRS]


def _cube_corners(a):
    return [(x * a, y * a, z * a) for x, y, z in _CORNERS]


def _body_diagonals(a):
    """The four dashed cube body-diagonals (each passes through the centre)."""
    c = _cube_corners(a)
    return [(c[0], c[6], "dash"), (c[1], c[7], "dash"),
            (c[2], c[4], "dash"), (c[3], c[5], "dash")]


def _crystal(el_at, a=2.0, extra_edges=None, bonds=None):
    """Build a crystal model from ``el_at`` = list of (element, (x,y,z))."""
    atoms = [(e, p[0], p[1], p[2]) for e, p in el_at]
    edges = _cube_edges(a) + (extra_edges or [])
    return atoms, (bonds or []), edges


def _xtal_simple_cubic():
    a = 3.0
    return _crystal([("Cu", p) for p in _cube_corners(a)], a)


def _xtal_bcc():
    a = 3.0
    pts = [("Fe", p) for p in _cube_corners(a)]
    pts.append(("Fe", (a / 2, a / 2, a / 2)))
    return _crystal(pts, a, extra_edges=_body_diagonals(a))


def _xtal_fcc():
    a = 3.0
    pts = [("Al", p) for p in _cube_corners(a)]
    faces = [(a / 2, a / 2, 0), (a / 2, a / 2, a), (a / 2, 0, a / 2),
             (a / 2, a, a / 2), (0, a / 2, a / 2), (a, a / 2, a / 2)]
    pts += [("Al", p) for p in faces]
    # dashed face diagonals (each passes through a face-centre atom)
    c = _cube_corners(a)
    fdiag = [(c[0], c[2], "dash"), (c[4], c[6], "dash"),
             (c[0], c[5], "dash"), (c[3], c[6], "dash"),
             (c[0], c[7], "dash"), (c[1], c[6], "dash")]
    return _crystal(pts, a, extra_edges=fdiag)


def _xtal_hcp():
    """A hexagonal-close-packed cell: two hexagon layers + 3 middle atoms."""
    atoms, r, hz = [], 1.6, 1.6
    for z in (0.0, 2 * hz):
        _add(atoms, "Mg", (0.0, 0.0, z))
        for k in range(6):
            ang = math.radians(k * 60)
            _add(atoms, "Mg", (r * math.cos(ang), r * math.sin(ang), z))
    for k in range(3):
        ang = math.radians(30 + k * 120)
        _add(atoms, "Mg", (r * 0.58 * math.cos(ang),
                           r * 0.58 * math.sin(ang), hz))
    # hexagon prism edges
    edges = []
    top = [(r * math.cos(math.radians(k * 60)),
            r * math.sin(math.radians(k * 60)), 0.0) for k in range(6)]
    bot = [(p[0], p[1], 2 * hz) for p in top]
    for k in range(6):
        edges.append((top[k], top[(k + 1) % 6]))
        edges.append((bot[k], bot[(k + 1) % 6]))
        edges.append((top[k], bot[k]))
    return atoms, [], edges


def _xtal_diamond():
    """FCC carbon lattice with the 4 tetrahedral interior atoms + bonds."""
    a = 4.0
    atoms = []
    corners = _cube_corners(a)
    for p in corners:
        _add(atoms, "C", p)
    faces = [(a / 2, a / 2, 0), (a / 2, a / 2, a), (a / 2, 0, a / 2),
             (a / 2, a, a / 2), (0, a / 2, a / 2), (a, a / 2, a / 2)]
    for p in faces:
        _add(atoms, "C", p)
    inner = [(a / 4, a / 4, a / 4), (3 * a / 4, 3 * a / 4, a / 4),
             (3 * a / 4, a / 4, 3 * a / 4), (a / 4, 3 * a / 4, 3 * a / 4)]
    inner_idx = [_add(atoms, "C", p) for p in inner]
    # bond each interior atom to its 4 nearest lattice atoms
    bonds = []
    for ii in inner_idx:
        ip = (atoms[ii][1], atoms[ii][2], atoms[ii][3])
        dists = sorted(range(len(atoms)),
                       key=lambda k: (atoms[k][1] - ip[0]) ** 2
                       + (atoms[k][2] - ip[1]) ** 2
                       + (atoms[k][3] - ip[2]) ** 2)
        for k in dists[1:5]:
            bonds.append((ii, k, 1))
    return atoms, bonds, _cube_edges(a)


def _xtal_nacl():
    """Rock salt: a 3x3x3 grid of alternating Na+/Cl- ions."""
    atoms = []
    step = 1.6
    for i in range(3):
        for j in range(3):
            for k in range(3):
                el = "Na" if (i + j + k) % 2 == 0 else "Cl"
                _add(atoms, el, (i * step, j * step, k * step))
    return atoms, [], _cube_edges(2 * step)


def _xtal_cscl():
    a = 3.0
    pts = [("Cl", p) for p in _cube_corners(a)]
    pts.append(("Cs", (a / 2, a / 2, a / 2)))
    return _crystal(pts, a, extra_edges=_body_diagonals(a))


# ------------------------------------------------------------------- registry
#: name -> (builder returning (atoms, bonds, edges), radius scale)
_MODELS = {
    "water": (_mol_water, 0.9), "ammonia": (_mol_ammonia, 0.9),
    "methane": (_mol_methane, 0.9), "carbon_dioxide": (_mol_carbon_dioxide, 0.9),
    "methanol": (_mol_methanol, 0.9), "ethanol": (_mol_ethanol, 0.9),
    "formaldehyde": (_mol_formaldehyde, 0.9),
    "acetic_acid": (_mol_acetic_acid, 0.88),
    "ethane": (_mol_ethane, 0.9), "propane": (_mol_propane, 0.9),
    "ethene": (_mol_ethene, 0.9), "ethyne": (_mol_ethyne, 0.9),
    "benzene": (_mol_benzene, 0.9), "cyclohexane": (_mol_cyclohexane, 0.88),
    "glucose": (_mol_glucose, 0.82), "pet": (_mol_pet, 0.72),
    "simple_cubic": (_xtal_simple_cubic, 0.62), "bcc": (_xtal_bcc, 0.58),
    "fcc": (_xtal_fcc, 0.52), "hcp": (_xtal_hcp, 0.5),
    "diamond": (_xtal_diamond, 0.42), "nacl": (_xtal_nacl, 0.5),
    "cscl": (_xtal_cscl, 0.6),
}

#: Polymer repeat units share the zig-zag backbone builder.
_POLYMERS = {
    "polyethylene": lambda k: None,
    "polypropylene": lambda k: "CH3" if k % 2 == 0 else None,
    "pvc": lambda k: "Cl" if k % 2 == 0 else None,
    "ptfe": lambda k: "F",
    "polystyrene": lambda k: "phenyl" if k % 2 == 0 else None,
}
_POLYMER_LEN = 6

#: Page footprint (mm) per model; scaled to a fraction of the page.
REFERENCE_MM = 130.0
SIZES = {
    "water": (48, 40), "ammonia": (48, 44), "methane": (52, 52),
    "carbon_dioxide": (64, 34), "methanol": (58, 50), "ethanol": (68, 52),
    "formaldehyde": (52, 46), "acetic_acid": (66, 54),
    "ethane": (60, 46), "propane": (72, 46), "ethene": (58, 44),
    "ethyne": (66, 32), "benzene": (64, 62), "cyclohexane": (64, 60),
    "glucose": (70, 64), "pet": (118, 58),
    "polyethylene": (112, 48), "polypropylene": (112, 56),
    "pvc": (112, 52), "ptfe": (112, 52), "polystyrene": (116, 66),
    "simple_cubic": (66, 70), "bcc": (66, 72), "fcc": (70, 74),
    "hcp": (66, 74), "diamond": (78, 82), "nacl": (76, 80),
    "cscl": (66, 72),
}
LABELS = {
    "water": "Water (H₂O)", "ammonia": "Ammonia (NH₃)",
    "methane": "Methane (CH₄)", "carbon_dioxide": "Carbon dioxide (CO₂)",
    "methanol": "Methanol", "ethanol": "Ethanol",
    "formaldehyde": "Formaldehyde", "acetic_acid": "Acetic acid",
    "ethane": "Ethane", "propane": "Propane", "ethene": "Ethene",
    "ethyne": "Ethyne", "benzene": "Benzene", "cyclohexane": "Cyclohexane",
    "glucose": "Glucose", "pet": "PET repeat unit",
    "polyethylene": "Polyethylene", "polypropylene": "Polypropylene",
    "pvc": "PVC", "ptfe": "PTFE", "polystyrene": "Polystyrene",
    "simple_cubic": "Simple cubic", "bcc": "BCC", "fcc": "FCC",
    "hcp": "HCP", "diamond": "Diamond", "nacl": "NaCl (rock salt)",
    "cscl": "CsCl",
}
CATEGORIES = [
    ("Simple molecules",
     ["water", "ammonia", "methane", "carbon_dioxide", "formaldehyde"]),
    ("Alcohols & acids",
     ["methanol", "ethanol", "acetic_acid", "glucose"]),
    ("Hydrocarbons",
     ["ethane", "propane", "ethene", "ethyne", "benzene", "cyclohexane"]),
    ("Polymers",
     ["polyethylene", "polypropylene", "pvc", "ptfe", "polystyrene", "pet"]),
    ("Crystal structures",
     ["simple_cubic", "bcc", "fcc", "hcp", "diamond", "nacl", "cscl"]),
]


#: Default bond spread for molecules — >1 so the sticks read clearly
#: between the spheres (crystals keep their true lattice spacing, 1.0).
DEFAULT_BOND = 1.6


def is_crystal(name):
    return name in _MODELS and _MODELS[name][0].__name__.startswith("_xtal")


def default_bond(name):
    """The default bond spread for *name* (crystals stay at true spacing)."""
    return 1.0 if is_crystal(name) else DEFAULT_BOND


def model_data(name):
    """Return ``(atoms, bonds, edges, rscale)`` for a named model.

    The 3D data behind a model, so the viewer can re-project it at any
    orientation. Polymers share the zig-zag backbone builder."""
    if name in _POLYMERS:
        atoms, bonds, edges = _polymer_atoms(_POLYMER_LEN, _POLYMERS[name])
        return atoms, bonds, edges, 0.92
    builder, rscale = _MODELS[name]
    atoms, bonds, edges = builder()
    return atoms, bonds, edges, rscale


def build_specs_oriented(name, w, h, az=None, el=None, bond=None):
    """Shape specs for model *name* in a (w, h) box, viewed at (az, el)
    radians, with bond spread *bond* (defaults per model)."""
    atoms, bonds, edges, rscale = model_data(name)
    return _model(atoms, bonds, w, h, edges=edges, rscale=rscale,
                  az=DEFAULT_AZ if az is None else az,
                  el=DEFAULT_EL if el is None else el,
                  bond_scale=default_bond(name) if bond is None else bond)


def build_specs(name, w, h):
    """Shape specs for model *name* drawn into a (w, h) px box."""
    return build_specs_oriented(name, w, h)


def specs_from_atoms(atoms, bonds, w, h, az=None, el=None, bond=1.0,
                     rscale=0.92):
    """Shape specs for a custom (atoms, bonds) model — used by the builder
    when the user has edited the structure atom by atom."""
    return _model(atoms, bonds, w, h, rscale=rscale,
                  az=DEFAULT_AZ if az is None else az,
                  el=DEFAULT_EL if el is None else el, bond_scale=bond)


def size_mm(name):
    return SIZES[name]


# --------------------------------------------------- high-level AI vocabulary
def expand_specs(specs):
    """Expand any `atom`/`bond` specs into primitive circle/line specs.

    Lets the AI (or any caller) describe a molecule with element spheres and
    bonds: ``{"shape":"atom","element":"O","x":.,"y":.,"r":.}`` and
    ``{"shape":"bond","x1":.,"y1":.,"x2":.,"y2":.,"order":2}``. Any other
    spec passes through unchanged."""
    out = []
    for spec in specs:
        shape = str(spec.get("shape", "")).lower()
        if shape in ("atom", "sphere"):
            r = float(spec.get("r", spec.get("radius", 16)))
            cx = float(spec.get("cx", spec.get("x", 0)))   # x,y = centre
            cy = float(spec.get("cy", spec.get("y", 0)))
            el = str(spec.get("element", spec.get("el", "C")))
            out += atom_specs(cx, cy, r, el, label=bool(spec.get("label")))
        elif shape == "bond":
            p1 = (float(spec.get("x1", 0)), float(spec.get("y1", 0)))
            p2 = (float(spec.get("x2", 0)), float(spec.get("y2", 0)))
            out += bond_specs(p1, p2, int(spec.get("order", 1)),
                              width=float(spec.get("width", 6)))
        else:
            out.append(spec)
    return out
