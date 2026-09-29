# Card Shop Kit: per-piece reference prompts (image generation)

**Date:** 2026-09-29. **Purpose:** a reference sheet for every piece in the kit (`CARDSHOP_KIT_SPEC.md` section 3), so
each one is modelled to match a picture by eye and confirmed by measurement (the CLAUDE.md bar: match by looking,
confirm by measuring, invent nothing the reference doesn't show). The G1 test pieces come first because they get
rebuilt first.

**How to use**

1. Start one image chat (ChatGPT or similar). Paste the **shared rules** block once. Then paste **sheet 0** and save
   the result: it is the style anchor. Attach it to every later sheet so the whole kit looks like one shop.
2. Paste one sheet prompt at a time. One image per prompt.
3. If a result adds anything from the "never" list (text, logos, a real brand's look, a red-framed slab label, a
   character on a pack), reply "remove the ..." and regenerate. If the proportions drift badly from the numbers, ask
   it to fix them. **The spec's dimensions always win over the picture**; the picture decides the look, the detail
   and how the parts are built.
4. Save each image as `References/CardShop/<file name>` (names below), or drop them in Downloads and tell me. I log
   them in `References/CardShop/REFERENCE_LOG.md` as AI-generated modelling references. The meshes are still built
   new from the numbers, so no AI output ships in the product.

**Printed surfaces are left blank on purpose.** Packs, boxes, labels, posters and card faces show plain colour
blocks only. Your card art and the kit's own brand art (Pyrecall, Lumenfold, Rimvault, Clearmark, Halcyon,
Sleevesmith, Longhaul, Corner Pocket Cards) go on later as textures.

---

## Shared rules (paste once, before sheet 0)

```
I am building a realistic video-game asset kit: an original trading-card and collectibles shop (the kind of small
hobby shop that sells card packs, graded cards, sleeves and binders, with glass display counters and play tables).
I will ask for reference sheets of individual pieces, one per message, so a 3D artist can model them. Every sheet
follows these rules unless I say otherwise:

- Format: a clean model sheet on a plain light-grey seamless background, soft even studio light. Show the piece in a
  front view, a side view and a top view (true orthographic, straight on, no perspective) plus one 3/4 perspective
  view, all at the same scale, side by side and clearly separated. Landscape 3:2.
- Scale: small handheld items: place a plain blank grey card (63 x 88 mm, rounded corners) beside the front view.
  Furniture: place a plain grey 1.8 m tall human silhouette beside the front and side views. Keep the proportions to
  the dimensions I give.
- Style: clean modern realism, like a well-kept real shop. Physically based materials: clear glass, clear acrylic,
  brushed aluminium, powder-coated steel, white laminate, light oak, kraft cardboard, matte plastics. Crisp
  edges with small real bevels. New and tidy, not grungy.
- Show construction clearly: how parts join, hinges, seams, folds, screws, rails, where lids open.
- Printed areas (packs, boxes, labels, signs, card faces) are PLAIN COLOUR BLOCKS: no pictures, no characters, no
  patterns that look like a real product.
- Never include: any text, letters or numbers; any logo, emblem, crest or brand; anything that resembles Pokemon,
  Magic: The Gathering, Yu-Gi-Oh, Lorcana, One Piece, sports-card brands, or any real card game (no poke-ball shapes,
  no red-and-white ball, no brown swirl card backs, no yellow-and-blue lettering); any real grading company's look
  (no white label with a red border, no hologram sticker, no grade numbers); real currency; real phone, terminal or
  printer brands and their recognisable shapes; people other than the grey scale silhouette.
Reply "ready" and wait for the first sheet.
```

---

## Sheet list

| # | File name | Pieces (spec ids) | G1 |
|---|---|---|---|
| 0 | `csk_style_anchor.png` | The whole shop, one wide view (style anchor) | |
| 1 | `csk_card.png` | C1 card, C2 card stacks | **yes** |
| 2 | `csk_toploader.png` | C5 top-loaders (35 pt, 130 pt) | **yes** |
| 3 | `csk_slab.png` | D1 slab, D2 thick slab, D3 filled slab | **yes** |
| 4 | `csk_pack.png` | B1 booster pack: sealed, opened, torn wrapper, tear strip | **yes** |
| 5 | `csk_booster_box.png` | B2 booster display box S and L, lid open and closed | **yes** |
| 6 | `csk_showcase_full.png` | A1 full-vision glass counter (with rear sliding doors) | **yes** |
| 7 | `csk_showcase_detail.png` | A1 close-ups: corner post, glass joints, door track, lock, LED strip | **yes** |
| 8 | `csk_sleeves_holders.png` | C3 penny sleeve, C4 deck sleeve, C6 semi-rigid, C7 magnetic holder | |
| 9 | `csk_grade_return.png` | D4 grading-return box with foam insert | |
| 10 | `csk_collector_box.png` | B3 collector box, B7 starter deck tuck box | |
| 11 | `csk_cartons.png` | B4 shipping carton of 6 boxes, B5 delivery boxes, flattened states | |
| 12 | `csk_blister_retail.png` | B6 blister pack, B8 retail accessories (8 items) | |
| 13 | `csk_storage_boxes.png` | E1 row boxes, E2 monster boxes | |
| 14 | `csk_binder.png` | E3 binder (open, closed), 9-pocket page | |
| 15 | `csk_deckbox_playmat_dice.png` | E4 deck box, E5 playmat flat and rolled, E6 dice and token | |
| 16 | `csk_showcase_half.png` | A2 half-vision showcase | |
| 17 | `csk_tower_wallcase.png` | A3 glass tower, A4 lit wall case | |
| 18 | `csk_counter_case_wallslab.png` | A5 countertop case, A6 wall slab case | |
| 19 | `csk_slatwall.png` | A7 slatwall panels, A8 hooks, A9 shelf | |
| 20 | `csk_gondola.png` | A10 gondola sections, A11 shelves and corner | |
| 21 | `csk_wire_rack_box_shelf.png` | A12 wire rack, A13 tiered box shelf | |
| 22 | `csk_card_table.png` | A14 glass-top card tables (8, 10, 12 slots) | |
| 23 | `csk_easels_risers.png` | A15 easels, A16 risers and card stands | |
| 24 | `csk_play_area.png` | F1 tournament tables, F2 folding chair | |
| 25 | `csk_counter_pos.png` | G1 cash counter with G2-G7 on it, G8 money | |
| 26 | `csk_pos_devices.png` | G2-G7, G9, G10 close-ups (drawer, terminal, printer, screen, scanner, price gun, phone, laptop) | |
| 27 | `csk_bag_mailers.png` | G11 paper bag, H3 mailers, H4 tape gun | |
| 28 | `csk_backroom.png` | H1 warehouse rack, H2 workbench, H7 hand truck | |
| 29 | `csk_bins.png` | H5 bin, H6 full trash bag | |
| 30 | `csk_signs_tags.png` | I1 open/closed sign, I2 price tags, I5 hanging sign | |
| 31 | `csk_posters_storefront.png` | I3 poster frames, I4 storefront lightbox | |
| 32 | `csk_shell.png` | J1 walls, window wall, door wall, floor, ceiling | |
| 33 | `csk_entry_door.png` | J2 glass entry door and frame | |
| 34 | `csk_lights.png` | J3 panel light, track and heads, pendant | |
| 35 | `csk_scale_figure.png` | J4 neutral scale figure | |
| 36 | `csk_wall_unit.png` | Oak wall shelving unit seen in the style anchor (proposed addition) | |

---

## 0. Style anchor (`csk_style_anchor.png`)

```
Sheet 0 (an exception to the model-sheet format): one wide, eye-level interior photo of the whole shop, about 8 m x
10 m, bright and clean, daylight from a glass shop front plus warm ceiling panel lights. Along one side, a row of
full-vision glass display counters (aluminium frame, glass on all sides, glass shelves) holding graded cards in clear
slabs, cards in rigid holders and small foil booster packs. A cash counter with a card terminal and a receipt
printer. Behind it, a wall of white slatwall with hooks holding sleeve boxes and blister packs, and a tiered shelf
of small booster display boxes. In the back, a play area with white folding tournament tables, playmats and folding
chairs. Light oak and white laminate, brushed aluminium, grey vinyl floor. All packaging and signs are plain colour
blocks with no text or pictures. No people.
```

## 1. Card and card stacks (`csk_card.png`) — G1

```
Sheet 1: a blank trading card and card stacks. The card: 63 x 88 mm, 0.3 mm thick, 3 mm corner radius, flat, no
bend. Show the face with a plain coloured border and a plain rectangular art window (no picture), and the back as a
plain darker colour. Show the edge close up (thin white card core between the printed faces). Next to it, three
neat stacks of the same card: 10 mm, 30 mm and 90 mm tall, squared up, showing the layered edge lines.
```

## 2. Top-loaders (`csk_toploader.png`) — G1

```
Sheet 2: rigid clear PVC top-loader card holders. Outer 76.2 x 101.6 mm. The standard one is 2.0 mm thick; a thick
one for chunky cards is 4.8 mm thick. The card slides in from the top (short edge): the top edge is open, with a
shallow semicircular thumb notch about 20 mm wide cut into the front skin at the top centre. Walls about 3.6 mm wide
on the sides and bottom. Show one empty and one holding the blank card (the card sits at the bottom of the pocket,
a few mm of air above it). Show the top edge close up so the pocket opening and notch are clear, and the slight blue
tint and edge highlights of clear PVC.
```

## 3. Graded slabs (`csk_slab.png`) — G1

```
Sheet 3: an original graded-card slab (a sealed clear acrylic case for one card). Outer 84 x 134 mm, 7 mm thick; a
thick version is 8 mm. Our own design, not any real grading company's: the outline is a rectangle with 4 mm 45-degree
CHAMFERED corners (not rounded). A 3.5 mm solid clear frame runs all round. At the top, a 24 mm tall label band
holds a plain white paper label insert with NO border colour, no stripe, no hologram and no printing. Below it, a
card well (65 x 90 mm, 1 mm deep) holds the card behind a clear window, framed by a thin white gasket. The back has
thin raised ridges along the edges so slabs stack and nest. A faint welded seam line runs round the side. Show:
empty slab, slab with the blank card inside, the side profile, a stack of three slabs, and a close-up of a corner
chamfer and the label band.
```

## 4. Booster pack (`csk_pack.png`) — G1

```
Sheet 4: a foil trading-card booster pack, 67 x 117 mm, about 4 mm thick at the middle: a soft sealed pillow shape.
Both short ends are flat crimped seals about 9 mm deep with a fine serrated (zigzag) cut edge. A vertical fin seal
runs down the middle of the back. Metallic foil with a plain single-colour print, no picture. Show four states: sealed
(front and back); opened (the top crimp torn off, the pack gaping slightly); the torn-off tear strip on its own
(67 x 12 mm); and the empty wrapper flattened and crumpled as trash.
```

## 5. Booster display box (`csk_booster_box.png`) — G1

```
Sheet 5: a printed cardboard booster display box, the kind shops put on the counter. Small size: 140 mm wide,
80 mm deep, 125 mm tall, board 2 mm; it holds 36 packs standing on edge in two rows. Large size: 190 x 76 x 140 mm,
24 packs. The top panel is a flap hinged at the rear top edge: it tears along perforations at the front and folds
back (up to 200 degrees) to stand up as a display header. Show: sealed (closed, in thin shrink film); open with the
lid folded back and the packs standing inside; the flat dieline of the box (front, sides, back, bottom and top flap
laid out). Plain printed colour blocks only, plain kraft-grey inside.
```

## 6. Full-vision glass counter (`csk_showcase_full.png`) — G1

```
Sheet 6: a full-vision glass display counter (showcase). 1778 mm long, 508 mm deep, 965 mm tall. Glass on the
front, both ends and the top (6 mm tempered glass) in a slim brushed-aluminium frame (25 mm square corner posts,
20 mm rails). Inside, two glass shelves: the lower one
356 mm deep at about 430 mm height, the upper one 305 mm deep at about 690 mm, both starting at the front glass.
The back is two sliding glass doors in top and bottom aluminium tracks (each door about 914 mm wide, overlapping in
the middle), with a small lock at the centre. A thin LED strip runs along the inside of the top front rail. Show
empty; one small 3/4 view with a few slabs and packs on the shelves for scale.
```

## 7. Showcase details (`csk_showcase_detail.png`) — G1

```
Sheet 7: close-up details of the glass counter from sheet 6 (attach it). A grid of six close-ups, each straight on:
(1) a top corner where two rails meet a post and the glass sits in the frame; (2) the bottom corner where the post
meets the oak base and toe kick; (3) the rear door tracks top and bottom, showing the two doors in separate
channels; (4) the door lock at the centre; (5) a glass shelf resting on its support pins or clips; (6) the LED strip
under the top rail. Realistic hardware, no brand marks.
```

## 8. Sleeves and holders (`csk_sleeves_holders.png`)

```
Sheet 8: card protection, all with the blank grey card. (1) Penny sleeve: a thin clear soft plastic pouch
66.7 x 92.1 mm, open on one short edge, slightly crinkly. (2) Deck sleeve: 66 x 91 mm, clear front, matte coloured
back, open at the top. (3) Semi-rigid holder: 84 x 124 mm, 1 mm thick, clear stiff plastic with a small pull tab at
the open end. (4) Magnetic holder: two thick clear halves, outer 74 x 110 mm, 6 mm thick closed, with a recessed well
for the card and four small round magnets hidden in the border; show it closed, and open with the halves apart.
```

## 9. Grading-return box (`csk_grade_return.png`)

```
Sheet 9: a small white corrugated cardboard box that graded cards come back in: 150 x 125 x 170 mm, board 4 mm,
with a separate lift-off lid. Inside, a grey foam insert with eight slots holds eight slabs standing on edge side by
side. Show closed, open with slabs inside, and the lid off. Plain, no printing except a blank white shipping label.
```

## 10. Collector box and starter deck (`csk_collector_box.png`)

```
Sheet 10: (1) A premium collector box: a two-piece telescoping box, 190 x 89 x 165 mm, the lid slides down 30 mm
over the base. Inside: a plastic tray holding 8 booster packs standing on edge at the back, a small dice
compartment, a stack of cards and a pack of sleeves. Show closed, lid lifted, and the interior layout from above.
(2) A sealed starter-deck tuck box: 70 x 30 x 95 mm, a folded card carton with tuck flaps at the top, shrink-wrapped.
Plain printed colour blocks only.
```

## 11. Cartons and delivery boxes (`csk_cartons.png`)

```
Sheet 11: brown corrugated cardboard shipping boxes. (1) A distributor case holding 6 booster display boxes in a
row: 492 x 152 x 137 mm, taped shut with brown tape, a blank white label on the end; show closed, open (flaps up,
the 6 boxes visible) and knocked down flat for trash (644 x 289 mm). (2) Delivery boxes in three sizes:
305 x 229 x 102, 406 x 305 x 254 and 610 x 406 x 406 mm, each closed and taped, and open with the flaps up; and one
flattened. Realistic corrugated edges and fold lines, no printing.
```

## 12. Blister pack and retail accessories (`csk_blister_retail.png`)

```
Sheet 12: things a card shop sells, all hanging or shelf-ready, plain colour-block packaging only. (1) Hanging
blister: a printed card back 180 x 250 mm with a euro hang slot at the top, a clear moulded bubble holding two booster
packs. (2) Box of 100 deck sleeves with a hang tab: 72 x 42 x 98 mm. (3) Bag of 25 top-loaders with a folded header
card: 82 x 35 x 108 mm. (4) Bag of 100 penny sleeves with a header: 72 x 12 x 97 mm. (5) Clamshell of 7 dice with a
hang tab: 60 x 25 x 130 mm. (6) A card binder in shrink film with a sticker: 250 x 55 x 295 mm. (7) A tube holding a
rolled playmat: 70 mm across, 380 mm long, end caps. (8) A deck box in a window box: 82 x 86 x 116 mm. (9) A 60 ml
card-cleaner spray bottle: 40 mm across, 140 mm tall.
```

## 13. Storage boxes (`csk_storage_boxes.png`)

```
Sheet 13: white corrugated card storage boxes. (1) Row boxes that hold cards standing on edge in one row, with a
fold-over lid: outer 104.8 mm wide x 76.2 mm tall, lengths 85.7 mm (100 cards), 200 mm (400) and 381 mm (800); show
closed and open with cards inside. (2) "Monster" boxes with fold-up row dividers, hand holes at the ends and a
telescoping lid: 336.6 x 406.4 x 103.2 mm with 4 rows, and 419.1 x 495.3 x 104.8 mm with 5 rows; show closed and
open with the rows partly full of cards.
```

## 14. Binder (`csk_binder.png`)

```
Sheet 14: a 3-ring card collector binder. Cover 247.7 x 292.1 mm, spine 51 mm, padded matte cover, three D-rings on
the back cover. Show: closed (standing, spine view and front); open flat with a 9-pocket clear page (220.7 x
293.7 mm, pockets 65 x 90 mm in 3 x 3, three punched holes) holding blank cards; the ring mechanism close up; the
front cover opening on its hinge.
```

## 15. Deck box, playmat, dice (`csk_deckbox_playmat_dice.png`)

```
Sheet 15: (1) A flip-top deck box for 100 sleeved cards: outer 76 x 80 x 108 mm, hard matte plastic, the lid hinged
at the back; show closed, open and with cards inside. (2) A cloth-top rubber playmat 609.6 x 355.6 x 2 mm with a
stitched edge, plain single colour; show it flat and rolled up (about 45 mm across, 356 mm long). (3) Dice: a 16 mm
six-sided die with rounded corners and plain pips, a 22 mm twenty-sided die with blank faces, and a 22 mm round
counter token 2 mm thick.
```

## 16. Half-vision showcase (`csk_showcase_half.png`)

```
Sheet 16 (attach sheet 6): a half-vision display counter from the same family as sheet 6: 1778 mm long, 457 mm deep,
965 mm tall. A light-oak cabinet carcass like the attached shop image; glass only on the front upper part (470 mm tall) and the top; two glass
shelves; below the glass, a closed storage bay with sliding panel doors at the back; black kick base. Same
aluminium trim and rear sliding glass doors as sheet 6.
```

## 17. Glass tower and lit wall case (`csk_tower_wallcase.png`)

```
Sheet 17 (attach sheet 6): (1) A frameless glass tower case 457 x 457 x 1829 mm: glass on four sides, a 152 mm light-oak base,
four glass shelves, a hinged glass door with a small lock. (2) A lit framed wall case 1016 x 457 x 1848 mm: aluminium
frame, 203 mm light-oak base, four glass shelves, two sliding front doors, LED strips in the corner posts. Same materials as
sheet 6.
```

## 18. Countertop case and wall slab case (`csk_counter_case_wallslab.png`)

```
Sheet 18: (1) A countertop glass case for single cards and slabs: 900 x 450 x 300 mm, aluminium frame, a glass lid
hinged at the back (opens to about 80 degrees), dark felt deck inside. (2) A shallow wall-mounted case for graded
slabs: 1000 mm wide, 90 mm deep, 700 mm tall, four narrow ledges that hold 10 slabs each leaning back slightly, a
glass front that lifts up on a top hinge. Show both empty and one with a few slabs for scale.
```

## 19. Slatwall, hooks and shelf (`csk_slatwall.png`)

```
Sheet 19: white MDF slatwall panels, 19 mm thick, 2400 mm tall, in 1000 mm and 2000 mm widths, with horizontal
grooves every 76.2 mm (T-slot profile shown in a cut-away). Chrome wire hooks that slot into the grooves: 102, 203 and
305 mm long, 4.8 mm wire, with a flat price plate at the tip. A 1000 x 305 mm shelf on two slatwall brackets. Show a
panel with hooks and a shelf fitted, and the hook and bracket shapes on their own.
```

## 20. Gondola shelving (`csk_gondola.png`)

```
Sheet 20: retail gondola shelving with a white slatwall back (so hooks fit). One section is 1219 mm wide, 1372 mm
tall, with a 406 mm deep base deck and a 100 mm kick plate; slotted uprights. Show a single-sided section, a
double-sided section, an end cap, shelves 305 and 406 mm deep with a front price channel (38 mm lip), and an inside
corner unit 610 x 610 mm. Powder-coated light grey steel.
```

## 21. Wire rack and tiered box shelf (`csk_wire_rack_box_shelf.png`)

```
Sheet 21: (1) A chrome wire shelving rack 914 x 457 x 1829 mm with four wire decks on round posts and adjustable
clips. (2) A stepped display shelf for booster boxes: 1219 x 457 x 1372 mm, four tiers each tilted back 10 degrees
with a small front lip, light oak and white laminate. Show the tier profile from the side.
```

## 22. Card tables (`csk_card_table.png`)

```
Sheet 22: a glass-top card display table (a counter-height table with a shallow glass-lidded tray showing single
cards in slots). Three widths: 640, 760 and 880 mm; 460 mm deep; 914 mm tall. The tray holds 8, 10 or 12 cards in two
rows of shallow slots on a dark felt base; the glass lid is hinged at the back. White laminate legs and apron, light
oak top frame. Show the three sizes and the lid open.
```

## 23. Easels, risers and stands (`csk_easels_risers.png`)

```
Sheet 23: clear acrylic display pieces, 3 mm acrylic with polished edges. (1) Bent easels: for a slab 66 x 57 x 64 mm,
for a card 76 x 60 x 57 mm with a 25 mm lip, small 54 x 54 x 51 mm with a 19 mm lip. (2) A slab riser block 200 x 80
x 25 mm with two slots angled back 15 degrees, and a 3-tier riser 200 x 150 x 75 mm with six slots. (3) A clear block
card stand 70 x 40 x 25 mm with one slot, and one with a 9-card fan of slots. Show each with a slab or card in it.
```

## 24. Play area (`csk_play_area.png`)

```
Sheet 24: (1) White folding tournament tables, 762 mm deep, 737 mm tall, in lengths 914, 1524 and 1829 mm, grey
steel folding legs; show the longest set for three matches with two playmats facing each other per match.
(2) A black steel folding chair, 450 x 520 x 800 mm, seat height 445 mm; show open and folded.
```

## 25. Cash counter (`csk_counter_pos.png`)

```
Sheet 25: a shop cash counter (cash wrap) 1397 mm long, 610 mm deep, 965 mm tall, in the style of the attached shop
image: light-oak front panel, thick white top with a rounded edge, a bag shelf and cable hole on the staff side. On it: a steel cash drawer under the worktop, a generic card
terminal, a receipt printer, a POS screen on a stand and a handheld scanner in a cradle, a price-labelling gun. Show
the customer side and the staff side. All devices are plain generic shapes with no brand marks. (Plain paper notes
and a plain coin on the drawer tray, with no currency design.)
```

## 26. POS devices (`csk_pos_devices.png`)

```
Sheet 26: close-ups of generic, original-shaped shop devices, no brand marks, no recognisable real product shapes.
(1) Steel cash drawer 409 x 417 x 112 mm, the tray slid out: 5 note slots and 8 coin cups. (2) Countertop card
terminal 168 x 81 x 56 mm with a keypad and small screen. (3) Clamshell receipt printer 179 x 152 x 118 mm, lid
open showing the 80 mm paper roll. (4) POS screen 360 x 230 mm on a 200 x 200 mm base. (5) Handheld scanner
160 x 70 x 95 mm and its cradle. (6) Pistol-grip price labeller 190 x 45 x 125 mm with its label roll. (7) A generic
smartphone 72 x 150 x 8 mm. (8) A generic laptop 320 x 220 x 16 mm closed; show it open.
```

## 27. Bag, mailers, tape gun (`csk_bag_mailers.png`)

```
Sheet 27: (1) A kraft paper shopping bag 250 x 130 x 300 mm with twisted paper handles, open and folded flat.
(2) Kraft bubble mailers 100 x 200 mm and 150 x 250 mm, sealed and open. (3) A tape dispenser gun 250 x 75 x 180 mm
with a roll of brown tape. No printing.
```

## 28. Back room (`csk_backroom.png`)

```
Sheet 28: (1) A boltless steel warehouse rack 1829 x 610 x 2134 mm, four levels with particle-board decks, orange
beams and grey uprights. (2) A workbench 1524 x 762 x 914 mm with a green cutting-mat top and a lower shelf.
(3) A two-wheel hand truck (dolly) 450 x 500 x 1200 mm with a 350 x 200 mm nose plate and 250 mm rubber wheels.
```

## 29. Bins (`csk_bins.png`)

```
Sheet 29: (1) A round swing-lid shop bin 400 mm across, 700 mm tall, matte grey plastic; show the lid swinging.
(2) A full black trash bag, tied at the top, about 450 mm across and 600 mm tall, resting on the floor.
```

## 30. Signs and price tags (`csk_signs_tags.png`)

```
Sheet 30: all blank (no words). (1) A hanging shop-door sign: a 300 x 150 x 5 mm plate on a cord and suction hook,
the two faces in two different plain colours. (2) Price tags: a shelf-edge strip clip 76 x 32 mm that clips into a
38 mm shelf lip; a folded tent card 60 x 40 mm; a flat scan plate 76 x 38 mm for a hook tip. (3) A ceiling-hung
category sign 600 x 10 x 200 mm on two thin cables.
```

## 31. Posters and storefront sign (`csk_posters_storefront.png`)

```
Sheet 31: (1) Slim black aluminium poster frames, A2 (420 x 594 mm) and A1 (594 x 841 mm), with a plain colour-block
poster inside, no picture or text. (2) An exterior lightbox shop sign 1829 x 100 x 457 mm, a slim frame with a
plain lit face, mounting brackets. Show it lit and unlit.
```

## 32. Shop shell (`csk_shell.png`)

```
Sheet 32: modular shop walls, each 2000 mm wide, 150 mm thick, 3000 mm tall: a plain plastered wall, a wall with a
large shop window (aluminium frame), and a wall with a door opening (1000 x 2200 mm). A floor tile module
2000 x 2000 mm of grey vinyl and a ceiling module 2000 x 2000 mm of white acoustic tiles. Show them joined into an
L-shaped corner so the edges and joins are clear.
```

## 33. Entry door (`csk_entry_door.png`)

```
Sheet 33: a glass shop entry door and frame to fit the door opening of sheet 32: leaf 900 x 45 x 2100 mm, frame
1000 x 150 x 2200 mm, aluminium stiles with a full glass pane, a long vertical pull handle, a small bell above the
door, a spot for a hanging sign. Show closed and open to about 90 degrees.
```

## 34. Lights (`csk_lights.png`)

```
Sheet 34: (1) A recessed LED ceiling panel 600 x 600 x 12 mm. (2) A 2000 mm ceiling track rail (35 x 20 mm) with
three adjustable spot heads, each 70 mm across and 150 mm long. (3) A pendant light with a 300 mm wide, 250 mm tall
metal shade on a 1000 mm cord. Show each lit and unlit, all in matte white or black.
```

## 35. Scale figure (`csk_scale_figure.png`)

```
Sheet 35: a neutral, featureless 3D scale figure, 1800 mm tall, like an artist's mannequin: smooth light-grey
surfaces, simple rounded head with no face, standing in a relaxed pose. Front, side, back and 3/4 views. It must not
look like any existing game or engine mannequin.
```

## 36. Oak wall shelving unit (`csk_wall_unit.png`), optional

```
Sheet 36: the wall shelving unit from the attached shop image: an open light-oak shelving bay about 1200 mm wide,
400 mm deep and 2100 mm tall, with four fixed shelves above a row of white base cabinets (about 900 mm tall) with
doors and a white top. Show it empty, and one small view with deck boxes and small display boxes on the shelves.
```

---

## After the sheets arrive

- I log each one in `References/CardShop/REFERENCE_LOG.md`: its file, date, AI tool, the prompt number and any fixes
  asked for.
- **Build order:** the G1 pieces (sheets 1-7) are rebuilt first to match their sheets. Then the Unreal G1 run is
  repeated; the current G1 run still tests the pipeline and can go ahead now. After that, the families in the spec's
  P3-P5 order.
- **The blind test** (CLAUDE.md): for each piece, a judge sees the reference and a render side by side and must not
  be able to pick the copy on design. The spec's dimensions still win where they differ from the picture.
