"""SR01 W4: gates/review_fixes.json (the SMG's layout): the Part A items (W3 leftovers) and every review finding (craft,
tech, realism, blind) with its verdict (FIXED / PARTIAL / DEFERRED / REJECTED / DECLARED), the fix and the evidence
read from the regated files, plus the stage files' status after the fix round and the judges before / after.

    py -3 -B Scripts/guns/sniper/sr_review_fixes.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import GATES, WORK  # noqa: E402

J = WORK / "review" / "w4" / "judges"
JF = WORK / "review" / "w4fix" / "judges"


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def gate(fname, prefix):
    d = load(GATES / fname) or {}
    for g in d.get("gates", []):
        if g["name"].startswith(prefix):
            return {"value": g["value"], "pass": g["pass"]}
    return None


def part_iou(name):
    d = load(GATES / "form.json") or {}
    for g in d.get("gates", []):
        if g["name"].startswith("L2 per part on GR"):
            v = g["value"]
            return v.get(name) if isinstance(v, dict) else None
    return None


def paint(key):
    d = load(GATES / "uv_bake_paint.json") or {}
    return json.dumps(d).count(key) and key


def verdicts(d):
    if not d:
        return None
    return {"overall": d.get("overall"), "images": {k: v.get("verdict") for k, v in d.get("images", {}).items()}}


def blind_score(jd, keyf):
    if not jd:
        return None
    key = load(keyf)["pairs"]
    hits = sum(1 for k, v in jd["pairs"].items() if v.get("copy") == key[k]["ours"])
    return {"pairs": len(jd["pairs"]), "copy_identified": hits,
            "basis": {b: sum(1 for v in jd["pairs"].values() if v.get("basis") == b) for b in ("design", "style only", "guess")}}


def main():
    I = []

    def item(id_, source, area, severity, verdict, fix, evidence=None):
        I.append({"id": id_, "source": source, "area": area, "severity": severity, "verdict": verdict, "fix": fix,
                  "evidence": evidence or {}})
    # ---------------------------------------------------------------- Part A (W3 leftovers)
    item("A1", "W3", "Magazine catch (M2 0.87 / M3 1.45 / M4 ride)", "major", "FIXED",
         "sniper_parts: the spring-catch hook (flat bearing top Z -47.5, nose X 415.75, 41 deg ramp underside), notch 2.2 "
         "deep, magazine body top -21.2 (the shelf is the stop at 1.5) and lips + top round +0.5 (round to bolt 1.82); "
         "M4 in gunlib's catch_spring mode (the SMG's real-pattern rule). Proven first on the form blend "
         "(sr_catch_probe.py), then the full chain", {
             "M2": gate("mag.json", "M2"), "M3": gate("mag.json", "M3"), "M4": gate("mag.json", "M4 "),
             "M4b": gate("mag.json", "M4b"), "M5": gate("mag.json", "M5 "), "F5": gate("mag.json", "F5")})
    item("A2", "W3", "Scope LOD2: FBX dropped 2 coincident faces", "minor", "FIXED",
         "sr_lodlib.drop_coincident_pairs after the joined LOD's weld (back-to-back internal walls of touching parts go "
         "in pairs) and on any fin a decimated part keeps; the check is unchanged",
         {"scope LOD triangles build = FBX": gate("scope_export.json", "re-imported LOD triangles"),
          "SK LOD triangles": gate("rig_export.json", "LOD triangles Blender = FBX (SK)")})
    item("A3", "W3", "LOD2 switching late (25.6 m)", "major", "FIXED",
         "sr_game: silhouette-weighted LOD ratios (hidden pins / screws / swivel / bolt at 0.4 x at LOD2, 0.3 x at LOD3) and "
         "silhouette parts never dropped (W3 dropped pad_plate at LOD2: the 2.9 px pop at the butt). LOD2 15.1 m, LOD3 "
         "30.1 m (were 25.6 / 45.8); relative to size LOD2 now switches earlier than the SMG's (s 0.066 vs 0.053)",
         {"game_lod_sizes": load(GATES / "game_lod_sizes.json")})
    item("A3b", "W4", "Hull UCX_SM_SR01_LOD0_01 (cheek riser) diverged to 1e16 m (W4 LOD change)", "blocker", "FIXED",
         "sr_game.valid_hull: every hull checked (outward faces, box, containment); a failed gunlib hull is rebuilt by "
         "sr_lodlib.hull_safe (same method, 1 um dedup, normals recalculated after every hull step)",
         {"C1": gate("game.json", "C1")})
    item("A4", "W3", "Magazine LOD0 878 triangles (target 2-3k)", "minor", "DECLARED",
         "not raised: the body sits in the well; the visible lower body + floorplate already carry the chamfers and pressed "
         "ribs as geometry; more triangles would not change the close read (A4 of the run brief)")
    item("A5", "W3", "Re-export + fresh-process verify + regate", "-", "FIXED", "run_rig_mag.sh on the fix-round blend",
         {f: (load(GATES / f"{f}.json") or {}).get("status") for f in ("game", "rig_export", "mag", "scope_export")})
    # ---------------------------------------------------------------- craft
    item("C1", "craft + both realism judges", "Scope anodize reads as polished chrome", "major", "FIXED",
         "sr_surface FIN scope_anod rough 0.24-0.34 -> 0.46-0.56 (study type III 0.45-0.65)")
    item("C2", "craft", "Trigger guard open at the bottom (sheet: closed loop)", "major", "FIXED",
         "sniper_parts.chassis: the bottom bar X 336.5-399.5 from the arms' lowest point to the opening floor, sides at "
         "Y +-8.6 (0.4 inside the arms: the coplanar / short variants left 1-10 UD1 slivers)",
         {"trigger_guard GR IoU": part_iou("trigger_guard"), "B3 trigger": "form.json B3 (0 intersections)",
          "F9": "form.json F9"})
    for cid, area in (("C3", "Traced outline noise (forend nose sawtooth, butt-pad notches, mag-well facets)"),
                      ("C4", "Pistol grip: flat stepped extrusion, toe spur, no draft / parting line"),
                      ("C5", "Chassis / butt / riser: no readable chamfer highlights"),
                      ("C6", "Wear and grime effectively invisible")):
        item(cid, "craft (+ realism)", area, "major", "DEFERRED",
             "W4b close-up realism pass: generator-level (C3 line / arc fit of the trace before extrusion, C4 lofted "
             "grip, C5 chassis edge bevels with the UD repair) and paint (C6 chips / grime); each is a method change "
             "with its own gate run, larger than this fix round")
    item("C7", "craft", "Barrel flutes narrow / short vs the sheet", "minor", "DEFERRED",
         "W4b: measure the flute width / ends on GR / Q34 first (spec flutes.X is the traced authority)")
    item("C8", "craft + both realism judges", "Bolt reads as mirror chrome; identical bright ring on every turret cap",
         "minor", "FIXED", "FIN bolt_polish lin 0.42-0.46 / rough 0.32-0.44 (was 0.50-0.54 / 0.24-0.36), leg_polish "
         "rough 0.24-0.34; scope cap wear rarer (dash > 0.93)")
    item("C9", "craft", "Release pin end half in air on the outline", "minor", "FIXED",
         "the pin ends inside the cheeks (Y +-8.0) and its bore stops at +-8.1: hidden (a 0.3 mm boss was tried first: "
         "1 UD1 sliver)")
    item("C10", "craft", "Butt side discs read as flat stickers", "minor", "DEFERRED", "W4b: size vs GR, edge + recess")
    item("C11", "craft", "White specks on the rail / receiver flat", "minor", "DEFERRED",
         "W4b wear pass (rail teeth wear specks; the S / F marking stays)")
    item("C12", "craft", "OD washes to grey-sage under the 3/4 key", "minor", "DEFERRED",
         "W4b: L5 is calibrated on GR; a Q34 crop match is added there")
    item("C13", "craft + both realism judges", "Scope eyepiece / bell rims faceted; trigger blade kinks", "minor",
         "PARTIAL", "scope body revolve 36 -> 64 sides (scope LOD0 now inside the 6-10k target); trigger blade: W4b",
         {"scope LOD triangles": gate("scope_export.json", "re-imported LOD triangles")})
    # ---------------------------------------------------------------- tech
    item("T1", "tech", "No README / MATERIALS_README", "major", "PARTIAL",
         "Exports/Guns/SR01/README.md written (pre-Unreal: contents, LOD sizes, sockets, colour spaces); the Unreal "
         "import notes come with W5, MATERIALS_README + recolour_constants with the pack (W6)")
    item("T2", "tech", "No Unreal import gate", "major", "DEFERRED", "W5 (out of scope for W4)")
    item("T3", "tech", "Stale declared list in uv_bake_paint.json", "major", "FIXED",
         "sr_w2_gates declared list: UD2 / UD3 resolved in W3, S / F delivered (109 texels), B9 still open")
    item("T4", "tech", "Triangles under target floors", "minor", "PARTIAL",
         "scope now in target (C13); gun 34-35k declared (A5 of the plan: 35k floor is the twin with the magazine); mag A4")
    item("T5", "tech", "UV1 collapsed on LODs", "minor", "DEFERRED", "W5 U8 lightmap check in engine")
    item("T6", "tech", "PNGs carry no colour-space tags", "minor", "FIXED", "README states BC sRGB, ORM / N / Masks linear")
    item("T7", "tech", "Mag hull name", "minor", "REJECTED",
         "the shipped hull is UCX_SM_SR01_Mag_LOD0_00 (blend + mag.json); the rule is met")
    item("T8", "tech", "SK_AR01_Skeleton compatibility untested", "minor", "DEFERRED", "W5")
    item("T9", "tech", "Mag vs gun LOD2/3 intersections", "minor", "REJECTED",
         "the M1 rule: < 1 px at the switch distance outside the LOD0 well (gate passes)")
    item("T10", "tech", "FBX absolute source path", "minor", "DEFERRED", "W5 / W6 pack check")
    # ---------------------------------------------------------------- realism wants -> W4b
    ra, rb = load(J / "realism_A.json"), load(J / "realism_B.json")
    item("R", "realism A + B", "Both judges: fake on 5 / 5 views (before the fix round)", "-", "W4b",
         "their priorities are the W4b list (FIX_LOG.md)", {"A": (ra or {}).get("priorities"), "B": (rb or {}).get("priorities")})
    # ---------------------------------------------------------------- stage files + judges
    stages = {f: {"status": (load(GATES / f"{f}.json") or {}).get("status"),
                  "failed": (load(GATES / f"{f}.json") or {}).get("failed")}
              for f in ("form", "scope_form", "uv_bake_paint", "game", "rig_export", "mag", "scope_export")}
    judges = {"before": {"realism_A": verdicts(ra), "realism_B": verdicts(rb),
                         "blind": blind_score(load(J / "blind.json"), WORK / "review" / "w4" / "blind_key.json")},
              "after": {"realism_A": verdicts(load(JF / "realism_A.json")),
                        "realism_B": verdicts(load(JF / "realism_B.json"))}}
    counts = {v: sum(1 for i in I if i["verdict"] == v) for v in ("FIXED", "PARTIAL", "DEFERRED", "REJECTED", "DECLARED")}
    out = {"stage": "W4 review fixes (SR01_BUILD_PLAN 9 row W4)", "date": dt.datetime.now().isoformat(timespec="seconds"),
           "stage_files": stages, "judges": judges, "counts": dict(items=len(I), **counts), "items": I}
    (GATES / "review_fixes.json").write_text(json.dumps(out, indent=1, default=str))
    print("[review_fixes] written", json.dumps(out["counts"]), json.dumps(judges["before"]["blind"]))


if __name__ == "__main__":
    main()
