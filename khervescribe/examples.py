"""Built-in Examples menu — labelled schematics of lab techniques.

Each example loads a detailed, fully labelled instrument schematic onto
an A4 page; every element is a real, editable KherveScribe item (built
from the same shape-spec format the AI assistant uses), so a sketch is a
starting point you can restyle, relabel and export. The drawing toolkit
lives in `example_kit.py` and the builders in `example_sketches.py`.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from .example_kit import PAGE_W, PAGE_H, PAGE_DPI       # noqa: F401
from .example_sketches import SKETCHES

#: Menu category order.
_ORDER = ["Spectroscopy", "Mass spectrometry", "Diffraction", "Microscopy",
          "Thermal & sorption", "Electrochemistry", "Chromatography"]

#: (category, display name, builder) sorted by category then name.
EXAMPLES = sorted(
    SKETCHES,
    key=lambda e: (_ORDER.index(e[0]) if e[0] in _ORDER else 99, e[1]))
