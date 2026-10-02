# Dojo rocks: build notes

## 2026-10-01: Pilot (RiverRound, RiverLong, CliffChunk): technically complete, does NOT match the sheet (stop)

**Scope:** two river boulders from the sheet's row 2 (boulder 2 is the rounded loaf, boulder 3 is the long low one) and
cliff chunk 1 from row 4. Lock `DojoRocks` (claude). No Unreal in this run. Nothing committed.

**Verdict.** Do not build the full set on this recipe yet. The pipeline works end to end: sheet trace, SDF source,
Nanite mid, unique UVs, bakes, masks, UCX, qa_check, FBX, catalog and renders. The silhouettes match (IoU 0.84-0.94).
The **look** does not match, and by my reading the pilot is well under the owner's ~7/10 gate:
- local contrast is at about 40 % of the sheet's;
- the grain reads as camouflage blotches, not salt-and-pepper crystals;
- the river forms are rounded boxes, where the sheet draws faceted domes;
- the cliff blocks are too flat-faced;
- the lichen has no rosette structure.

Details are under "What fails" below.

### Method (study 4.9, and where it deviates)
- **Trace:** `Scripts/stone/rock_ref.py` (new) finds silhouettes in seed mode on the sheet's flat grey background.
  It rejects shadows by chroma and texture, and clamps the bottom 12 % of each mask (the contact shadow made a 15 cm
  plinth). Overlays are in `pilot/refcrops/ovl_*`. Figure scale: row 2 is 143 px = 1.8 m (79.4 px/m); row 4 is
  134 px (74.4 px/m).
- **Sizes (m, L x D x H above grade):**
  - RiverRound: 2.08 x 1.27 x 1.36.
  - RiverLong: 3.36 x 1.28 x 1.18.
  - Cliff: 2.79 x 1.74 x 3.08.

  Depth is the one dimension the sheet draws inconsistently:
  - RiverRound: the end views say 1.33-1.36 m and the oblique plan says 0.90 m, so 1.27 m was used (end views lead).
  - RiverLong: 1.18 m against 1.38 m (17 % apart), so the geometric mean, 1.28 m, was used.
- **Form:** a visual hull (front, side and plan outlines, Gaussian-smoothed σ 1.5 px, extruded and intersected as
  SDFs), built in two SDF stages.
  - Stage 1 (1 cm voxels):
    - River boulders: shallow oblique joint facets, then an opening at r 0.165-0.17 m.
    - Cliff: columnar joint sets. There are 4 vertical x-joints and 1 y-joint. Each column draws its own 0-2 bed
      joints. Each block takes the hull eroded by its own recess, which never decreases up a column. The blocks are
      unioned, then opened at r 0.028.
  - Stage 2 (5-6 mm voxels): flakes (spall-scar polytopes with leaning walls), cracks (planned from the sheet, plus,
    on the cliff, cracks traced where the joint planes meet the surface), facet cuts on exposed block faces, chips on
    column tops, a lip opening, then Grid to Mesh at threshold 0.
  - Then masked meso noise, and an above-grade rescale to the measured size (+0.0-4 %).
  - **Deviation:** no lobe hulls. The traced visual hull is the 2D authority (CLAUDE.md tracing rule).
- **Ship:**
  - The mid is a voxel remesh of the dense source: 147k / 167k / 262k rock tris, with verts/tri 0.50-0.52.
  - It also carries a moss cushion shell (slot 1) and, on the cliff, 34 opaque grass tufts (slot 2, 5.6k tris).
  - Unique UV0 is box-direction charts, ABF, packed. UV1 is the full-tile copy.
  - Maps: N (DirectX), ORM (baked AO, roughness) and M (R moss, G lichen, B wet, A signed tone: tan > 0.5 > grime).
  - Shared tiling `T_DKR_GraniteDetail_*` and `T_DKR_MossDetail_BC` (our own procedural).
- **Collision:**
  - River boulders: 3 UCX each, tops flattened at a 0.83 x 0.61 m landing (RiverRound z 1.31, crown 5 cm above the
    flat) or at z 1.16 (RiverLong). Both are marked climbable (mantle), with a traversal box in the catalog.
  - Cliff: 5 UCX by column, not climbable (3.08 m is over the 2.75 m mantle).
- **QA:** qa_check reports 0 hard fails on all three, with require_uv1 and require_ucx and texel 5.12 ±25 %. Measured
  texel: 4.87, 4.47 (2K) and 5.12 (4K). Exported through `Scripts/pipeline`. No waivers.

### Measured (pilot/measure.json; the same code runs on the sheet and on ours, our crop resampled to the sheet's px)
| | RiverRound | RiverLong | CliffChunk | gate |
|---|---|---|---|---|
| IoU front / side / top-or-oblique | 0.93 / 0.94 / 0.73 | 0.92 / 0.93 / 0.91 | 0.92 / 0.84 / 0.87 | SG15 ≥ 0.80 (RR's plan view is the sheet's inconsistent oblique) |
| luma p50 ours / sheet | 0.32 / 0.38 | 0.32 / 0.32 | 0.38 / 0.33 | |
| local std (16 px at sheet scale) ours / sheet | 0.060 / 0.145 | 0.056 / 0.129 | 0.059 / 0.142 | SG10 ±25 %: **fail** |
| wet band p50 (bottom 30 %) ours / sheet | 0.23 / 0.20 | 0.24 / 0.19 | n/a | |
| hue / sat ours | 34° / 0.11 | 38° / 0.13 | 32° / 0.13 | landscape family 24-29° / 0.14-0.19: sat low, hue 5-9° warm |
| moss share (hue test) ours / sheet | 1.4 % / 2.7 % | 4.1 % / 8.9 % | 2.1 % / 5.0 % | SG12 ±30 %: low |
| plane fraction (k6, 15°) | 0.46 | 0.47 | 0.54 | SG14 ≥ 0.60: fail |
| arris radius p50 / short axis | 0.12 m / 9 % | 0.14 m / 11 % | 0.09 m | river ≥ 15 % (the sheet's silhouette corners measure 10-12 %) |
| sharp-crease share (>30°) | 0.6 % | 0.4 % | 2.2 % | |

Close-ups, ours against the sheet:
- **Local std:** our close-ups are 0.02-0.05 against the sheet's 0.13-0.18.
- **Grain:** the dark share is 0 % below 0.25 luma, against the sheet's 11 %.

### What fails, and the next method (not patching values)
1. **Albedo contrast and grain.** FlattenToMean 0.45 plus the 1 m tile made camouflage blotches. The sheet's grain is
   crisp black/white/grey crystals with high contrast, and its rocks carry dark/light weathering at 2-10 cm.
   - Next: drop Flatten.
   - Next: ship a darker, higher-contrast grain tile, matched to the grain close-up by its own numbers (dark share
     11 %, p95 0.83).
   - Next: put the 2-10 cm weathering into the unique mask at higher contrast.
   - Gate it on the close-ups before re-baking the rocks.
2. **River form.** The visual hull makes rounded boxes with flat crease faces. The sheet's boulders are faceted domes
   whose sides taper in toward the top.
   - Next: a corestone ellipsoid cut by joint planes (lobes, study 4.9.2 step 1), with the visual hull only as a
     clamp, not the shape.
3. **Cliff form.** Columns and beds now read right; the block faces are still too planar and in one plane.
   - Next: give each block its own prism with an outward bulge.
   - Next: steeper facets on most exposed faces.
   - Next: rubble at the foot.
4. **Lichen.** The sheet's rosettes are lobed, 3-6 cm.
   - Next: a lobed rosette mask (polar noise), not discs.
5. **Riverbank.** The stand-in bed is a flat slab with a channel, so the rocks read as objects on a table. That is the
   stand-in, not the rocks. A real bank needs the landscape round's ground.

**Judge deltas:** no judges were run. The measurements already fail SG10 decisively, so per the study (6.6, and
"stop early") no judge round was spent.

### Files
- **Code:**
  - `Scripts/stone/`: rock_ref, stone_sdf, rock_forms, stone_bake, stone_weather, granite_tile (all new).
  - `Scripts/dojo/rocks/`: rocks_ref, rocks_plans, rocks_form, build_rocks, rocks_material, rocks_render(_final),
    rocks_measure.
- **Run order:**
  1. `py -3 rocks_ref.py`
  2. `blender rocks_form.py`
  3. `blender build_rocks.py`
  4. `blender rocks_render.py -- sheet|sil|close|river --src blend`
  5. `py -3 rocks_measure.py --sbs`
- **Assets:**
  - `Assets/Dojo/DojoRocks.blend`
  - `Exports/DojoKit/Rocks/SM_DKR_Rock_{BoulderRiver01,BoulderRiver02,Cliff01}.fbx` + `Textures/T_DKR_*`
  - `rocks_catalog.json` (sizes, tris, collision, traversal, masks, the Unreal MI plan)
  - `qa_report.json`, `export_report.json`
- **Renders:** `pilot/sheet`, `pilot/sil`, `pilot/close`, `pilot/river`, `pilot/sbs` (sheet | ours).
- **Times:**
  - Form: 25-150 s per rock.
  - Build (3 rocks, bakes on GPU): about 9 min.
  - Sheet renders: about 1 min per rock.
- **Not done:**
  - Unreal (DojoLab busy).
  - Fab LOD meshes.
  - The M_ST_RockUnique master.
  - Final renders to `Renders/`.

## 2026-10-01: Pilot 2 (method change): forms fixed, look still fails (stop and show)

**Scope:** the same three rocks (RiverRound and RiverLong from row 2, CliffChunk from row 4), rebuilt with the
owner-approved method change. Lock `DojoRocks` re-claimed (claude). No Unreal in this run. Nothing committed. Pilot 1
is kept as a backup:
- `pilot/` (renders, measure.json, sbs);
- `pilot/DojoRocks_pilot1.blend`;
- `pilot/backup_exports/` (pilot 1 FBX and maps, including the retired `T_DKR_GraniteDetail_*`);
- `pilot/rocks_catalog.json`, `qa_report.json`, `export_report.json`.

**Verdict.** The forms are a real step up from pilot 1:
- RiverRound is a domed corestone that rolls under into the ground, with soft facets (no loaf).
- RiverLong is one long low mass with the join crack.
- The cliff is a fractured mass with blocks in many directions, protruding and receding, with tilted faces, deep
  joints, chipped arrises and rubble at the foot (no masonry grid).

The surface still does not match the sheet:
- Local contrast at the sheet's pixel size is 54-77 % of the sheet's.
- The weathering reads as camouflage blotches.
- On the rock the grain close-up loses the crisp crystals that the test patch had.
- Moss is a painted shell rather than tufts.
- The wet zone is weak in close-up.

My read is about 4/10, so I stopped here rather than iterate further without the owner.

### What changed (method)
- **Surface:** `Scripts/stone/scan_surface.py` (new) builds the layers from the Poly Haven CC0 scans
  (`Assets/Dojo/SourceTextures/PolyHaven/*/SOURCE.md`).
  - **Grain** (granite_tile_03). Only tile interiors are used, 12 px clear of every grout joint. They are quilted along
    warped Voronoi boundaries into a periodic tile, then flattened at low frequency. The luma is quantile-mapped onto
    the sheet's grain panel and the chroma is transferred. The tile is upsampled 2x with crisp mineral classes.
    Result: shipped `T_DKR_GraniteGrain_BC/_N`, 2048 px = 0.75 m.
  - **Macro albedo and relief:** rock_surface for the river rocks, tiger_rock for the cliff. Both are regraded to grey
    (only 10 % of the scan's chroma kept). The scan height goes onto the dense mesh as real geometry, triplanar in
    object space, and is baked into the unique normal.
  - **Moss:** mossy_rock, regraded.
- **Composite bake:** `rocks_material2.py`. The macro scan is combined with these layers:
  - tan staining used only as staining;
  - pale crust and dark spots with crisp edges;
  - lobed lichen rosettes, drawn per pixel from per-vertex seed offsets (`stone_weather2.lichen_fields`; a 3-D
    Voronoi sliced by the surface gave few, truncated rosettes);
  - a wet zone and an olive tint;
  - moss.

  It is baked from the dense mesh into unique maps: BC, N, ORM (AO, plus baked roughness so the wet areas are glossy)
  and M (moss, lichen, wet). The shipped material multiplies BC by the tiling grain, with GrainAmount 0.45 on the
  river rocks and 0.8 on the cliff.
- **Wet:** `stone_weather2.masks`. A water level warped by two noise octaves (±20 % of H) that rises in hollows and
  joints and on down-facing faces. It has a wide soft fade, splash patches above it, olive in the lowest part and
  roughness 0.09. There is no straight line.
- **River forms:** `rock_corestone.py` with `rocks_form2.py`. In order:
  1. A lumpy superellipsoid with its equator at about 0.23 H above grade (the ellipse that fits the sheet's width
     rows within 0.03), the crown off-centre and the flank tucked under.
  2. Six old joint planes and 16-24 soft facets.
  3. A clamp by the traced hull grown by 3.5 cm.
  4. An opening at r 0.18 m (14 % of the short axis).
  5. 40-56 secondary facets re-rounded at 0.04 m, then cracks and lumps.
- **Cliff form:** `rock_fracture.py`. In order:
  1. A Voronoi partition on a sheared, anisotropic lattice (yaw 8°, lean 5°, columns 0.56 m, 2-4 levels, zstretch
     1.8), with every shared face tilted ±8°.
  2. Each block takes the hull eroded by its own recess, from -0.10 to +0.30 m (lower blocks prouder), and 2-3
     tilted fracture facets (15-38°, 5-20 cm deep).
  3. Each block has its own core eroded 14-26 cm deeper, so the joints are deep slots, never holes through the rock.
  4. Rubble at the foot, an opening at 1.5 cm, 120 conchoidal arris chips and 40 spall flakes.

  Iterations, each shown in the clay renders:
  - Round 1: shattered slivers and see-through gaps.
  - Round 2: crazy paving on a flat wall, and square chip pockets.
  - Round 3: lozenge columns. Kept.
- **UV:** the fractured cliff's 2000 box-direction charts never cleared the SAT overlap test. It now uses Smart UV
  Project at 45°, which gives 0 overlaps and fill 0.38.

### Surface gate (test patch, before the re-bake)
`pilot2/surface/`, with ours resampled to the sheet panel's pixels.

| Check | Ours | Sheet | Result |
|---|---|---|---|
| Grain local std / p50 | 0.333 | 0.318 | pass |
| Grain dark share (below 0.437 x p50) | 0.093 | 0.118 | pass, -21 % |
| Grain raw local std | 0.187 | 0.182 | |
| Lichen patch local std / p50 | 0.28 | 0.38 | |

**But on the rock, the grain close-up fails:**

| Check | Ours | Sheet |
|---|---|---|
| Local std / p50 | 0.24 | 0.32 |
| Dark share | 0.05 | 0.118 |

The crust, the macro blur and GrainAmount 0.8 wash it out, and the spot picked was a shaded edge.

### Measured (pilot2/measure.json; the same code on the sheet and on ours, ours resampled to the sheet's pixels)
| | RiverRound | RiverLong | CliffChunk | pilot 1 |
|---|---|---|---|---|
| IoU front / side | 0.92 / 0.90 | 0.91 / 0.93 | 0.83 / 0.79 | 0.92-0.93 / 0.84-0.94 |
| IoU sheet lower (3/4) view, best oblique | 0.60 (a 0, e 65; the sheet's view is inconsistent) | 0.95 (e 25) | 0.73 (a +10, e 65) | 0.73 / 0.91 / 0.87 |
| IoU plan top / RR end view 2 | 0.69 / 0.88 | 0.91 | 0.78 | |
| corner r / short, front (ours / sheet) | 0.21 / 0.10 | 0.28 / 0.26 | 0.10 / 0.11 | |
| arris r p50 / short axis (dense) | 8 % | 9 % | 5 % | 9-11 % |
| plane fraction k6 15° (dense, noisy) | 0.18 | 0.24 | 0.34 (SG14 ≥ 0.6: fail) | 0.46-0.54 |
| local std, whole rock (ours / sheet) | 0.078 / 0.145 | 0.091 / 0.129 | 0.101 / 0.142 | 0.056-0.060 |
| luma p50 top / bottom 30 % (ours / sheet) | 0.47 / 0.21 vs 0.54 / 0.20 | 0.40 / 0.20 vs 0.52 / 0.19 | 0.44 / 0.35 vs 0.41 / 0.31 | |
| hue / sat, all (ours / sheet) | 40° / 0.13 vs 34° / 0.17 | 44° / 0.11 vs 36° / 0.15 | 43° / 0.10 vs 35° / 0.21 | |
| moss share (ours / sheet) | 2.4 % / 2.7 % | 4.5 % / 8.9 % | 2.1 % / 5.0 % | 1.4 / 4.1 / 2.1 % |
| wet mask share (dense) | 58 % | 54 % | damp foot | hard band |

The RiverRound plan IoU is limited by the sheet: its lower oblique view does not agree with its own end views.

**Close-ups at the sheet panel's pixels** (local std / p50, ours vs sheet):

| Close-up | Ours | Sheet | Notes |
|---|---|---|---|
| fracture | 0.21 | 0.39 | |
| moss | 0.15 | 0.40 | moss hue share matches at 0.19 vs 0.19 |
| lichen | 0.31 | 0.38 | the dark share matches |
| wet | 0.15 | 0.39 | |
| riverbank | 0.17 | 0.38 | |

**QA and export:**
- qa_check reports 0 hard fails on all three, with require_uv1, require_ucx and texel 5.12 ±25 %. No waivers.
- Texel: 5.00 and 4.43 px/cm (2K), 4.44 px/cm (4K).
- Tris: 147k, 182k and 250k (the cliff's 236k rock includes rubble and 40 tufts); verts/tri 0.51-0.53.
- UCX: 3, 3 and 5.
- Exported through `Scripts/pipeline` as `SM_DKR_Rock_{BoulderRiver01,BoulderRiver02,Cliff01}.fbx` with `T_DKR_*`.
- `rocks_catalog.json` carries the CC0 provenance per texture.

### What fails, and the next method (for the owner to approve)
1. **The weathering pattern reads as camouflage.** The noise-threshold crust and spots are too large, too even and
   too pale. The sheet's surface is high-contrast at 2-8 cm: crisp white crust with a dark matrix, plus specular
   sparkle.
   - Next: drive the pattern from the scans' own albedo (the mossy_rock lichen and tiger_rock patterns, regraded to
     a bimodal light/dark), not from procedural noise.
   - Next: put the lighting rig's contrast to the sheet as a measured target.
2. **The grain is lost on the rock.** Gate the on-rock grain close-up, not only the test patch. Fresh fracture faces
   need GrainAmount 1 and no crust: carry a "fresh" mask on the cliff's facet and chip surfaces.
3. **The cliff has lozenge-shaped blocks and few flat ledges.** The sheet has flat bed joints with moss and grass on
   the ledges, and smaller multi-facet faces per block.
   - Next: a joint-set fracture (2-3 plane families, each jittered) instead of Voronoi.
   - Next: ledge tops levelled so moss and tufts can sit on them.
4. **Moss is a flat shell.** The sheet's moss is cushions of strands. Use the grass-tuft generator for moss strands on
   the cushions.
5. **The wet close-up is weak.** It needs a wet-film normal and stronger darkening at the waterline. The stand-in
   water is flat teal.

**Judge deltas:** no judge was run; the measures fail decisively (study 6.6). I checked pilot 1's four deltas against
the sheet and all four hold. Rejected deltas: none.

### Files
- **Code:**
  - `Scripts/stone/`: scan_surface, stone_weather2, rock_corestone, rock_fracture (new).
  - `Scripts/dojo/rocks/`: rocks_plans2, rocks_form2, build_rocks2, rocks_material2, rocks_surface_test,
    rocks_render2(_final), rocks_measure2(_all) (new). Pilot 1 scripts are unchanged.
- **Run order:**
  1. `py -3 scan_surface.py --ship Exports/DojoKit/Rocks/Textures --work WorkFiles/dojo/build/rocks/work2/tex`
  2. `blender rocks_surface_test.py`, then `py -3 rocks_measure2.py surface`
  3. `blender rocks_form2.py`
  4. `blender build_rocks2.py`
  5. `blender rocks_render2.py -- clay|sil|sheet|close|river [--src blend]`
  6. `py -3 rocks_measure2.py all --sbs`
- **Times:**
  - Forms: 35-95 s for the river rocks; 6-10 min for the cliff (stage 1).
  - Build of all three: about 15 min.
  - Renders: about 6 min.
- **Renders:** `pilot2/`:
  - `sheet/<r>_{main,mainonly,top,side,q34,clay_q34,row}`
  - `form/clay_*`
  - `sil/`
  - `close/close_*`
  - `river/riverbank_sunset(_close)`
  - `surface/`
  - `sbs/` (pilot 1's names, plus `_q34`, `_clay_q34` and `_row`)
- **Not done:**
  - Unreal (DojoLab is busy).
  - Fab LODs.
  - `M_ST_RockUnique`.

## 2026-10-01: pilot 2 fix 1 (judge round on pilot 2: 4/10)

Backup of pilot 2 first: `WorkFiles/dojo/build/rocks/pilot2/backup_p2/` (exports, every Scripts/stone and
Scripts/dojo/rocks .py, DojoRocks_pilot2.blend, work2 dense npz/json, catalog, QA and export reports). Pilot 1's
backup (`pilot/`) and pilot 2's renders (`pilot2/`) are untouched. Renders of this round: `pilot2_f1/`.
No Unreal, no downloads, nothing committed. Lock DojoRocks re-claimed.

### Judge-steer check (I looked at the sheet for each delta)
- Accepted: 1 (faceted water-worn blocks), 2 (lobes split by joints with steps and rounded lips; no slots),
  3 (horizontal joint set, cuboid blocks, crisp arrises, benches with tufts), 4 (crisp grain at the right scale,
  neutral hue), 5 (macro variation from cavity and pits, smaller and crisper mottles), 6 (rosette lichen with
  structure, sparse and up-facing on the cliff), 7 (moss with volume, crest band on RiverLong), 8 (wet band at the
  base, no mid-rock splash patches, waterline algae), 9 (grounding in the riverbank test only: the sheet's studio
  rows stand on a flat floor).
- Partly accepted:
  - Delta 2 says "the joint runs diagonally". On the sheet's RiverLong the two joints are near-vertical and curving,
    so I modelled them that way.
  - Delta 4 says "about 15 % black biotite". The sheet's grain panel measures 11.8 % dark, so I used that.
- **Rejected delta: 10** (RiverRound "0.9x the figure; the sheet's is 0.55-0.6x"). On the sheet, row 2's rock is
  108 px tall against a 143 px figure: 0.755x, or 1.36 m (ref_measure.json). Our RiverRound is 1.359 m, so I kept
  its size.

### Method changes
- **River boulders: faceted water-worn block.** Code: `rock_corestone.broad_facet_cuts` and `wavy_halfspace`,
  `rocks_form2.river_stage1_faceted`, plans in `rocks_plans2.py` ("pilot 2 fix 1"). Build order:
  1. The dome mass ∩ the traced hull (+1.2 cm).
  2. Minus 18-19 designed broad facets. Cap depths are 6-17 cm, so the planes are 40-90 cm across.
  3. One opening: r 0.13 m on RiverRound, 0.15 m on RiverLong.
  4. Joints split the mass into lobes along meandering surfaces. Each lobe is stepped down by its own amount
     (RiverLong 4.0 / 2.2 / 0 cm, RiverRound 2.0 / 0 cm) and opened on its own (lips 3-4.5 cm).
  5. A core keeps each joint a groove 4.5-8 cm deep.

  RiverRound's single diagonal joint dies out outside a zone: it runs over the front and fades. Pilot 2's slot
  cracks are removed, and the meso noise is cut to 1.0 / 0.6 / 0.3 cm.
- **Cliff: joint-set fracture.** Code: `rock_fracture.jointset_cells_cols`, `jointset_recess_cols` and
  `block_face_planes`; `rocks_form2.cliff_stage1_jointset`.
  - Joints:
    - Columns are bounded by long, near-vertical U joints (0.40-0.85 m apart, +-7 deg).
    - Each column has its own cross joints every 0.40-1.20 m, tilted up to 9 deg.
    - V joints are set per column and bed.
  - Each block is its shrunk cell (4 mm gap) intersected with:
    - the hull, eroded by the block's own recess (-0.14 to 0.55 m: column offsets, upper beds stepped back);
    - a face plane tilted 14-32 deg;
    - a top chamfer (50 % of blocks) and a vertical-arris chamfer (50 %);
    - 2-3 fracture facets;
    - a broken, tilted crown on the top blocks.
  - Per-block cores keep the joints 5-12 cm deep. A 2.0 cm opening keeps the arrises crisp.
  - 70 arris chips. The spall flakes are dropped because they cut square pockets.

  Rounds:
  1. One global bed grid: read as coursed masonry.
  2. Columns and stepped beds: still brick-like, with wide gaps.
  3. Tight joints and facets: flat faces.
  4. Tilted faces and deeper relief.
  5. As round 4 with more relief. Kept.
- **Surface.**
  - The grain tile now spans 0.45 m instead of 0.75 m; the pixels of T_DKR_GraniteGrain are unchanged.
  - Full-strength grain everywhere read as terrazzo. The grain weight now comes per pixel from a new M.A channel:
    1 on fresh fracture patches and worn arrises, 0.3 on the weathered surface. Fresh areas also lose 60 % of the
    weathering tint.
  - The macro scans are graded at the bake's own resolution (2.5 px pre-blur, then quantile targets from p5
    0.14-0.16 to p95 0.80), so the contrast survives the bake.
  - Crust and dark spots are now 3-6 cm across (scale 17-32 /m) instead of 25 cm blotches. The world-space grime
    blotches are cut to 55 %.
  - Ochre and rust come from the cavity and the fine pits (the unsmoothed curvature of the dense mesh).
  - Tint (1.0, 0.90, 0.80).
- **Lichen as a tiling detail.** `scan_surface.lichen_layer` is new and ours (no scan).
  - Maps: T_DKR_LichenDetail_BC (A = cover), _N and _HID (R height, G rosette id); 1024 px = 0.5 m.
  - The tile holds 103 foliose rosettes in clusters. Each has 4-7 overlapping lobes with scalloped margins,
    lighter raised rims, radial striation, and a darker centre with a spot.
  - The shipped material shows a rosette whole where its id < M.G x density + bias. The baked M.G is now the lichen
    zone; nothing is baked as stamps.
  - On the cliff the zone is up-facing only and about 60 % sparser.
- **Moss with volume.** `Scripts/stone/stone_moss.py` is new. Cushion sites are Poisson-spaced on the moss field.
  Each cushion has 26-44 tapered shoots (1.2-3.2 cm, domed, about 4 % red-brown sporophytes) over a darker cushion
  shell. RiverLong's moss follows the crest: a band set by distance in plan, plus satellites. Grass tufts now sit
  on the cliff's benches (70).
- **Foliage UVs.** The moss shoots and grass blades are joined after the unwrap and the bakes. Each strip gets its
  own tiny cell in a reserved UV band (u > 0.985). Smart project had folded the curved blades (5-13 SAT overlaps),
  and the partial re-projects then collapsed the cliff's packing to fill 0.04. The cliff's last 3-9 overlapping
  sliver faces are isolated the same way.
- **Wet.**
  - Band height 0.30-0.32 H, warp 0.12, softness 0.10.
  - No splash patches; an algae line at the waterline.
  - Wet roughness 0.07 in the pits, 0.22 on flats.
- **Riverbank test.** The stand-in ellipsoid cobbles are replaced by linked, scaled copies of our river boulders:
  cobbles, pebbles, gravel, and a denser skirt at each boulder. The boulders sit 8 cm deeper.
- **River UVs.** Two methods were tried and reverted:
  - smart project at 40 deg: bake-margin bleed on the island borders at 2K;
  - 26-direction charts: seam slits.

  Pilot 2's 6-direction charts are kept.

### Measured (pilot2_f1/measure.json; at the sheet's pixel size)
| | RiverRound | RiverLong | CliffChunk |
|---|---|---|---|
| IoU front / side | 0.92 / 0.85 | 0.89 / 0.92 | 0.87 / 0.85 |
| IoU vs the sheet's lower view (best oblique) | 0.65 | 0.95 | 0.82 |
| solidity front (ours / sheet) | 0.992 / 0.976 | 0.974 / 0.968 | 0.939 / 0.96 |
| solidity side (ours / sheet) | 0.983 / 0.945 | 0.994 / 0.978 | 0.954 / 0.966 |
| corners > 35 deg front (ours / sheet) | 3 / 5 | 6 / 4 | 16 / 17 |
| corners > 35 deg side (ours / sheet) | 4 / 12 | 6 / 8 | 17 / 8 |
| corner r / short, front (ours / sheet) | 0.18 / 0.10 | 0.27 / 0.26 | 0.11 / 0.11 |
| plane fraction k6 15 deg (dense; pilot 2 in brackets) | 0.30 (0.18) | 0.30 (0.24) | 0.45 (0.34); SG14 0.6 not met |
| local std, whole rock (ours / sheet) | 0.084 / 0.145 | 0.092 / 0.129 | 0.099 / 0.142 |
| luma p50, whole rock (ours / sheet) | 0.37 / 0.38 | 0.34 / 0.32 | 0.39 / 0.33 |
| luma p50, bottom 30 % (ours / sheet) | 0.20 / 0.20 | 0.18 / 0.19 | 0.37 / 0.31 |
| hue / sat (ours) | 40 / 0.10 | 45 / 0.08 | 39 / 0.08 |
| hue / sat (sheet) | 34 / 0.17 | 36 / 0.15 | 35 / 0.21 |
| moss share (ours / sheet) | 2.4 % / 2.7 % | 5.6 % / 8.9 % | 5.8 % / 5.0 % |

Close-ups, local std / p50 (ours / sheet):

| Close-up | Ours | Sheet | Note |
|---|---|---|---|
| grain | 0.41 | 0.32 | crystals now at scale; hue 46 vs 10, still warm |
| fracture | 0.27 | 0.39 | |
| moss | 0.25 | 0.40 | |
| lichen | 0.24 | 0.38 | the chosen spot shows almost no rosettes |
| wet | 0.23 | 0.39 | |
| riverbank | 0.18 | 0.38 | |

QA and export:
- qa_check (require_uv1, require_ucx, texel 5.12 +-25 %): 0 hard fails on all three.
- Texel: 5.12, 4.81 and 4.72 px/cm.
- Exported through Scripts/pipeline: SM_DKR_Rock_BoulderRiver01, SM_DKR_Rock_BoulderRiver02 and SM_DKR_Rock_Cliff01,
  with their T_DKR_* maps. New maps: T_DKR_LichenDetail_BC/_N/_HID.
- Triangles: 187k / 315k / 396k. Of these, moss shoots and grass are 37k / 133k / 150k. The catalog was patched with
  these totals; build_rocks2 now records them itself.

### What still fails (my read: about 5/10; no judge run)
1. **Cliff.** Cuboid joint blocks, horizontal joints, crisp arrises and benches are in, but the front still reads as
   a flat, gridded wall (coursed masonry). The blocks' faces come from the traced hull's flat prism walls.
   - Next method: build the chunk as an assembly of separate jointed blocks, each with its own hull, rotated and
     displaced, instead of fracturing one hull in place.
2. **RiverRound form.** In the clay 3/4 view it reads as a rounded box with three big planes; the sheet's boulder
   is lumpier, with more and smaller facets.
   - The 6-direction chart seam on its left face stretches the grain; it shows in the riverbank close-up.
3. **Surface value and colour.**
   - Whole-rock local contrast is 0.08-0.10 against the sheet's 0.13-0.15.
   - Saturation is about half the sheet's. That is by design (grey granite, tan only as staining: the owner's
     call); flag it if the owner wants the sheet's warmth.
4. **Lichen and moss close-ups.**
   - At the picked spot the lichen zone is too low to show rosettes.
   - The moss shoots read as sprigs over a flat shell; the sheet's cushions are denser.
5. **Wet and riverbank.** The wet close-up has no splash and no meniscus. The riverbank bed is still a flat stand-in
   plane.
6. **Foliage budget.** The foliage is heavy (133k-150k tris on RiverLong and the cliff) and needs a LOD or Nanite
   foliage decision.

### Files
- New code: Scripts/stone/stone_moss.py.
- Changed in Scripts/stone/: rock_corestone, rock_fracture, scan_surface, stone_weather2, and stone_bake (a
  CHART_DIRS option).
- Changed in Scripts/dojo/rocks/: rocks_plans2, rocks_form2, build_rocks2, rocks_material2, rocks_render2,
  rocks_render2_final, rocks_measure2.
- Render and measure output now defaults to `pilot2_f1/` (env ROCKS_OUT).
- The round 4 cliff dense is kept as work2/CliffChunk_dense_r4.npz.
