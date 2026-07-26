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

from PyQt5.QtCore import (QMimeData, QPointF, QRectF, QSettings, QSize, Qt,
                          QUrl)
from PyQt5.QtGui import (QColor, QDesktopServices, QIcon, QImage, QKeySequence,
                         QPixmap)
from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QComboBox,
                             QColorDialog, QDoubleSpinBox, QFileDialog,
                             QInputDialog, QLabel, QMainWindow, QMenu,
                             QMessageBox, QSlider, QToolBar, QToolButton,
                             QUndoStack)

from . import APP_NAME, __version__, canvassize, document, icons, library, svgio
from .undo import SnapshotCommand
from .canvas import (ARROW, ARROW_RIGHT, BUCKET, ERASER, PICKER, PROTRACTOR,
                     CHEM_ATOM,
                     CHEM_BENZENE,
                     CHEM_CYCLOHEXANE, CHEM_CYCLOPENTANE, CHEM_DOUBLE,
                     CHEM_CHAIN, CHEM_HASH, CHEM_HBOND, CHEM_SINGLE,
                     CHEM_TRIPLE, CHEM_WEDGE, CHEVRON,
                     CIRCLE, DIAMOND, DIMENSION, ELLIPSE, HALFCIRCLE, HEPTAGON,
                     HEXAGON, HOUSE, LIGHTNING, LINE, OCTAGON, PARALLELOGRAM,
                     PENCIL, PENTAGON, PLUS, POINTER, QUARTERCIRCLE, RECT,
                     ELEC_PLACE, PLAN_PLACE, OPTICS_PLACE, VACUUM_PLACE,
                     LABWARE_PLACE, FLOW_PLACE, NET_PLACE, PID_PLACE,
                     ARROW_PLACE, BIO_PLACE, MATH_PLACE, MOL_PLACE, S3D_PLACE,
                     RIGHT_TRIANGLE, ROUNDRECT, STAR,
                     ROOM, STAR6, TEXT, TRAPEZOID, TRIANGLE, ImageItem,
                     LineItem, PaintScene, PaintView)
from . import (chemistry, crystals, electrical, floorplan, flowchart, labware,
               optics, vacuum, network, pid, arrows, biology, maths, molecules,
               scheme3d)
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
    (ERASER, "mdi.eraser", "Eraser (raster)", "X"),
    (PICKER, "mdi.eyedropper-variant",
     "Colour picker — click: stroke, Shift+click: fill", "K"),
    (BUCKET, "mdi.format-color-fill", "Bucket fill", "B"),
    (LINE, "mdi.vector-line", "Line", "L"),
    (ARROW, "mdi.arrow-top-right", "Arrow", "A"),
]

#: Chemistry tools shared by the toolbar dropdown and the context menu.
CHEM_BOND_TOOLS = [
    (CHEM_SINGLE, "Single bond"),
    (CHEM_CHAIN, "Chain (connected bonds)"),
    (CHEM_DOUBLE, "Double bond"),
    (CHEM_TRIPLE, "Triple bond"),
    (CHEM_WEDGE, "Wedge (up)"),
    (CHEM_HASH, "Hash (down)"),
    (CHEM_HBOND, "Hydrogen bond (dashed)"),
]
CHEM_RING_TOOLS = [
    (CHEM_BENZENE, "Benzene (aromatic)"),
    (CHEM_CYCLOHEXANE, "Cyclohexane"),
    (CHEM_CYCLOPENTANE, "Cyclopentane"),
]

#: Ruler dropdown: orientation choices and end-cap style choices, each
#: (key, label). Picking any activates the dimension tool.
DIM_ORIENTATIONS = [("aligned", "Aligned (free angle)"),
                    ("horizontal", "Horizontal (Δx)"),
                    ("vertical", "Vertical (Δy)")]
DIM_CAPS = [("arrows", "Arrows"), ("ticks", "Ticks"),
            ("dots", "Dots"), ("none", "Plain")]

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

#: Symbol-palette libraries, in toolbar order: (menu title, mdi glyph,
#: toolbar tooltip, spec module, scene attribute holding the armed
#: element name, placement tool). Drives both the left-toolbar dropdowns
#: and the Library menu, so the two never drift apart.
SYMBOL_LIBRARIES = [
    ("Molecules", "mdi.molecule",
     "Molecules — 3D ball-and-stick models",
     molecules, "mol_element", MOL_PLACE),
    ("Crystals", "mdi.cube-outline",
     "Crystals — unit cells & lattice systems (stackable, tiltable)",
     crystals, "mol_element", MOL_PLACE),
    ("3D scheme", "mdi.layers-triple-outline",
     "3D scheme — slabs, particle beds, glows (device schematics)",
     scheme3d, "s3d_element", S3D_PLACE),
    ("Room layout", "mdi.floor-plan",
     "Room layout — walls, doors, furniture (top view)",
     floorplan, "plan_element", PLAN_PLACE),
    ("Electrical", "mdi.flash",
     "Electrical — circuit & installation symbols",
     electrical, "elec_element", ELEC_PLACE),
    ("Optics", "mdi.flare",
     "Optics — lasers, mirrors, lenses (beam-path diagrams)",
     optics, "optics_element", OPTICS_PLACE),
    ("Vacuum", "mdi.gauge",
     "Vacuum — UHV chambers, pumps, valves (surface science)",
     vacuum, "vacuum_element", VACUUM_PLACE),
    ("Lab glassware", "mdi.flask-outline",
     "Lab glassware — beakers, flasks, apparatus",
     labware, "labware_element", LABWARE_PLACE),
    ("Flowchart", "mdi.sitemap",
     "Flowchart — process, decision, connector nodes",
     flowchart, "flow_element", FLOW_PLACE),
    ("Network / IT", "mdi.lan",
     "Network / IT — servers, devices, cloud",
     network, "net_element", NET_PLACE),
    ("P&&ID", "mdi.factory",
     "P&ID — tanks, pumps, valves, instruments (process flow)",
     pid, "pid_element", PID_PLACE),
    ("Arrows && callouts", "mdi.arrow-top-right",
     "Arrows & callouts — block arrows, callouts, banners",
     arrows, "arrow_element", ARROW_PLACE),
    ("Biology", "mdi.dna",
     "Biology — cells, molecules, lab",
     biology, "bio_element", BIO_PLACE),
    ("Math", "mdi.function-variant",
     "Math — axes, vectors, graphs & symbols",
     maths, "math_element", MATH_PLACE),
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
        self.view.cursor_moved.connect(self._update_size_readout)
        self.scene.selectionChanged.connect(self._update_size_readout)
        self.view.item_context.connect(self._show_item_menu)
        self.view.canvas_context.connect(self._show_canvas_menu)
        self.view.content_dropped.connect(self._on_drop)
        self.scene.color_picked.connect(self._on_color_picked)

        self._build_tool_bar()
        self._build_ai_dock()           # before the options bar (toggle button)
        self._build_options_bar()
        self._build_menus()
        self._build_status_zoom()
        self.view.apply_scroll_bounds()     # honour infinite-paper default
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
        self._build_dimension_dropdown(bar)
        bar.addSeparator()
        for label, items in SHAPE_GROUPS:
            self._build_shape_dropdown(bar, label, items)
        bar.addSeparator()
        self._add_tool_action(bar, TEXT, icons.icon("mdi.format-text"),
                              "Text", "T")
        self._build_chemistry_dropdown(bar)
        for _title, glyph, tip, module, attr, tool in SYMBOL_LIBRARIES:
            self._build_symbol_dropdown(bar, glyph, tip, module,
                                        self._library_picker(attr, tool),
                                        extra=self._library_extra(module))
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
        # live size of the shape being drawn / resized / selected, in mm
        self._size_label = QLabel("")
        self._size_label.setToolTip("Size of the current shape (mm)")
        bar.addPermanentWidget(self._size_label)
        # last eyedropper pick (permanent: the cursor-position message
        # repaints on every mouse move, so a temporary message would vanish)
        self._pick_label = QLabel("")
        bar.addPermanentWidget(self._pick_label)
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

    def _build_dimension_dropdown(self, bar):
        """The ruler/dimension tool as a dropdown: pick an orientation
        (aligned / horizontal / vertical) and an end-cap style; either
        choice activates the dimension tool. M also activates it."""
        button = QToolButton()
        button.setPopupMode(QToolButton.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.setIcon(icons.icon("mdi.ruler"))
        button.setToolTip("Dimension / measure (M) — orientation & style")
        menu = QMenu(button)

        menu.addSection("Orientation")
        self._dim_orient_group = QActionGroup(self)
        for key, label in DIM_ORIENTATIONS:
            act = QAction(label, self, checkable=True)
            act.setChecked(key == self.scene.dim_orientation)
            act.triggered.connect(lambda _, k=key: self._set_dim_orientation(k))
            self._dim_orient_group.addAction(act)
            menu.addAction(act)

        menu.addSection("End caps")
        self._dim_cap_group = QActionGroup(self)
        for key, label in DIM_CAPS:
            act = QAction(label, self, checkable=True)
            act.setChecked(key == self.scene.dim_cap)
            act.triggered.connect(lambda _, k=key: self._set_dim_cap(k))
            self._dim_cap_group.addAction(act)
            menu.addAction(act)

        button.setMenu(menu)
        bar.addWidget(button)
        shortcut = QAction(self)
        shortcut.setShortcut("M")
        shortcut.triggered.connect(self._activate_dimension)
        self.addAction(shortcut)

    def _activate_dimension(self):
        # Dimension isn't a checkable tool-group button, so clear whatever
        # tool button is currently lit before switching to it.
        checked = self._tool_group.checkedAction()
        if checked is not None:
            self._tool_group.setExclusive(False)
            checked.setChecked(False)
            self._tool_group.setExclusive(True)
        self._set_tool(DIMENSION)

    def _set_dim_orientation(self, key):
        self.scene.dim_orientation = key
        self._activate_dimension()

    def _set_dim_cap(self, key):
        self.scene.dim_cap = key
        self._activate_dimension()

    # ------------------------------------------------------------ chemistry
    def _build_chemistry_dropdown(self, bar):
        """Dropdown of chemistry tools: bonds, stereo bonds, rings and an
        atom-label sub-menu. Bonds/rings are checkable tools; an atom pick
        sets the label and activates the atom tool."""
        button = QToolButton()
        button.setPopupMode(QToolButton.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.setIcon(icons.icon("mdi.molecule"))
        button.setToolTip("Chemistry — bonds, rings, atoms")
        menu = QMenu(button)
        self._populate_chemistry_menu(menu)
        button.setMenu(menu)
        bar.addWidget(button)

    def _populate_chemistry_menu(self, menu):
        """Fill *menu* with the chemistry tools (shared between the left
        toolbar dropdown and the Library menu)."""
        menu.addSection("Bonds")
        for tool, label in CHEM_BOND_TOOLS:
            self._add_grouped_tool(menu, tool, label)
        menu.addSection("Rings")
        for tool, label in CHEM_RING_TOOLS:
            self._add_grouped_tool(menu, tool, label)
        atoms = menu.addMenu("Atom / group label")
        for sym in chemistry.ATOMS:
            atoms.addAction(sym, lambda _=False, s=sym: self._set_chem_atom(s))

    def _add_grouped_tool(self, menu, tool, label):
        """A checkable tool action in the shared tool group (so it lights up
        when active) added to *menu*."""
        act = QAction(label, self, checkable=True)
        act.setData(tool)
        act.triggered.connect(lambda _, t=tool: self._set_tool(t))
        self._tool_group.addAction(act)
        menu.addAction(act)

    def _set_chem_atom(self, symbol):
        self.scene.chem_atom = symbol
        self._activate_placement_tool(CHEM_ATOM)

    def _activate_placement_tool(self, tool):
        """Activate a non-checkable placement tool, clearing the lit tool."""
        checked = self._tool_group.checkedAction()
        if checked is not None:
            self._tool_group.setExclusive(False)
            checked.setChecked(False)
            self._tool_group.setExclusive(True)
        self._set_tool(tool)

    # ------------------------------------------------ symbol-library dropdowns
    def _build_symbol_dropdown(self, bar, glyph, tip, module, on_pick,
                               extra=None):
        """A dropdown listing a spec-library module's elements by category;
        picking one calls *on_pick(name)* to arm its placement tool. *extra*
        is an optional (section title, [(label, callback), …]) prepended."""
        button = QToolButton()
        button.setPopupMode(QToolButton.InstantPopup)
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.setIcon(icons.icon(glyph))
        button.setToolTip(tip)
        menu = QMenu(button)
        self._populate_symbol_menu(menu, module, on_pick, extra)
        button.setMenu(menu)
        bar.addWidget(button)

    def _populate_symbol_menu(self, menu, module, on_pick, extra=None):
        """Fill *menu* with a spec-library module's elements by category
        (shared between the toolbar dropdowns and the Library menu)."""
        if extra:
            menu.addSection(extra[0])
            for label, callback in extra[1]:
                menu.addAction(label, callback)
        for title, names in module.CATEGORIES:
            menu.addSection(title)
            for name in names:
                menu.addAction(module.LABELS[name],
                               lambda _=False, n=name: on_pick(n))

    def _library_picker(self, attr, tool):
        """An on_pick callback arming *tool* with the chosen element name
        stored on the scene as *attr*."""
        def on_pick(name):
            setattr(self.scene, attr, name)
            self._activate_placement_tool(tool)
        return on_pick

    def _library_extra(self, module):
        """Palette-specific extra menu entries (the drag-to-size Room, the
        from-scratch molecule builder)."""
        if module is floorplan:
            return ("Room", [("Room",
                              lambda: self._activate_placement_tool(ROOM))])
        if module is molecules:
            return ("Build", [("Molecule builder…",
                               self.open_new_molecule_builder)])
        return None

    def open_new_molecule_builder(self):
        """Open the 3D molecule builder on a fresh atom, then place whatever
        the user builds on the canvas."""
        from .molview import MoleculeViewer
        atoms, bonds = molecules.single_atom("C")
        dlg = MoleculeViewer("custom", atoms=atoms, bonds=bonds, parent=self)
        if dlg.exec_():
            a, b = dlg.result()
            centre = self.view.mapToScene(
                self.view.viewport().rect().center())
            self.scene.place_built_molecule(a or atoms, b or bonds, centre,
                                            dlg.az, dlg.el, dlg.bond,
                                            dlg.representation())

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
        menu.addAction(icons.icon("mdi.folder-cog-outline"),
                       "Template Explorer…", self.open_template_explorer)
        menu.addAction(icons.icon("mdi.folder-open-outline"),
                       "Open objects folder", self.open_objects_folder)
        menu.addSeparator()
        objects = library.iter_objects()
        if not objects:
            empty = menu.addAction("(no saved objects yet)")
            empty.setEnabled(False)
            return
        # nested sub-menus mirror the folder structure
        submenus = {(): menu}
        for parts, name, path in objects:
            parent = self._objects_submenu(menu, submenus, parts)
            parent.addAction(name,
                             lambda _=False, p=path: self.insert_object(p))

    def _objects_submenu(self, root, cache, parts):
        """Return the QMenu for folder *parts*, creating nested menus."""
        if parts in cache:
            return cache[parts]
        parent = self._objects_submenu(root, cache, parts[:-1])
        sub = parent.addMenu(icons.icon("mdi.folder-outline"), parts[-1])
        cache[parts] = sub
        return sub

    def open_template_explorer(self):
        from .templates import TemplateExplorer
        TemplateExplorer(self).exec_()

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

        self._fill_style_combo = QComboBox()
        self._fill_style_combo.addItems(["Fill: Solid", "Fill: Linear",
                                         "Fill: Radial", "Fill: Sun"])
        self._fill_style_combo.setToolTip(
            "Fill style for new shapes — solid colour, a linear/radial "
            "gradient from the fill colour to the gradient end colour, or "
            "Sun: an off-centre highlight of the end colour, as if the "
            "shape were lit from the top-left")
        self._fill_style_combo.currentIndexChanged.connect(
            self._on_fill_style_changed)
        bar.addWidget(self._fill_style_combo)

        self._fill2_btn = QToolButton()
        self._fill2_btn.setToolTip(
            "Gradient end colour (the fill fades from the fill colour "
            "to this one)")
        self._fill2_btn.clicked.connect(self.pick_fill_color2)
        self._fill2_btn.setEnabled(False)          # solid by default
        bar.addWidget(self._fill2_btn)

        self._fill_act = QAction(icons.icon("mdi.shape"),
                                 "Fill new shapes", self)
        self._fill_act.setCheckable(True)
        self._fill_act.setToolTip("Give newly drawn shapes a fill")
        self._fill_act.toggled.connect(self._set_fill_enabled)
        bar.addAction(self._fill_act)

        self._bucket_mode = QComboBox()
        self._bucket_mode.addItems(["Bucket: Raster", "Bucket: Vector"])
        self._bucket_mode.setCurrentIndex(1)   # vector: fills stay editable
        self._bucket_mode.setToolTip(
            "Bucket fill output — an editable vector path (movable/"
            "deletable like any shape), or paint baked into the raster "
            "layer")
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
        bar.addSeparator()
        bar.addAction(icons.icon("mdi.arrange-bring-to-front"),
                      "Bring to front",
                      lambda: self._reorder_selection("front"))
        bar.addAction(icons.icon("mdi.arrange-bring-forward"),
                      "Bring forward",
                      lambda: self._reorder_selection("forward"))
        bar.addAction(icons.icon("mdi.arrange-send-backward"),
                      "Send backward",
                      lambda: self._reorder_selection("backward"))
        bar.addAction(icons.icon("mdi.arrange-send-to-back"),
                      "Send to back",
                      lambda: self._reorder_selection("back"))
        bar.addSeparator()
        bar.addAction(icons.icon("mdi.delete-outline"), "Delete",
                      self.scene.delete_selection)
        bar.addSeparator()
        ai_toggle = self.ai_dock.toggleViewAction()   # show/hide chat panel
        ai_toggle.setIcon(icons.icon("mdi.robot-outline"))
        ai_toggle.setText("AI Chat")
        ai_toggle.setToolTip("Show / hide the AI Assistant panel")
        bar.addAction(ai_toggle)
        ai_btn = bar.widgetForAction(ai_toggle)       # label it so it's clear
        if ai_btn is not None:
            ai_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

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
        edit_menu.addSeparator()
        arrange = edit_menu.addMenu("&Arrange")
        arrange.addAction("Bring to &Front",
                          lambda: self._reorder_selection("front"),
                          "Ctrl+Shift+]")
        arrange.addAction("Bring F&orward",
                          lambda: self._reorder_selection("forward"), "Ctrl+]")
        arrange.addAction("Send &Backward",
                          lambda: self._reorder_selection("backward"), "Ctrl+[")
        arrange.addAction("Send to Bac&k",
                          lambda: self._reorder_selection("back"),
                          "Ctrl+Shift+[")

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

        self._build_library_menu(m)
        self._build_measure_menu(m)
        self._build_examples_menu(m)

        help_menu = m.addMenu("&Help")
        help_menu.addAction("&User Guide", self._user_guide, "F1")
        help_menu.addSeparator()
        help_menu.addAction("&About", self._about)

    def _build_measure_menu(self, menubar):
        """Measure ▸ the mm measuring tools: dimension line, scale bar and
        the edge-ruler toggle."""
        menu = self._measure_menu = menubar.addMenu("&Measure")
        menu.addAction(icons.icon("mdi.ruler"),
                       "&Dimension line\tM", self._activate_dimension)
        menu.addAction(icons.icon("mdi.angle-acute"),
                       "&Protractor (angle)", self._activate_protractor)
        menu.addSeparator()
        menu.addAction(icons.icon("mdi.ruler-square-compass"),
                       "&Scale bar…", self._insert_scale_bar)
        menu.addSeparator()
        self._rulers_act = QAction("Show &rulers (mm)", self, checkable=True)
        self._rulers_act.toggled.connect(self.view.set_rulers_visible)
        menu.addAction(self._rulers_act)

    def _insert_scale_bar(self):
        """Ask for a length + unit and drop a labelled scale bar at the
        centre of the current view."""
        from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                                     QDoubleSpinBox, QFormLayout, QVBoxLayout)
        dlg = QDialog(self)
        dlg.setWindowTitle("Scale bar")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        layout.addLayout(form)
        value = QDoubleSpinBox()
        value.setRange(0.001, 1_000_000.0)
        value.setDecimals(3)
        value.setValue(10.0)
        unit = QComboBox()
        unit.addItems(["nm", "µm", "mm", "cm"])
        unit.setCurrentText("mm")
        form.addRow("Length", value)
        form.addRow("Unit", unit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec_() != QDialog.Accepted:
            return
        factor = {"nm": 1e-6, "µm": 1e-3, "mm": 1.0, "cm": 10.0}[
            unit.currentText()]
        length_mm = value.value() * factor
        label = f"{value.value():g} {unit.currentText()}"
        center = self.view.mapToScene(self.view.viewport().rect().center())
        self.scene.place_scale_bar(length_mm, label, center)

    def _activate_protractor(self):
        """Arm the three-click angle-measure tool."""
        self._activate_placement_tool(PROTRACTOR)

    def _build_library_menu(self, menubar):
        """Library ▸ every symbol palette of the left toolbar (chemistry,
        room layout, electrical, … math) plus the reusable-object library,
        so the palettes are also reachable from the menu bar."""
        menu = menubar.addMenu("&Library")
        chem = menu.addMenu(icons.icon("mdi.molecule"), "Chemistry")
        self._populate_chemistry_menu(chem)
        for title, glyph, _tip, module, attr, tool in SYMBOL_LIBRARIES:
            sub = menu.addMenu(icons.icon(glyph), title)
            self._populate_symbol_menu(sub, module,
                                       self._library_picker(attr, tool),
                                       self._library_extra(module))
        menu.addSeparator()
        objects = menu.addMenu(icons.icon("mdi.bookshelf"), "&Objects")
        objects.aboutToShow.connect(
            lambda: self._rebuild_objects_menu(objects))

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
        self.scene.end_chain()              # finish any in-progress bond chain
        self.scene.end_angle()              # cancel any in-progress protractor
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

    @staticmethod
    def _focused_text_widget():
        """The focused text widget (e.g. the AI chat box/transcript), so
        Ctrl+C/X/V there act on the text rather than the canvas — the
        window-level Edit shortcuts would otherwise swallow them."""
        from PyQt5.QtWidgets import QLineEdit, QPlainTextEdit, QTextEdit
        w = QApplication.focusWidget()
        return w if isinstance(w, (QLineEdit, QPlainTextEdit, QTextEdit)) \
            else None

    def copy_selection(self):
        w = self._focused_text_widget()
        if w is not None:
            w.copy()
            return
        items = self._selected_top_items()
        if not items:
            return
        payload = json.dumps([document.item_to_dict(i) for i in items])
        mime = QMimeData()
        mime.setData(MIME_ITEMS, payload.encode("utf-8"))
        QApplication.clipboard().setMimeData(mime)

    def cut_selection(self):
        w = self._focused_text_widget()
        if w is not None:
            w.cut()
            return
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
        w = self._focused_text_widget()
        if w is not None:
            w.paste()
            return
        mime = QApplication.clipboard().mimeData()
        if mime is None:
            return
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

    # ------------------------------------------------------------ drag & drop
    def _on_drop(self, paths, image, scene_pos):
        """Drop handler: a dropped .svg/.kpaint opens as a document; any
        image (file in any Qt-supported format, or raw image data dragged
        from another app) is placed as a movable image item at the drop
        point. Multiple images cascade and select together."""
        docs = [p for p in paths
                if Path(p).suffix.lower() in (".svg", ".kpaint")]
        if docs:
            if self._confirm_discard():
                self._load_document(docs[0])
            return

        pixmaps = []
        for p in paths:
            pm = QPixmap(p)                 # uses Qt's image plugins
            if not pm.isNull():
                pixmaps.append(pm)
        if not pixmaps and isinstance(image, QImage) and not image.isNull():
            pixmaps.append(QPixmap.fromImage(image))
        if not pixmaps:
            if paths or image is not None:
                QMessageBox.warning(
                    self, APP_NAME,
                    "Could not load the dropped item as an image.")
            return

        self.scene.clearSelection()
        pos = QPointF(scene_pos)
        for pm in pixmaps:
            item = ImageItem(pm)
            item.setPos(pos)
            self.scene.addItem(item)
            item.setSelected(True)
            pos += QPointF(20, 20)          # cascade multiple drops
        self.scene.changed_by_user.emit()

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
        name, ok = QInputDialog.getText(
            self, "Save object",
            "Object name (use Folder/Name to file it in a sub-folder):")
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

    def _update_size_readout(self, *_):
        """Show the current shape's size in mm in the status bar: the item
        being drawn (scene._temp_item) if any, else the selection. A single
        line shows its length; other single shapes add their perimeter;
        multiple items show the combined bounding box."""
        from .handles import Handle
        scene = self.scene
        dpi = max(getattr(scene, "dpi", 96), 1)
        k = 25.4 / dpi                                   # px -> mm
        target = getattr(scene, "_temp_item", None)
        items = [target] if target is not None else scene.selectedItems()
        items = [it for it in items
                 if it is not None and not isinstance(it, Handle)]
        if not items:
            self._size_label.setText("")
            return
        if len(items) == 1 and isinstance(items[0], LineItem):
            self._size_label.setText(
                f"↔ {items[0].line().length() * k:.1f} mm")
            return
        if len(items) == 1:
            # Single shape: report its true geometry (outline, no stroke
            # inflation) and perimeter where the outline is known.
            outline = PaintScene._outline_path(items[0])
            if outline is not None:
                br = outline.boundingRect()
                text = f"{br.width() * k:.1f} × {br.height() * k:.1f} mm"
                if outline.length() > 0:
                    text += f"   perim {outline.length() * k:.1f} mm"
                self._size_label.setText(text)
                return
        rect = None
        for it in items:
            r = it.sceneBoundingRect()
            rect = r if rect is None else rect.united(r)
        self._size_label.setText(
            f"{rect.width() * k:.1f} × {rect.height() * k:.1f} mm")

    # ------------------------------------------------------------ editing
    def _show_item_menu(self, item, global_pos):
        from .properties import build_context_menu
        build_context_menu(self, item).exec_(global_pos)

    def _show_canvas_menu(self, scene_pos, global_pos):
        """Right-click on empty canvas: pop up the tools + library menu."""
        self._build_canvas_menu(scene_pos).exec_(global_pos)

    def _build_canvas_menu(self, scene_pos) -> QMenu:
        """The empty-canvas menu: a Tools submenu plus every symbol-library
        palette listed directly (as on the left toolbar). A library pick
        drops that symbol at the click point (grouped, selected, undoable)."""
        menu = QMenu(self)
        tools = menu.addMenu(icons.icon("mdi.toolbox-outline"), "Tools")
        for tool, glyph, label, _sc in DIRECT_TOOLS:
            tools.addAction(icons.icon(glyph), label,
                            lambda _=False, t=tool: self._activate_tool(t))
        tools.addAction(icons.icon("mdi.format-text"), "Text",
                        lambda: self._activate_tool(TEXT))
        tools.addAction(icons.icon("mdi.ruler"), "Dimension",
                        self._activate_dimension)
        tools.addSeparator()
        for label, items in SHAPE_GROUPS:
            sub = tools.addMenu(label)
            for tool, glyph, lbl, _sc in items:
                sub.addAction(self._tool_icon(tool, glyph), lbl,
                              lambda _=False, t=tool: self._activate_tool(t))
        chem = tools.addMenu(icons.icon("mdi.molecule"), "Chemistry")
        for tool, lbl in CHEM_BOND_TOOLS + CHEM_RING_TOOLS:
            chem.addAction(lbl,
                           lambda _=False, t=tool: self._activate_tool(t))
        atoms = chem.addMenu("Atom / group label")
        for sym in chemistry.ATOMS:
            atoms.addAction(sym, lambda _=False, s=sym: self._set_chem_atom(s))

        menu.addSeparator()
        for title, glyph, _tip, module, _attr, _tool in SYMBOL_LIBRARIES:
            sub = menu.addMenu(icons.icon(glyph), title)
            self._populate_symbol_menu(
                sub, module,
                lambda name, m=module: self._insert_library_item(m, name,
                                                                 scene_pos))
        return menu

    def _activate_tool(self, tool):
        """Switch to *tool*, keeping the left toolbar's lit button in sync by
        triggering that tool's existing action when it has one."""
        for act in self._tool_group.actions():
            if act.data() == tool:
                act.trigger()
                return
        self._set_tool(tool)

    def _insert_library_item(self, module, name, scene_pos):
        """Drop a symbol-library element at *scene_pos* on the canvas."""
        if module is molecules or module is crystals:
            self.scene.place_mol_element(name, scene_pos)
        else:
            self.scene._place_symbol(module, name, scene_pos)

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

    def remove_image_background(self, item):
        """Make *item*'s background transparent: flood the modal border
        colour inward and clear its alpha (undoable; PNG-embedded alpha
        survives save in both SVG and legacy JSON)."""
        from . import imageops
        result = imageops.remove_background(item.pixmap().toImage())
        if result is None:
            self.statusBar().showMessage(
                "No uniform background found at the image edges")
            return
        item.setPixmap(QPixmap.fromImage(result))
        self.scene.changed_by_user.emit()
        self.statusBar().showMessage("Background removed — now transparent")

    def reorder_item(self, item, where: str):
        """Restack *item*: to front/back, or one step forward/backward.
        z values are first normalised to 0..n-1 in current stacking order
        so a single step is reliable even when items share a z."""
        items = self.scene.vector_items()      # bottom-to-top (z ascending)
        if item not in items or len(items) < 2:
            return
        for idx, it in enumerate(items):
            it.setZValue(idx)
        i, n = items.index(item), len(items)
        if where == "front":
            item.setZValue(n)
        elif where == "back":
            item.setZValue(-1)
        elif where == "forward" and i < n - 1:
            item.setZValue(i + 1); items[i + 1].setZValue(i)
        elif where == "backward" and i > 0:
            item.setZValue(i - 1); items[i - 1].setZValue(i)
        else:
            return
        self.scene.changed_by_user.emit()

    def _reorder_selection(self, where: str):
        """Restack the selected top-level item (menu/shortcut entry point)."""
        items = self._selected_top_items()
        if len(items) == 1:
            self.reorder_item(items[0], where)

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

    def pick_fill_color2(self):
        color = QColorDialog.getColor(self.scene.fill_color2, self,
                                      "Gradient end colour")
        if color.isValid():
            self.scene.fill_color2 = color
            self._fill_act.setChecked(True)
            self._refresh_color_buttons()

    def _on_fill_style_changed(self, index: int):
        from .gradient import FILL_STYLES
        self.scene.fill_style = FILL_STYLES[index]
        self._fill2_btn.setEnabled(index > 0)
        if index > 0:                     # choosing a gradient implies fill
            self._fill_act.setChecked(True)

    def _refresh_color_buttons(self):
        for btn, color in ((self._stroke_btn, self.scene.pen.color()),
                           (self._fill_btn, self.scene.fill_color),
                           (self._fill2_btn, self.scene.fill_color2)):
            pixmap = QPixmap(22, 22)
            pixmap.fill(QColor(color))
            btn.setIcon(QIcon(pixmap))
        self._refresh_width_icons()      # swatches follow the stroke colour

    def _on_color_picked(self, hexname, target):
        """The eyedropper sampled a colour: refresh the swatches and say
        where it landed (stroke, or fill with Shift+click)."""
        self._refresh_color_buttons()
        self._pick_label.setText(f"Picked {hexname} → {target}  ")

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
            "All supported (*.svg *.png);;SVG image (*.svg);;"
            "PNG image (*.png);;"
            "All files (*)")          # legacy .kpaint via All files
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

    def open_path(self, path: str) -> bool:
        """Open a file given on the command line. Used by the launcher and
        by KherveBook's "Open in KhervePaint", which writes an SVG and runs
        ``python -m khervepaint <file>`` — editing then Save (Ctrl+S) writes
        straight back to that file, where KherveBook reloads it."""
        if not Path(path).exists():
            return False
        return self._load_document(str(path))

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
        # SVG is the native format: a standard, fully SVG-compatible file
        # that round-trips as editable items here and opens anywhere.
        path, _ = QFileDialog.getSaveFileName(
            self, "Save As", "", "SVG image (*.svg)")
        if not path:
            return
        if Path(path).suffix.lower() != ".svg":
            path += ".svg"
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
