"""Custom atom colours and the colour legend for molecule/crystal models.

Two colour mechanisms, matching how each kind of model persists:

* An **editable molecule** stores its atoms, so a custom colour rides on
  the atom itself (an optional 5th slot, already understood by
  `molecules._model`/`atom_specs`).
* A **crystal** regenerates from its builder on every draw, so colours are
  a mapping keyed by `color_key` — the element symbol, suffixed with the
  site tint when the lattice distinguishes sites (``"Fe"`` vs
  ``"Fe@#2f6fed"`` for a BCC body centre). `apply_colors` re-applies the
  map to freshly built atoms; the map lives on the placed item as
  ``mol_colors`` and round-trips through JSON and SVG.

`place_legend` drops a colour key (lit sphere + element name per colour)
next to a placed model as ordinary editable items.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from .molecules import ATOM_COLORS, SITE_COLORS, atom_specs

#: Full element names for legend labels.
ELEMENT_NAMES = {
    "H": "Hydrogen", "C": "Carbon", "N": "Nitrogen", "O": "Oxygen",
    "F": "Fluorine", "Cl": "Chlorine", "Br": "Bromine", "I": "Iodine",
    "P": "Phosphorus", "S": "Sulfur", "B": "Boron", "Si": "Silicon",
    "Na": "Sodium", "K": "Potassium", "Mg": "Magnesium", "Ca": "Calcium",
    "Fe": "Iron", "Zn": "Zinc", "Cu": "Copper", "Al": "Aluminium",
    "Ti": "Titanium", "Cs": "Caesium",
}

#: Lattice-site descriptions, keyed by the site tint colour.
SITE_LABELS = {
    SITE_COLORS["body"]: "body centre",
    SITE_COLORS["face"]: "face centre",
    SITE_COLORS["inner"]: "interior site",
    SITE_COLORS["mid"]: "middle layer",
}


def color_key(atom):
    """The colour-map key for *atom* ``(el, x, y, z[, tint])``: recolouring
    one sphere recolours every atom of the same element **and** site."""
    tint = atom[4] if len(atom) > 4 and atom[4] else None
    return f"{atom[0]}@{tint}" if tint else atom[0]


def atom_color(atom, colors=None):
    """The colour *atom* is currently drawn in (override > tint > CPK)."""
    over = (colors or {}).get(color_key(atom))
    if over:
        return over
    if len(atom) > 4 and atom[4]:
        return atom[4]
    return ATOM_COLORS.get(atom[0], "#c8c8c8")


def apply_colors(atoms, colors):
    """Freshly built *atoms* with the *colors* override map applied (the
    override lands in the atom's tint slot, which drives the sphere)."""
    if not colors:
        return atoms
    out = []
    for a in atoms:
        over = colors.get(color_key(a))
        out.append((a[0], a[1], a[2], a[3], over) if over else a)
    return out


def legend_entries(atoms, colors=None):
    """Ordered unique ``(element, label, color)`` rows for a legend —
    one per distinct colour actually drawn."""
    entries, seen = [], set()
    for a in atoms:
        over = (colors or {}).get(color_key(a))
        color = atom_color(a, colors)
        if (a[0], color) in seen:
            continue
        seen.add((a[0], color))
        name = ELEMENT_NAMES.get(a[0])
        label = f"{a[0]} — {name}" if name else str(a[0])
        site = SITE_LABELS.get(a[4]) if len(a) > 4 and not over else None
        if site:
            label += f" ({site})"
        entries.append((a[0], label, color))
    return entries


def legend_specs(entries, r=10.0):
    """Shape specs for a legend column: a lit sphere + text label per row,
    with sphere radius *r* setting the overall scale."""
    specs = []
    gap = r * 2.8
    for i, (el, label, color) in enumerate(entries):
        cy = r + i * gap
        specs += atom_specs(r, cy, r, el, color=color)
        specs.append({"shape": "text", "text": label, "x": r * 2.6,
                      "y": cy - r * 1.05, "size": max(int(r * 1.5), 9),
                      "color": "#1a1a1a"})
    return specs


def model_atoms(item):
    """The 3D atoms behind a placed model *item* (hand-built structure, or
    a single unit cell of its named model — enough for the colour set)."""
    from . import molecules
    atoms = getattr(item, "mol_atoms", None)
    if atoms:
        return atoms
    name = getattr(item, "mol_name", None)
    if not name:
        return []
    return molecules.model_data(name)[0]


def place_legend(scene, item):
    """Drop a colour legend for the placed model *item* just to its right,
    as an ordinary editable group (undoable, one gesture). Returns the
    group, or None if *item* isn't a model."""
    from .ai_assistant import _spec_to_item
    from .canvas import GroupItem, center_origin
    atoms = model_atoms(item)
    entries = legend_entries(atoms, getattr(item, "mol_colors", None))
    if not entries:
        return None
    rect = item.sceneBoundingRect()
    r = max(rect.height() * 0.045, 6.0)
    items = [it for it in (_spec_to_item(s) for s in legend_specs(entries, r))
             if it is not None]
    if not items:
        return None
    scene.clearSelection()
    group = GroupItem()
    scene.addItem(group)
    for z, it in enumerate(items):
        it.setZValue(z)
        group.addToGroup(it)
    gb = group.sceneBoundingRect()
    was_snap = scene.snap_enabled
    scene.snap_enabled = False
    group.moveBy(rect.right() + rect.width() * 0.06 - gb.left(),
                 rect.center().y() - gb.center().y())
    scene.snap_enabled = was_snap
    center_origin(group)
    group.setSelected(True)
    scene.changed_by_user.emit()
    return group
