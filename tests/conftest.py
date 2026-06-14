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

from khervepaint import ai_assistant, mainwindow, style

_TEST_SETTINGS_FILE = os.path.join(
    tempfile.mkdtemp(prefix="khervepaint-test-settings-"), "settings.ini")


def _isolated_settings(*_args, **_kwargs):
    """Drop-in for QSettings(org, app): one shared throwaway INI file."""
    return QSettings(_TEST_SETTINGS_FILE, QSettings.IniFormat)


# Redirect every app module's QSettings to the temp file.
for _module in (ai_assistant, mainwindow, style):
    _module.QSettings = _isolated_settings
