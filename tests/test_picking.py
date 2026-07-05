"""Click hit-testing: unfilled curves/arcs must not swallow clicks
inside their implicit fill region — a bucket fill behind them stays
clickable (movable, deletable).

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
from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QPainterPath, QPen
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from khervepaint import fill
from khervepaint.canvas import (ArcShapeItem, PaintScene, PaintView,
                                 PathItem, RectItem)


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(400, 300)


def _view(scene):
    view = PaintView(scene)
    view.resize(500, 400)
    view.show()
    return view


def _curve() -> PathItem:
    path = QPainterPath(QPointF(50, 200))
    path.quadTo(QPointF(200, -100), QPointF(350, 200))   # open arch
    item = PathItem(path)
    item.setPen(QPen(QColor("#000000"), 2))
    return item


def test_unfilled_curve_shape_is_stroke_only(scene):
    curve = _curve()
    scene.addItem(curve)
    # A point well inside the arch (its implicit fill region) but far
    # from the stroke must not hit the curve...
    assert not curve.shape().contains(QPointF(200, 150))
    # ...while the stroke itself still does.
    assert curve.shape().contains(QPointF(50, 200))


def test_unfilled_arc_shape_is_stroke_only(scene):
    arc = ArcShapeItem(QRectF(50, 100, 300, 150))        # open 'bowl'
    scene.addItem(arc)
    assert not arc.shape().contains(QPointF(200, 160))   # inside the disc
    # A filled arc is a solid shape and keeps its clickable interior.
    arc.setBrush(QColor("#4aa3ff"))
    assert arc.shape().contains(QPointF(200, 160))


def test_click_selects_fill_behind_curve(scene, app):
    view = _view(scene)
    curve = _curve()
    scene.addItem(curve)
    region = QPainterPath()
    region.addRect(120, 100, 160, 90)                    # under the arch
    blue = PathItem(region)
    blue.setBrush(QColor("#4aa3ff"))
    blue.setPen(QPen(Qt.NoPen))
    blue.setZValue(curve.zValue() - 1)                   # behind the curve
    scene.addItem(blue)

    QTest.mouseClick(view.viewport(), Qt.LeftButton, Qt.NoModifier,
                     view.mapFromScene(200, 150))
    app.processEvents()
    assert blue.isSelected() and not curve.isSelected()


def test_bucket_fill_is_editable_by_default(scene, app):
    assert scene.bucket_vector                           # vector by default
    view = _view(scene)
    box = RectItem(QRectF(100, 80, 150, 120))            # encloses a region
    box.setPen(QPen(QColor("#000000"), 3))
    scene.addItem(box)
    item = fill.bucket_fill(scene, QPointF(170, 140), QColor("#4aa3ff"),
                            vector=scene.bucket_vector)
    assert item is not None
    # The fill is a normal item: selectable by clicking it, movable,
    # deletable.
    scene.clearSelection()
    QTest.mouseClick(view.viewport(), Qt.LeftButton, Qt.NoModifier,
                     view.mapFromScene(170, 140))
    app.processEvents()
    selected = scene.selectedItems()
    assert selected and selected[0] in (item, box)
    # the fill sits behind the box, but the box's unfilled interior is
    # not clickable any more, so the fill itself is what gets picked
    assert selected[0] is item
    scene.delete_selection()
    assert item not in scene.vector_items()
