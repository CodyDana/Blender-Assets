# SR01 W3 report: Part 0 (W2 leftovers) + rig, magazine, bipod, exports

**Date:** 2026-10-13. **Branch:** `claude/sniper-sr01` (worktree), nothing committed. **Lock:** `SR01` (claude,
refreshed). Blender headless only. Every export went through `Scripts/pipeline/export_fbx` with `qa_check` first.
No review round, close-up pass, Unreal or pack materials (as instructed).

## Part 0: W2 leftovers (all rerun from nothing; textures come from the final geometry)

| # | Item | Result |
|---|---|---|
| 1 | UD2 chassis micro edges / needles | **0 / 0 / 0**, fixed in the generator (`sniper_parts.chassis`). Three coincident-face sources removed: the knob filler box (Y +-27 -> +-28, clipped by the plan); the forend root box (Y +-36.9 -> +-38, top 15.9 -> 15.6); the stem relief face (Y -10.5 -> -10.2, which sat 0.035 mm from an inlet facet vertex). The plan prism also lost a collinear point. |
| 1 | UD3 float32 zero-tangent corners (8) | **0** on the twin, every part and every LOD (gun, mag, scope). **Declared deviation:** the fix is in the UV stage, not the generators. `sr_uv.f32_visible` is the SMG's W3 visible-sliver rule: flat normals on sub-degree bevel-strip slivers, plus a corner tilt where needed. It changes normals only and moves no geometry. Generator-side attempts failed and are documented in `sniper_parts`: planar edge flips cannot reach non-planar strips; collapses broke UD1 min-area; post-boolean station cuts made more micro strips than they removed. The exact boolean also merges coplanar stations made before it. |
| 2 | S / F safety marking | On the visible outer face (Y -27, under the pocket): **109 texels** painted (was 0). Generic letters only. |
| 3 | Trigger blade 5 mm back | Done. The root stays at pivot X 368; the chassis trigger slot runs 6 mm further back (the first try hit the slot: 54 intersecting steps). **B3 trigger 0 intersections** (min 0.155 mm to the pin, hinge row), **F9 0.185 mm**, H1 reach 44.7 mm (was 49.2; gate <= 80). |
| 4 | TOP conventions + GL window | Recorded as ACCEPTED (user) in `SR01_STUDY.md` (new section at the end). |
| 5 | Chains rerun | `run_sniper.sh` (form) then `run_surface.sh` (W2), via `scratch/w3/part0_chain.sh`. Form gates: B3 all 0 intersections, F1-F9 pass, UD1/UD2 0, B7 33/33, B8 35,060. Still open from W1/W2: L2 GL/TOP/per-part, L3 P95, L4 13/14. W2: 59/61 pass; the B9 class-C near-misses (Metal 31.3 vs 31.5, scope 40.9 vs 41.1) remain. L5 12/12. |

## W3 results (gate files in `WorkFiles/guns/sniper/gates/`)

| Gate file | Status | Key numbers |
|---|---|---|
| `game.json` | **pass** | LOD0-3 (gun without mag) **34,182 / 15,350 / 5,096 / 2,526** (45 % / 15 %); twin with mag 35,060 / 15,744 / 5,226 / 2,576. 10 hulls `UCX_SM_SR01_LOD0_00..09` (27-28 verts), C1 0 samples outside. 20 sockets. LOD1-3 UD1 0, UD3 0. |
| `game_lod_sizes.json` | **pass** | LOD-pop on BOTH bipod poses: SM sizes [1, 0.25, 0.0387, 0.0217] (3.97 / 25.6 / 45.8 m, worst max 2.92 px). SK [1, 0.273, 0.0423, 0.0237] at SK engine radius 0.609 m (bind box + extension). |
| `rig_export.json` | **pass, 14/14** (fresh process, exported bytes) | B1 13 bones on all 4 SK files, heads <= 0.001 mm, magazine bone unweighted. Clips read back: max 0.00017 mm / 0.00003 deg. B4/B5 sockets <= 0.001. SM_SR01 tris + 10 hulls equal. sha256 equal. B10 clean. |
| `mag.json` | **fail (declared)** | Pass: M7 bytes, M6 (MagInsertStart on axis 3e-6 mm), M1 (LOD0-1 0 hits; LOD2/3 0.02 / 0.16 px), M4b, M5, F5, **M8 0 hits**, M9, M10 (twin mag = SM_SR01_Mag per LOD), qa, UD. **Fail, catch geometry:** M2 bearing gap 0.87 (gunlib wants 0-0.3) and overtravel 2.32 (1-2); M3 engagement 1.45 (>= 1.5); M4 with the catch at rest (the square hook rides the mag for 30 mm). This design inserts with the paddle pressed (M4b = the W1 rule), but a real catch would need a ramped hook underside, a flat bearing top and a notch moved ~0.6 mm. That is a W4 generator change; I didn't do it here because it needs another full form + W2 rerun. |
| `scope_export.json` | **fail (1 declared)** | Pass: sha, 3 hulls, qa, S1 (0.0004 mm), **A1** (+20.02), **A4** (Sight 57.6, 0 deg), **A3 on bytes** (2.46 mm at rest above the rail, 19.7 mm min over BoltCycle), B10. **Fail:** at LOD2 the FBX round trip drops 2 coincident faces of touching parts (build 850, FBX 848). |

**Rig (`SK_SR01`):**
- 13 bones as plan 2.2, rigid, triangulated; qa_skeletal max_influences=1 passes.
- The legs' 12 deg splay lives in the motion: the deployed rotation is about the pin axis (0, cos 12, +-sin 12). Rest rotations stay identity, as the standard requires.
- **P1:** `cheek_riser` under `body` is validated with a sniper-side table (`sr_common.standard_bones_p1`); gunlib is untouched. gunlib's own table is also run and rejects only `cheek_riser<-body` (recorded in the rig report).

**Clips:**
- 8 clips: Fire 60 fps, BoltCycle, Reload, ReloadEmpty (starts open), Selector, BipodDeploy (ends deployed), BipodStow (starts deployed at ext 38), CheekRiser.
- Safety held at FIRE in Fire / BoltCycle / ReloadEmpty; the bolt slides only at -60.
- Notifies are in the sidecar.
- M8 caught a real bug: the paddle was half-pressed when the mag reached the hook. Fixed (full press f40-43).

**B11:**
- Every LOD x every clip frame x the extreme poses (bipod folded / deployed x ext 0 / 76 x cant +-15, riser range, bolt open / back).
- Posed box M: X 0..1100, Y +-165.7, Z -349.1..54.2.
- Extension: +cm [0, 8.68, 2.42], -cm [0, 12.88, 18.39].
- The physics envelope box (no collision, no mass) carries the same bounds (SMG W5 lesson).

**Sockets:** 20 bone sockets (skeletal sidecar) + Empties / `.sockets.json` on SM_SR01, 5 on the mag, 5 on the scope.
CoM (part volumes x densities, bipod folded, mag out) is at M (497.5, -0.3, -27.3).

**Exports** (`Exports/Guns/SR01/`):
- the SK set + 8 clips + `Physics/` proxy + `SK_SR01.skeletal.json`;
- `SM_SR01` (+ sockets.json);
- `SM_SR01_Mag`;
- `SM_Att_Scope_LongRange`.

sha256 values are in `scratch/w3/rig/rig_report.json`, `scratch/w3/mag/mag_report.json` and `scratch/w3/scope/scope_report.json`.

**H1 full:** not run. The SMG harness (`smg_h1_full.py`, 714 lines, posed hand on MH_PlayerDefault) needs a sniper
port (grip axis 27.15 deg, its socket names), which didn't fit this run's budget. H1 early stands: girth 161, reach 44.7.

## Look at

- `Renders/Guns/SR01/w3_rig_contact_sheet.png`: every clip's key frames from the exported SK, including BipodDeploy side + front (splay) and BipodStow. The posing copies absolute matrices: a clip FBX whose first frame isn't rest carries that frame as its bind pose.
- `Renders/Guns/SR01/w3_lod_switch_sheet.png`: LOD0-3, plus each switch pair at its on-screen size.
- `WorkFiles/guns/sniper/review/w3/game/lodpop_*.png`.
- Refreshed W2 renders: `Renders/Guns/SR01/tex_*.png`.

## New / changed scripts (`Scripts/guns/sniper/`)

- **New:** `run_rig_mag.sh`, `sr_game.py`, `sr_lodlib.py`, `sr_viewgates.py`, `sr_rig.py`, `sr_clips.py`, `sr_gun.py`, `sr_rig_verify.py`, `sr_attach.py`, `sr_verify_static.py`, `sr_magfit.py`, `sr_rig_render.py`, `sr_w3_gates.py`, and the probes `sr_ud3_probe.py` / `sr_sliver_probe.py`.
  - `sr_rig_verify.py` is generated by `WorkFiles/guns/sniper/tools/port_w3.py` from gunlib's rig_verify. It differs in two places: B4 reads the scope's A4 (the gun has no Sight), and the expected pose matrices compose parents, which the bipod extension bones need. gunlib's flat form would report a false 90 deg error there.
- **Changed:** `sniper_parts.py` (UD2, trigger, slot, plan), `sr_uv.py` (UD3 rule, main guarded), `sr_surface.py` / `sr_paint.py` (S/F), `sr_fgates.py` (measured reach, `b3t`), `sr_common.py` (socket rows, P1 table).

## Left for W4 / blockers

1. Magazine catch geometry (M2/M3/M4 numbers above).
2. Scope LOD2 FBX drops 2 coincident faces.
3. The LOD2 switch is late (25.6 m: the 15 % collapse LOD changes the silhouette up to 2.92 px). A better LOD2 (generator-level LODs as on the SMG) would let it switch earlier.
4. LODs are collapse-decimated, not generator LODs. UV0/UV1 overlaps were collapsed (LOD1: UV0 74, UV1 2,378 triangles) and UV1 is the decimated LOD0 atlas: check U8 lightmaps in W5.
5. Mag LOD0 878 tris (target 2-3k) and scope LOD0 5,884 (target 6-10k), both from the W1 form.
6. H1 full port.
7. B9 class-C near-misses; L2/L3/L4 open items from W1.
8. Dry-run scratch blends are left in `scratch/w3/dry/` (untracked).

**gunlib proposals still pending:** P1 (now exercised; sniper-side table), P2, P3, P4, P5, P6, P7, P8, P9. New candidates:
- the parent-composed pose check in rig_verify (needed by any chained bone);
- the collapse-LOD helper with the qa UV-overlap rule;
- `f32_visible` as a UV-stage UD3 step.

**Spend:** about $20 of the $40 cap.
