#!/usr/bin/env python
"""Are the four sockets actually ON the card, and does Cord still mate with the kunai?

The sidecar's numbers were confirmed in the engine (pass B).  What the engine cannot say
is whether those centimetres land on the mesh or in mid-air, so the distance from each
socket to the nearest point of the LOD0 surface is measured here, on the shipped FBX.
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealVerify2"
FBX = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
SIDECAR = json.loads((PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.sockets.json")
                     .read_text(encoding="utf-8"))
KUNAI = PROJ / "Exports" / "Shuriken" / "SM_Kunai_Plain.sockets.json"
OUT = HERE / "sockets.json"


def point_tri_dist(p, a, b, c):
    """Squared distance from p to triangle abc (Ericson, Real-Time Collision Detection)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = np.dot(ab, ap), np.dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return np.dot(ap, ap)
    bp = p - b
    d3, d4 = np.dot(ab, bp), np.dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return np.dot(bp, bp)
    vc = d1 * d4 - d3 * d2
    if vc <= 0 <= d1 and d3 <= 0:
        v = d1 / (d1 - d3)
        q = ap - v * ab
        return np.dot(q, q)
    cp = p - c
    d5, d6 = np.dot(ab, cp), np.dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return np.dot(cp, cp)
    vb = d5 * d2 - d1 * d6
    if vb <= 0 <= d2 and d6 <= 0:
        w = d2 / (d2 - d6)
        q = ap - w * ac
        return np.dot(q, q)
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        q = (b + w * (c - b)) - p
        return np.dot(q, q)
    denom = 1.0 / (va + vb + vc)
    v, w = vb * denom, vc * denom
    q = a + ab * v + ac * w - p
    return np.dot(q, q)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX), automatic_bone_orientation=True)
    obj = bpy.data.objects["SM_PaperBomb_LOD0"]
    me = obj.data
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) * 1000.0                 # mm, Blender frame
    tris = np.array([list(t.vertices) for t in me.loop_triangles], np.int64)

    rep = {"mesh": "SM_PaperBomb_LOD0", "triangles": int(len(tris)),
           "extent_mm": {"min": [round(float(x), 4) for x in co.min(axis=0)],
                         "max": [round(float(x), 4) for x in co.max(axis=0)]},
           "frame_note": ("sidecar locations are Unreal cm; Unreal's Y is Blender's -Y, so "
                          "the probe negates Y before comparing")}
    rows = []
    for s in SIDECAR["sockets"]:
        lx, ly, lz = s["location_cm"]
        p = np.array([lx * 10.0, -ly * 10.0, lz * 10.0])     # cm -> mm, UE Y -> Blender Y
        # nearest vertex first, then the true surface distance over nearby triangles
        dv = np.linalg.norm(co - p, axis=1)
        near = np.argsort(dv)[:60]
        cand = [i for i, t in enumerate(tris) if any(v in near for v in t)]
        best = min((point_tri_dist(p, co[a], co[b], co[c]) for a, b, c in tris[cand]),
                   default=float(dv.min()) ** 2)
        rows.append({
            "socket": s["socket"],
            "location_cm": s["location_cm"],
            "location_mm_unreal": [round(v * 10.0, 4) for v in s["location_cm"]],
            "rotation_deg": s["rotation_deg"],
            "scale": s["scale"],
            "nearest_vertex_mm": round(float(dv.min()), 5),
            "distance_to_surface_mm": round(float(math.sqrt(best)), 5),
            "on_surface_within_0.2mm": bool(math.sqrt(best) < 0.2),
            "inside_bbox": bool(np.all(p >= co.min(axis=0) - 0.5) and
                                np.all(p <= co.max(axis=0) + 0.5)),
        })
    rep["sockets"] = rows

    if KUNAI.is_file():
        k = json.loads(KUNAI.read_text(encoding="utf-8"))
        ring = next((x for x in k["sockets"] if x["socket"].lower() == "ring"), None)
        cord = next((x for x in SIDECAR["sockets"] if x["socket"] == "Cord"), None)
        if ring and cord:
            rep["kunai_dry_fit"] = {
                "kunai_ring_cm": ring["location_cm"],
                "kunai_ring_rotation": ring["rotation_deg"],
                "paperbomb_cord_cm": cord["location_cm"],
                "paperbomb_cord_rotation": cord["rotation_deg"],
                "offset_to_mate_cm": [round(a - b, 5) for a, b in
                                      zip(ring["location_cm"], cord["location_cm"])],
                "both_rotations_identity_or_flat": bool(
                    all(abs(v) < 1e-6 for v in ring["rotation_deg"].values()) and
                    all(abs(v) < 1e-6 for v in cord["rotation_deg"].values())),
                "readme_claims_ring_mm": [-103.5, 0, 0],
                "ring_matches_readme_within_0.1mm": bool(
                    abs(ring["location_cm"][0] * 10.0 + 103.5) < 0.1),
            }
    OUT.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print("[sockets] ->", OUT)
    print(json.dumps(rep, indent=1))


main()
