"""UnrealCheck12: evaluate every gate for SM_Kunai_Plain from the fresh-process evidence and write
verification_summary.json.  Plain Python (py summarize.py).

Evidence: b1_truth.json (Blender: Assets/Shuriken.blend + the shipped FBX), u1_import.json, u3_readback.json (fresh),
u4_textures_verify.json (fresh, Scripts/shuriken/ue_import_textures.py), u6_renderdata.json (fresh) via
b2_roundtrip.json, the Unreal re-export (u5) via b2_roundtrip.json, and the six commandlet logs u1..u6.
Expectations: the study (References/Kunai/KUNAI_STUDY.md section 4/5: 280 mm overall, 36 mm blade, 20 mm grip, pack
screen sizes 1.0 / 0.10 / 0.035 scaled by bounds radius / 50 mm, two hulls, Grip / Trail / Tip / Ring sockets), the
sidecar, and Blender's own reading - never the build's UnrealCheck6 result.
"""
import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[2]
FBX = PROJ / "Exports" / "Shuriken" / "SM_Kunai_Plain.fbx"
SIDECAR = PROJ / "Exports" / "Shuriken" / "SM_Kunai_Plain.sockets.json"


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


B1, U1, U3, U4, B2 = (load(n) for n in ("b1_truth.json", "u1_import.json", "u3_readback.json",
                                         "u4_textures_verify.json", "b2_roundtrip.json"))
SC = json.loads(SIDECAR.read_text(encoding="utf-8"))
REPORT = json.loads((PROJ / "WorkFiles" / "shuriken" / "kunai_plain_report.json").read_text(encoding="utf-8"))
M = U3["mesh"]
gates, detail, notes = {}, {}, []

# ---- bytes
fbx_now = sha256(FBX)
reg_md5 = M["registry_import_tag"]["parsed"][0]["FileMD5"]
gates["00_bytes_bound"] = (U1["fbx_sha256_before"] == U1["fbx_sha256_after"] == fbx_now == B1["fbx_sha256"]
                           == REPORT["export_sha256"]["fbx"] and reg_md5 == md5(FBX)
                           and U1["sidecar_sha256_before"] == sha256(SIDECAR) == REPORT["export_sha256"]["sidecar"])
detail["00_bytes_bound"] = {"fbx_sha256": fbx_now, "report_export_sha256": REPORT["export_sha256"]["fbx"],
                            "unreal_asset_import_md5": reg_md5, "fbx_md5": md5(FBX),
                            "sidecar_sha256": sha256(SIDECAR), "dest": U1["dest"], "save_mode": U1["save_mode"],
                            "dest_fresh": U1["dest_assets_before"] == []}

# ---- 1 LODs and triangles
blend_tris = [B1["blend_scene"]["lods"][f"LOD{i}"]["triangles"] for i in range(3)]
fbx_tris = [B1["fbx_scene"]["lods"][f"LOD{i}"]["triangles"] for i in range(3)]
per_slot_ok = all(
    [s["triangles"] for s in B2["render"]["lods"][f"LOD{i}"]["sections"]]
    == [B1["fbx_scene"]["lods"][f"LOD{i}"]["triangles_per_slot"][k] for k in ("0", "1")] for i in range(3))
gates["01_lods_and_triangles_equal_blender"] = (M["num_lods"] == 3 and M["lod_triangles"] == blend_tris == fbx_tris
                                                and per_slot_ok)
detail["01_lods_and_triangles_equal_blender"] = {"unreal": M["lod_triangles"], "blend": blend_tris, "fbx": fbx_tris,
                                                 "unreal_sections_per_lod": M["lod_sections"],
                                                 "per_slot_triangles_match_blender": per_slot_ok}

# ---- 2 collision
H = B2["hulls"]
c = B2["containment_in_unreal_hull_union_cm"]
hull_geo_ok = (B2["unreal_hull_components"] == 2 and B2["hull_components_matched_one_to_one"]
               and all(h["two_sided_vertex_distance_cm"] < 1e-5 and h["shipped_unique_verts"] == h["unreal_unique_verts"]
                       and h["shipped_tris"] == h["unreal_tris"]
                       and abs(h["shipped_volume_cm3"] - h["unreal_volume_cm3"]) < 1e-4
                       and h["unreal_self_convex_max_outside_cm"] < 1e-6 for h in H.values()))
gates["02_two_convex_hulls_geometry_lod0_inside"] = (M["convex_hulls"] == 2
                                                     and all(v == 0 for v in M["other_collision_elems"].values())
                                                     and hull_geo_ok and c["LOD0_shipped"] < 1e-4
                                                     and c["LOD0_unreal"] < 1e-4)
detail["02_two_convex_hulls_geometry_lod0_inside"] = {
    "convex_elems": M["convex_hulls"], "other_elems": M["other_collision_elems"],
    "unreal_ucx_nodes": B2["unreal_hull_nodes"], "components": B2["unreal_hull_components"],
    "per_hull": {k: {x: v[x] for x in ("two_sided_vertex_distance_cm", "unreal_unique_verts", "unreal_tris",
                                       "unreal_volume_cm3", "unreal_self_convex_max_outside_cm")} for k, v in H.items()},
    "containment_cm": c, "collision_trace_flag": M["collision_trace_flag"]}

# ---- 3 sockets
bmin, bmax = M["bounds_min_cm"], M["bounds_max_cm"]
side = {r["socket"]: r for r in SC["sockets"]}
sock_ok, sd = True, {}
for s in M["socket_objects"]:
    exp = side.get(s["name"])
    comp = M["component_sockets"].get(s["name"], {})
    ok = (s["found"] and exp is not None and s["outer"].startswith(f"{U3['dest']}/SM_Kunai_Plain")
          and s["relative_scale"] == [1.0, 1.0, 1.0] and comp.get("scale") == [1.0, 1.0, 1.0]
          and all(abs(a - b) < 1e-4 for a, b in zip(s["relative_location_cm"], exp["location_cm"]))
          and all(abs(v) < 1e-6 for v in s["relative_rotation"].values()))
    sd[s["name"]] = {"location_cm": s["relative_location_cm"], "scale": s["relative_scale"], "ok": ok,
                     "forward": comp.get("forward_x_axis"), "up": comp.get("up_z_axis")}
    sock_ok = sock_ok and ok
loc = {k: v["location_cm"][0] for k, v in sd.items()}
wrap_x = [(-102.0 + 21.06) / 10.0, (-6.0 + 21.06) / 10.0]
sane = {"grip_inside_wrap": wrap_x[0] < loc["Grip"] < wrap_x[1],
        "grip_at_design_x_-54mm": abs(loc["Grip"] - (-54.0 + 21.0563) / 10.0) < 1e-3,
        "trail_at_bounds_min_x": abs(loc["Trail"] - bmin[0]) < 1e-3,
        "tip_at_bounds_max_x": abs(loc["Tip"] - bmax[0]) < 1e-3,
        "ring_16mm_inside_trail": abs(loc["Ring"] - loc["Trail"] - 1.6) < 1e-3,
        "grip_plus_z_is_lettering_face": sd["Grip"]["up"] == [-0.0, 0.0, 1.0] or sd["Grip"]["up"] == [0.0, 0.0, 1.0],
        "plus_x_toward_tip": sd["Grip"]["forward"] == [1.0, 0.0, 0.0]}
gates["03_sockets_scale_1_sane_cm"] = (sock_ok and set(M["component_socket_names"]) == {"Grip", "Trail", "Tip", "Ring"}
                                      and all(sane.values()))
detail["03_sockets_scale_1_sane_cm"] = {"sockets": sd, "sane": sane}

# ---- 4 bounds vs the study
size = M["size_cm"]
study = {"overall_x_cm": 28.0, "blade_max_width_y_cm": 3.6, "grip_over_wrap_z_cm": 2.0}
gates["04_bounds_cm_match_study"] = (abs(size[0] - 28.0) < 1e-3 and abs(size[1] - 3.6) < 1e-3
                                    and abs(size[2] - B1["fbx_scene"]["lods"]["LOD0"]["ue_size_cm"][2]) < 1e-4)
detail["04_bounds_cm_match_study"] = {"unreal_size_cm": size, "study": study,
                                      "blender_predicted_size_cm": B1["fbx_scene"]["lods"]["LOD0"]["ue_size_cm"],
                                      "z_note": "Z 2.12 cm = the 21.2 mm collars (build ESTIMATE); the study grip is 20 mm",
                                      "sphere_radius_cm": M["bounds_sphere_radius_cm"],
                                      "blender_predicted_sphere_radius_cm":
                                          B1["fbx_scene"]["lods"]["LOD0"]["ue_bounds_sphere_radius_cm"]}

# ---- 5 screen sizes
r = M["bounds_sphere_radius_cm"]
rule = [1.0, round(0.10 * r / 5.0, 4), round(0.035 * r / 5.0, 4)]
ss = M["lod_screen_sizes"]
thr = B2["unreal_export_lodgroup"]["lod_groups"][0]["properties"]
gates["05_lod_screen_sizes_applied"] = (len(ss) == 3 and all(abs(a - b) < 1e-6 for a, b in zip(ss, SC["lod_screen_sizes"]))
                                       and SC["lod_screen_sizes"] == rule == [1.0, 0.28, 0.098]
                                       and abs(thr["Thresholds|Level0"][0] - 10.0 / ss[0]) < 1e-3
                                       and abs(thr["Thresholds|Level1"][0] - 10.0 / ss[1]) < 1e-3)
detail["05_lod_screen_sizes_applied"] = {"fresh_process": ss, "sidecar": SC["lod_screen_sizes"],
                                         "study_rule_from_unreal_radius": rule, "exporter_thresholds_10_over_render_ss": thr,
                                         "switch_m_at_90deg_hfov_16x9": [round(16.0 / 9.0 * r / 100.0 / s, 3) for s in ss[1:]]}

# ---- 6 lightmap
lm = [b for b in M["lod_build_settings"]]
uv1 = {k: B2["lods"][k]["uv1"] for k in ("LOD0", "LOD1", "LOD2")}
ctl = all(B2["lods"][k]["uv1_negative_control"]["detects"] for k in uv1)
gates["06_lightmap_index_1_uv1_0_1_no_overlap"] = (
    M["light_map_coordinate_index"] == 1
    and all(b["generate_lightmap_u_vs"] and b["src_lightmap_index"] == 0 and b["dst_lightmap_index"] == 1 for b in lm)
    and all(B2["lods"][k]["unreal_uv_channels"][1:] for k in uv1)
    and all(v["inside_0_1"] and v["overlapping_pairs"] == 0 and v["zero_area_triangles"] == 0
            and all(t["texels_claimed_by_two_charts"] == 0 for t in v["texel"].values()) for v in uv1.values()) and ctl)
detail["06_lightmap_index_1_uv1_0_1_no_overlap"] = {
    "light_map_coordinate_index": M["light_map_coordinate_index"], "light_map_resolution": M["light_map_resolution"],
    "per_lod": {k: {"u": v["u_range"], "v": v["v_range"], "overlapping_pairs": v["overlapping_pairs"],
                    "shared_texels": {rr: t["texels_claimed_by_two_charts"] for rr, t in v["texel"].items()},
                    "charts": v["charts"]} for k, v in uv1.items()},
    "negative_control_detects": ctl}

# ---- 7 material slots
slots = [s["slot"] for s in M["material_slots"]]
gates["07_two_material_slots_every_lod"] = (slots == ["M_Shuriken_Master", "M_Kunai_Wrap"]
                                           and M["lod_section_material_slot"] == [[0, 1], [0, 1], [0, 1]]
                                           and all([s["material_slot"] for s in B2["render"]["lods"][f"LOD{i}"]["sections"]]
                                                   == [0, 1] for i in range(3)))
detail["07_two_material_slots_every_lod"] = {"slots": M["material_slots"], "section_to_slot": M["lod_section_material_slot"],
                                             "section_uv_tiles": {k: [(s["material_slot"], s["u_range"]) for s in v["sections"]]
                                                                  for k, v in B2["render"]["lods"].items()}}

# ---- 8 textures
want = {"BC": ("True", "TC_DEFAULT"), "ORM": ("False", "TC_MASKS"), "N": ("False", "TC_NORMALMAP"),
        "Lettering": ("False", "TC_GRAYSCALE")}
tex = {}
tex_ok = True
for stem, t in U3["textures"].items():
    kind = stem.rsplit("_", 1)[-1]
    i = t["info"]
    s, comp = want[kind]
    ok = (i.get("srgb") == s and comp in i.get("compression_settings", "")
          and i["registry_import_tag"]["parsed"][0]["FileMD5"] == t["png_md5_now"])
    if kind == "N":
        ok = ok and i.get("flip_green_channel") == "False"
    if kind == "Lettering":
        ok = ok and "TA_CLAMP" in i["address_x"] and "TA_CLAMP" in i["address_y"] and "STRETCH" in i["power_of_two_mode"]
    if stem.startswith("T_Kunai_Wrap_"):
        ok = ok and "TA_WRAP" in i["address_x"] and "TA_WRAP" in i["address_y"]
    tex_ok = tex_ok and ok
    if t["kunai"]:
        tex[stem] = {"srgb": i["srgb"], "compression": i["compression_settings"], "flip_green": i["flip_green_channel"],
                     "address": [i["address_x"], i["address_y"]], "pot": i["power_of_two_mode"],
                     "mip_gen_settings": i["mip_gen_settings"], "size": i["size"], "imported_bytes_md5_match": True,
                     "ok": ok}
gates["08_texture_srgb_and_compression"] = tex_ok and U4["passed"] and len(U3["textures"]) == 26
detail["08_texture_srgb_and_compression"] = {"kunai_maps": tex, "ue_import_textures_verify_passed": U4["passed"],
                                             "maps_checked": len(U3["textures"])}
lett = U3["textures"]["T_Kunai_Lettering"]["info"]
gates["08b_lettering_mask_has_mips"] = "NO_MIPMAPS" not in lett["mip_gen_settings"]
probe = load("u7_mip_probe_verify.json")
detail["08b_lettering_mask_has_mips"] = {"mip_gen_settings": lett["mip_gen_settings"],
                                         "power_of_two_mode": lett["power_of_two_mode"],
                                         "probe_fresh_process": {k: v["fresh_process"]["mip_gen_settings"]
                                                                 for k, v in probe["copies"].items()}}

# ---- 9 logs
logs = {}
for s in ("u1", "u2", "u3", "u4", "u5", "u6"):
    lines = (HERE / f"{s}.log").read_text(encoding="utf-8", errors="replace").splitlines()
    strict = [ln for ln in lines if re.search(r":\s*(Warning|Error)\s*:", ln)]
    summary = [ln for ln in lines if "Success - " in ln or "Failure - " in ln]
    stderr = (HERE / f"{s}.log.stderr").read_text(encoding="utf-8", errors="replace").strip()
    logs[s] = {"lines": len(lines), "strict_warning_error": len(strict), "engine_summary": summary[-1][-40:] if summary else None,
               "stderr_bytes": len(stderr)}
gates["09_zero_warning_error_lines"] = all(v["strict_warning_error"] == 0 and v["stderr_bytes"] == 0 for v in logs.values())
detail["09_zero_warning_error_lines"] = logs

# ---- 10 render data + round trip agree with the FBX truth
rd = B2["render"]["lods"]
rt = B2["lods"]
gates["10_render_data_and_roundtrip_match_fbx"] = all(
    rd[k]["position_two_sided_max_cm"] < 1e-4 and rd[k]["uv0_unreal_to_fbx"]["no_position_match"] == 0
    and rd[k]["uv0_fbx_to_unreal"]["no_position_match"] == 0
    and rd[k]["uv0_unreal_to_fbx"]["worst_delta_over_float16_half_ulp"] <= 1.0
    and rd[k]["uv0_fbx_to_unreal"]["worst_delta_over_float16_half_ulp"] <= 1.0
    and rd[k]["normals_fbx_to_unreal"]["worst_deg"] < 1.0 and rd[k]["normals_unreal_to_fbx"]["worst_deg"] < 1.0
    and rt[k]["shipped_tris"] == rt[k]["unreal_tris"] and rt[k]["position_two_sided_max_cm"] < 1e-4
    and rt[k]["uv0_unreal_to_shipped"]["no_position_match"] == 0
    and rt[k]["uv0_unreal_to_shipped"]["worst_uv_axis_delta"] <= 2.0 ** -11 for k in rd)
detail["10_render_data_and_roundtrip_match_fbx"] = {
    k: {"render_pos_cm": rd[k]["position_two_sided_max_cm"],
        "render_uv0_over_f16_half_ulp": max(rd[k]["uv0_unreal_to_fbx"]["worst_delta_over_float16_half_ulp"],
                                            rd[k]["uv0_fbx_to_unreal"]["worst_delta_over_float16_half_ulp"]),
        "render_normals_deg": max(rd[k]["normals_fbx_to_unreal"]["worst_deg"], rd[k]["normals_unreal_to_fbx"]["worst_deg"]),
        "roundtrip_pos_cm": rt[k]["position_two_sided_max_cm"],
        "roundtrip_uv0_max_delta": rt[k]["uv0_unreal_to_shipped"]["worst_uv_axis_delta"],
        "roundtrip_normals_deg": rt[k]["normals_unreal_to_shipped"]["worst_deg"]} for k in rd}

# ---- 11 lettering band in Unreal's render data
band = {k: rd[k]["lettering_band"] for k in rd}
xr = [(-90.0 + 21.0563) / 10.0, (-18.0 + 21.0563) / 10.0]
gates["11_lettering_band_plus_z_every_lod"] = all(
    b["triangles"] > 0 and abs(b["x_cm"][0] - xr[0]) < 1e-3 and abs(b["x_cm"][1] - xr[1]) < 1e-3
    and b["z_cm"][0] > 0.8 and b["corr_u_x"] > 0.999 and b["corr_v_unreal_y"] > 0.999 for b in band.values())
detail["11_lettering_band_plus_z_every_lod"] = {"expected_x_cm": xr, "rect_unreal": B2["render"]["rect_unreal"],
                                                "per_lod": band}

# ---- information
info = {
    "nanite_enabled": M["nanite_enabled"], "import_settings": M["import_settings"],
    "body_instance_on_asset": M.get("body_instance"),
    "unreal_hull_derived_com_cm_blender_axes": B2["unreal_hull_derived_com_cm_blender_axes"],
    "com_nudge_to_reach_pivot_cm_unreal_axes": B2["com_nudge_needed_to_reach_pivot_cm_unreal_axes"],
    "report_claimed_com_nudge_cm": REPORT.get("measured", {}).get("centre_of_mass_and_pivot"),
    "lettering_band_v_unreal_float16_vs_documented": {
        "stored": [band["LOD0"]["v"][0], band["LOD0"]["v"][1]],
        "documented": [B2["render"]["rect_unreal"]["v_min"], B2["render"]["rect_unreal"]["v_max"]]},
    "run1_double_save_warning": "run1_double_save/u1.log: LogPackageName GetLocalFullPath warning during the "
                                "sidecar's second save (UncontrolledChangelists discovery race); race_probe_*.out",
}
out = {"asset": "SM_Kunai_Plain", "dest": U3["dest"], "engine": U3["engine"], "gates": gates,
       "all_gates_passed": all(gates.values()), "failed": [k for k, v in gates.items() if not v],
       "detail": detail, "info": info}
(HERE / "verification_summary.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
for k, v in gates.items():
    print(("PASS " if v else "FAIL ") + k)
print("ALL", out["all_gates_passed"], out["failed"])
