# Family a_display: card tables, easels, risers, stands, oak wall unit (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_a_display.py`, 14 item keys prefixed `a_display_`. The spec rows are
CARDSHOP_KIT_SPEC.md 3.A A14, A15 and A16, plus `SM_CSK_WallUnit_Oak`, which has no spec row (the lead gave
1200 x 400 x 2100, budget 1500). The references are sheets 22, 23 and 36; I looked at each on disk and measured it.

**Build:** a single build of all 14 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD, and the kit
checks pass 16/16 (hashes, deny scan, socket count).

**Verification build:** the wall unit was built with the G1 class items (card, top-loader, slab, pack, sealed box).
The kit checks pass 90/90, including all 20 level grids (volume, cell, hulls, stacks).

**Extra check** (`scratchpad/fam_a_display/extra_check.py`, bpy). The kit build does not test fixed slots, so this
check does:
- It seats the real G1 item of every accepted class in every `Slot_NN` / `Item` socket (with the class seat offset)
  and runs a BVH triangle-intersection test against the fixture's LOD0 mesh, the neighbouring items and the closed lid.
- It sweeps the card-table lid from 0° to 70° in 1° steps against the body and 12 seated slabs.
- The run covers 334 placements and steps, and all pass. A negative test (items pushed 1 mm into their supports) is
  caught.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | Hulls |
|---|---|---|---|---|---|---|
| a_display_table_08 / _10 / _12 | SM_CSK_CardTable_{08,10,12} | 972/332/140, 996/356/140, 1020/380/140 | 1500 | PASS | 18 / 22 / 26 | 5 |
| a_display_table_lid_* | SM_CSK_CardTable_Lid_{08,10,12} | 200 / 84 / 12 | 200 | PASS | 2 | 1 |
| a_display_easel_slab / _card / _small | SM_CSK_Easel_{Slab,Card,Small} | 108 (LOD0 only) | 150 | PASS | 2 | 1 |
| a_display_riser_1 | SM_CSK_Riser_Slab_1 | 156 / 60 / 12 | 300 | PASS | 3 | 1 |
| a_display_riser_3 | SM_CSK_Riser_Slab_3 | 428 / 172 / 28 | **500** (spec 300) | PASS | 7 | 3 |
| a_display_stand_1 | SM_CSK_Stand_Card_1 | 68 (LOD0 only) | 150 | PASS | 2 | 1 |
| a_display_stand_9 | SM_CSK_Stand_Card_9 | 260 / 156 / 12 | **300** (spec 150) | PASS | 10 | 1 |
| a_display_wallunit | SM_CSK_WallUnit_Oak | 860 / 236 / 96 | 1500 | PASS | 29 | 7 |

**Sockets** (every mesh also has `Seat`):
- **Tables:** `Slot_01..NN`, numbered front row left to right, then the back row. Each is tilted 20° about X.
  `PriceTag_01..NN` sit on the felt in front of each slot. `Lid` is on the hinge axis. The lid mesh carries `Seat`
  and `Grip`.
- **Easels:** `Item`, rotated 75° about X, so the item leans back 15°.
- **Risers:** `Slot_01..02` and `Slot_01..06`, at 75° as the easels.
- **Stands:** the 1-slot has `Item`; the 9-slot has `Slot_01..09`. Both are at 75°.
- **Wall unit:** `Level_L1..L4` (L1 is the cabinet top at 900; then 1200, 1500, 1800), `Compartment_<L>_01..03` and
  `PriceTag_<L>_01..03`.

**Fixed-slot seating:**
- A leaning item rests on its bottom edge, so each socket is authored for one design item: tables use
  `SM_CSK_Card_Std`, stands `TopLoader_35pt`, risers and the slab easel `Slab_Std`.
- `data.slots.seat_offset_mm` gives each other accepted class's shift along the socket's local +Y. For example, on a
  table the Slab shifts +23 and the CardProt +6.8.

**Lid:** a hinge on X, 0-70°, `open_rot_deg` [-70, 0, 0], wired in `data.parts.Lid`.

## Deviations from the spec (and why)

- **A14 size:** built to the spec numbers ({640, 760, 880} x 460 x 914), as the log says. Sheet 22 reads about 1.4x
  wider. H = 914 is the top of the closed hood at the back.
- **A14 heights (E, from sheet 22 and scaled):**
  - The legs zone runs to 676, then an 85 oak tray band, with the felt deck 40 below the rim.
  - The glass hood is 153 tall at the back and 123 at the front (the top slopes down to the front).
  - The views disagree on the band: the front view reads about 60, the side view about 106.
- **A14 card holding:** sheet 22's plan shows a thin line across each row under the cards and a small tick under each
  card's front edge. These are built as a 3 mm black rail fin and small black stops. The card lies tilted 20°: its
  bottom edge is on the felt and its back face rests on the rail, 55% up the card.
- **A14 lid:**
  - The lid is a closed glass hood: top, front, sides and back, 6 mm glass.
  - It has two rear chrome hinges with real knuckles; the body has the fixed leaves and outer knuckles.
  - A small round lock sits on the hood back at the top right (sheet 22 side view).
  - The hood opens 0-70° (sheet 22 "about 70"; the spec's E was 0-80).
- **A14 materials:** the legs and apron use the slot `M_CSK_Steel` (white powder coat; the spec's "Frame (tint)"). The
  tray is `M_CSK_Oak`, the deck `M_CSK_Felt`, the glides, rail and stops `M_CSK_Base`, and the hinges and lock
  `M_CSK_Metal`.
- **A15 easel profile:**
  - Each easel is one 3 mm strip with real bends (inner radius 1): front lip, floor, rear leg, apex, then the back plate
    at 15°.
  - W, D and H hit the M sizes exactly.
  - The slab easel's lip (no call-out) is 16, read off sheet 23.
  - The ledge clearance is E: slab 7.5, card 6.5 (holders up to 6 thick), small 4.
- **A15 classes:** the slab easel takes Slab, the card easel CardProt (sheet 23 shows a card in a thick holder), and the
  small easel Card.
- **A15 crisp edges:** there is no bevel, because 150 is a LOD0-only budget.
- **A16 construction:**
  - Both risers are closed clear shells: solid blocks, as the log's "solid clear block".
  - Each slot is two slanted guide cheeks that stand 20 above the surface. Each cheek has a real groove the slab edge
    sits in, over its side lugs (sheet 23).
  - The slot pitch is 100.
- **A16 3-tier riser:** 3 steps of 2 slots (the log). Sheet 23's picture shows 2 rows of 3, but 3 slabs cannot fit in
  200 (3 x 85 = 255).
- **A16 budgets raised (logged in the module):**
  - Riser_Slab_3: 300 to 500, for 12 grooved cheeks.
  - Stand_Card_9: 150 to 300, for 9 real through-slots.
  - Stand_Card_9's LOD1 is 60% of LOD0, above the guide's 25-50%, because the slots define its silhouette. Its LOD2 is a
    plain block.
- **A16 stands:**
  - Solid blocks with through-slots, 12 deep, at 15°, 3.2 wide (horizontal). They take cards, penny sleeves and 35pt
    top-loaders.
  - A 76.2 top-loader overhangs the 70 block by 3.1 on each side.
  - The 9-slot is 70 x 120 x 25 with 9 slots at 12 pitch, the user-accepted pick.
- **Wall unit:**
  - An oak top plus 3 thick oak shelves (30) at equal spacing above the 900 white cabinet give 4 levels. The sheet 36
    notes' "4 shelves" counts the top, and the picture shows 4 loaded levels.
  - The cabinet has 4 doors in 2 pairs, 3 gaps, a recessed white plinth (100 tall, 30 back) and a 40 white top.
  - Small round knobs sit near each pair's meeting edges.
  - Materials are `M_CSK_Oak`, `M_CSK_Laminate` (white) and `M_CSK_Metal` (knobs).
  - It has 7 hulls (guide: 1-6): 2 side panels, the cabinet, the top and 3 shelves, so the level tests hold.
- **Tables:** 5 hulls (spec "5 + 1"): the base up to the deck and the 4 tray walls. The lid has 1.

## New material slot names

None. All slots already exist in the kit: `M_CSK_Oak`, `M_CSK_Felt`, `M_CSK_Steel`, `M_CSK_Base`, `M_CSK_Metal`,
`M_CSK_Glass`, `M_CSK_Acrylic`, `M_CSK_Laminate`. The table legs need a **white** MI of `M_CSK_Steel`.

## Not built

- **A14 lid stay:** sheet 22's open view (row 1) shows a curved chrome stay on the left, but the notes do not mention
  it. With a glass-sided hood, a stay needs its own sliding or linked part.
- **Wall unit cabinet interior:** the adjustable shelf on pins, the concealed hinges (sheet 36 detail) and the side
  panels' pin-hole rows are not built. The doors are closed parts of the body.
- **`Lock` socket for A14:** not in the spec row, so it is not added, though the lock is modelled.

## Open questions for the user

1. **A14 lid form:** sheet 22's closed views show a glass hood with glass sides, but its open view shows a single flat
   glass sheet. I built the hood (the notes). Keep the hood, or switch to a flat lid?
2. **A14 stay:** add the curved lid stay from sheet 22's open view as its own part?
3. **A14 lock:** sheet 22's side view puts the small lock at the back top corner, on the hinge side. Keep it there,
   move it to the front, or drop it?
4. **A16 3-tier riser:** keep 3 steps x 2 slots (the log), or follow the picture's 2 rows x 3 on a wider riser
   (about 300 wide)?
5. **A16 risers and stands, solid or sheet?** They are built as solid clear blocks (the log). The sheet 23 headings say
   "3 mm clear acrylic", and a fabricated hollow box looks the same from outside.
6. **Wall unit cabinet:** keep the doors fixed, or split the 4 doors into hinged part meshes, with the interior shelf?
7. **Wall unit snaps:** add `Snap_L` / `Snap_R` so units can run side by side? They are not added, because nothing
   shows them.
8. **Wall unit cabinet height:** sheet 36's proportions read about 690 against the 900 call-out. I built 900 (the
   number).

## Renders (`WorkFiles/cardshop/families/a_display/`)

| Item | Files |
|---|---|
| A14 | `a_display_table08_34` (8 cards, lid closed), `a_display_table08_34_open` (lid at 70°), `a_display_table08_front`, `a_display_table08_right`, `a_display_table12_34_open_slabs` (12 slabs, lid at 70°) |
| A15 | `a_display_easel_{slab,card,small}_34`, `a_display_easel_{slab,card,small}_right` (profile) |
| A16 | `a_display_riser1_34`, `a_display_riser1_empty_34`, `a_display_riser3_34`, `a_display_riser3_right`, `a_display_stand1_34`, `a_display_stand9_34`, `a_display_stand9_empty_34`, `a_display_stand9_right` |
| Wall unit | `a_display_wallunit_34`, `a_display_wallunit_front` |

All files are PNG. The shot tool guesses materials from slot names: the felt renders light grey, the white steel legs
render silver and the glass renders milky. Treat them as shape checks only.
