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
from PyQt5.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog,
                             QDialogButtonBox, QDoubleSpinBox, QFontComboBox,
                             QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                             QLineEdit, QMenu, QPlainTextEdit, QSpinBox,
                             QToolButton, QVBoxLayout)

from . import gradient, icons
from .canvas import (ArcShapeItem, ArrowItem, DimensionItem, EllipseItem,
                     GroupItem, ImageItem, LabelMixin, LineItem, PathItem,
                     PolygonItem, RectItem, RoundedRectItem, TextItem,
                     center_origin)

#: Shapes whose outline can be exploded into edge segments.
_EXPLODABLE = (PolygonItem, RectItem, EllipseItem, RoundedRectItem,
               ArcShapeItem, PathItem)

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
        self.setMinimumWidth(560)
        layout = QVBoxLayout(self)

        # Sections register themselves in self._boxes; they are then
        # dealt across two side-by-side columns so the dialog stays
        # short instead of growing into one tall stack.
        self._boxes = []
        self._build_common(layout)
        if not isinstance(item, (TextItem, ImageItem, GroupItem)):
            self._build_stroke(layout)
        if isinstance(item, _HAS_FILL):
            self._build_fill(layout)
        self._build_geometry(layout)
        if isinstance(item, DimensionItem):
            self._build_dimension(layout)
        if isinstance(item, TextItem):
            self._build_text(layout)
        if isinstance(item, LabelMixin):
            self._build_label(layout)

        columns = QHBoxLayout()
        left, right = QVBoxLayout(), QVBoxLayout()
        columns.addLayout(left)
        columns.addLayout(right)
        layout.addLayout(columns)
        # Greedy balance: drop each section into whichever column is
        # currently the shorter (by summed row count).
        heights = [0, 0]
        for box, form in self._boxes:
            rows = max(form.rowCount(), 1)
            side = 0 if heights[0] <= heights[1] else 1
            (left if side == 0 else right).addWidget(box)
            heights[side] += rows
        left.addStretch(1)
        right.addStretch(1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Apply
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply_and_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(
            self._apply_live)
        layout.addWidget(buttons)

    # -------------------------------------------------------- sections
    def _section(self, parent_layout, title) -> QFormLayout:
        box = QGroupBox(title)
        form = QFormLayout(box)
        # Register for two-column placement; weight ~ number of rows so
        # the greedy balancer keeps the two columns roughly even.
        self._boxes.append((box, form))
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
        spec = gradient.brush_spec(brush)
        self.fill_on = QCheckBox("Fill")
        self.fill_on.setChecked(brush.style() != Qt.NoBrush)
        if spec is not None:
            start = QColor(spec["c1"])
            end = QColor(spec["c2"])
        else:
            start = brush.color() if brush.style() != Qt.NoBrush \
                else QColor("#4aa3ff")
            end = QColor("#ffffff")
        self.fill_style = QComboBox()
        self.fill_style.addItems(["Solid", "Linear gradient",
                                  "Radial gradient",
                                  "Sun (lit from top-left)"])
        self.fill_style.setCurrentIndex(
            gradient.FILL_STYLES.index(spec["kind"]) if spec else 0)
        self.fill_color = ColorButton(start)
        self.fill_color2 = ColorButton(end)
        self.fill_angle = _spin(spec["angle"] if spec else 90.0,
                                -360, 360, 1)
        for w in (self.fill_style.currentIndexChanged,
                  self.fill_color.changed, self.fill_color2.changed):
            w.connect(lambda *_: self.fill_on.setChecked(True))
        form.addRow(self.fill_on)
        form.addRow("Style", self.fill_style)
        form.addRow("Colour", self.fill_color)
        form.addRow("End colour", self.fill_color2)
        form.addRow("Angle °", self.fill_angle)

    def _build_geometry(self, layout):
        item = self.item
        if isinstance(item, LineItem):           # line + arrow
            form = self._section(layout, "Endpoints")
            ln = item.line()
            self.x1 = _spin(ln.x1()); self.y1 = _spin(ln.y1())
            self.x2 = _spin(ln.x2()); self.y2 = _spin(ln.y2())
            form.addRow("X1", self.x1); form.addRow("Y1", self.y1)
            form.addRow("X2", self.x2); form.addRow("Y2", self.y2)
            if not isinstance(item, DimensionItem):
                bend = item.bend()
                mid = (ln.p1() + ln.p2()) / 2
                self.curved = QCheckBox("Curved (bend through a control "
                                        "point)")
                self.curved.setChecked(bend is not None)
                ctrl = bend if bend is not None else mid
                self.bend_x = _spin(ctrl.x()); self.bend_y = _spin(ctrl.y())
                for w in (self.bend_x.valueChanged,
                          self.bend_y.valueChanged):
                    w.connect(lambda *_: self.curved.setChecked(True))
                form.addRow(self.curved)
                form.addRow("Bend X", self.bend_x)
                form.addRow("Bend Y", self.bend_y)
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

    def _build_dimension(self, layout):
        form = self._section(layout, "Dimension style")
        item = self.item
        self.dim_cap = QComboBox()
        self.dim_cap.addItems(["arrows", "ticks", "dots", "none"])
        self.dim_cap.setCurrentText(item.cap_style)
        self.dim_ext = QCheckBox("Extension (witness) lines")
        self.dim_ext.setChecked(item.extension)
        self.dim_dash = QCheckBox("Dashed line")
        self.dim_dash.setChecked(item.dash)
        self.dim_unit = QComboBox()
        self.dim_unit.addItems(["mm", "cm", "in"])
        self.dim_unit.setCurrentText(item.unit)
        self.dim_decimals = QSpinBox()
        self.dim_decimals.setRange(0, 4)
        self.dim_decimals.setValue(item.decimals)
        self.dim_prefix = QLineEdit(item.prefix)
        self.dim_prefix.setPlaceholderText("e.g. Ø, ±")
        self.dim_suffix = QLineEdit(item.suffix)
        form.addRow("End caps", self.dim_cap)
        form.addRow(self.dim_ext)
        form.addRow(self.dim_dash)
        form.addRow("Unit", self.dim_unit)
        form.addRow("Decimals", self.dim_decimals)
        form.addRow("Prefix", self.dim_prefix)
        form.addRow("Suffix", self.dim_suffix)

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

    def _build_label(self, layout):
        form = self._section(layout, "Label (text inside shape)")
        self.label_text = QPlainTextEdit(self.item.label())
        self.label_text.setFixedHeight(50)
        self.label_text.setPlaceholderText("Text shown centred in the shape")
        self.label_family = QFontComboBox()
        self.label_family.setCurrentFont(QFont(self.item._label_family))
        self.label_size = QSpinBox()
        self.label_size.setRange(4, 400)
        self.label_size.setValue(self.item._label_size)
        self.label_bold = QCheckBox("Bold")
        self.label_bold.setChecked(self.item._label_bold)
        self.label_italic = QCheckBox("Italic")
        self.label_italic.setChecked(self.item._label_italic)
        self.label_color = ColorButton(self.item.label_color())
        form.addRow("Text", self.label_text)
        form.addRow("Font", self.label_family)
        form.addRow("Size", self.label_size)
        form.addRow(self.label_bold)
        form.addRow(self.label_italic)
        form.addRow("Colour", self.label_color)

    # -------------------------------------------------------- apply
    def _apply_and_accept(self):
        self._apply()
        self.accept()

    def _apply_live(self):
        """Apply the current field values to the item now and push an
        undoable snapshot, leaving the dialog open so changes (text size,
        font, colour…) can be previewed live before OK."""
        self._apply()
        scene = self.item.scene()
        if scene is not None:
            scene.changed_by_user.emit()

    def _apply(self):
        item = self.item
        # Honour the exact coordinates typed here, bypassing grid snap.
        scene = item.scene()
        prev_snap = getattr(scene, "snap_enabled", False)
        if scene is not None:
            scene.snap_enabled = False
        item.setPos(self.x.value(), self.y.value())
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
            if self.fill_on.isChecked():
                style = gradient.FILL_STYLES[self.fill_style.currentIndex()]
                item.setBrush(gradient.brush_for(
                    style, self.fill_color.color(),
                    self.fill_color2.color(), self.fill_angle.value()))
            else:
                item.setBrush(QBrush(Qt.NoBrush))

        self._apply_geometry()
        if isinstance(item, DimensionItem):
            self._apply_dimension()
        if isinstance(item, TextItem):
            self._apply_text()
        if isinstance(item, LabelMixin):
            self._apply_label_fields()
        # Re-centre the rotation origin against the (possibly new)
        # geometry, then rotate — so it spins about its own centre.
        center_origin(item)
        item.setRotation(self.rotation.value())
        if scene is not None:
            scene.snap_enabled = prev_snap

    def _apply_geometry(self):
        from PyQt5.QtCore import QLineF, QRectF
        item = self.item
        if isinstance(item, LineItem):
            item.setLine(QLineF(self.x1.value(), self.y1.value(),
                                self.x2.value(), self.y2.value()))
            if hasattr(self, "curved"):
                from PyQt5.QtCore import QPointF
                item.set_bend(
                    QPointF(self.bend_x.value(), self.bend_y.value())
                    if self.curved.isChecked() else None)
            if item.isSelected():
                item.setSelected(False); item.setSelected(True)
        elif isinstance(item, RoundedRectItem):
            item.set_rect(QRectF(self.rx.value(), self.ry.value(),
                                 self.rw.value(), self.rh.value()))
            item.set_radius(self.radius.value())
        elif isinstance(item, (RectItem, EllipseItem)):
            item.setRect(QRectF(self.rx.value(), self.ry.value(),
                                self.rw.value(), self.rh.value()))

    def _apply_dimension(self):
        item = self.item
        item.cap_style = self.dim_cap.currentText()
        item.extension = self.dim_ext.isChecked()
        item.dash = self.dim_dash.isChecked()
        item.unit = self.dim_unit.currentText()
        item.decimals = self.dim_decimals.value()
        item.prefix = self.dim_prefix.text()
        item.suffix = self.dim_suffix.text()
        item.update()

    def _apply_text(self):
        item = self.item
        item.setPlainText(self.text.toPlainText())
        font = QFont(self.font_family.currentFont().family(),
                     self.font_size.value())
        font.setBold(self.bold.isChecked())
        font.setItalic(self.italic.isChecked())
        item.setFont(font)
        item.setDefaultTextColor(self.text_color.color())

    def _apply_label_fields(self):
        item = self.item
        item.set_label(self.label_text.toPlainText())
        font = QFont(self.label_family.currentFont().family(),
                     self.label_size.value())
        font.setBold(self.label_bold.isChecked())
        font.setItalic(self.label_italic.isChecked())
        item.set_label_font(font)
        item.set_label_color(self.label_color.color())


def stack_cells_dialog(window, item):
    """Ask for the ``a×b×c`` unit-cell repeats and rebuild *item* as that
    supercell (stacked unit cells). Prefilled from the item's current counts;
    1×1×1 restores the single cell."""
    cells = getattr(item, "mol_cells", None) or (1, 1, 1)
    dlg = QDialog(window)
    dlg.setWindowTitle("Stack unit cells")
    layout = QVBoxLayout(dlg)
    layout.addWidget(QLabel("Repeat the unit cell along each lattice vector:"))
    form = QFormLayout()
    spins = []
    for axis, val in zip(("a", "b", "c"), cells):
        sp = QSpinBox(dlg)
        sp.setRange(1, 30)
        sp.setValue(int(val))
        form.addRow(axis, sp)
        spins.append(sp)
    layout.addLayout(form)
    buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                               parent=dlg)
    buttons.accepted.connect(dlg.accept)
    buttons.rejected.connect(dlg.reject)
    layout.addWidget(buttons)
    if dlg.exec_() == QDialog.Accepted:
        window.scene.set_cells(item, *(s.value() for s in spins))


def build_context_menu(window, item) -> QMenu:
    """Right-click menu for *item*, wired to *window* (the MainWindow)."""
    menu = QMenu(window)
    menu.addAction(icons.icon("mdi.pencil-box-outline"), "Edit properties…",
                   lambda: window.edit_item(item))
    if getattr(item, "mol_name", None):        # molecule / crystal model
        menu.addAction(icons.icon("mdi.molecule"), "Molecule builder…",
                       lambda: window.view.open_molecule_builder(item))
        menu.addAction(icons.icon("mdi.rotate-3d-variant"), "Rotate in 3D",
                       lambda: window.scene.enter_orbit_mode(item))
        from . import molrepr, molecules
        show_as = menu.addMenu(icons.icon("mdi.eye-outline"), "Show as")
        for mode in molrepr.MODES:
            show_as.addAction(
                molrepr.MODE_LABELS[mode],
                lambda _=False, mo=mode: window.scene.set_representation(item, mo))
        if molecules.can_stack(item.mol_name):
            menu.addAction(icons.icon("mdi.cube-outline"), "Stack unit cells…",
                           lambda: stack_cells_dialog(window, item))
        from . import molcolor
        menu.addAction(icons.icon("mdi.palette-outline"), "Add colour legend",
                       lambda: molcolor.place_legend(window.scene, item))
    if isinstance(item, ImageItem):
        menu.addAction(icons.icon("mdi.crop"), "Crop image",
                       lambda: window.crop_image(item))
        menu.addAction(icons.icon("mdi.image-remove"), "Remove background",
                       lambda: window.remove_image_background(item))
    menu.addSeparator()
    menu.addAction(icons.icon("mdi.content-copy"), "Duplicate",
                   window.duplicate_selection)
    menu.addAction(icons.icon("mdi.delete-outline"), "Delete",
                   window.scene.delete_selection)
    menu.addSeparator()
    menu.addAction(icons.icon("mdi.flip-horizontal"), "Flip horizontal",
                   lambda: window.scene.mirror_selection(True))
    menu.addAction(icons.icon("mdi.flip-vertical"), "Flip vertical",
                   lambda: window.scene.mirror_selection(False))
    menu.addAction(icons.icon("mdi.arrange-bring-to-front"), "Bring to front",
                   lambda: window.reorder_item(item, "front"))
    menu.addAction(icons.icon("mdi.arrange-bring-forward"), "Bring forward",
                   lambda: window.reorder_item(item, "forward"))
    menu.addAction(icons.icon("mdi.arrange-send-backward"), "Send backward",
                   lambda: window.reorder_item(item, "backward"))
    menu.addAction(icons.icon("mdi.arrange-send-to-back"), "Send to back",
                   lambda: window.reorder_item(item, "back"))
    menu.addSeparator()
    if isinstance(item, GroupItem):
        menu.addAction(icons.icon("mdi.ungroup"), "Ungroup",
                       window.scene.ungroup_selection)
    else:
        menu.addAction(icons.icon("mdi.group"), "Group selection",
                       window.scene.group_selection)
    if isinstance(item, _EXPLODABLE):
        menu.addAction(icons.icon("mdi.arrow-expand-all"),
                       "Explode shape", window.scene.explode_selection)
    return menu
