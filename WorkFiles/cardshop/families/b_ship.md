# Family b_ship: distributor carton, delivery boxes, hanging blister (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_b_ship.py`, 11 item keys prefixed `b_ship_`. The spec rows are
CARDSHOP_KIT_SPEC.md 3.B B4, B5 and B6. The references are sheet 11 (`csk_cartons.png`) and sheet 12 item 1
(`csk_blister_retail.png`). I looked at both on disk and measured them with zoomed crops.

**Build:** one build of all 11 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD, and the kit
checks pass 12/12 (hashes and the deny scan).

**Verification build:** the 11 keys plus the G1 `pack`, `box` and `slab` pass. The kit checks pass 81/81, including
the contain fits for `Box_01..06`, `Pack_01..02` and every `Contents` class.

**Extra check** (`scratchpad/fam_b_ship/extra_check.py`, bpy). It seats the real G1 item of each class in every
CONTAIN socket and every `Contents` grid slot:
- It runs `fit.check_level` on each grid (16 grids × volume, cell and hulls).
- It runs a BVH triangle-intersection test against the container's LOD0 and the neighbouring items. Items are shrunk by
  0.05% and lifted by 0.02 mm, so touching is allowed.
- Everything passes: 20/20 seatings and 48/48 grid tests. A negative control (a pack pushed 0.2 mm into the blister
  card) is caught.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | Hulls |
|---|---|---|---|---|---|---|
| b_ship_carton_closed | SM_CSK_Carton_Box6_Closed | 132 (LOD0 only) | 500 | PASS | 11 | 1 |
| b_ship_carton_open | SM_CSK_Carton_Box6_Open | 280 / 152 / 88 | 800 | PASS | 10 | 5 |
| b_ship_carton_flat | SM_CSK_Carton_Box6_Flat | 276 / 140 / 44 | **300** (spec 100) | PASS | 4 | 1 |
| b_ship_{s,m,l}_closed | SM_CSK_Box_Ship_{S,M,L}_Closed | 120 (LOD0 only) | 300 | PASS | 6 | 1 |
| b_ship_{s,m,l}_open | SM_CSK_Box_Ship_{S,M,L}_Open | 268 / 140 / 76 | 700 | PASS | 4 | 5 |
| b_ship_flat | SM_CSK_Box_Ship_Flat | 276 / 140 / 44 | 300 | PASS | 3 | 1 |
| b_ship_blister | SM_CSK_Blister_Pack | 448 / 228 / 24 | **500** (spec 300) | PASS | 6 | 1 |

**Sockets** (every mesh also has `Seat`):
- **Carton Closed / Open:**
  - `Box_01..06` (CONTAIN, BoxS standing in a row at 80 pitch, turned 90° about Z, on the 4 mm floor).
  - `Label`, on the label face, with +Z facing -X.
  - `Grip_L` and `Grip_R`, at the end-face centres.
  - `Stack`: Closed only, at H + 0.2 of tape.
- **Carton Flat:** `Grip_L`, `Grip_R` and `Stack`.
- **Ship boxes Closed / Open:**
  - `Contents`: CONTAIN, at the floor centre. The `.csk.json` `contain.Contents` holds the per-class `solve_grid`
    grids: S gets Pack and Slab; M and L get Pack, BoxS and Slab.
  - `Label`, at the -X end centre, with +Z facing -X.
  - `Grip`, at the front face centre.
  - `Tape` and `Stack`: Closed only.
- **Ship Flat:** `Grip` and `Stack`.
- **Blister:**
  - `Hang`: at the euro slot's peak on the card mid-plane, rotated -90° about X. Item world = hook point × inverse(Hang)
    hangs it plumb, with the bubble toward the customer.
  - `Pack_01..02` (CONTAIN): lying face up, one per cup.
  - `Face` and `Stack`, at T = 20.

**Classes (`CLASSES`):**
- `Carton`: 492.4 × 152 × 137.2, pitch 512 × 172.
- `BoxShipS`, `BoxShipM` and `BoxShipL`: render footprints, pitch +20.
- Closed states carry the class. Open and Flat have `class: null`, with `class_when_closed` or `state` in the data.
- The blister is `Hang` (T 20, `hang.pitch_mm` 22).

## Construction (sheet 11 / 12)

- **Closed:**
  - A block with 1.5 folded-edge bevels.
  - A crisp 0.8 × 0.6 joint line across each end at the top flap joint.
  - One tape strip, 0.2 proud and sunk 0.5. It follows the bevels along the top seam and down both ends.
  - B4 adds a blank 95 × 75 label on the -X end, with the tape tab lying over its top (the sheet close-up).
- **Open:**
  - A walled shell with a 4 mm board, a floor and a rim.
  - Four real W/2-deep flaps. Each is a bent-board prism rising from its fold line, with a 2.2 fold radius.
  - The pose, read off all four sheet 11 open views: back 15°, ends 45° and front 100° outward from vertical.
- **Flat:** knocked down, per the sheet 11 notes decided 2026-09-29, at (L + W) × (H + W) × 8.
  - Half-round 180° folds at both outer edges.
  - Flap rows with 8 mm slots: the top layer's at the L|W score, the bottom layer's mirrored, and half slots at the
    folds.
  - V creases on every fold line on both faces.
- **Blister:**
  - A 180 × 250 × 0.6 card with R4 corners and a real euro-slot hole: 38.3 × 8.6, with an r 6 half-round peak.
  - A twin-cup PET bubble, one cup per pack, with a 1 mm divider web.
  - The bubble is a closed 0.4 thin shell: flange 174 × 152, cups 78 × 136 at the base, 3° draft, a 3 mm top
    chamfer, 20 overall.

## Deviations from the spec (and why)

- **B4 tape width:** 36 (sheet 11 reads 37), with 45 mm tabs down each end (read off the sheet). B5 uses 48 mm tape
  (E, because the sheet draws 40-78 inconsistently by size). The tabs run 0.88 H down each end (the sheet reads
  0.85-0.9).
- **B4 Open keeps the label:** the sheet's open view omits it (AI drift). I kept it so the Closed/Open state swap is
  consistent.
- **B5 has no Label geometry and no `M_CSK_Label` slot:** sheet 11 shows no label on the delivery boxes (invent
  nothing). The `Label` socket marks where one goes.
- **Open states have no `Stack` socket, and B5 Open has no `Tape` socket:** nothing stacks on raised flaps, and the
  tape is cut. The sheet's open views show no tape.
- **`SM_CSK_Box_Ship_Flat` = the M box knocked down, 711 × 559 × 8 (D):** the spec's 700 × 450 (E) matches no box. The
  sheet notes say to build the knocked-down flat.
- **Flat details not modelled:** the glue flap (hidden between the layers). The flap slots are 8 (E; the sheet reads
  8-9).
- **Budgets raised:**
  - Carton_Box6_Flat 100 → 300: slots, two rounded folds and 6 creases as real geometry.
  - Blister 300 → 500: the closed twin-cup shell plus the real slot hole.
- **Blister:**
  - Euro slot 38.3 × 8.6 plus the peak (sheet 12; spec E 30 × 10).
  - Bubble 19.4 deep (sheet 12 side view; spec E 14).
  - The bubble is sized to the M 117 pack: cups 78 × 136 (spec E 150 × 130 interior; the sheet's dome reads 159 wide).
    The sheet's bubble is taller (flange 174) because it draws the packs 142 long. The bubble is centred where the
    sheet's is (y -25.3), which leaves a 74 header (sheet 64).
- **Class codes:** `BoxShipS/M/L` rather than a single `BoxShip`, because class footprints are single-size.

## New material slot names

`M_CSK_Cardboard` (kraft corrugated), `M_CSK_Tape` (brown packing tape), `M_CSK_Label` (Labels atlas, label tile
(0,1)). Reused: `M_CSK_BoxPrint`, `M_CSK_Film`.

## Not built

Nothing from B4-B6 is left unbuilt. UV2 metre-scale tiling for a corrugated tileable is not written, because `mesh.py`
has no hook for it.

## Open questions for the user

1. **The carton doesn't fit sealed boxes.** Sealed booster boxes are 80.8 thick (0.4 film), and 6 × 80.8 = 484.8 > the
   484 inner. The fit test uses the opened G1 box, which passes. Should the carton grow to inner 490 / outer 498
   (flat 650 × 289)?
2. **One ship flat or three?** Should the one `Box_Ship_Flat` stay the M size, or should there be S, M and L flats (the
   sheet draws one per size)?
3. **Blister bubble:** keep the pack-sized bubble (current), or stretch it to the sheet's taller 174 flange, with gaps
   around the packs?
4. **Class codes:** are `BoxShipS/M/L` acceptable, for H1 racks and the hand truck to accept?

## Renders (`WorkFiles/cardshop/families/b_ship/`)

- `carton_closed_34L.png`, `carton_closed_left.png`, `carton_open_34.png` (with 6 G1 boxes), `carton_open_right.png`,
  `carton_flat_top.png`
- `ship_closed_SML_34L.png`, `ship_open_SML_34.png`, `ship_flat_top.png`
- `blister_hang_front.png`, `blister_hang_34.png`, `blister_hang_right.png` (hanging, with 2 G1 packs)
- Sheet-vs-build pairs: `cmp_carton_closed.png`, `cmp_carton_open.png`, `cmp_carton_flat.png`, `cmp_ship_closed.png`,
  `cmp_ship_open.png`, `cmp_blister.png`, `cmp_blister_side.png`

The shot tool guesses materials (the tape and label render grey); these are shape checks.
