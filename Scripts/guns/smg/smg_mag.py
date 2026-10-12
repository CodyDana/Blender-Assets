"""SMG01 W3d: SM_SMG01_Mag from the shipped twin (headless Blender, on the W3c blend; the AR-01's rifle_mag.py):

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/smg/smg_mag.py

SMG_BUILD_PLAN 7.2 / 10.2 / 11 / 12.1:
- refuses to run unless Exports/Guns/SMG01/SM_SMG01.fbx is the byte-identical file the rig stage recorded (sha256): a
  re-exported twin rebuilds the magazine;
- the magazine frame from the SHIPPED twin sidecar (SM_SMG01.sockets.json 'Mag': the well-entry centre, +Z up the
  insertion axis), so the seated magazine attaches with zero relative transform;
- SM_SMG01_Mag_LOD0..3 = the magazine parts of each LOD (LOD0 the form parts, LOD1-2 the same generators, LOD3 the
  traced silhouette prism): the very objects the twin merges, so the twin's magazine is the shipped one by construction
  (M10 measured); UV0 = the T_SMG01_Mag set (0..1); UV1 authored for the magazine alone (smg_uv1lib, UD4 at 64 / 128
  px); UD1 / UD3 measured per LOD;
- 1 hull UCX_SM_SMG01_Mag_LOD0_00 (straight magazine: spec collision.mag), 5 sockets (spec; CenterOfMass = the LOD0
  solid's volume centroid), LOD screen sizes derived from the SK's (size_mag = size_SK x r_mag / r_SK engine);
- qa_check (budget 5,000, UV1, texel = the measured aggregate), C1, export_fbx(kind="static"), S1, B10.
Writes scratch/mag/mag_report.json and saves Assets/Guns/SMG01_Mag.blend (the magazine alone).
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SCRATCH, GATES, SPEC, CODE, PARTS_COLL, D  # noqa: E402

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Euler, Matrix  # noqa: E402

from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.helpers import make_lod_group, make_socket  # noqa: E402
from gunlib import game as GM  # noqa: E402
from gunlib import qa_gun  # noqa: E402
from gunlib import ud as UD  # noqa: E402
from gunlib import tspace as TS  # noqa: E402
import smg_uv1lib as U1  # noqa: E402
import smg_ud4 as UD4  # noqa: E402

NAME = f"SM_{CODE}_Mag"
SM = f"SM_{CODE}"
EXP = ROOT / "Exports" / "Guns" / CODE
MAG_BLEND = ROOT / "Assets" / "Guns" / f"{CODE}_Mag.blend"
OUT = SCRATCH / "mag"
OUT.mkdir(parents=True, exist_ok=True)
BUDGET = int(D["budgets_triangles"]["mag"]["lod0_ceiling"])
MAG_SLOT = "M_SMG01_Mag"


def log(*a):
    print("[SMG01-mag]", *a, flush=True)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def part_rec(ob):
    try:
        return json.loads(ob.get("gun_part", "{}"))
    except Exception:  # noqa: BLE001
        return {}


def mag_objects(lv):
    cn = PARTS_COLL if lv == 0 else f"{CODE}_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH" and part_rec(o).get("slot") == MAG_SLOT]


def mag_socket_frame(side):
    s = next(r for r in side["sockets"] if r["socket"] == "Mag")
    loc = np.array(s["location_cm"], float) * 10.0
    t = np.array([loc[0], -loc[1], loc[2]])
    ro = s["rotation_deg"]
    R = np.array(Euler(GM.blender_euler_for_ue(ro["roll"], ro["pitch"], ro["yaw"]), "XYZ").to_matrix())
    return R, t, s


def twin_mag_check(lods, Mx):
    """M10: the twin SM_SMG01_LOD<n>'s magazine faces against SM_SMG01_Mag_LOD<n> (both in the magazine frame):
    triangle counts equal and every vertex within 0.001 mm of the other set (both ways)."""
    def nearest(A, B):
        if not len(A) or not len(B):
            return 1e9
        worst = 0.0
        for i in range(0, len(A), 512):
            d = np.sqrt(((A[i:i + 512, None, :] - B[None, :, :]) ** 2).sum(-1)).min(1)
            worst = max(worst, float(d.max()))
        return worst
    out = {"lods": {}, "rule": "twin magazine tris == SM_SMG01_Mag_LOD<n> tris; vertex sets within 0.001 mm both ways"}
    ok = True
    for lv, mob in enumerate(lods):
        tw = bpy.data.objects.get(f"{SM}_LOD{lv}")
        slot = next(i for i, m in enumerate(tw.data.materials) if m and m.name == MAG_SLOT)
        mw = Matrix(Mx) @ tw.matrix_world
        Vt, tt = [], 0
        for poly in tw.data.polygons:
            if poly.material_index == slot:
                tt += len(poly.vertices) - 2
                Vt += [tuple(mw @ tw.data.vertices[i].co) for i in poly.vertices]
        Vt = np.unique(np.round(np.array(Vt) * 1000.0, 5), axis=0)
        Vm = np.unique(np.round(np.array([tuple(mob.matrix_world @ v.co) for v in mob.data.vertices]) * 1000.0, 5), axis=0)
        mt = sum(len(p.vertices) - 2 for p in mob.data.polygons)
        dev = float(max(nearest(Vt, Vm), nearest(Vm, Vt)))
        good = tt == mt and dev <= 0.001
        ok &= good
        out["lods"][f"LOD{lv}"] = {"twin_tris": int(tt), "mag_tris": int(mt), "max_dev_mm": round(dev, 6),
                                   "pass": bool(good)}
    out["pass"] = bool(ok)
    return out


def main():
    from pipeline import lock as L
    L.assert_owner(CODE, "claude")
    t0 = time.time()
    rep = {"stage": "W3d magazine build"}
    rig = json.loads((SCRATCH / "rig" / "rig_report.json").read_text())
    gun_fbx = EXP / f"{SM}.fbx"
    key = f"Exports/Guns/{CODE}/{SM}.fbx"
    want, have = rig["files"][key]["sha256"], sha256(gun_fbx)
    rep["gun_bytes"] = {"file": key, "sha256": have, "recorded_by_rig": want, "equal": have == want}
    if have != want:
        raise SystemExit("[SMG01-mag] the shipped SM_SMG01.fbx is not the rig stage's bytes: re-run the rig first")
    side = json.loads((EXP / f"{SM}.sockets.json").read_text())
    R, t, srec = mag_socket_frame(side)
    rep["mag_frame"] = {"from": f"{SM}.sockets.json Mag", "location_B_mm": t.round(5).tolist(),
                        "rotation_deg": srec["rotation_deg"], "R": R.round(9).tolist()}
    Minv = np.eye(4)
    Minv[:3, :3] = R.T
    Minv[:3, 3] = -R.T @ (t * 0.001)
    Mx = Matrix(Minv.tolist())
    mat = bpy.data.materials[MAG_SLOT]
    for o in list(bpy.data.objects):
        if o.name.startswith((NAME, "UCX_" + NAME, "SOCKET_" + NAME)):
            bpy.data.objects.remove(o, do_unlink=True)
    c0 = bpy.data.collections.get(NAME)
    if c0 is not None:
        bpy.data.collections.remove(c0)
    coll = bpy.data.collections.new(NAME)
    bpy.context.scene.collection.children.link(coll)
    vis0 = np.load(SCRATCH / "uv" / "islands.npz")
    visL = np.load(SCRATCH / "uv" / "lod_vis.npz")
    lods = []
    rep["lods"], rep["uv1"], rep["ud4"], rep["ud"] = {}, {}, {}, {}
    for lv in range(4):
        objs = mag_objects(lv)
        vis = np.concatenate([(vis0[f"{o.name}__vis"] if lv == 0 else visL[o.name]).astype(bool) for o in objs])
        ob = GM.join_copies(objs, f"{NAME}_LOD{lv}", coll, lambda o: 0, [mat], None)
        ob.data.transform(Mx)
        ob.matrix_world = Matrix.Identity(4)
        for lay in list(ob.data.uv_layers):
            if lay.name not in ("UV0", "UV1"):
                ob.data.uv_layers.remove(lay)
        r1, T1, C1 = U1.author({ob.name: ob}, {ob.name: vis}, keep=40, min_keep_mm2=150.0)
        rows = [UD4.measure(T1.astype(np.float64), C1, Rr, 2) for Rr in (64, 128)]
        rep["uv1"][ob.name] = {k: r1[k] for k in ("charts_packed", "fill", "overlap_pairs_qa", "range")}
        rep["ud4"][ob.name] = {"rows": rows, "pass": all(r_["pass"] for r_ in rows)}
        r = UD.check_object(ob)
        rep["ud"][ob.name] = {"ud1_drops": int(r["unreal_drops"]), "min_area_mm2": r["min_area_mm2"],
                              "ud3_collapsed_unreal": int(len(TS.collapsed(ob.data, "UV0", unreal=True)))}
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        rep["lods"][ob.name] = {"triangles": tris, "parts": [o.name for o in objs],
                                "method": "LOD0 form parts" if lv == 0 else
                                ("the same generators at gunlib.lod level %d" % lv if lv < 3 else
                                 "the blockout generator (traced silhouette prism)")}
        lods.append(ob)
        log(ob.name, tris, "UD4", rep["ud4"][ob.name]["pass"], "UD", rep["ud"][ob.name])
    rep["twin_mag_equal"] = twin_mag_check(lods, Mx)
    log("twin mag = shipped mag per LOD", rep["twin_mag_equal"]["pass"])
    lod0 = lods[0]
    V0, T0 = GM.mesh_vt(lod0)
    # ---------------------------------------------------------------- hull (one: straight magazine)
    samples = []
    for lv, ob in enumerate(lods):
        V, T = GM.mesh_vt(ob)
        samples.append(V if lv == 3 else GM.dense_samples(V, T, 1.0 if lv == 0 else 2.0))
    P = np.vstack(samples)
    h = GM.hull_from_points(f"UCX_{NAME}_LOD0_00", P * 0.001, lod0, coll)
    hulls = [h]
    rep["hulls"] = [{"name": h.name, "covers": "the whole straight magazine", "vertices": len(h.data.vertices),
                     "points": int(len(P))}]
    # ---------------------------------------------------------------- sockets (spec; CoM computed)
    vol, com = 0.0, np.zeros(3)
    for o in mag_objects(0):
        v, c = GM.signed_volume_centroid(o)
        vol += abs(v)
        com += abs(v) * c
    com_B = com / vol
    com_mag = R.T @ (com_B - t)
    rep["center_of_mass"] = {"mag_mm": com_mag.round(3).tolist(), "method": "volume centroid of the LOD0 magazine "
                             "solids (moulded polymer shell, follower, floor plate)", "volume_cm3": round(vol / 1000.0, 2)}
    rep["sockets"] = {}
    for r in SPEC.mag_sockets():
        n = r["socket"]
        loc = com_mag if n == "CenterOfMass" else np.array(r["mag_mm"], float)
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
    sk_sizes, r_sk = rig["lod_screen_sizes"]["SK"], float(rig["lod_screen_sizes"]["r_sk_engine_m"])
    r_mag = GM.static_sphere_radius(V0) / 1000.0          # (W4) Unreal's static-mesh sphere radius (was the half-diagonal)
    sizes = [1.0] + [round(s * r_mag / r_sk, 5) for s in sk_sizes[1:]]
    grp["lod_screen_sizes"] = json.dumps(sizes)
    rep["lod_screen_sizes"] = {"sizes": sizes, "r_mag_m": round(r_mag, 4), "r_SK_engine_m": r_sk, "SK_sizes": sk_sizes,
                               "spec_derived_start": D["lods"]["mag_screen_sizes_derived"],
                               "rule": "size_mag = size_SK x r_mag / r_SK (the SK's engine radius incl. the bounds "
                                       "extension): the attached magazine switches with the gun"}
    # ---------------------------------------------------------------- C1
    rng = np.random.default_rng(20261011)
    Pj = GM.dense_samples(V0, T0, 0.5, rng) * 0.001
    ins = GM.inside_union(Pj, hulls)
    Vall = np.vstack([GM.mesh_vt(o)[0] for o in lods]) * 0.001
    insv = GM.inside_union(Vall, hulls)
    rep["C1"] = {"hulls": len(hulls), "hull_vertices": [len(x.data.vertices) for x in hulls],
                 "jittered_lod0_samples": int(len(Pj)), "samples_outside": int((~ins).sum()),
                 "lod_vertices": int(len(Vall)), "vertices_outside": int((~insv).sum()),
                 "pass": bool(ins.all() and insv.all() and len(hulls) == 1 and len(h.data.vertices) <= 32)}
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
        raise SystemExit("[SMG01-mag] qa_check failed: not exported")
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
    want_names = sorted(r["socket"] for r in SPEC.mag_sockets())
    rep["S1"] = {"sockets": rows, "names_match_spec": names == want_names, "worst_mm": round(worst_mm, 6),
                 "worst_deg": round(worst_deg, 6), "pass": names == want_names and worst_mm <= 0.001 and worst_deg <= 0.001}
    allnames = [o.name for o in coll.objects] + [mat.name] + [r["socket"] for r in rows] + [Path(res["filepath"]).name]
    hits = {n: qa_gun.deny_hits(n) for n in allnames if qa_gun.deny_hits(n)}
    rep["B10_names"] = {"checked": len(allnames), "hits": hits, "pass": not hits}
    rep["files"] = {str(Path(f).relative_to(ROOT)).replace("\\", "/"): {"sha256": sha256(f), "bytes": Path(f).stat().st_size}
                    for f in (res["filepath"], res["sidecar"])}
    rep["seconds"] = round(time.time() - t0, 1)
    (OUT / "mag_report.json").write_text(json.dumps(rep, indent=1, default=str))
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
