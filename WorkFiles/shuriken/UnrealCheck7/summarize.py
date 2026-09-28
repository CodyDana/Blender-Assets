"""Independent verifier summary for UnrealCheck7 (plain Python, no Blender, no Unreal).

    py WorkFiles/shuriken/UnrealCheck7/summarize.py

Reads, per form, <form>_pass1/2/3.json and their logs, roundtrip_compare.json, blender_fbx_counts.json,
blend_lod_counts.json (counts read straight from Assets/Shuriken.blend), the build report's export_sha256
and the sidecar, plus textures_pass4/5.json and their logs, and writes verification_summary.json next to
this file.  It NEVER writes into the build reports (that is attach_engine_check.py's job in UnrealCheck6);
this file is the independent evidence.

Gates per form: the nine of UnrealCheck6 (1-6 from pass 2, 7 logs, 8 round trip, 9 bytes) plus
  10 blend truth: LOD triangles in the .blend == build report == FBX re-import == Unreal, hull keyed
     UCX_<render node>_00 with the same vertex/triangle counts in the .blend, the shipped FBX and Unreal's
     re-export, sockets are Empties whose records equal the sidecar
  x_ extra read-backs from pass 2.
Texture gate (pack-wide): every map 2048 square; BC sRGB / TC_Default, N linear / TC_Normalmap with
green not flipped, ORM linear / TC_Masks - reported separately for the raw AssetImportTask result and
for the flag-corrected copy, both read back in a fresh process.
"""
import hashlib
import json
import re
import time
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "shuriken" / "UnrealCheck7"
REPORTS = PROJ / "WorkFiles" / "shuriken"
FORMS = {"four_point": "SM_Shuriken_FourPoint", "eight_point": "SM_Shuriken_EightPoint",
         "square_plate": "SM_Shuriken_SquarePlate"}
PATTERN = re.compile(r":\s*(Warning|Error)\s*:")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def log_problems(path):
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    return [line for line in lines if PATTERN.search(line)]


def main():
    roundtrip = load(HERE / "roundtrip_compare.json")
    fbx_counts = load(HERE / "blender_fbx_counts.json")["forms"]
    blend = load(HERE / "blend_lod_counts.json")["forms"]
    summary = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "verifier": "UnrealCheck7 (independent)",
               "project": str(REPORTS / "UnrealShuriken" / "ShurikenValidation.uproject"),
               "content_path": "/Game/ShurikenCheck7/Indep", "forms": {}, "textures": {}}
    for form, mesh in FORMS.items():
        report = load(REPORTS / f"{form}_report.json")
        p1, p2, p3 = (load(HERE / f"{form}_pass{i}.json") for i in (1, 2, 3))
        logs = {name: log_problems(HERE / f"{form}_{name}.log") for name in ("pass1", "pass2", "pass3")}
        fbx, sidecar = Path(report["fbx"]), Path(report["sockets_sidecar"])
        hashes = {"report": report.get("export_sha256") or {},
                  "imported_by_unreal": {"fbx": p1.get("fbx_sha256"), "sidecar": p1.get("sidecar_sha256")},
                  "on_disk_now": {"fbx": sha256(fbx), "sidecar": sha256(sidecar)}}
        same_bytes = (hashes["report"].get("fbx") == hashes["imported_by_unreal"]["fbx"] == hashes["on_disk_now"]["fbx"]
                      and hashes["report"].get("sidecar") == hashes["imported_by_unreal"]["sidecar"]
                      == hashes["on_disk_now"]["sidecar"])
        rt = roundtrip.get(form, {})
        lods = rt.get("lods", {})
        hulls = list((rt.get("unreal_hulls") or {}).values())
        sh = rt.get("shipped_hull") or {}
        roundtrip_ok = bool(
            lods and all(e.get("position_two_sided_max_cm", 1.0) <= 1e-5
                         and e.get("unreal_tris") == e.get("shipped_tris")
                         and (e.get("uv0_keyed_position_check") or {}).get("max_position_diff_cm", 1.0) <= 1e-5
                         and (e.get("uv1_lightmap") or {}).get("inside_0_1")
                         and (e.get("uv1_lightmap") or {}).get("overlap_pixels", 1) == 0
                         and (e.get("uv1_lightmap_2048") or {}).get("overlap_pixels", 1) == 0
                         for e in lods.values())
            and len(hulls) == 1 and hulls[0].get("lod0_max_outside_cm", 1.0) <= 1e-5
            and hulls[0].get("verts_unique") == sh.get("verts") and hulls[0].get("tris") == sh.get("tris")
            and rt.get("hull_shipped_vs_unreal_two_sided_max_cm", 1.0) <= 1e-5)
        # gate 10: truth read from the .blend itself
        b = blend[form]
        blend_tris = b["lod_triangles"]
        fbx_tris = [fbx_counts[form]["nodes"][f"{mesh}_LOD{i}"]["triangles"] for i in range(3)]
        hull_name = f"UCX_{mesh}_LOD0_00"
        bh = b["hulls"].get(hull_name) or {}
        sidecar_payload = load(sidecar)
        sidecar_records = {r["socket"]: r for r in sidecar_payload["sockets"]}
        blend_sockets = {s["record"]["socket"]: s for s in b["sockets"] if "record" in s}
        sockets_match = (set(blend_sockets) == set(sidecar_records) == {"Grip", "Trail"}
                         and all(s["is_empty"] and s["ue_correction"] for s in blend_sockets.values())
                         and all(blend_sockets[n]["record"]["location_cm"] == sidecar_records[n]["location_cm"]
                                 and blend_sockets[n]["record"]["rotation_deg"] == sidecar_records[n]["rotation_deg"]
                                 and blend_sockets[n]["record"]["scale"] == sidecar_records[n]["scale"]
                                 for n in blend_sockets))
        blend_ok = (blend_tris == report["lod_triangles"] == fbx_tris == p2.get("lod_triangles")
                    and bh.get("keyed_to_render_node") is True
                    and bh.get("vertices") == sh.get("verts") == (hulls[0].get("verts_unique") if hulls else None)
                    and bh.get("triangles") == sh.get("tris") == (hulls[0].get("tris") if hulls else None)
                    and all(v["transform_applied"] and v["material_slots"] == ["M_Shuriken_Master"] and not v["modifiers"]
                            for v in b["lods"].values())
                    and sockets_match)
        gates = dict(p2.get("gates") or {})
        gates["7_zero_warning_error_log_lines"] = all(v == [] for v in logs.values())
        gates["8_unreal_export_roundtrip_hull_positions_uv"] = roundtrip_ok
        gates["9_verified_bytes_are_this_build"] = same_bytes
        gates["10_blend_truth_lods_hull_sockets"] = blend_ok
        verified = bool(p2.get("passed_1_to_6")) and all(gates.values())
        summary["forms"][form] = {
            "verified": verified, "gates": gates, "sha256": hashes, "asset": p2.get("asset"),
            "engine": p2.get("engine"),
            "lod_triangles": {"blend": blend_tris, "report": report["lod_triangles"], "fbx_reimport": fbx_tris,
                              "unreal": p2.get("lod_triangles")},
            "lod_vertices_unreal": p2.get("lod_vertices"),
            "lod_screen_sizes": {"sidecar": sidecar_payload.get("lod_screen_sizes"), "unreal": p2.get("lod_screen_sizes"),
                                 "before_sidecar_in_pass1": (p1.get("after_import") or [{}])[0].get("lod_screen_sizes")},
            "hull": {"blend": bh, "shipped_fbx": sh, "unreal_reexport": hulls[0] if hulls else None,
                     "hull_vs_shipped_two_sided_cm": rt.get("hull_shipped_vs_unreal_two_sided_max_cm"),
                     "convex_hulls_in_body_setup": p2.get("convex_hulls"),
                     "other_collision_elems": p2.get("other_collision_elems")},
            "bounds": {"unreal_size_cm": p2.get("size_cm"), "expected_size_cm": (p2.get("gate_detail") or {}).get("expected_size_cm"),
                       "blend_dimensions_cm": b["lods"]["LOD0"]["dimensions_cm"]},
            "sockets": {"unreal": p2.get("sockets"), "unreal_raw_array": p2.get("socket_array"),
                        "sidecar": list(sidecar_records.values()),
                        "blend_empties": [{k: s.get(k) for k in ("name", "type", "ue_correction")} | {"record": s.get("record")}
                                          for s in b["sockets"]],
                        "sockets_in_fbx_before_sidecar": [s["name"] for s in (p1.get("after_import") or [{}])[0].get("sockets", [])]},
            "lightmap": {"coordinate_index": p2.get("light_map_coordinate_index"), "resolution": p2.get("light_map_resolution"),
                         "uv1_per_lod": {k: {"inside_0_1": (v.get("uv1_lightmap") or {}).get("inside_0_1"),
                                             "u_range": (v.get("uv1_lightmap") or {}).get("u_range"),
                                             "v_range": (v.get("uv1_lightmap") or {}).get("v_range"),
                                             "overlap_pixels_1024": (v.get("uv1_lightmap") or {}).get("overlap_pixels"),
                                             "overlap_pixels_2048": (v.get("uv1_lightmap_2048") or {}).get("overlap_pixels"),
                                             "coverage": (v.get("uv1_lightmap") or {}).get("coverage")} for k, v in lods.items()},
                         "build_settings_lod0": (p2.get("lod_build_settings") or [None])[0]},
            "roundtrip_positions": {k: {"two_sided_max_cm": v.get("position_two_sided_max_cm"),
                                        "uv0_keyed_max_cm": (v.get("uv0_keyed_position_check") or {}).get("max_position_diff_cm"),
                                        "unreal_tris": v.get("unreal_tris")} for k, v in lods.items()},
            "material_slots": p2.get("material_slots"),
            "nanite_enabled": p2.get("nanite_enabled"),
            "log_warning_error_lines": {k: (len(v) if v is not None else None) for k, v in logs.items()},
            "pass3_export": {k: p3.get(k) for k in ("export_ok", "fbx_out", "fbx_bytes")},
            "build_report_engine_check_status": (report.get("engine_check") or {}).get("status"),
            "build_report_engine_check_asset": ((report.get("engine_check") or {}).get("pass2") or {}).get("asset"),
            "evidence": [str(HERE / f"{form}_pass{i}.{ext}") for i in (1, 2, 3) for ext in ("json", "log")]
            + [str(HERE / n) for n in ("roundtrip_compare.json", "blender_fbx_counts.json", "blend_lod_counts.json")],
        }
        if not verified:
            summary["forms"][form]["reason"] = {k: v for k, v in gates.items() if not v}
        print(f"{form}: {'VERIFIED' if verified else 'FAILED'} {gates}")

    # textures
    p4, p5 = load(HERE / "textures_pass4.json"), load(HERE / "textures_pass5.json")
    tlogs = {name: log_problems(HERE / f"textures_{name}.log") for name in ("pass4", "pass5")}
    maps = {}
    for stem, rec in p5["maps"].items():
        png = Path(p4["maps"][stem]["png"])
        maps[stem] = {
            "kind": rec["kind"], "png": str(png), "sha256_imported": p4["maps"][stem]["sha256"], "sha256_on_disk_now": sha256(png),
            "raw_import": {k: rec["Raw"].get(k) for k in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "size", "matches_intent")},
            "after_flags_set_fresh_process": {k: rec["Fixed"].get(k) for k in ("srgb", "compression_settings", "flip_green_channel", "lod_group", "size", "matches_intent")},
            "factory_auto_detected": p4["maps"][stem]["Raw"].get("factory"),
        }
    summary["textures"] = {
        "dest": p5.get("dest"),
        "gates": {
            "T1_all_nine_import_as_Texture2D_2048": all(rec[v].get("uasset_exists") and rec[v].get("size") == [2048, 2048]
                                                        for rec in p5["maps"].values() for v in ("Raw", "Fixed")),
            "T2_raw_assetimporttask_flags_match_intent": bool(p5.get("raw_import_all_match_intent")),
            "T3_flags_set_after_import_persist_in_fresh_process": bool(p5.get("fixed_all_match_intent")),
            "T4_zero_warning_error_log_lines": all(v == [] for v in tlogs.values()),
            "T5_bytes_verified_are_on_disk": all(m["sha256_imported"] == m["sha256_on_disk_now"] for m in maps.values()),
        },
        "raw_import_mismatches": {stem: m["raw_import"]["matches_intent"] for stem, m in maps.items()
                                  if not (m["raw_import"]["matches_intent"] or {}).get("all")},
        "maps": maps,
        "log_warning_error_lines": {k: (len(v) if v is not None else None) for k, v in tlogs.items()},
        "evidence": [str(HERE / f"textures_pass{i}.{ext}") for i in (4, 5) for ext in ("json", "log")],
    }
    summary["all_mesh_forms_verified"] = all(f["verified"] for f in summary["forms"].values())
    summary["textures_verified_as_shipped"] = summary["textures"]["gates"]["T2_raw_assetimporttask_flags_match_intent"]
    (HERE / "verification_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("textures:", summary["textures"]["gates"], "mismatches:", summary["textures"]["raw_import_mismatches"])
    print("SUMMARY", HERE / "verification_summary.json")


if __name__ == "__main__":
    main()
