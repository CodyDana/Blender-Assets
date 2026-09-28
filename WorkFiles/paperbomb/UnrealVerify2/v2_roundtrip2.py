#!/usr/bin/env python
"""Round-trip part 2, with the unit scale fixed and the UV1 overlap decided exactly.

Unreal's FBX export is in centimetres and Blender's importer does not rescale it, so the
imported coordinates are 100x the metre-based numbers.  Everything here divides by 100
and then by 1000 -> millimetres, and the result is checked against the plan size the
shipped FBX actually has.

The UV1 overlap test is the strict one: exact polygon-clipping area of every pair of
triangles that do NOT share a vertex.  A shared edge or a shared vertex can put two
triangles in one texel without any lightmap bleeding; only a genuine area overlap can.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealVerify2"
RT = HERE / "roundtrip.fbx"
OUT = HERE / "roundtrip2.json"
TRUTH = json.loads((HERE / "blender_truth.json").read_text(encoding="utf-8"))
SCALE_MM = 1000.0 / 100.0          # Blender units -> mm, undoing Unreal's cm export


def verts_tris_mm(obj):
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) * SCALE_MM
    tris = np.array([list(t.vertices) for t in me.loop_triangles], np.int64)
    return co, tris


def planes_of(v, t, tol=1e-4):
    out = []
    for a, b, c in t:
        n = np.cross(v[b] - v[a], v[c] - v[a])
        L = np.linalg.norm(n)
        if L < 1e-9:
            continue
        n /= L
        d = float(np.dot(n, v[a]))
        for pn, pd in out:
            if np.dot(pn, n) > 1 - 1e-6 and abs(pd - d) < tol:
                break
        else:
            out.append((n, d))
    return out


def clip_poly(poly, a, b):
    """Sutherland-Hodgman half-plane clip: keep the side left of a->b."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        sp = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        sq = (b[0] - a[0]) * (q[1] - a[1]) - (b[1] - a[1]) * (q[0] - a[0])
        if sp >= 0:
            out.append(p)
        if (sp > 0 and sq < 0) or (sp < 0 and sq > 0):
            t = sp / (sp - sq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return out


def tri_area(p):
    a = 0.0
    for i in range(len(p)):
        x1, y1 = p[i]
        x2, y2 = p[(i + 1) % len(p)]
        a += x1 * y2 - x2 * y1
    return abs(a) * 0.5


def overlap_area(t1, t2):
    if tri_area(t1) < 1e-16 or tri_area(t2) < 1e-16:
        return 0.0
    # orient t2 CCW so the clip keeps the interior
    if (t2[1][0] - t2[0][0]) * (t2[2][1] - t2[0][1]) - \
       (t2[1][1] - t2[0][1]) * (t2[2][0] - t2[0][0]) < 0:
        t2 = [t2[0], t2[2], t2[1]]
    poly = list(t1)
    for i in range(3):
        poly = clip_poly(poly, t2[i], t2[(i + 1) % 3])
        if len(poly) < 3:
            return 0.0
    return tri_area(poly)


def strict_uv_overlap(obj, layer_index):
    """Exact overlap area between triangles that share NO vertex, in UV units."""
    me = obj.data
    me.calc_loop_triangles()
    lay = me.uv_layers[layer_index]
    uv = np.empty(len(me.loops) * 2, np.float64)
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    tris = []
    for t in me.loop_triangles:
        tris.append((tuple(int(i) for i in t.vertices),
                     [tuple(uv[l]) for l in t.loops]))
    n = len(tris)
    total_area = sum(tri_area(t[1]) for t in tris)
    # bucket by UV grid so the pair loop stays cheap
    cell = 1.0 / 128.0
    buckets = {}
    boxes = []
    for i, (vids, p) in enumerate(tris):
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
        for gx in range(int(min(xs) / cell), int(max(xs) / cell) + 1):
            for gy in range(int(min(ys) / cell), int(max(ys) / cell) + 1):
                buckets.setdefault((gx, gy), []).append(i)
    worst = 0.0
    total_overlap = 0.0
    pairs = 0
    seen = set()
    for key, idxs in buckets.items():
        for ai in range(len(idxs)):
            for bi in range(ai + 1, len(idxs)):
                i, j = idxs[ai], idxs[bi]
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                if set(tris[i][0]) & set(tris[j][0]):
                    continue                        # adjacent: a shared edge is not overlap
                b1, b2 = boxes[i], boxes[j]
                if b1[2] <= b2[0] or b2[2] <= b1[0] or b1[3] <= b2[1] or b2[3] <= b1[1]:
                    continue
                a = overlap_area(tris[i][1], tris[j][1])
                if a > 1e-12:
                    pairs += 1
                    total_overlap += a
                    worst = max(worst, a)
    return {"triangles": n,
            "uv_area_total": round(total_area, 8),
            "overlapping_pairs_sharing_no_vertex": pairs,
            "overlap_area_uv": round(total_overlap, 10),
            "overlap_fraction_of_chart_area": round(total_overlap / max(total_area, 1e-12), 9),
            "worst_single_pair_area_uv": round(worst, 12)}


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(RT), automatic_bone_orientation=True)
    meshes = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    lods = sorted(n for n in meshes if not n.upper().startswith("UCX"))
    ucx = [n for n in meshes if n.upper().startswith("UCX")]

    rep = {"scale_mm_per_blender_unit": SCALE_MM}
    sizes = {}
    for n in lods + ucx:
        v, t = verts_tris_mm(meshes[n])
        sizes[n] = {"size_mm": [round(float(x), 4) for x in np.ptp(v, axis=0)],
                    "min_mm": [round(float(x), 4) for x in v.min(axis=0)],
                    "max_mm": [round(float(x), 4) for x in v.max(axis=0)],
                    "triangles": int(len(t)), "vertices": int(len(v))}
    rep["sizes_mm"] = sizes
    shipped = {k: TRUTH["nodes"][k]["extents_mm"]["size"] for k in TRUTH["nodes"]
               if TRUTH["nodes"][k]["type"] == "MESH"}
    rep["shipped_sizes_mm"] = shipped
    rep["size_deltas_mm"] = {
        n: [round(sizes[n]["size_mm"][i] - shipped.get(n if n in shipped else n + "_00",
                                                       [0, 0, 0])[i], 5) for i in range(3)]
        for n in sizes if (n in shipped or (n + "_00") in shipped)}

    # ---- collision ------------------------------------------------------------------
    coll = {}
    if ucx:
        hv, ht = verts_tris_mm(meshes[ucx[0]])
        pl = planes_of(hv, ht)
        coll["name"] = ucx[0]
        coll["vertices"] = int(len(hv))
        coll["triangles"] = int(len(ht))
        coll["distinct_planes"] = len(pl)
        coll["self_max_outside_mm"] = round(float(max((hv @ n - d).max() for n, d in pl)), 9)
        coll["is_convex"] = coll["self_max_outside_mm"] < 1e-3
        for n in lods:
            lv = verts_tris_mm(meshes[n])[0]
            w = float(max((lv @ nn - dd).max() for nn, dd in pl))
            coll[f"{n}_max_outside_mm"] = round(w, 9)
            coll[f"{n}_contained"] = w < 1e-3
        # does the hull still hug the 8.05 mm chamfer?  the diagonal supporting planes
        # should be tangent to LOD0, i.e. clearance ~ 0
        l0 = verts_tris_mm(meshes[lods[0]])[0]
        diag = []
        for nn, dd in pl:
            if abs(nn[2]) > 0.2:
                continue
            ang = math.degrees(math.atan2(abs(nn[1]), abs(nn[0])))
            sup = float((l0 @ nn).max())
            diag.append({"normal": [round(float(x), 4) for x in nn],
                         "plan_angle_deg": round(ang, 3),
                         "clearance_over_lod0_mm": round(dd - sup, 7)})
        coll["side_planes"] = sorted(diag, key=lambda r: r["plan_angle_deg"])
        coll["max_side_clearance_mm"] = round(max(r["clearance_over_lod0_mm"] for r in diag), 7)
    rep["collision"] = coll

    # ---- strict lightmap-UV overlap --------------------------------------------------
    ov = {}
    for n in lods:
        me = meshes[n].data
        names = [l.name for l in me.uv_layers]
        rec = {"uv_layers": names}
        for li, nm in enumerate(names):
            uv = np.empty(len(me.loops) * 2, np.float64)
            me.uv_layers[li].data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)
            rec[nm] = {"min": [round(float(uv[:, 0].min()), 6), round(float(uv[:, 1].min()), 6)],
                       "max": [round(float(uv[:, 0].max()), 6), round(float(uv[:, 1].max()), 6)],
                       "inside_0_1": bool(uv.min() >= -1e-6 and uv.max() <= 1 + 1e-6)}
        if len(names) > 1:
            rec["lightmap_strict_overlap"] = strict_uv_overlap(meshes[n], 1)
            rec["uv0_strict_overlap"] = strict_uv_overlap(meshes[n], 0)
        ov[n] = rec
    rep["uv"] = ov

    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("[roundtrip2] ->", OUT)
    print(json.dumps(rep, indent=1)[:6000])


main()
