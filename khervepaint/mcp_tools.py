"""Runs an MCP tool against the live KhervePaint window.

`mcp_schema.py` is the contract; this is the implementation.  Every
method here touches real Qt items, so it MUST run on the GUI thread —
`mcp_bridge.McpBridge` is what guarantees that, and it also wraps each
mutating call in one undo macro so the user gets their drawing back
with a single Ctrl+Z.

Items are addressed by an integer id handed out on demand and stamped
on the item itself.  Ids are not persisted: undo restores the document
from a snapshot, which rebuilds every item, so a client has to re-read
`list_items` afterwards.  That is cheaper — and much more honest — than
pretending an identity survives a rebuild it does not.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from __future__ import annotations

import base64
from pathlib import Path

from PyQt5.QtCore import QBuffer, QByteArray, QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QImage, QPainter, QPen, QPolygonF

from . import document, library, svgio
from .canvas import (ArcShapeItem, ArrowItem, DimensionItem, EllipseItem,
                     GroupItem, ImageItem, LineItem, PathItem, PolygonItem,
                     RectItem, RoundedRectItem, TextItem, center_origin)
from .mcp_schema import LIBRARY_KEYS
from .mcp_server import IMAGE_KEY

#: Palette key -> module name inside the package.
_LIBRARY_MODULES = {
    "molecules": "molecules", "crystals": "crystals",
    "scheme3d": "scheme3d", "floorplan": "floorplan",
    "electrical": "electrical", "optics": "optics", "vacuum": "vacuum",
    "labware": "labware", "flowchart": "flowchart", "network": "network",
    "pid": "pid", "arrows": "arrows", "biology": "biology",
    "maths": "maths",
}

#: Class -> the kind name reported by list_items.  Order matters:
#: DimensionItem and ArrowItem are LineItems, and RoundedRectItem /
#: ArcShapeItem are PathItems.
_KINDS = [
    (DimensionItem, "dimension"), (ArrowItem, "arrow"), (LineItem, "line"),
    (RoundedRectItem, "rounded_rect"), (ArcShapeItem, "arc"),
    (PolygonItem, "polygon"), (RectItem, "rect"), (EllipseItem, "ellipse"),
    (TextItem, "text"), (ImageItem, "image"), (GroupItem, "group"),
    (PathItem, "path"),
]

#: Cap on a rendered preview, so one look at the canvas stays cheap.
_DEFAULT_RENDER_WIDTH = 1000


class ToolError(Exception):
    """A tool failed for a reason the client should read and act on."""


def _kind_of(item) -> str:
    for cls, name in _KINDS:
        if isinstance(item, cls):
            return name
    return type(item).__name__


def _pen_color(pen: QPen):
    return "none" if pen.style() == Qt.NoPen else pen.color().name()


def _brush_color(brush: QBrush):
    if brush.style() == Qt.NoBrush:
        return "none"
    if brush.gradient() is not None:
        return "gradient"
    return brush.color().name()


class McpToolExecutor:
    """Executes one named tool against a `MainWindow`."""

    def __init__(self, window):
        self._w = window
        self._next_id = 1
        self._by_id = {}

    # ── Plumbing ────────────────────────────────────────────────

    @property
    def _scene(self):
        return self._w.scene

    def execute(self, name: str, tool_input: dict) -> dict:
        """Run *name*; never raises — a failure comes back as {"error"}."""
        handler = getattr(self, f"_t_{name}", None)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        try:
            return handler(tool_input or {})
        except ToolError as exc:
            return {"error": str(exc)}
        except Exception as exc:              # pragma: no cover - defensive
            return {"error": f"{type(exc).__name__}: {exc}"}

    # ── Item identity ───────────────────────────────────────────

    def _id_of(self, item) -> int:
        ident = getattr(item, "_mcp_id", None)
        if ident is None or self._by_id.get(ident) is not item:
            ident = self._next_id
            self._next_id += 1
            item._mcp_id = ident
            self._by_id[ident] = item
        return ident

    def _item(self, ident):
        try:
            item = self._by_id.get(int(ident))
        except (TypeError, ValueError):
            raise ToolError(f"{ident!r} is not an item id.")
        alive = False
        if item is not None:
            try:
                alive = item.scene() is self._scene
            except RuntimeError:              # C++ side already deleted
                alive = False
        if not alive:
            raise ToolError(
                f"No item with id {ident} on the canvas. Ids change when "
                "the document is rebuilt (undo, open, load_example) — "
                "call list_items again.")
        return item

    def _items(self, ids):
        if not isinstance(ids, (list, tuple)) or not ids:
            raise ToolError("Pass a non-empty list of item ids.")
        return [self._item(i) for i in ids]

    # ── Geometry helpers ────────────────────────────────────────

    def _px_per_mm(self) -> float:
        return getattr(self._scene, "dpi", 96) / 25.4

    def _centre(self, params, default_to_page=True) -> QPointF:
        if "x" in params and "y" in params:
            return QPointF(float(params["x"]), float(params["y"]))
        if default_to_page:
            return self._scene.sceneRect().center()
        return self._w._view_centre()

    def _unsnapped(self, fn):
        """Run *fn* with grid snapping off.

        A client asks for exact coordinates; SnapMixin would quantise
        them to the grid on the way in and the reported position would
        not be the one that was requested.
        """
        scene = self._scene
        was = scene.snap_enabled
        scene.snap_enabled = False
        try:
            return fn()
        finally:
            scene.snap_enabled = was

    def _commit(self):
        self._scene.changed_by_user.emit()

    def _recentre(self, item, centre: QPointF):
        """Put *item*'s real bounding box on *centre*.

        The app centres a placed symbol on its nominal design box, which
        is what a click-to-place gesture wants — the user drags it into
        position afterwards anyway. A client that asked for (x, y) gets
        no second chance, so it gets the centre it named.
        """
        if item is None:
            return item
        rect = item.sceneBoundingRect()
        dx, dy = centre.x() - rect.center().x(), centre.y() - rect.center().y()
        if not (dx or dy):
            return item
        self._unsnapped(lambda: item.moveBy(dx, dy))
        # The place_* helpers already emitted for their own placement, so
        # this nudge needs an emit of its own or the undo snapshot would
        # record the item where it never actually sat.
        self._commit()
        return item

    # ── Inspection ──────────────────────────────────────────────

    def _t_get_document_info(self, _params) -> dict:
        scene = self._scene
        rect = scene.sceneRect()
        ppm = self._px_per_mm()
        return {
            "width_px": round(rect.width()), "height_px": round(rect.height()),
            "dpi": getattr(scene, "dpi", 96),
            "width_mm": round(rect.width() / ppm, 2),
            "height_mm": round(rect.height() / ppm, 2),
            "pixels_per_mm": round(ppm, 4),
            "origin": "top-left; x grows right, y grows down",
            "grid_mm": scene.grid_mm, "show_grid": scene.show_grid,
            "snap": scene.snap_enabled, "infinite_paper": scene.infinite,
            "item_count": len(scene.vector_items()),
            "selected_ids": [self._id_of(i) for i in scene.selectedItems()
                             if i.parentItem() is None],
            "path": self._w._path,
            "unsaved_changes": not self._w._undo_stack.isClean(),
        }

    def _describe(self, item, depth: int) -> dict:
        rect = item.sceneBoundingRect()
        ppm = self._px_per_mm()
        info = {
            "id": self._id_of(item), "kind": _kind_of(item),
            "x": round(rect.x(), 2), "y": round(rect.y(), 2),
            "w": round(rect.width(), 2), "h": round(rect.height(), 2),
            "w_mm": round(rect.width() / ppm, 2),
            "h_mm": round(rect.height() / ppm, 2),
            "z": item.zValue(),
        }
        if item.rotation():
            info["rotation"] = round(item.rotation(), 2)
        if item.opacity() != 1.0:
            info["opacity"] = round(item.opacity(), 3)
        if not item.isVisible():
            info["visible"] = False
        if hasattr(item, "pen"):
            info["stroke"] = _pen_color(item.pen())
            info["width"] = round(item.pen().widthF(), 2)
        if hasattr(item, "brush"):
            info["fill"] = _brush_color(item.brush())
        if isinstance(item, TextItem):
            info["text"] = item.toPlainText()
            info["size"] = item.font().pointSize()
            info["stroke"] = item.defaultTextColor().name()
        label = getattr(item, "label", None)
        if callable(label) and label():
            info["label"] = label()
        if isinstance(item, LineItem):
            ln = item.line()
            info.update(x1=round(ln.x1(), 2), y1=round(ln.y1(), 2),
                        x2=round(ln.x2(), 2), y2=round(ln.y2(), 2))
        if isinstance(item, GroupItem):
            children = [c for c in item.childItems()]
            info["children"] = len(children)
            model = getattr(item, "mol_name", None)
            if model:
                info["model"] = model
                info["model_az"] = getattr(item, "mol_az", None)
                info["model_el"] = getattr(item, "mol_el", None)
                info["representation"] = getattr(item, "mol_repr", "3d")
                if getattr(item, "mol_cells", None):
                    info["cells"] = list(item.mol_cells)
                if getattr(item, "mol_tilts", None):
                    info["tilts"] = dict(item.mol_tilts)
            if depth > 0:
                info["items"] = [self._describe(c, depth - 1)
                                 for c in children]
        return info

    def _t_list_items(self, params) -> dict:
        depth = int(params.get("depth", 0) or 0)
        if params.get("ids"):
            items = self._items(params["ids"])
        else:
            items = self._scene.vector_items()
        return {"count": len(items), "order": "bottom to top",
                "items": [self._describe(i, depth) for i in items]}

    def _t_render_canvas(self, params) -> dict:
        from .handles import Handle
        scene = self._scene
        rect = scene.sceneRect()
        if params.get("region"):
            try:
                x, y, w, h = [float(v) for v in params["region"]]
            except (TypeError, ValueError):
                raise ToolError("region must be [x, y, w, h].")
            rect = QRectF(x, y, w, h)
        if rect.width() < 1 or rect.height() < 1:
            raise ToolError("Nothing to render: the region is empty.")
        limit = int(params.get("max_width") or _DEFAULT_RENDER_WIDTH)
        scale = min(1.0, max(1, limit) / rect.width())
        width = max(1, round(rect.width() * scale))
        height = max(1, round(rect.height() * scale))

        # The selection handles are scene items, so they would appear in
        # the picture.  Hide them for the render rather than clearing the
        # selection, which would be a visible change the client did not
        # ask for.
        hidden = [i for i in scene.items()
                  if isinstance(i, Handle) and i.isVisible()]
        for handle in hidden:
            handle.setVisible(False)
        try:
            image = QImage(width, height, QImage.Format_ARGB32)
            image.fill(Qt.white)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.Antialiasing)
            scene.render(painter, target=QRectF(image.rect()), source=rect)
            painter.end()
        finally:
            for handle in hidden:
                handle.setVisible(True)

        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QBuffer.WriteOnly)
        image.save(buffer, "PNG")
        buffer.close()
        return {IMAGE_KEY: base64.b64encode(bytes(data)).decode("ascii"),
                "rendered_width": width, "rendered_height": height,
                "scale": round(scale, 4),
                "region": [round(rect.x(), 2), round(rect.y(), 2),
                           round(rect.width(), 2), round(rect.height(), 2)]}

    def _module(self, key: str):
        name = _LIBRARY_MODULES.get(str(key))
        if name is None:
            raise ToolError(
                f"Unknown library {key!r}. Choose one of: "
                f"{', '.join(LIBRARY_KEYS)}.")
        from importlib import import_module
        return import_module(f".{name}", __package__)

    def _t_list_symbols(self, params) -> dict:
        if not params.get("library"):
            return {"libraries": [
                {"library": key, "sections": len(self._module(key).CATEGORIES)}
                for key in LIBRARY_KEYS]}
        module = self._module(params["library"])
        return {"library": params["library"], "sections": [
            {"section": title,
             "elements": [{"name": n, "label": module.LABELS.get(n, n)}
                          for n in names]}
            for title, names in module.CATEGORIES]}

    def _t_list_models(self, params) -> dict:
        from . import molecules
        kind = str(params.get("kind", "all")).lower()
        groups = []
        if kind in ("all", "molecules"):
            groups += list(molecules.CATEGORIES)
        if kind in ("all", "crystals"):
            groups += list(molecules.CRYSTAL_CATEGORIES)
        return {"sections": [
            {"section": title,
             "models": [{"name": n, "label": molecules.LABELS.get(n, n),
                         "stackable": bool(molecules.can_stack(n))}
                        for n in names]}
            for title, names in groups]}

    def _t_list_examples(self, _params) -> dict:
        from . import examples
        return {"examples": [{"category": c, "name": n}
                             for c, n, _b in examples.EXAMPLES]}

    def _t_list_objects(self, _params) -> dict:
        return {"folder": str(library.objects_dir()),
                "objects": [{"name": name,
                             "folder": "/".join(parts) or None}
                            for parts, name, _p in library.iter_objects()]}

    # ── Drawing ─────────────────────────────────────────────────

    def _t_draw(self, params) -> dict:
        from .ai_assistant import apply_specs
        specs = params.get("shapes")
        if not isinstance(specs, list) or not specs:
            raise ToolError("'shapes' must be a non-empty list of specs.")
        created = self._unsnapped(lambda: apply_specs(self._scene, specs))
        if not created:
            raise ToolError(
                "None of those specs produced a shape. Check the 'shape' "
                "names against the tool description.")
        return {"created": len(created),
                "ids": [self._id_of(i) for i in created],
                "skipped": len(specs) - len(created)}

    def _apply_pen(self, item, change):
        if not hasattr(item, "pen") or not hasattr(item, "setPen"):
            return
        pen = QPen(item.pen())
        if "stroke" in change:
            value = str(change["stroke"])
            if value.lower() == "none":
                pen.setStyle(Qt.NoPen)
            else:
                pen.setColor(QColor(value))
                if pen.style() == Qt.NoPen:
                    pen.setStyle(Qt.SolidLine)
        if "width" in change:
            pen.setWidthF(float(change["width"]))
            if pen.style() == Qt.NoPen and "stroke" not in change:
                pen.setStyle(Qt.SolidLine)
        item.setPen(pen)

    def _apply_brush(self, item, change):
        if "fill" not in change or not hasattr(item, "setBrush"):
            return
        from .ai_assistant import _brush
        item.setBrush(_brush({"fill": change["fill"]}))

    def _resize(self, item, w, h):
        """Give *item* a new size, by whatever means it supports."""
        rect = item.sceneBoundingRect()
        w = float(w) if w is not None else rect.width()
        h = float(h) if h is not None else rect.height()
        if w <= 0 or h <= 0:
            raise ToolError("Width and height must be positive.")
        if isinstance(item, LineItem):
            return                              # use x1/y1/x2/y2 instead
        if isinstance(item, PolygonItem) and item.kind == "polygon":
            # A free polygon has no parametric form to rebuild from, so
            # map its vertices into the new box instead.
            old = item.polygon().boundingRect()
            if old.width() and old.height():
                sx, sy = w / old.width(), h / old.height()
                item.setPolygon(QPolygonF([
                    QPointF(old.x() + (p.x() - old.x()) * sx,
                            old.y() + (p.y() - old.y()) * sy)
                    for p in item.polygon()]))
        elif hasattr(item, "set_rect"):
            local = item.boundingRect()
            item.set_rect(QRectF(local.x(), local.y(), w, h))
        elif hasattr(item, "setRect"):
            local = item.rect()
            item.setRect(QRectF(local.x(), local.y(), w, h))
        elif rect.width():
            # Groups, images, text: no geometry to rewrite, so scale.
            item.setScale(item.scale() * (w / rect.width()))
        center_origin(item)

    def _move_to(self, item, x=None, y=None, dx=0.0, dy=0.0):
        rect = item.sceneBoundingRect()
        tx = (float(x) - rect.x()) if x is not None else 0.0
        ty = (float(y) - rect.y()) if y is not None else 0.0
        item.moveBy(tx + float(dx), ty + float(dy))

    def _update_one(self, change: dict):
        item = self._item(change.get("id"))
        if "w" in change or "h" in change:
            self._resize(item, change.get("w"), change.get("h"))
        if isinstance(item, LineItem) and any(
                k in change for k in ("x1", "y1", "x2", "y2")):
            ln = item.line()
            item.setLine(float(change.get("x1", ln.x1())),
                         float(change.get("y1", ln.y1())),
                         float(change.get("x2", ln.x2())),
                         float(change.get("y2", ln.y2())))
            center_origin(item)
        self._apply_pen(item, change)
        self._apply_brush(item, change)
        if isinstance(item, TextItem):
            if "text" in change:
                item.setPlainText(str(change["text"]))
                center_origin(item)
            if "stroke" in change and str(change["stroke"]).lower() != "none":
                item.setDefaultTextColor(QColor(str(change["stroke"])))
            if "size" in change:
                font = item.font()
                font.setPointSize(int(change["size"]))
                item.setFont(font)
                center_origin(item)
        if "label" in change and hasattr(item, "set_label"):
            item.set_label(str(change["label"]))
        if "scale" in change:
            item.setScale(float(change["scale"]))
        if "rotation" in change:
            item.setRotation(float(change["rotation"]))
        if "opacity" in change:
            item.setOpacity(max(0.0, min(1.0, float(change["opacity"]))))
        if "visible" in change:
            item.setVisible(bool(change["visible"]))
        if any(k in change for k in ("x", "y", "dx", "dy")):
            self._move_to(item, change.get("x"), change.get("y"),
                          change.get("dx", 0.0), change.get("dy", 0.0))
        return item

    def _t_update_items(self, params) -> dict:
        changes = params.get("changes")
        if not isinstance(changes, list) or not changes:
            raise ToolError("'changes' must be a non-empty list.")
        self._scene.clear_handles()
        items = self._unsnapped(
            lambda: [self._update_one(c) for c in changes])
        self._commit()
        return {"updated": len(items),
                "items": [self._describe(i, 0) for i in items]}

    def _t_delete_items(self, params) -> dict:
        items = self._items(params.get("ids"))
        self._scene.clear_handles()
        for item in items:
            self._scene.removeItem(item)
        self._commit()
        return {"deleted": len(items)}

    def _t_group_items(self, params) -> dict:
        items = self._items(params.get("ids"))
        if len(items) < 2:
            raise ToolError("Grouping needs at least two items.")
        self._select(items)
        self._scene.group_selection()
        groups = [i for i in self._scene.selectedItems()
                  if isinstance(i, GroupItem)]
        if not groups:
            raise ToolError("Could not group those items.")
        return {"group_id": self._id_of(groups[0]), "members": len(items)}

    def _t_ungroup_items(self, params) -> dict:
        items = self._items(params.get("ids"))
        groups = [i for i in items if isinstance(i, GroupItem)]
        if not groups:
            raise ToolError("None of those items is a group.")
        self._select(groups)
        self._scene.ungroup_selection()
        freed = [i for i in self._scene.selectedItems()
                 if i.parentItem() is None]
        return {"ungrouped": len(groups),
                "ids": [self._id_of(i) for i in freed]}

    def _t_order_items(self, params) -> dict:
        where = str(params.get("where", ""))
        if where not in ("front", "back", "forward", "backward"):
            raise ToolError("'where' must be front, back, forward or "
                            "backward.")
        items = self._items(params.get("ids"))
        for item in items:
            self._w.reorder_item(item, where)
        return {"reordered": len(items), "where": where}

    def _t_align_items(self, params) -> dict:
        how = str(params.get("how", ""))
        items = self._items(params.get("ids"))
        if len(items) < 2:
            raise ToolError("Aligning needs at least two items.")
        rects = {id(i): i.sceneBoundingRect() for i in items}

        def rect(i):
            return rects[id(i)]

        def move(fn):
            self._unsnapped(lambda: [i.moveBy(*fn(i)) for i in items])

        if how == "left":
            edge = min(rect(i).left() for i in items)
            move(lambda i: (edge - rect(i).left(), 0))
        elif how == "right":
            edge = max(rect(i).right() for i in items)
            move(lambda i: (edge - rect(i).right(), 0))
        elif how == "top":
            edge = min(rect(i).top() for i in items)
            move(lambda i: (0, edge - rect(i).top()))
        elif how == "bottom":
            edge = max(rect(i).bottom() for i in items)
            move(lambda i: (0, edge - rect(i).bottom()))
        elif how == "center_x":
            mid = sum(rect(i).center().x() for i in items) / len(items)
            move(lambda i: (mid - rect(i).center().x(), 0))
        elif how == "center_y":
            mid = sum(rect(i).center().y() for i in items) / len(items)
            move(lambda i: (0, mid - rect(i).center().y()))
        elif how in ("distribute_x", "distribute_y"):
            self._distribute(items, rects, how.endswith("x"))
        else:
            raise ToolError(f"Unknown alignment {how!r}.")
        self._commit()
        return {"aligned": len(items), "how": how}

    def _distribute(self, items, rects, horizontal: bool):
        """Space *items* evenly between the two outermost ones."""
        def key(i):
            r = rects[id(i)]
            return r.center().x() if horizontal else r.center().y()

        ordered = sorted(items, key=key)
        if len(ordered) < 3:
            return
        first, last = key(ordered[0]), key(ordered[-1])
        step = (last - first) / (len(ordered) - 1)
        moves = []
        for n, item in enumerate(ordered[1:-1], start=1):
            delta = first + n * step - key(item)
            moves.append((item, (delta, 0) if horizontal else (0, delta)))
        self._unsnapped(lambda: [i.moveBy(*d) for i, d in moves])

    def _select(self, items):
        self._scene.clearSelection()
        for item in items:
            item.setSelected(True)

    def _t_select_items(self, params) -> dict:
        items = self._items(params["ids"]) if params.get("ids") else []
        self._select(items)
        return {"selected": len(items)}

    # ── Libraries and models ────────────────────────────────────

    def _t_place_symbol(self, params) -> dict:
        key = params.get("library")
        name = str(params.get("name", ""))
        module = self._module(key)
        if name not in getattr(module, "LABELS", {}):
            raise ToolError(
                f"{name!r} is not in the {key} palette — call "
                "list_symbols for the exact names.")
        centre = self._centre(params)
        if key in ("molecules", "crystals"):
            item = self._unsnapped(
                lambda: self._scene.place_mol_element(name, centre))
        else:
            item = self._unsnapped(
                lambda: self._scene._place_symbol(module, name, centre))
        if item is None:
            raise ToolError(f"Could not build {name!r}.")
        self._recentre(item, centre)
        return {"placed": name, "library": key,
                "item": self._describe(item, 0)}

    def _t_place_model(self, params) -> dict:
        from . import molecules
        name = molecules.resolve_name(params.get("name"))
        if not name:
            raise ToolError(
                f"No model called {params.get('name')!r} — call "
                "list_models for the catalogue, or build_molecule to "
                "make one from a skeleton.")
        centre = self._centre(params)
        item = self._unsnapped(
            lambda: self._scene.place_mol_element(name, centre))
        if item is None:
            raise ToolError(f"Could not build the {name!r} model.")
        item = self._reconfigure(item, params) or item
        self._recentre(item, centre)
        return {"placed": name, "item": self._describe(item, 0)}

    def _t_build_molecule(self, params) -> dict:
        from . import molecules
        atoms = params.get("atoms")
        if not isinstance(atoms, list) or not atoms:
            raise ToolError("'atoms' must be a list of element symbols.")
        links = [[int(b[0]), int(b[1]), int(b[2]) if len(b) > 2 else 1]
                 for b in (params.get("bonds") or [])]
        name = params.get("name") or "custom"
        known = molecules.resolve_name(params.get("name"))
        if known:                       # a curated model beats a guess
            built, bonds, _e, _r = molecules.model_data(known)
            name = known
        else:
            built, bonds = molecules.build_molecule(
                [str(e) for e in atoms], links)
        if not built:
            raise ToolError("Could not build a structure from those atoms.")
        mode = str(params.get("representation", "3d"))
        centre = self._centre(params)
        item = self._unsnapped(
            lambda: self._scene.place_built_molecule(
                built, bonds, centre, mode=mode, name=name))
        if item is None:
            raise ToolError("Could not place the molecule.")
        self._recentre(item, centre)
        return {"placed": name, "atoms": len(built), "bonds": len(bonds),
                "item": self._describe(item, 0)}

    def _reconfigure(self, item, params):
        """Apply the model options in *params* to a placed model."""
        scene = self._scene
        if params.get("cells"):
            try:
                nx, ny, nz = [int(c) for c in params["cells"]]
            except (TypeError, ValueError):
                raise ToolError("'cells' must be [nx, ny, nz].")
            stacked = scene.set_cells(item, nx, ny, nz)
            if stacked is None:
                raise ToolError(
                    f"{getattr(item, 'mol_name', 'This model')} cannot be "
                    "stacked into a supercell.")
            item = stacked
        keys = ("az", "el", "bond", "representation", "tilts", "colors",
                "polyhedra")
        if not any(k in params for k in keys):
            return item
        kwargs = {}
        if "tilts" in params:
            kwargs["tilts"] = {str(k): tuple(float(a) for a in v)
                               for k, v in (params["tilts"] or {}).items()}
        if "colors" in params:
            kwargs["colors"] = dict(params["colors"] or {})
        if "polyhedra" in params:
            kwargs["poly"] = bool(params["polyhedra"])
        rebuilt = scene.reorient_model(
            item,
            params.get("az", getattr(item, "mol_az", None)),
            params.get("el", getattr(item, "mol_el", None)),
            bond=params.get("bond"),
            mode=params.get("representation"),
            **kwargs)
        return rebuilt or item

    def _t_configure_model(self, params) -> dict:
        item = self._item(params.get("id"))
        if not getattr(item, "mol_name", None):
            raise ToolError(
                "That item is not a molecule or crystal model. "
                "configure_model only works on one placed by place_model "
                "or build_molecule.")
        item = self._reconfigure(item, params)
        return {"model": getattr(item, "mol_name", None),
                "item": self._describe(item, 0)}

    def _t_insert_object(self, params) -> dict:
        name = str(params.get("name", ""))
        match = [p for _parts, n, p in library.iter_objects() if n == name]
        if not match:
            raise ToolError(
                f"No saved object called {name!r} — call list_objects.")
        dicts = library.load_object(match[0])
        if not dicts:
            raise ToolError(f"{name!r} is empty.")
        centre = self._centre(params)

        def place():
            items = [document.item_from_dict(d) for d in dicts]
            box = QRectF()
            for item in items:
                self._scene.addItem(item)
                box = box.united(item.sceneBoundingRect())
            dx = centre.x() - box.center().x()
            dy = centre.y() - box.center().y()
            for item in items:
                item.moveBy(dx, dy)
            return items

        items = self._unsnapped(place)
        self._select(items)
        self._commit()
        return {"inserted": name, "ids": [self._id_of(i) for i in items]}

    def _t_load_example(self, params) -> dict:
        from . import examples
        from .ai_assistant import apply_specs
        name = str(params.get("name", ""))
        match = [b for _c, n, b in examples.EXAMPLES if n == name]
        if not match:
            raise ToolError(
                f"No example called {name!r} — call list_examples.")
        self._guard_unsaved(params, "load_example")
        scene = self._scene
        scene.new_document(examples.PAGE_W, examples.PAGE_H)
        scene.dpi = examples.PAGE_DPI
        self._unsnapped(lambda: apply_specs(scene, match[0]()))
        scene.clearSelection()
        scene.clear_handles()
        self._w._path = None
        self._reset_view()
        return {"loaded": name,
                "item_count": len(scene.vector_items())}

    # ── Canvas and document ─────────────────────────────────────

    def _t_set_canvas(self, params) -> dict:
        scene = self._scene
        if params.get("fit_to_content"):
            scene.fit_to_content()
        if "dpi" in params:
            scene.dpi = int(params["dpi"])
        if "width" in params or "height" in params:
            rect = scene.sceneRect()
            scene.resize_canvas(int(params.get("width", rect.width())),
                                int(params.get("height", rect.height())))
        if "grid_mm" in params:
            scene.grid_mm = float(params["grid_mm"])
        if "show_grid" in params:
            scene.show_grid = bool(params["show_grid"])
        if "snap" in params:
            scene.snap_enabled = bool(params["snap"])
        self._w._sync_grid_controls()
        self._commit()
        return self._t_get_document_info({})

    def _guard_unsaved(self, params, tool: str):
        if (not self._w._undo_stack.isClean()
                and not params.get("discard_unsaved_changes")):
            raise ToolError(
                "The user has unsaved changes. Offer to save_document "
                f"first; pass discard_unsaved_changes: true to {tool} "
                "only if they say to throw the work away.")

    def _reset_view(self):
        self._w._sync_grid_controls()
        self._w._reset_history()
        self._w.view.zoom_reset()
        self._w._update_title()

    def _t_new_document(self, params) -> dict:
        from . import canvassize
        self._guard_unsaved(params, "new_document")
        w, h, dpi = canvassize.default_size()
        self._scene.new_document(int(params.get("width", w)),
                                 int(params.get("height", h)))
        self._scene.dpi = int(params.get("dpi", dpi))
        self._w._path = None
        self._reset_view()
        return self._t_get_document_info({})

    def _t_open_document(self, params) -> dict:
        path = Path(str(params.get("path", ""))).expanduser()
        if not path.is_file():
            raise ToolError(f"No such file: {path}")
        self._guard_unsaved(params, "open_document")
        suffix = path.suffix.lower()
        if suffix == ".png":
            document.open_png(self._scene, str(path))
            self._w._path = None
        elif suffix == ".svg":
            svgio.load_svg(self._scene, str(path))
            self._w._path = str(path)
        elif suffix == ".kpaint":
            document.load_kpaint(self._scene, str(path))
            self._w._path = str(path)
        else:
            raise ToolError(
                f"{suffix or 'That file'} is not a drawing KhervePaint "
                "opens — use .svg, .kpaint or .png.")
        self._reset_view()
        self._w._add_recent(str(path))
        info = self._t_get_document_info({})
        info["opened"] = str(path)
        return info

    def _t_save_document(self, params) -> dict:
        path = params.get("path") or self._w._path
        if not path:
            raise ToolError(
                "This drawing has never been saved, so there is nowhere "
                "to save it. Pass an absolute path ending in .svg.")
        path = str(Path(str(path)).expanduser())
        suffix = Path(path).suffix.lower()
        if suffix == ".kpaint":
            document.save_kpaint(self._scene, path)
        elif suffix == ".svg":
            svgio.save_svg(self._scene, path)
        else:
            raise ToolError("Save as .svg (native, editable) or .kpaint. "
                            "For PNG or PDF use export_document.")
        self._w._path = path
        self._w._undo_stack.setClean()
        self._w._add_recent(path)
        self._w._update_title()
        return {"saved": path}

    def _t_export_document(self, params) -> dict:
        path = str(Path(str(params.get("path", ""))).expanduser())
        exporters = {".png": document.export_png, ".pdf": document.export_pdf,
                     ".svg": document.export_svg}
        suffix = Path(path).suffix.lower()
        if suffix not in exporters:
            raise ToolError("Export path must end in .png, .pdf or .svg.")
        exporters[suffix](self._scene, path)
        return {"exported": path, "format": suffix.lstrip(".")}
