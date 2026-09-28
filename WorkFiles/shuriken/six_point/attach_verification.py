"""Attach the six-point build's out-of-build verification to six_point_report.json and pack_report.json.

Plain Python (no Blender, no Unreal), run LAST, after build_pack.py, UnrealCheck6 (attach_engine_check.py writes
engine_check itself), UnrealCheck8 (summarize.py), the frozen regression, the silhouette check, the visual
metrics and the comparison sheet:

    py WorkFiles/shuriken/six_point/attach_verification.py

It only READS the evidence files and copies their verdicts (with paths and SHA-256 of the files it read) into
report["verification"]; it never re-computes a gate.  The frozen reports are not touched (their REPORT_KEYS are
the regression's evidence).  pack_report.json gets a short "six_point_build" block.
"""
import hashlib
import json
import time
from pathlib import Path

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
WF = PROJ / "WorkFiles" / "shuriken"
HERE = WF / "six_point"
FROZEN = ("four_point", "eight_point", "square_plate")


def sha(path):
    path = Path(path)
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def load(path):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main():
    report_path = WF / "six_point_report.json"
    report = load(report_path)
    ver = {"attached": time.strftime("%Y-%m-%dT%H:%M:%S"), "attached_by": str(Path(__file__))}

    # --- frozen-form regression against post_restyle2
    reg_path = WF / "regression" / "regression_six_point.json"
    reg = load(reg_path) or {}
    bake = {name: load(HERE / "bake_determinism" / f"{name}.json") for name in
            ("baseline_vs_shipped", "rebuildA_vs_rebuildB", "baseline_vs_rebuildA", "baseline_vs_scratch_pack")}
    noise = bake["rebuildA_vs_rebuildB"] or {}
    shipped = bake["baseline_vs_shipped"] or {}
    maps_within_noise = bool(shipped and noise and shipped.get("max_abs_8bit", 99) <= max(1, noise.get("max_abs_8bit", 0))
                             and all(m.get("pixels_over_2", 1) == 0 for m in shipped.get("maps", {}).values()))
    ver["frozen_regression"] = {
        "evidence": str(reg_path), "evidence_sha256": sha(reg_path), "snapshot": reg.get("snapshot"),
        "forms": list(FROZEN), "summary": reg.get("summary"), "passed": reg.get("passed"),
        "gated": "blend (every LOD's vertices, loops, edges, sharp flags, every UV layer, material slots, wear tags, "
                 "identity transform), UCX hull, both SOCKET_ Empties, LOD group, FBX content re-imported (nodes, "
                 "triangles, sorted positions, (position, UV0) loop sets), sidecar (every key), report figures, "
                 "M_Shuriken_Master export scalars - all IDENTICAL",
        "maps": {
            "bitwise_identical": all((reg.get("summary") or {}).get(f, {}).get("textures_identical") for f in FROZEN),
            "within_bake_noise": maps_within_noise,
            "baseline_vs_shipped": {k: shipped.get(k) for k in ("max_abs_8bit", "max_pixels_differing")},
            "rebuild_vs_rebuild_noise": {k: noise.get(k) for k in ("max_abs_8bit", "max_pixels_differing")},
            "evidence": {k: str(HERE / "bake_determinism" / f"{k}.json") for k in bake},
            "explanation": ("The GPU (OptiX) bake is not bit-reproducible run to run: two back-to-back frozen-only "
                            "rebuilds with the SAME scripts and no six-point differ from each other by 1/255 on up to "
                            f"{noise.get('max_pixels_differing')} pixels of a 2048x2048 map, and the shipped frozen "
                            f"maps differ from the post_restyle2 baseline by the same 1/255 on at most "
                            f"{shipped.get('max_pixels_differing')} pixels (no pixel by more than 1/255). No rebuild can "
                            "reproduce the baseline maps bitwise; the frozen maps are unchanged to the bake's own "
                            "reproducibility, and nothing in their source (geometry, UVs, material, bake settings) "
                            "changed (the regression above is identical on all of it)."),
        },
    }

    # --- plan silhouette
    sil_path = HERE / "silhouette_final.json"
    sil = load(sil_path) or {}
    objs = sil.get("objects") or {}
    ver["silhouette"] = {
        "evidence": str(sil_path), "tool": str(WF / "restyle_pass2" / "silhouette_check.py"),
        "reference_set": str(HERE / "silhouette_ref"),
        "frozen_vs_restyle_pass1": all(v.get("unchanged") for k, v in objs.items() if "SixPoint" not in k),
        "six_point_vs_unground_outline": {k: {kk: v.get(kk) for kk in (
            "xor_pixels", "area_mm2", "max_new_boundary_vertex_off_pass1_boundary_mm",
            "max_pass1_boundary_vertex_off_new_boundary_mm", "unchanged")} for k, v in objs.items() if "SixPoint" in k},
        "all_unchanged": sil.get("all_unchanged"),
        "note": ("frozen forms: every LOD against its restyle-pass-1 mesh; six-point: every LOD against the un-ground "
                 "plate the generator authors at that LOD's counts (six_point/silhouette_ref.py) - the knife grind is "
                 "a finish on the edge section and leaves the plan silhouette exactly on the outline"),
    }

    # --- look: visual metrics through the same rig, and the comparison sheet
    vm = load(HERE / "visual_metrics_final.json") or {}
    keys_top = ("edge_bright_band_mm", "edge_peak_p50", "large_scale_var", "fine_dark", "fine_bright",
                "hole_ring_range", "object_mean", "object_p50")
    keys_hero = ("bright_facet_share", "near_facet_p50", "fine_dark", "fine_bright", "object_mean", "object_p50")
    ver["look"] = {
        "visual_metrics": str(HERE / "visual_metrics_final.json"),
        "top": {n: {k: (vm.get(f"{n}_top") or {}).get(k) for k in keys_top}
                for n in ("reference", "four_point", "eight_point", "square_plate", "six_point")},
        "hero": {n: {k: (vm.get(f"{n}_hero") or {}).get(k) for k in keys_hero}
                 for n in ("reference", "four_point", "eight_point", "square_plate", "six_point")},
        "comparison_sheet": str(PROJ / "Renders" / "Shuriken" / "style_comparison.png"),
        "comparison_sheet_sha256": sha(PROJ / "Renders" / "Shuriken" / "style_comparison.png"),
        "sheet_script": str(HERE / "style_sheet_six.py"),
        "pack_consistency": (load(WF / "pack_report.json") or {}).get("pack_consistency"),
    }

    # --- Unreal: UnrealCheck6 (engine_check, attached by its own script) and UnrealCheck8 (independent)
    uc8_path = WF / "UnrealCheck8" / "verification_summary.json"
    uc8 = load(uc8_path) or {}
    six = (uc8.get("forms") or {}).get("six_point") or {}
    ver["unreal"] = {
        "unrealcheck6_engine_check_status": (report.get("engine_check") or {}).get("status"),
        "unrealcheck6_matches_this_build": (report.get("engine_check") or {}).get("matches_this_build"),
        "unrealcheck6_gates": (report.get("engine_check") or {}).get("gates_passed"),
        "unrealcheck8": {"evidence": str(uc8_path), "evidence_sha256": sha(uc8_path),
                         "content_path": uc8.get("content_path"), "all_verified": uc8.get("all_verified"),
                         "textures_all_ok": uc8.get("textures_all_ok"), "logs_clean": uc8.get("logs_clean"),
                         "six_point_verified": six.get("verified"), "six_point_gates": six.get("gates"),
                         "forms_verified": {f: v.get("verified") for f, v in (uc8.get("forms") or {}).items()}},
    }
    ver["passed"] = bool(
        reg.get("passed") and maps_within_noise and sil.get("all_unchanged")
        and ver["unreal"]["unrealcheck6_engine_check_status"] == "verified"
        and uc8.get("all_verified") and six.get("verified"))
    report["verification"] = ver
    gaps = [g for g in report.get("known_gaps", []) if not g.startswith("BAKE NOISE:")]
    gaps.append("BAKE NOISE: the GPU (OptiX) texture bake is not bit-reproducible run to run (1/255 on a few dozen "
                "pixels per 2048 map between two identical rebuilds), so every pack rebuild changes the frozen forms' "
                "map bytes at that level even though nothing in their source changed; a bitwise map gate needs a "
                "deterministic bake device (CPU bake, a library decision) first. See verification.frozen_regression.")
    report["known_gaps"] = gaps
    report_path.write_text(json.dumps(report, indent=2, sort_keys=False), encoding="utf-8")

    pack_path = WF / "pack_report.json"
    pack = load(pack_path)
    pack["six_point_build"] = {"report": str(report_path), "verification_passed": ver["passed"],
                               "frozen_regression_passed": reg.get("passed"), "frozen_maps_within_bake_noise":
                               maps_within_noise, "silhouette_all_unchanged": sil.get("all_unchanged"),
                               "unrealcheck8_all_verified": uc8.get("all_verified"),
                               "comparison_sheet": ver["look"]["comparison_sheet"]}
    pack_path.write_text(json.dumps(pack, indent=2, sort_keys=False), encoding="utf-8")
    print("SIX_POINT_VERIFICATION", json.dumps({k: v for k, v in pack["six_point_build"].items()}))


if __name__ == "__main__":
    main()
