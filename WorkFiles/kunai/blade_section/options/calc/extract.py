"""Pull the comparison figures out of a kunai_plain_report.json (+ pack_report.json).  Pure python.
usage: python extract.py <report.json> [pack_report.json]  -> prints JSON"""
import json
import sys


def g(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d


def extract(rep_path, pack_path=None):
    r = json.load(open(rep_path, encoding="utf-8"))
    m = r["measured"]
    out = {
        "steel_unground_g": m.get("steel_unground_mass_g"),
        "steel_finished_g": m.get("steel_ground_mass_g"),
        "assembled_g": m.get("assembled_mass_g"),
        "wrap_g": m.get("wrap_mass_g"),
        "mass_target_g": m.get("mass_target_g"),
        "mass_error_g": m.get("mass_error_g"),
        "mass_gate_passed": g(m, "mass_gate", "passed"),
        "pivot_design_x_mm": m.get("pivot_design_x_mm"),
        "centre_of_volume_x_mm": m.get("centre_of_volume_x_mm"),
        "thickness_mm": m.get("thickness_mm"),
        "apex_x_mm": m.get("apex_x_mm"),
        "grind_width_mm": g(m, "grind", "grind_width_mm"),
        "tip_edge_height_mm": m.get("tip_edge_height_mm"),
        "min_edge_mm": m.get("min_edge_mm"), "min_face_area_mm2": m.get("min_face_area_mm2"),
        "unreal_bounds_sphere_radius_mm": m.get("unreal_bounds_sphere_radius_mm"),
        "overall_z_mm": m.get("overall_z_mm"), "overall_y_mm": m.get("overall_y_mm"),
        "lod_triangles": r.get("lod_triangles"),
        "lod_bands_ok": r.get("lod_bands_ok"),
        "lod1_is_distinct": r.get("lod1_is_distinct"),
        "physics": {k: g(r, "physics", k) for k in ("mass_kg_override", "mass_kg_override_exact")},
        "collision": {k: g(r, "collision_choice", k) for k in
                      ("hull_derived_centre_of_mass_mm", "unreal_com_nudge_cm", "two_hulls_mm3", "one_hull_mm3",
                       "three_hulls_mm3", "render_mesh_mm3")},
        "hulls": g(r, "collision_choice", "hulls"),
        "gates": r.get("gates"),
        "form_gates": r.get("form_gates"),
        "render_gates": r.get("render_gates"),
        "qa_passed": g(r, "qa", "passed"),
        "qa_failed": [c for c in (g(r, "qa", "checks") or []) if isinstance(c, dict) and not c.get("passed", True)],
        "hero_coat": g(r, "render_stats", "kunai_plain_persp", "coat_luminance"),
        "top_coat": g(r, "render_stats", "kunai_plain_top", "coat_luminance"),
        "texel": g(r, "uv", "px_per_cm"),
        "uv_consistency": g(r, "uv_consistency"),
        "symmetry_max_dev_mm": g(r, "symmetry", "max_deviation_mm"),
        "knife_shading": g(r, "knife_shading"),
    }
    if pack_path:
        p = json.load(open(pack_path, encoding="utf-8"))
        pc = p.get("pack_consistency") or {}
        out["pack_passed"] = p.get("passed")
        out["pack_consistency_passed"] = pc.get("passed")
        out["knife_coat_vs_anchor"] = pc.get("knife_coat_vs_coat_anchor")
        out["pack_consistency_failures"] = {k: v for k, v in pc.items() if isinstance(v, dict) and v.get("passed") is False}
        out["result_passed"] = g(p, "results", "kunai_plain", "passed")
    return out


if __name__ == "__main__":
    print(json.dumps(extract(*sys.argv[1:]), indent=1, default=str))
