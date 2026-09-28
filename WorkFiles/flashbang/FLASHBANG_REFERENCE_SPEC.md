# Flashbang - reference metrology spec

Reference: `References/Flashbang/flashbang_reference.png`, 1254 x 1254, sha256 `64d1f560...8fa9994a`. This is the only source.
Data file: `WorkFiles/flashbang/flashbang_spec.json`. Scripts: `WorkFiles/flashbang/metrology/fb_m*.py`, run headless in Blender 5.2 with NumPy. Debug images are in `metrology/debug/`.
Registered crops: `WorkFiles/flashbang/ref/`.

**Units.** D is the outer diameter of the perforated body tube. It measures 175.31 px at the objects' depth, taken as the mean of v2 (174.91) and v3 (175.71). H is height above the bottom contact line. Reference pixels are measured from the top-left of the file, with y pointing down.

## 1. Layout and camera

| id | panel | box x0,y0,x1,y1 | body centre x | body width px |
|---|---|---|---|---|
| v1 | front, pull ring toward viewer, lever on right | 40,30,345,725 | 157.7 | 178.5 |
| v2 | 3/4 A: lever hidden behind, ring edge-on at right | 345,30,615,725 | 467.0 | 174.9 |
| v3 | 3/4 B: lever at right limb, pin points right | 615,30,950,725 | 745.6 | 175.7 |
| v4 | lever side: lever front-right, ring at left | 950,30,1240,725 | 1103.2 | 181.1 |
| p1 | close-up: fuze head, ring, lever top | 6,756,318,1220 | | |
| p2 | close-up: perforated body | 323,756,629,1220 | | |
| p3 | close-up: base end face (oblique) | 634,756,939,1220 | | |
| p4 | close-up: one hole, inner brass tube | 946,756,1249,1220 | | |

- All four top-row objects sit in one perspective scene. Their bottom contact rows are y 720.5, 716.8, 717.0 and 717.0.
- v1 and v4 read 2.0% and 3.5% wider than v2 and v3, but their heights do not change. This is the off-axis widening of a cylinder, not a size difference. The true D comes from v2 and v3.
- **Camera estimate:** focal length about 2600 px (range 1750-3500), or about 75 mm full-frame equivalent (range 50-100). The horizon sits at about row y 460 (range 430-510), roughly level with the lower ring line. The camera is about 14.8 D from the axis.
  - Evidence: the sleeve step bows upward 4-5 px at the centre, so it is seen from below. The base-cap bottom bows downward 4-5 px, so it is seen from above.
  - This matters for heights. Front-surface points below the horizon read 3.5% too tall in a plain orthographic reading.
- The background is a neutral dark grey studio sweep, sRGB about (41,41,40), slightly lighter toward the top-right. Each object has a soft contact shadow. The key light is soft and comes from the upper right/front. Metal edges pick up bright rims.

## 2. Stack of heights (v2 front centre)

Both readings are listed. "Raw" is a plain orthographic reading. "Corr" is corrected for perspective with the camera above. **Build to the corrected column** and confirm it by overlaying a render from that camera on the registered crops.

| landmark | ref y | H raw (D) | H corr (D) |
|---|---|---|---|
| bottom contact (foot, front) | 716.8 | 0.000 | 0.000 |
| foot chamfer top = cap side bottom | 703.5 | 0.076 | 0.081 |
| cap side top = top-chamfer bottom (bright worn edge) | 643.0 | 0.421 | 0.413 |
| cap top-chamfer top = end of paint / body bottom | 632.0 | 0.484 | 0.471 |
| hole row C bottom / centre / top | 599.6 / 561.6 / 523.5 | 0.669 / 0.885 / 1.103 | 0.649 / 0.859 / 1.069 |
| ring line B/C | 501.5 | 1.228 | 1.190 |
| hole row B bottom / centre / top | 479.2 / 441.5 / 403.7 | 1.355 / 1.570 / 1.786 | 1.313 / 1.521 / 1.729 |
| ring line A/B | 383.5 | 1.901 | 1.840 |
| hole row A bottom / centre / top | 363.1 / 325.9 / 288.6 | 2.018 / 2.230 / 2.443 | 1.953 / 2.158 / 2.363 |
| sleeve bottom step (sleeve band starts) | 258.0 | 2.617 | 2.529 |
| sleeve top at full diameter (chamfer bottom) | 198.5 | 2.957 | 2.857 |
| sleeve top chamfer top | 185.3 | 3.032 | 2.936 |
| collar disc bottom (thin neck gap below) | 181.5 | 3.053 | 2.966 |
| collar disc top = plinth bottom | 156.5 | 3.196 | 3.105 |
| plinth top = housing box bottom | 149.0 | 3.239 | 3.158 |
| lever joggle (v4) | 140 | 3.290 | 3.168 |
| pin boss centre (median of 4 views) | 83.7 | 3.611 | 3.514 |
| ring top (v2-v4) | 77 | 3.650 | 3.544 |
| housing box top (v2) | 59 | 3.752 | 3.671 |
| top cover plate top (v3) | 48 | 3.815 | 3.732 |
| overall top: hinge knuckle / lever bend | 45 | 3.832 | 3.770 |

The landmark rows agree between v2 and v3 to within 1-3 px. v1 sits 4-8 px lower on some edges; for example, its sleeve step is at 266 instead of 258.

## 3. Diameters and sections

| part | D | notes |
|---|---|---|
| body (perforated tube) | 1.000 | constant from the sleeve step to the cap. v2 widths at three heights: 174.95 / 174.76 / 175.03 px |
| sleeve (solid top band) | 1.066 | v2 186.74 px, v3 187.10 px. Stands 0.033 D proud of the body. Small chamfers top and bottom; the bottom chamfer reads as a strong dark line |
| sleeve top chamfer, top edge | about 0.94 | roughly 45 deg, 0.063 D radial by 0.075 D tall. Paint is worn to bare steel on it |
| neck under the collar | about 0.74 | a 0.02 D dark gap |
| collar disc | 0.773 | height 0.143 D. Round steel disc with a chamfered top edge |
| plinth disc under the housing | 0.59 | height 0.043 D. Round |
| housing box | 0.48 square (range 0.46-0.52) | height 0.51 D. v2 face-on reads 82 px (0.46 after perspective). v3 shows two faces of 57 and 70 px, giving a 0.52 D side |
| base cap side | 1.095 | v2 189.9 px, v3 193.9 px. **Reads as 12 flats**: faint vertical facet lines about 30 deg apart and a polygonal top-chamfer edge. Corners are soft |
| foot (bottom edge after the lower chamfer) | about 0.94 | |
| inner brass tube | 0.76 (0.74-0.78) | its limb is visible inside the side holes: v2 r = 64.5 px, v3 r = 67.9 px |
| outer tube wall | about 0.04 (0.03-0.05) | the lit cut face shows on the side holes |

**Base cap.**
- Height 0.47-0.48 D. From the top down: a top chamfer (H 0.41-0.48), the faceted side (H 0.08-0.41), then a lower chamfer and foot (H 0-0.08).
- **End face (p3):** from the outside in there is a flat outer annulus, then a raised rim lip (about 0.045 D radial), then a narrow recessed groove (about 0.03 D), then a central disc (about 0.8 D), roughly flush with the rim.
- **There are 5 notches**, rectangular cuts about 0.05 D wide through the rim lip. Each has a matching step on the disc edge.
  - In p3 they sit at ref px (870,960), (778,995), (731,1124), (803,1157) and (918,1075).
  - Unprojected, they fall at about -10, -72, -156, 147 and 70 deg, which is a 72 deg pitch within +-12 deg.
- The side views v1 and v3 do not show narrow notches. Each shows one wide recess of 58-68 deg in the foot band instead. This conflicts with p3.

## 4. Holes

- **3 rows, and the rows are aligned** (no angular offset from row to row). This holds in all four views: each column's x extents match within 1-2 px.
- Row centres are at H 0.859 / 1.521 / 2.158 D (corrected). The row pitch is 0.66-0.69 D, with a 3% taller gap between B and C.
- **Shape: slightly tall ovals.** The paint-edge outline in v2 (front) is 0.349 D wide along the arc by 0.41 D tall, so w/h is 0.86. Measurements run 0.85-0.88 in v2, v3 and p4. The angular width is about 40 deg.
- Every hole has a thin bare-steel rim where the paint has chipped. The outer wall's cut face shows on the side holes.
- **Holes per row: the views do not agree.** Hole centres per view, in degrees from the camera direction (positive = right):
  - v1: -61, 36.5. The web between them is 57 deg.
  - v2: -61, 1.4, 63. The webs are 19-20 deg.
  - v3: -52, 11, 77. The webs are 22-25 deg.
  - v4: -67, 20, 87. The webs are 46 and about 20 deg.
- Candidate patterns:
  - **5 holes at 0/60/120/180/270, webs 20/20/20/50/50: recommended.** It is the only pattern that reproduces every view's local spacing.
  - 6 evenly spaced holes: matches v2, v3 and p2, but v1 and v4 would show an extra front hole where the reference shows paint.
  - 5 evenly spaced holes: wrong by 10-25 deg in every view.
  - Study should decide.
- **Inner brass tube:** it shows through every hole and carries one circumferential seam line at each row's centre height (0-3 px above centre), so 3 seams. The seam is about 0.006 D wide. The bright vertical band seen in each hole is the cylinder's specular highlight, not a part.

**Ring lines.** There are two thin engraved grooves, 2-3 px (about 0.015 D), with a light upper lip. They sit midway between rows (H 1.19 and 1.84 corrected), and the paint is worn along them. The sleeve-bottom step reads as a third, stronger line.

## 5. Fuze head, pin and ring

- **Hinge knuckle:** a horizontal cylinder, Ø 0.137 D by 0.33 D long, at the top edge of the lever-side face. Its top is the overall top of the grenade. The lever's top end curls around it.
- **Top cover plate:** about 0.1 D thick, over the box top. On the side away from the pin it continues as an arm that ends in a small curl with a cross pin. The arm's overhang is 0.07-0.25 D and differs per view: v1 x 75-118, v3 x 679-692, v4 x 1013-1035.
- **Pin boss:** a horizontal cylinder, Ø about 0.095 D by 0.17 D long, at the upper corner of the housing next to the knuckle. Its centre is at H about 3.5 D (corrected). The ring passes through the pin eye at its end.
  - In v1, v2 and v4, the pin axis is 90 deg from the lever normal: lever at the back / pin points right (v2); lever front-right / pin front-left (v4); lever right / pin toward the viewer (v1). v3 disagrees.
- **Small bosses:** a round boss about 0.057 D across near the top corner of a housing face (v1 x185 y63, v3 x802 y68). v3 also shows a slotted or spiral screw head of the same size at x760 y67.
- **Pull ring:** outer Ø about 1.05 D (1.00-1.09). It measures 186/183/176 px tall in v2/v3/v4 and 171 x 192 in v1. It hangs from the pin eye; the top is at H about 3.55 and the bottom reaches about the sleeve step.
  - The p1 close-up shows **one round wire of about 0.04 D**.
  - v1 reads as **two parallel strands** (split-ring style), each about 0.022 D. This is a conflict; p1 is the sharper source.
  - The ring's rotation differs per view: 26 / 74 / 66 / 72 deg from face-on for v1-v4.

## 6. Lever (spoon)

- The overall length is 2.9-3.1 D, running from the top curl at the knuckle to the tip.
- **Upper segment:** H 3.29 to 3.83 raw. It hugs the housing face and tapers from 0.41 D wide at the top to 0.29 D. In v4 the left edge slants and the right edge is vertical.
- **Joggle** at H 3.29 raw (v4 y 138-143). The lower segment steps outward, with a rounded top corner, to clear the collar and sleeve.
- **Lower segment:**
  - Flat face, 0.26 D wide (41 px face in v4).
  - It stands about 0.11 D off the body surface. v1 shows a 21 px gap; a fit to v4 gives 19 px.
  - A side band of 8-15 px shows along it. It is either a thick plate (about 0.05 D) or a shallow flange; the image cannot resolve which.
- **Tip:** the height above the bottom varies by view: v1 0.78, v3 0.99, v4 0.91 D. **Use 0.91 D**, which is level with the row C hole centre.
  - The end is squared with rounded corners (r about 0.05 D).
  - In v1 the last 0.1 D bends inward toward the body; this is the "bent tip". v3 shows only a rounded corner.
- Outlines: v4 is in `lever.v4_outline_ref_px`. For v1 (y >= 295) and v3 (y >= 265), per-row [y, xl, xr] data is in `lever.per_view_rows_ref_px`. The ring overlaps the lever above those rows.

## 7. Traced outlines

`outlines.silhouettes_ref_px`: the outer silhouette of each view as a polygon in reference pixels. It was traced with a Moore trace and simplified with Douglas-Peucker at 0.8 px. The floor shadow was clipped below y 690, and ring interiors are excluded. The bounding boxes are v1 [57,46,332,720], v2 [368,42,585,720], v3 [647,44,928,720] and v4 [976,41,1204,720].

## 8. Colour, measured under the reference lighting (sRGB 8-bit, p10 / p50 / p90 by luminance)

| material | p10 | p50 | p90 | linear p50 |
|---|---|---|---|---|
| olive paint | 46,46,31 | **71,71,54** | 111,110,90 | .063,.063,.036 |
| bare steel in chips (body) | 86,79,69 | 102,94,84 | 149,141,131 | .134,.111,.088 |
| dark steel, base cap | 17,17,15 | 39,37,36 | 76,71,67 | .020,.019,.018 |
| worn bright edges, cap (top 3%) | 94,89,81 | 106,99,89 | 167,158,146 | |
| fuze housing steel | 32,31,29 | 62,59,57 | 91,85,80 | |
| collar steel | 24,23,21 | 58,54,51 | 102,96,91 | |
| lever face (v4, toward the key light) | 70,66,65 | 84,80,77 | 109,102,95 | |
| brass inner tube (lit half) | 40,33,23 | 62,53,41 | 114,98,80 | .048,.035,.022 |
| brass inner tube (all, mostly shadow) | 7,6,2 | 29,24,16 | 87,75,60 | |
| dark grime on paint (includes contact shadows) | 8,6,4 | 23,22,14 | 31,29,20 | |
| background | 36,36,36 | 41,41,40 | 47,47,46 | |

- **Paint:** a muted olive-khaki. R and G are about equal, with B about 25% lower. It is matte with a faint sheen.
- **Bare steel:** a slightly warm, antiqued silver.
- **Steel parts:** dark oxidised steel with bright, sharp worn edges.
- **Brass:** a warm bronze-gold.
- These values are appearance under the reference light, not albedo.

## 9. Wear pattern

- Paint covers about 72% of the body area outside the holes. About 14% is chipped, of which 3.4% is bright bare steel. About 6% is dark grime or shadow.
- **Where the chips are:**
  - A continuous thin bare rim around every hole. 58% of pixels within 3 px of a hole edge are unpainted, against 11% elsewhere.
  - The sleeve top chamfer, which is almost fully bare.
  - Along the sleeve-bottom step, both ring lines, and the body bottom above the cap.
  - Scattered small flecks, 0.005-0.02 D, across all paint.
  - A few larger patches up to about 0.1 D, for example on the v1 and v4 sleeves and the lower body in v2 and v3.
  - A thin vertical dark scratch or streak in v2 at x about 453, over rows A and B.
- **By height:** chip fraction per 10 px band runs 0.03-0.24. It peaks at the sleeve top, the sleeve step, the ring lines and the hole zones, and is lowest just under the ring lines.
- **Steel parts:** dark, with bright worn edges on every arris: cap facets and chamfers, collar edges, housing edges, and the lever's edges and face. There are fine bright scratches, heavier on the lever face (v4), and small pits or dents on the cap.
- There are no markings or text anywhere.

## 10. Inconsistencies in the reference

The four top-row views are **not a rigid turntable of one object**.

1. **Hole spacing** is 60-63 deg in v2 and v3 but has one about 50 deg web in v1 and v4 (section 4).
2. **Lever position against the holes and pin:** no single set of per-view yaws fits all four views. v3 is the odd one for the pin.
3. **Ring wire:** single in p1, a double strand in v1.
4. **Lever tip height:** 0.78 / 0.99 / 0.91 D in v1 / v3 / v4.
5. **Top-plate arm overhang:** 0.07-0.25 D depending on the view.
6. **Base notches:** five narrow notches in p3, one wide recess in the v1 and v3 side views.
7. **Housing box side:** 0.46 D (v2) against 0.52 D (v3).
8. **v1 landmark rows** sit 4-8 px lower than v2 and v3.

When comparing, give each view its own best yaw instead of a fixed turntable step.

## 11. What the reference does not show

- A plan view of the fuze top, or the far side of the housing and the underside of the top plate.
- Details of the pin: shaft length, the far or cotter end, and how the pin passes through the housing.
- The ring's split or gap, and whether the wire is truly round.
- The lever's inner face and cross-section (flat or channel), and whether anything retains the lower end.
- The hinge internals and how the curl is formed.
- The back of the body in any single view, so the full hole count cannot be seen directly.
- The ends of the inner tube and anything inside it.
- A straight-on view of the base end face (there is only one oblique close-up), plus notch depth and rim height.
- Whether the cap is a separate threaded part.
- Real-world scale: there is no size reference.
- Roughness and metalness values; only appearance is shown.
- Any markings, labels, text or serials. None are shown, so none should be added.

## 12. Files

**Specs:**
- `WorkFiles/flashbang/flashbang_spec.json` holds all numbers, per-view data, outlines, colours and registration.
- `WorkFiles/flashbang/FLASHBANG_REFERENCE_SPEC.md` is this file.

**Registered crops in `WorkFiles/flashbang/ref/`:**
- `fb_ref_v{1-4}_registered_D200.png`: each view scaled by its own body width, D = 200 px, axis at column 220, bottom contact at row 790.
- `fb_ref_v{1-4}_registered_common.png`: all four views at one common scale (200/175.31). **Use these for render comparison**, because v1 and v4 are widened by perspective.
- Strips: `fb_ref_top_row_registered_D200.png`, `..._D200_guides.png` (guides every 0.5 D and at ±0.5 D) and `fb_ref_top_row_registered_common.png`.
- `fb_ref_p{1-4}_*_native.png` / `_x2.png`: the close-up panels.
- `parts/fb_ref_v{1-4}_{head,sleeve_and_rowA,holes_rows,base_cap,lever_lower}_common.png`: part crops at the common scale.
- `fb_registration.json` gives the mapping for each view: `reg = 220 + (x - centre)*scale`, `reg_y = 790 + (y - bottom)*scale`.

**Measurement scripts:** `WorkFiles/flashbang/metrology/`. `fb_crop.py` and `fb_ruler.py` are crop tools with pixel rulers. `fb_m01`-`fb_m23` are the measurement stages.
