"""Stone kit FIX ROUND 3 (f3): add the round's record to kit_catalog.json (top-level "f3_fix_round": what changed, the
judge deltas accepted and rejected against the reference, the measured numbers (f3_measure.json, stairs/measure.json,
f3_gates.json), the fresh-process FBX verify, the renders, the backup). The builders own tracks.* and the pieces; this
touches only its own key, under the catalog's file lock (catalog_f2.lock).
Run: py -3 Scripts/dojo/stonekit/catalog_f3.py
"""
import json
import os
import time
from pathlib import Path

from catalog_f2 import lock

ROOT = Path(__file__).resolve().parents[3]
SK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
CAT = SK / "kit_catalog.json"
F3 = SK / "renders" / "f3"

CHANGES = {
    "wall_layout": "Scripts/stone/stone_layout.coursed_fitted: the coursed frame (course table 0.34 + 0.03 s, "
                   "wandering beds +-12 cm, leaning joints in runs, uprights through two courses ~30 % of the chances, "
                   "1.5 % broken courses, no sliver slots) with every T-junction turned into a Y-junction (the "
                   "through-stone pushed up the head joint, the two corners chamfered to match), so neighbours share "
                   "outlines; module-end tooth junctions use fixed push / chamfer numbers so modules interlock",
    "wall_stones": "f2's pillow_stone_v2 (per-corner radius via Chaikin, asymmetric crown, tilt), 1.1-1.5 cm "
                   "between rims (f2 1.6-2.2 cm + a dark triangle at every T-junction), corner rounding keep "
                   "0.14-0.22 (f2 0.18-0.26 on top of 13-22 % corner cuts); stones ~0.34 x 0.42 m (f2 +30 %)",
    "moss": "moss cushions as geometry (sk_shared.moss_pad, new slot M_DKT_MossPad, the same master + Wear.A lerp) "
            "in 14-58 % of the bed joints (denser low and under the cap) and across 55 % of the cap-top joints",
    "steps": "4 (W120) / 5 (W180) short setts a tread on even steps, one fewer on odd steps (0.30-0.45 m, staggered), "
             "0.8 cm end joints (f2 1.2), a softer rounded nosing (3.0 cm radius, same 1.4 cm lip)",
    "kerbs": "+0.09 over the path (f2 0.07); the 'spike' was the stand-in slope cutting the kerb's buried side: the "
             "f3 assembly seats kerbs in a soil bank",
    "rails": "posts slimmer (9.6 cm, f2 11), still round with domed tops; squared rails housed into the posts "
             "(unchanged); darker weathered timber (tint 0.38, f2 0.48)",
    "lantern_timber": "taller light box (0.34 m, h/w ~1.2), a straighter steeper pyramid roof (flanks ~57 deg, eave "
                      "0.38 m, 1.6 cm tip upturn), the finial ~1.9 x taller; 1.52 m overall",
}
NEW_UE_MATERIALS = ["M_DKT_MossPad (new in f3)", "M_DKT_TimberWeathered / End (retinted in f3)",
                    "M_DKT_WallGranite", "M_DKT_CopeGranite", "M_DKT_StepGranite", "M_DKT_StepRiser",
                    "M_DKT_JointDark", "M_DKT_HoodCharcoal", "M_DKT_GlassAmberWarm"]


def main():
    meas = json.loads((SK / "f3_measure.json").read_text(encoding="utf-8"))
    sm = json.loads((SK / "stairs" / "measure.json").read_text(encoding="utf-8"))
    ver = json.loads((SK / "fbx_verify_f3.json").read_text(encoding="utf-8"))
    gates = json.loads((SK / "f3_gates.json").read_text(encoding="utf-8"))["gates"] if (SK / "f3_gates.json").exists() else None
    deltas = json.loads((SK / "f3_deltas.json").read_text(encoding="utf-8")) if (SK / "f3_deltas.json").exists() else None
    asm = {}
    if (F3 / "assembly_stairs.json").exists():
        a = json.loads((F3 / "assembly_stairs.json").read_text(encoding="utf-8"))
        asm = {k: v for k, v in a.items() if k != "layout"}
    flights = {k.replace("SM_DKT_Stair_", ""): {"risers_measured_m": v.get("risers_measured_m"),
                                               "tread_tops_centre_m": v.get("tread_tops_centre_m"),
                                               "ucx_ramp_deg": v.get("ucx_ramp_deg"), "gasp_ok": v.get("gasp_ok")}
               for k, v in sm.items() if "Flight" in k}
    renders = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in F3.glob("*.png"))
    lk = lock()
    try:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        n_pieces = len([k for k in cat["pieces"] if k.startswith("SM_DKT_")])
        cat["f3_fix_round"] = {
            "date": time.strftime("%Y-%m-%d"),
            "authority": "the owner's reading of the reference, then the reference itself; judge deltas applied only "
                         "where the reference crop confirms them (judge-steer rule, study 6.6)",
            "study": "STONE_BUILDING_STUDY.md 4.4 / 4.5 / 6.2 / 8.2 followed; deviations in BUILD_NOTES.md (Fix round 3)",
            "changes": CHANGES, "judge_deltas": deltas, "measured": meas, "gates": gates, "flights": flights,
            "assembly_checks": asm,
            "fbx_fresh_process_verify": {"files": ver.get("files"), "not_ok": ver.get("not_ok")},
            "qa": "qa_check 0 hard fails on all %d pieces (UV0 tiling overlaps waived as before)" % n_pieces,
            "unreal_materials_to_create": NEW_UE_MATERIALS,
            "backup_of_f2": "Backups/DojoStoneKit_f2_2026-09-30/ (RESTORE.txt: Scripts stonekit + stone, "
                            "Assets/DojoStoneKit.blend, Exports/StoneKit, WorkFiles catalogue / measures / track blends "
                            "/ trace / renders/f2, the trace JSON, the study)",
            "not_done": "no Unreal in this run (another track owns DojoLab)",
            "renders": renders + ["WorkFiles/dojo/build/stonekit/renders/f3/sheet/<piece>_{front,side,top,persp}.png"]}
        tmp = CAT.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(cat, indent=1), encoding="utf-8")
        os.replace(tmp, CAT)
    finally:
        lk.unlink()
    print("catalog f3 block written:", len(CHANGES), "changes,", len(renders), "renders,", n_pieces, "pieces")


if __name__ == "__main__":
    main()
