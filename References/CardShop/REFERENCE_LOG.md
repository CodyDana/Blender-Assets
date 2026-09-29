# Card Shop Kit: reference log

Every reference image used to model the kit (CLAUDE.md: match by looking, confirm by measuring). The prompts are in
`WorkFiles/cardshop/CARDSHOP_REFERENCE_PROMPTS.md`. All images below are **AI-generated modelling references**. The
meshes are built new from the spec's numbers and no image goes into the product, so they don't make the product
"Created with AI" (FAB_ASSET_STUDY 4.3). They are logged here for the per-product AI decision log (spec 6.1 rule 7).

| # | File | Sheet | Date | Source | SHA-256 (first 16) | IP check | Notes |
|---|---|---|---|---|---|---|---|
| 0 | `csk_style_anchor.png` | 0 style anchor | 2026-09-29 | AI image chat (user), 1536 x 1024, given as webp and saved as PNG | c9810491d24bb72c | Pass | See "Sheet 0 notes" |
| 1 | `csk_card.png` | 1 card + stacks | 2026-09-29 | AI image chat (user), 1536 x 1024, given as webp and saved as PNG | fd3ce06451d6a464 | Pass | See "Sheet 1 notes" |
| 2 | `csk_toploader.png` | 2 top-loaders | 2026-09-29 | AI image chat (user), 1536 x 1024, given as webp and saved as PNG | a06be7ffcbf66cd6 | Pass | See "Sheet 2 notes" |
| 3 | `csk_slab.png` | 3 graded slab | 2026-09-29 | AI image chat (user), 1536 x 1024, webp -> PNG | 8af5a603b8dd818b | Pass | See "Sheet 3 notes" |
| 4 | `csk_pack.png` | 4 booster pack | 2026-09-29 | AI image chat (user), 1536 x 1024, webp -> PNG | 5902d6b4b32334f7 | Pass (dimension call-outs only) | See "Sheet 4 notes" |
| 5 | `csk_booster_box.png` | 5 booster display box | 2026-09-29 | AI image chat (user), 1536 x 1024, webp -> PNG | d4cd57f6deecfe62 | Pass (dimension call-outs only) | See "Sheet 5 notes" |
| 6 | `csk_showcase_full.png` | 6 full-vision counter | 2026-09-29 | AI image chat (user), 1536 x 1024, webp -> PNG | aa4408cb387276b5 | Pass | See "Sheet 6 notes" |
| 7 | `csk_showcase_detail.png` | 7 counter details | 2026-09-29 | AI image chat (user), 1536 x 1024, webp -> PNG | d321077786d405c9 | Pass | See "Sheet 7 notes" |

## Sheet 0 notes (style anchor)

**IP check (Claude, 2026-09-29):**
- no text, numbers, logos or brand marks anywhere;
- the posters, packs, boxes and sleeve packs are plain colour blocks;
- the slab labels are plain white bands with no red border and no hologram;
- no franchise shapes;
- the devices on the counter (screen, receipt printer) are generic.

**What the anchor sets for the whole kit** (later sheets attach it, so they inherit this look):
- **Palette:** light oak veneer, white laminate and white solid-surface tops, brushed aluminium frames, clear glass,
  grey polished vinyl/concrete floor, white acoustic ceiling with flat LED panels and black track spots, black
  folding chairs, white tournament tables.
- **Display counters:** the central run is light-oak lower cabinets with a recessed black toe kick, white edge trim,
  and aluminium-framed glass above with two lit glass shelves. The spec's full-vision counter (A1) has a black kick
  base. It follows the anchor instead: **oak cabinet base + black toe kick**. The half-vision counter (A2) already
  matches this layout. Sheet 6 will settle the exact proportions.
- **Towers:** full-glass towers on light-oak bases near the window (A3), as specified.
- **Cash counter:** light-oak front, thick white top with a rounded edge, generic screen and receipt printer, a clear
  acrylic tiered riser with slabs (A16), as specified.
- **Wall:** white slatwall with hanging clear sleeve and blister packs (A7, A8, B8), as specified.

**Seen in the anchor but not in the spec** (candidates, for the user to decide):
1. **Wall cubby shelving unit:** an open light-oak shelving bay (about 1.2 m wide, 4 shelves) above white base
   cabinets with doors, holding deck boxes and small display boxes. A strong, cheap hard-surface piece that fits the
   kit. Proposed as `SM_CSK_WallUnit_Oak` in v1.
2. **Potted plants:** decor. Organic modelling is our weak spot, so they're proposed as out of scope (buyers have
   plant packs).
3. **Small display boxes on the shelves** (many sizes, colour blocks): already covered by B2/B3/B8 variants.

## Sheet 1 notes (card)

**IP:** blank faces (blue border, plain window, navy back); no text or symbols.

**Geometry:** matches the built card (63 x 88 x 0.3 mm, rounded corners, flat). The picture's corners read nearer 2.5 mm
than 3 mm. 3 mm stays (real cards are about 3.2 mm; the picture is not measured). The stacks show layered edge lines:
the planned edge-stripe texture for C2.

**Art (P2):** the frame layout (a border about 5 mm wide round a plain window, a dark back) guides the card frame
design Claude draws around the user's illustrations.

The grey scale card on the left is out of proportion (AI drift); ignored.

## Sheet 2 notes (top-loaders)

**IP:** generic clear PVC holders; no marks.

**Changes to the build (to match the picture):**
- **Rounded outer corners**, about 3.5 mm radius (the G1 build has square corners).
- **Thumb notch:** a semicircle about 14 mm wide and 7 mm deep, cut into the FRONT skin and the top edge at the centre
  of the open end. The spec guessed 20 mm; the picture wins where the spec was an estimate.
- **Softened edges:** a small round-over all round.
- **Wall widths:** about 3.5 mm at the sides, matching the spec's 3.6 mm.
- **Thicknesses:** a standard one and a thick one (side views), so `TopLoader_130pt` (4.8 mm) is built as well.

## Sheet 3 notes (graded slab)

**IP:** a plain white label band; no red border, stripe, hologram or grade. The design is ours: chamfered corners and a
stepped frame. The blind brand test (spec 6.3) still runs on the built shell.

**Changes to the build (to match the picture):**
- **Frame:** a stepped perimeter frame. An outer rim with 45-degree chamfered corners, then an inset step about 1 mm
  lower, on the front and the back. The spec called for a single flat frame.
- **Label band:** its own raised, framed recess at the top, separated from the window by a cross bar. The label insert
  sits inside it, flush with the step.
- **Card gasket:** a white gasket with rounded corners runs round the card well (a thin opaque ring).
- **Stacking lugs:** small rounded-rectangle lugs on both long side edges near the top, with matching recesses, so
  stacked slabs nest. These replace the spec's back ridges (same purpose, and the picture wins).
- The side views show the standard and thick slabs (7 and 8 mm). The stack of three shows the nesting.
- **Detail:** this is enough real geometry to reach the spec's 1200-tri LOD0, so the slab gets proper LODs again.

## Sheet 4 notes (booster pack)

**IP:** a plain blue foil pack. The dimension call-outs (67 / 117 / 4 mm) are sheet annotations, not product art. It
matches the spec's numbers.

**Changes to the build (to match the picture):**
- **Crimp bands** (about 9 mm) carry fine **vertical ribs**, with a **serrated edge of about 20 teeth** across the
  width (the G1 build has 10 coarse teeth).
- **Fin seal:** a ribbed vertical fin seal about 6 mm wide down the back centre, slightly raised.
- **Side profile:** lens-shaped, tapering to the crimps.
- **Opened state:** the top crimp is torn off along a jagged line, showing silver foil inside, and the pack gapes.
- **Tear strip:** on its own it is a ribbed strip with teeth on both edges.
- **Wrapper:** flattened and crumpled, with silver showing at the torn end.

## Sheet 5 notes (booster display box)

**IP:** plain two-tone colour blocks. The call-outs are annotations only.

**Changes to the build (to match the picture):**
- **Opened state:**
  - the **front panel has a die-cut window**: a trapezoid cut down to about half height, with angled sides, so the
    packs show from the front;
  - the **lid is a tall header panel hinged at the back top edge that stands upright**, with a centred tab on its top
    edge (a display header, not a flap folded 200 degrees flat);
  - a **centre divider** separates the two pack columns.
- **Sealed state:** closed, in shrink film (a thin film shell with soft corners).
- **Dieline:** a tuck-end carton with dust flaps and glue tabs. The print layout follows it: front, right, back and
  left in one band, with the header over the back.
- The large box (190 x 76 x 140, 24 packs) is the same design.

## Sheet 6 notes (full-vision counter)

**IP:** generic aluminium, glass and oak.

**Changes to the build (to match the picture):**
- **Base:** a **light-oak cabinet about 190 mm tall with a recessed black toe kick about 60 mm tall**, inset about
  10 mm. It replaces the black kick base, and matches the style anchor.
- **Deck:** a pale oak/cream deck board.
- **Shelf standards:** **slotted aluminium standards** run up the inside of the end posts; the glass shelves rest on pins.
- **Doors:** two rear sliding doors with a **cylinder lock at the centre** where they overlap.
- **LED strip:** in an aluminium channel under the top front rail.
- The small tower on the right of the sheet is A3's look (sheet 17).

## Sheet 7 notes (counter details)

**IP:** generic hardware.

**Details for the build:**
1. **Top corner:** square aluminium posts, with the rails meeting them in a simple butt joint. The top glass sits on
   the frame with its edge exposed (a green glass edge).
2. **Bottom corner:** the post stands on the oak base. The oak has a clean square edge and the black toe kick is
   recessed.
3. **Rear tracks:** an aluminium U-channel top and bottom, the two doors in separate channels, and small guide shoes at
   the bottom of each door.
4. **Lock:** a chrome cylinder lock body clamped on the edge of the inner door.
5. **Shelf support:** a slotted standard with a round steel pin and a clear shelf clip.
6. **LED:** an LED strip in an aluminium channel with a diffuser.
