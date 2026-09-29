# Family h_backroom: warehouse rack, workbench, mailers, tape gun, bin, trash bag, hand truck (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_h_backroom.py`. It has 11 item keys, all prefixed `h_backroom_`, and covers
CARDSHOP_KIT_SPEC.md 3.H, rows H1-H7. The references are:
- sheet 27, `csk_bag_mailers.png`: the mailers and the tape gun;
- sheet 28, `csk_backroom.png`: the rack, the workbench and the hand truck;
- sheet 29, `csk_bins.png`: the bin and the trash bag.

I opened every sheet, measured zoomed crops with Pillow, read the "Sheet 27/28/29 notes" in REFERENCE_LOG.md, and
compared every render with its crop side by side.

**Build:** one build of all 11 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD, and the kit
checks pass 13/13 (11 hashes, the fixture socket count and the deny scan).

**Verification build:** the 11 keys plus b_ship's carton and S/M/L delivery boxes, the G1 `card` and the G1
`toploader`. It passes 112/112:
- 20 rack level grids, each with volume, cell, hull and stack checks (5 levels × Carton, BoxShipS, BoxShipM,
  BoxShipL);
- 13 contain fits: the four mailers' `Contents` (Card, CardProt) and the hand truck's `Nose`, `Nose_M` and `Nose_L`.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | Hulls |
|---|---|---|---|---|---|---|
| h_backroom_rack | SM_CSK_Rack_Warehouse_1829 | 19100 / 4300 / 876 | **20000** (spec 1500) | PASS | 23 (Seat, Level_L1..L5, Compartment_L1..L5_01..03, Snap_L, Snap_R) | 7 |
| h_backroom_workbench | SM_CSK_Workbench_1524 | 5476 / 1348 / 324 | **6000** (spec 1500) | PASS | 8 (Seat, Work, BulkOut, Tool_01..04, Lamp) | 4 |
| h_backroom_mailer_s | SM_CSK_Mailer_S | 108 (LOD0 only) | 150 | PASS | 4 (Seat, Contents, Label, Grip) | 1 (2 mm) |
| h_backroom_mailer_l | SM_CSK_Mailer_L | 108 (LOD0 only) | 150 | PASS | 4 | 1 |
| h_backroom_mailer_s_open | SM_CSK_Mailer_S_Open | 124 (LOD0 only) | 150 | PASS | 4 | 1 |
| h_backroom_mailer_l_open | SM_CSK_Mailer_L_Open | 124 (LOD0 only) | 150 | PASS | 4 | 1 |
| h_backroom_tapegun | SM_CSK_TapeGun | 1200 / 526 / 284 | **1200** (spec 800) | PASS | 2 (Seat, Grip) | 1 |
| h_backroom_trashcan | SM_CSK_TrashCan | 1040 / 550 / 180 | **1200** (spec 800) | PASS | 4 (Seat, Lid, Drop, Bag) | 2 |
| h_backroom_trashcan_lid | SM_CSK_TrashCan_Lid | 160 / 84 / 32 | 200 | PASS (winding 0) | 1 (Seat = the swing axis) | 1 |
| h_backroom_trashbag | SM_CSK_TrashBag_Full | 574 / 198 / 82 | 600 | PASS | 2 (Seat, Grip) | 1 |
| h_backroom_handtruck | SM_CSK_HandTruck | 2172 / 956 / 356 | 2500 | PASS | 6 (Seat, Nose, Nose_M, Nose_L, Grip, Axle) | 3 |

Footprints as built (render AABB, mm):

| Mesh | Footprint |
|---|---|
| Rack | 1829 × 610 × 2134 |
| Workbench | 1524 × 762 × 914 |
| Mailers | 100 × 200 × 5 and 150 × 250 × 6 |
| Open mailers | 100 × 240 × 5.3 and 150 × 290 × 6.3 (with the opened flap) |
| Tape gun | 241 × 72.5 × 180 |
| Bin | 422 × 422 × 700 (the band is Ø 422) |
| Trash bag | 450 × 451 × 609 |
| Hand truck | 450 × 499 × 1200 |

**Parts** (in `.csk.json`):
- The bin's flap, `SM_CSK_TrashCan_Lid`, is a `hinge` on X on the `Lid` socket at (0, -116.9, 609). That axis runs
  through the pins at the flap's sides.
- Its range is -45° to 45° (E). Negative angles tip its top inward, as in sheet 29's "Lid swinging" frame.

## What was built (sheet → mesh)

- **H1 rack (sheet 28):**
  - Grey 60 × 45 uprights with real keyhole slots: two columns on the front face and one on the outer side, at a
    45 pitch. Each slot is 16 wide × 28 tall, a round head over a slot half as wide.
  - Five levels. Each has orange 60 × 40 beams on the front, back and both ends, and a 16 mm particle-board deck
    resting on them (its edge shows, as in the deck detail).
  - End plates 30 wide with three rivet holes, over the upright's inner slot column.
  - Black square foot plates, 15 proud and 16 thick.
- **H2 workbench (sheet 28):**
  - A 40 oak top, with the green cutting mat set flush inside a 30 oak edge frame.
  - 55 grey steel legs, each with a slot column on the front face and a hole column on the outer side.
  - Black 66 × 42 foot caps and a grey steel apron.
  - The lower shelf is oak on grey beams, its board top at 248.
  - The mat is print region 1 on tile (0, 0).
- **H3 mailers (sheet 27):** a flat, puffy padded panel inside 4.5 side seams, a 10 flap band at the top end and a
  rounded fold at the bottom. The back lies flat on z = 0.
- **H4 tape gun (sheet 27):**
  - A black housing with a rounded, tilted cheek plate on each side, with two screws.
  - Light grey side plates round the roll's foot, and a far arm to the axle.
  - A tape roll on a cardboard core, with a grey hub showing three dark window pockets and a centre bolt.
  - A serrated 9-tooth blade under a clear guard, and a black pressure roller.
  - A ribbed raked grip with a grey end cap.
  - The tape's end hangs from the blade to the floor, as in view 1.
- **H5 bin (sheet 29):**
  - Ø 400 at the top, tapering to 375 at the base.
  - A raised band, Ø 422 and 48 tall, where the dome meets the body.
  - A dome rising to 700, with the flap opening (a 1.5 gap groove) on its front.
  - Hollow, with a 3 wall and a 4 floor, so the inside shows when the flap swings.
- **H6 trash bag (sheet 29):**
  - The profile was measured row by row off the sheet: the base spreads to 464, the sides are near-straight, and the
    shoulders are round.
  - Pleats run down from a twisted neck tied at 510. A ruffled tuft reaches 610.
  - The crumple is deterministic: a hash of ring and segment, dents only, on a regular triangle lattice.
- **H7 hand truck (sheet 28):**
  - Blue Ø 28 rails turn back 40° at 1000 into handles with black Ø 34 grips.
  - Three Ø 20 cross bars (220 / 590 / 950) and a centre upright.
  - A 350 × 200 × 5 nose plate, with its back turned up 120.
  - Struts from the rails to the axle.
  - Ø 250 × 75 pneumatic wheels with block tread (alternate crown segments 3 lower) and dished grey hubs with a
    centre cap.

## Deviations from the spec (and why)

**H1 rack:**
1. **5 levels, not 4:** the sheet 28 notes say "Build 5". The sockets are `Level_L1..L5` and
   `Compartment_L1..L5_01..03`, 23 in all.
2. **7 hulls, not 6:** one per deck (5) and one per end frame (2).
3. **Budget 1500 → 20000.** The keyhole slots are the rack's defining detail on sheet 28 (the lead's note says
   "keyhole-slot uprights"). There are 468 of them (plus 30 rivet holes), all real pockets.
   - LOD1 (4300, 22 %) keeps rectangular slots on the front faces at every other pitch.
   - LOD2 (876, 4.6 %) has none.
4. **Slot pockets have 45° dark walls, 3 deep** (walls and floor in `M_CSK_SteelBlack`). Two approaches failed first:
   - Straight-walled pockets made thousands of UV islands. UV0's pack (0.02 margin) shrank them to nothing: 232
     degenerate UV faces.
   - One planar fill round a whole slot column made zero-area slivers along the collinear slot sides, which dissolved
     into wire edges. The faces are now built as bands, one per slot row, sharing their edge vertices.
5. **The 1829 × 610 footprint includes the foot plates.** The uprights sit 15 inside them.
6. **Level pitch is 482.5 from L1 = 200.** That leaves 406.5 clear, so the L delivery box (406.2) fits a level. L5's
   clear height is set to 600 (open top, E).
7. **Grid classes:** the grids use b_ship's per-size codes `BoxShipS/M/L` for the spec's "BoxShip". Retail is accepted
   per item, with no fixed grid (as the tier shelf does).

**H2 workbench:**

8. **Budget 1500 → 6000:** the legs' slot and hole columns on sheet 28 are real pockets.
9. **4 hulls, not 3:** the top, the lower shelf and the two end frames. The lower shelf needs its own hull for
   `BulkOut`.

**H3 mailers:**

10. **An `Open` state was added**, per the sheet 27 notes: `SM_CSK_Mailer_S_Open` and `SM_CSK_Mailer_L_Open`. The
    budget is 150 (E, as the sealed ones).
    - The flap (40, E*) lies opened flat past the mouth.
    - The white peel strip on it uses `M_CSK_Paper`.
    - The mouth pocket shows the bubble lining (`M_CSK_Bubble`).
11. **No label geometry and no `M_CSK_Label` slot:** sheet 27 shows plain kraft, as b_ship did for its boxes. The
    `Label` socket marks the face centre.
12. **The seams' fine crimp ribs are not modelled** (surface detail at 150 tris).
13. **`Contents` accepts Card and CardProt.** A 7 mm slab does not fit a 5 or 6 mm mailer.

**H4 tape gun:**

14. **Budget 800 → 1200:** the three-window hub, the two side plates, the serrated blade and the clear guard. It has
    8 material slots.
15. **Length 241, not 250 (E):** sheet 27's own drawing measures about 235-240 at its 250 arrow's scale, so the
    picture wins.

**H5 bin:**

16. **Budget 800 → 1200:** the hollow inside, seen through the swinging flap, and the band's rounds.
17. **The flap is one convex solid** (see open question 1):
    - the dome's surface inside the outline;
    - a 3 mm rim;
    - a faceted back reaching up to about 40 mm into the bin.

    The build's `_Lid` winding test needs convex parts, and a thin curved shell fails it by construction. The back is
    unseen when closed, and it stays inside the bin when the flap swings.

**H6 trash bag:**

18. **Height 610 (spec 600, E):** measured at the sheet's own 450 scale, whose line spans the base exactly. Sheet 29's
    600 arrow is drawn from the knot to the floor, which the drawing contradicts.

**H7 hand truck:**

19. **`Nose_M` and `Nose_L` sockets were added** (the spec lists `Nose`). The load stands against the flange, so each
    box depth needs its own bottom-centre seat:
    - `Nose` takes the Carton and BoxShipS;
    - `Nose_M` and `Nose_L` take the M and L delivery boxes.
20. **Nose plate 350 × 200, as the sheet 28 callout and notes say.** The side view draws it about 250 deep.

## New material slot names (the lead adds their MIs)

| Slot | Used on | Look |
|---|---|---|
| `M_CSK_SteelOrange` | H1 beams and end plates | Orange powder coat (sheet 28) |
| `M_CSK_Chipboard` | H1 decks | Particle board (sheet 28 deck detail) |
| `M_CSK_CuttingMat` | H2 mat | Print: green cutting-mat grid on tile (0, 0) |
| `M_CSK_Bubble` | H3 Open mouth | Bubble lining (sheet 27) |
| `M_CSK_PlasticGrey` | H5 bin and flap; H4 hub and grip cap | Matte grey plastic (sheet 29), tint |
| `M_CSK_BagBlack` | H6 | Glossy black bin-bag film (sheet 29) |
| `M_CSK_SteelBlue` | H7 frame and nose plate | Blue powder coat (sheet 28), tint |

Reused slots:
- `M_CSK_SteelDark`: the rack uprights and the bench legs and apron;
- `M_CSK_SteelBlack`: the rack feet, the bench foot caps and the slot throats;
- `M_CSK_Oak`, `M_CSK_Kraft`, `M_CSK_Paper`, `M_CSK_Tape`, `M_CSK_Board`, `M_CSK_Metal`, `M_CSK_Acrylic` and
  `M_CSK_Rubber`;
- `M_CSK_Plastic`: the tape gun's black frame;
- `M_CSK_Steel`: the tape gun's light grey side plates.

## Not built

Nothing. Every H1-H7 row is built, plus the two `Open` mailers.

## Open questions for the user

1. **Bin flap construction.** The `_Lid` winding test forces a convex flap: a solid with a faceted back inside the
   bin, where the real part is a 3 mm curved shell. Keep it, or allow a thin shell? That would mean exempting this
   part from the test, or naming it `SM_CSK_TrashCan_Flap`.
2. **Rack slot budget.** Keep 20000 tris for 468 real keyhole pockets, or accept a cheaper rack? For example,
   slots on the front faces only (about 13k), or the spec's 1500 with slots as a normal and opacity mask.
3. **Hand truck seats.** Keep the extra `Nose_M` and `Nose_L` sockets, or use one `Nose` with per-class offsets in
   the data?
4. **Workbench lower shelf.** The notes say oak, and it is built in oak. The picture reads closer to the rack's
   particle board: switch it to `M_CSK_Chipboard`?

## Renders (`WorkFiles/cardshop/families/h_backroom/`, 16 samples, shape check; the shot tool guesses colours from slot names)

| Item | Files |
|---|---|
| Rack | `rack_34.png`, `rack_front.png`, `rack_slots.png` (keyhole close-up), `rack_foot.png` |
| Workbench | `bench_34.png`, `bench_legs.png` |
| Mailers | `mailers_top.png`, `mailers_open_mouth.png` |
| Tape gun | `tapegun_side.png`, `tapegun_34.png`, `tapegun_end.png` |
| Bin | `bin_front.png`, `bin_34.png`, `bin_swing.png` (flap at 30°) |
| Trash bag | `bag_front.png`, `bag_34.png` |
| Hand truck | `truck_34.png`, `truck_side.png`, `truck_back.png` |
| All together | `overview_34.png` |
