# Compact SMG SM-01 (SMG01): craft study (2026-10-09)

Role: craft study. It says what every part is in 3D, how the real pattern builds it, and how it should look. The sheet
`References/Guns/SMG/smg_sheetA.webp` (1254x1254, AI-generated, Sheet A only) is the authority for silhouette and
proportion. The real pattern decides how small parts are made. Companion data: `craft_parts.json` (one record per part
plus materials, rulings, stations, inconsistencies, unseen surfaces and Fab options). The game/tech plan
(`SMG_BUILD_PLAN.md`, R1-R20) asked this study to confirm several of its rulings; section 4 answers each one.

Asset names: `SK_SMG01`, `SM_SMG01`, `SM_SMG01_Mag`. Study notes name the real pattern (a modern boxy polymer .45
blowback SMG with a side-folding stock, the "UMP" family) for reference only. Nothing buyer-facing uses it.

## 0. Sources

### 0.1 Sheet crops (all in `WorkFiles/guns/smg/scratch/craft/`, not committed)

| Crop | Shows |
|---|---|
| `p_left.png`, `p_right.png`, `p_top.png`, `p_34.png` | the four panels at 1:1 |
| `z_L_front.png`, `z_R_front.png` (4x) | muzzle, sights, forearm, vents, charging knob, port, lower rail |
| `z_L_mid.png`, `z_R_mid.png` (4x / 3.8x) | receiver centre, selector, magwell, guard, grip, rear sight |
| `z_L_stock.png`, `z_R_stock.png`, `z_Q_stock.png` (3-3.5x) | end block, hinge/latch, skeleton stock, butt pad |
| `z_T_front.png`, `z_T_rear.png` (3x) | top rail, sights from above, knob, hinge, stock from above |
| `z_Q_rec.png`, `z_Q_low.png` (2.6x) | 3/4: front face, sling hole, knob, vents, magazine, grip |
| `mask_L/R/T/Q.png` | threshold silhouettes (< 85 grey) |

### 0.2 Real-pattern evidence (saved in `WorkFiles/guns/smg/scratch/realref/craft/`, gitignored)

| File | Source URL | Used for |
|---|---|---|
| `manual_text_extract.txt` + `manual_fig_img*.jpg` (29 figures) | Operator's manual, UMP45/UMP40, 10/1999 rev. 08/2000: https://archive.org/download/MManuals/HkUmp40.pdf (served from https://ia601500.us.archive.org/28/items/MManuals/HkUmp40.pdf; text and figures pulled from the encrypted PDF locally) | construction text (materials, fold side, catch, cocking lever, lower receiver, magazine, rails), the specs table, figures: whole gun L/R (img7, 24, 29, 30), stock folded (img29, 42), release (img43), field strip (img34, 114, 118, 132), bolt group (img47-49), lower receiver (img69), magazine (img73, 74, 86, 87), selector positions (img62, 65, 68), cocking lever (img97, 102), rear sight (img192, 193) |
| `commons_HKUMP45_left.jpg` | https://upload.wikimedia.org/wikipedia/commons/d/d6/HKUMP45.JPG | the left side photo: cocking lever at the FRONT of its slot, slot length, forearm vents and hard-point bosses, support-pin head, trigger guard, mag release, stock |
| `commons_Ump-side_illustration.png` | https://upload.wikimedia.org/wikipedia/commons/8/80/Ump-side.png (CC BY-SA) | the folded stock lying along the right side, its position against the port and magwell |
| `commons_HK_HV_080810_046.jpg` | https://upload.wikimedia.org/wikipedia/commons/5/52/H%26K_HV_080810_046.jpg | context only (display table); low value |
| (text only) | https://en.wikipedia.org/wiki/Heckler_%26_Koch_UMP, https://hk-usa.com/hk-models/ump45/ | material, 25-round straight mag, aperture rear sight, rails screwed to hard points |

Gaps: no close-up photo of the right-side hinge knuckles, the feed lips from above, or the polymer surface under raking
light. The real pattern has no rail-clamp flip sights (its sights are fixed on the receiver), so those follow the
generic rail flip-sight pattern (RP15). The manual figures are small (~250 px) half-tones. They decide construction and
topology, not dimensions.

### 0.3 Real figures (manual specs table, UMP45)

Overall length 690 mm extended / 450 mm folded. Overall width 63.5 mm. Height with magazine 326 mm. Barrel 200 mm.
Sight radius 325 mm (the real gun's fixed sights). Mass 2.26 kg without magazine. Empty 25-round magazine 0.17 kg.
Polygonal bore, simple blowback, closed bolt. Line standard (study 3.5): 690 / 450 / 200 mm, **2.5 kg** (Wikipedia
figure; see open question C-Q4).

## 1. Scale, frames and stations

- **Scale.** The LEFT silhouette runs x = 23 to 608 sheet px (585 px). Scaled to 690 mm, that is **1.1795 mm per
  sheet px**. The ruler reads 86.6 cm (+26 %), so it is ignored. The TOP view runs 23-605 (582 px), the same scale
  within 0.5 %. Round parts read the same in TOP and side (muzzle device 22 vs 20-21 px), so TOP widths can be trusted
  to about +-1 px of shading.
- **Checks against the real figures.** Height from the sight tops to the magazine base is 287 px = 338 mm, against the
  real 326 mm with magazine (+3.7 %; the rail-clamp sights stand taller than the real fixed ones). The TOP body width
  is 53-55 px = 62.5-65 mm, against the real overall width of 63.5 mm. Folded length is 690 - 255 (hinge rear) = 435
  mm, against the real 450 (-3 %). Barrel: the muzzle is at X 690, so a 200 mm barrel puts its breech at about X 485,
  which lies inside the ejection port span (X 453-515), as on the real blowback. So the sheet's proportions hold, and
  it can be scaled uniformly.
- **Sides.** The labels are correct. The LEFT panel (muzzle to screen left) shows the knob. The RIGHT panel shows the
  port. In TOP, screen-down is the gun's left (the knob protrudes there).
- **Frame used below.** As in the AR-01 craft study: X = mm forward of the butt face along the bore, Z = mm above (+)
  or below (-) the bore axis (sheet y 201 in LEFT), Y = 0 on the bore plane, left = +Y. The spec converts these to the
  line frame (origin `Grip`, study 5.1). These are craft-level readings (+-3 px = +-3.5 mm). The measurer's trace
  replaces every number.

| Station | X (mm) | Z (mm) | Note |
|---|---|---|---|
| Muzzle device | 651 - 690 | +-11.8 (OD ~24) | 6-slot cage, open front |
| Jam nut / barrel thread collar | 632 - 651 | OD ~17.7 | groove ring at its front |
| Barrel collar at the receiver face | 620 - 632 | OD ~26 | steel ring in the polymer face |
| Receiver front face | ~620 | +33 to -42 | sling eyelet hole at the upper-left corner (3/4 view) |
| Front flip sight | ~590 - 605 | top +79 | post between ears; base screw head on the left |
| Forward long vent (left / right) | 561-602 / 531-598 | +21.8 to +29.5 | see RP3/RP4 |
| Charging knob centre (left) | ~551 | +19.5 | ball ~18 mm; bar with a pin runs back to X ~505 |
| Lower vents (two per side) | 579-606, 541-570 | -3.2 to -10.6 | oblong, through |
| Lower rail | ~540 - 611 | bottom -42.5 | 6 slots on the sheet |
| Diagonal forearm-to-magwell step | ~530 → ~510 | -3 → -42 | then a horizontal shelf rearward |
| Magwell (outer, with lip) | 452 - 512 | down to -79 (lip band ~-68 to -79) | integral with the lower |
| Magazine (visible) | top 512/452 → bottom 521/479 | -79 → -256 | 42 mm fore-aft; raked ~8 deg (bottom forward) |
| Ejection port (right) | 453 - 515 | -1.8 to +21.8 | the stock catch lip at X 517-527 |
| Trigger guard | 363 - 448 | bottom -100 | integral polymer loop |
| Selector hub (both sides) | ~364 | -31 | hub dia ~20; blade tip at about (355, -49.5) on the left (down-rear) |
| Pistol grip | top ~290-370, bottom 287-347 | bottom -167.5 | rake ~22 deg (front 17, rear 26) |
| Top rail | ~308 - 607 | base +35.4, top +47.2 | height 11.8 on the sheet |
| Rear flip sight | ~322 - 336 | top +82.6 | aperture; base screw head on the left |
| End block (lower's backplate) | 278 - 302 | +33 to ~-58 | lower-receiver locking pin head on the left |
| Hinge / latch block | 255 - 278 | | drawn as a vertical rounded boss on both sides |
| Stock top strut | 42 - 255 | +16.5 to +4.7 | |
| Stock web (slanted) | ~121 - 138 | | splits the front triangle and rear opening |
| Rear upright + butt pad | 0 - 42 (pad 0 - 28) | +20.1 to -87.3 | pad height 107 |

Sight radius on the sheet: 597 - 329 = **268 mm** (real fixed sights 325 mm; the sheet's rail sights stand closer).
Knob protrusion in TOP: about 16 px = 19 mm beyond the body side.

## 2. Part-by-part construction

Conventions for the builder:
- **Polymer:** P-round class (study 3.1). Edges R 0.6-2.0 mm (larger where hands go). Draft 1-2 deg on every wall
  parallel to a mould draw, and 2-3 deg where a moulded texture covers the wall (texture needs about 1 deg per 0.025 mm
  of depth). Nominal wall 3.0-3.5 mm (glass-filled polyamide). Ribs 0.6-0.7 x wall (2.0-2.5 mm) so they do not sink.
  Inside corners R >= 0.5 x wall.
- **Steel:** M-chamfer 0.3-0.6 mm, M-round 0.8-1.5 mm on sight ears.
- **Degenerate rule from day one (AR-01 lesson):** no bevel under 0.1 mm. A feature under the visibility minimum gets
  no bevel (or texture only), never a 0.02 mm strip. Cutters stay >= 0.1 mm from existing edges. Every generator
  checks `gunlib.tspace.unreal_drops() == 0` on its own output at every LOD. Small grooves (index line, panel seams,
  stipple border) go into the profile or loft, not a boolean, wherever the shape allows.

### 2.1 Upper receiver (fibre-reinforced polymer shell): LEFT, RIGHT, TOP, 3/4

- **What it is (manual).** The upper is "produced using fiber-reinforced plastics and houses other subassemblies". It
  contains metal guideways for the bolt, attachment points (support bolts) for the lower, the pinned barrel, the
  cocking lever above the barrel, the ejection port (right) with its integral stock catch, sling eyebolts (left), the
  sights or rail hard points on top, and the stock hinge at the rear.
- **Form.** A long box with flat vertical sides, as wide as the TOP trace (~62-64 mm; real overall width 63.5). Top
  flat at Z +33 under the rail. The forearm front reaches X 620 with a near-vertical front face (1-2 deg draft, edge R
  2). Its lower edge sits at Z ~ -35 under the lower rail. A full-length horizontal ledge line runs along both sides at
  Z ~ +12 to +15 (the knob sits just above it). Build it as a real 0.5-0.8 mm step: the upper band is set in, as a
  moulded shoulder. Behind the diagonal step (forearm to magwell, see 2.4), the shell's lower edge meets the lower
  receiver at the drawn horizontal seam.
- **Wall and openings.** Wall 3.0-3.5 mm. Every opening shows that wall: the forward long vents, the two lower vents
  per side, the port, the charging channel and the front-face bore opening. Vent ends are full radius (stadium),
  inside walls drafted 1 deg, and there is a 0.4 mm break on the outer lip. Through the vents the barrel shows
  (phosphated, dark).
- **Inside (model at form, task rule).** Two steel bolt guide rails, as L-section strips (3 x 4 mm) along the inner
  walls at bolt height, from the barrel's breech face rearward over the whole bolt travel plus 10 mm. A guide slot for
  the charging lever's slide above the barrel (see 2.3). The barrel's seat: a boss with the cross roll-pin bore (real:
  6 x 32 mm roll pin). The support-bolt bosses at the front of the magwell. The rear hinge knuckles (2.12).
- **Moulding notes.** Mould split: side actions form the two flat sides, and the core and cavity form the top and
  bottom. The parting witness runs along the top and bottom edge rounds of the side walls. At 0.05-0.1 mm it is texture
  only (normal map), under the visibility minimum. Ejector circles (dia 4-6 mm, 0.05 mm) go only on hidden faces: the
  inside of the top under the rail and the inner faces at the port. No sink is drawn on the sheet, so none is built.
- **Fasteners (sheet only, count and position from the trace).** Left: the lower's front support bolt head at about
  (X 509, Z -25), small round heads around the trigger housing, the lower's rear locking pin head on the end block
  (X ~282, Z -18). The right side has its own set. Sizes: support bolt and locking pin heads 6-7 mm, flush pins 4-5 mm
  (inset ring, 0.3 mm proud or 0.2 mm sunk as each sheet head reads).

### 2.2 Forearm vents, the forward long slot, and the front face: LEFT, RIGHT, 3/4

- Two oblong through-vents per side at Z -3 to -11 (~27 x 8.7 mm each), stadium ends, aligned on one line. The real
  pattern has the same pair. The real pattern's round side-rail hard-point bosses (front and rear of the forearm side)
  are **not** drawn on the sheet, so they are not built.
- One long upper slot per side at Z +22 to +29.5 (left X 561-602, right X 531-598): **built as a moulded through-vent
  on both sides, as drawn** (RP4). It is 7.7 mm tall, with stadium ends and 3 mm walls.
- Front face (3/4 view): flat, with a small 0.5 mm draft. A steel barrel collar ring (OD ~26) sits in a counterbore. A
  round eyelet hole (dia 6-7 mm) at the upper-left corner, just below the rail base, through a solid corner boss, is
  the front sling point (RP17). The right upper corner is plain.

### 2.3 Charging handle (cocking lever), its channel and the lock indent: LEFT, TOP, 3/4

- **Real pattern (manual and photo).** A non-reciprocating cocking lever, "located above the barrel", protruding left.
  At rest it is at the FRONT of a horizontal channel. It is pulled rearward to cock, and at full travel it is
  "rotated upward slightly" into an indent in the lever housing, which locks the bolt open. The lever sits on a sliding
  support with a roll pin (parts 12-15) and has its own return spring. Slot length on the photo is 85 mm, so travel is
  **~75 mm** (+-5) once the lever width is taken off.
- **As built (RP3).**
  - Knob: the sheet's ball (dia ~18 mm, from LEFT/TOP/3/4) on a short round neck (dia ~8 mm, ~6 mm long) that comes
    out of the channel. Knob centre at about X 551, Z +19.5, protruding ~19 mm.
  - Lever arm: the drawn flat bar behind the knob (to X ~505, with the round pin head at its rear end) is the lever's
    outer arm. It lies flush in a 0.8 mm recess and moves with the knob.
  - Channel: a 6.5 mm tall slot through the left wall, centred on Z +19.5. It runs from the knob's neck rearward for
    the full travel plus the neck (to about X 468). At its rear end a short upward notch (the indent, ~8 mm rise, ~7
    mm wide, round bottom) takes the neck when the lever rotates ~15-20 deg up about X.
  - Inside: the slide (a steel block 12 x 10 mm in a moulded guide over the barrel) carries a hook that pushes a lug on
    the bolt's top front. When fired, the bolt leaves the slide behind.
- **Bones and motion.** `charging_handle`: translate -X 0..75 mm, plus a lock rotation about X (0..+18 deg) at full
  travel, used by the Charge clip and the ReloadEmpty "slap". Joint row: sliding, 0.15-0.40 mm in the channel.
- **Finish.** Knob and neck in phosphated steel (or black polymer over a steel core; the sheet shows a satin dark
  knob). Wear: a polished crown and a bright rim on the knob. The polymer channel lips are polished along the travel.

### 2.4 Lower receiver (trigger housing, magwell, guard, grip, backplate): LEFT, RIGHT, 3/4

- **Real pattern (manual fig 10).** One polymer moulding holds the trigger mechanism, the selector levers, the magazine
  well, the magazine release, the bolt catch, and the integrated backplate with buffer and recoil-spring support (the
  tall block at the rear). Its front has hooked lugs that engage support bolts on the upper. Its rear is held by one
  removable locking pin. The grip is integral, with a separate bottom cover (part 58).
- **Magwell.** A box around the magazine, X 452-512, from the receiver bottom down to Z -79. The outer front face
  continues the diagonal step from the forearm (a sloped panel from about (530, -3) down to (512, -42), then a
  horizontal shelf). The drawn bottom lip band (~10 mm tall) is the **insertion flare**: the mouth widens 1.5-2.0 mm per
  side over its lowest 8-10 mm, with an R 1.5 rolled lip. Inner walls are drafted ~1 deg, opening downward, and fit the
  magazine with 0.3 mm per side (3.7 seated-mag row). There are **no internal guide ribs**, because the sheet's
  magazine ladder is recessed, not raised (RP22). A catch window in the rear wall takes the release paddle's nose. At
  the top is a hard stop shelf (the feed-ramp ledge) 1-2 mm above the seated magazine. Inside is dark polymer, class E
  texels (visible with the magazine out).
- **Trigger guard.** An integral polymer loop (RP12), drawn heavy: bottom bar ~6-7 mm deep at Z -100, front and rear
  legs ~6 mm, all edges R 1.5-2. The inside is large and rectangular with R 6-8 corners (gloved finger). There is no
  seam to the receiver, because it is one moulding.
- **Pistol grip.** Integral. The section is a rounded oblong, ~31-33 mm wide (unseen; real-pattern norm), with the
  front strap R 9-10 and the back strap R 12-14. The sheet's fore-aft depth is ~55-62 mm with a beaver-tail web at the
  top rear. Rake ~22 deg. The bottom is flared into a lip ~3 mm proud all round, and its lower 8-10 mm is the separate
  **grip cover** (real part 58): a seam 0.3 mm wide and 0.5 mm deep, with a flat plain bottom face and an R 1 rim.
  - **Stipple panel** (both sides, sheet): a rounded-rectangle inset following the grip axis, from ~20 % below the top
    to ~12 % above the bottom, inset ~5 mm from both straps. The border is geometry: a 0.5-0.6 mm step with a crisp
    0.3 mm break. The stipple inside is normal map only: raised pebbles 0.5-0.8 mm pitch, 0.1-0.15 mm tall, random,
    with roughness 0.78-0.88.
  - The small horizontal mark near the grip bottom in the 3/4 view is the cover seam, not a slot.
- **Backplate / end block.** The tall block at X 278-302 rises from the lower to the receiver top (the lower's
  integrated backplate; real fig 10 #8-10). Its front edge is a visible design seam (0.3-0.5 mm) against the upper. The
  rear locking pin head (dia 7 mm, flush steel with a 0.5 mm chamfer) sits on its left face. The pin runs through to
  the right, where a plain flush end shows.
- **Upper/lower seam.** The drawn horizontal line from the diagonal step back to the end block (Z about -5 to -12 on
  the trace) is the parting between upper and lower: a 0.3-0.5 mm modelled seam, 0.6 mm deep.

### 2.5 Selector (ambidextrous): LEFT, RIGHT, 3/4, manual fig 11a-c

- **Real pattern.** Safety/selector levers "fitted on both sides of the pistol grip" on one shaft (parts 48 left, 49
  right). Each lever is a **teardrop**: a round hub (the indicator dial) tapering into a short flat blade. It is a
  steel plate with a black finish, ~2.5-3 mm thick, standing ~1 mm off a raised round seat in the housing. The hub
  carries a straight index line. The real gun has painted pictograms on the housing. The sheet's small red dot and the
  engraved marks near the selector are those markings, and they are **not built** (RP7).
- **As built.** Hub dia ~20 mm (sheet) on a seat boss 1.0 mm proud. The blade tapers from ~12 mm at the hub tangent to
  ~6 mm at a rounded tip (R 3), with the tip ~21-24 mm from the axis. The outer face is flat with an R 0.8 edge round,
  and the blade tip is slightly thicker as a thumb ledge (+0.5 mm). The index line is a 0.5 mm wide, 0.3 mm deep groove
  across the hub along the blade axis, cut in the profile with no paint (C-Q2). The right lever is the same outline,
  ~10 % smaller (real: the right lever is the smaller part).
- **Rest pose = the sheet's pose.** The blade points down-rear at ~65 deg below the rearward horizontal (both side
  views agree: left 65, right 64). Real positions from manual fig 11: SAFE with the blade forward-down (~45 deg below
  forward); SEMI and AUTO with the blade swung rearward, AUTO the furthest rearward (near horizontal). Builder default:
  the sheet pose = SEMI, AUTO = 45 deg further rearward, SAFE = 110 deg forward of SEMI. The measurer confirms the
  three angles on the saved figures. Clips that move the bolt hold AUTO (AR-01 lesson).
- **Bone.** `selector`: rotate about Y (the transverse shaft), both levers on one bone. Hinge row 0.10-0.30 mm, and the
  swept minimum to the grip and guard >= 0.10.

### 2.6 Trigger: LEFT, RIGHT, manual fig 10

- A steel blade (real part 34), C-fillet class, ~6 mm wide, curved forward-concave. The face is smooth and slightly
  crowned (R 8 across). It hangs ~30 mm below the housing and pivots on a transverse axle (one of the "axle (3x)" pins:
  a flush pin head on each side above the guard). `trigger`: rotate about Y, ~12-15 deg pull.

### 2.7 Magazine release: LEFT (front of the guard), manual fig 10 #2, photo

- **Real pattern.** A steel paddle (parts 50-52) on a transverse axle with a spring. It hangs below the lower behind the
  magwell, just ahead of the trigger guard's front leg. To release, the paddle is pushed FORWARD with the trigger
  finger. The paddle rotates about Y, its lower end moving forward and its upper nose moving rearward out of the notch
  in the magazine's rear face. One centred paddle (Y = 0) serves either hand.
- **As built.** Paddle ~10 mm wide, 3 mm thick, ~18 mm hanging below the housing, with a slight forward-curved lower
  end (finger pad, R 4). The nose engages the magazine's notch by >= 1.5 mm. The pivot sits ~8 mm above the housing's
  lower face inside the catch window. `mag_release`: rotate about Y, ~10-12 deg to clear the notch.

### 2.8 Bolt (visible through the port): RIGHT, manual fig 8-9, img47-49

- **Real pattern.** A heavy rectangular steel block. Its upper section is longer (it overhangs rearward) and carries the
  recoil-spring guide bore at the top front. The lower section carries the bolt face with the extractor (right side,
  port side) and the firing pin with its retaining pin. **"The right side of the bolt has a thumb recess for manual
  closing (forward assist)."** It runs in the upper's metal guideways. The recoil spring assembly (guide rod + spring
  + cone support in the backplate) sits above the bolt's centre line.
- **As built.** The block section fills the port height (~22 mm visible) and is ~26 mm wide. M-chamfer 0.4 mm on every
  edge, with fine milling passes in roughness only. The extractor is a flat steel claw ~5 x 25 mm, inset in the right
  face at the bolt face, its hook 1 mm over the face. The **thumb recess** is a shallow oval scallop ~16 x 9 mm, 1.5 mm
  deep, on the right face, centred in the port with the bolt forward. The face has a 12 mm boss for the case head and
  a 1.5 mm firing-pin hole. A guide-rail groove is cut along each lower edge to ride the receiver rails (0.2 mm per
  side). A charging lug on the top front takes the slide's hook.
- **Travel = 75 mm** (charging lever travel, RP5). The bolt face rests at the barrel breech, about X 485. Fully back it
  is at about X 410, behind the top round's base (~X 452) and the port's rear edge. `bolt`: translate -X.

### 2.9 Ejection port and the stock catch: RIGHT, manual p.11

- The port is right side only: X 453-515, Z -2 to +22, through the 3.0-3.5 mm wall, with corners R 2. The rear edge
  has a slight 45 deg deflector chamfer (real moulded ports ramp the case out). The interior is dark: bolt face,
  barrel breech and feed lips, with class E texels.
- **Stock catch (real: "the ejection port includes an integral catch for engagement of the buttstock in its folded
  position").** The drawn vertical rounded tab at the port's front edge (X 517-527, full port height, proud ~3 mm) is
  that catch. It is moulded with the upper, with a hooked rear face (undercut 1.0-1.5 mm) that the folded stock frame
  snaps behind. Polished wear on its rear lip.

### 2.10 Barrel, collar and muzzle device: LEFT, RIGHT, TOP, 3/4

- **Barrel.** Phosphated steel. Visible OD 17.7 mm (the thread collar) ahead of a steel collar ring (OD ~26, X
  620-632) seated in the receiver face. 200 mm long: the breech is at ~X 485. It is held by a transverse roll pin in the
  receiver (unseen). The bore is .45-class (dia 11.4), dark, >= 2 calibres deep from the device's front. The polygonal
  bore is texture only.
- **Muzzle device (`muzzle_device`, X 651-690).** A slotted cage, OD ~24 mm, 39 mm long, open front. **Six through
  slots** at 60 deg spacing with one slot centred on each side (3 and 9 o'clock). That gives 3 slots in the side views
  and 2 in the TOP view, which matches both panels. Slots ~4 mm wide, ~26 mm long, with round ends. The bars between
  slots are 6-7 mm. The front rim is a solid ring ~5 mm long, chamfered 0.6 mm outside and 1 mm at the bore. The rear
  is a solid ring, then a 2 mm groove (drawn), then the jam nut / thread collar (X 632-651) with two 3 mm wrench flats
  (unseen; real practice) on the underside only. Inside the cage: bore ID ~13.5 mm, walls 4-5 mm. Soot gradient from
  the slots.

### 2.11 Rails: top (long) and lower (short): LEFT, RIGHT, TOP

- **Real pattern.** MIL-STD-1913 rails are "screwed onto the molded-in hard points", with **two cylindrical screws
  per rail** (short and long rail kits).
- **As built.** `gunlib.rail_1913` profile on top: dovetail 21.2 mm, 45 deg flanks, slots 5.24 mm square-bottomed at
  10.01 mm pitch, 3.0 mm deep, M-chamfer 0.3-0.5. The TOP view draws the rail band ~35 mm wide, so the rail body has a
  **base flange** ~30-34 mm wide and ~4 mm tall under the dovetail, seated on the receiver top. Real receiver rails
  often have a base wider than the dovetail. Height: the sheet reads 11.8 mm (dovetail ~7.8 + flange ~4). Slot count =
  round(length / 10.01). The sheet's ~20 visible teeth over the middle are AI-irregular, so the standard pitch wins.
  - Top rail X ~308-607, about 29 slots. Lower rail X ~540-611, 6 slots (sheet), facing down.
  - Two socket-head cap screws per rail (head dia 8.5, 5 mm thread written in mm), counterbored in two slot floors so
    the heads sit 0.3 mm below the floor: visible only looking into those slots. The flat butt joint to the receiver is
    0.01-0.05 mm.
- Material: phosphated steel per the prompt. The slot edges and flank crests wear bright (bare steel, R mask).

### 2.12 Side-folding skeleton stock, hinge, latch and fold: LEFT, RIGHT, TOP, 3/4, manual p.12, img29/42/43

- **Real pattern.**
  - "The buttstock folds **to the right** along the upper receiver." The open frame lets the gun fire folded.
  - "Pressing the catch releases the buttstock for folding." The release is a push button on the LEFT side of the
    stock's hinge block, pressed inward by the thumb (img43: a vertical oval recess).
  - "When folded, the buttstock engages on the catch located on the forward part of the ejection port. For unfolding,
    the buttstock is lifted off the catch."
  - The butt plate has a rubber pad. The real stock top carries a rubber cheek piece, which the sheet does not draw, so
    it is not built.
  - "In the forward part of the buttstock a hole is provided for insertion of the locking pin": the sheet's small hole
    on the front strut.
  - Parts: buttstock axle (vertical), buttstock lock + spring.
- **Hinge (RP2).** A corner hinge at the **right rear** of the receiver: a vertical steel axle (dia 6) through two
  receiver-side knuckles (top and bottom, moulded with steel bushings) and one stock-side centre knuckle. The drawn
  vertical rounded boss on the **left** is the stock's **latch housing** (the stock-side lock: a spring-loaded latch
  bolt moving along Y that drops into a notch in the receiver's left rear). The vertical oval **release button**
  (~7 x 16 mm, 1 mm proud, pressed inward 2 mm) sits in its outer face. The sheet's horizontal grooves on that boss
  are the button outline and the knuckle split lines. On the right, the drawn boss is the true knuckle stack.
- **Frame.** A one-piece moulded polymer frame, symmetric about its mid-plane. The mould splits on the mid-plane, so
  every outer perimeter and opening wall has 1 deg draft each way from a parting line around the middle (witness
  texture only).
  - Top strut Z +4.7 to +16.5 (11.8 tall), ~29.5 mm wide (TOP).
  - Lower strut from the hinge block rising rearward (~19 deg) to the butt toe, ~12 mm deep.
  - A slanted web X ~121-138 splits a small front triangle opening from a large rear opening. A rear upright X 28-42.
  - Openings have a raised border (a 0.8-1.0 mm step at 1.5 mm from the edge, as drawn) with R 1.5 inner rounds.
  - Struts are solid with flat faces (both faces are seen when folded).
  - Two round through-holes (dia ~6) on the rear upright, top and bottom. The bottom one is the rear sling point (the
    real stock has a sling hole at the toe; RP17).
  - A dia 4 mm locking-pin storage hole in the front strut near the hinge block.
- **Butt pad.** Rubber, X 0-28, height 107, width ~55-59 mm (TOP). It is wider than the frame and wraps the upright
  with a 2 mm lip. The rear face has horizontal ribs as geometry (they show in the side silhouette): count them from
  the trace (about 12-14; pitch ~7-8 mm, depth ~1.2 mm), with R 0.6 crests. Edges R 3-4. A 0.3 mm seam to the frame.
- **Fold.** `stock` rotates about the vertical axle (+Z) by ~180 deg to the right. Folded, it lies along the right side
  with the frame flat, the top strut at about receiver top height and the pad near the magwell front. Real
  construction keeps it close: the stock-side hinge block is **joggled** (a short Z-link) so the folded frame's inner
  face sits ~2-4 mm off the highest right-side feature (selector lever, port catch). The joggle hides inside the hinge
  block's drawn outline. The folded frame clips behind the port catch's hook.
  - **Gates for the fold:** 0 intersections and swept minimum >= 0.10 mm (hinge row) over the whole sweep. Catch
    engagement >= 1.0 mm folded. Clearance to the right selector, grip, magwell and charging knob (left: n/a).
  - **Bounds extension** for both states at every LOD (AR-01 lesson).
  - **Folded length check:** muzzle to the rear-most point = 450 +-15 mm.
- **Flag (sheet geometry).** On the sheet's proportions the folded top strut crosses the port at Z +5..+17, and the
  rear upright covers the port's front ~20 mm. The real stock lets the gun fire folded. See C-Q3: default accept, and
  the game treats folded as no-fire or spawns `ShellEject` unchanged.

### 2.13 Flip sights (rail-clamp; no real-pattern equivalent on this gun): LEFT, RIGHT, TOP, 3/4

- **Pattern followed (RP15).** Generic rail-clamp backup sights: a machined aluminium (black anodized; or phosphated
  steel per the prompt) clamp base with a recoil lug in one rail slot (integer slot index), clamped by a transverse
  cross-bolt. The bolt head is on the LEFT (the sheet shows a round head on the left of both bases), with a captive
  clamp jaw and nut on the right. A spring-detented leaf rides a transverse pin. The sheet shows no release button, so
  none is built: the leaf folds by pushing it over its detent. **Fold directions: rear leaf forward, front leaf
  rearward** (toward each other, the common arrangement). Folded height <= rail top + 12 mm.
- **Rear (`sight_rear`, X ~322-336, top Z +82.6).** A rectangular leaf with two protective side ears framing a round
  aperture disc. Aperture dia 2.0 mm (diopter) in a 10 mm disc boss, with a 45 deg countersink on the eye side. A small
  plain round windage drum on the base's right (3/4: a disc beside the leaf) with fine knurl in the normal map and no
  ticks. Class A texels.
- **Front (`sight_front`, X ~590-605, top Z +79).** Two ears (2.5-3 mm thick plates, tops R 1) standing on the leaf.
  Between them a square post 1.85 mm wide, its tip level with the aperture centre for B4. The tip is flat-topped with a
  0.2 mm break. The post base is threaded into the leaf, with a 4-lobe adjuster ring (geometry only if >= 4 px at ADS;
  else texture). Class A.
- **B4 from the blockout (AR-01 lesson).** The `Sight` socket goes at the aperture centre. The post tip is centred in
  the aperture within 0.5 px at ADS. Nothing (knob, rail teeth, ears) occludes the post.

### 2.14 Magazine (`SM_SMG01_Mag`): LEFT, RIGHT, 3/4, manual fig 12-13, img73/74/86/87

- **Real pattern.** A polymer housing, 25 rounds of .45, straight, double stack. The real body has transparent witness
  panels. The sheet and the prompt ("transparent-free solid body") make it **solid**. Parts: housing, floor plate,
  follower, follower spring, locking plate. The floor plate **slides on from the rear** on rails moulded into the
  housing's bottom flange. It is retained by the locking plate's tab, which shows through a hole in the floor plate.
  The lips present the top round centrally (img87: the round sits between the two lips at the centre), so it is a
  double stack tapering to a single-feed position over the top ~30 mm. A catch notch is in the rear face near the top.
- **Section.** Fore-aft 42 mm (sheet), thickness ~27 mm (real norm: .45 rim 12.0 x (1 + sin 60) = 22.4 mm inside, plus
  two 2.3 mm walls; confirm against the 3/4 panel in the blockout, AR-01 R32 precedent). Corners R 3 (front) / R 2.5
  (rear). Draft: the body is drawn straight, so a 0.25 deg core draft on the inside only (the outside is formed by
  slides).
- **Side detail (sheet).** Two parallel **recessed channels** (each ~4.5 mm wide, 1.0 mm deep, 3.5 mm apart) run down
  the centre of each side from ~25 mm below the top to ~15 mm above the floor plate. They are crossed by flush ties
  (a "ladder") at the levels the trace shows (4 on the LEFT view). Floors flat, walls drafted 2 deg, edges R 0.4. These
  are moulded, not windows.
- **Front spine.** A raised rib ~6 mm wide, 0.8 mm proud, full length. The mould parting line runs down its crest (the
  sheet's bright line on the 3/4 front edge = edge wear on the rib's crest). The rear spine is plain, with the parting
  line, and the **catch notch**: a rectangular window ~8 x 4 mm, 2.5 mm deep, with a square bearing face on top, ~30
  mm below the top.
- **Top.** Polymer feed lips folded inward (wall 2.0), tapering from double to single. A dark polymer follower is
  visible between the lips (no cartridge, AR-01 precedent). The front top edge is stepped higher than the rear (img73).
- **Floor plate.** A separate polymer cap 5 mm thick with a 1.5-2.0 mm lip proud all round (sheet), the front edge
  rounded R 4. On the bottom face: a dia 8 mm hole with the locking plate's dark tab flush inside it (real; unseen on
  the sheet) and two fine slide-rail seams along the sides.
- **Fit.** 0.3 mm per side in the well. The notch carries the paddle nose >= 1.5 mm. 1-2 mm overtravel to the well's
  top shelf. Insertion is straight along the mag axis (raked ~8 deg, so `Mag` +Z is tilted with it).
- **Wear (mag).** Insertion streaks along the axis on the upper 40 mm (the part that enters the well). Whitened scuffs
  on the floor plate corners and lip (drops). A polished front spine crest and polished feed lips. The ladder floors
  collect dust (B).

### 2.15 Small fixed parts

- **Sling points.** Front: the eyelet hole in the receiver's front-left corner boss (dia 6-7, a steel sleeve 0.6 mm
  proud), `SlingFront`. Rear: the stock's lower rear through-hole, `SlingRear`. The real gun's left-side eyebolts are
  only where the sheet shows holes.
- **Pins.** The support bolt (front of the magwell), the locking pin (end block), the trigger and selector axles. They
  are steel flush inset rings: dia 4-7 mm, a 0.3 mm chamfer, set 0.1-0.2 mm proud or sunk as the sheet head reads.
- **Recoil spring assembly.** Internal, hidden in every rest and clip pose, so it is not modelled (the port only shows
  the bolt's side and the breech).

## 3. Materials, texture and wear

Sheet samples, median sRGB under the sheet light (background ~152-160):

| Region | sRGB median | Ratio to backdrop |
|---|---|---|
| Receiver side flat (L / R) | (63, 64, 66) / (76, 78, 81) | 0.40 / 0.49 (the right panel is lit more) |
| Grip stipple | (64, 65, 66) | 0.41 |
| Magazine side | (55, 57, 59) | 0.36 (darker than the receiver) |
| Stock struts | (59-63, 60-64, 61-66) | 0.39 |
| Butt pad | (55, 55, 58) | 0.36 |
| Muzzle device / rail side | (40, 40, 40) / (49, 50, 51) | 0.26 / 0.32 (the steel is darker than the polymer) |

The hue is neutral with a faint cool cast (B - R = +2 to +3). The sheet's polymer is a flat dark grey-black, not jet.

| Material | Metallic | Base colour sRGB (linear) | Roughness | Micro-texture | Wears to |
|---|---|---|---|---|---|
| **Glass-filled black polymer** (upper, lower, grip, guard, stock frame) | 0 | (46, 47, 50) ~0.028-0.031, +-4 levels mottling | **0.50-0.58 on flats (satin); 0.44 on hand zones** (spec R46, W4b: 0.58-0.66 overlapped the phosphate and both read as one material) | moulded-in matte texture (EDM-spark class, Ra ~2-3 um) as Detail16 normal noise, feature scale **0.05-0.15 mm**, tile ~20 mm; plus faint flow lines only near the gates (hidden faces) | **polish**: roughness -0.10 to -0.18, base -2 levels (handling); **scuff/whitening**: base +15 to +35 levels, roughness +0.05 (impact, edge abrasion) |
| Grip stipple panel | 0 | as polymer (pebbles x 1.24-1.46, R46) | 0.72-0.82 (R46; was 0.78-0.88) | pebbles 0.5-0.8 mm pitch, 0.1-0.15 mm tall (normal + AO) | crowns polished (palm) |
| **Magazine polymer** | 0 | (41, 42, 45) ~0.022-0.025 | 0.55-0.65 | finer matte, 0.04-0.1 mm | polish on the upper 40 mm, the spine and the lips; whitening on the floor plate corners |
| **Rubber** (butt pad) | 0 | (42, 42, 44) ~0.023 | 0.82-0.92 | fine rubber grain 0.05 mm, mould flash at the rib ends (texture) | barely; dust in the rib roots |
| **Manganese phosphate (parkerized) steel** (barrel, collar, device, rails, sight bodies if steel, knob, selector, release paddle, trigger, pins, bolt outside) | 0 | **(40, 41, 42) ~0.021-0.023** (spec R44, W4 review: this row first read (48-52, 49-53, 50-54), which put the steel LIGHTER than the polymer against the sheet samples above and the ratio rule below) | **0.66-0.78 dry, 0.56-0.66 where oiled, base (45, 46, 47)** (spec R46: a dead-flat crystalline charcoal against the polymer's satin, the base raised so the rendered ratio stays at the sheet's, G20; R44 read 0.62-0.76 / 0.52-0.62 at (40, 41, 42)); oiled = bolt, rail slots | crystalline phosphate grain 0.02-0.05 mm (roughness noise +-0.05) | bare steel |
| Bare / worn steel (edges, rail crests, slot edges, knob crown, bolt flanks, trigger face) | 1 | 0.53-0.56 linear (190-196) | 0.50-0.62 as painted (micro-scratched; R46: 0.42-0.55 still glinted as white specks at 35 cm; the clean 0.25-0.40 only on the bolt's sliding flanks, 0.15-0.25) | lengthwise scratches | - |
| Anodized aluminium (only if the sight bodies are aluminium) | 0 | (45-55) | 0.45-0.60 | | bright aluminium: metallic 1, 0.91, rough 0.30-0.45 |
| Soot (muzzle slots, crown, port) | 0 | 0.013 (sRGB 30, the PBR floor; R44: 0.02-0.03 sat on the darkened phosphate and could not be seen) | 0.85-0.95 | | gradient from each slot |

Calibrate each finish against a sheet crop under matched light before the first look review (study 3.3). The ratio
polymer / steel ~ 1.3-1.5 on the sheet must hold: the steel parts read darker and slightly glossier-edged than the
polymer.

**Wear logic (by cause, study 3.4; the sheet's level is "moderate": white specks and edge scuffs).**
- **Polymer never shows metal.** It polishes where hands slide, and whitens where it is struck or abraded:
  - polish (G mask): grip front and back straps, the beaver-tail web, the forearm belly and left side (support hand),
    the magwell flare (support hand on the well), the top strut where the cheek rests, the selector's swept arc;
  - whitening and scuffs (R mask, thin 0.3-1.0 mm bands): receiver vertical corners, the front face rim, the forearm
    lower edge, vent and port lips, the magwell lip, stock frame outer corners, the pad toe and heel, the magazine
    floor plate;
  - small scratches: light grey, under 0.2 mm, mostly fore-aft on the receiver sides.
- **Insertion:** a scratch fan into the magwell mouth, and streaks on the magazine's upper body along the axis.
- **Steel:** bright edges on the rail slot edges and flank crests, sight ear tops, device front rim and slot edges, knob
  crown, selector blade tip, trigger face. Sliding polish on the bolt flanks (seen through the port) and the
  charging-channel lips.
- **Cavity grime (B):** rail slot roots, vent ends, the ladder channels, around pin heads, rib roots of the pad, the
  hinge knuckles, stipple roots.
- **Soot:** muzzle device slots and crown; a light gradient at the port's rear edge.
- **Handedness:** right-handed shooter. The left side carries more support-hand polish (forearm, magwell). The right
  side carries the port soot and the selector thumb arc. Left and right wear differ (G9).

## 4. Real-pattern rulings (the builder follows these; the plan's R numbers are answered)

| # | Part | Sheet says | Real pattern | **Ruling** | Plan |
|---|---|---|---|---|---|
| RP1 | Stock fold side | TOP: hinge block reads toward the gun's right | "folds to the right along the upper receiver" (manual p.12; img29, Ump-side) | **Right.** Axle vertical at the right rear corner | confirms R10 / Q2 |
| RP2 | Hinge, latch, folded retention | a vertical rounded "knuckle" on BOTH sides | right-corner axle; release = push button on the left of the stock's hinge block; folded, the stock engages the integral catch at the front of the ejection port | Right side: true knuckle stack + steel axle. Left side: the drawn boss = latch housing with an oval release button. Folded retention = the port-front catch hook (the drawn tab), not a stud. Stock-side hinge block joggled so the folded frame lies 2-4 mm off the side | adjusts R10 ("hook over a stud" → the port catch) |
| RP3 | Charging handle | ball knob with a bar + pin behind it; a long open slot AHEAD of the knob | lever rests at the FRONT of its channel; the channel runs rearward ~85 mm; travel ~75 mm; rotates up into an indent at the rear to lock the bolt open | Knob at rest where drawn (silhouette: LEFT, TOP, 3/4). A 6.5 mm channel runs REARWARD from the knob for 75 mm + neck, with the lock indent notch at its rear. The drawn bar = the lever arm, flush, moving with the knob. The forward slot is a vent (RP4) | resolves R4's "confirm"; C-Q1 |
| RP4 | Forward long slot, both sides | drawn on the left (X 561-602) and the right (X 531-598) | no such slot on the real right side; on the real left the long slot is the cocking channel (behind the lever) | Both drawn slots are built as **moulded through-vents**, as drawn per side. The sheet shows them on both sides, so they are the sheet's design, not a mirrored handle slot | **overrides R18's default** (plain right wall); C-Q1 |
| RP5 | Bolt | port shows a flat dark block | rectangular blowback block, longer upper section with the spring-guide bore, extractor right, **thumb recess on the right face** | Build the block with the extractor and the thumb recess (visible in the port). Travel 75 mm, rest face at the breech (~X 485) | refines R5 (travel 75, not 60-70) |
| RP6 | Port | rectangular, with a vertical tab at its front | right side only; integral stock catch at its front | As 2.9; the tab is the catch with a hooked rear face | confirms R6 |
| RP7 | Selector | round hub + thin lever; a white line on the hub; a red dot nearby (LEFT, 3/4) | teardrop steel levers on both sides of one shaft; index line on the hub; painted pictograms on the housing | Teardrop levers (hub 20, blade tip 21-24 from the axis), right lever ~10 % smaller, one bone. Index line = an unpainted groove. **No red dot, no pictograms.** Positions: sheet pose = SEMI; SAFE forward-down; AUTO further rearward | confirms R7 (dots not built); C-Q2 |
| RP8 | Mag release | small lever at the guard's front | one central steel paddle behind the magwell, pushed FORWARD to release; nose in a notch on the mag's rear | As 2.7: centred paddle, rotate about Y, ~10-12 deg | confirms R8 (one centred paddle = ambidextrous) |
| RP9 | Bolt catch | not distinguishable | internal catch above the mag release; released by a catch on the left | **Not built** (no `bolt_catch` bone). ReloadEmpty: bolt held open (internal), released by the charging lever (real "slap" from the locked indent) | confirms R9 / Q7 default |
| RP10 | Magazine | solid; 2 recessed channels with cross ties; front spine highlight; flared floor plate | polymer, translucent panels, floor plate slides on from the rear and is locked by a plate tab through a hole; single-feed lips; rear catch notch | Solid (prompt). Ladder channels recessed 1.0 mm. Front spine rib with the parting line. Floor plate on rear-entry rails with the dia 8 locking-tab hole (unseen face). Single-feed lips, follower, no cartridge. Thickness ~27 (confirm in blockout) | refines R16 |
| RP11 | Trigger | thin curved blade | steel trigger on an axle | Steel C-fillet blade, smooth crowned face | confirms R14 |
| RP12 | Trigger guard | heavy loop | integral with the pistol-grip moulding | Integral polymer loop at the sheet's thickness; no seam | confirms R14 |
| RP13 | Grip | stipple panel, flared base, small mark near the bottom | integral grip + separate bottom cover (part 58) | Integral grip; stipple border in geometry + stipple in the normal map; the bottom ~9 mm is a separate cover with a seam (the drawn mark) | refines R13 |
| RP14 | Rails | top rail band ~35 mm wide in TOP; lower rail 6 slots | 1913 rails screwed to moulded hard points, 2 screws each | Standard 21.2 dovetail on a ~30-34 mm base flange (TOP width). 2 counterbored screws per rail in slot floors. Pitch 10.01 (the sheet's teeth are irregular) | refines R2/R3 |
| RP15 | Flip sights | rail-clamp sights, a screw head on the left of each base; front ears + post; rear frame + aperture + side drum | (none on the real gun) generic rail-clamp BUIS | Clamp base + recoil lug + cross-bolt head on the left; spring detent, no button; rear folds forward, front folds rearward; aperture dia 2.0 in a 10 mm disc; post 1.85 mm; folded <= rail + 12 | confirms R12 |
| RP16 | Muzzle device | slotted cage + groove + collar | flash hider timed by a jam nut on a threaded muzzle | 6 slots at 60 deg, one centred on each side (3 in side views, 2 in TOP); open front; jam nut with flats on the underside | refines R15 |
| RP17 | Sling points | hole at the receiver's front-left corner (3/4); two holes on the stock's rear upright | eyebolts on the left of the upper; sling hole at the stock toe | `SlingFront` = the front-left eyelet; `SlingRear` = the lower stock hole. The top stock hole is a plain through-hole | adds sockets' places |
| RP18 | Lower attachment | round heads at the magwell front top and the end block | front support bolts + a rear removable locking pin; a locking-pin storage hole in the stock | Steel flush pin heads where drawn; the stock's small front hole = the storage hole (dia 4) | new |
| RP19 | Upper/lower seam | horizontal line from the diagonal step to the end block | separate upper and lower mouldings | 0.3-0.5 mm design seam, 0.6 deep | confirms R1 |
| RP20 | End block | tall block between the receiver and the hinge | the lower's integrated backplate (buffer, spring support) | Part of the lower moulding; seam at its front edge | new |
| RP21 | Magwell internals | lip band | flared mouth; catch window; hard top stop | Flare 1.5-2 mm per side; 1 deg draft; catch window; top shelf; **no guide ribs** (the mag's ladder is recessed) | adjusts R17 (drops the guide channels) |
| RP22 | Cheek piece, side-rail bosses, cocking-lever housing screws | not drawn | the real gun has them | Not built (the main views decide visible surfaces; invent nothing) | - |

## 5. Unseen surfaces and their plain treatment

| Surface | Treatment |
|---|---|
| Receiver underside between the lower rail and the magwell | flat polymer, the diagonal panel continued, two ejector-free plain faces |
| Underside of the lower between the magwell and the guard | flat; the paddle's catch window and pivot boss |
| Receiver front face (right half) | plain; the barrel collar centred; no right eyelet |
| End-block rear face and the hinge faces behind the stock | plain polymer; knuckle faces steel-bushed; class E; visible only during the fold |
| Inside the vents and port | dark polymer walls (1 deg draft), the barrel and bolt behind |
| Inside the magwell | dark; catch window; top shelf; class E (seen on reload) |
| Grip bottom | the flat cover face with an R 1 rim; no hole, no trap (unseen; not invented) |
| Stock frame inner faces (seen folded) | same as the outer faces: symmetric moulding, parting witness at mid-plane |
| Butt pad sides/top | smooth rubber; ribs on the rear face only |
| Rail undersides / sight base undersides | flat on the receiver (0.01-0.05 mm joint) |
| Magazine rear face, bottom, inside | plain with the catch notch; the floor plate's locking-tab hole and slide seams; follower top only |
| Bolt top/left (hidden) | plain block with the charging lug and guide grooves; class E |
| Charging slide and guide | plain steel block in a plain moulded guide; class E |
| Muzzle device underside | jam-nut wrench flats only here |

## 6. Inconsistencies between views (and how they are handled)

1. **Forward long slot**: left X 561-602 (ends at the knob), right X 531-598 (longer). The real lever sits ahead of
   its channel; the sheet has the slot ahead of the knob. Handling: RP3 + RP4 (both vents as drawn per side, the real
   channel behind the knob). User check: C-Q1.
2. **Hinge "knuckle" drawn on both sides.** A side-folder has its axle on one side only. Handling: RP2 (right = axle,
   left = latch housing with button).
3. **Front sight.** The side views read as one post on a base; the 3/4 reads as two ears with a gap. Consistent once the
   ears line up with the post in a side view. Both are built.
4. **Selector markings.** A red dot and fine engraved marks in LEFT and 3/4; the RIGHT shows marks only. Not built
   (RP7).
5. **Top rail band width** ~35 mm in TOP vs the 21.2 mm standard. Handling: RP14 (base flange).
6. **Ruler**: 86.6 cm against 69 cm (+26 %). Ignored.
7. **Sight radius** 268 mm vs the real 325 mm: a design change (rail sights), not a conflict. The sheet wins.
8. **Folded stock vs port.** The sheet's top strut height puts the folded strut across the port (Z +5..+17) and the
   upright over the port's front 20 mm. The real pattern fires folded. C-Q3.
9. **Magazine ladder ties** read as 4 levels in LEFT and a slightly different spacing in the 3/4. The LEFT trace is
   the authority.
10. **Butt pad width** (TOP 55-59 mm) vs the frame (29.5 mm). Plausible (a pad wider than the frame). Built as drawn.
11. **Selector hub** reads ~20 mm in the side views; the real teardrop hub is ~16-18 mm. The sheet wins (silhouette is
    not affected; the hub is a surface part, but it is clearly drawn).
12. **Mass** (real-pattern data, not the sheet): the manual says 2.26 kg without magazine, the line standard 2.5 kg.
    C-Q4.

## 7. Original detail changes for a Fab version (not applied)

1. **Vent pattern:** replace the two oblong lower vents with three stepped, tapered vents (rising toward the rear).
2. **Magwell flank:** a raised chevron reinforcement rib in place of the plain diagonal step panel.
3. **Stock frame:** one long rounded-trapezoid opening with the web reversed (leaning forward), plus a moulded
   thumb-rest notch on the top strut.
4. **Butt pad:** a chevron tread instead of horizontal ribs; an exposed hex-head pad screw at the centre.
5. **Grip panel:** an original hex-cell stipple with a moulded thumb ledge above it on both sides.
6. **Muzzle device:** a 4-port compensator (two top ports, two side ports, closed bottom) instead of the 6-slot cage.
7. **Magazine:** one offset vertical rib plus three short horizontal grip ribs instead of the ladder; a floor plate
   with a finger-pull ledge.
8. **Charging knob:** a mushroom knob with three flats instead of the ball.
9. **Selector:** a squared paddle tip with a scalloped thumb face.
10. **Rear sight:** a triangular protective frame around the aperture instead of the rectangular leaf.

Any five of these (vents, stock, grip, muzzle, magazine) move the read clearly away from the real pattern while
keeping the "boxy polymer SMG" feel.

## 8. Notes for the build plan

- **First-person priority** (class A/B): the rear sight leaf and aperture, front ears/post, top rail, charging knob and
  channel, selector (left), the grip top and web, the stock top strut and hinge/latch, the receiver top edges.
- **Form stage must include the internals** the moving parts touch: bolt rails and travel space, the charging slide
  guide and the bolt's charging lug, the magwell walls/shelf/catch window, the paddle pivot, the hinge knuckles and
  axle, the latch housing and its receiver notch, the port catch hook, and the sight leaf pins/detents.
- **Early realism review in the rough look** per part group (AR-01 lesson). Give the judges the real references
  in `scratch/realref/craft/` beside the renders. The tells to watch on a polymer gun are uniform sheen (needs the
  polish/whitening split), missing draft and parting lines, metal-looking polymer, and plastic-looking steel (the
  phosphate must read darker and drier than the polymer, with bright bare edges).
- **Gates added by this study:** catch engagement (stock folded) >= 1.0 mm; folded length 450 +-15 mm; selector sweep
  clearance >= 0.10 mm; charging-lever sweep (translate + lock rotation) clear of the channel by 0.15-0.40 mm; the bolt
  thumb recess visible in the port in the rest pose (render check).

## 9. Open questions for the user (each has a default the build follows)

| # | Question | Default |
|---|---|---|
| C-Q1 | The sheet puts the long slot ahead of the knob on both sides; the real lever sits at the front of a channel behind it. Keep the knob where drawn with a real channel cut behind it (75 mm), and the drawn slots as vents? (The alternative moves the knob ~35 mm forward to the slot's front, costing TOP/3/4 silhouette.) | keep the knob as drawn; channel behind; slots as vents |
| C-Q2 | Selector: paint the hub's index groove white (the sheet shows a light line), or leave it unpainted? (No dots or pictograms either way.) | unpainted groove |
| C-Q3 | Folded stock crosses the port on the sheet's proportions (the real one fires folded). Accept as drawn (folded = carry/no-fire in game), or raise the top strut to clear the port (changes the side silhouette)? | accept as drawn |
| C-Q4 | Physics mass: line standard 2.5 kg or the manual's 2.26 kg (without magazine)? | 2.5 kg (line standard) |
