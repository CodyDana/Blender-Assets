"""Measure Unreal's re-export (pass B) against this verifier's truth of the shipped FBX.

    blender.exe -b --factory-startup --python bhv_roundtrip.py

* LOD triangles and positions (two-sided) against the shipped LODs, triangle identity
* the collision hulls: count (connected components of every UCX object), convexity, vertices
  against the shipped UCX hulls, containment of shipped and Unreal LODs by the hull UNION
* UV1 (the lightmap UV Unreal generated) per LOD: range and overlapping texel centres at 1024/2048
"""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\blackhat\UnrealVerify_indep_v1")
RT = HERE / "bhv_unreal_roundtrip.fbx"
TRUTH = json.loads((HERE / "truth_fbx.json").read_text(encoding="utf-8"))


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def mesh_arrays(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    me.calc_loop_triangles()
    mw = np.array(obj.matrix_world, dtype=np.float64)
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    co = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3] * 100.0
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
    out = {"verts": co, "tv": tv, "uvs": uvs, "tri_mat": tm,
           "mats": [s.material.name if s.material else None for s in obj.material_slots]}
    ev.to_mesh_clear()
    return out


def nn(a, b, chunk=256):
    idx = np.empty(len(a), np.int64)
    dist = np.empty(len(a))
    for i in range(0, len(a), chunk):
        d = ((a[i:i + chunk, None, :] - b[None, :, :]) ** 2).sum(-1)
        idx[i:i + chunk] = d.argmin(1)
        dist[i:i + chunk] = np.sqrt(d.min(1))
    return idx, dist


def two_sided(a, b):
    return float(max(nn(a, b)[1].max(), nn(b, a)[1].max()))


def components(tv, n):
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b, c in tv:
        for x, y in ((a, b), (b, c)):
            rx, ry = find(int(x)), find(int(y))
            if rx != ry:
                parent[rx] = ry
    roots = np.array([find(i) for i in range(n)])
    comps = []
    for r in sorted(set(roots.tolist())):
        vids = np.where(roots == r)[0]
        tsel = np.isin(tv[:, 0], vids)
        comps.append((vids, tv[tsel]))
    return comps


def planes_of(verts, tv):
    P = verts[tv]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    L = np.linalg.norm(n, axis=1)
    k = L > 1e-12
    n = n[k] / L[k, None]
    d = (n * P[k, 0]).sum(1)
    # orient every face plane away from the vertex centroid (winding-independent: Unreal's
    # collision export may reverse winding); the record keeps how many faces were flipped
    c = verts.mean(0)
    flip = (n @ c - d) > 0
    n[flip] *= -1
    d[flip] *= -1
    planes_of.flipped = int(flip.sum())
    return n, d


def outside(pl, pts):
    n, d = pl
    return (pts @ n.T - d).max(1)


def raster_overlap(uv_tris, res):
    cov = np.zeros((res, res), np.int32)
    T = uv_tris * res
    oor = int(((uv_tris < 0) | (uv_tris > 1)).any(axis=(1, 2)).sum())
    for tri in T:
        a, b, c = tri
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(area) < 1e-12:
            continue
        if area < 0:
            b, c = c, b
        x0 = max(int(np.floor(min(a[0], b[0], c[0]) - 0.5)), 0)
        x1 = min(int(np.ceil(max(a[0], b[0], c[0]) - 0.5)), res - 1)
        y0 = max(int(np.floor(min(a[1], b[1], c[1]) - 0.5)), 0)
        y1 = min(int(np.ceil(max(a[1], b[1], c[1]) - 0.5)), res - 1)
        if x1 < x0 or y1 < y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)

        def E(p, q):
            return (q[0] - p[0]) * (Y - p[1]) - (q[1] - p[1]) * (X - p[0])
        inside = (E(a, b) > 1e-7) & (E(b, c) > 1e-7) & (E(c, a) > 1e-7)
        cov[y0:y1 + 1, x0:x1 + 1] += inside
    return {"res": res, "covered_texels": int((cov >= 1).sum()), "overlap_texels": int((cov >= 2).sum()),
            "max_coverage": int(cov.max()), "triangles_outside_0_1": oor}


MAPS = {"identity": np.diag([1.0, 1.0, 1.0]), "flipY": np.diag([1.0, -1.0, 1.0]),
        "flipX": np.diag([-1.0, 1.0, 1.0]), "flipXY": np.diag([-1.0, -1.0, 1.0])}


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(RT))
    rep = {"roundtrip_sha256": sha256(RT), "objects": {}}
    A = {}
    for obj in sorted(bpy.data.objects, key=lambda o: o.name):
        e = {"type": obj.type, "parent": obj.parent.name if obj.parent else None}
        if obj.type == "MESH":
            a = mesh_arrays(obj)
            A[obj.name] = a
            e.update({"triangles": int(len(a["tv"])), "vertices": int(len(a["verts"])),
                      "uv_layers": list(a["uvs"].keys()), "materials": a["mats"]})
        rep["objects"][obj.name] = e
    ucx = [n for n in A if n.upper().startswith("UCX")]
    lods = sorted(n for n in A if n not in ucx)
    rep["roundtrip_lod_objects"] = lods
    rep["roundtrip_ucx_objects"] = ucx

    tv_ = {i: np.load(HERE / f"truth_SM_BlackHat_LOD{i}_tv.npy") for i in range(3)}
    tvx = {i: np.load(HERE / f"truth_SM_BlackHat_LOD{i}_verts_cm.npy") for i in range(3)}
    hull_truth = {h: (np.load(HERE / f"truth_{h}_verts_cm.npy"), np.load(HERE / f"truth_{h}_tv.npy"))
                  for h in TRUTH["ucx_names"]}

    by_idx = {}
    for n in lods:
        for i in range(3):
            if n.endswith(f"LOD{i}"):
                by_idx[i] = n
    if len(by_idx) < 3:
        for n in lods:
            if n in by_idx.values():
                continue
            i = int(np.argmin([abs(len(A[n]["tv"]) - len(tv_[i])) for i in range(3)]))
            by_idx.setdefault(i, n)
    rt0 = A[by_idx[0]]["verts"]
    fits = {k: two_sided(rt0[::7] @ M.T, tvx[0][::7]) for k, M in MAPS.items()}   # coarse pick
    best = min(fits, key=fits.get)
    M = MAPS[best]
    rep["axis_map_fit_coarse_cm"] = fits
    rep["axis_map_used"] = best

    per = {}
    for i in range(3):
        n = by_idx.get(i)
        if n is None:
            per[f"LOD{i}"] = {"error": "missing"}
            continue
        a = A[n]
        v = a["verts"] @ M.T
        tris = v[a["tv"]]
        idx, dist = nn(tris.reshape(-1, 3), tvx[i])
        kr = set(tuple(sorted(t)) for t in idx.reshape(-1, 3).tolist())
        kt = set(tuple(sorted(t)) for t in tv_[i].tolist())
        rec = {"object": n, "unreal_triangles": int(len(a["tv"])), "shipped_triangles": int(len(tv_[i])),
               "positions_two_sided_cm": two_sided(v, tvx[i]), "corner_snap_max_cm": float(dist.max()),
               "shipped_triangles_absent_in_unreal": int(len(kt - kr)),
               "unreal_triangles_absent_in_shipped": int(len(kr - kt)),
               "uv_layers": list(a["uvs"].keys()), "materials": a["mats"],
               "triangles_per_material_index": {str(k): int((a["tri_mat"] == k).sum()) for k in sorted(set(a["tri_mat"].tolist()))}}
        layers = list(a["uvs"].keys())
        if len(layers) >= 2:
            uv1 = a["uvs"][layers[1]]
            rec["uv1_layer"] = layers[1]
            rec["uv1_range"] = [uv1.reshape(-1, 2).min(0).tolist(), uv1.reshape(-1, 2).max(0).tolist()]
            rec["uv1_overlap_1024"] = raster_overlap(uv1, 1024)
            rec["uv1_overlap_2048"] = raster_overlap(uv1, 2048)
            uv0 = a["uvs"][layers[0]]
            rec["uv0_range"] = [uv0.reshape(-1, 2).min(0).tolist(), uv0.reshape(-1, 2).max(0).tolist()]
        else:
            rec["uv1_error"] = f"only {len(layers)} UV layer(s)"
        per[f"LOD{i}"] = rec
    rep["lods"] = per

    hulls = []
    for h in ucx:
        a = A[h]
        v = a["verts"] @ M.T
        for vids, tvc in components(a["tv"], len(v)):
            remap = -np.ones(len(v), np.int64)
            remap[vids] = np.arange(len(vids))
            hv, ht = v[vids], remap[tvc]
            pl = planes_of(hv, ht)
            flipped = planes_of.flipped
            conv = float((hv @ pl[0].T - pl[1]).max())
            best_t = min(hull_truth, key=lambda k: two_sided(hv, hull_truth[k][0]))
            hulls.append({"object": h, "vertices": int(len(hv)), "triangles": int(len(ht)), "faces_reoriented": flipped,
                          "max_vertex_in_front_of_own_face_cm": conv, "convex": bool(conv <= 1e-3),
                          "matches_shipped": best_t,
                          "vertices_two_sided_vs_shipped_cm": two_sided(hv, hull_truth[best_t][0]),
                          "aabb_min": hv.min(0).round(4).tolist(), "aabb_max": hv.max(0).round(4).tolist(),
                          "_pl": pl})
    rep["hull_count"] = len(hulls)
    cont = {}
    for i in range(3):
        for label, pts in (("shipped", tvx[i]), ("unreal", A[by_idx[i]]["verts"] @ M.T if i in by_idx else None)):
            if pts is None:
                continue
            worst = np.min(np.stack([outside(h["_pl"], pts) for h in hulls]), axis=0)
            cont[f"LOD{i}_{label}"] = {"points": int(len(pts)), "outside_union": int((worst > 1e-3).sum()),
                                       "worst_signed_cm": float(worst.max())}
    rep["hull_union_contains"] = cont
    # engine LOD0 description positions (pass B, Unreal space) vs shipped mapped to Unreal (flip Y)
    try:
        pb = json.loads((HERE / "passB.json").read_text(encoding="utf-8"))
        pos = np.array(pb["lod0_description_positions_cm"], np.float64)
        ue_truth = tvx[0] * np.array([1.0, -1.0, 1.0])
        rep["engine_lod0_description_vs_shipped_flipY_two_sided_cm"] = two_sided(pos, ue_truth)
        ue_hull_pl = []
        for h in hulls:
            n, d = h["_pl"]
            ue_hull_pl.append((n * np.array([1.0, -1.0, 1.0]), d))
        worst = np.min(np.stack([outside(p, pos) for p in ue_hull_pl]), axis=0)
        rep["engine_lod0_description_in_hull_union_ue_space"] = {
            "points": int(len(pos)), "outside": int((worst > 1e-3).sum()), "worst_signed_cm": float(worst.max())}
    except Exception as exc:                                     # noqa: BLE001
        rep["engine_space_error"] = f"{type(exc).__name__}: {exc}"
    for h in hulls:
        h.pop("_pl")
    rep["hulls"] = hulls
    (HERE / "roundtrip.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("BHV_ROUNDTRIP_DONE")


main()
