# Round 2: Unreal polish (DojoLab, 2026-09-28)

This round fixed three failures from the showcase verify. It changed nothing in Blender assets.
Run: `run_showcase_unreal.sh prep import materials level verify capture`, then the Blender walk, climb and roof-walk checks.
Result: verify passes 7 of 7 gates (gate 7, the in-engine GASP trace, is new). Walk passes 15/15 routes with 8/8 controls blocked, climb passes every route, and roof walk passes 6/6.

## 1. Colour cast: the cause was lighting and post, not the materials

The probe script `Scripts/dojo/unreal/dj_sc_colour_probe.py` puts cards into the level in memory and never saves.
- It uses neutral grey 18 % cards, the kit's own tile and plaster BC textures, and unlit neutral emissive cards.
- The cards are placed in sun and in the wall's shade.
- Probe runs 1 to 4 are in `probe1..4/`, with the card numbers in `probe_cards.json`.

What the probes showed:

**Materials are clean.**
- Every texture was imported with the right flags (BC sRGB, ORM and N linear), and the verify gate passes.
- Source BC means are neutral: RoofTile (73, 74, 77) and EarthPlaster (158, 133, 103).

**Post.** The grade (colour gain (1.06, 1, 0.9) with saturation 0.85) tinted an unlit neutral card from (145, 145, 144) to (153, 144, 134). That is a global orange filter.

**Sun.** UE's atmosphere sun already reddens a sun at 13 degrees.
- At 6500 K a lit grey card reads (183, 153, 105), about Blender's sun colour.
- The old 4300 K on top of that gave saturation 0.59.

**Sky.** The sky luminance factor was (3.4, 2.6, 2.1), so the sky-light fill was orange: a grey card in shade read (25, 15, 7).
- With the physical sky at factor 1, the shade card is almost black: (0, 1, 6).
- The Blender world is a strong lilac fill.

**Lamps.** The lamps are photometric conversions of the Blender review lights. The exposure is +2.0 EV over the analytic Blender parity, so the lamps came out 4x too strong: the gate posts and ceiling glowed orange.

**Offscreen sky light.** In the offscreen editor, the real-time sky light does not follow changes made after load. The probe therefore recaptures the sky (test B1 against B1b). A fresh load captures correctly, and the final captures confirm the probe's numbers.

**Fix.** The values are in `dj_sc_common.py` and the layout:

| Setting | Before | After |
|---|---|---|
| Sun | 4300 K | 5500 K |
| Sky luminance factor | (3.4, 2.6, 2.1) | (2.6, 1.8, 1.6) |
| Sky light intensity | 1 | 6 |
| Grade gain / saturation | warm | neutral 1.0 |
| Lamps (candela) | x 1 | x 2^-2.0 (0.25) |

Exposure, bloom and vignette are unchanged.

**Measured result.** sRGB means of each region. Round 1 was saturation 0.95 on the tiles. The Blender values come from the kit1_f2 beauty render and ground C_Establish; the lighting there is similar but not identical.

| Region | Round 1 | Round 2 | Blender |
|---|---|---|---|
| Gate tiles | (29, 9, 2) s0.95 | (37, 27, 29) s0.28 | (38, 32, 38) s0.15 |
| Plaster | (118, 40, 5) s0.96 | (154, 105, 69) s0.55 | (101, 66, 52) s0.49 |
| Sky | (168, 154, 132) s0.22, beige | (134, 131, 147) s0.10, lilac | (182, 177, 193) s0.08 |
| Sand, gate view | (219, 155, 80) s0.64 | (216, 190, 167) s0.23 | n/a |
| Sand, establishing view | (242, 177, 93) s0.62 | (221, 186, 154) s0.30 | (193, 160, 132) s0.32 |
| Path | (181, 106, 43) s0.76 | (163, 134, 128) s0.22 | (150, 124, 108) s0.28 |

Probe D4, which is the chosen setting:
- An 18 % grey card in shade reads lilac (104, 98, 117).
- A sun-lit card reads warm (206, 178, 152).

The result is a warm key with cool-lilac shadows, not a global orange filter. The files are `before_regions.json` and `after_regions.json`, and `regions_*.png` shows the measured boxes.

**Still open.**
- The sky is darker than Blender's (134 against 182).
- Reference 2's golden horizon glow is not reproduced; the sky is flat lilac-grey.
- The grey-box outside ground and the tree read green or yellow now that the filter is gone. These are grey-box flat colours.

## 2. Nanite bounds

`dj_sc_import.py` now sets `fallback_target` to RELATIVE_ERROR with relative error 0.
- It does this on every run, including meshes that the manifest skips.
- Before this, the error value was ignored while the target was AUTO, so the fallback was decimated.
- All 38 of 38 meshes now match: fallback triangles equal the source and Blender triangles, and the fallback box is off by 0.000 cm (`nanite_fallback_probe.json`).

**Finding: the render bounds are still 0.5 to 27.6 cm larger, and settings cannot change that.**
- In UE 5.8, a Nanite mesh's bounds are `ClusterDAG.TotalBounds`. That is the union of the cluster boxes of every level of the Nanite DAG, including the simplified levels.
- Engine source: `NaniteEncode.cpp` `CalculateMeshBounds`, and `ClusterDAG.cpp:1115` `TotalBounds += Bounds`.
- So the fallback was not the cause, and no Nanite setting shrinks these bounds. They are only culling bounds.

**How the gates measure Nanite actors now.** The level and verify gates measure the rendered geometry (`dj_sc_nanite.py`): the full-detail fallback's vertex box, carried through the actor transform, against Blender.
- Maximum error across 139 Nanite actors: 0.0005 cm.
- Maximum error for non-Nanite actors: 0.477 cm.
- The culling-box inflation is still reported, per piece, in `level.json` and `verify.json`.

## 3. Markers

`Scripts/dojo/showcase/marker_policy.py` holds the marker rules. `compose_showcase.py` uses it, and `apply_round2.py` (the runner's `prep` step) applies it to the existing layout. The round-1 layout is kept in `layout_showcase_before_round2.json`.

- **TRV_Landing_PavilionPad:** bottom raised from +1.25 to +1.50. GASP's trace capsule from the courtyard reaches +1.484 at most.
- **TRV_Wall_S_W2 and TRV_Wall_S_E1:** removed. Kit 1's gate frame and 0.49 m gate joins stand there now, and the joins are shorter than the 0.60 m minimum ledge. No route used these markers. The level has 26 markers now.

**climb_check.py** now tests the first marker the sweep reaches among all markers (a start-penetrating overlap counts as distance 0).
- Run on the round-1 layout, it reproduces the in-engine failure: the plinth route reaches Landing_PavilionPad first (`climb_check_old_layout_new_logic.json`).
- On the round-2 layout, every route passes.

**Verify gate 7** runs the in-engine Traversable capsule trace from all 20 marker routes. Every route hits its own marker first; the plinth route hits TRV_Pavilion_Plinth.

## Files

**Captures:**
- `captures_after/CAM_*.png`: the same 10 cameras as round 1.
- `before/captures/`: the round-1 captures.
- `BEFORE_AFTER_SHEET.png` and `SBS_COLOUR.png`: comparison sheets.

**Scripts changed:**
- `dj_sc_common.py`, `dj_sc_level.py`, `dj_sc_verify.py`, `dj_sc_import.py`, `run_showcase_unreal.sh` (new `prep` step), `run_sc_capture.ps1` (new `-Script` and `-LogName` options).

**Scripts added:**
- `dj_sc_nanite.py` and `dj_sc_colour_probe.py`.
- `showcase/marker_policy.py` and `showcase/apply_round2.py`.
- `climb_check.py` (first-marker logic).
