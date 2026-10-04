# Basic katana + saya: final report (2026-10-03)

The user asked for "a basic katana (do the same thing [a study, then develop it, using workflows]). also a sheathe for
it." Delivered:
- `SM_Katana` and `SM_Katana_Saya`, exported through `Scripts/pipeline`, verified in Unreal 5.8.3 on the exact shipped
  bytes, and added to the pack's colour system.
- The showcase folder `showcase/Katana/`.

There is no user reference image. The study's design sheet (`KATANA_DESIGN_SHEET.png`) and spec
(`katana_spec.json`) are the reference.

| | |
|---|---|
| Exports | `Exports/Katana/` (FBX + sidecars + `Textures/` + `README.md` + `MATERIALS_README.md`) |
| Sources | `Assets/Katana/Katana.blend`, `Assets/Katana/Saya.blend` |
| Scripts | `Scripts/Katana/` (`run_katana.sh`, `run_saya.sh`, `katana_recolour.py`), `Scripts/unreal/materials/maps/derive_constants_katana.py` |
| Renders | `Renders/Katana/`, `WorkFiles/katana/KATANA_DESIGN_COMPARE.png`, `SAYA_DESIGN_COMPARE.png`, `showcase/Katana/` (18 images) |
| Shipped bytes | `SM_Katana.fbx` sha256 `114c79f43f66...`, `SM_Katana_Saya.fbx` `d97bd9b74b30...` |

## 1. The study in short

`KATANA_STUDY.md`, `katana_spec.json`, `KATANA_DESIGN_SHEET.png` and `KATANA_BUILD_PLAN.md` define a plain uchigatana.

**Blade.**
- Shinogi-zukuri with an iori-mune, no hi.
- Nagasa 705 mm, sori 17 mm. The mune is **one circular arc** (R 3663.1 mm) tangent to the tsuka axis at the
  mune-machi, so drawing from the saya is a pure rotation about one point.
- Motohaba 31 mm, sakihaba 22 mm; kasane 7.0 to 5.0 mm; chu-kissaki 38 mm.
- A quiet ko-notare hamon with a ko-maru boshi.

**Fittings.**
- Brass habaki (28 mm) and seppa.
- Plain round blackened-iron tsuba (76 mm); iron fuchi and kashira.
- Lozenge menuki of our own design; bamboo mekugi.

**Tsuka.** 265 mm, black hira-ito over white same in the classic hishigami diamond pattern, built as **real
geometry**: 9 crossings per face, pitch 26.78 mm, omote and ura offset half a pitch.

**Saya.**
- Black roiro lacquer, concentric with the blade arc: 40 x 27.5 mm at the mouth, 35 x 23 mm at the end.
- Horn koiguchi, kojiri and kurikata (80 mm from the mouth) with a brass-lined hole.
- No sageo and no kaeshizuno.

**Sheathed.** The seppa sits 0.3 mm off the mouth, the habaki is a friction fit, and the tip stops 10 mm short of the
cavity end.

The build plan sets the frames and sockets (8 on the katana, 4 on the saya), the budgets (25k / 12k ceilings), the
slots (3 + 2), the collision (6 + 5 hulls) and the LOD screen sizes (1.0 / 0.35 / 0.15).

## 2. Builds (katana builder, saya builder)

**Katana** (`Scripts/Katana/build_katana.py` + `katana_*.py`):
- True shinogi-zukuri sections lofted on the mune arc, with a real yokote crease.
- Bevelled fittings.
- Tsuka-ito as two crowned ribbons with over/under crossings, a fold ridge at each hineri, and hishigami lift at the
  edges.
- Per-texel painted maps from each face's parametric attributes; AO baked in Cycles.
- Authored LODs; 6 hulls; 8 sockets.

**Saya** (`build_saya.py` + `saya_*.py`):
- Fitted to the shipped katana bytes: every katana point is mapped to arc coordinates, where the draw is a straight
  shift, so the Snow Flower swept-support method applies unchanged.
- Closed solid body with a real cavity; horn fittings; a real see-through kurikata hole.
- Gloss lacquer with subtle wear in roughness.

The builders' own Unreal checks passed. Their reports are `katana_report.json` and `saya_report.json` (both rewritten
at the final export).

## 3. Review findings and what was done

Two independent reviewers (Unreal + fit, and craft) passed both assets with fixes. Every major and every minor item
was handled. The fixes are in `Scripts/Katana/`; the pre-fix scripts are kept in `final/script_backups/`.

| # | Finding (severity) | Fix | Evidence |
|---|---|---|---|
| 1 | Collision holes: consecutive chord hulls left 6-9 mm (katana) and 17-30 mm (saya) gaps; 1.5 % / 12.5 % of the surface outside (major) | Hulls built from **dense surface samples** (<= 1 mm LOD0, <= 2 mm LOD1/2), with neighbouring chords overlapping by 3 mm of arc. A build gate checks an independent jittered 0.5 mm LOD0 sampling plus every LOD's vertices against the hull union (raises on failure). Collinear and coplanar hull vertices dissolved | Build gate 0 outside. **On Unreal's stored hulls: 0 of 300,000 LOD0 samples outside, both assets** (`UnrealVerify_Final2/kv_diag_hullsurf.json`) |
| 2 | Hamon read as a flat sharpening bevel (major) | 2 mm nioi transition with a smooth falloff and a little mist into the ji. Low-frequency mottling in the hardened zone (roughness 0.28-0.44; BC +-3-6 % at 3-8 mm). Wave +-1.5 mm plus an irregular secondary ripple. Hamon frosted: brightest and roughest | `Renders/Katana/katana_hamon.png`, `katana_kissaki.png` |
| 3 | Blade far too dark: ji linear 0.16, below polished steel's F0 (major) | Ji `#A7ACB0` rough 0.10; shinogi-ji/mune burnished `#B9BDC0` rough 0.05; hamon `#D6D9DB` rough 0.36 | Shipped ji BC sRGB (185, 189, 192) (was `#6E757B` = 110, 117, 123); `katana_hero.png`, `showcase/Katana/Katana_hero.png` |
| 4 | Steel atlas: 46 % empty, blade 28.9 px/cm, hidden seppa faces at 3.6x (major) | Re-pack by visibility: blade = reference, split into two islands per face at s 334 mm (a station of every LOD); fittings 1.9x, tsuba 1.25x, hidden faces 0.12-0.3x | **Blade 54.8 px/cm** (target 55); seam continuous (BC within 1 level, ORM within 3) |
| 5 | Kashira end: 15 mm open band of same, loose cord slivers, two "rubber bumper" band stubs (major) | Wrap phase compressed (C1-smooth) below the last ura crossing, so the wrap ends with an omote crossing exactly at the kashira lip; the mirror case at the fuchi. Kashira band dropped (reviewer's option B) | `fbx_sheet_tsuka2x.png`; the measurer reports the lip half-crossings apart from the spec's 9 + 9 |
| 6 | Grey stains in the windows from a lateral dark-paint band (minor) | Cord-dark paint only under each ribbon's own footprint + 0.5 mm (ray-cast from the core); edge folds 12.4 mm so neighbouring folds never intersect | `katana_tsuka.png` |
| 7 | Cords like thick rubber straps; blobby twists; seatbelt weave (minor) | Ribbon 1.25 mm (was 1.4) with a flatter crown; upper cord pinched to 76 % at the hineri; weave relief halved, finer chevrons (1.3 mm) | `katana_tsuka.png` |
| 8 | Lacquer shading facets (minor) | Custom split normals from the analytic superellipse normal on the outer skin (rounds, grooves and faces keep their own) | `saya_sheathed_side.png` |
| 9 | Mouth read as a solid black disc; horn grain like brushed metal (minor) | Polished mouth face (x1.45, rough 0.20), pocket much darker (x0.40, rough 0.62); horn grain half contrast, shorter streaks | `saya_mouth.png`, `saya_lod0_mouth.png` |
| 10 | Kurikata like a rubber grommet (minor) | Near-vertical sides, crisp 1 mm shoulder, nearly flat top (0.8 mm crown), squarer plan (corner r 2); 30 x 11 x 9 envelope kept | `saya_kurikata.png` |
| 11 | Mekugi read as a brass rivet; menuki a shiny gold bean; habaki streaks (minor) | Mekugi `#8A6E45` rough 0.62 metal 0 with end-grain rings, moved to the Fittings slot (on the Grip slot it would have recoloured with the ito). Menuki `#8C6E3C` rough 0.35. Habaki streak relief halved | `katana_tsuka.png`, `katana_habaki.png` |
| 12 | Kurikata an open shell, breaking ray-parity tests (minor) | Every boundary loop capped with a fan facing into the body; constrained fill for the hole annulus | Unreal read-back: 0 open edges at every LOD (`kv3_fit.json` TOPO) |
| 13 | README: Unreal flips Y (omote/kurikata at +Y in Unreal) (minor) | Stated in `Exports/Katana/README.md` section 3 | Saya Unreal bbox Y -1.37..+2.25 |
| 14 | README import line incomplete; "straight slide collides after 1 cm" (minor) | Convert Scene ON, Convert Scene Unit ON, Force Front X OFF, Uniform Scale 1.0 added; "about 3 mm" | Unreal: first collision at 2.8 mm |
| 15 | Steel ORM imported as a normal map group (minor) | README says Texture Group World for every ORM. The new steel ORM is no longer auto-detected as a normal map | Pack import and verify import: all three ORMs TEXTUREGROUP_World |
| 16 | Draw must follow the arc (note) | README + MATERIALS: rotate about `DrawPivot` Y, 11.04 deg to the mouth, tangent to `Mouth` -Z | Unreal: 223 steps, 0 intersections, 9 pairs |
| 17 | LOD2 tsuka shell bake smears (minor, invisible at its 5.8 m switch) | Not rebaked (the reviewer's "if rebaked for other reasons") | Section 7 |

### Revisions to the spec

The craft review's colour and hamon values replace the study's for the paint. They live in `Scripts/Katana/katana_spec.py`
(`REV_MATERIALS`, `REV_HAMON`, `ITO_EDGE_W`, `CORD_THICK`, the wrap-end warp). `katana_spec.json` and the design sheet
are left as the study wrote them, so the sheet still shows the old blade grey and the open band at the kashira.

The saya lacquer is `#1D1D1F` instead of `#0C0C0D`. Two reasons:
- `#0C0C0D` sits below `M_Fabric_Master`'s black floor (linear 0.01), and the derive gate `colour_above_floor`
  refuses it.
- It is also darker than any real black lacquer's albedo.

## 4. Verification on the final bytes

| Check | Result |
|---|---|
| `qa_check` | katana 110 checks, saya 88: pass |
| Measured (`katana_measured.json`, `saya_measured.json`) | Every key dimension equals the spec within 0.01 mm; ito 9 + 9 crossings within 0.56 mm of the spec z, pitch 26.77; saya 721.79 on the arc, 40.0 x 27.5 mouth, kurikata 80.0 / 9.0 proud |
| Design compare (IoU at the sheet's scale) | Katana: side 0.985, top 0.963, end 0.991, tsuka 2:1 0.981, kissaki 3:1 0.928 (the sheet crop shows a cut blade end). Saya 0.990 / end 0.988; sheathed 0.986 / end 0.992 |
| Fit (`saya_fit_verify.json`, 9 LOD pairs) | 0 intersections; blade clearance >= 0.495 mm; habaki 0.1105-0.1111 mm; hilt >= 0.578 mm; 0 enclosure failures; arc draw clean; seat gap <= 0.35 mm; walls 2.32 mm (pocket) / 3.64 mm (body) at LOD0, >= 2.22 at every LOD; tip 10.0 mm from the cavity end; sockets within 0.001 mm; katana bytes = shipped |
| Unreal 5.8.3 (`UnrealVerify_Final2`, `/Game/KatanaVerify/Final_1003c`) | See the list below |

**Unreal 5.8.3 runs.** Pass A imported the meshes; pass B read them back in a second fresh process; pass C rendered in
a third. One commandlet ran at a time, none was left running, and every result is on the exact bytes.
- Triangles 20368/6824/1724 and 7412/2210/954, equal to Blender's.
- 6 + 5 hulls.
- 8 + 4 sockets with 0.000 cm and 0.000 deg error, scale 1, owned by the asset, no extras.
- Screen sizes 1.0 / 0.35 / 0.15, lightmap index 1, Nanite off, 3 + 2 slots.
- 9 maps at 2048 with their flags.
- Attach to `Holster` gives (0, 0, -13.83) cm, rotation 0, scale 1. The katana's sockets composed through it are
  within 4e-15 cm.
- Fit on the read-back geometry: 0 intersections in 9 pairs, habaki 0.110-0.111 mm, seat 0.300-0.303 mm, tip 10.000 mm.
- Arc draw: 223 steps of 0.05 deg, 0 intersections.
- Depth captures from 4 sides: 0 uncovered pixels.
- Hull surface: 0 of 300k samples outside.
- No warnings or errors from the assets.

The earlier finaliser run's Unreal check (`UnrealVerify_Final`, 05:35) was on the bytes before the last re-export.
It was superseded by this run.

## 5. Pack colours (step 2)

- Materials lock `katana-wf`. `material_spec.json` gains items `Katana` and `Katana_Saya`: 10 instances
  (`MI_Katana_Blade`, `_Fittings` and `MI_Katana_Saya_Fittings` on `M_Steel_Master`; `MI_Katana_Grip` on
  `M_Fabric_Master` with Metal From ORM; `MI_Katana_Saya_Lacquer` on `M_Fabric_Master`; each with its `_Base`), plus a
  `changes` entry.
- **Additions only:** the spec with the katana entries removed equals `final/materials/material_spec_before_katana.json`.
- Recolour maps: `Scripts/Katana/katana_recolour.py` writes the 1024 16-bit linear Detail16 maps and
  `recolour_maps.json`. To keep the master's keep ramp clean, the grip BC holds no texel between the ito (about 0.01)
  and 0.4 linear luminance.
- Constants: `Scripts/unreal/materials/maps/derive_constants_katana.py`. Every gate passes for both parts: default
  equals the v1 contract at every mip, guards inactive, mip drift within 2 %. Shipped colours: ito `#19191B`, lacquer
  `#1E1E20`, Lightest `#CBCBCB`.
- **Build:** `NP_OWNER=katana-wf bash Scripts/unreal/materials/run_build.sh katana_1003 maps_check import_meshes
  import_textures clean build assign verify render`.
  - Preflight and maps_check OK; every step `passed=True`; **0 compile failures, 0 errors**.
  - Verify gates functions, masters, instances, meshes, textures, dependencies and accounting all true.
- **Every other entry unchanged:** dump `senbon_1003b` vs `katana_1003` (`final/materials/materials_dump_compare_*.json`).
  - Instances 59 -> 69, meshes 21 -> 23, textures 103 -> 114: only katana entries added; none removed or changed.
  - Masters (3) and functions (5) unchanged; node layout identical.
  - No pack build has run since (checked at resume).
- The lock was released; `np_lock.py status` = null.
- **UV-plane base-colour captures.** The Grip captures were split by the master's keep weight, because the pack
  analyser has no Metal From ORM branch (`final/materials/fin_keep_split.py`, `uv_capture_keep_split_katana.json`).
  - Ito: cord texels vs the twin p99.9 1 level (default and white, red and black).
  - White and red keep the detail: Spearman 0.987 against the detail map. The default near-black capture holds only
    9 levels, so Spearman against it is tie-bound.
  - Same texels: black identical to the default. White and red differ on about 1,000 edge texels (0.35 % of the same),
    where BC1 compression drops the boundary under the keep ramp.
  - Lacquer: all captures within 1 level of the twin; white and red pass v3. Black fails v3 Spearman (0.53), the pack's
    known near-black trait (pack gap A6.2, as on the kunai grip and the senbon wrap).
  - The earlier run's whole-atlas analysis (`uv_capture_analysis_katana_only.json`) flagged the Grip only because its
    kept texels show BC1 block error against the PNG twin.
- PS instructions: steel 165, grip 235, lacquer 227.

## 6. Showcase

`showcase/Katana/` holds 18 images from the studio script (`.claude/worktrees/cardshop-build-integration-5227b4/Scripts/showcase/studio.py`,
run read-only): `Katana_*`, `Katana_Saya_*` and `Katana_Sheathed_*`, each with hero, hero_dark, front, side, back and
top. They are rendered from the final maps (05:49-05:51, after the 05:48 maps). There is one row in
`showcase/ASSET_LIST.md` under "Throwables and weapons". Logs are in `final/showcase_logs/`.

## 7. Known gaps (honest)

**Look**
- **No blind-test judge has been run.** The hamon's visibility depends on lighting: it reads in the raking and kissaki
  renders, and is subtle in the 3/4 studio hero. The blade normal map is flat; there is no hada.
- In the tsuka renders, a tiny dark notch is visible where two cords meet near the omote menuki crossing.
- The LOD2 tsuka shell bake is slightly soft, with specks, and was not rebaked. It is invisible at its 5.8 m switch.

**Spec and design sheet**
- `katana_spec.json` and the design sheet still carry the study's colours and the open band at the kashira. The
  revisions live in `katana_spec.py`, and the tsuka 2:1 IoU against the sheet is 0.981 because of the closed wrap end.
- The edge folds are 12.4 mm wide, against the spec's 16 mm, so neighbouring folds never intersect.
- The hineri is a lifted, pinched upper cord with a fold ridge, not a full 180-degree ribbon twist. The hishigami are
  implied by the lift.

**Textures and materials**
- The steel atlas stays 2048 square (blade 54.8 px/cm). The plan's 4096x1024 atlas was not taken.
- Grip recolour: a fringe about 0.1 mm wide at the window edges under very light or saturated ito colours (BC1 plus
  the keep ramp). Saya lacquer black recolour v3 Spearman 0.53 (pack-wide near-black trait).
- The mekugi sits on the Fittings slot, so Steel Tint tints it with the brass.

**Unreal and game integration**
- Unreal's own rebuild of hull `UCX_SM_Katana_LOD0_02` drops one of its 24 vertices: Hausdorff 1.77 mm to the
  shipped hull. The hull union still contains every LOD0 surface sample (0 of 300k outside), so collision is complete.
- LOD screen sizes 1.0 / 0.35 / 0.15 are the plan's proposal; the 1440p LOD-pop measurement was not run. There is no
  LOD3.
- `CenterOfMass` includes an assumed tang that is not modelled.
- The skeleton sockets (`Katana_R` on `hand_r`, `Saya_L` on `pelvis`) are not authored: they need the user's go in the
  game project.
- No mobile, Substrate or forward-shading test of these instances.

**Housekeeping**
- The cutaway renders do not fill the cut faces.
- The Unreal check content `/Game/KatanaCheck/*` and `/Game/KatanaVerify/*` remains in the ShurikenValidation project.
- Heavy scratch in `WorkFiles/katana/build`, `saya_build` and `Unreal*/` is not for git. `KATANA_DESIGN_SHEET.png`
  (20 MB): the main chat decides whether to commit it.

## 8. Open questions for the user

1. Sageo: a separate rigged or simulated cord later, or none? The kurikata hole is ready.
2. A bo-hi (groove) variant?
3. Carry: left hip, edge up (the default `BeltMount` + `Saya_L` on `pelvis`), or a back carry?
4. Go-ahead to author `Katana_R` / `Saya_L` on the player skeleton in the game project.
5. A blind-test round and an LOD-pop measurement before release on Fab?

## 9. Process notes

- **Resume.** The finaliser was paused mid-way and resumed. Already complete and kept:
  - every fix, the re-export (05:40-05:41), the fit verify and measurements on those bytes;
  - the maps re-run (05:48, paint only) and the recolour maps and constants;
  - the pack build `katana_1003` (05:49-05:55);
  - the showcase images (05:49-05:51).

  Redone or added at resume:
  - the Unreal verify on the final bytes (the earlier one predated the re-export);
  - the keep-split capture analysis;
  - the docs and the ASSET_LIST row;
  - the frozen proof.
- **Frozen check.** `check_exports_frozen.sh` output at resume is identical to the builders' start
  (`build/frozen_at_start.txt`), and identical again at the end. Its DIFF lines (Kunai, BlackHat, ...) are other chats'
  pre-existing changes. Every non-Katana file under `Exports/` is byte-identical between resume and end
  (`final/resume/`).
- **Locks.** The Katana asset lock was re-claimed at resume (the recorded pid was dead) and released at the end. The
  materials lock was free at resume and is free now.
- **Processes.** No Blender or UnrealEditor-Cmd started here is left running.
