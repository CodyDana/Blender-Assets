# Compact SMG SM-01: final report (2026-10-13)

The second gun of the line: a compact polymer SMG with a side-folding skeleton stock, matched to the user's AI design
sheet (`References/Guns/SMG/smg_sheetA.webp`) for the UE 5.8 ninja game, usable in first and third person. Delivered:
- `SK_SMG01`: the rigged skeletal gun (11 bones + root, 4 LODs, 8 weapon clips incl. stock fold / unfold and sight
  flip, `PHYS_SMG01`, 21 sockets);
- `SM_SMG01`: the static twin (stock extended) with a merged magazine (4 LODs, 8 hulls);
- `SM_SMG01_Mag`: the removable straight 25-round magazine (4 LODs, 1 hull, 5 sockets).

All three are exported through `Scripts/pipeline`. They were checked in Unreal 5.8.3 on the exact shipped bytes (W5:
34 of 34 gates, **no import gate open**, unlike the AR-01's three). They are in the pack's colour system: the polymer
(furniture and magazine) is recolourable as one group. The showcase folder is `showcase/CompactSMG_SM01/`.

**Not reached: the close-up realism bar.** Both realism judges still call every close view fake after two W4b rounds
(section 4). The user's bar says the judges decide, so this is the main open item.

| | |
|---|---|
| Exports | `Exports/Guns/SMG01/` (FBX + `SK_SMG01.skeletal.json` + `.sockets.json` + `Physics/` + `Textures/` + `README.md` + `MATERIALS_README.md`) |
| Source | `Assets/Guns/SMG01.blend` |
| Scripts | `Scripts/guns/gunlib/` (0.2.x, shared with the AR-01 and the next guns), `Scripts/guns/smg/` (`run_all.sh` = `run_smg.sh` -> `run_surface.sh` -> AR-01 regression -> `run_rig_mag.sh`), `Scripts/unreal/materials/maps/derive_constants_smg01.py` |
| Spec and plan | `WorkFiles/guns/smg/smg_spec.json` (rulings R1-R47, `tools/make_spec.py`), `SMG_BUILD_PLAN.md`, `SMG_STUDY.md`, `CRAFT_STUDY.md`, `SMG_DESIGN_SHEET.png`, `trace/`; the line's `GUN_BUILDING_STUDY.md` |
| Gates | `WorkFiles/guns/smg/gates/*.json` (one file per stage), `UnrealCheck/verification_summary.json`, `gates/pack_materials.json`, `gates/docs_showcase.json` |
| Reviews | `review/FIX_LOG.md` (W4 craft / tech / realism, W4b close-up r1 and r2), `review/closeup_r2/shots.json` |
| Renders | `Renders/Guns/SMG01/` (form greys, local), `showcase/CompactSMG_SM01/` (10 images), review sets in `review/` (PNGs local, not in git) |

## 1. The study in short

- **Pattern.** A compact polymer-framed pistol-calibre SMG (the APC / UMP family of construction: two-piece polymer
  receiver over a steel bolt, top Picatinny-pattern rail, side-folding skeleton stock, straight polymer magazine).
  - The sheet's LEFT, RIGHT and TOP views are the authority for silhouette and proportion (labels true, nothing
    mirrored, R3). The 3/4 panel is reported only: no rigid camera fits it (R39).
  - Small parts follow the real pattern (photos in `scratch/realref/`, rulings RP1-RP22 in `CRAFT_STUDY.md`).
- **Scale.** 625 mm overall (orchestrator ruling R26; the sheet's ruler and the first 690 mm read were wrong); one
  uniform factor on every sheet proportion, line-standard hardware absolute.
- **Generic.** No names, markings or logos anywhere. Selector detents (Safe -63.4 / Semi 0 / Auto +45) are a design
  call (R27); the folded stock is held by a moulded lug under the port catch (R28).
- **Line decisions.** Skeleton compatible with the AR-01's (`gun.compatible_with`), so one long-gun Anim Blueprint can
  drive both; FP / TP components as the AR-01; the magazine reloads on a **straight** path (no rock, R36 spring catch).

## 2. Build (W1-W3) and gates

Rebuild from nothing: `Scripts/guns/smg/run_all.sh`. The last full rebuild was W4b r2 (from W1); W5 re-ran the W3
chain from the rig step after its one fix (FBX content identical).

| Stage | Key results |
|---|---|
| W1a gunlib (`gunlib_regression.json`) | Shared parts (`rail_1913`, `mag_box`, `hinge`, `sights_flip`, `hardware`) and gun-agnostic drivers promoted to `Scripts/guns/gunlib/` (LIB 0.2.x); the AR-01's stage values reproduce exactly (14 / 14 value groups) after every gunlib change |
| W1b form (`form.json`, 54 / 54; `form_magfit.json`, 8 / 8) | L2 IoU LEFT **0.981**, RIGHT 0.955, TOP 0.932; 23 / 23 parts; L3 contour P95 2.0 px, 24 / 24 features; L4 20 / 20 key dimensions; every B3 sweep clean (bolt and charging 67.9 mm, selector -63.4..45, stock 0..180 within its declared allowances, both sights 90); G5 0 intersections; gun LOD0 48,238 triangles, magazine 4,300; H1 early (grip girth, reach 77.6 mm, length of pull 370.8 mm) pass. Mag fit: 0 intersections seated, seam 0.35-0.52 mm, the straight insert and removal paths clean with the spring catch cammed (M4: 138 steps) |
| W2 surface (`uv_bake_paint.json`, 43 / 43) | UV0 by texel class: Metal 2048 fill 0.73 (class A 118 px/cm P5), Furniture 4096 fill 0.67 (class B 95 px/cm P5), Mag 1024 fill 0.74; 0 overlaps, 0 mirrored; authored UV1 (0 overlaps at 64 / 128 px). Bakes margin 0, mag AO alone (AR-01 lessons). L5 colour matches the sheet under the physical light in every region (polymer sRGB 46 / 47 / 49); G20 steel darker than the polymer 1.543 (sheet 1.453). Polymer never metallic; bare steel only as edge lines (0 clusters off an edge). UD1-UD3 0 |
| W3 game, rig, mag (`game.json` 33 / 33, `rig_export.json` 21 / 21, `mag.json` 21 / 21) | Gun LOD0-3 48,236 / 23,832 / 8,844 / 1,420 triangles; twin 52,536 / 25,252 / 9,532 / 1,444; LOD-pop on both stock states max 2.5 px at the switches 2.33 / 10.97 / 17.67 m; UD1-UD4 0 on every LOD; sight picture 0.0 px at LOD0-2; hulls hold 39.7 M jittered samples; 11 bones, 8 clips (the bolt clips hold the selector at Auto), bounds extension over every LOD / frame / stock state; magazine from the shipped twin bytes (identical at every LOD), mag LOD sizes derived from the gun's; H1 full on `MH_PlayerDefault` |

## 3. Review findings and what was done (W4, W4b)

- **W4 review** of renders from the exported W3 bytes: craft review 5 major / 6 minor / 2 notes, tech review PASS with
  3 minor and 9 notes, two realism judges (every close view fake for both, `tp_3m` passed by both). All findings were
  checked against the bytes, the generators and the sheet; fixes went into the generators only and the chain was
  rebuilt from nothing (`review/FIX_LOG.md`, `gates/review_fixes.json`, 37 items). Main fixes: G3 opening facets
  (24 segments per semicircle, new gate G3o), bare steel as continuous edge lines instead of specks, moulded polymer
  texture in the normal map, the steel made darker than the polymer (G20), knurled windage drum, chamber-mouth wear,
  muzzle soot at the PBR floor, rolled magazine lips, twin LOD sizes on Unreal's sphere rule.
- **"Flat clay" measured.** The maps did reach the renders (hookup, colour space and UVs right); the paint was
  near-uniform at render scale (textured vs constant clay 1.8-3.5 levels) and the grey-world light gave a black
  dielectric nothing to reflect.
- **W4b close-up r1 and r2** (the user's dedicated close-up pass): curved surfaces keep smooth shading (the stock
  head's banding was `_flatten_planar` setting gently curved regions to flat normals: shading / geometric spread 0.27
  -> 0.98, K1); a product rig with mirror-placed softboxes (on a black dielectric the 4 % specular IS the look); satin
  polymer 0.47-0.55 vs phosphate ~0.8 (split 0.27); wear MIXED toward a worn grey (polymer BC P99 - P50 13 -> 27
  levels) instead of multiplied steps that no light could show; no bare steel on sights or selector; dust off the vent
  walls. `gates/closeup_r1.json` K1-K7 and `closeup_r2.json` K1-K8 pass.

## 4. Blind and realism results (reported; the realism judges decide)

- **Blind test:** 15 pairs re-rendered from the final bytes (`review/blind/`, key `review/blind_key.json`); reported,
  not blocking.
- **Realism judges after W4b r2: both judges call every close view fake** (hero_34, hero_34_folded, fp_35cm,
  ads_55deg, c1 rear sight / rail, c2 receiver left, c3 front end, their L5 versions, the clay diagnostics and both
  before / after sheets). Their recurring reasons:
  1. **One grey for everything.** Still read as no polymer / anodised / phosphate separation and low specular cues,
     even under the product rig.
  2. **The stock head** in FP / ADS reads as a thin draped sheet or ribbon (it is the traced S-curved top; smooth
     shading fixed the banding, not the form). The judges also call the hinge barrel a bare cylinder.
  3. **The ball charging knob** on its neck reads as a CG primitive.
  4. **Rail teeth** read as thin fins rather than flat-topped crossbars; the receiver's two-piece step and V grooves
     (the sheet's, R43) read as decorative booleans; isolated pin dots read as unexplained.
  5. **No markings** (selector letters, roll marks, slot numbers): an asset rule (generic), rejected by design.
  6. Wear on flats read as a speckle / concrete overlay rather than edge-focused wear.
  The c2 receiver-left close-up (trigger, guard, grip, pins) is the one both judges found closest to real.
  Next step if the user wants this bar met: a W4c round on the four geometry tells (stock head volume with wall
  thickness and a hinge knuckle, a moulded charging handle to the real pattern, flat-topped rail crossbars, seam /
  pin logic checked against the real photos) and a material pass that separates the steel by sheen, not only value.

## 5. Unreal (W5, UE 5.8.3, `UnrealCheck/verification_summary.json`)

34 of 34 gates pass in fresh processes, sha256 checked at start and end, behind a machine guard (one Unreal process).
Content `/Game/GunCheck/SMG01_1013b` in the katana / AR-01 verification project.
- U1-U12: import settings, 4 LODs with **triangles equal Blender / FBX / Unreal at every LOD**, 21 + 21 + 5 sockets
  on the right bones (within 0.001 cm), the 8 clips (rigid parts within 0.01 cm / deg, notifies on their frames),
  FP / TP (FP casts no world shadow, ForcedLodModel 1 keeps LOD0), PHYS_SMG01 drops (extended and folded),
  authored UV1 at 64 / 128 px, **0 asset warnings (U10)**, top-mip residency at hip and ADS, C2 hulls, M9 straight
  insert path with the R36 catch.
- **U2b, the first proof of the shared long-gun ABP:** one `ABP_Gun_LongGun` on `SK_AR01_Skeleton` drives `SK_SMG01`
  (Compatible Skeletons) and `SK_AR01` through normalized inputs and each gun's `abp_angle_table`; bolts 6.79 / 10.325
  cm, triggers 13 / 12 deg, detents reached, releases -11 / -10 deg, all within 0.01.
- **One asset fault found and fixed (U7):** with bodies instanced, a skeletal component takes its bounds from the
  physics asset; the folded stock lay 5.5 cm outside them and every SK on that route had a 33.6 cm LOD radius instead
  of 37.54. Fix in `smg_rig.physics_bodies`: a no-collision, no-mass envelope box spanning the extended bounds. Bounds
  now 0 cm outside, LOD radius 37.54 on every route.
- Reported: the ABP node on the SMG-only `stock` bone compiles with a "bone not found" warning (no runtime error);
  Unreal's stored UV1 shows 17-22 px overlap at 1024 px only; U11 (MetaHuman hand fit in Unreal) not run (no player
  MetaHuman in the verification project; H1 full passed in Blender).

## 6. Pack colours (W6, `gates/pack_materials.json`)

**Lock and spec.**
- Materials lock owner `smg01-gun-chat`, held with the session's live pid for the whole stage (`run_build.sh`
  releases it on exit, so it was re-claimed after each run) and released at the end.
- `material_spec.json` gains 3 items: `SMG01` (`SK_SMG01`, skeletal, `Meshes/SMG01`), `SMG01_Static` (`SM_SMG01`),
  `SMG01_Mag` (`SM_SMG01_Mag`).
- 6 instances: `MI_SMG01_Metal` on `M_Steel_Master` (Steel Tint), `MI_SMG01_Furniture` and `MI_SMG01_Mag` on
  `M_Fabric_Master` (Metal From ORM off), each with its `_Base`; the SMG01 recolour group (two members), the three
  Masks maps as not imported, `changes_v10_smg01`. Masters and code unchanged except one new script,
  `maps/derive_constants_smg01.py`.
- **Additions only:** removing the SMG01 keys gives back `materials/material_spec_before_smg01.json`
  (`materials/add_smg01_to_spec.py`).
- **Constants:** every `derive_constants.fabric_part` gate passes for both parts (default = v1 contract at every mip,
  guards inactive, mip fit within 2 %). They were derived **in the mirror**, on main's LF bytes of the pack code (see
  lessons): the constants record those sha256s, so `maps_check` passes on main after the merge.

**Build.** `run_build.sh smg01_1013b` (preflight, maps_check, import_meshes, import_textures, clean, build, assign,
verify) + `render`: every step passed, 0 compile failures; all verify gates true; every SMG01 LOD section resolves to
the pack's instances; PS instructions 163 (polymer) / 165 (steel); SK_SMG01 came through with 4 LODs, 21 sockets, 8
clips, PHYS_SMG01 (8 boxes + 1 capsule) and the bounds extension, from the W5-verified bytes. It ran from a short-path
mirror root (copies of main's pack code with this branch's spec and script; junctions to main's Exports of the other
items, whose 114 textures and 23 meshes match the last build's import records byte for byte, and to this worktree's
`Exports/Guns`), so nothing tracked in the main checkout changed.

**Every other entry unchanged.** Dump `katana_1003` (the last build in the main checkout) vs `smg01_1013b`: instances
69 -> 81, meshes 23 -> 29, textures 114 -> 135, only AR01 (the AR-01's additions-only build) and SMG01 entries added;
nothing removed or changed; node layout identical.

**Polymer default.** The recolour path at the default sits 20 (furniture) / 47 (magazine) levels p99.9 from the BC at
the detail size: the whitening specks and scuffs are finer than the 2048 / 1024 detail maps. Both `_Base` instances
ship *Use Original Baked Colours* ON; a buyer recolour switches it off on both and sets one Colour.

**UV-plane captures** (`materials/smg01_ue_capture.py` + `smg01_pack_analyse.py`, the pack's own twin and metrics):

| Gate | Result |
|---|---|
| P1 default capture = shipped BC, p99.9 <= 2 levels | **PASS with BC7** (the plan's fallback): furniture 2 / magazine 2 levels (dE00 mean 0.17 / 0.23). Measured first with BC1: 5 / 8 levels, so both polymer BCs ship BC7 (+10.7 MiB furniture, +0.7 MiB magazine) |
| P2 recolour path at the default vs twin (p99.9 <= 1, mean <= 0.3) | PASS: max 1, mean 0.12 / 0.03 |
| P3a 13-colour stress (10 + tan / OD / FDE) on both sets vs twin | PASS: every colour p99.9 1 level (26 captures) |
| P3b the pack's v3 gate | **FAIL as worded on Spearman only, at near black**: furniture 000000 0.973 / 1A1A1A 0.972, magazine 000000 0.946 (bar 0.98); clip 0, max gap 1, detail kept. The pack's float twin gives 1.0 there and the same 0.95-0.98 once stored in 8 bits: the 8-bit output at the black floor (sRGB ~25), the pack's known kunai-wrap miss |
| P4 mip drift (mip 4 vs box-filtered mip 0) <= 2 % | PASS: worst 1.73 % |
| Metal BC1 vs PNG (reported) | p99.9 4 levels |
| Texture memory | 81.0 MiB with mips for the whole set (furniture 4096 BC7 / N / ORM 21.4 / 21.4 / 10.7 MiB) |

Lit Unreal frames of `SM_SMG01` and the magazine with the pack instances were looked at: metal, polymer and the merged
magazine resolve on all three UV tiles of the twin. A pinkish glint on the magwell lip is the pack rig's atmosphere-
tinted key light, not the maps (max R - B in every SMG01 BC is 1-3 levels).

## 7. Docs and showcase (W6, `gates/docs_showcase.json`)

- **`README.md`**: files and skeleton; mesh, LOD and clip import (bone compression, notifies, bounds extension);
  selector state; stock states; the shared long-gun ABP; First Person; sockets; the straight reload path; materials and
  colour controls; collision (UCX names, no collision in hand), centre of mass (extended and folded), physics (the
  envelope box); textures and compression; measured Unreal notes.
- **`MATERIALS_README.md`**: slots and instances, map settings (polymer BC7), the polymer recolour steps (switch off
  on both, one Colour), Steel Tint, the measured numbers.
- **Showcase** `showcase/CompactSMG_SM01/`, 10 images: 9 studio renders of the shipped FBX + maps (`studio.py`; hero,
  front, side, back, top, hero_dark, magazine hero / front / side) + 1 Unreal pack frame (`*_Scene_UE_threequarter`).
  Studio logs in `WorkFiles/guns/smg/showcase_logs/`.
- **`showcase/ASSET_LIST.md` was not edited** (another chat has edits on main); the row text is in the stage summary
  for the main chat to add, as for the AR-01.

## 8. Shipped bytes (sha256; FBX and sidecars unchanged since the W5 record)

| File | sha256 |
|---|---|
| `SK_SMG01.fbx` | `2f671038e6cffb3a65ce0a7f78ca3a182df50abf8ac95f8d9e41dbe836ae484f` |
| `SK_SMG01_LOD1.fbx` / `_LOD2` / `_LOD3` | `e53c7e8ab290...` / `0472ac5c93a2...` / `010d5e7e11a6...` |
| `SM_SMG01.fbx` | `9145428cee628963c2413033f1b90c2ca790dc7cec723ca7277e8f646e0c1efe` |
| `SM_SMG01_Mag.fbx` | `7f44422cddbccfc4513c3b6e12269ef141975046937239896c0ad8519e60cceb` |
| `SK_SMG01.skeletal.json` | `c49acd7ddd2002bf642406fa6a2e0139ef0cab725f2b141ac6475dd0b368bea9` |
| `Physics/SK_SMG01_PhysicsProxy.fbx` | `262d01f76ab874d0384c1381c8c07a3e7a936955fe68984ace44cab08ac706da` |
| `A_SMG01_Fire` / `Charge` / `Reload` / `ReloadEmpty` / `Selector` | `abffef9009c6...` / `56823127eec8...` / `1baca15f32a8...` / `05543eb70b32...` / `f54deccd0d1f...` |
| `A_SMG01_StockFold` / `StockUnfold` / `SightFlip` | `d6924d88fb4c...` / `ae3db1564d46...` / `7b340ebfb19c...` |
| `Textures/Recolour/recolour_constants.json` (new, W6) | `2ced1c284252...` |

The full list is in `UnrealCheck/verification_summary.json` (33 files, all unchanged) and `gates/pack_materials.json`.
`README.md`, `MATERIALS_README.md` and `recolour_constants.json` are new in W6.

## 9. What is left (honest)

1. **Close-up realism** (section 4): both judges, every close view. The decision on a W4c geometry + material round
   is the user's.
2. **Game-side ABP.** `DemoGame_1_Guns`'s `ABP_Gun_LongGun` still drives the trigger with a constant AR-01 angle; it
   needs the normalized inputs and per-gun table proven in U2b before the SMG is wired in, and the SMG-only bones
   (`stock`, `sight_front`, `charging_handle`) on clips or a linked layer for a warning-free class ABP.
3. **U11 hand fit in Unreal** (no player MetaHuman in the verification project); `SupportHand` and the `Grip` offset
   come from the Blender H1 fit.
4. **P3b** near-black Spearman (the pack's 8-bit floor, proven on the twin).
5. **Texture budget decision:** the furniture set is 4096 (BC7 BC 21.4 MiB); a 2048 furniture set would lose the
   class-B density floor (95 px/cm P5 now).
6. **Merge order.** The validation project now holds the SMG01 meshes and instances under `/Game/NinjaPack`. Until this
   branch is merged, a pack build from a spec without SMG01 stops at `clean`, listing the `MI_SMG01_*` assets as
   unexpected (safe, but blocking). Merge before the next pack build, or build from a spec that includes SMG01.
7. **ASSET_LIST row** to add on main (text in the W6 stage summary).
8. **Lock `GunLib`** is still recorded from the W4 fix round (no gunlib edits in W5 / W6); release it if no other chat
   is editing gunlib.

## 10. Lessons for the next guns (carbine, sniper, long rifle)

- **A skeletal component with physics bodies takes its bounds from the physics asset.** Any moving part that leaves
  the rest box (a folding stock, a bipod) needs a no-collision, no-mass envelope in the body, or the dropped gun culls
  and picks LODs on the wrong radius. Measure it in Unreal with the part moved (U7).
- **Planar normal flattening must test for curvature.** A region whose normals follow a smooth field is curved:
  smooth-shade it. Flattening it gives 3-6 deg bands that judges read as a bent sheet.
- **Black dielectrics need light in the mirror direction to read at all,** and wear must be MIXED toward a worn grey;
  multiplied albedo steps of a few levels are invisible under the coat's specular. Measure textured vs clay before
  blaming the maps.
- **Fine polymer wear needs BC7 at the shipped default** (BC1 5-8 levels on a dark BC) and cannot ride the recolour
  detail map at half size: ship *Use Original Baked Colours* ON.
- **Derive recolour constants from the mirror, on main's bytes.** With `core.autocrlf` true a worktree checks the pack
  code out with CRLF, so constants derived there record shas that `maps_check` rejects on main. Keep the new derive
  script CRLF (as checkouts produce it) and run it from the mirror.
- **Hold the materials lock with a live pid** (`np_lock.py claim <owner> --pid <session pid>`): a claim from a
  short-lived process is "dead" at once and can be taken over; `run_build.sh` releases on exit, so re-claim after it.
- **Check a near-black v3 miss on the twin at 8 bits** before chasing it: it is usually the output's quantisation.
- **A class ABP on the pilot skeleton works across guns** with normalized inputs and per-gun angle tables; bones only
  some guns have belong on clips or linked layers.
- **Harness:** drop tests away from the game's DefaultPawn at the origin; compare LODs from a side view.
