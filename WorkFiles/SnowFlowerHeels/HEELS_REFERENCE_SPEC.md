# Snow Flower heels: reference metrology

2026-09-27, role "reference metrology". Source: `References/SnowFlowerHeels/snowflowerheels_reference.png`
(1254 x 1254, sha256 `77916fb82645386ce36792a38da093a914270897eef104560cab3b45d71402dc`; the `_OLD_superseded` file was
not used). Every number below is in `heels_spec.json` (same folder). Traced outlines are in `heels_spec.json -> traces`
(reference pixels, x right, y down, origin top-left) and in `Scripts/SnowFlowerHeels/metro_traces.py`.

Scripts (Blender's bundled python, numpy only, no bpy):
`Scripts/SnowFlowerHeels/metro_png.py` (PNG IO), `metro_common.py` (morphology, contour trace), `metro_crop.py`
(zoom crops with a labelled grid, overlays), `metro_traces.py` (the hand traces), `metro_overlay.py`,
`metro_measure.py` (materials, camera, proportions, crops, registration), `metro_write_spec.py` (builds the JSON).

---

## 0. The short version for the builders

1. **View A (the front, left shoe in the image) is the design authority.** It is 1.18x larger, sharper and carries the
   most ornament. View B (the rear, right shoe) agrees on shape, heel, strap, buckle and toe, but has less ornament on
   the vamp (no big vamp blossom). Where they disagree, follow A. Use B for geometry cross-checks only.
2. **Both views show the same side of the shoe: the wearer's RIGHT side.** It is not a mirrored pair. The recommended
   reading is a **right shoe seen from its outer side** (buckle on the outside of the ankle). The left shoe is its
   exact mirror. See section 2.
3. **Camera for compare renders:** orthographic or a long lens, elevation **22 deg** above the ground (range 18 to 26),
   camera on the shoe's right side, **48 deg from the toe direction** for view A (44 deg for view B), white ground,
   soft studio light. See section 3.
4. **Most robust proportions are the vertical ones** (section 4.2). Two items matter most for the fit:
   - heel: seat about **0.32 x the top-lift-to-toe length** above the ground, which is **about 82 mm** for her
     (range 73 to 91). The pose chat's 90 mm (`heel_pose.json`) sits at the top of that range, which is fine.
   - **The back is tall.** The heel counter and its crest spike rise about **1.8 x the stiletto height above the
     seat**. On her that is roughly 150 mm above the seat, or 70 to 110 mm above the ankle joint. The ankle strap
     sits 30 to 60 mm above the ankle joint. **This conflicts with the "nothing above the ankle except the strap"
     skinning rule**, so it is an open decision (section 10).
5. **Registered crops for compares** are in `ref/` (section 5). Match a render to them with the similarity
   transform built from the landmarks. Do not trust pixel-level agreement with view B, because its yaw differs from
   A by about 4.5 deg.

---

## 1. The design (what is actually shown)

The shoe is a black pointed-toe stiletto pump:

- **Half-d'Orsay cut.** The visible side is cut away down to the sole at the waist. The far side is closed, and
  its topline falls smoothly from a very high back collar to the throat.
- **Tall armoured heel counter.** It carries layered silver leaf plates, a C-shaped silver branch around a bulging
  crackle-leather medallion, and a tall pointed **crest spike** that stands above the collar.
- **Ankle strap.** It forms a closed loop around the ankle. It folds (U-turn) at the front of the ankle and returns
  on the visible side to a **blossom buckle**: a pearl five-petal blossom on an open pointed-hex silver frame, with
  open diamond frames on each side. A pyramidal diamond stud sits on the strap.
- **Stiletto.** A black stiletto wrapped at its back by the main silver branch band. The band carries one thorn
  and one elongated diamond boss, and ends at a black top-lift.
- **Topline piping.** Silver piping runs along the vamp topline of the open side into the toe plate.
- **Vamp vine.** On the vamp side, a silver vine forms a pointed-oval frame. The frame holds the largest blossom and
  seven buds, with a lower vine running down to the toe frame.
- **Toe plate.** An upright pointed leaf spike stands at the throat, with a pearl blossom on it. A long rear arm
  points back along the piping, and a keystone diamond sits under the blossom. Two silver rails run from the
  keystone to the silver-capped toe tip and frame the **glossy black toe cap**.
- **Insole.** A dark insole (sock lining) with a lighter centre band. It carries a printed **kite-shaped emblem**
  at the heel seat and a printed blossom branch with two blossoms and about 11 buds.
- **Leather.** The vamp leather has a fine grain plus a **tone-on-tone floral emboss** (dark blossoms and branches
  on black, visible in both views). The counter medallion has a coarser crackle grain.

Counts (view A): metal-set pearl blossoms **4** (buckle, toe, vamp, counter back). Printed insole blossoms **2**.
Metal buds **7** on the vamp and 1 in the medallion. Printed insole buds **about 11**. Leaf plates on the counter:
crest spike + 2 sickle lames + a leaf cluster around the counter blossom + 1 spur. Heel ornaments: 1 thorn and 1
diamond boss. Toe plate: apex spike + rear arm + keystone + far rail + near rail, with 2 inward thorns on the far
rail. Vine thorns: 3.

---

## 2. Left vs right

- The toe points toward camera-right, the heel away-left, and the camera looks down about 22 deg. In both views
  the side facing the camera is **the wearer's right side** (checked with a right-handed frame: forward x up =
  right, which points toward the camera).
- Both shoes show the open side, the buckle and the ornament on the side facing the camera. So the image is **two
  views of the same right-side design, not a left/right pair.**
- **Recommendation: the reference is the RIGHT shoe seen from its OUTER (lateral) side.** Ankle-strap buckles sit on
  the outside of the ankle, and showcase shots show the outer side. Build the right shoe as shown. The **left
  shoe is its mirror** across the sagittal plane, so the opening, buckle, counter ornament and vamp vine are all on
  the outer side of both feet.
- Alternative the image cannot rule out: a left shoe seen from its inner side, meaning the opening is on the arch
  side. This is flagged for the user or the Study agent if they prefer that.
- Mirror rules:
  - All silver, the vines, the buckle, the strap run and the opening mirror.
  - Blossoms are 5-fold radial, so only their petal twist flips. Instance one blossom and mirror it.
  - The insole emblem is symmetric about its long axis, which lies on the insole midline, so it is unchanged.
  - The printed insole branch is asymmetric and mirrors with the insole.

---

## 3. Camera estimate (for compare renders)

- **Model: weak perspective.** Verticals (stiletto sides, top-lift edges, strap edges) stay parallel, and there is
  no measurable perspective convergence.
- **Elevation.** The top-lift footprint is a small square-cornered block. Its two visible bottom edges give the
  elevation independently of its aspect ratio: **A 22.4 deg, B 21.3 deg**, so the mean is **21.9 deg**. With
  1-2 px corner error on a 24-32 px edge, the range is 18 to 26 deg.
- **Yaw of the shoe axis** (top-lift front corner to toe tip, both on the ground): **A 41.9 deg** out of the image
  plane toward the camera, **B 46.4 deg**. In other words, the camera sits on the shoe's right side at **48.1 deg
  (A) / 43.6 deg (B) from the toe direction**.
- **Scale.** View A spans 1024 px per unit of top-lift-to-toe length. **B/A = 0.85.**
- **Two-view reconstruction is not possible.** A and B differ by only about 4.5 deg of yaw, which is too little
  parallax: a rigid two-view fit converged to a 10 px rms solution with meaningless depth. So 3D values below
  come from this camera plus stated assumptions, not from triangulation.
- **Compare-render recipe:**
  - Orthographic camera, 22 deg elevation, 48 deg from the toe on the right side. Frame so that the top-lift
    front corner and the toe tip land on A's pixels.
  - Top-lift front corner (107.4, 917.3); toe tip (869, 1172) on a 1254 canvas; 803 px apart.
  - Then fine-tune yaw and elevation by maximising silhouette IoU against `ref/viewA_mask.png` (inside box
    `[0,0,894,1202]`).
  - That silhouette fit is the only accurate 3D check this image allows.

---

## 4. Proportions

Frame per view: origin at the **top-lift front (ground) corner**, axis toward the **toe tip**. "along" = fraction of
that length. "across" is positive below the axis line in the image. Image lengths: **A 803.1 px, B 644.6 px.**
Silhouette bbox: A `[10,8,869,1177]`, B `[551,37,1234,1032]`. Image height / length: A 1.456, B 1.544.

### 4.1 Landmarks (image space)

| Landmark | A xy | A along | B along | A height above ground (image px) |
|---|---|---|---|---|
| toe tip (silver-capped) | 869,1172 | 1.000 | 1.000 | -255 (nearer the camera) |
| top-lift front corner | 107.4,917.3 | 0 | 0 | 0 |
| heel-breast arch apex | 160,628 | -0.052 | -0.085 | 289 |
| heel seat, rear silhouette | 67,600 | -0.173 | - | 317 |
| counter rearmost point (leaf spur) | 10,371 | -0.331 | - | 546 |
| collar top (far panel) | 171,26 | -0.277 | -0.314 | 891 |
| crest spike tip | 118,8 | -0.347 | -0.351 | 909 |
| buckle blossom centre | 201,221 | -0.165 | -0.149 | 696 |
| strap stud | 308,244 | -0.029 | -0.016 | 673 |
| strap fold (front of ankle) | 470,248 | 0.164 | 0.249 | 669 |
| insole emblem top / bottom | 163,405 / 248,535 | -0.137 / 0.015 | -0.082 / 0.077 | 512 / 382 |
| opening front edge, low (counter front band) | 118,560 | -0.129 | - | 357 |
| piping start (open side, at the sole) | 205,745 | 0.047 | - | 172 |
| far-side throat corner | 402,727 | 0.273 | - | 190 |
| toe apex spike tip (throat) | 625,818 | 0.572 | 0.591 | 99 |
| toe blossom centre | 672,913 | 0.665 | 0.689 | 4 |
| toe keystone | 683,963 | 0.698 | - | -46 |
| toe cap rear edge | 690,1000 | 0.721 | - | -83 |
| vamp blossom centre | 475,955 | 0.449 | (absent) | -38 |
| vine-frame rear corner | 268,1006 | 0.225 | - | -89 |
| counter blossom | 72,575 | -0.177 | - | 342 |

"Height above ground (image px)" is image-vertical offset from the top-lift ground corner. Points nearer the
camera than the top-lift (toe, vamp) sit lower in the image, so they come out negative. This is not physical height.

### 4.2 Vertical proportions (the robust ones)

Ratios to the heel-breast arch apex height (A 289 px, B 262 px). They depend on the camera only through small
depth offsets. A and B agree to about 10 %.

| Height | A | B |
|---|---|---|
| top-lift block | 0.081 (23.5 px) | 0.10 (27 px) |
| heel seat at the back | 1.10 | - |
| insole emblem top | 1.77 | 1.39 |
| strap fold (front of ankle) | 2.31 | 2.02 |
| buckle blossom | 2.41 | 2.14 |
| collar top (far panel) | 3.08 | 2.78 |
| crest spike tip | 3.14 | 2.88 |
| toe apex spike tip | 0.34 | 0.19 |

- The crest spike rises about 18 px above the collar top (A).
- The collar top sits about 1.3x higher above the seat than the strap does.
- In short: **tall back, then strap, then heel**, in the ratio of roughly **2.8-3.1 : 2.0-2.4 : 1**.

### 4.3 3D estimates (camera of section 3, midline assumption; units of top-lift-to-toe length L)

| Item | e = 18 deg | **e = 21.9 deg** | e = 26 deg |
|---|---|---|---|
| heel seat (back) height | 0.285 | **0.320** | 0.353 |
| heel-breast arch apex height | 0.305 | **0.343** | 0.379 |
| top-lift height | 0.022 | **0.025** | 0.027 |
| toe apex spike tip (x, z) | 0.68, 0.26 | **0.68, 0.29** | 0.68, 0.32 |
| strap fold (x, z) | 0.48, 0.74 | **0.48, 0.83** | 0.48, 0.92 |
| buckle (z, if on the side, y = 0.12 L) | 0.74 | **0.83** | 0.92 |
| crest spike tip (z, y = 0.12 L) | 0.91 | **1.03** | 1.13 |
| counter rearmost point (x behind the top-lift, z) | -0.13, 0.48 | **-0.13, 0.54** | -0.13, 0.60 |

- The top-lift footprint side is about 0.031 L, a near-square block (edge aspect 1.04).
- The heel back at the seat is about 0.05 L behind the top-lift front corner.

**Example on her** (foot 242.4 mm per `heel_pose.json`). Assume a pointed-toe shoe about 275 mm long, so
L is about 257 mm. The mm scale on view A is about 3.8 px/mm (plus or minus 10 %) for details seen face-on.

| Item | Estimate |
|---|---|
| heel height at the seat | about 82 mm (73 to 91) |
| top-lift | about 6.3 mm tall, 8 x 8 mm |
| stiletto shank (apparent width, includes the silver band) | 43-45 px, about 11 mm; the true shank is about 9-10 mm |
| strap | about 185-215 mm above the ground |
| collar top | about 245-270 mm above the ground |
| throat (apex spike tip) | about 175 mm ahead of the top-lift |
| glossy toe cap | covers the front about 28 % of L |

**Stiletto taper** (A, silhouette row widths incl. the silver band; B in brackets):
- y 647: 75 px (flare into the seat)
- y 677: 64
- y 707: 57
- y 767: 45 [B 43-45 from mid-height down]
- top-lift: 56 px diagonal

So the stiletto is a near-constant shank over its lower 60 % and flares into the seat over the top 40 %. The heel
breast is a smooth concave arch, not a sharp corner.

**Openings (A):**
- The open side runs from the counter's front band (along -0.13 at the low end) down to the sole at the waist.
  It then runs forward to the piping start (along 0.05, about 172 px above ground at the sole line) and rises
  along the piping to the throat (along 0.58).
- The far-side topline falls from the collar (along -0.28, height 891 px) to the far throat corner (along 0.27,
  height 190 px), then to the throat.

---

## 5. Registered crops and compare files (`WorkFiles/SnowFlowerHeels/ref/`)

| File | What it is |
|---|---|
| `viewA_crop.png`, `viewA_mask.png`, `viewA_rgba.png` | View A, box `[0,0,894,1202]` of the reference (24 px pad), RGB, binary silhouette, RGBA with the silhouette as alpha |
| `viewB_crop.png`, `viewB_mask.png`, `viewB_rgba.png` | View B, box `[527,13,1254,1057]` |
| `viewB_registered_to_A_crop.png` / `_mask.png` | B warped into A's crop frame with the best similarity (scale 1.2214, rot -4.26 deg, t (-742.36, 7.56)). B is masked to its own silhouette |
| `silhouette_A_vs_B_registered.png` | Red = A only, blue = B only, grey = both. **IoU 0.81.** The difference is the yaw (B's stiletto sits further left, its counter bulges further back) plus design drift |
| `viewA_traces_overlay.png`, `viewB_traces_overlay.png` | Every trace drawn over its view (cyan silver, magenta pearl, yellow toe cap, green strap, orange other) with a 10 px grid, labelled every 50 px |
| `full_masks.png` | Both silhouettes on the full 1254 canvas (R = A, G = B) |
| `silhouettes.json` | Silhouette outlines (RDP 0.75 px) + bbox + area per view |

**Registration of B to A.** The landmark similarity has rms 29 px and the affine 27 px. That is the yaw parallax
(strap fold -45 px, emblem -57 px), not tracing error.

**Recipe for later compares.** Render with the section 3 camera at 1254 x 1254 and crop with the same box. Snap the
render with a similarity fitted on toe tip + top-lift front corner + buckle blossom centre + toe blossom centre.
Then compare silhouette IoU (mask) and ornament positions (traces).

**Silhouettes.** Method: background flood fill over low-gradient bright pixels, contact-shadow removal under the
sole, and a 3 px closing. Accuracy is 1 px on the sides and 2-3 px along the sole, where the contact shadow touches.

---

## 6. Element-by-element (view A; px and fraction of L_img = 803 px; mm at about 3.8 px/mm)

All outlines are in `heels_spec.json -> traces["A.<name>"]`:
- `outline` = closed polygon
- `centerline` = open polyline with `width_px`
- `point` = centre with `d_px`

`layer` = overlap order (section 7).

### Heel counter (visible side and back)

- **crest_spike** (`outline`, inset `crest_spike_inset`). A tall pointed leaf plate, 189 x 55 px (0.235 L_img),
  about 50 x 14 mm.
  - It is the TOP END of the front branch band.
  - Silver rim about 6-10 px, with a dark recessed lens 146 px long.
  - The tip (118,8) leans back and stands about 18 px above the collar.
- **front_branch_band** (`centerline`, 690 px long, 12-17 px wide, about 3.5-4.5 mm). The main S-curved band.
  - It climbs from the top-lift up the back of the stiletto (x about 95-100).
  - It swings forward at the seat (122,585), runs up the counter's front edge (the edge of the opening, x 118-140)
    and ends in the crest spike.
  - On the stiletto it carries **heel_thorn_1** (points back, at y 708-730) and **heel_diamond** (elongated
    boss, 56 px, at y 797-853).
- **rear_c_band** (`centerline`, 7 px, about 2 mm). A C-shaped branch around the counter back from (95,268) to
  (68,555). It frames the **medallion_leather**: a bulging oval of crackle-grain leather, 77 x 185 px, centre about
  (85,380).
  - **rear_leaf_spur**: a leaf on the C-band that makes the rearmost silhouette point (10,371).
  - **medallion_leaf**: a small silver leaf inside the oval.
  - **medallion_bud**: at (85,447).
- **sickle_plate_1 / sickle_plate_2** (`centerline`, 10-11 px wide, 153 / 113 px long). Layered armour lames
  under the crest spike.
  - sickle_plate_1: knob at (77,125), sweeps down and forward.
  - sickle_plate_2: follows the counter-back silhouette.
- **counter_blossom** (pearl, d 38 px, about 10 mm) at (72,575). It sits where the C-band meets the front band,
  on a cluster of pointed leaves (**counter_low_leaves**, envelope 70 x 120 px).
- **stiletto_outline / toplift**.
  - The stiletto runs from the seat (73..172 at y 600) to the top-lift.
  - Top-lift block: step line at y 894 down to the ground corners (83.6,905.6), (107.4,917.3) and (139.5,907.8).
  - Heel breast: a concave arch from (163,610) down to (139,890).

### Far (closed) side, seen from inside

- **far_panel_topline** (`polyline`). A high collar with a stitched binding about 5 px inside the edge.
  - Top at (171,26).
  - Front edge near x 283 down to the strap roots, then falls through (358,500) to the far throat corner
    (402,727) and the throat (620,815).
  - The inside is black lining leather.

### Ankle strap and buckle

- **strap_near_run** (`outline`). About 41 px across in the image, a true width of roughly 10 mm, with edge
  stitching on both edges. It runs from the buckle to the **strap_fold** (U-turn, outer end x 470-472,
  y 228-277).
- **strap_far_run** (`outline`, about 19 px wide in the image because it is seen edge-on). It emerges from behind
  the far panel's front edge at x about 270-283 and reaches the fold.
- **buckle_blossom**: pearl, d 51 px (about 13 mm), centre (201,221), silver stamen boss.
- **buckle_hex_frame**: an open pointed hexagon (bar about 5 px), 38 x 88 px (about 10 x 23 mm), long axis
  near-vertical, behind the blossom.
- **buckle_left_diamond**: an open diamond, 28 x 50 px, pointing back to the counter. The strap root passes
  under the crest spike / front band junction at about (140-150, 190-200).
- **buckle_right_diamond**: an open diamond, 33 x 49 px, with a small silver pin (the tongue).
- **strap_stud**: a pyramidal diamond, 36 x 15 px (about 9.5 x 4 mm), long axis along the strap, at (308,244).

### Insole (printed, flat)

- **insole_emblem**: a kite from (163,405) to (248,535), 155 x about 55 px, with an inner kite
  (**insole_emblem_inner**), a centre spine and chevrons.
  - The line work is metallic silver print (p90 #dcd6d1). The emblem ground is dark warm brown-black (#28221f).
  - It sits on the heel seat, and its long axis follows the insole midline.
- **insole_branch_stem**: a printed branch, 291 px long, running from the emblem tip toward the toe.
- **insole_blossom_1** (345,737), d 48 px; **insole_blossom_2** (300,812), d 55 px. Both are printed and
  grey-pearl, flatter than the metal-set blossoms.
- **insole_buds**: 11 printed buds, d about 12 px (centres listed in the JSON).

### Vamp

- **topline_piping** (`centerline`, 7 px, about 2 mm). A raised silver piping from the waist (205,745) along the
  vamp topline of the open side to the toe plate (612,878).
- **Vine frame, a pointed oval on the vamp side, made of three silver runs (5 px, about 1.3 mm):**
  - **vine_frame_back**: drops from the piping at (287,827) to the rear corner (268,1006).
  - **vine_frame_upper**: rises from the corner to the toe plate's rear arm (548,892).
  - **vine_frame_lower**: runs from the corner along the lower vamp to (400,1052), then up to the vamp blossom.
  - **vine_frame_corner**: a small pointed thorn plate at the V join.
- **vine_lower_run**: runs from the vamp blossom along the lower vamp to the toe frame's near rail (700,1110).
  It carries a diamond thorn at (652,1070).
- **vine_thorns**: 3 small pointed diamonds, at (372,910), (477,910) and (652,1070).
- **vamp_blossom**: pearl, d 68 px (about 18 mm), at (475,955). This is the largest blossom. **View B has no
  blossom here** (see section 9).
- **vamp_buds**: 7 closed buds (d about 16 px) on short silver stems.

### Toe

- **toe_apex_spike**: an upright pointed leaf plate at the throat, 57 x 67 px (bbox), tip (625,818). It has a dark
  recessed lens, and the tip stands proud of the topline.
- **toe_blossom**: pearl, d 64 px (about 17 mm), centre (672,913). It sits on the spike base and the arm junction.
- **toe_rear_arm**: a long pointed bar, 92 px, pointing back along the piping. The vine's upper arc runs into it.
- **toe_keystone**: a pointed diamond plate, 43 x 44 px, under the blossom where the two rails meet.
- **toe_frame_far_rail** (12 px, about 3 mm): runs along the far and top edge to the tip. It has inward thorns at
  about (773,1027) and (805,1090).
- **toe_frame_near_rail** (8 px): frames the cap on the visible side, then runs along the sole line to the tip.
- **toe_cap**: glossy black patent, polygon 161 x 169 px (area 13.2k px), 0.28 L_img long. A strong specular
  triangle sits at about (685-770, 1000-1075). The cap ends in a silver-capped tip (869,1172).
- **Sole edge**: a thin black semi-gloss edge about 8-10 px thick (about 2-3 mm) along the forefoot, with a lighter
  line at its top. It is visible from the waist to the toe.

---

## 7. Overlap order (back to front)

| Layer | Contents |
|---|---|
| 0 | insole + insole print; far-side lining |
| 1 | sole edge, stiletto body, top-lift |
| 2 | upper leather: counter (incl. the crackle medallion), vamp with the tone-on-tone emboss, far quarter |
| 3 | silver line work fixed to the leather: front branch band (also over the stiletto), C-band, sickle lames, topline piping, vine frame and vine runs |
| 4 | small silver details on the line work: crest spike (end of the front band), leaf spur, heel thorn, heel diamond, vine thorns, frame corner |
| 5 | glossy toe cap (inside the frame, flush or slightly proud of the vamp); counter blossom and vamp blossom and buds on their vines |
| 6 | toe plate: apex spike, rear arm, keystone, far and near rails (over the vamp and the cap edge); strap far run (in front of the far lining) |
| 7 | strap near run (in front of the far run at the fold); toe blossom (over the spike base, arm and keystone) |
| 8 | buckle hex frame, side diamonds, strap stud (on the strap) |
| 9 | buckle blossom (topmost) |

The strap root on the visible side passes UNDER the crest spike / front band junction.

---

## 8. Materials (sampled from view A; as rendered in the reference)

The values are lit colours, not albedo. Use them as render targets under similar light.

"Lum lin" is linear luminance. The p10/p50/p90/p98 columns are the median sRGB colour at those luminance
percentiles. Every material is near-neutral (saturation 0.06-0.15). Silver and pearl are slightly warm (R-B about
+13/255).

| Material | px | p10 | p50 | p90 | p98 | lum lin p10/p50/p90 | Notes |
|---|---|---|---|---|---|---|---|
| silver, antiqued (plates, bands, rails) | 17.3k | #463e39 | #817772 | #e4dfdb | #fdfcfb | 0.050 / 0.191 / 0.744 | Warm grey metal. Near-white bright edges on bevels; dark recesses. Reads as polished antique silver: high metallic, roughness about 0.25-0.35, cavity darkening |
| silver recess (lens inside the spikes) | 2.6k | #1b1816 | #605955 | #afa6a2 | #dcd6d2 | 0.009 / 0.102 / 0.391 | Recessed field: darker, still metallic |
| pearl blossom petals | 3.0k | #7c6e67 | #a79f9b | #d1ccc8 | #e4e0dd | 0.164 / 0.353 / 0.608 | Warm pearl-grey, **not pure white**. Soft sheen; silver-edged petals |
| blossom centre boss (stamens) | 76 | #7b6960 | #998a83 | #dbd4c8 | #edebe0 | | Silver stamen dots on a warm centre |
| toe cap, glossy black | 13.2k | #060505 | #161515 | #7e7a7c | #bdbbbb | 0.002 / 0.008 / 0.198 | Neutral patent black: base near-black, sharp broad speculars |
| vamp leather | 8.4k | #0c0b0b | #1e1c1b | #343230 | #434240 | 0.003 / 0.012 / 0.032 | Black; fine grain (autocorrelation zero at 2 px, about 0.5 mm) + tone-on-tone floral emboss |
| counter medallion leather | 9.7k | #131110 | #312f2e | #5a5857 | #696765 | 0.006 / 0.029 / 0.098 | Crackle grain, cells about 6-10 px; bulging, so lighter |
| far-side lining | 8.3k | #0a0908 | #0d0c0b | #141312 | #312e2c | 0.003 / 0.004 / 0.007 | Shadowed interior, matte |
| strap leather | 5.7k | #0e0d0c | #1d1b1a | #514f4f | #b5b4b5 | 0.004 / 0.011 / 0.079 | Smooth, satin sheen on the edges; stitching |
| stiletto body | 5.3k | #181614 | #262422 | #353230 | #403c3b | 0.008 / 0.018 / 0.033 | Black semi-gloss |
| top-lift | 0.7k | #0f0d0c | #1f1c1b | #3b3836 | #787473 | | Black |
| insole ground | 7.4k | #070505 | #282726 | #6a6968 | #7a7979 | 0.002 / 0.020 / 0.141 | Charcoal with a lighter centre band (satin) |
| insole printed blossoms | 1.0k | #5b5451 | #76706e | #928c89 | #a9a3a1 | 0.091 / 0.166 / 0.266 | Grey-pearl print, flat |
| insole emblem lines | 1.3k | #5d544f | #857c77 | #dcd6d1 | #fdfbf8 | 0.093 / 0.207 / 0.680 | Metallic silver foil print |
| insole emblem ground | 2.2k | #14110f | #28221f | #48403c | #514843 | | Dark warm brown-black (saturation 0.22) |

Sample regions are listed in `metro_measure.py`. Silver = front band + crest rim + piping + far rail, with
leather-edge pixels below 0.18 dropped. Pearl = petal ring 0.22-0.62 R of the four metal-set blossoms.

---

## 9. View A vs view B (design drift in the image)

| Item | View A | View B | Follow |
|---|---|---|---|
| Vamp side inside the vine frame | Big blossom (d 68) + 7 buds | Plain leather with the tone-on-tone emboss, 1 bud, a V-notch thorn on the upper arc (950,820) | **A** |
| Counter ornament | Crest spike + 2 sickle lames + C-band + medallion + counter blossom | Crest spike + stacked hooked lames (claw-like, pointing down-back), fewer vines; the medallion is visible | A for layout; B shows the same hooked lame shapes more clearly, so use B to read their hook profile |
| Heel, strap, buckle, stud, toe plate, toe cap, piping, emblem | Same design | Same design | Either (A is sharper) |
| Toe blossom / buckle blossom size vs shoe | 0.080 / 0.064 L_img | Slightly smaller relative size | A |

---

## 10. What the reference does NOT show (continue plainly; invent nothing)

**Hidden surfaces:**

- **The far side's outside** (the wearer's left, i.e. the inner side if right shoe). Only its lining and top edge are
  visible. Continue it as plain black leather: same collar line, stitched binding, no ornament and no opening. It
  is a closed quarter.
- **The outsole / sole underside, the waist underside and the top-lift face.** Only the sole edge is seen. Make it
  a plain black sole with the same thin edge.
- **The strap attachment on the far side and the strap's free tail and holes.** The loop is shown closed, and no
  tail or holes are visible. Keep the buckle decorative, with the strap entering it as shown, and no visible tail.
- **The heel back seen straight on, and the stiletto's far face.** Only the right side and back 3/4 are visible.
  Keep the silver band on the back of the stiletto as seen and the far face plain black.
- **The toe box interior and the forefoot insole.** Hidden. The printed branch simply ends under the vamp.

**Ornament beyond what is shown:**

- The crest spike, lames and C-band exist on the visible side and the back. Whether the C-band or lames wrap onto
  the far side is not shown, so stop them at the back centre line.
- The vamp vine frame and blossom exist on the visible side only. Do not add a mirrored vine on the inner vamp.

**Other unknowns:**

- The physical heel height and shoe length: only estimated (section 4.3).
- Anything under the strap or buckle (the buckle back).

## 11. Open points for the Study / Build agents

1. **Tall back vs the skinning rule.** The counter plus crest spike rise about 70-110 mm above her ankle joint
   (lower shin), and the strap about 30-60 mm above it. Skinning only to foot/ball plus the strap is likely to clip
   or look rigid in ankle flexion. Options:
   - add calf influence to the back panel and strap;
   - make the back panel stiff but let it slide;
   - lower the back.

   The last option changes the design and is the user's call.
2. **Opening side** (outer vs inner): recommended outer (section 2). The user may prefer inner.
3. **Heel height.** The image says about 82 mm (73-91) at her size. The pose chat uses 90 mm, which is inside the
   range. Confirm it with a silhouette-IoU fit of the built shoe in the section 3 camera.
4. **Accuracy.** Hand traces are 1-3 px on edges and landmarks, and 3-6 px on the dense counter-ornament envelopes
   (the lames and leaf cluster are simplified to centrelines and envelopes). For pixel detail, read
   `ref/viewA_crop.png` directly.
