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
from khervepaint.canvas import (ArrowItem, EllipseItem, GroupItem, ImageItem,
                                LineItem, PaintScene, PathItem, PolygonItem,
                                RectItem, RoundedRectItem, TextItem)


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


def test_roundtrip_new_shapes(scene, tmp_path):
    from PyQt5.QtGui import QPolygonF

    arrow = ArrowItem(QLineF(0, 0, 40, 40))
    arrow.setPen(QPen(QColor("#123456"), 4))
    arrow.setOpacity(0.5)
    scene.addItem(arrow)

    rrect = RoundedRectItem(QRectF(0, 0, 50, 30), radius=8)
    rrect.setPos(10, 10)
    rrect.setBrush(QBrush(QColor("#abcdef")))
    scene.addItem(rrect)

    tri = PolygonItem(
        QPolygonF([QPointF(0, 0), QPointF(20, 0), QPointF(10, 20)]),
        kind="triangle")
    tri.setRotation(30)
    scene.addItem(tri)

    path = tmp_path / "shapes.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))

    items = other.vector_items()
    a = next(i for i in items if isinstance(i, ArrowItem))
    assert a.line() == QLineF(0, 0, 40, 40)
    assert a.pen().color().name() == "#123456"
    assert abs(a.opacity() - 0.5) < 1e-6

    rr = next(i for i in items if isinstance(i, RoundedRectItem))
    assert rr.rect() == QRectF(0, 0, 50, 30)
    assert rr.radius() == 8
    assert rr.pos() == QPointF(10, 10)

    pg = next(i for i in items if isinstance(i, PolygonItem))
    assert pg.kind == "triangle"
    assert pg.polygon().count() == 3
    assert abs(pg.rotation() - 30) < 1e-6


def test_polygon_set_rect_shapes():
    for kind, vertices in (("triangle", 3), ("diamond", 4),
                           ("pentagon", 5), ("hexagon", 6), ("star", 10)):
        item = PolygonItem(kind=kind)
        item.set_rect(QRectF(0, 0, 100, 100))
        assert item.polygon().count() == vertices


def test_roundtrip_image(scene, tmp_path):
    from PyQt5.QtGui import QPixmap
    pm = QPixmap(20, 12)
    pm.fill(QColor("#ff8800"))
    img = ImageItem(pm)
    img.setPos(5, 6)
    scene.addItem(img)

    path = tmp_path / "img.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    loaded = next(i for i in other.vector_items() if isinstance(i, ImageItem))
    assert loaded.pixmap().width() == 20
    assert loaded.pixmap().height() == 12
    assert loaded.pos() == QPointF(5, 6)


def test_svg_export(scene, tmp_path):
    _populated(scene)
    out = tmp_path / "out.svg"
    document.export_svg(scene, str(out))
    text = out.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "hello" in text          # text item survives as SVG text


def test_svg_native_roundtrip(scene, tmp_path):
    from khervepaint import svgio
    from PyQt5.QtGui import QPolygonF
    _populated(scene)
    poly = PolygonItem(kind="star")
    poly.set_rect(QRectF(0, 0, 60, 60))
    poly.setPos(100, 100)
    scene.addItem(poly)

    path = tmp_path / "doc.svg"
    svgio.save_svg(scene, str(path))
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))

    items = other.vector_items()
    assert any(isinstance(i, LineItem) for i in items)
    assert any(isinstance(i, RectItem) for i in items)
    assert any(isinstance(i, EllipseItem) for i in items)
    assert any(isinstance(i, TextItem) for i in items)
    star = next(i for i in items if isinstance(i, PolygonItem))
    assert star.kind == "star"
    assert star.polygon().count() == 10
    assert star.pos() == QPointF(100, 100)
    assert other.sceneRect().width() == 400


def test_svg_grid_metadata_roundtrip(scene, tmp_path):
    from khervepaint import svgio
    scene.grid_size = 25
    scene.show_grid = False
    scene.snap_enabled = False
    path = tmp_path / "grid.svg"
    svgio.save_svg(scene, str(path))
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    assert other.grid_size == 25
    assert other.show_grid is False
    assert other.snap_enabled is False


def test_svg_import_external_group_and_path(scene, tmp_path):
    from khervepaint import svgio
    svg = '''<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"
     viewBox="0 0 100 100">
  <g fill="#ff0000" transform="translate(10,10)">
    <rect x="0" y="0" width="20" height="20"/>
    <circle cx="50" cy="50" r="8"/>
    <path d="M0 0 L10 0 L10 10 Z"/>
  </g>
  <rect x="5" y="5" width="10" height="10"
        transform="matrix(2 0 0 1 0 0)"/>
</svg>'''
    p = tmp_path / "ext.svg"
    p.write_text(svg, encoding="utf-8")
    svgio.load_svg(scene, str(p))

    items = scene.vector_items()
    group = next(i for i in items if isinstance(i, GroupItem))
    assert len(group.childItems()) == 3
    # group fill is inherited by the children
    rect = next(c for c in group.childItems() if isinstance(c, RectItem))
    assert rect.brush().color().name() == "#ff0000"
    # the sheared rect is baked into a PathItem (non-simple transform)
    assert any(isinstance(i, PathItem) for i in items)


def test_svg_import_ungroup(scene, tmp_path):
    from khervepaint import svgio
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="50" height="50">
  <g><rect x="0" y="0" width="10" height="10"/>
     <rect x="20" y="20" width="10" height="10"/></g>
</svg>'''
    p = tmp_path / "grp.svg"
    p.write_text(svg, encoding="utf-8")
    svgio.load_svg(scene, str(p))
    group = scene.vector_items()[0]
    assert isinstance(group, GroupItem)
    group.setSelected(True)
    scene.ungroup_selection()
    assert len([i for i in scene.vector_items()
                if isinstance(i, RectItem)]) == 2


def test_pdf_export(scene, tmp_path):
    _populated(scene)
    out = tmp_path / "out.pdf"
    document.export_pdf(scene, str(out))
    assert out.read_bytes().startswith(b"%PDF")


def test_line_endpoint_handles(scene):
    line = LineItem(QLineF(0, 0, 100, 50))
    scene.addItem(line)
    assert line._handles is None
    line.setSelected(True)
    assert all(h.isVisible() for h in line._handles)
    assert line._handles[0].pos() == QPointF(0, 0)
    assert line._handles[1].pos() == QPointF(100, 50)

    line.endpoint_moved(1, QPointF(200, 80))
    assert line.line() == QLineF(0, 0, 200, 80)

    line.setSelected(False)
    assert not any(h.isVisible() for h in line._handles)
    # Handles are implementation details: not serialised, not listed.
    assert scene.vector_items() == [line]
    assert document.item_to_dict(line)["x2"] == 200


def test_copy_paste_and_duplicate(app):
    from khervepaint.mainwindow import MainWindow
    win = MainWindow()
    rect = RectItem(QRectF(0, 0, 30, 20))
    rect.setPos(5, 5)
    win.scene.addItem(rect)
    rect.setSelected(True)

    win.copy_selection()
    before = len(win.scene.vector_items())
    win.paste()
    items = win.scene.vector_items()
    assert len(items) == before + 1
    pasted = [i for i in items if i is not rect][0]
    assert pasted.pos() == QPointF(25, 25)        # offset by 20

    win.scene.clearSelection()
    rect.setSelected(True)
    win.duplicate_selection()
    assert len(win.scene.vector_items()) == before + 2


def test_pencil_paints_raster(scene):
    before = scene.raster_item.pixmap().toImage()
    scene.pen = QPen(QColor("#000000"), 5)
    scene._paint_raster(QPointF(10, 10), QPointF(100, 100))
    after = scene.raster_item.pixmap().toImage()
    assert before != after
    assert after.pixelColor(55, 55).name() == "#000000"
