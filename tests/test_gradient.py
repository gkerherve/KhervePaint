"""Gradient-fill round-trip tests (JSON snapshot + SVG file).

Run with: python -m pytest tests/  (offscreen Qt).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication

from khervescribe import document, gradient, svgio
from khervescribe.canvas import EllipseItem, PaintScene, RectItem


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(400, 300)


def _gradient_items(scene):
    rect = RectItem(QRectF(10, 10, 100, 60))
    rect.setBrush(gradient.linear_brush(QColor("#ff0000"),
                                        QColor("#0000ff"), 45.0))
    scene.addItem(rect)
    ell = EllipseItem(QRectF(150, 40, 80, 80))
    ell.setBrush(gradient.radial_brush(QColor("#00ff00"),
                                       QColor("#000000")))
    scene.addItem(ell)


def _specs(scene):
    out = {}
    for item in scene.vector_items():
        spec = gradient.brush_spec(item.brush())
        if spec:
            out[spec["kind"]] = spec
    return out


def test_spec_round_trip():
    spec = gradient.brush_spec(
        gradient.linear_brush(QColor("#102030"), QColor("#a0b0c0"), 30.0))
    assert spec["kind"] == "linear"
    assert abs(spec["angle"] - 30.0) < 0.1
    back = gradient.brush_spec(gradient.brush_from_spec(spec))
    assert back == spec


def test_json_snapshot_round_trip(scene, app):
    _gradient_items(scene)
    data = document.scene_to_dict(scene)
    restored = PaintScene(400, 300)
    document.dict_to_scene(data, restored)
    specs = _specs(restored)
    assert specs["linear"]["c1"] == "#ffff0000"
    assert specs["linear"]["c2"] == "#ff0000ff"
    assert abs(specs["linear"]["angle"] - 45.0) < 0.1
    assert specs["radial"]["c1"] == "#ff00ff00"


def test_svg_round_trip(scene, app, tmp_path):
    _gradient_items(scene)
    path = str(tmp_path / "grad.svg")
    svgio.save_svg(scene, path)
    text = Path(path).read_text(encoding="utf-8")
    assert "linearGradient" in text and "radialGradient" in text
    restored = PaintScene(400, 300)
    svgio.load_svg(restored, path)
    specs = _specs(restored)
    assert specs["linear"]["c1"] == "#ffff0000"
    assert specs["linear"]["c2"] == "#ff0000ff"
    assert abs(specs["linear"]["angle"] - 45.0) < 0.5
    assert specs["radial"]["c1"] == "#ff00ff00"
    assert specs["radial"]["c2"] == "#ff000000"


def test_external_svg_gradient_imports(app, tmp_path):
    """A foreign SVG with href-chained stops (Inkscape style) imports."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg"
      xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 100 100">
      <defs>
        <linearGradient id="base">
          <stop offset="0" style="stop-color:#ff0000"/>
          <stop offset="1" style="stop-color:#0000ff"/>
        </linearGradient>
        <linearGradient id="g1" xlink:href="#base"
          x1="0" y1="0" x2="0" y2="1"/>
      </defs>
      <rect x="10" y="10" width="50" height="40" fill="url(#g1)"/>
    </svg>"""
    path = tmp_path / "ext.svg"
    path.write_text(svg, encoding="utf-8")
    scene = PaintScene(100, 100)
    svgio.load_svg(scene, str(path))
    specs = _specs(scene)
    assert specs["linear"]["c1"] == "#ffff0000"
    assert specs["linear"]["c2"] == "#ff0000ff"
    assert abs(specs["linear"]["angle"] - 90.0) < 0.5
