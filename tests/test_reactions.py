"""Reaction schemes (parse, balance, lay out, place, persist) and the
2D depictions they are drawn with.

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

from khervepaint import (ai_assistant, document, mcp_schema, molecules,
                         molrepr, reaction, reactionview, svgio)
from khervepaint.canvas import GroupItem, PaintScene
from khervepaint.mcp_tools import McpToolExecutor


@pytest.fixture
def scene(qapp):
    return PaintScene(975, 1200)


def _coefs(rxn):
    return [int(reaction.coef_value(sp))
            for sp in rxn["reactants"] + rxn["products"]]


# ── formulas ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("text, counts, charge", [
    ("H2O", {"H": 2, "O": 1}, 0),
    ("Ca(OH)2", {"Ca": 1, "O": 2, "H": 2}, 0),
    ("CuSO4·5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}, 0),
    ("CuSO4.5H2O", {"Cu": 1, "S": 1, "O": 9, "H": 10}, 0),
    ("SO4^2-", {"S": 1, "O": 4}, -2),
    ("SO₄²⁻", {"S": 1, "O": 4}, -2),
    ("NH4+", {"N": 1, "H": 4}, 1),
    ("Fe^3+", {"Fe": 1}, 3),
    ("e-", {}, -1),
])
def test_parse_formula(text, counts, charge):
    assert reaction.parse_formula(text) == (counts, charge)


@pytest.mark.parametrize("text", ["ethanol", "Xx2", "(CH3", "2"])
def test_parse_formula_rejects_what_is_not_a_formula(text):
    with pytest.raises(ValueError):
        reaction.parse_formula(text)


def test_pretty_formula_and_conditions():
    assert reaction.pretty_formula("H2SO4") == "H₂SO₄"
    assert reaction.pretty_formula("SO4^2-") == "SO₄²⁻"
    assert reaction.pretty_formula("CuSO4.5H2O") == "CuSO₄·5H₂O"
    assert reaction.pretty_formula("glucose-6-phosphate") == \
        "glucose-6-phosphate"
    assert reaction.pretty_text("H2SO4, 80 °C") == "H₂SO₄, 80 °C"
    assert reaction.pretty_text("hv") == "hν"


@pytest.mark.parametrize("text, expected", [
    ("water", {"name": "water"}), ("H2O", {"name": "water"}),
    ("CH3COOH", {"name": "acetic_acid"}), ("C2H5OH", {"name": "ethanol"}),
    ("O2", {"name": "oxygen"}), ("Fe2O3", {"formula": "Fe2O3"}),
    ("NaCl", {"formula": "NaCl"}),         # a formula, not the crystal cell
])
def test_resolve_species(text, expected):
    assert reaction.resolve_species(text) == expected


# ── equations and balancing ──────────────────────────────────────────

def test_parse_equation_resolves_molecules_and_states():
    rxn = reaction.parse_equation("CH4 + 2 O2 -> CO2 + 2 H2O(g)")
    assert [sp["name"] for sp in rxn["reactants"]] == ["methane", "oxygen"]
    assert [sp["name"] for sp in rxn["products"]] == ["carbon_dioxide",
                                                       "water"]
    assert _coefs(rxn) == [1, 2, 1, 2]
    assert rxn["products"][1]["state"] == "g"
    assert reaction.balance_report(rxn)["balanced"]


def test_arrows_conditions_and_ions():
    rxn = reaction.parse_equation("N2 + 3 H2 <=>[Fe][450 °C] 2 NH3")
    assert rxn["arrow"] == "equilibrium"
    assert (rxn["above"], rxn["below"]) == ("Fe", "450 °C")
    assert reaction.balance_report(rxn)["balanced"]
    assert reaction.parse_equation("phenol => benzene")["arrow"] == "retro"
    ions = reaction.parse_equation("Na+ + Cl- -> NaCl")
    assert [sp["formula"] for sp in ions["reactants"]] == ["Na+", "Cl-"]
    assert reaction.balance_report(ions)["balanced"]
    with pytest.raises(ValueError):
        reaction.parse_equation("H2 + O2")


def test_equation_text_round_trips():
    rxn = reaction.parse_equation(
        "CH3COOH + C2H5OH <=>[H2SO4] CH3COOCH2CH3 + H2O(l)")
    again = reaction.parse_equation(reaction.to_equation(rxn))
    for side in ("reactants", "products"):
        assert [(s.get("name"), s.get("formula"), s["coef"], s["state"])
                for s in again[side]] == \
               [(s.get("name"), s.get("formula"), s["coef"], s["state"])
                for s in rxn[side]]
    assert again["above"] == "H2SO4"


@pytest.mark.parametrize("equation, expected", [
    ("C3H8 + O2 -> CO2 + H2O", [1, 5, 3, 4]),
    ("Fe + O2 -> Fe2O3", [4, 3, 2]),
    ("glucose + O2 -> CO2 + H2O", [1, 6, 6, 6]),
    ("Al + HCl -> AlCl3 + H2", [2, 6, 2, 3]),
    ("MnO4^- + Fe^2+ + H+ -> Mn^2+ + Fe^3+ + H2O", [1, 5, 8, 1, 5, 4]),
])
def test_auto_balance(equation, expected):
    rxn = reaction.parse_equation(equation)
    assert reaction.auto_balance(rxn) is None
    assert _coefs(rxn) == expected
    assert reaction.balance_report(rxn)["balanced"]


def test_unbalanced_equation_says_what_is_off():
    rxn = reaction.parse_equation("H2 + O2 -> H2O")
    report = reaction.balance_report(rxn)
    assert not report["balanced"]
    assert report["diffs"] == {"O": (2, 1)}
    assert "O 2 → 1" in reaction.balance_text(report)


def test_unknown_species_cannot_be_balanced():
    rxn = reaction.parse_equation("substrate + H2O -> product")
    assert reaction.balance_report(rxn)["unknown"]
    assert reaction.auto_balance(rxn)                    # a reason string


def test_fractional_coefficients():
    rxn = reaction.parse_equation("H2 + 1/2 O2 -> H2O")
    assert reaction.balance_report(rxn)["balanced"]
    assert reaction.coef_text(rxn["reactants"][1]) == "½"


# ── layout, placement, persistence ───────────────────────────────────

@pytest.mark.parametrize("style", reaction.STYLES)
def test_every_style_and_arrow_builds_items(qapp, style):
    for arrow in reaction.ARROWS:
        rxn = reaction.parse_equation("ethanol + O2 -> CO2 + H2O(l)")
        rxn.update(style=style, arrow=arrow, above="Pt", below="Δ",
                   labels=True)
        specs, w, h = reaction.reaction_specs(rxn, 30)
        assert w > 0 and h > 0
        assert all(ai_assistant._spec_to_item(s) is not None for s in specs)


def test_place_reaction_is_one_undoable_tagged_group(scene):
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    rxn = reaction.parse_equation("CH4 + 2 O2 -> CO2 + 2 H2O")
    top = reactionview.place_reaction(scene, rxn, QPointF(480, 400))
    assert isinstance(top, GroupItem)
    assert fired == [1]
    assert top.rxn_data["unit"] > 0
    assert top.sceneBoundingRect().width() < scene.sceneRect().width()
    c = top.sceneBoundingRect().center()
    assert abs(c.x() - 480) < 2 and abs(c.y() - 400) < 2


def test_reaction_round_trips_through_snapshot_and_svg(scene, tmp_path):
    rxn = reaction.parse_equation("N2 + 3 H2 <=>[Fe][450 °C] 2 NH3(g)")
    reactionview.place_reaction(scene, rxn, QPointF(480, 400))
    data = document.scene_to_dict(scene)
    restored = PaintScene(975, 1200)
    document.dict_to_scene(data, restored)
    g = next(i for i in restored.items() if getattr(i, "rxn_data", None))
    assert reaction.to_equation(g.rxn_data) == \
        "N2 + 3 H2 <=>[Fe][450 °C] 2 NH3(g)"
    path = str(tmp_path / "rxn.svg")
    svgio.save_svg(scene, path)
    r2 = PaintScene(975, 1200)
    svgio.load_svg(r2, path)
    g2 = next(i for i in r2.items() if getattr(i, "rxn_data", None))
    assert g2.rxn_data["arrow"] == "equilibrium"
    assert g2.rxn_data["below"] == "450 °C"


def test_redraw_replaces_in_place(scene):
    top = reactionview.place_reaction(
        scene, reaction.parse_equation("H2 + O2 -> H2O"), QPointF(400, 300))
    before = top.sceneBoundingRect().center()
    rxn = dict(top.rxn_data)
    assert reaction.auto_balance(rxn) is None
    new = reactionview.place_reaction(scene, rxn, replace=top)
    assert top.scene() is None and new.scene() is scene
    after = new.sceneBoundingRect().center()
    assert abs(after.x() - before.x()) < 2 and abs(after.y() - before.y()) < 2
    assert _coefs(new.rxn_data) == [2, 1, 2]


def test_ai_reaction_spec(scene):
    created = ai_assistant.apply_specs(
        scene, [{"shape": "reaction", "equation": "H2 + O2 -> H2O",
                 "balance": True, "x": 300, "y": 200}])
    assert len(created) == 1 and created[0].rxn_data
    assert _coefs(created[0].rxn_data) == [2, 1, 2]


def test_mcp_draw_reaction(win):
    ex = McpToolExecutor(win)
    r = ex.execute("draw_reaction", {"equation": "C3H8 + O2 -> CO2 + H2O",
                                     "balance": True, "x": 480, "y": 500})
    assert "error" not in r, r.get("error")
    assert r["balanced"] and r["item"]["kind"] == "group"
    assert r["equation"].endswith("-> 3 CO2 + 4 H2O")
    again = ex.execute("draw_reaction", {"id": r["item"]["id"],
                                         "style": "formula"})
    assert "error" not in again, again.get("error")
    groups = [i for i in win.scene.items() if getattr(i, "rxn_data", None)]
    assert len(groups) == 1 and groups[0].rxn_data["style"] == "formula"
    assert "error" in ex.execute("draw_reaction", {"equation": "no arrow"})
    # leave the shared window as the other tests do (clean, nothing
    # selected) — Qt tears it down at exit and a dirty stack or a live
    # selection fires slots into already-deleted objects
    win.scene.clearSelection()
    win._reset_history()


def test_schema_mirrors_the_reaction_module():
    assert mcp_schema.REACTION_STYLES == reaction.STYLES
    assert mcp_schema.REACTION_ARROWS == reaction.ARROWS
    assert mcp_schema.REPR_MODES == molrepr.MODES


# ── 2D depictions ────────────────────────────────────────────────────

@pytest.mark.parametrize("name, condensed", [
    ("ethanol", "CH₃CH₂OH"), ("acetic_acid", "CH₃COOH"),
    ("acetone", "CH₃COCH₃"), ("isopropanol", "CH₃CH(OH)CH₃"),
    ("chloroform", "CHCl₃"), ("water", "H₂O"), ("methane", "CH₄"),
    ("carbon_dioxide", "CO₂"), ("toluene", "C₆H₅CH₃"),
    ("formic_acid", "HCOOH"), ("propene", "CH₃CH=CH₂"),
    ("glucose", "C₆H₁₂O₆"),
])
def test_condensed_formula(name, condensed):
    atoms, bonds = molecules.model_data(name)[:2]
    assert molrepr.condensed_formula(atoms, bonds) == condensed


def test_glucose_model_has_the_right_formula():
    atoms = molecules.model_data("glucose")[0]
    assert molrepr.molecular_formula(atoms) == "C₆H₁₂O₆"


def test_skeletal_leaves_carbons_bare(qapp):
    atoms, bonds = molecules.model_data("ethanol")[:2]
    texts = [s["text"] for s in molrepr.skeletal_specs(atoms, bonds, 200, 200)
             if s["shape"] == "text"]
    assert texts == ["O", "H"]


@pytest.mark.parametrize("name", ["ethanol", "propane", "isopropanol",
                                  "toluene", "glucose", "acetic_acid",
                                  "benzoic_acid", "glycine"])
def test_2d_layout_is_clean(name):
    atoms, bonds = molecules.model_data(name)[:2]
    pos = molrepr.layout_2d(atoms, bonds, explicit_h=True)
    assert len(pos) == len(atoms)
    pts = list(pos.values())
    closest = min(math.dist(p, q) for i, p in enumerate(pts)
                  for q in pts[i + 1:])
    assert closest > 0.5                                  # no overlaps
    for i, j, _o in bonds:                                # uniform bonds
        if atoms[i][0] != "H" and atoms[j][0] != "H":
            assert abs(math.dist(pos[i], pos[j]) - 1.0) < 0.05


@pytest.mark.parametrize("mode", ["skeletal", "structural", "lewis",
                                  "condensed", "formula"])
def test_representation_fits_its_box(qapp, mode):
    for name in ("benzoic_acid", "water", "hexane"):
        atoms, bonds = molecules.model_data(name)[:2]
        specs = molrepr.representation_specs(mode, atoms, bonds, 240, 180)
        x0, y0, x1, y1 = molrepr.specs_bounds(specs)
        assert x0 >= -1 and y0 >= -1 and x1 <= 241 and y1 <= 181
