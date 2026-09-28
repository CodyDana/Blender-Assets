# Snow Flower sword: revision-3 audit (v4 planning)

**Date:** 2026-09-26. **Role:** sword auditor (acting as `claude`, lock "SnowFlower" untouched).
**Subject:** revision 3 as built by another AI agent: `Assets/SnowFlower/SnowFlower_Master.blend` (bake source),
`Assets/SnowFlower/SnowFlower_Game.blend`, `Exports/SnowFlower/` (FBX/GLB LOD0-2, 32 PNGs).
**Reference:** `References/SnowFlower/SnowFlower_user_reference.png` (front, side and back views plus guard, blade and pommel crops).
**Scope:** read-only review. Nothing in revision 3 was modified. All evidence is in `WorkFiles/SnowFlower/v4/audit/`.

## 0. Verdict

Revision 3 is a detailed sculpture of the right *idea*. At sheet scale its overall length, the guard and grip landmark
heights, and the mid and lower blade width match the reference to within about 1-3 %. But:

* **Three parts of the design are wrong in shape, not just in detail.** (a) The **pommel** is a coin-like wheel on a thin
  neck, with its axis front-to-back. The reference shows an **end cap** whose flower medallion sits on the end face.
  (b) The **guard** is 12 % too wide and has almost no front-to-back depth: at the wing line it is 8 mm deep in side
  view, where the reference is about 60 mm. (c) The **grip** is a thin 31 x 25 mm oval. The reference grip is nearly
  round (about 35 x 33 mm) and flares toward the guard.
* **The blade finish misses the look of the reference.** It is a flat mid-grey slab with a narrow edge strip. The
  reference has a blue-black mottled field, a wide mirror bevel, a recessed channel that holds the relief, and a
  bright wavy ribbon down the lower half.
* **It is not a game asset.** LOD0 has 456,024 triangles, 9 to 23 times the 20-50k hero-weapon budget. It has eight
  material slots, and its normal maps are baked from the mesh itself, so they hold no ornament detail and nothing
  would survive a reduction. AO is a constant 1. The normals are OpenGL. There is no UV1 and no sockets. It never
  went through `Scripts/pipeline/`, and it was never imported into Unreal. The pipeline gate (`qa_check`) fails on
  6 counts (section 3).

**Recommendation:** keep the master as the high-poly bake source. Copy it into v4, fix the pommel, guard, grip, blade
profile and blade finish there, and remove the tassel. Then build a new low-poly game mesh of about 35-45k
triangles, baked from that high-poly, and ship it through the pipeline. Do not try to decimate the revision-3 game
mesh.

## 1. Evidence and method

| File (all under `WorkFiles/SnowFlower/v4/audit/`) | What it is |
|---|---|
| `compare_views_ref_rev3_overlay.png` | Front, side and back: reference crop, then the rev-3 **shipped FBX** rendered with its own baked textures, then a silhouette overlay (red = reference only, blue = rev-3 only, grey = both). Same scale: both are 1,206 px from pommel to tip, so 1 px = 1.042 mm at rev-3 size |
| `compare_hilt_ref_rev3_4x.png` | Hilt front and side, reference pixels at 4x beside rev-3 at the same 4x scale |
| `compare_blade_ref_rev3_2x.png` | Blade front at 2x, upper and lower halves, reference beside rev-3 |
| `renders/rev3_*.png` | Rev-3 FBX renders: 1x views, 4x hilt views, and perspective guard/pommel/blade details |
| `ref_crop_guard_detail.png`, `ref_crop_pommel_detail.png` | The sheet's detail crops, for side-by-side reading |
| `compare_profiles.json`, `ref_measure.json` | Per-row silhouette widths, taken from the run containing the blade axis (this excludes the tassel wherever a gap exists) |
| `rev3_master_inspect.json`, `rev3_game_inspect.json` | Per-object triangles, bounds, materials, UV layers, images and colourspaces |
| `rev3_uv_permaterial.json` | Per-material texel density, UV fill and overlap on the game mesh |
| `rev3_blade_envelope.json` | Blade, relief and guard envelope (handed to the sheath) |
| `qa_check_rev3_game.json` | `Scripts/pipeline/qa_check.py` run on `SnowFlower_Game.blend` (read-only gate) |
| `*.py` | The scripts that produced all of the above (headless Blender 5.2, factory startup, nothing saved) |

Renders were made in Cycles from `Exports/SnowFlower/SM_SnowFlower.fbx` (SHA-256 `32f0e2c7...`, matching
`export_report.json`), with the textures listed in `material_manifest.json`, under a neutral studio environment.
Value and colour comparisons are therefore qualitative: the sheet's lighting cannot be recovered. Shape comparisons
are measured.

## 2. Design deviations from the reference

Widths are in mm at rev-3 size (overall length 1,256 mm). "Ref" means the sheet silhouette scaled to the same overall length.

### 2.1 Proportions and landmarks: mostly right

| Landmark | Ref | Rev 3 | Note |
|---|---:|---:|---|
| Overall length (pommel top to tip) | 1,256 (by definition) | 1,253-1,256 | Match. The sheet has no absolute scale; 1.256 m is rev-3's choice (section 5) |
| Guard band (sheet rows) | 272-335 | 270-330 | Match |
| Guard width, front | **~111** | **124** | Rev 3 is 12 % too wide; its wings flare into flat bat shapes |
| Guard depth, side view | **56-62** | **8-33** (8 at the wing line) | **Wrong.** Rev-3 wings and leaves are thin plates |
| Grip width, front | 34-35 near the pommel, flaring to 40-42 at the collar | 31.3, constant | 10-25 % thin, no flare |
| Grip width, side | 32-33, flaring to 36-40 | 25.0, constant | 25-35 % thin. The reference grip is nearly round; rev 3 is a flat oval |
| Pommel, side view | ~35 (a round cap) | 23 (a disc seen edge-on) | Shape misread (2.5) |
| Blade width 5-15 % below guard | 50-53 | 45.8 | Rev 3 is 10-13 % narrow at the base |
| Blade width, mid | 45-47 | 44.8 | Match |
| Blade width at 70-85 % | 43 -> 40 | 43.8 -> 40.6 | Match |
| Blade thickness, first 15 % (side) | 24-31 (the guard's lower leaves wrap the blade base) | 8-10 | The reference pendant leaves cup the blade front and back; rev 3's pendant lies flat |
| Blade thickness, mid (side) | 5-6, 10-15 at blossoms | 6, 6-13 at relief | Match |

### 2.2 Blade curve and width

* Both blades are straight, and the tip sweeps toward the edge side (+X in the master). The **reference sweep starts
  earlier**: its centreline is already off-axis by about 3.5 px at row 860 (about 60 % of the blade) and 6 px at row
  940. Rev 3 stays on-axis until about row 940 (about 75 %) and then bends sharply. At row 1100 the reference
  centreline is about 16 px off-axis, against 11 px on rev 3. So rev 3 has a short, late hook where the sheet shows a
  longer, gentler belly.
* **Distal taper is missing.** The reference narrows from about 52 mm at the base to about 40 mm at 85 %. Rev 3 runs
  nearly parallel, 46 mm to 41 mm.

### 2.3 Guard (`compare_hilt_ref_rev3_4x.png`, `rev3_guard_detail.png` vs `ref_crop_guard_detail.png`)

* **Layout is right; form is not.** Both have a large five-petal central blossom, pointed side wings, a chevron crown
  under the collar and a lower pendant. But the reference guard is a chunky, cupped lotus of **pointed almond leaves**
  radiating like a star: up-left, up-right, left, right and down. They have thick, bevelled silver rims and dark
  inset panels, and they tilt toward the viewer. The wing ends turn forward into bold, angular **hooked points**.
* Rev 3 has two **rounded, bulbous lower lobes** where the reference has pointed leaves. Its wings are flat plates
  outlined with **thin wire rims**, filled with thin wire thorns. The central blossom is slightly small relative to
  the guard (about 32 mm across on a 124 mm guard).
* **Depth** is the largest miss. In the reference side view the guard reads as a 60 mm deep sculpted block, and the
  lower leaves hang onto the blade base front and back. Rev 3 reads as a thin cross-plate (8 mm at the wing line).

### 2.4 Grip wrap

* The reference wrap is **near-black tight cord**: fine texture, many small diamond windows (about 11 crossings over
  the grip), and a nearly round cross-section flaring toward the guard. Rev 3 has **wide, smooth, flat bands** (about
  7 crossings) on a flat oval. It reads as grey leather strips under neutral light, and the base colour is not the
  problem: the wide smooth specular is.
* **Grip ornament.** The reference has substantial silver branches climbing the wrap, with two clusters of fairly
  large blossoms (upper third and just above the collar). Rev 3 has thin wire twigs and small flowers in two sparse
  spots.
* **Collar (ferrule).** The reference collar is a flared silver fitting, about 40 mm, with V-chevron plates front and
  back that seat into the guard crown. Rev 3's collar is a 35 mm dark cylinder with a thorn-engraved band and a small
  chevron.

### 2.5 Pommel (`rev3_pommel_detail.png` vs `ref_crop_pommel_detail.png`): shape misread

* Reference: a squat **end cap** on the end of the grip, with its axis along the grip. It is about 36-40 mm across
  and about 25 mm tall. A thick silver bezel frames a **recessed dark medallion on the end face** holding a silver
  five-petal blossom and vine scrollwork. The side band carries pierced vine scrollwork, and the cap sits directly on
  the wrap with a silver ring. The front view shows the medallion only because the sheet is drawn slightly from above.
* Rev 3 (`QA_NOTES.md`: "one rounded housing with its axis along Blender Y") is a **wheel standing on edge**, with its
  flowers on the front and back faces, on a narrow 25 mm neck above a separate collar. It looks like a coin on a stalk
  from the front and a 23 mm disc from the side. The medallion *parts* are good (flower, concentric rims, thorn
  wreath); only their orientation and the housing are wrong.

### 2.6 Blade relief and finish (`compare_blade_ref_rev3_2x.png`, `rev3_blade_detail.png`)

* **Surface.** The reference blade is a deep **blue-black, mottled, watery** field (a damascus or etched look). A
  **wide mirror-polished edge bevel** takes about 25-30 % of the width, and a narrow bright spine flat runs on the other
  side. Rev 3 is uniform mid-grey with faint lengthwise tool marks, a narrow edge strip, and no mottling.
* **Channel.** In the reference, the relief sits in a **recessed dark channel** between the bevels, and the branches
  stand out in high relief. In rev 3 the relief sits on a flat face.
* **Wavy ribbon.** From about 45 % of the blade to the tip, the reference shows a **bright wavy ribbon** (hamon-like)
  winding down the blade, with the vine following it. Rev 3 has no ribbon.
* **Composition.** The reference has **dense clusters of large blossoms** (about 12-15 mm) from the guard to about
  40 % of the blade, then a thick trunk and sparse sprigs lower down. Rev 3 runs one thin vine the full length with
  small, sparse clusters. Its trunk reads as a pale tube at a distance.
* **What is good.** Rev 3's individual blossoms (cupped petals, rims, engraving, stamens, filaments) are the best part
  of the model and read correctly in close-up.

### 2.7 Things the reference does not show

The sheet shows no scabbard, no hand position, and no pommel underside. The inferred hidden geometry in rev 3 is
acceptable. The v4 fixes above add nothing the sheet does not show.

## 3. Game readiness: what is missing or wrong

| Area | Rev-3 state (measured) | Project standard | Consequence |
|---|---|---|---|
| **Budget** | LOD0 **456,024** triangles (floral relief 194,584; grip 106,044; tassel 71,880; pommel 46,320; guard 36,840; blade 356). LOD1 181,995, LOD2 118,428 | Hero weapon 20-50k (`ASSET_GUIDELINES.md` 2) | `qa_check` triangle_budget **FAIL**. Even LOD2 is more than twice the LOD0 budget |
| **Detail transfer** | Normals baked with `use_selected_to_active=False`: each map records only the procedural micro-bump of the mesh itself (`export_snow_flower.py`) | Bake the ornament high -> low (Cycles, selected-to-active, cage, Extend margin) | No ornament lives in any map. Any reduction deletes the detail outright |
| **LODs** | LOD1/LOD2 are *separate FBX files* made by a blind whole-mesh Decimate (0.40 / 0.28). No LodGroup | Authored LODs in one LodGroup FBX, strictly descending, Import Mesh LODs ON | Unreal imports one LOD unless each is added by hand |
| **Collision naming** | `UCX_SM_SnowFlower_00/01/02` are not parented, in a flat FBX whose node is `SM_SnowFlower`. That name is correct *for this flat file*, but `qa_check` ucx_present **FAILS** because they are not children | With a LodGroup the node is `SM_SnowFlower_LOD0`, so the hulls must be `UCX_SM_SnowFlower_LOD0_NN` (measured rule) | Once LODs are done properly, keeping the rev-3 names gives *convex count 0* in Unreal with no error |
| **Collision shape** | Hull 00 is the blade (z 0.19-1.085); 01 a guard box 130 x 41 x 68 mm; 02 a 12-sided cylinder over grip and pommel. z 0.171-0.190 is uncovered. The curved tip is filled in by a single convex hull | Tight hulls with LOD0 inside them | Small gap and slight overfill. Fine for a weapon trace, but rebuild |
| **Normal convention** | OpenGL (+Y), "flip green in Unreal" (`material_manifest.json`) | **DirectX on disk**, flip OFF in Unreal | Wrong convention for the pack |
| **Tangent space** | Exported with `use_tspace=True` via raw `bpy.ops.export_scene.fbx` | Tangent Space OFF (Unreal recomputes MikkTSpace); export only through `Scripts/pipeline/export_fbx.py` | Pipeline bypassed |
| **Materials** | **8 slots** (BlackenedSteel, BladeEdge, BranchSteel, Recess, Inlay, Silver, Leather, Silk). 32 PNGs (BC, N, Roughness, ORM each). `Recess` metallic 0.85 | A few slots joining the pack masters (`M_Steel_Master`, `M_Fabric_Master`, MI with colour option). Metals 0.95-1.0 | 8 draw calls on a hand-held prop. Partial metallic breaks the metal rule. Roughness is shipped twice (standalone and ORM.G) |
| **ORM.R (AO)** | Constant 1.0 (`np.ones`, "no baked AO") | ORM.R is baked AO; a constant is listed as a bug | Ornament recesses will read flat |
| **UV0** | One UV map; each material has its own 0-1 space. Fill of each texture: Silk 0.6 %, Silver 0.7 %, BranchSteel 1.7 %, BladeEdge 2.2 %, Inlay 5.7 %, BlackenedSteel 8.3 %, Recess 12 %, Leather 59 %. Texel density ranges from **3.6 px/cm (Silk) and 6.1 (Silver) up to 76.5 (Leather)** | Consistent density, one atlas, 16 px padding at 2K | `qa_check` uv_no_overlap **FAIL** (697,198 pairs; materials stacked in one 0-1 space) and texel_density **FAIL**. Most texture memory is empty fill colour, and the silver ornament is starved |
| **UV1** | Missing | UV1 strictly in 0-1 with no overlap (or Generate Lightmap UVs ON) | `qa_check` uv1_present **FAIL** |
| **Topology** | 3,282 coincident vertex pairs. 160 open boundary edges (informational) | No coincident verts | `qa_check` no_coincident_vertices **FAIL** |
| **Sockets** | The master has Empties `Socket_MainHand` (0,0,0), `Socket_OffHand` (0,0,-0.07), `Socket_BladeTip`, `Socket_TasselRoot`: wrong names, not exported (`object_types={'MESH'}`), and deleted from the game blend. No sheath or holster reference | `SOCKET_<node>_<name>` Empties, written to the `.sockets.json` sidecar and recreated with `ue_import_sockets.py` (FBX sockets die in a LodGroup; flat-file sockets import at scale 100) | No hand attach and no sheath snap |
| **Scale and pivot** | Metric, unit scale 1.0, transforms applied (pass). Origin at z = 0, where the grip spans -0.141..0.101, so the origin is 20 mm guard-side of centre, not a hand point. Blade +Z, edge +X, front -Y | Pivot at the grip point | Acceptable. v4 should put the pivot at the primary hand point and publish the axis convention (section 5) |
| **Engine verification** | None ("gameplay_tested": false). Never imported into Unreal | Second fresh Unreal process on the exact exported bytes | Nothing is engine-verified |
| **Naming/IP** | Asset names are clean (`SnowFlower`, no deny-list hit). The reference sheet is titled with a franchise character's name (section 7) | Deny list in `qa_check` | Fine as long as no name ever carries the sheet's title |

`qa_check` result on `SnowFlower_Game.blend` (object `SM_SnowFlower`, budget 50,000, texel 10.24, `--require-uv1`):
**6 failures in 114 checks**: triangle_budget, no_coincident_vertices, texel_density, uv_no_overlap, uv1_present,
ucx_present. Transforms, unit scale, n-gons, non-manifold edges, degenerate faces, power-of-two maps and colourspaces pass.

**A note on the texel target.** The house number 10.24 px/cm would put the entire sword in about a 512 map. It cannot
hold petal engraving, which has 0.3-0.5 mm features. v4 should record a deliberate hero-relief target of about
40-80 px/cm on the metal atlas, and pass it to `qa_check --texel`. The blade is 94 cm long, so at 80 px/cm it must be
split into strips; at 40 px/cm it fits.

## 4. Tassel removal (decided: no tassel on the sword or the sheath)

What it involves:

* **Geometry.** Delete collection `06_Tassel` from the **v4 copy** of the master: 21 objects, **71,880 triangles
  (15.8 % of LOD0)**. The objects are the cord (core + braid), attachment knots and knot crossings, the lower cord,
  charm eyelets, the charm (backing, petals, rims, engraving, stamens, filaments, centre), the bead, the gathered cap,
  the silver cap and its engraving, the filled bundle, the strands and the loose fibres. All the material the sword
  loses with it is Silk (9 objects). Silver, Recess and Inlay are also used by the tassel's metal parts, but remain in
  use elsewhere.
* **Pommel cleanup.** The cord and knots only touched the pommel housing at about (-0.018, 0, -0.151). No pommel mesh
  exists only to hold the cord, so nothing dangles when the tassel goes. The reference cap shows a small side lug
  where its cord exits. Per the decision, **omit the lug** and keep the bezel and the pierced vine band continuous.
  The pommel is rebuilt as an end cap anyway (change 3).
* **Helpers and data.** Delete the `Socket_TasselRoot` Empty. `lod_helpers.thin_tassel` and the
  `sf_secondary_motion_candidate` flag become obsolete. The rev-3 collision already excluded the tassel, so it is
  unaffected.
* **Bounds.** Width drops from 171.9 mm (the tassel reached x = -0.1076) to the guard width: 128.6 mm today, about
  111 mm after the guard fix. The sheath and the holster envelope must use the tassel-free bounds.
* **Material count.** It drops from 8 to 7 by itself, before the consolidation in change 8.
* **Record.** The sheet shows a tassel, so the tassel-free sword is an intentional deviation, decided by the user
  2026-09-26. Note this in the v4 README so a later reviewer does not "restore" it.

## 5. Ranked change list

**Keep from rev 3 (as bake source, in a v4 copy; never edit the rev-3 file):**

* The individual blossom construction: cupped petals, rims, engraving, stamens, filaments, centres. Used on the blade,
  guard, grip and pommel.
* The upper-blade trunk and twig routing.
* The guard's central blossom and crown chevron.
* The pommel medallion parts: flower, concentric rims, thorn wreath.
* The build-script helpers (`tube`, `bezier`, `flower`, `collar`, `ellipsoid`).
* The overall length and landmark heights.

| Rank | Change | Approach (keep vs rebuild) |
|---:|---|---|
| 1 | **Build a real game mesh and bake from the high-poly.** LOD0 about 35-45k triangles: blade about 3-5k with the channel, bevels and major relief clusters as low geometry; guard 10-12k (the silhouette is critical); grip 5-7k (round, 24-32 sides); pommel 3-4k; collar about 1.5k | Copy `SnowFlower_Master.blend` to a v4 high-poly file and apply changes 2-7 there. Model the low-poly by hand, or from simplified retopo of the kept parts. Do not decimate the rev-3 mesh. One atlas UV0 (Angle Based for hard surface; texel density per the note in section 3) plus UV1. Cycles bake **selected-to-active with cage, Extend margin**: normal (flipped to **DirectX** on write), **AO into ORM.R**, roughness, metallic, and BC from the procedural high-poly materials. Load data maps with `textures.load_data_image` |
| 2 | **Remove the tassel** | As in section 4. It is the first edit in the v4 high-poly |
| 3 | **Pommel: end-cap rebuild** | Rebuild the housing as a cap about 38 mm across and about 25 mm tall, with its axis along the grip. Re-seat the rev-3 flower, rims and thorn wreath as a recessed medallion on the **end face**. Add a pierced vine side band and a silver ring directly on the wrap. Remove the 25 mm neck and the separate pommel collar. No cord lug |
| 4 | **Guard: depth and silhouette** | Narrow it to about 111 mm and give it about 55-60 mm front-to-back depth. Replace the two rounded lower lobes with pointed almond leaves that cup the viewer. Radiate pointed leaves up, sideways and down, and turn the wing ends forward into bevelled angular hooks. Use thick bevelled silver rims instead of wire rims. Let the front and back pendant leaves wrap the blade base (about 25-30 mm deep in side view). Scale the central blossom up about 20 %. Keep the thorn lace as baked detail, not geometry |
| 5 | **Blade profile and surface form** | Widen the base to about 51-52 mm and taper to about 40 mm at 85 %. Start the tip sweep at about 50-55 % of the blade, with about 1.4x the rev-3 tip offset; keep the edge on +X. Model a wide edge bevel (about 25-30 % of the width), a narrow spine flat, and a shallow **recessed central channel** for the relief. Refit the kept relief with a lattice or curve deform rather than re-authoring it. Hand the new envelope to the sheath (section 6) |
| 6 | **Grip and collar** | A round cross-section of about 35 x 33 mm, flaring to about 40 mm at the collar. Wrap it in tight near-black cord with small diamond windows (about 11 crossings), baked from a high-poly cord wrap. A flared silver collar with front and back V-chevrons seated into the guard crown. Thicken the grip branches and enlarge the two blossom clusters |
| 7 | **Ornament density and finish (bake content)** | Dense, larger (about 12-15 mm) blossom clusters from the guard to about 40 % of the blade. Lower half: a thicker trunk with sparse sprigs. BC and roughness: blue-black mottled watery steel in the channel, mirror bevel (low roughness), the bright **wavy ribbon** from about 45 % to the tip (texture only), and antiqued silver with dark recesses (via AO and cavity). Recess metallic 1.0, or 0 if it is meant as lacquer |
| 8 | **Materials: 2 slots in the pack system** | `MI_SnowFlower_Steel` (blade, guard, collar, pommel; `M_Steel_Master`, BC/ORM/N at 4096) and `MI_SnowFlower_Wrap` (grip cord; `M_Fabric_Master` with the `Colour` option, 2048), following `WorkFiles/materials/MATERIALS_REPORT.md` conventions. Blackened steel vs silver lives in the maps, not in slots. Done in the Finalise phase |
| 9 | **Sockets** | Empties `SOCKET_SM_SnowFlower_LOD0_Grip` (primary hand, just below the collar), `_OffHand`, `_BladeTip` (trails) and `_BladeBase`, written to the `.sockets.json` sidecar and recreated with `ue_import_sockets.py`. Put the **mesh pivot at the Grip socket**, so the sheath's HOLSTER socket can simply be "where the sword pivot goes when sheathed" |
| 10 | **Collision** | Four hulls: straight blade, curved tip segment (so the concave side is not filled), guard, and grip + pommel, with no gap at z 0.171-0.19. Named `UCX_SM_SnowFlower_LOD0_00..03`, parented as the pipeline expects. Round-trip-verify the hull in Unreal as on the shuriken |
| 11 | **Authored LODs** | LOD1 about 50 % (drop the small relief geometry and let the bake carry it), LOD2 about 20-25 % (flat blade, simplified guard). Strictly descending, in one LodGroup, screen sizes set and verified in Unreal. No blind whole-mesh Decimate |
| 12 | **Export and verify** | FBX only through `Scripts/pipeline/export_fbx.py --kind static`. `qa_check` passes with the documented texel target. Import into Unreal with Import Mesh LODs ON and flip-green OFF, then a **second fresh process** asserts LOD count, triangles, hulls, sockets, textures and flags on the exact bytes. README records the DirectX normals and that the tassel was removed on purpose. Drop the GLBs unless the user wants them |

**Decisions for the user** (the auditor did not decide these):

1. **Overall length.** The sheet has no scale. Rev 3 chose 1.256 m (blade 0.943 m). That is long for a one-handed
   dao: confirm it against the MetaHuman player's height before the sheath is sized.
2. **Nanite.** Recommended **off** for a hand-held weapon with authored LODs and normal maps.

## 6. Handoff to the sheath

These are rev-3 numbers in master space: metres, blade +Z, edge +X, front -Y, origin at z = 0. The v4 values change
with changes 4 and 5.

* **Blade.** z 0.142 -> 1.085 (0.943 m). Width 46 mm (x ±0.023) down to z of about 0.79, then the tip sweeps toward
  +X, up to x = 0.0305 at the tip. Envelope x [-0.023, +0.0305]. Steel is 6 mm thick (y ±0.003); with relief it is
  y ±0.0065.
* **Guard.** Rev 3: x ±0.0643, y ±0.0201, z 0.1036-0.1708. The central pendant is 23 mm wide and reaches z 0.1708.
  After the guard fix, expect about 111 mm wide, about 55-60 mm deep, with the lower pendant leaves about 25-30 mm
  deep wrapping the blade base. The sheath throat must clear them or seat against them.
* **After change 5**, the blade base is about 52 mm wide, and the tip sweep is deeper and longer. A **straight
  scabbard** (as in the sheath reference) needs interior width of at least the swept envelope (about 60 mm near the
  tip) plus clearance, or the sweep must stay inside the straight cavity's width.

## 7. IP note (for the user to decide; nothing was acted on)

The reference sheet is titled "JIN MUWON - SNOW FLOWER BLADE". Jin Mu-won is the protagonist of an existing Korean
webtoon, *The Legend of the Northern Blade*. If this design derives from that franchise, it is fine for the dev's
personal game. It **must not be sold on Fab** under that name or as that design. `qa_check`'s deny list already
blocks "jinmuwon" and "northern blade" in names; the design question is for the user to decide.

## 8. Integrity

* The rev-3 files were read only: master `d3cd0780...bebb` and game blend `8e94b178...6d86`, both unchanged before and
  after every inspection run; the LOD0 FBX is `32f0e2c7...`.
* **Backup:** `Backups/SnowFlower_rev3_pre_review_2026-09-26/`, 154 files and 767 MB, with `SHA256SUMS.txt`. Every
  checksum was verified against the live files. It contains Assets, Exports (without v4, plus the three rev-3 zips from
  `Exports/`), Renders, Scripts (no `__pycache__`), WorkFiles (without v4) and References.
* No Unreal process was started. No JinMuWon, MetaHuman or BlackCloak file was opened.
