"""Internationalisation: language list, persistence, translator install.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Mechanism note: strings throughout the app are wrapped in the standard
Qt ``self.tr(...)`` / ``QCoreApplication.translate(context, text)``
calls, which is what a normal Qt app uses with ``.ts``/``.qm`` files
compiled by ``lrelease``. This checkout only has ``pylupdate5``
available (no ``lrelease``/``pyside*-lupdate``), so there is no way to
compile a binary ``.qm`` here. Rather than skip translation entirely,
``JsonTranslator`` below is a ``QTranslator`` subclass that overrides
``translate()`` and looks the string up in a plain JSON dictionary
(``translations/<lang>.json``, ``{"Context": {"Source": "Translated"}}``)
instead of a compiled catalogue. It still installs on ``QApplication`` the
normal way (``app.installTranslator(...)``) and every call site still goes
through ``tr()``/``QCoreApplication.translate()``, so if ``lrelease``
becomes available later, real ``.ts``/``.qm`` files can be generated from
the same source strings (``pylupdate5`` already works) and this loader
swapped for a stock ``QTranslator.load(...)`` with no call-site changes.
"""

import json
from pathlib import Path

from PyQt5.QtCore import QSettings, QTranslator

SETTINGS = ("Kherve", "KhervePaint")
APP_KEY = "app/language"

LANGUAGES = [
    ("en", "English"),
    ("zh", "中文"),
    ("fr", "Français"),
    ("es", "Español"),
]
LANGUAGE_CODES = [code for code, _ in LANGUAGES]

_TRANSLATIONS_DIR = Path(__file__).resolve().parent.parent / "translations"


def current_language():
    """Return the saved language code, defaulting to ``"en"``.

    Deliberately does NOT auto-detect the OS locale — the user picks the
    language explicitly (View ▸ Language) and it sticks until changed.
    """
    settings = QSettings(*SETTINGS)
    lang = settings.value(APP_KEY, "en")
    return lang if lang in LANGUAGE_CODES else "en"


def set_language(code):
    """Persist the chosen language code to QSettings."""
    if code not in LANGUAGE_CODES:
        code = "en"
    QSettings(*SETTINGS).setValue(APP_KEY, code)


class JsonTranslator(QTranslator):
    """A QTranslator backed by a JSON dict instead of a compiled .qm.

    See the module docstring for why this exists in place of the usual
    ``load("*.qm")``.
    """

    def __init__(self, code, parent=None):
        super().__init__(parent)
        self._data = {}
        path = _TRANSLATIONS_DIR / f"{code}.json"
        if path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                self._data = {}

    def translate(self, context, source_text, disambiguation=None, n=-1):
        ctx = self._data.get(context)
        if ctx:
            hit = ctx.get(source_text)
            if hit:
                return hit
        return ""  # fall back to the source text (Qt's default behaviour)

    def isEmpty(self):
        return not self._data


_installed_translator = None


def install_language(app, code):
    """Install (or clear, for "en") the translator for `code` on `app`."""
    global _installed_translator
    if _installed_translator is not None:
        app.removeTranslator(_installed_translator)
        _installed_translator = None
    if code != "en":
        translator = JsonTranslator(code)
        if not translator.isEmpty():
            app.installTranslator(translator)
            _installed_translator = translator


def apply_saved_language(app):
    """Install whatever language is currently saved. Call at start-up."""
    install_language(app, current_language())
