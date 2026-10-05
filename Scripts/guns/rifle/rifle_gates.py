"""Assemble the AR-01 stage gate files from the measured results (plain Python):

    py -3 -B Scripts/guns/rifle/rifle_gates.py --stage blockout|form

blockout -> WorkFiles/guns/rifle/gates/blockout.json   (L1 + the magazine-thickness check on the solved 3/4 view)
form     -> WorkFiles/guns/rifle/gates/form.json       (L2, L3, L4, B3, B6a, H1 early, budgets, closed solids,
                                                         the early image-pair crops)
Also writes render-vs-sheet comparison images (grey renders blended over the sheet panels) into review/<stage>/.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import ROOT, SPEC, GATES, SCRATCH, REVIEW, RENDERS, SHEET, TRACE  # noqa: E402


def load(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def g(name, value, threshold, ok, note=""):
    d = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        d["note"] = note
    return d


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")


def blend_images(stage):
    """Grey render at panel scale over the sheet panel: side-by-side and a 50 % blend."""
    out = []
    sheet = Image.open(SHEET).convert("RGB")
    for view, box_src in (("side", "LEFT"), ("top", "TOP"), ("q34", None)):
        r = RENDERS / f"form_grey_{view}.png"
        if not r.exists():
            continue
        if box_src:
            box = json.loads((TRACE / f"{box_src}_outline.json").read_text())["panel_box_sheet_px"]
        else:
            box = (771, 322, 1528, 600)
        P = sheet.crop((box[0], box[1], box[2] + 1, box[3] + 1))
        R = Image.open(r).convert("RGB").resize((P.width * 2, P.height * 2), Image.LANCZOS)
        P2 = P.resize((P.width * 2, P.height * 2), Image.LANCZOS)
        both = Image.new("RGB", (P2.width, P2.height * 3 + 20), (255, 255, 255))
        both.paste(P2, (0, 0))
        both.paste(R, (0, P2.height + 10))
        both.paste(Image.blend(P2, R, 0.5), (0, 2 * P2.height + 20))
        o = REVIEW / stage / f"render_vs_sheet_{view}.png"
        both.save(o)
        out.append(rel(o))
    return out


def stage_blockout():
    sil = load(SCRATCH / "sil_blockout.json")
    q = load(REVIEW / "blockout" / "q34_result.json")
    s, t = sil["views"]["side"], sil["views"]["top"]
    gates = [g("L1 side IoU vs traced LEFT-labelled panel (similarity fit)", s["iou_fit"], ">= 0.95", s["iou_fit"] >= 0.95),
             g("L1 top IoU vs traced TOP panel (excluded zones masked)", t["iou_fit_valid"], ">= 0.92",
               t["iou_fit_valid"] >= 0.92, "excluded: TOP left-side bumps X 236-295 / 353-462 (spec excluded_zones) and "
               "the charging-handle knob the TOP draws 25 mm forward; all-pixel IoU %.4f" % t["iou_identity_all_pixels"]),
             g("L1 stop rule (change method below 0.90)", min(s["iou_fit"], t["iou_fit_valid"]), ">= 0.90",
               min(s["iou_fit"], t["iou_fit_valid"]) >= 0.90)]
    mt = q["magazine_thickness_check"]
    info = {"magazine_thickness_check_on_solved_3q_view": mt,
            "camera": q.get("camera"), "camera_landmark_rms_px": q.get("landmark_rms_px"),
            "q34_iou_blockout": q.get("iou"),
            "verdict": ("%.1f (spec, R32: the physical minimum of a staggered double stack): the 3/4 panel prefers "
                        "%.1f mm (IoU %.4f at the best vs %.4f at the spec value); the panel is thinner than a real "
                        "magazine can be (camera landmark residual %.1f px RMS)"
                        % (mt["spec_mm"], mt["parabola_peak_mm"], max(mt["iou_in_mag_zone_by_thickness_mm"].values()),
                           mt["iou_in_mag_zone_by_thickness_mm"].get(str(int(mt["spec_mm"])),
                                                                   mt["iou_in_mag_zone_by_thickness_mm"].get(int(mt["spec_mm"]), 0)),
                           q.get("landmark_rms_px", 0)))}
    res = {"stage": "1 blockout", "date": datetime.now().isoformat(timespec="seconds"),
           "status": "pass" if all(x["pass"] for x in gates) else ("fail" if min(s["iou_fit"], t["iou_fit_valid"]) < 0.90 else "partial"),
           "gates": gates, "details": {"silhouette": sil, "magazine_thickness": info},
           "method": "primary volumes = the traced side profiles (spec side_profile_M, Douglas-Peucker 0.35 mm) extruded "
                     "across their TOP widths; stock tapered by the TOP width profile; round parts as cylinders; "
                     "magazine = the traced magazine ring at the spec thickness (26 mm, R32). IoU on 4x supersampled rasters in the trace's own "
                     "px<->mm frame (no camera error).",
           "files": {"blend": rel(SCRATCH / "AR01_blockout.blend"), "overlays": [rel(p) for p in sorted((REVIEW / "blockout").glob("*.png"))]}}
    (GATES / "blockout.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"status": res["status"], "gates": gates}, indent=1))


def stage_form():
    sil = load(SCRATCH / "sil.json")
    q = load(REVIEW / "form" / "q34_result.json")
    b3 = load(SCRATCH / "b3_result.json")
    b6 = load(SCRATCH / "b6a_result.json")
    me = load(SCRATCH / "measure_result.json")
    h1 = load(SCRATCH / "h1_result.json")
    rep = load(SCRATCH / "form_build_report.json")
    cl = load(SCRATCH / "closeup_cameras.json")
    b4 = load(SCRATCH / "b4_result.json")
    s, t, l = sil["views"]["side"], sil["views"]["top"], sil["views"]["left_vs_RIGHT_panel"]
    gates = []
    gates.append(g("L2 side IoU (authority, rifle + seated mag)", s["iou_fit"], ">= 0.96", s["iou_fit"] >= 0.96))
    gates.append(g("L2 top IoU (excluded zones masked)", t["iou_fit_valid"], ">= 0.93", t["iou_fit_valid"] >= 0.93))
    gates.append(g("L2 true-left vs RIGHT-labelled panel", l["iou_fit"], ">= 0.88", l["iou_fit"] >= 0.88))
    parts = s["parts"]
    bad = [k for k, v in parts.items() if not v["pass"]]
    gates.append(g("L2 per part (IoU >= 0.95 for masks >= 400 px; thin parts contour P95 <= 1 px, max <= 2 px)",
                   "%d / %d parts pass" % (len(parts) - len(bad), len(parts)), "all", not bad,
                   "failing: " + ", ".join("%s (IoU %.3f, P95 %s, max %s)" % (k, parts[k]["iou"], parts[k]["contour_p95_px"],
                                                                       parts[k]["contour_max_px"]) for k in bad)))
    ex = q.get("exception", {})
    nc = ex.get("not_explained", ex.get("not_contradictions", []))
    gates.append(g("L2 3/4 view IoU (camera solved, outer silhouettes)", q["iou"], ">= 0.93", q["iou"] >= 0.93,
                   "raw (our holes open against the hole-filled reference mask, the round-0 measure) %.4f; camera "
                   "landmark residual %.1f px RMS" % (q.get("iou_raw_unfilled", float("nan")), q.get("landmark_rms_px", float("nan")))))
    gates.append(g("L2 3/4 view contour P95 (sheet px)", q["contour_px"]["p95"], "<= 3", q["contour_px"]["p95"] <= 3))
    gates.append(g("L2 3/4 documented exception (IoU >= 0.915 and every residual region > 3 px a 3/4-panel contradiction "
                   "or the magazine physical-minimum residual)",
                   {"iou": q["iou"], "regions_over_3px": ex.get("regions_over_3px"), "contradictions": ex.get("contradictions"),
                    "magazine_minimum": ex.get("magazine_minimum")},
                   "IoU >= 0.915 and all regions contradict LEFT/RIGHT/TOP or are the R32 magazine residual", bool(ex.get("pass")),
                   ("not explained: " + "; ".join("region %d %s: %s" % (r["id"], "/".join(r["objects"]), r["verdict"])
                                                  for r in nc) if nc else "all regions explained")
                   + "; evidence images " + ex.get("evidence_dir", "")))
    gates.append(g("L3 side contour P95 (sheet px)", s["contour_px"]["p95"], "<= 2", s["contour_px"]["p95"] <= 2))
    l3bad = [f["feature"] for f in me["L3"] if not f["pass"]]
    gates.append(g("L3 feature positions (<= 2 sheet px = %.2f mm)" % me["tol_mm_side"],
                   "%d / %d" % (len(me["L3"]) - len(l3bad), len(me["L3"])), "all", not l3bad,
                   ("failing: " + ", ".join(l3bad)) if l3bad else ""))
    l4bad = [d for d in me["L4"] if not d["pass"]]
    gates.append(g("L4 key dimensions (<= 0.05 mm)", "%d / %d" % (len(me["L4"]) - len(l4bad), len(me["L4"])), "all",
                   not l4bad, "; ".join("%s %.3f vs %.3f" % (d["dimension"], d["measured"], d["spec"]) for d in l4bad)))
    for grp, d in b3["groups"].items():
        sm = d["summary"]
        gates.append(g("B3 %s sweep %s..%s (step %.4f, %d steps)" % (grp, sm["range"][0], sm["range"][1], sm["step"], sm["steps"]),
                       {"intersecting_steps": sm["intersecting_steps"], "min_clearance_mm": sm["min_clearance_mm"],
                        "min_with": sm["min_with"], "rest_mm": sm["rest_clearance_mm"], "end_mm": sm["end_clearance_mm"]},
                       "0 intersections; clearance in row %s" % sm["row_mm"], sm["pass"]))
    gates.append(g("G5 static intersections between parts at rest (LOD0)", len(b3["static_intersections"]), "0",
                   len(b3["static_intersections"]) == 0))
    gaps = b3.get("contact_gaps", [])
    zero = [x for x in gaps if x["min_gap_mm"] < 0.009]
    gates.append(g("G5 butt-joint gaps (no vertex of one part within 1 micron of another; modelled 0.01-0.05)",
                   "min %.4f mm over %d contact pairs" % (min(x["min_gap_mm"] for x in gaps), len(gaps)), ">= 0.01 (0.009 sampling)",
                   not zero, ("below: " + ", ".join("%s/%s %.4f" % (x["a"], x["b"], x["min_gap_mm"]) for x in zero)) if zero else ""))
    if b4 and "lateral_offset_mm" in b4:
        gates.append(g("B4 sight picture (ADS 55 deg, eye 0.25 m behind Sight on its line, occlusion-aware raster)",
                       {"lateral_mm": b4["lateral_offset_mm"], "vertical_mm": b4["vertical_offset_mm"],
                        "post_visible_in_notch_mm": b4["post"]["visible_height_in_notch_mm_at_notch"],
                        "occluders": b4["occluders_in_notch_px"]},
                       "|lateral|, |vertical| <= 0.2 mm at the notch; post visible >= 1.0 mm; no occluder", b4["pass"],
                       "post tip vs the notch top (shoulders) and the notch centre, measured in the 2560x1440 raster "
                       "at 8x; image " + b4.get("image", "")))
    else:
        gates.append(g("B4 sight picture", (b4 or {}).get("error", "not run"), "post centred in the notch", False))
    gates.append(g("B6a joined twin: qa_check topology + degenerate checks", b6["passed"], "all pass", b6["passed"],
                   "; ".join("%s: %s" % (c["name"], c["detail"]) for c in b6["checks"]) + "; UV: " + b6["uv_checks"]))
    gates.append(g("B10 tokenised gun deny list on every object name", b6["deny_list_clean"], "clean", b6["deny_list_clean"]))
    closed = [k for k, v in rep.items() if v["boundary_edges"] or v["multi_face_edges"]]
    gates.append(g("B7 closed manifold parts", "%d / %d closed" % (len(rep) - len(closed), len(rep)), "all", not closed,
                   ", ".join(closed)))
    tri_total = sum(v["triangles"] for v in rep.values())
    tri_mag = sum(v["triangles"] for k, v in rep.items() if k.startswith("magazine"))
    tri_rifle = tri_total - tri_mag
    gates.append(g("B8 LOD0 triangles, rifle (target 30-45k, ceiling 50k)", tri_rifle, "<= 50000 (target <= 45000)",
                   tri_rifle <= 50000, "above the 45k target" if tri_rifle > 45000 else ""))
    gates.append(g("B8 magazine block-in triangles (target 4.5k, ceiling 7k)", tri_mag, "<= 7000", tri_mag <= 7000))
    if h1:
        gi, rc, gp = h1["girth"], h1["reach"], h1["grip"]
        gates.append(g("H1 early: grip section vs real AK grips (width, girth)",
                       {"girth_mm": gi["perimeter_mm"], "width_Y_mm": gi["width_Y_mm"], "depth_mm": gi["depth_mm"]},
                       "width %s mm (documented: IMI 30, FAB Gradus 36); girth in %s mm (+2 recess allowance)"
                       % (gi["real_world_width_band_mm"], gi["girth_band_mm"]), gi["pass"],
                       "section perpendicular to the axis at the Grip origin; the round-0 proxy (Kong & Lowe cylinder "
                       "optimum %.1f mm for this hand) is kept as information only" % gi["kong_lowe_cylinder_optimum_mm_info"]))
        gates.append(g("H1 early: trigger reach (web hollow -> trigger face)", rc["reach_mm"],
                       "%s mm (documented: AR-15 2.25 in, Glock 17 72 mm)" % rc["real_world_band_mm"], rc["pass"],
                       "trigger stays where the sheet puts it; round-0 definition (along X at the trigger height) %.1f mm; "
                       "hand web->DIP %.1f, web->pad %.1f mm" % (rc["reach_at_trigger_height_along_X_mm_round0_definition"],
                                                               rc["hand_web_to_DIP_mm"], rc["hand_web_to_pad_mm"])))
        gates.append(g("H1 early: Grip origin depth set from the hand", gp["spec_Grip_depth_mm"],
                       "within 1 mm of the hand's palm centre on the knuckle line (%.1f mm)"
                       % gp["hand_palm_centre_along_knuckle_line_mm"], gp["pass"],
                       "was 40 mm provisional; the 55.2 mm round-0 estimate is the Euclidean web->palm-centre distance, "
                       "which includes the palm's %.1f mm offset behind the axis; the posed H1 at the rig stage records "
                       "hand_offset" % gp["palm_offset_behind_axis_mm"]))
        gates.append(g("H1 early: SupportHand on the handguard underside, reachable", h1["support"]["offset_from_surface_mm"],
                       "|offset| <= 1.5 mm", h1["support"]["pass"]))
    else:
        gates.append(g("H1 early", "blocked", "fit body available", False, "MH_PlayerDefault fit body not found"))
    early = {"crops": {"ours": [rel(REVIEW / "early" / "ours_receiver.png"), rel(REVIEW / "early" / "ours_frontsight.png")],
                       "reference": [rel(REVIEW / "early" / "ref_receiver.png"), rel(REVIEW / "early" / "ref_frontsight.png")]},
             "look": "ROUGH LOOK (gunlib.look; review blend with the grip's checker bake source; selector posed at "
                     "c1's 13.25 deg in the c1 crop)",
             "blind_pairs": rel(REVIEW / "early_blind2"), "blind_key": rel(REVIEW / "early_key2.json"),
             "cameras": cl,
             "note": "the close-ups are stylised and not to scale (spec sheet_panels): weak-perspective cameras with the "
                     "view angles set by eye and scale/shift fitted to landmarks; the blind judge runs in the next stage"}
    # the 3/4 pair (IoU, P95) is met either directly or through the documented exception
    q34_names = ("L2 3/4 view IoU", "L2 3/4 view contour P95")
    exc_ok = any(x["name"].startswith("L2 3/4 documented exception") and x["pass"] for x in gates)
    hard = [x for x in gates if not x["pass"] and not (exc_ok and x["name"].startswith(q34_names))
            and not (x["name"].startswith("L2 3/4 documented exception") and q["iou"] >= 0.93 and q["contour_px"]["p95"] <= 3)]
    lone = min(s["iou_fit"], t["iou_fit_valid"])
    status = "pass" if not hard else ("fail" if lone < 0.90 else "partial")
    res = {"stage": "2 form", "date": datetime.now().isoformat(timespec="seconds"), "status": status,
           "failed": [x["name"] for x in hard], "gates": gates,
           "details": {"silhouette": sil, "q34": q, "q34_section_sweeps": load(SCRATCH / "q34_sweeps.json"),
                       "B3": b3, "B4": b4, "B6a": b6, "measure": me, "H1": h1,
                       "build_report": rep, "early_look": early},
           "files": {"blend": rel(ROOT / "Assets" / "Guns" / "AR01.blend"),
                     "renders": [rel(p) for p in sorted(RENDERS.glob("form_grey_*.png"))],
                     "comparisons": blend_images("form") + [rel(p) for p in sorted((REVIEW / "form").glob("*overlay*.png"))]}}
    (GATES / "form.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({"status": status, "failed": res["failed"]}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="form")
    a = ap.parse_args()
    {"blockout": stage_blockout, "form": stage_form}[a.stage]()
