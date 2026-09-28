# Kunai blade section: options A / B / C (phase 1, for the user's pick)

**Date:** 2026-09-26. **Status:** prototypes built and measured. **Nothing in the live pack changed.** `Assets/`, `Exports/`,
`Renders/`, `Scripts/`, `WorkFiles/shuriken/` and `WorkFiles/locks/` have the same timestamps and sizes as before the
run (`tmp/live_before.txt` = `tmp/live_after.txt`). No Unreal was run. Blender ran headless only.

Contact sheet: `blade_section_options.png`. Machine-readable figures: `options_data.json`.

## 1. How the prototypes were made

- `proto_tree/` is a copy of `Scripts/shuriken` + `Scripts/pipeline`, laid out so the library's `PROJECT` resolves to
  `proto_tree/`. Nothing defaults into the live tree, and every output path was also passed explicitly (`run_build.sh`).
- Only the section changed, in three places:
  - `kunai_spec.py` reads an option file (`KUNAI_SECTION_JSON`) for `RIDGE_BASE`, `RIDGE_TIP`, `RIDGE_TIP_AT` and
    `EDGE_T`. It adds two things a deeper ridge needs:
    - `RIDGE_RAMP`: a ridge above the 5 mm neck stock has to meet the flat plateau at the plunge at 5 mm, so it
      rises from 5.0 at x = 5 to its peak.
    - `RIDGE_KNOTS`: extra knots in the front taper.
  - `kunai.py`: the head hull samples the ridge at those knots as well, only when an option file is set.
  - `build_kunai_plain.py`: the mass-gate target and study basis come from the option file. `LOD1_BASE_INTERVALS`
    gives LOD1 LOD0's base stations under a ramped ridge (+40 LOD1 triangles).
- **Proof the copy is faithful:** built with no option file, the proto tree reproduces the shipped kunai. The extracted
  report figures are identical to `WorkFiles/shuriken/kunai_plain_report.json` (masses, pivot, hulls, LODs, gates,
  hero and top coat), and the sockets sidecar is byte-identical. The FBX bytes differ only in its header. The 3/4 render
  reproduces `Renders/Shuriken/kunai_plain_3q.png` (mean abs diff 0.00005 / 255).
- **Each option:** `build_pack.py --forms kunai_plain` ran with the **full** bake and all gates, at 1-2.5 min per build.
  The study basis was re-run with the option's section (`calc/study_basis.py`, a copy of `plain_calc` arithmetic), and
  that sets the mass-gate target. After the build:
  - `measure_mesh.py` takes true LOD0 sections at the stations, and LOD1/LOD2 ridge fidelity.
  - `ours/render_photo_pose.py` renders the photo's pose.
  - `render_3q.py` renders the 3/4 pose (`kunai_plain_3q.png`'s own rig: yaw 40, 72 mm, el 29 / az -22, hero lamps x
    2.724318, 160 spp), the build's end-on hero and the top view. For each it records the coat statistics, the
    flat/tilted split and a uniform reference-coat render.

## 2. The three options

| | Current (3.10.1) | **A** deeper at 5 mm stock | **B** match the photo ratio | **C** full diamond, forged thickness |
|---|---|---|---|---|
| Ridge (full thickness) | 5.0 to x 35, then to 1.6 at x 135 | **5.0 held to x 63.6**, then to 1.6 at x 135 | 5.0 at x 5, up to **9.0** at x 24.4, held to x 35, then to **2.7** at x 135 | 5.0 at x 5, up to **7.0** at x 24.4, held to x 35, then to 1.6 at x 135 |
| Un-ground edge flat `EDGE_T` | 1.5 mm | **0.6 mm** | 1.5 mm (kept) | **0.3 mm** (faces run to the grind) |
| Max blade thickness | 5.0 mm | 5.0 mm | 9.0 mm | 7.0 mm |
| What moved | - | edge flat 1.5 to 0.6; ridge held at 5.0 from x 35 to x 63.6 | ridge peak 5 to 9, ramp, tip 1.6 to 2.7; LOD1 base stations 1 to 3 | ridge peak 5 to 7, ramp; edge flat 1.5 to 0.3; LOD1 base stations 1 to 3 |

### 2.1 Section, measured on each option's own LOD0 mesh

face_slope = (ridge half-thickness - edge half-thickness) / half-width. The photo figures are the reconciled
measurements (`ours/photo_reconciled.json`). Brackets give option / photo.

| Station (frac of visible blade, our x) | Photo | Current | A | B | C |
|---|---|---|---|---|---|
| 0.10, x 13.4 (rear) | 0.325 | 0.148 (0.45) | 0.186 (0.57) | 0.222 (0.68) | 0.236 (0.73) |
| 0.20, x 26.7 (rear) | 0.237 | 0.112 (0.47) | 0.141 (0.59) | 0.240 (1.01) | 0.214 (0.90) |
| 0.30, x 39.4 | 0.175 | 0.096 (0.55) | 0.126 (0.72) | 0.207 (1.18) | 0.186 (1.06) |
| 0.45, x 56.7 | 0.185 | 0.092 (0.50) | 0.147 (0.79) | 0.204 (1.10) | 0.184 (0.99) |
| 0.60, x 74.1 | 0.215 | 0.088 (0.41) | 0.158 (0.74) | 0.204 (0.95) | 0.186 (0.87) |
| 0.75, x 91.4 | 0.217 | 0.084 (0.39) | 0.163 (0.75) | 0.209 (0.96) | 0.193 (0.89) |
| 0.90, x 108.7 (least reliable) | 0.228 | 0.079 (0.35) | 0.179 (0.78) | 0.227 (0.99) | 0.216 (0.95) |
| **Front median (0.30-0.90)** | **0.215** (0.15-0.27) | 0.088 | 0.158 (0.73x) | **0.207 (0.96x)** | **0.186 (0.87x)** |
| Face angle mid-blade (x 56.7) | 10.5 deg | 5.2 deg | 8.3 deg | 11.5 deg | 10.4 deg |
| ridge_ratio at x 56.7 | 0.235* | 0.142 | 0.167 | 0.254 | 0.194 |
| Grind band in plan at x 35 | not resolvable | 1.12 mm | 0.39 mm | 1.38 mm | **0.15 mm** |

\* The photo's ridge_ratio assumes our 1.5 mm edge. With a sharp edge it equals the face_slope.

All three options fall inside the photo's honest range (0.15-0.27) on the front. A is at its lower end. B is the
closest match, and C is close to it.

### 2.2 Mass, balance, collision, LODs (each option's own build report)

| | Current | A | B | C |
|---|---|---|---|---|
| Steel, un-ground (mass-gate basis) | 151.89 g | 146.17 g (-5.7) | 185.61 g (+33.7) | 153.34 g (+1.5) |
| Mass-gate target (study basis re-run with the section; was 153.02) | 153.02 g, error -1.13 | **146.98 g**, error -0.81 | **186.17 g**, error -0.56 | **154.06 g**, error -0.72 |
| Steel, finished | 149.04 g | 144.64 g | 182.07 g | 151.96 g |
| **Assembled** (study plain range 164.8-170.0; replicas 140-283) | 161.93 g | 157.53 g (-4.4) | **194.96 g (+33.0)** | 164.85 g (+2.9, now inside the study range) |
| Physics override | 0.1619 kg | 0.1575 kg | 0.1950 kg | 0.1648 kg |
| Pivot (mass-weighted centre), design x | -20.52 mm | -22.08 mm (1.6 mm toward the ring) | **-8.10 mm (12.4 mm toward the tip; 2.1 mm inside the wrap's front)** | -19.59 mm (0.9 mm toward the tip) |
| Unreal COM offset | +3.04 cm | +2.95 cm | +3.59 cm | +3.10 cm |
| Head hull (UCX_00) | 10,356 mm3, 26 v | 9,985 mm3, 28 v | 14,716 mm3, 26 v | 10,739 mm3, 30 v |
| Two hulls total | 60,316 mm3 | 59,946 | 64,677 | 60,699 |
| Hulls contain every LOD vertex | yes | yes | yes | yes |
| Grind apex (grind reaches the ridge) | x 135.2 | x 135.2 | **x 130.5** | x 135.2 |
| Grind plan width, plunge / x 35 / x 90 / x 130 | 1.35 / 1.12 / 1.10 / 1.06 | 0.51 / 0.39 / 0.42 / 0.56 | 1.35 / 1.38 / 1.38 / 1.98 | 0.18 / 0.15 / 0.15 / 0.23 |
| Material edge band (tag `chamfer_w` = 0.95 x grind at x 130) | 1.01 mm | 0.53 mm | 1.88 mm | **0.22 mm (~3 texels)** |
| LOD triangles | 2182 / 696 / 366 | 2182 / 696 / 366 | 2182 / **736** / 366 | 2182 / **736** / 366 |
| LOD2 ridge vs LOD0 (worst) | -0.15 mm | -0.19 mm | **-1.29 mm at x 25** | **-0.63 mm at x 25** |
| Two-sided LOD deviation (max; set by the grip) | 0.63 / 1.18 mm | same | same | same |
| Blade texel density (area-weighted) | 13.21 px/mm | 13.25 | 13.07 | 13.23 |
| Unreal bounds (the 20 mm grip is the thickest part) | 28.0 x 3.6 x 2.0 cm | same | same | same |
| Geometry gates: qa_check (62), hulls, UV (0 overlaps, tiles, no collapsed faces), LOD bands, mass gate, slots, lettering, franchise names, knife shading | all pass | all pass | all pass | all pass |
| Render gates today | pass | pass | **top_plate FAIL** (coat 0.354 / 0.359) | **top_plate FAIL** (mean 0.370 < 0.38) |
| pack_consistency today (end-on hero / top, coat p50 vs anchor) | pass (-0.025 / -0.009) | pass (-0.046 / -0.029; 0.001 headroom on the hero mean) | **FAIL** (-0.081 / -0.076) | **FAIL** (-0.073 / -0.057) |

## 3. The hero gate (the 3/4 pose) and a principled knife rule

**The situation.** The user chose the 3/4 diagonal as the kunai's main picture. Today's rule compares the kunai's
coat pixels (every face with |N.z| >= 0.95) with `PACK_COAT_ANCHOR`, the anchor stars' plate pixels (hero p50 0.560 /
mean 0.550, tolerance 0.05). In the 3/4 pose, every blade fails that rule, including today's:

| 3/4 pose (yaw 40, `kunai_plain_3q.png` rig) | Current | A | B | C |
|---|---|---|---|---|
| All coat p50 / mean | 0.420 / 0.424 | 0.309 / 0.330 | 0.236 / 0.280 | 0.254 / 0.285 |
| vs anchor (today's rule) | -0.140 / -0.127 **FAIL** | -0.251 / -0.220 **FAIL** | -0.324 / -0.270 **FAIL** | -0.306 / -0.266 **FAIL** |
| Flat coat (\|N.z\| >= 0.9995: ring flats, neck plateau, rear neck), p50 / mean | 0.541 / 0.532 (5,032 px) | 0.541 / 0.532 | 0.535 / 0.526 | 0.541 / 0.531 |
| Flat coat vs anchor | -0.019 / -0.018 | -0.019 / -0.018 | -0.025 / -0.024 | -0.019 / -0.019 |
| Tilted diamond faces, p50 | 0.416 | 0.299 | 0.235 | 0.254 |
| Finish transfer: (baked - uniform reference) on tilted minus on flat, p50 / mean | +0.004 / +0.006 | +0.016 / +0.014 | +0.015 / +0.026 | +0.020 / +0.021 |
| Coat below 0.03 (the hole gate, max 0.02) | 0.0007 | 0.0006 | 0.0004 | 0.0005 |

In the top (spec) view:
- The flat coat reads 0.429 / 0.425 in every option (anchor 0.430 / 0.424).
- The tilted faces read 0.420 (current), 0.398 (A), 0.350 (B) and 0.366 (C).
- The finish transfer is within 0.004 for all four.

**Why today's rule fails, and why that is geometry, not finish.** The anchor was measured on flat plates. A satin
metal's brightness depends on which part of the rig its normal mirrors. The diamond faces are tilted 5-13 deg, so in
the 3/4 pose they mirror the darker side of the rig: the deeper the ridge, the darker. The uniform reference-coat
render (the pack's nominal coat, `material.COAT`, metallic 1, roughness 0.34, on the same mesh in the same pose) reads
the same darkness. The baked blade sits within 0.03 of it, exactly as the flat plates do. So the gap is the rig and the
geometry, not the material the gate exists to protect.

**Proposed knife rule** (applies to `consistency_class == "knife"` only, so the six stars and the spike stay a no-op):
1. **Orientation-matched anchor (like with like).** Coat pixels within 1.8 deg of flat (|N.z| >= 0.9995), the anchor
   plates' own orientation, are compared with `PACK_COAT_ANCHOR` on p50 and mean, tolerance 0.05, in the hero and in
   the top view. It needs at least 2,000 such pixels (the 3/4 has ~5,000).
2. **Finish transfer on the tilted faces.** The same frame is rendered again with the uniform reference coat. The
   tilted faces' (baked - reference) must equal the flat faces' (baked - reference) within 0.05 on p50 and mean. This
   gates the blade's own finish at its real angle with the geometry and light cancelled.
3. **The hole gate stays:** at most 2 % of coat pixels below 0.03.
4. The whole-object and all-coat figures stay reported as information, as they are today for the knife's whole object.

**Why this is not a relaxation:**
- Every comparison stays like with like at the same 0.05 tolerance.
- Part 2 adds a check that does not exist today: today a mis-baked blade island could hide inside an averaged coat.
- Part 1 is stricter where it matters. On today's end-on hero (yaw -25), the flat coat reads 0.479 / 0.412 (-0.08 /
  -0.14). That is the neck plateau mirroring the dark grip, the "black slot" the 3.10.1 review found. The rule would
  have failed that pose, while today's averaged rule passed it.

All four sections pass it in the 3/4 pose and in the top view:
- Flat -0.019 to -0.025.
- Finish transfer +0.004 to +0.026.
- Hole 0.0004-0.0007.

The same split replaces `hero_plate` / `top_plate` for a knife. That is what C's and B's `top_plate` failures come from.

**A presentation note (not a gate).** In the 3/4 pose, B's and C's blade faces read darker than today's: tilted p50
0.24-0.25 against 0.42. In the photo, one facet catches the light and the other falls dark, and that contrast is what
sells the ridge. The rebuild can try a few yaws around 40 deg, or the key's placement, so one facet catches the key. The
knife rule above holds whichever yaw is chosen.

## 4. What each option would need in the rebuild (phase 2)

All options need these steps:
- Put the section into `Scripts/shuriken/shuriken_lib/kunai_spec.py`, as proper constants rather than the prototype's
  JSON hook. Add the ridge knots to the head hull in `kunai.py`.
- Re-run `WorkFiles/kunai/plain_calc` with the new section for the new mass-gate target, and update the study
  section 4 table.
- Add the knife coat rule to `render.py` (`plate_gate` / `pack_consistency` for class `knife`). Prove it is a no-op
  on the six frozen forms.
- Make the 3/4 pose the gallery hero (`kunai_plain_persp.png`), with the line-sheet panel.
- Build with `build_pack.py` and `--frozen-maps`. Run the frozen-forms regression (six forms identical), Unreal
  UnrealCheck6 on the exact bytes (one UnrealEditor-Cmd at a time), the pack materials rebuild, the study, the report
  and the backup.

Per option:
- **A:** nothing else. The grind band narrows from 1.1 mm to 0.4 mm, and the material's polished edge band from 1.0 mm
  to 0.5 mm.
- **B:**
  - LOD2 needs a second base station: its ridge is 1.29 mm thin at x 25.
  - The 9 mm blade moves the balance to the grip's front edge (pivot x -8.1).
  - The apex moves back 4.7 mm (x 130.5), and the grind widens to ~2 mm near the tip.
  - Heaviest: 195 g assembled.
- **C:**
  - LOD2 needs a second base station: its ridge is 0.63 mm thin at x 25.
  - The grind becomes a 0.15 mm line and the material edge band 0.22 mm (~3 texels at 13.4 px/mm). Check it for
    aliasing in the hero.
  - An untested knob if a visible band is wanted: `EDGE_T` 0.5 would give a ~0.3 mm band for about -0.01 of face slope.

## 5. Recommendation (the user picks)

**C.**
- It reaches 0.87-1.06x of the photo's front face slope (median 0.186 against 0.215; 10.4 deg mid-blade against the
  photo's 10.5 deg).
- It does so at 7.0 mm, the forged replicas' range (6.35-8 mm in the research sources).
- It costs +1.5 g of steel (assembled 164.8 g, now inside the study's plain range for the first time).
- The pivot moves 0.9 mm, the head hull grows 4 %, and every geometry gate passes.

Its one real cost is the look of the edge: the 1.1 mm grind band becomes a 0.15 mm bright line.

**B** is the literal ratio match (0.96x), and it keeps the grind band. But it needs a 9 mm blade, +33 g and the balance
12 mm forward. That is thicker than any kunai source except one 8 mm thrower, and it changes how the item throws.

**A** changes least and passes every gate today. But at ~0.73x of the photo it is still visibly shallower than the
reference, which is what the user asked to fix.

## 6. Files

- `blade_section_options.png`: the contact sheet.
- `options_data.json`: every figure above.
- `<id>/`:
  - `section.json`, `study_basis.json`, `build.log`.
  - `report/kunai_plain_report.json` and `pack_report.json`.
  - `export/` (FBX, sidecar, textures), `renders/`, `diag/`.
  - `mesh_measure.json`.
  - `views/`: `photo_pose.png`, `kunai_3q_y40.png`, `kunai_hero_y-25.png`, `kunai_top_y0.png`, masks, reference
    renders, `kunai_3q_stats.json`.
  - `extract.json`.
- `sections/`: the end-on section diagrams.
- Scripts:
  - `run_build.sh`, `run_renders.sh`, `render_3q.py`, `measure_mesh.py`.
  - `make_sections.py`, `collect.py`, `make_sheet.py`.
  - `calc/`: `secmod.py`, `explore.py`, `study_basis.py`, `extract.py`, `section_post.py`, plus copies of the study
    and plain-calc scripts.
- `proto_tree/`: the prototype generator copy.
- `tmp/live_before.txt` and `tmp/live_after.txt`: the live-tree check.

The reference photo appears only on the contact sheet, a WorkFiles diagnostic. No pixel of it is used in any asset.
