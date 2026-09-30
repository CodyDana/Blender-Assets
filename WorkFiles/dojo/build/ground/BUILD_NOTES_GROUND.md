# Dojo kit 2: the ground (build notes)

**Date:** 2026-09-27. **Workflow:** kit 2 (ground), built in Blender only (headless, `--factory-startup`), no Unreal.
**Lock:** `DojoGround` (claimed at the start, released at the end of the stage).
**Scope:** `WorkFiles/dojo/DOJO_QUEUE.md`, "Kit 2 breakdown". **Sizes:** `WorkFiles/world/DOJO_ARENA_SPEC.md` (the spec wins over
the image). **Look:** `References/Dojo/dojo1_reference2.png` (the view from the gate), `dojo1_reference1.png` (overview).

## Files

| What | Where |
|---|---|
| Texture generator | `Scripts/dojo/ground/make_ground_textures.py` |
| Kit builder (pieces, UCX, layout, QA, export) | `Scripts/dojo/ground/build_ground_kit.py` |
| Context renders | `Scripts/dojo/ground/render_ground.py` |
| Texture sheet renders | `Scripts/dojo/ground/render_texture_sheet.py` |
| Reference / ours sheets and stats, sheet composer | `Scripts/dojo/ground/compare_ground.py` (system Python, PIL) |
| Blend | `Assets/Dojo/DojoGround.blend` (collections `Kit` and `Assembly`) |
| Meshes | `Exports/DojoKit/Ground/SM_DKG_*.fbx` (r0: 47; f1: 68) |
| Textures | `Exports/DojoKit/Ground/Textures/T_DKG_<Set>_{BC,N,ORM}.png` + `T_DKG_Macro_M.png` |
| Layout (armory layout.json schema) | `layout_ground.json` (this folder) |
| Reports | `textures_report.json`, `qa_report.json`, `export_report.json` |
| Renders | `renders/r0/` (final = round 3; `round1/`, `round2/` kept); `renders/f1/` (fix round f1) |
| Collision check | `Scripts/dojo/ground/measure_collision.py` -> `collision_check.json` (f1) |

Rebuild in order (f1; renders go to `renders/f1/`, r0 is kept):
```
blender -b --factory-startup --python Scripts/dojo/ground/make_ground_textures.py
blender -b --factory-startup --python Scripts/dojo/ground/build_ground_kit.py
blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/measure_collision.py
blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/render_ground.py -- --samples 128 --out <abs>/renders/f1
blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/render_texture_sheet.py -- --samples 64 --px 512 --out <abs>/renders/f1
py Scripts/dojo/ground/compare_ground.py WorkFiles/dojo/build/ground/renders/f1 --sheet
py Scripts/dojo/ground/compare_ground.py WorkFiles/dojo/build/ground/renders/f1
```
(Pass `--out` as an absolute path: Blender resolves a plain relative render path elsewhere.)

## Stage 1: study of the reference (measured)

**Camera fit of dojo1_reference2.** The sand fields' side edges converge at image row 160-167 (left 167, right 160); the
near sand edge is at row 903 and the far edge at row 488; the full 28 m floor is 2042 px wide at the near edge (the
left corner is off frame: extrapolated along the side edge) and 908 px at the far edge. Ratio 2.25, so with the spec's
17 m depth the near edge is 13.6 m from the eye and the far edge 30.6 m. Focal length 72.9 px/m x 13.6 m = 991 px =
24.6 mm on a 36 mm sensor; horizon row 180; eye height 9.7 m (9.9 from the near edge, 9.5 from the far edge).
Result: a LEVEL camera at (22.0, -11.6, 9.7), 24.6 mm, shift_y -0.2507 (camera `C_Establish` in layout_ground.json).
Check against the grey-box hall: the veranda front (+0.5, Y 22) lands at row 451 (image: about 440-462).

The reference is not geometrically possible at spec size: that eye is 11.6 m outside the gate and 9.7 m up, and the
gatehouse roof (eave +3.25 at Y -2.5) would hide the near sand. The render therefore removes the gatehouse and the
south wall from that one view (the reference frames the shot with gate posts instead). The path is also drawn wider in
the image (168 px of 1323 at the near edge = 3.6 m on a 28 m floor); the spec's 2.0 m path is built.

**Rake spacing.** Luminance profiles down the sand columns (x 330-600 and 860-1150), mapped from image rows to ground Y
through the fitted camera, resampled to even Y and Fourier-analysed: period 0.166 / 0.179 / 0.204 m (left field, far to
near bands), 0.170 / 0.179 / 0.177 m (right field), 0.188 / 0.179 m over the whole depth. The same value at every depth
also confirms the camera fit. **Built: 22 lines per 4 m tile = 0.1818 m.** Groove depth (crest to furrow) 1.8 cm
(real raked beds are about 2-3 cm; 2.2 cm read as a corrugated sheet at eye height, round 1).
**Lines run east-west (along X)**, parallel to the gate and hall fronts, as in both references.

**What the ground shows (zoomed crops).** Straight parallel rake lines with crumbly crests; at the path the ridges stop
in round scalloped ends against the slabs; a pale timber board (about 10 cm) round the outer sides of each field, not
along the path; two slab columns with staggered joints (left column joints about half a slab off the right); a gravel
strip then a heavy granite kerb band at the gate; soil beds with rocks and shrubs at the near corners and round the
trees; fine pale grey gravel elsewhere.

**Colour ratios (reference 2, median sRGB).** Sand lit (179,149,131); gravel far (136,107,97), near strip (120-131,
96-101, 89-90); gravel / sand in linear light 0.41-0.55; slabs (147,127,127), a cool mauve grey.

## Stage 2: textures (`make_ground_textures.py`)

Every set is 2048 px over 4.0 m = **5.12 px/cm** (STYLE_GUIDE 6); the sand edge strip is 2048 x 256 px over 4.0 x 0.5 m
(the same density). Normal maps are DirectX (Unreal), computed from heights in metres with true slopes. ORM = AO,
roughness, metal. Seam score = mean |step| across the wrap / mean |step| between interior neighbours (1.0 = seamless):

| Set | Source | Mean BC sRGB | Seam score BC rows/cols | Notes |
|---|---|---|---|---|
| SandRaked | own | (179,167,144), palette sand #B3A791 | 0.97 / 0.97 | 22 lines per tile, crest at v = k/22; crumbly grain, dark/bright grains, crest/furrow tone, AO in the furrows |
| SandEdge | own | (178,166,144) | 1.02 / 0.97 (wraps along U only) | the same phase along U; each ridge ends in a round cap 9.8 cm from the edge; heaped margin |
| Granite | own | (133,130,130), palette granite #8A8680 brightness | 1.07 / 1.01 | mica specks, feldspar flecks, 5-80 cm mottling, a cool mauve cast, cleft relief +-2.5 mm, smoother worn patches |
| Soil | own | (76,61,47) | 0.94 / 1.03 | clods, crumbs, small stones, twigs, damp patches |
| EdgeTimber | own | (151,133,110), palette worn pale timber #9C8466 | 0.97 / 1.04 | grain along U, checks, grey weathering |
| Gravel | **CC0, NOT our own**: Poly Haven gravel_floor_02 | (134,131,133), graded from the scan's (170,166,155) | 0.96 / 0.99 | graded to #8A8789 at 45 % chroma; scan N (nor_dx) re-normalised; scan ARM = our ORM order |
| Macro_M | own | R tint, G roughness, B dirt (0.5 neutral) | 1.06 / 1.04 | 1024 px over 32 m, sampled on world XY |

- **Gravel scale:** the scan's autocorrelation half-width is 5 px, so pebbles are about 10-15 px = 2.0-2.9 cm at the
  4 m tile. Kept at 4 m for the house texel density; the reference's near gravel reads coarser still (about 5 cm).
- **Gravel grade:** first #928C84; it rendered (140,108,83) against the reference's (121,97,91), so it went cooler and
  a touch darker (#8A8789). Final render (140,118,111): lighter than the reference, whose near strip is in shade.
  Kept pale, as the brief asks ("fine pale grey").
- **Edge darkening on the granite** comes from a `Wear` vertex colour on the slab and kerb meshes (1 = clean face, 0 =
  arris), multiplied in as 0.62-1.0: the M_Env_Stone weathering-by-vertex-colour rule. A tiling map cannot know where
  a slab's edge is.
- **Macro variation:** every material multiplies its albedo by (1 + tint (R - 0.5) 2)(1 - dirt max(B - 0.5, 0) 2) and
  adds rough (G - 0.5) 2 to roughness, with the mask on world XY / 32 m (Unreal: WorldPosition.xy / 3200 cm). Amounts
  per material are in layout_ground.json `materials`.
- **Gravel and soil sample on world XY / 4 m** (`coords: world_xy`; Unreal: WorldPosition.xy / 400 cm), so panels of
  any size and position join with no seam; their pieces are never rotated, so the UV0 tangent frame stays world
  aligned for the normal map. Sand, granite and timber sample UV0.
- **Per-slab tone:** the granite material varies each instance by +-10 % (Blender Object Info Random; Unreal
  PerInstanceRandom), as reference 2's slabs differ slab to slab.

## Stage 3: meshes and layout (`build_ground_kit.py`)

**Collision (spec 5.3, class "Ground, floors"): every piece has flat box UCX hulls.** Walk tops at Z 0 for sand, gravel,
soil, slabs (visually 12 mm proud) and the timber boards (25 mm proud); kerbs collide at their top +0.05 (a 5 cm step
against the 0.45 m step-up). Rake grooves, gravel and soil relief are normal-map only. The path bed hull sits at -0.02.

| Family | Pieces | Tris each | Notes |
|---|---|---|---|
| Sand field | `SM_DKG_SandField_13x17` | 6 | one fight-floor half; raked panel 11.9 x 16.8 m + two 0.5 m edge strips (ridges end at the board and at the path); UV v = (y - 8.5)/4 puts a crest on the centre line, so the E half is the same piece turned 180 deg about (22, 10.5) with the same phase; 92.4 rake lines across the field |
| Field edging (timber) | `SM_DKG_SandEdging_Straight_2`, `_Straight_1`, `_Corner` (L, 1 m legs) | 10 / 10 / 16 | 0.10 m wide, top +0.025, round the outer three sides of each half, none along the path (reference 2) |
| Path slabs (granite) | `SM_DKG_PathSlab_100x{60,80,100,120}_{A,B}` | 26 | 1.0 m wide, 6 mm joints, 8 mm chamfer, top +0.012; A/B = two UV offsets; random 0/180 deg; 23 slabs per column |
| Path bed | `SM_DKG_PathBed_2x3` | 2 | soil under the slab joints, -0.02 |
| Gate kerb band (granite) | `SM_DKG_Kerb50_Straight_2`, `_Straight_1`, `_Corner`, `_End` | 26 | 0.50 m wide, top +0.05; the End slopes down to +0.012 at its free end |
| Bed kerbs (granite) | `SM_DKG_Kerb25_Straight_{2,1,0p5,0p25}`, `_Corner`, `_End` | 26 | 0.25 m wide, top +0.05 |
| Gravel panels | `SM_DKG_Gravel_<w>x<d>` (18 sizes used, 0.25-4 m) | 2 | greedy cover of the gravel region on a 0.25 m grid, largest first |
| Soil panels | `SM_DKG_Soil_<w>x<d>` (7 sizes used) | 2 | the same for the beds |

UV0: world-scale tiling at 5.12 px/cm on every piece (QA reads 5.120 px/cm on the panels; it reads the sand piece as
6.36 because it assumes a square 2048 map for the 2048 x 256 edge strip; per axis both maps are 5.12). UV1: Blender's
lightmap pack, 0-1, no overlap. **QA: 47 pieces, 0 hard fails** (tiling pieces waive `uv0_tile_range` /
`uv_no_overlap`, as the armory). **Exported 47 FBX** through `pipeline.export_fbx` (kind static, each with its UCX).

**Zones (spec frame: origin = inside SW corner, X east 0-44, Y north 0-36).**

| Zone | Rect (X0, X1, Y0, Y1) | Source |
|---|---|---|
| Fight floor | 8-36 x 2-19 = 28 x 17 m (two 13 x 17 halves) | spec 4.2 |
| Stone path | 21-23 x 0.5-21.5 = 2.0 x 21.0 m | spec 4.2 (X 21-23, gate to the hall steps; ends under the grey-box step band Y 21.4-21.7) |
| Gate kerb band | 18-26 x 0-0.5 | under the gatehouse roof (X 18-26), reference 2 |
| Beds (W; E mirrored about X 22) | tree 1.5-5.5 x 14-18 (round the tree at 3.5, 16); wall foot 0-1 x 5.5-13.5 and 0-1 x 15.5-27.5 (the side wicket Y 14-15 kept clear); gate corner 6-7.5 x 0-2.25 | reference 2's side beds; the gate beds stop at Y 2.25 so the grey-box climb crate (36.35-37.35, 2.5-3.5) stands on gravel |
| No gravel under | hall + veranda 11-33 x 22-34; corridors 7.5-10.5 / 33.5-36.5 x 29.5-32.5; storehouse 0-7.5 x 27.5-36; residence 36.5-44 x 27.5-36; drum plinth 39-43 x 1-5 | spec 4.4-4.5 (edges 0.1 m under the building walls) |
| Gravel | everything else inside the walls, rear alley included | spec 4.3 |

Areas: sand (incl. boards) 442 m2, path 42 m2, gravel 595.75 m2, soil 78.75 m2; bed kerb run 81 m.
**376 instances, 4448 triangles assembled** (gravel 165 panels, soil 20).

**Sun (layout_ground.json `lights`):** 22 deg up, travelling toward +X and -Y (heading 45 deg: from the north-west),
2700 K. Computed: the grey-box west tree's canopy (+4.0 to +7.5) throws its shadow 9.9-18.6 m along the ray, onto the
west field's near half (X 10.5-16.6, Y 9.0-2.8) as in reference 2; the 2 m wall's shadow stays in the yards. At 12 and
18 deg with heading 25 (round-0 tests) the canopy shadow crossed both fields.

## Stage 4: renders (`renders/r0/`, round 3 final)

| File | What |
|---|---|
| `TEXTURE_SHEET.png` | six materials: 3 x 3 tiles top down (red ticks = tile seams) and a 1.7 m eye close-up; grey world, neutral sun across the rake lines |
| `C_Establish.png` | the fitted reference-2 camera, sunset |
| `C_Overview.png` | the reference-1 style overview: 94 mm, 140 m out, 36 deg down (fitted from ref 1's near/far field widths 809/735 px and the depth/width foreshortening 0.58) |
| `C_PlayerEye.png` | 1.7 m eye in the west field, looking east along the rake lines across the path |
| `SBS_Establish.png` | reference 2 / C_Establish |
| `SBS_GroundCrop.png` | the same pixel box (430-1030, 640-1000) of both, 2x: near path, sand, gravel strip, kerb band |
| `compare_stats.json` | matched-region medians |

Context: the grey-box from the dojo-greybox-kit1 workflow (`Assets/Dojo/DojoGreybox.blend`) is appended read-only into
the render session (never saved), minus its own flat floors and the 1v1 boundary. Its solid canopies throw dappled
shadows for shadow rays only (a review stand-in for foliage). The gatehouse and the south wall are removed from
`C_Establish` only. A grey slab stands in for the gate approach under that camera (kit 1 / kit 12 area).

| Region (C_Establish, sRGB median) | Reference 2 | Ours (round 3) |
|---|---|---|
| Sand, lit (x 850-1100, y 600-700) | 179,149,131 | 173,144,122 |
| Sand, far | 203,165,138 | 171,141,118 |
| Gravel, near strip | 121,97,91 | 140,118,111 |
| Path slabs | 147,127,127 | 143,121,112 |

**Rounds.** Round 0 (scratch tests): sun position, camera-only hiding, an approach slab for the hole under the grey-box
wall line. Round 1: first full set; the slabs read flat and brown, the rake ridges smooth; granite blotches repeated
3 x 3 on the sheet. Round 2: crumbly sand, mottled granite with a per-slab tone, the tile-scale noise removed; the
slabs then read pink. Round 3 (final): calmer, cooler granite.

**Open against the reference (for the look pass, kit 13):**
- The slabs are still a little warmer than reference 2's cool mauve grey (B 112 against 127).
- Our near gravel is lighter than reference 2's (it sits in shade there); gravel pebbles are about 2.5 cm, the
  reference's near strip reads coarser.
- Reference 2's far sand glows brighter (203 against 171): its haze and bounce light, not the albedo (the lit mid sand
  matches within 6/255).
- The rake ridge-end caps read at eye height (texture sheet) but are too small to see from the establishing camera.
- The gate kerb band is 8 m (the gatehouse width); the reference's band runs the full frame because its eye stands in
  the gate.
- No blend masks yet (gravel into sand, moss at the wall foot): kit 11, decals.

**Performance note for Unreal:** 376 small instances (185 of them 2-triangle panels); use instanced static meshes or
merge them in the level's HLOD. Nanite is not needed (every piece is under 30 triangles).

**IP:** no text, crests or marks on any piece or texture. The references are AI images used for layout and look only;
no pixels from them are in any texture.

## Stage 5: fix round f1 (2026-09-27): measurer fixes + blind-judge deltas

Inputs: the measurer's four findings and the blind judge (5.5/10: brightness order backwards, sand read as corrugated
plastic, one cool gravel for everything, black rectangular soil trays) with eleven ranked deltas. Renders in
`renders/f1/`. **QA: 68 pieces, 0 hard fails; 68 FBX exported** through `pipeline.export_fbx` (tiling pieces waive
`uv0_tile_range` / `uv_no_overlap`; the three dressing pieces carry no UCX by spec 5.3, so the export warns "no UCX"
for those only). The six r0 `SM_DKG_Soil_*` panel FBX are no longer part of the kit (the beds replaced them) and were
moved to `Exports/DojoKit/Ground/_superseded_r0/`.

### Measurer fixes

| Finding | Fix | Measured after |
|---|---|---|
| T_DKG_Gravel_ORM wrap seam (AO 1.88 / 1.82, roughness 1.49 / 1.53), inherited from the scan's ARM | `seam_repair()`: a least-squares fit of each channel from seamless predictors of the same pebbles (the scan's disp cavities at 2/4/8/16 px, disp, diff luminance; r2 0.57 AO, 0.64 roughness) plus the scan's own residual taken from mid-tile (continuous across the wrap), cross-faded in over a 24 px (4.7 cm) band at each edge, so the band stays aligned with the pebbles in BC and N | **AO 1.00 / 1.03, roughness 0.96 / 1.04** (BC 0.96 / 0.99, N 0.93 / 1.13) |
| ORM not in the seam score | `save_set` now scores ORM per channel (`seam_score_orm_rows_cols`: ao, rough) for every set | in `textures_report.json` (the sand tile's AO rows read low because its AO is constant along a row; the edge strip does not wrap in V by design) |
| Kerb50_End / Kerb25_End: flat box UCX at +0.050 floated up to 5 cm over the sloped free end | the End hull is now the convex hull of the block itself (the block is convex: planar sloped top, rounded arris); the top slopes from the kerb top to +0.012 + arris at the free end | **float 0.0 / sink 0.0 mm** on a 1 cm ray grid (`collision_check.json`) |
| SandEdging boards +0.025 over a hull at 0 (feet sank 2.5 cm) | boards lowered: top 6-10 mm proud, irregular (a new height every 0.25 m), hull top +0.008 | **float <= 1.5 mm, sink <= 1.9 mm** |
| (minor) gravel under the gate band, 3.99 m2 overdraw | `GATE_BAND` (and the new gate strip) added to the surround gravel's exclusions; a 0.25 m coverage check over the whole compound now runs in the build | **0 holes, 0 overlaps** (`zones.coverage_check_0p25_cells`) |
| (minor) rake relief reported as 1.8 cm | the tile's encoded height is now reported: rake 1.8 cm x the per-line depth variation (+-18 %) + the grain body | **2.4 cm p1-p99** (3.75 cm max-min, a few deep furrow pixels) |

`Scripts/dojo/ground/measure_collision.py` (new) casts rays straight down on every piece's render mesh and UCX hulls
(1 cm grid on small pieces) and writes `collision_check.json`. Sand field, path bed, mortar and gravel panels: 0 float.
Slabs float 8 mm only over the 8 mm rounded arris (0.03-0.05 % of the area); kerb box hulls float 12-14 mm only over
their 12-20 mm rounded arris (the outer 2 cm, 0.04-8 % of the area); beds float <= 7.2 mm and sink <= 11.5 mm (the
Gate beds' steepest rim, where the dome hull is sampled every 0.25 m; tree beds <= 7.6 mm). Every step is under the
0.45 m step-up; the tallest is the gate band at +0.10.

### Judge deltas

| # | Delta | What changed | Measured |
|---|---|---|---|
| 1 | Brightness order: sand must be the brightest plane | sand albedo #B3A791 -> **#DEC9A7** (a deliberate step off the STYLE_GUIDE swatch toward reference 2's cream; still the pale backdrop the palette intends; tile mean sRGB 209/190/158); sun 6.0 -> 7.5 W/m2, sky 0.8 -> 0.6 | C_Establish lit sand **193/160/131** (luma 165), far sand 191/159/129 (ref 203/165/138: the judge's 195-205 is not quite reached); lit surround gravel 166/137/115 (luma 142); gate strip 116/91/75 (luma 95). Order now sand > surround > strip, as the reference |
| 2 | Ridge profile | `(1-d)^1.5` (sharp crest, wide flat trough), crest rounded by a 3 mm blur; per-line wobble std 5 mm (peak 1.57 cm) at 1-3 m wavelength, fading to 0 within 0.48 m of the tile's u edges so the ridges still meet the straight edge strips in phase (the field UV now puts u = 0 at the path-side edge); line-to-line depth variation 10 -> 18 %; grain relief 0.6 -> 0.9 mm; 0.8 % glossier quartz grains (roughness -0.30); crests 0.06 smoother | a test at 7 mm wobble read as dune ripples at eye height, so 5 mm |
| 3 | Rake lines smear with distance | crest/furrow tone baked into BC (+-6 %) plus 9 % furrow occlusion; AO 0.22 -> 0.25 | the lines hold across both fields in C_Establish and C_Overview |
| 4 | Two gravels | **Gravel (surround)**: the CC0 scan re-graded to a neutral warm grey #ABA59E at 40 % chroma (a #AFA491 test rendered 166/132/103, too orange under the 2700 K sun; r0's #8A8789 read lavender). **GravelCoarse (gate strip, new)**: our own pebbles (two jittered-grid layers, 2.3-3.9 cm and 1.1-1.9 cm ellipses, 72 % cover, six grey / brown-grey tones, a per-stone rim darkening baked in as micro-shadow) over the scan as a darker fines bed. Strip zone X 7.75-36.25, Y 0-2 (50 m2, 16 panels) | strip 116/91/75 against ref 121/97/91 (ours a little warmer: B 75 vs 91) |
| 5 | Granite slabs | per-slab value +-15 % and a warm-grey / blue-grey hue lerp (x0.93-1.09 per channel) on frac(random x 17.31) (Unreal: PerInstanceRandom); rounded 8 mm arris and 10 mm cut plan corners; flamed finish (2-6 mm crystal pits, -0.9 mm); joints 6 -> 8 mm, with the path bed (soil) raised to +0.004 as the dirt fill | slab mid 152/125/108 (ref 147/127/127: still warmer, B -19) |
| 6 | Slabs flush / pasted on | slabs +0.012 -> **+0.020** (hull +0.020); the sand strips rise into a berm over their last 8 cm (+10 mm against the slabs, +7 mm against the boards); a 3 cm contact shade baked into the SandEdge texture | |
| 7 | Gate kerb band | new **GraniteHewn** set (hewn facets +-5 mm, 3-10 mm pits over 14 % of the face, pick marks, glossier crowns); band 5 -> **10 cm** proud (the grey-box gate-leaf sill is +0.0997), 20 mm rounded arris, 15 mm cut corners; block lengths 1.5 / 2 / 1 / 1.5 / 1 m between the two sloped ends; 10 mm joints over a dark joint fill (`SM_DKG_KerbMortar_7x0p5`, top +0.06); moss tufts in the joints | from the gate camera the band's top reads; its front face is barely in view |
| 8 | Edging too orange | bleached timber #BCAE96 weathering to #B1AA9E (mean 183/172/153, close to the sand's value); irregular top 6-10 mm | |
| 9 | Transitions | `SM_DKG_Tuft_Grass` (14 blades, 4.5-11 cm), `SM_DKG_Tuft_Moss` (10 blades, 1.5-3.5 cm), `SM_DKG_Pebbles_Stray` (9 pebbles, 1-2.4 cm): vertex-coloured (`M_DKG_Dressing`), no collision (spec 5.3 dressing). 40 tufts (path edges, slab joints, kerb joints, gate strip, tree-bed rims) and 14 pebble scatters (slab edges near the gate, the sand's south strip) | the gravel-into-sand blend mask and the wall-foot moss stay in kit 11 (decals) |
| 10 | Soil beds | the kerbed rectangular trays are replaced by 8 **mounded islands** (`SM_DKG_Bed_<name>_W/_E`): a concave dome (tree 8 cm, others 5 cm) inside a wobbly superellipse outline, and a 'Blend' vertex colour (soil 1 inside 0.78 of the radius, feathered with noise to 0 by 1.10) driving `M_DKG_BedBlend` (gravel and soil, both world-aligned, height-blended by the gravel's luminance); pure gravel at every non-wall rect edge, so the join with the panels is invisible. Soil #4E3E30 -> **#735B44** (mid brown). The Kerb25 bed kerbs are no longer placed (kept in the kit, like Kerb25_End / Kerb50_Corner) | soil area (blend > 0.5): tree beds 9.5 / 9.3 m2, wall-foot 5.9 / 5.6 and 8.9 / 8.5 m2, gate beds 2.5 / 2.4 m2 |
| 11 | Sunset grading | roughness drops 0.10 (slabs) / 0.14 (kerbs) on the worn crowns (by the Wear colour); sky fill 0.8 -> 0.6 for deeper contact shadow | frame luma p10/p50/p90 **36.7 / 145.5 / 177.0** (ref 34.4 / 117.1 / 171.1; r0 43 / 138): p10 now matches; p50 stays high because the grey-box walls and sky are pale planes where the reference has dark buildings and trees |

**Counts:** 68 pieces, **374 instances, 20,636 triangles assembled** (r0 4,448): the beds are 12,704 of them (0.125 m
grids; Tree 2,592 each). Gravel 189 panels (surround 521.25 m2), coarse strip 16 panels (50 m2), bed rects 99.25 m2,
dressing 54 instances. **Textures:** 2048 px / 4 m (5.12 px/cm) for every set; seam scores (rows / cols) BC and N
0.79-1.13 on every wrapping set; ORM per channel 0.87-1.06 (plus the low-by-construction rows noted above).

**Provenance:** our own procedural work, EXCEPT T_DKG_Gravel_* (Poly Haven gravel_floor_02, CC0 1.0, graded and
repacked) and the fines bed inside T_DKG_GravelCoarse_* (the same CC0 scan; the pebbles on top are ours): list both
as CC0 / CC0-derived on Fab. No text, crests or marks anywhere (STYLE_GUIDE 10).

**Unreal notes (in layout_ground.json `materials`):** M_DKG_BedBlend lerps the gravel and soil sets by VertexColor.R,
height-blended with the gravel BC luminance (smoothstep 0.4-0.6 of R + 0.35 (0.5 - lum)), world-aligned
(WorldPosition.xy / 400 cm); M_DKG_Dressing is BaseColor = VertexColor, two-sided; granite and hewn granite take the
hue lerp on frac(PerInstanceRandom x 17.31) and the crown gloss from the Wear colour.

**Renders (`renders/f1/`):** `TEXTURE_SHEET.png` (eight sets: 3 x 3 flat tiles, red ticks at the tile seams, and a 1.7 m
eye close-up), `C_Establish.png`, `C_Overview.png`, `C_PlayerEye.png`, `SBS_Establish.png`, `SBS_GroundCrop.png`,
`compare_stats.json`. 128 samples, OIDN, AgX Medium High Contrast. The `gravel_far_band` stats region falls in the
hall's shadow in ours (38/34/37), so it is not a like-for-like gravel comparison; the lit surround gravel was sampled at
(1340-1440, 560-640) instead: 166/137/115.

**Still open after f1:**
- The far sand is 191 against the reference's 203 (haze and bounce in the reference); the slabs stay warmer than the
  reference's mauve grey (B 108 vs 127) and the gate strip slightly warmer (B 75 vs 91).
- From the 13-30 m gate camera the rake lines still read as clean stripes more than grainy crests; the grain and the
  crest highlight show from the player's eye (C_PlayerEye).
- The gate band's front face hardly shows from C_Establish (our eye is 9.7 m up; the reference's eye stands in the
  gate); the reference's band runs the full frame, ours is the 8 m gatehouse width.
- The bed dome hulls are sampled every 0.25 m: up to 1.15 cm sink on the Gate beds' steepest rim.
- The beds are 12.7k of the ground's 20.6k triangles; a coarser grid in the pure-gravel margin would halve that.
- Gravel-into-sand blend masks and wall-foot moss: kit 11. Rocks and plants for the beds: later kits / packs.

## ROUND 3 (2026-09-28): look pass for Unreal, ground + shared material library

Brief: the round-2 final judge (6.5/10, whole courtyard in Unreal) found the ground and the materials gave the copy
away. Blender only (no Unreal run in this stage); lock `DojoGround` taken for the stage. Outputs:
`WorkFiles/dojo/build/round3/ground_materials/` (start backup of every script, texture, layout and the blend in
`r3start_backup/`). Library side: `WorkFiles/dojo/build/materials/BUILD_NOTES.md` (same date).

Commands (in order):
```
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/materials/dojo_tex_gen.py --only TimberDark,TimberDarkEnd,TimberAged,TimberAgedEnd,Granite,PlasterCream,PlasterEarth,RoofTile,Lacquer
blender -b --factory-startup --python Scripts/dojo/ground/make_ground_textures.py -- --only Sand,Gravel
blender -b --factory-startup --python Scripts/dojo/ground/build_ground_kit.py
blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/measure_collision.py
blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/render_ground.py -- --cams CAM_EstablishingRef2,CAM_PlayerEyeSand --samples 64 --rig ue|studio --out <abs>/round3/ground_materials/renders/<rig>
blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/render_ground.py -- --cams C_Establish --samples 64 --rig sunset --out <abs>/round3/ground_materials/renders/sunset
py -3 Scripts/dojo/ground/r3/measure_rake_r3.py [--ours]
py -3 Scripts/dojo/ground/r3/sbs_r3.py
py -3 Scripts/dojo/materials/r3/compare_tex_r3.py
```

### 1. Raked sand: re-measured, rebuilt at real size with both scales
- `r3/measure_rake_r3.py` maps image rows to ground Y through each camera, resamples to even Y and takes the
  spectrum (`rake_measure.json`).
  - Reference 2, under the round-1 fit to the spec's 28 m floor: dominant period 0.17-0.20 m at every depth, a
    0.094 m harmonic (power 0.12-0.22: a second, finer line in each band) and a broad 3-14 cm bead spectrum along the
    crests. Its near rows sample 44 px/m (Nyquist 4.6 cm), so 3-5 cm grooves cannot be resolved in it at all.
  - The round-2 UE capture (CAM_EstablishingRef2): exactly 0.178 m, a pure sinusoid (every other peak <= 0.003 of
    the main). So the r2 spacing equalled the fitted reference; what differed is regularity and camera distance: the
    UE judge camera (eye 3.1 m, near sand ~5 m away) sees the sand 2.3x larger per metre than the reference's eye
    (9.7 m up, 13-30 m away), hence the judge's "3-4x too wide".
  - The same spec-scale fit makes the reference's other ground details oversized against their real sizes (path
    2.3 m of ~1.1 m slabs, near gravel ~5 cm; real: 0.4-0.6 m pavers, 2-3 cm gravel, 6-10 cm rake tines): the image's
    ground detail is about 0.5x the fitted scale.
- **Built:** 42 rake lines per 4 m tile (mean 9.52 cm = 0.5 x the fitted 0.19 m), each line jittered +-16 % (spacing
  7.2-11.1 cm), crest positions symmetric about v = 0 so both edge strips (U = +v and U = -v) continue the field's lines
  in phase; per-line depth +-20 % (symmetric too); profile `(1-d)^1.5` plus a fine ridge at 26 % of the crest in each
  trough (fine grooves every ~4.8 cm riding on the 9.5 cm bands); groove depth 1.8 -> 1.3 cm; wobble 5 -> 4 mm
  (peak 1.25 cm); beaded crests (crumbs ~4.5 cm along, 2 cm across) plus the r2 4-20 cm slumps; baked stripe tone
  +-6 -> +-4 %, trough occlusion 9 -> 6 %.
- Measured on our render of the UE framing (studio rig): main 0.0951 m, fine 0.0476 m (power 0.22), side peaks
  (irregular), against r2's single 0.178 m line.
- **Albedo:** tile mean graded to `#CAB089` (202, 176, 137), a warm beige-tan (r2 (209, 190, 158)). UE's cool sky
  fill lifts B about 16 % against R relative to the albedo (r2 sand albedo R/B 1.32 -> UE 1.24), so this lands near
  the reference's lit sand (179-203, 149-165, 131-138) in UE.
- **Moire:** irregular spacing (no single frequency) plus the weaker baked stripe; the Unreal recipe for a
  view-distance fade of the rake normal is in `layout_ground.json` `materials.M_DKG_Sand*.normal_fade` (start 1200 cm,
  end 3500 cm, far strength 0.35). **It needs adding to `M_DJ_Ground_Master` in `dj_sc_materials.py` (not this
  track's file).**

### 2. Centre path: warm-grey pavers in running bond
- `SM_DKG_PaverCourse_2x0p42_A..H` replace the eight `SM_DKG_PathSlab_*` (their FBX moved to
  `Exports/DojoKit/Ground/_superseded_r2/`; delete them from DojoLab after the re-import).
  - Each course is 2.0 x 0.42 m, 4-5 granite pavers, 10 mm joints over the dark joint fill (`SM_DKG_PathBed_2x3` at
    +0.004), 10 mm rounded arris, 10 mm cut plan corners, top +0.020, one flat UCX at +0.020 (bottom -0.10).
  - Paver lengths: interior 0.40-0.60 m; the edge pavers may be cut to 0.20-0.35 m (real running bond cuts at the
    path edges). The eight patterns come from a random search over all 515 compositions of 2.0 m for the most
    running-bond neighbours: a strict 4 x (0.40-0.60) set can only alternate two patterns (the first r3 build
    repeated one pattern every other course).
  - 50 courses over Y 0.5-21.5; every joint >= 0.12 m from the joints of the course before, and no pattern twice
    within three courses; half the courses turned 180 deg. The path stays X 21-23, 2.0 m wide, flat collision.
- **Tone:** each paver adds 0-0.40 to the `Wear` R (grime) channel, i.e. 0-16 % darker through the library wear
  maths, in Blender and Unreal alike. G (edge wear) is cleared on the pavers: in test render t1 the bleached arrises
  drew the joints as pale lines and flashed as white dashes under the low sun. Per-actor tone / hue is off (one
  course = one actor would stripe the path): `M_DKG_Granite` `instance_tint` 0, hue neutral.
- **Colour:** `M_DKG_Granite` tint (1.66, 1.92, 2.60) -> **(1.45, 1.38, 1.25)** on the new library granite (median
  (115, 111, 106)): albedo median about (137, 129, 118). The r2 tint was the lilac path (UE (166, 162, 185)). Studio
  render of the path: (154, 145, 131).
- Collision (`collision_check.json`): pavers float <= 10 mm only over the rounded arris and joints (0.17-0.20 % of
  the area), sink 0; every other piece as in f1.

### 3. Gravel
- Surround gravel: the CC0 scan graded to **#9F8F7B** (was #ABA59E) at 55 % chroma, with the pebble-to-pebble contrast
  x 0.62 about a 12 px local mean. Tile mean (157, 141, 122) (r2 (168, 162, 155)); speckle (high-pass luminance
  std / mean) 0.167 -> 0.099. It sits a step under the sand.
- Coarse gate strip: kept (same pebbles), 6 % more R and 10 % less B so it does not read lilac beside the warm
  surround: mean (112, 103, 95).

### 4. Dressing UCX
- `SM_DKG_Tuft_Grass`, `SM_DKG_Tuft_Moss` and `SM_DKG_Pebbles_Stray` each carry one trivial box UCX (2 x 2 x 0.4 cm /
  0.2 cm) at the root. `piece_meta.collision` stays False, so compose keeps them in class `nocollision` (NoCollision
  in Unreal). QA now requires a UCX on every piece.

### Checks
- QA: 68 pieces, **0 hard fails** (the tiling pieces waive `uv0_tile_range` / `uv_no_overlap` as before). **68 FBX
  exported** through `pipeline.export_fbx`, no warnings (the three dressing pieces no longer warn "no UCX").
- 378 instances, 33,166 triangles assembled (pavers 280-350 tris per course); coverage 0 holes, 0 overlaps.
- Texture seams (`textures_report.json`): SandRaked BC 0.995 / 0.986, N 1.03 / 1.03; Gravel BC 0.95 / 0.97, ORM AO
  1.00 / 1.03.
- Walk / climb numbers: unchanged by construction (every walk surface and hull height is the r2 one; the path hull is
  +0.020, as the slabs').

### Renders (`round3/ground_materials/`)
| File | What |
|---|---|
| `SBS_R3_UE_framing.png` | the round-2 UE capture / ours r3 under a UE-like rig (5500 K sun 13 deg, lilac-grey sky) / ours r3 under a neutral studio rig, for CAM_EstablishingRef2 and CAM_PlayerEyeSand, full frame plus near-ground crop |
| `SBS_R3_ref2_crops.png` | dojo1_reference2 crops beside the same boxes of C_Establish (the reference-fitted camera, the kit's sunset rig) |
| `renders/{ue,studio,sunset}/` | the frames; `renders/sunset/SBS_*.png` and `compare_stats.json` (compare_ground.py) |
| `TEXTURES_R2_vs_R3.png`, `texture_metrics_r2_vs_r3.json` | every changed BC map, r2 vs r3, tile plus 0.5 m corner, medians and speckle metrics |
| `rake_measure.json`, `sbs_r3_stats.json`, `unreal_recipe_r3.json` | measurements and the Unreal hand-off (re-imports, instance values, capture targets) |

The UE-like rig renders are darker than UE overall (the grey-box canopies and buildings shade most of the ground at
13 deg): read them for pattern and hue, and the studio renders for albedo.

### Open / flagged
- **Scale conflict (the main risk).** At the reference's own fitted camera (`SBS_R3_ref2_crops.png`) the r3 ground is
  FINER than reference 2: its two columns of ~1 m slabs and its 0.18 m crumbly rake bands are what the spec-scale fit
  measures. r3 follows the brief and the real-world sizes (pavers 0.4-0.6 m, rake ~9.5 cm + ~4.8 cm), which read
  right from the game cameras. If the next judge on the Unreal captures finds the sand too fine or the path too busy,
  the one-number fallbacks are `RAKE_LINES` 42 -> 30 (13 cm) and a 3-paver course set.
- The beaded crest texture shows at the player eye but not from the 9.7 m reference-fit eye, where the reference's
  ridges read as distinct crumbly ropes.
- The sand normal fade needs the Unreal material change above; until then the irregular lines are the only moire
  guard.
- The path starts under the kit-1 gate paving (Y 0.5-2.0): compose drops the courses it covers >= 95 %, as before.
