# SR01 W2 report: W1 follow-ups (Part A) + W2 surface (Part B)

**Date:** 2026-10-13. **Branch:** `claude/sniper-sr01` (worktree), nothing committed. **Lock:** `SR01` (claude).
Blender headless only; no rig, LODs, export or Unreal. Gate files are rebuilt from the built bytes:
`gates/form.json`, `gates/form_magfit.json` (W1, final form-stage bytes) and `gates/uv_bake_paint.json` + `gates/w2/`.

## User decision applied: bipod legs SPLAY 12 deg (2026-10-13)

- Real tension-swivel pattern. Each leg pin is rolled 12 deg about the leg's own axis (X through the hub, outboard
  side down), so the 0..90 swing carries the leg down and out. Deployed, each leg leans 12.0 deg out of vertical.
- Folded pose unchanged: legs lie along the forend as in the side views.
- The cheeks, pin bores, pins and the yoke's knuckle faces roll with the pins. The rolled cheeks are clipped 2.8 mm
  lower; at the old height they met the forend underside at cant +-15.
- **Why 12:** it is the middle of the 10-15 deg spread of fixed-splay swivel bipods. It gives about 3x the
  parallel-leg foot track at ext 0 (119 mm centres instead of 39), and the downhill leg never goes more than 3 deg
  past vertical at full cant.
- **Re-derived values** (spec `bipod.splay`, `ground_Z_deployed`, `foot_centre_track_deployed_mm`):
  - Ground Z by detent = -62.3 - 206 cos12 - 14 sin12 - ext cos12, which gives -266.71 / -285.29 / -303.88 / -322.46 /
    -341.05.
  - The built feet measure exactly that: -266.709 ... -341.05, coplanar 0.0, splay 12.0 / 12.0, outward.
  - Foot centre track at ext 0: 118.97 mm.
- Updated: `SR01_STUDY.md` (Q2 + an update section), `sr01_spec.json`, the plan's F3 line and
  `SR01_DESIGN_SHEET.png`. The sheet generator `tools/design_sheet.py` now draws the splay in the side and front
  views.
- **Full bipod sweep on the new geometry, all 0 intersections:**
  - fold 0..90 at ext 0 / 76 for both legs (1 deg, proof): min 0.167;
  - ext 0..76 folded and deployed: min 0.200;
  - cant +-15 folded and deployed (0.5 deg, proof): min 0.184.
  - F1-F9 all pass.
- Deployed hero re-rendered: `Renders/Guns/SR01/form_real_deployed_hero.png`,
  `form_real_scope_deployed_hero.png` and the textured `tex_deployed_hero.png` / `tex_bipod_close.png`.

## Part A: W1 follow-ups

| # | Item | Before | Now | How |
|---|---|---|---|---|
| 1 | UD1 Unreal-drop triangles | 647 (chassis 35, bolt_handle 361, magazine 241, butt_knobs 8, leg 2) | **0** on all 33 parts (min tri 0.0105 mm2) | at the source (below) |
| 2 | per-part L2 method | trigger / paddle 0.0 (painter's order) | z-buffer labels + a declared trace-label fix; real numbers below | `sr_silhouette.py` |
| 3 | L2 GR | 0.957 | **0.961** (pass >= 0.96) | riser top 32 -> 31; magazine floor sloped 5.4 deg (GR and GL both put the sheet's edge 1+ px off ours there) |
| 3 | L2 GL | 0.942 | 0.943 raw / 0.951 with the declared window (needs 0.958) | sheet problem, evidence below |
| 3 | L2 TOP | 0.837 / 0.902 | 0.837 / 0.902 (needs 0.93) | unchanged; the TOP conventions still need the user's call |
| 3 | L3 GR contour P95 | 4 px | 3.23 px (needs 2) | GL window out: 3.16 |
| 4 | riser post clearance | 0.140 | **0.160** (>= 0.15) | posts 4.98 (32-gon facet sag) |
| 4 | muzzle device gap (G5) | 0.0072 | **0.0152** min over 16 pairs (>= 0.01) | the gap was axial: device 0.02 further from the shoulder |
| 5 | whole chain from nothing | | `run_sniper.sh` ran clean; after the last two generator fixes (cant cheeks, device gap) the gate steps re-ran on the final form bytes | `scratch/w1/rerun_w1_gates.sh` (the run_sniper.sh gate steps on a byte copy, sha 17fe0c0d...) |

**UD1 source fixes:**
- **chassis:**
  - internal pockets and bores (inlet, raceway, channel, well, clevis, trigger pocket, pin bores, safety pocket,
    stem relief, screw seat) are cut after the 1.0 round, so the bevel never meets them;
  - guard outline at the centre's 1.3 tolerance;
  - inlet and channel overlap 1.34 mm, forend root box 2 mm into the clip, dovetail flank 0.6 into the side;
  - the forend box under the knob lowered 0.6;
  - a 0.016 mm weld of the boolean's near-duplicate vertex pairs. This is a generator step that moves a vertex by at
    most 0.008 mm. 0.02 made 2 multi-face edges, so 0.016 was chosen.
- **bolt_handle:** stem + ball as one revolve (no ellipsoid union, no bevel modifier). The boss runs 2 mm past the
  stem's base disk.
- **magazine:** a lofted body with its 0.6 chamfers as geometry, square feed lips, the top round's nose square at r 2.8.
- **butt_knobs:** the flutes run through both cap chamfers.
- **leg:** the lock button is seated 1 mm deeper.
- **Still failing:** UD2 (a margin gate) is 3 / 4 / 2 on the chassis. It is the only part left outside the repair
  pass, which stays skipped there because it moved gate-critical surfaces.

**Per-part GR L2 (z-buffer, 2 / 19 >= 0.95):**
- **>= 0.95:** butt_pad 0.962, scope 0.961 (stand-in).
- **0.90-0.95:** grip 0.947, magazine 0.936, device 0.926, chassis_forend 0.910.
- **0.75-0.90:** chassis_centre 0.877, barrel 0.803, bipod 0.792, guard 0.758.
- **0.45-0.75:** riser 0.738, pad_plate 0.679, rail 0.660, butt 0.581, receiver 0.460.
- **Below 0.45:** bolt_handle 0.352, bolt_shroud 0.281, trigger 0.0, paddle 0.0.

What covers the missed pixels shows that most misses are label disagreements, not silhouette errors:
- the receiver's label is covered by our rail (335 px), our bolt through the port (289) and the chassis (265);
- the butt's label is covered by our riser skirts (204);
- the forend's label is covered by our barrel (290; the barrel OD is Q3);
- the bolt_handle's label is covered by the chassis wall (242).

Real geometry offsets:
- **trigger:** the trace's 'trigger' label also carried the guard's bottom bar (65 px, now dropped, declared). The
  blade itself is drawn about 3 px (5-6 mm) behind ours. Ours sits on the spec pivot X 368 (F9 / H1 reach 49 mm), so
  this is left for the user's call.
- **paddle:** it sits behind the chassis side wall (declared in W1).
- Evidence: `scratch/w1/sil_form.json` (`missed_px_covered_by`), `scratch/w1/l2_columns.json` (per-X top / bottom in
  GR and GL), `scratch/w1/dbg_trigger.png`, `dbg_confusion.png`.

**Why GL can't reach 0.958 (sheet problem):**
- The sheet's GL silhouette is 602 px (1.8 %) smaller than its GR for the same object. Ours differ by 108 px.
- GL draws the forend underside (X 555..700) 5-13 mm higher than GR, and GR matches the build there within 1 px.
- The barrel top jitters 1 px between the views.
- With only that band left out, GL is 0.951. Fitting GL beyond that would break GR.
- GR was tuned only where both views agree we were off.

The TOP stays non-authority with the declared conventions (needs the user's call, as in W1).

## Part B: W2 surface (gun + scope attachment)

**Chain:** `Scripts/guns/sniper/run_surface.sh` runs these steps from the gated form-stage blend:
1. UV0 by class
2. UV1 + UD4
3. bakes
4. paint
5. Detail16 / recolour pre-check
6. Blender-side gates
7. the same for the scope (`SR01_SURFACE_TARGET=scope`)
8. renders from the baked maps
9. L5
10. `gates/uv_bake_paint.json` + `gates/w2/`

Three copies of the form-stage blends are kept: `scratch/w2/SR01_form_stage.blend`,
`scratch/w2_scope/Att_Scope_form_stage.blend`, and `scratch/w1/SR01_form_final.blend` for the W1 gates.

**Ported from the SMG** by `tools/port_w2.py` (read-only use of `Scripts/guns/smg`): `sr_uv.py`, `sr_uv1.py`,
`sr_lmpack.py`, `sr_uvproj.py`, `sr_ud4.py`, `sr_bake.py`, `sr_w2_blender.py`.

**New sniper-side scripts:**
- `sr_surface.py`: sets, classes, finishes and wear causes.
- `sr_paint.py`
- `sr_recolour.py`
- `sr_l5.py`
- `sr_w2_gates.py`
- `sr_render.py` gained a `tex` look, the studio rig and the L5 panel render.

**Gates: 57 / 61 pass.**

**UV sets** (the packer picked every size; the x2.3 lesson held):

| Set | Size | Fill | Class densities, median px/cm |
|---|---|---|---|
| Metal | 2048 | 0.774 | B 74.4, C 37.1, D 28.2, E 12.2 |
| Chassis | 4096 | 0.679 | B 100 (at the 1.25 x ceiling), C 50, E 16.4 |
| Mag | 1024 | 0.749 | C 50, E 16.4 |
| Scope_Body | 2048 | 0.491 | A 118.8, C 48.4, E 18.0 |
| Scope_Lens | 512 | 0.510 | |

- UV0: 0 overlaps, 0 flipped, everything in 0..1.
- UV1 authored lightmap: UD4 PASS at 64 / 128 px, 2 px padding (gun and scope).
- **qa_check on the static twins passes:**
  - SM_SR01: 35,080 tris, 3 slots on U tiles 0 / 1 / -1, UV1 present, 75.4 px/cm aggregate.
  - SM_Att_Scope_LongRange: 5,884 tris.
- UD1 is 0 on both twins.

**Bakes:**
- margin 0 on every pass;
- the magazine's AO and edge passes see the magazine alone;
- the gun's AO is baked with the magazine out;
- OptiX GPU, 256 AO samples.

**Paint:** separate value and roughness per family (gate passes, no indistinct dark pair). Painted medians, sRGB /
roughness:

| Family | Base sRGB | Roughness |
|---|---|---|
| OD | 84/85/72 | 0.62 |
| anodize | 55 | 0.43 |
| phosphate | 55-62 | 0.80-0.84 |
| barrel phosphate | 47 | 0.70 |
| device | 36 | 0.76 |
| polymer | 44/44/46 | 0.60 |
| rubber | 38/38/40 | 0.91 |
| bolt (bare steel, metal 1) | | 0.36 |
| scope anodize | 31 | 0.29 |
| lens (coated violet-black) | | 0.05 |

Wear by cause:
- **OD:** chips on sharp edges only in the cause zones: 1,546 texels, 114 of them bright aluminium cores. Edge rub
  covers 120 k texels.
- **Anodize:** wear lines, 1,023 texels.
- **Phosphate:** bare steel only at named contact edges: 277 texels on Metal, 204 on Mag.

Other paint content:
- the shroud is phosphate;
- the bolt ball is checkered (1.3 mm);
- the grip has its own pyramid panel (360 k texels);
- soot at the device exit and bore.

**Masks and recolour:**
- `T_SR01_*_Masks`: A = 1 on 100 % of OD texels and on 0 texels of any other finish (all sets).
- Detail16 written: `Exports/Guns/SR01/Textures/Recolour/`.
- Recolour reconstruction on the OD is p99.9 2.66 levels.
- Maps: `Exports/Guns/SR01/Textures/T_SR01_{Metal,Chassis,Mag}_{BC,ORM,N,Masks}.png` and
  `T_Att_Scope_LongRange_Scope_{Body,Lens}_*`. All are POT.

**L5: 12 / 12.**
- Panel-matched GR render from the maps, physical rig, one light k = 1.255 fitted on the forend OD.
- The OD renders 88/89/78 against the sheet's 88/88/78 (spec about 89/89/78).
- Grip, pad, barrel, magazine, receiver, butt, riser, device, rail and bipod are all within luma +-0.05 / sat +-0.05.
- The rail is near black (sat not tested under 30 levels, declared). The scope is in the L5 render, because the
  sheet's rail is in its shadow.

**Markings:** not delivered. The S / F stamp selected the safety pocket and painted 0 texels. Generic markings stay
allowed (no maker / model / serial anywhere).

**Fails (declared, not decisive):**
- **B9 uniformity, two near-misses:**
  - Metal class C P5 31.3 vs 31.5 needed;
  - scope class C P5 40.9 vs 41.1.
- **Scope fill:** 0.49 against a declared 0.45 minimum. The ceiling caps the scale and 1024 can't hold the floors.
- **UD2 on the chassis:** 3 / 4 / 0.
- **UD3 float32 zero-tangent corners:** 8 (barrel 4, chassis 2, clamp 1, swivel 1). These must be 0 before the W3
  export.

## Realism judges (one pass, two independent judges) and the one fix round

**Round 1: both judges FAKE on all 7 views each** (`scratch/w2/judges.json`; the pre-fix renders are in
`review/w2_r1/`). Common tells:
- the dark parts read as one charcoal;
- the OD showed no micro-texture or edge rub;
- the wear looked like draped blotches (barrel oil field, grip polish mottle, butt clouds);
- the bolt read as mirror chrome;
- the knob was a plain sphere.

Geometry tells for W4b:
- fin-like rail teeth (the gunlib rail);
- faceted scope rings, turrets and eyepiece;
- faceted forend flats.

**Fix round** (`tools/w2_fix_round.py` + the shroud / device / knob edits):
- families separated;
- OD peel +-14 um at 0.65 mm with a sheen split;
- rub on every exposed edge and more chips in the zones;
- the blotch fields removed;
- the bolt honed 0.24-0.36 with machining lines;
- the knob checkered;
- the device darker;
- the scope gloss-black and the lens coated.

One L5-driven correction after that: the anodize went back to near-neutral, because the blue tint failed the
sheet's neutral bipod.

The post-fix renders were **not re-judged**: the brief allows one pass. My read is that the surfaces are clearly
better but still clean. Wear stays sparse at hero distance, so close-up realism is W4b work.

## Renders to look at (all from the baked maps, studio-HDRI rig)

- `Renders/Guns/SR01/tex_q34.png`, `tex_deployed_hero.png` (splayed legs), `tex_fp_action.png`,
  `tex_action_close.png` (checkered knob, phosphate shroud), `tex_scope_close.png`, `tex_bipod_close.png`.
- Orthos: `tex_right.png`, `tex_left.png`, `tex_top.png`.
- Pre-fix comparison: `WorkFiles/guns/sniper/review/w2_r1/`.
- L5: `WorkFiles/guns/sniper/scratch/w2/l5/side_k1.255.png`.
- W1 form renders (re-rendered on the final bytes, splay): `Renders/Guns/SR01/form_real_deployed_hero.png`,
  `form_real_scope_deployed_hero.png`.

## What is left

1. **UD3 (8 corners) and UD2 (chassis)** at the generator or the UV stage, before the W3 export.
2. **Markings:** place S / F on the visible chassis face beside the safety (and rail slot numbers if wanted).
3. **B9:** a per-island scale normalisation for the two class-C near-misses (W3 UV item).
4. **W4b close-up realism:**
   - more visible use-wear;
   - the scope's geometry facets;
   - rail tooth chamfers (a gunlib proposal);
   - the forend flats' shading;
   - a re-judge.
5. **The user's calls:**
   - the TOP conventions (L1 / L2 TOP);
   - whether to move the trigger blade ~5 mm back to the drawn one (H1 / F9 re-check);
   - the GL sheet issue (accept the declared window).
6. W3 (rig, LODs, export) is not started, as instructed.

## Spend

About $25 of this run's $45 cap (Part A about $10, Part B about $15). Long Blender waits past the 5-minute prompt
cache cost about $2 per wake-up.
