"""3D-schematic palette (slabs, particle beds, glows), diatomic molecules
and zero atom-spacing for crystals.

Run with: python -m pytest tests/  (offscreen Qt).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QApplication

from khervepaint import ai_assistant, document, molecules, scheme3d, svgio
from khervepaint.canvas import PaintScene


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(600, 480)


# --------------------------------------------------------- scheme3d palette
def test_registry_is_consistent():
    names = set(scheme3d._BUILDERS)
    assert names == set(scheme3d.LABELS) == set(scheme3d.SIZES)
    cat_names = [n for _t, ns in scheme3d.CATEGORIES for n in ns]
    assert set(cat_names) == names and len(cat_names) == len(names)


def test_every_symbol_builds_to_items(app):
    for name in scheme3d._BUILDERS:
        w, h = scheme3d.size_mm(name)
        specs = scheme3d.build_specs(name, w * 3, h * 3)
        assert specs, name
        items = [ai_assistant._spec_to_item(s) for s in specs]
        assert all(it is not None for it in items), name


def test_slab_has_three_shaded_faces(app):
    specs = scheme3d.build_specs("slab_orange", 300, 90)
    fills = [s["fill"] for s in specs]
    assert len(specs) == 3 and len(set(fills)) == 3   # top/front/side shades
    kinds = {s["shape"] for s in specs}
    assert kinds == {"polygon", "rect"}


def test_bed_spheres_are_lit_and_staggered(app):
    specs = scheme3d.build_specs("bed_blue", 288, 78)
    circles = [s for s in specs if s.get("shape") == "circle"]
    assert len(circles) > 12                          # a real pile
    assert all(s["fill"]["kind"] == "sun" for s in circles)
    xs = sorted({round(s["x"], 1) for s in circles})
    assert len(xs) > len(circles) / 3                 # staggered offsets


def test_glow_uses_translucent_layers(app):
    specs = scheme3d.build_specs("glow_orange", 48, 48)
    ops = [s.get("opacity") for s in specs]
    assert len(specs) == 3 and ops == sorted(ops)     # fades outward
    item = ai_assistant._spec_to_item(specs[0])
    assert 0 < item.opacity() < 0.5                   # opacity really applied


def test_polygon_points_spec(app):
    item = ai_assistant._spec_to_item(
        {"shape": "polygon", "points": [[0, 10], [10, 0], [40, 0], [30, 10]],
         "fill": "#ff0000", "stroke": "#000000"})
    assert item is not None and item.polygon().count() == 4


def test_place_s3d_element_is_grouped_and_undoable(scene):
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    before = len(scene.vector_items())
    scene.place_s3d_element("bed_grey", QPointF(300, 240))
    assert len(scene.vector_items()) == before + 1    # one group
    assert fired == [1]                               # one gesture


def test_s3d_round_trips_json_and_svg(scene, tmp_path):
    scene.place_s3d_element("slab_grey", QPointF(300, 240))
    scene.place_s3d_element("glow_blue", QPointF(200, 150))
    n = len(scene.vector_items())
    data = document.scene_to_dict(scene)
    restored = PaintScene(600, 480)
    document.dict_to_scene(data, restored)
    assert len(restored.vector_items()) == n
    path = str(tmp_path / "s3d.svg")
    svgio.save_svg(scene, path)
    r2 = PaintScene(600, 480)
    svgio.load_svg(r2, path)
    assert len(r2.vector_items()) == n


# ------------------------------------------------------- diatomic molecules
def test_diatomics_are_registered_and_build():
    for name, count in (("hydrogen", 2), ("oxygen", 2), ("nitrogen", 2)):
        w, h = molecules.size_mm(name)
        spheres = [s for s in molecules.build_specs(name, w * 3, h * 3)
                   if s.get("shape") == "circle"]
        assert len(spheres) == count, name
    assert molecules.resolve_name("O2") == "oxygen"
    assert molecules.resolve_name("h2") == "hydrogen"
    assert molecules.resolve_name("dinitrogen") == "nitrogen"


# ------------------------------------------------------- zero atom spacing
def _sphere_centres(specs):
    return [(s["x"] + s["w"] / 2, s["y"] + s["h"] / 2)
            for s in specs if s.get("shape") == "circle"]


def test_crystal_spacing_shrinks_to_zero():
    spread1 = _sphere_centres(
        molecules.build_specs_oriented("fcc", 300, 300, bond=1.0))
    spread0 = _sphere_centres(
        molecules.build_specs_oriented("fcc", 300, 300, bond=0.0))
    # at 0 every atom collapses onto the centroid
    assert len({(round(x, 2), round(y, 2)) for x, y in spread0}) == 1
    assert len({(round(x, 2), round(y, 2)) for x, y in spread1}) > 1
    # partial contraction keeps distinct but closer atoms
    part = _sphere_centres(
        molecules.build_specs_oriented("simple_cubic", 300, 300, bond=0.3))
    assert len({(round(x, 1), round(y, 1)) for x, y in part}) > 1


def test_zero_spacing_survives_reorient(scene):
    scene.place_mol_element("simple_cubic", QPointF(300, 240))
    (top,) = scene.selectedItems()
    new = scene.reorient_model(top, top.mol_az, top.mol_el, bond=0.0)
    assert new.mol_bond == 0.0
    # a plain rotation must KEEP the 0.0 spacing, not fall back to 1.0
    spun = scene.reorient_model(new, 0.5, 0.3)
    assert spun.mol_bond == 0.0


def test_builder_spacing_slider_reaches_zero(app):
    from khervepaint.molview import MoleculeViewer
    xtal = MoleculeViewer("fcc")
    assert xtal.bond_slider.isEnabled()
    assert xtal.bond_slider.minimum() == 0
    xtal.bond_slider.setValue(0)
    assert xtal.bond == 0.0
    # molecules keep the safe lower bound
    mol = MoleculeViewer("methane")
    assert mol.bond_slider.minimum() == 80
    xtal.deleteLater(); mol.deleteLater()
