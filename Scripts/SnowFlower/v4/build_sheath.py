"""Snow Flower sheath build (headless Blender 5.2).

    blender -b --factory-startup --python Scripts/SnowFlower/v4/build_sheath.py -- --stage <stage>

Stages (each its own process, in order):
    fit     seat the SHIPPED v4 sword FBX (read-only) in the reference outline; tilt, offset, swept cavity per LOD
    geo     build high-poly + LOD0/1/2, pack the atlas, paint the lacquer, save the work blend
    bake    bake NORMAL / AO / BC / ROUGH / METAL per part (selected-to-active) into float arrays
    maps    compose the shipped PNGs (DirectX normals, ORM, sRGB BC, lacquer Detail)
    game    join LODs, game materials, UCX hulls, sockets, LOD group -> Assets/SnowFlower/SnowFlower_Sheath.blend
            (+ the high-poly -> WorkFiles/SnowFlower/v4/SnowFlower_Sheath_HighPoly.blend)
    export  Scripts/pipeline/export_fbx.py + qa_check -> Exports/SnowFlower/v4/SM_SnowFlower_Sheath.fbx
The sword's files and every revision-3 file are only ever read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "shv4_lib"))   # look-match: the frozen sfv4_* helpers (the sword builder edits the live ones)
sys.path.insert(0, str(ROOT / "Scripts"))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import shv4_spec as S  # noqa: E402

WORK = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sheath_build"
BAKE_DIR = WORK / "bake"
WORK_BLEND = WORK / "SH4_work.blend"
HIGH_BLEND = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "SnowFlower_Sheath_HighPoly.blend"
GAME_BLEND = ROOT / "Assets" / "SnowFlower" / "SnowFlower_Sheath.blend"
EXPORT_DIR = ROOT / "Exports" / "SnowFlower" / "v4"
TEX_DIR = EXPORT_DIR / "Textures"
NAME = "SM_SnowFlower_Sheath"
TEX_STEM = "T_SnowFlower_Sheath"
SLOT_LACQUER = S.SLOT_LACQUER
SLOT_SILVER = S.SLOT_SILVER
#: files this build must never write (revision 3, the finished v4 sword)
FORBIDDEN = [ROOT / "Assets" / "SnowFlower" / "SnowFlower_Master.blend",
             ROOT / "Assets" / "SnowFlower" / "SnowFlower_Game.blend",
             ROOT / "Assets" / "SnowFlower" / "SnowFlower_Game_v4.blend",
             ROOT / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.fbx",
             ROOT / "Exports" / "SnowFlower" / "v4" / "SM_SnowFlower.sockets.json"]


def log(*a):
    print("[SH4]", *a, flush=True)


def guard_paths(*paths):
    for p in paths:
        for f in FORBIDDEN:
            if Path(p).resolve() == f.resolve():
                raise RuntimeError(f"refusing to write {f}")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--channels", default="NORMAL,AO,BC,ROUGH,METAL")
    a = ap.parse_args(argv)
    t = time.time()
    if a.stage == "fit":
        import shv4_fit
        shv4_fit.run()
    elif a.stage in ("geo", "bake", "maps", "game", "export"):
        import shv4_stages as ST
        getattr(ST, "stage_" + a.stage)(**({"channels": [c.strip() for c in a.channels.split(",") if c.strip()]}
                                            if a.stage == "bake" else {}))
    else:
        raise SystemExit(f"unknown stage {a.stage}")
    log(f"stage {a.stage} finished in {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
