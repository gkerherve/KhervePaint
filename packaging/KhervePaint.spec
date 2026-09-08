# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for KhervePaint — one-folder (onedir) build.

Produces ``dist/KhervePaint/KhervePaint.exe`` alongside a folder of the
decompressed runtime (Python + Qt), so it launches instantly with nothing
to unpack. Build with:

    pyinstaller packaging/KhervePaint.spec --noconfirm

The window/taskbar icon is baked in from ``packaging/khervepaint.ico``
(regenerate it with ``python packaging/make_icon.py`` after editing the
mark in ``khervepaint/icons.py``).
"""

import os
import subprocess
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

_HERE = os.path.abspath(SPECPATH)                 # packaging/
_ROOT = os.path.dirname(_HERE)                    # project root

_IS_MAC = sys.platform == "darwin"

# The icon format is per-platform, and .icns is built from the committed
# PNG on demand, so a Mac checkout needs no binary the Windows build would
# never read.
if _IS_MAC:
    _ICON = os.path.join(_ROOT, "build", "KhervePaint.icns")
    if not os.path.isfile(_ICON):
        subprocess.run([sys.executable,
                        os.path.join(_HERE, "make_icns.py"), _ICON],
                       check=True)
else:
    _ICON = os.path.join(_HERE, "khervepaint.ico")

datas, binaries, hiddenimports = [], [], []

# Bake the resolved version into the frozen build — a PyInstaller bundle
# never ships .git, so without this khervepaint/_version.py would fall
# back to the placeholder "0.1.0".
#
# Written here, from the spec, rather than by whatever script started the
# build: the documented Windows flow runs PyInstaller *before*
# build_installer.py, so a stamp written by that script would always be one
# build late. Doing it at the top of the spec means every entry point —
# bare `pyinstaller`, build_installer.py, build_macos.py, CI — freezes the
# version that is actually checked out.
sys.path.insert(0, _HERE)
from build_installer import write_version          # noqa: E402

write_version()
_version_file = os.path.join(_ROOT, "khervepaint", "VERSION")
if os.path.isfile(_version_file):
    datas.append((_version_file, "khervepaint"))

# The whole app package (some submodules are imported lazily inside
# functions, e.g. the spec-library palettes — pull them all in explicitly).
hiddenimports += collect_submodules("khervepaint")

# Dependencies that ship data files or dynamically-imported submodules.
for _pkg in ("qtawesome",):
    try:
        d, b, h = collect_all(_pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass   # optional dependency not installed — skip it

a = Analysis(
    [os.path.join(_ROOT, "KhervePaint.py")],
    pathex=[_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # Trim heavy libraries the app never uses, to keep the folder smaller.
    excludes=["tkinter", "PyQt6", "PySide2", "PySide6", "PyQt5.QtQml",
              "PyQt5.QtQuick", "numpy", "scipy", "matplotlib", "pandas",
              "PIL"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,                 # onedir: binaries live in COLLECT
    name="KhervePaint",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,                         # GUI app: no console window
    icon=_ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="KhervePaint",                    # -> dist/KhervePaint/
)

# --------------------------------------------------------- macOS bundle

if _IS_MAC:
    # CFBundleShortVersionString has to be dot-separated digits, and the
    # git-derived string carries a "+sha" suffix Finder rejects.
    _short_version = "0.1.0"
    with open(_version_file, encoding="utf-8") as _fh:
        _short_version = _fh.read().strip().split("+")[0] or _short_version

    # No CFBundleDocumentTypes: registering .kpaint/.svg would put
    # KhervePaint in Finder's Open With menu, but the app has no
    # QFileOpenEvent handler — macOS delivers a double-clicked file as an
    # event, not in argv, so it would launch to an empty canvas. Claim the
    # extensions once that handler exists.
    app = BUNDLE(
        coll,
        name="KhervePaint.app",
        icon=_ICON,
        bundle_identifier="com.kerherve.khervepaint",
        version=_short_version,
        info_plist={
            "CFBundleName": "KhervePaint",
            "CFBundleDisplayName": "KhervePaint",
            "CFBundleShortVersionString": _short_version,
            "CFBundleVersion": _short_version,
            "LSMinimumSystemVersion": "11.0",
            # Without this the canvas draws at 1x and is scaled up — every
            # stroke, symbol and mm ruler reads soft on a Retina display,
            # which for a drawing app is the whole product.
            "NSHighResolutionCapable": True,
            # The app ships its own light and dark themes; letting macOS
            # force the Aqua light appearance would fight them.
            "NSRequiresAquaSystemAppearance": False,
            "NSHumanReadableCopyright":
                "Copyright (C) 2026 Gwilherm Kerherve. GPL-3.0.",
        },
    )
