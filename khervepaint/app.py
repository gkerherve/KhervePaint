"""Application entry: QApplication setup, crash log, Fusion style.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import faulthandler
import sys
import tempfile
from pathlib import Path

from PyQt5.QtWidgets import QApplication

CRASH_LOG = Path(tempfile.gettempdir()) / "khervepaint_crash.log"


def main():
    # An MCP host launches us as a plain stdio subprocess it owns.  That
    # half must not build a QApplication (or a window), so it forks off
    # before anything Qt happens.
    if "--mcp-server" in sys.argv[1:]:
        from .mcp_server import main as mcp_main
        sys.exit(mcp_main([a for a in sys.argv[1:] if a != "--mcp-server"]))

    crash_file = open(CRASH_LOG, "w")
    faulthandler.enable(file=crash_file)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setOrganizationName("Kherve")
    app.setApplicationName("KhervePaint")

    from .i18n import apply_saved_language
    apply_saved_language(app)

    from .style import apply_style
    apply_style(app)

    # the start-up picture: the window's modules take a moment to load
    from .splash import Splash
    splash = Splash()
    splash.show()
    splash.step("Loading the canvas")
    from .mainwindow import MainWindow
    splash.step("Building the window")
    win = MainWindow()
    splash.step("Opening the workspace")
    win.show()

    # A file path on the command line (e.g. from KherveBook's "Open in
    # KhervePaint") opens straight away, so the drawing is ready to edit.
    opened = False
    for arg in app.arguments()[1:]:
        if not arg.startswith("-") and Path(arg).exists():
            opened = win.open_path(arg)
            break

    # the start-up wallpaper, unless a file is already open
    from .welcome import show_at_startup
    if not opened and show_at_startup():
        win.show_welcome()

    win.start_mcp_if_enabled()
    win.updates.schedule_startup_check()
    splash.step("Ready")
    splash.finish(win)

    sys.exit(app.exec_())
