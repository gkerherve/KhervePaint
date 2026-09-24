"""3D solids: shaded, rotatable primitives (cube, cylinder, sphere, torus…).

Each solid is a small polygon **mesh** (vertices + faces in a unit box).
Drawing it projects the mesh orthographically at a view angle (azimuth
about the vertical, elevation above the horizon), drops back-faces, sorts
the rest far-to-near (painter's algorithm) and shades each face by a fixed
light (Lambert + ambient) — so the result is a group of ordinary, editable
filled polygons that still reads as a solid object.

A placed solid is a `GroupItem` carrying ``item.solid`` =
``{"name", "az", "el", "color", "box"}``; double-click spins it on the
canvas (the scene's orbit mode, like molecule models), and the tag
round-trips through document.py (``"solid"``) and svgio.py (``kp:solid``),
so it survives save, reload and undo.

Same `build_specs`/`size_mm`/`REFERENCE_MM`/`SIZES`/`LABELS`/`CATEGORIES`
interface as the other palettes, plus `solid_specs` for any orientation.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

DEFAULT_AZ = math.radians(35.0)
DEFAULT_EL = math.radians(25.0)
DEFAULT_COLOR = "#5b8fd9"
#: light direction in view space (from upper-left, towards the viewer)
_LIGHT = (-0.45, 0.65, 0.62)
_AMBIENT = 0.42


# ──────────────────────────────────────────────────────────── meshes
# Coordinates: x right, y up, z towards the viewer at az = el = 0.
# Faces are vertex-index lists wound counter-clockwise seen from outside.

def _box(sx=1.0, sy=1.0, sz=1.0):
    x, y, z = sx / 2, sy / 2, sz / 2
    v = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
         (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    f = [[4, 5, 6, 7], [1, 0, 3, 2], [0, 4, 7, 3], [5, 1, 2, 6],
         [7, 6, 2, 3], [0, 1, 5, 4]]
    return v, f, False


def _prism(n, r_bot=0.5, r_top=0.5, h=1.0, smooth=False, rot=0.0):
    """n-gon prism / frustum / cone (r_top = 0) standing on the y axis."""
    v, f = [], []
    y0, y1 = -h / 2, h / 2
    for i in range(n):
        a = rot + 2 * math.pi * i / n
        v.append((r_bot * math.cos(a), y0, -r_bot * math.sin(a)))
    apex = r_top <= 1e-9
    if apex:
        v.append((0.0, y1, 0.0))
        top = n
        for i in range(n):
            f.append([i, (i + 1) % n, top])
    else:
        for i in range(n):
            a = rot + 2 * math.pi * i / n
            v.append((r_top * math.cos(a), y1, -r_top * math.sin(a)))
        for i in range(n):
            j = (i + 1) % n
            f.append([i, j, n + j, n + i])
        f.append([n + i for i in range(n)])              # top cap
    f.append([i for i in reversed(range(n))])            # bottom cap
    return v, f, smooth


def _sphere(nu=20, nv=12, hemi=False):
    v, f = [], []
    v_start = nv // 2 if hemi else 0
    rings = []
    for j in range(v_start, nv + 1):
        phi = math.pi * j / nv - math.pi / 2           # -90° .. 90°
        ring = []
        for i in range(nu):
            th = 2 * math.pi * i / nu
            v.append((0.5 * math.cos(phi) * math.cos(th), 0.5 * math.sin(phi),
                      -0.5 * math.cos(phi) * math.sin(th)))
            ring.append(len(v) - 1)
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(nu):
            j = (i + 1) % nu
            f.append([a[i], a[j], b[j], b[i]])
    if hemi:                                           # flat base
        f.append(list(reversed(rings[0])))
    return v, f, True


def _torus(nu=24, nv=12, R=0.34, r=0.15):
    v, f = [], []
    for i in range(nu):
        th = 2 * math.pi * i / nu
        for j in range(nv):
            ph = 2 * math.pi * j / nv
            d = R + r * math.cos(ph)
            v.append((d * math.cos(th), r * math.sin(ph), -d * math.sin(th)))
    for i in range(nu):
        for j in range(nv):
            a = i * nv + j
            b = ((i + 1) % nu) * nv + j
            c = ((i + 1) % nu) * nv + (j + 1) % nv
            d = i * nv + (j + 1) % nv
            f.append([a, b, c, d])
    return v, f, True


def _tube(n=28, r_out=0.5, r_in=0.32, h=1.0):
    """Hollow cylinder (pipe)."""
    v, f = [], []
    y0, y1 = -h / 2, h / 2
    for r in (r_out, r_in):
        for y in (y0, y1):
            for i in range(n):
                a = 2 * math.pi * i / n
                v.append((r * math.cos(a), y, -r * math.sin(a)))
    ob, ot, ib, it = 0, n, 2 * n, 3 * n
    for i in range(n):
        j = (i + 1) % n
        f.append([ob + i, ob + j, ot + j, ot + i])        # outer wall
        f.append([ib + j, ib + i, it + i, it + j])        # inner wall
        f.append([ot + i, ot + j, it + j, it + i])        # top ring
        f.append([ob + j, ob + i, ib + i, ib + j])        # bottom ring
    return v, f, True


def _poly_solid(verts, faces, fix=True):
    """Normalise a polyhedron into the unit box, fixing face winding so
    every normal points away from the centroid."""
    cx = sum(p[0] for p in verts) / len(verts)
    cy = sum(p[1] for p in verts) / len(verts)
    cz = sum(p[2] for p in verts) / len(verts)
    span = max(max(abs(p[k] - c) for p in verts)
               for k, c in enumerate((cx, cy, cz))) * 2
    v = [((p[0] - cx) / span, (p[1] - cy) / span, (p[2] - cz) / span)
         for p in verts]
    out = []
    for face in faces:
        n = _normal([v[i] for i in face])
        m = [sum(v[i][k] for i in face) / len(face) for k in range(3)]
        out.append(list(face) if (not fix or _dot(n, m) >= 0)
                   else list(reversed(face)))
    return v, out, False


def _octa():
    return _poly_solid([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                        (0, 0, 1), (0, 0, -1)],
                       [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
                        [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])


def _icosa():
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t),
         (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1),
         (-t, 0, -1), (-t, 0, 1)]
    f = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
         [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
         [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
         [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    return _poly_solid(v, f)


def _dodeca():
    """Dual of the icosahedron: one vertex per icosahedron face centre."""
    iv, ifaces, _ = _icosa()
    centres = [tuple(sum(iv[i][k] for i in face) / 3 for k in range(3))
               for face in ifaces]
    faces = []
    for vi in range(len(iv)):                  # faces around each vertex
        ring = [fi for fi, face in enumerate(ifaces) if vi in face]
        # order the ring by angle around the vertex direction
        axis = _unit(iv[vi])
        ref = _unit(_sub(centres[ring[0]], iv[vi]))
        side = _cross(axis, ref)
        ring.sort(key=lambda fi: math.atan2(
            _dot(_sub(centres[fi], iv[vi]), side),
            _dot(_sub(centres[fi], iv[vi]), ref)))
        faces.append(ring)
    return _poly_solid(centres, faces)


def _extrude(profile, depth, parts):
    """Extrude a counter-clockwise (x, y) *profile* along z by *depth*.
    *parts* are convex (x, y) polygons that tile the profile, used for the
    two caps (a non-convex cap drawn as one polygon would fill wrongly)."""
    d = depth / 2
    n = len(profile)
    v = [(x, y, d) for x, y in profile] + [(x, y, -d) for x, y in profile]
    f = []
    for i in range(n):
        j = (i + 1) % n
        f.append([j, i, n + i, n + j])                   # side walls
    for part in parts:
        base = len(v)
        v += [(x, y, d) for x, y in part]
        f.append(list(range(base, base + len(part))))    # front cap
        base = len(v)
        v += [(x, y, -d) for x, y in part]
        f.append(list(reversed(range(base, base + len(part)))))  # back
    return _poly_solid(v, f, fix=False)


def _stairs(steps=4):
    """A staircase block: an extruded step profile."""
    t = 1.0 / steps
    prof = [(0.0, 0.0), (1.0, 0.0)]
    for i in reversed(range(steps)):                 # down the steps
        prof += [((i + 1) * t, (i + 1) * t), (i * t, (i + 1) * t)]
    prof = [p for k, p in enumerate(prof) if p != prof[k - 1]]
    parts = [[(i * t, 0.0), ((i + 1) * t, 0.0), ((i + 1) * t, (i + 1) * t),
              (i * t, (i + 1) * t)] for i in range(steps)]
    return _extrude(prof, 0.6, parts)


def _arrow3d():
    """A block arrow extruded in depth, pointing right."""
    prof = [(-0.5, -0.12), (0.1, -0.12), (0.1, -0.3), (0.5, 0.0),
            (0.1, 0.3), (0.1, 0.12), (-0.5, 0.12)]
    parts = [[(-0.5, -0.12), (0.1, -0.12), (0.1, 0.12), (-0.5, 0.12)],
             [(0.1, -0.3), (0.5, 0.0), (0.1, 0.3)]]
    return _extrude(prof, 0.2, parts)


_MESHES = {
    "cube": lambda: _box(),
    "cuboid": lambda: _box(1.0, 0.55, 0.7),
    "plate": lambda: _box(1.0, 0.12, 0.7),
    "cylinder": lambda: _prism(32, 0.35, 0.35, 1.0, smooth=True),
    "disc": lambda: _prism(40, 0.5, 0.5, 0.18, smooth=True),
    "tube": lambda: _tube(),
    "cone": lambda: _prism(32, 0.45, 0.0, 1.0, smooth=True),
    "frustum": lambda: _prism(32, 0.45, 0.25, 0.8, smooth=True),
    "sphere": lambda: _sphere(32, 18),
    "hemisphere": lambda: _sphere(32, 18, hemi=True),
    "torus": lambda: _torus(),
    "pyramid": lambda: _prism(4, 0.62, 0.0, 0.9, rot=math.pi / 4),
    "tri_prism": lambda: _prism(3, 0.55, 0.55, 1.0, rot=math.radians(-125)),
    "hex_prism": lambda: _prism(6, 0.5, 0.5, 0.9),
    "tetrahedron": lambda: _prism(3, 0.55, 0.0, 0.78, rot=math.radians(-125)),
    "octahedron": _octa,
    "icosahedron": _icosa,
    "dodecahedron": _dodeca,
    "stairs": lambda: _stairs(),
    "arrow_3d": _arrow3d,
}

LABELS = {
    "cube": "Cube", "cuboid": "Box (cuboid)", "plate": "Plate / slab",
    "cylinder": "Cylinder", "disc": "Disc", "tube": "Tube / pipe",
    "cone": "Cone", "frustum": "Truncated cone", "sphere": "Sphere",
    "hemisphere": "Hemisphere", "torus": "Torus (ring)",
    "pyramid": "Square pyramid", "tri_prism": "Triangular prism",
    "hex_prism": "Hexagonal prism", "tetrahedron": "Tetrahedron",
    "octahedron": "Octahedron", "icosahedron": "Icosahedron",
    "dodecahedron": "Dodecahedron", "stairs": "Stairs",
    "arrow_3d": "3D arrow",
}

CATEGORIES = [
    ("Boxes", ["cube", "cuboid", "plate", "stairs"]),
    ("Round solids", ["cylinder", "disc", "tube", "cone", "frustum",
                      "sphere", "hemisphere", "torus"]),
    ("Prisms & pyramids", ["pyramid", "tri_prism", "hex_prism"]),
    ("Platonic solids", ["tetrahedron", "octahedron", "icosahedron",
                         "dodecahedron"]),
    ("Annotation", ["arrow_3d"]),
]

REFERENCE_MM = 130.0
SIZES = {name: (30, 30) for name in _MESHES}

#: Named colours offered in the menus / accepted by the MCP tool.
COLORS = {
    "blue": "#5b8fd9", "red": "#d9534f", "green": "#4caf6a",
    "orange": "#ee9a3a", "yellow": "#e6c229", "purple": "#8e6bc9",
    "grey": "#9aa0a8", "gold": "#d4a73a", "copper": "#c77b4a",
    "glass": "#a8d4ee", "white": "#eeeeee", "black": "#3a3a3a",
}


# ──────────────────────────────────────────────────────────── vectors
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = math.sqrt(_dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def _normal(pts):
    """Newell normal of a planar polygon (robust for any vertex count)."""
    nx = ny = nz = 0.0
    for i, p in enumerate(pts):
        q = pts[(i + 1) % len(pts)]
        nx += (p[1] - q[1]) * (p[2] + q[2])
        ny += (p[2] - q[2]) * (p[0] + q[0])
        nz += (p[0] - q[0]) * (p[1] + q[1])
    return _unit((nx, ny, nz))


def _rotate(p, az, el):
    """World → view: spin by *az* about y, then tilt by *el* about x."""
    x, y, z = p
    ca, sa = math.cos(az), math.sin(az)
    x, z = x * ca + z * sa, -x * sa + z * ca
    ce, se = math.cos(el), math.sin(el)
    y, z = y * ce - z * se, y * se + z * ce
    return (x, y, z)


def _shade(hex_color, k):
    """Scale an RGB hex colour's brightness by *k* (clamped)."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        h = DEFAULT_COLOR.lstrip("#")
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    if k > 1.0:                               # highlight towards white
        rgb = [c + (255 - c) * min(k - 1.0, 1.0) for c in rgb]
    else:
        rgb = [c * max(k, 0.0) for c in rgb]
    return "#" + "".join(f"{max(0, min(255, int(round(c)))):02x}"
                         for c in rgb)


def resolve_color(color):
    if not color:
        return DEFAULT_COLOR
    color = str(color).strip()
    return COLORS.get(color.lower(), color)


# ──────────────────────────────────────────────────────────── drawing
def solid_specs(name, w, h, az=DEFAULT_AZ, el=DEFAULT_EL,
                color=DEFAULT_COLOR, outline=True):
    """Polygon shape specs drawing solid *name* into a (w, h) px box seen
    from (*az*, *el*) radians, shaded in *color*. Faces are ordered far to
    near so later polygons correctly cover earlier ones."""
    if name not in _MESHES:
        raise KeyError(name)
    color = resolve_color(color)
    if name == "sphere":
        # A sphere looks the same from everywhere: one smooth lit-sphere
        # gradient disc beats any facetted mesh (and matches the atoms).
        d = min(w, h)
        return [{"shape": "circle", "x": (w - d) / 2, "y": (h - d) / 2,
                 "w": d, "h": d, "stroke": _shade(color, 0.45),
                 "width": 1.0, "fill": {"kind": "sun",
                                        "c1": _shade(color, 0.8),
                                        "c2": _shade(color, 1.75)}}]
    verts, faces, smooth = _MESHES[name]()
    view = [_rotate(p, az, el) for p in verts]
    light = _unit(_LIGHT)
    # Scale by the mesh's own bounding sphere: it projects to the same
    # circle from every angle, so the solid fills its box without ever
    # spilling out as it turns.
    radius = max(math.sqrt(_dot(p, p)) for p in verts) or 0.5
    scale = min(w, h) / (2.0 * radius)
    cx, cy = w / 2.0, h / 2.0
    drawn = []
    for face in faces:
        pts = [view[i] for i in face]
        n = _normal(pts)
        if n[2] <= 1e-6:                      # facing away: hidden
            continue
        depth = sum(p[2] for p in pts) / len(pts)
        lam = max(_dot(n, light), 0.0)
        # a touch of specular so round solids get a highlight
        spec = max(n[2] * 0.9 + lam * 0.4 - 0.95, 0.0) * 2.2 if smooth else 0
        k = _AMBIENT + (1.0 - _AMBIENT) * lam + spec
        fill = _shade(color, k)
        points = [[round(cx + p[0] * scale, 2), round(cy - p[1] * scale, 2)]
                  for p in pts]
        drawn.append((depth, {
            "shape": "polygon", "points": points, "fill": fill,
            # smooth solids: stroke in the fill colour hides mesh seams
            "stroke": fill if (smooth or not outline) else
            _shade(color, 0.35),
            "width": 0.6 if (smooth or not outline) else 1.0,
        }))
    drawn.sort(key=lambda t: t[0])
    return [spec for _d, spec in drawn]


def build_specs(name, w, h):
    return solid_specs(name, w, h)


def size_mm(name):
    return SIZES[name]


def resolve_name(name):
    """Forgiving lookup: key, label or a loose spelling ('hex prism')."""
    if not name:
        return None
    key = str(name).strip().lower().replace("-", "_").replace(" ", "_")
    if key in _MESHES:
        return key
    for k, label in LABELS.items():
        if label.lower() == str(name).strip().lower():
            return k
    aliases = {"box": "cuboid", "ball": "sphere", "ring": "torus",
               "donut": "torus", "doughnut": "torus", "pipe": "tube",
               "prism": "tri_prism", "d20": "icosahedron",
               "d12": "dodecahedron", "d8": "octahedron",
               "d4": "tetrahedron", "d6": "cube"}
    return aliases.get(key)


# ──────────────────────────────────────────────────────────── scene glue
def _items(specs):
    from .ai_assistant import _spec_to_item
    return [it for it in (_spec_to_item(s) for s in specs) if it is not None]


def place_solid(scene, name, center, color=None, az=None, el=None,
                size=None, commit=True):
    """Drop solid *name* centred on *center* as a tagged, rotatable group.
    *size* is the build box in px (default: a page-relative size, like the
    other palettes). Undoable when *commit*. Returns the group."""
    name = resolve_name(name)
    if name is None:
        return None
    az = DEFAULT_AZ if az is None else az
    el = DEFAULT_EL if el is None else el
    color = resolve_color(color)
    if not size:
        w_mm, _h = size_mm(name)
        size = (scene.sceneRect().width() or 1) / REFERENCE_MM * w_mm
    items = _items(solid_specs(name, size, size, az, el, color))
    if not items:
        return None
    top = scene._drop_items(items, center, size, size)
    top.solid = {"name": name, "az": az, "el": el, "color": color,
                 "box": size}
    if commit:
        scene.changed_by_user.emit()
    return top


def _bbox_offset(tag, box):
    """How far the drawn outline's centre sits from the mesh centre."""
    specs = solid_specs(tag["name"], box, box,
                        tag.get("az", DEFAULT_AZ), tag.get("el", DEFAULT_EL),
                        tag.get("color", DEFAULT_COLOR))
    xs, ys = [], []
    for s in specs:
        pts = s.get("points") or [[s["x"], s["y"]],
                                  [s["x"] + s["w"], s["y"] + s["h"]]]
        xs += [p[0] for p in pts]
        ys += [p[1] for p in pts]
    if not xs:
        return 0.0, 0.0
    return ((min(xs) + max(xs)) / 2 - box / 2,
            (min(ys) + max(ys)) / 2 - box / 2)


def reorient_solid(scene, item, az=None, el=None, color=None, commit=True):
    """Rebuild a placed solid at a new view / colour, keeping its centre and
    build box. Returns the new group (the old one is removed)."""
    tag = dict(getattr(item, "solid", None) or {})
    if not tag.get("name"):
        return None
    if az is not None:
        tag["az"] = az
    if el is not None:
        tag["el"] = max(-math.pi / 2, min(math.pi / 2, el))
    if color is not None:
        tag["color"] = resolve_color(color)
    box = tag.get("box") or max(item.sceneBoundingRect().width(), 1.0)
    old = dict(getattr(item, "solid"))
    items = _items(solid_specs(tag["name"], box, box, tag["az"], tag["el"],
                               tag["color"]))
    if not items:
        return None
    # The drawn outline's centre moves as the solid turns; the mesh centre
    # must not, or an orbit drag would walk the object across the page.
    ox, oy = _bbox_offset(old, box)
    rc = item.sceneBoundingRect().center()
    from PyQt5.QtCore import QPointF
    center = QPointF(rc.x() - ox, rc.y() - oy)
    scene.clear_handles()
    scene.removeItem(item)
    top = scene._drop_items(items, center, box, box)
    top.solid = tag
    if commit:
        scene.changed_by_user.emit()
    return top
