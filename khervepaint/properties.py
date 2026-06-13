"""Per-item properties editor and the right-click context menu.

`PropertiesDialog` introspects the selected item and exposes
everything editable about it: position, rotation, opacity, stroke,
fill, the type-specific geometry, and (for text) the content and font.
`build_context_menu` assembles the right-click menu, wiring the
edit/duplicate/delete/order/group actions back to the main window.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QIcon, QPen, QPixmap
from PyQt5.QtWidgets import (QCheckBox, QColorDialog, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QFontComboBox,
                             QFormLayout, QGroupBox, QLabel, QMenu,
                             QPlainTextEdit, QSpinBox, QToolButton,
                             QVBoxLayout)

from . import icons
from .canvas import (ArrowItem, EllipseItem, GroupItem, ImageItem, LineItem,
                     PathItem, PolygonItem, RectItem, RoundedRectItem,
                     TextItem)

_HAS_FILL = (RectItem, EllipseItem, RoundedRectItem, PolygonItem, PathItem)


class ColorButton(QToolButton):
    """A swatch button that opens a colour picker (alpha enabled)."""

    changed = pyqtSignal()

    def __init__(self, color: QColor, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedSize(48, 24)
        self.clicked.connect(self._pick)
        self._refresh()

    def color(self) -> QColor:
        return QColor(self._color)

    def set_color(self, color: QColor):
        self._color = QColor(color)
        self._refresh()

    def _pick(self):
        c = QColorDialog.getColor(self._color, self, "Choose colour",
                                  QColorDialog.ShowAlphaChannel)
        if c.isValid():
            self.set_color(c)
            self.changed.emit()

    def _refresh(self):
        pm = QPixmap(40, 18)
        pm.fill(self._color)
        self.setIcon(QIcon(pm))


def _spin(value, lo=-100000.0, hi=100000.0, step=1.0, decimals=1):
    box = QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setSingleStep(step)
    box.setDecimals(decimals)
    box.setValue(value)
    return box


class PropertiesDialog(QDialog):
    """Edit every property of a single item; applies on OK."""

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Item properties")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)

        self._build_common(layout)
        if not isinstance(item, (TextItem, ImageItem, GroupItem)):
            self._build_stroke(layout)
        if isinstance(item, _HAS_FILL):
            self._build_fill(layout)
        self._build_geometry(layout)
        if isinstance(item, TextItem):
            self._build_text(layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # -------------------------------------------------------- sections
    def _section(self, parent_layout, title) -> QFormLayout:
        box = QGroupBox(title)
        form = QFormLayout(box)
        parent_layout.addWidget(box)
        return form

    def _build_common(self, layout):
        form = self._section(layout, "Transform")
        self.x = _spin(self.item.pos().x())
        self.y = _spin(self.item.pos().y())
        self.rotation = _spin(self.item.rotation(), -360, 360, 1)
        self.opacity = QSpinBox()
        self.opacity.setRange(0, 100)
        self.opacity.setValue(round(self.item.opacity() * 100))
        self.opacity.setSuffix(" %")
        form.addRow("X", self.x)
        form.addRow("Y", self.y)
        form.addRow("Rotation", self.rotation)
        form.addRow("Opacity", self.opacity)

    def _build_stroke(self, layout):
        form = self._section(layout, "Stroke")
        pen = self.item.pen()
        self.stroke_on = QCheckBox("Stroke")
        self.stroke_on.setChecked(pen.style() != Qt.NoPen)
        self.stroke_color = ColorButton(pen.color())
        self.stroke_width = _spin(max(pen.widthF(), 0), 0, 500, 1)
        form.addRow(self.stroke_on)
        form.addRow("Colour", self.stroke_color)
        form.addRow("Width", self.stroke_width)

    def _build_fill(self, layout):
        form = self._section(layout, "Fill")
        brush = self.item.brush()
        self.fill_on = QCheckBox("Fill")
        self.fill_on.setChecked(brush.style() != Qt.NoBrush)
        start = brush.color() if brush.style() != Qt.NoBrush \
            else QColor("#4aa3ff")
        self.fill_color = ColorButton(start)
        self.fill_color.changed.connect(
            lambda: self.fill_on.setChecked(True))
        form.addRow(self.fill_on)
        form.addRow("Colour", self.fill_color)

    def _build_geometry(self, layout):
        item = self.item
        if isinstance(item, LineItem):           # line + arrow
            form = self._section(layout, "Endpoints")
            ln = item.line()
            self.x1 = _spin(ln.x1()); self.y1 = _spin(ln.y1())
            self.x2 = _spin(ln.x2()); self.y2 = _spin(ln.y2())
            form.addRow("X1", self.x1); form.addRow("Y1", self.y1)
            form.addRow("X2", self.x2); form.addRow("Y2", self.y2)
        elif isinstance(item, (RectItem, EllipseItem, RoundedRectItem)):
            form = self._section(layout, "Geometry")
            r = item.rect()
            self.rx = _spin(r.x()); self.ry = _spin(r.y())
            self.rw = _spin(r.width(), 0); self.rh = _spin(r.height(), 0)
            form.addRow("X", self.rx); form.addRow("Y", self.ry)
            form.addRow("Width", self.rw); form.addRow("Height", self.rh)
            if isinstance(item, RoundedRectItem):
                self.radius = _spin(item.radius(), 0, 1000, 1)
                form.addRow("Corner radius", self.radius)
        elif isinstance(item, PolygonItem):
            form = self._section(layout, "Geometry")
            form.addRow(QLabel(f"{item.polygon().count()} vertices "
                               f"({item.kind})"))

    def _build_text(self, layout):
        form = self._section(layout, "Text")
        self.text = QPlainTextEdit(self.item.toPlainText())
        self.text.setFixedHeight(60)
        self.font_family = QFontComboBox()
        self.font_family.setCurrentFont(QFont(self.item.font().family()))
        self.font_size = QSpinBox()
        self.font_size.setRange(4, 400)
        self.font_size.setValue(max(self.item.font().pointSize(), 4))
        self.bold = QCheckBox("Bold")
        self.bold.setChecked(self.item.font().bold())
        self.italic = QCheckBox("Italic")
        self.italic.setChecked(self.item.font().italic())
        self.text_color = ColorButton(self.item.defaultTextColor())
        form.addRow("Content", self.text)
        form.addRow("Font", self.font_family)
        form.addRow("Size", self.font_size)
        form.addRow(self.bold)
        form.addRow(self.italic)
        form.addRow("Colour", self.text_color)

    # -------------------------------------------------------- apply
    def _apply_and_accept(self):
        item = self.item
        # Honour the exact coordinates typed here, bypassing grid snap.
        scene = item.scene()
        prev_snap = getattr(scene, "snap_enabled", False)
        if scene is not None:
            scene.snap_enabled = False
        item.setPos(self.x.value(), self.y.value())
        item.setRotation(self.rotation.value())
        item.setOpacity(self.opacity.value() / 100)

        if hasattr(self, "stroke_on"):
            if self.stroke_on.isChecked():
                pen = QPen(self.stroke_color.color(),
                           self.stroke_width.value())
                pen.setCapStyle(Qt.RoundCap)
                pen.setJoinStyle(Qt.RoundJoin)
            else:
                pen = QPen(Qt.NoPen)
            item.setPen(pen)

        if hasattr(self, "fill_on"):
            item.setBrush(QBrush(self.fill_color.color())
                          if self.fill_on.isChecked()
                          else QBrush(Qt.NoBrush))

        self._apply_geometry()
        if isinstance(item, TextItem):
            self._apply_text()
        if scene is not None:
            scene.snap_enabled = prev_snap
        self.accept()

    def _apply_geometry(self):
        from PyQt5.QtCore import QLineF, QRectF
        item = self.item
        if isinstance(item, LineItem):
            item.setLine(QLineF(self.x1.value(), self.y1.value(),
                                self.x2.value(), self.y2.value()))
            if item.isSelected():
                item.setSelected(False); item.setSelected(True)
        elif isinstance(item, RoundedRectItem):
            item.set_rect(QRectF(self.rx.value(), self.ry.value(),
                                 self.rw.value(), self.rh.value()))
            item.set_radius(self.radius.value())
        elif isinstance(item, (RectItem, EllipseItem)):
            item.setRect(QRectF(self.rx.value(), self.ry.value(),
                                self.rw.value(), self.rh.value()))

    def _apply_text(self):
        item = self.item
        item.setPlainText(self.text.toPlainText())
        font = QFont(self.font_family.currentFont().family(),
                     self.font_size.value())
        font.setBold(self.bold.isChecked())
        font.setItalic(self.italic.isChecked())
        item.setFont(font)
        item.setDefaultTextColor(self.text_color.color())


def build_context_menu(window, item) -> QMenu:
    """Right-click menu for *item*, wired to *window* (the MainWindow)."""
    menu = QMenu(window)
    menu.addAction(icons.icon("mdi.pencil-box-outline"), "Edit properties…",
                   lambda: window.edit_item(item))
    menu.addSeparator()
    menu.addAction(icons.icon("mdi.content-copy"), "Duplicate",
                   window.duplicate_selection)
    menu.addAction(icons.icon("mdi.delete-outline"), "Delete",
                   window.scene.delete_selection)
    menu.addSeparator()
    menu.addAction(icons.icon("mdi.arrange-bring-to-front"), "Bring to front",
                   lambda: window.reorder_item(item, "front"))
    menu.addAction(icons.icon("mdi.arrange-send-to-back"), "Send to back",
                   lambda: window.reorder_item(item, "back"))
    menu.addSeparator()
    if isinstance(item, GroupItem):
        menu.addAction(icons.icon("mdi.ungroup"), "Ungroup",
                       window.scene.ungroup_selection)
    else:
        menu.addAction(icons.icon("mdi.group"), "Group selection",
                       window.scene.group_selection)
    return menu
