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
