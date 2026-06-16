'''Schematic vacuum / surface-science symbols (UHV systems: XPS/AES/SIMS).

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

# Palette
_OUT = "#333333"        # outline
_BODY = "#e6e9ee"       # steel / body
_STEEL = "#cfd6de"      # darker steel
_ACC = "#333333"        # accent
_NONE = "none"
_W = 2.0                # outline width
_D = 1.2                # detail width


# ---------------------------------------------------------------------------
# Chamber & sources
# ---------------------------------------------------------------------------

def build_chamber(w, h):
    """UHV chamber: octagon body with short flange stubs on its sides."""
    cx, cy = w * 0.5, h * 0.5
    ow, oh = w * 0.62, h * 0.62
    ox, oy = cx - ow * 0.5, cy - oh * 0.5
    specs = [
        {"shape": "octagon", "x": ox, "y": oy, "w": ow, "h": oh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # flange stubs: top, bottom, left, right + four diagonals approximated
    sw, sh = w * 0.10, h * 0.07
    # top stub
    specs.append({"shape": "rect", "x": cx - sw * 0.5, "y": oy - sh,
                  "w": sw, "h": sh, "stroke": _OUT, "fill": _STEEL, "width": _D})
    # bottom stub
    specs.append({"shape": "rect", "x": cx - sw * 0.5, "y": oy + oh,
                  "w": sw, "h": sh, "stroke": _OUT, "fill": _STEEL, "width": _D})
    # left stub
    specs.append({"shape": "rect", "x": ox - sh, "y": cy - sw * 0.5,
                  "w": sh, "h": sw, "stroke": _OUT, "fill": _STEEL, "width": _D})
    # right stub
    specs.append({"shape": "rect", "x": ox + ow, "y": cy - sw * 0.5,
                  "w": sh, "h": sw, "stroke": _OUT, "fill": _STEEL, "width": _D})
    return specs


def build_analyser(w, h):
    """Hemispherical electron analyser: halfcircle dome on a snout column."""
    dome_w = w * 0.78
    dome_h = h * 0.58
    dome_x = (w - dome_w) * 0.5
    dome_y = h * 0.06
    specs = [
        {"shape": "halfcircle", "x": dome_x, "y": dome_y,
         "w": dome_w, "h": dome_h, "stroke": _OUT, "fill": _BODY,
         "width": _W, "rotation": 0},
    ]
    # inner hemisphere hint
    in_w = dome_w * 0.55
    in_h = dome_h * 0.55
    specs.append({"shape": "halfcircle", "x": (w - in_w) * 0.5,
                  "y": dome_y + (dome_h - in_h), "w": in_w, "h": in_h,
                  "stroke": _OUT, "fill": _STEEL, "width": _D, "rotation": 0})
    # lens / snout column below
    col_w = w * 0.20
    col_h = h * 0.34
    col_x = (w - col_w) * 0.5
    col_y = dome_y + dome_h
    specs.append({"shape": "rect", "x": col_x, "y": col_y,
                  "w": col_w, "h": col_h, "stroke": _OUT, "fill": _STEEL,
                  "width": _W})
    return specs


def build_xray_source(w, h):
    """Rectangular source body with angled anode line + stub at the sample."""
    bw, bh = w * 0.58, h * 0.62
    bx, by = w * 0.06, (h - bh) * 0.5
    specs = [
        {"shape": "rect", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # angled anode line inside
    specs.append({"shape": "line", "x1": bx + bw * 0.25, "y1": by + bh * 0.25,
                  "x2": bx + bw * 0.75, "y2": by + bh * 0.75,
                  "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": bx + bw * 0.25, "y1": by + bh * 0.75,
                  "x2": bx + bw * 0.55, "y2": by + bh * 0.45,
                  "stroke": _ACC, "width": _D})
    # short stub pointing at the sample (right)
    stub_y = by + bh * 0.5
    specs.append({"shape": "rect", "x": bx + bw, "y": stub_y - h * 0.06,
                  "w": w * 0.14, "h": h * 0.12, "stroke": _OUT,
                  "fill": _STEEL, "width": _D})
    specs.append({"shape": "line", "x1": bx + bw + w * 0.14, "y1": stub_y,
                  "x2": w * 0.96, "y2": stub_y, "stroke": _ACC, "width": _D})
    return specs


def build_ion_gun(w, h):
    """Tapering nozzle: trapezoid (narrow end out) + barrel emitting an arrow."""
    cy = h * 0.5
    # barrel (wide end, left)
    bw, bh = w * 0.30, h * 0.42
    bx, by = w * 0.05, cy - bh * 0.5
    specs = [
        {"shape": "rect", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # tapering trapezoid nozzle (narrow end out -> rotate so it points right)
    tw, th = w * 0.34, h * 0.50
    tx, ty = bx + bw, cy - th * 0.5
    specs.append({"shape": "trapezoid", "x": tx, "y": ty, "w": tw, "h": th,
                  "stroke": _OUT, "fill": _STEEL, "width": _W,
                  "rotation": 90})
    # emitted ion arrow
    specs.append({"shape": "arrow", "x1": tx + tw, "y1": cy,
                  "x2": w * 0.97, "y2": cy, "stroke": _ACC, "width": _W})
    return specs


def build_electron_gun(w, h):
    """Tapering barrel with a filament hint (V) at the wide end."""
    cy = h * 0.5
    bw, bh = w * 0.30, h * 0.46
    bx, by = w * 0.05, cy - bh * 0.5
    specs = [
        {"shape": "rect", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # filament V hint at the wide (left) end
    fx = bx + bw * 0.15
    specs.append({"shape": "line", "x1": fx, "y1": cy - bh * 0.22,
                  "x2": bx + bw * 0.45, "y2": cy,
                  "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": fx, "y1": cy + bh * 0.22,
                  "x2": bx + bw * 0.45, "y2": cy,
                  "stroke": _ACC, "width": _D})
    # tapering trapezoid barrel
    tw, th = w * 0.34, h * 0.46
    tx, ty = bx + bw, cy - th * 0.5
    specs.append({"shape": "trapezoid", "x": tx, "y": ty, "w": tw, "h": th,
                  "stroke": _OUT, "fill": _STEEL, "width": _W,
                  "rotation": 90})
    # emitted electron arrow
    specs.append({"shape": "arrow", "x1": tx + tw, "y1": cy,
                  "x2": w * 0.97, "y2": cy, "stroke": _ACC, "width": _W})
    return specs


def build_manipulator(w, h):
    """Sample manipulator: long vertical rod with a sample stage at bottom."""
    cx = w * 0.5
    rod_w = w * 0.16
    rod_h = h * 0.74
    specs = [
        {"shape": "rect", "x": cx - rod_w * 0.5, "y": h * 0.04,
         "w": rod_w, "h": rod_h, "stroke": _OUT, "fill": _STEEL, "width": _W},
    ]
    # top knob / drive
    kw, kh = w * 0.34, h * 0.10
    specs.append({"shape": "rect", "x": cx - kw * 0.5, "y": h * 0.02,
                  "w": kw, "h": kh, "stroke": _OUT, "fill": _BODY, "width": _D})
    # sample stage plate at bottom
    pw, ph = w * 0.56, h * 0.12
    specs.append({"shape": "rect", "x": cx - pw * 0.5, "y": h * 0.04 + rod_h,
                  "w": pw, "h": ph, "stroke": _OUT, "fill": _BODY, "width": _W})
    return specs


# ---------------------------------------------------------------------------
# Pumps
# ---------------------------------------------------------------------------

def build_turbo_pump(w, h):
    """Circle with angled turbine blade lines inside, on a flange stub."""
    d = min(w, h * 0.82)
    cx = w * 0.5
    cy = h * 0.42
    cir_x = cx - d * 0.5
    cir_y = cy - d * 0.5
    specs = [
        {"shape": "circle", "x": cir_x, "y": cir_y, "w": d, "h": d,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # angled turbine blades
    r = d * 0.5
    n = 8
    for i in range(n):
        a = (2.0 * math.pi * i) / n
        x1 = cx + math.cos(a) * r * 0.35
        y1 = cy + math.sin(a) * r * 0.35
        x2 = cx + math.cos(a + 0.5) * r * 0.92
        y2 = cy + math.sin(a + 0.5) * r * 0.92
        specs.append({"shape": "line", "x1": x1, "y1": y1,
                      "x2": x2, "y2": y2, "stroke": _ACC, "width": _D})
    # hub
    hd = d * 0.16
    specs.append({"shape": "circle", "x": cx - hd * 0.5, "y": cy - hd * 0.5,
                  "w": hd, "h": hd, "stroke": _OUT, "fill": _STEEL,
                  "width": _D})
    # flange stub
    sw, sh = w * 0.34, h * 0.12
    specs.append({"shape": "rect", "x": cx - sw * 0.5, "y": cir_y + d,
                  "w": sw, "h": sh, "stroke": _OUT, "fill": _STEEL,
                  "width": _D})
    return specs


def build_ion_pump(w, h):
    """Rectangular body with a magnet U hint and a flange stub."""
    bw, bh = w * 0.78, h * 0.62
    bx, by = (w - bw) * 0.5, h * 0.08
    specs = [
        {"shape": "rect", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # magnet "U" hint
    ux = bx + bw * 0.22
    uy = by + bh * 0.22
    uw = bw * 0.56
    uh = bh * 0.50
    specs.append({"shape": "line", "x1": ux, "y1": uy,
                  "x2": ux, "y2": uy + uh, "stroke": _ACC, "width": _W})
    specs.append({"shape": "line", "x1": ux, "y1": uy + uh,
                  "x2": ux + uw, "y2": uy + uh, "stroke": _ACC, "width": _W})
    specs.append({"shape": "line", "x1": ux + uw, "y1": uy + uh,
                  "x2": ux + uw, "y2": uy, "stroke": _ACC, "width": _W})
    # flange stub at bottom
    sw, sh = w * 0.30, h * 0.14
    specs.append({"shape": "rect", "x": w * 0.5 - sw * 0.5, "y": by + bh,
                  "w": sw, "h": sh, "stroke": _OUT, "fill": _STEEL,
                  "width": _D})
    return specs


def build_scroll_pump(w, h):
    """Box with an internal spiral (coiled polyline of lines)."""
    bw, bh = w * 0.84, h * 0.84
    bx, by = (w - bw) * 0.5, (h - bh) * 0.5
    specs = [
        {"shape": "rect", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # spiral: archimedean, approximated by a polyline
    cx, cy = w * 0.5, h * 0.5
    rmax = min(bw, bh) * 0.40
    turns = 2.5
    steps = 48
    pts = []
    for i in range(steps + 1):
        t = i / steps
        a = t * turns * 2.0 * math.pi
        r = rmax * t
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    for i in range(len(pts) - 1):
        specs.append({"shape": "line", "x1": pts[i][0], "y1": pts[i][1],
                      "x2": pts[i + 1][0], "y2": pts[i + 1][1],
                      "stroke": _ACC, "width": _D})
    return specs


def build_rotary_pump(w, h):
    """Circle with an off-centre smaller circle (eccentric rotor) on a base."""
    d = min(w, h * 0.78)
    cx = w * 0.5
    cy = h * 0.40
    cir_x = cx - d * 0.5
    cir_y = cy - d * 0.5
    specs = [
        {"shape": "circle", "x": cir_x, "y": cir_y, "w": d, "h": d,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # eccentric rotor circle
    rd = d * 0.46
    rx = cx - rd * 0.5 + d * 0.14
    ry = cy - rd * 0.5 - d * 0.10
    specs.append({"shape": "circle", "x": rx, "y": ry, "w": rd, "h": rd,
                  "stroke": _OUT, "fill": _STEEL, "width": _D})
    # base rect
    bw, bh = w * 0.74, h * 0.16
    specs.append({"shape": "rect", "x": w * 0.5 - bw * 0.5, "y": cir_y + d,
                  "w": bw, "h": bh, "stroke": _OUT, "fill": _STEEL,
                  "width": _W})
    return specs


def build_cryo_pump(w, h):
    """Circle with concentric cold-baffle rings on a flange stub."""
    d = min(w, h * 0.82)
    cx = w * 0.5
    cy = h * 0.42
    cir_x = cx - d * 0.5
    cir_y = cy - d * 0.5
    specs = [
        {"shape": "circle", "x": cir_x, "y": cir_y, "w": d, "h": d,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    for f in (0.66, 0.34):
        rd = d * f
        specs.append({"shape": "circle", "x": cx - rd * 0.5, "y": cy - rd * 0.5,
                      "w": rd, "h": rd, "stroke": _OUT, "fill": _NONE,
                      "width": _D})
    # flange stub
    sw, sh = w * 0.34, h * 0.12
    specs.append({"shape": "rect", "x": cx - sw * 0.5, "y": cir_y + d,
                  "w": sw, "h": sh, "stroke": _OUT, "fill": _STEEL,
                  "width": _D})
    return specs


# ---------------------------------------------------------------------------
# Valves & fittings
# ---------------------------------------------------------------------------

def _bowtie(cx, cy, bw, bh):
    """Two triangles tip-to-tip forming a bow-tie valve symbol."""
    half = bw * 0.5
    # left triangle: box left half, pointing right (rotation 90 -> apex right)
    left = {"shape": "triangle", "x": cx - half, "y": cy - bh * 0.5,
            "w": half, "h": bh, "stroke": _OUT, "fill": _BODY,
            "width": _W, "rotation": 90}
    # right triangle: box right half, pointing left (rotation 270 -> apex left)
    right = {"shape": "triangle", "x": cx, "y": cy - bh * 0.5,
             "w": half, "h": bh, "stroke": _OUT, "fill": _BODY,
             "width": _W, "rotation": 270}
    return [left, right]


def build_gate_valve(w, h):
    """Bow-tie with a handle stem on top."""
    cx, cy = w * 0.5, h * 0.56
    bw, bh = w * 0.72, h * 0.52
    specs = _bowtie(cx, cy, bw, bh)
    # handle stem
    specs.append({"shape": "line", "x1": cx, "y1": cy - bh * 0.5,
                  "x2": cx, "y2": h * 0.10, "stroke": _ACC, "width": _W})
    # handle top bar
    specs.append({"shape": "line", "x1": cx - w * 0.18, "y1": h * 0.10,
                  "x2": cx + w * 0.18, "y2": h * 0.10,
                  "stroke": _ACC, "width": _W})
    return specs


def build_angle_valve(w, h):
    """Bow-tie with one port turned 90° (an L of two ports)."""
    cx, cy = w * 0.46, h * 0.56
    bw, bh = w * 0.56, h * 0.46
    specs = _bowtie(cx, cy, bw, bh)
    # horizontal port stub (left)
    specs.append({"shape": "line", "x1": cx - bw * 0.5, "y1": cy,
                  "x2": w * 0.06, "y2": cy, "stroke": _ACC, "width": _W})
    # vertical port stub (up) from centre -> L shape
    specs.append({"shape": "line", "x1": cx, "y1": cy,
                  "x2": cx, "y2": h * 0.08, "stroke": _ACC, "width": _W})
    # small flange at vertical port end
    specs.append({"shape": "line", "x1": cx - w * 0.10, "y1": h * 0.08,
                  "x2": cx + w * 0.10, "y2": h * 0.08,
                  "stroke": _ACC, "width": _W})
    return specs


def build_leak_valve(w, h):
    """Bow-tie with a fine-adjust needle hint (a small triangle/arrow)."""
    cx, cy = w * 0.5, h * 0.56
    bw, bh = w * 0.66, h * 0.50
    specs = _bowtie(cx, cy, bw, bh)
    # needle hint: small triangle pointing into the bow-tie from top
    nw, nh = w * 0.16, h * 0.20
    specs.append({"shape": "triangle", "x": cx - nw * 0.5,
                  "y": cy - bh * 0.5 - nh, "w": nw, "h": nh,
                  "stroke": _OUT, "fill": _STEEL, "width": _D,
                  "rotation": 180})
    # adjust stem
    specs.append({"shape": "line", "x1": cx, "y1": cy - bh * 0.5 - nh,
                  "x2": cx, "y2": h * 0.10, "stroke": _ACC, "width": _D})
    return specs


def build_gauge(w, h):
    """Circle with a needle line and a short stem (pressure gauge)."""
    d = min(w, h * 0.74)
    cx = w * 0.5
    cy = h * 0.40
    cir_x = cx - d * 0.5
    cir_y = cy - d * 0.5
    specs = [
        {"shape": "circle", "x": cir_x, "y": cir_y, "w": d, "h": d,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    # needle
    specs.append({"shape": "line", "x1": cx, "y1": cy,
                  "x2": cx + d * 0.32, "y2": cy - d * 0.28,
                  "stroke": _ACC, "width": _W})
    # short stem
    specs.append({"shape": "line", "x1": cx, "y1": cir_y + d,
                  "x2": cx, "y2": h * 0.96, "stroke": _ACC, "width": _W})
    return specs


def build_flange(w, h):
    """Conflat flange in section: two parallel plates with bolt circles."""
    cy = h * 0.5
    pw = w * 0.18
    ph = h * 0.78
    py = cy - ph * 0.5
    lx = w * 0.30
    rx = w * 0.52
    specs = [
        {"shape": "rect", "x": lx, "y": py, "w": pw, "h": ph,
         "stroke": _OUT, "fill": _STEEL, "width": _W},
        {"shape": "rect", "x": rx, "y": py, "w": pw, "h": ph,
         "stroke": _OUT, "fill": _STEEL, "width": _W},
    ]
    # bolt circles between the plates
    bd = h * 0.12
    bx = (lx + pw + rx) * 0.5 - bd * 0.5
    for fy in (0.30, 0.70):
        specs.append({"shape": "circle", "x": bx, "y": h * fy - bd * 0.5,
                      "w": bd, "h": bd, "stroke": _OUT, "fill": _NONE,
                      "width": _D})
    return specs


def build_bellows(w, h):
    """Accordion: a row of zigzag lines forming flexible bellows + stubs."""
    cy = h * 0.5
    bh = h * 0.46
    x0 = w * 0.16
    x1 = w * 0.84
    n = 6
    seg = (x1 - x0) / n
    specs = []
    # end stubs
    specs.append({"shape": "rect", "x": w * 0.04, "y": cy - bh * 0.35,
                  "w": x0 - w * 0.04, "h": bh * 0.70,
                  "stroke": _OUT, "fill": _STEEL, "width": _D})
    specs.append({"shape": "rect", "x": x1, "y": cy - bh * 0.35,
                  "w": w * 0.96 - x1, "h": bh * 0.70,
                  "stroke": _OUT, "fill": _STEEL, "width": _D})
    # zigzag bellows
    top = cy - bh * 0.5
    bot = cy + bh * 0.5
    px, py = x0, cy
    for i in range(n):
        mx = x0 + seg * (i + 0.5)
        ex = x0 + seg * (i + 1)
        ey = top if i % 2 == 0 else bot
        specs.append({"shape": "line", "x1": px, "y1": py,
                      "x2": mx, "y2": ey, "stroke": _ACC, "width": _W})
        specs.append({"shape": "line", "x1": mx, "y1": ey,
                      "x2": ex, "y2": cy, "stroke": _ACC, "width": _W})
        px, py = ex, cy
    return specs


def build_viewport(w, h):
    """Flange ring: two concentric circles (window / viewport)."""
    d = min(w, h) * 0.86
    cx, cy = w * 0.5, h * 0.5
    specs = [
        {"shape": "circle", "x": cx - d * 0.5, "y": cy - d * 0.5,
         "w": d, "h": d, "stroke": _OUT, "fill": _STEEL, "width": _W},
    ]
    di = d * 0.64
    specs.append({"shape": "circle", "x": cx - di * 0.5, "y": cy - di * 0.5,
                  "w": di, "h": di, "stroke": _OUT, "fill": _BODY,
                  "width": _W})
    return specs


# ---------------------------------------------------------------------------
# Gauges & pressure
# ---------------------------------------------------------------------------

def build_pirani_gauge(w, h):
    """Pirani gauge: circle body with a heated-filament zigzag + stem + tag."""
    cx = w * 0.5
    bw, bh = w * 0.60, w * 0.60
    bx, by = cx - bw * 0.5, h * 0.06
    specs = [
        {"shape": "circle", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    fy = by + bh * 0.5
    x0 = bx + bw * 0.24
    seg = (bw * 0.52) / 4.0
    amp = bh * 0.12
    pts = [(x0, fy)]
    for i in range(1, 5):
        pts.append((x0 + seg * i, fy + (amp if i % 2 else -amp)))
    for i in range(len(pts) - 1):
        specs.append({"shape": "line", "x1": pts[i][0], "y1": pts[i][1],
                      "x2": pts[i + 1][0], "y2": pts[i + 1][1],
                      "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh,
                  "x2": cx, "y2": h * 0.98, "stroke": _OUT, "width": _W})
    specs.append({"shape": "text", "text": "Pi", "x": cx, "y": by + bh * 0.78,
                  "size": h * 0.085, "color": _ACC})
    return specs


def build_penning_gauge(w, h):
    """Penning cold-cathode gauge: circle with crossed-field hint + stem."""
    cx = w * 0.5
    bw, bh = w * 0.60, w * 0.60
    bx, by = cx - bw * 0.5, h * 0.06
    cy = by + bh * 0.5
    specs = [
        {"shape": "circle", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    r = bw * 0.22
    specs.append({"shape": "line", "x1": cx - r, "y1": cy - r,
                  "x2": cx + r, "y2": cy + r, "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": cx - r, "y1": cy + r,
                  "x2": cx + r, "y2": cy - r, "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": bx + bw * 0.18, "y1": cy - r * 1.4,
                  "x2": bx + bw * 0.82, "y2": cy - r * 1.4,
                  "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": bx + bw * 0.18, "y1": cy + r * 1.4,
                  "x2": bx + bw * 0.82, "y2": cy + r * 1.4,
                  "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh,
                  "x2": cx, "y2": h * 0.98, "stroke": _OUT, "width": _W})
    specs.append({"shape": "text", "text": "Pen", "x": cx, "y": by + bh * 0.80,
                  "size": h * 0.075, "color": _ACC})
    return specs


def build_ion_gauge(w, h):
    """Bayard-Alpert hot-cathode ion gauge: grid arcs + collector + stem."""
    cx = w * 0.5
    bw, bh = w * 0.60, w * 0.60
    bx, by = cx - bw * 0.5, h * 0.06
    cy = by + bh * 0.5
    specs = [
        {"shape": "circle", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    for f, rot in ((0.46, 0.0), (0.30, 180.0)):
        gw = bw * f
        gh = bh * f
        specs.append({"shape": "halfcircle", "x": cx - gw * 0.5,
                      "y": cy - gh * 0.5, "w": gw, "h": gh,
                      "stroke": _ACC, "fill": _NONE, "width": _D,
                      "rotation": rot})
    specs.append({"shape": "line", "x1": cx, "y1": cy - bh * 0.30,
                  "x2": cx, "y2": cy + bh * 0.30, "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh,
                  "x2": cx, "y2": h * 0.98, "stroke": _OUT, "width": _W})
    specs.append({"shape": "text", "text": "IG", "x": bx + bw * 0.80,
                  "y": by + bh * 0.20, "size": h * 0.075, "color": _ACC})
    return specs


def build_capacitance_manometer(w, h):
    """Baratron capacitance manometer: capsule with a diaphragm + stem."""
    cx = w * 0.5
    bw, bh = w * 0.62, w * 0.62
    bx, by = cx - bw * 0.5, h * 0.06
    cy = by + bh * 0.5
    specs = [
        {"shape": "circle", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    gap = bh * 0.045
    x1 = bx + bw * 0.18
    x2 = bx + bw * 0.82
    specs.append({"shape": "line", "x1": x1, "y1": cy - gap,
                  "x2": x2, "y2": cy - gap, "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": x1, "y1": cy + gap,
                  "x2": x2, "y2": cy + gap, "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh,
                  "x2": cx, "y2": h * 0.98, "stroke": _OUT, "width": _W})
    specs.append({"shape": "text", "text": "CDG", "x": cx, "y": by + bh * 0.80,
                  "size": h * 0.070, "color": _ACC})
    return specs


def build_bourdon_gauge(w, h):
    """Bourdon dial gauge: white face, C-shaped tube, needle + short stem."""
    cx = w * 0.5
    bw, bh = w * 0.62, w * 0.62
    bx, by = cx - bw * 0.5, h * 0.06
    cy = by + bh * 0.5
    specs = [
        {"shape": "circle", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": "#ffffff", "width": _W},
    ]
    tw, th = bw * 0.50, bh * 0.50
    tx, ty = cx - tw * 0.5, cy - th * 0.5
    for rot in (0, 90, 270):
        specs.append({"shape": "quartercircle", "x": tx, "y": ty,
                      "w": tw, "h": th, "stroke": _ACC, "fill": _NONE,
                      "width": _D, "rotation": rot})
    specs.append({"shape": "line", "x1": cx, "y1": cy,
                  "x2": cx + bw * 0.26, "y2": cy - bh * 0.20,
                  "stroke": _OUT, "width": _W})
    hd = bw * 0.06
    specs.append({"shape": "circle", "x": cx - hd * 0.5, "y": cy - hd * 0.5,
                  "w": hd, "h": hd, "stroke": _OUT, "fill": _OUT, "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh,
                  "x2": cx, "y2": h * 0.98, "stroke": _OUT, "width": _W})
    return specs


def build_manometer(w, h):
    """U-tube manometer: two vertical tubes + curved bottom + liquid."""
    lx = w * 0.34
    rx = w * 0.66
    top = h * 0.06
    bot = h * 0.82
    specs = [
        {"shape": "line", "x1": lx - w * 0.05, "y1": top,
         "x2": lx - w * 0.05, "y2": bot, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": lx + w * 0.05, "y1": top,
         "x2": lx + w * 0.05, "y2": bot, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": rx - w * 0.05, "y1": top,
         "x2": rx - w * 0.05, "y2": bot, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": rx + w * 0.05, "y1": top,
         "x2": rx + w * 0.05, "y2": bot, "stroke": _OUT, "width": _W},
    ]
    arc_w = (rx + w * 0.05) - (lx - w * 0.05)
    arc_h = h * 0.18
    specs.append({"shape": "halfcircle", "x": lx - w * 0.05,
                  "y": bot - arc_h * 0.5, "w": arc_w, "h": arc_h,
                  "stroke": _OUT, "fill": _NONE, "width": _W,
                  "rotation": 180})
    l_top = h * 0.30
    r_top = h * 0.52
    specs.append({"shape": "rect", "x": lx - w * 0.05, "y": l_top,
                  "w": w * 0.10, "h": bot - l_top, "stroke": _NONE,
                  "fill": _STEEL, "width": _D})
    specs.append({"shape": "rect", "x": rx - w * 0.05, "y": r_top,
                  "w": w * 0.10, "h": bot - r_top, "stroke": _NONE,
                  "fill": _STEEL, "width": _D})
    return specs


def build_pressure_transducer(w, h):
    """ISA transmitter: circle 'PT' with a ticked signal line + stem."""
    cx = w * 0.5
    bw, bh = w * 0.60, w * 0.60
    bx, by = cx - bw * 0.5, h * 0.16
    specs = [
        {"shape": "circle", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "text", "text": "PT", "x": cx, "y": by + bh * 0.5,
         "size": h * 0.090, "color": _ACC},
    ]
    sig_top = h * 0.02
    specs.append({"shape": "line", "x1": cx, "y1": by, "x2": cx, "y2": sig_top,
                  "stroke": _ACC, "width": _D})
    for ty in (by * 0.55, by * 0.40):
        specs.append({"shape": "line", "x1": cx - w * 0.06, "y1": ty + h * 0.02,
                      "x2": cx + w * 0.06, "y2": ty - h * 0.02,
                      "stroke": _ACC, "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh,
                  "x2": cx, "y2": h * 0.98, "stroke": _OUT, "width": _W})
    return specs


# ---------------------------------------------------------------------------
# More pumps
# ---------------------------------------------------------------------------

def build_diaphragm_pump(w, h):
    """Diaphragm pump: box body, curved diaphragm + two check-valve tris."""
    bw, bh = w * 0.70, h * 0.56
    bx, by = (w - bw) * 0.5, h * 0.10
    cx = w * 0.5
    cy = by + bh * 0.5
    specs = [
        {"shape": "rect", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    dw = bw * 0.74
    dh = bh * 0.34
    specs.append({"shape": "halfcircle", "x": cx - dw * 0.5, "y": cy - dh * 0.5,
                  "w": dw, "h": dh, "stroke": _ACC, "fill": _NONE,
                  "width": _D, "rotation": 0})
    tw, th = bw * 0.16, bh * 0.22
    specs.append({"shape": "triangle", "x": bx + bw * 0.16,
                  "y": by + bh * 0.18, "w": tw, "h": th,
                  "stroke": _OUT, "fill": _STEEL, "width": _D, "rotation": 0})
    specs.append({"shape": "triangle", "x": bx + bw * 0.68,
                  "y": by + bh * 0.18, "w": tw, "h": th,
                  "stroke": _OUT, "fill": _STEEL, "width": _D, "rotation": 0})
    fw, fh = w * 0.16, h * 0.10
    specs.append({"shape": "rect", "x": cx - fw * 0.5, "y": by + bh,
                  "w": fw, "h": fh, "stroke": _OUT, "fill": _STEEL,
                  "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh + fh,
                  "x2": cx, "y2": h * 0.99, "stroke": _OUT, "width": _W})
    return specs


def build_roots_pump(w, h):
    """Roots blower: rounded casing with two interlocking figure-8 lobes."""
    bw, bh = w * 0.74, h * 0.50
    bx, by = (w - bw) * 0.5, h * 0.10
    cx = w * 0.5
    cy = by + bh * 0.5
    specs = [
        {"shape": "rounded_rect", "x": bx, "y": by, "w": bw, "h": bh,
         "radius": bh * 0.30, "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    lobe_d = bh * 0.40
    off = lobe_d * 0.40
    lcx = cx - bw * 0.18
    specs.append({"shape": "circle", "x": lcx - lobe_d * 0.5,
                  "y": cy - off - lobe_d * 0.5, "w": lobe_d, "h": lobe_d,
                  "stroke": _ACC, "fill": _NONE, "width": _D})
    specs.append({"shape": "circle", "x": lcx - lobe_d * 0.5,
                  "y": cy + off - lobe_d * 0.5, "w": lobe_d, "h": lobe_d,
                  "stroke": _ACC, "fill": _NONE, "width": _D})
    rcx = cx + bw * 0.18
    specs.append({"shape": "circle", "x": rcx - off - lobe_d * 0.5,
                  "y": cy - lobe_d * 0.5, "w": lobe_d, "h": lobe_d,
                  "stroke": _ACC, "fill": _NONE, "width": _D})
    specs.append({"shape": "circle", "x": rcx + off - lobe_d * 0.5,
                  "y": cy - lobe_d * 0.5, "w": lobe_d, "h": lobe_d,
                  "stroke": _ACC, "fill": _NONE, "width": _D})
    fw, fh = w * 0.16, h * 0.10
    specs.append({"shape": "rect", "x": cx - fw * 0.5, "y": by + bh,
                  "w": fw, "h": fh, "stroke": _OUT, "fill": _STEEL,
                  "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh + fh,
                  "x2": cx, "y2": h * 0.99, "stroke": _OUT, "width": _W})
    return specs


def build_getter_pump(w, h):
    """NEG getter pump: steel-filled circle with diagonal hatch + stub."""
    cx = w * 0.5
    bw, bh = w * 0.62, w * 0.62
    bx, by = cx - bw * 0.5, h * 0.10
    specs = [
        {"shape": "circle", "x": bx, "y": by, "w": bw, "h": bh,
         "stroke": _OUT, "fill": _STEEL, "width": _W},
    ]
    n = 5
    for i in range(1, n):
        f = i / n
        specs.append({"shape": "line",
                      "x1": bx + bw * f, "y1": by + bh * 0.10,
                      "x2": bx + bw * 0.10, "y2": by + bh * f,
                      "stroke": _ACC, "width": _D})
        specs.append({"shape": "line",
                      "x1": bx + bw, "y1": by + bh * f,
                      "x2": bx + bw * f, "y2": by + bh,
                      "stroke": _ACC, "width": _D})
    specs.append({"shape": "text", "text": "NEG", "x": cx, "y": by + bh * 0.5,
                  "size": h * 0.075, "color": _OUT})
    fw, fh = w * 0.16, h * 0.10
    specs.append({"shape": "rect", "x": cx - fw * 0.5, "y": by + bh,
                  "w": fw, "h": fh, "stroke": _OUT, "fill": _STEEL,
                  "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh + fh,
                  "x2": cx, "y2": h * 0.99, "stroke": _OUT, "width": _W})
    return specs


def build_sublimation_pump(w, h):
    """Titanium sublimation pump: chamber with a filament coil + stub."""
    bw, bh = w * 0.66, h * 0.52
    bx, by = (w - bw) * 0.5, h * 0.10
    cx = w * 0.5
    cy = by + bh * 0.45
    specs = [
        {"shape": "rounded_rect", "x": bx, "y": by, "w": bw, "h": bh,
         "radius": bh * 0.14, "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    x0 = bx + bw * 0.18
    seg = (bw * 0.64) / 5.0
    amp = bh * 0.16
    pts = [(x0, cy)]
    for i in range(1, 6):
        pts.append((x0 + seg * i, cy + (amp if i % 2 else -amp)))
    for i in range(len(pts) - 1):
        specs.append({"shape": "line", "x1": pts[i][0], "y1": pts[i][1],
                      "x2": pts[i + 1][0], "y2": pts[i + 1][1],
                      "stroke": _ACC, "width": _D})
    specs.append({"shape": "text", "text": "TSP", "x": cx, "y": by + bh * 0.82,
                  "size": h * 0.070, "color": _ACC})
    fw, fh = w * 0.16, h * 0.10
    specs.append({"shape": "rect", "x": cx - fw * 0.5, "y": by + bh,
                  "w": fw, "h": fh, "stroke": _OUT, "fill": _STEEL,
                  "width": _D})
    specs.append({"shape": "line", "x1": cx, "y1": by + bh + fh,
                  "x2": cx, "y2": h * 0.99, "stroke": _OUT, "width": _W})
    return specs


# ---------------------------------------------------------------------------
# More valves
# ---------------------------------------------------------------------------

def build_butterfly_valve(w, h):
    cx, cy = w * 0.5, h * 0.55
    r = w * 0.34
    return [
        {"shape": "circle", "x": cx - r, "y": cy - r, "w": r * 2, "h": r * 2,
         "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "line", "x1": cx - r * 0.72, "y1": cy + r * 0.72,
         "x2": cx + r * 0.72, "y2": cy - r * 0.72, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": cx, "y1": cy - r, "x2": cx, "y2": h * 0.08,
         "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx - w * 0.12, "y1": h * 0.08,
         "x2": cx + w * 0.12, "y2": h * 0.08, "stroke": _OUT, "width": _W},
    ]


def build_ball_valve(w, h):
    cx, cy = w * 0.5, h * 0.55
    bw, bh = w * 0.72, h * 0.42
    parts = _bowtie(cx, cy, bw, bh)
    r = bh * 0.34
    parts += [
        {"shape": "circle", "x": cx - r, "y": cy - r, "w": r * 2, "h": r * 2,
         "stroke": _OUT, "fill": _STEEL, "width": _W},
        {"shape": "line", "x1": cx, "y1": cy - r, "x2": cx, "y2": h * 0.16,
         "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx, "y1": h * 0.16,
         "x2": cx + w * 0.3, "y2": h * 0.16, "stroke": _OUT, "width": _W},
    ]
    return parts


def build_needle_valve(w, h):
    cx, cy = w * 0.5, h * 0.55
    bw, bh = w * 0.72, h * 0.42
    parts = _bowtie(cx, cy, bw, bh)
    nw = w * 0.1
    parts += [
        {"shape": "triangle", "x": cx - nw * 0.5, "y": cy - bh * 0.45,
         "w": nw, "h": bh * 0.95, "rotation": 180.0,
         "stroke": _OUT, "fill": _STEEL, "width": _D},
        {"shape": "line", "x1": cx, "y1": cy - bh * 0.5, "x2": cx,
         "y2": h * 0.12, "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx - w * 0.13, "y1": h * 0.12,
         "x2": cx + w * 0.13, "y2": h * 0.12, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": cx, "y1": h * 0.12, "x2": cx, "y2": h * 0.04,
         "stroke": _OUT, "width": _D},
    ]
    return parts


def build_solenoid_valve(w, h):
    cx, cy = w * 0.5, h * 0.55
    bw, bh = w * 0.72, h * 0.42
    parts = _bowtie(cx, cy, bw, bh)
    parts.append({"shape": "line", "x1": cx, "y1": cy - bh * 0.5,
                  "x2": cx, "y2": h * 0.28, "stroke": _OUT, "width": _D})
    boxw, boxh = w * 0.38, h * 0.2
    bx, by = cx - boxw * 0.5, h * 0.08
    parts += [
        {"shape": "rect", "x": bx, "y": by, "w": boxw, "h": boxh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "line", "x1": bx, "y1": by + boxh, "x2": bx + boxw, "y2": by,
         "stroke": _OUT, "width": _D},
    ]
    return parts


def build_manual_valve(w, h):
    cx, cy = w * 0.5, h * 0.55
    bw, bh = w * 0.72, h * 0.42
    parts = _bowtie(cx, cy, bw, bh)
    parts.append({"shape": "line", "x1": cx, "y1": cy - bh * 0.5,
                  "x2": cx, "y2": h * 0.22, "stroke": _OUT, "width": _D})
    hw, hh = w * 0.42, h * 0.12
    parts.append({"shape": "ellipse", "x": cx - hw * 0.5, "y": h * 0.16,
                  "w": hw, "h": hh, "stroke": _OUT, "fill": _BODY, "width": _W})
    return parts


def build_relief_valve(w, h):
    inx, iny = w * 0.08, h * 0.7
    cx = w * 0.42
    parts = [
        {"shape": "line", "x1": inx, "y1": iny, "x2": cx, "y2": iny,
         "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": inx, "y1": iny - h * 0.07, "x2": inx,
         "y2": iny + h * 0.07, "stroke": _OUT, "width": _W},
        {"shape": "triangle", "x": cx - w * 0.16, "y": iny - h * 0.18,
         "w": w * 0.32, "h": h * 0.18, "rotation": 0.0,
         "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "triangle", "x": cx - w * 0.16, "y": iny - h * 0.36,
         "w": w * 0.32, "h": h * 0.18, "rotation": 180.0,
         "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "line", "x1": cx, "y1": iny - h * 0.36, "x2": cx,
         "y2": h * 0.34, "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx, "y1": h * 0.34, "x2": cx + w * 0.1,
         "y2": h * 0.3, "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx + w * 0.1, "y1": h * 0.3, "x2": cx - w * 0.1,
         "y2": h * 0.25, "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx - w * 0.1, "y1": h * 0.25, "x2": cx + w * 0.1,
         "y2": h * 0.2, "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx + w * 0.1, "y1": h * 0.2, "x2": cx,
         "y2": h * 0.16, "stroke": _OUT, "width": _D},
        {"shape": "rect", "x": cx - w * 0.1, "y": h * 0.08, "w": w * 0.2,
         "h": h * 0.08, "stroke": _OUT, "fill": _STEEL, "width": _W},
    ]
    return parts


# ---------------------------------------------------------------------------
# Lines & fittings
# ---------------------------------------------------------------------------

def build_pipe(w, h):
    cy = h * 0.5
    ph = h * 0.32
    return [
        {"shape": "rect", "x": w * 0.06, "y": cy - ph * 0.5,
         "w": w * 0.88, "h": ph, "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "line", "x1": w * 0.06, "y1": cy - ph * 0.9,
         "x2": w * 0.06, "y2": cy + ph * 0.9, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": w * 0.94, "y1": cy - ph * 0.9,
         "x2": w * 0.94, "y2": cy + ph * 0.9, "stroke": _OUT, "width": _W},
    ]


def build_tee(w, h):
    cx = w * 0.5
    cy = h * 0.62
    ph = h * 0.26
    return [
        {"shape": "rect", "x": w * 0.06, "y": cy - ph * 0.5,
         "w": w * 0.88, "h": ph, "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "rect", "x": cx - ph * 0.5, "y": h * 0.1,
         "w": ph, "h": cy - ph * 0.5 - h * 0.1, "stroke": _OUT,
         "fill": _BODY, "width": _W},
        {"shape": "line", "x1": w * 0.06, "y1": cy - ph * 0.85,
         "x2": w * 0.06, "y2": cy + ph * 0.85, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": w * 0.94, "y1": cy - ph * 0.85,
         "x2": w * 0.94, "y2": cy + ph * 0.85, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": cx - ph * 0.85, "y1": h * 0.1,
         "x2": cx + ph * 0.85, "y2": h * 0.1, "stroke": _OUT, "width": _W},
    ]


def build_elbow(w, h):
    ph = h * 0.24
    cy = h * 0.78
    cx = w * 0.74
    return [
        {"shape": "rect", "x": w * 0.08, "y": cy - ph * 0.5,
         "w": cx - w * 0.08, "h": ph, "stroke": _OUT, "fill": _BODY,
         "width": _W},
        {"shape": "rect", "x": cx - ph * 0.5, "y": h * 0.1,
         "w": ph, "h": cy - ph * 0.5 - h * 0.1, "stroke": _OUT,
         "fill": _BODY, "width": _W},
        {"shape": "quartercircle", "x": cx - ph * 0.5, "y": cy - ph * 0.5,
         "w": ph, "h": ph, "stroke": _OUT, "fill": _STEEL,
         "width": _D, "rotation": 0.0},
        {"shape": "line", "x1": w * 0.08, "y1": cy - ph * 0.85,
         "x2": w * 0.08, "y2": cy + ph * 0.85, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": cx - ph * 0.85, "y1": h * 0.1,
         "x2": cx + ph * 0.85, "y2": h * 0.1, "stroke": _OUT, "width": _W},
    ]


def build_reducer(w, h):
    cy = h * 0.5
    bigh = h * 0.5
    smallh = h * 0.26
    return [
        {"shape": "rect", "x": w * 0.06, "y": cy - bigh * 0.5,
         "w": w * 0.22, "h": bigh, "stroke": _OUT, "fill": _BODY,
         "width": _W},
        {"shape": "rect", "x": w * 0.72, "y": cy - smallh * 0.5,
         "w": w * 0.22, "h": smallh, "stroke": _OUT, "fill": _BODY,
         "width": _W},
        {"shape": "trapezoid", "x": w * 0.28, "y": cy - bigh * 0.5,
         "w": w * 0.44, "h": bigh, "rotation": 90.0,
         "stroke": _OUT, "fill": _STEEL, "width": _W},
        {"shape": "line", "x1": w * 0.06, "y1": cy - bigh * 0.85,
         "x2": w * 0.06, "y2": cy + bigh * 0.85, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": w * 0.94, "y1": cy - smallh * 0.85,
         "x2": w * 0.94, "y2": cy + smallh * 0.85, "stroke": _OUT,
         "width": _W},
    ]


def build_blank_flange(w, h):
    cy = h * 0.5
    ph = h * 0.3
    capx = w * 0.66
    capw = w * 0.16
    caph = h * 0.62
    return [
        {"shape": "rect", "x": w * 0.08, "y": cy - ph * 0.5,
         "w": capx - w * 0.08, "h": ph, "stroke": _OUT, "fill": _BODY,
         "width": _W},
        {"shape": "rect", "x": capx, "y": cy - caph * 0.5, "w": capw,
         "h": caph, "stroke": _OUT, "fill": _STEEL, "width": _W},
        {"shape": "circle", "x": capx + capw * 0.3, "y": cy - caph * 0.32,
         "w": w * 0.045, "h": w * 0.045, "stroke": _OUT, "fill": _OUT,
         "width": _D},
        {"shape": "circle", "x": capx + capw * 0.3, "y": cy + caph * 0.26,
         "w": w * 0.045, "h": w * 0.045, "stroke": _OUT, "fill": _OUT,
         "width": _D},
        {"shape": "line", "x1": w * 0.08, "y1": cy - ph * 0.85,
         "x2": w * 0.08, "y2": cy + ph * 0.85, "stroke": _OUT, "width": _W},
    ]


def build_cold_trap(w, h):
    cx = w * 0.5
    vw, vh = w * 0.46, h * 0.62
    vx, vy = cx - vw * 0.5, h * 0.2
    return [
        {"shape": "rounded_rect", "x": vx, "y": vy, "w": vw, "h": vh,
         "radius": w * 0.1, "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "line", "x1": cx - vw * 0.2, "y1": vy, "x2": cx - vw * 0.2,
         "y2": h * 0.06, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": cx + vw * 0.2, "y1": vy, "x2": cx + vw * 0.2,
         "y2": h * 0.06, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": vx + vw * 0.18, "y1": vy + vh * 0.4,
         "x2": vx + vw * 0.82, "y2": vy + vh * 0.4, "stroke": _ACC,
         "width": _D},
        {"shape": "line", "x1": vx + vw * 0.18, "y1": vy + vh * 0.6,
         "x2": vx + vw * 0.82, "y2": vy + vh * 0.6, "stroke": _ACC,
         "width": _D},
        {"shape": "line", "x1": vx + vw * 0.18, "y1": vy + vh * 0.8,
         "x2": vx + vw * 0.82, "y2": vy + vh * 0.8, "stroke": _ACC,
         "width": _D},
        {"shape": "text", "text": "LN2", "x": cx - vw * 0.22,
         "y": vy + vh * 0.18, "size": h * 0.07, "color": _OUT},
    ]


def build_mass_flow_controller(w, h):
    cy = h * 0.5
    ph = h * 0.2
    boxw, boxh = w * 0.5, h * 0.5
    bx, by = w * 0.5 - boxw * 0.5, cy - boxh * 0.5
    parts = [
        {"shape": "line", "x1": w * 0.04, "y1": cy, "x2": bx, "y2": cy,
         "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": bx + boxw, "y1": cy, "x2": w * 0.96, "y2": cy,
         "stroke": _OUT, "width": _W},
        {"shape": "rect", "x": bx, "y": by, "w": boxw, "h": boxh,
         "stroke": _OUT, "fill": _BODY, "width": _W},
    ]
    parts += _bowtie(w * 0.5, by + boxh * 0.62, boxw * 0.4, boxh * 0.3)
    parts += [
        {"shape": "line", "x1": w * 0.5, "y1": by + boxh * 0.47,
         "x2": w * 0.5, "y2": by + boxh * 0.2, "stroke": _OUT, "width": _D},
        {"shape": "text", "text": "MFC", "x": bx + boxw * 0.18,
         "y": by + boxh * 0.04, "size": h * 0.13, "color": _OUT},
        {"shape": "line", "x1": w * 0.04, "y1": cy - ph * 0.7,
         "x2": w * 0.04, "y2": cy + ph * 0.7, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": w * 0.96, "y1": cy - ph * 0.7,
         "x2": w * 0.96, "y2": cy + ph * 0.7, "stroke": _OUT, "width": _W},
    ]
    return parts


def build_regulator(w, h):
    cx = w * 0.42
    bodyw, bodyh = w * 0.4, h * 0.34
    by = h * 0.42
    domew = bodyw * 1.05
    return [
        {"shape": "rect", "x": cx - bodyw * 0.5, "y": by, "w": bodyw,
         "h": bodyh, "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "halfcircle", "x": cx - domew * 0.5, "y": by - domew * 0.5,
         "w": domew, "h": domew, "stroke": _OUT, "fill": _STEEL,
         "width": _W, "rotation": 0.0},
        {"shape": "line", "x1": cx, "y1": by - domew * 0.5, "x2": cx,
         "y2": h * 0.08, "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx - w * 0.08, "y1": h * 0.08,
         "x2": cx + w * 0.08, "y2": h * 0.08, "stroke": _OUT, "width": _W},
        {"shape": "line", "x1": w * 0.04, "y1": by + bodyh * 0.5,
         "x2": cx - bodyw * 0.5, "y2": by + bodyh * 0.5, "stroke": _OUT,
         "width": _W},
        {"shape": "line", "x1": cx + bodyw * 0.5, "y1": by + bodyh * 0.5,
         "x2": w * 0.7, "y2": by + bodyh * 0.5, "stroke": _OUT, "width": _W},
        {"shape": "circle", "x": w * 0.72, "y": by - h * 0.02,
         "w": w * 0.2, "h": w * 0.2, "stroke": _OUT, "fill": "#ffffff",
         "width": _W},
        {"shape": "line", "x1": w * 0.82, "y1": by + h * 0.08,
         "x2": w * 0.87, "y2": by + h * 0.03, "stroke": _OUT, "width": _D},
    ]


def build_gas_cylinder(w, h):
    cx = w * 0.5
    bw = w * 0.62
    bx = cx - bw * 0.5
    by = h * 0.16
    bh = h * 0.74
    return [
        {"shape": "rounded_rect", "x": bx, "y": by, "w": bw, "h": bh,
         "radius": bw * 0.45, "stroke": _OUT, "fill": _BODY, "width": _W},
        {"shape": "rect", "x": cx - bw * 0.16, "y": h * 0.06,
         "w": bw * 0.32, "h": h * 0.1, "stroke": _OUT, "fill": _STEEL,
         "width": _W},
        {"shape": "line", "x1": cx, "y1": h * 0.06, "x2": cx, "y2": h * 0.02,
         "stroke": _OUT, "width": _D},
        {"shape": "line", "x1": cx + bw * 0.16, "y1": h * 0.1,
         "x2": cx + bw * 0.34, "y2": h * 0.1, "stroke": _OUT, "width": _W},
    ]


# ---------------------------------------------------------------------------
# Sizes / labels / categories
# ---------------------------------------------------------------------------

REFERENCE_MM = 2000.0

SIZES = {
    "chamber": (450.0, 450.0),
    "analyser": (440.0, 500.0),
    "xray_source": (320.0, 220.0),
    "ion_gun": (300.0, 160.0),
    "electron_gun": (300.0, 160.0),
    "manipulator": (220.0, 460.0),
    "turbo_pump": (250.0, 280.0),
    "ion_pump": (260.0, 240.0),
    "scroll_pump": (250.0, 250.0),
    "rotary_pump": (260.0, 270.0),
    "cryo_pump": (250.0, 280.0),
    "gate_valve": (160.0, 180.0),
    "angle_valve": (160.0, 170.0),
    "leak_valve": (160.0, 180.0),
    "gauge": (140.0, 170.0),
    "flange": (140.0, 160.0),
    "bellows": (220.0, 140.0),
    "viewport": (150.0, 150.0),
    # gauges & pressure
    "pirani_gauge": (150.0, 170.0),
    "penning_gauge": (150.0, 170.0),
    "ion_gauge": (150.0, 170.0),
    "capacitance_manometer": (150.0, 170.0),
    "bourdon_gauge": (150.0, 170.0),
    "manometer": (160.0, 260.0),
    "pressure_transducer": (150.0, 170.0),
    # more pumps
    "diaphragm_pump": (250.0, 280.0),
    "roots_pump": (250.0, 280.0),
    "getter_pump": (250.0, 280.0),
    "sublimation_pump": (250.0, 280.0),
    # more valves
    "butterfly_valve": (180.0, 190.0),
    "ball_valve": (190.0, 190.0),
    "needle_valve": (180.0, 200.0),
    "solenoid_valve": (190.0, 200.0),
    "manual_valve": (190.0, 190.0),
    "relief_valve": (190.0, 200.0),
    # lines & fittings
    "pipe": (240.0, 80.0),
    "tee": (200.0, 180.0),
    "elbow": (180.0, 180.0),
    "reducer": (220.0, 120.0),
    "blank_flange": (200.0, 140.0),
    "cold_trap": (200.0, 300.0),
    "mass_flow_controller": (240.0, 160.0),
    "regulator": (240.0, 220.0),
    "gas_cylinder": (180.0, 420.0),
}

LABELS = {
    "chamber": "UHV chamber",
    "analyser": "Hemispherical analyser",
    "xray_source": "X-ray source",
    "ion_gun": "Ion gun",
    "electron_gun": "Electron gun",
    "manipulator": "Manipulator",
    "turbo_pump": "Turbo pump",
    "ion_pump": "Ion pump",
    "scroll_pump": "Scroll pump",
    "rotary_pump": "Rotary pump",
    "cryo_pump": "Cryo pump",
    "gate_valve": "Gate valve",
    "angle_valve": "Angle valve",
    "leak_valve": "Leak valve",
    "gauge": "Pressure gauge",
    "flange": "Flange (CF)",
    "bellows": "Bellows",
    "viewport": "Viewport",
    "pirani_gauge": "Pirani gauge",
    "penning_gauge": "Penning gauge",
    "ion_gauge": "Ion gauge (Bayard-Alpert)",
    "capacitance_manometer": "Capacitance manometer (Baratron)",
    "bourdon_gauge": "Bourdon gauge",
    "manometer": "U-tube manometer",
    "pressure_transducer": "Pressure transducer",
    "diaphragm_pump": "Diaphragm pump",
    "roots_pump": "Roots pump (blower)",
    "getter_pump": "Getter pump (NEG)",
    "sublimation_pump": "Titanium sublimation pump",
    "butterfly_valve": "Butterfly valve",
    "ball_valve": "Ball valve",
    "needle_valve": "Needle valve",
    "solenoid_valve": "Solenoid valve",
    "manual_valve": "Manual valve",
    "relief_valve": "Relief valve",
    "pipe": "Pipe",
    "tee": "Tee junction",
    "elbow": "Elbow (90°)",
    "reducer": "Reducer",
    "blank_flange": "Blank flange",
    "cold_trap": "Cold trap (LN2)",
    "mass_flow_controller": "Mass flow controller",
    "regulator": "Pressure regulator",
    "gas_cylinder": "Gas cylinder",
}

CATEGORIES = [
    ("Chamber & sources",
     ["chamber", "analyser", "xray_source", "ion_gun",
      "electron_gun", "manipulator"]),
    ("Pumps",
     ["turbo_pump", "ion_pump", "scroll_pump", "rotary_pump", "cryo_pump",
      "diaphragm_pump", "roots_pump", "getter_pump", "sublimation_pump"]),
    ("Gauges & pressure",
     ["bourdon_gauge", "pirani_gauge", "penning_gauge", "ion_gauge",
      "capacitance_manometer", "manometer", "pressure_transducer", "gauge"]),
    ("Valves",
     ["gate_valve", "angle_valve", "leak_valve", "butterfly_valve",
      "ball_valve", "needle_valve", "solenoid_valve", "manual_valve",
      "relief_valve"]),
    ("Lines & fittings",
     ["pipe", "tee", "elbow", "reducer", "flange", "blank_flange",
      "bellows", "viewport", "cold_trap", "mass_flow_controller",
      "regulator", "gas_cylinder"]),
]


_BUILDERS = {name: globals()["build_" + name] for name in SIZES}


def build_specs(name, w, h):
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
