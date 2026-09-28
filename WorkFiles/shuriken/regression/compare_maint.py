"""Regression gate for the maintenance pass (library 3.2): the four-point must not have moved.

Headless:
    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python-exit-code 3 \
        --python WorkFiles/shuriken/regression/compare_maint.py -- [--root DIR]

``--root`` points at a build tree with Shuriken.blend, export/, renders/, reports/ (a scratch
build); without it the project's own Assets / Exports / Renders / WorkFiles are compared.

Baselines:
  * rev 2 (Backups/four_point_report_rev2_2026-09-17.json, Backups/Shuriken_rev_fourpoint_2026-09-17.blend):
    build-to figures, LOD0 mesh data (vertices, loops, edges, sharp flags, UV0), hull, sockets;
  * pre_maint_snapshot/ (the pack exactly as the review saw it): every four-point LOD's geometry, the hull,
    sockets, FBX content, sidecar sockets, report figures; the eight-point report for before/after figures.

Expected differences (reported, not failed): four-point LOD1/LOD2 UV0 (now transferred from LOD0's
islands), the sidecar's lod_screen_sizes (1.0 / 0.10 / 0.035), every gallery PNG (rig, baked textures),
the material node count, report schema additions.  Everything else must be identical.
Writes regression_maint.json next to this file (or into --root when given).
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

PROJECT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SNAP = HERE / "pre_maint_snapshot"
REV2_REPORT = PROJECT / "Backups" / "four_point_report_rev2_2026-09-17.json"
REV2_BLEND = PROJECT / "Backups" / "Shuriken_rev_fourpoint_2026-09-17.blend"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ROOT = Path(argv[argv.index("--root") + 1]) if "--root" in argv else None
if ROOT:
    NEW_BLEND, EXPORTS, RENDERS, REPORTS = ROOT / "Shuriken.blend", ROOT / "export", ROOT / "renders", ROOT / "reports"
    OUT = ROOT / "regression_maint.json"
else:
    NEW_BLEND = PROJECT / "Assets" / "Shuriken.blend"
    EXPORTS, RENDERS, REPORTS = PROJECT / "Exports" / "Shuriken", PROJECT / "Renders" / "Shuriken", \
        PROJECT / "WorkFiles" / "shuriken"
    OUT = HERE / "regression_maint.json"

FOUR, EIGHT = "SM_Shuriken_FourPoint", "SM_Shuriken_EightPoint"
LODS = [f"{FOUR}_LOD0", f"{FOUR}_LOD1", f"{FOUR}_LOD2"]
HULL = f"UCX_{FOUR}_LOD0_00"
SOCKETS = [f"SOCKET_{FOUR}_LOD0_Grip", f"SOCKET_{FOUR}_LOD0_Trail"]
GEOMETRY_KEYS = ("verts", "loops", "loop_start", "loop_total", "edges", "sharp_edge", "sharp_face")


def arr(data, prop, width, dtype=np.float32):
    out = np.empty(len(data) * width, dtype=dtype)
    data.foreach_get(prop, out)
    return out.reshape(-1, width) if width > 1 else out


def attr(mesh, name):
    a = mesh.attributes.get(name)
    if a is None:
        return None
    out = np.empty(len(a.data), dtype=bool)
    a.data.foreach_get("value", out)
    return out


def mesh_record(obj):
    mesh = obj.data
    return {
        "verts": arr(mesh.vertices, "co", 3),
        "loops": arr(mesh.loops, "vertex_index", 1, np.int64),
        "loop_start": arr(mesh.polygons, "loop_start", 1, np.int64),
        "loop_total": arr(mesh.polygons, "loop_total", 1, np.int64),
        "edges": arr(mesh.edges, "vertices", 2, np.int64),
        "sharp_edge": attr(mesh, "sharp_edge"),
        "sharp_face": attr(mesh, "sharp_face"),
        "uv": arr(mesh.uv_layers[0].data, "uv", 2) if mesh.uv_layers else None,
        "uv_layers": [uv.name for uv in mesh.uv_layers],
    }


def same(a, b):
    if a is None or b is None:
        return {"identical": a is None and b is None}
    if a.shape != b.shape:
        return {"identical": False, "shape": [list(a.shape), list(b.shape)]}
    if a.dtype == bool or np.issubdtype(a.dtype, np.integer):
        return {"identical": bool(np.array_equal(a, b)), "mismatches": int(np.count_nonzero(a != b))}
    return {"identical": bool(np.array_equal(a, b)),
            "max_abs_diff": float(np.abs(a.astype(np.float64) - b.astype(np.float64)).max()) if a.size else 0.0}


def append_objects(path, names):
    before = set(bpy.data.objects.keys())
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in names if n in src.objects]
    got = {}
    for obj in dst.objects:
        base = obj.name if obj.name in names else obj.name.rsplit(".", 1)[0]
        got[base] = obj
    return got


def principled(mat):
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    return {"base_color": [round(v, 6) for v in bsdf.inputs["Base Color"].default_value],
            "metallic": round(bsdf.inputs["Metallic"].default_value, 6),
            "roughness": round(bsdf.inputs["Roughness"].default_value, 6),
            "nodes": len(mat.node_tree.nodes)}


def fbx_record(path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(path))
    out = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            out[obj.name] = {"type": obj.type}
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        co = np.array([(obj.matrix_world @ v.co)[:] for v in mesh.vertices], dtype=np.float64)
        out[obj.name] = {"type": "MESH", "triangles": len(mesh.loop_triangles), "vertices": len(mesh.vertices),
                         "co": co, "uv_layers": [uv.name for uv in mesh.uv_layers]}
    return out


def sorted_rows(co):
    return co[np.lexsort((co[:, 2], co[:, 1], co[:, 0]))]


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
        return {"shape": [list(a.shape), list(b.shape)]}
    d = np.abs(a[..., :3].astype(np.float64) - b[..., :3].astype(np.float64)).max(axis=-1)
    return {"mean_abs": round(float(d.mean()), 5), "pixels_over_8_of_255": round(float((d > 8.5 / 255).mean()), 4)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


result = {"root": str(ROOT) if ROOT else "project", "snapshot": str(SNAP), "rev2_report": str(REV2_REPORT)}
rev2 = json.loads(REV2_REPORT.read_text(encoding="utf-8"))
snap4 = json.loads((SNAP / "four_point_report.json").read_text(encoding="utf-8"))
snap8 = json.loads((SNAP / "eight_point_report.json").read_text(encoding="utf-8"))
new4 = json.loads((REPORTS / "four_point_report.json").read_text(encoding="utf-8"))
new8 = json.loads((REPORTS / "eight_point_report.json").read_text(encoding="utf-8"))

# ------------------------------------------------------------------ gate figures
gate = [("across_mm", 0.01), ("across_y_mm", 0.01), ("thickness_mm", 0.01), ("arm_width_mm", 0.01),
        ("hole_across_flats_mm", 0.01), ("plate_area_mm2", 0.1), ("mass_g", 0.01)]
figures = {}
for key, tol in gate:
    a, b = rev2["measured"][key], new4["measured"][key]
    figures[key] = {"rev2": a, "now": b, "delta": round(b - a, 9), "pass": abs(b - a) <= tol}
    figures[key]["identical_to_pre_maint"] = snap4["measured"][key] == b
figures["lod_triangles"] = {"pre_maint": snap4["lod_triangles"], "now": new4["lod_triangles"],
                            "pass": new4["lod_triangles"] == snap4["lod_triangles"] == [1376, 576, 160]}
figures["c4_max_deviation_mm"] = {"now": new4["c4_max_deviation_mm"],
                                  "pass": all(v == 0.0 for v in new4["c4_max_deviation_mm"].values())}
figures["qa"] = {"now": f"{sum(c['passed'] for c in new4['qa']['checks'])}/{len(new4['qa']['checks'])}",
                 "pass": bool(new4["qa"]["passed"]) and len(new4["qa"]["checks"]) == 55}
figures["hull"] = {"now": new4["hull"], "pass": new4["hull"] == snap4["hull"] == {"name": HULL, "verts": 24,
                                                                               "faces": 44}}
figures["socket_records"] = {"pass": new4["socket_records"] == snap4["socket_records"]}
figures["lod_bands_ok"] = {"now": new4["lod_bands_ok"], "pass": all(new4["lod_bands_ok"])}
figures["tip_included_deg_measured"] = {"now": new4["measured"].get("tip_included_deg"),
                                        "pass": abs(new4["measured"].get("tip_included_deg", 0) - 40.0) < 1e-4}
result["gate_figures"] = figures
result["measured_keys_changed_vs_pre_maint"] = sorted(
    k for k in set(snap4["measured"]) | set(new4["measured"]) if snap4["measured"].get(k) != new4["measured"].get(k))

# ------------------------------------------------------------------ .blend mesh data
bpy.ops.wm.open_mainfile(filepath=str(NEW_BLEND))
result["collections"] = {c.name: sorted(o.name for o in c.objects) for c in bpy.data.collections}
result["scene_root_objects"] = sorted(o.name for o in bpy.context.scene.collection.objects)
new_recs = {n: mesh_record(bpy.data.objects[n]) for n in LODS + [HULL]}
new_sock = {n: np.array(bpy.data.objects[n].matrix_basis, dtype=np.float64) for n in SOCKETS}
new_mat = principled(bpy.data.materials["M_Shuriken_Master"])
eight_objects = {o.name: {"type": o.type, "collections": [c.name for c in o.users_collection],
                          "identity": bool(np.allclose(np.array(o.matrix_world), np.eye(4)))}
                 for o in bpy.data.objects if "EightPoint" in o.name and not o.name.startswith("SOCKET_")}
snap_objs = append_objects(SNAP / "Shuriken.blend", LODS + [HULL] + SOCKETS)
snap_recs = {n: mesh_record(snap_objs[n]) for n in LODS + [HULL]}
snap_mat = principled(snap_objs[LODS[0]].data.materials[0])
result["four_point_vs_pre_maint"] = {
    n: {**{k: same(snap_recs[n][k], new_recs[n][k]) for k in GEOMETRY_KEYS},
        "uv0": same(snap_recs[n]["uv"], new_recs[n]["uv"]),
        "uv_layers": [snap_recs[n]["uv_layers"], new_recs[n]["uv_layers"]]}
    for n in LODS + [HULL]}
result["sockets_vs_pre_maint"] = {n: float(np.abs(np.array(snap_objs[n].matrix_basis) - new_sock[n]).max())
                                  for n in SOCKETS}
result["material_export_scalars"] = {"pre_maint": snap_mat, "now": new_mat,
                                     "scalars_identical": {k: snap_mat[k] == new_mat[k]
                                                           for k in ("base_color", "metallic", "roughness")}}
result["eight_point_objects_in_blend"] = eight_objects

bpy.ops.wm.read_factory_settings(use_empty=True)
rev2_objs = append_objects(REV2_BLEND, [LODS[0], HULL] + SOCKETS)
rev2_lod0 = mesh_record(rev2_objs[LODS[0]])
result["lod0_vs_rev2"] = {**{k: same(rev2_lod0[k], new_recs[LODS[0]][k]) for k in GEOMETRY_KEYS},
                          "uv0": same(rev2_lod0["uv"], new_recs[LODS[0]]["uv"])}
result["hull_vs_rev2"] = same(mesh_record(rev2_objs[HULL])["verts"], new_recs[HULL]["verts"])
result["sockets_vs_rev2"] = {n: float(np.abs(np.array(rev2_objs[n].matrix_basis) - new_sock[n]).max())
                             for n in SOCKETS}

# ------------------------------------------------------------------ FBX + sidecar
fbx_snap, fbx_new = fbx_record(SNAP / "export" / f"{FOUR}.fbx"), fbx_record(EXPORTS / f"{FOUR}.fbx")
fbx = {"nodes": [sorted(fbx_snap), sorted(fbx_new)], "meshes": {}}
for name in sorted(set(fbx_snap) | set(fbx_new)):
    a, b = fbx_snap.get(name), fbx_new.get(name)
    if not a or not b or a.get("type") != "MESH":
        continue
    fbx["meshes"][name] = {"triangles": [a["triangles"], b["triangles"]], "vertices": [a["vertices"], b["vertices"]],
                           "uv_layers": [a["uv_layers"], b["uv_layers"]],
                           "sorted_vertex_max_abs_diff_m": float(np.abs(sorted_rows(a["co"]) - sorted_rows(b["co"])).max())
                           if a["co"].shape == b["co"].shape else None}
result["four_point_fbx_vs_pre_maint"] = fbx
side_snap = json.loads((SNAP / "export" / f"{FOUR}.sockets.json").read_text(encoding="utf-8"))
side_new = json.loads((EXPORTS / f"{FOUR}.sockets.json").read_text(encoding="utf-8"))
result["four_point_sidecar"] = {
    "sockets_identical": side_snap["sockets"] == side_new["sockets"],
    "lod_screen_sizes": [side_snap.get("lod_screen_sizes"), side_new.get("lod_screen_sizes")],
    "other_keys_identical": {k: side_snap.get(k) == side_new.get(k) for k in set(side_snap) | set(side_new)
                             if k not in ("sockets", "lod_screen_sizes")},
}
fbx8 = fbx_record(EXPORTS / f"{EIGHT}.fbx")
sizes = {}
for name, rec in fbx8.items():
    if rec.get("type") == "MESH":
        co = rec.pop("co")
        rec["size_mm"] = [round(float(v) * 1000, 5) for v in (co.max(axis=0) - co.min(axis=0))]
lod8 = [fbx8.get(f"{EIGHT}_LOD{i}", {}).get("triangles") for i in range(3)]
result["eight_point_fbx"] = {"nodes": fbx8, "lod_triangles_fbx": lod8, "lod_triangles_report": new8["lod_triangles"],
                             "pass": bool(lod8 == new8["lod_triangles"] and f"UCX_{EIGHT}_LOD0_00" in fbx8
                                          and not any(k.startswith("SOCKET_") for k in fbx8)
                                          and all(abs(a - b) < 1e-3 for a, b in
                                                  zip(fbx8[f"{EIGHT}_LOD0"]["size_mm"], (100.0, 100.0, 2.5))))}
result["sha256"] = {f"{m}.{ext}": sha(EXPORTS / f"{m}.{ext}") for m in (FOUR, EIGHT) for ext in ("fbx", "sockets.json")}

# ------------------------------------------------------------------ renders (expected to change)
result["renders_vs_pre_maint"] = {
    f"{form}_{shot}": png_diff(SNAP / "renders" / f"{form}_{shot}.png", RENDERS / f"{form}_{shot}.png")
    for form in ("four_point", "eight_point") for shot in ("persp", "top", "wire", "lods")}

# ------------------------------------------------------------------ eight-point before / after
result["eight_point_before_after"] = {
    "lod_triangles": [snap8["lod_triangles"], new8["lod_triangles"]],
    "measured": {k: [snap8["measured"].get(k), new8["measured"].get(k)]
                 for k in ("across_mm", "thickness_mm", "arm_width_mm", "hole_across_flats_mm", "plate_area_mm2",
                           "mass_g", "tip_included_deg", "hole_segments")},
    "lod1_two_sided_mm": [snap8["lod1_is_distinct"]["max_surface_deviation_mm"],
                          new8["lod1_is_distinct"]["max_surface_deviation_mm"]],
    "topology_quality_now": new8.get("topology_quality"),
}

# ------------------------------------------------------------------ verdict
geom_same = all(v["identical"] for rec in result["four_point_vs_pre_maint"].values()
                for k, v in rec.items() if k in GEOMETRY_KEYS)
lod0_uv_same = result["four_point_vs_pre_maint"][LODS[0]]["uv0"]["identical"]
lod0_rev2 = all(v["identical"] for v in result["lod0_vs_rev2"].values())
fbx_same = all(m["sorted_vertex_max_abs_diff_m"] == 0.0 and m["triangles"][0] == m["triangles"][1]
               for m in fbx["meshes"].values()) and fbx["nodes"][0] == fbx["nodes"][1]
result["summary"] = {
    "gate_figures_pass": all(v["pass"] for v in figures.values()),
    "four_point_lod_geometry_and_hull_bitwise_identical_to_pre_maint": geom_same,
    "four_point_lod0_uv_bitwise_identical": lod0_uv_same,
    "four_point_lod0_bitwise_identical_to_rev2": lod0_rev2,
    "hull_identical_to_rev2": result["hull_vs_rev2"]["identical"],
    "socket_matrices_identical": all(v == 0.0 for v in list(result["sockets_vs_pre_maint"].values())
                                     + list(result["sockets_vs_rev2"].values())),
    "four_point_fbx_positions_identical": fbx_same,
    "four_point_sidecar_sockets_identical": result["four_point_sidecar"]["sockets_identical"],
    "material_export_scalars_identical": all(result["material_export_scalars"]["scalars_identical"].values()),
    "eight_point_fbx_pass": result["eight_point_fbx"]["pass"],
    "expected_differences": [
        "four-point LOD1/LOD2 UV0 (transferred from LOD0's islands)",
        f"sidecar lod_screen_sizes {result['four_point_sidecar']['lod_screen_sizes']}",
        "every gallery PNG (rig fixes, baked-texture beauty shots, labelled LOD strip)",
        f"M_Shuriken_Master nodes {snap_mat['nodes']} -> {new_mat['nodes']} (wear, scratches; export scalars equal)",
    ],
}
result["passed"] = all(v for k, v in result["summary"].items() if k != "expected_differences")
OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
print("MAINT_REGRESSION " + json.dumps(result["summary"]) + " passed=" + str(result["passed"]))
