#!/usr/bin/env python
"""Collision containment, with plane orientation taken from the hull's own centroid.

Unreal's FBX collision export comes back with inverted winding, so a normal derived from
the triangle order points the wrong way.  Orienting every plane so the hull centroid is
strictly inside removes the assumption entirely.  Run over BOTH the shipped FBX and
Unreal's re-export, with one instrument, so the two are comparable.
"""
import json
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealVerify2"
OUT = HERE / "collision.json"
CASES = [("shipped", PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx", 1000.0),
         ("unreal_roundtrip", HERE / "roundtrip.fbx", 10.0)]


def load(path, scale):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=True)
    out = {}
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        me = o.data
        me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3) * scale
        tris = np.array([list(t.vertices) for t in me.loop_triangles], np.int64)
        out[o.name] = (co, tris)
    return out


def oriented_planes(v, t, tol=1e-4):
    c = v.mean(axis=0)
    planes = []
    for a, b, d3 in t:
        n = np.cross(v[b] - v[a], v[d3] - v[a])
        L = np.linalg.norm(n)
        if L < 1e-9:
            continue
        n = n / L
        d = float(np.dot(n, v[a]))
        if np.dot(n, c) - d > 0:            # centroid outside -> flip
            n, d = -n, -d
        for pn, pd in planes:
            if np.dot(pn, n) > 1 - 1e-6 and abs(pd - d) < tol:
                break
        else:
            planes.append((n, d))
    return planes


def main():
    rep = {}
    for tag, path, scale in CASES:
        if not Path(path).is_file():
            rep[tag] = {"error": "missing"}
            continue
        objs = load(path, scale)
        ucx = next((n for n in objs if n.upper().startswith("UCX")), None)
        rec = {"file": str(path), "objects": sorted(objs)}
        if ucx:
            hv, ht = objs[ucx]
            pl = oriented_planes(hv, ht)
            rec["hull"] = ucx
            rec["hull_vertices"] = int(len(hv))
            rec["hull_triangles"] = int(len(ht))
            rec["distinct_planes"] = len(pl)
            rec["hull_size_mm"] = [round(float(x), 4) for x in np.ptp(hv, axis=0)]
            rec["self_max_outside_mm"] = round(float(max((hv @ n - d).max() for n, d in pl)), 9)
            rec["is_convex"] = rec["self_max_outside_mm"] < 1e-3
            for n2 in sorted(objs):
                if n2.upper().startswith("UCX"):
                    continue
                lv = objs[n2][0]
                w = float(max((lv @ n - d).max() for n, d in pl))
                rec[f"{n2}_max_outside_mm"] = round(w, 9)
                rec[f"{n2}_contained_1um"] = w < 1e-3
                rec[f"{n2}_contained_exact"] = w < 1e-6
            l0 = next((objs[k][0] for k in objs if k.endswith("LOD0")
                       and not k.upper().startswith("UCX")), None)
            if l0 is not None:
                sides = []
                for n, d in pl:
                    if abs(n[2]) > 0.2:
                        continue
                    sides.append({"n": [round(float(x), 4) for x in n],
                                  "slack_over_lod0_mm": round(d - float((l0 @ n).max()), 7)})
                rec["side_plane_slack"] = sorted(sides, key=lambda r: r["slack_over_lod0_mm"])
                rec["max_side_slack_mm"] = round(max(s["slack_over_lod0_mm"] for s in sides), 7)
                caps = [{"n": [round(float(x), 4) for x in n],
                         "slack_over_lod0_mm": round(d - float((l0 @ n).max()), 7)}
                        for n, d in pl if abs(n[2]) > 0.2]
                rec["cap_plane_slack"] = caps
        rep[tag] = rec
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("[collision] ->", OUT)
    print(json.dumps(rep, indent=1))


main()
