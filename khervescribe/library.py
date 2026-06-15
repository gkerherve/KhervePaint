"""Reusable-object library: save selections as SVG, list and load them.

Saved objects are standalone SVG files in a per-user folder. The left
toolbar's Objects dropdown lists them by file name (so a "wall.svg"
appears as "wall") and inserts a fresh, editable copy onto the canvas.
The folder can be overridden for tests via KHERVESCRIBE_OBJECTS_DIR.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import math
import os
import shutil
from pathlib import Path

from PyQt5.QtCore import QRectF, QStandardPaths
from PyQt5.QtGui import QPixmap

from . import document, svgio
from .canvas import PaintScene


def objects_dir() -> Path:
    """The folder holding saved objects, created on first use."""
    override = os.environ.get("KHERVESCRIBE_OBJECTS_DIR")
    if override:
        path = Path(override)
    else:
        base = QStandardPaths.writableLocation(
            QStandardPaths.AppDataLocation) or str(Path.home() / ".khervescribe")
        path = Path(base) / "objects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_name(name: str) -> str:
    """A filesystem-friendly base name derived from a user-typed label."""
    keep = "".join(c for c in name.strip()
                   if c.isalnum() or c in " _-()").strip()
    return keep or "object"


def _parts(rel) -> list:
    """Normalise a folder reference (tuple/list, or '/'-joined string) to a
    list of safe folder names, relative to the objects root."""
    if rel is None:
        return []
    seq = rel if isinstance(rel, (tuple, list)) else str(rel).split("/")
    return [_safe_name(x) for x in seq if str(x).strip() not in ("", ".")]


def folder_path(rel) -> Path:
    """Absolute path of a (relative) folder under the objects root."""
    return objects_dir().joinpath(*_parts(rel))


def list_objects():
    """[(name, path), ...] for objects at the TOP level, sorted by name."""
    return sorted(((p.stem, p) for p in objects_dir().glob("*.svg")),
                  key=lambda np: np[0].lower())


def list_folders():
    """Every sub-folder as a relative-parts tuple, sorted (parents first)."""
    root = objects_dir()
    return sorted((p.relative_to(root).parts
                   for p in root.rglob("*") if p.is_dir()))


def iter_objects():
    """(rel_parts, name, path) for every object anywhere under the root,
    where rel_parts is the tuple of sub-folder names containing it."""
    root = objects_dir()
    out = []
    for p in sorted(root.rglob("*.svg")):
        rel = p.parent.relative_to(root)
        out.append((() if str(rel) == "." else rel.parts, p.stem, p))
    return out


def create_folder(rel) -> Path:
    path = folder_path(rel)
    path.mkdir(parents=True, exist_ok=True)
    return path


def rename_object(path, new_name: str) -> Path:
    path = Path(path)
    dest = path.with_name(_safe_name(new_name) + ".svg")
    if dest != path:
        path.rename(dest)
    return dest


def move_object(path, rel_folder) -> Path:
    dest_dir = create_folder(rel_folder)
    dest = dest_dir / Path(path).name
    Path(path).rename(dest)
    return dest


def rename_folder(rel, new_name) -> Path:
    src = folder_path(rel)
    if src == objects_dir():
        return src
    dest = src.with_name(_safe_name(new_name))
    if dest != src:
        src.rename(dest)
    return dest


def delete_object(path):
    Path(path).unlink(missing_ok=True)


def delete_folder(rel):
    path = folder_path(rel)
    if path != objects_dir() and path.exists():
        shutil.rmtree(path)


def save_object(item_dicts, name: str, dpi: int = 96, folder=()) -> Path:
    """Write serialised *item_dicts* to <objects_dir>/<folder>/<name>.svg,
    cropped to their bounding box, and return the path. A '/' in *name*
    is treated as folder separators. The object carries no raster layer."""
    *name_folder, leaf = name.split("/") if "/" in name else [name]
    folder = list(_parts(folder)) + name_folder

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

    path = create_folder(folder) / f"{_safe_name(leaf)}.svg"
    svgio.save_svg(scene, str(path))
    return path


def load_object(path) -> list:
    """Parse an object SVG into serialised item dicts ready for
    `document.item_from_dict` / paste-style insertion."""
    scene = PaintScene()
    svgio.load_svg(scene, str(path))
    return [document.item_to_dict(i) for i in scene.vector_items()]
