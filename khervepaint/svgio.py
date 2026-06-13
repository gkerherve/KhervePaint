"""SVG import/export — the editable, default document format.

Two directions:

* **Write** (`save_svg`) emits clean, standard SVG: one element per
  native item, geometry in local coordinates with a `translate`/
  `rotate` transform, the raster layer as an embedded `<image>`, and
  KhervePaint-specific bits (grid settings, polygon kind, arrow flag)
  under a private ``kp:`` namespace so our own files round-trip
  losslessly while staying readable by any SVG tool.

* **Read** (`load_svg`) parses an arbitrary SVG into *editable* native
  items.  `<g>` becomes a `GroupItem` (so it can be ungrouped), the
  common primitives become their native items, and anything carrying a
  non-trivial (scaled/sheared) transform — or a `<path>` — becomes a
  `PathItem`.  This is what lets an imported SVG be broken apart and
  edited entity by entity.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import base64
import math
import re
import xml.etree.ElementTree as ET

from PyQt5.QtCore import QBuffer, QByteArray, QLineF, QPointF, QRectF, Qt
from PyQt5.QtGui import (QBrush, QColor, QFont, QPainterPath, QPen, QPixmap,
                         QPolygonF, QTransform)

from .canvas import (ArrowItem, EllipseItem, GroupItem, ImageItem, LineItem,
                     PaintScene, PathItem, PolygonItem, RectItem,
                     RoundedRectItem, TextItem)
from .document import cmds_to_painterpath, painterpath_to_cmds

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
KP_NS = "https://kerherve.app/khervepaint"

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ET.register_namespace("kp", KP_NS)

_EPS = 1e-4


def _svg(tag):
    return f"{{{SVG_NS}}}{tag}"


def _kp(tag):
    return f"{{{KP_NS}}}{tag}"


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


# ================================================================ writing
def _pixmap_data_uri(pixmap: QPixmap) -> str:
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QBuffer.WriteOnly)
    pixmap.save(buf, "PNG")
    buf.close()
    b64 = base64.b64encode(bytes(data)).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _transform_attr(item) -> str:
    parts = []
    pos = item.pos()
    if abs(pos.x()) > _EPS or abs(pos.y()) > _EPS:
        parts.append(f"translate({pos.x():g},{pos.y():g})")
    if abs(item.rotation()) > _EPS:
        parts.append(f"rotate({item.rotation():g})")
    return " ".join(parts)


def _set_common(el, item):
    tf = _transform_attr(item)
    if tf:
        el.set("transform", tf)
    if item.opacity() < 1 - _EPS:
        el.set("opacity", f"{item.opacity():g}")


def _set_stroke(el, pen: QPen):
    if pen.style() == Qt.NoPen:
        el.set("stroke", "none")
        return
    color = pen.color()
    el.set("stroke", color.name())
    el.set("stroke-width", f"{pen.widthF():g}")
    if color.alpha() < 255:
        el.set("stroke-opacity", f"{color.alphaF():g}")
    el.set("stroke-linecap", "round")
    el.set("stroke-linejoin", "round")


def _set_fill(el, brush: QBrush):
    if brush is None or brush.style() == Qt.NoBrush:
        el.set("fill", "none")
        return
    color = brush.color()
    el.set("fill", color.name())
    if color.alpha() < 255:
        el.set("fill-opacity", f"{color.alphaF():g}")


def painterpath_to_d(path: QPainterPath) -> str:
    out = []
    for c in painterpath_to_cmds(path):
        if c[0] == "M":
            out.append(f"M{c[1]:g},{c[2]:g}")
        elif c[0] == "L":
            out.append(f"L{c[1]:g},{c[2]:g}")
        elif c[0] == "C":
            out.append(f"C{c[1]:g},{c[2]:g} {c[3]:g},{c[4]:g} "
                       f"{c[5]:g},{c[6]:g}")
    return " ".join(out)


def _item_to_element(parent, item):
    if isinstance(item, GroupItem):
        g = ET.SubElement(parent, _svg("g"))
        _set_common(g, item)
        for child in item.childItems():
            _item_to_element(g, child)
        return g

    if isinstance(item, ArrowItem):
        ln = item.line()
        el = ET.SubElement(parent, _svg("line"))
        el.set("x1", f"{ln.x1():g}"); el.set("y1", f"{ln.y1():g}")
        el.set("x2", f"{ln.x2():g}"); el.set("y2", f"{ln.y2():g}")
        el.set(_kp("kind"), "arrow")
        _set_stroke(el, item.pen())
    elif isinstance(item, LineItem):
        ln = item.line()
        el = ET.SubElement(parent, _svg("line"))
        el.set("x1", f"{ln.x1():g}"); el.set("y1", f"{ln.y1():g}")
        el.set("x2", f"{ln.x2():g}"); el.set("y2", f"{ln.y2():g}")
        _set_stroke(el, item.pen())
    elif isinstance(item, RoundedRectItem):
        r = item.rect()
        el = ET.SubElement(parent, _svg("rect"))
        el.set("x", f"{r.x():g}"); el.set("y", f"{r.y():g}")
        el.set("width", f"{r.width():g}"); el.set("height", f"{r.height():g}")
        el.set("rx", f"{item.radius():g}"); el.set("ry", f"{item.radius():g}")
        _set_stroke(el, item.pen()); _set_fill(el, item.brush())
    elif isinstance(item, RectItem):
        r = item.rect()
        el = ET.SubElement(parent, _svg("rect"))
        el.set("x", f"{r.x():g}"); el.set("y", f"{r.y():g}")
        el.set("width", f"{r.width():g}"); el.set("height", f"{r.height():g}")
        _set_stroke(el, item.pen()); _set_fill(el, item.brush())
    elif isinstance(item, EllipseItem):
        r = item.rect()
        el = ET.SubElement(parent, _svg("ellipse"))
        el.set("cx", f"{r.center().x():g}"); el.set("cy", f"{r.center().y():g}")
        el.set("rx", f"{r.width() / 2:g}"); el.set("ry", f"{r.height() / 2:g}")
        _set_stroke(el, item.pen()); _set_fill(el, item.brush())
    elif isinstance(item, PolygonItem):
        el = ET.SubElement(parent, _svg("polygon"))
        pts = " ".join(f"{p.x():g},{p.y():g}" for p in item.polygon())
        el.set("points", pts)
        if item.kind and item.kind != "polygon":
            el.set(_kp("kind"), item.kind)
        _set_stroke(el, item.pen()); _set_fill(el, item.brush())
    elif isinstance(item, PathItem):
        el = ET.SubElement(parent, _svg("path"))
        el.set("d", painterpath_to_d(item.path()))
        _set_stroke(el, item.pen()); _set_fill(el, item.brush())
    elif isinstance(item, TextItem):
        el = ET.SubElement(parent, _svg("text"))
        el.set("x", "0"); el.set("y", "0")
        el.set("dominant-baseline", "text-before-edge")
        font = item.font()
        el.set("font-family", font.family())
        el.set("font-size", f"{font.pointSize()}")
        if font.bold():
            el.set("font-weight", "bold")
        if font.italic():
            el.set("font-style", "italic")
        el.set("fill", item.defaultTextColor().name())
        el.text = item.toPlainText()
    elif isinstance(item, ImageItem):
        pm = item.pixmap()
        el = ET.SubElement(parent, _svg("image"))
        el.set("x", "0"); el.set("y", "0")
        el.set("width", f"{pm.width()}"); el.set("height", f"{pm.height()}")
        el.set(f"{{{XLINK_NS}}}href", _pixmap_data_uri(pm))
    else:
        return None
    _set_common(el, item)
    return el


def save_svg(scene: PaintScene, path: str):
    rect = scene.sceneRect()
    root = ET.Element(_svg("svg"))
    root.set("width", f"{int(rect.width())}")
    root.set("height", f"{int(rect.height())}")
    root.set("viewBox", f"0 0 {int(rect.width())} {int(rect.height())}")
    root.set(_kp("grid-size"), str(scene.grid_size))
    root.set(_kp("grid-show"), "1" if scene.show_grid else "0")
    root.set(_kp("grid-snap"), "1" if scene.snap_enabled else "0")

    raster = scene.raster_item.pixmap()
    if not raster.isNull():
        img = ET.SubElement(root, _svg("image"))
        img.set("x", "0"); img.set("y", "0")
        img.set("width", f"{raster.width()}")
        img.set("height", f"{raster.height()}")
        img.set(_kp("role"), "raster")
        img.set(f"{{{XLINK_NS}}}href", _pixmap_data_uri(raster))

    for item in scene.vector_items():
        _item_to_element(root, item)

    ET.ElementTree(root).write(path, xml_declaration=True, encoding="utf-8")


# ================================================================ reading
def _color(value: str, fallback="#000000") -> QColor:
    if value is None:
        return QColor(fallback)
    value = value.strip()
    if value in ("none", "transparent"):
        return QColor(Qt.transparent)
    m = re.match(r"rgba?\(([^)]+)\)", value)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        nums = [int(round(float(p[:-1]) * 2.55)) if p.endswith("%")
                else int(round(float(p))) for p in parts[:3]]
        c = QColor(*nums)
        if len(parts) == 4:
            c.setAlphaF(float(parts[3]))
        return c
    c = QColor(value)
    return c if c.isValid() else QColor(fallback)


def _resolve_style(el, inherited: dict) -> dict:
    s = dict(inherited)
    style = el.get("style")
    if style:
        for decl in style.split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                s[k.strip()] = v.strip()
    for key in ("fill", "stroke", "stroke-width", "fill-opacity",
                "stroke-opacity", "font-size", "font-family", "font-weight",
                "font-style"):
        if el.get(key) is not None:
            s[key] = el.get(key)
    if el.get("opacity") is not None:           # opacity composes
        s["_opacity"] = s.get("_opacity", 1.0) * float(el.get("opacity"))
    return s


def _pen_from_style(s: dict) -> QPen:
    stroke = s.get("stroke", "none")
    if stroke in (None, "none"):
        return QPen(Qt.NoPen)
    color = _color(stroke)
    if "stroke-opacity" in s:
        color.setAlphaF(float(s["stroke-opacity"]))
    pen = QPen(color, float(s.get("stroke-width", 1)))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _brush_from_style(s: dict) -> QBrush:
    fill = s.get("fill", "#000000")        # SVG default fill is black
    if fill in (None, "none"):
        return QBrush(Qt.NoBrush)
    color = _color(fill)
    if "fill-opacity" in s:
        color.setAlphaF(float(s["fill-opacity"]))
    return QBrush(color)


def _parse_transform(text: str) -> QTransform:
    t = QTransform()
    if not text:
        return t
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", text):
        n = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        op = QTransform()
        if name == "translate":
            op.translate(n[0], n[1] if len(n) > 1 else 0)
        elif name == "scale":
            op.scale(n[0], n[1] if len(n) > 1 else n[0])
        elif name == "rotate":
            if len(n) == 3:
                op.translate(n[1], n[2]); op.rotate(n[0])
                op.translate(-n[1], -n[2])
            else:
                op.rotate(n[0])
        elif name == "matrix" and len(n) == 6:
            op = QTransform(n[0], n[1], n[2], n[3], n[4], n[5])
        elif name == "skewX":
            op.shear(math.tan(math.radians(n[0])), 0)
        elif name == "skewY":
            op.shear(0, math.tan(math.radians(n[0])))
        t = op * t          # right-to-left: leftmost op applied last
    return t


def _decompose(tf: QTransform):
    """Return (dx, dy, degrees, simple) where *simple* means the matrix
    is a pure translation + rotation (uniform scale 1, no shear)."""
    m11, m12, m21, m22 = tf.m11(), tf.m12(), tf.m21(), tf.m22()
    dx, dy = tf.dx(), tf.dy()
    simple = (abs(m11 * m11 + m12 * m12 - 1) < 1e-3
              and abs(m11 - m22) < 1e-3 and abs(m12 + m21) < 1e-3
              and (m11 * m22 - m12 * m21) > 0)
    degrees = math.degrees(math.atan2(m21, m11))
    return dx, dy, degrees, simple


def _finalise(item, total: QTransform, style: dict):
    """Apply transform + opacity to a freshly built native item."""
    dx, dy, deg, _ = _decompose(total)
    item.setPos(dx, dy)
    if abs(deg) > _EPS:
        item.setRotation(deg)
    if "_opacity" in style:
        item.setOpacity(style["_opacity"])
    return item


def _styled(item, style: dict, fill=True):
    item.setPen(_pen_from_style(style))
    if fill and hasattr(item, "setBrush"):
        item.setBrush(_brush_from_style(style))
    return item


def _rect_of(el) -> QRectF:
    return QRectF(float(el.get("x", 0)), float(el.get("y", 0)),
                  float(el.get("width", 0)), float(el.get("height", 0)))


def _baked_path(local_path: QPainterPath, total: QTransform, style: dict):
    item = PathItem(total.map(local_path))
    _styled(item, style)
    if "_opacity" in style:
        item.setOpacity(style["_opacity"])
    return item


def _build_leaf(el, total: QTransform, style: dict):
    tag = _localname(el.tag)
    dx, dy, deg, simple = _decompose(total)

    if tag == "line":
        line = QLineF(float(el.get("x1", 0)), float(el.get("y1", 0)),
                      float(el.get("x2", 0)), float(el.get("y2", 0)))
        cls = ArrowItem if el.get(_kp("kind")) == "arrow" else LineItem
        if simple:
            item = cls(line)
            return _finalise(_styled(item, style, fill=False), total, style)
        path = QPainterPath(line.p1()); path.lineTo(line.p2())
        return _baked_path(path, total, style)

    if tag == "rect":
        rect = _rect_of(el)
        rx = float(el.get("rx", 0) or 0)
        if simple and rx > 0:
            item = RoundedRectItem(rect, rx)
            return _finalise(_styled(item, style), total, style)
        if simple:
            item = RectItem(rect)
            return _finalise(_styled(item, style), total, style)
        path = QPainterPath()
        path.addRoundedRect(rect, rx, rx) if rx else path.addRect(rect)
        return _baked_path(path, total, style)

    if tag in ("circle", "ellipse"):
        if tag == "circle":
            r = float(el.get("r", 0))
            rx = ry = r
        else:
            rx = float(el.get("rx", 0)); ry = float(el.get("ry", 0))
        cx = float(el.get("cx", 0)); cy = float(el.get("cy", 0))
        rect = QRectF(cx - rx, cy - ry, 2 * rx, 2 * ry)
        if simple:
            item = EllipseItem(rect)
            return _finalise(_styled(item, style), total, style)
        path = QPainterPath(); path.addEllipse(rect)
        return _baked_path(path, total, style)

    if tag in ("polygon", "polyline"):
        poly = _parse_points(el.get("points", ""))
        if simple:
            item = PolygonItem(poly, kind=el.get(_kp("kind"), "polygon"))
            return _finalise(_styled(item, style), total, style)
        path = QPainterPath(); path.addPolygon(poly)
        if tag == "polygon":
            path.closeSubpath()
        return _baked_path(path, total, style)

    if tag == "path":
        local = _path_from_d(el.get("d", ""))
        if simple:
            item = PathItem(local)
            return _finalise(_styled(item, style), total, style)
        return _baked_path(local, total, style)

    if tag == "text":
        return _build_text(el, total, style)

    if tag == "image":
        return _build_image(el, total, style)

    return None


def _build_text(el, total: QTransform, style: dict):
    text = "".join(el.itertext())
    item = TextItem(text.strip())
    size = int(float(re.sub(r"[^\d.]", "", style.get("font-size", "14")) or 14))
    font = QFont(style.get("font-family", "Segoe UI"), size)
    font.setBold("bold" in str(style.get("font-weight", "")))
    font.setItalic(style.get("font-style") == "italic")
    item.setFont(font)
    item.setDefaultTextColor(_color(style.get("fill", "#000000")))
    x, y = float(el.get("x", 0)), float(el.get("y", 0))
    if el.get("dominant-baseline") != "text-before-edge":
        y -= size * 0.8                       # baseline -> top-left approx
    pt = total.map(QPointF(x, y))
    item.setPos(pt)
    _, _, deg, _ = _decompose(total)
    if abs(deg) > _EPS:
        item.setRotation(deg)
    if "_opacity" in style:
        item.setOpacity(style["_opacity"])
    return item


def _href(el):
    return el.get(f"{{{XLINK_NS}}}href") or el.get("href")


def _pixmap_from_href(href: str) -> QPixmap:
    pm = QPixmap()
    if href and href.startswith("data:"):
        b64 = href.split(",", 1)[1]
        pm.loadFromData(base64.b64decode(b64))
    return pm


def _build_image(el, total: QTransform, style: dict):
    pm = _pixmap_from_href(_href(el))
    item = ImageItem(pm)
    w = float(el.get("width", pm.width() or 1))
    h = float(el.get("height", pm.height() or 1))
    if pm.width() and pm.height():
        sx, sy = w / pm.width(), h / pm.height()
        if abs(sx - 1) > _EPS or abs(sy - 1) > _EPS:
            item.setTransform(QTransform.fromScale(sx, sy))
    pt = total.map(QPointF(float(el.get("x", 0)), float(el.get("y", 0))))
    item.setPos(pt)
    if "_opacity" in style:
        item.setOpacity(style["_opacity"])
    return item


def _parse_points(text: str) -> QPolygonF:
    nums = [float(x) for x in re.split(r"[\s,]+", text.strip()) if x]
    return QPolygonF([QPointF(nums[i], nums[i + 1])
                      for i in range(0, len(nums) - 1, 2)])


def _parse_element(el, parent_tf: QTransform, inherited: dict, scene):
    """Return a native item (or None). Raster images set the layer
    directly and return None."""
    tag = _localname(el.tag)
    style = _resolve_style(el, inherited)
    total = _parse_transform(el.get("transform")) * parent_tf

    if tag == "g":
        group = GroupItem()
        for child in el:
            sub = _parse_element(child, total, style, scene)
            if sub is not None:
                sub.setParentItem(group)
        return group if group.childItems() else None

    if tag == "image" and el.get(_kp("role")) == "raster":
        pm = _pixmap_from_href(_href(el))
        if not pm.isNull():
            scene.set_raster_pixmap(pm)
        return None

    if tag in ("defs", "title", "desc", "metadata", "style"):
        return None

    return _build_leaf(el, total, style)


def load_svg(scene: PaintScene, path: str):
    root = ET.parse(path).getroot()
    width, height = _root_size(root)
    scene.new_document(width, height)

    gs = root.get(_kp("grid-size"))
    if gs is not None:
        scene.grid_size = int(float(gs))
        scene.show_grid = root.get(_kp("grid-show"), "1") == "1"
        scene.snap_enabled = root.get(_kp("grid-snap"), "1") == "1"

    base = {"fill": "#000000", "stroke": "none"}
    for child in root:
        item = _parse_element(child, QTransform(), base, scene)
        if item is not None:
            scene.addItem(item)


def _root_size(root):
    vb = root.get("viewBox")
    if vb:
        nums = [float(x) for x in re.split(r"[\s,]+", vb.strip())]
        if len(nums) == 4:
            return int(nums[2]), int(nums[3])
    w = re.sub(r"[^\d.]", "", root.get("width", "800") or "800") or "800"
    h = re.sub(r"[^\d.]", "", root.get("height", "600") or "600") or "600"
    return int(float(w)), int(float(h))


# ---------------------------------------------------------------- path data
def _path_from_d(d: str) -> QPainterPath:
    path = QPainterPath()
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?",
                        d)
    i, n = 0, len(tokens)
    cur = QPointF(0, 0)
    start = QPointF(0, 0)
    prev_cmd = ""
    prev_ctrl = None

    def num():
        nonlocal i
        v = float(tokens[i]); i += 1
        return v

    while i < n:
        tok = tokens[i]
        if re.match(r"[A-Za-z]", tok):
            cmd = tok; i += 1
        else:
            cmd = prev_cmd if prev_cmd not in ("Z", "z") else "L"
        rel = cmd.islower()
        C = cmd.upper()

        if C == "M":
            x, y = num(), num()
            cur = QPointF(cur.x() + x, cur.y() + y) if rel else QPointF(x, y)
            path.moveTo(cur); start = QPointF(cur)
            prev_cmd = "l" if rel else "L"
        elif C == "L":
            x, y = num(), num()
            cur = QPointF(cur.x() + x, cur.y() + y) if rel else QPointF(x, y)
            path.lineTo(cur); prev_cmd = cmd
        elif C == "H":
            x = num()
            cur = QPointF(cur.x() + x if rel else x, cur.y())
            path.lineTo(cur); prev_cmd = cmd
        elif C == "V":
            y = num()
            cur = QPointF(cur.x(), cur.y() + y if rel else y)
            path.lineTo(cur); prev_cmd = cmd
        elif C == "C":
            c1 = _pt(num(), num(), cur, rel)
            c2 = _pt(num(), num(), cur, rel)
            end = _pt(num(), num(), cur, rel)
            path.cubicTo(c1, c2, end)
            prev_ctrl = c2; cur = end; prev_cmd = cmd
        elif C == "S":
            c1 = _reflect(prev_ctrl, cur) if prev_cmd.upper() in ("C", "S") \
                else QPointF(cur)
            c2 = _pt(num(), num(), cur, rel)
            end = _pt(num(), num(), cur, rel)
            path.cubicTo(c1, c2, end)
            prev_ctrl = c2; cur = end; prev_cmd = cmd
        elif C == "Q":
            c = _pt(num(), num(), cur, rel)
            end = _pt(num(), num(), cur, rel)
            path.quadTo(c, end)
            prev_ctrl = c; cur = end; prev_cmd = cmd
        elif C == "T":
            c = _reflect(prev_ctrl, cur) if prev_cmd.upper() in ("Q", "T") \
                else QPointF(cur)
            end = _pt(num(), num(), cur, rel)
            path.quadTo(c, end)
            prev_ctrl = c; cur = end; prev_cmd = cmd
        elif C == "A":
            rx, ry = num(), num()
            rot = num(); large = num(); sweep = num()
            end = _pt(num(), num(), cur, rel)
            _arc_to(path, cur, rx, ry, rot, large, sweep, end)
            cur = end; prev_cmd = cmd
        elif C == "Z":
            path.closeSubpath(); cur = QPointF(start); prev_cmd = cmd
        else:
            break
    return path


def _pt(x, y, cur, rel):
    return QPointF(cur.x() + x, cur.y() + y) if rel else QPointF(x, y)


def _reflect(ctrl, cur):
    if ctrl is None:
        return QPointF(cur)
    return QPointF(2 * cur.x() - ctrl.x(), 2 * cur.y() - ctrl.y())


def _arc_to(path, p0, rx, ry, phi_deg, large, sweep, p1):
    """Append an SVG elliptical arc to *path* as cubic segments."""
    if rx == 0 or ry == 0 or (p0 == p1):
        path.lineTo(p1)
        return
    rx, ry = abs(rx), abs(ry)
    phi = math.radians(phi_deg)
    cos_p, sin_p = math.cos(phi), math.sin(phi)
    dx, dy = (p0.x() - p1.x()) / 2, (p0.y() - p1.y()) / 2
    x1p = cos_p * dx + sin_p * dy
    y1p = -sin_p * dx + cos_p * dy
    denom = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    if denom == 0:
        path.lineTo(p1)
        return
    lam = (rx * rx * ry * ry) / denom
    if lam < 1:
        scale = math.sqrt(lam)
        rx, ry = rx / scale, ry / scale
    sign = -1 if large == sweep else 1
    num_ = max(rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p, 0)
    co = sign * math.sqrt(num_ / (rx * rx * y1p * y1p + ry * ry * x1p * x1p)) \
        if denom else 0
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cos_p * cxp - sin_p * cyp + (p0.x() + p1.x()) / 2
    cy = sin_p * cxp + cos_p * cyp + (p0.y() + p1.y()) / 2

    def angle(ux, uy, vx, vy):
        dot = ux * vx + uy * vy
        det = ux * vy - uy * vx
        return math.atan2(det, dot)

    theta1 = angle(1, 0, (x1p - cxp) / rx, (y1p - cyp) / ry)
    dtheta = angle((x1p - cxp) / rx, (y1p - cyp) / ry,
                   (-x1p - cxp) / rx, (-y1p - cyp) / ry)
    if not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep and dtheta < 0:
        dtheta += 2 * math.pi

    segments = max(1, int(math.ceil(abs(dtheta) / (math.pi / 2))))
    delta = dtheta / segments
    t = (4 / 3) * math.tan(delta / 4)
    theta = theta1
    for _ in range(segments):
        cos1, sin1 = math.cos(theta), math.sin(theta)
        cos2, sin2 = math.cos(theta + delta), math.sin(theta + delta)
        e1 = _elpt(cx, cy, rx, ry, cos_p, sin_p, cos1, sin1)
        e2 = _elpt(cx, cy, rx, ry, cos_p, sin_p, cos2, sin2)
        d1 = _elpt(0, 0, rx, ry, cos_p, sin_p, -sin1, cos1)
        d2 = _elpt(0, 0, rx, ry, cos_p, sin_p, -sin2, cos2)
        c1 = QPointF(e1.x() + t * d1.x(), e1.y() + t * d1.y())
        c2 = QPointF(e2.x() - t * d2.x(), e2.y() - t * d2.y())
        path.cubicTo(c1, c2, e2)
        theta += delta


def _elpt(cx, cy, rx, ry, cos_p, sin_p, cos_t, sin_t):
    x = rx * cos_t
    y = ry * sin_t
    return QPointF(cx + cos_p * x - sin_p * y, cy + sin_p * x + cos_p * y)
