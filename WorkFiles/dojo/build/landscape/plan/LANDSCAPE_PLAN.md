# Dojo LANDSCAPE ROUND: plan (stage: PLAN, 2026-09-30)

This plan replaces the town around the compound with the setting of `References/Dojo/dojo_landscape_ref.png`, and it
keeps the sunset. It was written read-only everywhere except this folder: no Unreal process ran, and nothing was
written to DojoLab, a content source, DemoGame_1, the GASP sample, ArmoryLab, git, or another chat's files.

**Files in this folder**

| File | What |
|---|---|
| `landscape_plan.json` | The layout. Level frame, the same as `layout_showcase.json`: metres, x east, y north, z up, courtyard z 0. Unreal cm = (x*100, -y*100, z*100); UE yaw = -rot_z. Azimuths in this plan are measured from north (+y) toward east |
| `landscape_plan_topdown.png` | Top-down plan. Near field: 200 x 190 m, 10 m grid. Far field: 12 km, 1 km grid |
| `ref_camera_check.png` | The reference beside a wire projection of the plan through `CAM_LandscapeRef`, with the check points marked |
| `owned_inventory.json` | Measured owned content: asset-registry tags read straight from the `.uasset` bytes (`scan_owned.py`, `uatags.py`) |
| `make_plan.py` | Regenerates the JSON and both images: `py -3 -B make_plan.py` |

**Owner constraints carried into every stage**
- UDS dusk stays: time locked at 1730, sun 9.08 deg from the west, the round-9 `restore_s1` look values.
- The Water plugin is approved.
- The Megaplants settings are on.
- **The Yoshino cherry is on hold.** The plan uses hidden CherrySlots only.
- Scenery is sourced, never generated. We sculpt only the UE Landscape.
- Owned content is copied into DojoLab by FILE COPY, never Migrate, and never written back into its source.

## 0. Reading the reference (the authority for this plan)

I looked at the reference and at 2x crops (terrace, stair, river, far).

- **Gate and forecourt.** The compound's front wall stands on a stone base. From the gate, 3-4 steps go down to a
  narrow forecourt, and a 2-4 m ishigaki wall holds the forecourt.
- **River side.** To the right of the forecourt, the compound's SE part stands on a taller stone base directly above
  huge rounded boulders and the river.
- **Stair path.** It leaves the west end of the forecourt: a few steps and a lantern landing, then a paved stretch
  under the cliff, then a lantern landing at the head of a long flight, then a foreground flight down toward the
  viewer. The rails are timber on the river side; the other side is a tall, rounded, mossy granite cliff.
- **River.** It comes from the far right (NE), runs past the SE of the terrace as white-water rapids among big rounded
  boulders, and leaves the frame at the bottom centre-right.
- **Trees and ground.**
  - Cherries: a big framing cherry on the right, on both banks, around the compound, and low pink ones by the stair.
  - Niwaki pines by the compound and at the gate.
  - Conifers directly behind the hall.
- **Far view.** A dark forested ridge stands in front of two snow peaks (the left one larger); hazy ridges recede
  up the valley to the right.

**Rejected deltas:** none. There were no judge deltas at this stage.

**One conflict is resolved by the owner.** The stone study's SG11 target, measured on this daylight reference, is
hue 32 deg / saturation 0.24 / R/B 1.33-1.40, which is warm. The owner's target is **mid-grey granite with moss**,
and the owner wins. The kit's tan in Blender renders is fixed in the Unreal material instances (section 7).

## 1. Inventory of owned content that fits (measured)

Resolutions are the asset-registry `Dimensions` tag.

**Caution:** several Scenery_Tutorial textures are named "4K" but register 1024x1024. Confirm in-editor before
relying on them. Triangle counts are the registry's Nanite source counts.

| # | Asset | Path (read-only source) | Measured | Fit to the reference |
|---|---|---|---|---|
| 1 | **Fir trees** `SM_Fir_Tree_01..08` + `SMF_Fir_Tree_Billboard` (impostor) | VaultCache `NordicFi1d739256ce1cV1/data/Content/Fishermans_Cabin/Meshes/Foliage/Tree` (Nordic Fishing Hut; also in DemoGame_1 and MyProject6, do not use those copies) | 10.3-16.0 m tall, 4.9-6.8 m wide; Nanite 274k-811k tris, 1 simple collision each. Needles `T_Fir_Tree_DO/N` **512**; bark `T_Bark_DO/N` 2K, ORM 1K; billboard 1K; `MF_Tree_Wind` | **GOOD for the slope conifer forest** (FZ1-FZ3) at 30 m or more. A Nordic spruce/fir, not a Japanese cedar or cypress, so the silhouette is close enough in mass. The 512 needle texture is too soft near a camera: keep them 30 m or more from gameplay cameras. The billboard serves the mid ridges |
| 2 | **Megaplants Japanese Cypress** `Tree_Japanese_Cypress_01_A..G` | VaultCache `Megaplanb3dc3e6c5a59V1/.../Tree_Japanese_Cypress` | Skeletal Nanite Foliage (Route B), 44-959 bones; 0.36-83 M Nanite assembly tris; textures 4K (bark C/NAH, foliage CA/NT) | **GOOD species, HEAVY.** A few only (5) as the front row directly behind the hall, where the reference shows tall conifers. PVE + Nanite Foliage are already on |
| 3 | Megaplants Ginkgo `Tree_Ginkgo_01_A..D` | VaultCache `Megaplan1093c7601c36V1` | Route B, 299-792 bones; 4K textures | **NOT USED.** The reference shows no ginkgo (invent nothing) |
| 4 | **Bushes** `SM_Bush_01..10` | Fishermans `Meshes/Foliage/Bush` | 1.4-2.4 m; Nanite 3.7k-33.7k tris; `T_Bush_DO` 2K, N/ORM 1K; no collision | **FAIR.** Interim rounded green shrubs for the forecourt corners, stair sides and banks (the reference's green mounds) |
| 5 | Grass `SM_Grass_01..07`, Flower `01..03` (+ foliage types) | Fishermans `Meshes/Foliage/Grass`, `Flower` | 0.2-1.6 m clumps, 142-1,025 tris; foliage atlas 2K | **GOOD** for the grass and moss-bank scatter. Flowers are optional (the reference shows none) |
| 6 | **Rocks** `SM_Rocks_01..04` | Fishermans `Meshes/Rocks` | 1.3-2.9 m (01 131x191x169, 02 251x184x213, 03 138x204x195, 04 171x293x56 cm); Nanite 78.6-80.0k tris, 2-6 collision prims. Unique `T_Rocks_N` **1K** + `T_Rocks_Mask` 2K over a **4K** tiling rock set (`T_Rocks_D/N/R/DP`) | **UNCERTAIN form** (the stone study's unchecked candidate for foot boulders). A 1K unique normal fails "2K or more for rocks over 1 m", but the 4K tiling detail helps. **Form check in staging before use** (study 2.4). 04 is a flat slab: river-bed only |
| 7 | Pebbles `SM_Small_Rocks_01..05` | Fishermans `Meshes/Small_Rocks` | 8-15 cm, 118-270 tris; mask/N 1K | **GOOD** as waterline and path-edge pebble scatter (NoCollision), after the colour check |
| 8 | **Mountain** `SM_Mountain_01` + `MI_Mountain` (`M_Mountain` with **`MF_Snow`**, `MPC_Global_Snow`) | Fishermans `Meshes/Mountains` | 303 x 303 x 47 m; Nanite **2.16 M** tris | **CANDIDATE** for the two snow peaks and far ridges (peaks option A), scaled about 12-15x in xy and about 40x in z. Its look is unknown: it needs a staging capture. The snow function is useful even if the mesh is not |
| 9 | Landscape mesh `SM_Landscape_01` | Fishermans `Meshes/Landscape` | 87 x 131 x 19 m, 92k tris, not Nanite, vertex-paint path material | **NOT USED.** We sculpt our own Landscape |
| 10 | **Tiling ground** `T_Grass_D` 4K / N, ORD 2K; `T_Ground_Dirt` D/N 4K, ORD 2K; `T_Ground_Dirt_Cracked` 4K | Fishermans `Textures/Tiling_Textures` | as listed | **GOOD** landscape layers: grass on the terrace strips, dirt on the paths and the BR trail |
| 11 | Fog cards `T_Fog_01..03` (1K), `M_Fog`; `T_Water_N` 2K/512 | Fishermans | 1K | FAIR, for low mist cards if the Niagara mist is heavy |
| 12 | **Megascans surfaces**: MossyRockyGround (+ vcrkeax), MossyGrass, ForestGround, MossyCreekStones, BeachCliff, Snow | `Documents/Unreal Projects/Scenery_Tutorial/Content/Megascans/Surfaces` | all **1K** in the registry (roughness 256); displacement 1K | **GOOD in kind, WEAK in resolution.** Landscape layers: moss, forest floor, river bed, cliff slope, snow. 1K tiling is fine at landscape scale, but soft on the banks next to the stair (a gap, rank 6) |
| 13 | Megascans 3D `Nordic_Beach_Rocks` | Scenery_Tutorial `Megascans/3D_Assets` | 16.6 x 9.4 x 2.7 m shelf, Nanite 19k tris, 1K maps | **WEAK.** A flat coastal shelf, not rounded granite. At most a river-bed or far-bank ledge beyond 60 m |
| 14 | **Landscape tools**: `BP_Landscape_Patch`, **`T_Land_Mountain01/02`**, `T_Land_Erosion00/01` (heightmap stamps, 1K); `MF_SlopeBlend`, `MF_TriplanarProjection`, `MF_VTGroundBlend`, `MF_CellBomb`; `T_MacroVariation` 2K, `T_NoiseMask_RGB` 4K, `T_Voronoi_Perturbed_4k` | Scenery_Tutorial `Landscape/`, `Example/` | as listed. `LG_A..E` grass types are **empty** (no meshes) | **GOOD.** The stamps sculpt the north hill, ridges and (option B) the peaks on our Landscape. The functions build the landscape material |
| 15 | Scenery_Tutorial `Mountain.umap` (a sculpted mountain landscape) | Scenery_Tutorial `Example/Maps` | 65 MB level | Only usable as a heightmap export, which means opening Scenery_Tutorial in an editor (writes its `Saved/`). **Owner call**; not needed if 8 or 14 pass |
| 16 | **Engine Water plugin** content: `Water_Material_River` (+ LOD, transitions), `WaterRiverFlowmaps`, `T_WaterFlow_01/03_Foam_Tiled` (+N) **2K**, caustics, `WaterBody_Niagara_ShoreFoam` | `UE_5.8/Engine/Plugins/Experimental/Water/Content` | 2K foam, 512 flowmaps | **GOOD.** The river body, the turquoise retint and the rapids foam. Engine content, nothing to copy; enable the plugin (approved). WaterAdvanced (Niagara fluids) is optional and not needed |
| 17 | **Niagara Examples** `FX_Fog/BP_FogBankVolume` + `SVT_FogBank_*` (sparse volume) + `T_FogBank_*` 1024x512 | VaultCache `NiagaraExamplesPack` | as listed | **GOOD** for the low mist bank over the rapids (with our own mist Niagara) |
| 18 | Paragon Kallari water FX `T_Mist` 512, `T_WaterSplash2x2` (+N) 1K, `M_WaterMist`, `M_Water_Drops_Master` | VaultCache `ParagonKallari/.../FX` | as listed | FAIR, as spray-sprite textures if our spray flipbook falls short |
| 19 | UDS `Wind_Debris`, `UDW_Wind_Force`, `Sound/Environment/Forest_Example` | DojoLab's UDS copy (already in the project) | - | Wind for the petals; a forest ambience bed (optional) |
| 20 | **Electric Dreams Env** (in the owner's Fab library) | VaultCache `ElectricDreamsSample_5.8` | **Download incomplete:** 23.9 GB staged of about 60 GB, nothing under `data/`, idle since 2026-09-12 | Epic's big Nanite rock/cliff/forest sample: **the most likely owned source of rounded granite rocks and cliffs**, unverified until the owner resumes the download |
| 21 | Our own: stone kit `SM_DKT_*` (71 pieces, f3), pines `SM_DKN_*` (8 trees + 4 mounds, v2f), this round's petal and mist FX | `Exports/DojoKit/StoneKit`, `Exports/DojoKit/Pines` | see `kit_catalog.json`, `Pines/README.md` | Terrace walls, stair path, rails, lanterns; niwaki pines; petals (held) and mist |

**Other projects checked** (`Documents/Unreal Projects`, read-only): BatmanScene has urban Megascans shrubs (39 cm,
2K) and cobbles. **Weak fit, not used.** OceanSide_Tutorial has the Water plugin enabled but no content. The other
projects hold no scenery.

**The queue's "Scenery_Tutorial firs/bushes/grass" are in fact the Nordic Fishing Hut (Fishermans_Cabin) pack.**
Scenery_Tutorial holds only Megascans surfaces, one beach-rock shelf, the landscape functions and patch stamps.

## 2. Gap list for the owner (ranked; UE-native `.uasset` with textures and Nanite on; deliver to a staging project, not DojoLab)

1. **Rounded granite rocks: the stone study 2.4 sourcing list, about 12-16 rocks.** Nothing owned is verified to
   fit.
   - Huge foot boulders, 1.5-3 m, rounded jointed granite: **2-3** (BF1 at the terrace walls). Candidate: Fishermans
     `SM_Rocks_01..03` only if the staging form check passes.
   - River boulders, 0.5-1.5 m, rounded, some elongated along the flow: **4-6** (the rapids and banks; about 40-60
     instances).
   - Mid rocks / cobbles, 0.15-0.5 m, or a merged cobble pile: **3-5**.
   - Jointed granite cliff/outcrop chunks, 2-8 m, vertical fractures, designed to overlap and bury: **3-4** (the
     west cliff C1 beside the stair, the reference's left cliff).
   - Pebbles and far vista rock: covered by owned content (Small_Rocks; the Nordic shelf beyond 60 m).
   - Spec: Nanite at least 50k tris within 10 m; a unique normal of 2K or more on rocks over 1 m; game-only licence,
     never in a Fab product of ours.
   - **Do first:** resume the Electric Dreams Env download in the launcher, which probably closes much of this with
     owned content.
   - Search terms: "granite boulder", "river rock", "rounded boulder", "granite cliff".
2. **Two snow-capped peaks.** This gap exists only if both owned options fail the staging look check: option A,
   Fishermans `SM_Mountain_01` scaled; option B, the Landscape sculpted with the Scenery_Tutorial mountain stamps.
   - Need: 1-2 Nanite alpine mountain meshes, or 2K-4K mountain heightmaps, 3-5 km wide, sharp snow-cap ridgelines,
     with snow/rock masks.
3. **The Yoshino cherry: ON HOLD by the owner.** When released: Megaplants Yoshino Cherry, UE format. Confirm the
   name and size before downloading. 20 CherrySlots wait for it (section 3.9).
4. **Japanese slope conifers (optional).** The Nordic firs make a believable forest mass, and the Megaplants cypress
   is too heavy to mass. Closer would be 3-5 static Nanite sugi (Japanese cedar) or hinoki trees, 15-30 m, with an
   impostor or billboard.
5. **Understorey that the reference shows.** 4-6 rounded evergreen shrub variants (azalea/boxwood-like mounds,
   0.6-1.5 m) and 3-4 fern or moss-cushion clumps. The Fishermans bushes are the interim.
6. **Higher-resolution ground surfaces.** 2K-4K versions of mossy rocky ground, moss, forest floor, river gravel and
   a granite cliff surface (4-5 surfaces). The owned ones are 1K in the registry.
7. **(Optional) River and nature ambience audio:** a rapids loop, a calmer run loop, wind in pines, birds. UDS
   `Forest_Example` is the interim.

## 3. Layout plan (numbers in `landscape_plan.json`; picture in `landscape_plan_topdown.png`)

### 3.1 The compound (unchanged)
- Footprint: x -1..45, y -1..37. Courtyard z 0, wall top +2.0, gate centre (22, -1), hall at y 21.5-33.85.
- Every piece, gameplay number, collision, GASP marker, the 1v1 ring and the alley blockers stay.

### 3.2 Terrace and forecourt
- **Upper terrace, z 0.0:** (-7, -3) to (49, 44) around the compound. It has four strips:
  - the south verge in front of the south wall: y -1..-3. The south wall's footing bottom is at -0.06, so this band
    stays at z 0;
  - the west strip: x -7..-1;
  - the east strip: x 45..49;
  - the north strip: y 37..44.
- North of y 44, the hillside rises. There is no wall there.
- Under the compound, the landscape sits at z -0.30, hidden below the kit ground meshes.
- **Forecourt, z -0.5:** x 12..34, y -3.0..-7.6.
  - Its north edge is a 0.5 m dressed step course (WallFoot) with its top at z 0.
  - The **gate stair** is two `Stair_Flight_W180_R050` side by side at x 21.1 / 22.9 (3 risers). They run from the
    gate paving edge at y -3.0 down to y -4.0, with outer cheeks at x 20 / 24.
  - A timber lantern stands left of the gate stair, and PineA1 stands right of it (as in the reference).

### 3.3 Ishigaki wall runs (SM_DKT_Wall_*, straight batter by default; about 97 m)

| Run | From → to | Faces | Top | Module / foot | Pieces |
|---|---|---|---|---|---|
| WR1 SW verge | (4,-3) → (12,-3) | south | 0.0 | H2 / -2.0 | 2 x 4m_H2; EndL at x 4 buried in the west rock knoll; becomes the north cheek of F1 |
| WR2 forecourt front | (12,-7.6) → (34,-7.6) | south | -0.5 | H4 / -4.5 | 5 x 4m + 1 x 2m; EndL at x 12; CornerOut at (34,-7.6); the west half is buried about 1 m by the rock bank; foot boulders on the east half |
| WR3 forecourt east | (34,-7.6) → (34,-3) | east | -0.5 | H4 / -4.5 | 1 x 4m; CornerIn at (34,-3); the 0.5 m top step there is closed with WallCoping_CornerIn + a WallFoot return |
| WR4 SE terrace | (34,-3) → (49,-3) | south | 0.0 | H6 / -6.0 | 3 x 4m + 1 x 2m + CornerOut_H6; the compound's SE corner stands on it above the rapids |
| WR5 east terrace | (49,-3) → (49,44) | east | 0.0 | H6 (y -3..9), H4 (9..29), H3 (29..44) | 3 + 5 + 3 x 4m + 1 x 2m; EndR_H3 into the hill at y 44; the foot steps are hidden by the rising bank |

The heights come from the reference: 2-4 m under the forecourt, taller under the SE of the compound.

### 3.4 Stair path, river landing → gate
- **Totals:** 7.0 m of rise, 42 risers (1/6 m riser, 1/3 m tread, 1:2 pitch, 26.57 deg), width 1.8 m.
- **Route:** 7 flights (plus the 2 side by side at the gate) and 7 landings or turns.
- **Kit pieces only:** flights R050/R100/R200, Landing/LandingL/LandingSB, cheeks, kerbs, rails, lanterns. The build
  stage derives each piece's loc/rot from `kit_catalog.json` `how_to_chain`; the JSON gives the bottom/top points.

| Seg | Piece | Bottom → top (x, y, z) | Notes |
|---|---|---|---|
| F1 | Flight_W180_R100 | (10.0,-6.5,-1.5) → (12.0,-6.5,-0.5), climbing east | leaves the forecourt west end |
| L1 | LandingL | (9.1,-6.5,-1.5) | turn; timber lantern |
| P1a | LandingSB (rot 90) | y -7.4..-11.4 at -1.5 | cliff-foot path |
| F2 | R050 | (9.1,-12.4,-2.0) → (9.1,-11.4,-1.5) | |
| L2 | Landing | (9.1,-13.3,-2.0) | timber lantern, river side |
| P1b | 2 x LandingSB (rot 90) | y -14.2..-22.2 at -2.0 | paved stretch under the cliff; rail on the east side |
| L3 | Landing | (9.1,-23.1,-2.0) | the reference's lantern landing at the head of the long flight; stone lantern |
| F3 | R200 (12 risers) | (9.1,-28.0,-4.0) → (9.1,-24.0,-2.0) | the long flight; rail on the river side, cliff face west |
| L4 / P2 / L5 | LandingL / LandingSB / LandingL | (9.1 → 3.3, -28.9, -4.0) | 4 m traverse west; rail on the south side |
| F4 | R200 | (3.3,-33.8,-6.0) → (3.3,-29.8,-4.0) | the reference's foreground flight; rails both sides |
| L6 | Landing | (3.3,-34.7,-6.0) | timber lantern |
| F5 | R100 | (3.3,-37.6,-7.0) → (3.3,-35.6,-6.0) | rail east |
| L7 | Landing + kerbs | (3.3,-38.5,-7.0) | river landing, about 0.6 m over the water and about 10 m from it; stone lantern; the BR trail continues SW (dirt) |

- **Rails:** about 34 m, timber (Rail_Slope R200/R100, Rail_Flat L180, end and corner posts).
- **Lanterns:** 6, about one per landing or turn, every 2.5-3.5 m of rise; timber on the upper path, stone lower
  down; lights at 2400-2700 K.
- **GASP:** riser 0.167 < MaxStepHeight 0.45; 26.6 deg < 44.77; width 1.8 > capsule 0.6; flags level; every landing
  at least 1.8 x 1.8. The path is outside the 1v1 bounds; it is walkable for the BR.

### 3.5 River (one WaterBodyRiver spline, downstream order)

| Pt | x, y | Water z | Width | Zone |
|---|---|---|---|---|
| R0-R2 | (300,470) (160,230) (88,95) | -1.0 / -2.4 / -3.6 | 26 / 22 / 18 | upstream valley from the NE |
| R3 | (66,42) | -4.3 | 15 | run beside the NE of the compound |
| R4 | (62,14) | -4.8 | 14 | riffle |
| **R5** | (57,-12) | -5.3 | 15 | **rapids:** SE corner, foot boulders |
| **R6** | (37,-17) | -6.2 | 16 | **rapids** under the forecourt wall (1.9 m of bank at the WR2 foot) |
| **R7** | (26,-30) | -7.2 | 16 | **rapids** tail beside the long flight |
| R8 | (17,-45) | -7.9 | 18 | run past the river landing; leaves the ref frame bottom centre-right |
| R9-R11 | (4,-64) (-30,-115) (-100,-230) | -8.3 / -9.0 / -9.8 | 19 / 24 / 28 | pool, exits SW |

- **Rapids R4→R7:** 61 m, 2.4 m drop (3.9 %), velocity 250-350 cm/s, depth 0.6-0.8 m. Elsewhere: run 1.2 m / 80-120,
  pool 2.0 m / 40.
- **Material:** `Water_Material_River` retuned turquoise-grey, with foam from the engine `T_WaterFlow_01/03` (2K)
  driven by velocity and boulder distance.
- **FX (ours):**
  - the river mist Niagara at 3 points of the rapids;
  - spray bursts at 6 emergent boulders;
  - a low mist bank along R4..R8 (NiagaraExamples `BP_FogBankVolume` or a Local Fog Volume).

### 3.6 Bank, slope, cliff and boulder zones

| Zone | Where | Content |
|---|---|---|
| **BF1** foot boulders | foot of WR2-east and WR4, x 24-58, y -3..-12 | 3 foot boulders 2-3 m + 6-8 river boulders + cobbles |
| **BF2** rapids channel | along R4-R7 | 14-18 boulders 0.5-1.5 m, 30-40 % emergent, elongated along the flow, sunk 15-35 % |
| **BF3** west bank | between the stair (x ~10) and the rapids | steep mossy rock bank: 6-10 boulders 1-2.5 m, moss cushions, shrubs, PineD2, CS08 |
| **C1** west cliff | x -16..7.9, y -3..-44 | Jointed granite outcrop; east face along the path at x ~7.9 (3.5-4.5 m) and x ~1.7 (about 5 m). Top +2.5 at (-2,-12), +1.5 at (0,-24), -1.0 at (-2,-36). PineD1, CS09, CS10 on top |
| **E1** far bank | east/south of the river, x 27-100 | boulder-edged bank rising 3-20 m; the cherry-slot row; bushes; firs behind |
| **P** lower bank | below L7 | dirt and moss, the BR trail SW, cobbles at the waterline |

- **Hero boulder targets:** 21, listed in the JSON (5 foot, 4 west bank, 12 in the rapids). They are placement
  targets for the sourced rocks.
- **Placement:** PCG per the stone study 5.8, with hand-placed heroes. Seating is burial, a moss skirt, same-rock
  debris, then decals.

### 3.7 Terrain and landscapes
- **LS_Valley:** 1,008 m square, 2017² vertices at 0.5 m, 16 x 16 components (126 quads each), Nanite, centred on
  (22, 18); z range -12..+120.
  - Base from the JSON spot heights plus the river channel carve.
  - Detail from Landscape Patches using the **owned** `T_Land_Mountain01/02` and `T_Land_Erosion00/01` stamps.
  - **Spot heights:**
    - north hill: 0 at y 44, +6 at y 60, +20 at y 100, +45 at y 200, +90 at y 400;
    - west ridge: +4 at x -30, +18 at x -80, +40 at x -200;
    - far bank: +2 at x 70, +5 at x 85, +20 at x 130.
- **LS_Far:** 8 km square, 1009² vertices at 8 m, Nanite, centred on (0, 3000), 30 m below LS_Valley where they
  overlap. It carries ridges M1, M2 and F (and option B's peaks).
- **Layers:**

| Layer | Source | Where |
|---|---|---|
| Grass | Fishermans 4K | terrace strips, gentle banks |
| MossyGrass | Megascans 1K | moss patches, bank crests |
| MossyRock | Megascans 1K | banks, stair sides, cliff ledges |
| ForestFloor | Megascans 1K | under the forest zones |
| RockSlope | Fishermans 4K tiling | auto on slopes over 35 deg |
| Dirt | Fishermans 4K | paths, BR trail, river margins |
| RiverBed | MossyCreekStones | under the water |
| Snow | Megascans 1K + our snow-peak material | LS_Far above the snowline |

  Macro variation comes from Scenery_Tutorial `T_MacroVariation` and `T_NoiseMask_RGB`.

### 3.8 Far ridges and the two snow peaks (placed from the reference pixels through CAM_LandscapeRef)

| Item | Position (x, y, z) | Scale | Look |
|---|---|---|---|
| **Peak A** (left, larger) | summit (1826, 7214, **+2078**) | 7.5 km, azimuth 14.1 deg; base about 4.7 km; snowline about +1140 | snow cap, rock ribs |
| **Peak B** (right, smaller) | summit (3861, 7288, **+2006**) | 8.3 km, azimuth 27.7 deg; base about 3.3 km; snowline about +1100 | appears lower in frame (farther) |
| M1 dark forested ridge | crest (118,1234,+164) → (346,1141,+261) → (569,1165,+179) | about 1.2 km N | hides the lower flanks of peak A |
| M2 valley ridges | (580,631,+81) → (1930,1686,+41) | receding NE along the river valley | hazier |
| F far ridges | about (2173,3536,+527) | 3.5-4.5 km | hazy blue, between the peaks |
| N near hill | crest about (22,200,+45) | directly behind the hall | Fir forest FZ1 + 5 Megaplants cypress |

- **Peak build, option A:** Fishermans `SM_Mountain_01` + `MF_Snow`, scaled.
- **Peak build, option B:** LS_Far sculpted with the patch stamps, plus our snow-peak material.
- Pick one by a staging capture.
- **Risk:** the UDS fog (round-9 values) may wash out peaks 7-8 km away (section 6).

### 3.9 Pines (SM_DKN; each tree = Trunk + Foliage (+ Rock for D) + its BaseMound; one transform)

| Id | Variant | Loc (x,y,z) | Yaw / scale | Where |
|---|---|---|---|---|
| P01 | PineA1 | (26.0,-4.6,-0.5) | 200 / 1.10 | forecourt, right of the gate stair (as in the reference) |
| P02 | PineC1 | (10.8,-2.1,0) | 135 / 1.00 | verge at the stair head; limb reaching SE over F1 |
| P03 | PineD1 | (6.2,-17.5,+1.8) | 70 / 1.15 | cliff edge above P1b |
| P04 | PineD2 | (13.8,-30.5,-4.8) | 250 / 1.20 | bank boulder east of L4 / the F3 foot |
| P05 | PineB1 | (-4.5,9.0,0) | 30 / 1.20 | west strip |
| P06 | PineC2 | (47.0,3.0,0) | 290 / 1.00 | east strip, leaning out over WR5 |
| P07 | PineB2 | (47.0,24.0,0) | 160 / 1.15 | east strip |
| P08 | PineA2 | (-3.5,33.0,0) | 10 / 1.25 | west strip |
| P09 / P10 | PineA1 / A2 | (0.62,21.0,0) / (43.38,21.0,0) | - | **OPTIONAL, inside the wall beds.** The reference shows pines by the hall. Gated: trunk-only collision (thin upright at most 0.4 m), then the walk and climb re-run; drop them if anything changes |

- Scale ranges follow `Pines/README.md`: A-D up to about 1.3x, C at most 1.05x.
- **Import recipe** (TREE_BUILDING_STUDY 4.13 / 5):
  - legacy FBX, Vertex Color **Replace**, Nanite on, Generate Lightmap UVs OFF;
  - trunk shape_preservation NONE; foliage **Voxelize** with **bLerpUVs off** (the PP2 index is in UV2);
  - PP2 textures Nearest / NoMips;
  - WPO Disable Distance 40-60 m;
  - trunk UCX only; canopies ignore Visibility and Camera.

### 3.10 CHERRY SLOTS (hidden; no cherry imported)
- **What a slot is:** an empty Actor named `CherrySlot_<id>` (or a hidden grey-box scaled to the slot), folder
  `Dojo/CherrySlots`, tags `[CherrySlot, <id>]`, bHiddenInGame.
- **Collision:** none, except CS01 and CS02, which keep today's grey-box trunk hull (0.5 m) so every walk and climb
  route stays identical.
- **Ground z:** snapped to the landscape at build.
- **Clearance:** no other tree within 0.5 x canopy; at least 1 m from any path edge.
- **Slots** (x, y, z; height / canopy in metres):

| Id | Loc | h / canopy | Where |
|---|---|---|---|
| CS01, CS02 | (3.5,16,0), (40.5,16,0) | 7 / 6.4 | courtyard W and E (the existing tree slots) |
| CS03-CS05 | (-4,1.5,0), (-4,22,0), (-3.5,41,0) | 7-8 / 7-8 | west strip and NW corner |
| CS06, CS07 | (47.2,13,0), (47,40,0) | 7 / 6 | east strip, NE |
| CS08 | (13,-23,-3.2) | 5 / 5 | bank beside the long flight |
| CS09, CS10 | (-6,-9,+1), (-1.5,-31,-0.5) | 8 / 8, 6 / 6 | cliff top |
| **CS11** | (28,-43.5,-6.5) | 10 / 11 | **hero cherry**, east bank, right edge of the ref camera |
| CS12 | (5,-47,-7.2) | 4 / 4 | low cherry by the pool |
| CS13-CS18 | (41,-31), (62,-22), (74,2), (78,30), (92,62), (108,95); z -5.5..-2 | 7 / 7 | far-bank row receding upstream |
| CS19, CS20 | (40,42,+0.5), (12,42,+0.5) | 7 / 6 | behind the residence and the storehouse |

- **Petals:** the petal Niagara is placed per slot but **inactive** (tag `CherrySlotFX`), plus one courtyard layer,
  until the cherries land. We capture one showcase variant with them on for the owner.

### 3.11 Conifer forest zones (PCG: Surface Sampler → filters → Self Pruning → Static Mesh Spawner, ISM, Nanite Voxelize, WPO off beyond 60 m)
- **Keep-outs for every zone:** water, walls, the terrace, paths plus 3 m, CherrySlot clearances, and the wedge from
  CAM_LandscapeRef to the compound.
- **FZ1 north hill:** (-40,46) (95,46) (130,210) (-70,210).
  - Fir 01..08: 1 per 60 m² at the edge, 1 per 35 m² beyond y 70, spacing at least 5 m.
  - **5 Megaplants Japanese Cypress** as the front row at y 47-52, x about 5 / 16 / 28 / 38 / 46 (the tall conifers
    behind the hall).
- **FZ2 west ridge:** (-170,-80) to (-16,-2) and on to (-14,44); Fir, 1 per 50 m².
- **FZ3 east valley:** (92,-80) (260,-70) (330,320) (140,270) (104,95) (88,20); Fir, 1 per 45 m², thinning near the
  far-bank cherries.
- **FZ4 mid ridges on LS_Far:** `SMF_Fir_Tree_Billboard` at 1 per 150 m² out to about 2.5 km, then a canopy
  material only.
- **Ground cover:** Fishermans grass on the strips and banks; bushes at the forecourt corners, stair sides and bank;
  pebbles at the waterline.

### 3.12 1v1 boundary (a separable group; the BR drops it)
- **Kept as is:** `SM_DGB_Boundary_1v1` (the ring on the wall's outer face, 11 UCX; it is still what stops a 1v1
  player at the open gate) and the 13 alley/pocket/roof blockers.
- **New second line on the terrace edge:**
  - folder `Dojo/Boundary_1v1`, tags `[Boundary_1v1, TerraceEdge]`;
  - Pawn block only, Camera and Visibility ignore;
  - 6 m tall, 0.5 m thick.

| Line | From → to | Base z |
|---|---|---|
| B1 forecourt front | (11.4,-7.35) → (34.25,-7.35) | -0.5 |
| B2 forecourt east | (34.25,-7.35) → (34.25,-3.0) | -0.5 |
| B3 stair head | x 12.2, y -5.4..-7.6 | -0.5 |
| B4 SE edge | y -2.75, x 34.25..48.75 | 0.0 |
| B5 east edge | x 48.75, y -2.75..44 | 0.0 |
| B6 north edge | y 44, x -7..49 (follows the ground) | 0.0 |
| B7 west edge | x -7, y -3..44 | 0.0 |
| B8 SW verge | y -2.75, x -7..12.2 | 0.0 |

- **Proposal, owner call:** `Dojo/Boundary_World`, kept in every mode at the playable-landscape edge and the far
  river bank.
- **Checks:**
  - the new CONTROLs for B1-B8, run with the ring disabled in a test copy;
  - `BR_stair_path_river_landing_to_gate` and its reverse, walkable;
  - everything existing unchanged: 47 walk routes, 32/32 alley CONTROLs, climb routes, GASP trace 23/23.
- The old `BR_road_onto_the_gate_apron` route is retired with the road.

### 3.13 Cameras
- **CAM_LandscapeRef**, level frame:
  - loc (4.8, -61.6, +12.9), yaw 24.2 deg from north, pitch -3.7, hfov 60, out 1024 x 1536 (portrait, as the
    reference);
  - UE: loc (480, 6160, 1290) cm, rotation yaw -65.8 / pitch -3.7.
- **How it was fitted:** weighted least squares on 10 reference landmarks, with the horizon held near the reference.

| Landmark | Error |
|---|---|
| gate ridge | 12 px |
| SE corner | 15 px |
| foreground flight | 29 px |
| river exit | 32 px |
| gate threshold / SW corner / lantern landing | 38-39 px |
| rapids | 48 px |
| hero cherry | 60 px |
| long-flight foot | 99 px |
| **hall ridge** | **116 px** |

- The hall-ridge error cannot be fixed: the AI reference exaggerates the hall. The composition matches: compound
  across the frame, gate left of centre, stair from bottom-left, rapids centre-right, river leaving at the bottom,
  peaks above the hall. See `ref_camera_check.png`.
- **Known deviation:** the reference's giant framing cherry fills the upper right. From a camera high enough to see
  the courtyard, CS11 fills the lower-right third instead.
- **Supporting cameras:**
  - `CAM_StairClimb`: L7 looking up to the gate;
  - `CAM_Rapids`: from L3 over the rapids;
  - `CAM_PeaksOverHall`: forecourt eye level toward the peaks.
- The 12 existing stills stay; the courtyard look is judged on `CAM_Ref2Match` as before.
- **Stills only via `-game HighResShot`** (run_game_capture.ps1), with shot names without dots.

### 3.14 Removed and kept
- **Removed:**
  - Outside/Street (237: road, kerbs, verges, canal, `SM_DKX_Road_Gate`);
  - Outside/Town (42);
  - Outside/Ground (4);
  - Outside/Far (6);
  - the modern props outside the walls (street lamps, poles, wires, junction box);
  - the grey-box tree visuals;
  - the 22 old tree_slots.
- **Kept:** every compound piece, prop, decal, light and GASP marker; the alley/pocket fences and Boundary_1v1; the
  UDS dusk and the round-9 look.

## 4. Stages for the build (each: back up L_Dojo + Config first; one Unreal process on DojoLab; one commandlet machine-wide; guards as run_game_capture.ps1)

1. **Staging checks (no DojoLab writes).** File-copy the candidates into a staging copy. Then:
   - clay captures of `SM_Rocks_01..04` and `SM_Mountain_01` (SG14 ratios) and of the patch-stamp peaks;
   - a colour check through our granite master;
   - pick peak option A or B, and decide rock gap 1.
2. **DojoLab setup.**
   - Enable Water (approved).
   - File-copy the Fishermans foliage, rocks, mountain and tiling textures, the Megaplants cypress, the
     Scenery_Tutorial surfaces, landscape functions and stamps, and NiagaraExamples FX_Fog, into
     `/Game/Scenery/...`, keeping their `/Game/<Pack>/` package paths so references resolve.
   - Import `SM_DKT_*` and `SM_DKN_*` per the recipes.
   - Stone MIs to the **owner's mid-grey granite target**: under the daylight test light after `G.look()`, saturation
     at most about 0.12, R/B 1.05-1.15, moss in the joints. Measured, not eyeballed.
3. **Level.**
   - Remove the town.
   - Place LS_Valley and LS_Far, walls, forecourt, gate stair, path, lanterns and rails, the river, boulders, pines,
     CherrySlots, forests, ground cover, FX (petals held) and the boundary group.
4. **Checks in fresh processes on the exact bytes:**
   - walk (existing + stair both ways), climb, alley 32/32, GASP trace, B1-B8 CONTROLs;
   - Nanite/UCX read-back;
   - perf: GPU mean and p95 at 1080p/1440p against round 9.
5. **Look.**
   - HighResShot stills: CAM_LandscapeRef + CAM_Ref2Match + the 3 new cameras.
   - Paired judge against the reference and against round 9 restore_s1. The sunset stays; apply the judge-steer rule.
6. **Notes.** A dated `LANDSCAPE ROUND` section in `BUILD_NOTES.md`. No commit.

## 5. Acceptance numbers (measure, don't eyeball)
- **Composition:** CAM_LandscapeRef landmark error within 60 px of the plan's projection (not of the reference),
  except the hall.
- **Horizon:** horizon y 700-760.
- **Peaks:** peaks A/B summits within 40 px of (350,457) / (567,493); snow visibly separated from the sky (peak
  luma - sky luma of 10 or more at 1730).
- **Stone:** kit wall vs sourced rock dE76 < 5 under the sunset rig (study 5.9).
- **River:** foam covers 25-45 % of the rapids surface in the reference-camera crop (reference: about 40 % white
  water in R5-R7).
- **Gameplay:** every existing route and CONTROL identical; stair path walkable end to end; B1-B8 block.
- **Perf:** GPU p95 at 1440p no worse than round 9 + 2 ms, with the forest at the planned density. If over, reduce
  FZ density first, then the cypress count.

## 6. Risks
- **The AI reference has no single perspective.** The camera is a compromise (hall off by 116 px). Judges comparing
  literally will flag the hall and the framing cherry.
- **Frame time.** Round 8/9 p95 is already over 16.7 ms at 1440p. The landscape (2017² Nanite), about 1-2k firs of
  274k-811k Nanite tris each, the Water body, 5 Route-B cypresses and the Niagara FX all add cost. Instance budget
  and WPO distances are critical; measure early (stage 4) before the look pass.
- **Nordic firs vs Japanese conifers.** 512 needle textures and a Nordic silhouette; acceptable at 30 m or more.
  The Megaplants cypress is heavy (up to 959 bones, 83 M assembly tris), so 5 at most.
- **Unverified rock forms.** 1K unique normals on the only owned boulders; Electric Dreams is incomplete. The
  boulder-heavy reference could stay weak until gap 1 closes.
- **Water plugin (experimental in 5.8).** A WaterBodyRiver edits landscape edit layers and adds a WaterZone. Test in
  the staging copy first. Keep the terrace/wall collision independent of the water.
- **UDS fog at the owner's round-9 values may wash out peaks 7-8 km away.** A peak-only material lift (emissive or
  fog-exempt) may be needed to avoid touching the approved look.
- **Portrait HighResShot** (1024x1536 from a 1920x1080 window). Confirm the horizontal FOV is kept; measure on the
  first still.
- **Landscape under the compound at -0.30** must never poke through the kit ground (check holes and bed edges). The
  south verge stays at z 0 because the south wall footing ends at -0.06.
- **"4K" names vs 1K registry sizes** on the Scenery_Tutorial surfaces: soft banks near the stair.
- **CherrySlots:** 20 Route-B cherries later would be very expensive. Record per-slot priority (hero CS11, courtyard
  CS01/02, CS03, CS06, far-bank row last) for the cherry round.
- **Licence:** Megascans, Fab and Paragon content is game-only; none of it goes into a Fab product of ours. The
  stone kit and pines stay our own.
- **Optional interior pines P09/P10** could touch the yard routes. They are gated and dropped on any change.
