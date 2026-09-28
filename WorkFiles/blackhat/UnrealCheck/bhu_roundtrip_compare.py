#!/usr/bin/env python
"""Compare Unreal's own FBX export of the saved asset with the FBX that shipped (Blender).

    blender -b --factory-startup --python bhu_roundtrip_compare.py

    lods      per-LOD triangle counts and two-sided nearest-vertex distance (cm)
    missing   shipped triangles with no counterpart in Unreal's export, by corner
              positions (what Unreal's build dropped, and why: their shortest edge / area)
    hull      the hull's vertices round trip, and whether the engine's hull CONTAINS every
              LOD0 vertex (planes of the convex hull of Unreal's exported hull points)
"""
import json
import math
from pathlib import Path

import bmesh
import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "blackhat" / "UnrealCheck"
SHIPPED = PROJ / "Exports" / "BlackHat" / "SM_BlackHat.fbx"
UNREAL = HERE / "unreal_roundtrip.fbx"
OUT = HERE / "roundtrip_compare.json"
REPORT = json.loads((PROJ / "WorkFiles" / "blackhat" / "blackhat_report.json").read_text(encoding="utf-8"))


def load(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        me = obj.data
        me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        m = np.array(obj.matrix_world)
        co = (co @ m[:3, :3].T + m[:3, 3]) * 100.0
        tris = np.array([t.vertices[:] for t in me.loop_triangles], np.int64).reshape(-1, 3)
        mats = np.array([t.material_index for t in me.loop_triangles], np.int64)
        slots = [(s.material.name if s.material else "") for s in obj.material_slots]
        out[obj.name] = {"co": co, "tris": tris, "mat": mats, "slots": slots}
    return out


def classify(name):
    n = name.upper()
    if n.startswith("UCX"):
        return "hull" + n[-2:]
    for i in range(3):
        if n.endswith(f"LOD{i}") or f"_LOD{i}" in n:
            return f"LOD{i}"
    return name


def nn_max(a, b, cell=0.05):
    """max over a of the distance to the nearest point of b (grid hash, cm)."""
    from collections import defaultdict
    grid = defaultdict(list)
    for i, p in enumerate(b):
        grid[tuple(np.floor(p / cell).astype(int))].append(i)
    worst = 0.0
    for p in a:
        k = np.floor(p / cell).astype(int)
        best = 1e9
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                        d = float(np.linalg.norm(b[j] - p))
                        best = min(best, d)
        if best == 1e9:
            best = float(np.min(np.linalg.norm(b - p, axis=1)))
        worst = max(worst, best)
    return worst


def vertex_map(a, b, tol=1e-4, cell=0.01):
    """index in b of the vertex at each vertex of a (within tol cm), -1 if none"""
    from collections import defaultdict
    grid = defaultdict(list)
    for j, p in enumerate(b):
        grid[tuple(np.floor(p / cell).astype(int))].append(j)
    out = -np.ones(len(a), np.int64)
    for i, p in enumerate(a):
        k = np.floor(p / cell).astype(int)
        best, bj = tol, -1
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in grid.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                        d = float(np.linalg.norm(b[j] - p))
                        if d <= best:
                            best, bj = d, j
        out[i] = bj
    return out


def absent_triangles(a, b):
    """shipped triangles (a) with no triangle of b on the same three vertices"""
    m = vertex_map(a["co"], b["co"])
    # b's vertices can be split copies (UV / normal seams): compare by POSITION class
    cls = vertex_map(b["co"], b["co"])            # first copy of each position
    have = {tuple(sorted(cls[t])) for t in b["tris"]}
    out = []
    for t in a["tris"]:
        mt = m[t]
        if (mt < 0).any() or tuple(sorted(cls[mt])) not in have:
            out.append(t)
    return out


def main():
    shipped = {classify(k): v for k, v in load(SHIPPED).items()}
    unreal = {}
    for k, v in load(UNREAL).items():
        c = classify(k)
        if c in unreal:          # Unreal may split a LOD into pieces: merge
            n = len(unreal[c]["co"])
            unreal[c] = {"co": np.concatenate([unreal[c]["co"], v["co"]]),
                         "tris": np.concatenate([unreal[c]["tris"], v["tris"] + n])}
        else:
            unreal[c] = v
    report = {"shipped_nodes": sorted(shipped), "unreal_nodes": sorted(unreal), "lods": {}}
    for lod in ("LOD0", "LOD1", "LOD2"):
        a, b = shipped.get(lod), unreal.get(lod)
        if a is None or b is None:
            report["lods"][lod] = {"missing": True}
            continue
        entry = {"shipped_triangles": int(len(a["tris"])), "unreal_triangles": int(len(b["tris"])),
                 "positions_two_sided_cm": round(max(nn_max(a["co"], b["co"]), nn_max(b["co"], a["co"])), 6)}
        missing = absent_triangles(a, b)
        info = []
        for t in missing[:20]:
            p = a["co"][t] * 10.0                          # mm
            e = [float(np.linalg.norm(p[i] - p[(i + 1) % 3])) for i in range(3)]
            area = 0.5 * float(np.linalg.norm(np.cross(p[1] - p[0], p[2] - p[0])))
            info.append({"shortest_edge_um": round(min(e) * 1000, 4), "longest_edge_mm": round(max(e), 4),
                         "area_um2": round(area * 1e6, 4), "centre_mm": [round(float(x), 3) for x in p.mean(axis=0)]})
        entry["shipped_triangles_absent_in_unreal"] = len(missing)
        entry["absent_detail"] = info
        report["lods"][lod] = entry
    def components(d):
        """split hull nodes into connected pieces (Unreal writes both hulls into ONE UCX node)"""
        out = {}
        for k, h in d.items():
            n = len(h["co"])
            par = list(range(n))

            def f(x):
                while par[x] != x:
                    par[x] = par[par[x]]
                    x = par[x]
                return x
            for t in h["tris"]:
                a0 = f(int(t[0]))
                for v in t[1:]:
                    par[f(int(v))] = a0
            roots = sorted({f(i) for i in range(n)})
            for ci, r in enumerate(roots):
                idx = [i for i in range(n) if f(i) == r]
                out[f"{k}_{ci}"] = {"co": h["co"][idx], "tris": np.zeros((0, 3), np.int64)}
        return out
    hs = components({k: v for k, v in shipped.items() if k.startswith("hull")})
    hu = components({k: v for k, v in unreal.items() if k.startswith("hull")})
    report["hull_nodes"] = {"shipped": sorted(hs), "unreal": sorted(hu)}
    if hs and hu:
        # every LOD0 BODY vertex must lie inside AT LEAST ONE of Unreal's hulls, and every shipped
        # hull's vertices must round-trip onto one of Unreal's.  Final pass: the hanging tails have
        # no collision by design; they are the cloth slot's vertices below the rim bottom (z < 0)
        # or outside the rim tube's centre circle (the build's own rule, blackhat_report collision)
        L0 = shipped["LOD0"]
        cloth = [i for i, n in enumerate(L0["slots"]) if "cloth" in n.lower()]
        cv = np.unique(L0["tris"][np.isin(L0["mat"], cloth)])
        rc_cm = float(REPORT["geometry"]["frame"]["tube_centre_mm"][0]) / 10.0
        co0 = L0["co"]
        hang = np.zeros(len(co0), bool)
        hang[cv] = True
        hang &= (co0[:, 2] < -0.05) | (np.hypot(co0[:, 0], co0[:, 1]) > rc_cm)
        lod0 = co0[~hang]
        inside_any = np.full(len(lod0), np.inf)
        per = {}
        for k, h in hu.items():
            bm = bmesh.new()
            for p in h["co"]:
                bm.verts.new(p)
            bmesh.ops.convex_hull(bm, input=bm.verts)
            bm.normal_update()
            planes = [(np.array(f.normal[:]), float(np.dot(np.array(f.normal[:]), np.array(f.verts[0].co[:]))))
                      for f in bm.faces]
            bm.free()
            d = np.max(np.stack([lod0 @ n - dd for n, dd in planes]), axis=0)
            inside_any = np.minimum(inside_any, d)
            per[k] = {"vertices": int(len(h["co"])), "planes": len(planes)}
        vt = max(min(max(nn_max(a["co"], b["co"]), nn_max(b["co"], a["co"])) for b in hu.values()) for a in hs.values())
        report["hull"] = {"shipped_vertices": [int(len(v["co"])) for v in hs.values()], "unreal": per,
                          "vertices_two_sided_cm": round(vt, 7),
                          "lod0_body_vertices_tested": int(len(lod0)), "hanging_tail_vertices_excluded": int(hang.sum()),
                          "lod0_worst_outside_cm": round(float(inside_any.max()), 7),
                          "contains_lod0_body": bool(inside_any.max() <= 1e-4)}
    else:
        report["hull"] = {"missing": True}
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("ROUNDTRIP", json.dumps(report)[:3000])


main()
