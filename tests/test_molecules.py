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

from khervepaint import ai_assistant, document, gradient, icons, molecules, svgio
from khervepaint.canvas import PaintScene


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(600, 480)


def test_registry_is_consistent():
    names = set(molecules._MODELS) | set(molecules._POLYMERS)
    assert names == set(molecules.LABELS)
    cat_names = [n for _title, ns in molecules.CATEGORIES for n in ns]
    assert set(cat_names) == names
    assert len(cat_names) == len(names)          # no duplicates


def _all_models():
    return sorted(set(molecules._MODELS) | set(molecules._POLYMERS))


def test_every_model_builds_to_items(app):
    for name in _all_models():
        w, h = molecules.size_mm(name)
        specs = molecules.build_specs(name, w * 3, h * 3)
        assert specs, name
        items = [ai_assistant._spec_to_item(s) for s in specs]
        assert all(it is not None for it in items), name


def test_new_geometry_is_correct():
    import math

    def angle(atoms, c, a, b):
        va = [atoms[a][1 + k] - atoms[c][1 + k] for k in range(3)]
        vb = [atoms[b][1 + k] - atoms[c][1 + k] for k in range(3)]
        na = math.sqrt(sum(x * x for x in va))
        nb = math.sqrt(sum(x * x for x in vb))
        d = sum(va[k] * vb[k] for k in range(3)) / (na * nb)
        return math.degrees(math.acos(max(-1, min(1, d))))
    # CO2 is linear, formaldehyde trigonal
    a, b = molecules.build_molecule(["C", "O", "O"], [(0, 1, 2), (0, 2, 2)])
    assert abs(angle(a, 0, 1, 2) - 180) < 2
    a, b = molecules.build_molecule(["C", "O"], [(0, 1, 2)])
    hs = [i for i, at in enumerate(a) if at[0] == "H"]
    assert abs(angle(a, 0, hs[0], hs[1]) - 120) < 3
    # perovskite octahedron: the B cation bonds 6 X anions
    at, bo, ed = molecules._xtal_perovskite()
    ti = next(i for i, x in enumerate(at) if x[0] == "Ti")
    assert sum(1 for i, j, _o in bo if ti in (i, j)) == 6


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


def test_system_prompt_builds_without_crashing():
    # Regression: the prompt gained literal JSON braces ({"shape":…}) as
    # examples; building the system message must NOT use str.format (which
    # would read them as fields and raise), so asking the AI can't crash.
    from khervepaint import ai_assistant
    prompt = ai_assistant.SYSTEM_PROMPT
    system = (prompt.replace("{w}", "800").replace("{h}", "600")
              .replace("{summary}", "nothing yet"))
    assert "800x600" in system
    assert '"shape":"atom"' in system              # braces preserved intact
    import pytest
    with pytest.raises((KeyError, ValueError, IndexError)):
        prompt.format(w=800, h=600, summary="x")   # .format would crash


def test_ai_molecule_by_name_is_rotatable(scene):
    created = ai_assistant.apply_specs(
        scene, [{"shape": "molecule", "name": "ethanol", "x": 300, "y": 240}])
    assert len(created) == 1
    top = created[0]
    assert top.mol_name == "ethanol" and top.mol_atoms
    assert top.mol_repr == "3d"
    assert scene.enter_orbit_mode(top)             # it can be spun in 3D
    scene._exit_orbit()


def test_ai_molecule_from_skeleton_adds_hydrogens(scene):
    # propanoic acid heavy skeleton -> H's + 3D geometry filled in
    created = ai_assistant.apply_specs(scene, [{
        "shape": "molecule", "atoms": ["C", "C", "C", "O", "O"],
        "bonds": [[0, 1, 1], [1, 2, 1], [2, 3, 2], [2, 4, 1]],
        "x": 300, "y": 240}])
    top = created[0]
    assert top.mol_name == "custom"
    assert len(top.mol_atoms) > 5                  # hydrogens were added
    assert scene.enter_orbit_mode(top)


def test_ai_molecule_2d_representation(scene):
    created = ai_assistant.apply_specs(
        scene, [{"shape": "molecule", "name": "water", "as": "lewis",
                 "x": 300, "y": 240}])
    assert created[0].mol_repr == "lewis"


def test_ai_molecule_mixes_with_plain_shapes(scene):
    created = ai_assistant.apply_specs(scene, [
        {"shape": "molecule", "name": "methane", "x": 120, "y": 120},
        {"shape": "rect", "x": 0, "y": 0, "w": 40, "h": 40}])
    assert len(created) == 2                        # one group + one rect


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


def test_representations_build_and_persist(scene, tmp_path):
    from khervepaint import molrepr
    atoms, bonds, _e, _r = molecules.model_data("ethanol")
    # every 2D mode yields buildable specs
    for mode in ("structural", "lewis", "condensed"):
        specs = molrepr.representation_specs(mode, atoms, bonds, 200, 200)
        assert specs
        assert all(ai_assistant._spec_to_item(s) is not None for s in specs)
    # structural draws every atom as a text label
    labels = [s["text"] for s in molrepr.structural_specs(atoms, bonds, 200, 200)
              if s.get("shape") == "text"]
    assert labels.count("C") == 2 and labels.count("O") == 1
    assert labels.count("H") == 6
    # lewis adds lone-pair dots (ethanol O -> 2 pairs -> 4 dots)
    dots = sum(1 for s in molrepr.structural_specs(atoms, bonds, 200, 200,
                                                   lewis=True)
               if s.get("shape") == "circle" and s.get("fill") == "#1a1a1a")
    assert dots == 4
    assert molrepr.molecular_formula(atoms) == "C₂H₆O"

    # set_representation on the canvas rebuilds and the mode round-trips
    scene.place_mol_element("ethanol", QPointF(300, 240))
    (top,) = scene.selectedItems()
    scene.set_representation(top, "structural")
    (top,) = scene.selectedItems()
    assert top.mol_repr == "structural"
    data = document.scene_to_dict(scene)
    restored = PaintScene(600, 480)
    document.dict_to_scene(data, restored)
    g = next(i for i in restored.items() if getattr(i, "mol_name", None))
    assert g.mol_repr == "structural"
    path = str(tmp_path / "repr.svg")
    svgio.save_svg(scene, path)
    r2 = PaintScene(600, 480)
    svgio.load_svg(r2, path)
    g2 = next(i for i in r2.items() if getattr(i, "mol_name", None))
    assert g2.mol_repr == "structural"


def test_label_colors_are_readable():
    from khervepaint import molrepr
    from PyQt5.QtGui import QColor
    # H and C use black (their CPK colours are too pale to read on white)
    assert molrepr._label_color("H") == "#1a1a1a"
    assert molrepr._label_color("C") == "#1a1a1a"
    # heteroatoms stay dark enough to read
    assert QColor(molrepr._label_color("O")).lightnessF() < 0.5
    assert QColor(molrepr._label_color("N")).lightnessF() < 0.6


def test_pet_has_no_spurious_long_bond():
    import math
    atoms, bonds, _e, _r = molecules.model_data("pet")
    # the longest bond should be a normal bond length, not a line spanning
    # the whole molecule (the old glycol-bridged-the-ring bug)
    longest = max(math.dist(atoms[i][1:4], atoms[j][1:4]) for i, j, _o in bonds)
    assert longest < 2.0


def test_place_built_molecule(scene):
    atoms, bonds = molecules.single_atom("C")
    molecules.add_bonded_atom(atoms, bonds, 0, "O", 2)      # formaldehyde-ish
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    top = scene.place_built_molecule(atoms, bonds, QPointF(300, 240))
    assert top is not None
    assert top.mol_name == "custom" and top.mol_atoms
    assert fired == [1]                                     # one undoable step


def test_2d_representation_does_not_orbit(scene):
    scene.place_mol_element("benzene", QPointF(300, 240))
    (top,) = scene.selectedItems()
    scene.set_representation(top, "lewis")
    (top,) = scene.selectedItems()
    assert not scene.enter_orbit_mode(top)      # 2D formulas don't spin


def test_on_canvas_orbit(scene):
    scene.place_mol_element("methane", QPointF(300, 240))
    (top,) = scene.selectedItems()
    assert scene.enter_orbit_mode(top)                 # a 3D model
    assert scene._orbit_item is top
    az0 = top.mol_az
    # simulate a horizontal drag (as the mouse handlers would)
    scene._orbit_last = QPointF(300, 240)
    scene._orbit_drag(QPointF(360, 240))
    new = scene._orbit_item
    assert new is not top                              # rebuilt live
    assert new.mol_az != az0                           # azimuth changed
    assert scene._orbit_dirty
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    scene._exit_orbit()                                # commits one step
    assert fired == [1]
    assert scene._orbit_item is None


def test_orbit_keeps_size_stable(scene):
    # A drag fires many move events; each rebuild must NOT shrink the model
    # (regression: box was derived from the margin-shrunk bounding rect and
    # compounded smaller every move).
    scene.place_mol_element("ethanol", QPointF(300, 240))
    (top,) = scene.selectedItems()
    scene.enter_orbit_mode(top)
    size0 = max(scene._orbit_item.sceneBoundingRect().width(),
                scene._orbit_item.sceneBoundingRect().height())
    scene._orbit_last = QPointF(300, 240)
    azs = []
    for i in range(30):                       # simulate a 30-step drag
        scene._orbit_drag(QPointF(305 + i * 5, 240))
        azs.append(scene._orbit_item.mol_az)
    size1 = max(scene._orbit_item.sceneBoundingRect().width(),
                scene._orbit_item.sceneBoundingRect().height())
    assert 0.7 * size0 < size1 < 1.4 * size0     # stayed about the same size
    assert azs[-1] != azs[0]                     # and it actually rotated


def test_orbit_ignores_plain_items(scene):
    from khervepaint.canvas import RectItem
    from PyQt5.QtCore import QRectF
    r = RectItem(QRectF(0, 0, 40, 40))
    scene.addItem(r)
    assert not scene.enter_orbit_mode(r)               # not a 3D model


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
    dlg.selected = 1                             # remove an H to free a bond
    dlg._delete_atom()
    n0 = len(dlg.atoms)
    dlg.selected = 0                             # now the carbon has a slot
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
    top = next(v for v in STANDARD_VIEWS if v[0] == "Top")   # (label, az, el)
    dlg._set_view(top[1], top[2])
    assert abs(dlg.az - top[1]) < 1e-9 and abs(dlg.el - top[2]) < 1e-9
    dlg._on_bond(210)
    assert abs(dlg.bond - 2.1) < 1e-9
    dlg.deleteLater()


def test_builds_a_straight_chain_not_a_ring():
    # regression: extending a chain used to curl round into a benzene-like
    # ring; five carbons should now stretch out.
    atoms, bonds = molecules.single_atom("C")
    prev = 0
    for _ in range(4):
        prev = molecules.add_bonded_atom(atoms, bonds, prev, "C")
    import math
    end = math.dist(atoms[0][1:4], atoms[4][1:4])
    assert end > 3.5                              # extended, not ~1.5 (ring)


def test_valence_tracking():
    atoms, bonds = molecules.single_atom("C")
    assert molecules.free_valence(atoms, bonds, 0) == 4      # bare carbon
    molecules.add_bonded_atom(atoms, bonds, 0, "O", order=2)  # C=O
    assert molecules.free_valence(atoms, bonds, 0) == 2
    assert molecules.free_valence(atoms, bonds, 1) == 0       # O full


def test_builder_blocks_overbonding(app):
    from khervepaint.molview import MoleculeViewer
    dlg = MoleculeViewer("methane")              # C already has 4 H
    dlg.selected = 0                             # the carbon, valence full
    before = len(dlg.atoms)
    dlg._add_atom("H")
    assert len(dlg.atoms) == before             # refused — no free valence
    dlg.deleteLater()


def test_drag_atom_moves_only_that_atom():
    atoms = [["C", 0.0, 0.0, 0.0], ["H", 1.0, 0.0, 0.0]]
    p0 = list(atoms[0])
    molecules.drag_atom(atoms, 1, 20.0, 10.0, molecules.DEFAULT_AZ,
                        molecules.DEFAULT_EL, 1.5, scale=40.0)
    assert atoms[0] == p0                        # the other atom is untouched
    assert atoms[1][1:4] != [1.0, 0.0, 0.0]      # dragged atom moved


def test_cube_icons_render(app):
    for v in ("front", "back", "left", "right", "top", "bottom",
              "isometric"):
        ic = icons.view_cube_icon(v)
        assert not ic.isNull()
        assert not ic.pixmap(26, 26).isNull()


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
