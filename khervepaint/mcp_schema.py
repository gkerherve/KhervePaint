"""The tool table KhervePaint offers MCP clients — schemas only.

Deliberately Qt-free and import-free: this is the contract, and
`mcp_tools.py` is the implementation.  Keeping them apart means the
tool list can be inspected (and tested) without a running window, and
the stdio server never drags PyQt5 into the host's subprocess.

Every tool answers with JSON.  ``render_canvas`` additionally returns a
PNG under `mcp_server.IMAGE_KEY`, which the stdio/HTTP servers turn
into a real MCP image block — a drawing app that could only describe
itself in prose would be half blind.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from __future__ import annotations

#: Symbol palettes reachable through ``place_symbol``/``list_symbols``.
#: The key is what a client passes; `mcp_tools` maps it to the module.
LIBRARY_KEYS = [
    "molecules", "crystals", "scheme3d", "floorplan", "electrical",
    "optics", "vacuum", "labware", "flowchart", "network", "pid",
    "arrows", "biology", "maths",
]

#: Representations a placed molecule/crystal can be drawn in.
REPR_MODES = ["3d", "structural", "lewis", "condensed"]


def _obj(properties: dict, required=()) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(required)}


_IDS = {
    "type": "array",
    "items": {"type": "integer"},
    "description": "Item ids from list_items.",
}

_POINT = {
    "x": {"type": "number",
          "description": "Scene x in pixels (0 = left edge)."},
    "y": {"type": "number",
          "description": "Scene y in pixels (0 = top edge, y grows down)."},
}

#: One entry of ``draw``'s shapes array.  Loosely typed on purpose: the
#: spec format is shared with the built-in AI chat and the example
#: builders, and pinning every shape's keys here would freeze it.
_SHAPE_SPEC = {
    "type": "object",
    "description": (
        "One shape. 'shape' is required; which coordinate keys apply "
        "depends on it."
    ),
    "properties": {
        "shape": {
            "type": "string",
            "description": (
                "rect, rounded_rect, ellipse, circle, line, arrow, text, "
                "triangle, right_triangle, diamond, parallelogram, "
                "trapezoid, pentagon, hexagon, heptagon, octagon, star, "
                "star6, plus, chevron, block_arrow, lightning, house, "
                "halfcircle, quartercircle, or polygon with explicit "
                "'points'."
            ),
        },
        "x": {"type": "number", "description": "Left edge (area shapes)."},
        "y": {"type": "number", "description": "Top edge (area shapes)."},
        "w": {"type": "number", "description": "Width in pixels."},
        "h": {"type": "number", "description": "Height in pixels."},
        "x1": {"type": "number"}, "y1": {"type": "number"},
        "x2": {"type": "number"}, "y2": {"type": "number"},
        "points": {
            "type": "array",
            "description": "[[x, y], …] absolute vertices for 'polygon'.",
            "items": {"type": "array", "items": {"type": "number"}},
        },
        "text": {"type": "string", "description": "Content of a 'text'."},
        "size": {"type": "integer", "description": "Text point size."},
        "anchor": {
            "type": "string",
            "description": "'center' treats (x, y) as the text centre.",
        },
        "stroke": {"type": "string",
                   "description": "Outline colour: #rrggbb, or 'none'."},
        "fill": {"description": (
            "Fill: #rrggbb, 'none', or a gradient object "
            "{\"kind\": \"linear\"|\"radial\"|\"sun\", \"c1\": hex, "
            "\"c2\": hex, \"angle\": deg}. 'sun' is a lit-sphere "
            "highlight — what makes a circle read as a 3-D ball.")},
        "width": {"type": "number", "description": "Stroke width."},
        "radius": {"type": "number",
                   "description": "Corner radius of a rounded_rect."},
        "label": {"type": "string",
                  "description": "Text centred inside the shape and "
                                 "carried with it when it moves."},
        "rotation": {"type": "number", "description": "Degrees, clockwise."},
        "opacity": {"type": "number", "description": "0 (clear) to 1."},
    },
    "required": ["shape"],
}


TOOLS = [
    # ── Inspection ─────────────────────────────────────────────────
    {
        "name": "get_document_info",
        "description": (
            "The canvas: size in pixels and millimetres, dpi, grid and "
            "snap settings, item count, file path and whether there are "
            "unsaved changes. Call this first — every other tool speaks "
            "scene pixels with (0, 0) at the top-left."
        ),
        "input_schema": _obj({}),
    },
    {
        "name": "list_items",
        "description": (
            "Every top-level item on the canvas, bottom to top, with its "
            "id, kind, bounding box (pixels and mm), colours, rotation "
            "and label. Ids are stable while an item lives but are not "
            "saved in the file, and undo rebuilds items — re-read them "
            "after an undo or an open."
        ),
        "input_schema": _obj({
            "depth": {
                "type": "integer",
                "description": (
                    "How far to recurse into groups (0 = top level "
                    "only, the default; 1 lists a group's children)."),
            },
            "ids": dict(_IDS, description=(
                "Only describe these items (and their children when "
                "depth > 0). Omit for the whole canvas.")),
        }),
    },
    {
        "name": "render_canvas",
        "description": (
            "A PNG picture of the drawing as it stands, returned as an "
            "image you can look at. Do this after drawing anything "
            "non-trivial: overlapping shapes, off-canvas items and bad "
            "spacing are obvious in the picture and invisible in JSON."
        ),
        "input_schema": _obj({
            "max_width": {
                "type": "integer",
                "description": (
                    "Scale the picture down to at most this many pixels "
                    "wide (default 1000). Smaller is cheaper to look at."),
            },
            "region": {
                "type": "array",
                "description": "[x, y, w, h] to render only part of the "
                               "canvas. Omit for the whole page.",
                "items": {"type": "number"},
            },
        }),
    },
    {
        "name": "list_symbols",
        "description": (
            "The symbol palettes, or one palette's elements grouped by "
            "section with the exact names place_symbol takes. Guessing a "
            "name wastes a call — list first."
        ),
        "input_schema": _obj({
            "library": {
                "type": "string",
                "enum": LIBRARY_KEYS,
                "description": "Omit to list the palettes themselves.",
            },
        }),
    },
    {
        "name": "list_models",
        "description": (
            "The built-in molecule and crystal catalogue: exact names for "
            "place_model, grouped by section, flagged with whether each "
            "can be stacked into a supercell."
        ),
        "input_schema": _obj({
            "kind": {
                "type": "string",
                "enum": ["all", "molecules", "crystals"],
                "description": "Default 'all'.",
            },
        }),
    },
    {
        "name": "list_examples",
        "description": (
            "The built-in example figures (labelled instrument "
            "schematics), by category. load_example replaces the "
            "document with one, fully editable."
        ),
        "input_schema": _obj({}),
    },
    {
        "name": "list_objects",
        "description": (
            "The user's saved-object library — reusable drawings they "
            "have filed away, ready for insert_object."
        ),
        "input_schema": _obj({}),
    },

    # ── Drawing ────────────────────────────────────────────────────
    {
        "name": "draw",
        "description": (
            "Create shapes on the canvas. Takes a LIST and makes them all "
            "in one undoable step, so build a whole figure in one call "
            "rather than one shape per call. Later shapes sit on top of "
            "earlier ones — draw backgrounds first. Returns the new ids."
        ),
        "input_schema": _obj({
            "shapes": {"type": "array", "items": _SHAPE_SPEC,
                       "description": "The shapes to create, back to front."},
        }, ["shapes"]),
    },
    {
        "name": "update_items",
        "description": (
            "Move, resize, restyle or relabel existing items. Each change "
            "names an id and only the properties to alter; everything "
            "else is left alone. 'x'/'y' move the item so its bounding "
            "box starts there; 'dx'/'dy' nudge it instead."
        ),
        "input_schema": _obj({
            "changes": {
                "type": "array",
                "description": "One entry per item.",
                "items": _obj({
                    "id": {"type": "integer"},
                    "x": {"type": "number"}, "y": {"type": "number"},
                    "dx": {"type": "number"}, "dy": {"type": "number"},
                    "w": {"type": "number"}, "h": {"type": "number"},
                    "x1": {"type": "number"}, "y1": {"type": "number"},
                    "x2": {"type": "number"}, "y2": {"type": "number"},
                    "stroke": {"type": "string"},
                    "fill": {"description": "Hex, 'none', or a gradient "
                                            "object as in draw."},
                    "width": {"type": "number"},
                    "rotation": {"type": "number"},
                    "opacity": {"type": "number"},
                    "scale": {"type": "number"},
                    "label": {"type": "string"},
                    "text": {"type": "string",
                             "description": "New content of a text item."},
                    "size": {"type": "integer",
                             "description": "Text point size."},
                    "visible": {"type": "boolean"},
                }, ["id"]),
            },
        }, ["changes"]),
    },
    {
        "name": "delete_items",
        "description": "Remove items from the canvas. One undoable step.",
        "input_schema": _obj({"ids": _IDS}, ["ids"]),
    },
    {
        "name": "group_items",
        "description": (
            "Group items so they move, rotate and scale as one figure. "
            "Returns the new group's id."
        ),
        "input_schema": _obj({"ids": _IDS}, ["ids"]),
    },
    {
        "name": "ungroup_items",
        "description": "Break groups apart into their members.",
        "input_schema": _obj({"ids": _IDS}, ["ids"]),
    },
    {
        "name": "order_items",
        "description": (
            "Restack items: bring to front / send to back, or one step "
            "forward / backward."
        ),
        "input_schema": _obj({
            "ids": _IDS,
            "where": {"type": "string",
                      "enum": ["front", "back", "forward", "backward"]},
        }, ["ids", "where"]),
    },
    {
        "name": "align_items",
        "description": (
            "Line items up on an edge or centre line, or space them "
            "evenly. The outermost items stay put and the rest move."
        ),
        "input_schema": _obj({
            "ids": _IDS,
            "how": {
                "type": "string",
                "enum": ["left", "right", "top", "bottom", "center_x",
                         "center_y", "distribute_x", "distribute_y"],
                "description": "'center_x' aligns vertical centre lines.",
            },
        }, ["ids", "how"]),
    },
    {
        "name": "select_items",
        "description": (
            "Select items in the window, so the user sees what you mean "
            "and the app's own handles appear on them. Pass no ids to "
            "clear the selection."
        ),
        "input_schema": _obj({"ids": _IDS}),
    },

    # ── Libraries and models ───────────────────────────────────────
    {
        "name": "place_symbol",
        "description": (
            "Drop a symbol from one of the app's palettes onto the "
            "canvas, centred on (x, y), as an editable group. Symbols "
            "are scaled relative to the page, so they stay in proportion "
            "with one another whatever the canvas size."
        ),
        "input_schema": _obj({
            "library": {"type": "string", "enum": LIBRARY_KEYS},
            "name": {"type": "string",
                     "description": "Element name from list_symbols."},
            **_POINT,
        }, ["library", "name", "x", "y"]),
    },
    {
        "name": "place_model",
        "description": (
            "Place a molecule or crystal from the built-in catalogue as a "
            "real tagged 3-D model — the user can still spin it by "
            "double-clicking and edit it in the molecule builder. Do NOT "
            "draw these out of circles by hand."
        ),
        "input_schema": _obj({
            "name": {"type": "string",
                     "description": "Model name from list_models."},
            **_POINT,
            "cells": {
                "type": "array",
                "description": "[nx, ny, nz] to place a crystal straight "
                               "away as a supercell.",
                "items": {"type": "integer"},
            },
            "representation": {"type": "string", "enum": REPR_MODES},
        }, ["name", "x", "y"]),
    },
    {
        "name": "build_molecule",
        "description": (
            "Build any molecule from its heavy-atom skeleton and place it "
            "as a 3-D model: 'atoms' are element symbols with NO "
            "hydrogens, 'bonds' are [i, j, order]. Hydrogens and correct "
            "geometry are added for you. Give 'name' as well when the "
            "molecule is a common one — a curated model is used instead."
        ),
        "input_schema": _obj({
            "atoms": {
                "type": "array",
                "description": "Heavy atoms, e.g. [\"C\", \"C\", \"O\"].",
                "items": {"type": "string"},
            },
            "bonds": {
                "type": "array",
                "description": "[i, j, order] triples; order defaults to 1.",
                "items": {"type": "array", "items": {"type": "integer"}},
            },
            **_POINT,
            "name": {"type": "string",
                     "description": "Molecule name, used for a curated "
                                    "model when one exists."},
            "representation": {"type": "string", "enum": REPR_MODES},
        }, ["atoms", "x", "y"]),
    },
    {
        "name": "configure_model",
        "description": (
            "Change a placed molecule or crystal in place: view angles, "
            "bond spread, representation, per-element colours, supercell "
            "size and per-cell tilts (a defect, not a detached grain). "
            "Rebuilds the model without losing its position."
        ),
        "input_schema": _obj({
            "id": {"type": "integer",
                   "description": "A model item's id from list_items."},
            "az": {"type": "number",
                   "description": "Azimuth in degrees (spin about the "
                                  "vertical)."},
            "el": {"type": "number", "description": "Elevation in degrees."},
            "bond": {"type": "number",
                     "description": "Bond-length multiplier; 0 packs the "
                                    "atoms together."},
            "representation": {"type": "string", "enum": REPR_MODES},
            "cells": {
                "type": "array",
                "description": "[nx, ny, nz] supercell; [1, 1, 1] restores "
                               "the single unit cell.",
                "items": {"type": "integer"},
            },
            "tilts": {
                "type": "object",
                "description": (
                    "Per-cell rotations inside a supercell, "
                    "{\"i,j,k\": [rx, ry, rz]} in degrees."),
            },
            "colors": {
                "type": "object",
                "description": "Per-element colour overrides, "
                               "{\"O\": \"#ff0000\"}.",
            },
            "polyhedra": {"type": "boolean",
                          "description": "Draw translucent coordination "
                                         "polyhedra (crystals)."},
        }, ["id"]),
    },
    {
        "name": "insert_object",
        "description": (
            "Insert one of the user's saved objects (see list_objects) "
            "onto the canvas as fresh editable items."
        ),
        "input_schema": _obj({
            "name": {"type": "string",
                     "description": "Object name from list_objects."},
            **_POINT,
        }, ["name"]),
    },
    {
        "name": "load_example",
        "description": (
            "Replace the document with a built-in example figure. Like "
            "new_document, this discards the current drawing, so it "
            "refuses unsaved work unless discard_unsaved_changes is set."
        ),
        "input_schema": _obj({
            "name": {"type": "string",
                     "description": "Example name from list_examples."},
            "discard_unsaved_changes": {"type": "boolean"},
        }, ["name"]),
    },

    # ── Canvas and document ────────────────────────────────────────
    {
        "name": "set_canvas",
        "description": (
            "Resize the page, change its dpi, adjust the grid, or shrink "
            "the page to fit the drawing. Content keeps its position."
        ),
        "input_schema": _obj({
            "width": {"type": "integer", "description": "Pixels."},
            "height": {"type": "integer", "description": "Pixels."},
            "dpi": {"type": "integer",
                    "description": "Pixels per inch — sets the physical "
                                   "size of the page and of every mm."},
            "grid_mm": {"type": "number",
                        "description": "Grid spacing in millimetres."},
            "show_grid": {"type": "boolean"},
            "snap": {"type": "boolean"},
            "fit_to_content": {
                "type": "boolean",
                "description": "Shrink the page to the drawing's bounding "
                               "box (with a small margin).",
            },
        }),
    },
    {
        "name": "new_document",
        "description": (
            "Start a blank drawing. The user's unsaved work is real: this "
            "refuses unless discard_unsaved_changes is set. Offer to save "
            "instead."
        ),
        "input_schema": _obj({
            "width": {"type": "integer"},
            "height": {"type": "integer"},
            "dpi": {"type": "integer"},
            "discard_unsaved_changes": {"type": "boolean"},
        }),
    },
    {
        "name": "open_document",
        "description": (
            "Open an SVG, .kpaint or PNG file in the window. Refuses to "
            "discard unsaved work unless discard_unsaved_changes is set."
        ),
        "input_schema": _obj({
            "path": {"type": "string", "description": "Absolute file path."},
            "discard_unsaved_changes": {"type": "boolean"},
        }, ["path"]),
    },
    {
        "name": "save_document",
        "description": (
            "Save the drawing. With no path it saves over the file the "
            "user already has open; a path saves a copy there and makes "
            "it the current file. SVG is the native, fully editable "
            "format."
        ),
        "input_schema": _obj({
            "path": {"type": "string",
                     "description": "Absolute path ending in .svg or "
                                    ".kpaint. Omit to save in place."},
        }),
    },
    {
        "name": "export_document",
        "description": (
            "Export a flattened copy: PNG, PDF or SVG, chosen by the "
            "path's extension. The page is exported at its own dpi, so a "
            "PDF comes out at the figure's true physical size."
        ),
        "input_schema": _obj({
            "path": {"type": "string",
                     "description": "Absolute path ending in .png, .pdf "
                                    "or .svg."},
        }, ["path"]),
    },
]

#: Name -> definition, for the executor and the access-level checks.
BY_NAME = {t["name"]: t for t in TOOLS}
