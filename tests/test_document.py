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


@pytest.fixture
def window(app):
    """A MainWindow destroyed immediately (sip.delete) after the test,
    so accumulated top-level widgets don't segfault at interpreter exit."""
    from khervepaint.mainwindow import MainWindow
    win = MainWindow()
    yield win
    win._undo_stack.setClean()       # avoid the offscreen discard dialog
    win.close()
    app.processEvents()
    from PyQt5 import sip
    sip.delete(win)
    app.processEvents()


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


def test_new_polygon_shapes_vertex_counts():
    counts = {"right_triangle": 3, "parallelogram": 4, "trapezoid": 4,
              "heptagon": 7, "octagon": 8, "star6": 12, "plus": 12,
              "chevron": 6, "arrow_right": 7, "lightning": 7, "house": 5}
    for kind, n in counts.items():
        item = PolygonItem(kind=kind)
        item.set_rect(QRectF(0, 0, 100, 100))
        assert item.polygon().count() == n, kind


def test_explode_octagon(scene):
    octa = PolygonItem(kind="octagon")
    octa.set_rect(QRectF(0, 0, 80, 80))
    scene.addItem(octa)
    octa.setSelected(True)
    scene.explode_selection()
    lines = [i for i in scene.vector_items() if isinstance(i, LineItem)]
    assert len(lines) == 8                       # one per edge


def test_new_shape_roundtrips_kind(scene, tmp_path):
    house = PolygonItem(kind="house")
    house.set_rect(QRectF(0, 0, 60, 60))
    scene.addItem(house)
    path = tmp_path / "house.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    loaded = other.vector_items()[0]
    assert loaded.kind == "house"
    assert loaded.polygon().count() == 5


def test_kpaint_image_scale_rotation(scene, tmp_path):
    from khervepaint.canvas import center_origin
    from PyQt5.QtGui import QPixmap
    pm = QPixmap(30, 20)
    pm.fill(QColor("#0088ff"))
    img = ImageItem(pm)
    img.setPos(12, 8)
    center_origin(img)
    img.setRotation(45)
    img.setScale(1.5)
    scene.addItem(img)

    path = tmp_path / "imgscale.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    loaded = next(i for i in other.vector_items() if isinstance(i, ImageItem))
    assert abs(loaded.scale() - 1.5) < 1e-6
    assert abs(loaded.rotation() - 45) < 1e-6


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


def _scene_br(item):
    r = item.sceneBoundingRect()
    return [round(v, 2) for v in (r.x(), r.y(), r.width(), r.height())]


def test_svg_image_scale_rotation_roundtrip(scene, tmp_path):
    from khervepaint import svgio
    from khervepaint.canvas import center_origin
    from PyQt5.QtGui import QPixmap
    pm = QPixmap(40, 20)
    pm.fill(QColor("#ff0000"))
    img = ImageItem(pm)
    img.setPos(50, 60)
    center_origin(img)
    img.setRotation(30)
    img.setScale(2.0)
    scene.addItem(img)
    before = _scene_br(img)

    path = tmp_path / "img.svg"
    svgio.save_svg(scene, str(path))
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    loaded = next(i for i in other.vector_items() if isinstance(i, ImageItem))
    # scale (2x) and rotation (30 deg) survive: same on-screen footprint
    assert _scene_br(loaded) == before
    assert loaded.pixmap().width() == 40        # native pixels unchanged


def test_svg_shape_rotation_sign(scene, tmp_path):
    from khervepaint import svgio
    from khervepaint.canvas import center_origin
    rect = RectItem(QRectF(0, 0, 40, 20))
    rect.setPos(50, 60)
    center_origin(rect)
    rect.setRotation(30)
    scene.addItem(rect)

    path = tmp_path / "rot.svg"
    svgio.save_svg(scene, str(path))
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    loaded = other.vector_items()[0]
    assert abs(loaded.rotation() - 30) < 1e-3   # +30, not mirrored to -30


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


def test_box_resize_all_shapes(scene):
    from khervepaint.canvas import ArcShapeItem, RoundedRectItem
    from khervepaint.handles import SelectionHandles, RESIZE
    builders = [
        lambda: RectItem(QRectF(10, 10, 60, 40)),
        lambda: EllipseItem(QRectF(10, 10, 60, 40)),
        lambda: RoundedRectItem(QRectF(10, 10, 60, 40), 8),
        lambda: ArcShapeItem(QRectF(10, 10, 60, 40), "halfcircle"),
        lambda: ArcShapeItem(QRectF(10, 10, 60, 40), "quartercircle"),
    ]
    for build in builders:
        item = build()
        scene.addItem(item)
        item.setSelected(True)
        handles = SelectionHandles(scene, item, RESIZE)
        assert handles.kind == "box"
        handles.begin("se", QPointF(70, 50))
        handles.drag("se", QPointF(140, 110))      # must not raise
        handles.end()
        assert item.rect().width() > 60            # actually grew
        handles.remove()
        scene.removeItem(item)


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


def test_copy_paste_and_duplicate(window):
    win = window
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


def test_context_menu_builds(window):
    from khervepaint.properties import build_context_menu
    win = window
    rect = RectItem(QRectF(0, 0, 10, 10))
    win.scene.addItem(rect)
    menu = build_context_menu(win, rect)
    labels = [a.text() for a in menu.actions() if a.text()]
    assert "Edit properties…" in labels
    assert "Bring to front" in labels


def test_reorder_persists_through_svg(window, tmp_path):
    from khervepaint import svgio
    win = window
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


def test_crop_session_applies(app):
    from PyQt5.QtGui import QPixmap
    from khervepaint.crop import CropSession
    scene = PaintScene(200, 200)
    pm = QPixmap(40, 30)
    pm.fill(QColor("#00ff00"))
    img = ImageItem(pm)
    img.setPos(10, 10)
    scene.addItem(img)

    session = CropSession(scene, img)
    session.rect = QRectF(5, 4, 20, 15)
    session.apply()
    assert img.pixmap().width() == 20
    assert img.pixmap().height() == 15
    # the kept region stays in place: pos shifts by the crop offset
    assert img.pos() == QPointF(15, 14)


def test_scene_crop_flow(app):
    from PyQt5.QtGui import QPixmap
    scene = PaintScene(200, 200)
    pm = QPixmap(50, 50)
    pm.fill(QColor("#3366cc"))
    img = ImageItem(pm)
    scene.addItem(img)

    scene.begin_crop(img)
    assert scene.crop_active() is True
    scene._crop.rect = QRectF(0, 0, 10, 10)
    scene.apply_crop()
    assert scene.crop_active() is False
    assert img.pixmap().width() == 10
    # crop overlay items are gone (only the image remains as a vector item)
    assert scene.vector_items() == [img]


def test_undo_redo_add_move_delete(window):
    win = window
    s = win.scene
    s.snap_enabled = False

    rect = RectItem(QRectF(0, 0, 30, 20))
    rect.setPos(10, 10)
    s.addItem(rect)
    s.changed_by_user.emit()                   # an "add" gesture
    assert len(s.vector_items()) == 1

    s.vector_items()[0].setPos(80, 90)
    s.changed_by_user.emit()                   # a "move" gesture
    assert s.vector_items()[0].pos() == QPointF(80, 90)

    win._undo_stack.undo()                     # undo the move
    assert s.vector_items()[0].pos() == QPointF(10, 10)

    win._undo_stack.undo()                     # undo the add
    assert s.vector_items() == []

    win._undo_stack.redo()                     # redo the add
    assert len(s.vector_items()) == 1
    assert s.vector_items()[0].pos() == QPointF(10, 10)


def test_undo_restores_label_and_transform(window):
    from khervepaint.canvas import center_origin
    win = window
    s = win.scene
    rect = RectItem(QRectF(0, 0, 40, 40))
    s.addItem(rect)
    s.changed_by_user.emit()

    rect = s.vector_items()[0]
    rect.set_label("Hi")
    center_origin(rect)
    rect.setRotation(45)
    s.changed_by_user.emit()
    assert s.vector_items()[0].label() == "Hi"

    win._undo_stack.undo()                     # revert label + rotation
    reverted = s.vector_items()[0]
    assert reverted.label() == ""
    assert abs(reverted.rotation()) < 1e-6


def test_save_marks_history_clean(window, tmp_path):
    win = window
    s = win.scene
    s.addItem(RectItem(QRectF(0, 0, 10, 10)))
    s.changed_by_user.emit()
    assert win._undo_stack.isClean() is False
    win._path = str(tmp_path / "doc.svg")
    win.save_file()
    assert win._undo_stack.isClean() is True


def test_arc_shapes_roundtrip(scene, tmp_path):
    from khervepaint.canvas import ArcShapeItem
    half = ArcShapeItem(QRectF(0, 0, 40, 40), kind="halfcircle")
    half.setPos(10, 10)
    scene.addItem(half)
    quarter = ArcShapeItem(QRectF(0, 0, 30, 30), kind="quartercircle")
    quarter.flip_h = True
    quarter._rebuild()
    scene.addItem(quarter)

    path = tmp_path / "arcs.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    arcs = [i for i in other.vector_items() if isinstance(i, ArcShapeItem)]
    assert len(arcs) == 2
    h = next(a for a in arcs if a.kind == "halfcircle")
    assert h.rect() == QRectF(0, 0, 40, 40)
    assert h.pos() == QPointF(10, 10)
    q = next(a for a in arcs if a.kind == "quartercircle")
    assert q.flip_h is True


def test_arc_shape_roundtrip_svg(scene, tmp_path):
    from khervepaint import svgio
    from khervepaint.canvas import ArcShapeItem
    arc = ArcShapeItem(QRectF(0, 0, 50, 50), kind="halfcircle")
    scene.addItem(arc)
    path = tmp_path / "arc.svg"
    svgio.save_svg(scene, str(path))
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    loaded = [i for i in other.vector_items() if isinstance(i, ArcShapeItem)]
    assert len(loaded) == 1
    assert loaded[0].kind == "halfcircle"


def test_mirror_polygon_flips_geometry(scene):
    from PyQt5.QtGui import QPolygonF
    tri = PolygonItem(
        QPolygonF([QPointF(0, 0), QPointF(40, 0), QPointF(0, 30)]),
        kind="triangle")
    scene.addItem(tri)
    before = [(p.x(), p.y()) for p in tri.polygon()]
    tri.setSelected(True)
    scene.mirror_selection(horizontal=True)
    after = [(p.x(), p.y()) for p in tri.polygon()]
    assert after != before
    # mirroring twice returns to the original geometry
    scene.mirror_selection(horizontal=True)
    again = [(round(p.x(), 3), round(p.y(), 3)) for p in tri.polygon()]
    assert again == [(round(x, 3), round(y, 3)) for x, y in before]


def test_no_default_selection_rectangle(app):
    from PyQt5.QtWidgets import QStyle, QStyleOptionGraphicsItem
    from PyQt5.QtGui import QImage, QPainter
    s = PaintScene(100, 100)
    rect = RectItem(QRectF(0, 0, 40, 30))
    s.addItem(rect)
    image = QImage(100, 100, QImage.Format_ARGB32)
    painter = QPainter(image)
    option = QStyleOptionGraphicsItem()
    option.state = QStyle.State_Selected           # pretend it's selected
    rect.paint(painter, option)
    painter.end()
    # NoSelMixin strips the selected state, so Qt draws no dashed box
    assert not (option.state & QStyle.State_Selected)


def test_mirror_group_swaps_sides(scene):
    left = RectItem(QRectF(0, 0, 20, 20))
    left.setPos(20, 40)
    right = RectItem(QRectF(0, 0, 20, 20))
    right.setPos(120, 40)
    scene.addItem(left)
    scene.addItem(right)
    left.setSelected(True)
    right.setSelected(True)
    scene.group_selection()
    group = scene.vector_items()[0]

    lc0 = left.sceneBoundingRect().center().x()
    rc0 = right.sceneBoundingRect().center().x()
    assert lc0 < rc0                              # left starts on the left

    scene.clearSelection()
    group.setSelected(True)
    scene.mirror_selection(horizontal=True)
    assert left.sceneBoundingRect().center().x() > \
        right.sceneBoundingRect().center().x()    # sides swapped

    scene.mirror_selection(horizontal=True)       # flip back
    assert abs(left.sceneBoundingRect().center().x() - lc0) < 1


def test_mirror_arc_flips_flag(scene):
    from khervepaint.canvas import ArcShapeItem
    arc = ArcShapeItem(QRectF(0, 0, 40, 40), kind="quartercircle")
    scene.addItem(arc)
    arc.setSelected(True)
    assert arc.flip_h is False
    scene.mirror_selection(horizontal=True)
    assert arc.flip_h is True


def test_explode_hexagon_to_six_lines(scene):
    hexa = PolygonItem(kind="hexagon")
    hexa.set_rect(QRectF(0, 0, 60, 60))
    hexa.setPos(20, 20)
    scene.addItem(hexa)
    hexa.setSelected(True)
    scene.explode_selection()

    items = scene.vector_items()
    lines = [i for i in items if isinstance(i, LineItem)]
    assert len(lines) == 6                       # one per edge
    assert not any(isinstance(i, PolygonItem) for i in items)
    assert all(ln.isSelected() for ln in lines)  # ready to regroup
    # the edges form a closed loop: every endpoint is shared by exactly
    # two segments (each hexagon vertex is met by its two adjacent edges)
    from collections import Counter
    endpoints = Counter()
    for ln in lines:
        endpoints[(round(ln.line().x1()), round(ln.line().y1()))] += 1
        endpoints[(round(ln.line().x2()), round(ln.line().y2()))] += 1
    assert len(endpoints) == 6                    # six distinct vertices
    assert all(count == 2 for count in endpoints.values())


def test_explode_ellipse_to_arcs(scene):
    ell = EllipseItem(QRectF(0, 0, 80, 60))
    ell.setPen(QPen(QColor("#aa3300"), 2))
    scene.addItem(ell)
    ell.setSelected(True)
    scene.explode_selection()
    items = scene.vector_items()
    assert not any(isinstance(i, EllipseItem) for i in items)
    arcs = [i for i in items if isinstance(i, PathItem)]
    assert len(arcs) == 4                        # ellipse = four cubic arcs
    assert all(a.pen().color().name() == "#aa3300" for a in arcs)


def test_explode_halfcircle(scene):
    from khervepaint.canvas import ArcShapeItem
    arc = ArcShapeItem(QRectF(0, 0, 40, 40), kind="halfcircle")
    scene.addItem(arc)
    arc.setSelected(True)
    scene.explode_selection()
    items = scene.vector_items()
    assert not any(isinstance(i, ArcShapeItem) for i in items)
    # the flat diameter becomes a line, the curve becomes arc path(s)
    assert any(isinstance(i, LineItem) for i in items)
    assert any(isinstance(i, PathItem) for i in items)


def test_explode_rect_to_four_lines(scene):
    rect = RectItem(QRectF(0, 0, 40, 30))
    rect.setPen(QPen(QColor("#336699"), 3))
    scene.addItem(rect)
    rect.setSelected(True)
    scene.explode_selection()
    lines = [i for i in scene.vector_items() if isinstance(i, LineItem)]
    assert len(lines) == 4
    assert lines[0].pen().color().name() == "#336699"   # pen inherited


def test_explode_then_regroup_after_delete(window):
    s = window.scene
    tri = PolygonItem(kind="triangle")
    tri.set_rect(QRectF(0, 0, 30, 30))
    s.addItem(tri)
    s.changed_by_user.emit()                     # baseline

    s.vector_items()[0].setSelected(True)
    s.explode_selection()
    lines = [i for i in s.vector_items() if isinstance(i, LineItem)]
    assert len(lines) == 3
    # remove one edge, regroup the remaining two
    lines[0].setSelected(False)
    s.removeItem(lines[0])
    for ln in lines[1:]:
        ln.setSelected(True)
    s.group_selection()
    assert any(isinstance(i, GroupItem) for i in s.vector_items())

    # explode is undoable: undo regroup, delete, and explode
    window._undo_stack.undo()                    # undo the explode chain step
    # after enough undos the triangle returns
    while window._undo_stack.canUndo() and not any(
            isinstance(i, PolygonItem) for i in s.vector_items()):
        window._undo_stack.undo()
    assert any(isinstance(i, PolygonItem) for i in s.vector_items())


def test_generated_shape_icons(app):
    from khervepaint import icons
    # shapes with no Material Design glyph get a drawn icon (not blank,
    # which would otherwise widen the toolbar by falling back to text)
    assert not icons.shape_icon("parallelogram").isNull()
    assert not icons.shape_icon("heptagon").isNull()
    assert not icons.shape_icon("halfcircle").isNull()      # arc kind
    assert icons.shape_icon("not_a_shape").isNull()


def test_ai_extract_specs():
    from khervepaint.ai_assistant import extract_specs
    reply = ('Sure, here you go:\n```json\n'
             '[{"shape":"rect","x":10,"y":20,"w":80,"h":40}]\n```\nDone.')
    specs = extract_specs(reply)
    assert specs == [{"shape": "rect", "x": 10, "y": 20, "w": 80, "h": 40}]
    # the {"shapes": [...]} form and bare JSON also work
    assert extract_specs('```\n{"shapes":[{"shape":"circle"}]}\n```') \
        == [{"shape": "circle"}]
    assert extract_specs("no shapes here") == []


def test_ai_apply_specs_creates_items(scene):
    from khervepaint.ai_assistant import apply_specs
    from khervepaint.canvas import ArrowItem, PolygonItem
    specs = [
        {"shape": "rect", "x": 0, "y": 0, "w": 60, "h": 40,
         "stroke": "#112233", "fill": "#abcdef", "label": "Start"},
        {"shape": "arrow", "x1": 0, "y1": 0, "x2": 50, "y2": 50},
        {"shape": "hexagon", "x": 100, "y": 100, "w": 40, "h": 40},
        {"shape": "text", "x": 10, "y": 10, "text": "hi", "size": 20},
    ]
    created = apply_specs(scene, specs)
    assert len(created) == 4
    rect = next(i for i in created if isinstance(i, RectItem))
    assert rect.brush().color().name() == "#abcdef"
    assert rect.label() == "Start"
    assert any(isinstance(i, ArrowItem) for i in created)
    assert any(isinstance(i, PolygonItem) and i.kind == "hexagon"
               for i in created)
    assert any(isinstance(i, TextItem) for i in created)


def test_ai_providers_metadata():
    from khervepaint import ai_providers as p
    assert set(p.PROVIDERS) == {"Claude", "ChatGPT", "Mistral",
                                "Ollama", "Local"}
    assert "Claude" in p.NEEDS_KEY and "Ollama" not in p.NEEDS_KEY
    assert p.DEFAULT_BASE["Ollama"].startswith("http://localhost")


def test_ai_dock_builds(window):
    assert window.ai_dock is not None
    # the toggle is wired into the View menu
    assert window.ai_dock.toggleViewAction() is not None


def test_ai_send_without_key_warns(window):
    dock = window.ai_dock
    dock._settings.setValue("ai/provider", "Claude")
    dock._settings.setValue("ai/key/Claude", "")
    dock._settings.setValue("ai/model/Claude", "claude-x")
    dock.input.setPlainText("hi")
    dock._send()                              # no key: warns, no network
    assert "API key" in dock.transcript.toPlainText()


def test_ai_settings_dialog(window):
    from khervepaint.ai_assistant import AiSettingsDialog
    from khervepaint import ai_providers as p
    dlg = AiSettingsDialog(window)
    assert dlg.provider_combo.count() == 5            # five providers
    assert dlg.provider_combo.itemData(0) in p.PROVIDERS
    assert p.provider_for_display("Anthropic (Claude)") == "Claude"
    assert "console.anthropic.com" in p.PROVIDER_HELP["Claude"]
    # the Model combo is populated per provider
    for key, least in (("Claude", 4), ("ChatGPT", 6), ("Mistral", 4),
                       ("Ollama", 5)):
        dlg.provider_combo.setCurrentIndex(dlg.provider_combo.findData(key))
        assert dlg.model_combo.count() >= least, key


def test_help_content(window):
    from khervepaint import help as h
    guide = h.user_guide_html()
    for token in ("User Guide", "Tools", "ACS", "Ctrl+Z", "Bucket",
                  "Explode", "Drawing Size", "Crop", "Undo"):
        assert token in guide
    about = h.about_html()
    assert "KhervePaint" in about and "GPL-3.0" in about
    dlg = h.UserGuideDialog(window)        # builds without error
    assert dlg.windowTitle()


def test_recent_files_list(window):
    window._clear_recent()
    window._add_recent("/docs/first.svg")
    window._add_recent("/docs/second.kpaint")
    assert window._recent_files()[0] == "/docs/second.kpaint"  # newest first
    # re-adding moves to front and dedupes
    window._add_recent("/docs/first.svg")
    files = window._recent_files()
    assert files[0] == "/docs/first.svg"
    assert len(files) == 2
    window._remove_recent("/docs/first.svg")
    assert "/docs/first.svg" not in window._recent_files()
    window._clear_recent()
    assert window._recent_files() == []


def test_save_adds_to_recent(window, tmp_path):
    window._clear_recent()
    s = window.scene
    s.addItem(RectItem(QRectF(0, 0, 10, 10)))
    s.changed_by_user.emit()
    path = str(tmp_path / "doc.svg")
    window._path = path
    window.save_file()
    assert path in window._recent_files()
    window._clear_recent()


def test_dpi_roundtrip_kpaint(scene, tmp_path):
    scene.dpi = 300
    path = tmp_path / "dpi.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    assert other.dpi == 300


def test_dpi_roundtrip_svg(scene, tmp_path):
    from khervepaint import svgio
    scene.dpi = 300
    path = tmp_path / "dpi.svg"
    svgio.save_svg(scene, str(path))
    text = path.read_text(encoding="utf-8")
    assert 'in"' in text                       # physical width in inches
    assert "viewBox" in text                    # pixel coordinate system
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    assert other.dpi == 300
    assert other.sceneRect().width() == 400     # px size preserved


def test_acs_preset_pixels(app):
    from khervepaint.canvassize import CanvasSizeDialog
    dlg = CanvasSizeDialog(current=(800, 600), dpi=96)
    # select the ACS single column preset (index 1)
    dlg.preset_combo.setCurrentIndex(1)
    dlg._apply_preset(1)
    mode, pw, ph, dpi = dlg.result_value()
    assert mode == "size"
    assert dpi == 300
    assert pw == round(3.25 * 300)              # 975 px wide
    assert ph == round(2.50 * 300)              # 750 px tall


def test_size_dialog_mm_conversion(app):
    from khervepaint.canvassize import CanvasSizeDialog
    dlg = CanvasSizeDialog(current=(800, 600), dpi=300)
    dlg.unit_combo.setCurrentText("mm")
    dlg.width_spin.setValue(82.5)               # ACS single column in mm
    dlg.height_spin.setValue(50)
    _, pw, ph, dpi = dlg.result_value()
    # 82.5 mm at 300 dpi = 82.5/25.4*300 ≈ 974 px
    assert abs(pw - round(82.5 / 25.4 * 300)) <= 1


def test_resize_canvas_keeps_items(scene):
    rect = RectItem(QRectF(0, 0, 30, 20))
    rect.setPos(15, 15)
    scene.addItem(rect)
    scene.resize_canvas(1000, 700)
    assert scene.sceneRect().width() == 1000
    assert scene.sceneRect().height() == 700
    assert scene.raster_item.pixmap().width() == 1000
    assert scene.vector_items()[0].pos() == QPointF(15, 15)   # unmoved


def test_fit_to_content_shrinks_and_shifts(scene):
    rect = RectItem(QRectF(0, 0, 40, 30))
    rect.setPos(200, 150)                       # far from the origin
    scene.addItem(rect)
    scene.fit_to_content(selection_only=False, margin=10)
    # canvas now snug around the drawing plus the margin
    assert abs(scene.sceneRect().width() - (40 + 20)) <= 1
    assert abs(scene.sceneRect().height() - (30 + 20)) <= 1
    # the rect sits at the margin (within the pen half-width)
    assert abs(scene.vector_items()[0].sceneBoundingRect().left() - 10) <= 1
    assert abs(scene.vector_items()[0].sceneBoundingRect().top() - 10) <= 1


def test_resize_canvas_is_undoable(window):
    s = window.scene
    s.addItem(RectItem(QRectF(0, 0, 10, 10)))
    s.changed_by_user.emit()                    # baseline (the add)
    s.resize_canvas(1234, 567)
    assert s.sceneRect().width() == 1234
    window._undo_stack.undo()                   # undo the resize
    assert s.sceneRect().width() == 800         # back to the default


def test_pencil_creates_vector_stroke(scene):
    from khervepaint.canvas import PathItem
    scene.pen = QPen(QColor("#000000"), 4)
    scene.pencil_begin(QPointF(0, 0))
    for x in range(5, 65, 5):
        scene.pencil_extend(QPointF(x, x))
    scene.pencil_end()

    strokes = [i for i in scene.vector_items() if isinstance(i, PathItem)]
    assert len(strokes) == 1
    stroke = strokes[0]
    # selectable, movable and a real vector path
    assert bool(stroke.flags() & stroke.ItemIsSelectable)
    assert bool(stroke.flags() & stroke.ItemIsMovable)
    assert stroke.path().elementCount() > 1
    assert stroke.pen().color().name() == "#000000"
    # round-trips as a vector path
    assert document.item_to_dict(stroke)["type"] == "path"


def test_pencil_single_click_makes_no_stroke(scene):
    scene.pencil_begin(QPointF(20, 20))
    scene.pencil_end()                         # no drag in between
    assert scene.vector_items() == []          # no degenerate stroke left


def test_pencil_stroke_resizes_with_handles(scene):
    from khervepaint.canvas import PathItem
    scene.pencil_begin(QPointF(0, 0))
    for x in range(5, 45, 5):
        scene.pencil_extend(QPointF(x, x / 2))
    scene.pencil_end()
    stroke = next(i for i in scene.vector_items()
                  if isinstance(i, PathItem))
    stroke.setSelected(True)
    scene.refresh_handles()
    handles = scene._sel_handles
    assert handles is not None and handles.kind == "scale"
    before = stroke.scale()
    handles.begin("se", QPointF(40, 20))
    handles.drag("se", QPointF(80, 40))        # drag a corner outward
    assert stroke.scale() > before             # the stroke grew
