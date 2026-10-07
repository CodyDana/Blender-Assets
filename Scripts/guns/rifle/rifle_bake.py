"""AR-01 stage 3b: Cycles bakes of the LOD0 parts into the three sets (headless Blender; GPU when present):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_bake.py [-- --ao-samples 256]

Per set (sizes from the UV stage, scratch/uv/sets.json): pos, nrm, ids, edge, ao (gunlib.bake); the Furniture set
also gets the checkering: a selected-to-active tangent-space NORMAL bake of the modelled pyramid field
(parts/grip.build_checker_field, the user's 2026-10-04 choice) onto pistol_grip, plus its hit mask. Output:
WorkFiles/guns/rifle/scratch/bake/<Set>_<pass>.npy (+ bake_meta.json). The .blend is not saved (bake materials are
temporary).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH, GRIP  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import rifle_surface as RS  # noqa: E402
from gunlib import bake as BK  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
AO_SAMPLES = int(argv[argv.index("--ao-samples") + 1]) if "--ao-samples" in argv else 256
EDGE_SAMPLES = int(argv[argv.index("--edge-samples") + 1]) if "--edge-samples" in argv else 64
ONLY = argv[argv.index("--only") + 1].split(",") if "--only" in argv else None
PASSES = argv[argv.index("--passes") + 1].split(",") if "--passes" in argv else None
OUT = SCRATCH / "bake"
OUT.mkdir(parents=True, exist_ok=True)
UVD = SCRATCH / "uv"
AO_DISTANCE_M = 0.025


def log(*a):
    print("[AR01-bake]", *a, flush=True)


def part_rec(ob):
    return json.loads(ob.get("gun_part", "{}"))


def main():
    t0 = time.time()
    dev = BK.setup_cycles(1)
    log("device", dev)
    sc = bpy.context.scene
    if sc.world is None:
        sc.world = bpy.data.worlds.new("bake_world")
    sc.world.light_settings.distance = AO_DISTANCE_M
    for c in bpy.data.collections:
        if c.name.startswith("AR01_LOD") or c.name.startswith("SM_AR01"):
            c.hide_render = True
            for o in c.objects:
                o.hide_render = True
    parts = sorted((o for o in bpy.data.collections["AR01_Parts"].objects if o.type == "MESH"), key=lambda o: o.name)
    pidx = {o.name: i for i, o in enumerate(parts)}
    isl = np.load(UVD / "islands.npz")
    sets = json.loads((UVD / "sets.json").read_text())
    for o in parts:
        BK.set_face_attr(o, "pid", np.full(len(o.data.polygons), pidx[o.name] + 1.0))
        BK.set_face_attr(o, "cls", isl[f"{o.name}__cls"].astype(np.float32))
        BK.set_face_attr(o, "isl", isl[f"{o.name}__isl"].astype(np.float32) + 1.0)
        o.hide_render = False
        # AO rays leave smooth-shaded long triangles from the true surface, not the interpolated one (no dark
        # terminator streaks along the long thin faces of lofts)
        for att, val in (("shadow_terminator_geometry_offset", 1.0), ("shadow_terminator_normal_offset", 0.0)):
            if hasattr(o, att):
                setattr(o, att, val)
    meta = {"parts": {o.name: pidx[o.name] + 1 for o in parts}, "ao_samples": AO_SAMPLES, "ao_distance_m": AO_DISTANCE_M,
            "edge_samples": EDGE_SAMPLES, "device": dev, "sets": {}, "encoding": {
                "pos": "metres frame B + 1.0", "nrm": "n * 0.5 + 0.5 (world)", "ids": "R part index + 1 (0 = empty), "
                "G class code (rifle_surface.CLASS_CODE), B island id + 1", "edge": "R 1 - Nbevel(0.6 mm).N, "
                "G 1 - Nbevel(2.0 mm).N, B pointiness", "ao": "Cycles AO", "rows": "bottom-up (Blender pixel order)"}}
    for st, info in sets.items():
        if ONLY and st not in ONLY:
            continue
        S = int(info["size"])
        objs = [o for o in parts if RS.SLOT_SET[part_rec(o)["slot"]] == st]
        img = BK.new_image(f"BAKE_{st}", S)
        mat = BK.bake_material(f"BAKE_{st}", img)
        saved = {o.name: [s.material for s in o.material_slots] for o in objs}
        for o in objs:
            o.data.materials.clear()
            o.data.materials.append(mat)
        times = {}
        # the triangles for the geometric edge masks (gunlib.edgemask, realism-fix round 2026-10-07): the bevel-node
        # edge bake follows the interpolated shading normals, so long sliver triangles of the CDT flats came out as
        # whole lit / bare triangles; the painter now measures convex edges on the true geometry
        if not PASSES or "tris" in PASSES:
            BK.dump_tris(objs, {o.name: pidx[o.name] + 1 for o in objs}, OUT / f"{st}_tris.npz",
                         [float(v) for v in GRIP])
            log(st, "tris dumped")
        for name, kind, src, spp in (("pos", "EMIT", "pos", 1), ("nrm", "EMIT", "nrm", 1), ("ids", "EMIT", "ids", 1),
                                     ("edge", "EMIT", "edge", EDGE_SAMPLES), ("ao", "AO", None, AO_SAMPLES)):
            if PASSES and name not in PASSES:
                continue
            # ids: no margin (the EXTEND margin averages neighbours, which would invent part / class / island codes in
            # the gutters); the painter fills the gutters itself from the exact interior
            times[name] = round(BK.bake_pass(objs, [mat], img, kind, src, samples=spp,
                                             margin=0 if name == "ids" else 16), 1)
            px = BK.read_image(img)
            if name == "pos":
                np.save(OUT / f"{st}_pos.npy", px[..., :3] - 1.0)
            elif name == "ids":
                np.save(OUT / f"{st}_ids.npy", np.rint(px[..., :3]).astype(np.int16))
            elif name == "ao":
                np.save(OUT / f"{st}_ao.npy", px[..., 0].astype(np.float16))
            else:
                np.save(OUT / f"{st}_{name}.npy", px[..., :3].astype(np.float16))
            log(st, name, "%.1fs" % times[name])
        if st == "Furniture" and (not PASSES or "checker" in PASSES):
            times.update(bake_checker(S))
        for o in objs:
            o.data.materials.clear()
            for m in saved[o.name]:
                o.data.materials.append(m)
        bpy.data.images.remove(img)
        meta["sets"][st] = {"size": S, "objects": [o.name for o in objs], "seconds": times}
    mp = OUT / "bake_meta.json"
    if PASSES and mp.exists():
        old = json.loads(mp.read_text())
        for st_, v in meta["sets"].items():
            old["sets"].setdefault(st_, v)["seconds"].update(v["seconds"])
        meta = old
    mp.write_text(json.dumps(meta, indent=1))
    log("BAKE_DONE %.1fs" % (time.time() - t0))


def bake_checker(S):
    """Selected-to-active: the modelled diamond field (high) onto the LOD0 grip (low), tangent space (OpenGL, Blender's
    own), plus the hit mask (emission white from the high)."""
    import parts as PM
    GR = PM.load("grip")
    low = bpy.data.objects["pistol_grip"]
    col = bpy.data.collections.get("AR01_BakeSource") or bpy.data.collections.new("AR01_BakeSource")
    if col.name not in [c.name for c in bpy.context.scene.collection.children]:
        bpy.context.scene.collection.children.link(col)
    old = bpy.data.objects.get("pistol_grip_checker")
    if old is not None:
        bpy.data.objects.remove(old, do_unlink=True)
    t = time.time()
    hi = GR.build_checker_field(col, GRIP)
    log("checker field built", len(hi.data.polygons), "faces %.1fs" % (time.time() - t))
    hi.hide_render = False
    img = BK.new_image("BAKE_Checker", S)
    mlow = BK.bake_material("BAKE_CheckerLow", img)
    mhi = BK.bake_material("BAKE_CheckerHigh", img)
    keep = [s.material for s in low.material_slots]
    low.data.materials.clear()
    low.data.materials.append(mlow)
    hi.data.materials.clear()
    hi.data.materials.append(mhi)
    times = {}
    kw = dict(use_selected_to_active=True, cage_extrusion=0.0015, max_ray_distance=0.004, active=low)
    times["checker_normal"] = round(BK.bake_pass([hi, low], [mlow], img, "NORMAL", None, samples=16,
                                                 normal_space="TANGENT", **kw), 1)
    np.save(OUT / "Furniture_ckn.npy", BK.read_image(img)[..., :3].astype(np.float16))
    BK.route(mhi, "white")
    times["checker_mask"] = round(BK.bake_pass([hi, low], [mlow], img, "EMIT", None, samples=16, **kw), 1)
    np.save(OUT / "Furniture_ckm.npy", BK.read_image(img)[..., 0].astype(np.float16))
    low.data.materials.clear()
    for m in keep:
        low.data.materials.append(m)
    hi.hide_render = True
    bpy.data.objects.remove(hi, do_unlink=True)
    log("checker", times)
    return times


main()
