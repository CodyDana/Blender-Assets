# Family de_storage: thick slab, grading-return box, row boxes, monster boxes (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_de_storage.py`, 13 item keys prefixed `de_storage_`. The spec rows are
CARDSHOP_KIT_SPEC.md 3.D D2 and D4, and 3.E E1 and E2. The references are sheet 3 (`csk_slab.png`), sheet 9
(`csk_grade_return.png`) and sheet 13 (`csk_storage_boxes.png`). I looked at all three on disk and measured them with
zoomed crops (Pillow).

**Build:** one build of all 13 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD, and the kit
checks pass 22/22: 8 contain fits (the D4 slots seated with the D2 thick slab), 13 hashes and the deny scan.

**Verification build:** the 13 keys plus the G1 `card` and `slab` pass 38/38. That run adds the contain fits of
`Cards_Start` (E1 ×3), `Row_01..05` (E2) and the D2 `Card` for the G1 card, and the D4 slots for the 7 mm slab.

**Extra check** (`scratchpad/fam_de_storage/wind.py`): every closed part of every builder, cutter and extra has
positive signed volume and no non-manifold edges. The one exception is the slab's card well, which is meant to
face inward. The socket rotations were checked with `fit.rot_xyz`.

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | Hulls |
|---|---|---|---|---|---|---|
| de_storage_slab_thick | SM_CSK_Slab_Thick | 684 / 108 / 60 | 1200 | PASS | 6 (Seat, Card, Label, Face, Grip, Stack) | 1 |
| de_storage_grade | SM_CSK_Box_GradeReturn | 304 / 168 / 40 | 500 | PASS | 10 (Seat, Slab_01..08, Lid) | 1 |
| de_storage_grade_lid | SM_CSK_Box_GradeReturn_Lid | 80 (LOD0 only) | 150 | PASS | 2 (Seat, Label) | 1 |
| de_storage_row_{100,400,800} | SM_CSK_Box_Row_{100,400,800} | 232 / 104 / 28 | 300 | PASS | 5 (Seat, Cards_Start, Lid, Label, Stack) | 5 |
| de_storage_row_lid_{100,400,800} | SM_CSK_Box_Row_Lid_{100,400,800} | 108 (LOD0 only) | 150 | PASS | 1 (Seat) | 1 |
| de_storage_monster_3200 | SM_CSK_Box_Monster_3200 | 368 / 176 / 64 | 600 | PASS | 7 (Seat, Row_01..04, Lid, Stack) | 5 |
| de_storage_monster_5000 | SM_CSK_Box_Monster_5000 | 380 / 188 / 76 | 600 | PASS | 8 (Seat, Row_01..05, Lid, Stack) | 5 |
| de_storage_monster_lid_{3200,5000} | SM_CSK_Box_Monster_Lid_{3200,5000} | 284 / 140 / 28 | **300** (spec 200) | PASS | 1 (Seat) | 1 |

**Parts** (in `.csk.json`):
- The D4 and E2 lids are `slide` parts on Z (lift-off), with the pivot at the closed position.
- The E1 lid is a `hinge` on X at the back top edge, range 0-180, open pose -100° (negative angles open it).

**Classes** (`CLASSES`), each footprint being the closed box's outside, pitch + 10:
- `StorageRow100`, `StorageRow400`, `StorageRow800`;
- `StorageMonster3200`, `StorageMonster5000`;
- `BoxGrade` (159 × 134 × 170).

The D2 slab is class `Slab`, with an 8.0 stack pitch.

## Construction

- **Board boxes:** one closed "tray" shell on a 4 × 4 vertex grid. The side walls' cut ends are their own kraft
  faces on the front and back, giving the butt-joint flute strips of sheets 9 and 13 with no T-junctions. The outside
  is white, and the inside and every cut edge are kraft. There is a 0.5 bevel before the cuts, so the hand holes and
  the finger cut are crisp exact booleans with kraft cut faces.
- **D2:** `geom._slab_lod` with an 8 mm dict. The D1 face design is kept, and the card well is 65 × 90 × 3.4 between
  2.3 skins. The side view matches sheet 3's 7 / 8 mm pair.
- **D4 base:**
  - 150 × 125 × 166, board 4.
  - A grey foam insert up to 20 under the rim, with 8 slots of 9 × 87 at 14 pitch running front to back and a slot
    floor at 30. The foam is joined after the bevel.
- **D4 lid:**
  - 159 × 134 × 60, telescoping.
  - Convex board slabs, so it passes the `_Lid` winding check.
  - A chamfered folded top, and the side skirts' ends kraft.
  - A blank label (85 × 55, 0.2 proud) on the label tile (0, 1).
- **E1 base:**
  - M outer and inner dimensions.
  - The side walls are 4.75, folded double: white inside with a white rim.
  - A 3 mm front wall with the finger cut, and a 16.0 back end.
- **E1 lid:**
  - A top panel with a folded front edge.
  - A 36-deep front flap with R4 corners over the front wall.
  - 1.5 side dust flaps that tuck inside when closed.
  - Kraft inside.
- **E2 base:**
  - The M outside is the lid's, so the base is M − 7 in plan and M − 3 high.
  - 3.0 fold-up dividers with round tops, 8 under the rim: 4 or 5 rows of 78.7-78.8 running front to back.
  - Stadium hand holes, 90 × 30, through both ends.
- **E2 lid:** a 57.5 telescoping skirt, with the hand holes level with the base's.

## Deviations from the spec / sheet notes (and why)

1. **D4, slabs stand on the SHORT edge** (84 along Y, 134 tall, face +X, rot (90, 0, 90)), not on the "long edge"
   of the sheet 9 notes. On the long edge, 134 cannot fit the 117 inner depth. Sheet 9's top-down and lid-off views
   show 8 slots running front to back across the 150 width.
2. **D4 lid 60 deep:** read off sheet 9 (0.35 H). The spec gives no lid depth.
3. **D4 base 150 × 125, lid 159 × 134:** the spec's inner size is 142 × 117 = outer − 8, which is the base, so the
   telescoping lid is larger. The class footprint uses the lid.
4. **E1 orientation:** the 104.8 end with the finger cut faces the customer and the length runs along +Y. The spec
   column lists the length first. The sheet shows this front, and the back-edge hinge only works this way.
5. **E1 end walls:** the M outer and inner lengths need 22.2 of end structure. The sheet draws thin walls. I built a
   3 front wall + a 3.2 flap and gap (as the sheet shows) + a 16.0 folded back end, which is hidden in every view.
   The side walls are 4.75 (M), which the sheet shows as folded double white walls.
6. **E1 finger cut is a U** (26 wide, round bottom 11 below the flap edge). Sheet 13's closed views show a half-moon
   under a 36-deep outside flap, but its open views show an 11-deep half-moon at the rim; one design cannot do both.
   The U matches the closed look exactly, and in the open state it opens from the rim, but it is deeper (47) than the
   open views show. See question 1.
7. **E1 dust flaps are 1.5 thick**, not board 3. Closed, they tuck inside the side walls, and the M inner 95.3 must
   still take a sleeved card (92.1).
8. **E2 lid depth 57.5:** both closed views read 0.55 H. The spec's E was 40, and the picture wins.
9. **E2 hand holes 90 × 30** (spec E) are kept. Sheet 13 reads 87-100 × 22-35 between its two sizes.
10. **E2 has 5 hulls, not 6** (the floor and 4 walls). The dividers get none: more would pass the 6-hull cap, and the
    contained cards are NoCollision.
11. **E2 monster lid budget 200 → 300.** It has two real hand-hole cuts and bevelled folds. Base + lid (668) stays
    inside the spec's combined 800.
12. **Labels:** sheet 13 shows no labels, so E1 has only the spec's `Label` socket (on the front wall under the finger
    cut) and no label geometry or slot. E2 has none. D4's label is on the lid mesh, so the `Label` socket is on the lid.
13. **E1/E2 interiors:** sheet 13's open views show white side walls inside the row box (folded double) and kraft
    inside the monster box. I followed the picture for the row box sides; everything else follows the lead's rule
    (kraft inside).
14. **D4 LOD1 is 55% of LOD0** (the foam's 8 slots are kept at 4 m), slightly over the ~50% guide.

## New material slot names

- `M_CSK_BoardWhite`: white corrugated board, outside.
- `M_CSK_Foam`: grey foam insert.

The families reuse `M_CSK_Board` (kraft: inside and cut edges), `M_CSK_Label`, `M_CSK_SlabBody` and
`M_CSK_SlabWindow`.

## Not built

- Sheet 9's single-slab foam panel: a different product (AI drift), per the sheet notes.
- The E2 hinged lid of sheet 13's open views: the user decided on the telescoping lid.

## Open questions for the user

1. **E1 finger cut:** keep the U (the closed shelf look is exact, and it opens deep), or use the open views' 11-deep
   half-moon at the rim (hidden under the flap when closed)?
2. **E1 ends:** keep the M inner length, which gives a 16 mm hidden back end? Or use thin walls everywhere, as the
   sheet draws, which gives a 13 mm longer card cavity than M?
3. **E2 footprint:** is the M outside the lid's (as built) or the base's?
4. **D4:** is the proposed `BoxGrade` placement class wanted? D4 is not in the spec's class table.

## Renders (`WorkFiles/cardshop/families/de_storage/`)

- **Comparisons:** `cmp_grade_34.png`, `cmp_grade_top_lidoff.png`, `cmp_row100.png`, `cmp_row800.png`,
  `cmp_monster3200.png`, `cmp_monster5000.png`, `cmp_slab_thick.png`.
- **Shots:** `grade_closed_34.png`, `grade_open_34.png`, `grade_top.png`, `grade_lidoff_34.png`,
  `row100_closed_34.png`, `row100_open_34.png`, `row100_front.png`, `row800_closed_34.png`, `mon3200_closed_34.png`,
  `mon3200_open_34.png`, `mon5000_open_34.png`, `slab_thick_34.png`, `slab_thick_stack_34.png`,
  `slab_thick_vs_std_side.png`.

The shots used a scratch copy of `csk_shot.py` whose palette reads `BoardWhite` / `Label` as white and `Foam` as dark
grey. The kit tool reads "board" as kraft.
