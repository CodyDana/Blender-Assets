# Card Shop Kit: cloud -> local handoff

For a local Claude session on the user's PC, taking over from the cloud session (which may stop at any time when its
credits run out). Everything the cloud did is committed on branch `claude/confident-meitner-ac6z3c`. A background job
in the cloud commits the family builders' progress every 10 minutes (commits titled "checkpoint").

**Read first:**
- `CLAUDE.md` (the repo rules);
- `WorkFiles/cardshop/CARDSHOP_KIT_SPEC.md` (the kit spec);
- `References/CardShop/REFERENCE_LOG.md` (all 37 reference sheets, 0-36, with notes and decisions);
- `Scripts/cardshop/csk_lib/FAMILY_GUIDE.md` (how a family is built).

## 000. Showcase room (2026-09-30)

`L_CSK_Shop` (spec 5.2), built by code from the imported kit: `bash Scripts/cardshop/run_shop.sh` (project, shop,
capture; the G1 run's import + materials first). 14 x 8 x 3 m from the J1 shell: a sales floor (counter line with the
POS devices, lit wall cases, oak wall units, towers, the wall slab case, two gondola runs, slatwall with hooks, box tier,
wire rack, card tables, a countertop case, a play area) and a back room (warehouse racks, workbench, hand truck, bins,
cartons); 2,489 actors, every case and shelf stocked from its own slot grids. Lighting: 600 panels + rect lights, a
track over the counter line, pendants, daylight through the storefront, Lumen with hardware ray tracing (the project is
now DX12 SM6, like ArmoryLab), exposure fixed at EV100 7.6. Ten cameras; renders in `Renders/CardShopKit/Shop/`.
It is the editor start-up map. Lessons: software Lumen had no mesh cards in short offscreen runs (black ceiling), and
thin wide meshes get a two-sided, finer distance field at import (`csk_import.thin_distance_field`). The offscreen
editor segfaults at shutdown after writing the captures (harmless so far).

## 00. Local session on the PC (2026-09-29, branch `claude/cardshop-build-integration-5227b4`)

Steps 1-6 below are done. **The G1 Unreal run passes end to end** (`bash Scripts/cardshop/run_g1.sh`, UE 5.8, verify
in a fresh process, `g1/unreal/verify.json`): all 179 meshes imported and verified (LODs, LOD0 tris, sockets,
hulls, screen sizes, an MI on every slot), G1 test 2 (slot seats <= 0.0001 cm for all 6 classes), both levels.
**Next: the user's manual G1 checks (tests 1 and 3, `G1_HANDOFF.md` section 3), then the design review.**
- **Unreal drops tiny triangles:** the first run lost 4 LOD0 tris on `SM_CSK_PriceGun` (Unreal cuts any triangle of
  area <= 0.005 mm^2). The build now fails such triangles on every LOD (`mesh.small_triangles`); fixed at the cause
  on the price gun (print-head frame top 97, back past the bevel) and the filled top-loader's LOD2 (print recess
  0.2 deep on LOD2).
- **Nothing was left uncommitted** by the cloud: all 12 modules and reports were in its last commit.
- **Combined build in Blender 5.2: `CSK_BUILD PASSED`**, 179 meshes, kit checks 1359/1359, self-tests 11/11
  (`g1/pc_build_report.json`). The 12 G1 meshes have exactly the cloud's triangle counts. No class-code conflicts
  (16 family classes, none clashing).
  - **The 5.2 difference:** the exact boolean appends an empty material slot per cutter (5.0.1 did not), which
    failed `material_assigned` on every mesh with a cut. Fixed in `mesh._apply_boolean`.
- **a_cases vs sheets 16-18:** A2 bay-door pulls made vertical; A6 sides made oak behind aluminium posts; the rest
  matches or is a question (`families/a_cases.md`, "Checked against the sheet pictures"). a_shelving had already been
  compared with its PNGs by its builder.
- **Winding check:** it now covers every `_Glass` / `_Lid` / `_Door` / `_BayDoor` part (35, was 12) with a per-shell
  ray-parity test (`mesh.check_outward_rays`) that is right for concave parts; negative-tested.
- **Unreal materials:** an `MI_CSK_G1_<Part>` for each of the 64 new slots (79 slots, 93 MIs with the variants),
  on the three G1 test masters; print slots use the plain test-pattern textures. All 179 meshes are in
  `csk_common.MESHES` (`G1_MESHES` + `FAMILY_MESHES`), so import, materials and verify cover them.
- **`run_g1.sh`** now finds the repo from its own path, so it runs from a worktree too.
- **Questions:** all 66 in `WorkFiles/cardshop/OPEN_QUESTIONS.md`, with recommendations.

## 0. Latest status (cloud session ended here, out of credits)

**The family-build workflow FINISHED.** All 12 families report a passing build of their own keys: **167 new meshes**,
no `qa_check` failures, none over budget. Each family's report, with its deviations, anything not built and its open
questions, is `WorkFiles/cardshop/families/<family>.md`.

**Next, in order:**
1. **Commit anything left over.** Run `git status`. The h_backroom / ij_shell modules and reports may be uncommitted
   if the cloud's auto-checkpoint missed them.
2. **Combined build of ALL items in Blender 5.2** (never run yet; each family was only built on its own). It should end
   `CSK_BUILD PASSED`. Watch the cross-family kit checks (contain fits, level grids) and duplicate class codes: the
   loader keeps the first `CLASSES` entry.
3. **Check a_cases and a_shelving against their sheet PNGs (16-21).** Those two builders started before the PNGs were
   on disk. The other 10 families had the images.
4. **Unreal materials:**
   - about 60 new material slot names (listed in the family reports), each needing a material instance in
     `Scripts/cardshop/unreal/csk_materials.py` (`build_instances` + `SLOT_DEFAULT`);
   - add the new meshes to `csk_common.MESHES` if they should go through the Unreal import;
   - some builders used names outside the part-before-size pattern the build's winding check expects (a_cases says
     so); check that the Glass / Lid / Door winding check actually covers them.
5. **Answer or collect the builders' open questions** (about 70, in the reports) for the user.
6. **Then the G1 Unreal run** (`run_g1.sh`) and the user's design review.

## 1. State at handoff

**Done and pushed:**
- The G1 set, rebuilt from sheets 1-7 (12 meshes, every one passes `qa_check`, 113/113 kit checks, 11/11 self-tests):
  card, top-loaders 35pt and 130pt, slab and filled slab, sealed pack, booster box S with its lid and the sealed box,
  and the 1778 showcase with its glass and door. `WorkFiles/cardshop/G1_HANDOFF.md` has the details and the PC steps
  for Unreal.
- All reference sheets 0-36 in `References/CardShop/` (plain git), logged with hashes. The user accepted every conflict
  pick in the log. **J4 (scale figure) is dropped**: the user uses the UE mannequin.
- The family infrastructure:
  - `csk_lib/fam_<family>.py` modules auto-register in `geom.ALL_ITEMS`;
  - `tools/csk_shot.py` renders an exported FBX for comparison with its sheet.

**In progress when the cloud may stop: the family build.** A workflow was building 12 families, 2 at a time, each
touching only its own module and report. A family is **done** when both exist:
- `Scripts/cardshop/csk_lib/fam_<family>.py`, with its `ITEMS`;
- `WorkFiles/cardshop/families/<family>.md`, its report ending with a passing build.

A module without a report, or a report that says the build failed, is **unfinished**: finish it, don't restart it.

| Family | Spec rows | Sheets |
|---|---|---|
| a_cases | A2, A3, A4, A5, A6 | 16, 17, 18 (+6, 7) |
| a_shelving | A7-A13 | 19, 20, 21 |
| a_display | A14, A15, A16 + `SM_CSK_WallUnit_Oak` (1200 x 400 x 2100, budget 1500) | 22, 23, 36 |
| b_pack | B1 Open/Wrapper/Strip, B2 L + lid, B3, B7 | 4, 5, 10, 12 |
| b_ship | B4, B5, B6 | 11, 12 |
| c_retail | C1 Small, C2, C3, C4, C5 35pt_Filled, C6, C7, B8 (8 retail meshes) | 1, 2, 8, 12 |
| de_storage | D2, D4, E1, E2 | 3, 9, 13 |
| e_play | E3, E4, E5, E6 | 14, 15 |
| fg_counter | F1, F2 (+ Folded), G1, G11 (+ Flat) | 24, 25, 27 |
| g_devices | G2-G10 | 26 |
| h_backroom | H1-H7 | 27, 28, 29 |
| ij_shell | I1-I5, J1, J2, J3 (no J4) | 30-34 |

To see what is finished: `ls Scripts/cardshop/csk_lib/fam_*.py WorkFiles/cardshop/families/*.md`, then read each
report.

## 2. How to continue on the PC

**Blender 5.2** replaces the cloud's pip `bpy` 5.0.1. Commands (Git Bash, from the repo root):

```
B="C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
"$B" -b --factory-startup --python Scripts/cardshop/build_csk.py -- --no-save --items <keys> --out <scratch> --report <scratch>/r.json
"$B" -b --factory-startup --python Scripts/cardshop/tools/csk_shot.py -- OUT.png <scratch>/<Mesh>.fbx --view 34 --samples 16
py -3 Scripts/cardshop/test_csk.py
```

`FAMILY_GUIDE.md` shows the cloud form (`bpy_run.py`); on the PC, call `blender.exe` as above instead.

1. **Rebuild everything in 5.2 first:**
   ```
   "$B" -b --factory-startup --python Scripts/cardshop/build_csk.py -- --no-save --report WorkFiles/cardshop/g1/pc_build_report.json
   ```
   Compare it with `WorkFiles/cardshop/g1/cloud_build_report.json`. Triangle counts should match within a few. Fix
   any 5.2 differences, such as an API rename, or a budget tipped over by a boolean. The showcase sits exactly on its
   3000 budget, so give it headroom if 5.2 adds triangles.
2. **Finish the unfinished families.** Use one session per family, or a workflow, with the builder brief below.
   Families never edit shared files, so they can run in parallel.
3. **Review every family against its sheet PNGs.** Render each item and put it side by side with the sheet: the
   user's bar is "to the T". Some families were built before the sheet PNGs were on disk (their builders worked from
   the log's notes), so check those most carefully.
4. **Integrate:**
   - a full build of all keys ending `CSK_BUILD PASSED`;
   - collect every new material slot name from the reports and add an instance per name in
     `Scripts/cardshop/unreal/csk_materials.py` (`build_instances` + `SLOT_DEFAULT`);
   - add the new meshes to `csk_common.MESHES` when they should go to Unreal;
   - update `G1_HANDOFF.md` / the spec deviations;
   - commit.
5. **Unreal:** `bash Scripts/cardshop/run_g1.sh` (the G1 gate; see `G1_HANDOFF.md` section 3). It has never run yet.

## 3. The builder brief (the prompt the cloud used for each family)

> You are building one family of the Card Shop Kit (a Fab asset pack) in this repo. Family: `<family>`. Module:
> `Scripts/cardshop/csk_lib/fam_<family>.py`. Item keys prefixed `"<family>_"`.
>
> Spec rows to build: `<rows>` (`WorkFiles/cardshop/CARDSHOP_KIT_SPEC.md` section 3). Read each row fully, plus the
> section-3 notes and the section 4 rules they reference.
>
> Reference sheets: `<sheets>`. The PNGs are in `References/CardShop/`; their notes are in `REFERENCE_LOG.md`
> ("Sheet N notes").
>
> FIRST read `Scripts/cardshop/csk_lib/FAMILY_GUIDE.md` and follow it exactly: the parallel-safe file rules, frames,
> recipe, build/check/render commands, and the report. Then read `geom.py` (the G1 items are the worked examples) and
> `shapes.py`.
>
> Touch ONLY your module, your report `WorkFiles/cardshop/families/<family>.md` and your renders folder.
>
> Work item by item:
> 1. write it;
> 2. build it;
> 3. fix every qa or kit-check failure at its cause;
> 4. render it and compare it with the sheet;
> 5. fix what does not match.
>
> The bar: match the reference to the T with real geometry and crisp bevels, and invent nothing. Spec M numbers win;
> the picture wins over E numbers, and you log it. Stay within the budgets, or raise one with a logged reason.
>
> Finish with ONE build of all your keys that ends `CSK_BUILD PASSED`, then write the report.

Family-specific notes the cloud gave:
- **a_cases:** same look as the built full-vision showcase (aluminium posts, oak, black kick, glass as a separate
  mesh, doors as parts, levels + `solve_grid`). Sheet 18: build to the spec sizes, not the silhouette scale.
- **a_shelving:**
  - slatwall with real T-slot grooves, modelled efficiently;
  - wire rack with 5 decks;
  - box tier shelf with tapered oak sides and 10-degree shelves with 25 mm lips.
- **a_display:**
  - easels bent from 3 mm acrylic;
  - stands `SM_CSK_Stand_Card_1` (70 x 40 x 25) and `SM_CSK_Stand_Card_9` (70 wide x 120 long x 25, 9 cross slots at
    12 mm pitch).
- **b_pack:**
  - reuse `geom._pack_builder` ideas for Open (torn crimp, silver inside `M_CSK_PackInner`) and Strip;
  - Wrapper: a flattened creased pack (deterministic);
  - B2 L: reuse `geom._box_body` / `item_box_booster` with an L dict (190 x 76 x 140, 24 packs);
  - B3: telescoping lid 123 deep, visible base band 42, black tray;
  - B7: tuck box with the half-moon thumb cut.
- **b_ship:** 4 mm corrugated board, real flaps for the Open states, tape strips; Flat = knocked down (two panels).
- **c_retail:**
  - C5 Filled on the G1 top-loader shape (`geom._toploader_lod`);
  - B8 hang packages with a real euro-slot cut, two-tone print regions.
- **de_storage:**
  - D2: reuse `geom._slab_lod` with an 8 mm dict;
  - D4: foam insert (`M_CSK_Foam`);
  - E1: fold-over lid;
  - E2: telescoping lid, dividers, stadium hand holes.
- **e_play:**
  - binder with the spine band and 3 O-rings;
  - deck box: lid with the wave dip;
  - playmat: flat + rolled;
  - dice: d6 with pip dimples, d20, token.
- **fg_counter:** the counter per the sheet 25 notes (thick white top, bag shelf bay, drawer housing, grommets).
- **g_devices:** generic, our own shapes, no product silhouettes or logos; the drawer tray and the laptop lid are
  parts.
- **h_backroom:** rack with 5 levels; workbench mat as a print region; bin swing flap as a part; crumpled bag with a
  tied neck.
- **ij_shell:**
  - signs and posters with print regions;
  - shell modules 2000 x 150 x 3000 with black skirting;
  - door leaf on the hinge axis;
  - lights with the track head as its own mesh.

## 4. Waiting on the user (unchanged)

- The PC G1 run (`run_g1.sh`).
- ~~The USPTO screen of the brand names.~~ Deferred by the user (2026-09-29): the kit is private for now; trademarks are for later, before any sale.
- The card illustrations (`CARD_ART_BRIEF.md`).
- The publisher name (spec D9).
