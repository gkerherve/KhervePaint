"""AI Assistant dock — chat with an LLM that can draw into the canvas.

The assistant talks to any provider in ai_providers.py. When you ask it
to draw, it replies with a fenced JSON block of shape specs which this
module turns into real, undoable items on the vector layer.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
import re

from PyQt5.QtCore import (QLineF, QRectF, QSettings, QSize, Qt, QThread,
                          QTimer, pyqtSignal)
from PyQt5.QtGui import QBrush, QColor, QFont, QPen, QPixmap, QTextCursor
from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                             QDockWidget, QFormLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMainWindow, QMessageBox,
                             QPlainTextEdit, QPushButton, QSizePolicy,
                             QTextBrowser, QToolButton, QVBoxLayout, QWidget)

from . import ai_providers as providers
from . import icons
from .canvas import (ARC_KINDS, POLYGON_KINDS, ArcShapeItem, ArrowItem,
                     EllipseItem, LineItem, PolygonItem, RectItem,
                     RoundedRectItem, TextItem, center_origin)

_SETTINGS = ("Kherve", "KhervePaint")

#: AI shape name -> internal kind / handling.
_ALIASES = {"rectangle": "rect", "rounded_rectangle": "rounded_rect",
            "block_arrow": "arrow_right", "half_circle": "halfcircle",
            "quarter_circle": "quartercircle"}

SYSTEM_PROMPT = """You are a drawing assistant inside KhervePaint, a \
vector drawing app. Help the user create and arrange shapes.

The canvas is {w}x{h} pixels; the origin (0,0) is the top-left corner. \
The drawing currently contains: {summary}.

When the user asks you to draw, add or create something, reply with one \
short sentence and then a fenced code block tagged json holding a JSON \
array of shape specs. Do NOT output shapes unless drawing is requested.

Each spec is an object:
- "shape": one of rect, rounded_rect, ellipse, circle, line, arrow, text,
  triangle, right_triangle, diamond, parallelogram, trapezoid, pentagon,
  hexagon, heptagon, octagon, star, star6, plus, chevron, block_arrow,
  lightning, house, halfcircle, quartercircle
- area shapes use "x","y" (top-left) and "w","h" (size)
- line/arrow use "x1","y1","x2","y2"
- text uses "text","x","y" and optional "size"
- optional: "stroke" (hex or "none"), "fill" (hex or "none"),
  "width" (stroke width), "label" (text centred inside the shape)
- "fill" may instead be a gradient object {"kind":"linear"|"radial"|"sun",
  "c1":hex,"c2":hex,"angle":deg}. "sun" is a lit-sphere highlight (c2 =
  light colour) — use it to make a circle look like a 3D ball.

For chemistry, use the high-level "molecule" shape — it makes a real 3D
ball-and-stick model the user can rotate (double-click) and edit. ALWAYS
include the heavy-atom skeleton so it works even for an unusual name:
  {"shape":"molecule","name":"propan-2-ol","atoms":["C","C","C","O"],
   "bonds":[[0,1,1],[1,2,1],[1,3,1]],"x":cx,"y":cy}
- "atoms" = the HEAVY atoms only (no H's), as element symbols.
- "bonds" = [atom_i, atom_j, order] with order 1/2/3 (default 1).
- Hydrogens and correct 3D geometry are added automatically.
- "name" is optional (used to fetch a curated model for common
  molecules/crystals like water, methane, ethanol, benzene, glucose, pet,
  bcc, fcc, perovskite — but ALWAYS also give atoms/bonds as a fallback).
- Optional "as":"structural"|"lewis"|"condensed" draws the 2D formula.
For a ring molecule (benzene, cyclohexane…) prefer a library "name"; the
skeleton builder is best for chains and branched molecules.
Use "molecule" whenever the user asks for a molecule or crystal.

Two low-level shapes also exist for flat, non-rotatable sketches only:
{"shape":"atom","element":"C","x":cx,"y":cy,"r":radius} (a lit sphere,
x,y is the centre, r~20 for C/O/N, ~13 for H) and
{"shape":"bond","x1","y1","x2","y2","order":1|2|3}.
Keep coordinates within the canvas."""


# ---------------------------------------------------------------- specs
def prose_only(reply: str) -> str:
    """The human-readable part of a reply, with the drawing code removed.

    Cuts at the first code fence or JSON array start, so it also hides the
    code when the reply is *truncated* (a cut-off ```json block has no
    closing fence, which a simple ```...``` strip would miss — that's how
    raw JSON used to leak into the chat)."""
    cut = None
    fence = reply.find("```")
    if fence != -1:
        cut = fence
    m = re.search(r"\[\s*\{", reply)          # a bare (unfenced) spec array
    if m and (cut is None or m.start() < cut):
        cut = m.start()
    return (reply[:cut] if cut is not None else reply).strip()


def extract_specs(text: str):
    """Pull a JSON array of shape specs out of an assistant reply.

    Falls back to salvaging individual ``{...}`` objects when the JSON is
    truncated (long diagrams can be cut off by the token limit)."""
    candidates = re.findall(r"```[a-zA-Z-]*\s*(.*?)```", text, re.DOTALL)
    candidates.append(text)
    for blob in candidates:
        try:
            data = json.loads(blob.strip())
        except (ValueError, TypeError):
            continue
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and isinstance(data.get("shapes"), list):
            return data["shapes"]
    source = candidates[0] if len(candidates) > 1 else text
    return _salvage_objects(source)


def _salvage_objects(text: str):
    """Parse every complete top-level {...} object in *text* (so a cut-off
    JSON array still yields the shapes that were fully written)."""
    objs = []
    depth = start = 0
    in_str = esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}' and depth > 0:
            depth -= 1
            if depth == 0:
                try:
                    objs.append(json.loads(text[start:i + 1]))
                except ValueError:
                    pass
    return objs


def _pen(spec):
    color = spec.get("stroke", "#1a1a1a")
    if not color or str(color).lower() == "none":
        return QPen(Qt.NoPen)
    pen = QPen(QColor(color), float(spec.get("width", 2)))
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _brush(spec):
    fill = spec.get("fill")
    # A gradient fill (lit sphere, linear/radial) may be given as a spec dict
    # under "fill" or "gradient" — {"kind","c1","c2","angle"}.
    grad = spec.get("gradient")
    if grad is None and isinstance(fill, dict):
        grad = fill
    if isinstance(grad, dict):
        from . import gradient
        return gradient.brush_from_spec(grad)
    if not fill or str(fill).lower() == "none":
        return QBrush(Qt.NoBrush)
    return QBrush(QColor(fill))


def _spec_to_item(spec):
    shape = str(spec.get("shape", "")).lower().replace("-", "_")
    shape = _ALIASES.get(shape, shape)
    x = float(spec.get("x", 0))
    y = float(spec.get("y", 0))
    w = float(spec.get("w", spec.get("width_px", 80)))
    h = float(spec.get("h", spec.get("height_px", 60)))
    rect = QRectF(x, y, w, h)

    if shape in ("line", "arrow"):
        line = QLineF(float(spec.get("x1", x)), float(spec.get("y1", y)),
                      float(spec.get("x2", x + w)), float(spec.get("y2", y)))
        item = ArrowItem(line) if shape == "arrow" else LineItem(line)
        item.setPen(_pen(spec))
    elif shape == "text":
        from PyQt5.QtGui import QFont
        item = TextItem(str(spec.get("text", "Text")))
        item.setDefaultTextColor(QColor(spec.get("color",
                                                 spec.get("stroke", "#1a1a1a"))))
        item.setFont(QFont("Segoe UI", int(spec.get("size", 14))))
        if str(spec.get("anchor", "")).lower() == "center":
            # treat (x, y) as the text centre rather than its top-left corner
            br = item.boundingRect()
            item.setPos(x - br.width() / 2.0, y - br.height() / 2.0)
        else:
            item.setPos(x, y)
        center_origin(item)
        if spec.get("rotation"):
            item.setRotation(float(spec["rotation"]))
        return item
    elif shape in ("rect", "circle", "ellipse"):
        item = RectItem(rect) if shape == "rect" else EllipseItem(rect)
        item.setPen(_pen(spec))
        item.setBrush(_brush(spec))
    elif shape == "rounded_rect":
        item = RoundedRectItem(rect, float(spec.get("radius", 12)))
        item.setPen(_pen(spec))
        item.setBrush(_brush(spec))
    elif shape in ARC_KINDS:
        item = ArcShapeItem(rect, kind=shape)
        item.setPen(_pen(spec))
        item.setBrush(_brush(spec))
    elif shape in POLYGON_KINDS:
        item = PolygonItem(kind=shape)
        item.set_rect(rect)
        item.setPen(_pen(spec))
        item.setBrush(_brush(spec))
    else:
        return None

    label = spec.get("label")
    if label and hasattr(item, "set_label"):
        item.set_label(str(label))
    center_origin(item)
    if spec.get("rotation"):
        item.setRotation(float(spec["rotation"]))
    return item


def _bond_triple(b):
    """Normalise a bond entry to [i, j, order] (order defaults to single)."""
    b = list(b)
    return [int(b[0]), int(b[1]), int(b[2]) if len(b) > 2 else 1]


def _place_ai_molecule(scene, spec):
    """Place a high-level `molecule` spec as a tagged, 3D-rotatable group.

    The model gives either a library ``name`` or a heavy-atom skeleton
    (``atoms`` = element strings + ``bonds`` = [i, j, order]); hydrogens and
    correct 3D geometry are filled in. Full 3D coordinates
    (``atoms`` = [[el, x, y, z], …]) are also accepted."""
    from . import molecules
    from PyQt5.QtCore import QPointF
    name = spec.get("name")
    key = molecules.resolve_name(name)             # tolerant name lookup
    atoms = bonds = None
    if key:                                        # a library model (best)
        atoms, bonds, _e, _r = molecules.model_data(key)
        name = key
    elif spec.get("atoms"):
        raw = spec["atoms"]
        links = [_bond_triple(b) for b in spec.get("bonds", [])]
        if raw and isinstance(raw[0], str):        # heavy-atom skeleton
            atoms, bonds = molecules.build_molecule(
                [str(e) for e in raw], links)
        else:                                      # explicit 3D atoms
            atoms = [list(a) for a in raw]
            bonds = links
    if not atoms:
        return None
    cx = float(spec.get("x", spec.get("cx", scene.sceneRect().center().x())))
    cy = float(spec.get("y", spec.get("cy", scene.sceneRect().center().y())))
    mode = str(spec.get("as", spec.get("repr", "3d"))).lower()
    return scene.place_built_molecule(atoms, bonds, QPointF(cx, cy), mode=mode,
                                      name=name or "custom", commit=False)


def apply_specs(scene, specs):
    """Create items from *specs* and add them (selected) to the scene.

    Items are stacked in spec order (first at the back, last in front) and
    placed above anything already on the canvas, so the layering the model
    intends is preserved — and survives grouping. High-level ``molecule``
    specs become tagged 3D-rotatable groups (see `_place_ai_molecule`)."""
    from . import molecules
    created = []
    flat = []
    for spec in specs:
        if str(spec.get("shape", "")).lower() in ("molecule", "molecule3d"):
            try:
                mol = _place_ai_molecule(scene, spec)
            except Exception:
                mol = None
            if mol is not None:
                created.append(mol)
        else:
            flat.append(spec)
    flat = molecules.expand_specs(flat)       # atom/bond -> spheres + sticks
    existing = [i.zValue() for i in scene.vector_items()]
    base = (max(existing) + 1) if existing else 0
    items = []
    for spec in flat:
        try:
            item = _spec_to_item(spec)
        except Exception:
            item = None
        if item is not None:
            scene.addItem(item)
            item.setZValue(base + len(items))
            items.append(item)
    created += items
    if created:
        scene.clearSelection()
        for item in created:
            item.setSelected(True)
        scene.changed_by_user.emit()
    return created


def _scene_summary(scene):
    items = scene.vector_items()
    if not items:
        return "nothing yet"
    kinds = {}
    for item in items:
        name = type(item).__name__.replace("Item", "").lower()
        kinds[name] = kinds.get(name, 0) + 1
    return ", ".join(f"{n} {k}" for k, n in kinds.items())


# ---------------------------------------------------------------- worker
class _Worker(QThread):
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as exc:                  # pragma: no cover - network
            self.failed.emit(str(exc))


# ---------------------------------------------------------------- settings
class AiSettingsDialog(QDialog):
    """Provider / model / API-key settings, like the rest of the family."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Chat Settings")
        self.setMinimumWidth(440)
        self._settings = QSettings(*_SETTINGS)
        self._worker = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.provider_combo = QComboBox()
        for key in providers.PROVIDERS:
            self.provider_combo.addItem(providers.DISPLAY_NAMES[key], key)
        form.addRow("Provider:", self.provider_combo)

        model_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.refresh_btn = QToolButton()
        self.refresh_btn.setIcon(icons.icon("mdi.refresh"))
        self.refresh_btn.setToolTip("Refresh the model list from the provider")
        model_row.addWidget(self.model_combo, 1)
        model_row.addWidget(self.refresh_btn)
        form.addRow("Model:", model_row)

        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        form.addRow("API Key:", self.key_edit)

        self.base_label = QLabel("Base URL:")
        self.base_edit = QLineEdit()
        form.addRow(self.base_label, self.base_edit)

        self.help_box = QGroupBox("How to get an API key")
        help_layout = QVBoxLayout(self.help_box)
        self.help_label = QLabel()
        self.help_label.setWordWrap(True)
        help_layout.addWidget(self.help_label)
        layout.addWidget(self.help_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.provider_combo.currentIndexChanged.connect(self._load_provider)
        self.refresh_btn.clicked.connect(self._refresh)

        saved = self._settings.value("ai/provider", "Claude")
        idx = self.provider_combo.findData(saved)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self._load_provider()

    def _provider(self):
        return self.provider_combo.currentData()

    def _load_provider(self, *_):
        provider = self._provider()
        self.key_edit.setText(self._settings.value(f"ai/key/{provider}", ""))
        self.base_edit.setText(self._settings.value(f"ai/base/{provider}", ""))
        self.key_edit.setEnabled(provider in providers.NEEDS_KEY)
        show_base = provider in ("Local", "Ollama")
        self.base_label.setVisible(show_base)
        self.base_edit.setVisible(show_base)
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(providers.DEFAULT_MODELS.get(provider, []))
        saved = self._settings.value(f"ai/model/{provider}", "")
        if saved:
            self.model_combo.setCurrentText(saved)
        self.model_combo.blockSignals(False)
        self.help_label.setText(providers.PROVIDER_HELP.get(provider, ""))

    def _refresh(self):
        provider = self._provider()
        key, base = self.key_edit.text(), self.base_edit.text()
        self.refresh_btn.setEnabled(False)
        self._worker = _Worker(
            lambda: providers.list_models(provider, key, base), self)
        self._worker.done.connect(self._models_ready)
        self._worker.failed.connect(self._refresh_failed)
        self._worker.start()

    def _models_ready(self, models):
        self.refresh_btn.setEnabled(True)
        if not models:
            QMessageBox.information(self, "AI Chat", "No models returned.")
            return
        current = self.model_combo.currentText()
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.setCurrentText(current if current in models
                                        else models[0])

    def _refresh_failed(self, message):
        self.refresh_btn.setEnabled(True)
        QMessageBox.warning(self, "AI Chat",
                            f"Could not list models:\n{message}")

    def _accept(self):
        provider = self._provider()
        self._settings.setValue("ai/provider", provider)
        self._settings.setValue(f"ai/key/{provider}", self.key_edit.text())
        self._settings.setValue(f"ai/base/{provider}", self.base_edit.text())
        if self.model_combo.currentText():
            self._settings.setValue(f"ai/model/{provider}",
                                    self.model_combo.currentText())
        self.accept()


# ---------------------------------------------------------------- dock
class _ChatInput(QPlainTextEdit):
    """Multi-line input that submits on Enter (Shift+Enter = newline) and
    recalls previously sent prompts with Up/Down (at the first/last line)."""

    submitted = pyqtSignal()
    history_prev = pyqtSignal()
    history_next = pyqtSignal()
    image_pasted = pyqtSignal(object)        # a pasted QImage (screenshot)

    def insertFromMimeData(self, source):
        if source.hasImage():                # paste a screenshot, not text
            self.image_pasted.emit(source.imageData())
        else:
            super().insertFromMimeData(source)

    def keyPressEvent(self, event):
        if (event.key() in (Qt.Key_Return, Qt.Key_Enter)
                and not event.modifiers() & Qt.ShiftModifier):
            self.submitted.emit()
            return
        cursor = self.textCursor()
        if event.key() == Qt.Key_Up and cursor.blockNumber() == 0:
            self.history_prev.emit()
            return
        if (event.key() == Qt.Key_Down
                and cursor.blockNumber() == self.document().blockCount() - 1):
            self.history_next.emit()
            return
        super().keyPressEvent(event)


class AiDock(QDockWidget):
    def __init__(self, scene, parent=None):
        super().__init__("AI Chat", parent)
        self.scene = scene
        self.setObjectName("AiAssistant")
        self._worker = None
        self._is_busy = False
        self._think_dots = 0
        self._think_timer = QTimer(self)
        self._think_timer.setInterval(400)
        self._think_timer.timeout.connect(self._tick)
        self._history = []
        self._sent = []                 # past user prompts (Up/Down recall)
        self._hist_index = None
        self._draft = ""
        self._settings = QSettings(*_SETTINGS)
        self._font_pt = int(self._settings.value("ai/fontpt", 10))

        self.body = body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        header.setSpacing(2)
        header.addWidget(QLabel("<b>AI Assistant</b>"))
        self.provider_label = QLabel()
        self.provider_label.setStyleSheet("color:#888;")
        header.addWidget(self.provider_label, 1)
        self.smaller_btn = self._tool("A−", "Smaller text",
                                       lambda: self._change_font(-1))
        self.larger_btn = self._tool("A+", "Larger text",
                                      lambda: self._change_font(1))
        self.help_btn = self._tool(None, "Help", self._show_help,
                                   "mdi.help-circle-outline")
        self.settings_btn = self._tool(None, "AI Chat settings",
                                       self._open_settings, "mdi.cog-outline")
        self.clear_btn = self._tool(None, "Clear chat", self._clear,
                                    "mdi.notification-clear-all")
        for btn in (self.smaller_btn, self.larger_btn, self.help_btn,
                    self.settings_btn, self.clear_btn):
            header.addWidget(btn)
        layout.addLayout(header)

        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(True)
        layout.addWidget(self.transcript, 1)

        self.thinking_label = QLabel()
        self.thinking_label.setStyleSheet("color:#2e7d4f; font-style:italic;")
        self.thinking_label.setVisible(False)
        layout.addWidget(self.thinking_label)

        # Pasted-screenshot attachment row (hidden until an image is pasted).
        self._pending_image = None
        self.attach_row = QWidget()
        attach = QHBoxLayout(self.attach_row)
        attach.setContentsMargins(0, 0, 0, 0)
        self.attach_thumb = QLabel()
        self.attach_label = QLabel("Image attached")
        self.attach_label.setStyleSheet("color:#888;")
        remove = self._tool(None, "Remove image", self._clear_image,
                            "mdi.close")
        attach.addWidget(self.attach_thumb)
        attach.addWidget(self.attach_label, 1)
        attach.addWidget(remove)
        self.attach_row.setVisible(False)
        layout.addWidget(self.attach_row)

        input_row = QHBoxLayout()
        self.input = _ChatInput()
        self.input.setPlaceholderText("Ask Claude to draw… (paste a "
                                      "screenshot with Ctrl+V)")
        self.input.setFixedHeight(70)
        self.send_btn = self._tool(None, "Send", self._send_or_stop, "mdi.send")
        self.send_btn.setIconSize(QSize(24, 24))
        input_row.addWidget(self.input, 1)
        input_row.addWidget(self.send_btn, 0, Qt.AlignBottom)
        layout.addLayout(input_row)

        # A thin collapse strip on the LEFT edge: click to fold the panel
        # to a sliver and click again to expand it (like a sidebar).
        outer = QWidget()
        row = QHBoxLayout(outer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._collapsed = False
        self._expanded_w = 360
        self.collapse_btn = QToolButton()
        self.collapse_btn.setAutoRaise(True)
        self.collapse_btn.setArrowType(Qt.RightArrow)
        self.collapse_btn.setToolTip("Collapse the chat panel")
        self.collapse_btn.setFixedWidth(16)
        self.collapse_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.collapse_btn.clicked.connect(self._toggle_collapse)
        row.addWidget(self.collapse_btn)
        row.addWidget(body, 1)
        self.setWidget(outer)

        self.input.submitted.connect(self._send)
        self.input.history_prev.connect(self._history_prev)
        self.input.history_next.connect(self._history_next)
        self.input.image_pasted.connect(self._attach_image)

        self._apply_font()
        self._update_status()
        self._load_history()

    def _toggle_collapse(self):
        """Fold the panel to a thin edge strip, or expand it back."""
        main = self.parent() if isinstance(self.parent(), QMainWindow) else None
        if not self._collapsed:
            self._expanded_w = max(self.width(), 220)
            self.body.setVisible(False)
            self.collapse_btn.setArrowType(Qt.LeftArrow)
            self.collapse_btn.setToolTip("Expand the chat panel")
            self.setFixedWidth(self.collapse_btn.width() + 6)
            self._collapsed = True
        else:
            self.setMinimumWidth(0)
            self.setMaximumWidth(16777215)
            self.body.setVisible(True)
            self.collapse_btn.setArrowType(Qt.RightArrow)
            self.collapse_btn.setToolTip("Collapse the chat panel")
            self._collapsed = False
            if main is not None:
                main.resizeDocks([self], [self._expanded_w], Qt.Horizontal)

    def _tool(self, text, tip, slot, glyph=None):
        btn = QToolButton()
        if glyph:
            btn.setIcon(icons.icon(glyph))
        if text:
            btn.setText(text)
        btn.setToolTip(tip)
        btn.setAutoRaise(True)
        btn.clicked.connect(slot)
        return btn

    # ------------------------------------------------------- image attach
    def _attach_image(self, image):
        """Hold a pasted screenshot to send with the next message."""
        if image is None or image.isNull():
            return
        self._pending_image = image
        self.attach_thumb.setPixmap(QPixmap.fromImage(image).scaledToHeight(
            36, Qt.SmoothTransformation))
        self.attach_label.setText(f"Screenshot attached "
                                  f"({image.width()}×{image.height()})")
        self.attach_row.setVisible(True)

    def _clear_image(self):
        self._pending_image = None
        self.attach_thumb.clear()
        self.attach_row.setVisible(False)

    @staticmethod
    def _image_to_b64(image) -> str:
        from PyQt5.QtCore import QBuffer, QByteArray
        import base64
        data = QByteArray()
        buf = QBuffer(data)
        buf.open(QBuffer.WriteOnly)
        image.save(buf, "PNG")
        buf.close()
        return base64.b64encode(bytes(data)).decode("ascii")

    # ------------------------------------------------------- settings
    def _open_settings(self):
        if AiSettingsDialog(self).exec_():
            self._update_status()

    def _update_status(self):
        provider = self._settings.value("ai/provider", "Claude")
        self.provider_label.setText(
            providers.DISPLAY_NAMES.get(provider, provider))

    def _change_font(self, delta):
        self._font_pt = max(7, min(28, self._font_pt + delta))
        self._settings.setValue("ai/fontpt", self._font_pt)
        self._apply_font()

    def _apply_font(self):
        for widget in (self.transcript, self.input):
            font = widget.font()
            font.setPointSize(self._font_pt)
            widget.setFont(font)

    # ------------------------------------------------------- persistence
    def _save_history(self):
        # keep the last 100 turns so the store stays small
        self._settings.setValue("ai/history",
                                json.dumps(self._history[-100:]))
        self._settings.sync()           # flush now so a hard close keeps it

    def _load_history(self):
        raw = self._settings.value("ai/history", "")
        try:
            self._history = json.loads(raw) if raw else []
        except (ValueError, TypeError):
            self._history = []
        self._sent = [m["content"] for m in self._history
                      if m.get("role") == "user"]
        if self._history:
            for msg in self._history:
                if msg.get("role") == "user":
                    self._log("you", msg.get("content", ""))
                elif msg.get("role") == "assistant":
                    prose = prose_only(msg.get("content", ""))
                    self._log("ai", prose or "(shapes)")
        else:
            self._welcome()

    def _welcome(self):
        self._log("system",
                  "Hello! I can help you build your drawing — ask me to add "
                  "shapes, a flowchart or a diagram and I'll place them on "
                  "the canvas. Set your provider (Anthropic, OpenAI, Mistral, "
                  "Ollama or Local) and API key via the gear icon.")

    def _show_help(self):
        self._log("system",
                  "Describe what to draw, e.g. “a blue box labelled Start "
                  "with an arrow to a circle below”. Shapes are added as real, "
                  "editable, undoable items. A−/A+ resize this text; the "
                  "gear sets the provider/model/key; the last icon clears the "
                  "chat.")

    def _clear(self):
        self.transcript.clear()
        self._history = []
        self._sent = []
        self._hist_index = None
        self._draft = ""
        self._save_history()
        self._welcome()

    # ------------------------------------------------------- transcript
    def _log(self, role, text):
        colours = {"you": "#2176c7", "ai": "#2e7d4f",
                   "system": "#888", "error": "#c0392b"}
        who = {"you": "You", "ai": "Assistant", "system": "",
               "error": "Error"}.get(role, role)
        prefix = f"<b style='color:{colours.get(role, '#000')}'>{who}:</b> " \
            if who else ""
        safe = (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("\n", "<br>"))
        self.transcript.append(f"<div style='margin:4px 0;'>{prefix}{safe}</div>")

    def _busy(self, busy):
        self._is_busy = busy
        if busy:
            self._think_dots = 0
            self.thinking_label.setText("Assistant is thinking")
            self.thinking_label.setVisible(True)
            self._think_timer.start()
            self.send_btn.setIcon(icons.icon("mdi.stop"))
            self.send_btn.setToolTip("Stop")
        else:
            self._think_timer.stop()
            self.thinking_label.setVisible(False)
            self.send_btn.setIcon(icons.icon("mdi.send"))
            self.send_btn.setToolTip("Send")

    def _tick(self):
        self._think_dots = (self._think_dots + 1) % 4
        self.thinking_label.setText("Assistant is thinking"
                                    + "." * self._think_dots)

    def _send_or_stop(self):
        self._stop() if self._is_busy else self._send()

    def _stop(self):
        """Abandon the in-flight request (its late result is ignored)."""
        if self._worker is not None:
            for sig in (self._worker.done, self._worker.failed):
                try:
                    sig.disconnect()
                except TypeError:
                    pass
            self._worker = None
        self._busy(False)
        self._log("system", "Stopped.")

    # ------------------------------------------------------- history
    def _history_prev(self):
        if not self._sent:
            return
        if self._hist_index is None:
            self._draft = self.input.toPlainText()
            self._hist_index = len(self._sent) - 1
        elif self._hist_index > 0:
            self._hist_index -= 1
        self._set_input(self._sent[self._hist_index])

    def _history_next(self):
        if self._hist_index is None:
            return
        if self._hist_index < len(self._sent) - 1:
            self._hist_index += 1
            self._set_input(self._sent[self._hist_index])
        else:
            self._hist_index = None
            self._set_input(self._draft)

    def _set_input(self, text):
        self.input.setPlainText(text)
        cursor = self.input.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.input.setTextCursor(cursor)

    # ------------------------------------------------------- actions
    def _send(self):
        if self._is_busy:
            return
        text = self.input.toPlainText().strip()
        if not text and self._pending_image is None:
            return
        provider = self._settings.value("ai/provider", "Claude")
        model = self._settings.value(f"ai/model/{provider}", "")
        key = self._settings.value(f"ai/key/{provider}", "")
        base = self._settings.value(f"ai/base/{provider}", "")
        if not model:
            self._log("error", "Open Settings and choose a model first.")
            return
        if provider in providers.NEEDS_KEY and not key.strip():
            self._log("error", "Set your API key for this provider in "
                              "Settings (the gear icon).")
            return
        # A pasted screenshot is sent with THIS message only (not stored in
        # history, which stays text). Clear the attachment once consumed.
        image_b64 = None
        if self._pending_image is not None:
            image_b64 = self._image_to_b64(self._pending_image)
            self._clear_image()

        self.input.clear()
        self._sent.append(text)
        self._hist_index = None
        self._draft = ""
        self._log("you", text + ("  🖼 [screenshot]" if image_b64 else ""))
        self._history.append({"role": "user", "content": text or "(image)"})
        self._save_history()

        rect = self.scene.sceneRect()
        # Substitute the placeholders with str.replace, NOT str.format — the
        # prompt now contains literal JSON braces ({"shape":…}) as examples,
        # which str.format would misread as fields and raise.
        system = (SYSTEM_PROMPT
                  .replace("{w}", str(int(rect.width())))
                  .replace("{h}", str(int(rect.height())))
                  .replace("{summary}", _scene_summary(self.scene)))
        messages = [{"role": "system", "content": system}] + self._history
        self._busy(True)
        self._run(lambda: providers.chat(provider, model, messages, key, base,
                                         image=image_b64),
                  self._reply_ready)

    def _reply_ready(self, reply):
        self._busy(False)
        self._history.append({"role": "assistant", "content": reply})
        self._save_history()
        specs = extract_specs(reply)
        # Show only the prose, never the raw JSON block (even if truncated).
        prose = prose_only(reply)
        if specs:
            created = apply_specs(self.scene, specs)
            self._log("ai", prose or "Done.")
            self._log("system", f"Drew {len(created)} shape(s) on the canvas.")
        else:
            self._log("ai", prose or reply)

    # ------------------------------------------------------- threading
    def _run(self, fn, on_done):
        worker = _Worker(fn, self)
        worker.done.connect(on_done)
        worker.failed.connect(self._on_error)
        worker.finished.connect(lambda: self._clear_worker(worker))
        self._worker = worker
        worker.start()

    def _on_error(self, message):
        self._busy(False)
        self._log("error", message)

    def _clear_worker(self, worker):
        if self._worker is worker:
            self._worker = None
