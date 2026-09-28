"""Attach the Unreal result to the build report - only if it verified THESE bytes.

Plain Python (no Blender, no Unreal):

    py WorkFiles/paperbomb/UnrealCheck/attach_engine_check.py

Reads pass1/2/3.json and their logs plus roundtrip_compare.json and blender_fbx_counts.json,
and checks that the SHA-256 of the FBX and the sidecar Unreal actually imported (pass 1)
equals BOTH the build report's export_sha256 AND the file on disk now.  Only then does it
write ``engine_check.status = "verified"`` into WorkFiles/paperbomb/paperbomb_report.json.
The build writes nothing about the engine; this script is the only thing that promotes it,
and it is deliberately a separate process from anything that could have produced the bytes.
"""
import hashlib
import json
import re
import time
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "paperbomb" / "UnrealCheck"
REPORT_PATH = PROJ / "WorkFiles" / "paperbomb" / "paperbomb_report.json"
PATTERN = re.compile(r":\s*(Warning|Error)\s*:")
#: log lines that are about the commandlet's own environment, not the asset
LOG_IGNORE = (
    "HIPEW initialization failed",
    "Failed to load Vulkan",
    "LogD3D12RHI",
    "GPU",
    "No SSL",
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def log_problems(path):
    """Warning/Error lines, and how many the environment filter removed.

    The filter is reported as well as applied, so it cannot quietly hide anything: on
    this build it removed nothing at all, because the three commandlets emitted zero
    Warning or Error lines between them.
    """
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None, None
    hits = [line for line in lines if PATTERN.search(line)]
    kept = [line for line in hits if not any(skip in line for skip in LOG_IGNORE)]
    return kept, len(hits) - len(kept)


def main():
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    fbx = PROJ / report["export"]["fbx"]
    sidecar = PROJ / report["export"]["sockets_sidecar"]

    def load(name):
        path = HERE / name
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    pass1, pass2, pass3 = load("pass1.json"), load("pass2.json"), load("pass3.json")
    roundtrip = load("roundtrip_compare.json")
    counts = load("blender_fbx_counts.json")
    raw = {name: log_problems(HERE / f"{name}.log") for name in ("pass1", "pass2", "pass3")}
    logs = {k: v[0] for k, v in raw.items()}
    filtered_out = {k: v[1] for k, v in raw.items()}

    hashes = {
        "build_report": report["export"]["sha256"],
        "imported_by_unreal": {"fbx": pass1.get("fbx_sha256"), "sidecar": pass1.get("sidecar_sha256")},
        "reread_by_pass2": {"fbx": pass2.get("fbx_sha256"), "sidecar": pass2.get("sidecar_sha256")},
        "on_disk_now": {"fbx": sha256(fbx), "sidecar": sha256(sidecar)},
        "reimported_by_blender": counts.get("sha256"),
    }
    same_bytes = bool(
        hashes["build_report"]["fbx"] == hashes["imported_by_unreal"]["fbx"]
        == hashes["reread_by_pass2"]["fbx"] == hashes["on_disk_now"]["fbx"]
        == hashes["reimported_by_blender"]
        and hashes["build_report"]["sidecar"] == hashes["imported_by_unreal"]["sidecar"]
        == hashes["on_disk_now"]["sidecar"])

    gates = dict(pass2.get("gates") or {})
    gates["12_unreal_reexport_roundtrip"] = bool(roundtrip.get("passed"))
    gates["13_zero_warning_error_log_lines"] = all(v == [] for v in logs.values() if v is not None)
    gates["14_verified_bytes_are_this_build"] = same_bytes
    verified = bool(pass2.get("passed_all")) and all(gates.values())

    report["engine_check"] = {
        "status": "verified" if verified else "failed",
        "matches_this_build": same_bytes,
        "engine": pass2.get("engine") or pass1.get("engine"),
        "project": str(PROJ / "WorkFiles" / "shuriken" / "UnrealShuriken" / "ShurikenValidation.uproject"),
        "content_path": pass2.get("asset"),
        "attached": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "attached_by": str(Path(__file__)),
        "gates_passed": gates,
        "sha256": hashes,
        "read_in_a_fresh_process": {
            "lod_triangles": pass2.get("lod_triangles"),
            "lod_screen_sizes": pass2.get("lod_screen_sizes"),
            "convex_hulls": pass2.get("convex_hulls"),
            "size_cm": pass2.get("size_cm"),
            "sockets": pass2.get("sockets"),
            "textures": {k: v.get("matches") for k, v in (pass2.get("textures") or {}).items()},
            "uv": pass2.get("uv"),
            "hull": pass2.get("hull"),
        },
        "roundtrip": {"lods": roundtrip.get("lods"), "hull": roundtrip.get("hull"),
                      "passed": roundtrip.get("passed")},
        "pass3_export": {k: pass3.get(k) for k in ("export_ok", "fbx_out", "fbx_bytes")},
        "log_warning_error_lines": {k: (len(v) if v is not None else None) for k, v in logs.items()},
        "log_lines_removed_by_the_environment_filter": filtered_out,
        "environment_filter": list(LOG_IGNORE),
        "log_lines": {k: v[:20] for k, v in logs.items() if v},
        "evidence": [str(HERE / n) for n in ("pass1.json", "pass2.json", "pass3.json",
                                             "roundtrip_compare.json", "blender_fbx_counts.json",
                                             "pass1.log", "pass2.log", "pass3.log")],
    }
    if not verified:
        report["engine_check"]["reason"] = {k: v for k, v in gates.items() if not v}
        if not pass2.get("passed_all"):
            report["engine_check"]["reason"]["pass2_gates"] = {
                k: v for k, v in (pass2.get("gates") or {}).items() if not v}

    gaps = [g for g in report.get("known_gaps", []) if not g.startswith("ENGINE CHECK")]
    if not verified:
        gaps.append(f"ENGINE CHECK FAILED: {report['engine_check'].get('reason')}")
    report["known_gaps"] = gaps
    report.setdefault("gates", {})["20_unreal_verified_on_the_exported_bytes"] = verified
    report["gates"]["_all"] = all(v for k, v in report["gates"].items() if not k.startswith("_"))

    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print("VERIFIED" if verified else "FAILED")
    print(json.dumps(gates, indent=2))
    if not verified:
        print(json.dumps(report["engine_check"].get("reason"), indent=2))


if __name__ == "__main__":
    main()
