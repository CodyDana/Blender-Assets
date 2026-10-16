# SR01 realism round 2: a new edge method (rim slab)

**Date:** 2026-10-14. **Branch:** `claude/sniper-sr01-realism` (worktree). Nothing is committed. **Lock:** `SR01` (claude).
Blender ran headless. Every export went through `Scripts/pipeline/` with `qa_check` first. No Unreal work was done.
**Spend:** about $15 of the $20 cap.

> **W5 does not apply to these bytes.** `Exports/Guns/SR01/` changed in this round. The Unreal 5.8 verification (W5)
> must be re-run on the new bytes before this branch is merged. The round-1 bytes are in git (HEAD) and in
> `scratch/r2/before_exports/`.

**Status: stopped. The round did not reach a clean gated point.** Read the gates section before using the exports.

## Method: why the change, and what it is

Round 1 used an unclamped weighted bevel plus exclusion boxes. Where the round overlapped itself, it tore slivers.
This round runs no bevel on the chassis, butt, butt pad, cheek riser or grip. The edge radius is built into the
generator instead (`Scripts/guns/sniper/sr_rimslab.py`, wired in `sniper_parts.py` as `*_r2`; `SR01_RIMSLAB=0` gives
back round 1). The steps:

1. **2D side-view CSG.** The traced rings, boxes and seat cuts are united and subtracted as thin prisms with the exact
   solver, and the outline is read back. Seams between traced pieces vanish before any 3D work.
2. **Outline clean-up.**
   - Fairing: Gaussian smoothing, with real corners pinned.
   - De-step: steps and spikes smaller than the radius are removed.
   - Belly: a lower convex hull for the chassis belly.
   - Fillets: every corner is filleted at more than the rim radius.
3. **Rings.** Per-edge offsets of the outline, r(1 − sin φ) at y = W − r + r cos φ.
   - One vertex per outline vertex, so the loft is 1:1.
   - Joint edges take offset 0, so joint faces stay flat and sharp.
   - Any fold is detected and unfolded.
4. **Plan width as a shear.** h(x, z) sets the width, and the dovetail band's 45° flanks are part of h, not a boolean.
   Break vertices are snapped into every ring.
5. **Caps.** Constrained Delaunay fill with the breaks as constraints. This fill gives no needle ears.
6. **Residual fix.** A no-move pass: it rotates needle edges, and collapses only sub-0.15 mm edges or needles, never
   on joint or seat slabs.

**Probe evidence** (`scratch/r2/p1..p8`, Workbench close-ups):
- All five parts are manifold and pass UD1 and UD2.
- No torn slivers: compare `p1/grip_base_r34.png` with the round-1 crops.

Three of the judges' items turned out to be in the trace itself, and were fixed at the outline:
- **Nose zig-zag:** the trace had a 4 mm sawtooth at x 832–838. The nose is now one chamfer.
- **Wavy underside:** the trace had a 1.2 mm bump at x 522–533 and a 0.6 mm dip at the centre/forend seam. The belly
  is now a lower convex hull.
- **Grip-base sliver:** the trace had a 1–3 mm lip under a 1 mm slot. The heel is now solid, with the same rear
  reach.

Also:
- The pad's rear-top jags are dropped.
- The grip tang's neck is widened from 1.3 to 4.5 mm.
- Two coincidences are removed: the guard-opening walls appeared in both slabs, and an outline step sat 0.05 mm from
  the inlet end.

**Paint (cheap K items):**
- K4 source found: anodized small parts took the bright-wear mask, which sets metal to 1. They are now excluded.
- K2: the bolt satin is floored at 0.46 after the handling polish.

## Gates (exported bytes = first full pass; build = second pass)

The **first full pass** (rim slab, before the joint fixes) ran end to end: form → scope → W2 → W3, exports, and
fresh-process verifies. The review renders and `gates/closeup_r2.json` come from those bytes.

Stage gates:
- `scope_form`, `scope_export`, `game`, `rig_export` and `mag` all pass. `rigv` passes.
- LOD0 is 45,590 tris, magazine included (round 1: 41,396).

Form found regressions:
- **G5:** the grip/chassis joint (gap 0, 78 intersecting pairs) and the bipod clamp/chassis.
- **F1:** fails from the clamp intersection.

**Second pass** (fixes: the clamp seat as a joint edge, the guard clipped at the grip-front plane, the fine pass kept
off joints):
- The grip/chassis joint is fixed.
- **The bipod clamp still intersects the chassis seat:** 23 triangle pairs, gap 0.003 mm against ≥ 0.01. G5 and F1
  fail.
- The run stopped at the form check (`scratch/r2/logs/master.log`), so the **exports were not regenerated** from the
  second pass.

| Gate | Round 1 (W4b) | Round 2 |
|---|---|---|
| L2 GR IoU | 0.9602 | **0.9571** (−0.003: fillets and fairing) |
| L2 GL | 0.9426 / 0.9505 | **0.9410 / 0.9490** |
| L2 TOP | 0.8375 / 0.9020 | 0.8376 / 0.9026 |
| L3 GR P95 px | 3.0 | **3.61** |
| UD1 / UD2, B3 (all, incl. full bipod sweeps), F2–F9, H1 | pass | pass |
| G5 / F1 | pass | **fail** (clamp seat) |
| K1 hard creases (after/before) | 15.9 → 14.9 m | 14.9 → **8.6 m** (0.58×, target ≤ 0.5×) |
| K2 bolt P5 | 0.39 | 0.39 (misread: the gate's rows were mirrored, see "K-gate measurement fix"; the floor did reach the ORM) |
| K3 peel tilt | 0.435 | 0.436 (not addressed) |
| K4 small-part metal texels | 13,254 | **8,331** (misread, same bug: mirrored rows; neither number describes the small parts) |
| K8 hot pixels fp_35cm | 6 | **2** (pass) |
| K5, K6, K7, K11 | pass | pass |
| K10 side views | pass | **fail** (GR −0.003) |

## Judges (independent, fresh, once; Sonnet to save credit)

| Judge | Round 1 | Round 2 |
|---|---|---|
| Realism A | fake 8/8 (88) | **fake 8/8** (85–98) |
| Realism B | fake 8/8 (89) | **fake 8/8** (80–96) |

Results are in `review/r2/judges/realism_A.json` and `realism_B.json`.

- **No longer named:** torn grip slivers, the grip-base sliver, the forend-nose zig-zag, jagged riser/pad notches.
- **Still named by both:**
  - A wavy / stepped lower handguard edge (`deployed_34`).
  - Stepped stock seams and a boxy riser.
  - Faceted flat planes, trigger and turret flutes.
  - Blocky floor shadows, which come from the render rig.
- A also sees a notch on the handguard top near the mount (`hero_34`).
- Both still call out materials, lighting and optics, as in round 1.

## Renders to compare

- `review/r2/compare/*.png` and `compare_all.png`: round 1 on the left, round 2 on the right, same cameras.
  - Items: grip base, grip side, riser, butt pad, stock body, chassis underside, trigger guard, forend nose.
- `review/r2/realism/` and `review/r2/set/` (22 images) against `review/w4b/`.

## Blockers / left

1. **The clamp seat intersection** (G5 / F1).
   - The clamp's top (z −39.61) sits 0.03 mm under the seat (z −39.58).
   - The slab's seat floor or rim still dips 0.03 mm somewhere in x 740–845.
   - Next: locate it with `fgates` pairs, or move the seat floor to a joint at exact z, then rerun `scratch/r2/master.sh`.
2. **K10 / silhouette −0.003 GR.** Fillet radii (rc = 1.3r + 0.3) and fairing round the traced corners. Smaller corner
   fillets on the long runs (or rc = r + 0.1) would likely recover it.
3. **The judges still call the round fake.** The geometry list moved from tears to faceting, seams and the lower
   handguard edge. Materials, lighting and optics need the in-engine pass (W5), as in round 1.
4. **The exports in `Exports/Guns/SR01/` are the first-pass bytes and fail G5 / F1.** Don't merge them. Re-export after
   item 1. W5 must then be re-run on those bytes.
5. **Housekeeping for the user:** 8 probe PNGs landed in `C:\WorkFiles\guns\sniper\scratch\r2\p1\` (a relative render
   path, since fixed). That is outside this worktree and I can't delete it.
6. Two of my Blender processes overlapped once: the first form chain's `fgates` was still running while the next
   chain started. The second process only read the blend.

## Finish (2026-10-16): clamp seat fixed, one full pass, W5 37/37

**What changed**
- `Scripts/guns/sniper/sniper_parts.py` now builds the clamp seat floor as material at exact z. The outline's floor
  edge is split inside the `flat` handler, which removes the needle rim triangles UD2 flagged.
- The probe (`scratch/r2/p8`) reports no bad parts.
- **GR recovery:** not attempted. It was not cheap enough for the remaining credit. GR stays at 0.9571 (−0.003),
  caused by the fillets and fairing that removed the four defects. K10 is still the one side-view regression.

**One chain from nothing** (`scratch/r2/master.sh`, run in full, 10:26–12:19)
- The blend and every export come from this pass. Logs: `scratch/r2/logs/` (killed run: `logs_pass3_killed/`).

| Gate | Round 2 (first pass) | Round 2 final |
|---|---|---|
| G5 rest intersections / butt-joint gaps | **fail** (23 pairs, 0.003 mm) | **pass** (0; min 0.0152 mm over 16 pairs) |
| F1 bipod folded gaps | **fail** | **pass** |
| B3 (bolt, trigger, safety, release, riser, full bipod fold / extend / cant sweeps) | pass | pass (0 intersecting steps; min clearance 0.153 mm) |
| UD1–UD4, F2–F9, H1, scope A1–A5 | pass | pass |
| game, rig_export, mag M1–M10, scope_export | pass | pass |
| L2 GR / L3 GR P95 | 0.9571 / 3.61 | 0.9571 / 3.61 (declared, see above) |
| uv_bake_paint | partial (B9 density class C) | partial (same, as W4) |
| K1 / K3 | fail | fail (unchanged; not addressed) |
| K2 bolt P5 | 0.39 | 0.384 as first measured; **0.565 pass** after the measurement fix (see "K-gate measurement fix") |
| K4 small-part metal texels | 8,331 | 19,463 as first measured; **0 pass** after the measurement fix |
| K9 / K10 | fail | fail (K9 = the form stage gate's failed list; K10 = GR −0.003) |

- qa_check passed before every export.
- Export sha256: `scratch/r2/exports_sha256_r2.txt`.

**W5 (Unreal 5.8.3, `/Game/GunCheck/SR01_1016r2`)**
- **37 of 37 pass**, `engine_verified: true`, sha256 equal at start and end. See `W5_REPORT.md` → "Round 2 bytes".

**Renders**
- From the exported bytes: `review/r2/realism/deployed_34.png`, `hero_34.png`, `review/r2/set/deployed_hero.png`,
  `q34.png`.
- From Unreal: `UnrealCheck/renders/look_deployed_hero34.png`, `look_hero34.png`.
- `Renders/Guns/SR01/tex_deployed_hero.png` was refreshed by the chain.
- No judges this round (no budget).

**Left**
1. ~~K4 went up (8,331 → 19,463).~~ Resolved: a measurement bug, see "K-gate measurement fix". K4 = 0.
2. GR −0.003 / K10, and K1 / K3: as listed above.
3. The judges still call the renders fake. That is unchanged from round 2's first pass and was not re-judged.

## K-gate measurement fix (2026-10-16)

**Cause.** `sr_closeup.py` `maps_metrics()` compared the bake arrays (`*_ids.npy`, `*_pos.npy`, stored bottom-up in
Blender pixel order) with the PNG maps (top-down) without flipping either. K2, K4 and K5 were read from the vertically
mirrored texels. The paint was never wrong. Details: `K4_NOTE.md`.

**Fix.** The bake arrays are flipped to PNG row order (`[::-1]`). A registration guard now stops the run unless the bolt
is > 50 % metal and the receiver < 5 % (measured: bolt 81.7 %, receiver 0.0 %). Round 1's "before" snapshot
(`scratch/r2/before_metrics.json`) was taken with the same bug and with bake ids that no longer exist, so it is marked
invalid; K2's relative P50 test falls back to the absolute P50 ≥ 0.45. Re-run with
`sr_closeup.py --round r2 --reuse-k1` (no Blender, no export; the old gate file is kept in
`scratch/k4/closeup_r2_before_fix.json`).

| Gate | before the fix | after the fix |
|---|---|---|
| K2 bolt roughness P5 / P50 / P95 | 0.384 / 0.627 / 0.89, **fail** | 0.565 / 0.608 / 0.655, **pass** |
| K4 small-part metal texels | 19,463, **fail** | **0, pass** |
| K5 scope anodize roughness P50 | 0.60, pass | 0.51, pass |
| K5 lens BC std / mean (sRGB) | 19.42 / (24, 21, 25) | 5.16 / (35, 35, 36) (reported, not gated) |

`gates/closeup_r2.json` is still **fail**, now on K1, K3, K9 and K10 only. K9 fails on the form stage gate's failed list
(it contains "L2 GR IoU", which is not one of the W1-open items), not on K2/K4. Nothing was re-exported, so W5 (37/37) stays valid.
