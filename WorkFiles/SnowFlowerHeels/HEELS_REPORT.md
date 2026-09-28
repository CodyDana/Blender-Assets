# Snow Flower heels: final report (2026-09-27)

**Result: the heels are engine-ready but not a "to the T" match.**

The shoes import correctly onto MH_PlayerFemale's skeleton, render at the right size as a Leader Pose follower, and stay on the floor and outside her skin in standing, walking and running with the rebuilt foot-pose correction. They are in the pack colour system.

The look still clearly differs from the reference: blind round 1 picked our copy 16/16. Closing that gap needs a new look-matching round that rebuilds the counter, toe and stiletto geometry. The user decides whether to run it.

Exports: `Exports/SnowFlowerHeels/` (README.md there covers use in DemoGame_1).

## 1. Timeline

| Phase | Result |
|---|---|
| Study | Female fitting body `References/Characters/MH_PlayerFemale/` locked. Feet measured. Heel pose solved and verified in Unreal. Heel 90 mm, pitch 33.67 deg, pelvis 71 mm |
| Reference metrology | `HEELS_REFERENCE_SPEC.md`, 66 traces, camera about 22 deg elevation |
| Round 1 build | All gates pass. Silhouette IoU 0.835. LOD 19,665 / 9,821 / 5,041 |
| Blind round 1 | **16/16 correct, 16 confident, 16 design-confident.** Round 2 not run (decisive fail, early stop) |
| Verify | Unreal: FAIL (metre FBX drawn 100x small; feet float and sink; the back crumples). Craft: FAIL (bake, UVs, counter shape) |
| Finalise (this pass) | Every blocker and major item that does not need a new look round is fixed (section 2). Pack materials built. Final renders. Documentation |

## 2. What the finalise pass fixed (and how it was measured)

| Issue (severity) | Fix | Evidence |
|---|---|---|
| **FBX in metres, drawn 100x small as a follower (blocker, all garments)** | `Scripts/pipeline/export_fbx.py` (pipeline 1.2.0): `kind="garment"` now writes centimetres. It exports temporary x100 copies from a 0.01 unit-scale scene; the sources and scene are untouched. `units="m"` is kept for comparisons. `test_garment.py` checks the file itself: the cm and m files agree to 0.026 deg / 0.00006 cm, and the sources are left as they were. The test passes, and `test_pipeline.py` passes | Unreal: root scale 1, local translations within 0.003 mm of her body, max scale deviation 1e-5, `follower_safe` true. Round 1 file: root 100, 90 cm off, `follower_safe` false (`final/ue_garment_check.json`). Worn renders at the right size (`Renders/SnowFlowerHeels/ue_fin3/`) |
| Unreal check missed it | `Scripts/garments/ue_check_garment.py` now compares the LOCAL reference pose with scale (`ref_pose_local_vs_body`, `follower_safe`) | Same run as above |
| **Bake: broken normals, AO 0, black blotches (blocker)** | Per-piece selected-to-active bake. Each game piece (58 pieces, face attribute `piece`, ornaments matched by `orn_id`) bakes only from its own high counterpart. Pieces closer than 6 mm never bake together (11 groups). Cage 1.5 mm, rays 4 mm. Margin 0 inside a rasterised mask, then a 16 px dilation. AO falls back to self-only when a piece's median AO is below 0.15 (insole, stiletto). Hard edges above 60 deg | N z < 0.2: Leather 5.24 → 1.18 % of island texels, Metal 7.92 → 2.86 %. Insole AO = 0: 65.7 → 0.01 %. Remaining AO = 0 (Leather 21 %, Metal 26 %) is mostly the hidden footprints under ornaments and the sunk plate walls. No black blotches in the final renders |
| **UVs shattered into hundreds of islands (blocker)** | Unwrapped per piece: SLIM (minimum stretch) for the upper's leather and lining, smart project 55 deg elsewhere, planar for the insole. One texel density, 8 px padding. Two round 1 bugs fixed. First, the overlap re-unwrap re-selected every face and re-projected whole slots at 20 deg. Second, re-projected faces were not brought back to the slot density | Leather 84 islands (coverage 0.57), Metal 628 (0.31, ornament shells), Insole 1 |
| Faceted colour and roughness in Unreal (major) | Same bake rewrite: missed or crossed rays had baked triangle patches into BC and ORM | Unreal close-ups `ue_fin3/*close*` |
| **Tall back crumples, leg passes through it (major)** | Three skinning variants measured on the round 1 walk capture before choosing. Rigid on foot: 568 vertices inside her leg, 30 mm deep. Height ramp: 435 inside. **Chosen:** her skin weights blurred in 3D (sigma 10 mm, up to 4 influences) so every ornament moves with the leather under it; the stiletto and top-lift stay rigid | Final walk: 0 shoe vertices inside her skin (round 1: 59). Stretch 27.9 → 24.4 mm, edges over 3 mm 945 → 546. Still bends, see section 4 |
| **Feet float or sink in walk (major)** | CR_HeelPose v2 (`HEEL_POSE.md` 4.3.1): heel rocker, toe contacts (barefoot toe, shoe toe underside, pointed tip), a floor guard, a pelvis that drops at once and rises smoothed | Whole-shoe metric (`final/analysis_r1_capture_newmetric.json` vs `ue/analysis_fin3_shipped.json`). Sinking over 3 mm: 136-144 → 14-25 grounded ticks; worst -72 → -3.7 mm. Floating over 10 mm: 46-58 → 52-74 ticks; worst about 19-20 mm, partly the 8 fps barefoot baseline |
| **Leaning-back stance (major)** | `PelvisForwardFollow` 0.8: pelvis 5.0 cm forward, reach-safe lift recomputed with the shifted hips, MaxPelvisLiftCm 7.30 | Self-test: pitch 33.68 deg, pelvis +7.13 cm up and +5.0 cm forward, ankle 0.55 mm from heel_pose.json, heel tip and ball sole on the floor (0.02 / 0.00 mm). Shin tilt 3.5 deg (barefoot 3.4 deg); round 1 leaned the shins a further 4.5 deg forward |
| HEEL_POSE 4.3 pitch axis (minor) | Documented: foot-axis pitch, as built | `HEEL_POSE.md` 4.3.1 |
| LOD influences; mirror not exact (minor) | LODs built on the right shoe, then mirrored (identical topology), each limited to 4 influences. The README now says 4, not 2 | Pair triangles 18,490 / 9,242 / 4,252 (9,245 / 4,621 / 2,126 per shoe) |
| Leather reads as plastic; silver highlights weak (major) | Leather roughness 0.68 (strap 0.62, sole 0.48) with ±0.05 grain variation from the baked relief. Silver base colour 0.72 linear at roughness 0.18, glossier and brighter on the bevels (curvature from N), and darker in the AO recesses | Reference-camera p95 luminance, ours vs reference: counter 0.761 / 0.758, toe 0.775 / 0.818, vamp 0.745 / 0.750 (`final/compare_final.json`) |
| Invented pieces; hollow outlines (major and minor) | Removed the toe "keystone". Crest spike and toe apex are now solid plates (their lenses rendered as a torn shard and a hollow triangle). Buckle hex and diamonds are solid bevelled plates instead of wire outlines | `Renders/SnowFlowerHeels/final_*` |

HeelAlpha wiring (minor): in 5.8 the variable pin cannot be exposed from Python. The README says to drive the node's Alpha, which is the tested path.

## 3. Pack materials (heels-chat, `run_build.sh heels_0927`)

- **Recolour maps.** `Scripts/SnowFlowerHeels/fin_recolour_maps.py` writes 16-bit linear tint-ready Detail maps: Leather 2048², and Insole 1024² box-filtered from 2048x1024.
- **Constants.** `maps/make_snowflowerheels_recolour_maps.py` and `maps/derive_constants_snowflowerheels.py` (copies of the Snow Flower pair). Every derive gate passes for both parts, including the default equal to the v1 contract at every mip and mip drift within 2 %.
  - Leather: Colour `#1B1A19`, Lightest 0.6
  - Insole: Colour `#3D3B39`, Lightest 0.544
- **Spec.** `material_spec.json` gained the item `SnowFlowerHeels` (skeletal, `/Game/NinjaPack/Meshes/SnowFlowerHeels`, its own skeleton copy), 6 instances, the recolour entries and `changes_v5_heels`. Masters and code are unchanged. The pre-edit copy is `final/materials/material_spec_before_heels_2026-09-27.json`.
- **Instances:**
  - `MI_SnowFlowerHeels_Leather` and `_Insole` on M_Fabric_Master (Colour)
  - `MI_SnowFlowerHeels_Metal` on M_Steel_Master (Steel Tint)
  - each with a `_Base`
- **Build.** Preflight OK, maps_check OK, then import_meshes, import_textures, clean, build, assign and verify all passed. Every verify gate is true (functions, masters, instances, meshes, textures, dependencies, accounting), with **0 compile failures**.
- **Other instances.** All 43 other instances and every master and function dump are **identical** to the previous build (kblade_0927). The only additions are the 6 heels instances (`final/materials/instances_unchanged_check.json`).
- **Lock.** Taken as heels-chat with a live keeper process, and released by run_build.sh at exit (status: nobody holds it).

## 4. Still differs (honest)

- **Counter.** A tall (129 mm above the ankle joint; reference 70-110), straight, bootie-like wall, 20-39 mm off the Achilles.
  - It lacks the reference's dense layered curved lames and leaf plates, the narrowing top and the mid bulge.
  - The traced front band reads as one straight silver bar. The crackle medallion is a flat oval.
  - Silver covers about a third of the reference's.
  - In walk and run it bends with the calf (stretch up to 24-26 mm): a tall back cannot be both rigid and clear of the leg. The fix is a lower, cupped counter (craft: 3-5 mm clearance, collar at most 100 mm).
- **Silhouette.** IoU 0.835. Straight heel-to-sole line. Straight stiletto rod with no flare, taper or silver cladding. Toe 67 mm past her toes, box-like with a slab sole. The heel height and toe length were never re-fitted together; a higher heel would be the user's call.
- **Ornaments.** Projected from view A, so they are stretched or chipped from other angles. Thin vines, flat blossoms, stick buds, simpler buckle.
- **Strap.** A plain 10 x 2 mm band (32 segments) with no stitching, keeper or tail.
- **Insole.** Line-art emblem, dotted-line branch, no stitched rim.
- **Leather.** The emboss and grain are barely visible at the reference distance.
- **Walk grounding.** About 10-13 % of grounded ticks still float more than 10 mm (worst about 20 mm), partly baseline sampling. Re-check with DemoGame_1's own GASP clips.
- **Not built in DemoGame_1.** CR_HeelPose and the heels are in CharacterLab `/Game/HeelsCheck` only. DemoGame_1 was not edited.
- **Other garments.** The BlackCloak_MH_v2 garment (another chat) was exported in metres before the pipeline fix. Its owner should re-export it and check `follower_safe`.

## 5. Proofs

- **Frozen items** (shuriken pack incl. kunai, smoke bomb, black hat, fan, paper bomb): 120 export and asset files, SHA-256 identical before and after (`final/frozen_before.sha256` / `frozen_after.sha256`).
- **Her MetaHuman assets.** All 342 files under CharacterLab `Content/MetaHumans` are identical before and after (`final/metahumans_*.sha256`). Every one of the 20 CharacterLab runs of this pass reports 0 changed, 0 added, and no new content outside `/Game/HeelsCheck`.
- **Fitting body.** The 9 files under `References/Characters/MH_PlayerFemale/` are identical. The fitbody blend sha is b35c9247.
- **Processes.** No Blender or UnrealEditor-Cmd process is left running. MH_Hiyuki_Private and DemoGame_1 were never touched.
- **Locks.** SnowFlowerHeels (claimed for the asset blends) and PackMaterials (heels-chat) are released. mh_playerfemale_heels was not needed; her export was not redone.
- **Backups.** Round 1 is backed up in `Backups/SnowFlowerHeels_r1_2026-09-27/`. Pre-edit copies of every changed shared script are in `final/scripts_before/`.

## 6. Files

- **Build:**
  - `Scripts/SnowFlowerHeels/hb_d_assemble.py` (solid plates, keystone removed, materials)
  - `hb_f_build.py` (per-piece UV and bake, skinning, mirrored LODs, cm export)
  - `fin_cr_toe_points.py`, `fin_recolour_maps.py`, `fin_pack_sidecar.py`
  - Report: `final/build_report.json`; log: `final/build_log.txt`
- **Unreal:**
  - `ue_hc_build_cr.py` (CR v2), `ue_hc_build_abp.py`, `ue_hc_capture.py`, `hc_analyze.py` (whole-shoe metric)
  - Results: `ue/import_fin3.json`, `ue/refpose_fin.json`, `ue/build_cr.json`, `ue/capture_fin3_shipped.json`, `ue/analysis_fin3_shipped.json`
  - Renders: `Renders/SnowFlowerHeels/ue_fin3/`
- **Renders from the shipped maps:**
  - `Renders/SnowFlowerHeels/final_side_by_side_viewA.png` (reference | ours | overlay), `final_refcam_viewA.png`
  - `final_pair_{34,side,back,front,top}.png`, `final_worn_{34,side}.png`, `final_lod_strip.png`
  - Part compares: `final_parts/cmp_final_*.png`
  - Worn standing, walking and running in Unreal: `ue_fin3/fin3_SHIPPED_*`
- **Pipeline:**
  - `Scripts/pipeline/export_fbx.py`, `test_garment.py`, `__init__.py` (1.2.0)
  - `Scripts/garments/ue_check_garment.py`
  - `ASSET_GUIDELINES.md` 6.1, `Scripts/garments/README.md`
