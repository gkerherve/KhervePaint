"""Toolbar icon helpers — qtawesome MDI glyphs with graceful fallback.

Same icon system as the rest of the Kherve family: themed Material
Design icons via qtawesome. When qtawesome is missing the actions
fall back to their text labels, so the app still works.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import (QColor, QIcon, QPainter, QPainterPath, QPen,
                         QPixmap, QTransform)

try:
    import qtawesome as qta
except ImportError:          # pragma: no cover - optional dependency
    qta = None

#: Glyph colour for neutral icons — set by the active theme.
DEFAULT_COLOR = "#444444"

#: The app mark: a "KPaint" wordmark and a brush over a light-yellow tile
#: (KhervePaint's colour), in the same style as KherveBook's icon.
_TILE_FILL = "#fdf1a0"
_TILE_EDGE = "#e6cf6a"
_INK = "#2b2b2b"


def set_icon_color(color: str):
    """Called by style.apply_style so icons follow the theme."""
    global DEFAULT_COLOR
    DEFAULT_COLOR = color


def icon(name: str, color: str = None) -> QIcon:
    """Return the qtawesome icon *name* (e.g. "mdi.pencil"), or a null
    icon if qtawesome is unavailable."""
    if qta is None:
        return QIcon()
    try:
        return qta.icon(name, color=color or DEFAULT_COLOR)
    except Exception:
        return QIcon()


# The brush schematic is a stroked vector path (font-independent); the
# "KPaint" wordmark itself is drawn with a normal system font.


def _stroke(p, path, color, box, weight):
    """Map *path* (unit box) into *box* and stroke it in *color* with a
    uniform pen (width = *weight* of the box height)."""
    t = QTransform()
    t.translate(box.x(), box.y())
    t.scale(box.width(), box.height())
    pen = QPen(QColor(color))
    pen.setWidthF(weight * box.height())
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(t.map(path))


def _paint_tile(p, s):
    """Fill the light-yellow rounded tile; return the inner rect."""
    m = s * 0.06
    radius = s * 0.22
    rect = QRectF(m, m, s - 2 * m, s - 2 * m)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(_TILE_FILL))
    p.drawRoundedRect(rect, radius, radius)
    pen = QPen(QColor(_TILE_EDGE))
    pen.setWidthF(max(1.0, s * 0.02))
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(rect, radius, radius)
    return rect


def _paint_wordmark(p, rect, text):
    """Draw *text* centred in *rect* with a normal bold system font,
    scaled up to the largest size that still fits the tile width."""
    from PyQt5.QtGui import QFont, QFontMetricsF
    avail = rect.width() * 0.80
    font = QFont("Segoe UI")
    font.setBold(True)
    size = 1.0
    while size < rect.height():
        font.setPointSizeF(size + 0.5)
        fm = QFontMetricsF(font)
        if fm.horizontalAdvance(text) > avail or fm.height() > rect.height():
            break
        size += 0.5
    font.setPointSizeF(size)
    p.setFont(font)
    p.setPen(QColor(_INK))
    p.drawText(rect, Qt.AlignCenter, text)


def _paint_brush(p, box):
    """Stroke a schematic paintbrush (handle, ferrule, bristle tuft)."""
    path = QPainterPath()
    # Handle.
    path.moveTo(0.43, 0.00); path.lineTo(0.57, 0.00)
    path.lineTo(0.57, 0.42); path.lineTo(0.43, 0.42); path.lineTo(0.43, 0.00)
    # Ferrule (metal band), a little wider, with a seam line.
    path.moveTo(0.38, 0.42); path.lineTo(0.62, 0.42)
    path.lineTo(0.62, 0.55); path.lineTo(0.38, 0.55); path.lineTo(0.38, 0.42)
    path.moveTo(0.38, 0.485); path.lineTo(0.62, 0.485)
    # Bristle tuft: flare out below the ferrule, then taper to a point.
    path.moveTo(0.38, 0.55); path.lineTo(0.30, 0.74)
    path.lineTo(0.50, 1.00); path.lineTo(0.70, 0.74); path.lineTo(0.62, 0.55)
    # A few bristle lines.
    path.moveTo(0.45, 0.60); path.lineTo(0.44, 0.92)
    path.moveTo(0.50, 0.60); path.lineTo(0.50, 0.96)
    path.moveTo(0.55, 0.60); path.lineTo(0.56, 0.92)
    _stroke(p, path, _INK, box, 0.05)


def _paint_kpaint(size):
    """Draw the KhervePaint mark on a light-yellow tile: the single-line
    'KPaint' wordmark above a schematic brush, at every size."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    s = float(size)
    rect = _paint_tile(p, s)
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    _paint_wordmark(p, QRectF(x, y + h * 0.05, w, h * 0.44), "KPaint")
    bw, bh = w * 0.34, h * 0.40
    _paint_brush(p, QRectF(x + (w - bw) / 2.0, y + h * 0.54, bw, bh))
    p.end()
    return pm


def app_icon() -> QIcon:
    """Window/taskbar icon: the single-line 'KPaint' wordmark above a
    brush on a light-yellow tile, rendered at each standard size."""
    ic = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        ic.addPixmap(_paint_kpaint(size))
    return ic


def line_width_icon(width: float, color: str = None,
                    w: int = 72, h: int = 16) -> QIcon:
    """A horizontal stroke drawn at *width* pixels — a visual swatch for
    the line-width picker, so widths read as thin-to-thick lines."""
    from PyQt5.QtCore import Qt, QPointF
    from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap

    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color or DEFAULT_COLOR), max(1.0, float(width)))
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    y = h / 2
    painter.drawLine(QPointF(4, y), QPointF(w - 4, y))
    painter.end()
    return QIcon(pixmap)


def shape_icon(kind: str, color: str = None, size: int = 24) -> QIcon:
    """Draw a shape's own outline into an icon — used for shapes that
    have no Material Design glyph (e.g. parallelogram, heptagon)."""
    from PyQt5.QtCore import Qt, QRectF
    from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
    from . import canvas

    margin = max(2, size // 7)
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    is_arc = kind in canvas.ARC_KINDS
    if is_arc:
        outline = canvas.arc_path(kind, rect)
    elif kind in canvas.POLYGON_KINDS:
        outline = canvas.polygon_for_kind(kind, rect)
    else:
        return QIcon()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor(color or DEFAULT_COLOR), 1.5))
    painter.setBrush(Qt.NoBrush)
    if is_arc:
        painter.drawPath(outline)
    else:
        painter.drawPolygon(outline)
    painter.end()
    return QIcon(pixmap)
