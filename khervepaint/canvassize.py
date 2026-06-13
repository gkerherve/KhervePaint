"""Drawing-size dialog: publication presets, fit-to-drawing, custom.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QDialog,
                             QDialogButtonBox, QFormLayout, QHBoxLayout,
                             QLabel, QRadioButton, QSpinBox, QVBoxLayout)

#: Publication-ready canvas sizes in pixels: (label, width, height).
#: Print sizes are at 300 dpi; slides at their native pixel size.
PRESETS = [
    ("A4 portrait — 300 dpi", 2480, 3508),
    ("A4 landscape — 300 dpi", 3508, 2480),
    ("A5 portrait — 300 dpi", 1748, 2480),
    ("US Letter portrait — 300 dpi", 2550, 3300),
    ("Journal single column (90 mm) — 300 dpi", 1063, 1417),
    ("Journal double column (190 mm) — 300 dpi", 2244, 1683),
    ("Square — 2000 px", 2000, 2000),
    ("Slide 16:9 — 1920×1080", 1920, 1080),
    ("Slide 4:3 — 1024×768", 1024, 768),
]


class CanvasSizeDialog(QDialog):
    """Choose a new canvas size. ``result_value()`` returns one of
    ``("preset"|"custom", width, height)`` or ``("fit", selection_only)``."""

    def __init__(self, parent=None, current=(800, 600), has_selection=False):
        super().__init__(parent)
        self.setWindowTitle("Drawing size")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        self._group = QButtonGroup(self)

        # --- preset ---------------------------------------------------
        self.preset_radio = QRadioButton("Standard size")
        self.preset_radio.setChecked(True)
        self._group.addButton(self.preset_radio)
        layout.addWidget(self.preset_radio)
        self.preset_combo = QComboBox()
        for label, w, h in PRESETS:
            self.preset_combo.addItem(f"{label}  ({w}×{h})", (w, h))
        layout.addWidget(self.preset_combo)

        # --- custom ---------------------------------------------------
        self.custom_radio = QRadioButton("Custom size (px)")
        self._group.addButton(self.custom_radio)
        layout.addWidget(self.custom_radio)
        form = QFormLayout()
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 30000)
        self.width_spin.setValue(int(current[0]))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(1, 30000)
        self.height_spin.setValue(int(current[1]))
        row = QHBoxLayout()
        row.addWidget(self.width_spin)
        row.addWidget(QLabel("×"))
        row.addWidget(self.height_spin)
        form.addRow("Width × Height", row)
        layout.addLayout(form)

        # --- fit to drawing ------------------------------------------
        self.fit_radio = QRadioButton("Fit to drawing")
        self._group.addButton(self.fit_radio)
        layout.addWidget(self.fit_radio)
        self.selection_only = QCheckBox("Use selection only")
        self.selection_only.setEnabled(has_selection)
        self.selection_only.setChecked(has_selection)
        layout.addWidget(self.selection_only)

        # editing a field selects its radio
        self.preset_combo.activated.connect(
            lambda *_: self.preset_radio.setChecked(True))
        self.width_spin.valueChanged.connect(
            lambda *_: self.custom_radio.setChecked(True))
        self.height_spin.valueChanged.connect(
            lambda *_: self.custom_radio.setChecked(True))
        self.selection_only.toggled.connect(
            lambda *_: self.fit_radio.setChecked(True))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def result_value(self):
        if self.fit_radio.isChecked():
            return ("fit", self.selection_only.isChecked())
        if self.custom_radio.isChecked():
            return ("custom", self.width_spin.value(), self.height_spin.value())
        w, h = self.preset_combo.currentData()
        return ("preset", w, h)
