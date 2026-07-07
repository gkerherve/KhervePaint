"""Interactive 3D viewer for molecule / crystal models.

Double-clicking a placed molecule or crystal opens this dialog: the model
is re-projected live as you drag to rotate it, and standard-view buttons
(Front, Back, Left, Right, Top, Bottom, Isometric) snap to the usual
orthographic viewpoints. On OK the chosen orientation (azimuth, elevation)
is returned so the canvas can rebuild the model's flat vector group at the
new angle — it stays an ordinary editable, savable drawing.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QPainter
from PyQt5.QtWidgets import (QDialog, QDialogButtonBox, QGridLayout,
                             QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
                             QWidget)

from . import molecules

#: Standard viewpoints as (azimuth, elevation) in radians.
_HALF = math.pi / 2.0
STANDARD_VIEWS = [
    ("Front", 0.0, 0.0), ("Back", math.pi, 0.0),
    ("Left", -_HALF, 0.0), ("Right", _HALF, 0.0),
    ("Top", 0.0, _HALF), ("Bottom", 0.0, -_HALF),
    ("Isometric", molecules.DEFAULT_AZ, molecules.DEFAULT_EL),
]


class _Preview(QWidget):
    """Paints a model re-projected at the current (az, el); drag to rotate."""

    def __init__(self, name, az, el, parent=None):
        super().__init__(parent)
        self.name = name
        self.az = az
        self.el = el
        self._drag = None
        self.setMinimumSize(340, 300)
        self.setCursor(Qt.OpenHandCursor)

    def set_view(self, az, el):
        self.az, self.el = az, el
        self.update()

    def mousePressEvent(self, event):
        self._drag = event.pos()
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._drag is None:
            return
        delta = event.pos() - self._drag
        self._drag = event.pos()
        self.az = (self.az + delta.x() * 0.012) % (2 * math.pi)
        self.el = max(-_HALF, min(_HALF, self.el - delta.y() * 0.012))
        self.update()

    def mouseReleaseEvent(self, event):
        self._drag = None
        self.setCursor(Qt.OpenHandCursor)

    def paintEvent(self, _event):
        from PyQt5.QtWidgets import QGraphicsScene
        from .ai_assistant import _spec_to_item
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setRenderHint(QPainter.Antialiasing)
        specs = molecules.build_specs_oriented(self.name, w * 0.9, h * 0.9,
                                               self.az, self.el)
        scene = QGraphicsScene()
        for spec in specs:
            item = _spec_to_item(spec)
            if item is not None:
                scene.addItem(item)
        src = scene.itemsBoundingRect()
        if src.isEmpty():
            return
        margin = 0.06 * min(w, h)
        target = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        scene.render(painter, target, src, Qt.KeepAspectRatio)


class MoleculeViewer(QDialog):
    """Rotate a molecule / crystal in 3D and pick a standard view."""

    def __init__(self, name, az=None, el=None, parent=None):
        super().__init__(parent)
        label = molecules.LABELS.get(name, name)
        self.setWindowTitle(f"3D view — {label}")
        self.setMinimumSize(420, 420)
        az = molecules.DEFAULT_AZ if az is None else az
        el = molecules.DEFAULT_EL if el is None else el

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"<b>{label}</b> — drag to rotate, or pick a "
                                "standard view:"))
        self.preview = _Preview(name, az, el)
        layout.addWidget(self.preview, 1)

        views = QGridLayout()
        for i, (title, vaz, vel) in enumerate(STANDARD_VIEWS):
            btn = QPushButton(title)
            btn.setToolTip(f"View from {title.lower()}")
            btn.clicked.connect(
                lambda _=False, a=vaz, e=vel: self.preview.set_view(a, e))
            views.addWidget(btn, i // 4, i % 4)
        layout.addLayout(views)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def az(self):
        return self.preview.az

    @property
    def el(self):
        return self.preview.el
