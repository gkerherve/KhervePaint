"""Start-up welcome wallpaper and the auto-updater's pure half.

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

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor, QImage, QPainter

from khervepaint import updater, welcome


# ── welcome screen ─────────────────────────────────────────────────

def test_wallpaper_paints(qapp):
    img = QImage(900, 600, QImage.Format_ARGB32)
    img.fill(QColor("white"))
    p = QPainter(img)
    welcome.paint_wallpaper(p, QRectF(0, 0, 900, 600))
    p.end()
    assert QColor(img.pixel(5, 5)).lightness() < 90       # dark backdrop
    # some decorative solid made it onto the right-hand side
    colours = {img.pixel(x, y) for x in range(600, 900, 7)
               for y in range(0, 600, 7)}
    assert len(colours) > 40


def test_welcome_overlays_and_dismisses(win):
    win.show_welcome()
    screen = win._welcome
    assert screen is not None and not screen.isHidden()
    assert screen.geometry() == win.view.rect()
    was_clean = win._undo_stack.isClean()
    screen.dismiss()
    assert win._welcome is None
    assert win._undo_stack.isClean() == was_clean      # never a doc change


def test_welcome_3d_tile_arms_the_solid_tool(win):
    from khervepaint.canvas import SOLID_PLACE
    win.show_welcome()
    win._welcome._three_d()
    assert win.scene.tool == SOLID_PLACE
    assert win.scene.solid_element == "cube"


def test_show_at_startup_setting_round_trips(qapp):
    welcome.set_show_at_startup(False)
    assert welcome.show_at_startup() is False
    welcome.set_show_at_startup(True)
    assert welcome.show_at_startup() is True


# ── updater ────────────────────────────────────────────────────────

_RELEASES = [
    {"tag_name": "macos-v0.1.166", "html_url": "m", "body": "mac notes",
     "assets": [
         {"name": "KhervePaint-0.1.166-macOS-arm64.dmg", "size": 9,
          "browser_download_url": "u-arm"},
         {"name": "KhervePaint-0.1.166-macOS-x86_64.dmg", "size": 9,
          "browser_download_url": "u-x86"}]},
    {"tag_name": "v0.1.164", "html_url": "w", "assets": [
        {"name": "KhervePaint-Setup.exe", "browser_download_url": "plain"},
        {"name": "KhervePaint-0.1.164-portable.zip",
         "browser_download_url": "zip"},
        {"name": "KhervePaint-Setup-0.1.164.exe",
         "browser_download_url": "setup-164"}]},
    {"tag_name": "v0.1.200", "draft": True, "assets": [
        {"name": "KhervePaint-Setup-0.1.200.exe",
         "browser_download_url": "draft"}]},
    {"tag_name": "v0.1.139", "assets": [
        {"name": "KhervePaint-Setup-0.1.139.exe",
         "browser_download_url": "old"}]},
]


def test_build_number():
    assert updater.build_number("0.1.170+de5d01f") == 170
    assert updater.build_number("macos-v0.1.166") == 166
    assert updater.build_number("KhervePaint-Setup.exe") is None


def test_platform_key():
    assert updater.platform_key("Windows", "AMD64") == "windows"
    assert updater.platform_key("Darwin", "arm64") == "macos-arm64"
    assert updater.platform_key("Darwin", "x86_64") == "macos-x86_64"
    assert updater.platform_key("Linux", "x86_64") is None


def test_newest_asset_per_platform():
    win = updater.newest_asset(_RELEASES, "windows")
    assert win["build"] == 164 and win["url"] == "setup-164"  # not draft
    arm = updater.newest_asset(_RELEASES, "macos-arm64")
    assert arm["build"] == 166 and arm["url"] == "u-arm"
    assert arm["notes"] == "mac notes"
    assert updater.newest_asset(_RELEASES, "macos-x86_64")["url"] == "u-x86"
    assert updater.newest_asset([], "windows") is None


def test_check_reports_binary_update(monkeypatch):
    monkeypatch.setattr(updater, "is_source_checkout", lambda: False)
    monkeypatch.setattr(updater, "platform_key", lambda: "windows")
    monkeypatch.setattr(updater, "_get_json", lambda *a, **k: _RELEASES)
    monkeypatch.setattr(updater, "current_version", lambda: "0.1.150+abc")
    res = updater.check()
    assert res["status"] == "update" and res["kind"] == "binary"
    assert res["latest"] == "0.1.164"
    monkeypatch.setattr(updater, "current_version", lambda: "0.1.170+abc")
    assert updater.check()["status"] == "current"


def test_check_offline_is_an_error_not_a_crash(monkeypatch):
    def boom(*_a, **_k):
        raise OSError("no network")
    monkeypatch.setattr(updater, "is_source_checkout", lambda: False)
    monkeypatch.setattr(updater, "platform_key", lambda: "windows")
    monkeypatch.setattr(updater, "_get_json", boom)
    res = updater.check()
    assert res["status"] == "error" and "no network" in res["message"]


def test_download_writes_atomically(tmp_path):
    src = tmp_path / "payload.bin"
    src.write_bytes(b"x" * 600_000)
    seen = []
    dest = updater.download(src.as_uri(), tmp_path / "out.exe",
                            lambda d, t: seen.append(d))
    assert dest.read_bytes() == src.read_bytes()
    assert seen and seen[-1] == 600_000
    assert not (tmp_path / "out.exe.part").exists()


def test_due():
    assert updater.due(0)
    assert not updater.due(1000, now=1000 + 60)
    assert updater.due(1000, now=1000 + updater.CHECK_INTERVAL)
