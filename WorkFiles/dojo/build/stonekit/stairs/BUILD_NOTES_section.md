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
