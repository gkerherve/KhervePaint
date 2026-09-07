"""MCP tool execution against a live KhervePaint window.

Run with: python -m pytest tests/  (offscreen Qt).

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import base64
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from khervepaint import mcp_schema
from khervepaint.canvas import GroupItem
from khervepaint.mcp_server import IMAGE_KEY, valid_png_b64
from khervepaint.mcp_tools import McpToolExecutor


@pytest.fixture
def ex(win):
    """A fresh executor on the shared, reset window (`win` lives in
    conftest.py, so both MCP test modules share one MainWindow)."""
    return McpToolExecutor(win)


def call(ex, _tool, **params):
    """Run a tool and insist it succeeded.  The first argument is
    positional-only in spirit: several tools take a "name" of their
    own."""
    result = ex.execute(_tool, params)
    assert "error" not in result, f"{_tool} failed: {result.get('error')}"
    return result


# ── the contract ───────────────────────────────────────────────────

def test_every_declared_tool_has_an_implementation(ex):
    for tool in mcp_schema.TOOLS:
        assert hasattr(ex, f"_t_{tool['name']}"), \
            f"{tool['name']} is declared but not implemented"


def test_every_implementation_is_declared(ex):
    implemented = {n[3:] for n in dir(ex) if n.startswith("_t_")}
    assert implemented == set(mcp_schema.BY_NAME)


def test_an_unknown_tool_is_an_error_not_a_crash(ex):
    assert "error" in ex.execute("draw_a_cat", {})


# ── inspection ─────────────────────────────────────────────────────

def test_document_info_reports_pixels_and_millimetres(ex, win):
    win.scene.resize_canvas(800, 600)
    win.scene.dpi = 254                     # 10 px per mm, exactly
    info = call(ex, "get_document_info")
    assert info["width_px"] == 800
    assert info["pixels_per_mm"] == pytest.approx(10.0)
    assert info["width_mm"] == pytest.approx(80.0)
    assert "top-left" in info["origin"]


def test_draw_then_list_round_trips_the_geometry(ex):
    made = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 10, "y": 20, "w": 100, "h": 50,
         "fill": "#ff0000", "stroke": "#000000"},
        {"shape": "text", "text": "Hello", "x": 30, "y": 200},
    ])
    assert made["created"] == 2
    listed = call(ex, "list_items")
    assert listed["count"] == 2
    rect = listed["items"][0]
    assert rect["kind"] == "rect"
    assert (rect["x"], rect["y"]) == (pytest.approx(10, abs=2),
                                      pytest.approx(20, abs=2))
    assert rect["fill"] == "#ff0000"
    assert listed["items"][1]["text"] == "Hello"


def test_drawn_positions_are_not_snapped_to_the_grid(ex, win):
    win.scene.snap_enabled = True
    ident = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 0, "y": 0, "w": 40, "h": 40}])["ids"][0]
    call(ex, "update_items", changes=[{"id": ident, "x": 33.5, "y": 71.5}])
    item = call(ex, "list_items", ids=[ident])["items"][0]
    assert item["x"] == pytest.approx(33.5, abs=0.01)
    assert item["y"] == pytest.approx(71.5, abs=0.01)
    assert win.scene.snap_enabled is True     # restored for the user


def test_render_canvas_returns_a_real_png(ex):
    call(ex, "draw", shapes=[{"shape": "circle", "x": 5, "y": 5,
                              "w": 50, "h": 50, "fill": "#00aa00"}])
    shot = call(ex, "render_canvas", max_width=120)
    assert valid_png_b64(shot[IMAGE_KEY])
    assert shot["rendered_width"] <= 120
    base64.b64decode(shot[IMAGE_KEY])


def test_render_hides_the_selection_handles_but_keeps_the_selection(ex, win):
    ident = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 10, "y": 10, "w": 60, "h": 60}])["ids"][0]
    call(ex, "select_items", ids=[ident])
    call(ex, "render_canvas")
    assert [i for i in win.scene.selectedItems()], \
        "rendering must not clear what the user had selected"


# ── editing ────────────────────────────────────────────────────────

def test_update_moves_resizes_and_restyles(ex):
    ident = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 0, "y": 0, "w": 40, "h": 40}])["ids"][0]
    call(ex, "update_items", changes=[
        {"id": ident, "x": 100, "y": 120, "w": 80, "h": 60,
         "stroke": "#123456", "fill": "none", "opacity": 0.5}])
    item = call(ex, "list_items", ids=[ident])["items"][0]
    assert item["w"] == pytest.approx(80, abs=3)
    assert item["h"] == pytest.approx(60, abs=3)
    assert item["x"] == pytest.approx(100, abs=1)
    assert item["stroke"] == "#123456"
    assert item["fill"] == "none"
    assert item["opacity"] == pytest.approx(0.5)


def test_a_stale_id_says_so_instead_of_crashing(ex):
    ident = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 0, "y": 0, "w": 10, "h": 10}])["ids"][0]
    call(ex, "delete_items", ids=[ident])
    result = ex.execute("update_items", {"changes": [{"id": ident, "x": 5}]})
    assert "error" in result and "list_items" in result["error"]


def test_group_then_ungroup(ex, win):
    ids = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 0, "y": 0, "w": 30, "h": 30},
        {"shape": "rect", "x": 60, "y": 0, "w": 30, "h": 30}])["ids"]
    group_id = call(ex, "group_items", ids=ids)["group_id"]
    assert len(win.scene.vector_items()) == 1
    assert isinstance(win.scene.vector_items()[0], GroupItem)
    call(ex, "ungroup_items", ids=[group_id])
    assert len(win.scene.vector_items()) == 2


def test_align_left_lines_the_edges_up(ex):
    ids = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 10, "y": 0, "w": 30, "h": 30},
        {"shape": "rect", "x": 90, "y": 60, "w": 30, "h": 30},
        {"shape": "rect", "x": 50, "y": 120, "w": 30, "h": 30}])["ids"]
    call(ex, "align_items", ids=ids, how="left")
    lefts = [i["x"] for i in call(ex, "list_items", ids=ids)["items"]]
    assert max(lefts) - min(lefts) < 0.5


def test_distribute_spaces_the_middle_item_evenly(ex):
    ids = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 0, "y": 0, "w": 20, "h": 20},
        {"shape": "rect", "x": 30, "y": 0, "w": 20, "h": 20},
        {"shape": "rect", "x": 200, "y": 0, "w": 20, "h": 20}])["ids"]
    call(ex, "align_items", ids=ids, how="distribute_x")
    centres = sorted(i["x"] + i["w"] / 2
                     for i in call(ex, "list_items", ids=ids)["items"])
    assert centres[1] - centres[0] == pytest.approx(
        centres[2] - centres[1], abs=0.5)


def test_order_items_brings_a_shape_to_the_front(ex, win):
    ids = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 0, "y": 0, "w": 30, "h": 30},
        {"shape": "rect", "x": 5, "y": 5, "w": 30, "h": 30}])["ids"]
    call(ex, "order_items", ids=[ids[0]], where="front")
    top = call(ex, "list_items")["items"][-1]
    assert top["id"] == ids[0]


# ── libraries and models ───────────────────────────────────────────

def test_list_symbols_names_every_palette(ex):
    libs = {row["library"] for row in call(ex, "list_symbols")["libraries"]}
    assert libs == set(mcp_schema.LIBRARY_KEYS)


def test_place_symbol_puts_a_group_where_asked(ex):
    names = call(ex, "list_symbols", library="optics")
    first = names["sections"][0]["elements"][0]["name"]
    placed = call(ex, "place_symbol", library="optics", name=first,
                  x=200, y=150)
    box = placed["item"]
    assert box["x"] + box["w"] / 2 == pytest.approx(200, abs=2)
    assert box["y"] + box["h"] / 2 == pytest.approx(150, abs=2)


def test_an_unknown_symbol_name_points_at_list_symbols(ex):
    result = ex.execute("place_symbol", {"library": "vacuum",
                                         "name": "flux capacitor",
                                         "x": 10, "y": 10})
    assert "list_symbols" in result["error"]


def test_place_model_makes_a_tagged_rotatable_model(ex, win):
    placed = call(ex, "place_model", name="water", x=150, y=150)
    assert placed["placed"] == "water"
    item = win.scene.vector_items()[0]
    assert getattr(item, "mol_name", None) == "water"
    assert placed["item"]["model"] == "water"


def test_build_molecule_adds_hydrogens_and_geometry(ex):
    built = call(ex, "build_molecule", atoms=["C", "C", "O"],
                 bonds=[[0, 1, 1], [1, 2, 1]], x=200, y=200,
                 name="ethanol")
    assert built["atoms"] > 3          # hydrogens filled in for us
    assert built["item"]["model"] == "ethanol"


def test_configure_model_stacks_a_crystal_into_a_supercell(ex):
    placed = call(ex, "place_model", name="bcc", x=200, y=200)
    out = call(ex, "configure_model", id=placed["item"]["id"],
               cells=[2, 2, 1], az=25)
    assert out["item"]["cells"] == [2, 2, 1]


def test_a_placed_model_survives_undo_and_redo_where_it_was(ex, win):
    """Guards the snapshot: a placement that moves the item after
    emitting would record it somewhere it never sat, and redo would
    put it there."""
    call(ex, "place_model", name="water", x=220, y=180)
    while win._undo_stack.canUndo():
        win._undo_stack.undo()
    assert win.scene.vector_items() == []
    while win._undo_stack.canRedo():
        win._undo_stack.redo()
    centre = win.scene.vector_items()[0].sceneBoundingRect().center()
    assert centre.x() == pytest.approx(220, abs=1)
    assert centre.y() == pytest.approx(180, abs=1)


def test_configure_model_refuses_an_ordinary_shape(ex):
    ident = call(ex, "draw", shapes=[
        {"shape": "rect", "x": 0, "y": 0, "w": 10, "h": 10}])["ids"][0]
    result = ex.execute("configure_model", {"id": ident, "az": 10})
    assert "not a molecule or crystal" in result["error"]


def test_list_models_flags_what_can_be_stacked(ex):
    sections = call(ex, "list_models", kind="crystals")["sections"]
    names = {m["name"]: m["stackable"]
             for s in sections for m in s["models"]}
    assert names["bcc"] is True
    assert names["hcp"] is False


# ── canvas and documents ───────────────────────────────────────────

def test_set_canvas_resizes_and_keeps_the_content(ex):
    call(ex, "draw", shapes=[{"shape": "rect", "x": 10, "y": 10,
                              "w": 40, "h": 40}])
    info = call(ex, "set_canvas", width=640, height=480, grid_mm=2.5)
    assert (info["width_px"], info["height_px"]) == (640, 480)
    assert info["grid_mm"] == 2.5
    assert info["item_count"] == 1


def test_new_document_refuses_to_bin_unsaved_work(ex):
    call(ex, "draw", shapes=[{"shape": "rect", "x": 0, "y": 0,
                              "w": 10, "h": 10}])
    result = ex.execute("new_document", {})
    assert "unsaved" in result["error"]
    call(ex, "new_document", discard_unsaved_changes=True)
    assert call(ex, "get_document_info")["item_count"] == 0


def test_save_and_reopen_round_trips_the_drawing(ex, tmp_path):
    call(ex, "draw", shapes=[
        {"shape": "rect", "x": 10, "y": 10, "w": 60, "h": 40,
         "fill": "#3366cc"},
        {"shape": "ellipse", "x": 100, "y": 30, "w": 50, "h": 50}])
    path = tmp_path / "figure.svg"
    call(ex, "save_document", path=str(path))
    assert path.exists()
    info = call(ex, "open_document", path=str(path),
                discard_unsaved_changes=True)
    assert info["item_count"] == 2
    assert info["path"] == str(path)


def test_saving_clears_the_unsaved_flag(ex, tmp_path):
    call(ex, "draw", shapes=[{"shape": "rect", "x": 0, "y": 0,
                              "w": 10, "h": 10}])
    call(ex, "save_document", path=str(tmp_path / "a.svg"))
    assert call(ex, "get_document_info")["unsaved_changes"] is False


def test_export_writes_png_and_pdf(ex, tmp_path):
    call(ex, "draw", shapes=[{"shape": "rect", "x": 0, "y": 0,
                              "w": 30, "h": 30, "fill": "#222222"}])
    for ext in (".png", ".pdf", ".svg"):
        out = tmp_path / f"fig{ext}"
        call(ex, "export_document", path=str(out))
        assert out.exists() and out.stat().st_size > 0


def test_export_rejects_a_format_it_cannot_write(ex, tmp_path):
    result = ex.execute("export_document",
                        {"path": str(tmp_path / "fig.docx")})
    assert "png" in result["error"]


def test_open_refuses_a_file_that_is_not_a_drawing(ex, tmp_path):
    junk = tmp_path / "notes.txt"
    junk.write_text("hello")
    result = ex.execute("open_document", {"path": str(junk),
                                          "discard_unsaved_changes": True})
    assert ".svg" in result["error"]


def test_load_example_replaces_the_document(ex):
    name = call(ex, "list_examples")["examples"][0]["name"]
    out = call(ex, "load_example", name=name, discard_unsaved_changes=True)
    assert out["item_count"] > 0
