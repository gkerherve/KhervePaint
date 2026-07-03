"""Image operations: background removal for ImageItem bitmaps.

`remove_background` makes an image's background transparent: it takes
the most common colour along the image border as the background, then
scanline-floods inward from every border pixel of that colour (within a
per-channel tolerance) and clears the alpha of the flooded pixels.
Because the flood starts at the border, same-coloured regions *inside*
the subject (e.g. white text in a logo) are preserved.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from collections import Counter

from PyQt5.QtGui import QImage

#: Per-channel tolerance: border pixels this close to the background
#: colour are treated as background (JPEG noise, soft gradients).
DEFAULT_TOLERANCE = 40


def _border_color(data: bytes, w: int, h: int, bpl: int):
    """The modal (most common) colour among the border pixels, as a
    (b, g, r) tuple in the ARGB32 byte order."""
    counts = Counter()
    for x in range(w):
        for y in (0, h - 1):
            i = y * bpl + x * 4
            counts[data[i:i + 3]] += 1
    for y in range(1, h - 1):
        for x in (0, w - 1):
            i = y * bpl + x * 4
            counts[data[i:i + 3]] += 1
    return counts.most_common(1)[0][0]


def remove_background(image: QImage, tolerance: int = DEFAULT_TOLERANCE):
    """A copy of *image* with its background made transparent, or None
    when no border pixel matches the background colour (nothing to do).
    The background is the modal border colour; only pixels connected to
    the border are cleared."""
    img = image.convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    if w < 2 or h < 2:
        return None
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    data = memoryview(ptr)
    bpl = img.bytesPerLine()

    tb, tg, tr = _border_color(bytes(data), w, h, bpl)

    def match(x, y):
        i = y * bpl + x * 4
        return (abs(data[i] - tb) <= tolerance
                and abs(data[i + 1] - tg) <= tolerance
                and abs(data[i + 2] - tr) <= tolerance)

    # Scanline flood (as in fill.py) seeded from every matching border
    # pixel, so disconnected background corners all clear in one pass.
    stack = [(x, y) for x in range(w) for y in (0, h - 1) if match(x, y)]
    stack += [(x, y) for y in range(1, h - 1) for x in (0, w - 1)
              if match(x, y)]
    if not stack:
        return None
    visited = bytearray(w * h)
    cleared = False
    while stack:
        x, y = stack.pop()
        row = y * w
        if visited[row + x] or not match(x, y):
            continue
        xl = x
        while xl > 0 and not visited[row + xl - 1] and match(xl - 1, y):
            xl -= 1
        xr = x
        while xr < w - 1 and not visited[row + xr + 1] and match(xr + 1, y):
            xr += 1
        base = y * bpl
        for xx in range(xl, xr + 1):
            visited[row + xx] = 1
            data[base + xx * 4 + 3] = 0          # alpha -> transparent
        cleared = True
        for xx in range(xl, xr + 1):
            if y > 0 and not visited[row - w + xx] and match(xx, y - 1):
                stack.append((xx, y - 1))
            if y < h - 1 and not visited[row + w + xx] and match(xx, y + 1):
                stack.append((xx, y + 1))
    return img if cleared else None
