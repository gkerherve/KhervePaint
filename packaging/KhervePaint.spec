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

from PyInstaller.utils.hooks import collect_all, collect_submodules

_HERE = os.path.abspath(SPECPATH)                 # packaging/
_ROOT = os.path.dirname(_HERE)                    # project root

datas, binaries, hiddenimports = [], [], []

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
    icon=os.path.join(_HERE, "khervepaint.ico"),
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
