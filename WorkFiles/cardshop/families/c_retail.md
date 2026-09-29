# Family c_retail: singles & protection (C1-C7) and the B8 retail accessories (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_c_retail.py`, 21 item keys prefixed `c_retail_`. Spec rows: CARDSHOP_KIT_SPEC.md
3.C C1 (Small), C2, C3, C4, C5 (35pt_Filled), C6, C7, and 3.B B8 (all 8 `SM_CSK_Retail_*`). References: sheets 1, 2, 8
and 12, all opened on disk and measured with Pillow. Each sheet was compared side by side with its render.

**Build:** a single build of the G1 `card` key plus all 21 keys ends `CSK_BUILD PASSED`.
- The house `qa_check` passes on every LOD.
- The kit checks pass 29/29: 6 contain fits, 22 hashes and the deny scan.
- `card` is in the build as the Card-class stand-in for the contain tests. Without it the penny sleeve would be the
  Card stand-in, and a sleeve does not fit a deck sleeve.
- Command: `build_csk.py -- --no-save --items card,c_retail_... --out scratchpad/fam_c_retail/final`.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | Hulls |
|---|---|---|---|---|---|---|
| c_retail_card_small | SM_CSK_Card_Small | 92 | 96 | PASS | Seat, Face, Grip | 1 (2 mm) |
| c_retail_stack_10 / _30 / _90 | SM_CSK_CardStack_{10,30,90} | 60 | 60 | PASS | Seat, Top | 1 |
| c_retail_sleeve_penny | SM_CSK_Sleeve_Penny | 44 | 60 | PASS | Seat, Card | 1 (2 mm) |
| c_retail_sleeve_deck_std / _small | SM_CSK_Sleeve_Deck_{Std,Small} | 28 | 80 | PASS | Seat, Card | 1 (2 mm) |
| c_retail_toploader_filled | SM_CSK_TopLoader_35pt_Filled | 396 / 200 / 68 | 396 (300 + 96) | PASS | Seat, Face, Grip, Stack | 1 |
| c_retail_semirigid | SM_CSK_Holder_SemiRigid | 108 | 150 | PASS | Seat, Card | 1 (2 mm) |
| c_retail_magnetic | SM_CSK_Holder_Magnetic | 576 / 176 / 60 | 800 | PASS | Seat, Card, Face, Grip, Stack | 1 |
| c_retail_magnetic_front | SM_CSK_Holder_Magnetic_Front | 468 / 116 / 76 | 500 (E) | PASS | Seat, Face, Grip | 1 |
| c_retail_magnetic_back | SM_CSK_Holder_Magnetic_Back | 468 / 116 / 76 | 500 (E) | PASS | Seat, Card, Half, Grip | 1 |
| c_retail_magnetic_filled | SM_CSK_Holder_Magnetic_Filled | 596 / 196 / 92 | 800 | PASS | Seat, Face, Grip, Stack | 1 |
| c_retail_sleevebox | SM_CSK_Retail_SleeveBox100 | 168 / 64 / 32 | 200 | PASS | Seat, Hang, Stack, Face, Grip | 2 |
| c_retail_tlpack | SM_CSK_Retail_TopLoaderPack25 | 268 / 100 / 36 | 300 | PASS | Seat, Hang, Stack, Face, Grip | 2 |
| c_retail_pennypack | SM_CSK_Retail_PennyPack100 | 204 / 84 / 36 | **220** (spec 150) | PASS | Seat, Hang, Stack, Face, Grip | 2 |
| c_retail_diceclam | SM_CSK_Retail_DiceClam | 394 / 178 / 48 | 400 | PASS | Seat, Hang, Stack, Face, Grip | 1 |
| c_retail_binder | SM_CSK_Retail_BinderWrapped | 236 / 76 / 28 | 500 | PASS | Seat, Stack, Face, Grip | 1 |
| c_retail_tube | SM_CSK_Retail_PlaymatTube | 276 / 124 / 64 | 300 | PASS | Seat, Stack, Face, Grip | 1 |
| c_retail_deckboxpack | SM_CSK_Retail_DeckBoxPack | 260 / 124 / 60 | 300 | PASS | Seat, Hang, Stack, Face, Grip | 2 |
| c_retail_bottle | SM_CSK_Retail_CleanerBottle | 394 / 162 / 92 | 400 | PASS | Seat, Stack, Face, Grip | 1 |

**Classes:**
- Card_Small is **CardSmall**, a new class (59 x 86, pitch 69 x 96).
- The penny sleeve is Card.
- The deck sleeves, the filled top-loader, the semi-rigid and the closed and filled magnetic holders are CardProt.
- The hang packages are Hang. The binder is Binder, the tube and bottle are Retail, and the deck-box pack is Deck.

**Frames:**
- The cards, sleeves and holders lie on their back, with +Y as the open end.
- The B8 items stand upright (W x D x H, as the spec's table).
- `Hang` sits at the euro-slot peak apex on the tab mid-plane, with identity rotation. The `.csk.json` `hang` block
  holds T and pitch T + 2.
- The magnetic back half carries `Half` at the closed position and `parts.Front`: a slide on Z, 0-30 (E).

**Print:**
- Every B8 item is one Boxes-atlas cell on `M_CSK_BoxPrint`, as a dieline in tile (0,0) with regions 10 and up.
- Each `.csk.json` carries `print_layout` (the panel rectangles in sheet mm) and `print_art` (sheet 12's two-tone blocks
  with sampled colours), so the art pass can paint the cells.
- Labels on round parts use two regions that share one wrap panel, with the seam at the back (+Y).
- The dice pips are "baked detail": each die's visible faces are their own print cells.

## Deviations (and why)

**Card_Small class:** it is CardSmall, not Card. A Std card cannot go in the 62-wide Small deck sleeve, so the Small
sleeve accepts CardSmall and its contain test seats the Small card.

**C2 card stacks:** the edge band maps to the U -1 tile with V = z / 90 mm in every size. One stripe texture then
serves all three stacks.

**C3 penny sleeve:** the sheet shows a lens-shaped mouth. It is built as a hexagonal section whose skins meet in welded
knife edges. The crinkled film is texture.

**C4 deck sleeves:**
- T is 0.6 (E).
- Sheet 8 shows the back wrapping about 1 mm onto the front. It is built as slanted edge faces on the long edges and the
  bottom.

**C5 filled top-loader:**
- It uses the G1 `_toploader_lod` shape.
- The card print is split in 0.05 under both skins (the same region split as the slab), in one opaque slot.

**C6 semi-rigid holder:**
- The tab is **22.3 x 10.1, R 2.7**, measured on sheet 8. The spec's E was 30 x 12 and the log estimated 28 x 9.
- T is kept at 1.0. The top view draws it about 9 thick; the side view and the prompt give about 1.

**C7 magnetic holder:**
- The magnets sit 6.5 in from the side edges, as on sheet 8, but 3.9 from the top and bottom edges (the picture reads
  about 6). At 6 they would cut the E* well (67.6 x 94.7).
- The well is 0.5 deep in each half.
- Following the spec, the Body is opaque. So the magnets show as 0.4-deep pockets on both faces of each half.
- The parting line is a 0.3 chamfer on each half's meeting rim.

**B8 pose:** the accessories stand upright. The b_ship blister (B6) lies on its back instead.

**SleeveBox100:** the tab is **24** tall (sheet 12; the spec's E was 40). It is flush with the back panel.

**TopLoaderPack25:**
- The header is **42.3** tall (sheet 12; the spec's E was 30).
- The contents are one PVC block, 76.2 x 101.6 x **33**. 25 loaders at the kit's T of 2.0 (E) would be 50 thick, which
  does not fit the 35-deep bag.
- The 101.6 stack fills the 108 bag, so the pillow pinch is only 1.5 at each end. The sheet draws the stack smaller and
  the pinch longer.

**PennyPack100:**
- The header is **37** tall (sheet 12; the spec's E was 25).
- The budget is 150 -> 220. The euro slot is a real hole, and the pillow bag and the sleeve stack are real forms.
- The 1 mm perforated tear line is not modelled.

**DiceClam:**
- Sheet 12 draws the clam 176 tall at 60 wide. The printed 130 (including the tab) wins, so the dice rows are pitched
  20 / 20 / 22 (the picture reads 21 / 21 / 27).
- The dice are M 16, laid out 2 x 3 + 1, with the 18.4 column pitch read off the sheet.

**BinderWrapped:**
- The prompt's sticker is not in the picture, so none is built.
- The covers and spine stand 3 proud of the page block at the top only: a pocket inside the rims. At the fore-edge and
  bottom the cuts crossed the chamfered rims and made degenerate slivers.
- The crinkles and the stitching are texture.

**PlaymatTube:**
- The caps are 70 across and the tube 67 (E).
- The roll is E5 Rolled at 45 x 356 (D). The sheet draws it fuller, about 58 across.
- The small dot on the cap top is not modelled.

**DeckBoxPack:**
- The hang tab is in the picture but not the spec. It is built, with a Hang socket, and the class stays Deck, so the
  footprint's H of 116 does not count the 25 tab.
- The deck box behind the window is E4's 76 wide. So the flap edge crosses the window straight, where the picture draws
  its corners inside the window.
- The window is an open die-cut, with no film (the picture shows none).

**CleanerBottle:**
- The proportions follow the printed 40 x 140. The picture draws it about 10 % taller.
- The collar ribs, the nozzle hole and the dip tube are not modelled.

## New material slot names

| Slot | Used for |
|---|---|
| `M_CSK_SleeveBack` | Named in the spec; new in code. Deck sleeve back, on the back tile (1,0). |
| `M_CSK_TopLoaderFilled` | 1 opaque Clear Coat section with the card art. |
| `M_CSK_MagHolderBody` | Opaque border and magnets, Clear Coat. |
| `M_CSK_MagHolderWindow` | Translucent acrylic. |
| `M_CSK_MagHolderFilled` | 1 opaque section. |
| `M_CSK_FilmStack` | The frosted block of 100 penny sleeves. |
| `M_CSK_Rubber` | The rolled playmat in the tube. |
| `M_CSK_Plastic` | The blue deck box behind the window; a tint MI (E4's "Plastic (tint)"). |
| `M_CSK_PlasticWhite` | The spray pump. |

Reused: `M_CSK_Card`, `M_CSK_Film`, `M_CSK_PVC`, `M_CSK_BoxPrint`, `M_CSK_Board`, `M_CSK_Base`.

## Not built

Nothing from the assigned rows. C1 Std and C5 35pt / 130pt already exist in `geom.py` and were not touched.

## Open questions for the user

1. **CardSmall class:** should the fixture grids list CardSmall in `accepts`? It fits any Card cell.
2. **Top-loader pack depth:** 25 x 2.0 is 50, but the bag is 35. Keep the 33 proxy block, or make the bag 52 deep?
3. **Deck-box pack tab:** keep the picture's hang tab (the Deck footprint's H would become 141), or drop it to match
   the spec?
4. **Hang pose:** B8 hangs upright, but the b_ship blister lies on its back. Should one convention win?
5. **Dice pips:** printed in the item's Boxes cell, or E6's `M_CSK_Resin` pip mask once E6 exists? The mask's UVs would
   overlap across 7 dice.
6. **Magnet spacing:** move the magnets to the picture's 6 mm from the top edge by shrinking the well to about 92 tall?

## Renders

All renders are in `WorkFiles/cardshop/families/c_retail/`. The scratch shot tool paints `print_art` onto the print slot.
- `c1_cards_stacks_34.png`
- `c3c4c5c6_top.png` and `c3c4c5c6_34.png`: penny, deck Std and Small, semi-rigid and filled top-loader.
- `c7_magnetic_34.png`, `c7_magnetic_top.png` and `c7_magnetic_right.png`
- `b8_hang_front.png`, `b8_hang_34.png` and `b8_hang_right.png`, plus `b8_hang_vs_sheet.png`
- `b8_shelf_front.png` and `b8_shelf_34.png`, plus `b8_shelf_vs_sheet.png`
- `b8_bottle_front.png`, `b8_bottle_34.png` and `b8_bottle_vs_sheet.png`
