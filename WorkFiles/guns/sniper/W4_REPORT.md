# SR01 W4 report: W3 leftovers, review, one fix round

**Date:** 2026-10-13. **Branch:** `claude/sniper-sr01` (worktree). Nothing is committed. **Lock:** `SR01` (claude,
refreshed). Blender ran headless only. Every export went through `Scripts/pipeline/export_fbx` with `qa_check` first.
The gates were rebuilt from exported bytes, each in a fresh process. Not done, as instructed: W4b close-ups, Unreal,
pack materials. Item-by-item record: `gates/review_fixes.json` and `review/FIX_LOG.md`.

## Gate state after the fix round (full chain from nothing: form -> scope -> W2 -> W3)

| Gate file | Status | Key numbers |
|---|---|---|
| `mag.json` | **PASS** (was fail) | M2: bearing 0.21, overtravel 1.82 (the shelf is the real stop at 1.5), seam 0.3. M3: engagement 1.65. M4 in spring-catch mode: cam 0.40 mm per step, snaps at the seat, 0 gun contacts. M4b / M5 / F5 / M1-M10 pass. |
| `scope_export.json` | **PASS** (was fail) | build = FBX on every LOD: 9,938 / 4,464 / 1,454. LOD0 is now inside the 6-10k target (was 5,884). |
| `game.json` | **PASS** | gun LOD0-3: 34,280 / 15,396 / 5,094 / 2,468 (44.9 % / 14.9 %). C1: 10 hulls, 0 samples outside. |
| `game_lod_sizes.json` | **PASS** | SM [1, 0.25, 0.0656, 0.033] = 3.97 / **15.1** / **30.1** m (were 3.97 / 25.6 / 45.8 m). Both bipod poses pass, LOD1->2 max 2.5 px. |
| `rig_export.json` | **PASS** | 13 bones on 4 SK files, clips, sockets, sha, B10, SM tris + hulls equal on re-import. |
| `scope_form.json` | **PASS** | A1-A5 on the 64-side scope. |
| `uv_bake_paint.json` | partial (unchanged) | Only the two known B9 class-C near-misses remain. L5 12/12. UD4 pass. |
| `form.json` | partial (unchanged) | W1-open items only: L2 GL / TOP / per part, L3, L4. B3, F1-F9, UD1 and UD2 are all 0. Form magfit passes. |

## Part A (W3 leftovers)

1. **Magazine catch** (generator, `sniper_parts`):
   - The hook now follows the real spring-catch pattern: a flat bearing top, the nose 1.65 mm into the notch, and a 41 deg ramp underside.
   - The notch is 2.2 mm deep.
   - The magazine body top moved down 1.2 mm. The 0.3 mm shelf gap was the true stop, and the gate's rays from the top round never saw it.
   - The lips and the top round moved up 0.5 mm.
   - `sr_magfit` uses gunlib's `catch_spring` M4 (the SMG rule).
   - Every catch iteration was proven on the form blend first with the new `sr_catch_probe.py` (9 min against the 50 min chain).
2. **Scope LOD2:** `sr_lodlib.drop_coincident_pairs` removes the back-to-back walls that the joined LOD's weld makes, plus decimation fins. The check itself is unchanged.
3. **LOD2 late:** the LOD generator now uses silhouette-weighted ratios, and silhouette parts are never dropped. W3 had dropped `pad_plate`, which caused the pop at the butt.
4. **New, found here:** the new LOD3 point set made gunlib's hull for the cheek riser come out with inward faces. Its grow step then scaled it to 1e16 m, and that hull would have shipped.
   - `sr_game.valid_hull` now checks every hull.
   - A failed hull is rebuilt by `sr_lodlib.hull_safe` (gunlib's method with normals recalculated). gunlib itself is untouched.
5. **Mag LOD0 at 878 triangles:** declared, not raised. The body sits in the well.

## Part B (review from the exported bytes)

- **Renders.** `scratch/w4/q34_camera.json` is a new camera solve for the sheet's 3/4 panel (silhouette IoU 0.76).
  - Review set: `review/w4/` before and `review/w4fix/` after. Each has `set/` with 18 shots: right, left, top, q34, deployed hero, bolt open, scope close, eyepiece, FP, 3x close-ups and wireframe.
  - Realism set: `realism/` with 5 shots on the SMG's product-set studio rig.
  - Blind set: `blind/` with 14 pairs.
  - Scripts: `sr_review_export.py`, `sr_review_job.py` (a copy of gunlib's job with the scope added) and `sr_q34_cam.py`.
- **Judges** (independent and fresh, results in `review/w4*/judges/`):
  - **Blind** (reported, not blocking): the copy was picked in **14/14 pairs on design**. The tells were stock hardware, the open guard, the glossy scope, the flutes and the grip.
  - **Craft:** G1-G20 walked; 6 major and 7 minor findings.
  - **Tech:** 0 blockers, 3 major and 7 minor findings.
  - **Realism A / B** (5 views each: FP 35 cm, eyepiece, TP 3 m, hero 3/4, deployed 3/4):
    - Before: **fake 5/5** and **fake 5/5**.
    - After the fix round: **fake 5/5** and **fake 5/5**, confidence 80-99.
- **Fix round.** Fixed in the generators and paint:
  - C1: scope anodize roughness 0.46-0.56. It had read as chrome.
  - C2: closed trigger guard. The sheet draws a loop; ours was open.
  - C8: satin bolt, and rarer wear on the turret caps.
  - C9: hidden release pin.
  - C13: 64-side scope body.
  - T3: the stale declared list.
  - T1 / T6: README written, as a pre-Unreal draft.
  - A W2 gate budget for the scope was stale at 8k against the plan's 12k ceiling. It is now aligned with the plan.
  - The guard bar and the boss had first added UD1 slivers. They were solved by bar variants run as chassis-only builds, and the boss was dropped.

## Look at

- `review/w4fix/set/close_action_right.png`: the closed guard and the hidden pin. Compare with `review/w4/set/`.
- `review/w4fix/realism/fp_35cm.png` and `hero_34.png`: the scope finish.
- `review/w4/blind/pair_01_*.png` (GR panel); the key is in `review/w4/blind_key.json`.
- `review/w3/game/lodpop_*.png` (regenerated): the LOD switches.

## Left for W4b / W5 / W6

- **W4b**, in the judges' order:
  - chassis finish: Cerakote with roughness breakup and edge wear (C6);
  - chassis, butt and riser edge bevels, with the chassis brought into the UD repair pass (C5);
  - outline fairing by line / arc fitting the trace (C3);
  - a lofted grip with draft and no toe spur (C4);
  - coated lens glass;
  - generic turret graduations;
  - a bolt finish that no longer reads chrome. Both judges still call it chrome after C8, so it needs a darker, anisotropic satin;
  - flutes measured against the sheet (C7), butt discs (C10), rail specks (C11), OD under the 3/4 light (C12), trigger-blade segments;
  - a floor and contact shadow in the review rig.
- **W5:** Unreal U1-U12. This includes an in-engine scope material (reticle and ADS view, which both judges want), the U8 lightmaps (T5), SK_AR01 compatibility (T8) and README import notes.
- **W6:** pack materials, MATERIALS_README and recolour constants.
- **Still open from W1-W3:** L2 / L3 / L4 form items, the B9 class-C near-misses, and the H1 full port.
- **gunlib proposals** (no gunlib edits here): a hull validity check plus a normals recalculation in `hull_from_points`; `_hull_only` fails on raw point clouds (duplicate geometry in its delete list); and the earlier W3 proposals.

## Spend

About $25 of the $35 cap.
