# Kit 5 (part): the two covered corridors (Blender)

**Lock:** `DojoCorridors` (claude, `Assets/Dojo/DojoCorridors.blend`), still held for the round-4 fix round.
**Spec:** `WorkFiles/world/DOJO_ARENA_SPEC.md` 4.5 and the grey-box (`Scripts/dojo/build_dojo_greybox.py`).
**Look:** `References/Dojo/dojo_corridor_ref.png`, an AI-generated modelling reference (`REFERENCE_LOG.md`). It was
measured, never sampled.
**Materials:** only the shared library (`M_DJ_*`). Roofs use the shared roof system `roof_kit` 1.3.0 unchanged: tile
field, sarking, rafters, eave trim, verge, `noshi_tiles`, `cap_row`, `onigawara`, `wall_flashing`, gutter and
downpipe.

# ROUND 4 (2026-09-29): the corridors as bay modules

## Commands (headless, --factory-startup; no MCP, no Unreal)
```
blender -b --factory-startup --python Scripts/dojo/corridors/build_corridors.py [-- --quick] [--no-export] [--no-context]   # ~20 s
blender -b --factory-startup Assets/Dojo/DojoCorridors.blend --python Scripts/dojo/walk_check.py  -- --layout corridors/layout_corridors_checks.json --out corridors/walk_check_corridors.json
blender -b --factory-startup Assets/Dojo/DojoCorridors.blend --python Scripts/dojo/climb_check.py -- --layout corridors/layout_corridors_checks.json --out corridors/climb_check_corridors.json --hover 0.019
blender -b --factory-startup Assets/Dojo/DojoCorridors.blend --python Scripts/dojo/roof_walk_check.py -- --layout corridors/layout_corridors_checks.json --out corridors/roof_walk_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoCorridors.blend --python Scripts/dojo/hall/hall_roof_walk.py -- --layout corridors/layout_corridors_checks.json --out corridors/roof_walk_hall_ctx.json
blender -b --factory-startup Assets/Dojo/DojoCorridors.blend --python Scripts/dojo/corridors/corridor_checks.py      # route-3 roof walk + clearance
blender -b --factory-startup Assets/Dojo/DojoCorridors.blend --python Scripts/dojo/corridors/render_corridors.py -- --what sheet|close|context --samples 64 --tag r0
py -3 Scripts/dojo/corridors/compose_corridors.py r0
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <ref.png> <ours.png> <out.png>     # ABSOLUTE paths
```
The check context: the build loads `DojoHall.blend` read only. That blend holds the showcase compound with the
round-4 hall. The grey-box corridors are dropped from it. `layout_corridors_checks.json` is
`hall/layout_hall_checks.json` with the corridors swapped in, plus 6 corridor walk routes.

## Layout
World metres, W corridor. E is the mirror about X 22.

| Item | Value | Grey-box |
|---|---|---|
| Outbuilding gable wall | X 7.0; corridor work from X 7.02 | storehouse body X 0-7.0 |
| Post lines | X 7.30 / 10.05 (one 2.75 m bay = 11 tile pitches), Y 29.85 (open) / 32.15 (closed) | posts Y 29.5-29.7, wall Y 32.3-32.5 |
| Roof | gable, eaves +3.0 at Y 29.5 / 32.5, planes meet +3.6995 at Y 31.0, 25 deg | same |
| Roof extent | X 7.02 (under the outbuilding verge, to its wall) to 10.30 | slab X 7.6-10.5 |
| Floor | +0.5, X 7.02-11.0 (the hall veranda edge), deck Y 29.77-32.22 | X 7.0-11.0, Y 29.5-32.5 |
| E corridor | posts X 33.95 / 36.70; roof X 33.70-36.98; floor X 33.0-36.98 | roof X 33.5-36.4 |

- **Why the gable ends at X 10.30, not 10.5.** The hall's west gutter is at X 10.34-10.48, z 2.76-2.83
  (`layout_hall`). Ending at 10.30 keeps the corridor verge boards 3.3 cm clear of it. The roof hull follows the
  visible roof. The route-3 walk still passes (below).
- **Why the ridge sits above the hall eave.** The corridor ridge (+3.70, cap top +3.94) stands above the hall's
  side eave (+3.0), because the spec gives both roofs the same eave height. So at the hall the corridor shows an open
  gable over the hall's eave line; it cannot tuck under that eave.
- **The outbuilding end does tuck under.** The corridor roof runs under the outbuilding verge (X 7.0-7.6) to its
  wall, with a noshi flashing up each slope. Its highest point there is 0.99 m below the outbuilding's roof plane.
  That is 0.58 m below where `gable_roof`'s verge structure hangs (0.41 m below the plane).

## Pieces
14 pieces, `SM_DKC_*`, in `Exports/DojoKit/Corridors`. There are 20 instances, all at rot 0; the E ends are their
own mirrored meshes, so no piece needs a negative scale.

| Piece | Class | Tris | UCX | Distance detail |
|---|---|---|---|---|
| Bay_Floor | ground | 3,696 | 1 | Nanite |
| Bay_Frame | thin | 1,276 | 5 | LOD0-2 |
| Bay_Wall | building | 2,376 | 1 | Nanite |
| Bay_Roof | roof | 19,660 | 3 | Nanite |
| PostFrame | thin | 352 | 4 | 1 LOD |
| EndWall_W/E_Base | building | 1,804 | 2 | LOD0-2 |
| EndWall_W/E_Roof | roof | 3,466 | 3 | Nanite |
| EndGable_W/E_Floor | ground | 2,024 | 1 | Nanite |
| EndGable_W/E_Roof | roof | 7,220 | 3 | Nanite |
| Downpipe | thin | 964 | 1 | LOD0-2 |

- **What the pieces hold:**
  - Bay_Floor: planks, edge beam, sill, joists, a centre beam on short posts, granite paving.
  - Bay_Frame: the post frame at local x 0 (posts on granite pedestals, tie beam, king post, bracket arm), both keta,
    the ridge purlin, and the lattice rail.
  - Bay_Wall: the closed side between the posts.
  - Bay_Roof: tiles, sarking, plain rafter ends, fascia, two noshi courses plus the cap-tile row, and the gutter.
  - EndGable roof: verges, bargeboards and a plain onigawara (0.46 x 0.52 x 0.26).
  - Downpipe: the swan neck, clamps with stays to the post, and a shoe.
- **Module rule:** EndWall base + roof, then n bays (Floor, Frame, Wall, Roof) every 2.75 m from the west post line,
  then one PostFrame, EndGable floor + roof, and a Downpipe at the outbuilding-end post. Both grey-box gaps take
  n = 1. The tile rolls sit on world-anchored 0.25 m lines, and ridge, keta and gutter joints are flush, so bays
  repeat seamlessly.
- **QA:** 14/14 pieces with 0 hard fails. Waived: uv0_tile_range and uv_no_overlap (tile-unit UVs, the hall's
  practice). Texel density p50 is 5.1-6.1 px/cm (library measure). The LODs have 0 fails. 57,352 unique tris, 85,676
  placed.

## Numbers
- Keta and tie beams +2.708-2.908, the ridge purlin +3.264-3.444.
- **Headroom under the tie beams / keta:** 2.21 m over the deck. R5 asks 2.5, which the spec's eave +3.0 over a
  +0.5 floor cannot give once the structure is in. This is the same exception as the hall veranda (flag for the
  user). The capsule (1.72) clears everything.
- Lattice rail top: 0.69 m above the deck (13 x 4 openings, as the sheet).
- **Closed wall:**
  - boards +0.56-1.40;
  - rail +1.40-1.48;
  - plaster +1.47-2.53;
  - head beam to the keta.
- Gutter rim +2.82 at Y 29.41. Tile courses 5 x 0.291 m.

## Checks
All pass. GASP capsule r 0.30, 1.72 m, step 0.45.
- **walk_check:** PASS, also at r 0.35. All routes are clear and all controls blocked. New corridor routes:
  - the floor from the outbuilding end to the hall veranda, both corridors: clear;
  - through the closed wall: blocked by Bay_Wall;
  - yard up over the rail: blocked by the deck edge.
- **climb_check** (hover 0.019): every route works. Route 3 is still the drops of 1.224 and 0.513 m
  (layout-number walk).
- **roof_walk_check** (kit 1 paths): PASS.
- **hall_roof_walk:** PASS (16 paths). Route 3 runs from both corridor roofs onto the side lower roofs, on the real
  corridor hulls.
- **corridor_checks roof walk:** PASS on the real hulls.
  - Route 3, W and E: outbuilding roof -> corridor -> hall lower roof; walk-off drops 0.99-1.01 m and 0.16 m along
    Y 30.4.
  - Along the south slope by the eave: clear.
  - Up to the ridge blocker: clear.
  - BR over both ridges: clear.
  - BR off the north slope onto the hall roof: clear.
  - CONTROL, back up onto the outbuilding roof: blocked by its slab.
- **Clearance** (render meshes, BVH overlap), `clearance_corridors.json`:
  - 0 intersections with the hall, the veranda, the chidori or the outbuilding. The only overlaps are the paving
    sitting in the ground kit's gravel (z <= 0.05).
  - Minimum gaps:

    | Between | Gap |
    |---|---|
    | Gable verge and the hall gutter | 0.033 m |
    | Gable post bracket and the hall roof | 0.097 m |
    | Deck and the hall veranda | 0.010 m |
    | End pieces and the outbuilding wall | 0.020 m |

## Renders
`renders/r0/`: Cycles GPU, 64 spp, denoised.

| Kind | Files |
|---|---|
| Sheet | `sheet_corridor.png` (the reference's layout and grey; 75 px/m with 1.8 m silhouettes) |
| Sheet views | `corr_closed.png` (E corridor from the alley), `corr_open.png` (W from the courtyard), `corr_end.png` (W from the hall side, the corridor alone), `corr_top.png`, `corr_34.png` |
| Close-ups | `close_gable_at_hall_eave`, `close_gable_junction_below`, `close_outbuilding_end_downpipe`, `close_rail_pedestal_deck`, `close_closed_wall_alley`, `close_inside_frame`, `close_roof_route3` |
| Sunset | `context_corridor_W_sunset`, `context_corridor_W_high_sunset` |
| Reference and ours | `sbs_sheet`, `sbs_closed`, `sbs_open`, `sbs_end`, `sbs_top`, `sbs_34` |

## Deviations and open points (flagged)
1. **One bay, not three.** The grey-box gap (2.9 m of roof, 4 m of floor) holds one 2.75 m bay; the sheet shows
   about 3 x 2.5 m. The modules repeat for longer runs (the BR).
2. **The hall end is an open gable standing above the hall's side eave, not tucked under it.** Tucking under is
   impossible at the spec heights: both eaves are +3.0, and the corridor ridge +3.70 is proven by route 3.
3. **R5 headroom 2.21 m** under the tie beams and keta (as the hall veranda).
4. **The north side is open between the last post and the hall veranda** (X 10.14-11.0). The grey-box had
   X 10.5-11.0. The 1v1 alley blockers belong to the duel level.
5. **Outbuildings are grey-box in the context.** The storehouse/residence track must keep its gable wall face at
   X <= 7.0 (>= 37.0 E) over Y 29.4-32.6 and z 0-4.1, and keep its verge structure within 0.58 m of the plane.
6. **Look is library-owned.** The sheet's timber is warmer and redder than the library's greyed TimberDark.
7. **Unreal:** not imported (combined import next).
   - 14 FBX; layout in `layout_corridors.json`.
   - Replace SM_DGB_Corridor_W/_E and _Roof.
   - Classes per piece: Frame/PostFrame/Downpipe thin, floors ground, walls/bases building, roofs roof.


# ROUND 4 FIX f1 (2026-09-29)
Full notes: `WorkFiles/dojo/build/BUILD_NOTES.md` (ROUND 4 FIX f1). The outbuildings are gable-front, so the corridors
meet their EAVE walls: the end roof strip (EndWall_W/E_Roof) runs from X 6.0 into the outbuilding's near slope and is
kept inside the wall line only above that slope (valleys, iron valley flashings, a plaster infill over the plate; no
wall flashing any more); floor and roof start at X 7.045 (clear of the granite band), the closed wall at 7.005.
Lattice rail 18 x 5 near-square cells; the hall-end onigawara 0.30 x 0.34 x 0.20. QA 14 / 14, 0 hard fails.
Route 3 is now a walk from the outbuilding roof onto the corridor (both ways), then the 0.51 m drop to the hall.
