# Dojo OUTSIDE + BACKGROUND track: build notes

## 2026-09-29 - ROUND 5: outside + background (final look pass, vegetation excluded)

User: "start with everything else and leave the vegetation for later". So there are no trees, plants or grass packs this
round. Trees stay grey-box and `layout_outside.json` lists 22 empty tree slots.

What was left alone:
- Headless Blender only; no MCP.
- No Unreal process was started. The combined DojoLab import is the showcase stage's job.
- Other chats' files are untouched: the modern kit's files and `layout_modern.json`, `DojoShowcase.blend` (read only),
  and the round-4 check copies.
- Nothing was committed.

Lock `DojoOutside` (claude, Assets/Dojo/DojoOutside.blend) is taken and kept for the fix round.

### Commands
```
py -3 Scripts/dojo/outside/ox_tex.py                          # T_DKX_Cobble + T_DKX_Kawara (numpy; PIL reads the library maps)
blender -b --factory-startup --python Scripts/dojo/outside/build_outside.py [-- --quick --no-export --no-context]
blender -b --factory-startup Assets/Dojo/DojoOutside.blend --python Scripts/dojo/{walk_check,climb_check,roof_walk_check}.py -- --layout outside/layout_outside_checks.json --out outside/checks/<x>.json [--hover 0.019]
blender ... --python Scripts/dojo/hall/hall_roof_walk.py | Scripts/dojo/outbuildings/ob_roof_walk.py  (same --layout / --out)
blender ... --python Scripts/dojo/outside/checks/{ox_corridor_checks,ox_sp_roof_walk,ox_clearance,ox_measure}.py [-- --asset shed|pavilion]
blender -b --factory-startup Assets/Dojo/DojoOutside.blend --python Scripts/dojo/outside/render_outside.py -- --samples 96 --scale 100 --tag r5
py -3 Scripts/dojo/outside/make_sheet.py r5
```
- `ox_corridor_checks.py` and `ox_sp_roof_walk.py` copy the round-4 check copies. Only the layout path
  (`outside/layout_outside_checks.json`) and the output folder (`outside/checks/`) changed.
- `ox_corridor_checks_baseline.py` is the same check on the UNCHANGED showcase, as a baseline.

### What was built (31 pieces, all `SM_DKX_*`, `Exports/DojoKit/Outside/`; QA 0 hard fails; UCX on every piece)
Frame: the grey-box world frame, metres. The town rectangle is X -86..130 (27 modules of 8 m), Y -34..76.

| Group | Pieces | Notes |
|---|---|---|
| Approach road (dojo1_reference1) | Road_W / _Gate / _E | Rounded granite cobbles (new `T_DKX_Cobble`, 16 cm stones, dark sandy joints), Y -2.85..-7.75. Crowned: -0.10 at the edges, -0.05 on the centre line |
| | Verge_W / _E | Wall-foot soil strip, Y -0.96..-2.30, at 0.00 to -0.01. Packed earth across the side-lane mouths. It dips to -0.03 under kit 1's apron |
| | Kerb_8m / _4m | Granite kerb stones, 0.20 wide. Near side top +0.03, continuous: under the apron it carries the apron's front slabs. Far side top +0.02 |
| | Gutter_8m / _4m | Dished granite channel stones, Y -2.50..-2.85, lips -0.10, 4.5 cm dip. They end 0.10 m under the apron's front step |
| | FarVerge_W / _E, Landing | The terrace-edge strip, Y -7.95..-9.20 at 0.00. The granite slab landing, X 14.4..29.6, lies between the street lamps as in the reference |
| | RailFence_4m | Timber post-and-rail fence, 1.0 m, at Y -9.05. There is no fence at the landing (the reference has none) |
| | Terrace_8m, Canal_8m, Water | Granite coping (+0.04) on a battered rubble retaining wall (library GraniteRubble) down to the canal bed (-2.45). The water is at -2.05, below a far bank wall and coping |
| | Ground_South, BoardFence_4m | The lower lane (-1.50, packed earth) and house plots. A 1.8 m board fence runs along the lane, with a gap every 6th module |
| Outside ground | Ground_W / _E / _N | Replaces `SM_DGB_Ground_Outside`. Soil, level with the courtyard for about 4 m round the walls, then undulating up to +-0.3 m. Packed-earth side lanes at X -12..-9 and 53..56, a north lane at Y 41.5..44.5. Skirts under every border hide T-junction cracks |
| Rear alley (spec 4.6) | AlleyFence_W / _E | Replaces `SM_DGB_AlleyFence` x2 with a dark board fence: back rails, cap board, end posts. A 0.9 m braced wicket gate at the veranda's level (+0.50) has iron strap hinges and a pull. See "Collision kept exactly" below |
| Town | House_A..E (43 placed) | Low-detail neighbours, no interiors, one UCX box each. Kawara roofs: geometry rolls plus the new `T_DKX_Kawara` courses, built on the library RoofTile maps. Plaster (cream / earthen), timber bases, posts and beams, lattice fronts, some lit shoji (library GlassAmber), a pent roof on the two-storey houses. Placed in rows along the lanes, a staggered second row, a mostly two-storey north row (dojo1_reference2's roofs over the outbuildings) and a row on the lower level |
| Far | FarGround | Flat olive plain from the town edge (0.3 m under it) out to 1.4 km, falling to -12 m. A stand-in until the vegetation pass |
| | Mountains_Near / _Far | Ridge rings at 0.9-1.35 km (ridge 30-90 m) and 1.6-2.2 km (ridge 120-300 m, inside the 2.4 km cloud dome). Flat blue-grey instances that the level's height fog hazes |

**Collision kept exactly (the alley fences):**
- The UCX of each alley fence is the grey-box hull, measured in world space: W = X 10.5-13.0, E = X 31.0-33.5, both Y 34.0-34.1,
  Z 0-2.0 (`checks/measure_outside.json` `alley_hulls_match_greybox: true`). The class stays `building`.
- The visual stays clear of the hall's rear corner posts and foundation stones. It sits behind the veranda deck's end; the
  clearance probe finds 0 contacts.

**Mountains as a far MESH, not an Unreal landscape:**
- The showcase pipeline imports FBX static meshes in one commandlet step (`dj_sc_import`) and places them from the layout
  (`dj_sc_level`). A Landscape needs a heightmap import through the editor's landscape tools. No commandlet step has that,
  and it could not be verified in the same fresh process as the meshes.
- Both rings are Nanite, have no collision (a 4 cm token UCX 60 m underground) and sit inside the 2.4 km sky dome.

### Materials (recipes in `layout_outside.json` "materials"; existing masters only, no new master)
| Instance | Master | Maps / values |
|---|---|---|
| M_DKX_RoadCobble | M_DJ_GroundXY_Master | `T_DKX_Cobble` on world XY / 4 m + ground macro. Albedo median sRGB (103, 100, 95) |
| M_DKX_VergeSoil / M_DKX_LaneEarth | M_DJ_GroundXY_Master | The ground kit's `T_DKG_Soil`. Verge: sat 0.85, value 0.80. Lanes: sat 0.55, value 1.25 (the shed's packed-earth values) |
| M_DKX_Kawara | M_DJ_Lib_Opaque | `T_DKX_Kawara` = the library `T_DJ_RoofTile_*` maps with courses every 0.2667 m. Median (58, 61, 67) against the library's (64, 67, 74) |
| M_DKX_Water / MountainNear / MountainFar / FarGround | M_DJ_Flat_Master | Linear colours from sRGB (26, 30, 30) / (46, 52, 60) / (70, 76, 90) / (50, 52, 42) |

Library slots on the pieces:
- M_DJ_Granite, GraniteRubble, TimberDark (+End), PlasterCream, PlasterEarth, RoofTile, GlassAmber, Iron.
- M_DJ_PlasterEarth on the houses takes the showcase's kit-1 triplanar instance. The compose reports a warning for it,
  and that is expected.

### Modern kit re-placed along the road (`layout_outside.json` "modern_instances"; its own files untouched)
- **Street lamps** (dojo1_reference1 shows two different lamps at the landing ends):
  - B at (14.0, -8.55), lantern toward the gate axis;
  - A at (30.0, -8.55), lantern toward the gate axis.

  Both stand on the terrace-edge strip. The round-3 positions (17 / 27, -4.5) were in the middle of the new road.
- **Poles:** every 25 m from X -65.5 to 109.5, at Y -8.55. That is 8 poles and 7 spans of 8 conductors plus telecom (56 + 7 wires).
  - The transformer stays on the X 9.5 pole.
  - Guys are on the end poles.
  - The gatehouse service drop is re-aimed from the moved rack. Its end point is unchanged: (17.90, -1.20, 3.20), measured.
- **Rule for the compose:** drop every showcase instance of these 8 modern pieces (37 rows) and place the 77 rows instead.
  The lamp lights follow (`LAMP_LIGHTS` has both lamps).

### Numbers (measured, `checks/measure_outside.json`)
- **Outside ground along the walls:** rays at 0.30 m and 1.00 m out, every 0.5 m, on all four sides (680 samples). The worst |z|
  is **0.038 m**, well inside the spec's 0.5 m (the south minimum is the verge's dip under the apron).
- **Street section** (at X 10.5 and X 0.5):

  | Point | z |
  |---|---|
  | Verge | -0.009 |
  | Near kerb top | +0.030 |
  | Gutter lip / centre | -0.106 / -0.144 |
  | Road edge / crown | -0.098 / -0.049 |
  | Far kerb | +0.017 |
  | Far strip | 0.000 |
  | Coping | +0.039 |
  | Water | -2.05 (2.09 m below the coping) |
  | Lower lane | -1.50 (1.54 m below the coping) |

  The kerb face stands **0.136 m** over the gutter lip.
- **Kit 1's apron front step** stands **0.141 m** over the road in front of it (step top +0.047, road -0.093 at Y -3.05).
- **Wall climbs from outside (BR):** 197.8-198.7 cm on all four sides. That is the GASP 2.5 m mantle set, so the wall stays
  climbable from outside. The stances are 0.45 m off the wall face, clear of the duel level's 1v1 ring.
- **Triangles:** 79,812 unique and 492,176 placed (houses 43 x 4.5-10.8k; every piece at or over 2k tris is Nanite).
  - Verge, Terrace, Canal, the board fence and the alley fences ship LOD0-2.
  - The rest ship 1 LOD, either because they are Nanite or under 400 tris.

### Checks (GASP capsule r 0.30, 1.72 m, step 0.45; `checks/`)
- **walk_check: PASS**, also at r 0.35.
  - 41 routes: the showcase's 31 plus 10 new ones.
  - 6 BR street routes are clear: along the road crown, road onto the gate apron, the verge along the wall foot, road up the kerb into the west lane and the north lane, the lower lane, and the west band along the wall.
  - 15 CONTROLs are blocked, 4 of them new: the alley fences from the veranda at +0.5, and on the ground.
- **climb_check: PASS.** Every route number is unchanged from round 4:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4 |
  | Shed crate -> band | 123.1 -> 122.9 |
  | Pavilion crate -> pad | 122.3 -> 197.9 |
  | Vending | 173.1 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Rack hurdle | 111.8 |

  Plus the 5 new outside wall climbs.
- **Roof walks: PASS** for kit-1 gate 3/3, hall 16/16, outbuildings 15/15, shed 5/5 and pavilion 6/6.
- **Corridor roof walk: "passed False" on BOTH this compose and the unchanged showcase.** The results are identical
  (`corridor_roof_walk_outside.json` == `corridor_roof_walk_showcase_baseline.json`).
  - Cause: the check's two CONTROLs, "corridor back up onto the outbuilding roof", are no longer blocked since round 4 f1
    turned the outbuildings gable-front. Route 3 became a walk, so walking back up is legitimate.
  - The CONTROL expectation is stale. This is not a regression from this track. FLAGGED for the corridor or showcase owner.
- **Clearance** (`checks/clearance_outside.json`): only intended grade contacts.
  - Verge under the wall footing and the gate-join rubble.
  - Kerb and road under kit 1's apron and front step.
  - Guy anchors buried in the far strip.
  - None at the alley fences, lamps, poles, rail fence or landing.

### Renders (Cycles, denoised, 96 samples, sunset rig as the other tracks: sun 13 deg from az 160, AgX; lamps lit)
`WorkFiles/dojo/build/outside/renders/r5/`:
- `SHEET_OUTSIDE_r5.png`: the references beside the renders.
- `ref1_overview.png`
- `ref2_establishing.png`
- `road_gate.png`
- `road_east.png`
- `terrace.png`
- `alley_W.png`
- `alley_E.png`
- `walltop_W.png`
- `skyline_NW.png`
- `junction_E.png`
- `junction_W.png`

Measured against the references:

| Region | Reference (sRGB) | Ours (sRGB) |
|---|---|---|
| Road (reference 1, dusk; our sunset) | (75, 75, 87) | (65, 62, 74) |
| Background roofs | (39, 41, 55) | (39, 39, 53) |
| Terrace wall in shade | (44, 38, 28) | (16, 13, 17): darker |
| Ridges | (60, 66, 84) - (109, 99, 113) | (123, 118, 140) |

The ridge colour here comes from Blender's preview-only haze mix; in Unreal the height fog sets it.

### Deviations / decisions (flagged)
- The road is rounded granite cobbles, not packed earth or asphalt: dojo1_reference1 shows a grey stony road.
- A canal runs under the terrace wall, with a lower lane and board fence beyond. The reference shows dark water and a lower
  lane with a board fence; the spec only says "a terrace".
- Lamps B (west) and A (east) sit at the landing ends. The reference's two lamps differ, and there are no other street lamps.
- The power line is extended to 8 poles over the whole town rectangle; the modern kit placed 4.
- The houses, lanes and far plain are this track's layout (the references show houses round the compound, not a plan).
  They are background tier: 2.56 px/cm would do, but they share the 5.12 tiling sets.
- The road's world-XY normal is mirrored in V in Unreal (world Y is flipped). This is the ground kit's existing behaviour; the
  cobbles are isotropic.

### Open (for the Unreal stage / judges)
- **Integration:** the showcase compose needs the round-5 hookup (`Scripts/dojo/outside/round5_outside.py` has everything):
  - the KIT entry, `/Game/DojoKit/Outside`;
  - a `T_DKX_` texture home;
  - `replaces_greybox`;
  - the modern street re-placement;
  - the new walk and climb routes.
- **The ridge and far-plain colour and haze need tuning on the UE captures** (fog density 0.02, falloff 0.12 at 1-2 km).
- Mountain silhouettes are smooth hills. If the judges want crisper ridgelines, raise the noise octaves in `ridge_heights`.
- Vegetation pass: 22 tree slots, including shrub beds at the gate apron, the wall bands and the lower lane. The grass on
  the outside ground and verges comes with it.
- The corridor check's stale CONTROLs (above).

### Scripts (new, not committed)
- `Scripts/dojo/outside/`:
  - `ox_tex.py`
  - `ox_common.py`
  - `build_outside.py`
  - `render_outside.py`
  - `make_sheet.py`
  - `round5_outside.py`
- `Scripts/dojo/outside/checks/`:
  - `ox_corridor_checks.py`
  - `ox_corridor_checks_baseline.py`
  - `ox_sp_roof_walk.py`
  - `ox_clearance.py`
  - `ox_measure.py`

## 2026-09-29 - ROUND 6: the 1v1 rear seal + the far background (Blender fixes stage)

User: "yes start first round. keep emblem for now". The emblem plaques are untouched; no vegetation (trees stay grey-box).
Headless Blender only, no MCP, no Unreal process started, nothing committed. Lock `DojoOutside` (claude) refreshed and
kept. Other chats' files untouched (the showcase blend and layouts are read only). Output folder:
`WorkFiles/dojo/build/round6/build/` (round-5 scripts, layouts and check JSONs backed up there first:
`*_r5_backup.py`, `r5_layout_backup/`, `r5_checks_backup/`).

### 1. The 1v1 rear area is now sealed (verify_r5 fail 1)
**What was open** (mapped on the real UCX of the combined compose; `checks/alley_seal.json`, mode `r5`):
- ground: the corridors' north walls end at their last post (X 10.14 / 33.86). The 0.9 m between that post and the
  veranda post (X 11.05), and the veranda's side edge (X 11.0, Y 32.2-34.0), opened straight into the pocket, and the
  pocket runs on into the strip behind the hall. This is the verify_r5 path, reproduced: 188,748 pocket cells reached;
- roofs:
  - the hall's lower side roofs: off the eave into the pocket, and off their north end into the strip;
  - the corridor north slopes, entered from the lower roof across the 0.2 m gap at X 10.30-10.50;
  - the outbuildings' north roof halves, through a 0.6 m slot between the grey-box corridor-ridge and outbuilding-ridge rects;
  - the hall's upper rear half: from the lower roof a double jump reaches the hips' rear halves, and the grey-box ridge
    rect only covers Y 29.0;
- the north wall top behind the outbuildings (X -1 to 7.6 and 36.4 to 45) had no blocker.

**The fix** (`build_outside.py` "round 6: 1v1 rear seal"). Every piece below is listed in `layout_outside.json`
`onev1_only` and sits in folder `Boundary_1v1` (Unreal tag `Dojo/Boundary_1v1`), so the BR copy drops them.

| Piece | Kind | World box(es) X / Y / Z (m) | Closes |
|---|---|---|---|
| SM_DKX_PocketFence_W / _E | visible: the alley fence's board-fence style, 1.98 m, 2 UCX | 10.50-10.60 (E 33.40-33.50) x 32.24-34.00 x 0-2.0; return 10.14-10.50 (E 33.50-33.86) x 32.24-32.34 | the pocket's side, from the corridor's last post to the alley fence |
| SM_DKX_AlleyFence_W / _E | visible (round 5, unchanged) | grey-box hull | the veranda's rear ends |
| SM_DKX_1v1_PocketSide_W / _E | invisible | 10.40-10.50 x 32.22-34.10 x 0-20; 10.40-10.50 x 31.00-32.23 x 2.75-20 (E 33.50-33.60) | behind and over the pocket fence; the gap between the lower-roof eave and the corridor roof |
| SM_DKX_1v1_CorridorRoof_W / _E | invisible | 7.00-10.50 x 31.00-31.10 x 2.75-20; 6.99-7.10 x 31.00-31.80 x 2.75-20 | the corridor ridge, and the link to the outbuilding cut (the 0.6 m slot) |
| SM_DKX_1v1_OutbuildingRoof_W / _E | invisible | -1.00-7.10 (E 36.90-45.00) x 31.70-31.80 x 2.0-20 | the storehouse / residence north roof halves (routes 2 and 3 stay south) |
| SM_DKX_1v1_HallRear | invisible | 10.40-33.60 x 34.00-34.10 x 0-20 | the strip's south face: alley fences, the side roofs' ends, the upper rear overhang |
| SM_DKX_1v1_HallUpperRear | invisible, 3 UCX | ridge 12.00-32.00 x 29.00-29.10 x 5.30-20; hips 12.00-12.10 / 31.90-32.00 x 28.99-34.10 x 5.45-20 | the upper roof's rear half, hips included |
| SM_DKX_1v1_NorthWallTop | invisible | -1.00-45.00 x 36.00-37.00 x 2.0-20 | the whole north wall top |

- The invisible pieces are class `boundary`: Pawn block, Camera / Visibility ignore, hidden in game, no shadow. Their
  material M_DKX_Blocker1v1 is flat red, for the editor only.
- They reach +20.0, meeting the duel level's ring (Y 37.0) and ceiling (+20).
- They repeat the grey-box set's rear rects, so they seal the area without depending on SM_DGB_Boundary_1v1, which is
  kept as it is.

**Proof** (`Scripts/dojo/outside/checks/ox_alley_seal.py` writes `round6/build/checks/alley_seal.json`; the plan
picture is `alley_seal_plan.png`):
- FLOOD with a FLYING GASP capsule (r 0.30, 1.72 m; any jump, double jump, mantle or fall is a subset of what it can
  do) through the whole compound inside the ring, on 0.1 m cells, with capsule bottoms from +0.05 to +18.25:
  - `1v1`: 23,767,037 cells reached, and **0** in every rear target: both pockets, the strip, both corridor north
    slopes, both outbuilding north roofs, the hall's upper rear half, the north wall top. The area is **sealed**;
  - `r5` (without this round's pieces): the leak reproduces in every target (pocket W 188,748 cells, strip 600,336);
  - `br` (no boundary class, no 1v1 fences): every target is open, so the BR back way works.
- CONTROL paths (a capsule swept every 2 cm at a fixed feet height): **32 / 32 blocked** in the 1v1, none of them
  blocked at its start.
  - **30 of the 32 are clear in the BR**, so the 1v1 set is what stops them:
    - on the ground: from the corridor end deck, the corridor floor, the veranda edge and the side yard;
    - hops over both fences;
    - off the lower side roof's eave and off its north end;
    - a hop onto the corridor north slope, and a double jump over the corridor ridge;
    - along the outbuilding roof past the cut, and through the old slot;
    - a double jump onto the upper hip; over the upper ridge at +9.5; a flight at +15 over the hall.
  - The other 2 (the west / east wall top round the corner) are stopped by the outbuilding eave in both modes.
- POSITIVE paths beside the new blockers: **10 / 10 clear**. They are:
  - the corridor floor to the veranda;
  - the veranda side to its rear end;
  - the lower side roof to its north end;
  - route 3 off the corridor's south slope;
  - the side yard along the corridor.
- walk_check (the showcase's AABB format): PASS at r 0.30 and at 0.35, 47 routes.
  - The 6 new `CONTROL_alley_pocket_*` routes are all blocked by the round-6 pieces.
  - They reach the showcase through `round5_outside.WALK_ROUTES`.
  - Two first tries were dropped because they proved nothing: they stopped at the deck's 0.5 m edge and at the wall's
    step pier, before reaching the seal.

**Every existing number kept** (final bytes, `round6/build/checks/` compared with `r5_checks_backup/`):
- climb_check: PASS, and all 30 routes are byte-identical to round 5:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4 |
  | Shed crate -> band | 123.1 -> 122.9 |
  | Pavilion crate -> pad | 122.3 -> 197.9 |
  | Vending | 173.1 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Hurdle | 111.8 |
  | Outside wall climbs | 197.8-198.7 |

- Roof walks:
  - kit 1 gate 3/3, outbuildings 15/15, shed 5/5 and pavilion 6/6: identical;
  - hall 16/16: PASS. One BR-only CONTROL (`CONTROL_upper_end_slope_into_the_gable`) now blocks 6 cm earlier, at
    (14.20, 29.0). The cause is the dressing track's smaller hall-gable emblem board (r5 f1), not this round.
- Corridor roof walk: identical to round 5. It still reports "passed False", only because of its two stale CONTROLs
  (flagged in round 5).
- measure: identical, except 0.1 mm on kit 1's apron (float noise in the showcase context).
- clearance: two new contacts, where the pocket fences' boards rest on the corridor end deck's 7 cm edge strip
  (16 vertices each side). The return panel stops 2 cm short of the corridor post's foot block. Nothing else.

### 2. Far background (the final judge's "primitive background" gap)
- **The "outline strokes" were found:**
  - The round-5 f1 ridge rings were smooth-shaded, so every crest vertex normal pointed straight UP, at 90 deg to any
    view from the town.
  - M_DJ_EmissiveFlat_Master has no Specular input, so it uses the default 0.5. At that grazing angle its Fresnel term
    reflected the bright sunset sky, which drew a bright line along every crest.
  - The fix: CUSTOM NORMALS on all four rings, horizontal toward the compound centre and tilted 12 deg up, so N.V is
    about 0.98 from anywhere in the town.
  - Verified on the EXPORTED FBX in a fresh process (`checks/fbx_ridge_normals.json`): on all four rings the horizontal
    cos to the centre is >= 0.99991, and the normal z is 0.2051-0.2056.
  - The first export bent the normals by up to 25 deg, because the FBX exporter's own triangulation re-encodes custom
    normals. The rings are now triangulated before the normals are set.
- **Jagged ridges:**
  - `ridge_heights` is now a periodic ridged fractal: 1 - |S| octaves from 9 to 288 cycles a turn at gain 0.55, over a
    broad massing, shaped ^1.35.
  - Each ring has 1,440 samples (0.25 deg) and four rows: foot, shoulder, crest and back fall.

    | Ring | Distance | Heights | Sharp peaks |
    |---|---|---|---|
    | 1 | 0.56 km | 14-46 m | 17 |
    | 2 | 0.98 km | 28-88 m | 14 |
    | 3 | 1.52 km | 50-150 m | 13 |
    | 4 | 2.08 km | 85-225 m | 7 |

  - Elevations are 1.4-6.2 deg. The back ring ends at 2.25 km, inside the 2.4 km dome.
  - Colours are unchanged: the r5 f1 emissive ladder from (58, 64, 82) to (128, 124, 148), so value and saturation
    fall toward the sky.
- **The far town, as impostors of our own houses:**
  - `ox_facade.py` bakes albedo elevations of SM_DKX_House_A..E (5 fronts, 3 sides) under a uniform white sky. It uses
    the Standard view, so open faces render at their albedo and the eaves' occlusion is baked in.
  - `ox_facade_atlas.py` packs them into T_DKX_FarFacade_BC / ORM / N (2048 x 1024, 8 tiles of 512).
  - Every far house is about 20 tris and wears:
    - its type's front on the street side, and a side tile elsewhere;
    - a plaster patch on the gables (M_DKX_FarFacade);
    - kawara roofs (M_DKX_FarKawara: the town's tile set at ValueMult 0.62, Saturation 0.8).
  - The flat M_DKX_FarRoofA/B and M_DKX_FarWallPlaster/Wood are retired (`round5_outside.RETIRED_MATERIALS`).
- **The hard straight edge:**
  - An EDGE ROW of 74 houses stands just outside all four sides of the town rectangle, fronts turned in. The road,
    lanes, canal and lower lane now end at house fronts (render `road_end_E.png`).
  - The far districts keep clear of that band. FarGround stays under the town and ring 1's foot.
- **Budget:**
  - The far meshes are 71,386 tris (r5 f1: 70,052): FarTown 35,866 (1,966 houses), the rings 4 x 8,640, FarGround 960.
  - The whole kit is 137,590 unique / 521,962 placed (r5: 134,184 / 518,556).

### Export / QA
- 45 pieces: 34 + 2 pocket fences + 9 blockers.
- **QA: 0 hard fails.** Every SM_ has a UCX (the blockers carry their boxes). Everything went through Scripts/pipeline
  to `Exports/DojoKit/Outside/`.
- qa_check now uses the operator UV-overlap method above 20k tris. The SAT method on the 35.9k-tri far town ran out of
  memory at 25 GB.

### Renders (Cycles 64 spp, `round6/build/renders/`)
- far_background
- approach_road
- road_end_E
- horizon_N
- ref2_establishing
- skyline_NW
- walltop_W
- alley_W
- pocket_W
- pocket_E
- seal_blockers: top-down, north at the bottom, with the 1v1 blockers in translucent red

The ridge previews use emission of their target colour; Unreal lays the height fog on top.

### For the Unreal stage
- Import the new FBX and T_DKX_FarFacade_*.
- Create the new instances M_DKX_FarFacade / M_DKX_FarKawara (M_DJ_Lib_Opaque) and M_DKX_Blocker1v1 (M_DJ_Flat_Master).
- If the showcase wants a clean project, delete the four retired far-town instances.
- Keep FBX normal import ON for the ridge rings (FBXNIM_IMPORT_NORMALS, as dj_sc_import already has): the rim fix
  lives in the normals. If a rim remains in a capture, the next lever is a Specular input on
  M_DJ_EmissiveFlat_Master (a showcase-owned file).
- Re-run the verify_r5 flood and pocket probes. The expected result is 0 alley cells; the ring and ceiling stay the
  grey-box's.

### Scripts (new or changed, not committed)
- Changed:
  - `build_outside.py`: the 1v1 seal, the far-town impostors and edge row, the ridged rings with custom normals, the
    routes, and `onev1_only`;
  - `ox_common.py`: the FarFacade / FarKawara / Blocker recipes, the FarFacade textures, the previews, and the overlap
    threshold;
  - `render_outside.py`: `--outdir`, the round-6 views, and the blocker / ridge previews;
  - `round5_outside.py`: ONEV1_ONLY and RETIRED_MATERIALS;
  - `checks/ox_clearance.py`: now skips the far pieces and the invisible blockers.
- New:
  - `ox_facade.py`
  - `ox_facade_atlas.py`
  - `checks/ox_alley_seal.py`
  - `checks/ox_alley_seal_plot.py`
  - `checks/ox_fbx_normals.py`
- Runner: `WorkFiles/dojo/build/round6/build/run_r6_checks.sh`.


## 2026-09-30 - ROUND 6 FIX f1: lower ridges, far town in distance bands (the Blender outside stage of the fix pass)

User: "yes start first round. keep emblem for now". The plaques are untouched; vegetation comes later.
- Headless Blender only.
- Lock `DojoOutside` (claude) refreshed and kept.
- Nothing committed.
- Backups: `unreal/round6/f1_work/start_backup/`.

### Ridges
The round-6 judge: "too tall and too close; in ref 2 the hills barely clear the rooftops".
- Every ring's base and amplitude are x0.6 (`RIDGE_SCALE`).
- Seeds, radii, silhouettes and custom normals are unchanged.

| Ring | Height (m) | Elevation from the centre (deg) |
|---|---|---|
| 1 | 8.4-27.6 | 0.86-2.82 |
| 2 | 16.8-52.8 | |
| 3 | 30-90 | |
| 4 | 51-135 | 1.40-3.71 |

### Far town
The judge: "one repeated house type on a regular grid, evenly and brightly lit; darken the far rows".
- **Three distance bands** from the compound centre (`ox_common.FAR_BANDS`: 170 / 290 m). Same maps, same master.

  | Band | Facade (ValueMult, Sat) | Kawara (ValueMult, Sat) | District houses |
  |---|---|---|---|
  | near | M_DKX_FarFacade (unchanged) | M_DKX_FarKawara (unchanged) | 228 |
  | mid | M_DKX_FarFacadeMid (0.62, 0.75) | M_DKX_FarKawaraMid (0.46, 0.7) | 730 |
  | far | M_DKX_FarFacadeFar (0.42, 0.6) | M_DKX_FarKawaraFar (0.34, 0.6) | 1,057 |

  The 71 edge-row houses come on top of these.
- **Variety:**
  - every block gets its own yaw (+-9 deg) and roof-pitch range (a base of 17-24 deg, plus 6-12 deg);
  - every house gets another +-3 deg of yaw;
  - 4 % of houses are three-storey (eave 7.0-8.4 m).
- **Tris:** SM_DKX_FarTown 38,098 (r6: 35,866). The kit is 139,822 unique (r6: 137,590).

### Export and checks
- **Export:** 45 FBX through Scripts/pipeline. QA: 0 hard fails, and every SM_ has its UCX.
- **Compose:** `compose_showcase.py` re-run: 253 pieces, 1,110 instances, 86 decals. Its one warning is the old
  PlasterEarth note.
- **Checks** (`round6/build/checks_f1/`; runner `unreal/round6/f1_work/checks/run_outside_checks_f1.sh`): every result
  is **identical** to `round6/build/checks/`:
  - alley seal, walk, climb;
  - the kit-1, hall, outbuilding, corridor, shed and pavilion roof walks;
  - clearance and measure.

  The far pieces have no collision and sit outside every check volume.
- **Framing study:** Workbench renders on DojoOutside.blend (`unreal/round6/f1_work/wb_cams.py`, `wb/grid1-2.png`).
  - From any eye under the gate roof (<= 3.1 m), the hall and the outbuildings hide the whole town.
  - From about 5.5 m up, the town and the ridges show between the hall hips and the outbuilding gables.
  - This is why CAM_Ref2Match was raised (see BUILD_NOTES.md).

### Changed (not committed)
- `build_outside.py`: far_house mats / pitch, the far_town bands and variety, RIDGE_SCALE.
- `ox_common.py`: the four band recipes, and their preview dispatch.
