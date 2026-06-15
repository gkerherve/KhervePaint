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

from PyQt5.QtGui import QIcon

try:
    import qtawesome as qta
except ImportError:          # pragma: no cover - optional dependency
    qta = None

#: Glyph colour for neutral icons — set by the active theme.
DEFAULT_COLOR = "#444444"


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


def app_icon() -> QIcon:
    """Window/taskbar icon: a 'K' wordmark over 'scribe' on a rounded
    tile (reads 'K scribe', not 'KS')."""
    from PyQt5.QtCore import Qt, QRectF
    from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap

    size = 256
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#2f6f9f"))
    p.drawRoundedRect(QRectF(10, 10, size - 20, size - 20), 44, 44)

    p.setPen(QColor("#ffffff"))
    big = QFont("Segoe UI", 132)
    big.setBold(True)
    p.setFont(big)
    p.drawText(QRectF(0, 6, size, size * 0.64), Qt.AlignCenter, "K")

    small = QFont("Segoe UI", 52)
    small.setItalic(True)
    p.setFont(small)
    p.drawText(QRectF(0, size * 0.60, size, size * 0.34),
               Qt.AlignCenter, "scribe")
    p.end()
    return QIcon(pm)


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
