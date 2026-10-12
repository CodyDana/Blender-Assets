"""Assemble the SMG01 stage gate files from the measured results (plain Python):

    py -3 -B Scripts/guns/smg/smg_gates.py --stage blockout|form

blockout -> WorkFiles/guns/smg/gates/blockout.json   (L1, B4 at blockout, the 3/4 solve + magazine thickness)
form     -> WorkFiles/guns/smg/gates/form.json       (L2, L3, L4, B3, B3b, B4/B4b/B4c, B6a, B7, B8, B10, G5, UD1-UD2,
                                                       F1-F7, H1 early, MAGFIT (gates/form_magfit.json), L8 renders)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, GATES, SCRATCH, REVIEW, RENDERS, D as SPECD  # noqa: E402
EARLY = REVIEW / "early_realism"            # the realism review set the form gates cite (--early)


def load(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def g(name, value, threshold, ok, note=""):
    d = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        d["note"] = note
    return d


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def stage_blockout():
    sil = load(SCRATCH / "sil_blockout.json")
    b4 = load(SCRATCH / "b4_blockout.json")
    q = load(REVIEW / "blockout" / "q34_result.json")
    L, R, T = sil["views"]["LEFT"], sil["views"]["RIGHT"], sil["views"]["TOP"]
    ceil = R.get("sheet_ceiling_iou_LEFT_trace_vs_RIGHT")
    gates = [g("L1 LEFT IoU (similarity fit)", L["iou_fit"], ">= 0.95", L["iou_fit"] >= 0.95),
             g("L1 RIGHT IoU (similarity fit)", R["iou_fit"], ">= 0.95 or within 0.005 of the sheet's own LEFT/RIGHT "
               "ceiling", R["iou_fit"] >= 0.95 or (ceil and R["iou_fit"] >= ceil - 0.005),
               "the sheet's own LEFT trace vs its RIGHT panel reads %s: the two panels disagree by that much" % ceil),
             g("L1 TOP IoU (X >= %.1f)" % float(SPECD["gates"]["look"]["L2_TOP_exclusion_X"]), T["iou_fit_valid"],
               ">= 0.92", T["iou_fit_valid"] >= 0.92),
             g("L1 stop rule (change the method below 0.90)", min(L["iou_fit"], R["iou_fit"], T["iou_fit_valid"]),
               ">= 0.90", min(L["iou_fit"], R["iou_fit"], T["iou_fit_valid"]) >= 0.90),
             g("B4 sight picture at blockout (aperture)", {"lateral_mm": b4["lateral_offset_mm"],
                                                           "vertical_mm": b4["vertical_offset_mm"],
                                                           "aperture_mm": b4["aperture"]["diameter_mm_at_aperture"],
                                                           "post_visible_mm": b4["post"]["visible_height_in_aperture_mm_at_aperture"]},
               "post tip at the aperture centre <= 0.2 mm; post visible >= 0.4 x hole", b4["pass"], b4.get("image", ""))]
    if q:
        gates.append(g("3/4 camera solve at blockout (info)", {"iou": q.get("iou"), "landmark_rms_px": q.get("landmark_rms_px")},
                       "reported", True, "magazine thickness sweep: %s" % json.dumps(q.get("magazine_thickness_check", {}))[:300]))
    res = {"stage": "W1b blockout", "date": datetime.now().isoformat(timespec="seconds"),
           "status": "pass" if all(x["pass"] for x in gates) else "fail",
           "failed": [x["name"] for x in gates if not x["pass"]], "gates": gates,
           "details": {"silhouette": sil, "b4": b4, "q34": q},
           "files": {"blend": rel(SCRATCH / "SMG01_blockout.blend"),
                     "overlays": [rel(p) for p in sorted((REVIEW / "blockout").glob("*.png"))]}}
    (GATES / "blockout.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"status": res["status"], "failed": res["failed"]}, indent=1))


def stage_form():
    sil = load(SCRATCH / "sil_form.json")
    q = load(REVIEW / "form" / "q34_result.json")
    b3 = load(SCRATCH / "b3_result.json")
    b3b = load(SCRATCH / "b3_result_run2.json")
    if b3b:                          # a later run of some groups (--only) on the final bytes overrides those groups and
        b3 = dict(b3 or {}, groups=dict((b3 or {}).get("groups", {}), **b3b["groups"]))      # the static checks
        b3["static_intersections"] = b3b["static_intersections"]
        b3["contact_gaps"] = b3b["contact_gaps"]
        b3["runs"] = {"run1": "scratch/b3_result.json (every group)",
                      "run2": "scratch/b3_result_run2.json (%s; static + gaps)" % ", ".join(b3b["groups"])}
    b6 = load(SCRATCH / "b6a_result.json")
    me = load(SCRATCH / "measure_result.json")
    h1 = load(SCRATCH / "h1_result.json")
    fg = load(SCRATCH / "fgates_result.json")
    rep = load(SCRATCH / "form_build_report.json")
    b4 = load(SCRATCH / "b4_result.json")
    b4b = load(SCRATCH / "b4b_result.json")
    mf = load(GATES / "form_magfit.json")
    er = load(EARLY / "shots.json")
    gates = []
    # ---- L2
    L, R, T = sil["views"]["LEFT"], sil["views"]["RIGHT"], sil["views"]["TOP"]
    ceil = R.get("sheet_ceiling_iou_LEFT_trace_vs_RIGHT", 0.948)
    raw_note = lambda e: "raw (no R34 conventions) %s / identity %s" % (e.get("iou_fit_raw"), e.get("iou_identity_raw"))
    gates.append(g("L2 LEFT IoU (authority; R34 side conventions)", L["iou_fit"], ">= 0.96", L["iou_fit"] >= 0.96,
                   raw_note(L)))
    ceil_raw = R.get("sheet_ceiling_iou_LEFT_trace_vs_RIGHT_raw", 0.948)
    ok_conv = R["iou_fit"] >= 0.96 or R["iou_fit"] >= ceil - 0.005
    ok_raw = (R.get("iou_fit_raw") or 0) >= 0.96 or (R.get("iou_fit_raw") or 0) >= ceil_raw - 0.005
    gates.append(g("L2 RIGHT IoU (authority, port side; R34 side conventions)", R["iou_fit"], ">= 0.96 or within 0.005 "
                   "of the sheet's own LEFT/RIGHT ceiling %.4f (same conventions)" % ceil, ok_conv,
                   "raw: %s vs the raw ceiling %.3f - 0.005 -> %s; residual split (details.silhouette.views.RIGHT."
                   "residual_split): %s" % (R.get("iou_fit_raw"), ceil_raw, "pass" if ok_raw else "fail",
                                            R.get("residual_split"))))
    gates.append(g("L2 TOP IoU (X >= %.1f)" % float(SPECD["gates"]["look"]["L2_TOP_exclusion_X"]), T["iou_fit_valid"],
                   ">= 0.93", T["iou_fit_valid"] >= 0.93))
    parts = L.get("parts", {})
    bad = {k: v for k, v in parts.items() if not (v["pass"] or v.get("pass_waived"))}
    gates.append(g("L2 per part, LEFT (IoU >= 0.95 for masks >= 400 px and mean width >= 7 px; thin parts contour "
                   "P95 <= 1 px, max <= 2; fold-resized sights >= ceiling - 0.05; R33 conventions; the paddle waived, "
                   "declared C1)",
                   "%d / %d parts pass" % (len(parts) - len(bad), len(parts)), "all", not bad,
                   "failing: " + ", ".join("%s (IoU %.3f, P95 %s)" % (k, v["iou"], v["contour_p95_px"])
                                           for k, v in bad.items())))
    if q:
        ex = q.get("exception") or {}
        exn = ("exception (R38) %s: floor IoU %s %s, regions > 3 px %s (contradictions %s, R26 magazine %s, unexplained %s); "
               "solve candidates %s; global search: review/form/q34_global_search.json; evidence images: "
               "review/form/q34_exception/" % ("PASS" if ex.get("pass") else "FAIL", ex.get("floor_iou"),
                                        "met" if ex.get("floor_pass") else "NOT met", ex.get("regions_over_3px"),
                                        ex.get("contradictions"), ex.get("r26_magazine"), len(ex.get("not_explained") or []),
                                        (q.get("solve") or {}).get("candidates_iou")))
        # R39 (orchestrator ruling 2026-10-10): no rigid camera fits the AI 3/4 panel; the side + top views are the
        # exact-match authority, the 3/4 rows are measured and REPORTED (not blocking)
        ok_iou = (q.get("iou") or 0) >= 0.93 or bool(ex.get("pass"))
        r = g("L2 3/4 FRONT (LEFT) IoU, camera solved (reported, R39)", q.get("iou"),
              ">= 0.93 (or the R38 exception); reported only (R39)", True,
              "bar %s; %s" % ("met" if ok_iou else "not met", exn))
        r["reported"] = True
        r["bar_met"] = ok_iou
        gates.append(r)
        cp = (q.get("contour_px") or {}).get("p95")
        ok_cp = (cp is not None and cp <= 3) or bool(ex.get("pass"))
        r = g("L2 3/4 contour P95 (sheet px) (reported, R39)", cp, "<= 3 (or the R38 exception); reported only (R39)",
              True, "bar %s; panel consistency: %s" % ("met" if ok_cp else "not met",
                                                      json.dumps(q.get("panel_consistency", {}).get("reading"))[:400]))
        r["reported"] = True
        r["bar_met"] = ok_cp
        gates.append(r)
    else:
        gates.append(g("L2 3/4 FRONT (LEFT)", "not run", ">= 0.93", False))
    # ---- L3 / L4
    gates.append(g("L3 LEFT contour P95 (sheet px; R34 conventions, the paddle zone out)", L["contour_px"]["p95"],
                   "<= 2", L["contour_px"]["p95"] <= 2, "raw %s" % (L.get("contour_px_raw") or {}).get("p95")))
    l3bad = [f["feature"] for f in me["L3"] if not f["pass"]]
    gates.append(g("L3 feature positions (<= 2 sheet px = %.2f mm)" % me["tol_mm_side"],
                   "%d / %d" % (len(me["L3"]) - len(l3bad), len(me["L3"])), "all", not l3bad,
                   ("failing: " + ", ".join(l3bad)) if l3bad else ""))
    l4bad = [d for d in me["L4"] if not d["pass"]]
    gates.append(g("L4 key dimensions (<= 0.05 mm unless noted)", "%d / %d" % (len(me["L4"]) - len(l4bad), len(me["L4"])),
                   "all", not l4bad, "; ".join("%s %.3f vs %.3f" % (d["dimension"], d["measured"], d["spec"]) for d in l4bad)))
    # ---- B3, G5
    for grp, d in b3["groups"].items():
        sm = d["summary"]
        v = {"intersecting_steps": sm["intersecting_steps"], "min_clearance_mm": sm["min_clearance_mm"],
             "min_with": sm["min_with"], "rest_mm": sm["rest_clearance_mm"], "end_mm": sm["end_clearance_mm"]}
        if sm.get("allowances"):
            v["allowances"] = sm["allowances"]
        if sm.get("coarse_proof"):
            v["coarse_proof"] = sm["coarse_proof"]
        gates.append(g("B3 %s sweep %s..%s (step %.4f, %d steps)" % (grp, sm["range"][0], sm["range"][1], sm["step"],
                                                                  sm["steps"]), v,
                       "0 intersections (declared allowances only); clearance in row %s" % sm["row_mm"], sm["pass"]))
    gates.append(g("G5 static intersections between parts at rest (LOD0)", len(b3["static_intersections"]), "0",
                   len(b3["static_intersections"]) == 0,
                   ", ".join("%s/%s %d" % (x["a"], x["b"], x["intersecting_triangle_pairs"])
                             for x in b3["static_intersections"])))
    gaps = b3.get("contact_gaps", [])
    zero = [x for x in gaps if x["min_gap_mm"] < 0.009]
    gates.append(g("G5 butt-joint gaps", "min %.4f mm over %d contact pairs" % (min(x["min_gap_mm"] for x in gaps), len(gaps)),
                   ">= 0.01 (0.009 sampling)", not zero,
                   ("below: " + ", ".join("%s/%s %.4f" % (x["a"], x["b"], x["min_gap_mm"]) for x in zero)) if zero else ""))
    # ---- craft F-gates, B3b, B4c
    if fg:
        sel = b3["groups"].get("selector", {}).get("summary", {})
        gates.append(g("F1 selector sweep SAFE..AUTO, swept minimum", sel.get("min_clearance_mm"), ">= 0.10",
                       (sel.get("min_clearance_mm") or 0) >= 0.10 and sel.get("intersecting_steps", 1) == 0))
        gates.append(g("F2 folded length", fg["F2"]["folded_length_mm"], "383.6 +-3 (real 450 reported)", fg["F2"]["pass"],
                       "folded min Y by part %s" % fg["F2"]["folded_min_Y_by_part"]))
        f3 = fg["F3"]
        sf = b3["groups"].get("stock_fold", {}).get("summary", {})
        gates.append(g("F3 stock folded: barb under the port catch's lip", {k: f3.get(k) for k in
                                                                              ("engagement_X_mm", "barb_to_lip_min_distance_mm",
                                                                               "folded_intersections")},
                       "engagement >= 1.0; barb-to-lip 0.2-0.4; 0 intersections folded", f3.get("pass")))
        cl = b3["groups"].get("charging", {}).get("summary", {})
        lk = b3["groups"].get("charging_lock", {}).get("summary", {})
        gates.append(g("F4 charging handle: travel + lock, neck and arm clearances",
                       {"travel_min_mm": cl.get("min_clearance_mm"), "travel_min_with": cl.get("min_with"),
                        "lock_min_mm": lk.get("min_clearance_mm"), "lock_min_with": lk.get("min_with")},
                       "neck 0.15-0.40 to the slot / notch; arm >= 0.10 off the wall at every frame",
                       (cl.get("min_clearance_mm") or 0) >= 0.10 and (lk.get("min_clearance_mm") or 0) >= 0.10
                       and cl.get("intersecting_steps", 1) == 0 and lk.get("intersecting_steps", 1) == 0))
        mr = b3["groups"].get("mag_release", {}).get("summary", {})
        gates.append(g("F5 magazine catch sweep 0..-11 deg, magazine seated", {"intersecting_steps": mr.get("intersecting_steps"),
                                                                               "min_clearance_mm": mr.get("min_clearance_mm"),
                                                                               "min_with": mr.get("min_with")},
                       "0 intersections except the nose leaving the notch", mr.get("intersecting_steps", 1) == 0))
        gates.append(g("F5 bolt thumb recess visible in the port at rest", fg["F5b"], ">= 10 grid rays in the recess",
                       fg["F5b"]["pass"]))
        f6 = fg["F6"]
        gates.append(g("F6 stock latch: full diameter in the lug's bore (released / pressed); fold exit clearance",
                       {"released_mm": f6.get("engaged_full_diameter_released_mm"),
                        "pressed_mm": f6.get("engaged_full_diameter_pressed_mm"),
                        "fold_sweep_min_mm": sf.get("min_clearance_mm"), "fold_min_with": sf.get("min_with")},
                       ">= 1.5 released; 0 pressed; fold sweep >= 0.10", f6.get("pass") and (sf.get("min_clearance_mm") or 0) >= 0.10,
                       f6.get("declared", "")))
        f7 = fg["F7"]
        gates.append(g("F7 charging-handle lock: the neck's rise into the rear notch at the wall's inner face; knob rise",
                       {"neck_rise_mm": f7["neck_rise_at_wall_inner_face_mm"],
                        "neck_top_over_slot_top_mm": f7["neck_top_over_slot_top_mm"],
                        "knob_rise_mm": f7["knob_rise_mm"]}, ">= 2.0 (spec 2.09); knob 5.15 reported", f7["pass"]))
        gates.append(g("B3b folded state: 0 intersections; casing throw cone (reported)", fg["B3b"], "0 intersections",
                       fg["B3b"]["pass"], "throw cone clear: %s" % fg["B3b"]["throw_cone"]["clear"]))
        gates.append(g("B4c sights folded", fg["B4c"], "rear <= Z 60.1, front <= Z 51.7; nothing below the rail top 45.4 (the front over its relief flat: >= 44.8, spec folded_Z)",
                       fg["B4c"]["pass_all"]))
    else:
        gates.append(g("F-gates, B3b, B4c", "not run", "smg_fgates.py", False))
    # ---- B4 / B4b
    for nm, r, rule in (("B4 sight picture (ADS 55 deg, eye 0.25 m behind the aperture)", b4,
                         "post tip at the aperture centre <= 0.2 mm; post visible; no occluder"),
                        ("B4b sight picture at the cheek-weld eye (90 mm behind the aperture), reported", b4b, "reported")):
        if r and "lateral_offset_mm" in r:
            gates.append(g(nm, {"lateral_mm": r["lateral_offset_mm"], "vertical_mm": r["vertical_offset_mm"],
                                "aperture_mm": r["aperture"]["diameter_mm_at_aperture"],
                                "post_visible_mm": r["post"]["visible_height_in_aperture_mm_at_aperture"],
                                "occluders": r.get("occluders_in_aperture_px")}, rule,
                           r["pass"] if nm.startswith("B4 ") else True, r.get("image", "")))
        else:
            gates.append(g(nm, (r or {}).get("error", "not run"), rule, nm.startswith("B4b")))
    # ---- B6a, B10, B7, B8, UD1-UD2
    gates.append(g("B6a joined twin: qa_check topology + degenerate checks", b6["passed"], "all pass", b6["passed"],
                   "; ".join("%s: %s" % (c["name"], c["detail"]) for c in b6["checks"])))
    gates.append(g("B10 tokenised gun deny list on every object name", b6["deny_list_clean"], "clean", b6["deny_list_clean"]))
    closed = [k for k, v in rep.items() if v["boundary_edges"] or v["multi_face_edges"]]
    gates.append(g("B7 closed manifold parts", "%d / %d closed" % (len(rep) - len(closed), len(rep)), "all", not closed,
                   ", ".join(closed)))
    # (W4 review fixes) G3o: facets on the openings' boundary loops (smg_facet_check.py on the form triangles)
    fc_p = SCRATCH / "facet_check.json"
    if fc_p.exists():
        fc = json.loads(fc_p.read_text())
        gates.append(g("G3o facets on opening loops (vents, channel + lock notch, port, recesses, windows)",
                       {k: {"holes": v["holes"], "max_facet_deg_r_ge_5": v["max_facet_deg"],
                            "max_sagitta_mm": v["max_sagitta_mm"], "fails": len(v["fail"])} for k, v in fc["parts"].items()},
                       "chord error <= 0.035 mm on every arc; <= 7.5 deg where r >= 5 mm", fc["pass"]))
    else:
        gates.append(g("G3o facets on opening loops", "not run", "smg_facet_check.py", False))
    tri_total = sum(v["triangles"] for v in rep.values())
    tri_mag = sum(v["triangles"] for k, v in rep.items() if k.startswith("magazine"))
    tri_gun = tri_total - tri_mag
    gates.append(g("B8 LOD0 triangles, gun (target 25-40k, ceiling 50k)", tri_gun, "<= 50000 (target <= 40000)",
                   tri_gun <= 50000, "above the 40k target" if tri_gun > 40000 else ""))
    gates.append(g("B8 magazine LOD0 triangles (floor 3,000, qa budget 5,000)", tri_mag, "<= 5000", tri_mag <= 5000))
    ud_keys = ("unreal_drops", "edges_under_0.05mm", "needles_under_0.02mm", "strip_polygons_under_0.1mm")
    ud = {k: sum(int(v.get("ud", {}).get(k) or 0) for v in rep.values()) for k in ud_keys}
    min_area = min(float(v.get("ud", {}).get("min_area_mm2") or 9) for v in rep.values())
    small = {k: v["ud"]["min_area_mm2"] for k, v in rep.items() if (v.get("ud", {}).get("min_area_mm2") or 9) < 0.01}
    gates.append(g("UD1 Unreal degenerate rule on every LOD0 part (drops; min triangle area)",
                   {"unreal_drops": ud["unreal_drops"], "min_area_mm2": min_area}, "0; >= 0.01 mm2",
                   ud["unreal_drops"] == 0 and min_area >= 0.01,
                   ("under the 2x margin: %s (Unreal's own drop rule, 0.005, passes)" % small) if small else ""))
    zt = {k: v.get("ud", {}).get("needle_groups") for k, v in rep.items() if v.get("ud", {}).get("needle_groups")}
    gates.append(g("UD2 micro edges / needles / strips", {k: ud[k] for k in ud_keys[1:]}, "0 / 0 / 0",
                   all(ud[k] == 0 for k in ud_keys[1:]),
                   "information (UD3-type, W2): gunlib zero-tangent-risk needle-corner groups %s" % zt if zt else ""))
    # ---- H1 early
    if h1:
        gi, rc = h1["girth"], h1["reach"]
        gates.append(g("H1 early: grip girth vs real polymer SMG grips + 10 %",
                       {"perimeter_mm": gi["perimeter_mm"], "width_Y_mm": gi["width_Y_mm"], "depth_mm": gi["depth_mm"]},
                       "<= %.1f mm (real band %s + 10 %%)" % (gi["limit_mm"], gi["real_band_mm"]), gi["pass"]))
        gates.append(g("H1 early: trigger reach (web hollow -> trigger face)", rc["reach_mm"], "<= 80 mm (real %s)"
                       % rc["real_band_mm"], rc["pass"], "the sheet's reach at 625 reads 82.0; a FAIL puts Q1 to the user "
                                                         "(does not stop the build)"))
        gates.append(g("H1 early: Grip depth vs the hand's palm centre (reported)", h1["grip"],
                       "|46 - palm| <= 1 mm", h1["grip"]["pass"]))
        gates.append(g("H1 early: SupportHand on the magwell front (reported)", h1["support"], "<= 1.5 mm, reachable",
                       h1["support"]["pass"]))
        gates.append(g("H1 early: length of pull and cheek weld (reported)", {"length_of_pull": h1["length_of_pull"],
                                                                              "cheek_weld": h1["cheek_weld"]}, "reported", True))
    else:
        gates.append(g("H1 early", "not run", "fit body", False))
    # ---- MAGFIT
    if mf:
        for x in mf["gates"]:
            gates.append(g("MAGFIT " + x["name"], x["value"], x["threshold"], x["pass"], x.get("note", "")))
    else:
        gates.append(g("MAGFIT form magazine fit", "not run", "gates/form_magfit.json", False))
    # ---- L8 early realism: the renders; the verdict belongs to the realism judges (run by the orchestrator)
    early = {"renders": [s["out"] for s in (er or {}).get("shots", [])], "contact": rel(EARLY / "contact.png")
             if (EARLY / "contact.png").exists() else None,
             "verdict": "pending: 2 realism judges per part group (plan 14.1 L8), not run by this stage"}
    declared = [
        "stock latch: stroke 2.5 (spec 2.0) and full-diameter engagement 1.75 (2.5 with the 45 deg inner shoulder): with "
        "real shoulders the spec's 2.0 stroke / 2.0 engagement / 6.4 neck / 6.0 lug do not close (F6 passes at 2.5)",
        "stock latch: the end block lug's outer face relieved 0.8 under the button (X < 245.4): folding, the pressed button "
        "and the bolt's outer shoulder drift up to 0.46 inward; the head's lug recess 0.9 on its outer side",
        "bolt: underside on the rails' shelf (Z -9.0, spec box -10.1): the spec bolt hung 1 mm under the R30 shelf and left "
        "the seated magazine 0.5 overtravel (M2 asks 1.0-2.0); invisible (the port shows Z >= 2.3); face boss 0.15 short "
        "of the breech (sliding row)",
        "magazine: floor plate bottom at the traced -158.3 along the axis (spec floor_along_axis -160.57 sits 2.3 under "
        "the traced plate and under box_M Z -230)",
        "ejection port: the visible front edge is the port catch's lip (spec catch X 463.1 < port X 464.3)",
        "mag catch: nose top 0.2 under the notch's bearing face, tip +0.15 (M2 0.0-0.3, M3 >= 1.5 past the 0.3 break), "
        "top-front corner chamfered 0.8 (releasing, the nose lifts 0.14 at exit), pad's lower front corner R 2.0 (released "
        "it stops 0.1+ short of the magwell), the guard leg relieved 1.2 above the pin, the nose slot opened 3.6 rearward",
        "charging slide: hook 0.2 off the bolt's lug at rest (449.2, spec 449.02: the sliding row's lower bound)",
        "front sight leaf: round end R 2.25 about the pin (B4c folded <= 51.7)",
        "muzzle device: six slots symmetric about the bore (the side panels draw the side slot ~2.5 mm high)",
        "muzzle wrench flats: 0.5 deep at +-35 deg off the bottom (spec 'two 3 mm flats' read as their chord scale)",
        "fore-end: the moulded charging-slide guide runs on to the front wall (the sheet's long vents read dark, not "
        "daylight)",
        "stock head: narrower than the end block (Y -25..22) with the latch housing boss proud on the left to Y 28.6 "
        "(3/4 and TOP read); at the neck's end its top / bottom held 0.5 inside the neck's (no coplanar union faces)",
        "lower rail: its rear end butts the lower's flat front face across the rail band (X 484.2, 0.3 gap; R42: the "
        "former 4.1 mm pocket left a hooked flap); L2 per part leaves the stretch behind the face line out (R33)",
        "front sight: the TOP panel's right-side knob is not built (R40: RIGHT + 3/4 draw none, real pattern); the "
        "cross-bolt ends in a captive hex nut, the cheeks carry a lower rear step over the knob's X span",
        "outlines: every traced ring faired (R41: corners pinned, runs smoothed, straight stretches on their "
        "least-squares lines); the trigger one fair curve through the trace and the guard one opening (R42)",
        "front sight base: starts at X 532.3 (spec base_X) while the sheet draws its rear face at ~529.6: the folded "
        "leaf's head lands behind 532.3 (B4c); the 2.7 x 5 mm strip shows in the side IoU",
        "front sight leaf: below the head (Z < 61) the arm is 3.5 wide in X (the folded arm clears the base top by "
        "0.15), above it the head 6.6 (B4c); the sheet draws 11.5: L2 per part against the fold ceiling (R33)",
        "rear sight leaf: the head's rear face at 293.7 (folded top 59.8 <= 60.1); the sheet draws 292.3",
        "muzzle device: real through-slots (daylight through the bore at the 90 / 270 deg pair); the sheet draws dark "
        "slots and a 1 px daylight slit at the upper slot: measured hole-filled (R33 / R34)",
        "magazine: body 41.4 + the front spine rib 0.8 = the traced 42.2 front-to-back (R35)",
        "magazine catch: spring-loaded, cammed back by the magazine's top rear edge on its 41 deg underside ramp and "
        "snapping into the notch (M4 per R36); the well's mouth a 0.25 / 2.5 mm lead-in (M2 per R36)",
        "grip: sections perpendicular to the raked axis held 16 mm on up into the housing (the front strap's top corner "
        "otherwise sat 14 mm under the housing)",
    ]
    info_only = ("H1 early: Grip depth", "H1 early: SupportHand", "H1 early: length of pull", "B4b ")
    hard = [x for x in gates if not x["pass"] and not x["name"].startswith(info_only)]
    status = "pass" if not hard else "fail"
    res = {"stage": "W1b form", "date": datetime.now().isoformat(timespec="seconds"), "status": status,
           "failed": [x["name"] for x in hard], "gates": gates, "declared_deviations": declared,
           "details": {"silhouette": sil, "q34": q, "B3": b3, "B4": b4, "B4b": b4b, "B6a": b6, "measure": me, "H1": h1,
                       "F": fg, "build_report": rep, "early_realism": early},
           "files": {"blend": rel(ROOT / "Assets" / "Guns" / "SMG01.blend"),
                     "form_stage_blend": rel(SCRATCH / "SMG01_form_stage.blend"),
                     "renders": [rel(p) for p in sorted(RENDERS.glob("form_grey_*.png"))],
                     "overlays": [rel(p) for p in sorted((REVIEW / "form").glob("*.png"))],
                     "early_realism": early["renders"]}}
    (GATES / "form.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"status": status, "failed": res["failed"]}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="form")
    ap.add_argument("--early", default="early_realism", help="the review set (under review/) the gates cite")
    a = ap.parse_args()
    globals()["EARLY"] = REVIEW / a.early
    {"blockout": stage_blockout, "form": stage_form}[a.stage]()
