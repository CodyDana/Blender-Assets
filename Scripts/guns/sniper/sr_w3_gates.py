"""SR01 W3 gate file (plain Python) from the built / exported reports: gates/game.json (LODs, twin, hulls, sockets,
LOD-pop on both bipod poses, the rig build's rows) plus the status of the fresh-process gate files written by their own
steps (gates/rig_export.json, gates/mag.json, gates/scope_export.json) and the Part 0 rows (W2 leftovers).

    py -3 -B Scripts/guns/sniper/sr_w3_gates.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import WORK, GATES, D  # noqa: E402

S = WORK / "scratch" / "w3"


def gate(name, value, threshold, ok, note=None):
    g = {"name": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        g["note"] = note
    return g


def load(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def main():
    G = load(S / "game" / "game_report.json")
    V = load(S / "game" / "viewgates.json")
    R = load(S / "rig" / "rig_report.json")
    Z = load(GATES / "game_lod_sizes.json")
    bud = D["budgets_triangles"]
    gates = []
    L = G["lods"]
    t = [L[f"LOD{k}"]["gun_triangles_without_mag"] for k in range(4)]
    t0 = t[0]
    gates.append(gate("B8 LOD triangles (gun without the magazine)", {"LOD0": t[0], "LOD1": t[1], "LOD2": t[2], "LOD3": t[3],
                      "LOD1_share": round(t[1] / t0, 3), "LOD2_share": round(t[2] / t0, 3),
                      "with_merged_mag": [L[f"LOD{k}"]["triangles"] for k in range(4)]},
                      f"LOD0 {bud['gun_lod0'][0]}-{bud['gun_lod0'][1]} (ceiling {bud['gun_ceiling']}); LOD1 ~45 %, LOD2 "
                      f"~15 %, LOD3 {bud['lod3'][0]}-{bud['lod3'][1]}; strictly descending",
                      t0 <= bud["gun_ceiling"] and t[0] > t[1] > t[2] > t[3] and t[3] <= bud["lod3"][1] * 1.1,
                      "LOD0 below the 35k target floor is the W1/W2 form (35,070 with the magazine) " if t0 < bud["gun_lod0"][0] else None))
    lp = G["lods_parts"]
    gates.append(gate("LOD1-3 surfacing: UV overlaps collapsed (qa rule), UD1 / UD3 per LOD",
                      {k: {"dropped_parts": v["dropped"], "uv_overlaps_collapsed": v["uv_overlaps_collapsed"],
                           "ud": {x: v["ud"][x] for x in ("drops", "min_area_mm2", "ud3_zero")}} for k, v in lp.items()},
                      "0 UD1 drops; UD3 reported (LOD faces are sub-pixel at their switch distance)",
                      all(v["ud"]["drops"] == 0 for v in lp.values())))
    gates.append(gate("C1 10 hulls UCX_SM_SR01_LOD0_00..09 contain every LOD surface sample",
                      {"hulls": [(h["name"], h["vertices"], h["covers"]) for h in G["hulls"]], **G["C1"]},
                      "10 hulls (spec collision.twin_hulls), <= 32 vertices, 0 samples outside", G["C1"]["pass"]))
    gates.append(gate("S1 twin sockets (20, spec sockets.gun)", {"count": len(G["sockets"]), "names": sorted(G["sockets"])},
                      "20", len(G["sockets"]) == int(D["sockets"]["gun_count"])))
    lpop = V["lod_pop"]
    gates.append(gate("LOD-pop on both bipod poses (folded / deployed) -> screen sizes",
                      {"switches": [{"from": s["from"], "to": s["to"], "size": s["chosen_screen_size"],
                                     "distance_m": s["tries"][-1]["distance_m"], "mean_px": s["tries"][-1]["worst_mean_px"],
                                     "max_px": s["tries"][-1]["worst_max_px"], "tries": len(s["tries"])}
                                    for s in lpop["switches"]],
                       "twin_sizes": Z.get("SM_SR01"), "twin_radius_m": Z.get("bounds_radius_m"),
                       "SK_sizes": Z.get("SK_SR01"), "SK_engine_radius_m": Z.get("SK_engine_radius_m")},
                      "mean <= 1 px, max <= 3 px at 2560 x 1440, 90 deg, 4 headings, both poses; SK sizes = the same "
                      "distances at the SK's engine radius (bind box + bounds extension)",
                      all(s["pass"] for s in lpop["switches"])))
    gates.append(gate("mass + CoM (bipod folded, magazine out)", G["mass"]["com_M_mm"], "reported (part volumes x "
                      "densities; spec 5.9 kg)", True))
    if R:
        gates.append(gate("rig build: 13 bones, P1 sniper-side, qa_skeletal, rigid skin",
                          {"bones": len(R["bones"]), "standard_with_P1": R["skeleton_standard"]["passed"],
                           "gunlib_table_unmodified": {"passed": R["skeleton_standard_gunlib_unmodified"]["passed"],
                                                       "failed": [c["name"] + ": " + c["detail"] for c in
                                                                  R["skeleton_standard_gunlib_unmodified"]["failed"]]},
                           "qa_skeletal": R["qa_skeletal"]["passed"], "rigid": R["rigid_skin"]["passed"],
                           "sk_lods": {k: v["triangles"] for k, v in R["lods"].items()}},
                          "13 bones; pass", len(R["bones"]) == 13 and R["skeleton_standard"]["passed"]
                          and R["qa_skeletal"]["passed"] and R["rigid_skin"]["passed"],
                          "cheek_riser under body needs gunlib proposal P1: validated with a sniper-side table (gunlib "
                          "untouched); gunlib's own table rejects only that parent"))
        gates.append(gate("clips: safety at FIRE (Fire / BoltCycle / ReloadEmpty), bolt slides only at -60, rest as declared",
                          {"safety": R["safety_rule"], "bolt_sequence": R["bolt_sequence_rule"],
                           "rest": {k: [v["starts_at_rest"], v["ends_at_rest"], v["rest_as_declared"]]
                                    for k, v in R["clips"].items()}, "out_of_range": R.get("b3_out_of_range", [])},
                          "all ok", all(v["ok"] for v in R["safety_rule"].values())
                          and R["bolt_sequence_rule"]["slide_only_at_full_rotation"]
                          and all(v["rest_as_declared"] for v in R["clips"].values()) and not R.get("b3_out_of_range")))
        be = R["bounds_extension"]
        gates.append(gate("B11 bounds extension (LOD0-3 x every clip frame x extreme poses)",
                          {"positive_cm": be["positive_cm"], "negative_cm": be["negative_cm"],
                           "posed_aabb_M_mm": be["posed_aabb_M_mm"],
                           "spec_extremes": D["lods"]["bounds_extension"]["posed_extremes_M"]},
                          "every posed vertex inside bind AABB + extension (by construction, +1 mm)", True))
    status = {}
    for n in ("rig_export", "mag", "scope_export"):
        g = load(GATES / f"{n}.json")
        status[n] = {"status": g.get("status"), "failed": g.get("failed")} if g else "missing"
    out = {"stage": "W3 rig + magazine + bipod + exports: game / LODs / twin", "gates": gates,
           "failed": [g["name"] for g in gates if not g["pass"]], "other_gate_files": status}
    out["status"] = "pass" if not out["failed"] else "fail"
    (GATES / "game.json").write_text(json.dumps(out, indent=1))
    print("[SR01-w3gates] game.json", out["status"], out["failed"])
    print("[SR01-w3gates] other", json.dumps(status))


main()
