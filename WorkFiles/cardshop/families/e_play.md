# Family e_play: binder system, deck box, playmat, dice (built 2026-09-29, cloud)

Module: `Scripts/cardshop/csk_lib/fam_e_play.py`, 11 item keys prefixed `e_play_`. The spec rows are CARDSHOP_KIT_SPEC.md
3.E E3, E4, E5 and E6. The references are sheet 14 (`csk_binder.png`) and sheet 15 (`csk_deckbox_playmat_dice.png`).
I opened both sheets on disk, measured them with zoomed crops (Pillow) and read their notes in REFERENCE_LOG.md.

**Build:** one build of all 11 keys ends `CSK_BUILD PASSED`. The house `qa_check` passes on every LOD, and the kit
checks pass 12/12 (11 hashes and the deny scan).

**Verification build:** the 11 keys plus the G1 `card` pass 32/32. That run adds 19 contain fits: the deck box `Cards`
socket, and the 18 page pockets (`Pocket_F01..09`, `Pocket_B01..09`).

## Meshes

| Key | Mesh | LOD tris | Budget | qa | Sockets | Hulls |
|---|---|---|---|---|---|---|
| e_play_binder_body | SM_CSK_Binder_Body | 1694 / 692 / 204 | **1800** (spec 1500) | PASS | 22 (Seat, Cover, Ring_01..20) | 3 |
| e_play_binder_cover | SM_CSK_Binder_Cover | 188 / 60 / 20 | 300 | PASS | 1 (Seat = hinge) | 1 |
| e_play_binder_page | SM_CSK_Binder_Page | 360 / 132 / 48 | 400 | PASS | 19 (Seat = pivot, Pocket_F01..09, Pocket_B01..09) | 1 (2 mm) |
| e_play_binder_closed | SM_CSK_Binder_Closed | 448 / 160 / 64 | 800 | PASS | 3 (Seat, Stack, Face) | 1 |
| e_play_deckbox | SM_CSK_DeckBox | 380 / 104 / 48 | 600 | PASS | 5 (Seat, Cards, Lid, Grip, Stack) | 1 |
| e_play_deckbox_lid | SM_CSK_DeckBox_Lid | 288 / 128 / 60 | 300 | PASS (winding 0) | 1 (Seat = hinge) | 1 |
| e_play_playmat_flat | SM_CSK_Playmat_Flat | 188 / 68 / 28 | 200 | PASS | 4 (Seat, Zone_Play, Zone_Deck, Zone_Discard) | 1 (2 mm) |
| e_play_playmat_rolled | SM_CSK_Playmat_Rolled | 1124 / 380 / 96 | **1200** (spec 600) | PASS | 2 (Seat, Grip) | 1 |
| e_play_die_d6 | SM_CSK_Die_D6 | 762 / 360 / 108 | **800** (spec 300) | PASS | 2 (Seat, Grip) | 1 |
| e_play_die_d20 | SM_CSK_Die_D20 | 116 (LOD0 only) | 500 | PASS | 2 (Seat, Grip) | 1 |
| e_play_token_22 | SM_CSK_Token_22 | 188 / 92 / 28 | **200** (spec 100, LOD0 only) | PASS | 2 (Seat, Grip) | 1 |

**Parts** (in `.csk.json`):
- **Deck box lid:** a `hinge` on X at the base's rear top edge (0, 40, 66.5), range 0-110. The open pose is -110°:
  negative angles open it.
- **Binder cover:** a `hinge` on Y at the fold between the spine and the front cover (inner face level). It is
  modelled lying open flat (0°); positive angles lift it, and past about 150° it meets the ring tops.
- **Binder page:** a `path` part. Attach the page at `Ring_01` (at rest on the right). A turn moves its pivot (the
  middle hole) along `Ring_01..20` over the ring arc, turning it from -2.45° to 182.45° about Y. `Ring_20` is the page
  at rest on the left.

**Class:** `Binder` (`CLASSES`), footprint 250 × 57 × 295 standing, pitch 260 × 59 (spec 4.2: spine + 2 along Y). The
deck box is class `Deck`; the Closed binder is class `Binder`.

## Construction

- **Dice (sheet 15 (3)):**
  - The d6 is 16 (M) on a welded rounded-cube grid: R 2 edges in 22.5° steps.
  - Its 21 pips are real 10-sided cone dimples: Ø 3.0, 0.95 deep, 4.1 off centre.
  - The pip faces are UV0 tile (0, 0), one cell per face, so the ink mask in `M_CSK_Resin` is `UV0.u >= 0`.
  - The d20 is an icosahedron 22 face to face, resting on a face. Its edges and vertices are chamfered 0.55 (crisp).
  - The token is Ø 22 × 2, 24 sides, with 0.3 chamfers on both rims.
- **Playmat (sheet 15 (2)):**
  - Flat: 609.6 × 355.6 × 2 (M), corners R 10 (sheet). The stitched binding (slot `M_CSK_Stitch`) covers the side,
    rounds 0.5 over the top edge and forms a 2-wide band on top. The cloth print fills tile (0, 0) inside the band.
    The base is rubber.
  - Rolled: the 609.6 mat is wound cloth side out, as an Archimedean spiral at the M 2.0 pitch from a Ø 20 core.
    That gives 5.8 turns and an outer Ø of 43.0-47.0 (mean 45 = spec D). The layers are 1.9 thick with 0.1 gaps.
    Each turn has 16 facets at the same angles, so the wraps never cross.
  - The roll ends are black rubber with a 0.3 cloth chamfer on each wrap's edge, which gives sheet 15's red spiral
    lines. The flat mat's print wraps onto the roll: u = the length along the mat, v = the roll axis. The free end
    lies at the back, below the axis.
- **Deck box (sheet 15 (1)):**
  - Outside 76 × 80 × 108 (E = sheet call-outs), inside 68 × 71 × 100 (M), with vertical edges at R 3.
  - The lid is the top 41.5 (38 %). Its front edge dips in a wave 38 wide, 23.7 across the flat and 9.4 deep, which
    fills the base's matching finger scoop. The scoop is an exact cut, bevelled 0.5 after the cuts, so the seam and
    the dip read as a groove.
  - A chrome hinge pin (Ø 3 × 35) sits on the rear top edge.
  - The lid is built from convex parts: the side walls carry the rounded corners, and the front and back walls sit
    flush between them. The top plate has a 0.8 chamfer, and there is the tongue. So the `_Lid` winding check passes
    with no visible seams.
- **Binder (sheet 14):**
  - Navy padded boards, 247.7 × 292.1 (M). The padded edges are hand-built rounds (3 facets, 22.5° apart), and each
    face carries its own slot. A Lod bevel would give every new face slot 0, which made the black edges navy.
  - The black spine band reaches 38 from the spine face (sheet 14): 34 on each cover. The inside is black, with navy
    piping round the edges.
  - The ring mechanism: a chrome dome rail 22 × 7, lever-booster ends with a round stud, a knuckle clip under each
    ring, and three O-rings (Ø 40, wire 3.5, 13 × 16 facets) at the M 108 pitch.
  - The 9-pocket page is a welded core film with 3 punched Ø 7 holes. It has 18 raised pocket pads (M 65.1 × 90.5),
    with the gaps between them as the welded seams.
  - The Closed mesh stands with the front toward -Y and the spine at -X. The spine is a padded board turned upright,
    and there is an opaque page block inside.

## Deviations from the spec / sheet notes (and why)

1. **Spine 57, not 51:** sheet 14's spine view measures the black spine at 56.4 (the picture wins over the E value).
   It also fits the picture's Ø 40 rings on a 7-high rail inside the closed covers (ring top at 48.3, cover inside at
   53). `Retail_BinderWrapped` (family c_retail) is 55 deep, so its binder is now thinner than E3; see question 2.
2. **O-rings, not D-rings:** sheet 14 and its notes show round O-rings.
3. **The binder Body and Cover are modelled open flat**, not in the closed pose. Pages can only turn over O-rings when
   the spine lies flat. With the spine standing, a turned page runs into it, because the rings are 1 mm from its
   inner face. The closed binder is the separate Closed mesh (a state swap). The cover's range is 0-150, not 0-180:
   past about 150° it meets the ring tops.
4. **The page rest pose is tilted 2.45°.** A threaded page must sit on the ring's crossing point, so its hole strip
   rests on the ring clips (13.3 up) and its fore edge on the back cover. Sheet 14 draws the pages flat on the cover
   beside the rail, with the holes off the rings, which cannot be threaded. `Ring_01..20` are the pivot stations on
   the arc (the spec's E).
5. **M page 293.7 vs M cover 292.1:** the open binder's page overhangs the covers by 0.8 at the top and at the bottom.
   The Closed mesh's page block stops 1 inside the covers so the standing binder rests on its covers. Both numbers
   are M [D17]; see question 1.
6. **The spine label cell lives in `M_CSK_BinderSpine`**, the black PU of the spine, the band and the inside. The
   spec put it in `M_CSK_BinderCover`, but the picture's spine is black, not navy, so it needs its own slot. The label
   is the spine's outer face, UV0 tile (0, 1).
7. **The binder's spec slot "Metal" is the existing `M_CSK_Chrome`.**
8. **Budgets raised:**
   - Body 1500 → 1800: the three round-wire O-rings need 13 sides to shade round under the kit's 30° sharp rule,
     about 1250 tris.
   - Rolled mat 600 → 1200: sheet 15's spiral end is a real wound strip, with the red wrap chamfers.
   - d6 300 → 800: 21 real pip dimples plus round edges.
   - Token 100 (LOD0 only) → 200 with 3 LODs: an 18-sided disc read polygonal in the hand; 24 sides with both rims
     chamfered is 188.
9. **d6 faces:** sheet 15 shows 2 on top and a 4 on both visible sides, which no die can have. I built top 2, front
   4 and right 6 (6 keeps the picture's four corner pips). It is a western die: opposites sum to 7, and 1-2-3 run
   counter-clockwise.
10. **d20 "22" is face to face:** it rests on a face, and the picture's silhouette (about 26-27 across) matches 22
    face to face, not 22 vertex to vertex.
11. **Rolled mat:** sheet 15 draws about 4 loose turns round a large core. The M mat (609.6 × 2) round a Ø 20 core at
    Ø 45 is 5.8 tight turns; the M and D numbers win. The rolled mesh uses `M_CSK_Playmat` and `M_CSK_Rubber` only,
    because the picture's roll ends are black rubber, not thread.
12. **Deck box:**
    - The emblem is UV only: the base's front face is tile (0, 0), and sheet 15 shows the box plain. It is a single
      `M_CSK_Plastic` slot, not a separate Print slot.
    - The hinge pin (visible in the open views) adds `M_CSK_Chrome`.
    - The far LOD drops the dip and the scoop.
13. **E values I chose:**
    - Playmat zones: play at (-45, 0), deck at (+249.3, +55), discard at (+249.3, -55), on the top face.
    - Deck box card pitch 0.66: 100 sleeved cards in 66 of the 71.
    - Page seams 2.5, top and bottom margins 8.6: the M page less the M pockets, spread out.
    - Rail length 266.

## New material slot names

`M_CSK_BinderCover` (named in the spec), `M_CSK_BinderSpine`, `M_CSK_BinderPages` (opaque page block, Closed only),
`M_CSK_Playmat` (Playmats atlas cell), `M_CSK_Stitch`, `M_CSK_Resin` (named in the spec; tint plus the pip-ink rule
`UV0.u >= 0`).

Reused: `M_CSK_Chrome`, `M_CSK_Film`, `M_CSK_Plastic`, `M_CSK_Rubber`.

## Not built

Nothing. All 11 meshes of rows E3-E6 are built.

## Open questions for the user

1. **The M page (293.7) is 1.6 taller than the M cover (292.1)**, both [D17]. Should the cover grow to about 296, or
   the page be trimmed? Today the page overhangs the open binder by 0.8 top and bottom.
2. **Spine 57 from the picture, or the spec's 51?** Should `Retail_BinderWrapped` follow (about 61 deep with its
   film)?
3. **Is the open-flat binder** (Body + Cover lying flat, Closed as the state swap, cover range 0-150) right for the
   game? Or do you want a standing binder whose cover opens (sheet 14's lower-left view), which could not turn pages?
4. **Is the tilted page rest (2.45°) acceptable?** The alternative is a page lying level, 10 up on the ring clips,
   with a visible gap over the cover.
5. **Are the budget raises OK?** Body 1800, Rolled 1200, d6 800, and the Token at 200 with LODs.
6. **Is the pip ink by UV rule OK for the materials pass?** Pip faces are in UV0 tile (0, 0) and everything else is
   in the U -1 tile.

## Renders (`WorkFiles/cardshop/families/e_play/`)

These are shape checks. The look-dev colours come from a scratch wrapper round `csk_shot.py`, whose palette only
guesses from the slot names. `cmp_*` = the sheet crop (left) beside the render (right).

- **Binder:** `binder_closed_front.png`, `binder_closed_34.png`, `binder_closed_spine.png`, `binder_open_top.png`,
  `binder_open_34.png`, `binder_rings_close.png`, `binder_cover_90.png`, `binder_page_turn.png`;
  `cmp_binder_front.png`, `cmp_binder_open.png`, `cmp_binder_rings.png`, `cmp_binder_cover.png`.
- **Deck box:** `deckbox_closed_34.png`, `deckbox_open_34.png`, `deckbox_open_cards_34.png`;
  `cmp_deckbox_closed.png`, `cmp_deckbox_open.png`.
- **Playmat:** `playmat_flat_34.png`, `playmat_flat_top.png`, `playmat_rolled_34.png`, `playmat_rolled_end.png`;
  `cmp_playmat_flat.png`, `cmp_playmat_rolled_end.png`.
- **Dice:** `dice_34.png`, `die_D6_34.png`, `die_D20_34.png`, `token_34.png`; `cmp_d6.png`, `cmp_d20.png`,
  `cmp_token.png`.
