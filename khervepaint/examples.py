"""Built-in example drawings — labelled schematics of lab techniques.

Each example is a builder returning a list of shape specs (the same
format the AI assistant uses, applied via `ai_assistant.apply_specs`),
laid out on an A4 portrait page (1240 x 1754 px at 150 dpi). The
Examples menu loads one into a fresh document; every element is a real,
editable KhervePaint item, so a sketch is a starting point you can
tweak.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

#: A4 portrait at 150 dpi.
PAGE_W, PAGE_H, PAGE_DPI = 1240, 1754, 150

# palette
INK = "#1a1a1a"
MUTE = "#5b6b7a"
TITLE = "#11324d"
BEAM = "#c0392b"       # x-rays / primary beam
SIGNAL = "#1f8a4c"     # emitted signal / electrons
OPTIC = "#2563c0"      # lenses / optics
DET = "#7a3fb0"        # detectors / electronics
SAMP = "#e8b53a"       # sample


# ---------------------------------------------------------------- helpers
def _t(x, y, text, size=20, color=INK):
    return {"shape": "text", "x": x, "y": y, "text": text, "size": size,
            "color": color}


def _box(x, y, w, h, label="", fill=None, stroke=INK, width=2, shape="rect"):
    d = {"shape": shape, "x": x, "y": y, "w": w, "h": h,
         "stroke": stroke, "width": width}
    if fill:
        d["fill"] = fill
    if label:
        d["label"] = label
    return d


def _round(x, y, w, h, label="", fill=None, stroke=INK, width=2):
    return _box(x, y, w, h, label, fill, stroke, width, shape="rounded_rect")


def _circle(x, y, d, label="", fill=None, stroke=INK, width=2):
    return _box(x, y, d, d, label, fill, stroke, width, shape="circle")


def _arrow(x1, y1, x2, y2, color=BEAM, width=4):
    return {"shape": "arrow", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": color, "width": width}


def _line(x1, y1, x2, y2, color="#888", width=2):
    return {"shape": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2,
            "stroke": color, "width": width}


def _page(title, subtitle, body, caption=""):
    specs = [_box(40, 40, PAGE_W - 80, PAGE_H - 80, stroke="#cfd8e0", width=2),
             _t(70, 70, title, 36, TITLE),
             _t(70, 124, subtitle, 20, MUTE)]
    specs += body
    if caption:
        specs.append(_t(70, PAGE_H - 130, caption, 16, MUTE))
    return specs


def _spectrum(x, y, w, h, xlabel, ylabel):
    """A small framed plot with axes and a wiggly trace."""
    pts = [(0.0, 0.85), (0.12, 0.8), (0.2, 0.3), (0.26, 0.8), (0.42, 0.7),
           (0.5, 0.15), (0.56, 0.72), (0.72, 0.6), (0.8, 0.45), (0.9, 0.7),
           (1.0, 0.65)]
    specs = [_box(x, y, w, h, fill="#ffffff", stroke=INK, width=2),
             _line(x, y + h, x + w, y + h, INK, 2),
             _line(x, y, x, y + h, INK, 2)]
    for a, b in zip(pts, pts[1:]):
        specs.append(_line(x + a[0] * w, y + a[1] * h,
                           x + b[0] * w, y + b[1] * h, DET, 2))
    specs.append(_t(x + w / 2 - 60, y + h + 14, xlabel, 15, MUTE))
    specs.append(_t(x - 10, y - 26, ylabel, 15, MUTE))
    return specs


# ---------------------------------------------------------------- XPS
def build_xps():
    cy = 520
    body = [
        _box(120, cy - 70, 150, 140, "Al Kα\nanode", "#fbe3e0", BEAM),
        _t(140, cy + 90, "X-ray source", 16, BEAM),
        _arrow(275, cy, 360, cy),
        _t(280, cy - 34, "X-rays", 15, BEAM),
        _box(360, cy - 90, 170, 180, "", "#fff8e6", "#9a7b1f"),
        _box(395, cy - 30, 100, 70, "sample", SAMP, "#9a7b1f"),
        _t(372, cy + 110, "UHV chamber", 16, "#9a7b1f"),
        _arrow(470, cy - 30, 560, cy - 90, SIGNAL),
        _t(520, cy - 130, "photoelectrons", 15, SIGNAL),
        _box(560, cy - 150, 120, 70, "electron\nlens", "#e4ecfb", OPTIC),
        # hemispherical analyser: two concentric half circles
        _box(700, cy - 230, 260, 260, "", None, DET, 3, shape="halfcircle"),
        _box(745, cy - 185, 170, 170, "", None, DET, 3, shape="halfcircle"),
        _t(760, cy - 250, "hemispherical analyser", 15, DET),
        _arrow(680, cy - 115, 760, cy - 150, SIGNAL),
        _box(905, cy - 60, 110, 70, "detector", "#efe3f7", DET),
        _arrow(950, cy + 10, 950, cy + 90, DET),
        _box(870, cy + 90, 180, 110, "computer", "#eef1f4", INK),
    ]
    body += _spectrum(360, 1000, 520, 300, "Binding energy (eV)",
                      "Intensity (counts/s)")
    return _page("X-ray Photoelectron Spectroscopy (XPS)",
                 "Surface elemental composition & chemical state", body,
                 "X-rays eject core photoelectrons; their kinetic energy "
                 "gives the binding energy spectrum.")


# ---------------------------------------------------------------- XRD
def build_xrd():
    cx, cy = 620, 560
    body = [
        _circle(cx - 320, cy - 320, 640, "", None, "#ccd5dd", 2),
        _box(cx - 470, cy - 40, 150, 90, "X-ray\ntube", "#fbe3e0", BEAM),
        _arrow(cx - 320, cy, cx - 70, cy),
        _box(cx - 150, cy - 26, 60, 52, "slit", "#eef1f4", INK, 2),
        _box(cx - 70, cy - 45, 140, 90, "sample\n(θ)", SAMP, "#9a7b1f"),
        _arrow(cx + 70, cy, cx + 290, cy - 150, SIGNAL),
        _t(cx + 150, cy - 170, "2θ", 22, SIGNAL),
        _box(cx + 250, cy - 230, 150, 90, "detector", "#efe3f7", DET),
        _line(cx, cy, cx + 300, cy, "#ccd5dd", 1),
        _t(cx - 60, cy + 330, "goniometer circle", 16, MUTE),
    ]
    body += _spectrum(360, 1040, 520, 300, "2θ (degrees)", "Intensity")
    return _page("X-ray Diffraction (XRD)",
                 "Crystal structure & phase identification", body,
                 "Bragg diffraction (nλ = 2d·sinθ) of a scanned beam gives "
                 "the diffractogram of lattice spacings.")


# ---------------------------------------------------------------- FTIR
def build_ftir():
    cy = 520
    body = [
        _box(120, cy - 35, 120, 70, "IR\nsource", "#fbe3e0", BEAM),
        _arrow(240, cy, 360, cy),
        # beam splitter
        _box(360, cy - 60, 8, 120, "", None, OPTIC, 0, shape="rect"),
        _line(360, cy + 60, 420, cy, OPTIC, 3),
        _t(330, cy + 80, "beam splitter", 14, OPTIC),
        _box(360, 150, 120, 24, "fixed mirror", "#e4ecfb", OPTIC),
        _arrow(364, cy - 60, 420, 180, OPTIC, 2),
        _box(640, cy - 12, 24, 120, "", "#e4ecfb", OPTIC),
        _t(610, cy + 130, "moving mirror →", 14, OPTIC),
        _arrow(372, cy, 630, cy, OPTIC, 2),
        _arrow(364, cy + 6, 364, cy + 120, BEAM),
        _box(300, cy + 120, 150, 80, "sample", SAMP, "#9a7b1f"),
        _arrow(375, cy + 200, 375, cy + 270, SIGNAL),
        _box(300, cy + 270, 150, 80, "detector", "#efe3f7", DET),
    ]
    body += _spectrum(360, 1010, 520, 300, "Wavenumber (cm⁻¹)",
                      "Transmittance (%)")
    return _page("Fourier-Transform Infrared (FTIR)",
                 "Molecular bonds & functional groups", body,
                 "A Michelson interferometer modulates IR light; the "
                 "Fourier transform of the interferogram is the spectrum.")


# ---------------------------------------------------------------- TGA
def build_tga():
    cx = 470
    body = [
        _box(cx - 60, 260, 120, 40, "balance", "#eef1f4", INK),
        _line(cx, 300, cx, 430, "#888", 2),
        # furnace
        _round(cx - 140, 430, 280, 320, "", "#fde7e0", BEAM, 2),
        _box(cx - 45, 470, 90, 70, "crucible\n(sample)", SAMP, "#9a7b1f"),
        _line(cx - 130, 470, cx - 60, 470, BEAM, 3),
        _line(cx - 130, 540, cx - 60, 540, BEAM, 3),
        _line(cx - 130, 610, cx - 60, 610, BEAM, 3),
        _line(cx + 60, 470, cx + 130, 470, BEAM, 3),
        _line(cx + 60, 540, cx + 130, 540, BEAM, 3),
        _line(cx + 60, 610, cx + 130, 610, BEAM, 3),
        _t(cx - 135, 760, "furnace (heating coils)", 16, BEAM),
        _arrow(cx + 200, 700, cx + 120, 640, SIGNAL),
        _t(cx + 150, 720, "purge gas", 14, SIGNAL),
        _t(cx - 60, 250, "microbalance", 14, MUTE),
    ]
    body += _spectrum(360, 1000, 520, 300, "Temperature (°C)",
                      "Mass (%)")
    return _page("Thermogravimetric Analysis (TGA)",
                 "Mass change vs temperature", body,
                 "A sample is heated on a microbalance under controlled "
                 "atmosphere; mass loss reveals decomposition & volatiles.")


# ---------------------------------------------------------------- BET
def build_bet():
    cx = 470
    body = [
        _box(cx - 60, 250, 240, 70, "N₂ gas\ndosing", "#e4ecfb", OPTIC),
        _box(cx + 220, 250, 150, 70, "pressure\ntransducer", "#efe3f7", DET),
        _line(cx + 60, 285, cx + 220, 285, "#888", 2),
        _arrow(cx + 60, 320, cx + 60, 430, OPTIC),
        # sample tube in dewar
        _round(cx, 430, 120, 360, "", "#eaf4ff", "#2980b9", 2),
        _box(cx + 30, 470, 60, 120, "sample", SAMP, "#9a7b1f"),
        _t(cx - 30, 810, "liquid-N₂ dewar (77 K)", 15, "#2980b9"),
    ]
    body += _spectrum(360, 1010, 520, 300, "Relative pressure  p/p₀",
                      "Quantity adsorbed")
    return _page("Gas Sorption — BET Surface Area",
                 "Specific surface area & porosity", body,
                 "N₂ adsorption isotherms at 77 K fit the BET equation to "
                 "give the specific surface area.")


# ---------------------------------------------------------------- TEM
def build_tem():
    cx = 430
    body = [
        _box(cx - 70, 230, 140, 70, "electron\ngun", "#fbe3e0", BEAM),
        _arrow(cx, 300, cx, 360, SIGNAL),
        _box(cx - 90, 360, 180, 46, "condenser lens", "#e4ecfb", OPTIC),
        _arrow(cx, 406, cx, 450, SIGNAL),
        _box(cx - 60, 450, 120, 36, "specimen", SAMP, "#9a7b1f"),
        _arrow(cx, 486, cx, 530, SIGNAL),
        _box(cx - 90, 530, 180, 46, "objective lens", "#e4ecfb", OPTIC),
        _arrow(cx, 576, cx, 620, SIGNAL),
        _box(cx - 90, 620, 180, 46, "projector lens", "#e4ecfb", OPTIC),
        _arrow(cx, 666, cx, 720, SIGNAL),
        _box(cx - 120, 720, 240, 70, "fluorescent screen /\ncamera",
             "#efe3f7", DET),
        _t(cx - 130, 820, "evacuated column", 15, MUTE),
        _box(820, 360, 320, 320, "", "#101418", INK, 2),
        _circle(900, 430, 70, "", "#cfe0ff", "#9fc0ff", 2),
        _circle(980, 520, 50, "", "#cfe0ff", "#9fc0ff", 2),
        _circle(870, 560, 40, "", "#cfe0ff", "#9fc0ff", 2),
        _t(830, 700, "bright-field image (nanoparticles)", 15, MUTE),
    ]
    return _page("Transmission Electron Microscopy (TEM)",
                 "Nanoscale structure & morphology", body,
                 "Electrons transmitted through a thin specimen are focused "
                 "by magnetic lenses into a high-resolution image.")


# ---------------------------------------------------------------- AFM
def build_afm():
    body = [
        _box(180, 300, 120, 70, "laser", "#fbe3e0", BEAM),
        _arrow(300, 335, 540, 470, BEAM, 2),
        _box(560, 250, 150, 100, "photo-\ndiode", "#efe3f7", DET),
        _arrow(540, 470, 600, 350, BEAM, 2),
        # cantilever + tip
        _line(360, 470, 540, 470, INK, 4),
        {"shape": "triangle", "x": 350, "y": 470, "w": 36, "h": 46,
         "stroke": INK, "width": 2, "fill": "#dfe6ec"},
        _t(300, 430, "cantilever + tip", 14, INK),
        # sample surface (wavy)
        _box(220, 560, 520, 90, "sample", SAMP, "#9a7b1f"),
        _box(220, 650, 520, 70, "piezo scanner (x,y,z)", "#e4ecfb", OPTIC),
        _box(800, 470, 200, 70, "feedback\ncontroller", "#eef1f4", INK),
        _arrow(710, 300, 800, 470, DET, 2),
        _arrow(900, 540, 620, 690, OPTIC, 2),
        _box(820, 720, 260, 220, "topography map", "#101418", INK),
        _t(820, 960, "surface height image", 15, MUTE),
    ]
    return _page("Atomic Force Microscopy (AFM)",
                 "Surface topography at the nanoscale", body,
                 "A sharp tip on a cantilever rasters the surface; laser "
                 "deflection feedback maps the height with sub-nm resolution.")


# ---------------------------------------------------------------- XRF
def build_xrf():
    cy = 520
    body = [
        _box(120, cy - 45, 150, 90, "X-ray\nsource", "#fbe3e0", BEAM),
        _arrow(270, cy, 470, cy + 60),
        _t(300, cy - 6, "primary X-rays", 15, BEAM),
        _box(440, cy + 50, 200, 120, "sample", SAMP, "#9a7b1f"),
        _arrow(540, cy + 50, 720, cy - 70, SIGNAL),
        _t(640, cy - 90, "fluorescent\nX-rays", 14, SIGNAL),
        _box(720, cy - 150, 170, 110, "energy-\ndispersive\ndetector",
             "#efe3f7", DET),
        _arrow(805, cy - 40, 805, cy + 30, DET),
        _box(720, cy + 30, 170, 90, "MCA /\ncomputer", "#eef1f4", INK),
    ]
    body += _spectrum(360, 1040, 520, 300, "Energy (keV)", "Counts")
    return _page("X-ray Fluorescence (XRF)",
                 "Elemental composition (bulk)", body,
                 "Primary X-rays excite atoms that emit characteristic "
                 "fluorescent X-rays — each element a peak in energy.")


# ---------------------------------------------------------------- SIMS
def build_sims():
    cy = 520
    body = [
        _box(120, cy - 90, 160, 90, "primary\nion gun", "#fbe3e0", BEAM),
        _arrow(280, cy - 45, 470, cy + 40),
        _t(300, cy - 70, "primary ions", 14, BEAM),
        _box(430, cy + 40, 200, 110, "sample", SAMP, "#9a7b1f"),
        _arrow(520, cy + 40, 700, cy - 80, SIGNAL),
        _t(610, cy - 100, "secondary ions", 14, SIGNAL),
        _box(700, cy - 150, 180, 110, "mass\nanalyser", "#e4ecfb", OPTIC),
        _arrow(880, cy - 95, 960, cy - 95, SIGNAL),
        _box(960, cy - 130, 150, 80, "detector", "#efe3f7", DET),
    ]
    body += _spectrum(360, 1040, 520, 300, "Sputter depth", "Intensity")
    return _page("Secondary-Ion Mass Spectrometry (SIMS)",
                 "Trace elements & depth profiling", body,
                 "A focused ion beam sputters the surface; ejected secondary "
                 "ions are mass-analysed for a depth profile.")


#: (category, display name, builder)
EXAMPLES = [
    ("Spectroscopy", "XPS — X-ray Photoelectron Spectroscopy", build_xps),
    ("Spectroscopy", "FTIR — Fourier-Transform Infrared", build_ftir),
    ("Spectroscopy", "XRF — X-ray Fluorescence", build_xrf),
    ("Spectroscopy", "SIMS — Secondary-Ion Mass Spectrometry", build_sims),
    ("Diffraction", "XRD — X-ray Diffraction", build_xrd),
    ("Microscopy", "TEM — Transmission Electron Microscopy", build_tem),
    ("Microscopy", "AFM — Atomic Force Microscopy", build_afm),
    ("Thermal & sorption", "TGA — Thermogravimetric Analysis", build_tga),
    ("Thermal & sorption", "BET — Gas Sorption (surface area)", build_bet),
]
