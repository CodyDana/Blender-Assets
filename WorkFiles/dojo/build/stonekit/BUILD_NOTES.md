# Dojo stone kit: BUILD NOTES

<!-- track9-stairs:begin -->
## Track 9: STAIR PATH kit (2026-09-29, first build)

**Brief:** extend our own stone kit for the landscape reference's stone stair path (References/Dojo/dojo_landscape_ref.png,
lower left): granite flights, landings, rubble cheeks, timber handrails, path lanterns. Sunset. Modular (the terrain is
not in yet). No Unreal in this run (another workflow owns DojoLab).

**Code:** `Scripts/dojo/stonekit/build_stairs.py` (builder), `render_stairs.py` (Cycles renders), `compose_stairs.py`
(sheets, reference crops), `verify_stairs_fbx.py` (fresh-process FBX re-import), shared helpers in `sk_shared.py`.
Nothing is forked: kit 1 (`build_kit1.py`) and the courtyard stone props (`build_stone_props.py`) are imported without
running their main() (`sk_shared.load_builder`); `kit1_geo` and the material library are plain imports.

### Grid (measured on the built meshes, not assumed)
| | value |
|---|---|
| riser / tread | 1/6 m (0.1667) / 1/3 m (0.3333), pitch 1:2 = 26.57 deg; 3 risers per 0.5 m rise per 1.0 m run |
| measured risers (centre line, all 6 flights) | 0.162 - 0.172 m (worn tops, per-stone tilt +-4 mm) |
| collision ramp (UCX) | 25.97 - 26.43 deg through the tread midpoints, 8.3 cm lip at the foot; feet within +-R/2 of the stone |
| GASP | MaxStepHeight 45 cm, walkable 44.77 deg: every flight passes (measure.json `gasp_ok`) |
| widths | 1.2 and 1.8 m; rises 0.5 / 1.0 / 2.0 m (runs 1 / 2 / 4 m) |
| landings | W x W square, W x W turn (curbs on the two outside edges), (2W + 0.4) x W switchback; paving top 0 +0.3 cm (joints 1.0 - 1.4 cm wide, 7.5 cm deep) |
| cheeks | 0.40 thick, stepped 0.30 above each metre's highest tread; placed at +-(W/2 + 0.20) |
| rail line | inset 1/6 m from every edge and set back 1/6 m before the first riser: posts stand mid-tread and a rail turns a landing corner exactly (outside-turn span W - 1/3: Rail_Flat_T120 / T180) |
| below grade | every stone piece runs 0.35 m under its walking level |
Chaining rules, snaps and pivots per piece: `kit_catalog.json` -> tracks.stairs.how_to_chain, pieces[*].snaps.

### Pieces (30, all `Exports/DojoKit/StoneKit/SM_DKT_Stair_*.fbx`)
| group | pieces | tris LOD0 | render budget |
|---|---|---|---|
| flights | Flight_W{120,180}_R{050,100,200} | 5.6k - 34.7k | Nanite, LOD0 only (<= 250k per piece) |
| landings | Landing / LandingL / LandingSB _W{120,180} | 7.3k - 47.3k | Nanite |
| cheeks | Cheek_R{050,100,200}, Cheek_L{120,180}, CheekCorner | 2.4k - 162.5k (R200) | Nanite |
| rails | Rail_Slope_R{050,100,200}, Rail_Flat_L{120,150,180}, Rail_Flat_T{120,180}, Rail_EndPost, Rail_CornerPost | 224 - 864 | LOD0-2 (50 / 25 %) |
| lanterns | Lantern_Timber 1.18 m (r2 hood), Lantern_Stone 0.90 m | 1.6k / 13.8k | LOD0-2 |

Collision: flights one convex ramp; landings one flat box (+ curb boxes); cheeks one box per 1 m segment (flat walkable
tops); rails a post box + a thin slab per bay; lanterns post + lamp boxes (thin upright class).

### Stone language (what is reused)
- Steps and landing kerbs: `kit1_geo.rough_block` (kit 1's side / sill steps), then worn: the top keeps 30 % of the
  block relief, a foot-traffic hollow (7 mm, deepest at the nosing), per-stone tilt, 0-2 chips out of the rounded
  (28 mm) nosing. 2 stones per 1.2 m step, 3 per 1.8 m, staggered joints.
- Flagstones: `kit1_geo.pillow_face` laid flat, dressed parameters (flat crown, low relief).
- Cheeks: kit 1's footing language: pillow-faced rubble courses (`pillow_face`, kit 1's big-row numbers, material
  `M_DK_FootingStone`), a dressed coping course and squared quoin through-stones (`rough_block`), a joint-earth core
  (`M_DK_JointEarth`) recessed 8 cm behind every face.
- Stone lantern: the courtyard `LANTERN_SHORT` (build_stone_props.lantern, moss cushions, library pass) at 0.75 scale.

### Materials
- `M_DKT_StepGranite` (new kit variant, recipe in `sk_shared.granite_moss_variant` + `VARIANT_NORMAL`, keyed by name so
  track 8's stair opening builds the identical material): library Granite x 0.92, 0.20 to its mean, moss by Wear.A
  (kit 1's moss colour), normal strength 0.55 (walked stone; UE FlattenNormal 0.45). Moss passes: step ends, tread
  backs, riser feet, joints; landings: joints and the kerb foot.
- Kit 1's `M_DK_FootingStone` / `M_DK_JointEarth` (same MIs as kit 1), library `M_DJ_GraniteRubble` (flight cores),
  `M_DJ_TimberDark(+End)` (rails, lantern), `M_DJ_Iron` (lantern hood / finial), `M_DJ_GlassAmber` (the panes, a
  separate slot). The stone lantern keeps the courtyard lantern's own slots (`M_DJ_Granite_Tri`, `M_DKP_Stone_Moss`...).

### Rounds and decisions
1. Rail inset 0.09 -> 1/6 m: the assembly showed a rail could not turn a landing corner on the grid (7.7 cm miss);
   with the inset = the post set-back every corner lands exactly; added the T spans.
2. Cheek core showed through on the step faces (probe_pixel.py hit `M_DK_JointEarth` on the step plane): the core above
   each lower coping line is now recessed 8 cm like the wall ends.
3. Step tops were lumpy ("sponge" in raking sun): relief compressed on the tops, step granite normal 0.55.
4. Timber lantern r1 was a slim post; measured the sheet's lantern (8x crop): panelled pedestal as wide as the light box,
   bracket feet, cornice, two panes a face, hood 1.55 x the box -> rebuilt. Side-by-side then showed the hood as a flat
   pyramid against the sheet's steep hipped roof with upturned tips -> r2 hood (square loft: concave flanks, 3 cm
   corner upturn, rise 0.19) and a flared pedestal skirt.
5. Turn in the assembly: a LEFT turn into the cliff (LandingL rot -90); the catalog documents both hands.

### Verification
- qa_check: 30 pieces, 0 hard fails (UV0 tiling overlaps waived as kit 1); texel 5.08 - 5.37 px/cm on the stone.
- Fresh Blender process re-import of all 30 FBX (`stairs/fbx_verify.json`): LOD counts, UCX keyed to the render node,
  slots, sizes = catalog: 30 / 30 ok.
- NOT done here: Unreal import (DojoLab busy); run the kit's FBX through the usual fresh-process UE verify when free.

### Open points
- GlassAmber panes read pale peach under Blender AgX at the library strength 5 (the library's known hue issue); the
  sheet's panes are deep amber. Set in the Unreal look pass with the lantern point lights.
- The iron hood shows the library Iron's rust patches; the sheet's hoods read charcoal. A darker hood (TimberDark or a
  roof-tile set) is a one-line change if the user prefers.
- The reference steps read lighter and smoother than our granite under sunset; the upper flight of the sheet uses long
  single slabs per step (ours: 2-3 stones). Either could be a variant.
- Rails only on outside turns / straight runs: an inside-corner rail is not in the kit (the grid would need a 1/3 m
  short span).
- Stand-ins only in the assembly (terrain, terrace block, boulders): the user sources the landscape.
- `Assets/Dojo/DojoStoneKit.blend` holds collection `StoneKit_Stairs`, merged under `sk_shared.file_lock`; a track
  that saves the whole file without merging would drop it (re-run build_stairs.py to restore).
<!-- track9-stairs:end -->

## Track 8: terrace retaining wall (2026-09-29)

Full notes: `wall/BUILD_NOTES.md`. 41 pieces SM_DKT_Wall* (straight 2/4 m x H2/3/4/6, CornerOut/CornerIn, EndL/EndR, StairOpening_H2/3/4 on the track-9 stair grid, WallCoping_*, WallFoot_*), QA 0 hard fails, 32 Nanite + 9 LOD0-2, 3.15 M tris LOD0. Grid: Z 0 = terrace grade, pivot on the face line at the module start, face -> -Y, batter d(s) = 0.10 s + 0.035 s^2, interlocking 0.18 m course teeth at every module end. Renders: `renders/wall/` (KIT_SHEET_*, asm_*, close_*, sbs_*).

<!-- f1-fix:begin -->
## Fix round 1 (2026-09-30): both tracks, the judge's 6/10 blockers and 12 deltas

The judge could pick our wall and steps in a blind test for three reasons. The wall stones were uniform pillows in
wide, pebbled joints. The stone was one pitted "sponge" material that read chocolate at sunset. The steps had no
nosing. This round fixes the shared stone language in `sk_shared.py`, which both builders import. It then fixes each
track's pieces.

### Shared stone language (`Scripts/dojo/stonekit/sk_shared.py`)
- **`lay_courses`:** lays face stones as irregular 5-7 sided polygons in rough courses.
  - Each course boundary zig-zags through the joints of the two courses it separates. It rises under each joint of
    the course above and drops over each joint of the course below.
  - So every stone is convex, neighbours nest with diagonal and rhomboid joints, and both sides share the boundary.
  - Module ends stay on the global course table, so the teeth still interlock.
  - Used by: the wall faces, the flight sides, the cheek bases, the landing sides and the bastion sides.
- **`dressed_stone`:** calls `kit1_geo.pillow_face` with the judge's numbers.
  - A flat crown: bulge 1.4 cm or less, crown exponent 3.5-5.
  - Small crisp arrises (8-13 mm), little corner rounding, calm relief (2.5 / 0.8 mm).
  - A ±2 deg tilt, so neighbouring stones catch the light differently.
  - A sliver filter: a stone narrower than 6 cm at its narrowest caliper width is skipped.
- **`KIT_MATS` / `kit_material`:** one granite family for the whole kit. Each is an `M_DJ_Lib_Opaque` recipe: Tint,
  FlattenToMean, moss lerp on VertexColor.A, normal strength.
  - `M_DKT_WallGranite`: tint 1.40/1.42/1.46, flatten 0.40, normal 0.25. Used on wall faces, coping, cheeks and
    flight sides.
  - `M_DKT_StepGranite`: tint 1.52/1.53/1.56, flatten 0.48, normal 0.18. Treads and flags: light and smooth.
  - `M_DKT_StepRiser`: tint 1.02/1.02/1.05, flatten 0.30, normal 0.35. Risers and ends: darker and rougher.
  - `M_DKT_JointDark`: tint 0.26, flatten 0.65. The joint core; it replaces kit 1's pebbled `M_DK_JointEarth` in
    this kit.
  - The albedo is pale grey-beige (linear mean about 0.25 / 0.22 / 0.20); the warmth comes from the sunset light.
- **`stone_tone`:** macro variation written into the `Wear` corner colours after the moss pass. Unreal reads these
  unchanged.
  - Each stone gets its own grime offset (0-12 % darker).
  - Undersides are darker.
  - Upward faces get the edge-wear lift, which gives light, patchy weathered tops.
- **Moss:** only in the joints (occluded rims) and on ledges, never as a tint across whole faces.
- **UVs:** every kit stone material is box-projected per face (`BOX_UV_MATS`). This removes the planar stretch on the
  stone flanks.

### Track 8, wall (`build_wall.py`)
- The faces use `lay_courses` with `dressed_stone`. Packing chips are gone.
- The coping, sangi-zumi and plinth blocks have calmer relief.
- **H6 inside corners** now take **3 m arms**, so the next pivot is (3, -3, 0) at yaw -90. H2-H4 keep 2 m. The
  return leg is fully laid to the foot. `SM_DKT_WallFoot_CornerIn_H6` is now 1.51 x 1.52 m.
- **Outside-corner flare:** now 0.005 s² faded over 1.4 m (was 0.008 over 1.0).
  - The sangi-zumi blocks move rigidly.
  - The face stones take only their own outward component, so none is stretched along the face.
  - The joint core no longer follows the flare, which removes the curled sheet at the toe.
- **Foot skirt:** sparse, flat, angular slabs, mostly buried: `skirt_flat`, one row, about 40 % cover, tops 2-7 cm
  above grade.
- **Stair openings:** use track 9's f1 steps (1-2 slabs per step, nosing set-back, tread / riser materials).
- The merge into `DojoStoneKit.blend` now folds duplicate `.001` materials, as the stairs merge does.
  `fold_kit_blend.py` repaired the file once.

### Track 9, stairs (`build_stairs.py`)
- **Steps:**
  - 1-2 long slabs per step (`step_cuts`).
  - The riser face sits **4.0 cm** behind a rounded, worn nosing (LIP 5 cm).
  - Treads use `M_DKT_StepGranite`; risers, ends and undersides use `M_DKT_StepRiser`.
  - Slabs are 0.40 m deep, with the underside sheared to the pitch, so all the slabs' bottoms lie on one line.
- **Flight sides:** wall-granite polygon courses under that line, with a `M_DKT_JointDark` core. They replace the
  GraniteRubble prism.
- **Landings:** flush Voronoi flags (0.45-0.9 m) run to the edges with joints of about 1 cm and flat tops. There are
  no curbs on any landing now, so Landing and LandingL differ only in flag layout and snaps. One low course of side
  stones sits under the flags.
- **Cheeks** are LOW:
  - One dressed through-stone per tread, standing **+0.15 m** over it. Their undersides lie on the pitch line: 0.30 m
    thick at the thin end.
  - Cheek_L: the same, flat over the paving.
  - Below them, a buried wall-granite base.
  - Collision: one flat-topped box per stone.
- **Rails:**
  - Round poles (6.8 / 5.6 cm) pass through round posts with domed tops. Posts are 0.86 m (top pole at 0.76, mid at
    0.38).
  - Every `Rail_Slope_*` carries the posts at both its ends.
  - `Rail_Flat_L*` / `Rail_Flat_T*` are the poles alone, hung between posts that other pieces supply: a slope's end
    or start post, `Rail_CornerPost` or `Rail_EndPost`.
  - Two slopes chained with no landing would put two identical posts in the same place: use the longer slope piece.
- **`Lantern_Timber`** (1.31 m):
  - The shaft is 0.176 m, against 0.244 in r0.
  - Four splayed legs sit under a flared skirt, with frame panels on the shaft and a cove bracket to the cornice.
  - The roof is steep and pointed (rise 0.27) with curved, upturned eaves and a tall bulb finial.
- `Lantern_Stone` stays in the kit as an extra and is not used in the reference-matching assemblies.
- Nanite pieces now ship without UV1, as track 8 does; the two R200 flights had failed UV1 overlap. LOD pieces keep kit
  1's checked UV1.

### Measured (`f1_measure.json`, `stairs/measure.json`, `fbx_verify_f1.json`)

**Wall face** (Wall_4m_H3, 2 mm ray scans; visible joint = rays that miss a stone's front):

| measure | median | p10 | p90 |
|---|---|---|---|
| visible joint (m) | 0.018 | 0.012 | 0.046 (junctions crossed on the diagonal) |
| crown rise (m) | 0.0047 | | 0.0088 |

**Steps:**
- Nosing overhang, frontmost nosing point to the riser face: median **0.026 m** on every flight (range 0.007-0.031).
- Risers 0.156-0.176 m.
- UCX ramp 25.97-26.43 deg, GASP ok on all 6 flights.
- On Flight_W180_R100, 18 of 18 tread rays hit StepGranite and 18 of 18 riser rays hit StepRiser.

**Landings:** paving top -0.007 to +0.001 m. Joints median 0.016 m.

**Lantern:** shaft (with its frames) 0.186 m against a 0.28 m light box.

**QA and export:**
- `qa_check`: 0 hard fails on all 71 pieces.
- Fresh-process re-import of all 71 FBX: 71 / 71 ok (LODs, UCX keyed to the render node, sizes equal the catalog,
  slots clean).

**Budgets:**

| track | pieces | Nanite | LOD0-2 | LOD0 total |
|---|---|---|---|---|
| wall | 41 | 27 | 14 | 2.96 M |
| stairs | 30 | 18 | 12 | 0.68 M |

Largest pieces: StairOpening_H4 386k, Flight_W180_R200 121k.

### Renders (`renders/f1/`, Cycles, denoised, headless)

**Kit sheets:** `KIT_SHEET_{wall_straight, wall_corners, wall_ends, wall_stairs, wall_topfoot, stair_flights,
stair_landings, stair_cheeks, stair_rails, stair_lanterns, overview}.png`. Each piece is shown ortho front / side /
top plus 3/4 on grey with the 1.8 m figure, from `sheet/`.

**Sunset A: terrace wall.** `asm_overview`, `asm_corner`, `asm_terrace_wall`, `asm_stair_head`, `asm_stair_path`.
- The run: EndL_H3, 4m_H3, StairOpening_H3, 4m_H3, 2m_H4, CornerOut_H4, 4m_H4, with feet.
- Kit 1's wall and footing stand on the coping.
- The path runs down the wall foot, with rails on the drop side only (none on the wall-face flight), low cheeks and
  timber lanterns only.

**Sunset B: stair path.** `assembly_{overview, up_the_path, turn, down}`. Flights, a straight landing and a left-turn
landing climb a stand-in slope, with a low cheek on the cliff side, rails on the drop side (slope posts at both ends,
corner post and T span) and one lantern per landing.

**Close-ups:** `close_stone_faces`, `close_sangi_zumi`, `close_opening_nosing`, `close_coping_top`, `cu_step_nosing`,
`cu_step_side`, `cu_cheek_stone`, `cu_rail_joint`, `cu_lanterns`, `cu_landing_turn`, `cu_landing_flags`.

**Reference | ours:** `sbs_{terrace_wall, stair_head, stair_path, overview, stone_faces, wall_lower, step_nosing,
stairs_low, stairs_mid, lanterns, lantern_close, rail_joint, landing_flags}.png`, made with
`Scripts/armory/side_by_side.py`. Crops are in `refcrops/`.

**Code:** `render_f1.py`, `compose_f1.py`, `measure_f1.py`, `catalog_f1.py`, `fold_kit_blend.py`, and
`verify_stairs_fbx.py --all`.

### Open points (f1)
- **Not verified in Unreal** (DojoLab belongs to the round 8 sky workflow). Still to check: import, Nanite, UCX, and
  the new MIs, which do not exist in Unreal yet. They need creating from `tracks.*.materials` in the catalog, under the
  PackMaterials lock: M_DKT_WallGranite, M_DKT_StepGranite, M_DKT_StepRiser and M_DKT_JointDark.
- **Style anchor tone:** the terrace now reads paler than kit 1's footing, which keeps FootingStone at tint 0.55. If
  the dojo footing should match, retinting it is the kit 1 owner's call.
- **Step close-ups:** the risers still show the library granite's speckle and normal pits at arm's length under the
  grazing sunset sun, though much calmer than r0. A smoother dedicated tread / riser texture set would be the next step
  if the blind test still picks them.
- **Visible joints:** the p90 (4.6 cm) comes from junctions crossed on the diagonal. The joints themselves are 0.7-1.1
  cm between rims.
- **Landings** have no curbs now (the judge: flush, low edge). A railing on a landing's drop side stands on the paving.
- **Rails:** chaining two slopes directly (no landing) doubles one post (identical geometry): prefer the longer slope.
- **Lantern_Timber:** panes pale peach in Blender (library GlassAmber under AgX); the Iron roof shows rust patches. Both
  are for the Unreal look pass.
- **CheekCorner** (1.4k tris) is flagged Nanite, which is harmless but could be LOD0-2.
- **Earlier open points still stand:** no step-down piece between wall heights, stair openings stop at H4, and the
  assemblies use stand-ins (terrain, boulders, terrace block) that the user's landscape replaces.
- **Lock:** `DojoStoneKit` is still held by agent "claude"; release it when the orchestrator is done. Nothing is
  committed.
<!-- f1-fix:end -->

## Fix round 2, f2 relaunched after STONE_BUILDING_STUDY.md (2026-09-30)

The owner stopped the first f2 run at about 09:33 and asked for a stone study first. This round follows
`STONE_BUILDING_STUDY.md`: its pipeline (sections 4.4 and 4.5), its gates (6.2) and its dojo appendix (8.2). The
owner's reading of the reference is the authority. There was no Unreal work in this round (another track owns DojoLab),
and nothing was committed.

**Backup:** `Backups/DojoStoneKit_f2pre_2026-09-30/` holds the stopped run's state: Scripts, `Assets/DojoStoneKit.blend`,
`Exports/StoneKit`, and in WorkFiles the catalogue, measures, track blends, `renders/f2` and `renders/f2dev`. To restore,
copy those folders back. The f1 backup is untouched.

**What I reused from the stopped run:** the whole f2 kit. That covers the kerbs, the low cheeks, the sweep variant set,
the squared rails, the charcoal hood and weathered timber, `render_f2` / `compose_f2` / `measure_f2` / `catalog_f2`, and
the stair track's geometry (3-5 short blocks per tread, flush flags). The stair geometry was not changed; the stairs were
rebuilt once so the new materials would take. The things this round changed are listed below.

### Tools (new, in `Scripts/stone/`, lock `StoneTools`: the study's 4.17 / 6.8 location)
- `stone_measure.py`: both value methods from study 3.11, shape statistics from a trace or a layout, and gates SG3,
  SG4, SG7, SG8, SG9, SG10, SG11 and SG12. Checked against the study: method A and the method C percentiles and dark
  fraction reproduce 3.11 exactly. The method C saturation does not reproduce (see pitfall P49).
- `stone_trace.py`: manual and seed modes, gridded crops, overlay, validation.
- `stone_layout.py`: `coursed_rounded`, with the measured h/w mixture, leaning joints in runs, broken courses and
  per-corner cuts.
- First trace: `References/Dojo/trace_terrace_lower.json`. Made in seed mode and curated by hand: 33 body stones and
  4 cap stones at 32 +- 6 px/m. Scale cues: the rail posts give about 30 px/m and the cap course about 34 px/m.
  Reference, scale-free: upright share 0.70, tall share 0.49, h/w median 1.18 (p10 0.78, p90 1.84), area CV 0.55,
  cap height / body height 1.12.

### Wall (track 8)
- **Layout:** `sk_shared.lay_measured` now uses `stone_layout.coursed_rounded`. Course table 0.31 + 0.03 s. Every
  built outline is logged to `wall/layout_Wall_*.json`.
- **Stones:** `pillow_stone_v2`.
  - Per-corner radius (cuts at 13-22 % of the short side, 0.5-1.5 x each).
  - Crown at 8-22 % of the short side (1.5-6 cm), crown exponent 2.0-2.8.
  - The crown peak sits 15-30 % off centre, toward the top.
  - Tilt up to 3 degrees.
- **Cap course:** 0.34 m high, 0.34-0.46 m long, arris radius 24 mm, moss cushions on top.
- **Joint core:**
  - noisy front, 6-14 cm behind the face (no flat board);
  - darker (0.034);
  - patchy moss.
- **Materials:**
  - Per-stone tone spread 0.48.
  - Granite flatten 0.64 / normal 0.28 (less of the blotchy speckle).
  - Stone tint: kit 1's footing hue at mid-grey, channel ratio 1 : 0.86 : 0.74.
- **Unchanged:** the straight 1:10 default, the sweep variant set, sangi-zumi corners, the level buried footing.

Measured on Wall_4m_H3 (`f2_measure.json`, `f2_gates.json`):

| Measure | Ours | Target / reference |
|---|---|---|
| Visible joint (ray scan) | median 3.2 cm (p10 2.4, p90 7.0) | owner: 2-4 cm |
| Batter | 1:10.2 | 1:10 |
| Upright share | 0.755 | 0.70 |
| h/w median | 1.23 | 1.18 |
| Area CV | 0.554 | 0.554 |
| Crown CV / corner-radius CV | 0.36 / 0.46 | >= 0.3 |
| Stone size | 0.25 x 0.32 m | trace cells 0.23 x 0.27 m + joint, +-20 % |

Daylight gate rig (sun 62 degrees, exposure 0.6, AgX Medium High Contrast, close view framed to the reference crop's
stone size):

| Gate | Ours | Reference |
|---|---|---|
| Dark-joint fraction | 0.318 | 0.252 |
| p90/p50 | 1.77 | 2.04 |
| Local std | 0.058 | 0.056 |
| Hue | 34.9 degrees | 30.5 degrees |

### Stairs (track 9), lanterns, rails
- Only the materials changed: warm mid-grey treads and risers (f2's cool tint read lilac at sunset), calmer risers
  (flatten 0.66), and yellower amber panes (tint 0.80 / 1.0 / 0.26).
- Timber lantern to rail clearance: 1.0-1.2 m in the stair scene and 1.1-1.3 m in the wall scene. One lantern per
  landing; no rail runs through a roof.
- The "second lantern" seen in `assembly_overview` is the lantern's own shadow on the slope behind it, not geometry.

### QA and export
- 104 pieces, `qa_check` 0 hard fails. UV0 tiling is waived as before, and the Nanite pieces ship without UV1: they are
  game only, and UV1 must be restored before Fab.
- Fresh-process FBX re-import: 104 / 104 OK.
- verts/tris: max 0.56.
- Walkability:
  - risers 0.163-0.170 m;
  - treads 0.331-0.333 m;
  - UCX ramps 25.97-26.43 degrees (GASP walkable 44.77).
- `kit_catalog.json`:
  - 173 `traversal` boxes (study 4.13);
  - the `f2_fix_round.study_round_2` record and the gates.
- Wall track LOD0: 7.9 M tris (f2: 2.96 M), because there are about twice as many, smaller stones. Wall_4m_H3 is
  218k (the study proposes 100-150k).

### Deviations from the study (and why)
- **Coursed layout (4.5.1) with the measured mix, not a power diagram (4.5.2).**
  - Why: module ends must interlock on the global course table, and the owner asked for round 0's rounded stones.
  - Cost: the flat J1 sheet (`gate_layout_flat.png`) shows our bed lines are more regular than the reference's
    ranzumi. SG5 is not measured yet.
- **SG11 saturation / R/B not met on purpose.** A saturation of 0.11 against the reference's 0.176 is the owner's
  "mid-grey, not beige or brown". A warmer trial passed in daylight but read tan at sunset.
- **One layout seed per module** (the study proposes 3 seeds: open decision 8.5).
- **Only the short-block flight** (the owner's reading). The long-slab variant is open decision 8.5.
- **Moss is a vertex-colour lerp.** The reference's joint "moss" is mostly grass tufts; SG12 is 0.013 against 0.0195.
  The tufts are the pines chat's units, not built here.
- **Traces:** only the terrace wall was traced (one crop, seed mode). The flights and landing were not re-traced; the
  owner's reading was used for them.

### Renders (`renders/f2/`, Cycles headless, denoised)
- Kit sheets: `KIT_SHEET_*.png` (13 sheets), and `sheet/<piece>_{front,side,top,persp}.png` for all 104 pieces.
- Sunset assemblies: `asm_*`, `assembly_*`.
- Close-ups: `close_*`, `cu_*`, `match_*`.
- Gates: `gate_stone_faces`, `gate_elevation`, `gate_grazing`, `gate_layout_flat`, `GATES_f2.png`.
- Side by sides: `sbs_asm_terrace_wall`, `sbs_stairs_low`, `sbs_stairs_mid`, `sbs_close_stone_faces`,
  `sbs_close_step_nosing`, `sbs_lanterns`, `sbs_rail_joint` (plus wall_lower, lantern_close, landing_flags).
- New scripts: `gates_f2.py` and `retone_f2.py`, a material-only re-tone. The FBX carry no material values.

## Fix round 3, f3 (2026-09-30)

Built from the f2 round-2 state, following `STONE_BUILDING_STUDY.md` (4.4 stones, 4.5 layout, 6.2 gates, 8.2 dojo
appendix) with the owner's reading on top. No Unreal (another track owns DojoLab), nothing committed, no downloads. The
pines chat's Blender job was left running.

**Backup:** `Backups/DojoStoneKit_f2_2026-09-30/` holds the f2 state: Scripts `stonekit` and `stone`,
`Assets/DojoStoneKit.blend`, `Exports/StoneKit`, the WorkFiles catalogue, measures, track blends, trace and `renders/f2`,
the trace JSON and the study. `RESTORE.txt` says where each folder goes back.

**Judge deltas vs the reference:** every delta was checked on the reference crops (the lower terrace wall at 4x and 6x,
the stair path at 2x, the f2 ref crops). The accepted and rejected list, with reasons, is in `f3_deltas.json` and in
the catalogue under `f3_fix_round.judge_deltas`.

### Wall (track 8)
- **Layout: method change** (study P38 and pitfall P56). `Scripts/stone/stone_layout.coursed_fitted` keeps the coursed
  frame and turns every T-junction into a Y-junction:
  - the stone that runs through the junction is pushed up the head joint;
  - the two corners that meet there are chamfered to match.

  Neighbours now share their outlines, so one inset makes every joint.
  - Module ends: tooth junctions use fixed push and chamfer numbers, so modules still interlock.
  - Hard ends (corner blocks, openings) stay square.
  - Beds wander +-12 cm. Tall stones get about 30 % of the chances. Narrow slots merge into a neighbour instead of
    leaving a hole.
- **Rims and rounding:** 1.3-1.7 cm between rims (inset 0.65-0.85 cm). Corner rounding (Chaikin keep) is 0.14-0.22.
- **Course table:** 0.34 + 0.03 s, so stones are about 0.36 x 0.45 m (f2 +30 %). The reference's near end of the lower
  terrace wall confirms the size.
- **Moss cushions as geometry:** `sk_shared.moss_pad`, on a new slot `M_DKT_MossPad` (the same master, with the Wear.A
  lerp).
  - In the bed joints: 30-75 % of stones, denser low down and under the cap.
  - On the cap tops: across 55 % of the top joints.
- **Tone:** per-stone tone spread 0.62 (f2 0.48). The tint is unchanged (the owner's mid-grey).
- **New tool:** `sim_layout_f3.py` simulates the flat layout outside Blender (study stage b) and writes
  `renders/f3/layout/sim_flat.png`.

### Stairs (track 9), kerbs, rails, lanterns
- **Treads:** 4 (W120) / 5 (W180) short setts on even steps and one fewer on odd steps (0.30-0.45 m, staggered).
  End joints are 0.8 cm and the rounded nosing has a 3.0 cm radius.
- **Kerbs:** +0.09 over the path.
  - The f2 "spike" was the stand-in slope cutting away from the kerb's buried end. All kerb bottoms measure -0.25 m.
  - The f3 scene seats kerbs in a soil bank (study pitfall P58).
- **Rails:** posts are 9.6 cm (f2 11), still round with domed tops. The timber is darker (tint 0.38). The rails were
  already housed into the posts.
- **Lantern_Timber:** a taller box (h/w about 1.2) and a straighter, steeper roof (flanks about 57 deg, eave 0.38 m).
  The finial is 1.9 x taller. The lantern is now 1.51 m tall; clearance to the rails is 1.02-1.23 m.
- **The "doubled lantern":** it was each lantern's shadow falling on the slope behind it at sun azimuth -35. The f3
  stair renders use -75. One lantern per landing, measured.

### Measured (`f3_measure.json`, `f3_gates.json`)
| Measure | f3 | f2 | Target |
|---|---|---|---|
| Visible joint, Wall_4m_H3 (ray scan) | median 2.8 cm (p10 0.8, p90 6.6) | 3.2 | owner 2-4 cm |
| Dark-joint fraction (daylight gate, 6 stones across) | 0.208 | 0.318 | 0.252 +-30 % PASS |
| p90/p50 | 1.59 | 1.77 | 2.04 +-15 % FAIL |
| Local std | 0.060 | 0.058 | 0.056 PASS |
| Moss share (hue 50-80) | 0.020 | 0.013 | 0.0195 PASS |
| Hue / sat | 35.6 / 0.113 | 34.9 / 0.110 | 30.5 / 0.176 (owner mid-grey: deviation kept) |
| Upright share / h/w median (H3) | 0.71 / 1.19 | 0.76 / 1.23 | 0.70 / 1.18 PASS |
| Area CV (H3) | 0.53 | 0.55 | 0.55 PASS |
| Bed continuity (SG5, tol 0.2 h) | 0.78-0.85 | not measured | 0.44 FAIL |
| Crown rise | median 2.0 cm, p90 4.0 | 1.4 / 2.9 | - |
| Batter | 1:10.7 | 1:10.2 | 1:10 |
| Kerb top over walk | 0.083-0.092 | 0.051-0.072 | 0.08-0.10 |
| Wall track LOD0 | 6.90 M tris (4m_H3 156k) | 7.9 M (218k) | - |

- **QA:** 104 pieces, 0 hard fails. The fresh-process FBX re-import gives 104 / 104 OK.
- **Geometry:** verts/tri max 0.56.
- **Walkability:** risers 0.157-0.171 m and treads at least 0.327 m, which pass.
- **Catalogue:** 173 traversal boxes kept.

### Deviations from the study (and why)
- **Coursed-and-fitted, not the power diagram (4.5.2).** The kit's corner, end and opening pieces depend on the
  course table and the tooth interlock. The fitted version closed the joints (the biggest visible gap to the reference)
  within one round. The cost is SG5: bed continuity is 0.78-0.85 against the reference's 0.44. Pitfall P59 records
  that a convex coursed frame cannot break its beds. The next step is a power diagram with coursed teeth only at
  module ends.
- **SG10 p90/p50** is 1.59 against 2.04. The reference is a soft daylight AI image with near-white highlights. Wider
  joints, crowns and tone spread moved it only a little (1.54 to 1.59). Flatter crowns (a judge delta) would move it
  the wrong way.
- **SG11:** the owner's mid-grey is kept, as in f2 (pitfall P50).
- **SG3 cap / body height:** 0.75-0.98 against the trace's 1.12, and H6 fails. The trace's right-hand part says caps
  are taller than body stones; the reference's near end shows caps smaller than the body courses. The cap was kept at
  0.34 m until a second trace settles it.
- **One layout seed per module and only the short-block flight**, as in f2 (open decisions 8.5).

### Renders (`renders/f3/`, Cycles headless, denoised)
- **Kit sheets:** `KIT_SHEET_*.png` (13) and `sheet/<piece>_{front,side,top,persp}.png` for all 104 pieces.
- **Sunset assemblies:** `asm_*` and `assembly_*`.
- **Close-ups:** `close_*`, `cu_*` and `match_*`.
- **Gates:** `gate_stone_faces`, `gate_elevation`, `gate_grazing`, `gate_layout_flat` and `GATES_f3.png`.
- **Side by sides:** `sbs_*` in round 0's framings.
- **Scripts:** `render_f3.py`, `compose_f3.py`, `gates_f3.py`, `measure_f3.py`, `catalog_f3.py` and `sim_layout_f3.py`.
