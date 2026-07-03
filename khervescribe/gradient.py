"""Two-stop gradient fills for shapes.

A gradient fill is an ordinary QBrush whose QGradient uses
ObjectBoundingMode coordinates (0..1 relative to the item's bounding
rect), so it stretches with the shape when resized. Everything is
described by one JSON-able spec dict — {"kind": "linear"|"radial",
"c1": "#aarrggbb", "c2": "#aarrggbb", "angle": degrees} — shared by the
document snapshot (undo / legacy .kscribe) and the SVG writer/parser.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QPointF
from PyQt5.QtGui import (QBrush, QColor, QGradient, QLinearGradient,
                         QRadialGradient)

#: UI names for the fill styles, in combo order.
FILL_STYLES = ["solid", "linear", "radial"]


def angle_points(angle: float):
    """(x1, y1, x2, y2) of a linear gradient at *angle* degrees inside
    the unit box: 0 = left->right, 90 = top->bottom (y grows down)."""
    rad = math.radians(angle)
    dx, dy = math.cos(rad) / 2, math.sin(rad) / 2
    return 0.5 - dx, 0.5 - dy, 0.5 + dx, 0.5 + dy


def linear_brush(c1, c2, angle: float = 90.0) -> QBrush:
    x1, y1, x2, y2 = angle_points(angle)
    g = QLinearGradient(QPointF(x1, y1), QPointF(x2, y2))
    g.setCoordinateMode(QGradient.ObjectBoundingMode)
    g.setColorAt(0.0, QColor(c1))
    g.setColorAt(1.0, QColor(c2))
    return QBrush(g)


def radial_brush(c1, c2) -> QBrush:
    # radius 0.7071 (half the box diagonal) so the corners reach c2.
    g = QRadialGradient(QPointF(0.5, 0.5), 0.7071, QPointF(0.5, 0.5))
    g.setCoordinateMode(QGradient.ObjectBoundingMode)
    g.setColorAt(0.0, QColor(c1))
    g.setColorAt(1.0, QColor(c2))
    return QBrush(g)


def brush_for(style: str, c1, c2, angle: float = 90.0) -> QBrush:
    if style == "linear":
        return linear_brush(c1, c2, angle)
    if style == "radial":
        return radial_brush(c1, c2)
    return QBrush(QColor(c1))


def brush_spec(brush: QBrush):
    """*brush*'s gradient as a spec dict, or None for solid/no fills."""
    g = brush.gradient() if brush is not None else None
    if g is None:
        return None
    stops = g.stops()
    if not stops:
        return None
    c1, c2 = stops[0][1], stops[-1][1]
    spec = {"c1": c1.name(QColor.HexArgb), "c2": c2.name(QColor.HexArgb),
            "angle": 90.0}
    if g.type() == QGradient.RadialGradient:
        spec["kind"] = "radial"
    else:
        spec["kind"] = "linear"
        from PyQt5 import sip
        lg = sip.cast(g, QLinearGradient)
        dx = lg.finalStop().x() - lg.start().x()
        dy = lg.finalStop().y() - lg.start().y()
        if dx or dy:
            spec["angle"] = round(math.degrees(math.atan2(dy, dx)), 2) % 360
    return spec


def brush_from_spec(spec) -> QBrush:
    return brush_for(spec.get("kind", "linear"),
                     QColor(spec.get("c1", "#ff4aa3ff")),
                     QColor(spec.get("c2", "#ffffffff")),
                     float(spec.get("angle", 90.0)))
