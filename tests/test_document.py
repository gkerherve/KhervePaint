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
    scene.grid_divisions = 35
    scene.show_grid = False
    scene.snap_enabled = False
    path = tmp_path / "grid.kpaint"
    document.save_kpaint(scene, str(path))

    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    assert other.grid_divisions == 35
    assert other.show_grid is False
    assert other.snap_enabled is False


def test_grid_size_derived_from_divisions():
    scene = PaintScene(800, 600)
    scene.grid_divisions = 40
    assert scene.grid_size == 20          # 800 / 40
    scene.grid_divisions = 80
    assert scene.grid_size == 10          # more divisions -> finer
    assert scene.grid_size < 20


def test_legacy_pixel_grid_loads(scene, tmp_path):
    import json
    # An old .kpaint stored the grid as a pixel "size".
    legacy = {"format": "kpaint", "version": 1, "width": 800, "height": 600,
              "grid": {"size": 20, "show": True, "snap": True}, "items": []}
    path = tmp_path / "legacy.kpaint"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    assert other.grid_divisions == 40     # 800 / 20


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
    scene.grid_divisions = 20          # 400px wide / 20 -> 20px spacing
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
    scene.grid_divisions = 25
    scene.show_grid = False
    scene.snap_enabled = False
    path = tmp_path / "grid.svg"
    svgio.save_svg(scene, str(path))
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    assert other.grid_divisions == 25
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


def test_line_resize_handles(scene):
    line = LineItem(QLineF(0, 0, 100, 50))
    scene.addItem(line)
    line.setSelected(True)
    scene.refresh_handles()
    handles = scene._sel_handles
    assert handles is not None and handles.kind == "line"
    assert len(handles.handles) == 2

    handles.drag("p2", QPointF(200, 80))      # drag the second endpoint
    assert line.line().p2() == QPointF(200, 80)
    # Handles are not vector items and not serialised.
    assert scene.vector_items() == [line]
    assert document.item_to_dict(line)["x2"] == 200


def test_box_resize_handle(scene):
    rect = RectItem(QRectF(0, 0, 40, 40))
    scene.addItem(rect)
    rect.setSelected(True)
    scene.refresh_handles()
    handles = scene._sel_handles
    assert handles.kind == "box"
    assert len(handles.handles) == 8
    handles.drag("se", QPointF(100, 80))      # drag bottom-right corner
    assert rect.rect() == QRectF(0, 0, 100, 80)


def test_polygon_vertex_handle(scene):
    from PyQt5.QtGui import QPolygonF
    tri = PolygonItem(
        QPolygonF([QPointF(0, 0), QPointF(40, 0), QPointF(20, 40)]),
        kind="triangle")
    scene.addItem(tri)
    tri.setSelected(True)
    scene.refresh_handles()
    handles = scene._sel_handles
    assert handles.kind == "polygon"
    assert len(handles.handles) == 3
    handles.drag(2, QPointF(20, 80))          # drag the apex down
    assert tri.polygon().at(2) == QPointF(20, 80)


def test_double_click_rotate_uses_centre(scene):
    from PyQt5.QtGui import QPolygonF
    tri = PolygonItem(
        QPolygonF([QPointF(100, 100), QPointF(160, 100), QPointF(130, 160)]),
        kind="triangle")
    scene.addItem(tri)
    before = tri.sceneBoundingRect().center()

    scene.enter_rotate_mode(tri)
    assert scene._sel_handles.kind == "rotate"
    assert tri.transformOriginPoint() == tri.boundingRect().center()

    tri.setRotation(90)
    after = tri.sceneBoundingRect().center()
    # Rotating about its own centre keeps the shape in roughly the
    # same place (it does NOT fly off to the scene origin).
    assert abs(after.x() - before.x()) < 1.0
    assert abs(after.y() - before.y()) < 1.0


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


def test_properties_dialog_applies(app):
    from khervepaint.properties import PropertiesDialog
    scene = PaintScene(200, 200)
    rect = RectItem(QRectF(0, 0, 40, 30))
    scene.addItem(rect)

    dlg = PropertiesDialog(rect)
    dlg.x.setValue(15); dlg.y.setValue(25)
    dlg.rotation.setValue(45)
    dlg.opacity.setValue(50)
    dlg.stroke_on.setChecked(True)
    dlg.stroke_color.set_color(QColor("#112233"))
    dlg.stroke_width.setValue(6)
    dlg.fill_on.setChecked(True)
    dlg.fill_color.set_color(QColor("#445566"))
    dlg.rw.setValue(80); dlg.rh.setValue(60)
    dlg._apply_and_accept()

    assert rect.pos() == QPointF(15, 25)
    assert abs(rect.rotation() - 45) < 1e-6
    assert abs(rect.opacity() - 0.5) < 1e-6
    assert rect.pen().color().name() == "#112233"
    assert rect.pen().widthF() == 6
    assert rect.brush().color().name() == "#445566"
    assert rect.rect() == QRectF(0, 0, 80, 60)


def test_properties_dialog_text(app):
    from khervepaint.properties import PropertiesDialog
    scene = PaintScene(200, 200)
    text = TextItem("old")
    scene.addItem(text)
    dlg = PropertiesDialog(text)
    dlg.text.setPlainText("new label")
    dlg.font_size.setValue(28)
    dlg.bold.setChecked(True)
    dlg._apply_and_accept()
    assert text.toPlainText() == "new label"
    assert text.font().pointSize() == 28
    assert text.font().bold() is True


def test_context_menu_builds(app):
    from khervepaint.mainwindow import MainWindow
    from khervepaint.properties import build_context_menu
    win = MainWindow()
    rect = RectItem(QRectF(0, 0, 10, 10))
    win.scene.addItem(rect)
    menu = build_context_menu(win, rect)
    labels = [a.text() for a in menu.actions() if a.text()]
    assert "Edit properties…" in labels
    assert "Bring to front" in labels


def test_reorder_persists_through_svg(app, tmp_path):
    from khervepaint import svgio
    from khervepaint.mainwindow import MainWindow
    win = MainWindow()
    bottom = RectItem(QRectF(0, 0, 10, 10))
    top = EllipseItem(QRectF(0, 0, 10, 10))
    win.scene.addItem(bottom)
    win.scene.addItem(top)
    win.reorder_item(bottom, "front")
    assert bottom.zValue() > top.zValue()

    path = tmp_path / "order.svg"
    svgio.save_svg(win.scene, str(path))
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    items = other.vector_items()          # ascending z
    assert isinstance(items[-1], RectItem)   # bottom is now on top


def _enclosed_rect_scene():
    """A 200x200 scene with a hollow black rectangle outline (50..150)."""
    scene = PaintScene(200, 200)
    box = RectItem(QRectF(50, 50, 100, 100))
    box.setPen(QPen(QColor("#000000"), 4))
    box.setBrush(QBrush(Qt.NoBrush))
    scene.addItem(box)
    return scene


def test_bucket_raster_fills_only_enclosed(app):
    from khervepaint import fill
    scene = _enclosed_rect_scene()
    fill.bucket_fill(scene, QPointF(100, 100), QColor("#ff0000"),
                     vector=False)
    pm = scene.raster_item.pixmap().toImage()
    assert pm.pixelColor(100, 100).name() == "#ff0000"   # inside filled
    assert pm.pixelColor(10, 10).name() == "#ffffff"      # outside untouched


def test_bucket_vector_creates_path_behind(app):
    from khervepaint import fill
    from khervepaint.canvas import PathItem
    scene = _enclosed_rect_scene()
    box = scene.vector_items()[0]
    item = fill.bucket_fill(scene, QPointF(100, 100), QColor("#00aa00"),
                            vector=True)
    assert isinstance(item, PathItem)
    assert item.brush().color().name() == "#00aa00"
    assert item.zValue() < box.zValue()                   # sits behind
    # the traced fill covers the interior click point
    assert item.path().contains(QPointF(100, 100))


def test_bucket_unenclosed_leaks_to_edge(app):
    from khervepaint import fill
    scene = _enclosed_rect_scene()
    # Clicking the surrounding white floods out to the canvas border.
    runs, edge = fill.flood_runs(
        fill.render_scene_image(scene), 10, 10, fill.DEFAULT_TOLERANCE)
    assert edge is True


def test_shape_label_roundtrip_kpaint(scene, tmp_path):
    rect = RectItem(QRectF(0, 0, 80, 40))
    rect.set_label("Start")
    from PyQt5.QtGui import QFont
    f = QFont("Arial", 18)
    f.setBold(True)
    rect.set_label_font(f)
    rect.set_label_color(QColor("#cc0000"))
    scene.addItem(rect)

    path = tmp_path / "label.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    loaded = other.vector_items()[0]
    assert loaded.label() == "Start"
    assert loaded.label_font().pointSize() == 18
    assert loaded.label_font().bold() is True
    assert loaded.label_color().name() == "#cc0000"


def test_shape_label_roundtrip_svg(scene, tmp_path):
    from khervepaint import svgio
    ell = EllipseItem(QRectF(0, 0, 60, 60))
    ell.set_label("Node")
    ell.setPos(40, 40)
    scene.addItem(ell)

    path = tmp_path / "label.svg"
    svgio.save_svg(scene, str(path))
    text = path.read_text(encoding="utf-8")
    assert "Node" in text                     # visible to other viewers

    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    items = [i for i in other.vector_items() if isinstance(i, EllipseItem)]
    assert len(items) == 1                     # label text not a 2nd item
    assert items[0].label() == "Node"


def test_properties_dialog_label(app):
    from khervepaint.properties import PropertiesDialog
    scene = PaintScene(200, 200)
    poly = PolygonItem(kind="triangle")
    poly.set_rect(QRectF(0, 0, 60, 60))
    scene.addItem(poly)
    dlg = PropertiesDialog(poly)
    dlg.label_text.setPlainText("Hi")
    dlg.label_size.setValue(22)
    dlg._apply_and_accept()
    assert poly.label() == "Hi"
    assert poly.label_font().pointSize() == 22


def test_pencil_paints_raster(scene):
    before = scene.raster_item.pixmap().toImage()
    scene.pen = QPen(QColor("#000000"), 5)
    scene._paint_raster(QPointF(10, 10), QPointF(100, 100))
    after = scene.raster_item.pixmap().toImage()
    assert before != after
    assert after.pixelColor(55, 55).name() == "#000000"
