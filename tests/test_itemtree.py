"""The Items panel: tree of canvas contents, selection, edit, delete.

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
from PyQt5.QtCore import QPointF, QRectF

from khervepaint import document, itemtree, solids
from khervepaint.canvas import RectItem
from khervepaint.itemtree import COL_NAME, COL_ROT, COL_X, COL_Y


@pytest.fixture
def panel(win):
    dock = win.items_dock
    dock.show()
    yield dock
    dock.hide()


def _rows(panel):
    t = panel.tree
    return [t.topLevelItem(i) for i in range(t.topLevelItemCount())]


def _add_rect(win, x=50, y=60):
    r = RectItem(QRectF(0, 0, 40, 30))
    r.setPos(x, y)
    win.scene.addItem(r)
    win.scene.changed_by_user.emit()
    return r


def test_lists_items_front_first_with_names(win, panel):
    _add_rect(win)
    solids.place_solid(win.scene, "cube", QPointF(300, 200))
    win.scene._place_symbol(__import__("khervepaint.scheme3d",
                                       fromlist=["x"]),
                            "slab_grey", QPointF(200, 400))
    names = [r.text(COL_NAME) for r in _rows(panel)]
    assert names[0].startswith("3D scheme: Slab")      # newest on top
    assert "3D solid: Cube" in names and "Rectangle" in names
    assert panel.count.text() == "3 item(s)"


def test_groups_expand_to_children(win, panel):
    win.scene._place_symbol(__import__("khervepaint.floorplan",
                                       fromlist=["x"]),
                            "double_bed", QPointF(200, 200))
    (row,) = _rows(panel)
    assert row.childCount() > 1


def test_row_selects_item_and_back(win, panel):
    r = _add_rect(win)
    (row,) = _rows(panel)
    row.setSelected(True)
    assert r.isSelected()
    win.scene.clearSelection()
    assert not row.isSelected()
    r.setSelected(True)
    assert _rows(panel)[0].isSelected()


def test_edit_position_and_rotation_is_undoable(win, panel):
    r = _add_rect(win, 50, 60)
    before = document.scene_to_dict(win.scene)
    (row,) = _rows(panel)
    row.setText(COL_X, "120")
    assert r.sceneBoundingRect().x() == pytest.approx(120, abs=0.01)
    (row,) = _rows(panel)
    row.setText(COL_ROT, "30")
    assert r.rotation() == 30
    win._undo_stack.undo()
    win._undo_stack.undo()
    assert document.scene_to_dict(win.scene)["items"] == before["items"]


def test_delete_removes_and_is_undoable(win, panel):
    _add_rect(win)
    solids.place_solid(win.scene, "torus", QPointF(300, 200))
    _rows(panel)[0].setSelected(True)
    panel.delete_selected()
    assert len(win.scene.vector_items()) == 1
    assert [r.text(COL_NAME) for r in _rows(panel)] == ["Rectangle"]
    win._undo_stack.undo()
    assert len(win.scene.vector_items()) == 2


def test_symbol_identity_round_trips(win, tmp_path):
    from khervepaint import svgio, scheme3d
    from khervepaint.canvas import PaintScene
    win.scene._place_symbol(scheme3d, "disk_grey", QPointF(200, 200))
    restored = PaintScene(600, 480)
    document.dict_to_scene(document.scene_to_dict(win.scene), restored)
    assert restored.vector_items()[0].symbol == "scheme3d:disk_grey"
    path = str(tmp_path / "s.svg")
    svgio.save_svg(win.scene, path)
    again = PaintScene(600, 480)
    svgio.load_svg(again, path)
    assert again.vector_items()[0].symbol == "scheme3d:disk_grey"
    assert itemtree.describe(again.vector_items()[0])[0] == \
        "3D scheme: Disk (3D)"
