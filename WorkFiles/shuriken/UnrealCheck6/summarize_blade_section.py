"""Condense the blade-section Unreal run (UC6_OUT, default blade_section_c1/) into one JSON: per-form gates, the kunai's
detail (LOD tri deltas, hulls, sockets, bounds, screen sizes, UV1 overlap, sections, lettering band gate 13), texture
flags, log Warning/Error counts, input SHA-256 before/after, and the six forms against their earlier (KunaiFix6) run.

    py summarize_blade_section.py
"""
import json
import os
import re
from pathlib import Path

HERE = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\shuriken\UnrealCheck6")
OUT = Path(os.environ.get("UC6_OUT") or HERE / "blade_section_c1")
FORMS = ("kunai_plain", "four_point", "eight_point", "square_plate", "six_point", "spike", "hooked_cross")
PAT = re.compile(r":\s*(Warning|Error)\s*:")


def j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def we(p):
    try:
        return sum(1 for line in Path(p).read_text(encoding="utf-8", errors="replace").splitlines() if PAT.search(line))
    except OSError:
        return None


res = {"out": str(OUT), "forms": {}}
rt = j(OUT / "roundtrip_compare.json")
old_rt = j(HERE / "roundtrip_compare.json")
for f in FORMS:
    p1, p2, p3 = (j(OUT / f"{f}_pass{i}.json") for i in (1, 2, 3))
    o2 = j(HERE / f"{f}_pass2.json")          # the earlier run (KunaiFix6), for the six's "identical" comparison
    keys = ("lod_triangles", "lod_vertices", "lod_sections", "lod_screen_sizes", "convex_hulls", "size_cm",
            "bounds_min_cm", "bounds_max_cm", "sockets", "light_map_coordinate_index", "light_map_resolution",
            "lod_source_uv_channels", "gates")
    same_as_old = {k: p2.get(k) == o2.get(k) for k in keys}
    lods = rt.get(f, {}).get("lods", {})
    rec = {
        "fbx_sha256": p1.get("fbx_sha256"), "sidecar_sha256": p1.get("sidecar_sha256"),
        "asset_existed_before_import": p1.get("asset_existed_before_import"), "saved": p1.get("saved"),
        "pass1_error": p1.get("error"), "pass2_error": p2.get("error"), "pass3_export_ok": p3.get("export_ok"),
        "gates": p2.get("gates"), "passed_1_to_6": p2.get("passed_1_to_6"),
        "tri_delta": (p2.get("gate_detail") or {}).get("triangle_delta"),
        "lod_triangles": p2.get("lod_triangles"), "lod_sections": p2.get("lod_sections"),
        "convex_hulls": p2.get("convex_hulls"), "size_cm": p2.get("size_cm"),
        "screen_sizes": p2.get("lod_screen_sizes"), "sockets": p2.get("sockets"),
        "lod_bands_ok": (p2.get("gate_detail") or {}).get("lod_bands_ok"),
        "warning_error_lines": {n: we(OUT / f"{f}_pass{n}.log") for n in (1, 2, 3)},
        "roundtrip": {k: {"pos_cm": v.get("position_two_sided_max_cm"),
                          "tris": [v.get("shipped_tris"), v.get("unreal_tris")],
                          "uv0_keyed_cm": (v.get("uv0_keyed_position_check") or {}).get("max_position_diff_cm"),
                          "uv1_inside_0_1": (v.get("uv1_lightmap") or {}).get("inside_0_1"),
                          "uv1_overlap_1024": (v.get("uv1_lightmap") or {}).get("overlap_pixels"),
                          "uv1_overlap_2048": (v.get("uv1_lightmap_2048") or {}).get("overlap_pixels")}
                      for k, v in lods.items()},
        "hull_vs_shipped_cm": rt.get(f, {}).get("hull_shipped_vs_unreal_two_sided_max_cm"),
        "part_hulls": {k: v for k, v in (rt.get(f, {}).get("part_hulls") or {}).items()
                       if k in ("union_lod0_max_outside_cm", "distinct_unreal_hulls_matched", "matches")},
        "unreal_hulls": rt.get(f, {}).get("unreal_hulls"),
        "pass2_same_as_previous_run": same_as_old,
        "roundtrip_same_as_previous_run": rt.get(f) == old_rt.get(f),
    }
    if f == "kunai_plain":
        k = p2.get("kunai") or {}
        rec["gate13"] = {"passed": k.get("passed"), "slots": k.get("slots"), "lod_sections": k.get("lod_sections"),
                         "rect_unreal": k.get("rect_unreal"),
                         "lods": {n: {"passed": v.get("passed"), "tiles_ok": v.get("tiles_ok"),
                                      "band_ok": v.get("band_ok"),
                                      "sections": v.get("sections"),
                                      "band": {kk: (v.get("lettering_band") or {}).get(kk) for kk in (
                                          "corners", "triangles", "corner_x_cm", "centroid_x_cm", "expected_x_cm",
                                          "centroid_z_min_cm", "z_floor_cm", "corr_u_x", "corr_v_unreal_y",
                                          "map_max_du_texels", "map_max_dv_texels", "band_length_covered")}}
                                  for n, v in (k.get("lods") or {}).items()},
                         "dirty_before_after": [k.get("dirty_packages_before"), k.get("dirty_packages_after")],
                         "allow_cpu_access_saved": k.get("allow_cpu_access_saved")}
    if f == "hooked_cross":
        rec["handedness"] = (p2.get("handedness") or {}).get("passed")
        rec["handedness_render"] = (p2.get("handedness_render") or {}).get("passed")
    res["forms"][f] = rec
for mode in ("import", "verify"):
    t = j(OUT / f"textures_{mode}.json")
    maps = t.get("maps", {})
    res[f"textures_{mode}"] = {
        "passed": t.get("passed"), "maps": len(maps),
        "warning_error_lines": we(OUT / f"textures_{mode}.log"),
        "failures": {s: m.get("matches_intent") or m.get("in_process_matches_intent") or m.get("error")
                     for s, m in maps.items()
                     if not ((m.get("matches_intent") or m.get("in_process_matches_intent") or {}).get("all"))},
        "kunai": {s: {kk: (m.get("flags") or m.get("after_apply_in_process") or {}).get(kk)
                      for kk in ("srgb", "compression_settings", "mip_gen_settings", "address_x", "address_y",
                                 "power_of_two_mode", "flip_green_channel", "size")}
                  | ({"sha256": m.get("sha256")} if m.get("sha256") else {})
                  for s, m in maps.items() if s.startswith("T_Kunai_")},
    }
b, a = j(OUT / "input_sha256_before.json"), j(OUT / "input_sha256_after.json")
imp = j(OUT / "textures_import.json")
tex_sha_ok = all(a["files"].get(str(Path(m["png"]).relative_to(Path(r"C:\Users\Cody\Desktop\Blender_Projects")))
                                .replace("\\", "/")) == m.get("sha256") for m in imp["maps"].values())
res["inputs"] = {"files": len(a["files"]), "before_equals_after": b["files"] == a["files"],
                 "frozen_six_overlap": a.get("frozen_six_overlap_checked"),
                 "frozen_six_mismatches": a.get("frozen_six_mismatches"),
                 "texture_sha_imported_equals_disk": tex_sha_ok,
                 "fbx_sidecar_imported_equals_disk": all(
                     a["files"].get(f"Exports/Shuriken/{j(OUT / f'{f}_pass1.json')['fbx'].split(chr(92))[-1]}")
                     == res["forms"][f]["fbx_sha256"] for f in FORMS)}
(OUT / "blade_section_summary.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
print(json.dumps({f: {"gates_all": all((r["gates"] or {}).values()), "we": r["warning_error_lines"],
                      "same_as_prev": all(r["pass2_same_as_previous_run"].values()),
                      "rt_same": r["roundtrip_same_as_previous_run"]} for f, r in res["forms"].items()}, indent=0))
print("textures", res["textures_import"]["passed"], res["textures_verify"]["passed"],
      res["textures_import"]["warning_error_lines"], res["textures_verify"]["warning_error_lines"])
print("inputs", res["inputs"])
