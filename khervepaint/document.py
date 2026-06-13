""".kpaint (de)serialisation and PNG import/export.

`.kpaint` is JSON: format/version header, canvas size, grid settings,
the raster layer as a base64 PNG, and the vector items (recursively
through groups). All item properties must round-trip — when adding a
property, update item_to_dict() and item_from_dict() together and
extend the round-trip test.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import base64
import json

from PyQt5.QtCore import (QBuffer, QByteArray, QLineF, QMarginsF, QPointF,
                          QRectF, QSize, QSizeF, Qt)
from PyQt5.QtGui import (QBrush, QColor, QFont, QImage, QPageSize, QPainter,
                         QPainterPath, QPdfWriter, QPen, QPixmap, QPolygonF)
from PyQt5.QtSvg import QSvgGenerator

from .canvas import (ArrowItem, EllipseItem, GroupItem, ImageItem, LineItem,
                     PaintScene, PathItem, PolygonItem, RectItem,
                     RoundedRectItem, TextItem, center_origin)

FORMAT_VERSION = 1


# ---------------------------------------------------------------- pens
def _pen_to_dict(pen: QPen) -> dict:
    return {"color": pen.color().name(QColor.HexArgb),
            "width": pen.widthF()}


def _pen_from_dict(d: dict) -> QPen:
    pen = QPen(QColor(d.get("color", "#ff1a1a1a")), d.get("width", 2))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _brush_to_dict(brush: QBrush):
    if brush.style() == Qt.NoBrush:
        return None
    return {"color": brush.color().name(QColor.HexArgb)}


def _brush_from_dict(d) -> QBrush:
    if not d:
        return QBrush(Qt.NoBrush)
    return QBrush(QColor(d.get("color", "#ff4aa3ff")))


# ---------------------------------------------------------------- paths
def painterpath_to_cmds(path: QPainterPath) -> list:
    """A QPainterPath as a JSON-friendly command list (M/L/C)."""
    cmds, i = [], 0
    while i < path.elementCount():
        e = path.elementAt(i)
        if e.isMoveTo():
            cmds.append(["M", e.x, e.y])
            i += 1
        elif e.isLineTo():
            cmds.append(["L", e.x, e.y])
            i += 1
        else:                                   # curve: e + 2 data points
            c2, ep = path.elementAt(i + 1), path.elementAt(i + 2)
            cmds.append(["C", e.x, e.y, c2.x, c2.y, ep.x, ep.y])
            i += 3
    return cmds


def cmds_to_painterpath(cmds: list) -> QPainterPath:
    path = QPainterPath()
    for c in cmds:
        if c[0] == "M":
            path.moveTo(c[1], c[2])
        elif c[0] == "L":
            path.lineTo(c[1], c[2])
        elif c[0] == "C":
            path.cubicTo(c[1], c[2], c[3], c[4], c[5], c[6])
    return path


# ---------------------------------------------------------------- items
def item_to_dict(item) -> dict:
    pos = {"x": item.pos().x(), "y": item.pos().y()}
    common = {"pos": pos, "opacity": item.opacity(),
              "rotation": item.rotation(), "z": item.zValue()}
    if isinstance(item, ArrowItem):
        ln = item.line()
        return {"type": "arrow", "pen": _pen_to_dict(item.pen()),
                "x1": ln.x1(), "y1": ln.y1(), "x2": ln.x2(), "y2": ln.y2(),
                **common}
    if isinstance(item, LineItem):
        ln = item.line()
        return {"type": "line", "pen": _pen_to_dict(item.pen()),
                "x1": ln.x1(), "y1": ln.y1(), "x2": ln.x2(), "y2": ln.y2(),
                **common}
    if isinstance(item, RoundedRectItem):
        r = item.rect()
        return {"type": "roundrect", "pen": _pen_to_dict(item.pen()),
                "brush": _brush_to_dict(item.brush()), "radius": item.radius(),
                "x": r.x(), "y": r.y(), "w": r.width(), "h": r.height(),
                **common}
    if isinstance(item, PolygonItem):
        return {"type": "polygon", "pen": _pen_to_dict(item.pen()),
                "brush": _brush_to_dict(item.brush()), "kind": item.kind,
                "points": [[p.x(), p.y()] for p in item.polygon()],
                **common}
    if isinstance(item, PathItem):
        return {"type": "path", "pen": _pen_to_dict(item.pen()),
                "brush": _brush_to_dict(item.brush()),
                "cmds": painterpath_to_cmds(item.path()), **common}
    if isinstance(item, ImageItem):
        return {"type": "image", "image": _pixmap_to_b64(item.pixmap()),
                **common}
    if isinstance(item, (RectItem, EllipseItem)):
        r = item.rect()
        return {"type": "rect" if isinstance(item, RectItem) else "ellipse",
                "pen": _pen_to_dict(item.pen()),
                "brush": _brush_to_dict(item.brush()),
                "x": r.x(), "y": r.y(), "w": r.width(), "h": r.height(),
                **common}
    if isinstance(item, TextItem):
        return {"type": "text", "text": item.toPlainText(),
                "color": item.defaultTextColor().name(QColor.HexArgb),
                "family": item.font().family(),
                "size": item.font().pointSize(),
                "bold": item.font().bold(),
                "italic": item.font().italic(), **common}
    if isinstance(item, GroupItem):
        from .handles import Handle
        return {"type": "group",
                "children": [item_to_dict(c) for c in item.childItems()
                             if not isinstance(c, Handle)],
                **common}
    raise ValueError(f"unserialisable item: {type(item).__name__}")


def item_from_dict(d: dict):
    kind = d.get("type")
    if kind in ("line", "arrow"):
        cls = ArrowItem if kind == "arrow" else LineItem
        item = cls(QLineF(d["x1"], d["y1"], d["x2"], d["y2"]))
        item.setPen(_pen_from_dict(d.get("pen", {})))
    elif kind in ("rect", "ellipse"):
        cls = RectItem if kind == "rect" else EllipseItem
        item = cls(QRectF(d["x"], d["y"], d["w"], d["h"]))
        item.setPen(_pen_from_dict(d.get("pen", {})))
        item.setBrush(_brush_from_dict(d.get("brush")))
    elif kind == "roundrect":
        item = RoundedRectItem(QRectF(d["x"], d["y"], d["w"], d["h"]),
                               d.get("radius", 12))
        item.setPen(_pen_from_dict(d.get("pen", {})))
        item.setBrush(_brush_from_dict(d.get("brush")))
    elif kind == "polygon":
        poly = QPolygonF([QPointF(x, y) for x, y in d.get("points", [])])
        item = PolygonItem(poly, kind=d.get("kind", "polygon"))
        item.setPen(_pen_from_dict(d.get("pen", {})))
        item.setBrush(_brush_from_dict(d.get("brush")))
    elif kind == "path":
        item = PathItem(cmds_to_painterpath(d.get("cmds", [])))
        item.setPen(_pen_from_dict(d.get("pen", {})))
        item.setBrush(_brush_from_dict(d.get("brush")))
    elif kind == "image":
        item = ImageItem(_pixmap_from_b64(d["image"]))
    elif kind == "text":
        item = TextItem(d.get("text", ""))
        item.setDefaultTextColor(QColor(d.get("color", "#ff1a1a1a")))
        font = QFont(d.get("family", "Segoe UI"), d.get("size", 14))
        font.setBold(d.get("bold", False))
        font.setItalic(d.get("italic", False))
        item.setFont(font)
    elif kind == "group":
        item = GroupItem()
        for child_dict in d.get("children", []):
            child = item_from_dict(child_dict)
            child.setParentItem(item)
    else:
        raise ValueError(f"unknown item type: {kind!r}")
    pos = d.get("pos", {})
    item.setPos(pos.get("x", 0), pos.get("y", 0))
    item.setOpacity(d.get("opacity", 1.0))
    center_origin(item)          # rotate about centre, matching how it saved
    item.setRotation(d.get("rotation", 0.0))
    item.setZValue(d.get("z", 0.0))
    return item


# ---------------------------------------------------------------- raster
def _pixmap_to_b64(pixmap: QPixmap) -> str:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()
    return base64.b64encode(bytes(data)).decode("ascii")


def _pixmap_from_b64(text: str) -> QPixmap:
    pixmap = QPixmap()
    pixmap.loadFromData(base64.b64decode(text), "PNG")
    return pixmap


# ---------------------------------------------------------------- files
def scene_to_dict(scene: PaintScene) -> dict:
    rect = scene.sceneRect()
    return {"format": "kpaint", "version": FORMAT_VERSION,
            "width": int(rect.width()), "height": int(rect.height()),
            "grid": {"size": scene.grid_size, "show": scene.show_grid,
                     "snap": scene.snap_enabled},
            "raster": _pixmap_to_b64(scene.raster_item.pixmap()),
            "items": [item_to_dict(i) for i in scene.vector_items()]}


def dict_to_scene(data: dict, scene: PaintScene):
    if data.get("format") != "kpaint":
        raise ValueError("not a .kpaint document")
    scene.new_document(data.get("width", 800), data.get("height", 600))
    grid = data.get("grid", {})
    scene.grid_size = grid.get("size", 20)
    scene.show_grid = grid.get("show", True)
    scene.snap_enabled = grid.get("snap", True)
    if data.get("raster"):
        scene.set_raster_pixmap(_pixmap_from_b64(data["raster"]))
    for item_dict in data.get("items", []):
        scene.addItem(item_from_dict(item_dict))


def save_kpaint(scene: PaintScene, path: str):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(scene_to_dict(scene), fh, indent=1)


def load_kpaint(scene: PaintScene, path: str):
    with open(path, encoding="utf-8") as fh:
        dict_to_scene(json.load(fh), scene)


def open_png(scene: PaintScene, path: str):
    """Load *path* into the raster layer, resizing the canvas to fit."""
    pixmap = QPixmap(path)
    if pixmap.isNull():
        raise ValueError(f"cannot read image: {path}")
    scene.set_raster_pixmap(pixmap)


def export_png(scene: PaintScene, path: str):
    """Render raster + vector layers flattened to a PNG (no grid)."""
    scene.clearSelection()
    rect = scene.sceneRect()
    image = QImage(int(rect.width()), int(rect.height()),
                   QImage.Format_ARGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    scene.render(painter, target=QRectF(image.rect()), source=rect)
    painter.end()
    if not image.save(path, "PNG"):
        raise ValueError(f"cannot write image: {path}")


def export_svg(scene: PaintScene, path: str):
    """Render raster + vector layers to an SVG (raster embedded)."""
    scene.clearSelection()
    rect = scene.sceneRect()
    generator = QSvgGenerator()
    generator.setFileName(path)
    generator.setSize(QSize(int(rect.width()), int(rect.height())))
    generator.setViewBox(QRectF(0, 0, rect.width(), rect.height()))
    generator.setTitle("KhervePaint export")
    painter = QPainter(generator)
    painter.setRenderHint(QPainter.Antialiasing)
    scene.render(painter, source=rect)
    painter.end()


def export_pdf(scene: PaintScene, path: str):
    """Render to a single-page PDF sized to the canvas (96 dpi)."""
    scene.clearSelection()
    rect = scene.sceneRect()
    writer = QPdfWriter(path)
    writer.setResolution(96)
    # Page size is in points (1/72 inch); the canvas is in 96-dpi px.
    writer.setPageSize(QPageSize(
        QSizeF(rect.width() * 72 / 96, rect.height() * 72 / 96),
        QPageSize.Point))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))
    painter = QPainter(writer)
    painter.setRenderHint(QPainter.Antialiasing)
    scene.render(painter,
                 target=QRectF(0, 0, writer.width(), writer.height()),
                 source=rect)
    painter.end()
