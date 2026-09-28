"""Regression gate: the four-point after the two-form pack rebuild (four_point + eight_point).

Headless:
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python WorkFiles/shuriken/regression/compare_pack_eight.py

Baselines:
  * rev 2 (Backups/four_point_report_rev2_2026-09-17.json, Backups/Shuriken_rev_fourpoint_2026-09-17.blend):
    the build-to figures and LOD0 mesh data, as compare_rev2.py checks them;
  * rev 3 single-form state, snapshotted to pre_eight_snapshot/ just before the pack rebuild:
    every LOD's mesh data, hull, sockets, FBX content, sidecar bytes, report and renders.
Also checks the new .blend's collections and the eight-point FBX round trip.
Writes regression_pack_eight.json next to this file.
"""
import hashlib
import json
from pathlib import Path

import bpy
import numpy as np

PROJECT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "pre_eight_snapshot"
REV2_REPORT = PROJECT / "Backups" / "four_point_report_rev2_2026-09-17.json"
REV2_BLEND = PROJECT / "Backups" / "Shuriken_rev_fourpoint_2026-09-17.blend"
NEW_REPORT = PROJECT / "WorkFiles" / "shuriken" / "four_point_report.json"
EIGHT_REPORT = PROJECT / "WorkFiles" / "shuriken" / "eight_point_report.json"
NEW_BLEND = PROJECT / "Assets" / "Shuriken.blend"
EXPORTS = PROJECT / "Exports" / "Shuriken"
RENDERS = PROJECT / "Renders" / "Shuriken"
DIAG = PROJECT / "WorkFiles" / "shuriken" / "diag"
FOUR = "SM_Shuriken_FourPoint"
LODS = [f"{FOUR}_LOD0", f"{FOUR}_LOD1", f"{FOUR}_LOD2"]
HULL = f"UCX_{FOUR}_LOD0_00"
SOCKETS = [f"SOCKET_{FOUR}_LOD0_Grip", f"SOCKET_{FOUR}_LOD0_Trail"]
SHOTS = ["four_point_persp", "four_point_top", "four_point_wire", "four_point_lods"]
VOLATILE = {"generated", "seconds"}


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
        "uv": arr(mesh.uv_layers[0], "uv", "vector", 2) if mesh.uv_layers else None,
    }
    rec["materials"] = [m.name if m else None for m in mesh.materials]
    return rec


def compare_arrays(a, b):
    if a is None or b is None:
        return {"old_present": a is not None, "new_present": b is not None, "identical": a is None and b is None}
    if a.shape != b.shape:
        return {"shape_old": list(a.shape), "shape_new": list(b.shape), "identical": False}
    if a.dtype == bool or np.issubdtype(a.dtype, np.integer):
        diff = int(np.count_nonzero(a != b))
        return {"count": int(a.size), "mismatches": diff, "identical": diff == 0}
    d = np.abs(a.astype(np.float64) - b.astype(np.float64))
    return {"count": int(a.size), "max_abs_diff": float(d.max()) if d.size else 0.0,
            "identical": bool(np.array_equal(a, b))}


def append_objects(path, names):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
    return {obj.name.rsplit(".", 1)[0] if obj.name not in names else obj.name: obj for obj in dst.objects}


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
    return {"max_abs_x255": round(float(d.max()) * 255, 3), "mean_abs": round(float(d.mean()), 7),
            "pixels_over_1_5_of_255": round(float((per_px > 1.5 / 255).mean()), 6),
            "pixels_over_8_5_of_255": round(float((per_px > 8.5 / 255).mean()), 6),
            "identical": bool(np.array_equal(a, b))}


def fbx_record(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            out[obj.name] = {"type": obj.type, "parent": obj.parent.name if obj.parent else None}
            continue
        ev = obj.evaluated_get(depsgraph)
        m = ev.to_mesh()
        co = np.array([(obj.matrix_world @ v.co)[:] for v in m.vertices], dtype=np.float64)
        rec = {"type": "MESH", "parent": obj.parent.name if obj.parent else None,
               "triangles": len(m.loop_triangles), "vertices": len(m.vertices), "co": co}
        ev.to_mesh_clear()
        out[obj.name] = rec
    return out


def sorted_rows(co):
    return co[np.lexsort((co[:, 2], co[:, 1], co[:, 0]))]


def dict_diff(a, b, path=""):
    """Paths where two JSON trees differ (volatile keys skipped)."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key in VOLATILE:
                continue
            if key not in a:
                out.append(f"{path}/{key}: added")
            elif key not in b:
                out.append(f"{path}/{key}: removed")
            else:
                out += dict_diff(a[key], b[key], f"{path}/{key}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += dict_diff(x, y, f"{path}[{i}]")
    elif a != b:
        out.append(f"{path}: {json.dumps(a)[:80]} -> {json.dumps(b)[:80]}")
    return out


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


result = {"rev2_report": str(REV2_REPORT), "snapshot": str(SNAP), "new_report": str(NEW_REPORT)}
rev2 = json.loads(REV2_REPORT.read_text(encoding="utf-8"))
snap = json.loads((SNAP / "four_point_report.json").read_text(encoding="utf-8"))
new = json.loads(NEW_REPORT.read_text(encoding="utf-8"))

# ------------------------------------------------------------------ gate figures (rev 2 baseline)
gate = [("across_mm", 0.01), ("across_y_mm", 0.01), ("thickness_mm", 0.01), ("arm_width_mm", 0.01),
        ("hole_across_flats_mm", 0.01), ("plate_area_mm2", 0.1), ("mass_g", 0.01)]
figures = {}
for key, tol in gate:
    a, b = rev2["measured"][key], new["measured"][key]
    figures[key] = {"rev2": a, "now": b, "delta": round(b - a, 9), "tolerance": tol, "pass": abs(b - a) <= tol}
figures["lod_triangles"] = {"rev3_single_form": snap["lod_triangles"], "now": new["lod_triangles"],
                            "pass": new["lod_triangles"] == snap["lod_triangles"] == [1376, 576, 160]}
figures["lod_bands_ok"] = {"now": new["lod_bands_ok"], "pass": all(new["lod_bands_ok"])}
figures["c4_max_deviation_mm"] = {"now": new["c4_max_deviation_mm"],
                                  "pass": all(v == 0.0 for v in new["c4_max_deviation_mm"].values())}
figures["qa"] = {"now": f"{sum(c['passed'] for c in new['qa']['checks'])}/{len(new['qa']['checks'])}",
                 "rev3_single_form": f"{sum(c['passed'] for c in snap['qa']['checks'])}/{len(snap['qa']['checks'])}",
                 "pass": bool(new["qa"]["passed"]) and len(new["qa"]["checks"]) == 55}
figures["hull"] = {"now": new["hull"], "pass": new["hull"] == snap["hull"] == {
    "name": HULL, "verts": 24, "faces": 44}}
figures["socket_records"] = {"pass": new["socket_records"] == snap["socket_records"] == rev2.get("socket_records",
                                                                                               snap["socket_records"])}
result["gate_figures"] = figures
result["report_vs_rev3_single_form"] = dict_diff(snap, new)
result["measured_identical_to_rev3_single_form"] = snap["measured"] == new["measured"]
result["measured_identical_to_rev2"] = {k: rev2["measured"].get(k) == new["measured"].get(k)
                                        for k in sorted(new["measured"]) if k in rev2["measured"]}
for key in ("mesh_stats", "lod_mesh_stats", "lod_params", "uv", "lod_uv", "hull", "socket_records", "sockets",
            "lod_surface_deviation_two_sided_mm", "lod_measured", "symmetry", "density", "export"):
    result[f"{key}_identical_to_rev3_single_form"] = snap.get(key) == new.get(key) if key != "export" else \
        {k: snap["export"].get(k) == new["export"].get(k) for k in ("objects", "settings", "warnings", "sockets",
                                                                   "lod_screen_sizes")}

# ------------------------------------------------------------------ mesh data (.blend)
bpy.ops.wm.open_mainfile(filepath=str(NEW_BLEND))
result["new_blend_collections"] = {c.name: sorted(o.name for o in c.objects) for c in bpy.data.collections}
result["new_blend_scene_root_objects"] = sorted(o.name for o in bpy.context.scene.collection.objects)
result["new_blend_materials"] = sorted(m.name for m in bpy.data.materials)
names = LODS + [HULL] + SOCKETS
new_objs = {name: bpy.data.objects.get(name) for name in names}
new_recs = {name: mesh_record(new_objs[name]) for name in LODS + [HULL]}
new_mats = {name: np.array(new_objs[name].matrix_basis, dtype=np.float64) for name in SOCKETS}
new_parent = {name: (new_objs[name].parent.name if new_objs[name].parent else None) for name in names}
new_principled = principled(bpy.data.materials["M_Shuriken_Master"])
new_eight = {o.name: {"type": o.type, "parent": o.parent.name if o.parent else None,
                      "collections": [c.name for c in o.users_collection],
                      "matrix_identity": bool(np.allclose(np.array(o.matrix_world), np.eye(4)))
                      if not o.name.startswith("SOCKET_") else None}
             for o in bpy.data.objects if "EightPoint" in o.name}

snap_objs = append_objects(SNAP / "Shuriken.blend", names)
snap_recs = {name: mesh_record(snap_objs[name]) for name in LODS + [HULL]}
result["vs_rev3_single_form_blend"] = {
    name: {k: compare_arrays(snap_recs[name][k], new_recs[name][k])
           for k in ("verts", "loops", "loop_start", "loop_total", "edges", "sharp_edge", "sharp_face", "uv")}
    for name in LODS + [HULL]}
result["sockets_vs_rev3_single_form"] = {
    name: {"max_abs_matrix_diff": float(np.abs(np.array(snap_objs[name].matrix_basis) - new_mats[name]).max()),
           "parent_now": new_parent[name], "type_now": new_objs[name].type}
    for name in SOCKETS}
result["material_export_scalars"] = {"now": new_principled}

bpy.ops.wm.read_factory_settings(use_empty=True)
rev2_objs = append_objects(REV2_BLEND, [LODS[0], HULL] + SOCKETS)
rev2_lod0 = mesh_record(rev2_objs[LODS[0]])
result["lod0_vs_rev2_blend"] = {k: compare_arrays(rev2_lod0[k], new_recs[LODS[0]][k])
                                for k in ("verts", "loops", "loop_start", "loop_total", "edges", "sharp_edge",
                                          "sharp_face", "uv")}
result["hull_vs_rev2_blend"] = compare_arrays(mesh_record(rev2_objs[HULL])["verts"], new_recs[HULL]["verts"])
result["sockets_vs_rev2_blend"] = {
    name: float(np.abs(np.array(rev2_objs[name].matrix_basis) - new_mats[name]).max()) for name in SOCKETS}
result["eight_point_objects_in_blend"] = new_eight

# ------------------------------------------------------------------ FBX round trip + sidecar
fbx_snap = fbx_record(SNAP / "export" / f"{FOUR}.fbx")
fbx_new = fbx_record(EXPORTS / f"{FOUR}.fbx")
fbx = {"nodes_snapshot": sorted(fbx_snap), "nodes_now": sorted(fbx_new), "meshes": {}}
for name in sorted(set(fbx_snap) | set(fbx_new)):
    a, b = fbx_snap.get(name), fbx_new.get(name)
    if not a or not b or a.get("type") != "MESH":
        continue
    entry = {"triangles": [a["triangles"], b["triangles"]], "vertices": [a["vertices"], b["vertices"]]}
    if a["co"].shape == b["co"].shape:
        entry["sorted_vertex_max_abs_diff_m"] = float(np.abs(sorted_rows(a["co"]) - sorted_rows(b["co"])).max())
    fbx["meshes"][name] = entry
fbx["bytes_equal"] = (SNAP / "export" / f"{FOUR}.fbx").read_bytes() == (EXPORTS / f"{FOUR}.fbx").read_bytes()
fbx["bytes_note"] = ("FBX bytes differ only in the header CreationTimeStamp and the per-run object UIDs; "
                     "content is compared by re-import above")
result["four_point_fbx_reimport"] = fbx
result["four_point_sidecar_sha256"] = {"snapshot": sha(SNAP / "export" / f"{FOUR}.sockets.json"),
                                       "now": sha(EXPORTS / f"{FOUR}.sockets.json")}
result["four_point_sidecar_byte_identical"] = (result["four_point_sidecar_sha256"]["snapshot"]
                                               == result["four_point_sidecar_sha256"]["now"])

eight = json.loads(EIGHT_REPORT.read_text(encoding="utf-8"))
fbx8 = fbx_record(EXPORTS / "SM_Shuriken_EightPoint.fbx")
bounds = {}
for name, rec in fbx8.items():
    if rec.get("type") == "MESH":
        co = rec.pop("co")
        rec["size_mm"] = [round(float(v) * 1000, 6) for v in (co.max(axis=0) - co.min(axis=0))]
        bounds[name] = rec["size_mm"]
result["eight_point_fbx_reimport"] = {
    "nodes": {k: {kk: vv for kk, vv in v.items() if kk != "co"} for k, v in fbx8.items()},
    "lod_triangles_blender_report": eight["lod_triangles"],
    "lod_triangles_fbx": [fbx8.get(f"SM_Shuriken_EightPoint_LOD{i}", {}).get("triangles") for i in range(3)],
    "hull_node": "UCX_SM_Shuriken_EightPoint_LOD0_00" in fbx8,
    "socket_nodes_in_fbx": sorted(k for k in fbx8 if k.startswith("SOCKET_")),
}
lod0_size = fbx8.get("SM_Shuriken_EightPoint_LOD0", {}).get("size_mm") or [0.0, 0.0, 0.0]
result["eight_point_fbx_reimport"]["pass"] = bool(
    result["eight_point_fbx_reimport"]["lod_triangles_fbx"] == eight["lod_triangles"]
    and result["eight_point_fbx_reimport"]["hull_node"]
    and not result["eight_point_fbx_reimport"]["socket_nodes_in_fbx"]
    and all(abs(a - b) < 1e-3 for a, b in zip(lod0_size, (100.0, 100.0, 2.5))))

# Unreal verified the FBX files copied to UnrealCheck4/verified/; the final export must carry the same content.
VERIFIED = PROJECT / "WorkFiles" / "shuriken" / "UnrealCheck4" / "verified"
result["final_export_vs_unreal_verified"] = {}
for mesh_name in (FOUR, "SM_Shuriken_EightPoint"):
    verified_fbx = VERIFIED / f"{mesh_name}.fbx"
    if not verified_fbx.exists():
        result["final_export_vs_unreal_verified"][mesh_name] = {"missing": str(verified_fbx)}
        continue
    a, b = fbx_record(verified_fbx), fbx_record(EXPORTS / f"{mesh_name}.fbx")
    per = {}
    for name in sorted(set(a) | set(b)):
        ra, rb = a.get(name), b.get(name)
        if not ra or not rb:
            per[name] = {"present": [ra is not None, rb is not None]}
        elif ra.get("type") == "MESH":
            same_shape = ra["co"].shape == rb["co"].shape
            per[name] = {"triangles": [ra["triangles"], rb["triangles"]],
                         "sorted_vertex_max_abs_diff_m": (float(np.abs(sorted_rows(ra["co"]) - sorted_rows(rb["co"])).max())
                                                          if same_shape else None)}
    sidecar_same = sha(VERIFIED / f"{mesh_name}.sockets.json") == sha(EXPORTS / f"{mesh_name}.sockets.json")
    result["final_export_vs_unreal_verified"][mesh_name] = {
        "meshes": per, "sidecar_byte_identical": sidecar_same,
        "identical": sidecar_same and all(v.get("sorted_vertex_max_abs_diff_m") == 0.0
                                          and v["triangles"][0] == v["triangles"][1] for v in per.values())}

# ------------------------------------------------------------------ renders
result["renders_vs_rev3_single_form"] = {shot: png_diff(SNAP / "renders" / f"{shot}.png", RENDERS / f"{shot}.png")
                                         for shot in SHOTS}
result["masks_vs_rev3_single_form"] = {shot: png_diff(SNAP / "diag" / f"{shot}_mask.png", DIAG / f"{shot}_mask.png")
                                       for shot in SHOTS}

# ------------------------------------------------------------------ verdict
mesh_same = all(v.get("identical") for per in result["vs_rev3_single_form_blend"].values() for v in per.values())
lod0_rev2_same = all(v.get("identical") for v in result["lod0_vs_rev2_blend"].values())
fbx_same = all(m.get("sorted_vertex_max_abs_diff_m") == 0.0 and m["triangles"][0] == m["triangles"][1]
               for m in fbx["meshes"].values()) and fbx["nodes_snapshot"] == fbx["nodes_now"]
sockets_same = all(v["max_abs_matrix_diff"] == 0.0 for v in result["sockets_vs_rev3_single_form"].values())
renders_ok = all(r.get("max_abs_x255", 99) <= 2.0 and r.get("pixels_over_1_5_of_255", 1) <= 0.001
                 for r in result["renders_vs_rev3_single_form"].values())
result["summary"] = {
    "gate_figures_pass": all(v["pass"] for v in figures.values()),
    "all_lod_meshes_hull_bitwise_identical_to_rev3_single_form": mesh_same,
    "lod0_bitwise_identical_to_rev2": lod0_rev2_same,
    "hull_identical_to_rev2": result["hull_vs_rev2_blend"].get("identical"),
    "socket_matrices_identical": sockets_same,
    "fbx_content_identical": fbx_same,
    "sidecar_byte_identical": result["four_point_sidecar_byte_identical"],
    "renders_within_noise_floor": renders_ok,
    "collections": sorted(result["new_blend_collections"]),
    "eight_point_fbx_pass": bool(result["eight_point_fbx_reimport"]["pass"]),
    "final_exports_match_unreal_verified": all(v.get("identical") for v in
                                               result["final_export_vs_unreal_verified"].values()),
}
result["passed"] = all(v for k, v in result["summary"].items() if k != "collections")
out = HERE / "regression_pack_eight.json"
out.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
print("REGRESSION_SUMMARY " + json.dumps(result["summary"]) + " passed=" + str(result["passed"]))
