"""AR-01 stage 6 build: SM_AR01_Mag from the shipped rifle (headless Blender, on the stage-5 blend):

    blender -b Assets/Guns/AR01.blend --factory-startup --python Scripts/guns/rifle/rifle_mag.py

RIFLE_BUILD_PLAN 2.3 / 3.3 / 6.2 / 7.1 / 8.1, GUN_BUILDING_STUDY 5.6:
- refuses to run unless Exports/Guns/AR01/SM_AR01.fbx is the byte-identical file stage 5 recorded (sha256): if the
  rifle is re-exported, the magazine rebuilds;
- the magazine frame comes from the SHIPPED rifle sidecar (SM_AR01.sockets.json 'Mag'): origin = the front-lug hook,
  axes = the Mag socket's, so the seated magazine attaches with zero relative transform;
- geometry: the magazine's real-geometry parts (curved two-half steel body, pressed ribs, front panel and spine bead,
  feed lips and follower, domed top plates, front locking lug, rear catch lug, layered floor plate: parts/magazine.py,
  detail pass r2b) at LOD0-2 and the blockout silhouette at LOD3, their UV0 (T_AR01_Mag set) and painted maps;
- SM_AR01_Mag_LOD0..3, UV1 (authored fallback), 2 hulls UCX_SM_AR01_Mag_LOD0_00 / _01 (upper / lower half of the curve,
  3 mm overlap: one hull would fill the curve's sagitta; rifle_spec collision_static_twin.mag), 5 sockets (Mag,
  HandReload, Feed, Base, CenterOfMass = the thin-shell centroid), LOD screen sizes derived from the rifle's
  (size_mag = size_rifle x r_mag / r_rifle, measured box half-diagonals of SM_AR01_Mag_LOD0 and SK_AR01);
- qa_check (budget 7,000, UV1, texel target = the measured aggregate), C1, export_fbx(kind="static"), S1.
Writes WorkFiles/guns/rifle/scratch/mag/mag_report.json and saves Assets/Guns/AR01_Mag.blend.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SCRATCH, GRIP, SPEC, GATES  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Euler, Matrix, Vector  # noqa: E402

sys.path.insert(0, str(ROOT / "Scripts"))
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.helpers import make_lod_group, make_socket  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import qa_gun  # noqa: E402

NAME = "SM_AR01_Mag"
EXP = ROOT / "Exports" / "Guns" / "AR01"
MAG_BLEND = ROOT / "Assets" / "Guns" / "AR01_Mag.blend"
OUT = SCRATCH / "mag"
OUT.mkdir(parents=True, exist_ok=True)
BUDGET = 7000
ARC_C_M = np.array([604.8, 0.0, 3.3])


def log(*a):
    print("[AR01-mag]", *a, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def mag_socket_frame(side):
    """Mag socket of the shipped rifle sidecar -> (R, t): Blender frame B rotation and location (mm)."""
    s = next(r for r in side["sockets"] if r["socket"] == "Mag")
    loc = np.array(s["location_cm"], float) * 10.0
    t = np.array([loc[0], -loc[1], loc[2]])
    ro = s["rotation_deg"]
    R = np.array(Euler(GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"]), "XYZ").to_matrix())
    return R, t, s


def lod_mag_objects(lv):
    cn = "AR01_Parts" if lv == 0 else f"AR01_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH" and o.data.materials
            and o.data.materials[0].name == "M_AR01_Mag"]


UVFIX = {}
LOD_TARGETS = {1: 2000, 2: 650, 3: 250}     # plan 3.3: ~1,750 / ~580 / 200-300 (LOD1 a little richer: the pressed ribs)


def decimated_parts(lv):
    """LOD1-3 of the magazine: each LOD0 part (closed solid) collapse-decimated to the LOD's share of the target, UV0
    interpolated (the LOD0 maps stay valid), weighted normals with sharp edges at 35 deg. The part generator at the
    coarse levels either held LOD0 resolution (its fit with the floor plate, build_rifle HOLD_AT) or left 4,520
    triangles at LOD2 with UV0 overlaps, so the magazine LODs are reduced from LOD0 instead."""
    from gunlib import bl
    src = lod_mag_objects(0)
    total = sum(len(o.data.polygons) for o in src)
    out = []
    for o in src:
        c = o.copy()
        c.data = o.data.copy()
        c.name = f"{o.name}_dec{lv}"
        bpy.context.scene.collection.objects.link(c)
        md = c.modifiers.new("dec", "DECIMATE")
        md.decimate_type = "COLLAPSE"
        md.ratio = LOD_TARGETS[lv] / float(total)
        md.use_collapse_triangulate = True
        bl.apply_modifiers(c)
        bl.finish(c)
        bl.weighted_normals(c, keep_sharp=True, sharp_deg=35.0)
        from gunlib import lodfix
        UVFIX.setdefault(lv, {})[o.name] = lodfix.relax_uv_foldovers(c)
        out.append(c)
    return out


def shell_centroid(V, T):
    a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    A = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
    return ((a + b + c) / 3.0 * A[:, None]).sum(0) / A.sum(), float(A.sum())


def main():
    from pipeline import lock as L
    L.assert_owner("AR01", "claude")
    t0 = time.time()
    rep = {"stage": "6 magazine build"}
    rig = json.loads((SCRATCH / "rig" / "rig_report.json").read_text())
    rifle_fbx = EXP / "SM_AR01.fbx"
    want = rig["files"]["Exports/Guns/AR01/SM_AR01.fbx"]["sha256"]
    have = sha256(rifle_fbx)
    rep["rifle_bytes"] = {"file": "Exports/Guns/AR01/SM_AR01.fbx", "sha256": have, "recorded_by_stage5": want,
                          "equal": have == want}
    if have != want:
        raise SystemExit("[AR01-mag] the shipped SM_AR01.fbx is not the stage-5 bytes: re-run stage 5 first")
    side = json.loads((EXP / "SM_AR01.sockets.json").read_text())
    R, t, srec = mag_socket_frame(side)
    rep["mag_frame"] = {"from": "SM_AR01.sockets.json Mag", "location_B_mm": t.round(5).tolist(),
                        "rotation_deg": srec["rotation_deg"], "R": R.round(9).tolist()}
    # mag-local = R^T (B - t), in metres for Blender
    Minv = np.eye(4)
    Minv[:3, :3] = R.T
    Minv[:3, 3] = -R.T @ (t * 0.001)
    Mx = Matrix(Minv.tolist())
    mat = bpy.data.materials["M_AR01_Mag"]
    coll = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(coll)
    lods = []
    rep["lods"] = {}
    for lv in range(4):
        objs = lod_mag_objects(0) if lv == 0 else decimated_parts(lv)
        ob = GM.join_copies(objs, f"{NAME}_LOD{lv}", coll, lambda o: 0, [mat], None)
        ob.data.transform(Mx)
        ob.matrix_world = Matrix.Identity(4)
        for lay in list(ob.data.uv_layers):
            if lay.name != "UV0":
                ob.data.uv_layers.remove(lay)
        if lv:
            from gunlib import lodfix
            rep.setdefault("uv0_overlap_fix", {})[ob.name] = lodfix.fix_uv_overlaps(ob)
        GM.uv1_from_uv0(ob, {0: (0.0, 0.0, 1.0)})
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        rep["lods"][ob.name] = {"triangles": tris, "parts": [o.name for o in objs],
                                "method": "LOD0 parts" if lv == 0 else f"LOD0 parts collapse-decimated to ~{LOD_TARGETS[lv]}"}
        if lv:
            rep["lods"][ob.name]["uv0_foldover_fix"] = UVFIX.get(lv)
            for o in objs:
                bpy.data.objects.remove(o, do_unlink=True)
        lods.append(ob)
        log(ob.name, tris)
    lod0 = lods[0]
    V0, T0 = GM.mesh_vt(lod0)                                       # mag frame, mm
    # ---------------------------------------------------------------- hulls: upper / lower half of the curve
    C = R.T @ (ARC_C_M - GRIP - t)                                  # arc centre in the mag frame
    samples = []
    for lv, ob in enumerate(lods):
        V, T = GM.mesh_vt(ob)
        samples.append(V if lv == 3 else GM.dense_samples(V, T, 1.0 if lv == 0 else 2.0))
    P = np.vstack(samples)
    ang = np.degrees(np.arctan2(P[:, 2] - C[2], P[:, 0] - C[0]))
    a_lo, a_hi = float(ang.min()), float(ang.max())
    a_mid = 0.5 * (a_lo + a_hi)
    r_mid = float(np.median(np.hypot(P[:, 0] - C[0], P[:, 2] - C[2])))
    ov = math.degrees(1.5 / r_mid)                                  # +-1.5 mm: 3 mm overlap along the arc
    # the upper hull spans the top (larger angle magnitude = nearer the receiver: angles about -170..-128 deg)
    upper = P[ang <= a_mid + ov] if abs(a_lo) > abs(a_hi) else P[ang >= a_mid - ov]
    lower = P[ang > a_mid - ov] if abs(a_lo) > abs(a_hi) else P[ang < a_mid + ov]
    hulls = []
    for i, (pts, what) in enumerate(((upper, "upper half of the curve: lugs, lips, top plates"),
                                     (lower, "lower half: ribs' lower ends, band, floor plate"))):
        h = GM.hull_from_points(f"UCX_{NAME}_LOD0_{i:02d}", pts * 0.001, lod0, coll)
        hulls.append(h)
        rep.setdefault("hulls", []).append({"name": h.name, "covers": what, "vertices": len(h.data.vertices),
                                            "points": int(len(pts))})
    rep["hull_split"] = {"arc_centre_mag_mm": C.round(3).tolist(), "angle_range_deg": [round(a_lo, 3), round(a_hi, 3)],
                         "split_deg": round(a_mid, 3), "overlap_mm": 3.0}
    # ---------------------------------------------------------------- sockets (spec; CoM computed)
    com, area = shell_centroid(V0, T0)
    rep["center_of_mass"] = {"mag_mm": com.round(3).tolist(), "method": "area centroid of the LOD0 surface (a pressed "
                             "sheet-steel box: mass in the skin, not the volume)", "surface_cm2": round(area / 100.0, 2),
                             "mass_kg_empty": 0.33, "mass_kg_loaded": 0.82}
    rep["sockets"] = {}
    for r in SPEC.sockets["mag"]:
        n = r["socket"]
        loc = com if n == "CenterOfMass" else np.array(r["mag_mm"], float)
        ro = r["unreal_rotation_deg"]
        e = GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"])
        make_socket(lod0, n, tuple(loc * 0.001), e)
        rep["sockets"][n] = {"mag_mm": [round(float(v), 4) for v in loc], "unreal_rotation_deg": ro,
                             "computed": n == "CenterOfMass"}
    # ---------------------------------------------------------------- LOD group + derived screen sizes
    grp = make_lod_group(NAME, lods)
    for o in [grp] + list(grp.children_recursive):
        for c in list(o.users_collection):
            if c != coll:
                c.objects.unlink(o)
        if coll not in o.users_collection:
            coll.objects.link(o)
    rifle_sizes = json.loads((GATES / "game_lod_sizes.json").read_text())["SM_AR01"]
    r_mag = 0.5 * float(np.linalg.norm(V0.max(0) - V0.min(0))) / 1000.0
    Vsk, _ = GM.mesh_vt(bpy.data.objects["SK_AR01"])
    r_rifle = 0.5 * float(np.linalg.norm(Vsk.max(0) - Vsk.min(0))) / 1000.0
    sizes = [1.0] + [round(s * r_mag / r_rifle, 4) for s in rifle_sizes[1:]]
    grp["lod_screen_sizes"] = json.dumps(sizes)
    rep["lod_screen_sizes"] = {"sizes": sizes, "r_mag_m": round(r_mag, 4), "r_rifle_m (SK_AR01, no mag)": round(r_rifle, 4),
                               "rifle_sizes": rifle_sizes, "spec_derived": SPEC.d["lods"]["mag_screen_sizes_derived"],
                               "rule": "size_mag = size_rifle x r_mag / r_rifle (box half-diagonals): both switch at "
                                       "the same distance; Unreal's bounds re-derive them in stage 8"}
    # ---------------------------------------------------------------- C1
    rng = np.random.default_rng(20261006)
    Pj = GM.dense_samples(V0, T0, 0.5, rng) * 0.001
    ins = GM.inside_union(Pj, hulls)
    Vall = np.vstack([GM.mesh_vt(o)[0] for o in lods]) * 0.001
    insv = GM.inside_union(Vall, hulls)
    rep["C1"] = {"hulls": len(hulls), "hull_vertices": [len(h.data.vertices) for h in hulls],
                 "jittered_lod0_samples": int(len(Pj)), "samples_outside": int((~ins).sum()),
                 "lod_vertices": int(len(Vall)), "vertices_outside": int((~insv).sum()),
                 "pass": bool(ins.all() and insv.all() and len(hulls) == 2 and max(len(h.data.vertices) for h in hulls) <= 32)}
    log("C1", rep["C1"])
    # ---------------------------------------------------------------- qa_check, export
    q0 = qa_check(lods, budget_tris=BUDGET, texel_density=None, require_uv1=True)
    agg = {c["object"]: float(c["detail"].split(" px/cm")[0]) for c in q0["checks"] if c["name"] == "texel_density"}
    q = qa_check(lods[:3], budget_tris=BUDGET, texel_density=agg[f"{NAME}_LOD0"], require_uv1=True)
    failed = [c for c in q0["checks"] + q["checks"] if not c["passed"]]
    rep["qa_check"] = {"passed": q0["passed"] and q["passed"], "triangles": q0["triangles"],
                       "texel_target_px_cm": agg[f"{NAME}_LOD0"], "texel_aggregate": agg, "failed": failed,
                       "checks": len(q0["checks"]) + len(q["checks"])}
    log("qa_check", rep["qa_check"]["passed"], [c["name"] + ":" + str(c["object"]) for c in failed][:10])
    if not rep["qa_check"]["passed"]:
        (OUT / "mag_report.json").write_text(json.dumps(rep, indent=1, default=str))
        raise SystemExit("[AR01-mag] qa_check failed: not exported")
    res = export_fbx(str(EXP / f"{NAME}.fbx"), [grp], kind="static", lod_screen_sizes=sizes)
    rep["export"] = {"fbx": res["filepath"], "sidecar": res["sidecar"], "warnings": res["warnings"],
                     "lod_screen_sizes": res["lod_screen_sizes"]}
    # ---------------------------------------------------------------- S1
    ms = json.loads(Path(res["sidecar"]).read_text())
    worst_mm = worst_deg = 0.0
    rows = []
    for s in ms["sockets"]:
        b = rep["sockets"][s["socket"]]
        e = [b["mag_mm"][0] / 10.0, -b["mag_mm"][1] / 10.0, b["mag_mm"][2] / 10.0]
        dmm = max(abs(a - x) for a, x in zip(s["location_cm"], e)) * 10.0
        er = b["unreal_rotation_deg"]
        ddeg = max(abs(((s["rotation_deg"][k] - er[k]) + 180.0) % 360.0 - 180.0) for k in ("roll", "pitch", "yaw"))
        worst_mm, worst_deg = max(worst_mm, dmm), max(worst_deg, ddeg)
        rows.append({"socket": s["socket"], "location_cm": s["location_cm"], "rotation_deg": s["rotation_deg"],
                     "d_mm": round(dmm, 6), "d_deg": round(ddeg, 6)})
    names = sorted(r["socket"] for r in rows)
    rep["S1"] = {"sockets": rows, "names_match_spec": names == sorted(r["socket"] for r in SPEC.sockets["mag"]),
                 "worst_mm": round(worst_mm, 6), "worst_deg": round(worst_deg, 6),
                 "pass": names == sorted(r["socket"] for r in SPEC.sockets["mag"]) and worst_mm <= 0.001 and worst_deg <= 0.001}
    allnames = [o.name for o in coll.objects] + [mat.name] + [r["socket"] for r in rows] + [Path(res["filepath"]).name]
    hits = {n: qa_gun.deny_hits(n) for n in allnames if qa_gun.deny_hits(n)}
    rep["B10_names"] = {"checked": len(allnames), "hits": hits, "pass": not hits}
    rep["files"] = {str(Path(f).relative_to(ROOT)).replace("\\", "/"): {"sha256": sha256(f), "bytes": Path(f).stat().st_size}
                    for f in (res["filepath"], res["sidecar"])}
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / "mag_report.json").write_text(json.dumps(rep, indent=1, default=str))
    # ---------------------------------------------------------------- AR01_Mag.blend: the magazine asset alone
    keep = set([grp] + list(grp.children_recursive))
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    for c in list(bpy.data.collections):
        if c != coll:
            bpy.data.collections.remove(c)
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(MAG_BLEND))
    log("MAG_DONE %.1fs" % (time.time() - t0))


main()
