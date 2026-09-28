# PAPER BOMB — REFERENCE SPECIFICATION

> **THE RULE:** every element is matched in **position, size, proportion, weight, colour and
> density** — while **every stroke stays our own drawing, never traced.**

---

## 0. AUTHORITY — read this before you use any number below

**The reference of record is `References/PaperBomb/paperbomb_guide_v2_real_glyphs.png`**
(300 × 653, real kanji). It is byte-identical to `Downloads/paperbomb.png`, the file the user
named: sha256 `670acbd782c9a43bb0b2838851ec6bec7aaae144f18aaeb5e8cf45ca7ef01099`. Everything
visible on the card — layout, proportions, sizes, positions, stroke weights, ink density, colour,
ornament shapes, **and the silhouette** — comes from that file and from nothing else. It is called
**RG** throughout.

`References/PaperBomb/paperbomb_guide.png` (1024 × 1536, pseudo-glyph side columns) is **supporting
material only**, called **HR**. It may be consulted for **sub-pixel character that 300 × 653
cannot resolve** — the roughness of a stroke edge, the shape of a kasure hole, the size of a
paper fibre, brush-tip behaviour — and **never** to set or override a position, size, weight,
colour or shape. Where the two disagree structurally, RG wins, every time. Rows that consulted HR
say so in the **HR?** column; a `yes` there means *character only*, never the row's own value.

**This rewrite replaces the previous edition of this file**, which declared "**V1** for every
proportion, stroke, ornament and colour" and is therefore no longer authoritative. Every reference
number below was re-derived from RG in this pass. Numbers the old edition carried forward that
re-measurement did **not** confirm are listed in §8 and must not be reinstated.

### Why the aspect moved

RG is a **non-uniform resize** of HR: RG's tag is 274.19 × 635.67 px (aspect **0.43134**) where
HR's is 616.14 × 1378.92 px (aspect 0.4468) — RG is ≈3.6 % taller per unit width. Both files are
pictures, and the user named RG, so **the card's proportion comes from RG**. Width stays the
product decision (70.0 mm); the height moves.

### The instrument, and its honest limit

| | |
|---|---|
| **Tag edge rule** | half-maximum of the **paper-to-background warmth (R − B) step**. The paper level is the top of that step, **not** a high percentile — red ink reaches warmth 0.80 against the paper's 0.25, so a p99 "maximum" puts the threshold above the paper and the mask collapses onto the ink. (That trap is why an earlier pass reported the top rule as 25 % occupied.) |
| **Resolution** | tag 274.189 × 635.673 px → **3.917 px/mm**. **One pixel is 0.2553 mm.** Nyquist is 1.96 cycles/mm, so **nothing finer than a 0.51 mm cell is resolvable in RG.** |
| **Stability** | a threshold sweep from 0.25 to 0.80 of the paper level moves the tag box by ≤1 px and the aspect by ≤0.0016 (0.36 %). |
| **Rectification** | none applied and none needed: the four edges fit to within **0.047°** of axis-aligned, line-fit rms 0.053–0.069 px. Every measurement is in the file's own pixels, so no resampling blur enters any statistic. |
| **Units** | fractions of the tag's own width **W** and height **H** first; millimetres second, on the **70.0 × 162.29 mm** card that RG's aspect implies. Origin is the tag's top-left *virtual* corner — the intersection of the fitted top and left edge lines, i.e. the corner the chamfer cuts off. |
| **Binarisation** | red classified **first** (redness R − ½(G+B) above the paper/ink half-max), then black. Continuity and width are measured on **ink = red ∪ black**, because part of the top rule is drawn in dark, desaturated ink and a red-only mask reports a 20 mm hole a photograph does not show. |
| **Colour** | **stored** file values, sRGB-encoded 0–1. Linear values are named as such. |
| **Uncertainty** | quoted per row. The floor for any single edge is ±0.3 px = **±0.08 mm**; for an ink bounding box ±0.5 px = **±0.13 mm**; for an area ±1 px of perimeter. |
| **Machine twin** | `WorkFiles/paperbomb/reference_metrology/reference_spec_realglyph.json` |
| **Debug overlay** | `WorkFiles/paperbomb/reference_metrology/debug/DEBUG_NEVER_SHIP_RG_s9_overlay_LABELLED.png` — **DEBUG, NEVER SHIP** |

**Nothing in this document is derived artwork.** It is positions, sizes, fractions, angles, counts,
densities and colour values, plus descriptions of shape in words. No crop, mask, trace, outline or
threshold of either guide exists anywhere a build can read. `paperbomb_art.py` refuses to open the
guides (`FORBIDDEN_INPUT_FRAGMENTS`, `GuideAccess`, `no_guide_access`) — keep that gate, and keep
this spec numeric. This is what keeps the asset clear of Fab's CreatedWithAI disclosure.

### How to read the "Ours" column

**ROUND 6 — the Ours column is now live for every row that round 6 touched.** The previous
edition carried its Ours figures forward from a build two rounds old, measured on a 156 mm card,
and kept the current numbers in a separate table in the report; a reader had to know which table
to believe. Every row this round re-measured now carries the value the **shipped build** measured
(FBX content hash `d5db9968…`, BC `11aca785…`, 55/55 spec rows green, 89/89 build gates green),
and §2.9 collects the round-6 rows in one live table with the same columns. Rows round 6 did not
touch still say *(stale)* and still mean it.

---

## 1. SILHOUETTE — its own table, because a mesh change hangs on it

**Verdict: the reference tag is a clean octagon. Four straight sides, four straight corner
chamfers. There is no tear, no nick and no folded corner anywhere on it.**

This was tested, not assumed. The four straight edges were fitted sub-pixel, the four bevels were
fitted independently, and the resulting eight-sided polygon was compared against **1 820 boundary
samples** taken from every scanline and every column of the tag mask:

* worst deviation outward **+0.78 px (+0.200 mm)**, worst inward **−0.72 px (−0.184 mm)**, rms
  **0.193 px (0.049 mm)** — all of it pixel quantisation;
* **zero** boundary samples on **any** side lie more than 1.5 px (0.38 mm) inboard of the octagon,
  so there is no run of missing paper of any length, at any corner or along any edge;
* the bottom-right region specifically: 189 samples on the right edge's lower third (mean −0.05 px,
  worst −0.07 px) and 234 on the bottom edge (worst −0.56 px = −0.14 mm). A 12 mm dog-ear, a 5 mm
  nick or a 16 mm torn edge would each show as tens of samples 20–60 px inboard. **None exists.**

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| S1 | **Card aspect W/H** | **0.43134** | **70.0 × 162.29** | ±0.0016 aspect (±0.6 mm on H) | 0.44872 (70.0 × 156.0) | **−4.0 % on H** | new one-line knob `spec.card_h_mm` = 162.29 | no |
| S2 | **Outline** | regular octagon, 4 straight sides + 4 straight chamfers | — | see S5–S7 | octagon **plus** a 12 mm dog-ear (BR, ~105° out of plane), a 5 mm nick (right edge) and a 16 mm torn bottom edge with lobes | **three features the reference does not have** | `FoldSpec` dog-ear, nick and tear terms — **delete all three** | no |
| S3 | **Chamfer, horizontal leg** | 0.11397 W (per-corner 0.11015 / 0.11167 / 0.11680 / 0.11726) | **7.98 mean** (TL 7.71, TR 7.82, BL 8.18, BR 8.21) | mean ±0.35 mm; no corner >0.6 mm from the mean | 7.6 (all four) | −0.38 mm mean | `CORNER_CLIP_MM`, `spec.corner_clip_mm` | no |
| S4 | **Chamfer, vertical leg** | 0.05039 H (per-corner 0.04751 / 0.04807 / 0.05258 / 0.05337) | **8.18 mean** (TL 7.71, TR 7.80, BL 8.53, BR 8.66) | mean ±0.35 mm | 7.6 | −0.58 mm mean | same | no |
| S5 | **Chamfer angle** | — | **45.7° mean** (TL 45.0, TR 44.9, BL 46.2, BR 46.6) | 44–48°, i.e. legs equal within 8 % | 45.0 | bottom corners are cut ~1.5° steeper | derived from S3/S4 | no |
| S6 | **Chamfer chord** | — | **11.42 mean** (10.90 / 11.05 / 11.81 / 11.94) | ±0.5 mm | 10.75 | −0.67 mm | derived | no |
| S7 | **Bevel straightness** | — | fit rms **0.00–0.15 mm**, max departure ≤0.29 mm | rms ≤0.20 mm, max ≤0.40 mm | n/a *(stale)* | — | chamfer must be a straight cut, not a bevelled curve | no |
| S8 | **Side straightness** | — | fit rms **0.014–0.018 mm**, max departure **0.033–0.044 mm** | rms ≤0.05 mm per side, max ≤0.12 mm | n/a *(stale)* | — | edge loop must not wander | no |
| S9 | **Side squareness** | — | all four edges within **0.047°** of axis-aligned (L 0.002°, R 0.003°, T 0.003°, B 0.047°) | ≤0.10° | n/a *(stale)* | — | — | no |
| S10 | **Tear / nick / dog-ear** | **none** | **none** | zero boundary run >0.38 mm inboard of the octagon on any side | three such features | **remove** | `FoldSpec` | no |
| S11 | **Sheet curvature** | not measurable from a flat scan | — | curl and creases are allowed in 3D **only if they do not move the outline**; the projected silhouette must still pass S1–S10 | gentle curl + creases | keep the curl | `FoldSpec` curl terms | no |

**Consequences of S1/S2/S3/S4, all of which are mesh work:** new card height, a slightly larger
chamfer, and the deletion of three damage features. Redo the LODs, the collision hull, the UVs,
the bounds, the LOD screen sizes, the sockets and the Unreal verification. Because the card grows
4 % taller at the same width, every **vertical** millimetre in §2 changes even where the fraction
does not — build from the fractions.

**What an eye must judge here:** at thumbnail size the tag must read as a *cut ticket*, four clean
corners, nothing snagged. Look at each corner at 4×: the chamfer is a straight cut, not a rounded
one, and the paper's own edge is crisp all the way round. The reference has a soft drop shadow
outside the sheet and **no** damage inside it.

---

## 2. THE SPECIFICATION — one row per element

Fractions are primary. Millimetres are on the 70.0 × 162.29 mm card of §1 row S1.

### 2.1 Frame, rules and corners

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 1 | **Rule frame rectangle** | 0.88748 W × 0.91366 H, centre (0.49729, 0.49699) | **62.12 × 148.28**, centre (34.81, 80.65) | ±0.35 mm on each side | 61.836 × 142.033 → 0.88337 W × 0.91047 H | −0.4 % W, −0.3 % H (**in fractions this is already right**) | `rule_inset_*` | no |
| 2 | **Rule insets** | L 0.05355 W, R 0.05533 W, T 0.04016 H, B 0.04461 H | **L 3.75, R 3.87, T 6.52, B 7.24** | ±0.25 mm | in fractions: L 0.05804, R 0.05859, T 0.04217, B 0.04737 | **+0.31, +0.23, +0.33, +0.45 mm too far inboard** — small, but all four the same way | `rule_inset_*` | no |
| 3 | **Rule weight (swept)** | — | median **L 0.68, R 0.52, T 0.47, B 0.52**; mean of four **0.55** | mean 0.45–0.70; L may be up to 0.20 heavier than R, never the reverse | L 0.62, R 1.01, T 0.70, B 0.46 | R is **+0.49 mm** and is the heaviest where the reference's is its lightest | `rule_weight_mm` → 0.55 | no |
| 4 | **Rule width modulation** | — | p05 **0.00–0.12**, p95 **0.78–0.93**, max 1.20; coefficient of variation **0.37–0.59** | cv 0.30–0.65; p95/p05 ≥ 5 | cv ≈0.10 *(stale)* | ours is nearly constant-width | taper term in `draw_rules` | no |
| 5 | **Rule continuity** | — | zero-ink **L 4.6 %, R 5.0 %, T 6.5 %, B 11.3 %**; breaks per side **L 6, R 6, T 3, B 4**; longest break **L 2.55, R 3.06, T 1.79, B 2.30 mm** | zero-ink 4–12 % per side, **longest single break ≤2.8 mm** (ROUND 6: 3.5 was 54 % above RG's own worst break, so a rule could read dashed and still pass), **no side with more than 8 breaks** | bare paper on 7.5–11.7 % of each side, but broken into many short dashes | occupancy is inside band; **the break-length distribution is not** | break pass in `draw_rules` — gate the distribution, not just the total | no |
| 6 | **Rule thins, never lifts** | — | the stroke narrows to 0.00–0.12 mm before it breaks; **60 % of the zero-ink length on the bottom rule is the two deliberate gaps either side of the black diamond (2.30 and 2.04 mm)** | every break ≥0.5 mm must be preceded and followed by ≥1.5 mm of stroke under 0.25 mm wide | ours cuts from full width to nothing | reads as a dashed rectangle | taper-into-the-gap term | no |
| 7 | **Rule ink colour** | — | **the top rule is drawn in dark, desaturated ink over 36.2 % of its length, in one continuous 15.3 mm run through the middle**; bottom 6.1 %, left 0 %, right 1.2 %. Median red share of the stroke: T 0.73, B 1.00, L 0.86, R 0.88 | top rule 25–45 % dark with one run ≥10 mm; sides ≥0.80 red share | all four rules 100 % red | **an element nobody has drawn** | new: a desaturation ramp on the top rule | no |
| 8 | **Corner ornament, total ink** | — | TL **31.5**, TR **35.6**, BL **42.0**, BR **43.1 mm²** in a 9 mm corner box | ±25 % per corner; bottom corners heavier than top | *(stale)* | — | `draw_ornaments` | no |
| 9 | **Corner ornament, outboard ink** | — | **RE-MEASURED, ROUND 6 — the figures this row used to carry are four times the truth.** Two independent instruments agree: `reference_metrology/lfl.py` reads V1 **0.67–0.81** and V2 **0.70–1.03 mm²**, and round 6's own probe reads RG at **TL 1.59, TR 1.08, BL 0.89, BR 0.82 mm²**, reach **1.89–2.14 mm**. The old 4.56/2.54/5.80/5.87 came from a probe whose corner box also swallowed the rule ends. | **0.55–2.00 mm² per corner** (the two instruments' union), reach 1.6–2.5 mm, all four corners | **TL 1.61, TR 0.95, BL 1.06, BR 0.89 mm²**, reach 1.72–2.29 mm — *live* | inside band at every corner | `corner_dart_weight_mm` = 0.95 | no |
| 10 | **Corner ornament, colour** | — | outboard ink is **red**: red 2.41–5.80 mm², black **0.065–0.912 mm²**. Inboard, the **top** corners carry a dark pool (black share 0.364 TL / 0.445 TR); the **bottom** corners are almost pure red (0.056 BL / 0.026 BR) | outboard black ≤1.0 mm² per corner; top-corner black share 0.30–0.50; bottom ≤0.10 | **all four corners ship black outboard ink** | **wrong colour, and gate s14b enforces the wrong thing** | fix `draw_ornaments`; **rewrite gate s14b** | no |
| 11 | **Corner ornament, form** | — | **1–3 components per corner** (TL 2, TR 2, BL 3, BR 1); darkest luma **0.014–0.145**; a pooled knot of **27.5–35.9 mm²** sits where the two rules meet | ≤3 components; a contiguous dark pool ≥20 mm² at the junction | *(stale)* | — | `draw_ornaments` | no |
| 12 | **Above the top rule, centreline** | — | **nothing** | zero centre-column ink above the top rule | a red leaf at (35.0, 3.5) | one ornament the reference lacks | `diamond_top_y` — delete | no |

**What an eye must judge (rules and corners).** The rules must read as **one loaded brush laid
down in a single pass that runs dry and picks up again** — the band narrows *into* its own gap and
widens *out of* it. Ours reads as a dashed line because it cuts square. Judge at 4×: you should be
able to point at where the brush was running out. At thumbnail size the frame must read as a
continuous rectangle, not a dotted one. The corner ornament is **one continuous stroke that turns
and pools where the rules meet**, then throws a tapering flick out past the frame toward the
chamfer — draw the turn, not two lines plus a decoration.

### 2.2 The ring

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 13 | **Ring centre** | **(0.50246, 0.47623)** | **(35.17, 77.29)** | ±0.30 mm | (0.5196, 0.5030) | **+1.2 mm x, +2.7 mm y** (in fractions) | `ring_centre` | no |
| 14 | **Ring mid-stroke axes** | **0.75741 W × 0.36780 H** | **53.02 × 59.70** | ±1.0 mm each axis | 0.7176 W × 0.3919 H | −5.3 % w, +6.5 % h | `ring_outer_mm` | no |
| 15 | **Ring axis ratio h/w** | **1.126** | — | 1.09–1.17 | 1.217 | **+8 % too upright** | `ring_outer_mm` | no |
| 16 | **Ring stroke (swept band)** | 0.0688 W median | median **4.82**, mean 4.66, p05 **1.69**, p95 **7.11**, max 9.06, cv **0.351** | median 4.4–5.3, p95 ≥6.3, p05 ≤2.3, cv ≥0.28 | 3.40 median (p05 1.40, p95 4.96) | **−29 % median, −30 % p95** | `ring_stroke_mm` → about (1.6, 7.3) | no |
| 17 | **Ring angular coverage** | — | **96.3 %** at ink-present; **4 gaps**, longest **6.5°**; at a 50 % ink threshold 94.3 %, longest gap 10° | coverage 94–98 %; **longest gap ≤9°**; ≥3 and ≤8 gaps | **91.2 %, with coarse localised gaps** | too few, too wide | gap placement in `draw_ring` | no |
| 18 | **Ring striation (kasure)** | — | paper shows through **22.8 %** of the swept envelope; **67 holes** in RG at this sampling | 0.18–0.28 area fraction; **≥55 holes**; measured on **visible ink**, never on a drawing layer | 0.122, 37 holes | **−46 % area, −45 % count** | hole density in `draw_ring` | no |
| 19 | **Ring hole shape** | — | RG resolves 1.53 × 1.02 mm, elongation 1.20 — **at its own limit**. **HR (character only): elongation 1.91, long axis 1.36 mm, short axis 0.68 mm, area fraction 0.223** — the two files agree on area to 2 %, which validates row 18 | elongation ≥1.7, long axis 1.0–1.8 mm, ≥70 % within 30° of the local tangent | 0.31 mm median, elongation 4.8 | ours are finer and thinner than either file | hole shape in `draw_ring` | **yes** |
| 20 | **Ring ink area** | — | **611 mm²** of classified red in the annulus | ±12 % | *(stale)* | — | derived | no |
| 21 | **Ring band alpha** | — | mean **0.523**, std **0.233**, p05 0.05, p95 0.86 along the band | mean 0.45–0.60, std ≥0.18 | reads as a smooth airbrushed annulus | ours has too little modulation | ink-load ramp in `draw_ring` | no |
| 22 | **Ring stroke thickness by sector** | — | thinnest at ~202° and ~322° from east (0.0 and 1.84 mm), thickest at 68° and 248° (7.33 and 7.00 mm) | at least one sector under 2.0 mm and one over 6.5 mm | *(stale)* | — | lap start/end placement | no |

**What an eye must judge (the ring).** Trace the band with your eye and see whether you can tell
**where the brush started and where it ran out**. In the reference the stroke **thins into its own
gap** — it tapers at the end of the lap rather than bulging — and the striation runs *along* the
stroke, long thin parallel streaks of paper, visible nearly everywhere rather than in a few coarse
bites. Ours currently ends wetter than it starts, which reads directionless. The failure mode when
you add holes is *speckle*: holes scattered evenly like film grain instead of clustered where a
splitting brush would leave them. Cover the rest of the card and ask whether the voids follow the
stroke.

### 2.3 The hero character 爆

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 23 | **爆 bounding box** | **0.82791 W × 0.32557 H** | **57.95 × 52.84** | ±1.0 mm | 0.6832 W × 0.2832 H | **−17 % w, −13 % h** | `centre_em_mm`, `centre_stretch_y` | no |
| 24 | **爆 aspect w/h** | **1.097** | — | 1.05–1.15 (**wider than tall**) | 1.082 | close — grow both, keep the ratio | as above | no |
| 25 | **爆 centroid** | **(0.51746, 0.48469)** | **(36.22, 78.66)** | ±0.40 mm | *(stale)* | — | `centre_*` | no |
| 26 | **爆 ink area** | — | **1129 mm²** (fill of its own box 0.369) | ±10 % | *(stale)* | — | stroke widths in `typeset_centre` | no |
| 27 | **爆 component structure** | — | **2 components** over 15 mm² (809 and 321 mm²) | ≤2 components >15 mm²; ≤2 specks under 1 mm² | **5 components** | +3 fragments | cap the kasure so no hole may sever a stroke | no |
| 28 | **爆 clearance, left rule** | 0.0564 W | **3.95** | 3.2–4.7 mm | 8.2 | +4.2 mm | grows shut with row 23 | no |
| 29 | **爆 clearance, right rule** | 0.0163 W | **1.14** nearest ink to nearest ink; its bounding box stops **0.22 mm** short of the rule's centreline | 0.6–1.8 mm ink-to-ink — it must **nearly kiss** the right rule | 5.9 | +4.8 mm | grows shut with row 23 | no |
| 30 | **爆 clearance, ring** | — | **0.26** — it **touches** the ring | ≤0.6 mm; touching is correct | *(stale)* | — | — | no |
| 31 | **爆 clearance, 焼 (lower-right column)** | 0.0389 H | **6.32** | **5.5–7.5 mm — gate this** | **1.70** | **−4.6 mm; they merge at thumbnail size** | `col_lower_right_y`, hero size | no |
| 32 | **爆 clearance, flame emblem** | 0.0549 H | **8.91** | 8.0–10.0 mm | *(stale)* | — | `emblem_y` | no |
| 33 | **爆 clearance, 瞬 (lower centre)** | 0.0592 H | **9.61** | 8.5–10.8 mm | *(stale)* | — | `col_lower_centre_y` | no |
| 34 | **爆 clearance, upper columns** | — | TL **10.73**, TR **7.15** | ±1.5 mm | *(stale)* | — | — | no |
| 35 | **爆 stroke modulation** | — | RG cannot resolve the thinnest filament (1 px floor). **HR (character only): 22.6:1 thinnest to widest — a lower bound, not a target** | ratio ≥8:1, treated as a floor to beat | 3.4:1 | ours reads drawn, not brushed | brush profile in `typeset_centre` | **yes** |

**What an eye must judge (爆).** At thumbnail (≈40 px wide) the 火 radical and the body must merge
into **one mass**; at 100 % they must read as two strokes that nearly touch. The character bursts
out of the ring left and right — it is not contained by it. And it must not merge with 焼: row 31
is a gate because the two currently read as one blot at thumbnail size.

### 2.4 The flame emblem

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 36 | **Emblem box** | **0.34648 W × 0.14313 H**, centre (0.49903, 0.19258) | **24.25 × 23.23**, centre (34.93, 31.25) | ±0.8 mm on size, ±0.4 mm on centre | 23.29 × 24.68 at (34.75, 30.41) | box is **already right** — do not move it | `emblem_size_mm` | no |
| 37 | **Emblem aspect w/h** | **1.044** | — | 0.99–1.10 | 0.944 | ours is too tall | `emblem_size_mm` | no |
| 38 | **Emblem ink** | — | **176 mm²**, fill of its box **0.313** | 155–200 mm²; fill 0.28–0.35 | 268 mm², fill 0.466 | **+52 % ink** | stroke widths in `_flame_paths` | no |
| 39 | **Emblem components** | — | **4 strokes** ≥3 mm² (73.3 / 60.2 / 21.4 / 21.4 mm²) plus ≤5 specks totalling ≤3.5 mm² | 4–5 components ≥3 mm²; **no single welded mass** | 1 welded stroke | 4 → 1 | thin until the tongues separate | no |
| 40 | **Outer tongues** | — | two **separate** crescents, **21.4 mm² each**, 5.11 × 11.74 (left) and 4.85 × 11.49 (right), centres (24.66, 33.49) and (45.12, 33.62) — symmetric to 0.25 mm² | area ±15 %, left/right within 10 % of each other | *(stale)* | — | `_flame_paths` | no |
| 41 | **Inner tongues** | — | the 73.3 mm² upper mass, 14.04 × 16.59 at (34.87, 27.33), split by a notch on the centreline | 2 tips rising above y = 21 mm | *(stale)* | — | `_flame_paths` | no |
| 42 | **Heart: a SOLID spiral comma** | 0.2006 W × 0.10695 H | **14.04 × 17.36** at (34.96, 31.62), **116 mm²** of ink | ink ≥95 mm²; see row 43 | a thin line wound **2.5 turns** with white gaps; 2 stray specks (1.4 and 1.1 mm²) | **wrong construction** | `_flame_paths` heart | no |
| 43 | **Heart: exactly one paper channel** | — | a vertical cut through its centre reads **ink 4.85 / paper 1.53 / ink 3.83 / paper 2.81 / ink 1.02 mm** — a solid comma with **one** 1.5 mm channel, then the outer tongue gap | exactly **one** enclosed-looking paper channel of 1.2–2.0 mm; **the ink arms either side ≥3.5 mm thick** | 2.5 laps of a thin line | ours has 4–5 channels and no solid arm | `_flame_paths` heart | no |
| 44 | **Heart: the spiral is OPEN** | — | **zero enclosed paper voids** in the whole emblem — the channel spirals out and exits | the emblem must have **no** closed eye | *(stale)* | — | `_flame_paths` | no |
| 45 | **Emblem run ladder** | — | horizontal ink runs at 10…90 % of its height: 2, 2, 2, 5, 5, 6, 7, 4, 1 runs per row, widths from **0.26 to 5.62 mm** | ≥6 runs on at least one row; at least one run ≤0.6 mm and one ≥4.5 mm | *(stale)* | — | `_flame_paths` widths | no |

**What an eye must judge (the flame).** The eye should land on **爆 first, the ring second, the
emblem third** — after thinning, squint at the card and check that order. The heart is a **solid
comma that curls once and a half with a single paper channel**, tapering into a tail that sweeps
down-right; it is not a coil of wire. The two outer tongues are detached crescents; the two inner
tongues rise from the body with a notch between them. Whether the alternation of thin and thick
reads as *flame* is not a number.

### 2.5 The four columns

Leading is effectively zero in every column: consecutive glyphs are **0.26 mm apart or touching**.

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 46 | **火遁術 (upper left)** — axis | **0.17884 W** | **12.52** | ±0.5 mm | 0.2427 W | **−4.4 mm inboard** | `col_upper_left_x` | no |
| 47 | 火遁術 — cell width / em | **0.19330 W** | cell **13.53**; per-glyph em 13.02 / 13.78 / **17.36** (術 is the big one) | cell ±0.9 mm | 0.1361 W = 9.53 | **−30 %** | `col_upper_em_mm` | no |
| 48 | 火遁術 — pitch, extent, rule clearance | column 0.2044 W × 0.2736 H | pitch **13.26 / 13.43**; box **5.14–19.44 × 10.22–54.64**; clears the left rule by **1.40** | pitch ±0.8 mm; clearance 1.0–2.0 mm | pitch 14.7–16.1 | pitch is nearly right; the glyphs inside it are small | `col_*_y` | no |
| 49 | **爆炎陣 (upper right)** — axis | **0.80882 W** | **56.62** | ±0.5 mm | 0.7617 W | **+3.3 mm inboard** | `col_upper_right_x` | no |
| 50 | 爆炎陣 — cell width / em | **0.19938 W** | cell **13.96**; per-glyph em 15.57 / 13.78 / **20.93** (陣 is the big one) | cell ±0.9 mm | 9.53 | −32 % | `col_upper_em_mm` | no |
| 51 | 爆炎陣 — pitch, extent, rule clearance | column 0.2298 W × 0.3004 H | pitch **13.94 / 13.25**; box **48.80–64.89 × 9.46–58.21**; clears the right rule by **0.99** | pitch ±0.8 mm; clearance 0.6–1.6 mm | — | — | `col_*_y` | no |
| 52 | **焼尽 (lower right)** — axis | **0.82539 W** | **57.78** | ±0.5 mm | 56.7–57.8 | **already right** | `col_lower_right_x` | no |
| 53 | 焼尽 — cell width / em | **0.20424 W** | cell **14.30**; em 13.79 / 14.81 | ±0.9 mm | 14.0 nominal | close | `col_lower_right_em_mm` | no |
| 54 | 焼尽 — pitch and extent | column 0.2117 W × 0.1730 H | pitch **13.02**; box **50.08–64.89 × 103.39–131.47**; clears the right rule by **0.99** | pitch ±0.8 mm | — | — | `col_lower_right_y` | no |
| 55 | **瞬業 (lower centre)** — axis | **0.50215 W** | **35.15** | ±0.4 mm | 35.2 | **already right** | `col_lower_centre_x` | no |
| 56 | 瞬業 — cell width / em | **0.18236 W** | cell **12.77**; em 15.32 (瞬) / 18.12 (業) | ±0.9 mm | 16.1 nominal | close | `col_lower_centre_em_mm` | no |
| 57 | 瞬業 — pitch and extent | column 0.1970 W × 0.2059 H | pitch **16.54**; box **28.12–41.91 × 114.62–148.06** | pitch ±0.9 mm | — | — | `col_lower_centre_y` | no |
| 58 | **Column leading** | ≤0.0016 H | **0.26 — the glyphs touch** | ≤0.8 mm every join | 2.24–5.80 | **+2.0 to +5.5 mm** | closes for free with rows 47/50 | no |
| 59 | **Which glyphs, where** | — | 火遁術 upper left, 爆炎陣 upper right, 焼尽 lower right, 瞬業 lower centre, all vertical, all black | exact | correct | — | `LAYOUT` | no |

**What an eye must judge (the columns).** They must read as **written**, not set: each column is
one downward gesture, the glyphs touching or nearly so, the last glyph in each column noticeably
larger than the first two. The upper third of the card carries real density in the reference —
ours looks hollow because the glyphs are small inside a correct pitch.

### 2.6 The two seals

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 60 | **Big chop — outer box** | **0.22977 W × 0.16829 H**, centre (0.19566, 0.83919) | **16.08 × 27.31**, centre (13.70, 136.19) | ±0.6 mm size, ±0.4 mm centre | 20.12 × 29.71 at (15.05, 130.12) | **+25 % w** in fractions | `big_seal_frame_x` | no |
| 61 | Big chop — double frame | — | outer rule **1.02**, paper gap **1.28** (both from column scans at 25 % and 75 % of its height, which agree exactly), then the inner rule and the panel | rule 0.85–1.25; gap 1.0–1.6 | single rule 0.45 | **the second rule is missing** | `big_seal_rule_mm`, new inner rule | no |
| 62 | Big chop — solid panel | 0.1751 W × 0.1305 H | **12.26 × 21.19** at (8.46–20.72, 125.60–146.78) | ±0.6 mm | 13.7 × 22.1 | close in mm, **too wide** in fraction | `big_seal_panel_x` | no |
| 63 | Big chop — device is **reversed out** | — | panel red fraction **0.666**; the device is **paper-coloured, 86.8 mm², 33 % of the panel** | panel red 0.60–0.72; device must be paper on red | red fill 0.478 | ours is not solid enough behind the device | `draw_big_seal` | no |
| 64 | Big chop — device **shape** | — | a **tall curling flame with a spiral base** — two tongues rising, a comma spiral at the foot, the same motif as the emblem | must read as a flame, not a disc | **a round fireball** | wrong device | `_seal_flame_paths` | no |
| 65 | **Small chop 火道 — outer box** | **0.11671 W × ~0.0893 H**, centre (0.84671, ~0.88606) | **8.17 × ~14.5**, centre (59.27, ~143.8) — ±0.4 mm, this box touches the BR corner ornament so its right edge is the harder read | ±0.5 mm | 10.7 × 21.9 | **−24 % w, −34 % h** in fractions — **ours is much too big** | `small_seal_*` | no |
| 66 | Small chop — frame | — | a **single** rounded-rectangle rule, **0.77 mm** | 0.6–0.95 mm, single, rounded corners | 0.45 | thin, and the box is oversized | `small_seal_rule_mm` | no |
| 67 | Small chop — device is **positive** | — | 火 above 道 in **red on paper**; red covers **0.29–0.39** of the box; **no reversed-out area** | red fill 0.26–0.44; **light-on-red ≤5 %** | **32 % light on red** | ours inverts part of it | `draw_small_seal` | no |
| 68 | Small chop — glyph em | — | ≈**5.5–6.5 mm** per character inside a 6.9 × 13.3 mm panel | ±0.7 mm | 4.8–5.4 | slightly small, but the **box** is the real error | `small_seal_em_mm` | no |
| 69 | **Seal balance** | — | big chop **280 mm²** of red, small chop **61 mm²** — a 4.6 : 1 ratio that is what makes the lower-left corner the heavy one | ratio 4.0–5.4 : 1 | *(stale)* | — | derived | no |

**What an eye must judge (the seals).** The big chop must read as a **stamped seal**: a solid red
block with a shape cut out of it, double-ruled, ink slightly uneven inside the block. The small
chop is the opposite: an outlined box with two red characters written inside it, nothing reversed.
The reference's card is slightly **left- and bottom-weighted** — the filled lower-left chop
balances the sparser lower right. Look at the card upside down and out of focus: the two lower
quadrants should feel about equally heavy.

### 2.7 The centreline chain

Four ornaments on the vertical midline below the ring, and nothing above the top rule.

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 70 | **Red lozenge A** (below the ring, above 瞬) | (0.49949, 0.69112), 0.02188 W × 0.01730 H | **(34.96, 112.16)**, **1.53 × 2.81**, 2.35 mm² | ±0.3 mm position, ±0.4 mm size | present | check size | `LAYOUT` lozenge | no |
| 71 | **Red lozenge B** (below 業, above the rule) | (0.49906, 0.92574), 0.02188 W × 0.01730 H | **(34.93, 150.24)**, **1.53 × 2.81**, 2.09 mm² | ±0.3 mm | present | check size | `LAYOUT` lozenge | no |
| 72 | **Black diamond on the bottom rule** | (0.49867, 0.95037), 0.03647 W × 0.02513 H | **(34.91, 154.23)**, **2.55 × 4.08**, 4.82 mm² | ±0.3 mm position, ±0.5 mm size | **1.86 mm tall** | **−2.2 mm tall** | `LAYOUT` diamond | no |
| 73 | **The rule parts for it** | — | the bottom rule stops **2.30 mm** to its left and **2.04 mm** to its right | 1.8–2.8 mm each side, both present | *(stale)* | — | `draw_rules` exclusion | no |
| 74 | **Red spike C** (below the rule) | (0.5000, 0.97340), 0.0073 W × 0.0094 H | **(35.00, 157.97)**, **0.51 × 1.53** | ±0.3 mm | red leaf at (34.98, 151.91), 0.77 × 2.17 | close in kind, ~0.3 mm too wide | `LAYOUT` | no |
| 75 | **Nothing else on the centreline** | — | no centre ornament above the top rule, none between the emblem and the ring | zero ink | one extra red leaf at the top | delete | `diamond_top_y` | no |

### 2.8 Paper, ink and colour

| # | Element | Reference (fraction) | Reference (mm / value) | Tolerance | Ours (last good build) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 76 | **Paper colour** | — | stored **#F6E4C1** = (0.9647, 0.8941, 0.7569); hue **39.6°**, S **0.215**, V 0.965; linear (0.9216, 0.7758, 0.5333); **linear luma 0.7893** | hue 38–42°, S 0.19–0.24, linear luma ≥0.72 | #DACAA8, linear luma 0.597 | **−24 % value** (hue and saturation are right) | `PALETTE.paper` | no |
| 77 | **Black ink core** | — | stored **#080907** = (0.0314, 0.0353, 0.0275); **linear luma 0.00262**; stored luma p01 0.015, median 0.052 | linear luma ≤0.02; no hard floor above stored 0.10 | floor pinned at stored 0.2400 (min = p01 = 0.24) | **the ink has no dark tail at all** | `PALETTE.black_wet`, `DIELECTRIC_FLOOR_LINEAR` | no |
| 78 | **Paper : ink contrast** | — | **301 : 1** linear | within ×3 of the reference, i.e. ≥100 : 1 | 11.7 : 1 | **−96 %** | see the ladder below | no |
| 79 | **Red hue** | — | **3.6–4.1°** across all six red elements — **spread 0.49°** | every red within 1.5° of 3.9° | 5.4° | hue is not the problem | `PALETTE.red_wet` | no |
| 80 | **Red saturation** | — | **0.934–0.947** — **spread 0.020** | S ≥0.88 for every red; spread ≤0.05 | 0.61–0.64 | **−32 %** | `PALETTE.red_wet` | no |
| 81 | **Red value spread** | — | border **#CD1C0F** (V 0.804), ring **#D1190C** (0.820), big seal **#CF170B** (0.812), small seal **#DA1B0E** (0.855), lozenges **#D51A0E** (0.835), corners **#C8170B** (0.784). Spread across the four named reds **0.051**, across all six **0.071** | spread 0.035–0.09; one pigment, several weights | **0.047** but with the wrong ordering | ordering, not magnitude | four weights off one `red_wet` | no |
| 82 | **Which red is heaviest** | — | by mean luma of its own ink: **border rule 0.251 (heaviest)**, corners 0.257, big seal 0.258, ring 0.284, lozenges 0.288, **small seal 0.320 (lightest)** | the **border rule must be the heaviest** and the **small seal the lightest** | our border is our **lightest** | **inverted** | per-element red weight | no |
| 83 | **Coverage** | — | red **0.1102**, black **0.1899**, ink **0.3001**; **black ÷ red = 1.724** | black/red 1.55–1.90 | 1.064 | **−38 %** — the shortfall is entirely black | follows rows 23, 38, 47, 50 | no |
| 84 | **Ink halo** | — | paper is **fully recovered 0.51 mm** from a black stroke edge; at 0.26 mm the luma is 0.838 against 0.899 — **one pixel of ramp, the file's own sampling floor**. **HR (character only): the ramp is 1–2 px at 0.114 mm/px, i.e. ≈0.11–0.23 mm** | 95 % recovery within **0.30 mm** of the ink edge | **0.54 mm** | ×2–5 too soft — a visible bloom around 爆 and the ring | halo/bleed term in `paper_ground` | **yes** |
| 85 | **Edge ageing** | reach 0.1186 W | edge luma **0.822** against a plateau of **0.899** → **8.6 % deep**; half-recovered by ≈2.4 mm, **95 % recovered by 8.30 mm**; four sides agree within **1.39 luma points** | depth 6–12 %; 95 % reach 6–10 mm; sides within 3 points; no directional tilt | 21.9 % deep, reach 14.75 mm, sides differ 12.4 pts, tilt 5.3 % | **+155 % depth, ×1.8 reach, ×9 unevenness** | `PALETTE.paper_edge`, `_edge_distance_mm` | no |
| 86 | **Paper grain — amplitude** | — | **0.63 %** of paper luma (std), **2.07 %** p05–p95; the whole paper's p05–p95 is 3.17 % | std 0.4–1.0 % of paper luma | amplitude "settled" | keep | `PALETTE.grain_linear` | no |
| 87 | **Paper grain — cell** | — | RG measures **0.40 × 0.41 mm**, which **is** its resolution floor (Nyquist cell 0.51 mm) and therefore an **upper bound**. **HR (character only): 0.128 × 0.125 mm, anisotropy 1.03** | cell **0.10–0.22 mm**, anisotropy ≤1.4 | ~1 mm | **×5–8 too coarse, and directional** | noise cell / anisotropy | **yes** |
| 88 | **Paper mottle** | — | banded std as a fraction of paper luma: 0.5–1.5 mm **0.47 %**, 1–3 mm **0.39 %**, 3–10 mm **0.32 %**, 10–20 mm **0.45 %** — **the sheet is essentially flat at every scale above the fibre** | every band ≤0.8 %; no band above 1.0 % | cloudy blotching in the render | **ours has low-frequency cloud the reference does not** | mottle term in `paper_ground` | no |
| 89 | **Baked crease shading** | — | **none**; the sheet is flat and evenly lit | no row-luma dip >1.2 % spanning >25 % of W | lines at 51.6 and 104.4 mm | two lines the reference lacks | crease term in `paper_ground` / `_relief` — the mesh already has the folds | no |

**The contrast ladder (rows 77/78), unchanged in substance from the previous edition and still a
user decision.** The module clamps every channel at `DIELECTRIC_FLOOR_LINEAR = 0.0473` (stored
0.235) and says so in its own comment. Step (a) — `PALETTE.paper` → (0.870, 0.747, 0.533) — is
free and inside the band the module already declares. Steps (b) (floor → 30/255) and (c) (drop the
floor for ink only, `black_wet` → the measured (0.031, 0.035, 0.028)) change a shipped-asset rule
the user wrote down on purpose. **Do (a) now; ask before (b) or (c).** Red saturation (row 80) is
governed by the same decision, because `red_wet`'s green and blue are pinned on the same floor.

---

### 2.9 ROUND 6 — re-measured rows and the gates built for them

Same columns as every table above. **Ours is live**: measured by `props_lib.art_metrics` on the
artwork the shipped build drew, at 12.4222 px/mm, supersample 2. Reference figures marked *(r6)*
were measured this round on RG by an instrument written for it (3.971 px/mm, red classified
first, sub-pixel card edge) and cross-checked against the figures already in this file.

| # | Element | Reference (fraction) | Reference (mm) | Tolerance | Ours (live) | Δ | Knob | HR? |
|---|---|---|---|---|---|---|---|---|
| 90 | **Column block ink** *(r6)* | — | UL **229.6**, UR **241.4**, LR **143.0**, LC **187.7 mm²** inside each block's own window | ratio to reference ≥ **0.62** on the build's own (tighter, hero-excluded) window | UL 205.1, UR 207.2, LR 98.3, LC 167.8 mm² → **0.893 / 0.858 / 0.687 / 0.894** | LR is the worst block, 0.687 | `column_brush_mm` | no |
| 91 | **Column stroke connectivity** *(r6)* | — | **2–4** components ≥2 mm² per block | ≤ **10** per block | 9 / 8 / 6 / 5 | still fragmenting, but well under round 5's 7–10 on a quarter more ink | `_fatten` + `glyph_counter_*` | no |
| 92 | **Hero component split** *(r6)* | — | 暴 **816.1**, 火 **325.3 mm²** → ratio **0.399** | **0.330–0.450** | 806.1 / 301.4 → **0.374** | −0.025 | `centre_radical_brush_mm` = 0.505 | no |
| 93 | **Hero-to-column clearance** *(r6)* | — | **5.99 mm** of clear paper between 爆 and 焼, as a TRUE 2-D nearest distance | **5.00–7.10 mm** | **5.47 mm** (next three 5.77 / 6.34 / 8.61) | −0.52 | `column_centre_clear_mm`, `centre_column_clear_mm` | no |
| 94 | **Ring kasure hole shape** *(r6)* | — | elongation **1.20** at RG's own sampling, **1.91** in HR's finer character | median long/short ≤ **3.40**, ≥12 holes measured | **1.93** over 63 holes | on HR's figure | `streak_cell_mm`, `ring_kasure_dry` | yes (character only) |
| 95 | **Big chop device form** *(r6)* | — | a **tall curling flame**, taller than wide, printing as one island | h/w **1.25–2.30**, largest island ≥ **0.78** of the device's paper | h/w **1.70**, share **0.83**, 2 islands | in band; the device's *drawing* is still a bulb, see §5 | `flame_device(style="seal")` | yes |
| 96 | **Flame heart solidity** *(r6)* | — | a **solid comma**: one mass, one hairline cut | box fill ≥ **0.52**, ≤ **2.40** ink runs per scanline | fill **0.701**, **1.75** runs | solid | `emblem_heart_r_mm`, `emblem_cut_turns` | no |
| 97 | **Rule zero-ink fraction** | — | **0.000–0.016** on three sides, 0.050 on the fourth (RG, chroma instrument) | ≤ **0.105** on the worst side | worst side **0.080** | inside | `RULE_GAP_FLOOR`, break pass | no |
| 98 | **Longest single break** | — | **2.27 mm** (independent instrument) / **3.06 mm** (this file's) | ≤ **2.80 mm** | **2.74 mm** | between the two reference readings | `_rule_breaks` clip | no |
| 99 | **Rule weight, per side** | — | L **0.679**, R **0.524**, T **0.468**, B **0.520**; mean **0.548** | mean 0.45–0.70, L 0.02–0.22 heavier than R | L 0.684, R 0.525, T **0.624**, B 0.538; mean 0.593; L−R **+0.159** | L, R and B on the number; **the top rule is +0.156 over** — see §5 | `rule_weight_side_mm` | no |
| 100 | **Ink coverage** | — | black **0.19198**, red **0.11651**, total **0.30849** of the card | black ≥0.155, red ≥0.095, total 0.255–0.33 | black **0.176**, red **0.1133**, total **0.2893** | −8.3 % / −2.7 % / −6.2 % | glyph brush, rule weights | no |
| 101 | **Paper grain** | — | amplitude **0.0207**, cell **0.62 mm**, anisotropy **1.037** | amp 0.014–0.028, cell 0.47–0.85, aniso ≤1.40 | **0.0194 / 0.805 / 1.00** | amplitude 13 % closer than round 5's 0.0172; anisotropy off its ceiling at last | `grain_weight`, `grain_cell_mm`, `grain_aniso` | no |
| 102 | **Guide-access guard** | — | must refuse **every** route to the guide during a build | `builtins.open`, `io.open`, `io.open_code`, `bpy.data.images.load`, both slash styles | all five **blocked**, the licensed font still opens | the `io.open` hole the round-1 audit found is closed | `no_guide_access` | no |

**What an eye must judge (round 6's rows).** The columns must read as **writing**, not as weight:
the ink went up by a quarter and the counters had to survive it, so judge the column 爆's 日 and
the 瞬's 目 at 14 px/mm — if either has filled in, the brush is too full whatever the ink says.
The hero must read as **one character** at 40 px: 火 carries a third of the mass and sits level
with 暴, not below it. The clearance between 爆 and 焼 is **paper you can see** at gallery size.

## 3. What the real-glyph reference does NOT have

Each of these was looked for and is absent. Do not draw them, and delete them where we ship them.

1. **Any damage to the outline** — no dog-ear, no nick, no tear, no fold that moves the silhouette.
   1 820 boundary samples, worst deviation 0.20 mm, zero runs inboard. (§1)
2. **A free-standing flanking leaf pair.** The V1 layout put two tapered leaves in clean paper at
   fy ≈0.838. In RG the only marks at those x positions (fx 0.456 and 0.537) are at **fy 0.889 and
   0.896** and they are the **八 strokes at the foot of 業** — part of the glyph, 1.43 and 2.80 mm²,
   tapered brush strokes. Drawing them as separate ornaments, or as hard geometric diamonds fused
   into 業, is wrong twice over. The zone carries **59 mm² of black in two components, all of it
   glyph.**
3. **A second full-width rule on any side.** Scanning inward from each edge, the ink profile falls
   below 0.02 immediately after the rule and stays there (top 0.009, bottom 0.099 at its highest);
   on the left and right it only rises again where the **ring's own ink** starts, ≈6 mm inboard,
   and it rises gradually as a curve approaches rather than as a second peak.
   `inner_rule_sides = ()`.
4. **Any ornament above the top rule on the centreline.**
5. **A closed eye inside the flame emblem** — the spiral is open.
6. **A lower-left mark group.** V1 had one at x 7.3–15.9 mm, y 100–114 mm. RG does not.
7. **Baked crease or fold shading**, and no internal shadow of any kind.
8. **Black outboard ink at the corners.** There *is* 2.5–5.8 mm² of outboard ink per corner, but it
   is red (black ≤0.91 mm²). **Gate s14b enforces the wrong thing and must be rewritten.**

---

## 4. Ranked worklist

Ordered by how far each moves the asset toward the reference. 1–6 a buyer sees at thumbnail size;
7–14 in a product shot; the rest at 100 %.

| # | Do this | Expected visual effect |
|---|---|---|
| 1 | **Repair `paperbomb_art.py`** (`lay.emblem_heart_r_mm` is read but never defined, ~line 2789), finish the half-made heart change rather than reverting it, then prove determinism against the shipped maps before touching anything else | nothing builds until this lands |
| 2 | **Delete the dog-ear, the nick and the torn bottom edge**; set the card to **70.0 × 162.29 mm**; chamfer to **8.1 mm** | fixes the defect the user reported, and the silhouette becomes the reference's. Mesh work: LODs, collision, UVs, bounds, screen sizes, sockets, Unreal re-verify |
| 3 | **Raise the paper to the band ceiling, then decide the ink floor** (§2.8 ladder) | the card stops reading grey-on-tan and starts reading black-on-cream. Nothing else changes the read at every distance the way this does |
| 4 | **Grow 爆 to 0.828 W × 0.326 H** (57.95 × 52.84 mm) and **re-join it into two components** | the hero stops floating in a moat and fills its ring; the 火 radical stops reading as a blot |
| 5 | **Open the 爆 → 焼 clearance to 6.3 mm and gate it** | at thumbnail the two currently merge into one mark |
| 6 | **Grow the column glyphs ≈40 % so they touch**, and move the upper axes out to 0.1788 W / 0.8088 W | the top of the card stops looking hollow; the leading closes for free |
| 7 | **Rebuild the flame heart as a solid comma spiral with ONE 1.5 mm paper channel**, arms ≥3.5 mm thick, and keep the four separate strokes at ≈176 mm² | the emblem stops reading as a wire coil and starts reading as flame |
| 8 | **Ring: wider, shorter, heavier** — centre (0.5025, 0.4762), axes 53.0 × 59.7 mm, stroke median 4.8 with p95 7.1 | an upright narrow oval is what a parametric sweep looks like; the reference's is nearly round with a loaded brush |
| 9 | **Ring striation to 0.23 area fraction across ≥55 holes, elongated along the tangent, coverage 96 %** with no gap over 9° | a quarter of the reference's ring is bare paper in fine streaks; ours is a nearly solid band, which is what reads as a filled vector shape |
| 10 | **Make the border rule thin into its gaps**: cv 0.37–0.59, longest break ≤3.5 mm, 3–6 breaks a side | an unbroken rule of constant width is the most machine-made thing on the card; a dashed one is the second |
| 11 | **Red saturation to ≥0.88**, and **invert the weight order** so the border is the heaviest red and the small seal the lightest | ours reads brick-pink and evenly weighted; cinnabar laid on at four weights is what the guide reads as |
| 12 | **Corner ornament: one continuous stroke that turns and pools**, 2.5–5.8 mm² outboard **in red**, 1.9–2.2 mm reach, dark pool at the top corners only | corners are where a buyer zooms in looking for craft |
| 13 | **Rewrite gate s14b** so it requires red outboard ink and forbids black | the gate currently enforces a defect |
| 14 | **Big chop: double frame, solid panel, flame device reversed out**; **small chop: shrink the box to 8.2 × 14.5 mm, all positive** | the chops read as stamps rather than as a red rectangle and an oversized outline |
| 15 | **Black diamond on the bottom rule to 2.55 × 4.08 mm**, with the rule parting 2.3 / 2.0 mm either side | the vertical chain down the centre is a signature element and it currently stops short |
| 16 | **Halve the ink halo to ≤0.30 mm** | removes the bloom around 爆 and the ring |
| 17 | **Paper grain to a 0.10–0.22 mm cell, isotropic, 0.6 % amplitude**; **kill the low-frequency mottle** (every band ≤0.8 %) | our sheet reads smooth-and-cloudy; the reference reads laid and flat |
| 18 | **Edge ageing: 8.6 % deep, 8.3 mm reach, isotropic** | our vignette is twice as deep and has a direction, which reads as a bug rather than wear |
| 19 | **Add the top rule's dark middle section** (36 % of its length, one 15 mm run) | a detail nobody has drawn, and the only place on the card where the border changes colour |
| 20 | **Delete `diamond_top_y`** | free deletion; it breaks the clean top edge |
| 21 | **Take the crease term out of the base colour** | double-shaded folds read as printed-on dirt rather than geometry |

---

## 5. What is *not* capturable as a number

A number can tell you the ring is 4.82 mm thick. It cannot tell you the ring looks like a brush
moved. Judge every element at **gallery size, at 4×, and at thumbnail (≈40 px wide)**. A row inside
tolerance whose element still looks different is **failing**.

* **Does 爆 read as ONE character?** At thumbnail the 火 radical and the body merge into one mass;
  at 100 % they are clearly two strokes that nearly touch.
* **Does the ring read as ONE fast brush stroke?** You should be able to see where the brush
  started and where it ran out. The band **thins into its own gap** rather than bulging.
* **Is the dry-brush breakup believable, or is it noise?** The failure mode is speckle — holes
  scattered evenly like film grain instead of clustered where a splitting brush would leave them.
* **Does the flame sit above the character, or compete with it?** Squint: 爆 first, ring second,
  emblem third.
* **Does the heart read as a comma, or as wire?** One solid arm, one channel, one tail.
* **Do the corners look like craft or like decoration?** The measurable part is the outboard red
  flick. The unmeasurable part is the hook: the stroke turns like a comma going down-and-in, ink
  pooling darkest where the two rules cross.
* **Is the ink DARK, or merely darker?** Judge in the shipped gallery render, not in the map.
* **Is the red cinnabar or brick?** Put our red and the reference's side by side at the same size
  on the same background before accepting it.
* **Does the whole card balance?** The reference is slightly left- and bottom-weighted. Look at it
  upside down and out of focus; the two lower quadrants should feel about equally heavy.
* **And the process test that protects the product:** *is anything traced?* Every stroke must come
  out of `paperbomb_art.py`'s own path generators. Matching a measured width is not tracing;
  sampling a pixel is.

---

## 6. Resolution honesty — which rows RG cannot settle

RG samples the card at 3.917 px/mm. These rows are at or past that limit and are marked **HR?
yes** above. For each, RG's own number is an **upper bound** on fineness, HR describes the
character, and the tolerance is written to be satisfiable by either reading.

| Row | Why RG cannot settle it | What RG bounds | What HR contributes (character only) |
|---|---|---|---|
| 19 — ring hole shape | a 1 px striation is 0.26 mm | elongation ≥1.2, area fraction 0.228 | elongation 1.91, long axis 1.36 mm — **and area fraction 0.223, which agrees with RG to 2 %** |
| 35 — 爆 stroke modulation | thinnest filament is 1 px | ratio ≥4:1 | 22.6:1, itself floored by HR's grid |
| 84 — ink halo | one pixel of ramp is the sampling floor | ≤0.26 mm | 0.11–0.23 mm |
| 87 — grain cell | Nyquist cell is 0.51 mm | ≤0.41 mm | 0.128 × 0.125 mm, anisotropy 1.03 |

Everything else in this document — every position, size, proportion, weight, count, colour and
shape — is RG's, and RG's alone.

---

## 7. Measurement provenance

| Stage | Script | Output |
|---|---|---|
| shared loader, morphology, fitting | `rg_lib.py` | — |
| silhouette, chamfers, damage test | `rg_s1_silhouette.py` | `rg_s1_silhouette.json` |
| classification, rules, corners, ink inventory | `rg_s2_elements.py` | `rg_s2_elements.json` |
| rule insets, continuity, corner ornaments, named zones | `rg_s3_geometry.py` | `rg_s3_geometry.json` |
| ring ellipse, hero glyph, clearances | `rg_s3b_ring_glyph.py` | `rg_s3b_ring_glyph.json` |
| paper, ageing, reds, black, halo, seals | `rg_s4_ink.py` | `rg_s4_ink.json` |
| columns, flame, seals, HR sub-pixel character | `rg_s5_detail.py` | `rg_s5_detail.json` |
| column splitting, flame ladder and heart | `rg_s6_columns.py` | `rg_s6_columns.json` |
| ink-aware grain and mottle, chain, rule ink colour | `rg_s7_fix.py` | `rg_s7_fix.json` |
| seal isolation | `rg_s8_seals.py` | `rg_s8_seals.json` |
| consolidation and labelled overlay | `rg_s9_consolidate.py` | `reference_spec_realglyph.json` |

All under `WorkFiles/paperbomb/reference_metrology/`. Debug rasters are in `debug/` and are
labelled **DEBUG — NEVER SHIP**; see `debug/README-REALGLYPH-DEBUG-NEVER-SHIP.txt`. Nothing under
`Scripts/` imports any of it, and no derived reference artwork exists anywhere a build can read.

---

## 8. Corrections to the previous edition of this file

The previous edition took V1 (HR) as the authority for "every proportion, stroke, ornament and
colour". Re-measurement against RG changes these:

1. **The card's aspect is 0.43134, not 0.4468.** The height moves from 156.0 to **162.29 mm** at a
   fixed 70 mm width. Every vertical millimetre in the old file is 4 % short.
2. **There is no flanking leaf pair.** Old rows 17 and 20 came from V1's pseudo-glyph layout. In RG
   those marks are the foot of 業. (§3 item 2)
3. **The corners do carry outboard ink, and it is red.** The old file said "2.0–2.2 mm of ornament
   beyond the top and bottom rules at all four corners" and called our all-red overshoot a defect.
   RG says: 2.5–5.8 mm² per corner, reaching 1.9–2.2 mm, **red**, with black ≤0.91 mm². What is
   wrong in our build is that the outboard ink is **black**.
4. **The rules are not 1 : 1 continuous and not evenly weighted.** Zero-ink 4.6–11.3 % per side,
   3–6 breaks, longest 1.8–3.1 mm — and the **left** rule is the heaviest (0.68 mm) where the old
   file had them all at 0.57–0.68.
5. **The top rule changes colour.** 36 % of its length is dark, desaturated ink in one 15.3 mm run.
   No previous pass recorded this, because every previous pass measured the rules on the **red**
   mask alone and so reported the top rule as 25–56 % occupied.
6. **The ring is at (0.5025, 0.4762), 53.0 × 59.7 mm.** The old file's (35.47, 76.99) on a 156 mm
   card is fy 0.4935; RG puts it at **0.4762** — 2.8 mm higher on the new card.
7. **The flame emblem has four strokes, not five**, totalling **176 mm²** on the new card
   (≈169 mm² scaled to the old one, which is why the old 167 mm² figure survives the change). Its
   heart is a **solid comma with one paper channel**, and the emblem contains **no closed eye**.
8. **爆 is 0.828 W × 0.326 H**, not 0.847 W × 0.336 H — 2 % narrower as a fraction, and its
   clearance to 焼 is **6.32 mm**, at the bottom of the 6.5–8.5 mm the brief expected.
9. **The small chop is much smaller than the old file said**: 8.2 × 14.5 mm, not 9.0 × 17.8. The
   old reading included the bottom-right corner ornament, which touches the seal's right edge.
10. **The paper grain amplitude is 0.63 %, not 17 %.** The old figure was measured with an
    ink-blind high-pass, so every stroke edge counted as fibre. The same correction takes the
    mottle bands from 2–11 % down to 0.3–0.5 %.
11. **The edge ageing is 8.6 % deep with an 8.3 mm reach**, not 15 % deep recovering by 7.25 mm.
12. **The red value spread is 0.051 across the four named reds** (0.071 across all six), not 0.139
    and not 0.365. The *ordering* is the finding that survives: **the border rule is the heaviest
    red on the card and the small seal the lightest**, and ours is inverted.

---

*Machine-readable twin: `WorkFiles/paperbomb/reference_metrology/reference_spec_realglyph.json`.
Labelled overlay: `WorkFiles/paperbomb/reference_metrology/debug/DEBUG_NEVER_SHIP_RG_s9_overlay_LABELLED.png`
— **DEBUG, NEVER SHIP.***

### Round 6's corrections

* **Row 9's outboard corner ink was wrong by a factor of four.** The previous edition carried
  TL 4.56 / TR 2.54 / BL 5.80 / BR 5.87 mm² forward and set a 2.0–6.5 mm² band from it. Two
  instruments now read RG at 0.67–1.59 mm². Round 5 drew 2.64–2.97 to satisfy the wrong band and
  the four corners read as blobs of sealing wax. Band re-based to **0.55–2.00**, a quarter of the
  old window.
* **The hero-to-neighbour clearance had no honest instrument.** The build measured the horizontal
  distance in shared scanlines, capped at 6.0 mm, and reported its own cap. It is now a true 2-D
  nearest distance over the whole card with a 20 mm cap; on round 5's art the same instrument
  reads **2.0 mm** where the build reported 6.0.
* **The longest-break ceiling was calibrated to pass our own drawing**, not to the reference:
  3.50 mm against RG's own worst of 2.27–3.06. Now 2.80.
* **`ring_hole_elongation` exists.** Two briefs asked for it; it is row 94.
