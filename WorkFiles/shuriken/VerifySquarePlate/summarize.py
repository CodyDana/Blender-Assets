"""Combine the verifier's evidence into <form>_verify_summary.json (plain Python: py summarize.py).

Read-only with respect to the build: it never writes the build report, pack_report.json or UnrealCheck6.
Gates 1-6 come from the fresh-process pass 2; 7 from every commandlet log of this verification; 8 from the
Blender round trip of Unreal's own export; 9 from the SHA-256 recorded at every step.
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vsp_config as V  # noqa: E402

S = V.spec()
H = V.HERE
PAT = re.compile(V.LOG_PATTERN)


def load(name):
    p = H / name
    return json.loads(p.read_text(encoding="utf-8-sig")) if p.exists() else None


def log_lines(name):
    p = H / name
    if not p.exists():
        return None
    return [ln for ln in p.read_text(encoding="utf-8", errors="replace").splitlines() if PAT.search(ln)]


def main():
    f = V.FORM
    bfbx, bblend = load("vsp_blender_fbx.json"), load("vsp_blender_blend.json")
    p1, p2, p3 = load(f"{f}_vpass1.json"), load(f"{f}_vpass2.json"), load(f"{f}_vpass3.json")
    p2b, neg = load(f"{f}_vpass2_after_pass3.json"), load(f"{f}_vpass2_negctl_side76.json")
    rt = load(f"{f}_roundtrip.json")
    runs = {n: load(f"{f}_{n}.run.json") for n in ("vpass1", "vpass2", "vpass3", "vpass2_after_pass3", "vpass2_negctl_side76")}
    report = json.loads((V.PROJ / "WorkFiles" / "shuriken" / f"{f}_report.json").read_text(encoding="utf-8"))
    logs = {n: log_lines(f"{f}_{n}.log") for n in runs}
    on_disk = {"fbx": V.sha256(S["fbx"]), "sidecar": V.sha256(S["sidecar"])}
    hashes = {
        "on_disk_now": on_disk,
        "build_report_export_sha256": {k: report["export_sha256"].get(k) for k in ("fbx", "sidecar")},
        "blender_reimport": {"fbx_before": bfbx["fbx_sha256_before_import"], "fbx_after": bfbx["fbx_sha256_after_import"],
                             "sidecar": bfbx["sidecar_sha256"]},
        "unreal_pass1_before_import": p1["sha256_before_import"], "unreal_pass1_after_import": p1["sha256_after_import"],
        "unreal_pass2_fresh_process": p2["sha256_now"], "roundtrip_shipped_fbx": rt["shipped_fbx_sha256"],
    }
    fbx_all = {on_disk["fbx"], hashes["build_report_export_sha256"]["fbx"], bfbx["fbx_sha256_before_import"],
               bfbx["fbx_sha256_after_import"], p1["sha256_before_import"]["fbx"], p1["sha256_after_import"]["fbx"],
               p2["sha256_now"]["fbx"], rt["shipped_fbx_sha256"]}
    side_all = {on_disk["sidecar"], hashes["build_report_export_sha256"]["sidecar"], bfbx["sidecar_sha256"],
                p1["sha256_before_import"]["sidecar"], p1["sha256_after_import"]["sidecar"], p2["sha256_now"]["sidecar"]}
    uassets = {runs[n]["uasset_sha256_after"] for n in runs if runs[n]} | {
        runs[n]["uasset_sha256_before"] for n in runs if runs[n] and n != "vpass1"}
    gates = dict(p2["gates"])
    gates["7_zero_warning_error_log_lines"] = all(v == [] for v in logs.values()) and all(
        r and r["exit"] == 0 and r["stderr_bytes"] == 0 for r in runs.values())
    gates["8_unreal_export_roundtrip_hull_positions_uv"] = bool(rt["passed"])
    gates["9_verified_bytes_are_this_build"] = len(fbx_all) == 1 and len(side_all) == 1 and len(uassets) == 1
    out = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "form": f, "mesh": S["mesh"], "engine": p2["engine"],
        "project": str(V.UPROJECT), "content_path": S["asset"], "build_agent_content_path_not_used": V.BUILD_AGENT_DEST,
        "verified": all(gates.values()), "gates": gates, "sha256": hashes,
        "fbx_sha256": on_disk["fbx"], "sidecar_sha256": on_disk["sidecar"],
        "uasset_sha256_constant_across_passes_2_3": sorted(uassets),
        "processes": {n: {k: r[k] for k in ("pid", "exit", "start", "end", "log_lines", "warning_error_lines", "stderr_bytes")}
                      for n, r in runs.items() if r},
        "readback_fresh_process": {
            "lod_triangles": p2["inspect"]["lod_triangles"], "lod_vertices": p2["inspect"]["lod_vertices"],
            "blender_fbx_reimport_lod_triangles": bfbx["lod_triangles"], "blender_blend_lod_triangles": bblend["lod_triangles"],
            "build_report_lod_triangles": report["lod_triangles"],
            "lod_screen_sizes": p2["inspect"]["lod_screen_sizes"], "lod_screen_sizes_raw": p2["extra"]["lod_screen_sizes_raw"],
            "expected_screen_sizes_from_study": S["screen_sizes"],
            "bounds_sphere_radius_cm": p2["extra"]["bounds_sphere_radius_cm"],
            "switch_distance_cm": p2["gate_detail"]["switch_distance_cm"],
            "size_cm": p2["gate_detail"]["size_cm_6dp"], "expected_size_cm": [round(v, 6) for v in S["size_cm"]],
            "bounds_min_cm": p2["extra"]["bounding_box_min_cm_6dp"], "bounds_max_cm": p2["extra"]["bounding_box_max_cm_6dp"],
            "convex_hulls": p2["inspect"]["convex_hulls"], "other_collision_elems": p2["inspect"]["other_collision_elems"],
            "collision_trace_flag": p2["inspect"]["collision_trace_flag"],
            "sockets": p2["inspect"]["sockets"], "socket_checks": p2["gate_detail"]["socket_checks"],
            "socket_geometry_unreal_frame": p2["extra"]["unreal_frame_geometry"],
            "light_map_coordinate_index": p2["inspect"]["light_map_coordinate_index"],
            "light_map_resolution": p2["inspect"]["light_map_resolution"],
            "lod_build_settings": p2["inspect"]["lod_build_settings"], "lod_build_flags": p2["extra"]["lod_build_flags"],
            "nanite_enabled": p2["inspect"]["nanite_enabled"], "material_slots": p2["inspect"]["material_slots"],
        },
        "roundtrip": {"checks": rt["checks"], "lods": rt["lods"], "unreal_hulls": rt["unreal_hulls"],
                      "shipped_hull": rt["shipped_hull"], "unreal_fbx_sha256": rt["unreal_fbx_sha256"]},
        "uc6_parameterized_gates_same_process": p2["uc6_parameterized_gates"],
        "after_pass3_readback_passed": p2b and p2b["passed_1_to_6"],
        "negative_control": neg and {"override": {"side_mm": 76.0}, "gates": neg["gates"],
                                     "expected_to_fail": ["3", "4", "5"], "failed_as_expected":
                                     (not neg["gates"]["3_grip_trail_scale_1_sane_cm"]
                                      and not neg["gates"]["4_bounds_cm_match_spec"]
                                      and not neg["gates"]["5_screen_sizes_applied_from_sidecar"]
                                      and neg["gates"]["1_lod_count_and_triangles_delta_0"])},
        "blender_side": {"fbx_nodes": sorted(bfbx["nodes"]), "socket_nodes_in_fbx": bfbx["socket_nodes_in_fbx"],
                         "ucx_name_matches_lod0_node": bfbx["ucx_name_matches_lod0_node"],
                         "shipped_hull": {k: v for k, v in bfbx["shipped_hull"].items() if k != "verts_cm"},
                         "lod0_geometry_cm": bfbx["lod0_geometry_cm"], "blend_is_dirty_after_load": bblend["is_dirty_after_load"],
                         "blend_socket_empties": bblend["socket_empties"]},
        "log_warning_error_lines": {n: (len(v) if v is not None else None) for n, v in logs.items()},
    }
    (H / f"{f}_verify_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"{f}: {'VERIFIED' if out['verified'] else 'FAILED'} {gates}")


main()
