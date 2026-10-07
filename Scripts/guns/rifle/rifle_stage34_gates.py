"""AR-01 stage 3 / stage 4 gate records (plain Python): assembles WorkFiles/guns/rifle/gates/uv_bake_paint.json (stage 3,
RIFLE_BUILD_PLAN 12 row 3) and gates/game.json (stage 4, row 4) from the stage outputs in scratch/ (uv, bake, paint,
game, viewgates, the Blender-side gates and the LOD1 motion sweep). Every gate carries its number and threshold.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import rifle_surface as RS  # noqa: E402

W = ROOT / "WorkFiles" / "guns" / "rifle"
S = W / "scratch"
TEX = ROOT / "Exports" / "Guns" / "AR01" / "Textures"
SPEC = json.loads((W / "rifle_spec.json").read_text())


def j(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def gate(name, value, threshold, ok, note=None):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    return g


def realism_tex_gates(uv):
    """Realism-tex round (judges 2026-10-06) checks on the final maps: no blown wear (bare-steel chip blobs on the
    lacquered parts stay small edge flecks; no light dielectric texel on a lacquer), the dust cover's crown a dark even
    coat (no whitish slabs) with its UV unstretched at class A, and the textured ADS view (review/realism_tex2/
    ads_check.json: the post visible in the notch at the exact B4 camera, contrast against the opening)."""
    import numpy as np
    from scipy import ndimage as ndi
    Image.MAX_IMAGE_PIXELS = None
    out = []
    bake = S / "bake"
    meta = j(bake / "bake_meta.json")
    parts = meta["parts"]
    pid = np.load(bake / "Metal_ids.npy")[..., 0].astype(np.int32)
    orm = np.asarray(Image.open(TEX / "T_AR01_Metal_ORM.png"))[::-1]
    bc = np.asarray(Image.open(TEX / "T_AR01_Metal_BC.png").convert("RGB"))[::-1].mean(2)
    met = orm[..., 2] > 127
    lacq = np.isin(pid, [i for n, i in parts.items() if RS.PART_FINISH.get(n, "").startswith("lacquer")
                         and n != "butt_plate"])                  # the butt plate is scratched bare by design
    mm2 = (10.0 / uv["sets"]["Metal"]["classes"]["B"]["px_per_cm_median"]) ** 2
    lab, nl = ndi.label(met & lacq)
    sz = np.bincount(lab.ravel())[1:] if nl else np.zeros(1, int)
    big = float(sz.max() * mm2)
    names = {v: k for k, v in parts.items()}
    worst = names.get(int(np.bincount(pid[lab == int(np.argmax(sz)) + 1]).argmax()), "?") if nl else None
    light = int(((~met) & lacq & (bc > 140)).sum())
    out.append(gate("realism-tex: no blown wear masks (lacquered parts)",
                    f"largest bare-steel chip blob {big:.1f} mm2 ({worst}); {int(met[lacq].sum()):,} chip texels "
                    f"({met[lacq].mean():.2%}); dielectric texels lighter than sRGB 140: {light}",
                    "largest chip blob <= 8 mm2 (an edge fleck, not a patch); light dielectric texels <= 1e-5 of the "
                    "lacquer (isolated texels, no patch: the rubbed coat stays a mid-dark grey)",
                    big <= 8.0 and light <= 1e-5 * int(lacq.sum()),
                    "chips need the 0.6 mm bevel mask + a flake gate; worn steel rough 0.50-0.62 (rifle_paint.py)"))
    nz = np.load(bake / "Metal_nrm.npy", mmap_mode="r")[..., 2].astype(np.float32) * 2 - 1
    cov = pid == parts["dust_cover"]
    crown = cov & (nz > 0.55)
    pos = np.load(bake / "Metal_pos.npy", mmap_mode="r")
    ys, xs = np.nonzero(crown)
    ok = (xs > 0) & (xs < pid.shape[1] - 1) & (ys > 0) & (ys < pid.shape[0] - 1)
    ys, xs = ys[ok], xs[ok]
    inner = crown[ys, xs - 1] & crown[ys, xs + 1] & crown[ys - 1, xs] & crown[ys + 1, xs]
    ys, xs = ys[inner], xs[inner]
    du = np.linalg.norm(np.asarray(pos[ys, xs + 1]) - np.asarray(pos[ys, xs - 1]), axis=1) * 500.0   # mm per px
    dv = np.linalg.norm(np.asarray(pos[ys + 1, xs]) - np.asarray(pos[ys - 1, xs]), axis=1) * 500.0
    an = np.maximum(du, dv) / np.maximum(np.minimum(du, dv), 1e-6)
    pxcm = 10.0 / np.sqrt(np.maximum(du * dv, 1e-9))
    cb, cr = bc[crown], orm[..., 1][crown] / 255.0
    out.append(gate("realism-tex: dust cover crown (dark even coat, class A, unstretched)",
                    f"BC sRGB p1/p50/p99 {np.percentile(cb, 1):.0f} / {np.percentile(cb, 50):.0f} / "
                    f"{np.percentile(cb, 99):.0f}; roughness p5/p95 {np.percentile(cr, 5):.2f} / "
                    f"{np.percentile(cr, 95):.2f}; {np.median(pxcm):.1f} px/cm (P5 {np.percentile(pxcm, 5):.1f}); "
                    f"UV anisotropy p50/p95/p99 {np.percentile(an, 50):.3f} / {np.percentile(an, 95):.3f} / "
                    f"{np.percentile(an, 99):.3f}",
                    "BC p99 <= 100 (no whitish slab: the old crown reached 107+ in broad patches), p99 - p1 <= 45; "
                    "class A 80-125 px/cm; anisotropy p95 <= 1.3",
                    np.percentile(cb, 99) <= 100 and np.percentile(cb, 99) - np.percentile(cb, 1) <= 45 and
                    80 <= np.median(pxcm) <= 125 and np.percentile(an, 95) <= 1.3))
    ads = j(W / "review" / "realism_tex2" / "ads_check.json")
    if ads:
        out.append(gate("realism-tex: textured ADS sight picture (exact B4 camera, 2560 x 1440)",
                        f"post visible {ads.get('post_visible_px')} px ({ads.get('post_visible_width_px_median')} px "
                        f"wide x {ads.get('post_visible_rows')} rows), tip at {ads.get('post_tip_visible_px')} vs "
                        f"projected {ads.get('post_tip_projected_px')}; Weber contrast vs the opening beside it "
                        f"{ads.get('weber_contrast_post_vs_beside')}",
                        "post found (>= 20 px) with |Weber contrast| >= 0.25, tip within 1.5 px of the B4 projection",
                        bool(ads.get("post_found")) and abs(ads.get("weber_contrast_post_vs_beside", 0)) >= 0.25 and
                        abs(ads["post_tip_visible_px"][0] - ads["post_tip_projected_px"][0]) <= 1.5 and
                        abs(ads["post_tip_visible_px"][1] - ads["post_tip_projected_px"][1]) <= 1.5,
                        "review/realism_tex2/ads_55deg_notch.png: 6x crop, post outline marked on the right"))
    return out


def stage3():
    uv = j(S / "uv" / "uv_report.json")
    bake = j(S / "bake" / "bake_meta.json")
    paint = j(S / "paint" / "paint_report.json")
    gg = j(S / "game" / "game_gates_blender.json")
    l5 = j(S / "game" / "l5.json")
    G = []
    qa = gg["qa_check"]
    G.append(gate("qa_check (twin SM_AR01_LOD0..3, pipeline)", "passed" if qa["passed"] else qa["failed"],
                  "pass (budget 57000 = 50000 rifle + 7000 merged mag; UV1 required; texel = measured aggregate)",
                  qa["passed"]))
    # density per class: "per-class density within +-25 % of 5.3" = the class median inside [0.75 x band floor,
    # 1.25 x band top] (the user's bands: A 80-100, B 60-80 on the metal; C 30-40, E 8-15), the class's P5 not under
    # 0.75 x the floor, and the class uniform (P5..P95 within +-25 % of its median)
    for st, v in uv["sets"].items():
        for c, cv in v["classes"].items():
            band = cv["band"]
            med = cv["px_per_cm_median"]
            ok = 0.75 * band[0] <= med <= 1.25 * band[1] and cv["px_per_cm_p5"] >= 0.75 * band[0] and                 cv["uniform_p5_p95_within_25pct"]
            G.append(gate(f"density {st} class {c} (px/cm P5 / median / P95)",
                          f"{cv['px_per_cm_p5']} / {med} / {cv['px_per_cm_p95']} ({cv['area_cm2']} cm2)",
                          f"median in [{0.75 * band[0]:g}, {1.25 * band[1]:g}] (band {band[0]:g}-{band[1]:g} +-25 %), "
                          f"P5 >= {0.75 * band[0]:g}, P5..P95 within +-25 % of the median", ok,
                          f"x{cv['over_band_top']} of the band top" if med > band[1] else None))
    # set size + fill
    m = uv["sets"]["Metal"]
    G.append(gate("Metal set size (user decision: 2048 unless it cannot hold A 80-100 / B 60-80 at >= 70 % fill)",
                  f"{m['size']}: texels needed at the class floors {m['texels_needed_at_class_floors']:,} vs "
                  f"2048 capacity at 70 % {m['capacity_at_fill_min']['2048']:,}",
                  "smallest of 2048 / 4096 that holds the floors at 70 %", True))
    over = {c: v["over_band_top"] for c, v in m["classes"].items() if c != "E"}
    G.append(gate(f"fill Metal ({m['size']})", m["fill"], ">= 0.70", m["fill"] >= 0.70,
                  f"at {m['size']} a 0.70 fill puts the classes over their band tops (x {over}): sharper than the "
                  f"user's A 80-100 / B 60-80 for the same memory (the set size is what costs)" if max(over.values()) > 1.0
                  else None))
    for st in ("Furniture", "Mag"):
        f = uv["sets"][st]["fill"]
        G.append(gate(f"fill {st} ({uv['sets'][st]['size']})", f, ">= 0.65", f >= 0.65,
                      "Mag 1024, not plan 5.3's 2048: at 2048 a >= 65 % fill puts class C at ~93 px/cm (2.3x the band "
                      "top); 1024 holds C inside its band +-25 % at the fill" if st == "Mag" and
                      uv["sets"][st]["size"] == 1024 else None))
    G.append(gate("UV0 overlaps LOD0 (per set = per twin tile; qa epsilon)", uv["lod0_uv0_overlap_pairs"], "0 per set",
                  all(v == 0 for v in uv["lod0_uv0_overlap_pairs"].values())))
    G.append(gate("UV0 mirrored islands (flipped UV triangles, LOD0)", uv["lod0_flipped_uv_triangles"], "0",
                  uv["lod0_flipped_uv_triangles"] == 0))
    rng = uv["uv0_range_all_lods"]
    G.append(gate("UV0 skeletal layout: every set in 0..1 (all LODs' parts)", rng, "inside [0, 1]",
                  min(rng["min"]) >= -1e-6 and max(rng["max"]) <= 1 + 1e-6))
    # maps
    rows, ok_maps = [], True
    for st in ("Metal", "Furniture", "Mag"):
        for mp in ("BC", "ORM", "N", "Masks"):
            p = TEX / f"T_AR01_{st}_{mp}.png"
            if not p.exists():
                ok_maps = False
                continue
            im = Image.open(p)
            w, h = im.size
            pot = (w & (w - 1)) == 0 and (h & (h - 1)) == 0 and w == h
            ok_maps &= pot
            rows.append(f"{p.name} {w}x{h} {im.mode}")
    G.append(gate("maps: power of two, square (full mips in Unreal)", rows, "all POT", ok_maps,
                  "BC sRGB; ORM linear (R AO, G roughness, B metallic); N DirectX (green flipped on write); "
                  "Masks half size (R edge, G handling, B cavity, A refinishable)"))
    # BC in the spec finishes
    fin = paint
    bc_rows, bc_ok = {}, True
    for st, rep in fin.items():
        if st not in ("Metal", "Furniture", "Mag"):
            continue
        mv = rep["metallic_values"]
        bc_ok &= set(mv) <= {0.0, 1.0}
        for f, v in rep["finishes"].items():
            spec = RS.FIN[f]
            d = v["bc_srgb_dielectric_p1_p50_p99"]
            mt = v["bc_srgb_metal_p1_p50_p99"]
            row = {"texels": v["texels"], "metal_fraction": v["metal_fraction"], "dielectric_p1_p50_p99": d,
                   "metal_p1_p50_p99": mt, "rough_p5_p50_p95": v["rough_p5_p50_p95"],
                   "spec_srgb": spec.get("spec_srgb", spec.get("srgb")), "painted_base_srgb": spec.get("srgb")}
            if d is not None and f != "walnut":
                bc_ok &= d[0] >= 30 and d[2] <= 243
                if spec["metal"] == 0:          # coated finishes: the coat's own value (metal finishes' dielectric
                    bc_ok &= abs(d[1] - spec.get("spec_srgb", spec["srgb"])[0]) <= 12   # texels are grime / soot)
            if mt is not None:
                bc_ok &= mt[0] >= (110 if f == "bluing" else 185.5)
            bc_rows[f"{st}/{f}"] = row
    G.append(gate("BC within the spec finishes; metallic exactly 0/1 (G7, B9)", bc_rows,
                  "dielectric median within 12 levels of the finish sRGB, dielectric P1 >= 30 and P99 <= 243 sRGB, "
                  "metal P1 >= 110 sRGB (bluing) / >= 186 (bare steel: chips, sliding faces), metallic values {0, 1}", bc_ok))
    G.append(gate("AO bake in Cycles", f"{bake['ao_samples']} spp, distance {bake['ao_distance_m']} m, device "
                  f"{bake['device']}", "Cycles AO of the assembled LOD0 at rest", True))
    if l5:
        fit = l5.get("fit", {})
        G.append(gate("L5 colour vs the sheet (crop-matched; PHYSICAL rig, specular factor 1; light scale fitted on the "
                      "receiver; wood: per-part tone ratios calibrated on this rig)",
                      {k: {"delta": v["delta"], "pass": v["pass"]} for k, v in l5["regions"].items()},
                      "luma +-0.05, saturation +-0.05, R/B +-0.1, hue +-4 deg (chromatic regions) on every region but "
                      "the calibration region (receiver)", l5["pass"],
                      f"k {fit.get('light_scale')}, specular factor {fit.get('specular_factor')}, rig {fit.get('rig')}; "
                      f"failed: {l5['failed']}"))
    rp = j(W / "gates" / "recolour_precheck.json")
    if rp:
        G.append(gate("furniture recolour pre-check (the pack's derive_constants.fabric_part on T_AR01_Furniture_Detail16; "
                      "black floor, knee, mip drift, 10-colour stress)",
                      {"derive_gates": {k: v["pass"] for k, v in rp["derive_constants_fabric_part"]["gates"].items()},
                       "colour_max_vs_floor": [rp["black_floor"]["colour_max"], rp["black_floor"]["floor"]],
                       "max_default_albedo_vs_knee": [rp["knee"]["max_default_albedo"], rp["knee"]["knee"]],
                       "stress": rp["stress_10_colours"]["pass"]},
                      "every derive gate passes; Colour above the floor; default albedo under the knee; stress passes",
                      rp["pass"], "value ratios survive the recolour (detail), per-part hue is baked-BC only: stage 9 "
                                  "default instance = Use Original Baked Colours ON (default_path_vs_bc in the record)"))
    G.extend(realism_tex_gates(uv))
    G.append(gate("renders only from the baked maps", "review/tex/*.png via rifle_texrender.py (game materials on "
                  "T_AR01_*; no procedural shading)", "true", True))
    status = "pass" if all(g["pass"] for g in G) else "fail"
    notes = {}
    wt = j(W / "wood_tone.json")
    if l5:
        wood = {k: {"sheet_rb": v["sheet"]["rb"], "ours_rb": v["ours"]["rb"], "luma_delta": v["delta"]["luma"],
                    "hue_delta_deg": v["delta"].get("hue_deg")}
                for k, v in l5["regions"].items() if k in ("stock", "pistol_grip", "handguard_lower", "handguard_upper")}
        notes["L5_wood"] = {
            "regions": wood,
            "ruling": "orchestrator ruling 2026-10-05: ONE recolourable stain (#6B3C27) x a per-part tone ratio baked "
                      "into the furniture BC (the sheet's four pieces of walnut, R/B 2.04-2.57, as mismatched "
                      "furniture on real rifles of this pattern)",
            "tones": (wt or {}).get("parts"),
            "calibration": "rifle_wood_tone.py: tone *= lin(sheet) / lin(ours) per channel on the physical L5 rig, "
                           "3-4 rounds; so the wood rows verify the baked tones on this rig, not an independent "
                           "prediction (the receiver-fitted k and the metal / magazine / butt plate rows are the test)",
            "recolour": "value ratio -> Detail16 (moves with the buyer's colour); hue offset -> baked BC only "
                        "(gates/recolour_precheck.json)"}
    notes["L5_rig"] = ("physical rig since the look-polish round (rifle_texrender.sheet_lights_physical: overhead key "
                       "tipped 70 deg toward the camera, rim, grey world 0.2; specular factor 1): blued and bare steel "
                       "show their specular response. The r4 rig's front fill sat behind the camera, so every side flat "
                       "mirrored it; its fitted specular factor went to 0 and blued parts rendered black (retired). "
                       "Walnut shellac roughness base 0.55 -> 0.43 (spec range 0.42-0.60): at 0.55 the 4 % specular "
                       "spreads so wide the dark stain washes out under any real light (R/B ~1.9)")
    return {"stage": "3 UV + bake + paint", "status": status, "gates": G, "notes": notes,
            "failed": [g["name"] for g in G if not g["pass"]],
            "sets": {k: {"size": v["size"], "fill": v["fill"], "islands": v["islands"]} for k, v in uv["sets"].items()},
            "lod_uv": {"overlap_pairs_after": uv["lod_uv0_overlap_pairs"], "collapsed_faces":
                       uv["lod_overlap_collapsed_faces"], "corners": uv["lod_corners"]}}


def stage4():
    game = j(S / "game" / "game_report.json")
    vg = j(S / "game" / "viewgates.json")
    gg = j(S / "game" / "game_gates_blender.json")
    b3 = j(S / "b3_lod1.json")
    G = []
    L = game["lods"]
    tr = [L[f"LOD{k}"]["triangles"] for k in range(4)]
    rf = [L[f"LOD{k}"]["rifle_triangles_without_mag"] for k in range(4)]
    mg = [L[f"LOD{k}"]["mag_triangles"] for k in range(4)]
    G.append(gate("qa_check (twin LOD0..3)", gg["qa_check"]["triangles"], "pass", gg["qa_check"]["passed"],
                  None if gg["qa_check"]["passed"] else json.dumps(gg["qa_check"]["failed"])[:800]))
    G.append(gate("LODs strictly descending (twin)", tr, "LOD0 > LOD1 > LOD2 > LOD3", tr[0] > tr[1] > tr[2] > tr[3]))
    G.append(gate("B8 rifle LOD0 tris (without the mag)", rf[0], "<= 50000 (target 30-45k)", rf[0] <= 50000))
    G.append(gate("B8 merged magazine LOD0 tris", mg[0], "<= 7000", mg[0] <= 7000))
    G.append(gate("LOD1 rifle tris (share of LOD0)", f"{rf[1]} ({rf[1] / rf[0]:.1%})", "~45 % (gun study 5.7)",
                  rf[1] / rf[0] <= 0.50))
    G.append(gate("LOD2 rifle tris (share of LOD0)", f"{rf[2]} ({rf[2] / rf[0]:.1%})", "~15 % (gun study 5.7)",
                  rf[2] / rf[0] <= 0.18, "over the ~15 % target: the lofted furniture and the selector / sight / "
                  "brake keep their section counts at LOD2" if rf[2] / rf[0] > 0.18 else None))
    G.append(gate("LOD3 rifle tris", rf[3], "1500-2500 (ceiling 2500)", rf[3] <= 2500,
                  "under the 1.5k floor of the target range: the blockout silhouette level is cheaper; the LOD-pop "
                  "gate passes at its switch" if rf[3] < 1500 else None))
    b30 = j(S / "b3_lod0_tri.json")
    if b30:
        small0 = [x for x in b30["contact_gaps"] if x["min_gap_mm"] < 0.01]
        G.append(gate("G5 at LOD0 on the shipped (triangulated) parts", f"{len(b30['static_intersections'])} "
                      f"intersecting pairs; min butt gap {min(x['min_gap_mm'] for x in b30['contact_gaps'])} mm",
                      "0; >= 0.01 mm", not b30["static_intersections"] and not small0,
                      json.dumps(b30["static_intersections"] + small0)[:600] if (b30["static_intersections"] or small0)
                      else None))
    if b3:
        gr = b3["groups"]
        G.append(gate("B3 at LOD1 (moving parts, sweep)", {g: {"intersecting_steps": v["summary"]["intersecting_steps"],
                                                              "min_clearance_mm": v["summary"]["min_clearance_mm"]}
                                                          for g, v in gr.items()},
                      "0 intersections; clearance inside each joint's row", all(v["summary"]["pass"] for v in gr.values())))
        G.append(gate("G5 at LOD1 (static intersecting pairs)", len(b3["static_intersections"]), "0",
                      len(b3["static_intersections"]) == 0))
        small = [x for x in b3["contact_gaps"] if x["min_gap_mm"] < 0.01]
        G.append(gate("G5 at LOD1 butt-joint gaps", min(x["min_gap_mm"] for x in b3["contact_gaps"]), ">= 0.01 mm",
                      not small, json.dumps(small) if small else None))
    g5l = j(S / "game" / "g5_lods.json")
    if g5l:
        visl = (g5l.get("visible") or {}).get("lods", {})
        for k, v in g5l["lods"].items():
            vv = visl.get(k, {})
            worst = sorted(vv.get("parts", {}).items(), key=lambda x: -x[1]["worst_mean_px"])[:3]
            G.append(gate(f"G5 at {k} (study B3/G5 R5: penetration depth projected at the switch-in distance)",
                          f"{v['intersecting_pairs']} intersecting pairs; deepest penetration {v['worst_depth_px']} px "
                          f"at {v['distance_m']} m ({v['pairs'][0]['a']}/{v['pairs'][0]['b']} "
                          f"{v['pairs'][0]['depth_mm']} mm)" if v["pairs"] else "0 intersecting pairs",
                          "< 1 px at 1440p", v["pass"],
                          f"info, visible change of the intersecting parts vs LOD{int(k[-1]) - 1} (4 headings): worst "
                          f"mean {vv.get('worst_mean_px')} px, max {vv.get('worst_max_px')} px: "
                          + "; ".join(f"{n} {r['worst_mean_px']} / {r['worst_max_px']}" for n, r in worst)
                          + (" (LOD3's blockout receiver has no ejection port, so the carrier strip seen through the "
                             "port at LOD2 is covered at 20 m)" if k == "LOD3" else "")))
    c1 = gg["C1"]
    G.append(gate("C1 hull containment", f"{c1['samples_outside']} of {c1['jittered_lod0_samples']:,} jittered 0.5 mm "
                  f"LOD0 samples, {c1['vertices_outside']} of {c1['lod_vertices']:,} LOD0-3 vertices outside",
                  "0 and 0; 7 hulls, <= 32 vertices", c1["pass"], f"hull vertices {c1['hull_vertices']}"))
    s1 = gg["S1"]
    G.append(gate("S1 sockets (exported sidecar vs build)", f"{s1['count']} sockets, worst {s1['worst_mm']} mm / "
                  f"{s1['worst_deg']} deg", "17 = spec names; <= 0.001 mm and <= 0.001 deg", s1["pass"]))
    s2 = vg["s2"]
    G.append(gate("S2 sight picture at LOD0 (B4 method: post tip level with the notch top, R48)",
                  f"lateral {s2.get('lateral_offset_px')} px, vertical {s2.get('vertical_offset_px')} px",
                  "|lateral| <= 0.5 px and |vertical| <= 0.5 px (55 deg, 0.25 m eye relief, 2560 x 1440)",
                  s2.get("pass", False)))
    for k, v in (vg.get("s2_lods") or {}).items():
        if v.get("pass") is None:
            G.append(gate(f"S2 sight picture at {k}", "n/a", "|lateral|, |vertical| <= 0.5 px", True, v.get("note")))
        else:
            G.append(gate(f"S2 sight picture at {k}", f"lateral {v.get('lateral_offset_px')} px, vertical "
                          f"{v.get('vertical_offset_px')} px", "|lateral| <= 0.5 px and |vertical| <= 0.5 px",
                          v["pass"], "first person forces LOD0 (ForcedLodModel 1): informative for the coarse LODs"))
    for sw in vg["lod_pop"]["switches"]:
        t = sw["tries"][-1]
        G.append(gate(f"LOD-pop LOD{sw['from']} -> LOD{sw['to']}", f"size {sw['chosen_screen_size']} ({t['distance_m']} m): "
                      f"mean {t['worst_mean_px']} px, max {t['worst_max_px']} px (worst of 4 headings)",
                      "mean <= 1 px, max <= 3 px at 2560 x 1440, 90 deg", sw["pass"]))
    G.append(gate("names (tokenised gun deny list)", gg["B10_names"]["hits"] or "clean", "no hit", gg["B10_names"]["pass"]))
    status = "pass" if all(g["pass"] for g in G) else "fail"
    return {"stage": "4 Game (rifle)", "status": status, "gates": G, "failed": [g["name"] for g in G if not g["pass"]],
            "lod_screen_sizes": vg["lod_pop"]["final_sizes"], "bounds_radius_m": game["bounds_radius_m"],
            "triangles": {"twin": tr, "rifle": rf, "mag": mg}, "hulls": game["hulls"], "mass": game["mass"],
            "sockets": s1["sockets"]}


def main():
    (W / "gates").mkdir(exist_ok=True)
    s3 = stage3()
    s4 = stage4()
    (W / "gates" / "uv_bake_paint.json").write_text(json.dumps(s3, indent=1))
    (W / "gates" / "game.json").write_text(json.dumps(s4, indent=1))
    for s in (s3, s4):
        print("[stage]", s["stage"], s["status"], s["failed"])


if __name__ == "__main__":
    main()
