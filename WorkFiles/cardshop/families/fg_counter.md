# Family fg_counter: play tables, folding chair, cash counter, kraft bag (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_fg_counter.py`, 8 item keys prefixed `fg_counter_`. It covers spec rows
F1, F2 and G1, G11 (CARDSHOP_KIT_SPEC.md 3.F and 3.G), plus the two states the reference log adds:
`SM_CSK_Chair_Folding_Folded` (sheet 24) and `SM_CSK_Bag_Paper_Flat` (sheet 27). I opened sheets 24, 25 and 27 on
disk, measured them with Pillow crops and pixel scans, and compared each render side by side with its sheet crop.

**Build:** one build of all 8 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD, and the kit
checks pass 9/9 (hashes and deny scan).

**Verification build:** I also built the bag and the chair together with the G1 card, top-loader, slab and pack. That
build passes 13/13 kit checks, including `contain_fit` 6/6 for the bag's `Contents` socket.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets (+ `Seat`) | Hulls |
|---|---|---|---|---|---|---|
| fg_counter_table_2 | SM_CSK_Table_Play_2 (914) | 884 / 420 / 84 | 1000 | PASS | `Mat_1A/B`, `Deck_1A/B`, `Zone_1`, `Chair_01..02` | 3 |
| fg_counter_table_4 | SM_CSK_Table_Play_4 (1524) | 884 / 420 / 84 | 1000 | PASS | as above for matches 1-2, `Chair_01..04` | 3 |
| fg_counter_table_6 | SM_CSK_Table_Play_6 (1829) | 884 / 420 / 84 | 1000 | PASS | as above for matches 1-3, `Chair_01..06` (22 in all) | 3 |
| fg_counter_chair | SM_CSK_Chair_Folding | 1000 / 488 / 152 | 1200 | PASS | `Sit`, `Grip` | 3 |
| fg_counter_chair_folded | SM_CSK_Chair_Folding_Folded | 1000 / 488 / 152 | 1200 (parent's) | PASS | `Grip` | 1 |
| fg_counter_counter | SM_CSK_Counter_1397 | 924 / 252 / 120 | 2000 | PASS | `POS`, `Drawer`, `Terminal`, `Printer`, `Scanner`, `Drop`, `PriceGun`, `Bag`, `Phone`, `Staff`, `Snap_L`, `Snap_R` | 4 |
| fg_counter_bag | SM_CSK_Bag_Paper | 420 / 172 / 92 | **450** (spec 400) | PASS | `Contents` (CONTAIN), `Grip` | 1 |
| fg_counter_bag_flat | SM_CSK_Bag_Paper_Flat | 304 / 108 / 40 | 450 (parent's) | PASS | `Grip`, `Stack` | 1 |

**Render bounds (mm):**

| Mesh | Render bounds | What sets it |
|---|---|---|
| Tables | L × 762 × 737 exactly | |
| Chair | 450 × 520 × 800 exactly | The feet are placed so the tilted caps land on ±260 |
| Folded chair | 450 × 66 × 901 | |
| Counter | 1397 × 610 × 968.5 | The top grommet's flange stands 3.5 above the 965 top |
| Bag | 250 × 130 × 402 | The handles rise 100 above the 300 body |
| Flat bag | 250 × 385 × 72 | The handle loops spring out of the mouth |

**Socket conventions:**
- The kit rule is that an item's front faces −Y. A rotation of 180° about Z turns something to face +Y.
- **Tables:**
  - Player A sits on the customer side (−Y), player B on +Y.
  - `Mat_<m>A/B` is the playmat `Seat` on the top at y ±190.5 (2 × 356 fits in 762, as the spec derives). The B mat is
    turned 180°.
  - `Deck_<m>A/B` sits on the mat (z 739), at the player's right-hand far corner.
  - `Zone_<m>` is the match centre.
  - `Chair_NN` is the chair's `Seat`, at y ±640 and facing the table: odd numbers are side A (rot 180), even are
    side B.
  - The matches share the length evenly: 1 on the 914, 2 on the 1524, 3 on the 1829.
- **Chair:** `Sit` is the centre of the seat top (z 445). `Grip` is the centre of the top bar.
- **Counter:**
  - Devices on the top (z 965) that face the staff are turned 180°. `Terminal` faces the customer.
  - `Drawer` is the G2 drawer's closed `Seat` on the housing floor (z 775). Its tray slides toward +Y.
  - `Bag` is the bay's oak bottom shelf.
  - `Staff` is the floor point 320 behind the counter, facing the customer.
  - `Snap_L` and `Snap_R` sit at the worktop ends.
- **Bag:**
  - `Contents` is the inside floor, turned 90° about Z. It accepts Card, CardProt, Slab, Pack and Deck.
  - `Grip` is the top of the handles.
- **Flat bag:** `Grip` is at the mouth edge. `Stack` has a pitch of 5, max 25.

## What was built (from the sheets)

- **F1 tables (sheet 24):**
  - A white blow-moulded top, 38 thick, with R40 plan corners. Its top edge is a real quarter round (R8, 3 rings)
    with an R4 round under it.
  - Per end, a dark grey trestle frame made of 25.4 tube legs:
    - the legs are vertical to z 380, then a smooth S-jog 30 out toward the table end, then vertical to the foot;
    - a Ø19 cross brace at the jog;
    - black foot caps;
    - a flat-bar folding strut from each leg (z 530) to the underside, 150 inboard;
    - small brackets under the top.
  - LOD1 drops the S and the brackets. LOD2 is the top, straight legs and braces.
- **F2 chair (sheet 24):**
  - **Frame:** one Ø22 tube runs from the front feet up into the back posts and over R90 top corners. The rear legs sit
    inside it and pivot on it at z 470, with bolts. There are two low Ø16 cross bars, and black caps on the feet, cut
    flat by the floor.
  - **Seat:** a steel pan (a band with rolled edges) under a thick vinyl pad with an R14 rounded top edge. Hangers
    join the seat to the main tubes.
  - **Back:** a padded back between the posts that follows the top corners. It stands 22 proud in front with an R10
    padded round.
  - All the rounds are modelled as real rings. The auto bevel is off, because the budget could not afford it.
- **F2 Folded:**
  - The main frame stands upright on its front feet.
  - The rear legs fold parallel, 22 behind it.
  - The seat is turned up inside the frame, just under the back pad, with its pad facing +Y. Its hangers meet the
    posts.
  - The geometry is chosen so all four feet stand when folded, as the sheet shows.
- **G1 counter (sheet 25):**
  - **Carcass:** light-oak, cut with exact booleans from one block, with a 1.5 bevel on the block edges. It sits on a
    recessed black kick (90 high, 40 in) that runs along the customer side, both ends and under the bay. The knee
    space is open to the floor.
  - **Worktop:** white, 60 thick, overhanging 25 all round. It has R20 plan corners and an R12 rounded top edge (real
    rings).
  - **Customer side:** a plain oak panel.
  - **Staff side:**
    - the bag bay at +X (the staff's left), with a white middle shelf at z 500-520 and the oak bottom as the bag
      shelf;
    - a partition that runs to the floor;
    - the knee space at −X, with the cash-drawer housing slung under the top from the partition (440 × 130 inner,
      450 deep, fits G2's 409 × 417 × 112);
    - a black grommet low in the modesty panel;
    - a grommet in the top: a real Ø62 hole with a black liner and flange.
- **G11 bag (sheet 27):**
  - The paper is a real shell: outside and inside skins, 0.5 thick, with a rim.
  - The side gussets fold in along their centre crease, 5 at z 65 and 14 at the rim. The bottom gusset triangles are
    real fold edges.
  - The front has a V-crease 95 up (the bottom fold).
  - A turned top band 40 deep runs inside the rim.
  - Two twisted paper handles are glued inside the front and back walls. Each is a Ø5.5 cord with 6 sides and a real
    40°-per-segment twist, bent into a superellipse arch 108 wide and 100 high.
- **G11 Flat:**
  - A layered 250 × 300 × 5 slab, lying front up in the flat-item pose.
  - The gusset fold shows as a notch between the layers along both long edges, and the bottom-fold V-crease runs
    across the front.
  - The two handle loops come out of the mouth nested and spring up (40° and 28°).
- **Prints:**
  - On the bag, the front and back outer panels are `M_CSK_BagPrint` and fill UV0 tiles (0,0) and (1,0), for the
    shop-logo cell.
  - On the flat bag, the top and bottom faces carry the same mapping.

## Deviations from the spec (and why)

- **F1 top thickness 38:** sheet 24's edge reads 30-38 over its rounds, on all three tables. Blow-moulded tables are
  usually 50. The picture wins over an E value.
- **F1 legs:** the jog heights, the strut, the brackets and the cap sizes are read off sheet 24 (E values).
- **F1, the 1829 table:** it keeps the spec's 3 matches (3 × 609.6 = 1828.8, D; the user accepted this pick). As a
  result, the outer mats' corners overhang the top's R40 plan corners by up to about 8.
- **F1 Deck socket:** its place on the mat is E. It should line up with the playmat's own `Zone_Deck` (E5, built by
  another family).
- **F2 geometry (E and D):**
  - The back top sits 79 in front of the rear feet (sheet 24 reads 60-80). That places the pivot half way, so all four
    feet stand when folded (D).
  - The seat is 350 × 360 (E): it has to fit 2 mm inside the rear legs.
  - The seat front sits over the front feet, so the depth stays 520.
- **F2 Folded height 901:** the folded frame stands at the length of its back tube. Sheet 24's folded view repeats
  the open call-out of 800, but a frame that is 800 tall open at this lean cannot fold shorter. The folded depth is
  66.
- **G1 numbers:**
  - The top is 60 thick (sheet 25 measured 60-70 against the 965 call-out).
  - The kick is 90 (measured at about 0.14 × the oak height).
  - The 25 overhang and 25 panels are E.
- **G1 hulls: 4, not the spec's 3.** The knee space is open, so the modesty panel and the −X end panel need boxes of
  their own. The four are the top, the bay pedestal with the partition, the modesty panel and the −X end panel.
- **G1 device sockets:** sheet 25's two views place the devices differently. The layout here is E: the screen sits
  next to the top grommet and the terminal is on the customer edge.
- **G1 modesty-panel grommet:** it is a blind cup (a black flange plus a 13-deep pocket), so the customer face stays
  plain as sheet 25 draws it.
- **G11 budget 400 → 450:** the two twisted cords and the front V-crease are both drawn on sheet 27.
- **G11 contents:** the `Contents` socket is turned 90°, because a slab (134 long) does not fit the 128-deep inside
  unturned. A BoxS fits only unturned, so it is not in `accepts`.
- **Bag LOD2:** it is 22% of LOD0, a little over the guide's "about 5-20%". It keeps the open mouth, the inside and
  the handles.
- **Added states:** `SM_CSK_Chair_Folding_Folded` and `SM_CSK_Bag_Paper_Flat` take their parents' budgets. They come
  from the reference log; neither has a spec row.

## New material slot names (the lead adds their Unreal instances)

| Slot | Used on | Default look |
|---|---|---|
| `M_CSK_TableTop` | F1 top | White HDPE. Tint MIs for black and wood (spec "Top (tint)") |
| `M_CSK_SteelDark` | F1 legs, struts and brackets | Dark grey powder coat (sheet 24). A new slot, because `M_CSK_Steel` already means white on the card tables and light grey on the gondolas |
| `M_CSK_SteelBlack` | F2 frame and seat pan | Black powder-coated steel |
| `M_CSK_Vinyl` | F2 seat and back pads | Black vinyl (spec "Seat (tint)") |
| `M_CSK_Kraft` | G11 paper and handles | Kraft (tint) |
| `M_CSK_BagPrint` | G11 outer front and back | Print master, shop-logo cell from the Signs atlas |

Reused slots: `M_CSK_Rubber` (foot caps); `M_CSK_Oak`, `M_CSK_Laminate` and `M_CSK_Base` (the counter's Carcass,
Top and Trim).

## Not built

Nothing. All four rows and both added states are built.

## Open questions for the user

1. **Folded chair height:** it is 901 tall. Sheet 24's folded view says 800, but a real frame that is 800 tall open
   folds taller. Is 901 all right?
2. **Counter device layout:** sheet 25's two views disagree. Is the E layout here all right? It has the screen and
   grommet at −X (over the knee space), the printer in the middle, the scanner and price gun at +X, and the terminal
   on the customer edge.
3. **Bag print default:** sheet 27 shows plain kraft, while the spec has a shop-logo print cell. Should the default MI
   show the logo cell or stay blank?
4. **Modesty-panel grommet:** it is a blind cup, so the customer face stays plain. Should it be a through hole instead?
5. **Mat and deck layout:** the mats sit y ±190.5 on the tables. The deck position should be checked against the
   playmat's zones once E5 exists.

## Renders (`WorkFiles/cardshop/families/fg_counter/`)

- **Tables:** `table6_34.png`, `table6_front.png`, `table2_34.png`, `table4_34.png`, and `table6_chairs_34.png` (six
  chairs placed at the `Chair_NN` sockets).
- **Chair:** `chair_34.png`, `chair_folded_34.png`, `chair_front_right.png` (the open and folded chairs side on).
- **Counter:** `counter_customer.png`, `counter_staff.png` (the sheet 25 staff angle), `counter_back.png` (the staff
  face, square on).
- **Bag:** `bag_34.png`, `bag_flat_34.png`.
- **Side by sides with the sheet crops:** `cmp_chair.png`, `cmp_table.png`, `cmp_counter.png`, `cmp_bag.png`.
