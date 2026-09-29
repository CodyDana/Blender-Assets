# Family a_shelving: slatwall, hooks, shelves, gondola, wire rack, box tier (spec 3.A7-A13)

**Date:** 2026-09-29. **Module:** `Scripts/cardshop/csk_lib/fam_a_shelving.py` (14 item keys, `a_shelving_*`).
**Sheets:** 19, 20, 21. They are not on disk yet, so the work follows their notes in `References/CardShop/REFERENCE_LOG.md`
and the prompts. Compare against the pictures again once they are saved.

**Build:** one build of all 14 keys ends `CSK_BUILD PASSED`. House `qa_check` passes on every LOD (68-148 checks per
mesh), and the kit checks pass 24/24 (hashes, deny scan, fixture socket counts).

A second validation build added the G1 `pack` and `box`, so the level grids were tested against real items. It passed
214/214: level volume, cell and hull 38/38 each, stacks 38/38 and the booster box's contain fits. No Deck, BoxL or BoxC
items exist yet, so those grids have not been tested against a real mesh.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | UCX |
|---|---|---|---|---|---|---|
| `a_shelving_slatwall_1000` | `SM_CSK_Slatwall_1000x2400` | 1268 / 524 / 276 | 3000 | PASS | 34: Seat, Groove_01..31, Snap_L/R | 1 |
| `a_shelving_slatwall_2000` | `SM_CSK_Slatwall_2000x2400` | 1268 / 524 / 276 | 3000 | PASS | 34 | 1 |
| `a_shelving_hook_102` | `SM_CSK_Hook_Slat_102` | 168 / 64 / 40 | 400 | PASS | 4: Seat, Mount, Hang_Start, Label | 1 |
| `a_shelving_hook_203` | `SM_CSK_Hook_Slat_203` | 168 / 64 / 40 | 400 | PASS | 4 | 1 |
| `a_shelving_hook_305` | `SM_CSK_Hook_Slat_305` | 168 / 64 / 40 | 400 | PASS | 4 | 1 |
| `a_shelving_shelf_slat` | `SM_CSK_Shelf_Slat_1000` | 468 / 148 / 52 | 600 | PASS | 10: Seat, Level/Compartment/PriceTag S1, Mount_L/R | 1 |
| `a_shelving_gondola_single` | `SM_CSK_Gondola_Single_1372` | 2516 / 420 / 196 | 4000 | PASS | 37: Deck level (7), Mount_F_01..11, Groove_F_01..16, Snap_L/R, Seat | 4 |
| `a_shelving_gondola_double` | `SM_CSK_Gondola_Double_1372` | 4904 / 728 / 296 | 6000 | PASS | 39: DeckF + DeckB levels (14), Mount_F/B_01..11, Snap_L/R, Seat; grooves as rails data | 5 |
| `a_shelving_gondola_endcap` | `SM_CSK_Gondola_EndCap_1372` | 2516 / 420 / 196 | 4000 | PASS | 37 | 4 |
| `a_shelving_gondola_shelf_305` | `SM_CSK_Gondola_Shelf_305` | 416 / 128 / 48 | 500 | PASS | 10 | 1 |
| `a_shelving_gondola_shelf_406` | `SM_CSK_Gondola_Shelf_406` | 416 / 128 / 48 | 500 | PASS | 10 | 1 |
| `a_shelving_gondola_corner` | `SM_CSK_Gondola_Corner_1372` | 1936 / 976 / 448 | 2000 | PASS | 38: Deck + S1..S4 levels (35), Snap_L/R, Seat | 4 |
| `a_shelving_rack_wire` | `SM_CSK_Rack_Wire_914` | 13664 / 4224 / 1982 | **14000** (spec 7000) | PASS | 28: L1..L5 levels (25), Snap_L/R, Seat | 5 |
| `a_shelving_box_tier` | `SM_CSK_Shelf_BoxTier_1219` | 440 / 128 / 92 | 1200 | PASS | 31: T1..T4 levels (28), Snap_L/R, Seat | 6 |

**What each mesh is built from (all real geometry):**
- **Slatwall:** 31 T-slot grooves with chamfered lips, run through the full width, so the T profile shows at the panel
  ends. The mesh is one swept profile of about 1.3k tris (the spec estimated about 1.4k).
- **Hook:** a bent back plate whose tab passes through the groove opening and drops behind the lower lip. Then a
  4.76 wire arm, an upward kink and a tilted price plate.
- **Slatwall shelf brackets:** tapered blades with two tongues that hook into the grooves.
- **Gondola uprights:** chamfered, with 49 real slot pockets per face at a 25.4 pitch. The shelf brackets hook into
  those slots.
- **Gondola shelf front:** a price channel with a sloped face.
- **Rack posts:** 4 posts with 60 visible ring grooves each. Each of the 5 decks has truss zigzags, front-to-back mat
  wires, tapered collars and black feet.
- **Box tier:** tapered oak sides and 3 planks tilted 10 deg with 25 mm lips.

## Deviations from the spec (and why)

- **A7 slatwall:**
  - No aluminium `Insert` slot. Sheet 19 shows bare MDF in the grooves, so the slot is `M_CSK_MDF`.
  - The T-slot sizes are E: an opening 11 wide and 5 deep, and a head 24 tall and 6 deep.
  - The pivot is the bottom-left corner of the back (wall) face, as the spec's end-corner pivot asks. The face is at
    y = -19.
  - Grooves are numbered from the bottom. The first groove centre is at z = 57.
  - LOD1 has rectangular grooves; LOD2 has flat MDF bands.
- **A8 hook:**
  - These are all E: plate 38 x 45 x 1.5, arm 36 below the groove centre, kink 22 long at 30 deg, price plate
    40 x 28 x 1.2 tilted 30 deg.
  - The pivot and the `Mount` socket are the groove centre on the face plane, so a hook seats straight on a `Groove_*`.
  - The `Label` socket's +Z is the plate's face normal.
  - `.csk.json` gets a `hang` block: axis -Y, run length, class Hang, pitch T + 2.
- **A9 slatwall shelf:**
  - The board is `M_CSK_Laminate`, because `M_CSK_Board` is already the carton-board slot.
  - The brackets are `M_CSK_Chrome`, to match the hooks.
  - The sheet's "front lip" is read as the brackets' upturned tips, 6 mm proud of the board.
  - Brackets at +-375 and a clear height of 280 are E.
- **A10 gondola:**
  - The end cap is 610 wide, from sheet 20.
  - `Mount_<Side>_NN` start at 2 x 101.6 above the deck (303.2 to 1319.2, 11 per side). A lower shelf would leave the
    deck no room.
  - **Double:** the spec's socket list comes to 73, over the 40 limit. So there are no `Groove_*` sockets; the grooves
    are published as `rails` (first groove, pitch, count and rotation per side). Every gondola also carries its groove
    and mount rails.
  - The Double's levels are `DeckF` / `DeckB`, and its B side sockets are turned 180 deg.
  - UCX count is 4 for the Single and End cap, and 5 for the Double (it has two decks).
  - The slat panel's ends sit inside the uprights, so they are left open.
- **A11 shelves:**
  - The price channel has its own slot, `M_CSK_PriceStrip`. Sheet 20 says "clear/white extrusion"; the spec said
    Metal only.
  - The shelf is a steel U-pan with two slot-hooking end brackets. The pivot is the upper slot on the upright face, the
    same point as a gondola `Mount_*`.
- **A11 corner:**
  - Deck 406, shelves 305. The shelf heights 354 / 608 / 862 / 1116 are E: they split deck-to-top into fifths.
  - The L shelves are fixed, so the uprights are unslotted and there are no `Mount_L/R` sockets.
  - Each L level's grid is its rear arm. The left arm's extension is Compartment 01 only.
  - The 4 hulls (per spec) cover the two backs and the two arms of the deck. **The L shelves have no collision.**
- **A12 wire rack:**
  - 5 decks, L1..L5, from the sheet notes.
  - **Budget 7000 -> 14000.** The fifth deck and the sheet's ring-grooved posts are real geometry; the posts alone are
    about 7.7k tris.
  - The grooves are a steep ring step with a taper, 2 rings per 25.4 pitch. Grooves hidden under the collars are
    skipped.
  - Deck tops sit on the groove grid: 152.4 + 406.4 k.
  - The feet use `M_CSK_Base` (black).
  - There is one hull per deck and none on the posts.
- **A13 box tier:**
  - Tier 1 is the deck at 252. The shelves are at 532 / 812 / 1092, measured at the foot of the lip. I read
    "280 apart starting at 252" as tier heights, since 252 + 4 x 280 = 1372 exactly.
  - **The deck is flat.** The sheet tilts only the 3 shelves; the spec said 4 tilted tiers.
  - The shelves' back edge is lower ("tilted back").
  - No Metal slot, because no metal shows on the sheet.
  - These are E: side top depth 152.4 (a 76.2 step per tier), a black kick 60 tall recessed 30, lip 12 thick.
  - 6 hulls (the spec says 5): 2 sides, the base, and one box per shelf up to the plank's mid-depth top. The hull
    boxes are axis-aligned, so that top is a flat stand-in for the tilted plank.
- **New placement classes:** `BoxL` 190 x 76 x 140 and `BoxC` 190 x 89 x 165 are added to `CLASSES`, with pitch +10
  (spec 4.2). The shelves need them.

## New material slots

`M_CSK_Slatwall` (white laminate face, tint), `M_CSK_MDF` (bare MDF: grooves, edges, back), `M_CSK_Chrome` (hooks,
slatwall brackets, wire rack), `M_CSK_Laminate` (white boards: slatwall shelf, box tier deck and shelves),
`M_CSK_Steel` (gondola powder-coated light grey), `M_CSK_PriceStrip` (gondola price channel). Reused: `M_CSK_Oak`,
`M_CSK_Base`.

## Not built

- **610-wide end cap shelves.** Sheet 20 shows 3 shelves on the end cap, but A11 only lists 1219 widths.
  `item_gondola_shelf` would take a width parameter in one line if you want them.
- **Retail class grids** on the box tier: per item, so it is only listed in `accepts`. The `Hang` class itself is not
  defined here.
- **The rack's split-sleeve clips:** they are hidden inside the collars.

## Open questions

1. **Faceted round parts.** `mesh.py` marks every edge sharper than 30 deg as sharp. So any tube with fewer than 13
   sides shades flat-faceted: the rack posts (8 sides), wires, collars and feet, the hook arm and the gondola feet.
   - **Fix at the cause:** a per-face "smooth" region or a Lod option in the shared `mesh.py`, which the lead owns.
     That would smooth them at today's tri counts.
   - **The alternative:** 14-sided posts, which takes the rack to about 19.5k.
2. **Tilted levels (A13 T2-T4).** `fit.grid_slots` and `slots.write_csk_json` ignore the Level socket's rotation. The
   `slots_ue` for the tilted tiers come out with rotation 0 and horizontal offsets. The Level, Compartment and PriceTag
   sockets themselves carry the -10 deg.
   - The shared code needs to rotate the grid offsets and slot rotations by the level socket.
   - Until then the kit check tests the tiers axis-aligned: an approximation.
3. **A13 tilt direction.** I built the back edge lower, so box faces tip up to the customer. The sheet shows no back
   panel to stop boxes at the rear. Is that right, or should the shelves tip forward against the 25 lip?
4. **A13 heights.** Is "starting at 252" the deck height, as built?
5. **A9 lip.** Is the lip on the brackets' tips, as built, or a lip along the board's front edge?
6. **A10 end cap.** It is 610 wide per sheet 20, but a Double is 852 deep, so the end cap cannot close a Double run's
   end. Should it be 852? And should it get shelves (see Not built)?
7. **Rack budget.** Keep 14000 with the grooved posts, or drop the grooves to get about 6.3k?
8. **Gondola Double.** Is publishing its grooves as rails acceptable, or should this fixture get more than 40 sockets?
9. **Gondola deck clear height.** It is published as open to the top (1272), since shelves are separate meshes. The
   corner's levels use the real gap to the next shelf's price channel.

## Renders (`WorkFiles/cardshop/families/a_shelving/`)

| Render | What it shows |
|---|---|
| `slatwall_1000_34.png` | The panel |
| `slatwall_end_detail.png` | The T-slot profile at the panel end |
| `slatwall_fitted_34.png` | A 2000 panel with a shelf and 5 hooks on `Groove_*` sockets |
| `slatwall_mount_side.png` | The hook tab and bracket tongues in the grooves |
| `hook_34.png`, `hook_side.png` | The hooks |
| `shelf_slat_34.png`, `shelf_slat_side.png` | The slatwall shelf |
| `gondola_single_34.png` | Single with 2 shelves on `Mount_F_*` |
| `gondola_double_34.png` | Double with 3 shelves a side |
| `gondola_endcap_34.png` | End cap |
| `gondola_corner_34.png` | Inside corner |
| `gondola_detail.png` | Chamfered slotted upright, T grooves, shelf |
| `gondola_shelf_side.png` | Bracket tongues and the sloped price channel |
| `rack_wire_34.png`, `rack_wire_detail.png` | Rack: truss, collars, ring grooves |
| `box_tier_34.png` | Box tier shelf |
| `box_tier_section.png` | A section through the tier profile |

## Process notes

- Renders were made with a scratch copy of `csk_shot.py` that adds palette entries for the new slots, a close-up
  target and section cuts. The shared tool is unchanged.
- One build run without arguments wrote the default `WorkFiles/cardshop/g1/build_report.json` (the lock check failed
  first). I deleted it right away. No other file outside this family's module, report and render folder was touched.
