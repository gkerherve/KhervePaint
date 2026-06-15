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
    scene.grid_mm = 3.5
    scene.show_grid = False
    scene.snap_enabled = False
    scene.infinite = True
    path = tmp_path / "grid.kpaint"
    document.save_kpaint(scene, str(path))

    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    assert other.grid_mm == 3.5
    assert other.show_grid is False
    assert other.snap_enabled is False
    assert other.infinite is True


def test_grid_size_derived_from_mm():
    scene = PaintScene(800, 600)
    scene.dpi = 25.4                      # 1 mm == 1 px, for an easy check
    scene.grid_mm = 20
    assert scene.grid_size == 20
    scene.grid_mm = 10
    assert scene.grid_size == 10          # smaller mm -> finer
    scene.grid_mm = 5
    assert scene.grid_size == 5


def test_grid_size_is_not_rounded_to_whole_pixels():
    # A 1 mm grid at 300 dpi is 11.81 px; rounding it to 12 px made
    # snapped points miss true mm, so a 10 mm dimension read 10.2 mm.
    scene = PaintScene(800, 600)
    scene.dpi = 300
    scene.grid_mm = 1.0
    assert scene.grid_size == pytest.approx(1.0 / 25.4 * 300)   # ~11.81, exact


def test_dimension_on_snapped_grid_reads_exact_mm():
    from khervepaint.canvas import DimensionItem
    scene = PaintScene(2000, 1500)
    scene.dpi = 300
    scene.grid_mm = 1.0
    scene.snap_enabled = True
    p1 = scene.snap(QPointF(100.3, 100.0))
    p2 = scene.snap(QPointF(p1.x() + 118.0, 100.0))   # ~10 mm to the right
    dim = DimensionItem()
    dim.setLine(QLineF(p1, p2))
    scene.addItem(dim)
    assert dim.length_mm() == pytest.approx(10.0, abs=1e-6)
    assert dim._label_text() == "10.0 mm"


def test_legacy_pixel_grid_loads(scene, tmp_path):
    import json
    # An old .kpaint stored the grid as a pixel "size".
    legacy = {"format": "kpaint", "version": 1, "width": 800, "height": 600,
              "grid": {"size": 20, "show": True, "snap": True}, "items": []}
    path = tmp_path / "legacy.kpaint"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    # 20 px at 96 dpi -> mm, and that mm yields 20 px spacing back.
    assert other.grid_mm == pytest.approx(20 / 96 * 25.4)
    assert other.grid_size == pytest.approx(20)


def test_legacy_divisions_grid_loads(scene, tmp_path):
    import json
    # A v3 .kpaint stored the grid as divisions across the canvas width.
    legacy = {"format": "kpaint", "version": 3, "width": 800, "height": 600,
              "grid": {"divisions": 40, "show": True, "snap": True},
              "items": []}
    path = tmp_path / "legacy_div.kpaint"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    assert other.grid_size == pytest.approx(20)   # 800 / 40, same spacing


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


def test_group_preserves_child_positions(scene):
    # Grouping must not snap children into the grid (they kept their pos).
    scene.dpi = 25.4; scene.grid_mm = 20; scene.snap_enabled = True
    r1 = RectItem(QRectF(0, 0, 30, 20)); r1.setPos(37, 51); scene.addItem(r1)
    r2 = RectItem(QRectF(0, 0, 30, 20)); r2.setPos(115, 93); scene.addItem(r2)
    before = [r1.scenePos(), r2.scenePos()]
    r1.setSelected(True); r2.setSelected(True)
    scene.group_selection()
    assert r1.scenePos() == before[0]
    assert r2.scenePos() == before[1]


def _two_rect_group(scene):
    scene.snap_enabled = False
    r1 = RectItem(QRectF(0, 0, 30, 20)); r1.setPos(40, 40); scene.addItem(r1)
    r2 = RectItem(QRectF(0, 0, 30, 20)); r2.setPos(120, 100); scene.addItem(r2)
    r1.setSelected(True); r2.setSelected(True)
    scene.group_selection()
    return scene.vector_items()[0]


def test_group_resize_anchors_opposite_corner(scene):
    from khervepaint.handles import SelectionHandles, RESIZE
    g = _two_rect_group(scene)
    br = g.sceneBoundingRect()
    h = SelectionHandles(scene, g, RESIZE)
    assert h.kind == "gbox"                      # 8 handles for X/Y resize
    h.begin("se", br.bottomRight())             # drag the SE corner out
    h.drag("se", br.bottomRight() + QPointF(60, 40))
    h.end()
    br2 = g.sceneBoundingRect()
    # the opposite (NW) corner stays put; the group only grows
    assert abs(br2.topLeft().x() - br.topLeft().x()) <= 1
    assert abs(br2.topLeft().y() - br.topLeft().y()) <= 1
    assert br2.width() > br.width() and br2.height() > br.height()


def test_group_side_handles_resize_one_axis(scene):
    from khervepaint.handles import SelectionHandles, RESIZE
    # East handle: stretch X only — top, height and left stay; width grows.
    g = _two_rect_group(scene)
    br = g.sceneBoundingRect()
    h = SelectionHandles(scene, g, RESIZE)
    e = next(x for x in h.handles if x.role == "e")
    h.begin("e", e.scenePos()); h.drag("e", e.scenePos() + QPointF(100, 0))
    h.end()
    br2 = g.sceneBoundingRect()
    assert abs(br2.left() - br.left()) <= 1
    assert abs(br2.height() - br.height()) <= 1   # Y untouched
    assert br2.width() > br.width() + 50

    # South handle on a fresh group: stretch Y only.
    scene.clearSelection()
    g2 = _two_rect_group(scene)
    br = g2.sceneBoundingRect()
    h2 = SelectionHandles(scene, g2, RESIZE)
    s = next(x for x in h2.handles if x.role == "s")
    h2.begin("s", s.scenePos()); h2.drag("s", s.scenePos() + QPointF(0, 80))
    h2.end()
    br2 = g2.sceneBoundingRect()
    assert abs(br2.top() - br.top()) <= 1
    assert abs(br2.width() - br.width()) <= 1     # X untouched
    assert br2.height() > br.height() + 40


def test_group_nonuniform_resize_roundtrips(scene):
    from khervepaint.handles import SelectionHandles, RESIZE
    g = _two_rect_group(scene)
    h = SelectionHandles(scene, g, RESIZE)
    e = next(x for x in h.handles if x.role == "e")
    h.begin("e", e.scenePos()); h.drag("e", e.scenePos() + QPointF(120, 0))
    h.end()
    h.remove()
    b0 = [round(v, 1) for v in g.sceneBoundingRect().getRect()]
    other = PaintScene()
    document.dict_to_scene(document.scene_to_dict(scene), other)
    b1 = [round(v, 1) for v in
          other.vector_items()[0].sceneBoundingRect().getRect()]
    assert b0 == b1                              # exact in .kpaint


def test_group_handles_are_scene_level(scene):
    # A QGraphicsItemGroup intercepts its children's mouse events, so a
    # group's handles must NOT be its children (or they'd be dead) — they
    # live at scene level and are excluded from vector_items.
    from khervepaint.handles import SelectionHandles, RESIZE, ROTATE
    r1 = RectItem(QRectF(0, 0, 40, 30)); r1.setPos(100, 100); scene.addItem(r1)
    r2 = RectItem(QRectF(0, 0, 40, 30)); r2.setPos(200, 160); scene.addItem(r2)
    r1.setSelected(True); r2.setSelected(True); scene.group_selection()
    g = scene.vector_items()[0]
    for mode in (RESIZE, ROTATE):
        h = SelectionHandles(scene, g, mode)
        assert h.handles and all(hd.parentItem() is None for hd in h.handles)
        assert all(hd.scene() is scene for hd in h.handles)
        assert all(hd not in scene.vector_items() for hd in h.handles)
        h.remove()
        assert all(hd.scene() is None for hd in h.handles)


def test_normal_item_handles_stay_children(scene):
    # Non-group items keep child handles so they follow the item.
    from khervepaint.handles import SelectionHandles, RESIZE
    r = RectItem(QRectF(0, 0, 40, 30)); scene.addItem(r); r.setSelected(True)
    h = SelectionHandles(scene, r, RESIZE)
    assert all(hd.parentItem() is r for hd in h.handles)
    h.remove()


def _scaled_group(scene):
    from khervepaint.handles import SelectionHandles, RESIZE
    scene.dpi = 25.4; scene.grid_mm = 20
    r1 = RectItem(QRectF(0, 0, 30, 20)); r1.setPos(40, 40); scene.addItem(r1)
    r2 = RectItem(QRectF(0, 0, 30, 20)); r2.setPos(120, 100); scene.addItem(r2)
    r1.setSelected(True); r2.setSelected(True); scene.group_selection()
    g = scene.vector_items()[0]
    br0 = g.sceneBoundingRect()
    h = SelectionHandles(scene, g, RESIZE)
    h.begin("se", br0.bottomRight())
    h.drag("se", br0.bottomRight() + QPointF(60, 40))
    h.end()
    return g.sceneBoundingRect()


def test_scaled_group_roundtrips_kpaint(scene):
    target = _scaled_group(scene)
    other = PaintScene()
    document.dict_to_scene(document.scene_to_dict(scene), other)
    got = other.vector_items()[0].sceneBoundingRect()
    assert all(abs(a - b) <= 1 for a, b in zip(target.getRect(),
                                               got.getRect()))


def test_scaled_group_roundtrips_svg(scene, tmp_path):
    from khervepaint import svgio
    target = _scaled_group(scene)
    path = tmp_path / "scaled_group.svg"
    svgio.save_svg(scene, str(path))
    other = PaintScene()
    svgio.load_svg(other, str(path))
    got = other.vector_items()[0].sceneBoundingRect()
    # SVG bakes scaled geometry; allow a small rounding tolerance
    assert all(abs(a - b) <= 2 for a, b in zip(target.getRect(),
                                               got.getRect()))


def test_dimension_length_mm():
    from khervepaint.canvas import DimensionItem
    scene = PaintScene(800, 600); scene.dpi = 300
    d = DimensionItem(QLineF(0, 0, 300, 0))     # 300 px = 1 in = 25.4 mm
    scene.addItem(d)
    assert abs(d.length_mm() - 25.4) < 0.1
    longer = DimensionItem(QLineF(0, 0, 600, 0)); scene.addItem(longer)
    assert longer.length_mm() > d.length_mm()    # longer line -> larger mm


def test_dimension_roundtrips(scene, tmp_path):
    from khervepaint.canvas import DimensionItem
    from khervepaint import svgio
    scene.dpi = 300
    scene.addItem(DimensionItem(QLineF(0, 0, 300, 0)))
    # kpaint
    other = PaintScene(800, 600); other.dpi = 300
    document.dict_to_scene(document.scene_to_dict(scene), other)
    d2 = other.vector_items()[0]
    assert isinstance(d2, DimensionItem)
    assert abs(d2.length_mm() - 25.4) < 0.1
    # svg
    path = tmp_path / "dim.svg"
    svgio.save_svg(scene, str(path))
    other2 = PaintScene()
    svgio.load_svg(other2, str(path))
    d3 = other2.vector_items()[0]
    assert isinstance(d3, DimensionItem)
    assert abs(d3.length_mm() - 25.4) < 0.1


def test_dimension_orientation_constraint(scene):
    scene._start = QPointF(10, 10)
    scene.dim_orientation = "horizontal"
    assert scene._dim_constrain(QPointF(50, 80)) == QPointF(50, 10)   # Δx only
    scene.dim_orientation = "vertical"
    assert scene._dim_constrain(QPointF(50, 80)) == QPointF(10, 80)   # Δy only
    scene.dim_orientation = "aligned"
    assert scene._dim_constrain(QPointF(50, 80)) == QPointF(50, 80)   # free


def test_ruler_dropdown_sets_tool_and_defaults(window):
    from khervepaint.canvas import DIMENSION
    window._set_dim_orientation("vertical")
    assert window.scene.tool == DIMENSION
    assert window.scene.dim_orientation == "vertical"
    window._set_dim_cap("dots")
    assert window.scene.tool == DIMENSION
    assert window.scene.dim_cap == "dots"


def test_dimension_label_format():
    from khervepaint.canvas import DimensionItem
    scene = PaintScene(2000, 1500); scene.dpi = 300
    d = DimensionItem(QLineF(0, 0, 118.110236, 0))   # 10 mm at 300 dpi
    scene.addItem(d)
    assert d._label_text() == "10.0 mm"              # defaults
    d.unit = "cm"; d.decimals = 2; d.prefix = "Ø"; d.suffix = " max"
    assert d._label_text() == "Ø1.00 cm max"
    d.unit = "in"; d.decimals = 3; d.prefix = ""; d.suffix = ""
    assert d._label_text() == f"{10 / 25.4:.3f} in"


def test_dimension_style_roundtrips(scene, tmp_path):
    from khervepaint.canvas import DimensionItem
    from khervepaint import svgio
    scene.dpi = 300
    d = DimensionItem(QLineF(0, 0, 300, 0))
    d.cap_style = "ticks"; d.extension = True; d.dash = True
    d.unit = "cm"; d.decimals = 2; d.prefix = "Ø"; d.suffix = " max"
    scene.addItem(d)

    def check(item):
        assert item.cap_style == "ticks" and item.extension is True
        assert item.dash is True and item.unit == "cm"
        assert item.decimals == 2 and item.prefix == "Ø"
        assert item.suffix == " max"

    other = PaintScene(); document.dict_to_scene(document.scene_to_dict(scene),
                                                 other)
    check(other.vector_items()[0])                   # kpaint
    path = tmp_path / "dimstyle.svg"
    svgio.save_svg(scene, str(path))
    other2 = PaintScene(); svgio.load_svg(other2, str(path))
    check(other2.vector_items()[0])                  # svg


def test_snap(scene):
    scene.dpi = 25.4                   # 1 mm == 1 px, for an easy check
    scene.grid_mm = 20                 # -> 20 px spacing
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

    before = img.sceneBoundingRect()
    path = tmp_path / "imgscale.kpaint"
    document.save_kpaint(scene, str(path))
    other = PaintScene(10, 10)
    document.load_kpaint(other, str(path))
    loaded = next(i for i in other.vector_items() if isinstance(i, ImageItem))
    after = loaded.sceneBoundingRect()             # full transform round-trips
    assert abs(after.width() - before.width()) < 0.5
    assert abs(after.height() - before.height()) < 0.5
    assert abs(after.x() - before.x()) < 0.5
    assert abs(after.y() - before.y()) < 0.5


def test_image_resize_snaps_to_grid(scene):
    from khervepaint.handles import SelectionHandles, RESIZE
    from PyQt5.QtGui import QPixmap
    scene.dpi = 25.4                                 # 1 mm == 1 px
    scene.grid_mm = 20                               # -> 20px grid
    scene.snap_enabled = True
    pm = QPixmap(40, 40)
    pm.fill(QColor("#777777"))
    img = ImageItem(pm)
    img.setPos(0, 0)
    scene.addItem(img)
    img.setSelected(True)
    handles = SelectionHandles(scene, img, RESIZE)
    assert handles.kind == "image"
    handles.begin("se", QPointF(40, 40))
    handles.drag("se", QPointF(83, 97))            # snaps to 80, 100
    handles.end()
    br = img.sceneBoundingRect()
    assert round(br.right()) == 80                  # snapped to the grid
    assert round(br.bottom()) == 100


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


def test_ai_chat_hides_code_even_when_truncated():
    from khervepaint.ai_assistant import prose_only, extract_specs
    truncated = ('Here is the wall design!\n\n```json\n[\n'
                 '{"shape":"rect","x":1,"y":2,"w":3,"h":4}')
    assert prose_only(truncated) == "Here is the wall design!"
    assert "shape" not in prose_only(truncated)
    assert len(extract_specs(truncated)) == 1        # shapes still parsed
    # closed fence, bare array, and pure prose
    assert prose_only('Done.\n```json\n[{"shape":"rect"}]\n```') == "Done."
    assert prose_only('Box:\n[{"shape":"rect","x":0,"y":0,"w":5,"h":5}]') \
        == "Box:"
    assert prose_only("Just a question?") == "Just a question?"


def test_svg_use_resolves_defs(tmp_path):
    # Inkscape/matplotlib exports render ticks, markers and text via
    # <use href="#id"> referencing <defs>; these were dropped before.
    from khervepaint import svgio
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 100 100">'
        '<defs><path id="tick" d="M 0,0 L 0,10" style="stroke:#000000"/>'
        '</defs>'
        '<use xlink:href="#tick" x="20" y="5"/>'
        '<use xlink:href="#tick" transform="translate(60,5)"/>'
        '</svg>')
    path = tmp_path / "use.svg"
    path.write_text(svg, encoding="utf-8")
    scene = PaintScene()
    svgio.load_svg(scene, str(path))
    items = scene.vector_items()
    assert len(items) == 2                       # both <use> instances import
    xs = sorted(round(i.sceneBoundingRect().center().x()) for i in items)
    assert xs[0] != xs[1]                         # placed at their offsets


def test_drop_image_files_place_items(window, tmp_path):
    from khervepaint.canvas import ImageItem
    from PyQt5.QtGui import QPixmap, QColor
    paths = []
    for ext in ("png", "bmp"):
        p = tmp_path / f"img.{ext}"
        pm = QPixmap(20, 16); pm.fill(QColor("#3377cc")); pm.save(str(p))
        paths.append(str(p))
    window._on_drop(paths, None, QPointF(30, 40))
    imgs = [i for i in window.scene.vector_items()
            if isinstance(i, ImageItem)]
    assert len(imgs) == 2 and imgs[0].isSelected()


def test_drop_raw_image_data(window):
    from khervepaint.canvas import ImageItem
    from PyQt5.QtGui import QImage, QColor
    img = QImage(12, 12, QImage.Format_ARGB32)
    img.fill(QColor("#aa3333"))
    window._on_drop([], img, QPointF(0, 0))
    assert any(isinstance(i, ImageItem)
               for i in window.scene.vector_items())


def test_svg_grid_metadata_roundtrip(scene, tmp_path):
    from khervepaint import svgio
    scene.grid_mm = 2.5
    scene.show_grid = False
    scene.snap_enabled = False
    scene.infinite = True
    path = tmp_path / "grid.svg"
    svgio.save_svg(scene, str(path))
    other = PaintScene(10, 10)
    svgio.load_svg(other, str(path))
    assert other.grid_mm == 2.5
    assert other.show_grid is False
    assert other.snap_enabled is False
    assert other.infinite is True


def test_object_library_roundtrip(scene, tmp_path, monkeypatch):
    from khervepaint import library
    monkeypatch.setenv("KHERVEPAINT_OBJECTS_DIR", str(tmp_path / "objects"))
    _populated(scene)
    dicts = [document.item_to_dict(i) for i in scene.vector_items()]

    path = library.save_object(dicts, "Wall", dpi=96)
    assert path.exists()
    assert path.name == "Wall.svg"
    assert ("Wall", path) in library.list_objects()

    loaded = library.load_object(path)
    assert len(loaded) == len(dicts)
    types = {d["type"] for d in loaded}
    assert {"line", "rect", "ellipse", "text"} <= types


def test_object_name_is_sanitised(scene, tmp_path, monkeypatch):
    from khervepaint import library
    monkeypatch.setenv("KHERVEPAINT_OBJECTS_DIR", str(tmp_path / "objects"))
    _populated(scene)
    dicts = [document.item_to_dict(i) for i in scene.vector_items()]
    path = library.save_object(dicts, "wall/../x?:y", dpi=96)
    # Path separators and illegal chars are stripped to a safe stem.
    assert "/" not in path.stem and ":" not in path.stem
    assert path.exists()


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
    scene.snap_enabled = False                # test drag mechanics, not snap
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
    scene.snap_enabled = False                # test drag mechanics, not snap
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
    scene.snap_enabled = False                # test drag mechanics, not snap
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


def test_crop_freezes_image_then_restores(app):
    from PyQt5.QtWidgets import QGraphicsItem
    from PyQt5.QtGui import QPixmap
    scene = PaintScene(200, 200)
    pm = QPixmap(40, 30)
    pm.fill(QColor("#00aa00"))
    img = ImageItem(pm)
    scene.addItem(img)
    assert img.flags() & QGraphicsItem.ItemIsMovable

    scene.begin_crop(img)
    assert not (img.flags() & QGraphicsItem.ItemIsMovable)
    assert not (img.flags() & QGraphicsItem.ItemIsSelectable)
    scene._crop.rect = QRectF(5, 5, 20, 15)
    scene.apply_crop()
    assert img.pixmap().width() == 20
    # move/select restored after cropping
    assert img.flags() & QGraphicsItem.ItemIsMovable
    assert img.flags() & QGraphicsItem.ItemIsSelectable


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


def test_ai_extract_truncated_json():
    from khervepaint.ai_assistant import extract_specs
    # a long reply cut off mid-array (no closing ]/```): salvage what's whole
    reply = ('Here you go:\n```json\n'
             '[{"shape":"rect","x":0,"y":0,"w":10,"h":10},\n'
             '{"shape":"circle","x":5,"y":5,"w":8,"h":8},\n'
             '{"shape":"rect","x":9')
    specs = extract_specs(reply)
    assert len(specs) == 2                       # two complete objects salvaged
    assert specs[0]["shape"] == "rect"
    assert specs[1]["shape"] == "circle"


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


def test_new_window_opens_independent_window(window):
    cls = type(window)
    win2 = window.new_window()
    assert win2 is not window
    assert win2.scene is not window.scene          # independent document
    assert win2 in cls._windows                    # tracked so it survives
    win2._undo_stack.setClean()
    win2.close()                                   # closeEvent untracks it
    assert win2 not in cls._windows
    from PyQt5 import sip
    sip.delete(win2)


def test_settings_isolated_from_real_store():
    """Guard: the suite must never read/write the developer's real
    KhervePaint settings (registry on Windows) — conftest redirects all
    app QSettings to a throwaway temp file."""
    from khervepaint import ai_assistant, mainwindow, style
    for mod in (ai_assistant, mainwindow, style):
        name = mod.QSettings("Kherve", "KhervePaint").fileName()
        assert name.endswith("settings.ini"), name
        assert "HKEY" not in name.upper(), name


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


def test_ai_input_history_recall(window):
    dock = window.ai_dock
    dock._sent = ["first prompt", "second prompt"]   # simulate two sent
    dock.input.setPlainText("draft")
    dock._history_prev()                              # Up -> newest
    assert dock.input.toPlainText() == "second prompt"
    dock._history_prev()                              # Up -> older
    assert dock.input.toPlainText() == "first prompt"
    dock._history_prev()                              # Up -> stays at oldest
    assert dock.input.toPlainText() == "first prompt"
    dock._history_next()                              # Down -> newer
    assert dock.input.toPlainText() == "second prompt"
    dock._history_next()                              # Down past newest -> draft
    assert dock.input.toPlainText() == "draft"


def test_ai_busy_shows_thinking_and_stop(window):
    dock = window.ai_dock
    dock._busy(True)
    assert dock._is_busy
    assert not dock.thinking_label.isHidden()
    assert dock.send_btn.toolTip() == "Stop"
    # a send is ignored while a request is in flight
    before = len(dock._history)
    dock.input.setPlainText("ignored while busy")
    dock._send()
    assert len(dock._history) == before
    # stopping clears the busy state
    dock._stop()
    assert not dock._is_busy
    assert dock.thinking_label.isHidden()
    assert dock.send_btn.toolTip() == "Send"


def test_ai_history_persists(window):
    dock = window.ai_dock
    dock._history = [{"role": "user", "content": "remember this"},
                     {"role": "assistant", "content": "ok ```json\n[]```"}]
    dock._save_history()
    # a fresh load (as on app restart) restores the conversation
    dock._history = []
    dock._sent = []
    dock._load_history()
    assert dock._history[0]["content"] == "remember this"
    assert dock._sent == ["remember this"]
    assert "remember this" in dock.transcript.toPlainText()
    assert "json" not in dock.transcript.toPlainText().lower()  # JSON hidden
    dock._clear()                                # reset stored history


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
    from khervepaint import canvassize
    dlg = canvassize.CanvasSizeDialog(current=(800, 600), dpi=96)
    # the ACS single column preset is the first non-Custom entry
    dlg.preset_combo.setCurrentIndex(1)
    dlg._apply_preset(1)
    mode, pw, ph, dpi = dlg.result_value()
    assert mode == "size"
    assert dpi == 300
    # ACS single column = 3.25 in, now specified in mm (~975 x 750 px)
    assert abs(pw - round(3.25 * 300)) <= 1
    assert abs(ph - round(2.50 * 300)) <= 1


def test_default_size_is_acs_single_column(app):
    from khervepaint import canvassize
    w, h, dpi = canvassize.default_size()
    assert dpi == 300
    assert abs(w - round(3.25 * 300)) <= 1      # ~975 px
    assert abs(h - round(2.50 * 300)) <= 1      # ~750 px


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
    from khervepaint import canvassize
    default_w = canvassize.default_size()[0]
    s = window.scene
    assert s.sceneRect().width() == default_w   # new docs open at the default
    s.addItem(RectItem(QRectF(0, 0, 10, 10)))
    s.changed_by_user.emit()                    # baseline (the add)
    s.resize_canvas(1234, 567)
    assert s.sceneRect().width() == 1234
    window._undo_stack.undo()                   # undo the resize
    assert s.sceneRect().width() == default_w   # back to the default


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


# ------------------------------------------------------------ examples
def test_examples_registry_covers_techniques():
    from khervepaint import examples
    names = " ".join(n for _, n, _ in examples.EXAMPLES)
    for tech in ("XPS", "UPS", "AES", "XRD", "LEED", "FTIR", "Raman",
                 "UV-Vis", "NMR", "TGA", "DSC", "BET", "TEM", "SEM", "AFM",
                 "STM", "XRF", "SIMS", "ICP-MS", "GC-MS", "HPLC"):
        assert tech in names, tech
    assert len(examples.EXAMPLES) >= 20
    # categories appear in the intended menu order
    cats = [c for c, _, _ in examples.EXAMPLES]
    assert cats == sorted(cats, key=lambda c: examples._ORDER.index(c))
    # every entry has a callable builder and a category
    for cat, name, builder in examples.EXAMPLES:
        assert cat and name and callable(builder)


def test_examples_build_real_items(app):
    from khervepaint import examples
    from khervepaint.ai_assistant import apply_specs
    scene = PaintScene(examples.PAGE_W, examples.PAGE_H)
    for _, name, builder in examples.EXAMPLES:
        scene.new_document(examples.PAGE_W, examples.PAGE_H)
        specs = builder()
        items = apply_specs(scene, specs)
        # almost every spec should become an item (allow a stray skip)
        assert len(items) >= len(specs) - 1, name
        assert len(items) > 15, name           # a detailed schematic
        # drawn geometry sits inside the A4 page (text width is
        # font-dependent and unreliable headless, so skip text extents)
        for it in items:
            r = it.sceneBoundingRect()
            assert r.left() > -5 and r.top() > -5, name
            if not isinstance(it, TextItem):
                assert r.right() < examples.PAGE_W + 5, name
                assert r.bottom() < examples.PAGE_H + 5, name


def test_example_spec_rotation_is_applied(app):
    from khervepaint.ai_assistant import apply_specs
    scene = PaintScene(400, 400)
    items = apply_specs(scene, [{"shape": "triangle", "x": 50, "y": 50,
                                 "w": 40, "h": 40, "rotation": 180}])
    assert abs(items[0].rotation() - 180) < 0.01


def test_load_example_resets_document(window):
    from khervepaint import examples
    builder = examples.EXAMPLES[0][2]
    window.load_example(builder, "test")
    assert window.scene.sceneRect().width() == examples.PAGE_W
    assert window.scene.dpi == examples.PAGE_DPI
    assert window._path is None
    assert len(window.scene.vector_items()) > 5
    assert window._undo_stack.isClean()        # loaded as the clean baseline
