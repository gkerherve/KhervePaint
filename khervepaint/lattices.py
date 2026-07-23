"""Non-cubic crystal lattice systems for the molecules palette.

The seven crystal systems beyond the cubic family are described by their
lattice parameters (a, b, c, α, β, γ); `lattice_vectors` turns those into
the three cell vectors and `_cell` builds the parallelepiped unit cell
(8 corner atoms + 12 wireframe edges) from them. `LATTICE_VECTORS` lets
`molecules._supercell` tile these cells along their true lattice vectors,
so a hexagonal or monoclinic supercell stacks skewed — cells meet
face-to-face in the crystallographically correct orientations rather
than on an orthogonal grid.

Registered into `molecules._MODELS` (the builders are named `_xtal_*` so
`molecules.is_crystal`/`can_stack` recognise them), which drives the left
toolbar's Molecules dropdown, stacking, rotation and persistence for free.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

#: Fractional corner coordinates and the 12 edges of a parallelepiped,
#: in the same order as the cube tables in `molecules`.
_CORNERS = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
            (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)]
_EDGE_PAIRS = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
               (0, 4), (1, 5), (2, 6), (3, 7)]


def lattice_vectors(a, b, c, alpha, beta, gamma):
    """The three cell vectors for lattice parameters (lengths in model
    units, angles in degrees), using the standard crystallographic
    convention: **a** along x, **b** in the xy-plane at γ to **a**."""
    al, be, ga = (math.radians(v) for v in (alpha, beta, gamma))
    sg = math.sin(ga) or 1.0
    va = (a, 0.0, 0.0)
    vb = (b * math.cos(ga), b * math.sin(ga), 0.0)
    cx = c * math.cos(be)
    cy = c * (math.cos(al) - math.cos(be) * math.cos(ga)) / sg
    cz = math.sqrt(max(c * c - cx * cx - cy * cy, 0.0))
    return va, vb, (cx, cy, cz)


def rotation(rx, ry, rz):
    """A 3D rotation for tilt angles in **degrees** about the x, y then z
    axes; returns a point -> rotated-point function. Used to tilt a single
    unit cell inside a supercell about its own centre."""
    ax, ay, az = (math.radians(v) for v in (rx, ry, rz))
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    m = (                                       # R = Rz · Ry · Rx
        (cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
        (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
        (-sy, cy * sx, cy * cx),
    )

    def apply(p):
        return (m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2],
                m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2],
                m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2])
    return apply


def _corner(f, va, vb, vc):
    return tuple(f[0] * va[k] + f[1] * vb[k] + f[2] * vc[k] for k in range(3))


def _cell(element, va, vb, vc):
    """A primitive (P) unit cell: one *element* atom at each corner of the
    parallelepiped spanned by the cell vectors, with solid wireframe edges."""
    corners = [_corner(f, va, vb, vc) for f in _CORNERS]
    atoms = [(element, p[0], p[1], p[2]) for p in corners]
    edges = [(corners[i], corners[j], "solid") for i, j in _EDGE_PAIRS]
    return atoms, [], edges


#: name -> (element, a, b, c, alpha, beta, gamma). The element just picks a
#: distinct, recognisable sphere colour per system (Zn really is hexagonal,
#: B rhombohedral…); the lengths/angles are illustrative, not measured.
PARAMS = {
    "tetragonal": ("Ti", 2.6, 2.6, 3.8, 90, 90, 90),
    "orthorhombic": ("S", 2.2, 3.0, 3.8, 90, 90, 90),
    "hexagonal": ("Zn", 2.7, 2.7, 3.6, 90, 90, 120),
    "rhombohedral": ("B", 3.0, 3.0, 3.0, 75, 75, 75),
    "monoclinic": ("Fe", 2.4, 3.0, 3.4, 90, 70, 90),
    "triclinic": ("Cu", 2.2, 2.8, 3.2, 80, 70, 85),
}

#: Cell vectors per lattice — `molecules._supercell` tiles along these, so
#: stacked cells sit in the lattice's own (possibly skewed) orientations.
LATTICE_VECTORS = {name: lattice_vectors(*p[1:]) for name, p in PARAMS.items()}


def _make_builder(name):
    element = PARAMS[name][0]
    va, vb, vc = LATTICE_VECTORS[name]

    def build():
        return _cell(element, va, vb, vc)
    # is_crystal/can_stack key off the builder's `_xtal_` name prefix
    build.__name__ = f"_xtal_{name}"
    return build


MODELS = {name: (_make_builder(name), 0.55) for name in PARAMS}
SIZES = {
    "tetragonal": (62, 74), "orthorhombic": (64, 74), "hexagonal": (68, 70),
    "rhombohedral": (66, 68), "monoclinic": (66, 72), "triclinic": (66, 70),
}
LABELS = {
    "tetragonal": "Tetragonal", "orthorhombic": "Orthorhombic",
    "hexagonal": "Hexagonal", "rhombohedral": "Rhombohedral (trigonal)",
    "monoclinic": "Monoclinic", "triclinic": "Triclinic",
}
CATEGORY = ("Lattice systems", list(PARAMS))
