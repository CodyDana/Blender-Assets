# SR01 W4 fix log (Part A leftovers + the W4 review fix round)

Machine record: `gates/review_fixes.json` (`Scripts/guns/sniper/sr_review_fixes.py`). Judges' raw files:
`review/w4/judges/` (before) and `review/w4fix/judges/` (after the fix round). Every number below comes from gates
rebuilt on exported bytes.

## Part A: W3 leftovers

| # | Item | What changed (generator / pipeline step) | Result |
|---|---|---|---|
| A1 | Magazine catch (M2 0.87, M3 1.45, M4 ride) | `sniper_parts.mag_release`: the real spring-catch hook: flat bearing top Z -47.5, nose X 415.75, 41 deg ramp underside. Notch 2.2 deep. Magazine body top -21.2 (the shelf at -19.7 is the stop: 1.5 mm overtravel, was 0.3 and unseen by the gate) and lips + top round +0.5 (round to bolt 2.32 -> 1.82). `sr_magfit` runs M4 in gunlib's `catch_spring` mode (the SMG W1b rule). Proven on the form blend first with `sr_catch_probe.py` (9 min instead of the 50 min chain) | M1-M10 PASS on exported bytes: bearing 0.21, overtravel 1.82, engagement 1.65, M4 cam 0.40 mm / step, snaps at the seat; M4b / M5 / F5 pass |
| A2 | Scope LOD2 FBX dropped 2 faces | `sr_lodlib.drop_coincident_pairs` after the joined LOD's weld (back-to-back internal walls of touching parts go in pairs) and on fins a decimated part keeps | build = FBX on every LOD (scope, SK, SM) |
| A3 | LOD2 switching late (25.6 m) | `sr_game`: silhouette-weighted ratios (hidden pins / screws / swivel / bolt at 0.4 x at LOD2, 0.3 x at LOD3), silhouette parts never dropped (W3 dropped `pad_plate` at LOD2: the 2.9 px pop at the butt) | LOD-pop pass on both bipod poses: LOD1 3.97 m, **LOD2 15.1 m**, **LOD3 30.1 m** (were 25.6 / 45.8); screen size LOD2 0.066 (SMG 0.053) |
| A3b | New: hull `UCX_SM_SR01_LOD0_01` grew to 1e16 m | `sr_game.valid_hull` checks every hull (outward faces, box, containment); a failed gunlib hull is rebuilt by `sr_lodlib.hull_safe` (same method, 1 um dedup, normals recalculated after each hull step) | C1: 0 samples outside, 10 hulls <= 32 verts |
| A4 | Mag LOD0 878 (target 2-3k) | **declared**: the body sits in the well; the visible part already carries its chamfers / ribs as geometry | - |
| A5 | Re-export, verify, regate | `run_rig_mag.sh` on the new blend | game / rig_export / mag / scope_export PASS |

## The review (before the fix round, from the exported bytes)

- Set + realism renders: `review/w4/set/`, `review/w4/realism/` (SMG W4b r2 product-set studio rig).
- Blind: 14 pairs (4 panels incl. the solved 3/4 camera `scratch/w4/q34_camera.json`, silhouette IoU 0.76; 10 side
  windows). **The judge picked the copy in 14 / 14 on design** (stock hardware, open guard, glossy scope, flutes).
  Reported, not blocking.
- Realism A and B: **fake on 5 / 5 each** (scope chrome, black-disc eyepiece, flat clay chassis, no wear, faceting).
- Craft: 6 major (C1-C6), 7 minor (C7-C13). Tech: 0 blockers, 3 major (T1-T3), 7 minor.

## The fix round (one round, full chain from nothing: form -> scope -> W2 -> W3)

| Id | Finding | Verdict | Fix |
|---|---|---|---|
| C1 | Scope anodize reads as chrome (craft + both realism judges) | FIXED | FIN `scope_anod` rough 0.24-0.34 -> 0.46-0.56 |
| C2 | Trigger guard open at the bottom (sheet: closed) | FIXED | chassis bottom bar X 336.5-399.5, Y +-8.6. Tried first: Y +-9 coplanar and X 338-398 ends: 1-10 UD1 slivers each (variants run as chassis-only builds) |
| C8 | Bolt mirror chrome; identical bright ring on each turret cap | FIXED | `bolt_polish` lin 0.42-0.46 / rough 0.32-0.44; `leg_polish` rough 0.24-0.34; scope cap wear rarer |
| C9 | Release pin end half in air | FIXED | pin +-8.0, bore +-8.1: hidden inside the cheeks (a 0.3 mm boss was tried first: 1 UD1 sliver) |
| C13 | Faceted eyepiece / bell rims | PARTIAL | scope body 36 -> 64 sides (scope LOD0 now ~9.9k, inside 6-10k); trigger blade kinks -> W4b |
| T1 | No README | PARTIAL | `Exports/Guns/SR01/README.md` (pre-Unreal); MATERIALS_README in W6 |
| T3 | Stale declared list | FIXED | `sr_w2_gates` declared text |
| T6 | No colour-space tags | FIXED | stated in the README |
| T7, T9 | Mag hull name; LOD2/3 mag intersections | REJECTED | hull is `UCX_SM_SR01_Mag_LOD0_00`; M1 sub-pixel rule passes |
| C3-C7, C10-C12, T2, T5, T8, T10 | see review_fixes.json | DEFERRED | W4b (close-up realism) or W5 (Unreal) |

## For W4b (what the realism judges and the craft judge want)

1. Scope: matte anodize everywhere (done in the fix round; re-judge), coated glass with depth and a reticle (an ADS
   view needs an in-engine scope material: W5), turret markings (generic).
2. Chassis / butt / riser edge bevels (M-chamfer 0.6-0.9 mm) with the chassis taken into the UD repair pass (C5).
3. Wear and grime that read: edge chips to bare aluminium on the new bevels, grime in slots and the port (C6, C11).
4. Trace fairing: line / arc fit of the traced outlines before extrusion (C3); a lofted grip with draft and a parting
   line, no toe spur (C4).
5. Barrel flutes measured against GR / Q34 (C7); butt discs (C10); OD under the 3/4 light (C12, a Q34 crop match).
6. More segments / analytic normals on small rounds (trigger blade, knobs); a floor + contact shadow in the review rig.

## W4b close-up round 1 (2026-10-13; full report W4B_REPORT.md, gates/closeup_r1.json)

| Item | What changed | Result |
|---|---|---|
| Edges | `sniper_parts`: weighted unclamped 1.2 mm / 3-seg round on chassis / butt / riser with round_free boxes + a protected local UD fix (Blender's global clamp had shrunk the W4 chamfer to microns); faired centre + guard outlines | UD / G5 / B3 / F / H1 pass; K1 hard creases 15.9 -> 14.9 m (FAIL vs <= 0.5x) |
| Grip | moulded: YZ lens (palm swell), 3.5 mm round, stipple | H1 165.9 (<= 167); judges still call the grip torn / primitive |
| Chassis finish | 1.3 mm peel, sheen drift, wear by cause only, dark-anodize chips, handling polish, dust | K3 FAIL (tilt 1.4x of the 2x target; rub -91 %) |
| Bolt / legs | blasted satin 0.48-0.60, lathe bands | K2 FAIL (P5 0.39) |
| Small parts | no bare-steel chips; hex sockets painted (66) | K4 FAIL (13,254 metallic texels left, source not traced); K6 pass |
| Scope | turret ticks + numerals, coated convex lens (BC lifted to the B9 floor) | K5 pass |
| Review rig | tabletop + contact shadows, DoF | K7 pass; K8 FAIL (6 hot px) |
| Judges | realism A / B on 8 views each | fake 8/8 (88) and fake 8/8 (89): no movement; geometry artifacts now their top tell |

## Realism round 2 (2026-10-14, branch claude/sniper-sr01-realism): rim-slab edges
- Method changed: no bevel on the chassis / butt / pad / riser / grip. Edge radii are built into the generator
  (`sr_rimslab.py`: 2D CSG -> fair / de-step / fillet -> 1:1 offset rings -> plan shear incl. the dovetail band -> CDT
  caps). Round-1 weighted round + exclusion boxes retired (`SR01_RIMSLAB=0` restores them).
- Trace fixes at the outline: nose sawtooth (x 832-838), belly bump / dip (lower hull, x 500-600), grip heel lip +
  slot, pad rear-top jags, grip tang neck 1.3 -> 4.5 mm.
- Paint: anodized small parts are excluded from bright wear (K4 13,254 -> 8,331); bolt satin is floored at 0.46 (K2 is
  unchanged in the shipped ORM).
- Gates (see `REALISM_R2_REPORT.md`):
  - UD1 / UD2, B3, F2-F9, H1, W2 / W3 all pass.
  - G5 / F1 fail: the bipod clamp is 0.003 mm into the seat.
  - K10: GR 0.9602 -> 0.9571.
  - K1: 14.9 -> 8.6 m.
- Judges: A and B fake 8/8. The tears, grip base and nose zig-zag are no longer named. The lower handguard edge,
  stock seams and faceting are still named.
- Stopped before a clean export. W5 must be re-run on any new bytes.
