"""Shift/Ctrl+click multi-select tests (offscreen Qt, real mouse events).

Run with: python -m pytest tests/  (offscreen Qt).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License or (at your
option) any later version.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from khervescribe.canvas import (GroupItem, LineItem, PaintScene, PaintView,
                                 RectItem)


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def setup(app):
    scene = PaintScene(400, 300)
    view = PaintView(scene)
    view.resize(500, 400)
    view.show()
    r1 = RectItem(QRectF(20, 20, 80, 60))
    r2 = RectItem(QRectF(200, 100, 80, 60))
    # filled, so their interiors are clickable (unfilled shapes are
    # picked by their outline only — see OutlinePickMixin)
    r1.setBrush(QColor("#cc4444"))
    r2.setBrush(QColor("#44cc44"))
    scene.addItem(r1)
    scene.addItem(r2)
    return scene, view, r1, r2


def _click(app, view, x, y, mod=Qt.NoModifier):
    QTest.mouseClick(view.viewport(), Qt.LeftButton, mod,
                     view.mapFromScene(x, y))
    app.processEvents()


def test_shift_click_adds_and_removes(setup, app):
    scene, view, r1, r2 = setup
    _click(app, view, 60, 50)
    _click(app, view, 240, 130, Qt.ShiftModifier)
    assert r1.isSelected() and r2.isSelected()
    _click(app, view, 60, 50, Qt.ShiftModifier)      # toggle r1 back off
    assert not r1.isSelected() and r2.isSelected()


def test_ctrl_click_adds(setup, app):
    scene, view, r1, r2 = setup
    _click(app, view, 60, 50)
    _click(app, view, 240, 130, Qt.ControlModifier)
    assert r1.isSelected() and r2.isSelected()


def test_modifier_click_survives_jitter(setup, app):
    """Press and release a few pixels apart (a real-world 'click') must
    still toggle, and must not nudge any item — Qt's native Ctrl toggle
    failed both."""
    scene, view, r1, r2 = setup
    _click(app, view, 60, 50)
    p2_before = r2.pos()
    vp = view.viewport()
    QTest.mousePress(vp, Qt.LeftButton, Qt.ShiftModifier,
                     view.mapFromScene(240, 130))
    QTest.mouseMove(vp, view.mapFromScene(243, 132))
    QTest.mouseRelease(vp, Qt.LeftButton, Qt.ShiftModifier,
                       view.mapFromScene(243, 132))
    app.processEvents()
    assert r1.isSelected() and r2.isSelected()
    assert r2.pos() == p2_before


def test_modifier_click_on_group_child_toggles_group(setup, app):
    scene, view, r1, r2 = setup
    child = LineItem(QLineF(300, 200, 360, 260))
    scene.addItem(child)
    group = GroupItem()
    scene.addItem(group)
    group.addToGroup(child)
    _click(app, view, 60, 50)
    _click(app, view, 330, 230, Qt.ShiftModifier)     # on the child line
    assert r1.isSelected() and group.isSelected()
    # the group is what got toggled, not the child inside it
    assert group in scene.selectedItems()
    assert child not in scene.selectedItems()


def test_modifier_click_on_empty_space_keeps_selection(setup, app):
    """A Shift/Ctrl+click that misses (lands on empty canvas) must not
    throw away the selection being built."""
    scene, view, r1, r2 = setup
    _click(app, view, 60, 50)
    _click(app, view, 240, 130, Qt.ShiftModifier)
    _click(app, view, 380, 20, Qt.ShiftModifier)      # empty corner
    assert r1.isSelected() and r2.isSelected()


def test_plain_click_still_replaces(setup, app):
    scene, view, r1, r2 = setup
    _click(app, view, 60, 50)
    _click(app, view, 240, 130)                       # no modifier
    assert not r1.isSelected() and r2.isSelected()
