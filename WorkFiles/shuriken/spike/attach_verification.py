"""Fold the spike build's verification evidence into WorkFiles/shuriken/spike_report.json (plain Python).

    "<blender python>" WorkFiles/shuriken/spike/attach_verification.py

Reads (all written by this build's checks, never recomputed here): the frozen-form regressions against
post_six_point and post_restyle2 (regression/regression_spike_*.json), the map pixel diffs, the CPU material
no-op proof, the plan-silhouette check, the coat-interior and visual metrics, both Unreal verifications
(UnrealCheck6 attach + UnrealCheck8 summary, both on the exact exported bytes) and the pack report, and writes
them under ``verification`` with an overall ``all_gates_passed``.
"""
import json
from pathlib import Path

W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken")
S = W / "spike"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


report_path = W / "spike_report.json"
report = load(report_path)
pack = load(W / "pack_report.json")
reg6 = load(W / "regression" / "regression_spike_frozen.json")
reg2 = load(W / "regression" / "regression_spike_vs_post_restyle2.json")
tex6 = load(S / "texdiff_frozen_vs_post_six_point.json")
tex2 = load(S / "texdiff_frozen_vs_post_restyle2.json")
noop = load(S / "material_noop_check.json")
sil = load(S / "silhouette.json")
coat = load(S / "coat_interior_metrics.json")
uc8 = load(W / "UnrealCheck8" / "verification_summary.json")
uc6 = load(W / "UnrealCheck6" / "verification_summary.json")

frozen = {
    "vs_post_six_point": {"forms": reg6["forms"], "passed": reg6["passed"], "summary": reg6["summary"],
                          "file": str(W / "regression" / "regression_spike_frozen.json")},
    "vs_post_restyle2": {"forms": reg2["forms"], "passed": reg2["passed"], "summary": reg2["summary"],
                         "file": str(W / "regression" / "regression_spike_vs_post_restyle2.json")},
    "maps_pixel_diff": {"vs_post_six_point": {"max_abs_8bit": tex6["max_abs_8bit"], "max_pixels_differing": tex6["max_pixels_differing"]},
                        "vs_post_restyle2": {"max_abs_8bit": tex2["max_abs_8bit"], "max_pixels_differing": tex2["max_pixels_differing"]},
                        "note": ("GPU (OptiX) bake noise: two identical-source builds differ by the same 1/255 on a few dozen "
                                 "pixels (six_point_maint/texdiff_all_vs_pre_maint.json); the material itself is proven "
                                 "unchanged by the CPU bake below")},
    "material_noop_cpu_bake": {"all_bitwise_identical": noop["all_bitwise_identical"], "size": noop["size"],
                               "library_old_new": [noop["library_old"], noop["library_new"]],
                               "forms": {k: {c: v["bitwise_identical"] for c, v in r.items()} for k, r in noop["forms"].items()},
                               "file": str(S / "material_noop_check.json")},
}
spike_sil = {k: v for k, v in sil["objects"].items() if k.startswith("SM_Shuriken_Spike")}
checks = {
    "qa_check_55": bool(report["qa"]["passed"]) and len(report["qa"]["checks"]) == 55,
    "lod_bands": all(report["lod_bands_ok"]),
    "outline_mass_gate": bool(report["measured"]["mass_within_tolerance"]),
    "uv_consistency": bool(report["uv_consistency"]["passed"]),
    "knife_shading": bool(report["knife_shading"]["passed"]),
    "render_gates_5": bool(report["render_gates"]["passed"]),
    "pack_consistency": bool(pack["pack_consistency"]["passed"]),
    "pack_passed": bool(pack["passed"]),
    "frozen_regression_post_six_point": bool(reg6["passed"]),
    "frozen_regression_post_restyle2": bool(reg2["passed"]),
    "material_noop_cpu_bitwise": bool(noop["all_bitwise_identical"]),
    "silhouette_all_unchanged": bool(sil["all_unchanged"]),
    "unreal_uc6_all_forms_verified": all(v["verified"] for v in uc6["forms"].values()) and len(uc6["forms"]) == 5,
    "unreal_uc8_all_forms_verified": all(v["verified"] for v in uc8["forms"].values()) and len(uc8["forms"]) == 5,
    "engine_check_this_build": report["engine_check"]["status"] == "verified" and report["engine_check"]["matches_this_build"],
}
report["verification"] = {
    "checks": checks,
    "all_gates_passed": all(checks.values()),
    "frozen_forms": frozen,
    "silhouette": {"all_unchanged": sil["all_unchanged"], "spike": {k: {"unchanged": v["unchanged"], "xor_pixels": v["xor_pixels"],
                                                                         "extents_mm": v["extents_mm"]} for k, v in spike_sil.items()},
                   "reference": "frozen forms: their pass-1 / un-ground references; the spike: the same bar with square arrises",
                   "file": str(S / "silhouette.json")},
    "coat_interior_same_material_read": {"top": {k.replace("_top", ""): {"fine_dark": v["fine_dark"], "core_mean": v["core_mean"]}
                                                 for k, v in coat.items() if k.endswith("_top")},
                                         "hero": {k.replace("_hero", ""): {"fine_dark": v["fine_dark"], "core_mean": v["core_mean"]}
                                                  for k, v in coat.items() if k.endswith("_hero")},
                                         "file": str(S / "coat_interior_metrics.json")},
    "pack_consistency_spike": pack["pack_consistency"]["bar_coat_vs_coat_anchor"],
    "unreal": {"uc6": {f: v["verified"] for f, v in uc6["forms"].items()},
               "uc6_dest": "/Game/ShurikenCheck6/Spike1", "uc6_out": str(W / "UnrealCheck6" / "run_all_spike.out"),
               "uc8": {f: v["verified"] for f, v in uc8["forms"].items()},
               "uc8_dest": "/Game/ShurikenCheck8/Spike1", "uc8_out": str(W / "UnrealCheck8" / "run_uc8_spike.out"),
               "uc8_spike_gates": uc8["forms"]["spike"]["gates"],
               "fbx_sha256": report["export_sha256"]["fbx"]},
    "gallery": {"style_comparison": r"C:\Users\Cody\Desktop\Blender_Projects\Renders\Shuriken\style_comparison.png",
                "modern_line_sheet": r"C:\Users\Cody\Desktop\Blender_Projects\Renders\Shuriken\modern_line_sheet.png",
                "iteration": str(S / "iteration")},
    "regression_baseline_for_the_next_form": str(W / "regression" / "post_spike"),
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")
print("SPIKE_VERIFICATION", json.dumps(checks), "ALL", report["verification"]["all_gates_passed"])
