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
                         QPen, QPixmap, QPolygonF, QTextCursor, QTransform)
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                             QGraphicsItemGroup, QGraphicsLineItem,
                             QGraphicsPathItem, QGraphicsPixmapItem,
                             QGraphicsPolygonItem, QGraphicsRectItem,
                             QGraphicsScene, QGraphicsTextItem,
                             QGraphicsView, QStyle)

# Tool identifiers.
POINTER, PENCIL, LINE, RECT, CIRCLE, ELLIPSE, TEXT = (
    "pointer", "pencil", "line", "rect", "circle", "ellipse", "text")
BUCKET = "bucket"
ARROW, ROUNDRECT = "arrow", "roundrect"
DIMENSION = "dimension"
HALFCIRCLE, QUARTERCIRCLE = "halfcircle", "quartercircle"
TRIANGLE, DIAMOND, PENTAGON, HEXAGON, STAR = (
    "triangle", "diamond", "pentagon", "hexagon", "star")
RIGHT_TRIANGLE, PARALLELOGRAM, TRAPEZOID = (
    "right_triangle", "parallelogram", "trapezoid")
HEPTAGON, OCTAGON, STAR6 = "heptagon", "octagon", "star6"
PLUS, CHEVRON, ARROW_RIGHT, LIGHTNING, HOUSE = (
    "plus", "chevron", "arrow_right", "lightning", "house")

#: Parametric polygons created by dragging a bounding rect — all of
#: these are vertex polygons, so they explode into their edge lines.
POLYGON_KINDS = (TRIANGLE, RIGHT_TRIANGLE, DIAMOND, PARALLELOGRAM,
                 TRAPEZOID, PENTAGON, HEXAGON, HEPTAGON, OCTAGON, STAR,
                 STAR6, PLUS, CHEVRON, ARROW_RIGHT, LIGHTNING, HOUSE)

#: Custom polygons given as fractional (x, y) vertices within the rect.
_POLY_FRACTIONS = {
    TRIANGLE: [(0.5, 0), (1, 1), (0, 1)],
    RIGHT_TRIANGLE: [(0, 0), (0, 1), (1, 1)],
    DIAMOND: [(0.5, 0), (1, 0.5), (0.5, 1), (0, 0.5)],
    PARALLELOGRAM: [(0.25, 0), (1, 0), (0.75, 1), (0, 1)],
    TRAPEZOID: [(0.25, 0), (0.75, 0), (1, 1), (0, 1)],
    PLUS: [(0.34, 0), (0.66, 0), (0.66, 0.34), (1, 0.34), (1, 0.66),
           (0.66, 0.66), (0.66, 1), (0.34, 1), (0.34, 0.66), (0, 0.66),
           (0, 0.34), (0.34, 0.34)],
    CHEVRON: [(0, 0), (0.6, 0), (1, 0.5), (0.6, 1), (0, 1), (0.4, 0.5)],
    ARROW_RIGHT: [(0, 0.3), (0.6, 0.3), (0.6, 0), (1, 0.5), (0.6, 1),
                  (0.6, 0.7), (0, 0.7)],
    LIGHTNING: [(0.6, 0), (0, 0.6), (0.35, 0.6), (0.15, 1), (1, 0.35),
                (0.55, 0.35), (0.75, 0)],
    HOUSE: [(0.5, 0), (1, 0.45), (1, 1), (0, 1), (0, 0.45)],
}
#: Regular polygons by number of sides.
_POLY_SIDES = {PENTAGON: 5, HEXAGON: 6, HEPTAGON: 7, OCTAGON: 8}
#: Parametric arc shapes created by dragging a bounding rect.
ARC_KINDS = (HALFCIRCLE, QUARTERCIRCLE)
#: Tools defined by two points (drag start -> end).
_TWO_POINT_TOOLS = (LINE, ARROW, DIMENSION)
#: Tools defined by a dragged bounding rect.
_RECT_TOOLS = (RECT, CIRCLE, ELLIPSE, ROUNDRECT) + POLYGON_KINDS + ARC_KINDS
#: Tools that rubber-band a new vector item between press and release.
_SHAPE_TOOLS = _TWO_POINT_TOOLS + _RECT_TOOLS

_ITEM_FLAGS = (QGraphicsItem.ItemIsSelectable
               | QGraphicsItem.ItemIsMovable
               | QGraphicsItem.ItemSendsGeometryChanges)


class NoSelMixin:
    """Suppress Qt's built-in dashed selection rectangle. Selection is
    shown by our own handles, and the default dashes were lingering on
    screen after deselect (especially for grouped items)."""

    def paint(self, painter, option, widget=None):
        option.state = option.state & ~QStyle.State_Selected
        super().paint(painter, option, widget)


class SnapMixin:
    """Snaps the item's position to the scene grid while it is moved."""

    def itemChange(self, change, value):
        if (change == QGraphicsItem.ItemPositionChange
                and self.scene() is not None
                and getattr(self.scene(), "snap_enabled", False)):
            value = self.scene().snap(value)
        return super().itemChange(change, value)


def center_origin(item):
    """Make the item rotate/scale about its own centre rather than the
    scene origin (otherwise a shape whose geometry sits far from (0,0)
    swings off-screen when rotated)."""
    item.setTransformOriginPoint(item.boundingRect().center())


class LabelMixin:
    """An optional text label drawn centred inside a shape. Defaults
    live at class level (immutable), so an unlabelled shape carries no
    per-instance state until set_label() is called."""

    _label = ""
    _label_family = "Segoe UI"
    _label_size = 14
    _label_bold = False
    _label_italic = False
    _label_color_name = "#1a1a1a"

    def label(self) -> str:
        return self._label

    def set_label(self, text: str):
        self._label = text or ""
        self.update()

    def label_font(self) -> QFont:
        font = QFont(self._label_family, self._label_size)
        font.setBold(self._label_bold)
        font.setItalic(self._label_italic)
        return font

    def set_label_font(self, font: QFont):
        self._label_family = font.family()
        self._label_size = font.pointSize()
        self._label_bold = font.bold()
        self._label_italic = font.italic()
        self.update()

    def label_color(self) -> QColor:
        return QColor(self._label_color_name)

    def set_label_color(self, color):
        self._label_color_name = QColor(color).name()
        self.update()

    def _paint_label(self, painter):
        if not self._label:
            return
        painter.save()
        painter.setFont(self.label_font())
        painter.setPen(self.label_color())
        painter.drawText(self.boundingRect(),
                         Qt.AlignCenter | Qt.TextWordWrap, self._label)
        painter.restore()

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        self._paint_label(painter)


class LineItem(NoSelMixin, SnapMixin, QGraphicsLineItem):
    def __init__(self, *a):
        super().__init__(*a)
        self.setFlags(_ITEM_FLAGS)


class RectItem(NoSelMixin, LabelMixin, SnapMixin, QGraphicsRectItem):
    def __init__(self, *a):
        super().__init__(*a)
        self.setFlags(_ITEM_FLAGS)


class EllipseItem(NoSelMixin, LabelMixin, SnapMixin, QGraphicsEllipseItem):
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


class DimensionItem(LineItem):
    """A measured line: arrowheads at both ends and a length label in mm
    (derived from the scene dpi). Edited like a line via its endpoints;
    the label updates live as the endpoints move."""

    HEAD = 10
    _LABEL_PAD = 60         # boundingRect slack for arrows + label text

    def boundingRect(self):
        extra = self.HEAD + self.pen().widthF() + self._LABEL_PAD
        return super().boundingRect().adjusted(-extra, -extra, extra, extra)

    def length_mm(self) -> float:
        scene = self.scene()
        dpi = getattr(scene, "dpi", 96) if scene is not None else 96
        return self.line().length() / max(dpi, 1) * 25.4

    def _label_text(self) -> str:
        return f"{self.length_mm():.1f} mm"

    def _head(self, tip: QPointF, other: QPointF) -> QPolygonF:
        angle = math.atan2(tip.y() - other.y(), tip.x() - other.x())
        left = tip - QPointF(math.cos(angle - math.pi / 7) * self.HEAD,
                             math.sin(angle - math.pi / 7) * self.HEAD)
        right = tip - QPointF(math.cos(angle + math.pi / 7) * self.HEAD,
                              math.sin(angle + math.pi / 7) * self.HEAD)
        return QPolygonF([tip, left, right])

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)        # the line itself
        ln = self.line()
        if ln.length() < 1:
            return
        color = self.pen().color()
        painter.setPen(QPen(color, self.pen().widthF()))
        painter.setBrush(QBrush(color))
        painter.drawPolygon(self._head(ln.p2(), ln.p1()))
        painter.drawPolygon(self._head(ln.p1(), ln.p2()))
        # length label, offset just off the line at its midpoint
        angle = math.atan2(ln.dy(), ln.dx())
        mid = QPointF((ln.x1() + ln.x2()) / 2, (ln.y1() + ln.y2()) / 2)
        off = QPointF(math.sin(angle), -math.cos(angle)) * 14
        painter.save()
        font = QFont("Segoe UI", 10)
        painter.setFont(font)
        painter.setPen(QPen(color))
        painter.setBrush(Qt.NoBrush)
        text = self._label_text()
        fm = painter.fontMetrics()
        w = fm.horizontalAdvance(text)
        tp = mid + off
        painter.drawText(QPointF(tp.x() - w / 2,
                                 tp.y() + fm.ascent() / 2 - 1), text)
        painter.restore()


def polygon_for_kind(kind: str, rect: QRectF) -> QPolygonF:
    """Vertices of a parametric polygon *kind* inscribed in *rect*."""
    left, top = rect.left(), rect.top()
    w, h = rect.width(), rect.height()
    cx, cy = rect.center().x(), rect.center().y()
    rx, ry = w / 2, h / 2

    if kind in _POLY_FRACTIONS:
        pts = [(left + fx * w, top + fy * h)
               for fx, fy in _POLY_FRACTIONS[kind]]
    elif kind in (STAR, STAR6):
        points = 5 if kind == STAR else 6
        pts = []
        for i in range(points * 2):
            ang = -math.pi / 2 + i * math.pi / points
            scale = 1.0 if i % 2 == 0 else 0.4
            pts.append((cx + rx * scale * math.cos(ang),
                        cy + ry * scale * math.sin(ang)))
    else:                                   # regular polygon
        sides = _POLY_SIDES.get(kind, 6)
        pts = []
        for i in range(sides):
            ang = -math.pi / 2 + i * 2 * math.pi / sides
            pts.append((cx + rx * math.cos(ang), cy + ry * math.sin(ang)))
    return QPolygonF([QPointF(x, y) for x, y in pts])


class PolygonItem(NoSelMixin, LabelMixin, SnapMixin, QGraphicsPolygonItem):
    """Free or parametric polygon. *kind* is kept for display only;
    geometry is always the vertex list, so SVG-imported polygons and
    triangle/star/etc. behave identically."""

    def __init__(self, polygon=None, kind="polygon"):
        super().__init__(QPolygonF(polygon) if polygon else QPolygonF())
        self.setFlags(_ITEM_FLAGS)
        self.kind = kind

    def set_rect(self, rect: QRectF):
        self.setPolygon(polygon_for_kind(self.kind, rect))


class RoundedRectItem(NoSelMixin, LabelMixin, SnapMixin, QGraphicsPathItem):
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


def arc_path(kind: str, rect: QRectF, flip_h=False, flip_v=False
             ) -> QPainterPath:
    """A half- or quarter-disc filling *rect* (with optional flips)."""
    r = QRectF(rect)
    path = QPainterPath()
    if r.width() <= 0 or r.height() <= 0:
        return path
    if kind == HALFCIRCLE:
        # flat side on the bottom edge, arc bulging up over the top
        ell = QRectF(r.left(), r.top(), r.width(), r.height() * 2)
        path.arcMoveTo(ell, 0)
        path.arcTo(ell, 0, 180)
        path.closeSubpath()
    else:                                  # quarter: corner at bottom-left
        ell = QRectF(r.left() - r.width(), r.top(),
                     r.width() * 2, r.height() * 2)
        path.moveTo(r.left(), r.bottom())
        path.arcTo(ell, 0, 90)
        path.closeSubpath()
    if flip_h or flip_v:
        c = r.center()
        t = QTransform()
        t.translate(c.x(), c.y())
        t.scale(-1 if flip_h else 1, -1 if flip_v else 1)
        t.translate(-c.x(), -c.y())
        path = t.map(path)
    return path


class ArcShapeItem(NoSelMixin, LabelMixin, SnapMixin, QGraphicsPathItem):
    """Half- or quarter-circle, parametric on a bounding rect plus
    horizontal/vertical flip flags (so it can be mirrored and still
    round-trip)."""

    def __init__(self, rect=None, kind=HALFCIRCLE):
        super().__init__()
        self.setFlags(_ITEM_FLAGS)
        self._rect = QRectF(rect) if rect else QRectF()
        self.kind = kind
        self.flip_h = False
        self.flip_v = False
        self._rebuild()

    def rect(self) -> QRectF:
        return QRectF(self._rect)

    def set_rect(self, rect: QRectF):
        self._rect = QRectF(rect)
        self._rebuild()

    def mirror(self, horizontal=True):
        if horizontal:
            self.flip_h = not self.flip_h
        else:
            self.flip_v = not self.flip_v
        self._rebuild()

    def _rebuild(self):
        self.setPath(arc_path(self.kind, self._rect, self.flip_h, self.flip_v))


class PathItem(NoSelMixin, SnapMixin, QGraphicsPathItem):
    """An arbitrary vector path — the import target for SVG <path> and
    for elements carrying a non-trivial (scaled/sheared) transform."""

    def __init__(self, path=None):
        super().__init__(path if path else QPainterPath())
        self.setFlags(_ITEM_FLAGS)


class ImageItem(NoSelMixin, SnapMixin, QGraphicsPixmapItem):
    """A pasted/placed bitmap living on the vector layer (movable)."""

    def __init__(self, pixmap=None):
        super().__init__(pixmap if pixmap else QPixmap())
        self.setFlags(_ITEM_FLAGS)
        self.setTransformationMode(Qt.SmoothTransformation)


class GroupItem(NoSelMixin, SnapMixin, QGraphicsItemGroup):
    def __init__(self):
        super().__init__()
        self.setFlags(_ITEM_FLAGS)


class TextItem(NoSelMixin, SnapMixin, QGraphicsTextItem):
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

        # The grid is specified as a physical distance in millimetres
        # between adjacent lines; the pixel spacing is derived from the
        # canvas dpi (see grid_size). Smaller mm -> finer cells.
        self.grid_mm = 1.0
        self.snap_enabled = True
        self.show_grid = True
        self.infinite = False     # infinite paper: grid fills the view
        self.dpi = 96             # pixels per inch, for physical export size

        self.raster_item = QGraphicsPixmapItem()
        self.raster_item.setZValue(-10)
        self.addItem(self.raster_item)

        self._drawing = False
        self._start = QPointF()
        self._temp_item = None
        self._stroke_path = None        # freehand pencil path while drawing

        self._sel_handles = None        # SelectionHandles for active item
        self._rotate_target = None      # item currently in rotate mode
        self._crop = None               # active CropSession, if any
        self._press_positions = {}      # selected item positions at press
        self.selectionChanged.connect(self._on_selection_changed)

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

    def resize_canvas(self, width: int, height: int):
        """Change the canvas size, keeping all content where it is
        (raster content is preserved at the top-left, padded white)."""
        width, height = max(1, int(width)), max(1, int(height))
        old = self.raster_item.pixmap()
        new = QPixmap(width, height)
        new.fill(Qt.white)
        painter = QPainter(new)
        painter.drawPixmap(0, 0, old)
        painter.end()
        self.raster_item.setPixmap(new)
        self.setSceneRect(0, 0, width, height)
        self.changed_by_user.emit()

    def fit_to_content(self, selection_only: bool = False, margin: int = 10):
        """Resize the canvas to the bounding box of the drawing (or the
        selection), shifting all content so it sits at *margin* from the
        top-left. Both layers move together, so nothing is lost."""
        chosen = [i for i in self.selectedItems() if i.parentItem() is None] \
            if selection_only else []
        items = chosen or self.vector_items()
        rect = QRectF()
        for item in items:
            rect = rect.united(item.sceneBoundingRect())
        if rect.isEmpty():
            return
        dx = int(round(margin - rect.left()))
        dy = int(round(margin - rect.top()))
        width = int(math.ceil(rect.width())) + 2 * margin
        height = int(math.ceil(rect.height())) + 2 * margin

        was_snap = self.snap_enabled
        self.snap_enabled = False
        for item in self.vector_items():
            item.moveBy(dx, dy)
        self.snap_enabled = was_snap

        old = self.raster_item.pixmap()
        new = QPixmap(width, height)
        new.fill(Qt.white)
        painter = QPainter(new)
        painter.drawPixmap(dx, dy, old)
        painter.end()
        self.raster_item.setPixmap(new)
        self.setSceneRect(0, 0, width, height)
        self.changed_by_user.emit()

    def vector_items(self):
        """Top-level vector items, bottom to top (excludes the raster and
        any scene-level selection handles)."""
        from .handles import Handle
        return [i for i in sorted(self.items(), key=lambda i: i.zValue())
                if i is not self.raster_item and i.parentItem() is None
                and not isinstance(i, Handle)]

    # ------------------------------------------------------------ grid
    @property
    def grid_size(self) -> float:
        """Exact pixel spacing between grid lines, from the physical grid
        distance (mm) and the canvas dpi. Kept as a float (NOT rounded to
        whole pixels): a rounded spacing makes snapped points miss true
        millimetre positions, so a measured dimension drifts — e.g. a
        1 mm grid at 300 dpi is 11.81 px, and rounding to 12 px turned a
        10 mm line into 10.2 mm."""
        return max(1e-6, self.grid_mm / 25.4 * self.dpi)

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
        # Reparenting must not snap: addToGroup repositions each child
        # into group coords, and snapping that would shift them.
        was_snap = self.snap_enabled
        self.snap_enabled = False
        for item in items:
            group.addToGroup(item)
        self.snap_enabled = was_snap
        self.clearSelection()
        group.setSelected(True)
        self.changed_by_user.emit()

    def ungroup_selection(self):
        was_snap = self.snap_enabled
        self.snap_enabled = False
        for item in self.selectedItems():
            if isinstance(item, QGraphicsItemGroup):
                children = item.childItems()
                self.destroyItemGroup(item)
                for child in children:
                    child.setFlags(_ITEM_FLAGS)
                    child.setSelected(True)
        self.snap_enabled = was_snap
        self.changed_by_user.emit()

    def delete_selection(self):
        self.clear_handles()
        for item in self.selectedItems():
            self.removeItem(item)
        self.changed_by_user.emit()

    def explode_selection(self):
        """Break each selected shape's outline into its individual edge
        segments (straight edges -> lines, curved edges -> arc paths), so
        a single piece can be deleted or edited (then the rest regrouped
        with Ctrl+G). The new segments are left selected."""
        self.clear_handles()
        new_items = []
        originals = []
        for item in self.selectedItems():
            segments = self._explode_item(item)
            if segments:
                originals.append(item)
                new_items.extend(segments)
        if not new_items:
            return
        for item in originals:
            self.removeItem(item)
        self.clearSelection()
        for seg in new_items:
            self.addItem(seg)
            seg.setSelected(True)
        self.changed_by_user.emit()

    @staticmethod
    def _outline_path(item):
        """The shape's outline as a QPainterPath in item-local coords, or
        None if the item has no breakable outline (line/text/image/group)."""
        if isinstance(item, PolygonItem):
            path = QPainterPath()
            path.addPolygon(item.polygon())
            path.closeSubpath()
            return path
        if isinstance(item, RectItem):
            path = QPainterPath()
            path.addRect(item.rect())
            return path
        if isinstance(item, EllipseItem):
            path = QPainterPath()
            path.addEllipse(item.rect())
            return path
        if isinstance(item, (RoundedRectItem, ArcShapeItem, PathItem)):
            return QPainterPath(item.path())
        return None                          # line/arrow/text/image/group

    def _explode_item(self, item):
        local = self._outline_path(item)
        if local is None or local.elementCount() < 2:
            return None
        path = item.sceneTransform().map(local)   # to scene coordinates
        pen = QPen(item.pen())
        segments = []
        cur = None
        i, n = 0, path.elementCount()
        while i < n:
            e = path.elementAt(i)
            if e.isMoveTo():
                cur = QPointF(e.x, e.y)
                i += 1
            elif e.isLineTo():
                end = QPointF(e.x, e.y)
                if cur is not None:
                    line = LineItem(QLineF(cur, end))
                    line.setPen(pen)
                    segments.append(line)
                cur = end
                i += 1
            else:                            # cubic: control1 + 2 data points
                c2 = path.elementAt(i + 1)
                ep = path.elementAt(i + 2)
                sub = QPainterPath()
                sub.moveTo(cur)
                sub.cubicTo(QPointF(e.x, e.y), QPointF(c2.x, c2.y),
                            QPointF(ep.x, ep.y))
                arc = PathItem(sub)
                arc.setPen(pen)
                arc.setBrush(QBrush(Qt.NoBrush))
                segments.append(arc)
                cur = QPointF(ep.x, ep.y)
                i += 3
        return segments

    # ------------------------------------------------------------ handles
    def clear_handles(self):
        if self._sel_handles is not None:
            self._sel_handles.remove()
            self._sel_handles = None

    def _on_selection_changed(self):
        # Force a repaint so vacated selection outlines never linger.
        self.update()
        # Drop handles whenever the active single selection goes away
        # (covers clearSelection() before export/fill/save, and
        # rubber-band multi-select).
        if len(self.selectedItems()) != 1:
            self.clear_handles()
            self._rotate_target = None

    def refresh_handles(self, mode=None, item=None):
        """Rebuild handles for the active item. Without *mode*, keep
        rotate mode if this item was put in it, else show resize."""
        from .handles import RESIZE, ROTATE, SelectionHandles
        sel = self.selectedItems()
        target = item if item is not None else (
            sel[0] if len(sel) == 1 else None)
        self.clear_handles()
        if target is None or self.tool != POINTER:
            self._rotate_target = None
            return
        if mode is None:
            mode = ROTATE if target is self._rotate_target else RESIZE
        self._rotate_target = target if mode == ROTATE else None
        self._sel_handles = SelectionHandles(self, target, mode)

    def enter_rotate_mode(self, item):
        from .handles import ROTATE
        center_origin(item)
        self.clearSelection()
        item.setSelected(True)
        self.refresh_handles(mode=ROTATE, item=item)

    # ------------------------------------------------------------ cropping
    def crop_active(self) -> bool:
        return self._crop is not None

    def begin_crop(self, image):
        from .crop import CropSession
        self.cancel_crop()
        self.clear_handles()
        self.clearSelection()
        self._crop = CropSession(self, image)

    def apply_crop(self):
        if self._crop is not None:
            self._crop.apply()
            self._crop = None

    def cancel_crop(self):
        if self._crop is not None:
            self._crop.cancel()
            self._crop = None

    # ------------------------------------------------------------ tools
    def mousePressEvent(self, event):
        if self.tool == POINTER or event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            if self.tool == POINTER:
                self._press_positions = {it: it.pos()
                                         for it in self.selectedItems()}
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
            self.pencil_begin(event.scenePos())
        elif self.tool in _TWO_POINT_TOOLS:
            cls = {ARROW: ArrowItem, DIMENSION: DimensionItem}.get(
                self.tool, LineItem)
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
            self.pencil_extend(event.scenePos())
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
            if self.tool == POINTER and event.button() == Qt.LeftButton:
                moved = self._moved_since_press()
                self.refresh_handles()
                if moved:
                    self.changed_by_user.emit()
            return
        self._drawing = False
        if self.tool == PENCIL:
            self.pencil_end()
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
            center_origin(item)
            self.changed_by_user.emit()

    # ------------------------------------------------------------ pencil
    def pencil_begin(self, point: QPointF):
        """Start a freehand vector stroke at *point* (scene coords)."""
        self._stroke_path = QPainterPath(point)
        stroke = PathItem(self._stroke_path)
        stroke.setPen(QPen(self.pen))          # copy, not shared
        stroke.setBrush(QBrush(Qt.NoBrush))
        self.addItem(stroke)
        self._temp_item = stroke

    def pencil_extend(self, point: QPointF):
        if self._stroke_path is None or self._temp_item is None:
            return
        if (point - self._stroke_path.currentPosition()
                ).manhattanLength() >= 2:
            self._stroke_path.lineTo(point)
            self._temp_item.setPath(self._stroke_path)

    def pencil_end(self):
        stroke = self._temp_item
        path = self._stroke_path
        self._temp_item = None
        self._stroke_path = None
        if stroke is None:
            return
        if path is None or path.elementCount() <= 1:
            self.removeItem(stroke)            # a click with no drag
        else:
            center_origin(stroke)
            self.changed_by_user.emit()

    def _moved_since_press(self) -> bool:
        """True if any item selected at press has since changed position
        (a pointer move gesture), so it can be recorded for undo."""
        return any(it.scene() is self and it.pos() != pos
                   for it, pos in self._press_positions.items())

    def _new_rect_item(self, tool: str):
        """A fresh, empty rect-defined item for *tool*."""
        if tool == RECT:
            return RectItem(QRectF())
        if tool == ROUNDRECT:
            return RoundedRectItem(QRectF())
        if tool in POLYGON_KINDS:
            return PolygonItem(kind=tool)
        if tool in ARC_KINDS:
            return ArcShapeItem(kind=tool)
        return EllipseItem(QRectF())          # RECT/CIRCLE/ELLIPSE ellipses

    @staticmethod
    def _apply_rect(item, rect: QRectF):
        """Resize a rect-defined item during the creation drag."""
        if isinstance(item, (PolygonItem, RoundedRectItem, ArcShapeItem)):
            item.set_rect(rect)
        else:
            item.setRect(rect)

    # ------------------------------------------------------------ mirror
    def mirror_selection(self, horizontal: bool = True):
        """Flip the selected items in place (about their own centres)."""
        items = [i for i in self.selectedItems() if i.parentItem() is None]
        for item in items:
            self._mirror_item(item, horizontal)
        if items:
            self.changed_by_user.emit()

    def _mirror_item(self, item, horizontal: bool):
        if isinstance(item, GroupItem):
            self._mirror_group(item, horizontal)
            return
        if isinstance(item, ArcShapeItem):
            item.mirror(horizontal)
            return
        if isinstance(item, ImageItem):
            item.setPixmap(item.pixmap().transformed(
                QTransform().scale(-1 if horizontal else 1,
                                   1 if horizontal else -1)))
            return
        c = item.boundingRect().center()
        t = QTransform()
        t.translate(c.x(), c.y())
        t.scale(-1 if horizontal else 1, 1 if horizontal else -1)
        t.translate(-c.x(), -c.y())
        if isinstance(item, PolygonItem):
            item.setPolygon(t.map(item.polygon()))
        elif isinstance(item, LineItem):       # includes arrow
            ln = item.line()
            item.setLine(QLineF(t.map(ln.p1()), t.map(ln.p2())))
        elif isinstance(item, PathItem):
            item.setPath(t.map(item.path()))
        # rect/ellipse/rounded-rect/text are symmetric: nothing to do

    def _mirror_group(self, group, horizontal: bool):
        """Flip a group about its centre: flip each child in place and
        reflect its position about the group centre (the two together
        equal reflecting the whole group). Keeps every child native, so
        the flip round-trips through save."""
        from .handles import Handle
        centre = group.boundingRect().center()
        was_snap = self.snap_enabled
        self.snap_enabled = False
        for child in group.childItems():
            if isinstance(child, Handle):
                continue
            self._mirror_item(child, horizontal)
            cc = child.mapToParent(child.boundingRect().center())
            if horizontal:
                child.moveBy(2 * (centre.x() - cc.x()), 0)
            else:
                child.moveBy(0, 2 * (centre.y() - cc.y()))
        self.snap_enabled = was_snap

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


class PaintView(QGraphicsView):
    """Canvas view: grid overlay, zoom, cursor tracking."""

    cursor_moved = pyqtSignal(QPointF)
    #: (top-level item, global QPoint) when an item is right-clicked.
    item_context = pyqtSignal(object, object)
    #: emitted with the new zoom factor (1.0 == 100%) whenever it changes.
    zoom_changed = pyqtSignal(float)

    MIN_ZOOM, MAX_ZOOM = 0.1, 16.0

    def __init__(self, scene: PaintScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing
                            | QPainter.SmoothPixmapTransform)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)   # so Enter/Esc reach the view
        # Repaint the whole viewport on every change: partial updates
        # leave stale selection dashes / handles behind after deselect.
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

    def _pick_item(self, view_pos):
        """Top-level editable item under *view_pos*, or None.
        Skips endpoint handles and the raster layer; climbs to the
        outermost group so right-clicking inside a group targets it."""
        from .handles import Handle
        for it in self.items(view_pos):
            if isinstance(it, Handle) or it is self.scene().raster_item:
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
        if self.scene().crop_active():        # double-click confirms a crop
            self.scene().apply_crop()
            return
        if self.scene().tool == POINTER:
            item = self._pick_item(event.pos())
            if item is not None and not isinstance(item, TextItem):
                self.scene().enter_rotate_mode(item)
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
        if getattr(scene, "show_grid", False):
            self._draw_grid(painter, rect)
        self._draw_selection(painter)

    def _draw_grid(self, painter: QPainter, rect: QRectF):
        scene = self.scene()
        g = scene.grid_size
        # Infinite paper: the grid fills the whole exposed view; finite
        # paper clips it to the page and draws the page border.
        infinite = getattr(scene, "infinite", False)
        area = rect if infinite else rect.intersected(scene.sceneRect())
        if area.isEmpty():
            return
        painter.setPen(QPen(QColor(120, 144, 168, 70), 0))
        x = math.floor(area.left() / g) * g     # g is a float (exact mm)
        while x <= area.right():
            painter.drawLine(QPointF(x, area.top()),
                             QPointF(x, area.bottom()))
            x += g
        y = math.floor(area.top() / g) * g
        while y <= area.bottom():
            painter.drawLine(QPointF(area.left(), y),
                             QPointF(area.right(), y))
            y += g
        if not infinite:
            painter.setPen(QPen(QColor(120, 144, 168, 160), 0))
            painter.drawRect(scene.sceneRect())

    def _draw_selection(self, painter: QPainter):
        """A cosmetic dashed box around every selected top-level item, so
        a multi-selection is visible (handles only mark a single item).
        Drawn in the foreground, so it never lingers and never exports."""
        from .handles import Handle
        scene = self.scene()
        items = [i for i in scene.selectedItems()
                 if i.parentItem() is None and not isinstance(i, Handle)]
        if not items:
            return
        pen = QPen(QColor("#2176c7"), 0, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        for item in items:
            painter.drawRect(item.sceneBoundingRect().adjusted(-1, -1, 1, 1))

    # ------------------------------------------------------------ zoom
    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.zoom(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
        else:
            super().wheelEvent(event)

    def zoom(self, factor: float):
        current = self.transform().m11()
        if self.MIN_ZOOM <= current * factor <= self.MAX_ZOOM:
            self.scale(factor, factor)
            self.zoom_changed.emit(self.transform().m11())

    def set_zoom(self, scale: float):
        """Set the absolute zoom factor (1.0 == 100%), clamped."""
        scale = max(self.MIN_ZOOM, min(self.MAX_ZOOM, scale))
        self.resetTransform()
        self.scale(scale, scale)
        self.zoom_changed.emit(scale)

    def current_zoom(self) -> float:
        return self.transform().m11()

    def zoom_reset(self):
        self.resetTransform()
        self.zoom_changed.emit(1.0)

    def apply_scroll_bounds(self):
        """Let the view scroll across a large empty area when the scene
        is in infinite-paper mode; otherwise follow the page rect."""
        if getattr(self.scene(), "infinite", False):
            m = 100000
            self.setSceneRect(QRectF(-m, -m, 2 * m, 2 * m))
        else:
            self.setSceneRect(QRectF())   # follow the scene's page rect

    def mouseMoveEvent(self, event):
        self.cursor_moved.emit(self.mapToScene(event.pos()))
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event):
        if self.scene().crop_active():
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.scene().apply_crop()
                return
            if event.key() == Qt.Key_Escape:
                self.scene().cancel_crop()
                return
        super().keyPressEvent(event)
