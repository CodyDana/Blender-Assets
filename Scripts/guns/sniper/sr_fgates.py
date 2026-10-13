"""SR01 form gates measured in Blender on the built bytes (Assets/Guns/SR01.blend): G5 (rest intersections + butt gaps),
B3 (every motion swept: bolt cycle, trigger, safety, release, riser, bipod fold x ext x cant), F1-F9 (bipod, bolt,
release, riser, trigger), B6a (qa_check topology on the joined twin + deny list), B7 (closed manifold), form magfit
(seated clearances, straight insert path released / catch cammed, removal), H1 early (grip girth, trigger reach).

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_fgates.py --
            [--only g5,b3,f,magfit,b6a,h1] [--out scratch/w1/fgates.json] [--fast]
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import GRIP, SCRATCH, D, dims, CODE  # noqa: E402
import sr_motion as MO  # noqa: E402
from gunlib import fit, bl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set((argv[argv.index("--only") + 1] if "--only" in argv else "g5,b3,f,magfit,b6a,h1").split(","))
OUT = Path(argv[argv.index("--out") + 1]) if "--out" in argv else SCRATCH / "fgates.json"
FAST = "--fast" in argv

OBJS = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("_")]
GEO = {}
for o in OBJS:
    V, T = bl.tris_np(o)
    GEO[o.name] = (V + GRIP, T)                         # frame M, mm
BONE = {o.name: json.loads(o.get("gun_part", "{}")).get("bone", "body") for o in OBJS}
ROWS = {"sliding": [0.15, 0.40], "hinge": [0.10, 0.30], "butt": [0.01, 0.05]}


def by_bone(*bones):
    return {n: GEO[n] for n in GEO if BONE[n] in bones}


def fixed_except(*bones):
    return {n: GEO[n] for n in GEO if BONE[n] not in bones}


def posed(geoms, M):
    return {n: (fit.apply(M, V), T) for n, (V, T) in geoms.items()}


def sweep(name, moving, fixed, motion, values, row, proof=None, every=1):
    t0 = time.time()
    recs, s = fit.sweep(moving, fixed, motion, values, clearance_every=every, cap_mm=3.0, sample_mm=0.5, proof=proof)
    s["row"] = row
    s["pass"] = s["intersecting_steps"] == 0 and s["min_clearance_mm"] >= ROWS[row][0] - 0.005
    if proof:
        s["proof_fails"] = int(sum(r.get("proof_fails", 0) for r in recs))
        s["pass"] = s["pass"] and s["proof_fails"] == 0
    s["hits_at"] = [r["value"] for r in recs if r["intersections"]][:12]
    print(f"[B3] {name}: steps {s['steps']} hits {s['intersecting_steps']} {s['parts_hit']} min {s['min_clearance_mm']}"
          f" with {s['min_with']} at {s['min_at']} ({time.time() - t0:.0f}s)")
    return s


R = {"stage": "W1a form (Blender gates on the built bytes)", "blend": "Assets/Guns/SR01.blend"}

# ------------------------------------------------------------------------------------------------ B7 / G5
if "g5" in ONLY:
    from gunlib import bl as _bl
    R["B7"] = {o.name: _bl.manifold_report(o) for o in OBJS}
    R["B7_closed"] = sum(1 for r in R["B7"].values() if r["boundary_edges"] == 0 and r["multi_face_edges"] == 0)
    R["B8_triangles"] = int(sum(len(T) for _, T in GEO.values()))
    t0 = time.time()
    R["G5_rest_intersections"] = fit.pair_intersections(GEO)
    print("[G5]", R["G5_rest_intersections"], f"{time.time() - t0:.0f}s")
    pairs = [("butt", "chassis"), ("grip", "chassis"), ("grip", "butt"), ("butt_pad", "pad_plate"), ("pad_plate", "butt"),
             ("receiver", "chassis"), ("rail", "receiver"), ("barrel", "receiver"), ("muzzle_device", "barrel"),
             ("bipod_clamp", "chassis"), ("fasteners", "pad_plate"), ("fasteners", "chassis"), ("butt_knobs", "butt"),
             ("riser_lever", "butt"), ("magazine_floorplate", "magazine"), ("pins", "chassis")]
    R["G5_butt_gaps"] = fit.min_gaps(GEO, pairs, 0.5, 0.5)
    print("[G5] gaps", R["G5_butt_gaps"])

# ------------------------------------------------------------------------------------------------ B3 sweeps
if "b3" in ONLY:
    B3 = {}
    bolt_mv = by_bone("bolt")
    rot_step = 0.5 if not FAST else 1.0
    B3["bolt_rotate"] = sweep("bolt_rotate", bolt_mv, fixed_except("bolt"), lambda v: MO.bolt(v, 0.0),
                              np.arange(0.0, MO.BOLT_ROT - 1e-6, -rot_step), "sliding",
                              proof={"pivot": (0, 0, 0), "axis": (1, 0, 0), "step_deg": rot_step, "skip": lambda v: False})
    B3["bolt_slide"] = sweep("bolt_slide", bolt_mv, fixed_except("bolt"), lambda v: MO.bolt(MO.BOLT_ROT, v),
                             np.arange(0.0, MO.BOLT_TRAVEL + 1e-6, 0.5 if not FAST else 1.0), "sliding", every=2)
    B3["trigger"] = sweep("trigger", by_bone("trigger"), fixed_except("trigger"), MO.trigger,
                          np.arange(0.0, 6.0001, 0.1), "hinge")
    B3["safety"] = sweep("safety", by_bone("selector"), fixed_except("selector"), MO.selector,
                         np.arange(0.0, -12.0001, -0.1), "hinge")
    B3["mag_release"] = sweep("mag_release", by_bone("mag_release"), fixed_except("mag_release", "magazine"),
                              MO.mag_release, np.arange(0.0, -4.5001, -0.05), "hinge")
    B3["riser"] = sweep("riser", by_bone("cheek_riser"), fixed_except("cheek_riser"), MO.riser,
                        np.arange(-12.9, 12.0001, 0.3 if not FAST else 1.0), "sliding", every=2)
    leg_bones = ("bipod_leg_l", "bipod_leg_r", "bipod_leg_l_ext", "bipod_leg_r_ext")
    fold_step = 1.0 if not FAST else 2.0
    for side in ("l", "r"):
        mv = by_bone(f"bipod_leg_{side}", f"bipod_leg_{side}_ext")
        fx = fixed_except(*leg_bones)
        other = "r" if side == "l" else "l"
        fx.update(by_bone(f"bipod_leg_{other}", f"bipod_leg_{other}_ext"))
        for ext in (0.0, 76.0):
            ext_geo = {n: (fit.apply(MO.T((ext, 0, 0)), V), T) if BONE[n].endswith("_ext") else (V, T)
                       for n, (V, T) in mv.items()}
            B3[f"fold_{side}_ext{int(ext)}"] = sweep(
                f"fold_{side}_ext{int(ext)}", ext_geo, fx, lambda v, s=side: MO.leg(s, v), np.arange(0.0, 90.0001, fold_step),
                "hinge", proof={"pivot": (MO.HUB[0], MO.LEG_Y if side == "l" else -MO.LEG_Y, MO.HUB[2]),
                                "axis": tuple(MO.pin_axis(side)), "step_deg": fold_step,
                                "skip": lambda v: False}, every=8)
        for pose, deg in (("folded", 0.0), ("deployed", 90.0)):
            ext_mv = by_bone(f"bipod_leg_{side}_ext")
            fx2 = {n: g for n, g in GEO.items() if n not in ext_mv}
            fx2 = {n: (fit.apply(MO.leg(side, deg), V), T) if BONE[n] == f"bipod_leg_{side}" else (V, T)
                   for n, (V, T) in fx2.items()}
            fx2 = {n: (fit.apply(MO.leg(other, deg), V), T) if BONE[n] in (f"bipod_leg_{other}", f"bipod_leg_{other}_ext")
                   else (V, T) for n, (V, T) in fx2.items()}
            B3[f"ext_{side}_{pose}"] = sweep(f"ext_{side}_{pose}", ext_mv, fx2,
                                             lambda v, s=side, d=deg: MO.leg_ext(s, d, v),
                                             np.arange(0.0, 76.0001, 0.5 if not FAST else 2.0), "sliding", every=4)
    cant_mv_bones = ("bipod",) + leg_bones
    for pose, deg, ext in (("folded", 0.0, 0.0), ("deployed", 90.0, 76.0)):
        mv = {}
        for n, (V, T) in by_bone(*cant_mv_bones).items():
            b = BONE[n]
            M = np.eye(4)
            if b.startswith("bipod_leg_"):
                s = b[10]
                M = MO.leg_ext(s, deg, ext) if b.endswith("_ext") else MO.leg(s, deg)
            mv[n] = (fit.apply(M, V), T)
        cstep = 0.5 if not FAST else 1.0
        B3[f"cant_{pose}"] = sweep(f"cant_{pose}", mv, fixed_except(*cant_mv_bones), MO.cant,
                                   np.arange(-15.0, 15.0001, cstep), "hinge",
                                   proof={"pivot": (0, 0, MO.CANT_Z), "axis": (1, 0, 0), "step_deg": cstep,
                                          "skip": lambda v: False}, every=10)
    R["B3"] = B3

# ------------------------------------------------------------------------------------------------ F gates
def zmin(names, M=np.eye(4)):
    return float(min(fit.apply(M, GEO[n][0])[:, 2].min() for n in names))


if "f" in ONLY:
    F = {}
    gaps = fit.min_gaps(GEO, [("bipod_leg_l", "bipod_clamp"), ("bipod_leg_r", "bipod_clamp"), ("bipod_foot_l", "chassis"),
                              ("bipod_foot_r", "chassis"), ("bipod_foot_l", "bipod_foot_r"), ("bipod_leg_l", "bipod_knob"),
                              ("bipod_leg_r", "bipod_knob"), ("bipod_leg_l", "bipod_swivel"), ("bipod_foot_l", "barrel")],
                        0.25, 8.0)
    F["F1_folded_gaps"] = gaps
    feet = {}
    for ext in (0.0, 19.0, 38.0, 57.0, 76.0):
        zl = zmin(["bipod_foot_l"], MO.leg_ext("l", 90.0, ext))
        zr = zmin(["bipod_foot_r"], MO.leg_ext("r", 90.0, ext))
        feet[f"ext_{int(ext)}"] = {"left_Z": round(zl, 3), "right_Z": round(zr, 3),
                                   "spec": D["bipod"]["ground_Z_deployed"][f"ext_{int(ext)}"]}
    ax = {s: MO.leg(s, 90.0)[:3, :3] @ np.array([1.0, 0, 0]) for s in ("l", "r")}
    yfoot = {s: float(fit.apply(MO.leg_ext(s, 90.0, 0.0), GEO[f"bipod_foot_{s}"][0])[:, 1].mean()) for s in ("l", "r")}
    F["F3_deployed"] = {"feet": feet, "splay_spec_deg": MO.SPLAY,
                        "leg_splay_deg": {s: round(math.degrees(math.acos(abs(a[2]))), 4) for s, a in ax.items()},
                        "leg_outward": {s: bool(np.sign(a[1]) == (1 if s == "l" else -1)) for s, a in ax.items()},
                        "leg_axis_deg_from_vertical": round(math.degrees(math.acos(abs(ax["l"][2]))), 4),
                        "foot_centre_track_ext0_mm": round(yfoot["l"] - yfoot["r"], 2),
                        "coplanar_mm": round(max(abs(v["left_Z"] - v["right_Z"]) for v in feet.values()), 4)}
    # F6 knob vs the mounted scope (blockout stand-in until W1b), over rotate + slide
    sc = np.load(SCRATCH / "blockout_tris.npz", allow_pickle=True)
    nm = [str(n) for n in sc["names"]]
    sel = np.isin(sc["lab"], [i for i, n in enumerate(nm) if n.startswith("scope")])
    tS = fit.tree(sc["V"], sc["T"][sel])
    kn = bl.surface_samples(*GEO["bolt_handle"], 1.0)
    best = 1e9
    for u in np.linspace(0, 1, 121):
        d, _ = fit.nearest_dist(fit.apply(MO.bolt_cycle_param(u), kn), tS, 80.0)
        best = min(best, d)
    F["F6_handle_to_scope_mm"] = round(best, 2)
    # F7 release: hook engagement (seated), hook travel at -4.5, pad to the magazine pressed
    hook = GEO["mag_release"][0]
    hk = hook[(hook[:, 2] > -52.5) & (hook[:, 2] < -47.0)]
    F7 = {"hook_tip_X_rest": round(float(hk[:, 0].max()), 3), "mag_rear_X": 414.1}
    F7["engagement_mm"] = round(F7["hook_tip_X_rest"] - 414.1, 3)
    hp = fit.apply(MO.mag_release(-4.5), hook)
    hk2 = hp[(hook[:, 2] > -52.5) & (hook[:, 2] < -47.0)]
    F7["hook_travel_mm"] = round(F7["hook_tip_X_rest"] - float(hk2[:, 0].max()), 3)
    F7["hook_tip_X_pressed"] = round(float(hk2[:, 0].max()), 3)
    F7["pad_gap_pressed_mm"] = fit.min_gaps({"rel": (hp, GEO["mag_release"][1]), "mag": GEO["magazine"]},
                                            [("rel", "mag")], 0.25, 6.0)[0]["min_gap_mm"]
    F["F7_release"] = F7
    # F8 riser low stop, F9 trigger at full pull
    rl = {n: (fit.apply(MO.riser(-12.9), V), T) for n, (V, T) in by_bone("cheek_riser").items()}
    rl.update({"butt": GEO["butt"]})
    F["F8_riser_low_stop"] = fit.min_gaps(rl, [("cheek_riser", "butt")], 0.25, 3.0)
    tg = {"trigger": (fit.apply(MO.trigger(6.0), GEO["trigger"][0]), GEO["trigger"][1]), "chassis": GEO["chassis"]}
    F["F9_trigger_full_pull"] = fit.min_gaps(tg, [("trigger", "chassis")], 0.25, 6.0)
    R["F"] = F
    print("[F]", json.dumps(F)[:1500])

# ------------------------------------------------------------------------------------------------ magfit
if "magfit" in ONLY:
    MG = {}
    mag = by_bone("magazine")
    gun = fixed_except("magazine", "mag_release")
    MG["M1_seated_intersections"] = fit.pair_intersections({**mag, **{"chassis": GEO["chassis"],
                                                                     "receiver": GEO["receiver"],
                                                                     "mag_release": GEO["mag_release"]}})
    MG["M1_seated_intersections"] = [p for p in MG["M1_seated_intersections"]
                                     if ("magazine" in p["a"]) != ("magazine" in p["b"])]
    V, T = GEO["magazine"]
    MG["M3_lateral_foreaft_top"] = fit.min_gaps({"magazine": GEO["magazine"], "chassis": GEO["chassis"],
                                                 "receiver": GEO["receiver"]},
                                                [("magazine", "chassis"), ("magazine", "receiver")], 0.25, 1.0)
    rel_p = {"mag_release": (fit.apply(MO.mag_release(-4.5), GEO["mag_release"][0]), GEO["mag_release"][1])}
    drop = np.arange(0.0, 67.8 + 1e-6, 0.5)
    MG["M4b_insert_released"] = sweep("insert_released", mag, {**gun, **rel_p}, lambda v: MO.magazine(v), drop[::-1],
                                      "sliding")
    MG["M5b_removal_catch_rest"] = sweep("remove_catch_rest", mag, {**gun, **{"mag_release": GEO["mag_release"]}},
                                         lambda v: MO.magazine(v), drop, "sliding")
    MG["note"] = ("M5b is expected to collide while the hook holds the magazine (the catch retains it) and only at the "
                  "hook: hits outside mag_release fail")
    R["magfit"] = MG

# ------------------------------------------------------------------------------------------------ B6a
if "b6a" in ONLY:
    from gunlib import qa_gun
    res = qa_gun.b6a_topology(OBJS, name=f"SM_{CODE}_B6aCheck")
    res["deny_list"] = {o.name: qa_gun.deny_hits(o.name) for o in OBJS if qa_gun.deny_hits(o.name)}
    res["deny_list_clean"] = not res["deny_list"]
    R["B6a"] = res
    print("[B6a] PASSED", res["passed"], [c["name"] for c in res["checks"] if not c["passed"]])

# ------------------------------------------------------------------------------------------------ H1 early
if "h1" in ONLY:
    import bmesh
    from mathutils import Vector
    o = bpy.data.objects["grip"]
    ax = math.radians(D["frames"]["grip"]["axis_deg_from_vertical"])
    n = Vector((math.sin(ax), 0.0, math.cos(ax)))          # the grip axis (rearward-leaning, pointing up)
    H = {}
    for depth in (25.0, 46.0, 70.0):
        web = np.array(D["frames"]["grip"]["web_point_M"])
        p = np.array([web[0], 0.0, web[1]]) - np.array([n.x, 0, n.z]) * depth
        bm = bmesh.new()
        bm.from_mesh(o.data)
        pB = Vector(((p - GRIP) / 1000.0).tolist())
        r = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=pB, plane_no=n,
                                   clear_inner=False, clear_outer=False)
        cut = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)
               and ((e.verts[0].co + e.verts[1].co) / 2 - pB).length < 0.045]      # this section only (not the horn)
        per = sum(e.calc_length() for e in cut) * 1000.0
        H[f"girth_at_{int(depth)}mm_mm"] = round(per, 1)
        bm.free()
    face = 363.2
    web = D["frames"]["grip"]["web_point_M"]
    H["trigger_reach_mm"] = round(math.hypot(face - web[0], -75.0 - web[1]), 1)
    H["length_of_pull_mm"] = round(face - float(GEO["butt_pad"][0][:, 0].min()), 1)
    H["real_reference"] = ("precision-rifle polymer grips: girth ~140-160 mm at the palm; trigger reach 60-80 mm "
                           "(reported; the gate band is the SMG's polymer grip +10 %: <= 167 mm, reach <= 80 mm)")
    R["H1"] = H
    print("[H1]", H)

prev = json.loads(OUT.read_text()) if OUT.exists() else {}
prev.update(R)
OUT.write_text(json.dumps(prev, indent=1, default=float), encoding="utf-8")
print("[SR01] FGATES DONE", OUT)
