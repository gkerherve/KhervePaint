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
    app.setApplicationName("KhervePaint")

    from .style import apply_style
    apply_style(app)

    from .mainwindow import MainWindow
    win = MainWindow()
    win.show()

    # A file path on the command line (e.g. from KherveBook's "Open in
    # KhervePaint") opens straight away, so the drawing is ready to edit.
    for arg in app.arguments()[1:]:
        if not arg.startswith("-") and Path(arg).exists():
            win.open_path(arg)
            break

    win.start_mcp_if_enabled()

    sys.exit(app.exec_())
