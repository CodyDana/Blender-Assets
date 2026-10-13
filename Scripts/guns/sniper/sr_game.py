"""SR01 W3a/b: LOD1-3 + the static twin SM_SR01 (headless Blender, on the W2 asset blend; the SMG's smg_lods.py +
smg_game.py, adapted):

    blender -b Assets/Guns/SR01.blend --factory-startup --python Scripts/guns/sniper/sr_game.py

LODs (plan 6 budgets: LOD1 ~45 %, LOD2 ~15 %, LOD3 2-3k): every LOD0 part (the surfaced W2 objects: UV0 per set, the
authored UV1, the final custom normals) is copied to '<part>_LOD<k>' in collection SR01_LOD<k> and reduced with
Blender's collapse decimation, which keeps UV seams and both UV layers (no UV re-projection: the LOD0 maps stay valid).
Parts too small to read at the level's switch distance are left out (LOD2: < 130 triangles; LOD3: < 420). After the
decimation: weighted normals again (sharp 30, weight 100: the SMG 0.2.1 rule), then per LOD and set every pair of
overlapping UV0 triangles (qa_check's SAT rule) collapses the smaller one's UVs to its centre (qa ignores zero-area UVs;
the SMG's LOD rule), and the same over the LOD's UV1. UD1 / UD3 are measured on every LOD part.

Twin: game materials M_SR01_Metal (0), M_SR01_Chassis (1), M_SR01_Mag (2) on the painted maps; SM_SR01_LOD0..3 = each
LOD's parts joined, the magazine merged, the bipod FOLDED (bind pose), the riser at rest; UV0 slot k on U tile
(Metal 0, Chassis 1, Mag -1); 10 hulls UCX_SM_SR01_LOD0_00..09 (spec collision.twin_hulls) from dense samples of every
LOD; 20 sockets (spec sockets.gun; CenterOfMass and Holster = the part-volume CoM, magazine out, bipod folded) as
Empties; the LOD group with the start screen sizes (sr_viewgates.py fixes them). Writes scratch/w3/game/game_report.json,
lod<k>_folded_tris.npz + lod<k>_deployed_tris.npz (frame M mm, per-part labels: LOD-pop on both bipod poses) and saves
Assets/Guns/SR01.blend.
"""
from __future__ import annotations

import json
import os
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, WORK, BLEND, GRIP, CODE, PARTS_COLL, D, x_axis_rot  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402

import sr_surface as SS  # noqa: E402
import sr_motion as MO  # noqa: E402
from gunlib import bl  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import ud as UD  # noqa: E402
from gunlib import tspace as TS  # noqa: E402
import sr_lodlib as LL  # noqa: E402
from pipeline.helpers import make_lod_group, make_socket  # noqa: E402

NAME = f"SM_{CODE}"
OUT = WORK / "scratch" / "w3" / "game"
OUT.mkdir(parents=True, exist_ok=True)
TEX = ROOT / "Exports" / "Guns" / CODE / "Textures"
SETS = ("Metal", "Chassis", "Mag")
SLOTS = tuple(SS.SETS[s]["slot"] for s in SETS)
SLOT_INDEX = {s: i for i, s in enumerate(SLOTS)}
TILE = {i: SS.TILE_OF_SET[s] for i, s in enumerate(SETS)}
SCREEN_SIZES_START = [float(v) for v in D["lods"]["gun_screen_sizes_start"]]
MASS_KG = float(D["scale"]["real"]["mass_kg_without_scope_and_mag"])
# g/cm3: steel action / barrel / hardware, aluminium chassis + bipod, polymer grip, rubber pad (the CoM only; the total
# is scaled to the spec's 5.9 kg)
DENSITY = {"M_SR01_Metal": 7.85, "M_SR01_Chassis": 2.7, "M_SR01_Mag": 2.0}
DENSITY_PART = {"grip": 1.2, "butt_pad": 1.1, "bipod_foot_l": 1.1, "bipod_foot_r": 1.1}
TARGET = {1: 0.45, 2: 0.15, 3: 2600}                 # LOD1 / LOD2 share of LOD0, LOD3 triangles
DROP_UNDER = {1: 0, 2: 130, 3: 420}                  # parts left out below this many LOD0 triangles
MIN_TRIS = 16
# (W4 A3) silhouette-weighted LODs: W3's uniform ratio dropped pad_plate at LOD2 (the butt's end: the 2.9 px pop that
# pushed LOD2 to 25.6 m) and spent as many triangles per part on hidden pins / screws / the swivel as on the chassis.
# Silhouette parts are never dropped; the parts that don't make the outline decimate at LOW_W x the ratio.
KEEP_ALWAYS = {"pad_plate", "grip", "magazine_floorplate", "trigger", "cheek_riser", "butt", "butt_pad"}
SIL_LOW = {"pins", "rail_screws", "fasteners", "bipod_pins", "butt_knobs", "riser_posts", "bolt", "bipod_swivel",
           "bipod_knob", "bipod_clamp", "safety", "riser_lever", "mag_release"}
LOW_W = {1: 1.0, 2: 0.4, 3: 0.3}


def solve_ratio(t0, keep, want, lv):
    """the base ratio r so that sum(max(r x w, MIN_TRIS / t0) x t0) = want (w = LOW_W for SIL_LOW parts)."""
    def tot(r):
        return sum(t0[o.name] * min(1.0, max(r * (LOW_W[lv] if o.name in SIL_LOW else 1.0), MIN_TRIS / t0[o.name]))
                   for o in keep)
    lo, hi = 0.0, 1.0 / LOW_W[lv]
    if tot(hi) <= want:
        return hi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if tot(mid) < want else (lo, mid)
    return 0.5 * (lo + hi)
OV = 1.5                                             # each side of a hull split: 3 mm overlap


def log(*a):
    print("[SR01-game]", *a, flush=True)


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def base_of(name):
    for lv in (1, 2, 3):
        if name.endswith(f"_LOD{lv}"):
            return name[: -len(f"_LOD{lv}")]
    return name


def slot_of(o):
    return SLOT_INDEX[part_rec(o)["slot"]]


def lod_objects(lv):
    cn = PARTS_COLL if lv == 0 else f"{CODE}_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH"]


def clean_previous():
    for o in list(bpy.data.objects):
        if (o.name.startswith((NAME, "UCX_" + NAME, "SOCKET_" + NAME)) and not o.name.startswith(NAME + "_Mag")) or \
                any(o.name.endswith(f"_LOD{k}") and not o.name.startswith(("SM_", "SK_", "UCX_")) for k in (1, 2, 3)):
            d = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if d is not None and getattr(d, "users", 1) == 0:
                bpy.data.meshes.remove(d)
    for cn in [NAME] + [f"{CODE}_LOD{k}" for k in (1, 2, 3)] + ["_W2_TwinCheck"]:
        c = bpy.data.collections.get(cn)
        if c is not None:
            for o in list(c.objects):
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.collections.remove(c)
    for m in list(bpy.data.meshes):
        if m.users == 0:
            bpy.data.meshes.remove(m)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)


# ---------------------------------------------------------------------------------- LODs
def tris_of(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def make_lods(rep):
    parts0 = lod_objects(0)
    t0 = {o.name: tris_of(o) for o in parts0}
    total0 = sum(t0.values())
    rep["lod0_triangles"] = total0
    for lv in (1, 2, 3):
        coll = bpy.data.collections.new(f"{CODE}_LOD{lv}")
        bpy.context.scene.collection.children.link(coll)
        keep = [o for o in parts0 if t0[o.name] >= DROP_UNDER[lv] or o.name in KEEP_ALWAYS]
        want = TARGET[lv] * total0 if lv < 3 else TARGET[lv]
        ratio = solve_ratio(t0, keep, want, lv)
        rows = {}
        for o in keep:
            r = min(1.0, max(ratio * (LOW_W[lv] if o.name in SIL_LOW else 1.0), MIN_TRIS / max(t0[o.name], 1)))
            c = LL.decimate_copy(o, f"{o.name}_LOD{lv}", coll, r)
            rows[c.name] = {"lod0": t0[o.name], "tris": tris_of(c), "ratio": round(r, 4)}
        rep["lods_parts"][f"LOD{lv}"] = {"ratio": round(ratio, 4), "dropped": sorted(o.name for o in parts0
                                                                                      if o not in keep),
                                         "triangles": sum(v["tris"] for v in rows.values()), "parts": rows}
        log(f"LOD{lv}", rep["lods_parts"][f"LOD{lv}"]["triangles"], "tris, ratio", round(ratio, 3), "dropped",
            rep["lods_parts"][f"LOD{lv}"]["dropped"])


def surface_lods(rep):
    for lv in (1, 2, 3):
        objs = lod_objects(lv)
        fx = {}
        for st in SETS:
            fx[f"UV0_{st}"] = LL.fix_uv_overlaps([o for o in objs if SS.SLOT_SET[part_rec(o)["slot"]] == st], "UV0")
        fx["UV1"] = LL.fix_uv_overlaps(objs, "UV1")
        import sr_uv                                  # UD3: the W2 visible-sliver rule on the LOD parts (normals only)
        sr_uv.F32.clear()
        f32 = sr_uv.f32_visible({o.name: o for o in objs})
        rep["lods_parts"][f"LOD{lv}"]["ud3_visible_slivers"] = {k: {x: v[x] for x in ("corners_before", "corners_after")}
                                                               for k, v in f32.items()}
        ud = {}
        for o in objs:
            r = UD.check_object(o)
            z = TS.float32_zero_corners(o.data, "UV0")
            ud[o.name] = {"ud1_drops": int(r["unreal_drops"]), "min_area_mm2": r["min_area_mm2"], "ud3_zero": int(len(z))}
        rep["lods_parts"][f"LOD{lv}"]["uv_overlaps_collapsed"] = fx
        rep["lods_parts"][f"LOD{lv}"]["ud"] = {"drops": sum(v["ud1_drops"] for v in ud.values()),
                                              "min_area_mm2": min(v["min_area_mm2"] for v in ud.values()),
                                              "ud3_zero": sum(v["ud3_zero"] for v in ud.values()),
                                              "parts_with_issues": {k: v for k, v in ud.items()
                                                                    if v["ud1_drops"] or v["ud3_zero"]}}
        log(f"LOD{lv} uv overlaps collapsed", fx, "UD", {k: v for k, v in rep["lods_parts"][f"LOD{lv}"]["ud"].items()
                                                         if k != "parts_with_issues"})


# ---------------------------------------------------------------------------------- poses / npz
def pose_M(bone, deployed):
    if not deployed:
        return None
    for sd in ("l", "r"):
        if bone == f"bipod_leg_{sd}":
            return MO.leg(sd, 90.0)
        if bone == f"bipod_leg_{sd}_ext":
            return MO.leg_ext(sd, 90.0, 0.0)
    return None


def export_lod_npz(objs, path, deployed=False):
    Vs, Ts, Ls, names = [], [], [], []
    n = 0
    for k, ob in enumerate(objs):
        V, T = bl.tris_np(ob, GRIP)
        M = pose_M(part_rec(ob).get("bone"), deployed)
        if M is not None:
            V = V @ M[:3, :3].T + M[:3, 3]
        Vs.append(V)
        Ts.append(T + n)
        Ls.append(np.full(len(T), k, np.int32))
        names.append(base_of(ob.name))
        n += len(V)
    np.savez_compressed(path, V=np.vstack(Vs), T=np.vstack(Ts), lab=np.concatenate(Ls), names=np.array(names))


# ---------------------------------------------------------------------------------- hulls (spec collision.twin_hulls)
SPREAD = ("chassis", "receiver", "rail", "rail_screws", "fasteners", "pins")
X_ACTION, X_WELL1, X_BARREL_OUT = 414.0, 504.0, 830.0
Z_GUARD = -52.0


def hull_points(S):
    def take(names):
        return [S[n] for n in names if n in S]

    def reg(names, f):
        out = []
        for n in names:
            if n in S:
                P = S[n]
                out.append(P[f(P)])
        return out
    x = lambda P: P[:, 0]                                          # noqa: E731
    z = lambda P: P[:, 2]                                          # noqa: E731
    return [
        ("butt + pad + pad plate + butt knobs", take(("butt", "butt_pad", "pad_plate", "butt_knobs"))),
        ("cheek riser + posts + lever", take(("cheek_riser", "riser_posts", "riser_lever"))),
        ("grip + trigger guard + trigger + release paddle",
         take(("grip", "trigger", "mag_release")) + reg(("chassis",), lambda P: (x(P) < X_ACTION + OV) & (z(P) < Z_GUARD + OV))),
        ("action: chassis centre, receiver rear, rail rear, bolt + handle, safety",
         take(("bolt", "bolt_handle", "safety")) + reg(SPREAD, lambda P: (x(P) < X_ACTION + OV) & (z(P) >= Z_GUARD - OV))),
        ("magazine well + merged magazine (twin only)",
         take(("magazine", "magazine_floorplate")) + reg(SPREAD, lambda P: (x(P) >= X_ACTION - OV) & (x(P) < X_WELL1 + OV))),
        ("forend + clamp + barrel inside the channel",
         take(("bipod_clamp",)) + reg(SPREAD, lambda P: x(P) >= X_WELL1 - OV) +
         reg(("barrel",), lambda P: x(P) < X_BARREL_OUT + OV)),
        ("barrel (exposed) + muzzle device", take(("muzzle_device",)) + reg(("barrel",), lambda P: x(P) >= X_BARREL_OUT - OV)),
        ("bipod swivel + tension knob + pins", take(("bipod_swivel", "bipod_knob", "bipod_pins"))),
        ("bipod leg left (folded) + extension + foot", take(("bipod_leg_l", "bipod_ext_l", "bipod_foot_l"))),
        ("bipod leg right (folded) + extension + foot", take(("bipod_leg_r", "bipod_ext_r", "bipod_foot_r"))),
    ]


def valid_hull(name, P_m, parent, coll):
    """(W4) gunlib's hull_from_points, checked: every face outward, the box within the points' box + 20 mm, every point
    inside. W4's cheek-riser hull (its LOD3 kept now) came back with 18 inward faces and grew to 1e16 m; a failed hull
    is rebuilt with a lower vertex cap (a different collapse path). Returns (hull, tries)."""
    lo, hi = P_m.min(0) - 0.02, P_m.max(0) + 0.02
    for k, (how, mv) in enumerate((("gunlib", 32), ("safe", 32), ("safe", 30), ("safe", 28))):
        try:
            h = (GM.hull_from_points if how == "gunlib" else LL.hull_safe)(name, P_m, parent, coll, max_verts=mv)
        except RuntimeError as e:                 # gunlib's grow gave up
            log("hull", name, how, mv, repr(e))
            h = bpy.data.objects.get(name)
            if h is not None:
                me = h.data
                bpy.data.objects.remove(h, do_unlink=True)
                bpy.data.meshes.remove(me)
            continue
        V = np.array([v.co[:] for v in h.data.vertices])
        c = V.mean(0)
        inward = sum(1 for p in h.data.polygons if np.dot(np.array(p.normal[:]), np.array(p.center[:]) - c) < 0)
        ok = inward == 0 and np.all(V >= lo) and np.all(V <= hi) and GM.inside_union(P_m, [h], tol_m=1e-6).all()
        if ok:
            return h, [how, mv, k + 1]
        log("hull", name, "invalid (inward", inward, ")", how, "max_verts", mv, "- rebuilt")
        me = h.data
        bpy.data.objects.remove(h, do_unlink=True)
        bpy.data.meshes.remove(me)
    raise SystemExit(f"no valid hull for {name}")


def main():
    from pipeline import lock as L
    L.assert_owner(CODE, "claude")
    t0 = time.time()
    clean_previous()
    for n in [m.name for m in bpy.data.materials if m.name.startswith("BAKE_")]:
        bpy.data.materials.remove(bpy.data.materials[n])
    rep = {"stage": "W3a/b LODs + static twin, hulls, sockets", "lods_parts": {}, "lods": {}, "hulls": [], "sockets": {}}
    make_lods(rep)
    surface_lods(rep)
    mats = [GM.game_material(s, f"T_{CODE}_{st}", TEX) for s, st in zip(SLOTS, SETS)]
    for lv in range(4):
        for o in lod_objects(lv):
            o.data.materials.clear()
            o.data.materials.append(mats[slot_of(o)])
    coll = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(coll)
    lods = []
    for lv in range(4):
        objs = lod_objects(lv)
        ob = GM.join_copies(objs, NAME if lv == 0 else f"{NAME}_LOD{lv}", coll, slot_of, mats, TILE)
        for lay in list(ob.data.uv_layers):
            if lay.name not in ("UV0", "UV1"):
                ob.data.uv_layers.remove(lay)
        ob.data.uv_layers.active = ob.data.uv_layers["UV0"]
        tris = tris_of(ob)
        mi = np.empty(len(ob.data.polygons), np.int32)
        ob.data.polygons.foreach_get("material_index", mi)
        rep["lods"][f"LOD{lv}"] = {"triangles": tris, "gun_triangles_without_mag": int((mi != 2).sum()),
                                   "mag_triangles": int((mi == 2).sum()), "parts": len(objs)}
        lods.append(ob)
        export_lod_npz(objs, OUT / f"lod{lv}_folded_tris.npz")
        export_lod_npz(objs, OUT / f"lod{lv}_deployed_tris.npz", deployed=True)
        log("LOD%d" % lv, tris, "tris")
    lod0 = lods[0]
    # ---------------------------------------------------------------- hulls
    samples = {}
    for lv in range(4):
        for o in lod_objects(lv):
            V, T = GM.mesh_vt(o)
            pts = V if lv == 3 else GM.dense_samples(V, T, 1.0 if lv == 0 else 2.0)
            samples.setdefault(base_of(o.name), []).append(pts + GRIP)
    samples = {k: np.vstack(v) for k, v in samples.items()}
    hulls = []
    for i, (desc, pts) in enumerate(hull_points(samples)):
        P = np.vstack([p for p in pts if len(p)])
        h, tries = valid_hull(f"UCX_{NAME}_{i:02d}", (P - GRIP) * 0.001, lod0, coll)
        hulls.append(h)
        rep["hulls"].append({"name": h.name, "covers": desc, "vertices": len(h.data.vertices), "points": int(len(P)),
                             "tries": tries})
        log("hull", h.name, len(h.data.vertices), "verts from", len(P), "points")
    # C1: every surface sample of every LOD inside the union of the hulls (world metres; the hulls ride LOD0 at identity)
    allP = (np.vstack(list(samples.values())) - GRIP) * 0.001
    ins = GM.inside_union(allP, hulls, tol_m=1e-6)
    rep["C1"] = {"samples": int(len(allP)), "outside": int((~ins).sum()), "max_hull_vertices":
                 max(len(h.data.vertices) for h in hulls), "pass": bool(ins.all()) and len(hulls) == 10}
    log("C1", rep["C1"])
    # ---------------------------------------------------------------- mass properties (bipod folded, magazine out)
    m_tot, mc = 0.0, np.zeros(3)
    parts_g = {}
    for o in lod_objects(0):
        rec = part_rec(o)
        if rec.get("slot") == "M_SR01_Mag":
            continue
        vol, cen = GM.signed_volume_centroid(o)
        g = abs(vol) / 1000.0 * DENSITY_PART.get(o.name, DENSITY[rec["slot"]])
        parts_g[o.name] = round(g, 1)
        m_tot += g
        mc += g * cen
    com_B = mc / m_tot
    rep["mass"] = {"modelled_g": round(m_tot, 1), "mass_kg": MASS_KG, "com_B_mm": [round(float(v), 2) for v in com_B],
                   "com_M_mm": [round(float(v), 2) for v in com_B + GRIP], "parts_g": parts_g,
                   "densities_g_cm3": {"slots": DENSITY, "parts": DENSITY_PART},
                   "note": "part volumes x densities (steel 7.85, aluminium 2.7, polymer 1.2, rubber 1.1); the total is "
                           "scaled to the spec's 5.9 kg (hollow internals not modelled): bipod folded, magazine out"}
    log("mass", round(m_tot, 1), "g modelled, CoM B", np.round(com_B, 2))
    # ---------------------------------------------------------------- sockets (20)
    for r in D["sockets"]["gun"]:
        name = r["socket"]
        loc = np.array(r["B_mm"], float)
        if name in ("CenterOfMass", "Holster"):
            loc = com_B.copy()
        ro = x_axis_rot(r["x_axis_M"])
        eul = GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"])
        make_socket(lod0, name, tuple(loc * 0.001), eul)
        rep["sockets"][name] = {"blender_mm": [round(float(v), 4) for v in loc], "unreal_rotation_deg": ro,
                                "bone": r["bone"], "computed": name in ("CenterOfMass", "Holster")}
    # ---------------------------------------------------------------- LOD group
    grp = make_lod_group(NAME, lods)
    grp["lod_screen_sizes"] = json.dumps(SCREEN_SIZES_START)
    for o in [grp] + list(grp.children_recursive):
        for c in list(o.users_collection):
            if c != coll:
                c.objects.unlink(o)
        if coll not in o.users_collection:
            coll.objects.link(o)
    V0 = GM.mesh_vt(bpy.data.objects[f"{NAME}_LOD0"])[0]
    rep["bounds_radius_m"] = {"twin_engine_sphere_radius": round(GM.static_sphere_radius(V0) / 1000.0, 5),
                              "twin_box_half_diagonal": round(float(0.5 * np.linalg.norm(V0.max(0) - V0.min(0))) / 1000.0, 4),
                              "spec_rest": D["lods"]["rest_bounds_radius_m"]}
    rep["names"] = {"group": grp.name, "lods": [o.name for o in lods], "hulls": [h.name for h in hulls],
                    "sockets": sorted(c.name for c in bpy.data.objects[f"{NAME}_LOD0"].children
                                      if c.name.startswith("SOCKET_"))}
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / "game_report.json").write_text(json.dumps(rep, indent=1))
    bpy.ops.wm.save_as_mainfile(filepath=os.environ.get("SR01_BLEND_OUT", str(BLEND)))   # (dry runs save elsewhere)
    log("GAME_DONE %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
