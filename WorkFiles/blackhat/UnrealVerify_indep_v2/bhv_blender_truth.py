"""INDEPENDENT Blender-side truth for the Unreal verification of SM_BlackHat.

Uses none of the build's code or reports.
    mode fbx   : fresh factory-startup Blender imports the SHIPPED FBX bytes and measures
                 every node (triangles, UVs, hulls, bounds, head-seat geometry).
    mode blend : opens Assets/BlackHat.blend READ-ONLY (never saved) and counts the
                 evaluated triangles of every mesh object.

    blender.exe -b [Assets/BlackHat.blend] --factory-startup --python bhv_blender_truth.py -- fbx|blend
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "blackhat" / "UnrealVerify_indep_v2"
FBX = PROJ / "Exports" / "BlackHat" / "SM_BlackHat.fbx"
SIDECAR = PROJ / "Exports" / "BlackHat" / "SM_BlackHat.sockets.json"
MODE = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "fbx"


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def arrays(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    mw = np.array(obj.matrix_world, dtype=np.float64)
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    co = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3]
    tv = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tv)
    tl = np.empty(len(me.loop_triangles) * 3, np.int64)
    me.loop_triangles.foreach_get("loops", tl)
    tm = np.empty(len(me.loop_triangles), np.int64)
    me.loop_triangles.foreach_get("material_index", tm)
    tv, tl = tv.reshape(-1, 3), tl.reshape(-1, 3)
    uvs = {}
    for layer in me.uv_layers:
        uv = np.empty(len(me.loops) * 2, np.float64)
        layer.data.foreach_get("uv", uv)
        uvs[layer.name] = uv.reshape(-1, 2)[tl]
    edges = {}
    for a, b, c in tv:
        for e in ((a, b), (b, c), (c, a)):
            k = (min(e), max(e))
            edges[k] = edges.get(k, 0) + 1
    hist = {}
    for v in edges.values():
        hist[str(v)] = hist.get(str(v), 0) + 1
    out = {"verts": co, "tv": tv, "tris": co[tv], "uvs": uvs, "tri_mat": tm, "edge_hist": hist,
           "mats": [s.material.name if s.material else None for s in obj.material_slots],
           "n_polys": len(me.polygons)}
    ev.to_mesh_clear()
    return out


def face_planes(verts, tv):
    """Outward planes of a closed mesh's triangles (normal from winding), deduplicated."""
    P = verts[tv]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    L = np.linalg.norm(n, axis=1)
    keep = L > 1e-14
    n = n[keep] / L[keep, None]
    d = (n * P[keep, 0]).sum(1)
    return n, d


def convex_report(verts, tv):
    n, d = face_planes(verts, tv)
    s = verts @ n.T - d                     # <= 0 means behind every face plane
    scale = max(1.0, float(np.abs(verts).max()))
    centroid = verts.mean(0)
    sc = n @ centroid - d
    return n, d, {"vertices": int(len(verts)), "triangles": int(len(tv)),
                  "max_vertex_in_front_of_a_face_cm": float(s.max()),
                  "convex_within_1e-4cm": bool(s.max() <= 1e-4 * scale),
                  "centroid_behind_all_faces": bool((sc < 0).all()),
                  "aabb_min_cm": verts.min(0).round(4).tolist(), "aabb_max_cm": verts.max(0).round(4).tolist()}


def signed_in(n, d, pts):
    return (pts @ n.T - d).max(1)          # > 0 outside


def run_fbx():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    before = sha256(FBX)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    side = json.loads(SIDECAR.read_text(encoding="utf-8"))
    rep = {"mode": "fbx", "fbx_sha256": before, "blender": bpy.app.version_string,
           "sidecar_sha256": sha256(SIDECAR), "nodes": {}}
    A = {}
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        e = {"type": obj.type, "parent": obj.parent.name if obj.parent else None,
             "matrix_world": [[round(float(v), 7) for v in row] for row in obj.matrix_world]}
        if obj.type == "MESH":
            a = arrays(obj)
            v_cm = a["verts"] * 100.0
            A[obj.name] = a
            e.update({"triangles": int(len(a["tv"])), "vertices": int(len(a["verts"])), "polygons": a["n_polys"],
                      "materials": a["mats"],
                      "triangles_per_material": {str(a["mats"][i] if i < len(a["mats"]) else i): int((a["tri_mat"] == i).sum())
                                                 for i in sorted(set(a["tri_mat"].tolist()))},
                      "uv_layers": list(a["uvs"].keys()),
                      "uv_ranges": {k: [v.reshape(-1, 2).min(0).round(5).tolist(), v.reshape(-1, 2).max(0).round(5).tolist()]
                                    for k, v in a["uvs"].items()},
                      "edge_use_hist": a["edge_hist"],
                      "aabb_min_cm": v_cm.min(0).round(4).tolist(), "aabb_max_cm": v_cm.max(0).round(4).tolist()})
            np.save(HERE / f"truth_{obj.name}_verts_cm.npy", v_cm)
            np.save(HERE / f"truth_{obj.name}_tv.npy", a["tv"])
        rep["nodes"][obj.name] = e

    lods = sorted(n for n in A if n.startswith("SM_BlackHat_LOD"))
    ucx = sorted(n for n in A if n.startswith("UCX_"))
    rep["lod_names"] = lods
    rep["ucx_names"] = ucx
    rep["empties"] = [n for n, e in rep["nodes"].items() if e["type"] == "EMPTY"]
    rep["lod_triangles"] = [rep["nodes"][n]["triangles"] for n in lods]

    v0 = A[lods[0]]["verts"] * 100.0
    lo, hi = v0.min(0), v0.max(0)
    c = (lo + hi) / 2
    R = float(np.linalg.norm(v0 - c, axis=1).max())
    rep["lod0_bounds_cm"] = {"min": lo.round(5).tolist(), "max": hi.round(5).tolist(),
                             "size": (hi - lo).round(5).tolist(), "centre": c.round(5).tolist(),
                             "sphere_radius_about_box_centre": R,
                             "box_half_diagonal": float(np.linalg.norm(hi - lo) / 2)}
    # Unreal's static-mesh bounds sphere: max(|v - box centre|) over LOD0 render vertices, but
    # Unreal takes min(that, half-diagonal); both reported.
    for key, rad in (("from_sphere", R), ("from_half_diag", float(np.linalg.norm(hi - lo) / 2))):
        rmm = rad * 10.0
        rep.setdefault("rule_screen_sizes", {})[key] = [1.0, 0.10 * rmm / 50.0, 0.035 * rmm / 50.0]
    rep["sidecar_lod_screen_sizes"] = side.get("lod_screen_sizes")

    # hulls
    hulls = {}
    planes = {}
    for h in ucx:
        a = A[h]
        n, d, r = convex_report(a["verts"] * 100.0, a["tv"])
        planes[h] = (n, d)
        r["edge_use_hist"] = a["edge_hist"]
        hulls[h] = r
    rep["hulls"] = hulls
    cont = {}
    for L in lods:
        pts = A[L]["verts"] * 100.0
        per = {h: signed_in(*planes[h], pts) for h in ucx}
        best = np.min(np.stack(list(per.values())), axis=0) if per else None
        rec = {"points": int(len(pts))}
        if best is not None:
            rec["outside_union_count"] = int((best > 1e-4).sum())
            rec["worst_outside_cm"] = float(best.max())
            rec["per_hull_inside_count"] = {h: int((v <= 1e-4).sum()) for h, v in per.items()}
            # slack: how far the hull extends past the mesh along each axis
        cont[L] = rec
    rep["containment"] = cont
    allh = np.concatenate([A[h]["verts"] * 100.0 for h in ucx]) if ucx else None
    if allh is not None:
        rep["hull_union_aabb_vs_lod0_aabb_slack_cm"] = {
            "min_side": (lo - allh.min(0)).round(3).tolist(), "max_side": (allh.max(0) - hi).round(3).tolist()}
        # volume ratio (Monte Carlo): hull union vs mesh AABB
        rng = np.random.default_rng(1)
        box_lo, box_hi = np.minimum(allh.min(0), lo), np.maximum(allh.max(0), hi)
        S = rng.uniform(box_lo, box_hi, size=(400000, 3))
        inside = np.zeros(len(S), bool)
        for h in ucx:
            inside |= signed_in(*planes[h], S) <= 0
        vol_box = float(np.prod(box_hi - box_lo))
        rep["hull_union_volume_cm3_mc"] = float(inside.mean() * vol_box)
        per_h = {}
        for h in ucx:
            ins = signed_in(*planes[h], S) <= 0
            per_h[h] = float(ins.mean() * vol_box)
        rep["hull_volume_cm3_mc"] = per_h

    # head seat: inner surface near the axis.  Straw LOD0 triangles facing down (normal z < 0)
    a0 = A[lods[0]]
    P = a0["tris"] * 100.0
    nrm = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    nl = np.linalg.norm(nrm, axis=1)
    ok = nl > 1e-12
    nz = np.zeros(len(P))
    nz[ok] = nrm[ok, 2] / nl[ok]
    cen = P.mean(1)
    rr = np.linalg.norm(cen[:, :2], axis=1)
    down = nz < -0.2
    prof = []
    for r0 in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 25, 30):
        sel = down & (rr >= r0) & (rr < r0 + 1.0)
        if sel.any():
            prof.append({"r_cm": r0 + 0.5, "inner_z_min_cm": float(cen[sel, 2].min()),
                         "inner_z_max_cm": float(cen[sel, 2].max()), "n": int(sel.sum())})
    rep["inner_surface_profile"] = prof
    sock = side["sockets"][0]
    rep["sidecar_socket"] = sock
    # sphere of radius r (57 cm circumference) resting in the inner cone: fit a line z = z0 + k r to the profile
    pr = np.array([[p["r_cm"], p["inner_z_min_cm"]] for p in prof if 4 <= p["r_cm"] <= 20])
    if len(pr) >= 3:
        k, z0 = np.polyfit(pr[:, 0], pr[:, 1], 1)
        half_angle = math.degrees(math.atan2(1.0, -k)) if k < 0 else float("nan")   # angle from axis
        rh = 57.0 / (2 * math.pi)
        # sphere centred on axis tangent to cone z = z0 + k r (k<0): distance from centre (0,zc) to line = rh
        # line: k r - z + z0 = 0 -> |z0 - zc| / sqrt(1+k^2) = rh -> zc = z0 - rh*sqrt(1+k^2)
        zc = z0 - rh * math.sqrt(1 + k * k)
        rep["head_seat_model"] = {"inner_cone_fit_z0_cm": float(z0), "inner_cone_slope_dz_dr": float(k),
                                  "inner_cone_half_angle_from_axis_deg": half_angle,
                                  "head_radius_cm_from_57cm": rh, "tangent_sphere_centre_z_cm": zc,
                                  "tangent_sphere_top_z_cm": zc + rh,
                                  "contact_radius_cm": rh * (-k) / math.sqrt(1 + k * k) if k < 0 else None,
                                  "socket_z_cm": sock["location_cm"][2],
                                  "socket_minus_sphere_top_cm": sock["location_cm"][2] - (zc + rh)}
    rep["fbx_sha256_after"] = sha256(FBX)
    (HERE / "truth_fbx.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("BHV_TRUTH_FBX_DONE")


def run_blend():
    rep = {"mode": "blend", "blend": bpy.data.filepath, "blend_sha256": sha256(bpy.data.filepath), "objects": {}}
    dg = bpy.context.evaluated_depsgraph_get()
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        e = {"type": obj.type, "parent": obj.parent.name if obj.parent else None,
             "collections": [c.name for c in obj.users_collection]}
        if obj.type == "MESH":
            ev = obj.evaluated_get(dg)
            me = ev.to_mesh()
            me.calc_loop_triangles()
            e["evaluated_triangles"] = len(me.loop_triangles)
            e["evaluated_vertices"] = len(me.vertices)
            e["materials"] = [s.material.name if s.material else None for s in obj.material_slots]
            ev.to_mesh_clear()
        if obj.type == "EMPTY":
            e["matrix_world"] = [[round(float(v), 6) for v in row] for row in obj.matrix_world]
            e["empty_display_type"] = obj.empty_display_type
        rep["objects"][obj.name] = e
    (HERE / "truth_blend.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("BHV_TRUTH_BLEND_DONE")


if MODE == "blend":
    run_blend()
else:
    run_fbx()
