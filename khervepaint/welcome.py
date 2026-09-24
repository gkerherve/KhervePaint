"""The start-up wallpaper: a welcome screen over the empty canvas.

Shown when KhervePaint starts (unless a file was opened from the command
line, or the user unticked *Show at start-up*), and again from Help ▸
Welcome Screen. It is a painted wallpaper — the splash's warm slate, a
faint drafting grid and real shaded 3D solids from `solids` scattered
behind — with the things you do first: new drawing, open, recent files,
examples, a 3D scene, the guide. Any choice (or Esc, or Start drawing)
lifts it and hands over the canvas.

It is an overlay widget on the view, not a dialog: nothing modal, nothing
in the document, so it can't touch undo or the saved file.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math
from pathlib import Path

from PyQt5.QtCore import QEvent, QPointF, QRectF, QSettings, Qt
from PyQt5.QtGui import (QColor, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap, QPolygonF,
                         QRadialGradient)
from PyQt5.QtWidgets import (QCheckBox, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QPushButton, QVBoxLayout, QWidget)

SETTINGS = ("Kherve", "KhervePaint")
KEY_SHOW = "welcome/show"
ACCENT = QColor("#e6b325")
TEXT = QColor("#f6f1e0")
MUTED = QColor("#a89f88")

#: decorative solids: (name, colour, x frac, y frac, size frac, az°, el°)
_DECOR = [
    ("cube", "#5b8fd9", 0.83, 0.20, 0.13, 30, 24),
    ("torus", "#e6b325", 0.92, 0.55, 0.12, 20, 50),
    ("sphere", "#d9534f", 0.72, 0.70, 0.09, 0, 20),
    ("icosahedron", "#4caf6a", 0.69, 0.44, 0.07, 40, 20),
    ("cylinder", "#8e6bc9", 0.86, 0.80, 0.08, 25, 25),
    ("cone", "#ee9a3a", 0.955, 0.88, 0.07, 30, 20),
]

_BUTTON_CSS = """
QPushButton {
    background: rgba(255,255,255,18); color: #f6f1e0;
    border: 1px solid rgba(255,255,255,40); border-radius: 10px;
    padding: 12px 16px; text-align: left; font-size: 14px;
}
QPushButton:hover { background: rgba(230,179,37,60);
                    border-color: #e6b325; }
QPushButton:pressed { background: rgba(230,179,37,110); }
"""
_LINK_CSS = """
QPushButton { background: transparent; color: #e6d9b0; border: none;
              text-align: left; padding: 3px 2px; font-size: 13px; }
QPushButton:hover { color: #e6b325; text-decoration: underline; }
"""


def show_at_startup() -> bool:
    return QSettings(*SETTINGS).value(KEY_SHOW, True, type=bool)


def set_show_at_startup(on: bool):
    QSettings(*SETTINGS).setValue(KEY_SHOW, bool(on))


def paint_wallpaper(p: QPainter, rect: QRectF):
    """The background alone (also used by tests to check it paints)."""
    from . import solids
    w, h = rect.width(), rect.height()
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0.0, QColor("#35321f"))
    grad.setColorAt(0.55, QColor("#221f17"))
    grad.setColorAt(1.0, QColor("#15130f"))
    p.fillRect(rect, grad)
    glow = QRadialGradient(QPointF(w * 0.22, h * 0.3), max(w, h) * 0.6)
    glow.setColorAt(0.0, QColor(230, 179, 37, 38))
    glow.setColorAt(1.0, QColor(230, 179, 37, 0))
    p.fillRect(rect, glow)
    # drafting grid, like the canvas's own grid overlay
    p.setPen(QPen(QColor(255, 255, 255, 12), 1))
    step = 32
    for x in range(0, int(w) + step, step):
        p.drawLine(QPointF(x, 0), QPointF(x, h))
    for y in range(0, int(h) + step, step):
        p.drawLine(QPointF(0, y), QPointF(w, y))
    # a hand-drawn-looking curve and dimension line
    path = QPainterPath(QPointF(w * 0.05, h * 0.62))
    path.cubicTo(QPointF(w * 0.25, h * 0.42), QPointF(w * 0.42, h * 0.95),
                 QPointF(w * 0.62, h * 0.66))
    p.setPen(QPen(QColor(230, 179, 37, 70), 2.2, Qt.DashLine))
    p.drawPath(path)
    # scattered, softly faded 3D solids — the real renderer, not clip-art
    # Each solid is drawn opaque into its own layer and the layer faded:
    # fading face by face would show every mesh seam through the overlap.
    for name, color, fx, fy, fs, az, el in _DECOR:
        size = min(w, h) * fs * 1.6
        if size < 4:
            continue
        layer = QPixmap(int(size) + 2, int(size) + 2)
        layer.fill(Qt.transparent)
        lp = QPainter(layer)
        lp.setRenderHint(QPainter.Antialiasing)
        for spec in solids.solid_specs(name, size, size, math.radians(az),
                                       math.radians(el), color):
            lp.setBrush(QColor(spec["fill"]))
            lp.setPen(QPen(QColor(spec["stroke"]), spec["width"]))
            lp.drawPolygon(QPolygonF([QPointF(x + 1, y + 1)
                                      for x, y in spec["points"]]))
        lp.end()
        p.setOpacity(0.6)
        p.drawPixmap(QPointF(w * fx - size / 2, h * fy - size / 2), layer)
    p.setOpacity(1.0)


class WelcomeScreen(QWidget):
    """Overlay covering the canvas view until the user picks something."""

    def __init__(self, window):
        super().__init__(window.view)
        self._win = window
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setFocusPolicy(Qt.StrongFocus)
        window.view.installEventFilter(self)
        self._build()
        self._fit()

    # ── layout ────────────────────────────────────────────────
    def _build(self):
        from . import APP_NAME, __version__
        from .icons import _paint_kpaint
        outer = QHBoxLayout(self)
        outer.setContentsMargins(56, 40, 56, 40)
        col = QVBoxLayout()
        col.setSpacing(10)
        outer.addLayout(col, 3)
        outer.addStretch(2)

        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(_paint_kpaint(88))
        head.addWidget(logo)
        titles = QVBoxLayout()
        name = QLabel(APP_NAME)
        name.setStyleSheet("color:#f6f1e0; font-size:34px; font-weight:bold;"
                           "background:transparent;")
        tag = QLabel("Hybrid raster + vector drawing — science, "
                     "schematics and 3D")
        tag.setStyleSheet("color:#a89f88; font-size:14px;"
                          "background:transparent;")
        ver = QLabel(f"v{__version__}")
        ver.setStyleSheet("color:#e6b325; font-size:12px; font-weight:bold;"
                          "background:transparent;")
        for lab in (name, tag, ver):
            titles.addWidget(lab)
        head.addLayout(titles)
        head.addStretch(1)
        col.addLayout(head)
        col.addSpacing(18)

        grid = QGridLayout()
        grid.setSpacing(12)
        tiles = [
            ("mdi.file-outline", "New drawing", "A blank page",
             self._new),
            ("mdi.folder-open-outline", "Open…", "SVG, .kpaint or an image",
             self._open),
            ("mdi.cube-scan", "3D drawing", "Place solids, double-click to "
             "spin", self._three_d),
            ("mdi.image-multiple-outline", "Examples", "Instrument schematics",
             self._examples),
            ("mdi.molecule", "Molecule builder", "3D ball-and-stick models",
             self._molecule),
            ("mdi.book-open-variant", "User guide", "Every tool explained",
             self._guide),
        ]
        from . import icons
        for i, (glyph, title, sub, slot) in enumerate(tiles):
            b = QPushButton(icons.icon(glyph, color="#e6b325"),
                            f"  {title}\n  {sub}")
            b.setStyleSheet(_BUTTON_CSS)
            b.setCursor(Qt.PointingHandCursor)
            b.setMinimumHeight(64)
            b.clicked.connect(slot)
            grid.addWidget(b, i // 2, i % 2)
        col.addLayout(grid)

        recent = [p for p in self._win._recent_files() if Path(p).exists()]
        if recent:
            col.addSpacing(14)
            lab = QLabel("RECENT")
            lab.setStyleSheet("color:#a89f88; font-size:11px; "
                              "letter-spacing:2px; background:transparent;")
            col.addWidget(lab)
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("color: rgba(255,255,255,40);")
            col.addWidget(line)
            for path in recent[:6]:
                b = QPushButton(Path(path).name)
                b.setToolTip(path)
                b.setStyleSheet(_LINK_CSS)
                b.setCursor(Qt.PointingHandCursor)
                b.clicked.connect(lambda _=False, p=path: self._recent(p))
                col.addWidget(b)
        col.addStretch(1)

        foot = QHBoxLayout()
        self.show_box = QCheckBox("Show this screen at start-up")
        self.show_box.setChecked(show_at_startup())
        self.show_box.setStyleSheet("color:#a89f88; background:transparent;")
        self.show_box.toggled.connect(set_show_at_startup)
        foot.addWidget(self.show_box)
        foot.addStretch(1)
        start = QPushButton("Start drawing  ›")
        start.setStyleSheet(_BUTTON_CSS.replace("text-align: left",
                                                "text-align: center"))
        start.setCursor(Qt.PointingHandCursor)
        start.clicked.connect(self.dismiss)
        foot.addWidget(start)
        col.addLayout(foot)

    def _fit(self):
        self.setGeometry(self._win.view.rect())
        self.raise_()

    def eventFilter(self, obj, event):
        if obj is self._win.view and event.type() == QEvent.Resize:
            self._fit()
        return False

    def paintEvent(self, _event):
        p = QPainter(self)
        paint_wallpaper(p, QRectF(self.rect()))
        p.end()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
            self.dismiss()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, _event):
        pass                         # clicks on the wallpaper do nothing

    # ── actions ───────────────────────────────────────────────
    def dismiss(self):
        self._win.view.removeEventFilter(self)
        self.hide()
        self.deleteLater()
        if getattr(self._win, "_welcome", None) is self:
            self._win._welcome = None
        self._win.view.setFocus()

    def _new(self):
        self.dismiss()
        self._win.new_document()

    def _open(self):
        before = self._win._path
        self._win.open_file()
        if self._win._path != before:
            self.dismiss()

    def _recent(self, path):
        self.dismiss()
        self._win.open_recent(path)

    def _three_d(self):
        from .canvas import SOLID_PLACE
        self.dismiss()
        self._win._library_picker("solid_element", SOLID_PLACE)("cube")
        self._win.statusBar().showMessage(
            "3D solids: click to place a cube (pick other solids and colours "
            "from the 3D solids button); double-click a solid and drag to "
            "spin it.", 12000)

    def _examples(self):
        from PyQt5.QtWidgets import QMenu
        menu = self._win.findChild(QMenu, "examplesMenu")
        self.dismiss()
        if menu is not None:
            from PyQt5.QtGui import QCursor
            menu.popup(QCursor.pos())

    def _molecule(self):
        self.dismiss()
        self._win.open_new_molecule_builder()

    def _guide(self):
        self.dismiss()
        self._win._user_guide()
