"""Generate the Windows ``.ico`` from the in-app KhervePaint mark.

Renders the same vector mark used for the window/taskbar icon
(``khervepaint.icons._paint_kpaint`` — the "KPaint" wordmark above a
brush on a light-yellow tile) at every standard icon size and packs them
into a single multi-resolution ``khervepaint.ico`` next to this file, so
Windows Explorer, the taskbar and the installer all show the running
app's own icon. Re-run whenever the mark in ``icons.py`` changes:

    python packaging/make_icon.py

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import io
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Allow "python packaging/make_icon.py" from anywhere in the checkout.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

#: Icon sizes Windows requests, small to large.
SIZES = (16, 24, 32, 48, 64, 128, 256)


def build(out_path: str) -> str:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QBuffer, QIODevice
    from PIL import Image

    app = QApplication.instance() or QApplication([])       # noqa: F841
    from khervepaint import icons

    frames = []
    for size in SIZES:
        pm = icons._paint_kpaint(size)
        buf = QBuffer()
        buf.open(QIODevice.ReadWrite)
        pm.save(buf, "PNG")                # keep the transparent background
        frames.append(Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA"))

    # Pillow writes a multi-image .ico from the largest frame + a size list.
    largest = max(frames, key=lambda im: im.size[0])
    largest.save(out_path, format="ICO",
                 sizes=[(s, s) for s in SIZES])
    return out_path


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "khervepaint.ico")
    print("wrote", build(out))
