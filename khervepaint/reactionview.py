"""Reaction builder — write a chemical reaction with real molecules.

Chemistry ▸ Reaction builder… (also Molecules ▸ Build, and double-click
or right-click ▸ Edit reaction… on a placed scheme) opens this dialog:

* an **Equation** line — type ``CH4 + 2 O2 -> CO2 + 2 H2O`` and press
  Enter; names and formulas resolve to library molecules where they can;
* **Reactants** / **Products** tables — coefficient, species, state and
  a per-species drawing style; *Add* offers the molecule library, a typed
  formula or name, or the 3D Molecule builder for a new structure;
* the **arrow** (reaction, equilibrium, reversible, resonance,
  retrosynthesis, no reaction) with reagents above and conditions below;
* a live **balance** check (atoms and charge) with one-click balancing,
  and a live preview.

OK drops the scheme as ONE group of ordinary editable items, tagged with
the reaction (``rxn_data``) so it re-opens here; the tag round-trips
through undo snapshots (document.py) and SVG (svgio.py).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import copy
import math

from PyQt5.QtCore import QCoreApplication, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox,
                             QDialog, QDialogButtonBox, QGraphicsScene,
                             QGraphicsView, QGridLayout, QGroupBox,
                             QHBoxLayout, QHeaderView, QInputDialog, QLabel,
                             QLineEdit, QMenu, QPushButton, QTableWidget,
                             QTableWidgetItem, QToolButton, QVBoxLayout)

from . import molecules, molrepr, reaction

#: Bond length (px) of the dialog's preview.
_PREVIEW_UNIT = 40.0
#: Symbols offered next to the above/below-arrow fields.
_SYMBOLS = ["Δ", "hν", "°C", "→", "⁺", "⁻", "·", "½", "α", "β", "μ"]


# ------------------------------------------------------------- placement
def default_unit(scene):
    """Bond length for a new scheme: a fraction of the page width, so a
    two-step scheme fills a column figure."""
    return (scene.sceneRect().width() or 800.0) / 24.0


def build_items(rxn, unit):
    from .ai_assistant import _spec_to_item
    specs, w, h = reaction.reaction_specs(rxn, unit)
    return [it for it in (_spec_to_item(s) for s in specs)
            if it is not None], w, h


def place_reaction(scene, rxn, center=None, replace=None, commit=True):
    """Drop *rxn* on *scene* as one tagged group centred on *center* (the
    page centre by default). With *replace*, the old scheme is swapped
    out in place — same centre, rotation, stacking and scale (a resized
    group redraws at the matching bond length). Undoable when *commit*."""
    rxn = reaction.normalise(rxn)
    page_w = scene.sceneRect().width() or 800.0
    unit = rxn.get("unit")
    if replace is not None:
        tf = replace.transform()
        unit = (unit or default_unit(scene)) * (math.hypot(tf.m11(),
                                                           tf.m12()) or 1.0)
        if center is None:
            center = replace.sceneBoundingRect().center()
    if not unit:                          # new: fit the page if it is long
        unit = default_unit(scene)
        _s, w, _h = reaction.reaction_specs(rxn, unit)
        if w > 0.94 * page_w:
            unit *= 0.94 * page_w / w
    rxn["unit"] = round(float(unit), 3)
    items, w, h = build_items(rxn, unit)
    if center is None:
        center = scene.sceneRect().center()
    rotation = z = None
    if replace is not None:
        rotation, z = replace.rotation(), replace.zValue()
        scene.clear_handles()
        scene.removeItem(replace)
    top = scene._drop_items(items, center, w, h)
    if rotation:
        top.setRotation(rotation)
    if z is not None:
        top.setZValue(z)
    top.rxn_data = rxn
    if commit:
        scene.changed_by_user.emit()
    return top


def species_from_model(item):
    """A reaction species for a placed molecule model (None for crystals
    and anything else)."""
    name = getattr(item, "mol_name", None)
    if not name or molecules.is_crystal(name):
        return None
    if getattr(item, "mol_atoms", None):
        return {"coef": "1", "atoms": copy.deepcopy(item.mol_atoms),
                "bonds": copy.deepcopy(item.mol_bonds or [])}
    if name in molecules._MODELS:
        return {"coef": "1", "name": name}
    return None


def open_reaction_builder(view, item=None):
    """Open the builder on *item*'s reaction (or a new one, seeded with
    any molecule models selected on the canvas as reactants) and place /
    redraw the result. Returns the placed group, or None if cancelled."""
    scene = view.scene()
    rxn = getattr(item, "rxn_data", None) if item is not None else None
    seed = []
    if rxn is None:
        seed = [s for s in (species_from_model(it)
                            for it in scene.selectedItems()) if s]
    dlg = ReactionBuilder(rxn, seed=seed, parent=view.window())
    if not dlg.exec_():
        return None
    if rxn is not None:
        return place_reaction(scene, dlg.reaction(), replace=item)
    centre = view.mapToScene(view.viewport().rect().center())
    return place_reaction(scene, dlg.reaction(), centre)


# ------------------------------------------------------------------ UI
class _SideTable(QGroupBox):
    """Reactants or products: coefficient | species | state | draw as."""

    changed = pyqtSignal()

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.species = []
        self._filling = False
        lay = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            [self.tr("Coef."), self.tr("Species"), self.tr("State"),
             self.tr("Draw as")])
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        head.setSectionResizeMode(1, QHeaderView.Stretch)
        head.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        head.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemChanged.connect(self._on_item_changed)
        lay.addWidget(self.table)
        row = QHBoxLayout()
        add = QToolButton()
        add.setText(self.tr("Add ▾"))
        add.setPopupMode(QToolButton.InstantPopup)
        add.setMenu(self._add_menu())
        add.setToolTip(self.tr("Add a library molecule, a formula / name, "
                               "or build a new molecule"))
        row.addWidget(add)
        for text, tip, slot in (
                (self.tr("Remove"), self.tr("Remove the selected species"),
                 self._remove),
                ("▲", self.tr("Move up"), lambda: self._move(-1)),
                ("▼", self.tr("Move down"), lambda: self._move(1))):
            btn = QToolButton()
            btn.setText(text)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        row.addStretch(1)
        lay.addLayout(row)

    def _add_menu(self):
        menu = QMenu(self)
        menu.addAction(self.tr("Formula or name…"), self._add_typed)
        menu.addAction(self.tr("Build a molecule…"), self._add_built)
        menu.addSeparator()
        for title, names in molecules.CATEGORIES:
            if title == "Polymers":
                continue
            sub = menu.addMenu(
                QCoreApplication.translate("molecules", title))
            for key in names:
                label = QCoreApplication.translate(
                    "molecules", molecules.LABELS.get(key, key))
                sub.addAction(label,
                              lambda _=False, k=key: self.add({"name": k}))
        return menu

    # ------------------------------------------------------------ data
    def set_species(self, species):
        self.species = [dict(sp) for sp in species]
        self._fill()

    def add(self, sp):
        sp = dict(sp)
        sp.setdefault("coef", "1")
        sp.setdefault("state", "")
        self.species.append(sp)
        self._fill()
        self.table.selectRow(len(self.species) - 1)
        self.changed.emit()

    def _fill(self):
        self._filling = True
        t = self.table
        t.setRowCount(len(self.species))
        for r, sp in enumerate(self.species):
            coef = QTableWidgetItem(str(reaction.coef_value(sp)))
            coef.setTextAlignment(Qt.AlignCenter)
            t.setItem(r, 0, coef)
            name = QTableWidgetItem(reaction.species_text(sp))
            name.setToolTip(
                self.tr("Hand-built molecule — type over it to replace it")
                if sp.get("atoms") else
                self.tr("Type a name or formula (ethanol, H2O, Fe2O3, "
                        "SO4^2-…)"))
            t.setItem(r, 1, name)
            state = QComboBox()
            state.addItems(["—", "(s)", "(l)", "(g)", "(aq)"])
            state.setCurrentIndex(reaction.STATES.index(sp.get("state", "")))
            state.currentIndexChanged.connect(
                lambda i, row=r: self._set(row, "state", reaction.STATES[i]))
            t.setCellWidget(r, 2, state)
            mode = QComboBox()
            mode.addItem(self.tr("(scheme style)"), None)
            for m in reaction.STYLES:
                mode.addItem(QCoreApplication.translate(
                    "molrepr", molrepr.MODE_LABELS[m]), m)
            mode.setCurrentIndex(max(0, mode.findData(sp.get("mode"))))
            mode.setEnabled(reaction.species_atoms(sp)[0] is not None)
            mode.currentIndexChanged.connect(
                lambda i, row=r, cb=mode: self._set(row, "mode",
                                                    cb.itemData(i)))
            t.setCellWidget(r, 3, mode)
        self._filling = False

    def _set(self, row, key, value):
        if row >= len(self.species):
            return
        if value:
            self.species[row][key] = value
        else:
            self.species[row].pop(key, None)
        self.changed.emit()

    def _on_item_changed(self, cell):
        if self._filling or cell.row() >= len(self.species):
            return
        sp = self.species[cell.row()]
        if cell.column() == 0:
            sp["coef"] = str(reaction.coef_value({"coef": cell.text()}))
        elif cell.column() == 1:
            text = cell.text().strip()
            if text == reaction.species_text(sp):
                return
            new = reaction.resolve_species(text)
            if new is None:
                self.species.pop(cell.row())
            else:
                for key in ("name", "formula", "atoms", "bonds"):
                    sp.pop(key, None)
                sp.update(new)
        # re-fill after the edit commits (the edited cell is replaced)
        QTimer.singleShot(0, self._fill)
        self.changed.emit()

    def _remove(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.species):
            self.species.pop(row)
            self._fill()
            self.changed.emit()

    def _move(self, step):
        row = self.table.currentRow()
        dest = row + step
        if 0 <= row < len(self.species) and 0 <= dest < len(self.species):
            self.species[row], self.species[dest] = \
                self.species[dest], self.species[row]
            self._fill()
            self.table.selectRow(dest)
            self.changed.emit()

    def _add_typed(self):
        text, ok = QInputDialog.getText(
            self, self.tr("Add species"),
            self.tr("Name or formula — e.g. ethanol, H2O, CH3COOH, Fe2O3, "
                    "NH4+, SO4^2-:"))
        sp = reaction.resolve_species(text) if ok else None
        if sp:
            self.add(sp)

    def _add_built(self):
        from .molview import MoleculeViewer
        atoms, bonds = molecules.single_atom("C")
        dlg = MoleculeViewer("custom", atoms=atoms, bonds=bonds, parent=self)
        if dlg.exec_():
            a, b = dlg.result()
            self.add({"atoms": a or atoms, "bonds": b or bonds})


class ReactionBuilder(QDialog):
    """Compose, balance and preview a reaction scheme."""

    def __init__(self, rxn=None, seed=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Reaction builder"))
        self.setMinimumSize(860, 660)
        start = reaction.normalise(rxn or reaction.new_reaction())
        if seed and not start["reactants"]:
            start["reactants"] = [dict(s, coef="1", state="") for s in seed]
        self._unit = start.get("unit")
        lay = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Equation:")))
        self.eq = QLineEdit()
        self.eq.setPlaceholderText(self.tr(
            "e.g.  CH4 + 2 O2 -> CO2 + 2 H2O   ·   "
            "N2 + 3 H2 <=>[Fe][450 °C] 2 NH3"))
        self.eq.setToolTip(self.tr(
            "Type a reaction and press Enter.\n"
            "Arrows: ->  <=> (equilibrium)  <-> (resonance)  => (retro)  "
            "-/-> (no reaction)\n"
            "Conditions in brackets after the arrow: ->[H2SO4][reflux]\n"
            "States: H2O(l), NaCl(aq)   Charges: Na+, SO4^2-, Fe^3+"))
        self.eq.returnPressed.connect(self._parse)
        row.addWidget(self.eq, 1)
        apply_btn = QPushButton(self.tr("Apply"))
        apply_btn.clicked.connect(self._parse)
        row.addWidget(apply_btn)
        lay.addLayout(row)
        self.eq_error = QLabel()
        self.eq_error.setStyleSheet("color:#b3261e;")
        self.eq_error.hide()
        lay.addWidget(self.eq_error)

        sides = QHBoxLayout()
        self.left = _SideTable(self.tr("Reactants"))
        self.right = _SideTable(self.tr("Products"))
        sides.addWidget(self.left)
        sides.addWidget(self.right)
        lay.addLayout(sides, 2)

        grid = QGridLayout()
        self.arrow = QComboBox()
        for key in reaction.ARROWS:
            self.arrow.addItem(QCoreApplication.translate(
                "reaction", reaction.ARROW_LABELS[key]), key)
        self.style = QComboBox()
        for key in reaction.STYLES:
            self.style.addItem(QCoreApplication.translate(
                "molrepr", molrepr.MODE_LABELS[key]), key)
        self.style.setToolTip(self.tr(
            "How the molecules are drawn (each species "
            "can override it under Draw as)"))
        self.above = QLineEdit()
        self.above.setPlaceholderText(
            self.tr("reagent / catalyst, e.g. H2SO4"))
        self.below = QLineEdit()
        self.below.setPlaceholderText(
            self.tr("conditions, e.g. Δ, 80 °C, 2 h"))
        grid.addWidget(QLabel(self.tr("Arrow:")), 0, 0)
        grid.addWidget(self.arrow, 0, 1)
        grid.addWidget(QLabel(self.tr("Above arrow:")), 0, 2)
        grid.addLayout(self._with_symbols(self.above), 0, 3)
        grid.addWidget(QLabel(self.tr("Draw molecules as:")), 1, 0)
        grid.addWidget(self.style, 1, 1)
        grid.addWidget(QLabel(self.tr("Below arrow:")), 1, 2)
        grid.addLayout(self._with_symbols(self.below), 1, 3)
        self.states = QCheckBox(self.tr("State symbols"))
        self.labels = QCheckBox(self.tr("Name labels"))
        self.labels.setToolTip(
            self.tr("Caption each library molecule with its name"))
        checks = QHBoxLayout()
        checks.addWidget(self.states)
        checks.addWidget(self.labels)
        checks.addStretch(1)
        grid.addLayout(checks, 2, 1, 1, 3)
        grid.setColumnStretch(3, 1)
        lay.addLayout(grid)

        row = QHBoxLayout()
        self.status = QLabel()
        row.addWidget(self.status, 1)
        balance = QPushButton(self.tr("Balance"))
        balance.setToolTip(self.tr(
            "Set the smallest whole-number coefficients that "
            "conserve every element and the charge"))
        balance.clicked.connect(self._balance)
        row.addWidget(balance)
        lay.addLayout(row)

        self.preview = QGraphicsView(QGraphicsScene(self))
        self.preview.setRenderHint(QPainter.Antialiasing)
        self.preview.setBackgroundBrush(QColor("#ffffff"))
        self.preview.setMinimumHeight(170)
        lay.addWidget(self.preview, 2)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

        self._load(start)
        for table in (self.left, self.right):
            table.changed.connect(self._changed)
        self.arrow.currentIndexChanged.connect(self._changed)
        self.style.currentIndexChanged.connect(self._changed)
        self.above.textChanged.connect(self._changed)
        self.below.textChanged.connect(self._changed)
        self.states.toggled.connect(self._changed)
        self.labels.toggled.connect(self._changed)

    def _with_symbols(self, edit):
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        btn = QToolButton()
        btn.setText("Ω ▾")
        btn.setToolTip(self.tr("Insert a symbol"))
        btn.setPopupMode(QToolButton.InstantPopup)
        menu = QMenu(btn)
        for sym in _SYMBOLS:
            menu.addAction(sym, lambda s=sym: edit.insert(s))
        btn.setMenu(menu)
        row.addWidget(btn)
        return row

    # ------------------------------------------------------------ state
    def _load(self, rxn):
        widgets = (self.arrow, self.style, self.above, self.below,
                   self.states, self.labels)
        for w in widgets:
            w.blockSignals(True)
        self.arrow.setCurrentIndex(max(0, self.arrow.findData(rxn["arrow"])))
        self.style.setCurrentIndex(max(0, self.style.findData(rxn["style"])))
        self.above.setText(rxn.get("above", ""))
        self.below.setText(rxn.get("below", ""))
        self.states.setChecked(bool(rxn.get("states", True)))
        self.labels.setChecked(bool(rxn.get("labels", False)))
        for w in widgets:
            w.blockSignals(False)
        self.left.set_species(rxn["reactants"])
        self.right.set_species(rxn["products"])
        self._refresh()

    def reaction(self):
        """The reaction as currently edited (a normalised dict)."""
        rxn = {"reactants": self.left.species, "products": self.right.species,
               "arrow": self.arrow.currentData(),
               "style": self.style.currentData(),
               "above": self.above.text(), "below": self.below.text(),
               "states": self.states.isChecked(),
               "labels": self.labels.isChecked()}
        if self._unit:
            rxn["unit"] = self._unit
        return reaction.normalise(rxn)

    def _changed(self):
        self.eq_error.hide()
        self._refresh()

    def _refresh(self):
        rxn = self.reaction()
        report = reaction.balance_report(rxn)
        self.status.setText(reaction.balance_text(report))
        color = "#1b7f3b" if report["balanced"] else "#b3261e"
        if not rxn["reactants"] or not rxn["products"]:
            color = "#666666"
        self.status.setStyleSheet(f"color:{color}; font-weight:bold;")
        if not self.eq.hasFocus():
            self.eq.setText(reaction.to_equation(rxn))
        scene = self.preview.scene()
        scene.clear()
        items, _w, _h = build_items(rxn, _PREVIEW_UNIT)
        for it in items:
            scene.addItem(it)
        rect = scene.itemsBoundingRect().adjusted(-12, -12, 12, 12)
        scene.setSceneRect(rect)
        self._fit()

    def _fit(self):
        rect = self.preview.sceneRect()
        view = self.preview.viewport().rect()
        if rect.isEmpty() or view.isEmpty():
            return
        k = min(view.width() / rect.width(), view.height() / rect.height(),
                1.0)                          # shrink to fit, never blow up
        self.preview.resetTransform()
        self.preview.scale(k, k)
        self.preview.centerOn(rect.center())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def showEvent(self, event):
        super().showEvent(event)
        self._fit()

    def _parse(self):
        try:
            rxn = reaction.parse_equation(self.eq.text())
        except ValueError as exc:
            self.eq_error.setText(str(exc))
            self.eq_error.show()
            return
        current = self.reaction()
        for key in ("style", "states", "labels"):   # the look stays
            rxn[key] = current[key]
        self.eq_error.hide()
        self.eq.clearFocus()
        self._load(reaction.normalise(rxn))

    def _balance(self):
        rxn = self.reaction()
        problem = reaction.auto_balance(rxn)
        if problem:
            self.status.setText(problem)
            self.status.setStyleSheet("color:#b3261e; font-weight:bold;")
            return
        self._load(rxn)
