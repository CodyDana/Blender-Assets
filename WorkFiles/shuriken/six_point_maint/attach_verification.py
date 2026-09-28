"""Attach the six-point MAINTENANCE pass's out-of-build verification to six_point_report.json and pack_report.json.

Plain Python (no Blender, no Unreal), run LAST, after build_pack.py (library 3.7.1), UnrealCheck6 (its
attach_engine_check.py writes engine_check itself), UnrealCheck8 (summarize.py), both regressions, the map
differences, the silhouette check, the visual metrics and both sheets:

    py WorkFiles/shuriken/six_point_maint/attach_verification.py

Adapted from six_point/attach_verification.py (the build's).  It only READS the evidence files and copies their
verdicts (with paths and SHA-256 of what it read) into report["verification"] and report["maintenance"]; it
never re-computes a gate.  The frozen reports are not touched (their REPORT_KEYS are the regression's evidence).
pack_report.json gets "six_point_build" (refreshed) and "six_point_maintenance".
"""
import hashlib
import json
import time
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
WF = PROJ / "WorkFiles" / "shuriken"
HERE = WF / "six_point_maint"
REG = WF / "regression"
FROZEN = ("four_point", "eight_point", "square_plate")
RENDERS = PROJ / "Renders" / "Shuriken"


def sha(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def load(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def maps_verdict(diff, noise):
    """A map diff is within bake noise when no pixel is off by more than the noise's max (1/255) and none by > 2."""
    if not diff or not noise:
        return False
    return bool(diff.get("max_abs_8bit", 99) <= max(1, noise.get("max_abs_8bit", 0))
                and all(m.get("pixels_over_2", 1) == 0 for m in diff.get("maps", {}).values()))


def main():
    report_path = WF / "six_point_report.json"
    report = load(report_path)
    ver = {"attached": time.strftime("%Y-%m-%dT%H:%M:%S"), "attached_by": str(Path(__file__)),
           "pass": "six-point maintenance (review: visual PASS, geometry PASS, Unreal VERIFIED; minors only)"}

    noise_path = WF / "six_point" / "bake_determinism" / "rebuildA_vs_rebuildB.json"
    noise = load(noise_path) or {}

    # --- frozen forms against post_restyle2
    reg_path = REG / "regression_six_maint_frozen.json"
    reg = load(reg_path) or {}
    tex_frozen_path = HERE / "texdiff_frozen_vs_post_restyle2.json"
    tex_frozen = load(tex_frozen_path) or {}
    frozen_maps_ok = maps_verdict(tex_frozen, noise)
    ver["frozen_regression"] = {
        "evidence": str(reg_path), "evidence_sha256": sha(reg_path), "snapshot": reg.get("snapshot"),
        "forms": list(FROZEN), "summary": reg.get("summary"), "passed": reg.get("passed"),
        "gated": "blend (every LOD's vertices, loops, edges, sharp flags, every UV layer, material slots, wear tags, "
                 "identity transform), UCX hull, both SOCKET_ Empties, LOD group, FBX content re-imported (nodes, "
                 "triangles, sorted positions, (position, UV0) loop sets), sidecar (every key), report figures, "
                 "M_Shuriken_Master export scalars - all IDENTICAL",
        "maps": {"within_bake_noise": frozen_maps_ok, "evidence": str(tex_frozen_path),
                 "max_abs_8bit": tex_frozen.get("max_abs_8bit"),
                 "max_pixels_differing": tex_frozen.get("max_pixels_differing"),
                 "bake_noise_reference": {"evidence": str(noise_path), "max_abs_8bit": noise.get("max_abs_8bit"),
                                          "max_pixels_differing": noise.get("max_pixels_differing")}},
    }

    # --- the six-point against its own pre-maintenance state (the pass changed reporting only)
    six_reg_path = REG / "regression_six_maint_sixpoint.json"
    six_reg = load(six_reg_path) or {}
    tex_six_path = HERE / "texdiff_six_vs_pre_maint.json"
    tex_six = load(tex_six_path) or {}
    six_maps_ok = maps_verdict(tex_six, noise)
    ver["six_point_unchanged_by_maintenance"] = {
        "evidence": str(six_reg_path), "evidence_sha256": sha(six_reg_path), "snapshot": six_reg.get("snapshot"),
        "summary": (six_reg.get("summary") or {}).get("six_point"), "passed": six_reg.get("passed"),
        "maps": {"within_bake_noise": six_maps_ok, "evidence": str(tex_six_path),
                 "max_abs_8bit": tex_six.get("max_abs_8bit"), "max_pixels_differing": tex_six.get("max_pixels_differing")},
        "note": ("the maintenance changed reporting only (library 3.7.1: pack_consistency anchor + headroom, "
                 "cross_lod_uv metric names and splits; form script: gallery + review_dispositions), so the "
                 "six-point's blend objects, FBX content, sidecar and report figures must be bitwise identical to "
                 "the pre-maintenance snapshot, and its maps equal to the bake's own run-to-run noise"),
    }

    # --- plan silhouette
    sil_path = HERE / "silhouette.json"
    sil = load(sil_path) or {}
    objs = sil.get("objects") or {}
    ver["silhouette"] = {
        "evidence": str(sil_path), "tool": str(WF / "restyle_pass2" / "silhouette_check.py"),
        "reference_set": str(WF / "six_point" / "silhouette_ref"),
        "frozen_vs_restyle_pass1": all(v.get("unchanged") for k, v in objs.items() if "SixPoint" not in k),
        "six_point_vs_unground_outline": {k: {kk: v.get(kk) for kk in (
            "xor_pixels", "area_mm2", "max_new_boundary_vertex_off_pass1_boundary_mm",
            "max_pass1_boundary_vertex_off_new_boundary_mm", "unchanged")} for k, v in objs.items() if "SixPoint" in k},
        "all_unchanged": sil.get("all_unchanged"),
    }

    # --- look
    vm_path = HERE / "visual_metrics.json"
    vm = load(vm_path) or {}
    keys_top = ("edge_bright_band_mm", "edge_peak_p50", "large_scale_var", "fine_dark", "fine_bright",
                "hole_ring_range", "object_mean", "object_p50")
    keys_hero = ("bright_facet_share", "near_facet_p50", "fine_dark", "fine_bright", "object_mean", "object_p50")
    names = ("reference", "four_point", "eight_point", "square_plate", "six_point")
    pack = load(WF / "pack_report.json") or {}
    ver["look"] = {
        "visual_metrics": str(vm_path),
        "top": {n: {k: (vm.get(f"{n}_top") or {}).get(k) for k in keys_top} for n in names},
        "hero": {n: {k: (vm.get(f"{n}_hero") or {}).get(k) for k in keys_hero} for n in names},
        "comparison_sheet": str(RENDERS / "style_comparison.png"),
        "comparison_sheet_sha256": sha(RENDERS / "style_comparison.png"),
        "sheet_script": str(HERE / "style_sheet.py"),
        "line_sheet": str(RENDERS / "modern_line_sheet.png"),
        "line_sheet_sha256": sha(RENDERS / "modern_line_sheet.png"),
        "line_sheet_script": str(PROJ / "Scripts" / "shuriken" / "line_sheet.py"),
        "pack_consistency": pack.get("pack_consistency"),
    }

    # --- Unreal
    uc8_path = WF / "UnrealCheck8" / "verification_summary.json"
    uc8 = load(uc8_path) or {}
    six = (uc8.get("forms") or {}).get("six_point") or {}
    uc6_path = WF / "UnrealCheck6" / "verification_summary.json"
    uc6 = load(uc6_path) or {}
    ver["unreal"] = {
        "unrealcheck6_engine_check_status": (report.get("engine_check") or {}).get("status"),
        "unrealcheck6_matches_this_build": (report.get("engine_check") or {}).get("matches_this_build"),
        "unrealcheck6_gates": (report.get("engine_check") or {}).get("gates_passed"),
        "unrealcheck6_summary": {"evidence": str(uc6_path), "evidence_sha256": sha(uc6_path)},
        "unrealcheck6_textures": {"import": (load(WF / "UnrealCheck6" / "textures_import.json") or {}).get("passed"),
                                  "verify": (load(WF / "UnrealCheck6" / "textures_verify.json") or {}).get("passed")},
        "unrealcheck8": {"evidence": str(uc8_path), "evidence_sha256": sha(uc8_path),
                         "content_path": uc8.get("content_path"), "all_verified": uc8.get("all_verified"),
                         "textures_all_ok": uc8.get("textures_all_ok"), "logs_clean": uc8.get("logs_clean"),
                         "six_point_verified": six.get("verified"), "six_point_gates": six.get("gates"),
                         "forms_verified": {f: v.get("verified") for f, v in (uc8.get("forms") or {}).items()}},
    }
    engine_all = all(((load(WF / f"{f}_report.json") or {}).get("engine_check") or {}).get("status") == "verified"
                     for f in (*FROZEN, "six_point"))
    ver["unreal"]["unrealcheck6_all_forms_verified"] = engine_all
    ver["passed"] = bool(
        reg.get("passed") and frozen_maps_ok and six_reg.get("passed") and six_maps_ok and sil.get("all_unchanged")
        and ver["unreal"]["unrealcheck6_engine_check_status"] == "verified" and engine_all
        and ver["unreal"]["unrealcheck6_textures"]["import"] and ver["unreal"]["unrealcheck6_textures"]["verify"]
        and uc8.get("all_verified") and six.get("verified") and pack.get("passed")
        and (pack.get("pack_consistency") or {}).get("passed"))
    previous = report.get("verification")
    report["verification"] = ver
    report["maintenance"] = {
        "date": "2026-09-18",
        "library": f"{report.get('library_version')} (was 3.7.0)",
        "changed": [
            "shuriken_lib.render.pack_consistency: fixed anchor (PACK_ANCHOR, the three forms frozen at restyle pass 2) "
            "instead of the all-forms mean; per-form offsets and headroom, min headroom, all-forms figures as "
            "information, anchor-drift check",
            "shuriken_lib.uv.cross_lod_uv: each figure names its metric; surface split into plate / non-plate / "
            "off-LOD0-surface triangles",
            "build_six_point.py: report gains gallery (lead with the hero) and review_dispositions",
            "Renders/Shuriken/modern_line_sheet.png regenerated from the current renders with the six-point "
            "(Scripts/shuriken/line_sheet.py); the pre-restyle sheet moved to WorkFiles/shuriken/archive/",
        ],
        "unchanged": "geometry, LODs, UVs, hull, sockets, sidecar, material, bake settings, export settings of every form",
        "review_dispositions": report.get("review_dispositions"),
        "previous_verification_attached": (previous or {}).get("attached"),
        "regression_snapshot_after": str(REG / "post_six_point"),
    }
    gaps = [g for g in report.get("known_gaps", []) if not g.startswith("BAKE NOISE:")]
    gaps.append("BAKE NOISE: the GPU (OptiX) texture bake is not bit-reproducible run to run (1/255 on a few dozen "
                "pixels per 2048 map between two identical rebuilds), so every pack rebuild changes the maps' bytes "
                "at that level even though nothing in their source changed; a bitwise map gate needs a deterministic "
                "bake device (CPU bake, a library decision) first. See verification.frozen_regression.")
    report["known_gaps"] = gaps
    report_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")

    pack["six_point_build"] = {"report": str(report_path), "verification_passed": ver["passed"],
                               "frozen_regression_passed": reg.get("passed"),
                               "frozen_maps_within_bake_noise": frozen_maps_ok,
                               "silhouette_all_unchanged": sil.get("all_unchanged"),
                               "unrealcheck8_all_verified": uc8.get("all_verified"),
                               "comparison_sheet": ver["look"]["comparison_sheet"]}
    pack["six_point_maintenance"] = {
        "report_block": "six_point_report.json maintenance + verification",
        "six_point_unchanged": six_reg.get("passed"), "six_point_maps_within_bake_noise": six_maps_ok,
        "pack_gate_min_headroom_vs_anchor": (pack.get("pack_consistency") or {}).get("min_headroom_vs_anchor"),
        "pack_gate_all_forms_min_headroom_information": ((pack.get("pack_consistency") or {}).get("all_forms") or {})
        .get("min_headroom"),
        "line_sheet": ver["look"]["line_sheet"], "verification_passed": ver["passed"]}
    pack["engine_checks_verified"] = engine_all
    (WF / "pack_report.json").write_text(json.dumps(pack, indent=2, sort_keys=False), encoding="utf-8")
    print("SIX_POINT_MAINT_VERIFICATION", json.dumps({"passed": ver["passed"], **pack["six_point_maintenance"]}))


if __name__ == "__main__":
    main()
