"""MainWindow shell: menus, tool/option toolbars, file I/O.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
from pathlib import Path

from PyQt5.QtCore import QMimeData, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QComboBox,
                             QColorDialog, QFileDialog, QLabel, QMainWindow,
                             QMenu, QMessageBox, QSpinBox, QToolBar,
                             QToolButton)

from . import APP_NAME, __version__, document, icons, svgio
from .canvas import (ARROW, BUCKET, CIRCLE, DIAMOND, ELLIPSE, HEXAGON, LINE,
                     PENCIL, PENTAGON, POINTER, RECT, ROUNDRECT, STAR, TEXT,
                     TRIANGLE, ImageItem, PaintScene, PaintView)
from .style import THEMES, apply_style, current_theme

ICON_SIZE = QSize(32, 32)

#: Custom clipboard MIME carrying serialised KhervePaint items.
MIME_ITEMS = "application/x-khervepaint-items"

#: (tool id, mdi icon, label, shortcut)
TOOLS = [
    (POINTER, "mdi.cursor-default-outline", "Pointer", "V"),
    (PENCIL, "mdi.pencil", "Pencil", "P"),
    (BUCKET, "mdi.format-color-fill", "Bucket fill", "B"),
    (LINE, "mdi.vector-line", "Line", "L"),
    (ARROW, "mdi.arrow-top-right", "Arrow", "A"),
    (RECT, "mdi.rectangle-outline", "Rectangle", "R"),
    (CIRCLE, "mdi.circle-outline", "Circle", "C"),
    (ELLIPSE, "mdi.ellipse-outline", "Ellipse", "E"),
    (TEXT, "mdi.format-text", "Text", "T"),
]

#: Extra shapes gathered under one dropdown: (tool id, mdi icon, label).
SHAPE_TOOLS = [
    (ROUNDRECT, "mdi.rounded-corner", "Rounded rectangle"),
    (TRIANGLE, "mdi.triangle-outline", "Triangle"),
    (DIAMOND, "mdi.rhombus-outline", "Diamond"),
    (PENTAGON, "mdi.pentagon-outline", "Pentagon"),
    (HEXAGON, "mdi.hexagon-outline", "Hexagon"),
    (STAR, "mdi.star-outline", "Star"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(icons.app_icon())
        self.resize(1200, 800)

        self.scene = PaintScene(800, 600)
        self.view = PaintView(self.scene)
        self.setCentralWidget(self.view)

        self._path = None
        self._dirty = False
        self.scene.changed_by_user.connect(self._mark_dirty)
        self.view.cursor_moved.connect(
            lambda p: self.statusBar().showMessage(
                f"x: {p.x():.0f}  y: {p.y():.0f}"))
        self.view.item_context.connect(self._show_item_menu)

        self._build_tool_bar()
        self._build_options_bar()
        self._build_menus()
        self.statusBar()
        self._update_title()

    # ------------------------------------------------------------ chrome
    def _build_tool_bar(self):
        bar = QToolBar("Tools")
        bar.setIconSize(ICON_SIZE)
        bar.setMovable(False)
        self.addToolBar(Qt.LeftToolBarArea, bar)
        self._tool_group = QActionGroup(self)
        for tool, glyph, label, shortcut in TOOLS:
            act = QAction(icons.icon(glyph), label, self)
            act.setCheckable(True)
            act.setShortcut(shortcut)
            act.setToolTip(f"{label} ({shortcut})")
            act.setData(tool)
            act.triggered.connect(
                lambda _, t=tool: self._set_tool(t))
            self._tool_group.addAction(act)
            bar.addAction(act)
        self._build_shapes_button(bar)
        self._tool_group.actions()[0].setChecked(True)

    def _build_shapes_button(self, bar: QToolBar):
        """A dropdown gathering the extra parametric shapes."""
        button = QToolButton()
        button.setPopupMode(QToolButton.MenuButtonPopup)
        button.setToolTip("More shapes")
        menu = QMenu(button)
        for tool, glyph, label in SHAPE_TOOLS:
            act = QAction(icons.icon(glyph), label, self)
            act.setCheckable(True)
            act.setData(tool)
            act.triggered.connect(
                lambda _, t=tool, g=glyph: self._pick_shape(t, g))
            self._tool_group.addAction(act)
            menu.addAction(act)
        button.setMenu(menu)
        first = SHAPE_TOOLS[0]
        button.setIcon(icons.icon(first[1]))
        button.clicked.connect(lambda: self._pick_shape(*self._last_shape))
        self._last_shape = (first[0], first[1])
        self._shapes_button = button
        bar.addWidget(button)

    def _pick_shape(self, tool: str, glyph: str):
        self._last_shape = (tool, glyph)
        self._shapes_button.setIcon(icons.icon(glyph))
        for act in self._tool_group.actions():
            act.setChecked(act.data() == tool)
        self._set_tool(tool)

    def _build_options_bar(self):
        bar = QToolBar("Options")
        bar.setIconSize(ICON_SIZE)
        bar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, bar)

        bar.addAction(icons.icon("mdi.file-outline"), "New",
                      self.new_document)
        bar.addAction(icons.icon("mdi.folder-open-outline"), "Open",
                      self.open_file)
        bar.addAction(icons.icon("mdi.content-save-outline"), "Save",
                      self.save_file)
        bar.addAction(icons.icon("mdi.export"), "Export PNG / PDF",
                      self.export_file)
        bar.addSeparator()

        self._stroke_btn = QToolButton()
        self._stroke_btn.setToolTip("Stroke colour")
        self._stroke_btn.clicked.connect(self.pick_stroke_color)
        bar.addWidget(self._stroke_btn)

        self._fill_btn = QToolButton()
        self._fill_btn.setToolTip("Fill colour")
        self._fill_btn.clicked.connect(self.pick_fill_color)
        bar.addWidget(self._fill_btn)

        self._fill_act = QAction(icons.icon("mdi.shape"),
                                 "Fill new shapes", self)
        self._fill_act.setCheckable(True)
        self._fill_act.setToolTip("Give newly drawn shapes a fill")
        self._fill_act.toggled.connect(self._set_fill_enabled)
        bar.addAction(self._fill_act)

        self._bucket_mode = QComboBox()
        self._bucket_mode.addItems(["Bucket: Raster", "Bucket: Vector"])
        self._bucket_mode.setToolTip(
            "Bucket fill output — paint into the raster layer, or create "
            "an editable vector path")
        self._bucket_mode.currentIndexChanged.connect(
            lambda i: setattr(self.scene, "bucket_vector", i == 1))
        bar.addWidget(self._bucket_mode)

        bar.addWidget(QLabel(" Width "))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(1, 60)
        self._width_spin.setValue(int(self.scene.pen.widthF()))
        self._width_spin.valueChanged.connect(self._set_pen_width)
        bar.addWidget(self._width_spin)
        bar.addSeparator()

        self._grid_act = QAction(icons.icon("mdi.grid"), "Grid", self)
        self._grid_act.setCheckable(True)
        self._grid_act.setChecked(self.scene.show_grid)
        self._grid_act.setToolTip("Show grid (Ctrl+')")
        self._grid_act.setShortcut("Ctrl+'")
        self._grid_act.toggled.connect(self._set_show_grid)
        bar.addAction(self._grid_act)

        self._snap_act = QAction(icons.icon("mdi.magnet"), "Snap", self)
        self._snap_act.setCheckable(True)
        self._snap_act.setChecked(self.scene.snap_enabled)
        self._snap_act.setToolTip("Snap to grid (Ctrl+Shift+')")
        self._snap_act.setShortcut("Ctrl+Shift+'")
        self._snap_act.toggled.connect(self._set_snap)
        bar.addAction(self._snap_act)

        bar.addWidget(QLabel(" Divisions "))
        self._grid_spin = QSpinBox()
        self._grid_spin.setRange(2, 200)
        self._grid_spin.setValue(self.scene.grid_divisions)
        self._grid_spin.setToolTip(
            "Grid divisions across the canvas — higher means more, "
            "finer cells")
        self._grid_spin.valueChanged.connect(self._set_grid_divisions)
        bar.addWidget(self._grid_spin)
        bar.addSeparator()

        bar.addAction(icons.icon("mdi.group"), "Group",
                      self.scene.group_selection)
        bar.addAction(icons.icon("mdi.ungroup"), "Ungroup",
                      self.scene.ungroup_selection)
        bar.addAction(icons.icon("mdi.delete-outline"), "Delete",
                      self.scene.delete_selection)

        self._refresh_color_buttons()

    def _build_menus(self):
        m = self.menuBar()

        file_menu = m.addMenu("&File")
        file_menu.addAction("&New", self.new_document, QKeySequence.New)
        file_menu.addAction("&Open...", self.open_file, QKeySequence.Open)
        file_menu.addAction("&Save", self.save_file, QKeySequence.Save)
        file_menu.addAction("Save &As...", self.save_file_as,
                            QKeySequence.SaveAs)
        file_menu.addSeparator()
        file_menu.addAction("&Export PNG / PDF...",
                            self.export_file, "Ctrl+E")
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, "Ctrl+Q")

        edit_menu = m.addMenu("&Edit")
        edit_menu.addAction("Cu&t", self.cut_selection, QKeySequence.Cut)
        edit_menu.addAction("&Copy", self.copy_selection, QKeySequence.Copy)
        edit_menu.addAction("&Paste", self.paste, QKeySequence.Paste)
        edit_menu.addAction("D&uplicate", self.duplicate_selection, "Ctrl+D")
        edit_menu.addSeparator()
        edit_menu.addAction("Select &All", self._select_all,
                            QKeySequence.SelectAll)
        edit_menu.addAction("&Delete", self.scene.delete_selection,
                            QKeySequence.Delete)
        edit_menu.addSeparator()
        edit_menu.addAction("&Group", self.scene.group_selection, "Ctrl+G")
        edit_menu.addAction("&Ungroup", self.scene.ungroup_selection,
                            "Ctrl+Shift+G")

        view_menu = m.addMenu("&View")
        view_menu.addAction(self._grid_act)
        view_menu.addAction(self._snap_act)
        view_menu.addSeparator()
        view_menu.addAction("Zoom &In", lambda: self.view.zoom(1.25),
                            QKeySequence.ZoomIn)
        view_menu.addAction("Zoom &Out", lambda: self.view.zoom(1 / 1.25),
                            QKeySequence.ZoomOut)
        view_menu.addAction("&Reset Zoom", self.view.zoom_reset, "Ctrl+0")
        view_menu.addSeparator()
        theme_menu = view_menu.addMenu("&Theme")
        theme_group = QActionGroup(self)
        for name in THEMES:
            act = QAction(name, self, checkable=True)
            act.setChecked(name == current_theme())
            act.triggered.connect(
                lambda _, n=name: apply_style(QApplication.instance(), n))
            theme_group.addAction(act)
            theme_menu.addAction(act)

        help_menu = m.addMenu("&Help")
        help_menu.addAction("&About", self._about)

    # ------------------------------------------------------------ state
    def _set_tool(self, tool: str):
        self.scene.tool = tool
        self.view.set_tool_cursor(tool)
        if tool != POINTER:
            self.scene.clear_handles()

    def _set_pen_width(self, width: int):
        self.scene.pen.setWidthF(width)

    def _set_fill_enabled(self, enabled: bool):
        self.scene.fill_enabled = enabled

    def _set_show_grid(self, show: bool):
        self.scene.show_grid = show
        self.view.viewport().update()

    def _set_snap(self, snap: bool):
        self.scene.snap_enabled = snap

    def _set_grid_divisions(self, divisions: int):
        self.scene.grid_divisions = divisions
        self.view.viewport().update()

    def _select_all(self):
        for item in self.scene.vector_items():
            item.setSelected(True)

    # ------------------------------------------------------------ clipboard
    def _selected_top_items(self):
        return [i for i in self.scene.selectedItems()
                if i.parentItem() is None]

    def copy_selection(self):
        items = self._selected_top_items()
        if not items:
            return
        payload = json.dumps([document.item_to_dict(i) for i in items])
        mime = QMimeData()
        mime.setData(MIME_ITEMS, payload.encode("utf-8"))
        QApplication.clipboard().setMimeData(mime)

    def cut_selection(self):
        self.copy_selection()
        if self._selected_top_items():
            self.scene.delete_selection()

    def duplicate_selection(self):
        items = self._selected_top_items()
        if not items:
            return
        dicts = [document.item_to_dict(i) for i in items]
        self._spawn_items(dicts, offset=20)

    def paste(self):
        mime = QApplication.clipboard().mimeData()
        if mime.hasFormat(MIME_ITEMS):
            dicts = json.loads(bytes(mime.data(MIME_ITEMS)).decode("utf-8"))
            self._spawn_items(dicts, offset=20)
        elif mime.hasImage():
            image = QApplication.clipboard().image()
            pixmap = QPixmap.fromImage(image)
            if pixmap.isNull():
                return
            item = ImageItem(pixmap)
            item.setPos(self._view_centre())
            self._place_new(item)

    def _spawn_items(self, dicts, offset: float):
        """Recreate serialised *dicts*, offset, select them as the paste."""
        self.scene.clearSelection()
        new_items = []
        for d in dicts:
            item = document.item_from_dict(d)
            item.moveBy(offset, offset)
            self.scene.addItem(item)
            item.setSelected(True)
            new_items.append(item)
        if new_items:
            self.scene.changed_by_user.emit()
        return new_items

    def _place_new(self, item):
        self.scene.clearSelection()
        self.scene.addItem(item)
        item.setSelected(True)
        self.scene.changed_by_user.emit()

    def _view_centre(self):
        return self.view.mapToScene(self.view.viewport().rect().center())

    # ------------------------------------------------------------ editing
    def _show_item_menu(self, item, global_pos):
        from .properties import build_context_menu
        build_context_menu(self, item).exec_(global_pos)

    def edit_item(self, item):
        from .properties import PropertiesDialog
        if PropertiesDialog(item, self).exec_():
            self.scene.changed_by_user.emit()

    def reorder_item(self, item, where: str):
        """Move *item* in front of / behind every other vector item."""
        others = [i for i in self.scene.vector_items() if i is not item]
        if not others:
            return
        zs = [i.zValue() for i in others]
        item.setZValue(max(zs) + 1 if where == "front" else min(zs) - 1)
        self.scene.changed_by_user.emit()

    def pick_stroke_color(self):
        color = QColorDialog.getColor(self.scene.pen.color(), self,
                                      "Stroke colour")
        if color.isValid():
            self.scene.pen.setColor(color)
            self._refresh_color_buttons()

    def pick_fill_color(self):
        color = QColorDialog.getColor(self.scene.fill_color, self,
                                      "Fill colour")
        if color.isValid():
            self.scene.fill_color = color
            self._fill_act.setChecked(True)
            self._refresh_color_buttons()

    def _refresh_color_buttons(self):
        for btn, color in ((self._stroke_btn, self.scene.pen.color()),
                           (self._fill_btn, self.scene.fill_color)):
            pixmap = QPixmap(22, 22)
            pixmap.fill(QColor(color))
            btn.setIcon(QIcon(pixmap))

    # ------------------------------------------------------------ files
    def new_document(self):
        if not self._confirm_discard():
            return
        self.scene.new_document(800, 600)
        self._path = None
        self._dirty = False
        self._update_title()

    def open_file(self):
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open", "",
            "All supported (*.svg *.kpaint *.png);;SVG image (*.svg);;"
            "KhervePaint document (*.kpaint);;PNG image (*.png)")
        if not path:
            return
        ext = Path(path).suffix.lower()
        try:
            if ext == ".png":
                document.open_png(self.scene, path)
                self._path = None          # PNG opens as a new document
            elif ext == ".svg":
                svgio.load_svg(self.scene, path)
                self._path = path
            else:
                document.load_kpaint(self.scene, path)
                self._path = path
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not open:\n{exc}")
            return
        self._sync_grid_controls()
        self._dirty = False
        self.view.zoom_reset()
        self._update_title()

    def save_file(self):
        if self._path is None:
            self.save_file_as()
            return
        try:
            if Path(self._path).suffix.lower() == ".kpaint":
                document.save_kpaint(self.scene, self._path)
            else:
                svgio.save_svg(self.scene, self._path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not save:\n{exc}")
            return
        self._dirty = False
        self._update_title()

    def save_file_as(self):
        path, chosen = QFileDialog.getSaveFileName(
            self, "Save As", "",
            "SVG image (*.svg);;KhervePaint document (*.kpaint)")
        if not path:
            return
        if Path(path).suffix.lower() not in (".svg", ".kpaint"):
            path += ".kpaint" if "kpaint" in chosen else ".svg"
        self._path = path
        self.save_file()

    def _sync_grid_controls(self):
        self._grid_act.setChecked(self.scene.show_grid)
        self._snap_act.setChecked(self.scene.snap_enabled)
        self._grid_spin.setValue(self.scene.grid_divisions)

    def export_file(self):
        # Flattened raster exports; editable SVG is handled by Save.
        exporters = {".png": document.export_png,
                     ".pdf": document.export_pdf}
        suggestion = str(Path(self._path).with_suffix(".png")) \
            if self._path else ""
        path, chosen = QFileDialog.getSaveFileName(
            self, "Export", suggestion,
            "PNG image (*.png);;PDF document (*.pdf)")
        if not path:
            return
        ext = Path(path).suffix.lower()
        if ext not in exporters:
            ext = ".pdf" if "pdf" in chosen else ".png"
            path += ext
        try:
            exporters[ext](self.scene, path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not export:\n{exc}")

    # ------------------------------------------------------------ misc
    def _mark_dirty(self):
        self._dirty = True
        self._update_title()

    def _update_title(self):
        name = Path(self._path).name if self._path else "Untitled"
        star = "*" if self._dirty else ""
        self.setWindowTitle(f"{star}{name} — {APP_NAME} v{__version__}")

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, APP_NAME, "Discard unsaved changes?",
            QMessageBox.Discard | QMessageBox.Cancel)
        return answer == QMessageBox.Discard

    def closeEvent(self, event):
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()

    def _about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<b>{APP_NAME}</b> v{__version__}<br>"
            "Hybrid raster + vector drawing app in the Kherve family."
            "<br><br>GPL-3.0 — Gwilherm Kerherve")
