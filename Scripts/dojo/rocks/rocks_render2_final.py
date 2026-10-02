"""Pilot 2 final renders (called from rocks_render2.py): sheet / close / river. Cycles, denoised, headless; the
shipped SM_DKR_* objects with their MI_DKR_* materials from Assets/Dojo/DojoRocks.blend.

sheet  per rock: <r>_main (figure, perspective 85 mm, 8 deg up), <r>_mainonly, <r>_top (50 deg oblique), <r>_side,
       <r>_q34 (textured 3/4), <r>_clay_q34 (the shipped mesh in clay, same camera)
close  five close-ups framed like the sheet's panels; the spots are picked by reading the baked mask map at ray hits
river  the sunset riverbank test (stand-in bed, water and cobbles are NOT shipped; the dojo's 9 deg western sun)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import bpy
from mathutils import Vector

import rocks_render as R
import rocks_render_final as RF
import rocks_render2 as R2
from rocks_plans2 import PLANS

OUT = R2.OUT


def load(names):
    objs = R.append_from_blend([PLANS[n]["prefix"] for n in names])
    return {n: objs[PLANS[n]["prefix"]] for n in names}


def studio2(key=260.0):
    """Pilot 1's studio, with the fill made small and brighter (1.2 m, 0.45 x key): the sheet's wet river rocks
    show crisp specular sparkle on their lower faces, which a 5 m soft fill at 0.15 x key cannot produce."""
    floor = R.studio(key=key)
    f = bpy.data.objects.get("Fill")
    if f is not None:
        f.data.size = 1.2
        f.data.energy = key * 0.45
        f.location = (5.0, -5.5, 1.6)
        d = Vector((0, 0, 0.6)) - f.location
        f.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return floor


def mode_sheet(rocks, src):
    out = OUT / "sheet"
    meta = {}
    for r in rocks:
        sc = R.reset()
        studio2()
        ob = load([r])[r]
        RF.holdout_below()
        lo, hi = R.bbox_of(ob)
        L, D, H = hi[0] - lo[0], hi[1] - lo[1], hi[2]
        sc.cycles.samples = 192
        fig = R.figure(lo[0] - 0.75, 0.0)
        res = (1600, 1000)
        lens = 85.0
        w = hi[0] - (lo[0] - 1.05)
        cx = (hi[0] + lo[0] - 1.05) / 2
        RF.persp_cam((cx, 0.0, max(H, 1.8) * 0.47), RF.fit_dist(w, max(H, 1.85), lens, res, 1.12), 0.0, 8.0, lens)
        R.render(out / f"{r}_main.png", res=res)
        fig.hide_render = True
        RF.persp_cam(((lo[0] + hi[0]) / 2, 0.0, H * 0.45), RF.fit_dist(L, H, lens, (1400, 1000), 1.12), 0.0, 8.0,
                     lens)
        R.render(out / f"{r}_mainonly.png", res=(1400, 1000))
        RF.persp_cam(((lo[0] + hi[0]) / 2, 0.0, H * 0.3), RF.fit_dist(L, D + H * 0.6, lens, (1200, 900), 1.15),
                     0.0, 50.0, lens)
        R.render(out / f"{r}_top.png", res=(1200, 900))
        RF.persp_cam((0.0, (lo[1] + hi[1]) / 2, H * 0.45), RF.fit_dist(D, H, lens, (900, 1000), 1.15), 90.0, 8.0,
                     lens)
        R.render(out / f"{r}_side.png", res=(900, 1000))
        R2.q34_cam(lo, hi)
        R.render(out / f"{r}_q34.png", res=(1400, 1000))
        clay = R.clay_material()
        for i in range(len(ob.material_slots)):
            ob.material_slots[i].material = clay
        R.render(out / f"{r}_clay_q34.png", res=(1400, 1000))
        meta[r] = {"bbox": [list(map(float, lo)), list(map(float, hi))], "lens": lens, "elev_main": 8.0,
                   "q34": R2.Q34}
    p = out / "sheet_meta.json"
    old = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    old.update(meta)
    p.write_text(json.dumps(old, indent=1), encoding="utf-8")


def mode_close(rocks, src):
    out = OUT / "close"
    rng = np.random.default_rng(31)
    sc = R.reset()
    objs = load(list(PLANS))
    R.world_colour((0.62, 0.64, 0.68), 0.9)
    R.sun("Key", 48.0, 300.0, 3.2, (1.0, 0.97, 0.92), angle_deg=6.0)
    sc.cycles.samples = 256
    res = (1000, 1400)
    meta = {}
    shots = [
        # name, rock, score(mask (moss, lichen, wet, 1), normal, point), width m, tilt deg, up bias
        # pilot 2 fix 1: 7.5 cm field (the grain tile is now 0.45 m; the sheet panel shows ~12-16 crystals across)
        ("grain", "CliffChunk", lambda m, n, p: -4 * m[0] - 4 * m[1] - 2 * m[2] + (1 - abs(n.z)) * 1.5
         - abs(p.z - 1.4) * 0.2, 0.075, 0.0, 0.0),
        # pilot 2 fix 1: a fresh fracture arris (M.A = fresh), away from the moss and the grass on the ledges
        ("fracture", "CliffChunk", lambda m, n, p: (0.25 < n.z < 0.75) * 1.0 + m[3] * 1.5 - m[0] * 2 - m[2] - m[1]
         - abs(p.z - 1.5) * 0.25, 0.42, 30.0, 0.35),
        ("moss", "RiverLong", lambda m, n, p: m[0] * 2 + n.z, 0.40, 0.0, 0.6),
        # pilot 2 fix 1: lichen is sparse on the cliff now (delta 6); the close-up is taken where the boulder's
        # lichen zone is strongest
        ("lichen", "RiverLong", lambda m, n, p: m[1] * 3 - m[0] * 3 - m[2] * 2 + n.z * 0.5, 0.22, 0.0, 0.1),
    ]
    for name, r, score, width, tilt, ub in shots:
        RF.place_only(objs, r)
        spot = RF.find_spot(objs[r], score, rng, n=4000)
        if spot is None:
            log_ = f"no spot for {name}"
            print(log_)
            continue
        p, n = spot
        RF.close_cam(p, n, width, tilt, ub, res)
        R.render(out / f"close_{name}.png", res=res)
        meta[name] = {"rock": r, "point": list(p), "normal": list(n), "width_m": width}
    # the wet zone at the water: RiverRound with a water plane low on its wet band
    r = "RiverRound"
    RF.place_only(objs, r)
    ob = objs[r]
    lo, hi = R.bbox_of(ob)
    zw = 0.12
    water = RF.water_plane(zw, 6.0, colour=(0.30, 0.42, 0.40))
    for nd in water.data.materials[0].node_tree.nodes:
        if nd.type == "VOLUME_ABSORPTION":
            nd.inputs["Density"].default_value = 0.35           # clear shallow water (was opaque teal)
    deps = bpy.context.evaluated_depsgraph_get()
    o = Vector((0.15, -6.0, zw + 0.30))
    hit, loc, nrm, fi, hob, _ = sc.ray_cast(deps, o, Vector((0, 1, 0)))
    if hit:
        # camera a little below the target, near the water level: the water reads as the sheet's lower band
        RF.close_cam(loc, nrm, 0.55, 15.0, -0.10, res)
        R.render(out / "close_wetline.png", res=res)
        meta["wetline"] = {"rock": r, "point": list(loc), "water_z": zw, "width_m": 0.55}
    bpy.data.objects.remove(water)
    (out / "close_meta.json").write_text(json.dumps(meta, indent=1, default=float), encoding="utf-8")


def small_rock_bed(n, region, zfun, rng, sources, size=(0.04, 0.28), sink=0.35):
    """Pilot 2 fix 1 (delta 9): the stand-in ellipsoid cobbles read as clay; the bed is now made of OUR rock
    meshes (linked copies of the shipped river boulders, scaled down to cobbles and pebbles, random yaw / roll),
    sizes log-uniform, packed denser near the boulders, each sunk ``sink`` of its height."""
    obs = []
    meshes = [s.data for s in sources]
    for i in range(n):
        x = rng.uniform(*region[0])
        y = rng.uniform(*region[1])
        s = float(np.exp(rng.uniform(np.log(size[0]), np.log(size[1]))))
        me = meshes[int(rng.integers(len(meshes)))]
        ob = bpy.data.objects.new(f"Pebble{i}", me)
        bpy.context.scene.collection.objects.link(ob)
        k = s / max(me.dimensions[0] if hasattr(me, "dimensions") else 2.0, 1e-3)
        ob.scale = (s / 2.0, s / 2.0 * rng.uniform(0.8, 1.2), s / 2.0 * rng.uniform(0.6, 1.0))
        ob.rotation_euler = (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), rng.uniform(0, 6.283))
        ob.location = (x, y, zfun(x, y) - sink * s * 0.6)
        obs.append(ob)
    return obs


def mode_river(rocks, src):
    RF.OUT = OUT
    import rocks_plans as P1
    saved = P1.PLANS
    saved_cob = RF.stand_in_cobbles
    rng = np.random.default_rng(91)
    state = {}

    def cobbles(n, region, zfun, rng_, mat):
        srcs = [o for o in bpy.data.objects if o.name in (PLANS["RiverRound"]["prefix"], PLANS["RiverLong"]["prefix"])]
        out = small_rock_bed(int(n * 4), region, zfun, rng, srcs, size=(0.04, 0.32))
        # gravel: many tiny ones, plus a denser skirt wedged against each boulder (the sheet's riverbank)
        out += small_rock_bed(int(n * 8), region, zfun, rng, srcs, size=(0.015, 0.05), sink=0.25)
        for nm in (PLANS["RiverRound"]["prefix"], PLANS["RiverLong"]["prefix"]):
            o = bpy.data.objects.get(nm)
            if o is None:
                continue
            c = o.location
            hx = o.dimensions[0] * 0.55
            hy = o.dimensions[1] * 0.6
            out += small_rock_bed(60, ((c.x - hx, c.x + hx), (c.y - hy, c.y + hy)), zfun, rng, srcs,
                                  size=(0.04, 0.22))
        # rocks sit deeper (study 3.10: 15-35 % of their height for loose river boulders)
        for nm, dz in ((PLANS["RiverRound"]["prefix"], -0.08), (PLANS["RiverLong"]["prefix"], -0.08)):
            o = bpy.data.objects.get(nm)
            if o is not None and not state.get(nm):
                o.location.z += dz
                state[nm] = True
        return out
    try:
        RF.PLANS = PLANS
        RF.stand_in_cobbles = cobbles
        RF.mode_river(rocks, src)
    finally:
        RF.PLANS = saved
        RF.stand_in_cobbles = saved_cob
