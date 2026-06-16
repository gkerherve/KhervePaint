'''Process & instrumentation (P&ID) / process-flow diagram symbols.

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
EQUIP = "#eef2f6"
METAL = "#dfe7ee"
WHITE = "#ffffff"
NONE = "none"
W_OUT = 2
W_DET = 1.2


# ---------------------------------------------------------------- Vessels

def build_tank(w, h):
    """Vertical storage tank: rect body, domed top, short legs."""
    bx = w * 0.18
    bw = w * 0.64
    top = h * 0.12
    body_top = h * 0.20
    body_bot = h * 0.86
    bh = body_bot - body_top
    specs = []
    specs.append({"shape": "halfcircle", "x": bx, "y": top,
                  "w": bw, "h": body_top - top,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT,
                  "rotation": 0})
    specs.append({"shape": "rect", "x": bx, "y": body_top,
                  "w": bw, "h": bh,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": bx + bw * 0.18, "y1": body_bot,
                  "x2": bx + bw * 0.18, "y2": h * 0.98,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": bx + bw * 0.82, "y1": body_bot,
                  "x2": bx + bw * 0.82, "y2": h * 0.98,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


def build_vessel(w, h):
    """Horizontal drum: rect body, domed ends, two saddles."""
    left = w * 0.12
    right = w * 0.88
    body_top = h * 0.30
    body_bot = h * 0.70
    bh = body_bot - body_top
    cap_w = w * 0.12
    specs = []
    specs.append({"shape": "rect", "x": left, "y": body_top,
                  "w": right - left, "h": bh,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT})
    specs.append({"shape": "halfcircle", "x": left - cap_w, "y": body_top,
                  "w": cap_w * 2, "h": bh,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT,
                  "rotation": 270})
    specs.append({"shape": "halfcircle", "x": right - cap_w, "y": body_top,
                  "w": cap_w * 2, "h": bh,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT,
                  "rotation": 90})
    for cx in (left + (right - left) * 0.25, left + (right - left) * 0.75):
        specs.append({"shape": "trapezoid",
                      "x": cx - w * 0.07, "y": body_bot,
                      "w": w * 0.14, "h": h * 0.18,
                      "stroke": OUTLINE, "fill": METAL, "width": W_OUT,
                      "rotation": 180})
    return specs


def build_column(w, h):
    """Tall distillation column with internal tray lines."""
    bx = w * 0.28
    bw = w * 0.44
    top = h * 0.05
    bh = h * 0.90
    specs = []
    specs.append({"shape": "rounded_rect", "x": bx, "y": top,
                  "w": bw, "h": bh, "radius": bw * 0.45,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT})
    n = 6
    for i in range(1, n + 1):
        ty = top + bh * (i / (n + 1))
        specs.append({"shape": "line",
                      "x1": bx + bw * 0.10, "y1": ty,
                      "x2": bx + bw * 0.90, "y2": ty,
                      "stroke": OUTLINE, "width": W_DET})
    return specs


def build_reactor(w, h):
    """Stirred reactor: jacketed vessel with stirrer shaft + impeller."""
    jx = w * 0.16
    jw = w * 0.68
    jtop = h * 0.12
    jh = h * 0.78
    specs = []
    specs.append({"shape": "rounded_rect", "x": jx, "y": jtop,
                  "w": jw, "h": jh, "radius": jw * 0.20,
                  "stroke": OUTLINE, "fill": METAL, "width": W_OUT})
    ix = w * 0.24
    iw = w * 0.52
    itop = h * 0.18
    ih = h * 0.66
    specs.append({"shape": "rounded_rect", "x": ix, "y": itop,
                  "w": iw, "h": ih, "radius": iw * 0.30,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT})
    cx = w * 0.50
    specs.append({"shape": "line",
                  "x1": cx, "y1": h * 0.02,
                  "x2": cx, "y2": h * 0.66,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": cx - iw * 0.22, "y1": h * 0.66,
                  "x2": cx + iw * 0.22, "y2": h * 0.66,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


def build_heat_exchanger(w, h):
    """Shell-and-tube exchanger: shell, zigzag tube, two nozzles."""
    left = w * 0.10
    right = w * 0.90
    top = h * 0.30
    bot = h * 0.70
    sh = bot - top
    specs = []
    specs.append({"shape": "rounded_rect", "x": left, "y": top,
                  "w": right - left, "h": sh, "radius": sh * 0.45,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT})
    n = 5
    x0 = left + (right - left) * 0.10
    x1 = right - (right - left) * 0.10
    span = x1 - x0
    hi = top + sh * 0.28
    lo = bot - sh * 0.28
    px = x0
    py = (hi + lo) / 2
    for i in range(n + 1):
        nx = x0 + span * (i / n)
        ny = hi if i % 2 == 0 else lo
        specs.append({"shape": "line", "x1": px, "y1": py,
                      "x2": nx, "y2": ny,
                      "stroke": OUTLINE, "width": W_DET})
        px, py = nx, ny
    specs.append({"shape": "line",
                  "x1": left + (right - left) * 0.20, "y1": top,
                  "x2": left + (right - left) * 0.20, "y2": h * 0.12,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": left + (right - left) * 0.80, "y1": bot,
                  "x2": left + (right - left) * 0.80, "y2": h * 0.88,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


def build_hopper(w, h):
    """Inverted trapezoid (wide top, narrow bottom) with outlet stub."""
    specs = []
    specs.append({"shape": "trapezoid", "x": w * 0.12, "y": h * 0.12,
                  "w": w * 0.76, "h": h * 0.66,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT,
                  "rotation": 180})
    specs.append({"shape": "rect", "x": w * 0.44, "y": h * 0.78,
                  "w": w * 0.12, "h": h * 0.14,
                  "stroke": OUTLINE, "fill": METAL, "width": W_OUT})
    return specs


# ------------------------------------------------------- Rotating equipment

def build_pump(w, h):
    """Centrifugal pump: circle, impeller triangle, tangential discharge."""
    cx = w * 0.50
    cy = h * 0.62
    d = min(w, h) * 0.60
    r = d / 2
    specs = []
    specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                  "w": d, "h": d,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT})
    specs.append({"shape": "triangle", "x": cx - r * 0.45, "y": cy - r * 0.45,
                  "w": r * 0.90, "h": r * 0.90,
                  "stroke": OUTLINE, "fill": METAL, "width": W_DET,
                  "rotation": 90})
    specs.append({"shape": "line",
                  "x1": cx + r * 0.55, "y1": cy - r * 0.84,
                  "x2": cx + r * 0.55, "y2": h * 0.06,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": cx + r * 0.55, "y1": h * 0.06,
                  "x2": cx + r * 1.05, "y2": h * 0.06,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": cx - r, "y1": cy,
                  "x2": w * 0.04, "y2": cy,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


def build_compressor(w, h):
    """Converging trapezoid body with inlet/outlet stubs."""
    specs = []
    specs.append({"shape": "trapezoid", "x": w * 0.18, "y": h * 0.22,
                  "w": w * 0.64, "h": h * 0.56,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT,
                  "rotation": 90})
    cy = h * 0.50
    specs.append({"shape": "line",
                  "x1": w * 0.18, "y1": cy,
                  "x2": w * 0.04, "y2": cy,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": w * 0.82, "y1": cy,
                  "x2": w * 0.96, "y2": cy,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


def build_blower(w, h):
    """Blower: circle (volute scroll) with curved fan blades."""
    cx = w * 0.46
    cy = h * 0.54
    d = min(w, h) * 0.62
    r = d / 2
    specs = []
    specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                  "w": d, "h": d,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT})
    specs.append({"shape": "circle", "x": cx - r * 0.18, "y": cy - r * 0.18,
                  "w": r * 0.36, "h": r * 0.36,
                  "stroke": OUTLINE, "fill": METAL, "width": W_DET})
    for k in range(6):
        a = math.radians(k * 60)
        specs.append({"shape": "line",
                      "x1": cx + r * 0.20 * math.cos(a),
                      "y1": cy + r * 0.20 * math.sin(a),
                      "x2": cx + r * 0.80 * math.cos(a),
                      "y2": cy + r * 0.80 * math.sin(a),
                      "stroke": OUTLINE, "width": W_DET})
    specs.append({"shape": "line",
                  "x1": cx + r * 0.70, "y1": cy - r * 0.70,
                  "x2": w * 0.94, "y2": h * 0.10,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


# ----------------------------------------------------------------- Valves

def _tri_pointing(cx, cy, length, base, direction):
    """Filled triangle whose APEX is at (cx, cy), `base` wide, reaching
    `length` in `direction` ('l','r','u','d'), built so the rotated bounding
    box keeps the intended proportions (no aspect distortion)."""
    if direction in ("u", "d"):
        if direction == "u":          # triangle below the seat, apex up
            x, y, rot = cx - base * 0.5, cy, 0
        else:                          # triangle above the seat, apex down
            x, y, rot = cx - base * 0.5, cy - length, 180
        return {"shape": "triangle", "x": x, "y": y, "w": base, "h": length,
                "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT,
                "rotation": rot}
    if direction == "r":
        cxb, rot = cx - length * 0.5, 90
    else:                              # 'l'
        cxb, rot = cx + length * 0.5, 270
    return {"shape": "triangle", "x": cxb - base * 0.5, "y": cy - length * 0.5,
            "w": base, "h": length, "stroke": OUTLINE, "fill": EQUIP,
            "width": W_OUT, "rotation": rot}


def _bowtie(w, h, cy=None):
    """Two triangles tip-to-tip, apexes meeting cleanly at the centre."""
    if cy is None:
        cy = h * 0.50
    cx = w * 0.50
    half = w * 0.40
    th = h * 0.40
    specs = [_tri_pointing(cx, cy, half, th, "r"),
             _tri_pointing(cx, cy, half, th, "l")]
    return specs, cx, cy, th


def build_gate_valve(w, h):
    """Bow-tie with a short stem."""
    specs, cx, cy, th = _bowtie(w, h)
    specs.append({"shape": "line",
                  "x1": cx, "y1": cy - th * 0.05,
                  "x2": cx, "y2": h * 0.14,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


def build_globe_valve(w, h):
    """Bow-tie with a filled centre circle (the globe)."""
    specs, cx, cy, th = _bowtie(w, h)
    r = th * 0.30
    specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                  "w": r * 2, "h": r * 2,
                  "stroke": OUTLINE, "fill": METAL, "width": W_DET})
    specs.append({"shape": "line",
                  "x1": cx, "y1": cy - r,
                  "x2": cx, "y2": h * 0.14,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


def build_ball_valve(w, h):
    """Bow-tie with a centre circle outline + small handle line."""
    specs, cx, cy, th = _bowtie(w, h)
    r = th * 0.32
    specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                  "w": r * 2, "h": r * 2,
                  "stroke": OUTLINE, "fill": WHITE, "width": W_DET})
    specs.append({"shape": "line",
                  "x1": cx, "y1": cy - r,
                  "x2": cx, "y2": h * 0.12,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": cx - w * 0.10, "y1": h * 0.12,
                  "x2": cx + w * 0.10, "y2": h * 0.12,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


def build_check_valve(w, h):
    """Bow-tie with a ball near one seat (one-way) + flow arrow."""
    specs, cx, cy, th = _bowtie(w, h)
    r = th * 0.22
    bx = cx + (w * 0.90 - cx) * 0.30
    specs.append({"shape": "circle", "x": bx - r, "y": cy - r,
                  "w": r * 2, "h": r * 2,
                  "stroke": OUTLINE, "fill": METAL, "width": W_DET})
    specs.append({"shape": "arrow",
                  "x1": w * 0.20, "y1": h * 0.16,
                  "x2": w * 0.80, "y2": h * 0.16,
                  "stroke": OUTLINE, "width": W_DET})
    return specs


def build_control_valve(w, h):
    """Bow-tie with a diaphragm actuator (dome on a stem) on top."""
    specs, cx, cy, th = _bowtie(w, h, cy=h * 0.66)
    specs.append({"shape": "line",
                  "x1": cx, "y1": cy - th * 0.05,
                  "x2": cx, "y2": h * 0.30,
                  "stroke": OUTLINE, "width": W_OUT})
    dw = w * 0.40
    specs.append({"shape": "halfcircle", "x": cx - dw / 2, "y": h * 0.12,
                  "w": dw, "h": h * 0.18,
                  "stroke": OUTLINE, "fill": EQUIP, "width": W_OUT,
                  "rotation": 0})
    specs.append({"shape": "line",
                  "x1": cx - dw / 2, "y1": h * 0.30,
                  "x2": cx + dw / 2, "y2": h * 0.30,
                  "stroke": OUTLINE, "width": W_DET})
    return specs


def build_three_way_valve(w, h):
    """Three triangles meeting at the centre seat (left, right + bottom)."""
    cx = w * 0.50
    cy = h * 0.45
    th = h * 0.34
    half = w * 0.42
    return [
        _tri_pointing(cx, cy, half, th, "r"),        # left port
        _tri_pointing(cx, cy, half, th, "l"),        # right port
        _tri_pointing(cx, cy, h * 0.45, w * 0.30, "u"),   # bottom port
    ]


# ------------------------------------------------------------- Instruments

def build_instrument(w, h):
    """Field instrument bubble: plain circle with a faint tag."""
    d = min(w, h) * 0.80
    cx = w * 0.50
    cy = h * 0.50
    r = d / 2
    specs = []
    specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                  "w": d, "h": d,
                  "stroke": OUTLINE, "fill": WHITE, "width": W_OUT})
    specs.append({"shape": "text", "text": "TIC",
                  "x": cx - r * 0.45, "y": cy - r * 0.30,
                  "size": h * 0.20, "color": OUTLINE})
    return specs


def build_flow_meter(w, h):
    """Circle on a pipe segment with an FE tag and flow arrow."""
    d = min(w, h) * 0.70
    cx = w * 0.50
    cy = h * 0.50
    r = d / 2
    specs = []
    specs.append({"shape": "line",
                  "x1": w * 0.02, "y1": cy,
                  "x2": w * 0.98, "y2": cy,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                  "w": d, "h": d,
                  "stroke": OUTLINE, "fill": WHITE, "width": W_OUT})
    specs.append({"shape": "arrow",
                  "x1": cx - r * 0.55, "y1": cy,
                  "x2": cx + r * 0.55, "y2": cy,
                  "stroke": OUTLINE, "width": W_DET})
    specs.append({"shape": "text", "text": "FE",
                  "x": cx - r * 0.40, "y": cy - r * 0.55,
                  "size": h * 0.16, "color": OUTLINE})
    return specs


def build_gauge(w, h):
    """Pressure gauge: circle with a needle and a short stem."""
    d = min(w, h) * 0.70
    cx = w * 0.50
    cy = h * 0.46
    r = d / 2
    specs = []
    specs.append({"shape": "circle", "x": cx - r, "y": cy - r,
                  "w": d, "h": d,
                  "stroke": OUTLINE, "fill": WHITE, "width": W_OUT})
    a = math.radians(-55)
    specs.append({"shape": "line",
                  "x1": cx, "y1": cy,
                  "x2": cx + r * 0.75 * math.cos(a),
                  "y2": cy + r * 0.75 * math.sin(a),
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "circle", "x": cx - r * 0.10, "y": cy - r * 0.10,
                  "w": r * 0.20, "h": r * 0.20,
                  "stroke": OUTLINE, "fill": OUTLINE, "width": W_DET})
    specs.append({"shape": "line",
                  "x1": cx, "y1": cy + r,
                  "x2": cx, "y2": h * 0.94,
                  "stroke": OUTLINE, "width": W_OUT})
    specs.append({"shape": "line",
                  "x1": cx - w * 0.10, "y1": h * 0.94,
                  "x2": cx + w * 0.10, "y2": h * 0.94,
                  "stroke": OUTLINE, "width": W_OUT})
    return specs


# -------------------------------------------------------------- Metadata

REFERENCE_MM = 2400.0

SIZES = {
    "tank": (400.0, 500.0),
    "vessel": (600.0, 320.0),
    "column": (300.0, 900.0),
    "reactor": (420.0, 520.0),
    "heat_exchanger": (640.0, 300.0),
    "hopper": (360.0, 380.0),
    "pump": (240.0, 240.0),
    "compressor": (300.0, 240.0),
    "blower": (260.0, 260.0),
    "gate_valve": (200.0, 160.0),
    "globe_valve": (200.0, 160.0),
    "ball_valve": (200.0, 180.0),
    "check_valve": (200.0, 160.0),
    "control_valve": (200.0, 200.0),
    "three_way_valve": (200.0, 180.0),
    "instrument": (160.0, 160.0),
    "flow_meter": (200.0, 160.0),
    "gauge": (160.0, 180.0),
}

LABELS = {
    "tank": "Tank",
    "vessel": "Drum / vessel",
    "column": "Column",
    "reactor": "Reactor",
    "heat_exchanger": "Heat exchanger",
    "hopper": "Hopper",
    "pump": "Pump",
    "compressor": "Compressor",
    "blower": "Blower / fan",
    "gate_valve": "Gate valve",
    "globe_valve": "Globe valve",
    "ball_valve": "Ball valve",
    "check_valve": "Check valve",
    "control_valve": "Control valve",
    "three_way_valve": "3-way valve",
    "instrument": "Instrument",
    "flow_meter": "Flow meter",
    "gauge": "Gauge",
}

CATEGORIES = [
    ("Vessels", ["tank", "vessel", "column", "reactor",
                 "heat_exchanger", "hopper"]),
    ("Rotating equipment", ["pump", "compressor", "blower"]),
    ("Valves", ["gate_valve", "globe_valve", "ball_valve",
                "check_valve", "control_valve", "three_way_valve"]),
    ("Instruments", ["instrument", "flow_meter", "gauge"]),
]


_BUILDERS = {name: globals()["build_" + name] for name in SIZES}


def build_specs(name, w, h):
    return _BUILDERS[name](w, h)


def size_mm(name):
    return SIZES[name]
