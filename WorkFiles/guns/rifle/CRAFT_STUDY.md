# Assault Rifle AR-01: craft study (2026-10-04)

Role: craft study. What every part is in 3D, how to build it procedurally, and how it should look, read from the one
reference sheet `References/Guns/Rifle/rifle_sheetAB.webp` (1536x1024, AI-generated with ChatGPT). Companion data:
`craft_parts.json` (one record per part plus materials, stations, inconsistencies, unseen surfaces and IP options).

Asset names: `SM_AR01` (rifle), `SM_AR01_Mag` (separate magazine for the reload). Study notes may name the real
pattern (stamped-receiver 7.62x39 "AKM" family) for reference only; nothing buyer-facing uses it.

## 0. Crops used (all in `WorkFiles/guns/rifle/scratch/`, not committed)

| Crop | Shows |
|---|---|
| `sheet_full.png` | whole sheet as PNG |
| `p_left.png`, `p_right.png`, `p_top.png`, `p_34.png` | the four big panels |
| `c1_receiver_right.png` … `c7_buttplate.png` (+ `z_c*` 3x upscales) | the seven close-ups |
| `z_L_receiver.png`, `z_R_receiver.png`, `z_Q_receiver.png` | receiver, both sides + 3/4 (4x) |
| `z_L_front.png`, `z_R_front.png`, `z_Q_front.png`, `z_T_front.png` | handguards, gas system, front sight, brake |
| `z_L_stock.png`, `z_R_stock.png`, `z_T_stock.png` | stock both sides + top |
| `z_L_rearsight_ch.png`, `z_R_rearsight_ch.png` | rear sight block and lever, 8x |
| `z_T_receiver.png` | dust cover, rear sight leaf from above |
| `g_left_a.png`, `g_left_b.png`, `g_left_mid.png` | LEFT view with a sheet-pixel grid (coordinates below come from these) |
| `mask_left.png`, `mask_right.png`, `mask_top.png` | threshold silhouettes |

## 1. Scale and stations

The ruler is wrong (it reads the gun as ~97 cm). LEFT view silhouette runs x = 24 to 746 sheet px (722 px). Scaled to
880 mm overall: **1.219 mm per sheet px**. Bore axis in the LEFT view sits at sheet y ≈ 96.7. The TOP view is the same
scale within 1 % (716 px). Positions below: X = mm forward of the butt face along the bore, Z = mm above (+) or below
(−) the bore axis. These are craft-level readings (±3 px ≈ ±4 mm); the measurement stage should refine them by tracing.

| Station | X (mm) | Z (mm) | Note |
|---|---|---|---|
| Butt face / butt plate band | 0 – 11 | +2 (heel) to −108 (toe) | butt height ≈ 110 |
| Rear sling swivel | ≈ 72 | under the bottom line | |
| Comb nose (step down to wrist) | ≈ 156 | +9 → +1 | step ≈ 7 mm, concave |
| Stock top tang screw (top view) | ≈ 219 | top of wrist | |
| Rear tang block (steel) | 227 – 240 | | |
| Receiver body | 240 – 483 | +33 (dust cover crown) to −32 (bottom) | height 66 |
| Dust cover | 244 – 458 | crown +33, skirt edge ≈ +4 | |
| Selector pivot | ≈ 283 | ≈ −8 | lever reaches X ≈ 357 |
| Ejection port opening | ≈ 345 – 458 | ≈ +4 to −4 | carrier fills front 2/3 |
| Mag-well side dimple centre | ≈ 397 | ≈ −18 | oval ≈ 18 × 11 |
| Pistol grip top (rear → front) | 246 – 299 | −35 | bottom at Z ≈ −130 |
| Trigger guard | 301 – 353 | bottom −67 | |
| Mag catch paddle | 353 – 367 | tip −70 | |
| Magazine top (rear → front) | 372 – 429 | −32 | floor plate rear (449, −181), front (494, −137) |
| Rear sight block | 450 – 523 | top +37, leaf rear +48 | |
| Upper handguard (+ rear cap 518–528) | 528 – 644 | +41 to +14 | |
| Lower handguard | 485 – 644 | +12 to −30 (rear) / −20 (front) | |
| Front ferrules (both handguards) | 641 – 648 | | |
| Exposed gas tube | 648 – 687 | axis ≈ +24, Ø ≈ 16 | vent slots |
| Gas block | 687 – 736 | | 45° sweep down to barrel |
| Cleaning rod | 647 – 836 | axis ≈ −11, Ø ≈ 5 | |
| Front sight block collar | 808 – 840 | ears top +49 | |
| Muzzle brake | 840 – 880 | Ø ≈ 19–22 | |

Sanity check against the real pattern (~880 mm, 415 mm barrel): barrel visible from the receiver face (483) to the
brake (840) = 357 mm, plus ~50–60 mm inside the trunnion ≈ 410–415 mm. Receiver 243 mm + tang, grip ~95 mm tall,
magazine ~240 mm along its curve: all within a few percent of the real pattern, so the sheet's proportions can be
trusted and scaled uniformly.

## 2. Part-by-part construction

Conventions for the builder: steel bevels 0.3–0.6 mm (crisp, real geometry, weighted normals), stamped-sheet edges
0.4 mm; wood edges rounded 1.5–3 mm; all forms real geometry. Parts that animate are separate objects with clean pivots
(magazine always; selector, trigger, mag catch, charging handle + carrier optional, see open questions).

### 2.1 Receiver (stamped sheet steel) – panels LEFT, RIGHT, 3/4, c1, c2, c6

- **Body**: a U-channel, flat vertical side walls, flat bottom, open top closed by the dust cover. Outer width: the top
  view reads ~38 mm across the dust cover (shading inflates it; the real pattern is ~33–35 mm). Side wall visible from
  the dust cover skirt (Z ≈ +4) to the bottom (Z ≈ −32): 36 mm. Bottom corners: small radius (~1.5 mm) with a thin
  ledge line where the bottom plate meets the sides (seen in c1 as a lighter lip).
- **Wall thickness**: 1.0 mm sheet. Model the receiver as a solid block with the outer form, but give the openings a
  real 1.0 mm wall reveal: ejection port, magazine well, and the rear where the tang block enters. Never show a
  zero-thickness edge.
- **Rear**: a short steel tang/trunnion block (X 227–240) slightly taller than the stock wrist, into which the stock
  seats; vertical rear face, two rivets on its side region.
- **Front**: the front trunnion region under the rear sight block (X ≈ 450–483) carries a 3-rivet cluster (two high,
  one low) and ends in a thin steel cup (the lower handguard rear retainer, X ≈ 483–487) slightly larger than the
  handguard section.
- **Mag-well side dimple**: a shallow pressed oval (≈ 18 × 11 mm, ~1 mm deep, soft 1 mm fillet edges) above the
  magazine well on the side, centre X ≈ 397, Z ≈ −18. Seen on both sides (LEFT, RIGHT, 3/4, c2). The RIGHT view alone
  also shows a longer horizontal pressed groove ahead of it (see inconsistencies).
- **Rivets**: domed heads ~4 mm Ø, ~1 mm proud, bright on the crown. As seen per side (LEFT view grid): rear group 2
  (one above-behind the selector pivot, one low near the rear), centre-low 2 (above the trigger guard ends), mag-well 2
  (flanking the dimple), front trunnion 3 (two high, one low) — about 9 per side; the RIGHT view shows a similar 8–10.
  Exact positions to be traced by the measure stage from `g_left_mid.png`.
- **Magazine well**: rectangular opening in the bottom between X ≈ 372 and 429, matched to the magazine section
  (≈ 29 mm wide), with the front lug recess at the front edge and the catch notch at the rear; interior dark.

### 2.2 Dust cover – TOP, c2, LEFT, RIGHT, c1

- Stamped sheet cover: a **smooth** semicircular-topped crown (radius ≈ half the width) with straight vertical skirts
  that overlap the receiver side walls by ~10 mm; total height ≈ 29 mm (Z +33 to +4). **No transverse ribs** in any
  panel (unlike the real stamped pattern) – match the sheet, keep it smooth. A subtle shoulder line runs lengthwise
  where crown meets skirt (c2, z_T_receiver).
- Rear end: squared end with a ~45° chamfer at the top rear corner (~8 mm), and a rectangular hole through which the
  recoil-spring-guide button protrudes (top view rear; c1 draws it loop-like, see inconsistencies). Model the button as
  a small rectangular tab ~8 × 6 mm with a rounded top, 3 mm proud.
- Front end: tucks under the rear face of the rear sight block (the block's rear has a step/groove that receives it).
- Skirt bottom edge: a crisp 1 mm stamped edge with a visible shadow gap to the receiver side – strong edge wear here.

### 2.3 Ejection port, bolt carrier, charging handle – LEFT/RIGHT (both, see inconsistencies), c1, 3/4, TOP

- Port: a horizontal opening in the side wall just under the dust cover skirt, X ≈ 345–458, ~8 mm tall, 1 mm wall
  reveal, dark interior.
- Carrier: a flat steel block visible in the forward two-thirds of the port, its face ~2 mm behind the wall, with a
  lengthwise highlight (c1, 3/4).
- **Charging handle as drawn**: a short rectangular tab (~20 × 10 mm, ~9 mm proud of the wall, flat-topped, rounded
  outer corners) at the front end of the port, just behind the rear sight block (c1, c2, 3/4, and the TOP view tab on
  the right side). The sheet does **not** show the classic round knob; build the tab as drawn.

### 2.4 Selector lever – RIGHT, c1 (and mirrored in LEFT/3/4/c2)

- Pivot at the rear (X ≈ 283, Z ≈ −8): a domed round boss ~12 mm Ø, 3 mm proud, with a central pin face.
- Lever: a flat stamped plate ~3 mm thick standing ~1.5 mm off the wall, ~74 mm long, tapering from ~14 mm deep at the
  pivot to ~8 mm, with a **pressed stiffening ridge** running its length (c1). The front end steps up and bends outward
  into a finger tab (~12 mm long, bent out ~25°) that sits just under the port's lower edge; a small pin/dimple at the
  tab (c1). Upper edge near the front shows 3–4 small notches (3/4 view) – low confidence, treat as a plain edge or
  subtle notches.
- Detents: c1/z_R show small stamped marks under the lever tip. In the real pattern those are the selector markings
  (letters): **omit them** (no markings rule). Keep two plain shallow detent dimples at most.
- Pose: the sheet shows the lever in the up (safe) position, parallel to the receiver's long axis, angled ~8° up at the
  front.

### 2.5 Rear sight block, leaf and slider – c2, LEFT, RIGHT, TOP

- Block: a steel block on top of the front trunnion, X 450–523, the width of the receiver plus ~2 mm, top at Z ≈ +37,
  front face vertical, rear upper part stepping down to the dust cover crown with a groove that seats the cover's front
  edge. Its top carries the leaf's curved ramps on both sides (the real pattern's cam surfaces), modelled as two low
  curved rails.
- Leaf: a flat bar hinged at the front of the block, lying rearward along the top, ~45 mm long, ~12 mm wide, with a
  raised centre strip and **graduation ticks** (the sheet's glyphs read like numerals/text – model plain ticks or
  nothing, no numerals). Rear end: a tall notch plate (Z ≈ +48) with a square-bottomed U-notch.
- Slider: a box riding on the leaf with two spring catches on its sides (c2, the two "ears").
- Retainer lever: the LEFT view shows a ~45° flat arm on the side of the block (pivot top-front, rounded end with a
  hole, ~22 mm long); the RIGHT view shows only a round boss at the same spot. Real pattern: lever on the right.

### 2.6 Trigger, trigger guard, mag catch – c1, c6, LEFT/RIGHT

- Trigger: curved stamped blade ~6 mm wide, hooked forward-concave, ~35 mm visible below the receiver, pivot hidden.
- Guard: a steel strap ~10 mm wide × 3 mm thick, a flat-bottomed rectangle with a large rounded rear corner (R ≈ 8 mm)
  and a near-square front corner; rear end riveted to the receiver bottom just ahead of the grip, front end rising into
  the mag-catch housing.
- Mag catch: a flat paddle ~10 mm wide in front of the guard, pinned at mid-height (round pin head visible, c1), its
  lower tip protruding ~5 mm below the guard bottom as a short tab; top merges into a small housing block under the
  receiver at the magazine's rear.

### 2.7 Pistol grip – c6, c1, LEFT, RIGHT, 3/4

- Profile: top ≈ 54 mm fore–aft, bottom ≈ 41 mm; height ≈ 95 mm below the receiver. Rear edge raked ~13°, front edge
  ~22° (the grip tapers downward). Bottom edge slants so the **front-bottom corner is the lowest point**, a small
  rounded toe/lip; the rear-bottom heel is a rounded corner with a slight rearward bulge.
- Section: rounded oblong, ~30 mm wide (unseen, real-pattern value), flatter sides where the checkering sits, front and
  back straps rounded R ≈ 8–10 mm. Top face flat against the receiver bottom with a slight steel-to-wood gap line.
- **Checkering patch** (both sides): a tall quadrilateral following the grip's long axis, raked top edge (higher at the
  rear), rounded corners R ≈ 3 mm, starting ~25 % down from the top and ending ~12 % above the bottom, inset ~4 mm from
  the front strap, ~40 % of the grip's fore–aft width (c6). Diamond cells, elongated along the grip axis (~60°/120°
  hatch), pitch ~1.2–1.5 mm.
  Construction: the patch **boundary is real geometry** (a 0.6 mm recess with a crisp 0.3 mm border bevel). The diamond
  field inside is a **crisp tiled normal map + AO/cavity** baked from a real modelled pyramid tile (not a height-field
  relief on the silhouette – it never touches the silhouette, so this is safe). For a first-person hero LOD0 the
  pyramids can be real geometry (~18 × 50 cells per side ≈ 900 pyramids, ~3.6k tris per side) if the budget allows;
  decide at build time.
  Note: c6 places the patch in the front half; c1 (mirrored right) in the rear half – use c6 (the true left
  close-up) and mirror for the right.

### 2.8 Buttstock – LEFT, RIGHT, TOP, 3/4

- Profile (LEFT view): bottom line straight from the toe (0, −108) rising ~18.6° to the receiver tang (≈ 230, −35);
  top line: comb nearly level from the heel (+2) rising slightly to the comb nose at X ≈ 156 (+9), then a short concave
  step down (~7 mm) to the wrist, wrist top rising gently into the tang. Butt height 110 mm.
- Section: rounded rectangle, width ≈ 38 mm at the butt tapering to ≈ 34 mm at the wrist (top view), edges R ≈ 6–8 mm,
  sides very slightly convex. Solid wood (no laminate lines visible anywhere).
- Right side of the wrist (RIGHT view only): a pointed, rearward-V shaped inlet outline (~25 × 20 mm) holding two small
  dark screw/pin heads. Top of the wrist (TOP view): one round tang screw head at X ≈ 219.
- Rear sling swivel: a small steel loop (~12 mm) on a short base plate on the bottom line at X ≈ 72.

### 2.9 Butt plate – c7, LEFT, RIGHT, TOP

- Steel plate covering the whole butt end (TOP view shows the dark cap as wide as the stock), ~110 × 38 mm, stadium
  outline following the stock section, face very slightly convex, with a wraparound skirt ~8 mm deep (the side views
  show a 9–11 mm dark band). Rim edge rounded ~1 mm.
- Two screws on the centre line near top and bottom (c7), countersunk, slotted. c7 draws the slot as an "X"; the
  resolution cannot tell slot vs cross – use a single straight slot (period-plausible) unless the user prefers cross.
- **No trap door is visible** – keep the face plain.

### 2.10 Lower handguard – LEFT, RIGHT, 3/4, TOP

- Wood, X 485–644 (159 mm). Height 42 mm at the rear tapering to 34 mm at the front; top edge straight at Z ≈ +12;
  bottom edge a shallow convex belly. Section: U-shaped (rounded bottom, slightly swelling sides), outer width ≈ 45 mm
  rear, ≈ 40 mm front; hollow inside (channel for the barrel) – the hollow is only visible at the ends.
- **Finger relief**: two dark elongated recesses per side along the top edge (at ~10–30 % and ~45–65 % of the length),
  read as shallow scallops/finger grooves cut into the top edge (~25–35 mm long, ~5 mm deep). Consistent in LEFT,
  RIGHT and 3/4.
- Rear: sits in the receiver's steel cup. Front: a steel ferrule cup (X 641–648) slightly proud of the wood, with a
  rolled rim.

### 2.11 Upper handguard and gas tube – LEFT, RIGHT, 3/4, TOP

- Upper handguard: wood shell over the gas tube, X 528–644, Z +14 to +41 (27 mm tall), section a half-round top with
  short vertical sides (~30 mm wide), small gap line to the lower handguard. Rear: steel cap ring (X 518–528) entering
  the rear sight block; front: steel ring (X 641–648).
- Gas tube: steel tube Ø ≈ 16 mm, axis Z ≈ +24, exposed X 648–687. Near its front it shows short **vent slots**: the
  TOP view suggests 2 rows of ~3 short oval slots, the side views one blurred dark slot zone. Model 3 short oval slots
  (~6 × 3 mm) per side, low confidence.

### 2.12 Gas block, barrel, cleaning rod – LEFT, RIGHT, 3/4, TOP, c3

- Gas block (X 687–736): a short rectangular collar receiving the gas tube's front end, sweeping down at ~45° (as a
  flat-sided arm ~14 mm thick) to a barrel collar ~20 mm Ø; a round pin boss on the arm's side (3/4); a small lug under
  the barrel collar (the rod guide / bayonet lug, ~10 × 8 mm).
- Barrel: plain steel, Ø ≈ 15 mm visible (side view reads 12, top view 17 – use 15), essentially straight with a very
  slight taper; visible X 648–687 and 736–808. Bore Ø 7.6 mm, ~30 mm deep dark bore at the muzzle.
- Cleaning rod: Ø ≈ 5 mm, Z ≈ −11, from under the lower handguard ferrule to the front sight block lug, passing
  through the gas block lug; its front end has a flat T-head seated in the FSB lug (c3).

### 2.13 Front sight block – c3, LEFT, RIGHT, 3/4, TOP

- Collar: a cylinder Ø ≈ 22 mm, X 808–840, with a cross pin (round head ~4 mm) on the side and a small detent plunger
  at its top front (c3) that retains the brake.
- Ears: two thin steel plates (~2.5 mm) standing on the collar's left and right edges (TOP view: they protrude
  slightly beyond the collar width), rising to Z ≈ +49. Each ear: vertical front edge, rear edge raked ~20°, flat top
  with rounded corners, a **triangular lightening window** in its lower half and a small round hole near the top (c3).
- Between the ears: a round windage drum (disc ~8 mm Ø, seen side-on as a circle at mid-height) carrying a thin
  vertical post (~2 mm) slightly lower than the ear tops.
- Under the collar: a lug that holds the cleaning rod's head.

### 2.14 Slant muzzle brake – c3, LEFT, RIGHT, 3/4, TOP

- A cylinder Ø ≈ 20–22 mm, X 840–880, screwed onto the barrel (thin seam ring at the FSB face).
- The front is cut by a single slanted plane, ~35–40° from vertical, removing the **top** front and leaving the
  **lower lip longer** (side views: top line ends first, the slope runs down-forward; TOP view: the cut face reads as an
  oval opening from above). The cut exposes the bore as an elongated oval with a rounded, worn rim (c3).
- Inside the cut, a second smaller scalloped relief is visible on one side (c3) – a shallow side relief, low
  confidence; keep it as a soft scallop on the cut face.

### 2.15 Magazine (separate mesh SM_AR01_Mag) – c4, c5, LEFT, RIGHT, 3/4

- Body: two stamped steel halves welded at front and rear spines. Section rectangular ~29 mm wide with rounded spine
  edges; depth 57 mm at the top growing to ~62 mm at the floor plate.
- Curve: front and rear edges are concentric arcs about a centre ~580 mm forward of the butt face and ~10 mm below the
  bore (LEFT view fit): rear (outer) radius ≈ 210 mm, front (inner) ≈ 150 mm, spanning ~46°. The magazine bends
  forward (bottom ahead of the top).
- **Ribs** (each side): 4 raised pressed ribs running parallel to the curve in the rear/middle zone, each ~2.5 mm wide,
  ~1 mm proud, round-crowned, ending in rounded tips ~25 mm below the top and ~15 mm above the floor plate; plus a
  narrower rib along the front edge. Rib crests are worn bright in every panel (the strongest visual cue).
- Top: a flat reinforcing plate (smooth panel, ~45 × 30 mm) on each side above the ribs (c4); feed lips folded inward
  at the top (c5 front view), a dark follower plate inside.
- Lugs: front locking lug at the top front (a hooked tab, c4, c5); rear catch lug at the top rear (a small block).
- Front spine (c5): a centre channel with two raised lengthwise lines running the full curve.
- Floor plate: a separate flat plate sliding in rails at the bottom, slightly proud all round (~1.5 mm lip), with a
  rounded front edge (c4, c5, 3/4).

## 3. Materials and wear

Sampled from the sheet (sRGB, background grey = 126, close to an 18 % card, so values read as albedo-like).

| Material | Base colour (sRGB) | Metallic | Roughness | Notes |
|---|---|---|---|---|
| Blued steel (receiver, cover, sight, barrel, FSB, brake, guard) | #3C3C3E (60,60,62), ±10 % variation | 1.0 | 0.45 (flats 0.40–0.55; dust cover crown 0.35) | neutral dark grey, no visible blue cast, satin sheen |
| Magazine steel | #333334 | 1.0 | 0.50 | slightly darker and rougher |
| Butt plate | #48484A | 1.0 | 0.50 | greyer, heavily scratched |
| Bare steel (edge wear, rib crests, rivet crowns) | #A09E9A (160,158,154) | 1.0 | 0.25–0.32 | bright silver-grey |
| Grime in recesses | #2A2826 | 0.0 | 0.80 | around rivets, sight block joints, checkering cells |
| Wood (stock, grip, handguards) | #6B3C27 (107,60,39) | 0.0 | 0.50 (0.42–0.60) | reddish-brown stain, oil/shellac sheen |
| Wood grain dark streaks | #482C1B | 0.0 | 0.55 | long streaks |
| Wood light figure / highlights | #965F46 | 0.0 | 0.45 | |
| Wood handling wear | #87573F, desaturated | 0.0 | 0.62 | worn finish = lighter and rougher |
| Checkering cell interiors | #4E2E1E | 0.0 | 0.70 | |

Parkerized option: if the user wants a matte phosphate look instead of blued, use base #3A3A3A, metallic 0.3,
roughness 0.70. The sheet reads as blued/satin (soft specular streaks on the cover and barrel), so blued is the match.

**Grain direction**: along the stock length (parallel to the stock axis, straight, with long dark streaks and a few
flecks), along the bore on both handguards, along the grip's raked long axis on the grip. Solid wood, no laminate.

**Where the wear sits (as seen)**:
- Steel edges: dust cover skirt edge and rear chamfer (strongest), receiver bottom edge and front/rear corners, rear
  sight block corners, leaf slider, FSB ear edges and collar rims, brake rim and slant edge, gas block corners,
  ferrule rims, trigger guard edges, selector edges and tab, rivet crowns (bright dots), magazine rib crests, spine
  edges and floor plate rim.
- Steel flats: dense fine random scratches and light scuffs on the receiver sides (c1, c6 show many short light
  scratches), a long lengthwise highlight/wear band along the dust cover crown, butt plate face covered in bright
  scratches (c7).
- Wood: rounded-edge wear on handguard ends, grip straps and toe, stock comb and toe/heel; a few dents on the stock
  sides (a round ding on the left at ~X 100, a C-shaped mark on the right at ~X 30–40), scratches on the upper grip
  (c6), darker grime in the checkering.
- No rust, no cracks, no repairs shown.

## 4. Inconsistencies in the sheet

1. **Controls on both sides.** LEFT view, 3/4 view and close-ups c1/c2 all show the selector lever, ejection port +
   carrier and the charging tab on the side that faces the viewer with the muzzle to the RIGHT (the gun's left), while
   the RIGHT view also shows a selector. Physically there is one set, on the right (the prompt says so; the TOP view's
   charging tab and selector boss are on the right side). The AI mirrored right-side features onto the left.
2. **3/4 "FRONT RIGHT" shows the left side orientation** (stock left, muzzle right toward the viewer): mislabelled or
   mirrored.
3. **c1 "RECEIVER AND SELECTOR (RIGHT)" is drawn muzzle-right**, i.e. a mirrored right side.
4. **c4 "MAGAZINE (LEFT)" curves the wrong way** relative to the LEFT view (bottom swings left/back): mirrored, shape
   is otherwise consistent.
5. **Rear sight retainer lever**: LEFT view shows a 45° arm on the block's side; RIGHT view shows only a round boss.
6. **Extra pressed groove**: RIGHT view shows a long horizontal pressed groove ahead of the oval mag-well dimple;
   LEFT view and c2 show only the oval.
7. **TOP view artifact**: a ribbed plate sticks out of the gun's left side over the magazine well (looks like the
   magazine seen sideways) – impossible in a top orthographic; ignore.
8. **Barrel diameter** reads ~12 mm in the side views and ~17 mm in the top view.
9. **Ruler** reads ~97 cm for an ~88 cm gun (known; we scale ourselves).
10. **Rear sight leaf graduations and a mark on the leaf base read like text/numerals** (c2) – the no-markings rule
    wins; plain ticks.
11. **Selector marks** under the lever tip (c1, z_R) correspond to stamped letters on the real pattern – omit.
12. **Recoil-spring-guide button** looks like a loop/ring in c1 but a small squared tab in the TOP view.
13. **Checkering patch position**: front half of the grip in c6, rear half in c1 (mirrored right).
14. **Butt plate width**: c7 shows wood beyond the plate on both sides (perspective); TOP view shows the plate as wide
    as the stock. Use the TOP view.
15. **Butt plate screw heads** drawn as X/cross at low resolution.

Recommended resolution (orchestrator/user decides, see open questions): build the mechanically real arrangement
(selector, port, carrier, charging tab and retainer lever on the RIGHT; left side plain receiver wall with rivets and
the oval dimple) and judge the left side against a horizontally mirrored LEFT view only for silhouette and furniture.
The literal alternative (controls on both sides) matches the LEFT panel but is a mechanically impossible gun.

## 5. Unseen surfaces and their plain treatment

| Surface | Treatment |
|---|---|
| Receiver bottom between grip and mag well, and ahead of the well | flat steel bottom plate, two trigger-guard rivets, same finish |
| Receiver left side (if option A) | plain wall: rivet pattern mirrored from the right, oval dimple, no port, no lever |
| Inside the ejection port | carrier face 2 mm in, dark cavity behind, 1 mm wall reveal |
| Inside the receiver | never visible (cover closed); no interior |
| Magazine well interior | 25–30 mm deep dark cavity matched to the magazine top, front lug recess, rear catch notch |
| Barrel bore and brake interior | 7.6 mm bore, ~30 mm deep, dark; brake inner wall plain |
| Magazine internals | feed lips + plain dark follower; no cartridges (optional loaded variant if the game wants it) |
| Magazine rear spine | same as the front spine: channel with two raised lines |
| Magazine top face (inside the well) | top of the lips and lugs only, plain |
| Pistol grip right side | checkering patch mirrored from c6 |
| Pistol grip bottom | plain flat wood end, small chamfer, no cap/screw (none shown) |
| Stock left side wrist | plain (the V inlet is shown only on the right) |
| Stock and handguard insides / channels | only visible at the ends; plain dark wood channel |
| Lower handguard underside | smooth continuation of the belly |
| Butt plate | plain, no trap |
| Underside of the rear sight block, gas block, FSB | plain steel continuation of the visible forms |

## 6. IP: original detail changes for a Fab version (NOT applied; the user decides)

1. **Muzzle device**: replace the slant brake with an original faceted (hex-flat) brake with two angled side ports.
2. **Dust cover**: an original pattern, e.g. two lengthwise stiffening ribs and a stepped rear end, instead of the
   smooth crown.
3. **Lower handguard**: a single long palm swell with three shallow horizontal flutes instead of the two finger
   scallops; a flat-sided front band with one screw instead of the round ferrule.
4. **Grip texture**: a horizontal-groove or hex-stipple panel instead of diamond checkering, plus a subtle finger swell.
5. **Buttstock**: a straight comb without the nose step and an inset oval cheek panel; sling swivel moved to the side.
6. **Front sight**: a closed round hood, or ears with round windows instead of triangular ones.
7. **Gas block**: an angular block with a vertical front face instead of the 45° sweep; round vent holes in a 2-2
   pattern on the gas tube.
8. **Receiver**: an original rivet layout (fewer rivets) and a long pressed reinforcement rib in place of the oval
   dimple.
9. **Selector**: a shorter, wider lever with a hooked finger tab.
10. **Magazine**: two wide ribs plus one cross-rib near the top, and a floor plate with an original stepped lip.

Any four or five of these together (brake, handguard, grip texture, stock, dust cover) would make the silhouette and
the close-up read as the user's own design while keeping the "classic wooden rifle" feel.

## 7. Notes for the build plan

- First-person view puts the dust cover crown, rear sight leaf/slider, selector and upper handguard closest to the
  camera: spend detail and texel density there.
- Tracing the LEFT view (stock, grip, handguards, magazine, FSB, brake) and the RIGHT view (selector, retainer side)
  is the 2D outline authority; sections come from the TOP view, c5 and real-pattern values.
- Keep the magazine a separate mesh with its pivot at the front lug (rock-in reload).
