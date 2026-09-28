"""UnrealCheck8: fold every process's evidence into verification_summary.json (system Python, no Unreal).

  py WorkFiles/shuriken/UnrealCheck8/summarize.py
"""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck8"
EXPORTS = PROJ / "Exports" / "Shuriken"
FORMS = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint",
         "square_plate": "SM_Shuriken_SquarePlate", "six_point": "SM_Shuriken_SixPoint",
         "spike": "SM_Shuriken_Spike"}
STEPS = {"p1": "import 3 FBX + ue_import_sockets.apply_sidecar + save",
         "p2": f"ue_import_textures.py MODE=import ({3 * len(FORMS)} maps)",
         "p3": "FRESH read-back of meshes + textures (gates M1-M7, T)",
         "p3b": "ue_import_textures.py MODE=verify (fresh)",
         "p4": "FRESH export of the saved meshes with LODs + collision"}
STRICT = re.compile(r":\s*(Warning|Error)\s*:")
LOOSE = re.compile(r"(?i)\b(warning|error)\b")
LOOSE_OK = re.compile(r"0 error\(s\), 0 warning\(s\)|Failed to load '.*\.dll'")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def logs():
    out = {}
    for step, what in STEPS.items():
        lines = (HERE / f"{step}.log").read_text(encoding="utf-8", errors="replace").splitlines()
        err = (HERE / f"{step}.log.stderr").read_text(encoding="utf-8", errors="replace").splitlines()
        strict = [l for l in lines if STRICT.search(l)]
        loose = [l for l in lines if LOOSE.search(l) and not LOOSE_OK.search(l)]
        summary = [l for l in lines if "Success - " in l or "error(s)" in l]
        out[step] = {"what": what, "lines": len(lines), "strict_warning_error_lines": len(strict),
                     "loose_warning_error_mentions": len(loose), "stderr_lines": len([e for e in err if e.strip()]),
                     "engine_summary": summary[-1].split("]")[-1].strip() if summary else None,
                     "examples": (strict + loose)[:5]}
    return out


def main():
    p1, p3, rt, truth = load("p1_import.json"), load("p3_readback.json"), load("roundtrip_compare.json"), load("blend_truth.json")
    p2, p3b = load("p2_textures_import.json"), load("p3b_textures_verify.json")
    lg = logs()
    logs_clean = all(v["strict_warning_error_lines"] == 0 and v["loose_warning_error_mentions"] == 0
                     and v["stderr_lines"] == 0 for v in lg.values())
    summary = {"generated": datetime.now().isoformat(timespec="seconds"),
               "verifier": "UnrealCheck8 (independent import verifier, style pass 2 / knife grind, library 3.6.0)",
               "engine": p3["engine"], "project": str(PROJ / "WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject"),
               "content_path": p3["dest"], "logs": lg, "logs_clean": logs_clean, "forms": {}, "textures": {}}
    for form, mesh in FORMS.items():
        rep = json.loads((PROJ / "WorkFiles" / "shuriken" / f"{form}_report.json").read_text(encoding="utf-8"))
        a, r, b = p1["forms"][form], p3["forms"][form], rt[form]
        disk = {"fbx": sha(EXPORTS / f"{mesh}.fbx"), "sidecar": sha(EXPORTS / f"{mesh}.sockets.json")}
        imported = {"fbx": a["fbx_sha256_before"], "sidecar": a["sidecar_sha256_before"]}
        g = dict(r["gates"])
        h = b["hull"]
        g["R1_stored_hull_identical_to_shipped_ucx"] = (h["vertex_sets_equal_1e-5cm"]
                                                       and h["shipped"]["unique_verts"] == h["unreal"]["unique_verts"]
                                                       and h["shipped"]["tris"] == h["unreal"]["tris"]
                                                       and h["two_sided_vertex_distance_cm"] <= 1e-6
                                                       and abs(h["shipped"]["volume_cm3"] - h["unreal"]["volume_cm3"]) <= 1e-5)
        g["R1_lod0_0cm_outside_hull"] = max(h["lod0_shipped_max_outside_unreal_hull_cm"],
                                            h["lod0_unreal_max_outside_unreal_hull_cm"]) <= 1e-6
        lods = b["lods"]
        g["R2_positions_within_1e-6cm_triangles_equal_handedness"] = all(
            e["shipped_tris"] == e["unreal_tris"] and e["position_two_sided_max_cm"] <= 1e-6
            and e["uv0_keyed"]["ok_position_and_handedness"] for e in lods.values())
        g["R3_uv1_inside_0_1_zero_overlap"] = all(
            e["unreal_uv_channels"][1:2] == ["LightMapUV"] and e["uv1"]["strictly_inside_0_1"]
            and e["uv1"]["overlapping_pairs"] == 0 and e["uv1"]["flipped_or_zero_triangles"] == 0
            for e in lods.values()) and lods["LOD0"]["uv1_negative_control"]["detects"]
        g["S_bytes_imported_equal_disk_and_report"] = (imported == disk == {"fbx": rep["export_sha256"]["fbx"],
                                                                            "sidecar": rep["export_sha256"]["sidecar"]}
                                                       and a["fbx_sha256_after"] == disk["fbx"]
                                                       and truth["forms"][form]["fbx"]["fbx_sha256"] == disk["fbx"])
        g["L_zero_warning_error_lines_all_processes"] = logs_clean
        summary["forms"][form] = {
            "verified": all(g.values()), "gates": g, "asset": r["info"]["asset"],
            "sha256": {"imported": imported, "on_disk_now": disk, "report_export_sha256": rep["export_sha256"]},
            "lod_triangles": {"unreal": r["info"]["lod_triangles"], "blend": truth["forms"][form]["blend"]["lod_triangles"],
                              "fbx_reimport": truth["forms"][form]["fbx"]["lod_triangles"], "report": rep["lod_triangles"],
                              "unreal_reexport": [lods[f"LOD{i}"]["unreal_tris"] for i in range(3)]},
            "lod_vertices_unreal": r["info"]["lod_vertices"],
            "lod_screen_sizes": r["detail"]["M5"],
            "bounds_cm": r["detail"]["M4"],
            "sockets": {s["name"]: {k: s[k] for k in ("relative_location_cm", "relative_rotation", "relative_scale", "outer")}
                        for s in r["info"]["socket_objects"]},
            "hull": h,
            "lightmap": {"light_map_coordinate_index": r["info"]["light_map_coordinate_index"],
                         "light_map_resolution": r["info"]["light_map_resolution"],
                         "uv1": {l: {k: e["uv1"][k] for k in ("u_range", "v_range", "strictly_inside_0_1", "overlapping_pairs",
                                                              "candidate_pairs", "charts", "texels_sampled_by_two_charts")}
                                 for l, e in lods.items()},
                         "negative_control": lods["LOD0"]["uv1_negative_control"]},
            "positions_two_sided_max_cm": {l: e["position_two_sided_max_cm"] for l, e in lods.items()},
            "uv0_roundtrip": {l: {"worst_du": max(e["uv0_keyed"]["unreal_to_shipped"]["worst_du"], e["uv0_keyed"]["shipped_to_unreal"]["worst_du"]),
                                  "worst_dv": max(e["uv0_keyed"]["unreal_to_shipped"]["worst_dv"], e["uv0_keyed"]["shipped_to_unreal"]["worst_dv"]),
                                  "u_float16_exact_fraction": e["uv0_keyed"]["unreal_u_float16_exact_fraction"]}
                              for l, e in lods.items()},
            "build_settings_lod0": r["info"]["lod_build_settings"][0],
            "material_slots": r["info"]["material_slots"], "nanite": r["info"]["nanite_enabled"],
        }
    for stem, t in p3["textures"].items():
        imp = p2["maps"].get(stem, {})
        summary["textures"][stem] = {
            "ok_fresh_process": t["ok"], "checks": t.get("checks"),
            "flags": {k: t["info"][k] for k in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "size")},
            "raw_assetimporttask_matched_intent": (imp.get("as_imported_matches_intent") or {}).get("all"),
            "sha256_imported": imp.get("sha256"), "sha256_on_disk_now": t["png_sha256_now"],
            "script_verify_mode_passed": (p3b["maps"].get(stem, {}).get("matches_intent") or {}).get("all"),
        }
    summary["textures_all_ok"] = (all(v["ok_fresh_process"] and v["script_verify_mode_passed"]
                                      and v["sha256_imported"] == v["sha256_on_disk_now"] for v in summary["textures"].values())
                                  and p2["passed"] and p3b["passed"] and len(summary["textures"]) == 3 * len(FORMS))
    summary["all_verified"] = all(f["verified"] for f in summary["forms"].values()) and summary["textures_all_ok"]
    (HERE / "verification_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for form, f in summary["forms"].items():
        print(form, "VERIFIED" if f["verified"] else "FAILED", {k: v for k, v in f["gates"].items() if not v})
    print("textures_all_ok", summary["textures_all_ok"], "logs_clean", logs_clean, "ALL", summary["all_verified"])


main()
