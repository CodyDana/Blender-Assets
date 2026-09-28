"""UnrealCheck10: evaluate every gate for SM_Shuriken_Spike from the fresh-process results and write
verification_summary.json.  Plain Python (py summarize.py); reads b1_truth.json, u1_import.json,
u2_textures_import.json, u3_readback.json, u4_textures_verify.json, u5_export.json, b2_roundtrip.json and the
five Unreal logs.  Expectations come from the spec numbers and the .blend / shipped-FBX truth, not the build report.
"""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parents[2]


def j(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def close(a, b, tol):
    return len(a) == len(b) and all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


b1, u1, u2, u3, u4, u5, b2 = (j(n) for n in ("b1_truth.json", "u1_import.json", "u2_textures_import.json",
                                               "u3_readback.json", "u4_textures_verify.json", "u5_export.json",
                                               "b2_roundtrip.json"))
spec, blend, fbx = b1["spec"], b1["blend_scene"], b1["fbx_scene"]
m = u3["mesh"]
side = json.loads((PROJ / "Exports" / "Shuriken" / "SM_Shuriken_Spike.sockets.json").read_text(encoding="utf-8"))
G, D = {}, {}

# G0 exact bytes
sha_now = sha256(PROJ / "Exports" / "Shuriken" / "SM_Shuriken_Spike.fbx")
reg = (m.get("registry_import_tag") or {}).get("parsed") or [{}]
G["G0_exact_bytes"] = (b1["fbx_sha256"] == b1["fbx_sha256_after"] == u1["fbx_sha256_before"] == u1["fbx_sha256_after"]
                       == u3["fbx_sha256_now"] == sha_now
                       and reg[0].get("FileMD5") == u1["fbx_md5"] == u3["fbx_md5_now"]
                       and u1["sidecar_sha256_before"] == u1["sidecar_sha256_after"] == u3["sidecar_sha256_now"]
                       == b1["sidecar_sha256"]
                       and m.get("import_filenames") == ["C:/Users/Cody/Desktop/Blender_Projects/Exports/Shuriken/SM_Shuriken_Spike.fbx"])
D["G0"] = {"fbx_sha256": sha_now, "fbx_md5": u1["fbx_md5"], "unreal_recorded_md5": reg[0].get("FileMD5"),
           "sidecar_sha256": u3["sidecar_sha256_now"], "fresh_dest": u1["dest"],
           "dest_existed_before": u1["dest_existed_before"], "dest_assets_before": u1["dest_assets_before"]}
G["G0_fresh_content_path"] = u1["dest_existed_before"] is False and u1["dest_assets_before"] == []

# G1 LODs
blend_t = [blend["lods"][f"LOD{i}"]["triangles"] for i in range(3)]
fbx_t = [fbx["lods"][f"LOD{i}"]["triangles"] for i in range(3)]
rt_t = [b2["lods"][f"LOD{i}"]["unreal_tris"] for i in range(3)]
G["G1_lod_count_3_tris_equal_blender"] = (m["num_lods"] == 3 and m["lod_count_subsystem"] == 3
                                         and m["lod_triangles"] == blend_t == fbx_t == rt_t
                                         == spec["lod_triangles_formula"])
D["G1"] = {"unreal": m["lod_triangles"], "blend": blend_t, "fbx_reimport": fbx_t, "unreal_reexport": rt_t,
           "formula_16K_plus_28": spec["lod_triangles_formula"], "unreal_render_vertices": m["lod_vertices"],
           "blend_vertices": [blend["lods"][f"LOD{i}"]["vertices"] for i in range(3)]}

# G2 one hull, identical to the shipped UCX, LOD0 0.0 cm outside
h = b2["hull"]
ship_ucx = [k for k in fbx["hulls"]]
G["G2_exactly_one_convex_hull"] = (m["convex_hulls"] == 1 and all(v == 0 for v in m["other_collision_elems"].values())
                                   and ship_ucx == ["UCX_SM_Shuriken_Spike_LOD0_00"]
                                   and fbx["hulls"]["UCX_SM_Shuriken_Spike_LOD0_00"]["keys_to_render_node"]
                                   and len(b2["unreal_hull_nodes"]) == 1)
G["G2_stored_hull_identical_to_shipped_ucx"] = (h["shipped"]["unique_verts"] == h["unreal"]["unique_verts"] == 16
                                                and h["shipped"]["tris"] == h["unreal"]["tris"] == 28
                                                and h["vertex_sets_equal_1e-5cm"]
                                                and h["two_sided_vertex_distance_cm"] <= 1e-6
                                                and abs(h["shipped"]["volume_cm3"] - h["unreal"]["volume_cm3"])
                                                <= 1e-6 * h["shipped"]["volume_cm3"])
LOD0_OUT = max(h["lod0_shipped_max_outside_unreal_hull_cm"], h["lod0_unreal_max_outside_unreal_hull_cm"])
G["G2_lod0_0.0cm_outside_hull"] = LOD0_OUT <= 1e-6 and h["lod1_lod2_unreal_max_outside_unreal_hull_cm"] <= 1e-6
D["G2"] = {"hull": h, "lod0_max_outside_cm": LOD0_OUT, "lod0_max_outside_cm_rounded_5dp": round(LOD0_OUT, 5),
           "note": "1e-6 cm = 10 nm; the residual is float32 position quantisation (1 ulp at 7.9 cm = 4.8e-7 cm)"}

# G3 sockets
socks = {s["name"]: s for s in m["socket_objects"]}
exp = {r["socket"]: r for r in side["sockets"]}
bsock = {k.rsplit("_", 1)[-1]: v for k, v in blend["sockets"].items() if "Spike" in k}
x_min, x_max = m["bounds_min_cm"][0], m["bounds_max_cm"][0]
sd = {}
ok3 = set(m["component_socket_names"]) == {"Grip", "Trail"} == set(exp) == set(bsock)
for name in ("Grip", "Trail"):
    s, e, b = socks.get(name, {}), exp.get(name), bsock.get(name)
    c = m["component_sockets"].get(name, {})
    r = s.get("relative_rotation", {})
    one = (bool(s.get("found")) and e is not None and b is not None
           and (s.get("outer") or "").startswith(u3["asset"] + ".")
           and close(s["relative_scale"], [1.0, 1.0, 1.0], 0.0) and close(c["scale"], [1.0, 1.0, 1.0], 1e-6)
           and close(s["relative_location_cm"], e["location_cm"], 1e-6)
           and close(s["relative_location_cm"], b["ue_location_cm"], 1e-4)
           and close(c["location_cm"], e["location_cm"], 1e-5)
           and all(abs(r[k]) < 1e-6 for k in ("roll", "pitch", "yaw"))
           and close(c["forward_x_axis"], [1.0, 0.0, 0.0], 1e-6)
           and abs(s["relative_location_cm"][1]) < 1e-6 and abs(s["relative_location_cm"][2]) < 1e-6
           and x_min - 1e-4 <= s["relative_location_cm"][0] <= x_max)
    sd[name] = {"ok": one, "unreal_cm": s.get("relative_location_cm"), "sidecar_cm": e and e["location_cm"],
                "blend_cm": b and b["ue_location_cm"], "scale": s.get("relative_scale"),
                "component_scale": c.get("scale"), "forward": c.get("forward_x_axis"),
                "from_butt_mm": round((s["relative_location_cm"][0] - x_min) * 10.0, 4) if s.get("found") else None}
    ok3 = ok3 and one
sane = (abs(sd["Trail"]["from_butt_mm"]) < 0.01 and abs(sd["Grip"]["from_butt_mm"] - spec["grip_from_butt_mm_design"]) < 0.01
        and socks["Grip"]["relative_location_cm"][0] < 0.0)
G["G3_grip_trail_scale_1_sane_locations"] = ok3 and sane
D["G3"] = sd

# G4 bounds
G["G4_bounds_cm_match_spec"] = (close(m["size_cm"], spec["size_cm_expected"], 5e-5)
                                and close(m["bounds_min_cm"], blend["lods"]["LOD0"]["ue_bounds_min_cm"], 1e-5)
                                and close(m["bounds_max_cm"], blend["lods"]["LOD0"]["ue_bounds_max_cm"], 1e-5)
                                and abs(m["bounds_sphere_radius_cm"] - spec["bounds_sphere_radius_mm_expected"] / 10.0) < 1e-4)
e0 = b2["lods"]["LOD0"]["ends_unreal"]
G["G4_point_on_plus_x"] = (abs(e0["plus_x_end_half_width_cm"][0] - 0.0075) < 1e-5 and abs(e0["minus_x_end_half_width_cm"][0] - 0.15) < 1e-5
                           and abs(e0["x_max_cm"] - x_max) < 1e-5)
D["G4"] = {"unreal_size_cm": m["size_cm"], "spec_cm": spec["size_cm_expected"], "min": m["bounds_min_cm"],
           "max": m["bounds_max_cm"], "sphere_radius_cm": m["bounds_sphere_radius_cm"],
           "sphere_radius_spec_cm": spec["bounds_sphere_radius_mm_expected"] / 10.0,
           "origin_to_butt_mm": -x_min * 10.0, "blend_com_from_butt_mm": blend["lod0_com_from_butt_mm"],
           "blend_com_residual_mm": blend["lod0_com_mm"], "ends": e0}

# G5 screen sizes
ss = m["lod_screen_sizes"]
G["G5_lod_screen_sizes_applied"] = (close(ss, side["lod_screen_sizes"], 1e-6) and close(side["lod_screen_sizes"], spec["screen_sizes_expected"], 1e-9))
r_cm = m["bounds_sphere_radius_cm"]
D["G5"] = {"unreal": ss, "sidecar": side["lod_screen_sizes"], "spec": spec["screen_sizes_expected"],
           "switch_distance_m_16x9_90deg_from_unreal_radius": [round(1.7778 * r_cm / 100.0 / s, 4) for s in ss[1:]],
           "before_sidecar_in_process": u1["sidecar_result"]["lod_screen_sizes"].get("before")}

# G6 lightmap
bs = m["lod_build_settings"]
uv1 = {k: v["uv1"] for k, v in b2["lods"].items()}
G["G6_lightmap_index_1_uv1_0_1_no_overlap"] = (m["light_map_coordinate_index"] == 1
                                              and all(b["generate_lightmap_u_vs"] is True and b["src_lightmap_index"] == 0
                                                      and b["dst_lightmap_index"] == 1 for b in bs)
                                              and all(len(v["unreal_uv_channels"]) == 2 for v in b2["lods"].values())
                                              and all(u["inside_0_1"] and u["overlapping_pairs"] == 0
                                                      and u["overlap_area_total"] == 0.0 and u["zero_area_triangles"] == 0
                                                      for u in uv1.values())
                                              and all(v["uv1_negative_control"]["detects"] for v in b2["lods"].values()))
D["G6"] = {"light_map_coordinate_index": m["light_map_coordinate_index"], "light_map_resolution": m["light_map_resolution"],
           "uv1": uv1, "negative_control": {k: v["uv1_negative_control"] for k, v in b2["lods"].items()}}

# G7 textures
tex_ok, td = True, {}
want = {"BC": ("True", "TC_DEFAULT", None), "ORM": ("False", "TC_MASKS", None), "N": ("False", "TC_NORMALMAP", "False")}
for kind, rec in u3["textures"].items():
    info = rec["info"]
    srgb, comp, flip = want[kind]
    regt = (info.get("registry_import_tag") or {}).get("parsed") or [{}]
    stem = f"T_Shuriken_Spike_{kind}"
    v = u4["maps"].get(stem, {})
    ok = (info.get("class") == "Texture2D" and info.get("srgb") == srgb and comp in info.get("compression_settings", "")
          and (flip is None or info.get("flip_green_channel") == flip) and info.get("size") == [2048, 2048]
          and regt[0].get("FileMD5") == rec["png_md5_now"] == md5(rec["png"])
          and u2["maps"][stem]["sha256"] == rec["png_sha256_now"] == sha256(rec["png"])
          and (v.get("matches_intent") or {}).get("all") is True)
    td[kind] = {"ok": ok, "srgb": info.get("srgb"), "compression": info.get("compression_settings"),
                "flip_green": info.get("flip_green_channel"), "lod_group": info.get("lod_group"), "size": info.get("size"),
                "png_sha256": rec["png_sha256_now"], "unreal_recorded_md5": regt[0].get("FileMD5"),
                "as_imported_before_flags": u2["maps"][stem].get("as_imported_matches_intent")}
    tex_ok = tex_ok and ok
G["G7_textures_bc_srgb_orm_linear_masks_n_linear_normalmap"] = tex_ok and u4["passed"] is True
D["G7"] = td

# G8 logs
logs = {}
for s in ("u1", "u2", "u3", "u4", "u5"):
    text = (HERE / f"{s}.log").read_text(encoding="utf-8", errors="replace").splitlines()
    strict = [ln for ln in text if re.search(r":\s*(Warning|Error)\s*:", ln)]
    summary = [ln for ln in text if "Success - 0 error(s), 0 warning(s)" in ln]
    stderr = (HERE / f"{s}.log.stderr").read_text(encoding="utf-8", errors="replace").strip()
    logs[s] = {"lines": len(text), "warning_error_lines": len(strict), "first": strict[:5],
               "commandlet_summary_0_0": bool(summary), "stderr_bytes": len(stderr)}
G["G8_zero_warning_error_lines"] = all(v["warning_error_lines"] == 0 and v["commandlet_summary_0_0"] and v["stderr_bytes"] == 0
                                       for v in logs.values())
D["G8"] = logs

# informational round-trip fidelity
D["info_roundtrip"] = {k: {"position_two_sided_max_cm": v["position_two_sided_max_cm"], "uv0_ok": v["uv0"]["ok"],
                           "uv0_worst": v["uv0"]["unreal_to_shipped"]["worst_uv0_axis_delta"],
                           "normals_max_deg": max(v["normals"].values())} for k, v in b2["lods"].items()}
D["info_asset"] = {"material_slots": m["material_slots"], "sections": m["lod_sections"], "nanite": m["nanite_enabled"],
                   "body_mass_override": m.get("body_mass_override"), "collision_trace_flag": m.get("collision_trace_flag"),
                   "light_map_resolution": m["light_map_resolution"]}
out = {"asset": u3["asset"], "engine": u3["engine"], "gates": G, "all_passed": all(G.values()), "detail": D}
(HERE / "verification_summary.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
for k, v in G.items():
    print(("PASS " if v else "FAIL ") + k)
print("ALL", out["all_passed"])
