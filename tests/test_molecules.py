"""Molecular-model tests: builders, AI atom/bond vocabulary, placement and
lit-sphere gradient round-trip (JSON snapshot + SVG file).

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

from khervepaint import ai_assistant, document, gradient, molecules, svgio
from khervepaint.canvas import PaintScene


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(600, 480)


def test_registry_is_consistent():
    names = set(molecules.SIZES)
    assert names == set(molecules.LABELS)
    cat_names = [n for _title, ns in molecules.CATEGORIES for n in ns]
    assert set(cat_names) == names
    assert len(cat_names) == len(names)          # no duplicates


def test_every_model_builds_to_items(app):
    for name in molecules.SIZES:
        w, h = molecules.size_mm(name)
        specs = molecules.build_specs(name, w * 3, h * 3)
        assert specs, name
        items = [ai_assistant._spec_to_item(s) for s in specs]
        assert all(it is not None for it in items), name


def test_known_atom_counts():
    # (element spheres are `circle` specs)
    def spheres(name):
        w, h = molecules.size_mm(name)
        return sum(1 for s in molecules.build_specs(name, w, h)
                   if s.get("shape") == "circle")
    assert spheres("water") == 3          # O + 2 H
    assert spheres("methane") == 5        # C + 4 H
    assert spheres("carbon_dioxide") == 3
    assert spheres("benzene") == 12       # 6 C + 6 H
    assert spheres("bcc") == 9            # 8 corners + centre
    assert spheres("fcc") == 14           # 8 corners + 6 faces
    assert spheres("nacl") == 27          # 3x3x3 alternating ions


def test_atom_sphere_uses_sun_gradient():
    (spec,) = molecules.atom_specs(50, 50, 20, "O")
    assert spec["shape"] == "circle"
    assert spec["fill"]["kind"] == "sun"          # lit sphere
    item = ai_assistant._spec_to_item(spec)
    assert item.brush().gradient() is not None     # gradient brush, not solid


def test_bond_orders():
    assert len(molecules.bond_specs((0, 0), (10, 0), order=1)) == 1
    assert len(molecules.bond_specs((0, 0), (10, 0), order=2)) == 2
    assert len(molecules.bond_specs((0, 0), (10, 0), order=3)) == 3
    assert molecules.bond_specs((0, 0), (0, 0)) == []      # zero length


def test_expand_atom_and_bond():
    out = molecules.expand_specs([
        {"shape": "atom", "element": "N", "x": 100, "y": 100, "r": 18},
        {"shape": "bond", "x1": 100, "y1": 100, "x2": 150, "y2": 100,
         "order": 2},
        {"shape": "rect", "x": 0, "y": 0, "w": 10, "h": 10},
    ])
    assert [s["shape"] for s in out] == ["circle", "line", "line", "rect"]
    # atom x,y is treated as the sphere CENTRE
    assert out[0]["x"] == 100 - 18 and out[0]["y"] == 100 - 18


def test_ai_brush_accepts_gradient_dict():
    spec = {"shape": "circle", "x": 0, "y": 0, "w": 40, "h": 40,
            "fill": {"kind": "sun", "c1": "#123456", "c2": "#ffffff"}}
    brush = ai_assistant._brush(spec)
    assert brush.gradient() is not None


def test_place_mol_element_is_grouped_and_undoable(scene):
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    before = len(scene.vector_items())
    scene.place_mol_element("methane", QPointF(300, 240))
    assert len(scene.vector_items()) == before + 1     # one group
    assert fired == [1]                                # exactly one gesture


def test_lit_sphere_round_trips_json_and_svg(scene, tmp_path):
    scene.place_mol_element("water", QPointF(300, 240))
    # JSON snapshot (powers undo)
    data = document.scene_to_dict(scene)
    restored = PaintScene(600, 480)
    document.dict_to_scene(data, restored)
    assert _has_sun_sphere(restored)
    # SVG (the only on-disk native format)
    path = str(tmp_path / "mol.svg")
    svgio.save_svg(scene, path)
    restored2 = PaintScene(600, 480)
    svgio.load_svg(restored2, path)
    assert _has_sun_sphere(restored2)


def test_oriented_projection_changes_with_view():
    front = molecules.build_specs_oriented("methane", 200, 200, az=0.0, el=0.0)
    top = molecules.build_specs_oriented("methane", 200, 200, az=0.0,
                                         el=1.5708)
    # a different viewpoint moves the atoms to different screen positions
    fc = [(s.get("x"), s.get("y")) for s in front if s.get("shape") == "circle"]
    tc = [(s.get("x"), s.get("y")) for s in top if s.get("shape") == "circle"]
    assert fc != tc


def test_default_bond_lengthens_molecules_only():
    assert molecules.default_bond("methane") == molecules.DEFAULT_BOND
    assert molecules.DEFAULT_BOND > 1.0            # longer than raw geometry
    assert molecules.default_bond("bcc") == 1.0    # crystals keep spacing


def test_bond_scale_spreads_atoms():
    tight = molecules.build_specs_oriented("methane", 300, 300, bond=1.0)
    loose = molecules.build_specs_oriented("methane", 300, 300, bond=2.0)

    def spread(specs):
        pts = [(s["x"], s["y"]) for s in specs if s.get("shape") == "circle"]
        xs = [x for x, _ in pts]
        ys = [y for _, y in pts]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    # both are fit to the same box, but looser bonds push the H's out so the
    # spheres shrink relative to the frame — the drawn spheres get smaller
    r_tight = next(s["w"] for s in tight if s.get("shape") == "circle")
    r_loose = next(s["w"] for s in loose if s.get("shape") == "circle")
    assert r_loose < r_tight


def test_model_data_covers_every_model():
    for name in molecules.SIZES:
        atoms, bonds, edges, rscale = molecules.model_data(name)
        assert atoms and rscale > 0


def test_placed_model_is_tagged(scene):
    scene.place_mol_element("bcc", QPointF(300, 240))
    (top,) = scene.selectedItems()
    assert top.mol_name == "bcc"
    assert top.mol_az is not None and top.mol_el is not None


def test_reorient_rebuilds_and_keeps_tag(scene):
    scene.place_mol_element("methane", QPointF(300, 240))
    (top,) = scene.selectedItems()
    before = top.sceneBoundingRect().center()
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    scene.reorient_model(top, az=0.0, el=1.5708)     # top view
    (new,) = scene.selectedItems()
    assert new is not top                             # rebuilt
    assert new.mol_name == "methane"
    assert new.mol_az == 0.0
    assert fired == [1]                               # one undoable gesture
    after = new.sceneBoundingRect().center()
    assert abs(after.x() - before.x()) < 30           # centre preserved
    assert abs(after.y() - before.y()) < 30


def test_model_tag_round_trips_json_and_svg(scene, tmp_path):
    scene.place_mol_element("fcc", QPointF(300, 240))
    data = document.scene_to_dict(scene)
    restored = PaintScene(600, 480)
    document.dict_to_scene(data, restored)
    assert _find_model(restored) == "fcc"
    path = str(tmp_path / "xtal.svg")
    svgio.save_svg(scene, path)
    restored2 = PaintScene(600, 480)
    svgio.load_svg(restored2, path)
    assert _find_model(restored2) == "fcc"


def test_custom_structure_round_trips(scene, tmp_path):
    scene.place_mol_element("methane", QPointF(300, 240))
    (top,) = scene.selectedItems()
    atoms = [["C", 0, 0, 0], ["O", 1.4, 0, 0], ["H", 1.9, 0.7, 0]]
    bonds = [[0, 1, 1], [1, 2, 1]]
    scene._tag_model(top, "custom", 0.4, 0.3, 1.6, atoms, bonds)
    data = document.scene_to_dict(scene)
    restored = PaintScene(600, 480)
    document.dict_to_scene(data, restored)
    grp = next(it for it in restored.items()
               if getattr(it, "mol_name", None) == "custom")
    assert grp.mol_atoms == atoms and grp.mol_bonds == bonds
    assert grp.mol_bond == 1.6
    # SVG too
    path = str(tmp_path / "custom.svg")
    svgio.save_svg(scene, path)
    r2 = PaintScene(600, 480)
    svgio.load_svg(r2, path)
    grp2 = next(it for it in r2.items()
                if getattr(it, "mol_name", None) == "custom")
    assert grp2.mol_atoms == atoms and grp2.mol_bonds == bonds


def test_builder_add_and_delete_atoms():
    atoms, bonds = molecules.single_atom("C")
    for el in ("H", "H", "H", "H"):
        molecules.add_bonded_atom(atoms, bonds, 0, el)
    assert len(atoms) == 5 and len(bonds) == 4     # methane built by hand
    # every H is bonded to the carbon and roughly one bond-length away
    for i, j, _o in bonds:
        assert 0 in (i, j)
    molecules.delete_atom(atoms, bonds, 4)          # drop one H
    assert len(atoms) == 4 and len(bonds) == 3
    assert all(i < 4 and j < 4 for i, j, _o in bonds)   # re-indexed


def test_builder_edits_and_returns_structure(app):
    from khervepaint.molview import MoleculeViewer
    dlg = MoleculeViewer("methane")
    assert dlg.editable
    n0 = len(dlg.atoms)
    dlg.selected = 0
    dlg._add_atom("O")
    assert len(dlg.atoms) == n0 + 1 and dlg.dirty
    atoms, bonds = dlg.result()
    assert atoms is not None and len(atoms) == n0 + 1
    # a crystal is not editable and returns no custom structure
    xtal = MoleculeViewer("bcc")
    assert not xtal.editable
    assert xtal.result() == (None, None)
    dlg.deleteLater(); xtal.deleteLater()


def test_builder_standard_view_and_bond(app):
    from khervepaint.molview import MoleculeViewer, STANDARD_VIEWS
    dlg = MoleculeViewer("ethanol")
    top = next(v for v in STANDARD_VIEWS if v[0] == "Top")
    dlg._set_view(top[2], top[3])
    assert abs(dlg.el - top[3]) < 1e-9 and abs(dlg.az - top[2]) < 1e-9
    dlg._on_bond(210)
    assert abs(dlg.bond - 2.1) < 1e-9
    dlg.deleteLater()


def _find_model(scene):
    for it in scene.items():
        if getattr(it, "mol_name", None):
            return it.mol_name
    return None


def _has_sun_sphere(scene):
    """True if some item (recursing into groups) carries a `sun` gradient."""
    def walk(items):
        for it in items:
            if hasattr(it, "childItems") and it.childItems():
                if walk(it.childItems()):
                    return True
            spec = gradient.brush_spec(it.brush()) if hasattr(it, "brush") \
                else None
            if spec and spec.get("kind") == "sun":
                return True
        return False
    return walk(scene.items())
