# Snow Flower heels: wearable pumps for MH_PlayerFemale

Built from `References/SnowFlowerHeels/snowflowerheels_reference.png`, using view A as the design authority.

- **Round 1** built them on 2026-09-27.
- The **finalise pass** fixed them on 2026-09-27. It covered the export units, bake, UVs, skinning, the foot-pose correction and the pack materials.

**Status:** the shoes are engine-ready and verified in Unreal 5.8.3, worn by her standing, walking and running. The **look is NOT "to the T"**: the blind test picked our copy 16 times out of 16 (see "Still differs" below). The full report is `WorkFiles/SnowFlowerHeels/HEELS_REPORT.md`.

## Files

| File | What |
|---|---|
| `SK_SnowFlowerHeels.fbx` | LOD0 with both shoes in one skeletal mesh: 18,490 triangles (9,245 per shoe). **Centimetre FBX** (pipeline 1.2.0) |
| `SK_SnowFlowerHeels_LOD1.fbx` / `_LOD2.fbx` | 9,242 / 4,252 triangles. Add them as LOD1 and LOD2 of the LOD0 asset |
| `SK_SnowFlowerHeels.garment.json` | Garment sidecar: skeleton and hash, slots, triangles, LOD screen sizes (1.0 / 0.5 / 0.25), max 4 influences, the heel-tip floor constant |
| `SK_SnowFlowerHeels.skeletal.json` | Sidecar the pack's material build uses to import the mesh |
| `Textures/T_SnowFlowerHeels_<Slot>_BC/ORM/N.png` | Baked maps. BC is sRGB. ORM is linear (R = AO, G = roughness, B = metallic). N is DirectX (green down). Leather and Metal are 2048². Insole is 2048x1024 |
| `Textures/Recolour/` | 16-bit linear tint-ready Detail maps for Leather (2048²) and Insole (1024²), plus `recolour_maps.json` and `recolour_constants.json`. All derive gates pass |

The left shoe is the exact mirror of the right one: same topology, UVs shifted +1 in U.

Sources:
- `Assets/SnowFlowerHeels/SnowFlowerHeels.blend` is the posed high-poly and game shells.
- `SnowFlowerHeels_Build.blend` is the built, skinned, rest-pose result.
- The scripts are in `Scripts/SnowFlowerHeels/`, mainly `hb_d_assemble.py` and `hb_f_build.py`.

## Put them on her in DemoGame_1

Nothing in DemoGame_1 was edited. These are the steps for you, or for a chat you authorise.

### 1. Import

This is the tested path (UE 5.8.3, legacy FBX importer):

1. Import `SK_SnowFlowerHeels.fbx` as a Skeletal Mesh onto her **existing** skeleton `metahuman_base_skel` (Female/Medium/NormalWeight). Never create a new skeleton.
2. Use these options:
   - Import Normals
   - Convert Scene ON
   - Convert Scene Unit ON
   - Force Front X OFF
   - no morph targets, materials, textures or physics asset
3. Add `_LOD1.fbx` and `_LOD2.fbx` as LOD1 and LOD2.
4. Set the screen sizes to 1.0 / 0.5 / 0.25. While the shoes follow her body, they use the body's LOD anyway.

A metre FBX (round 1) imported with root bone scale 100 and was drawn 100x too small on her. The centimetre file imports with root scale 1, and its local bone translations match her body to 0.003 mm. In a check with `Scripts/garments/ue_check_garment.py`, `follower_safe` is **true** for this file and false for round 1's.

### 2. Materials

The pack project (`WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject`, `/Game/NinjaPack`) holds:
- `MI_SnowFlowerHeels_Leather` and `MI_SnowFlowerHeels_Insole` on `M_Fabric_Master` (recolourable: set **Colour**)
- `MI_SnowFlowerHeels_Metal` on `M_Steel_Master` (**Steel Tint** only)

Each has its `_Base` instance under `MaterialInstances/Base`. Migrate the three buyer-facing instances to DemoGame_1; their masters, functions and textures come along. Then assign them by slot name: `M_SnowFlowerHeels_Leather`, `_Insole` and `_Metal`.

### 3. Wear them

1. In `BP_MH_PlayerFemale`, add a Skeletal Mesh component under **Body** with `SK_SnowFlowerHeels`.
2. Set its Leader Pose Component to **Body** (Copy Pose From Mesh also works).

### 4. Enable the foot-pose correction (required)

The shoes are modelled on her foot posed IN the heel and exported in the bind pose. Without the correction they sit on a flat foot.

1. **Get the Control Rig.** Migrate `/Game/HeelsCheck/CR_HeelPose` from the CharacterLab project (`Exports/CharacterLab/Unreal`) to DemoGame_1. Or rebuild it with `Scripts/SnowFlowerHeels/ue_hc_build_cr.py`, adjusting its body path.
2. **Add the node.** In `ABP_MH_NinjaBody_Female`, add a **Control Rig** node (class `CR_HeelPose`) right **after** the Retarget Pose From Mesh node. It must come before the body's own post-process ABP.
3. **Drive it.** Drive the node's **Alpha** with a float `HeelAlpha`: 1 while the heels are equipped, 0 barefoot. Set it from the equip logic. The rig also has a public `HeelAlpha` variable. In 5.8 its pin cannot be exposed from Python, so tick "Use Pin" in the editor if you prefer that; the tested wiring is the node's Alpha.
4. **Tuning pins** (defaults are the tested values):

| Pin | Default |
|---|---|
| HeelPitchDeg | 33.67 |
| BallLiftCm | 0.745 |
| ToeSpringDeg | 3 |
| GroundedCm / GroundedFadeCm | 2 / 4 |
| MaxPelvisLiftCm | 7.30 |
| PelvisSmoothTime | 0.1 s |
| PelvisForwardFollow | 0.8 |

What the rig does each frame (full design in `WorkFiles/SnowFlowerHeels/HEEL_POSE.md`, sections 4.3 and 4.3.1):
- pitches the foot up to 33.67 deg about the ball contact; clips that already lift the heel are left alone;
- keeps the toes level plus toe spring;
- clamps the shoe to the floor while the foot is grounded, and never lets any shoe point go below the floor;
- raises the pelvis by the reach-safe amount (7.1 cm standing) and moves it 5 cm forward so the shins stay upright;
- runs two-bone IK on each leg.

Re-check the result with DemoGame_1's GASP-retargeted clips. The test used the MetaHuman plugin's Idle, Walk and Run clips as a stand-in.

## Colours (default look)

| Part | Default |
|---|---|
| Leather (upper, lining, strap, sole, heel cover) | `#1B1A19`: near-black satin with a fine grain and a tone-on-tone floral emboss. Roughness about 0.6-0.76 |
| Insole | `#3D3B39` ground with a pale blossom-branch print and a silver-grey diamond emblem |
| Silver fittings | Antiqued silver `#DDD7D1` base with bright, glossy bevels (roughness about 0.07) and dark recesses (`#7C7673`) |
| Blossoms | Pearl `#CBC5C0`, dielectric |
| Toe cap | Glossy black patent `#121212`, roughness 0.06 |

Recolour the leather and insole with **Colour**, and the silver with **Steel Tint**. Pearl and patent keep their colours because they are dielectric in the ORM.

## Checks

| | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| Triangles (pair) | 18,490 | 9,242 | 4,252 |
| garment_qa + qa_check (fitted, MH_PlayerFemale) | 76/76 | 76/76 | 76/76 |
| Worn in the heel pose: vertices inside her skin | 0 | 0 | 0 |
| Worn: smallest clearance (1st percentile) | 1.28 mm | 1.02 mm | 0.63 mm |
| Unreal import (vertices) | 18,224 | 9,274 | 3,876 |

The character's LOD0 total is 130,120 + 18,490 = 148,610 of 160k.

Worn in Unreal with CR_HeelPose (MetaHuman plugin clips, fresh editor):

| | Round 1 | Final |
|---|---|---|
| Shoe vertices inside her skin, walk | up to 59 (5.5 mm deep) | 0 (walk and run) |
| Grounded ticks where the shoe sinks more than 3 mm below the floor | 136-144 of about 550, worst -72 mm (the long toe at push-off) | 14-25, worst -3.7 mm |
| Grounded ticks floating more than 10 mm (whole shoe) | 46-58, worst about 19 mm | 52-74, worst about 20 mm |
| Edge stretch, walk | 27.9 mm max, 945 edges over 3 mm | 24.4 mm max, 546 edges over 3 mm |

About the grounded ticks: the barefoot baseline is sampled at 8 fps, so part of the float count is foot-lift transitions. Round 1's own 51-53 mm floats were measured on the heel-tip and ball regions only, which misses the toe.

Standing: the pelvis rises 6.8 cm and moves 5 cm forward, and the shins tilt 3.5 deg (3.4 deg barefoot).

## Blind tests

Round 1: the judge picked our copy in **16 of 16** pairs, 16 confidently and 16 on design. Round 2 was not run: the workflow stopped early because the gap was decisive. The finalise pass changed only construction defects, not the design, so no new blind round was run.

## Still differs from the reference (honest list)

- **Heel counter.** It is a tall, straight, bootie-like wall. Its top is about 129 mm above the ankle joint, where the reference measures 70-110 mm, and it stands 20-39 mm off the Achilles. The reference has dense layered curved lames and leaf plates on a heel cup that narrows at the top and bulges in the middle. Ours has a straight vertical silver band (the traced "front branch band"), a thin sickle and a flat oval crackle medallion. Silver covers about a third of what the reference shows.
- **Silhouette.** IoU 0.835 in view A. The heel-to-sole line is straight with no arch curve. The stiletto is a straight rod with no flare, taper or silver cladding. The toe is long (67 mm past her toes) and box-like, with a slab sole.
- **Ornaments.** They are projected from view A, so they read right in view A but look stretched or chipped from the back and inner side. The vines are thin. The blossoms are flat five-petal stars. The buds are dots on sticks.
- **Buckle.** The plates are now solid, but it is still simpler than the reference's blossom-between-diamonds buckle.
- **Strap.** It is a 10 x 2 mm band on 32 segments, faceted up close, with no stitching, keeper or tail.
- **Insole.** The emblem is a flat line drawing, the branch is a straight line with dots, and there is no stitched rim.
- **Leather.** The emboss and grain barely read at the reference camera distance.
- **Motion.** The tall back still bends with the calf in walk and run, stretching edges up to about 24-26 mm. The fix is a lower, cupped counter.

These need a new look-matching round that rebuilds the counter, toe and stiletto geometry. The user decides whether to run it.
