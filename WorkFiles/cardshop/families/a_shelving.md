# Family a_shelving: slatwall, hooks, shelves, gondola, wire rack, box tier (spec 3.A7-A13)

**Date:** 2026-09-29. **Module:** `Scripts/cardshop/csk_lib/fam_a_shelving.py` (14 item keys, `a_shelving_*`).

**Sheets used:** 19, 20 and 21, now on disk: `References/CardShop/csk_slatwall.png`, `csk_gondola.png` and
`csk_wire_rack_box_shelf.png`. The first pass used only their notes in the reference log. Once the PNGs were saved I
compared each item against the pictures and rebuilt what differed (see "Changed after comparing with the pictures").

**Final build:** one build of all 14 keys ends `CSK_BUILD PASSED`.
- House `qa_check` passes on every LOD (69-145 checks per mesh).
- The kit checks pass 24/24 (hashes, deny scan, fixture socket counts).

**Grid validation:** a second build with the same code plus the G1 `pack` and `box` passes 214/214. That covers level
volume, cell and hull (38/38 each) and stacks (38/38) against real Pack and BoxS items. No Deck, BoxL or BoxC item
meshes exist yet, so those grids have not been tested against a real mesh.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | UCX |
|---|---|---|---|---|---|---|
| `a_shelving_slatwall_1000` | `SM_CSK_Slatwall_1000x2400` | 1268 / 524 / 276 | 3000 | PASS | 34: Seat, Groove_01..31, Snap_L/R | 1 |
| `a_shelving_slatwall_2000` | `SM_CSK_Slatwall_2000x2400` | 1268 / 524 / 276 | 3000 | PASS | 34 | 1 |
| `a_shelving_hook_102` | `SM_CSK_Hook_Slat_102` | 254 / 104 / 58 | 400 | PASS | 4: Seat, Mount, Hang_Start, Label | 1 |
| `a_shelving_hook_203` | `SM_CSK_Hook_Slat_203` | 254 / 104 / 58 | 400 | PASS | 4 | 1 |
| `a_shelving_hook_305` | `SM_CSK_Hook_Slat_305` | 254 / 104 / 58 | 400 | PASS | 4 | 1 |
| `a_shelving_shelf_slat` | `SM_CSK_Shelf_Slat_1000` | 468 / 164 / 84 | 600 | PASS | 10: Seat, Level/Compartment/PriceTag S1, Mount_L/R | 1 |
| `a_shelving_gondola_single` | `SM_CSK_Gondola_Single_1372` | 2564 / 444 / 220 | 4000 | PASS | 36: Deck level (7), Mount_F_01..10, Groove_F_01..16, Snap_L/R, Seat | 4 |
| `a_shelving_gondola_double` | `SM_CSK_Gondola_Double_1372` | 5000 / 776 / 344 | 6000 | PASS | 37: DeckF + DeckB levels (14), Mount_F/B_01..10, Snap_L/R, Seat; grooves as rails data | 5 |
| `a_shelving_gondola_endcap` | `SM_CSK_Gondola_EndCap_1372` | 2564 / 444 / 220 | 4000 | PASS | 36 | 4 |
| `a_shelving_gondola_shelf_305` | `SM_CSK_Gondola_Shelf_305` | 416 / 128 / 48 | 500 | PASS | 10 | 1 |
| `a_shelving_gondola_shelf_406` | `SM_CSK_Gondola_Shelf_406` | 416 / 128 / 48 | 500 | PASS | 10 | 1 |
| `a_shelving_gondola_corner` | `SM_CSK_Gondola_Corner_1372` | 3968 / 1048 / 520 | **4000** (spec 2000) | PASS | 38: Deck + S1..S4 levels (35), Snap_L/R, Seat | 4 |
| `a_shelving_rack_wire` | `SM_CSK_Rack_Wire_914` | 13752 / 4312 / 2046 | **14000** (spec 7000) | PASS | 28: L1..L5 levels (25), Snap_L/R, Seat | 5 |
| `a_shelving_box_tier` | `SM_CSK_Shelf_BoxTier_1219` | 508 / 148 / 104 | 1200 | PASS | 31: T1..T4 levels (28), Snap_L/R, Seat | 6 |

Everything is real geometry with crisp bevels (0.3-1 mm on LOD0, or pre-chamfered profiles):

- **Slatwall:** 31 T-slot grooves (sheet 19 cut-away) with chamfered lips. They run through the full width, so the T
  shows at the panel ends.
- **Hook:** a bent back plate whose tab passes through the groove opening and drops behind the lower lip. The wire is
  welded up the plate, bends out, falls 8 deg, then kinks up at the tip. A white label holder sits on the tip.
- **Slatwall shelf brackets:** a back plate (hooked like the hooks, with a lower tongue in the next groove down), a
  tapered blade and a round lip post at the tip.
- **Gondola uprights:** chamfered, with real slot pockets (5 x 12 at 25.4) that the shelf brackets hook into.
- **Gondola base:** a deck pan with the shelves' sloped price channel, on a set-back kick plate and levelling feet.
- **Corner unit:** L deck and L shelves with the price channel mitred round the corner, and slotted end uprights.
- **Wire rack:** 4 posts with 60 visible ring grooves each, black caps and black feet. Each of the 5 decks has truss
  zigzags, front-to-back mat wires and tapered collars.
- **Box tier:** tapered oak sides, a white back panel, and 4 tiers tilted back 10 deg with 25 lips. The oak cabinet's
  top follows tier 1, over a recessed black kick.

## Changed after comparing with the pictures

- **Sheet 19:**
  - T-slot measured off the cut-away: opening 12 wide x 6.5 deep, head 30 tall x 6 deep (was 11 / 5 / 24 / 6, all
    E).
  - Hook back plate 28 x 60.
  - The wire now runs up the plate from 80 % to 40 % of its height before bending out.
  - The arm falls 8 deg.
  - The kink is steeper: 20 long at 38 deg.
  - The label holder is white/clear, 38 x 32 x 2.5 (slot `M_CSK_PriceStrip`).
  - Shelf brackets: a back plate, a 50-to-10 tapered blade, and a round lip post at the tip.
- **Sheet 20:**
  - The base deck is a pan with the shelves' price channel, on a kick plate set back 12. Deck top 130; kick top 100.
  - The corner unit's two end uprights are slotted. The corner post stays plain because both backs cover its faces.
- **Sheet 21:**
  - Black caps on the rack posts.
  - The box tier gets a white back panel.
  - All four tiers tilt 10 deg with a 25 lip. Tier 1 was flat before; the sheet's own caption and section show it
    tilted and lipped.
  - The lip detail confirms the tilt direction: the shelf falls toward the rear.
- **A build bug found on the way:** Blender's scanfill (`Builder.fill`) left holes in the comb-shaped slatwall end
  caps once the grooves grew (297 open edges). QA passes open edges, so nothing flagged it. The module's sweeps now
  triangulate their caps with their own ear clipping, and every mesh was checked for unintended open edges.

## Deviations from the spec (and why)

- **A7 slatwall:**
  - No aluminium `Insert` slot: sheet 19 shows bare MDF in the grooves, so the slot is `M_CSK_MDF`.
  - The pivot is the bottom-left corner of the back (wall) face, as the spec's end-corner pivot asks. The face is at
    y = -19.
  - Grooves are numbered from the bottom; the first centre is at z = 57.
  - LOD1 has rectangular grooves; LOD2 has flat MDF bands.
- **A8 hook:**
  - The pivot and `Mount` are the groove centre on the face plane, so a hook seats straight on a `Groove_*`.
  - `.csk.json` gets a `hang` block: the arm's axis (falling 8 deg), its run length, class Hang, pitch T + 2.
  - `Label` +Z is the holder's face normal.
  - The holder has its own slot, `M_CSK_PriceStrip`. The spec said Metal only; the picture's holder is white/clear.
- **A9 slatwall shelf:**
  - The board is `M_CSK_Laminate`, because `M_CSK_Board` is already the carton-board slot.
  - The brackets are `M_CSK_Chrome`.
  - Brackets at +-375 and a clear height of 280 are E.
- **A10 gondola:**
  - The end cap is 610 wide, from sheet 20.
  - `Mount_<Side>_NN` start at 2 x 101.6 above the deck (333.2 to 1247.6, 10 per side). A lower shelf leaves the deck
    no room.
  - **Double:** the spec's socket list would come to 73, over the 40 limit. So its grooves are published as `rails`
    (first groove, pitch, count and rotation per side) instead of `Groove_*` sockets. Every gondola also carries its
    groove and mount rails.
  - The Double's levels are `DeckF` / `DeckB`; its B side sockets are turned 180 deg.
  - The deck price channel adds the slot `M_CSK_PriceStrip` to the gondolas.
  - UCX count is 4 for the Single and End cap (uprights, back, base) and 5 for the Double (two bases).
  - The panel ends sit inside the uprights, so they are left open.
- **A11 shelves:**
  - The steel U-pan has two slot-hooking end brackets and a price channel with a sloped face, slot
    `M_CSK_PriceStrip`.
  - The pivot is the upper hook slot on the upright face, the same point as a gondola `Mount_*`.
  - The bracket's round hole in the sheet 20 detail is not cut. Booleans on this multi-part mesh are not advised.
- **A11 corner:**
  - **Budget 2000 -> 4000:** its two slotted end uprights (sheet 20) cost what they cost on the Single (budget 4000).
  - Deck 406 and shelves 305. The shelf heights 378.4 / 626.8 / 875.2 / 1123.6 are E: they split deck-to-top into
    fifths.
  - The shelves are fixed L pieces, so there are no `Mount_L/R` sockets.
  - Each L level's grid is its rear arm; the left arm's extension is Compartment 01 only.
  - The 4 hulls (per spec) cover the two backs and the two arms of the base. **The L shelves have no collision.**
- **A12 wire rack:**
  - 5 decks, L1..L5. That is the picture's count and the log's decision; the sheet caption and the spec say 4.
  - **Budget 7000 -> 14000:** the fifth deck and the sheet's ring-grooved posts. The posts are about 7.7k tris; each
    groove is a sharp ring step, 2 rings per 25.4.
  - Deck tops sit on the groove grid: 152.4 + 406.4 k.
  - The feet and caps are `M_CSK_Base` (black).
  - There is one hull per deck and none on the posts.
- **A13 box tier:**
  - The heights follow the sheet's dimensioned section: tiers at 252 / 532 / 812 / 1092 (at the lip's foot) and sides
    to 1372.
  - No Metal slot: there is no metal on the sheet.
  - These are E: side top depth 152.4 (a 76.2 step per tier), kick 60 tall recessed 30, lip 12 thick, back panel 12.
  - 6 hulls (the spec says 5): 2 sides, the base with tier 1, and one box per upper tier. Each tier box reaches the
    board's mid-depth top: a flat stand-in, because hull boxes are axis-aligned. The back panel has no hull of its own
    (the family guide's 6-hull limit).
- **New placement classes:** `BoxL` 190 x 76 x 140 and `BoxC` 190 x 89 x 165 are added to `CLASSES`, with pitch +10
  (spec 4.2).

## New material slots

- `M_CSK_Slatwall`: white laminate face, tintable.
- `M_CSK_MDF`: bare MDF in the grooves, on the edges and the back.
- `M_CSK_Chrome`: hooks, slatwall brackets, wire rack.
- `M_CSK_Laminate`: white boards on the slatwall shelf and the box tier.
- `M_CSK_Steel`: gondola powder-coated light grey.
- `M_CSK_PriceStrip`: gondola and corner price channels, and the hook label holders (white/clear).

Reused: `M_CSK_Oak` and `M_CSK_Base`.

## Not built

- **610-wide end cap shelves.** Sheet 20 shows 3 shelves on the end cap, but A11 lists only 1219 widths.
  `item_gondola_shelf` would take a width parameter in one line.
- **Retail class grids** on the box tier: per item, so it is only listed in `accepts`. The `Hang` class itself is not
  defined here.
- **The rack's split-sleeve clips:** they are hidden inside the collars.

## Open questions

1. **Faceted round parts.** The shared `mesh.py` marks every edge sharper than 30 deg as sharp. So any round part with
   fewer than 13 sides shades flat-faceted: the rack posts, wires, collars, caps and feet, the hook wire and the
   gondola feet.
   - **Fix at the cause:** a per-face "smooth" region or a Lod option in `mesh.py`, which the lead owns. That fixes
     them at today's tri counts.
   - **The alternative:** 14-sided posts, which takes the rack to about 19.5k.
2. **Tilted levels (A13 T1-T4).** `fit.grid_slots` and `slots.write_csk_json` ignore the Level socket's rotation. The
   `slots_ue` for these tiers come out with rotation 0 and horizontal offsets. The Level, Compartment and PriceTag
   sockets themselves carry the -10 deg.
   - The shared code needs to rotate grid offsets and slot rotations by the level socket.
   - Until then the kit check tests the tiers axis-aligned: an approximation.
3. **A10 end cap.** It is 610 wide per the sheet, but a Double is 852 deep, so the end cap cannot close a Double run's
   end. Keep 610, or make it 852? And should it get 610-wide shelves (see Not built)?
4. **Rack budget.** Keep 14000 with the grooved posts, or drop the grooves to get about 6.3k?
5. **Gondola Double.** Is publishing its grooves as rails acceptable, or should this fixture get more than 40 sockets?
6. **Hulls.** The corner's L shelves have no collision (4-hull spec), and neither does the box tier's back panel
   (6-hull limit). Is that acceptable, or should the limits be raised for these two?

## Renders (`WorkFiles/cardshop/families/a_shelving/`)

| Render | What it shows |
|---|---|
| `slatwall_1000_34.png` | The panel |
| `slatwall_end_detail.png` | The T-slot at the panel end |
| `slatwall_fitted_34.png` | A panel with a shelf and 7 hooks on `Groove_*` sockets, as sheet 19 panel 5 |
| `slatwall_mount_side.png` | The hook tab and bracket tongues in the grooves |
| `hook_34.png` | The three hooks, from the sheet's angle |
| `hook_side.png` | Hook side view |
| `shelf_slat_34.png` | The shelf mounted on a panel |
| `shelf_slat_side.png` | Shelf side view |
| `gondola_single_34.png` | Single with 2 shelves on `Mount_F_*` |
| `gondola_double_34.png` | Double with 3 shelves a side |
| `gondola_endcap_34.png` | End cap |
| `gondola_corner_34.png` | Inside corner |
| `gondola_detail.png` | Slotted upright, T grooves, shelf |
| `gondola_base_detail.png` | Deck pan, price channel, set-back kick plate, foot |
| `gondola_shelf_side.png` | Bracket tongues and the sloped price channel |
| `rack_wire_34.png` | Wire rack |
| `rack_wire_detail.png` | Truss, collar, ring grooves, black cap |
| `box_tier_34.png` | Box tier shelf |
| `box_tier_section.png` | A section at x = 0: the tier profile |

Every render uses the final geometry.

## Process notes

- Renders were made with a scratch copy of `csk_shot.py` that adds palette entries for the new slots, a close-up target,
  section cuts and two camera angles. The shared tool is unchanged.
- One build run without arguments wrote the default `WorkFiles/cardshop/g1/build_report.json` (the lock check failed
  first). I deleted it right away.
- The lead committed a checkpoint of this module (fc4cf84) while I worked; the file now differs from that checkpoint.
- No other file outside this family's module, report and render folder was touched.
