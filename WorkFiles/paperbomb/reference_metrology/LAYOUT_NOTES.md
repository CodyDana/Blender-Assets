# PaperBomb — LAYOUT metrology of the reference

Measured 2026-09-19. Machine-readable companion: `layout.json` (same folder).
Debug overlays: `debug/DEBUG_NEVER_SHIP_*.png` — **DEBUG - NEVER SHIP**.

## What this is, and what it is not

This is a *measurement* of the two guide images. No pixel of either guide is
traced, sampled, masked, vectorised or otherwise carried into anything a build
consumes. Everything below is numbers and prose descriptions. The shipped art
stays our own procedural drawing; that is what keeps the asset clear of Fab's
CreatedWithAI flag.

## Conventions

* **Origin** = the TAG's top-left *virtual* corner (the intersection of the
  fitted top and left edge lines, i.e. the corner the chamfer cuts off), x to
  the right, y down. Not the image canvas.
* **fW / fH** = fraction of the tag's own width / height.
* **mm** = millimetres on the shipped 70.0 × 156.0 mm card.
* Canonical measuring space is 980 × 2184 px = 14 px/mm; 1 px = 0.0714 mm.
* All colour values are **STORED (file) values**, i.e. sRGB-encoded 0..1 as the
  PNG holds them — *not* linear. Read in Blender with
  `colorspace_settings.name = 'Non-Color'` so no transform is applied.
* Tooling: Blender 5.2 headless + NumPy 2.3.4. Scripts in this folder
  (`lib_metro.py`, `lib_tag.py`, `measure2.py`).

## Rectification applied

Both guides are effectively square to the pixel grid; nothing needed straightening
beyond a fraction of a degree, but the correction was computed and applied anyway.

| | V1 | V2 | OURS (T_PaperBomb_BC.png) |
|---|---|---|---|
| left edge off vertical | +0.0195° | +0.0272° | +0.0312° |
| right edge off vertical | −0.0087° | −0.0150° | +0.0850° |
| top edge off horizontal | +0.0304° | −0.0011° | +0.0922° |
| bottom edge off horizontal | −0.0268° | −0.0091° | +0.0235° |
| net rotation | −0.0036° | −0.0112° | −0.0003° |
| keystone (bottom−top width) | −0.11 % | −0.17 % | +0.21 % |
| keystone (right−left height) | −0.045 % | −0.006 % | −0.053 % |

Method: least-squares fit of the four straight edge runs, **then a sub-pixel
refinement** that finds the 50 % luminance crossing between the ground outside
the tag and the paper just inside it, per scanline; the four refined lines are
intersected for virtual corners and that quad is perspective-warped onto
980 × 2184. The refinement matters: the naive binary mask over-reads V1's width
by 5.3 px (0.85 %) because it swallows the soft edge on both sides, which is
exactly the error that would have made V1 look like the wrong aspect.

## 1. Tag outline

| | V1 | V2 | OURS | card |
|---|---|---|---|---|
| tag size (source px) | 622.03 × 1385.78 | 278.03 × 639.46 | 891.23 × 2004.43 | — |
| aspect W/H | **0.44887** | 0.43478 | 0.44463 | 0.44872 |
| error vs card | **+0.03 %** | −3.11 % | −0.91 % | — |

**V1 reproduces the 70 × 156 mm card to within 0.03 %.** Use V1 for every
proportion. V2 is 3.1 % taller per unit width — see §9.

Edge quality (V1): residual rms 0.024–0.042 mm, worst single deviation 0.128 mm,
0–5 samples beyond 3σ. **The edges are clean straight cuts — no tears, no
nicks, no deckle.** Do not add edge damage to the silhouette; V1 has none.

### Corner clips

Straight 45° bevels, all four corners.

| corner | cut along top/bottom edge | cut along side edge | chord | angle | straightness rms |
|---|---|---|---|---|---|
| V1 TL | 7.76 mm | 8.30 mm | 11.37 mm | 46.9° | 0.09 mm |
| V1 TR | 8.65 mm | 8.01 mm | 11.79 mm | 42.8° | 0.64 mm |
| V1 BL | 8.38 mm | 8.88 mm | 12.21 mm | 46.7° | 0.06 mm |
| V1 BR | 8.65 mm | 8.99 mm | 12.47 mm | 46.1° | 0.10 mm |
| V2 TL / TR / BL / BR chords | 11.25 / 11.35 / 12.49 / 10.94 mm | | | 43.4–48.0° | |

Chord spread 9.3 % (V1), 13.4 % (V2) — hand-drawn jitter, not a design feature.
**Recommended target: a straight 45° bevel cutting 8.6 mm off each edge
(chord 12.2 mm, 0.1229 W / 0.0551 H), identical at all four corners.** The
bottom pair measures ~5 % larger than the top pair in both guides; that is
within the noise, but if you want to honour it, use 8.3 mm top / 8.9 mm bottom.

## 2. Red border system — ONE rule per side

Verified two ways (peak-grouped scanline runs, and a red-occupancy profile
across the border band): **V1 and V2 have exactly one rule on each side. There
is no inner rule, no double frame.** The only other red lines inside the border
band belong to the two seal boxes.

| side | inset from tag edge | inset (fraction) | stroke median | p10 / p90 | max | wobble rms | breaks | longest break | coverage |
|---|---|---|---|---|---|---|---|---|---|
| V1 left | **4.214 mm** | 0.06020 W | **0.714 mm** | 0.357 / 0.929 | 1.286 | 0.051 mm | 12 | 3.00 mm | 0.91 |
| V1 right | **4.429 mm** | 0.06327 W | 0.643 mm | 0.286 / 0.929 | 1.071 | 0.024 mm | 12 | 3.00 mm | 0.91 |
| V1 top | **6.786 mm** | 0.04350 H | 0.571 mm | 0.071 / 1.000 | 1.429 | 0.078 mm | 10 | 1.86 mm | 0.92 |
| V1 bottom | **7.786 mm** | 0.04991 H | 0.714 mm | 0.286 / 0.929 | 1.929 | 0.061 mm | 7 | 3.93 mm | 0.84 |
| V2 left / right / top / bottom | 4.214 / 4.536 / 6.643 / 7.643 mm | | 0.857 / 0.714 / 0.857 / 0.786 mm | | | | | | |

Notes that matter for the redraw:

* **The frame is not a uniform inset.** Sides sit 4.2–4.4 mm in; top and bottom
  sit 6.8–7.8 mm in. Vertical inset ≈ 1.6 × the horizontal inset.
* **The frame is not centred on the tag.** Frame inner area 61.36 × 141.43 mm,
  its centre at (34.89, 77.50) mm vs the tag centre (35.0, 78.0) — 0.11 mm left
  and 0.50 mm up.
* **The rules are straight, not wobbled.** Centre-line wobble rms is
  0.024–0.078 mm, i.e. under a tenth of the stroke width. What varies is the
  *width*, not the path.
* **The width modulation is extreme and is the whole character of the stroke.**
  The top rule runs p10 = 0.071 mm to p90 = 1.000 mm — a 14× swing. It thins to
  a near-invisible hairline across mid-span and fattens toward the corners. The
  side rules run 2.6–3.2×.
* **Dry-brush breaks:** 7–12 per side, the longest 1.9–3.9 mm. 8–16 % of each
  rule's length is bare paper.
* **Colour shifts along the rule.** Near the corners the rule is bright
  vermilion; across mid-span it darkens to near-black maroon (it classifies as
  black ink by luminance: a 16.2 mm × 0.5 mm dark segment at y = 6.4–6.9 mm on
  the top rule). Model the rule as a pigment load that runs out, not a flat fill.
* **Beads on the rules:** local width bulges to 2.5–2.8 mm (3.9 × the rule
  stroke), 0.9–1.5 mm long, at 8.7 mm and 144.6 mm along the side rules and at
  7.8 / 61.6 mm along the bottom rule — these are the flourish junctions, not
  mid-span ornaments. V2 reproduces all nine within 0.5 mm.

## 3. Corner flourishes

Shape (from the high-resolution zooms): the two rules run past each other at the
corner; at the junction there is a **hook that curls inboard** (a comma / spiral
turning down-and-in), and a separate **tapered dart** aimed diagonally outboard
at the chamfered corner. Ink pools darkest where the two rules cross.

| | bbox | ink | stroke median / p90 | run along horiz rule | run along vert rule | outboard of side rule | outboard of horiz rule | max reach from rule corner |
|---|---|---|---|---|---|---|---|---|
| V1 TL | 11.86 × 15.71 mm | 50.4 mm² | 1.50 / 3.43 mm | 10.93 mm | 13.36 mm | 0.86 mm | 2.29 mm | 17.00 mm |
| V1 TR | 11.86 × 15.64 mm | 45.2 mm² | 1.36 / 3.21 mm | 11.29 mm | 13.36 mm | 0.50 mm | 2.21 mm | 16.86 mm |
| V1 BL | 17.43 × 14.57 mm | 41.5 mm² | 1.50 / 3.26 mm | 16.71 mm | 12.43 mm | 0.64 mm | 2.07 mm | 20.83 mm |
| V1 BR | 11.50 × 14.64 mm | 28.9 mm² | 0.79 / 3.07 mm | 10.93 mm | 12.43 mm | 0.50 mm | 2.14 mm | 16.50 mm |

Key fact: **the ornament always pokes outboard of both rules** — 0.5–0.9 mm past
the side rule and 2.1–2.3 mm past the top/bottom rule, at every corner, in both
guides. The flourish stroke is ~2× the rule stroke at its median and swells to
3.1–3.4 mm.

## 4. Red ring (ensō)

| | V1 | V2 | OURS |
|---|---|---|---|
| centre | **(35.26, 76.85) mm** | (35.26, 74.16) | (36.43, 78.46) |
| outer radius median | **30.36 mm** | 29.64 | 29.10 |
| outer radius p10 / p90 | 28.41 / 32.67 | 28.41 / 31.43 | 27.13 / 33.16 |
| outer radius min / max | 26.81 / 36.43 | 27.70 / 35.63 | 26.06 / 34.36 |
| outer radius sd (raggedness) | 1.85 mm | 1.25 | 2.30 |
| inner radius median | 25.10 mm | 24.48 | 26.16 |
| **stroke thickness median** | **5.31 mm** | 5.09 | **3.54** |
| thickness p10 / p90 / max | 3.17 / 7.22 / 10.10 | 3.48 / 6.75 / 10.35 | 2.08 / 4.83 / 5.98 |
| angular coverage | 0.98 | 0.98 | 0.96 |
| **ink fill of its own annulus** | **0.66** | 0.74 | **1.01** |
| ellipticity / major axis | 6.7 % @ 86° | 5.0 % @ 83° | 10.7 % @ −89° |
| gap to left / right rule | 1.86 / 1.79 mm | 1.79 / 1.68 | 5.86 / 2.86 |

Read that fill number carefully: **a third of the reference ring's annulus is
bare paper.** It is a single fast dry brush stroke, 60.7 mm across the outside
(0.867 W), whose thickness swings between 3.2 and 10.1 mm, whose outer edge
wanders ±1.85 mm, and which is 6.7 % taller than wide. It very nearly touches
the side rules (1.8 mm clear on both sides — symmetric).

## 5. Content elements

Positions are bounding boxes and ink centroids. V2 is authoritative for *which
glyph is where* and for glyph block size (V1's side columns are pseudo-glyphs,
not characters); V1 is authoritative for everything vertical and for ink detail.

| element | V1 box (fW, fH) | V2 box (fW, fH) | V1 size mm | V2 size mm | V1 centroid mm |
|---|---|---|---|---|---|
| flame emblem | x .329–.663, y .121–.270 | x .327–.666, y .119–.260 | 23.5 × 23.4 | 23.9 × 22.1 | (34.7, 30.9) |
| red ring | x .087–.911, y .283–.759 | x .086–.911, y .274–.759 | 57.8 × 74.4 | 57.9 × 75.7 | — |
| centre 爆 | x .102–.944, y .335–.668 | x .115–.937, y .323–.646 | **59.0 × 52.1** | 57.6 × 50.4 | (36.0, 77.9) |
| 火遁術 upper-left | x .092–.217, y .066–.474 | **x .080–.295, y .064–.334** | 8.9 × 63.7 | **15.1 × 42.2** | (10.4, 35.8) |
| 爆炎陣 upper-right | x .776–.903, y .068–.474 | **x .701–.918, y .060–.332** | 9.0 × 63.5 | **15.3 × 42.5** | (59.6, 36.1) |
| 焼尽 lower-right | x .771–.902, y .644–.777 | **x .711–.918, y .634–.805** | 9.2 × 20.8 | **14.6 × 26.9** | (59.3, 111.8) |
| 瞬業 lower-centre | x .443–.568, y .721–.957 | **x .402–.595, y .704–.908** | 8.9 × 36.9 | **13.6 × 31.9** | (35.0, 127.7) |
| seal box large (left) | x .113–.309*, y .760–.893* | same within 0.2 mm | **18.0 × 26.5** | 18.0 × 26.3 | (15.0, 127.3) |
| seal box small (right) | x .781–.908, y .789–.894 | x .781–.943, y .838–.965 | **9.0 × 17.9** | 11.4 × 18.1 | (59.2, 132.2) |

\* seal fractions are for the inner panel; the outer box size in mm is the merged
outer border, which is what the table's mm column reports.

### The proportions that actually define the look

* **爆 width ÷ ring outer diameter = 0.972 (V1), 0.971 (V2).** The character is
  as wide as the circle. Its bbox diagonal ÷ ring diameter = 1.296, i.e. it
  *bursts out* of the ring at the corners.
* 爆 ink centroid sits (+0.77, +1.05) mm from the ring centre.
* 爆 overlaps the right rule by 0.50 mm and leaves 2.93 mm to the left rule.
* Column glyph em ≈ **15.1 mm**; pitch in a 3-glyph column ≈ **14.1 mm** (the
  glyphs nearly touch).
* Column clear space to its own rule: 1.36 mm (V2 left), 1.18 mm (V2 right).
  The columns hug the frame.
* Flame emblem clear of both rules by 18.6–19.1 mm, ring top 2.0–2.2 mm below it.
* Large seal: a **solid filled red panel** with a paper-coloured flame knocked
  out of it — 43 % of its bbox is knockout — inside a double border whose
  strokes read 1.21 mm (thin outer) and 4.07 mm at p90 (thick inner). Clear of
  the left rule by 1.64 mm.
* Small seal: an **outline box** (58 % knockout), border stroke 0.79 mm, clear of
  the right rule by 2.00 mm.

## 6. Diamonds / lozenges and the centre chain

V1, on or near the vertical centreline, top to bottom:

| what | position | size |
|---|---|---|
| (nothing above the top rule) | — | — |
| red leaf, above 瞬業 | (35.0, 111.5) mm | 1.79 × 2.79 mm |
| two small red leaves flanking the column | (32.1, 130.2) and (37.9, 130.1) | 1.07 × 1.57 / 1.21 × 1.93 mm |
| large black lozenge with a drawn-out tail | inside the 瞬業 column box, which runs to y = 149.3 mm | — |
| black diamond sitting on the bottom rule | (34.9, 147.4) mm | 2.36 × 3.64 mm |
| red leaf below the bottom rule | (34.9, 151.1) mm | 0.79 × 2.57 mm |

Off-centreline red leaf accents flanking the ring: (11.9, 101.1) mm
1.86 × 2.43 mm and (59.6, 99.6) mm 1.79 × 2.50 mm.

V2 agrees on all of these and resolves the chain as three separate centreline
marks below 瞬業: red 143.7, black 147.6, red 151.1 mm.

**There is no ornament above the top rule in either guide.**

The lozenges are not rhombi: they are leaf/spindle shapes, w/h ≈ 0.31–0.71, with
the widest row at roughly mid-height, and a fill of 0.49–0.61 of their bbox
(i.e. genuinely pointed at both ends).

## 7. Composition and optical centring

| | content bbox (mm) | bbox centre offset | ink centroid offset | margins L/R/T/B | ink balance L−R | ink balance T−B |
|---|---|---|---|---|---|---|
| V1 | 3.3–66.1 × 4.5–152.6 | (−0.32, +0.54) mm | (−1.16, +1.11) mm | 3.29 / 3.93 / 4.50 / 3.43 | **+3.0 %** | −2.1 % |
| V2 | 0.5–66.1 × 4.4–152.5 | (−1.71, +0.46) mm | (−0.20, −1.34) mm | 0.50 / 3.93 / 4.43 / 3.50 | −1.3 % | +5.0 % |
| OURS | 2.9–67.1 × 2.5–153.3 | (+0.04, −0.11) mm | (+0.32, +0.79) mm | 2.93 / 2.86 / 2.50 / 2.71 | **−9.1 %** | −5.0 % |

The reference composition is **very slightly left-weighted and bottom-weighted**:
its ink centroid sits 1.16 mm left of and 1.11 mm below the tag centre. Its
bounding box is near-centred (0.3 mm left, 0.5 mm low). This is an optical
balance, not an error — the large filled seal in the lower left is offset by the
sparser lower right.

## 8. Ink levels (stored sRGB, not linear)

| | paper | black ink | red ink | red % | black % | total ink % |
|---|---|---|---|---|---|---|
| V1 | (0.952, 0.871, 0.733) | (0.079, 0.082, 0.066) | (0.735, 0.176, 0.117) | 11.8 | 16.4 | **28.2** |
| V2 | (0.943, 0.858, 0.723) | (0.097, 0.098, 0.080) | (0.809, 0.215, 0.153) | 12.6 | 17.9 | 30.5 |
| OURS | (0.837, 0.762, 0.636) | (0.279, 0.272, 0.261) | (0.728, 0.337, 0.295) | 10.6 | 11.8 | **22.4** |

## 9. Where V1 and V2 disagree

1. **Tag aspect — the big one.** V1 0.44887, V2 0.43478: V2 is 3.1 % taller per
    unit width. V2's tag is fully inside its canvas (the ground is visible for
    2–3 rows below it, edges located at x 12.56 / 290.83, y 9.45 / 649.42), so
    this is not a crop artifact. The frame occupies the same fraction of the tag
    in both (inner box 0.8765 W × 0.9066 H in V1, 0.8750 W × 0.9084 H in V2), so
    the frame was not moved — the whole composition was rescaled non-uniformly.
    But it is not *only* a rescale: individual elements also changed height as a
    fraction of the tag (flame emblem 0.149 H in V1 vs 0.141 H in V2, −5.6 %;
    small seal centroid 4.4 % H lower in V2). V2 is best read as a regenerated /
    inpainted variant of V1, not a pixel edit of it.
    **Follow V1 for every proportion and every mm conversion.**
2. **Side column width and height.** V1's side columns are pseudo-glyph
    scribbles: 8.9–9.2 mm wide, 63.5–63.7 mm tall (more marks than characters).
    V2's are the real kanji: 14.6–15.3 mm wide, 26.9–42.5 mm tall.
    **Follow V2** — V1's columns are not text.
3. **Small right seal (火道) vertical position.** V1 centroid y = 132.2 mm,
    V2 = 139.1 mm — 6.9 mm apart, far more than V2's 3 % stretch explains.
    **Follow V1** (higher resolution, correct aspect). Flagged as a genuine
    content difference between the two generations, not a measurement error.
4. **Ring centre y.** V1 76.85 mm, V2 74.16 mm (2.7 mm). **Follow V1.**
5. **Ring dry-brush texture.** V1 fills 0.66 of its annulus, V2 0.74 — V2's
    2.2× downsampling closes the small gaps. **Follow V1 for ink texture.**
6. **Top rule continuity.** V1: coverage 0.92, longest break 1.86 mm. V2:
    coverage 0.65, longest break 18.2 mm. V2 simply lost the hairline mid-span.
    **Follow V1.**
7. **Stroke widths generally.** V2 measures 15–20 % fatter everywhere because a
    threshold on a 2.2×-downsampled image eats the antialiased shoulder.
    **Follow V1 for all stroke widths.**
8. Corner clips, border insets, flame emblem, large seal, diamond chain and the
    column x-placement all agree between the two to within 0.5 mm. Where V2 is
    listed above as authoritative for text, its x numbers can be used directly.

## 10. Our current build vs the reference

Measured from `Exports/PaperBomb/Textures/T_PaperBomb_BC.png` (read-only), front
UV island, through the identical code path. Worst first; "buyer sees it" is my
judgement of whether it shows in a Fab thumbnail.

1. **Centre 爆 is 14 % too small relative to the ring.** width/ring-diameter
    0.832 vs 0.972; absolute 48.4 × 44.4 mm vs 59.0 × 52.1 mm. The reference's
    character fills and bursts the circle; ours floats inside it with 8.4 mm of
    slack to the left rule and 6.1 mm to the right where the reference has
    2.9 mm and −0.5 mm (overlap). **Buyer sees it.**
2. **Ring stroke is 33 % too thin and has no dry brush.** 3.54 mm vs 5.31 mm
    median, p90 4.83 vs 7.22 mm, and annulus fill 1.01 vs 0.66 — ours is a
    solid even outline, the reference is a broken ensō with a third of its
    annulus bare. **Buyer sees it.**
3. **Side columns are ~35 % undersized.** Glyph em 9.6 mm vs 15.1 mm; column
    block 10.0 mm wide vs 15.1 mm. Our glyphs are anchored on the inner edge
    and grow inward, so the clear space to the side rules is 6.57 / 5.86 mm
    where the reference has 1.36 / 1.18 mm. Our pitch is also 7 % loose
    (15.0 mm vs 14.1 mm) — small glyphs, wide gaps. **Buyer sees it.**
4. **The whole central stack is pushed right.** Ring centre x 36.43 mm vs
    35.26 mm; ring clear space 5.86 mm left vs 2.86 mm right (reference:
    1.86 / 1.79, symmetric); whole-tag ink balance −9.1 % (right-heavy) vs the
    reference's +3.0 % (left-heavy) — a 12-point swing. **Buyer sees it.**
5. **The ornament chain below 瞬業 is missing.** We have none of: the red leaf
    above the column (35.0, 111.5), the two flanking leaves at y ≈ 130, the
    large black tailed lozenge, or the black diamond on the bottom rule
    (34.9, 147.4). Only the red leaf below the bottom rule exists. The lower
    third of our tag is visibly emptier. **Buyer sees it.**
6. **We have a double frame; the reference has a single rule.** Occupancy
    profile across the border band: ours has two full-width horizontal rules at
    6.25 mm and 9.21 mm (top) and 6.96 mm and ~9.9 mm (bottom), plus short
    corner brackets on the sides. V1 and V2 have exactly one rule per side and
    nothing else. **Buyer sees it.**
7. **Border rules are half the reference weight and 0.5 mm too close to the
    edge.** Left/right stroke 0.286 / 0.357 mm vs 0.714 / 0.643 mm; inset
    3.714 / 3.679 mm vs 4.214 / 4.429 mm; top inset 6.25 vs 6.79 mm. Our rules
    also wobble 4–10× more on their centre line (rms 0.21–0.28 mm vs
    0.024–0.078 mm) while varying *less* in width — exactly backwards: the
    reference wobbles in width, not in path.
8. **Corner flourishes are lighter and sit entirely inside the frame.** Ink
    22–36 mm² vs 29–50 mm²; stroke 0.57–1.00 mm vs 0.79–1.50 mm. Three of our
    four corners never cross the rules (outboard −1.4 to −2.9 mm) where the
    reference's dart always overshoots the horizontal rule by ~2.2 mm and the
    side rule by 0.5–0.9 mm.
9. **Ink is washed out.** Black ink stored-sRGB luminance 0.264 vs 0.079; paper
    0.762 vs 0.871; total ink coverage 22.4 % vs 28.2 %. The page reads grey.
    (Caveat: this is the base-colour map; the shader may push it further. The
    *coverage* number is geometric and does not depend on that.)
10. **Large seal is 12 % wide / 16 % tall oversize** (20.1 × 30.6 mm vs
    18.0 × 26.5 mm) and reads as an outline rather than a solid panel — 41 % of
    its bbox is inked vs the reference's 57 %.
11. **Small seal is 21 % wide / 31 % tall oversize** (10.9 × 23.4 mm vs
    9.0 × 17.9 mm) and sits 2.8 mm low (centroid y 135.0 vs 132.2).
12. **Corner clips are inconsistent.** Our cut lengths run 7.07–12.45 mm
    (76 % spread) vs the reference's 7.76–9.23 mm (19 % spread), and two
    corners fit at 67–85° instead of 43–47°. *Low confidence* — see §11.
13. **Extra red diamond at the top centre**, (35.0, 3.5) mm, outboard of the
    top rule. Neither guide has anything above the top rule.
14. **焼尽 sits 3.3 mm high** (centroid y 108.5 vs 111.8) and is 14 % narrow.
15. **Tag aspect of the texture island is 0.44463**, −0.91 % vs the card and
    −0.95 % vs V1. Worth a look at the UV layout. *Low confidence* — see §11.
16. **The flame emblem is essentially right**: 23.6 × 24.9 mm vs 23.5 × 23.4,
    x centroid 34.9 vs 34.7 mm. Its ink centroid is 2.7 mm low (33.6 vs 30.9),
    i.e. our emblem is bottom-heavy, but the box is correct. Leave it alone.

Incidental: our 爆 is drawn far enough right that its sweep nearly touches 焼 —
the two merge into one ink blob at a 0.7 mm dilation. In V1 they stay separate
at the same test. Fixing delta 4 fixes this too.

## 11. Uncertainties and caveats

* **Our texture island's edge is soft** (a ~0.6 mm ramp from UV padding into
  paper) and its bottom edge fits with an rms of 0.25 mm, ten times V1's. Every
  OURS outline number — aspect, corner clips, rule insets referenced to the tag
  edge — carries roughly ±0.3 mm because of this. The corner-clip *chord* fits
  for OURS TL/TR/BR have fit residuals of 17–44 px and should be treated as
  unreliable; use the departure-based cut lengths (7.07–12.45 mm) instead.
* **The diamond detector has false positives.** It keys on compact, pointed,
  40–80 %-filled blobs, which also matches some glyph strokes and parts of the
  corner ornaments. Every candidate is listed in `layout.json` with its full
  geometry so it can be filtered; the centreline chain in §6 is hand-verified
  against the zooms.
* **Beads sitting on a rule are measured as width bulges**, not as separate
  shapes, because the rule mask removes them from the blob search. Their
  lengths (0.9–1.5 mm) are therefore along-rule extents, not true diamond
  heights.
* **V2's small seal and its TR / BL flourish boxes** may include a few mm² of
  neighbouring corner-ornament ink; V1's equivalents are clean.
* **The 爆 bounding box depends on whether detached splatter counts as part of
  the character.** V1's figure merges clusters within 0.7 mm; a stricter rule
  shrinks its height by up to 4 mm. The width and the width/ring-diameter ratio
  are stable.
* Stroke widths are measured as run lengths across a binary classification at a
  per-image adaptive threshold (midpoint between the paper mode and the ink
  mode). That is fair between images but adds ~±0.07 mm (1 canonical px) to any
  single width.
