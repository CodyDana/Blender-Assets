#!/usr/bin/env python3
"""Self-tests for the Card Shop Kit library, including negative cases (CARDSHOP_KIT_SPEC.md 7.2). System Python:

    py -3 Scripts/cardshop/test_csk.py            (Pillow needed for the atlas tests; skipped without it)

Covers: fit maths (a slot that is too small, a pack 0.1 mm over a box, neighbour overlap, touching allowed, rotated
seating), the stack rule, the grid solver's spec example, the deny scan (hits and the PriceTag / Stage false
positives), the LOD screen-size rule, the pack -> box map, and csk_pack_cards (cell rects, padding, bad input).
The Blender half (qa_check, exports, hashes) is exercised by build_csk.py itself, which fails on any check.
Exit code 0 when every test passes.
"""
from __future__ import annotations

import json
import sys
import tempfile
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tools"))

from csk_lib import fit  # noqa: E402
from csk_lib import spec as S  # noqa: E402

RESULTS = []


class Skip(Exception):
    pass


def test(fn):
    try:
        fn()
        RESULTS.append((fn.__name__, True, ""))
    except Skip as exc:
        RESULTS.append((fn.__name__, True, f"SKIP {exc}"))
    except Exception:  # noqa: BLE001
        RESULTS.append((fn.__name__, False, traceback.format_exc(limit=3)))
    return fn


CARD = ((-31.5, -44.0, 0.0), (31.5, 44.0, 0.3))
PACK = ((-33.5, -58.5, 0.0), (33.5, 58.5, 4.0))


@test
def contain_fits_and_rejects_too_small():
    cav = ((-32.5, -45.0, 0.0), (32.5, 45.0, 1.0))
    ok = fit.check_contain("slab", cav, [("Card", (0, 0, 0), (0, 0, 0))], "card", CARD)
    assert all(r["passed"] for r in ok), ok
    small = ((-31.0, -45.0, 0.0), (31.0, 45.0, 1.0))           # 1 mm too narrow
    bad = fit.check_contain("slab", small, [("Card", (0, 0, 0), (0, 0, 0))], "card", CARD)
    assert not bad[0]["passed"]


@test
def pack_over_box_by_0_1mm_fails():
    s = S.BOX_BOOSTER_S
    inner_z1 = s["h"]
    cav = ((-68.0, -38.0, 2.0), (68.0, 38.0, inner_z1))
    loc_ok = (-33.5, -34.0, 2.0 + 58.5)
    r = fit.check_contain("box", cav, [("P", loc_ok, (90, 0, 0))], "pack", PACK)
    assert r[0]["passed"], r
    loc_bad = (-34.6, -34.0, 2.0 + 58.5)                        # left edge at -68.1: 0.1 mm past the wall
    r = fit.check_contain("box", cav, [("P", loc_bad, (90, 0, 0))], "pack", PACK)
    assert not r[0]["passed"]


@test
def standing_pack_rotation_maps_length_to_z():
    b = fit.transform_box(PACK, (0, 0, 0), (90, 0, 0))
    assert abs(b[0][2] + 58.5) < 1e-9 and abs(b[1][2] - 58.5) < 1e-9, b
    assert abs(b[0][1] + 4.0) < 1e-9 and abs(b[1][1]) < 1e-9, b


@test
def neighbours_touching_pass_overlapping_fail():
    cav = ((-100, -100, 0), (100, 100, 10))
    touch = [("A", (-31.5, 0, 0), (0, 0, 0)), ("B", (31.5, 0, 0), (0, 0, 0))]
    assert all(r["passed"] for r in fit.check_contain("x", cav, touch, "card", CARD))
    lap = [("A", (-31.4, 0, 0), (0, 0, 0)), ("B", (31.4, 0, 0), (0, 0, 0))]
    res = fit.check_contain("x", cav, lap, "card", CARD)
    assert any(r["test"] == "contain_neighbours" and not r["passed"] for r in res), res


@test
def grid_solver_matches_spec_example():
    # spec 4.2: interior 1740 x 356, Slab 94 x 144 -> 18 x 2; Card 77 x 102 -> 22 x 3
    from csk_lib.geom import solve_grid
    g = solve_grid(1740, 356, 180, "Slab")
    assert (g["cols"], g["rows"]) == (18, 2), g
    g = solve_grid(1740, 356, 180, "Card")
    assert (g["cols"], g["rows"]) == (22, 3), g
    assert solve_grid(1740, 356, 100, "BoxS") is None           # a 125 mm box does not fit 100 clear


@test
def level_check_catches_hull_intrusion():
    level = {"socket": "Level_T", "interior_mm": [400, 200], "clear_h_mm": 100}
    grid = {"class": "Card", "cols": 4, "rows": 1, "pitch_mm": [77, 102], "first_mm": [-115.5, 0]}
    clear = fit.check_level("fx", level, (0, 0, 0), grid, "card", CARD, [((-500, -500, -10), (500, 500, 0))])
    assert all(r["passed"] for r in clear), clear                  # the shelf under it only touches
    hit = fit.check_level("fx", level, (0, 0, 0), grid, "card", CARD, [((-10, -10, 0.1), (10, 10, 5))])
    assert any(r["test"] == "level_hulls" and not r["passed"] for r in hit)


@test
def stack_rule_caps_at_clear_height():
    box = ((-70, -40, 0), (70, 40, 125))
    r = fit.check_stack("box", box, {"pitch_mm": 125, "max": 4}, 253.0)
    assert r["passed"] and r["effective_max"] == 2, r
    r = fit.check_stack("box", box, {"pitch_mm": 125, "max": 4}, 100.0)
    assert not r["passed"]
    r = fit.check_stack("box", box, {"pitch_mm": 120, "max": 4}, 500.0)   # pitch below the render height
    assert not r["passed"]


@test
def deny_scan_hits_and_false_positives():
    assert S.deny_hits("SM_CSK_PSA_Slab")
    assert S.deny_hits("Pokemon booster")
    assert S.deny_hits("M_TAG_Label")
    for clean in ("PriceTag_S1_01", "SM_CSK_Stage", "hang tag", "Vintage", "tags", "Pyrecall", "Clearmark Grading"):
        assert not S.deny_hits(clean), (clean, S.deny_hits(clean))


@test
def screen_sizes_follow_the_kit_rule():
    ss = S.screen_sizes(71.0, 3)                                   # a handheld pack, R = 71 mm
    assert ss[0] == 1.0 and abs(ss[1] - 1.778 * 0.071 / 1.5) < 1e-6 and abs(ss[2] - 1.778 * 0.071 / 4) < 1e-6
    assert S.lod_class(71).name == "handheld" and S.lod_class(300).name == "medium" and S.lod_class(900).name == "fixture"


@test
def pack_box_map_fits_by_the_numbers():
    b, p = S.BOX_BOOSTER_S, S.PACK_STD
    inner = (b["w"] - 2 * b["board"], b["d"] - 2 * b["board"], b["h"] - b["board"])
    cols, rows = b["packs"]
    assert cols * p["w"] <= inner[0] and rows * b["pack_pitch"] <= inner[1] and p["h"] <= inner[2]
    assert b["pack_pitch"] >= p["t"]


@test
def pack_cards_tool_rects_and_padding():
    try:
        from PIL import Image
    except ImportError:
        raise Skip("Pillow is not installed")
    import csk_pack_cards as P
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for i, col in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255))):
            Image.new("RGB", (630, 880), col).save(td / f"{i:02d}.png")
        idx = P.pack(sorted(td.glob("*.png")), td / "atlas.png", 1024, (2, 2), (512, 512), (315, 440), 16)
        assert len(idx["cells"]) == 3
        c1 = idx["cells"][1]
        assert c1["rect_px"] == [512 + 98, 36, 315, 440], c1
        assert abs(c1["rect_uv"][0] - (512 + 98) / 1024) < 1e-12
        im = Image.open(td / "atlas.png").convert("RGB")
        assert im.getpixel((512 + 98 - 16, 36 - 16)) == (0, 255, 0)     # padding repeats the edge colour
        assert im.getpixel((512 + 98 - 17, 36)) == (0, 0, 0)            # nothing beyond the padding
        assert json.loads((td / "atlas.json").read_text())["uv_origin"].startswith("top-left")
        try:
            P.pack(sorted(td.glob("0*.png")), td / "bad.png", 1024, (2, 2), (512, 512), (500, 440), 16)
            raise AssertionError("content + padding larger than the cell was accepted")
        except ValueError:
            pass


def main() -> int:
    for name, ok, err in RESULTS:
        tag = "SKIP " if err.startswith("SKIP") else ("PASS " if ok else "FAIL ")
        print(tag + name + ("" if ok and not err else " " + err if ok else "\n" + err))
    passed = all(ok for _, ok, _ in RESULTS)
    print(f"CSK_SELFTEST {'PASSED' if passed else 'FAILED'} {sum(ok for _, ok, _ in RESULTS)}/{len(RESULTS)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
