"""2D chemical representations of a molecule graph.

The same (atoms, bonds) that back a 3D ball-and-stick model can also be
drawn as flat chemistry diagrams — the styles of a textbook or a paper:

* ``skeletal``   — line-angle (bond-line) formula: carbons are the bare
  vertices of a 120° zig-zag, H on carbon is implicit, heteroatoms carry
  their hydrogens as a label (OH, NH₂), ring double bonds sit inside.
* ``structural`` — displayed formula: every atom (hydrogens too) as an
  element letter joined by single/double/triple bond lines.
* ``lewis``      — the structural drawing plus lone-pair dots.
* ``condensed``  — condensed structural formula (CH₃CH₂OH, CH₃COOH,
  C₆H₅CH₃), falling back to the molecular formula for other rings.
* ``formula``    — the molecular formula in Hill notation (C₂H₆O).

The 2D coordinates are a proper **depiction**, not a flattened 3D view:
rings become regular polygons (fused rings share an edge), chains run as
a 120° zig-zag (linear through sp centres) and substituents fan out into
the largest free angle. Every function returns shape-spec dicts (the
AI/library format), so the scene turns them into ordinary editable items
just like the 3D model. `depict` draws at a fixed bond length (the
reaction builder uses it so every molecule of a scheme shares one bond
length); `representation_specs` fits a drawing into a box.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math
from collections import Counter, deque

from PyQt5.QtGui import QColor, QFont, QFontMetricsF

from . import molecules

#: The representation modes, in menu order.
MODES = ["3d", "skeletal", "structural", "lewis", "condensed", "formula"]
MODE_LABELS = {"3d": "3D ball-and-stick", "skeletal": "Skeletal (line-angle)",
               "structural": "Structural formula", "lewis": "Lewis structure",
               "condensed": "Condensed formula",
               "formula": "Molecular formula"}
#: Modes drawn as a single line of text rather than a bond drawing.
TEXT_MODES = ("condensed", "formula")

_INK = "#1a1a1a"
FONT = "Segoe UI"                 # the family `_spec_to_item` gives text
#: Valence electrons per element, for counting lone pairs in Lewis mode.
_VALENCE_E = {"H": 1, "B": 3, "C": 4, "N": 5, "O": 6, "F": 7, "Si": 4,
              "P": 5, "S": 6, "Cl": 7, "Br": 7, "I": 7}
_HALOGENS = {"F", "Cl", "Br", "I"}
_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_H_BOND = 0.8                     # drawn X–H length, in heavy-bond units
_TAU = 2.0 * math.pi


def sub(n):
    """Unicode subscript for a count (empty for 1)."""
    return str(n).translate(_SUB) if n > 1 else ""


# ----------------------------------------------------------------- text
_PX_PER_PT = []


def font_metrics(pt):
    return QFontMetricsF(QFont(FONT, max(1, int(pt))))


def pt_for_height(px):
    """Point size whose line height is about *px* pixels (text items take
    a point size; layout needs pixels)."""
    if not _PX_PER_PT:
        _PX_PER_PT.append(font_metrics(100).height() / 100.0 or 1.0)
    return max(4, int(round(px / _PX_PER_PT[0])))


def text_size(text, pt):
    """(width, height) in px of *text* at *pt* — the inked extent, without
    the text item's document margin."""
    fm = font_metrics(pt)
    return fm.horizontalAdvance(text), fm.height()


def text_spec(text, cx, cy, pt, color=_INK):
    return {"shape": "text", "text": text, "x": cx, "y": cy,
            "anchor": "center", "size": int(pt), "color": color}


# ------------------------------------------------------ spec bounding boxes
def spec_bounds(spec):
    """(x0, y0, x1, y1) of one shape spec."""
    shape = spec.get("shape")
    if shape == "text":
        w, h = text_size(str(spec.get("text", "")), spec.get("size", 14))
        x, y = float(spec.get("x", 0)), float(spec.get("y", 0))
        if spec.get("anchor") == "center":
            return x - w / 2, y - h / 2, x + w / 2, y + h / 2
        return x, y, x + w, y + h
    if "points" in spec:
        xs = [float(p[0]) for p in spec["points"]]
        ys = [float(p[1]) for p in spec["points"]]
        return min(xs), min(ys), max(xs), max(ys)
    if "x1" in spec:
        hw = float(spec.get("width", 1)) / 2
        xs = (float(spec["x1"]), float(spec["x2"]))
        ys = (float(spec["y1"]), float(spec["y2"]))
        return min(xs) - hw, min(ys) - hw, max(xs) + hw, max(ys) + hw
    x, y = float(spec.get("x", 0)), float(spec.get("y", 0))
    return x, y, x + float(spec.get("w", 0)), y + float(spec.get("h", 0))


def specs_bounds(specs):
    boxes = [spec_bounds(s) for s in specs]
    if not boxes:
        return 0.0, 0.0, 0.0, 0.0
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def shift_specs(specs, dx, dy):
    """Translate specs in place by (dx, dy); returns them."""
    for s in specs:
        if "points" in s:
            s["points"] = [[float(p[0]) + dx, float(p[1]) + dy]
                           for p in s["points"]]
        if "x1" in s:
            s["x1"] = float(s["x1"]) + dx
            s["x2"] = float(s["x2"]) + dx
            s["y1"] = float(s["y1"]) + dy
            s["y2"] = float(s["y2"]) + dy
        if "x" in s:
            s["x"] = float(s["x"]) + dx
            s["y"] = float(s["y"]) + dy
    return specs


def normalize(specs, pad=0.0):
    """Shift specs so their bounding box starts at (pad, pad); returns
    (specs, width, height) including the padding."""
    x0, y0, x1, y1 = specs_bounds(specs)
    shift_specs(specs, pad - x0, pad - y0)
    return specs, (x1 - x0) + 2 * pad, (y1 - y0) + 2 * pad


# ---------------------------------------------------------------- graph
def _adjacency(n, bonds):
    adj = [dict() for _ in range(n)]
    for b in bonds:
        i, j = int(b[0]), int(b[1])
        o = int(b[2]) if len(b) > 2 else 1
        if 0 <= i < n and 0 <= j < n and i != j:
            adj[i][j] = o
            adj[j][i] = o
    return adj


def _heavy_set(atoms):
    """Indices of the non-hydrogen atoms (all atoms for H₂)."""
    heavy = [i for i, a in enumerate(atoms) if a[0] != "H"]
    return set(heavy or range(len(atoms)))


def _components(nodes, adj, keep):
    seen, comps = set(), []
    for s in nodes:
        if s in seen:
            continue
        comp, queue = [], [s]
        seen.add(s)
        while queue:
            u = queue.pop()
            comp.append(u)
            for v in adj[u]:
                if v in keep and v not in seen:
                    seen.add(v)
                    queue.append(v)
        comps.append(sorted(comp))
    return comps


def _path(u, v, nodes, adj, skip_edge=None):
    """Shortest path u → v inside *nodes* (optionally ignoring one edge)."""
    prev = {u: None}
    queue = deque([u])
    while queue:
        a = queue.popleft()
        if a == v:
            break
        for b in adj[a]:
            if b not in nodes or b in prev:
                continue
            if skip_edge and {a, b} == set(skip_edge):
                continue
            prev[b] = a
            queue.append(b)
    if v not in prev:
        return None
    out, a = [], v
    while a is not None:
        out.append(a)
        a = prev[a]
    return out[::-1]


def rings(atoms, bonds):
    """Smallest set of smallest rings of the heavy-atom graph, each an
    ordered atom list."""
    adj = _adjacency(len(atoms), bonds)
    return _rings(_heavy_set(atoms), adj)


def _rings(nodes, adj):
    nodes = set(nodes)
    edges = sorted({(min(i, j), max(i, j)) for i in nodes for j in adj[i]
                    if j in nodes})
    need = len(edges) - len(nodes) + len(_components(sorted(nodes), adj,
                                                     nodes))
    if need <= 0:
        return []
    index = {e: k for k, e in enumerate(edges)}
    cands, seen = [], set()
    for u, v in edges:
        p = _path(u, v, nodes, adj, skip_edge=(u, v))
        if p and frozenset(p) not in seen:
            seen.add(frozenset(p))
            cands.append(p)
    cands.sort(key=len)
    basis, out = {}, []
    for ring in cands:                     # keep GF(2)-independent cycles
        vec = 0
        for k in range(len(ring)):
            a, b = ring[k], ring[(k + 1) % len(ring)]
            vec |= 1 << index[(min(a, b), max(a, b))]
        while vec:
            top = vec.bit_length() - 1
            if top not in basis:
                basis[top] = vec
                out.append(ring)
                break
            vec ^= basis[top]
        if len(out) == need:
            break
    return out


# --------------------------------------------------------------- layout
def _ang(p, q):
    return math.atan2(q[1] - p[1], q[0] - p[0])


def _step(p, a, length=1.0):
    return (p[0] + math.cos(a) * length, p[1] + math.sin(a) * length)


def _angdiff(a, b):
    return abs((a - b + math.pi) % _TAU - math.pi)


def _fill_gaps(angs, k, avoid=(), room=None):
    """*k* directions spread into the free angular gaps between *angs*:
    each goes to the gap that leaves the widest spacing, then sits evenly
    inside it. A gap holding an *avoid* direction (a ring's inside) counts
    as much narrower; equal gaps go to the one whose middle has the most
    *room* (a callable: angle -> clearance), then to the bigger one."""
    angs = sorted(a % _TAU for a in angs)
    gaps = []
    for n, a in enumerate(angs):
        nxt = angs[(n + 1) % len(angs)] + (_TAU if n == len(angs) - 1 else 0)
        size = nxt - a
        inside = any(1e-6 < (v - a) % _TAU < size - 1e-6 for v in avoid)
        gaps.append([a, size, 0, size * (0.3 if inside else 1.0)])

    def key(g):
        mid = g[0] + g[1] / (g[2] + 2)
        return (round(g[3] / (g[2] + 1), 2),
                round(min(room(mid), 1.5), 2) if room else 0.0, g[3])
    for _ in range(k):
        best = max(gaps, key=key)
        best[2] += 1
    out = []
    for start, size, c, _eff in gaps:
        out += [start + size * (i + 1) / (c + 1) for i in range(c)]
    return out


def _ring_dirs(u, ring_list, pos):
    """Directions from *u* to the centres of its (already placed) rings."""
    out = []
    for ring in ring_list:
        if u in ring and all(a in pos for a in ring):
            cx = sum(pos[a][0] for a in ring) / len(ring)
            cy = sum(pos[a][1] for a in ring) / len(ring)
            out.append(_ang(pos[u], (cx, cy)))
    return out


def _nearest(p, pos, skip=()):
    return min((math.dist(p, q) for i, q in pos.items() if i not in skip),
               default=9.0)


def _branch_size(start, parent, adj, keep):
    seen, stack = {start, parent}, [start]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v in keep and v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) - 1


def _linear(u, adj, keep):
    orders = [o for v, o in adj[u].items() if v in keep]
    return any(o >= 3 for o in orders) or orders.count(2) >= 2


def _chain_end(comp, adj, keep, atoms):
    """One end of the longest path (a tree's diameter), carbon preferred,
    so a chain is laid out from one end to the other."""
    def far(s):
        dist, queue = {s: 0}, deque([s])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if v in keep and v not in dist:
                    dist[v] = dist[u] + 1
                    queue.append(v)
        return max(dist, key=lambda n: (dist[n], atoms[n][0] == "C"))
    e1 = far(comp[0])
    e2 = far(e1)
    if atoms[e1][0] != "C" and atoms[e2][0] == "C":
        return e2
    return e1


def _ring_systems(ring_list):
    systems = []
    for r, ring in enumerate(ring_list):
        hit = [s for s in systems if any(set(ring) & set(ring_list[k])
                                         for k in s)]
        merged = [r]
        for s in hit:
            merged += s
            systems.remove(s)
        systems.append(merged)
    return systems


def _place_polygon(ring, pos, centre, first_angle, direction):
    """Regular polygon of unit edges around *centre*; ring[0] sits at
    *first_angle*, walking *direction* (±1) round the ring."""
    n = len(ring)
    radius = 0.5 / math.sin(math.pi / n)
    for k, a in enumerate(ring):
        if a not in pos:
            pos[a] = _step(centre, first_angle + direction * k * _TAU / n,
                           radius)


def _place_system(system, ring_list, pos, anchor=None, direction=0.0):
    """Lay out one ring system: the first ring as a regular polygon (on
    the anchor, pointing along *direction*), then fused rings across
    their shared edge and spiro rings off their shared atom."""
    todo = list(system)
    if anchor is not None:
        todo.sort(key=lambda r: anchor not in ring_list[r])
    first = ring_list[todo.pop(0)]
    n = len(first)
    radius = 0.5 / math.sin(math.pi / n)
    if anchor is None:
        _place_polygon(first, pos, (0.0, 0.0), -math.pi / 2, 1)
    else:
        k = first.index(anchor)
        ring = first[k:] + first[:k]
        centre = _step(pos[anchor], direction, radius)
        _place_polygon(ring, pos, centre, direction + math.pi, 1)
    progress = True
    while todo and progress:
        progress = False
        for r in list(todo):
            ring = ring_list[r]
            n = len(ring)
            edge = next((k for k in range(n) if ring[k] in pos
                         and ring[(k + 1) % n] in pos), None)
            done = [a for a in ring if a in pos]
            if edge is not None:                     # fused: share an edge
                ring = ring[edge:] + ring[:edge]
                a, b = pos[ring[0]], pos[ring[1]]
                others = [pos[x] for x in pos if x not in ring[:2]]
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                nx, ny = -(b[1] - a[1]), b[0] - a[0]
                ln = math.hypot(nx, ny) or 1.0
                nx, ny = nx / ln, ny / ln
                if others:
                    ox = sum(p[0] for p in others) / len(others)
                    oy = sum(p[1] for p in others) / len(others)
                    if (ox - mx) * nx + (oy - my) * ny > 0:
                        nx, ny = -nx, -ny
                apothem = 0.5 / math.tan(math.pi / n)
                centre = (mx + nx * apothem, my + ny * apothem)
                ta, tb = _ang(centre, a), _ang(centre, b)
                turn = 1 if ((tb - ta) % _TAU) < math.pi else -1
                _place_polygon(ring, pos, centre, ta, turn)
            elif len(done) == 1:                     # spiro: share an atom
                a = done[0]
                k = ring.index(a)
                ring = ring[k:] + ring[:k]
                cx = sum(p[0] for p in pos.values()) / len(pos)
                cy = sum(p[1] for p in pos.values()) / len(pos)
                out = _ang((cx, cy), pos[a])
                radius = 0.5 / math.sin(math.pi / n)
                _place_polygon(ring, pos, _step(pos[a], out, radius),
                               out + math.pi, 1)
            else:
                continue
            todo.remove(r)
            progress = True


def _layout_component(comp, atoms, adj, keep, ring_list, pos):
    comp_set = set(comp)
    mine = [r for r, ring in enumerate(ring_list) if ring[0] in comp_set]
    systems = [[r for r in s] for s in _ring_systems([ring_list[r]
                                                      for r in mine])]
    systems = [[mine[r] for r in s] for s in systems]
    sys_of = {}
    for s_i, s in enumerate(systems):
        for r in s:
            for a in ring_list[r]:
                sys_of[a] = s_i
    placed_sys = set()
    turn = {}
    queue = deque()
    if systems:
        s0 = max(range(len(systems)),
                 key=lambda k: len({a for r in systems[k]
                                    for a in ring_list[r]}))
        _place_system(systems[s0], ring_list, pos)
        placed_sys.add(s0)
        queue.extend(a for a in comp if a in pos)
    else:
        root = _chain_end(comp, adj, keep, atoms)
        pos[root] = (0.0, 0.0)
        queue.append(root)
    while queue:
        u = queue.popleft()
        kids = [v for v in adj[u] if v in keep and v not in pos]
        if not kids:
            continue
        for v, a in _kid_directions(u, kids, atoms, adj, keep, pos, turn,
                                    ring_list):
            p = _step(pos[u], a)
            pos[v] = p
            if v in sys_of and sys_of[v] not in placed_sys:
                before = set(pos)
                _place_system(systems[sys_of[v]], ring_list, pos, anchor=v,
                              direction=a)
                placed_sys.add(sys_of[v])
                queue.append(v)
                queue.extend(x for x in pos if x not in before)
            else:
                queue.append(v)
    for a in comp:                                   # anything unreachable
        pos.setdefault(a, (0.0, 0.0))


def _kid_directions(u, kids, atoms, adj, keep, pos, turn, ring_list=()):
    """Bond angles for the unplaced heavy neighbours *kids* of *u*."""
    placed = [v for v in adj[u] if v in keep and v in pos]
    angs = [_ang(pos[u], pos[v]) for v in placed]
    k = len(kids)
    linear = _linear(u, adj, keep)
    # main chain first: the biggest branch, carbon over heteroatom
    kids = sorted(kids, key=lambda v: (-_branch_size(v, u, adj, keep),
                                       atoms[v][0] != "C", adj[u][v]))
    if not angs:                                     # the root atom
        if k == 1:
            turn[kids[0]] = -1
            return [(kids[0], -math.pi / 6)]
        start = 0.0 if linear else -math.pi / 6
        return [(v, start + _TAU * i / k) for i, v in enumerate(kids)]
    if len(angs) == 1:
        fwd = angs[0] + math.pi
        if linear:
            return [(v, fwd + i * math.pi / 2) for i, v in enumerate(kids)]
        s = -turn.get(u, 1)
        if k == 1:
            best = None
            for sign in (s, -s):
                a = fwd + sign * math.pi / 3
                room = _nearest(_step(pos[u], a), pos, skip=(u,))
                if best is None or room > best[2] + 0.25:
                    best = (sign, a, room)
                if room > 0.8:
                    break
            turn[kids[0]] = best[0]
            return [(kids[0], best[1])]
        if k == 2:
            turn[kids[0]], turn[kids[1]] = s, -s
            return [(kids[0], fwd + s * math.pi / 3),
                    (kids[1], fwd - s * math.pi / 3)]
        if k == 3:
            turn[kids[0]] = turn.get(u, 1)
            return [(kids[0], fwd), (kids[1], fwd + math.pi / 2),
                    (kids[2], fwd - math.pi / 2)]
    dirs = _fill_gaps(angs, k, avoid=_ring_dirs(u, ring_list, pos),
                      room=lambda a: _nearest(_step(pos[u], a), pos,
                                              skip=(u,)))
    return list(zip(kids, dirs))                      # ring atom / crowded


def _straighten(comp, pos):
    """Turn a collinear component (a diatomic, CO₂, a C≡C chain…) so it
    reads left to right."""
    pts = [pos[a] for a in comp]
    if len(pts) < 2:
        return
    far = max(((p, q) for p in pts for q in pts), key=lambda pq:
              math.dist(*pq))
    a = _ang(*far)
    ux, uy = math.cos(a), math.sin(a)
    if any(abs((p[0] - far[0][0]) * uy - (p[1] - far[0][1]) * ux) > 1e-6
           for p in pts):
        return                                        # not collinear
    ox, oy = far[0]
    for n in comp:
        x, y = pos[n][0] - ox, pos[n][1] - oy
        pos[n] = (x * ux + y * uy, -x * uy + y * ux)


def _place_hydrogens(comp, atoms, adj, keep, pos, ring_list=()):
    # CH3/CH2 first: their H's have fixed fans, a lone H then picks the
    # gap with room left (so a ring CH never lands on a CH2OH's H's)
    order = sorted(comp, key=lambda u: -sum(1 for v in adj[u]
                                            if v not in keep))
    for u in order:
        hn = [v for v in adj[u] if v not in keep]
        if not hn:
            continue
        angs = [_ang(pos[u], pos[v]) for v in adj[u] if v in keep]
        k = len(hn)
        if angs:
            dirs = _fill_gaps(
                angs, k, avoid=_ring_dirs(u, ring_list, pos),
                room=lambda a, u=u: _nearest(_step(pos[u], a, _H_BOND), pos,
                                             skip=(u,)))
        else:                             # a lone atom: H₂O bent, NH₃, CH₄
            dirs = {1: [0.0], 2: [5 * math.pi / 6, math.pi / 6],
                    3: [math.pi, 0.0, math.pi / 2]}.get(
                        k, [_TAU * i / k for i in range(k)])
        for v, a in zip(hn, dirs):
            pos[v] = _step(pos[u], a, _H_BOND)


def layout_2d(atoms, bonds, explicit_h=False):
    """Depiction coordinates in bond-length units: ``{atom index: (x, y)}``
    (screen orientation, y down). Hydrogens get positions only when
    *explicit_h*; disconnected fragments sit side by side."""
    n = len(atoms)
    if not n:
        return {}
    adj = _adjacency(n, bonds)
    keep = _heavy_set(atoms)
    if len(atoms) > 1 and not any(adj):
        return _projected(atoms)                      # bond-less crystal
    ring_list = _rings(keep, adj)
    pos = {}
    x_off = 0.0
    for comp in _components(sorted(keep), adj, keep):
        cpos = {}
        _layout_component(comp, atoms, adj, keep, ring_list, cpos)
        if not any(set(r) & set(comp) for r in ring_list):
            _straighten(comp, cpos)
        if explicit_h:
            _place_hydrogens(comp, atoms, adj, keep, cpos, ring_list)
        xs = [p[0] for p in cpos.values()]
        ys = [p[1] for p in cpos.values()]
        dx, dy = x_off - min(xs), -(min(ys) + max(ys)) / 2
        for a, p in cpos.items():
            pos[a] = (p[0] + dx, p[1] + dy)
        x_off = max(xs) + dx + 1.4
    return pos


def _projected(atoms):
    """Fallback for bond-less structures (crystals): the orthographic view
    that spreads the atoms out most, scaled to unit spacing."""
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
    pts = best[1]
    near = min((math.dist(p, q) for i, p in enumerate(pts)
                for q in pts[i + 1:] if math.dist(p, q) > 1e-6), default=1.0)
    return {i: (p[0] / near, p[1] / near) for i, p in enumerate(pts)}


# -------------------------------------------------------------- drawing
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


def _skeletal_labels(atoms, adj, keep, pos):
    """Atoms that get a letter in a line-angle drawing -> H count. Carbons
    stay bare vertices unless isolated, part of a two-atom molecule
    (H₃C–CH₃ reads better than a lone stroke) or a cumulated =C=."""
    heavy = [i for i in pos if i in keep]
    small = len(heavy) <= 2
    out = {}
    for i in heavy:
        nb = [j for j in adj[i] if j in keep]
        h = sum(1 for j in adj[i] if j not in keep)
        cumulated = len(nb) == 2 and all(adj[i][j] == 2 for j in nb)
        if atoms[i][0] != "C" or not nb or small or cumulated:
            out[i] = h
    return out


def _h_side(i, pos, adj, keep, element):
    """Where an atom's H label goes: the side with most room from its
    bonds (right, then left, below, above). A lone O/S/halogen writes
    its H first (H₂O, HCl), the rest after (NH₃, CH₄)."""
    angs = [_ang(pos[i], pos[j]) for j in adj[i] if j in keep and j in pos]
    if not angs:
        return "left" if element in ("O", "S") or element in _HALOGENS \
            else "right"
    sides = [("right", 0.0), ("left", math.pi), ("below", math.pi / 2),
             ("above", -math.pi / 2)]
    room = {s: min(_angdiff(a, b) for b in angs) for s, a in sides}
    for s, _a in sides:
        if room[s] >= math.radians(75):
            return s
    return max(room, key=room.get)


def _bond_offset_side(i, j, P, adj, ring_centres):
    """Which side (+1/-1 along the left normal) an inner double-bond line
    goes on, or 0 for a centred pair."""
    (x1, y1), (x2, y2) = P[i], P[j]
    nx, ny = -(y2 - y1), x2 - x1
    for centre in ring_centres.get(frozenset((i, j)), []):
        d = (centre[0] - (x1 + x2) / 2) * nx + (centre[1] - (y1 + y2) / 2) * ny
        return 1 if d > 0 else -1
    score = 0.0
    for a, b in ((i, j), (j, i)):
        for k in adj[a]:
            if k != b and k in P:
                d = (P[k][0] - x1) * nx + (P[k][1] - y1) * ny
                score += 1 if d > 0 else -1
    return 0 if score == 0 else (1 if score > 0 else -1)


def _draw(mode, atoms, bonds, pos, unit):
    """Bond + label specs for a laid-out molecule (*pos* in bond units)."""
    n = len(atoms)
    adj = _adjacency(n, bonds)
    keep = _heavy_set(atoms)
    skeletal = mode == "skeletal"
    pt = pt_for_height(unit * 0.6)
    fm = font_metrics(pt)
    lw = max(1.0, unit * 0.045)
    dbl = unit * 0.17
    P = {i: (x * unit, y * unit) for i, (x, y) in pos.items()}
    labels = (_skeletal_labels(atoms, adj, keep, pos) if skeletal
              else {i: 0 for i in P})
    radius = {}
    for i in labels:
        adv = fm.horizontalAdvance(atoms[i][0])
        radius[i] = max(0.5 * adv + 0.12 * fm.height(), 0.36 * fm.height())
    ring_centres = {}
    if skeletal:
        for ring in _rings(keep, adj):
            cx = sum(P[a][0] for a in ring) / len(ring)
            cy = sum(P[a][1] for a in ring) / len(ring)
            for k in range(len(ring)):
                key = frozenset((ring[k], ring[(k + 1) % len(ring)]))
                ring_centres.setdefault(key, []).append((cx, cy))
    specs = []

    def line(a, b, off=0.0, shrink=0.0):
        (x1, y1), (x2, y2) = a, b
        ln = math.hypot(x2 - x1, y2 - y1) or 1.0
        ux, uy = (x2 - x1) / ln, (y2 - y1) / ln
        px, py = -uy * off, ux * off
        specs.append({"shape": "line", "x1": x1 + px + ux * shrink,
                      "y1": y1 + py + uy * shrink,
                      "x2": x2 + px - ux * shrink,
                      "y2": y2 + py - uy * shrink,
                      "stroke": _INK, "width": lw})

    for b in bonds:
        i, j = int(b[0]), int(b[1])
        order = int(b[2]) if len(b) > 2 else 1
        if i not in P or j not in P:
            continue
        (x1, y1), (x2, y2) = P[i], P[j]
        ln = math.hypot(x2 - x1, y2 - y1) or 1.0
        ux, uy = (x2 - x1) / ln, (y2 - y1) / ln
        ti, tj = radius.get(i, 0.0), radius.get(j, 0.0)
        a = (x1 + ux * ti, y1 + uy * ti)
        z = (x2 - ux * tj, y2 - uy * tj)
        if order == 2:
            side = 0
            if skeletal and i not in labels and j not in labels:
                side = _bond_offset_side(i, j, P, adj, ring_centres)
            if side:
                line(a, z)
                line(a, z, off=side * dbl, shrink=unit * 0.14)
            else:
                line(a, z, off=-dbl / 2)
                line(a, z, off=dbl / 2)
        elif order >= 3:
            for o in (-dbl * 0.9, 0.0, dbl * 0.9):
                line(a, z, off=o)
        else:
            line(a, z)

    for i, h in labels.items():
        el = atoms[i][0]
        color = _label_color(el)
        cx, cy = P[i]
        specs.append(text_spec(el, cx, cy, pt, color))
        if h:
            htxt = "H" + sub(h)
            side = _h_side(i, pos, adj, keep, el)
            half = (fm.horizontalAdvance(el) + fm.horizontalAdvance(htxt)) / 2
            hx, hy = {"right": (cx + half, cy), "left": (cx - half, cy),
                      "below": (cx, cy + fm.height() * 0.82),
                      "above": (cx, cy - fm.height() * 0.82)}[side]
            specs.append(text_spec(htxt, hx, hy, pt, color))
    if mode == "lewis":
        specs += _lewis_dots(atoms, adj, P, radius, fm)
    return specs


def _lewis_dots(atoms, adj, P, radius, fm):
    """Lone-pair dot pairs on the sides of each atom clear of its bonds,
    spread apart (each pair claims its direction before the next)."""
    dot = max(1.2, fm.height() * 0.07)
    dd = fm.height() * 0.16                  # spacing of the two dots
    specs = []
    for i, (cx, cy) in P.items():
        el = atoms[i][0]
        pairs = _lone_pairs(el, sum(adj[i].values()))
        if pairs <= 0:
            continue
        used = [_ang(P[i], P[j]) for j in adj[i] if j in P]
        r = radius.get(i, fm.height() * 0.4) + dot * 1.5
        for _ in range(pairs):
            cands = [math.radians(a) for a in range(-90, 270, 30)]
            a = max(cands, key=lambda c: min((_angdiff(c, u) for u in used),
                                             default=math.pi))
            used.append(a)
            bx, by = cx + math.cos(a) * r, cy + math.sin(a) * r
            tx, ty = -math.sin(a), math.cos(a)
            for sgn in (-1.0, 1.0):
                x, y = bx + tx * dd * sgn, by + ty * dd * sgn
                specs.append({"shape": "circle", "x": x - dot, "y": y - dot,
                              "w": 2 * dot, "h": 2 * dot, "stroke": "none",
                              "fill": _INK})
    return specs


# ------------------------------------------------------------- formulas
def molecular_formula(atoms):
    """Hill-notation molecular formula string (C, then H, then alphabetical)."""
    counts = Counter(a[0] for a in atoms)
    order = []
    if "C" in counts:
        order.append("C")
        if "H" in counts:
            order.append("H")
    for el in sorted(counts):
        if el not in order:
            order.append(el)
    return "".join(el + sub(counts[el]) for el in order)


def _appended(i, atoms, adj, keep, hc):
    """A terminal atom written straight after its parent in a condensed
    formula: a carbonyl =O/=S or a halogen (C=O → CO, CHCl₃)."""
    nb = [j for j in adj[i] if j in keep]
    if len(nb) != 1 or hc[i]:
        return False
    el = atoms[i][0]
    return el in _HALOGENS or (el in ("O", "S") and adj[i][nb[0]] == 2)


def _deepest(start, parent, adj, core, atoms):
    """Longest path from *start* into its branch (away from *parent*),
    carbon-rich paths preferred."""
    best = [start]
    for v in adj[start]:
        if v in core and v != parent:
            p = [start] + _deepest(v, start, adj, core, atoms)
            key = (len(p), sum(atoms[a][0] == "C" for a in p))
            if key > (len(best), sum(atoms[a][0] == "C" for a in best)):
                best = p
    return best


def _write_path(path, parent, ctx):
    atoms, adj, core, app, hc = ctx
    out = ""
    for k, i in enumerate(path):
        prev = path[k - 1] if k else parent
        nxt = path[k + 1] if k + 1 < len(path) else None
        el, h = atoms[i][0], hc[i]
        tail = Counter(atoms[j][0] for j in adj[i] if j in app)
        carbonyl = el == "C" and any(e in ("O", "S") for e in tail)
        if k == 0 and parent is None and h and (el != "C" or carbonyl):
            # HO…, H₂N…, and HCOOH / HCHO rather than CHOOH / CH₂O
            grp = ("HC" + ("H" + sub(h - 1) if h > 1 else "")) if carbonyl \
                else "H" + sub(h) + el
        else:
            grp = el + ("H" + sub(h) if h else "")
        grp += "".join(e + sub(c) for e, c in tail.items())
        branches = Counter()
        for j in adj[i]:
            if j in core and j not in (prev, nxt):
                branches[_write_path(_deepest(j, i, adj, core, atoms), i,
                                     ctx)] += 1
        for s, c in branches.items():
            grp += "(" + s + ")" + sub(c)
        if nxt is not None and el == "C" and atoms[nxt][0] == "C":
            grp += {2: "=", 3: "≡"}.get(adj[i][nxt], "")
        out += grp
    return out


def condensed_formula(atoms, bonds):
    """Condensed structural formula — CH₃CH₂OH, CH₃COOH, CH₃CH(OH)CH₃,
    C₆H₅CH₃ — or the molecular formula where none reads naturally."""
    n = len(atoms)
    if not n:
        return ""
    adj = _adjacency(n, bonds)
    keep = _heavy_set(atoms)
    if all(a[0] == "H" for a in atoms) \
            or len(_components(sorted(keep), adj, keep)) != 1:
        return molecular_formula(atoms)
    hc = {i: sum(1 for j in adj[i] if j not in keep) for i in keep}
    app = {i for i in keep if _appended(i, atoms, adj, keep, hc)}
    core = keep - app
    ctx = (atoms, adj, core, app, hc)
    ring_list = _rings(keep, adj)
    if ring_list:
        ring = ring_list[0]
        if len(ring_list) != 1 or len(ring) != 6 \
                or any(atoms[a][0] != "C" for a in ring):
            return molecular_formula(atoms)
        rs = set(ring)
        subs = [(a, b) for a in ring for b in adj[a] if b in keep
                and b not in rs]
        doubles = sum(1 for k in range(6)
                      if adj[ring[k]][ring[(k + 1) % 6]] == 2)
        if len(subs) != 1 or doubles != 3 \
                or any(hc[a] != 1 for a in ring if a != subs[0][0]):
            return molecular_formula(atoms)
        a, b = subs[0]
        return "C₆H₅" + _write_path(_deepest(b, a, adj, core, atoms), a, ctx)
    if not core:
        return molecular_formula(atoms)
    if len(core) == 1:
        i = next(iter(core))
        el, h = atoms[i][0], hc[i]
        if not any(j in app for j in adj[i]):
            hp = "H" + sub(h) if h else ""
            return hp + el if el in ("O", "S") or el in _HALOGENS \
                else el + hp
    if not any(atoms[i][0] == "C" for i in core):
        return molecular_formula(atoms)
    ends = [i for i in core if sum(1 for j in adj[i] if j in core) <= 1]
    best = None
    for s in ends:
        for t in ends:
            p = _path(s, t, core, adj) if s != t else [s]
            if not p:
                continue
            key = (len(p), sum(atoms[a][0] == "C" for a in p),
                   atoms[s][0] == "C", hc[s])
            if best is None or key > best[0]:
                best = (key, p)
    return _write_path(best[1], None, ctx)


# ------------------------------------------------------------ public API
def depict(mode, atoms, bonds, unit):
    """Draw *mode* at *unit* px per bond (text modes use a matching font
    size). Returns (specs, width, height) with the drawing's top-left at
    (0, 0) — every molecule drawn at one *unit* shares a bond length."""
    if mode in TEXT_MODES:
        text = condensed_formula(atoms, bonds) if mode == "condensed" \
            else molecular_formula(atoms)
        return normalize([text_spec(text, 0.0, 0.0,
                                    pt_for_height(unit * 0.62))])
    explicit = mode in ("structural", "lewis")
    pos = layout_2d(atoms, bonds, explicit_h=explicit)
    return normalize(_draw(mode, atoms, bonds, pos, unit), pad=unit * 0.06)


def representation_specs(mode, atoms, bonds, w, h):
    """Shape specs for *mode*, fitted and centred in a (w, h) box (the 3D
    mode is handled by molecules._model / specs_from_atoms)."""
    if mode not in MODES or mode == "3d" or not atoms:
        return []
    margin = 0.08 * min(w, h)
    if mode in TEXT_MODES:
        text = condensed_formula(atoms, bonds) if mode == "condensed" \
            else molecular_formula(atoms)
        pt = int(max(18, min(w, h) * 0.22))
        tw, _th = text_size(text, pt)
        if tw > w - 2 * margin:
            pt = max(6, int(pt * (w - 2 * margin) / tw))
        return [text_spec(text, w / 2.0, h / 2.0, pt)]
    trial = 40.0
    _s, sw, sh = depict(mode, atoms, bonds, trial)
    k = min((w - 2 * margin) / (sw or 1), (h - 2 * margin) / (sh or 1))
    unit = min(trial * k, 0.45 * min(w, h))
    specs, sw, sh = depict(mode, atoms, bonds, unit)
    return shift_specs(specs, (w - sw) / 2.0, (h - sh) / 2.0)


def structural_specs(atoms, bonds, w, h, lewis=False):
    """Displayed formula (optionally with Lewis lone-pair dots) in a box."""
    return representation_specs("lewis" if lewis else "structural",
                                atoms, bonds, w, h)


def skeletal_specs(atoms, bonds, w, h):
    return representation_specs("skeletal", atoms, bonds, w, h)


def condensed_specs(atoms, bonds, w, h):
    return representation_specs("condensed", atoms, bonds, w, h)
