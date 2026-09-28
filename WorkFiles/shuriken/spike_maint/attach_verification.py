"""Fold the spike maintenance pass's verification evidence into WorkFiles/shuriken/spike_report.json (plain Python).

    "<blender python>" WorkFiles/shuriken/spike_maint/attach_verification.py

Reads (all written by this pass's checks, never recomputed here): the frozen-form regressions against post_spike and
post_restyle2, the spike's own diff against post_spike (geometry unchanged, UVs by design), the map pixel diffs, the
CPU material no-op proof, the plan-silhouette check, the FBX normals check, the coat-interior metrics, the three
Unreal verifications on the exact exported bytes (UnrealCheck6 attach, UnrealCheck8 summary, UnrealCheck10 summary)
and the pack report; writes them under ``verification`` with an overall ``all_gates_passed``, and the review
resolution under ``maintenance_3_8_1``.
"""
import json
from pathlib import Path

W = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken")
S = W / "spike_maint"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def frozen_maps(texdiff):
    maps = {k: v for k, v in texdiff["maps"].items() if "Spike" not in k}
    return {"max_abs_8bit": max(v["max_abs_8bit"] for v in maps.values()),
            "max_pixels_differing": max(v["pixels_differing"] for v in maps.values()),
            "pixels_over_2_of_255": sum(v["pixels_over_2"] for v in maps.values()), "maps": len(maps)}


report_path = W / "spike_report.json"
report = load(report_path)
pack = load(W / "pack_report.json")
reg_spike = load(W / "regression" / "regression_spike_maint_frozen.json")
reg2 = load(W / "regression" / "regression_spike_maint_vs_post_restyle2.json")
self_diff = load(W / "regression" / "regression_spike_maint_spike_vs_post_spike.json")
tex_spike = load(S / "texdiff_vs_post_spike.json")
tex2 = load(S / "texdiff_frozen_vs_post_restyle2.json")
noop = load(S / "material_noop_check.json")
sil = load(S / "silhouette.json")
coat = load(S / "coat_interior_metrics.json")
normals = load(S / "fbx_normals_check.json")
uc6 = load(W / "UnrealCheck6" / "verification_summary.json")
uc8 = load(W / "UnrealCheck8" / "verification_summary.json")
uc10 = load(W / "UnrealCheck10_SpikeVerify" / "verification_summary.json")

spike_fbx = self_diff["per_form"]["spike"]["fbx"]["meshes"]
spike_blend = self_diff["per_form"]["spike"]["blend"]
geometry_unchanged = (all(m["sorted_positions"]["identical"] and m["triangles"]["identical"] for m in spike_fbx.values())
                      and all(all(rec[k]["identical"] for k in ("verts", "loops", "edges", "sharp_edge", "sharp_face"))
                              for rec in spike_blend["lods"].values())
                      and all(spike_blend["hull"][k]["identical"] for k in ("verts", "loops", "edges"))
                      and all(all(v["identical"] for v in s.values()) for s in spike_blend["sockets"].values())
                      and self_diff["per_form"]["spike"]["sidecar"]["all_keys"]["identical"])
frozen = {
    "vs_post_spike": {"forms": reg_spike["forms"], "passed": reg_spike["passed"], "summary": reg_spike["summary"],
                      "file": str(W / "regression" / "regression_spike_maint_frozen.json")},
    "vs_post_restyle2": {"forms": reg2["forms"], "passed": reg2["passed"], "summary": reg2["summary"],
                         "file": str(W / "regression" / "regression_spike_maint_vs_post_restyle2.json")},
    "maps_pixel_diff": {"vs_post_spike": frozen_maps(tex_spike), "vs_post_restyle2": frozen_maps(tex2),
                        "note": ("GPU (OptiX) bake noise: 1/255 on a few dozen pixels, as between any two builds; the "
                                 "material itself is proven unchanged on the plate forms by the CPU bake below")},
    "material_noop_cpu_bake": {"all_bitwise_identical": noop["all_bitwise_identical"], "size": noop["size"],
                               "library_old_new": [noop["library_old"], noop["library_new"]],
                               "forms": {k: {c: v["bitwise_identical"] for c, v in r.items()} for k, r in noop["forms"].items()},
                               "file": str(S / "material_noop_check.json")},
}
spike_sil = {k: v for k, v in sil["objects"].items() if k.startswith("SM_Shuriken_Spike")}
rg = report["render_gates"]
checks = {
    "qa_check_55": bool(report["qa"]["passed"]) and len(report["qa"]["checks"]) == 55,
    "lod_bands": all(report["lod_bands_ok"]),
    "outline_mass_gate": bool(report["measured"]["mass_within_tolerance"]),
    "uv_consistency": bool(report["uv_consistency"]["passed"]),
    "uv_island_map_deviation_0": all(v == 0.0 for v in report["uv_consistency"]["island_map_deviation_px_at_2048"].values()),
    "knife_shading": bool(report["knife_shading"]["passed"]),
    "render_gates_6": bool(rg["passed"]) and len([k for k, v in rg.items() if isinstance(v, dict)]) == 6,
    "pack_consistency": bool(pack["pack_consistency"]["passed"]),
    "pack_passed": bool(pack["passed"]),
    "frozen_regression_post_spike": bool(reg_spike["passed"]),
    "frozen_regression_post_restyle2": bool(reg2["passed"]),
    "material_noop_cpu_bitwise": bool(noop["all_bitwise_identical"]),
    "silhouette_all_unchanged": bool(sil["all_unchanged"]),
    "spike_geometry_hull_sockets_sidecar_unchanged_vs_3_8_0": bool(geometry_unchanged),
    "fbx_carries_analytic_round_normals": all(v["matched"] == v["corners_blend"] and v["max_angle_fbx_vs_blend_deg"] < 0.1
                                              and v["round_max_dev_from_analytic_deg_fbx"] < 0.1 for v in normals.values()),
    "unreal_uc6_all_forms_verified": all(v["verified"] for v in uc6["forms"].values()) and len(uc6["forms"]) == 5,
    "unreal_uc8_all_forms_verified": all(v["verified"] for v in uc8["forms"].values()) and len(uc8["forms"]) == 5,
    "unreal_uc10_spike_all_gates": bool(uc10["all_passed"]),
    "engine_check_this_build": report["engine_check"]["status"] == "verified" and report["engine_check"]["matches_this_build"],
}
report["verification"] = {
    "checks": checks,
    "all_gates_passed": all(checks.values()),
    "frozen_forms": frozen,
    "spike_vs_3_8_0": {"geometry_hull_sockets_sidecar_identical": geometry_unchanged,
                       "changed_by_design": ["UV0 of every LOD (bar_uv_layout)", "corner normals of the arris round (analytic)",
                                             "the maps (2048 x 512, material bar mode)", "report wording"],
                       "file": str(W / "regression" / "regression_spike_maint_spike_vs_post_spike.json")},
    "fbx_normals": normals,
    "silhouette": {"all_unchanged": sil["all_unchanged"],
                   "spike": {k: {"unchanged": v["unchanged"], "xor_pixels": v["xor_pixels"]} for k, v in spike_sil.items()},
                   "reference": "frozen forms: their pass-1 / un-ground references; the spike: the same bar with square arrises",
                   "file": str(S / "silhouette.json")},
    "coat_interior_same_material_read": {"top": {k.replace("_top", ""): {"fine_dark": v["fine_dark"], "core_mean": v["core_mean"]}
                                                 for k, v in coat.items() if k.endswith("_top")},
                                         "hero": {k.replace("_hero", ""): {"fine_dark": v["fine_dark"], "core_mean": v["core_mean"]}
                                                  for k, v in coat.items() if k.endswith("_hero")},
                                         "file": str(S / "coat_interior_metrics.json")},
    "pack_consistency_spike": {"coat": pack["pack_consistency"]["bar_coat_vs_coat_anchor"],
                               "side_faces_vs_walls": pack["pack_consistency"]["bar_walls_vs_wall_anchor"],
                               "backdrop": pack["pack_consistency"]["backdrop"]["per_form"].get("spike")},
    "unreal": {"uc6": {f: v["verified"] for f, v in uc6["forms"].items()},
               "uc6_dest": "/Game/ShurikenCheck6/SpikeMaint2", "uc6_out": str(W / "UnrealCheck6" / "run_all_spike_maint.out"),
               "uc8": {f: v["verified"] for f, v in uc8["forms"].items()},
               "uc8_dest": "/Game/ShurikenCheck8/SpikeMaint2", "uc8_out": str(W / "UnrealCheck8" / "run_uc8_spike_maint.out"),
               "uc8_spike_gates": uc8["forms"]["spike"]["gates"],
               "uc10_dest": uc10["detail"]["G0"]["fresh_dest"], "uc10_gates": uc10["gates"],
               "uc10_textures": {k: {"size": v["size"], "ok": v["ok"]} for k, v in uc10["detail"]["G7"].items()},
               "uc10_normals_roundtrip_deg": {k: v["normals_max_deg"] for k, v in uc10["detail"]["info_roundtrip"].items()},
               "fbx_sha256": report["export_sha256"]["fbx"],
               "note": ("the first maintenance attempts ran on /Game/*SpikeMaint1 and /Game/SpikeVerify10/Maint1 with the "
                        "pre-final material; everything here is the final build's bytes on fresh *Maint2 paths")},
    "gallery": {"style_comparison": r"C:\Users\Cody\Desktop\Blender_Projects\Renders\Shuriken\style_comparison.png",
                "modern_line_sheet": r"C:\Users\Cody\Desktop\Blender_Projects\Renders\Shuriken\modern_line_sheet.png"},
    "regression_baseline_for_the_next_form": str(W / "regression" / "post_spike_maint"),
}
report["maintenance_3_8_1"] = {
    "library": "3.8.1", "revision": 2,
    "resolved": {
        "major_hero_backdrop": ("hero lamps scaled about the origin by fitted camera distance / 0.2157 m (size x s, power x s^2) "
                                "and the bar slid on the floor so its framing needs the anchor forms' lens shift; new "
                                "pack_consistency backdrop gate (12 fixed frame points within the anchor forms' range +- 0.05): "
                                "every form passes, the spike with 0.049 headroom (it missed 6 points before)"),
        "major_side_face_pepper": ("the dots were the dirt specks (round BC dots), not the pits: specks x0.35 and pits x0.33 on the "
                                   "+-Y side faces only; hero side-face dots 8.28 -> 0.0 per 10k at 30 %, top-view coat fine "
                                   "dark unchanged (0.0032); new render gate hero_bar_walls (<= 1.0)"),
        "lod_strip_legibility": "an end-on x5 section of each LOD's butt end beside it (4 / 2 / 0-chord round visible)",
        "hero_value_colour": ("side faces gated like with like against the anchor forms' hero wall p50 0.2678 (spike 0.2227, "
                              "-0.045); the top-view note fixed; the blue cast is not doubled by bar mode (it changes no "
                              "colour or lamp): the violet coat mirrors the same bluish card and fill as the stars' walls"),
        "shoulder_line": "the shoulder is no longer a grind line: no worn band or nicks across it (plain coat-to-satin change)",
        "arris_two_lines": ("round satin-bright (roughness 0.46) with analytic normals: mid-round dip 0.33 -> 0.54 between "
                            "peaks 0.89 / 0.68 (reads as one worn edge)"),
        "texture_usage": "2048 x 512 maps, 54.6 % used at 135 px/cm (was 13.9 % of 2048 x 2048)",
        "uv_padding": "deterministic layout: 16 px between islands, 8 px to the border; empty texels filled with the covered mean",
        "lod2_uv_transfer": "every LOD on its island's exact affine map: 0 clamped loops, per-loop deviation 0.0 px (new metric)",
        "round_normals": "custom split normals = analytic arc normal; FBX carries them (<= 0.078 deg), Unreal round trip 0.234 deg",
        "lod_chain_value": "kept 3 LODs for pack uniformity; lod_choice.lod1_value states LOD1 is visually equal to LOD2",
        "report_accuracy": ("two-sided LOD deviation headline, switch distances at the Unreal radius 75.03 mm, no per-arm tip "
                            "radii, bar wording in mass_gate / mass_check / physics, hull = convex hull of the un-rounded bar"),
        "mass": "no change (brief allows the ESTIMATE): outline 35.325 g vs 37 +-2; state 35.3 g in the Fab description",
        "physics": "one figure 0.0353 kg (finished); study 0.037 kg reference only; 'the spike' wording",
    },
    "not_done": {
        "sidecar_mass_field": "needs a Scripts/pipeline feature (export + ue_import_sockets), not a pipeline bug",
        "unreal_master_material": "pack-wide gap (M_Shuriken_Master / MI_Shuriken_Blackened in Unreal), out of this form's scope",
        "perspective_wire_shot": "optional; the insets carry the LOD difference, the plan wire stays for pack uniformity",
        "log_whitelist_blender_fbx_layer_message": "informational verifier tooling note; not needed",
    },
}
report_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")
print("SPIKE_VERIFICATION", json.dumps(checks), "ALL", report["verification"]["all_gates_passed"])
