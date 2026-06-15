"""MainWindow shell: menus, tool/option toolbars, file I/O.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
import math
from pathlib import Path

from PyQt5.QtCore import QMimeData, QRectF, QSettings, QSize, Qt, QUrl
from PyQt5.QtGui import QColor, QDesktopServices, QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QComboBox,
                             QColorDialog, QDoubleSpinBox, QFileDialog,
                             QInputDialog, QLabel, QMainWindow, QMenu,
                             QMessageBox, QSlider, QToolBar, QToolButton,
                             QUndoStack)

from . import APP_NAME, __version__, canvassize, document, icons, library, svgio
from .undo import SnapshotCommand
from .canvas import (ARROW, ARROW_RIGHT, BUCKET, CHEVRON, CIRCLE, DIAMOND,
                     DIMENSION, ELLIPSE, HALFCIRCLE, HEPTAGON, HEXAGON, HOUSE,
                     LIGHTNING, LINE, OCTAGON, PARALLELOGRAM, PENCIL, PENTAGON,
                     PLUS, POINTER, QUARTERCIRCLE, RECT, RIGHT_TRIANGLE,
                     ROUNDRECT, STAR, STAR6, TEXT, TRAPEZOID, TRIANGLE,
                     ImageItem, PaintScene, PaintView)
from .style import THEMES, apply_style, current_theme

ICON_SIZE = QSize(32, 32)
#: The left tool column holds many shapes, so its icons are smaller.
TOOL_ICON_SIZE = QSize(24, 24)

#: Custom clipboard MIME carrying serialised KhervePaint items.
MIME_ITEMS = "application/x-khervepaint-items"

#: Selectable stroke widths (px) shown as thin-to-thick line swatches.
LINE_WIDTHS = [1, 2, 3, 4, 6, 8, 12, 16, 24]

#: QSettings scope (shared with the theme settings) and recent-files key.
SETTINGS = ("Kherve", "KhervePaint")
MAX_RECENT = 10

#: Standalone tool buttons: (tool id, mdi icon, label, shortcut).
DIRECT_TOOLS = [
    (POINTER, "mdi.cursor-default-outline", "Pointer", "V"),
    (PENCIL, "mdi.pencil", "Pencil", "P"),
    (BUCKET, "mdi.format-color-fill", "Bucket fill", "B"),
    (LINE, "mdi.vector-line", "Line", "L"),
    (ARROW, "mdi.arrow-top-right", "Arrow", "A"),
    (DIMENSION, "mdi.ruler", "Dimension / measure", "M"),
]

#: Shapes grouped into dropdown buttons: (button tooltip, [(tool, icon,
#: label, shortcut), ...]). A None icon is drawn from the shape itself.
SHAPE_GROUPS = [
    ("Rectangles", [
        (RECT, "mdi.rectangle-outline", "Rectangle", "R"),
        (ROUNDRECT, "mdi.rounded-corner", "Rounded rectangle", None),
    ]),
    ("Ellipses & arcs", [
        (CIRCLE, "mdi.circle-outline", "Circle", "C"),
        (ELLIPSE, "mdi.ellipse-outline", "Ellipse", "E"),
        (HALFCIRCLE, "mdi.circle-half-full", "Half circle", None),
        (QUARTERCIRCLE, "mdi.circle-slice-2", "Quarter circle", None),
    ]),
    ("Polygons", [
        (TRIANGLE, "mdi.triangle-outline", "Triangle", None),
        (RIGHT_TRIANGLE, "mdi.vector-triangle", "Right triangle", None),
        (DIAMOND, "mdi.rhombus-outline", "Diamond", None),
        (PARALLELOGRAM, None, "Parallelogram", None),
        (TRAPEZOID, "mdi.vector-polygon", "Trapezoid", None),
        (PENTAGON, "mdi.pentagon-outline", "Pentagon", None),
        (HEXAGON, "mdi.hexagon-outline", "Hexagon", None),
        (HEPTAGON, None, "Heptagon", None),
        (OCTAGON, "mdi.octagon-outline", "Octagon", None),
    ]),
    ("Stars & symbols", [
        (STAR, "mdi.star-outline", "Star (5-point)", None),
        (STAR6, "mdi.hexagram-outline", "Star (6-point)", None),
        (PLUS, "mdi.plus", "Cross / plus", None),
        (CHEVRON, "mdi.chevron-right", "Chevron", None),
        (ARROW_RIGHT, "mdi.arrow-right-bold-outline", "Block arrow", None),
        (LIGHTNING, "mdi.lightning-bolt-outline", "Lightning bolt", None),
        (HOUSE, "mdi.home-outline", "House", None),
    ]),
]


class MainWindow(QMainWindow):
    #: Live top-level windows, so additional ones aren't garbage-collected.
    _windows = []

    def __init__(self):
        super().__init__()
        MainWindow._windows.append(self)
        self.setWindowIcon(icons.app_icon())
        self.resize(1200, 800)

        w, h, dpi = canvassize.default_size()
        self.scene = PaintScene(w, h)
        self.scene.dpi = dpi
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
        self._build_ai_dock()
        self._build_menus()
        self._build_status_zoom()
        self._update_title()

    # ------------------------------------------------------------ chrome
    def _build_tool_bar(self):
        bar = QToolBar("Tools")
        bar.setIconSize(TOOL_ICON_SIZE)
        bar.setMovable(False)
        self.addToolBar(Qt.LeftToolBarArea, bar)
        self._tool_group = QActionGroup(self)
        self._group_current = {}          # dropdown button -> active QAction
        for tool, glyph, label, shortcut in DIRECT_TOOLS:
            self._add_tool_action(bar, tool, icons.icon(glyph), label,
                                  shortcut)
        bar.addSeparator()
        for label, items in SHAPE_GROUPS:
            self._build_shape_dropdown(bar, label, items)
        bar.addSeparator()
        self._add_tool_action(bar, TEXT, icons.icon("mdi.format-text"),
                              "Text", "T")
        bar.addSeparator()
        self._build_objects_button(bar)
        self._tool_group.actions()[0].setChecked(True)

    def _add_tool_action(self, bar, tool, icon, label, shortcut):
        act = QAction(icon, label, self)
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

    def _tool_icon(self, tool, glyph):
        ic = icons.icon(glyph) if glyph else QIcon()
        if ic.isNull():               # no MDI glyph: draw the shape itself
            ic = icons.shape_icon(tool, size=TOOL_ICON_SIZE.width())
        return ic

    def _build_shape_dropdown(self, bar, tooltip, items):
        """A dropdown button grouping related shapes; the button shows the
        last-picked shape, the arrow opens the rest."""
        button = QToolButton()
        # Clicking the icon opens the shape list directly (no split arrow).
        button.setPopupMode(QToolButton.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.setToolTip(tooltip)
        menu = QMenu(button)
        first_act = None
        for tool, glyph, label, shortcut in items:
            act = QAction(self._tool_icon(tool, glyph), label, self)
            act.setCheckable(True)
            act.setData(tool)
            if shortcut:
                act.setShortcut(shortcut)
                act.setToolTip(f"{label} ({shortcut})")
                self.addAction(act)       # keep the shortcut active app-wide
            act.triggered.connect(
                lambda _, b=button, a=act: self._pick_grouped(b, a))
            self._tool_group.addAction(act)
            menu.addAction(act)
            first_act = first_act or act
        button.setMenu(menu)
        button.setIcon(first_act.icon())
        self._group_current[button] = first_act
        bar.addWidget(button)

    def _pick_grouped(self, button, act):
        self._group_current[button] = act
        button.setIcon(act.icon())
        act.setChecked(True)
        self._set_tool(act.data())

    # ------------------------------------------------------------ status zoom
    _ZOOM_STEPS = 1000              # slider resolution (log scale)

    def _build_status_zoom(self):
        """Zoom controls at the bottom-right of the status bar: a −/+
        pair, a log-scaled slider and a clickable percentage (reset)."""
        bar = self.statusBar()
        out_btn = QToolButton(); out_btn.setText("−"); out_btn.setAutoRaise(True)
        out_btn.setToolTip("Zoom out")
        out_btn.clicked.connect(lambda: self.view.zoom(1 / 1.25))

        self._zoom_slider = QSlider(Qt.Horizontal)
        self._zoom_slider.setRange(0, self._ZOOM_STEPS)
        self._zoom_slider.setFixedWidth(150)
        self._zoom_slider.setToolTip("Zoom")
        self._zoom_slider.valueChanged.connect(
            lambda v: self.view.set_zoom(self._slider_to_zoom(v)))

        in_btn = QToolButton(); in_btn.setText("+"); in_btn.setAutoRaise(True)
        in_btn.setToolTip("Zoom in")
        in_btn.clicked.connect(lambda: self.view.zoom(1.25))

        self._zoom_label = QToolButton(); self._zoom_label.setAutoRaise(True)
        self._zoom_label.setToolTip("Reset to 100%")
        self._zoom_label.setMinimumWidth(46)
        self._zoom_label.clicked.connect(self.view.zoom_reset)

        for w in (out_btn, self._zoom_slider, in_btn, self._zoom_label):
            bar.addPermanentWidget(w)
        self.view.zoom_changed.connect(self._sync_zoom_controls)
        self._sync_zoom_controls(self.view.current_zoom())

    def _slider_to_zoom(self, value: int) -> float:
        lo, hi = self.view.MIN_ZOOM, self.view.MAX_ZOOM
        return lo * (hi / lo) ** (value / self._ZOOM_STEPS)

    def _zoom_to_slider(self, zoom: float) -> int:
        lo, hi = self.view.MIN_ZOOM, self.view.MAX_ZOOM
        zoom = max(lo, min(hi, zoom))
        return round(self._ZOOM_STEPS * math.log(zoom / lo) / math.log(hi / lo))

    def _sync_zoom_controls(self, zoom: float):
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(self._zoom_to_slider(zoom))
        self._zoom_slider.blockSignals(False)
        self._zoom_label.setText(f"{round(zoom * 100)}%")

    def _build_objects_button(self, bar):
        """Dropdown for the reusable-object library: save the current
        selection as a named object, or insert a saved one. The list of
        objects is rebuilt from the folder each time it opens."""
        button = QToolButton()
        button.setPopupMode(QToolButton.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.setIcon(icons.icon("mdi.bookshelf"))
        button.setToolTip("Objects — save the selection or insert a "
                          "saved object")
        menu = QMenu(button)
        menu.aboutToShow.connect(lambda: self._rebuild_objects_menu(menu))
        button.setMenu(menu)
        bar.addWidget(button)

    def _rebuild_objects_menu(self, menu):
        menu.clear()
        menu.addAction(icons.icon("mdi.content-save-plus-outline"),
                       "Save selection as object…", self.save_object)
        menu.addAction(icons.icon("mdi.folder-open-outline"),
                       "Open objects folder", self.open_objects_folder)
        menu.addSeparator()
        objects = library.list_objects()
        if not objects:
            empty = menu.addAction("(no saved objects yet)")
            empty.setEnabled(False)
            return
        for name, path in objects:
            menu.addAction(name,
                           lambda _=False, p=path: self.insert_object(p))

    def _build_ai_dock(self):
        from .ai_assistant import AiDock
        self.ai_dock = AiDock(self.scene, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ai_dock)

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

        self._width_combo = QComboBox()
        self._width_combo.setIconSize(QSize(72, 16))
        self._width_combo.setToolTip("Line width — thin to thick")
        for w in LINE_WIDTHS:
            self._width_combo.addItem(f"{w} px", w)
        self._select_width(self.scene.pen.widthF())
        self._width_combo.currentIndexChanged.connect(self._on_width_changed)
        bar.addWidget(self._width_combo)
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

        self._infinite_act = QAction(
            icons.icon("mdi.infinity"), "Infinite paper", self)
        self._infinite_act.setCheckable(True)
        self._infinite_act.setChecked(self.scene.infinite)
        self._infinite_act.setToolTip(
            "Infinite paper — grid fills the view, no fixed page edge")
        self._infinite_act.toggled.connect(self._set_infinite)
        bar.addAction(self._infinite_act)

        bar.addWidget(QLabel(" Grid (mm) "))
        self._grid_spin = QDoubleSpinBox()
        self._grid_spin.setRange(0.1, 100.0)
        self._grid_spin.setDecimals(1)
        self._grid_spin.setSingleStep(0.5)
        self._grid_spin.setValue(self.scene.grid_mm)
        self._grid_spin.setToolTip(
            "Distance between grid lines in millimetres "
            "(smaller means finer cells)")
        self._grid_spin.valueChanged.connect(self._set_grid_mm)
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
        file_menu.addAction("New &Window", self.new_window, "Ctrl+Shift+N")
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
        edit_menu.addAction("Save Selection as &Object…", self.save_object)
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
        view_menu.addAction(self._infinite_act)
        view_menu.addSeparator()
        view_menu.addAction("Zoom &In", lambda: self.view.zoom(1.25),
                            QKeySequence.ZoomIn)
        view_menu.addAction("Zoom &Out", lambda: self.view.zoom(1 / 1.25),
                            QKeySequence.ZoomOut)
        view_menu.addAction("&Reset Zoom", self.view.zoom_reset, "Ctrl+0")
        view_menu.addSeparator()
        ai_action = self.ai_dock.toggleViewAction()
        ai_action.setText("AI &Chat")
        view_menu.addAction(ai_action)
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

        self._build_examples_menu(m)

        help_menu = m.addMenu("&Help")
        help_menu.addAction("&User Guide", self._user_guide, "F1")
        help_menu.addSeparator()
        help_menu.addAction("&About", self._about)

    def _build_examples_menu(self, menubar):
        """Examples ▸ <category> ▸ <technique>: labelled A4 schematics."""
        from . import examples
        menu = menubar.addMenu("E&xamples")
        submenus = {}
        for category, name, builder in examples.EXAMPLES:
            sub = submenus.get(category)
            if sub is None:
                sub = submenus[category] = menu.addMenu(category)
            sub.addAction(name, lambda _=False, b=builder, n=name:
                          self.load_example(b, n))

    def load_example(self, builder, name=""):
        """Replace the document with a built-in example sketch."""
        from . import examples
        from .ai_assistant import apply_specs
        if not self._confirm_discard():
            return
        self.scene.new_document(examples.PAGE_W, examples.PAGE_H)
        self.scene.dpi = examples.PAGE_DPI
        try:
            apply_specs(self.scene, builder())
        except Exception as exc:               # never leave a half doc
            QMessageBox.warning(self, APP_NAME,
                                f"Could not build example:\n{exc}")
        self.scene.clearSelection()
        self.scene.clear_handles()
        self._path = None
        self._sync_grid_controls()
        self._reset_history()
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self._update_title()

    # ------------------------------------------------------------ state
    def _set_tool(self, tool: str):
        self.scene.tool = tool
        self.view.set_tool_cursor(tool)
        if tool != POINTER:
            self.scene.clear_handles()

    def _on_width_changed(self, index: int):
        width = self._width_combo.itemData(index)
        if width is not None:
            self.scene.pen.setWidthF(float(width))

    def _select_width(self, width: float):
        """Select the listed width nearest to *width* without firing the
        change handler."""
        idx = min(range(len(LINE_WIDTHS)),
                  key=lambda i: abs(LINE_WIDTHS[i] - width))
        self._width_combo.blockSignals(True)
        self._width_combo.setCurrentIndex(idx)
        self._width_combo.blockSignals(False)

    def _refresh_width_icons(self):
        """Redraw the line-width swatches in the current stroke colour."""
        color = self.scene.pen.color().name()
        for i in range(self._width_combo.count()):
            w = self._width_combo.itemData(i)
            self._width_combo.setItemIcon(i, icons.line_width_icon(w, color))

    def _set_fill_enabled(self, enabled: bool):
        self.scene.fill_enabled = enabled

    def _set_show_grid(self, show: bool):
        self.scene.show_grid = show
        self.view.viewport().update()

    def _set_snap(self, snap: bool):
        self.scene.snap_enabled = snap

    def _set_grid_mm(self, mm: float):
        self.scene.grid_mm = mm
        self.view.viewport().update()

    def _set_infinite(self, on: bool):
        self.scene.infinite = on
        self.view.apply_scroll_bounds()
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

    # ------------------------------------------------------------ object library
    def save_object(self):
        """Save the current selection as a named SVG object in the
        library folder, ready to re-insert from the Objects dropdown."""
        items = self._selected_top_items()
        if not items:
            QMessageBox.information(
                self, APP_NAME,
                "Select one or more items first, then save them as an "
                "object.")
            return
        name, ok = QInputDialog.getText(self, "Save object", "Object name:")
        if not ok or not name.strip():
            return
        dicts = [document.item_to_dict(i) for i in items]
        try:
            path = library.save_object(dicts, name,
                                       dpi=getattr(self.scene, "dpi", 96))
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME,
                                f"Could not save object:\n{exc}")
            return
        self.statusBar().showMessage(f"Saved object “{path.stem}”")

    def insert_object(self, path):
        """Insert a saved object as fresh, editable items, centred on the
        current view and selected as one paste-like gesture (undoable)."""
        try:
            dicts = library.load_object(path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME,
                                f"Could not load object:\n{exc}")
            return
        if not dicts:
            return
        self.scene.clearSelection()
        new_items = []
        for d in dicts:
            item = document.item_from_dict(d)
            self.scene.addItem(item)
            item.setSelected(True)
            new_items.append(item)
        rect = QRectF()
        for it in new_items:
            rect = rect.united(it.sceneBoundingRect())
        target = self._view_centre()
        dx, dy = target.x() - rect.center().x(), target.y() - rect.center().y()
        for it in new_items:
            it.moveBy(dx, dy)
        self.scene.changed_by_user.emit()

    def open_objects_folder(self):
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(library.objects_dir())))

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
            "Crop: drag the handles, then double-click (or Enter) to apply "
            "— Esc to cancel")

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
        self._refresh_width_icons()      # swatches follow the stroke colour

    # ------------------------------------------------------------ files
    def new_document(self):
        if not self._confirm_discard():
            return
        w, h, dpi = canvassize.default_size()
        self.scene.new_document(w, h)
        self.scene.dpi = dpi
        self._path = None
        self._reset_history()
        self._update_title()

    def new_window(self):
        """Open a second, independent KhervePaint window (own document)."""
        win = MainWindow()
        win.move(self.x() + 40, self.y() + 40)
        win.show()
        win.raise_()
        win.activateWindow()
        return win

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
        rect = self.scene.sceneRect()
        has_sel = any(i.parentItem() is None
                      for i in self.scene.selectedItems())
        dlg = canvassize.CanvasSizeDialog(
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
        self._infinite_act.setChecked(self.scene.infinite)
        self._grid_spin.setValue(self.scene.grid_mm)
        self.view.apply_scroll_bounds()

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
            if self in MainWindow._windows:
                MainWindow._windows.remove(self)
            event.accept()
        else:
            event.ignore()

    def _about(self):
        from . import help as help_dialogs
        help_dialogs.show_about(self)

    def _user_guide(self):
        from . import help as help_dialogs
        help_dialogs.show_user_guide(self)
