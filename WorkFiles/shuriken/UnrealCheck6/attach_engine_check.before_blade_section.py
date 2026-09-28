"""Attach the UnrealCheck6 result to each build report - only if it verified THESE bytes.

Plain Python (no Blender, no Unreal):   py WorkFiles/shuriken/UnrealCheck6/attach_engine_check.py [form ...]
(no forms named: every pack form in FORMS whose pass files exist)

For each form it reads <form>_pass1/2/3.json and their logs plus roundtrip_compare.json, and checks
that the SHA-256 of the FBX and sidecar Unreal imported (pass 1) equals both the build report's
export_sha256 and the file on disk now.  Only then does it write engine_check.status = "verified"
and matches_this_build = true into WorkFiles/shuriken/<form>_report.json (and remove the
"ENGINE CHECK PENDING" gap); otherwise it writes "failed" with the reason.  It also updates
pack_report.json and writes verification_summary.json next to this file.  The build writes
engine_check as "pending"; this script is the only thing that promotes it.
"""
import hashlib
import json
import re
import time
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck6"
REPORTS = PROJ / "WorkFiles" / "shuriken"
FORMS = ("four_point", "eight_point", "square_plate", "six_point", "spike", "hooked_cross", "kunai_plain")
PART_HULLS = {"kunai_plain": 2}      # 3.10: forms with several part hulls (the union must contain LOD0)
PATTERN = re.compile(r":\s*(Warning|Error)\s*:")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def log_problems(path):
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return [line for line in lines if PATTERN.search(line)]


def stamp(path):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(Path(path).stat().st_mtime))


def main():
    import sys
    wanted = sys.argv[1:] or [f for f in FORMS if all((HERE / f"{f}_pass{i}.json").exists() for i in (1, 2, 3))]
    roundtrip = json.loads((HERE / "roundtrip_compare.json").read_text(encoding="utf-8"))
    summary = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "project":
               str(REPORTS / "UnrealShuriken" / "ShurikenValidation.uproject"), "forms": {}}
    for form in wanted:
        report_path = REPORTS / f"{form}_report.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        pass1 = json.loads((HERE / f"{form}_pass1.json").read_text(encoding="utf-8"))
        pass2 = json.loads((HERE / f"{form}_pass2.json").read_text(encoding="utf-8"))
        pass3 = json.loads((HERE / f"{form}_pass3.json").read_text(encoding="utf-8"))
        logs = {name: log_problems(HERE / f"{form}_{name}.log") for name in ("pass1", "pass2", "pass3")}
        fbx, sidecar = Path(report["fbx"]), Path(report["sockets_sidecar"])
        hashes = {
            "report": report.get("export_sha256") or {},
            "imported_by_unreal": {"fbx": pass1.get("fbx_sha256"), "sidecar": pass1.get("sidecar_sha256")},
            "on_disk_now": {"fbx": sha256(fbx), "sidecar": sha256(sidecar)},
        }
        same_bytes = (hashes["report"].get("fbx") == hashes["imported_by_unreal"]["fbx"] == hashes["on_disk_now"]["fbx"]
                      and hashes["report"].get("sidecar") == hashes["imported_by_unreal"]["sidecar"]
                      == hashes["on_disk_now"]["sidecar"])
        rt = roundtrip.get(form, {})
        lods = rt.get("lods", {})
        hulls = list((rt.get("unreal_hulls") or {}).values())
        lods_ok = bool(
            lods and all(e.get("position_two_sided_max_cm", 1.0) <= 1e-5
                         and e.get("unreal_tris") == e.get("shipped_tris")
                         and (e.get("uv0_keyed_position_check") or {}).get("max_position_diff_cm", 1.0) <= 1e-5
                         and (e.get("uv1_lightmap") or {}).get("inside_0_1")
                         and (e.get("uv1_lightmap_2048") or {}).get("overlap_pixels", 1) == 0
                         for e in lods.values()))
        if form in PART_HULLS:
            part = rt.get("part_hulls") or {}
            roundtrip_ok = bool(lods_ok and len(part.get("unreal") or []) == PART_HULLS[form]
                                and part.get("distinct_unreal_hulls_matched") == PART_HULLS[form]
                                and (part.get("union_lod0_max_outside_cm") if part.get("union_lod0_max_outside_cm")
                                     is not None else 1.0) <= 1e-5
                                and rt.get("hull_shipped_vs_unreal_two_sided_max_cm", 1.0) <= 1e-5)
        else:
            roundtrip_ok = bool(lods_ok and len(hulls) == 1 and hulls[0].get("lod0_max_outside_cm", 1.0) <= 1e-5
                                and rt.get("hull_shipped_vs_unreal_two_sided_max_cm", 1.0) <= 1e-5)
        gates = dict(pass2.get("gates") or {})
        gates["7_zero_warning_error_log_lines"] = all(v == [] for v in logs.values())
        gates["8_unreal_export_roundtrip_hull_positions_uv"] = roundtrip_ok
        gates["9_verified_bytes_are_this_build"] = same_bytes
        verified = bool(pass2.get("passed_1_to_6")) and all(gates.values())
        check = dict(report.get("engine_check") or {})
        check.update({
            "status": "verified" if verified else "failed",
            "matches_this_build": verified,
            "engine": pass2.get("engine"),
            "attached_by": str(HERE / "attach_engine_check.py"),
            "attached": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "gates_passed": gates,
            "sha256": hashes,
            "pass2": {
                "file_time": stamp(HERE / f"{form}_pass2.json"),
                "asset": pass2.get("asset"),
                "lod_triangles": pass2.get("lod_triangles"),
                "lod_vertices": pass2.get("lod_vertices"),
                "triangle_delta": (pass2.get("gate_detail") or {}).get("triangle_delta"),
                "lod_screen_sizes": pass2.get("lod_screen_sizes"),
                "convex_hulls": pass2.get("convex_hulls"),
                "size_cm": pass2.get("size_cm"),
                "sockets": pass2.get("sockets"),
                "light_map_coordinate_index": pass2.get("light_map_coordinate_index"),
                "light_map_resolution": pass2.get("light_map_resolution"),
                "material_slots": pass2.get("material_slots"),
                **({"kunai": {k: pass2["kunai"].get(k) for k in ("passed", "slots", "lod_sections", "rect_unreal", "lods",
                                                                 "allow_cpu_access_saved", "dirty_packages_before",
                                                                 "dirty_packages_after")}}
                   if "kunai" in pass2 else {}),
                **({"handedness": pass2["handedness"]} if "handedness" in pass2 else {}),
                # 3.9.1: the render-data gate of every LOD (gates 11, 12), condensed
                **({"handedness_render": {
                    "passed": pass2["handedness_render"].get("passed"),
                    "texture_sheets_passed": pass2["handedness_render"].get("texture_sheets_passed"),
                    "negative_control": pass2["handedness_render"].get("negative_control"),
                    "dirty_packages_before_after": [pass2["handedness_render"].get("dirty_packages_before"),
                                                    pass2["handedness_render"].get("dirty_packages_after")],
                    "allow_cpu_access_saved": pass2["handedness_render"].get("allow_cpu_access_saved"),
                    "lods": {k: {kk: v.get(kk) for kk in ("passed", "build_scale3d", "build_reversed_index_buffer",
                                                         "triangles", "winding_agrees_with_normals_unreal_rule",
                                                         "position_max_cm_documented_conversion",
                                                         "position_max_cm_if_mirrored", "texture_sheets",
                                                         "viewer_below_accepted_back_face")}
                             | {"viewer_above_reads": v["viewer_above"].get("reads"),
                                "tip_offsets_ccw_deg": [t.get("offset_ccw_deg") for t in v["viewer_above"].get("tips") or []]}
                             for k, v in pass2["handedness_render"].get("lods", {}).items()},
                }} if "handedness_render" in pass2 else {}),
            },
            "roundtrip": {"lods": {k: {"position_two_sided_max_cm": v.get("position_two_sided_max_cm"),
                                        "uv0_keyed_max_cm": (v.get("uv0_keyed_position_check") or {}).get(
                                            "max_position_diff_cm"),
                                        "uv1_overlap_pixels_2048": (v.get("uv1_lightmap_2048") or {}).get(
                                            "overlap_pixels")} for k, v in lods.items()},
                          "unreal_hull": hulls[0] if hulls else None,
                          **({"part_hulls": rt.get("part_hulls")} if rt.get("part_hulls") else {}),
                          "hull_vs_shipped_two_sided_cm": rt.get("hull_shipped_vs_unreal_two_sided_max_cm")},
            "pass3_export": {k: pass3.get(k) for k in ("export_ok", "fbx_out", "fbx_bytes")},
            "log_warning_error_lines": {k: (len(v) if v is not None else None) for k, v in logs.items()},
            "evidence": [str(HERE / f"{form}_pass{i}.{ext}") for i in (1, 2, 3) for ext in ("json", "log")]
            + [str(HERE / "roundtrip_compare.json"), str(HERE / "blender_fbx_counts.json")],
        })
        if form in PART_HULLS:
            # 3.10 kunai: the build's "pending" block lists the stars' gate text (one hull, two sockets); describe the
            # gates this form was actually held to (gate 2 counts its part hulls, gate 3 all its sockets, gate 13)
            names = sorted(s.get("name") for s in (pass2.get("sockets") or []))
            check["gates"] = [
                "engine LOD triangle counts equal the Blender counts exactly",
                f"LOD screen sizes read back as {pass2.get('lod_screen_sizes')} in a fresh process",
                f"exactly {PART_HULLS[form]} convex hulls; the sockets {', '.join(names)} at relative scale 1; bounds "
                "equal the measured size",
                "LightMapCoordinateIndex 1 with a generated UV1 on every LOD",
                "two material sections on every LOD (steel in UV tile u 0..1, wrap in u 1..2) and the lettering band's "
                "triangles on +Z inside its UV rectangle with U toward +X in the render data of every LOD",
                "Unreal's own FBX export of the saved asset: every hull, the positions and UV-keyed positions equal the "
                "shipped FBX, and the hulls' union contains LOD0",
                "zero Warning or Error lines in the commandlet logs"]
        if not verified:
            check["reason"] = {k: v for k, v in gates.items() if not v}
        report["engine_check"] = check
        gaps = [g for g in report.get("known_gaps", []) if not g.startswith("ENGINE CHECK PENDING")]
        if not verified:
            gaps.append(f"ENGINE CHECK FAILED: {check.get('reason')} (UnrealCheck6).")
        report["known_gaps"] = gaps
        report_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")
        summary["forms"][form] = {"verified": verified, "gates": gates, "sha256": hashes}
        print(f"{form}: {'VERIFIED' if verified else 'FAILED'} {gates}")

    pack_path = REPORTS / "pack_report.json"
    pack = json.loads(pack_path.read_text(encoding="utf-8"))
    for form, result in summary["forms"].items():
        if form in pack.get("results", {}):
            pack["results"][form]["engine_check_status"] = "verified" if result["verified"] else "failed"
    pack["engine_checks_verified"] = all(r["verified"] for r in summary["forms"].values())
    pack_path.write_text(json.dumps(pack, indent=2, sort_keys=False), encoding="utf-8")
    (HERE / "verification_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
