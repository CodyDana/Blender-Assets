"""Fold the hooked-cross build's verification evidence into WorkFiles/shuriken/hooked_cross_report.json (plain Python).

    "<blender python>" WorkFiles/shuriken/hooked_cross/attach_verification.py

Reads (all written by this build's checks, never recomputed here): the frozen-form regression against
post_spike_maint, the frozen maps' pixel diff, the CPU material no-op proof, the plan-silhouette check, the Unreal
verification on the exact exported bytes (UnrealCheck6: attach_engine_check + textures import / verify, the hooked
cross's handedness gate in the saved asset), the Blender-side truth of the shipped FBX, the grind-extent evidence and
the two sheets; writes them under ``verification`` with an overall ``all_gates_passed``.
"""
import json
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
W = PROJ / "WorkFiles" / "shuriken"
H = W / "hooked_cross"
UC6 = W / "UnrealCheck6"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


report_path = W / "hooked_cross_report.json"
report = load(report_path)
pack = load(W / "pack_report.json")
reg = load(W / "regression" / "regression_hooked_cross_frozen.json")
tex = load(H / "texdiff_frozen_vs_post_spike_maint.json")
noop = load(H / "material_noop_check.json")
sil = load(H / "silhouette.json")
uc6 = load(UC6 / "verification_summary.json")
pass2 = load(UC6 / "hooked_cross_pass2.json")
truth = load(UC6 / "hooked_cross_truth.json")
tex_imp = load(UC6 / "textures_import.json")
tex_ver = load(UC6 / "textures_verify.json")

maps = tex["maps"]
frozen = {
    "vs_post_spike_maint": {"forms": reg["forms"], "passed": reg["passed"], "summary": reg["summary"],
                            "file": str(W / "regression" / "regression_hooked_cross_frozen.json"),
                            "gated": ("every LOD's vertices, loops, edges, sharp edges / faces, CORNER NORMALS, every UV "
                                      "layer, materials, custom properties, identity transforms; the UCX hull; both "
                                      "sockets; the LOD group; the FBX re-imported (nodes, triangles, sorted positions, "
                                      "position + UV0 loops); the sidecar; the report's measured figures")},
    "maps_pixel_diff": {"max_abs_8bit": max(v["max_abs_8bit"] for v in maps.values()),
                        "max_pixels_differing": max(v["pixels_differing"] for v in maps.values()),
                        "pixels_over_2_of_255": sum(v["pixels_over_2"] for v in maps.values()), "maps": len(maps),
                        "file": str(H / "texdiff_frozen_vs_post_spike_maint.json"),
                        "note": ("GPU (OptiX) bake noise, 1/255 on a few dozen pixels, as between any two builds of the "
                                 "pack; the 3.9 material change is proven a bitwise no-op on the CPU below")},
    "material_noop_cpu_bake": {"all_bitwise_identical": noop["all_bitwise_identical"], "size": noop["size"],
                               "library_old_new": [noop["library_old"], noop["library_new"]],
                               "forms": {k: {c: v["bitwise_identical"] for c, v in r.items()} for k, r in noop["forms"].items()},
                               "file": str(H / "material_noop_check.json")},
}
hc_sil = {k: v for k, v in sil["objects"].items() if k.startswith("SM_Shuriken_HookedCross")}
engine = report.get("engine_check") or {}
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
    "pack_consistency": bool(pack["pack_consistency"]["passed"]),
    "pack_passed": bool(pack["passed"]),
    "frozen_regression_post_spike_maint": bool(reg["passed"]),
    "frozen_material_noop_cpu": bool(noop["all_bitwise_identical"]),
    "plan_silhouettes_all_forms_unchanged": bool(sil["all_unchanged"]),
    "unreal_engine_check_verified_all_six": bool(all(f["verified"] for f in uc6["forms"].values()) and len(uc6["forms"]) == 6),
    "unreal_handedness_saved_asset": bool(pass2["handedness"]["passed"]),
    "unreal_textures_import_verify": bool(tex_imp.get("passed") and tex_ver.get("passed")),
    "fbx_truth_handedness": bool(truth["handedness_gate_passed"]),
}
report["verification"] = {
    "checks": checks,
    "all_gates_passed": all(checks.values()),
    "frozen_forms": frozen,
    "plan_silhouette": {"file": str(H / "silhouette.json"), "all_unchanged": sil["all_unchanged"],
                        "hooked_cross_vs_unground": {k: {"xor_pixels": v.get("xor_pixels"), "unchanged": v.get("unchanged")}
                                                     for k, v in hc_sil.items()},
                        "reference": str(H / "silhouette_ref.py")},
    "unreal": {"project": uc6.get("project"), "content_path": "/Game/ShurikenCheck6/HookedCross1",
               "forms": {k: {"verified": v["verified"], "gates": v["gates"]} for k, v in uc6["forms"].items()},
               "hooked_cross_handedness_in_saved_asset": pass2["handedness"],
               "textures": {"import_passed": tex_imp.get("passed"), "verify_passed": tex_ver.get("passed"),
                            "maps": sorted(tex_ver.get("maps", {}))},
               "runner": str(UC6 / "run_all_hooked_cross.sh"), "log": str(UC6 / "run_all_hooked_cross.out")},
    "fbx_truth": {"file": str(UC6 / "hooked_cross_truth.json"), "fbx_sha256": truth["fbx_sha256"],
                  "lods": {k: {"passed": v["passed"], "matrix_world_determinant": v["matrix_world_determinant"]}
                           for k, v in truth["lods"].items()},
                  "negative_control_caught": truth["lods"]["LOD0"]["negative_control"]["caught"]},
    "evidence": {
        "grind_extent_compare": str(H / "grind_extent_compare.png"),
        "style_comparison": str(PROJ / "Renders" / "Shuriken" / "style_comparison.png"),
        "modern_line_sheet": str(PROJ / "Renders" / "Shuriken" / "modern_line_sheet.png"),
        "visual_metrics": str(H / "visual_metrics.json"), "coat_interior_metrics": str(H / "coat_interior_metrics.json"),
        "build_log": str(H / "build_pack.log"),
    },
}
report["known_gaps"] = [g for g in report.get("known_gaps", []) if not g.startswith("ENGINE CHECK PENDING")]
report_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")
pack.setdefault("verification", {})["hooked_cross"] = {"all_gates_passed": all(checks.values()),
                                                       "report": str(report_path)}
(W / "pack_report.json").write_text(json.dumps(pack, indent=2, sort_keys=False), encoding="utf-8")
print("ATTACHED", json.dumps(checks), "all:", all(checks.values()))
