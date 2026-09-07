"""Shared pytest configuration.

KhervePaint persists provider API keys, recent files, the theme and the
AI chat history in QSettings under ("Kherve", "KhervePaint"). On Windows
that two-argument scope resolves to the user's real registry **even with
setDefaultFormat(IniFormat)** — so a naive isolation attempt fails and
the suite clobbers the developer's real settings (notably wiping the
saved AI chat on every run).

Each app module imports `QSettings` into its own namespace and builds it
from a module-level scope constant, so we redirect those names to a
factory that returns a throwaway INI file in a temp dir. Every app
setting then lives in one temp file and the real registry is never
touched. This runs at import time, before any test module.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import os
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QSettings

from khervepaint import ai_assistant, mainwindow, mcp_dialog, style

_TEST_SETTINGS_FILE = os.path.join(
    tempfile.mkdtemp(prefix="khervepaint-test-settings-"), "settings.ini")


def _isolated_settings(*_args, **_kwargs):
    """Drop-in for QSettings(org, app): one shared throwaway INI file."""
    return QSettings(_TEST_SETTINGS_FILE, QSettings.IniFormat)


# Redirect every app module's QSettings to the temp file.
for _module in (ai_assistant, mainwindow, mcp_dialog, style):
    _module.QSettings = _isolated_settings


import pytest
from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="session")
def paint_window(qapp):
    """ONE MainWindow for the whole session.

    A window per test churns through QMainWindows, and one collected
    while its scene or undo stack still has signals in flight raises
    inside a Qt slot — which PyQt turns into an abort of the whole run,
    not a test failure. Tests that need a window share this one and
    reset it (see the `win` fixture).
    """
    from khervepaint.mainwindow import MainWindow
    return MainWindow()


@pytest.fixture
def win(paint_window):
    """The shared window, reset to a blank document for this test."""
    from khervepaint import canvassize
    w, h, dpi = canvassize.default_size()
    paint_window.scene.new_document(w, h)
    paint_window.scene.dpi = dpi
    paint_window.scene.snap_enabled = True
    paint_window.scene.grid_mm = 1.0
    paint_window._path = None
    paint_window._reset_history()
    return paint_window
