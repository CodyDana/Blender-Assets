"""Stone kit FIX ROUND 1: add the round's record to kit_catalog.json (top-level "f1_fix_round": the judge's deltas and
what was done, the measured numbers from f1_measure.json / stairs measure.json, the fresh-process FBX verify summary,
the renders). The builders own tracks.* and the pieces; this touches only its own key, under the catalog's file lock
(the same O_EXCL '<catalog>.lock' as sk_shared.file_lock).
Run: py -3 Scripts/dojo/stonekit/catalog_f1.py
"""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
CAT = SK / "kit_catalog.json"
F1 = SK / "renders" / "f1"

DELTAS = {
    "1_wall_stone_shape": "done: irregular 5-7 sided polygon stones nested course to course with diagonal joints "
                          "(sk_shared.lay_courses), flat dressed faces with 8-13 mm arrises and +-2 deg tilt "
                          "(sk_shared.dressed_stone), no packing chips; joint core = M_DKT_JointDark (no pebble specks)",
    "2_stone_material": "done: kit granite family sk_shared.KIT_MATS (pale grey-beige, warmth from the light), per-stone "
                        "tone + light tops + dark undersides in the Wear colours (stone_tone), moss only in joints / on "
                        "ledges, box-projected UVs (no flank stretch), calmer normals and relief",
    "3_steps": "done: 4.0 cm riser set-back under a rounded worn nosing (measured overhang median 2.6 cm), treads "
               "M_DKT_StepGranite (light, smooth), risers / ends M_DKT_StepRiser (darker, rougher), 1-2 slabs a step "
               "(also the wall's stair openings)",
    "4_flight_sides": "done: wall-granite polygon courses under the slabs' sloped common underside, dark core behind",
    "5_landings": "done: flush Voronoi flags (0.45-0.9 m) to the edges, joints ~1.0-1.2 cm, flat tops, no curbs; a low "
                  "course of side stones under the flags",
    "6_lantern": "done: shaft 0.176 m (was 0.244; measured with frames 0.186 vs 0.26), splayed legs under a flared "
                 "skirt, frame panels, steep pointed roof (rise 0.27) with curved upturned eaves, tall bulb finial; "
                 "assembly placements one per landing, >= 0.5 m clear of every rail line",
    "7_rails": "done: round poles (dia 6.8 / 5.6 cm) let through round posts with domed tops, posts 0.86 m (was 0.94), "
               "no bosses; every Rail_Slope carries the posts at BOTH its ends; Rail_Flat_* are poles only",
    "8_wall_foot_skirt": "done: sparse (~40 %) flat angular slabs mostly buried (tops 2-7 cm above grade), one row",
    "9_corners": "done: CornerIn_H6 takes 3 m arms (face fully laid to the foot); the outside-corner flare is gentler "
                 "(0.005 s^2 over 1.4 m), sangi-zumi blocks move rigidly, face stones only along their own normal, the "
                 "core never follows the flare (no curled sheet)",
    "10_cheeks": "done: LOW cheeks: one dressed through-stone per tread standing +0.15 m over it (flat +0.15 on landing "
                 "sides) on a buried wall-granite base",
    "11_stone_lantern": "kept as a kit extra; not used in the reference-matching assemblies",
    "12_opening_rails": "the wall-face flight is not railed in the assemblies (the rail snaps stay, optional)",
}


def lock():
    lk = Path(str(CAT) + ".lock")
    t0 = time.time()
    while True:
        try:
            fd = os.open(str(lk), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}".encode())
            os.close(fd)
            return lk
        except FileExistsError:
            if time.time() - t0 > 120:
                raise
            time.sleep(0.5)


def main():
    meas = json.loads((SK / "f1_measure.json").read_text(encoding="utf-8"))
    sm = json.loads((SK / "stairs" / "measure.json").read_text(encoding="utf-8"))
    ver = json.loads((SK / "fbx_verify_f1.json").read_text(encoding="utf-8"))
    flights = {k.replace("SM_DKT_Stair_", ""): {"nosing_overhang_m": v.get("nosing_overhang_m"),
                                               "risers_measured_m": v.get("risers_measured_m"),
                                               "ucx_ramp_deg": v.get("ucx_ramp_deg"), "gasp_ok": v.get("gasp_ok")}
               for k, v in sm.items() if "Flight" in k}
    landings = {k.replace("SM_DKT_Stair_", ""): v.get("paving_top_m") for k, v in sm.items() if "Landing" in k}
    renders = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in F1.glob("*.png"))
    lk = lock()
    try:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        cat["f1_fix_round"] = {
            "date": time.strftime("%Y-%m-%d"), "judge": "6/10 blockers + 12 deltas (both tracks)",
            "deltas": DELTAS, "measured": meas, "flights": flights, "landing_paving_top_m": landings,
            "fbx_fresh_process_verify": {"files": ver.get("files"), "not_ok": ver.get("not_ok")},
            "qa": "qa_check 0 hard fails on all 71 pieces (UV0 tiling overlaps waived as kit 1); Nanite pieces "
                  "ship without UV1 (Lumen) on both tracks",
            "not_done": "no Unreal in this run (DojoLab owned by the round 8 sky workflow)",
            "renders": renders + ["WorkFiles/dojo/build/stonekit/renders/f1/sheet/<piece>_{front,side,top,persp}.png"]}
        tmp = CAT.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(cat, indent=1), encoding="utf-8")
        os.replace(tmp, CAT)
    finally:
        lk.unlink()
    print("catalog f1 block written:", len(DELTAS), "deltas,", len(renders), "renders")


if __name__ == "__main__":
    main()
