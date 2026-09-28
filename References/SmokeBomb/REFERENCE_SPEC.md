# SMOKE BOMB: REFERENCE SPECIFICATION

> **The rule:** the shipped ball must look like `smokebomb.png`: the same outline, the same strips in the same
> places, the same over/under at every crossing, the same fray, weave, sparkle and colour. **Nothing may be added
> that the reference does not show.** Measure the build's render with the same instruments this document used.
> If the render looks different, it fails, even when every number passes.

Machine twin: `WorkFiles/smokebomb/reference_metrology/reference_spec.json`. It holds every row below, plus
seven control points for every traced edge in image px, disc coordinates and camera-frame lat/lon.
Labelled debug diagram: `WorkFiles/smokebomb/reference_metrology/debug/DEBUG_NEVER_SHIP_sb_strip_layout_LABELLED.png`
(**DEBUG, NEVER SHIP**).

---

## 0. Authority, instrument, conventions

| | |
|---|---|
| **Reference of record** | `References/SmokeBomb/smokebomb.png`, 1254 × 1254 RGBA (alpha 1 everywhere), sha256 `813105ec…2e1c2`. It is byte-identical to `Downloads/smokebomb.png`. Nothing else is evidence. |
| **Status labels** | Every row is **MEASURED** unless it says **INFERRED** (a geometric consequence of measured rows) or **DESIGNED** (a proposal for something the photo cannot show, mainly the far side). |
| **Instrument** | Blender 5.2 Python + NumPy 2 in headless runs. The scripts are `WorkFiles/smokebomb/reference_metrology/sb_m00 … sb_m29`, and the stage outputs are `sb_s*.json`. |
| **Scale** | The ball's diameter in the reference is **D = 928.2 px**. Lengths are given in reference px and as fractions of D (`frac D`). The photo does not show the real size, so mm are the build's decision. Multiply `frac D` by the chosen diameter. |
| **Image frame** | x points right and y points down, in px. The **image angle** is measured CCW from 3 o'clock about the ball centre (90° = 12 o'clock, 180° = 9 o'clock, 270° = 6 o'clock). |
| **Camera frame** | X points right, Y up and Z toward the camera. **lat** is measured up from the X–Z plane. **lon** is measured from +Z (facing the camera) toward +X (right). The image centre is lat 0, lon 0, and the right limb is lon 90. |
| **Back-projection** | Orthographic about the silhouette circle (see §2). Every sphere position in this spec depends on that choice. |
| **Colour values** | Stored sRGB 0–1, unless the name ends `_lin` (linear). |
| **Build input policy** | This spec is numbers and words. The trace (`sb_trace.json`) and every debug image exist only for measurement. The build must never read them, and must never sample, project or trace the reference pixels. |
| **What the reference is** | A single product-style still. Its strips are not guaranteed to be physically consistent. The strips differ in width (0.04–0.24 D), several edges are not circles on the sphere, and the over/under contains a cycle (§4.4). The spec records what is seen. It does not tidy it. |

---

## 1. SILHOUETTE

**Verdict: the ball is round to ±2 %. The outline is lumpy at a low order, with a flat upper-right and lower-left
and a fuller upper-left. It is stepped wherever a strip edge crosses the limb. It is fuzzy with fibres but carries
no loose thread.**

| Row | Reference | Tolerance for the build's render | How |
|---|---|---|---|
| Centre | (627.38, 628.92) px | ±3 px | Geometric circle fit to 3600 sub-pixel radial edge samples. The edge is the half-maximum between the backdrop (0.996) and the rim cloth (0.162). |
| Diameter | **928.2 px = 0.7402 of the frame width** | ±1.0 % | Circle fit |
| Circularity (rms radial deviation) | **5.78 px = 1.24 % R** | 0.8 – 1.8 % R | Residual of the circle fit |
| Largest departures | +18.7 px / −14.2 px | ±4 px each | Same |
| Ellipse | axes 937.4 × 919.2 px (ratio 1.020). The long axis lies along image angle **125°** (upper-left ↔ lower-right). | ratio 1.01–1.03; axis ±20° | Direct least-squares ellipse |
| Harmonics of r(θ) (px) | n2 4.58 · n3 3.14 · n4 1.50 · n5 2.45 · n6 2.07 · n7 1.97 · n8 0.67 | each ±50 % | FFT of r(θ) about the fitted centre |
| **Flattening** | sector 30–60° (upper-right) **−1.75 % R**; sector 180–210° (left, just below 9 o'clock) **−1.67 % R** | ±0.7 % R | 30° sector means |
| **Bulge** | sector 120–150° (upper-left) **+1.83 % R**; a local bump at **88°** (top, where the whorl strips stack) of **+14.9 px = +3.2 % R**, about 6° wide | ±0.7 % R; bump ±5 px | Sector mean; high-pass peak |
| **Bumpiness** (radius minus its n ≤ 6 reconstruction) | rms **3.42 px = 0.74 % R**; range −9.5 … +14.9 px | rms 0.5–1.0 % R | Same |
| **Strip-edge steps in the outline** | **12 jumps ≥ 4 px** (within 0.5° of arc). Median **5.7 px**, max **8.5 px**. They sit at 11.8° (B's lower edge), 51.0°, 64.2°, 87.1°/88.4° (whorl), 155.1° (upper-left strips), 196.1° (C's upper edge), 211–221° (C's lower edge), 285.4°, and 332.0° (W/A). | count 8–16; median 4.5–7 px; max ≤ 10 px | Radius jumps |
| **Thread tips past the outline** | Only fibre fuzz reaches past the outline: 56 places reach > 3 px beyond the half-max edge, the largest **7.4 px** (1.6 % R). There is one small hook (**T4**, image angle ≈155°, (191, 432), 6 px). **No loose thread hangs off the ball.** | max ≤ 9 px; none longer than 10 px | Outermost 97 %-of-step crossing minus the 50 % edge |
| Not present | No fuse, knot, tag or cord. No tear, cut, scorch or dirt. **No free strip end anywhere on the visible side.** (W's corner at the right limb wraps around the limb. It is not a cut end: see the 6× check `sb_view_960_660_T150_K6`.) | must stay absent | Visual, 2×–6× views |

---

## 2. CAMERA AND FRAME

| Row | Value | Tolerance | Why |
|---|---|---|---|
| **Projection** | **Orthographic** (long-lens equivalent) | Use orthographic for the comparison render | A centred sphere's outline is a circle at every focal length, and the photo carries no other perspective cue. This spec back-projected orthographically, so an orthographic camera reproduces every position exactly. **Do not mix a perspective camera with these numbers.** With a 100 mm full-frame lens, a point 45° from the view axis lands 9 % R further out than orthographic. With 200 mm it lands 4.7 % R further out. |
| Ortho scale | frame width = **1.3510 D** | ±1 % | 1254 / 928.2 |
| Frame | 1254 × 1254, square | exact aspect | File |
| Ball centre in frame | (627.4, 628.9) px, about 2 px below the frame centre | ±3 px | Circle fit |
| **Elevation** | **0° by convention.** The strip layout is given in the camera frame. Rendering at elevation 0 with the ball oriented as specified *is* the reference view. | — | A ball on a seamless white sweep has no horizon, no ground plane and no contact shadow, so elevation cannot be measured. |
| Elevation, alternative (INFERRED) | If the build makes the **top whorl** the asset's world-up axis, the same view needs the camera at **+34.6° elevation** (±5°), with the whorl leaning **9.4° right of vertical** in the frame. | ±5° | 90° − 55.4° (the whorl's angle from the view axis, §4.5) |
| Focal length | Not measurable. Any lens ≥ 85 mm also explains the outline. | — | See the projection row |
| **Background** | Uniform **0.996 stored (254, 254, 254)**, std 0.002. Rings 25–240 px outside the ball read 0.9960 below, above, left and right. **No gradient, no shadow, no ground line.** | ±0.004 | Corner patches and radial rings |

---

## 3. LIGHTING

Method: 16 px blocks, taking the 75th percentile of linear luminance in each (the lit top of the cloth, with
crevices excluded). The blocks were fitted on their sphere normals (`sb_m20`, `sb_m24`). The strip structure
carries much of the variance, so fits reach R² 0.53–0.57. The directions are good to the tolerances given.

| Row | Value | Tolerance |
|---|---|---|
| **Key** (direction *to* the light, camera frame) | **az +60° (right), el +64° (up)**, vector (0.380, 0.899, 0.219). This is a soft light high above and to the right, slightly in front of the ball. | az ±25°, el ±10° |
| **Fill / rim** | **az −116°, el +4°**, vector (−0.897, 0.070, −0.437). It comes from the **left and behind** the ball, grazing the left limb, which is why the left-limb strips read bright. | az ±25°, el ±15° |
| Fill / key | **0.67** | ±0.2 |
| Ambient / key | **0.42** | ±0.15 |
| Softness | Large, soft sources. There is no terminator line, no cast shadow, and no hard shadow at any step apart from the crevices (§5). The shading ramps smoothly (a wrap-lighting fit gives w ≈ 0.1). On the order-2 SH irradiance, the brightest visible normal is (0.22, 0.89, 0.40), the darkest is (−0.09, −0.56, 0.82) (lower centre), and **max/min = 4.15**. | max/min 3.2–5.2 |
| Quadrant targets (block-p75 linear luminance) | upper-left **0.0338**, upper-right **0.0435**, lower-left **0.0176**, lower-right **0.0176**, centre **0.0204**. The top half is about **2.2×** the bottom half. | each ±15 %, after matching the render's exposure at the centre |
| Specular | **None.** No glossy hot spot appears anywhere. The brightest pixels (p99.9 = 0.615 stored) are fibre sparkle and rolled strip edges. | must stay matte |

---

## 4. STRIP LAYOUT

### 4.1 What the ball is made of

The visible hemisphere shows **21 ± 2 strip segments**. Because one strip shows on both sides of the belt
(§4.3), they come from about **20 distinct strips**. They fall into five families:

1. **The belt**: four strips crossing the front diagonally, the most prominent part of the image.
   - **W** is a narrow top-most strip. It is twisted edge-on at its left end and lies flat on the right.
   - **A** is a wide strip under W.
   - **B** (upper right) and **C** (lower left) look like one strip passing under A and W.
   - **X** is a wedge showing between B and W at the right.
2. **The rim / left-limb family**:
   - **R_in/L5, R2 and R3** sweep from the top whorl leftward around the upper-left.
   - **R_in** continues down the left limb as **L5**.
   - **L3 and L4** run down the left side between L5 and A.
3. **The upper family**: **U0 … U5** fan from the top whorl down to B's upper edge and to W's twisted section.
4. **The bottom family**: **D_a, D_b, D_c** plus two strips along the bottom outline. All converge toward the
   bottom outline.
5. **E**: a strip along the lower-right outline, under A.

There are two **whorls**:
- a **top whorl**, well inside the visible disc at (690, 252), where the rim and upper families meet around a
  dark V-gap;
- a **bottom convergence**, at or just behind the bottom outline and not visible.

### 4.2 Strip table

The width is measured on the sphere, as the nearest-point angular distance between the strip's two boundary
edges, and is given as the median (p10–p90). "Visible" means one boundary belongs to another strip lying on top,
so the true width is at least this value. The edge ids refer to the control points in the JSON and to the debug
diagram. Limb angles are image angles.

| Strip | Width (arc °) | frac D | image px | Width is | Edges | Enters → leaves | Over | Under | Tol |
|---|---|---|---|---|---|---|---|---|---|
| **W** (flat part, x 700–1040) | 9.8 (6.2–12.6) | **0.085** | 79 (50–102) | true | WUP, WLO | from under R_in at (363, 390) → right limb **334°–349°** | A, X, B, U0 | R_in | ±15 % |
| **W twisted section** | 1.1 (0.5–2.1) | 0.010 | 9 (4–17) | seen edge-on | WTW | (363, 390) → (610, 550), about 290 px long, then it opens over about 150 px | — | — | ±50 % |
| **A** | 25.3 (17.2–29.5) | **0.221** | 199 (127–232) | visible (upper edge under W) | ALO (own), WLO/WTW (W's) | from under R_in at the upper-left → right limb **330°–334°** | C, L3, D family, E | W, R_in | ±12 % |
| **B** | 19.9 (17.6–20.6) | **0.173** | 157 (141–164) | true | BUP, BLO | from under W (tip between (556, 510) and (705, 586)) → right limb **12°–26°** | X, U1–U5 | W | ±10 % |
| **X** | 9.8 (1.5–20.4), a wedge | 0.086 | 77 (12–161) | visible only | BLO (B's), WUP (W's) | from under B and W at x ≈ 705 → right limb **349°–12°** | — | B, W | ±20 % |
| **C** | 26.0 (23.5–27.2) | **0.227** | 208 (189–213) | true | CUP, CLO | left limb **198°–221°** → under A between (365, 676) and (625, 843) | L3, L4, L5, D family | A | ±10 % |
| **R_in / L5** | upper part 4.4 (3.7–5.8) | 0.038 | 26 (21–38); left-limb part ~40 (foreshortened) | visible | LIN | from beside the whorl (580, 306), around the upper-left and down the left limb → under C at (258, 712) | W's left end, A's top-left, U0, L4 | C | ±25 % |
| **R2** | 18.5 (13.7–22.8) | 0.162 | 118 (78–147) | visible | LC, LA | from the whorl region leftward → upper-left limb **140°–167°** | ? | ? | ±25 % |
| **R3** | — | — | 10–40 (foreshortened) | visible | LA | outermost upper-left strip → limb at **~140°** | ? | ? | ±30 % |
| **L3** | 9.6 (7.4–10.3) | 0.083 | 64 (50–67) | visible (right edge under A) | L3L | from under R_in at (270, 452) → under C at (310, 700) | — | A, C, R_in (L4: low confidence) | ±20 % |
| **L4** | 9.0 (1.7–10.6) | 0.078 | 49 (7–56) | visible | L3L, LIN (lower) | same extent as L3 | L3? | R_in/L5, C | ±25 % |
| **U0** | — | ~0.145 | ~135 | visible | UA, LIN (upper) | from under W's twisted section up-right → top whorl | — | W, R_in | ±25 % |
| **U1** | 5.7 (5.0–11.6) | 0.050 | 45 | visible | UA, UC | from B's upper edge → top whorl | — | B | ±25 % |
| **U2** | 8.5 (6.8–11.2) | 0.075 | 69 | visible | UC, UD | same | — | B | ±25 % |
| **U3** | 13.5 (8.5–17.5) | 0.118 | 98 | visible | UD, UE | bends over toward the right | — | B | ±25 % |
| **U4** | 9.9 (9.2–11.6) | 0.086 | 66 | visible | UE, UF | runs from the whorl toward the right limb | — | B | ±25 % |
| **U5** | — | — | 60–80 | visible | UF | between UF and the upper-right limb, image angles **~39°–55°**, down to B | — | B | ±30 % |
| **D_a** | 27.2 (25.0–29.6) | 0.237 | 173 | visible | D14, D57 | from under C → bottom-left outline | — | C | ±20 % |
| **D_b** | 12.3 (11.6–13.4) | 0.107 | 86 | visible | D57, D9 | from under C → bottom | — | C | ±20 % |
| **D_c + bottom-rim strips** | — | — | 60–140 | visible | D9, D19, D27 | from under A/C → bottom outline (converging toward image angle **265°–280°**) | — | A, C | ±30 % |
| **E** | — | — | ~140 at x = 800 | visible | ALO (A's), D27 | along the lower-right outline | — | A | ±30 % |

**Strip widths are not all equal**, and that is measured, not noise. There are three wide strips (A, C, D_a:
0.22–0.24 D), a medium one (B, 0.17 D) and a narrow top strip (W, 0.085 D, whose edges are both its own). Build
each strip at its own measured width.

**Edge shape (MEASURED).**
- **Near great circles.** These edges fit a great circle to within a few px:
  BUP (pole lat −58.6°, lon 56.3°; 3.4 px rms), BLO (−77.8°, 79.6°; 2.8 px), WUP (−72.3°, −63.1°; 3.1 px),
  CUP (−70.5°, 70.3°; 2.3 px), LC (−43.8°, 1.6°; 4.2 px), D9 (17.7°, 64.7°; 1.2 px) and D57 (5.4°, 58.7°; 2.0 px).
- **Not circles.** ALO, LIN, WTW and CLO are clearly not circles (11.8 / 26.8 / 1.7 / 2.3 px rms for their best
  *small* circle, and much worse for great circles).
  - A's lower edge drops almost vertically at the left (x 282 → 340 over y 455 → 635). It then swings right and
    down across the centre. **Build those edges through their control points, not as circles.**

**Main edge control points** (image px → camera-frame lat, lon). Seven evenly spaced points each; every edge is
in the JSON.

| Edge | Points |
|---|---|
| WTW (W twisted) | (363, 390) 31.0, −41.6 · (438, 451) 22.5, −26.2 · (520, 509) 15.0, −13.8 · (609, 550) 9.8, −2.3 |
| WUP (W upper) | (610, 550) 9.8, −2.2 · (757, 602) 3.4, 16.2 · (902, 656) −3.3, 36.4 · (1048, 712) −10.3, 67.0 → limb 348.8° |
| WLO (W lower) | (540, 522) 13.3, −11.2 · (703, 635) −0.7, 9.3 · (875, 736) −13.3, 33.2 · (1044, 837) −26.5, 90.0 (limb 333.5°) |
| ALO (A lower) | (282, 455) 22.0, −53.4 · (330, 612) 2.1, −39.9 · (435, 732) −12.9, −25.2 · (574, 817) −23.9, −7.3 · (727, 876) −32.1, 14.6 · (882, 920) −38.8, 44.8 · (1027, 861) −30.0, 83.9 |
| BUP (B upper) | (556, 510) 14.8, −9.2 · (722, 441) 23.9, 12.9 · (893, 393) 30.5, 41.7 · (1069, 417) 25.6, 90.0 |
| BLO (B lower) | (705, 586) 5.3, 9.7 · (830, 573) 6.9, 26.0 · (954, 544) 10.5, 45.8 · (1079, 535) 11.7, 83.9 |
| CUP (C upper) | (190, 768) −17.4, −81.0 · (271, 710) −10.1, −51.2 · (365, 676) −5.8, −34.6 |
| CLO (C lower) | (270, 935) −40.6, −90.0 · (385, 891) −34.4, −39.2 · (503, 862) −30.1, −18.1 · (623, 843) −27.4, −0.6 |
| LIN (R_in inner) | (580, 306) 44.1, −8.2 · (385, 378) 32.8, −38.5 · (293, 434) 24.8, −52.6 · (223, 513) 14.5, −64.1 · (215, 616) 1.6, −62.8 · (258, 712) −10.3, −54.0 |

### 4.3 One strip on both sides of the belt (INFERRED from measured fits)

The great circle through **C's upper edge** meets the right limb at **18.4°**, inside B's exit band (12°–26°).
The great circles through **B's two edges** come back to the limb at **192°–207°**, inside C's entry band
(198°–221°). Their poles lie within 8°–13° of each other.

**B and C are therefore one strip. It enters at the lower-left, dives under A and W, and comes out as B.** It is
0.227 D wide as C and 0.173 D as B, so it narrows by about 25 % across the hidden stretch. Build it as one strip
with that taper.

**X** is either its own strip lying parallel to A, or the upper part of A showing above W. The photo cannot
settle which, because both of X's boundaries belong to other strips. Build it as a separate strip at least 0.18 D
wide, parallel to A, under B and W.

### 4.4 Over/under at every crossing

`X > Y` means X lies over Y. The evidence types are:
- **T-junction**: one edge ends against another; the edge that continues belongs to the strip on top.
- **Hanging fibres**: fibres drape from the upper strip onto the lower one.
- **Outline step**: the upper strip stands proud at the limb.
- **Shading rule**: the rolled bright rim belongs to the strip on top, and the dark crevice lies on the strip
  beneath. This rule is reliable only on edges facing down or sideways.

| # | Crossing | Where | Evidence | Confidence |
|---|---|---|---|---|
| 1 | **W > A** | along W's whole lower edge (540, 522) → (1046, 838) | T1/T2 hang from W onto A; rim on W, crevice on A; outline step 5.8 px at 332° | high |
| 2 | **W > X** | W's upper edge, x 705 → 1048 | rim on W; X has no edge of its own | high |
| 3 | **W > B** | B's tip, between (556, 510) and (705, 586) | both of B's edges end at W (T-junctions) | high |
| 4 | **W > U0** | (496, 486) | UA ends at W's twisted section | medium |
| 5 | **R_in > W** | (363, 390) | W's twisted end comes out of R_in's crevice | high |
| 6 | **R_in > A** | (282, 455) | A's lower edge ends at R_in's crevice | high |
| 7 | **R_in > U0** | R_in's inner edge (378–505, 314–387) | deep crevice on the U0 side | medium |
| 8 | **B > X** | B's lower edge (705, 586) → (1080, 535) | rim on B, crevice on X; outline step 6.2 px at 11.8° | high |
| 9 | **B > U1…U5** | B's upper edge (556, 510) → (1070, 418) | the U edges end at it; the rolled rim carries B's along-strip texture | medium-high |
| 10 | **A > C** | (365, 676) and (625, 843) | both of C's edges end at A's lower edge | high |
| 11 | **A > L3** | A's lower edge, x 282 → 365 | L3's own right edge is hidden | medium |
| 12 | **A > D family, E** | A's lower edge, x 540 → 1028 | crevice below it; D9 ends at the A/C junction | high |
| 13 | **C > L3, L4, L5** | C's upper edge (190, 768) → (365, 676) | the L edges end at C; outline step 6.7 px at 196° | high |
| 14 | **C > D family** | C's lower edge (270, 935) → (625, 843) | D14 and D57 end at it; rim on C, crevice below | high |
| 15 | L4 > L3 | (250–310, 480–700) | shading rule only | **low** |
| 16 | **gaps**: U0 / U1 V-gap, from (496, 486) opening to ~30 px at (585, 390); **whorl V-gap** (626–693, 188–254) | | dark wedges: the strips butt together without overlapping | high |

Not resolvable: R_in against R2 against R3, X against A, and any order inside the U family.

**The order is not one stack.** R_in lies over A (row 6), A over C (row 10), and C over L5, which is R_in's own
lower end (row 13). That is a cycle, so the strips are **woven**. Build crossing-local layering: at each crossing,
offset the upper strip radially by one step height (§5). A single global layer index cannot represent this.

### 4.5 Whorls

| Row | Value | Tol |
|---|---|---|
| **Top whorl** | Apex of the V-gap at **(690, 252) px**, sphere (0.135, 0.812, 0.568). That is **55.4°** from the view axis, leaning **9.4°** right of vertical (image angle 80.6°). These meet there: R2, R3 and R_in from the left; U0–U4 from below; U5 and UF toward the right. The V-gap is a dark wedge about 90 px long, about 20 px wide at its open end. | ±10 px |
| **Bottom convergence** | At or just behind the bottom outline, image angle **265°–280°**. Not visible. | — |

---

## 5. OVERLAP STEP (thickness) AND EDGE LOOK

| Row | Value | Tolerance | How |
|---|---|---|---|
| **Step height** | **5.7 px = 0.0062 D** | 4 – 8.5 px (0.004 – 0.009 D) | Measured directly as the outline jumps where strip edges cross the limb (12 jumps ≥ 4 px). The shading agrees (next row). |
| **Edge look** (averaged cross-profile along each edge) | Every over-strip edge reads as a **rolled, fuzzy rim** 4–8 px wide and **1.5–3× brighter** than the strip body (log +0.42 … +1.13). An **occlusion crevice** lies 2.5–3.5 px beyond it on the strip beneath, **30–47 % darker** (log −0.35 … −0.63). Per edge, rim / crevice offsets in px: WLO −8.3 / +3.0; BLO −6.8 / +3.0; ALO −4.8 / +2.5; CLO −7.0 / +3.5. | rim 0.4–1.2 log; crevice 0.3–0.65 log | `sb_m22` |
| Upward-facing edges (B's upper edge) | The rim sits on the edge line, and a thin dark line runs about 6 px *inside* B (the roll's own shadow). The crevice on the strip beneath is weak, because the key light is overhead. | — | same |

This matches the kunai lesson: **the step must be geometry**, so that it reaches the outline (8–16 steps of
4–8.5 px), and each edge must be a rounded, fraying roll, not a sharp cut.

---

## 6. FRAY AND LOOSE THREADS

| Row | Value | Tolerance | How |
|---|---|---|---|
| **Fray amplitude** | Edge position jitter **rms 1.5 px** (0.0016 D), **p95 3.5 px**. Per edge rms: WLO 2.0, WUP 1.0, BLO 1.7, BUP 1.9, ALO 0.9, CLO 1.4, CUP 1.1 px. | rms 0.9–2.0 px; p95 2–5 px | Sub-pixel edge location every 1 px along each edge, about a 41 px running median |
| **Fray wavelength** | **11.5 px** (0.012 D); per edge 8.4–15.2 px | 8–15 px | 2 / the zero-crossing rate of the jitter |
| Fibre fuzz | Concentrated on the rolled rims. It sets the outline wisps (≤ 7.4 px past the edge). | see §1 | — |

**Loose threads: exactly two you notice, plus three tiny ones. Add no others.**

| id | Where | Size | Shape | Tol |
|---|---|---|---|---|
| **T1** | Hangs from **W's lower edge at (801, 703)** and drapes down over A to its tip at (797, 741) | **38 px (0.041 D)** long, 2–3 px thick | curly; forks about 12 px from the tip | position ±6 px, length ±8 px |
| **T2** | Hangs from **W's lower edge at (936, 783)** to its tip at (932, 812) | **29 px (0.031 D)**, 2–3 px thick | slight fork near the edge | ±6 px / ±8 px |
| T3 | Short fibre curl lying on A, centred at (375, 607) | 14 px | forked curl | ±8 px |
| T4 | Hook on the outline at the left, (191, 432), image angle ≈155° | protrudes 6 px | small loop | ±3 px |
| T5 | Stub at W's lower edge near the right limb, (989, 820) | 9 px | straight stub | ±5 px |

---

## 7. CLOTH

| Row | Value | Tolerance | How |
|---|---|---|---|
| Construction | A plain-weave, cotton-like tape that reads **warp-faced**: the visible texture is fine striations running **along each strip**, and the cross (weft) structure is only a faint, irregular grid. | — | FFT of 64 px patches in seven strips. 39–58 % of the texture power lies within ±20° of the along-strip direction, and only 13–20 % across it. |
| **Warp pitch** | **4.1 px = 0.0044 D** (by patch: A 4.3/4.1, B 4.0, C 3.4, U 3.6, W 3.2, X 5.5, rim 3.0–3.9). That is about **50 threads across a wide (0.22 D) strip**. | 3.4–5.5 px | dominant spectral peak |
| Weft | No stable period (3–18 px across patches). It reads as irregular cross-dots at about twice the warp pitch. | faint | weft-wedge peak |
| Weave visibility | high-pass log-luminance std **0.13** (±13 %); linear p90/p10 within a patch about **8** | 0.10–0.16; 5–13 | per patch |
| **Persistent streaks** (the only slub-like feature) | **7 per 100 px across a strip** (A 6.6, B 7.7, C 5.0, X 9.8), amplitude **0.07 log**, spacing about 10 px | 5–10 per 100 px; amplitude 0.05–0.09 | warp lines averaged 120–220 px along each strip |
| Slubs | **No distinct slubs (thick knots) can be resolved. Do not add any** beyond the streaks. | — | visual + streak statistics |
| Texture correlation | along the strip 5–10 px (C 31 px); across it 3.5–4.5 px | along 4–30; across 3–5 | autocorrelation falling to 0.3 |
| **Sheen / sparkle** | **4.2 %** of disc pixels are > 3× their local median. These are fibre sparkle, **warm light grey** at stored (0.405, 0.387, 0.367) with chroma (0.367, 0.334, 0.298): tinted by the dye, not white. Density falls toward the limb: 5.1 % → 4.7 % → 4.1 % → 3.2 % over r bands 0–0.3, 0.3–0.6, 0.6–0.8 and 0.8–0.9 R. There is no broad sheen lobe. | fraction 3–5.5 % | `sb_m20` |
| Roughness reading | Matte cloth. There is no specular lobe (the kunai wrap's 0.85–0.9 is the right range). | — | — |

---

## 8. COLOUR AND ALBEDO

| Row | Value | Tolerance | How |
|---|---|---|---|
| **Albedo (luminance, linear)** | **0.043** | ±0.010 | Each region's mean linear luminance, divided by the modelled key + ambient irradiance (§3). The irradiance is scaled so that a perfect white surface facing the key reads 1.0, matching the backdrop's 0.996. If the sweep was lit hotter than the ball, as is common, the true albedo is higher. 0.043 is also the kunai wrap's dark cotton (~0.04), and the kunai sits in the same product line. |
| **Albedo RGB** | linear **(0.0486, 0.0418, 0.0383)** = stored **(0.244, 0.226, 0.216)**, **#3E3A37** | each ±25 % (stored ±0.03) | albedo luminance × measured chromaticity |
| Chromaticity (linear r, g, b fractions) | **(0.378, 0.325, 0.298)**; every region falls within r 0.375–0.386 | r ±0.012, g ±0.008 | 11 regions pooled |
| Hue / saturation (sRGB HSV) | **hue 20.5°** (range 17.5°–23.9°), **saturation 0.13** (0.113–0.160; darker regions read slightly more saturated) | ±4°; ±0.03 | region means |
| **Strip-to-strip variation** | **None beyond lighting.** Chromaticity is identical within 1.5 %. The shading-normalised luminance spread (cv 0.22) follows the lighting model's residual: the left limb reads bright from the rim/fill, and the bottom reads dark. It does not follow the strips. | build: one BC for every strip; per-strip variation ≤ 5 % | 11 regions |
| **Pixel targets (what the viewer sees)** | Stored luminance over the disc (r < 0.9 R): p1 0.017 · p10 **0.050** · p25 0.077 · p50 **0.116** · p75 0.174 · p90 **0.248** · p99 0.437 · p99.9 0.615 | p10, p50 and p90 each ±12 % | measure the build's render (orthographic camera, §3 lights, baked maps) the same way |
| Region means (stored sRGB) | A (0.136, 0.124, 0.117) · B (0.208, 0.193, 0.185) · C (0.160, 0.145, 0.138) · W (0.155, 0.143, 0.135) · X (0.173, 0.158, 0.151) · U (0.207, 0.191, 0.182) · upper-left rim (0.223, 0.206, 0.197) · bottom (0.110, 0.098, 0.093) · top whorl (0.234, 0.216, 0.208) | ±15 % each | 20–95th percentile mean in 22 px discs |

---

## 9. WHAT THE REFERENCE CANNOT SHOW, AND THE DESIGNED FAR SIDE

**Cannot show** (so not measured):
- the far hemisphere;
- the ball's real size;
- the camera elevation and focal length;
- the order of R_in, R2 and R3 against one another;
- the hidden edges of X and A;
- the order of L3 against L4 (low confidence);
- any tape thickness beyond what the outline steps show;
- where the tape's free end lies.

**FAR SIDE: DESIGNED, NOT MEASURED.** It follows the wrapping logic seen on the front.

1. Continue every visible strip along its own path across the back. **Add no strip that cannot be traced from a
   visible one.**
2. **A and W** leave the right limb at 330°–349° heading down-right. Their edges' great circles come back to the
   visible side at **147°–164°**, where they have already passed under R_in and R2 at the upper-left. On the back,
   run A and W from the right limb, under the bottom-back, up over the back, and to the upper-left limb. Each loop
   closes, and the widths stay as measured (±15 %).
3. **The B/C strip** (§4.3) closes its loop across the back, from the right limb at 12°–26° to the lower-left limb
   at 198°–221°. It runs diagonally, widening from 0.173 D at B's end to 0.227 D at C's end.
4. **X** continues under B and W across the back and ends tucked under the bottom family.
5. **The U and R families** pass through the top whorl and run down the back as meridian-like strips. They
   converge on a **bottom whorl** placed 10°–20° behind the bottom outline (sphere ≈ (0.05, −0.97, −0.25)).
6. Keep the front's crossing style on the back: woven, with about half of the belt crossings on top. Keep the step
   height, fray, sparkle, weave and colour identical to the front.
7. If the tape's free end is modelled at all, **tuck it under a strip on the back**. No visible flap, knot, fuse
   or tag, because the front shows none.

Acceptance for the back: a back view must read as the same object. The strips stay 0.04–0.24 D wide, there is a
whorl at each pole, and nothing appears that the front lacks.

---

## 10. ACCEPTANCE CHECKS (measure the render, never the builder's report)

1. Render SM_SmokeBomb **from the baked maps**. Use an **orthographic camera** (1.351 D per frame width) at
   1254 × 1254, the ball centred at (627.4, 628.9), a 0.996 backdrop, and the §3 key, fill and ambient.
2. **Look first.** Overlay the render on the reference at 50 % opacity and flip between them. Any of these
   reading differently is a failure, whatever the numbers say:
   - any strip, or the twisted end of W;
   - either V-gap, or the whorl;
   - T1 or T2;
   - the woven cycle.
3. **Outline** (§1 instrument):
   - circle fit within ±1 % D;
   - rms deviation 0.8–1.8 % R;
   - flat sectors at 30–60° and 180–210°, and a full sector at 120–150°;
   - 8–16 steps ≥ 4 px;
   - nothing past the outline beyond 9 px.
4. **Strips**:
   - every strip in §4.2 is present, at its width within tolerance;
   - each enters and leaves at the listed limb angles ±6°;
   - its control points lie within 10 px (primary edges W, A, B, C: 6 px);
   - every §4.4 row holds in the stated order.
5. **Surface**:
   - disc p10, p50 and p90 of stored luminance within ±12 %;
   - quadrant lighting ratios within ±15 %;
   - warp pitch 3.4–5.5 px at this framing;
   - sparkle fraction 3–5.5 %;
   - chromaticity within §8.
6. **Absent**:
   - no fuse, knot, tag, cord, dirt, scorch, cut, tear or extra wear;
   - no slubs;
   - no third prominent loose thread;
   - no visible free tape end.

---

## 11. Provenance

The scripts are in `WorkFiles/smokebomb/reference_metrology/`. Each is a headless Blender 5.2 run, using
`--factory-startup --python`.

| Stage | Script(s) | Output |
|---|---|---|
| Load | `sb_m00_load` | `sb_ref_srgb.npy` |
| Silhouette | `sb_m01_silhouette`, `sb_m22_silh_fray` | `sb_s1_silhouette.json`, `sb_s22_silh_fray.json` |
| Viewing tools | `sb_m02`, `sb_m03`, `sb_m09`, `sb_m10`, `sb_m11`, `sb_m12`, `sb_m19` | — |
| Orientation / lines / segments | `sb_m04_orient`, `sb_m07_lines`, `sb_m08_segments` | — |
| Profiles | `sb_m06`, `sb_m13`, `sb_m16`, `sb_m17` | — |
| Edge trace | `sb_trace.json` (by-eye reading of 2×–6× views, snapped to the crevice segments; primary edges ±6 px, secondary ±10 px) | — |
| Sphere fits | `sb_sphere.py`, `sb_m18_fit` | `sb_s18_fits.json` |
| Widths and control points | `sb_m23_consolidate` | `sb_s23_bands.json` |
| Lighting and colour | `sb_m20_light_colour`, `sb_m24_light2` | `sb_s20_light_colour.json`, `sb_s24_light2.json` |
| Weave | `sb_m21_weave`, `sb_m27_streaks` | `sb_s21_weave.json`, `sb_s27_streaks.json` |
| Threads | `sb_m26_threads` + the zoom sheets | — |
| Diagram | `sb_m25_diagram` | `debug/DEBUG_NEVER_SHIP_sb_strip_layout_LABELLED.png` |
| Assembly | `sb_m29_assemble` | `reference_spec.json` |
