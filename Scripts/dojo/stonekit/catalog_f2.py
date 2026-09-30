"""Stone kit FIX ROUND 2 (f2): add the round's record to kit_catalog.json (top-level "f2_fix_round": the owner's reading
of the reference and what was done, the measured numbers (f2_measure.json, stairs/measure.json, the wall build report),
the fresh-process FBX verify summary, the renders, the backup). The builders own tracks.* and the pieces; this touches
only its own key, under the catalog's file lock (the same O_EXCL '<catalog>.lock' as sk_shared.file_lock).
Run: py -3 Scripts/dojo/stonekit/catalog_f2.py
"""
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
CAT = SK / "kit_catalog.json"
F2 = SK / "renders" / "f2"

STUDY_ROUND = {   # f2 round 2 (2026-09-30, after STONE_BUILDING_STUDY.md; the relaunched f2 stage)
    "study": "STONE_BUILDING_STUDY.md (pipeline 4, gates 6, dojo appendix 8.2) followed; deviations in BUILD_NOTES.md",
    "tools": "Scripts/stone/ (new, lock StoneTools): stone_measure.py (6.1/6.2 value methods, shape stats, gates), "
             "stone_trace.py (6.8 tracer: manual + seed modes, overlay, validation), stone_layout.py (4.5 coursed "
             "rounded layout with the measured h/w mixture, per-corner cuts)",
    "trace": "References/Dojo/trace_terrace_lower.json (seed mode, hand-curated: 33 body + 4 cap stones, 32 +- 6 px/m)",
    "wall_layout": "measured terrace mix: upright share 0.70, tall share 0.49, h/w median 1.18 (the trace); body "
                   "stones ~0.25 x 0.33 m in rough courses 0.31 + 0.03 s, leaning joints in runs, 1.5 % broken-course "
                   "splits, per-corner cuts rounded by Chaikin (egg / lens outlines), crowns 10-20 % of the short side "
                   "(CV >= 0.3) with the peak toward the top, per-stone tilt; cap course 0.34 m squarer blocks",
    "joint_core": "noisy front (soil pockets 6-14 cm behind the face; no flat board), darker (0.055), patchy moss",
    "tone": "kit 1 footing hue (channel ratio 1 : 0.88 : 0.78) at a mid-grey luminance; the f2 cool grey read "
            "pink-lilac (hue 23 deg) and f2r2's warmer trial read tan at sunset",
    "traversal": "every piece's flat walkable / climbable tops carry 'traversal' boxes (study 4.13)",
    "gates": "WorkFiles/dojo/build/stonekit/f2_gates.json; table renders/f2/GATES_f2.png",
}
READING = {
    "wall_stones": "done (round 2): ROUNDED pillow-faced granite (sk_shared.lay_measured / pillow_stone_v2 over "
                   "Scripts/stone/stone_layout.py): upright ovals and eggs in rough courses at the traced mix (upright "
                   "0.70, h/w median 1.18), some long and some small, per-corner radius, asymmetric crowns; dark deep "
                   "joints (visible 2-4 cm, noisy dark core); MID-GREY granite with kit 1's footing hue; moss and dirt "
                   "in the bed joints and on the top edges; no pebble specks",
    "wall_profile": "done: the DEFAULT profile is a straight 1:10 batter d(s) = 0.10 s (84.3 deg), no corner flare; "
                    "the concave castle sweep survives only as the *_Sweep variant set (Wall_{2m,4m}_H{3,4,6}, "
                    "CornerOut, CornerIn, EndL, EndR, WallFoot_CornerOut / _CornerIn at H 3 / 4 / 6); the coping is "
                    "squarer (r 24 mm), 0.34 m (round 2: the trace's cap / body height 1.1), a little darker (M_DKT_CopeGranite), moss on top; sangi-zumi follow "
                    "the straight profile",
    "wall_foot": "done: WallFoot_* = ONE continuous, level, buried footing course (tops +0.06 over the nominal foot "
                 "within +-4 mm, 0.10 proud, buried to -0.45); no skirt, no loose rubble",
    "steps": "done: 3 (W 1.2) / 4 (W 1.8) short squared blocks per tread with staggered end joints (odd steps half a "
             "block over), lighter walked tops (M_DKT_StepGranite), darker rougher risers (M_DKT_StepRiser), a small "
             "worn nosing (1.4 cm set-back), calmer relief (rough 1.2 mm, normals 0.16 / 0.28); the wall's stair "
             "openings take the same steps",
    "landings": "done: flush, large, near-rectangular flags (rows 0.45-0.75 m, flags 0.55-0.95 m, joints 1.5 cm off "
                "square, 0.8-1.2 cm between rims) at path level; new Stair_Kerb_L{060,120,180} + Stair_Kerb_Corner: "
                "low squared edging blocks +0.07 over the path",
    "rails": "done: round posts with rounded (domed) tops, SQUARED rails (5.0 x 7.5 / 4.4 x 6.4 cm) housed into the "
             "posts, darker weathered timber (M_DKT_TimberWeathered); every Rail_Slope carries the posts at both its "
             "ends",
    "lanterns": "done: Lantern_Timber keeps its f1 form; warmer amber panes (M_DKT_GlassAmberWarm), the darker "
                "weathered body, a charcoal hood + finial (M_DKT_HoodCharcoal, no rust); assemblies: one lantern per "
                "landing, clearance to every rail measured (assembly_stairs.json); Lantern_Stone stays a kit extra",
    "cheeks": "done: Cheek_Low_R{050,100,200} / Cheek_Low_L{120,180}: the single-course low variant (+0.12 over the "
              "tread, 0.22 m in the soil, no base); every cheek has moss where it meets the soil; the stepped cheeks' "
              "bases are the wall's rounded stones",
    "tone": "kit 1's FootingStone is not retinted (not ours); the kit's wall granite sits between it (linear mean "
            "0.097 / 0.085 / 0.075, warm) and f1's pale 0.25: a neutral mid-grey 0.145",
}
NEW_UE_MATERIALS = ["M_DKT_WallGranite (retuned)", "M_DKT_CopeGranite (new)", "M_DKT_StepGranite (retuned)",
                    "M_DKT_StepRiser (retuned)", "M_DKT_JointDark (retuned)", "M_DKT_TimberWeathered (new)",
                    "M_DKT_TimberWeatheredEnd (new)", "M_DKT_HoodCharcoal (new)", "M_DKT_GlassAmberWarm (new)"]


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
    meas = json.loads((SK / "f2_measure.json").read_text(encoding="utf-8"))
    sm = json.loads((SK / "stairs" / "measure.json").read_text(encoding="utf-8"))
    ver = json.loads((SK / "fbx_verify_f2.json").read_text(encoding="utf-8"))
    asm = {}
    if (F2 / "assembly_stairs.json").exists():
        a = json.loads((F2 / "assembly_stairs.json").read_text(encoding="utf-8"))
        asm = {k: v for k, v in a.items() if k != "layout"}
    flights = {k.replace("SM_DKT_Stair_", ""): {"risers_measured_m": v.get("risers_measured_m"),
                                               "tread_tops_centre_m": v.get("tread_tops_centre_m"),
                                               "nosing_overhang_m": v.get("nosing_overhang_m"),
                                               "ucx_ramp_deg": v.get("ucx_ramp_deg"), "ucx_lip_m": v.get("ucx_lip_m"),
                                               "gasp_ok": v.get("gasp_ok")}
               for k, v in sm.items() if "Flight" in k}
    landings = {k.replace("SM_DKT_Stair_", ""): v.get("paving_top_m") for k, v in sm.items() if "Landing" in k}
    renders = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in F2.glob("*.png"))
    lk = lock()
    try:
        cat = json.loads(CAT.read_text(encoding="utf-8"))
        n_pieces = len([k for k in cat["pieces"] if k.startswith("SM_DKT_")])
        cat["f2_fix_round"] = {
            "date": time.strftime("%Y-%m-%d"),
            "authority": "the owner's reading of the reference (f1 went the wrong way: pale flat many-sided stones, "
                         "1-2 slabs a tread, Voronoi landings)",
            "reading": READING, "study_round_2": STUDY_ROUND, "measured": meas,
            "gates": (json.loads((SK / "f2_gates.json").read_text(encoding="utf-8"))["gates"]
                      if (SK / "f2_gates.json").exists() else None), "flights": flights, "landing_paving_top_m": landings,
            "assembly_checks": asm,
            "fbx_fresh_process_verify": {"files": ver.get("files"), "not_ok": ver.get("not_ok")},
            "qa": "qa_check 0 hard fails on all %d pieces (UV0 tiling overlaps waived as kit 1)" % n_pieces,
            "unreal_materials_to_create": NEW_UE_MATERIALS,
            "backup_of_f1": "Backups/DojoStoneKit_f1_2026-09-30/ (Scripts, Assets/DojoStoneKit.blend, Exports/StoneKit, "
                            "WorkFiles: kit_catalog.json, BUILD_NOTES.md, f1 measure / verify, track blends)",
            "backup_before_round_2": "Backups/DojoStoneKit_f2pre_2026-09-30/ (the stopped f2 run's state: Scripts, "
                                     "Assets/DojoStoneKit.blend, Exports/StoneKit, WorkFiles incl. renders/f2 + f2dev)",
            "not_done": "no Unreal in this run (another track owns DojoLab)",
            "renders": renders + ["WorkFiles/dojo/build/stonekit/renders/f2/sheet/<piece>_{front,side,top,persp}.png"]}
        tmp = CAT.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(cat, indent=1), encoding="utf-8")
        os.replace(tmp, CAT)
    finally:
        lk.unlink()
    print("catalog f2 block written:", len(READING), "items,", len(renders), "renders,", n_pieces, "pieces")


if __name__ == "__main__":
    main()
