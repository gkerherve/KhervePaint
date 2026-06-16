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
}

CATEGORIES = [
    ("Chamber & sources",
     ["chamber", "analyser", "xray_source", "ion_gun",
      "electron_gun", "manipulator"]),
    ("Pumps",
     ["turbo_pump", "ion_pump", "scroll_pump", "rotary_pump", "cryo_pump"]),
    ("Valves & fittings",
     ["gate_valve", "angle_valve", "leak_valve", "gauge",
      "flange", "bellows", "viewport"]),
]


_BUILDERS = {name: globals()["build_" + name] for name in SIZES}


def build_specs(name, w, h):
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
