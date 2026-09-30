# Kits 3 + 4: main hall and the shared roof system (Blender)

**Date:** 2026-09-28. **Lock:** `DojoHall` (claude, `Assets/Dojo/DojoHall.blend`), still held.
**Spec:** `WorkFiles/world/DOJO_ARENA_SPEC.md` 4.4, plus the user's decisions of 2026-10-02 (`DOJO_QUEUE.md`).
**Look:** `References/Dojo/dojo_hall_front_ref.png`, `dojo_roof_details_ref.png` and `dojo1_reference2.png`. All three are
AI-generated modelling references (`REFERENCE_LOG.md`). They were measured, never sampled.

**Materials:** only the shared library (`Scripts/dojo/materials`, M_DJ_*):
- TimberDark (+End): the frame, bays and lattice;
- TimberAged (+End): the deck boards and the landing deck;
- Granite, PlasterCream, Iron, RoofTile;
- GlassAmber: the lit paper behind every lattice. It is opaque and the hall stays closed.

No texture of our own was made.

## Commands (headless, --factory-startup; no MCP, no Unreal)
```
blender -b --factory-startup --python Scripts/dojo/hall/build_hall.py [-- --quick] [--no-export] [--no-context]   # ~5-6 min
blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/walk_check.py  -- --layout hall/layout_hall_checks.json --out hall/walk_check_hall.json
blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/climb_check.py -- --layout hall/layout_hall_checks.json --out hall/climb_check_hall.json --hover 0.019
blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/hall_roof_walk.py            # hall/roof_walk_hall.json
blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/render_hall.py -- --what sheet|roof|close|context --samples 128 --tag r2
py Scripts/dojo/hall/compose_hall.py r2
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <ref.png> <ours.png> <out.png>
```

### Files
- `Scripts/dojo/roof/roof_kit.py`: the ROOF SYSTEM API (v1.0.0). It imports kit 1's `kit1_geo` and does not edit it.
  - Parts:
    - `RoofSlope`, `tile_field` / `roll_run` (kit 1's tiles with the sheet's plain eave disc);
    - `sarking`, `rafters`, `eave_trim`;
    - `ridge`, `ridge_end` (plain block-and-disc), `hip` (with an optional corner block), `wall_flashing`;
    - `verge`, `gable_face` (boards or plaster, tie beam, king post), `bargeboards`;
    - `gutter` (half-round, rolled rims, hooked strap brackets), `downpipe` (two-bend swan neck, clamps, shoe);
    - `plan_clip`, `slab` (collision), `sag_warp` (corner upsweep).
  - Compound builders:
    - `irimoya()`: returns separate main-slope, end, ridge and hull sets, so one piece can be instanced twice;
    - `lean_to_wrap()`: front + sides, hips, verges, gutter polylines;
    - `gable_roof()`: plain kirizuma for the storehouse, residence and corridors. It is shown working in roof panel e.
- `Scripts/dojo/hall/`:
  - `build_hall.py`, `render_hall.py`, `compose_hall.py`;
  - `hall_roof_walk.py`: the roof-walk replay for routes 3/4/5. `roof_walk_check.py`'s paths are kit-1 only.
- `Assets/Dojo/DojoHall.blend`:
  - `Kit` holds the 18 hall pieces with UCX, plus the showcase compound's pieces (loaded read-only from
    DojoShowcase.blend so the check scripts run unchanged).
  - `Assembly` holds the showcase with the hall in place of the grey-box hall.
- `Exports/DojoKit/Hall/`: 18 `SM_DKH_*.fbx`, plus sidecars for the LOD pieces.
- `WorkFiles/dojo/build/hall/`:
  - `layout_hall.json`: pieces, 102 instances, numbers, AC zones, the upper eave step;
  - `layout_hall_checks.json`: `layout_showcase.json` with the swap;
  - QA / export / hall reports, the check JSONs, logs, renders.

## Pieces (grey-box world frame; pivots in layout_hall.json)

| Piece | Class | Tris | Nanite | Notes |
|---|---|---|---|---|
| SM_DKH_StepBand | ground | 1,584 | no, LOD0-2 | granite band, two 0.25 steps, treads 0.35 m (Y 21.30-21.65-22.0), X 11-33; the central stair X 20-24 with 0.5 m treads (Y 21.0-21.5-22.0) inside it |
| SM_DKH_Veranda | ground | 12,276 | yes | deck boards +0.5 (front along X, sides along Y), edge beams, sleepers, short posts on footing stones, granite side curb; 1 hull X 11-33, Y 22-34 |
| SM_DKH_VerandaFrame | thin | 3,388 | yes | 24 posts 0.21 m on the 2 m bays, capital blocks, iron base plates, keta (top +3.048), hip rafters; hulls = the posts only |
| SM_DKH_Frame | building | 7,744 | yes | 28 posts 0.24 m, granite foundation, ground sills, skirting, wall plates (+5.366-5.606), lower-roof ledgers, upper-eave bracket arms + blocks + outer purlins; hull = the closed body |
| SM_DKH_Bay_Plaster / _Window / _Door | building | 748 / 2,866 / 2,600 | no / yes / yes | 2 m bays from the floor to the head beam: board koshi + plaster; window (small-grid band + 2 lattice sashes); door (2 sliding doors, 6 x 9 lattice, board lower panel, iron pulls) |
| SM_DKH_Bay_Transom | building | 88 | no | plaster from the head beam (+2.67) to the clerestory sill (+4.20) |
| SM_DKH_Bay_ClerePlaster / _ClereLattice | building | 132 / 838 | no | the clerestory band between the roofs (+4.20-5.37); lattice 12 x 5 over the three door bays, as on the sheet |
| SM_DKH_RoofLower_Front / _SideW / _SideE | roof | 103,948 / 55,853 / 55,853 | yes | eave +3.0 at Y 21.5 / X 10.5 / 33.5, 25 deg to +4.166 at the walls, hips + corner blocks, wall flashing, soffit + rafters, fascia, gutters; verge + end board at the back |
| SM_DKH_RoofUpper_Slope (x2: front, back turned 180) | roof | 153,741 (corrected; it said ~161k) | yes | main slope eave +5.5 (0.9 m overhang), verge overhangs + verge ridges ending in small block-and-disc ends, bargeboards, soffit, purlin ends, rafters, fascia |
| SM_DKH_RoofUpper_End (x2: west, east turned 180) | roof | 45,530 (corrected; it said ~51k) | yes | hip slope, both hips (round rolls, end discs, corner blocks), gable-foot flashing, gable of dark vertical boarding with tie beam and king post |
| SM_DKH_RoofUpper_Ridge | roof | 8,916 (corrected; it said 8,508) | yes | bed, six noshi, ridge roll (top +8.703), plain block-and-disc ridge ends (top +9.48) |
| SM_DKH_Downpipe (x4: front and rear corners) | thin | 876 | no, LOD0-2 | from the side gutter, swan neck to the corner post, clamps, shoe |
| SM_DKH_EaveLanding (x2) | landing | 616 | no, LOD0-2 | the route-4 flat eave deck, top +3.0, 1.2 x 0.75 m, on two cantilever joists over the gutter |

- **Triangles:** 457,597 unique; 701,646 placed. 102 instances: 45 wall-bay stacks of three modules each, plus the rest.
- **Bay layout, front:** P W P D D D P W P, as the sheet. The sheet has plaster bays where the task text says "windows in
  the others".
- **Bay layout, other walls:**
  - sides: P P D P P (one side door, spec);
  - back: P W P P D P P W P (a door into the alley, spec).
- **Doors:** two panels per door bay, six across the three door bays. The sheet shows 2 per bay, and the prompt says
  "three bays of sliding doors". The task text's "4-panel" matches the two central bays together.

## Numbers
- **Upper roof** (irimoya):
  - eave +5.5 on all four sides, over the rectangle X 12.1-31.9, Y 23.1-34.9, 25.0 deg;
  - the planes meet at +8.251; the ridge roll top is +8.703 (spec: crest to +8.7); the ridge ends reach +9.48;
  - gable faces at X 14.0 / 30.0 (gable_in 1.9 m, round r2), verges at X 13.55 / 30.45, gable foot +6.386;
  - 7 courses of 0.30 m per gable run; the corners sweep up 0.12 m.
  - Ridge / eave length ratio 0.85; the sheet measures about 0.81.
- **Lower roof:** eave +3.0; +4.166 at the walls; 9 courses of 0.294 m; the corners sweep up 0.04 m.
- **Veranda:**
  - floor +0.5; the keta runs +2.808-3.048 on posts at Y 22.15 / X 11.15 / 32.85;
  - the head beam is at +2.67 (door head +2.40);
  - the gutter rim is at +2.823, 0.09 m outside the eave lines.
- **Collision:**
  - one flat slab per roof plane, as the grey-box's planes. The upper slope is two coplanar convex slabs (trapezoid +
    the verge rectangle);
  - the gable is a triangular prism; the body is one box X 12.88-31.12, Y 23.88-34.12, to +5.42;
  - the landing pads are exactly the grey-box pads: X 13.05-14.25 / 29.75-30.95, Y 20.75-21.5, z 2.8-3.0.
- **AC zones** (the modern kit's unit, not rebuilt here):
  - X 15.0-16.2 / 27.8-29.0, Y 21.98-23.1, on the lower roof plane z = 3.0 + (y - 21.5) tan 25. The unit's front feet
    at Y 22.0 sit at +3.2332, the same plane as before.
  - Nothing of the hall (gutter, flashing, brackets) stands in the zones or in the stances (15.6 / 28.4, 21.66).
  - The upper eave step is the upper slab's edge, +5.5 at Y 23.1: 0.40 m above the AC top.
- **QA:** 18/18 pieces with 0 hard fails; the LODs have 0 fails too.
  - Waived (kit 1's practice): uv0_tile_range and uv_no_overlap (tiling UVs in tile units).
  - texel_density is also waived on the three bays with GlassAmber. The panes' 0-1 hotspot UV skews the QA average.
    The library's own texel_density for those bays: p50 5.57-6.01, p5 4.92-4.97.
  - Texel density otherwise 4.3-6.0 px/cm (p5..p95), with p50 5.1-5.4 on the timber, stone and tile pieces.
  - The big roofs get a per-face grid UV1. lightmap_pack left about 2,000 sliver overlaps at 100k+ faces. They are
    Nanite under Lumen, so no lightmap is baked.
- **Nanite:** every piece of 2k tris or more (11; corrected in the f1 round, it said 13), shipped as a single LOD. StepBand, Downpipe, EaveLanding,
  Bay_Plaster and Bay_ClereLattice ship LOD0-2. Transom and ClerePlaster are under 400 tris and ship one LOD.

## Checks (hall in place of the grey-box hall; GASP capsule r 0.30, 1.72 m, step 0.45)
- **walk_check:** PASS. All 15 routes are clear and all 8 CONTROLs blocked, including:
  - gate -> path -> central stair -> veranda;
  - veranda front -> both sides -> both corridors;
  - CONTROL_into_the_hall, blocked at Y 23.58 by the body.
  - Also PASS at the spec's 0.35 m radius: the grey-box's 0.30 m tread failure is gone (treads 0.35 / 0.5 m).
- **climb_check** (hover 0.019): every route works.
  - Route 3: corridor -> hall lower roof, a 0.513 m drop.
  - Route 4:
    - cistern 122.3 cm, depth 145 -> Mantle 1 m;
    - pad 172.9 cm, depth 85.6 -> Mantle 2.5 m.
  - Route 5:
    - AC 197.4 cm, depth 112 -> Mantle 2.5 m;
    - then a 0.40 m walk-up.
  - Veranda from the side yard: 48.1 cm, depth 188 -> Mantle 1 m.
  - The spec as written (no pad, AC at 4.75) still fails, as in stage 1.
- **hall_roof_walk:** PASS. 10 paths clear, max slope 25.0 deg; 2 CONTROLs blocked.
  - Route 3: both corridor roofs down onto the side lower roofs.
  - Route 4: landing deck -> lower roof -> AC stance, both sides.
  - Route 5: AC top -> 0.40 step onto the upper eave -> up the front slope to +8.0 at the 1v1 ridge blocker.
  - Also: along the lower roof between the ACs; round the west hip corner; across the upper slope; BR over the ridge.
  - The controls:
    - lower roof -> clerestory: the upper eave slab (+5.3) stops a standing capsule at Y 22.9;
    - end slope -> gable.

## Renders (Cycles GPU, 128 spp, denoised)
Rounds:

| Round | What |
|---|---|
| p1-p5 | previews |
| r0 | first full round |
| r1 | gable slit fixed, elevated establishing camera |
| r2 | FINAL: gable face out to gable_in 1.9 |

The r2 files, all in `renders/r2/`:

| Kind | Files |
|---|---|
| Model sheet (the reference's layout, exact 1.8 m silhouettes at 33 px/m) | `sheet_hall.png` |
| Roof panels a-f (the silhouette beside the ridge) | `sheet_roof.png` |
| Close-ups | `sheet_closeups.png`: route 4 landing, route 5 AC zone, downpipe corner, stair + band, gable + verge, veranda side |
| Sunset context | `context_ref2_elevated.png` (reference 2's composition, 9.2 m up behind the gate), `context_establishing_ref2.png` (the showcase's camera under the gate roof), `context_from_courtyard.png`, `context_34_sunset.png` |
| Reference-and-ours pairs | `sbs_hall_sheet.png`, `sbs_roof_sheet.png`, `sbs_establishing.png` (side_by_side.py); `cmp_*.png` for every view and roof panel; `cmp_roof_all.png` |

- **Sheet colour** (sRGB medians, front elevation, `numbers` in this note; reference first, then ours):

  | Surface | Reference | Ours |
  |---|---|---|
  | Plaster | 188,155,128 | 173,134,103 |
  | Upper tiles | 92,95,106 | 98,100,102 |
  | Lower boards | 75,51,36 | 80,57,43 |
  | Lower tiles | 65,63,68 | 97,87,83 |

- The sheet rig is soft and low, with a front fill: the sheet lights the facade evenly under the eaves.

## Decisions / deviations (flagged)
1. **Route-4 landings:**
   - a flat timber eave deck on two cantilever joists that pass over the gutter, 1.2 x 0.75 m;
   - top +3.0, flat collision identical to the grey-box pad;
   - it reads as a small platform at the eave above each cistern.
   - The references show no such thing; it is the smallest believable form of the proven landing. User call.
2. **Continuous granite band:** per the user decision (two 0.25 steps, 0.35 m treads, walk up anywhere), with the
   sheet's wide stair as a deeper 4 m flight in the middle.
   - Because the band's upper tread is flush with the deck, the front shows no timber edge beam or short posts under
     the deck, as the sheet does. The sides do show them.
3. **Veranda edge headroom:**
   - the keta bottom is +2.808, only 2.31 m over the deck at the post line;
   - the capital blocks leave about 2.23 m;
   - over the step band under the lower eave: 2.22-2.47 m (rafter tails +2.73, gutter +2.74-2.82). The r2 text left
     this out (corrected in f1);
   - it is at least 2.68 m inside the posts (R5 asks 2.5).
   - The fixed eave (+3.0 at Y 21.5) leaves no room for more. R5 is NOT met at these lines. Open for the user.
4. **Upper roof = irimoya:** the gable faces sit 1.9 m in, with the roof sheet's dark vertical boarding (panel d).
   - The hall sheet's own side view shows a plaster gable; `gable_face(style="plaster")` gives that.
   - The sheet's odd raised middle eave / double hips over the clerestory were not copied: they are inconsistent across
     its views. The spec's hip-and-gable with a straight +5.5 eave was built instead.
5. **Downpipes:** 4, at the front corners (spec) and at the rear corners (the sheet's side view). Gutters run along the
   front and both side eaves. There are no gutters on the upper roof (the sheet shows none).
6. **Doors and panels:** 2 per door bay (above); plaster / window alternation as the sheet, not "windows in all the
   others".
7. **The hall's AC units are the modern kit's pieces at their showcase placement** (Z-scaled 1.23; the rear runners
   float, a known open item there). The hall provides the zones, stances and step, with nothing in the way.

## Open points
- **Tiles:**
  - The sheets' tiles are bigger, rounder and glossier blue-black with a metallic sheen. Ours are the library's matte
    charcoal (RoofTile), with warm dirt in the pans that reads brownish on the lower roof (median 97,87,83 vs 65,63,68).
  - The ridge noshi read as plain slabs next to the sheet's stepped, collared stack.
  - This is a RoofTile look pass in the material library (shared with kit 1), not a hall-kit edit.
- **Plaster:** it renders a little more orange than the sheet (173,134,103 vs 188,155,128) under the sheet rig.
  Library-owned.
- **Unreal:** not imported (not in this stage's scope). For the combined import:
  - the 18 FBX in Exports/DojoKit/Hall;
  - instances and classes in layout_hall.json;
  - replace the 6 grey-box pieces (SM_DGB_Hall_Veranda / StepBand / Body / RoofLower / RoofUpper,
    SM_DGB_Landing_EavePad);
  - the marker Hall_Veranda box is now Y 22.0-34 (layout_hall_checks.json);
  - library masters per Scripts/dojo/materials/README.md; GlassAmber EmissiveIntensity 500 (retune with the look pass).
- **Blind judge:** the hall and roof are signature pieces; they have not been judged yet.


---

# Fix round f1 (2026-09-28): measurer fixes + judge deltas

**Scope:** the measurer's seven fixes and the judge's blockers and deltas. The user asked for all of them (1-4 first).
Spec sizes and climb numbers are unchanged. Blender only; nothing was imported into DojoLab. Lock `DojoHall` is still
held by claude.

## Code
- **`Scripts/dojo/roof/kit_mesh.py` (NEW):** the shared mesh module: `Piece`, `cobox` / `cbox` / `member` / `quad`,
  `geo_to_object`, `stone_uv` (Granite + GraniteRubble), `grid_uv1`, `add_uv1`, `fix_lod`. It was moved out of
  `build_hall.py`, so the next kits no longer import the hall builder. `render_hall.py`'s demo gable uses it.
- **`roof_kit.py` 1.0.0 -> 1.1.0:**
  - docstring: the `corner_warp` reference is now `sag_warp`, and it points at kit_mesh;
  - docstrings added for `plane_clip`, `slope_tiles`, `course_off`, `_courses`;
  - new functions:
    - `eave_blocking`: the frieze board (menado-ita) over a wall line;
    - `rafter_cap`: the X-marked iron cap; `rafters(caps=)` uses it;
    - `ridge_cap` + `cap_straps`: kit 1's banded `ridge_tube` with an iron strap over every joint (0.40 m);
    - `clip_poly2` / `poly2_area`;
    - `chidori_hafu`.
  - `ridge`: four noshi layers plus the banded, strapped cap (was flat plates + roll).
  - `ridge_end`: a stepped, chamfered block-and-disc, 0.95 m tall (was a 1.35 m tombstone).
  - `hip`: about 0.3 m profile: three noshi, a banded strapped cap, a larger disc or a stepped disc end.
  - `verge(banded=)`; `gable_face(frame=)`: plaster in a timber frame.
  - `irimoya(front_recess=, blocking=, rafter_caps=, rafter_spacing=0.30, gable_frame=)`. The back slope is now the
    plain slope; the front can differ.
  - `lean_to_wrap(rafter_caps=, rafter_spacing=0.30)`; `gable_roof(blocking_run=, rafter_caps=, gable_frame=)`, so
    the storehouse, residence and corridors get the blocking too.
- **`build_hall.py`:** see the fixes below. New checks script `Scripts/dojo/hall/hall_sightlines.py`.
- **`hall_roof_walk.py`:** paths updated for the new roof (below).

## Measurer fixes
1. **Wall-head slot:**
   - `head_beams` now adds a filler behind the nageshi, so the nageshi has full depth back to the kamoi's back face.
     It laps the kamoi (+1.2 cm) and the transom above (+1.2 cm).
   - The kamoi laps the panels below.
   - Every infill (plaster, panels, lattice paper, sills) laps 12 mm into the posts.
   - Panel rows lap each other by 4-5 mm.
   - The module seams at +2.40 and +4.32 now overlap (plaster to KAMOI + 6 mm; clere plaster from +0.105).
2. **Upper-eave blocking:** `eave_blocking` runs along all four upper wall lines. Where it goes:
   - in `irimoya`: the main slopes, the recess centre and the end slopes;
   - in `gable_roof`: via `blocking_run`.
3. **Veranda deck to the wall:**
   - The front boards run to the skirting face, Y 23.912 (the last board is ripped to fit).
   - The west boards run to X 12.912 and the east boards from X 31.088.
   - No slot remains at the wall foot.
4. **R5 headroom: FLAGGED for the user, not changed.**
   - At the keta line: 2.308 m.
   - At the capital blocks: 2.228 m.
   - Over the step band under the lower eave: 2.219 m (upper tread) and 2.469 m (lower tread).
   - These follow from the spec's fixed eave, +3.0 at Y 21.5, for route 4.
   - The choice is to accept them as an exception or change the eave.
   - Deviation 3 above is corrected. `layout_hall.json` has `numbers.r5_headroom_exceptions`.
5. **Roof API housekeeping:** done (see Code).
6. **BUILD_NOTES corrections:** done above (11 Nanite; 153,741 / 45,530 / 8,916).
7. **AC units (cross-kit, for the modern-props owner):**
   - `SM_DKP_Modern_ACUnit_Roof`'s rear runners float 0.12-0.2 m over the lower roof and reach 7 cm into the wall.
   - Rebuild the unit at +5.10 so the runners sit on the plane and stop at Y 23.92.
   - It is not the hall's file, so it was not touched.

**Sightlines** (`hall_sightlines.py`, `sightlines_hall.json`):
- Method: rays against the hall's render meshes. A leak is a ray that enters the interior before it hits anything.
- Interior: 0.25 m inside the inner wall faces, from +0.55 up to 0.16 m under the upper roof planes, so the rafter bays
  count.
- Calibration: on the r2 geometry (rebuilt in scratch) the same test finds 1,028 wall-head leaks and 883 eave leaks,
  which matches the measurer's report.
- **f1: 0 / 352,872 wall-head rays and 0 / 169,000 upper-eave rays. PASS.**
  - The wall-head eyes stand 0.4 / 0.7 / 1.0 m out, at six heights, including the rail heights.
  - The eave eyes are in the courtyard (Y 12-18, +1.6..3.0), on the lower roofs (+5.1), in the side yards and in the
    alley.
- A first f1 run had 1,384 horizontal leaks at +1.30, through the zero-width seam between the wainscot and the rail.
  The panel rows now lap, and the test got more eye heights.

## Judge deltas
1. **Upper roof form:**
   - The centre eave X 17-27 is raised 0.30 m to +5.80. It is cut back 0.643 m on the same 25 deg plane, so the
     collision stays planar.
   - Two banded, strapped descending diagonal ridges run from the ridge ends (13.9 / 30.1, 28.75) past the centre eave
     corners to the outer eave (17.40 / 26.60, 23.1). Each ends in a stepped disc end.
   - The lit lattice frieze sits under the centre eave: `Bay_ClereFrieze`, 14 x 3, at +4.97..5.32.
   - The outer bays keep a plaster band.
   - The collision is split along the diagonals into 6 convex slabs. Each diagonal also has a 0.25 m walkable hull.
   - **Ridge length: kept at 0.83 of the eave length.** I measured the front reference at about 0.76-0.80, from the
     ridge between the verge ridges. The judge's 60-65 % does not match the sheets.
   - Route 5 is untouched: both AC zones lie outside the recess. The 25 deg centre eave cannot be mantled, since GASP
     needs a flat landing.
2. **Ridge:**
   - bed, four noshi layers, a banded round cap with an iron strap every 0.40 m; cap top +8.681;
   - the ridge ends are stepped chamfered blocks with a disc tile, top +9.081, 0.40 m above the cap (was 0.78);
   - the verge ridges and every hip foot end in stepped disc ends.
3. **Hips, upper and lower:**
   - about 0.3 m profile, a banded cap with visible joints and straps;
   - disc end blocks at the upswept corners.
4. **Side chidori-hafu (W and E):**
   - Where: on the side lower roofs over the side door, which moved to bay Y 26-28 (west index 3, east index 1). It is
     centred at Y 27. At Y 29 it would have met the corridor roofs at Y 29.5-32.5 (route 3).
   - Shape: a 35 deg gable; face at X 11.05 / 32.95, verge at X 10.70 / 33.30; 4.87 m wide at the verge foot; plane at
     the ridge +4.797; ridge cap +5.073, under the upper eave; end +5.197.
   - Parts: plaster tympanum in a timber frame, bargeboards with a hanging board, banded verges with discs (starting
     where they clear the lean-to), iron valley flashings.
   - Collision: one walkable hull (36.9 deg measured).
   - The upper gables are now plaster in a timber frame (tie beam, beam, studs, king post).
5. **AC size: NOT changed (user call).**
   - The spec makes the ACs climb props, 1.2 x 2.0 m with top +5.10 for route 5 (the 0.40 m step to the upper eave).
   - A 0.7 x 0.55 m unit would break route 5.
   - They are also the modern kit's pieces.
6. **Clerestory:** the three tall lit lattices are gone. The band is plaster everywhere except the centre frieze.
7. **Front openings:**
   - Kept 9 bays of 2 m: the spec's 18 m body. The sheet shows 7.
   - The doors are now full-height lattice: 6 x 11 square kumiko over about 70 %, a mid rail and a board foot.
   - The former window bays are `Bay_Lattice`: full-height lattice with a low small-grid strip and a board foot.
   - The plaster bays sit over a plain dark board wainscot.
   - The barcode wainscot is fixed by `calm_boards`: every board samples one window of the timber tile, plus a small
     jitter. The deck boards got the same treatment.
8. **Materials: library-owned, not changed.**
   - The RoofTile still renders matte grey with speckle. The ridge, oni and hip parts read as stone on the flat faces
     under the sheet rig.
   - Plaster reads warm; timber reads orange.
   - This needs the RoofTile / Plaster / Timber look pass in `Scripts/dojo/materials` (shared with kit 1).
9. **Eave details:**
   - Removed: the bracket arms, blocks and outer purlins.
   - The upper and lower roofs now have rafters at 0.30 m, each with an X-marked iron cap under the continuous fascia.
10. **Stone:**
    - The hall foundation and the side curb are now GraniteRubble: darker, rough, mossy joints.
    - The steps stay Granite.
    - The under-deck posts and gap show on the sides. The front is covered by the user's step band.

## Pieces (f1)
- 21 pieces, 104 instances; 669,540 unique tris, 768,318 placed (chidori 14,182 each after the verge fix).
- **Renamed / new:**
  - `RoofUpper_Slope` becomes `RoofUpper_Front` (165,219) + `RoofUpper_Back` (158,485);
  - `Bay_Window` becomes `Bay_Lattice` (3,528);
  - `Bay_ClereLattice` becomes `Bay_ClereFrieze` (882);
  - new: `RoofChidori_W` / `_E` (about 14.4k each).
- **Changed counts:** Ridge 11,732; End 49,326; LowerFront 108,782; Side 57,531; Frame 5,104; Door 2,820.
- **Nanite (13):** Veranda, VerandaFrame, Frame, Bay_Lattice, Bay_Door and the 8 roof pieces.
- **LOD0-2:** StepBand, Bay_Plaster, Bay_ClereFrieze, Downpipe, EaveLanding.
- **Single LOD:** Transom, ClerePlaster.
- **QA:** 21/21 with 0 hard fails. Waivers as before: uv0_tile_range / uv_no_overlap, and texel_density on the
  GlassAmber bays.
- **Stale r2 exports** (`RoofUpper_Slope`, `Bay_Window`, `Bay_ClereLattice`) moved to `hall/stale_exports_r2/` (not
  deleted).
- **The combined Unreal import must:**
  - place `RoofUpper_Front` and `RoofUpper_Back` at rot 0;
  - place the two chidori pieces at rot 0;
  - leave out the removed pieces.

## Checks (f1, the hall in the showcase)
- walk_check PASS (15 routes, controls blocked, and at r 0.35).
- climb_check PASS (all routes).
- hall_roof_walk PASS, 12 paths + 2 controls. New paths:
  - across the whole front slope over both diagonal ridges;
  - route 5 east up over the diagonal;
  - over both chidori-hafu along the side lower roofs.
- sightlines PASS.

## Renders (`renders/f1/`, Cycles GPU 128 spp, denoised)
- `sheet_hall.png` (front / side / top ortho with 1.8 m silhouettes, bay, 3/4), `sheet_roof.png`,
  `sheet_closeups.png` (13 close-ups, including the recess frieze, chidori, ridge + diagonal, soffit caps, door head
  and deck at the wall), four sunset context shots.
- `cmp_*` pairs from compose.
- `sbs_*` from `side_by_side.py`: hall sheet, roof sheet, front, side, top, 3/4, bay, establishing, ref2 elevated.
- **The r2 -> f1 change is visible in every sheet** (the judge asked this be confirmed): upper roof form, chidori,
  ridge ends, lattice doors, clerestory.

## Still open
- The RoofTile / plaster / timber look pass (library).
- AC size (the spec) and the AC runners (modern kit).
- R5 headroom (user).
- Ridge ratio: 0.83 kept against the judge's 60-65 %.
- 9 bays kept against the sheet's 7 (spec).
- The chidori valley flashing reads a little busy close up.
- Route-4 landing look (user).
- Unreal import.
- A blind judge on f1.


---

# ROUND 3 (2026-09-28): look pass, the upper roof form (hall + roof system track)

**Scope:** round 3 of the dojo, judged later on Unreal captures. This track: the upper roof form (the round-2 judge's #1),
finished ridges / ridge ends / hips (roof sheet panels b + c), and the open measurer items. Blender only, headless; no
Unreal, no material-library edit, no git. Lock `DojoHall` (claude) refreshed. Start state backed up in
`hall/r3_start_backup/` (scripts, the 21 FBX, the JSONs, DojoHall.blend).
The user's round-3 decision (drop the invented street lamps inside the courtyard and the short lanterns inside the gate)
is outside the hall kit; the hall's context renders now leave them out (`render_hall.py` DROPPED), whatever the showcase
layout still holds.

## Commands (as before, plus)
```
blender -b --factory-startup --python Scripts/dojo/hall/build_hall.py                         # ~1.5 min
blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/measure_r3.py    # hall/measure_r3.json
blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/render_hall.py -- --what sheet|roof|close|context --samples 64 --tag r3
py Scripts/dojo/hall/compose_hall.py r3 ; py Scripts/dojo/hall/compose_r3.py r3
```

## 1. Upper roof form: the raised centre PLANE (roof_kit 1.2.0, `irimoya(front_recess={..., "setback"})`)
What the sheet draws (front elevation and top view, `refcrops/r3/front_upper_x2.png`, `top_x2.png`, and reference 2):
two diagonal ridges run from the ridge ends inward and down to the corners of a centre eave that sits HIGHER than the
outer eaves, with the lit frieze under it; the outer wings come down lower, over a plaster band.

Why f1 did not read: f1 cut the centre eave back on the SAME plane, and on one plane a 0.30 m rise already needs a 0.64 m
setback (0.14 m of overhang left), so the rise could not grow and the diagonals were rolls lying on a flat slope.
Measured on the sheet: the centre fascia sits about 15 % of the eave-to-ridge height above the outer eave (0.41 m at the
sheet's scale), set back about 4.5 % of the roof depth.

Built (a new construction, not a patch of f1):
- The outer wings keep the main plane: eave +5.5 at Y 23.1, 25 deg (route 5 untouched).
- Between the diagonals the centre section X 17-27 is its OWN flat plane through the same ridge line (+8.2512 at Y 29,
  so the ridge stays straight) down to a centre eave at Y 23.55, +5.95: 0.45 m behind and 0.45 m above the outer eave;
  22.89 deg. The centre plane stands above the wing along each diagonal by 0 at the ridge end and 0.24 m at the foot.
- Each diagonal: bed + noshi + banded, strapped, riveted roll on the centre plane's edge (up = the two planes'
  bisector), a TILE cheek closing the step under its outer flank (0.30 m at the foot), a small block end at the centre
  eave corner (0.36 x 0.42 x 0.20). The wing's short cut edge in front of the corner (0.50 m) gets a board, two noshi
  and a small verge roll with a disc.
- Diagonals in plan: (17.216, 23.1) - (17.0, 23.55) - (14.5, 28.75) and the mirror (numbers in layout_hall.json
  `upper_roof.front_recess`).
- The frieze: a RAISED centre wall plate (Frame) +5.593..5.833 on the posts X 17-27 under the centre rafters (the outer
  plate stays +5.366..5.606); `Bay_ClereFrieze`'s lit lattice now runs +5.093..5.543 (0.55 m tall, 14 x 3) right under
  it, so the lit strip sits between the outer eave level and the raised centre eave, as on the sheet.
- gable_in 1.9 -> 2.5: ridge / eave length 0.83 -> 0.773 (the sheet's front elevation and reference 2 measure 0.77-0.78;
  the top view's 0.64 disagrees with both). Ridge X 14.35-29.65, gable faces X 14.6 / 29.4, gable foot +6.666 (gable
  about 1.6 m tall; the side view shows about 1.5).
- Collision: the four wing slabs (25.0 deg), two centre slabs (22.89 deg), and a gentle ramp hull over each diagonal
  (0.75 m onto the wing, 0.10 m over the centre plane on the line, 0.30 m inside; faces 37.9 deg max).
- Measured (measure_r3.json, rays on the render meshes): lowest visible eave +5.33..5.40 at Y 23.108 on the wings,
  +5.76 at Y 23.558 in the centre (a 0.43 m step in elevation); crest +8.694..8.716; ridge-end top +8.951.
- FLAG (spec R4, "25 degrees"): the centre plane is 22.89 deg. It is flatter, so still walkable and one flat collision
  plane. A raised centre eave on a shared straight ridge cannot keep 25 deg (both planes hold the ridge line and the
  wings' eave is fixed), so this is the price of the sheet's form. User call if 25 deg must hold everywhere.

## 2. Ridge, ridge ends, hips (panels b + c)
- Ridge (panel b's elevation, top down): banded crown r 0.12 with an iron strap every 0.40 m and a rivet head on each
  flank of every strap; a flat noshi band (0.36); a banded half-round r 0.085; two flat noshi (0.52 / 0.46); bed.
  Crest +8.71 (spec +8.7).
- Ridge ends: `ridge_end_stack`, the sheet's column of chamfered blocks (plinth block with a band, a narrower block
  with a band, an arched chamfered top block with an inset plain disc face, ring and boss) and two short round roll ends
  with disc faces low on the outer face. 0.56 x 0.82 x 0.46, top 0.24 m above the crest (f1: 0.40; the sheet: about
  0.25). Plain: no symbol. The chidori ridges use the same column (without roll ends).
- Hips (upper corners and the lower roof's front corners): the banded roll now ends in the roll's own thick round end
  tile with a plain disc face (panel c), in place of f1's small block; straps riveted.
- Unchanged: the verge (kudari-mune) ridges and their small foot blocks, the chidori verges.
- `tile_field`: a field that starts on a course line (the verge field over the gable foot) now gets that course's riser;
  the r3 preview showed a see-through slit there, between the verge foot and the diagonal.
- The tile material (matte, stony flat faces, rust-brown straps) is the library's RoofTile / Iron, not edited here.

## 3. Measurer items
| Item | Round 3 | Measured |
|---|---|---|
| Veranda deck meets the wall | done in f1; re-measured | front (X 16) and west (Y 28.9) profiles: +0.500 to the skirting face; the only lower hits are board joints landing on the new backing (+0.464) |
| White deck-board gaps (UE) | a dark TimberDark backing under the boards (top +0.464, 4 mm under the board bottoms), front and both sides | 5,659 rays down through the deck: 0 reach below +0.40 |
| Interior closed | sightlines extended for the raised centre (a second interior volume under the centre plane; targets between the raised plate and the centre sarking) | A 0 / 352,872, B 0 / 201,292: PASS |
| R5 headroom at the veranda edge | ACCEPTED EXCEPTION, recorded in layout_hall.json `numbers.r5_headroom_exceptions.status` | at the keta line (Y 22.06-22.24) 2.308 m; capital blocks 2.228; step band upper tread 2.387-2.523, lower tread 2.497-2.548; just behind the keta (Y 22.3) 2.608-2.730; Y 22.6 2.748+; inside the post line 2.8+. The lower eave (+3.0 at Y 21.5, route 4) leaves no room: its plane is +3.303 at the post line |
| StepBand LOD1 3.6 cm past LOD0 | `kit_mesh.fix_lod(clamp_to=LOD0)`: every LOD vertex clamped into LOD0's box | re-imported FBX: LOD1 / LOD2 0.0 past LOD0 on all five LOD pieces |

QA note: the SAT UV-overlap test builds every candidate pair in memory; on the big tiled roofs (70-120 million UV0 pairs)
it took 15 GB and stalled the machine with other chats' Blenders open (the first r3 build was stopped), so pieces over
40k tris now use the pipeline's other method (`overlap_method="operator"`, bpy.ops.uv.select_overlap). uv1_no_overlap
stays a hard check (0 on all).

## Pieces (r3)
- Same 21 pieces and 104 instances (names, pivots and rotations unchanged: a plain reimport for the combined import).
- Tris: RoofUpper_Front 165,732; Back 164,108; End 59,421; Ridge 18,164; LowerFront 109,598; LowerSide 57,531 x2;
  Chidori 14,340 x2; Veranda 12,936; Frame 5,192; others unchanged. 693,555 unique, 802,428 placed.
- QA 21/21 with 0 hard fails (waivers as before); the LOD pieces have 0 LOD fails.
- Changed hulls: RoofUpper_Front (wings / centre / ramps), Bay_ClereFrieze (to +5.543), RoofUpper_Ridge / End (the new
  gable_in).

## Checks (hall in the showcase context; the showcase's own earlier SM_DKH_* copy is now dropped from the check context,
which had doubled the hall once the combined import put it into DojoShowcase.blend)
- walk_check PASS (15 routes, controls blocked; also at r 0.35).
- climb_check PASS, the proven numbers unchanged: route 4 cistern 122.3 / 145, pad 172.9 / 85.6; route 5 AC 197.4 / 112.
- hall_roof_walk PASS: 16 paths + 2 CONTROLs (new: the wing onto the raised centre plane near the diagonal's foot, and
  the centre plane up to the ridge). Max floor slope 37.9 deg (the ramps), max rise per 2 cm 0.188 (the AC step).
  A first run failed at 64 deg on a narrower ramp hull; widened.
- sightlines PASS (above).

## Renders (`renders/r3/`, Cycles GPU 64 spp, denoised)
- Neutral studio (the sheet rig): `hall_front`, `hall_side`, `hall_top`, `hall_bay`, `hall_34`, `context_ref2_studio`
  (reference 2's elevated framing, the hall alone), roof panels `roof_*`, close-ups `close_*`, `sheet_hall`,
  `sheet_roof`, `sheet_closeups`.
- Sunset: `context_ref2_elevated`, `context_establishing_ref2`, `context_from_courtyard`, `context_34_sunset`.
- Reference | ours: `cmp_r3_upper_front.png` (the sheet's upper roof), `cmp_r3_top.png`, `cmp_r3_ref2_hall.png` /
  `cmp_r3_ref2_roof.png` (reference 2 at high zoom, sunset), `cmp_r3_ref2_hall_studio.png`, `cmp_r3_f1_vs_r3.png`
  (before / after); compose_hall's `cmp_hall_*`, `cmp_roof_*`.

## Open
- The tile / ridge material look (library): the ridge parts read as grey stone with rust straps, not the sheet's glossy
  blue-black; timber and plaster saturation in UE (the verifier's round-2 fails) are library / grade items.
- Unreal: not imported by this track. The combined import can reimport the 21 FBX as they are (same names and
  placements); then re-measure the hall region colours and re-run the in-engine traces.
- R4: the centre plane's 22.89 deg (above).
- Still open from before: 9 bays vs the sheet's 7 (spec), the route-4 landing look, the AC size (modern kit).


# ROUND 4 (2026-09-28): ridges + onigawara in the shared roof system (roof_kit 1.3.0), hall + gate + wall cap re-export

**Scope:** the round-3 final judge's #1 (7.5/10): "the main ridges on the hall upper roof and the gatehouse are one
plain light box with a single row of round caps; the end blocks are simple slabs". References: roof sheet panels b + c,
the gatehouse, hall front and wall sheets (crops in `round4/ridges/refcrops/`). Blender only, headless; no Unreal, no
material-library edit, no git. Output: `WorkFiles/dojo/build/round4/ridges/`. Start state backed up in
`round4/ridges/start_backup/` (scripts, the hall FBX, the kit-1 gate / cap / pier FBX, DojoHall.blend, DojoKit1.blend,
layout JSONs, measure_kit1_r3.json).

## Commands
```
blender -b --factory-startup --python Scripts/dojo/hall/build_hall.py                 # ~1 min + export
blender -b --factory-startup --python Scripts/dojo/build_kit1.py                      # 12-34 min (UV1 packing; CPU shared)
blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/{walk_check,climb_check,hall/hall_roof_walk,hall/hall_sightlines}.py [args as before]
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/{walk_check,climb_check,roof_walk_check}.py -- --out round4/ridges/<x>_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/measure_kit1.py   # copied to round4/ridges/measure_kit1_r4.json (the r3 file restored)
blender -b --factory-startup --python WorkFiles/dojo/build/round4/ridges/compare_hulls.py -- <old.blend> <new.blend> SM_DKH_|SM_DK_ <out.json>
blender -b --factory-startup Assets/Dojo/DojoHall.blend --python Scripts/dojo/hall/render_hall.py -- --what sheet|roof --samples 64 --tag ../../round4/ridges/hall
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/render_kit1.py -- --what r4ridges|gate --samples 64 --tag @round4/ridges/kit1
py -3 Scripts/dojo/hall/compose_hall.py ../../round4/ridges/hall ; py -3 Scripts/dojo/compose_kit1.py ../../round4/ridges/kit1
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <ref crop> <ours> <round4/ridges/sbs/sbs_*.png>
```

## Roof system API added (Scripts/dojo/roof/roof_kit.py 1.3.0; every future roof gets these by default)
- `noshi_tiles(g, p0, p1, up, widths, h, mat, seg=0.30, ..., core_in=0.010, ends=(True, True))`: courses of REAL
  noshi tiles. Each tile is a bullnose bar (rounded lip, rounder foot, the foot 7 mm in, so each course shades the one
  below), bevelled ends with a 5 mm joint over a recessed core (a dark ~1 cm groove, never see-through), alternate
  courses staggered half a tile, +-2 mm hand-laid width jitter. `h` may be a list per course. A drop-in for
  `kit1_geo.noshi_stack` (same arguments and return); `roof_kit.noshi_stack` now IS this, so every roof_kit stack
  (ridge, hips, verges, gable-foot flashing, the diagonal ridges, the wing verge) is real tiles.
  `ends=(False, False)` makes a module end flush (the wall caps meet their neighbours as one run).
- `cap_row(g, p0, p1, up, r, seg=0.30, straps=None, ...)`: the round cap-tile row with raised collars in the tile
  colour. `CAP_STRAPS = False` (r3's riveted iron straps are gone; the sheets show tile collars).
- `end_tile(g, p, out, up, r, length=0.07, disc_r=None)`: the round end tile (collar + plain disc face: rim, ring, low
  boss) closing a cap row or hip roll.
- `onigawara(g, base, facing, W, H, T, tiers=3, cap_z=None, cap_r=None, lobes=True, crest=True, knob=0.10)`: the
  plain ridge-end tile inside the envelope W x H x T: three bullnose tiers (the noshi courses carried round the end),
  an arched tile with a raised border and a plain round crest (rings + boss), sized so the crest stands just above
  the cap row's end disc, and that disc flanked by two round lobes (the hall and gate sheets' end views). No faces,
  creatures, symbols or text. The cap disc and lobes stand `knob` proud of the face (ornament outside the envelope).
- `ridge(g, p0, p1, z_planes, ..., courses=None, caps=True, ends=None|'onigawara'|'stack'|'block_disc'|'disc',
  end_size=None, end_out=0.20, top=None, legacy=False)`: a bed (now kept under the bottom course), `courses` noshi
  courses (int or a list of relative heights; widths from widths[0] down to the narrowest given) and the cap row,
  filling EXACTLY the round-3 ridge height (`ridge_top_legacy(...)`, or `top`), so hulls built on the returned top do
  not move. `legacy=True` rebuilds the r3 ridge for comparisons.
- `hip_roll(g, a, b, n_left, n_right, courses=3, w0=0.34, dw=0.03, h=0.055, roll_r=0.10, end='disc'|'onigawara'|...,
  end_size=(0.40, 0.46, 0.20), end_r=None)`: hip / descending / barge ridge = bed + real noshi courses + cap row + the
  eave end (disc end tile or an end ornament). `hip()` keeps its signature (straps default CAP_STRAPS, `end_style`).
- `ridge_end_any(g, base, facing, W, H, T, style=None, cap_z=, cap_r=)`: one entry for 'onigawara' (END_STYLE, the
  default), 'stack' (r3), 'block_disc' (r2). Same envelope for all.
- Compound builders: `irimoya(ridge_courses=, ridge_legacy=, verge_oni_style=, oni_style='onigawara')`,
  `chidori_hafu(ridge_courses=, oni_style='onigawara')`, `gable_roof(oni_style=None -> END_STYLE, ridge_courses=)`:
  the storehouse / residence / corridor / pavilion kits get the new ridges and ends with no extra arguments.

## Hall (build_hall.py)
- Upper ridge: 4 courses of real tiles (0.52 -> 0.36 m wide, 72 mm each) under the cap row (r 0.12, collars every
  0.30 m), in the round-3 height: cap top **+9.3649** and ridge-end top **+9.6064** (both unchanged, layout_hall.json).
- Ridge ends: the plain onigawara in the round-3 envelope 0.56 x 0.82 x 0.46 (the chidori ends 0.40 x 0.50 x 0.20;
  the verge feet and diagonal feet the small ones). Hips (upper corners, lower front corners) end in the disc end
  tile; every hip / verge / diagonal / flashing stack is real tiles; no iron straps or rivets anywhere.
- Collision: `compare_hulls.py` on the start backup vs the rebuild: **59 / 59 UCX hulls, max vertex delta 0.0 mm**
  (`round4/ridges/hulls_hall.json`). Visual envelope: ridge piece top +2 mm (the crest ring), 1.6 cm narrower (the
  bed under the bottom course); the chidori ends' knobs 7.8 cm past the r3 block face.
- QA 21 / 21 with 0 hard fails; 21 FBX re-exported to `Exports/DojoKit/Hall` (names, pivots, placements unchanged: a
  plain reimport). Tris: RoofUpper_Ridge 18,164 -> 27,756; RoofUpper_Front 170,859 -> 188,931; Back 164,144 ->
  169,936; End 59,529 -> 67,041; LowerFront 109,598 -> 124,206; LowerSide 57,531 -> 64,491 (x2); Chidori 14,340 ->
  19,986 (x2). Unique 699,354 -> 780,142; placed 821,887 -> 910,187 (all Nanite pieces).
- Checks (hall in the showcase context): walk_check PASS (15 routes + controls, also r 0.35); climb_check PASS (every
  route); hall_roof_walk PASS (paths + controls; max floor slope 39.4 deg on the ramps, as before: the hulls are
  identical); sightlines PASS (A 0 / 352,872, B 0 / 201,292).

## Gate + wall cap (build_kit1.py; kit1_geo.py untouched)
- Gate ridge: the same 0.24 m of stack as FOUR real noshi courses (0.46 -> 0.34 m, 60 mm each; was five flat 48 mm
  slabs) under the banded cap row (r 0.10); the bed narrowed to +-0.215 (under the bottom course). Ridge ends: the
  plain onigawara in the r2f-r3 envelope 0.42 x 0.70 x 0.34 (was `scroll_oni` with a disc face). Barge ridges
  (kudari): real tile courses and, at the eave, the round END TILE with its plain disc face (the gate sheet's front
  view; was a small scroll block). The verge's single course is real tiles.
- Wall cap (every cap module, End, Corner, and the piers / gate join that reuse `cap_geo`): the three noshi layers
  (0.30 / 0.27 / 0.24 m, 38 mm) are real tiles, flush at plain module ends, bevelled at gables; the banded tube and the
  round end tiles (`roll_end`) are unchanged.
- Heights (measure_kit1_r4.json): planes meet +4.4158, ridge roll top **+4.705**, ridge-end top **+4.936** (unchanged);
  wall tops 2.0 / 2.5 / 3.0, cap collision 0.3752 (unchanged); headroom 3.0353 (r3 3.0354).
- Collision: **61 / 61 UCX hulls, max vertex delta 0.0 mm** (`round4/ridges/hulls_kit1.json`).
- QA 28 / 28 with 0 hard fails; LOD0-2 on the LOD pieces; 28 FBX re-exported to `Exports/DojoKit/Kit1` (unchanged
  names / pivots). Tris: Gate_Roof 80,400 -> 103,628; WallCap 1 m 6,632 -> 7,628, 2 m 13,224 -> 15,228, 4 m 26,408 ->
  30,428, End 8,596 -> 9,664, Corner 9,544 -> 10,680; StepPier 61,645 -> 63,037; GateJoin 20,058 -> 20,550;
  FramePier 26,304 -> 27,696 (all Nanite).
- Checks: walk_check PASS (routes + controls; r 0.35 False, as in the r3 kit-1 file); climb_check PASS (every route);
  roof_walk_check 3 / 3, max rise over the ridge 0.32 m (unchanged); noshi slits **0** on the 1 m / 2 m / 4 m / End caps
  (a first build with a 22 mm-deep joint core read 161 on the 4 m cap: kit 1's slit rays count any ray that goes
  12 mm past the face, so the core now sits 10 mm in and spans the whole course); module joints 1 / 123 (1 m to 1 m,
  r3: 0) and 1 / 123 (corner, r3: 1), on the seam line itself. cap_float means unchanged (faces 0.2083, capsule rows
  0.0987, centre -0.1213); the outer row's max 0.237 -> 0.258 now equals the inner row's (the stack is symmetric).
- `layout.json` kit-1 section: tris, `ridge_noshi_layers` 4, `ridge_style`, 0.1 mm bbox rounding; nothing else.

## Renders (Cycles GPU, 64 spp, denoised; studio grey)
- Hall sheet: `round4/ridges/hall/sheet_hall.png` (front / side ortho with 1.8 m silhouettes, top, bay, 3/4); views
  `hall_front`, `hall_side`, `hall_top`, `hall_34`.
- Hall roof close-ups: `roof_r4_ridge_front` (panel b elevation), `roof_r4_apex` (the west ridge end from the gable),
  `roof_b1_ridge`, `roof_b2_ridgeend`, `roof_c1_hip`, `roof_c2_hipcorner`, `roof_d1_gable`, `roof_e2_verge34`
  (gable_roof demo with the new defaults).
- Gate sheet: `round4/ridges/kit1/sheet_gate.png` (front / side ortho with silhouettes, oblique top, 3/4); r4 views
  `r4_gate_front`, `r4_gate_side`, `r4_gate_top`, `r4_gate_34`, `r4_gate_ridge_close`, `r4_gate_apex`,
  `r4_gate_ridge34`; wall `r4_wall_front`, `r4_wall_34`, `r4_wall_ridge_close`, `r4_wall_end_elev`.
- Reference | ours (`round4/ridges/sbs/`): sbs_hall_sheet, sbs_hall_ridge_elev, sbs_hall_ridge_end34,
  sbs_hall_ridge_front_end, sbs_hall_apex, sbs_hall_hip, sbs_hall_hipcorner, sbs_gate_sheet, sbs_gate_front,
  sbs_gate_ridge_end_front, sbs_gate_apex, sbs_gate_ridge34, sbs_wall_ridge, sbs_wall_34, sbs_wall_end.
- Read: the ridges now read as stacked courses with joints under a collared cap row, in the field's dark blue-grey;
  from the gable the ends read as the sheets' crest-over-disc-with-lobes. The real judgement is on Unreal captures.

## Open / for the next stage
- Unreal: not imported by this track. Reimport the 21 hall FBX and the 28 kit-1 FBX as they are (same names and
  placements), then re-capture the ridges.
- Seen from the FRONT, the gate sheet's ends show a deeper cluster of round knobs past the gable (about 0.15-0.2 m)
  than ours (knob 0.10); `onigawara(knob=)` can take more if the Unreal judge still reads them as slabs.
- The wall's gable end keeps r3's `roll_end` (round end tile + a small stacked tile); the sheet's end view shows a
  slightly bigger curled end.
- The ridge tone in sun is the library RoofTile (glossy, partly metallic): the up-facing noshi ledges still catch the
  sky from above; the material is not this track's.
