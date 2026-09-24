"""Qt side of the auto-updater: background check, dialog, download.

`UpdateManager` is owned by the main window. At start-up it checks
silently (once a day, unless turned off in Help ▸ Automatically check for
updates) and only speaks up when there is something new that the user has
not chosen to skip; Help ▸ Check for Updates… checks now and always
reports. All network work runs on a `QThread` so the window never stalls.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import sys
import time

from PyQt5.QtCore import QObject, QSettings, Qt, QThread, QTimer, QUrl, \
    pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QLabel,
                             QMessageBox, QPlainTextEdit, QProgressDialog,
                             QPushButton, QVBoxLayout)

from . import updater

SETTINGS = ("Kherve", "KhervePaint")
KEY_AUTO = "updates/auto"
KEY_LAST = "updates/last_check"
KEY_SKIP = "updates/skip"
STARTUP_DELAY_MS = 4000       # let the window settle before touching the net


class _Worker(QThread):
    """Runs one callable off the GUI thread and hands back its result."""
    done = pyqtSignal(object)
    progress = pyqtSignal(int, int)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
        self.cancelled = False

    def run(self):
        try:
            result = self._fn(self)
        except Exception as exc:
            result = exc
        self.done.emit(result)


class UpdateDialog(QDialog):
    """What's new + Install / Skip this version / Later."""
    INSTALL, SKIP = 10, 11

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Update available")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        if info["kind"] == "git":
            head = (f"<b>{info['behind']} new commit(s)</b> on "
                    f"<code>{info['upstream']}</code>.<br>You have "
                    f"{info['current']}. Update pulls them into this "
                    "source checkout (fast-forward only — local changes are "
                    "never overwritten).")
        else:
            a = info["asset"]
            size = f" ({a['size'] / 1e6:.0f} MB)" if a.get("size") else ""
            head = (f"<b>KhervePaint {info['latest']}</b> is available — "
                    f"you have {info['current']}.<br>Update downloads "
                    f"<code>{a['name']}</code>{size} and starts it.")
        label = QLabel(head)
        label.setWordWrap(True)
        label.setTextFormat(Qt.RichText)
        lay.addWidget(label)
        notes = info.get("notes") or (info.get("asset") or {}).get("notes")
        if notes:
            box = QPlainTextEdit(notes)
            box.setReadOnly(True)
            box.setMaximumHeight(180)
            lay.addWidget(box)
        buttons = QDialogButtonBox()
        install = QPushButton("Update now")
        install.setDefault(True)
        buttons.addButton(install, QDialogButtonBox.AcceptRole)
        skip = buttons.addButton("Skip this version",
                                 QDialogButtonBox.DestructiveRole)
        buttons.addButton("Later", QDialogButtonBox.RejectRole)
        install.clicked.connect(lambda: self.done(self.INSTALL))
        skip.clicked.connect(lambda: self.done(self.SKIP))
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)


class UpdateManager(QObject):
    """Owns the checks for one window."""

    def __init__(self, window):
        super().__init__(window)
        self._win = window
        self._worker = None

    # ── settings ──────────────────────────────────────────────
    @staticmethod
    def _settings():
        return QSettings(*SETTINGS)

    def auto_enabled(self) -> bool:
        return self._settings().value(KEY_AUTO, True, type=bool)

    def set_auto(self, on: bool):
        self._settings().setValue(KEY_AUTO, bool(on))

    # ── checking ──────────────────────────────────────────────
    def schedule_startup_check(self):
        """A quiet check a few seconds after start-up, at most daily."""
        s = self._settings()
        if not self.auto_enabled():
            return
        if not updater.due(s.value(KEY_LAST, 0.0, type=float)):
            return
        QTimer.singleShot(STARTUP_DELAY_MS, lambda: self.check(quiet=True))

    def check(self, quiet=False):
        if self._worker is not None and self._worker.isRunning():
            return
        if not quiet:
            self._status("Checking for updates…")
        self._worker = _Worker(lambda _w: updater.check(), self)
        self._worker.done.connect(lambda r: self._checked(r, quiet))
        self._worker.start()

    def _checked(self, result, quiet):
        self._settings().setValue(KEY_LAST, time.time())
        if isinstance(result, Exception):
            result = {"status": "error", "message": str(result)}
        status = result.get("status")
        if status == "update":
            latest = updater.build_number(result.get("latest")) or 0
            skipped = self._settings().value(KEY_SKIP, 0, type=int)
            if quiet and latest and latest <= skipped:
                return
            self._status(f"KhervePaint {result.get('latest')} is available.")
            self._offer(result)
        elif quiet:
            return                               # say nothing at start-up
        elif status == "current":
            self._status("KhervePaint is up to date.")
            QMessageBox.information(
                self._win, "Check for updates",
                f"You have the latest version ({result.get('current')}).")
        else:
            QMessageBox.information(self._win, "Check for updates",
                                    result.get("message", "Unknown error."))

    def _offer(self, info):
        choice = UpdateDialog(info, self._win).exec_()
        if choice == UpdateDialog.SKIP:
            self._settings().setValue(
                KEY_SKIP, updater.build_number(info.get("latest")) or 0)
        elif choice == UpdateDialog.INSTALL:
            if info["kind"] == "git":
                self._pull()
            else:
                self._download(info["asset"])

    # ── installing ────────────────────────────────────────────
    def _pull(self):
        ok, out = updater.git_pull()
        if ok:
            QMessageBox.information(
                self._win, "Updated",
                "KhervePaint was updated. Restart it to use the new "
                "version.\n\n" + out[-800:])
        else:
            QMessageBox.warning(
                self._win, "Update failed",
                "git pull could not fast-forward (local changes or a "
                "diverged branch?). Nothing was changed.\n\n" + out[-800:])

    def _download(self, asset):
        dest = updater.download_dir() / asset["name"]
        dlg = QProgressDialog(f"Downloading {asset['name']}…", "Cancel",
                              0, 100, self._win)
        dlg.setWindowTitle("Updating KhervePaint")
        dlg.setWindowModality(Qt.WindowModal)
        dlg.setMinimumDuration(0)
        dlg.setValue(0)

        def job(worker):
            def progress(done, total):
                worker.progress.emit(done, total)
                return not worker.cancelled
            return updater.download(asset["url"], dest, progress)

        worker = _Worker(job, self)
        self._worker = worker

        def on_progress(done, total):
            if total:
                dlg.setValue(int(done * 100 / total))

        worker.progress.connect(on_progress)
        dlg.canceled.connect(lambda: setattr(worker, "cancelled", True))
        worker.done.connect(lambda r: self._downloaded(r, dlg, asset))
        worker.start()

    def _downloaded(self, result, dlg, asset):
        dlg.reset()
        if isinstance(result, InterruptedError):
            return
        if isinstance(result, Exception):
            box = QMessageBox(QMessageBox.Warning, "Update failed",
                              f"The download failed: {result}",
                              QMessageBox.Close, self._win)
            page = box.addButton("Open download page",
                                 QMessageBox.ActionRole)
            box.exec_()
            if box.clickedButton() is page:
                QDesktopServices.openUrl(QUrl(asset.get("page")
                                              or updater.RELEASES_PAGE))
            return
        # The Windows installer replaces the running files, so the app
        # quits for it — but never over unsaved work without asking.
        if sys.platform.startswith("win") and \
                not self._win._confirm_discard():
            return
        quit_app = updater.launch_installer(result)
        if quit_app:
            QApplication.quit()
        else:
            QMessageBox.information(
                self._win, "Install the update",
                "The new version has been opened in Finder: drag "
                "KhervePaint onto Applications (replace the old one), "
                "then restart it.")

    def add_menu_actions(self, menu):
        """Help ▸ Check for Updates… and the automatic-check toggle."""
        menu.addAction("Check for &Updates…", lambda: self.check(quiet=False))
        auto = menu.addAction("Automatically check for updates")
        auto.setCheckable(True)
        auto.setChecked(self.auto_enabled())
        auto.toggled.connect(self.set_auto)

    def _status(self, text):
        try:
            self._win.statusBar().showMessage(text, 6000)
        except RuntimeError:
            pass
