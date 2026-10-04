"""Basic katana build (headless Blender 5.2).

    blender -b --factory-startup --python Scripts/Katana/build_katana.py -- --stage <stage>

Stages (each its own process, in order):
    geo      LOD0/1/2 from the spec generators, pack the atlases, save the work blend (+ part data for the painter)
    ao       Cycles AO bake of the LOD0 game mesh into both atlases (float arrays)
    maps     paint BC / ORM / N from the parts' parametric attributes + the AO; LOD2 tsuka shell ray-cast from LOD0;
             write the shipped PNGs (BC sRGB, ORM linear, N DirectX)
    game     join each LOD into one mesh with the 3 slots, UCX hulls, sockets, LOD group -> Assets/Katana/Katana.blend
    export   Scripts/pipeline export_fbx + qa_check -> Exports/Katana/SM_Katana.fbx (+ .sockets.json)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
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

import katana_spec as K  # noqa: E402
import katana_parts as KP  # noqa: E402
import katana_uvpack as UP  # noqa: E402

WORK = ROOT / "WorkFiles" / "katana" / "build"
BAKE_DIR = WORK / "bake"
WORK_BLEND = WORK / "katana_work.blend"
GAME_BLEND = ROOT / "Assets" / "Katana" / "Katana.blend"
EXPORT_DIR = ROOT / "Exports" / "Katana"
TEX_DIR = EXPORT_DIR / "Textures"
NAME = K.NAME


def log(*a):
    print("[KAT]", *a, flush=True)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def new_collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def assert_lock():
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline.lock import assert_owner
    assert_owner("Katana", "claude")


# ====================================================================== geo
def stage_geo():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    t0 = time.time()
    lows = {lv: KP.build_lod(lv) for lv in (0, 1, 2)}
    tri = {lv: {p: m.tri_count() for p, m in d.items()} for lv, d in lows.items()}
    log("tris", {lv: sum(v.values()) for lv, v in tri.items()}, f"{time.time() - t0:.1f}s")
    log("tris per part LOD0", tri[0])
    steel_isl, grip_isl = {}, {}
    for lv, d in lows.items():
        for part, mb in d.items():
            tgt = grip_isl if part in KP.GRIP_PARTS else steel_isl
            for k, pts in mb.islands().items():
                tgt[k] = np.vstack([tgt[k], pts]) if k in tgt else pts
    steel = UP.pack(steel_isl, K.STEEL_MAP, 4, 0.0, KP.island_scale)
    grip = UP.pack(grip_isl, K.GRIP_MAP, 4, 1.0, KP.island_scale)
    allisl = dict(steel_isl)
    allisl.update(grip_isl)
    lm = UP.pack(allisl, 1024, 3, 0.0, None)
    WORK.mkdir(parents=True, exist_ok=True)
    UP.save(steel, WORK / "atlas_steel.json")
    UP.save(grip, WORK / "atlas_grip.json")
    UP.save(lm, WORK / "atlas_lightmap.json")
    log(f"steel {steel.density * 10:.1f} px/cm cover {UP.coverage_fraction(steel):.2f} ({len(steel_isl)} islands); "
        f"grip {grip.density * 10:.1f} px/cm cover {UP.coverage_fraction(grip):.2f} ({len(grip_isl)} islands); "
        f"lightmap {lm.density * 10:.2f} px/cm")

    def uvt(island, uv):
        return (grip if island in grip_isl else steel).transform(island, uv)

    def uv1(island, uv):
        return lm.transform(island, uv)

    def uvt_bake(island, uv):
        out = uvt(island, uv)
        if island in grip_isl:
            out = out.copy()
            out[:, 0] -= 1.0
        return out

    slot_mats = [bpy.data.materials.new(n) for n in K.SLOT_NAMES]
    for lv, d in lows.items():
        col = new_collection(f"LOD{lv}_parts")
        for part, mb in d.items():
            ob = mb.to_object(f"KAT_L{lv}_{part}", col, materials=slot_mats, uv_transform=uvt, uv1_transform=uv1,
                              smooth_angle=KP.SMOOTH_ANGLE.get(part, 50.0), recalc=True)
            ob["kat_part"] = part
            ob["kat_level"] = lv
    # bake targets: LOD0 parts, one object per atlas, UVs in 0..1
    col = new_collection("BAKE_LOW")
    for atlas in ("steel", "grip"):
        bm_ = bpy.data.materials.new(f"BAKE_{atlas}")
        bm_.use_nodes = True
        objs = []
        for part, mb in lows[0].items():
            if (part in KP.GRIP_PARTS) != (atlas == "grip"):
                continue
            ob = mb.to_object(f"KAT_BAKE_{atlas}_{part}", col, materials=[bm_, bm_, bm_], uv_transform=uvt_bake,
                              smooth_angle=KP.SMOOTH_ANGLE.get(part, 50.0), recalc=True)
            objs.append(ob)
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
        objs[0].name = f"KAT_BAKE_{atlas}"
        objs[0]["kat_atlas"] = atlas
    # LOD2 shell (painted by ray-cast from LOD0): its own bake object too, for the coverage mask
    pickle.dump({"lod0": lows[0], "lod1": lows[1], "lod2": lows[2]}, open(WORK / "parts.pkl", "wb"))
    json.dump({"tris": tri, "steel_px_per_cm": steel.density * 10, "grip_px_per_cm": grip.density * 10,
               "lightmap_px_per_cm": lm.density * 10, "steel_cover": UP.coverage_fraction(steel),
               "grip_cover": UP.coverage_fraction(grip)}, open(WORK / "geo_report.json", "w"), indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=str(WORK_BLEND))
    log("saved", WORK_BLEND, f"{time.time() - t0:.1f}s")


# ====================================================================== ao
def setup_cycles(samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as exc:  # noqa: BLE001
        log("GPU unavailable, CPU:", exc)
        sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    return sc.cycles.device


def stage_ao(samples=64):
    bpy.ops.wm.open_mainfile(filepath=str(WORK_BLEND))
    dev = setup_cycles(samples)
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("bake_world")
    sc.world.light_settings.distance = 0.010
    for c in bpy.data.collections:
        if c.name.startswith("LOD"):
            for o in c.objects:
                o.hide_render = True
    BAKE_DIR.mkdir(parents=True, exist_ok=True)
    for atlas, size in (("steel", K.STEEL_MAP), ("grip", K.GRIP_MAP)):
        ob = bpy.data.objects[f"KAT_BAKE_{atlas}"]
        img = bpy.data.images.new("AO_" + atlas, size, size, alpha=False, float_buffer=True, is_data=True)
        mat = ob.data.materials[0]
        nt = mat.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        nt.nodes.active = node
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        t = time.time()
        res = bpy.ops.object.bake(type="AO", margin=4, margin_type="EXTEND", use_clear=True,
                                  use_selected_to_active=False)
        if "FINISHED" not in res:
            raise RuntimeError(f"AO bake failed: {res}")
        px = np.empty(size * size * 4, np.float32)
        img.pixels.foreach_get(px)
        np.save(BAKE_DIR / f"{atlas}_AO.npy", px.reshape(size, size, 4)[..., 0])
        log(f"AO {atlas} {time.time() - t:.1f}s on {dev}")
        nt.nodes.remove(node)


# ====================================================================== maps
def stage_maps():
    import katana_tex as TX
    TX.make_maps(WORK, BAKE_DIR, TEX_DIR)


# ====================================================================== game
def stage_game():
    import bmesh
    import katana_game as KG
    assert_lock()
    bpy.ops.wm.open_mainfile(filepath=str(WORK_BLEND))
    KG.make_game(WORK, TEX_DIR, GAME_BLEND)


# ====================================================================== export
def stage_export():
    import katana_game as KG
    assert_lock()
    bpy.ops.wm.open_mainfile(filepath=str(GAME_BLEND))
    KG.export(WORK, EXPORT_DIR)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--samples", type=int, default=256)
    a = ap.parse_args(argv)
    t = time.time()
    {"geo": stage_geo, "ao": lambda: stage_ao(a.samples), "maps": stage_maps, "game": stage_game,
     "export": stage_export}[a.stage]()
    log(f"stage {a.stage} finished in {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
