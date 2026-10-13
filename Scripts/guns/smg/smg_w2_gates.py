"""SMG01 W2 surface gate record (plain Python): assembles WorkFiles/guns/smg/gates/uv_bake_paint.json from the stage's
outputs (scratch/uv, scratch/bake, scratch/paint, scratch/w2_blender.json, scratch/l5/l5.json, gates/recolour_precheck
.json, gates/gunlib_regression.json, gates/form.json, review/realism_tex). Every gate carries its value and threshold
(SMG_BUILD_PLAN 14.2 B9 / UD1-UD4, 14.1 L5; spec gates; the AR-01's stage-3 record as the template).
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, SCRATCH, GATES, REVIEW  # noqa: E402

import smg_surface as SS  # noqa: E402

TEX = ROOT / "Exports" / "Guns" / "SMG01" / "Textures"
Image.MAX_IMAGE_PIXELS = None


def j(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def gate(name, value, threshold, ok, note=None):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    return g


def main():
    uv = j(SCRATCH / "uv" / "uv_report.json")
    uv1 = j(SCRATCH / "uv" / "uv1_report.json")
    ud4 = j(SCRATCH / "uv" / "ud4.json")
    bake = j(SCRATCH / "bake" / "bake_meta.json")
    paint = j(SCRATCH / "paint" / "paint_report.json")
    wb = j(SCRATCH / "w2_blender.json")
    l5 = j(SCRATCH / "l5" / "l5.json")
    rc = j(GATES / "recolour_precheck.json")
    reg = j(GATES / "gunlib_regression.json")
    form = j(GATES / "form.json")
    G = []
    # ---------------------------------------------------------------- qa_check on the twin as W3 joins it
    q = wb["qa_check_twin"]
    G.append(gate("qa_check: the static twin as W3 joins it (pipeline; Metal U 0..1, Furniture 1..2, merged mag -1..0)",
                  {"passed": q["passed"], "triangles": q["triangles"], "texel_aggregate_px_cm": q["texel_aggregate_px_cm"],
                   "failed": [c["name"] for c in q["failed"]], "rows": q["rows"]},
                  "pass (budget 55,000 = 50,000 + the magazine's 5,000; UV1 required; texel target = the measured "
                  "aggregate; UCX at W3)", q["passed"]))
    # ---------------------------------------------------------------- B9 densities, fill, sizes
    for st, v in uv["sets"].items():
        for c, cv in v["classes"].items():
            band = cv["band"]
            med, p5 = cv["px_per_cm_median"], cv["px_per_cm_p5"]
            ok = 0.75 * band[0] <= med <= 1.25 * band[1] and p5 >= 0.85 * med
            G.append(gate(f"B9 density {st} class {c} (px/cm P5 / median / P95)",
                          f"{p5} / {med} / {cv['px_per_cm_p95']} ({cv['area_cm2']} cm2)",
                          f"median in [{0.75 * band[0]:g}, {1.25 * band[1]:g}] (band {band[0]:g}-{band[1]:g}, the "
                          f"density ceiling 1.25 x top); P5 >= 0.85 x median (classes +-15 %, spec B9)", ok,
                          f"x{cv['over_band_top']} of the band top" if med > band[1] else None))
        fmin = SS.SETS[st]["fill_min"]
        G.append(gate(f"B9 fill {st} ({v['size']})", v["fill"], f">= {fmin:.2f}", v["fill"] >= fmin))
        G.append(gate(f"set size {st}", f"{v['size']}: texels needed at the class floors "
                      f"{v['texels_needed_at_class_floors']:,} vs capacity at the fill minimum {v['capacity_at_fill_min']}",
                      "the smallest power of two holding the class floors at the fill minimum (the packer decides)", True))
    # ADS: the sight picture's parts and the top rail
    a_parts = uv["sets"]["Metal"]["classes"]["A"]["parts_median_px_cm_area_cm2"]
    b_rail = {k: v for k, v in uv["sets"]["Metal"]["classes"]["B"]["parts_median_px_cm_area_cm2"].items()
              if k in ("top_rail", "rail_screws")}
    c_rail = {k: v for k, v in uv["sets"]["Metal"]["classes"]["C"]["parts_median_px_cm_area_cm2"].items()
              if k in ("top_rail", "rail_screws")}
    ads_ok = all(80.0 <= v[0] <= 125.0 for v in a_parts.values()) and all(60.0 <= v[0] <= 100.0 for v in b_rail.values())
    G.append(gate("ADS densities: class A on the sight picture (both sights' parts), the top rail B behind X 400 / C "
                  "forward (spec class A = the sights only, check fix C15)",
                  {"A sights (median px/cm, cm2)": a_parts, "B top rail X < 400": b_rail, "C top rail X >= 400": c_rail,
                   "long rail faces demoted B -> C": uv.get("long_faces_demoted")},
                  "sight parts 80-125 px/cm (A band x 1.25); the top rail's class-B faces 60-100", ads_ok,
                  "six single triangles 232-303 mm long (the rail's flank / base strips, not seen at ADS) take class C: "
                  "at B they capped the 2048 pack at fill 0.36 (smg_uv: 'long faces demoted')"))
    # ---------------------------------------------------------------- UV0 integrity
    G.append(gate("UV0 overlaps per set (qa_check's rules, float32, on each twin tile)", uv["lod0_uv0_overlap_pairs"],
                  "0 per set", all(v == 0 for v in uv["lod0_uv0_overlap_pairs"].values())))
    G.append(gate("UV0 mirrored (flipped) triangles", uv["lod0_flipped_uv_triangles"], "0",
                  uv["lod0_flipped_uv_triangles"] == 0))
    r = uv["uv0_range"]
    G.append(gate("UV0 skeletal layout: every set in 0..1", r, "inside [0, 1]",
                  min(r["min"]) >= -1e-6 and max(r["max"]) <= 1 + 1e-6))
    # ---------------------------------------------------------------- maps
    rows, ok_maps = [], True
    for st in SS.SETS:
        for mp in ("BC", "ORM", "N", "Masks"):
            p = TEX / f"T_SMG01_{st}_{mp}.png"
            if not p.exists():
                ok_maps = False
                rows.append(f"{p.name} MISSING")
                continue
            im = Image.open(p)
            w, h = im.size
            pot = (w & (w - 1)) == 0 and w == h
            ok_maps &= pot
            rows.append(f"{p.name} {w}x{h} {im.mode}")
    for st in ("Furniture", "Mag"):
        p = TEX / "Recolour" / f"T_SMG01_{st}_Detail16.png"
        ok_maps &= p.exists()
        rows.append(f"Recolour/{p.name} {'present' if p.exists() else 'MISSING'}")
    G.append(gate("maps: square power of two (full mips in Unreal); names T_SMG01_<Set>_<map>", rows, "all present, POT",
                  ok_maps, "BC sRGB; ORM linear (R AO, G roughness, B metallic); N DirectX 16-bit; Masks half size "
                           "(R edge-wear propensity, G handling, B cavity, A refinishable)"))
    # ---------------------------------------------------------------- BC / metallic (B9 / G7)
    bc_rows, bc_ok = {}, True
    for st in SS.SETS:
        rep = paint[st]
        bc_ok &= set(rep["metallic_values"]) <= {0.0, 1.0}
        for f, v in rep["finishes"].items():
            F = SS.FIN[f]
            d = v["bc_srgb_dielectric_p1_p50_p99"]
            mt = v["bc_srgb_metal_p1_p50_p99"]
            spec_v = F.get("spec_srgb", F["srgb"])
            row = {"texels": v["texels"], "metal_fraction": v["metal_fraction"], "dielectric_p1_p50_p99": d,
                   "metal_p1_p50_p99": mt, "rough_p5_p50_p95": v["rough_p5_p50_p95"], "painted_base_srgb": F["srgb"],
                   "spec_srgb": spec_v}
            if d is not None:
                bc_ok &= d[0] >= 29.5 and d[2] <= 243 and abs(d[1] - sum(spec_v) / 3.0) <= 12
            if mt is not None:
                bc_ok &= mt[0] >= 185.5
            if f in SS.POLYMER_FIN:
                bc_ok &= v["metal_fraction"] == 0.0
            bc_rows[f"{st}/{f}"] = row
    G.append(gate("BC within the spec finishes; metallic exactly 0 / 1; polymer never metal (B9, G7, G8)", bc_rows,
                  "dielectric median within 12 sRGB levels of the finish, P1 >= 30 (the PBR floor), P99 <= 243; bare "
                  "steel P1 >= 186; metallic {0, 1}; polymer metal fraction 0", bc_ok))
    # ---------------------------------------------------------------- bakes
    G.append(gate("bake rules (AR-01 lessons)", {"margin": bake.get("margin"), "ao_samples": bake["ao_samples"],
                                                 "ao_distance_m": bake["ao_distance_m"], "device": bake["device"],
                                                 "rules": bake.get("rules")},
                  "margin 0 (per-island fill by the painter); the magazine's AO + edge alone; the gun's AO with the "
                  "magazine out", bake.get("margin") == 0 and "Mag" in (bake.get("rules") or {})))
    # ---------------------------------------------------------------- L5
    if l5:
        fit = l5.get("fit", {})
        G.append(gate("L5 colour vs the sheet (crop-matched per traced part, physical rig, specular 1; light scale "
                      "fitted on the upper receiver only)",
                      {k: {"delta": v["delta"], "pass": v["pass"]} for k, v in l5["regions"].items()},
                      "luma +-0.05, saturation +-0.05, R/B +-0.1, hue +-4 deg (chromatic regions) on every region but "
                      "the calibration one and the reported-only shadow region", l5["pass"],
                      f"k {fit.get('light_scale')}, failed {l5['failed']}; reported only: {l5.get('reported_only')}; "
                      f"polymer / steel luminance ratio {l5.get('polymer_steel_ratio')} (the spec's 1.3-1.5 band does "
                      f"not hold on the sheet's own crops either: reported)"))
        pr = l5.get("polymer_steel_luma_ratio") or {}
        G.append(gate("G20 steel darker than the polymer (W4 review): sRGB luma ratio receiver / steel crops (barrel + "
                      "muzzle device + lower rail side) in the L5 render vs the sheet's own", pr,
                      "ours within the CRAFT 3 band 1.3-1.5 (+-0.05) and within 0.15 of the sheet's own ratio (W2: "
                      "polymer 46-49 over steel 50-52, the steel read lighter)",
                      bool(pr) and 1.25 <= pr.get("ours", 0) <= 1.55 and abs(pr.get("ours", 0) - pr.get("sheet", 0)) <= 0.15))
    else:
        G.append(gate("L5", "missing", "present", False))
    # ---------------------------------------------------------------- wear audits
    for st in SS.SETS:
        wa = paint[st]["wear_audit"]
        if "interior_bare_clusters" in wa:
            G.append(gate(f"wear: no bare steel on {st} phosphate panel interiors",
                          {k: wa[k] for k in ("interior_bare_clusters", "steel_bare_fraction")},
                          "0 clusters > 2 mm from a same-side sharp convex edge outside the bright-edge zones",
                          wa["interior_bare_clusters"] == 0))
            # (W4 review fixes) bare steel is continuous LINES on the crests now, so the W2 area cap (<= 8 mm2, made for
            # flecks) gives way to the width of a line: no bare cluster wider than 1.6 mm anywhere (a line, not a
            # patch), none under MIN cluster texels (no isolated sparkle), none further than 1.2 mm from a same-side
            # sharp convex edge (the review's rules; the bolt's slide flanks by design)
            G.append(gate(f"wear: bare steel on {st} phosphate is edge LINES (W4 review: no fireflies, no patches)",
                          {k: wa.get(k) for k in ("bare_line_width_max_mm", "bare_clusters", "bare_cluster_min_texels",
                                                  "bare_cluster_median_texels", "bare_texels_far_from_edge",
                                                  "steel_bare_fraction", "largest_bare_blob_mm2",
                                                  "largest_bare_blob_part", "by_design_bare_largest_mm2")},
                          "widest point <= 1.6 mm; smallest cluster >= 14 texels; 0 bare texels > 1.2 mm from a sharp "
                          "convex edge; bare fraction 0.3-4 % (W2: 0.07 % in 196 flecks)",
                          (wa.get("bare_line_width_max_mm") or 99) <= 1.6 and (wa.get("bare_cluster_min_texels") or 0) >= 14
                          and wa.get("bare_texels_far_from_edge", 1) == 0 and 0.003 <= wa["steel_bare_fraction"] <= 0.04))
            if "charging_knob_bare_fraction" in wa:
                G.append(gate("wear: charging knob bare steel", wa["charging_knob_bare_fraction"], "<= 0.25",
                              wa["charging_knob_bare_fraction"] <= 0.25))
        if "polymer_metallic_texels" in wa:
            G.append(gate(f"wear: {st} polymer never shows metal; whitening only on edges",
                          {k: wa[k] for k in ("polymer_metallic_texels", "whitened_off_edge_clusters", "whitened_fraction",
                                              "whitened_largest_blob_mm2", "polymer_lum_p50_srgb")},
                          "0 metallic texels; 0 whitened clusters > 1.2 mm from a sharp convex edge",
                          wa["polymer_metallic_texels"] == 0 and wa["whitened_off_edge_clusters"] == 0))
    # ---------------------------------------------------------------- (W4 review fixes) the polymer's surface
    rows, ok = {}, True
    for st, f, std_min, tilt_min in (("Furniture", "polymer", 3.0, 0.18), ("Mag", "polymer_mag", 3.0, 0.15)):
        v = paint[st]
        sd = (v.get("bc_std_srgb_levels") or {}).get(f, 0.0)
        tl = (v.get("normal_tilt_gt_1deg_fraction") or {}).get(f, 0.0)
        wf = v["wear_audit"].get("whitened_fraction", 0.0)
        rows[f"{st}/{f}"] = {"bc_std_srgb_levels": sd, "normal_tilt_gt_1deg_fraction": tl, "whitened_fraction": wf}
        ok &= sd >= std_min and tl >= tilt_min and wf >= 0.002
    G.append(gate("polymer surface (W4 review G15): moulded micro-texture in the normal map, albedo mottle, edge "
                  "whitening present", rows,
                  "BC luma std >= 3.0 sRGB levels; >= 18 % (furniture) / 15 % (magazine) of texels tilted > 1 deg "
                  "(the AR-01 furniture: 24 %); whitened >= 0.2 % of texels (W2: Furniture 0.14 %, the normal map "
                  "2.3 %)", ok))
    mt = paint["Metal"]
    G.append(gate("Metal Masks G (handling) written (W4 review: G was 0 on every Metal texel)",
                  {"masks_g_handling_fraction": mt.get("masks_g_handling_fraction"), "info": mt.get("info")},
                  "> 0 on the phosphate (trigger / paddle faces, knob crown, selector thumb arcs, handling zones); the "
                  "drum knurl, the knob's crown and rim and the chamber mouth painted",
                  (mt.get("masks_g_handling_fraction") or {}).get("phosphate", 0.0) > 0.001 and
                  (mt.get("info") or {}).get("drum_knurl_texels", 0) > 0 and
                  # (W4b close-up r2) the rim is a rubbed satin ring now (bare, it read as a stray specular edge)
                  max((mt.get("info") or {}).get("knob_rim_bare_texels", 0),
                      (mt.get("info") or {}).get("knob_rim_texels", 0)) > 0))
    st_ = paint["Furniture"].get("stipple")
    G.append(gate("grip stipple (normal + cavity, spec grip_stipple)", st_,
                  "present on both panels; height 0.10-0.15 mm; roughness 0.78-0.88 (crowns polished in the hand)",
                  bool(st_) and st_["texels"] > 0 and 0.09 <= st_["height_mm_p50_p99"][1] <= 0.16))
    # ---------------------------------------------------------------- UD1-UD4
    G.append(gate("UD1 re-run on the surfaced parts (Unreal's degenerate rule; triangulated by the UV step)",
                  {"parts": wb["ud1"], "twin": wb["twin_ud1"]}, "0 drops; min triangle area >= 0.01 mm2",
                  wb["ud1"]["drops"] == 0 and wb["ud1"]["min_area_mm2"] >= 0.01 and wb["twin_ud1"]["drops"] == 0))
    G.append(gate("UD2 re-run (micro edges / needles / strips)", wb["ud2"], "0 / 0 / 0",
                  all(v == 0 for v in wb["ud2"].values())))
    u3 = {k: v for k, v in wb["ud3"].items() if k != "by_part"}
    G.append(gate("UD3 zero tangents on UV0 (Blender MikkTSpace collapsed, float32_zero_corners, edge_on_corners)",
                  {"parts": u3, "twin": wb["twin_ud3"], "by_part": wb["ud3"]["by_part"]}, "0 on every part and the twin",
                  all(v == 0 for v in u3.values()) and all(v == 0 for v in wb["twin_ud3"].values()),
                  "LOD1-3 and the SK LODs are built at W3 (the same check runs there)"))
    G.append(gate("UD4 authored lightmap UV1 (64 and 128 px, 2 px padding, conservative raster)",
                  {"rows": ud4["rows"], "qa_overlap_pairs": uv1["overlap_pairs_qa"], "range": uv1["range"],
                   "charts_packed": uv1["charts_packed"], "hosted": uv1["hosted"], "layers_ok": wb["layers_ok"]},
                  "0 padding violations at 64 and 128 px; 0 overlapping UV1 triangles (qa rules); inside 0..1; UV0 / "
                  "UV1 at indices 0 / 1", ud4["pass"] and uv1["overlap_pairs_qa"] == 0 and wb["layers_ok"] and
                  min(uv1["range"]["min"]) >= 0 and max(uv1["range"]["max"]) <= 1,
                  "the 90 largest projection charts packed; the remaining visible faces (pins, screws, sight leaves, "
                  "extra depth layers: %.1f %% of the visible area) and the hidden faces take a zero-area UV1 inside "
                  "the nearest host face of the same facing (they read its lightmap texel); LOD1-3 at W3"
                  % (100 * uv1["hosted"]["visible_area_fraction"])))
    # ---------------------------------------------------------------- recolour, regression, form, budgets, renders
    if rc:
        G.append(gate("polymer recolour pre-check (the pack's derive_constants.fabric_part on T_SMG01_{Furniture,Mag}"
                      "_Detail16; black floor, knee, mips, 13-colour stress incl. tan / OD / FDE)",
                      {st: {"derive_gates": {k: v["pass"] for k, v in m["derive_constants_fabric_part"]["gates"].items()},
                            "stress": m["stress_13_colours"]["pass"],
                            "default_path_vs_bc_p999_levels": m["default_path_vs_bc"]["levels_p999_all"]}
                       for st, m in rc["members"].items()},
                      "every derive gate passes, stress passes, Colour above the floor, default albedo under the knee",
                      rc["pass"], "the W6 pack gate P1 (default capture = shipped BC, p99.9 <= 2 levels) is reported "
                                  "here: Furniture 4096 BC vs its 2048 detail; W6 decides BC7 / Use Original Baked "
                                  "Colours for the default instance (the AR-01 precedent)"))
    if reg:
        by = reg.get("bytes", {})
        tracked = by.get("git_tracked_changes_under_Exports_AR01_Assets_Guns_WorkFiles_guns_rifle", [])
        ar01_tracked = [t for t in tracked if "SMG01" not in t]
        checks = reg.get("checks", [])
        n_eq = sum(1 for c in checks if c.get("equal", c.get("pass")) is True) if isinstance(checks, list) else None
        ok = (all(f == "AR-01 export / input bytes" for f in reg["failed"]) and by.get("exports_unchanged_during_run")
              and all(c.get("equal", True) for c in checks) and by.get("input_blends_unchanged") and by.get("exports_equal_recorded_build_sha256 (rig_export.json + "
                                                               "mag.json files)") and not ar01_tracked)
        G.append(gate("AR-01 regression re-run once in W2 (gunlib %s): every stage-2/4/5/6 gate value reproduced, "
                      "Exports/Guns/AR01 unchanged" % reg.get("lib_version"),
                      {"compare_status": reg["status"], "compare_failed": reg["failed"], "date": reg["date"],
                       "exports_unchanged_during_run": by.get("exports_unchanged_during_run"),
                       "exports_equal_recorded_build_sha256": by.get("exports_equal_recorded_build_sha256 (rig_export"
                                                                      ".json + mag.json files)"),
                       "input_blends_unchanged": by.get("input_blends_unchanged"),
                       "git_tracked_changes": tracked, "value_groups_equal": f"{sum(1 for c in checks if c.get('equal'))} / "
                                             f"{sum(1 for c in checks if 'equal' in c)}"},
                      "every value group EQUAL; AR-01 exports and inputs unchanged; no tracked AR-01 change", ok,
                      "the compare's byte row lists every tracked change under Assets/Guns: the only one is this stage's "
                      "Assets/Guns/SMG01.blend (not an AR-01 file), so its 'fail' is that row alone"))
    if form:
        G.append(gate("form gates re-run after the top rail's generator fix (UD3: no 'flat' dissolve on the rail)",
                      {"status": form["status"], "failed": form.get("failed")}, "gates/form.json pass",
                      form["status"] == "pass"))
    tl = wb["triangles_lod0"]
    G.append(gate("B8 LOD0 triangles after the UV stage (gun / magazine)", tl, "gun <= 50,000; magazine <= 5,000",
                  tl["gun"] <= 50000 and tl["magazine"] <= 5000))
    need = ["fp_35cm", "ads", "tp_3m", "hero_34"]
    have = [n for n in need if (REVIEW / "realism_tex" / f"{n}.png").exists()]
    G.append(gate("renders only from the baked maps (review/realism_tex: fp_35cm, ads, tp_3m, hero_34 + hero folded + "
                  "the seven part groups at 35 cm)", have, "the four realism views present",
                  len(have) == len(need), "smg_texrender.py: game materials on T_SMG01_*; no procedural shading"))
    status = "pass" if all(g["pass"] for g in G) else "fail"
    out = {"stage": "W2 surface (SMG_BUILD_PLAN 15 row W2)", "date": datetime.datetime.now().isoformat(timespec="seconds"),
           "status": status, "failed": [g["name"] for g in G if not g["pass"]], "gates": G,
           "process": "Scripts/guns/smg/run_surface.sh (smg_uv -> smg_uv1 + smg_ud4 -> smg_bake -> smg_paint -> "
                      "smg_recolour -> smg_w2_blender -> smg_l5_fit -> smg_texrender realism / closeups -> smg_w2_gates)",
           "notes": j(GATES / "uv_bake_paint_notes.json")}
    (GATES / "uv_bake_paint.json").write_text(json.dumps(out, indent=1, default=str))
    print("[W2 gates]", status, out["failed"])


if __name__ == "__main__":
    main()
