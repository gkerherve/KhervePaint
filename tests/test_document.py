"""Round-trip and behaviour tests for the .kpaint document layer.

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
from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import QApplication

from khervepaint import document
from khervepaint.canvas import (EllipseItem, GroupItem, LineItem, PaintScene,
                                RectItem, TextItem)


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(400, 300)


def _populated(scene):
    line = LineItem(QLineF(0, 0, 100, 50))
    line.setPen(QPen(QColor("#ff0000"), 3))
    scene.addItem(line)

    rect = RectItem(QRectF(10, 10, 80, 40))
    rect.setPen(QPen(QColor("#00ff00"), 2))
    rect.setBrush(QBrush(QColor("#0000ff")))
    rect.setPos(20, 30)
    scene.addItem(rect)

    ellipse = EllipseItem(QRectF(0, 0, 60, 60))
    ellipse.setPen(QPen(QColor("#112233"), 1))
    scene.addItem(ellipse)

    text = TextItem("hello")
    text.setDefaultTextColor(QColor("#aa00aa"))
    text.setPos(40, 40)
    scene.addItem(text)
    return scene


def test_roundtrip_items(scene, tmp_path):
    _populated(scene)
    path = tmp_path / "doc.kpaint"
    document.save_kpaint(scene, str(path))

    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))

    items = other.vector_items()
    assert len(items) == 4
    line = next(i for i in items if isinstance(i, LineItem))
    assert line.line() == QLineF(0, 0, 100, 50)
    assert line.pen().color().name() == "#ff0000"

    rect = next(i for i in items if isinstance(i, RectItem))
    assert rect.rect() == QRectF(10, 10, 80, 40)
    assert rect.pos() == QPointF(20, 30)
    assert rect.brush().color().name() == "#0000ff"

    text = next(i for i in items if isinstance(i, TextItem))
    assert text.toPlainText() == "hello"
    assert text.defaultTextColor().name() == "#aa00aa"

    assert other.sceneRect().width() == 400
    assert other.sceneRect().height() == 300


def test_roundtrip_grid_settings(scene, tmp_path):
    scene.grid_size = 35
    scene.show_grid = False
    scene.snap_enabled = False
    path = tmp_path / "grid.kpaint"
    document.save_kpaint(scene, str(path))

    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    assert other.grid_size == 35
    assert other.show_grid is False
    assert other.snap_enabled is False


def test_roundtrip_group(scene, tmp_path):
    _populated(scene)
    for item in scene.vector_items():
        item.setSelected(True)
    scene.group_selection()
    assert len(scene.vector_items()) == 1
    assert isinstance(scene.vector_items()[0], GroupItem)

    path = tmp_path / "group.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))

    groups = other.vector_items()
    assert len(groups) == 1
    assert isinstance(groups[0], GroupItem)
    assert len(groups[0].childItems()) == 4


def test_ungroup_restores_items(scene):
    _populated(scene)
    for item in scene.vector_items():
        item.setSelected(True)
    scene.group_selection()
    scene.vector_items()[0].setSelected(True)
    scene.ungroup_selection()
    assert len(scene.vector_items()) == 4


def test_snap(scene):
    scene.grid_size = 20
    assert scene.snap(QPointF(27, 51)) == QPointF(20, 60)
    assert scene.snap(QPointF(-9, 10)) == QPointF(0, 20)


def test_png_roundtrip(scene, tmp_path):
    _populated(scene)
    out = tmp_path / "flat.png"
    document.export_png(scene, str(out))
    assert out.exists()

    other = PaintScene(10, 10)
    document.open_png(other, str(out))
    assert other.sceneRect().width() == 400
    assert other.sceneRect().height() == 300
    assert other.vector_items() == []


def test_pencil_paints_raster(scene):
    before = scene.raster_item.pixmap().toImage()
    scene.pen = QPen(QColor("#000000"), 5)
    scene._paint_raster(QPointF(10, 10), QPointF(100, 100))
    after = scene.raster_item.pixmap().toImage()
    assert before != after
    assert after.pixelColor(55, 55).name() == "#000000"
