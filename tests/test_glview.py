"""OpenGL Molecule-builder preview: camera/picking math and the
`MoleculeViewer.render_geometry` contract it consumes.

Runs headless (no real GL context needed — `_rotation_rows`/`_build_camera`
/`_project` are plain functions, tested the same way `molecules._proj` is).

Run with: python -m pytest tests/  (offscreen Qt).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PyQt5.QtWidgets import QApplication

from khervepaint import glview, molecules, molview

pytestmark = pytest.mark.skipif(not glview.GL_AVAILABLE,
                                reason="PyOpenGL not installed")


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def test_rotation_rows_orthonormal():
    for az_deg in (0, 28, 90, 143, 270):
        for el_deg in (-80, -20, 0, 20, 89):
            rows = glview._rotation_rows(math.radians(az_deg),
                                         math.radians(el_deg))
            for row in rows:
                assert math.isclose(sum(v * v for v in row), 1.0, abs_tol=1e-9)
            for a, b in ((rows[0], rows[1]), (rows[0], rows[2]),
                        (rows[1], rows[2])):
                dot = sum(x * y for x, y in zip(a, b))
                assert math.isclose(dot, 0.0, abs_tol=1e-9)


def test_rotation_rows_match_proj():
    # glview's camera rotation must agree exactly with molecules._proj —
    # the flat preview and the GL preview share the same "standard views".
    az, el = molecules.DEFAULT_AZ, molecules.DEFAULT_EL
    row0, row1, row2 = glview._rotation_rows(az, el)
    p = (1.3, -0.7, 2.1)
    sx, sy, depth = molecules._proj(*p, az, el)
    assert math.isclose(glview._dot(row0, p), sx, abs_tol=1e-9)
    assert math.isclose(glview._dot(row1, p), -sy, abs_tol=1e-9)
    assert math.isclose(glview._dot(row2, p), depth, abs_tol=1e-9)


def test_build_camera_and_project_round_trip(app):
    dlg = molview.MoleculeViewer("ethanol")
    geom = dlg.render_geometry()
    cam = glview._build_camera(geom, dlg.az, dlg.el, geom["rscale"], 480, 360)
    assert cam["right"] > cam["left"]
    assert cam["top"] > cam["bottom"]
    assert cam["near"] < cam["far"]
    for atom in geom["atoms"]:
        sx, sy, _depth = glview._project(cam, atom[1:4])
        assert -1 <= sx <= cam["width"] + 1
        assert -1 <= sy <= cam["height"] + 1


def test_pick_finds_clicked_atom(app):
    dlg = molview.MoleculeViewer("ethanol")
    geom = dlg.render_geometry()
    cam = glview._build_camera(geom, dlg.az, dlg.el, geom["rscale"], 480, 360)
    preview = glview.GLPreview.__new__(glview.GLPreview)
    preview._cam = cam
    preview._geom = geom
    for idx, atom in enumerate(geom["atoms"]):
        sx, sy, _ = glview._project(cam, atom[1:4])
        picked = preview._pick(sx, sy)
        assert picked is not None
        # an overlapping nearer atom is a valid pick too — just never miss
        picked_depth = glview._project(cam, geom["atoms"][picked][1:4])[2]
        clicked_depth = glview._project(cam, atom[1:4])[2]
        assert picked_depth >= clicked_depth - 1e-6


def test_pick_misses_empty_space(app):
    dlg = molview.MoleculeViewer("ethanol")
    geom = dlg.render_geometry()
    cam = glview._build_camera(geom, dlg.az, dlg.el, geom["rscale"], 480, 360)
    preview = glview.GLPreview.__new__(glview.GLPreview)
    preview._cam = cam
    preview._geom = geom
    assert preview._pick(-9999, -9999) is None


def test_render_geometry_crystal_with_polyhedra(app):
    dlg = molview.MoleculeViewer("perovskite")
    dlg.poly = True
    geom = dlg.render_geometry()
    assert geom["atoms"]
    assert geom["edges"]                 # unit-cell wireframe
    assert geom["faces"]                 # BX6 octahedra
    for face_points, color in geom["faces"]:
        assert len(face_points) >= 3
        assert color.startswith("#")


def test_render_geometry_atom_colors_resolved(app):
    dlg = molview.MoleculeViewer("ethanol")
    geom = dlg.render_geometry()
    for atom in geom["atoms"]:
        element, x, y, z, color = atom
        assert isinstance(color, str) and color.startswith("#")


def test_screen_delta_to_world_uses_bond_scale(app):
    dlg = molview.MoleculeViewer("ethanol")
    dlg.bond = 1.0
    geom = dlg.render_geometry()
    cam = glview._build_camera(geom, dlg.az, dlg.el, geom["rscale"], 480, 360)
    preview = glview.GLPreview.__new__(glview.GLPreview)
    preview._b = dlg
    preview._cam = cam
    d1 = preview._screen_delta_to_world(10, 0)
    dlg.bond = 2.0
    d2 = preview._screen_delta_to_world(10, 0)
    # a bigger bond spread means the same pixel drag moves the underlying
    # (pre-spread) atom coordinate less
    len1 = math.sqrt(sum(v * v for v in d1))
    len2 = math.sqrt(sum(v * v for v in d2))
    assert len2 < len1
