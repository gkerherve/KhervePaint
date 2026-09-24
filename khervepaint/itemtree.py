"""The Items panel: a tree of everything on the canvas.

Toggled from the top toolbar (and View ▸ Items panel). One row per
top-level item, bottom-to-top like the stacking order reversed (front
first, as in a layers list); groups expand to show their children. Each
row shows what the item is — "Rectangle", "3D solid: Cube", "Molecule:
benzene", "Room layout: Double bed" — and its X, Y and rotation, which
can be edited in place. Clicking a row selects the item on the canvas
(and canvas selection highlights the row); Delete removes it.

The panel only reads the scene and goes through ordinary moves/removals
that emit `changed_by_user`, so every edit made here is undoable.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5 import sip
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QAbstractItemView, QDockWidget, QHBoxLayout,
                             QHeaderView, QLabel, QPushButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from . import icons
from .canvas import (ArcShapeItem, ArrowItem, DimensionItem, EllipseItem,
                     GroupItem, ImageItem, LineItem, PathItem, PolygonItem,
                     RectItem, RoundedRectItem, TextItem)

COL_NAME, COL_X, COL_Y, COL_ROT = range(4)
_ROLE = Qt.UserRole

#: (class, label, mdi glyph) — subclasses before their bases
_KINDS = [
    (DimensionItem, "Dimension", "mdi.ruler"),
    (ArrowItem, "Arrow", "mdi.arrow-top-right"),
    (LineItem, "Line", "mdi.vector-line"),
    (RoundedRectItem, "Rounded rectangle", "mdi.rectangle-outline"),
    (ArcShapeItem, "Arc", "mdi.circle-slice-4"),
    (PolygonItem, "Polygon", "mdi.vector-polygon"),
    (RectItem, "Rectangle", "mdi.rectangle-outline"),
    (EllipseItem, "Ellipse", "mdi.ellipse-outline"),
    (TextItem, "Text", "mdi.format-text"),
    (ImageItem, "Image", "mdi.image-outline"),
    (GroupItem, "Group", "mdi.group"),
    (PathItem, "Path", "mdi.vector-curve"),
]

#: palette module → the name shown before a symbol's label
_PALETTES = {
    "scheme3d": "3D scheme", "floorplan": "Room layout",
    "electrical": "Electrical", "optics": "Optics", "vacuum": "Vacuum",
    "labware": "Glassware", "flowchart": "Flowchart", "network": "Network",
    "pid": "P&ID", "arrows": "Arrow", "biology": "Biology",
    "maths": "Math", "molecules": "Molecule", "crystals": "Crystal",
    "solids": "3D solid",
}


def describe(item):
    """(label, glyph) naming *item* the way a person would."""
    solid = getattr(item, "solid", None)
    if solid:
        from . import solids
        name = solids.LABELS.get(solid.get("name"), solid.get("name"))
        return f"3D solid: {name}", "mdi.cube-outline"
    if getattr(item, "mol_name", None):
        return f"Molecule: {item.mol_name}", "mdi.molecule"
    if getattr(item, "rxn_data", None):
        from . import reaction
        try:
            eq = reaction.to_equation(item.rxn_data)
        except Exception:
            eq = ""
        return f"Reaction: {eq}".rstrip(": "), "mdi.flask-outline"
    symbol = getattr(item, "symbol", None)
    if symbol and ":" in symbol:
        mod, key = symbol.split(":", 1)
        label = key
        try:
            from importlib import import_module
            label = import_module(f".{mod}", __package__).LABELS.get(key, key)
        except Exception:
            pass
        return f"{_PALETTES.get(mod, mod)}: {label}", "mdi.shape-outline"
    for cls, label, glyph in _KINDS:
        if isinstance(item, cls):
            if isinstance(item, TextItem):
                text = item.toPlainText().strip().replace("\n", " ")
                return f'Text "{text[:30]}"', glyph
            if isinstance(item, PolygonItem) and getattr(item, "kind", None):
                return str(item.kind).replace("_", " ").capitalize(), glyph
            return label, glyph
    return type(item).__name__, "mdi.shape-outline"


class ItemTreePanel(QDockWidget):
    """Dock listing the canvas contents as an editable tree."""

    def __init__(self, window):
        super().__init__("Items", window)
        self.setObjectName("itemsDock")
        self._win = window
        self._syncing = False
        # Rows carry an int key, never the item itself: a QGraphicsItem in
        # a QVariant dangles (and crashes) once undo/open rebuilds the
        # scene. The Python wrappers here can be checked with sip first.
        self._by_key = {}
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(4, 4, 4, 4)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item", "X", "Y", "Rotation"])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setEditTriggers(QAbstractItemView.DoubleClicked
                                  | QAbstractItemView.EditKeyPressed)
        head = self.tree.header()
        head.setStretchLastSection(False)
        head.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        self.setMinimumWidth(360)
        for col in (COL_X, COL_Y, COL_ROT):
            head.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        lay.addWidget(self.tree)
        row = QHBoxLayout()
        self.count = QLabel()
        row.addWidget(self.count)
        row.addStretch(1)
        self.delete_btn = QPushButton(icons.icon("mdi.delete-outline"),
                                      "Delete")
        self.delete_btn.setToolTip("Delete the selected items (Del)")
        self.delete_btn.clicked.connect(self.delete_selected)
        row.addWidget(self.delete_btn)
        lay.addLayout(row)
        self.setWidget(body)

        scene = window.scene
        scene.changed_by_user.connect(self.refresh)
        scene.selectionChanged.connect(self._from_scene_selection)
        window._undo_stack.indexChanged.connect(lambda *_: self.refresh())
        self.tree.itemSelectionChanged.connect(self._to_scene_selection)
        self.tree.itemChanged.connect(self._edited)
        self.visibilityChanged.connect(lambda on: on and self.refresh())

    # ── building ──────────────────────────────────────────────
    def refresh(self):
        if sip.isdeleted(self) or self.isHidden():
            return
        scene = self._win.scene
        expanded = {self._item(r) for r in self._all_rows()
                    if r.isExpanded()}
        expanded = {id(i) for i in expanded if i is not None}
        self._syncing = True
        self.tree.clear()
        self._by_key = {}
        tops = list(reversed(scene.vector_items()))      # front first
        for item in tops:
            self.tree.addTopLevelItem(self._row(item, expanded))
        self.count.setText(f"{len(tops)} item(s)")
        self._syncing = False
        self._from_scene_selection()

    def _row(self, item, expanded):
        label, glyph = describe(item)
        row = QTreeWidgetItem([label, "", "", ""])
        row.setIcon(COL_NAME, icons.icon(glyph))
        row.setToolTip(COL_NAME, label)
        key = len(self._by_key) + 1
        self._by_key[key] = item
        row.setData(COL_NAME, _ROLE, key)
        top = item.parentItem() is None
        r = item.sceneBoundingRect()
        row.setText(COL_X, f"{r.x():.1f}")
        row.setText(COL_Y, f"{r.y():.1f}")
        row.setText(COL_ROT, f"{item.rotation():.1f}°")
        solid = getattr(item, "solid", None)
        if solid:
            row.setToolTip(COL_NAME, label + " — 3D view: az {:.0f}°, el {:.0f}° — "
                           "double-click it on the canvas to spin".format(
                               math.degrees(solid.get("az", 0)),
                               math.degrees(solid.get("el", 0))))
        flags = row.flags()
        if top:                                   # children move with it
            flags |= Qt.ItemIsEditable
        row.setFlags(flags)
        # models, reactions and solids are one object to the user — their
        # spheres/polygons are regenerated, so don't list them as parts
        whole = solid or getattr(item, "mol_name", None) or \
            getattr(item, "rxn_data", None)
        if isinstance(item, GroupItem) and not whole:
            for child in reversed(item.childItems()):
                if child.isVisible():
                    row.addChild(self._row(child, expanded))
            row.setExpanded(id(item) in expanded)
        return row

    def _item(self, row):
        """The live item behind *row*, or None once it has gone."""
        item = self._by_key.get(row.data(COL_NAME, _ROLE))
        if item is None:
            return None
        # Graphics items aren't QObjects, so sip can't tell when the scene
        # frees one: ask the scene what is alive instead of the wrapper.
        live = {id(i) for i in self._win.scene.items()}
        return item if id(item) in live else None

    def _all_rows(self):
        out, stack = [], [self.tree.topLevelItem(i)
                          for i in range(self.tree.topLevelItemCount())]
        while stack:
            row = stack.pop()
            out.append(row)
            stack += [row.child(i) for i in range(row.childCount())]
        return out

    # ── selection sync ────────────────────────────────────────
    def _from_scene_selection(self):
        if self._syncing or sip.isdeleted(self) or self.isHidden():
            return
        self._syncing = True
        try:
            selected = set(map(id, self._win.scene.selectedItems()))
            for row in self._all_rows():
                item = self._item(row)
                row.setSelected(item is not None and id(item) in selected)
        except RuntimeError:
            pass
        self._syncing = False

    def _to_scene_selection(self):
        if self._syncing:
            return
        self._syncing = True
        scene = self._win.scene
        scene.clearSelection()
        for row in self.tree.selectedItems():
            item = self._item(row)
            if item is not None:
                # a child inside a group can't be selected on its own in
                # Qt; select its group so the canvas still shows it
                top = item
                while top.parentItem() is not None:
                    top = top.parentItem()
                top.setSelected(True)
        self._syncing = False

    # ── editing ───────────────────────────────────────────────
    def _edited(self, row, col):
        if self._syncing or col not in (COL_X, COL_Y, COL_ROT):
            return
        item = self._item(row)
        if item is None:
            return
        try:
            value = float(row.text(col).replace("°", "").strip())
        except ValueError:
            self.refresh()                        # put the old value back
            return
        scene = self._win.scene
        scene.clear_handles()
        was = scene.snap_enabled
        scene.snap_enabled = False                # exact typed values
        try:
            if col == COL_ROT:
                item.setRotation(value)
            else:
                r = item.sceneBoundingRect()
                if col == COL_X:
                    item.moveBy(value - r.x(), 0)
                else:
                    item.moveBy(0, value - r.y())
        finally:
            scene.snap_enabled = was
        scene.changed_by_user.emit()              # undoable; refreshes

    def delete_selected(self):
        scene = self._win.scene
        items = [self._item(r) for r in self.tree.selectedItems()]
        items = [i for i in items if i is not None]
        if not items:
            return
        scene.clear_handles()
        for item in items:
            if item.scene() is not scene:
                continue                          # went with its parent
            parent = item.parentItem()
            if parent is not None:                # remove from its group
                parent.removeFromGroup(item)
            scene.removeItem(item)
        scene.changed_by_user.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace) and \
                self.tree.state() != QAbstractItemView.EditingState:
            self.delete_selected()
            return
        super().keyPressEvent(event)
