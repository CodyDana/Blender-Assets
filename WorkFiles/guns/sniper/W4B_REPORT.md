# SR01 W4b report: one close-up realism round

**Date:** 2026-10-13. **Branch:** `claude/sniper-sr01` (worktree). Nothing is committed. **Lock:** `SR01` (claude, refreshed).
Blender ran headless only. Every export went through `Scripts/pipeline/` with `qa_check` first. The chain was rebuilt from nothing (form -> scope -> W2 -> W3), and every gate was re-run on the exported bytes in fresh processes. No Unreal work and no pack-materials work were done, as instructed.

**Spend:** about $17 of the $25 cap.

## What changed

1. **Edges (geometry), in `sniper_parts.py`.**
   - **Root cause found.** Blender's bevel "clamp overlap" limits the width over the whole mesh at once. So one short edge anywhere cut the chassis / butt / riser 1.0 mm chamfer down to microns, and the 16 um weld then collapsed it. W4's "sharp CG creases" came from this.
   - **New weighted round.** `Part._round_weighted` applies an unclamped, weighted 1.2 mm / 3-segment round to the chassis, butt and riser.
     - Edges inside `round_free` boxes are not rounded. These boxes are the post-cutter zones, the joint faces and a few spots where the round overlapped itself, each found with `ud.locate`.
     - After rounding, a protected local UD fix runs (`Part._local_fix`, which uses gunlib's own UD metrics). It collapses only failing triangles that lie outside the protected walls (inlet, raceway, well, clevis, catch window) and outside thin joint slabs.
     - gunlib's global `ud.repair` was not usable here. It welds at 0.03 mm, which closed the grip / guard joint, and it moved the protected walls.
   - **Faired outlines.** The traced centre and guard outlines are now faired (`fair()`: clean_smooth plus pinned corners). The forend is not faired: fairing it left a sliver in the barrel channel.
   - **Grip** (`GRIP_SWELL`).
     - It is now moulded: the sheet's side outline is cut by a YZ lens. The half-width runs 14.6 at the tang, 16.4 at the palm swell, 15.6 at the waist and 17.2 at the flare.
     - Its edges get a 3.5 mm / 5-segment round. The outline corners, the top joint and the guard joint stay unrounded.
     - There are no finger grooves, because the sheet shows none.
2. **Finishes, in `sr_paint.py` and `sr_surface.py`.**
   - **OD Cerakote:**
     - The orange peel is now 1.3 mm cells, ±28 um in the normal map, so it reads in the sheen.
     - A slow roughness sheen drift is added.
     - Edge rub only appears in the caused zones; outside them it fades to 12 %.
     - Chips show dark hard anodize. Bright aluminium appears only at the core of large chips in high-contact areas.
     - Added handling polish (roughness −0.18 and slightly darker) and stronger recess dust.
     - The chip base rate is 0.04. New zones: grip area, and the riser top at 0.8.
   - **Bolt:** bead-blasted satin (lin 0.36-0.40, rough 0.48-0.60), with lathe bands and blast grain. The bipod inner legs are satin too.
   - **Small parts:** they no longer get bare-steel chips.
   - **Grip:** a hot-iron stipple of random pits about 0.75 mm wide, replacing the pyramid pattern.
   - **Hex sockets** are painted (BC, roughness and normal) on 66 socket-head faces.
   - **Scope:**
     - Generic turret markings: ticks every 9°, long ticks every 45° with numerals on elevation and windage, ticks only on the focus knob. No brand.
     - Lens: a green-black centre with a violet / amber coating ring and a convex normal. It is still the opaque-glossy slot (Q6).
     - The lens BC was first too dark for the B9 ≥ 30 sRGB rule, then lifted. Only the scope surface and export were re-run for that fix.
3. **Review rig**, in `sr_review_job.py` and `sr_review_export.py --table`.
   - A satin-grey tabletop sits under the lowest posed point, so the gun gets real contact shadows.
   - Depth of field: f/4 for the 35 cm and eyepiece views, f/8 to f/11 for the hero and 3 m views.

## Gates (from nothing; exported bytes)

All stage gates are back at W4's status.

| Gate | Status | Notes |
|---|---|---|
| form | partial | Only the W1-open L2 / L3 / L4 items. G5, B3, F1-F9, UD1 / UD2 and H1 all pass. H1 grip girth is 165.9, against a limit of ≤ 167 (W4: 161.1). LOD0 is 41,396 triangles (W4: 35,158; target 35-45k). |
| uv_bake_paint | partial | Only the two known B9 class-C near-misses. |
| scope_form, scope_export, game, rig_export, mag | PASS | |
| LOD sizes | pass | Per the viewgates log. |

### Side views (K10)

K10 passes, within its 0.001 IoU tolerance. GL lost 0.0008 IoU, from the grip round; this is declared.

| View | W4 | W4b |
|---|---|---|
| GR | 0.9603 | 0.9602 |
| GL | 0.9434 / 0.9513 | 0.9426 / 0.9505 |
| TOP | 0.8373 / 0.9015 | 0.8375 / 0.9020 |
| L3 | 3.0 | 3.0 |
| Per part on GR | 2/19 | 2/19 |

### Close-up gates (`gates/closeup_r1.json`, **status: fail**)

5 of 11 gates fail. They are reported as measured, and no threshold was moved to pass. I did fix two scripting bugs in the gate script itself:
- K9 read a `status` key that `game_lod_sizes.json` does not have.
- K11's image count is now taken from the job, not hard-coded.

| Gate | Result | Value |
|---|---|---|
| K1 hard creases on the chassis slot | **FAIL** | 15.9 m → 14.9 m; target ≤ 0.5×. The new rounds cover only the non-excluded edges, so many 90° creases remain, including the grip outline corners and the joints. |
| K2 bolt roughness | **FAIL** | P50 0.49 → 0.61 passes, but P5 is 0.39 against ≥ 0.45. The bolt through the port still shows a bright streak in fp_35cm. |
| K3 OD peel / rub / chips | **FAIL** | Normal tilt 0.31 → 0.44, short of the 2× target. Rub texels 121k → 10.8k (pass). Chips 1,216 (pass). |
| K4 bare metal on small parts | **FAIL** | 19,717 → 13,254 metallic texels. Another source than the phosphate chips remains; not traced. |
| K5 scope | pass | Roughness 0.60, 2,795 marking texels, convex lens 0.97. |
| K6 hex sockets and stipple | pass | |
| K7 table and depth of field | pass | |
| K8 sparkle | **FAIL** | fp_35cm has 6 isolated hot pixels, against a limit of 5. |
| K9 stage gates | pass | |
| K10 side views | pass | |
| K11 set complete | pass | 22 images. |

## Judges (independent, fresh, run once)

| Judge | W4 fix round | W4b |
|---|---|---|
| Realism A | fake 5/5 | **fake 8/8**, mean confidence 88 |
| Realism B | fake 5/5 | **fake 8/8**, mean confidence 89 |

Results are in `review/w4b/judges/realism_A.json` and `realism_B.json`.

**What the judges still want:**
- **Geometry artifacts.** Both judges named these. A: torn slivers on the grip and the grip base, jagged riser and pad edges, stepped stock seams, a wavy chassis underside, a crude trigger. B: a zig-zag at the forend nose, sawtooth / stepped forend edges, a wavy chassis edge near the well, and a thin mag release. These need a look; some are likely shading or edges left by the unclamped round, even though UD passes.
- **More wear and variation.** Fingerprints, dust, tone variation, and a bolt that is still too clean.
- **Optics.** Lens elements, a reticle and an exit pupil. These need the in-engine scope material (W5).
- **Backdrop and lights.** A real environment instead of the grey studio; the floor shadow has blotchy patches.

## Renders to look at

- `review/w4b/realism/`: `fp_35cm`, `ads_eyepiece`, `tp_3m`, `hero_34`, `deployed_34`.
- `review/w4b/set/`: `scope_close`, `eyepiece_view`, `fp_action`, the `close_*` 3x crops, `deployed_hero`.
- Compare against `review/w4fix/`.

## Blockers / notes

- **This round did not move the judges.** It fails decisively on realism (16/16 fake), so I stopped here, as instructed.
- **The judges' geometry complaints should be checked first.** The unclamped weighted round with exclusion boxes is a patchwork: 3 rounds of exclusions and slabs. Per CLAUDE.md, the next round should change method, for example a gunlib-level per-vertex clamped bevel or authored round profiles, rather than add more boxes.
- **Accidental Blender kill.** When I stopped the first chain (its form gates failed), I killed `blender.exe` by image name. Only one process was running, PID 214112, which was that chain's step. No other session's Blender was listed afterwards.
- **Leftover settings.** Env knobs remain in `sniper_parts.py` (`SR01_FAIR_*`, `SR01_ROUND_*`, `SR01_GRIP_*`, `SR01_CH_R`, `SR01_SHELL_FLAT`). The defaults are the shipped settings.
- **Scratch and probes.** Kept in `scratch/w4b/` (not in git). The chain scripts are `w4b_chain.sh` and `scope_redo.sh`.
