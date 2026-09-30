
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
