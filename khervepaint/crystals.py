"""Crystals & unit cells palette.

A left-toolbar dropdown of its own, split out from **Molecules** so unit
cells and lattice systems are easy to find. It is backed entirely by the
`molecules` model registry — every crystal name here is already registered
in `molecules._MODELS`/`LABELS`/`SIZES` (the cubic family in `molecules`,
the seven non-cubic systems in `lattices`). Placement, the 3D builder,
supercell stacking, tilt and persistence all go through the same
`molecules` machinery (`PaintScene.place_mol_element`), so this module only
supplies the *menu grouping* — its `CATEGORIES`/`LABELS`/`SIZES` mirror the
molecules registry for the crystal subset.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from . import molecules

#: Menu grouping for the Crystals dropdown (cubic family + lattice systems).
CATEGORIES = molecules.CRYSTAL_CATEGORIES

#: Labels/sizes are shared with the molecules registry (supersets — only the
#: crystal names in CATEGORIES are ever looked up here).
LABELS = molecules.LABELS
SIZES = molecules.SIZES
