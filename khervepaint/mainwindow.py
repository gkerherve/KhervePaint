"""MainWindow shell: menus, tool/option toolbars, file I/O.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from pathlib import Path

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication,
                             QColorDialog, QFileDialog, QLabel, QMainWindow,
                             QMessageBox, QSpinBox, QToolBar, QToolButton)

from . import APP_NAME, __version__, document, icons
from .canvas import (CIRCLE, ELLIPSE, LINE, PENCIL, POINTER, RECT, TEXT,
                     PaintScene, PaintView)
from .style import THEMES, apply_style, current_theme

ICON_SIZE = QSize(32, 32)

#: (tool id, mdi icon, label, shortcut)
TOOLS = [
    (POINTER, "mdi.cursor-default-outline", "Pointer", "V"),
    (PENCIL, "mdi.pencil", "Pencil", "P"),
    (LINE, "mdi.vector-line", "Line", "L"),
    (RECT, "mdi.rectangle-outline", "Rectangle", "R"),
    (CIRCLE, "mdi.circle-outline", "Circle", "C"),
    (ELLIPSE, "mdi.ellipse-outline", "Ellipse", "E"),
    (TEXT, "mdi.format-text", "Text", "T"),
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
        self._tool_group.actions()[0].setChecked(True)

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
        bar.addAction(icons.icon("mdi.export"), "Export PNG / SVG / PDF",
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

        self._fill_act = QAction(icons.icon("mdi.format-color-fill"),
                                 "Fill shapes", self)
        self._fill_act.setCheckable(True)
        self._fill_act.toggled.connect(self._set_fill_enabled)
        bar.addAction(self._fill_act)

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

        bar.addWidget(QLabel(" Grid "))
        self._grid_spin = QSpinBox()
        self._grid_spin.setRange(2, 200)
        self._grid_spin.setValue(self.scene.grid_size)
        self._grid_spin.valueChanged.connect(self._set_grid_size)
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
        file_menu.addAction("&Export PNG / SVG / PDF...",
                            self.export_file, "Ctrl+E")
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, "Ctrl+Q")

        edit_menu = m.addMenu("&Edit")
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

    def _set_pen_width(self, width: int):
        self.scene.pen.setWidthF(width)

    def _set_fill_enabled(self, enabled: bool):
        self.scene.fill_enabled = enabled

    def _set_show_grid(self, show: bool):
        self.scene.show_grid = show
        self.view.viewport().update()

    def _set_snap(self, snap: bool):
        self.scene.snap_enabled = snap

    def _set_grid_size(self, size: int):
        self.scene.grid_size = size
        self.view.viewport().update()

    def _select_all(self):
        for item in self.scene.vector_items():
            item.setSelected(True)

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
            "All supported (*.kpaint *.png);;"
            "KhervePaint document (*.kpaint);;PNG image (*.png)")
        if not path:
            return
        try:
            if path.lower().endswith(".png"):
                document.open_png(self.scene, path)
                self._path = None          # PNG opens as a new document
            else:
                document.load_kpaint(self.scene, path)
                self._path = path
                self._grid_act.setChecked(self.scene.show_grid)
                self._snap_act.setChecked(self.scene.snap_enabled)
                self._grid_spin.setValue(self.scene.grid_size)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not open:\n{exc}")
            return
        self._dirty = False
        self.view.zoom_reset()
        self._update_title()

    def save_file(self):
        if self._path is None:
            self.save_file_as()
            return
        try:
            document.save_kpaint(self.scene, self._path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Could not save:\n{exc}")
            return
        self._dirty = False
        self._update_title()

    def save_file_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", "KhervePaint document (*.kpaint)")
        if not path:
            return
        if not path.lower().endswith(".kpaint"):
            path += ".kpaint"
        self._path = path
        self.save_file()

    def export_file(self):
        exporters = {".png": document.export_png,
                     ".svg": document.export_svg,
                     ".pdf": document.export_pdf}
        suggestion = str(Path(self._path).with_suffix(".png")) \
            if self._path else ""
        path, chosen = QFileDialog.getSaveFileName(
            self, "Export", suggestion,
            "PNG image (*.png);;SVG image (*.svg);;PDF document (*.pdf)")
        if not path:
            return
        ext = Path(path).suffix.lower()
        if ext not in exporters:
            ext = "." + chosen.split("*.")[-1].rstrip(")")
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
