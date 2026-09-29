# Card Shop Kit: G1 handoff (cloud to PC)

**Date:** 2026-09-29. **Status:** the Blender half of the G1 standards spike (spec 7.1 P1) is built and checked in a
cloud session. The Unreal half is written but has **never run**, because the cloud has no Unreal. One command on the PC
runs everything, then two checks need your eyes.

**Lock:** `CardShopKit` is held by agent `claude` (`WorkFiles/locks/cardshopkit.json`). The build step checks it.

## 1. What the cloud session did and measured

The run used Blender **5.0.1**, the pip `bpy` module. The house version is 5.2 and isn't available in the cloud, so the PC
re-runs the build with 5.2 and those exports are the ones that count. Full report: `g1/cloud_build_report.json`.

| Item | Result |
|---|---|
| 12 meshes: card, top-loader 35pt + 130pt, slab, filled slab, sealed pack, booster box S, box lid, sealed box, 1778 showcase, its glass, its door | Every mesh passes the house `qa_check` (26-130 checks each, `--require-uv1`, UCX present, budgets) |
| Kit checks (`build_csk.py`) | **111/111** (rebuild; 110 before): contain fits 38 (card in slab and top-loader, 36 packs in the box), shelf grids 15 x 3 (volume, cell, hull clearance), stacks 15, `.csk.json` hashes 10, deny scan, socket count |
| Showcase sockets | **33** (limit 40): 3 levels x (Level + 4 Compartment + 4 PriceTag), 2 doors, LED, 2 snaps, Seat |
| Slot maths pre-check | Unreal-style slots (imported Level socket + grid numbers) vs the Blender-computed `slots_ue`: **0.0001 cm** max error for all 6 classes. This is the G1 test 2 computation, pre-run on the exported sidecar |
| Self-tests (`test_csk.py`) | **11/11**, including negative cases: 0.1 mm pack overhang, too-small slot, overlap, hull intrusion, deny hits and false hits, atlas padding |
| Preview renders | Built only from the exported FBX + `.csk.json` + textures. Every face reads correctly: card back, pack back, slab label, card in slab, filled slab (corner colours in place, TOP at the top) |
| Placeholder art | Test-pattern faces + 3 atlases via the buyer tool `csk_pack_cards.py` + 6 plain textures |

**Found and fixed during the build**, each caught by a check:

- the box lid's print was 40 mm off (the dieline hinge reference);
- the pack's thin sealed edges had zero-area UVs (now each edge gets its own band, plus a new zero-UV-area gate on UV0 and
  UV1);
- the showcase posts, deck and base had coincident corners;
- the stack check itself was wrong, because the spec caps a stack by the shelf's clear height.

**Rebuilt from the reference sheets (same day, after the user's sheets 1-7 arrived).** Every G1 mesh now follows its
sheet; the notes and measurements are in `References/CardShop/REFERENCE_LOG.md`.

| Mesh | Sheet | What changed | LOD tris |
|---|---|---|---|
| Top-loader 35pt + **130pt (new)** | 2 | Rounded corners (R 3.5), boolean pocket, thumb notch 20.8 x 8.4 through the front skin | 228 / 96 / 28 |
| Slab + filled slab | 3 | Stepped rim, label and window recesses with a cross bar, shell seam groove, 4 side stacking lugs (render width 85.0) | 652 / 108 / 60 |
| Sealed pack | 4 | Lens-shaped pillow, 27 teeth, one pressed rib per tooth, flat seal strip, back fin seal | 1488 / 440 / 136 |
| Booster box S | 5 | Front die-cut window, centre divider (packs either side), lid = top + tuck-flap tab, printed inside as the header, display pose 100 deg | 196 / 84 / 68 |
| Box sealed (**new**) | 5 | Closed carton in a shrink-film shell | 136 |
| Showcase 1778 | 6, 7 | Oak cabinet on a recessed black kick, cream deck, full-depth shelves in thirds, 4 slotted standards with pins, LED channel | 3000 / 328 / 72 |
| Door | 6, 7 | Clamp + cylinder lock on the meeting edge (the right door is turned 180 deg so both locks meet at the centre) | 92 |

**Spec deviations, logged:**

- **Budgets:** pack LOD0 300 -> 1500 (the sheet's 27 ribbed teeth and fin seal need about 1.4k); every other mesh is
  inside its section 3 budget (showcase exactly 3000).
- **The card ships LOD0 only** (92 tris; the section 3 rule, 150 or fewer). The slab and box have real LODs again.
- **Showcase:** base kick 60 + oak 140 (was a 152 black kick base + 23 deck); shelves full depth (was 356 / 305).
- **Box dieline:** 440 x 305 (was 285): the lid's tab.
- **Not modelled yet:** the pack's Open / Strip / Wrapper states; the slab lugs' matching recesses (not visible).
- The fit tests count 0.1 micron as "touching", which only absorbs float32 vertex noise (about 0.004 micron).

**Build-speed fix:** island packing now uses bounding boxes (concave packing took about 10 s per call; a full G1
build is now under 10 s). An unwrap that folds faces onto each other retries at a tighter angle.

**Independent review of the Unreal scripts** (a separate agent checked every Unreal API call and the material and
transform logic against the armory's and the pipeline's proven scripts). No crash-level bug was found. Four fixes were
applied:

- the right door slid the wrong way;
- print UVs now sit 0.1% inside their tiles, so the tile pick never lands on a neighbour tile at an edge;
- `import unreal` comes first in two scripts;
- the materials step now writes its report even if an atlas index is missing.

One thing to watch in the art check: a 1-pixel ring of flat colour at a print face's edge, seen from a distance, would
be the mip seam of `frac()` sampling. If you see it, tell Claude; the fix is explicit-derivative sampling in the print
master.

## 2. On the PC

1. Pull the branch `claude/confident-meitner-ac6z3c`. Nothing new needs LFS: the art and exports are generated.
2. If Pillow is missing: `py -3 -m pip install pillow`.
3. Close any editor that has `CardShopKit.uproject` open, then in Git Bash:

   ```
   bash Scripts/cardshop/run_g1.sh
   ```

   It runs `selftest art build preview project import materials map verify` in that order and stops at the first
   failure. Each Unreal step is a fresh commandlet process, one at a time. Logs are in
   `WorkFiles/cardshop/g1/unreal/logs/`. You can re-run from a step with, for example,
   `bash Scripts/cardshop/run_g1.sh import materials map verify`.
4. If a step fails, commit `WorkFiles/cardshop/g1/` (the logs and JSON) and tell Claude. The Unreal scripts are
   first-run code, so a fix round is likely.

## 3. The G1 gate (spec 7.1): stop and show the user if any test fails

| # | Test | How it's checked | Pass |
|---|---|---|---|
| 1 | **Buyer art.** A plain one-texture material and a `csk_pack_cards` atlas both show correctly on card, pack and slab label | **You**, in `L_CSK_G1` (it opens at start-up). Look at the table in front of the case: row `ArtRows/Plain` (plain textures) and row `ArtRows/Atlas` (atlas cells) | On every face (cards, card backs, packs, pack backs, slab labels, filled slabs): **TL red, TR green, BL blue, BR yellow**, "TOP" at the top edge, nothing mirrored. The atlas row shows the right line name and cell number |
| 2 | **Sockets.** Slots seat 3 classes at 1 mm or less, with 40 or fewer sockets on the showcase | **Automatic**: `csk_verify.py` recomputes every grid slot in Unreal from the imported Level socket and compares it to `slots_ue`. It also checks every socket's place and rotation, and every placed actor | `verify.json` → `g1_test2_slots.passed = true` (Card, Slab, Pack required; all 6 classes are checked) |
| 3 | **Draws and sorting.** 200 socket-attached empty slabs vs 200 `_Filled` slabs batched in one instanced actor | **You**, in `L_CSK_G1_Stress`. See the steps below | The batched half costs about 1 draw per LOD; the attached half is about 600 draws (spec 4.5). Through the glass from the customer side, no slab window draws in front of the glass or over its neighbour |

Test 3 steps:

1. Open `/Game/CardShopKit/G1/Maps/L_CSK_G1_Stress`.
2. In the Outliner, select every actor in `Stress/Filled_ToBatch`. Then **Tools → Merge Actors → Batch** (instancing) and
   merge them into one actor.
3. Type `stat scenerendering` in the console. Frame the two attached cases (A, B), then the two batched ones (C, D).
   Note **Mesh draw calls** and the frame time from `stat unit` for each.
4. Walk to the customer side (+Y) and look through the front glass at the attached slabs. Check that no window flickers,
   pops in front of the glass, or hides its neighbour.

Also worth a look while you're in `L_CSK_G1`: the showcase, with S2 top-loaders holding cards, S1 slabs with cards plus
filled slabs, and two open boxes of 36 standing packs on the deck. The right-hand door is slid open by 42 cm. Nothing
should float, sink or clip.

## 4. After the run

Commit and push:

- `WorkFiles/cardshop/g1/`: the reports, `unreal/*.json` and logs. This is text, so the next cloud session reads it.
- `Assets/CardShopKit/CSK_G1.blend`, `Exports/CardShopKit/G1/**` and `Renders/CardShopKit/G1/*` (LFS).
- Your notes on tests 1 and 3: the draw-call numbers and what you saw. A line in this file under "Results" is enough.

Then tell Claude "G1 results are pushed". Next is P2 (brand art with your card illustrations) once G1 passes, or a fix
round if it doesn't.

## 5. Files

| Path | What |
|---|---|
| `Scripts/cardshop/build_csk.py` | Blender entry: build, `qa_check`, export, `.csk.json`, kit checks, save the `.blend` |
| `Scripts/cardshop/csk_lib/` | `spec.py` (numbers, classes, LOD rule, deny list), `shapes.py` (pure-Python face builder), `geom.py` (the G1 items), `mesh.py` (Blender mesh, UV tiles, UV1, hulls), `fit.py` (seating and fit maths), `slots.py` (`.csk.json`) |
| `Scripts/cardshop/test_csk.py` | Self-tests (system Python) |
| `Scripts/cardshop/tools/csk_pack_cards.py` | The buyer atlas tool (ships with the kit) |
| `Scripts/cardshop/art/g1_placeholder_art.py` | G1 test-pattern art (not for sale) |
| `Scripts/cardshop/preview_g1.py` | Preview renders from the exported files |
| `Scripts/cardshop/unreal/` | `make_project.py`, `csk_import.py`, `csk_materials.py`, `csk_map.py`, `csk_verify.py`, `csk_common.py` |
| `Scripts/cardshop/run_g1.sh` | The PC runner |
| `Scripts/cardshop/cloud/bpy_run.py` | Cloud only: runs a Blender script under the pip `bpy` module |

## Results (fill in after the PC run)

| Test | Result | Notes |
|---|---|---|
| run_g1.sh | | |
| 1 Buyer art | | |
| 2 Sockets (verify.json) | | |
| 3 Draws: attached / batched | | |
| 3 Sorting through the glass | | |
