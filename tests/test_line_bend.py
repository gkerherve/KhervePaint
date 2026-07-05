"""Bent (curved) line/arrow round-trip tests (JSON snapshot + SVG).

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
from PyQt5.QtCore import QLineF, QPointF
from PyQt5.QtWidgets import QApplication

from khervepaint import document, svgio
from khervepaint.canvas import ArrowItem, LineItem, PaintScene


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene(app):
    return PaintScene(400, 300)


def _bent_items(scene):
    line = LineItem(QLineF(10, 10, 200, 10))
    line.set_bend(QPointF(105, 80))
    scene.addItem(line)
    arrow = ArrowItem(QLineF(20, 100, 220, 100))
    arrow.set_bend(QPointF(120, 180))
    scene.addItem(arrow)
    straight = LineItem(QLineF(0, 200, 100, 250))
    scene.addItem(straight)


def _by_type(scene):
    out = {"line": [], "arrow": []}
    for item in scene.vector_items():
        if isinstance(item, ArrowItem):
            out["arrow"].append(item)
        elif isinstance(item, LineItem):
            out["line"].append(item)
    return out


def _assert_restored(scene):
    items = _by_type(scene)
    bends = sorted((i.bend() for i in items["line"]),
                   key=lambda b: b is not None)
    assert bends[0] is None                     # the straight line stays
    assert abs(bends[1].x() - 105) < 0.01
    assert abs(bends[1].y() - 80) < 0.01
    (arrow,) = items["arrow"]
    assert abs(arrow.bend().x() - 120) < 0.01
    assert abs(arrow.bend().y() - 180) < 0.01


def test_json_snapshot_round_trip(scene, app):
    _bent_items(scene)
    data = document.scene_to_dict(scene)
    restored = PaintScene(400, 300)
    document.dict_to_scene(data, restored)
    _assert_restored(restored)


def test_svg_round_trip(scene, app, tmp_path):
    _bent_items(scene)
    path = str(tmp_path / "bend.svg")
    svgio.save_svg(scene, path)
    text = Path(path).read_text(encoding="utf-8")
    assert " Q" in text or "Q1" in text          # curve emitted as a path
    restored = PaintScene(400, 300)
    svgio.load_svg(restored, path)
    _assert_restored(restored)


def test_mirror_flips_bend(scene, app):
    line = LineItem(QLineF(0, 0, 100, 0))
    line.set_bend(QPointF(50, 40))
    scene.addItem(line)
    line.setSelected(True)
    scene.mirror_selection(horizontal=False)     # flip about y-centre
    b = line.bend()
    assert abs(b.x() - 50) < 0.01
    assert abs(b.y() - (-20)) < 0.01             # reflected about y=10

    scene.mirror_selection(horizontal=True)      # x-flip keeps bend.x = 50
    assert abs(line.bend().x() - 50) < 0.01


def test_straighten_clears_bend(app):
    line = LineItem(QLineF(0, 0, 100, 0))
    line.set_bend(QPointF(50, 40))
    assert line.bend() is not None
    line.set_bend(None)
    assert line.bend() is None
    d = document.item_to_dict(line)
    assert "bend" not in d
