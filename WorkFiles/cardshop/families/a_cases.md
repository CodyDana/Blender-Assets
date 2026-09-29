# Family a_cases: glass cases A2-A6 (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_a_cases.py`, 19 item keys prefixed `a_cases_`. The spec rows are in
CARDSHOP_KIT_SPEC.md 3.A. The references are sheets 16-18 (the notes in REFERENCE_LOG.md, since the PNGs are not on disk yet) plus
sheets 6-7 and the built A1 for the family look.

**Build:** a single build of all 19 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD, and the kit
checks pass 25/25.

**Verification build:** the same keys were built with the G1 class items (card, top-loader, slab, pack, sealed box), so
the level grids are fit-tested against real render bounds. The kit checks pass 324/324, including all 73 level grids
(volume, cell, hulls against body and glass, stacks).

**Extra checks** (`scratchpad/fam_a_cases/extra_check.py`), all passing:
- the A6 fixed slots: in the cavity, no neighbour overlap, clear of all hulls, and seated on the ledges with 1 mm clearance;
- ray-parity winding on every mesh and LOD;
- hinge sweeps at 1-degree steps: the A3 door 0-100°, the A5 lid 0-80° and the A6 front 0-90° do not touch any glass, rail, post or knuckle.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | Hulls |
|---|---|---|---|---|---|---|
| a_cases_half_1219 / _1778 | SM_CSK_Showcase_Half_{1219,1778} | 868 / 244 / 96 | 2500 | PASS | 28 | 6 |
| a_cases_half_glass_* | SM_CSK_Showcase_Half_Glass_{…} | 84 | 500 | PASS | 0 | 3 |
| a_cases_half_door_* | SM_CSK_Showcase_Half_Door_{…} | 92 | 150 | PASS | 1 | 1 |
| a_cases_half_baydoor_* | SM_CSK_Showcase_Half_BayDoor_{…} (new) | 140 | 150 (new) | PASS | 1 | 1 |
| a_cases_tower | SM_CSK_Showcase_Tower | 1120 / 312 / 108 | 1500 | PASS | 19 | 2 |
| a_cases_tower_glass | SM_CSK_Showcase_Tower_Glass | 128 | 400 | PASS | 0 | 8 |
| a_cases_tower_door | SM_CSK_Showcase_Tower_Door | 92 | 150 | PASS | 1 | 1 |
| a_cases_wall | SM_CSK_Showcase_Wall_1016 | 3468 / 444 / 116 | **3500** (spec 2500) | PASS | 27 | 2 |
| a_cases_wall_glass | SM_CSK_Showcase_Wall_Glass_1016 | 96 | 500 | PASS | 0 | 8 |
| a_cases_wall_door | SM_CSK_Showcase_Wall_Door_1016 | 36 | 150 | PASS | 1 | 1 |
| a_cases_counter | SM_CSK_Case_Counter_900 | 528 / 144 / 96 | 1200 | PASS | 10 | 1 |
| a_cases_counter_glass | SM_CSK_Case_Counter_Glass_900 | 48 | 200 | PASS | 0 | 4 |
| a_cases_counter_lid | SM_CSK_Case_Counter_Lid_900 | 136 | 150 | PASS | 1 | 1 |
| a_cases_wallslab | SM_CSK_Case_WallSlab | 788 / 244 / 140 | 1500 | PASS | 46 | 5 |
| a_cases_wallslab_door | SM_CSK_Case_WallSlab_Door | 52 | 200 | PASS | 1 | 1 |

**Sockets:**
- **A2:** `Level_{Deck,S1}`, `Compartment_`/`PriceTag_<Lvl>_01..04`, `Door_L/R`, `LED`, `Snap_L/R`, `Bay_01..02`, and `BayDoor_L/R` (new).
- **A3:** `Level_L1..L5`, `Compartment_<Lvl>_01..02`, `Door`, `Lock`, `LED`.
- **A4:** `Level_L1..L5`, `Compartment_<Lvl>_01..03`, `Door_L/R`, `Lock`, `LED`, `Snap_L/R`.
- **A5:** `Level_Deck`, `Compartment_`/`PriceTag_Deck_01..03`, `Lid`, `Lock`.
- **A6:** `Slot_R1..R4_01..10` (rotated 80° about X, so the slab leans 10°), `Door`, `Lock`, `LED`, `Snap_L/R`.

Every mesh also has `Seat`.

**Moving parts** (in `data["parts"]`):
- A2 doors: slide, as A1.
- A2 bay doors: slide, travel L/2 − 46.
- A4 doors: slide, 458.
- A3 door: hinge on Z, 0-100°.
- A5 lid: hinge on X, 0-80°.
- A6 front: hinge on X, 0-90°.

The right-hand sliding doors of A2 are turned 180°, so their locks and pulls meet at the centre, as in A1.

**Naming:** the part goes before the size (`_Door_1778`, `_Lid_900`), following A1. As a result the build's name-based
winding check does not match these meshes; the extra check covers them instead.

## Deviations from the spec (and why)

- **A2, 1 glass shelf:** sheet 16 shows one shelf plus the deck; the spec's 2 was E. The shelf splits the glass zone in
  half (227 clear each) and is 254 deep (E*).
- **A2, storage bay:** 184 clear, as in the spec (sheet 16 reads about 250; the log says keep 184). The sheet's oak internal
  shelf splits it into two 82.5-clear levels (`Bay_01` floor, `Bay_02` shelf).
- **A2, bay doors as a new mesh:** sheet 16 shows two sliding oak panels with recessed pulls. They have to move to reach
  the bay, so they ship as `SM_CSK_Showcase_Half_BayDoor_{L}`. That is +2 meshes over the spec's 6.
- **A2 carcass slot = `M_CSK_Oak`, and the deck is `M_CSK_Deck`:** sheet 16 shows light oak and a white deck. This is the
  same material instance as A1's cabinet.
- **A2 body has 6 hulls (spec 3):** one per panel (below the bay, deck board, bay front, the two end panels, top), so items
  can sit inside and the level tests hold.
- **A3 extras:** the light pole (sheet 17) is part of the body. A glass top pane is added, since the tower is frameless and
  sheet 17's corner clips hold it. The glass mesh has 8 panes and hulls (spec 7). The lock cylinder stands 12 proud of
  the 457 footprint.
- **A4 budget 2500 → 3500:** the two full-height slotted standards carry 128 real slot pockets (sheet 7 hardware at 25 pitch), about 2,560 tris.
  - LOD1 (444, 13%) and LOD2 (116, 3%) are below the guide's ratios, because 74% of LOD0 is sub-pixel slot detail. A1 is
    the same (11% and 2%).
  - The glass mesh has 8 panes and hulls (spec 6): glass on both sides, the back and the top.
- **A4 shelf supports:** sheet 17 shows standards only in the back corners, so the shelves' front corners rest on the
  tower's metal glass clips (a shelf needs 4 supports). _Check against the sheet._
- **A4 posts stand on the 203 base (plinth).** A1's posts run down to the kick, but sheet 17 describes a separate base. _Check against the sheet._
- **A5 base proportions (E):** kick 20, oak band 50, deck at 70; posts 20 and rails 15. The case is built to the spec size.
- **A5 stays and hinge:**
  - The stays are **quadrant stays**: arcs round the hinge axis that slide through guides on the body, so they are right at every angle.
  - The hinge is a continuous barrel whose axis sits 1 behind and 1 above the rear top edge; it stands 4 proud at the back.
- **A6 materials:** the back is oak (sheet 18; the spec said felt). The ledges are `M_CSK_Acrylic`.
- **A6 opening:** 0-90° (sheet 18 "to horizontal"; the spec's 0-85 was E).
- **A6 pivot:** the centre of the back face (the face it rests on). It is wall-mounted.
- **A6 rows:** pitch 162.5, spread over the 650 interior (the spec's 144 is the minimum).
- **A6 sockets:** 46 in total: the spec row's 40 fixed slots, plus 5 more, plus `Seat`. The ≤ 40 rule is for grid
  fixtures; the kit check does not test A6.

## New material slot names

- `M_CSK_Metal`: chrome hardware (the tower's patch hinges, clips and lock).
- `M_CSK_Felt`: the A5 deck, dark felt.
- `M_CSK_Acrylic`: the A6 ledges.

Reused: `Frame`, `Base`, `LED`, `Oak`, `Deck`, `Glass`.

## Not built

- **A6 door stays** (sheet 18): the hinge axis is only 6 mm under the frame's top member, so a quadrant arc covering 90°
  plus its guide would pass through the frame. A folding stay or gas strut needs its own linked parts.
- **A5, A6 lock bodies:** no lock appears in the notes. The spec's `Lock` sockets are placed (A5 at the front rim centre,
  A6 at the bottom front centre).
- **Sheet 18's short countertop case:** not in the spec.

## Open questions for the user

1. A6 stays: add a separate stay part, or leave the front on its hinge only?
2. A5 and A6 locks: model a cylinder lock at the `Lock` sockets, or leave the sockets for buyers?
3. A4: are there front standards or clips in sheet 17? Do the posts run down to the black band, as on A1, or stand on the base?
4. A2: keep the 184 bay (spec), or build the picture's ~250 (the glass zone would shrink or the deck would rise)?
5. A3: which back corner holds the light pole (built back-right)?
6. Keep `SM_CSK_Showcase_Half_BayDoor_{L}` as its own mesh (+2 meshes)?

## Renders (`WorkFiles/cardshop/families/a_cases/`)

| Item | Files |
|---|---|
| A2 | `a_cases_half1778_34`, `a_cases_half1778_34back`, `a_cases_half1219_back` |
| A3 | `a_cases_tower_34_open` (door at 60°), `a_cases_tower_front`, `a_cases_tower_body_34` (glass hidden) |
| A4 | `a_cases_wall_34`, `a_cases_wall_front`, `a_cases_wall_body_34` (glass and doors hidden) |
| A5 | `a_cases_counter_34`, `a_cases_counter_34_open45`, `a_cases_counter_right_open80` |
| A6 | `a_cases_wallslab_34`, `a_cases_wallslab_filled_34` (40 slabs from the slot sockets), `a_cases_wallslab_right_open` |

All files are PNG.
