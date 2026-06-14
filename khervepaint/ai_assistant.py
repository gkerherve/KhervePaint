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

from PyQt5.QtCore import QSettings, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtCore import QLineF, QRectF
from PyQt5.QtWidgets import (QComboBox, QDockWidget, QHBoxLayout, QLabel,
                             QLineEdit, QPlainTextEdit, QPushButton,
                             QTextBrowser, QVBoxLayout, QWidget)

from . import ai_providers as providers
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
Keep coordinates within the canvas."""


# ---------------------------------------------------------------- specs
def extract_specs(text: str):
    """Pull a JSON array of shape specs out of an assistant reply."""
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
    return []


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
        item.setPos(x, y)
        center_origin(item)
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
    return item


def apply_specs(scene, specs):
    """Create items from *specs* and add them (selected) to the scene."""
    items = []
    for spec in specs:
        try:
            item = _spec_to_item(spec)
        except Exception:
            item = None
        if item is not None:
            scene.addItem(item)
            items.append(item)
    if items:
        scene.clearSelection()
        for item in items:
            item.setSelected(True)
        scene.changed_by_user.emit()
    return items


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


# ---------------------------------------------------------------- dock
class AiDock(QDockWidget):
    def __init__(self, scene, parent=None):
        super().__init__("AI Assistant", parent)
        self.scene = scene
        self.setObjectName("AiAssistant")
        self._worker = None
        self._history = []
        self._settings = QSettings(*_SETTINGS)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(6, 6, 6, 6)

        row = QHBoxLayout()
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(providers.PROVIDERS)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setMinimumWidth(120)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("List the models this provider offers")
        row.addWidget(self.provider_combo)
        row.addWidget(self.model_combo, 1)
        row.addWidget(self.refresh_btn)
        layout.addLayout(row)

        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("API key")
        layout.addWidget(self.key_edit)
        self.base_edit = QLineEdit()
        self.base_edit.setPlaceholderText("Base URL (Local / Ollama)")
        layout.addWidget(self.base_edit)

        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(True)
        layout.addWidget(self.transcript, 1)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(
            "Ask me to draw… e.g. “draw a blue flowchart box with the "
            "label Start and an arrow to a circle below it”")
        self.input.setFixedHeight(64)
        layout.addWidget(self.input)
        self.send_btn = QPushButton("Send")
        layout.addWidget(self.send_btn)

        self.setWidget(body)

        self.provider_combo.currentTextChanged.connect(self._load_provider)
        self.model_combo.currentTextChanged.connect(self._save_model)
        self.key_edit.editingFinished.connect(self._save_settings)
        self.base_edit.editingFinished.connect(self._save_settings)
        self.refresh_btn.clicked.connect(self._refresh_models)
        self.send_btn.clicked.connect(self._send)

        saved = self._settings.value("ai/provider", "Claude")
        if saved in providers.PROVIDERS:
            self.provider_combo.setCurrentText(saved)
        self._load_provider(self.provider_combo.currentText())
        self._log("system", "Pick a provider, set its API key, then ask me "
                            "to draw something. Use Refresh to list models.")

    # ------------------------------------------------------- settings
    def _provider(self):
        return self.provider_combo.currentText()

    def _load_provider(self, provider):
        self._settings.setValue("ai/provider", provider)
        self.key_edit.setText(self._settings.value(f"ai/key/{provider}", ""))
        self.base_edit.setText(self._settings.value(f"ai/base/{provider}", ""))
        self.key_edit.setEnabled(provider in providers.NEEDS_KEY)
        self.base_edit.setEnabled(provider in ("Local", "Ollama"))
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(providers.DEFAULT_MODELS.get(provider, []))
        saved_model = self._settings.value(f"ai/model/{provider}", "")
        if saved_model:
            self.model_combo.setCurrentText(saved_model)
        self.model_combo.blockSignals(False)

    def _save_model(self, model):
        if model:
            self._settings.setValue(f"ai/model/{self._provider()}", model)

    def _save_settings(self):
        provider = self._provider()
        self._settings.setValue(f"ai/key/{provider}", self.key_edit.text())
        self._settings.setValue(f"ai/base/{provider}", self.base_edit.text())

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
        self.send_btn.setEnabled(not busy)
        self.refresh_btn.setEnabled(not busy)

    # ------------------------------------------------------- actions
    def _refresh_models(self):
        provider = self._provider()
        key, base = self.key_edit.text(), self.base_edit.text()
        self._busy(True)
        self._log("system", f"Fetching {provider} models…")
        self._run(lambda: providers.list_models(provider, key, base),
                  self._models_ready)

    def _models_ready(self, models):
        self._busy(False)
        if not models:
            self._log("system", "No models returned.")
            return
        current = self.model_combo.currentText()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(models)
        self.model_combo.setCurrentText(current if current in models
                                        else models[0])
        self.model_combo.blockSignals(False)
        self._log("system", f"{len(models)} models available.")

    def _send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        provider = self._provider()
        model = self.model_combo.currentText().strip()
        if not model:
            self._log("error", "Choose a model first (try Refresh).")
            return
        self.input.clear()
        self._log("you", text)
        self._history.append({"role": "user", "content": text})

        rect = self.scene.sceneRect()
        system = SYSTEM_PROMPT.format(
            w=int(rect.width()), h=int(rect.height()),
            summary=_scene_summary(self.scene))
        messages = [{"role": "system", "content": system}] + self._history
        key, base = self.key_edit.text(), self.base_edit.text()
        self._busy(True)
        self._run(lambda: providers.chat(provider, model, messages, key, base),
                  self._reply_ready)

    def _reply_ready(self, reply):
        self._busy(False)
        self._history.append({"role": "assistant", "content": reply})
        self._log("ai", reply)
        specs = extract_specs(reply)
        if specs:
            created = apply_specs(self.scene, specs)
            self._log("system", f"Added {len(created)} shape(s) to the canvas.")

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
