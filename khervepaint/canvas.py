"""Canvas: raster layer + vector items in one QGraphicsScene.

The raster layer is a QGraphicsPixmapItem pinned at z=-10 — "Open
PNG" loads into it and the pencil tool paints into its pixmap.
Vector tools (line, rect, circle, ellipse, text) create snap-aware
QGraphicsItem subclasses on top, edited with the pointer tool.
The grid is drawn in the view's foreground so it never ends up in
exported PNGs.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QLineF, QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import (QBrush, QColor, QFont, QPainter, QPainterPath,
                         QPen, QPixmap, QPolygonF, QTextCursor)
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                             QGraphicsItemGroup, QGraphicsLineItem,
                             QGraphicsPathItem, QGraphicsPixmapItem,
                             QGraphicsPolygonItem, QGraphicsRectItem,
                             QGraphicsScene, QGraphicsTextItem,
                             QGraphicsView)

# Tool identifiers.
POINTER, PENCIL, LINE, RECT, CIRCLE, ELLIPSE, TEXT = (
    "pointer", "pencil", "line", "rect", "circle", "ellipse", "text")
BUCKET = "bucket"
ARROW, ROUNDRECT = "arrow", "roundrect"
TRIANGLE, DIAMOND, PENTAGON, HEXAGON, STAR = (
    "triangle", "diamond", "pentagon", "hexagon", "star")

#: Parametric polygons created by dragging a bounding rect.
POLYGON_KINDS = (TRIANGLE, DIAMOND, PENTAGON, HEXAGON, STAR)
#: Tools defined by two points (drag start -> end).
_TWO_POINT_TOOLS = (LINE, ARROW)
#: Tools defined by a dragged bounding rect.
_RECT_TOOLS = (RECT, CIRCLE, ELLIPSE, ROUNDRECT) + POLYGON_KINDS
#: Tools that rubber-band a new vector item between press and release.
_SHAPE_TOOLS = _TWO_POINT_TOOLS + _RECT_TOOLS

_ITEM_FLAGS = (QGraphicsItem.ItemIsSelectable
               | QGraphicsItem.ItemIsMovable
               | QGraphicsItem.ItemSendsGeometryChanges)


class SnapMixin:
    """Snaps the item's position to the scene grid while it is moved."""

    def itemChange(self, change, value):
        if (change == QGraphicsItem.ItemPositionChange
                and self.scene() is not None
                and getattr(self.scene(), "snap_enabled", False)):
            value = self.scene().snap(value)
        return super().itemChange(change, value)


HANDLE_SIZE = 10


class EndpointHandle(QGraphicsRectItem):
    """Drag handle pinned to one end of a LineItem.

    Dragging is handled manually (grab on press) instead of via
    ItemIsMovable so the parent line keeps its selection while the
    handle is dragged.
    """

    def __init__(self, line_item: "LineItem", index: int):
        s = HANDLE_SIZE
        super().__init__(-s / 2, -s / 2, s, s, line_item)
        self._line_item = line_item
        self.index = index
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setPen(QPen(QColor("#2176c7"), 0))
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setCursor(Qt.SizeAllCursor)
        self.setZValue(10)
        self.hide()

    def mousePressEvent(self, event):
        # Clicking a non-selectable item cleared the scene selection —
        # restore it so the handles stay visible during the drag.
        self._line_item.setSelected(True)
        event.accept()

    def mouseMoveEvent(self, event):
        scene_pos = event.scenePos()
        if self.scene() is not None and self.scene().snap_enabled:
            scene_pos = self.scene().snap(scene_pos)
        pos = self._line_item.mapFromScene(scene_pos)
        self.setPos(pos)
        self._line_item.endpoint_moved(self.index, pos)

    def mouseReleaseEvent(self, event):
        if self.scene() is not None:
            self.scene().changed_by_user.emit()
        event.accept()


class LineItem(SnapMixin, QGraphicsLineItem):
    def __init__(self, *a):
        super().__init__(*a)
        self.setFlags(_ITEM_FLAGS)
        self._handles = None

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self._show_handles(bool(value))
        return super().itemChange(change, value)

    def _show_handles(self, show: bool):
        if show and self._handles is None:
            self._handles = (EndpointHandle(self, 0),
                             EndpointHandle(self, 1))
        if self._handles is not None:
            self.sync_handles()
            for handle in self._handles:
                handle.setVisible(show)

    def sync_handles(self):
        if self._handles is not None:
            self._handles[0].setPos(self.line().p1())
            self._handles[1].setPos(self.line().p2())

    def endpoint_moved(self, index: int, pos):
        ln = self.line()
        (ln.setP1 if index == 0 else ln.setP2)(pos)
        self.setLine(ln)


class RectItem(SnapMixin, QGraphicsRectItem):
    def __init__(self, *a):
        super().__init__(*a)
        self.setFlags(_ITEM_FLAGS)


class EllipseItem(SnapMixin, QGraphicsEllipseItem):
    def __init__(self, *a):
        super().__init__(*a)
        self.setFlags(_ITEM_FLAGS)


class ArrowItem(LineItem):
    """A line with a filled arrowhead at the second endpoint."""

    HEAD = 14

    def boundingRect(self):
        h = self.HEAD + self.pen().widthF()
        return super().boundingRect().adjusted(-h, -h, h, h)

    def _head_polygon(self) -> QPolygonF:
        ln = self.line()
        angle = math.atan2(ln.dy(), ln.dx())
        tip = ln.p2()
        left = tip - QPointF(math.cos(angle - math.pi / 7) * self.HEAD,
                             math.sin(angle - math.pi / 7) * self.HEAD)
        right = tip - QPointF(math.cos(angle + math.pi / 7) * self.HEAD,
                              math.sin(angle + math.pi / 7) * self.HEAD)
        return QPolygonF([tip, left, right])

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.line().length() < 1:
            return
        painter.setPen(QPen(self.pen().color(), self.pen().widthF()))
        painter.setBrush(QBrush(self.pen().color()))
        painter.drawPolygon(self._head_polygon())


def polygon_for_kind(kind: str, rect: QRectF) -> QPolygonF:
    """Vertices of a parametric polygon *kind* inscribed in *rect*."""
    cx, cy = rect.center().x(), rect.center().y()
    rx, ry = rect.width() / 2, rect.height() / 2
    if kind == TRIANGLE:
        pts = [(cx, rect.top()), (rect.right(), rect.bottom()),
               (rect.left(), rect.bottom())]
    elif kind == DIAMOND:
        pts = [(cx, rect.top()), (rect.right(), cy),
               (cx, rect.bottom()), (rect.left(), cy)]
    elif kind == STAR:
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            scale = 1.0 if i % 2 == 0 else 0.4
            pts.append((cx + rx * scale * math.cos(ang),
                        cy + ry * scale * math.sin(ang)))
    else:
        sides = 5 if kind == PENTAGON else 6
        pts = []
        for i in range(sides):
            ang = -math.pi / 2 + i * 2 * math.pi / sides
            pts.append((cx + rx * math.cos(ang), cy + ry * math.sin(ang)))
    return QPolygonF([QPointF(x, y) for x, y in pts])


class PolygonItem(SnapMixin, QGraphicsPolygonItem):
    """Free or parametric polygon. *kind* is kept for display only;
    geometry is always the vertex list, so SVG-imported polygons and
    triangle/star/etc. behave identically."""

    def __init__(self, polygon=None, kind="polygon"):
        super().__init__(QPolygonF(polygon) if polygon else QPolygonF())
        self.setFlags(_ITEM_FLAGS)
        self.kind = kind

    def set_rect(self, rect: QRectF):
        self.setPolygon(polygon_for_kind(self.kind, rect))


class RoundedRectItem(SnapMixin, QGraphicsPathItem):
    """A rectangle with rounded corners (radius is a real property)."""

    def __init__(self, rect=None, radius: float = 12.0):
        super().__init__()
        self.setFlags(_ITEM_FLAGS)
        self._rect = QRectF(rect) if rect else QRectF()
        self._radius = radius
        self._rebuild()

    def rect(self) -> QRectF:
        return QRectF(self._rect)

    def set_rect(self, rect: QRectF):
        self._rect = QRectF(rect)
        self._rebuild()

    def radius(self) -> float:
        return self._radius

    def set_radius(self, radius: float):
        self._radius = radius
        self._rebuild()

    def _rebuild(self):
        path = QPainterPath()
        r = min(self._radius, self._rect.width() / 2, self._rect.height() / 2)
        path.addRoundedRect(self._rect, r, r)
        self.setPath(path)


class PathItem(SnapMixin, QGraphicsPathItem):
    """An arbitrary vector path — the import target for SVG <path> and
    for elements carrying a non-trivial (scaled/sheared) transform."""

    def __init__(self, path=None):
        super().__init__(path if path else QPainterPath())
        self.setFlags(_ITEM_FLAGS)


class ImageItem(SnapMixin, QGraphicsPixmapItem):
    """A pasted/placed bitmap living on the vector layer (movable)."""

    def __init__(self, pixmap=None):
        super().__init__(pixmap if pixmap else QPixmap())
        self.setFlags(_ITEM_FLAGS)
        self.setTransformationMode(Qt.SmoothTransformation)


class GroupItem(SnapMixin, QGraphicsItemGroup):
    def __init__(self):
        super().__init__()
        self.setFlags(_ITEM_FLAGS)


class TextItem(SnapMixin, QGraphicsTextItem):
    """Vector text — double-click to edit inline."""

    def __init__(self, text: str = "Text"):
        super().__init__(text)
        self.setFlags(_ITEM_FLAGS)
        self.setFont(QFont("Segoe UI", 14))

    def start_editing(self):
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setFocus(Qt.MouseFocusReason)
        cursor = self.textCursor()
        cursor.select(QTextCursor.Document)
        self.setTextCursor(cursor)

    def mouseDoubleClickEvent(self, event):
        self.start_editing()
        super().mouseDoubleClickEvent(event)

    def focusOutEvent(self, event):
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        super().focusOutEvent(event)


class PaintScene(QGraphicsScene):
    """One scene holding the raster layer plus all vector items."""

    changed_by_user = pyqtSignal()

    def __init__(self, width: int = 800, height: int = 600, parent=None):
        super().__init__(parent)
        self.tool = POINTER
        self.pen = QPen(QColor("#1a1a1a"), 2)
        self.pen.setCapStyle(Qt.RoundCap)
        self.pen.setJoinStyle(Qt.RoundJoin)
        self.fill_color = QColor("#4aa3ff")
        self.fill_enabled = False
        self.bucket_vector = False        # bucket output: raster vs vector

        self.grid_size = 20
        self.snap_enabled = True
        self.show_grid = True

        self.raster_item = QGraphicsPixmapItem()
        self.raster_item.setZValue(-10)
        self.addItem(self.raster_item)

        self._drawing = False
        self._start = QPointF()
        self._temp_item = None
        self._last_raster_pos = None

        self.new_document(width, height)

    # ------------------------------------------------------------ document
    def new_document(self, width: int, height: int):
        """Reset to a blank white canvas of the given size."""
        for item in list(self.items()):
            if item is not self.raster_item:
                self.removeItem(item)
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.white)
        self.raster_item.setPixmap(pixmap)
        self.setSceneRect(0, 0, width, height)

    def set_raster_pixmap(self, pixmap: QPixmap):
        """Replace the raster layer (Open PNG) and resize the canvas."""
        self.raster_item.setPixmap(pixmap)
        self.setSceneRect(0, 0, pixmap.width(), pixmap.height())

    def vector_items(self):
        """Top-level vector items, bottom to top (excludes the raster)."""
        return [i for i in sorted(self.items(), key=lambda i: i.zValue())
                if i is not self.raster_item and i.parentItem() is None]

    # ------------------------------------------------------------ snapping
    def snap(self, pos: QPointF) -> QPointF:
        # floor(x/g + 0.5) rounds half-up; round() would banker-round
        # half-grid points inconsistently.
        g = self.grid_size
        return QPointF(math.floor(pos.x() / g + 0.5) * g,
                       math.floor(pos.y() / g + 0.5) * g)

    def _tool_pos(self, pos: QPointF) -> QPointF:
        """Snap vector-tool positions; the pencil stays freehand."""
        if self.snap_enabled and self.tool in _SHAPE_TOOLS + (TEXT,):
            return self.snap(pos)
        return pos

    # ------------------------------------------------------------ brushes
    def current_brush(self) -> QBrush:
        return QBrush(self.fill_color) if self.fill_enabled \
            else QBrush(Qt.NoBrush)

    # ------------------------------------------------------------ grouping
    def group_selection(self):
        items = [i for i in self.selectedItems() if i.parentItem() is None]
        if len(items) < 2:
            return
        group = GroupItem()
        self.addItem(group)
        for item in items:
            group.addToGroup(item)
        group.setSelected(True)
        self.changed_by_user.emit()

    def ungroup_selection(self):
        for item in self.selectedItems():
            if isinstance(item, QGraphicsItemGroup):
                children = item.childItems()
                self.destroyItemGroup(item)
                for child in children:
                    child.setFlags(_ITEM_FLAGS)
                    child.setSelected(True)
        self.changed_by_user.emit()

    def delete_selection(self):
        for item in self.selectedItems():
            self.removeItem(item)
        self.changed_by_user.emit()

    # ------------------------------------------------------------ tools
    def mousePressEvent(self, event):
        if self.tool == POINTER or event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return
        # Let an in-progress text edit receive the click first.
        focus = self.focusItem()
        if isinstance(focus, TextItem) and focus.textInteractionFlags():
            super().mousePressEvent(event)
            return

        if self.tool == BUCKET:
            from . import fill
            fill.bucket_fill(self, event.scenePos(), self.fill_color,
                             vector=self.bucket_vector)
            return

        pos = self._tool_pos(event.scenePos())
        self._drawing = True
        self._start = pos

        if self.tool == PENCIL:
            self._last_raster_pos = event.scenePos()
            self._paint_raster(event.scenePos(), event.scenePos())
        elif self.tool in _TWO_POINT_TOOLS:
            cls = ArrowItem if self.tool == ARROW else LineItem
            self._temp_item = cls(QLineF(pos, pos))
            self._temp_item.setPen(self.pen)
            self.addItem(self._temp_item)
        elif self.tool in _RECT_TOOLS:
            item = self._new_rect_item(self.tool)
            item.setPen(self.pen)
            item.setBrush(self.current_brush())
            self.addItem(item)
            self._temp_item = item
        elif self.tool == TEXT:
            item = TextItem()
            item.setDefaultTextColor(self.pen.color())
            item.setPos(pos)
            self.addItem(item)
            item.start_editing()
            self._drawing = False
            self.changed_by_user.emit()

    def mouseMoveEvent(self, event):
        if not self._drawing:
            super().mouseMoveEvent(event)
            return
        if self.tool == PENCIL:
            self._paint_raster(self._last_raster_pos, event.scenePos())
            self._last_raster_pos = event.scenePos()
            return
        if self._temp_item is None:
            return
        pos = self._tool_pos(event.scenePos())
        if self.tool in _TWO_POINT_TOOLS:
            self._temp_item.setLine(QLineF(self._start, pos))
        else:
            self._apply_rect(self._temp_item, self._shape_rect(pos))

    def mouseReleaseEvent(self, event):
        if not self._drawing:
            super().mouseReleaseEvent(event)
            return
        self._drawing = False
        if self.tool == PENCIL:
            self._last_raster_pos = None
            self.changed_by_user.emit()
            return
        item = self._temp_item
        self._temp_item = None
        if item is None:
            return
        if isinstance(item, LineItem):
            degenerate = item.line().length() < 1
        else:
            br = item.boundingRect()
            degenerate = br.width() < 1 and br.height() < 1
        if degenerate:
            self.removeItem(item)
        else:
            self.changed_by_user.emit()

    def _new_rect_item(self, tool: str):
        """A fresh, empty rect-defined item for *tool*."""
        if tool == RECT:
            return RectItem(QRectF())
        if tool == ROUNDRECT:
            return RoundedRectItem(QRectF())
        if tool in POLYGON_KINDS:
            return PolygonItem(kind=tool)
        return EllipseItem(QRectF())          # RECT/CIRCLE/ELLIPSE ellipses

    @staticmethod
    def _apply_rect(item, rect: QRectF):
        """Resize a rect-defined item during the creation drag."""
        if isinstance(item, (PolygonItem, RoundedRectItem)):
            item.set_rect(rect)
        else:
            item.setRect(rect)

    def _shape_rect(self, pos: QPointF) -> QRectF:
        """Rect from drag start to *pos*; the circle tool stays square."""
        dx = pos.x() - self._start.x()
        dy = pos.y() - self._start.y()
        if self.tool == CIRCLE:
            side = max(abs(dx), abs(dy))
            dx = side if dx >= 0 else -side
            dy = side if dy >= 0 else -side
        return QRectF(self._start,
                      self._start + QPointF(dx, dy)).normalized()

    def _paint_raster(self, p1: QPointF, p2: QPointF):
        pixmap = self.raster_item.pixmap()
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(self.pen)
        painter.drawLine(p1, p2)
        painter.end()
        self.raster_item.setPixmap(pixmap)


class PaintView(QGraphicsView):
    """Canvas view: grid overlay, zoom, cursor tracking."""

    cursor_moved = pyqtSignal(QPointF)
    #: (top-level item, global QPoint) when an item is right-clicked.
    item_context = pyqtSignal(object, object)
    #: top-level item when a non-text item is double-clicked (edit).
    item_edit = pyqtSignal(object)

    def __init__(self, scene: PaintScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing
                            | QPainter.SmoothPixmapTransform)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

    def _pick_item(self, view_pos):
        """Top-level editable item under *view_pos*, or None.
        Skips endpoint handles and the raster layer; climbs to the
        outermost group so right-clicking inside a group targets it."""
        for it in self.items(view_pos):
            if isinstance(it, EndpointHandle) or it is self.scene().raster_item:
                continue
            while it.parentItem() is not None:
                it = it.parentItem()
            return it
        return None

    def contextMenuEvent(self, event):
        if self.scene().tool != POINTER:
            return
        item = self._pick_item(event.pos())
        if item is None:
            return
        if not item.isSelected():
            self.scene().clearSelection()
            item.setSelected(True)
        self.item_context.emit(item, event.globalPos())

    def mouseDoubleClickEvent(self, event):
        if self.scene().tool == POINTER:
            item = self._pick_item(event.pos())
            if item is not None and not isinstance(item, TextItem):
                self.item_edit.emit(item)
                return
        super().mouseDoubleClickEvent(event)

    def set_tool_cursor(self, tool: str):
        if tool == POINTER:
            self.setDragMode(QGraphicsView.RubberBandDrag)
            self.viewport().setCursor(Qt.ArrowCursor)
        else:
            self.setDragMode(QGraphicsView.NoDrag)
            self.viewport().setCursor(
                Qt.IBeamCursor if tool == TEXT else Qt.CrossCursor)

    # ------------------------------------------------------------ grid
    def drawForeground(self, painter: QPainter, rect: QRectF):
        super().drawForeground(painter, rect)
        scene = self.scene()
        if not getattr(scene, "show_grid", False):
            return
        g = scene.grid_size
        area = rect.intersected(scene.sceneRect())
        if area.isEmpty():
            return
        painter.setPen(QPen(QColor(120, 144, 168, 70), 0))
        x = int(area.left()) - int(area.left()) % g
        while x <= area.right():
            painter.drawLine(QPointF(x, area.top()),
                             QPointF(x, area.bottom()))
            x += g
        y = int(area.top()) - int(area.top()) % g
        while y <= area.bottom():
            painter.drawLine(QPointF(area.left(), y),
                             QPointF(area.right(), y))
            y += g
        painter.setPen(QPen(QColor(120, 144, 168, 160), 0))
        painter.drawRect(scene.sceneRect())

    # ------------------------------------------------------------ zoom
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
        else:
            super().wheelEvent(event)

    def zoom(self, factor: float):
        current = self.transform().m11()
        if 0.1 <= current * factor <= 16:
            self.scale(factor, factor)

    def zoom_reset(self):
        self.resetTransform()

    def mouseMoveEvent(self, event):
        self.cursor_moved.emit(self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)
