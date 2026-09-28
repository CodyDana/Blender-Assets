# Shuriken photo measurement: decision document

**Date:** 2026-09-18. **For:** the user and the modeller.
**Inputs:** five public-domain Commons scans in `References/Shuriken/images/` (`provenance.json` has source, licence and SHA-1). Two independent methods measured each photo, then a reconciler resolved them. Built parameters come from the reports in `inputs/`.
**Ground rule:** photo numbers are proportions of the piece's own span. The 96 dpi headers are a re-save default. No photo gives an absolute size or a thickness. Any millimetre value for a photo feature is that proportion scaled to the study's build size.
**Contact sheet:** `contact_sheet.png`. Left: built or spec outline on the photo. On the juji row the green line is the raw edge trace, not smoothed. Right: the photo-matched set below, at the build size, apex to apex. Every caption names its IoU variant.

---

## Headline

Four of the five photographed pieces are different designs from what the pack built or specified. Only the senban is the same design, and its edge grind still differs.

- **Juji:** a waisted leaf cross. No parallel arm, no hub, no hole.
- **Happo:** a straight-edged star with V notches. No round hub, no hole.
- **Roppo:** straight triangular points on a large hub with a large bore. The hub is 0.488 and the bore 0.228 of the observed span, which is 46.5 and 21.7 mm at the 98 mm build size taken apex to apex.
- **Manji:** tapered arms and swept blade hooks. No hole.
- **Senban:** the sagitta is 0.0616 of the side (4.69 mm at the 76.2 mm build size). The hole is 0.264 of the side (20.1 mm at build size). A bevel runs the full perimeter.

Every thickness stays as the study gives it. At the study's span and plate, the photo outlines weigh 36.8 g (juji), 67.4 g (happo), 35.0 g (roppo), 69.9 g (senban with the kept 12.7 mm hole) and 37.1 g (manji).

- The juji and roppo land below sourced masses. Those masses belong to other objects with other outlines, so these two sets are hybrids. The gap is not a thickness error.
- The happo, senban and manji targets were DERIVED from modelled outlines, so the photo outlines re-derive them. The happo and senban stay inside the study's mass ranges.

---

## 1. Photo versus built or spec

| Form | Feature | Photo (mm at build size) | Built or spec | Significance |
|---|---|---|---|---|
| Juji | Arm profile | Waisted leaf: 6.04 mm neck at 0.30 R, 12.7 mm blade at 0.67 R | 11 mm parallel arm | different design |
| Juji | Hub | None. Four concave crotch fillets, R 5.5 mm, nearest point 7.57 mm from centre | 11 mm radius round hub | different design |
| Juji | Hole | None | 8 mm (ESTIMATE) | different design |
| Juji | Tip | 66.5 ± 2.5° over the last 5 % of span; 55.8° over the last 10 % | 40° | major |
| Juji | Grind | 4.9 mm per side at 0.7 R (about 80 % of the local half-width). The facets meet on an off-centre ridge through the neck and the outer fifth of the blade | 0.9 mm facet on the last 15 mm | major |
| Happo | Construction | Straight star {8/3.25}, inner/outer radius 0.458 | 22 mm radius hub, 10 mm parallel arms | different design |
| Happo | Point root | 17.5 mm chord | 10 mm arm | major |
| Happo | Notch | V, 78.8°, 1.24 mm root fillet, floor at 23.6 mm | Hub arc at 22 mm | different shape, depth minor |
| Happo | Tip | 33.6 ± 0.4° | 35° | minor |
| Happo | Hole | None | 9.5 mm (SOURCED) | different design |
| Roppo | Points | Straight triangles from the hub | 11 mm parallel arms, taper on the last 16 mm | different design |
| Roppo | Tip | 25.1 ± 0.5° | 38° | major |
| Roppo | Hub | 46.5 mm diameter (0.488 of the observed span) | 36 mm (18 mm radius) | major |
| Roppo | Hole | 21.7 mm bore (0.228 of the observed span), rounded rim | 8 mm (ESTIMATE) | major |
| Senban | Sagitta | 4.69 mm (0.0616 of the side); corners 61.9° | 6 mm (ESTIMATE); 54.2° implied | minor |
| Senban | Hole | 20.1 mm (0.264 of the side), sides parallel to the plate, 0.9 mm fillets | 12.7 mm (SOURCED) | major |
| Senban | Bevel | Full perimeter, 1.27 mm in plan, mitred corners | None specified; section 3 says tips only | different design |
| Manji | Arms | Taper from 11.2 to 8.5 mm (4.53° included) | 13 mm parallel | major |
| Manji | Hooks | Swept triangular blade, inner edge 75°, 24.5° point | 20 x 13 mm rectangle | different design |
| Manji | Arm end | One arc, R 98 mm | Square cut | major |
| Manji | Hole | None | None drawn; state was unknown | matches |
| Manji | Handedness | Reads 卍 as stored; the face shown and any mirroring by the uploader are unknown | 卍 required (a design rule) | no conflict; the photo does not confirm it |

Point counts, pitch and overall squareness match on every form.

---

## 2. Photo-matched parameter sets at the build size

**Rule.** The study's span and plate thickness stay, because the photos carry no scale or thickness. SOURCED shape values stay too. Only ESTIMATE, DERIVED and modelling-default shape values move to the photo. A DERIVED mass is re-derived from the photo outline, not held as a target. Every span is taken apex to apex, because the scans' blurred tips are not geometry. Areas are un-bevelled plan areas, as in the study's cross-checks. Mass uses 7.85 g/cm³. Outlines in mm are in `synthesis/photo_matched_outlines_mm.json`.

### 2.1 Juji, 97 mm, 3.0 mm

| Parameter | Study (status) | Photo-matched |
|---|---|---|
| Hole | 8 mm (ESTIMATE) | none |
| Hub | 11 mm radius (default) | none; crotch fillets R 5.5 mm, nearest point 7.57 mm from centre |
| Arm width | 11 mm (DERIVED) | station table below |
| Tip | 40° (default) | 67°, straight over the last 4.85 mm to a sharp apex |

**Span convention.** 97 mm is taken apex to apex. Extended, the photo's 67° flanks meet 0.013 R beyond the scan's blurred tips. The blur is not geometry, so the photo profile is scaled by 0.987 to put that sharp apex at 48.5 mm. The happo and roppo use the same convention.

**How the outline is built.**
- **Profile:** the median width profile of the 8 arm sides, smoothed with a degree-8 Chebyshev fit. The fit is within 0.03 mm rms of the data and has one inflection.
- **Crotch:** an exact R 5.5 mm arc centred on the diagonal. Its nearest point is 7.57 mm from centre (0.078 of the span). It is tangent to both arms and blends into the measured flank by 10.3 mm from centre, staying within 0.03 mm of the data. The photo's own four crotches read 7.2 to 7.7 mm at this scale.
- **Tip:** a 67° straight tip over the last 4.85 mm, blended in from 42.7 mm. The sharp apex sits 0.5 to 1.4 mm beyond the scan's blurred tips.
- **Symmetry and QA:** exact C4 plus mirror symmetry, resampled evenly at 0.2 mm, with no decimation. The loop has no reversals and no self-intersections. Its only corners over 30° are the four tips. The previous outline had four path reversals of more than 120° and twelve concave kinks.

Width against distance from the centre:

| mm | 7.3 | 9.7 | 12.1 | **14.5** | 19.4 | 24.3 | 29.1 | **32.7** | 38.8 | 43.7 | 46.1 | 47.5 | 48.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Width | 8.19 | 6.86 | 6.21 | **6.04** | 6.76 | 9.10 | 11.87 | **12.71** | 10.66 | 6.42 | 3.21 | 1.28 | 0 |

The inflection is at 25.3 mm (0.52 R; reconciled 0.53 ± 0.04). Build an ogee: concave flank, convex leaf, short straight tip.

**Area 1563.1 mm²** (0.166 of span squared), giving **36.81 g** at the SOURCED 3.0 mm. At equal scale the repairs add 2.5 mm². The rest of the change from the previous 1600.5 mm² comes from taking the span apex to apex. If the 97 mm is read as the blunt tip-to-tip instead, everything scales up 1.3 %: 1603.0 mm² and 37.75 g. The IoU against the photo contour is 0.961. The piece's own 90° self-IoU is 0.944, so a symmetric model cannot do much better.

**Mass reading.** The sourced 97 mm, 3.0 mm and 39 g all come from one object, a museum-shop replica whose outline the build approximated. This photo shows a different piece. The set above therefore puts this photo's outline on that replica's size and plate. Its 2.2 g shortfall reflects that mix and is not a thickness error.
- Keep 3.0 mm.
- A 3.18 mm plate would hold 39 g, but only by overriding a SOURCED value. That is the user's call.
- If a ground piece of this outline weighed 39 g, its plate would have to be thicker than 3.18 mm. The grind removes volume that a plan scan cannot measure.

Surface features are material masks, not geometry:
- an unground lens 17.5 x 3.5 mm, running from 20.7 to 38.2 mm;
- a central diamond 14.1 x 16.4 mm.

### 2.2 Happo, 100 mm, 2.5 mm

| Parameter | Study (status) | Photo-matched |
|---|---|---|
| Hole | 9.5 mm (SOURCED) | kept by rule; the photo has none |
| Hub and arms | 22 mm hub, 10 mm arms (DERIVED) | V-notch star: notch vertex 22.88 mm, root chord 17.51 mm |
| Tip | 35° (default) | 33.75°, implied by the radius ratio (measured 33.6 ± 0.4) |
| Notch | hub arc | 78.75°, 1.24 mm root fillet, floor at 23.59 mm |

**Area:** 8 x 50 x 22.88 x sin 22.5° = 3502.3 mm². The fillets add 4.1 mm² and the hole removes 70.9 mm², for **3435.6 mm²**.

**Mass 67.42 g** at the SOURCED 2.5 mm, or 68.81 g without the hole. This re-derives the study's 60 g, which was DERIVED from the modelled hub-and-arm outline. 67.4 g is inside the study's 53 to 79 g.

XXVIM.21's 57.5 g is not a like-for-like check. That object is 102 mm across, has trident points and has a 3 mm hole near the rim.

**IoU** against the reconciled mask: 0.968 for this set with the kept 9.5 mm hole, and 0.988 for the hole-free variant.

### 2.3 Roppo, 98 mm, 2.0 mm

| Parameter | Study (status) | Photo-matched |
|---|---|---|
| Hole | 8 mm (ESTIMATE) | 21.74 mm bore, 0.33 mm rim round |
| Hub | 18 mm radius (default) | 23.26 mm radius |
| Arm | 11 mm parallel (DERIVED) | triangle, 11.80 mm root chord at 22.50 mm |
| Tip | 38° (default) | 25.1° |

98 mm is taken apex to apex. The exposed hub arc is 30.6° per gap. **Area:** the hub (1699.8 mm²) plus six points of 150.3 mm², minus the bore (371.0 mm²), gives **2230.7 mm²**.

**Mass 35.02 g** at the SOURCED 2.0 mm.
- **Why it misses 40 g:** the sourced 98 mm, 2 mm and 40 g come from one retail object whose outline is unknown. The spec outline was sized to reproduce that mass (2505 mm², 39.3 g). This set puts this photo's outline on that object's size and plate, so the 5 g gap is not a thickness error.
- **Thickness:** keep 2.0 mm. A 2.28 mm plate would hold 40 g, but only by overriding a SOURCED value.
- **Alternative span reading:** if the 98 mm is the blunt observed span instead, everything scales up 2.8 %, to 2357 mm² and 37.0 g.

**IoU** 0.956 against method A's mask, and 0.933 against method B's mask, which counts the scanner shadow band as metal.

### 2.4 Senban, 76.2 mm side, 1.9 mm

| Parameter | Study (status) | Photo-matched |
|---|---|---|
| Sagitta | 6 mm (ESTIMATE) | 4.69 mm; arc R 157.0 mm; corners 61.9° |
| Hole | 12.7 mm (SOURCED) | 12.7 mm kept, sides parallel to the plate, 0.89 mm fillets |
| Option B | | the photo's 20.1 mm, inside the sourced 12.7 to 25.4 mm |

**Area:** 76.2² minus four segments of 239.2 mm² is 4849.7 mm². Minus the kept hole, it is **4689.1 mm²**, giving **69.94 g** at the SOURCED 1.9 mm.

This re-derives the study's 66 g, which was DERIVED from the spec outline and equals that outline's own 65.9 g. 69.9 g is inside the study's 45 to 82 g. The IoU with the kept 12.7 mm hole is 0.931.

**Option B rests on photo evidence only.** The photographed hole is 0.264 of the side, which is 20.1 mm at build size and inside the study's sourced 12.7 to 25.4 mm. Adopting it would replace the one retailer's 12.7 mm. That choice is about which sourced value to follow; it is not a mass fix. Option B gives 4445.7 mm², 66.31 g and an IoU of 0.962.

**Bevel mass is an assumption-driven estimate.** The scan gives the bevel's plan width (1.27 mm) but not its depth, profile or far face. Assume a plain chamfer 1.27 mm wide along the 308 mm outer perimeter:
- cut to half the plate (0.95 mm) on one face, it removes 1.45 g;
- cut through the full 1.9 mm on one face, or to half depth on both faces, it removes 2.90 g.

The delivered outline has a corner on +X, rotated 45° from the photo's framing, which rests on a side. Both holes rotate with it, so their sides stay parallel to the plate's chords.

### 2.5 Manji, 100 mm, 2.5 mm

No manji size is sourced, so the study's ESTIMATE stays.

| Parameter | Placeholder | Photo-matched |
|---|---|---|
| Arms | 13 mm parallel | 11.24 mm at the centre to 8.51 mm at the hook; central square 10.81 mm |
| Hook | 20 x 13 mm rectangle | triangle: inner corner 34.41 mm out, inner edge 75.05°, tip at r 50 mm, 35.0° counter-clockwise of the arm |
| Arm end | square | one arc, R 98 mm, running into the hook back; across the arms 82.9 mm |
| Corners | right angles | concave corners filleted 0.56 mm; elbows and tips sharp |

**Area 1890.0 mm²** (the masks read 1.6 % more), giving **37.09 g** at the ESTIMATE 2.5 mm. This re-derives the study's 60.5 g, which was DERIVED from the placeholder outline; the placeholder has 60 % more area. The IoU against the contour mask is 0.978. The outline has an arm axis on +X, with each tip 35° counter-clockwise of its arm.

### Mass summary

| Form | Area mm² | Mass at the study's plate | Study mass (status) | Reading |
|---|---|---|---|---|
| Juji | 1563.1 | 36.81 g at 3.0 mm (SOURCED) | 39 g SOURCED, from another object's outline | hybrid; 37.75 g if 97 mm is the blunt tip-to-tip |
| Happo | 3435.6 | 67.42 g at 2.5 mm (SOURCED) | 60 g DERIVED | re-derived; inside 53 to 79 g |
| Roppo | 2230.7 | 35.02 g at 2.0 mm (SOURCED) | 40 g SOURCED, from another object's outline | hybrid; 37.01 g if 98 mm is the observed span |
| Senban | 4689.1 | 69.94 g at 1.9 mm (SOURCED) | 66 g DERIVED | re-derived; inside 45 to 82 g; option B 66.31 g |
| Manji | 1890.0 | 37.09 g at 2.5 mm (ESTIMATE) | 60.5 g DERIVED | re-derived |

All masses are un-bevelled. No thickness moves. Overriding a SOURCED plate to hold a sourced mass (juji 3.18 mm, roppo 2.28 mm) is a user decision, listed in section 8. If these outlines are adopted, the physics Mass overrides in study section 4 (0.04, 0.06, 0.06, 0.04 and 0.06 kg) should follow the masses above.

---

## 3. Can the radial-star generator express them?

This reading comes from the report parameters (hub-to-hole bridge, parallel run, taper, hub arcs). The code in `Scripts/` was not read.

| Form | Verdict |
|---|---|
| Roppo | **Yes, by parameters.** Hub 23.26 mm, hole 21.74 mm, tip 25.1°, arm width 11.80 mm so the taper starts at the hub root. If a zero-length run trips the zero-length-edge gate, use 11.56 mm for a 0.5 mm run. Bevel the whole flank. |
| Happo | **New mode.** A 17.5 mm arm shrinks the hub arcs to 0°, leaving zero-length edges. It needs a star-polygon mode: 16 straight edges with filleted V roots. |
| Juji | **New family.** It needs a profiled arm (width as a function of radius, or the delivered D4 fundamental edge), a zero hub, concave crotch fillets, no hole ring and a wide full-outline grind. |
| Senban | Not a radial star. New outline numbers only, but the mitred perimeter bevel is a topology change. |
| Manji | Not a radial star. It needs an L-arm family. |

One generalisation covers all three stars: a width profile per arm, a hub radius of zero or more, and an optional V-notch mode.

---

## 4. Scale: the 300 dpi hypothesis

| Photo | Span px | At 300 dpi | Versus build-to | Sourced range mm | Build-to mm | dpi for build-to |
|---|---|---|---|---|---|---|
| Juji | 1324 blunt, 1341 apex | 112.1 / 113.5 mm | +15.6 % / +17.0 % | 70 to 114 | 97 | 347 / 351 |
| Happo | 1264 (sharp) | 107.0 mm | +7.0 % | 89 to 146 | 100 | 321 |
| Roppo | 1177 observed, 1210 apex | 99.7 / 102.4 mm | +1.7 % / +4.5 % | 82 to 135 | 98 | 305 / 314 |
| Senban | 852 side | 72.2 mm | -5.3 % | 57 to 102 | 76.2 | 284 |
| Manji | 2843 | 240.7 mm | +141 % | none | 100 (ESTIMATE) | 722 |

At 300 dpi the four small scans deviate from their build sizes as follows:

| Photo | Deviation at 300 dpi |
|---|---|
| Juji | +15.6 % (+17.0 % apex to apex) |
| Happo | +7.0 % |
| Roppo | +1.7 % (observed span) or +4.5 % (apex span) |
| Senban | -5.3 % |

- No single dpi reproduces all four build sizes; that would take anywhere from 284 to 351 dpi.
- Any single dpi from 295 to 361 puts all four scans inside their sourced ranges (299 to 361 on the juji's apex reading), and 300 falls in that window. But the ranges are too wide for this test to carry weight.
- The manji needs about 600 dpi to be plausible, so no one setting fits all five.

**Circumstantial at best. Use proportions only.**

---

## 5. Manji: hole and handedness

- **Hole:** none. The centre is solid rusted plate with no punch mark. This answers study open question 5 for this piece only.
- **Handedness:** the file as stored reads 卍. The top hook turns left and the right hook turns up.
  - It passes the study's gate: the +Y arm's hook is at negative X, and the +X arm's hook is at positive Y. The exported outline keeps this.
  - The scan cannot show which face the maker presented, and a plate reads 卐 from behind. A mirrored upload also cannot be ruled out.
  - So 卍 remains a design rule, not something this photo confirms. Section 2.6's storefront warning stands.
- **Extreme points:** they sit 35.0° off the arm axis, not on the diagonals as section 2.6 says.

---

## 6. Sharpening evidence against study section 3

Section 3 says to grind short facets near the points and leave long edges square. Each scan shows one face only.

| Form | Photo evidence | Section 3 |
|---|---|---|
| Happo | Both edges of every point: 1.1 mm at the tip, gone about 18 mm along the edge | consistent |
| Manji | Hook back edge only: 0.7 mm wide, 17 mm long | consistent |
| Roppo | 0.75 mm band on both flanks of all points, root to tip; none on the hub or bore | partly |
| Senban | 1.27 mm bevel round the whole perimeter, mitred at the corners | contradicted |
| Juji | Ground from every edge, 4.9 mm per side at 0.7 R (about 80 % of the half-width); the facets meet on an off-centre ridge through the neck and the outer fifth of the blade | contradicted |

The convention holds on two of five. Make it a per-form choice, not a pack rule.

---

## 7. Juji and the Naruto traits in study section 5

**Net: further away, with two risks to manage.**

- **Large open round hole:** gone. This is the strongest trait, and it is removed outright.
- **Four thin prongs:** closer at the neck. 6.04 mm is 55 % of the 11 mm that section 5 relies on. But the 12.7 mm blade reads as a leaf, not a prong.
- **Arrow-headed tips:** ambiguous. A broad head on a narrow neck is arrow-like. A 67° convex tip with no shoulders is not.
- **Flat grey blades, dark hub:** there is no hub. But a literal texture of the dark diamond against bright facets could read as a dark hub. Keep the blackened finish and a low-contrast diamond.

If the photo form is adopted, section 5's differentiators become "no hole, leaf blades".

---

## 8. Open questions

1. **Absolute scale.** No photo has one. Ask the uploader, or find a measured specimen.
2. **Provenance.** Author and dates are unknown. The pieces may be antiques or replicas, possibly one maker's set.
3. **Thickness and far-face grind** are invisible in every scan. Because of the juji's grind, a 39 g piece of that outline would need a plate thicker than 3.18 mm.
4. **Holes.** Keep the happo's SOURCED 9.5 mm hole, or match the hole-free photo? For the senban, keep the retailer's 12.7 mm hole or adopt the photo's 20.1 mm? Decide on the photo evidence, not on mass.
5. **Hybrid sets.** The juji and roppo sets use other objects' sizes and plates.
   - Keep the SOURCED 3.0 and 2.0 mm plates (recommended), giving 36.8 g and 35.0 g.
   - Or deliberately override them (3.18 mm and 2.28 mm) to hold the sourced 39 g and 40 g.
   - Either way, update the section 4 physics masses to match.
6. **Span readings.** Every set is taken apex to apex. The alternatives are a 1.3 % larger juji or a 2.8 % larger roppo.
7. **Hand-forged variation.** The juji varies 2 to 6 % between arms, and its crotches read 7.2 to 7.7 mm. Model any of it?
8. **Generator.** Its owner must confirm that a zero or 0.5 mm parallel run is allowed for the roppo.
9. **Clipped tips.** The juji top, the happo SSW tip and one roppo tip were extrapolated.

---

## Files

- `contact_sheet.png`, rendered by `synthesis/s6_contact.py`.
- `synthesis/synthesis_numbers.json`: every number in section 2, the IoU of each variant, the bevel assumption and the outline QA.
- `synthesis/photo_matched_outlines_mm.json`: outlines in mm in Blender top view, outer loops CCW and evenly resampled.
  - Orientation follows study section 4. The juji, happo and roppo have a tip on +X. The senban has a corner on +X. The manji has an arm axis on +X, with its tips 35° counter-clockwise of each arm, which keeps the handedness gate readable.
  - The juji entry also carries its D4 fundamental edge. The senban's hole entries include their loops.
- `synthesis/*_photo_matched*.png` and `synthesis/roppo_spec_at_apex_span.png`: full-resolution panels.
- `synthesis/fix/`: 4x crops of the rebuilt juji at the crotches and tips, and the pre-edit s2 outputs (`*_before_s5.json`).
- Scripts, run in order in Blender 5.2 headless:
  1. `synthesis/s1_juji_profile.py`
  2. `s2_synthesis.py`
  3. `s5_fix.py`: the juji rebuild, the senban orientation, the IoU variants and the QA. It supersedes s2 for those items.
  4. `s6_contact.py`: supersedes `s4_contact.py`.

  `s3_roppo_diff.py` is a check.
- Per-photo evidence: `juji/`, `happo/`, `roppo/`, `senban/`, `manji/`.
