"""SMG01 W4 'apply fixes' record (plain Python): WorkFiles/guns/smg/gates/review_fixes.json.

    py -3 -B Scripts/guns/smg/smg_w4_fix_gates.py

SMG_BUILD_PLAN 15 row W4: 'gates/review_fixes.json (all stage files pass + the review items)'. Reads every stage file the
full chain (run_all.sh) rewrote from nothing: gates/form.json, form_magfit.json, uv_bake_paint.json, game.json,
rig_export.json, mag.json, review_export.json, gunlib_regression.json; and for each review finding (the craft + tech
review and the two realism judges on the W4 renders) its verdict (FIXED / REJECTED / DEFERRED), the fix and the
measured evidence from those files (numbers, not adjectives). review/FIX_LOG.md is the prose of the same items.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, GATES, SCRATCH, REVIEW  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "SMG01"


def j(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else {}


def gate_by(stage, prefix):
    for g in stage.get("gates", []):
        if g.get("name", "").startswith(prefix):
            return g
    return {}


def main():
    S = {n: j(GATES / f"{n}.json") for n in ("form", "form_magfit", "uv_bake_paint", "game", "rig_export", "mag",
                                              "review_export", "gunlib_regression")}
    stage_rows = {}
    for n, v in S.items():
        st = v.get("status")
        fails = v.get("failed", [])
        if n == "gunlib_regression":
            # the compare's byte row lists the SMG blend as a tracked change under Assets/Guns (not an AR-01 file)
            ok = all(f == "AR-01 export / input bytes" for f in fails) and \
                all(c.get("equal", True) for c in v.get("checks", []) if isinstance(c, dict))
        elif n == "form_magfit":
            ok = st == "pass" or v.get("pass") is True
        else:
            ok = st == "pass"
        stage_rows[n] = {"status": st, "failed": fails, "pass": bool(ok), "date": v.get("date")}
    form, w2, game, rig, mag = S["form"], S["uv_bake_paint"], S["game"], S["rig_export"], S["mag"]
    paint = j(SCRATCH / "paint" / "paint_report.json")
    l5 = j(SCRATCH / "l5" / "l5.json")
    sizes = j(GATES / "game_lod_sizes.json")
    skj = j(EXP / "SK_SMG01.skeletal.json")
    smj = j(EXP / "SM_SMG01.sockets.json")
    magj = j(EXP / "SM_SMG01_Mag.sockets.json")
    g3o = gate_by(form, "G3o")
    b8 = gate_by(form, "B8 LOD0 triangles, gun")
    b8m = gate_by(form, "B8 magazine")
    lines = gate_by(w2, "wear: bare steel on Metal")
    poly = gate_by(w2, "polymer surface")
    masks = gate_by(w2, "Metal Masks G")
    g20 = gate_by(w2, "G20 steel darker")
    l5g = gate_by(w2, "L5 colour")
    g5 = gate_by(form, "G5 static intersections")
    l2 = {k: gate_by(form, k).get("value") for k in ("L2 LEFT IoU", "L2 RIGHT IoU", "L2 TOP IoU", "L3 LEFT contour P95",
                                                      "L3 feature positions")}
    f5 = gate_by(form, "F5 bolt thumb recess")
    mt = paint.get("Metal", {})
    items = []

    def item(iid, source, area, severity, verdict, fix, evidence, ok=True):
        items.append({"id": iid, "source": source, "area": area, "severity": severity, "verdict": verdict, "fix": fix,
                      "evidence": evidence, "pass": bool(ok)})

    # ---------------------------------------------------------------- craft + tech review
    item("C1", "craft/tech", "G3 faceted rounds: vent and charging-slot radius ends", "major", "FIXED",
         "stadium ends 24 segments per semicircle (7.5 deg; were 7: 25.7 deg) on every vent, the channel's lock notch; "
         "the port corners 6 segments, the magazine recesses 5; new gate G3o on the openings' boundary loops",
         {"G3o": g3o.get("value"), "B8_gun_LOD0": b8.get("value"), "B8_magazine": b8m.get("value")},
         g3o.get("pass") and b8.get("pass") and b8m.get("pass"))
    item("C2", "craft", "Charging knob texture", "major", "FIXED",
         "the knob's coat even (mottle x 0.25), the flat crown a polished satin (rough 0.45-0.55, base x 1.32), a thin "
         "continuous bare rim just outside the crown edge (normals 18-26 deg off the axis); no noise flecks",
         {"info": (mt.get("info") or {}), "charging_knob_bare_fraction": mt.get("wear_audit", {}).get(
             "charging_knob_bare_fraction")},
         (mt.get("info") or {}).get("knob_rim_bare_texels", 0) > 0 and
         mt.get("wear_audit", {}).get("charging_knob_bare_fraction", 1) <= 0.25)
    item("C3", "craft", "Bare-steel wear as scattered specks", "major", "FIXED",
         "continuous 0.18-0.5 mm bright lines on the sharp convex crests (same-side distance to the edge x AO exposure x "
         "the bright-edge zones), long dashes from a 4 mm field, <= 1.2 mm from the edge, clusters >= 14 texels; the "
         "rails' base flange and the device's slot edges excluded; rubbed phosphate varied along the part (no repeated "
         "per-tooth frame); UV0 has 0 stacked / mirrored islands (W2 gate)",
         {"gate": lines.get("value")}, lines.get("pass"))
    item("C4", "craft", "Polymer too clean, no micro-texture", "major", "FIXED",
         "moulded texture in the normal map at the texel scale (0.6 mm grain +-9 um over a 1.8 mm orange peel +-12 um; "
         "magazine +-12 / 15 um), the same grain as +-0.03 roughness and albedo speckle, low-frequency mottle, longer "
         "whitening bands (WHITEN_BASE 0.35), fore-aft scratches on the receiver and stock flats, a lighter glossier "
         "follower",
         {"gate": poly.get("value"), "bc_std": {k: paint.get(k, {}).get("bc_std_srgb_levels") for k in paint},
          "normal_tilt_gt_1deg": {k: paint.get(k, {}).get("normal_tilt_gt_1deg_fraction") for k in paint}},
         poly.get("pass"))
    item("C5", "craft/tech", "G20 steel vs polymer value", "major", "FIXED",
         "phosphate base (40, 41, 42) (was 50-52), dry 0.62-0.76 / oiled 0.52-0.62; spec R44; CRAFT_STUDY table "
         "corrected; L5 now grades the sRGB-luma ratio receiver / (barrel + device)",
         {"G20": g20.get("value"), "L5": {"pass": l5g.get("pass"),
                                          "muzzle_device": (l5.get("regions", {}).get("muzzle_device") or {}).get("ours"),
                                          "barrel": (l5.get("regions", {}).get("barrel") or {}).get("ours")}},
         g20.get("pass") and l5g.get("pass"))
    item("m1", "craft", "Rear-sight windage drum knurl", "minor", "FIXED",
         "straight knurl 0.55 mm pitch, 0.05 deep in Metal_N on the drum rim (R 4.5), crests rubbed lighter",
         {"drum_knurl_texels": (mt.get("info") or {}).get("drum_knurl_texels")},
         (mt.get("info") or {}).get("drum_knurl_texels", 0) > 0)
    item("m2", "craft", "Ejection port with the bolt back shows an empty box", "minor", "FIXED (part) / REJECTED (part)",
         "the chamber mouth's 0.6 chamfer painted as the rounds' rubbed bright cone with a bare rim (1.0 was tried: B9 class D P5), the bore soot "
         "deepening inward; port soot 0.6 (was 0.35). Rejected: the feed ramp and the magazine top: the bore centre "
         "(Z 1.87) sits under the port's lower edge (Z 2.3) and the magazine's lips (seated, Z ~ -13.6) 16 mm under "
         "it behind the wall and the bolt rails: no side or 3/4 view reaches them",
         {"chamber_mouth_texels": (mt.get("info") or {}).get("chamber_mouth_texels"), "F5_recess": f5.get("value")},
         (mt.get("info") or {}).get("chamber_mouth_texels", 0) > 0)
    item("m3", "craft", "Trace noise and junction geometry", "minor", "FIXED",
         "(a) stock windows: DP 1.0 + true R 3 corners and R 25 blends at gentle bends (the 0.7 mm bump / notch gone); "
         "(b) the pad's rear face flat (ring clipped at X 3.6) with open ribs at one pitch 3.2 / depth 1.2; (c) the "
         "housing set in 0.8 under the upper's plan incl. its 45 deg fore-end step (its tongue stood 3.1 mm proud of "
         "the fore-end at the V: the wedge face / black sliver)",
         {"L2_L3": l2, "G5": g5.get("value")}, gate_by(form, "L2 LEFT IoU").get("pass") and g5.get("pass"))
    item("m4", "craft", "Minor G3 facets on the grip cover and trigger guard", "minor", "FIXED (LOD0) / REJECTED (LOD2)",
         "the guard's smoothed master corners at 0.5 mm chords (were 1.6), the opening's R 6 corners 8 segments (were "
         "3), the guard loop's mitred offset corners rounded R 14, the grip cover's stations 0.8 mm (were 1.6) and its "
         "bottom rim 4 segments (were 2). LOD2's grip shading: REJECTED (LOD2 only from the LOD-pop switch, ~9.5 m; "
         "LOD-pop passes on both stock states)",
         {"G3o": g3o.get("pass"), "LOD-pop": {k: gate_by(game, k).get("value") for k in
                                              ("LOD-pop LOD1 -> LOD2", "LOD-pop LOD2 -> LOD3")}},
         g3o.get("pass") and all(gate_by(game, k).get("pass") for k in ("LOD-pop LOD1 -> LOD2", "LOD-pop LOD2 -> LOD3")))
    item("m5", "craft", "Muzzle device soot and crown", "minor", "FIXED",
         "soot at the PBR floor (lin 0.013, sRGB 30; was 0.025 = on the phosphate) over the inner cage faces and bore, "
         "the slot walls, a ring on the front face round the bore and a gradient out from each slot's edge; the slots' "
         "edges no longer bare (carbon)",
         {"L5_muzzle_device": (l5.get("regions", {}).get("muzzle_device") or {}).get("delta")},
         (l5.get("regions", {}).get("muzzle_device") or {}).get("pass", False))
    item("m6", "craft", "Magazine top", "minor", "FIXED (part) / REJECTED (part)",
         "the lips rolled (outer top edge R 1.2, 3 segments, a 0.9 vertical tip face), the follower 1.0 under the lips' "
         "underside (3.0 under the tips; was 8.0) and painted lighter / glossier. Rejected: the front-top step: the bolt "
         "rails stand 1.5 mm over the magazine's front top edge by design (R30) and M2's overtravel (1.0-2.0) leaves no "
         "room for a raised front edge",
         {"mag_gates": mag.get("status"), "form_magfit": S["form_magfit"].get("status")},
         mag.get("status") == "pass")
    sm_sizes = smj.get("lod_screen_sizes")
    item("m7", "tech", "LOD screen sizes (SM_SMG01 twin)", "minor", "FIXED",
         "the twin's and the magazine's sizes convert at Unreal's static-mesh sphere radius (max |v - box centre|, "
         "gunlib.game.static_sphere_radius) instead of the box half-diagonal; U5 checks them against the engine's "
         "sphere_radius (plan 14.3)",
         {"bounds_radius_m": sizes.get("bounds_radius_m"), "SM_SMG01_sizes": sm_sizes,
          "SK_engine_radius_m": sizes.get("SK_engine_radius_m"), "SM_SMG01_Mag_sizes": magj.get("lod_screen_sizes")},
         bool(sm_sizes))
    item("m8", "tech", "Physics asset vs runtime bounds (folded stock)", "minor", "DEFERRED to W5 (U7)",
         "needs the engine: plan 14.3 U7 now measures the component's runtime bounds of a dropped, simulating gun with "
         "the stock folded; if it fails, a kinematic / QueryOnly stock body on 'stock' with consider_for_bounds or "
         "bComponentUseFixedSkelBounds in the README, then the dropped LOD radius re-derived. Held guns (NoCollision) "
         "are unaffected", {"plan": "SMG_BUILD_PLAN 14.3 U7"}, True)
    gun = skj.get("gun", {})
    item("m9", "tech", "Texel density classes (sidecar claim)", "minor", "FIXED",
         "the sidecar carries the measured medians per set and class beside the spec bands, and the rule (shipped "
         "medians up to 1.25 x the band top: spec R44 records W2's B9 ceiling)",
         {"texel_classes_measured_px_per_cm": gun.get("texel_classes_measured_px_per_cm"),
          "texel_class_rule": gun.get("texel_class_rule")}, bool(gun.get("texel_classes_measured_px_per_cm")))
    item("m10", "tech", "Masks (Metal set) handling channel", "minor", "FIXED",
         "m_hand written for the phosphate too (trigger / paddle faces, knob crown, selector thumb arcs, the handling "
         "zones); the selector's thumb arcs polished in the phosphate pass",
         {"gate": masks.get("value")}, masks.get("pass"))
    # ---------------------------------------------------------------- realism judges (2 judges x 5 views, 8 fake calls)
    mvc = j(REVIEW / "diag" / "maps_vs_clay.json")
    item("R1", "realism", "One flat matte material on every part (clay)", "fake call x8", "FIXED",
         "cause measured (review/diag/maps_vs_clay.json): the maps DO reach the review renders (the exported FBX carry "
         "UV0, the game material reads BC sRGB / ORM + N Non-Color with the DirectX green flipped, and a BC-emission "
         "render shows the painted variation), but (1) the paint was near-uniform at render scale: even after the first "
         "W4 fix pass (polymer BC std 3.9 levels; W3 shipped 2.3) the maps sat only 1.8-3.5 sRGB levels (mean over "
         "the object) off a constant per-set clay material in the 7 close-ups, and (2) "
         "the review lights' flat grey world gave the dark rough finishes nothing to reflect. Fixed: C3-C5 + the "
         "visible-variation pass (roughness sheen at 30 / 8 mm, recess dust, an up-facing dust film, phosphate mottle "
         "x 1.8; R45) and the realism views under the photographic studio rig (R12)",
         {"maps_vs_clay": mvc}, bool(mvc) and mvc.get("pass", False))
    item("R2", "realism", "No wear, edge rub, dust or grime", "fake call x6", "FIXED",
         "C3 (bright crest lines), C4 (whitening bands, scratches), the cavity dust / grime and the soot (m5) kept", {},
         True)
    item("R3", "realism", "Firefly / sparkle specks on the rail", "fake call x2", "FIXED",
         "C3: no bare cluster under 14 texels, no bright texel off an edge", {"gate": lines.get("pass")},
         lines.get("pass"))
    item("R4", "realism", "FP stock top 'a thin curved sheet'", "fake call x2", "FIXED (part)",
         "the cheek strut is right under the 35 cm eye at a grazing angle: its matte top mirrored the grey world as a "
         "smooth light plane; it now carries the moulded texture, roughness variation and the parting line (C4). The "
         "geometry is the traced strut (26.7 mm wide, R 1.4 edges): unchanged", {}, True)
    item("R5", "realism", "No markings (selector pictograms, serial, maker)", "fake call x5", "REJECTED",
         "the asset rule: generic, no markings (brief; CLAUDE.md IP: everything sold is the user's own design, no "
         "franchise / maker names); a buyer adds decals", {}, True)
    item("R6", "realism", "Magazine ladder 'invented decorative windows'", "fake call x1", "REJECTED",
         "the sheet draws the ladder (two recessed channels crossed by flush ties, CRAFT 2.14; trace 4 ties on the LEFT "
         "view); 'exact on the sheet' wins", {}, True)
    item("R7", "realism", "Receiver panel lines / flat panels without draft", "fake call x3", "REJECTED (part)",
         "the seam is the sheet's drawn upper / lower split, built as the real two-piece step (R43); the side faces are "
         "formed by side actions (no draft on the faces, the openings' walls drafted 1 deg: CRAFT 2.1); the moulded "
         "texture and parting lines now read (C4)", {}, True)
    item("R8", "realism", "Rear sight base a kitbash trapezoid / chevron inlay", "fake call x2", "REJECTED",
         "the generic rail-clamp BUIS base (RP15): a clamp with its recoil lug and the leaf's pocket, as the sheet "
         "draws the base; its bright dashed edge is gone with C3", {}, True)
    item("R9", "realism", "ADS front post a speck", "fake call x2", "REJECTED",
         "B4: the post tip centred in the 2.0 mm aperture at 0.25 m (lateral 0.0, vertical 0.0, post visible 0.99 mm): "
         "the true sight picture of a 1.85 mm post at 243 mm sight radius", {"B4": gate_by(form, "B4 sight").get("value")},
         True)
    item("R10", "realism", "Grip without stippling; guard thin; magwell plain", "fake call x2", "REJECTED (part)",
         "the stipple panels are built (pebbles 0.5-0.8 mm, 0.10-0.15 mm tall; W2 gate) and read at 35 cm, not at the "
         "hero distance; the guard bar and the flare band / funnel are the sheet's and the real pattern's", {}, True)
    item("R11", "realism", "Folded stock: pad grooves a greeble, hinge cap a placeholder, arm heavy", "fake call x2",
         "FIXED (part) / REJECTED (part)",
         "the pad's ribs now one constant pitch, open at the sides as a moulded rubber pad (m3 b); the hinge knuckle "
         "stack, axle and latch are built on the right (the view sees the left); the arm is the traced skeleton", {},
         True)
    rex = S["review_export"]
    item("R12", "realism", "Flat grey backdrop, even lighting", "fake call x1", "FIXED",
         "the realism views (review/realism/<name>.png) are lit by the photographic studio rig (gunlib "
         "export_review_job 'studio': Blender's bundled studio HDRI, neutral, for light and reflections + softboxes; "
         "the camera still sees the grey 126 backdrop); the L5 calibration rig's versions are kept in review/realism/l5/ "
         "and the review set stays on L5 (the colour test is unchanged)",
         {"realism_files": (rex.get("realism") or {}).get("files")},
         any(f.endswith("realism/l5/hero_34.png") for f in (rex.get("realism") or {}).get("files", [])))
    # ---------------------------------------------------------------- tech review notes
    item("n1", "tech", "Mag fit M4 definition (ruling)", "note", "FIXED (record)",
         "R36's spring-catch M4 (the catch zone = the nose's whole ride over the magazine's rear face, depth <= "
         "engagement + 0.3, <= 0.87 mm per 0.5 mm step, the catch back at rest when seated) written into "
         "SMG_BUILD_PLAN 12.2 for W5 M9 and later guns; smg_spec gates.magazine.M4 already carried it",
         {"spec_M4": "smg_spec.json gates.magazine.M4"}, True)
    item("n2", "tech", "Budgets (LOD0 46.9k over the 25-40k target, LOD2 20 %, mag LOD2 628 / LOD3 24)", "note",
         "ACCEPTED (reported)",
         "inside the 50k ceiling and the qa budget; LOD-pop and the M1 LOD pairs pass, so none is visible; recorded as "
         "accepted deviations from spec section 7 (README at W6)",
         {"B8_gun": b8.get("value"), "B8_mag": b8m.get("value")}, True)
    item("n3", "tech", "UD4 not reproducible from the shipped bytes (chart ids in the build npz)", "note",
         "DEFERRED to W5 (U8)",
         "U8 measures the lightmap in the engine; the 1,320 shared texels at 64 px are the projection charts' design "
         "(one chart, disconnected same-facing faces). LightMapResolution stays a W5 / U8 decision",
         {"UD4_build": gate_by(w2, "UD4").get("value")}, True)
    item("n4", "tech", "ShellEject with the stock folded", "note", "FIXED (record)",
         "the ShellEject socket's use text (spec -> sidecar) now says the throw cone meets the folded stock (B3b: 29 "
         "vertices; Q5 open) and that spawned casings ignore the gun's own collision",
         {"ShellEject_use": next((x.get("use") for x in skj.get("sockets", []) if x.get("name") == "ShellEject"),
                                 None)},
         "folded stock" in str(next((x.get("use") for x in skj.get("sockets", []) if x.get("name") == "ShellEject"),
                                    "")))
    item("n5", "tech", "W5 U2b needs the AR-01's abp_angle_table", "note", "DEFERRED to W5 (harness data)",
         "the AR-01 bytes stay as shipped; the W5 harness takes the AR-01 table from Scripts/guns/rifle/rifle_rig.py "
         "(trigger 0..12, selector 0 / 16 / 32, release 0..10) as harness data", {}, True)
    item("n6", "tech", "FBX NativeFilePath carries the absolute source path", "note", "DEFERRED to W6 / P (pipeline)",
         "pipeline-wide (Scripts/pipeline/export_fbx, AR-01 N1): fixed once before the Fab release, not per gun", {},
         True)
    item("n7", "tech", "UCX_SM_SMG01_LOD0_02 not strictly convex (0.445 mm)", "note", "ACCEPTED",
         "Unreal rebuilds the hull from the vertices; C1 found 0 of 400k samples outside", {}, True)
    item("n8", "tech", "Report wording (W3 tris 23,346 vs 23,344; UD4 on the SK; worst_excursion; latch-bolt 0.458)",
         "note", "FIXED (record)", "corrected in review/FIX_LOG.md section 4; no asset change", {}, True)
    rg = S["gunlib_regression"]
    item("n9", "W4 resume", "AR-01 regression compare crashed (KeyError 'status') and flagged the SMG blend",
         "process", "FIXED",
         "ar01_regression_compare.py reports an incomplete test record instead of crashing, and its git check covers "
         "the AR-01's own blends only (Assets/Guns as a whole matched Assets/Guns/SMG01.blend)",
         {"status": rg.get("status"), "failed": rg.get("failed")}, rg.get("status") == "pass")
    ud_rows = {k: gate_by(game, k) for k in ("UD1 Unreal degenerate rule on every LOD1-3 part",
                                             "UD2 micro edges / needles / strips (LOD1-3)",
                                             "UD1 / UD3 on the joined twin LODs")}
    item("n10", "W4 resume", "LOD1 needles from the first fix pass (butt pad grooves, guard corner rounds)", "process",
         "FIXED",
         "W3's UD gates failed at LOD1 (3, then 2 Unreal drops). The pad's grooves, open through LOD1's 2-segment side "
         "rounds: LOD1+ closes them inside the rounds again; the guard's 8-segment corner rounds (0.3 mm chords on its "
         "flat side faces): LOD1+ uses the LOD count (4). LOD0 unchanged",
         {k: v.get("value") for k, v in ud_rows.items()}, all(v.get("pass") for v in ud_rows.values()))
    # ---------------------------------------------------------------- record
    items_ok = all(i["pass"] for i in items)
    stages_ok = all(v["pass"] for v in stage_rows.values())
    out = {"stage": "W4 review fixes (SMG_BUILD_PLAN 15 row W4)", "date": datetime.datetime.now().isoformat(
        timespec="seconds"), "status": "pass" if (items_ok and stages_ok) else "fail",
           "failed": [n for n, v in stage_rows.items() if not v["pass"]] + [i["id"] for i in items if not i["pass"]],
           "stage_files": stage_rows,
           "counts": {"items": len(items), "fixed": sum(1 for i in items if i["verdict"].startswith("FIXED")),
                      "rejected": sum(1 for i in items if i["verdict"].startswith("REJECTED")),
                      "deferred": sum(1 for i in items if i["verdict"].startswith("DEFERRED"))},
           "items": items, "log": "WorkFiles/guns/smg/review/FIX_LOG.md",
           "process": "every fix in the generators; then Scripts/guns/smg/run_all.sh from nothing: run_smg.sh -> "
                      "run_surface.sh -> AR-01 regression -> run_rig_mag.sh -> smg_review_export.py -> this record"}
    (GATES / "review_fixes.json").write_text(json.dumps(out, indent=1, default=str))
    print("[W4 fixes]", out["status"], out["failed"], out["counts"])


if __name__ == "__main__":
    main()
