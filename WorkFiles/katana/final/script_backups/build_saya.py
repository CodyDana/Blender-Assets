"""Saya (SM_Katana_Saya) build for the basic katana (headless Blender 5.2).

    blender -b --factory-startup --python Scripts/Katana/build_saya.py -- --stage <stage>

Stages (each its own process, in order):
    fit      seat the SHIPPED katana FBX (exact bytes, sha256-checked) and derive the cavity per LOD (saya_fit)
    geo      LOD0/1/2 from the generators (saya_parts), pack the atlas, save the work blend (+ part data)
    ao       Cycles AO bake of the LOD0 game mesh into the atlas
    maps     paint BC / ORM / N from the parts' parametric attributes + the AO (saya_tex)
    game     one mesh per LOD with the 2 slots, 5 UCX hulls, 4 sockets, LOD group -> Assets/Katana/Saya.blend
    export   Scripts/pipeline export_fbx + qa_check -> Exports/Katana/SM_Katana_Saya.fbx (+ .sockets.json)
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "Scripts"))

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import saya_spec as S  # noqa: E402

WORK = ROOT / "WorkFiles" / "katana" / "saya_build"
BAKE_DIR = WORK / "bake"
WORK_BLEND = WORK / "saya_work.blend"
GAME_BLEND = ROOT / "Assets" / "Katana" / "Saya.blend"
EXPORT_DIR = ROOT / "Exports" / "Katana"
TEX_DIR = EXPORT_DIR / "Textures"


def log(*a):
    print("[SAYA]", *a, flush=True)


def assert_lock():
    from pipeline.lock import assert_owner
    assert_owner("Katana", "claude")


def new_collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


# ====================================================================== fit
def stage_fit():
    import saya_fit
    saya_fit.run()


# ====================================================================== geo
def stage_geo():
    import katana_uvpack as UP
    import saya_parts as SPT
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    t0 = time.time()
    lows = {lv: SPT.build_lod(lv) for lv in (0, 1, 2)}
    tri = {lv: {p: m.tri_count() for p, m in d.items()} for lv, d in lows.items()}
    log("tris", {lv: sum(v.values()) for lv, v in tri.items()}, f"{time.time() - t0:.1f}s")
    log("tris per part", tri)
    isl = {}
    for lv, d in lows.items():
        for part, mb in d.items():
            for k, pts in mb.islands().items():
                isl[k] = np.vstack([isl[k], pts]) if k in isl else pts
    atlas = UP.pack(isl, S.ATLAS, 4, 0.0, SPT.island_scale)
    lm = UP.pack(isl, 1024, 3, 0.0, None)
    WORK.mkdir(parents=True, exist_ok=True)
    UP.save(atlas, WORK / "atlas_saya.json")
    UP.save(lm, WORK / "atlas_lightmap.json")
    log(f"atlas {atlas.density * 10:.1f} px/cm cover {UP.coverage_fraction(atlas):.2f} ({len(isl)} islands); "
        f"lightmap {lm.density * 10:.2f} px/cm")
    slot_mats = [bpy.data.materials.new(n) for n in S.SLOT_NAMES]
    for lv, d in lows.items():
        col = new_collection(f"LOD{lv}_parts")
        for part, mb in d.items():
            ob = mb.to_object(f"SAYA_L{lv}_{part}", col, materials=slot_mats, uv_transform=atlas.transform,
                              uv1_transform=lm.transform, smooth_angle=SPT.SMOOTH_ANGLE.get(part, 40.0), recalc=False)
            ob["saya_part"] = part
            ob["saya_level"] = lv
    # bake target: LOD0 parts joined, UVs in 0..1
    col = new_collection("BAKE_LOW")
    bm_ = bpy.data.materials.new("BAKE_saya")
    bm_.use_nodes = True
    objs = []
    for part, mb in lows[0].items():
        objs.append(mb.to_object(f"SAYA_BAKE_{part}", col, materials=[bm_, bm_], uv_transform=atlas.transform,
                                 smooth_angle=SPT.SMOOTH_ANGLE.get(part, 40.0), recalc=False))
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    objs[0].name = "SAYA_BAKE"
    pickle.dump({"lod0": lows[0], "lod1": lows[1], "lod2": lows[2]}, open(WORK / "parts.pkl", "wb"))
    json.dump({"tris": tri, "px_per_cm": atlas.density * 10, "lightmap_px_per_cm": lm.density * 10,
               "cover": UP.coverage_fraction(atlas),
               "island_px_per_cm": {k: atlas.px_per_mm(k) * 10 for k in atlas.place}},
              open(WORK / "geo_report.json", "w"), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK_BLEND))
    log("saved", WORK_BLEND, f"{time.time() - t0:.1f}s")


# ====================================================================== ao
def stage_ao(samples):
    from build_katana import setup_cycles
    bpy.ops.wm.open_mainfile(filepath=str(WORK_BLEND))
    dev = setup_cycles(samples)
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("bake_world")
    sc.world.light_settings.distance = 0.012
    for c in bpy.data.collections:
        if c.name.startswith("LOD"):
            for o in c.objects:
                o.hide_render = True
    BAKE_DIR.mkdir(parents=True, exist_ok=True)
    ob = bpy.data.objects["SAYA_BAKE"]
    size = S.ATLAS
    img = bpy.data.images.new("AO_saya", size, size, alpha=False, float_buffer=True, is_data=True)
    nt = ob.data.materials[0].node_tree
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = img
    nt.nodes.active = node
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    t = time.time()
    res = bpy.ops.object.bake(type="AO", margin=4, margin_type="EXTEND", use_clear=True, use_selected_to_active=False)
    if "FINISHED" not in res:
        raise RuntimeError(f"AO bake failed: {res}")
    px = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(px)
    np.save(BAKE_DIR / "saya_AO.npy", px.reshape(size, size, 4)[..., 0])
    log(f"AO {time.time() - t:.1f}s on {dev}")


# ====================================================================== maps
def stage_maps():
    import saya_tex as TX
    TX.make_maps(WORK, BAKE_DIR, TEX_DIR)


# ====================================================================== game / export
def stage_game():
    import saya_game as SG
    assert_lock()
    bpy.ops.wm.open_mainfile(filepath=str(WORK_BLEND))
    SG.make_game(WORK, TEX_DIR, GAME_BLEND)


def stage_export():
    import saya_game as SG
    assert_lock()
    bpy.ops.wm.open_mainfile(filepath=str(GAME_BLEND))
    SG.export(WORK, EXPORT_DIR)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--samples", type=int, default=256)
    a = ap.parse_args(argv)
    t = time.time()
    {"fit": stage_fit, "geo": stage_geo, "ao": lambda: stage_ao(a.samples), "maps": stage_maps, "game": stage_game,
     "export": stage_export}[a.stage]()
    log(f"stage {a.stage} finished in {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
