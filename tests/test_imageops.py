"""Tests for imageops.remove_background (image -> transparent background).

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
from PyQt5.QtGui import QColor, QImage, QPainter
from PyQt5.QtWidgets import QApplication

from khervepaint.imageops import remove_background


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


def _sample(app):
    """White background, red subject, and a white hole inside the subject
    (which must survive — only border-connected background clears)."""
    img = QImage(40, 30, QImage.Format_ARGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    p.fillRect(10, 8, 20, 14, QColor("red"))
    p.fillRect(16, 12, 6, 4, QColor("white"))
    p.end()
    return img


def test_border_background_becomes_transparent(app):
    out = remove_background(_sample(app))
    assert out is not None
    assert out.pixelColor(0, 0).alpha() == 0          # corner cleared
    assert out.pixelColor(39, 29).alpha() == 0        # far corner too
    assert out.pixelColor(12, 10).alpha() == 255      # subject kept
    assert out.pixelColor(12, 10).red() == 255


def test_interior_same_colour_region_is_kept(app):
    out = remove_background(_sample(app))
    hole = out.pixelColor(18, 13)                     # white hole in subject
    assert hole.alpha() == 255
    assert (hole.red(), hole.green(), hole.blue()) == (255, 255, 255)


def test_tiny_image_returns_none(app):
    img = QImage(1, 1, QImage.Format_ARGB32)
    img.fill(QColor("white"))
    assert remove_background(img) is None


def test_undoable_via_mainwindow(app):
    """remove_image_background emits changed_by_user -> a snapshot lands
    on the undo stack, and undo restores the opaque pixmap."""
    from PyQt5.QtGui import QPixmap
    from khervepaint.canvas import ImageItem
    from khervepaint.mainwindow import MainWindow
    win = MainWindow()
    try:
        item = ImageItem(QPixmap.fromImage(_sample(app)))
        win.scene.addItem(item)
        win.scene.changed_by_user.emit()              # item added
        before = win._undo_stack.count()
        win.remove_image_background(item)
        assert win._undo_stack.count() == before + 1
        assert item.pixmap().toImage().pixelColor(0, 0).alpha() == 0
        win._undo_stack.undo()
        images = [i for i in win.scene.vector_items()
                  if isinstance(i, ImageItem)]
        assert images
        assert images[0].pixmap().toImage().pixelColor(0, 0).alpha() == 255
    finally:
        win._undo_stack.setClean()
        win.close()
        app.processEvents()
        from PyQt5 import sip
        sip.delete(win)
        app.processEvents()
