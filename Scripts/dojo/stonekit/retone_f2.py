"""Stone kit f2 round 2: re-tone kit materials in place (no geometry change; the FBX carry no material values, Unreal
builds its own instances), so a recipe change in sk_shared.KIT_MATS / LIB_VARIANTS reaches the blends without a
25-minute rebuild. Rebuilds each named recipe, remaps every user of the old datablock onto it, and patches the
catalogue's recipe records (tracks.*.materials) under the catalogue lock.

  blender -b --factory-startup --python Scripts/dojo/stonekit/retone_f2.py -- --mats M_DKT_JointDark,M_DKT_GlassAmberWarm
Blends: Assets/Dojo/DojoStoneKit.blend (under sk_shared.file_lock), wall/DojoStoneKit_wall.blend,
        stairs/StairKit_build.blend
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sk_shared as sk  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
MATS = ARGS[ARGS.index("--mats") + 1].split(",")
BLENDS = [sk.BLEND, sk.WORK / "wall" / "DojoStoneKit_wall.blend", sk.WORK / "stairs" / "StairKit_build.blend"]


def retone():
    n = 0
    for name in MATS:
        old = bpy.data.materials.get(name)
        if old is None:
            continue
        old.name = name + "__old"
        new = sk.kit_material(name) if name in sk.KIT_MATS else sk.lib_variant(name)
        old.user_remap(new)
        bpy.data.materials.remove(old)
        n += 1
    return n


def main():
    assert_owner("DojoStoneKit", "claude")
    for b in BLENDS:
        if not b.exists():
            continue
        ctx = sk.file_lock(sk.BLEND) if b == sk.BLEND else None
        if ctx:
            ctx.__enter__()
        try:
            bpy.ops.wm.open_mainfile(filepath=str(b))
            n = retone()
            bpy.ops.wm.save_as_mainfile(filepath=str(b))
            print("RETONED", b.name, n, flush=True)
        finally:
            if ctx:
                ctx.__exit__(None, None, None)
    with sk.file_lock(sk.CATALOG):
        cat = json.loads(sk.CATALOG.read_text(encoding="utf-8"))
        for tr in cat.get("tracks", {}).values():
            mats = tr.get("materials") or {}
            for name in MATS:
                if name in mats and name in sk.KIT_MATS and isinstance(mats[name], dict):
                    r = sk.KIT_MATS[name]
                    mats[name]["tint_linear"] = list(r["tint"])
                    mats[name]["flatten_to_mean"] = r["flat"]
                    mats[name]["normal_strength"] = r["normal"]
                    mats[name]["mean_linear"] = [round(a * b, 4) for a, b in zip(sk.TEX_MEAN, r["tint"])]
        tmp = sk.CATALOG.with_suffix(".retone.tmp")
        tmp.write_text(json.dumps(cat, indent=1), encoding="utf-8")
        tmp.replace(sk.CATALOG)


main()
