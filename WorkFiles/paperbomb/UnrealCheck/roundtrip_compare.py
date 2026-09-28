#!/usr/bin/env python
"""Compare Unreal's own FBX export of the saved asset with the FBX that shipped.

Run in a FOURTH process, in Blender, after pass 3:

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/paperbomb/UnrealCheck/roundtrip_compare.py

This is the gate that cannot be fooled by an API.  Unreal's Python can be asked how many
convex hulls a mesh has and it will answer; asking it to WRITE THE HULL OUT and then
measuring that geometry against the hull that was sent is a different question, and it is
the one that matters for collision, which "silently lands as none" when the naming is
wrong.

Three comparisons, all in centimetres in Unreal space:

    positions           every LOD's vertex cloud, two-sided nearest-neighbour
    uv0_keyed           the same, but matched by UV0 instead of by proximity, so a
                        shuffled vertex order cannot hide a moved vertex
    hull                the convex hull's own vertices, two-sided, and whether the
                        hull's span still contains LOD0
"""
import json
import math
from pathlib import Path

import bpy
import numpy as np

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealCheck"
SHIPPED = PROJ / "Exports" / "PaperBomb" / "SM_PaperBomb.fbx"
UNREAL = HERE / "unreal_roundtrip.fbx"
OUT = HERE / "roundtrip_compare.json"


def load(path, tag):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        co = np.empty(len(mesh.vertices) * 3, np.float64)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        # WORLD space, not local.  Unreal's own FBX exporter leaves a transform on the
        # node (the shipped file's objects are at identity), and comparing local
        # coordinates made every LOD look 8 metres out of place on a 156 mm card.
        m = np.array(obj.matrix_world)
        co = (co @ m[:3, :3].T + m[:3, 3]) * 100.0         # Blender metres -> Unreal cm
        entry = {"vertices": co, "triangles": len(mesh.loop_triangles),
                 "uv_layers": [layer.name for layer in mesh.uv_layers],
                 "extents_cm": {"min": [round(float(x), 5) for x in co.min(axis=0)],
                                "max": [round(float(x), 5) for x in co.max(axis=0)],
                                "size": [round(float(x), 5) for x in np.ptp(co, axis=0)]},
                 "object_scale": [round(float(v), 6) for v in obj.scale],
                 "object_location_m": [round(float(v), 6) for v in obj.location]}
        if len(mesh.uv_layers) >= 2:
            uv1 = np.empty(len(mesh.loops) * 2, np.float64)
            mesh.uv_layers[1].data.foreach_get("uv", uv1)
            uv1 = uv1.reshape(-1, 2)
            entry["uv1_range"] = [round(float(uv1.min()), 6), round(float(uv1.max()), 6)]
        if mesh.uv_layers:
            uv = np.empty(len(mesh.loops) * 2, np.float64)
            mesh.uv_layers[0].data.foreach_get("uv", uv)
            uv = uv.reshape(-1, 2)
            vidx = np.empty(len(mesh.loops), np.int32)
            mesh.loops.foreach_get("vertex_index", vidx)
            pairs = {}
            for loop_index in range(len(mesh.loops)):
                pairs.setdefault((int(vidx[loop_index]), tuple(np.round(uv[loop_index], 5))),
                                 (uv[loop_index], co[vidx[loop_index]]))
            entry["uv_pairs"] = list(pairs.values())
        out[obj.name] = entry
    return out


def uv_matched_positions(a, b):
    """Match every shipped (uv, position) to the NEAREST Unreal one by UV.

    Exact UV keys do not survive the engine: Unreal stores static-mesh UVs as half
    floats unless "Use Full Precision UVs" is ticked, so a 2048 map's texel moves by up
    to ~0.5 texel and not one key matched.  Nearest-UV matching keeps the point of the
    test - a vertex that MOVED cannot hide behind a shuffled vertex order - and the UV
    quantisation itself is reported, because it is a real property of the shipped asset.
    """
    ua = np.array([p[0] for p in a], np.float64)
    pa = np.array([p[1] for p in a], np.float64)
    ub = np.array([p[0] for p in b], np.float64)
    pb = np.array([p[1] for p in b], np.float64)
    worst_pos = 0.0
    worst_uv = 0.0
    total = 0.0
    for start in range(0, len(ua), 256):
        chunk = ua[start:start + 256]
        d = np.linalg.norm(chunk[:, None, :] - ub[None, :, :], axis=2)
        nearest = d.argmin(axis=1)
        worst_uv = max(worst_uv, float(d[np.arange(len(chunk)), nearest].max()))
        diff = np.linalg.norm(pa[start:start + 256] - pb[nearest], axis=1)
        worst_pos = max(worst_pos, float(diff.max()))
        total += float(diff.sum())
    return {"pairs_compared": int(len(ua)),
            "max_position_diff_cm": round(worst_pos, 8),
            "mean_position_diff_cm": round(total / max(1, len(ua)), 10),
            "max_uv_quantisation": round(worst_uv, 8),
            "max_uv_quantisation_texels_at_2048": round(worst_uv * 2048, 4),
            "note": ("UVs are matched nearest-neighbour because Unreal stores static-mesh "
                     "UVs as half floats unless Use Full Precision UVs is on")}


def two_sided(a: np.ndarray, b: np.ndarray) -> float:
    def one_way(p, q):
        worst = 0.0
        for start in range(0, len(p), 256):
            chunk = p[start:start + 256]
            d = np.linalg.norm(chunk[:, None, :] - q[None, :, :], axis=2)
            worst = max(worst, float(d.min(axis=1).max()))
        return worst
    return max(one_way(a, b), one_way(b, a))


def normalise(name: str) -> str:
    """Unreal's exporter renames nodes; match on the LOD index and the UCX prefix."""
    low = name.lower()
    if low.startswith("ucx"):
        return "UCX"
    for i in range(4):
        if f"lod{i}" in low:
            return f"LOD{i}"
    return name


def main():
    if not UNREAL.is_file():
        OUT.write_text(json.dumps({"error": f"{UNREAL} not found - run pass 3 first"}, indent=2),
                       encoding="utf-8")
        print("[roundtrip] no Unreal export to compare")
        return

    shipped = {normalise(k): v for k, v in load(SHIPPED, "shipped").items()}
    unreal_side = {normalise(k): v for k, v in load(UNREAL, "unreal").items()}

    report = {"shipped_fbx": str(SHIPPED), "unreal_fbx": str(UNREAL),
              "shipped_nodes": sorted(shipped), "unreal_nodes": sorted(unreal_side),
              "lods": {}}

    for key in ("LOD0", "LOD1", "LOD2"):
        a, b = shipped.get(key), unreal_side.get(key)
        if a is None or b is None:
            report["lods"][key] = {"error": f"missing in {'shipped' if a is None else 'unreal'}"}
            continue
        entry = {"shipped_tris": a["triangles"], "unreal_tris": b["triangles"],
                 "position_two_sided_max_cm": round(two_sided(a["vertices"], b["vertices"]), 8),
                 "shipped_extents_cm": a.get("extents_cm"),
                 "unreal_extents_cm": b.get("extents_cm"),
                 "unreal_node_scale": b.get("object_scale"),
                 "shipped_uv_layers": a.get("uv_layers"),
                 "unreal_uv_layers": b.get("uv_layers"),
                 # the generated lightmap channel, read out of Unreal's own export of the
                 # BUILT data - which is the only place it exists
                 "unreal_uv1_range": b.get("uv1_range"),
                 "unreal_has_generated_uv1": len(b.get("uv_layers") or []) >= 2,
                 "unreal_uv1_inside_0_1": (b.get("uv1_range") is not None
                                           and b["uv1_range"][0] >= -1e-6
                                           and b["uv1_range"][1] <= 1.0 + 1e-6)}
        if "uv_pairs" in a and "uv_pairs" in b:
            entry["uv0_keyed_position_check"] = uv_matched_positions(a["uv_pairs"], b["uv_pairs"])
        report["lods"][key] = entry

    hull_a, hull_b = shipped.get("UCX"), unreal_side.get("UCX")
    if hull_a is not None and hull_b is not None:
        report["hull"] = {
            "shipped_vertices": len(hull_a["vertices"]),
            "unreal_vertices": len(hull_b["vertices"]),
            "two_sided_max_cm": round(two_sided(hull_a["vertices"], hull_b["vertices"]), 8),
        }
        lod0 = shipped.get("LOD0")
        if lod0 is not None:
            normals = [(math.cos(math.radians(t)), math.sin(math.radians(t)), 0.0)
                       for t in range(0, 360, 45)] + [(0, 0, 1.0), (0, 0, -1.0)]
            worst = -1e9
            for n in normals:
                nn = np.array(n)
                h = float((hull_b["vertices"] @ nn).max())
                worst = max(worst, float((lod0["vertices"] @ nn).max() - h))
            report["hull"]["unreal_hull_contains_lod0"] = bool(worst <= 1e-4)
            report["hull"]["lod0_max_outside_cm"] = round(float(worst), 8)
    else:
        report["hull"] = {"error": "no UCX node in one of the two files"}

    report["passed"] = bool(
        all(isinstance(v, dict) and "error" not in v
            and v.get("position_two_sided_max_cm", 1.0) <= 1e-4
            and v.get("shipped_tris") == v.get("unreal_tris")
            and (v.get("uv0_keyed_position_check") or {}).get("max_position_diff_cm", 1.0) <= 1e-4
            and v.get("unreal_has_generated_uv1")
            and v.get("unreal_uv1_inside_0_1")
            for v in report["lods"].values())
        and "error" not in report["hull"]
        and report["hull"].get("two_sided_max_cm", 1.0) <= 1e-4
        and report["hull"].get("unreal_hull_contains_lod0"))

    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("[roundtrip] ->", OUT, "passed" if report["passed"] else "FAILED")
    print(json.dumps({k: v for k, v in report.items() if k in ("lods", "hull", "passed")}, indent=2))


main()
