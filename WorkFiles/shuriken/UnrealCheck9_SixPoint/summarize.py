"""UnrealCheck9 summary (system Python): gather s1/s2/s3/s3b/s4 + b_compare into verification_summary.json.

    py WorkFiles/shuriken/UnrealCheck9_SixPoint/summarize.py
"""
import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[2]
MESH = "SM_Shuriken_SixPoint"


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


STRICT = re.compile(r":\s*(Warning|Error)\s*:")
LOOSE = re.compile(r"(warning|error)", re.IGNORECASE)


def scan(log):
    lines = (HERE / log).read_text(encoding="utf-8", errors="replace").splitlines()
    strict = [ln for ln in lines if STRICT.search(ln)]
    loose = [ln for ln in lines if LOOSE.search(ln) and "0 error(s), 0 warning(s)" not in ln
             and not re.search(r"Failed to load '.*\.dll'", ln)]
    stderr = HERE / (log + ".stderr")
    err_lines = stderr.read_text(encoding="utf-8", errors="replace").splitlines() if stderr.exists() else []
    summary = [ln for ln in lines if "error(s)" in ln and "warning(s)" in ln]
    return {"lines": len(lines), "strict_warning_error": len(strict), "loose_mentions": len(loose),
            "stderr_lines": len(err_lines), "summary_line": summary[-1].split("]")[-1].strip() if summary else None,
            "examples": (strict + loose)[:5]}


def main():
    s1, s3, s4, b = load("s1_import.json"), load("s3_readback.json"), load("s4_export.json"), load("b_compare.json")
    t_imp, t_ver = load("s2_textures_import.json"), load("s3b_textures_verify.json")
    report = load(str(Path("..") / "six_point_report.json"))
    fbx = PROJ / "Exports" / "Shuriken" / f"{MESH}.fbx"
    side = PROJ / "Exports" / "Shuriken" / f"{MESH}.sockets.json"
    now = {"fbx": sha256(fbx), "sidecar": sha256(side)}
    logs = {k: scan(f"{k}.log") for k in ("s1", "s2", "s3", "s3b", "s4")}
    m = s3["mesh"]
    r = m["sphere_bounds"]["sphere_radius_cm"]
    ss = m["lod_screen_sizes_render_data"]
    # 90 deg horizontal FOV on 16:9: screen size = 2 * 0.5 * (16/9) * r / d  ->  d = (16/9) r / s
    switch_m = [round((16.0 / 9.0) * r / s / 100.0, 4) for s in ss[1:]]
    gates = {
        "bytes_sha256_imported_eq_disk_eq_report": (s1["fbx_sha256_before"] == s1["fbx_sha256_after"] == now["fbx"]
                                                    == report["export_sha256"]["fbx"]
                                                    and s1["sidecar_sha256_before"] == now["sidecar"]
                                                    == report["export_sha256"]["sidecar"]),
        "unreal_stored_md5_eq_shipped_fbx": bool(s3.get("mesh_import_md5_matches_shipped")),
        "fresh_content_path": s1["dest_existed_before"] is False and s1["asset_existed_before"] is False,
        "lod_count_3_triangles_eq_blender": s3["gates"]["G1_three_lods"] and b["R2_lods"]["ok"],
        "exactly_one_convex_hull": s3["gates"]["G2_exactly_one_convex_hull"],
        "stored_hull_eq_shipped_ucx_lod0_0cm_outside": b["R1_hull"]["ok"],
        "grip_trail_scale_1_sane_cm": s3["gates"]["G3_grip_trail_scale_1_spec_cm"] and b["R4_sockets"]["ok"],
        "bounds_cm_eq_spec": s3["gates"]["G4_bounds_cm_match_spec_centred"] and b["R5_tips"]["ok"],
        "lod_screen_sizes_applied": s3["gates"]["G5_lod_screen_sizes"],
        "lightmap_index_1_uv1_0_1_no_overlap": s3["gates"]["G6_lightmap_index_1"] and b["R3_uv1"]["ok"],
        "textures_bc_srgb_orm_linear_masks_n_linear_normal": (all(t["ok"] for t in s3["textures"].values())
                                                             and t_ver["passed"] is True and t_imp["passed"] is True),
        "zero_warning_error_lines": all(v["strict_warning_error"] == 0 and v["loose_mentions"] == 0
                                        and v["stderr_lines"] == 0 for v in logs.values()),
        "export_roundtrip_ok": s4.get("export_ok") is True,
    }
    out = {
        "asset": s1["asset"], "engine": s3["engine"],
        "sha256": {"fbx": now["fbx"], "sidecar": now["sidecar"],
                   "maps": {k: v["shipped_sha256"] for k, v in s3["textures"].items()},
                   "unreal_reexport_fbx": s4.get("sha256")},
        "fbx_md5_stored_by_unreal": (m["registry_import_tag"].get("parsed") or [{}])[0].get("FileMD5"),
        "gates": gates, "passed": all(gates.values()),
        "readback": {"lod_triangles": m["lod_triangles"], "lod_vertices": m["lod_vertices"],
                     "lod_screen_sizes": ss, "auto_computed": m["is_lod_screen_size_auto_computed"],
                     "convex_hulls": m["convex_hulls"], "other_collision": m["other_collision_elems"],
                     "size_cm": m["size_cm"], "bounds_min_cm": m["bounds_min_cm"], "bounds_max_cm": m["bounds_max_cm"],
                     "sphere_radius_cm": r, "lod_switch_m_90hfov_16x9": switch_m,
                     "sockets": m["component_sockets"], "socket_outers": {k: v.get("outer") for k, v in m["socket_objects"].items()},
                     "light_map_coordinate_index": m["light_map_coordinate_index"],
                     "light_map_resolution": m["light_map_resolution"], "nanite": m["nanite_enabled"],
                     "material_slots": m["material_slots"], "default_instance_mass": m.get("default_instance_mass"),
                     "textures": {k: {kk: v["info"][kk] for kk in ("srgb", "compression_settings", "flip_green_channel",
                                                                    "lod_group", "size")} for k, v in s3["textures"].items()}},
        "hull": {k: b["R1_hull"][k] for k in ("shipped_hull_nodes", "unreal_hull_nodes", "shipped", "unreal",
                                              "vertex_sets_equal_1e-5cm", "two_sided_vertex_distance_cm",
                                              "lod_max_outside_unreal_hull_cm", "lod0_outside_cm_rounded_1dp")},
        "uv1": [{k: p[k] for k in ("lod", "u_range", "v_range", "overlapping_pairs", "overlap_area_total",
                                   "zero_area_triangles", "charts", "texels_covered_by_two_charts")} for p in b["R3_uv1"]["per_lod"]],
        "uv1_negative_control": b["R3_uv1"]["negative_control_lod0"],
        "blender_truth_tris": b["R2_lods"]["blend_tris"], "shipped_fbx_tris": b["R2_lods"]["shipped_fbx_tris"],
        "position_roundtrip_cm": [p["two_sided_position_cm"] for p in b["R2_lods"]["per_lod"]],
        "render_vertices_vs_hard_edge_estimate": [(p["unreal_render_vertices"], p["render_vertex_estimate_from_shipped"])
                                                  for p in b["R2_lods"]["per_lod"]],
        "grip": {k: b["R4_sockets"]["Grip"][k] for k in ("radius_cm", "polar_deg_blender", "distance_to_lod0_surface_cm",
                                                          "x_axis_dot_outward_normal", "delta_to_blend_empty_cm")},
        "tips": b["R5_tips"],
        "logs": logs,
        "notes": [
            "s3 was run twice. Run 1 (s3_run1_selfwarning.log) logged 1 unique Python DeprecationWarning raised by "
            "this verifier's OWN call site (new_object(StaticMeshEditorSubsystem) in __main__); the asset is not "
            "involved. The helper was moved to u9_common.py (same fallback the pipeline uses) and s3 re-run in a fresh "
            "process: 0 Warning/Error lines. Gate values were identical in both runs.",
        ],
    }
    (HERE / "verification_summary.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("U9_SUMMARY passed=%s" % out["passed"])
    for k, v in gates.items():
        print(f"  {k}: {v}")


main()
