# Taiko set (kit 6, separate from the pavilion): build notes

## Stage BUILD, 2026-09-27 (renders in `renders/r0/`)

**Scope:** SM_DKP_Taiko_Drum, SM_DKP_Taiko_Stand, SM_DKP_Taiko_Stick (one mesh, placed twice). Blender only, headless,
no Unreal. Lock `DojoTaiko` claimed at the start and released at the end of the stage.

**Files:** scripts `Scripts/dojo/props/taiko/{make_taiko_textures.py, build_taiko.py, render_taiko.py}`; blend
`Assets/Dojo/Taiko.blend` (collections Taiko_Drum, Taiko_Stand, Taiko_Stick, Taiko_Layout); FBX
`Exports/DojoKit/Props/taiko/SM_DKP_Taiko_*.fbx` (exported through Scripts/pipeline `export_fbx`); textures
`Exports/DojoKit/Props/taiko/Textures/T_DKP_Taiko_{Lacquer,Hide,Timber,StickWood,Iron}_{BC,N,ORM}.png` (N is DirectX);
`layout_taiko.json`, `measure.json`, `qa_report.json`, `export_report.json`, `textures_report.json` in this folder.

Run order: `py make_taiko_textures.py`, then `blender -b --factory-startup --python build_taiko.py`, then
`blender -b --factory-startup Assets/Dojo/Taiko.blend --python render_taiko.py`.

### Sizes (measured from the sheet, then the prompt's number applied)
Sheet front elevation: 1.8 m silhouette = 203 px, so 112.8 px/m. On it the drum is 117 px tall (1.04 m) and 151-163 px
long (L/D 1.29-1.39), with its bottom 64 px (0.57 m) above the plinth. The rails sit at 0.24 / 0.49 m and the post
tops at 0.78 m. The prompt says "about 1.2 m across", which wins, so every sheet value is scaled by 1.2 / 1.04 = 1.154.

| Item | Built (computed in measure.json) |
|---|---|
| Drum belly diameter | 1.200 m |
| Head face / rolled lip diameter | 1.052 / 1.093 m (WRONG, corrected in f1: the r0 flat face measured 1.022 m, lip 1.093 m) |
| Drum length | 1.550 m (L/D 1.292, the low end of the sheet's range) |
| Tacks | 84 per head, 168 in all, dome diameter 38 mm, zig-zag +-7 mm |
| Ring handles | diamond plate 0.19 m diagonal with 4 rivets and a boss; staple; ring outer diameter 0.167 m; 15 deg above the equator on both sides |
| Drum centre above the stand base | 1.25 m (bottom 0.65 m) |
| Stand | 1.481 x 1.441 x 0.836 m; posts 0.16 m square; rails at 0.215-0.345 and 0.495-0.625; tenons pegged; 8 iron strap plates with 24 bolts |
| Saddle gap to the drum | 3-18 mm (polyline chords are kept outside the drum) |
| Post top below the drum surface | 1.2 mm |
| Stick | 0.78 m long, 62 mm across at the grip and 75 mm at the strike end (sheet 0.75-0.87 m, 75-87 mm) |
| Stick lean | 14.9 / 15.7 deg (WRONG contact numbers, corrected in f1: the measurer found the feet 8.0 / 8.3 mm up and rail gaps 5.3 / 6.6 mm) |
| In the layout | drum top at world +2.85, 0.40 m under the pavilion eave (+3.25) |

### Layout (layout_taiko.json)
The layout follows spec 4.5 and the grey-box SM_DGB_Pavilion. The drum sits at the plinth centre (41, 3) on the plinth
top at +1.0, with rot_z 90. That puts the drum axis north-south, with the ring-handle side facing the courtyard on the
west, where route 7 and the plinth approach come in. A player on the courtyard therefore sees the sheet's front view.
Each instance records its world loc/rot, its stand-local matrix, bbox and Unreal cm.

### Collision (spec 5.2 / 5.3)
| Piece | Pawn | Camera | Visibility | UCX |
|---|---|---|---|---|
| Drum | block, unwalkable (StepUpOn No, slope override Unwalkable) | ignore | block | one convex 16-gon prism |
| Stand | block, unwalkable | ignore | ignore (thin-upright rule) | 12 boxes |
| Stick | ignore (dressing) | ignore | ignore | one 8-gon prism, kept for physics or a pickup |

The drum is not a climb prop, so rule R3 does not apply. Spec 5.2 lists "the drum and its stand" as blocking and
unwalkable.
**Decision to confirm:** the drum blocks Visibility because it is a 1.2 m opaque body. Check it in the grey-box G3
hiding sweep.

### QA and export
`qa_check(require_uv1=True)` gives **0 hard fails** on all three pieces (59 / 68 / 34 checks).
- `uv_no_overlap` on UV0 is waived for the drum and stand. The cause is tiling materials, following the armory
  precedent.
- UV1 is lightmap-packed, stays inside 0-1 and does not overlap.
- Triangles: drum 25,112 (the 168 tacks are about 60 % of that), stand 2,736, stick 544. The drum is over the style
  guide's 2k Nanite threshold, so it is a Nanite piece.
- Measured texel density: drum 11.2, stand 10.6, stick 10.7 px/cm.

### Materials and textures (all own procedural numpy, seamless, power of two)
| Material | Texture set | Kind (for the look pass) |
|---|---|---|
| M_DKP_Taiko_Lacquer | T_DKP_Taiko_Lacquer 2048 / 2 m, with a 0.2 clear coat | UNIQUE |
| M_DKP_Taiko_Hide | T_DKP_Taiko_Hide 2048 / 2 m, albedo capped at 0.80 | UNIQUE |
| M_DKP_Taiko_HideCollar | an MI of Hide, linear tint (0.40, 0.26, 0.15) | UNIQUE |
| M_DKP_Taiko_Timber | T_DKP_Taiko_Timber 2048 / 2 m | GENERIC dark timber |
| M_DKP_Taiko_StickWood | T_DKP_Taiko_StickWood 1024 / 1 m | GENERIC worn pale timber |
| M_DKP_Taiko_Iron | T_DKP_Taiko_Iron 1024 / 1 m, metallic | GENERIC iron |

Every set is 10.24 px/cm, which is 2x the style guide's 5.12. This is deliberate for a hero piece seen up close, and
the look pass can halve it. There are no emissive parts. There is no text, no mark and no crest anywhere.

### Render rounds (all within this stage)
- **t0 / t1 (tests):** the lacquer was too orange and bright, and the tacks were small and sparse (60 x 30 mm). The
  ring was too small (0.13 m). The textures had camo blotches. The top view was greyed by the shadow catcher. The lathe
  UV jumped at every ring, which showed as vertical bands on the barrel.
- **t2:** fixed all of those, with a single V scale, 72 then 84 tacks, the ring at 0.167 m, darker lacquer, rub spots
  removed, and the lights down.
  - Measured on the 3/4 view: lacquer median 84,45,39 against the sheet's 76,37,25; hide 180 against 200.
  - So the lacquer went darker and the studio exposure went to +0.3 EV.
- **r0 (final):** the sticks were made less orange (#654B38), and the close-up and line-up framings were fixed.
- Studio ortho scale (front/side):

  | Sheet | Ortho scale | Density |
  |---|---|---|
  | Drum | 2.80 m | 321 px/m |
  | Stand | 2.72 m | 331 px/m |
  | Stick | 2.475 m | 364 px/m |
  | Set | 2.80 m | 321 px/m |

- Line-up: warm sun at 2500 K and 9.7 deg elevation, sunset gradient sky, kit 2's T_DKG_Gravel (read only).

### Known gaps against the sheet (candidates for a review / fix round)
- **Tacks:** the sheet's row is denser and doubled in places (tacks touching). Ours is a single tidy zig-zag.
- **Hide:** the sheet's collar hide is wrinkled and bumpy with a torn lip. Ours is smooth apart from the ragged edge.
- **Lacquer:** the sheet shows visible crackle and scratches from mid distance. Ours only reads them in close-up.
- **Stand:**
  - The sheet's timber is darker and more split and worn.
  - The sheet has heavier base sills in both directions (a grid).
  - The sheet's cradle is lower. Ours has a tall U-saddle board, which shows in the side view.
- **Stick lean:** the sheet leans the sticks at the far end, by the post. Ours lean on the upper rail between the post
  and the centre. That is where the geometry gives a clean contact.
- **Silhouette:** a primitive mannequin. It is correct at 1.80 m, but blockier than the sheet's figure.


## Stage FIX ROUND f1, 2026-09-27 (renders in `renders/f1/`)

Inputs: the measurer's 7 fixes and the blind judge's 11 ranked deltas (score 6.5, no blockers). Lock `DojoTaiko`
claimed at the start and released at the end. Headless Blender only, no Unreal. Scripts changed:
`make_taiko_textures.py`, `build_taiko.py`, `render_taiko.py`. New scripts: `taiko_uv.py` (the UV layout shared by
the texture and build scripts) and `check_ucx_cover.py`. Every number below is from `measure.json`, `qa_report.json`,
`export_report.json` or `textures_report.json`.

### Measurer fixes
| # | Fix | Result (measured) |
|---|---|---|
| 1 | LOD0-2 on all three pieces, kit 1's pattern | pipeline `decimate_lods(0.5, 0.25)` + `make_lod_group`; UCX renamed `UCX_<base>_LOD0_NN`; each FBX holds a LodGroup (checked in the binary) plus a `.sockets.json` sidecar with the screen sizes. Drum 14,432 / 7,216 / 3,608, stand 2,624 / 1,312 / 655, stick 416 / 208 / 104, all strictly descending; LOD QA 0 hard fails. Collapse left 5 wire edges on the stand's LOD2 (a collapsed rivet), which the export step now deletes |
| 2 | Drum triangles | tacks now 30 triangles each (10 sides, open base sunk 2.5 mm), so 220 tacks = 6,600. The drum is 14,432 (r0 25,112). **Hero-tier budget exception:** the style guide lists the drum as a Hero piece. It is over the 1-5k prop budget because of the 96-sided lathe (the torn collar edge needs the columns) and the 220 tacks. It ships LOD0-2 and is Nanite-eligible (over 2k) |
| 3 | Lathe UV seam | the seam is now at local -Z (under the drum, in the cradle). The wrap is a whole number of tiles: lacquer, collar and lip strips each make 2 tiles around, so the V jump at the seam is exactly 2.0 (no visible step). The stick is fixed too: its texture repeats every 0.25 m around, and one wrap is one tile |
| 4 | Sticks grounded and touching | a new solver uses the real meshes, and the tilt is fixed. The stick slides along X until the two-way sampled gap is 0.5 mm. The samples are the stick's surface grid against the obstacle BVH, plus the stand/drum vertices and edges, clipped near the stick, against the stick BVH, at 1 mm. The lowest vertex sits 0.5 mm above the plinth. Result: both feet **0.50 mm** above the plinth; contact gap **0.50 mm** to the stand (the folded iron strap / rail end) for both |
| 5 | Iron metallic | a hard rust mask: rust 0.0 (2.3 % of texels), bare/oxide iron 0.96-1.0. Partial-metal texels (0.05-0.95): **0.0 %** |
| 6 | Stand UCX | 20 hulls: 2 sills, 4 stop blocks, 2 x 3 cradle hulls (the centre follows the saddle arc; the 2 shoulders include the wedge blocks), 4 posts including the strap legs, 4 rails including the straps. `check_ucx_cover.py`: **0 of 1,688** stand vertices outside the hulls by more than 1 mm (the worst is 0.5 mm). Drum and stick: 0 outside |
| 7 | Notes corrected | the rows above are marked; the f1 numbers are below |

### Judge deltas addressed
- **Hide collar:** has its own strip texture `T_DKP_Taiko_Collar` (256 x 2048: U across the band from the torn edge,
  V around). It is the head's cream about 13 % darker, dirtier toward the edge, with fibre tatter at the edge, folds
  across the band and bumps. Geometry: the torn edge is irregular (harmonics 2-40, per-vertex jitter and 5 torn
  notches per head; edge x 0.600-0.628). The lap edge is lifted 0-3 mm, and three fold rings have radial wrinkles.
- **Lacquer:**
  - Hue toward red-brown. Iteration: #561F0D rendered 98,47,36 on the front view against the sheet's 72,34,21, so
    the colour went to #3F1607.
  - Satin finish: no clear coat, roughness mean 0.40.
  - Craquelure: a periodic anisotropic Voronoi, 38 x 110 cells per 2 m tile, about 5 x 1.8 cm, in the normal and
    roughness.
  - Wear: edge wear baked at the collar U columns, and a worn, warmer band on the bulge. The round blotches are
    gone.
- **Stand timber:**
  - About 35 % darker (texture mean 55,42,32 against r0 69,52,39).
  - Long, deep checking cracks (150 stamped lines, 3.5 mm deep in the normal), lighter weathered raised grain and
    crack lips, dirt.
  - New `T_DKP_Taiko_TimberEnd` end grain: rings, a few radial checks and splits. It goes on every face across the
    grain: post tops, sill, rail and wedge ends. This fixes the stretched side grain on the caps.
- **Joint hardware:** the flat square plates and hex bolts are gone. Each rail end now has an iron L-strap folded
  down the post's outer face, along the rail top and over the rail's end face. A strap runs along the rail's outer
  face, folded onto the post's inner face. The heads are round domed rivets and nails (6 sides, 18 triangles each).
- **Cap blocks and pegs:** the top pegs and pins are removed. The crossbeam ends are now chunky kusabi wedge blocks:
  0.22 m tall (the beam is 0.15 m), tapered 80 % to 100 % toward the top, rough (6 mm per-corner jitter), with end
  grain on top. Sills are now 0.22 x 0.18 (were 0.18 x 0.15), stop blocks 0.25 x 0.14 x 0.13, posts 0.18 (were
  0.16), rails 0.13 x 0.15 (were 0.11 x 0.13).
- **Stick shape:** 1.5x thicker: 84 mm at the grip, 92 mm at the strike end, L/D 9.3 / 8.5 (sheet 8-9). The ends are
  flat faces with an 8 mm rounded edge, and there is a slight taper toward the grip.
- **Stick material:** a darker, less saturated brown (texture mean 71,55,42 against r0 #654B38), more grime, pores,
  and a darker, smoother hand-wear band baked at the grip end (x 0-0.26 m).
- **Tacks:**
  - 110 per head, 1.3x more (was 84).
  - Zig-zag +-16 mm, so neighbours nearly touch.
  - Jitter: position +-12 % of the pitch around and +-2.5 mm along the axis, size 0.92-1.08, random rotation, tilt
    +-4 deg.
  - Domes 39-46 mm across, +12 %.
- **Hide heads:**
  - Mottle, fibre, specks and a dirty centre.
  - A darker grimy rim band (0.39-0.485 m from the centre) and a dark rolled lip strip.
  - Each head is its own UV disc: centres (0.25, 0.25) and (0.25, 0.75).
  - The lip is now a real rolled bead: a 19 mm radius roll from the collar over to the flat face.
- **Sticks layout:**
  - Both sticks stand at the stand's front-right end (+X/-Y, the right end of the sheet's front view) and lean 15.0
    and 18.5 deg toward -X onto the upper front rail's strapped end.
  - Feet at stand-local x 0.97 / 1.01 (world y 3.97 / 4.01, inside the plinth's y 1-5).
- **Ring handles:** each ring now hangs in a vertical plane against the belly. Its top threads the staple, so the
  plate sits 8.67 deg above the equator. Minimum gap to the barrel: 2.1 mm. The ring tube is 1.3x thicker, 24.8 mm
  (outer diameter 0.173 m).

### Measured (f1)
| Item | Value |
|---|---|
| Drum belly / flat head face / rolled-lip outer diameter | 1.200 / **1.010** / **1.094** m |
| Drum length | 1.554 m (L/D 1.295) |
| Drum centre / bottom above the stand base | 1.25 / 0.65 m; drum top world +2.85, 0.40 m under the eave |
| Stand | 1.539 x 1.441 x 0.830 m; saddle gap 3-18 mm; post tops 4 mm under the drum |
| Stick | 0.78 m, 84 / 92 mm |
| Triangles LOD0 | drum 14,432, stand 2,624, stick 416 |
| QA | `qa_check(require_uv1=True)` **0 hard fails** on all three and on every LOD. `uv_no_overlap` on UV0 is waived for the drum and stand (tiling materials, armory precedent) |

The texel density `qa_check` prints (drum 15.5, stand 14.1, stick 19.1 px/cm) assumes one square texture at the
largest size. The real sets are 10.24 px/cm along U. Around the drum the 2-tile wrap gives 10.9 on the lacquer and
11.9 on the collar. The stick set is 1024 x 256 over 1.0 x 0.25 m, which gives 10.2-11.8 around.

### Materials (look-pass classification)
| Material | Set | Kind |
|---|---|---|
| M_DKP_Taiko_Lacquer | Lacquer 2048, 2 m | UNIQUE (collar wear baked at the drum's U) |
| M_DKP_Taiko_Hide | Hide 2048, 2 m | UNIQUE (head discs laid out per `taiko_uv`) |
| M_DKP_Taiko_HideCollar | Collar 256 x 2048 | UNIQUE (strip) |
| M_DKP_Taiko_Timber | Timber 2048, 2 m | GENERIC dark timber |
| M_DKP_Taiko_TimberEnd | TimberEnd 512, 0.5 m | GENERIC dark timber end grain (new) |
| M_DKP_Taiko_StickWood | StickWood 1024 x 256 | GENERIC hardwood (the grip wear is baked at the stick's U) |
| M_DKP_Taiko_Iron | Iron 1024, 1 m | GENERIC iron, no partial metallic |

There are no emissive parts. There is no text, mark or crest anywhere.

### Renders (f1)
The folder `renders/f1/` holds:
- `sheet_{Drum,Stand,Stick,Set}.png` (the Set front / side ortho scale is now 3.11 m, 290 px/m, because the sticks
  widen it).
- The close-ups `closeup_hide_tacks_ring.png`, `closeup_stand_joint.png` (the -X/-Y joint), `closeup_sticks.png`
  and the new `closeup_sticks_leaning.png`.
- `lineup_sunset.png`.
- `sbs_*.png` against the r0 reference crops, which were copied to `f1/refcrops`.

`render_report.json` now merges partial re-renders rather than overwriting.

### Open after f1
- **Drum:** the collar's torn lip is still tidier and less lifted than the sheet's. The tacks are 10-sided and read
  slightly faceted in the close-up.
- **Stand:**
  - The side grain still reads a little uniform and procedural at close range compared with the sheet's deeply
    carved timber.
  - The sheet's grid of heavy base sills in both directions is not modelled (sills run along Y only).
  - The U-saddle cradle is unchanged.
- **Sticks:**
  - In the Set front view the second stick is mostly behind the first (the feet are 3.4 cm apart in X).
  - Their colour is a little greyer than the sheet's warm brown.
- **Carried over:**
  - The drum's Visibility-blocking collision is still to be confirmed in the grey-box G3 sweep.
  - The pavilion's west-facing front is assumed.
  - The silhouette is still a primitive mannequin.


## 2026-09-28, PROP MATERIAL + SHAPE PASS r2 (group A; renders in `renders/r2/`)

Lock `DojoTaiko` claimed at the start and released at the end. Headless Blender only, no Unreal, no commit.
Scripts changed: `make_taiko_textures.py`, `build_taiko.py`, `render_taiko.py`. Every number is from `measure.json`,
`qa_report.json`, `export_report.json`, `textures_report.json` or a pixel median of the r2 renders.

### Materials: the shared library (`Scripts/dojo/materials`, v1.0.0)
| Slot | r2 material | Source |
|---|---|---|
| Stand faces / ends | `M_DJ_TimberDark` / `M_DJ_TimberDarkEnd` | library (4 m / 2 m tiles), UVs by the library's `grain_uv` |
| Sticks | `M_DJ_TimberAged` | library (the lighter warm wood; mirrored-ramp V round the stick, no seam) |
| Straps, rivets, tacks, rings | `M_DJ_Iron` | library (2 m tile) |
| Drum body | `M_DKP_Taiko_Lacquer` | library node graph (`make_material`, DJ_Wear_v1) + own maps, see below |
| Heads / collar | `M_DKP_Taiko_Hide` / `M_DKP_Taiko_HideCollar` | library node graph + own maps (the library has no hide) |

- Weathering: the library's `bake_wear` 'Wear' corner colour on all three meshes (exported in the FBX,
  LayerElementColor present). Two measured fixes on top, both keeping the library's channel meaning:
  - `regrime`: R re-sampled per face corner 30 % in from the corner (the library samples at the vertex; vertices
    buried inside an interpenetrating member darkened whole faces);
  - the stick's 16 narrow side facets were all flagged as bevels (96 % of the area): G kept only on the end
    round-overs.
- Tone band: the library timber sets carry a strong large-scale band across V (TimberDark row means: v 0.03-0.2 =
  12-15, v 0.27-0.51 = 43-67, v 0.52-0.97 = 95-124), so random member offsets gave black members next to orange ones.
  `pin_band_v` shifts every member rigidly into v 0.27-0.51 (stand) and v 0.745-0.83 of TimberAged (sticks): 20
  stand islands, none wider than the band.
- **Lacquer is a variant, not `M_DJ_Lacquer`.** The library set has the judged defects: low-frequency mottle
  (large-scale luminance std 9.7 vs 3.4 now = the water-spot blotches) and roughness 0.33 (wet). The taiko set is
  built from the library generator's own primitives (pnoise, voronoi, _dashes, gblur): warm red-brown `#391306`,
  satin (roughness mean 0.50), craquelure network + 2 mm lengthwise cracks, pale scratches, collar-edge wear, a
  worn lighter band on the bulge. Unreal: MI of M_DJ_Lib_Opaque, UseWear on, TileM (2, 2), no clear coat.
- Worn highlights on the bulge: Wear G set patchily across the belly (1,824 of 6,912 lacquer corners over 0.5), so
  the library wear maths lifts it by up to +17 % in broken patches.
- Hide collar: tan `#BF9A70` (sheet collar 188,150,115 vs head 201,176,150), about 14 % darker than the head, grime
  smudges over the band plus edge grime.
- Retired: `T_DKP_Taiko_{Timber,TimberEnd,StickWood,Iron}_*` moved to `retired_f1_textures/` (not deleted).
  Shipped maps now: `T_DKP_Taiko_{Lacquer,Hide,Collar}_{BC,N,ORM}`.

### Shape fixes (judges / measurers)
| Item | r2 |
|---|---|
| Rail-end iron | the L-plates are gone: a 6 mm iron U-strap wraps each protruding rail end (front + back straps joined by an end plate) from the post's outer face to the rail tip, full rail height; a big bolt and 3 nails on the outer face, a bolt on the end plate. The top stays wood (t3's closed box read as a black cube) |
| Collar lap edge | 144 lathe columns (was 96); torn edge harmonics 2-60 (12 mm) + 9 V-tears per head (8-14 mm, 2-4 columns) + 4 proud tabs; lap edge lifted 1.5-7 mm; a new ring 10 mm inside the edge follows it with small radiating folds (1.8 mm); edge x range 0.598-0.632 m |
| Tacks | 128 per head (was 110), zig-zag +-15.5 mm, around-jitter +-14 % of the pitch (neighbours bunch into doubled pairs), domes 38-45 mm; 256 in all |
| Sticks | both stand beside the far (+X/-Y) post, just outboard of the sill's stop block. Stick 0 leans back (+Y) 11 deg onto the front of the upper rail's iron wrap (foot at stand-local 0.745, -0.678); stick 1 leans 14 deg onto the wrap's end plate (foot 0.926, -0.436). Both: foot 0.5 mm above the plinth, contact gap 0.5 mm, solved on the real meshes (BVH) |
| LODs | kept: drum 19,256 / 9,628 / 4,814; stand 2,096 / 1,047 / 523; stick 416 / 208 / 104 (all strictly descending, LOD QA 0 hard fails). The drum is Nanite-eligible (over 2k) |

Unchanged: sizes (belly 1.200, head face 1.010, lip 1.094, length 1.554, stand 1.547 x 1.441 x 0.830), pivots,
collision classes, the drum's 16-gon hull, the stand's 20 hulls (rail hulls now reach 8 mm under the rail for the
strap), the stick hull. `check_ucx_cover.py`: 0 vertices outside the hulls by more than 1 mm (stand worst 0.5 mm).

### QA and export
`qa_check(require_uv1=True)`: **0 hard fails** on all three and every LOD (`uv_no_overlap` on UV0 waived as before,
tiling materials). FBX re-exported through `Scripts/pipeline` with LodGroups and sidecars.

### Renders (`renders/r2/`, Cycles, OIDN denoised, 96 samples)
`sheet_{Drum,Stand,Stick,Set}.png` (front | side over top | 3/4, grey background, 1.8 m silhouette),
`closeup_hide_tacks_ring.png`, `closeup_stand_joint.png`, `closeup_sticks.png`, `closeup_sticks_leaning.png`,
`lineup_sunset.png`, the new `context_sunset.png` (the set on a 1.0 m granite plinth stand-in, library
`M_DJ_Granite`, seen from the courtyard at eye height) and `sbs_*.png` (reference | ours) for every one of them.

Measured on the renders (median sRGB, front view):
| Surface | Ours r2 | Sheet |
|---|---|---|
| Lacquer | 86,54,47 (hue 10.8) | 76,37,23 (hue 15.8); f1 t2 106,61,50 |
| Stand rail | 61,45,37 | 90,61,41 |
| Head face (side view) | 181,161,138 | 201,176,150 |

### Open after r2
- Lacquer renders about 12 % lighter and less saturated than the sheet under the grey studio (the satin sheen
  greys it); the craquelure reads in close-ups but is faint at sheet distance.
- The library timber is about 30 % darker than the sheet's stand once pinned to its mid band (the only band wide
  enough for these members). A library-side fix (flatten the V tone band) would let every kit use the calibrated
  mean; flagged for the library owner.
- Iron reads near black in the studio (library Iron, metallic 0.85-1.0); the sheet's straps show a lighter grey
  sheen.
- Still open from f1: the sheet's grid of base sills and the lower cradle are not modelled.


## 2026-09-28, ROUND 3 LOOK PASS (props track; renders in `../round3/taiko/`)

Lock `DojoTaiko` claimed at the start and released at the end. Headless Blender only, no Unreal, no DojoLab write, no
commit. The material library was not edited. Scripts changed: `taiko_uv.py`, `make_taiko_textures.py`,
`build_taiko.py`. Inputs: the round-2 props-A judge (6.5): blockers 1 (sticks), 2 (stand iron), 4 (lacquer finish).

### Sticks (judge blocker 1 / delta 1)
- A lathe-turned stick: superellipse DOMED ends (dome height 0.62 x the end radius, exponent 2.4: a full round end
  with a soft shoulder, as the sheet's close-up), 20 sides, a 13 % taper toward the grip (80 / 92 mm), 0.78 m long.
  No flat end caps. LOD0 840 tris.
- Material: a smooth, oiled, mid-brown turned wood with soft low-contrast grain, soft darker flecks, darker end grain
  with faint rings on the domes and a soft hand-polish band at the grip, roughness about 0.40.
- **No new material slot**: the wood is a periodic patch of the HIDE atlas (`T_DKP_Taiko_Hide_*`, columns 1168-1464,
  rows 1075-1956; the hide tile's columns U 0.54-0.755 were unused) and the stick uses `M_DKP_Taiko_Hide`. The
  showcase composer's material recipes are fixed per slot (`compose_showcase.py` raises on an unknown slot), so a new
  slot would have broken the Unreal import. `M_DJ_TimberAged` is no longer on the stick.
- UV (the pinwheel fix): U = one whole wrap round the stick over the periodic patch (no seam step), V = arc length
  along the turned profile from the grip pole. The domes continue the side grain into the pole; the patch has its
  own wrapping normals.
- Measured on the close-up (median sRGB): t1 163,127,103, then t2 **139,106,85** against the sheet's close-up
  127,96,73.
- Poses re-solved on the new mesh (BVH, 0.5 mm): stick 0 foot (0.745, -0.711), stick 1 foot (0.909, -0.434). Both
  feet are 0.5 mm above the plinth, with a 0.5 mm contact gap to the stand.

### Stand iron (judge blocker 2 / delta 2)
- The r2 6 mm U-wraps round the rail ends ('black cubes') are gone.
- The UPPER rails now lap flush on the posts' outer faces, as in the sheet's joint close-up. A 4 mm FLAT strap plate
  is nailed flush across each joint, from just outside the cradle wedge (x 0.585) over the post corner to 12 mm
  short of the rail tip. Each plate carries 4 nail heads and 1 bolt.
- The LOWER rails stay centred through the posts: their outer face has to clear the sill stop block, which sits 3 cm
  outside. Their plate covers only the protruding end, with 2 nails and 1 bolt.
- The rail end grain shows. The iron is still library `M_DJ_Iron`, which reads dark in the studio; that is the
  library's judged set.
- Stand LOD0 1,712 tris (r2 2,096). 20 UCX hulls; the rail hulls follow the flush rails. `check_ucx_cover.py`:
  0 of 1,048 vertices outside by more than 1 mm (worst 0.5 mm).

### Lacquer (judge blocker 4 / delta 3)
- Roughness mean **0.288** (r2 about 0.5) between the cracks. The stave streaks are at 35 % and the pale scratches at
  30 %. The craquelure is kept.
- The sheet's glossy highlight band now reads on the drum top (`sheet_Set.png`).

### QA / export
- `qa_check(require_uv1=True)`: 0 hard fails on all three pieces and every LOD (UV0 overlap waived on the drum and
  stand as before).
- LOD0 / 1 / 2 tris: drum 19,256 / 9,628 / 4,814; stand 1,712 / 856 / 428; stick 840 / 420 / 210.
- FBX re-exported through Scripts/pipeline. `layout_taiko.json` rewritten (new stick poses).
- Drum sizes, pivots, collision classes and the drum hull are unchanged.

### Renders (`WorkFiles/dojo/build/props/round3/taiko/`)
`sheet_Set.png`, `closeup_sticks.png`, `closeup_sticks_leaning.png`, `closeup_stand_joint.png`,
`closeup_hide_tacks_ring.png`, `lineup_sunset.png`, `context_sunset.png`, and `sbs_r3_{sticks,joint,set_34}.png`
(reference | ours).

### Open
- For the showcase import: re-import `T_DKP_Taiko_{Lacquer,Hide}_*`. The stick's slot changed to `M_DKP_Taiko_Hide`,
  which is already a recipe.
- Still open from f1: the sheet's base-sill grid and lower cradle.
- The iron reads near-black. A lighter, rusty-edged iron would need the library.
