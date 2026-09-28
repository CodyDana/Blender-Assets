"""Derive the version-2 recolour constants of the PAPER BOMB's tag (ADDED 2026-09-26, the paper bomb's exact-match pass).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/unreal/materials/maps/derive_constants_paperbomb.py

``derive_constants.paper_part`` with ONE change, in the Paper Colour Limit (derive_constants.py is imported, never edited:
the other items' recolour_constants.json record its sha256, so that file must not change):

    Paper Colour Limit = max(AlbedoCeiling / p99.9 of the paper weight,  max channel of the default Paper Colour + 1e-5)

The traced face carries the reference's own paper, whose blue channel varies more than the old procedural paper's
(paper weight p99.9 1.209 against 1.064), so the base rule alone falls to 0.796 - under the default paper's own 0.912 -
and the v2 twin would scale the SHIPPED look down (default diff 0.122, gate default_equals_v1 FAIL). The limit is
raised to just above the default: a lighter buyer paper still stops there, and only the bluest 0.1 % of its grain can
touch the albedo ceiling. Same gates as derive_constants.paper_part: the v2 twin at the default colour equals the v1
contract, and the default paper is below the limit. Exit 1 if either fails.

Writes Exports/PaperBomb/Textures/Recolour/recolour_constants.json (the schema of the other items' files; the generator
block names THIS script and records derive_constants.py's sha256 as the base). Re-run it after
make_paperbomb_recolour_maps.py (run_build.sh's maps_check refuses a stale chain).
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import derive_constants as dc  # noqa: E402  (its main() is not run: only its constants and helpers are used)
import np_twin as tw  # noqa: E402
import recolour_common as rc  # noqa: E402

VERSION = "2.0.0-paperbomb"
GROUP, PART = "PaperBomb", "Tag"
FILES = dc.PAPER[GROUP][PART]


def paper_part(files: dict, gen: dict) -> dict:
    g = dict(gen["params"])
    pd8, _, _ = rc.png_read(rc.PROJECT / files["pd"])
    iw8, _, _ = rc.png_read(rc.PROJECT / files["iw"])
    w = tw.s2l(pd8[..., :3] / 255.0) * g["Paper Weight Scale"]
    wmax = w.max(axis=-1)
    p999 = float(np.percentile(wmax, 99.9))
    limit_rule = round(g["Albedo Ceiling"] / p999, 5)
    limit = max(limit_rule, round(float(np.max(g["Paper Colour"][:3])) + 1e-5, 5))
    red = np.asarray(g["Red Ink Colour"][:3], np.float64)
    sat = float((red.max() - red.min()) / red.max())
    p = dict(g)
    p["Paper Colour Limit"] = limit
    p["Red Ink Pool Default Saturation"] = sat
    maps = {"pd_rgb": tw.s2l(pd8[..., :3] / 255.0), "pd_a": pd8[..., 3:4] / 255.0, "iw": iw8 / 255.0,
            "ao": np.ones(pd8.shape[:2] + (1,))}
    v2, _, der = tw.paper_albedo(p, maps, ao_in_colour=0.0)
    # v1 (the build's first graph): no floor / limit / chroma fade - exactly as derive_constants.paper_part
    paper = np.asarray(g["Paper Colour"][:3]); black = np.asarray(g["Black Ink Colour"][:3])
    bd = (black + (paper - black) * g["Black Ink Dry Paper Mix"]) * np.asarray(g["Black Ink Dry Gain"][:3])
    rd = tw.s2l(np.clip(g["Red Ink Dry Value Scale"] * tw.l2s(red), 0, 1))
    y = float(red @ tw.LUM)
    rp = (y + (red - y) * g["Red Ink Pool Saturation"]) * np.asarray(g["Red Ink Pool Gain"][:3])
    iw = maps["iw"]
    v1 = np.minimum(paper * maps["pd_rgb"] * g["Paper Weight Scale"] + black * iw[..., 0:1] + bd * iw[..., 1:2]
                    + red * iw[..., 2:3] + rd * iw[..., 3:4] + rp * maps["pd_a"], g["Albedo Ceiling"])
    diff = float(np.abs(v2 - v1).max())
    gates = {"default_equals_v1": {"max_abs": diff, "pass": bool(diff < 1e-9)},
             "paper_default_below_limit": {"max3": float(paper.max()), "limit": limit, "pass": bool(paper.max() < limit)}}
    passed = all(v["pass"] for v in gates.values())
    dc.log(f"{GROUP}/{PART}: paper limit {limit} (rule {limit_rule}, p99.9 weight {p999:.5f}), red saturation "
           f"{sat:.5f}, default diff {diff:.2e} -> {'PASS' if passed else 'FAIL'}")
    return {"instance": gen["instance"], "master": "M_PaperInk_Master", "params": p,
            "derivation": {"paper_weight_p999_maxchannel": p999, "paper_weight_max": float(wmax.max()),
                           "paper_colour_limit_rule": limit_rule,
                           "paper_colour_limit_raised_to_default": bool(limit > limit_rule),
                           "derived_default": der},
            "gates": gates, "pass": passed}


def main() -> int:
    try:
        import bpy
        blender = bpy.app.version_string
    except ImportError:
        blender = None
    maps_json = rc.PROJECT / f"Exports/{GROUP}/Textures/Recolour/recolour_maps.json"
    gen = json.loads(maps_json.read_text(encoding="utf-8"))
    doc = {"schema": "ninjapack.recolour_constants/1", "item": GROUP, "generated": datetime.date.today().isoformat(),
           "generator": {"script": rc.rel(__file__), "script_sha256": rc.sha256(__file__),
                         "base_script": rc.rel(dc.__file__), "base_script_sha256": rc.sha256(dc.__file__),
                         "twin": rc.rel(tw.__file__), "twin_sha256": rc.sha256(tw.__file__),
                         "common_sha256": rc.sha256(rc.__file__), "version": VERSION, "blender": blender},
           "source": {"recolour_maps": rc.rel(maps_json), "sha256": rc.sha256(maps_json)},
           "merge_rule": "np_spec.py: params here override recolour_maps.json params of the same instance",
           "parts": {PART: paper_part(FILES, gen["parts"][PART])}}
    doc["pass"] = all(v["pass"] for v in doc["parts"].values())
    out = rc.PROJECT / f"Exports/{GROUP}/Textures/Recolour/recolour_constants.json"
    rc.write_json(out, doc)
    dc.log(f"wrote {rc.rel(out)} pass={doc['pass']}")
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    code = 1
    try:
        code = main()
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout.flush()
        import os
        os._exit(code)
