# Kit 9: training props, build notes

## 2026-09-27, BUILD stage (Blender only, no Unreal)

**What exists.** Seven separate assets. Each one has its own mesh, its own UCX hulls, its own collection
(`C_DKP_Train_*`) in `Assets/Dojo/TrainingProps.blend` and its own FBX in `Exports/DojoKit/Props/training/`. All were
exported through `Scripts/pipeline` (`export_fbx`, kind `static`, metres). `qa_check` reports **0 hard fails** on all
seven.

**Scripts** (all in `Scripts/dojo/props/training/`):
- `make_training_textures.py`: textures
- `build_training_props.py`: meshes, UCX, UV0/UV1, QA, export, `layout_training.json`, `measure.json`
- `render_training.py`: Cycles renders
- `make_training_sheets.py`: sheet layout and reference crops
- The side-by-side comparisons use `Scripts/armory/side_by_side.py` as it is (read-only use).

**Pivot and frame.** Every prop sits on the ground at z = 0. The front is -Y. The pivot is the base centre, except for
the posts and dummies, where it is the post or body axis. The Y sill of the post base runs further behind the post
than in front of it.

### Sizes (all computed, `measure.json`), and deviations from the sheet

| Asset | Built | Sheet (at its silhouette scale) | Why |
|---|---|---|---|
| SM_DKP_Train_Makiwara | 0.84 x 0.66 x **1.50** m; post 0.20 m square; rope pad +0.78..+1.40 (17 wrap turns of 2.7 cm rope, 2 binding turns of 3.8 cm at each end) | 1.91 m tall | The prompt says about 1.5 m, and the prompt wins. The base keeps the sheet's metric size (0.83 m sill) |
| SM_DKP_Train_StrikingPost | 0.84 x 0.66 x **1.90** m, same base | 1.92 m | No number in the prompt, so the sheet's height is used |
| SM_DKP_Train_WoodenDummy | 1.02 x 1.08 x **1.90** m; body r 0.16; 3 arms (r 0.052, 0.66 m from the axis) at +1.50 / +1.38 / +1.15; bent leg to the ground in front; framed base 1.0 x 0.9 | 1.94 m | Sheet. The grey-box stand-in was 1.7 m |
| SM_DKP_Train_LongArmDummy | 1.76 x 1.22 x **1.85** m; body r 0.185; arm r 0.055 at +1.40, tip 1.10 m from the axis; cross base 1.30 x 1.20 | 1.85 m | Sheet |
| SM_DKP_Train_WeaponRack | **2.00** x 0.65 x **1.137** m, EMPTY; 9 top pegs (155 mm pitch, tops +1.075); 2 cradle rails of 8 notches (116 mm wide, 45 mm deep) | 2.91 x 1.66 m | Spec: 2 m long, under 1.25 m. The sheet was scaled uniformly by 0.687, so its proportions are kept |
| SM_DKP_Train_Bench | **1.80** x 0.45 m, seat **+0.50**, 0.11 m two-board top | row-3 silhouettes are inconsistent (the bench would be 4.8 m long) | Real-world size, keeping the sheet's ratios (H/L 0.28, depth about height) |
| SM_DKP_Train_Stool | top 0.42 x 0.30 m, seat **+0.48**, splayed legs (feet 0.45 x 0.35 m) | same problem as the bench | Real-world size, the sheet's ratios |

**Sheet-to-model interpretations** (the sheet has front and side views only; the top view is ours):
- The makiwara brace sits behind the post (+Y). The striking face is -Y, and the brace takes the push.
- The dummy's arms point forward-left, forward-right and forward-left, at heights stepped as on the sheet. Square
  through-tenons with wedges show at the back.
- The long arm points along +X, 5 cm in front of the axis. It passes through a square root block, so the side view
  shows that block at the front edge, as the sheet does.
- The rack's rails sit in front of the uprights and project 0.115 m. Its side view is rendered from -X, so the rails
  point right, as on the sheet.
- **Deviations kept on purpose:**
  - The sill ends have iron shoes. The sheet has wooden blocks with small iron plates.
  - The makiwara pad is stacked rope turns, not a single continuous helix. A helix left visible gaps at the bindings in
    r0.

### Rules (spec section 3 and 5.3)
- **R3 (flat top at least 1.0 m deep):** does not apply. None of these props is a climb prop.
- **R8, low items at 1.25 m or less:**
  - rack +1.137
  - bench +0.50
  - stool +0.48
- **R8, thin uprights at 0.4 m or narrower:**
  - post 0.20 m (0.276 m at the rope bindings)
  - makiwara collar 0.29 m
  - dummy body 0.32 m
  - long-arm body 0.37 m
  - The bases are wider (0.84-1.30 m), but only 0.14-0.16 m high, plus braces.
  - Open point: the long arm reaches 1.10 m at +1.40 m. It is thin (0.11 m), and its UCX blocks the pawn.
- **Collision class and traversal** (`layout_training.json`): all seven are class **thin**, meaning pawn block,
  camera ignore, visibility ignore. The Unreal profile is set per class at import.
  - Posts and dummies: traversal `none`.
  - Rack, bench and stool: traversal `vault`.

**UCX hulls** (convex, named `UCX_<node>_NN`):

| Asset | Hulls | Parts |
|---|---|---|
| Makiwara | 3 | base hull, post, pad |
| Striking post | 2 | base, post |
| Wooden dummy | 7 | base, body prism, 3 arms, 2 leg segments |
| Long-arm dummy | 4 | base, body, arm, root block |
| Rack | 3 | upper frame slab 0.29 m deep (vault), 2 foot and brace hulls |
| Bench | 1 | box |
| Stool | 1 | frustum |

### Placement (`layout_training.json`, grey-box frame, UE = x*100, -y*100, z*100, yaw = -rot_z)
- **Taken from the grey-box:**
  - Makiwara at (6.5, 7.0) and (37.5, 7.0).
  - Striking posts at (6.5, 14.0) and (37.5, 14.0).
  - Wooden dummies at (2.0, 12.0) and (42.0, 12.0).
  - Racks at (4.0, 8.5) and (40.0, 8.5), long axis along Y.
- **PROPOSED** (not in the grey-box):
  - Long-arm dummies at (2.3, 15.0) and (41.7, 15.0).
  - Benches at (1.0, 8.5) and (43.0, 8.5).
  - Stools at (1.0, 10.3) and (43.0, 10.3).
- The makiwara face the yard, so the trainee stands in the yard. The dummies and racks face the floor.
- Everything stays in the X 0-8 / 36-44 yards.

### Materials and textures (`Exports/DojoKit/Props/training/Textures/`, DirectX normals, ORM = AO / rough / metal)

| Material | Texture | Tile / density | Kind |
|---|---|---|---|
| M_DKP_Train_Timber | T_DKP_Train_Timber 2048 | 2.0 m, **10.1 px/cm** measured on UV0 | **generic** timber: swap for `M_Env_Wood` in the look pass |
| M_DKP_Train_TimberEnd | T_DKP_Train_TimberEnd 1024 | 0.5 m (end-grain faces) | **generic** |
| M_DKP_Train_Iron | T_DKP_Train_Iron 1024 | 0.5 m | **generic** iron (Steel master tint later) |
| M_DKP_Train_Rope | T_DKP_Train_Rope 512 | one 0.105 m lay x once round | **unique** (straw rope) |

- The textures are procedural and original, with periodic FFT noise. The seam test passes on all four
  (`textures_report.json`).
- The timber is at 2x the style guide's 5.12 px/cm, as in the armory timber. The props are seen from 1-3 m. A texture
  LOD bias in Unreal can halve it.
- The rope's three strands are also in the mesh: the tube radius follows the strand lobes, in phase with the texture.
- No emissive parts in this kit.
- **Palette:**
  - Timber albedo mean #4B3627 (the style guide's #3A2E26, warmed toward the sheet)
  - Iron #3B3732
  - Rope #896A48
- The measured render p50 of the wood is close to the sheet's (r2, below).

### QA
- **0 hard fails** on all 7 (58-74 checks each; `qa_report.json`).
- **Waived** by house practice for tiling materials (armory, grey-box and ground kits): `uv_no_overlap` on UV0, and
  `uv0_tile_range` on the makiwara (rope U runs past the range).
- **UV1:**
  - smart project, 0-1, no overlap
  - lightmap pack on the makiwara, whose helix-like rope folds under projection
- **Triangles:**

  | Asset | Triangles |
  |---|---|
  | Makiwara | **32,444** (the rope geometry). Nanite on |
  | Rack | 4,836 |
  | Long-arm dummy | 3,776 |
  | Wooden dummy | 3,360 |
  | Striking post | 2,876 |
  | Bench | 1,464 |
  | Stool | 932 |

  - The style guide puts Nanite on over about 2k triangles, and props are the Mid tier ("Nanite or LODs"), so no
    LOD1-2 were made.
  - If the makiwara must be lighter, lower `sides` and `step` in the rope call. 8 / 0.012 m now; 6 / 0.02 m gives
    about 12k triangles.

### Render rounds
- **r0:** first full set. Wood too pale and grey. The rope helix left gaps. The line-up props were hidden by a
  naming bug.
- **r1:**
  - rope as stacked, lobed turns
  - timber warmer and less stripy
  - line-up fixed
  - side-by-sides added
- **r2 (current):**
  - studio key 1400 -> 750 W and timber darker, so the front-face wood p50 moved from (162,125,101) to (118,89,70);
    the sheet's dummy body is (77,52,34) and post (84-102, 68-77, 57-60)
  - dummy leg lowered to the sheet: knee +0.57, foot 0.53 m in front
  - arms r 0.045 -> 0.052
  - line-up reframed
- **r2 outputs** (`renders/r2/`):
  - `SM_DKP_Train_*_sheet.png`: silhouette, front, side, top, 3/4
  - `closeups_*.png`
  - `lineup_sunset.png`: warm 3000 K sun at 9 degrees on pale gravel
  - `sbs_*.png`: reference crop next to our silhouette, front and side, at the same height
  - `sbs_sheet_*.png`: reference crop next to our full sheet

**Open for the review / look pass:**
- The sheet's wood shows stronger edge wear and grime (lighter worn edges, darker crevices). Tiling textures cannot
  place those per edge. A baked AO or edge mask, or a vertex-colour pass, in the look pass would close that.
- The rope reads clean. The sheet's straw rope is hairier.


## 2026-09-27, FIX ROUND f1 (Blender only, no Unreal)

This section supersedes the BUILD section above where they differ (sizes of the rebuilt parts, texel density, LODs,
triangle counts, placements). Renders: `renders/f1/`. All numbers below are computed (`measure.json`,
`qa_report.json`, `export_report.json`, `clearance_check.json`, `textures_report.json`).

### Measurer fixes
1. **Walk route P1 (x = 1.2 / 7.2).** New placements in `layout_training.json` (mirrored in the east yard):
   - Bench (1.0, 8.5) -> **(0.5, 8.5)**; stool (1.0, 10.3) -> **(0.5, 11.0)** (clear of the west wall stance (0.36, 10.0)).
   - Striking post (6.5, 14.0) -> **(6.33, 14.0)**, east (37.67, 14.0): the 0.45 m back sill now clears x = 7.2.
   - Wooden dummy (2.0, 12.0) -> **(2.03, 12.0)**, east (41.97, 12.0): the new 0.92 m frame clears x = 1.2 too.
   - Re-checked with walk_check.py's rule (AABB of every UCX hull, 0.45 m step, 0.20-1.72 m band) against every
     grey-box ground route and ground climb stance: new script section `clearance()` in `build_training_props.py`,
     result `clearance_check.json`, **passed at r = 0.35 m (spec) and 0.30 m (GASP)**. Margins at r = 0.35 on P1:
     striking post 0.064, bench 0.112, long-arm dummy 0.144, stool 0.155, wooden dummy 0.320 (its base hull tops out
     at +0.435 m, under the 0.45 m step, so walk_check treats it as step-on; the frame itself clears by 0.014 m).
     Nearest stance: the west / east wall climb stance, 0.25 m clear (the bench). The rack hurdle stance (3.46, 8.5)
     sits 0.10 m from the rack by design (it is the vault approach). walk_check.py itself was not run (it reads the
     grey-box blend, which this run does not own); the grey-box owner can rerun it with this layout.
2. **LODs (STYLE_GUIDE 7).** Every FBX now ships LOD0-2 in a LodGroup (the kit 1 / taiko pattern: pipeline
   `decimate_lods` + `make_lod_group`, hulls renamed `UCX_<name>_LOD0_NN`, QA on every LOD, sidecar with screen sizes
   1.0 / 0.5 / 0.25). Triangles LOD0 / LOD1 / LOD2:

   | Asset | LOD0 | LOD1 | LOD2 |
   |---|---|---|---|
   | Makiwara (ratios 0.40 / 0.15) | 33,552 | **13,420** | 5,032 |
   | Striking post | 9,264 | 4,632 | 2,316 |
   | Wooden dummy | 13,112 | 6,556 | 3,278 |
   | Long-arm dummy | 11,604 | 5,802 | 2,900 |
   | Weapon rack | 11,352 | 5,676 | 2,838 |
   | Bench | 6,580 | 3,290 | 1,644 |
   | Stool | 3,892 | 1,946 | 972 |

   The makiwara's rope UV1 is re-packed on its LODs (a collapse folded two lightmap triangles). LOD0 counts rose
   because long members are now cut every 15 cm and edges are 2-segment rounds (the weathering vertex colour needs the
   vertices); bolts were made cheaper (8 sides, 3 dome rings) to pay for it.
3. **Texel density: halved to the guide.** Timber 1024 px over 2.0 m, TimberEnd 512 over 1.0 m, Iron 512 over
   1.0 m. Measured on UV0: Timber 5.05-5.09 px/cm (5.75-5.81 on the two dummies, whose round bodies wrap a whole tile
   round the circumference), TimberEnd 5.04-5.08, Iron 5.11-5.53. No sign-off needed any more.

### Blind-judge fixes
- **Wooden dummy leg:** one round member (r 0.056 m, slightly flattened sides, 20 sides, smooth) swept from a mortise
  at +0.64 (a third of the body) through a rounded knee at (-0.30, -0.33, +0.60) to a foot at (-0.40, -0.63, +0.035),
  outside the front of the frame (frame edge y = -0.46).
- **Wooden dummy base:** square frame 0.92 x 0.92 m of 0.12 x 0.13 m beams, raised 0.17 x 0.17 x 0.19 m corner blocks
  with iron caps and rivets (2 per outward face plus one low), 2 rivets per frame beam face, two diagonal sleepers
  that carry the body (no spacer blocks), four short diagonal knee braces (top +0.36 = 18.9 % of the height, about
  52 degrees) into short cleats on the body.
- **Faceting:** round bodies 48 sides, arms 32 sides with elliptical domes down to a tip vertex (no flat disc); the
  inner dome shows end grain; body tops have a 22-30 mm round-over; the long-arm arm is round with a 0.85 r dome.
  Round members map V as whole tiles (bodies) or a mirrored ramp (thin rounds), so no texture seam runs down them.
- **Weathering (all props):** timber albedo reworked (70 grain lines per tile, raised-grain scratches, scuffs, dark
  pits and flecks, checks, weaker large-scale blotch so members match). Plus a face-corner vertex colour **Wear**
  (STYLE_GUIDE 5, "weathering by vertex colour"): R grime = ray-traced AO (24 rays, 0.16 m, against the prop and the
  ground), G edge wear = the bevel faces of every flat member and the round-over rings, broken by noise, B ground dirt
  (fades out by 0.45 m). The review material darkens by R, dusts by B and lightens / desaturates by G; M_Env_Wood reads
  the same channels in the look pass. The FBX files carry it (LayerElementColor present). Measured render median on
  the front ortho: dummy body (82, 58, 42) against the sheet's (88, 60, 39); striking post (84, 61, 47) against
  (95, 73, 58).
- **Bench:** 13 cm top of three planks (was 11 cm, two), legs 9.5 cm (was 7.5), end overhang 0.213 m past the legs,
  long stretchers at 37.5 % of the height, through-tenoned with wedges outside the legs, pegged low side stretchers,
  bolt heads at the plank ends.
- **Makiwara:** pad +0.80..+1.35 (0.15 m = 10 % bare post above), 14 coil turns of 26 mm rope with random lay phase
  and a frayed radius, two 48 mm collar turns each end, rougher straw texture with loose fibres. Base and sleeve 18 %
  smaller than the striking post's (sill 0.69 m, sleeve top +0.44 = 29 %).
- **Makiwara and striking post sleeve:** four close boards round the post, an iron angle strap down each vertical
  corner with rivet rows on both flanges, flush side cleats taking the braces, X sill of three chunky butted blocks with
  rivets and small end plates. The post is now one 20 x 20 cm timber (the two-board seam showed as a worn light stripe
  down every face).
- **Weapon rack:** heavy inner foot block and a knee brace on the inside face of each upright, the outer cleat (and the
  loose-looking bolt) removed, rails spaced 0.139 / 0.141 / 0.173 m apart, top-rail through-tenons 9.5 cm proud with
  a 4 x 21.5 cm wedge, rail rivets moved onto the rail ends.
- **Long-arm dummy:** base beams 0.16 x 0.15 m, end blocks 0.20 m with iron caps and rivets, rounded body top.
- **Stool:** 9.6 cm top of three planks (20.0 % of the height), 6.6 cm legs, through-tenons proud of the legs, pegged
  side stretchers, rivets on the leg faces at the stretchers and aprons.
- **Collision overlay:** every model sheet now ends with a 3/4 view of the UCX hulls (translucent orange with wire).

### Materials (for the look pass)
| Material | Texture | Kind |
|---|---|---|
| M_DKP_Train_Timber | T_DKP_Train_Timber 1024 / 2 m | generic (M_Env_Wood) |
| M_DKP_Train_TimberEnd | T_DKP_Train_TimberEnd 512 / 1 m | generic (M_Env_Wood end grain) |
| M_DKP_Train_Iron | T_DKP_Train_Iron 512 / 1 m | generic (M_Steel_Master tint) |
| M_DKP_Train_Rope | T_DKP_Train_Rope 512 (one lay x once round) | unique (straw rope; M_Fabric_Master candidate) |

No emissive parts in this kit. All four sets pass the seam test.

### QA
0 hard fails on all 7 LOD0 meshes (58-74 checks each) and on every LOD1-2. Waived as before: `uv_no_overlap` on UV0
(tiling), `uv0_tile_range` on the makiwara.

### Still open
- The sheet's wood is still a little richer (more contrast, more pitting) than ours in the studio renders; the rope has
  no fibre fuzz (a hair-card shell or a look-pass material effect would add it).
- The bench / stool / long-arm dummy placements remain PROPOSALS; the striking post and wooden dummy moved 0.17 m and
  0.03 m off the grey-box stand-ins. The grey-box / kit 1 owner should confirm and rerun walk_check.py.
- The long arm (reach 1.10 m at +1.40 m) still blocks the pawn; it is 0.144 m clear of route P1.


## 2026-09-28, PROP MATERIAL + SHAPE PASS r2 (group A; renders in `renders/r2/`)

Lock `DojoTrainingProps` claimed at the start and released at the end. Headless Blender only, no Unreal, no commit.
Scripts changed: `build_training_props.py`, `render_training.py`, `make_training_sheets.py`; new
`make_rope_fuzz.py`. The BUILD stage's old r2 files (sbs sheets, 7 close-ups) were moved to
`renders/r2/_build_stage_r2_20260927/` so the r2 folder holds this pass only. Numbers are from `measure.json`,
`qa_report.json`, `export_report.json`, `clearance_check.json`, `textures_report.json` or r2 render medians.

### Materials: the shared library (`Scripts/dojo/materials`, v1.0.0)
| Slot | r2 material |
|---|---|
| Timber faces / end grain | `M_DJ_TimberDark` (4 m) / `M_DJ_TimberDarkEnd` (2 m) |
| Iron (straps, bands, rivets) | `M_DJ_Iron` (2 m) |
| Makiwara rope | `M_DKP_Train_RopeFuzz`: the library rope maps `T_DJ_Rope_*` plus a fibre-fuzz layer (`make_rope_fuzz.py`: 3,300 stray 1 px fibres mostly along the strands, a soft halo that half-fills the strand grooves, a softer lay in the normal, AO lifted). Built on the library node graph; Unreal = MI of M_DJ_Lib_Opaque, UseWear off, with `T_DKP_Train_RopeFuzz_{BC,N,ORM}` |

- UVs in library tile units (the Prop kernel's own per-member mapping with the library tiles; rope U = 4 lays per
  tile at 3.2 diameters per lay, V once round).
- Weathering: the library's `bake_wear` replaces the f1 bake (same channels: R grime, G edge, B dirt), with R
  re-sampled 30 % in from each face corner against the prop plus a ground plane (`regrime`, the f1 fix for buried
  corners). Wood area with edge wear G > 0.5: 14-33 % per prop.
- Tone band: every timber member is pinned rigidly into v 0.27-0.51 of the library tile (`pin_band_v`; the library
  TimberDark tile runs 12-15 / 43-67 / 95-124 in luminance across V, which made neighbouring members black or
  orange). Widest member span 0.218 tile (rack), none over the band. Same band on body, arms and leg, so the dummy's
  leg now has the body's stain.
- Retired: `T_DKP_Train_{Timber,TimberEnd,Iron,Rope}_*` moved to `retired_f1_textures/` (not deleted).

### Shape fixes (judges / measurers)
| Prop | r2 |
|---|---|
| Makiwara + striking post base | SYMMETRIC: a 0.30 m square centre block with four equal arm blocks (reach 0.344 / 0.420 m), a flush cleat centred on every sleeve face and four identical braces (tops +0.309 / +0.392); no short front block, no single back brace |
| Wooden dummy leg | one octagonal hewn member (flat faces, 0.112 m) from a mortise at +0.57 (30.0 % of 1.90 m), thigh rising to a tight knee at (-0.29, -0.32, +0.60), shin to the foot at (-0.40, -0.64), 0.124 m outside the frame front, front-left; through-tenon + wedge at the back of the body like the arms |
| Wooden dummy base | 0.92 m square frame of 14 x 15 cm beams, raised WOODEN corner blocks 19 x 19 x 22 cm with a thin 6 mm iron trim band (3.5 cm) and rivets only, diagonal sleepers, a 0.40 m seat block under the body, four 45 deg knee braces to +0.38 (20.0 %) |
| Seat bodies | dummy body foot at +0.13 into a 0.15 m seat block; long-arm body foot at +0.16 into a 0.44 m square, 0.18 m seat block: no gaps under the round bodies |
| Round parts | arm domes 40 sides, 14 dome rings, the whole dome end grain (no side-grain lines converging on the tip) |
| Makiwara rope | 6 sides (was 8), 22 mm steps (was 12), no geometric lobes, fray x 0.6: LOD0 20,872 tris (was 33,552) |
| Long-arm dummy base | same treatment: wooden end blocks 20 x 20 x 23 cm with iron trim bands, the seat block, four 45 deg braces to +0.37 (20.0 %) |

### Placement check (walk_check semantics, `clearance_check.json`)
Passed at r = 0.35. New per-prop report for route P1_round_west_yard_past_tree: wooden dummy 0.364 m, striking post
0.444, **bench 0.462, stool 0.505** (both over 0.35, `P1_bench_stool_ok_035: true`), long-arm 0.915. Placements
unchanged from f1.

### QA and export
0 hard fails on all 7 and every LOD (`uv_no_overlap` waived, plus `uv0_tile_range` on the makiwara, as before).
LOD0 / LOD1 / LOD2 triangles: makiwara 20,872 / 8,348 / 3,130; striking post 9,016 / 4,508 / 2,254; wooden dummy
15,420 / 7,710 / 3,854; long-arm 12,688 / 6,344 / 3,172; rack 11,352 / 5,676 / 2,838; bench 6,580 / 3,290 / 1,644;
stool 3,892 / 1,946 / 972. All over 2k: Nanite (decision 2026-10-02), LODs shipped as well. Pivots, sizes, collision
classes and hull counts unchanged (makiwara 3, post 2, dummy 7, long-arm 4, rack 3, bench 1, stool 1).

### Renders (`renders/r2/`, Cycles, OIDN denoised)
`SM_DKP_Train_*_sheet.png` (silhouette, front, side, top, 3/4, UCX overlay), `closeups_*.png` (new: makiwara base
front, dummy leg mortise, dummy corner block), `lineup_sunset.png`, the new `context_sunset.png` (the west yard as
laid out, in front of a library plaster/rubble wall stand-in), `sbs_*.png` and `sbs_sheet_*.png` (reference | ours)
for all seven.

Measured (front ortho medians, sRGB): makiwara post 60,46,38 (sheet 82,66,55); dummy body 65,47,37 (sheet
87,59,38); rope 152,117,75 (sheet 147,108,71).

### Open after r2
- Timber renders about 25-30 % darker than the sheets: the library tile's only band wide enough for whole members
  is its mid band (mean luminance about 52). A flatter library tone band would fix every kit at once.
- The rope's fuzz reads in close-ups; at sheet distance the pad is still cleaner than the sheet's hairy rope.
- The weapon rack's foot blocks keep their solid iron sleeves (not in this pass's list).


## 2026-09-28, ROUND 3 LOOK PASS (props track; renders in `../round3/training/`)

Lock `DojoTrainingProps` claimed at the start and released at the end. Headless Blender only, no Unreal, no commit.
The material library was not edited. Scripts changed: `build_training_props.py` and `make_rope_fuzz.py`. Inputs:
the round-2 props-A judge (6.5): blocker 3 (makiwara rope) and deltas 6-10.

### Makiwara rope (judge blocker 3 / delta 6)
- **One continuous helix** of 17 mm straw rope (r2 27.6 mm rings, so about 60 % of the gauge) wound tight round the
  post from +0.8165 to +1.3335. The pitch is 16.2 mm (neighbouring turns press 0.8 mm together, so no light gaps).
  The coil makes 31.9 turns, with no ring seams.
- Bulkier binding bands top and bottom: two 33 mm turns each, irregular. They cover the coil's two ends, which fixes
  r0's "helix gaps at the bindings".
- 384 loose straw fibres (1-1.5 mm, 1-2.8 cm) stick out of both edges of each band, spread evenly by arc length
  (a first try bunched them at the corners).
- Fibre fuzz in the material (`make_rope_fuzz.py`, `RopeFuzz_r3`): 4,200 + 1,300 stray fibres (r2 2,600 + 700) and a
  stronger halo. Fibre cover 15.9 %; median 145,114,74.
- Pad z, post and base unchanged.
- The post height stays 1.50 m (BUILD stage decision: the prompt's 1.5 m wins). The sheet shows it about 1.89 m, as
  tall as the striking post (judge delta 12). **For the user.**
- LOD0 27,484 tris (Nanite).

### Long-arm dummy (delta 9)
- The sheet's front elevation shows one continuous base beam with its end blocks and no foot block toward the viewer.
  The base is now a **T**: the full X beam with two end blocks, plus one arm running back (+Y). The front (-Y) arm is
  gone.
- Chunky cleats now stand 4.2 cm proud of the body's round on +-X and on the back arm, so they flank the post in the
  front view. Three 45 deg braces.
- The seat block is flush with the beam top (0.15 m) and tucks under the body.
- The sheet is inconsistent here: its side view shows the base beam on both sides. Front view followed, as the judge
  asked.

### Dummy arms (delta 7, the mirrored 'butterfly' knot)
- The long arm and the wooden dummy's three arms no longer use the mirrored V ramp.
- V is now linear round the arm, with the single seam on the underside (`cyl(..., side_vec=(0,0,-1), v_linear=True)`).

### Weapon rack (delta 10)
- Rails thinner and further apart:
  - rail depth 0.10 m (r2 0.16);
  - top rail 7 cm tall (r2 9.1);
  - cradle rails 6 cm under their teeth;
  - gaps 0.163 / 0.158 / 0.200 m (r2 0.139 / 0.141 / 0.173).
- The f1 inner foot blocks and long knee braces are gone. Each upright now has:
  - a short tapered WEDGE block (5.7 cm at the foot, 2.5 cm at the top, +0.14 to +0.40) against its inner face,
    with a bolt;
  - a plain cleat up its outer face (the sheet's side view).
- The iron caps on the foot blocks are gone; they are plain wood with rivets.
- The low stretcher now runs into both foot sills. It floated once the inner blocks were removed.
- Height 1.137 m unchanged (R8 under 1.25).

### Stool (delta 8)
- No proud tenons, wedges or pegs.
- Every rail now ends flush inside the legs, with round bolt heads on the leg faces at each joint.
- The front / back aprons are gone: the sheet's front view shows the top resting on the legs. The side aprons stay.

### Checks / QA / export
- Placements unchanged. `clearance_check.json`: passed at r 0.35, and P1 bench/stool ok.
- `qa_check`: 0 hard fails on all 7 and every LOD.
- LOD0 / 1 / 2 tris:

  | Prop | LOD0 | LOD1 | LOD2 |
  |---|---|---|---|
  | Makiwara | 27,484 | 10,992 | 4,121 |
  | Striking post | 9,016 | 4,508 | 2,254 |
  | Wooden dummy | 15,420 | 7,710 | 3,854 |
  | Long-arm dummy | 10,844 | 5,422 | 2,710 |
  | Rack | 10,984 | 5,492 | 2,746 |
  | Bench | 6,580 | 3,290 | 1,644 |
  | Stool | 3,708 | 1,854 | 926 |

- 7 FBX re-exported through Scripts/pipeline.
- Bug fix in `Prop.build`: the convex-hull clean-up now de-duplicates the vertices to delete (bmesh raised on a
  repeated vertex).

### Renders (`WorkFiles/dojo/build/props/round3/training/`)
`SM_DKP_Train_{Makiwara,LongArmDummy,WeaponRack,Stool}_sheet.png`, `closeups_*.png`, `context_sunset.png`, and
`sbs_r3_{makiwara_rope,longarm,rack,stool}.png` (reference | ours).

### Open
- The timber is still the library's mid band, darker and greyer than the sheets (library owner).
- The makiwara height (above).
- Re-import `T_DKP_Train_RopeFuzz_*` for the showcase.
