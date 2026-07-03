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
                         QPainterPathStroker, QPen, QPixmap, QPolygonF,
                         QTextCursor, QTransform)
from PyQt5.QtWidgets import (QGraphicsEllipseItem, QGraphicsItem,
                             QGraphicsItemGroup, QGraphicsLineItem,
                             QGraphicsPathItem, QGraphicsPixmapItem,
                             QGraphicsPolygonItem, QGraphicsRectItem,
                             QGraphicsScene, QGraphicsTextItem,
                             QGraphicsView, QStyle)

from . import chemistry

# Tool identifiers.
POINTER, PENCIL, LINE, RECT, CIRCLE, ELLIPSE, TEXT = (
    "pointer", "pencil", "line", "rect", "circle", "ellipse", "text")
BUCKET = "bucket"
ERASER, PICKER = "eraser", "picker"
ROOM = "room"                 # drag-to-size room (the empty space / walls)
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
# Chemistry tools.
CHEM_SINGLE, CHEM_DOUBLE, CHEM_TRIPLE, CHEM_WEDGE, CHEM_HASH = (
    "chem_single", "chem_double", "chem_triple", "chem_wedge", "chem_hash")
CHEM_HBOND = "chem_hbond"
CHEM_CHAIN = "chem_chain"
CHEM_BENZENE, CHEM_CYCLOHEXANE, CHEM_CYCLOPENTANE = (
    "chem_benzene", "chem_cyclohexane", "chem_cyclopentane")
CHEM_ATOM = "chem_atom"
_CHEM_BOND_TOOLS = (CHEM_SINGLE, CHEM_DOUBLE, CHEM_TRIPLE, CHEM_WEDGE,
                    CHEM_HASH, CHEM_HBOND)
_CHEM_RING_TOOLS = (CHEM_BENZENE, CHEM_CYCLOHEXANE, CHEM_CYCLOPENTANE)
_CHEM_PLACE_TOOLS = _CHEM_RING_TOOLS + (CHEM_ATOM,)   # placed on a click
_CHEM_TOOLS = _CHEM_BOND_TOOLS + _CHEM_PLACE_TOOLS + (CHEM_CHAIN,)
#: Room-layout / electrical / science element placement tools.
PLAN_PLACE = "plan_place"
ELEC_PLACE = "elec_place"
OPTICS_PLACE = "optics_place"
VACUUM_PLACE = "vacuum_place"
LABWARE_PLACE = "labware_place"
FLOW_PLACE = "flow_place"
NET_PLACE = "net_place"
PID_PLACE = "pid_place"
ARROW_PLACE = "arrow_place"
BIO_PLACE = "bio_place"
MATH_PLACE = "math_place"
#: All spec-library placement tools (drop a symbol on click).
_PLACE_TOOLS = (PLAN_PLACE, ELEC_PLACE, OPTICS_PLACE, VACUUM_PLACE,
                LABWARE_PLACE, FLOW_PLACE, NET_PLACE, PID_PLACE,
                ARROW_PLACE, BIO_PLACE, MATH_PLACE)

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
_RECT_TOOLS = (RECT, ROOM, CIRCLE, ELLIPSE, ROUNDRECT) + POLYGON_KINDS \
    + ARC_KINDS
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
    """A straight segment, optionally **bent** into a quadratic curve:
    the bend is a control point in item coordinates (None = straight),
    dragged via the round mid-handle when the line is selected."""

    def __init__(self, *a):
        super().__init__(*a)
        self.setFlags(_ITEM_FLAGS)
        self._bend = None               # QPointF control point, or None

    def bend(self):
        return QPointF(self._bend) if self._bend is not None else None

    def set_bend(self, point):
        self.prepareGeometryChange()
        self._bend = QPointF(point) if point is not None else None
        self.update()

    def curve_path(self) -> QPainterPath:
        """The drawn geometry: a straight segment, or the quadratic
        curve through the bend control point."""
        ln = self.line()
        path = QPainterPath(ln.p1())
        if self._bend is not None:
            path.quadTo(self._bend, ln.p2())
        else:
            path.lineTo(ln.p2())
        return path

    def end_angle(self) -> float:
        """Direction (radians) the line arrives at p2 — the curve's end
        tangent when bent, so arrowheads follow the curve."""
        ln = self.line()
        if self._bend is not None:
            v = ln.p2() - self._bend
            if abs(v.x()) > 1e-9 or abs(v.y()) > 1e-9:
                return math.atan2(v.y(), v.x())
        return math.atan2(ln.dy(), ln.dx())

    def boundingRect(self):
        if self._bend is None:
            return super().boundingRect()
        w = self.pen().widthF() / 2 + 1
        return self.curve_path().boundingRect().adjusted(-w, -w, w, w)

    def shape(self):
        if self._bend is None:
            return super().shape()
        stroker = QPainterPathStroker()
        stroker.setWidth(max(self.pen().widthF(), 8.0))
        return stroker.createStroke(self.curve_path())

    def paint(self, painter, option, widget=None):
        if self._bend is None:
            super().paint(painter, option, widget)
            return
        option.state = option.state & ~QStyle.State_Selected
        painter.setPen(self.pen())
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.curve_path())


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
        angle = self.end_angle()        # follows the curve when bent
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


#: Conversion from millimetres to each supported display unit.
_UNIT_PER_MM = {"mm": 1.0, "cm": 0.1, "in": 1.0 / 25.4}
#: Selectable end-cap styles for a dimension line.
DIM_CAPS = ("arrows", "ticks", "dots", "none")


class DimensionItem(LineItem):
    """A measured line with configurable style: end caps (arrows / ticks /
    dots / none), optional perpendicular extension lines, a solid or
    dashed line, and a length label whose unit, decimals and prefix/suffix
    are all adjustable (length derived from the scene dpi). Edited like a
    line via its endpoints; the label updates live as the endpoints move."""

    HEAD = 10
    TICK = 7               # half-length of a tick slash
    DOT_R = 4              # dot-cap radius
    EXT = 14              # half-length of an extension (witness) line
    _LABEL_PAD = 60        # boundingRect slack for caps + label text

    # Style defaults live at class level (immutable), so an unstyled
    # dimension carries no per-instance state until something is set.
    cap_style = "arrows"   # one of DIM_CAPS
    extension = False      # draw perpendicular witness lines at the ends
    dash = False           # dashed dimension + extension lines
    unit = "mm"            # mm | cm | in
    decimals = 1
    prefix = ""
    suffix = ""

    def boundingRect(self):
        extra = self.HEAD + self.pen().widthF() + self._LABEL_PAD
        return super().boundingRect().adjusted(-extra, -extra, extra, extra)

    def length_mm(self) -> float:
        scene = self.scene()
        dpi = getattr(scene, "dpi", 96) if scene is not None else 96
        return self.line().length() / max(dpi, 1) * 25.4

    def length_in_unit(self) -> float:
        return self.length_mm() * _UNIT_PER_MM.get(self.unit, 1.0)

    def _label_text(self) -> str:
        value = f"{self.length_in_unit():.{self.decimals}f}"
        return f"{self.prefix}{value} {self.unit}{self.suffix}"

    def _line_pen(self) -> QPen:
        pen = QPen(self.pen())
        pen.setStyle(Qt.DashLine if self.dash else Qt.SolidLine)
        return pen

    def _head(self, tip: QPointF, other: QPointF) -> QPolygonF:
        angle = math.atan2(tip.y() - other.y(), tip.x() - other.x())
        left = tip - QPointF(math.cos(angle - math.pi / 7) * self.HEAD,
                             math.sin(angle - math.pi / 7) * self.HEAD)
        right = tip - QPointF(math.cos(angle + math.pi / 7) * self.HEAD,
                              math.sin(angle + math.pi / 7) * self.HEAD)
        return QPolygonF([tip, left, right])

    def _draw_caps(self, painter, ln, angle, color):
        width = self.pen().widthF()
        if self.cap_style == "arrows":
            painter.setPen(QPen(color, width))
            painter.setBrush(QBrush(color))
            painter.drawPolygon(self._head(ln.p2(), ln.p1()))
            painter.drawPolygon(self._head(ln.p1(), ln.p2()))
        elif self.cap_style == "ticks":
            painter.setPen(QPen(color, max(width, 1)))
            d = QPointF(math.cos(angle + math.pi / 4),
                        math.sin(angle + math.pi / 4)) * self.TICK
            for p in (ln.p1(), ln.p2()):
                painter.drawLine(p - d, p + d)
        elif self.cap_style == "dots":
            painter.setPen(QPen(color, width))
            painter.setBrush(QBrush(color))
            for p in (ln.p1(), ln.p2()):
                painter.drawEllipse(p, self.DOT_R, self.DOT_R)

    def paint(self, painter, option, widget=None):
        ln = self.line()
        if ln.length() < 1:
            return
        color = self.pen().color()
        angle = math.atan2(ln.dy(), ln.dx())
        perp = QPointF(math.sin(angle), -math.cos(angle))

        painter.setBrush(Qt.NoBrush)
        painter.setPen(self._line_pen())
        painter.drawLine(ln)                           # the measured line
        if self.extension:
            for p in (ln.p1(), ln.p2()):
                painter.drawLine(p - perp * self.EXT, p + perp * self.EXT)
        self._draw_caps(painter, ln, angle, color)

        # length label, offset just off the line at its midpoint
        mid = QPointF((ln.x1() + ln.x2()) / 2, (ln.y1() + ln.y2()) / 2)
        tp = mid + perp * 14
        painter.save()
        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QPen(color))
        painter.setBrush(Qt.NoBrush)
        text = self._label_text()
        fm = painter.fontMetrics()
        painter.drawText(
            QPointF(tp.x() - fm.horizontalAdvance(text) / 2,
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
    #: emitted after the colour-picker samples a colour: (hex name,
    #: "stroke" or "fill" — which colour it landed in).
    color_picked = pyqtSignal(str, str)

    def __init__(self, width: int = 800, height: int = 600, parent=None):
        super().__init__(parent)
        self.tool = POINTER
        self.pen = QPen(QColor("#1a1a1a"), 2)
        self.pen.setCapStyle(Qt.RoundCap)
        self.pen.setJoinStyle(Qt.RoundJoin)
        self.fill_color = QColor("#4aa3ff")
        self.fill_color2 = QColor("#ffffff")  # gradient end colour
        self.fill_style = "solid"             # solid | linear | radial | sun
        self.fill_angle = 90.0                # linear gradient direction
        self.fill_enabled = False
        self.bucket_vector = False        # bucket output: raster vs vector
        self.dim_cap = "arrows"           # end-cap style for new dimensions
        self.dim_orientation = "aligned"  # aligned | horizontal | vertical
        self.chem_atom = "C"              # label placed by the atom tool
        self.plan_element = "wall"        # room-layout element to place
        self.elec_element = "resistor"    # electrical element to place
        self.optics_element = "laser"     # optics symbol to place
        self.vacuum_element = "chamber"   # vacuum symbol to place
        self.labware_element = "beaker"   # glassware symbol to place
        self.flow_element = "process"     # flowchart node to place
        self.net_element = "server"       # network symbol to place
        self.pid_element = "tank"         # P&ID symbol to place
        self.arrow_element = "arrow_right"  # annotation arrow to place
        self.bio_element = "cell"         # biology symbol to place
        self.math_element = "axes_2d"     # math/graph symbol to place
        self.chem_fixed = True            # ChemDraw-style fixed length + angle
        self.bond_length_mm = 6.0         # predefined bond length (mm)
        self._chain_pts = None            # vertices of an in-progress chain
        self._chain_preview = None        # rubber-band segment to the cursor
        self._erase_last = None           # previous eraser point while dragging

        # The grid is specified as a physical distance in millimetres
        # between adjacent lines; the pixel spacing is derived from the
        # canvas dpi (see grid_size). Smaller mm -> finer cells.
        self.grid_mm = 1.0
        self.snap_enabled = True
        self.show_grid = True
        self.infinite = True      # infinite paper by default (grid fills view)
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
        any scene-level selection handles). `items()` is top-first, so
        reverse before the (stable) z-sort — otherwise items sharing a z
        come back top-first, contradicting the documented order."""
        from .handles import Handle
        ordered = list(self.items())[::-1]            # bottom-to-top
        ordered.sort(key=lambda i: i.zValue())        # stable: honour z
        return [i for i in ordered
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
        if (self.snap_enabled
                and self.tool in _SHAPE_TOOLS + (TEXT,) + _PLACE_TOOLS
                + _CHEM_TOOLS):
            return self.snap(pos)
        return pos

    # ------------------------------------------------------------ brushes
    def current_brush(self) -> QBrush:
        if not self.fill_enabled:
            return QBrush(Qt.NoBrush)
        from . import gradient
        return gradient.brush_for(self.fill_style, self.fill_color,
                                  self.fill_color2, self.fill_angle)

    # ------------------------------------------------------------ grouping
    def group_selection(self):
        selected = {i for i in self.selectedItems()
                    if i.parentItem() is None}
        if len(selected) < 2:
            return
        # Add children in their CURRENT stacking order (bottom to top) and
        # give them sequential z, so the group keeps which item is in
        # front — selectedItems() order is arbitrary, which previously
        # let a later child cover earlier ones after grouping.
        ordered = [i for i in reversed(self.items()) if i in selected]
        group = GroupItem()
        self.addItem(group)
        # Reparenting must not snap: addToGroup repositions each child
        # into group coords, and snapping that would shift them.
        self.clear_handles()
        was_snap = self.snap_enabled
        self.snap_enabled = False
        for z, item in enumerate(ordered):
            item.setZValue(z)
            # Clear the child's own selection flag before it becomes a group
            # member — otherwise it stays 'selected' inside the group and,
            # once ungrouped, is stuck selected but unknown to the scene.
            item.setSelected(False)
            group.addToGroup(item)
        self.snap_enabled = was_snap
        self.clearSelection()
        group.setSelected(True)
        self.changed_by_user.emit()

    def ungroup_selection(self):
        self.clear_handles()
        was_snap = self.snap_enabled
        self.snap_enabled = False
        freed = []
        for item in list(self.selectedItems()):
            if isinstance(item, QGraphicsItemGroup):
                children = item.childItems()
                self.destroyItemGroup(item)
                for child in children:
                    child.setFlags(_ITEM_FLAGS)
                    freed.append(child)
        self.snap_enabled = was_snap
        self.clearSelection()
        for child in freed:
            # destroyItemGroup leaves children with a stale 'selected' flag
            # that the scene never registered; toggle it so setSelected(True)
            # is a real change the scene records (else selectedItems() stays
            # empty and re-grouping / deselecting break).
            child.setSelected(False)
            child.setSelected(True)
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

    # --------------------------------------------------------- chain tool
    def _chain_click(self, event):
        """Click-to-click connected bonds: each click drops a vertex; the
        bond runs from the previous vertex. Clicking the last vertex again
        (or any non-left button) ends the chain."""
        if event.button() != Qt.LeftButton:
            self.end_chain()
            return
        raw = event.scenePos()
        if self._chain_pts is None:
            pos = self._tool_pos(raw)
            self._chain_pts = [pos]
            self._chain_preview = LineItem(QLineF(pos, pos))
            self._chain_preview.setPen(QPen(self.pen))
            self.addItem(self._chain_preview)
            return
        last = self._chain_pts[-1]
        if QLineF(last, raw).length() < max(self.grid_size, 6):
            self.end_chain()                 # clicked the last vertex -> finish
            return
        pos = self._chem_constrain(last, raw)   # fixed length + 30° angle
        bond = LineItem(QLineF(last, pos))
        bond.setPen(QPen(self.pen))
        self.addItem(bond)
        center_origin(bond)
        self._chain_pts.append(pos)
        self._chain_preview.setLine(QLineF(pos, pos))
        self.changed_by_user.emit()

    def end_chain(self):
        """Finish an in-progress bond chain, removing the preview segment."""
        if self._chain_preview is not None:
            self.removeItem(self._chain_preview)
        self._chain_preview = None
        self._chain_pts = None

    # ------------------------------------------------------------ tools
    def mousePressEvent(self, event):
        if self.tool == CHEM_CHAIN:
            self._chain_click(event)
            return
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
        if self.tool == PICKER:                     # eyedropper: one click
            self._pick_color(event.scenePos(),
                             fill=bool(event.modifiers() & Qt.ShiftModifier))
            return

        pos = self._tool_pos(event.scenePos())
        self._drawing = True
        self._start = pos

        if self.tool == ERASER:
            self._erase_last = event.scenePos()
            self._erase(event.scenePos(), event.scenePos())
        elif self.tool == PENCIL:
            self.pencil_begin(event.scenePos())
        elif self.tool in _TWO_POINT_TOOLS:
            cls = {ARROW: ArrowItem, DIMENSION: DimensionItem}.get(
                self.tool, LineItem)
            self._temp_item = cls(QLineF(pos, pos))
            self._temp_item.setPen(self.pen)
            if self.tool == DIMENSION:
                self._temp_item.cap_style = self.dim_cap
            self.addItem(self._temp_item)
        elif self.tool in _RECT_TOOLS:
            item = self._new_rect_item(self.tool)
            if self.tool == ROOM:                       # a room = wall outline
                wall = QPen(QColor("#333333"),
                            max(self.pen.widthF() * 2, 4))
                wall.setJoinStyle(Qt.MiterJoin)
                item.setPen(wall)
                item.setBrush(QBrush(Qt.NoBrush))       # just the space
            else:
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
        elif self.tool in _CHEM_BOND_TOOLS:
            self._temp_item = self._new_chem_bond(pos)
            self.addItem(self._temp_item)
        elif self.tool in _CHEM_PLACE_TOOLS:        # rings / atom: one click
            self._drawing = False
            if self.tool == CHEM_ATOM:
                self.place_chem_atom(self.chem_atom, pos)
            else:
                self.place_chem_ring(self.tool.split("_")[1], pos)
        elif self.tool == PLAN_PLACE:               # room-layout element
            self._drawing = False
            self.place_plan_element(self.plan_element, pos)
        elif self.tool == ELEC_PLACE:               # electrical symbol
            self._drawing = False
            self.place_elec_element(self.elec_element, pos)
        elif self.tool == OPTICS_PLACE:             # optics symbol
            self._drawing = False
            self.place_optics_element(self.optics_element, pos)
        elif self.tool == VACUUM_PLACE:             # vacuum symbol
            self._drawing = False
            self.place_vacuum_element(self.vacuum_element, pos)
        elif self.tool == LABWARE_PLACE:            # glassware symbol
            self._drawing = False
            self.place_labware_element(self.labware_element, pos)
        elif self.tool == FLOW_PLACE:               # flowchart node
            self._drawing = False
            self.place_flow_element(self.flow_element, pos)
        elif self.tool == NET_PLACE:                # network symbol
            self._drawing = False
            self.place_net_element(self.net_element, pos)
        elif self.tool == PID_PLACE:                # P&ID symbol
            self._drawing = False
            self.place_pid_element(self.pid_element, pos)
        elif self.tool == ARROW_PLACE:              # annotation arrow
            self._drawing = False
            self.place_arrow_element(self.arrow_element, pos)
        elif self.tool == BIO_PLACE:                # biology symbol
            self._drawing = False
            self.place_bio_element(self.bio_element, pos)
        elif self.tool == MATH_PLACE:               # math / graph symbol
            self._drawing = False
            self.place_math_element(self.math_element, pos)

    def mouseMoveEvent(self, event):
        if self.tool == CHEM_CHAIN and self._chain_pts is not None:
            last = self._chain_pts[-1]
            self._chain_preview.setLine(
                QLineF(last, self._chem_constrain(last, event.scenePos())))
            return
        if not self._drawing:
            super().mouseMoveEvent(event)
            return
        if self.tool == ERASER:
            self._erase(self._erase_last, event.scenePos())
            self._erase_last = event.scenePos()
            return
        if self.tool == PENCIL:
            self.pencil_extend(event.scenePos())
            return
        if self._temp_item is None:
            return
        pos = self._tool_pos(event.scenePos())
        if self.tool in _TWO_POINT_TOOLS:
            if self.tool == DIMENSION:
                pos = self._dim_constrain(pos)
            self._temp_item.setLine(QLineF(self._start, pos))
        elif self.tool in _CHEM_BOND_TOOLS:
            end = self._chem_constrain(self._start, event.scenePos())
            self._update_chem_bond(self._temp_item, self._start, end)
        else:
            self._apply_rect(self._temp_item, self._shape_rect(pos))

    def _dim_constrain(self, pos: QPointF) -> QPointF:
        """Force a dimension to a pure horizontal/vertical line (so it
        measures Δx or Δy only) for those ruler orientations."""
        if self.dim_orientation == "horizontal":
            return QPointF(pos.x(), self._start.y())
        if self.dim_orientation == "vertical":
            return QPointF(self._start.x(), pos.y())
        return pos

    # ------------------------------------------------------------ chemistry
    def _chem_constrain(self, start: QPointF, pos: QPointF) -> QPointF:
        """ChemDraw-style: the bond endpoint sits at the predefined bond
        length from *start*, in the cursor's direction snapped to 30°. When
        fixed mode is off, fall back to plain grid snapping."""
        if not self.chem_fixed:
            return self._tool_pos(pos)
        dx, dy = pos.x() - start.x(), pos.y() - start.y()
        if dx == 0 and dy == 0:
            return QPointF(start)
        step = math.radians(30)
        ang = round(math.atan2(dy, dx) / step) * step
        length = self.bond_length_mm / 25.4 * self.dpi
        return QPointF(start.x() + length * math.cos(ang),
                       start.y() + length * math.sin(ang))

    def _chem_gap(self) -> float:
        """Spacing between the parallel lines of a multiple bond / the
        half-width of a wedge — scaled off the current stroke width."""
        return max(3.0, self.pen.widthF() * 2.0 + 2.0)

    def _new_chem_bond(self, pos: QPointF):
        if self.tool == CHEM_WEDGE:
            item = PolygonItem(chemistry.wedge_polygon(pos, pos,
                                                       self._chem_gap()))
            item.setPen(QPen(self.pen.color(), 1))
            item.setBrush(QBrush(self.pen.color()))     # solid filled wedge
        else:
            kind = self.tool.split("_")[1]              # single/double/...
            item = PathItem(chemistry.bond_path(kind, pos, pos,
                                                self._chem_gap()))
            item.setPen(QPen(self.pen))
            item.setBrush(QBrush(Qt.NoBrush))
        return item

    def _update_chem_bond(self, item, p1: QPointF, p2: QPointF):
        if self.tool == CHEM_WEDGE:
            item.setPolygon(chemistry.wedge_polygon(p1, p2, self._chem_gap()))
        else:
            item.setPath(chemistry.bond_path(self.tool.split("_")[1],
                                             p1, p2, self._chem_gap()))

    def place_chem_ring(self, kind: str, center: QPointF):
        """Drop a ready-made ring (editable) centred at *center*."""
        r = 6.0 / 25.4 * self.dpi                       # ~6 mm radius
        poly = chemistry.ring_polygon(kind, center, r)
        side = "pentagon" if kind == "cyclopentane" else "hexagon"
        ring = PolygonItem(poly, kind=side)
        ring.setPen(QPen(self.pen))
        ring.setBrush(self.current_brush())
        self.clearSelection()
        if chemistry.is_aromatic(kind):                 # benzene: inner circle
            ir = r * 0.55
            circle = EllipseItem(QRectF(center.x() - ir, center.y() - ir,
                                        2 * ir, 2 * ir))
            circle.setPen(QPen(self.pen))
            circle.setBrush(QBrush(Qt.NoBrush))
            group = GroupItem()
            self.addItem(group)
            for z, it in enumerate((ring, circle)):
                it.setZValue(z)
                group.addToGroup(it)
            center_origin(group)
            group.setSelected(True)
        else:
            self.addItem(ring)
            center_origin(ring)
            ring.setSelected(True)
        self.changed_by_user.emit()

    def _nearest_bond_end(self, scene_pos: QPointF, tol: float):
        """The nearest line/path endpoint to *scene_pos* within *tol*, so an
        atom label snaps onto the end of a bond. Returns None if none near."""
        best, best_d = None, tol
        for it in self.vector_items():
            pts = []
            if isinstance(it, LineItem):            # single/chain/arrow bonds
                ln = it.line()
                pts = [it.mapToScene(ln.p1()), it.mapToScene(ln.p2())]
            elif isinstance(it, PathItem):          # double/triple/hash bonds
                path = it.path()
                pts = [it.mapToScene(QPointF(path.elementAt(i).x,
                                             path.elementAt(i).y))
                       for i in range(path.elementCount())]
            for p in pts:
                d = QLineF(scene_pos, p).length()
                if d < best_d:
                    best, best_d = p, d
        return best

    def place_chem_atom(self, text: str, center: QPointF):
        """Place an atom/group label, snapping onto a nearby bond end so it
        sits exactly at the terminus (e.g. the O of a C=O)."""
        tol = self.bond_length_mm / 25.4 * self.dpi * 0.4
        anchor = self._nearest_bond_end(center, tol)
        if anchor is not None:
            center = anchor
        item = TextItem(text or "C")
        item.setDefaultTextColor(self.pen.color())
        self.addItem(item)
        c = item.boundingRect().center()        # exact centre incl. margins
        was_snap = self.snap_enabled
        self.snap_enabled = False               # sit exactly on the bond end
        item.setPos(center.x() - c.x(), center.y() - c.y())
        self.snap_enabled = was_snap
        center_origin(item)
        self.clearSelection()
        item.setSelected(True)
        self.changed_by_user.emit()

    # ------------------------------------------------------------ paint tools
    def _erase(self, p1: QPointF, p2: QPointF):
        """Erase the raster layer to white along p1->p2 (MS-Paint eraser)."""
        pixmap = self.raster_item.pixmap()
        if pixmap.isNull():
            return
        painter = QPainter(pixmap)
        pen = QPen(Qt.white, max(self.pen.widthF() * 4, 12))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        self.raster_item.setPixmap(pixmap)

    def _pick_color(self, pos: QPointF, fill: bool = False):
        """Colour picker / eyedropper: sample the colour under the cursor
        (raster, images and vector items, as drawn) into the stroke pen —
        or into the fill colour when *fill* (Shift+click)."""
        from PyQt5.QtGui import QImage
        img = QImage(1, 1, QImage.Format_ARGB32)
        img.fill(Qt.white)
        painter = QPainter(img)
        self.render(painter, QRectF(0, 0, 1, 1),
                    QRectF(pos.x(), pos.y(), 1, 1))
        painter.end()
        color = QColor(img.pixel(0, 0))
        if fill:
            self.fill_color = color
        else:
            self.pen.setColor(color)
        self.color_picked.emit(color.name(), "fill" if fill else "stroke")

    # ------------------------------------------------ symbol libraries (plan/elec)
    def place_plan_element(self, name: str, center: QPointF):
        """Drop a top-view room-layout element (walls/furniture/fittings),
        grouped and editable, centred on *center*."""
        from . import floorplan
        self._place_symbol(floorplan, name, center)

    def place_elec_element(self, name: str, center: QPointF):
        """Drop an electrical symbol (component or installation marker)."""
        from . import electrical
        self._place_symbol(electrical, name, center)

    def place_optics_element(self, name: str, center: QPointF):
        """Drop an optics / photonics symbol (beam-path diagrams)."""
        from . import optics
        self._place_symbol(optics, name, center)

    def place_vacuum_element(self, name: str, center: QPointF):
        """Drop a vacuum / surface-science symbol (UHV systems)."""
        from . import vacuum
        self._place_symbol(vacuum, name, center)

    def place_labware_element(self, name: str, center: QPointF):
        """Drop a lab-glassware / apparatus symbol."""
        from . import labware
        self._place_symbol(labware, name, center)

    def place_flow_element(self, name: str, center: QPointF):
        """Drop a flowchart node symbol."""
        from . import flowchart
        self._place_symbol(flowchart, name, center)

    def place_net_element(self, name: str, center: QPointF):
        """Drop a network / IT architecture symbol."""
        from . import network
        self._place_symbol(network, name, center)

    def place_pid_element(self, name: str, center: QPointF):
        """Drop a P&ID / process-flow symbol."""
        from . import pid
        self._place_symbol(pid, name, center)

    def place_arrow_element(self, name: str, center: QPointF):
        """Drop an annotation arrow / callout / banner."""
        from . import arrows
        self._place_symbol(arrows, name, center)

    def place_bio_element(self, name: str, center: QPointF):
        """Drop a biology / life-science symbol."""
        from . import biology
        self._place_symbol(biology, name, center)

    def place_math_element(self, name: str, center: QPointF):
        """Drop a math / graph / vector symbol."""
        from . import maths
        self._place_symbol(maths, name, center)

    def _place_symbol(self, module, name: str, center: QPointF):
        """Build items from a spec-library module's `build_specs`/`size_mm`
        and place them centred on *center* (grouped if multi-part).

        Symbols are sized as a fraction of the PAGE, not in absolute mm —
        the page width represents `module.REFERENCE_MM` of real space, so a
        whole room (or circuit) fits the drawing (e.g. a 480 mm chair on a
        4.8 m reference is ~1/10 of the page)."""
        from .ai_assistant import _spec_to_item
        w_mm, h_mm = module.size_mm(name)
        ref = getattr(module, "REFERENCE_MM", 4800.0)
        scale = (self.sceneRect().width() or 1) / ref
        w = w_mm * scale
        h = h_mm * scale
        items = [it for it in (_spec_to_item(s)
                               for s in module.build_specs(name, w, h))
                 if it is not None]
        if not items:
            return
        dx, dy = center.x() - w / 2, center.y() - h / 2
        was_snap = self.snap_enabled
        self.snap_enabled = False                # already grid-snapped centre
        self.clearSelection()
        if len(items) == 1:
            item = items[0]
            item.moveBy(dx, dy)
            self.addItem(item)
            center_origin(item)
            item.setSelected(True)
        else:
            group = GroupItem()
            self.addItem(group)
            for z, item in enumerate(items):
                item.moveBy(dx, dy)
                item.setZValue(z)
                group.addToGroup(item)
            center_origin(group)
            group.setSelected(True)
        self.snap_enabled = was_snap
        self.changed_by_user.emit()

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
        if self.tool == ERASER:
            self._erase_last = None
            self.changed_by_user.emit()         # raster change is undoable
            return
        if self.tool == PENCIL:
            self.pencil_end()
            return
        item = self._temp_item
        self._temp_item = None
        if item is None:
            return
        if self.tool == ROOM:
            self._finish_room(item)
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

    def _finish_room(self, preview):
        """Turn the dragged rectangle into a room: four solid wall bars with
        an empty (hollow) square at each corner where the walls meet."""
        rect = QRectF(preview.rect()).normalized()
        self.removeItem(preview)
        if rect.width() < 2 or rect.height() < 2:
            return
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
        t = max(min(w, h) * 0.02, 2.0)               # wall depth
        wall_pen = QPen(QColor("#222222"), 1)
        wall_pen.setJoinStyle(Qt.MiterJoin)
        corner_pen = QPen(QColor("#333333"), 2)
        corner_pen.setJoinStyle(Qt.MiterJoin)
        parts = []
        # solid wall bars, stopping short of the corners
        for r in (QRectF(x + t, y, w - 2 * t, t),            # top
                  QRectF(x + t, y + h - t, w - 2 * t, t),    # bottom
                  QRectF(x, y + t, t, h - 2 * t),            # left
                  QRectF(x + w - t, y + t, t, h - 2 * t)):   # right
            bar = RectItem(r)
            bar.setPen(QPen(wall_pen))
            bar.setBrush(QBrush(QColor("#222222")))
            parts.append(bar)
        # empty corner squares
        for r in (QRectF(x, y, t, t), QRectF(x + w - t, y, t, t),
                  QRectF(x, y + h - t, t, t),
                  QRectF(x + w - t, y + h - t, t, t)):
            sq = RectItem(r)
            sq.setPen(QPen(corner_pen))
            sq.setBrush(QBrush(Qt.NoBrush))
            parts.append(sq)
        group = GroupItem()
        self.addItem(group)
        self.clearSelection()
        for z, it in enumerate(parts):
            it.setZValue(z)
            group.addToGroup(it)
        center_origin(group)
        group.setSelected(True)
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
        if tool in (RECT, ROOM):
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
            if item.bend() is not None:
                item.set_bend(t.map(item.bend()))
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
    #: (list of local file paths, dropped QImage or None, scene pos) on drop.
    content_dropped = pyqtSignal(list, object, QPointF)

    MIN_ZOOM, MAX_ZOOM = 0.1, 16.0

    def __init__(self, scene: PaintScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing
                            | QPainter.SmoothPixmapTransform)
        self.setMouseTracking(True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setFocusPolicy(Qt.StrongFocus)   # so Enter/Esc reach the view
        self.setAcceptDrops(True)             # drop images/files onto canvas
        # Repaint the whole viewport on every change: partial updates
        # leave stale selection dashes / handles behind after deselect.
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)

    # --------------------------------------------------------- drag & drop
    @staticmethod
    def _has_droppable(mime) -> bool:
        return mime.hasImage() or mime.hasUrls()

    def dragEnterEvent(self, event):
        if self._has_droppable(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if self._has_droppable(event.mimeData()):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        mime = event.mimeData()
        if not self._has_droppable(mime):
            super().dropEvent(event)
            return
        paths = [u.toLocalFile() for u in mime.urls()
                 if u.isLocalFile()] if mime.hasUrls() else []
        image = mime.imageData() if mime.hasImage() else None
        self.content_dropped.emit(paths, image, self.mapToScene(event.pos()))
        event.acceptProposedAction()

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
            if isinstance(item, LineItem):
                # A line reads as a line, not a box: dash along its own
                # geometry (the curve when bent) — the endpoint handles
                # already mark it, so no bounding rectangle.
                painter.drawPath(
                    item.sceneTransform().map(item.curve_path()))
            else:
                painter.drawRect(
                    item.sceneBoundingRect().adjusted(-1, -1, 1, 1))

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
        is in infinite-paper mode; otherwise follow the page rect. In
        infinite mode the whole canvas is white (no themed surround)."""
        if getattr(self.scene(), "infinite", False):
            m = 100000
            self.setSceneRect(QRectF(-m, -m, 2 * m, 2 * m))
            self.setBackgroundBrush(QBrush(Qt.white))
        else:
            self.setSceneRect(QRectF())   # follow the scene's page rect
            self.setBackgroundBrush(QBrush())   # back to the theme surround

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
        if event.key() == Qt.Key_Escape:        # finish a bond chain
            self.scene().end_chain()
        super().keyPressEvent(event)
