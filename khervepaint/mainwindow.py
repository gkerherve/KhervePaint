"""MainWindow shell: menus, tool/option toolbars, file I/O.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
from pathlib import Path

from PyQt5.QtCore import QMimeData, QSettings, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QComboBox,
                             QColorDialog, QFileDialog, QLabel, QMainWindow,
                             QMessageBox, QSpinBox, QToolBar,
                             QToolButton, QUndoStack)

from . import APP_NAME, __version__, document, icons, svgio
from .undo import SnapshotCommand
from .canvas import (ARROW, ARROW_RIGHT, BUCKET, CHEVRON, CIRCLE, DIAMOND,
                     ELLIPSE, HALFCIRCLE, HEPTAGON, HEXAGON, HOUSE, LIGHTNING,
                     LINE, OCTAGON, PARALLELOGRAM, PENCIL, PENTAGON, PLUS,
                     POINTER, QUARTERCIRCLE, RECT, RIGHT_TRIANGLE, ROUNDRECT,
                     STAR, STAR6, TEXT, TRAPEZOID, TRIANGLE, ImageItem,
                     PaintScene, PaintView)
from .style import THEMES, apply_style, current_theme

ICON_SIZE = QSize(32, 32)
#: The left tool column holds many shapes, so its icons are smaller.
TOOL_ICON_SIZE = QSize(24, 24)

#: Custom clipboard MIME carrying serialised KhervePaint items.
MIME_ITEMS = "application/x-khervepaint-items"

#: QSettings scope (shared with the theme settings) and recent-files key.
SETTINGS = ("Kherve", "KhervePaint")
MAX_RECENT = 10

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

#: Extra shapes shown as their own tool buttons: (tool id, mdi icon, label).
SHAPE_TOOLS = [
    (ROUNDRECT, "mdi.rounded-corner", "Rounded rectangle"),
    (TRIANGLE, "mdi.triangle-outline", "Triangle"),
    (RIGHT_TRIANGLE, "mdi.vector-triangle", "Right triangle"),
    (DIAMOND, "mdi.rhombus-outline", "Diamond"),
    (PARALLELOGRAM, "mdi.vector-parallelogram", "Parallelogram"),
    (TRAPEZOID, "mdi.vector-polygon", "Trapezoid"),
    (PENTAGON, "mdi.pentagon-outline", "Pentagon"),
    (HEXAGON, "mdi.hexagon-outline", "Hexagon"),
    (HEPTAGON, "mdi.septagon-outline", "Heptagon"),
    (OCTAGON, "mdi.octagon-outline", "Octagon"),
    (STAR, "mdi.star-outline", "Star (5-point)"),
    (STAR6, "mdi.hexagram-outline", "Star (6-point)"),
    (PLUS, "mdi.plus", "Cross / plus"),
    (CHEVRON, "mdi.chevron-right", "Chevron"),
    (ARROW_RIGHT, "mdi.arrow-right-bold-outline", "Block arrow"),
    (LIGHTNING, "mdi.lightning-bolt-outline", "Lightning bolt"),
    (HOUSE, "mdi.home-outline", "House"),
    (HALFCIRCLE, "mdi.circle-half-full", "Half circle"),
    (QUARTERCIRCLE, "mdi.circle-slice-2", "Quarter circle"),
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
        self._undo_stack = QUndoStack(self)
        self._undo_stack.setUndoLimit(80)
        self._restoring = False
        self._snapshot = document.scene_to_dict(self.scene)
        self._undo_stack.cleanChanged.connect(lambda *_: self._update_title())

        self._undo_act = self._undo_stack.createUndoAction(self, "Undo")
        self._undo_act.setShortcut(QKeySequence.Undo)
        self._undo_act.setIcon(icons.icon("mdi.undo"))
        self._redo_act = self._undo_stack.createRedoAction(self, "Redo")
        self._redo_act.setShortcuts([QKeySequence.Redo, QKeySequence("Ctrl+Y")])
        self._redo_act.setIcon(icons.icon("mdi.redo"))

        self.scene.changed_by_user.connect(self._capture_change)
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
        bar.setIconSize(TOOL_ICON_SIZE)
        bar.setMovable(False)
        self.addToolBar(Qt.LeftToolBarArea, bar)
        self._tool_group = QActionGroup(self)
        for tool, glyph, label, shortcut in TOOLS:
            self._add_tool_action(bar, tool, glyph, label, shortcut)
        bar.addSeparator()
        for tool, glyph, label in SHAPE_TOOLS:
            self._add_tool_action(bar, tool, glyph, label, None)
        self._tool_group.actions()[0].setChecked(True)

    def _add_tool_action(self, bar, tool, glyph, label, shortcut):
        act = QAction(icons.icon(glyph), label, self)
        act.setCheckable(True)
        if shortcut:
            act.setShortcut(shortcut)
            act.setToolTip(f"{label} ({shortcut})")
        else:
            act.setToolTip(label)
        act.setData(tool)
        act.triggered.connect(lambda _, t=tool: self._set_tool(t))
        self._tool_group.addAction(act)
        bar.addAction(act)

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
        bar.addAction(self._undo_act)
        bar.addAction(self._redo_act)
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
        bar.addAction(icons.icon("mdi.arrow-expand-all"),
                      "Explode shape", self.scene.explode_selection)
        bar.addAction(icons.icon("mdi.flip-horizontal"), "Flip horizontal",
                      lambda: self.scene.mirror_selection(True))
        bar.addAction(icons.icon("mdi.flip-vertical"), "Flip vertical",
                      lambda: self.scene.mirror_selection(False))
        bar.addAction(icons.icon("mdi.delete-outline"), "Delete",
                      self.scene.delete_selection)

        self._refresh_color_buttons()

    def _build_menus(self):
        m = self.menuBar()

        file_menu = m.addMenu("&File")
        file_menu.addAction("&New", self.new_document, QKeySequence.New)
        file_menu.addAction("&Open...", self.open_file, QKeySequence.Open)
        self._recent_menu = file_menu.addMenu("Open &Recent")
        self._recent_menu.aboutToShow.connect(self._rebuild_recent_menu)
        file_menu.addAction("&Save", self.save_file, QKeySequence.Save)
        file_menu.addAction("Save &As...", self.save_file_as,
                            QKeySequence.SaveAs)
        file_menu.addSeparator()
        file_menu.addAction("&Drawing Size...", self.change_canvas_size,
                            "Ctrl+Shift+P")
        file_menu.addSeparator()
        file_menu.addAction("&Export PNG / PDF...",
                            self.export_file, "Ctrl+E")
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close, "Ctrl+Q")

        edit_menu = m.addMenu("&Edit")
        edit_menu.addAction(self._undo_act)
        edit_menu.addAction(self._redo_act)
        edit_menu.addSeparator()
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
        edit_menu.addAction("E&xplode shape", self.scene.explode_selection,
                            "Ctrl+Shift+E")
        edit_menu.addSeparator()
        edit_menu.addAction("Flip &Horizontal",
                            lambda: self.scene.mirror_selection(True),
                            "Ctrl+Shift+H")
        edit_menu.addAction("Flip &Vertical",
                            lambda: self.scene.mirror_selection(False),
                            "Ctrl+Shift+J")

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
        help_menu.addAction("&User Guide", self._user_guide, "F1")
        help_menu.addSeparator()
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

    def crop_image(self, item):
        self.scene.begin_crop(item)
        self.view.setFocus()
        self.statusBar().showMessage(
            "Crop: drag the handles, then Enter to apply or Esc to cancel")

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
        self._reset_history()
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
        self._load_document(path)

    def open_recent(self, path: str):
        if not Path(path).exists():
            self._remove_recent(path)
            QMessageBox.warning(self, APP_NAME, f"File not found:\n{path}")
            return
        if not self._confirm_discard():
            return
        self._load_document(path)

    def _load_document(self, path: str) -> bool:
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
            return False
        self._sync_grid_controls()
        self._reset_history()
        self.view.zoom_reset()
        self._update_title()
        self._add_recent(path)
        return True

    # ------------------------------------------------------------ recent
    def _recent_files(self):
        value = QSettings(*SETTINGS).value("recentFiles", [])
        if isinstance(value, str):
            value = [value]
        return [p for p in (value or []) if p]

    def _add_recent(self, path: str):
        path = str(path)
        files = [p for p in self._recent_files() if p != path]
        files.insert(0, path)
        del files[MAX_RECENT:]
        QSettings(*SETTINGS).setValue("recentFiles", files)

    def _remove_recent(self, path: str):
        files = [p for p in self._recent_files() if p != str(path)]
        QSettings(*SETTINGS).setValue("recentFiles", files)

    def _clear_recent(self):
        QSettings(*SETTINGS).setValue("recentFiles", [])

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        files = self._recent_files()
        if not files:
            empty = self._recent_menu.addAction("No recent files")
            empty.setEnabled(False)
            return
        for i, path in enumerate(files):
            act = self._recent_menu.addAction(f"&{i + 1}  {Path(path).name}")
            act.setToolTip(path)
            act.triggered.connect(
                lambda _=False, p=path: self.open_recent(p))
        self._recent_menu.addSeparator()
        self._recent_menu.addAction("Clear list", self._clear_recent)

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
        self._undo_stack.setClean()
        self._add_recent(self._path)
        self._update_title()

    def change_canvas_size(self):
        from .canvassize import CanvasSizeDialog
        rect = self.scene.sceneRect()
        has_sel = any(i.parentItem() is None
                      for i in self.scene.selectedItems())
        dlg = CanvasSizeDialog(
            self, current=(rect.width(), rect.height()),
            dpi=self.scene.dpi, has_selection=has_sel)
        if not dlg.exec_():
            return
        choice = dlg.result_value()
        if choice[0] == "fit":
            self.scene.fit_to_content(selection_only=choice[1])
        else:
            _, px_w, px_h, dpi = choice
            self.scene.dpi = dpi
            self.scene.resize_canvas(px_w, px_h)
        self.view.zoom_reset()

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

    # ------------------------------------------------------------ history
    def _capture_change(self):
        """Snapshot the document after a user change and push an undo
        command. Skipped while restoring (undo/redo) to avoid feedback."""
        if self._restoring:
            return
        after = document.scene_to_dict(self.scene)
        if after == self._snapshot:
            return
        self._undo_stack.push(SnapshotCommand(self, self._snapshot, after))
        self._snapshot = after

    def _restore_snapshot(self, state: dict):
        self._restoring = True
        document.dict_to_scene(state, self.scene)
        self._snapshot = state
        self._sync_grid_controls()
        self.scene.clear_handles()
        self.view.viewport().update()
        self._restoring = False

    def _reset_history(self):
        """Start a fresh history baseline (New / Open)."""
        self._snapshot = document.scene_to_dict(self.scene)
        self._undo_stack.clear()          # also marks the stack clean

    # ------------------------------------------------------------ misc
    def _update_title(self):
        name = Path(self._path).name if self._path else "Untitled"
        star = "" if self._undo_stack.isClean() else "*"
        self.setWindowTitle(f"{star}{name} — {APP_NAME} v{__version__}")

    def _confirm_discard(self) -> bool:
        if self._undo_stack.isClean():
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
        from . import help as help_dialogs
        help_dialogs.show_about(self)

    def _user_guide(self):
        from . import help as help_dialogs
        help_dialogs.show_user_guide(self)
