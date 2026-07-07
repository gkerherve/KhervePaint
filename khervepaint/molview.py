"""Molecule Builder — rotate a molecule / crystal in 3D and build it up.

Double-clicking a placed molecule (or right-clicking ▸ Molecule builder…)
opens this window:

* a horizontal **view toolbar** (icons) snaps to Front / Back / Left /
  Right / Top / Bottom / Isometric, and you can drag the preview to orbit;
* a **bond-length** slider spreads the atoms apart;
* an **atom palette** builds the structure — click an atom to select it,
  then click an element to bond a new atom onto it (bond order 1/2/3), or
  Delete the selected atom.

On OK the chosen orientation / bond length / edited structure is handed
back to the canvas, which rebuilds the model as an ordinary editable,
savable vector group.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                             QGraphicsEllipseItem, QGraphicsScene,
                             QGraphicsView, QHBoxLayout, QLabel, QPushButton,
                             QSlider, QToolButton, QVBoxLayout, QWidget)

from . import icons, molecules

_HALF = math.pi / 2.0
#: (label, mdi glyph, azimuth, elevation) for the view toolbar.
STANDARD_VIEWS = [
    ("Front", "mdi.arrow-up-bold", 0.0, 0.0),
    ("Back", "mdi.arrow-down-bold", math.pi, 0.0),
    ("Left", "mdi.arrow-left-bold", -_HALF, 0.0),
    ("Right", "mdi.arrow-right-bold", _HALF, 0.0),
    ("Top", "mdi.arrow-up-bold-box-outline", 0.0, _HALF),
    ("Bottom", "mdi.arrow-down-bold-box-outline", 0.0, -_HALF),
    ("Isometric", "mdi.cube-outline", molecules.DEFAULT_AZ,
     molecules.DEFAULT_EL),
]


class _Preview(QGraphicsView):
    """Renders the model; drag to orbit, click a sphere to select an atom."""

    atom_clicked = pyqtSignal(int)          # atom index, or -1 for empty
    rotated = pyqtSignal()

    def __init__(self, builder, parent=None):
        super().__init__(parent)
        self._b = builder
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QColor("#ffffff"))
        self.setMinimumSize(360, 300)
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._press = None
        self._press_atom = None
        self._rotating = False

    def rebuild(self):
        b = self._b
        scene = self.scene()
        scene.clear()
        w = h = 400.0
        specs = b.render_specs(w, h)
        from .ai_assistant import _spec_to_item
        sel_item = None
        for spec in specs:
            item = _spec_to_item(spec)
            if item is None:
                continue
            scene.addItem(item)
            if "_atom" in spec:
                item.setData(0, spec["_atom"])
                if spec["_atom"] == b.selected:
                    sel_item = item
        if sel_item is not None:               # highlight the selected atom
            r = sel_item.sceneBoundingRect().adjusted(-3, -3, 3, 3)
            ring = QGraphicsEllipseItem(r)
            ring.setPen(QPen(QColor("#2176c7"), 3))
            scene.addItem(ring)
        src = scene.itemsBoundingRect().adjusted(-10, -10, 10, 10)
        scene.setSceneRect(src)
        self.fitInView(src, Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        src = self.scene().sceneRect()
        if not src.isEmpty():
            self.fitInView(src, Qt.KeepAspectRatio)

    def _atom_at(self, pos):
        for item in self.items(pos):
            data = item.data(0)
            if data is not None:
                return int(data)
        return None

    def mousePressEvent(self, event):
        self._press = event.pos()
        self._press_atom = self._atom_at(event.pos())
        self._rotating = False

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        delta = event.pos() - self._press
        if not self._rotating and abs(delta.x()) + abs(delta.y()) < 4:
            return
        self._rotating = True
        self._press = event.pos()
        self._b.az = (self._b.az + delta.x() * 0.012) % (2 * math.pi)
        self._b.el = max(-_HALF, min(_HALF, self._b.el - delta.y() * 0.012))
        self.rebuild()
        self.rotated.emit()

    def mouseReleaseEvent(self, event):
        if self._press is not None and not self._rotating:
            self.atom_clicked.emit(self._press_atom if self._press_atom
                                   is not None else -1)
        self._press = None


class MoleculeViewer(QDialog):
    """Rotate and build a molecule / crystal in 3D."""

    def __init__(self, name, az=None, el=None, bond=None,
                 atoms=None, bonds=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.editable = not molecules.is_crystal(name)
        self.az = molecules.DEFAULT_AZ if az is None else az
        self.el = molecules.DEFAULT_EL if el is None else el
        self.bond = (bond if bond is not None else molecules.default_bond(name))
        self.selected = None
        self.order = 1
        self.dirty = atoms is not None
        # Editable structure: reuse a hand-built one, else load the model.
        if self.editable:
            if atoms is not None:
                self.atoms = [list(a) for a in atoms]
                self.bonds = [list(b) for b in bonds or []]
                self.rscale = 0.92
            else:
                ma, mb, _edges, self.rscale = molecules.model_data(name)
                self.atoms = [list(a) for a in ma]
                self.bonds = [list(b) for b in mb]
        else:
            self.atoms, self.bonds, self.rscale = [], [], 0.92

        label = molecules.LABELS.get(name, name)
        self.setWindowTitle(f"Molecule builder — {label}")
        self.setMinimumSize(600, 540)
        layout = QVBoxLayout(self)

        layout.addLayout(self._view_toolbar())
        self.preview = _Preview(self)
        self.preview.atom_clicked.connect(self._on_atom_clicked)
        layout.addWidget(self.preview, 1)

        self.status = QLabel()
        self.status.setStyleSheet("color:#666;")
        layout.addWidget(self.status)

        layout.addLayout(self._bond_row())
        if self.editable:
            layout.addLayout(self._palette_row())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_status()
        self.preview.rebuild()

    # ---------------------------------------------------------------- UI
    def _view_toolbar(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("View:"))
        for title, glyph, vaz, vel in STANDARD_VIEWS:
            btn = QToolButton()
            btn.setIcon(icons.icon(glyph))
            btn.setText(title)
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setAutoRaise(True)
            btn.setToolTip(f"View from {title.lower()}")
            btn.clicked.connect(lambda _=False, a=vaz, e=vel: self._set_view(a, e))
            row.addWidget(btn)
        row.addStretch(1)
        return row

    def _bond_row(self):
        row = QHBoxLayout()
        self._bond_label = QLabel("Bond length:")
        row.addWidget(self._bond_label)
        self.bond_slider = QSlider(Qt.Horizontal)
        self.bond_slider.setRange(80, 260)          # 0.8 .. 2.6
        self.bond_slider.setValue(int(self.bond * 100))
        self.bond_slider.valueChanged.connect(self._on_bond)
        row.addWidget(self.bond_slider, 1)
        if not self.editable:                        # crystals: fixed spacing
            self._bond_label.setEnabled(False)
            self.bond_slider.setEnabled(False)
        return row

    def _palette_row(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("Add atom:"))
        for el in molecules.PALETTE:
            btn = QPushButton(el)
            btn.setFixedWidth(34)
            color = molecules.ATOM_COLORS.get(el, "#cccccc")
            text = "#111" if QColor(color).lightnessF() > 0.5 else "#fff"
            btn.setStyleSheet(f"background:{color}; color:{text}; "
                              "font-weight:bold; border:1px solid #888;")
            btn.setToolTip(f"Bond a {el} atom onto the selected atom")
            btn.clicked.connect(lambda _=False, e=el: self._add_atom(e))
            row.addWidget(btn)
        row.addSpacing(8)
        row.addWidget(QLabel("Bond:"))
        self.order_combo = QComboBox()
        self.order_combo.addItems(["single", "double", "triple"])
        self.order_combo.currentIndexChanged.connect(
            lambda i: setattr(self, "order", i + 1))
        row.addWidget(self.order_combo)
        self.del_btn = QPushButton("Delete atom")
        self.del_btn.clicked.connect(self._delete_atom)
        row.addWidget(self.del_btn)
        row.addStretch(1)
        return row

    # ---------------------------------------------------------- rendering
    def render_specs(self, w, h):
        if self.editable:
            return molecules.specs_from_atoms(
                self.atoms, self.bonds, w, h, self.az, self.el, self.bond,
                self.rscale, tag_atoms=True)
        return molecules.build_specs_oriented(self.name, w, h, self.az,
                                              self.el, self.bond)

    # ------------------------------------------------------------ actions
    def _set_view(self, az, el):
        self.az, self.el = az, el
        self.preview.rebuild()

    def _on_bond(self, value):
        self.bond = value / 100.0
        self.preview.rebuild()

    def _on_atom_clicked(self, index):
        self.selected = None if index < 0 else index
        self._update_status()
        self.preview.rebuild()

    def _add_atom(self, element):
        anchor = self.selected if self.selected is not None else \
            (len(self.atoms) - 1 if self.atoms else None)
        if anchor is None:
            self.atoms.append([element, 0.0, 0.0, 0.0])
            self.selected = 0
        else:
            self.selected = molecules.add_bonded_atom(
                self.atoms, self.bonds, anchor, element, self.order)
        self.dirty = True
        self._update_status()
        self.preview.rebuild()

    def _delete_atom(self):
        if self.selected is None or len(self.atoms) <= 1:
            return
        molecules.delete_atom(self.atoms, self.bonds, self.selected)
        self.selected = None
        self.dirty = True
        self._update_status()
        self.preview.rebuild()

    def _update_status(self):
        if not self.editable:
            self.status.setText("Drag to rotate, or pick a standard view.")
            return
        if self.selected is not None and self.selected < len(self.atoms):
            el = self.atoms[self.selected][0]
            self.status.setText(f"Selected {el} (atom {self.selected}) — "
                                "click an element to bond it on.")
        else:
            self.status.setText("Click an atom to select it, then add an "
                                "element — or drag to rotate.")

    # ------------------------------------------------------------- result
    def result(self):
        """(atoms, bonds) if the structure was hand-edited, else (None, None);
        the canvas rebuilds from these or from the named model."""
        if self.editable and self.dirty:
            return self.atoms, self.bonds
        return None, None
