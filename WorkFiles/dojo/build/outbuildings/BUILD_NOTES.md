# Kit 5: storehouse (NW) + residence / wash house (NE) - build notes

**Lock:** `DojoOutbuildings` (claude, `Assets/Dojo/DojoOutbuildings.blend`), still held.
**Spec:** `WorkFiles/world/DOJO_ARENA_SPEC.md` 4.5 + the grey-box's proven numbers (`Scripts/dojo/build_dojo_greybox.py`).
**Look:** `References/Dojo/dojo_outbuildings_ref.png` (crops in `refcrops/`), the small elevations on
`dojo_roof_details_ref.png`, the overviews. AI-generated modelling references: measured, never sampled.
**Materials:** only the shared library (M_DJ_*): PlasterCream, Granite, TimberDark, TimberAged, Iron, RoofTile,
GlassAmber. No texture of our own, nothing forked. **Roof:** `roof_kit` 1.3.0 (noshi tiles, cap row, onigawara).

# ROUND 4 (2026-09-29): first build of both buildings (SM_DKO_*)

## Commands (headless, --factory-startup; no MCP, no Unreal, no git)
```
blender -b --factory-startup --python Scripts/dojo/outbuildings/build_outbuildings.py [-- --quick] [--no-export] [--no-context]   # ~25 s
LA=outbuildings/layout_outbuildings_checks.json
blender -b --factory-startup Assets/Dojo/DojoOutbuildings.blend --python Scripts/dojo/walk_check.py -- --layout $LA --out outbuildings/walk_check_outbuildings.json
blender -b --factory-startup Assets/Dojo/DojoOutbuildings.blend --python Scripts/dojo/climb_check.py -- --layout $LA --out outbuildings/climb_check_outbuildings.json --hover 0.019
blender -b --factory-startup Assets/Dojo/DojoOutbuildings.blend --python Scripts/dojo/roof_walk_check.py -- --layout $LA --out outbuildings/roof_walk_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoOutbuildings.blend --python Scripts/dojo/hall/hall_roof_walk.py -- --layout $LA --out outbuildings/roof_walk_hall.json
blender -b --factory-startup Assets/Dojo/DojoOutbuildings.blend --python Scripts/dojo/outbuildings/ob_roof_walk.py      # routes 2 + 3
blender -b --factory-startup Assets/Dojo/DojoOutbuildings.blend --python Scripts/dojo/outbuildings/render_outbuildings.py -- --what sheet|close|context --samples 64 --tag r0
py -3 Scripts/dojo/outbuildings/compose_outbuildings.py r0
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <abs ref> <abs ours> <abs out>
```

## Files
- `Scripts/dojo/outbuildings/`: `build_outbuildings.py` (pieces, layout, QA, export, check context),
  `ob_roof_walk.py` (routes 2 + 3 on the real hulls), `render_outbuildings.py`, `compose_outbuildings.py`.
- `Assets/Dojo/DojoOutbuildings.blend`: Kit = the 20 SM_DKO_ pieces + the showcase compound's pieces (read-only load
  of DojoShowcase.blend); Assembly = the showcase with our buildings in place of the grey-box storehouse / residence.
- `Exports/DojoKit/Outbuildings/`: 20 FBX (+ LOD sidecars).
- `WorkFiles/dojo/build/outbuildings/`: `layout_outbuildings.json` (pieces, 43 instances, numbers),
  `layout_outbuildings_checks.json` (layout_showcase.json with the swap), qa / export / outbuildings reports, the check
  JSONs + logs, `renders/r0/`.

## Pieces (walls are piece-local modules: face at local y 0 outward -y, 0.25 m thick; BR-reusable)

| Piece | Class | Tris | LOD / Nanite | Notes |
|---|---|---|---|---|
| Store_Bay_2m / _2p5 | building | 452 / 498 | LOD0-2 | kura bay: 2 courses of hewn granite to +1.0 (4 cm proud, staggered, pitched faces, dark joint core), plaster to the plate, plastered plate + frieze between the rafters |
| Store_Bay_Door | building | 768 | LOD0-2 | 2.5 m: frame (jambs, lintel), 1.9 x 2.2 m opening, granite threshold, 2.9 m granite step (+0.15) |
| Store_Gable | building | 1,610 | LOD0-2 | full body depth incl. both corners: band wrapping the corners, plaster to the roof underside, framed vent (surround 7 cm proud, bars) |
| Res_Bay_1p1 / _2p15 | building | 794 / 1,282 | LOD0-2 | granite course, sill beam, board-and-batten wainscot to +0.95, rail, plaster, timber plate + frieze |
| Res_Bay_Door | building | 586 | LOD0-2 | 2.0 m: jamb posts, lintel, sill as threshold, granite step |
| Res_Bay_Window | building | 1,634 | LOD0-2 | 2.3 m: 0.3 m strip + two posts round a 1.64 m window, proud sill, head rail |
| Res_Gable | building | 4,264 | Nanite | corner posts, the base, tie beam at the eave line, plaster triangle, slatted vent, 5 purlin ends 0.53 m out under the rake |
| Door_Steel / Door_Wood / Window_Lattice | building | 996 / 1,372 / 750 | LOD0-2 | closed; steel leaves with border, knobs, hinges; board leaves with rails, pull plates, strap hinges; 6 x 8 kumiko over lit paper (GlassAmber) |
| Canopy_2p8 / _2p2 / _Window | building | 9,848 / 7,820 / 6,612 | Nanite | tiled lean-tos (25 / 25 / 22 deg): eave discs, verge rolls + boards, noshi flashing at the wall, soffit + rafters, fascia, ledger, front beam, two brackets (arm + strut) |
| MeterBox | thin | 618 | LOD0-2 | the residence sheet's meter: steel box, window, hood, plate, 2 conduits up, 1 down, clamps (its own asset) |
| Roof_Slope | roof | 66,540 | Nanite | ONE slope (south; the north is the same piece turned 180): tiles, sarking, X-capped rafters, fascia, verges with bargeboards (0.16 m); used x4 |
| Roof_Ridge | roof | 15,456 | Nanite | bed, 3 real noshi courses, cap row with collars, plain onigawara both ends (roof_kit defaults) |
| Gutter | thin | 1,644 | LOD0-2 | 7.05 m half-round on strap brackets, capped; x4 (turned 180 = brackets toward the other fascia) |
| Downpipe | thin | 876 | LOD0-2 | swan neck 0.525 m, clamps, shoe; x8 (near each eave-side corner) |

- 20 pieces, 124,420 unique tris, 361,454 placed, 43 instances. Both buildings share the roof, gutter and downpipe
  pieces (same size roofs, placed at X 3.3 / 40.7, Y 31.7).
- QA 20 / 20 with 0 hard fails (waived as the hall / kit 1: uv0_tile_range, uv_no_overlap; texel_density on the
  GlassAmber window only). LOD pieces: 0 LOD fails. UCX on every piece (27 hulls).

## Numbers (grey-box world frame)
- **Roof = the grey-box's exactly:** X -1..7.6 / 36.4..45 (over the perimeter wall), Y 27.4..36, one 0.2 m slab per
  slope from +3.25 at the eaves to +5.25 at Y 31.7. Pitch = the grey-box's atan(2.0 / 4.3) = **24.944 deg** (roof_kit's
  25.0 would have put the planes at +5.255). Ridge cap top +5.5715; 16 courses of 0.284 m.
- Body X 0..7 / 37..44 (grey-box), faces Y **27.94** (the grey-box door face the modern props sit on) and 35.46 (0.54 m
  eaves both sides, symmetric about the ridge). Wall plate +3.088..3.248 (the rafter underside at the face).
- Store band +1.0; residence base: granite course +0.15, sill +0.27, rail +0.95..1.03.
- Doors: store opening 1.9 x 2.2 (+0.15..2.35), canopy eave +2.66; residence door 1.64 x 1.95 (+0.27..2.22), canopy
  eave +2.56; window 1.64 x 1.22 (+1.03..2.25), hood eave +2.44. Gutter rim +3.073, 0.09 m outside the eave line.

## Checks (our buildings in the showcase in place of the grey-box; GASP capsule r 0.30, 1.72 m, step 0.45) - ALL PASS
- **walk_check** PASS: every route clear, every CONTROL blocked; also PASS at r 0.35.
- **climb_check** (hover 0.019) PASS, every route, the proven numbers unchanged: route 2 pier 123.1 cm / depth 110.6 ->
  Mantle 1 m, then **0.0 m** walk onto the storehouse eave; route 3 drops **1.224** (outbuilding roof -> corridor)
  and **0.513** (corridor -> hall lower roof); routes 1, 4, 5, 7, 8 as before.
- **roof_walk_check** (kit 1) PASS; **hall_roof_walk** PASS (route 3 off both corridors onto the hall).
- **ob_roof_walk** (new) PASS: route 2 both sides, pier -> eave (max rise 0.012 m) -> up the south slope (24.9 deg) to
  the verge; route 3 walk-off at the 1v1 line Y 30.4 and the grey-box line Y 31.0 (BR): the fall is clear and lands on
  the corridor roof (plane drop 4.645 -> 3.42 = 1.225 m; the capsule leaves the slab edge about 0.3 m past the verge,
  measured capsule drop 0.96-1.04 m); along both eaves; BR over the ridge (0.348 m step onto the ridge box). CONTROLs
  blocked: the 1v1 ridge blockers, the west wall top under the roof (no headroom), both closed doors.
  - Note: at Y 31.0 the grey-box's 1v1 corridor-ridge blocker (Y 31.0-31.1) stops a capsule; in the 1v1 route 3 runs
    on the corridor's south slope (as hall_roof_walk already does at Y 30.4).

## Decisions / deviations (flagged)
1. **Door + canopy on the south EAVE wall, not the gable (the sheet).** The ridge must run along X (spec; route 2
   arrives on the south eave from kit 1's pier, route 3 leaves over the east / west verge), so the courtyard face is an
   eave wall. The door, canopy, the residence window + hood + meter box are there; the vents stay on the gables.
2. **Residence door canopy and window hood are two canopies** (the sheet's image shows a lower, separate hood over the
   window; REFERENCE_LOG's "one canopy" text is superseded by looking).
3. **North eave at Y 36.0 (spec), body north face at 35.46**: a 0.54 m strip between the body and the north
   perimeter wall, inside the closed rear pocket (the kit-1 cap overhang leaves 0.30 m; no capsule fits).
4. **South gutters stop at X 0.50 / 43.50** (clear of kit 1's step pier, visual to X 0.44 / 43.56); the corner
   downpipes stand beside it (X 0.65 / 43.35).
5. **Clean steel:** the library Iron has rust patches in its outer columns; the steel door and the meter box map their
   Iron faces into the measured rust-free column band (u 0.25-0.66, 0 % rust) at 0.85 x texel density (QA passes).
   UV only; the material is the library's.
6. **Bargeboards 0.16 m** (roof_kit verge `board_h`; its 0.26 default hid the residence's purlin ends that the sheet
   shows under the rake).
7. **Purlin ends only on the residence** (the storehouse sheet shows a plain plaster gable).

## For the combined import (other kits' pieces; applied ONLY in our check / render context)
- `SM_DKP_Modern_ACUnit_Wall` stood at (40.8, 27.94, 1.55) in front of the residence's lattice window: proposed
  (37.0, 28.7, 1.55) rot_z -90, on the residence's west gable between its corner and the corridor.
- `SM_DKP_Modern_JunctionBox` at (2.2, 27.94, 0.3) sank 4 cm into the storehouse granite band: proposed Y 27.90.
- Both are in `layout_outbuildings_checks.json` -> `outbuildings_proposed_moves`. The two wall lamps (6.6 / 37.4,
  27.94) sit on our plaster as they are.
- Replaces: SM_DGB_Storehouse, _Storehouse_Roof, _Residence, _Residence_Roof. Markers, climb routes and the 1v1
  boundary are unchanged (the grey-box roof slabs are identical).

## Renders (`renders/r0/`, Cycles GPU 64 spp, denoised; studio grey like the sheet, sunset for context)
- `sheet_outbuildings.png`: the reference's layout: storehouse front + gable | residence front + gable (ortho, exact
  1.8 m silhouettes), top views, 3/4 views. Views: `store_front/side/top/34`, `res_front/side/top/34`.
- Close-ups (`sheet_closeups.png`): `close_store_door_canopy`, `close_route2_pier_eave`, `close_res_door_window_meter`,
  `close_store_gable_vent_verge`, `close_res_gable_purlins`, `close_ridge_end`, `close_gutter_downpipe_corner`,
  `close_route3_verge_corridor`.
- Sunset context: `context_store_sunset`, `context_res_sunset`, `context_ref2_elevated`.
- Reference | ours (`sbs/`): sbs_sheet, sbs_store_front, sbs_store_side, sbs_store_34, sbs_store_top, sbs_res_front,
  sbs_res_side, sbs_res_34.
- sRGB medians (`numbers.json`, reference / ours, studio): store plaster 200,178,163 / 215,203,191; granite band
  114,101,88 / 160,155,150; residence plaster 196,173,157 / 208,195,181; boards 83,68,59 / 92,78,71; tiles
  103,104,112 / 66,70,75.

## Open
- **Granite band reads light and clean** (160 vs 114): the library Granite (look-pass r3, fine grain) under the studio
  rig; the sheet's band is darker, brown-grey with moss. Library / look-pass item (not forked here).
- **Tiles darker than the sheet** (66 vs 103): the library RoofTile, same as the hall.
- **Kit 1's route-2 pier** ends in a gabled cap with a ridge-end tile (visual top +3.487) right under our south eave's
  outer corner: it butts into our first tile course over X -1..0.44 (`close_route2_pier_eave`, both piers). Reads as a
  wall meeting a building, but the pier's end tile stands in the runner's path (kit 1's item, as with the grey-box).
- Context renders: the ground kit and the stone props show untextured (the showcase copies don't match their source
  blends' bounds); our pieces, the hall and kit 1's wall are textured.
- The sheet's storehouse door is mid grey; the library Iron reads darker and hammered.
- Not in Unreal yet (the combined import); the judgement is on UE captures.


# ROUND 4 FIX f1 (2026-09-29): GABLE-FRONT (both Unreal judges' first blocker)
Full notes: `WorkFiles/dojo/build/BUILD_NOTES.md` (ROUND 4 FIX f1). Deviation 1 above is withdrawn: the ridge runs N-S
over X 3.3 / 40.7 (the grey-box slab turned 90 deg: same footprint, pitch, eave and ridge planes), the courtyard sees
the gable with the door, hood, vent (and on the residence the window, its hood, the tie beam over the hoods and the
meter box) as the sheet. Pieces now: Store_Wall_N/F, Store_GableFront/Rear, Res_Wall_N/F, Res_GableFront/Rear,
Door_Steel (new instance M_DKO_SteelGrey: the library Iron on its clean UV band pulled to mid grey; recipe in
layout_outbuildings.json 'materials'), Door_Wood, Window_Lattice (7 x 8, 15 mm bars, no wear bake), the three
canopies, MeterBox, Roof_Slope (far slope, turned), Roof_SlopeNear_Store/_Res (notched under the corridor roof),
Roof_Ridge (turned 90), Gutter_S/N/F, Downpipe (gable corners). QA 23 / 23, 0 hard fails. Route 2 = 0.233 m step
onto the far slope; route 3 = a walk down the near slope onto the corridor roof (0.109 m step down). ob_roof_walk.py
rewritten for the new orientation: PASS.
