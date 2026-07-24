"""Lattice-system unit cells, vector-based supercell stacking, custom atom
colours and the colour legend (JSON snapshot + SVG round-trips).

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
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QApplication

from khervepaint import (ai_assistant, document, lattices, molcolor,
                         molecules, svgio)
from khervepaint.canvas import PaintScene


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(600, 480)


# ------------------------------------------------------------ lattice cells
def test_lattice_systems_are_registered():
    for name in lattices.PARAMS:
        assert name in molecules._MODELS
        assert name in molecules.LABELS and name in molecules.SIZES
        assert molecules.is_crystal(name)          # _xtal_* builder name
        assert molecules.can_stack(name)           # tiles by lattice vectors
    cat = dict(molecules.CATEGORIES)
    assert set(cat["Lattice systems"]) == set(lattices.PARAMS)


def test_lattice_cells_build_to_items(app):
    for name in lattices.PARAMS:
        w, h = molecules.size_mm(name)
        specs = molecules.build_specs(name, w * 3, h * 3)
        assert specs, name
        assert all(ai_assistant._spec_to_item(s) is not None for s in specs)
        # 8 corner atoms, 12 wireframe edges
        atoms, bonds, edges, _r = molecules.model_data(name)
        assert len(atoms) == 8 and len(edges) == 12 and not bonds


def test_lattice_vectors_follow_the_angles():
    va, vb, vc = lattices.lattice_vectors(2.0, 2.0, 3.0, 90, 90, 120)
    assert va == (2.0, 0.0, 0.0)
    assert vb[0] == pytest.approx(-1.0) and vb[1] == pytest.approx(math.sqrt(3))
    assert vc == pytest.approx((0.0, 0.0, 3.0))
    # every vector keeps its requested length
    for v, l in zip(lattices.lattice_vectors(2.2, 2.8, 3.2, 80, 70, 85),
                    (2.2, 2.8, 3.2)):
        assert math.sqrt(sum(x * x for x in v)) == pytest.approx(l)


def test_supercell_tiles_along_lattice_vectors():
    # 2 hexagonal cells share one face: 8 + 8 - 4 shared corners = 12
    a2, _b, e2, _r = molecules.model_data("hexagonal", (2, 1, 1))
    assert len(a2) == 12
    # monoclinic β=70°: stacking along c shifts the next cell in x too —
    # the tiled cell is skewed, not an orthogonal pile
    a1, _, _, _ = molecules.model_data("monoclinic")
    az2, _, _, _ = molecules.model_data("monoclinic", (1, 1, 2))
    _va, _vb, vc = lattices.LATTICE_VECTORS["monoclinic"]
    assert vc[0] > 0.1                              # skewed c vector
    max_x1 = max(a[1] for a in a1)
    assert max(a[1] for a in az2) == pytest.approx(max_x1 + vc[0])


def test_cubic_stacking_still_orthogonal():
    a2, _, _, _ = molecules.model_data("simple_cubic", (2, 2, 2))
    assert len(a2) == 27                            # unchanged behaviour


# ----------------------------------------------------------- per-cell tilts
def test_rotation_function():
    rot = lattices.rotation(0, 0, 90)
    assert rot((1, 0, 0)) == pytest.approx((0, 1, 0), abs=1e-9)
    rot = lattices.rotation(90, 0, 0)
    assert rot((0, 1, 0)) == pytest.approx((0, 0, 1), abs=1e-9)
    # rotations preserve length
    p = lattices.rotation(30, 40, 50)((1.0, 2.0, 3.0))
    assert math.sqrt(sum(x * x for x in p)) == pytest.approx(math.sqrt(14))


def test_supercell_owners_track_home_cells():
    owners = []
    atoms, _b, _e, _r = molecules.model_data("simple_cubic", (2, 1, 1),
                                             owners=owners)
    assert len(owners) == len(atoms) == 12
    assert owners[0] == "0,0,0" and "1,0,0" in owners
    # single cell: every atom belongs to cell 0,0,0
    owners = []
    molecules.model_data("bcc", owners=owners)
    assert set(owners) == {"0,0,0"}


def test_tilted_cell_detaches_from_its_neighbours():
    base, _, be, _ = molecules.model_data("simple_cubic", (2, 1, 1))
    tilted, _, te, _ = molecules.model_data(
        "simple_cubic", (2, 1, 1), tilts={"1,0,0": [0, 0, 30]})
    # the shared face un-merges: 12 shared atoms become 8 + 8
    assert len(base) == 12 and len(tilted) == 16
    assert len(te) > len(be)                    # shared edges split too
    # a zero tilt changes nothing
    same, _, _, _ = molecules.model_data(
        "simple_cubic", (2, 1, 1), tilts={"1,0,0": [0, 0, 0]})
    assert len(same) == 12


def test_tilt_rotates_about_the_cell_centre():
    # tilting must not translate the cell: its centroid stays put
    def centroid(atoms, owners, cell):
        pts = [(a[1], a[2], a[3]) for a, o in zip(atoms, owners) if o == cell]
        n = len(pts)
        return tuple(sum(p[d] for p in pts) / n for d in range(3))
    o1, o2 = [], []
    a1, _, _, _ = molecules.model_data("simple_cubic", (2, 1, 1), owners=o1,
                                       tilts={"1,0,0": [0, 0, 1]})
    a2, _, _, _ = molecules.model_data("simple_cubic", (2, 1, 1), owners=o2,
                                       tilts={"1,0,0": [25, 15, 40]})
    assert centroid(a1, o1, "1,0,0") == pytest.approx(
        centroid(a2, o2, "1,0,0"), abs=1e-6)


def test_tilting_one_cell_leaves_neighbours_untouched():
    # The user-visible guarantee: tilt cell (1,0,0) and every atom of cell
    # (0,0,0) keeps its exact drawn position AND size. (Regression: the
    # fit-to-box followed the tilted cell's protruding corners, so tilting
    # one cell rescaled and shifted all the others.)
    def cell0_spheres(specs):
        # cell (0,0,0) is tiled first, so its 8 corners are atoms 0..7
        return {s["_atom"]: (round(s["x"], 3), round(s["y"], 3),
                             round(s["w"], 3))
                for s in specs if s.get("shape") == "circle"
                and s.get("_atom", 99) < 8}
    plain = molecules.build_specs_oriented(
        "simple_cubic", 300, 300, cells=(2, 1, 1), tag_atoms=True)
    tilted = molecules.build_specs_oriented(
        "simple_cubic", 300, 300, cells=(2, 1, 1), tag_atoms=True,
        tilts={"1,0,0": [20, 10, 30]})
    assert cell0_spheres(plain) == cell0_spheres(tilted)
    # …while the tilted cell itself really did move
    others = lambda specs: {s["_atom"]: (round(s["x"], 2), round(s["y"], 2))
                            for s in specs if s.get("shape") == "circle"
                            and s.get("_atom", 0) >= 8}
    assert others(plain) != others(tilted)


def test_tilts_round_trip_json_and_svg(scene, tmp_path):
    scene.place_mol_element("simple_cubic", QPointF(300, 240))
    (top,) = scene.selectedItems()
    tilts = {"1,0,0": [10, 0, 25]}
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    new = scene.reorient_model(top, top.mol_az, top.mol_el,
                               cells=(2, 1, 1), tilts=tilts)
    assert new.mol_tilts == tilts and fired == [1]     # one undoable gesture
    data = document.scene_to_dict(scene)
    restored = PaintScene(600, 480)
    document.dict_to_scene(data, restored)
    g = next(i for i in restored.items() if getattr(i, "mol_name", None))
    assert g.mol_tilts == tilts
    path = str(tmp_path / "tilts.svg")
    svgio.save_svg(scene, path)
    r2 = PaintScene(600, 480)
    svgio.load_svg(r2, path)
    g2 = next(i for i in r2.items() if getattr(i, "mol_name", None))
    assert g2.mol_tilts == tilts


def test_reorient_drops_out_of_range_and_zero_tilts(scene):
    scene.place_mol_element("bcc", QPointF(300, 240))
    (top,) = scene.selectedItems()
    new = scene.reorient_model(top, top.mol_az, top.mol_el, cells=(2, 1, 1),
                               tilts={"1,0,0": [15, 0, 0],
                                      "5,0,0": [5, 0, 0],     # outside
                                      "0,0,0": [0, 0, 0]})    # no rotation
    assert new.mol_tilts == {"1,0,0": [15, 0, 0]}
    # shrinking back to a single cell clears the tilts entirely
    single = scene.set_cells(new, 1, 1, 1)
    assert single.mol_cells is None and single.mol_tilts is None


def test_builder_supercell_and_tilt_controls(app):
    from khervepaint.molview import MoleculeViewer
    dlg = MoleculeViewer("simple_cubic", cells=(2, 1, 1))
    assert hasattr(dlg, "cell_spins") and hasattr(dlg, "tilt_spins")
    dlg.preview.rebuild()
    assert len(dlg._owners) == len(dlg.atoms) == 12
    # pick an atom of the second cell, then tilt that cell via the spins
    dlg._on_atom_clicked(dlg._owners.index("1,0,0"))
    dlg.tilt_spins[2].setValue(30)                    # fires _on_tilt
    assert dlg.tilts == {"1,0,0": [0, 0, 30]}
    assert len(dlg.atoms) == 16                       # cell detached
    # the selection follows the cell through the renumbering
    assert dlg.selected is not None
    assert dlg._owners[dlg.selected] == "1,0,0"
    dlg._reset_tilts()
    assert dlg.tilts == {} and len(dlg.atoms) == 12
    # growing the supercell drops tilts that fall outside
    dlg.tilts = {"1,0,0": [5, 0, 0]}
    dlg.cell_spins[0].setValue(1)                     # 1×1×1 again
    assert dlg.tilts == {}
    # crystals stay non-editable: no structure handed back
    assert dlg.result() == (None, None)
    dlg.deleteLater()


def test_large_supercells_allowed(app):
    # counts above the old 6-per-axis cap tile correctly…
    a, _b, _e, _r = molecules.model_data("simple_cubic", (10, 10, 1))
    assert len(a) == 11 * 11 * 2
    # …and both spinner UIs accept them
    from khervepaint.molview import MoleculeViewer
    dlg = MoleculeViewer("simple_cubic")
    assert all(sp.maximum() >= 30 for sp in dlg.cell_spins)
    dlg.deleteLater()


def test_builder_hands_cells_and_tilts_to_canvas(app):
    from khervepaint.molview import MoleculeViewer
    dlg = MoleculeViewer("nacl", cells=(2, 2, 1),
                         tilts={"1,1,0": [0, 10, 0]})
    assert dlg.cells == (2, 2, 1)
    assert dlg.tilts == {"1,1,0": [0, 10, 0]}
    assert [sp.value() for sp in dlg.cell_spins] == [2, 2, 1]
    dlg.deleteLater()


# ------------------------------------------------------------- atom colours
def test_color_key_separates_lattice_sites():
    corner = ("Fe", 0, 0, 0)
    centre = ("Fe", 1, 1, 1, molecules.SITE_COLORS["body"])
    assert molcolor.color_key(corner) == "Fe"
    assert molcolor.color_key(centre) != "Fe"
    colors = {molcolor.color_key(centre): "#ff00ff"}
    out = molcolor.apply_colors([corner, centre], colors)
    assert len(out[0]) == 4                         # corner untouched
    assert out[1][4] == "#ff00ff"                   # centre recoloured
    assert molcolor.atom_color(out[0]) == molecules.ATOM_COLORS["Fe"]


def test_colored_specs_change_with_override():
    plain = molecules.build_specs_oriented("bcc", 200, 200)
    tinted = molecules.build_specs_oriented("bcc", 200, 200,
                                            colors={"Fe": "#00ff00"})
    fills = lambda specs: {s["fill"]["c1"] for s in specs
                           if s.get("shape") == "circle"}
    assert fills(plain) != fills(tinted)


def test_builder_recolors_crystal_and_molecule(app):
    from khervepaint.molview import MoleculeViewer
    # crystal: atoms are loaded (for hit-testing) but stay non-editable
    xtal = MoleculeViewer("bcc")
    assert not xtal.editable and len(xtal.atoms) == 9
    specs = xtal.render_specs(200, 200)
    assert any("_atom" in s for s in specs)         # spheres are clickable
    centre = next(i for i, a in enumerate(xtal.atoms) if len(a) > 4)
    xtal.colors[molcolor.color_key(xtal.atoms[centre])] = "#123456"
    tinted = xtal.render_specs(200, 200)
    assert {s["fill"]["c1"] for s in specs if s.get("shape") == "circle"} != \
        {s["fill"]["c1"] for s in tinted if s.get("shape") == "circle"}
    # molecule: the colour rides on the atom itself and marks it dirty
    mol = MoleculeViewer("methane")
    mol.selected = 0
    mol.atoms[0].append("#ff8800")
    mol.dirty = True
    (sphere,) = [s for s in mol.render_specs(200, 200)
                 if s.get("_atom") == 0]
    assert sphere["fill"]["c1"] != \
        molecules.atom_specs(0, 0, 10, "C")[0]["fill"]["c1"]
    mol._reset_colors()
    assert all(len(a) == 4 for a in mol.atoms)
    xtal.deleteLater(); mol.deleteLater()


def test_model_colors_round_trip_json_and_svg(scene, tmp_path):
    scene.place_mol_element("bcc", QPointF(300, 240))
    (top,) = scene.selectedItems()
    colors = {"Fe": "#22aa66"}
    new = scene.reorient_model(top, top.mol_az, top.mol_el, colors=colors)
    assert new.mol_colors == colors
    data = document.scene_to_dict(scene)
    restored = PaintScene(600, 480)
    document.dict_to_scene(data, restored)
    g = next(i for i in restored.items() if getattr(i, "mol_name", None))
    assert g.mol_colors == colors
    path = str(tmp_path / "colors.svg")
    svgio.save_svg(scene, path)
    r2 = PaintScene(600, 480)
    svgio.load_svg(r2, path)
    g2 = next(i for i in r2.items() if getattr(i, "mol_name", None))
    assert g2.mol_colors == colors


def test_reorient_keeps_colors_by_default(scene):
    scene.place_mol_element("fcc", QPointF(300, 240))
    (top,) = scene.selectedItems()
    top.mol_colors = {"Al": "#dd0044"}
    new = scene.reorient_model(top, 0.3, 0.2)       # plain rotation
    assert new.mol_colors == {"Al": "#dd0044"}


# ---------------------------------------------------- coordination polyhedra
def test_hull_faces_for_octahedron_tetrahedron_cube():
    octa = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1),
            (0, 0, -1)]
    faces = lattices.coordination_faces(octa)
    assert len(faces) == 8 and all(len(f) == 3 for f in faces)
    tetra = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
    faces = lattices.coordination_faces(tetra)
    assert len(faces) == 4 and all(len(f) == 3 for f in faces)
    cube = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
    faces = lattices.coordination_faces(cube)
    assert len(faces) == 6 and all(len(f) == 4 for f in faces)


def test_has_polyhedra_gates_to_bonded_crystals():
    assert molecules.has_polyhedra("perovskite")      # BX6 octahedron
    assert molecules.has_polyhedra("diamond")         # tetrahedra
    assert not molecules.has_polyhedra("nacl")        # no bonds
    assert not molecules.has_polyhedra("simple_cubic")
    assert not molecules.has_polyhedra("water")       # not a crystal


def test_polyhedra_specs_are_translucent_and_tiled():
    plain = molecules.build_specs_oriented("perovskite", 300, 300)
    poly = molecules.build_specs_oriented("perovskite", 300, 300, poly=True)
    faces = [s for s in poly if s.get("shape") == "polygon"]
    assert not [s for s in plain if s.get("shape") == "polygon"]
    assert len(faces) == 8                            # one octahedron
    assert all(0 < s["opacity"] < 1 for s in faces)
    assert all(len(s["points"]) == 3 for s in faces)  # triangles
    # faces interleave with the spheres (not all first or all last)
    kinds = [s["shape"] for s in poly]
    first_face = kinds.index("polygon")
    assert "circle" in kinds[:first_face] or first_face == 0
    assert "circle" in kinds[first_face:]
    # a supercell tiles one octahedron per cell
    stacked = molecules.build_specs_oriented("perovskite", 300, 300,
                                             cells=(2, 1, 1), poly=True)
    assert len([s for s in stacked
                if s.get("shape") == "polygon"]) == 16


def test_polyhedra_follow_atom_recolour():
    teal = molecules.build_specs_oriented("perovskite", 300, 300, poly=True,
                                          colors={"Ti": "#008b8b"})
    faces = [s for s in teal if s.get("shape") == "polygon"]
    assert all(s["fill"] == "#008b8b" for s in faces)


def test_polyhedra_round_trip_and_builder(scene, tmp_path, app):
    scene.place_mol_element("perovskite", QPointF(300, 240))
    (top,) = scene.selectedItems()
    new = scene.reorient_model(top, top.mol_az, top.mol_el, poly=True)
    assert new.mol_poly
    spun = scene.reorient_model(new, 0.4, 0.3)        # rotation keeps it
    assert spun.mol_poly
    data = document.scene_to_dict(scene)
    restored = PaintScene(600, 480)
    document.dict_to_scene(data, restored)
    g = next(i for i in restored.items() if getattr(i, "mol_name", None))
    assert g.mol_poly
    path = str(tmp_path / "poly.svg")
    svgio.save_svg(scene, path)
    r2 = PaintScene(600, 480)
    svgio.load_svg(r2, path)
    g2 = next(i for i in r2.items() if getattr(i, "mol_name", None))
    assert g2.mol_poly
    # builder: checkbox present, enabled only when the model has polyhedra
    from khervepaint.molview import MoleculeViewer
    dlg = MoleculeViewer("perovskite", poly=True)
    assert dlg.poly_check.isChecked() and dlg.poly_check.isEnabled()
    nacl = MoleculeViewer("nacl")
    assert not nacl.poly_check.isEnabled()
    dlg.deleteLater(); nacl.deleteLater()


# ------------------------------------------------------------ colour legend
def test_legend_entries_cover_sites_and_overrides():
    atoms, _b, _e, _r = molecules.model_data("bcc")
    entries = molcolor.legend_entries(atoms)
    assert len(entries) == 2                        # corner Fe + body centre
    labels = [label for _el, label, _c in entries]
    assert any("Iron" in l for l in labels)
    assert any("body centre" in l for l in labels)
    # an override collapses the site wording and recolours the swatch
    over = molcolor.legend_entries(
        atoms, {molcolor.color_key(atoms[-1]): "#101010"})
    assert ("#101010" in [c for _el, _l, c in over])
    assert not any("body centre" in l for _el, l, _c in over)


def test_place_legend_is_grouped_and_undoable(scene):
    scene.place_mol_element("nacl", QPointF(200, 240))
    (top,) = scene.selectedItems()
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    legend = molcolor.place_legend(scene, top)
    assert legend is not None and fired == [1]
    assert legend.sceneBoundingRect().left() > \
        top.sceneBoundingRect().center().x()        # sits to the right
    # a legend is plain editable items, not another 3D model
    assert not getattr(legend, "mol_name", None)
    texts = [c for c in legend.childItems()
             if c.__class__.__name__ == "TextItem"]
    assert len(texts) == 2                          # Na + Cl rows
