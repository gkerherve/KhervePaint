"""Selection handles: resize a shape, or double-click to rotate it.

Selecting a single item (pointer tool) shows **resize** handles:

* line / arrow → a handle at each endpoint,
* polygon → a handle at each vertex,
* rect / ellipse / rounded-rect → eight bounding-box handles,
* everything else (path / image / text / group) → four corner handles
  that scale the item uniformly.

Double-clicking an item switches it to **rotate** mode: a knob above
the centre that spins the item about its own centre.  The scene owns a
single `SelectionHandles` instance for the active item; handles are
parented to that item (so they follow it) and are never serialised.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPen, QPolygonF
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                             QGraphicsLineItem, QGraphicsRectItem)

from .canvas import (ArcShapeItem, EllipseItem, LineItem, PolygonItem,
                     RectItem, RoundedRectItem, center_origin)

HANDLE_SIZE = 9
RESIZE, ROTATE = "resize", "rotate"

_BLUE = QColor("#2176c7")
_GREEN = QColor("#2e9e5b")
_WHITE = QColor("#ffffff")

_BOX_CURSORS = {
    "nw": Qt.SizeFDiagCursor, "se": Qt.SizeFDiagCursor,
    "ne": Qt.SizeBDiagCursor, "sw": Qt.SizeBDiagCursor,
    "n": Qt.SizeVerCursor, "s": Qt.SizeVerCursor,
    "e": Qt.SizeHorCursor, "w": Qt.SizeHorCursor,
}


class Handle:
    """Marker base so handles can be filtered out everywhere."""


class _GuideLine(Handle, QGraphicsLineItem):
    """Non-interactive dashed line from centre to the rotate knob."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAcceptedMouseButtons(Qt.NoButton)


class _RectHandle(Handle, QGraphicsRectItem):
    def __init__(self, controller, role, parent, color, cursor):
        super().__init__(parent)
        s = HANDLE_SIZE
        self.setRect(-s / 2, -s / 2, s, s)
        self._init(controller, role, color, cursor)

    def _init(self, controller, role, color, cursor):
        self.controller = controller
        self.role = role
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.setZValue(1000)
        self.setPen(QPen(color, 0))
        self.setBrush(QBrush(_WHITE))
        self.setCursor(cursor)

    def mousePressEvent(self, event):
        self.controller.begin(self.role, event.scenePos())
        event.accept()

    def mouseMoveEvent(self, event):
        self.controller.drag(self.role, event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event):
        self.controller.end()
        event.accept()


class _RotateHandle(Handle, QGraphicsEllipseItem):
    def __init__(self, controller, parent):
        super().__init__(parent)
        s = HANDLE_SIZE + 2
        self.setRect(-s / 2, -s / 2, s, s)
        self.controller = controller
        self.role = "rotate"
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, True)
        self.setZValue(1000)
        self.setPen(QPen(_GREEN, 0))
        self.setBrush(QBrush(_GREEN))
        self.setCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        self.controller.begin(self.role, event.scenePos())
        event.accept()

    def mouseMoveEvent(self, event):
        self.controller.drag(self.role, event.scenePos())
        event.accept()

    def mouseReleaseEvent(self, event):
        self.controller.end()
        event.accept()


def _kind_of(item, mode: str) -> str:
    if mode == ROTATE:
        return "rotate"
    if isinstance(item, LineItem):
        return "line"
    if isinstance(item, PolygonItem):
        return "polygon"
    if isinstance(item, (RectItem, EllipseItem, RoundedRectItem,
                         ArcShapeItem)):
        return "box"
    return "scale"


class SelectionHandles:
    """The set of handles around one item, in resize or rotate mode."""

    def __init__(self, scene, item, mode):
        self.scene = scene
        self.item = item
        self.mode = mode
        self.kind = _kind_of(item, mode)
        self.handles = []
        self._guide = None
        self._scale_base = 1.0
        self._scale_dist = 1.0
        self._build()
        self.reposition()

    # ------------------------------------------------------------ build
    def _build(self):
        if self.kind == "rotate":
            self._guide = _GuideLine(self.item)
            self._guide.setPen(QPen(_GREEN, 0, Qt.DashLine))
            self._guide.setZValue(999)
            self.handles = [_RotateHandle(self, self.item)]
        elif self.kind == "line":
            self.handles = [self._rect_handle(r) for r in ("p1", "p2")]
        elif self.kind == "polygon":
            count = self.item.polygon().count()
            self.handles = [self._rect_handle(i) for i in range(count)]
        elif self.kind == "box":
            self.handles = [self._rect_handle(r, _BOX_CURSORS[r])
                            for r in _BOX_CURSORS]
        else:                       # scale
            self.handles = [self._rect_handle(r, _BOX_CURSORS[r])
                            for r in ("nw", "ne", "se", "sw")]

    def _rect_handle(self, role, cursor=Qt.SizeAllCursor):
        return _RectHandle(self, role, self.item, _BLUE, cursor)

    # ------------------------------------------------------------ layout
    def reposition(self):
        if self.kind == "rotate":
            br = self.item.boundingRect()
            knob = QPointF(br.center().x(), br.top() - 22)
            self.handles[0].setPos(knob)
            self._guide.setLine(QLineF(br.center(), knob))
            return
        for handle in self.handles:
            handle.setPos(self._anchor(handle.role))

    def _anchor(self, role) -> QPointF:
        if self.kind == "line":
            ln = self.item.line()
            return ln.p1() if role == "p1" else ln.p2()
        if self.kind == "polygon":
            return self.item.polygon().at(role)
        rect = self.item.rect() if self.kind == "box" \
            else self.item.boundingRect()
        table = {
            "nw": rect.topLeft(), "ne": rect.topRight(),
            "se": rect.bottomRight(), "sw": rect.bottomLeft(),
            "n": QPointF(rect.center().x(), rect.top()),
            "s": QPointF(rect.center().x(), rect.bottom()),
            "e": QPointF(rect.right(), rect.center().y()),
            "w": QPointF(rect.left(), rect.center().y()),
        }
        return table[role]

    # ------------------------------------------------------------ drag
    def begin(self, role, scene_pos):
        self.item.setSelected(True)
        if self.kind in ("rotate", "scale"):
            center_origin(self.item)
            self._center = self.item.mapToScene(
                self.item.transformOriginPoint())
        if self.kind == "scale":
            self._scale_base = self.item.scale() or 1.0
            self._scale_dist = max(_dist(scene_pos, self._center), 1.0)

    def drag(self, role, scene_pos):
        snapped = self.scene.snap(scene_pos) \
            if getattr(self.scene, "snap_enabled", False) else scene_pos
        local = self.item.mapFromScene(snapped)
        if self.kind == "rotate":
            self._rotate(scene_pos)
        elif self.kind == "scale":
            self._scale(scene_pos)
        elif self.kind == "line":
            self._drag_line(role, local)
        elif self.kind == "polygon":
            self._drag_vertex(role, local)
        elif self.kind == "box":
            self._drag_box(role, local)
        self.reposition()

    def end(self):
        self.scene.changed_by_user.emit()

    def remove(self):
        for handle in self.handles:
            if handle.scene() is not None:
                handle.scene().removeItem(handle)
        if self._guide is not None and self._guide.scene() is not None:
            self._guide.scene().removeItem(self._guide)
        self.handles = []
        self._guide = None

    # ------------------------------------------------------------ edits
    def _rotate(self, scene_pos):
        v = scene_pos - self._center
        angle = math.degrees(math.atan2(v.y(), v.x())) + 90
        if getattr(self.scene, "snap_enabled", False):
            angle = round(angle / 15) * 15
        self.item.setRotation(angle)

    def _scale(self, scene_pos):
        factor = _dist(scene_pos, self._center) / self._scale_dist
        self.item.setScale(max(self._scale_base * factor, 0.05))

    def _drag_line(self, role, local):
        ln = self.item.line()
        if role == "p1":
            ln.setP1(local)
        else:
            ln.setP2(local)
        self.item.setLine(ln)

    def _drag_vertex(self, index, local):
        poly = QPolygonF(self.item.polygon())
        poly.replace(index, local)
        self.item.setPolygon(poly)
        if self.item.rotation() == 0:
            center_origin(self.item)

    def _drag_box(self, role, local):
        r = QRectF(self.item.rect())
        if "n" in role:
            r.setTop(local.y())
        if "s" in role:
            r.setBottom(local.y())
        if "w" in role:
            r.setLeft(local.x())
        if "e" in role:
            r.setRight(local.x())
        r = r.normalized()
        if r.width() < 1:
            r.setWidth(1)
        if r.height() < 1:
            r.setHeight(1)
        if isinstance(self.item, RoundedRectItem):
            self.item.set_rect(r)
        else:
            self.item.setRect(r)
        if self.item.rotation() == 0:
            center_origin(self.item)


def _dist(a: QPointF, b: QPointF) -> float:
    return math.hypot(a.x() - b.x(), a.y() - b.y())
