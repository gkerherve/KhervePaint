"""Drawing-size dialog: physical figure sizes (in/mm) at a chosen DPI.

Publication figures are specified in physical units — e.g. ACS journals
use a single-column width of 3.25 in (8.25 cm) and a double-column width
of 7.0 in (17.78 cm), at 300 dpi.  This dialog lets the canvas be set in
px, inches or millimetres with a DPI, offers journal/paper presets, or
fits the canvas to the drawing.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
                             QSpinBox, QVBoxLayout)

#: Presets: label -> (unit, width, height, dpi). unit in {"px","in","mm"}.
PRESETS = [
    ("Custom", None),
    ("ACS single column — 3.25 in @ 300 dpi", ("in", 3.25, 2.50, 300)),
    ("ACS double column — 7.0 in @ 300 dpi", ("in", 7.00, 4.00, 300)),
    ("ACS max height — 7.0 × 9.5 in @ 300 dpi", ("in", 7.00, 9.50, 300)),
    ("A4 portrait @ 300 dpi", ("mm", 210, 297, 300)),
    ("A4 landscape @ 300 dpi", ("mm", 297, 210, 300)),
    ("US Letter portrait @ 300 dpi", ("in", 8.5, 11.0, 300)),
    ("Square — 100 mm @ 300 dpi", ("mm", 100, 100, 300)),
    ("Slide 16:9 — 1920 × 1080 px", ("px", 1920, 1080, 96)),
    ("Slide 4:3 — 1024 × 768 px", ("px", 1024, 768, 96)),
]

_UNITS = ["px", "in", "mm"]


def _to_px(value, unit, dpi):
    if unit == "in":
        return value * dpi
    if unit == "mm":
        return value / 25.4 * dpi
    return value


def _from_px(px, unit, dpi):
    if unit == "in":
        return px / dpi
    if unit == "mm":
        return px / dpi * 25.4
    return px


class CanvasSizeDialog(QDialog):
    """``result_value()`` returns ``("size", px_w, px_h, dpi)`` or
    ``("fit", selection_only)``."""

    def __init__(self, parent=None, current=(800, 600), dpi=96,
                 has_selection=False):
        super().__init__(parent)
        self.setWindowTitle("Drawing size")
        self.setMinimumWidth(420)
        self._unit = "px"
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.preset_combo = QComboBox()
        for label, data in PRESETS:
            self.preset_combo.addItem(label, data)
        form.addRow("Preset", self.preset_combo)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(_UNITS)
        form.addRow("Units", self.unit_combo)

        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(36, 2400)
        self.dpi_spin.setValue(int(dpi) or 96)
        self.dpi_spin.setSuffix(" dpi")
        form.addRow("Resolution", self.dpi_spin)

        self.width_spin = QDoubleSpinBox()
        self.height_spin = QDoubleSpinBox()
        size_row = QHBoxLayout()
        size_row.addWidget(self.width_spin)
        size_row.addWidget(QLabel("×"))
        size_row.addWidget(self.height_spin)
        form.addRow("Width × Height", size_row)

        self._pixel_label = QLabel()
        form.addRow("", self._pixel_label)

        self.fit_check = QCheckBox("Fit canvas to the drawing instead")
        layout.addWidget(self.fit_check)
        self.selection_only = QCheckBox("Use selection only")
        self.selection_only.setEnabled(has_selection)
        self.selection_only.setChecked(has_selection)
        layout.addWidget(self.selection_only)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # initial values: the current canvas, shown in pixels
        self._load_fields("px", current[0], current[1], int(dpi) or 96)

        self.preset_combo.activated.connect(self._apply_preset)
        self.unit_combo.currentTextChanged.connect(self._on_unit_changed)
        self.dpi_spin.valueChanged.connect(self._on_manual_change)
        self.width_spin.valueChanged.connect(self._on_manual_change)
        self.height_spin.valueChanged.connect(self._on_manual_change)
        self.fit_check.toggled.connect(self._on_fit_toggled)

    # ----------------------------------------------------------- helpers
    def _configure_spins(self, unit):
        for spin in (self.width_spin, self.height_spin):
            spin.blockSignals(True)
            if unit == "px":
                spin.setDecimals(0); spin.setRange(1, 30000)
                spin.setSuffix(" px")
            elif unit == "in":
                spin.setDecimals(2); spin.setRange(0.1, 60)
                spin.setSuffix(" in")
            else:
                spin.setDecimals(1); spin.setRange(1, 1500)
                spin.setSuffix(" mm")
            spin.blockSignals(False)

    def _load_fields(self, unit, width, height, dpi):
        self._unit = unit
        for widget, value in ((self.unit_combo, unit), (self.dpi_spin, dpi)):
            widget.blockSignals(True)
        self.unit_combo.setCurrentText(unit)
        self.dpi_spin.setValue(int(dpi))
        self.unit_combo.blockSignals(False)
        self.dpi_spin.blockSignals(False)
        self._configure_spins(unit)
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self._update_pixel_label()

    def _update_pixel_label(self):
        dpi = self.dpi_spin.value()
        pw = max(1, round(_to_px(self.width_spin.value(), self._unit, dpi)))
        ph = max(1, round(_to_px(self.height_spin.value(), self._unit, dpi)))
        self._pixel_label.setText(f"= {pw} × {ph} px")

    # ----------------------------------------------------------- slots
    def _apply_preset(self, index):
        data = self.preset_combo.itemData(index)
        if data is None:                       # "Custom"
            return
        unit, width, height, dpi = data
        self._load_fields(unit, width, height, dpi)

    def _on_unit_changed(self, new_unit):
        if new_unit == self._unit:
            return
        dpi = self.dpi_spin.value()
        px_w = _to_px(self.width_spin.value(), self._unit, dpi)
        px_h = _to_px(self.height_spin.value(), self._unit, dpi)
        self._unit = new_unit
        self._configure_spins(new_unit)
        self.width_spin.blockSignals(True)
        self.height_spin.blockSignals(True)
        self.width_spin.setValue(_from_px(px_w, new_unit, dpi))
        self.height_spin.setValue(_from_px(px_h, new_unit, dpi))
        self.width_spin.blockSignals(False)
        self.height_spin.blockSignals(False)
        self._set_custom()
        self._update_pixel_label()

    def _on_manual_change(self, *_):
        self._set_custom()
        self._update_pixel_label()

    def _on_fit_toggled(self, fit):
        for widget in (self.preset_combo, self.unit_combo, self.dpi_spin,
                       self.width_spin, self.height_spin):
            widget.setEnabled(not fit)

    def _set_custom(self):
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)

    # ----------------------------------------------------------- result
    def result_value(self):
        if self.fit_check.isChecked():
            return ("fit", self.selection_only.isChecked())
        dpi = self.dpi_spin.value()
        pw = max(1, round(_to_px(self.width_spin.value(), self._unit, dpi)))
        ph = max(1, round(_to_px(self.height_spin.value(), self._unit, dpi)))
        return ("size", pw, ph, dpi)
