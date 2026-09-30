# Family b_pack: B1 pack states, B2 L box, B3 collector box, B7 tuck box (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_b_pack.py`, 9 item keys prefixed `b_pack_`. The spec rows are in CARDSHOP_KIT_SPEC.md 3.B
(B1, B2, B3, B7). The references are sheet 4 (`csk_pack.png`), sheet 5 (`csk_booster_box.png`), sheet 10
(`csk_collector_box.png`) and sheet 12 (the two-tone print rule only).

**Build:** one build of all 9 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD, and the kit checks
pass 10/10 (hashes, deny scan).

**Verification build:** the same keys were built with the G1 `pack` and `card`, so the contain grids are fit-tested
against real render bounds. The kit checks pass 45/45, including 33/33 contain fits:
- the 24 L-box pack slots;
- the 8 collector pack slots;
- the collector's `Cards` slot.

**Reuse:** the L box calls geom's `_box_shell`, `_window_outline`, `_dieline`, `item_box_lid` and `item_box_sealed`
with an L dict. The lid and sealed builders read `spec.BOX_BOOSTER_S`, so a small context manager swaps the L dict in
and then restores it. Nothing is copied. The pack states reuse `spec.PACK_STD`, the G1 column and tooth layout, and
the edge-band UV idea.

**Noise:** all noise is a deterministic integer hash, and the builders were checked to produce identical output twice.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | Hulls |
|---|---|---|---|---|---|---|
| b_pack_open | SM_CSK_Pack_Std_Open | 1870 / 582 / 146 | **1950** (spec 250) | PASS | Seat, Grip, Face, CardsOut, Stack | 1 |
| b_pack_strip | SM_CSK_Pack_Std_Strip | 828 / 256 / 96 | **850** (spec 40) | PASS | Seat, Grip | 1 (padded to 2 mm) |
| b_pack_wrapper | SM_CSK_Pack_Std_Wrapper | 1740 / 716 / 296 | **1750** (spec 200) | PASS | Seat, Grip, Face | 1 |
| b_pack_box_l | SM_CSK_Box_Booster_L | 164 / 60 / 44 | 400 | PASS | Seat, Pack_01..24, Lid, Grip, Face, Stack (29) | 1 |
| b_pack_box_l_lid | SM_CSK_Box_Booster_L_Lid | 52 | 150 | PASS | Seat | 1 |
| b_pack_box_l_sealed | SM_CSK_Box_Booster_L_Sealed (extra, as the S) | 136 | 400 | PASS | Seat, Grip, Face, Stack | 1 |
| b_pack_collector | SM_CSK_Box_Collector | 388 / 128 / 44 | 600 | PASS | Seat, Pack_01..08, Dice, Cards, Sleeves, Lid, Stack (14) | 1 |
| b_pack_collector_lid | SM_CSK_Box_Collector_Lid | 60 | 300 | PASS | Seat | 1 |
| b_pack_tuck | SM_CSK_Deck_Tuck | 142 (LOD0 only) | 150 | PASS | Seat, Grip, Face, Stack | 1 |

**Classes:**
- `BoxL` for the L box and the sealed L box.
- `BoxC` for the collector box (added in `CLASSES`, with the same values as fam_a_shelving's).
- `Deck` for the tuck box.
- null for the Open pack, the Wrapper, the Strip and the lids.

**Moving parts:**
- The L lid is a hinge on X, 0-200°, with a display pose of −100°: geom's S lid with the L numbers.
- The collector lid is a slide on Z, 0-130 mm. It lifts off, and past 118 mm it clears the neck.
  Its pivot is the rim centre, which is the closed position at the base's `Lid` socket (z 42).

## What each item is (sheet notes)

**B1 Open:**
- The bottom crimp is the Sealed pack's: 27 ribbed teeth and the back fin.
- The top is torn off 12 mm below the sealed top, which is the strip's height, along a fine serration.
- The front skin's torn edge sags 8 mm, lowest just right of centre. The back edge is nearly straight.
- The mouth gapes into a lens: the front lifts 6.5 mm and the back drops 2 mm, over the top 30 mm.
- The foil's silver inside is a second surface (`M_CSK_PackInner`): the inner front and inner back skins plus a lip
  along the tear. The inner skins meet in a false bottom 65% of the way up, where the cards would fill.
- The mesh is closed, and every non-print face has an explicit UV band in the U −1 tile.
- It uses the Sealed pack's frame, so the swap happens in place. `.csk.json` has `strip.spawn_mm`, the Strip's Seat
  where it came off.

**B1 Strip:** built to the sheet's strip view, from the teeth down:
- 27 teeth with a pressed rib each, in a 2.6 mm band;
- a seal band with two sharp raised ridges, 3.9 mm;
- wrinkled foil, 5.5 mm, torn along an irregular edge.

**B1 Wrapper:** built to the sheet's picture:
- flattened and lying back up, so the fin seal shows;
- crumpled facets from hashed crease tents and vertex jitter; the top and bottom surfaces share one triangulation, so
  they never cross;
- both crimps with their teeth and ribs;
- the top skin torn away along both long edges, so the bottom skin's silver inside shows. This is a real 0.25 mm step
  with a torn-edge ramp.

**B2 L:**
- the S design at 190 × 76 × 140;
- a die-cut window measured on sheet 5: 168 wide at the rim, 129 at the bottom, 73 deep, R 6;
- no centre divider, because sheet 5's L has none;
- a header tab of 92 × 20, R 6;
- 24 packs in 2 × 12 at 5 mm pitch, the rows centred in the 72 mm inner depth.

**B3 collector:**
- a shoulder-neck telescoping box: a 42 mm light-blue base band;
- a navy neck inset 2.2 mm, rising to 160;
- a 190 × 89 × 123 lid that rests on the band. This follows the picture; the spec's lid depth of 30 was E;
- a black tray 3 mm under the neck rim: two pack wells (2 × 4 standing on edge) at the back, and dice / cards /
  sleeves pockets in front;
- a navy liner inside the lid and the neck, printed on tile (1, 0).

**B7 tuck box:**
- a closed carton, 70 × 30 × 95;
- the half-moon thumb cut in the front panel's top edge, as a real 0.4 mm recess (the board) with the tuck flap's
  print on its floor. It is 30 wide and 11.5 deep, flat-bottomed, with 2 mm rounded shoulders, matched against the
  sheet's close-up at the same view;
- shrink film with soft corners, as the S sealed box.

## Deviations from the spec (and why)

**B1 pack states:**
1. **Budgets raised:**
   - Open 250 → 1950;
   - Wrapper 200 → 1750;
   - Strip 40 → 850, so it has three LODs instead of LOD0 only.

   The sheet's 27 real teeth are the precedent: the Sealed pack went 300 → 1500 for the same reason. The Open also
   carries the silver inside, the Wrapper has two toothed crimps plus crumple, and the Strip is almost all teeth.
2. **Second slot `M_CSK_PackInner` on the Open and the Wrapper.** The lead asked for it; the spec's B1 lists one slot.
3. **Class null on the Open, Wrapper and Strip.** An opened pack's gape (11.6 mm) is thicker than the 4 / 5 mm box
   pitch, so as class `Pack` it would be fit-tested into boxes and fail. The Wrapper and Strip are litter.
4. **Sockets on the Wrapper and Strip.** B1's socket list is for a pack, so the Wrapper has no `CardsOut` / `Stack`
   and the Strip has only `Seat` and `Grip`.
5. **Wrapper.** The log says "silver showing at the torn end", but sheet 4 shows both crimps whole and the silver along
   the long sides. It is built to the picture.
6. **Strip.** The strip view (teeth band, then a seal band with horizontal ridges) differs from the pack close-up (ribs
   over the whole 7.1 mm crimp), which the Sealed pack follows. The Strip is built to its own view.

**B2 L box:**
7. **Material slot.** `M_CSK_BoxPrintL` replaces `M_CSK_BoxPrint`, so the default MI can point at the BoxesL atlas.
8. **Two packs across.** The pack's 67 mm width is M, so the numbers win over sheet 5, which draws about 7 narrow packs.
9. **No divider** (picture).
10. **Rows centred in depth.** The S box starts its rows at the front.
11. **`SM_CSK_Box_Booster_L_Sealed` built as an extra mesh**, as the S has one. Drop the key if it isn't wanted.

**B3 collector:**
12. **Lid depth 123 and a 42 mm band** (picture over the E 30), with a neck to 160 so that standing packs fit.
13. **Tray layout.** The spec's 2 × 4 packs standing on edge are kept. The sheet draws 8 packs in one row with cards
    lying flat, which needs about 155 mm of depth: its top view measures 190 × ~155. The printed 89 wins.
    Consequences:
    - cards and sleeves stand in 58 mm-deep pockets; a lying card does not fit in 89;
    - the dice lie 2 × 3;
    - the tray is modelled as a solid insert with the pockets cut, not a thin vacuum-formed shell (only its top shows).
14. **`Stack` socket added**, per the 4.3 rule. The collector's `Dice` and `Sleeves` contain entries have
    `accepts: []` (no class exists yet) and carry `holds` notes.
15. **New dieline.** The collector uses one BoxesL cell as a 1024 × 512 mm sheet, with outside print on tile (0, 0)
    and a navy liner on (1, 0). This replaces the spec's "base wrap 558 × 165 + lid 250 × 149" plan, which assumed a
    30 mm lid.
16. **The lid is five convex board slabs** (top panel, full-depth sides, front and back between them):
    - Why: the build's winding check (for `*_Lid` names) assumes convex parts, and a one-shell cup's inside faces
      point at its own centre.
    - Joins: each join is offset 0.02 mm, so there are no coplanar overlaps and no coincident vertices.
    - No bevel: slab bevels would groove the joins.

**B7 tuck box:**
17. **`M_CSK_Film` shell added.** Sheet 10's sealed view is shrink-wrapped; the spec lists Print only.

## New material slot names

- `M_CSK_PackInner`: the foil's silver inside (Open, Wrapper).
- `M_CSK_BoxPrintL`: box print on the BoxesL atlas (L box, L lid, L sealed, collector, collector lid).
- `M_CSK_Tray`: the collector's glossy black vacuum-formed tray.

## Not built

- **A sealed (shrink-film) state of the collector box.** The sheet shows one; the spec lists only box + lid.
- **Tuck box details** below the budget's reach (150 tris, LOD0 only): the dust-flap slits at the top corners and the
  lid's rounded front corners (both sub-millimetre); and an unsealed tuck box.
- **The cards** seen in the Open pack's mouth, and **the dice, cards and sleeves** in the collector. These are separate
  items; the sockets are there.

## Open questions for the user

1. **B3 depth.** Keep 89 mm (the spec and the printed number) with the 2 × 4 standing packs and the standing
   cards and sleeves? Or widen the box to about 155 mm to match sheet 10's layout: 8 packs in one row, with cards and
   sleeves lying flat? The second changes the `BoxC` class and the shelf grids. As built, the collector does not pass
   a blind test against sheet 10's lid-lifted view: a tall neck with standing contents against the sheet's shallow
   tray (see `cmp_collector.png`). No arrangement at 89 mm can reproduce the sheet's layout with 67 × 117 mm packs.
2. **Wrapper crimps.** Sheet 4 draws both crimps whole, but the state chain is Sealed → Open (top torn off) → Wrapper.
   Keep the picture, or tear the wrapper's top end like the Open?
3. **Triangle budgets.** Accept the raised budgets for the three pack states (1950 / 1750 / 850 against the spec's
   E 250 / 200 / 40)?
4. **L box packs.** Accept 2 packs across, as the numbers require, although sheet 5 draws many narrow packs?
5. **Tuck box film.** Keep the film in the tuck box mesh (a buyer hides it with a material), or make a separate
   unsealed mesh?
6. **For the lead:** measured with the same method as the L box, sheet 5's S window reads 128 / 87 / 64
   (top / bottom / depth), against geom's 126 / 100 / 70. geom was not changed.

## Renders (`WorkFiles/cardshop/families/b_pack/`)

- **Side-by-sides with the sheet:** `cmp_open.png`, `cmp_strip.png`, `cmp_wrapper.png`, `cmp_box_l.png`,
  `cmp_collector.png`, `cmp_tuck.png`.
- **Open pack:** `open_up34.png`, `open_34.png`, `open_mouth.png`.
- **Strip and Wrapper:** `strip_top.png`, `strip_34.png`, `wrapper_34.png`, `wrapper_top.png`.
- **L box:** `box_l_open_34.png` and `box_l_open_front.png` (with 24 Sealed packs at the sockets and the lid at the
  header pose), `box_l_sealed_34.png`.
- **Collector:** `collector_lifted_34.png` (packs and cards at the sockets), `collector_top.png`,
  `collector_closed_34.png`.
- **Tuck box:** `tuck_34.png`, `tuck_notch.png`.
- **LODs:** `lods_open_wrapper_collector.png`, showing LOD1 and LOD2.

The renders are shape checks: the shot tool guesses materials from the slot names, so the print tiles all show as one
colour and the two-tone bands (print) do not appear.
