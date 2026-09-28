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
FORMS = ("four_point", "eight_point", "square_plate")
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
        roundtrip_ok = bool(
            lods and all(e.get("position_two_sided_max_cm", 1.0) <= 1e-5
                         and e.get("unreal_tris") == e.get("shipped_tris")
                         and (e.get("uv0_keyed_position_check") or {}).get("max_position_diff_cm", 1.0) <= 1e-5
                         and (e.get("uv1_lightmap") or {}).get("inside_0_1")
                         and (e.get("uv1_lightmap_2048") or {}).get("overlap_pixels", 1) == 0
                         for e in lods.values())
            and len(hulls) == 1 and hulls[0].get("lod0_max_outside_cm", 1.0) <= 1e-5
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
            },
            "roundtrip": {"lods": {k: {"position_two_sided_max_cm": v.get("position_two_sided_max_cm"),
                                        "uv0_keyed_max_cm": (v.get("uv0_keyed_position_check") or {}).get(
                                            "max_position_diff_cm"),
                                        "uv1_overlap_pixels_2048": (v.get("uv1_lightmap_2048") or {}).get(
                                            "overlap_pixels")} for k, v in lods.items()},
                          "unreal_hull": hulls[0] if hulls else None,
                          "hull_vs_shipped_two_sided_cm": rt.get("hull_shipped_vs_unreal_two_sided_max_cm")},
            "pass3_export": {k: pass3.get(k) for k in ("export_ok", "fbx_out", "fbx_bytes")},
            "log_warning_error_lines": {k: (len(v) if v is not None else None) for k, v in logs.items()},
            "evidence": [str(HERE / f"{form}_pass{i}.{ext}") for i in (1, 2, 3) for ext in ("json", "log")]
            + [str(HERE / "roundtrip_compare.json"), str(HERE / "blender_fbx_counts.json")],
        })
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
