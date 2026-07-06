"""Application-wide look and feel — selectable themes.

Token-driven theming in the Kherve family style: every theme is a
small dict of colours fed into one QSS template and palette. The
chosen theme persists via QSettings (View > Theme).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtCore import QSettings
from PyQt5.QtGui import QColor, QPalette

#: theme name -> colour tokens.
THEMES = {
    "Light": dict(
        window="#f4f5f7", chrome="#fafbfc", card="#ffffff",
        border="#e1e4e8", text="#1a1a1a", editor="#f8f9fa",
        hover="#e3eef9", pressed="#cfe3f6", select="#2176c7",
        icon="#444444", gutter="#1565c0", dark=False),
    "Dark": dict(
        window="#1e2227", chrome="#262b31", card="#2b3138",
        border="#3a4149", text="#e6e9ec", editor="#23282e",
        hover="#37404a", pressed="#415060", select="#4aa3ff",
        icon="#cfd6dd", gutter="#6ab0f3", dark=True),
    # --- The yellow family (KhervePaint's signature colour) ---------------
    "Butter": dict(
        window="#fdf6d3", chrome="#faefb8", card="#fffdf4",
        border="#e7d9a0", text="#413815", editor="#fdf8e0",
        hover="#f5e7a6", pressed="#eeda8b", select="#c99e28",
        icon="#7c6620", gutter="#b98d1c", dark=False),
    "Cream": dict(
        window="#faf4df", chrome="#f4ebcb", card="#fffef8",
        border="#e2d4ac", text="#443b22", editor="#f9f2d8",
        hover="#eee2bb", pressed="#e5d5a3", select="#b78f2a",
        icon="#6f5d33", gutter="#a0791b", dark=False),
    "Lemon": dict(
        window="#fdf8bf", chrome="#fbf29a", card="#fffef1",
        border="#e6d878", text="#3f3b0f", editor="#fdfaca",
        hover="#f6ec8a", pressed="#efe16c", select="#cba614",
        icon="#7a6a12", gutter="#ba960e", dark=False),
    "Sunflower": dict(
        window="#fdef94", chrome="#fce572", card="#fffdef",
        border="#ecd257", text="#463c0e", editor="#fdf5b4",
        hover="#f8e669", pressed="#f1da4d", select="#d4a30f",
        icon="#7d6510", gutter="#c39109", dark=False),
    "Honey": dict(
        window="#fbeab0", chrome="#f7e094", card="#fffcee",
        border="#e1c56e", text="#48380f", editor="#fcf1c6",
        hover="#f2db86", pressed="#ebcf69", select="#c8941a",
        icon="#7a5c14", gutter="#b8830e", dark=False),
    "Amber": dict(
        window="#fce6b4", chrome="#f8d891", card="#fffbef",
        border="#e6c079", text="#4a3514", editor="#fcecc6",
        hover="#f3d78d", pressed="#ecc972", select="#cf8c1a",
        icon="#7d5714", gutter="#bd7a0f", dark=False),
    "Gold": dict(
        window="#f6e492", chrome="#f0d96f", card="#fffceb",
        border="#d6b950", text="#443410", editor="#f8ecb0",
        hover="#edd162", pressed="#e5c547", select="#b8860b",
        icon="#6d500d", gutter="#a87409", dark=False),
    "Mustard": dict(
        window="#eee0a6", chrome="#e5d28d", card="#fbf6e2",
        border="#ccb566", text="#3e3210", editor="#efe6b4",
        hover="#ddcc80", pressed="#d2be6a", select="#997c1a",
        icon="#63500f", gutter="#8a6b0f", dark=False),
    "Slate": dict(
        window="#e8ebef", chrome="#dde2e8", card="#ffffff",
        border="#c5ccd4", text="#2e3440", editor="#f0f3f6",
        hover="#cfd9e4", pressed="#b9c8d8", select="#4a6fa5",
        icon="#4c566a", gutter="#4a6fa5", dark=False),
    "Ocean": dict(
        window="#e7f1f6", chrome="#d9e9f2", card="#ffffff",
        border="#bcd6e4", text="#173a4d", editor="#eef6fa",
        hover="#c8e2ef", pressed="#aed5e8", select="#1a6e8e",
        icon="#2a647e", gutter="#1a6e8e", dark=False),
    "Forest": dict(
        window="#eaf1ea", chrome="#dde9dd", card="#ffffff",
        border="#c3d6c3", text="#23362a", editor="#f0f6f0",
        hover="#d0e4d0", pressed="#b9d6b9", select="#2e7d4f",
        icon="#3c5a44", gutter="#2e7d4f", dark=False),
    "Sand": dict(
        window="#f5f0e6", chrome="#efe7d8", card="#fffdf8",
        border="#ddd1bb", text="#3d3526", editor="#f8f4ea",
        hover="#ecdfc8", pressed="#e2d2b4", select="#b07d2b",
        icon="#6b5d40", gutter="#a06b1a", dark=False),
    "Graphite": dict(
        window="#26262a", chrome="#2e2e33", card="#333339",
        border="#46464d", text="#dddde2", editor="#2b2b30",
        hover="#3f3f47", pressed="#4c4c56", select="#9a7fd1",
        icon="#c4c4cc", gutter="#b49ae0", dark=True),
    "High Contrast": dict(
        window="#ffffff", chrome="#ffffff", card="#ffffff",
        border="#000000", text="#000000", editor="#ffffff",
        hover="#dddddd", pressed="#bbbbbb", select="#0000cc",
        icon="#000000", gutter="#0000cc", dark=False),
}

DEFAULT_THEME = "Butter"
_SETTINGS = ("Kherve", "KhervePaint")
# v2 key: the previous "theme" key was auto-written on every launch,
# pinning everyone to the old default. A fresh key lets the new yellow
# default take effect; only an explicit choice (View > Theme) is saved.
_THEME_KEY = "theme_v2"
_current = DEFAULT_THEME


def _template(t: dict) -> str:
    return f"""
QMainWindow, QDialog {{ background: {t['window']}; }}
QWidget {{ color: {t['text']}; }}

QMenuBar {{ background: {t['chrome']};
            border-bottom: 1px solid {t['border']}; }}
QMenuBar::item {{ padding: 5px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {t['hover']}; border-radius: 4px; }}
QMenu {{ background: {t['card']}; border: 1px solid {t['border']};
         padding: 4px; }}
QMenu::item {{ padding: 5px 24px 5px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {t['hover']}; }}

QToolBar {{
    background: {t['chrome']};
    border: none;
    border-bottom: 1px solid {t['border']};
    padding: 3px 6px;
    spacing: 2px;
}}
QToolBar[orientation="vertical"] {{
    border-bottom: none;
    border-right: 1px solid {t['border']};
}}
QToolButton {{ border: none; border-radius: 6px; padding: 4px;
               margin: 1px; }}
QToolButton:hover {{ background: {t['hover']}; }}
QToolButton:pressed {{ background: {t['pressed']}; }}
QToolButton:checked {{ background: {t['pressed']}; }}
QToolButton::menu-indicator {{ image: none; width: 0; height: 0; }}

QComboBox {{
    background: {t['card']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 4px 10px;
    min-width: 70px;
}}
QComboBox:hover {{ border-color: {t['select']}; }}
QComboBox::drop-down {{ subcontrol-origin: padding;
    subcontrol-position: center right; border: none; width: 18px; }}
QComboBox::down-arrow {{
    image: none;
    width: 0; height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {t['icon']};
    margin-right: 6px;
}}
QComboBox::down-arrow:on {{ border-top: none;
    border-bottom: 5px solid {t['icon']}; }}
QComboBox QAbstractItemView {{ background: {t['card']};
    selection-background-color: {t['hover']};
    selection-color: {t['text']}; }}

QSpinBox {{
    background: {t['card']};
    border: 1px solid {t['border']};
    border-radius: 6px;
    padding: 3px 6px;
}}
QSpinBox:focus {{ border-color: {t['select']}; }}

QGraphicsView {{ background: {t['window']}; border: none; }}

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {t['border']};
    border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 11px;
    margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {t['border']};
    border-radius: 4px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0; }}

QStatusBar {{ background: {t['chrome']};
              border-top: 1px solid {t['border']}; }}

QLineEdit {{
    background: {t['editor']};
    border: 1px solid {t['border']};
    border-radius: 5px;
    padding: 3px 6px;
    color: {t['text']};
}}
QLineEdit:focus {{ border-color: {t['select']}; }}
"""


def _palette(t: dict) -> QPalette:
    p = QPalette()
    p.setColor(QPalette.Window, QColor(t["window"]))
    p.setColor(QPalette.WindowText, QColor(t["text"]))
    p.setColor(QPalette.Base, QColor(t["card"]))
    p.setColor(QPalette.AlternateBase, QColor(t["chrome"]))
    p.setColor(QPalette.Text, QColor(t["text"]))
    p.setColor(QPalette.Button, QColor(t["window"]))
    p.setColor(QPalette.ButtonText, QColor(t["text"]))
    p.setColor(QPalette.ToolTipBase, QColor(t["chrome"]))
    p.setColor(QPalette.ToolTipText, QColor(t["text"]))
    p.setColor(QPalette.Highlight, QColor(t["select"]))
    p.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    p.setColor(QPalette.PlaceholderText, QColor(t["border"]))
    return p


def current_theme() -> str:
    return _current


def tokens(name: str = None) -> dict:
    return THEMES.get(name or _current, THEMES[DEFAULT_THEME])


def saved_theme() -> str:
    name = QSettings(*_SETTINGS).value(_THEME_KEY, DEFAULT_THEME)
    return name if name in THEMES else DEFAULT_THEME


def apply_style(app, name: str = None):
    """Apply theme *name* (or the saved one at startup).

    Only an explicit *name* (a user choice from the Theme menu) is
    persisted — startup must not overwrite the saved value, so the
    default stays the default until the user picks something."""
    global _current
    _current = name or saved_theme()
    t = tokens(_current)
    app.setPalette(_palette(t))
    app.setStyleSheet(_template(t))
    if name is not None:
        QSettings(*_SETTINGS).setValue(_THEME_KEY, name)
    from . import icons
    icons.set_icon_color(t["icon"])
