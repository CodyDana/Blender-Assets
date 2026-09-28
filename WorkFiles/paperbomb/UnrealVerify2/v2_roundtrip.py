#!/usr/bin/env python
"""Measure what Unreal ACTUALLY built, by re-importing Unreal's own FBX export.

Answers the three things the engine's Python API will not tell you on 5.8.2:
  * does the built render data really carry a second UV channel (the lightmap), is it
    inside 0-1, and do its charts overlap?
  * is the convex collision Unreal stored still convex, and does it still contain LOD0?
  * did the 8.05 mm corner chamfer survive the import, on every LOD?

Compares everything against blender_truth.json, which was measured from the SHIPPED FBX
before Unreal ever saw it.
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealVerify2"
RT = HERE / "roundtrip.fbx"
OUT = HERE / "roundtrip_analysis.json"
TRUTH = json.loads((HERE / "blender_truth.json").read_text(encoding="utf-8"))

ATLAS, PPMM = 2048.0, 12.923
MM_PER_UV = ATLAS / PPMM


def verts_tris(obj, to_mm=True):
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    if to_mm:
        co = co * 1000.0
    tris = np.array([list(t.vertices) for t in me.loop_triangles], np.int64)
    return co, tris


def loop_uv(obj, layer_index):
    me = obj.data
    me.calc_loop_triangles()
    lay = me.uv_layers[layer_index]
    uv = np.empty(len(me.loops) * 2, np.float64)
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    tri_uv = np.array([[uv[l] for l in t.loops] for t in me.loop_triangles], np.float64)
    return uv, tri_uv


def raster_overlap(tri_uv, res):
    """Count texels covered by more than one triangle at `res` x `res`."""
    count = np.zeros((res, res), np.int32)
    for tri in tri_uv:
        u0 = np.clip(np.floor(tri[:, 0].min() * res), 0, res - 1).astype(int)
        u1 = np.clip(np.ceil(tri[:, 0].max() * res), 0, res).astype(int)
        v0 = np.clip(np.floor(tri[:, 1].min() * res), 0, res - 1).astype(int)
        v1 = np.clip(np.ceil(tri[:, 1].max() * res), 0, res).astype(int)
        if u1 <= u0 or v1 <= v0:
            continue
        us = (np.arange(u0, u1) + 0.5) / res
        vs = (np.arange(v0, v1) + 0.5) / res
        U, V = np.meshgrid(us, vs)
        a, b, c = tri[0], tri[1], tri[2]
        d = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(d) < 1e-14:
            continue
        w0 = ((b[1] - c[1]) * (U - c[0]) + (c[0] - b[0]) * (V - c[1])) / d
        w1 = ((c[1] - a[1]) * (U - c[0]) + (a[0] - c[0]) * (V - c[1])) / d
        w2 = 1.0 - w0 - w1
        hit = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        count[v0:v1, u0:u1] += hit.astype(np.int32)
    covered = int((count > 0).sum())
    over = int((count > 1).sum())
    return {"resolution": res, "texels_covered": covered, "texels_multi_triangle": over,
            "fraction_multi": round(over / max(1, covered), 6),
            "max_triangles_per_texel": int(count.max()),
            "coverage_of_sheet": round(covered / float(res * res), 6)}


def exact_uv_overlap(tri_uv, sample_res=4096):
    """A finer raster: at 4096 a genuine chart overlap survives, a shared edge does not."""
    return raster_overlap(tri_uv, sample_res)


def planes_of(verts, tris, tol=1e-4):
    out = []
    for a, b, c in tris:
        n = np.cross(verts[b] - verts[a], verts[c] - verts[a])
        L = np.linalg.norm(n)
        if L < 1e-9:
            continue
        n = n / L
        d = float(np.dot(n, verts[a]))
        for pn, pd in out:
            if np.dot(pn, n) > 1 - 1e-6 and abs(pd - d) < tol:
                break
        else:
            out.append((n, d))
    return out


def hull2d(pts):
    p = sorted({(round(float(x), 7), round(float(y), 7)) for x, y in pts})
    if len(p) < 3:
        return p

    def half(seq):
        o = []
        for q in seq:
            while len(o) >= 2:
                (ax, ay), (bx, by) = o[-2], o[-1]
                if (bx - ax) * (q[1] - ay) - (by - ay) * (q[0] - ax) <= 1e-9:
                    o.pop()
                else:
                    break
            o.append(q)
        return o
    return half(p)[:-1] + half(p[::-1])[:-1]


def chamfer_from_uv(obj, uv_index=0):
    """8.05 mm corner clip, read off the card's own texture island (paper space)."""
    me = obj.data
    me.calc_loop_triangles()
    uv = np.empty(len(me.loops) * 2, np.float64)
    me.uv_layers[uv_index].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2) * MM_PER_UV
    # the atlas plan: front island u 0.007812-0.449517, back 0.465332-0.907036
    front = uv[(uv[:, 0] >= 0.007 * MM_PER_UV) & (uv[:, 0] <= 0.4500 * MM_PER_UV)]
    if len(front) < 8:
        return {"error": "front island empty"}
    front = front - front.min(axis=0)
    h = hull2d(front)
    xs = [q[0] for q in h]; ys = [q[1] for q in h]
    res = {"island_size_mm": [round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4)],
           "corners": {}}
    n = len(h)
    cx = (min(xs) + max(xs)) / 2.0; cy = (min(ys) + max(ys)) / 2.0
    for i in range(n):
        a = np.array(h[i]); b = np.array(h[(i + 1) % n])
        v = b - a
        L = float(np.hypot(*v))
        if L < 0.3:
            continue
        ang = math.degrees(math.atan2(abs(v[1]), abs(v[0])))
        if not (20 < ang < 70):
            continue
        m = (a + b) / 2.0
        key = ("x+" if m[0] > cx else "x-") + ("y+" if m[1] > cy else "y-")
        res["corners"][key] = {"leg_x_mm": round(abs(float(v[0])), 4),
                               "leg_y_mm": round(abs(float(v[1])), 4),
                               "chord_mm": round(L, 4), "angle_deg": round(ang, 4)}
    return res


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(RT), automatic_bone_orientation=True)

    rep = {"roundtrip_fbx": str(RT), "bytes": RT.stat().st_size,
           "objects": sorted(o.name for o in bpy.data.objects)}

    meshes = {o.name: o for o in bpy.data.objects if o.type == "MESH"}
    rep["mesh_names"] = sorted(meshes)

    # Unreal names the exported LODs after the asset; find them in LOD order
    lod_objs = []
    for nm in sorted(meshes):
        if nm.upper().startswith("UCX"):
            continue
        lod_objs.append(nm)
    rep["lod_object_order"] = lod_objs

    per = {}
    for nm, obj in meshes.items():
        v, t = verts_tris(obj)
        me = obj.data
        rec = {
            "triangles": int(len(t)),
            "vertices": int(len(v)),
            "uv_layers": [l.name for l in me.uv_layers],
            "uv_layer_count": len(me.uv_layers),
            "extents_mm": {"min": [round(float(x), 4) for x in v.min(axis=0)],
                           "max": [round(float(x), 4) for x in v.max(axis=0)],
                           "size": [round(float(x), 4) for x in np.ptp(v, axis=0)]},
            "materials": [m.name if m else None for m in me.materials],
        }
        for li in range(len(me.uv_layers)):
            uv, tri_uv = loop_uv(obj, li)
            rec[f"uv{li}_min"] = [round(float(uv[:, 0].min()), 6), round(float(uv[:, 1].min()), 6)]
            rec[f"uv{li}_max"] = [round(float(uv[:, 0].max()), 6), round(float(uv[:, 1].max()), 6)]
            rec[f"uv{li}_inside_0_1"] = bool(uv.min() >= -1e-6 and uv.max() <= 1.0 + 1e-6)
            if li == 1:
                rec["uv1_overlap_at_64"] = raster_overlap(tri_uv, 64)
                rec["uv1_overlap_at_512"] = raster_overlap(tri_uv, 512)
                rec["uv1_overlap_at_2048"] = exact_uv_overlap(tri_uv, 2048)
        if not nm.upper().startswith("UCX"):
            rec["chamfer_paper_space"] = chamfer_from_uv(obj, 0)
        per[nm] = rec
    rep["per_object"] = per

    # ---- collision, from Unreal's own re-export --------------------------------------
    ucx = [n for n in meshes if n.upper().startswith("UCX")]
    coll = {"ucx_objects": ucx}
    if ucx:
        hv, ht = verts_tris(meshes[ucx[0]])
        pl = planes_of(hv, ht)
        coll["hull_vertices"] = int(len(hv))
        coll["hull_triangles"] = int(len(ht))
        coll["distinct_planes"] = len(pl)
        coll["self_max_outside_mm"] = round(float(max((hv @ n - d).max() for n, d in pl)), 9)
        coll["is_convex"] = coll["self_max_outside_mm"] < 1e-3
        for nm in lod_objs:
            lv = verts_tris(meshes[nm])[0]
            worst = float(max((lv @ n - d).max() for n, d in pl))
            coll[f"{nm}_max_outside_mm"] = round(worst, 9)
            coll[f"{nm}_contained"] = worst < 1e-3
        h2 = hull2d(hv[:, :2])
        xs = [q[0] for q in h2]; ys = [q[1] for q in h2]
        cx = (min(xs) + max(xs)) / 2; cy = (min(ys) + max(ys)) / 2
        legs = {}
        for i in range(len(h2)):
            a = np.array(h2[i]); b = np.array(h2[(i + 1) % len(h2)])
            v = b - a
            L = float(np.hypot(*v))
            if L < 0.3:
                continue
            ang = math.degrees(math.atan2(abs(v[1]), abs(v[0])))
            if not (20 < ang < 70):
                continue
            m = (a + b) / 2
            key = ("x+" if m[0] > cx else "x-") + ("y+" if m[1] > cy else "y-")
            legs[key] = {"leg_mm": round(abs(float(v[0])), 4), "angle_deg": round(ang, 3)}
        coll["plan_diagonal_edges"] = legs
        coll["plan_hull_points"] = len(h2)
        coll["plan_size_mm"] = [round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4)]
    rep["collision"] = coll

    # ---- agreement with the SHIPPED fbx, measured before Unreal saw it ----------------
    ship = {f"SM_PaperBomb_LOD{i}": TRUTH["nodes"][f"SM_PaperBomb_LOD{i}"]["triangles"]
            for i in range(3)}
    rt_tris = {n: per[n]["triangles"] for n in lod_objs}
    rep["shipped_lod_triangles"] = ship
    rep["roundtrip_lod_triangles"] = rt_tris
    rep["triangle_sets_match"] = sorted(ship.values()) == sorted(rt_tris.values())

    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("[roundtrip] ->", OUT)
    print(json.dumps({k: rep[k] for k in ("objects", "triangle_sets_match",
                                          "shipped_lod_triangles", "roundtrip_lod_triangles")},
                     indent=1))
    print("collision:", json.dumps(coll, indent=1))
    for n in sorted(per):
        p = per[n]
        print(f"  {n:34s} tri={p['triangles']:5d} uv={p['uv_layer_count']} "
              f"{p.get('uv1_min')} {p.get('uv1_max')}")


main()
