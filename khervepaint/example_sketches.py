"""Builders for the built-in example schematics.

Each `build_*` returns a list of shape specs (see `example_kit`) laid
out on an A4 page; `SKETCHES` pairs them with a menu category and name.
Kept separate from the toolkit so neither file outgrows ~1500 lines.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from .example_kit import (BEAM, COOL, DETC, INK, MUTE, OPTIC, SAMP, SIGNAL,
                          TINT_BEAM, TINT_BODY, TINT_COOL, TINT_DET,
                          TINT_OPTIC, TINT_SAMP, TINT_SIGNAL, CATEGORY_COLOR,
                          _aperture, _arrow, _beam, _box, _callout, _circle,
                          _ellipse, _legend, _lens, _line, _micrograph,
                          _page, _plot, _poly, _round, _stage, _t, _tc)

SP = CATEGORY_COLOR["Spectroscopy"]
MS = CATEGORY_COLOR["Mass spectrometry"]
DF = CATEGORY_COLOR["Diffraction"]
MC = CATEGORY_COLOR["Microscopy"]
TH = CATEGORY_COLOR["Thermal & sorption"]
CH = CATEGORY_COLOR["Chromatography"]


def _ring(cx, cy, r, n, d, color="#dce8fb", start=0.0):
    """n small circles evenly spaced on a ring of radius r about (cx,cy)."""
    out = []
    for i in range(n):
        a = start + 2 * math.pi * i / n
        out.append(_circle(cx + r * math.cos(a) - d / 2,
                           cy + r * math.sin(a) - d / 2, d,
                           fill=color, stroke=color, width=0))
    return out


# ===================================================== Microscopy: TEM
def build_tem():
    cx = 330
    body = [_round(cx - 150, 208, 300, 612, fill=TINT_BODY, stroke="#c4ccd4")]
    # electron gun
    body += [_poly("triangle", cx - 20, 224, 40, 32, fill=TINT_BEAM,
                   stroke=BEAM, rotation=180)]
    body += _aperture(cx, 286)
    # beam envelope
    pts = [(258, 5), (312, 64), (330, 64), (366, 6), (415, 52), (492, 64),
           (520, 64), (567, 78), (606, 78), (642, 7), (688, 50), (748, 66),
           (818, 120)]
    body += _beam(cx, pts, SIGNAL, 2)
    # optical column
    body += [_lens(cx, 330, 150), _lens(cx, 430, 140)]
    body += _aperture(cx, 366, 8, 26)
    body += _stage(cx, 498, 130, "specimen")
    body += [_lens(cx, 585, 200, h=34)]
    body += _aperture(cx, 642, 8, 30)
    body += [_lens(cx, 700, 150), _lens(cx, 760, 160)]
    body += [_box(cx - 120, 822, 240, 70, "fluorescent screen / CCD",
                  fill=TINT_DET, stroke=DETC, width=2)]
    # callouts
    for cy, txt in [(256, "electron gun"), (330, "condenser lens 1"),
                    (430, "condenser lens 2"), (498, "specimen on grid"),
                    (585, "objective lens"), (700, "intermediate lens"),
                    (760, "projector lens")]:
        body += [_line(cx + 150, cy, cx + 178, cy, "#aab6c0", 1),
                 _t(cx + 184, cy - 10, txt, 15, INK)]
    body += [_t(cx - 150, 902, "evacuated electron column", 15, MUTE)]
    # right: micrograph + SAED
    body += _micrograph(660, 226, 470, 300,
                        [(120, 88, 74), (255, 150, 52), (330, 78, 38),
                         (180, 214, 46), (388, 198, 30)],
                        "Bright-field TEM image", "100 nm")
    body += [_box(660, 558, 470, 256, fill="#0a0c10", stroke=INK, width=2)]
    sc = (895, 686)
    body += [_circle(sc[0] - 9, sc[1] - 9, 18, fill="#dce8fb",
                     stroke="#dce8fb", width=0)]
    body += _ring(sc[0], sc[1], 64, 8, 13)
    body += _ring(sc[0], sc[1], 108, 12, 10, start=0.26)
    body += [_tc(895, 824, "Selected-area diffraction (SAED)", 15, MUTE)]
    # bottom: EDS
    body += _plot(120, 904, 1000, 466, "X-ray energy (keV)", "Counts",
                 [(0, .08), (.1, .08), (.108, .82), (.118, .08), (.27, .08),
                  (.278, .5), (.288, .08), (.46, .08), (.468, .66),
                  (.478, .08), (.64, .08), (.648, .34), (.658, .08),
                  (.82, .08), (.828, .46), (.838, .08), (1, .08)],
                 peaks=[(.108, "C"), (.278, "O"), (.468, "Fe"), (.648, "Cu"),
                        (.828, "Pt")], color=SIGNAL)
    return _page("Transmission Electron Microscopy (TEM)",
                 "Nanoscale structure, morphology & crystallography", MC, body,
                 "A focused electron beam is transmitted through a thin "
                 "specimen and magnified by a stack of magnetic lenses; "
                 "imaging, diffraction (SAED) and EDS run on the same column.")


# ===================================================== Microscopy: SEM
def build_sem():
    cx = 330
    body = [_round(cx - 150, 208, 300, 470, fill=TINT_BODY, stroke="#c4ccd4")]
    body += [_poly("triangle", cx - 20, 224, 40, 32, fill=TINT_BEAM,
                   stroke=BEAM, rotation=180)]
    pts = [(258, 5), (306, 56), (324, 56), (360, 7), (404, 46), (452, 46),
           (470, 7), (520, 52), (560, 78)]
    body += _beam(cx, pts, SIGNAL, 2)
    body += [_lens(cx, 322, 140), _lens(cx, 432, 150)]
    body += _aperture(cx, 376, 8, 24)
    # scan coils
    body += [_box(cx - 96, 496, 36, 44, fill=TINT_OPTIC, stroke=OPTIC),
             _box(cx + 60, 496, 36, 44, fill=TINT_OPTIC, stroke=OPTIC)]
    body += _stage(cx, 596, 150, "sample")
    # detectors
    body += [_box(cx + 110, 540, 96, 50, "SE / BSE\ndetector", fill=TINT_DET,
                  stroke=DETC, width=2)]
    body += [_arrow(cx + 40, 590, cx + 110, 560, SIGNAL, 2)]
    for cy, txt in [(256, "electron gun"), (322, "condenser lens"),
                    (432, "objective lens"), (516, "scan coils"),
                    (596, "stage / sample")]:
        body += [_line(cx + 150, cy, cx + 178, cy, "#aab6c0", 1),
                 _t(cx + 184, cy - 10, txt, 15, INK)]
    body += [_t(cx - 150, 700, "evacuated column", 15, MUTE)]
    body += _micrograph(660, 226, 470, 430,
                        [(120, 120, 96), (250, 250, 70), (360, 140, 54),
                         (170, 320, 60), (380, 330, 40), (300, 60, 34)],
                        "Secondary-electron image", "10 µm")
    body += _plot(120, 904, 1000, 466, "X-ray energy (keV)", "Counts",
                 [(0, .08), (.12, .08), (.128, .78), (.14, .08), (.32, .08),
                  (.328, .55), (.34, .08), (.52, .08), (.528, .42),
                  (.54, .08), (.72, .08), (.728, .6), (.74, .08), (1, .08)],
                 peaks=[(.128, "C"), (.328, "O"), (.528, "Al"), (.728, "Si")],
                 color=SIGNAL)
    return _page("Scanning Electron Microscopy (SEM)",
                 "Surface topography & composition (with EDS)", MC, body,
                 "A finely focused electron probe is rastered across the "
                 "surface; secondary and backscattered electrons build the "
                 "image while characteristic X-rays give EDS microanalysis.")


# ===================================================== Microscopy: AFM
def build_afm():
    body = [_round(150, 470, 760, 250, fill=TINT_BODY, stroke="#c4ccd4")]
    # laser + photodiode
    body += [_box(180, 250, 130, 70, "laser\ndiode", fill=TINT_BEAM,
                  stroke=BEAM, width=2)]
    body += [_box(560, 230, 150, 90, "position-sensitive\nphotodiode",
                  fill=TINT_DET, stroke=DETC, width=2)]
    body += [_arrow(310, 300, 470, 470, BEAM, 2),
             _arrow(470, 470, 600, 320, BEAM, 2)]
    # cantilever + tip
    body += [_line(330, 470, 470, 470, INK, 5)]
    body += [_poly("triangle", 452, 470, 34, 46, fill="#dfe6ec", stroke=INK,
                   rotation=180)]
    body += [_t(300, 426, "cantilever + tip", 15, INK)]
    # sample + piezo
    body += [_box(360, 560, 360, 70, "sample", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_box(360, 632, 360, 64, "piezo scanner  (x, y, z)",
                  fill=TINT_OPTIC, stroke=OPTIC, width=2)]
    # feedback loop
    body += [_box(740, 470, 150, 70, "feedback\ncontroller", fill="#eef2f5",
                  stroke=INK, width=2)]
    body += [_arrow(710, 300, 740, 470, DETC, 2),
             _arrow(815, 540, 720, 660, OPTIC, 2)]
    body += _legend(180, 348, [(BEAM, "laser deflection"),
                               (DETC, "feedback signal"),
                               (OPTIC, "piezo drive")])
    body += _plot(160, 880, 920, 480, "tip position (µm)", "height (nm)",
                 [(0, .3), (.08, .55), (.16, .35), (.24, .7), (.32, .5),
                  (.4, .85), (.48, .45), (.56, .6), (.64, .3), (.72, .65),
                  (.8, .4), (.88, .72), (.96, .45), (1, .55)], color=SIGNAL)
    return _page("Atomic Force Microscopy (AFM)",
                 "Surface topography at the nanoscale", MC, body,
                 "A sharp tip on a flexible cantilever rasters the surface; "
                 "laser-beam deflection feeds a feedback loop that drives the "
                 "piezo scanner, mapping height with sub-nanometre resolution.")


# ===================================================== Microscopy: STM
def build_stm():
    body = [_round(170, 360, 700, 340, fill=TINT_BODY, stroke="#c4ccd4")]
    # tip approaching surface
    body += [_box(420, 380, 60, 90, "W tip", fill="#cdd6de", stroke=MUTE,
                  width=2)]
    body += [_poly("triangle", 432, 470, 36, 40, fill="#cdd6de", stroke=INK,
                   rotation=180)]
    # tunnelling gap
    body += [_line(450, 512, 450, 540, BEAM, 2)]
    body += [_t(470, 506, "tunnelling gap (~1 nm)", 15, BEAM)]
    body += [_box(250, 540, 420, 70, "sample (conductive)", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_box(250, 612, 420, 60, "piezo scanner", fill=TINT_OPTIC,
                  stroke=OPTIC, width=2)]
    # bias + current amp
    body += [_box(700, 380, 150, 70, "bias voltage", fill="#eef2f5",
                  stroke=INK, width=2)]
    body += [_box(700, 470, 150, 70, "tunnelling-current\namplifier",
                  fill=TINT_DET, stroke=DETC, width=2)]
    body += [_arrow(680, 500, 510, 500, SIGNAL, 2)]
    body += [_arrow(775, 540, 670, 645, OPTIC, 2)]
    body += _micrograph(160, 800, 460, 470,
                        [(110, 100, 40), (190, 100, 40), (270, 100, 40),
                         (150, 175, 40), (230, 175, 40), (310, 175, 40),
                         (110, 250, 40), (190, 250, 40), (270, 250, 40),
                         (150, 325, 40), (230, 325, 40), (310, 325, 40)],
                        "Atomic-resolution image", "2 nm")
    body += _plot(660, 800, 460, 470, "bias voltage (V)", "dI/dV",
                 [(0, .2), (.2, .25), (.35, .55), (.45, .4), (.5, .45),
                  (.65, .8), (.8, .4), (1, .25)], color=DETC)
    return _page("Scanning Tunnelling Microscopy (STM)",
                 "Atomic-scale topography & electronic structure", MC, body,
                 "A sharp conductive tip is held ~1 nm above a surface; the "
                 "quantum tunnelling current (kept constant by feedback) maps "
                 "atoms, while dI/dV spectroscopy probes the local density of "
                 "states.")


# ===================================================== Spectroscopy: XPS
def _analyser_dome(cx, top):
    """A hemispherical-analyser cross-section: two concentric domes."""
    return [_box(cx - 135, top, 270, 135, shape="halfcircle", stroke=DETC,
                 width=3, fill="#f3edfa"),
            _box(cx - 86, top + 49, 172, 86, shape="halfcircle", stroke=DETC,
                 width=3, fill="#ffffff")]


def build_xps():
    cx = 380
    body = _analyser_dome(cx, 214)
    body += [_box(cx + 150, 250, 120, 60, "detector", fill=TINT_DET,
                  stroke=DETC, width=2)]
    body += [_arrow(cx + 120, 320, cx + 175, 300, SIGNAL, 2)]
    # transfer lens + chamber
    body += [_box(cx - 50, 352, 100, 44, "transfer\nlens", fill=TINT_OPTIC,
                  stroke=OPTIC, width=2)]
    body += [_round(cx - 170, 408, 340, 250, fill=TINT_BODY, stroke="#c4ccd4")]
    body += _stage(cx, 545, 130, "sample")
    # x-ray source
    body += [_round(120, 470, 180, 120, "Al / Mg Kα\ntwin anode",
                    fill=TINT_BEAM, stroke=BEAM, width=2)]
    body += [_arrow(300, 528, cx - 60, 545, BEAM, 3),
             _t(305, 500, "X-rays", 15, BEAM)]
    body += [_arrow(cx, 524, cx, 398, SIGNAL, 3),
             _t(cx + 12, 430, "photoelectrons", 15, SIGNAL)]
    body += [_line(cx + 135, 280, cx + 250, 280, "#aab6c0", 1),
             _t(cx + 150, 232, "hemispherical analyser", 15, INK)]
    body += [_t(cx - 168, 668, "ultra-high-vacuum chamber", 15, MUTE)]
    # principle: photoemission energy diagram
    body += _energy_inset(720, 230)
    body += _plot(120, 904, 1000, 466, "Binding energy (eV)",
                 "Intensity (a.u.)",
                 [(1, .12), (.86, .14), (.84, .72), (.82, .16), (.7, .18),
                  (.68, .9), (.66, .2), (.5, .22), (.48, .55), (.46, .24),
                  (.32, .26), (.3, .78), (.28, .28), (.14, .32), (.12, .6),
                  (.1, .34), (0, .4)],
                 peaks=[(.13, "Si 2p"), (.31, "C 1s"), (.49, "N 1s"),
                        (.69, "O 1s"), (.85, "F 1s")], color=DETC)
    return _page("X-ray Photoelectron Spectroscopy (XPS)",
                 "Surface elemental composition & chemical state", SP, body,
                 "Soft X-rays eject core-level photoelectrons; a hemispherical "
                 "analyser measures their kinetic energy, giving binding "
                 "energies that fingerprint each element and its bonding.")


def _energy_inset(x, y):
    """A small photoemission energy-level diagram."""
    b = [_box(x, y, 400, 300, fill="#ffffff", stroke="#c4ccd4", width=2),
         _t(x + 16, y + 12, "Photoemission", 16, MUTE)]
    b += [_line(x + 40, y + 250, x + 360, y + 250, INK, 2)]      # core level
    b += [_t(x + 12, y + 240, "core", 13, MUTE)]
    b += [_line(x + 40, y + 120, x + 360, y + 120, INK, 2)]      # vacuum
    b += [_t(x + 12, y + 110, "Eᵥ", 13, MUTE)]
    b += [_line(x + 40, y + 170, x + 360, y + 170, MUTE, 1)]     # fermi
    b += [_t(x + 12, y + 160, "E_F", 13, MUTE)]
    b += [_arrow(x + 120, y + 250, x + 120, y + 70, BEAM, 3),
          _t(x + 128, y + 150, "hν", 15, BEAM)]
    b += [_circle(x + 250, y + 244, 14, fill=SIGNAL, stroke=SIGNAL),
          _arrow(x + 257, y + 244, x + 257, y + 60, SIGNAL, 3),
          _t(x + 266, y + 90, "e⁻ (KE)", 14, SIGNAL)]
    return b


def _bigplot(xlabel, ylabel, curve, peaks=None, color=DETC):
    return _plot(120, 924, 1000, 496, xlabel, ylabel, curve, peaks, color)


def _grating(x, y, w=70, h=46, color=OPTIC):
    out = [_box(x, y, w, h, fill=TINT_OPTIC, stroke=color, width=2)]
    for i in range(1, 7):
        out.append(_line(x + w * i / 7, y, x + w * i / 7, y + h, color, 1))
    return out


# ===================================================== Spectroscopy: UPS
def build_ups():
    cx = 380
    body = _analyser_dome(cx, 214)
    body += [_box(cx + 150, 250, 120, 60, "channeltron\ndetector",
                  fill=TINT_DET, stroke=DETC, width=2),
             _arrow(cx + 120, 320, cx + 175, 300, SIGNAL, 2)]
    body += [_box(cx - 50, 352, 100, 44, "lens", fill=TINT_OPTIC,
                  stroke=OPTIC, width=2)]
    body += [_round(cx - 170, 408, 340, 250, fill=TINT_BODY, stroke="#c4ccd4")]
    body += _stage(cx, 545, 130, "sample")
    body += [_round(110, 450, 190, 130, "He I / He II\ndischarge lamp",
                    fill=TINT_BEAM, stroke=BEAM, width=2),
             _arrow(300, 520, cx - 60, 545, BEAM, 3),
             _t(305, 494, "UV photons (21.2 eV)", 14, BEAM)]
    body += [_arrow(cx, 524, cx, 398, SIGNAL, 3),
             _t(cx + 12, 430, "photoelectrons", 15, SIGNAL)]
    body += [_t(cx - 168, 668, "ultra-high-vacuum chamber", 15, MUTE),
             _line(cx + 135, 280, cx + 250, 280, "#aab6c0", 1),
             _t(cx + 150, 232, "hemispherical analyser", 15, INK)]
    body += _energy_inset(720, 230)
    body += _bigplot("Binding energy (eV)", "Intensity (a.u.)",
                    [(1, .15), (.85, .2), (.7, .35), (.6, .7), (.5, .55),
                     (.42, .8), (.32, .5), (.22, .65), (.12, .3), (.05, .5),
                     (0, .12)],
                    peaks=[(.45, "valence band"), (.12, "E_F")], color=DETC)
    return _page("Ultraviolet Photoelectron Spectroscopy (UPS)",
                 "Valence-band & work-function measurement", SP, body,
                 "He-discharge UV photons photoemit valence electrons; the "
                 "spectrum reveals the density of states near the Fermi level "
                 "and, from the cutoff, the sample work function.")


# ===================================================== Spectroscopy: AES
def build_aes():
    cx = 360
    body = [_round(cx - 150, 360, 300, 300, fill=TINT_BODY, stroke="#c4ccd4")]
    body += [_box(cx - 40, 224, 80, 60, "electron\ngun", fill=TINT_BEAM,
                  stroke=BEAM, width=2),
             _arrow(cx, 286, cx, 560, BEAM, 3)]
    # cylindrical mirror analyser: two nested cylinders
    body += [_box(cx - 140, 300, 280, 250, shape="rounded_rect", stroke=DETC,
                  width=3, fill=None),
             _box(cx - 95, 330, 190, 190, shape="rounded_rect", stroke=DETC,
                  width=2, fill=None)]
    body += _stage(cx, 588, 120, "sample")
    body += [_arrow(cx + 30, 560, cx + 120, 400, SIGNAL, 2),
             _t(cx + 90, 470, "Auger e⁻", 14, SIGNAL)]
    body += [_box(cx + 150, 320, 110, 56, "detector", fill=TINT_DET,
                  stroke=DETC, width=2)]
    body += [_line(cx + 140, 300, cx + 250, 300, "#aab6c0", 1),
             _t(cx + 150, 252, "cylindrical mirror analyser (CMA)", 14, INK)]
    body += _bigplot("Kinetic energy (eV)", "dN/dE (derivative)",
                    [(0, .5), (.15, .5), (.18, .8), (.21, .2), (.24, .5),
                     (.45, .5), (.48, .78), (.51, .22), (.54, .5), (.7, .5),
                     (.73, .7), (.76, .3), (.79, .5), (1, .5)],
                    peaks=[(.19, "C KLL"), (.49, "O KLL"), (.74, "N KLL")],
                    color=SIGNAL)
    return _page("Auger Electron Spectroscopy (AES)",
                 "Surface composition with high spatial resolution", SP, body,
                 "A focused electron beam excites core holes that relax by "
                 "emitting Auger electrons of element-specific energy; the "
                 "differentiated spectrum identifies surface species.")


# ===================================================== Spectroscopy: FTIR
def build_ftir():
    body = [_box(120, 392, 120, 70, "IR\nsource", fill=TINT_BEAM,
                 stroke=BEAM, width=2)]
    body += [_arrow(240, 427, 430, 427, BEAM, 3)]
    # beam splitter (45°)
    body += [_line(395, 387, 465, 467, OPTIC, 4),
             _t(360, 478, "beam splitter", 14, OPTIC)]
    body += [_box(400, 230, 130, 22, "fixed mirror", fill=TINT_OPTIC,
                  stroke=OPTIC, width=2),
             _arrow(430, 410, 460, 256, OPTIC, 2)]
    body += [_box(690, 392, 22, 110, fill=TINT_OPTIC, stroke=OPTIC, width=2),
             _arrow(720, 460, 760, 460, OPTIC, 2),
             _t(640, 516, "moving mirror →", 14, OPTIC),
             _arrow(465, 427, 685, 447, OPTIC, 2)]
    body += [_arrow(430, 467, 430, 560, BEAM, 3)]
    body += [_box(350, 560, 160, 70, "sample", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_arrow(430, 630, 430, 700, SIGNAL, 3),
             _box(350, 700, 160, 70, "detector (DTGS)", fill=TINT_DET,
                  stroke=DETC, width=2)]
    body += [_t(560, 410, "Michelson interferometer", 15, MUTE)]
    body += _bigplot("Wavenumber (cm⁻¹)", "Transmittance (%)",
                    [(0, .92), (.08, .9), (.12, .5), (.16, .9), (.3, .88),
                     (.34, .28), (.38, .86), (.52, .82), (.58, .4), (.63, .84),
                     (.78, .8), (.85, .45), (.9, .82), (1, .86)],
                    peaks=[(.14, "O–H"), (.36, "C=O"), (.6, "C–H"),
                           (.86, "C–O")], color=DETC)
    return _page("Fourier-Transform Infrared Spectroscopy (FTIR)",
                 "Molecular bonds & functional groups", SP, body,
                 "A Michelson interferometer modulates broadband IR light; "
                 "the Fourier transform of the interferogram yields an "
                 "absorption spectrum that fingerprints chemical bonds.")


# ===================================================== Spectroscopy: Raman
def build_raman():
    body = [_box(120, 300, 120, 64, "laser", fill=TINT_BEAM, stroke=BEAM,
                 width=2)]
    body += [_arrow(240, 332, 430, 332, BEAM, 3)]
    body += [_line(410, 312, 460, 362, OPTIC, 3),
             _t(380, 372, "dichroic / notch", 13, OPTIC)]
    body += [_box(400, 470, 80, 30, "objective", fill=TINT_OPTIC,
                  stroke=OPTIC, width=2),
             _poly("triangle", 412, 500, 56, 36, fill=TINT_OPTIC,
                   stroke=OPTIC, rotation=180),
             _arrow(435, 360, 435, 470, BEAM, 2)]
    body += [_box(360, 560, 160, 64, "sample", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_arrow(435, 540, 435, 372, SIGNAL, 2),
             _arrow(460, 337, 640, 337, SIGNAL, 2),
             _t(520, 312, "scattered light", 13, SIGNAL)]
    body += _grating(650, 308, 70, 56)
    body += [_t(648, 372, "grating", 13, OPTIC)]
    body += [_arrow(722, 320, 800, 320, SIGNAL, 2),
             _box(800, 290, 120, 64, "CCD", fill=TINT_DET, stroke=DETC,
                  width=2)]
    body += _bigplot("Raman shift (cm⁻¹)", "Intensity (a.u.)",
                    [(0, .1), (.28, .1), (.32, .72), (.36, .12), (.5, .12),
                     (.54, .9), (.58, .12), (.74, .12), (.78, .4), (.82, .1),
                     (1, .1)],
                    peaks=[(.34, "D band"), (.56, "G band"), (.8, "2D")],
                    color=DETC)
    return _page("Raman Spectroscopy",
                 "Vibrational fingerprint & disorder", SP, body,
                 "Monochromatic laser light is inelastically scattered by "
                 "molecular vibrations; the Raman shift spectrum is sensitive "
                 "to bonding, strain, crystallinity and disorder.")


# ==================================================== Spectroscopy: UV-Vis
def build_uvvis():
    body = [_box(110, 392, 110, 70, "lamp\n(D₂ / W)", fill=TINT_BEAM,
                 stroke=BEAM, width=2)]
    body += [_arrow(220, 427, 300, 427, BEAM, 3)]
    body += _grating(300, 400, 70, 56)
    body += [_t(298, 466, "monochromator", 13, OPTIC),
             _arrow(372, 427, 470, 427, BEAM, 3)]
    body += [_box(470, 392, 90, 90, "cuvette\n(sample)", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_arrow(560, 427, 660, 427, SIGNAL, 3),
             _box(660, 392, 120, 70, "photodiode\ndetector", fill=TINT_DET,
                  stroke=DETC, width=2)]
    body += [_box(800, 392, 130, 70, "absorbance\nA = log(I₀/I)",
                  fill="#eef2f5", stroke=INK, width=2)]
    body += _bigplot("Wavelength (nm)", "Absorbance",
                    [(0, .12), (.15, .2), (.3, .45), (.4, .78), (.46, .6),
                     (.5, .66), (.62, .3), (.78, .16), (1, .1)],
                    peaks=[(.43, "λ_max")], color=DETC)
    return _page("UV-Visible Spectroscopy (UV-Vis)",
                 "Electronic transitions & concentration", SP, body,
                 "Light is split by wavelength and passed through the sample; "
                 "the absorbance spectrum gives band gaps, chromophores and, "
                 "via Beer–Lambert, concentration.")


# ===================================================== Spectroscopy: XRF
def build_xrf():
    body = [_round(110, 470, 180, 120, "X-ray tube", fill=TINT_BEAM,
                   stroke=BEAM, width=2)]
    body += [_arrow(290, 528, 470, 600, BEAM, 3),
             _t(300, 512, "primary X-rays", 14, BEAM)]
    body += [_box(440, 590, 210, 110, "sample", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_arrow(545, 590, 740, 470, SIGNAL, 3),
             _t(640, 470, "fluorescent X-rays", 14, SIGNAL)]
    body += [_box(740, 410, 180, 120, "energy-dispersive\ndetector (SDD)",
                  fill=TINT_DET, stroke=DETC, width=2)]
    body += [_arrow(830, 530, 830, 600, DETC, 2),
             _box(740, 600, 180, 90, "multichannel\nanalyser", fill="#eef2f5",
                  stroke=INK, width=2)]
    body += _bigplot("X-ray energy (keV)", "Counts",
                    [(0, .08), (.1, .08), (.108, .82), (.12, .08), (.27, .08),
                     (.278, .55), (.29, .08), (.44, .08), (.448, .66),
                     (.46, .08), (.6, .08), (.608, .35), (.62, .08),
                     (.76, .08), (.768, .48), (.78, .08), (1, .08)],
                    peaks=[(.108, "K"), (.278, "Ca"), (.448, "Fe"),
                           (.608, "Cu"), (.768, "Zn")], color=DETC)
    return _page("X-ray Fluorescence (XRF)",
                 "Elemental composition (bulk, non-destructive)", SP, body,
                 "Primary X-rays ionise inner-shell electrons; the atoms relax "
                 "by emitting characteristic fluorescent X-rays whose energies "
                 "and intensities give elemental identity and amount.")


# ===================================================== Spectroscopy: NMR
def build_nmr():
    cx = 360
    # superconducting magnet cryostat (nested rings) with vertical bore
    body = [_circle(cx - 180, 250, 360, fill="#eaf1f8", stroke="#9bb6d2",
                    width=3),
            _circle(cx - 140, 290, 280, fill="#dfeaf5", stroke=COOL, width=2),
            _circle(cx - 55, 375, 110, fill="#ffffff", stroke="#9bb6d2",
                    width=2)]
    body += [_box(cx - 14, 250, 28, 380, fill="#ffffff", stroke="#c4ccd4",
                  width=2)]                              # bore
    body += [_box(cx - 9, 360, 18, 150, "", fill=TINT_SAMP, stroke="#9a7b1f",
                  width=1)]                              # sample tube
    body += [_box(cx - 28, 410, 56, 50, fill=None, stroke=OPTIC, width=3),
             _t(cx + 40, 420, "RF coil", 14, OPTIC)]
    body += [_t(cx - 150, 612, "superconducting magnet (liquid He)", 14, COOL)]
    body += [_box(700, 360, 180, 70, "RF transmitter\n/ receiver",
                  fill=TINT_DET, stroke=DETC, width=2),
             _box(700, 450, 180, 70, "console / FT", fill="#eef2f5",
                  stroke=INK, width=2),
             _arrow(700, 430, cx + 30, 435, SIGNAL, 2)]
    body += _bigplot("Chemical shift δ (ppm)", "Intensity",
                    [(1, .08), (.22, .08), (.235, .6), (.25, .08), (.45, .08),
                     (.46, .9), (.475, .08), (.475, .08), (.66, .08),
                     (.675, .45), (.69, .08), (.95, .08), (.96, .3),
                     (.975, .08), (0, .08)],
                    peaks=[(.235, "aromatic"), (.46, "CH₂"), (.675, "CH₃"),
                           (.96, "TMS")], color=DETC)
    return _page("Nuclear Magnetic Resonance (NMR)",
                 "Molecular structure & connectivity", SP, body,
                 "Nuclei in a strong magnetic field absorb radio-frequency "
                 "pulses; the Fourier-transformed free-induction decay gives "
                 "chemical shifts and couplings that map molecular structure.")


# ==================================================== Mass spec: SIMS
def build_sims():
    body = [_round(110, 300, 170, 90, "primary\nion gun", fill=TINT_BEAM,
                   stroke=BEAM, width=2)]
    body += [_arrow(280, 360, 470, 560, BEAM, 3),
             _t(300, 420, "primary ions (O⁻, Cs⁺)", 14, BEAM)]
    body += [_box(430, 560, 200, 90, "sample", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_arrow(520, 560, 700, 380, SIGNAL, 3),
             _t(610, 360, "secondary ions", 14, SIGNAL)]
    body += [_box(700, 300, 220, 110, "mass analyser\n(ToF / quadrupole)",
                  fill=TINT_OPTIC, stroke=OPTIC, width=2)]
    body += [_arrow(810, 410, 810, 480, SIGNAL, 2),
             _box(720, 480, 180, 80, "ion detector", fill=TINT_DET,
                  stroke=DETC, width=2)]
    body += _bigplot("Sputter depth (nm)", "Secondary-ion intensity",
                    [(0, .85), (.12, .82), (.28, .6), (.4, .3), (.5, .18),
                     (.62, .14), (.8, .12), (1, .1)],
                    peaks=[(.05, "surface")], color=SIGNAL)
    return _page("Secondary-Ion Mass Spectrometry (SIMS)",
                 "Trace analysis & depth profiling", MS, body,
                 "A focused primary-ion beam sputters the surface; ejected "
                 "secondary ions are mass-analysed, giving ppb-level "
                 "sensitivity and nanometre depth profiles.")


# ==================================================== Mass spec: ICP-MS
def build_icpms():
    body = [_box(110, 400, 130, 70, "nebuliser\n(sample)", fill=TINT_SAMP,
                 stroke="#9a7b1f", width=2)]
    body += [_arrow(240, 435, 320, 435, COOL, 3)]
    # plasma torch
    body += [_poly("triangle", 320, 390, 150, 90, fill="#ffe2b0",
                   stroke="#e08a1e", rotation=90),
             _t(330, 488, "Ar plasma (~7000 K)", 13, "#e08a1e")]
    body += [_arrow(470, 435, 540, 435, BEAM, 3)]
    body += [_poly("triangle", 540, 405, 50, 60, fill="#cdd6de", stroke=MUTE,
                   rotation=90),
             _poly("triangle", 590, 408, 44, 54, fill="#cdd6de", stroke=MUTE,
                   rotation=90),
             _t(536, 474, "sampler / skimmer cones", 12, MUTE)]
    body += [_arrow(636, 435, 700, 435, SIGNAL, 3),
             _box(700, 400, 150, 70, "quadrupole\nmass filter",
                  fill=TINT_OPTIC, stroke=OPTIC, width=2),
             _arrow(850, 435, 910, 435, SIGNAL, 3),
             _box(910, 400, 110, 70, "detector", fill=TINT_DET, stroke=DETC,
                  width=2)]
    body += _bigplot("m/z", "Counts per second",
                    [(0, .06), (.14, .06), (.148, .85), (.16, .06), (.34, .06),
                     (.348, .5), (.36, .06), (.52, .06), (.528, .7), (.54, .06),
                     (.72, .06), (.728, .4), (.74, .06), (.88, .06), (.888, .6),
                     (.9, .06), (1, .06)],
                    peaks=[(.148, "²⁴Mg"), (.348, "⁵⁶Fe"), (.528, "⁶³Cu"),
                           (.728, "⁹⁵Mo"), (.888, "²⁰⁸Pb")], color=DETC)
    return _page("Inductively-Coupled-Plasma Mass Spectrometry (ICP-MS)",
                 "Ultra-trace multi-element analysis", MS, body,
                 "Sample aerosol is ionised in an argon plasma; ions pass "
                 "through sampling cones into a quadrupole mass filter, giving "
                 "part-per-trillion elemental and isotopic quantification.")


# ==================================================== Mass spec: GC-MS
def build_gcms():
    body = [_box(110, 320, 110, 64, "injector", fill=TINT_SAMP,
                 stroke="#9a7b1f", width=2)]
    # oven with coiled column
    body += [_round(110, 430, 360, 260, fill=TINT_BODY, stroke="#c4ccd4")]
    body += [_circle(170, 470, 180, fill=None, stroke=SIGNAL, width=3),
             _circle(200, 500, 120, fill=None, stroke=SIGNAL, width=3),
             _circle(225, 525, 70, fill=None, stroke=SIGNAL, width=3),
             _t(150, 700, "GC column (in oven)", 14, MUTE)]
    body += [_arrow(165, 384, 165, 430, SIGNAL, 2)]
    body += [_arrow(470, 520, 540, 520, SIGNAL, 3)]
    body += [_box(540, 440, 150, 80, "ion source\n(EI 70 eV)", fill=TINT_BEAM,
                  stroke=BEAM, width=2),
             _box(700, 440, 150, 80, "quadrupole", fill=TINT_OPTIC,
                  stroke=OPTIC, width=2),
             _box(860, 440, 110, 80, "detector", fill=TINT_DET, stroke=DETC,
                  width=2),
             _arrow(690, 480, 700, 480, SIGNAL, 2),
             _arrow(850, 480, 860, 480, SIGNAL, 2)]
    body += _bigplot("Retention time (min)", "Total-ion current",
                    [(0, .08), (.12, .08), (.14, .7), (.16, .08), (.3, .08),
                     (.32, .9), (.34, .08), (.48, .08), (.5, .45), (.52, .08),
                     (.66, .08), (.68, .6), (.7, .08), (.84, .08), (.86, .35),
                     (.88, .08), (1, .08)], color=SIGNAL)
    return _page("Gas Chromatography–Mass Spectrometry (GC-MS)",
                 "Separation & identification of volatiles", MS, body,
                 "Volatile analytes are separated on a capillary column in a "
                 "temperature-programmed oven, then ionised and mass-analysed "
                 "— each chromatographic peak carries an identifying spectrum.")


# ==================================================== Diffraction: XRD
def build_xrd():
    cx, cy = 540, 540
    body = [_circle(cx - 300, cy - 300, 600, fill=None, stroke="#cdd6de",
                    width=2)]
    body += [_round(cx - 470, cy - 55, 160, 110, "X-ray tube", fill=TINT_BEAM,
                    stroke=BEAM, width=2)]
    body += [_arrow(cx - 300, cy, cx - 80, cy, BEAM, 3)]
    body += _aperture(cx - 150, cy, 10, 26)
    body += [_box(cx - 80, cy - 46, 160, 92, "sample (θ)", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_arrow(cx + 70, cy, cx + 285, cy - 165, SIGNAL, 3),
             _t(cx + 150, cy - 190, "2θ", 22, SIGNAL)]
    body += [_box(cx + 250, cy - 240, 160, 96, "detector", fill=TINT_DET,
                  stroke=DETC, width=2)]
    body += [_line(cx, cy, cx + 300, cy, "#cdd6de", 1),
             _t(cx - 70, cy + 320, "goniometer circle", 14, MUTE)]
    body += _bigplot("2θ (degrees)", "Intensity (counts)",
                    [(0, .06), (.14, .06), (.146, .92), (.155, .06), (.3, .06),
                     (.306, .5), (.315, .06), (.46, .06), (.466, .72),
                     (.475, .06), (.6, .06), (.606, .38), (.615, .06),
                     (.74, .06), (.746, .55), (.755, .06), (.88, .06),
                     (.886, .3), (.895, .06), (1, .06)],
                    peaks=[(.15, "(111)"), (.31, "(200)"), (.47, "(220)"),
                           (.61, "(311)"), (.75, "(222)")], color=DETC)
    return _page("X-ray Diffraction (XRD)",
                 "Crystal structure & phase identification", DF, body,
                 "A monochromatic X-ray beam is scanned in angle; Bragg "
                 "reflection (nλ = 2d·sinθ) from lattice planes produces a "
                 "diffractogram that fingerprints crystalline phases.")


# ==================================================== Diffraction: LEED
def build_leed():
    cx = 380
    body = [_box(cx - 200, 300, 400, 300, shape="halfcircle", stroke=SIGNAL,
                 width=3, fill="#eafaf0")]
    body += [_box(cx - 150, 350, 300, 250, shape="halfcircle", stroke=SIGNAL,
                  width=2, fill=None)]
    body += [_t(cx + 60, 300, "fluorescent screen + grids", 13, SIGNAL)]
    body += [_box(cx - 30, 560, 60, 90, "e⁻ gun", fill=TINT_BEAM, stroke=BEAM,
                  width=2)]
    body += [_arrow(cx, 560, cx, 470, BEAM, 3)]
    body += _stage(cx, 470, 110, "crystal")
    body += [_arrow(cx, 462, cx - 120, 360, SIGNAL, 2),
             _arrow(cx, 462, cx + 120, 360, SIGNAL, 2)]
    # LEED pattern panel (hexagonal spots)
    body += [_box(700, 300, 420, 420, fill="#0a0c10", stroke=INK, width=2)]
    pcx, pcy = 910, 510
    body += [_circle(pcx - 11, pcy - 11, 22, fill="#eafaf0", stroke="#eafaf0")]
    body += _ring(pcx, pcy, 90, 6, 18, color="#bfe9cf", start=math.pi / 6)
    body += _ring(pcx, pcy, 160, 6, 14, color="#bfe9cf", start=math.pi / 6)
    body += _ring(pcx, pcy, 175, 6, 12, color="#bfe9cf")
    body += [_tc(910, 730, "LEED pattern (hexagonal surface)", 14, MUTE)]
    return _page("Low-Energy Electron Diffraction (LEED)",
                 "Surface crystallography & ordering", DF, body,
                 "Low-energy electrons (20–200 eV) back-diffract from the "
                 "topmost atomic layers; the symmetry and spacing of the spot "
                 "pattern reveal the surface lattice and any reconstruction or "
                 "adsorbate superstructure.")


# ==================================================== Thermal: TGA
def build_tga():
    cx = 420
    body = [_box(cx - 70, 250, 140, 46, "microbalance", fill="#eef2f5",
                 stroke=INK, width=2)]
    body += [_line(cx, 296, cx, 430, MUTE, 2)]
    body += [_round(cx - 150, 430, 300, 320, fill=TINT_BEAM, stroke=BEAM,
                    width=2)]
    body += [_box(cx - 48, 470, 96, 70, "crucible\n(sample)", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    for yy in (470, 540, 610):
        body += [_line(cx - 135, yy, cx - 60, yy, BEAM, 3),
                 _line(cx + 60, yy, cx + 135, yy, BEAM, 3)]
    body += [_t(cx - 140, 762, "furnace (heating elements)", 14, BEAM)]
    body += [_arrow(cx + 210, 700, cx + 130, 640, COOL, 3),
             _t(cx + 150, 716, "purge gas", 13, COOL)]
    body += [_box(720, 300, 200, 80, "thermocouple\n+ controller",
                  fill="#eef2f5", stroke=INK, width=2),
             _arrow(720, 360, cx + 140, 540, MUTE, 1)]
    body += _bigplot("Temperature (°C)", "Mass (%)",
                    [(0, .97), (.16, .95), (.2, .8), (.3, .76), (.44, .74),
                     (.5, .46), (.6, .42), (.78, .4), (1, .38)], color=DETC)
    return _page("Thermogravimetric Analysis (TGA)",
                 "Mass change with temperature", TH, body,
                 "A sample on a microbalance is heated under a controlled "
                 "atmosphere; the mass-loss curve reveals moisture, "
                 "decomposition steps, oxidation and residual ash.")


# ==================================================== Thermal: DSC
def build_dsc():
    cx = 420
    body = [_round(cx - 200, 360, 400, 280, fill=TINT_BEAM, stroke=BEAM,
                   width=2)]
    body += [_box(cx - 150, 470, 110, 60, "sample\npan", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2),
             _box(cx + 40, 470, 110, 60, "reference\npan", fill=TINT_OPTIC,
                  stroke=OPTIC, width=2)]
    body += [_box(cx - 150, 540, 110, 26, fill="#cdd6de", stroke=MUTE,
                  width=1),
             _box(cx + 40, 540, 110, 26, fill="#cdd6de", stroke=MUTE,
                  width=1),
             _t(cx - 165, 580, "heat-flow sensors / thermocouples", 13, MUTE)]
    for yy in (590, 620):
        body += [_line(cx - 180, yy, cx + 180, yy, BEAM, 3)]
    body += [_t(cx - 150, 350, "furnace block", 14, BEAM)]
    body += _bigplot("Temperature (°C)", "Heat flow (endo →)",
                    [(0, .5), (.18, .5), (.26, .28), (.34, .5), (.5, .5),
                     (.56, .78), (.64, .5), (.78, .5), (.84, .34), (.9, .5),
                     (1, .5)],
                    peaks=[(.3, "T_g / melt"), (.6, "crystallisation"),
                           (.86, "decomp.")], color=DETC)
    return _page("Differential Scanning Calorimetry (DSC)",
                 "Thermal transitions & heat flow", TH, body,
                 "Sample and reference pans are heated together; the "
                 "differential heat flow needed to keep them at the same "
                 "temperature reveals melting, crystallisation and glass "
                 "transitions.")


# ==================================================== Thermal: BET
def build_bet():
    cx = 430
    body = [_box(cx - 60, 250, 250, 70, "N₂ dosing\nmanifold", fill=TINT_OPTIC,
                 stroke=OPTIC, width=2)]
    body += [_box(cx + 210, 250, 150, 70, "pressure\ntransducer",
                  fill=TINT_DET, stroke=DETC, width=2),
             _line(cx + 60, 285, cx + 210, 285, MUTE, 2)]
    body += [_arrow(cx + 60, 320, cx + 60, 440, COOL, 3)]
    body += [_round(cx, 440, 120, 360, fill=TINT_COOL, stroke=COOL, width=2)]
    body += [_box(cx + 30, 480, 60, 130, "sample", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2)]
    body += [_t(cx - 30, 818, "liquid-N₂ dewar (77 K)", 14, COOL)]
    body += _bigplot("Relative pressure  p/p₀", "Quantity adsorbed (cm³/g)",
                    [(0, .1), (.08, .26), (.18, .33), (.35, .4), (.55, .48),
                     (.72, .58), (.86, .74), (.95, .9), (1, .98)],
                    peaks=[(.2, "monolayer (BET)")], color=DETC)
    return _page("Gas Sorption — BET Surface Area",
                 "Specific surface area & porosity", TH, body,
                 "Nitrogen is dosed onto a degassed sample at 77 K; the "
                 "adsorption isotherm, fitted with the BET equation, gives the "
                 "specific surface area, while hysteresis reveals porosity.")


# ==================================================== Chromatography: HPLC
def build_hplc():
    body = [_box(110, 280, 90, 70, "solvent\nA", fill=TINT_COOL, stroke=COOL,
                 width=2),
            _box(210, 280, 90, 70, "solvent\nB", fill=TINT_COOL, stroke=COOL,
                 width=2)]
    body += [_arrow(155, 350, 230, 430, COOL, 2),
             _arrow(255, 350, 250, 430, COOL, 2)]
    body += [_box(200, 430, 110, 64, "pump", fill=TINT_OPTIC, stroke=OPTIC,
                  width=2),
             _arrow(310, 462, 380, 462, COOL, 3)]
    body += [_box(380, 430, 100, 64, "injector", fill=TINT_SAMP,
                  stroke="#9a7b1f", width=2),
             _arrow(480, 462, 540, 462, COOL, 3)]
    body += [_box(540, 422, 220, 80, "separation column", fill=TINT_BODY,
                  stroke=MUTE, width=2),
             _arrow(760, 462, 820, 462, SIGNAL, 3)]
    body += [_box(820, 430, 120, 64, "UV / DAD\ndetector", fill=TINT_DET,
                  stroke=DETC, width=2)]
    body += [_box(820, 540, 120, 56, "waste", fill="#eef2f5", stroke=INK,
                  width=2), _arrow(880, 494, 880, 540, COOL, 2)]
    body += _bigplot("Retention time (min)", "Absorbance (mAU)",
                    [(0, .08), (.12, .08), (.14, .55), (.16, .08), (.3, .08),
                     (.33, .9), (.36, .08), (.5, .08), (.52, .4), (.54, .08),
                     (.64, .08), (.67, .7), (.7, .08), (.84, .08), (.87, .3),
                     (.89, .08), (1, .08)],
                    peaks=[(.14, "t₀"), (.33, "analyte 1"), (.67, "analyte 2")],
                    color=DETC)
    return _page("High-Performance Liquid Chromatography (HPLC)",
                 "Separation & quantification in solution", CH, body,
                 "A high-pressure pump drives a solvent gradient carrying the "
                 "injected sample through a packed column; analytes separate by "
                 "affinity and are quantified as detector peaks.")


# (further builders appended below)
SKETCHES = [
    ("Spectroscopy", "XPS — X-ray Photoelectron Spectroscopy", build_xps),
    ("Spectroscopy", "UPS — Ultraviolet Photoelectron Spectroscopy",
     build_ups),
    ("Spectroscopy", "AES — Auger Electron Spectroscopy", build_aes),
    ("Spectroscopy", "FTIR — Fourier-Transform Infrared", build_ftir),
    ("Spectroscopy", "Raman Spectroscopy", build_raman),
    ("Spectroscopy", "UV-Vis Spectroscopy", build_uvvis),
    ("Spectroscopy", "XRF — X-ray Fluorescence", build_xrf),
    ("Spectroscopy", "NMR — Nuclear Magnetic Resonance", build_nmr),
    ("Mass spectrometry", "SIMS — Secondary-Ion Mass Spectrometry",
     build_sims),
    ("Mass spectrometry", "ICP-MS — Inductively-Coupled-Plasma MS",
     build_icpms),
    ("Mass spectrometry", "GC-MS — Gas Chromatography–Mass Spec", build_gcms),
    ("Diffraction", "XRD — X-ray Diffraction", build_xrd),
    ("Diffraction", "LEED — Low-Energy Electron Diffraction", build_leed),
    ("Microscopy", "TEM — Transmission Electron Microscopy", build_tem),
    ("Microscopy", "SEM — Scanning Electron Microscopy", build_sem),
    ("Microscopy", "AFM — Atomic Force Microscopy", build_afm),
    ("Microscopy", "STM — Scanning Tunnelling Microscopy", build_stm),
    ("Thermal & sorption", "TGA — Thermogravimetric Analysis", build_tga),
    ("Thermal & sorption", "DSC — Differential Scanning Calorimetry",
     build_dsc),
    ("Thermal & sorption", "BET — Gas Sorption (surface area)", build_bet),
    ("Chromatography", "HPLC — High-Performance Liquid Chromatography",
     build_hplc),
]
