# Paper bomb: ink and colour metrology

Measured 2026-09-19 against both reference images and against our shipped
basecolour map. Machine-readable companion: `ink_colour.json` in this folder.

**Legal / product note.** Every figure here is a measurement. No pixel of either
reference was reproduced, traced, masked, thresholded, vectorised or otherwise
derived into anything a build can consume. The rectified arrays live only in the
session scratchpad. The only images written under the project are schematics
drawn from these numbers, in `debug/`, prefixed `DEBUG_NEVER_SHIP`.

## Conventions

- Origin is the **tag's top-left paper corner**, not the image canvas. `u = x/W`,
  `v = y/H`, and millimetres on the shipped 70.0 x 156.0 mm card via `u*70`, `v*156`.
- **stored** = the 8-bit number in the PNG over 255 (sRGB-encoded). **linear** =
  the sRGB EOTF applied. A PNG carries no colourspace tag, so this was pinned down
  by decoding the IDAT directly and comparing against Blender's `Image.pixels`,
  which returned the stored value to the last bit. Every hex here is stored sRGB.
- **alpha** (ink opacity) = `1 - linear_G / local_paper_field_G`. The paper field is
  a masked blur of paper pixels at 4.5 % of tag width, refined three times, so edge
  darkening and stains belong to the paper and are never miscounted as ink.
- **ink mass fraction** = mean of alpha over the paper. Unlike an area count it
  weights kasure holes and soft halos correctly, so it is what the eye integrates.
- Area fractions are fractions of the paper **octagon** (rectangle less the four
  chamfers), with a 0.30 mm rim excluded.

## Rectification

**Neither reference needed correcting.** Both are axis-aligned to better than
0.04 degrees and square to better than 0.05 %:

| | V1 | V2 |
|---|---|---|
| left edge off vertical | -0.0029 deg | -0.0022 deg |
| right edge off vertical | -0.0019 deg | +0.0033 deg |
| top edge off horizontal | +0.0019 deg | +0.0082 deg |
| bottom edge off horizontal | -0.0247 deg | -0.0355 deg |
| width top / bottom | 0.99996 | 0.99978 |
| height left / right | 1.00021 | 1.00033 |
| tag size in source px | [616.13, 1379.09] | [274.38, 636.14] |
| sampling | 8.802 px/mm | 3.920 px/mm |
| aspect h/w | 2.2380 | 2.3178 |
| corner chamfer, mean along an edge | 8.09 mm | 7.96 mm |

Correction applied: a sub-pixel crop to the fitted paper rectangle, then a
bilinear resample to a common 840 x 1872 grid (12 px/mm). Nothing else. Every
high-frequency statistic below (fibre spectrum, kasure hole size, edge roughness)
was measured at **native** resolution so the resample stays out of it.

One thing that went wrong and is worth recording: an adaptive threshold set from a
high percentile landed *above* the paper level and traced the ink instead of the
paper, giving V1 a spurious 5.85 degree bottom edge. The half-maximum between the
measured background and paper levels is what fixed it.

## The headline

- **ink coverage** - V1 total ink mass 0.3035 of the tag, V2 0.3345, ours 0.2221. The earlier review's 'about a fifth less' is an understatement: 26.8 % less than V1, 33.6 % less than V2.
- **which elements are short** - black, not red. Black ink mass is 39.1 % short (0.1742 -> 0.1061); red is 17.3 % short (0.1161 -> 0.0960). The black:red area ratio has collapsed from 1.449 to 1.002. Worst elements, in order: the four text columns at 44-68 % short (measured against V2 de-smeared, because V1's columns are pseudo-glyphs and would let us off), the centre glyph at 46.4 % short, the enso ring at 27.1 % short, the seal block at 19.3 % short. One element is OVER-inked: the flame emblem, 44.5 % heavy, on which both references agree.
- **but coverage is not the main problem** - the contrast ratio is. Paper:ink luminance is 153.5:1 in V1, 202.7:1 in V2, 11.2:1 in our basecolour and 15.9:1 in our render. Even if coverage were matched exactly, ink at 1/11 of paper luminance would still read airy.
- **reds** - same pigment throughout the reference - hue spread 1.14 deg, saturation spread 0.021 - laid at four different weights (alpha_R 0.375 to 0.590). Ours is one weight at one third less saturation.
- **paper** - hue is right (40.1 deg vs 40.4), saturation is close (0.228 vs 0.198), value is 25 % too dark, the rim burn is too deep and too broad, and it is 12.4 points uneven between the left and right edges where the reference is even to 1.5 points.

## Paper

| | V1 | V2 | OURS |
|---|---|---|---|
| base colour, centre 44 % box (stored sRGB) | #F6E6C5 | #F6E5C3 | #DAC9A8 |
|   same, 8-bit | 246, 230, 197 | 246, 229, 195 | 218, 201, 168 |
|   hue, deg | 40.35 | 40.01 | 40.06 |
|   saturation | 0.1978 | 0.2076 | 0.2279 |
|   value | 0.9628 | 0.9651 | 0.8549 |
|   linear RGB | 0.917411, 0.788007, 0.558078 | 0.922449, 0.783538, 0.544561 | 0.701102, 0.586657, 0.391619 |
|   linear luma | 0.7989 | 0.7958 | 0.5969 |
| edges, outer 2 mm band (stored sRGB) | #EFD39F | #F1D5A5 | #C7B594 |
| plateau linear luma (beyond 12 mm in) | 0.78169 | 0.78292 | 0.57573 |
| rim darkening depth | 15.70 % | 14.31 % | 21.90 % |
| half-recovery distance | 4.75 mm | 3.75 mm | 4.25 mm |
| 95 % of plateau at | 7.25 mm | 5.25 mm | 14.75 mm |
| 99 % of plateau at | 19.25 mm | 12.75 mm | - |
| evenness: spread across the 4 sides | 0.0154 | 0.0287 | 0.1240 |
| global lighting gradient across width | +0.75 % | +0.44 % | -2.51 % |
| global lighting gradient down height | -0.79 % | -0.48 % | +5.31 % |

The reference's edge darkening is a **broad, gentle, even vignette**: about 15 % of
paper luminance at the rim, half recovered by 4.75 mm, 95 % recovered by 7.25 mm,
and the four sides agree to 1.5 points. Ours is deeper (21.9 %), reaches three
times further (95 % only at 14.75 mm) and is 12.4 points uneven side to side.

### Mottle and stains

| | V1 | V2 | OURS |
|---|---|---|---|
| mottle RMS, % of paper luma | 2.020 | 2.160 | 2.478 |
| correlation length (blotch size) | 0.789 mm | 0.853 mm | 1.050 mm |
| power at wavelengths 3-10 mm | 0.7105 | 0.7334 | 0.8631 |
| power at wavelengths 1-3 mm | 0.2879 | 0.2665 | 0.1363 |
| spectrum log-log slope | -5.21 | -6.39 | -6.69 |
| stains darker than 3 %, count | 382 | 338 | 366 |
|   their area | 0.04063 | 0.03783 | 0.06818 |
|   median equivalent diameter | 0.857 mm | 0.787 mm | 0.940 mm |
|   median elongation | 1.58 | 1.74 | 1.97 |
| stains darker than 6 %, count | 86 | 94 | 120 |
|   their area | 0.00354 | 0.00494 | 0.01298 |
| stains darker than 10 %, count | 0 | 3 | 15 |

The mottle spectrum is **red** in all three (power falls with frequency, slope
about -5 to -7), so there is no periodic 'grain wavelength' to match; the honest
descriptors are the correlation length and the band powers. Our amplitude is right
and our scale is wrong: too much 3-10 mm, half the reference's 1-3 mm content.

### Folds, creases and implied shadow

Neither reference has any. The band-pass detector finds no line spanning either
tag, and the global lighting gradient is small in both. They are flat, evenly lit
sheets. Our basecolour carries two horizontal crease lines, at 51.6 mm (v 0.331)
and 104.4 mm (v 0.669), covering 46 % and 51 % of the tag width. The mesh already
has real creases, so that is shading counted twice, and it is shading the reference
does not have at all.

### Paper fibre texture (measured at native resolution)

| | V1 | V2 | OURS |
|---|---|---|---|
| native sampling | 8.802 px/mm | 3.920 px/mm | 12.923 px/mm |
| Nyquist | 4.40 cyc/mm | 1.96 cyc/mm | 6.46 cyc/mm |
| clean patches found | 3 | 2 | 2 |
| grain amplitude, % of paper luma | 17.02 | 25.22 | 9.80 |
| dominant cell size | 0.499 mm | 2.355 mm | 2.786 mm |
| anisotropy max/min | 1.90 | 5.79 | 17.25 |
| preferred orientation | 85 deg | 15 deg | 125 deg |

Use **V1 only**. V2's Nyquist is 1.96 cyc/mm, so its 2.35 mm 'cell' and its 5.79
anisotropy are measuring its own downsample. V1 says a 0.50 mm cell (4.4 source px)
at 17.0 % amplitude, close to isotropic at 1.90. Ours is 9.8 % amplitude and
strongly streaked at 17.2 - though that rests on only two clean patches, so treat
the 125 degree angle as indicative and the streak itself as real.

## Black ink

| | V1 | V2 | OURS |
|---|---|---|---|
| core colour (stored sRGB) | #0F100D | #0C0D0A | #41403E |
|   8-bit | 15, 16, 13 | 12, 13, 10 | 65, 64, 62 |
|   linear luma | 0.00509 | 0.00386 | 0.05138 |
| neutrality R-B (stored) | 0.0077 | 0.0064 | 0.0118 |
| median value in the stroke core, 8-bit | 16 | 13 | 65 |
| p1 of value, 8-bit | 6 | 4 | 62 |
| minimum value reached, 8-bit | 0 | 0 | 62 |
| minimum linear luma | 0.000035 | 0.000049 | 0.046985 |
| p0.1 linear luma | 0.000656 | 0.000655 | 0.046985 |
| p1 linear luma | 0.001872 | 0.001268 | 0.046985 |
| alpha, median | 0.9930 | 0.9935 | 0.9072 |
| alpha, p5 | 0.6492 | 0.5246 | 0.6289 |
| within-stroke p5-p95 swing, /255 | 13.4 | 17.1 | 14.3 |
| modulation depth (swing / own median) | 0.838 | 1.315 | 0.220 |
| **paper : ink contrast ratio** | 153.5 : 1 | 202.7 : 1 | 11.2 : 1 |

Our shipped **render** reaches 15.9 : 1 (paper linear luma 0.3858, ink 0.0243), so
lighting recovers some of the gap but nowhere near it.

**Flat fill or loaded-to-dry?** Neither reference ramps. Fitting alpha against
height inside every element gives the reference a slope of -0.001 to +0.001 - its
black is opaque at alpha 0.99 at the top of a column and 0.99 at the bottom. All of
its dry-brush character comes from **holes punched clean through a solid fill**, not
from a density ramp. Ours does the opposite: a semi-transparent wash at alpha
0.84-0.92 that additionally fades 3.5 to 6.7 alpha points down each column.

## Reds

| | V1 | V2 | OURS |
|---|---|---|---|
| border: stored sRGB | #A3180F | #C0170B | #B75046 |
|   hue deg | 3.96 | 3.91 | 5.31 |
|   saturation | 0.9115 | 0.9398 | 0.6196 |
|   value | 0.6395 | 0.7546 | 0.7191 |
|   alpha_R over paper | 0.5903 | 0.4146 | 0.2291 |
|   alpha_G over paper | 0.9870 | 0.9882 | 0.8453 |
|   hue variation within a stroke, std deg | 0.88 | 1.26 | 2.83 |
|   value variation within a stroke, std | 0.0949 | 0.1064 | 0.0123 |
| ring: stored sRGB | #C32315 | #CE190C | #B95348 |
|   hue deg | 5.00 | 3.91 | 5.80 |
|   saturation | 0.8924 | 0.9421 | 0.6092 |
|   value | 0.7633 | 0.8097 | 0.7255 |
|   alpha_R over paper | 0.4079 | 0.3294 | 0.2894 |
|   alpha_G over paper | 0.9781 | 0.9877 | 0.8463 |
|   hue variation within a stroke, std deg | 1.41 | 1.29 | 4.08 |
|   value variation within a stroke, std | 0.0549 | 0.0570 | 0.0182 |
| seal block: stored sRGB | #BF1B10 | #C8150A | #B74C43 |
|   hue deg | 3.86 | 3.65 | 4.72 |
|   saturation | 0.9138 | 0.9499 | 0.6354 |
|   value | 0.7498 | 0.7836 | 0.7177 |
|   alpha_R over paper | 0.4301 | 0.3770 | 0.3338 |
|   alpha_G over paper | 0.9855 | 0.9899 | 0.8766 |
|   hue variation within a stroke, std deg | 1.33 | 0.77 | 2.71 |
|   value variation within a stroke, std | 0.0823 | 0.0747 | 0.0115 |
| small seal: stored sRGB | #C61E13 | #D71D11 | #B74F45 |
|   hue deg | 4.10 | 4.08 | 5.23 |
|   saturation | 0.9016 | 0.9216 | 0.6244 |
|   value | 0.7784 | 0.8433 | 0.7177 |
|   alpha_R over paper | 0.3750 | 0.2542 | 0.2740 |
|   alpha_G over paper | 0.9824 | 0.9832 | 0.8532 |
|   hue variation within a stroke, std deg | 1.11 | 2.33 | 3.22 |
|   value variation within a stroke, std | 0.0863 | 0.0872 | 0.0166 |
| hue spread across the four | 1.140 deg | 0.420 deg | 1.080 deg |
| saturation spread across the four | 0.0214 | 0.0283 | 0.0262 |
| value spread across the four | 0.1388 | 0.0887 | 0.0078 |
| weight spread, alpha_R | 0.2152 | 0.1604 | 0.1047 |

**Is it the same red?** In the reference, yes as a pigment and no as a laid-on
weight. Hue spread is 1.14 degrees and saturation spread 0.021 - a single ink -
but value spreads 0.139 and alpha_R runs from 0.375 at the small seal to 0.590 at
the border. The border is deliberately the **heaviest** red on the sheet. In our
build all four reds are the same colour *and* the same weight (value spread 0.008),
the border is our lightest rather than our heaviest, and every one of them is about
a third short on saturation: blue channel 72/255 against the reference's 21/255.

Red opacity over paper is strongly channel-split in both: alpha_G is 0.98 in the
reference (the paper's green is almost entirely absorbed) while alpha_R is only
0.38-0.59. That split is what makes it read as red rather than as a dark mark, and
ours is much weaker on both (alpha_G 0.85, alpha_R 0.23-0.33).

## Coverage

| | V1 | V2 | OURS |
|---|---|---|---|
| total ink mass fraction | 0.3035 | 0.3345 | 0.2221 |
| solid area fraction (alpha > 0.5) | 0.2986 | 0.3310 | 0.2313 |
| black ink mass | 0.1742 | 0.1943 | 0.1061 |
| red ink mass | 0.1161 | 0.1229 | 0.0960 |
| black area / red area | 1.449 | 1.502 | 1.002 |
| centre glyph, black - ink mass | 0.10521 | 0.10356 | 0.05643 |
| enso ring, red - ink mass | 0.05871 | 0.06171 | 0.04280 |
| upper-left column 火遁術 - ink mass | 0.01210 | 0.02076 | 0.00607 |
| upper-right column 爆炎陣 - ink mass | 0.01191 | 0.02195 | 0.00668 |
| lower-right 焼尽 - ink mass | 0.00947 | 0.01516 | 0.00697 |
| lower-centre 瞬業 - ink mass | 0.00924 | 0.01722 | 0.00870 |
| flame emblem - ink mass | 0.01581 | 0.01653 | 0.02285 |
| seal block, red - ink mass | 0.03164 | 0.03315 | 0.02548 |
| small seal 火道, red - ink mass | 0.00915 | 0.00881 | 0.00587 |
| border zone, red - ink mass | 0.00925 | 0.01745 | 0.00543 |

## Enso ring

| | V1 | V2 | OURS |
|---|---|---|---|
| centre u | 0.5067 | 0.5067 | 0.5267 |
| centre v | 0.4950 | 0.4750 | 0.5050 |
| centre, mm | 35.467, 77.22 | 35.467, 74.1 | 36.867, 78.78 |
| polar outer radius | 31.623 mm | 31.290 mm | 30.014 mm |
| polar inner radius | 25.474 mm | 24.984 mm | 25.738 mm |
| stroke width | 6.148 mm | 6.306 mm | 4.276 mm |
| ellipticity h/w | 1.1538 | 1.0996 | 1.2648 |
| outer edge roughness RMS | 0.9421 mm | 1.0419 mm | 0.4978 mm |
| inner edge roughness RMS | 0.7903 mm | 0.7327 mm | 0.6205 mm |
| outer raggedness, cycles per revolution | 45 | 34 | 26 |
| outer raggedness wavelength | 4.415 mm | 5.782 mm | 7.253 mm |

## Dry brush (kasure)

| | V1 | V2 | OURS |
|---|---|---|---|
| ring: hole count | 170 | 160 | 60 |
|   holes per 100 mm2 of stroke | 19.57 | 17.27 | 9.31 |
|   hole area / stroke area | 0.2103 | 0.1908 | 0.0902 |
|   median hole diameter | 0.305 mm | 0.220 mm | 0.312 mm |
|   p95 hole diameter | 2.843 mm | 2.915 mm | 2.321 mm |
|   median hole elongation | 4.24 | 4.45 | 4.75 |
|   mean alpha inside the stroke envelope | 0.7431 | 0.7335 | 0.7425 |
| centre glyph: hole count | 182 | 193 | 71 |
|   holes per 100 mm2 of stroke | 14.50 | 15.53 | 9.72 |
|   hole area / stroke area | 0.0727 | 0.0603 | 0.0690 |
|   median hole diameter | 0.249 mm | 0.210 mm | 0.312 mm |
|   p95 hole diameter | 1.919 mm | 1.817 mm | 2.271 mm |
|   median hole elongation | 3.91 | 4.47 | 3.40 |
|   mean alpha inside the stroke envelope | 0.9065 | 0.9031 | 0.8391 |
| all black outside the ring: hole count | 251 | 291 | 226 |
|   holes per 100 mm2 of stroke | 28.46 | 24.44 | 31.12 |
|   hole area / stroke area | 0.0967 | 0.0844 | 0.1227 |
|   median hole diameter | 0.249 mm | 0.326 mm | 0.339 mm |
|   p95 hole diameter | 1.492 mm | 1.472 mm | 1.447 mm |
|   median hole elongation | 3.92 | 2.89 | 3.16 |
|   mean alpha inside the stroke envelope | 0.8565 | 0.8314 | 0.7518 |
| ring holes within 30 deg of the stroke direction | 0.8269 | 0.7867 | 0.8750 |

Random orientation would give 0.333, so the reference's holes are strongly
**elongated along the stroke**, which is what a splitting brush does. Ours are too,
at a similar median elongation and a similar median size. The gap is purely in
**how many** and in how dark the surrounding ink is.

## Stroke edge roughness and bleed

| | V1 | V2 | OURS |
|---|---|---|---|
| black: mean boundary deviation | 0.0675 mm | 0.0505 mm | 0.0488 mm |
| black: mean lobe spacing along the edge | 2.802 mm | 3.036 mm | 2.858 mm |
| red: mean boundary deviation | 0.0629 mm | 0.0317 mm | 0.0675 mm |
| red: mean lobe spacing along the edge | 3.094 mm | 4.298 mm | 5.881 mm |
| black edge 10-90 transition width | 0.2254 mm | 0.4006 mm | 0.2496 mm |
|   same, in native pixels | 1.98 px | 1.57 px | 3.23 px |
|   one native pixel | 0.1136 mm | 0.2551 mm | 0.0774 mm |
|   soft halo beyond anti-aliasing | 0.1118 mm | 0.1455 mm | 0.1722 mm |
|   outward distance to 10 % of plateau | 0.1176 mm | 0.1792 mm | 0.1418 mm |
| red: soft halo beyond anti-aliasing | 0.1154 mm | 0.1545 mm | 0.1965 mm |

Any raster shows about one native pixel of anti-aliasing at a stroke edge, so only
the excess is bleed. V1's excess is 0.112 mm - the reference has very little bleed,
its edges are crisp and its softness is all kasure. Ours is 0.172 mm on top of a
finer pixel, so our edges are genuinely softer.

## Where V1 and V2 disagree

| what | V1 | V2 | follow | why |
|---|---|---|---|---|
| tag aspect ratio (paper height / paper width) | 2.2380 | 2.3178 | **V1** | V1's 2.2380 matches the shipped 70 x 156 mm card (2.2286) to 0.4 %. V2 is 3.6 % taller, a non-uniform rescale the user's crop introduced: V1's tag is 616.1 x 1379.1 source px, V2's is 274.4 x 636.0, so V2 was scaled 0.4453 in x but 0.4612 in y. Read V2 for WHICH glyph sits where; read V1 for how far down it sits, and divide any V2 v-fraction by 1.0356 before using it as a position. |
| source sampling over the tag | 8.802 px/mm | 3.920 px/mm | **V1** | V2 resolves nothing finer than 0.51 mm. Its fibre spectrum, kasure hole sizes and edge-roughness wavelengths all sit at or past its own Nyquist limit, so they measure the downsample rather than the artwork. |
| paper base colour, centre of the tag, stored sRGB | #F6E6C5 (246,230,197) H 40.35 S 0.198 V 0.963 | #F6E5C3 (246,229,195) H 40.01 S 0.208 V 0.965 | **either** | They agree to 2/255 on every channel and to 0.35 degrees of hue. The paper colour is settled and needs no adjudication. |
| black ink core colour, stored sRGB | #0F100D (15,16,13), linear luma 0.00509 | #0C0D0A (12,13,10), linear luma 0.00386 | **V1** | V2 is 3/255 darker because its downsample pushed the surviving core pixels toward the stroke centres. Both say the same thing: a near-neutral near-black at about 15/255, not a charcoal. Use V1's, which is measured over 2.2x more pixels per stroke. |
| paper:ink luminance contrast ratio | 153.5 : 1 | 202.7 : 1 | **V1** | Same cause as the row above. V1's 153:1 is the conservative target; even it is 14x what we currently ship. |
| total ink mass fraction of the tag | 0.3035 | 0.3345 | **V1** | V2 reads 10 % heavier because its 2.2x downsample smears every stroke edge outward and the smear counts as partial ink. The extra is blur, not design. Target V1's 0.3035. |
| black area / red area | 1.449 | 1.502 | **either** | The two agree to 3.7 %, so the black-to-red balance is the most robust composition number in the whole reference. Ours is 1.002. |
| enso ring stroke width (polar outer radius minus inner radius) | 6.148 mm | 6.306 mm | **V1** | 2.6 % apart, well inside V2's own 0.51 mm resolution. Either supports a 6.1-6.3 mm brush. Ours is 4.28 mm. |
| enso ring ellipticity (height / width) | 1.1538 | 1.0996 | **V1** | V2's figure is measured in its stretched frame; correcting it by the 1.0356 stretch gives 1.062. So V1 says slightly oval, V2 corrected says nearly round. Take V1's 1.154 as the upper bound and treat anything above 1.20 as wrong. Ours is 1.265. |
| enso ring centre, v fraction of tag height | 0.4950 | 0.4750 | **V1** | V1 puts the ring on the tag's vertical midline. V2's 0.475 is its crop and stretch, not a design difference. |
| ring red saturation | 0.8924 | 0.9421 | **V1** | The user's edit lifted saturation ~5 points. V1 is the conservative figure and still 0.28 above what we ship, so the disagreement does not change any decision. |
| are the border red, ring red and seal red the same red? | hue spread 1.14 deg, saturation spread 0.021, VALUE spread 0.139 | hue spread 0.42 deg, saturation spread 0.028, VALUE spread 0.089 | **V1** | Both say the same pigment at different weights: hue and saturation are locked, value is not. V1 shows the spread more strongly because it resolves the heavy border line. Follow V1 and vary the WEIGHT, not the hue. |
| ink mass of the four side/lower columns (the text blocks) | upper-left 0.01210, upper-right 0.01191, lower-right 0.00947, lower-centre 0.00924 | upper-left 0.02076, upper-right 0.02195, lower-right 0.01516, lower-centre 0.01722 | **V2, divided by 1.102** | THE most consequential disagreement in this pass. V1's side columns are pseudo-glyphs - thin, sketchy squiggles - while V2's are the real kanji the asset ships (火遁術, 爆炎陣, 焼尽, 瞬業). Real characters carry far more ink than squiggles, so V1 understates these blocks by 60-85 %, well beyond V2's uniform 10.2 % downsample smear. Take V2's figure and divide by 1.102 (the V2/V1 total-ink ratio) to strip the smear: targets are 0.0188, 0.0199, 0.0138 and 0.0156. Everything else on this page still follows V1. |
| ink mass of the red border zone (outer 8.4 mm) | 0.00925 | 0.01745 | **V1** | Unlike the columns this is the same artwork in both, so the 89 % gap is measurement, not design: the border is a thin line, and a thin line is exactly what a 2.2x downsample fattens most. V2's smear bias is far above its 10 % average here. Use V1. |
| paper fibre dominant cell size | 0.499 mm | 2.355 mm | **V1** | V2's figure is its resolution floor, not a measurement: 2.355 mm is barely above its 0.51 mm Nyquist scale once windowing is accounted for. V1's 0.50 mm (4.4 source px) is the real grain. |
| paper fibre anisotropy | 1.902 | 5.787 | **V1** | V2's is resampling streak. V1 says the grain is close to isotropic with a mild preference near 85 deg. |
| edge darkening depth at the rim | 15.70 % | 14.31 % | **either** | 1.4 points apart. The rim burn is settled at about 15 % of paper luminance. |
| edge darkening half-recovery distance | 4.75 mm | 3.75 mm | **V1** | V2's profile is quantised by its 0.255 mm pixel, which biases the crossing inward. V1's 4.75 mm, reaching 95 % of plateau by 7.25 mm, is the better number. |
| any fold, crease or internal shadow on the paper | none detected | none detected | **either** | Both references are flat, evenly lit sheets. The band-pass crease detector found no line spanning the tag in either. There is no fold shading to match, and our basecolour currently bakes two. |

## Our build, worst first

| # | element | metric | reference | ours | delta |
|---|---|---|---|---|---|
| 1 | black ink | paper:ink luminance contrast ratio | 153.5 :1 | 11.2 :1 | **-92.7%** |
| 2 | black ink | black core colour, stored sRGB 8-bit | #0F100D (15,16,13) | #41403E (65,64,62) | **+50/255 lighter** |
| 3 | black ink | darkest value the black actually reaches | min 0/255, p0.1 6/255, p1 6/255 | min 62/255, p0.1 62/255, p1 62/255 | **no dark tail: our p0.1 equals our minimum** |
| 4 | reds | border red saturation | 0.9115 | 0.6196 | **-32.0%** |
| 5 | reds | ring red saturation | 0.8924 | 0.6092 | **-31.7%** |
| 6 | reds | seal block red saturation | 0.9138 | 0.6354 | **-30.5%** |
| 7 | reds | small seal red saturation | 0.9016 | 0.6244 | **-30.7%** |
| 8 | whole tag | black ink mass fraction | 0.1742 of tag | 0.1061 of tag | **-39.1%** |
| 9 | whole tag | total ink mass fraction | 0.3035 of tag | 0.2221 of tag | **-26.8%** |
| 10 | whole tag | black area / red area | 1.449 | 1.002 | **-30.8%** |
| 11 | centre glyph | centre glyph ink mass | 0.10521 of tag | 0.05643 of tag | **-46.4%** |
| 12 | centre glyph | centre glyph bounding width | 59.7 mm | 47.7 mm | **-20.1%** |
| 13 | centre glyph | centre glyph bounding height | 54.2 mm | 45.4 mm | **-16.2%** |
| 14 | text columns | upper-left column 火遁術 - ink mass | 0.01884 of tag | 0.00607 of tag | **-67.8%** |
| 15 | text columns | upper-right column 爆炎陣 - ink mass | 0.01992 of tag | 0.00668 of tag | **-66.5%** |
| 16 | text columns | lower-right 焼尽 - ink mass | 0.01375 of tag | 0.00697 of tag | **-49.3%** |
| 17 | text columns | lower-centre 瞬業 - ink mass | 0.01562 of tag | 0.00870 of tag | **-44.3%** |
| 18 | flame emblem | flame emblem - ink mass | 0.01581 of tag | 0.02285 of tag | **+44.5%** |
| 19 | black ink | loaded-to-dry gradient down a column | -0.001 to +0.001 (flat, alpha 0.99 throughout) | -0.035 to -0.067 (fades toward the bottom) | **we ramp where the reference does not** |
| 20 | enso ring | ring stroke width | 6.15 mm | 4.28 mm | **-30.5%** |
| 21 | enso ring | ring kasure hole area fraction | 0.2103 of stroke | 0.0902 of stroke | **-57.1%** |
| 22 | enso ring | ring kasure hole count | 170 | 60 | **-64.7%** |
| 23 | centre glyph | kasure hole count in the centre glyph | 182 | 71 | **-61.0%** |
| 24 | enso ring | ring ink mass | 0.05871 of tag | 0.04280 of tag | **-27.1%** |
| 25 | enso ring | ring outer edge roughness RMS | 0.942 mm | 0.498 mm | **-47.2%** |
| 26 | enso ring | ring edge raggedness wavelength | 4.42 mm | 7.25 mm | **+64.3%** |
| 27 | reds | weight spread of the same red across elements | 0.2152 alpha_R | 0.1047 alpha_R | **-51.3%** |
| 28 | reds | border red opacity (alpha on the red channel) | 0.5903 | 0.2291 | **-61.2%** |
| 29 | paper | paper base colour, centre of the tag, stored sRGB | #F6E6C5 (246,230,197), linear luma 0.799 | #DAC9A8 (218,201,168), linear luma 0.597 | **-25.3% linear luma, -28/255 on R** |
| 30 | paper | paper plateau linear luma | 0.7817 | 0.5757 | **-26.3%** |
| 31 | paper | edge darkening depth at the rim | 15.7 % | 21.9 % | **+39.5%** |
| 32 | paper | edge darkening unevenness across the four sides | 0.0154 of plateau | 0.1240 of plateau | **+707.6%** |
| 33 | paper | whole-sheet lighting tilt, top to bottom | -0.79 % of plateau luma | +5.31 % of plateau luma | **-771.8%** |
| 34 | paper | corner chamfer, mean run along an edge | 8.09 mm | 7.58 mm | **-6.3%** |
| 35 | paper | mottle power in the 1-3 mm band | 0.2879 of mottle power | 0.1363 of mottle power | **-52.7%** |
| 36 | paper | area of stains darker than 6 % | 0.00354 of tag | 0.01298 of tag | **+266.7%** |
| 37 | paper | paper fibre grain amplitude | 17.02 % of paper luma | 9.80 % of paper luma | **-42.4%** |
| 38 | paper | paper fibre anisotropy | 1.90 max/min angular power | 17.25 max/min angular power | **+806.9%** |
| 39 | paper | fold or crease shading baked into the basecolour | none | 2 lines, at v 0.331 (51.6 mm) and v 0.669 (104.4 mm) | **we bake creases the reference does not have** |
| 40 | black ink | modulation depth within one stroke | 0.838 swing / own median | 0.220 swing / own median | **-73.7%** |
| 41 | ink edges | soft halo beyond raster anti-aliasing | 0.1118 mm | 0.1722 mm | **+54.0%** |
| 42 | enso ring | ring ellipticity, height / width | 1.154 | 1.265 | **+9.6%** |
| 43 | enso ring | ring centre position | (35.47, 77.22) mm | (36.87, 78.78) mm | **+1.40 mm x, +1.56 mm y** |

### Why each one matters

1. **black ink - paper:ink luminance contrast ratio** (153.5 :1 -> 11.2 :1, -92.7%). THE headline, and it is lighting-independent so the 'it is only an albedo map' objection does not apply. The reference's black sits at 1/153 of its paper's luminance. Our basecolour reaches 1/11 and our shipped render only 1/16. Our ink is a charcoal grey on a tan sheet, not black ink on cream paper. Nothing else on this list changes the read as much, and no amount of extra coverage compensates.
2. **black ink - black core colour, stored sRGB 8-bit** (#0F100D (15,16,13) -> #41403E (65,64,62), +50/255 lighter). The same fact in the units an artist edits in. The reference black is #0F100D; ours is #41403E. Hue neutrality is fine on both (R-B is 2/255 in the reference, 3/255 in ours) - it is purely a value error, 50 steps of it.
3. **black ink - darkest value the black actually reaches** (min 0/255, p0.1 6/255, p1 6/255 -> min 62/255, p0.1 62/255, p1 62/255, no dark tail: our p0.1 equals our minimum). The reference's ink has a tail: minimum 0/255, 0.1th percentile 6/255, so the densest passages go truly black. Ours is clamped - minimum, 0.1th percentile and 1st percentile are all exactly 62/255. There is no dark tail at all, which is why the strokes look printed rather than inked.
4. **reds - border red saturation** (0.9115 -> 0.6196, -32.0%). All four of our reds are desaturated by about a third, uniformly. The reference red is a near-pure vermilion whose blue channel sits at 21/255; ours sits at 72/255, and that blue is what makes it read brick-pink instead of cinnabar. The hue angle is not the problem - ours is 5.4 deg against the reference's 4.5 deg, which is fine.
5. **reds - ring red saturation** (0.8924 -> 0.6092, -31.7%). All four of our reds are desaturated by about a third, uniformly. The reference red is a near-pure vermilion whose blue channel sits at 21/255; ours sits at 72/255, and that blue is what makes it read brick-pink instead of cinnabar. The hue angle is not the problem - ours is 5.4 deg against the reference's 4.5 deg, which is fine.
6. **reds - seal block red saturation** (0.9138 -> 0.6354, -30.5%). All four of our reds are desaturated by about a third, uniformly. The reference red is a near-pure vermilion whose blue channel sits at 21/255; ours sits at 72/255, and that blue is what makes it read brick-pink instead of cinnabar. The hue angle is not the problem - ours is 5.4 deg against the reference's 4.5 deg, which is fine.
7. **reds - small seal red saturation** (0.9016 -> 0.6244, -30.7%). All four of our reds are desaturated by about a third, uniformly. The reference red is a near-pure vermilion whose blue channel sits at 21/255; ours sits at 72/255, and that blue is what makes it read brick-pink instead of cinnabar. The hue angle is not the problem - ours is 5.4 deg against the reference's 4.5 deg, which is fine.
8. **whole tag - black ink mass fraction** (0.1742 of tag -> 0.1061 of tag, -39.1%). The coverage shortfall is almost entirely black. Red is 17 % short, black is 39 % short. Adding red will make the tag worse, not better.
9. **whole tag - total ink mass fraction** (0.3035 of tag -> 0.2221 of tag, -26.8%). Confirms and sharpens the earlier review: not 'about a fifth', 26.8 % less ink mass than V1 and 33.6 % less than V2. Measured as the mean of ink opacity over the paper, so kasure holes and soft halos are counted at their real weight.
10. **whole tag - black area / red area** (1.449 -> 1.002, -30.8%). The reference is 1.45 parts black to 1 part red and V1 and V2 agree on that to 3.7 %. We are at 1.00. Our tag is half again too red for its black, which is the composition error behind 'reads airier'.
11. **centre glyph - centre glyph ink mass** (0.10521 of tag -> 0.05643 of tag, -46.4%). The 爆 carries 46 % less ink than the reference's. It is smaller AND lighter, so the two errors compound.
12. **centre glyph - centre glyph bounding width** (59.7 mm -> 47.7 mm, -20.1%). The reference glyph runs 59.7 mm across a 70 mm sheet - it very nearly touches the columns. Ours is inset about 6 mm on each side.
13. **centre glyph - centre glyph bounding height** (54.2 mm -> 45.4 mm, -16.2%). With the width, our glyph's bounding area is 33 % smaller than the reference's.
14. **text columns - upper-left column 火遁術 - ink mass** (0.01884 of tag -> 0.00607 of tag, -67.8%). Measured against V2 de-smeared, NOT against V1: V1's side columns are pseudo-glyphs and carry far less ink than the real kanji we ship, so using V1 here would let us off. On the honest target the text blocks are the second-worst shortfall after the centre glyph - collectively we lay about 40 % of the ink these four blocks should carry. Thin strokes, too much air between them, and the same pale ink as everywhere else.
15. **text columns - upper-right column 爆炎陣 - ink mass** (0.01992 of tag -> 0.00668 of tag, -66.5%). Measured against V2 de-smeared, NOT against V1: V1's side columns are pseudo-glyphs and carry far less ink than the real kanji we ship, so using V1 here would let us off. On the honest target the text blocks are the second-worst shortfall after the centre glyph - collectively we lay about 40 % of the ink these four blocks should carry. Thin strokes, too much air between them, and the same pale ink as everywhere else.
16. **text columns - lower-right 焼尽 - ink mass** (0.01375 of tag -> 0.00697 of tag, -49.3%). Measured against V2 de-smeared, NOT against V1: V1's side columns are pseudo-glyphs and carry far less ink than the real kanji we ship, so using V1 here would let us off. On the honest target the text blocks are the second-worst shortfall after the centre glyph - collectively we lay about 40 % of the ink these four blocks should carry. Thin strokes, too much air between them, and the same pale ink as everywhere else.
17. **text columns - lower-centre 瞬業 - ink mass** (0.01562 of tag -> 0.00870 of tag, -44.3%). Measured against V2 de-smeared, NOT against V1: V1's side columns are pseudo-glyphs and carry far less ink than the real kanji we ship, so using V1 here would let us off. On the honest target the text blocks are the second-worst shortfall after the centre glyph - collectively we lay about 40 % of the ink these four blocks should carry. Thin strokes, too much air between them, and the same pale ink as everywhere else.
18. **flame emblem - flame emblem - ink mass** (0.01581 of tag -> 0.02285 of tag, +44.5%). The one element we OVER-ink, and both references agree on the target (V1 0.01581, V2 0.01653, so this is not a pseudo-glyph artefact). Our emblem is 45 % heavier than it should be, which makes it compete with the centre glyph instead of sitting above it. Shrinking it is part of giving the 爆 its 59.7 mm back.
19. **black ink - loaded-to-dry gradient down a column** (-0.001 to +0.001 (flat, alpha 0.99 throughout) -> -0.035 to -0.067 (fades toward the bottom), we ramp where the reference does not). This one inverts the expected answer, so it is worth stating plainly. The reference has NO density ramp: its black is opaque at alpha 0.99 at the top of every column and 0.99 at the bottom, and all of its dry-brush character comes from holes punched clean through an otherwise solid fill. We do the opposite - a semi-transparent wash that additionally fades 3.5 to 6.7 alpha points down each column. Fixing this means making the fill opaque and taking the dryness out in holes, not ramping density.
20. **enso ring - ring stroke width** (6.15 mm -> 4.28 mm, -30.5%). The 'leaner ring' quantified from the polar radii: a 6.15 mm brush against our 4.28 mm. V2 independently says 6.31 mm.
21. **enso ring - ring kasure hole area fraction** (0.2103 of stroke -> 0.0902 of stroke, -57.1%). The reference's ring is dense ink with 21 % of its area punched out by dry-brush holes. Ours is 9 %, so ours reads as a thin even wash rather than a loaded brush running dry. Note our holes are already the right size (0.31 mm against 0.30 mm median), the right shape (elongation 4.8 against 4.2) and correctly aligned with the stroke (88 % within 30 deg of the tangent against 83 %, where random would be 33 %). There are simply not enough of them and the ink around them is not dark enough.
22. **enso ring - ring kasure hole count** (170 -> 60, -64.7%). 170 holes against 60 over a comparable stroke area.
23. **centre glyph - kasure hole count in the centre glyph** (182 -> 71, -61.0%). 182 against 71 at a similar total hole area (7.3 % against 6.9 %), so our glyph's breakup is the right amount of missing ink distributed into too few, too large gaps. Break the same area into 2.5x as many holes.
24. **enso ring - ring ink mass** (0.05871 of tag -> 0.04280 of tag, -27.1%). Follows from the thinner stroke and the paler red.
25. **enso ring - ring outer edge roughness RMS** (0.942 mm -> 0.498 mm, -47.2%). Our ring's outer edge is about half as ragged as the reference's.
26. **enso ring - ring edge raggedness wavelength** (4.42 mm -> 7.25 mm, +64.3%). Ours is not only shallower, it is a longer, smoother undulation: the reference wobbles roughly twice as often along the edge (45 cycles per revolution against 26). Shallow plus slow is exactly what reads as 'drawn with a vector tool'.
27. **reds - weight spread of the same red across elements** (0.2152 alpha_R -> 0.1047 alpha_R, -51.3%). The reference uses ONE red pigment at four different laid-on weights: the border is the heaviest at alpha_R 0.59, the small seal the lightest at 0.38, a spread of 0.215. We lay all four at essentially one weight, spread 0.105 and the border is our LIGHTEST red rather than our heaviest. Vary the weight, never the hue.
28. **reds - border red opacity (alpha on the red channel)** (0.5903 -> 0.2291, -61.2%). The reference's border is the darkest red on the sheet, carrying nearly 45 % more pigment than its own ring. Ours is the lightest.
29. **paper - paper base colour, centre of the tag, stored sRGB** (#F6E6C5 (246,230,197), linear luma 0.799 -> #DAC9A8 (218,201,168), linear luma 0.597, -25.3% linear luma, -28/255 on R). Our paper hue is right (40.06 deg against 40.35) and its saturation is close (0.228 against 0.198). The error is value: 218 against 246 on the red channel, 0.597 against 0.799 in linear luma. Our sheet is a kraft tan; the reference's is a pale cream.
30. **paper - paper plateau linear luma** (0.7817 -> 0.5757, -26.3%). The same error stated as the denominator of the contrast ratio. Note that lightening the paper alone would fix only a quarter of the contrast gap; the ink has to come down too.
31. **paper - edge darkening depth at the rim** (15.7 % -> 21.9 %, +39.5%). Ours burns deeper at the rim and recovers far more slowly: 95 % of plateau at 14.75 mm against the reference's 7.25 mm, so our vignette eats a fifth of the card width where the reference's eats a tenth.
32. **paper - edge darkening unevenness across the four sides** (0.0154 of plateau -> 0.1240 of plateau, +707.6%). The reference's four edges agree to 1.5 points of plateau luminance - the ageing is even all the way round. Ours disagree by 12.4 points, with the right edge markedly darker than the left. Nothing in either reference does that, and it is the kind of asymmetry that reads as a bug rather than as wear.
33. **paper - whole-sheet lighting tilt, top to bottom** (-0.79 % of plateau luma -> +5.31 % of plateau luma, -771.8%). A plane fitted to the paper luminance tilts by under 0.8 % across either axis in both references - they are evenly lit sheets. Ours tilts +5.3 % down the height and -2.5 % across the width, so our paper is measurably brighter at the bottom. Together with the 12.4-point edge unevenness this is the second half of the same problem: our ageing has a direction, and the reference's does not.
34. **paper - corner chamfer, mean run along an edge** (8.09 mm -> 7.58 mm, -6.3%). Measured from the paper support, not from our spec: the reference cuts about 8.0 mm off each corner (V1 8.09, V2 7.96) and we cut 7.58. Small, but it is a free 0.5 mm and it changes the silhouette at thumbnail size.
35. **paper - mottle power in the 1-3 mm band** (0.2879 of mottle power -> 0.1363 of mottle power, -52.7%). Our stain amplitude is fine (RMS 2.48 % against 2.02 %) but its scale is wrong: 86 % of our mottle power sits in the 3-10 mm band against the reference's 71 %, and we have only half its 1-3 mm content. Our correlation length is 1.05 mm against 0.79 mm. The result is a soft gradient where the reference has foxing.
36. **paper - area of stains darker than 6 %** (0.00354 of tag -> 0.01298 of tag, +266.7%). We have 3.7x the deep-stain area, and 15 patches darker than 10 % where V1 has none at all. We are over-staining the paper while under-inking the art, which is the worst of both.
37. **paper - paper fibre grain amplitude** (17.02 % of paper luma -> 9.80 % of paper luma, -42.4%). Our paper grain is a little over half the reference's depth, so the sheet reads smooth and printed rather than laid. Measured at native resolution on clean paper patches, so it is not a rectification artefact.
38. **paper - paper fibre anisotropy** (1.90 max/min angular power -> 17.25 max/min angular power, +806.9%). The reference's grain is nearly isotropic. Ours has a strong directional streak with its power lobe centred near 125 deg. CAVEAT: only two clean native patches were available on our busy card, so treat the exact angle as indicative; the presence of a strong streak is solid, since the reference measures 1.9 on the same estimator with three patches.
39. **paper - fold or crease shading baked into the basecolour** (none -> 2 lines, at v 0.331 (51.6 mm) and v 0.669 (104.4 mm), we bake creases the reference does not have). Neither reference has any fold, crease or internal shadow - both are flat, evenly lit sheets, and the band-pass detector finds no spanning line in either. Our basecolour carries two horizontal crease lines at 51.6 mm and 104.4 mm covering 46 % and 51 % of the tag width. The mesh already has real creases, so this is shading counted twice, and it is shading the reference does not have at all.
40. **black ink - modulation depth within one stroke** (0.838 swing / own median -> 0.220 swing / own median, -73.7%). In absolute 8-bit terms our strokes look as varied as the reference's (14.3/255 against 13.4/255) but that flatters a light ink. Against each stroke's own median value, the reference modulates by 0.84 and we modulate by 0.22. Their ink varies from deep to very deep; ours barely varies at all.
41. **ink edges - soft halo beyond raster anti-aliasing** (0.1118 mm -> 0.1722 mm, +54.0%). The one place we are HEAVIER than the reference. Both rasters must show about one native pixel of anti-aliasing at any stroke edge; the excess over that is real bleed, and ours is 0.172 mm against 0.112 mm. Softer edges on lighter ink is what makes the tag read printed-and-blurred rather than brushed.
42. **enso ring - ring ellipticity, height / width** (1.154 -> 1.265, +9.6%). Ours is a taller oval than either reference. V1 says 1.154 and V2 corrected for its own stretch says 1.062, so the reference ring is close to round.
43. **enso ring - ring centre position** ((35.47, 77.22) mm -> (36.87, 78.78) mm, +1.40 mm x, +1.56 mm y). Small but worth closing: the reference centres the ring on the vertical midline at 77.2 mm down and 35.5 mm across. Ours sits 1.4 mm to the right and 1.6 mm low.

## What is uncertain

- Paper fibre anisotropy for our build (17.2) rests on only two clean native patches, because our card leaves few large ink-free squares. The angle near 125 deg is indicative; the existence of a strong streak is solid.
- V2's fibre spectrum, kasure hole sizes and edge-roughness wavelengths are at or past its 1.96 cycles/mm Nyquist limit and should not be used at all. Its value as a reference is the identity and placement of the text.
- The reference images are finished illustrations with their own rendering; our basecolour is an albedo map. Absolute values are therefore not strictly comparable, which is exactly why the paper:ink contrast RATIO is quoted, and why the shipped render was measured as well. Both say the same thing.
- The 'ink bleed' halo of 0.11 mm in V1 is close to one source pixel (0.114 mm). It is real but small; the safest reading is that the reference has almost no bleed and our 0.172 mm is softer than it should be.
- Our black core statistics come from the basecolour's clamped floor at 62/255. If that floor is a deliberate PBR albedo decision it should be stated, but the render still only reaches a 15.9:1 contrast against the reference's 153:1, so the decision does not currently survive contact with the reference.
- Element windows for the side columns and seals are fixed fractional boxes; the ring and the centre glyph are fitted from the image. Per-element coverage for the column and seal windows is therefore accurate to the window, not to the glyph outline.

## Provenance

Blender 5.2 headless, factory startup, numpy only. PNGs decoded from their IDAT
chunks by `pngread.py` so stored 8-bit values are exact and no colour management is
involved. Scripts: `pngread.py`, `metro.py`, `tagmeas.py`, `stage1_rectify.py`, `stage2_measure.py`, `stage2b_render_colour.py`, `stage3_assemble.py`.
