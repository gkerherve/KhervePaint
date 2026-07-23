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
from PyQt5.QtWidgets import (QColorDialog, QComboBox, QDialog,
                             QDialogButtonBox, QGraphicsEllipseItem,
                             QGraphicsScene, QGraphicsView, QHBoxLayout,
                             QLabel, QPushButton, QSlider, QToolButton,
                             QVBoxLayout, QWidget)

from . import icons, molcolor, molecules

_HALF = math.pi / 2.0
#: (label, azimuth, elevation) for the view toolbar (icons are 3D cubes).
W = 400.0                               # preview model-box size (scene units)
STANDARD_VIEWS = [
    ("Front", 0.0, 0.0), ("Back", math.pi, 0.0),
    ("Left", -_HALF, 0.0), ("Right", _HALF, 0.0),
    ("Top", 0.0, _HALF), ("Bottom", 0.0, -_HALF),
    ("Isometric", molecules.DEFAULT_AZ, molecules.DEFAULT_EL),
]


class _Preview(QGraphicsView):
    """Renders the model. Drag empty space to orbit; drag a sphere to move
    that atom (adjust bond angles); click a sphere to select it."""

    atom_clicked = pyqtSignal(int)          # atom index, or -1 for empty
    rotated = pyqtSignal()
    atom_moved = pyqtSignal()

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
        self._mode = None               # None | "orbit" | "drag"
        self._frozen = None             # captured layout while dragging

    def rebuild(self):
        b = self._b
        scene = self.scene()
        scene.clear()
        specs = b.render_specs(W, W, frozen=self._frozen)
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
        # Keep a fixed scene rect while dragging so the view doesn't jump.
        if self._frozen is None:
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
        self._mode = None

    def mouseMoveEvent(self, event):
        if self._press is None:
            return
        delta = event.pos() - self._press
        if self._mode is None:
            if abs(delta.x()) + abs(delta.y()) < 4:
                return
            # start dragging the pressed atom, else orbit the whole model
            b = self._b
            if self._press_atom is not None and b.editable:
                self._mode = "drag"
                self._frozen = molecules.fit_params(
                    b.atoms, b.bonds, W, W, b.az, b.el, b.bond, b.rscale)
            else:
                self._mode = "orbit"
        self._press = event.pos()
        b = self._b
        if self._mode == "orbit":
            b.az = (b.az + delta.x() * 0.012) % (2 * math.pi)
            b.el = max(-_HALF, min(_HALF, b.el - delta.y() * 0.012))
            self.rebuild()
            self.rotated.emit()
        else:                                  # drag the atom in the view plane
            d = self.mapToScene(event.pos()) - self.mapToScene(
                event.pos() - delta)
            molecules.drag_atom(b.atoms, self._press_atom, d.x(), d.y(),
                                b.az, b.el, b.bond, self._frozen["scale"])
            self.rebuild()

    def mouseReleaseEvent(self, event):
        if self._mode == "drag":
            self._b.dirty = True
            self._frozen = None
            self.rebuild()                     # re-fit to the new geometry
            self.atom_moved.emit()
        elif self._mode is None and self._press is not None:
            self.atom_clicked.emit(self._press_atom if self._press_atom
                                   is not None else -1)
        self._press = None
        self._mode = None


class MoleculeViewer(QDialog):
    """Rotate and build a molecule / crystal in 3D."""

    def __init__(self, name, az=None, el=None, bond=None,
                 atoms=None, bonds=None, repr=None, colors=None, cells=None,
                 tilts=None, parent=None):
        super().__init__(parent)
        self.name = name
        self.editable = not molecules.is_crystal(name)
        self.az = molecules.DEFAULT_AZ if az is None else az
        self.el = molecules.DEFAULT_EL if el is None else el
        self.bond = (bond if bond is not None else molecules.default_bond(name))
        self._repr = repr or "3d"
        self.selected = None
        self.order = 1
        self.dirty = atoms is not None
        #: Per-element/site colour overrides (crystals; see `molcolor`).
        self.colors = dict(colors or {})
        #: Supercell repeats + per-cell tilt map (crystals only).
        self.cells = tuple(cells) if cells else (1, 1, 1)
        self.tilts = {k: list(v) for k, v in (tilts or {}).items()}
        self._owners = []               # atom index -> "i,j,k" home cell
        # Editable structure: reuse a hand-built one, else load the model.
        # A crystal keeps its fixed lattice, but its (supercell) atoms are
        # still loaded so clicked spheres map to an element and a cell.
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
            self._sync_crystal()

        label = "new molecule" if name == "custom" \
            else molecules.LABELS.get(name, name)
        self.setWindowTitle(f"Molecule builder — {label}")
        self.setMinimumSize(600, 540)
        layout = QVBoxLayout(self)

        layout.addLayout(self._view_toolbar())
        self.preview = _Preview(self)
        self.preview.atom_clicked.connect(self._on_atom_clicked)
        self.preview.atom_moved.connect(self._update_status)
        layout.addWidget(self.preview, 1)

        self.status = QLabel()
        self.status.setStyleSheet("color:#666;")
        layout.addWidget(self.status)

        layout.addLayout(self._bond_row())
        if self.editable:
            layout.addLayout(self._palette_row())
        layout.addLayout(self._color_row())
        if not self.editable and molecules.can_stack(name):
            layout.addLayout(self._supercell_row())
        if self.editable:
            layout.addLayout(self._repr_row())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_status()
        self.preview.rebuild()

    # ---------------------------------------------------------------- UI
    def _view_toolbar(self):
        from PyQt5.QtCore import QSize
        row = QHBoxLayout()
        row.addWidget(QLabel("View:"))
        for title, vaz, vel in STANDARD_VIEWS:
            btn = QToolButton()
            btn.setIcon(icons.view_cube_icon(title.lower()))
            btn.setIconSize(QSize(26, 26))
            btn.setText(title)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setAutoRaise(True)
            btn.setToolTip(f"View from {title.lower()}")
            btn.clicked.connect(lambda _=False, a=vaz, e=vel: self._set_view(a, e))
            row.addWidget(btn)
        row.addStretch(1)
        return row

    def _bond_row(self):
        row = QHBoxLayout()
        self._bond_label = QLabel("Bond length:" if self.editable
                                  else "Atom spacing:")
        row.addWidget(self._bond_label)
        self.bond_slider = QSlider(Qt.Horizontal)
        # Crystals slide all the way to 0: the lattice contracts about its
        # centre until the spheres touch (a close-packed electrode look)
        # and finally coincide.
        self.bond_slider.setRange(80 if self.editable else 0, 260)
        self.bond_slider.setValue(int(self.bond * 100))
        self.bond_slider.valueChanged.connect(self._on_bond)
        self.bond_slider.setToolTip(
            "Spread the atoms apart (molecule bond length)" if self.editable
            else "Contract or expand the lattice — near 0 the spheres "
                 "touch and overlap")
        row.addWidget(self.bond_slider, 1)
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

    def _color_row(self):
        row = QHBoxLayout()
        row.addWidget(QLabel("Atom colour:"))
        pick = QPushButton("Colour…")
        pick.setToolTip("Recolour the selected atom (a crystal recolours "
                        "every atom of that element and site)")
        pick.clicked.connect(self._pick_color)
        row.addWidget(pick)
        reset = QPushButton("Reset colours")
        reset.setToolTip("Restore the standard CPK / site colours")
        reset.clicked.connect(self._reset_colors)
        row.addWidget(reset)
        row.addStretch(1)
        return row

    def _supercell_row(self):
        from PyQt5.QtWidgets import QSpinBox
        row = QHBoxLayout()
        row.addWidget(QLabel("Supercell:"))
        self.cell_spins = []
        for axis in range(3):
            sp = QSpinBox()
            sp.setRange(1, 6)
            sp.setValue(self.cells[axis])
            sp.valueChanged.connect(self._on_cells)
            self.cell_spins.append(sp)
            row.addWidget(sp)
            if axis < 2:
                row.addWidget(QLabel("×"))
        row.addSpacing(14)
        row.addWidget(QLabel("Tilt cell:"))
        self.tilt_spins = []
        for axis in ("x", "y", "z"):
            sp = QSpinBox()
            sp.setRange(-180, 180)
            sp.setSingleStep(5)
            sp.setSuffix("°")
            sp.setToolTip(f"Rotate the selected unit cell about {axis}")
            sp.valueChanged.connect(self._on_tilt)
            self.tilt_spins.append(sp)
            row.addWidget(sp)
        reset = QPushButton("Reset tilts")
        reset.clicked.connect(self._reset_tilts)
        row.addWidget(reset)
        row.addStretch(1)
        return row

    def _repr_row(self):
        from . import molrepr
        row = QHBoxLayout()
        row.addWidget(QLabel("Insert as:"))
        self.repr_combo = QComboBox()
        for mode in molrepr.MODES:
            self.repr_combo.addItem(molrepr.MODE_LABELS[mode], mode)
        i = self.repr_combo.findData(self._repr)
        if i >= 0:
            self.repr_combo.setCurrentIndex(i)
        self.repr_combo.setToolTip("How to draw the molecule on the canvas — "
                                   "3D model or a 2D structural / Lewis / "
                                   "condensed formula")
        row.addWidget(self.repr_combo)
        row.addStretch(1)
        return row

    def representation(self):
        if self.editable and hasattr(self, "repr_combo"):
            return self.repr_combo.currentData()
        return "3d"

    # ---------------------------------------------------------- rendering
    def _crystal_cells(self):
        return self.cells if self.cells != (1, 1, 1) else None

    def _sync_crystal(self):
        """Refresh the crystal's atoms + per-atom home cells for the current
        supercell/tilt configuration (colour and cell picking hit-test
        against these; ordering matches the rendered specs exactly)."""
        self._owners = []
        ma, _mb, _me, self.rscale = molecules.model_data(
            self.name, self._crystal_cells(), tilts=self.tilts,
            owners=self._owners)
        self.atoms, self.bonds = [list(a) for a in ma], []
        if self.selected is not None and self.selected >= len(self.atoms):
            self.selected = None

    def render_specs(self, w, h, frozen=None):
        if self.editable:
            return molecules.specs_from_atoms(
                self.atoms, self.bonds, w, h, self.az, self.el, self.bond,
                self.rscale, tag_atoms=True, frozen=frozen)
        self._sync_crystal()
        return molecules.build_specs_oriented(self.name, w, h, self.az,
                                              self.el, self.bond,
                                              cells=self._crystal_cells(),
                                              colors=self.colors,
                                              tag_atoms=True,
                                              tilts=self.tilts)

    # ------------------------------------------------------------ actions
    def _set_view(self, az, el):
        self.az, self.el = az, el
        self.preview.rebuild()

    def _on_bond(self, value):
        self.bond = value / 100.0
        self.preview.rebuild()

    def _on_atom_clicked(self, index):
        self.selected = None if index < 0 else index
        # show the selected atom's cell tilt in the tilt spinboxes
        if hasattr(self, "tilt_spins") and self.selected is not None \
                and self.selected < len(self._owners):
            vals = self.tilts.get(self._owners[self.selected], [0, 0, 0])
            for sp, v in zip(self.tilt_spins, vals):
                sp.blockSignals(True)
                sp.setValue(int(v))
                sp.blockSignals(False)
        self._update_status()
        self.preview.rebuild()

    def _on_cells(self):
        self.cells = tuple(sp.value() for sp in self.cell_spins)
        # drop tilts that now point outside the supercell
        self.tilts = {k: v for k, v in self.tilts.items()
                      if self._cell_in_range(k)}
        self.selected = None
        self.preview.rebuild()
        self._update_status()

    def _cell_in_range(self, key):
        try:
            i, j, k = (int(v) for v in key.split(","))
        except ValueError:
            return False
        return i < self.cells[0] and j < self.cells[1] and k < self.cells[2]

    def _on_tilt(self):
        if self.selected is None or self.selected >= len(self._owners):
            self.status.setText("Click an atom of the cell you want to tilt "
                                "first.")
            return
        key = self._owners[self.selected]
        vals = [sp.value() for sp in self.tilt_spins]
        if any(vals):
            self.tilts[key] = vals
        else:
            self.tilts.pop(key, None)
        self.preview.rebuild()
        # tilting re-dedups the lattice, which can renumber atoms — keep
        # the same CELL selected so the next spin tick hits the right one
        if self.selected is None or self.selected >= len(self._owners) \
                or self._owners[self.selected] != key:
            self.selected = next((i for i, o in enumerate(self._owners)
                                  if o == key), None)
            self.preview.rebuild()
        self._update_status()

    def _reset_tilts(self):
        self.tilts = {}
        if hasattr(self, "tilt_spins"):
            for sp in self.tilt_spins:
                sp.blockSignals(True)
                sp.setValue(0)
                sp.blockSignals(False)
        self.preview.rebuild()
        self._update_status()

    def _add_atom(self, element):
        anchor = self.selected if self.selected is not None else \
            (len(self.atoms) - 1 if self.atoms else None)
        if anchor is None:
            self.atoms.append([element, 0.0, 0.0, 0.0])
            self.selected = 0
        else:
            # Respect valence: don't over-bond an atom that is already full.
            free = molecules.free_valence(self.atoms, self.bonds, anchor)
            if free < self.order:
                el = self.atoms[anchor][0]
                self.status.setText(
                    f"{el} (atom {anchor}) has no room for that bond — "
                    f"{molecules.valence(el)} bonds max, {free} free.")
                return
            if molecules.valence(element) < self.order:
                self.status.setText(f"{element} can't take a "
                                    f"{['', 'single', 'double', 'triple'][self.order]} bond.")
                return
            self.selected = molecules.add_bonded_atom(
                self.atoms, self.bonds, anchor, element, self.order)
        self.dirty = True
        self._update_status()
        self.preview.rebuild()

    def _pick_color(self):
        if self.selected is None or self.selected >= len(self.atoms):
            self.status.setText("Click an atom first, then pick its colour.")
            return
        atom = self.atoms[self.selected]
        current = molcolor.atom_color(atom, self.colors)
        color = QColorDialog.getColor(QColor(current), self, "Atom colour")
        if not color.isValid():
            return
        if self.editable:                     # colour rides on the atom
            if len(atom) > 4:
                atom[4] = color.name()
            else:
                atom.append(color.name())
            self.dirty = True
        else:                                 # crystal: element/site override
            self.colors[molcolor.color_key(atom)] = color.name()
        self.preview.rebuild()

    def _reset_colors(self):
        if self.editable:
            for atom in self.atoms:
                if len(atom) > 4:
                    del atom[4:]
                    self.dirty = True
        self.colors = {}
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
            if self.selected is not None and self.selected < len(self.atoms):
                atom = self.atoms[self.selected]
                site = molcolor.SITE_LABELS.get(atom[4]) \
                    if len(atom) > 4 else None
                where = f" ({site})" if site else ""
                cell = ""
                if self.cells != (1, 1, 1) and self.selected < len(self._owners):
                    cell = " in cell (" \
                        + self._owners[self.selected].replace(",", ", ") + ")"
                tilt = " Tilt-cell spins rotate that whole cell." \
                    if hasattr(self, "tilt_spins") and cell else ""
                self.status.setText(
                    f"Selected {atom[0]}{where}{cell} — Colour… recolours "
                    f"every {atom[0]} on this site.{tilt}")
            else:
                extra = " Set Supercell counts to stack cells; click an " \
                    "atom, then tilt its cell." if hasattr(self, "tilt_spins") \
                    else ""
                self.status.setText("Drag to rotate, pick a standard view, "
                                    f"or click an atom to recolour it.{extra}")
            return
        if self.selected is not None and self.selected < len(self.atoms):
            el = self.atoms[self.selected][0]
            free = molecules.free_valence(self.atoms, self.bonds,
                                          self.selected)
            total = molecules.valence(el)
            avail = (f"{free} of {total} bonds free — click an element to "
                     "add one" if free > 0 else f"full ({total} bonds)")
            self.status.setText(f"Selected {el} (atom {self.selected}): "
                                f"{avail}. Drag it to adjust the angle.")
        else:
            self.status.setText("Click an atom to select it (then add an "
                                "element), drag an atom to bend it, or drag "
                                "the background to rotate.")

    # ------------------------------------------------------------- result
    def result(self):
        """(atoms, bonds) if the structure was hand-edited, else (None, None);
        the canvas rebuilds from these or from the named model."""
        if self.editable and self.dirty:
            return self.atoms, self.bonds
        return None, None
