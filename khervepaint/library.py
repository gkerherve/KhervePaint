"""Reusable-object library: save selections as SVG, list and load them.

Saved objects are standalone SVG files in a per-user folder. The left
toolbar's Objects dropdown lists them by file name (so a "wall.svg"
appears as "wall") and inserts a fresh, editable copy onto the canvas.
The folder can be overridden for tests via KHERVEPAINT_OBJECTS_DIR.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math
import os
from pathlib import Path

from PyQt5.QtCore import QRectF, QStandardPaths
from PyQt5.QtGui import QPixmap

from . import document, svgio
from .canvas import PaintScene


def objects_dir() -> Path:
    """The folder holding saved objects, created on first use."""
    override = os.environ.get("KHERVEPAINT_OBJECTS_DIR")
    if override:
        path = Path(override)
    else:
        base = QStandardPaths.writableLocation(
            QStandardPaths.AppDataLocation) or str(Path.home() / ".khervepaint")
        path = Path(base) / "objects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_name(name: str) -> str:
    """A filesystem-friendly base name derived from a user-typed label."""
    keep = "".join(c for c in name.strip()
                   if c.isalnum() or c in " _-()").strip()
    return keep or "object"


def list_objects():
    """[(name, path), ...] for every saved object, sorted by name."""
    return sorted(((p.stem, p) for p in objects_dir().glob("*.svg")),
                  key=lambda np: np[0].lower())


def save_object(item_dicts, name: str, dpi: int = 96) -> Path:
    """Write serialised *item_dicts* to <objects_dir>/<name>.svg, cropped
    to their bounding box, and return the path. The object carries no
    raster layer."""
    scene = PaintScene()
    scene.dpi = dpi
    scene.raster_item.setPixmap(QPixmap())     # objects have no raster
    for d in item_dicts:
        scene.addItem(document.item_from_dict(d))

    items = scene.vector_items()
    rect = QRectF()
    for it in items:
        rect = rect.united(it.sceneBoundingRect())
    if not rect.isEmpty():
        for it in items:
            it.moveBy(-rect.left(), -rect.top())
        scene.setSceneRect(0, 0, int(math.ceil(rect.width())),
                           int(math.ceil(rect.height())))

    path = objects_dir() / f"{_safe_name(name)}.svg"
    svgio.save_svg(scene, str(path))
    return path


def load_object(path) -> list:
    """Parse an object SVG into serialised item dicts ready for
    `document.item_from_dict` / paste-style insertion."""
    scene = PaintScene()
    svgio.load_svg(scene, str(path))
    return [document.item_to_dict(i) for i in scene.vector_items()]
