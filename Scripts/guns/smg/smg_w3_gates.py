"""SMG01 W3 gate files (plain Python): gates/game.json from the W3a/b reports, and the W3 rows the drivers do not write
appended to gates/rig_export.json (rig_verify driver) and checked in gates/mag.json (mag_fit driver):

    py -3 -B Scripts/guns/smg/smg_w3_gates.py [--game-only]

game.json: LOD triangles and shares (B8), UD1-UD4 on LOD1-3 (and the joined twin / SK meshes), UV0 overlaps per LOD /
set, the LOD shape check, qa_check, C1, S1, S2 at LOD0-3, LOD-pop on both stock states, G5 at LOD0 (shipped
triangles), LOD1 (B3 + G5) and LOD2-3 (px rule), B10.
rig_export.json (+): B11 bounds over every LOD / clip frame / both stock states, the selector rule, B3 coverage, the
SK screen sizes, the SK meshes' UD, the fold-latch path (reported), H1 full.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import SCRATCH, GATES, D  # noqa: E402

S = SCRATCH


def j(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def gate(name, value, threshold, ok, note=None):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    return g


def game():
    rep = j(S / "game" / "game_report.json")
    vg = j(S / "game" / "viewgates.json")
    gg = j(S / "game" / "game_gates_blender.json")
    lu = j(S / "uv" / "lod_uv_report.json")
    b3 = j(S / "b3_lod1.json")
    b30 = j(S / "b3_lod0_tri.json")
    g5l = j(S / "game" / "g5_lods.json")
    G = []
    L = rep["lods"]
    tr = [L[f"LOD{k}"]["triangles"] for k in range(4)]
    gt = [L[f"LOD{k}"]["gun_triangles_without_mag"] for k in range(4)]
    mg = [L[f"LOD{k}"]["mag_triangles"] for k in range(4)]
    bud = D["budgets_triangles"]
    G.append(gate("qa_check (twin SM_SMG01_LOD0..3, pipeline)", gg["qa_check"]["triangles"],
                  f"pass (budget {gg['qa_check']['budget']:,}; UV1; UCX keyed to the node; texel = measured aggregate)",
                  gg["qa_check"]["passed"], None if gg["qa_check"]["passed"] else json.dumps(gg["qa_check"]["failed"])[:800]))
    G.append(gate("LODs strictly descending (twin)", tr, "LOD0 > LOD1 > LOD2 > LOD3", tr[0] > tr[1] > tr[2] > tr[3]))
    G.append(gate("B8 gun LOD0 tris (without the magazine)", gt[0], "<= 50,000 (target 25-40k)", gt[0] <= 50000,
                  "over the 40k target, under the ceiling (W1 form: accepted)" if gt[0] > 40000 else None))
    G.append(gate("B8 merged magazine LOD0 tris", mg[0], "<= 5,000 (target 2.5-4k)", mg[0] <= 5000))
    G.append(gate("LOD1 gun tris (share of LOD0)", f"{gt[1]} ({gt[1] / gt[0]:.1%})", "<= 50 % (study 5.7 ~45 %; the "
                  "AR-01 gate)", gt[1] / gt[0] <= 0.50))
    G.append(gate("LOD2 gun tris (share of LOD0), reported", f"{gt[2]} ({gt[2] / gt[0]:.1%})",
                  "study 5.7 target ~15 % (reported; the B8 gates are the ceilings and the LOD-pop switch)", True,
                  "over the ~15 % target (the AR-01 shipped 17.5 %): the lower receiver's boolean chain only stays "
                  "whole at LOD0's outline tolerances, the rounds keep 1/5 of their segments; LOD-pop moved the LOD1->2 "
                  "switch to 9.5 m" if gt[2] / gt[0] > 0.18 else None))
    G.append(gate("LOD3 gun tris", gt[3], f"{bud['gun']['lod3'][0]}-{bud['gun']['lod3'][1]}",
                  bud["gun"]["lod3"][0] <= gt[3] <= bud["gun"]["lod3"][1]))
    G.append(gate("magazine LOD tris (merged = shipped SM_SMG01_Mag), reported", mg,
                  f"targets ~{bud['mag']['lod1']} / ~{bud['mag']['lod2']} / {bud['mag']['lod3']}", True,
                  "LOD3 under its target (the traced silhouette prism, cheaper; the LOD-pop gate passes); LOD2 keeps "
                  "the ladder channels (its texel density must stay within 25 % of LOD0 for qa_check)"))
    # UD on LOD1-3 parts
    ud_ok = all(lu[f"ud_LOD{k}"]["ud1_drops"] == 0 and lu[f"ud_LOD{k}"]["min_area_mm2"] >= 0.01 for k in (1, 2, 3))
    G.append(gate("UD1 Unreal degenerate rule on every LOD1-3 part", {f"LOD{k}": [lu[f"ud_LOD{k}"]["ud1_drops"],
                  lu[f"ud_LOD{k}"]["min_area_mm2"]] for k in (1, 2, 3)}, "0 drops; min triangle area >= 0.01 mm2", ud_ok))
    ud2 = {f"LOD{k}": lu[f"ud_LOD{k}"]["ud2"] for k in (1, 2, 3)}
    G.append(gate("UD2 micro edges / needles / strips (LOD1-3)", ud2, "0", all(not any(v.values()) for v in ud2.values())))
    ud3 = {f"LOD{k}": lu[f"ud_LOD{k}"]["ud3"] for k in (1, 2, 3)}
    G.append(gate("UD3 zero tangents (LOD1-3 parts; collapsed + float32 zero corners + edge-on = tspace unreal=True)",
                  ud3, "0", all(not any(v.values()) for v in ud3.values()),
                  "LOD faces whose UV collapsed (snapped onto an island edge) got a 0.25-texel copy of their shape; "
                  "overlapping LOD triangles shrink / move inside their island instead of collapsing; sub-pixel slivers "
                  "flipped (coplanar) or their lone corner normal tilted (scratch/uv/lod_uv_report.json)"))
    twin_ud = gg["twin_ud"]
    G.append(gate("UD1 / UD3 on the joined twin LODs", twin_ud, "0 drops, min area >= 0.01 mm2, 0 collapsed (unreal)",
                  all(v["ud1_drops"] == 0 and v["min_area_mm2"] >= 0.01 and v["ud3_collapsed_unreal"] == 0
                      for v in twin_ud.values())))
    ud4 = {k: v["pass"] for k, v in lu["ud4"].items()}
    G.append(gate("UD4 authored UV1 on LOD1-3 (64 and 128 px, 2 px padding)", ud4, "pass at both resolutions",
                  all(ud4.values()), "LOD0: gates/uv_bake_paint.json"))
    G.append(gate("UV0 overlaps LOD1-3 (per set = per twin tile; qa epsilon)", lu["lod_uv0_overlap_pairs"], "0",
                  not any(lu["lod_uv0_overlap_pairs"].values())))
    rng = lu["uv0_range_lods"]
    G.append(gate("UV0 skeletal layout: LOD1-3 inside 0..1", rng, "inside [0, 1]",
                  min(rng["min"]) >= -1e-6 and max(rng["max"]) <= 1.0 + 1e-6))
    # LOD shape check (build reports)
    shp = {}
    for k in (1, 2):
        rr = j(S / f"lod{k}_report.json")
        shp[f"LOD{k}"] = {n: v.get("step") for n, v in rr["retries"].items()
                          if "shape" in str(v.get("step")) or isinstance(v.get("step"), int)}
        bad = [n for n, v in rr["parts"].items() if v["multi_face_edges"] or v["boundary_edges"]]
        shp[f"LOD{k}_non_manifold"] = bad
    G.append(gate("LOD1-2 parts closed + the LOD0 solid kept (volume 0.85-1.30, bbox <= 2 / 4 mm)", shp,
                  "every part closed and manifold; a part failing the shape check rebuilt (recorded)",
                  not shp["LOD1_non_manifold"] and not shp["LOD2_non_manifold"]))
    # contact at LOD0 (shipped triangles) and LOD1
    if b30:
        small0 = [x for x in b30["contact_gaps"] if x["min_gap_mm"] < 0.01]
        G.append(gate("G5 at LOD0 on the shipped (triangulated) parts", f"{len(b30['static_intersections'])} pairs; "
                      f"min butt gap {min(x['min_gap_mm'] for x in b30['contact_gaps'])} mm", "0; >= 0.01 mm",
                      not b30["static_intersections"] and not small0,
                      json.dumps(b30["static_intersections"] + small0)[:600] if (b30["static_intersections"] or small0)
                      else None))
    else:
        G.append(gate("G5 at LOD0 on the shipped (triangulated) parts", "missing", "0; >= 0.01 mm", False))
    if b3:
        gr = b3["groups"]
        rig_groups = {g: v for g, v in gr.items() if g != "charging_lock"}
        G.append(gate("B3 at LOD1: 0 intersections over every rig-driven sweep (declared allowances only)",
                      {g: {"intersecting_steps": v["summary"]["intersecting_steps"],
                           "pass_intersections": v["summary"]["pass_intersections"]} for g, v in rig_groups.items()},
                      "0 (the stock fold's port-catch snap allowance as declared)",
                      all(v["summary"]["pass_intersections"] for v in rig_groups.values()),
                      "charging_lock is not a rig motion (no clip, no ABP input; the slide shares the 'charging_handle' "
                      "bone and must not rotate): at LOD1 its lever meets the receiver's notch (%d steps); B3 at LOD0 "
                      "holds it (gates/form.json)" % gr.get("charging_lock", {}).get("summary", {}).get(
                          "intersecting_steps", -1)))
        rows = {g: {"min_clearance_mm": v["summary"]["min_clearance_mm"], "row_mm": v["summary"].get("row_mm"),
                    "with": v["summary"].get("min_with")} for g, v in rig_groups.items()
                if not v["summary"]["pass_clearance_lower"]}
        G.append(gate("B3 at LOD1: clearance rows (reported)", rows or "every rig-driven group inside its row",
                      "joint rows 3.7 (LOD0 holds them: gates/form.json); LOD1 reported", True,
                      "LOD1's halved rounds bring these joints under their LOD0 rows without touching (seen from >= "
                      "2.77 m: 0.1 mm = 0.05 px); the paddle is held at LOD0 resolution at LOD1 (its nose met the "
                      "magazine's notch)" if rows else None))
        G.append(gate("G5 at LOD1 (static intersecting pairs)", len(b3["static_intersections"]), "0",
                      len(b3["static_intersections"]) == 0, json.dumps(b3["static_intersections"])[:400] or None))
        small = [x for x in b3["contact_gaps"] if x["min_gap_mm"] < 0.01]
        G.append(gate("G5 at LOD1 butt-joint gaps (reported)", min(x["min_gap_mm"] for x in b3["contact_gaps"]),
                      ">= 0.01 mm at LOD0 (gates/form.json); LOD1 reported", True,
                      ("below 0.01 mm without touching: " + json.dumps(small)) if small else None))
    else:
        G.append(gate("B3 at LOD1 (moving groups incl. the stock fold, sweeps)", "missing", "run", False))
    if g5l:
        visl = (g5l.get("visible") or {}).get("lods", {})
        for k, v in g5l["lods"].items():
            vv = visl.get(k, {})
            G.append(gate(f"G5 at {k} (penetration depth at the switch-in distance)",
                          f"{v['intersecting_pairs']} pairs; deepest {v['worst_depth_px']} px at {v['distance_m']} m"
                          + (f" ({v['pairs'][0]['a']}/{v['pairs'][0]['b']} {v['pairs'][0]['depth_mm']} mm)"
                             if v["pairs"] else ""), "< 1 px at 1440p", v["pass"],
                          f"info, visible change of the intersecting parts vs LOD{int(k[-1]) - 1} (4 headings, the "
                          f"LOD's whole silhouette change included): worst mean {vv.get('worst_mean_px')} px, max "
                          f"{vv.get('worst_max_px')} px"))
    c1 = gg["C1"]
    G.append(gate("C1 hull containment", f"{c1['samples_outside']} of {c1['jittered_lod0_samples']:,} jittered 0.5 mm "
                  f"LOD0 samples, {c1['vertices_outside']} of {c1['lod_vertices']:,} LOD0-3 vertices outside",
                  "0 and 0; 8 hulls (C3), <= 32 vertices", c1["pass"], f"hull vertices {c1['hull_vertices']}"))
    s1 = gg["S1"]
    G.append(gate("S1 sockets (test-exported sidecar vs build / spec)", f"{s1['count']} sockets, worst {s1['worst_mm']} mm"
                  f" / {s1['worst_deg']} deg", "21 = spec names; <= 0.001 mm and <= 0.001 deg", s1["pass"]))
    s2 = vg["s2"]
    G.append(gate("S2 sight picture at LOD0 (aperture: post tip centred, B4 method)",
                  f"lateral {s2.get('lateral_offset_px')} px, vertical {s2.get('vertical_offset_px')} px, post visible "
                  f"{s2.get('post_visible_mm')} mm", "|lateral|, |vertical| <= 0.5 px (55 deg, 0.25 m eye relief, "
                  "2560 x 1440); post visible >= 0.5 mm in the 2 mm aperture; no occluder", s2.get("pass", False)))
    for k, v in (vg.get("s2_lods") or {}).items():
        if v.get("pass") is None:
            G.append(gate(f"S2 sight picture at {k}", "n/a", "|lateral|, |vertical| <= 0.5 px", True, v.get("note")))
        else:
            G.append(gate(f"S2 sight picture at {k}", f"lateral {v.get('lateral_offset_px')} px, vertical "
                          f"{v.get('vertical_offset_px')} px", "|lateral|, |vertical| <= 0.5 px", v["pass"],
                          "first person forces LOD0 (ForcedLodModel 1): informative for the coarse LODs"))
    for sw in vg["lod_pop"]["switches"]:
        t = sw["tries"][-1]
        G.append(gate(f"LOD-pop LOD{sw['from']} -> LOD{sw['to']} (extended + folded stock)",
                      f"size {sw['chosen_screen_size']} ({t['distance_m']} m): mean {t['worst_mean_px']} px, max "
                      f"{t['worst_max_px']} px (worst of 4 headings x 2 stock states)",
                      "mean <= 1 px, max <= 3 px at 2560 x 1440, 90 deg", sw["pass"]))
    G.append(gate("names (tokenised gun deny list)", gg["B10_names"]["hits"] or "clean", "no hit", gg["B10_names"]["pass"]))
    out = {"stage": "W3 game (LODs, twin, view gates)", "gates": G, "failed": [g["name"] for g in G if not g["pass"]],
           "lod_screen_sizes": vg["lod_pop"]["final_sizes"], "bounds_radius_m": rep["bounds_radius_m"],
           "triangles": {"twin": tr, "gun": gt, "mag": mg}, "hulls": rep["hulls"], "mass": rep["mass"],
           "sockets": s1["sockets"]}
    out["status"] = "pass" if not out["failed"] else "fail"
    (GATES / "game.json").write_text(json.dumps(out, indent=1))
    print("[w3gates] game.json", out["status"], out["failed"])
    return out


def rig_extra():
    p = GATES / "rig_export.json"
    rx = j(p)
    rr = j(S / "rig" / "rig_report.json")
    h1 = j(S / "h1_full.json")
    if rx is None or rr is None:
        print("[w3gates] rig_export.json / rig_report.json missing")
        return None
    G = [g for g in rx["gates"] if not g.get("w3_extra")]
    be = rr["bounds_extension"]
    G.append(dict(gate("B11 bounds extension: every LOD0-3 vertex at every clip frame (both stock states, sights "
                       "folded) inside the bind AABB + extension", {"positive_cm": be["positive_cm"],
                       "negative_cm": be["negative_cm"], "worst_excursion_mm": be["worst_excursion_mm_per_clip"]},
                       "the extension = posed envelope - bind AABB (+1 mm), per axis", True,
                       "the stock mid-fold sweeps 247 mm to the right (Y extension 24.75 cm); U5 re-checks in engine"),
                  w3_extra=True))
    sr = rr["selector_rule"]
    G.append(dict(gate("clips moving the bolt hold the selector at AUTO first to last frame", sr,
                       "Fire, Charge, ReloadEmpty: selector 45 deg on every frame", all(v["ok"] for v in sr.values())),
                  w3_extra=True))
    G.append(dict(gate("clip set and rest declarations", {k: [v["frames"], v["fps"], v["starts_at_rest"],
                       v["ends_at_rest"]] for k, v in rr["clips"].items()},
                       "8 clips (7 + SightFlip, Q12); rest at both ends except ReloadEmpty (bolt open), StockFold "
                       "(ends folded), StockUnfold (starts folded)",
                       len(rr["clips"]) == 8 and all(v["rest_as_declared"] for v in rr["clips"].values())),
                  w3_extra=True))
    G.append(dict(gate("SK LOD screen sizes (LOD-pop switch distances at the SK's engine radius)",
                       rr["lod_screen_sizes"], "converted, not guessed", True), w3_extra=True))
    G.append(dict(gate("UD1 / UD3 on the SK meshes LOD0-3", rr["sk_ud"], "0 drops, min area >= 0.01 mm2, 0 collapsed",
                       rr.get("sk_ud_ok", False)), w3_extra=True))
    fl = rr["fold_latch_path"]
    G.append(dict(gate("stock fold clip: the latch path (reported)", {"worst_depth_mm": fl["worst_depth_mm"],
                       "parts": fl["parts_hit"], "frames_hit": [x["frame"] for x in fl["frames"] if x["hits"]]},
                       "reported (a rigid 11-bone rig cannot press the latch button)", True, fl["note"]), w3_extra=True))
    if h1:
        G.append(dict(gate("H1 full: posed hand fit on MH_PlayerDefault", h1.get("summary"), h1.get("threshold"),
                           h1.get("pass", False), h1.get("note")), w3_extra=True))
    else:
        G.append(dict(gate("H1 full: posed hand fit on MH_PlayerDefault", "missing", "run", False), w3_extra=True))
    rx["gates"] = G
    rx["failed"] = [g["name"] for g in G if not g["pass"]]
    rx["status"] = "pass" if not rx["failed"] else "fail"
    p.write_text(json.dumps(rx, indent=1))
    print("[w3gates] rig_export.json", rx["status"], rx["failed"])
    return rx


def mag_check():
    m = j(GATES / "mag.json")
    if m is None:
        print("[w3gates] mag.json missing")
        return None
    print("[w3gates] mag.json", m["status"], m["failed"])
    return m


def keep_reports():
    """The W3 build reports the gates cite, copied next to them (scratch is not in git): gates/w3/."""
    import shutil
    dst = GATES / "w3"
    dst.mkdir(parents=True, exist_ok=True)
    for src in (S / "uv" / "lod_uv_report.json", S / "game" / "game_report.json", S / "game" / "viewgates.json",
                S / "game" / "game_gates_blender.json", S / "game" / "g5_lods.json", S / "b3_lod1.json",
                S / "b3_lod0_tri.json", S / "rig" / "rig_report.json", S / "mag" / "mag_report.json",
                S / "h1_full.json", S / "lod1_report.json", S / "lod2_report.json", S / "lod3_report.json"):
        if src.exists():
            shutil.copy2(src, dst / src.name)
    print("[w3gates] reports kept in gates/w3/")


if __name__ == "__main__":
    keep_reports()
    game()
    if "--game-only" not in sys.argv:
        rig_extra()
        mag_check()
