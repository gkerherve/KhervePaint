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
