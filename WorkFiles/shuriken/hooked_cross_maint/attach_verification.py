"""Fold the hooked-cross MAINTENANCE pass's verification evidence (library 3.9.1, revision 2) into
WorkFiles/shuriken/hooked_cross_report.json (plain Python, never recomputes a figure):

    py -3 WorkFiles/shuriken/hooked_cross_maint/attach_verification.py

Copied from hooked_cross/attach_verification.py (the 3.9.0 build's); it now also reads the frozen-maps gate
(build_pack --frozen-maps), the 3.9.1 CPU material no-op proof, the texture-sheet gate (and its run on the 3.9.0 layout,
which must fail), UnrealCheck6 pass 2 gates 11-12 (render data of every LOD, the texture sheets) and the maintenance
evidence images.  Writes the result under ``verification`` with ``all_gates_passed``.
"""
import json
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
W = PROJ / "WorkFiles" / "shuriken"
M = W / "hooked_cross_maint"
UC6 = W / "UnrealCheck6"
FROZEN = ("four_point", "eight_point", "square_plate", "six_point", "spike")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


report_path = W / "hooked_cross_report.json"
report = load(report_path)
pack = load(W / "pack_report.json")
reg = load(W / "regression" / "regression_hooked_cross_maint_frozen.json")
noop = load(M / "material_noop_check.json")
sil = load(M / "silhouette.json")
old_layout = load(M / "texture_gate_on_3_9_0_blend.json")
uc6 = load(UC6 / "verification_summary.json")
pass2 = load(UC6 / "hooked_cross_pass2.json")
truth = load(UC6 / "hooked_cross_truth.json")
tex_imp = load(UC6 / "textures_import.json")
tex_ver = load(UC6 / "textures_verify.json")
highlight = load(M / "lodgrind_highlight.json")

frozen_maps = {f: (load(W / f"{f}_report.json").get("textures") or {}).get("frozen_maps") for f in FROZEN}
maps_identical = {f: bool((reg.get("summary") or {}).get(f, {}).get("textures_identical")) for f in FROZEN}
hc_sil = {k: v for k, v in sil["objects"].items() if k.startswith("SM_Shuriken_HookedCross")}
render = pass2.get("handedness_render") or {}
checks = {
    "qa_check_55": bool(report["qa"]["passed"]) and len(report["qa"]["checks"]) == 55,
    "lod_bands": all(report["lod_bands_ok"]),
    "outline_mass_gate": bool(report["measured"]["mass_within_tolerance"]),
    "uv_consistency": bool(report["uv_consistency"]["passed"]),
    "knife_shading": bool(report["knife_shading"]["passed"]),
    "render_gates": bool(report["render_gates"]["passed"]),
    "handedness_gate_every_lod": bool(report["handedness"]["passed"]),
    "handedness_negative_control_caught": bool(report["handedness"]["negative_control"]["caught"]),
    "gallery_shows_plus_z": bool(report["gallery_presented_face"]["passed"]),
    "texture_sheets_read_plus_z": bool(report["texture_handedness"]["passed"]),
    "texture_negative_control_caught": bool(report["texture_handedness"]["negative_control"]["caught"]),
    "texture_gate_fails_on_the_3_9_0_layout": (not old_layout["passed"]) and old_layout["negative_control"]["caught"],
    "pack_consistency": bool(pack["pack_consistency"]["passed"]),
    "pack_passed": bool(pack["passed"]),
    "frozen_regression_post_spike_maint": bool(reg["passed"]),
    "frozen_maps_gate_all_five": all(v is not None and v.get("passed") for v in frozen_maps.values()),
    "frozen_maps_bit_identical_to_post_spike_maint": all(maps_identical.values()),
    "frozen_material_noop_cpu": bool(noop["all_bitwise_identical"]),
    "plan_silhouettes_all_forms_unchanged": bool(sil["all_unchanged"]),
    "unreal_engine_check_verified_all_six": bool(all(f["verified"] for f in uc6["forms"].values()) and len(uc6["forms"]) == 6),
    "unreal_handedness_saved_asset_gate_10": bool(pass2["handedness"]["passed"]),
    "unreal_render_data_every_lod_gate_11": bool(render.get("passed")),
    "unreal_texture_sheets_gate_12": bool((pass2.get("gates") or {}).get("12_texture_sheets_read_plus_z")),
    "unreal_textures_import_verify": bool(tex_imp.get("passed") and tex_ver.get("passed")),
    "fbx_truth_handedness": bool(truth["handedness_gate_passed"]),
    "fbx_truth_texture_sheets": bool((truth.get("texture_handedness") or {}).get("passed")
                                     and (truth.get("texture_handedness") or {}).get("negative_control_caught")),
}
report["verification"] = {
    "pass": "hooked-cross maintenance (library 3.9.1, revision 2)",
    "checks": checks,
    "all_gates_passed": all(checks.values()),
    "frozen_forms": {
        "vs_post_spike_maint": {"forms": reg["forms"], "passed": reg["passed"], "summary": reg.get("summary"),
                                "file": str(W / "regression" / "regression_hooked_cross_maint_frozen.json")},
        "frozen_maps": {f: {"passed": (v or {}).get("passed"),
                            "fresh_bake_vs_snapshot": {s: {k: m.get(k) for k in ("max_abs_8bit", "pixels_differing")}
                                                       for s, m in ((v or {}).get("maps") or {}).items()},
                            "shipped": (v or {}).get("shipped")} for f, v in frozen_maps.items()},
        "material_noop_cpu_bake": {"all_bitwise_identical": noop["all_bitwise_identical"], "size": noop["size"],
                                   "library_old_new": [noop["library_old"], noop["library_new"]],
                                   "file": str(M / "material_noop_check.json")},
    },
    "texture_sheets": {"gate": {k: report["texture_handedness"][k] for k in ("passed", "lod0_islands", "negative_control")},
                       "same_gate_on_the_3_9_0_blend": {"passed": old_layout["passed"],
                                                        "lod0_islands": old_layout["lod0_islands"],
                                                        "file": str(M / "texture_gate_on_3_9_0_blend.json")},
                       "image": str(M / "texture_sheets_compare.png")},
    "plan_silhouette": {"file": str(M / "silhouette.json"), "all_unchanged": sil["all_unchanged"],
                        "hooked_cross_vs_unground": {k: {"xor_pixels": v.get("xor_pixels"), "unchanged": v.get("unchanged")}
                                                     for k, v in hc_sil.items()}},
    "unreal": {"project": uc6.get("project"), "content_path": "/Game/ShurikenCheck6/HookedCrossMaint2 (the dry run on the second build used HookedCrossMaint1)",
               "forms": {k: {"verified": v["verified"], "gates": v["gates"]} for k, v in uc6["forms"].items()},
               "gate_10_source_lod0": pass2["handedness"],
               "gate_11_12_render_data": {k: render.get(k) for k in ("passed", "texture_sheets_passed", "negative_control",
                                                                      "allow_cpu_access_saved", "dirty_packages_before",
                                                                      "dirty_packages_after")}
               | {"lods": {k: {kk: v.get(kk) for kk in ("passed", "build_scale3d", "build_reversed_index_buffer",
                                                        "triangles", "winding_agrees_with_normals_unreal_rule",
                                                        "position_max_cm_documented_conversion",
                                                        "position_max_cm_if_mirrored", "texture_sheets",
                                                        "viewer_below_accepted_back_face")}
                           | {"viewer_above_reads": (v.get("viewer_above") or {}).get("reads"),
                              "tip_offsets_ccw_deg": [t.get("offset_ccw_deg") for t in (v.get("viewer_above") or {}).get("tips") or []]}
                           for k, v in (render.get("lods") or {}).items()}},
               "textures": {"import_passed": tex_imp.get("passed"), "verify_passed": tex_ver.get("passed"),
                            "maps": sorted(tex_ver.get("maps", {}))},
               "runner": str(UC6 / "run_all_hooked_cross_maint.sh"), "log": str(UC6 / "run_all_hooked_cross_maint.out")},
    "fbx_truth": {"file": str(UC6 / "hooked_cross_truth.json"), "fbx_sha256": truth["fbx_sha256"],
                  "lods": {k: {"passed": v["passed"], "matrix_world_determinant": v["matrix_world_determinant"]}
                           for k, v in truth["lods"].items()},
                  "negative_control_caught": truth["lods"]["LOD0"]["negative_control"]["caught"],
                  "texture_sheets": {k: (truth.get("texture_handedness") or {}).get(k)
                                     for k in ("passed", "negative_control_caught")}},
    "lodgrind_highlight_share_over_0_9_luma": highlight,
    "evidence": {
        "runout_compare": str(M / "runout_compare.png"),
        "texture_sheets_compare": str(M / "texture_sheets_compare.png"),
        "grind_extent_compare": str(W / "hooked_cross" / "grind_extent_compare.png"),
        "style_comparison": str(PROJ / "Renders" / "Shuriken" / "style_comparison.png"),
        "modern_line_sheet": str(PROJ / "Renders" / "Shuriken" / "modern_line_sheet.png"),
        "visual_metrics": str(M / "visual_metrics.json"), "coat_interior_metrics": str(M / "coat_interior_metrics.json"),
        "build_log": str(M / "build_pack.log"),
        "before_3_9_0": str(M / "before"),
    },
}
report["known_gaps"] = [g for g in report.get("known_gaps", []) if not g.startswith("ENGINE CHECK PENDING")]
report_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")
pack.setdefault("verification", {})["hooked_cross"] = {"all_gates_passed": all(checks.values()),
                                                       "report": str(report_path), "pass": "maintenance 3.9.1"}
(W / "pack_report.json").write_text(json.dumps(pack, indent=2, sort_keys=False), encoding="utf-8")
print("ATTACHED", json.dumps(checks), "all:", all(checks.values()))
