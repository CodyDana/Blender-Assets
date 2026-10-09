# Assault Rifle AR-01: final report (2026-10-09)

The user asked for the first gun of the line: an assault rifle matched to their AI design sheet
(`References/Guns/Rifle/rifle_sheetAB.webp`) for the UE 5.8 ninja game, usable in first and third person. Delivered:
- `SK_AR01`: the rigged skeletal rifle (8 bones + root, 4 LODs, 5 weapon clips, `PHYS_AR01`, 17 sockets);
- `SM_AR01`: the static twin with a merged magazine (4 LODs, 7 hulls);
- `SM_AR01_Mag`: the removable magazine (4 LODs, 2 hulls, 5 sockets).

All three are exported through `Scripts/pipeline`. They were checked in Unreal 5.8.3 on the exact shipped bytes, and 3
import gates are still open (section 5). They are also in the pack's colour system, and the walnut is recolourable.
The showcase folder is `showcase/AssaultRifle_AR01/`.

| | |
|---|---|
| Exports | `Exports/Guns/AR01/` (FBX + `SK_AR01.skeletal.json` + `.sockets.json` + `Physics/` + `Textures/` + `README.md` + `MATERIALS_README.md`) |
| Sources | `Assets/Guns/AR01.blend`, `Assets/Guns/AR01_Mag.blend` |
| Scripts | `Scripts/guns/gunlib/` (shared with the next guns), `Scripts/guns/rifle/` (`run_rifle.sh` -> `run_game.sh` -> `run_rig_mag.sh`), `Scripts/unreal/materials/maps/derive_constants_ar01.py` |
| Spec and plan | `WorkFiles/guns/rifle/rifle_spec.json` (R1-R52), `RIFLE_BUILD_PLAN.md`, `RIFLE_STUDY.md`, `CRAFT_STUDY.md`, `trace/`; the line's `GUN_BUILDING_STUDY.md` |
| Gates | `WorkFiles/guns/rifle/gates/*.json` (one file per stage), `UnrealCheck/verification_summary.json`, `gates/pack_materials.json` |
| Reviews | `review/REVIEW_RESULTS_paused_2026-10-07.json`, `review/FIX_LOG.md` |
| Renders | `Renders/Guns/AR01/` (form greys), `showcase/AssaultRifle_AR01/` (10 images), review sets in `review/` (scratch PNGs, not in git) |

## 1. The study in short

- **Pattern.** A stamped-receiver 7.62x39 rifle with walnut furniture, 880 mm long.
  - The sheet's side, top and 3/4 views are the authority for silhouette and proportion.
  - Small parts follow how the real stamped-receiver pattern is made, with the sheet's close-ups as guidance.
  - Where the close-ups contradict the main views (spec R36), the main views and the real pattern win.
- **Side.** The panel labelled LEFT is the gun's true RIGHT side.
- **Generic.** No names, markings or logos anywhere.
- **User decisions (binding).**
  - A rigged skeletal mesh (the pilot skeleton for the gun line), plus a static twin and a separate magazine.
  - Moving parts: the bolt (carrier + charging handle, full travel), trigger, selector, magazine catch, rear sight and
    magazine.
  - "We make the animations": 5 weapon clips.
  - ADS-sharp textures: class A 80-100 px/cm, class B 60-80 px/cm, a 4096 Metal set if 2048 cannot hold that at
    >= 70 % fill.
  - Magazine 26 mm thick (R32). Grip checkering is real modelled cuts, baked to a normal map.
  - UE 5.8 First Person rendering documented (`FP_Weapon` / `TP_Weapon`, `FP_Mag` / `TP_Mag`, ForcedLodModel 1).

## 2. Build (stages 1-6) and gates

Rebuild from nothing: `run_rifle.sh` -> `run_game.sh` -> `run_rig_mag.sh`. The last full rebuild was the stage-7 fix
round; all 59 rows in `gates/review_fixes.json` pass.

| Stage | Key results |
|---|---|
| 2 Form (`form.json`, 32 / 34 rows; the 2 rows that fail are the raw 3/4 view rows, covered by the exception rule) | Side IoU **0.9759** (>= 0.96); top **0.9321** (>= 0.93); true-left vs the RIGHT-labelled panel 0.9184. 3/4 view **0.9185**, passed through the documented exception (`rifle_q34.py`: IoU >= 0.915, and 16 of the 18 residual regions are 3/4-panel contradictions, 2 are the magazine minimum). Side contour P95 1.0 px; 15 / 15 feature positions; 26 / 26 key dimensions within 0.05 mm; 21 / 21 parts pass per-part IoU; 0 static intersections; LOD0 49,474 triangles (ceiling 50k) |
| Mag fit (`form_magfit.json`, `mag.json` M1-M8) | 0 intersecting pairs when seated (every co-visible LOD pair); top stop 0.30 mm; lateral 0.20 / 0.20 mm; front lug 0.19 mm in its recess; rear lug to catch 0.20 mm; the rock-in path is clean (a straight insert collides, as on the real pattern) |
| 3 UV + bake + paint (`uv_bake_paint.json`, 31 / 31) | Metal 4096: the 2048 set could not hold the class floors at 70 % fill (5.57 M texels needed vs 2.94 M). Density: class A 96.6 / 114.8 px/cm (P5 / median), class B 82.2 / 91.9, furniture B 73.9 / 95.7. Fill: Metal 0.727, Furniture 0.661, Mag 0.664. 0 UV overlaps, 0 mirrored islands. L5 colour matches the sheet under the physical light in every region. Wear audit: 0 bare clusters on panel interiors; largest bare blob 3.2 mm2 |
| 4 Game (`game.json`, 23 / 23) | Twin LOD0-3: 55,052 / 24,460 / 9,098 / 1,324 triangles; rifle LOD1 46.4 %, LOD2 17.5 %; sight picture 0.0 / 0.125 px; LOD-pop max 0.71 px |
| 5 Rig + export (`rig_export.json`, 14 / 14) | 8 bones, rigid skin, 5 clips read back within 5e-05 mm; the bounds extension (0, 0.378, 0) cm holds every LOD0-3 vertex on every clip frame |
| 6 Mag export (`mag.json`, 15 / 15) | `SM_AR01_Mag` LOD0-3: 6,666 / 1,998 / 648 / 248 triangles; the twin's merged magazine is identical at every LOD (0.0 mm) |

## 3. Review findings and what was done (stage 7)

The reviews ran on renders of the exported bytes (`review/blind`, `review/realism`, `review/set`):
- **Craft review L6: FAIL**, 8 major and 6 minor issues against a "0 major" bar. The silhouette, proportions and most
  small parts held. The surfacing and the motion failed.
- **Tech review:** 1 major, 8 minor and 4 notes.

All are dealt with in `review/FIX_LOG.md`.

**Root causes found and fixed in the generators** (every output rebuilt; 59 / 59 gates pass):
1. **The 16 px bake margin.** Blender writes each object's bake with its own margin, so each part overwrote its
   neighbours' border texels. In the Furniture set, 62,485 valid texels held another part's position. This one cause
   made the magwell wedge, the line across the upper handguard and the seam stipple. Every pass now bakes with
   margin 0, and the texel-size estimate respects island borders.
2. **The magazine's AO was baked with the magazine seated.** The receiver's shadow showed as dark triangles once the
   magazine was out. It now bakes alone.
3. **The edge masks measured 3D distance.** The far side of thin walls printed through. They now count only edges on
   the texel's own side.

**Majors.**
- **Bolt.** A real rotating bolt with extractor, a trunnion bore and a raised trunnion. The piston now moves with the
  carrier.
- **Clips.** Every clip that moves the bolt holds the selector at Auto. `ShellEject` moved to frame 3.
- **Magazine catch.** One flat stamped paddle.
- **Rivets.** 24 segments; LOD0 stays at 49,474 triangles.
- **Review lighting.** Review sets and realism renders now use the physical (L5) light.
- **Wear.** Real and gated: bare steel only on true edges and in the handling zones.

**Minors.** Front sight window, brake soot, dents along the grain, groove-only checkering, a floored latch recess,
magazine wear zones, and the twin's magazine now identical to `SM_AR01_Mag`.

**Rulings (spec R52).**
- LOD3 at about 1,100 triangles is accepted (LOD-pop max 1.41 px).
- The ribs and floor plate may exceed the 26 mm body (R32): they are pressed outward, as on real steel magazines.
- Texture sizes: Metal 4096, Furniture 2048, Mag 1024, Detail16 1024.

**Withdrawn partial fix.** The paused UV "visibility retry" split islands and dropped Metal fill to 0.649 (under the
0.70 gate). The wedge it targeted came from the bake margin.

## 4. Blind and realism results (reported, not blocking)

- **Blind test (one judge, 12 A/B pairs against the sheet): 12 / 12 picked, all confident, with design tells.** It ran
  before the stage-7 fixes and was not re-run after them.
  - Tells fixed: the handguard seam, the dark checkering patch, the white magazine chips.
  - Tells rejected:
    - The sheet contradicts itself on the selector shape and the true-left stamping.
    - The sheet draws a smooth dust cover (R50).
    - Close-up vs main-view conflicts (R36).
    - Render style: AI photo vs CG.
- **Realism (two judges, four judgements recorded, all before the fixes).** The close views were called fake: hero 3/4
  in 3 of 4 judgements; first person at 35 cm, ADS and the contact sheet in 4 of 4. The 3 m third-person view was
  called real in 4 of 4.
  - Tells fixed: the lighting rig, the blotchy cover, the procedural grain, the handguard line, the checkering patch,
    the magazine streaks, the glossy knob.
  - Tells rejected:
    - The wood is saturated on the sheet itself (L5 measured).
    - The ADS front post is visible and centred (B4).
- **Not done:** the two realism judges and the blind judge were **not re-run on the fixed bytes**. Target for that run:
  at most 1 single-judge fake call over the 4 realism views.

## 5. Unreal (stage 8, UE 5.8.3, `UnrealCheck/verification_summary.json`)

The harness is a copy of the katana's, extended. It ran in `/Game/GunCheck/AR01_1009b` of the validation project, on
the exact shipped bytes: sha256 was recorded first and stayed unchanged through every pass. One Unreal process ran at
a time, and none was left running.

The passes:
- A: import (fresh process);
- A2: builds a saved check level;
- B: read-back (second fresh process);
- C: GPU render;
- E: a ticking `-game` world (physics, texture streaming);
- D, F: analysis of the read-back geometry and poses.

**Pass:**
- U1 skeleton (head error 4e-06 cm);
- U2 procedural bolt and selector;
- U3 the 17 sockets within 0.001 cm, plus 17 + 5 on the statics;
- U4 First Person: the FP components cast no ground shadow and stay on LOD0, while the TP component falls to LOD3;
- U5 LOD counts and screen sizes (the magazine's re-derived from engine bounds match exactly) and U5 bounds (after the
  LOD0-3 extension fix);
- U6 / M9: magazine attach error 1e-14 cm; reload clips free of intersections on every frame;
- U7 physics: drop and rest in the game world;
- U9 clips within 0.1 mm, notifies on their frames;
- U12 textures at their top mip at the hip and at ADS;
- C2: every LOD0 surface point inside the hulls (7 + 2);
- slots, Nanite off, texture flags, full mips.

**Fail (open):**
- **U10.** The static import logs "nearly zero tangents" and "degenerate tangent bases".
- **U5 triangle equality.** Unreal's static import (Remove Degenerates) drops every triangle under 0.005 mm2:
  4,584 / 580 / 122 on `SM_AR01` LOD0-2 and 772 / 33 on the magazine LOD0-1. `gunlib.tspace.unreal_drops()` predicts
  these counts exactly.
- **U8.** Unreal's generated lightmap UV overlaps by a few texels: 1 / 3 / 4 texels on LOD1-3 at 64 px.

The root cause of U10 and U5 is micro bevel strips made by the part generators. Three post-process fixes made the test
meshes import clean, but each broke other gates: non-manifold edges, part clearance, UV range, worse lightmap overlap.
All three were reverted.

**Not run:**
- U11: no player MetaHuman in the verification project, and no posed H1 baseline.
- U4 owner-only visibility: this needs the weapon Blueprint on a possessed pawn.

## 6. Pack colours (stage 9, `gates/pack_materials.json`)

**Lock and spec.**
- Materials lock owner `ar01-gun-chat`, held for the whole stage and released at the end (`np_lock.py status` =
  null).
- `material_spec.json` gains 3 items:
  - `AR01` (`SK_AR01`, skeletal, `Meshes/AR01`);
  - `AR01_Static` (`SM_AR01`);
  - `AR01_Mag` (`SM_AR01_Mag`).
- 6 instances: `MI_AR01_Metal` and `MI_AR01_Mag` on `M_Steel_Master` (the katana's steel precedent: baked finish,
  Steel Tint), `MI_AR01_Furniture` on `M_Fabric_Master`, each with its `_Base`.
- Also added: the AR01 recolour group, the three Masks maps as not imported, a new texture kind `BC_BC7`, and
  `changes_v9_ar01`. Masters and code are unchanged except one new script, `maps/derive_constants_ar01.py`.
- **Additions only:** removing the AR01 keys gives back `materials/material_spec_before_ar01.json`
  (`materials/add_ar01_to_spec.py`).
- **Constants:** every `derive_constants.fabric_part` gate passes. The default equals the v1 contract at every mip,
  the guards are inactive, and the mip fit is within 2 %.

**Build.** `run_build.sh ar01_1009b` (maps_check, import_meshes, import_textures, clean, build, assign, verify):
- every step passed; 0 compile failures;
- all verify gates true: functions, masters, instances, meshes, textures, dependencies, accounting;
- every AR01 LOD section resolves to the pack's instances; PS instructions 163 (wood) / 165 (steel).

It ran from a temporary mirror root, so that the other items came from exactly the bytes of the last pack build
(`katana_1003`, main's working tree) and nothing tracked in the main checkout changed. The validation project itself
lives only in the main checkout.

**Every other entry unchanged.** Dump `katana_1003` vs `ar01_1009b`:
- instances 69 -> 75, meshes 23 -> 26, textures 114 -> 124: only AR01 entries added;
- nothing removed or changed; the node layout is identical.

**Wood default.** The four wood pieces carry different hues in the BC, and the scalar detail map cannot hold them: the
recolour path at the default sits 34 levels p99.9 from the BC. So `MI_AR01_Furniture_Base` ships *Use Original Baked
Colours* ON, and a buyer recolour switches it off.

**UV-plane captures** (`materials/ar01_ue_capture.py` + `ar01_pack_analyse.py`, the pack's own twin and metrics):

| Gate | Result |
|---|---|
| P1 default capture = shipped BC, p99.9 <= 2 levels | **FAIL as worded.** BC1: 12 levels (dE00 mean 0.71, p99 2.26). With the furniture BC switched to **BC7**: **4 levels** (dE00 mean 0.23, p99 0.92, +2.7 MiB). The default IS the BC (no material math), so this is the compression floor, which the pack reports but does not gate for every steel BC. Only an uncompressed map (+18.6 MiB) would reach 2 |
| P2 recolour path at the default vs twin (p99.9 <= 1, mean <= 0.3) | PASS: max 1, mean 0.10 |
| P3 10-colour stress on the wood vs twin + v3 | PASS: every colour max 1 level; v3 (clip, banding, std ratio, Spearman >= 0.98) all 10 |
| P4 mip drift (mip 4 vs box-filtered mip 0) <= 2 % | PASS: worst 0.08 % |
| Steel BC1 vs PNG (reported) | Metal p99.9 7, Mag 6 levels |
| Detail16 in memory | G16 (2.69 bytes/texel with mips) |

Lit Unreal frames of `SM_AR01` and the magazine with the pack instances were looked at: wood, lacquer and magazine read
correctly on all three UV tiles of the twin.

## 7. Docs and showcase (stage 10)

**`README.md`:**
- the files and the skeleton;
- the import of the mesh, LODs and clips (bone compression, notifies table, bounds extension);
- selector layering;
- First Person (`FP_Weapon` / `TP_Weapon`, `FP_Mag` / `TP_Mag`, ForcedLodModel 1);
- sockets;
- the reload path (`MagInsertStart` -> `MagRockStart` -> 8 degrees about the front-lug hook -> `Mag`);
- the materials table and the colour controls;
- collision (UCX names, no collision in hand), centre of mass, physics;
- textures and compression;
- the measured Unreal notes, including the open items.

**`MATERIALS_README.md`** (rewritten for the pack):
- the slots and instances;
- the map settings (furniture BC7, ORM composite);
- the wood recolour steps (switch off *Use Original Baked Colours*, then Colour);
- Steel Tint;
- the measured numbers.

**Showcase.** `showcase/AssaultRifle_AR01/` holds 10 images:
- 9 studio renders of the shipped FBX + maps: hero, front, side, back, top, hero_dark, and the magazine's hero, front
  and side;
- 1 Unreal pack frame (`*_Scene_UE_threequarter`).

There is one row in `showcase/ASSET_LIST.md`, and the studio logs are in `WorkFiles/guns/rifle/showcase_logs/`.

## 8. Shipped bytes (sha256, unchanged since the stage-8 record)

| File | sha256 |
|---|---|
| `SK_AR01.fbx` | `8ff09166711a947039ddad82c5279ebc2fceb9e29988c11fa4b8bbf54c181f72` |
| `SK_AR01_LOD1.fbx` / `_LOD2` / `_LOD3` | `2d3925cd9f1f...` / `91909db0ab05...` / `cc3354b082ea...` |
| `SM_AR01.fbx` | `bc6f1982abeca534990637fc841f84d1e177ef6faf0ea893b5415b819c97edbc` |
| `SM_AR01_Mag.fbx` | `e6462ccfde4e5c4e10fedd516e1b928ac40c31ddab10a0dbb7b97708c3cae296` |
| `SK_AR01.skeletal.json` | `f166e50097d7cd7fc52ce0ae8ab6cf6c8a2d2d1f1effbe2b37ecaca321999688` |
| `A_AR01_Fire` / `Charge` / `Reload` / `ReloadEmpty` / `Selector` | `2477354313aea3a1...` / `485ec8dbfd5d6275...` / `0faa3260ed8d872e...` / `fe4febf15621c24c...` / `d94a4e89dc3b9d2e...` |
| `Textures/Recolour/recolour_constants.json` (new, stage 9) | `f15ddbea389e60de...` |

The full list is in `UnrealCheck/verification_summary.json` (29 files) and `gates/pack_materials.json`.
`README.md` and `MATERIALS_README.md` changed after stage 8; they are docs only.

## 9. What is left (honest)

1. **Micro bevel strips in the part generators.** They cause U5 triangle equality and U10. Fix them in the generators
   (a gate on `tspace.unreal_drops()` = 0 at stage 2), then re-run stages 2-8.
2. **U8 lightmap overlap.** Unreal's generated UV1 overlaps by a few texels on LOD1-3. Choose one: ship an authored
   UV1, raise the lightmap resolution, or declare the gun dynamic-lit only.
3. **Re-run the blind judge and the two realism judges on the fixed bytes.** Target: at most 1 fake call over the 4
   views.
4. **U11 hand fit.** The posed H1 on the player character has not been done; `SupportHand` and the `Grip` offset are
   provisional.
5. **Sidecar `materials` block.** `SK_AR01.skeletal.json` says `M_Fabric_Master` + Metal From ORM for the metal set,
   where the pack uses `M_Steel_Master`. No importer reads that block. Fix it in `rifle_rig.py` (line ~482, and add
   the magazine) at the next re-export.
6. **P1.** The wood default's compression floor (BC7, 4 levels p99.9) vs the 2-level gate. Uncompressed would cost
   +18.6 MiB.
7. **Decisions for the user:**
   - LOD0 checkering as cut geometry (tech T5; about 3-6k triangles at 49.5k / 50k);
   - the Fab design changes (plan section 13; none applied).
8. **Pipeline-wide:** the FBX files embed the absolute source path (tech N1). Fix before Fab.
9. **Merge order.** The validation project now holds the AR01 meshes and instances under `/Game/NinjaPack`. Until this
   branch is merged, a pack build from a spec without AR01 stops at `clean`, which lists the `MI_AR01_*` assets as
   unexpected and deletes nothing (safe, but blocking). Merge this branch before the next pack build, or re-run the
   build from a spec that includes AR01.

## 10. Lessons for the next guns (SMG, carbine, sniper, long rifle)

- **Bake with margin 0** and fill afterwards per island. A per-object margin overwrites the neighbours' texels, and it
  causes many separate-looking defects (wedges, lines, stipple).
- **Bake a removable part's AO alone** (the magazine). Seated AO prints the host's shadow onto the part.
- **Edge masks must be same-side.** Otherwise the far side of thin walls prints through.
- **Gate Unreal's degenerate rule in Blender at stage 2.** Unreal drops triangles under 0.005 mm2
  (`|cross|^2 < 1e-8 cm^4`); count `unreal_drops()` = 0 at form time. Patching the meshes afterwards broke other
  gates three times.
- **The bounds extension must cover every LOD,** not only LOD0. A coarser LOD can be wider.
- **Clips that move the bolt must hold the selector at a firing position.** Blender's FBX exporter writes a clip's
  first frame as the node defaults, so review tools must pose from absolute matrices.
- **Wood with per-piece hues** cannot be carried by the pack's scalar detail. Ship *Use Original Baked Colours* ON,
  give the BC BC7, and say so in the README.
- **Pack builds from a worktree** need the main checkout's validation project and the exact export bytes of the other
  items. A short-path mirror root (copied scripts + junctions) works. The scratchpad path is too long: Windows
  MAX_PATH broke the Snow Flower v4 paths.
- **Keep the sidecar's material plan in step with the pack's master choice** (steel parts on `M_Steel_Master`).
