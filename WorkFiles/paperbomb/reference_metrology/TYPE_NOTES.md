# Paper bomb — typography and stroke metrology

**Role:** measure the drawn forms themselves — glyphs, strokes, the ring, the flame emblem,
the seals — in both reference guides and in our shipped map, and turn "it looks off" into
numbers a later pass can hit and prove.

**Legal / product constraint honoured throughout:** this study reads the reference guides
and emits **numbers and descriptions only**. Nothing here traces, samples, cuts out,
vectorises, thresholds-to-mask or otherwise derives shippable pixels from
`References/PaperBomb/*.png`. The diagrams in `debug/` named `DEBUG-NEVER-SHIP_*.svg` are
drawn from the numbers in `typography.json` onto a blank canvas and contain no reference
imagery.

**Files**

| file | what |
|---|---|
| `typography.json` | curated: conventions, per-element reference numbers, our numbers, 58 deltas worst-first, V1/V2 disagreements, uncertainties |
| `typography_raw.json` | the full unfiltered measurement dump for V1, V2, our shipped atlas and the stale WorkFiles art map |
| `debug/DEBUG-NEVER-SHIP_layout_boxes.svg` | every element box, reference vs ours, on the 70×156 mm card |
| `debug/DEBUG-NEVER-SHIP_ring_profile.svg` | ring thickness and radial ink coverage against angle |
| `debug/DEBUG-NEVER-SHIP_stroke_ladder.svg` | stroke-width span per element, reference vs ours |
| `pbmetro.py`, `pbtag.py`, `pbelem.py`, `stage_*.py` | the instrument |

---

## 0. Conventions, and what I had to correct before measuring

Coordinates: origin at the **tag's** top-left corner (the paper, not the canvas), x right,
y down, quoted as a fraction of the tag's own W and H **and** in millimetres on the shipped
70.0 × 156.0 mm card.

Colour: images are loaded with colourspace `Non-Color`, so every value quoted is the
**stored (sRGB-encoded)** 0–1 value unless the key says `linear`.

Ink binarisation: at the **50% contrast crossing** between the paper level (luma p75 inside
the tag) and the ink floor (luma p0.5). That is the only fair way to compare a guide whose
ink bottoms out at 0.034 against our map whose ink bottoms out at 0.240 — a fixed threshold
would have measured our strokes as systematically thinner than they are.

**Geometric correction applied.** Both guides turned out to be square to the pixel grid, so
almost nothing needed undoing:

| | rotation applied | keystone (vert / horiz convergence) | width taper |
|---|---|---|---|
| V1 | **0.001°** | −0.018° / 0.009° | −0.069% |
| V2 | **0.010°** | 0.023° / −0.019° | 0.093% |
| ours (shipped atlas) | −0.052° | 0.059° / −0.135° | 0.231% |

The four tag sides were fitted with outlier-trimmed least squares (residual RMS 0.07–0.50 px
on V1), the four corners taken as the intersections of those lines, and a homography applied
to that quad. In practice the correction is a scale normalisation, not a de-skew.

**Two corrections that did matter, both on V2** — see §7.

**Which of our maps I measured.** `WorkFiles/paperbomb/art/paperbomb_front_bc.png` is from
**19:30**, but `Scripts/props/props_lib/paperbomb_art.py` was last edited **22:06** and the
atlas re-exported at **22:12** and again at **22:31**. The WorkFiles art maps are **stale and
measurably different** from the shipped map. So every "ours" number below comes from a frozen
snapshot of `Exports/PaperBomb/Textures/T_PaperBomb_BC.png` as of **22:12:49**
(sha256-16 `87230965417121ae`). Its front-card UV island was located from grain/deckle edge
energy: **901.3 × 2015.0 px, aspect 0.4473** against the true 0.4487 — isotropic to 0.3%, so
no anisotropy correction was needed. Three independent thresholds agreed to 1.7 px on width. The build re-exported again at **22:31**; that map was re-measured on every headline metric and is identical to the 22:12 snapshot, so these numbers are current.

---

## 1. Centre character 爆 — the biggest problem, and not the one that was reported

| | V1 (ref) | V2 | ours (shipped) |
|---|---|---|---|
| ink bbox (mm) | 58.46 × 51.89 | 57.41 × 49.98 | **48.01 × 44.21** |
| **w/h** | **1.127** | **1.149** | **1.086** |
| bbox centre (mm) | 36.62, 78.28 | 37.01, 75.45 | 36.20, 78.23 |
| 90%-of-mass box (mm) | 36.29 × 38.41 | 36.51 × 37.12 | 34.11 × 35.77 |
| ink area (mm²) | 1099.5 | 1057.9 | **668.1** |
| fill of bbox | 0.362 | 0.369 | 0.315 |
| connected components | **2** | 2 | **4** |
| stroke max (mm) | 7.33 | 7.20 | 5.21 |
| stroke p95 / p05 (mm) | 5.08 / 0.22 | 5.44 / 0.49 | 4.05 / 1.18 |
| **thick/thin (p95÷p05)** | **22.6** | 11.0 | **3.4** |
| vertical-stroke median (mm) | 4.14 | 4.78 | 3.34 |
| horizontal-stroke median (mm) | 3.59 | 4.12 | 3.72 |
| edge roughness (perim ÷ 0.25 mm-smoothed perim) | **1.296** | 1.148 | **1.048** |
| edge deviation (mm) | 0.0235 | 0.0252 | 0.0089 |

### 1a. "Our 爆 is squat (1.04 w/h against the reference 0.81)" — **REFUTED, and inverted**

The reference 爆 is **wider than it is tall**: **1.127** in V1 and **1.149** in V2 — two
independent rasters agreeing to 2%. There is no measurement of this character, on either
guide, at any sensible ink threshold, that yields 0.81.

Ours is **1.086** — so ours is not squat, it is **not wide enough**: 3.6% too narrow in
proportion, on top of being too small overall. The fix is to *widen* 爆, not to compress it.

### 1b. "About 11% small against the ring" — **CONFIRMED but badly understated**

| against the ring | V1 | V2 | ours |
|---|---|---|---|
| glyph width ÷ ring mean diameter | **1.046** | 1.046 | **0.856** |
| glyph height ÷ ring mean diameter | 0.928 | 0.911 | 0.788 |
| glyph diagonal ÷ ring diameter | 1.399 | 1.387 | 1.164 |
| glyph ink area ÷ ring inner area | **0.548** | 0.536 | **0.315** |
| clear space to ring inner edge, median (mm) | **5.50** | 5.50 | **9.50** |
| clear space, mean (mm) | 5.89 | 6.08 | 9.86 |

It is **18% small on width**, 15% on height, 17% on the diagonal, and **43% down on ink
area inside the ring**. The reference character is *wider than the ring it sits in*
(ratio 1.046) and its sweeps break out past the band; ours is tucked safely inside with
**73% more clear space** all round. That single number — median clear space 5.5 mm, not
9.5 mm — is the most actionable target in this document.

### 1c. The finding nobody reported: **our 爆 has fallen apart**

The reference is **two** components — the 火 radical and the body — and they are all but
joined:

* reference radical box `x 7.39–31.92, y 59.41–98.05 mm` (24.53 × 38.63 mm)
* it **overlaps the body's box by 8.74 mm in x**
* closest ink-to-ink distance: **0.752 mm** (V2 agrees: 8.56 mm overlap, 0.781 mm gap)

Ours is **four** components:

| piece | box (mm) | x-overlap with body | ink gap to body |
|---|---|---|---|
| body | 28.82–60.21 × 56.13–100.33 | — | — |
| radical | 15.38–27.19 × 64.26–96.93 | **−1.63 mm (no overlap)** | **2.359 mm** |
| radical's left flick | 12.20–18.49 × 75.02–83.30 | −10.33 mm | **10.781 mm** |
| broken-off stroke | 47.78–54.54 × 92.13–97.86 | (inside) | 2.483 mm |

So our radical is a **detached island** floating 2.4 mm clear of the body, its own left
flick has snapped off 10.8 mm away, and a stroke has broken out of the body's lower right.
The reference radical is also **half again wider than ours** (24.53 mm vs 11.81 mm) — its
long left sweep is what carries the character out to x = 7.39 mm. Ours stops at 12.20 mm
and does so in a separate blob.

### 1d. "Too vector-smooth" — **CONFIRMED for the centre glyph only**

Edge roughness 1.048 against the reference's 1.296; edge deviation 0.0089 mm against
0.0235 mm. Our 爆's outline is **2.6× smoother** than the reference's. Combined with the
thick/thin ratio collapsing from ≥22.6 to 3.4, our character reads as a fat marker pen
rather than a loaded brush. Note the reference's 0.224 mm p05 is exactly 2 px at V1's
resolution — **22.6 is a lower bound**, the real brush went finer than the guide can show.

---

## 2. Red ring

| | V1 (ref) | V2 | ours (shipped) | ours (stale 19:30 art) |
|---|---|---|---|---|
| centre (mm) | 35.17, 76.71 | 35.33, 74.08 | **36.41, 78.32** | 36.22, 78.45 |
| centre (frac of tag) | 0.502, 0.492 | 0.505, 0.475 | 0.520, 0.502 | 0.517, 0.503 |
| mean mid radius (mm) | 27.79 | 27.28 | 27.75 | 28.23 |
| mean inner / outer radius (mm) | 25.28 / 30.29 | 25.06 / 29.50 | 26.00 / 29.49 | 26.24 / 30.23 |
| ellipse semi-major / semi-minor (mm) | 29.77 / 26.12 | 29.10 / 25.79 | 30.99 / 25.09 | 29.67 / 25.89 |
| axis ratio (minor÷major) | 0.877 | 0.886 | **0.810** | 0.873 |
| eccentricity | 0.480 | 0.463 | 0.587 | 0.488 |
| major-axis tilt off vertical | **5.93°** | 3.21° | **1.77°** | 0.38° |
| **core band thickness, mean (mm)** | **4.50** | 4.15 | **3.13** | 3.50 |
| core thickness median / p05 / p95 | 4.67 / 1.26 / 7.19 | 4.27 / 1.12 / 6.60 | 3.09 / 1.27 / 4.58 | 3.05 / 0.36 / 6.10 |
| core thickness CV | 0.398 | 0.373 | 0.358 | 1.015 |
| **radial ink coverage** | **0.589** | 0.413 | **0.896** | 0.743 |
| angular coverage | 0.964 | 0.958 | 0.946 | 0.924 |
| number of angular gaps | 5 | 5 | 3 | 5 |
| biggest gap | 6.5° (18.3→24.3°) | 6.0° (138.8→144.3°) | 8.5° (−15.8→−7.8°) | 10.5° |
| ring ink area (mm²) | 420.9 | 318.2 | 503.7 | 367.1 |

### 2a. Laps — "three thin concentric laps instead of one fast lap"

I count laps from the **radial occupancy histogram in ellipse-normalised radius**
ρ = r ÷ r_ellipse(θ). One lap gives one hump; concentric laps give separate humps with
clean troughs between them. Dry-brush streaking gives many radial *runs* but still only one
*mode*, which is why a run count alone would have been misleading (the reference shows ≥2
radial runs at 80% of angles and it is unambiguously one lap).

* **V1: 1 mode** at ρ = 0.998, FWHM 0.210 → **brush width 5.84 mm**
* **V2: 1 mode** at ρ = 1.048, FWHM 0.215 → brush 5.87 mm
* **our shipped map: 1 mode** at ρ = 0.998, FWHM 0.135 → **brush 3.75 mm**
* **our stale 19:30 art: 2 modes** at ρ = 0.983 and 1.048, FWHM 0.070 → brush **1.98 mm**

**Verdict: the claim was true of the art the reviewer saw and is already fixed in the
shipped map.** The current ring is a single lap. What remains is that the brush is
**36% too narrow** (3.75 mm against 5.84 mm) and the band is **30% too thin**
(3.13 mm core against 4.50 mm).

### 2b. Wet-to-dry, direction of travel, gaps and overlap

Angles are image-space: 0° = 3 o'clock, +90° = straight **down** (y points down), so
increasing angle is **clockwise on screen**.

* **Reference:** the arc runs from **24.25°** round to **18.25°**, i.e. **clockwise**, one
  full lap, leaving a **6.5° break just below 3 o'clock** and a second 4.0° break at
  138.8–142.3° (lower left). The starting end is the **wetter** one — radial ink coverage
  **0.690** at the start against **0.533** at the finish, a **wet-to-dry contrast of 0.227**.
  Band thickness at the ends is 3.68 mm (start) and 4.77 mm (end): the brush **splays as it
  dries**, getting wider but emptier.
* **Overlap:** there is essentially **none**. Near the break the core band is **0.885×** the
  ring's median thickness — thinner, not doubled — and splits into **2.04 radial runs** on
  average as the dry brush separates. The lap tapers into its own break rather than crossing
  over itself.
* **Ours:** break of 8.5° at −15.8→−7.8° (just *above* 3 o'clock). Coverage **0.767 at the
  start and 0.957 at the end** — our arc ends **wetter** than it starts, the reverse of the
  reference, so the stroke reads directionless. Local thickening near the break is 1.197×,
  i.e. ours *does* bulge slightly where the reference tapers.

### 2c. Ring placement and shape

Ours sits **+1.24 mm right and +1.61 mm down** of the reference centre. Its overall size is
right (mean mid-radius 27.75 mm vs 27.79 mm — within 0.2%), but it is a **more pronounced
oval** (axis ratio 0.810 vs 0.877) that is **almost upright** (1.77° off vertical) where the
reference is visibly **canted 5.93°**. An upright, more elliptical ring is exactly what a
parametric sweep looks like; the reference looks like an arm swung it.

---

## 3. Flame emblem

| | V1 (ref) | V2 | ours |
|---|---|---|---|
| bbox (mm) | 23.41 × 23.36 | 23.92 × 21.84 | **23.46 × 24.70** |
| w/h | 1.002 | 1.095 | 0.950 |
| centre (mm) | 34.78, 30.66 | 34.87, 29.84 | 34.81, 30.31 |
| **ink area (mm²)** | **163.3** | 164.6 | **272.1** |
| fill of bbox | 0.299 | 0.315 | **0.470** |
| **connected components (separate strokes)** | **5** | 5 | **1** |
| tongues in the top 46% | 5 | 5 | 6 |
| **fully enclosed holes** | **0** | 0 | **9** |
| mirror-symmetry IoU about its own axis | 0.795 | 0.801 | **0.669** |
| symmetry verdict | near-symmetric | near-symmetric | hand-asymmetric |
| stroke median / p95 / max (mm) | 1.33 / 2.93 / 3.55 | 1.56 / 3.03 / 3.60 | 0.66 / 4.09 / **7.11** |
| edge roughness | 1.104 | 1.072 | **1.394** |
| empty disc at the heart (eye radius, mm) | **1.25** | 1.24 | **2.78** |
| tongue widths (mm) | 1.79, 6.16, 1.46, 6.50, 1.57 | 2.01, 6.55, 2.01, 6.55, 1.76 | 3.88, 2.33, 5.67, 2.10, 2.10, 4.66 |

Ink runs crossed by a horizontal cut, top to bottom of the emblem
(0.05 / 0.12 / 0.20 / 0.30 / 0.40 / 0.50 / 0.65 / 0.80 / 0.92 of its height):

* **reference V1 and V2, identically:** 2, 2, 2, 2, 5, 5, 7, 4, 1
* **ours:** 1, 1, 2, 4, 7, 9, 7, 3, 1

### "Our flame emblem is about 13% narrow and too vector-smooth" — **BOTH REFUTED**

* **Width matches:** 23.46 mm against 23.41 mm, **+0.2%**. It is the *height* that is wrong,
  +5.7% (24.70 vs 23.36 mm), which makes w/h 0.950 against 1.002 — ours is proportionally
  5% narrow, not 13%.
* **Not smoother — rougher.** Edge roughness 1.394 against the reference's 1.104; edge
  deviation 0.0303 mm against 0.0142 mm. Our emblem's outline is the **noisier** of the two.
* And ours is not more symmetric either: IoU 0.669 against 0.795. **The reference emblem is
  the tidier, more symmetric of the two.**

The real emblem problems are **weight and welding**:

* **67% too much ink** (272 vs 163 mm²), fill 0.470 against 0.299;
* the widest stroke is **twice** the reference's (7.11 vs 3.55 mm);
* the reference is **five separate strokes with paper between them**; ours is **one welded
  mass** that closes **nine** pockets the reference leaves open (the reference's curl stays
  open to the outside — 0 enclosed holes);
* our heart is over twice as hollow (eye radius 2.78 vs 1.25 mm) while the body around it is
  twice as fat, so the emblem reads as a doughnut rather than a spiral.
* the reference's tongue widths alternate **thin–thick–thin–thick–thin**
  (1.79, 6.16, 1.46, 6.50, 1.57 mm): two fat central tongues flanked and separated by
  hairline ones. Ours has no such rhythm.

**Spiral turns — honest uncertainty.** A turn count cannot be automated reliably on an
*open* curl: casting 72 rays from the emblem's eye gives a median of 1 ink band with a tail
to 5 bands (reference) and to 7 (ours). The robust number is the eye radius above. Treat
"turns" as unmeasured; the structural facts (0 enclosed holes reference vs 9 ours,
5 strokes vs 1) are what a rebuild should chase.

---

## 4. The four text columns

Reference numbers are **V2** (authoritative for which characters go where); V1 is shown
because its side columns are pseudo-glyphs and its geometry is *not* a target.

### 火遁術 (upper left)

| | V2 (ref) | ours | V1 (pseudo-glyph) |
|---|---|---|---|
| column box (mm) | 14.60 × 41.73 | **9.95 × 38.87** | 8.74 × 63.68 |
| at x | 5.79 – 20.40 | **10.41 – 20.36** | 6.61 – 15.34 |
| at y | 10.19 – 51.92 | 11.23 – 50.09 | 10.45 – 74.12 |
| axis x (mm) | **13.303** | **15.357** | 10.444 |
| lean off vertical | −0.793° | +0.151° | −1.865° |
| advances (mm) | 12.74, 14.68 | 15.17, 14.67 | — |
| **gaps between cells (mm)** | **0.00, 0.24** | **5.81, 5.96** | 1.69 |
| cell sizes (mm) | 13.35×12.62, 13.60×12.86, 14.60×16.01 | 9.63×9.68, 9.95×9.06, 9.01×8.36 | — |
| cell w/h | 1.058, 1.057, 0.912 | 0.996, 1.098, 1.078 | — |
| cell ink (mm²) | 49.9, 67.2, 80.9 | 24.9, 26.1, 22.8 | — |
| cell stroke median (mm) | 1.48, 1.11, 1.48 | 1.09, 0.78, 0.62 | — |

### 爆炎陣 (upper right)

| | V2 (ref) | ours | V1 (pseudo) |
|---|---|---|---|
| column box (mm) | 15.36 × 42.22 | **10.49 × 39.41** | 11.54 × 63.68 |
| at x | 49.10 – 64.46 | **49.88 – 60.37** | 54.21 – 65.74 |
| axis x (mm) | **57.116** | **54.798** | 60.340 |
| lean | +0.209° | −0.826° | +1.280° |
| advances (mm) | 13.22, 14.44 | 14.90, 14.79 | — |
| **gaps (mm)** | **0.00, 0.00** | **5.27, 4.88** | 1.46 |
| cells (mm) | 15.36×13.34, 11.58×13.10, 12.09×15.77 | 10.49×9.45, 8.16×9.83, 8.70×9.99 | — |
| cell ink (mm²) | 86.1, 56.7, 70.2 | 30.8, 22.9, 26.3 | — |

### 焼尽 (lower right) and 瞬業 (lower centre)

| | 焼尽 V2 | 焼尽 ours | 瞬業 V2 | 瞬業 ours |
|---|---|---|---|---|
| box (mm) | 14.60 × 26.69 | 12.43 × 23.61 | 13.60 × 31.78 | 12.74 × 28.72 |
| at x | 49.86 – 64.46 | 51.59 – 64.02 | 28.20 – 41.80 | 28.82 – 41.57 |
| at y | 98.74 – 125.43 | 98.32 – 121.94 | 109.42 – 141.20 | 111.33 – 140.05 |
| axis x (mm) | 57.347 | **57.783** | 35.000 | **34.961** |
| lean | −1.594° | −0.168° | −3.630° | −1.686° |
| advance (mm) | 13.59 | 12.93 | 15.89 | 15.83 |
| **gap (mm)** | **0.49** | **2.25** | **0.00** | **2.94** |
| cells (mm) | 13.35×12.86, 14.60×13.34 | 12.43×11.46, 10.95×9.91 | 12.59×14.80, 12.59×16.98 | 12.74×13.16, 11.19×12.62 |

### "Our columns are pulled about 3 mm inboard" — **CONFIRMED for the two upper columns, refuted for the two lower ones**

| column | axis shift vs V2 | axis shift vs V1 | outer-edge shift vs V2 |
|---|---|---|---|
| 火遁術 (UL) | **+2.05 mm inboard** | +4.91 mm inboard | left edge **+4.62 mm inboard** |
| 爆炎陣 (UR) | **−2.32 mm inboard** | −5.54 mm inboard | right edge **−4.09 mm inboard** |
| 焼尽 (LR) | +0.44 mm *outboard* | — | right edge −0.44 mm |
| 瞬業 (LC) | −0.04 mm (spot on) | — | — |

So "about 3 mm" is right in spirit for the top two and wrong for the bottom two. And the
axis number **understates what the eye sees**: because our column glyphs are ~32% narrower,
the columns' **outer edges** have moved in by **4.1–4.6 mm**, which is what makes the top of
the card look hollowed out.

### The bigger column problem: size and leading

Across all four columns our glyph cells are **~30% smaller** and carry **50–64% less ink**
than V2's, and they are set with **2.2–6.0 mm gaps where the reference's characters touch
(0.00–0.49 mm)**. The reference sets a column as a continuous vertical stream of ink; ours
sets it like body text with generous leading. Advances are close (12.9–15.8 mm ours vs
12.7–15.9 mm reference) — so the pitch is right and the **glyphs inside the pitch are too
small**. Grow the glyphs to fill the advance and the gaps close by themselves.

Column lean is also flattened: V2's 瞬業 column leans **−3.63°** off vertical and 焼尽
**−1.59°**; ours lean −1.69° and −0.17°. Our columns are more mechanically upright.

---

## 5. Seals

### Big seal (lower left, red block with reversed-out flame)

| | V1 (ref) | V2 | ours |
|---|---|---|---|
| outer frame (mm) | **17.81 × 26.50** | 17.63 × 25.96 | **20.20 × 29.42** |
| at x / y (mm) | 6.16–23.97 / 116.35–142.86 | 6.29–23.92 / 116.94–142.90 | 4.89–25.09 / 115.20–144.62 |
| structure | **outline rectangle + inset solid block** | (block only at this resolution) | **one mass, no inset block** |
| outline rule thickness (mm) | **1.071** | — | — |
| inner solid block (mm) | **13.66 × 22.12** | — | — |
| inset, frame → block (mm) | **2.07 across, 2.19 down** | — | — |
| block ink fill | **0.718** (i.e. 28% broken out) | 0.757 | 0.480 |
| red fill of whole outer box | 0.643 | 0.657 | **0.482** |
| central-60% red fill | 0.567 | 0.564 | 0.583 |
| device (reversed-out flame) area (mm²) | 88.6 | 155.4 | 220.1 |
| device as fraction of the seal's red | **0.292** | 0.517 | **0.768** |
| device stroke median / p95 / max (mm) | 0.22 / 2.05 / 3.17 | 0.99 / 1.98 / 3.16 | 1.55 / 2.17 / 3.41 |
| corner fill (tl, tr, bl, br) | 0.50, 0.58, 0.56, 0.44 | 0.69, 0.81, 0.56, 0.56 | 0.61, 0.59, 0.51, 0.22 |
| corner treatment | partly broken | partly broken | broken / open (br worst at 0.22) |

**Reference construction, precisely:** a **17.81 × 26.50 mm outline rectangle drawn with a
1.07 mm rule**, and **inside it, inset 2.07 mm across and 2.19 mm down, a solid red block
13.66 × 22.12 mm**. The block is **72% inked** — the missing 28% is the reversed-out flame
plus genuine wear speckle. Corners are **partly broken**, none of the four closing fully
(0.44–0.58 fill), which is what makes it read as a stamped chop rather than a drawn box.

**Ours:** one 20.20 × 29.42 mm mass with **no separate outline and no inset block** — the
frame and the fill have merged. It is **13.4% wider and 11.0% taller** than the reference's
outer rectangle, prints thinner overall (red fill 0.482 vs 0.643), and its bottom-right
corner is essentially absent (0.22).

The reversed-out flame device is the same broad-stroke size in both (p95 2.17 vs 2.05 mm)
but the reference's median device stroke is 0.22 mm against our 1.55 mm — the reference's
white flame is broad strokes **plus a scatter of hairline wear filaments**; ours is broad
strokes only.

### Small seal (lower right, 火道)

| | V1 (ref) | V2 | ours |
|---|---|---|---|
| outer frame (mm) | **8.85 × 17.75** | 9.82 × 16.74 | **10.72 × 21.91** |
| at x / y (mm) | 54.66–63.50 / 123.09–140.84 | 54.89–64.71 / 130.28–147.02 | 53.76–64.48 / 122.71–144.62 |
| frame rule thickness (mm) | **0.691** | — | **0.450** |
| red fill of box | 0.449 | 0.395 | **0.173** |
| 火 cell (mm) | **6.50 × 6.18** at y 124.55–130.73 | — | **4.74 × 4.80** at y 126.27–131.07 |
| 道 cell (mm) | **6.61 × 7.41** at y 131.97–139.38 | — | **5.44 × 4.80** at y 134.40–139.20 |
| advance 火→道 (mm) | 8.1 | — | 8.14 |
| **gap between them (mm)** | **1.24** | — | **3.33** |

The text inside is the same story as the big columns: **the pitch is right (8.1 mm both) and
the characters are ~27% too small inside it**, so the gap nearly triples. Our box is
**21% wider and 23% taller** than the reference's while its rule is **35% finer**
(0.450 vs 0.691 mm) — a bigger, weaker box around smaller text.

---

## 6. Border rule (measured because it sets where the columns can go)

| | left x | right x | top y | bottom y | rule thickness (mm) |
|---|---|---|---|---|---|
| V1 | 4.368 | 65.464 | 6.851 | 148.082 | 0.672 / 0.672 / 0.505 / 0.618 |
| V2 | 4.281 | 65.468 | 6.672 | 147.751 | 0.755 / 0.504 / 0.485 / 0.485 |
| ours | **3.263 + 3.923** | 65.999 | **6.426 + 7.006 + 9.406** | **145.510 + 148.490** | 0.155 + 0.544 / 0.855 / 0.619+0.155+0.465 / 0.155+0.387 |

The reference frame is **one rule per side**, about **0.5–0.67 mm** thick, on the rectangle
`x 4.37 → 65.46, y 6.85 → 148.08 mm` (61.10 × 141.23 mm, sitting 0.08 mm left and 0.53 mm
above the card's centre). Our build draws **two parallel rules on the left, three across the
top and two along the bottom**, and is asymmetric side to side (0.544 mm left rule against a
0.855 mm right rule). Our frame rectangle is 62.08 × 142.06 mm — 1.6% wider and 0.6% taller.

---

## 7. Where V1 and V2 disagree, with numbers, and which to follow

1. **Raster aspect.** V1's tag is 624.9 × 1388.5 px, **aspect 0.4500** — true to the 70/156
   card (0.4487) within 0.3%. V2's is 278 × 643 px, **aspect 0.4323**: V2 is a **non-uniform
   resize, stretched 3.8% vertically** (3.971 px/mm across, 4.122 px/mm down).
   **Follow V1** for anything about aspect. Fractions of the tag are unharmed — a resize
   preserves them, and the big seal lands within 0.004 of V1's fractions, which is how I
   verified it — but any pixel-space ratio read off V2 is 3.8% wrong. Every V2 number in
   this study already uses its two separate scales.
2. **V2 is clipped at the bottom.** Its last canvas row (652) still holds 75.3% of full tag
   width; matching that against V1's bottom chamfer profile puts the true bottom edge about
   **2.3 px (0.55 mm)** below the canvas. V2's tag height is therefore ~0.36% short and all
   its y-fractions ~0.4% large. **Follow V1** for the card's outline.
3. **The side columns.** V1's are pseudo-glyphs: the upper-left column runs 63.68 mm
   (y 10.45–74.12) and is only 8.74 mm wide, and V1 carries an **extra lower-left mark group**
   at `x 7.28–15.90, y 100.07–114.11 mm` that V2 drops. V2's 火遁術 is three 13–15 mm cells
   over y 10.19–51.92 mm. **Follow V2** — V1's column extent is filler.
4. **The small 火道 seal moved.** V1 puts it at `x 54.66–63.50, y 123.09–140.84`; V2 at
   `x 54.89–64.71, y 130.28–147.02` — **6.6 mm lower and 1.2 mm right**, and only 0.5 mm
   clear of the border rule. **Follow V1**: it already carries real 火道 kanji there, so V2's
   edit added no text information for this element, and V1 has 2.2× the resolution.
5. **Lower-centre column height.** V1's ink runs y 112.42–145.22; V2's y 109.42–141.20 —
   **3.4 mm higher**. **Follow V2** (text placement is its remit); both put the diamond
   ornament below it at y 145.3–149.0 mm.
6. **Flame emblem height.** V1 23.41 × 23.36 mm, V2 23.92 × 21.84 mm — 6.5% shorter in V2.
   **Follow V1**: the widths agree within 2% and the ink **areas** agree within 0.8%
   (163.3 vs 164.6 mm²), which proves it is V2's coarser raster losing the thin tongue tips,
   not an edit.
7. **Stroke modulation.** The centre glyph's thick/thin ratio measures 22.6 on V1 and 11.0 on
   V2, because each is floored by its own pixel grid (both p05 values are exactly 2 px).
   **Follow V1, and treat 22.6 as a lower bound.** Never quote V2's 11.0 as a target.

---

## 8. Verdicts on the four prior claims

| claim | verdict | the numbers |
|---|---|---|
| "our ring is three thin concentric laps instead of one fast lap" | **was true, now fixed — but the brush is too narrow** | shipped map: **1** radial mode, brush FWHM **3.75 mm**. Stale 19:30 art: **2** modes, brush **1.98 mm**. Reference: **1** mode, brush **5.84 mm**, band 4.50 mm vs our 3.13 mm |
| "our 爆 is squat (1.04 w/h vs reference 0.81)" | **REFUTED, and inverted** | reference w/h **1.127** (V1) and **1.149** (V2); ours **1.086**. Ours is too *narrow*, not squat. Widen it |
| "our 爆 is about 11% small against the ring" | **CONFIRMED, understated** | width ÷ ring diameter **0.856 vs 1.046 = 18% small**; ink area ÷ ring inner area **0.315 vs 0.548 = 43% down**; clear space **9.50 mm vs 5.50 mm** |
| "our flame emblem is ~13% narrow and too vector-smooth" | **BOTH REFUTED** | width **23.46 vs 23.41 mm (+0.2%)**; edge roughness **1.394 vs 1.104** — ours is *rougher*. The real faults are **+67% ink**, **1 welded component vs 5**, **9 enclosed holes vs 0**, widest stroke **7.11 vs 3.55 mm** |

Bonus findings the prior reviews missed, in severity order: **our 爆 has broken into four
pieces** with a detached radical (2.36 mm ink gap, and a flick 10.78 mm adrift) where the
reference is two overlapping pieces 0.75 mm apart; **our column characters are ~30% too
small** and set with 2.2–6.0 mm gaps where the reference's touch; **the big seal has lost its
outline-plus-inset-block construction**; and **the WorkFiles art maps are stale** relative to
the shipped texture, so any review based on them is reviewing the wrong artwork.

---

## 9. Method notes (so the numbers can be re-derived or challenged)

* Connected components: run-length + union-find, 8-connected.
* Stroke widths: exact Euclidean distance transform (Felzenszwalb–Huttenlocher, separable,
  vectorised over lines), stroke width = 2× the distance on ridge pixels (local maxima of the
  distance transform). Cross-checked against a ribbon estimate 2·area/perimeter and against
  run-length histograms taken along rows (vertical strokes) and columns (horizontal strokes).
  All three agree within ~10% on the reference.
* Edge roughness: perimeter ÷ perimeter after an open+close at a fixed **physical** radius of
  0.25 mm, so images of different resolution are compared on equal terms; plus a mean edge
  deviation in mm.
* Ring: centre and ellipse from an iterated fit to the band's **midline** (per-angle median
  radius), not to the filled band, so a one-sided dry patch cannot drag the centre. Thickness
  reported three ways — full radial extent, p05→p95 "core" extent, and actual inked extent —
  because on a dry-brush band those differ a lot and only the core one is stable.
* Column cells: projection-profile gap split where the glyphs separate; where they touch
  (all of V2's columns do), a dynamic programme cuts the column into exactly the known number
  of cells at the lightest rows, with a minimum cell size of 0.55 × (height ÷ n).
* Seals: pieces are kept separate (an outline rectangle can lie *outside* the solid block's
  box, so the absorption radius is 3 mm), and an outline's rule thickness is solved from
  `ink area = 2·s·(W+H) − 4·s²`.
* One real bug found and fixed mid-study, worth knowing about: a deep seal red is **darker**
  than a sensible black threshold, so classifying black first loses it between the two masks.
  Red must win. Before the fix, V1's red coverage measured 0.060; after, 0.109, and the big
  seal's fill went from 0.173 to 0.643.
