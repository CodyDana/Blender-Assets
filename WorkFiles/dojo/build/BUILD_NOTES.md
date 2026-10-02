# Dojo arena build notes

Spec: `WorkFiles/world/DOJO_ARENA_SPEC.md`, look: `WorkFiles/world/STYLE_GUIDE.md`, references: `References/Dojo/`
(AI-generated, modelling reference only, `REFERENCE_LOG.md`). Lock: `DojoKit` (claude, `Assets/Dojo/DojoGreybox.blend`).

## 2026-09-27 - Stage 1: DojoLab + GASP traversal + grey-box

### Commands (all headless; no GUI, no MCP)
```
py -3 Scripts/dojo/unreal/make_dojolab.py                        # project copy (idempotent; re-run: 0 copied, all unchanged)
bash Scripts/dojo/unreal/run_dojo_unreal.sh gasp                 # GASP facts -> unreal/gasp_inspect.json + gasp_t3d/
py -3 Scripts/dojo/unreal/gasp_graph_dump.py <t3d> <Graph>       # readable Blueprint graph (pin defaults, links)
blender -b --factory-startup --python Scripts/dojo/build_dojo_greybox.py [-- --no-export]
blender -b --factory-startup Assets/Dojo/DojoGreybox.blend --python Scripts/dojo/render_greybox.py   # renders/wb_*.png
blender -b --factory-startup Assets/Dojo/DojoGreybox.blend --python Scripts/dojo/walk_check.py
blender -b --factory-startup Assets/Dojo/DojoGreybox.blend --python Scripts/dojo/climb_check.py
bash Scripts/dojo/unreal/run_dojo_unreal.sh bounds gamemode import materials level verify capture
```
Every Unreal step checks first that no UnrealEditor.exe has DojoLab open and waits while any UnrealEditor-Cmd runs (one at a
time machine-wide). Timings: `unreal/logs/timings.txt` (gamemode 63 s, import 54 s first / 8 s skip, materials 10 s,
level 17-33 s, verify 16 s, capture 48-54 s).

### 1. DojoLab project
- `C:/Users/Cody/Documents/Unreal Projects/DojoLab/DojoLab.uproject`: GASP's .uproject + PythonScriptPlugin +
  EditorScriptingUtilities (Epic sample hash dropped); Config copied, DefaultEngine / DefaultGame generated; Content copied
  (3898 files, 5.84 GB); DerivedDataCache / Intermediate / Saved / Binaries / Build not copied. Source untouched (0 files in
  GameAnimationSample or DemoGame_1 newer than DojoLab.uproject).
- Render settings = GASP's plus DemoGame_1's: added r.RayTracing, RayTracingProxies, r.Substrate (+ GBuffer format), local
  exposure contrast 0.8; AllowStaticLighting 0 -> False; Lumen GI + reflections, VSM, distance fields already on; DX12 with
  SM6. `Interchange.FeatureFlags.Import.FBX=0`. Default + startup map `/Game/Dojo/Maps/L_Dojo`.
- Game mode: GASP's `GM_Sandbox` defaults to **SandboxCharacter_Mover**, so `/Game/Dojo/Blueprints/GM_Dojo` (child of
  GM_Sandbox, `dj_gamemode.py`) sets DefaultPawnClass = **SandboxCharacter_CMC** (the CMC character the game's BP_NinjaGasp
  copies); project GlobalDefaultGameMode and the level's world settings both use GM_Dojo. 2030 hard /Game dependencies of
  GM_Dojo + the character, 0 missing.

### 2. GASP traversal (full write-up: `GASP_TRAVERSAL.md`)
- Marking: only `LevelBlock_Traversable` actors are traversed (a cast in AC_TraversalLogic), found by a capsule trace on the
  Traversable channel; ledges = its 4 top-edge splines (min 60 cm, contact 30 cm from ends), room checks on Visibility.
- Ranges (CHT_TraversalMontages_CMC, ground): mantle 0-150 cm (1 m set) and 150-**275** cm (2.5 m climb set), depth >= 59 cm
  or thin with the floor behind level; hurdle and vault **<= 125** cm over <= 60 cm thick obstacles (hurdle: >= 50 cm above
  the floor behind; vault: the far side drops > ~1.36 m). Capsule r 30 / half height 86 cm, step 45 cm, walkable 44.77 deg,
  jump apex 127.6 cm.

### 3. Grey-box (Blender)
- `Scripts/dojo/build_dojo_greybox.py` -> `Assets/Dojo/DojoGreybox.blend`, 48 pieces `SM_DGB_*` (63 instances, 1484 tris,
  UCX convex hulls, flat collision plane per roof slope, UV0 world 2 m + UV1 lightmap), QA 0 hard fails (the flat-colour
  pieces waive uv0_tile_range / uv_no_overlap as the armory does), exported through Scripts/pipeline to `Exports/DojoKit/`.
- 22 flat colours (`M_DGB_*`), one per class: sand, path, gravel, outside, wall, plaster, timber, veranda, stone, 3 roof
  greys, steel, climb prop orange, **landing yellow**, modern teal, thin uprights, trunk, canopy, boundary red, fence, drum.
- 8 collision classes (spec 5.3) in layout.json, applied per actor in Unreal: ground / building / roof / landing (block
  all), climbprop (camera ignore), thin + tree (camera + visibility ignore), boundary (Pawn only, hidden in game).
- The 1v1 boundary is its own piece `SM_DGB_Boundary_1v1` (outer ring on the wall top's outer edge 0-20 m, ceiling +20,
  hall ridge, outbuilding + corridor ridges, north wall top), folder Boundary_1v1 with the two alley fences.
- `WorkFiles/dojo/build/layout.json`: pieces, instances (folder, class), materials, 28 traversal markers, P1 / P2, sun,
  cameras, climb and walk routes. Review renders: `renders/wb_CAM_Overview.png`, `wb_CAM_Establishing.png`,
  `wb_CAM_WallTop.png`, `wb_top_ortho.png` (the top view lines up with DOJO_ARENA_TOPDOWN.png).

**Decisions / deviations (all flagged, measured reasons in GASP_TRAVERSAL.md section 4):**
1. **Landings.** GASP cannot mantle onto a sloped edge (the top sweep hits a 25 deg slope 10.6 cm in; replayed:
   `climb_check.json` 4-spec and 5-spec, depth 10.6 / 10.8 cm, "no root chooser row"). Every eave arrival gets a flat
   landing (yellow): 1 x 1 m wall piers, top +3.25, at the gatehouse sides and at the storehouse / residence corners
   (routes 6, 2); 1.2 x 0.75 m pads at the lower eave +3.0 above the cisterns (route 4); 1.5 x 0.75 m pad at the pavilion
   eave +3.25 (route 7); a flat 0.75 m front band on the shed lean-to (route 7; the rest slopes +3.0 -> +2.5).
2. **AC units** top +5.10 (spec +4.75), 1.2 x 1.0 m, entirely outside the upper eave line: the last rise to the upper eave is
   a 0.40 m walk-up step (0.75 m is neither walkable nor mantle-able onto a slope).
3. **Gatehouse roof hipped** (eaves all round +3.25, ridge +4.4, 8 x 5 m roof, posts 3.5 m apart in Y ("about 4 m deep" with
   the second post line)); the sheet's gable would leave the wall-top runner under a verge 2.2-2.4 m high. For the kit: an
   irimoya (hip-and-gable) keeps the sheet's ridge ends and this eave.
4. **Storehouse / residence roofs** extend over the perimeter wall they are built into (X -1 / 45).
5. Cisterns moved to X 13.05-14.25 / 29.75-30.95 (in front of the hall corners, clear of the lower-roof hip corners), Y
   19.3-20.5 (clear of the pad above).
6. Veranda Y 21.7-34 (its front 0.3 m is the second tread), step band tread Y 21.4-21.7 at +0.25.

### 4. DojoLab level and checks
- `/Game/Dojo/Maps/L_Dojo` (`dj_level.py`): 101 actors = 63 mesh actors + 28 `LevelBlock_Traversable` markers + P1 / P2 +
  sun, sky atmosphere, sky light (real-time), height fog, PPV + 3 cine cameras. Folders Dojo/{Ground, Wall, Gatehouse, Hall,
  Outbuildings, Yard, ClimbProps, Landings, Trees, Boundary_1v1, Traversal, Gameplay, Lighting, Cameras}. Sun: 7 deg high
  from azimuth 160 (W-N-W), 12 lux, 3000 K, atmosphere sun. KillZ -1000.
- **Bounds gate**: 63/63 mesh actors equal the Blender bounds converted, max error **0.0007 cm**. Markers: ledge splines on the
  box top edges, max error **0.0 cm**, mesh bounds 0.0 cm.
- **Fresh-process verify** (`unreal/verify.json`) all 5 gates PASS: meshes (48, hull counts = UCX, tris = Blender, slots = MIs
  on M_DGB_FlatMaster); level (63 mesh actors, collision responses per class, boundary hidden + Pawn-only); traversal (28
  markers hidden, Traversable-only, 4 ledges each, every climb route's marker present); gameplay (GM_Dojo, pawn
  SandboxCharacter_CMC, P1 (1450, -1050) facing +X, P2 (2950, -1050) facing -X, 15.0 m apart, 0 missing deps); environment.
- **Walk check** (`walk_check.json`, GASP capsule r 0.30, step 0.45): 13 / 13 routes clear (floor P1 -> P2, both yards past
  tree and well, gate -> path -> steps -> veranda +0.5, veranda sides -> both corridors, vending / crate fronts, under the
  gatehouse to the leaves, three wall-top runs at +2.0); 4 / 4 CONTROL routes blocked (closed gate leaves, hall body, gate
  pier from the wall top, the 1v1 boundary off the wall top). At the spec's 0.35 radius one route blocks: the 0.30 m step
  tread (the capsule cannot centre on it in this box model) -> make treads >= 0.35 m in the kit.
- **Climb check** (`climb_check.json`, GASP's own steps replayed on the UCX hulls): routes **1-8 all work**; plus veranda
  (+0.5 mantle), pavilion plinth (+1.0 mantle), weapon rack (hurdle, 1.20 m / 0.40 m). Per climb: 1 wall top 200 cm, depth
  100 -> Mantle 2.5 m set; 2 / 6 piers 124.8 cm, depth 110.5 -> Mantle 1 m set, then 0.0 m walk onto the eave; 3 drops of
  1.22 / 0.51 m; 4 cistern 125 cm (depth 145) then pad 174.8 cm (depth 85.6) -> Mantle 2.5 m set; 5 AC 193.7 cm (depth 100)
  -> Mantle 2.5 m set, then a 0.40 m step; 7 crates 125 cm, shed band 124.8 cm (depth 94.6), pavilion pad 199.8 cm (depth
  85.9); 8 vending 175 cm (depth 80) -> Mantle 2.5 m set, then a 0.25 m step. Spec as written: 4 and 5 FAIL (depth 10.6 /
  10.8 cm onto the 25 deg eaves).
- **Captures** (`unreal/captures/`, offscreen D3D12 editor, Lumen on, 96 frames): `CAM_Overview.png` (above the gate),
  `CAM_Establishing.png` (from the gate under the gatehouse roof, 1448 x 1086 = reference 2's aspect; the reference's
  camera is not reproducible at spec scale: fitting its floor edges drives the camera to 15 m or more behind the gate and about 14 m up, the edge of the search), `CAM_WallTop.png`
  (eye height on the west wall top, looking north to the storehouse pier).

### Open / next
- Not yet played in PIE; the climb check is GASP's logic replayed geometrically, not the animation.
- LevelBlock's construction script logs "index 0 of GetAllActorsOfClass" (no LevelVisuals actor in L_Dojo): harmless, markers
  are hidden. Hall doors and interiors closed (user decision).
- Spec numbers to change: R8 low cover (10-50 cm thin cover is not traversable), R3 (GASP needs >= 59 cm deep tops or a
  level floor behind), R4 (sloped roofs need flat landings for mantles), AC top +5.10, capsule 0.30 / 1.72 m, jump 1.28 m.
- Next stage: KIT 1 (perimeter wall footing / body / cap with 2.0 / 2.5 / 3.0 m variants, gatehouse) replacing the grey-box
  wall and gatehouse pieces; the landing piers become the gatehouse sleeve walls.


## 2026-09-27 - Stage 2: KIT 1 (perimeter wall + gatehouse) in Blender

### Commands (headless, --factory-startup; lock DojoKit, claude, Assets/Dojo/DojoKit1.blend)
```
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/kit1_textures.py
blender -b --factory-startup --python Scripts/dojo/build_kit1.py [-- --no-export] [--no-lods]
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/walk_check.py  -- --out kit1/walk_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/climb_check.py -- --out kit1/climb_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/roof_walk_check.py
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/render_kit1.py -- --what wall|gate|variants|beauty --samples 160 --tag r5
py Scripts/dojo/compose_kit1.py r5
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <ref.png> <sheet.png> <out.png>
```
Library: `Scripts/dojo/kit1_geo.py` (raw parts, primitives, the shared kawara tile system: pans laid in courses,
collared round tiles, eave discs, noshi ridge + ridge roll, verge / hip rolls, bisect clipping, weld). The build takes
about 2 minutes including LODs and export.

### Layout files
- `layout_greybox.json` is the grey-box layout (build_dojo_greybox.py now also writes it). `build_kit1.py` reads it
  and writes **`layout.json` with kit 1 in place of the 13 grey-box wall / pier / gatehouse / leaf / gate-roof
  pieces**, replacing the file atomically (other stages read grey-box prop positions from it; those are all kept).
  It also writes `kit1/layout_kit1.json`. Re-running the grey-box overwrites layout.json, so re-run build_kit1.py
  after it.
- New keys in layout.json:
  - `materials_kit1`: texture sets, tile 4 m, params.
  - `kit1`: cap height, body tops per variant, the assembled variants T200 / T250 / T300, gate-leaf placements (closed
    and open), lamp light positions, gate-roof numbers.
- Pieces carry `nanite` and `kit: kit1`. Kit 1 has 26 unique meshes and 152 instances (199 in total with the kept
  grey-box pieces).
- **For the Unreal stage:** the kit-1 FBX are in `Exports/DojoKit/Kit1/` and the textures in
  `Exports/DojoKit/Kit1/Textures/`. dj_import, dj_materials and dj_verify still expect only SM_DGB_ files in
  Exports/DojoKit and flat M_DGB instances, so they need a kit-1 branch: textured instances, world-aligned plaster,
  vertex colour R = moss and G = grime, and the LOD screen sizes from the sidecars.

### Numbers (measured)
- Wall:
  - Footing 0.50 m of granite; the stones stand 1.8-4.5 cm proud.
  - Plaster body from +0.5 m up to the cap.
  - Cap 0.4655 m tall: pitch 20 deg, eave 0.17 m past each face, 1.34 m wide. The top of the ridge roll is the wall
    top.
  - Body tops: T200 1.5345, T250 2.0345, T300 2.5345 (plaster 1.03 / 1.53 / 2.03 m).
  - Collision: one box per module (footing / body / cap). The cap's top is flat at the wall top on the 1.0 m strip,
    the same boxes as the grey-box wall.
- Layout:
  - The S, N, W and E runs use 4 / 2 / 1 m modules; every other footing is turned 180 deg for stone variety.
  - The grey-box's odd run lengths (26.4 m, 8.6 m) are absorbed by modules that run 0.4-0.6 m into the 1.4 m wide
    piers, where they are hidden, so no fitted modules are needed.
  - 4 corner blocks and 4 piers (1.0 x 1.4 m, flat top +3.25).
- Gatehouse:
  - Roof 8 x 5 m, eave +3.25 on all four sides, planes meeting at +4.4. The ridge-roll top is +4.533 and the upturned
    ends reach about +5.0.
  - Hip skirts have a 0.9 m run (skirt top +3.67); gables at x +/-3.1, verge at +/-3.35.
  - Opening 4.0 x 3.5 m; leaves 1.985 x 3.4 m on a +0.10 threshold.
  - Door posts rise to +3.82 with the lintel at +3.5-3.82. Four corner posts at (+/-3.1, +/-1.75), so the post lines
    are 3.5 m apart.
  - Collision: 7 roof hulls (S/N lower and upper bands, 2 skirts, the ridge stack), 13 frame hulls, 1 hull per leaf,
    2 for the paving.
- Triangles (LOD0):

  | Piece | Tris |
  |---|---|
  | WallFooting 1 / 2 / 4 m | 2652 / 5100 / 9212 |
  | WallFooting End / Corner | 2028 / 1612 |
  | WallBody 1 / 2 / 4 m | 28 / 44 / 76 |
  | WallCap 1 / 2 / 4 m | 2376 / 4648 / 9192 |
  | WallCap End / Corner | 3384 / 3312 |
  | Wall_Pier | 6808 |
  | Gate_Frame | 8688 |
  | Gate_Roof | 61924 |
  | Gate_Leaf_L / R | 4564 each |
  | Gate_Lamp | 292 |
  | Gate_Paving | 3544 |
  | **Unique total** | **134,344** |

- **Nanite** (tile- and stone-heavy pieces): all footings, all caps, the pier and Gate_Roof.
- LODs:
  - Every piece of 400 tris or more ships LOD0-2 (Collapse 0.5 / 0.25). The sidecar sets screen sizes 1.0 / 0.5 /
    0.25; on the LODs, UV1 is re-packed and non-manifold faces are removed.
  - The bodies (28-76 tris) and the lamp (292) ship one LOD; that is their LOD statement.
- QA:
  - 26 / 26 pieces with 0 hard fails. The tiling pieces waive uv0_tile_range / uv_no_overlap, as the armory does.
  - Texel density 5.06-5.12 px/cm against the 5.12 target.
  - All LOD1 / LOD2 meshes pass (0 fails). 26 FBX exported through Scripts/pipeline.
- Checks (GASP capsule r 0.30 m, 1.72 m tall, step 0.45 m):
  - Walk: 13/13 routes clear; 4/4 controls blocked (closed leaves, hall, gate pier, 1v1 ring).
  - Climb: routes 1-8 all WORK and the grey-box numbers are unchanged:
    - wall top: height 200 cm, depth 100 cm -> Mantle, 2.5 m set;
    - piers: 124.8 cm, depth 110.6 cm -> Mantle, 1 m set, then a 0.0 m walk onto the eave;
    - route 8: 175 cm, depth 80 cm, then a 0.25 m step.
  - New `kit1/roof_walk_check.json`: 5/5 paths clear, pier -> hip skirt -> slope -> ridge on both sides. In the 1v1
    only the N slope counts, because the 1v1 ring cuts the roof at the wall's outer face; the BR paths use the S slope
    and cross the ridge. Max floor slope 25.0 deg.

### Decisions / deviations (flagged)
1. **The gate roof is an irimoya (hip-and-gable), not the sheet's plain gable.** The user said "go with what you
   believe is correct".
   - With a plain gable, the sloped verge sits 0.9 m above the pier top. GASP cannot mantle onto it, and the capsule
     cannot stand under it.
   - The 0.9 m hip skirts keep the +3.25 eave that the wall-top runner reaches (route 6).
   - The front elevation keeps the sheet's tile field, eave and ridge ends. From the side there is a small
     board-and-batten gable instead of a full one.
2. **At the spec heights the eave hides the top of the gate.**
   - The eave (+3.25) is lower than the opening head (+3.5) and stands 2 m in front of the doors.
   - In the front elevation it hides the lintel and the top 0.2 m of the leaves. The sheet has a 2.8 m eave over a
     2.5 m opening.
   - The top batten was lowered so it stays visible. This needs the user's eye; the fix would be a higher eave, which
     changes route 6.
3. **Cap pitch 20 deg** (the sheet's is about 30-35 deg on a 0.6 m wall). This keeps the plaster body about 1.03 m
   tall, as on the sheet, at the 1.0 m width. The walkable collision is flat at the ridge top, so feet at the very
   edge of the 1.0 m strip float about 0.25 m above the tiles. The spec accepted a flat strip.
4. **Piers and side bays.** The piers (the grey-box landings) are cream "sleeve" piers, 1.0 x 1.4 m, with their own
   mini cap, as the sheet's sleeve. The side bays are a cream panel, a post and dark vertical boards, as the sheet's
   front. The lamps are on the front corner posts.
5. **Plaster is mapped in world space** (triplanar in Blender, world-aligned in UE). Heights can change without
   distortion, and modules of any length stay continuous. UV0 (local metres / 4 m) remains as the fallback. Grime (G)
   and moss (R) are vertex colours.
6. **Colours:**
   - timber albedo #4F3D2F, between the guide's #3A2E26 and the sheet's #574131;
   - tile #4E4F52 (the wall sheet's tiles measure #4A4A4B);
   - earthen plaster #AE8C66 (the sheet renders #B69B80).
7. **No emblem on kit 1.** The sheets show plain ridge ends, so the user's emblem is left for a later piece (a plaque
   or the hall).
8. **"Inside corner":** one corner module serves as both. A 1.0 m wall's L corner has the hip on the outside and the
   valley on the inside.

### Review (5 render rounds, renders/kit1/r0..r5; the final round is r5)
- Model sheets: `sheet_wall.png`, `sheet_gate.png`, `sheet_wall_variants.png`.
- Side-by-sides: `sbs_wall.png`, `sbs_gate.png`.
- Beauty shots: `beauty_gate_from_courtyard.png`, `beauty_along_east_wall.png`, `beauty_ref2_through_open_gate.png`.
- The gate plan view is cut at +3.0 m: cut solids are shown dark and the eave line dashed.
- Where we still fall short of the sheets:
  - the sheets' timber and iron are richer: more grain, heavier straps, more studs;
  - the sheet tiles are darker, with metallic highlights;
  - our plaster mottling is milder;
  - our footing rubble is less rounded;
  - our gate reads lower and wider, because of the spec heights and the irimoya roof.


## 2026-09-27 - Stage 2 fix round f1: KIT 1 (measurer fixes, blind-judge blockers, main-session direction)

### Commands (headless, --factory-startup; lock DojoKit, claude, Assets/Dojo/DojoKit1.blend)
```
blender -b --factory-startup --python Scripts/dojo/build_kit1.py                    # build + QA + LODs + export (about 9 min)
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/measure_kit1.py   # kit1/measure_kit1_f1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/walk_check.py  -- --out kit1/walk_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/climb_check.py -- --out kit1/climb_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/roof_walk_check.py
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/render_kit1.py -- --what wall|gate|variants|beauty --samples 160 --tag ../kit1_f1
py Scripts/dojo/compose_kit1.py ../kit1_f1
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <ref.png> <sheet.png> <out.png>
```
Renders, sheets and side-by-sides: `renders/kit1_f1/` (previews p1-p3 in subfolders). This round was interrupted once (usage
cap) mid-export and resumed; everything below comes from the final build.

### Direction followed (main session, 2026-10-02)
1. **Gate roof = the sheet's plain gable (kirizuma)**: straight verges with timber bargeboards, a gable with tie beam,
   king post and board infill, verge rolls with round end tiles at the four verge corners. Planes meet at +4.416
   (3.25 + 2.5 x tan 25 = 4.4158, not +4.400; the spec's 4.4 is the rounded figure).
2. **Ridge ends**: round stacked ridge-end tiles (base block, two drums, a 0.205 m disc face with a raised rim, a stepped
   inner ring and a low boss). **Plain: no symbol and no emblem** (the previous attempt had put the user's emblem on
   them; removed per the direction).
3. **White piers removed.** The wall runs into the timber post cluster; beside the doors are vertical-plank side panels
   on stone plinths.
4. **Route 6, the grey-box way (a flat landing at the eave), with the roof form unchanged.** Beside the gatehouse the
   wall turns north (a standard corner module at X 17-18 / 26-27) and returns 2 m at +2.0 outside the verge. At the
   gatehouse's courtyard eave corner it ends in a 1 x 1 m stepped block, flat top +3.25 (X 16.92-17.92 / 26.08-27.08,
   Y 2-3). Route: south wall top -> round the corner -> return wall top -> **1.25 m mantle** onto the block -> step east
   onto the N eave corner (the slope plane is +3.343 where the runner steps on at Y 2.3: a 0.093 m CMC step). New
   piece `SM_DK_Wall_GateReturn_W` / `_E` (mirror): the return wall, the step block, and a **stepped join** (+3.0, the
   sheet's side view: the wall cap steps up under the gate eave) in the wall line from the corner to the wall post.
   The block stops 8 cm short of the verge and the join 7 cm short of the post: **0 triangle pairs** against the gate
   frame, roof and paving.
   The courtyard half of each gatehouse side is now closed by a plank panel on a granite sill. The gap between the
   return wall and the posts (0.59 m) is then sealed, so no capsule-sized pocket is left.
   - Superseded: `SM_DK_Wall_StepPier_Gate` and the ridge-end mantle markers of the interrupted attempt. The old FBX
     (`SM_DK_Wall_Pier`, `SM_DK_Wall_StepPier_Gate`) were moved to `Exports/DojoKit/Kit1/_superseded_f1/`.

### Measurer fixes (all measured in kit1/measure_kit1_f1.json)
- **Gate leaves:** hinge axis at local x 2.24 (in the door-post recess). Open leaves at world X 19.760-19.998 and
  24.002-24.240, so the **clear width is 4.004 m** (the opening is X 20-24).
  - Leaf local x 0.004..2.237 (L) and -2.237..-0.004 (R): nothing reaches into the door-post hulls.
  - Leaf bottom +0.110 over a threshold top of +0.0987: **11.3 mm clear**.
  - The swing is tested every 5 deg from 0 to 90: **0 triangle overlaps** with the frame, roof, paving or returns.
  - The courtyard-side rafters over the swing are stubs on the rear keta. f1 bug fixed: the stubs ended at ridge height
    and stood up to 0.49 m through the tiles. Now no N-slope tile stands above the slope plane (max -0.009 m).
- **Nanite:** every opaque piece of 2k tris or more is flagged (NANITE_OK True): the frame, the paving, both leaves,
  the roof, the footings, the caps, the piers, the returns and the frame pier. The lamp (996 tris) stays off.
- **Wall-cap float:** the cap is now 8 deg (was 20), with a lower ridge (bed 35 mm, 2 x 28 mm noshi). The ridge roll
  stands 6.5 cm above the flat walk plane. Drop from the walk plane to the visual tiles, every 5 mm along 4 m:
  - at the wall faces: 0.061-0.149 m (mean 0.106);
  - at a capsule centre 0.3 m in: 0.007-0.111 m;
  - on the ridge line, feet sink up to 0.076 m into the ridge roll.
  **Every tile is within 0.15 m**, so builder deviation 3 is closed. Cap collision height 0.2053 m; body tops
  T200 / T250 / T300 are 1.7947 / 2.2947 / 2.7947, so the plaster is 1.14 / 1.64 / 2.14 m.
- **Noshi slits:** noshi tiles overlap 6 mm inside every cap: 0 see-through rays out of 2940 / 5940 / 11940 / 2940
  (1 m / 2 m / 4 m / End). The r5 renders' light ticks were at the **joints between modules**: the ridge bed and
  noshi stopped 5-10 mm short of each plain module end. They now run to the exact end (gable ends keep their inset). New
  joint test: every 0.5 mm over +-10 mm of the 1 m / 1 m joint and the corner / 1 m joint. Only rays exactly on the joint
  plane pass (2/123 and 3/123). At 0.05 mm steps every miss is at offset 0.0: a zero-width seam that an edge-on ray
  slips through, not a gap. In the final variants sheet and the wall front, the ridge ticks are gone.
- **Headroom (recorded):** the lowest roof or frame timber over the passage grid (X 20-24, Y -2.6..2.6) is **+3.036** at
  the N eave's rafter tails (Y 2.4). Under the tie beams (+3.06) the clearance is 2.96 m over the +0.10 threshold.
  Everywhere this is at or above the 2.5 m of R5 and below the 3.5 m door opening. The ridge-stack hull top is +4.725
  (the ridge-end tiles' top); the ridge roll top is +4.543.

### Judge blockers and deltas
- 1 / 2 roof form and ridge ends: done (above).
- 3 invented piers: removed (above). The route-6 step blocks are the only raised plaster left; they sit at the
  courtyard eave corners, which the spec's route 6 needs.
- 4 missing kit piece: **`SM_DK_Wall_FramePier`** (16,345 tris, 2 UCX), the wall sheet's freestanding timber-framed pier.
  - It has a 1.28 m granite slab plinth (+0.08), the squared stone base with quoins, corner posts, sills, head beams
    with square ends, a mid rail and exposed earthen panels. The panels use the new `M_DK_EarthCore`: the plaster set
    times the tint #9D8369, grime in G; in UE the same MI params plus a Tint.
  - The cap is gabled on both ends at the T200 top.
  - It is not placed in the 1v1 layout: it is a terminal for the BR wall openings (`kit1.frame_pier`).
  - It is on the wall sheet in the reference's bottom-right slot; the section cut moved to the middle-right slot.
- 5 wall end: the footing wraps the end in stone (quoins, the end face); the end gable has a tie beam, king post,
  bargeboards and a ridge-end disc.
- Deltas 3-11 (doors with L-strap hinges, studded battens, knockers; bracket clusters and layered eave beams; 3 courses
  per slope with stepped round tiles; 0.65 m footing with capstones over 3 rough courses; pale sandy plaster without
  soot; valley roll and finial at the inside corner; bigger bracket lanterns; blue-grey tiles; varied paving with a
  front step): all carried out in this round; see the sheets.

### Checks (GASP capsule r 0.30 m, 1.72 m tall, step 0.45 m)
- Walk: 14/14 routes clear, including the open-gate BR passage street -> courtyard, and 6/6 CONTROLs blocked. The
  controls: the closed leaves; the hall; wall top -> stepped join; wall top -> E stepped join; return wall top -> step
  block; the 1v1 ring. At the spec's 0.35 m radius only the grey-box veranda tread blocks, as in stage 1.
- Climb: all routes work. Route 6 (both sides): return wall top -> step block, **124.8 cm, depth 100 cm -> Mantle
  (1 m set)**, stand-on-top clear, then a 0.093 m walk onto the eave. Route 1: 200 cm, depth 100. Route 2: 125 cm,
  depth 110.6. Route 8: 175 cm, then a 0.25 m step.
- Roof walk (`kit1/roof_walk_check.json`): 6/6 paths clear, maximum floor slope 25.0 deg:
  - both step blocks -> N eave corner -> roof centre (max rise 0.024 m per 2 cm);
  - along the N eave;
  - N eave -> ridge;
  - N slope back onto the step block;
  - BR over the ridge.
- QA: 29/29 pieces with 0 hard fails; LOD1 and LOD2 also 0 fails. fix_lod now drops the wire edges that Collapse
  leaves. The tiling pieces waive uv0_tile_range / uv_no_overlap, as before. Texel density 5.00-5.12 px/cm.
  29 FBX were exported through Scripts/pipeline to Exports/DojoKit/Kit1.

### Deviations and open points (flagged)
1. **The route-6 step blocks are visible.** From the courtyard they read as two raised plaster blocks flanking the
   gate (beauty_gate_from_courtyard). In the street elevation they show above the wall cap, behind the stepped joins.
   The sheet has neither. They are the smallest landing that keeps spec route 6, a 1.25 m mantle onto a +3.25 eave,
   with a plain gable. The user should judge them. The alternatives: a higher gable eave, or dropping route 6.
2. **Cap pitch 8 deg** (the sheet's is about 30-35 deg). The spec asks for a flat 1.0 m walk strip within 0.15 m, so the
   cap reads flatter than on the sheet.
3. At the spec heights the eave (+3.25) is below the door head (+3.5), so the front elevation hides the lintel and the
   top of the leaves. This is unchanged from before and needs the user's eye.
4. The frame pier's earth panels are lighter and more orange than the sheet's dark straw-earth. Our timber still has
   less grain contrast than the sheets. The wall top view shows small specular glints on the round-tile collars of one
   slope; these are not openings (the ray tests find none).
5. Triangles: the gate roof has 80,524, each return about 41k, the 4 m cap 22,440; unique total 323,726 (all Nanite).
   `CreamPlaster` textures from the removed piers are still in Exports/DojoKit/Kit1/Textures; no piece uses them.
6. **For the Unreal stage** (unchanged, plus):
   - `M_DK_EarthCore` needs a Tint parameter.
   - The new pieces `SM_DK_Wall_GateReturn_W/_E` and `SM_DK_Wall_FramePier` are listed in layout.json; the frame
     pier is not instanced.
   - The gate corners are 2 more corner-module instances.
   - The route-6 markers `Landing_Pier_GW/GE` now box the step blocks; `kit1.gate_returns` holds their positions.


## 2026-09-28 - Stage 2 fix round f2: KIT 1 (blind-judge blockers at 6/10, ranked deltas 1-12; no measurer items)

### Commands (headless, --factory-startup; the DojoKit lock is still held by claude on Assets/Dojo/DojoKit1.blend)
```
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/kit1_textures.py
blender -b --factory-startup --python Scripts/dojo/build_kit1.py                    # build + QA + LODs + export (about 15 min)
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/walk_check.py  -- --out kit1/walk_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/climb_check.py -- --out kit1/climb_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/roof_walk_check.py
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/measure_kit1.py      # kit1/measure_kit1_f2.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/render_kit1.py -- --what wall|variants|gate|beauty --samples 160 --tag ../kit1_f2
py Scripts/dojo/compose_kit1.py ../kit1_f2
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <abs ref.png> <abs sheet.png> <abs out.png>
```
- All renders, sheets and side-by-sides are in `renders/kit1_f2/`; the previews are in p1 and p2.
- The script state before this round is saved as `kit1/*_f2start_backup.py`.
- An interrupted earlier f2 attempt had already edited the textures, the pillow-stone footing and the cap constants.
  This round finished its incomplete parts: the EarthCore diffuse fallback, NOSHI_N in the cap maths, and the grime
  colour.

### Blockers
1. **Gate/wall junction: the plaster piers, the return walls and the stepped join are gone.**
   - The wall runs straight in at T200. The south runs 16-18 and 26-28 are plain 2 m modules.
   - The wall ends in `SM_DK_Wall_GateJoin` (0.49 m: footing, plaster, and a cap closed by an end plate and a stacked
     end tile). It stops 1 cm short of a new timber **post cluster** at |x| 3.00-3.50 (world 18.5 / 25.5).
   - The cluster is the wall post plus a heavy face post at each wall face, with vertical planks between them, on one
     0.45 m granite plinth.
   - The cap ends under the verge (the verge is at world 18.0 / 26.0).
   - Joins against the frame, roof and paving: 0 triangle pairs.
2. **Gate roof silhouette.**
   - Verge stacks down both gable edges: two layers of flat verge tiles (0.26 / 0.22 m) under a round verge roll
     (r 0.075 m), with a small stacked end tile at each eave corner.
   - Ridge: five noshi layers (0.46-0.34 m wide, 48 mm each) and a ridge roll (r 0.085). The ridge roll top is +4.671.
   - Ridge ends: heavy stacked onigawara, plain, no symbol. Each is 0.66 wide x 0.78 tall x 0.40 deep: a plinth tier, a
     band, a second tier, shoulders, and a 0.33 m round disc face with a rim, an inner ring and a boss. Top +5.038.
   - **Brown between the courses: the cause was found and fixed.**
     - The f1 sarking was one flat board, while the tiles sag 3 cm mid-slope. The board showed through the pan hollows
       (ray probe: `M_DK_Timber` faces were the first hit in 50-90 of 200 rays per row at +3.3 to +3.6).
     - The sarking is now 16 strips that sag with the tiles, and the inboard rafters are 3 cm lower.
     - Also, `build_material` ignored each material's `grime_color`, so all grime was brown (#6A5A48). The tiles now
       take their own dirt colour, #4B4A3E.
3. **Gate plan view.**
   - The f1 plan was cut at +3.0 on purpose, with the roof lifted off. `gate_top.png` is now the true plan with the roof
     on.
   - The sheet's bottom-left slot holds `gate_top_oblique.png`: an ortho view from above the street at 38 deg, as in the
     reference.
   - Faces measured (`gate_roof_faces`): 161 x 101 rays cast down from +7.0 and up from +2.6 over the roof. 15,327 hits
     each way, **0 back faces hit first**.
   - A first run from +2.9 reported 12 back-face hits. Those rays started inside the bargeboard foot blocks.
   - The eave upturn warp is now continuous at |y| > 2.6.
   - The sarking now runs to the verge edge, so no one-sided tile strip shows from below.
4. **Wall cap mass.**
   - Pitch 8 -> 21 deg, four courses per slope, three noshi layers of 35 mm (0.36 / 0.32 / 0.28 m wide).
   - Stacked onigawara (0.36 x 0.44 x 0.14) stand at the gabled ends and at the gate stop. A large ball-topped block
     marks the corner.
   - The cap collision is 0.3751 above the body top. The body tops are 1.6249 / 2.1249 / 2.6249, so the plaster is
     1.02 / 1.52 / 2.02 m.
   - Mid-ridge seam: the RoofTile texture had variation broader than 2 m, which showed as tone steps where modules meet.
     Mottle, bloom and wear now drop frequencies under 0.25 cycles per 0.5 m (`fmin`). Seam ratio 1.013.
   - Walk plane vs tiles (`cap_float`, every 5 mm along 4 m):
     - capsule centre 0.3 m in from either face: feet float 0.052-0.155 m (mean 0.099);
     - centre line: feet sink up to 0.086 m (mean 0.076);
     - at the faces themselves (y 0 / -1): 0.161-0.261 m (mean 0.208), over the pan hollows.
   - **Flagged:** the spec describes a "shallow cap 15 cm high visually"; the cap now stands 0.48 m from the eave board to the top of the ridge roll. The gameplay
     numbers are unchanged: top +2.0, flat collision, 1.0 m strip.
   - Noshi see-through rays: 0 of 2940 / 5940 / 11940 / 2940, and 0 in both joint tests.

### Deltas 5-12
5. Footing:
   - a course of squared capstones over two courses of rounded pillow rubble (Chaikin outlines, 28-60 mm cushions);
   - joints 4 mm deep in pale mortar #6E675C;
   - moss low down and in the joints.
   This code came from the interrupted attempt and was kept.
6. Plaster:
   - base #A48B6D, mean #9E8567. The first f2 value, #AD8B62, rendered orange next to the sheet.
   - stronger blotch, stain, crack and trowel terms;
   - vertex grime, darkest under the cap drip line and in a splash band above the footing.
7. Post plinths raised from 0.20 to 0.45 m (corner, door, side panel, cluster, and the courtyard panel sill). A
   0.8 x 0.44 m step stone (top +0.24, with collision) stands in front of each door-post plinth.
8. Gable:
   - a 0.52 x 0.52 kagami block on the cluster's outer face at the tie beam;
   - under it, an iron plate with four bolts;
   - over it, two bolted straps and a boss;
   - two-tier stacked bracket blocks on the tie beams under the mid purlins.
9. Frame pier:
   - an ashlar base on the slab: two courses of large squared blocks with crossing joints;
   - a granite lintel band under the head beam;
   - the EarthCore panel, which has its own texture set (mean #6C5139).
   The section cut now shows the footing core as packed stones in pale mortar (it was a speckle).
10. Leaves:
    - a low 0.066 m boss on a washer beside each ring pull, 36 mm proud (inside the 0.24 m leaf). The first try stood
      74 mm proud and cut the clear width to 3.932 m.
    - timber vertex grime (ground splash and streaks) on the frame, leaves and stand;
    - Timber base #3F3027, with stronger silver streaks.
11. Tiles:
    - charcoal #47484B;
    - a crest sheen from the roll mask: roughness x0.62 and metallic +0.30 on the rolls;
    - olive-grey dirt in the pans.
    **UE note:** `M_DK_RoofTile` needs the same crest parameters (vertex colour R) in dj_materials.
12. Lanterns: scaled 1.25. The glass is #FFCE8A emitting #FF9A42 (about 2400 K), and the lamp lights sit at the scaled
    positions.

### Route 6 (direction item 1: the grey-box way, a flat landing at the eave; roof form unchanged)
- New piece `SM_DK_Gate_Stand` (class landing, 956 tris, 7 UCX; the same piece on both sides). It is an open timber
  stand in the gate's timber:
  - four posts on 0.40 m plinths, through-rails at +1.70, knee braces, a 0.35 m deck edge;
  - a plank deck with a **flat top at +3.25**;
  - world x 17.12-17.92 / 26.08-26.88, y 0.25-2.90, 8 cm short of the verge.
- The route, step by step:
  1. On the south wall top, go to x 17.52 (west) or 26.48 (east) and turn to the courtyard.
  2. **Mantle: 124.8 cm high, 265 cm deep, 1 m set, room to stand on top.**
  3. Walk north along the deck.
  4. Step east onto the N eave at y 2.3: a **+0.093 m** step.
- The markers `Landing_Pier_GW/GE` box the decks: [17.12, 17.92, 0.25, 2.90, 2.90, 3.25] and [26.08, 26.88, ...].
- **Flagged for the user: the stands are visible.**
  - From the street, they show as thin frames beside the verge, above the wall.
  - From the courtyard, they are open timber frames on either side of the gate (beauty_gate_from_courtyard).
  - They replace the f1 plaster step blocks and return walls.
  - The alternatives still stand: a higher gable eave, or dropping route 6. With route 6 dropped, the wall runs in with
    nothing beside the gate, exactly as on the sheet.

### Checks (GASP capsule r 0.30, 1.72 m, step 0.45)
- Walk:
  - 15/15 routes clear, including the open-gate passage and a ground route round the stand.
  - 8/8 CONTROLs blocked:
    - the closed leaves;
    - the hall;
    - wall top into the gate, west and east;
    - wall top north into the stand deck;
    - the pocket between the stand and the gate side;
    - under the stand into that pocket (closed by the rails' hulls).
  - At 0.35 m only the grey-box veranda tread blocks, as before.
- Climb: every route works.
  - Route 1: 200 cm high, 100 cm deep.
  - Route 2: 124.8 / 110.6.
  - Route 8: 175 cm, then a 0.25 m step.
  - Route 6: see above.
- Roof walk: 6/6 clear, max slope 25.0 deg. Slope to ridge rises 0.252 m; BR over the ridge 0.284 m (both under 0.45).
- Gate leaves:
  - clear at every 5 deg from 0 to 90;
  - clear width 4.004 m (19.998 -> 24.002);
  - closed bottom 11.3 mm over the threshold.
- Headroom: the lowest timber is at +3.035 (the N rafter tails).
- Nanite: every piece of 2k tris or more is flagged.
- QA: 29/29 pieces with 0 hard fails, LODs 0 fails, texel density 5.01-5.12 px/cm.
- Export: 29 FBX to Exports/DojoKit/Kit1. Unique triangles 313,767 (the gate roof alone is 83,080).
- `SM_DK_Wall_GateReturn_W/_E` were moved to `Exports/DojoKit/Kit1/_superseded_f2/`.

### Open points
- The route-6 stands need the user's call (above). On the sheet, the side elevation hides the near stand;
  `gate_side_stand.png` shows it.
- At the spec heights the eave (+3.25) still hides the door head (+3.5) in the front elevation (unchanged).
- The Unreal stage (the kit-1 branch of dj_import / dj_materials / dj_verify) is still to do:
  - new piece `SM_DK_Wall_GateJoin`, placed at (18, 0, 0) rot 0 and (26, -1, 0) rot 180;
  - new piece `SM_DK_Gate_Stand`, pivots (17.52, 0.25) and (26.48, 0.25);
  - `SM_DK_Wall_FramePier`, not placed;
  - `M_DK_EarthCore` now has its own texture set (no Tint);
  - the new `M_DK_Underlay` slot is defined but unused;
  - the tile crest sheen;
  - the corner modules beside the gate are gone (GATE_CORNERS is empty).
- Re-running build_dojo_greybox.py overwrites layout.json; re-run build_kit1.py after it.


## 2026-09-28 - Stage 3: SHOWCASE in DojoLab (kit 1 + kit 2 ground + the four prop kits, combined import)

### Commands (headless Blender, --factory-startup; Unreal commandlets one at a time; lock DojoKit, claude, Assets/Dojo/DojoShowcase.blend)
```
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py          # layout + blend + bounds (~40 s)
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/walk_check.py      -- --layout showcase/layout_showcase.json --out showcase/walk_check_showcase.json
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/climb_check.py     -- --layout showcase/layout_showcase.json --out showcase/climb_check_showcase.json --hover 0.019
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/roof_walk_check.py -- --layout showcase/layout_showcase.json --out showcase/roof_walk_check_showcase.json
bash Scripts/dojo/unreal/run_showcase_unreal.sh import materials level verify capture
```
Timings: import 150 s first / 25-40 s when skipping, materials 20-90 s, level 25-70 s, verify 25-40 s, capture 80-300 s.
Every Unreal step checks that no UnrealEditor.exe has DojoLab open and waits while any UnrealEditor-Cmd runs.
Outputs: `showcase/` (layout_showcase.json, blender_bounds.json, compose_report.json, the three check JSONs, logs) and
`unreal/showcase/` (import / materials / level / verify / capture JSON, logs/timings.txt, captures/).
New scripts:
- `Scripts/dojo/showcase/compose_showcase.py`;
- `Scripts/dojo/unreal/dj_sc_common.py`, `dj_sc_import.py`, `dj_sc_materials.py`, `dj_sc_level.py`, `dj_sc_verify.py`,
  `dj_sc_capture.py`, `run_sc_capture.ps1`, `run_showcase_unreal.sh`.
`roof_walk_check.py` gained optional `--layout/--out` arguments and `climb_check.py` an optional `--hover`. Both default
to the old behaviour.

### What is in L_Dojo now
L_Dojo holds 602 mesh actors (661 actors in all), every one tagged DJ_Managed; they replace the grey-box assembly.

| Kit | Instances | Replaces |
|---|---|---|
| kit 1 (wall + gatehouse, f2) | 156 | the grey-box wall, piers and gatehouse (build_kit1 had already swapped them in layout.json) |
| kit 2 ground (f1) | 342 | SM_DGB_Floor_Fight, _Path and _Yards. SM_DGB_Ground_Outside stays: it is outside the walls |
| taiko | 4 (stand, drum, 2 sticks) | the grey-box drum, through a new `SM_DGB_Pavilion_NoDrum` (below) |
| training | 14 | SM_DGB_WeaponRack, TrainingPost and Dummy, plus the proposed long-arm dummies, benches and stools |
| stone | 14 | SM_DGB_Cistern, Crate, Well and StoneLantern, plus the proposed short lanterns |
| modern | 46 | SM_DGB_Vending and ACUnit, plus the wall and street lamps, poles, wires, transformer, guys and junction box |
| grey-box kept | 25 + 1 | hall, outbuildings, corridors, shed, pavilion frame, landings, trees, alley fences, the 1v1 boundary |

- `SM_DGB_Pavilion_NoDrum` is the grey-box pavilion without the drum's faces and its hull (UCX_05). It passed pipeline
  QA with 0 hard fails and is exported to `Exports/DojoKit/Showcase/`.
- Every prop is its own StaticMeshActor. Folders: Dojo/{Wall, Gatehouse, Landings, Ground/<family>, Props/<Kit>, ...}.
- The gate leaves stand OPEN, placed from kit1.gate_leaf_placements.open. Verify reads their yaw as -90 / +90.
- Imported but not placed:
  - SM_DK_Wall_FramePier (the piece for the BR wall openings);
  - SM_DKP_Stone_WellFrameGable (a variant);
  - SM_DKP_Stone_CrateHalf;
  - the ground kit's kerb and edging variants that its layout does not place.

### Grey-box climb numbers win (measured fits, compose_report.json)
Climb heights below include the CMC's 1.9 cm floor hover (see Gates).
- **Vending machine:**
  - Scaled (0.98684, 0.77973, 1.0), so its hull is exactly the grey-box box: X 12.0-12.9, Y 0.0-0.8, top +1.75. The kit
    machine is 0.912 wide and 1.026 deep.
  - Route 8: 173.1 cm high, 80 cm deep -> Mantle (2.5 m set), then a 0.25 m step.
- **Roof AC:**
  - Scaled 1.23071 in Z about its front feet (+3.2332 on the lower roof), so its top is +5.10 (route 5), not the spec's
    +4.75.
  - The ACUnit markers were re-fitted to the kit's casing hull: X 15.0-16.2, Y 21.98-23.10, top 5.10. The casing starts
    12 cm in front of the grey-box box, which had put GASP's room point inside it.
  - The route-5 stance moved from Y 21.78 to 21.66.
  - Route 5: 197.4 cm, depth 112 -> Mantle (2.5 m set), then the 0.40 m walk-up.
  - Side effect: the rear runners scale with the unit and float up to about 0.21 m above the tiles at the hall wall,
    under the upper eave.
- **Cisterns and crates:** the stone kit's hulls equal the grey-box markers exactly (0.0 m on every edge and the top).
- **Weapon racks:**
  - The markers were re-fitted to the kit rack's body hull: 0.295 m deep, top +1.137 (the grey-box box was 0.40 deep,
    1.20 tall).
  - The hurdle stance moved from X 3.46 to 3.32, because the rack's feet reach X 3.68.
  - Hurdle: 111.8 cm, depth 29.5 cm -> the Hurdle row.
- **Bench, stool, dummy:**
  - The bench and stool stay at the training kit's f1 spots, (0.5, 8.5) and (0.5, 11.0). Nothing was moved.
  - Measured on render bounds, their clearance to route P1_round_west_yard_past_tree is 0.466 m (bench) and 0.520 m
    (stool); both clear the 0.35 m target. The wooden dummy clears it by 0.357 m.
- **Main-session defaults applied:**
  - The utility pole is 8 m.
  - The short lanterns stand at the stone layout's proposed spots, X 20.6 / 23.4, Y 1.0, on the gate paving at +0.030
    (found by ray cast).
  - The long-arm dummies, benches and stools stand at their proposed spots.

### Ground vs the kit-1 gate paving
The kit-1 paving (X 18.1-25.9, Y -3.0..+2.5) overlaps the ground kit's gate zone. Cover was measured with rays cast
straight down on a 5 cm grid.
- **Dropped:**
  - every ground piece at least 95 % under the paving: 2 sand-edge boards, 2 slabs, 4 coarse-gravel panels and 16 tufts
    or pebbles;
  - the ground kit's whole gate kerb band family: the Kerb50 blocks, their ends and the joint fill. The band stood in
    for the gate floor, and it would z-fight the +0.10 threshold.
- **Kept:** partly covered pieces stay under the paving's edge; the paving is 1-8 cm higher.
- **Round 1** dropped at 50 % cover, which opened a hole in the path; the first capture showed it.
- **Overlap:** the paving's courtyard apron (to Y 2.5) laps 0.4 m over the sand field's south edge at X 18.1-21 and
  23-25.9.

### Unreal import and materials
Content lives under /Game/DojoKit/{Kit1, Ground, Props/Taiko|Training|Stone|Modern, Showcase}.
- **Meshes (133):**
  - legacy FBX importer; UCX kept 1:1; vertex colours imported;
  - Import Mesh LODs ON: 52 meshes carry their 3 LODs, with the sidecar screen sizes 1.0 / 0.5 / 0.25;
  - Nanite on 38 pieces (kit 1's own flags, and props over 2k tris), with the fallback at full detail (relative error 0).
- **Textures (134):** BC sRGB TC_Default; ORM and _M linear TC_Masks; N TC_Normalmap with no green flip. All are power
  of two.
- **Masters (11)**, in /Game/DojoKit/Materials/Masters:
  - M_DJ_K1_Master;
  - M_DJ_K1World_Master: triplanar plaster;
  - M_DJ_Ground_Master: macro variation, wear, and a per-actor tone and hue from a position hash;
  - M_DJ_GroundXY_Master and M_DJ_BedBlend_Master;
  - M_DJ_Dressing_Master;
  - M_DJ_Prop_Master: the training kit's 'Wear' R/G/B weathering;
  - M_DJ_PropMasked_Master: the fan grille;
  - M_DJ_EmissiveTex_Master, M_DJ_Flat_Master and M_DJ_EmissiveFlat_Master.
- **Instances:** 62, each named like its slot.
- **Emissive** = the Blender strength x K 100:

  | Slot | Emissive |
  |---|---|
  | kit-1 lamp glow | 2600 |
  | bulbs | 1400 |
  | lamp glass | BC x 220 |
  | stone lantern | BC x 300 |
  | vending display | BC x 70 |

- **Deviations:**
  - The kit-1 grime noise only modulates the vertex grime (x 0.75-1.0), at half the Blender frequency across. At the
    Blender settings, Unreal's simplex noise drew hard vertical stripes over all the plaster (capture round 1).
  - The triplanar plaster has no normal map. The Blender material bumped it from BC + AO instead.

### Level and lighting (layout_showcase.json sun / lights)
- **Sun:**
  - 13 deg high, from azimuth 160 (W-N-W);
  - 420 lux: render_kit1's 4.2 W/m2 x K 100;
  - 4300 K at the light, as the atmosphere sun.
- **Sky:** SkyAtmosphere luminance factor (3.4, 2.6, 2.1), a real-time sky light, height fog.
- **Post process** (unbound PPV):
  - manual exposure -4.04 EV: the analytic value is 0.6 - log2 100 = -6.04; +2.0 on top (the armory measured about +2.4,
    and +2.44 clipped the sand);
  - saturation 0.85, colour gain (1.06, 1.0, 0.9), bloom 0.35, vignette 0.15.
- **Tuning rounds:**
  - r1 (3000 K, sky (4, 3, 2.6), -3.60 EV): read deep orange and clipped;
  - r2 (5000 K, sky (2.4, 2.1, 1.9)): read cold grey;
  - r3 / r4: the values above.
- **Lamp lights:** 14 point lights, in candela, without shadows, at the measured centres of the lamp-glow and bulb
  faces.
  - 4 gate bracket lamps: 358 cd, 2400 K (render_kit1's 45 W);
  - stone lanterns: 159 cd (tall) and 119 cd (short);
  - wall and street lamps: 239-279 cd, 2600 K.
- **Collision per class:**

  | Class | Instances | What |
  |---|---|---|
  | ground | 308 | |
  | building | 155 | |
  | nocollision | 70 | wires, rope, bucket, drum sticks, ground tufts and pebbles |
  | thin | 40 | lanterns, posts, dummies, racks, lamp poles, poles, the taiko stand |
  | roof | 9 | |
  | landing | 7 | |
  | climbprop | 7 | |
  | lowcover | 2 | |
  | tree | 2 | |
  | propblock | 1 | the drum |
  | boundary | 1 | |

  - thin = Pawn block, Camera and Visibility ignore.
  - nocollision = NoCollision.

### Gates
- **Level bounds gate:**
  - All 602 transforms are exact: 0.0 cm, and rotation and scale match.
  - Non-Nanite bounds are within 0.477 cm.
- **Nanite bounds finding (UE 5.8.2):**
  - A Nanite mesh's bounding box is exact right after import; four two-process probes measured this.
  - Once the materials step re-saves the package, the box reads 0.5-27.6 cm larger: the cistern by 16.4 cm, the gate
    frame by 27.6 cm, the 4 m footing by 8.5 cm.
  - No rebuild is logged, and swapping materials in memory does not change it.
  - So for Nanite actors the gate checks containment (the Blender box inside the UE box, within 1 cm) plus the exact
    transform. The per-piece inflation is in level.json `nanite_bounds_inflation_cm_by_piece`.
  - It only affects the culling bounds.
- **Fresh-process verify** (`unreal/showcase/verify.json`): 6 / 6 gates PASS.
  - **Meshes** (155 pieces):
    - hull counts = UCX; Nanite as requested; LOD counts match;
    - non-Nanite LOD0 tris = Blender;
    - every slot holds its MI on the right master;
    - LOD screen sizes applied.
  - **Textures:** all 134 pass.
  - **Level** (602 actors):
    - every actor has the right mesh, scale and location, and collision per class;
    - no replaced stand-in is left;
    - the leaves are open.
  - **Traversal:** 28 markers, 4 ledges each, 0.0 cm error.
  - **Gameplay:**
    - GM_Dojo with SandboxCharacter_CMC, KillZ, P1 / P2;
    - 0 missing dependencies, including L_Dojo's own.
  - **Environment:** sun, sky, fog, manual-exposure PPV, 14 lamps, 10 cameras.
- **Walk** (`showcase/walk_check_showcase.json`, 706 pawn hulls):
  - 15 / 15 routes clear, and 8 / 8 CONTROL routes blocked.
  - The closed-gate control is now `CONTROL_1v1_ring_at_the_open_gate`: the leaves are open, and the 1v1 ring blocks at
    Y -0.7.
  - At the spec's 0.35 m radius only the grey-box veranda tread blocks, as in every stage.
- **Climb** (`showcase/climb_check_showcase.json`: GASP's steps replayed, with the CMC's 1.9 cm floor hover):
  - Every route works: 1-8, the veranda, the plinth and the hurdle.
  - Heights read about 1.9 cm lower than in earlier stages because of the hover (e.g. the wall top now reads 198.1 cm).
  - Without the hover, the ground kit's irregular edging-board hulls made the capsule start its room sweep in contact.
    Routes 4 and 7 then failed at the stance, not at the obstacle.
- **Roof walk** (`showcase/roof_walk_check_showcase.json`): 6 / 6 clear.

### Captures
Folder: `WorkFiles/dojo/build/unreal/showcase/captures/`. 96 frames each, Lumen on. `SHOWCASE_SHEET.png` shows all ten.
- CAM_GateFromCourtyard
- CAM_Establishing: reference 2's framing, from inside the open gate
- CAM_PlayerEyeSand
- CAM_Drum
- CAM_EastYard
- CAM_VendingShed
- CAM_GateFromStreet
- CAM_WallTop
- CAM_WallCorner
- CAM_Overview

### Open / for the user
- **Establishing view:** reference 2's camera (9.7 m up, 11.6 m outside the gate) cannot exist at spec scale. The still
  is taken from inside the open gateway instead, so the gate roof fills the top third.
- **Grey-box buildings and trees** now read as flat blocks next to the textured kits. This is expected: they are the
  next kits.
- **Roof AC:** the Z-scale makes the rear runners float up to about 0.21 m under the upper eave. The alternative is a
  +5.10 AC build; in the modern kit that is one constant, `AC_TOP`.
- **Vending machine:** it is squeezed to 0.78 of its depth, to match the grey-box route 8 proven at 0.8 m. If the spec's
  R3 depth should win instead, the kit's 1.0 m machine needs route 8 re-proved.
- **Short lanterns:** they stand on the gate paving, under the gate roof, at the stone kit's proposed spots. They narrow
  the gateway visually; the walk routes still clear them by 0.995 m.
- **Nanite bounds inflation** (see Gates) is engine behaviour to keep an eye on. A StaticMesh "Build" in an editor
  session may reset it.
- Not played in PIE yet.

## 2026-09-28: Round 2, Unreal polish (DojoLab only; no Blender asset changes)
Full notes: `unreal/round2_polish/ROUND2_NOTES.md`. Captures: `unreal/round2_polish/captures_after/` (same 10 cameras), sheets `BEFORE_AFTER_SHEET.png` and `SBS_COLOUR.png`.
- **Run:** `run_showcase_unreal.sh prep import materials level verify capture`. Verify 7/7 PASS (new gate 7: in-engine GASP Traversable trace, 20/20 routes hit their own marker). Walk 15/15 routes with 8/8 controls blocked, climb all routes, roof walk 6/6.
- **Colour cast:** the cause was the lighting and post chain, not the materials. The colour probe (`dj_sc_colour_probe.py`) found:
  - a warm grade tinting neutral;
  - 4300 K on top of the atmosphere's own reddening;
  - a warm sky factor making the fill orange;
  - lamps 4x too strong at +2 EV.
  - Now: 5500 K sun, sky factor (2.6, 1.8, 1.6), sky light x 6, neutral grade, lamps x 0.25 (`dj_sc_common.py`).
  - Gate tiles: (29, 9, 2) s0.95 → (37, 27, 29) s0.28 (Blender (38, 32, 38)).
  - Sand: s0.62 → s0.30 (Blender 0.32).
  - Sky: beige → lilac.
- **Nanite:** `fallback_target` RELATIVE_ERROR 0 is set on all 38 meshes and in `dj_sc_import`; the fallback now equals the source (0.000 cm, tris equal).
  - The render bounds stay inflated (up to 27.6 cm): UE 5.8 Nanite bounds are the whole DAG's cluster-box union (`NaniteEncode.cpp` `CalculateMeshBounds`), not the fallback.
  - The gates now measure the fallback geometry through the actor transform: max 0.0005 cm over 139 actors.
- **Markers:** pavilion-pad bottom raised to +1.50; `Wall_S_W2` and `Wall_S_E1` removed (26 markers).
  - The rules live in `showcase/marker_policy.py`, used by compose and by `apply_round2.py`.
  - `climb_check.py` now tests the first marker along the sweep among ALL markers.


## 2026-09-28 - Stage: SHARED DOJO MATERIAL LIBRARY v1.0.0 (Blender only)

Full notes: `WorkFiles/dojo/build/materials/BUILD_NOTES.md`. Unreal recipe: `Scripts/dojo/materials/README.md`.

- **What it is:** one library for every dojo kit from now on.
  - 14 texture sets `Exports/DojoKit/Materials/Textures/T_DJ_*` plus WearMask.
  - `Scripts/dojo/materials/dojo_materials.py`: `make_material(name)`, `grain_uv`, `box_uv`, `round_uv`,
    `rope_uv`, `unit_uv`, `bake_wear`, `texel_density`.
- **Swatch sheet:** `WorkFiles/dojo/build/materials/SWATCH_SHEET_r4.png` (4 rounds).
- **Studio dE76 against the reference-crop medians:**
  - 2.6-6.6 on every opaque material;
  - timber end grain 0.78 x the face luminance;
  - iron 0 % partial metal;
  - edge wear on bevel faces only.
- **Still open:** the amber glass reads 14 deg redder than the sheets under AgX (tune in the Unreal look pass).
- **Not done here:** DojoLab and the shipped kits are untouched. Moving each kit over to the library is its own
  rebuild.


## 2026-09-28 - KIT 1 round 2: gate + wall fixes (blind judge 5.5/10) on the shared material library

### Commands (headless, --factory-startup; the DojoKit lock is held by claude; no Unreal in this stage)
```
blender -b --factory-startup --python Scripts/dojo/ground/make_ground_textures.py -- --only Sand
blender -b --factory-startup --python Scripts/dojo/ground/build_ground_kit.py              # QA + export + DojoGround.blend
blender -b --factory-startup --python Scripts/dojo/build_kit1.py                           # QA + LODs + export (~6 min)
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/walk_check.py  -- --out kit1/walk_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/climb_check.py -- --out kit1/climb_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/roof_walk_check.py
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/measure_kit1.py      # kit1/measure_kit1_r2.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/render_kit1.py -- --what wall|variants|gate|closeups|beauty --samples 160 --tag ../kit1_r2
py -3 Scripts/dojo/compose_kit1.py ../kit1_r2                                               # sheets + sbs_src/ pairs
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <ref> <ours> <out>     # one per pair (20 sheets)
```
- Script state before this round: `kit1/*_r2start_backup.py` and `ground/r2start_backup/` (scripts, layout, blend,
  sand textures).
- Renders: `renders/kit1_r2/` (previews in p1-p4). Ground review renders: `renders/kit1_r2/ground/` (t3 = final tint).

### 1. Rear frames removed; route 6 cannot be built inside the roof footprint (FLAGGED for the user)
- `SM_DK_Gate_Stand` is gone from the build, the layout and the renders. Its FBX + sidecar moved to
  `Exports/DojoKit/Kit1/_superseded_r2/`. Nothing stands outside the gate roof now.
- The second post line under the roof already exists: the rear corner posts at local y +1.75 on their plinths, inside
  the 8 x 5 m roof (post lines 3.5 m apart). No change was needed.
- **Route 6 is not buildable without a structure outside the roof.** Measured in `layout.json` `kit1.route6`
  (`build_kit1.route6_study`):
  - every plan point of the roof is under the roof. A standing capsule (1.72 m) fits on a floor of at most +2.44
    under the ridge and +1.28 at the eave;
  - a runner on the +2.0 wall top keeps head room only to |y| 0.95, still 1.55 m inside the eave line, so nothing
    under the roof can lift a runner above the eave;
  - the flat landings the grey-box proved all stood OUTSIDE their eaves (the 1 x 1 m wall piers at X 17-18 / 26-27,
    the eave pads, the pavilion pad). With the sheet's plain gable the verges slope (no mantle), and the ridge-end
    tiles top +5.04 (3.04 m over the wall top, over GASP's 2.75 m ceiling).
  - Route 6 is therefore dropped from `layout.json` (markers `Landing_Pier_GW/GE` and its climb steps removed).
    Options for the user: (a) accept route 6 dropped (no 1v1 route onto the gate roof; the spec's jump shortcut cannot
    land on a slope either); (b) re-admit a landing outside the roof, built as architecture (e.g. a stone sleeve pier
    at a courtyard eave corner); (c) a flat collision band under the N eave tiles plus a climb prop in front of it
    (the route-4 pattern), which would stand on the fight floor that the spec keeps empty.
- The showcase marker policy (`showcase/marker_policy.py`) now also runs in build_kit1: `Landing_PavilionPad` bottom
  +1.50, stale `Wall_S_W2` / `Wall_S_E1` removed (the plinth route passes again in layout.json's climb check).

### 2. The open wall end, modelled
- The footing's stones stay inside their module (x overshoot 0.0 m on every straight module and the join,
  `measure_kit1_r2.json` `footing_extents`). Face stones stand 3.8-4.0 cm proud. End and corner faces carry squared
  hewn quoins (3 courses, 0.37-0.38 m on both faces, in line with the other stones: 3.5 cm proud). No stone pokes
  past an end face.
- The section view (`wall_section.png`, the sheet's middle-right slot; render-only, not a kit piece) is now modelled
  geometry:
  - every cut stone, block, timber and tile shows its own library material on the cut;
  - the footing core is small hewn granite stones, 1-1.5 cm proud of a dark rubble backing 3 cm back;
  - the plaster body is a 25 mm plaster skin round a rammed-earth core (a smooth lumpy surface with up to 1 cm of
    relief, wavy lift steps every 9-14 cm, embedded pebbles); the cap's clay bed is the same;
  - a raking light shows the relief.
  It is still the weakest view: at sheet size the earth reads fairly flat.

### 3. Footing: hewn polygonal rubble on the library's GraniteRubble
- `kit1_geo.rubble_cells` rebuilds the library GraniteRubble texture's own stone cells (periodic jittered Voronoi,
  seed 1401, 12 x 16 per 4 m tile). Check: 192 / 192 seed pixels fall in their own texture cell; 227 / 229 cells map to
  one texture stone (the other 2 are clipped slivers).
- Each field stone is one cell, built by `kit1_geo.hewn_stone`:
  - inset 5-9 mm, so the joints are 1.0-1.8 cm and irregular;
  - a 10 cm deep side wall and a crisp, irregular 14-24 mm chamfer;
  - a smooth-shaded pitched face (6-14 mm) with a random tilt;
  - UV-mapped so the texture's stone, dark rim and joint moss land on it; the side walls sample the texture's dark
    joint.
  The joints are 3.5-5 cm deep, down to a recessed rubble core.
- Capstone course: squared hewn blocks (`kit1_geo.hewn_box`, 26-50 cm, 12-20 mm chamfers) in M_DJ_Granite. The post
  plinths are hewn boxes too.
- Moss comes only from the texture's joint and rim moss (the library has no moss channel). Heavier moss belongs to
  kit 11's decals.
- Module ends are straight 1-2 cm joints: the modules are instanced, so the pattern cannot interlock across them.

### 4. Kept from f1/f2
The plain gable (kirizuma) gate roof, the round stacked ridge-end tiles, the timber side panels, no white piers.
r2 fixes on the roof: the verge rolls sat 2.7 cm above their tile stacks (a sky slit along both verges in the side
elevation) and the ridge roll 4 mm above its noshi. Both now sit on their stacks (ridge roll top +4.663, was +4.671).

### 5. Library materials on every kit-1 piece
- Slots:
  - M_DJ_TimberAged, plus M_DJ_TimberAgedEnd on the end grain (via `grain_uv`);
  - M_DJ_Granite and M_DJ_GraniteRubble;
  - M_DJ_Iron;
  - M_DJ_PlasterEarth (world box projection in the Blender preview; world-aligned in Unreal);
  - M_DJ_RoofTile, also on the ridge beds and the tile underlay (no cream line);
  - M_DJ_GlassAmber (`unit_uv` per pane).
- Weathering is `bake_wear` ('Wear' R/G/B); the old 'Col' layer is gone. Granite, rubble and iron take a random UV
  offset per part (per-stone variation).
- **Kit-only exception:** `M_DK_EarthCore` (the frame pier's straw-earth panel): the library has no such set.
- Lost with the switch: the f2 tile crest sheen (the library RoofTile has no crest parameter).
- QA: 28 / 28 pieces with 0 hard fails.
  - The tiling pieces waive uv0_tile_range / uv_no_overlap, as before.
  - The lamp's texel check is off: qa_check assumes one texture size, and the lamp mixes 2 m iron tiles with unit-UV
    panes. Its library per-slot density is p50 5.12.
  - Texel density 5.07-5.80 px/cm (the qa figure); the library per-slot p50 is 5.12 everywhere.
  - LOD1 / LOD2 on 19 pieces, 0 fails. 28 FBX exported through Scripts/pipeline.
  - Unique tris 241,485 (313,767 with the stands); the 4 m footing 11,111; the gate roof 83,080.

### 6. Junctions + ground (Scripts/dojo/ground, Exports/DojoKit/Ground)
- The gate paving's courtyard apron now ends at Y 2.0 (the sand field's edging) instead of 2.5
  (`kit1.gate_paving_apron_y1`).
- The path slabs and ALL the kerbs are `M_DKG_Granite` = the library Granite maps (T_DJ_Granite) as a ground instance:
  - linear tint (1.66, 1.92, 2.60);
  - per-slab tone +-12 % and a warm / cool hue (Object Info Random; Unreal PerInstanceRandom);
  - the library Wear (bake_wear, no ground dust).
  The slab arris is 12 mm (was 8), the plan corners 14 mm. The 8 mm joints sit over a dark joint fill
  (`SM_DKG_PathBed_2x3` and the kerb mortar are now M_DJ_GraniteRubble). `T_DKG_Granite*` / `GraniteHewn` are no
  longer used.
- Path colour, measured in the ground rig's C_Establish: median 145/123/122 (reference 2's slabs 147/127/127; f1 was
  151/125/108). Under render_kit1's cooler sunset the same slabs read lavender-grey (124/110/135): the two rigs
  differ, noted for the look pass.
- Sand (`make_ground_textures.py`):
  - finer grain: 0.9 -> 0.6 mm at the texel scale only, fewer and fainter specks, smaller crumbs;
  - irregular crests: crest slump of up to -22 % in 4-20 cm patches and +-1.5 mm crest jitter at 8-15 cm, both faded
    at the tile's u edges, so the ridges still meet the edge strips in phase;
  - collision unchanged (flat).
- Ground QA: 68 pieces with 0 hard fails; 68 FBX re-exported.

### Checks (GASP capsule r 0.30, 1.72 m, step 0.45)
- Walk: 15 / 15 routes clear (the wall-top runs now end at the verge, x 17.6 / 26.4). 5 / 5 CONTROLs blocked: the
  closed leaves, the hall, the wall top into the gate on both sides, the 1v1 ring. At r 0.35 only the grey-box
  veranda tread blocks, as before.
- Climb: every route in layout.json works (1, 2, 3, 4, 5, 7, 8, veranda, plinth, hurdle). The spec-as-written 4 / 5
  fail by design. Route 6 is not buildable (above).
- Roof walk: 3 / 3 clear (N slope along the eave, N eave to the ridge, BR over the ridge); max rise 0.276 m, slope
  25 deg.
- Measure (`kit1/measure_kit1_r2.json`):
  - the leaves clear at every 5 deg; clear width 4.004 m; 11.3 mm over the threshold;
  - headroom +3.035;
  - roof faces: 0 back-face hits;
  - the joins: 0 triangle pairs with the frame, roof and paving;
  - Nanite flags OK; noshi: 0 see-through rays.

### Renders (`renders/kit1_r2/`)
- Sheets: `sheet_wall.png`, `sheet_gate.png`, `sheet_wall_variants.png`.
- Side-by-sides: `sbs_wall.png`, `sbs_gate.png`, `sbs_ref2.png`, and per piece
  `sbs_wall_{front,end,top,corner,corner_top,34,corner_34,end_34,footing,frame_pier}.png` and
  `sbs_gate_{front,side,top,34,doors,ridge_end,junction}.png`.
- Close-ups: `close_footing`, `close_wall_end`, `close_gate_junction`, `close_gate_ridge_end`,
  `close_gate_courtyard_corner`.
- Sunset context: `beauty_*`, with the kit-2 ground appended in place of the grey-box floors.

### Open / for the next stages
- Route 6 needs the user's decision (above).
- Unreal (not this stage): L_Dojo still has the two stands, the old kit-1 materials and the old ground granite.
  - The kit-1 import needs the library masters (README) with the 'Wear' colour.
  - M_DKG_Granite becomes an M_DJ_Lib_Opaque MI with the tint and PerInstanceRandom.
  - The new apron edge.
  - The stand markers must go from the showcase layout.
- The footing's shape reads right, but the lower zone's stones are larger than the sheet's (the library tile's
  33 x 25 cm cells), and the moss is light.


## 2026-09-28 - Stage: KITS 3 + 4, the main hall and the shared roof system (Blender only)

Full notes: `WorkFiles/dojo/build/hall/BUILD_NOTES.md`. Lock `DojoHall` (claude, `Assets/Dojo/DojoHall.blend`).
- **Roof system API:** `Scripts/dojo/roof/roof_kit.py` v1.0.0.
  - Parts: tile field, eave trim, ridge + plain block-and-disc ends, hips, verges, gable faces, bargeboards, gutters,
    downpipes, collision slabs.
  - Compound builders: `irimoya()`, `lean_to_wrap()`, `gable_roof()`. The outbuilding, corridor, pavilion and shed kits
    call these. The tile code is kit 1's (imported, not edited).
- **Hall:** 18 pieces `SM_DKH_*`, exported to `Exports/DojoKit/Hall`.
  - Modular 2 m wall bays (plaster / window / door, transom, clerestory plaster / lattice);
  - veranda, veranda frame, hall frame, granite step band with the central stair;
  - lower roof front / sides, upper roof slope / end / ridge (instanced twice where symmetric);
  - downpipe, eave landing.
  - Only the shared material library is used.
  - QA 18/18 with 0 hard fails; Nanite on the 13 pieces of 2k tris or more.
- **Gameplay:** the grey-box numbers are kept.
  - Eave pads: flat timber decks at +3.0.
  - AC zones and stance are clear; the upper eave step is a 0.40 m walk-up.
  - walk_check: 15/15 routes + 8/8 controls, also at r 0.35. climb_check: every route. New hall_roof_walk: routes 3, 4
    and 5 on the real roof hulls, 10/10 paths + 2/2 controls.
- **Renders:** `hall/renders/r2/` (final; r0 and r1 kept):
  - sheet_hall, sheet_roof (panels a-f), sheet_closeups;
  - sunset context incl. reference 2's composition;
  - side_by_side sheets.
- **Open:**
  - the tiles' gloss and colour (a library RoofTile pass);
  - the landing decks need the user's eye;
  - Unreal import still to do (combined import);
  - blind judge.


## 2026-09-28 - KIT 1 fix round r2f: judge blockers 1-4 (footing, frame pier, ridge + ridge ends, gate leaves)

User direction: address blockers 1-4; no DojoLab walk. Unreal was not touched in this stage.
Script state before this round: `kit1/*_r2fstart_backup.py`, `kit1/DojoKit1_r2fstart_backup.blend`, the r2 FBX in
`kit1/r2start_exports/`. Renders: `renders/kit1_r2f/`.

### Commands (headless, --factory-startup)
```
blender -b --factory-startup --python Scripts/dojo/build_kit1.py                       # QA + LODs + export (~5 min)
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/{walk_check,climb_check,roof_walk_check,measure_kit1}.py
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/render_kit1.py -- --what wall|variants|gate|closeups|beauty --samples 160 --tag ../kit1_r2f
py -3 Scripts/dojo/compose_kit1.py ../kit1_r2f
blender -b --factory-startup --python Scripts/armory/side_by_side.py -- <ABSOLUTE ref> <ABSOLUTE ours> <ABSOLUTE out>   (21 sheets)
```

### 1. Footing: rounded pillow rubble under one dressed course (blocker 1)
- The sheet's front elevation, measured at 123 px/m:
  - footing 0.55 m high;
  - a dressed top course 0.215 m high, with blocks 0.25-0.33 m long;
  - below it, two rows of rounded field stones 0.15-0.22 m high;
  - dark joints 2-3 cm wide.
- Our build (the footing stays 0.60 m high):
  - the dressed course is 0.22 m high (was 0.19): rounded blocks (`kit1_geo.block_stone`), 0.24-0.36 m long;
  - the lower zone is two jittered Voronoi rows (seeds at z 0.06 and 0.255, spacing 0.29). Each cell is inset
    0.8-1.3 cm, rounded by Chaikin and built by the new `kit1_geo.rubble_pillow`: a quarter-round shoulder, an
    off-centre dome 3-5 cm high, a smooth-shaded face, explicit UVs and a side wall unfolded outwards;
  - the joints are 6-10 cm deep, down to a core 5 cm back.
- The hewn polygonal cells and the ashlar quoins are gone. Ends and corners now take rounded corner stones in the
  same stone (`corner_stones`): no light columns.
- Materials (kit-only, recorded in `layout.json` `materials_kit1`):
  - `M_DK_FootingStone` = the library T_DJ_Granite maps, times a linear tint (0.55, 0.55, 0.56), lerped 40 % towards
    the texture's own mean (the "terrazzo" speckle: the BC's std is 0.7 x its mean). Moss (linear 0.085, 0.095,
    0.034) is lerped in by the 'Wear' colour's ALPHA before the library wear maths. `moss_alpha` in build_kit1 bakes
    that alpha: patchy, strongest in the low courses and where the stone is occluded.
  - `M_DK_JointEarth` = the T_DK_EarthCore maps tinted #7A97BB (mean -> linear 0.030, 0.026, 0.021): the dark joint
    packing.
  - Unreal needs a moss lerp on VertexColor.A in the M_DJ_Lib_Opaque instance (not done: no Unreal in this stage).
- Measured: every straight module and the join have 0.0 m x overshoot. Face stones stand 6.1-7.1 cm proud at the
  dome peak. The End module's end-face stones stand 5.5 cm past its end face, which is the exposed end.

### 2. Frame pier rebuilt to the sheet (blocker 2)
`SM_DK_Wall_FramePier` is the same 1 x 1 m footprint with its top at +2.0. Built on all four faces:
- the slab plinth;
- four corner stacks of rounded rubble, 0.23 m wide over three courses (the middle course is two small stones),
  standing 2.5 cm proud of the posts;
- a dressed centre block on each face (0.54 x 0.40 m);
- the recessed earth panel (M_DK_EarthCore, 3.5 cm behind the posts), from the centre block to a light grey stone
  band 0.13 m high;
- four light corner posts, 0.15 m, standing on the stacks. They sample TimberAged's light band (v 0.875-0.97,
  luminance 107-125);
- head beams 0.10 m high with 6 cm beam ends;
- the wall cap, gabled both ends (lighter bargeboards, compact ridge ends).
There is no plank infill, sill or ashlar cube any more.

### 3. Ridge, ridge ends and barge ridges (blocker 3; delta 8)
- Wall cap:
  - three noshi layers, 0.30 / 0.27 / 0.24 m wide and 38 mm each;
  - a banded ridge tube (the new `kit1_geo.ridge_tube`, r 0.068, was a 0.052 roll) with raised cross bands on every
    0.25 m tile;
  - end plates on every tube end, so a module end is never hollow. The section render also closes the cut tube and
    the lapped noshi with render-only plates.
- CAP_SINK 0.075 -> 0.120, so CAP_H (0.375), the body tops, the +2.0 walk plane and every eave tile stay where they
  were.
  - `measure.cap_float`: the faces are unchanged at 0.16-0.24;
  - the tube top (with its bands) now stands 12-13.3 cm above the walk plane (was 8.6).
- Ridge ends: the new `kit1_geo.scroll_oni`, a round-topped stem with a band and two stacked curls, replaces the
  horn slabs and coin discs.
  - Wall ends: 0.17 wide x 0.26 high x 0.12 deep.
  - Gate: 0.42 x 0.70 x 0.34, with a plain round face r 0.16 (no symbol), in place of the 0.66 x 0.78 discs.
- Gate ridge tube r 0.10 (was an 0.085 roll), with bands. Ridge tube top +4.705; ridge ends top +4.936.
- Gate barge ridges (kudari-mune):
  - over the gable plane (u 0.75 from the verge edge, x +-3.25), from under the ridge noshi down to 0.35 m above the
    eave;
  - a bed, three noshi layers (0.28 / 0.25 / 0.22), a banded tube r 0.078 and a scroll end at the eave;
  - the tile rolls under their noshi are left out.
  - The verge keeps a single flat course under a plain roll (r 0.058) with a relief disc at the eave.
  - The old verge-corner disc tiles are gone.
- Wall gable (delta 6): the verge overhang is 0.10 m (was 0.20); bargeboards 3.2 x 8.8 cm (were 5.6 x 13.6); the tie
  beam is lighter.

### 4. Gate leaves rebuilt (blocker 4)
- The street face was measured on the sheet's doors as fractions of each leaf. They are laid out on the leaf's
  VISIBLE height (+3.06 eave beam - LEAF_Z - 0.02 = 2.93 m):
  - hinge stile 0.12 W, meeting stile 0.11 W, standing 3.5 cm proud of the planks;
  - top and bottom rails 0.09 Hv, a middle rail 0.078 Hv at 0.46 Hv, plus a plain closing rail at the very top;
  - four V-grooved planks between the stiles;
  - round iron studs every 0.18-0.22 m along every rail and down both stiles;
  - arrow-end strap hinges at 0.18 and 0.82 Hv, reaching 0.45 W, bolted;
  - hinge-side plates on the middle and bottom rails;
  - big dome bosses on the middle rail: 0.19 m at the meeting stile, 0.16 m at 0.72 W.
  - The ring pulls are gone. The courtyard face is unchanged.
- Leaf envelope: y -0.2335..0 (inside LEAF_TT 0.24); the open passage stays 4.013 m.
- Timber tone:
  - TimberAged has broad V tone bands (row luminance 27-125 at plank width). grain_uv's random V per member caused
    the dark / light planks.
  - `timber_band` now re-centres every side-grain island in an even band: v 0.46-0.60 (luminance 80-101) for every
    kit-1 timber, so the gate frame and the leaves match. The pier uses its light band.
  - Measured in the preview rig: door median sRGB (83, 62, 46) against the sheet's (89, 67, 50).
  - The grain itself (the library texture) still reads streakier than the sheet at door scale: a library question.

### Render fixes (delta 12)
- The footing pair now uses an ortho strip (`footing_front`); the close-up is kept as `sbs_wall_footing_close`.
- The corner view is a 3/4 perspective from above the cap.
- The frame pier is shown near-front, with the other sheet runs hidden.
- The doors are shown face-on.
- `beauty_ref2` is elevated: 3.1 m, just past the courtyard eave.

### QA and checks
- QA 28 / 28 with 0 hard fails. LOD1 / LOD2 on 19 pieces with 0 LOD fails. 28 FBX exported through
  Scripts/pipeline.
- Unique tris 336,409 (r2: 241,485). The Nanite footings: 4 m 45,998 (was 11,111), 2 m 22,834, 1 m 11,753. The gate
  roof 80,400; the leaves 5,540 each; the pier 16,784. Nanite flags OK.
- Walk 15 / 15 routes and every CONTROL blocked. Climb: every route passes. Roof walk 3 / 3; the max rise over the
  ridge is 0.32 m, under the 0.45 step.
- Headroom 3.035. The leaves clear at every 5 deg, with 11.3 mm over the threshold.
- Noshi slits 0 on every cap and the 1 m joint. At the corner-to-1 m joint, 1 ray of 123 sees through (0.5 mm
  sampling).
- `measure_kit1.py` now reads the noshi widths from `layout.json` (`cap_noshi_widths_m`).
- `kit1_geo.py` only gained new functions (rubble_pillow, block_stone, ridge_tube, scroll_oni); nothing the hall and
  roof kits import changed.

### Open
- Deltas 5, 7, 9, 10 and 11 are not done in this round (user scope: 1-4):
  - 5: tile glaze;
  - 7: plaster craquelure and seam;
  - 9: lantern bracket / amber glow;
  - 10: taller plinths, side steps, sill;
  - 11: raked sand.
- The orange flecks in the gate plan are rafter / eave timber showing between the eave tiles. They were already
  there in r2.
- Unreal needs the kit-only materials as instances:
  - M_DK_FootingStone: Granite maps, Tint, a flatten lerp and the moss lerp on VertexColor.A;
  - M_DK_JointEarth.
  It also needs a reimport of the 28 kit-1 FBX. Route 6 still waits for the user's decision.


## 2026-09-28 - Stage: COMBINED DOJOLAB IMPORT, ROUND 2 (hall kit + kit 1 r2f + ground + all props + material library)

User direction: address 1-4, no DojoLab walk needed. The DojoLab editor was not open; one Unreal commandlet at a time.
Stage folder: `WorkFiles/dojo/build/unreal/showcase_r2/` (start backups of every script, layout and capture in
`start_backup/`, the emissive test captures, the sheet script and its region numbers).

### Commands
```
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py [-- --no-export]
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/{walk_check,climb_check,roof_walk_check}.py -- --layout showcase/layout_showcase.json --out showcase/<x>_showcase.json [--hover 0.019]
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/hall/hall_roof_walk.py -- --layout showcase/layout_showcase.json --out showcase/hall_roof_walk_showcase.json
bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify capture
py -3 WorkFiles/dojo/build/unreal/showcase_r2/make_sheet_r2.py
```
Order matters: compose re-exports SM_DGB_Pavilion_NoDrum (new bytes, so a reimport), so `materials` must run after
every `import` (verify gate 1 caught it once: default slots on the re-imported NoDrum).

### Composition (`compose_showcase.py`, layout_showcase.json)
- 169 pieces, 702 instances: grey-box 18, pavilion NoDrum 1, kit 1 154, ground 347, taiko 4, training 14, stone 14,
  modern 46, **hall 104**. 51 material instances, 98 textures, 14 lamp lights. Warnings 0.
- The hall kit (21 SM_DKH_* pieces, layout_hall.json) replaces SM_DGB_Hall_{Body, Veranda, StepBand, RoofLower,
  RoofUpper} and SM_DGB_Landing_EavePad. The grey-box outbuildings, corridors, shed, pavilion (+ its pad) and trees stay.
- Roof ACs: built at +5.10, placed **unscaled** (compose now refuses a scaled one). Vending machine: unscaled at its
  true 0.80 m depth, (12.45, 0.40) rot 180; its UCX box equals the grey-box box (X 12.0-12.9, Y 0.0-0.8, top 1.75).
- Short lanterns: from layout_stone.json at (20.6, 3.3) / (23.4, 3.3), on the sand field (ray cast, +0.000). Their
  footprint starts at Y 2.916: 0.323 m clear of the gate roof's max Y 2.593.
- Markers (24): Vending re-fitted to the machine's UCX; ACUnit_W/E to the casing hull (Y 21.98-23.1, top 5.10);
  Hall_Veranda to the kit veranda (X 11-33, Y 22-34, +0.5); Landing_EavePad_W/E to SM_DKH_EaveLanding's UCX (same boxes
  as the grey-box, top +3.0, 0 delta). Route-5 stance (15.6, 21.66), floor_z 3.0746 (hall numbers).
- Materials: every slot on the library recipe (README); see Unreal below. Kit variants:
  - M_DK_FootingStone: Granite x (0.55, 0.55, 0.56), FlattenToMean 0.40 to the tinted mean, UseMoss by Wear.A with
    (0.085, 0.095, 0.034); FS_FLAT / FS_MEAN are read from build_kit1.py;
  - M_DK_EarthCore / M_DK_JointEarth: triplanar, JointEarth tint #7A97BB; M_DJ_PlasterEarth (kit 1 walls): triplanar;
  - M_DKG_Granite: tint (1.66, 1.92, 2.60) + per-actor tone 0.12 and warm / cool hue;
  - taiko Lacquer / Hide / HideCollar (own maps, UseWear, TileM 2,2), M_DKP_Train_RopeFuzz, M_DJ_Granite_Tri
    (triplanar), M_DKP_Stone_Moss (own maps), the modern kit's own sets.
- Checked the path slabs' two 'Wear' colour layers: FBX layer 0 (the one UE imports) is the library bake.

### Checks on the composed blend (all PASS)
- walk_check: 15 / 15 routes clear, 5 / 5 CONTROLs blocked; also at r 0.35.
- climb_check (hover 0.019): every route (1, 2, 3, 4, 5, 7, 8, veranda, plinth, hurdle); the spec-as-written 4 / 5
  fail by design. Route 5 on the hall roof: mantle 197.4 cm, depth 112; route 4 pad: 172.9 cm, depth 85.6; route 8
  vending: 173.1 cm, depth 80.
- roof_walk_check (gate): PASS. hall_roof_walk on the showcase: 12 / 12 paths + 2 / 2 CONTROLs.

### Unreal (DojoLab, L_Dojo)
- import: 153 meshes: all 132 changed ones deleted before reimport, plus 21 new SM_DKH_*. 56 new textures (the T_DJ_*
  library set + WearMask in /Game/DojoKit/Materials/Textures). Nanite fallback full on every Nanite mesh.
- materials: new masters in /Game/DojoKit/Materials/Masters, built from code in dj_sc_materials.py:
  - M_DJ_Lib_Opaque (UV0; Tint, FlattenToMean / MeanColour, static switches UseMoss / UseWear / UseInstanceVar, the
    README wear maths on the 'Wear' vertex colour with WearMask at UV0 x TileM, RoughMult, NormalStrength);
  - M_DJ_Lib_Triplanar (the same on world projection, TextureSize = tile_m x 100 cm; world-space normal from the three
    DirectX projections);
  - M_DJ_Lib_Emissive (BC x BaseMult, BC x EmissiveIntensity x EmissiveTint).
  The ground masters, the masked grille and the flat masters are kept. Library MIs live in
  /Game/DojoKit/Materials/Library, one per slot name, shared by every kit. Static switches are read back on every MI.
- level: 702 mesh actors, 24 markers, 13 cameras. Bounds gate max 0.0008 cm (non-Nanite, against the all-LOD box) and
  0.0006 cm (Nanite fallback geometry).
  - Finding: UE's non-Nanite render bounds are the union of ALL LODs. SM_DKH_StepBand's decimated LOD1 bulges 3.59 cm
    in front of LOD0 (Y 20.964), so the gates now compare with the all-LOD box (`min_all_lods` / `max_all_lods` in
    blender_bounds.json).
- verify (fresh process): 7 / 7 gates. 169 meshes, 51 Nanite (all fallbacks full), 98 textures, 760 actors, no grey-box
  stand-in left, 24 markers, 18 GASP traces hit their own markers.
- Emissive: EMISSIVE_SCALE (new, dj_sc_common) tested at 1.0 and at LAMP_SCALE 0.25 on the hall lattice glow: x1 gives
  (184, 149, 50) with a 27 % clipped core, warm yellow-white like reference 2; x0.25 gives (165, 100, 8), saturation
  0.95, a deep orange. Kept at 1.0.
- Captures (`unreal/showcase/captures/`, 96 frames, Lumen): CAM_Establishing, CAM_EstablishingRef2 (new: kit 1's
  elevated ref-2 framing), CAM_PlayerEyeSand, CAM_HallVeranda (new), CAM_HallRoofClimb (new), CAM_GateFromCourtyard,
  CAM_GateFromStreet, CAM_Drum, CAM_EastYard (moved out of the grey-box tree canopy), CAM_VendingShed, CAM_WallTop,
  CAM_WallCorner, CAM_Overview. Sheet: `SHOWCASE_SHEET_R2.png` (with dojo1_reference2); region medians in
  `showcase_r2/capture_regions_r2.json`.

### Measured (sRGB medians)
| Region | Value |
|---|---|
| Upper roof tiles | 29-31, 25-27, 33-37 (s 0.24-0.27) |
| Gate tiles | 50, 36, 39 |
| Wall plaster | 186, 138, 97 |
| Sand | 208, 186, 167 (s 0.20) |
| Path | 166, 162, 185 |
| Sky | 136-146 (s 0.07-0.10) |
| Hall veranda deck / post | 103, 42, 15 (s 0.85) / 94, 30, 9 (s 0.90) |

The library timber reads strongly orange-red in UE (sheet TimberDark 80, 59, 46, s 0.43): the warm low sun on warm
timber under UE's tonemapper. The glow's GI is not the cause (the x0.25 glow moved the deck only to s 0.81).

### Open
- Timber saturation in UE (above) and the saturated red gate ceiling in CAM_Establishing (TimberAged under the four
  2400 K gate lamps): a look-pass call (grade, sun or library timber), not this stage's.
- Hall owner: SM_DKH_StepBand's LOD1 bulges 3.6 cm past LOD0.
- The lattice glow's core clips (20-27 % of the glow pixels); final hue and intensity in the look pass (EmissiveTint
  exists).
- The sand rake bands read coarse at player eye (delta 11, outside this round's 1-4 scope).
- The grey-box pieces (trees, outside ground, outbuildings, shed, pavilion) read as flat colours next to the kits.
- Stale round-1 Unreal assets (old M_DK_* / M_DKP_* MIs, the M_DJ_K1 / Prop / EmissiveTex masters, the grey-box hall
  meshes, T_DKP_Stone_* textures) are unused and left in the project; delete them once nothing references them.
- Scripts changed: showcase/compose_showcase.py, unreal/dj_sc_materials.py, unreal/dj_sc_common.py (EMISSIVE_SCALE),
  unreal/dj_sc_level.py and unreal/dj_sc_verify.py (all-LOD bounds), hall/hall_roof_walk.py (optional --layout /
  --out). Not committed.


## 2026-09-28 - INDEPENDENT VERIFIER, ROUND 2 (combined DojoLab import r2) - RESULT: FAIL (2 of 7 areas)

Read-only. Nothing in DojoLab was saved and no builder file was touched; every output is in `WorkFiles/dojo/build/verify_r2/`.
I waited for the ArmoryLab chat's commandlets to finish (two in turn), then ran one Unreal process at a time. No DojoLab
editor was open. The truth sources are my own: `v2_fbx_audit.py` re-imports all 169 exported FBX (UCX, LODs, tris,
slots and vertex boxes), and the expected world boxes are computed from those boxes and the layout matrices, not from
the builder's `blender_bounds.json`.

### Scripts and outputs (all in verify_r2/)
- `v2_fbx_audit.py` -> `fbx_audit.json` (Blender, headless).
- `v2_ue_verify.py` + `run_v2_ue.sh` -> `ue_verify.json` (fresh commandlet, 26 s).
- `v2_ue_ledges.py` + `run_v2_ledges.sh` -> `ue_ledges.json` (fresh commandlet).
- `v2_capture_measure.py` -> `capture_measure.json` + `capture_measure_extra.json`, crops `crop_*.png`.
- The builder's walk / climb / roof checks, re-run fresh on DojoShowcase.blend -> `walk_check.json`,
  `climb_check.json` (hover 0.019), `roof_walk_check.json`, `hall_roof_walk.json`.

### Results
| Check | Result | Numbers |
|---|---|---|
| L_Dojo default map + GASP CMC pawn | PASS | GameDefaultMap and EditorStartupMap are L_Dojo; GlobalDefaultGameMode is GM_Dojo_C, whose default pawn is SandboxCharacter_CMC_C; the world override is GM_Dojo_C |
| Meshes (169 layout pieces) | **FAIL** | 169 / 169 in UE. Convex hulls equal the FBX UCX count on every piece (337 in total), with no other simple shapes. LOD counts, LOD0 / fallback tris and slot names all match the FBX. 51 Nanite meshes, every one with its fallback at RELATIVE_ERROR 0. No prop over 2k tris lacks Nanite. 0 engine-default or missing materials: every MI chain ends in a /Game master. **FAIL: `SM_DKG_Tuft_Grass`, `SM_DKG_Tuft_Moss` and `SM_DKG_Pebbles_Stray` ship with 0 UCX** (NoCollision dressing by spec 5.3; the house rule is UCX on every SM_) |
| Exports vs layout | PASS | Every SM_*.fbx outside the `_superseded_*` folders is in the layout, except the 32 replaced grey-box SM_DGB_* stand-ins. 23 pieces are imported but not placed, as listed (spare gable well, frame pier, kerbs, wall bodies...) |
| Level: one actor per instance, transforms, bounds | PASS | 702 / 702 StaticMeshActors: 0 missing, 0 duplicate labels, 0 extra, per-piece counts equal. Location error <= 0.01 cm, rotation axes <= 1e-4, scale exact (the one scaled instance, Wire_Drop12 x 0.8384, matches the layout). Collision responses per class: 0 errors (tall lanterns block Pawn and ignore Camera / Visibility). Bounds, worst: non-Nanite render bounds 0.0005 cm; Nanite fallback geometry through the actor transform 0.0005 cm. Information only: the Nanite *render/culling* bounds sit up to 62.4 cm outside (SM_DKH_RoofLower_SideW/E; Frame 33.6, Gate_Frame 27.5), whatever the fallback |
| Traversal markers | PASS | 24 / 24 markers are LevelBlock_Traversable. Ledge error 0.000 cm; hidden; Traversable block and Pawn / Vis / Cam ignore. No TRV_ outside the layout. Every route marker is present. Ledge sampling (Pawn traces every 0.25 m, 0.15 m inset): **every ledge a route climbs is a real surface at the marker top (within 3 cm)**, incl. both hall eave landings: 3 / 3 samples each at +3.000 on SM_DKH_EaveLanding 0700 / 0701, and each landing is covered by its marker (1.2 x 0.75 m). Veranda west ledge 42 / 46 at +0.5 (4 on posts). Pavilion pad bottom +1.50; the 2 stale gate-side wall markers are gone. Note: the Hall_Veranda box spans the whole hall footprint; its unused N ledge lies on the hall body (72 / 86 samples start inside it). This is harmless: GASP's Visibility room check fails there |
| GASP forward trace | PASS | 18 / 18 climb stances hit their own TRV_ marker first, none starting in penetration |
| Walk + climb (with controls) | PASS | In-engine Pawn capsule sweeps: 15 / 15 routes clear and 5 / 5 CONTROLs blocked. Blender, fresh: walk 15 / 15 + 5 / 5 at r 0.30 and r 0.35; climb: every route (h 48-198 cm), the spec-as-written 4 / 5 fail by design; gate roof walk 3 / 3; hall roof walk 12 / 12 + 2 / 2 CONTROLs |
| Captures: orange cast, black, blown | **FAIL** | see below |

### Captures (sRGB medians, UE capture against the Blender render of the same view)
| Region | UE | Blender | Verdict |
|---|---|---|---|
| Hall upper roof tiles (ref-2 elevated) | 33,29,39 (s 0.26, R/B 0.85) | 43,40,54 (s 0.26, R/B 0.80) | charcoal, OK (28 % darker) |
| Hall lower roof tiles | 23,16,24 (R/B 0.96) | 31,26,32 (R/B 0.97) | OK |
| Gate roof tiles (gate from courtyard) | 50,36,39 (s 0.28, R/B 1.28) | 49,43,47 (s 0.12, R/B 1.04) | red-shifted |
| Wall-cap tiles | 15,8,8 (s 0.47, R/B 1.88) | 27,22,28 (s 0.21, R/B 0.96) | **red-brown, not charcoal** |
| Kit-1 wall plaster, shade / sun | 186,138,97 / 230,179,122 (s 0.47-0.48) | 116,77,62 / 133,90,71 (s 0.47) | same saturation, hue +11-13 deg towards orange, 1.6-1.7x brighter |
| Hall clerestory plaster, sun | 136,79,46 (s 0.66) | 87,46,27 (s 0.69) | OK in hue |
| Hall lower-bay plaster, shade | 61,14,2 (s 0.97, hue 12) | 69,32,12 (s 0.83, hue 21) | **red** |
| Hall plaster in CAM_HallVeranda | 72,19,3 (s 0.96) | 59,39,23 / 110,76,49 (s 0.55-0.61) | **red** |
| Veranda deck / post | 103,42,15 (s 0.85) / 94,29,9 (s 0.90) | 87,57,37 (s 0.58) / 144,98,65 (s 0.55) | **orange-red** |
| Gate posts (lamp side) | 179,71,15 (s 0.92, R/B 11.9) | 93,48,22 (s 0.76, R/B 4.2) | **orange** |
| Gate ceiling, CAM_Establishing (top 25 % px) | 33,0,0 (hue 1 deg, s 1.0) | 13,3,0 (hue 14 deg) | **pure red** |
| Lattice glow (CAM_HallVeranda) | 255,229,74 (s 0.71) | 245,175,130 (s 0.47) | saturated yellow, core clipped |
- The roof-tile orange cast from round 1 is fixed on the hall, but not on the gate and wall caps. Timber, and plaster in
  shade, read orange-red (saturation 0.85-1.0 against Blender's 0.55-0.83). The sun (5500 K), the neutral grade (gain
  and saturation 1.0), the sky factor (2.6, 1.8, 1.6) and the sky light x6 read back as the builder set them, so the cast
  now comes from the lighting / tonemapping of warm albedos (and the 2400 K lamps near the gate), not from the grade.
- Black: CAM_Drum is 18 % near-black tiles. The grey-box pavilion ceiling is (2, 1, 0): 100 % of its pixels have a max
  channel under 12, i.e. pure black.
- Blown: no capture has more than 0.06 % of its pixels at >= 250 on every channel. The 255-channel pixels are the glow
  cores: 4.7 % in CAM_HallVeranda.
- Missing: nothing. The yellow / green flat blocks are the grey-box stand-ins still in the level.
- The captures_emissive_x025 set measures the same (e.g. CAM_Drum black 18 %); the sheet is identical in both folders.

### Fixes required
1. Timber orange-red in UE, and the red-shifted gate and wall-cap tiles. Pull timber saturation down to Blender's
   (target around s 0.6, hue 20-25 deg), then re-measure these regions.
2. The CAM_Drum pavilion ceiling is pure black. Lift it or re-frame the camera, then re-measure.
3. UCX on SM_DKG_Tuft_Grass / Tuft_Moss / Pebbles_Stray: add a trivial hull (NoCollision stays in Unreal), or record an
   explicit user exception.

### Notes (not failures)
- Short lanterns stand at (20.6, 3.3), not the literal (20.6, 1.0): at 1.0 they would sit under the gate roof (max Y 2.593).
  Their footprint starts at Y 2.916. This honours the "in the courtyard, not under the gate roof" decision.
- Utility pole mesh top +8.05 (8 m). The gable-frame well is imported and not placed.


## 2026-09-28 - KIT 1 ROUND 3 (look pass): footing rebuilt to the sheet, wall end, gate front deltas (Blender only)

User direction: run round 3; drop the invented lamps (no street lamps inside the courtyard, no short lanterns inside
the gate). Those lamps belong to the showcase layout, not kit 1: kit 1 adds no lamp anywhere. Scope: kit 1 wall + gate.
No Unreal in this stage (the look is judged later on Unreal captures). The material library was used as is (another
track owns it this round). Script state before this round: `kit1/*_r3start_backup.py`, `kit1/DojoKit1_r3start_backup.blend`,
`kit1/layout_r3start_backup.json`, the r2f FBX in `kit1/r3start_exports/`.

### Commands (headless, --factory-startup)
```
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/kit1_textures.py --only EarthCore
blender -b --factory-startup --python Scripts/dojo/build_kit1.py                    # QA + LODs + export (~23 min now)
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/{walk_check,climb_check}.py -- --out kit1/<x>_check_kit1.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/roof_walk_check.py
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/measure_kit1.py   # kit1/measure_kit1_r3.json
blender -b --factory-startup Assets/Dojo/DojoKit1.blend --python Scripts/dojo/render_kit1.py -- --what r3studio|r3sunset --samples 96 --tag ../kit1_r3
py -3 Scripts/dojo/compose_kit1.py ../kit1_r3                                      # sbs_r3_*.png (reference crop | ours)
```

### 1. Footing: rounded pillow-faced rubble under one dressed course, squared quoins (a correction to round 2's steer)
- Re-measured on dojo_wall_ref.png's front elevation at 124 px/m (from the 1.8 m figure):
  - the footing is 0.54 m tall;
  - a dressed course 0.235 m tall, blocks 0.18-0.27 m long (19 across 3.9 m, about square);
  - under it, a thin row of small stones 0.10-0.13 m tall and 0.11-0.19 m long;
  - at the ground, a row of big stones 0.19-0.25 m tall and 0.24-0.36 m long;
  - about every metre, a big stone standing through both rows;
  - joints 2-3 cm, dark.
- New construction (`build_kit1` footing section; `kit1_geo.pillow_face`, `kit1_geo.rough_block`):
  - Each row is a chain of slanted joint lines shared by neighbouring stones. The joints stay 1.0-1.6 cm between the
    rims and read 2-3 cm with the shoulders.
  - A small row (0.14 m including joints, its split line jittered -3.5/+3 cm) sits over a big row, with a tall stone
    every 0.2-0.75 m of wall.
  - Rubble outlines lose one or two corners (15-35 %) and are rounded (Chaikin, keep 0.10-0.18) into rounded squares
    and ovals.
  - Each stone is built as a pillow face: a quarter-round shoulder (1.6-2.6 cm) under a broad flat-topped crown
    (bulge 1.4-3.4 cm, superellipse exponent 2-3). The crown carries two octaves of real relief: 9 / m lumps of 6-9 mm
    and 26 / m knobs of 3 mm.
  - The dressed course: blocks 0.18-0.28 m, tighter corners, crown exponent 3.5-5, 1-1.5 cm bulge. Their top joint
    closes under the plaster, so there is no dark band.
  - Ends and corners: a squared, rough-faced quoin block per course (dressed, small row, big row). Long and short
    alternate: 0.34 / 0.24, 0.24 / 0.34 and 0.36 / 0.25 m.
  - The core is 8 cm back (was 5), so the joints are deep and dark. The stones are 12 cm deep.
- Module ends no longer make one straight joint through the footing:
  - At every plain module end, each face's rows are offset along the face (`END_OFF`: dressed 0, small row +7 cm,
    big row -6 cm).
  - The same rule applies at both ends of every module, corner and join, so neighbours interlock whether or not one
    is turned 180 deg.
  - The gate join's end at its post cluster stays straight (`flush`).
  - Measured (`measure_kit1_r3.json` `r3_footing_interlock`, stone faces only): 0 triangle overlaps and closest stone
    gaps of 1.29-1.55 cm. Pairs checked: 4m|4m, 4m|4m turned, 4m turned|2m, 2m|End, Corner|4m, W-run 4m|Corner and
    2m|GateJoin.
  - `footing_extents` now reports the +-6 cm row overshoot by design (0.0 at the join's flush end).
- Material:
  - `M_DK_FootingStone`: FS_FLAT 0.40 -> 0.25 (the stones carry their own relief now).
  - Moss: a lighter olive (lin 0.125, 0.135, 0.036); patches smaller and stronger in the lower courses (`moss_alpha`).
  - Studio render medians (sRGB): dressed course 94, 91, 86 (sheet 99, 93, 89); lower courses 94, 90, 80 (sheet
    92, 82, 70).
- UV1: lightmap_pack overlapped on the dense footings. `uv1_build` now tries the preferred packer and verifies it with
  the pipeline's own UV1 checks. If they fail, it falls back to smart projection + the island packer, then to a wider
  margin. The LODs use it too.

### 2. The wall end (the sheet's bottom-right view) and the wall gables
- `SM_DK_Wall_FramePier`:
  - Every pier timber is now pale weathered timber: posts, head-beam ends, bargeboards, king posts. There is no gable
    tie beam (`cap_geo(tie=False)`).
  - The corner stacks and the centre block are rough-faced blocks.
  - The earth panel's texture is regenerated (`T_DK_EarthCore` r3): mid brown #80654A with about 4200 pale and 1400
    dark pebbles, grit, clods and straw. BC median 128, 101, 74 (the sheet's panel: 128, 102, 76); seam ratio 1.01.
  - Studio render: posts 170, 149, 129 (sheet 196, 166, 136); panel 129, 104, 80.
  - The joint-earth tint moved to #667589, so the footing joints keep the r2f dark mean (lin .030, .026, .021).
- **New kit-only material `M_DK_TimberPale` (FLAGGED for the showcase track):**
  - It is the library TimberAged maps x tint (4.30, 4.05, 3.60), lerped 0.45 towards its tinted band mean.
  - Unreal recipe: the M_DK_FootingStone branch of compose_showcase without moss (M_DJ_Lib_Opaque: Tint,
    FlattenToMean, MeanColour, UseWear on, TileM 4, 4). The numbers are in layout.json `materials_kit1.M_DK_TimberPale`.
  - **compose_showcase.py has no recipe for it yet. The next showcase compose will stop with "no material recipe"
    until one is added** (the frame pier is imported, though not placed).
- Wall-scale ridge ends (WallCap_End, StepPier, GateJoin, FramePier):
  - r2f's tall scroll stem read as a chimney. It is replaced by `kit1_geo.roll_end`: a fat round end tile (r 0.11, 4 cm
    past the verge) with a smaller round tile stacked on it.
  - A tile end plate closes the noshi stack and its bed, so the gable no longer shows a stepped pyramid.
  - The gate roof's own ridge ends are unchanged.
- Plaster body:
  - V-groove panel seams, 1.8 cm wide and 5 mm deep: at every module end (two modules make one groove) and at the
    middle of 4 m modules.
  - Crack ribbons in the joint earth, 1.6-3.6 mm wide and tapering, 1.5 mm off the face. They run down from the cap
    and up from the footing with short branches, 0.5-0.9 per metre per face.
  - Small crazed cell patches were tried and dropped: they read as scribbled marks.
  - Body modules are 220-648 tris, now with two slots (PlasterEarth + JointEarth).

### 3. Gate front deltas
- Lantern (delta 9): `SM_DK_Gate_Lamp` is rebuilt as the sheet's post lantern standing on its bracket:
  - a back plate with straps and bolts;
  - a square arm under the lantern with a curled tip, and an S-scrolled brace under it;
  - a tray, four amber panes with a middle mullion in an iron frame, a flared pyramid hood and a finial knob;
  - LAMP_SCALE 1.25 -> 1.40: about 0.19 m wide and 0.55 m tall with the hood, as the sheet.
  - The glass is the library's M_DJ_GlassAmber (unit UV per pane); the glow is as the library gives it.
  - The lamp light moves to the new glass centre (layout `lamp_lights_world`).
  - The back plate laps over the post's bolt plate: 16-20 hidden triangle overlaps per lamp (measured).
- Plinths, side steps and sill (delta 10):
  - The four street-side corner (lantern) posts stand on a two-block squared plinth, 0.46 m tall.
  - Each plinth sits on a side step 0.16 m tall of four blocks (|x| 2.26-3.62, y -2.17..-1.12), clear of the wall
    cluster and the door posts.
  - A long two-stone dressed sill step (+0.17) runs across the doorway in front of the leaves (y -1.25..-0.97), 7 cm
    clear of the closed leaves' street face.
  - The f2 step stones in front of the door posts are gone.
  - Collision: hull boxes for the steps and the sill (walkable rises of 7 and 16 cm).
- Tile glaze and edge wear (delta 5): not changed here; the library RoofTile belongs to another track. Kit 1's tiles
  already bake the 'Wear' colour, so a library wear switch applies without a rebuild.

### QA and checks
- QA 28 / 28 with 0 hard fails. LOD1 / LOD2 on 22 pieces with 0 LOD fails. 28 FBX exported through Scripts/pipeline.
- Tris:
  - footings: 4 m 117,657 (r2f 45,998), 2 m 60,180, 1 m 32,028, End 34,489, Corner 25,013;
  - StepPier 61,645, GateJoin 20,058, FramePier 26,304;
  - lamp 1,084, paving 19,025;
  - unique 567,337. Nanite flags OK (every piece over 2k).
- Walk: 15 / 15 routes, 5 / 5 CONTROLs blocked. At r 0.35 only the grey-box veranda tread blocks, as before.
- Climb: every route (1, 2, 3, 4, 5, 7, 8, veranda, plinth, hurdle). The spec-as-written 4 / 5 fail by design.
- Gate roof walk 3 / 3 (max rise 0.32). Headroom 3.035.
- Leaves clear at every 5 deg, 11.3 mm over the threshold.
- Noshi slits 0 (the corner-to-1 m joint's 1 of 123, as before). Roof faces: 0 back-face hits.
- Gate joins: 0 triangle pairs with the frame, roof and paving.
- Sizes, the wall and cap collision boxes and every climb and walk number are unchanged.

### Renders (`renders/kit1_r3/`: Cycles, denoised, 96 samples; studio grey from the lit side, plus sunset)
- Pairs (reference crop | ours):
  - wall: `sbs_r3_footing_front`, `sbs_r3_footing_close`, `sbs_r3_wall_34`, `sbs_r3_wall_end_elev`,
    `sbs_r3_wall_end_34`, `sbs_r3_frame_pier`;
  - gate: `sbs_r3_gate_front`, `sbs_r3_gate_base`, `sbs_r3_gate_lamp`, `sbs_r3_gate_34`, `sbs_r3_gate_side`;
  - sunset: `sbs_r3_sunset_gate_street`, `sbs_r3_sunset_footing`, `sbs_r3_sunset_gate_courtyard`.
- High-zoom reference crops: `renders/kit1_r3/refcrops/`. Test renders from before the final build:
  `renders/kit1_r3/_test_superseded/`.

### Open
- Footing vs the sheet:
  - the sheet's stones are a little smaller (19 dressed blocks per 3.9 m, ours about 16 per 4 m);
  - its lower zone is rounder and more tightly packed;
  - its stone faces show a stronger light speckle.
  Unreal will show how the relief reads under the sunset (in r2, UE rendered the footing very dark).
- Before the next DojoLab import:
  - M_DK_TimberPale needs its compose_showcase recipe (above);
  - the kit-1 reimport also brings the new body slots (JointEarth cracks), the new lamp and the gate front collision;
  - re-run the showcase walk / climb checks on it.
- The pier's posts render 170, 149, 129 against the sheet's 196, 166, 136 (a little dark). Its ridge-end plate reads as
  a dark block above the small pier gable.
- Tile glaze, the amber glow's hue and the plaster colour are the library's (not changed here).
- Scripts changed (not committed):
  - build_kit1.py;
  - kit1_geo.py (new functions only: pillow_face, rough_block, roll_end);
  - kit1_textures.py (EarthCore r3, `--only`);
  - render_kit1.py (r3studio / r3sunset);
  - compose_kit1.py (r3 pairs);
  - measure_kit1.py (r3 section).



## 2026-09-28 - ROUND 3: COMBINED DOJOLAB IMPORT + LOOK TUNING (measured in Unreal)

User: "yes run round 3, drop the invented lamps". No DojoLab editor was open. One Unreal process ran at a time,
checked before every step. Stage folder: `unreal/round3/`:
- `start_backup/`: every script, layout, the showcase blend and the r2 captures, as they were at the start;
- `it1`..`it6`: the look iterations;
- `probe1`..`probe7`: the colour probes;
- `r3/`: the final captures;
- `final_json/`: the final step JSONs.

Nothing committed.

### Commands
```
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/{walk_check,climb_check,roof_walk_check,hall/hall_roof_walk}.py -- --layout showcase/layout_showcase.json --out showcase/<x>_showcase.json [--hover 0.019]
DJ_CAPTURE_DIR=<abs>/unreal/round3/r3 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify capture
DJ_PROBE_SPEC=<spec.json> DJ_PROBE_OUT=<dir> powershell -File Scripts/dojo/unreal/run_sc_capture.ps1 -Script dj_sc_colour_probe.py -LogName <x>
py -3 WorkFiles/dojo/build/unreal/round3/{make_sheet_r3,measure_r3,rake_r3_ue}.py r3 [r3]
```
A look iteration that changes only instance values is `prep materials level capture`, about 3 minutes. `prep` runs the
new `showcase/apply_look_r3.py`, which patches layout_showcase.json from `showcase/look_r3.py`, so no re-compose is
needed.

### Import (every track's round-3 exports)
- **Meshes:** 140 of 153 re-imported; each changed FBX was deleted first.
  - kit 1 r3: footing, wall end, lamp, plinths, sill;
  - ground: 68 FBX, including the 8 new `SM_DKG_PaverCourse_2x0p42_A..H`;
  - hall r3: 21;
  - stone: 12;
  - taiko: 3;
  - training: 7.
- **Textures:** 98 (library v1.1.0, ground sand and gravel, taiko, rope fuzz).
- **Nanite:** full fallbacks on all 52 Nanite meshes.
- **Retired meshes:** the level step deleted the 8 `SM_DKG_PathSlab_*` from DojoLab once no actor used them
  (`dj_sc_level.delete_retired`, layout `retired_meshes`).
- **New recipes in compose:**
  - `M_DK_TimberPale` (kit 1 r3): library TimberAged x tint (4.30, 4.05, 3.60), FlattenToMean 0.45 to its mean, TileM 4;
  - the sand `normal_fade` scalars;
  - `M_DKP_Stone_WellMortar` came through the stone table.
- **Dressing:** the tufts and pebbles now carry their trivial UCX and stay NoCollision. Verify gate 1 checks hull
  count = UCX count.

### Layout: the invented lamps are gone
- **Short lanterns:** none placed. The stone layout keeps the piece as an unplaced spare.
- **Street lamps:**
  - none inside the wall;
  - street lamp A stands only on the road, at (17, -4.5) and (27, -4.5);
  - street lamp B is an unplaced spare in the modern layout.
- **Guard:** `look_r3.check_no_invented_lamps` makes compose and prep fail if either lamp comes back.
- **Counts:** 700 mesh actors (was 702) and 10 lamp lights (was 14).

### Look tuning
All values are in `Scripts/dojo/showcase/look_r3.py`; the masters are in `dj_sc_materials.py`.

**New master parameters** (their defaults change nothing):
- `Saturation`, `ValueMult` and `TopBleach` (unused in the end) on every library and ground master, and on the emission
  of `M_DJ_Lib_Emissive`;
- `AOStrength` on Lib_Opaque and Lib_Triplanar;
- in `M_DJ_Ground_Master`, a view-distance fade on the rake normal (`NormalFadeStart/End/FarStrength`, PixelDepth).

**Why the r2 cast was not the grade** (colour probe, `round3/probe1`, `probe2`, `probe5`):
- The grey cards read close to neutral:
  - open shade: lilac (104, 99, 116);
  - sunlit: warm (205, 176, 148);
  - under the veranda: (72-78, 56-63, 57-66), R/B 1.15-1.3.
- The unlit grey cards show the filmic tonemapper's toe: radiance x4 moves sRGB 10 -> 55.
- Dark albedos in shade sit in that toe, and the toe crushes G and B harder than R:
  - TimberDark (74, 62, 54) under the near-neutral veranda light came out (26, 9, 4), s 0.85;
  - even a fully grey lacquer (Saturation 0) on the sunlit drum read (63, 31, 9).
- So the fix is on the material side: lift the dark sets out of the toe (ValueMult) and pull their chroma (Saturation,
  Tint).

**Values:**

| Set | Values |
|---|---|
| Timber sets | VM 1.8, Sat 0.6, Tint (0.82, 1.0, 0.96) |
| RoofTile | VM 2.3, Sat 0.3, RoughMult 1.25, Tint (0.96, 1.0, 1.03) |
| PlasterCream | VM 1.35, Sat 0.78 |
| FootingStone | VM 2.6, Sat 0.55, Flatten 0.5, AO 0.45 |
| Granite (library, triplanar) | Flatten 0.7, Sat 0.55, NormalStrength 0.55, AOStrength 0.3 |
| GraniteRubble | AO 0.45 |
| Paver granite | Tint (1.52, 1.44, 1.10) |
| Gravel | Tint (1.10, 1.08, 0.82) |
| Sand | VM 0.9, Tint (1, 1, 0.95) |
| GlassAmber | EmissiveIntensity 500 -> 120, emission Saturation 0.85 (amber; only the cores clip) |
| Taiko lacquer | VM 1.4, Sat 0.45 |

The granite AOStrength matters most: the granite ORM's cavity AO (5th percentile 122/255) was the dalmatian speckle in
shade.

**Pavilion ceiling:**
- The DF fix alone (SM_DGB_Pavilion_Roof DF x6, two-sided; kept) did not move it.
- The cause was the dark grey-box albedo sitting in the toe.
- The roof actor now carries a flat `M_DJS_PavilionRoof_GB` (0.26, 0.25, 0.25) override. The shared grey-box MI and
  the mesh are untouched.
- Result: (2, 1, 0) -> (49, 28, 18).

**Lighting:** the sun, sky, sky light, exposure and grade are unchanged. Only the four gate bracket lamps changed:
2400 -> 3000 K (`LAMP_TUNE`). Doubling their power was tried and dropped: it warmed the wall cap to R/B 1.54.

### Measured
Final captures in `unreal/round3/r3/`, sRGB medians. The boxes are drawn in `r3/regions/`; every number is in
`r3/measure_r3.txt`.

| Region | r2 | r3 | Target |
|---|---|---|---|
| Hall post, veranda shade | (94, 29, 9) s 0.90 | (42, 27, 20) s 0.52, hue 19 | s 0.45-0.6, hue 20-25 |
| Veranda deck | (103, 42, 15) s 0.85 | (32, 17, 13) s 0.59 | s <= 0.6 |
| Gate post by its lamp | (179, 71, 15) s 0.92 | (133, 83, 40) s 0.70, hue 28 | |
| Upper roof tiles (ref-2 view) | (33, 29, 39) R/B 0.85 | (47, 43, 55) R/B 0.85 | R/B ~1.0 (ref 0.88) |
| Gate tiles, from the courtyard | R/B 1.28 | (85, 68, 69) R/B 1.23 | ~1.0 |
| Gate tiles, gate front close-up | - | (45, 37, 43) R/B 1.05 | ~1.0 |
| Wall cap, courtyard view | (15, 8, 8) R/B 1.88 | (31, 22, 25) R/B 1.24 | ~1.0 |
| Wall cap, close-up | - | (56, 45, 49) R/B 1.14 | ~1.0 |
| Kit-1 wall plaster, lit | s 0.48 | (223, 179, 134) s 0.40 | cream |
| Kit-1 wall plaster, shade | s 0.47 | (176, 138, 108) s 0.39 | cream |
| Hall clerestory plaster, lit | (136, 79, 46) s 0.66 | (162, 141, 124) s 0.23 | cream |
| Hall lower-bay plaster, veranda shade | (72, 19, 3) s 0.96 | (84, 46, 20) s 0.76 | <= 0.6 (NOT met) |
| Sand, lit | (208, 186, 167) s 0.20 | (212, 181, 149) s 0.30, hue 30 | (200, 172, 140) +-12 |
| Path pavers | (166, 162, 185) lilac | (143, 129, 119) s 0.17, R/B 1.20 | (145, 135, 125), R/B 1.08-1.25 |
| Gravel, lit | cool | (141-151, 123-128, 107-108) s 0.23-0.29, hue 27-29 | (150, 132, 112), hue 28-36 |
| Step band granite speckle (hp std / mean) | 0.26 (it1) | 0.15 | fine grey |
| Lattice glow (veranda) | (255, 229, 74), 27 % clipped | (248, 160, 61) hue 32, s 0.75, 17 % clipped | amber, only the cores clip |
| Lamp glass, gate front | - | (250, 178, 83) hue 34 | ref lamp (247, 174, 85) |
| Lamp glass, lantern | - | (254, 178, 77) | ref lamp (247, 174, 85) |
| Pavilion ceiling (CAM_Drum) | (2, 1, 0) | (49, 28, 18), 3.9 % near-black | not black |
| Gate ceiling in the gateway (CAM_Establishing top 25 %) | (33, 0, 0) | (5, 1, 0) | NOT met |

- **Rake spacing** (CAM_EstablishingRef2, the ground track's method): r3 is 0.093-0.096 m with the 0.048 m fine line;
  r2 was a single 0.178 m line.
- **Moire proxy** (band-passed row-mean rms / mean on shadow-free far sand):
  - ref-2 view: 0.008 (r2 0.008);
  - player eye: 0.014 (r2 0.012);
  - no beat bands are visible in the far-sand crops.
- **Blown:** at most 0.06 % of any capture is >= 250 on every channel.

### Checks (final state)
- **Blender** (the composed blend):
  - walk: 15 / 15 routes, 5 / 5 CONTROLs blocked, also at r 0.35;
  - climb: every route, with the proven numbers:

    | Obstacle | Height (cm) |
    |---|---|
    | Wall | 198.1 / 193.7 |
    | Pier | 123.1 |
    | Cistern | 122.3 |
    | Eave pad | 172.9 |
    | AC | 197.4 |
    | Crates | 123.1 / 122.3 |
    | Pavilion pad | 197.9 |
    | Vending | 173.1 |

  - gate roof walk: 3 / 3;
  - hall roof walk: PASS.
- **Unreal verify** (fresh process): 7 / 7 gates.
  - 169 meshes; 52 Nanite, all with full fallbacks; 98 textures;
  - 762 actors, 700 of them mesh actors; bounds within 0.0008 cm;
  - 24 markers at 0.0 cm; 18 / 18 GASP traces hit their own marker;
  - 10 lamps.

### Captures
Folder: `unreal/round3/r3/` (96 frames, Lumen), plus `SHOWCASE_SHEET_R3.png`. It holds the r2 set (13 CAM_*) plus
these close-ups:
- CU_SandEye;
- CU_PathStepBand;
- CU_WallFooting: east of the gate (the vending machine blocked the first framing);
- CU_GateFront;
- CU_HallUpperRoof: oblique, showing the west diagonal ridge and the ridge end;
- CU_Lantern;
- CU_Taiko;
- CU_Training: makiwara, rack, wooden dummy.

### Open (for the judges / next round)
- **Tonemapper toe:** this is the mechanism behind every "orange-red in shade" read. The materials now compensate for it.
  - A global fix was measured (probe2): film toe about 0.3 plus about +0.3 EV. It took the post from s 0.85 to 0.65 and
    the wall cap from R/B 1.71 to 1.27.
  - It was not applied: the brief changes lighting and post only for a measured cast.
- **Gate ceiling inside the gateway:** only the bracket lamps light it (sky light x2 moved it only from 8 to 11), and it
  reads near black (5, 1, 0). It needs the post toe change or a real fill; a material value cannot fix it.
- **Hall lower-bay plaster** under the veranda is still s 0.76 (warm glow plus the toe). Lit plaster is cream.
- **Sunlit timber** reads light and warm since the timber lift (taiko stand (143, 89, 44)). The sheet shows darker stands.
- **Taiko lacquer** reads orange-red (100, 25, 4). The light on it is warm enough that a grey albedo reads s 0.86.
- **Gate and wall-cap tiles** are at R/B 1.05-1.24 against a target of about 1.0, from warm bounce off the plaster and
  the sun. The upper roof is at 0.85.
- **Grey-box stand-ins** (trees, outbuildings, shed, pavilion) still read as flat colour blocks.
- **Scripts changed** (not committed):
  - showcase/compose_showcase.py;
  - new showcase/look_r3.py and apply_look_r3.py;
  - unreal/dj_sc_materials.py;
  - unreal/dj_sc_import.py (DF fix);
  - unreal/dj_sc_level.py (actor overrides, retired meshes);
  - unreal/dj_sc_capture.py (DJ_CAPTURE_DIR, DJ_CAMS);
  - unreal/dj_sc_colour_probe.py (veranda cards, MI overrides, capture PP);
  - unreal/run_showcase_unreal.sh (prep runs the look patch);
  - WorkFiles/dojo/build/unreal/round3/*.py.


## 2026-09-28 - ROUND 3 FIX f1: the two Unreal judges' blockers (whole 6/10, detail 6.5/10), Blender assets + Unreal

User: "yes run round 3, drop the invented lamps" (the lamp decision stands: no street lamp inside the wall, no short
lantern placed; `look_r3.check_no_invented_lamps` still guards compose and prep). No DojoLab editor was open; one Unreal
process at a time, each step its own fresh process.

- **Work folders:**
  - `unreal/round3/f1_work/`: start backups of every script and layout plus the stone layout; the look iterations L1..L8;
    the API probes.
  - `unreal/round3/f1/`: the final captures (21 stills), `SHOWCASE_SHEET_R3_f1.png`, `regions_f1.json`,
    `rake_moire.json`, and `json/` (the final step and check JSONs).
- Nothing committed.

### Commands
```
blender -b --factory-startup --python Scripts/dojo/ground/make_ground_textures.py -- --only Sand
blender -b --factory-startup --python Scripts/dojo/ground/build_ground_kit.py          (QA 72 pieces, 0 hard fails, 72 FBX)
blender -b --factory-startup --python Scripts/dojo/hall/build_hall.py                  (QA 21 pieces, 0 hard fails, 21 FBX)
py -3 Scripts/dojo/showcase/make_sky_clouds.py                                         (T_DJS_SunsetClouds, 4096 x 1024)
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py        (173 pieces, 708 instances, 0 warnings)
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/{walk_check,climb_check,roof_walk_check,hall/hall_roof_walk}.py -- --layout showcase/layout_showcase.json --out showcase/<x>_showcase.json [--hover 0.019]
DJ_CAPTURE_DIR=<abs>/unreal/round3/f1 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify capture
py -3 WorkFiles/dojo/build/unreal/round3/make_sheet_r3.py <abs>/unreal/round3/f1 f1
py -3 WorkFiles/dojo/build/unreal/round3/measure_r3.py <dir> f1 ; py -3 WorkFiles/dojo/build/unreal/round3/rake_r3_ue.py <dir>
```

### 1. Sky and sun (whole judge blocker 1, delta 1)
- **UE 5.8's VolumetricCloud does not render in the showcase's SceneCapture2D stills.**
  - Tested in L3 and L3b: coverage 0.9, density 0.03, layer 1.5-4.5 km, the Cloud show flag on the capture,
    r.VolumetricRenderTarget 0. No cloud appeared in any still.
  - The code path stays (`look_r3.ENV["clouds"]`, off).
- **A painted cloud dome instead** (our own work, nothing copied from the references).
  - `Scripts/dojo/showcase/make_sky_clouds.py` builds a periodic FFT-noise cloud field: flat banks stretched 5x along the
    azimuth, with most of the cloud at 10-35 deg elevation.
  - Colour is a function of the angle to the layout sun: lit peach-orange (244, 166, 116) toward the sun, grey-violet
    (138, 118, 142) away from it, brighter thin rims, darker thick cores.
  - `dj_sc_level.sky_dome()` imports the texture and builds `M_DJS_SkyClouds`: unlit, translucent, two-sided, no vertex
    fog. Its UV is the view direction from the dome centre, so mesh UVs do not matter.
  - It sits on the engine's `SM_SkySphere` (the engine asset is not edited): radius 2.4 km, centred on (22, 18),
    NoCollision, no shadow, emissive x 75, tag `DJ_SkyDome`. The SkyAtmosphere shows through the gaps.
- **Sun:** elevation 13 -> 12 deg, temperature 5500 -> 5000 K, lux 420 kept.
  - Set in `look_r3.ENV`; `apply_sun` patches the layout sun, so verify gate 6 compares against it.
  - L1 at 9 deg put most of the courtyard in the walls' shade: the sand read s 0.16 lilac and the sky violet.
- **Sky:** `SKY_FACTOR` (2.6, 1.8, 1.6) -> (3.4, 2.6, 2.5); sky light 6 -> 4.5.
  - Reference 2 measured: sky top (175, 157, 160), sky low (221, 162, 134), lit cloud (213, 173, 154).
  - f1 CAM_EstablishingRef2 sky box: (190, 150, 152). r3 was 136-146, s 0.07-0.10.
- **Film grain:** 0.15 in the PPV (`ENV["grade_extra"]`), against 8-bit banding.
  - The r3 sky column was already dithered +-1; the clouds now break up the flat gradient.
- **Tree shadows off:** the grey-box tree canopies cast no shadow (`look_r3.NO_SHADOW_PIECES`, delta 4). Their disc
  shadows are gone from every wide camera.
- **Verify:** gate 6 checks the dome (and the clouds when they are on); gate 3 leaves the dome out of the mesh-actor
  count.

### 2. Hall (whole blockers 2 and 3; deltas 2 and 3; detail blocker 3)
- **Upper roof 25 -> 30 deg** (`UP_PITCH`). The lower roof keeps 25 deg for routes 4-5.
  - The eave stays at +5.5 at Y 23.1 (route 5).
  - The planes meet at +8.906 (was +8.251); the ridge cap top is +9.365.
  - The wall plate follows the steeper rafters: +5.447 to +5.687.
- **Ridge step fix:** the 30 deg slope made the step onto the walkable ridge box 0.48 m, over the 0.45 m step limit (hall
  roof walk, `br_upper_roof_over_the_ridge`).
  - New `roof_kit.irimoya(ridge_hull_drop=)`: the hall passes 0.08, so the ridge box top sits 8 cm under the visual crown.
  - Default 0, so other callers are unchanged.
- **Measured** on CAM_EstablishingRef2 (luminance profile at x 600): the upper roof is 25 % of the grade-to-ridge image
  height in r3 and **28 %** in f1.
  - By geometry it is 41 % (ridge cap to eave, over ridge cap to grade).
  - The 3.1 m camera foreshortens the slope; the judge's 37 % comes from the reference's high camera.
- **Clerestory:** its height is the route-5 gap and stays: the lower roof at +4.17 at the wall, up to the upper eave at
  +5.5 (spec 4.4, and the proven AC +5.10 with the 0.40 m walk-up).
  - The two plaster courses are now the hall's own dark vertical boarding (koshi-ita, as on the wainscot).
  - Only a 0.30 m cream strip is left under the wall plate on the wings (the sheet's wing strip).
  - The centre keeps the lit frieze, now over boarding.
  - The visible lit band in the ref-2 view is now about 7 % of the hall height (r3: about 16 %, two cream courses).
- **Hall base:** the user's continuous band (2026-10-02, walk up anywhere) stays, as one low granite plinth course.
  - The plinth: top +0.15, Y 21.45-22.05, X 11-20 and 24-33.
  - The deck (+0.5) sits 0.35 m above the plinth on its fascia. Both rises are under the 0.45 m step.
  - The 17 cm gap under the fascia shows the short posts on their footing stones.
  - The first f1 import showed sky through that gap, because the ground kit stops at the veranda footprint. A rubble-stone
    underfloor at grade (in the Veranda piece) now keeps it dark.
  - The central stair spans X 20-24 (the two middle bays): 3 risers of 0.167 m, treads 0.40 m (Y 20.85 / 21.25 / 21.65,
    each to 22.05).
  - Every step joints at X 22.0, in line with the path's centre joint.

### 3. Ground (whole deltas 5 and 6; detail blocker 1; detail deltas 1 and 5)
- **Path re-laid as two slabs across:** 57 slabs, `SM_DKG_Slab_100x{60,70,80,90}_{A,B,C}`.
  - Each is 1.0 m across by 0.6-0.9 m long, with 8 mm joints, a 12 mm arris, and its own UV offset and Wear-R tone.
  - The two columns' joints are staggered by at least 0.30 m (`slab2_columns`, a depth-first search). The outer edges are
    straight.
  - The r3 paver courses are retired (`look_r3.RETIRED_MESHES`) and absent from DojoLab.
- **Path width:** kept at 2.0 m. Path / field = 2 / 13 = 0.154, and reference 2 measures 0.155 at the hall end, so the
  path already has the reference's ratio and was not narrowed.
- **Rake texture straightened** (`make_ground_textures.py`); the period is unchanged:

  | Parameter | Change |
  |---|---|
  | Line jitter | 0.16 -> 0.03 |
  | Wobble | 4 -> 0.6 mm |
  | Beads, slumps, width and depth variation | to about a quarter |
  | Crest blur | 1.2 -> 0.8 px |
  | Grain lumps | 0.8 -> 0.3 mm |
  | Crumbs | 0.7 -> 0.4 mm |

- **Rake measured in Unreal** (`rake_r3_ue`):
  - Spacing: near 0.0932 m, mid 0.0957 m.
  - The only secondary peak is now the 0.048 m fine-line harmonic. r3 had off-harmonic 0.12 m and 0.078 m components at
    5-6 %; they are now 0.3-0.9 %.
  - Moire proxy: ref-2 view 0.0085 (r3 0.0085); player eye 0.018 (r3 0.014). No beat bands show in the crops.
  - `NormalFarStrength` 0.35 -> 0.6, so the lines stay legible at mid distance.
- **Sand:** Saturation 0.85, ValueMult 0.88. Lit sand measures (208, 178, 150), s 0.28, hue 29 (r3: s 0.30, hue 30).
  - FLAGGED: reference 2's own lit sand measures s 0.29-0.35 at hue 23. A 25 % desaturation, as the judge asked, would move
    it off the reference, so only a small step was taken.
- **Gravel:** one look, desaturated (Sat 0.55, Tint (1, 1, 0.92)). The coarse gate strip is lifted x 1.5 to match.
  - Ref-2 view (134, 123, 125) s 0.08; lit near the stair (128, 100, 87) s 0.32; west yard (138, 126, 124).
- **Sand edging:** ValueMult 0.42, weathered brown; it no longer reads as a pale lilac strip.
- **Lanterns moved forward:** the tall pair goes from Y 20.5 to Y 19.75 (layout_stone.json and build_stone_props.py). The
  CU_Lantern camera follows.
- **Outside the gate:** the grey-box outside plane carries the gravel material (an actor override) instead of flat green.

### 4. Materials (instance values in the `look_r3.py` f1 section)
Covers deltas 7, 8, 10, 11 and 12, and detail deltas 2, 3, 10-12 and 14. Measured values are sRGB medians on the f1
captures.

| Set | f1 value | Measured |
|---|---|---|
| RoofTile: one material for gate, wall cap and hall | FlattenToMean 0.55 to the tinted mean (kills the fleck speckle); Tint (0.91, 0.98, 1.05) | Hall upper roof (59, 57, 72), R/B 0.82; ref 2 (63, 61, 72), 0.875. Ridge (47, 46, 61) and diagonal roll (54, 50, 60): the same charcoal as the tile field (r3: pale, with copper bands). Gate front (46, 38, 42) |
| Iron | Saturation 0.4 | Ridge straps read dull dark, not orange |
| GlassAmber (shoji, lamps) | EmissiveIntensity 120 -> 65; Saturation 0.85 -> 0.5 | Veranda glow (196, 131, 95), s 0.52, 0 % clipped (r3: s 0.75, 17 % clipped). Lantern glass 1 % clipped (r3: 50 %) |
| Taiko lacquer | FlattenToMean 0.85 to (0.075, 0.032, 0.055); VM 0.75 | Lit (121, 27, 14): deep red-maroon, not orange (r3: (100, 25, 4), s 0.96) |
| Taiko stand (new M_DJS_TimberStand) | VM 0.9, Sat 0.3, blue-shifted tint | Reads dark aged brown |
| Taiko sticks (M_DK_TimberPale) | Pale wood | Plain light wood |
| Training props (new M_DJS_TimberMid) | TimberDark maps x VM 3.8 | Rack (61, 53, 50), dummy (66, 54, 47); r3 was near-black, 30-36 |
| Makiwara rope | Saturation 0.38, VM 1.2 | (126, 95, 70), s 0.44: hemp (r3: s 0.80) |
| Lantern moss | Saturation 0.6, Tint (0.8, 1, 0.9) | Olive-grey, no orange |

### Checks (final state)
- **Blender** (the composed blend, capsule r 0.30):
  - Walk: 15 / 15 routes pass, the CONTROLs are blocked, and it also passes at r 0.35.
  - Climb: every route passes, with the proven numbers unchanged:

    | Obstacle | Height (cm) |
    |---|---|
    | Wall | 198.1 / 193.7 |
    | Pier | 123.1 |
    | Cistern | 122.3 |
    | Eave pad | 172.9 |
    | AC | 197.4, plus the 0.40 m walk-up |
    | Crates | 123.1 / 122.3 |
    | Pavilion pad | 197.9 |
    | Vending | 173.1 |

  - Gate roof walk: PASS.
  - Hall roof walk: PASS. This covers route 5 up the 30 deg slope, the diagonal ridges, the centre plane and the BR path
    over the ridge; 2 / 2 CONTROLs blocked.
- **QA:** ground (72 pieces) and hall (21 pieces) have 0 hard fails, with a UCX on every SM_. Both are exported through
  Scripts/pipeline.
- **Unreal verify** (fresh process): 7 / 7 gates.
  - 157 meshes, 98 textures, 708 mesh actors.
  - Bounds within 0.0008 cm.
  - 24 markers; 18 / 18 GASP traces hit their own marker.
  - The sky dome is present.
- **Blown pixels:** no capture has more than 0.1 % of its pixels blown.

### Captures
`WorkFiles/dojo/build/unreal/round3/f1/` holds:
- the 13 CAM_* and 8 CU_* stills, from the same cameras (CU_Lantern re-aimed at the moved lantern);
- `SHOWCASE_SHEET_R3_f1.png`.

### Not done / flagged for the user
Each of these was asked for by a judge, and each either conflicts with a proven number or belongs to another kit.
- **Hall clerestory height:** closing it to the sheet's thin strip means dropping the upper eave toward the lower roof.
  That breaks route 5 (AC +5.10, 0.40 m walk-up to +5.5) and spec 4.4, so it needs a route-5 redesign. User call.
- **AC units** (whole delta 10): their tall stands are route 5 (AC top +5.10), so they stay.
- **Gravel apron x 1.5** (whole delta 12): the apron (Y 19-21.5) sits between the spec's 28 x 17 m fight floor and the
  hall. Widening it would shrink the floor, so only the lanterns moved forward.
- **Kit-1 geometry**, not touched this round:
  - the wall plaster module seams (delta 9: vertical lines at the 4 m module joints);
  - the thick wall-cap log beam and the oversized eave discs (detail delta 8);
  - the gate ridge's noshi courses and disc onigawara, and verge ridges that do not reach the eave (detail delta 4);
  - the hall ridge-end onigawara disc face (detail delta 3);
  - footing moss and per-stone tint variation (detail delta 9).
- **Gate tiles in sun:** from the courtyard they read warm, (99, 71, 66), R/B 1.5, because the low sun hits that slope.
  At the gate front (shade) they read (46, 38, 42), and the wall cap (57, 46, 48). All roofs share one material; the
  difference is the lighting.
- **Still open from r3:**
  - the gate ceiling in the gateway reads (9, 1, 0) (tonemapper toe and fill);
  - the hall's lower-bay plaster under the veranda is s 0.72;
  - the deck reads (25, 17, 13), darker than the reference's (70, 44, 29).
- **Grey-box stand-ins** (trees, outbuildings, shed, pavilion) still read as flat blocks. Outside the gate there is only
  a gravel plane, with no roofline yet (kit 12).

### Scripts changed (not committed)
- `Scripts/dojo/showcase/look_r3.py`: the f1 section (ENV, NO_SHADOW_PIECES, apply_sun, the looks, the overrides).
- `Scripts/dojo/showcase/apply_look_r3.py`: the sun.
- `Scripts/dojo/showcase/make_sky_clouds.py`: new.
- `Scripts/dojo/unreal/dj_sc_common.py`: ENV hookup.
- `Scripts/dojo/unreal/dj_sc_level.py`: sky_dome, cloud_mi, the no-shadow pieces.
- `Scripts/dojo/unreal/dj_sc_verify.py`: dome and cloud checks.
- `Scripts/dojo/unreal/dj_sc_capture.py`: capture cvars and show flags.
- `Scripts/dojo/ground/make_ground_textures.py`.
- `Scripts/dojo/ground/build_ground_kit.py`: the slab path.
- `Scripts/dojo/hall/build_hall.py`: UP_PITCH, plinth and stair, clerestory boarding, underfloor.
- `Scripts/dojo/roof/roof_kit.py`: ridge_hull_drop.
- `Scripts/dojo/props/stone/build_stone_props.py`: the lantern Y.
- `WorkFiles/dojo/build/props/stone/layout_stone.json`.
- `WorkFiles/dojo/build/unreal/round3/make_sheet_r3.py`: the f1 tag.


## 2026-09-28 - INDEPENDENT VERIFIER, ROUND 3 (after fix f1) - RESULT: FAIL (look targets and black regions; everything structural passes)

Read-only. Nothing in DojoLab was saved and no builder file was touched. Every output is in `verify_r3/`. No Unreal
process was running at the start and no DojoLab editor was open. I ran two fresh commandlets, one at a time (83 s and
17 s), and none is left running. My truth sources:
- `v3_fbx_audit.py`: my own headless re-import of all 173 layout FBX;
- the layout matrices;
- my own boxes on the f1 captures (not the builder's `regions_f1.json`).

### Scripts and outputs (verify_r3/)
- `v3_fbx_audit.py` -> `fbx_audit.json`
- `v3_ue_verify.py` + `run_v3_ue.sh` -> `ue_verify.json`. This is r2's verifier plus two new gates: gate 8 (lamps, the new
  user decision) and gate 9 (retired meshes).
- `v3_ue_ledges.py` + `run_v3_ledges.sh` -> `ue_ledges.json`
- `v3_capture_measure.py` -> `capture_measure.json`, `regions/<cam>.png` (boxes drawn; red = off target),
  `near_black_map.png` (pixels with max channel < 12 painted red)
- Blender checks, re-run fresh on DojoShowcase.blend: `walk_check.json`, `climb_check.json` (hover 0.019),
  `roof_walk_check.json`, `hall_roof_walk.json`

### Results
| Check | Result | Numbers |
|---|---|---|
| L_Dojo default map + GASP CMC pawn | PASS | EditorStartupMap and GameDefaultMap are L_Dojo; GlobalDefaultGameMode and the world override are GM_Dojo_C, and its pawn is SandboxCharacter_CMC_C |
| Meshes | PASS | 173 / 173 in UE (UE 5.8.3). Hulls equal the FBX UCX on every piece (345), with no other simple shapes. Tufts and pebbles have 1 / 1 each. LODs, LOD0 tris and slots all match. 52 Nanite meshes, all fallbacks full. 0 engine-default or missing materials; the grey-box stand-ins in use are on /Game M_DGB_* |
| Level: actors, transforms, bounds | PASS | 708 / 708 layout actors, plus SkyClouds_Dome (not a layout piece): 0 missing, duplicate, extra or wrong-mesh. Location, rotation and scale errors 0 (loc <= 0.01 cm). Collision classes 0 errors. Bounds, worst: 0.0005 cm non-Nanite and 0.0005 cm Nanite fallback geometry. Nanite render-bounds inflation up to 62.4 cm (engine, information only). Retired PathSlab / PaverCourse meshes are gone from DojoLab |
| Traversal markers | PASS | 24 / 24 LevelBlock_Traversable, ledge error 0.000 cm. Ledge by ledge, every ledge a route climbs is a real surface: walls 70-104 / 70-104 on; Hall_Veranda W 42 / 46 (4 samples on posts). Both eave landings are covered at +3.000. Note: my centre probe starts 60 cm up, and on Hall_Veranda it now begins inside the hall frame hulls, which reports "1/5". That is a probe artefact, not a climb surface: the ledge check covers it |
| GASP forward trace | PASS | 18 / 18 stances hit their own marker, none starting in penetration |
| Walk / climb / roof walk, with controls | PASS | In engine: 15 / 15 routes clear, 5 / 5 CONTROLs blocked. Blender: walk 15 / 15 + 5 / 5 (also at r 0.35). Climb heights are identical to r2 (wall 198.1 / 193.7, pier 123.1, cistern 122.3, pad 172.9, AC 197.4, crates 123.1 / 122.3 / 122.9, pavilion pad 197.9, vending 173.1); the spec-as-written 4 / 5 fail by design. Gate roof 3 / 3; hall roof 5 / 5 + 2 / 2 CONTROLs |
| No invented lamps | PASS | Short lanterns: 0 placed. Street lamp A only at (17, -4.5) and (27, -4.5), outside the wall on the street, where reference 1 shows them; B is unplaced. No lantern in the gate zone. The tall lanterns stand at Y 19.75. 10 point lights, each on a placed lamp (0 orphans): 4 gate bracket, 2 tall lanterns, 2 wall lamps, 2 street A |
| Captures: region targets | **FAIL** | see below |
| Captures: no black / blown | **FAIL** blacks (blown PASS) | see below |

### Captures (sRGB medians, my boxes)
Reference 2, for calibration: upper roof (63, 61, 72) R/B 0.88; lit plaster (153, 113, 87) s 0.43 hue 24; timber
(81, 53, 33) s 0.59 hue 25; sand (190, 153, 128) s 0.33 hue 24. I calibrated "plaster cream" on this: hue 22-50,
s <= 0.45.
- **Sand: 7 / 7 PASS.** s 0.26-0.35, hue 28-30, e.g. (202-223, 168-187, 133-157).
- **Timber, s 0.45-0.60 and hue 20-25: 2 / 15 pass.** Only the hall posts in veranda shade pass: (36-38, 24-26, 17-18),
  s 0.53. Failures:
  - gate posts by their lamps: (125-132, 77-81, 38-39), s 0.70, hue 27;
  - CU_GateFront posts: s 0.72-0.77;
  - CAM_Establishing: sunlit post (143, 81, 27), s 0.81; shaded post (26, 12, 4), s 0.85;
  - taiko stand in sun: (102-114, 54-62, 21-26), s 0.77-0.79;
  - gate leaf in sun: hue 32;
  - veranda deck: (19, 12, 9), hue 18 and 26 % near-black;
  - wall-cap beam and clerestory boarding: s 0.34-0.40, hue 18-21.
- **Tiles, R/B 0.90-1.10: 3 / 14 pass.** Passes:
  - gate tiles in shade (47, 40, 44), 1.07;
  - gate ridge face, 0.94;
  - hall lower roof in CAM_Establishing, 0.95.

  Failures:
  - gate slope in sun (99, 71, 63), R/B 1.57, and its ridge 1.38;
  - wall caps: 1.21 (close-up), 1.38 / 1.53 (from the courtyard), 2.18 in sun (CAM_Drum);
  - hall upper / lower roof on the ref-2 view: 0.81 / 0.80, and 0.85 in CU_GateFront. These are bluer than the band;
    reference 2 itself is 0.88.
- **Plaster: 4 / 8 pass.** The kit-1 wall passes: (176-224, 140-178, 109-129), s 0.35-0.42, hue 28-31. Failures:
  - hall lower bay under the veranda: (70-82, 40-48, 18-23), s 0.72-0.74, orange-brown;
  - hall upper panel under the eave: (31, 8, 1), s 0.97;
  - kit-1 wall in direct sun (CAM_Drum): (224, 166, 94), s 0.58.
- **Black: FAIL.**
  - The gateway ceiling and lintel are (7, 1, 0) and (3, 1, 0): 62-83 % of their pixels have max channel < 12.
  - CAM_Establishing is 25.6 % near-black overall, with 89 fully black 32 px tiles. CU_GateFront's ceiling is 64 %
    near-black.
  - Shaded hall timber crushes too: CAM_HallVeranda 19.7 % near-black (88 black tiles), CU_PathStepBand 17 % (74),
    CU_Lantern 15 % (45), CAM_EastYard 13.8 % (34; hall and well). See `near_black_map.png`.
  - The r2 pavilion ceiling is fixed: (52, 29, 19), 0 % near-black.
- **Blown: PASS.** Max 0.06 % of any frame has min channel >= 250 (CAM_HallVeranda: 1 tile, the glow core). The
  shoji glow reads (196, 131, 95).

### Fixes required
1. Timber saturation and hue: every sunlit or lamp-lit timber (gate posts and leaves, taiko stand) is at s 0.70-0.81.
   Shaded dark timber and the deck crush toward black. Bring them to s 0.45-0.60, hue 20-25, and re-measure.
2. Tiles: the gate and wall-cap tiles run R/B 1.2-2.2 in sun and lamp light. The hall roofs are 0.80-0.85, bluer than
   the band (reference 0.88). Bring all of them into 0.90-1.10.
3. Hall plaster under the veranda and eave: s 0.72-0.97, orange-brown. Sunlit kit-1 plaster: s 0.58. Make both read
   cream.
4. Black regions: the gateway ceiling and lintel are pure black, and the shaded hall facade, deck, veranda and well
   timber crush below 12. This needs the toe / fill change the builder measured (probe2) or real fill light. Materials
   alone did not fix it in r3 or f1.

### Notes (not failures of this brief; for the user)
- Spec R4: the hall upper roof is now 30 deg (f1), where R4 and spec 4.4 say 25 deg; the ridge is at +8.906 where the
  spec says +8.3. All walk and climb checks still pass, the route-5 numbers are unchanged, and 30 deg is under the
  44.8 deg walkable limit. It is still a change to a spec number the grey-box proved, so the user should accept it or
  have it reverted.
- `Exports/DojoKit/Ground/SM_DKG_PaverCourse_2x0p42_A..H.fbx` are retired and absent from DojoLab, but they still sit in
  the live export folder, not in `_superseded_r3/`.
- The grey-box stand-ins still read as flat colour: the pavilion post (135, 64, 23) s 0.83, and the yellow tree blocks.


## 2026-09-28 - ROUND 4: ridges + onigawara in the shared roof system (hall + gate + wall cap re-export)

Full notes: `WorkFiles/dojo/build/hall/BUILD_NOTES.md` (ROUND 4). Output: `WorkFiles/dojo/build/round4/ridges/`.
- `roof_kit` 1.3.0: `noshi_tiles` (real noshi courses, the drop-in for every stack), `cap_row` (tile collars),
  `end_tile`, `onigawara` (plain crest), `ridge(courses=, caps=, ends=, top=)` filling the round-3 height,
  `hip_roll(end='disc'|'onigawara')`, `ridge_end_any`; the compound builders default to them.
- Hall: a 4-course ridge + plain onigawara; hips end in disc end tiles; no iron straps. Gate: 4 courses in the old
  0.24 m, onigawara ends, barge ridges ending in disc end tiles. Wall cap: its 3 noshi layers are real tiles.
- Collision identical (UCX vertex delta 0.0 mm on 59 hall + 61 kit-1 hulls); crest and ridge-end heights unchanged;
  QA 0 hard fails (21 + 28 FBX re-exported); walk / climb / roof walk / sightlines PASS; noshi slits 0.


## 2026-09-29 - ROUND 4: COMBINED DOJOLAB IMPORT (outbuildings, corridors, shed, pavilion; ridge-updated hall + kit 1)

User: "start step one. yes keep as is" (the hall clerestory stays; route 5 wins). No DojoLab editor was open at any
step (the runner's guard checked before each one); one Unreal process at a time, each step its own fresh process; no
Unreal process is left running. Lock `DojoKit` (claude, Assets/Dojo/DojoShowcase.blend) refreshed and still held for
the judge / fix steps. The four track locks (DojoOutbuildings, DojoCorridors, DojoShed, DojoPavilion) and their files
were not touched: their layouts and exports are read only. Nothing committed.

Stage folder: `unreal/round4/`:
- `start_backup/`: the showcase + Unreal scripts, every showcase JSON, the Unreal step JSONs and DojoShowcase.blend as
  they were at the start;
- `r4/`: the final captures (28 stills), `SHOWCASE_SHEET_R4.png`, `regions_r4.json` (the round-3 boxes),
  `regions_r4_new.json` (the new close-ups), `regions/` (the boxes drawn), `measure_r4.txt`, `measure_r4_new.txt`;
- `checks/`: the round-4 check scripts and their outputs; `final_json/`: every final step and check JSON;
- `patch_compose_r4.py` (the one-off compose patch, for the record), `make_sheet_r4.py`, `measure_r4_new.py`.

### Commands
```
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py      (204 pieces, 804 instances, 0 warnings)
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/{walk_check,climb_check,roof_walk_check,hall/hall_roof_walk}.py -- --layout showcase/layout_showcase.json --out showcase/<x>_showcase.json [--hover 0.019]
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python Scripts/dojo/outbuildings/ob_roof_walk.py -- --layout showcase/layout_showcase.json --out unreal/round4/checks/ob_roof_walk_showcase.json
blender -b --factory-startup Assets/Dojo/DojoShowcase.blend --python WorkFiles/dojo/build/unreal/round4/checks/{r4_corridor_checks,r4_sp_roof_walk,r4_clearance,r4_ground_holes}.py [-- --asset shed|pavilion]
DJ_CAPTURE_DIR=<abs>/unreal/round4/r4 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify capture
py -3 WorkFiles/dojo/build/unreal/round4/make_sheet_r4.py <abs>/unreal/round4/r4
py -3 WorkFiles/dojo/build/unreal/round3/measure_r3.py <abs>/unreal/round4/r4 r4 ; py -3 WorkFiles/dojo/build/unreal/round4/measure_r4_new.py <abs>/unreal/round4/r4
```
`r4_corridor_checks.py` and `r4_sp_roof_walk.py` are copies of the tracks' `corridors/corridor_checks.py` and
`shed/sp_roof_walk.py` with only the layout path (showcase/layout_showcase.json) and the output path changed, so the
tracks' own scripts stay untouched.

### Composition (compose_showcase.py + the new `Scripts/dojo/showcase/round4.py`)
- **New module `round4.py`** (plain Python): the four kits (FBX folder, Unreal root /Game/DojoKit/{Outbuildings,
  Corridors, Shed, Pavilion}), their layouts read exactly as the tracks wrote them, `replaced_greybox()`, the
  outbuildings track's prop moves, the tracks' new walk routes, the marker fits and the ground fill.
- **Replaced grey-box:** SM_DGB_Storehouse (+ _Roof), _Residence (+ _Roof), _Corridor_W/E (+ _Roof), _Shed (+ _Roof),
  _Pavilion, _Pavilion_Roof, _Landing_PavilionPad and the showcase's SM_DGB_Pavilion_NoDrum (no longer composed).
- **Grey-box kept:** SM_DGB_Tree x2, SM_DGB_Ground_Outside, and the 1v1 gameplay pieces SM_DGB_Boundary_1v1 (hidden in
  game) and SM_DGB_AlleyFence x2 (the spec 4.6 rear-alley fences, 1v1 only; no kit exists for them: FLAGGED).
- **Placed:** outbuildings 43 instances (20 pieces), corridors 20 (14), shed 6 (5), pavilion 8 (5); each kit's own
  Nanite flags (pieces of about 2k tris or more); collision classes as the tracks set them.
- **Materials:** all library instances (shared; round-3 look values unchanged), plus the shed's two recipes from
  layout_shed.json (M_DKS_GalvWeathered on M_DJ_Lib_Opaque, M_DKS_PackedEarth on M_DJ_GroundXY_Master; no new
  textures) and the modern kit's M_DKP_Modern_Concrete for the shed footings. 60 instances, 98 textures.
- **Prop moves** (the outbuildings track's measured proposals, applied here):
  - SM_DKP_Modern_ACUnit_Wall (40.8, 27.94, 1.55) -> (37.0, 28.7, 1.55) rot -90: it covered the residence lattice window;
  - SM_DKP_Modern_JunctionBox Y 27.94 -> 27.90: its back was 4 cm inside the storehouse granite band.
- **Taiko:** unchanged, from layout_taiko.json, on the new pavilion floor (+1.0; only the stand's feet touch the paving,
  contact z 0.99-1.0).
- **Ground fill (measured, then fixed):** the first r4 captures showed white-lilac strips in front of the outbuildings.
  `checks/r4_ground_holes.py` (rays down on a 5 cm grid against every mesh starting below +0.30) found that the ground
  kit's gravel stops at the GREY-BOX footprints:
  - Y 27.5 in front of both outbuildings (their faces are at 27.94);
  - X 7.0-7.5 / 36.5-37.0 between the outbuildings and the corridors;
  - the 0.25 m strips under the corridor decks (Y 29.5-29.75 / 32.25-32.5) and the pockets behind.

  `round4.GROUND_FILL` places 32 of the ground kit's own world-XY gravel panels there (pivot = min corner; they join
  seamlessly). After it: 0 open-air holes at the buildings. What remains is the closed interiors (hall, storehouse,
  residence) and the pre-existing slits at the gate posts (0.1-0.18 m2 each, not touched).
- **Cameras:** the round-3 set (13 CAM_* + 8 CU_*) plus 7 round-4 close-ups, added to `look_r3.CLOSEUPS` so prep keeps
  them: CU_R4_StorehouseFront, CU_R4_ResidenceFront, CU_R4_CorridorOpen, CU_R4_ShedVending, CU_R4_PavilionTaiko,
  CU_R4_RidgeHall, CU_R4_RidgeGate. `look_r3.DF_FIX` drops the grey-box pavilion roof's distance-field fix (that mesh is
  no longer in the layout).

### Traversal markers (24, all kept)
Route 7 and the plinth are re-fitted to the kits' own UCX hulls (`fit_round4_markers`), delta 0.0 mm on every side:

| Marker | Hull | Box |
|---|---|---|
| Shed_FrontBand | SM_DKS_Roof band | X 0-6, Y 4.25-5.0, top +2.5 |
| Landing_PavilionPad | SM_DKV_EavePad | X 37.65-38.4, Y 2.25-3.75, top +3.25 (bottom +1.50 by marker_policy) |
| Pavilion_Plinth | SM_DKV_Plinth | X 39-43, Y 1-5, top +1.0 |

Route 3 has no markers (walk-off drops).

### Checks (final state; GASP capsule r 0.30, 1.72 m, step 0.45) - ALL PASS
- **walk_check:** 31 routes: the showcase's 20 plus the tracks' 11 (corridor floors, the shed along the rack, the north
  stair onto the plinth, the drummer's stance, and their CONTROLs). Every route is clear and all 11 CONTROLs are
  blocked; also at r 0.35.
- **climb_check (hover 0.019):** every route, with the proven numbers unchanged:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4, plus the 0.40 m walk-up |
  | Shed crate -> band | 123.1 -> 122.9 |
  | Pavilion crate -> pad | 122.3 -> 197.9 |
  | Vending | 173.1 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Rack hurdle | 111.8 |

  Route 2 pier -> storehouse eave: rise 0.0. Route 3 drops: 1.224 and 0.513 m.
- **Roof walks:**
  - kit-1 gate: 3 / 3;
  - hall: 16 / 16, 2 CONTROLs blocked;
  - outbuildings (ob_roof_walk): 14 / 14, 5 CONTROLs;
  - corridors: 10 / 10. Route 3 on the real hulls: capsule drops 0.99-1.01 and 0.16 m along Y 30.4;
  - shed: 5 / 5;
  - pavilion: 6 / 6, finial CONTROL blocked.
- **Unreal import:** 93 meshes imported, 107 skipped as unchanged.
  - 49 changed meshes deleted first: the 21 SM_DKH_* hall pieces (ridges) and the 28 SM_DK_* kit-1 pieces.
  - 44 new: SM_DKO / DKC / DKS / DKV.
  - Hulls = UCX count on every new piece. 71 Nanite meshes, every fallback RELATIVE_ERROR 0 (full).
- **Unreal verify (fresh process): 7 / 7 gates.**
  - 204 meshes, 98 textures, 874 actors; 804 mesh actors = 804 layout instances; no grey-box stand-in left.
  - Bounds within 0.0008 cm (non-Nanite, all-LOD) and 0.0005 cm (Nanite fallback geometry).
  - 24 markers at 0.0 cm ledge error; 18 / 18 GASP traces hit their own marker.
  - Sun, sky, sky light, grade and dome unchanged from round 3.

### Clearance (`checks/clearance_r4.json`, render meshes, round-4 kits against every other kit)
Grade contacts (footings, plinth, paving bedded in the gravel) are expected. The real interpenetrations are all at
junctions between tracks; none is fixed here (other chats' assets; for the fix round):
1. **Corridor end walls into the outbuilding gables.** SM_DKC_EndWall_W/E_Base starts at X 7.02 / 36.98, but the
   storehouse / residence gable's proud granite band reaches X 7.075: 5.5 cm in, over z 0-1.0.
   SM_DKC_EndWall_E_Roof also runs into the residence gable's eave-line timber (z 3.09-3.25). The corridor track had
   asked for the gable faces at X <= 7.0.
2. **Kit 1's route-2 step pier** runs into both outbuilding roof slopes (known; flagged by the outbuildings track).
3. **Outbuilding outer gables against the perimeter wall** (X 0 / 44): the wall's footing rubble and cap overhang sit
   inside the 0.25 m gable walls. Hidden; no coplanar face shows.
4. Wall-lamp back plates and the junction box on the outbuilding faces: contact only.

### Measured (sRGB medians; `r4/regions_r4.json` vs round 3 f1 `regions_f1.json`, same boxes)
- **No regression where the scene is unchanged:** 70 / 75 round-3 regions are within 5 sRGB levels (sand, path, gravel,
  wall plaster, lantern, training props, hall roof and ridge).
- **Changed by the new geometry, not the look:**
  - CU_GateFront ridge (82, 77, 87) -> (69, 61, 69): 4 noshi courses + cap row instead of the box;
  - CU_HallUpperRoof diagonal roll (54, 50, 60) -> (55, 54, 71): the new hip roll.
- **REGRESSION, FLAGGED: the pavilion ceiling is black again.**
  - CAM_Drum ceiling (49, 28, 18) -> (8, 2, 1); CU_Taiko ceiling -> (0, 0, 0).
  - Near-black: CAM_Drum 2.7 % -> 19.9 %, CU_Taiko 2.7 % -> 17.2 %.
  - Round 3 fixed it only on the grey-box slab (a flat 0.26 grey actor override). The real roof's TimberDark rafters
    and sarking in shade fall into the tonemapper toe: the same mechanism as the gate ceiling (verifier r3 fix 4).
  - The CU_Taiko lit drum head also dropped, (237, 186, 120) -> (131, 76, 34): the new eave structure shades it from
    the 12 deg sun.
- **New close-ups** (`r4/regions_r4_new.json`):

  | Region | sRGB | Notes |
  |---|---|---|
  | Storehouse plaster, lamp-lit / left of the door | (185, 157, 129) / (155, 134, 111) | s 0.30 / 0.28 |
  | Storehouse granite band | (64, 53, 49) | s 0.23 (the track's studio render: 160) |
  | Storehouse steel door (shade) | (5, 4, 4) | 86 % near-black |
  | Outbuilding roof tiles | (41-46, 36-41, 46-52) | R/B 0.89 (ref 2: 0.88) |
  | Residence plaster, lamp-lit | (174, 134, 98) | s 0.44 |
  | Residence wainscot / wood door (shade) | (15, 9, 7) / (33, 24, 17) | 37 % / 11 % near-black |
  | Residence lattice glow | (209, 159, 126) | hue 24 |
  | Corridor open side: rail / inner plaster | (1, 0, 0) / (18, 5, 1) | rail 86 % near-black; whole frame 55 % |
  | Shed back wall / rack (shade) | (19, 11, 7) / (3, 1, 1) | |
  | Shed packed-earth floor | (51, 34, 29) | s 0.43 |
  | Pavilion roof tiles, sunlit | (144, 114, 93) | R/B 1.55: tan in low sun, as the gate in r3 |
  | Pavilion post, sunlit | (178, 121, 60) | s 0.66 (r3 timber target 0.45-0.60) |
  | Pavilion plinth granite, sunlit | (203, 162, 114) | s 0.44 |
  | Hall ridge noshi / cap / onigawara | (69, 66, 77) / (91, 89, 103) / (84, 79, 87) | R/B 0.90 / 0.88 / 0.97 |
  | Gate ridge noshi / cap / onigawara (sunlit) | (122, 93, 76) / (141, 128, 123) / (139, 111, 95) | R/B 1.61 / 1.15 / 1.46 |

### Captures
`unreal/round4/r4/`: 28 stills (96 frames each, Lumen) and `SHOWCASE_SHEET_R4.png` (with dojo1_reference2). They are
the round-3 set plus CU_R4_StorehouseFront, CU_R4_ResidenceFront, CU_R4_CorridorOpen, CU_R4_ShedVending,
CU_R4_PavilionTaiko, CU_R4_RidgeHall and CU_R4_RidgeGate. Blown pixels: at most 0.2 % of any frame.

### Open (for the judges / fix round)
- **Black shade on the new buildings** (the r3 toe issue, now on more surfaces): the pavilion ceiling, the corridor
  interior (CU_R4_CorridorOpen 55 % near-black: at this sun the corridors stand in the shade of the hall and the
  storehouse), the shed underside and rack, the storehouse steel door, the residence wainscot. This needs the look
  pass's post toe / fill (probe2) or per-kit lifts. Materials and grade stayed at round 3's values, as briefed.
- **Low-sun warmth:** the pavilion roof and the gate ridge read R/B 1.46-1.61, and sunlit pavilion timber s 0.66. These
  are the r3 verifier's open tile / timber items, now also on the pavilion.
- The junction interpenetrations above (corridor end walls vs the gables' proud band; the pier vs the outbuilding roofs).
- SM_DGB_AlleyFence x2 is still grey-box (a 1v1 gameplay fence; there is no kit). The trees stay grey-box, by the brief.
- The ground kit's own layout still stops at the grey-box footprints; the fill lives in `round4.GROUND_FILL`. If the
  ground track re-lays its gravel, drop the fill.
- Deviations carried over from the tracks (theirs, unchanged here): the outbuilding doors on the eave wall, one
  corridor bay, the pavilion stair on the north face, and the R5 headroom exceptions (corridor 2.21 m, shed 2.165 m,
  pavilion 1.745 m).

### Scripts changed (not committed)
- `Scripts/dojo/showcase/compose_showcase.py`: the round-4 kits, NoDrum only while the pavilion is grey-box, the prop
  moves, marker fits, walk routes, ground fill, the shed recipes, and the layout keys (round4 sources, greybox_kept).
- `Scripts/dojo/showcase/round4.py`: new.
- `Scripts/dojo/showcase/look_r3.py`: the ROUND 4 section (7 close-up cameras, the DF_FIX pop).
- `WorkFiles/dojo/build/unreal/round4/*.py` and `checks/*.py`: new.


## 2026-09-29 - ROUND 4 FIX f1: the two Unreal judges' blockers (whole 6.5/10, buildings 6.4/10), Blender assets + Unreal

User: "start step one. yes keep as is" (the hall clerestory stays). No DojoLab editor was open at any step (the
runner's guard); one Unreal process at a time, each step its own fresh process; none left running. Headless Blender
only (no MCP). Locks: DojoKit (showcase) and the track locks (DojoOutbuildings, DojoCorridors, DojoShed, DojoPavilion)
are this workflow's own; a new lock `DojoYard` (claude) for the new corner-post asset. Nothing committed.

- **Folders:** `unreal/round4/f1_work/` (start backups of every script and layout touched, the retired r4 outbuilding
  FBX in `retired_fbx/`, the compose and Unreal run logs, `checks/` = the f1 copies of the r4 check scripts plus
  `run_checks_f1.sh`, `measure_f1.py`); `unreal/round4/f1/` = the final 28 stills, `SHOWCASE_SHEET_R4_f1.png`,
  `regions_f1.json` (the round-3 boxes), `regions_f1_new.json` and `measure_f1_new.txt` (the new-building boxes),
  `json/` (every final step and check JSON).

### Commands
```
blender -b --factory-startup --python Scripts/dojo/outbuildings/build_outbuildings.py        (QA 23 pieces, 0 hard fails, 23 FBX)
blender -b --factory-startup --python Scripts/dojo/corridors/build_corridors.py              (QA 14, 0 hard fails, 14 FBX)
blender -b --factory-startup --python Scripts/dojo/shed/build_shed.py                        (QA 5, 0 hard fails)
blender -b --factory-startup --python Scripts/dojo/pavilion/build_pavilion.py                (QA 5, 0 hard fails)
blender -b --factory-startup --python Scripts/dojo/props/yard/build_yard_posts.py            (QA 1, 0 hard fails; new)
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py              (208 pieces, 796 instances, 0 warnings)
bash WorkFiles/dojo/build/unreal/round4/f1_work/checks/run_checks_f1.sh                      (walk, climb, 6 roof walks, clearance, ground holes)
DJ_CAPTURE_DIR=<abs>/unreal/round4/f1 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify capture
py -3 WorkFiles/dojo/build/unreal/round4/make_sheet_r4.py <abs>/unreal/round4/f1 f1
py -3 WorkFiles/dojo/build/unreal/round3/measure_r3.py <abs>/unreal/round4/f1 f1 ; py -3 WorkFiles/dojo/build/unreal/round4/f1_work/measure_f1.py <abs>/unreal/round4/f1
```
Six Unreal passes in all: run 1 the full import; runs 2-6 the corner posts and the look iterations L2-L5, each
prep to capture, verify 7/7 every time.

### 1. Storehouse + residence GABLE-FRONT (both judges' first blocker)
`Scripts/dojo/outbuildings/build_outbuildings.py` (track notes: `outbuildings/BUILD_NOTES.md`, f1 section).
- The ridge now runs N-S over the roof centre (X 3.3 / 40.7). The roof is the grey-box slab turned 90 deg. It was
  8.6 x 8.6 m with the ridge in the middle, so the footprint (X -1..7.6 / 36.4..45, Y 27.4..36), the pitch
  (24.944 deg), the eave +3.25 and the planes +5.25 hold exactly. The verges with bargeboards and the onigawara now
  face the courtyard, as dojo_outbuildings_ref and both overviews show.
- New pieces:
  - `Store_GableFront`: the door frame, threshold, wide step and vent centred under the apex; the canopy and steel
    leaves sit on it. `Store_GableRear`.
  - `Res_GableFront`: the door bay and lattice-window bay grouped under the apex, the tie beam across over the hoods
    (the sheet's horizontal beam), purlin ends under the rake, the vent, the meter box beside the window.
    `Res_GableRear`.
  - Eave walls `Store_Wall_N/F`, `Res_Wall_N/F`. N = the corridor side (0.6 m eave), F = the perimeter-wall side
    (1.0 m eave); each has its own wall plate (+3.276 / +3.462).
  - `Roof_SlopeNear_Store/_Res` (the near slope with the corridor notch), `Gutter_S/N/F`.
  - Downpipes stand at the front gable corners on the near eave wall (the sheet's corner pipes).
  - 10 r4 pieces retired: the level step's retired list deletes them from DojoLab; their FBX moved to
    `f1_work/retired_fbx/`.
- The apex sits 0.2 m off the body centre, because the roof over the perimeter wall has a 1.0 m eave there and a
  0.6 m eave on the corridor side. Door, hood and vent are centred under the apex.
- **Corridor junction, re-seated on the eave walls (ref 1).** The corridor roof now runs INTO the outbuilding's near
  slope: a lower gable meeting a main slope, the chidori-hafu case.
  - Corridor side: the end roof strip starts at X 6.0; inside the wall line only what stands above the outbuilding
    slope is kept. Iron valley flashings on the two valleys; a plaster infill over the outbuilding's plate under the
    corridor ridge.
  - Outbuilding side: the near slope keeps everything above the corridor's two planes (the notch).
  - Each roof overlaps the other by 6 cm under the valley.
  - The corridor floor and roof now start 4.5 cm off the eave wall (clear of the 4 cm granite band: the r4 clash);
    the closed wall butts the plaster.
- **Props on the old south faces:** the wall lamps stay (6.6 / 37.4 on the front gables). The junction box moves
  X 2.2 -> 1.2 (clear of the new door frame). The wall AC moves Y 28.7 -> 28.75 (clear of the front gable's corner
  post). Both go through the outbuildings' proposed moves; the modern kit's layout is unchanged.
- **Routes.** The layout-number entries are updated in `round4.apply_climb_f1`; the real walks were re-run on the
  hulls.
  - Route 2: pier +3.25 -> north onto the FAR slope, a 0.233 m step (was 0.0 onto the E-W eave; under the 0.45 m
    step), then up and over the ridge box (max rise 0.352 per 2 cm) and down the near slope.
  - Route 3: the near slope -> the corridor roof that runs into it, a 0.109 m step down (was a 1.224 m walk-off
    drop; spec 4.5 calls it "walk (small step down)"), then the unchanged 0.513 m drop onto the hall's lower roof.
  - The grey-box 1v1 blockers (outbuilding Y 31.7, corridor Y 31.0) still close the north halves.
  - **FLAGGED for the user:** the spec's "ridge along X" (4.5) was the grey-box's choice. The sheets and both judges
    want gable-front. Route 3's walk-off drop is now a walk.

### 2. Corridors (`Scripts/dojo/corridors/build_corridors.py`)
- The junction above.
- The lattice rail goes from 13 x 4 to 18 x 5 near-square cells (0.14 x 0.106 m) with even 24 mm bars.
- The hall-end onigawara is about half size: 0.46 x 0.52 x 0.26 -> 0.30 x 0.34 x 0.20.

### 3. Training shed (`Scripts/dojo/shed/build_shed.py`, `sp_common.py`)
- The r4 board wall already ran the full width (X 0.28-5.72) along the south wall. CU_R4_ShedVending looked along it
  edge-on from (18.5, 4.5), so both judges read it as a third of the width. The close-up now stands in front of the
  shed, (12, 12, 2.0) -> (6.2, 1.8, 1.3): full-width boards, rack, both footings, the vending machine at the edge.
- Corrugation 76 mm / 18 mm -> 120 mm / 30 mm (it reads at 15-20 m).
- Heavier knee braces (60-70 mm angles).
- The rack widened 3.4 -> 3.7 m (two-thirds of the bay).
- The galvanised tint lifted (0.44 -> 0.60 grey).

### 4. Drum pavilion (`Scripts/dojo/pavilion/build_pavilion.py`)
- Hip rolls slimmer and the hip end tiles smaller: roll r 0.085 -> 0.068, end r 0.115 -> 0.08, courses 0.30 -> 0.27 m.
- The knee braces stay. dojo_drum_pavilion_ref shows them in both elevations (short struts from the posts to the tie
  beam); the whole judge's "invented" call is wrong on that point.
- North stair kept (route 7 and the plinth mantle use the west face).

### 5. Sand-field corner posts (whole delta 9): new asset `SM_DKP_Yard_CornerPost`
- `Scripts/dojo/props/yard/build_yard_posts.py`: a 0.18 m square dark timber post, +0.60, pyramid top, granite
  collar.
- At the four OUTER field corners (X 8 / 36, Y 2 / 19, 0.13 m outside), as dojo1_reference1 / 2 show. The path-side
  corners have none in either reference.
- Its own kit in `round4.KITS` ("yard", /Game/DojoKit/Props/Yard). Thin class.

### 6. Look (instance and grade values only; `look_r3.py`, section "ROUND 4 FIX f1" plus L2-L5)
| Set | f1 value | Measured (sRGB medians) |
|---|---|---|
| Grade | film toe 0.55 -> 0.35 (round 3's probe2 fix, now applied) | near-black: CAM_Establishing 26 % -> 2 %, CAM_HallVeranda 20 -> 5 %, CU_R4_ResidenceFront 16 -> 9 %, CU_R4_CorridorOpen 55 -> 39 %, CU_R4_StorehouseFront 15 -> 7 % |
| Timber (Dark / Aged, + End) | VM 1.8 -> 3.4, Sat 0.6, Tint (1.0, 0.9, 0.76) | veranda deck (55, 38, 31) (r3 f1 (25, 17, 13); ref 2 (70, 44, 29)); veranda post (76, 53, 43); residence door (66, 46, 36) |
| Roof tile + ridge parts | VM 2.3 -> 1.45, Flatten 0.55 -> 0.75, Tint (0.8, 0.94, 1.18) | gate tiles (34, 33, 44) R/B 0.77; gate noshi in sun (122, 93, 76) -> (79, 59, 49) |
| Granite | Sat 0.55 -> 0.25, cooler tint | store band (53, 47, 48) s 0.11 |
| Store door, M_DKO_SteelGrey (new instance, the kit's own recipe) | the library Iron on the door's clean UV band, 75 % to mid steel grey | (50, 45, 48) in the hood's shade (r4 (5, 4, 4), 86 % near-black); seam, pulls and hinges read |
| Taiko lacquer | darker oxblood mean, Sat 0.6 | (86, 26, 7) (r4 (121, 27, 14)) |
| Taiko sticks | new flat M_DJS_StickPale (0.40, 0.26, 0.15) | plain light-brown bachi, no bark stripes |
| Training props | M_DJS_TimberMid warmer: Tint (1, 0.9, 0.76), Sat 0.62 | warm brown |
| Sand / gravel | sand Sat 0.85 -> 0.62; gravel VM 1.05 -> 1.22, warmer | paler cream sand |
| GlassAmber | EmissiveTint (1, 0.86, 0.55) | glow (190, 101, 64) hue 18: still salmon (open) |
- Cameras: CAM_Establishing moved from under the gate roof (22, -1.6, 2.85) to the threshold (22, 0.25, 2.3); the
  whole hall roof and clerestory are now in frame. CU_R4_ShedVending as above.

### Checks (final state; GASP capsule r 0.30, 1.72 m, step 0.45) - ALL PASS
- **QA:** 23 + 14 + 5 + 5 + 1 pieces, 0 hard fails, a UCX on every SM_; all exported through Scripts/pipeline.
- **walk_check:** 31 routes clear, every CONTROL blocked; also at r 0.35.
- **climb_check (hover 0.019):** every route. Heights unchanged:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4, plus the 0.40 m walk-up |
  | Shed crate -> band | 123.1 -> 122.9 |
  | Pavilion crate -> pad | 122.3 -> 197.9 |
  | Vending | 173.1 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Rack hurdle | 111.8 |

  Route 2 step 0.233 m; route 3 -0.109 / -0.513 m (above).
- **Roof walks:**
  - kit-1 gate: PASS; hall: PASS;
  - ob_roof_walk, rewritten for gable-front: PASS. It covers routes 2 and 3 on both sides, the BR line Y 31, along
    both eaves, over the ridge; controls: the 1v1 blocker, the wall top under the roof, both doors.
  - corridors: PASS, route 3 both ways. The r4 "back up onto the outbuilding roof" control is now a walk; it is
    replaced by the 1v1 corridor-ridge controls.
  - shed: PASS; pavilion: PASS.
- **Clearance** (`json/clearance_r4.json`, 48 contacts): all at intended joints (valley overlaps, walls butting the
  band, the outbuildings built into the perimeter wall, the corner posts in the gravel). Kit 1's route-2 pier cap
  (visual to Y 27.563, +3.487) still meets the far slope's front verge corner, as it met the r4 eave: kit 1's item.
- **Ground holes:** no open-air hole; only the closed interiors and the pre-existing gate-post slits.
- **Unreal verify (fresh process): 7 / 7 gates.**
  - 208 meshes, 98 textures, 866 actors; 796 mesh actors = the layout.
  - 76 Nanite meshes, every fallback full.
  - Bounds within 0.0008 cm.
  - 24 markers at 0.0 cm ledge error; every GASP trace hits its own marker.
  - Blown pixels: at most 0.03 % of any frame.

### Captures
`unreal/round4/f1/`: 28 stills (the r4 set; CAM_Establishing and CU_R4_ShedVending re-framed) and
`SHOWCASE_SHEET_R4_f1.png`.

### Open (for the verifier / judge)
- CU_R4_CorridorOpen is still 39 % near-black: the west corridor stands in the hall's and storehouse's shade at this
  sun, and the rail reads (12, 4, 3). It needs the look pass's fill light.
- Low-sun warmth on sunlit faces: pavilion tiles (101, 73, 55) R/B 1.84; sunlit pavilion posts (208, 140, 80)
  s 0.62; plinth granite in sun (181, 137, 96). This is the 5000 K / 12 deg sun: the look pass's call.
- The shoji / lattice glow is still salmon (hue 18; the EmissiveTint barely moves it). The taiko lacquer still reads
  red in direct sun.
- Not done (other kits or gameplay): hall shoji kumiko density, hall AC size (route 5 needs the stand), gravel grain
  size, slab-path stagger, wall panel seams and footing moss, lantern granite, the dummy's log body.
- SM_DGB_AlleyFence x2 and the trees are still grey-box (as briefed).

### Scripts changed (not committed)
- `Scripts/dojo/outbuildings/build_outbuildings.py`, `ob_roof_walk.py`
- `Scripts/dojo/corridors/build_corridors.py`
- `Scripts/dojo/shed/build_shed.py`, `sp_common.py`
- `Scripts/dojo/pavilion/build_pavilion.py`
- `Scripts/dojo/props/yard/build_yard_posts.py` (new)
- `Scripts/dojo/showcase/look_r3.py`, `round4.py`, `compose_showcase.py`
- `WorkFiles/dojo/build/unreal/round4/f1_work/` (checks, measure)


## 2026-09-29 - INDEPENDENT VERIFIER, ROUND 4 (after fix f1) - RESULT: FAIL (black captures + visible grey-box alley fences; everything structural passes)

Read-only. Nothing in DojoLab was saved and no builder file was touched. Every output is in `verify_r4/`. No DojoLab
editor was open; two fresh commandlets ran one at a time (verify 53 s, ledges 17 s) and none is left running. My truth
sources are my own re-import of all 208 layout FBX (`fbx_audit.json`), my own scene built from those FBX placed by the
layout matrices (`v4_measure.py`, `v4_roof_crest.py`; not the builder's composed blend), and the layout matrices.

### Scripts and outputs (verify_r4/)
- `v4_fbx_audit.py` -> `fbx_audit.json`
- `v4_ue_verify.py` + `run_v4_ue.sh` -> `ue_verify.json`: r3's gates, plus gate 10 (grey-box left), 11 (collision
  profiles of the new buildings) and 12 (taiko / pavilion fallback geometry)
- `v4_ue_ledges.py` + `run_v4_ledges.sh` -> `ue_ledges.json`
- `run_v4_blender_checks.sh`: walk / climb (hover 0.019) / gate roof / hall roof / outbuilding roof walks on
  DojoShowcase.blend, plus `v4_corridor_checks.py` and `v4_sp_roof_walk.py` (f1 copies, output path only)
- `v4_measure.py` -> `measure_buildings.json`: sizes, taiko, ridge sections, track layouts vs the showcase
- `v4_roof_crest.py` -> `roof_crest.json`
- `v4_capture_health.py` -> `capture_health.json`, `near_black/<cam>.png` (red = max channel < 12)

### Results
| Check | Result | Numbers |
|---|---|---|
| L_Dojo default + GASP CMC pawn | PASS | EditorStartupMap, GameDefaultMap = L_Dojo; GM_Dojo_C (ini + world override); pawn SandboxCharacter_CMC_C |
| Meshes | PASS | 208 / 208 in UE 5.8.3. Convex hulls = FBX UCX on every piece (394), with no other simple shapes. LODs, LOD0 tris and slots match. No SM_ without UCX. 76 Nanite, every fallback full. 0 engine-default or missing materials |
| Level | PASS | 796 / 796 layout instances, one actor each (0 missing / duplicate / extra / wrong mesh). Location, rotation, scale and collision errors all 0. Bounds, worst: 0.0005 cm (non-Nanite) and 0.0005 cm (Nanite fallback geometry). The track layouts (outbuildings 31, corridors 20, shed 6, pavilion 8, yard 4, taiko 4) match the showcase instances exactly |
| Grey-box left | **FAIL** | Trees x2 and Ground_Outside (allowed); Boundary_1v1 (hidden in game). **SM_DGB_AlleyFence x2 (X 10.5-13 / 31-33.5, Y 34, 2.0 m, class building) is visible.** It shows in CU_R4_CorridorOpen as a flat (3, 1, 0) slab behind the hall veranda |
| Markers + GASP trace | PASS | 24 / 24 markers, ledge error 0.0 cm. Every ledge a route climbs is a real surface: Shed_FrontBand N 22 / 22, Landing_PavilionPad W 4 / 4, Pavilion_Plinth W 14 / 14, crates 2 / 2. Route 3 is walks / drops, so it has no marker. 18 / 18 GASP traces hit their own marker. Hall_Veranda's centre probe reads "1/5": the same probe artefact as r3 (it starts inside the frame hulls); its used W ledge is 42 / 46 |
| Walk / climb / roof walk | PASS | UE: 20 / 20 routes clear, 11 / 11 CONTROLs blocked. Blender: walk 31 routes + 11 CONTROLs (also at r 0.35). Climb heights unchanged: wall 198.1 / 193.7, pier 123.1, cistern 122.3, pad 172.9, AC 197.4, shed crate -> band 123.1 -> 122.9, pavilion crate -> pad 122.3 -> 197.9, vending 173.1, plinth 98.1, veranda 48.1, hurdle 111.8. Spec-as-written 4 / 5 fail by design. Roof walks: gate 3 / 3, hall 14 + 2 CONTROLs, outbuildings 10 + 5, corridors 10 + 2, shed 5 (no control of its own), pavilion 5 + 1 |
| Sizes vs spec | PASS | See below |
| Taiko | PASS | Stand feet on the plinth surface (gap -0.1 to +2.7 mm). Drum top +2.85, under the +3.25 eave; the first structure above it is at +3.26. Inside the plinth |
| Ridges | PASS | Section lips: hall 4 noshi + cap; gate 4 + cap; outbuildings 3 + cap; corridor 2 + cap. Onigawara stand 0.22-0.26 m above the cap. Close-ups show plain rings and bosses: no faces, creatures or text |
| Captures: black | **FAIL** | See below |
| Captures: missing / blown | PASS | No missing mesh or checker tiles. Blown at most 0.035 % of any frame; 0 blown tiles |

### Sizes (collision exact; render tile crest 1-4 cm under it)
- **Outbuildings:**
  - roof X -1.08..7.68 (8.76; 7.68 inside the wall line) x Y 27.32..36.08 (8.76); residence mirrored;
  - body 7.06 x 8.07;
  - collision eave 3.25, planes meet 5.25 (pitch 24.94 deg); cap top 5.556; onigawara top 5.772.
- **Corridors:** floor top 0.50; collision eave 3.00 at Y 29.5 / 32.5; planes 3.70; cap 3.92-3.94.
- **Shed:** X -0.02..6.02, Y -0.01..5.2; roof 3.00 at the wall to 2.50 on the front band (render and collision).
- **Pavilion:**
  - plinth X 38.99..43.01, Y 0.99..5.0 (north stair to 6.2), top 1.00 (render 0.997);
  - collision eave 3.25 and apex 4.50; finial top 5.09;
  - render roof box 38.27..43.73 (the hip end tiles stand 0.13 m past 38.4 / 43.6).
- Tile crest vs collision (`roof_crest.json`): outbuildings -1.8 to -3.3 cm, corridors -2.9, pavilion -1.2 (the hall
  -0.8 and gate -4.1 for comparison).

### Captures (`capture_health.json`; near-black = max channel < 12)
- **CU_R4_CorridorOpen: 39.3 % near-black, 19.5 % pure black (<= 2), 329 of 1980 tiles black.**
  - Corridor soffit (1, 0, 0); rail (13, 5, 3); inner plaster (25, 11, 3).
  - The alley fence (3, 1, 0) and the hall veranda interior are black too.
- **CU_Taiko: 14.9 % near-black (163 tiles); CAM_Drum: 14.7 % (126 tiles).** The pavilion ceiling / rafters and the top
  of the drum are pure black (the r4 regression, not fixed by the f1 toe change).
- Everything else is at most 11 % (CAM_HallRoofClimb, 15 tiles); CU_Lantern has 27 tiles, CU_R4_ResidenceFront 21 and
  CU_R4_StorehouseFront 17 (small door / soffit pockets).

### Fixes required
1. The black shade on the new buildings:
   - the corridor interior and soffit;
   - the pavilion ceiling and rafters, and the top of the drum (CAM_Drum / CU_Taiko).

   Lift them above near-black (fill light, or per-kit shade lift / AO), then re-measure: no 32 px tile > 90 % near-black
   outside deliberate door gaps.
2. SM_DGB_AlleyFence x2 is visible grey-box geometry, and the brief allows only trees and outside ground. Give it a kit
   piece (for example a board fence from the corridor / shed kits), or hide it in game like the 1v1 boundary if the
   user agrees.

### Notes (not failures; for the user)
- Grey-box climb numbers changed by the gable-front turn (both routes still pass and are easier):
  - route 2: pier -> eave rise 0.0 -> a 0.233 m step;
  - route 3: first drop 1.224 m -> a 0.109 m step down (spec 4.5 says "walk (small step down)"); the 0.513 m drop is
    unchanged.

  The spec's "ridge along X" is now N-S. The builder flagged this; the user should accept it.
- `Exports/DojoKit/Ground/SM_DKG_PaverCourse_2x0p42_A..H.fbx` are still in the live export folder, though retired from
  DojoLab (carried over from r3).
- The shed roof walk has no CONTROL of its own. The same script's pavilion control (the finial) is blocked.


## 2026-09-29 - ROUND 5: the round-4 open asset fixes (Blender only; the fixes track of `dojo-round5-look`)

Full notes: `WorkFiles/dojo/build/round5/fixes/BUILD_NOTES.md`. No vegetation (user). Headless Blender only; no Unreal,
no git.
- **Shed:**
  - measured: the board wall was already full width; the "1/3" reading is the SW corner's west wall under the open
    side;
  - 0.20 m timber wall piers;
  - rack 3.7 -> 4.2 m between the framed end panels (the sheet's 3/4 view);
  - 150 / 42 mm corrugation;
  - timber purlins 65 x 63;
  - 80 mm rear steel braces from the piers.

  Collision identical except the rack's own box.
- **Residence ridge:** the slot is correct (M_DJ_RoofTile, the same mesh as the charcoal storehouse ridge). The tan
  is direct 12 deg sun on the only sun-facing ridge face: a lighting-pass item, no asset change.
- **Kit 1 route-2 step pier:**
  - the cap now closes 2.5 cm short of the outbuilding verge (it overhung into it by 0.12-0.16 m);
  - clearance 48 -> 46, both pier clashes gone;
  - route 2 unchanged (123.1 cm, +0.233 m).
- **Hall shoji:**
  - 7 x 9 cells with 36 mm muntins (sheet; were 6 x 11 / 20 mm);
  - a new named library variant M_DJ_ShojiPaper (unit UV per cell, honey amber, bright cores). Blender bright cells
    (254, 215, 183) -> (216, 164, 111), hue 30.
- **Wall plaster:** the regular V-groove panel seams removed (`PANEL_SEAMS = False`).
- **Dummies:** the round body's mirrored-ramp UV (the crease that read as a square post) replaced by a true-scale
  wrap, with the seam at the back.
- **Retired paver FBX:** moved out of `Exports/DojoKit/Ground` (to `round5/fixes/retired_fbx/`).
- **Checks** on the track's own composed scene: all PASS, numbers unchanged.
  - QA 0 hard fails.
  - FBX audit: collision identical except the rack.
  - walk 20 + 11 CONTROLs (also r 0.35).
  - climb unchanged.
  - Every roof walk passes, with a new shed CONTROL.


## 2026-09-29 - ROUND 5: DOJOLAB IMPORT + LIGHTING / COLOUR PASS + DECALS + PERFORMANCE + CAPTURES (no vegetation)

User: "start with everything else and leave the vegetation for later". The trees stay grey-box stand-ins, and no plant
or grass packs were used. No DojoLab editor was open at any step (the runner's guard ran before each one). One Unreal
process ran at a time, and none is left running. Headless Blender only, with no MCP. Nothing was committed.

Locks: `DojoKit` (claude, DojoShowcase.blend) refreshed and still held for the judges / fix round. The track locks
(DojoDressing, DojoOutside, and the fixes track's) and those tracks' files were only read. The one exception is the
outside track's `round5_outside.py`, which is read by design. The armory emblem files were read, never written.

Stage folder: `unreal/round5/`:
- `start_backup/`: every showcase and Unreal script, every showcase and Unreal step JSON, DojoShowcase.blend and the r3
  cloud texture, as they were at the start.
- `it1/`, `it2/`, `it3/`: full-pass iterations.
- `probe_a/` .. `probe_o/`: colour-probe variants (spec.json + stills).
- `r5/`: the FINAL 35 stills and `SHOWCASE_SHEET_R5.png`. Also `regions_r5_r5.json` + `regions_r5/` (the boxes
  drawn), `measure_r5.txt`, `health_r5.txt` + `near_black/`, `regions_r5_r3boxes.json` (the round-3 boxes) and
  `glow_cores_r5.json`.
- `json/`: the final import, materials, level, verify, perf, capture and compose JSONs, plus
  `perf_game_frametime.json`.
- `checks/`: `run_checks_r5sc.sh` + `r5sc_runcheck.py` and `json/` (all Blender check outputs).
- `work/`: logs, the compose logs and the CSV profiles.
- Scripts: `measure_r5.py`, `health_r5.py`, `make_sheet_r5.py`, `grid.py` / `summ.py` (scratch helpers).

### Commands
```
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py        (239 pieces, 1125 instances, 101 decals, 1 expected warning)
bash WorkFiles/dojo/build/unreal/round5/checks/run_checks_r5sc.sh                        (walk, climb, 6 roof walks, clearance, ground holes)
py -3 Scripts/dojo/showcase/make_sky_clouds.py                                           (r5 cloud layer)
DJ_CAPTURE_DIR=<abs>/unreal/round5/r5 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify perf capture
DJ_PROBE_SPEC=<spec> DJ_PROBE_OUT=<dir> DJ_NO_CARDS=1 powershell -File Scripts/dojo/unreal/run_sc_capture.ps1 -Script dj_sc_colour_probe.py -LogName <x>
powershell -File Scripts/dojo/unreal/run_game_perf.ps1 -Frames 900                       (GPU frame-time sample, -game offscreen)
py -3 WorkFiles/dojo/build/unreal/round5/{measure_r5,health_r5,make_sheet_r5}.py <abs>/unreal/round5/r5
```

### 1. Import and composition (`Scripts/dojo/showcase/round5.py`, new; `compose_showcase.py` hookup)
- **Dressing** (`/Game/DojoKit/Dressing`):
  - SM_DKD_EmblemPlaque_Hall on both hall upper gables, W (14.545, 29, 7.93) and E (29.455, 29, 7.93).
  - SM_DKD_EmblemPlaque_Gate on the gate's street-side eave beam (22, -1.945, 2.975).
  - M_DKD_EmblemPlaque on M_DJ_Lib_Opaque with T_DKD_Emblem_* (the user's armory emblem, byte-identical copies).
- **Outside** (`/Game/DojoKit/Outside`): 31 SM_DKX_* pieces, 289 instances.
  - They replace SM_DGB_Ground_Outside and SM_DGB_AlleyFence x2. The alley-fence hulls equal the grey-box's, so the
    1v1 rear alley stays closed.
  - New T_DKX_ texture home; 8 M_DKX_* instances on the existing masters.
- **Street furniture moved outside:** all 37 showcase rows of the 8 modern street pieces were dropped and the outside
  track's 77 rows placed.
  - Street lamps B (14, -8.55) and A (30, -8.55) stand on the terrace-edge strip.
  - 8 poles run every 25 m on Y -8.55, with 56 conductors, 7 telecom spans, the transformer and 2 guys.
  - The gatehouse drop is re-aimed; its end point is unchanged.
  - `check_no_invented_lamps`: 0 short lanterns; both street lamps outside (Y -8.55). No short lanterns at the gate.
- **Re-imported:** everything the fixes track changed (shed, kit 1, hall, training) plus the new kits. 94 meshes
  imported, the rest skipped by hash. New library variant M_DJ_ShojiPaper. 237 meshes and 134 textures in all.
- **Routes:** the outside track's 6 BR street walks, 4 alley-fence CONTROLs and 5 outside wall climbs (route O) were
  merged into the showcase layout.
- **Totals:** L_Dojo has 1303 actors (1125 mesh actors = the layout, the sky dome, 101 decals, 24 markers, 10 lamps,
  35 cameras). Trees x2 and the hidden 1v1 boundary are the only grey-box left.

### 2. Decals (M_DKD_Decal_Master, `dj_sc_materials.build_decal`; `dj_sc_level.place_decals`)
- The master is a deferred decal, translucent (DBuffer colour + normal + roughness):
  - BaseColor = BC x Tint, then the round-3 look (Saturation, ValueMult);
  - Normal = lerp(flat, N, NormalStrength);
  - Roughness = ORM.g x RoughMult; Metallic 0; Specular 0.5;
  - Opacity = saturate(M.r x Opacity).
- 6 instances; 101 DecalActors (DKD_<id>, folder Dojo/Dressing/Decals).
- **Decal texture axes, MEASURED (the dressing track's two open conventions):**
  - UE 5.8 puts the texture's U along the decal's local Z and V along local Y, with the image top at -Y.
  - With decals.json's rotators (image on Y/Z), the 4 x 0.85 m moss strip came out as horizontal smears (it1). The
    first corrected frame put the moss at the top of its box (it2).
  - `round5.ue_decal()` now builds each frame from the ray-cast centre, normal, up and right: X = -normal, Z = right,
    -Y = up; flip_u = scale Z -1; mirror = scale Y -1.
  - DecalSize = HALF extents (depth, height, width), confirmed.
  - r5 CU_R5_MossWallFoot: the moss cushions sit at the rubble foot.
- `decals.json`'s original rotators are kept per decal as `ue_track`.
- **Not done (FLAGGED):** bReceivesDecals off on the player character. That means editing DojoLab's copy of the GASP
  character or a child blueprint plus the gameplay gate (pawn class). A player standing against a wall foot will pick
  up moss or grime inside a decal box (depth 0.4 m, centred on the surface). User's call.

### 3. Lighting and colour (look_r3.py "ROUND 5"; every value is a light, GI, tone-curve or material-instance setting, with no grade)
**Diagnosis (colour probes on the saved level):**
- Lumen GI is live in the SceneCapture stills: turning off the LumenGlobalIllumination show flag gives unoccluded sky
  light.
- Its bounce under the deep roofs at a 12 deg sun was almost nil, so every shaded underside sat on the sky's occlusion
  alone.
- No measurable effect from: Lumen final-gather / scene quality 4, hardware RT with hit lighting, the sky light's
  lower hemisphere, and longer warm-ups.
- What moved the shade: the sky light, the sun's GI contribution and the tone curve.

| Setting | Round 4 | Round 5 |
|---|---|---|
| Sun temperature | 5000 K | **7000 K** (the atmosphere reddens a 12 deg sun; 5000 K double-warmed the tiles and plaster) |
| Sun indirect_lighting_intensity (its Lumen bounce) | 1 | **4** |
| Sky light (real-time capture) | 4.5 | **7.5** |
| SkyAtmosphere luminance factor | (3.4, 2.6, 2.5) | **(4.2, 2.8, 2.1)** (ref 2's warm upper sky) |
| Local exposure shadow contrast | 1 | **0.5** |
| Film toe | 0.35 | **0.28** |
| Lumen final gather / scene lighting / scene detail | default | 2 / 2 / 2 |
| Height fog | 0.02 / falloff 0.12 | **0.012 / 0.2** (ridges read) |
| Timber (Dark / Aged + End) | VM 3.4, Sat 0.6, Tint (1, 0.9, 0.76) | VM 3.0, Sat 0.75, Tint (1, 0.82, 0.66), **AOStrength 0.25** (the baked grain AO crushed shade to black) |
| Roof tile | Tint (0.8, 0.94, 1.18), RoughMult 1.25 | Tint (0.72, 0.92, 1.26), **RoughMult 2.0** |
| Sand | Sat 0.62, VM 0.95 | Sat 1.0, VM 0.92, Tint (1, 0.92, 0.84) |
| Plaster cream | VM 1.35, Sat 0.78 | VM 1.05, Sat 0.45, Tint (1, 0.95, 0.95) |
| ShojiPaper / GlassAmber | EI 75 / 65, tint 1 / (1, 0.86, 0.55) | EI 65 / 70, EmissiveTint (1, 0.7, 0.4), GlassAmber Sat 1.0 |

**Sky:**
- The painted cloud layer (make_sky_clouds.py "r5_shading") gets a soft alpha ramp, mean-preserving billow shading,
  sun-lit undersides and a +-1 LSB triangular dither.
- The texture is imported uncompressed (TC_VectorDisplacementmap, `ENV sky_texture`).
- The posterised flat cloud plates were the texture's saturated alpha + one flat colour per cloud, not BC compression:
  uncompressed alone measured no change.

**Verify gate 6** now also reads back every one of these extra values (`gate_env_extras`).

### 4. Measured (sRGB medians; it1 = the round-4 look on the round-5 scene; r5 = final; `measure_r5.py` boxes)
**Shade (32 px tiles > 90 % near-black, `health_r5.py`):**

| Region | it1 | r5 |
|---|---|---|
| Gate ceiling | (27, 5, 1), 13.5 % near-black | (40, 11, 2), 2.0 % |
| Pavilion ceiling | (1, 0, 0), 86 % | (15, 3, 1), 43 % |
| Drum top | (2, 0, 0), 95 % | (23, 3, 2), 3 % |
| Veranda soffit | (32, 12, 4), 16 % | (51, 27, 14), 3.7 % |
| West corridor, whole image | 39.8 % near-black, 331 black tiles | 16.6 %, 55 |
| West corridor rail | (12, 5, 3) | (29, 17, 13) |
| Alley fence, whole image | 60 %, 806 black tiles | 22 %, 43 |
| CAM_Drum black tiles | 136 | 8 |
| CU_Taiko black tiles | 171 | 13 |

Every other camera has at most 17 black tiles. What stays under 12 are the grain grooves of dark timber in deep
shade; the boards and posts read.

**Low sun** (targets from the brief / reference 2):

| Region | it1 | r5 | Target |
|---|---|---|---|
| Sunlit timber (drum post) | (198, 126, 68) h 27 s 0.66 | (192, 129, 87) h 24.0 s 0.55 | h 20-25, s 0.5-0.6 |
| Sunlit timber (pavilion post) | (208, 139, 79) h 28 s 0.62 | (201, 142, 98) h 25.6 s 0.51 | h 20-25, s 0.5-0.6 |
| Sunlit pavilion tiles | (100, 71, 53) R/B 1.90 | (105, 91, 90) R/B 1.17 | R/B <= 1.2 |
| Sunlit gate noshi / onigawara | R/B 1.65 / 1.52 | R/B 1.04 / 1.04 | R/B <= 1.2 |
| Residence plaster | (201, 139, 90) s 0.55 | (184, 143, 121) s 0.34 | ref 2 (155, 124, 112) s 0.28 |
| Storehouse gable plaster | (118, 92, 74) s 0.37 | (136, 117, 108) s 0.21 | ref 2 (155, 124, 112) s 0.28 |
| Perimeter plaster in sun | (217, 147, 73) s 0.66 | (207, 159, 108) s 0.48 | warm cream |
| Sand | (186, 160, 140) s 0.25 | (201, 176, 152) s 0.24 | ref 2 (192, 154, 128) s 0.33 |
| Glow cores: shoji bays | h 42 s 0.51 (yellow-white) | h 36-38 s 0.77-0.81 | warm amber, cores only clipping |
| Glow cores: lantern | h 32 | h 31.5, s 0.79 | as above |
| Glow cores: residence / gate lamp glass | s 0.29-0.30 | s 0.67-0.75 | as above |

Clipping is at most 0.1 % of the shoji bays, 4-5 % of the lamp and lantern boxes, and 13 % of the residence lattice
window box (its cores).

**Sky and haze:**
- Cloud plateaus (5 px median, flat runs >= 6 px): CAM_EstablishingRef2 44.5 % -> 19.9 % of the pixels, grey levels
  36 -> 92; CU_R5_FarBackground 46 % -> 25 %.
- Clouds (175, 140, 133) against ref 2's top (192, 149, 142).
- Mountain ridges (92-94, 86-88, 96-98) -> (56-62, 57-64, 71-79); ref 2 (60, 66, 84).

**Round-3 boxes** (`regions_r5_r3boxes.json`): 1 / 75 within 5 levels of r4 f1. The whole look moved on purpose:
- shade +20-30 levels;
- tiles slate-blue (50-60, 48-66, 56-89);
- the shoji now amber cells behind the 7 x 9 kumiko (the r3 box now lands on muntins).

### 5. Checks (GASP capsule r 0.30, 1.72 m, step 0.45) - ALL PASS; re-run on the final compose
- **walk_check:** 41 routes. The showcase's 31, 6 BR street routes clear, 4 alley-fence CONTROLs blocked. Also PASS at
  r 0.35.
- **climb_check (hover 0.019):** every route, numbers unchanged:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 (+0.233 step) |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4 + 0.40 |
  | Shed crate -> band | 123.1 -> 122.9 |
  | Pavilion crate -> pad | 122.3 -> 197.9 |
  | Vending | 173.1 + 0.25 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Hurdle | 111.8 |

  Route 3: -0.109 / -0.513. New outside wall climbs (BR) 197.8-198.7.
- **Roof walks:** gate, hall, outbuildings, corridors, shed (with the fixes track's new CONTROL) and pavilion: all PASS.
- **Clearance:** 46 contacts, all intended (the fixes track's figure). **Ground holes:** identical to round 4 (closed
  interiors and the gate-post slits only).
- **Unreal verify (fresh process): 8 / 8 gates.**
  - Meshes 237, textures 134.
  - Level: 1125 / 1125 actors. Bounds within 0.0014 cm non-Nanite and 0.024 cm on Nanite geometry (the km-scale
    far meshes).
  - 24 markers at 0.0 cm; the GASP trace hits its own marker 23 / 23 (the 5 outside climbs included).
  - Environment, including the new extras.
  - **New gate 8, decals:** 101 / 101 DecalActors with the right instance and master; location 0.0 cm; size exact;
    axes within 1e-4.

### 6. Performance (`dj_sc_perf.py`, read-only commandlet; `run_game_perf.ps1`)
- **Actors:** 1303 in all (1126 static mesh, 101 decals, 24 traversal blocks, 10 point lights, 35 cameras, 7 others).
- **Meshes:** 214 unique meshes placed. Nanite: 89 meshes / 251 actors. Non-Nanite: 125 meshes / 874 actors. 1122
  shadow casters.
- **Draw-call estimate (base pass):**
  - non-Nanite: 1410 sections (actor x slot), which collapse to 219 unique mesh + material pairs;
  - Nanite: 52 material shading bins (331 mesh + material pairs);
  - decals: 101 draws in 6 materials;
  - about 372 per base pass after instancing. The VSM shadow depths re-draw the casters.
- **Triangles placed:**
  - Nanite full-detail source 8.12 M (the wall footing alone 4.1 M: 35 x 117.7 k);
  - non-Nanite LOD0 0.34 M;
  - 1.94 M unique.
- **Textures:** 135 (54 at 2048^2, 41 at 1024^2). Estimated at most 387 MB with full mips (BC with alpha assumed;
  streaming keeps less resident). The largest is the uncompressed 4096 x 1024 sky layer at 21 MB.
- **Renderer:**
  - Lumen GI + reflections;
  - hardware RT on (r.Lumen.HardwareRayTracing 1, project r.RayTracing True);
  - mesh SDFs traced;
  - VSM on (directional LOD bias -1.5);
  - Nanite on; TSR (AA method 4); DBuffer 1; volumetric fog on.
- **GPU frame time:**
  - Setup: RTX 4070 SUPER, i7-14700K. `-game -RenderOffscreen` of L_Dojo in the editor binary with uncooked content;
    the GASP pawn at P1 and its camera; 900 frames with the first 300 dropped.
  - 1920 x 1080 (r.setres): GPUTime median 5.55 ms, p95 5.78.
  - Frame 6.11 ms: render-thread bound (6.11); game thread 2.91.
  - Top GPU passes: TSR 0.85, ShadowDepths 0.65, deferred lighting 0.42, Nanite VisBuffer 0.36, Nanite base pass
    0.29, volumetric fog 0.26, Lumen reflections 0.25.
  - At the offscreen default of 1066 x 600: GPU 3.83 ms.
  - One view only; not a cooked or shipping build.
  - `-csvExitOnCompletion` does not end an editor-binary -game run: the script's timeout ends its own process after
    the CSV is written.

### Captures
- `unreal/round5/r5/`: 35 stills (96 frames, Lumen) and `SHOWCASE_SHEET_R5.png` (with dojo1_reference2 and
  dojo1_reference1). They are the round-4 set plus 7 new ones:
  - CU_R5_ApproachRoad (from the street toward the gate);
  - CU_R5_HallGableEmblem;
  - CU_R5_GateEmblem;
  - CU_R5_AlleyFence;
  - CU_R5_MossWallFoot;
  - CU_R5_FarBackground (background + mountains);
  - CU_R5_Skyline.
- Blown pixels: at most 0.05 % of any frame.

### Open (for the judges / fix round)
- **Shaded roofs read slightly blue:** hall upper roof (56, 60, 78) R/B 0.72 against ref 2's (64, 61, 72) 0.89. A
  warmer tile tint pushes the sunlit tiles back over R/B 1.2 at this sun. That is the trade-off.
- **Sand is a little pale and low in chroma:** s 0.24 against 0.33.
- **The far plain reads as a pale lilac haze sheet** (117, 121, 144), like water, from high views. It is the fogged
  flat FarGround stand-in: specular 0 and a lower aerial-perspective scale changed nothing. The vegetation pass (trees
  on the plain, as in ref 2) is the real fix.
- **The pavilion ceiling between the rafters** stays dark (15, 3, 1): a deep underside at a 12 deg sun. The rafters
  and beams read.
- **Player decals:** bReceivesDecals on the player character (see 2).
- **The emblem:** the hall gable emblem reads bright gilt (the dressing track's note: lower the MI Tint if the judges
  want it older). It sits on the side gables (the hall has no front upper gable); user's call.
- **Hardware RT is on in the project:** the Lumen HWRT cvars measured no difference in the captures.
- **Outside track flags carried over:** cobbles; the canal; the corridor check's stale CONTROL (the f1 copy used here
  passes).
- **Grey-box left:** the 2 trees (vegetation later) and the hidden 1v1 boundary.

### Scripts changed (not committed)
- `Scripts/dojo/showcase/`:
  - `round5.py` (new);
  - `compose_showcase.py` (the round-5 kits, the modern-street swap, the texture homes, decal recipes, routes, layout
    keys);
  - `look_r3.py` (the ROUND 5 section: cameras, ENV, LOOK);
  - `make_sky_clouds.py` (r5 shading + dither).
- `Scripts/dojo/unreal/`:
  - `dj_sc_common.py` (ENV extras);
  - `dj_sc_materials.py` (the decal master);
  - `dj_sc_level.py` (decals, component / PPV extras, sky texture settings);
  - `dj_sc_verify.py` (gate 8, env extras, decal axes);
  - `dj_sc_colour_probe.py` (comp / cvars / show flags / capture props / no-card runs);
  - `run_showcase_unreal.sh` (the perf step);
  - `dj_sc_perf.py` (new);
  - `run_game_perf.ps1` (new).


## 2026-09-29 - ROUND 5 FIX f1: the two round-5 Unreal judges (whole 6.5 / detail 6.5), lighting + colour first, Blender assets + Unreal

User: "start with everything else and leave the vegetation for later" (trees stay grey-box). No DojoLab editor was
open at any step (the runner's guard); one Unreal process at a time, none left running. Headless Blender only (no MCP).
Nothing committed. The armory emblem files were read only (the plaque textures are the dressing track's byte copies).
- **Folders:** `unreal/round5/f1_work/`:
  - `start_backup/` (every showcase, Unreal, outside and dressing script, their layouts, the three .blend files and the
    r5 sky PNG as they were);
  - `it1`..`it8` (iterations); `probe_fog/` (the fog probe);
  - `calib_it1.json` + `fit_sky_calib.py` (the dome response);
  - `sky_preview.py`, `contact.py`, `m.py`, `cores.py` (helpers);
  - `patch_outside.py` (the outside builder patch, for the record);
  - `retired_fbx/` (SM_DKX_Mountains_Near / _Far);
  - `checks/run_checks_f1.sh`;
  - logs.
- `unreal/round5/f1/`: the FINAL 36 stills, `SHOWCASE_SHEET_R5_f1.png` (with CAM_Ref2Match), `measure_f1.txt`,
  `health_f1.txt`, `regions_r5_f1.json`, `json/` (import, materials, level, verify, perf, capture, compose) and
  `json/checks/` (every Blender check).

### Commands
```
py -3 Scripts/dojo/showcase/make_sky_sunset.py --calib WorkFiles/dojo/build/unreal/round5/f1_work/calib_it1.json
blender -b --factory-startup --python Scripts/dojo/outside/build_outside.py          (QA 34 pieces, 0 hard fails, 34 FBX)
blender -b --factory-startup --python Scripts/dojo/dressing/build_dressing.py -- --no-preview   (QA 2, 0 hard fails)
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py      (242 pieces, 1099 instances, 86 decals)
bash WorkFiles/dojo/build/unreal/round5/f1_work/checks/run_checks_f1.sh
DJ_CAPTURE_DIR=<abs>/unreal/round5/f1 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify perf capture
py -3 WorkFiles/dojo/build/unreal/round5/f1_work/make_sheet_r5_f1.py <abs>/unreal/round5/f1 f1
```

### 1. Sky and sun (both judges' first blocker)
- **Sun:** 12 deg / az 160 (west, side-lit) -> **14 deg / az 125** (north-west, behind the hall's left shoulder seen
  from the gate), 5600 K.
  - it1 tried 10 deg / 108: every 5 m building threw a 30 m shadow, so the whole courtyard sat in flat shade.
  - At 14 / 125: the hall front and the gable fronts are backlit (shade), the ridges and roof edges take rim light, and
    the sun rakes across the west sand field while the hall's shadow runs diagonally over the east field.
- **Sky:** `Scripts/dojo/showcase/make_sky_sunset.py` (new). T_DJS_SunsetSky is a FULL opaque painted sky, 8192 x 2048
  (1:1 with the 1920 captures; the r5 layer was 4096 x 1024, magnified 2.4x), BC7.
  - It replaces the translucent cloud layer over the SkyAtmosphere. The atmosphere stays for the sun's transmittance,
    the aerial perspective and the real-time sky light.
  - Gradient: ref 2's measured colours by elevation and angle to the sun (warm horizon band behind the hall -> dusty
    violet).
  - Clouds: band-limited noise projected on a flat deck (they shrink into banks toward the horizon), octaves faded
    under their texel footprint (no aliasing), lit undersides and sun-facing rims, thin edges glowing near the sun.
  - **Calibrated:** `fit_sky_calib.py` traces capture pixels back to dome texels and fits the tonemapper response, so
    the painting targets output colours. Dome Intensity 90 -> 148.
  - `dj_sc_level.sky_dome` takes `cfg["png"]`.
- **Measured (CAM_EstablishingRef2):** horizon left of the hall (238, 161, 107) s 0.55; judge target (240, 150, 90),
  ref 2 (249, 183, 126). Clouds (197, 144, 119).
- **Fog / haze:** explicit inscattering (1.2, 1.1, 1.45), warm directional lobe (2.0, 1.1, 0.5) exp 6 from 150 m,
  density 0.014, the SkyAtmosphere's height_fog_contribution 0. The fog probe (probe_fog) measured 6x that washing the
  ranges to (224, 195, 174).
- **Sky light:** 7.5 -> 9. Sky factor (4.2, 2.8, 2.1) -> (3.8, 2.8, 2.5).
- **Vignette:** 0.15 -> 0.42.

### 2. Far background (both judges' second blocker)
`Scripts/dojo/outside/build_outside.py` + `ox_common.py`.
- **Root cause, found:** SM_DKX_FarGround and both mountain shells were wound with their normals DOWN. Unreal culled the
  plain from above and every front slope of the rings. The judges' 'flat lavender plane with a hard edge' was the sky
  dome's horizon row seen through the culled plain, and the 'sine shells' were the back slopes' undersides. The
  winding is fixed (normals up: checked in Blender).
- **Four ridge rings SM_DKX_Ridge1..4** (0.45-2.25 km, heights 14-215 m, broader, gentler peaks), each ring's back
  falling to the next ring's foot, so no gap shows the sky.
  - Own flat emissive colours on M_DJ_EmissiveFlat_Master (M_DKX_Ridge1..4), so the backlit sun cannot light them
    unevenly. Their colours go (58, 64, 82) -> (128, 124, 148) before the fog.
  - Measured (probe V2): (93, 79, 81) ring 1 -> (157, 134, 128) ring 4, warm toward the sun.
- **SM_DKX_FarTown (new):** about 1,750 low-poly houses (gable, hip, gable-front, kura, two-storey; 38.4k tris, Nanite,
  token UCX) in rotated districts from the town rectangle to 430 m, so no ground reaches the horizon. Flat colour sets
  M_DKX_FarRoofA/B and M_DKX_FarWallPlaster/Wood. FarGround now ends at 470 m under ring 1 (Specular 0).
- **Local town:**
  - every house has its own frontage (x0.82-1.22) and height (x0.86-1.16) scale;
  - 35 % random types break the cycle, and single-storey and kura are mixed into the north rows (`place()` and
    `link_instances` take a scale);
  - the plots use M_DJS_TownYard (fine grey gravel) and the lanes the road cobble (actor overrides on Ground_W/E/N).
- **Power line:** the lower crossarm's four conductors (E-H) are dropped: 28 conductor spans, was 56.
  - `modern_instances()` now reads the modern kit's original rows from the pre-round-5 showcase backup (the live
    layout already carried the moved rows).
  - `compose_checks` no longer appends a second copy of the route-O climbs on every rebuild (they had grown to 25;
    deduped to 5).
- Retired: SM_DKX_Mountains_Near / _Far (RETIRED_MESHES; FBX in f1_work/retired_fbx).

### 3. Assets and look deltas
- **Hall gable emblem:** board 0.90 -> 0.64 m (`build_dressing.py` PLAQUES), clear of the bargeboard and the tie-beam
  block. Its own aged-gilt instance M_DJS_EmblemPlaque_Aged (Tint (1, 0.82, 0.6), VM 0.62, Rough x1.5) on the user's
  unchanged emblem textures.
- **Gate emblem back:** both plaques' back face is now a timber cap (slot M_DJ_TimberDark). It no longer reads as a black
  disc from the courtyard.
  - `dkd_common.load_showcase` leaves the track's own plaques out of the context (the rebuild had made '.001' nodes).
  - decals.json is the track's original: the rebuild's re-planned decals were discarded
    (`f1_work/decals_rebuild_discarded.json`).
- **Decals:** 15 lichen on the tiled roofs and wall caps are dropped (`round5.DROP_DECALS`: the white scribbles, and
  the gate-roof one's box printed black splatter on the soffit). 86 decals remain.
  - A new EdgeFeather in M_DKD_Decal_Master (a UV border fade: moss 0.16, grime / rain 0.1) ends the hard diagonal
    cuts.
  - Moss is subtler: Sat 0.5, Opacity 0.75. The lantern lichen is darkened.
- **Shoji / window glow:** cores (227, 182, 125) s 0.45 (hall) and (229, 194, 118) s 0.48 (residence), clip 0 %.
  Round 5 had s 0.77-0.81 and residence clip 12.9 %.
- **Roof tiles:** neutral warm charcoal (Tint (1, 0.98, 0.95), flatten target (0.058, 0.056, 0.054), not the blue
  texture mean). Hall upper roof (61, 57, 59) R/B 1.03: r5 0.72, ref 2 0.88.
- **Gate timber:** its own grey-brown instances M_DJS_GateTimber / End on the gate frame, roof and leaves; gate lamps
  3300 K x0.7.
- **Street lamps:** x5, 2900 K (pools on the road). The road cobble: tile 4 -> 2.4 m, macro tint / dirt 0.3 / 0.28,
  Sat 0.7, warmer.
- **Sand:** (187, 154, 131) s 0.30 lit, (179, 151, 136) mid. Ref 2: (185, 146, 120) / (179, 149, 131).
- **Training props:** darker walnut (M_DJS_TimberMid VM 3.4 -> 1.9).
- **Gravel:** tile 2 m, Sat 0.5. **Plaster:** normal x1.7.
- **Fill lights:** five shadowless 6000 K fill point lights (Light_Fill_*: pavilion ceiling, both alley fences, both
  corridors). They are layout lights, so verify counts them.
  - Alley fence black tiles 43 -> 0, near-black 21.8 -> 6.1 %; corridor 55 -> 2 tiles, 16.6 -> 8.6 %.
  - Pavilion ceiling (15, 3, 1) -> (34, 17, 9).
- **New camera CAM_Ref2Match** (22, -0.9, 2.1): ref 2's framing from the gate threshold (the paving across the bottom,
  the gate's leaves and posts at both edges).

### Checks (final compose; GASP capsule r 0.30, 1.72 m, step 0.45) - ALL PASS
- **QA:** outside 34 and dressing 2 pieces, 0 hard fails, a UCX on every SM_, all through Scripts/pipeline.
- **walk:** 41 routes + CONTROLs, PASS at r 0.30 and 0.35. The 1v1 rear alley is still closed (the alley-fence CONTROLs
  are blocked).
- **climb:** every route, numbers unchanged:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 (+0.233 step) |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4 + 0.40 |
  | Shed crate -> band | 123.1 -> 122.9 |
  | Pavilion crate -> pad | 122.3 -> 197.9 |
  | Vending | 173.1 + 0.25 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Hurdle | 111.8 |
  | Outside wall climbs (BR) | 197.8-198.7 |

  Route 3: -0.109 / -0.513.
- **Roof walks:** gate, hall, outbuildings, corridors, shed, pavilion: all PASS.
- **Clearance / ground holes:** identical to r5 (46 contacts; the same 136 closed-interior clusters).
- **Unreal verify (fresh process): 8 / 8 gates.** 240 meshes, 134 textures, 1099 / 1099 actors, 86 decals, 24 markers.
- **Perf:** 8.47 M placed triangles (+0.02 M), 2.0 M unique.

### Open (for the judges / user)
- Not done:
  - wall footing stones are still the pillow rubble (a kit-1 geometry rebuild);
  - the wooden dummy's square trunk;
  - the shed roof corrugation silhouette;
  - curb damp and the full-frontage flagstone apron (outside geometry);
  - the player's bReceivesDecals (user's call, as r5).
- The hall facade in shade is darker than ref 2 (veranda band (47, 28, 19) against (72, 49, 32)); the drum top and
  the gate soffit stay deep red-brown in shade.
- The fill lights are an authored bounce stand-in (the judge's ask); the sun's GI x4 stays.
- The far town is flat-colour low-poly (reads at 100 m+); the vegetation pass should add trees among it.
- The hall plaque is still on the side gables (user's call); the sun at az 125 is a look choice (ref 2), not a real
  bearing.
- Lock DojoKit is still held.

### Scripts changed (not committed)
- **Showcase:** `Scripts/dojo/showcase/look_r3.py` (ROUND 5 FIX f1 section), `make_sky_sunset.py` (new),
  `apply_look_r3.py` (fill lights, camera idempotence), `round5.py` (DROP_DECALS).
- **Unreal:** `Scripts/dojo/unreal/dj_sc_level.py` (sky png), `dj_sc_materials.py` (decal EdgeFeather).
- **Outside:** `Scripts/dojo/outside/build_outside.py`, `ox_common.py`.
- **Dressing:** `Scripts/dojo/dressing/build_dressing.py`, `dkd_common.py`.
- **Work files:** `WorkFiles/dojo/build/outside/layout_outside_checks.json` (route-O dedupe).


## 2026-09-29 - INDEPENDENT VERIFIER, ROUND 5 (after fix f1) - RESULT: FAIL (rear alley reachable in the 1v1, black gate soffit, fill-light hotspot, sunlit tiles too warm, 15 decals.json decals absent; the rest passes)

Read-only. Nothing in DojoLab was saved: L_Dojo.umap is still 07:28:43 and no DojoLab content is newer than my first
output. No builder file was touched. No DojoLab editor was open. Seven fresh commandlets ran one at a time (verify x2,
ledges, alley grid, alley flood, pocket probes x2; 17-24 s each), and none is left running. Every output is in
`verify_r5/`.

My truth sources:
- my own re-import of all 242 layout FBX (`fbx_audit.json`);
- the layout matrices;
- the dressing track's `dressing/decals.json`;
- the armory's own emblem PNGs.

### Scripts and outputs (verify_r5/)
- `v5_fbx_audit.py` -> `fbx_audit.json`: 242 pieces, 0 errors, 741 UCX hulls, every name `UCX_<node>_NN`, none missing.
- `v5_ue_verify.py` + `run_v5_ue.sh` -> `ue_verify.json`. The r4 gates, plus:
  - lamps / lights against the layout;
  - grey-box (trees and the hidden boundary only);
  - the alley closed without the ring;
  - decals against decals.json (an independent frame built from the source placement);
  - the emblem (textures exported from the UE texture SOURCE to `emblem_export/`);
  - a crest scan.
- `v5_ue_ledges.py` -> `ue_ledges.json`.
- `v5_ue_alley_grid.py` -> `ue_alley_grid.json`.
- `v5_ue_alley_flood.py` -> `ue_alley_flood.json`.
- `v5_ue_pocket_probe.py` / `v5_ue_pocket_probe2.py` -> `ue_pocket_probe.json` / `ue_pocket_probe2.json`.
- `run_v5_blender_checks.sh` (+ `v5_runcheck.py`, a copy of the r5 wrapper), on DojoShowcase.blend: walk, climb (hover
  0.019), the gate / hall / outbuilding / corridor / shed / pavilion roof walks, clearance, ground holes.
- `v5_emblem_pixels.py` -> `emblem_pixels.json`.
- `v5_capture_health.py` -> `capture_health.json` + `near_black/`.
- `v5_regions_nb.py` -> `regions_nb.json` (4 x 4 cells).
- `v5_sky_banding.py` -> `sky_banding.json`.
- `v5_look_measure.py` -> `look_measure.json` + `look_measure_tight.json`; `crops/`.

### Results
| Check | Result | Numbers |
|---|---|---|
| L_Dojo default + GASP CMC pawn | PASS | EditorStartupMap and GameDefaultMap = L_Dojo; GlobalDefaultGameMode GM_Dojo_C (+ the world override); pawn SandboxCharacter_CMC_C |
| Meshes | PASS | 242 / 242 in UE 5.8.3. Convex hulls = FBX UCX on every piece (741), with no other simple shapes. LODs, LOD0 tris and slots match. 97 Nanite, every fallback full. 0 engine-default or missing materials |
| Level | PASS | 1099 / 1099 instances, one actor each (0 missing / duplicate / extra / wrong mesh). Location, rotation, scale and collision errors all 0. Bounds, worst: 0.0005 cm (non-Nanite) and 0.0013 cm (Nanite fallback geometry). The only other mesh actor is SkyClouds_Dome |
| Grey-box left | PASS | SM_DGB_Tree x2 and SM_DGB_Boundary_1v1 (hidden in game, Pawn block). Nothing else |
| Decals | **FAIL as written** | See below |
| Emblem | PASS | See below |
| Street lamps | PASS | StreetLamp_B (14.0, -8.55) and _A (30.0, -8.55): boxes and lights outside the compound. The 8 poles, the transformer and the guys are outside too. 0 short lanterns. 15 / 15 layout lights at their spots (the 5 Light_Fill_* have no mesh by design) |
| Markers + GASP trace | PASS | 24 / 24 markers, ledge error 0.0. Every route ledge is a real surface: Hall_Veranda W 42 / 46 (its centre probe reads 1/5 again, the r3/r4 artefact). GASP traces hit their own marker 23 / 23 |
| Walk / climb / roof walk | PASS | UE: 41 routes clear, CONTROLs blocked. Blender: walk 41 (also at r 0.35); climb numbers identical to the builder's (below); all six roof walks with their controls; clearance 46 clashes; 136 ground-hole clusters |
| 1v1 ring | PASS | CONTROL_1v1_ring_at_the_open_gate is blocked by the Boundary |
| **Closed rear alley** | **FAIL** | See below |
| Captures: near-black | **FAIL** | See below |
| Captures: blown | **FAIL (small)** | See below |
| Sky banding | PASS | In the sky boxes (Ref2 establishing, far background, skyline, player eye): no missing 8-bit codes and 0 contour / flat-5x5 pixels. The 4x-stretched crops are smooth |
| Sunlit tiles R/B <= 1.2 | **FAIL** | See below |
| Sunlit timber sat <= 0.65 | PASS | Pavilion E post 0.52-0.59, W post 0.48, eave beam 0.30-0.37, fence boards 0.42-0.46, posts 0.47-0.52 |

**Climb heights (cm), identical to the builder's:**

| Obstacle | Height (cm) |
|---|---|
| Wall | 198.1 / 193.7 |
| Pier | 123.1 (+0.233 step) |
| Cistern | 122.3 |
| Eave pad | 172.9 |
| AC | 197.4 + 0.40 |
| Shed crate -> band | 123.1 -> 122.9 |
| Pavilion crate -> pad | 122.3 -> 197.9 |
| Vending | 173.1 + 0.25 |
| Plinth | 98.1 |
| Veranda | 48.1 |
| Hurdle | 111.8 |
| Outside wall climbs | 197.8-198.7 |

Route 3: -0.109 / -0.513.

**Decals (FAIL as written):**
- 86 / 86 layout decals are exact: location 0.0 cm, axis 4e-5, size 0.0.
- Each has the right instance, parent M_DKD_Decal_Master and its own T_DKD_ textures.
- decals.json has 101 entries. The 15 M_DKD_Decal_Lichen decals are absent (round5.DROP_DECALS, the fix-f1 judge
  change): wall cap 6, hall lower roof 4, gate roof 2, outbuilding roof 2, pavilion roof 1.

**Emblem (PASS):**
- All 3 plaques use T_DKD_Emblem_BC / N / ORM.
- Exported from the UE source, they are pixel-identical to T_AK_Emblem_BC / N / ORM: the SHA-256 of the RGBA is equal
  and the max difference is 0. The BC against the armory mask correlates 0.998.
- No other crest-like texture is in the level: all 134 level textures are under /Game/DojoKit.
- In the project only (none placed): the GASP sample's logo textures, Decal_ProjectLogo and the mannequin logos.

### The rear alley is reachable in the 1v1 (both sides)
**Test:** floor-following Pawn capsule sweeps (r 30, hh 62.5). Only the TRV markers are ignored; the 1v1 ring is kept.

**Result:** the sweeps walk CLEAR from the corridor floor / veranda (+0.5) into the rear alley (`ue_pocket_probe2.json`):
- they pass through a slot at the corridor's hall end, on its north side;
- then into the pocket behind the corridor;
- then on to (22, 35), behind the hall.

Example path: (9.0, 31.0) -> (10.45, 31.0) -> (10.45, 33.1) -> (9.0, 33.1) -> (9.0, 35.0) -> (22.0, 35.0). The mirror
route at X 33.55 is clear too.

**The slot:**
- It lies between SM_DKC_PostFrame (which ends at X 10.1) and SM_DKH_VerandaFrame (X ~11.0), at Y ~32.2.
- Its floor is SM_DKC_EndGable_W_Floor at +0.5, with nothing above it up to the roof at +2.9.

**Why it fails:** spec 4.6 closes both the strip behind the hall and the two pockets behind the corridors in the 1v1.
The fence kit (SM_DKX_AlleyFence_W / E, X 10.5-12.87 / 31.13-33.5, Y 34) only closes the veranda ends.

**Pre-existing:** these hulls are unchanged since round 4 (fbx_audit equal). The builders' CONTROL routes never cross
the slot, and the two "_ground" CONTROLs start inside the downpipe hull.

### Captures (4 x 4 cells; near-black = max channel < 12)
- **CU_R5_GateEmblem: 17.9 % of the frame, 13 / 16 cells over 10 % (up to 34.7 %).** The gate's street-side eave beam
  and brackets read (18-20, 7, 3), p25 (8, 2, 1). That is crushed, not night shade.
- Other stills with a cell over 10 %:

  | Still | Worst cell | Note |
  |---|---|---|
  | CU_R4_CorridorOpen | 32.8 % | Hall lower-roof soffit (19, 8, 4). The downpipes are near-black even against the sky-lit plaster: left pipe median (8, 6, 6) |
  | CU_Taiko | 19.1 % | |
  | CU_R4_ResidenceFront | 16.1 % | |
  | CU_Lantern | 15.5 % | |
  | CAM_Drum | 14.7 % | |
  | CU_R4_StorehouseFront | 13.8 % | |
  | CAM_HallVeranda | 13.2 % | |
  | CU_R5_AlleyFence | 11.9 % | |
  | CU_Training | 11.7 % | |
  | CAM_EastYard | 11.5 % | |
  | CU_GateFront | 10.4 % | |

- **Blown outside a glow core:**
  - A white specular hotspot on the drum top: CU_Taiko 342 px, CAM_Drum 212 px, CU_R4_PavilionTaiko 61 px.
  - Its source is Light_Fill_PavilionCeiling at (41, 3, 2.9), 5 cm above the drum top (+2.85). It reads as a bulb
    where no lamp exists.
  - Sky: 5-12 px specks in the sunset glow (most likely the sun disk).

### Sunlit tiles (sRGB medians; `look_measure*.json`)
- Pavilion sunlit E face (tiles only) (139, 119, 104): R/B 1.34; top 30 % 1.31.
- Gate ridge: onigawara 1.24-1.31, noshi 1.30-1.42, cap rolls 1.23-1.25.
- E wall-cap tiles in sun (88, 64, 46): R/B 1.91; top 30 % 1.44.
- The hall roofs pass (0.83-0.93: shaded, blue-grey).

### Fixes required
1. **Rear alley:** close both corridor-end slots in the 1v1 (X 10.1-11.0 and 33.0-33.9, Y ~32.2-32.6), with a fence
   piece or a Pawn blocker in the duel level. Then add CONTROLs through the slots and re-run the walk and in-engine
   sweeps.
2. **Black shade:** lift the gate's street-side soffit and beam (CU_R5_GateEmblem), then re-measure. No 4 x 4 cell may
   be over 10 % near-black outside true night shade. The hall lower-roof soffit and the downpipe material (near-black
   albedo) need a look too.
3. **Fill-light hotspot:** stop the pavilion fill light blowing a hotspot on the drum. Move it, lower it, or make it
   non-specular (specular scale 0).
4. **Warm tiles:** bring the sunlit tiles to R/B <= 1.2 (pavilion roof, gate ridge onigawara / noshi / cap, wall-cap
   tiles) without pushing the shaded roofs blue.
5. **Decals:** reconcile them. Either restore the 15 lichen decals, have the dressing track drop them from decals.json,
   or record the user's acceptance of the drop.

### Notes (not failures)
- The gate lamps (SM_DK_Gate_Lamp x4 at X 18.8 / 25.2, Y +-2.16) are the kit-1 gate fixtures, not short lanterns.
- The layout's `counts.decals` still says 101 (86 placed).

## 2026-09-30 - ROUND 6: DOJOLAB IMPORT + FIXES (the 1v1 rear seal, the far background, gravel, shade, drum bulb, slate tiles, decals sync)

User: "yes start first round. keep emblem for now". The emblem plaques are untouched (gate street side + both hall side
gables); no vegetation (trees stay grey-box). Headless Blender only (no MCP), no DojoLab editor open at any step (the
runners' guard), one Unreal process at a time and none left running. DemoGame_1*, the GASP sample and ArmoryLab were not
touched. Nothing committed. Lock DojoKit refreshed and still held (claude).
- **Folders:** `unreal/round6/r6_work/`:
  - `start_backup/`: every showcase and Unreal script, layout_showcase.json, decals.json, L_Dojo.umap and
    DojoShowcase.blend as they were;
  - `it1`, `it2`: the iterations;
  - `probe_a..c`: the probes;
  - `measure_r6.py`, `make_sheet_r6.py`;
  - `checks/run_checks_r6.sh`;
  - `checks/ue/`: the in-engine alley checks.

  `unreal/round6/r6/` holds:
  - the FINAL 42 stills and `SHOWCASE_SHEET_R6.png`;
  - `measure_r6.json`;
  - `json/`: import, materials, level, verify, perf, capture;
  - `json/checks/`: every Blender check and the UE alley checks.

### Commands
```
blender -b --factory-startup --python Scripts/dojo/showcase/compose_showcase.py      (253 pieces, 1110 instances, 86 decals)
bash WorkFiles/dojo/build/unreal/round6/r6_work/checks/run_checks_r6.sh
DJ_CAPTURE_DIR=<abs>/unreal/round6/r6 bash Scripts/dojo/unreal/run_showcase_unreal.sh prep import materials level verify perf capture
bash WorkFiles/dojo/build/unreal/round6/r6_work/checks/ue/run_r6_ue.sh r6_ue_alley_replay.py r6_ue_alley_flood.py r6_ue_pocket_probe.py r6_ue_pocket_probe2.py
py -3 WorkFiles/dojo/build/unreal/round6/r6_work/measure_r6.py <abs>/unreal/round6/r6
py -3 WorkFiles/dojo/build/unreal/round6/r6_work/make_sheet_r6.py <abs>/unreal/round6/r6
```

### 1. The outside kit in DojoLab (from the outside track's round-6 Blender stage)
- **Import:**
  - 251 meshes: the 45 outside FBX (incl. SM_DKX_PocketFence_W/E and the nine SM_DKX_1v1_* blockers), the new far town,
    and the four ridged rings with their custom normals (FBX normal import ON);
  - 137 textures (T_DKX_FarFacade_BC / ORM / N new); 0 errors.
- **Materials:**
  - new instances M_DKX_FarFacade and M_DKX_FarKawara (on M_DJ_Lib_Opaque) and M_DKX_Blocker1v1 (on M_DJ_Flat_Master);
  - the retired M_DKX_FarRoofA/B and FarWallPlaster/Wood are deleted from DojoLab. look_r3 RETIRED_MESHES now takes any
    package path; the level step reports them 'absent' afterwards.
- **The 1v1 group can be found for the BR:**
  - every instance in folder Boundary_1v1 sits in Outliner folder `Dojo/Boundary_1v1` and carries the actor tag
    `Dojo/Boundary_1v1` (new in dj_sc_level);
  - 14 actors carry it: the 2 alley fences, the 2 pocket fences, the 9 invisible blockers, and the grey-box ring
    SM_DGB_Boundary_1v1 (its folder is the same, and it is 1v1-only too);
  - the blockers are class 'boundary' (Pawn block, Camera / Visibility ignore, hidden in game, no shadow); perf counts
    10 hidden mesh actors.
- **The ridge rings:** no crest strokes in any capture (CU_R6_RidgesNorth, and CU_R5_FarBackground zoomed in).
  - No Specular change was needed on them. M_DJ_EmissiveFlat_Master's new Specular input defaults to 0.5, so nothing
    changed.
  - The far kawara flashed white at grazing angles in it1: M_DKX_FarKawara now has Specular 0.15 and RoughMult 1.6.

### 2. Look fixes (look_r3.py ROUND 6; measured, see `r6_work/probe_a..c`)
- **Masters (dj_sc_materials):** M_DJ_Lib_Opaque gets `Specular` (default 0.5) and `MetallicMult` (default 1).
  M_DJ_EmissiveFlat_Master gets `Specular` (default 0.5). The defaults leave every other instance as it was.
- **Gravel** (M_DKG_Gravel / Coarse): the r5 Saturation 0.5 had taken the warm gravel map grey.
  - Now: Saturation 1.0, Tint (1.1, 0.95, 0.77), ValueMult 0.84 / 1.05.
  - CAM_Overview yards: (156-163, 133-138, 115-123), R/B 1.31-1.39, s 0.24-0.28.
  - r5 f1 was (153, 146, 150) R/B 1.02 s 0.05. Ref 1: (148, 120, 109) R/B 1.36. Ref 2: R/B 1.31-1.48, s 0.23-0.32.
- **Shade:** the crush was the missing bounce, not the grain. In probe_a / probe_c, the timber flatten / AO moved the
  worst cells only 1-2 points.
  - GI settings in the PPV: Lumen diffuse colour boost 3.0 + skylight leaking 0.1 (probe_c C3).
  - The timbers (library timbers, gate, training and stand variants): AOStrength 0.15 + FlattenToMean 0.4 toward their
    own mean.
  - **Downpipes + gutters:** the library Iron is metal (ORM metallic 0.85), so it mirrored the dark eaves.
    - They get their own M_DJS_DownpipeMetal: the Iron maps, MetallicMult 0.15, VM 2.4, flatten 0.5 to a mid grey,
      RoughMult 1.35.
    - It is on SM_DKH/DKO/DKC_Downpipe, SM_DKO_Gutter_S/N/F and the roofs' own gutter (Iron) slot.
    - Left pipe (8, 6, 6) -> (80, 68, 66); mid pipe (94, 77, 71).
  - Results:
    - corridor soffit cell: 32.8 % in r5, now under 10 %;
    - gate emblem frame: 17.9 % near-black in r5, now under 10 % in every cell;
    - pavilion ceiling: (15, 3, 1) in r5, (51, 25, 13) in it1, now (93, 48, 26).
  - **Near-black over all 42 stills (4 x 4 cells, max channel < 12):** 2 stills keep one cell over 10 %. Both are
    geometric true shade:
    - CU_Lantern 13.2 %: the void under the veranda deck;
    - CU_Taiko 11.1 %: the creases between the shaded wall-cap tile rolls.

    For comparison: 12 stills in r5 (up to 34.7 %) and 12 in it1.
- **Drum bulb:** Light_Fill_PavilionCeiling is removed; 4 fill lights are left (the alleys and corridors).
  - Blown px on the drum: CU_Taiko 0, CAM_Drum 0, CU_R4_PavilionTaiko 0 (r5: 342 / 212 / 61).
  - The ceiling is lit by the GI above.
- **Sunlit tiles:** Specular and value barely move them (probe_a V4-V6: +-0.03). The tile instance's Saturation 0.3
  was washing every tint out.
  - Now: Saturation 1.0, flatten target (0.05, 0.056, 0.064) (albedo R/B about 0.78 linear), Tint
    (0.92, 0.975, 1.05), Specular 0.3, AOStrength 0.3.
  - Sunlit R/B (the brightest 30 % of each box):

    | Tile | r5 f1 (verify) | r6 |
    |---|---|---|
    | Gate onigawara | 1.24-1.31 | 1.11 |
    | Gate noshi | 1.30-1.42 | 1.12 |
    | Gate cap rolls | 1.23-1.25 | 1.10 |
    | Pavilion E face (tight box) | 1.31 | 1.13 |
    | E wall cap (tight box) | 1.44 | 1.19 |

  - The price: the shaded hall roofs read R/B 0.74-0.80 in CAM_Ref2Match / EstablishingRef2 (r5 0.83-0.93, ref 2 0.88),
    a cooler dark slate. The low sun is warm, so a tile that stays slate in it has to sit slightly cool in shade.
- **Sunlit timber** saturation is still <= 0.65: pavilion E post 0.57 (brightest 30 %: 0.49), W post 0.47, eave beam
  0.34.
- **Decals:** decals.json now lists the 86 decals the level places.
  - The 15 roof / wall-cap lichen moved to `dropped`, with the reason (the round 5 f1 judge drop).
  - build_dressing.py applies the same drop, so a rebuild stays in sync.
  - Unreal decal gate: 86 / 86, location error 0.0.

### 3. Checks (final level, fresh processes)
- **Unreal verify: 8 / 8 gates**, including 7_gasp_trace 23 / 23 and 8_decals 86 / 86.
  - 253 / 253 meshes (97 Nanite, every fallback full), 137 textures.
  - 1110 / 1110 actors, bounds max error 0.0014 cm.
  - 24 markers (ledge error 0.0), 14 point lights.
- **Perf:**
  - 8.47 M placed triangles, 2.0 M unique;
  - 219 unique meshes;
  - draw estimate 370 per pass;
  - 138 textures, about 395 MB at full mips.
- **In-engine alley seal** (`r6_work/checks/ue/`):
  - `ue_alley_replay.json` replays the outside track's 32 CONTROL + 10 POSITIVE paths as Pawn capsule sweeps (r 30,
    hh 86):
    - with the grey-box ring IGNORED, 32 / 32 CONTROLs are blocked, so the round-6 set seals on its own;
    - with everything in, 32 / 32 CONTROLs are blocked;
    - 10 / 10 POSITIVEs are clear in every mode;
    - in BR mode (the tagged group ignored), 30 / 30 of the CONTROLs the Blender check found open are open;
    - the two lower-roof-north-end CONTROLs start inside the upper roof's eave hull at full height, so they were
      replayed with the verifier's hh 62.5 capsule.
  - `ue_alley_flood.json` (the verify_r5 flood, ring ignored): 0 alley cells reached on either side (W max Y 33.6,
    E 33.7).
  - `ue_pocket_probe*.json` (the verify_r5 slot sweeps): 0 clear. In r5 the slot paths walked clear.
- **Blender** (`r6/json/checks/`, GASP capsule r 0.30, 1.72 m):
  - walk: 47 routes, PASS at r 0.30 and at r 0.35. The 6 new CONTROL_alley_pocket_* routes are blocked by
    SM_DKX_PocketFence_* and SM_DKX_1v1_PocketSide_*.
  - climb: PASS, identical field by field to verify_r5's climb_check.json:

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

  - Roof walks: gate, hall, outbuildings, corridors, shed and pavilion are all identical to verify_r5.
  - Clearance: 46 clashes (r5: 46). Ground holes: 135 clusters (r5: 136).

### Captures (unreal/round6/r6/, 42 stills + SHOWCASE_SHEET_R6.png)
The round-5 set (36, incl. CAM_Ref2Match), plus:
- CU_R6_AlleyPocketW and _E: the corridor ends from the courtyard side, through to the pocket and alley fences;
- CU_R6_AlleyAbove: the sealed strip from above and behind;
- CU_R6_PocketAboveW;
- CU_R6_TownEdgeE: the road ends at the edge-row house fronts;
- CU_R6_RidgesNorth: the jagged rings and the impostor town.

The far view, skyline and overview are CU_R5_FarBackground, CU_R5_Skyline and CAM_Overview.

### Open
- The shaded roofs are cooler than ref 2 (R/B 0.74-0.80 against 0.88). This is the trade-off for sunlit tiles <= 1.2.
- Two near-black cells over 10 % remain, both geometric true shade:
  - the void under the veranda deck (CU_Lantern 13.2 %);
  - the wall-cap tile creases (CU_Taiko 11.1 %).
- The pavilion ceiling is lit by GI only: (93, 48, 26), still a saturated red-brown.
- Lumen diffuse colour boost 3.0 lifts every bounce. The sunlit plaster and timber stayed within the limits (post s
  0.57), but the judges should look at the overall warmth.
- CU_R6_AlleyPocketE and _W read alike (the two ends are mirror-built).
- Still open from earlier rounds:
  - vegetation is pending;
  - the player's bReceivesDecals is the user's call;
  - the DojoKit lock is still held.

### Scripts changed (not committed)
- **Showcase:** `Scripts/dojo/showcase/look_r3.py` (ROUND 6 section).
- **Unreal:**
  - `dj_sc_materials.py`: Lib_Opaque Specular + MetallicMult, EmissiveFlat Specular;
  - `dj_sc_level.py`: the `Dojo/Boundary_1v1` actor tag.
- **Dressing:** `Scripts/dojo/dressing/build_dressing.py` (the decals.json drop sync).
- **Data:** `WorkFiles/dojo/build/dressing/decals.json`: 86 placements + `dropped`. The r5 copy is in
  `r6_work/start_backup/layouts/decals_r5.json`.


## 2026-09-30 - ROUND 6 FIX f1: the round-6 judge (7 / 10) and verifier (gravel), Blender outside + Unreal

User: "yes start first round. keep emblem for now". The emblem plaques are untouched, and there is no vegetation
(trees stay grey-box).

House rules kept:
- headless Blender only (no MCP);
- one Unreal process at a time, none left running;
- no DojoLab editor open at any step;
- DemoGame_1*, the GASP sample and ArmoryLab untouched;
- locks DojoKit and DojoOutside (claude) refreshed and kept;
- nothing committed.

Folders:
- **Work:** `unreal/round6/f1_work/`:
  - `start_backup/`: scripts, layouts, both blends, L_Dojo.umap;
  - `it1`-`it3`, `probe_a`/`probe_b`, `wb/`.
- **Final:** `unreal/round6/f1/`: 42 stills, SHOWCASE_SHEET_R6_f1.png, measure_f1.json, `json/`.

### The alley first
The round-6 seal still holds on the final level (fresh processes):
- **UE:**
  - replay: 32 / 32 CONTROL blocked, 10 / 10 POSITIVE clear, BR 30 / 30 open;
  - flood: 0 alley cells;
  - pocket probes: 0 clear.
- **Blender:** the flood, walk, climb, roof walks, clearance and ground holes are **identical** to round 6
  (`f1/json/checks/`, `round6/build/checks_f1/`).

### Fixes
All in look_r3.py "ROUND 6 FIX f1". Every value was measured with `f1_work/measure_f1.py`.

**Blocker 1: empty sky behind the hall in CAM_Ref2Match**
- Change:
  - CAM_Ref2Match raised to 7.3 m over the gate ridge, hfov 84;
  - CAM_EstablishingRef2 raised to 6.8 m inside the gate, hfov 80;
  - the ridges are 40 % lower (outside notes).
- Why the cameras moved: the Workbench studies show the town is hidden from any eye at 3.1 m or lower.
- Result:

  | | r6 | f1 | Ref 2 |
  |---|---|---|---|
  | Hall share of frame width | 60 % | about 56 % | about 50 % |
  | Behind the hall | sky | town roofs + ridges between the hips and the gables | |

  Both training yards are now in frame.

**Blocker 2: pale town ground**
- Change: M_DJS_TownYard now uses the cobble maps (tile 3.3 m, macro dirt 0.45) at VM 0.74; RoadCobble VM 0.7.
- Result:

  | Region | r6 | f1 | Ref 1 street |
  |---|---|---|---|
  | FarBackground sunlit lot E | (130, 111, 106) L 0.46 | (100, 87, 90) L 0.37 | |
  | FarBackground lot W | (134, 124, 131) L 0.51 | (76, 74, 87) L 0.32 | (77, 75, 87) |
  | Overview lot | | (65, 56, 60) | |
  | Overview street | | (69, 61, 72) | |

**Delta 1: blue slate tiles**
- Change:
  - flatten target with R = G: (0.046, 0.045, 0.059);
  - tint (0.95, 0.94, 1.0), VM 1.4, AO 0.2.
- Result:

  | Where | r6 | f1 | Ref 1 |
  |---|---|---|---|
  | Overview hall | hue 226, HLS s 0.20 | hue 238, s 0.19 | hue 245, s 0.09, L 0.24 |
  | Ref2Match | | hue 240-243, s 0.15-0.16, L 0.28-0.33 | |

- The gate kept (sunlit tile R/B <= 1.2): r6 1.10-1.19; now gate 1.12-1.15, pavilion 1.08, E wall cap 1.19.

**Delta 2: ridges, glow step and an evenly lit town**
- Ridge change:
  - the ring emissive ladder is compressed, with ring 1 lifted most;
  - fog sun lobe exponent 6 -> 3, luminance (1.5, 0.9, 0.45).
- Ridge result: lower, softer layers instead of 4 hard ones (CU_R6_RidgesNorth, CU_R5_FarBackground). Ref 2 shows
  hazy low hills.
- Town: the far town is in distance bands (outside notes). Far rows L 0.25 -> 0.23.

**Delta 3: sand**
- Rake lines:
  - UV Scale 2 halves the spacing;
  - the normal is about 65 % at the feet, falling to 35 % from 25 m (NormalFade -30 / 25 m);
  - Sat 0.9;
  - result: fine, soft lines instead of coarse corrugations (CU_SandEye).
- Ref2Match chroma (camera + material):

  | | r6 | f1 | Ref 2 |
  |---|---|---|---|
  | Ref2Match sand | s 0.43, L 0.67 | HLS s 0.27-0.28, L 0.63-0.64 | s 0.32, L 0.61 |

  The Overview sand stays (211, 175, 150), the same as r6 and ref 1.

**Verifier + delta 4: gravel**
- Change:
  - Sat 0.9, tint (1.12, 0.95, 0.76);
  - VM 0.74 / 0.94;
  - tile 2.8 m (bigger stones).
- Result:

  | Region | r6 | f1 | References |
  |---|---|---|---|
  | Shaded Overview | hue 16.6-24 | (145-148, 122-125, 109-113), hue 20-22, R/B 1.29-1.33 | hue 13-18; ref 1 hall front (148, 120, 109) R/B 1.36 |
  | CU_Training | (176, 144, 122) | (170, 139, 121), hue 22 | ref 2 (150, 119, 107) |

**Delta 5: soft shadows**
- Change: sun disc 0.53 -> 0.3 deg; contact shadows 0.04.
- Result: slightly crisper. The sky light stays at 9.

### The gravel band
The verifier's 25-40 deg band contradicts both references (13-18 deg). Option A, the verifier's own recommendation, is
applied: the gravel is judged against the references, with the band **13-30 deg, R/B >= 1.2, HSV s >= 0.15**.
- 9 / 11 boxes pass it.
- The two misses are eye-level foreground boxes seen at a grazing angle:
  - CAM_PlayerEyeSand W: hue 12.5, R/B 1.20;
  - CAM_EastYard front: hue 15.7, R/B 1.17.
- Against the old 25-40 band, only the sunlit W yard passes (as in r6).
- The final call on the band is the orchestrator's or the user's.

### Tried and rejected
From probe_a / probe_b (one offscreen editor each):

| Variant | Result | Why rejected |
|---|---|---|
| Warm sky-light tint (255, 238, 222) / (255, 228, 208) | shaded tiles neutral (R/B 0.68 -> 0.89 / 1.00) | the backlit scene is sky-lit almost everywhere, so every "sunlit" tile box rose over 1.2 (1.35-1.57); the gravel and sand went orange |
| Lumen colour boost 2.0 | | added a near-black corridor cell; the alley bounce stayed red |
| Sky light 8 / 7 | | E wall cap R/B 1.25 / 1.29; CU_Taiko crease cell 16 / 18 % near-black |

### Checks on the final level (fresh processes)
- **Unreal verify: 8 / 8 gates** (7_gasp_trace; 8_decals 86 / 86):
  - 251 meshes, 137 textures;
  - 1,110 actors, bounds max error 0.024 cm;
  - 24 markers;
  - import, materials (92 instances) and level: 0 errors.
- **Perf:** 219 unique meshes, 2.0 M unique tris, about 395 MB of textures at full mips (r6: 2.0 M / 395 MB).
- **Captures:** 42 / 42.
  - Near-black 4 x 4 cells: the same 2 stills as r6:
    - CU_Lantern 13.2 %: the void under the veranda deck;
    - CU_Taiko 13.0 % (r6: 11.1 %): the shaded wall-cap tile creases, after the darker tile.
  - Drum hotspot: 0 px.
  - The capture-health scan (`f1/json/capture_health.json`): 0 black, blown or grey tiles.
- **Blender:** walk 47 routes PASS, climb PASS. Every roof walk, clearance and ground holes are identical to r6. The
  numbers are kept:

  | Obstacle | Height (cm) |
  |---|---|
  | Wall | 198.1 / 193.7 |
  | Pier | 123.1 |
  | Cistern | 122.3 |
  | Eave pad | 172.9 |
  | AC | 197.4 |
  | Shed | 123.1 -> 122.9 |
  | Pavilion | 122.3 -> 197.9 |
  | Vending | 173.1 |
  | Plinth | 98.1 |
  | Veranda | 48.1 |
  | Hurdle | 111.8 |

### Open
- **Shaded tiles still read cool slate:** R/B 0.68-0.74, HLS s 0.15-0.19, against ref 1 / 2 at 0.84-0.94 and
  s 0.06-0.09. Under this sky light, the sunlit R/B <= 1.2 gate and the reference's neutral shade cannot both hold (see
  the rejected tint). The user or the judges should choose which wins.
- **The rear-alley strip** reads a saturated red-brown in deep shade (96, 56, 44). The cause is the warm bounce off the
  sunlit hall rear and the Lumen colour boost 3.0. It is not the gravel's albedo: the strip uses the same material as
  the yard.
- **CAM_Ref2Match** can no longer show the gate posts or sill, because the camera sits over the gate roof. From this
  height, the corridor lattice stays hidden behind the hall's lower roof.
- Still open:
  - the pavilion ceiling is still a saturated red-brown (94, 48, 27);
  - vegetation is pending;
  - bReceivesDecals is the user's call.

### Scripts changed (not committed)
- `Scripts/dojo/showcase/look_r3.py` (the ROUND 6 FIX f1 section).
- `Scripts/dojo/outside/build_outside.py`.
- `Scripts/dojo/outside/ox_common.py`.

Tools (in `f1_work/` only):
- `measure_f1.py`, `ref2match_boxes.json`;
- `wb_cams.py`, `gridov.py`, `pairs.py`;
- `make_sheet_r6_f1.py`, `v6_capture_health_f1.py`;
- `checks/run_checks_f1.sh`, `checks/run_outside_checks_f1.sh`;
- `checks/ue/run_f1_ue.sh`, plus the r6 UE check copies (they now write to f1_work).


## 2026-09-30 - ROUND 8 stage s1: ULTRA DYNAMIC SKY + the research's GAMEPLAY preset (DojoLab only; no Blender asset changes)

Plan: `WorkFiles/dojo/CINEMATIC_LOOK_RESEARCH.md` (5.1 gameplay preset, 3.x UDS integration). House rules kept: no MCP,
one Unreal process at a time and none left running, no DojoLab editor open at any step (the runners' guard),
DemoGame_1 only READ (a plain file copy of its UltraDynamicSky folder), the GASP sample and ArmoryLab untouched, other
chats' files untouched, nothing committed. Lock DojoKit (claude) refreshed.

**Baseline note:** the brief names `unreal/round7/t1/` as the state the user liked. That folder does not exist; there is
no ROUND 7 section here and no round-7 code in look_r3.py. L_Dojo.umap was last saved 2026-09-29 10:41 (the round-6 f1
level), and the DojoLab log shows the user opened that L_Dojo in the editor on 2026-09-29 21:08-21:11 (nothing saved). So the
"t1 state" backed up and compared against here is the **round-6 f1 level**. Its materials are kept as they are, apart from
the three small corrections listed below.

Folders: `unreal/round8/s1_work/` (start_backup, probes, iterations, tools), `unreal/round8/s1/` (final stills, sheets,
json).

### 1. Backup (restorable)
`s1_work/start_backup/`: L_Dojo.umap (md5 755cdd06...), every Scripts/dojo/unreal and showcase script,
layout_showcase.json + blender_bounds.json, the round-6 f1 json, DojoLab Config/*.ini. The retired lighting assets
(M_DJS_SkyClouds, T_DJS_SunsetSky, MI_DJ_SunsetClouds) stay in DojoLab, unused. To restore: delete the look_r3.py
"ROUND 8" section (ENV["uds"] = None gives the round-6 f1 lighting path), then run prep materials level; or copy the umap back.

### 2. UDS in DojoLab
- A file copy of DemoGame_1/Content/UltraDynamicSky to DojoLab/Content/UltraDynamicSky: 848 files, 545 MB, md5-identical.
  UDS 9.7 (saved with 5.5) loads in 5.8.3 with 0 errors.
- `dj_sc_level.py`: when look_r3.ENV["uds"] is set, the level spawns ONE `Ultra_Dynamic_Sky` actor (label UltraDynamicSky,
  folder Dojo/Lighting, tags DJ_Managed + DJ_UDS) at ground level (Blender (22, 18, 0) = UE (2200, -1800, 0)).
  - It no longer spawns our DirectionalLight, SkyAtmosphere, SkyLight, ExponentialHeightFog, VolumetricCloud or the
    painted sky dome.
  - The UDS variables are set in order, with the time last. Blueprint enums are set through the value's own type.
  - Each set re-runs the construction script, so the Sun component is fetched again before it is read.
  - The UDS lighting-conversion prompt is never used: our actors are simply not spawned. Ultra_Dynamic_Weather is not
    placed (a clear sunset needs no weather).
- Verify gate 6 has a UDS branch:
  - exactly 1 UDS actor and 0 conflicting sun / sky / fog / cloud / dome actors;
  - every UDS variable reads back as ENV;
  - the Sun component matches the layout sun within 3e-3;
  - UDS exposure is off, and our PPV is unbound, manual, at the ENV bias and at a priority above UDS's post-process components;
  - lamps match candela x LAMP_SCALE, there are no Light_Fill_* lights, and the grade is neutral.
  - The extras gate reads back every PPV value (pp_extra + tone curve / bloom / vignette / grain).

UDS values (look_r3.py ROUND 8):

| Variable | Value | Why |
|---|---|---|
| Project Mode | Game / Real-time | gameplay |
| Sky Mode / Cloud Rendering Mode | Volumetric Clouds / Fidelity + Performance | research 3.4 |
| Color Mode / Sky Light Mode | Sky Atmosphere / Capture Based | research 5.1 (fixed time) |
| Apply Exposure Settings | False | ONE exposure owner = our PPV |
| Animate Time of Day / Simulate Real Sun / Manually Position Sun Target | False / False / False | locked sunset |
| Dawn / Dusk Time | 600 / 1800 | defaults |
| Time of Day | 1760 (17:36, 24 min before Dusk) | see below |
| Sun Yaw | 305 | sun at 148 deg from +X (Blender): behind-left of the hall, just outside CAM_Ref2Match's left edge |
| Cloud Coverage / Cloud Speed | 3.0 / 0.2 | scattered to broken (UDS default 3.8 / 0.35) |
| Randomize Cloud Formation on Run / Clouds Move with Time of Day | False / False | repeatable |
| Sun Source Angle Scale | 0.53 | reads back 0.53 deg (UDS default 1.0 deg; ours was 0.3) |
| Half Rate Tick / Use Volumetric Fog | True / True | research 3.6 / 2.7 |
| Lighting Brightness (Dawn/Dusk) | 4.0 | dusk sun + sky light relative to the sky (measured, below) |
| Sky Light Color Multiplier (Dawn/Dusk) | (0.75, 0.88, 1.25) | the captured orange sky tinted every shade red |
| Sun component contact_shadow_length | 0.02 | research 2.3 (ours was 0.04) |

Measured sun: 5.194 deg elevation, 148.008 deg azimuth. Component values: intensity 15.35 (UDS non-physical units), source angle 0.53, contact shadows 0.02, indirect 1.0.

**Sun elevation, a brief conflict:**
- The brief asks for the time 20-40 min before Dusk AND a sun at about 10-14 deg. UDS's sun path (Time of Day is hours
  x 100) measured: 12.95 deg at 1700 (60 min before Dusk), 11.02 at 1715, 7.79 at 1740, 5.19 at 1760, 3.90 at 1770,
  2.60 at 1780.
- At 10-14 deg the physical sky stays a pale blue-white afternoon: the horizon behind the hall is R/B 1.06-1.12, against
  ref 2's 1.59, and top sky hue 208.
- None of the UDS sky controls fix that (probes c / d, CAM_Ref2Match):
  - Saturation 1.4, Mie x3, Rayleigh (Dawn/Dusk) x2: almost no change;
  - Dust 1-2: a sandstorm;
  - the sunset absorption scale x3-7, or an orange absorption colour: the whole scene goes violet.
- The sunset palette appears at 4-6 deg: orange-lit cloud undersides, a warm horizon, the courtyard in soft shade, rim
  light, the glows reading.
- Chosen: 1760 = 24 min before Dusk (inside the time spec), elevation 5.19 deg (under the 10-14 spec). The reference
  governs. The 1700 / 12.95 deg state is it1 (`s1_work/it1/`) if the owner wants the higher sun.

### 3. Gameplay preset (PPV `PostProcess_Dojo`, unbound, priority 10)
The five shadow-lifting overrides are reverted, and the fill lights are removed:

| Setting | round-6 f1 (the "t1" state) | round 8 s1 |
|---|---|---|
| Film Toe | 0.28 | 0.55 (+ Slope 0.88, Shoulder 0.26, Black Clip 0, White Clip 0.04 explicit) |
| Local exposure Shadow Contrast / Highlight / Detail | 0.5 / project 0.8 / - | 0.9 / 0.8 / 1.0 |
| Lumen Diffuse Color Boost | 3.0 | 1.0 |
| Lumen Skylight Leaking | 0.1 | 0.0 |
| Sun source angle | 0.3 | 0.53 (UDS scale) |
| Sun indirect lighting intensity (the round-5 GI x4) | 4.0 | 1.0 (UDS) |
| Fill lights (Light_Fill_AlleyW / E, CorridorW / E) | 4 | 0 (layout lights 14 -> 10) |
| Lumen Final Gather / Scene Lighting / Scene Detail | 2 / 2 / 2 | 1 / 1 / 1 |
| Lumen Final Gather Lighting Update Speed | - | 1 |
| Lumen Ray Lighting Mode | default | Surface Cache (explicit) |
| Sky light | ours, real-time, 9 | UDS captured, 1.0 x dusk brightness 4 = 3.07 (runtime) |
| Sky atmosphere / fog / clouds / sky dome | ours (factor 3.8/2.8/2.5, fog 0.014, dome 148) | UDS |
| Exposure | manual, bias -4.044 | manual, bias +2.35 (the PPV owns it; UDS exposure off) |
| Bloom / Vignette / Film grain | 0.35 / 0.42 / 0.15 | 0.5 / 0.42 / 0.0 |
| Motion blur Amount / Max | - | 0.3 / 2.5 |
| Lens flare / chromatic aberration | - | 0 / 0 |

**Exposure and the recalibration:**
- One owner: our PPV, manual, bias 2.35. That is the old -4.044 plus log2(420 lux / 5), because UDS's sun is 5 units
  against our 420 lux, so dEV = +6.394.
- The lamps (candela) and every EmissiveIntensity are multiplied by 2^-6.394 = 0.01189 (dj_sc_common LAMP_SCALE /
  EMISSIVE_SCALE via ENV["exposure"]). This keeps their look against the new exposure:
  - lamps: LAMP_SCALE 0.25 -> 0.002973;
  - EMISSIVE_SCALE: 1.0 -> 0.01189.
- The -game r.ExposureOffset sweep (+-0.25 / +-1 / +-2) confirmed that no further offset is needed: 0.25 gives 9 % of
  pixels under luma 40, -0.25 gives 16.7 %, ref 2 has 13.7 %.

**Material instance values (the round-6 f1 values kept, except these small corrections for the new light):**
- M_DKX_Ridge1-4 Emissive Colour x 0.25:
  - under the dusk sky the ridges read (184, 183, 195), brighter than the sky above them (about 150);
  - ref 2's hills sit at about half the sky ((109, 99, 113) / (60, 66, 84)).
- M_DJ_RoofTile: Tint (0.95, 0.94, 1.0) -> (0.9, 0.95, 1.06); MeanColour (0.046, 0.045, 0.059) -> (0.041, 0.044, 0.063).
  The shaded kawara read red-brown, R/B 1.39.
- M_DJ_ShojiPaper: EmissiveTint (1.0, 0.87, 0.64) -> (1.0, 0.78, 0.48); Saturation 0.72 -> 0.85; intensity 62 kept. It
  read pale cream against ref 2's deep amber.

### 4. Captures: -game HighResShot (new pipeline; no SceneCapture2D, so the UDS volumetric clouds render)
- New files:
  - `Scripts/dojo/unreal/run_game_capture.ps1`: the guards of run_game_perf.ps1, one UnrealEditor-Cmd `-game
    -RenderOffscreen -dx12` of L_Dojo, `-ExecCmds="py dj_game_capture.py"`. Python is available in -game, because the
    plugin module is UncookedOnly.
  - `Scripts/dojo/unreal/dj_game_capture.py`: a Slate post-tick state machine with these steps:
    1. PlayerController, then the cvars;
    2. the GASP pawn hidden, input ignored;
    3. a 30 s warm-up, then a warm pass of 6 s per camera (shader compiles, Lumen, clouds);
    4. per camera: `r.setres WxH`, SetViewTarget, 10 s settle, then `HighResShot filename=... WxH` at the native size (no
       upscale), and the PNG is awaited.
  - Probe-only options: per-shot console commands, runtime UDS variables (UDS's tick re-reads them), and a UDS read-back.
    A shot name must not contain a dot (HighResShot then drops the .png).
- Capture settings: `scalability 3`, `r.ScreenPercentage 100`, `r.HighResScreenshotDelay 8`, `t.MaxFPS 60`.
  - 16:9 cameras at 1920 x 1080.
  - CAM_Ref2Match / CAM_Establishing / CAM_EstablishingRef2 at 1920 x 1440 (their 4:3 filmback).
- Outputs, in `round8/s1/`:
  - CAM_Ref2Match, CAM_Establishing, CAM_EstablishingRef2, CAM_PlayerEyeSand, CAM_Overview, CAM_GateFromStreet,
    CAM_HallVeranda, CU_HallUpperRoof, CU_R5_Skyline, CAM_EastYard, CAM_Drum, CU_R4_StorehouseFront;
  - `REF2_vs_OURS.png` (reference | our matched camera);
  - `BEFORE_AFTER_vs_R7T1_STATE.png`: the same 12 cameras, before = the saved round-6 f1 level captured the same -game way,
    in `s1/before_game/`.
- Finding: in a real -game frame, the round-6 f1 level is far flatter than its SceneCapture stills showed. CAM_Ref2Match
  had 0.0 % of pixels under luma 40, mean 189.5; the round-6 SceneCapture read 1.9 % under 40.

### 5. Reference vs ours (CAM_Ref2Match matched framing, both at 1448 x 1086; `s1_work/measure_r8.py`, `s1/json/measure_ref2_vs_ours.*`)

| Metric | Ref 2 | Before (round-6 f1, -game) | Round 8 s1 |
|---|---|---|---|
| Luma share under 40 | 13.7 % | 0.0 % | 14.1 % |
| Luma mean / p90 / p10 | 107.9 / 171.1 / 34.4 | 189.5 / 214.5 / 139.1 | 91.2 / 169.3 / 34.8 |
| Clipped | 0.44 % | 1.49 % | 0.18 % |
| Sand texture: high-pass std / luma std | 11.7 / 12.8 | 2.0 / 4.4 | 2.6 / 6.7 |
| Tiles lit (top 30 %) | (91, 84, 94) R/B 0.97 | (151, 151, 171) 0.88 | (50, 37, 44) 1.14 |
| Tiles shade (bottom 50 %) | (43, 39, 45) 0.96 | (126, 122, 138) 0.91 | (37, 25, 28) 1.32 |
| Plaster | (148, 117, 106) 1.40 | (202, 186, 175) 1.15 | (74, 53, 43) 1.72 |
| Sand near | (182, 148, 125) h24 s0.28 | (226, 206, 192) h25 s0.37 | (99, 75, 63) h20 s0.22 |
| Sand far | (189, 157, 136) h24 s0.29 | (225, 207, 195) h24 s0.33 | (103, 78, 67) h18 s0.21 |
| Gravel | (136, 106, 95) 1.43 | (202, 187, 178) 1.14 | (75, 56, 52) 1.44 |
| Horizon sky behind the hall | (207, 153, 130) h18 s0.45 | (239, 204, 179) h25 s0.65 | (180, 155, 137) h25 s0.22 |
| Top sky | (166, 147, 148) | (211, 186, 183) | (139, 137, 137) |
| Shoji glow (top 30 %) | (182, 118, 53) h30 s0.55 | (216, 186, 168) h22 s0.38 | (217, 172, 114) h34 s0.57 |
| Lantern glow (top 10 %) | (241, 180, 90) h36 s0.84 | (199, 192, 194) s0.06 | (198, 135, 68) h31 s0.53 |
| Timber (veranda) | (75, 49, 30) s0.43 | (169, 155, 151) s0.10 | (63, 41, 32) s0.33 |

The histogram now matches ref 2 (share under 40, p90, p10). The subject regions sit about 1 EV under the reference while
the sky sits about level with it: ref 2 (an AI painting) lights its shaded courtyard as bright as its horizon, which a
physical dusk cannot do without a lift. Per still: `s1/json/capture_health.json`.

### 6. Functional checks (fresh processes, final level)
- **Unreal verify: 8 / 8 gates**:
  - 1-5 unchanged;
  - 6_environment is the UDS branch, every UDS variable and PPV value read back;
  - 7_gasp_trace passes;
  - 8_decals 86 / 86;
  - 1110 actors, bounds max error 0.024 cm, 24 markers, 10 lamps.
- **UE alley** (`s1/json/checks/`): identical to round-6 f1.
  - Replay: 32 / 32 CONTROLs blocked, 10 / 10 POSITIVEs clear, BR 30 / 30 open with no mismatch.
  - Flood: 0 alley cells.
  - Pocket probes: 0 clear.
- **Blender:** walk 47 routes (21 / 21 CONTROLs blocked, PASS at r 0.30 and r 0.35), climb PASS. The gate, hall,
  outbuilding, corridor, shed and pavilion roof walks, the clearance and the ground holes are all field-by-field
  identical to round-6 f1.
- No gameplay number, collision or 1v1 alley closure changed: the level step re-placed the same layout.

### Open
- **The owner's call:** the sun at 5.2 deg (sunset palette, reference look) against the brief's 10-14 deg (a daytime sky
  in UDS: it1).
- **Colour gaps:**
  - the horizon is less saturated than ref 2 (s 0.22 against 0.45);
  - shaded tiles and plaster are still warm (R/B 1.32 / 1.72 against 0.96 / 1.40);
  - the rake texture is soft in shade (high-pass std 2.6 against 11.7);
  - the subject regions sit about 1 EV under ref 2.
- CAM_Drum: the 5 deg sun at dusk brightness x4 lights the pavilion posts and taiko hot orange, 3.1 % clipped.
- Dark stills, judged against the reference, not the old anti-black rule: CAM_HallVeranda 57 % under luma 40,
  CU_HallUpperRoof 74 %, CAM_EastYard 42 %.
- Not measured here: GPU frame time with UDS (volumetric clouds + volumetric fog), which is for the verify stage.
- Not enabled (they need the owner's OK): Movie Render Queue / Graph, DLSS.

### Scripts changed (not committed)
- `Scripts/dojo/showcase/look_r3.py`: the ROUND 8 section.
- `Scripts/dojo/unreal/dj_sc_common.py`: UDS, EXPOSURE, EV_DELTA, and the scaled LAMP_SCALE / EMISSIVE_SCALE.
- `Scripts/dojo/unreal/dj_sc_level.py`:
  - `uds_environment()`, `sun_record()`, `environment_post()`;
  - the PPV priority;
  - the bias from ENV;
  - the 3e-3 sun tolerance with UDS.
- `Scripts/dojo/unreal/dj_sc_verify.py`: `gate_environment_uds()`, the UDS branch of `gate_env_extras()`.
- New: `Scripts/dojo/unreal/dj_game_capture.py`, `Scripts/dojo/unreal/run_game_capture.ps1`.
- Data: `WorkFiles/dojo/build/showcase/layout_showcase.json`, re-patched by prep: the fill lights are gone and the sun
  record is 5.19 / 148.01. The pre-round-8 copy is in `s1_work/start_backup/layouts/`.
- Tools (in `s1_work/` only): `run_ue.sh`, `measure_r8.py`, `health.py`, `sheet.py`, `grid.py`, `uds_strings.py`,
  `probe/uds_probe1.py`, the probe configs `probe_t` .. `probe_g`, and `checks/` (the round-6 f1 runners repointed to
  round 8).

## 2026-09-30 - ROUND 8 stage s2: RETUNE of the UDS level after the s1 judge (5/10) (DojoLab only; no Blender asset changes)

House rules kept:
- no MCP;
- one Unreal process at a time, and none left running;
- no DojoLab editor open at any step (the runner guards checked);
- DemoGame_1 not touched;
- the GASP sample, ArmoryLab, and other chats' files and locks untouched;
- nothing committed.

The DojoKit lock (claude) was refreshed.

Folders:
- `unreal/round8/s2_work/`: backup, probes, iterations, checks, tools.
- `unreal/round8/s2/`: final stills, sheets, json.

### 1. Backup of the s1 state (restorable)
`s2_work/start_backup/` holds:
- L_Dojo.umap (md5 d580da55...);
- every Scripts/dojo/unreal and showcase script (look_r3.py without the s2 sections);
- layout_showcase.json and blender_bounds.json;
- every DojoKit `*/Materials` folder;
- DojoLab Config/*.ini.

To restore s1, either:
- delete the "ROUND 8 s2" sections at the end of look_r3.py (and the radius lines in `apply_lights`), then run
  `run_showcase_unreal.sh prep materials level verify`; or
- copy the umap and the materials back.

### 2. What the judge blocked, and the fix
All fixes are UDS variables, the PPV and material instances. No sky light or fill light was re-added.

- **Key light inverted.** Probes (`s2_work/probe_a..h`, UDS variables set at runtime in -game) measured this:
  - At 5.2 deg no sun yaw lights the sand: the 2-3 m walls and the gatehouse shade it. From about 9-10 deg the sand takes
    the sun.
  - Chosen: **Time of Day 1730, Sun Yaw 268 = 9.08 deg elevation, 187.29 deg from +X (Blender)**. The sun comes from the
    west, 7 deg south of the hall's face line.
  - Result: the sun rakes the sand from the left, and the west-yard shadows stream across the left field. The hall front,
    veranda and lanterns take a grazing warm light.
  - Rejected: Yaw 262 and 258 put the shed and gatehouse shadows over the near field. 1740 (7.8 deg) shaded the near field.
- **Sky at 9 deg.** UDS's physical sky is a pale blue day sky at this sun height.
  - Rayleigh (Dawn/Dusk) (0.17, 0.41, 1.0) -> (0.45, 0.38, 0.52) turns the upper sky mauve-grey.
  - Fog Color Mode = UDS Fog Settings, All Fog Colors Multiplier (5.0, 1.6, 0.75) and Fog 2.2 lay a peach band on the
    horizon and warm haze on the far ridges.
  - The absorption knobs stay at their defaults (they turned the sky violet).
  - Simplified Color was tried at runtime and not kept: the sky did not change, and research 3.2 keeps Sky Atmosphere.
- **Clouds:** Cloud Coverage 3.0 -> 2.6, Layer Height Scale 0.35, Volumetric Clouds Scale 2.5 give thin layered stratus
  streaks instead of cumulus puffs. Cloud Wisps Opacity (Clear) 1.0 and Wisps Color Intensity 3.0.
- **Sun and ambient colour:**
  - Sun Light Color (0.96, 0.94, 1.0). The orange 9 deg sun on warm albedos read R/B 1.5-2.0 on plaster and gravel.
  - Sky Light Color Multiplier (Dawn/Dusk) (0.75, 0.88, 1.25) -> (0.6, 1.25, 1.5). The mauve sky, captured into the sky
    light, put magenta in every shade.
- **Exposure:** PPV manual bias 2.35 -> 1.5, because the sunlit sand made the frame bright. The lamps and emissives follow
  the bias (dj_sc_common: x 2^0.85 = 1.8), so they read hotter against the darker scene.
- **Materials** (instances, look_r3.py "ROUND 8 s2"):
  - Sand (Raked and Edge): Tint (1, 0.78, 0.66) -> (1, 0.92, 0.8); Saturation 0.9 -> 0.5; ValueMult 0.75 -> 0.88.
  - Rake relief, Raked only:
    - UV Scale 2 -> 1, back to the spec's 9.5 cm lines (the 4.8 cm lines averaged out in the mips);
    - NormalFade 2000 -> 3000 cm, far strength 0.35 -> 0.7.
  - Plaster: ValueMult 1.05 -> 1.5; Saturation 0.45 -> 0.22; Tint (0.97, 0.96, 1.0).
  - Gravel / GravelCoarse: ValueMult 0.74 / 0.94 -> 1.3 / 1.45; Saturation 0.9 -> 0.7; Tint (1.04, 0.96, 0.86).
  - Kawara: ValueMult 1.4 -> 1.6; Tint (0.76, 0.9, 1.22).
  - Timber Dark and Aged (and their End variants): ValueMult 3.0 -> 1.5.
  - Shoji: EmissiveTint (1, 0.64, 0.28); Saturation 1.0; intensity 62 -> 55.
  - Lantern glass: EmissiveTint (1, 0.55, 0.18); Saturation 1.0; intensity 55 -> 95.
  - Far ridges: emissive x (1.12, 1, 0.86), a warm mauve on the same brightness ladder.
- **Lamps** (LAMP_TUNE):
  - stone lanterns (LanternTall): candela x1.5, radius 7 -> 10 m;
  - gate lamps: 0.7 -> 1.1 x, radius 9 -> 12 m.
  - `look_r3.apply_lights` now also tunes `radius_m` (the composed value is kept in `base`).
- `Scripts/dojo/unreal/dj_game_capture.py`: probe runs can now set Blueprint-enum UDS variables ({"enum": ...}). A failed
  probe set is recorded, not fatal.

### 3. Captures (-game HighResShot with UDS volumetric clouds; no SceneCapture)
In `round8/s2/`:
- stills:
  - CAM_Ref2Match, CAM_Establishing and CAM_EstablishingRef2 at 1920 x 1440;
  - CAM_PlayerEyeSand, CAM_Overview, CAM_GateFromStreet, CAM_HallVeranda, CU_HallUpperRoof, CU_R5_Skyline, CAM_EastYard,
    CAM_Drum and CU_R4_StorehouseFront at 1920 x 1080;
- `REF2_vs_OURS.png`: the reference beside our matched camera;
- `BEFORE_AFTER_vs_R7T1_STATE.png`: three columns:
  - the saved round-6 f1 level, which is the "t1 state" (round7/t1 does not exist, see s1);
  - round 8 s1;
  - round 8 s2.

Iterations it1-it4 are in `s2_work/`; it4 is the final.

### 4. Reference vs ours
CAM_Ref2Match at 1448 x 1086; full data in `s2/json/measure_ref2_vs_ours.*`.

| Metric | Ref 2 | Round 8 s1 | Round 8 s2 |
|---|---|---|---|
| Luma share under 40 / mean / p90 | 13.7 % / 107.9 / 171.1 | 14.1 % / 91.2 / 169.3 | 9.7 % / 117.9 / 169.4 |
| Sand high-pass std / luma std | 11.7 / 12.8 | 2.6 / 6.7 | 7.0 / 12.1 |
| Tiles lit | (91, 84, 94) R/B 0.97 | (50, 37, 44) 1.14 | (82, 68, 66) 1.24 |
| Tiles shade | (43, 39, 45) 0.96 | (37, 25, 28) 1.32 | (39, 30, 34) 1.15 |
| Plaster | (148, 117, 106) 1.40 | (74, 53, 43) 1.72 | (103, 79, 66) 1.56 |
| Sand near | (182, 148, 125) s0.28 | (99, 75, 63) s0.22 | (165, 133, 103) s0.26 |
| Sand far | (189, 157, 136) s0.29 | (103, 78, 67) s0.21 | (185, 152, 118) s0.32 |
| Gravel | (136, 106, 95) 1.43 | (75, 56, 52) 1.44 | (112, 83, 71) 1.58 |
| Horizon behind the hall | (207, 153, 130) h18 s0.45 | (180, 155, 137) h25 s0.22 | (200, 163, 142) h22 s0.34 |
| Top sky | (166, 147, 148) | (139, 137, 137) | (156, 131, 130) |
| Shoji glow | (182, 118, 53) R/B 3.43 | (217, 172, 114) 1.90 | (217, 157, 65) 3.34 |
| Lantern glow | (241, 180, 90) s0.84 | (198, 135, 68) s0.53 | (219, 181, 104) s0.61 |
| Timber | (75, 49, 30) | (63, 41, 32) | (90, 60, 38) |

Per still (`s2/json/capture_health.json`), share of pixels under luma 40, s2 against s1:

| Camera | s2 | s1 |
|---|---|---|
| CAM_HallVeranda | 36.7 % | 57 % |
| CU_HallUpperRoof | 45.3 % | 74 % |
| CAM_EastYard | 31.0 % | 42.5 % |

CAM_Drum is at 52.3 %, mean 60: the pavilion interior sits in shade. It has 0 % clipped (s1: 3.1 %).

### 5. Functional checks (fresh processes, final level)
- **Unreal verify: 8 / 8 gates.**
  - 6_environment (the UDS branch):
    - every UDS variable reads back, including the new colours and the enum;
    - the sun is at 9.08 deg / 187.29 deg, within 3e-3;
    - the bias is 1.5;
    - 10 lamps at candela x LAMP_SCALE.
  - Level: 1110 actors, bounds max error 0.024 cm, 24 markers.
- **UE alley** (`s2/json/checks_ue/`):
  - replay: 32 / 32 CONTROLs blocked, 10 / 10 POSITIVEs clear, BR 30 / 30 with no mismatch;
  - flood: 0 alley cells;
  - pocket probes: 0 clear.
- **Blender** (`s2/json/checks/`):
  - walk: 47 routes, PASS at r 0.30 and r 0.35;
  - climb: PASS;
  - the gate, hall, outbuilding, corridor, shed and pavilion roof walks, the clearance and the ground holes are
    field-by-field identical to s1.
- No gameplay number, collision or 1v1 alley closure changed: only lights, the sun and material instances.

### Open
- **Sun height against the reference.** The sun is at 9.1 deg, higher than the reference implies. The reference lights the
  sand AND shows a sunset glow behind the hall; a physical sky cannot do both with one sun position.
  - The horizon behind the hall is still less saturated (s 0.34 against 0.45).
  - The upper sky is slightly dark.
- **Remaining gaps against ref 2:**
  - plaster and gravel are still about 0.5 EV under (the gables and side yards take only grazing sun at 187 deg);
  - lit kawara read a little warm (R/B 1.24);
  - rake relief is 7.0 against 11.7: it is normal-map only, and real depth would be a ground-kit change.
- **Exposure:** the frame mean on CAM_Ref2Match is 117.9 against 107.9 (+0.13 EV). The other cameras sit darker, so it was
  left.
- **Not added:**
  - ref 2's perimeter path and garden lanterns (they are new assets);
  - vegetation: the grey-box tree cylinders show in CAM_EastYard, CAM_GateFromStreet and CAM_Overview (the vegetation
    round).
- **Not checked here:**
  - the ridge-mesh "curtain" artefact in CU_HallUpperRoof, beyond the warmer haze (outside v2 replaces those meshes);
  - the CAM_Establishing sky banding;
  - GPU frame time (the verify stage).
- **Not enabled:** MRQ / Movie Render Graph, DLSS.

## 2026-09-30 - ROUND 9 stage s2: RETUNE after the paired judge (r9 5.5 vs r8 4.5) (DojoLab only; no Blender asset changes)

House rules kept:
- no MCP;
- one Unreal process at a time, none left running, and no DojoLab editor open (the runner guards checked);
- DemoGame_1, the GASP sample, ArmoryLab and other chats' files, locks and processes untouched (the armory chat's Blender
  jobs were left alone);
- nothing committed.

The DojoKit lock (claude) was refreshed. The sun stays at the owner's 9.08 deg from the west (Time of Day 1730, Sun Yaw
268). The Megaplants settings and the perf config were not touched.

**Scope note (the owner's request):** the owner asked for a study of how best to build stone, stone walls and rocks
BEFORE any more stone work. Judge delta 6 (the granite slab path) and the stone half of delta 8 (the gate-step glint)
are stone work, so they wait until that study exists. No stone mesh or stone material was changed here.

Folders:
- `unreal/round9/s2_work/`: backup, probes a-i, the build-1 capture, checks, tools;
- `unreal/round9/s2/`: final stills, sheets, json.

### 1. Starting state, and what was reused from the stopped run
- The stopped run (09:33) left DojoLab built at its **it4** (the look_r3 "ROUND 9" section up to "round 9 it4").
  - Its materials step (09:33:15) and level step (09:33:44) both completed cleanly: sc_level passed and saved, and the
    log exits normally.
  - No verify and no capture ran on it4.
  - The judged "r9" state is the it3 capture (`s1_work/it3`).
- Kept from that run:
  - the whole ROUND 9 section: the softer 3 deg sun disc, film grain 0.1 as the sky dither, the steeper fog falloff, the
    Rayleigh and cloud colours, the ShojiClere instance, shadow saturation 0.8, and the UseRakeVar sand switch in
    `dj_sc_materials.build_ground`;
  - its tools: measure_r8.py, extra_r9.py, health.py, sheet.py, mk.py, rungame.sh.
- Overridden by this stage (section 5): the teal roof tint, the 3.6 cloud deck, the 3x / 12 m lantern pools, the toe
  0.72 settings and the rake wobble.

### 2. Backup (restorable)
`s2_work/start_backup/` holds the round-9 s1 (it4) state:
- L_Dojo.umap (md5 5b408dbc...);
- every DojoKit `*/Materials` folder, plus DojoKit/Materials;
- Config/*.ini and DojoLab.uproject;
- Scripts/dojo/showcase and Scripts/dojo/unreal;
- layout_showcase.json and blender_bounds.json.

To restore, either:
- delete the "ROUND 9 s2" section and its "it2" block at the end of look_r3.py, then run
  `run_showcase_unreal.sh prep materials level verify`; or
- copy the umap and the materials back.

### 3. Judge deltas checked against dojo1_reference2 (the judge-steer rule)
| Delta | Reference check | Action |
|---|---|---|
| 1 roof teal | confirmed: the ref roof is (57, 52, 59), a neutral-lavender charcoal; the it4 albedo = 0.8 x MeanColour (0.053, 0.087, 0.115) x 1.85, which is teal | applied |
| 2 sky deck | confirmed: ref clear gaps (138, 123, 137) lavender, lit clouds (241, 183, 143); it3 gaps (133, 92, 96) maroon | applied |
| 3 horizon / banding | confirmed (ref band (245, 174, 128)); the banding near the sun shows in CAM_EastYard | partly (see Open) |
| 4 shadow fill | partly contradicted: in the matched frame ref 2's darks are as deep as ours (under-40 13.7 % against it3 11.7 %; deck (73, 47, 29)); the side cameras were crushed | lifted locally (local exposure), not by a global toe |
| 5 rake | frequency contradicted: FFT of the near sand gives a period of 7.5 px in ref 2 against 5.4 px ours at 1448 wide, so ours is already FINER; the ref lines are straight and regular (the it1-it4 wobble made the blotchy bands) | coarser lines, wobble off |
| 6 slab path | stone work: waits for the owner's stone study | not done |
| 7 shoji | confirmed: it3 (215, 140, 59) s 0.66 against ref (182, 118, 53) s 0.55 | applied (-22 %, saturation 0.9); the gradient and the thinner lattice need asset work |
| 8 sheen | the stone glint waits for the stone study; "lower sun angle" contradicts the owner's 9 deg decision | not done |
| 9 lantern pools | confirmed: the ref pools are small and modest | applied |

### 4. Probes (`s2_work/probe_a..i`)
All probes are -game captures with UDS, PPV, MID and lamp values overridden at runtime.
- a: the first candidate.
  - Toe 0.62 with sky light 3.4 over-lifted the frame (5.4 % of pixels under luma 40).
  - Coverage 2.6 with contrast 0.3 gave a flat haze.
- b: the deck was the 3.6 coverage in a 0.35 layer, plus opaque wisps. Overall Intensity scales the ground too
  (rejected).
- c: coverage 2.8-3.2 in a full-height layer at 1.2x scale, with wisps at 0.5, gives separated cumulus with gaps (c3
  kept).
- d / e:
  - a sky-light tint of (0.8, 1, 1.15) put magenta in every shade (tiles shade hue 326);
  - (0.7, 1.3, 1.25) lands the shade neutral;
  - roof R1 (tint (0.85, 0.97, 1.3), mean (0.045, 0.05, 0.072)) reads slate-charcoal in CU_HallUpperRoof.
- f: a redder fog tint (24, 4.5, 1.0) warmed the whole scene (tiles R/B 1.48); (16, 4, 1.2) was kept.
- g: the candidate on all 12 cameras.
- h: LB 1.0, SLI 3.6 and the warmer roof R3 were all worse.
- i (on the built level):
  - the sky sat ~0.5 EV under because local-exposure highlight contrast 0.7 compressed it;
  - fix: LB 0.7 with the bias +0.3, and highlight contrast 0.8 (1.0 clipped 4.75 % of CAM_EastYard around the sun).

### 5. Final values (look_r3.py "ROUND 9 s2" + "round 9 s2 it2")
- **UDS:**
  - clouds: Cloud Coverage 3.2, Macro Variation 0.5, Contrast 0.45, Layer Height Scale 1.0, Volumetric Clouds Scale
    1.2, Cloud Wisps Opacity (Clear) 0.5;
  - sky and fog: Rayleigh (Dawn/Dusk) (0.3, 0.4, 1.0), All Fog Colors Multiplier (16, 4, 1.2), Base Height Fog
    Falloff 0.5, Fog 2.3;
  - light: Lighting Brightness (Dawn/Dusk) 0.7, Sky Light Intensity 3.8, Sky Light Color Multiplier (Dawn/Dusk)
    (0.7, 1.28, 1.25);
  - Time of Day 1730 and Sun Yaw 268 unchanged (the time is still set last).
- **PPV:**
  - bias 1.2 -> 1.75 (the lamps and emissives follow it via dj_sc_common);
  - toe 0.72 -> 0.7;
  - local exposure shadow contrast 1.0 -> 0.65;
  - highlight contrast 0.8 (the same value, set explicitly).
- **Instances:**
  - M_DJ_RoofTile: ValueMult 1.75, Tint (0.85, 0.97, 1.3), MeanColour (0.045, 0.05, 0.072);
  - M_DJ_ShojiPaper: EmissiveIntensity 45 -> 35.1, Saturation 0.9;
  - M_DJS_ShojiClere: EmissiveIntensity 29.25 -> 22.8, Saturation 0.9;
  - the four timber instances: Saturation 0.26;
  - M_DKG_SandRaked: UV Scale 1 -> 0.72, RakeWarp 0.004, RakeWarpU 0.002, NormalVar 0.1, ValueMult 1.0;
  - M_DKG_SandEdge: ValueMult 1.0.
- **Lamps:**
  - stone LanternTall: 3.0x / 12 m -> 1.5x / 7 m;
  - Modern_WallLamp: 2.0x / 10 m -> 1.5x / 8 m.
- No master material changed in this stage.

### 6. Measurements
CAM_Ref2Match in the matched framing, 1448 x 1086; full data in `s2/json/measure_ref2_vs_ours.*`, `extra_r9.json` and
`sky_metrics.txt`.

| Metric | Ref 2 | r8 s2 | r9 s1 (it3) | **r9 s2** |
|---|---|---|---|---|
| luma under 40 / mean | 13.7 % / 107.9 | 9.7 / 117.9 | 11.7 / 111.2 | 9.45 / 119.2 |
| luma p10 / p90 / clipped | 34.4 / 171.1 / 0.44 % | 40.6 / 169.4 / 0.24 | 35.2 / 160.4 / 0.23 | 41.4 / 168.9 / 0.17 |
| sand high-pass std / luma std | 11.7 / 12.8 | 7.0 / 12.1 | 7.6 / 10.0 | 8.3 / 10.6 |
| tiles lit | (91, 84, 94) R/B 0.97 | (82, 68, 66) 1.24 | (92, 85, 84) 1.09 | (86, 67, 70) 1.23 |
| tiles shade | (43, 39, 45) 0.96 | (39, 30, 34) 1.15 | (37, 33, 41) 0.90 | (42, 33, 39) 1.08 |
| plaster | (148, 117, 106) 1.40 | (103, 79, 66) 1.56 | (143, 105, 89) 1.61 | (139, 115, 96) 1.45 |
| sand near | (182, 148, 125) | (165, 133, 103) | (163, 125, 101) | (162, 136, 112) |
| sand far | (189, 157, 136) | (185, 152, 118) | (179, 143, 113) | (176, 150, 123) |
| gravel | (136, 106, 95) 1.43 | (112, 83, 71) 1.58 | (132, 94, 82) 1.61 | (119, 97, 89) 1.34 |
| horizon behind the hall | (207, 153, 130) h18 s0.45 | (200, 163, 142) s0.34 | (195, 146, 123) s0.38 | (188, 158, 146) h17 s0.24 |
| top sky | (166, 147, 148) | (156, 131, 130) | (126, 84, 88) | (129, 108, 115) |
| shoji glow | (182, 118, 53) s0.55 | (217, 157, 65) s0.67 | (215, 140, 59) s0.66 | (206, 136, 80) s0.56 |
| lantern glow | (241, 180, 90) s0.84 | (219, 181, 104) s0.61 | (239, 188, 88) s0.82 | (222, 165, 76) s0.69 |
| timber | (75, 49, 30) s0.43 | (90, 60, 38) | (70, 36, 18) s0.59 | (74, 49, 31) s0.41 |
| sky band (rows 0-280): unique colours / zero-gradient | 29,978 / 6.5 % | 5,515 / 27.9 % | 35,679 / 4.6 % | 34,631 / 4.0 % |
| sky clear gaps (skym.py) | (138, 123, 137) | (156, 130, 128) | (133, 92, 96) | (131, 111, 119) |
| sky lit clouds (skym.py) | (241, 183, 143) | (192, 159, 145) | (167, 119, 101) | (175, 151, 133) |
| sand lit / shade (extra_r9) | 1.12 | 1.51 | 1.29 | 1.22 |

Per still (`s2/json/capture_health.json`): share of pixels under luma 40, it3 -> s2.

| Camera | it3 | s2 |
|---|---|---|
| CAM_HallVeranda | 44.3 % | 38.8 % |
| CAM_EastYard | 37.8 % | 31.2 % (clipped 0.47 -> 0.39 %) |
| CAM_Drum | 63.5 % | 42.9 % |
| CU_HallUpperRoof | 29.7 % | 25.0 % |
| CAM_Overview | 37.7 % | 21.2 % |
| CU_R4_StorehouseFront | 33.1 % | 26.3 % |
| CAM_Ref2Match | 11.9 % | 9.6 % |

### 7. Functional checks (fresh processes, final level)
- **Unreal verify: 8 / 8 gates.**
  - 6_environment: every UDS variable reads back, including Macro Variation; the bias is 1.75; the sun is at 9.08 deg /
    187.29 deg; 10 lamps.
  - Level: 1110 meshes, 24 markers, bounds max error 0.024 cm. L_Dojo.umap md5 85c04fc0...
- **UE alley** (`s2/json/checks_ue/`, run on the final level):
  - replay: 32 / 32 CONTROLs blocked, 10 / 10 POSITIVEs clear, BR 30 / 30 with no mismatch;
  - flood: 0 alley cells, W and E;
  - pocket probes: 0 / 0 clear.
- **Blender** (`s2/json/checks/`):
  - walk: 47 routes, PASS at r 0.30 and r 0.35;
  - climb: PASS;
  - the gate, hall, outbuilding, corridor, shed and pavilion roof walks, the clearance and the ground holes are
    field-by-field identical to round 8 s2.
  - layout_showcase.json is byte-identical between the two builds of this stage, so these checks also cover the final
    level.
- No gameplay number, collision or 1v1 alley closure changed.

### 8. Captures
In `round9/s2/`:
- the 12 stills: CAM_Ref2Match, CAM_Establishing and CAM_EstablishingRef2 at 1920 x 1440, the rest at 1920 x 1080;
- `REF2_vs_OURS.png`;
- `BEFORE_AFTER_R8S2_R9S1_R9S2.png`.

The first build's capture is in `s2_work/build1_capture/`.

### Open
- **Waiting for the owner's stone study:** delta 6 (the granite slab path, two slabs across, with joints) and the stone
  step / slab glint of delta 8.
- **Rejected deltas:**
  - delta 5, "increase groove frequency", because ref 2's grooves are coarser than ours;
  - delta 8, "sun at a lower angle", because of the owner's 9 deg decision;
  - delta 4, "lower the toe", in the matched view, because ref 2's darks are as deep as ours there.
- **Remaining gaps against ref 2:**
  - the horizon band is still less saturated (s 0.24 against 0.45); a redder fog tint warms every surface (probe f);
  - the top sky sits ~0.35 EV under ref 2 relative to the ground, and the lit cloud rims are peach but dimmer than
    ref 2's;
  - the lit kawara still read a touch warm in CAM_Ref2Match (R/B 1.23), while the close-up reads slate;
  - the frame mean is 119 against 108: our frame has no dark gate posts, and the ground regions sit within ~0.1 EV of
    ref 2;
  - rake relief is 8.3 against 11.7: it is normal-map only, and real relief would be a ground-kit change.
- **Asset changes, not done here:** the shoji gradient and the thinner lattice.
- CAM_Drum: the pavilion interior is still 42.9 % under luma 40 (interior shade).

## 2026-09-30 - ROUND 9 RESTORE of s1: round-9 s2 was judged worse, so the level goes back to the round-9 s1 (it4) look (DojoLab only; no Blender asset changes)

House rules kept:
- no MCP;
- one Unreal process at a time; none was running at the start (the stopped run's dj_sc_level.py commandlet had already
  exited), and none was left running;
- the runner guards checked that no DojoLab editor was open;
- the armory chat's Blender jobs, other chats' files and locks, DemoGame_1, the GASP sample and ArmoryLab were untouched;
- nothing committed.

The DojoKit lock (claude) was refreshed. The sun stays at the owner's 9.08 deg from the west (1730, Sun Yaw 268).

**Why:** the paired judge preferred s1 (it3) on warmth and mood: an orange-peach horizon, cream-peach sand, and no
white horizon puffs or posterised clouds. s2 won only on roof colour.

Folder: `unreal/round9/restore_s1/`.

### 1. Backup of the s2 state (restorable)
`restore_s1/start_backup/` holds the s2 state, with the same layout as the earlier backups (see its RESTORE.txt):
- L_Dojo.umap (md5 85c04fc0...);
- every DojoKit `*/Materials` folder, plus DojoKit/Materials;
- Config/*.ini and DojoLab.uproject;
- Scripts/dojo/showcase and Scripts/dojo/unreal (with the s2 look_r3.py);
- layout_showcase.json and blender_bounds.json.

### 2. Restore (method a, the code path)
- The backup `s2_work/start_backup` differed from the live scripts only in look_r3.py. Config, the uproject and every
  material file set were the same files; only the bytes differed.
- look_r3.py was cut back to its first 1264 lines. This drops the "ROUND 9 s2 (retune)" section and its "round 9 s2 it2"
  block, keeps CRLF, and matches the backup's copy line for line.
- Then: `run_showcase_unreal.sh prep materials level verify`.
  - prep: layout_showcase.json is **byte-identical** to the s1 backup's; blender_bounds.json is identical too.
  - materials: passed, 11 masters, 93 instances, 251 meshes, 0 errors.
  - level: passed, 1110 meshes, 24 markers, bounds max error 0.024 cm, 0 fails.
  - verify: **8 / 8 gates.**
- The 6_environment read-back is the it4 set, with no UDS mismatch:
  - bias 1.2;
  - Cloud Coverage 3.6, Contrast 0.6, Sky Light 2.8, Sun 4.0, Lighting Brightness 2.4;
  - Fog 2.0, falloff 0.2, fog tint (14, 2.8, 1.1);
  - Sun Source Angle Scale 3.0;
  - sun 9.08 deg.
- The new L_Dojo.umap md5 is 6598865e... A rebuild does not reproduce the backup's bytes (5b408dbc...), so the check was
  made on the read-back values and on the captures.
- Why method a, not a byte copy: the s2 run re-saved about 300 mesh assets that the backup does not hold. A code rebuild
  keeps the meshes, materials and level consistent.

### 3. Captures and CAM_Ref2Match against s1
- The 12 stills were captured with -game HighResShot, using the it3 cfg: `restore_s1/r9s1/`, 12 / 12.
- The sheets are `r9s1/REF2_vs_OURS.png` and `r9s1/COMPARE_R9S2_R9S1IT3_RESTORED.png` (r9 s2 | r9 s1 it3 | restored).
- **Noise floor:** a second capture of CAM_Ref2Match on the same level (`restore_s1/repeat/`) differs from the first by
  a mean |d| of 1.26, with 0.13 % of pixels over 12. The restored frame against it3 is 1.30 and 0.12 %.

| CAM_Ref2Match | it3 (judged s1) | restored | repeat | r9 s2 |
|---|---|---|---|---|
| under 40 / mean | 11.7 / 111.2 | 11.64 / 111.3 | 11.65 / 111.3 | 9.45 / 119.2 |
| p10 / p90 / clip | 35.2 / 160.4 / 0.23 | 35.4 / 160.5 / 0.23 | 35.4 / 160.5 / 0.23 | 41.4 / 168.9 / 0.17 |
| sand high-pass / luma std | 7.57 / 10.03 | 7.64 / 10.10 | 7.61 / 10.05 | 8.34 / 10.59 |
| horizon behind hall | (195, 146, 123) | (195, 146, 123) | same | (188, 158, 146) |
| top sky | (126, 84, 88) | (126, 84, 88) | same | (129, 108, 115) |
| sand near / far | (163, 125, 101) / (179, 143, 113) | same | same | (162, 136, 112) / (176, 150, 123) |
| plaster / gravel | (143, 105, 89) / (132, 94, 82) | same | same | (139, 115, 96) / (119, 97, 89) |
| timber | (70, 36, 18) | (69, 36, 18) | (69, 36, 18) | (74, 49, 31) |
| tiles lit | (92, 85, 84) R/B 1.09 | (92, 85, 88) R/B 1.04 | same | (86, 67, 70) |
| tiles shade | (37, 33, 41) R/B 0.90 | (37, 33, 44) R/B 0.84 | same | (42, 33, 39) |
| sky gaps / lit clouds (skym) | (133, 92, 96) / (167, 119, 101) | (134, 92, 96) / same | - | (131, 111, 119) / (175, 151, 133) |
| sand lit / shade | 1.294 | 1.293 | - | 1.22 |

- Every metric matches it3 within the repeat noise except the kawara, whose blue channel is up 3-4.
  - This is it4's own change: the tile tint blue 2.15 -> 2.28, the stopped run's "between it2 and it3" step.
  - it4 was built, but was never captured before this stage.
- The it4 shadow saturation 0.8 moved the timber by only 1 level.
- The other 11 cameras (`json/capture_health.json` against `capture_health_it3.json`):
  - the share under luma 40 is within 0.4 points of it3 and the means within 0.4;
  - the pixel diffs against it3 are 0.9-2.0 mean |d|.

### 4. Functional checks (fresh processes, final level)
- **Unreal verify: 8 / 8** (above).
- **UE alley** (`restore_s1/checks/ue/`):
  - replay: 32 / 32 CONTROLs blocked, 10 / 10 POSITIVEs clear, BR 30 / 30 with no mismatch;
  - flood: 0 alley cells, W and E;
  - pocket probes: 0 / 0 clear.
- **Blender** (`restore_s1/json/checks/`):
  - walk: PASS at r 0.30 and r 0.35;
  - climb: PASS;
  - the gate, hall, outbuilding, corridor, shed and pavilion roof walks, the clearance and the ground holes all pass;
  - every result JSON and every result line is identical to round 9 s2.
- No gameplay number, collision or 1v1 alley closure changed.

### Open
- **The kawara in the restored it4 read a touch bluer than it3.** In CAM_Ref2Match the shade is R/B 0.84 against ref
  2's 0.96. The judge saw it3's tiles as sage/teal in the mid and close views. s2's roof instance (Tint (0.85, 0.97, 1.3),
  MeanColour (0.045, 0.05, 0.072)) was the judge's one clear s2 win, and it is the obvious next single change to test on
  the s1 look.
- **Carried from s1 and the judge:**
  - X's ground-level upper sky is too dark and plum (top sky (126, 84, 88) against (166, 147, 148));
  - coarse rake with moire;
  - the gravel strip where ref 2 has granite slabs, which waits for the stone study;
  - the hard building shadow on the foreground sand (the owner's 9 deg sun);
  - the exposure is darker overall.

## LANDSCAPE ROUND - FX assets stage (2026-09-30)

Blender only, no Unreal. Lock `DojoFX`. Full notes: `WorkFiles/dojo/build/fx/BUILD_NOTES.md`. Unreal recipe:
`WorkFiles/dojo/build/fx/fx_catalog.json`. Assets: `Exports/DojoKit/FX/` (README).

- **Petals.**
  - Seven meshes: `SM_DKF_Petal_A`-`F` (the sheet's six petals: flat, cupped, curled, folded) and `SM_DKF_PetalOld_A`
    (browned).
  - Each is 56-84 triangles, two-sided masked, 12.5-14.5 mm long.
  - `qa_check` passes on all seven.
  - Three fallen drift clusters, `SM_DKF_PetalDrift_A`-`C`, with about 1 in 8 old petals. They fail only
    `uv_no_overlap`, which is by design (shared UV0).
  - The texture sets are Petal (front + back BC, N, ORM, SSS) and PetalOld.
  - `T_DKF_PetalScatter_*` is a 2x2 decal atlas.
  - Measured against the sheet:
    - W/L 0.730 against 0.717;
    - notch 0.077 against 0.075;
    - front band colours within about 8 sRGB levels.
- **River FX.**
  - Six-way flipbooks (8x8, 4096): `MistPuff`, `MistWisp` and `SprayBurst`.
  - The spray is a Mantaflow surge-into-boulder sim, a method change after the point-sprite spray failed.
  - Also `T_DKF_Haze_M` (2048 x 1024) and a tileable `T_DKF_Foam_M` / `_N` (2048) for the Water river material.
  - All colour-neutral.
  - Texture QA: all 21 maps PASS (power of two, colour space by suffix, alpha, normals).
- **Open:**
  - the mist cores read darker than their rims under a single key, and the puff is too opaque. The next step is a
    seventh ambient pass and a lower density;
  - there is no dedicated rising-plume flipbook;
  - the spray edge is harder and more gel-like than the sheet's foamy splash;
  - these previews are Blender stand-ins: judge in Unreal under the UDS sun.

## LANDSCAPE ROUND - world build stage in DojoLab (2026-09-30)

Followed `landscape/plan/LANDSCAPE_PLAN.md`. Output folder: `WorkFiles/dojo/build/landscape/world/`. Code is in
`Scripts/dojo/landscape/`.

House rules kept:
- no MCP tools;
- one Unreal process on DojoLab at a time, and one commandlet machine-wide (the `tools/run_ue.sh` guards);
- no DojoLab editor was open;
- DemoGame_1, the GASP sample, ArmoryLab and every content source were only read;
- owned content was FILE-COPIED (never migrated);
- no downloads;
- nothing was committed;
- the armory chat was left alone.

The sunset is unchanged: UDS 1730, sun at 9.08 deg from the west, the round-9 restore_s1 values.

### Backups
- `world/start_backup/`: L_Dojo.umap (md5 6598865e, the round-9 restore_s1 level), Config, uproject, every
  dojo/unreal and showcase script, layout_showcase.json and blender_bounds.json. `MD5.txt` is in the folder.
- `world/backup_pre_world/`: L_Dojo after the town removal (md5 f42a3e30), plus the config.
- **Final L_Dojo md5: 87a2d1b5** (448 MB; the two 2017 x 2017 landscapes make up most of it).

### 1. Water plugin
- `"Water"` is enabled in DojoLab.uproject. Its dependencies (Landmass, Niagara, GeometryProcessing,
  BlueprintMaterialTextureNodes) load with it.
- First load: 0 errors (`json/probe_api.json`).

### 2. Town removed
`Scripts/dojo/landscape/apply_landscape.py` is a new prep patch, chained into `run_showcase_unreal.sh prep`.
- It removed 338 instances: Outside/Street 237, Town 42, Ground 4, Far 6, and 49 modern props outside the walls
  (poles, wires, the street lamps and their 2 lights).
- It also dropped the WornPath_07 road decal and the 22 old tree_slots.
- The two SM_DGB_Tree are now hidden in game but keep their trunk hull. These hulls are the CS01/CS02 collision.
- Instances keep their indices, so every label and every check name is unchanged. The assets stay on disk.
- `dj_sc_level.py` and `dj_sc_verify.py` were patched to:
  - skip removed instances;
  - check that removed instances are absent;
  - gate the world-build actors (tag DJ_Landscape) separately, in `dj_ls_verify.py`.
- Result: 772 compound meshes, bounds max error 0.0008 cm.

### 3. Our assets imported (`dj_ls_import.py`; 136 meshes and 65 textures, 0 errors)
**Stone kit (104 SM_DKT, f3)**
- Legacy FBX import, UCX convex hulls, vertex colours set to Replace.
- Nanite as the catalogue says, ShapePreservation NONE, fallback RELATIVE_ERROR 1.0 (STONE study 5.2).
- Sidecar applied on the LOD pieces.

**Stone kit material instances, measured mid-grey (`stone_tone.py`, `json/stone_tone.json`)**
- Albedo through the Lib_Opaque maths. The f3 catalogue tone measured sRGB (106, 100, 94), saturation 0.116,
  R/B 1.13 (the tan).
- The UE MIs measure: WallGranite (124, 118, 113), saturation 0.082, R/B 1.09. Every slot is at saturation 0.08 and
  R/B 1.09, with the step and riser ladder kept.
- Moss comes from the Wear alpha.

**Pines (SM_DKN, v2f)**
- Nanite throughout. Trunks, rocks and mounds use ShapePreservation NONE. Foliage uses VOXELIZE with lerp_u_vs
  False.
- PP2 textures: PivotPos HDR and XVector VectorDisplacement, both Nearest, no mips.
- New masters:
  - M_DKN_Bark: UV2 unique AO, vertex G moss.
  - M_DKN_Needle: Two Sided Foliage. PP2 wind rotates each pad about its pivot, weighted by vertex R. Flutter comes
    from vertex B. Max WPO is 6 cm.
  - M_DKN_RockUnique.
- Foliage components: WPO disable distance 5000 cm, Rigid shadow cache, NoCollision.

**FX** (meshes, textures and a petal MI) are imported for the FX stage.

### 4. Owned content copied (`copy_owned.py`)
- 200 files (996 MB). Each pack keeps its /Game path, and the copy follows each pack's dependency closure.
- Fishermans_Cabin: firs and billboard, bushes, grass, rocks, small rocks, mountain, tiling ground and rock 4K.
- Scenery_Tutorial: Megascans surfaces, T_MacroVariation, T_NoiseMask, T_Land_Mountain01/02 and Erosion00/01.
- Megaplants: Tree_Japanese_Cypress_01 A-G.
- **Not copied:** NiagaraExamples FX_Fog. Its packages reference the plugin mount /NiagaraExamples, so a /Game copy
  cannot resolve.
- **Changed in our copies only:** the 8 SM_Fir_Tree meshes now use Nanite VOXELIZE (plan 3.11). The VaultCache
  source is untouched.

### 5. World (`make_terrain.py` + `make_world_layout.py` produce the data; `dj_ls_world.py` builds it)
**Landscape tool**
- The UE 5.8 Python API cannot create landscape components. A small editor plugin does this,
  `Scripts/dojo/unreal/DojoLandscapeTools` (ALandscapeProxy::Import, as New Landscape does).
- It is built with RunUAT BuildPlugin and installed in DojoLab ONLY while `tools/run_world.sh` runs, then removed.
  The level references nothing from it.
- `landscape.Nanite.MultithreadBuild 0` makes the Nanite build finish inside the commandlet.

**Two landscapes, both Nanite (256 components each)**
- **LS_Valley:** 2017^2 vertices at 0.5 m, centre (22, 18). It is built in this order:
  1. valley walls from the river (the far bank +2/+5/+20 at x 70/85/130), the north hill and the west ridge;
  2. the C1 cliff;
  3. the wall-foot ground (clamped to at least the water level + 0.4);
  4. the channel carve;
  5. the stair corridor;
  6. the pads: terrace 0, forecourt -0.5, -0.30 under the compound.

  Bank and hill relief come from the owned Erosion00 stamp.
- **LS_Far:** 16 km at 8 m. It carries ridges M1/M2/F and the two peaks. The peaks come from the owned stamp
  T_Land_Mountain02 (rotated, mirrored, raised to the power 1.6), which is plan option B.
  - Peak A summit: 2057 m (plan 2078).
  - Peak B summit: 1980 m (plan 2006).
  - LS_Far sits 30 m under the valley inside the valley's footprint.
- Valley probes traced against the heightmap: max error 0.03 cm.

**Materials**
- M_DJL_Valley: world-mask layers (T_DJL_ValleyMask 2048: dirt, forest floor, moss, river bed) plus slope rock.
  Owned textures only; shared samplers. A canopy colour blends in beyond 130-320 m.
- M_DJL_Far: forest canopy, rock and meadow, plus the height + slope snow blend (snow line 1120 m).

**Ishigaki: 36 SM_DKT wall pieces**
- WR1, plus a short WR1b (the forecourt's west drop), WR2, WR3, WR4, WR5 (H6, then H4, then H3, ending in EndR into
  the hill), and the forecourt step course.
- Deviation, measured on the kit's snaps: WR2 is at y -8.0, not the plan's -7.6. The CornerOut arm plus a 2 m module
  plus the CornerIn arm put WR4's face exactly on y -3.0. The WR3/WR4 junction uses CornerIn_H6.

**Stair path: 78 kit pieces**
- 7 flights + the 2 gate flights, 9 landings / paths, 22 cheeks, 16 kerbs, 18 rail pieces.
- 6 lanterns, each with a point light at 2550 K. Lanterns stand on the cliff side, which is the kit's own rule.

**River: one WaterBodyRiver**
- 222 points, 1.31 km (plan R0-R11 plus one extension point at each end so the water does not stop in view).
- Per-point width and depth; a WaterZone; affects_landscape off (the channel is carved in the heightmap).
- MI_DJL_River is turquoise.
- The rapids velocities are doubled (520-750 cm/s). The engine material showed no foam at 250-350 cm/s.
- **White water:** 17 foam strips over R4-R7 (M_DJL_RapidsFoam: the engine's T_WaterFlow_01 foam panning
  downstream, broken up by our T_DKF_Foam_M).
- A low Local Fog Volume sits over the rapids (44 x 18 x 4 m, extinction 0.03 / 0.08). The first build was a white
  wall.

**Rocks: 80 owned Fishermans rocks** (MI_DJL_Rocks_Granite, with the RVT blend switched off; with it on, the rocks
rendered sRGB 0, 0, 0)
- 21 hero targets from the plan;
- 9 rapids stones;
- 9 bank boulders;
- 13 cliff-face chunks;
- 8 cliff-top rocks;
- 16 edge boulders;
- 4 bed slabs.

**Trees and cover**
- Pines P01-P08: 26 actors (trunk, foliage, rock, mound).
- 5 Megaplants cypress behind the hall.
- Firs as ISMs, 1699 in all:
  - FZ1: 407;
  - FZ2: 316 (56 dropped by the sun corridor);
  - FZ3: 944;
  - FZ3b far bank: 32.

  Their leaves use the child MI_DJL_FirLeaves (the pack's warm Color Multiply read yellow).
- 53,450 fir billboards on the far hills.
- 2511 grass, 85 bushes, 420 pebbles.

**Markers and blockers**
- 20 CherrySlots: hidden cylinders, sized height x canopy, no collision, tags CherrySlot / <id> / CherrySlotFX. No
  cherry was imported.
- Boundary_1v1 B1-B8: hidden cubes, 6 m tall, Pawn-only, tags Boundary_1v1 + TerraceEdge + Dojo/Boundary_1v1. The
  BR drops them.
- 3 mist FX anchors.
- 4 SM_Mountain_01 far-ridge masses using MI_DJL_Mountain (the snow material).
- 6 new cameras.

**Sun corridor (the it6 measure found the regression)**
- The plan's west ridge (+18 m at x -80) and the FZ2 firs blocked the owner's 9 deg west sun. CAM_Ref2Match fell to
  mean luma 79.
- Fix:
  - the ridge stays under 0.12 x its distance;
  - the near-bank ground in the corridor is capped;
  - every tree that would cut the sun ray is dropped.
- Result: terrain-only sun reaches 100 % of 98 sand points.

### 6. Checks (fresh processes, final level 87a2d1b5)
- **Showcase verify: 8/8.**
  - 772 meshes;
  - GASP trace 23/23;
  - decals 85/85;
  - 8 lamps;
  - UDS read-back equal to restore_s1.
- **dj_ls_verify: 6/6.**
  - L1: landscapes 256 components, Nanite on, probes within 0.03 cm.
  - L2: every actor and every ISM count.
  - L3: B1-B8 hidden and Pawn-only, 20/20 slots, 28/28 thin uprights, foliage NoCollision with 5000 cm WPO.
  - L4: river and zone.
  - L5: GASP capsule stair walk.
    - BR_stair_path_river_landing_to_gate and its reverse are CLEAR. Max step 10 cm, min floor normal z 0.895 (the
      limit is 0.71).
    - The 1v1 CONTROL is stopped by B3.
  - L6: every B-line CONTROL hits its own blocker with the ring ignored, and passes in BR mode.
- **UE alley (copies in `world/checks/ue/`):** replay 32/32 CONTROLs blocked and 10/10 POSITIVEs clear, BR 30/30
  with no mismatch; flood 0 alley cells; pocket probes 0 / 0.
- **Blender (`world/checks/blender/`):**
  - walk 47 routes, PASS at r 0.30 and r 0.35;
  - climb PASS;
  - all roof walks, clearance and ground holes are identical to round-9 restore_s1. The walk and climb JSON are equal
    in content to the git checkpoint.
- BR_road_onto_the_gate_apron is retired with the road, as the plan says. It still passes in the Blender blend, which
  keeps the road.

### 7. Captures
-game HighResShot, iterations it2-it10 in `caps/itN`. The final set (it10) is in `caps/`:
- CAM_LandscapeRef at 1280 x 1920 (2:3, like the reference);
- CAM_RiverRapids, CAM_StairPath, CAM_TerraceWall, CAM_FromGateOut, CAM_Overview, CAM_PlayerEyeSand and
  CAM_PeaksOverHall at 1920 x 1080;
- CAM_Ref2Match at 1920 x 1440;
- LANDSCAPE_vs_OURS.png and REF2_vs_OURS.png.

Numbers are in `caps/json/`.

**CAM_LandscapeRef against the reference** (1024 x 1536, matched framing)

| Metric | Reference (day) | Ours (sunset) |
|---|---|---|
| Share under luma 40 | 8.95 % | 26.96 % |
| Mean | 140.4 | 73.1 |
| p10 | 42.3 | 22.5 |
| p90 | 232.3 | 133.3 |

Region medians, sRGB (reference -> ours):

| Region | Reference | Ours |
|---|---|---|
| Sky | (150, 186, 224) | (114, 77, 85) |
| Peaks | (221, 230, 240) | (162, 118, 112) |
| Forest slopes | (141, 166, 195) | (117, 79, 23) |
| River water | (106, 114, 121) | (11, 45, 42) |
| Foam | (176, 194, 206) | (71, 85, 78) |
| Terrace wall | (137, 119, 91) | (74, 44, 34) |
| Compound | (145, 116, 96) | (102, 72, 49) |

The reference is daytime, so the difference is mostly the kept sunset.

**Peaks**
- Summit A at (348, 460) against the plan's (350, 457): 3.6 px.
- Summit B at (566, 496) against (567, 493): 3.2 px.
- Snow luma: A 126 and B 185, against 113 for the sky beside A.

**Foam:** 13 % of the water in the rapids boxes, against the plan's target of 25-45 % (the reference box reads 80 %).
NOT met.

**Stone against the owned rock** (CAM_TerraceWall):
- lit wall against rock A: dE76 2.5;
- shaded wall against rock B: dE76 1.8.

The rock is still the pack's tan.

**CAM_Ref2Match (courtyard), round-9 restore_s1 -> landscape**
- The sand is sunlit again: near (163, 125, 101) -> (166, 131, 105); far (179, 143, 113) -> (179, 146, 118).
- Plaster, gravel, timber, shoji and lanterns are all within a few levels.
- Share under luma 40 went from 11.6 % to 22.2 %, and the mean from 111 to 95. The cause is the background: dark
  forest and hills now fill the old sky and town band.
- The tiles read bluer: lit R/B 1.04 -> 0.79. The captured sky light now sees the valley. This is for the lighting
  stage.

### Open
- **Foam** is under target. The reference's boulder-choked white water needs:
  - the FX stage's spray and mist;
  - more and bigger emergent boulders. The owned Fishermans rocks are the only ones available: gap 1 in the plan.
- **The far bank** still reads as a smooth tan grass levee (the cherry row is on hold). Wanted:
  - rounded granite boulders (gap 1);
  - the cherries.
- **Mid hills** carry billboards with tan grass or forest floor between them. The canopy blend is subtle at sunset.
- **Megaplants cypress:** a RENDERING commandlet that loads a level already holding them asserts on a worker thread
  (ShowFlags IsInGameThread). `run_world.sh` clears the world in a null-RHI process first. The -game and null-RHI
  loads are fine.
- Placing a water body after a landscape exists makes WaterEditor run LandscapeEditor UI code, which asserts in a
  commandlet. The water is therefore built before the landscapes.
- Water velocity in the rapids is a visual 520-750 cm/s. If BR swimming ever uses the water current, re-check it.
- Not measured: GPU frame time with the forest. There are 55k ISM instances (1.7k Nanite voxel firs plus
  billboards). Next: the perf verify.
- The plan's Boundary_World at the map edge is still the owner's call. P09/P10 were not placed (optional).

## LANDSCAPE ROUND - FX + LIGHTING stage in DojoLab (2026-09-30)

Output folder: `WorkFiles/dojo/build/landscape/fxlight/`. Code: `Scripts/dojo/landscape/dj_fxl_assets.py`,
`dj_fxl_place.py`, `dj_fxl_verify.py`, `measure_fxlight.py`; the editor helper `Scripts/dojo/unreal/DojoFXTools`; the
look in `Scripts/dojo/showcase/look_r3.py` (section "LANDSCAPE ROUND: FX + LIGHTING" and its it2 block).

House rules kept:
- no MCP tools; headless Blender only (the functional checks);
- one Unreal process at a time and one commandlet machine-wide (the runners wait on any UnrealEditor-Cmd and stop if a
  DojoLab editor is open); none was left running;
- DemoGame_1, the GASP sample, ArmoryLab and every content source were only read; no Migrate, no downloads;
- `DojoFXTools` is installed into `DojoLab/Plugins` only while an FX step runs (`fxlight/tools/run_fx.sh`), then removed
  (the Plugins folder is gone again); nothing references it;
- nothing in `Scripts/unreal/materials` was touched; the other chats' files, locks and processes were left alone;
- nothing was committed. The DojoKit lock (claude) was refreshed.

The sunset is kept: UDS Time of Day 1730, Sun Yaw 268, sun 9.08 deg from the west (the read-back is unchanged).

### Backups
- `fxlight/start_backup/` (before any write): L_Dojo.umap md5 87a2d1b5 (the world-stage final), Config/*.ini, the
  uproject, `materials.tar` (every DojoKit / DojoLandscape Materials folder + DojoKit/Showcase), `scripts/scripts.tar`
  (Scripts/dojo/{unreal,showcase,landscape}, layout_showcase.json, world_layout.json). See RESTORE.txt.
- `fxlight/backup_pre_light/`: L_Dojo after the FX placement, before the lighting build (md5 d7078859).
- **Final L_Dojo md5: 7d73c3a4.**

### 1. FX (from our DojoFX assets; recipe fx/fx_catalog.json)
**Method.** UE 5.8's Python cannot edit Niagara emitters (the lightweight emitter, its modules and the distribution
structs are not exposed). `DojoFXTools` adds generic reflection get/set (ExportText / ImportText by property path), a
renderer swap and a system finalise + compile. Each system is a copy of the engine template
`/Niagara/DefaultAssets/Templates/Systems/FountainLightweight` (one lightweight / stateless emitter: no per-particle
state, evaluated on the GPU, no CPU sim), every module's enable flag and values written explicitly.

**Materials** (`/Game/DojoKit/FX/Materials`):
- `M_DKF_SixWayMist`: lit translucent sprite (volumetric per-vertex non-directional); both six-way maps through SubUV
  (8 x 8, blended); key = the catalog's six-way formula with the UDS sun direction (written at build time from the
  layout sun: the time is locked) in the camera basis; the engine's translucency lighting gives the colour and the
  exposure; depth fade. MIs: MistPuff (opacity 0.25), MistWisp (0.22), SprayBurst (0.6).
- `M_DKF_HazeSprite` + MI_DKF_RiverHaze (0.55); `M_DKF_Droplet`; `M_DKF_PetalScatterDecal` + MI cells 0-3 (DBuffer
  decal, 2 x 2 atlas cell per MI); `M_DKF_FoamWake` + MI_DKF_FoamWake (0.95) / MI_DKF_FoamWakeSoft (0.5).
- M_DKF_Petal: Niagara mesh particle + instanced static mesh usage confirmed on (read back).

**Systems** (`/Game/DojoKit/FX/Niagara`):

| System | Renderer | Spawn per actor | Life | Notes |
|---|---|---|---|---|
| NS_DKF_PetalDrift | mesh: Petal_A-F + PetalOld_A (weight 0.45) | 26-34 /s, 60 x 60 x 10 m box 6-16 m up | 10-14 s | gravity + drag 6 (fall ~0.95 m/s), wind 110 cm/s W->E as an acceleration, curl noise, tumble 300-420 deg/s, real scale 1.0-1.4; shrink over the last 15 % (stateless: no collision) |
| NS_DKF_PetalCanopy | same | 2-5 /s, 3 m sphere | 7-10 s | one per CherrySlot |
| NS_DKF_MistPuff | MI_DKF_MistPuff, 8 x 8 SubUV | 2-4 /s | 4-7 s | 4.2-9.8 m sprites (1.4 x the mist width), rise + down-stream |
| NS_DKF_MistWisp | MI_DKF_MistWisp | 1-2 /s | 6-10 s | (11-20) x (6-10) m |
| NS_DKF_RapidSpray | MI_DKF_SprayBurst | 0.55-1.25 /s | 0.64-0.9 s | 1.0-1.8 m (the catalog's 1.5-3 m read as white cut-outs from above), pivot (0.5, 0.96) |
| NS_DKF_SprayDroplets | MI_DKF_Droplet, velocity-aligned | 50-90 /s | 0.6-0.9 s | cone 35 deg, 250-450 cm/s, gravity |
| NS_DKF_RiverHaze | MI_DKF_RiverHaze, Z-locked | 0.12-0.2 /s | 25-40 s | 20-40 x 8-12 m |

**Placement** (`dj_fxl_place.py`, tag DJ_FXL; re-run safe; the showcase level step and the world step never touch it):
- Petal drift over the courtyard / terrace and over the cliff stair (active).
- NS_DKF_PetalCanopy on all 20 CherrySlots at 0.6 x the slot height, tags CherrySlotFX + the slot id. Active now:
  CS01, CS02 (the courtyard pair), CS03, CS04 (west strip) and CS09 (cliff top over the stair). The other 15 are placed
  with auto-activate off, ready for the cherries.
- Fallen petals under every slot canopy (line traces; sand, water, roofs, walls and slopes steeper than ~45 deg are
  skipped): 140 scatter decals and 59 SM_DKF_PetalDrift clusters, NoCollision, shadowless. The two courtyard tree
  beds (Bed_Tree W / E) now carry them.
- River: only boulders that reach the water level get white water. The world stage's Rapids_01-09 stones all sit
  0.15-0.3 m UNDER the surface (measured from the actor bounds), so: 7 emergent boulders get spray + droplets + a dense
  wake; 16 pour-over stones get a soft wake only (a splash sheet on a hidden stone read as a white bird on open water);
  16 mist puffs (3 anchors + boulders >= 1.4 m), 6 wisps along the fast reach, 15 haze sheets.
- Totals: 73 Niagara actors, 82 static meshes, 140 decals.

**Particle budget.** The estimated steady count of the active emitters (rate x mean life) is about 1654:
- petal drift 720;
- droplets 368;
- mist puffs 264;
- canopy 149;
- haze 77;
- wisps 72;
- spray 5.

The cap is 6000.

**GPU cost** (`checks/perf/`). Same-session -game A/B, 1920 x 1080, scalability 3; frame time mean, FX on against FX
hidden:
- CAM_RiverRapids: 19.69 against 17.24 ms (+2.45; translucent mist close to the camera);
- CAM_PlayerEyeSand: 13.48 against 13.02 (+0.46);
- CAM_LandscapeRef: 9.11 against 8.41 (+0.70).

The full perf table is `checks/perf/perf_summary.md`.
- **Finding:** since verify_r9, ShadowDepths has grown from 0.68 ms to 2.5-8 ms (PlayerEyeSand GPU 7.1 -> 12.4 ms;
  RiverRapids 19.3 ms is over 16.7).
- That growth comes from the world build (forest, landscapes, cypress), not from the FX. The FX cast no shadows (the
  renderers and components are off, the meshes are shadowless).

### 2. Lighting rebalance (look_r3.py; -game probes `fxlight/probe/pa..pf`, measured)
Probe pe froze the clouds (Cloud Speed 0). Earlier probes showed the cloud drift alone moves the sky reads by up to 25
luma.
- **Upper sky.** The cloud ambient / dark colour and the Rayleigh colour (set at runtime) left the sky gaps unchanged
  (pe E0 -> E1 / E3: the LandscapeRef top band stayed at 41 luma). The lift comes from the post:
  - film toe 0.72 -> 0.64;
  - local-exposure shadow contrast 1.0 -> 0.85.

  Final top band: (85, 62, 70), luma 67.5, hue 339, s 0.16. Before it was (55, 31, 42) / luma 41 / hue 332 / s 0.28
  (about +0.6 EV and less red).
- **Valley haze.** Fog tint (14, 2.8, 1.1) -> (12, 3.0, 1.35) at Fog 2.2. The forest-slope box went from orange
  (137, 93, 24) s 0.70 to (116, 92, 45) s 0.44. The peaks keep a warm rim: (158, 124, 120).
- **Cloud ambient.** Ambient (1.2, 1.1, 1.4) and dark colour (0.15, 0.14, 0.2). This cools the captured sky light, and
  that is what lets the kawara read neutral with a near-neutral albedo.
- **Sand.** Saturation 0.58 (against the sky light), value 0.88 -> 0.98 (+0.15 EV).
  - Rake: a new `NormalStrength` in the ground master (`dj_sc_materials.build_ground`; default 1, so every other ground
    is unchanged), set to 3.0 on the raked sand, with NormalVar 0.35 -> 0.15.
- **Timber.** Value 1.35, saturation 0.42, tint (1, 0.84, 0.7).
- **Shoji.** x 0.55, tint (1, 0.6, 0.32); the clerestory band with it.
- **Lantern glass.** x 0.8, saturation 0.9, tint (1, 0.5, 0.22); the tall stone lanterns' lights x 0.85.
- **Kawara.** The flatten target (80 % of the colour) is a neutral lavender-charcoal: MeanColour (0.05, 0.057, 0.074),
  Tint (1.5, 1.3, 1.4), value 2.6.
- **Plaster / gravel.** Saturation 0.16 / 0.5.
- **Grey-box tree cylinders.** The two SM_DGB_Tree are hidden in game, with their trunk hulls kept for CS01 / CS02.
  Their box centres (3.5, 16) and (40.5, 16) are exactly CherrySlots CS01 / CS02. Those now carry the canopy petal
  emitters and the fallen petals on the tree beds. No grey-box cylinder shows in CAM_Overview or CAM_EastYard.

**CAM_Ref2Match against ref 2** (round 9's measure_r8 boxes; world stage -> final, with ref 2 last):

| Metric | World stage | Final | Ref 2 |
|---|---|---|---|
| Share under luma 40 | 22.4 % | 13.3 % | 13.7 % |
| Mean | 94.8 | 104.4 | 107.9 |
| p10 / p90 | - | 33.1 / 159.4 | 34.4 / 171.1 |
| Sand near | (165, 129, 102) R/B 1.62 s 0.26 | (168, 138, 118) R/B 1.42 s 0.22 | (182, 148, 125) R/B 1.46 s 0.28 |
| Sand high-pass | 7.7 | 9.1 | 11.7 |
| Timber | (66, 36, 19) R/B 3.5 | (78, 52, 38) R/B 2.05 | (75, 49, 30) R/B 2.5 |
| Tiles lit | (61, 64, 77) R/B 0.79 | (99, 84, 100) R/B 0.99 | (91, 84, 94) R/B 0.97 |
| Tiles shade | - | (57, 50, 65) R/B 0.88 | (43, 39, 45) R/B 0.96 |
| Shoji | (214, 139, 50) R/B 4.3 | (193, 118, 56) R/B 3.45 | (182, 118, 53) R/B 3.43 |
| Lantern | - | (233, 181, 107) s 0.74 | (241, 180, 90) s 0.84 |
| Plaster / gravel R/B | - | 1.27 / 1.27 | 1.40 / 1.43 |

**CU_HallUpperRoof tiles:** lit (123, 109, 123) R/B 1.0, shade (70, 64, 82). Lavender-charcoal; no sage, G < R.

**CAM_Drum:**
- near-black (luma < 10) 35 % (probe base) -> 20.3 %;
- share under 40: 65 % -> 46 %.

**CAM_HallVeranda:** near-black 26 % -> 9.8 %.

### 3. Functional checks (fresh processes, final level 7d73c3a4; copies in `fxlight/checks/`)
- **Showcase verify: 8 / 8.**
  - `dj_sc_verify.py` now leaves the DJ_FXL actors to dj_fxl_verify, as it does the DJ_Landscape ones (two filters).
  - 772 compound meshes; bounds max error 0.0008 cm; GASP trace and decals pass; the UDS read-back matches look_r3.
- **dj_ls_verify: 6 / 6** (stair walk, B-lines, collision).
- **dj_fxl_verify: 4 / 4:**
  - F1: 7 systems, petal scale 1.0-1.4;
  - F2: 295 actors; every static mesh NoCollision and shadowless; 20 / 20 slot emitters, active exactly on the 5 slots;
  - F3: materials;
  - F4: budget.
- **UE alley:**
  - replay 32 / 32 CONTROLs blocked and 10 / 10 POSITIVEs clear, BR 30 / 30 with no mismatch;
  - flood 0 alley cells;
  - pocket probes 0 / 0.

  All identical to the world stage. One pocket-probe profile names another actor at an equal-height seam (EndGable
  floor against the Veranda); it is still clear.
- **Blender** (headless, the world stage's runner): walk (r 0.30 / 0.35), climb and every roof walk PASS. Clearance,
  ground holes, corridor and roof JSONs are identical in content to the world stage.
- **layout_showcase.json** differs from the stage start only in materials, the round3 look record and the two tall
  lantern candelas. Instances, collision classes, markers, routes and player starts are identical. No gameplay number,
  collision, GASP marker, 1v1 closure or Boundary_1v1 changed.

### 4. Captures (`fxlight/caps/`, -game HighResShot; iterations it1-it4; the final set = it4)
- CAM_LandscapeRef 1280 x 1920;
- CAM_RiverRapids, CAM_StairPath, CAM_TerraceWall, CAM_FromGateOut, CAM_Overview, CAM_PlayerEyeSand,
  CAM_PeaksOverHall 1920 x 1080;
- CAM_Ref2Match 1920 x 1440;
- extras: CAM_Drum, CAM_HallVeranda, CU_HallUpperRoof, CU_Lantern, CAM_EastYard, CU_SandEye, CU_Training;
- LANDSCAPE_vs_OURS.png, REF2_vs_OURS.png, BEFORE_AFTER.jpg (world stage | final, 8 cameras).

Numbers are in `caps/json/fxl_measure.json` and `measure_landscape.json`.

**CAM_LandscapeRef** (reference day -> world stage -> final):
- share under 40: 8.95 % -> 26.96 % -> 7.85 %;
- mean: 140.4 -> 73.1 -> 87.6;
- p10 / p90: 42.3 / 232.3 -> 22.5 / 133.3 -> 43.3 / 138.3.

Foam: 79.9 % (reference) -> 13.1 % (world stage) -> 32.9 % (final). The plan's target band is 25-45 %; met.

Region medians (reference -> final):

| Region | Reference | Final |
|---|---|---|
| Sky | (150, 186, 224) | (109, 83, 91) |
| Peaks | (221, 230, 240) | (158, 124, 120) |
| Forest slopes | (141, 166, 195) | (116, 92, 45) |
| River water | (106, 114, 121) | (56, 77, 76) |
| Foam | (176, 194, 206) | (126, 114, 108) |
| Terrace wall | (137, 119, 91) | (91, 67, 61) |
| Compound | (145, 116, 96) | (113, 85, 68) |

The reference is daytime.

**Health per camera** (share under 40 / mean, world stage -> final):

| Camera | World stage | Final |
|---|---|---|
| CAM_RiverRapids | 21.9 / 82.6 | 1.6 / 105.7 |
| CAM_StairPath | 48.5 / 49.9 | 20.7 / 65.8 |
| CAM_TerraceWall | 36.6 / 100.1 | 8.4 / 122.8 |
| CAM_FromGateOut | 14.4 / 107.4 | 7.3 / 115.7 |
| CAM_Overview | 33.9 / 72.9 | 12.2 / 87.5 |
| CAM_PlayerEyeSand | 29.6 / 84.6 | 21.0 / 92.7 |

### Rejected deltas
None. No judge ran in this stage. Petal scale follows the brief (real 12-15 mm), not the sheet.

### Open
- **Petals at real scale are sub-pixel beyond a few metres.** A x25 render test (`probe/pf`, never kept) proved the
  systems emit, tumble and drift. At 1.0-1.4 they barely read in the gameplay views. Legible petals need about 3-4 x;
  that is the owner's call.
- **The rapids stones are submerged** (top 0.15-0.3 m under the water). Only 7 boulders break the surface. Raising them
  or adding bigger rounded boulders is a world / asset job (gap 1). It would let the splashes, which are now
  restricted, run on the whole reach.
- **Mist cost at the water** (+2.45 ms at CAM_RiverRapids). The river view is already 17 ms without FX (ShadowDepths
  8 ms from the world build). Next steps:
  - mist sprites camera-distance fade or fewer puffs on Medium / Low;
  - a shadow-cost pass on the world (VSM invalidation from the WPO foliage, cypress).
- **Sky.** The sky gaps stay plum-lavender (hue 339). The UDS sky colour knobs did not move them at runtime; a
  construction-time test of Rayleigh / sky-atmosphere values is the next lever.
- **Far bank.** It still reads as smooth tan grass (M_DJL_Valley, the cherry row). Not touched here.
- **The six-way mist uses a fixed sun direction**, valid while the time is locked. A time-of-day change needs the MPC
  path from the catalog.
- **Plaster / gravel** read a touch cool against ref 2 (R/B 1.27 against 1.40 / 1.43).

## LANDSCAPE ROUND - LANDSCAPE FIX stage in DojoLab (2026-09-30 / 10-01): the judge's 5 blockers and 13 deltas

Output folder: `WorkFiles/dojo/build/landscape/fix/`. Start state: the FX + LIGHTING stage final (L_Dojo md5 7d73c3a4).

**Code changed.** Every change is commented "fix round" in place.
- `Scripts/dojo/landscape/{ls_geo, make_terrain, make_world_layout, dj_ls_world, dj_ls_materials, dj_fxl_place,
  dj_fxl_verify, dj_ls_verify}.py`.
- A LANDSCAPE FIX ROUND block at the end of `Scripts/dojo/showcase/look_r3.py`.

**New tools in `fix/tools/`.**
- Runners: `run_ue.sh`, `run_world.sh`, `run_fx.sh`, `capture.sh`, `iterate.sh`, `run_checks.sh`.
- Measurers: `measure_fix.py`, `peak_silhouette.py`, `proj.py`, `terrain_look.py`.
- Read-only probes: `probe_fir.py`, `export_foam.py`.

House rules kept:
- no MCP tools; headless Blender only (the checks);
- one Unreal process on DojoLab at a time and one commandlet machine-wide. Every runner waits on any UnrealEditor-Cmd and
  stops if a DojoLab editor is open; none was open;
- DemoGame_1, the GASP sample, ArmoryLab and every content source were only read;
- no Migrate, no downloads, and no new owned content copied: everything placed was already in DojoLab;
- nothing in `Scripts/unreal/materials`; no other chat's files, locks or processes were touched;
- nothing was committed.

The plugins (DojoLandscapeTools / DojoFXTools) were installed only for their steps and then removed; DojoLab/Plugins is
gone. One slip: a typo in the first `run_fx.sh` left the DojoFXTools copy in place for about a minute, with no Unreal
process running. It was removed by hand and the runner was fixed. The DojoKit lock (claude) was refreshed.

The sunset is kept: UDS 1730, sun 9.08 deg from the west. The UDS sky, fog and exposure values are untouched.

### Backups
- `fix/start_backup/`, taken before any write (see RESTORE.txt):
  - L_Dojo.umap (md5 7d73c3a4);
  - Config/*.ini and the uproject;
  - `materials.tar`: DojoLandscape and the DojoKit material / FX folders;
  - `scripts/scripts.tar`: Scripts/dojo/{unreal,showcase,landscape}, layout_showcase.json, world_layout.json, the
    terrain r16 / npy / mask and fxlight/json;
  - `world_json/`.
- **Final L_Dojo md5: bf999fc9** (411 MB).

### Rejected and deferred deltas (judge-steer rule: I looked at the reference first)
- **Rejected (delta 4, part): "posterized cloud banding with 8-bit steps".**
  - Measured: the raw stills are smooth. CAM_LandscapeRef has 19k unique colours in its top quarter, CAM_FromGateOut 88k,
    and full-resolution crops show smooth gradients.
  - The steps appear only in a downscaled view of the side-by-side, and equally in the reference half.
- **Rejected (delta 12, part): "lower the gravel albedo".**
  - CAM_Ref2Match gravel measures (140, 114, 110) against ref 2's (136, 106, 95).
  - The near-white gravel in CAM_EastYard is the 9 deg sun raking the yard toward the camera, not albedo.
- **Deferred to the owner (delta 4, part): "warm and brighten the horizon band; the sky reads overcast mauve".**
  - Ref 2 does show a warm peach horizon, but the owner keeps the round-9 UDS dusk.
  - The "horizon behind the hall" the judge measured (76, 59, 39) is now forest from the landscape, not sky.
  - The sky and fog values are untouched.
- **Deferred to the owner (delta 7, gameplay rule): courtyard garden dressing** (clipped pines, round shrubs, boulders,
  training posts on the sand margins).
  - Ref 2 does show them, but they sit inside the 1v1 arena.
  - Adding props there changes the playable space and collision that the brief keeps.
- **Deferred (delta 9, part; the owner's earlier call): petal scale.**
  - Petals stay at real scale, so they are sub-pixel beyond a few metres.
  - The tint and the stair scatter were applied.

### Applied, by blocker and delta

**1. River (blocker 1, delta 1)**
- **The rapids step down.** `ls_geo.stepped()` turns keys 4.0-7.4 into 7 level runs, each ending in a pour (22 % of the
  step length); the total drop is unchanged.
- **Spline and water texture.** The spline takes every 2 m sample through the rapids (256 points, was 222). The WaterZone
  render target is 2048; the default 512 is 3.1 m per texel over 1.6 km.
- **Narrower toward the camera:** R7 16 -> 13 m, R8 18 -> 12, R9 19 -> 14, R10 24 -> 19.
- **38 new channel boulders** (`RapidsB_*`, owned Fishermans SM_Rocks_01-03, 1.5-2.7 m).
  - Each is set by its TOP, 0.35-1.09 m over the local water (the new `top_z` in dj_ls_world). Its foot is checked to
    reach the bed.
  - 20 of them sit on the pour lips as boulder bars.
- **Foam material** (M_DJL_RapidsFoam, rebuilt):
  - Streaked along the flow (flow-aligned UVs, about 3.5:1). The Voronoi breakup only modulates at 25 m, so the
    cracked-ice web is gone.
  - Colour runs from an aerated turquoise-grey to white crests.
- **Foam strips:**
  - one pitched strip per 2 m: 64 strips (was 17 flat);
  - MIs: MI_DJL_RapidsFoamDrop on the pours, MI_DJL_RapidsFoam on the runs, MI_DJL_RapidsFoamTail_0..5 fading out the
    two ends;
  - the white water now runs to key 8.3, where it4 measured the reference's rapids still reach (frame y ~1250), and
    fades out by key 9.0;
  - coverage was set from maths on the exported foam texture (`fix/probe`): run ~55 %, pour ~78 %.
- **FX re-placed on the new world.** 37 emergent boulders get spray, droplets and a wake (was 7); 53 foam wakes in all.

**2. Banks and hills (blocker 2, delta 2)**
- **Forest:**
  - every candidate kept, at 4.2 m Poisson spacing, on slopes to 40 deg;
  - 3126 firs (was 1699). The 1370 within 160 m cast shadows; the 1756 beyond do not;
  - the far bank is planted from 8 m off the water.
- **Billboards.** The card is 4 x 4 m (probed), so they now scale x2.6-3.6, giving 10-14 m trees (was 4-5 m). 114,389 of
  them, about 1 per 30 m2 at 230-900 m.
- **LS_Valley material:**
  - The canopy colour starts at 60 m and is full by 170 m (was 130 / 320 m). Inside the forest zones it takes 55 % from
    the first metre. Canopy albedo (0.026, 0.044, 0.036).
  - The forest floor is darker. Grass tint (0.40, 0.56, 0.30).
  - A mossy band runs 0.5-20 m off the water.
  - The Rock layer is now triplanar. It was projected in world XY, which caused the stretched cliff streaks of delta 8.
    Tinted to mid-grey granite: linear (0.104, 0.093, 0.079), R/B 1.13.
- **Bank relief** is non-repeating value noise. The mirrored stamp tiles made the diamond / ridge "striated dune"
  pattern.
- **Bank dressing:** 70 bank boulders (`BankB_*`, 0.8-2.6 m) and 70 bank bushes.

**3. Peaks and depth (blocker 3, delta 3)**
- Peak base x2.0 (was x1.25), power 1.0 (was 1.6). The summits are unchanged: A 2057 m, B 1980 m.
- Silhouette widths, measured on the LS_Far heightmap through CAM_LandscapeRef, 40 / 80 px under the summit:

  | Peak | World stage | Now | Reference (2x crop) |
  |---|---|---|---|
  | A | 71 / 128 | 172 / 318 | 155 / 290 |
  | B (40 px only) | 51 | 131 | 100 |

- M_DJL_Far:
  - rock ribs and couloirs now break the snowfield on the steeper faces;
  - aerial perspective in the albedo: 0-60 % toward a cool violet-blue (0.30, 0.34, 0.52) over 1.5-7.5 km.

**4. West cliff (blocker 4, delta 5)**
- The terrace was cut 6-8 m straight into the hill on the west (y > 24) and north sides.
- `make_terrain.rim()` now rises from a 0.6 m verge at <= 26.6 deg, broken with noise, and the forest (FZ2 to x -10)
  stands on it.
- The sun-ray filter also protects the hall front and the west kura face.

**5. Upstream plume (blocker 5, delta 6)**
- The key-4.6 mist anchor at the bend is gone.
- Haze sheets only over keys 4.8-8.5 (they reached 2.3 km upstream).
- Mist puffs are capped at the 4 biggest emergent boulders; wisps every 22 m.
- Local fog extinction halved (0.015 / 0.04).

**6. Stair path (delta 8)**
- The BF3 bank now falls from every path edge toward the river: at most walk level - 0.25 - 0.55 x the distance. It is
  kept above the water and the WR2 foot.
- The cliff-face chunks now stand at the foot of the face; one of them read as a boulder perched on the lip.
- 86 grass / moss tufts along the step edges and 66 petal decals on the steps and landings.

**7. Conifers (delta 10)**
- The fir bounding boxes reach 4.2-6.4 m under the pivot, but the roots end 1.3-2.2 m under it (`probe_fir.json`). The ISM
  placed them from the box, so the trunks floated 3.6-5.8 m in the air.
- They are now placed by the pivot (`pivot_ground`), 0.25 m deep, at the lowest ground within 2.2 m.

**8. Shadow fill (delta 11).** Lumen sky-light leaking 0 -> 0.06 (look_r3):
- CAM_Drum near-black 20.3 -> 17.3 %;
- CAM_HallVeranda near-black 9.8 -> 7.0 %;
- the open courtyard moved toward ref 2 (see below).

**9. Backdrop (delta 12)**
- The west sun-corridor ground drops from 0.12 to 0.07 x the run. The terrain-only sun still lights 100 % of the 98 sand
  points.
- 55 shrubs stand in the corridor, each under the sun line.

**10. Lantern (delta 13).** M_DJ_Granite_Tri NormalStrength 0.55 -> 0.3, TextureSize 400 -> 250 cm. The moss pads go to
value 0.95, saturation 0.45.

**11. Petals (delta 9).** M_DKF_Petal gets a Tint parameter. MI_DKF_Petal uses (0.96, 0.72, 0.82), which moves the pale
(236, 211, 218) toward the reference's pink. The stair decals are listed under 6.

### Measured
The final set is it6, copied to `fix/caps/` (numbers in `caps/json/` and `caps/fxl_measure.txt`).

**CAM_LandscapeRef**

| Metric | Reference (day) | FX stage | Fix |
|---|---|---|---|
| Share under luma 40 | 8.95 % | 7.85 % | 11.76 % |
| Mean | 140.4 | 87.6 | 84.1 |
| p10 / p90 | 42.3 / 232.3 | 43.3 / 138.1 | 37.8 / 134.5 |

**Foam** (the world stage's rule) in the rapids boxes: 32.9 % -> **80.8 %**. The reference is 79.9 % and the judge's
target is 70-80 %.

Regions, reference -> fix:

| Region | Reference | Fix |
|---|---|---|
| Sky | (150, 186, 224) | (111, 85, 93) |
| Peaks | (221, 230, 240) | (157, 125, 121) |
| Forest slopes | (141, 166, 195) | (108, 90, 41) |
| River water | (106, 114, 121) | (65, 75, 72) |
| Foam | (176, 194, 206) | (140, 126, 118) |
| Terrace wall | (137, 119, 91) | (67, 57, 58), saturation 0.08 (the owner's grey) |
| Compound | (145, 116, 96) | (118, 91, 74) |

The sky, peak and forest boxes are lit by the sunset, so the forest hue stays warm (44 deg) at 1730.

**CAM_Ref2Match against ref 2** (FX stage -> fix, ref 2 last)

| Metric | FX stage | Fix | Ref 2 |
|---|---|---|---|
| Share under 40 | 13.3 % | 12.7 % | 13.7 % |
| Mean | 104.4 | 106.4 | 107.9 |
| p10 / p90 | 33.1 / 159.4 | 34.7 / 163.7 | 34.4 / 171.1 |
| Sand near | (168, 138, 118) | (175, 144, 124) | (182, 148, 125) |

Tiles lit (110, 95, 106), R/B 1.04. Plaster / gravel R/B 1.27 / 1.27.

**Camera health** (share under 40 / mean; FX stage -> fix)

| Camera | FX stage | Fix | Note |
|---|---|---|---|
| RiverRapids | 1.6 / 105.7 | 0.1 / 120.5 | |
| StairPath | 20.7 / 65.8 | 32.3 / 57.8 | the grey cliff in shade |
| TerraceWall | 8.4 / 122.8 | 15.7 / 116.3 | |
| FromGateOut | 7.3 / 115.7 | 14.1 / 95.2 | |
| Overview | 12.2 / 87.5 | 19.7 / 85.8 | dark forest around the compound |
| PlayerEyeSand | 21.0 / 92.7 | 18.3 / 97.4 | |

**Perf** (`fix/checks/perf/perf_summary.md`; -game, scalability 3, GPU mean at 1080p; FX stage -> fix)

| View | FX stage | Fix |
|---|---|---|
| PlayerEyeSand | 12.36 ms | 12.32 ms |
| Overview | 10.76 ms | 11.43 ms |
| PAWN | 10.60 ms | 9.90 ms |
| LandscapeRef | 8.28 ms | 9.43 ms |
| **RiverRapids** | **19.28 ms** | **22.84 ms** |

RiverRapids is over budget: ShadowDepths went from 8.06 to 11.58 ms. Left open.

### Functional checks
Fresh processes on the final level (bf999fc9); copies in `fix/checks/`.
- **Showcase verify: 8 / 8.**
- **dj_ls_verify: 6 / 6.**
  - Landscape probes within 0.03 cm; every layout actor and ISM count present.
  - B1-B8 hidden and Pawn-only; 20 / 20 CherrySlots; 28 / 28 thin uprights; 256 water points.
  - Stair walk: BR clear both ways (max step 8.3 / 10.0 cm, min floor nz 0.895). The 1v1 CONTROL is blocked by B3.
  - Every B-line CONTROL hits its blocker.
- **dj_fxl_verify: 4 / 4.** Particle estimate 3012, under the 6000 cap.
- **UE alley:** replay 32 / 32 CONTROLs blocked, 10 / 10 POSITIVEs clear, BR 30 / 30 with no mismatch; flood passed;
  pocket probes 0 / 0.
- **Blender (headless):**
  - walk, climb and every roof walk PASS;
  - the clearance, ground-hole, corridor and roof JSONs are identical in content to the FX stage;
  - the walk / climb JSONs are unchanged against git.
- **layout_showcase.json against the stage start.**
  - Identical: instances, collision classes, traversal markers, player starts, routes, lights, cameras and decals.
  - Changed: two material looks only (M_DJ_Granite_Tri, M_DKP_Stone_Moss).
  - No gameplay number, collision, GASP marker, 1v1 closure or Boundary_1v1 changed.

### Captures
`fix/caps/`, -game HighResShot; iterations it1-it6, final it6.
- CAM_LandscapeRef at 1280 x 1920.
- CAM_RiverRapids, CAM_StairPath, CAM_TerraceWall, CAM_FromGateOut, CAM_Overview, CAM_PlayerEyeSand and
  CAM_PeaksOverHall at 1920 x 1080.
- CAM_Ref2Match at 1920 x 1440.
- Extras: CAM_Drum, CAM_HallVeranda, the CU_* close-ups and CAM_EastYard.
- Sheets: LANDSCAPE_vs_OURS.png, REF2_vs_OURS.png, BEFORE_AFTER.jpg (FX stage | fix, 8 cameras).

### Open
- **CAM_RiverRapids GPU 22.8 ms** (ShadowDepths 11.6 ms). Next:
  - a shadow pass: rocks beyond 40 m, and the VSM cache for the near firs' WPO;
  - fewer shadow-casting firs within 160 m.
- **Sourcing needs** (nothing owned fits):
  - rounded granite river and bank boulders (gap 1). The Fishermans rocks are the only owned ones, and they read tan
    in close-ups;
  - Japanese slope conifers (the Nordic firs stand in);
  - understorey shrubs (azalea / boxwood mounds) and moss cushions for the banks;
  - 2-4K ground surfaces.
- **Cherries (on hold).** The right bank and the stair foreground read bare without them. All 20 CherrySlots and their
  petal emitters are waiting.
- **Owner calls:** the warm horizon and sky (delta 4), the courtyard margin dressing (delta 7) and the petal scale.
- **Leftovers:** the unused MIs `MI_DJL_RapidsFoamTail` and `MI_DJL_RapidsFoamTailSoft` (from it3) are still in
  /Game/DojoLandscape/Materials. Nothing references them.

## 2026-10-01 - HALL + ARMORY round, stage 2 (Blender): the rear extension, the opened doors, the moved closure

Workflow wf_ac6d2186-d40. Blender only, headless; no Unreal, no commit. Nothing under Scripts/armory, Exports/ArmoryKit,
WorkFiles/armory or ArmoryLab was written (the armory FBXs were only imported into a check blend).

**Built** (Scripts/dojo/hall/build_hall_rear.py, which imports build_hall.py read-only; out: Assets/Dojo/DojoHallRear.blend):
- 13 new SM_DKH pieces, exported through Scripts/pipeline. qa_check: 0 hard fails.
  - Bay_DoorOpen, DoorLeaf_Parked, Frame_Open, RoofUpper_BackValley.
  - Rear_Frame, Rear_Bay_ClerePlaster, Rear_Bay1_Plaster / _Transom / _ClerePlaster.
  - Rear_Roof, Rear_RoofRidge, Rear_RoofGable, Rear_WindowBacker.
- The 21 existing SM_DKH FBX are unchanged (sha256 checked).
- 1v1 pieces: SM_DKX_1v1_HallRear_W / _E and SM_DKX_1v1_RearRoof. SM_DGB_Boundary_1v1 was rebuilt with its north side
  moved +11 m (same name, material and pivot; the old FBX is in hall_armory/blender/start_backup).

**Numbers (measured):**
- Rear roof: 25 deg gable, eave +5.1617 at Y 45.9, valley Y 34.4199 / +5.7772, planes meet +8.1461, cap +8.6046,
  onigawara ends +8.8461 (0.76 m under the main ridge's 9.3649 / 9.6064).
- Extension wall plate +5.0279 to +5.2679. Main rear beam over the opening +5.52 to +5.687.
- The regenerated main back slope matches the shipped SM_DKH_RoofUpper_Back tri for tri (169,936) before the valley cut.
- The rafter ends at the valley touched the armory's coffer tops (+5.500 / +5.512 against +5.5007). 84 + 84 vertices
  were raised to +5.522. Lowest shell vertex over the armory: +5.522 (0.0213 m clear). Envelope violations: 0.
- Doors (ray-measured): 3 x 1.76 m clear, sill +0.545, head +2.388, 1.843 m clear (0.123 m over the GASP capsule).

**Layout** (compose_hall_armory.py; layout_showcase.json updated IN PLACE, the start copy is in
hall_armory/blender/start_backup):
- 27 instances flagged removed: 'hall_armory_rev1' (21 rear-wall bays, 5 replaced, the old HallRear blocker).
- 40 moved (the north wall +11 m, NorthWallTop). 121 added: 83 shell with shell_id, 24 side-wall pieces, 11 gravel
  copies, 3 blockers.
- Markers Wall_N / _W_N / _E_N, climb route O north and CU_R6_AlleyAbove moved +11 m.
- CONTROL_into_the_hall became hall_front_centre_door_into_the_interior.
- Walk routes added: the 26 interior routes, 11 CONTROLs and 5 BR rear-yard / alley routes.
  - ARM_CONTROL_must_hit_case1 is renamed CONTROL_ARM_must_hit_case1, so walk_check treats it as a control.
  - The two wing-deck routes start at +1.10.
- BR_road_up_the_kerb_into_the_west_lane_north: its north leg moved Y 43 -> 54. It is still a dead town route
  (carry-over).
- The terrace-side moves are in hall_armory/blender/world_layout_hall_armory.json + world_layout_delta.json (B5/B6/B7,
  WR5 +4+4+2+2 m and its end, CherrySlot CS19/20, the cypress row). Pending for the DojoLab stage: the LS_Valley spot
  heights, FZ1 and the cypress z re-snap.

**Checks** (Assets/Dojo/DojoShowcase_HallArmory.blend: the showcase + the shell + the 461 armory instances; the
landscape round's 338 removed instances are taken out of the Assembly):
- walk_check: 93 routes, passed at r 0.30 and r 0.35.
- climb_check (hover 0.019): passed. Every 1v1 number is identical to the landscape verify; only route O moved.
- gate roof_walk: passed. hall_roof_walk: 16/16 passed. hall_rear_roof_walk (new): 13/13 passed.
  - BR over the valley and the rear ridge to the north eave.
  - 1v1 CONTROLs blocked by RearRoof / HallRear_W / _E.

**Courtyard silhouette:**
- Hall masks before / after are identical (0 px) from CAM_Establishing, EstablishingRef2, Ref2Match, PlayerEyeSand
  and HallVeranda.
- The rear pieces show 0 px from those cameras plus the gate and peaks cameras.

**Shared folder:** hall_shell_layout.json is BUILT, manifest.json has the sha256s and a stage-2 line, and interface.json
was updated (INTERFACE CHANGED before release: the front-wall intrusion x +-6.3, the leaf box). The folder is still
revision 1. armory_hall synced rev: none yet (DojoLab sync is the next stage).

**Files:**
- Renders: WorkFiles/dojo/build/hall_armory/blender/renders/.
- Checks: hall_armory/blender/checks/.
- Measurements: hall_armory/blender/{measure,silhouette,compose_report}.json.


## 2026-10-01 - HALL + ARMORY round, stage 3 (DojoLab): sync, relight, landscape move, carry-over fixes, checks

Workflow wf_ac6d2186-d40. Output folder `WorkFiles/dojo/build/hall_armory/ue/`. No MCP tools, headless Blender only, one
Unreal process at a time (every runner waits on any UnrealEditor-Cmd and stops if a DojoLab editor is open; none was),
nothing committed. Nothing under Scripts/armory, Exports/ArmoryKit, WorkFiles/armory or ArmoryLab was written; ArmoryLab
was never opened (its .uasset files were only read and file-copied). No edit in Scripts/unreal/materials. DemoGame_1*,
the GASP sample and other chats' files / locks untouched. The plugins (DojoLandscapeTools / DojoFXTools) were installed
only for their steps and removed (DojoLab/Plugins absent). Config/*.ini unchanged (md5 as the start backup). The DojoKit
lock (claude) was refreshed.

armory_hall synced rev 1

**Backups** (`ue/start_backup/`, before any write): L_Dojo.umap (md5 bf999fc9, the landscape fix final), Config,
uproject, Saved GameUserSettings, layout_showcase.json + blender_bounds.json, world_layout.json + world/json, the
terrain r16 / npy / mask, the SM_DGB_Boundary_1v1 uasset, scripts.tar (Scripts/dojo/{unreal,showcase,landscape,hall}).
**Final L_Dojo md5 b2764fc1** (412 MB).

### 1. Hall pieces, back wall, closure, boundary
- Blender: `Scripts/dojo/hall/hall_armory_bounds.py` refreshed showcase/blender_bounds.json for the composed layout
  (fresh FBX meta for the 17 hall-armory pieces + the rebuilt ring; the 1,069 unchanged instances re-derive with 0.0 m
  deviation).
- Unreal: dj_import (the rebuilt ring), sc_import (16 new meshes), sc_materials, dj_materials (the ring's M_DGB_Boundary:
  the fresh reimport had left WorldGridMaterial), sc_level: 866 mesh actors (772 - 27 removed + 121 added), bounds gate
  max 0.0008 cm, 24 markers.
- Prep: `Scripts/dojo/hall/apply_hall_armory.py` (new, runs last in `run_showcase_unreal.sh prep`; idempotent): keeps
  CU_R6_AlleyAbove +11 m (look_r3 re-creates the close-ups on every prep and had undone the Blender stage's move), adds
  11 cameras (CAM_DoorwayIn, CAM_RearExtension, CAM_ArmoryEntry, CAM_ArmoryCeiling and 7 CAM_AK_* = the armory chat's
  own ArmoryLab capture cameras converted exactly), and retires the 5 dead BR town routes.

### 2. The armory interior: `Scripts/dojo/unreal/dj_armory_sync.py` + `run_armory_sync.sh` (+ `dj_armory_look.py`)
- File stage (plain Python): the dependency closure (a string scan of each package's /Game/ imports) of the 97 slot
  instances + the 6 shuriken meshes = 209 packages, copied from ArmoryLab to the SAME package paths
  (/Game/ArmoryKit/{Materials,Textures}, /Game/NinjaPack/...): byte-identical, 0 drift against manifest.json, copied
  only when the sha256 differs.
- Unreal stage: 64 SM_AK_* imported from Exports/ArmoryKit by FBX sha256 (the ak_import recipe; slot = instance name;
  Nanite unless a slot derives from M_AK_Glass_Master; fallback at full detail); 461 instances + 6 items + 114 design
  lights + 10 shell backer lights placed (tag DJ_ArmoryHall, Outliner ArmoryHall/*). Gates: bounds against
  interior_layout bbox_m max 0.0704 cm (0 fails), transforms 0.0, envelope 0 violations, every light inside the
  envelope, 83 / 83 shell ids in L_Dojo, 12 shadowed local lights (budget 14), 0 FBX / package drift. Re-run safe;
  it MUST run after every sc_level (it sets lighting channels on hall actors).
- Collision: interface.json classes incl. 'glass' (pawn block, camera + visibility ignore); every SM_AK piece keeps its
  UCX hulls (convex count = UCX count on all 64). D6: the propblock / glass pieces get CanCharacterStepUpOn No and an
  unwalkable slope override on their BodySetup.
- Floors: armory z 0 = hall-local 0 = world +0.50 = the hall's finished floor (veranda deck +0.50). The approach:
  courtyard 0 -> step band +0.15 -> stair treads +0.167 / +0.333 / +0.50 -> veranda +0.50 -> door sill +0.545 (4.5 cm,
  the largest step inside the door) -> armory floor +0.50. The armory's sunken genkan (-0.12), its step beam and its
  exterior sill are not used; its two entry lanterns and the entry mat stand lifted +0.12 on the floor; the rear dais:
  4 risers x 0.15 to the deck at +0.60 local = world +1.10.

### 3. Relight (the DojoLab-only look in dj_armory_look.py; never synced)
- Exposure parity, measured: both PPVs are manual without the physical camera; ArmoryLab bias -2.68, DojoLab +1.20, so
  the lights and the emissives get x 2^-3.88 = 0.0679 (the emissive armory instances get DojoLab child MIs MI_DJA_* as
  per-actor overrides, so the copies stay byte-identical). The survey's 10.295 (from the analytic -6.04 EV) is replaced
  in lights_design.json (level_scale.DojoLab 0.06792, under the ArmoryHall lock, change line in manifest.json, still
  revision 1; manifest last_synced.DojoLab = 1).
- Lighting channels: the unshadowed design lights shone through the walls (look1: a lit band on the alley ground
  outside the rear wall). They now light channel 1 only; the interior meshes, the items and the 28 shell actors facing
  the interior (front-wall bays X 15-29, the open door bays, the parked leaves, the frame) are on 0 + 1. Band gone.
- An interior PPV (bounded: the envelope + 0.3 m, priority 20) sets ONLY lumen_skylight_leaking 0; PostProcess_Dojo
  stays the one exposure owner (sc_verify gate 9 checks it). Measured effect small (CW_WestAisle mean 61.8 -> 60.5).
- Window backers (D5): paper emission x 0.4 (a child MI on the 10 backer actors only; the facade's shoji keep their
  look), rects 3 cd.
- Perf: per-role attenuation radii, about 3x each light's throw (20 m before): case 2.5, glow 2, panel 4, down 12,
  alcove / rack / sill 6, banner / wash 7, lantern 3, backer 8 m. The 'Lights' pass went 9.4 -> 1.8 ms in the interior.
- Sunset through the doors: grazing (the 9 deg sun runs 7 deg to the front wall), so no direct sun inside; the interior
  reads by the design lights + the sky and bounce through the doors.

### 4. Landscape move (a DELTA: `Scripts/dojo/landscape/hall_armory_world.py`)
- `ls_geo.HALL_ARMORY`: TERRACE north 44 -> 56; hill spot heights 0 at 56, +6 at 72, +20 at 112, then the old profile;
  WR5's face to 57.2; COMPOUND_LOW ends at 35.5 inside the last gravel row (the old wall that hid it has moved); -0.30
  pads under the extension and under the moved alley gravel; CS19 / CS20 +11 m. make_terrain.py takes the hill from
  G.TERRACE and the pads; make_world_layout.py's constants follow (B-lines, FZ1 / FZ2 from y 59, keepout, cypress +12,
  lanterns). LS_Valley changed only north of y 36 (286,153 cells); LS_Far 14 cells at x -532.
- Why a delta: make_world_layout draws everything from one seeded stream, so a re-run re-rolls every tree in the valley.
  The delta keeps every record's and ISM row's x / y / yaw / scale and only rebuilds the deterministic groups (walls:
  WR5 + 4 + 4 + 2 + 2, EndR to y 56; B5 / B6 / B7 to y 56; the cherry slots; the lanterns + their lights), moves the
  cypresses +12 m, re-snaps z where the ground changed (firs 1,001 rows, billboards 291, grass 998), drops the 10 firs
  in the new keepout and 157 grass tufts + 1 bush inside the new structures, and regenerates the valley mask.
- World rebuilt (ls_clear 487, ls_world 491 actors; the plugin installed and removed), FX re-placed (426 actors: 2
  fewer petal drift meshes from the traces). The back wall, alley gravel, side walls, closure and ring come from
  sc_level (the layout).

### 5. Carry-over fixes
- Stair lanterns 3 / 4 / 6 off the 1.8 m tread to the cheek side: L2 / L3 onto the cliff-side low cheek (x 7.95, walk
  + 0.117), L7 onto the west kerb (x 2.15, z -6.907); the lights follow. The UE stair walker's centre lane is now clear
  at r 30 (lanes 0 / +0.1 / +0.3 both ways; before only +0.1 / +0.3); min clear width 0.90 -> 0.95 m, now at L6
  (Lantern_5, not in the brief: it still snags the r 35 centre lane).
- Dead BR routes: the 5 town routes moved to layout retired_walk_routes with the reason (walk routes 93 -> 88).
- Shadow pass: Rigid VSM invalidation on every shadow-casting WPO ISM (8 near-fir ISMs, 10 bush ISMs) in dj_ls_world.
  GPU at 1080p, configured %: RiverRapids 22.84 -> 12.87 ms (ShadowDepths 11.6 -> about 1.0), StairPath 19.1 -> 9.9 ms,
  PlayerEyeSand 12.32 -> 10.39 ms. No shadow removed, so the look elsewhere is unchanged (BEFORE_AFTER).

### 6. Checks (fresh processes on the final level; copies in ue/checks/)
- sc_verify 9 / 9 (new gate 9_armory_hall: 592 actors, every instance / item / light, the PPV bounded without
  exposure, sync rev 1; dj_sc_verify now leaves the DJ_ArmoryHall actors to gate 9). GASP trace 23 / 23, markers 24.
- dj_ls_verify 6 / 6 (stair walk BR both ways, max step 10 cm, nz 0.895; the 1v1 CONTROL stopped by B3; B1-B8 hit).
- dj_fxl_verify 4 / 4 (it needs the DojoFXTools plugin: tools/run_fx.sh).
- r6 UE alley replay 32 / 32 CONTROLs blocked, 10 / 10 POSITIVEs, BR 30 / 30 with no mismatch; alley flood 0 cells
  (max y 33.7); pocket probes 0 / 0 clear.
- Own alley seal (`checks/ue/ha_ue_alley_own.py`, the verifier's v10 with the new targets: strips W / E to y 47, the
  rear yards, the alley behind the extension, the rear roof, the moved wall top): 1v1 flood 3.46 M cells, 0 leaks;
  arcs r30 0 / 610,680, r35 0 / 602,560; mantles 0 leaks (1,540 GASP-valid; its 'path-ignored' list is stances OUTSIDE
  the ring at x -1.55 on the new side-wall run, blocked by the ring: not 1v1); the BR flood reaches all 14 targets.
- Boundary (`checks/ue/ha_ue_boundary.py`): 88 / 88 walk routes as expected incl. the 26 interior routes and the 11
  interface CONTROLs (33 CONTROLs blocked). The walker's step-up probe now clamps under a ceiling as the CMC does (the
  door head is 12 cm over the capsule). flood1v1 r30 1.04 M cells, 0 leaks (incl. 0 in the hidden side strips / wall
  cavities), reach y <= 43.57 = the interior; floodbr reaches outside the ring; highest standable 9.606 -> ceiling
  12.46. (Its arcs1v1 with a 'y > 34.8' closure line reports 13,806 'leaks': all launched from the corridor north
  slopes, which are closed targets in the alley test above, so they are not 1v1 positions; the alley test is the
  authority.)
- Blender (final layout, `checks/blender/`): walk 88 routes pass at r 0.30 and r 0.35, controls blocked; climb pass;
  gate roof, hall roof (16) and rear roof (13) walks pass.

### 7. Captures (ue/caps, -game HighResShot, 28 / 28; iteration 'final')
- REF2_vs_OURS.png (Ref2Match under40 12.9 %, mean 105.0; the fix round 12.7 / 106.4); LANDSCAPE_vs_OURS.png (under40
  11.0 %, mean 84.0). BEFORE_AFTER.jpg + DIFF_*.png: CAM_Ref2Match 0.14 % of the frame below the sky changed outside
  the door band (24.6 % inside it); HallVeranda changes only in the door bays; the river / mist views differ by live FX.
- ARMORY_vs_OURS.jpg + 9 pair sheets (entrance, aisle, case 3, hero, shuriken tray, case 1, cloak case, from the
  platform, ceiling). Ours reads about 1.3-1.6x the armory's night mean (the sunset sky through the doors).
- CAM_DoorwayIn, CAM_RearExtension, CAM_Overview, CAM_LandscapeRef and the landscape set.

### Perf (`checks/perf/perf_summary.md`, 1080p configured %, GPU mean)
PlayerEyeSand 10.39, Overview 14.17 (median 10.83; spikes), PAWN 9.28, LandscapeRef 8.08, RiverRapids 12.87, StairPath
9.9, DoorwayIn 10.36, WestAisle 11.48, FromPlatform 13.41 (median 11.76), RearExtension 10.94 ms: all under 16.7.
**Open: the frame time is render-thread bound** (PlayerEyeSand RT 20.5 ms = FT; the fix round 13.9): the 592 interior
actors + 124 movable lights. Next: one ISM per piece for the interior (461 actors -> 64 components) and fewer glow /
panel lights (MegaLights or emissive-only).

### Open
- Lantern_5 (L6) still stands 0.35 m inside the tread (it snags only the r 35 centre lane).
- The render-thread-bound frame time (above). The interior reads brighter than the armory's night stills by design
  (sunset); the judge may want it darker or more contrasted.
- ArmoryLab is not synced (manifest last_synced.ArmoryLab null): the user sends the armory chat its prompt.


## 2026-10-01 Hall + armory FIX round (DojoLab): judge deltas, shared revision 2

Output folder `WorkFiles/dojo/build/hall_armory/fix/`. Headless Blender only, no MCP tools, one Unreal process at a time
(each runner waited on any UnrealEditor-Cmd and checked that no DojoLab editor was open). Nothing committed. Nothing under
Scripts/armory, Exports/ArmoryKit, WorkFiles/armory or ArmoryLab was written, and ArmoryLab was never opened. No edit in
Scripts/unreal/materials. The ArmoryHall lock was claimed and released for each shared write, and the DojoHall lock was
refreshed (claude). Config/*.ini are unchanged (md5 matches the start backup) and DojoLab/Plugins is absent. One stray
log folder from my first probe (relative paths) went to Engine/Binaries/Win64/WorkFiles. I killed that probe's own
process and deleted the folder.

armory_hall synced rev 2

**Backups** (`fix/start_backup/`): L_Dojo.umap (md5 b2764fc1), Config, uproject, layout_showcase.json and
blender_bounds.json, the shared folder (rev 1), scripts.tar, and the old SM_DKH_RoofLower_Front.fbx.
**Final L_Dojo md5 506a2cca.**

### Judge deltas, each checked against the references first (JUDGE-STEER)
1. **Sunset shafts through real openings: rejected.** The hall has no sun-side opening. Every side bay of the main hall
   and the extension is plaster (hall_shell_layout.json), and the level's 9 deg sun runs 7 deg off the front wall, so
   direct sun cannot reach the floor through the doors. A floor patch would need an invented opening. The armory's own
   floor lattice comes from its per-level Sun_WindowFill, which has no source in the hall. The warm side of the delta is
   met by the threshold fill (6).
2. **Inside and outside disagree: accepted as "dark windows"**, which is what the armory's own night stills show. The 10
   backer rects are off (visible False) and the backer paper is at x0.02. The rear wall's centre bay X 21-23 (DKH_N0022,
   the old rear wall's closed lattice door, which glowed with the hero painting right behind it) is replaced by
   DKH_N0084 SM_DKH_Bay_Plaster at the same place (apply_hall_armory.py, idempotent). The two corner lattice bays stay.
3. **Dashes on the inner face of the front wall: accepted, measured.** fix/blender/probe_front_wall.py found 94 vertices
   of SM_DKH_RoofLower_Front (rafter ends / wall flashing on the 0.30 m pitch) at y 24.0545, z 3.926, which is 9.5 mm
   past the transom plaster face at 24.045. No other hall piece crosses that face. The new
   `Scripts/dojo/hall/fix_lower_front_clip.py` rebuilds the piece with build_hall.roof_pieces(). It matches the shipped
   mesh within 1e-6 m (75,361 vertices both) before any change, then clamps 124 vertices in z 3.80-4.10 to y 24.040.
   The y max goes from 24.0598 to 24.040 (1.98 cm, so the name is kept per SYNC.md 9). qa_check: 0 hard fails. Exported
   through Scripts/pipeline (sha 49c138fb). After the rebuild, 0 vertices are left past the face, and the dashes are
   gone in CAM_AK_CX_FromPlatform.
4. **Interior exposure: accepted, measured.** Probes fix/probe/p1 and p2 compared 7 CAM_AK views with the armory's r20
   stills, using display luma log2(ours/armory) of mean / p50. As built: 0.62 / 0.83, with p10 up to 15.
   - Fog off: no change.
   - Indirect lighting intensity 0.5 or 0.25: no change.
   - Sky light x0.25: 0.57 / 0.71.
   - The armory's toe 0.4: lifted the darks (p10 5 -> 24), so rejected.
   - -0.6 EV: 0.25 / 0.17.
   - -0.6 EV plus local exposure contrast 1.0 / 1.0: 0.14 / -0.24, with p10 back to 0-2.8.
   - -1.0 EV: too dark (p50 -0.83).

   Chosen for the bounded interior PPV only: bias 0.6 (-0.6 EV), local exposure 1.0 / 1.0, plus the armory's own
   bloom 0.3 and shadow saturation 1.0. Gate 9 now accepts the PPV's bias only when it equals dj_armory_look's value;
   PostProcess_Dojo still owns manual exposure everywhere else. Final pairs (armory | ours, mean / p50):
   - Hero 46.5 / 25.4 | 58.7 / 35.1
   - Tray 39.0 / 50.9 | 46.0 / 54.1
   - Case 1 34.4 / 24.0 | 31.7 / 19.2
   - West aisle 27.3 / 4.7 | 28.7 / 4.3
   - From the platform 23.0 / 5.3 | 24.8 / 4.9
   - Cloak case 28.0 / 12.6 | 24.0 / 6.3

   The p10 values are now 0-3.5, against 0-1.4 for the armory.
5. **Shoji beside the open doors glow from inside: accepted.** These are the six parked door leaves, which stand against
   the plaster bays with nothing behind them. They get an unlit paper MI (MI_DJA_ParkedLeafPaper: EmissiveIntensity 0,
   BaseMult 1.0) and lighting channel 0 only, so only the sun, sky and bounce through the doors light them. The first
   final pass still read orange because DJ_ThresholdFill lit them from 1.3 m away (caps/final_pass1).
6. **Dark slot from the courtyard: accepted.** Reference 2 shows every front bay glowing. DJ_ThresholdFill is a
   DojoLab-only rect light: 5.6 x 1.0 m at hall-local (0, 0.9, 2.3), pitch -55, 2700 K, 160 cd, channel 1, no shadow,
   no specular. It is listed in lights_design.json level_only_not_travelling. Probe p3 (x0 / 1 / 2 / 4 / 8 on 30 cd)
   moved the door-box mean in CAM_Ref2Match from 66.6 to 90.7. The CAM_Ref2Match frame outside the door box below the
   sky changed only 0.14 % (0.121 % on static pixels).
7. **A/B noise: accepted as a method.** The "before" stills belong to the landscape round's level and cannot be
   re-shot. A second capture of the same final state (caps/noise, warm-up 150 s instead of 75 s) marks every pixel that
   changes between two identical runs (> 24/255, dilated 3 px) as live noise. ha_sheets.py now also reports *_static
   numbers on the remaining pixels. Ref2Match: live noise 1.3 %, static change outside the door box 0.121 %.
   HallVeranda and CU_Lantern change only in the open door bays, which their boxes do not cover. RiverRapids and
   TerraceWall keep 4-5 % static change: river mist / foam that both runs happened to share, plus the stage-3 terrace
   move.
8. **Bare rear extension, gegyo, plinth, gravel, pull it in: rejected.** The extension already uses the main hall's
   language (build_hall_rear.py): gegyo under both verge apexes, a rubble-granite foundation (top +0.20), and a gravel
   drip strip (the moved alley gravel). Its gable is "plaster in a timber frame" like the main gable. A vent lattice
   would be invented. The 11 m depth is set by the armory's 20 m interior and the alley closure.
9. **White card in CAM_DoorwayIn: accepted, measured** (probe p4, cumulative switches in its 90 x 100 px box). Base
   p95 is 240 (5.2 % clipped). Reflect-card emission 0: 239. Adding CaseLight_08 + UnderGlow_08 off: 164. Adding sun
   off: 160. So the tray's upright reflect card is lit by its own case light 19 cm above it. DojoLab-only changes:
   CaseLight_08 x0.5 (LIGHT_TRIM) and reflect card emission x0.1.

### Shared folder: revision 2 (`Scripts/dojo/hall/update_shared_hall_armory_fix.py`, ArmoryHall lock)
- Shell only:
  - hall_shell_layout.json: DKH_N0022 is "removed (rev 2)" and DKH_N0084 is added; rear_Y45 "23" is now Plaster;
    DKH_S0604 has its new bbox; measured.front_wall_inner_face_rev2; the backers' per-level DojoLab state.
  - lights_design.json: the DJ_ThresholdFill level-only record.
  - manifest.json: the SM_DKH_RoofLower_Front sha, a rev-2 change line, and last_synced.DojoLab = 2.
- interior_layout.json and interface.json are untouched: no interior piece, case, item or design light changed, and
  there is no interface change.
- ArmoryLab has nothing to re-import, because the shell is not used there.

### Unreal (DojoLab)
- Steps: sc_import (only RoofLower_Front re-imported), sc_materials, sc_level (866 meshes, bounds gate 0.0008 cm), then
  run_armory_sync.sh at rev 2 (461 / 461 instances, bounds 0.0704 cm, 83 / 83 shell ids, 12 shadowed). sc_verify then
  passes 9/9.
- blender_bounds.json was refreshed by hall_armory_bounds.py, which now takes extra fresh pieces on its command line.
  The 1,137 unchanged instances deviate 0.0 m.
- dj_armory_sync.py now handles:
  - removed shell ids;
  - level-only lights (LOOK.LEVEL_LIGHTS);
  - per-light trims (LOOK.LIGHT_TRIM);
  - backers switched off;
  - the parked-leaf MI and channel 0;
  - PPV grade vectors.
- dj_game_capture.py probes now cover every local light type and any PPV by label.

### Checks (fresh processes on the final level; `fix/checks/`)
- sc_verify 9/9: GASP trace 23/23, 24 markers, gate 9 at rev 2 with 593 actors.
- dj_ls_verify 6/6 and dj_fxl_verify 4/4 (plugin installed for the run, then removed).
- r6 alley replay: 32/32 CONTROLs, 10 POSITIVEs, BR 30/30, no mismatch. Alley flood: 0 cells. Pockets: 0 / 0.
- Own alley seal (ha_ue_alley_own): 1v1 flood 3,460,860 cells with 0 leaks. Arcs: 0 of 1,016,400 at r30 and 0 of
  998,160 at r35 (a finer 0.25 m grid than stage 3). Mantles: 0 leaks, with the same 84 path-ignored outside stances as
  stage 3.
- Boundary (ha_ue_boundary): 88/88 walk routes as expected, including the interior routes and CONTROLs. flood1v1 has
  0 leaks at r30 and r35. Highest standable +9.606, ceiling 12.46. arcs1v1 reports the same 13,806 corridor-slope
  launches as stage 3; the alley test is the authority there.
- Collision is unchanged by this round: Bay_Plaster and Bay_Door have identical hulls, and the RoofLower_Front UCX is
  untouched. So the Blender walk / climb / roof-walk checks of stage 2 still hold and were not re-run.

### Perf (fix/checks/perf/perf_summary.md, GPU mean at 1080p and the configured %)

| View | ms |
|---|---|
| PlayerEyeSand | 10.36 |
| Overview | 10.50 |
| LandscapeRef | 8.02 |
| PAWN | 9.74 |
| RiverRapids | 12.86 |
| StairPath | 9.87 |
| DoorwayIn | 10.23 |
| WestAisle | 11.06 |
| FromPlatform | 11.21 |
| RearExtension | 10.68 |

All are under 16.7. PlayerEyeSand frame time is 16.02 ms with RT 16.0 ms (stage 3: RT 20.5), with the 10 backer rects
off.

### Captures (fix/caps, -game HighResShot, 28/28 + 16 noise)
- REF2_vs_OURS.png: Ref2Match under40 12.2 %, mean 107.5.
- LANDSCAPE_vs_OURS.png: under40 9.6 %, mean 82.2.
- BEFORE_AFTER.jpg and DIFF_*.png (blue = live noise).
- ARMORY_vs_OURS.jpg and 9 pair sheets.
- CAM_DoorwayIn, CAM_RearExtension, CAM_Overview, CAM_LandscapeRef, and the interior and landscape sets.

### Open
- The interior still reads a little hotter in highlights (p90 1.1-1.3x), and the entry views from outside the PPV
  (CAM_ArmoryEntry, CAM_DoorwayIn) are 0.6 EV brighter than inside by design: the outside exposure owns them.
- The render-thread cost of the 592 interior actors remains (ISM per piece is the next step).
- Lantern_5 (L6) is still in the r35 centre lane.
- ArmoryLab is not synced (last_synced.ArmoryLab null; rev 2 has nothing for it to import).


## 2026-10-01 Hall + armory FINISH stage (DojoLab + the shared folder): the sync made self-sufficient, shared revision 3

Output folder `WorkFiles/dojo/build/hall_armory/finish/`. Headless only, no MCP tools, one Unreal process at a time (every
runner waited on any UnrealEditor-Cmd and stopped if a DojoLab editor was open). Nothing committed. Nothing under
Scripts/armory, Exports/ArmoryKit, WorkFiles/armory or ArmoryLab was written and ArmoryLab was never opened (its files
were only read: the armory build reports and the material / texture .uasset hashes). No edit in Scripts/unreal/materials.
The ArmoryHall lock was held from the first shared write to the `--record-sync` and released; DojoKit and DojoHall were
refreshed (claude). Config/*.ini unchanged; DojoLab/Plugins absent after every plugin run.

armory_hall synced rev 3

**Backups** (`finish/start_backup/`): L_Dojo.umap (md5 506a2cca), Config, uproject, Content/ArmoryHall,
Content/DojoLandscape, the shared folder at rev 2, scripts.tar (Scripts/dojo + lock.py), the terrain (npy / r16 / mask),
world_layout.json, layout_showcase.json, blender_bounds.json, BUILD_NOTES.md, the armory_sync outputs.
**Final L_Dojo md5 e118ff65.**

### A. Shared tools (`WorkFiles/shared/armory_hall/tools/`, plain Python 3 + numpy, run from the repo root)
- `regen_interior.py`: interior_layout.json + lights_design.json from the armory chat's own data (its layout.json and
  unreal/{import,materials,level}.json). The survey's rules moved out of make_survey.py: the frame (+(-6,0,0)), the
  not-used list (all SM_AKX_*, Entrance_12, Threshold_4, GenkanFloor, StepBeam, EntryBand, the door leaves, the jamb
  posts, the sconces, the two south corner posts), the genkan substitutions (8 tiles AKI_9001-9008, lanterns / mat and
  their lights +0.12). Stable ids: piece + armory location + rotation, then the nearest same piece within 1 m (moved),
  then a new number; vanished ids go to `retired_ids`. Envelope from interface.json (a violation stops the write).
  Per-level values (level_scale, the `level` lights, case contents) carried over. Dry run prints the diff; `--write`
  needs the lock. **Proof:** on today's armory data it reproduces revision 2 with **0 content changes** in both files
  (461 / 461 ids, 0 moved / new / retired; only `source` metadata differs: the armory layout sha256 + the generator,
  written once at rev 3). Synthetic test (an instance inserted at index 0, a coffer moved 0.3 m, a wall deleted): every
  other id kept, the moved coffer kept AKI_0006, the new vase got AKI_0618, the deleted wall AKI_0188 went to
  retired_ids.
- `bump_manifest.py`: rebuilds the lists from the layouts and re-hashes every FBX (interior + shell + sidecars), item,
  ArmoryLab material / texture .uasset, armory PNG, the shell textures of shell_materials.json, the DojoLab-only site
  pieces and every shared file (`shared_files`); revision + 1 and a change line; `names_ever` + `--retire` for SYNC.md 9;
  `--record-sync DojoLab|ArmoryLab`; refuses without the ArmoryHall lock.
- `check_sync.py --side armory|dojo`: files (an edit without a bump fails), sha (275 entries), pieces / ids, envelope
  measured on the FBX bytes with `fbxlite.py` (a 150-line binary FBX reader; its frame reproduces every recorded bbox:
  shell 133 instances within 0.1 mm, interior 461 within 0.7 mm), names, light budget, freshness (the regen in memory;
  dojo side also make_shell_materials), revision compare. Exit 0 synced / 2 behind / 3 stale interior / 1 failed.
  Result now: **dojo 0, armory 2** (ArmoryLab not synced yet). Measured: interior 175,137 vertices, worst 0.7 mm past
  with_walls (tol 12 mm); shell 789,415 vertices, **0 inside the envelope** outside the intrusions; 0 interior bboxes
  off their FBX by > 2 cm; 12 shadowed lights (ArmoryLab budget 12, DojoLab 14).
- `ue_armorylab_shell.py` (Unreal, ArmoryLab): imports the 32 SM_DKH FBX + 31 PNG by sha256, builds the two masters
  from dj_sc_materials.py's graph code (exec without main()) and the 10 instances from shell_materials.json, places the
  161 shell instances at hall-local + (6,0,0), the backer rects (default off), a courtyard stand-in, hides + keeps the
  165 not-used armory instances (folder ArmoryHall_Reference/ArmoryExterior, tag AH_ExteriorHidden), places the 8
  hall-variant tiles and lifts the genkan pieces; gates; writes synced_revision.json. **Proven on DojoLab in no-save
  test mode** (`AH_TEST=1`, assets under /Game/_AHShellTest, L_Dojo loaded only): 31 textures + 32 meshes imported
  (UCX hull counts = expected on all 32), masters built, the 10 MI readbacks equal DojoLab's own (0 mismatches), 161 /
  161 placed, bounds max **0.0055 cm**, 8 tiles placed, **0 files changed in DojoLab Content / Config** (snapshot diff).
  Note: the fresh masters compile with 115 / 22 expressions where DojoLab's materials.json reports 228 / 42 for the
  masters it rebuilt in place (same functions; the in-place count is not explained here).

### B. SYNC.md revision 3 + shell_materials.json
- `shell_materials.json` (Scripts/dojo/hall/make_shell_materials.py): 32 pieces (fbx, sha256, sidecar, Nanite, UCX,
  collision, slot -> instance), 10 instances (exact scalars incl. DojoLab's emissive scale, linear vectors, switches,
  textures), 31 textures (kind, sRGB / compression / DirectX), the import recipe, the masters' recipe location, the
  per-level emission values (ArmoryLab parity x14.72) and DojoLab's per-actor paper overrides. Readback vs DojoLab's
  materials.json: 0 mismatches.
- SYNC.md: section 0 (one command at session start, the exit-code table), 3 (both projects' sync incl. the ArmoryLab
  commandlet line), 11 (ArmoryLab shows the extended hall: instances rule, offset, exact FBX / texture / material lists,
  hidden exterior kept for reference, the hall-variant interior, what stays per level), 12 (interior change flow),
  13 (shell change flow), 14 (first-time setup for ArmoryLab).
- Manifest revision 3 (change line, chat dojo): tools, shell_materials, SYNC.md, interior_layout source metadata; no
  geometry / light / interface change. ArmoryLab has the shell to import for the first time.

### C. dj_armory_sync.py writes only what changed
The level part is planned as pure data first; its sha256 is tagged on every actor (DJA_spec_<hash>). When the level
holds exactly that plan and the transform / bounds / light gates pass, nothing is touched; MI_DJA_* are created / saved
only when parent or value differ; the import manifest only when an import changed it; the shell channel / paper
assignments only when they differ; L_Dojo is saved only when dirty. **Proof:** second run `level_kept=True dirty=False
assets_saved=0`, `saved: skipped (no change)`; md5 + mtime of L_Dojo.umap and the 34 MI_DJA_* identical before / after,
0 files in DojoLab Content / Config newer than the marker (json/idem_final_*.txt). (The first ISM trial run gave the same
proof: json/idem_before/after.txt.)

### D1. CAM_Ref2Match backdrop restored (terrain + trees)
- ls_geo.HILL_RESTORE (56 -> 72): make_terrain.natural() blends the hill back to the landscape round's surface
  (TERRACE_OLD / HILL_SPOTS_OLD) through a smoothstep band behind the moved terrace. Measured against the landscape
  round's LS_Valley: y >= 80 **identical** (max |d| 0.000 m), y 72-80 mean -0.04 m; the terrace / extension / pads
  unchanged (y < 56 max 0.0 vs the previous terrain).
- hall_armory_world.py: the trees the camera sees where the ground is still lower (or that the keepout dropped, or the
  cypresses) are re-seated along their CAM_Ref2Match view ray: position C + k (P - C), scale k s, same yaw, k solved so
  the base meets the new ground (identical projection). 40 fir rows (k 1.00-1.44, median 1.11; 8 of them were dropped
  before) and Cypress_1-4 (k 1.20-1.23); Cypress_5 (no root) keeps the stage-3 +12 m move.
- World rebuilt (ls_clear 491 / ls_world 491, plugin installed and removed), FX re-placed (426).
- Measured (finish/json/ref2_backdrop.json, the verifier's regions, live noise from a second run masked):

| CAM_Ref2Match vs the landscape round | fix round final | finish final |
|---|---|---|
| backdrop rows 0-500, static change, % of frame | 3.50 | 1.48 |
| above the main roof (x 660-1260, rows 0-345), % of region | 14.98 | 3.81 |
| forest + hill pixels only (sky excluded), % of region | 11.39 | 3.90 |
| forest + hill above the main roof, % | 19.23 | 4.07 |
| hall + courtyard outside the door box, % of frame | 0.03 | 0.03 |

  The residual is mostly the UDS cloud layer (it differs from the landscape round's capture in every later run) and
  wind sway. Sheets: caps/BEFORE_AFTER_Ref2Match.jpg (landscape | fix | finish), caps/DIFF_CAM_Ref2Match_fix_vs_finish.png.

### D2. Render-thread cost: measured cause = Niagara in the ray tracing scene (not the interior actors)
- Probe 1 (finish/perf_probe/run1): hiding all 461 interior mesh actors changed the frame time by +0.65 ms
  (PlayerEyeSand) / -0.05 ms (WestAisle); hiding the 124 interior lights -0.8 / -1.0 ms.
- Probe 2 (cvars at runtime): `RayTracing_FinishGatherInstances` was 7.3-7.9 ms of render thread. Niagara RT geometry
  off: frame time 16.05 -> 11.36 ms (p95 17.56 -> 12.30) at PlayerEyeSand, 15.68 -> 11.66 (p95 17.62 -> 12.89) at
  WestAisle; ISMs / landscape / static meshes / water / WPO RT off changed nothing.
- Fix (dj_fxl_place.py): every Niagara component `visible_in_ray_tracing = False` (main view and shadows unchanged).
  Same-session A/B (perf_ab, the FX RT flag switched back on at runtime): PlayerEyeSand 14.9 / p95 18.6 (fix) against
  28.7 / 36.0 (FX in RT); WestAisle 14.0 / 17.3 against 27.8 / 33.7.
- **ISM conversion: implemented, then gated off by measurement.** dj_armory_sync.py builds one ISM_<piece> per Nanite
  piece (57 ISMs / 448 instances + 13 glass actors; gates 461 / 461, bounds 0.0704 cm). In -game every ISM rendered
  the DEFAULT material: `missing usage flag InstancedStaticMeshes` on 92 armory materials (caps/ism_trial). The flag is
  on the masters, which are byte copies of ArmoryLab's packages and must stay byte-identical. So a piece uses an ISM
  only when all its base materials carry `used_with_instanced_static_meshes`; today none do, so the interior stays 461
  single actors (sc_verify gate 9 accepts both forms). Open request for the owner / armory chat below.
- Final perf (finish/perf_cool, machine idle beforehand, no ProfileGPU, 1080p configured %):
  frame time mean / p95, ms:

  | run (state) | PlayerEyeSand | WestAisle |
  |---|---|---|
  | fix round (verify) | 16.09 / 17.92 | 16.19 / 18.95 |
  | probe 2, FX RT off at runtime | 11.36 / 12.30 | 11.66 / 12.89 |
  | finish, first segments of the ISM trial run | 11.68 / 12.07 | 10.81 / 11.57 |
  | finish final level, perf_cool (two passes) | 14.97 / 17.81, 15.02 / 18.40 | 13.58 / 16.67, 13.83 / 17.31 |
  | same session, FX back in RT | 29.13 / 35.53 | - |

  GPU 10.5 / 10.8 ms throughout (not the limit). From 11:18 on every run (ISM or single actors, any view, after an
  idle pause too) carries about +2.9 ms of render thread that the earlier runs did not: RenderOther +1.6, RenderLighting
  1.35 -> 2.7. Toggle run perf_diag: hiding the interior (meshes + lights) gives 12.29 / 15.98 at PlayerEyeSand, so
  most of the RenderLighting rise is the 124 interior lights; hiding Niagara 13.96 / 17.73, foliage 14.82 / 18.80,
  water 14.68 / 18.71. Cause of the step not found (not thermal: desktop i7-14700K on High performance; not the ISM
  change; not ProfileGPU).
  The full-view runs (perf/run_with_profilegpu, perf/) show the same step on every view (13-16 ms mean); in the
  first one the per-segment ProfileGPU dumps also grew GameThread/UI to 3.4 ms, so the final runs skip ProfileGPU.

### D3. Stair lantern 5 (L6)
make_world_layout.LANTERN_MOVES[5] = (2.15, -34.7, walk + 0.117): onto the west low cheek Cheek_21 (x 2.0-2.4), hull
1.91-2.39 < the tread edge 2.4, light follows. Stair walker: r35 lanes 0 / +0.1 / +0.3 clear both ways (before: the
r35 centre lane blocked at L6), min clear width 0.95 -> **1.55 m** (now at L3, x 9.1).

### Checks (fresh processes on the final level; finish/checks/)
- sc_verify **9/9**: GASP trace 23/23, 24 traversal markers, gate 9 (593 actors, rev 3).
- dj_ls_verify 6/6 (stair walk BR both ways, max step 10 cm; the terrain probes within 0.3 mm; 1v1 CONTROL stopped by
  B3), dj_fxl_verify 4/4.
- Boundary (the verifier's v11 checker, `fin_ue_boundary.py`; its unwalkable rule normalises ISM labels): 88 walk
  routes as expected (55 clear, 33 CONTROLs blocked); interior walking flood 3769 / 3769 free floor cells reached at r30
  (3644 / 3644 r35), dais reached (+1.09), 0 leaks into strips / cavities, no case / lantern / vase stood on; rear roof
  BR walks clear, 1v1 blocked; flood1v1 r30 1,043,633 / r35 583,870 cells, 0 leaks; highest standable +9.606, ceiling
  12.46.
- Alley (`fin_ue_alley.py`): 1v1 flood r30 3,131,839 / r35 3,102,552, 0 leaks; with the door window resolved (DJ_ZB0
  0.13, the verifier's setting) 3,465,803 / 3,423,597 cells, 0 leaks (= the verifier's); arcs 0 / 1,014,000 (r30) and
  0 / 996,000 (r35) from the exterior, 0 / 211,680 and 0 / 199,920 launched from the interior floor; mantles 1,540
  GASP-valid, 0 leaks; BR opens every target.

### Captures (finish/caps, -game HighResShot)
final/: CAM_Ref2Match, CAM_LandscapeRef, CAM_DoorwayIn, CAM_AK_CW_WestAisle, CAM_AK_C10_Hero; noise/: Ref2Match,
WestAisle, Hero. BEFORE_AFTER_Ref2Match.jpg + DIFF; FIX_vs_FINISH_<cam>.jpg: the interior is unchanged against the fix
round (static change 0.22 % / 0.20 % / 0.22 %; means 26.9 / 26.8, 54.6 / 54.6).

### Open
- The interior ISMs wait on the armory masters' `used_with_instanced_static_meshes` (an armory-side change, owner's call;
  then dj_armory_sync.py switches the pieces on its own). Measured benefit small (the actors are not the cost).
- Frame time in the state measured since 11:18 is 13.6-15 ms mean / 16.7-18.4 ms p95; the clean early segments meet the target (12.1 / 11.6 ms p95). In the current state the target is met at WestAisle in one pass (16.67) and missed at PlayerEyeSand (17.8-18.4). Next levers, per level only: a max draw distance on the interior lights seen from the courtyard, fewer glow / panel lights, or MegaLights; and finding the +2.9 ms step.
- ArmoryLab not synced yet: the owner sends the armory chat its prompt (SYNC.md sections 0 and 14).

## 2026-10-01 armory_hall revision 4: the verifier's two sync gaps closed (docs + tools, no Unreal run)

Shared folder only (WorkFiles/shared/armory_hall), under the ArmoryHall lock (claimed, released). SYNC.md rev 4:
section 3.2 fixes the ArmoryLab order (the armory chat's own run_armory_unreal.sh routine first and complete on its
unmodified layout, ue_armorylab_shell.py LAST, then check_sync --side armory as the hall-variant check; no ak_* Unreal
step after the tool, since ak_verify's 1 cm gate would fail on SM_AK_EntryMat__335 / SM_AK_Lantern__612 / __613 lifted
+0.12 m); 3.4 which revisions need a sync (manifest sync_needed_rev); 15 the shell master graph. NEW
tools/master_snapshot.py + shell_masters.json (the call graph of build_lib_opaque / build_lib_emissive, 48 members,
graph_sha256 04c9ecfb), check_sync checks 'masters' and 'hall_variant', bump_manifest records first-time files as added
and takes --correction (the rev-3 shared_files_changed correction is in the rev-4 line). check_sync --side dojo 0,
--side armory 2 (ArmoryLab never synced); regen_interior dry run 0 changes. ue_armorylab_shell.py unchanged. Nothing
under Scripts/armory, Exports/ArmoryKit, WorkFiles/armory or ArmoryLab written; no Unreal project opened; nothing
committed. Follow-up: dj_sc_verify gate_armory_hall wants sync.json synced_revision == manifest revision, so the next
DojoLab sc_verify needs a run_armory_sync.sh first (it records rev 4).

armory_hall synced rev 4

## 2026-10-02 - NINJA CHARACTER: the DemoGame_1 player ported into DojoLab (build stage)

Owner request (2026-10-02): DemoGame_1's player in DojoLab, its LOOK, MOVEMENT and JUTSU; not the air-jump flips,
lock-on, crouch-run / prone, free look or combat. Plan: `ninja_character/survey/PORT_PLAN.md`; provenance (DemoGame_1
commit, every file with sha256, every change, re-sync steps): `ninja_character/PORT_PROVENANCE.md`.
**PRIVATE LAB ONLY:** Naruto jutsu names and third-party anime audio (seal, release, Chidori, two voice lines) came
along; nothing of this goes into anything sold or shared, and no footage with them is published (R7).

### Source and guards
- DemoGame_1 `metahuman-player` HEAD `7ea694afab7420f552879ce0f0a917901fbd07d7` (Source identical to HEAD); the male
  player's BP_NinjaGasp / BP_NinjaVisual from the LFS blobs of `43fd6ce242b48c282e089e802d6f0c113f821c21` (today's
  files carry the private female body / catwalk). Read only: file reads + `git --no-optional-locks`; `git status`,
  HEAD and `.git/index` mtime identical before and after, no file under DemoGame_1 newer than the start snapshot.
  Nothing female / Hiyuki / 2B / catwalk / Mocap copied (`private_blocked` 0).
- check_sync --side dojo before and after: the same 25 `FAIL: sha` (Exports/ArmoryKit, owed by the armory chat) + 1
  STALE (armory interior data); nothing owed by the dojo side; no shared file touched.
- Lock `DojoNinjaPort` (claude) in WorkFiles/locks. Every Unreal step waited for no UnrealEditor-Cmd (an ArmoryLab
  ak_perf run of another chat finished first) and checked that no editor had DojoLab open.
- Backup before any write: `ninja_character/start_backup/` (uproject, Config/*.ini, L_Dojo.umap 44992f94...,
  GM_Dojo.uasset, the two verify scripts; SHA256SUMS.txt).

### What was built (run_ninja_port.sh build setup ini check; tools/port_copy.py)
- **C++:** new module `Source/DojoLab` (+ DojoLab.Target.cs / DojoLabEditor.Target.cs, V7 / Unreal5_8; uproject
  `Modules` entry; plugins unchanged). 29 files (15 classes) copied BYTE-IDENTICAL: jutsu (NinjaJutsuComponent,
  NinjaJutsu, NinjaFireball, NinjaHandEffect, NinjaGroundSeal, NinjaVisual), look (NinjaVisualBodyComponent), movement
  (NinjaTurnComponent, NinjaRunStyleComponent), compile/link only (Stance, LockOn + CameraModifier, Combat), load-clean
  only (AirJump, FreeLook). `PublicDefinitions DEMOGAME_1_API=DOJOLAB_API` keeps every copied file unedited.
  `[CoreRedirects] +PackageRedirects /Script/DemoGame_1 -> /Script/DojoLab` in DefaultEngine.ini. Build.bat
  DojoLabEditor Win64 Development -NoHotReloadFromIDE: 22 actions, 0 warnings, 0 errors, 51 s ->
  `Binaries/Win64/UnrealEditor-DojoLab.dll`. **DojoLab is now a C++ project: every commandlet / -game run needs this
  DLL built (rebuild after any re-sync, editor closed).**
- **Camera (D3, new code, `DojoNinjaCameraSubsystem`):** sets `DDCVar.NewGameplayCameraSystem.Enable` per spawned pawn
  before possession: 0 for a ninja (has UNinjaJutsuComponent), the original 1 back for GASP's SandboxCharacter_*. The ini
  keeps GASP's 1. `dojo.ninja.camera_switch 0` disables it.
- **Content:** 510 packages, 955,262,255 bytes (473 core + 37 feature-only), all at DemoGame_1's /Game paths: no path
  collision, so no remap and no redirector. Every source hash matched the survey; every destination was absent (no
  DojoLab file overwritten); every copy re-hashed. The 13 DIFFERENT packages (MetaHumans/Common hair / lash materials,
  skeletons, control rigs, GASP SK_Mannequin, IMC_Sandbox) were NOT copied: DojoLab's are kept (D1 option A).
- **One commandlet (dj_ninja_setup.py, 51 s), after the module was built:**
  - BP_NinjaGasp: SCS components NinjaAirJump, NinjaLockOn, NinjaStance, NinjaFreeLook, NinjaCombat removed (5 of 5),
    compiled, saved. Left: NinjaJutsu (4 jutsu: ShadowClone, GreatFireball, Summoning, Chidori), NinjaRunStyle,
    NinjaTurn, VisualOverride (BP_NinjaVisual -> BP_MH_PlayerDefault + CloakMH), SpringArm 375 / socket 0 / lag 12,
    Camera(NotUsedByDefault) FOV 85 auto-activate on, GameplayCamera auto-activate off, GASP's own components.
  - IMC_NinjaGasp: 24 rows -> the 8 jutsu rows (F / pad Y, Two / d-pad left, Three / d-pad up, Four / d-pad right); 11
    actions unmapped (LMB, RMB, E, Q, C, Z, Tab, LeftAlt, 1, 5, F1 reach GASP's IMC_Sandbox again).
  - New `/Game/Dojo/Blueprints/GM_DojoNinja` (child of GM_Dojo, DefaultPawnClass BP_NinjaGasp_C). GM_Dojo unchanged
    (sha256 ad9def16..., still SandboxCharacter_CMC).
  - L_Dojo World Settings GameMode GM_Dojo -> GM_DojoNinja, saved (L_Dojo sha256 now 3cd28a0e...). PlayerStarts P1
    (1450, -1050, 95) yaw 0 and P2 (2950, -1050, 95) yaw 180 unchanged (measured before and after).
  - Then (plain text) DefaultEngine.ini GlobalDefaultGameMode -> GM_DojoNinja.
- Verify scripts: `dj_verify.py` gate 4 and `dj_sc_verify.py` gate 5 now accept GM_DojoNinja (GM_Dojo's child with
  BP_NinjaGasp) as project default / world override and still require GM_Dojo -> SandboxCharacter_CMC (syntax-checked;
  not run: the next sc_verify needs run_armory_sync.sh first, see rev 4 above).

### Checks (measured)
- **Headless load, fresh process (dj_ninja_check.py, -nullrhi): 6 / 6 gates PASS.** A: all 15 classes load as
  /Script/DojoLab and through the old /Script/DemoGame_1 path. B: 510 / 510 ported packages load, 0 redirectors. C: the
  hard /Game dependency closure of GM_DojoNinja, GM_Dojo, BP_NinjaGasp, BP_NinjaVisual, IMC_NinjaGasp and the 4
  DA_Jutsu = 2,412 packages, 0 missing, 0 private. D: no unwanted component, no null class, 4 jutsu, turn + run style,
  BP_NinjaVisual NinjaVisualBody / MetaHuman (BP_MH_PlayerDefault_C) / CloakMH, capsule r 30 / hh 86 = the
  SandboxCharacter_CMC CDO, centred camera. E: ini + world override GM_DojoNinja, GM_Dojo -> CMC, 2 PlayerStarts
  unchanged, 2,563 actors. F: 8 jutsu rows.
- Log scan (tools/scan_log.py): 0 failed-to-load / missing / invalid-class / skeleton / compile lines on the ported
  paths in the setup, check and -game logs; the other lines are the same as the earlier verify.log baseline
  (4 profiler DLLs, 5 DDC pak notices, GASP LevelBlock construction-script warnings).
- **-game probe, L_Dojo (dj_ninja_game_probe.py via run_ninja_probe.ps1, -RenderOffscreen, real keys through
  `Input.+key`; a warm pass, then a measured pass with HighResShot stills):**
  - Spawn: BP_NinjaGasp_C via GM_DojoNinja + PC_Sandbox at P2. `LogDojoNinja: camera switch ... 1 -> 0`. Camera:
    cvar 0, SpringArm + Camera(NotUsedByDefault) active, GameplayCamera inactive, **lateral 0.0 cm, 375 cm behind,
    70 cm above, FOV 85** (DemoGame_1's centred camera).
  - Look: MetaHuman active, Body SKM_MH_PlayerDefault_BodyMesh visible with ABP_MH_NinjaBody, Manny host
    (SKM_Manny_Simple) hidden, CloakMH (SKM_BlackCloak_MH) attached to Body as a Leader Pose follower and visible; 6
    groom components visible, 3 with a groom (Hair, Eyebrows_M_SlightArch, Eyelashes_S_Fine; Fuzz / Mustache / Beard
    empty, as the MetaHuman BP ships). Head bone 77.5 cm above the
    capsule centre on the MetaHuman vs 72.3 on the hidden Manny (DemoGame_1 measured ~5 cm too).
  - Movement: W 575 cm/s with `ninja run ON A_NinjaRun_InPlace (575 cm/s, rate 1.20)`; Shift+W 1000 cm/s with
    `A_NinjaSprint_InPlace` (sprint probe, both key orders). The main probe's sprint step stayed at 575 (Shift pressed
    1.5 s into the run, sampled 0.9 s later); the dedicated sprint probe reached 1000 both ways; cause not found.
  - Jutsu, by real keys: F casts ShadowClone -> 2 BP_NinjaGasp_C at 2.4 s (clone with MetaHuman + cloak), back to 1 by
    9 s; Two casts GreatFireball -> 1 BP_GreatFireball_C at 1.65 s, gone by 6.5 s; Three casts Summoning ->
    BP_SummoningSeal_C decal at 2.45 s (seal visible on the gravel), gone by 9 s; Four casts Chidori -> finishing
    DA_Jutsu_Chidori with 1 BP_ChidoriLightning_C from 1.55 to 3.55 s, gone by 7.5 s.
  - GASP route (`L_Dojo?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C`): SandboxCharacter_CMC, cvar 1, GameplayCamera
    active (lateral 50 cm, 180 cm behind, FOV 80: GASP's own rig), run 500 / sprint 700 cm/s. The reference pawn and its
    camera are intact.
  - Stills: `ninja_character/build/probe/shots/01..12*.png` (1920x1080), contact sheet `build/probe/sheet.png`.
    Labels 01 "back" / 02 "front" are swapped in the stills: after the warm pass the body faced +X while the camera
    looked -X.

### Open
- D1 not measured: hair / brow / lash colour vs DemoGame_1's male reference shots, framed the same (option B-hair only
  if it fails). R4 (skin cache off project-wide): the hair sits on the head in the stills, not measured in motion.
- C7 perf delta not measured (run_game_perf.ps1 with the ninja pawn).
- dj_verify / dj_sc_verify edits not run in Unreal (sc_verify needs run_armory_sync.sh first).
- Known DemoGame_1 gaps came along (R12): hand effects on Manny's bones, no face animation, skin through the cloak in
  deep poses, jutsu and clones local only, foot-lock IK inert; the 37 feature-only packages are unreferenced after
  B4 / B5 (kept for a later port, D4).
- The probe's spring-arm close-up used set_editor_property, which re-ran BP_NinjaGasp's construction script and
  re-created the visual child actor (harmless for the test); the probe now writes the attribute directly (untested).
- Lock `DojoNinjaPort` still held by this chat for the follow-up stages. Nothing committed or pushed.

## 2026-10-02 - NINJA CHARACTER: play tests in -game (L_Dojo, from the build)

Output `WorkFiles/dojo/build/ninja_character/test/` (`RESULTS.json` / `RESULTS.md` = every number below,
`OVERVIEW.jpg`, per-suite reports, frames, videos, logs and log scans). Every run was a separate offscreen
`UnrealEditor-Cmd -game` process on L_Dojo (`run_ninja_playtest.ps1`: waits for any UnrealEditor-Cmd, stops if a DojoLab
editor is open; another chat's ArmoryLab ak_perf run was waited out). Real keys through `Input.+key`, the camera moved
by plain attribute writes (DemoGame_1's mh_cam.py rule), stills by HighResShot, frame sequences shot in slow motion
(time dilation 0.25-0.35) and assembled to MP4 at real GAME speed (`tools/pt_media.py`, ffmpeg concat with the
recorded game-time durations). Reference pawn runs: `L_Dojo?game=/Game/Dojo/Blueprints/GM_Dojo.GM_Dojo_C`
(SandboxCharacter_CMC). check_sync --side dojo before: the same 25 `FAIL: sha` (Exports/ArmoryKit, owed by the armory
chat) + 1 STALE as the build stage, nothing owed by the dojo side; no shared file touched. Nothing committed.
**PRIVATE LAB ONLY (R7)**: the videos carry the Naruto jutsu (names, look); they are muted, but nothing here is to be
published.

### Harness (new, Scripts/dojo/unreal)
- `dj_ninja_playtest.py` (suites look / move / jutsu / routes; a generator timeline in the Slate post-tick; a 10 Hz
  recorder of speed, location, movement mode, jutsu state, the visual host's UpperBody / DefaultSlot activity + montage +
  NinjaSealWeight, the GASP mesh montage, effect actors, cloak bounds + Chaos cloth interactor, MetaHuman-vs-Manny-host
  bone deltas, camera offsets, ninja audio components playing, new Niagara systems near the pawn; the jutsu component's
  own delegates OnJutsuSeal / Completed / Cancelled / HandPlanted / CloneSpawned), `dj_ninja_perf.py` (the finish
  stage's fp_game_perf method with the pawn placed in view), `run_ninja_playtest.ps1` (-Sound keeps the audio device,
  the probe mutes the output with `au.MuteAudio 1`), `dj_ninja_fixjump.py`. Tools in `ninja_character/tools/`:
  `pt_media.py`, `pt_compare_demogame.py`, `pt_scan.py` (errors / ensures per test window from `DJ_PT_MARK` markers),
  `pt_summary.py`.

### 1. Look (suite look; `test/look/`)
- Visible body = the MetaHuman (`Body` SKM_MH_PlayerDefault, Manny host hidden), cloak `CloakMH` visible, Leader Pose
  on the body. Stills at DemoGame_1's own beauty framing (cloak_mh_test.ps1 Cam(): arm 300, pitch -8, FOV 70, no lag,
  1600x900): front, side a, back, side b, close (face / cowl), three-quarter close; plus the gameplay camera.
- **Against DemoGame_1's male shots** (`Saved/Claude/Shots/metahuman_cloak/final/b01-b06`, read only; the same
  projection, so pixels compare 1:1; `look/compare/pairs_all.jpg`): character dark-mask IoU front 0.858, side a 0.870,
  back 0.843, side b 0.782, close 0.809, three-quarter 0.894; box deltas a few px left / right (the top deltas of
  front / side b / close are the dojo wall's dark coping touching the head in the mask, not the character). The
  remaining difference is the cloth's momentary pose and the lighting (sunset dojo vs DemoGame_1's day field), which is
  also why the hair colour (D1) is NOT judged from these pairs.
- **Cloth simulates**: Chaos interactor 1 cloth, 2,547 dynamic + 873 kinematic particles every sample; the per-frame
  solver time changes on 78-100 % of samples while live (1.5-3.5 ms) and is frozen on the SUSPENDED control (2 %, one
  value) - the measurement can tell a frozen cloth. No explosion: the cloak bounds' half extents stay <= 100 / 73 / 98 cm
  in every recording (run, sprint, stop, jumps, 15 traversals, 12 jutsu). Run -> stop slow-motion side view:
  `look/video/look_run_stop_side.mp4` (the cloak flares behind and settles).
- **No T-pose / reference pose**: MetaHuman hands / feet / head vs the Manny host <= 7.5 cm in every sample of every
  suite (idle 5.3); MetaHuman hand span 66-111 cm (a T-pose is ~170). The one exception is a shadow clone's FIRST sample
  (40-44 cm, 0.1 s) while it is hidden for CloneRevealDelay inside the smoke; the frames show it appear already posed
  (`jutsu/video/clone_spawn_zoom.jpg`).

### 2. Movement (suite move, ninja vs SandboxCharacter_CMC; `test/move*/`)
- Capsule r 30 / half height 86 on both (the dojo's checks use exactly these). Step 45, walkable 44.765 deg, JumpZ 500.
- Walk (LeftControl toggle) 200 / 200 cm/s; run 575 (ninja run clip) vs GASP 500; sprint 1000 (ninja sprint clip) vs
  GASP 700, both key orders in all three ninja runs (W, then Shift 1.2 s later: 575 -> 1000 within 0.25 s). The build probe's
  single 575 sample after Shift is not reproduced (cause not identified). The ninja's own speeds are DemoGame_1's run-style design.
- Jump: standing 127.5 cm on both. **Found and fixed (T1)**: a second SpaceBar in the air gave the ninja a plain engine
  double jump to 243-244 cm (GASP: 127.5). DemoGame_1's double jump is the removed UNinjaAirJumpComponent's flip PLUS
  `jump_max_count` 2 written on the BP_NinjaGasp CDO by its setup_ninja_gasp.py; the build removed only the component.
  `run_ninja_port.sh fixjump` (dj_ninja_fixjump.py) set the CDO to SandboxCharacter_CMC's value read live (1); backup
  `test/backup_before_fixjump/` (BP sha256 0bfbdc23... -> 480ec955...); dj_ninja_setup.py applies it on a re-sync. After:
  double press 127.5 cm standing and sprinting (move_run3), fresh headless `check` 6 / 6 gates, 0 errors.
- Camera: ninja cvar 0, centred: lateral offset 0.0 cm at idle and over a whole run (max |lateral| 0.0); GASP's pawn
  keeps its own rig (cvar 1, lateral 50, FOV 80).
- **Traversal sample** (15 climb routes of the layout: 3 wall tops +2.0, both cisterns +1.25 and eave pads +3.0, both
  crates +1.25, shed band +2.5, pavilion pad +3.25, vending +1.75, veranda +0.5, plinth +1.0, weapon-rack hurdle):
  stance - 2 m, run in, SpaceBar. Ninja and GASP play the SAME GASP montages on every route (Catch_Cliff_high_standF,
  Catch_Mantle_low_stand on the veranda, Mantle_1_0_run on the plinth, Catch_Hurdle_high_stand over the rack) and stand
  on the same tops (10 / 15 on top; the other 5 carry on past the top: pads onto the roof, vending onto the wall top,
  over the rack). Rise e.g. wall 199.5-200.3 cm, cistern 184 cm on both. Pose delta during traversals <= 7.2 cm.
  Frames: `move/video/trav_Wall_S_W1.mp4`, `trav_WeaponRack_W.mp4`.

### 3. Jutsu (suite jutsu; `test/jutsu/` frames + run 2 `test/jutsu_run2/` with the delegates and a clean log)
Each of the 4 cast standing, walking (200 cm/s) and running (575 cm/s), by its real key; slow-motion frame sequences
-> `jutsu/video/jutsu_<name>.mp4` (+ `_sheet.jpg`).

| jutsu (key) | seals (OnJutsuSeal) on UpperBody | completed | result: first -> last seen (s) | audio | FX |
|---|---|---|---|---|---|
| ShadowClone (F) | 3 / 3 montages @UpperBody | yes, all 3 modes | clone (2nd BP_NinjaGasp, AIController, MetaHuman + cloak) 0.75 -> 5.6 | HandSeal, JutsuRelease, Voice_KageBunshin | NS_CloneSmoke |
| GreatFireball (Two) | 6 / 6 | yes | BP_GreatFireball 1.15 -> 3.3-3.6 (bursts) | HandSeal, JutsuRelease, Voice_GreatFireball, FireballLaunch | NS_Fire, NS_Explosion_Small |
| Summoning (Three) | 5 + the thumb-bite opening = 6 @UpperBody, palm slam @DefaultSlot | yes (HandPlanted at 1.46) | BP_SummoningSeal decal 1.5 -> 7.2 | HandSeal (releases silently by design) | decal (no Niagara) |
| Chidori (Four) | 3 / 3, charge stance @DefaultSlot | yes | BP_ChidoriLightning on hand_r 0.97 -> 4.9 | HandSeal, SFX_Chidori | NS_ChidoriArcs |

- UpperBody slot active on every casting sample (e.g. 10 / 10, 6 / 6), NinjaSealWeight 1.0; no cancel in 12 / 12 casts.
- **Works while walking and running** (DemoGame_1: "you can walk and sprint while casting"): speed stays 200 / 575 for
  the whole seal chain; the finishers (palm slam, Chidori stance) stop the ninja by design (SetFinisherLock).
- `LogNinjaJutsu: voice ... (playing)` for both voice jutsu (the build probe ran -NoSound: "not spawned").
- Log: 0 errors, 0 ensures, 0 LogNinja warnings in every run of this stage (pt_scan: only the known startup baseline,
  GASP LevelBlock construction-script warnings and editor-UI factory notices). Jutsu run 1 had ONE ensure, caused by the
  harness itself (`-dpcvars=au.MuteAudio=1`, a cheat cvar from a device profile, ConfigUtilities.cpp); the runner now
  mutes by console command and run 2 is clean.
- Known DemoGame_1 behaviour (unchanged): the fireball turns the ninja to the camera's yaw; the hand effects use Manny's
  bones (R12).

### 4. The dojo's gameplay checks with the new pawn (suite routes; `test/routes*/`)
- **All 88 layout walk routes walked by the pawn itself** (walk gait, W + steering by the control yaw, capsule as
  spawned): ninja 88 / 88 as expected after the walker fix (run 1 87 / 88: ARM_deck_strip_in_front_of_hero_table folds
  back on itself and stalled BOTH pawns - a walker projection bug, fixed to waypoint order; re-walked: reached), incl.
  the armory interior 35 / 35 (ARM_*, HALL_*, interior CONTROLs), 33 / 33 CONTROLs blocked (1v1 ring at the open gate,
  wall top outside, alley fences, alley pockets, rear-yard corners, extension walls), 7 / 7 BR routes clear with the
  Dojo/Boundary_1v1 group's collision off. Max deviation on clear routes 0.18 m (0.41 at the folded route's U-turn).
  SandboxCharacter_CMC: the same outcome on every route (0 differences).
- **1v1 escape attempts** (12: sprint / run jumps at the open-gate ring, mantle onto the W / S / E wall tops then jump
  outward, jumps off the wall top, sprint jumps at both alley fences from the veranda, ground jumps at the fences,
  veranda corners into the rear yard): **0 leaks** for the ninja (before and after T1) and for GASP's pawn. The ring
  holds the capsule at y -0.70 / x -0.70 / x 44.70 (ring at -1.1 / 45.1); mantles onto the wall tops worked
  (Climb_Start_2_5_run).
- Capsule = SandboxCharacter_CMC's (r 30 / hh 86), so the offline floods / arcs of the finish stage (r 30, apex 2.55 m
  double-jump ceiling, 650 cm/s arcs) still bound the ninja: its apex is now 1.28 m; its 1000 cm/s sprint is faster than
  the arcs' 650 but the floods are speed-independent (flying-capsule superset) and the real sprint-jump attempts did not
  leak.
- dj_sc_verify.py (fresh, read-only; the canonical showcase/verify.json restored byte-identical afterwards, this run's
  copy in `test/sc_verify/verify_ninja_pawn.json`): **8 / 9** - gate 5 gameplay PASS with the edited code (ini + world
  override GM_DojoNinja -> BP_NinjaGasp, parent GM_Dojo; GM_Dojo still -> SandboxCharacter_CMC), gate 7 GASP trace 23 /
  23; gate 9 FAIL only on the pre-existing armory-hall record (sync.json rev 3 vs manifest rev 4: run_armory_sync.sh
  owed, see rev 4 above). 0 errors in the log.

### 5. Frame time
`dj_ninja_perf.py` (the finish stage's perf_cool method: scalability 3, t.MaxFPS 0, no vsync, 1920x1080 at the
configured screen percentage r.ScreenPercentage 0, every frame's delta over 10 s after an 8 s settle, no ProfileGPU),
with the controlled pawn placed IN VIEW: on the floor 450 cm in front of CAM_PlayerEyeSand / 350 cm in front of
CAM_AK_CW_WestAisle, facing the camera; plus the pawn's own camera at P1. Alternating processes ninja, GASP, ninja, GASP;
2 segments per view per process = 4 per view per pawn. **Idle machine** (gated: no blender.exe for 60 s, no other
Unreal process; `perf/background_load.csv`: 0 Blender, CPU 22 % mean):

| view | pawn | mean ms | p95 ms avg (min / max of 4) | vs 16.7 ms p95 |
|---|---|---|---|---|
| CAM_PlayerEyeSand | ninja | 17.15 | 20.53 (20.17 / 20.87) | miss |
| CAM_PlayerEyeSand | SandboxCharacter_CMC | 15.25 | 21.19 (19.82 / 22.27) | miss |
| CAM_AK_CW_WestAisle | ninja | 17.21 | 20.68 (20.23 / 21.58) | miss |
| CAM_AK_CW_WestAisle | SandboxCharacter_CMC | 13.87 | 19.01 (17.99 / 20.59) | miss |
| own camera (P1) | ninja | 13.22 | 17.10 (16.10 / 18.24) | miss |
| own camera (P1) | SandboxCharacter_CMC | 12.71 | 17.72 (16.63 / 18.22) | miss |

- **The ninja's cost, measured: +1.9 ms mean at PlayerEyeSand, +3.3 ms at WestAisle (close up, 3.5 m), +0.5 ms from
  its own camera; p95 -0.7 / +1.7 / -0.6 ms** (the p95s overlap between the two pawns at PlayerEyeSand and the own
  camera). It is a steady per-frame cost (MetaHuman body + grooms + Chaos cloak + the live retarget), not hitches.
- **16.7 ms p95 is missed at both views by BOTH pawns** in today's level state: GASP's own pawn in view gives 21.2 /
  19.0 ms p95 (the finish stage measured 17.8 / 16.7 without a pawn placed in the frame and in its "+2.9 ms after 11:18"
  state). So the target needs the level-side levers already listed under the finish stage (interior light draw
  distance, fewer glow lights / MegaLights, the +2.9 ms step), and for the ninja: MetaHuman body / groom LOD settings,
  the cloak's cloth LOD or a sim-distance cull. Not changed here (port rules: report).
- A first perf pass ran while another chat's Blender renders (up to 6 processes, GPU 70 % mean) were on the machine; it
  is kept as `perf/contaminated_run1/` and NOT used (GASP p95 up to 30.7 ms there).

### Changes to DojoLab in this stage
- `Content/Ninja/Blueprints/BP_NinjaGasp.uasset`: T1 only (CDO jump_max_count 2 -> 1). PORT_PROVENANCE.md section 3.1 /
  5a regenerated (`tools/write_provenance.py`; 508 / 510 packages still byte-identical, 29 / 29 C++ files). No C++, ini,
  level, plugin or other asset changed.

### Open
- 16.7 ms p95 not met at PlayerEyeSand / WestAisle by either pawn (section 5); the ninja adds +1.9 / +3.3 ms mean in
  view. Levers above; owner's call.
- D1 hair / brow / lash colour vs DemoGame_1: not judged (the lighting differs: sunset dojo vs day field); a same-light
  comparison (a neutral-lit spot or DemoGame_1's sky preset) would settle option B-hair. Silhouette match measured
  (IoU 0.78-0.89).
- R4 (skin cache off project-wide): grooms stay on the head through run / sprint / jumps / traversal / jutsu in the
  frames; not measured numerically.
- dj_sc_verify gate 9 needs run_armory_sync.sh to record rev 4 (pre-existing, not the port). dj_verify.py (grey-box
  stage) not run.
- Known DemoGame_1 gaps unchanged (R12): hand effects on Manny's bones, no face animation, jutsu and clones local only,
  foot-lock IK inert. PRIVATE LAB ONLY (R7).
- Lock DojoNinjaPort still held by this chat for any follow-up stage; release it when the port is closed.

## 2026-10-02 - armory_hall revision 5 synced into DojoLab (perf2 round, SYNC stage; the C++ project)

Rev 5 is the armory chat's (owner asked): entry mat removed (SM_AK_EntryMat / AKI_0335 retired), upper side windows
backlit by SM_AK_Window_Paper_35_W/_E x10 (AKI_0618..0627; M_AK_HWinPaperW/E, T_AK_HWinPaper_BC), ArmoryLab-only light
values, every other ArmoryKit FBX re-exported with the same geometry. Notes and numbers:
`ninja_character/perf2/sync/` (SYNC_NOTES.md, RESULTS.json, logs, sc_verify, routes). Backup first:
`perf2/sync/start_backup/` (L_Dojo.umap 3cd28a0e..., Content/ArmoryKit + ArmoryHall + NinjaPack, armory_sync jsons,
manifest.json, verify.json, this file; SHA256SUMS.txt). No other Unreal process ran; nothing committed or pushed.

- check_sync --side dojo at the start: exit 2 (synced 3, needs 5). DLL current: Build.bat DojoLabEditor -> "Target is up
  to date", 0 actions, UnrealEditor-DojoLab.dll unchanged (sha256 18065c72...); run_armory_sync.sh needed no change
  for the C++ module.
- run_armory_sync.sh: files 198 packages, 10 copied (7 M_AK_* masters, M_AK_HWinPaperE/W, T_AK_HWinPaper_BC), 0
  missing, 0 drift. Unreal 115 s: 65 / 65 SM_AK_* re-imported (0 FBX drift vs the manifest), 470 / 470 instances placed
  (461 - 1 + 10), bounds max 0.070 cm, 0 gate failures, 0 envelope violations, 124 travelling + 1 level light, 12
  shadowed <= 14, 83 / 83 shell ids; DJ_ArmoryHall actors 593 -> 602; new DojoLab children MI_DJA_AK_HWinPaperW / E
  (the existing EMISSIVE_SCALE rule: 38.5 -> 2.615, 30.66 -> 2.082). 0 errors. L_Dojo sha256 now 30aff252...
- check_sync --side dojo: exit 0. ArmoryHall lock claimed, `bump_manifest.py --record-sync DojoLab` (manifest diff:
  last_synced.DojoLab 4 -> 5 only), released; check_sync exit 0 again.
- dj_sc_verify (fresh): 9 / 9 gates PASS, incl. 5_gameplay (GM_DojoNinja -> BP_NinjaGasp; GM_Dojo ->
  SandboxCharacter_CMC) and 9_armory_hall (sync rev 5 = manifest rev 5, 0 instances wrong / missing). Level actors
  2,556 -> 2,565.
- Interior walk routes in -game, the pawn itself (40: every ARM_*, HALL_*, interior CONTROL + the centre door):
  ninja 40 / 40 as expected (31 reached, 9 blocked), SandboxCharacter_CMC 40 / 40, 0 differences, 0 errors / ensures.
  Centre-door route ends with the feet at 0.522 m (0.603 before: the mat is gone). Max deviation 0.43 m on both pawns
  = the play-test stage's waypoint-order walker metric (GASP 0.16 before that fix on the same routes), not a level change.
- Open: the window paper casts shadows in L_Dojo (dj_armory_look.NO_SHADOW_PIECES is empty; the armory says no shadow
  in ArmoryLab) - not changed (no look changes in this run). SM_AK_EntryMat.uasset stays in DojoLab, unreferenced. Lock
  DojoNinjaPort kept: the port still has open items (16.7 ms p95 / ninja perf levers, D1, R4) and the perf2 round
  continues.

armory_hall synced rev 5

## 2026-10-02 - NINJA CHARACTER: clean perf profile (perf2 round, PERF stage; measured, nothing applied)

Output `ninja_character/perf2/` (RESULTS.json; `main/MAIN_TABLE.md`, `levers/LEVER_TABLE.md`, `levers/visual/`,
`levers/profilegpu_PES_ninja.json`, `timeline/`, `contention/`, `tools/`). Harness: `Scripts/dojo/unreal/dj_ninja_perf2.py`
(dj_ninja_perf.py's method + `csvprofile` per window with -csvGpuStats, runtime levers, HighResShot, ProfileGPU, jutsu by
real key) via `perf2/tools/run_perf2.ps1` (one UnrealEditor-Cmd at a time, stops if DojoLab is open) and `tools/chain.sh`
(idle gate + background monitor). Backup first: `perf2/start_backup/` (this file, Saved GameUserSettings.ini, SHA256SUMS of
L_Dojo 30aff252..., BP_NinjaGasp, GM_Dojo, GM_DojoNinja, DefaultEngine/Game.ini, the DLL). After the stage all of them
are byte-identical and no file under DojoLab Content / Config is newer: **no lever was applied to the project; every
lever was a runtime change in a -game session, which is never saved.** No look change, nothing committed.

### Machine
- Idle gate before every chain (no blender.exe, no UnrealEditor*.exe, GPU < 40 % for 60 s): passed in 63 s each time; no
  other Blender / Unreal process during any measured run (`*_background_load.csv`: CPU %, clock %, GPU, top-5 processes).
- 1920x1080, `scalability 3`, t.MaxFPS 0, no vsync, r.ScreenPercentage 0. **Screen-percentage caveat (verify_r9):**
  Saved GameUserSettings sg.ResolutionQuality=100 makes the -game start at r.ScreenPercentage 100; the run sets 0 (the
  project curve), which is also 100 % at 1080p, so the numbers are the same either way here (ProfileGPU: TSR
  1920x1080 -> 1920x1080). At 1440p and above the saved file would still override the 75 % curve.

### 1. Clean profile (3 windows per view per pawn; processes alternated ninja, GASP x3, same view order; CSV = stat unit)
| view (pawn in view) | pawn | FrameTime mean / median / p95 | GameThread mean | RenderThread busy | GPU mean / p95 |
|---|---|---|---|---|---|
| CAM_PlayerEyeSand | ninja | 11.99 / 11.92 / **12.84** | 4.86 | 9.64 | 11.13 / 11.39 |
| CAM_PlayerEyeSand | GASP | 11.15 / 11.14 / **11.85** | 4.22 | 7.93 | 10.50 / 10.77 |
| CAM_AK_CW_WestAisle | ninja | 13.28 / 13.28 / **14.23** | 5.21 | 10.04 | 12.42 / 12.66 |
| CAM_AK_CW_WestAisle | GASP | 11.39 / 11.37 / **12.36** | 4.37 | 7.23 | 10.75 / 11.00 |
| CAM_RiverRapids | ninja | 13.49 / 13.47 / **14.50** | 4.52 | 6.95 | 12.71 / 13.12 |
| CAM_RiverRapids | GASP | 13.21 / 13.20 / **14.34** | 3.96 | 6.09 | 12.48 / 12.84 |
| own camera at spawn | ninja | 10.76 / 10.76 / **11.72** | 4.62 | 7.68 | 10.06 / 10.32 |
| own camera at spawn | GASP | 9.49 / 9.49 / **10.28** | 4.13 | 6.63 | 8.86 / 9.09 |

- **16.7 ms p95 is met at every view by both pawns**; worst single window 14.67 ms; the 3 windows agree within 0.4 ms.
  Ninja minus GASP: +0.84 / +1.89 / +0.28 / +1.27 ms mean (PES / WA / RR / own camera).
- Timeline probe (ninja, PES, 30 back-to-back 10 s windows over 6 min, then RR, WA, PES again): 11.89-12.06 ms mean,
  12.59-13.32 p95 the whole time; **no step over time and none after visiting other views**.

### 2. Why the earlier 17-21 ms: machine state, not the level
- The finish stage's +2.9 ms step (its CSVs of 2026-10-01 are still in DojoLab/Saved/Profiling/CSV; PES 11:17 vs 12:33):
  the scene work is identical (124 lights, 13 unbatched, 1,215 vs 1,206 draw calls, GPU 10.58 vs 10.49 ms) while EVERY
  CPU stat grew: game thread x1.60, RenderOther x1.82, RenderLighting x2.06, RDG x2.30, worker anim tasks x1.98. That is a
  uniform CPU slowdown, not content (it also appeared mid-run at one camera change and stayed for every later run).
- Reproduced in kind with this stage's own CPU load (busy-loop processes during the same profile, `contention/`):
  8 loaders PES 13.30 / 14.76, 20 loaders 14.71 / 16.30 (clean 11.99 / 12.84) ms mean / p95, GPU unchanged,
  RenderLighting x1.62, RDG x1.71, game thread x1.14, CPU clock 142 % -> 123 % of base. The play-test stage's gate checked
  only Blender and GPU, not CPU, and its background log came out empty, so what loaded the CPU then is not known.
- Reading: the earlier 17-21 ms are not a property of the level or the ninja. A perf gate needs a CPU-idle check too.

### 3. Where the time goes (ninja at PES, clean): the render thread is the critical path
- Render thread busy 9.6 ms (RenderOther 2.9, RenderLighting 2.1, RDG_CollectResources 0.9) plus waits; GPU 11.1 ms
  (one ProfileGPU frame, 10.79 ms: RenderDeferredLighting 1.67 + 0.29, ShadowDepths 1.60, BasePass 0.91, Nanite VisBuffer
  0.89, RayTracingScene 0.40, VolumetricCloud 0.29, TSR about 1.2; hair 0.13 ms as cards at 4.5 m). No single hot spot.

### 4. Levers (scratch -game sessions, one at a time, A/B against the base window just before it; n = 2-3; visual cost
from 1920x1080 HighResShots against the same-view base-to-base noise; `levers/LEVER_TABLE.md`, `levers/visual/pair_*.jpg`)
| lever | gain mean / p95 ms | visual cost (measured) | verdict |
|---|---|---|---|
| interior lights max draw distance 25 m (+5 m fade), PES | 0.67 / 0.67 (lights drawn 124 -> 32) | hall interior through the door darker: doorway luma 59.8 -> 51.4 | owner's call; WA 0.07, RR 0.01 (no gain inside) |
| all interior lights off (reference), PES | 0.98 / 1.02 | doorway luma 61.9 -> 43.9 | reference only |
| interior shadows off (12 shadowed lights) | PES 0.12, WA 0.49 / 0.39 | WA: light leaks, frame luma 28.0 -> 30.6, 4.5 % px > 24 | not worth it |
| rev-5 window paper (10 actors): shadows off / hidden | PES 0.08 / -0.01, WA -0.02 / -0.04 | hidden darkens WA (luma 28.0 -> 23.3) | **not a cost** |
| Niagara RT cvars off (level) | -0.01 / 0.00 | none | the level FX are already out of RT (census: 0 of 110 Niagara components) |
| r.RayTracing.Culling.Radius 30 m | 0.23 | frame luma 89.9 -> 95.6, 6.7 % px > 24 | reject |
| ninja hidden (reference = the ninja's whole cost) | PES 0.85, WA 1.95, RR 0.49 | - | - |
| **grooms (hair, brows, lashes) hidden** | PES 0.25, **WA 1.43**, own camera 0.22 | bald head | the ninja's main close-up cost |
| hair cards instead of strands / r.HairStrands.MinLOD 2 or 4 | **WA 1.44-1.46**, PES 0, own camera 0 | at 3.5 m the hair DISAPPEARS (`levers/visual/WA_head_strands_cards_minlod2_hidden.jpg`); at 4.5 m it already renders as cards | not usable as is |
| cloth suspended (CloakMH + the hidden Cloak) | 0.03-0.06 | cloak frozen | cloth is not a frame cost |
| groom simulation off | 0.04 | within noise | no |
| MetaHuman forced LOD 3 (all skeletal meshes) | 0.03-0.15 | within noise | no (body / face already LOD 1 at 4.5 m) |
| skin cache off (r.SkinCache.Mode 0) | -0.01 | the skinned cypress trees change | no |
| Niagara RT off during jutsu | Chidori 0.08-0.16, Fireball 0.15-0.5 | none | small; the jutsu FX are in RT by default (NS_ChidoriArcs, NS_Fire) |

- Groom LOD from Python: `GroomComponent.SetForcedLOD` is not exposed, so the hair cvars above were used.

### 5. Jutsu cost (cast by real key)
- From the ninja's own camera (the gameplay case; no cast 10.18 / 11.15): Chidori 10.50 / 11.54, Fireball 10.84 / 11.95,
  Summoning 10.25 / 11.29, ShadowClone 10.46 / 11.47 ms mean / p95. All far under 16.7.
- Fireball flying INTO a camera (PES, the ninja placed facing the camera): p95 20.5-22.7 ms, a ~10-frame GPU burst up
  to 49 ms while the flame fills the screen (translucent overdraw), not CPU. The FIRST fireball of a session also had one
  121 ms hitch (shaders created 1128 -> 1149). Chidori at PES 13.8 / 15.0.

### Recommendations (owner decides; nothing applied)
1. No level or ninja lever is needed for 16.7 ms p95 at 1080p on an idle machine (worst views 12.8 / 14.2 / 14.5 / 11.7).
2. Gate future perf runs on CPU load too (CPU % and clock), not only Blender / GPU; re-measure rather than lever when
   numbers jump.
3. If headroom is wanted: the interior-light draw distance (0.67 ms from the courtyard, darker doorway) is the only
   level lever with a real gain; the window paper, Niagara RT and MetaHuman LOD are not costs.
4. Ninja close-ups: the strand grooms cost 1.4 ms at 3.5 m. A cards fallback needs the groom's cards LOD fixed (it shows
   nothing at close range today) before any LOD bias is worth trying.
5. Fireball: a fade / size cap near the camera and a warm-up (PSO precache) of its systems would remove the in-camera
   burst and the first-cast hitch.

### Open
- The play-test stage's 17-21 ms run: the cause of that day's CPU slowdown is not identified (no CPU log).
- Harness note: one extra lever_3 session ran while this stage's own contention loaders were running (a chain left alive
  by a background task); it is kept as `levers/lever_3_run2_underload*` (windows +0.4 to +1.9 ms) and not used in the
  tables; the clean lever_3 data are `levers/lever_3_summary.json` (first block of lever_3.log.guard.txt).
- Lock DojoNinjaPort kept (port items D1, R4 still open).
