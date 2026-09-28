"""Look-match round 1 (sword): render the SHIPPED asset (an exported FBX + its baked PNGs, nothing else) in the
comparison views of sfv4_lm_views.py.

    blender -b --factory-startup --python sfv4_lm_render.py -- --fbx <fbx> --tex <texture dir> --out <dir>
        [--tag after_] [--views hilt_front,...] [--lod 0] [--samples 96]

``--fbx``/``--tex`` default to Exports/SnowFlower/v4 (the current shipped bytes).  The pre-look-match state renders from
Backups/SnowFlower_v4_pre_lookmatch_2026-09-27/Exports_v4 (read only).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_look as LK  # noqa: E402
import sfv4_spec as S  # noqa: E402
import sfv4_lm_views as LV  # noqa: E402

ROOT = HERE.parents[2]
ALL_VIEWS = "hilt_front,hilt_side,hilt_back,full_front,full_side,full_back,det_guard,det_pommel,det_blade"


def load(fbx: Path, tex: Path, lod: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    mats = {}
    for slot, stem in S.SLOT_TEX.items():
        mats[slot] = LK.make_game_material(slot + "_shipped", tex / f"{stem}_BC.png", tex / f"{stem}_ORM.png",
                                           tex / f"{stem}_N.png")
    # the pre-look-match export had two slot names (Steel / Wrap) in an earlier revision; map by stem too
    alias = {"M_SnowFlower_Steel": "M_SnowFlower_Fittings", "M_SnowFlower_Wrap": "M_SnowFlower_Grip"}
    for o in bpy.data.objects:
        if o.type == "MESH":
            for i, sl in enumerate(o.material_slots):
                name = sl.material.name.split(".")[0] if sl.material else ""
                name = alias.get(name, name)
                if name in mats:
                    o.material_slots[i].material = mats[name]
            is_lod = f"_LOD{lod}" in o.name
            o.hide_render = not is_lod or o.name.startswith("UCX_")
        elif o.type == "EMPTY":
            o.hide_render = True


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--fbx", default=str(ROOT / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.fbx"))
    ap.add_argument("--tex", default=str(ROOT / "Exports" / "SnowFlower" / "v4" / "Textures"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--views", default=ALL_VIEWS)
    ap.add_argument("--lod", type=int, default=0)
    ap.add_argument("--samples", type=int, default=96)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if not out.is_absolute():
        out = ROOT / out
    out = out.resolve()
    if not str(out).lower().startswith(str(ROOT.resolve()).lower()):
        raise SystemExit(f"refusing to write outside the project: {out}")
    out.mkdir(parents=True, exist_ok=True)
    load(Path(a.fbx), Path(a.tex), a.lod)
    for v in a.views.split(","):
        LV.render_view(v, out / f"{a.tag}{v}.png", samples=a.samples)
        print("[LMR] view", v, flush=True)
    print("LMR_DONE")


if __name__ == "__main__":
    main()
