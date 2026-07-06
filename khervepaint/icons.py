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


# The wordmark letters are drawn as stroked vector paths (not text) so
# the mark renders identically on every platform without depending on a
# system font. Each glyph is built in a unit box (x, y in 0..1) and
# transformed into place by _stroke. Caps fill the box height; lowercase
# glyphs sit on the baseline (y=1) at *xh* of the cap height.


def _glyph_K():
    w = 0.82
    path = QPainterPath()
    path.moveTo(0.0, 0.0); path.lineTo(0.0, 1.0)          # stem
    path.moveTo(0.0, 0.52); path.lineTo(w, 0.0)           # upper arm
    path.moveTo(0.0, 0.52); path.lineTo(w, 1.0)           # lower arm
    return path, w


def _glyph_P():
    w = 0.70
    path = QPainterPath()
    path.moveTo(0.0, 0.0); path.lineTo(0.0, 1.0)          # stem
    path.moveTo(0.0, 0.0)                                  # bowl
    path.cubicTo(w * 1.25, 0.02, w * 1.25, 0.52, 0.0, 0.54)
    return path, w


def _glyph_a(xh):
    w = 0.72
    top = 1.0 - xh
    path = QPainterPath()
    path.addEllipse(QRectF(0.0, top, w, xh))              # bowl
    path.moveTo(w, top); path.lineTo(w, 1.0)              # right stem
    return path, w


def _glyph_i(xh):
    w = 0.20
    top = 1.0 - xh
    path = QPainterPath()
    path.moveTo(w / 2, top); path.lineTo(w / 2, 1.0)      # stem
    path.moveTo(w / 2, top - 0.20)                        # dot (round cap)
    path.lineTo(w / 2, top - 0.19)
    return path, w


def _glyph_n(xh):
    w = 0.66
    top = 1.0 - xh
    path = QPainterPath()
    path.moveTo(0.0, top); path.lineTo(0.0, 1.0)          # left stem
    path.moveTo(0.0, top + 0.12)                          # arch + right leg
    path.cubicTo(0.0, top, w, top, w, top + 0.12)
    path.lineTo(w, 1.0)
    return path, w


def _glyph_t(xh):
    w = 0.42
    top = 1.0 - xh
    path = QPainterPath()
    path.moveTo(w * 0.40, top - 0.16); path.lineTo(w * 0.40, 0.96)   # stem
    path.moveTo(0.0, top); path.lineTo(w, top)            # crossbar
    return path, w


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


def _paint_wordmark(p, rect):
    """Draw 'KPaint' on one baseline: capital K, capital P, then 'aint'."""
    xh = 0.66
    items = [_glyph_K(), _glyph_P(), _glyph_a(xh), _glyph_i(xh),
             _glyph_n(xh), _glyph_t(xh)]
    gap = 0.10
    total = sum(w for _path, w in items) + gap * (len(items) - 1)
    pad_x, pad_y = rect.width() * 0.11, rect.height() * 0.22
    ch = min(rect.height() - 2 * pad_y, (rect.width() - 2 * pad_x) / total)
    x = rect.x() + (rect.width() - total * ch) / 2.0
    top = rect.y() + (rect.height() - ch) / 2.0
    for path, gw in items:
        _stroke(p, path, _INK, QRectF(x, top, gw * ch, ch), 0.15)
        x += (gw + gap) * ch


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
    _paint_wordmark(p, QRectF(x, y + h * 0.05, w, h * 0.44))
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
