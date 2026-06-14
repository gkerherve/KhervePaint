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

from PyQt5.QtCore import QLineF, QRectF, QSettings, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QPen
from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox,
                             QDockWidget, QFormLayout, QGroupBox, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
                             QPushButton, QTextBrowser, QToolButton,
                             QVBoxLayout, QWidget)

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

        header = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color:#888;")
        self.settings_btn = QPushButton(icons.icon("mdi.cog-outline"),
                                        " Settings")
        header.addWidget(self.status_label, 1)
        header.addWidget(self.settings_btn)
        layout.addLayout(header)

        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(True)
        layout.addWidget(self.transcript, 1)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText(
            "Ask me to draw… e.g. “a blue flowchart box labelled Start "
            "with an arrow to a circle below it”")
        self.input.setFixedHeight(64)
        layout.addWidget(self.input)
        self.send_btn = QPushButton("Send")
        layout.addWidget(self.send_btn)

        self.setWidget(body)

        self.settings_btn.clicked.connect(self._open_settings)
        self.send_btn.clicked.connect(self._send)

        self._update_status()
        self._log("system", "Click Settings to choose a provider and enter "
                            "your API key, then ask me to draw something.")

    # ------------------------------------------------------- settings
    def _open_settings(self):
        if AiSettingsDialog(self).exec_():
            self._update_status()

    def _update_status(self):
        provider = self._settings.value("ai/provider", "Claude")
        model = self._settings.value(f"ai/model/{provider}", "no model")
        self.status_label.setText(
            f"{providers.DISPLAY_NAMES.get(provider, provider)} · {model}")

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

    # ------------------------------------------------------- actions
    def _send(self):
        text = self.input.toPlainText().strip()
        if not text:
            return
        provider = self._settings.value("ai/provider", "Claude")
        model = self._settings.value(f"ai/model/{provider}", "")
        key = self._settings.value(f"ai/key/{provider}", "")
        base = self._settings.value(f"ai/base/{provider}", "")
        if not model:
            self._log("error", "Open Settings and choose a model first.")
            return
        self.input.clear()
        self._log("you", text)
        self._history.append({"role": "user", "content": text})

        rect = self.scene.sceneRect()
        system = SYSTEM_PROMPT.format(
            w=int(rect.width()), h=int(rect.height()),
            summary=_scene_summary(self.scene))
        messages = [{"role": "system", "content": system}] + self._history
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
