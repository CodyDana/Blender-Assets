"""Regression gate: rev 3 (shuriken_lib) four-point against the rev 2 baseline.

Headless:
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/shuriken/regression/compare_rev2.py -- [--noise-dir DIR]

Compares, and writes regression_rev3.json next to this file:
  * the report figures the gate names (across, thickness, arm, hole flats, plate area,
    mass, LOD0 triangles, C4, qa) against Backups/four_point_report_rev2_2026-09-17.json
  * LOD0 mesh data against the rev 2 .blend: vertex coordinates, face loops, UVs, sharp
    edges, smooth flags, hull vertices, socket matrices, material export scalars
  * both FBX files re-imported: node names, per-LOD triangles, LOD0 vertex set
  * gallery PNGs against the rev 2 snapshot, and (with --noise-dir) a same-code rev 2
    rerun against the snapshot, which is the run-to-run noise floor.
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

PROJECT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "rev2_snapshot"
BASE_REPORT = PROJECT / "Backups" / "four_point_report_rev2_2026-09-17.json"
BASE_BLEND = PROJECT / "Backups" / "Shuriken_rev_fourpoint_2026-09-17.blend"
NEW_REPORT = PROJECT / "WorkFiles" / "shuriken" / "four_point_report.json"
NEW_BLEND = PROJECT / "Assets" / "Shuriken.blend"
NEW_FBX = PROJECT / "Exports" / "Shuriken" / "SM_Shuriken_FourPoint.fbx"
OLD_FBX = SNAP / "export" / "SM_Shuriken_FourPoint.fbx"
NEW_RENDERS = PROJECT / "Renders" / "Shuriken"
LOD0 = "SM_Shuriken_FourPoint_LOD0"
HULL = "UCX_SM_Shuriken_FourPoint_LOD0_00"
SOCKETS = ["SOCKET_SM_Shuriken_FourPoint_LOD0_Grip", "SOCKET_SM_Shuriken_FourPoint_LOD0_Trail"]
SHOTS = ["four_point_persp", "four_point_top", "four_point_wire", "four_point_lods"]

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NOISE = Path(argv[argv.index("--noise-dir") + 1]) if "--noise-dir" in argv else None


def arr(mesh, collection, prop, width, dtype=np.float32):
    data = getattr(mesh, collection)
    out = np.empty(len(data) * width, dtype=dtype)
    data.foreach_get(prop, out)
    return out.reshape(-1, width) if width > 1 else out


def attr(mesh, name, dtype=bool):
    a = mesh.attributes.get(name)
    if a is None:
        return None
    out = np.empty(len(a.data), dtype=dtype)
    a.data.foreach_get("value", out)
    return out


def mesh_record(obj):
    mesh = obj.data
    rec = {
        "verts": arr(mesh, "vertices", "co", 3),
        "loops": arr(mesh, "loops", "vertex_index", 1, np.int64),
        "loop_start": arr(mesh, "polygons", "loop_start", 1, np.int64),
        "loop_total": arr(mesh, "polygons", "loop_total", 1, np.int64),
        "sharp_edge": attr(mesh, "sharp_edge"),
        "sharp_face": attr(mesh, "sharp_face"),
        "edges": arr(mesh, "edges", "vertices", 2, np.int64),
        "materials": [m.name if m else None for m in mesh.materials],
    }
    if mesh.uv_layers:
        rec["uv"] = arr(mesh.uv_layers[0], "uv", "vector", 2) if hasattr(mesh.uv_layers[0], "uv") else None
        if rec["uv"] is None:
            rec["uv"] = arr(mesh.uv_layers[0], "data", "uv", 2)
    return rec


def compare_arrays(a, b):
    if a is None or b is None:
        return {"old_present": a is not None, "new_present": b is not None}
    if a.shape != b.shape:
        return {"shape_old": list(a.shape), "shape_new": list(b.shape), "identical": False}
    if a.dtype == bool or np.issubdtype(a.dtype, np.integer):
        diff = int(np.count_nonzero(a != b))
        return {"count": int(a.size), "mismatches": diff, "identical": diff == 0}
    d = np.abs(a.astype(np.float64) - b.astype(np.float64))
    return {"count": int(a.size), "max_abs_diff": float(d.max()) if d.size else 0.0,
            "bitwise_identical": bool(np.array_equal(a, b))}


def append_objects(path, names):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
    return {name: obj for name, obj in zip(names, dst.objects)}


def principled(mat):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    return {"base_color": [round(v, 6) for v in bsdf.inputs["Base Color"].default_value],
            "metallic": round(bsdf.inputs["Metallic"].default_value, 6),
            "roughness": round(bsdf.inputs["Roughness"].default_value, 6),
            "nodes": len(mat.node_tree.nodes)}


def load_png(path):
    img = bpy.data.images.load(str(path), check_existing=False)
    img.colorspace_settings.name = "Non-Color"
    img.reload()
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    bpy.data.images.remove(img)
    return buf.reshape(h, w, 4)


def png_diff(a_path, b_path):
    if not Path(a_path).exists() or not Path(b_path).exists():
        return {"missing": [str(p) for p in (a_path, b_path) if not Path(p).exists()]}
    a, b = load_png(a_path), load_png(b_path)
    if a.shape != b.shape:
        return {"shape_a": list(a.shape), "shape_b": list(b.shape)}
    d = np.abs(a[..., :3].astype(np.float64) - b[..., :3].astype(np.float64))
    per_px = d.max(axis=-1)
    return {"max_abs": round(float(d.max()), 6), "mean_abs": round(float(d.mean()), 7),
            "pixels_over_1_255": round(float((per_px > 1.5 / 255).mean()), 6),
            "pixels_over_8_255": round(float((per_px > 8.5 / 255).mean()), 6),
            "identical": bool(np.array_equal(a, b))}


def fbx_record(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            out[obj.name] = {"type": obj.type}
            continue
        ev = obj.evaluated_get(depsgraph)
        m = ev.to_mesh()
        co = np.array([(obj.matrix_world @ v.co)[:] for v in m.vertices], dtype=np.float64)
        rec = {"type": "MESH", "triangles": len(m.loop_triangles), "vertices": len(m.vertices), "co": co}
        ev.to_mesh_clear()
        out[obj.name] = rec
    return out


def sorted_rows(co):
    order = np.lexsort((co[:, 2], co[:, 1], co[:, 0]))
    return co[order]


result = {"baseline_report": str(BASE_REPORT), "new_report": str(NEW_REPORT)}

# ------------------------------------------------------------------ report figures
old = json.loads(BASE_REPORT.read_text(encoding="utf-8"))
new = json.loads(NEW_REPORT.read_text(encoding="utf-8"))
gate = [("across_mm", 0.01), ("across_y_mm", 0.01), ("thickness_mm", 0.01), ("arm_width_mm", 0.01),
        ("hole_across_flats_mm", 0.01), ("plate_area_mm2", 0.1), ("mass_g", 0.01)]
figures = {}
for key, tol in gate:
    a, b = old["measured"][key], new["measured"][key]
    figures[key] = {"before": a, "after": b, "delta": round(b - a, 9), "tolerance": tol,
                    "pass": abs(b - a) <= tol}
tri_old, tri_new = old["lod_triangles"], new["lod_triangles"]
figures["lod0_triangles"] = {"before": tri_old[0], "after": tri_new[0], "pass": tri_new[0] == 1376}
figures["c4_lod0_mm"] = {"before": old["c4_max_deviation_mm"][LOD0], "after": new["c4_max_deviation_mm"][LOD0],
                         "pass": new["c4_max_deviation_mm"][LOD0] == 0.0}
figures["qa"] = {"before": f"{sum(c['passed'] for c in old['qa']['checks'])}/{len(old['qa']['checks'])}",
                 "after": f"{sum(c['passed'] for c in new['qa']['checks'])}/{len(new['qa']['checks'])}",
                 "pass": bool(new["qa"]["passed"])}
bands = new["lod_bands"]
figures["lod_bands"] = {"before": tri_old, "after": tri_new, "bands": bands,
                        "pass": all(new["lod_bands_ok"])}
all_measured = {k: {"before": old["measured"].get(k), "after": new["measured"].get(k)}
                for k in sorted(set(old["measured"]) | set(new["measured"]))
                if old["measured"].get(k) != new["measured"].get(k)}
result["gate_figures"] = figures
result["measured_keys_that_differ"] = all_measured
for key in ("mesh_stats", "uv", "hull", "socket_records", "sockets"):
    result[f"{key}_identical"] = old.get(key) == new.get(key)

# ------------------------------------------------------------------ mesh data
bpy.ops.wm.open_mainfile(filepath=str(NEW_BLEND))
new_objs = {name: bpy.data.objects.get(name) for name in [LOD0, HULL] + SOCKETS}
old_objs = append_objects(BASE_BLEND, [LOD0, HULL] + SOCKETS)
lod0_new, lod0_old = mesh_record(new_objs[LOD0]), mesh_record(old_objs[LOD0])
result["lod0_mesh"] = {k: compare_arrays(lod0_old[k], lod0_new[k])
                       for k in ("verts", "loops", "loop_start", "loop_total", "edges", "sharp_edge",
                                 "sharp_face", "uv")}
result["lod0_mesh"]["materials"] = {"before": lod0_old["materials"], "after": lod0_new["materials"]}
result["hull_mesh"] = {"verts": compare_arrays(arr(old_objs[HULL].data, "vertices", "co", 3),
                                               arr(new_objs[HULL].data, "vertices", "co", 3))}
result["sockets"] = {}
for name in SOCKETS:
    a = np.array(old_objs[name].matrix_basis, dtype=np.float64)
    b = np.array(new_objs[name].matrix_basis, dtype=np.float64)
    result["sockets"][name] = {"max_abs_matrix_diff": float(np.abs(a - b).max()),
                               "parent_before": old_objs[name].parent.name if old_objs[name].parent else None,
                               "parent_after": new_objs[name].parent.name if new_objs[name].parent else None,
                               "type_after": new_objs[name].type}
old_mat = old_objs[LOD0].data.materials[0]
new_mat = bpy.data.materials["M_Shuriken_Master"]
result["material_export_scalars"] = {"before": principled(old_mat), "after": principled(new_mat)}
result["new_blend_collections"] = {c.name: sorted(o.name for o in c.objects) for c in bpy.data.collections}

# ------------------------------------------------------------------ FBX round trip
fbx_old, fbx_new = fbx_record(OLD_FBX), fbx_record(NEW_FBX)
fbx = {"nodes_before": sorted(fbx_old), "nodes_after": sorted(fbx_new), "meshes": {}}
for name in sorted(set(fbx_old) | set(fbx_new)):
    a, b = fbx_old.get(name), fbx_new.get(name)
    if not a or not b or a.get("type") != "MESH":
        continue
    entry = {"triangles_before": a["triangles"], "triangles_after": b["triangles"],
             "vertices_before": a["vertices"], "vertices_after": b["vertices"]}
    if a["co"].shape == b["co"].shape:
        entry["sorted_vertex_max_abs_diff_m"] = float(np.abs(sorted_rows(a["co"]) - sorted_rows(b["co"])).max())
    fbx["meshes"][name] = entry
result["fbx_reimport"] = fbx

# ------------------------------------------------------------------ renders
result["renders_vs_rev2_snapshot"] = {shot: png_diff(SNAP / "renders" / f"{shot}.png", NEW_RENDERS / f"{shot}.png")
                                      for shot in SHOTS}
result["masks_vs_rev2_snapshot"] = {shot: png_diff(SNAP / "diag" / f"{shot}_mask.png",
                                                   PROJECT / "WorkFiles" / "shuriken" / "diag" / f"{shot}_mask.png")
                                    for shot in SHOTS}
if NOISE is not None:
    result["noise_floor_rev2_rerun_vs_snapshot"] = {
        shot: png_diff(SNAP / "renders" / f"{shot}.png", NOISE / "renders" / f"{shot}.png") for shot in SHOTS}
result["render_stats"] = {shot: {"before": old["render_stats"][shot].get("object_luminance"),
                                 "after": new["render_stats"][shot].get("object_luminance"),
                                 "sector_spread_before": old["render_stats"][shot].get("object_sector_spread"),
                                 "sector_spread_after": new["render_stats"][shot].get("object_sector_spread"),
                                 "stats_identical": old["render_stats"][shot] == new["render_stats"][shot]}
                          for shot in SHOTS}

result["passed"] = all(v["pass"] for v in figures.values())
out = HERE / "regression_rev3.json"
out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
print("REGRESSION_RESULT " + json.dumps(result, default=str))
