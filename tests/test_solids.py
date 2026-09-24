"""3D solids palette: meshes, projection, rotation, persistence, MCP.

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

from khervepaint import ai_assistant, document, mcp_schema, solids, svgio
from khervepaint.canvas import GroupItem, PaintScene


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(600, 480)


def _solids(scene):
    return [it for it in scene.items()
            if it.parentItem() is None and getattr(it, "solid", None)]


def test_registry_is_consistent():
    names = set(solids._MESHES)
    assert names == set(solids.LABELS) == set(solids.SIZES)
    listed = [n for _t, ns in solids.CATEGORIES for n in ns]
    assert set(listed) == names and len(listed) == len(names)
    assert set(mcp_schema.SOLID_NAMES) == names


@pytest.mark.parametrize("name", sorted(solids._MESHES))
def test_every_solid_draws_several_visible_faces(app, name):
    specs = solids.solid_specs(name, 200, 200)
    assert len(specs) >= (1 if name == "sphere" else 2), name
    for s in specs:
        pts = s.get("points") or [[s["x"], s["y"]],
                                  [s["x"] + s["w"], s["y"] + s["h"]]]
        for x, y in pts:
            assert -1 <= x <= 201 and -1 <= y <= 201, name  # fits the box
    assert all(ai_assistant._spec_to_item(s) is not None for s in specs)


def test_closed_meshes_have_outward_faces():
    """A convex solid seen from any angle shows roughly half its faces —
    inward-wound faces would make it vanish or show everything."""
    for name in ("cube", "octahedron", "icosahedron", "dodecahedron"):
        total = len(solids._MESHES[name]()[1])
        seen = len(solids.solid_specs(name, 100, 100, 0.7, 0.4))
        assert 0 < seen < total, name


def test_view_changes_the_drawing():
    a = solids.solid_specs("cube", 100, 100, 0.2, 0.3)
    b = solids.solid_specs("cube", 100, 100, 1.1, 0.3)
    assert [s["points"] for s in a] != [s["points"] for s in b]


def test_faces_are_shaded_differently():
    fills = {s["fill"] for s in solids.solid_specs("cube", 100, 100)}
    assert len(fills) == 3                     # top / front / side


def test_resolve_name_and_color():
    assert solids.resolve_name("Hexagonal prism") == "hex_prism"
    assert solids.resolve_name("donut") == "torus"
    assert solids.resolve_name("teapot") is None
    assert solids.resolve_color("red") == solids.COLORS["red"]
    assert solids.resolve_color("#123456") == "#123456"


def test_place_is_tagged_and_undoable(scene):
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    item = scene.place_solid_element("torus", QPointF(300, 240))
    assert isinstance(item, GroupItem) and item.solid["name"] == "torus"
    assert fired == [1]


def test_reorient_keeps_mesh_centre(scene):
    item = solids.place_solid(scene, "cone", QPointF(300, 240))
    tag = dict(item.solid)
    for step in range(12):                     # a long orbit drag
        item = solids.reorient_solid(scene, item, tag["az"] + step * 0.3,
                                     tag["el"] + step * 0.05, commit=False)
    back = solids.reorient_solid(scene, item, tag["az"], tag["el"],
                                 commit=False)
    c = back.sceneBoundingRect().center()
    fresh = PaintScene(600, 480)
    first = solids.place_solid(fresh, "cone",
                               QPointF(300, 240)).sceneBoundingRect().center()
    assert abs(c.x() - first.x()) < 1.5 and abs(c.y() - first.y()) < 1.5
    assert len(_solids(scene)) == 1


def test_orbit_mode_spins_a_solid(scene):
    item = solids.place_solid(scene, "cube", QPointF(300, 240))
    assert scene.enter_orbit_mode(item)
    scene._orbit_last = QPointF(300, 240)
    scene._orbit_drag(QPointF(340, 250))
    spun = scene._orbit_item
    assert spun is not item and spun.solid["az"] > item.solid["az"]
    fired = []
    scene.changed_by_user.connect(lambda: fired.append(1))
    scene._exit_orbit()
    assert fired == [1]                        # one undo step per session


def test_round_trips_json_and_svg(scene, tmp_path):
    solids.place_solid(scene, "cylinder", QPointF(300, 240), "red",
                       0.5, 0.4, size=150)
    restored = PaintScene(600, 480)
    document.dict_to_scene(document.scene_to_dict(scene), restored)
    (a,) = _solids(restored)
    assert a.solid["name"] == "cylinder" and a.solid["box"] == 150
    assert a.solid["color"] == solids.COLORS["red"]
    path = str(tmp_path / "solid.svg")
    svgio.save_svg(scene, path)
    restored2 = PaintScene(600, 480)
    svgio.load_svg(restored2, path)
    (b,) = _solids(restored2)
    assert b.solid["az"] == pytest.approx(0.5)
    # still rotatable after reload
    assert solids.reorient_solid(restored2, b, 1.0, 0.2) is not None


def test_ai_solid_spec(scene):
    created = ai_assistant.apply_specs(scene, [
        {"shape": "solid", "name": "sphere", "x": 200, "y": 200,
         "size": 80, "color": "gold"},
        {"shape": "rect", "x": 10, "y": 10, "w": 20, "h": 20}])
    assert any(getattr(c, "solid", None) for c in created)
