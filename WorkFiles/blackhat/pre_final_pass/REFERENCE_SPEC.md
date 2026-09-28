# BLACK HAT (SM_BlackHat): REFERENCE SPECIFICATION

> **The rule:** the shipped hat must look like `blackhat_guide.png`. That means the same cone, the same ribs and
> lashings in the same places, the same band and knot, the same two torn tails, and the same blackened, worn straw.
> **Nothing may be added that the reference does not show.** Measure renders of the shipped asset with the same
> instruments this document used. If the render looks different, it fails, even when every number passes.

Machine twin: `WorkFiles/blackhat/reference_metrology/reference_spec.json`. It holds every row below, each with a
value, a tolerance, a status and a method.
Labelled layout diagram: `WorkFiles/blackhat/reference_metrology/debug/DEBUG_NEVER_SHIP_bh_layout_LABELLED.png`
(**DEBUG, NEVER SHIP**). Legend: red = primary ribs, yellow rings = rib lashings, orange rings = bay lashings,
cyan = band ring, magenta = knot, green = tail rim crossings and tips, violet = cap edge, white boxes = main wear zones.

---

## 0. Authority, instrument, conventions

| | |
|---|---|
| **Reference of record** | `References/BlackHat/blackhat_guide.png`, 670 × 599 RGBA with alpha 1 everywhere, sha256 `8244fd61…7ec356`. It is byte-identical to `Downloads/blackhat.png`. Its provenance is unknown (see `provenance.json`). It may be a render or an AI image, so spacings are recorded **as seen, irregularities included**. |
| **Status labels** | **MEASURED** means read off the pixels. **INFERRED** means a geometric consequence of measured rows. **DESIGNED** means a proposal for what the photo cannot show. |
| **Instrument** | Blender 5.2 headless Python with NumPy 2. The scripts are `WorkFiles/blackhat/reference_metrology/bh_m00 … bh_m26`, the stage outputs are `bh_s*.json`, and the camera model is in `bh_cam.py`. |
| **Units** | **R** is the outer radius of the rim (the outside of the rolled rim tube), and **D = 2R**. The photo has no scale. The DESIGNED default is **D = 600 mm (R = 300 mm)**, and every length here is given in R. |
| **Hat coordinates** | The hat axis is +Z. z = 0 is the rim outline plane (bottom of the rim tube, ±0.02 R). The apex is at z = H. The cone surface is z = H(1 − ρ), where **ρ** = horizontal radius / R. **θ** is the azimuth about the axis: 0 is the rim point nearest the reference camera, and + runs toward image right. |
| **Image frame** | x points right and y points down, in px. |
| **Build input policy** | This spec is numbers and words. The build must never read, sample, project or trace the reference pixels or any debug image. |

---

## 1. CAMERA (reproduce the view)

**Verdict: this is a close perspective 3/4 shot from about 17° above the rim plane, with a normal lens (≈ 43 mm on
full frame) at 2.6 R from the rim centre. It is not orthographic.** The proof is the crown cap. Its edge circle reads almost
edge-on (aspect ≈ 0.06), while the rim reads at ≈ 0.3. Only a camera close enough to sit a few degrees above the
crown produces that. The band ring (aspect ≈ 0.14) falls between them, as perspective requires. An orthographic fit
misses the cap arc (rms 1.66 px against 0.61 px) and puts ribs visibly off (`dbg_camera_model_overlay_dinf.png` vs `…_d2.6.png`).

| Row | Value | Tolerance | How |
|---|---|---|---|
| Projection | **Perspective** | must be perspective | Joint fit of the silhouette lines, the rim bottom and the crown-cap arc over a distance ladder (`bh_m07`). The cap arc rms is 0.87 / 0.67 / **0.61** / 0.65 / 0.84 / 1.66 px at d = 1.8 / 2.2 / **2.6** / 3.0 / 4 / ∞ R. |
| Distance, camera to rim centre | **2.6 R** (780 mm at D = 600) | 2.2 – 3.0 R | Cap minimum. The band ring reads level (horizontal) at d ≈ 2.5. |
| Elevation of the line of sight to the rim centre | **17.03°** | ±0.5° | Same fit (16.5° at 2.2 R, 17.4° at 3.0 R) |
| Focal length | **42.8 mm** on a 36 mm sensor, 670 px wide (f = 796.7 px, HFOV 45.6°) | 35.1 – 50.3 mm, tied to the distance | f_px · 36 / 670 |
| Aim | Aim at the rim centre, which lands at image **(332.97, 291.94) px**. In Blender: render **670 × 599**, sensor fit Horizontal 36 mm, **shift_x −0.0030, shift_y +0.0113** | ±2 px; shift ±0.005 | Fit |
| Roll | Image content is rotated **0.51° clockwise**: the right rim tip is 5.5 px lower than the left (y 333.5 vs 328) | ±0.15° | Generator lines sit 25.47° (left) and 26.53° (right) below horizontal |
| Camera position (camera frame) | (0, −2.486, 0.761) R, looking at (0, 0, 0) | scales with distance | INFERRED |
| **Hat orientation in the view** | The knot sits at **θ = +61°**, to the camera's right, on the band's lower edge. The hat axis is upright in the frame (bisector tilt 0.5°, the same roll). | θ ±5° | MEASURED |
| World orientation (DESIGNED) | Hat +Z up and +X forward (the HEAD socket frame). The knot is on the wearer's **left (+Y)**. The reference camera then sits at azimuth **ψ = +29°** from +X toward +Y, at **(2.174, 1.205, 0.761) R** | ψ ±5° | ψ = 90° − 61°. The user can move the knot, and ψ follows. |
| Silhouette lines | left y = 299.06 − 0.47641 x; right y = −26.848 + 0.49928 x; virtual apex (334.03, 139.93) px | 1 px | `bh_m02`, rms 0.69 / 0.73 px |
| Frame | hat x 1 … 664; crown top y 142.5; rim bottom y 433.5 at x ≈ 340; lowest tail tip y 533 | ±2 px | `bh_m01` |

## 2. LIGHTING

| Row | Value | Tolerance |
|---|---|---|
| **Backdrop** | Pure white cut-out, 0.992 – 0.997 stored everywhere. **No cast shadow and no contact shadow on the backdrop.** | must stay absent |
| Softness | Large, soft sources. No hard shadow edge exists anywhere. The only darkness is in crevices: the rim groove (0.011 – 0.06 stored) and a black 1.5 – 2 px line under the cap lip. The tails shade the cone softly below the knot. | qualitative |
| **Brightness vs azimuth** (straw, linear lum p50, ρ 0.55 – 0.93) | front θ 0…16: **0.017**; θ −28…−24: **0.054**; θ −52…−44: **0.074** (worn + sheen); θ −76…−64: **0.035**; θ 72…76: **0.041** | ±20 % each after matching exposure on the front bay |
| Pattern | The camera-facing bays are the **darkest**. Both sides are 2 – 4× brighter, and the left is about 1.3× brighter than the right. No single Lambert light explains it (R² 0.11; two lights 0.23). The pattern is grazing sheen on the straw plus lights behind both sides. | INFERRED |
| Rim tube (lin p50) | front 0.012; θ −50 0.049; θ +55…60 0.030 | ±25 % |
| Specular | Straw: soft sheen, with streaky glints along the strands on the lit left bays (p90 0.16 lin). Cloth: matte (p90/p50 ≈ 1.4). | INFERRED |
| Proposed rig (DESIGNED) | Soft key area light upper-left-behind (θ −110°, elev 35°). Soft kicker right-behind (θ +115°, elev 25°, 0.6× key). Weak front fill 0.2×. Straw roughness ≈ 0.5 with sheen. | tune to the rows above |

## 3. CONE AND CROWN CAP

| Row | Value | Tolerance | Status |
|---|---|---|---|
| **Height / radius H/R** | **0.488** (virtual apex above the rim outline plane) | ±0.015 | MEASURED |
| Rim diameter / height D/H | **4.10** | ±0.13 | INFERRED |
| Slope from horizontal | **26.0°** (apex full angle 128.0°) | ±0.8° (±1.6°) | INFERRED |
| Profile | Straight generators (rms 0.7 px about straight lines, quadratic term negligible). **No sag or flare near the rim.** | ≤ 0.005 R from straight | MEASURED |
| **Crown cap radius** | **0.1055 R** | ±0.008 R | MEASURED |
| Cap profile | A low conical lid, slope ≈ 20° (flatter than the cone). Its top sits 0.005 R below the virtual apex. The lip thickness / overhang of ≈ 0.008 R casts the black line. Faint radial ribs on the lid meet at a point, with **no finial**. | slope ±5°; lip 0.004 – 0.012 R | INFERRED |

## 4. RIBS

**Verdict: 13 primary ribs (round twisted rods lying on the skin), irregularly spaced on the visible arc.** Build
the visible ribs at their measured azimuths, and do not tidy them.

| Row | Value | Tolerance | How / status |
|---|---|---|---|
| **Count** | **13** | exactly | 7 visible ribs span 167°, at a mean pitch of 27.84° (N = 12.93). Forced even pitch: N = 13 gives rms 2.16°, N = 12 gives 4.82°. N = 12 becomes the better even-pitch fit only for d ≥ 2.9 R, and matches its 30° pitch exactly at d = 3.5 R, where the cap residual is 21 % worse (`bh_m24`). INFERRED |
| **Visible azimuths** (where rib meets rim) | **−82.0, −54.5, −23.5, +7.6, +30.0, +58.0, +85.0°** | ±2° (±4° at −82 / +85) | Unrolled cone (`bh_m16`, `dbg_cone_unrolled_theta_rho_d2.6.png`) |
| Visible gaps | 27.5, 31.0, 31.1, **22.4**, 28.0, 27.0° | ±2° | as seen |
| Far side (DESIGNED) | 112.7, 140.3, 167.9, 195.4, 223.0, 250.6° (6 ribs evenly filling +85 → +278°, pitch 27.6°) | ±3° | DESIGNED |
| Diameter | **0.011 R** (3.3 mm at D = 600) | ±0.003 R | Dark flank to dark flank is 0.9° at ρ 0.78, with a bright core of 0.5° |
| Relief | A round rod lying **on** the skin, with a dark shadow flank on each side (≈ 0.3° each) | 0.6 – 1.0 × diameter | INFERRED |
| Construction | Twisted cord / split-cane rod. The rope twist is clearly visible on the θ = +7.6° rib (pitch ≈ 1.6 × diameter), and the others read smoother only through lighting. Each rib runs from under the cap lip to under the rim binding cord. | — | MEASURED (visual) |
| Fine radial seams | Thin (1 px) dark radial lines in the weave, irregular 3 – 8° apart. **Texture only, no relief.** | texture | θ spectrum peaks 3.8 – 7.7° |

## 5. WOVEN SKIN

| Row | Value | Tolerance |
|---|---|---|
| **Strand direction** | **Circumferential** flat strands (parallel to the rim). The fine radial seams break them into brick-like runs. | — |
| Strand width | **0.006 R** (≈ 2 px at the front) = **0.003 D** (≈ 1.8 mm at D = 600) | ±0.002 R |
| Course period | 0.031 R along the slant | ±0.008 R |
| **Weave meets rib** | The strands run continuously **under** each rib, with no gap or break. The rib sits on top with a shadow flank on each side. | — |
| Weave at the edges | It disappears under the cap lip at the top and under the binding cord / rim tube at the bottom. | — |

## 6. RIM AND LASHINGS

| Row | Value | Tolerance | How |
|---|---|---|---|
| **Rolled rim tube diameter** | **0.044 R** (13 mm) | ±0.006 R | Front: bottom outline 433.5 px to the dark groove 412 px = 21.5 px at 484.6 px/R |
| Binding cord | 0.005 R, a light cord on the inner-top edge of the tube, above the groove | ±0.002 R | |
| Groove | A dark crevice between cord and tube | must read black | |
| **Lashing count** | **26**: one at every primary-rib end plus one inside every bay | exactly 2 per bay | Seen in all 5 measurable bays. INFERRED for the circle |
| **Visible lashing azimuths** | at ribs **−53.7, −22.1, +7.65, (+30.0 hidden under tail A), +58.35°**; in bays **−67.0, −32.5, −9.0, +17.1, +42.75°** | ±1.5° for \|θ\| < 45, ±4° at the sides | θ-rectified rim face (`bh_m15`) |
| Bay-lashing position | 0.55, 0.68, 0.46, 0.42, 0.45 of the bay after its rib | ±0.08 | as seen |
| Lashing width | **0.038 R** (2.0 – 2.4°) | ±0.005 R | |
| **Wraps** | **3** per lashing | exactly | 3× – 8× crops (`crop_rimzoom.png`) |
| Wrap cord | 0.012 R | ±0.003 R | INFERRED |
| Extent | The wraps cover the tube and the binding cord, and reach ≈ 0.015 R onto the skin edge | ±0.005 R | |

## 7. BAND AND KNOT

| Row | Value | Tolerance | How |
|---|---|---|---|
| **Ring position** | Centre line at **ρ = 0.365**, i.e. z = 0.635 H, 0.29 R (slant) below the cap edge. **Horizontal.** | ρ ±0.015 | Back-projected band line at θ −80…0 (level within ±0.01) |
| Width | **0.010 R** (twisted, cord-like) for θ < −20°; 0.04 R at θ 0; **0.11 R** fanned at θ +30° | ±0.003 / 0.01 / 0.02 R | Unrolled views `dbg_band_unrolled_*.png` |
| Flat cloth width | 0.10 R (30 mm) | ±0.02 R | INFERRED from the fanned band and the tails |
| Wrap | One turn round the cone. It lies on the cone and passes **over** the ribs. Away from the knot it is twisted progressively into a narrow roll. Its lower edge dips to ρ 0.51 just before the knot. | — | |
| **Knot position** | **θ = +61°, ρ = 0.43** (image ≈ (462, 222)) | θ ±5°, ρ ±0.04 | Back-projection (57 – 64° over the distance range) |
| Knot size | 0.08 × 0.09 R (28 × 35 px) | ±0.02 R | |
| Knot shape | A compact gathered knot (square-knot bulk) sitting on the band's lower edge. The band fans into 3 – 4 fold lines entering it. | — | `crop_knot.png` |

## 8. TAILS

| Row | Value | Tolerance | Status |
|---|---|---|---|
| **Count** | **2** | exactly | MEASURED |
| Leave the knot at | θ +64°, ρ 0.51 | θ ±5°, ρ ±0.04 | MEASURED |
| Cross the rim at | **A θ +31°, B θ +40°** | ±4° | MEASURED |
| Order | A (inner, nearer the camera-facing side) lies over B near the knot | — | MEASURED (visual) |
| **Width** | **A 0.062 – 0.075 R, B 0.084 – 0.091 R** | ±0.01 R | Below-rim widths 28 – 34 px and 36 – 39 px |
| **Length, knot to tip** | **A 0.99 R, B 0.96 R ≈ 0.49 D** (≈ 295 mm) | ±0.10 R | INFERRED (on-cone path + straight fall) |
| Hang below the rim | A 0.30 R, B 0.32 R | ±0.04 R | MEASURED |
| Hang direction | 12 – 18° off vertical, outward (image right, away from the cone) | ±5° | INFERRED |
| Tip positions | A (592, 533) px, B (643, 520) px | ±4 px | MEASURED |
| Twist / drape | A is turned 60 – 90° (edge toward the camera, 17 px wide) for ≈ 0.15 R after the knot. It then lies flat on the cone and over the rim. B stays face-on and stands slightly off the cone near the rim (dark air gap). **No other twist.** | — | MEASURED (visual) |
| **Torn ends** | Each end is a long tapering **diagonal tear** that finishes in a point on the **outer (image-right) edge**. A's tear is 0.18 R long. B's is 0.25 R long, with one deep notch splitting off a narrow sliver. Ragged teeth are 0.007 – 0.02 R. The other edge stays straight to the tip. | tear ±0.04 R; teeth ±0.005 R | MEASURED |
| Cloth thickness | 0.004 R (1.2 mm) | 0.003 – 0.005 R | DESIGNED (not resolvable, ≤ 1.5 px) |

## 9. COLOUR, ALBEDO AND WEAR

Albedo = observed linear luminance ÷ estimated irradiance. The sides are lit near full and the front at ≈ 0.4, for a
mean of ≈ 0.8, scaled so that the white backdrop reads 1.0. The absolute level is therefore good only to about ±35 %.
Chromaticity is solid.

| Row | Value | Tolerance | Status |
|---|---|---|---|
| **Straw albedo** | lum **0.042** lin; RGB lin (0.0443, 0.0414, 0.0410) = sRGB **(0.233, 0.225, 0.224) #3B3939** | ±0.015 lum; sRGB ±0.03 | INFERRED |
| Straw chroma | (0.350, 0.327, 0.323); hue ≈ 9°, sat 0.04 (a near-neutral, faintly warm black) | r ±0.008, hue ±8°, sat ±0.02 | MEASURED |
| Rim tube and lashings | warmer: chroma (0.375, 0.324, 0.300), hue 18 – 21°, sat 0.10 – 0.13; albedo sRGB **(0.241, 0.223, 0.213) #3D3936** | ±0.03 | INFERRED |
| **Cloth (band and tails)** | lum **0.030** lin (≈ 0.72 × straw); RGB lin (0.0316, 0.0294, 0.0297) = sRGB **(0.195, 0.188, 0.189) #323030**; neutral, sat 0.04 | ±0.010 lum; sRGB ±0.03 | INFERRED |
| Observed region means | straw centre 0.029; left worn bay 0.059; right bay 0.039; band near the knot 0.010; tail A 0.017; tail B 0.012; cap top 0.039 (linear luminance, lighting included) | — | MEASURED (`bh_s20`) |
| **Wear flecks** | light neutral grey, observed sRGB (0.373, 0.362, 0.358); lin lum p50 0.082, p90 0.20 → albedo ≈ 0.10 (0.08 – 0.20) | ±0.04 | MEASURED / INFERRED |
| **Wear coverage** | **15 %** of the visible straw (pixels > 1.8 × the local p30) | ±4 % | MEASURED (`bh_m21`, `dbg_wear_map_unrolled_orange.png`) |
| Wear zones | **left θ −62…−25, ρ 0.45 – 0.97: 20 %** (the big worn area); streaks θ −18…−5, ρ 0.70 – 0.82: 12 %; front θ −5…16: 7 %; right θ 72…95: 18 % (partly grazing sheen) | ±5 % each | MEASURED |
| Fleck shape | Short streaks **along** the circumferential strands, 0.5 – 3° long and 0.003 – 0.006 R tall. They are lighter strand tops, **not holes**. | — | MEASURED |
| Dark smudge | One broad darker smudge at θ −45…−35, ρ 0.55 – 0.90, ≈ 15 % darker than its surround | ±10 % | MEASURED |
| Rim wear | Light scuffs on the front face of the tube (image x 280 – 330 and 360 – 380); rim p90 / p50 = 2.4 | — | MEASURED |
| **Not present** | No holes, no tears in the straw, no broken ribs, no missing lashings, no chin cord, no lining, no decals, no colour | must stay absent | MEASURED |

Tint-ready defaults for the sidecar (detail × tint = BC): straw (0.0443, 0.0414, 0.0410), cloth (0.0316, 0.0294,
0.0297), rim / lashing (0.0473, 0.0409, 0.0378) linear. All three are INFERRED, ±25 %.

## 10. WHAT THE REFERENCE CANNOT SHOW (DESIGNED, not measured)

| Part | Design |
|---|---|
| **Underside** | The reference never shows it. Use the plain inside of the woven skin (same circumferential strands), 0.006 R thick. Ribs go on the outside only. The rim tube is round all the way under, and the lashings wrap fully around it. **No headband ring, no lining, no chin cord.** |
| Far side (θ +90…+270) | 6 more primary ribs at a 27.6° pitch, with a lashing at every rib plus one per bay (26 in total). The band continues round the back as the narrow twisted roll at ρ 0.365. Wear flecks at ≈ 10 % coverage. No new damage. |
| HEAD socket | An Empty on the axis at the inner crown seat. A 57 cm head (sphere r = 9.07 cm) inscribed in the inner cone (half-angle 64°) has its centre 1.113 r below the inner apex, so the skull top sits **0.113 r = 1.03 cm below the inner apex**. +Z points up out of the crown and +X forward. |
| Real size | D = 600 mm, H = 146 mm, rib 3.3 mm, rim tube 13 mm, lashing cord 3.6 mm, band cloth 30 mm, tails ≈ 295 mm |
| Knot side | The wearer's left (+Y), so the reference camera sits at ψ = +29° (a front 3/4 view). |

## 11. ACCEPTANCE CHECKS (measure the shipped render, never the builder's report)

1. Render the shipped asset with the §1 camera (670 × 599) and run `bh_m01` / `bh_m02` on it. The generator lines must be within 1 px, the tips within 2 px and the rim bottom within 2 px.
2. The crown-cap arc (the `bh_m07` trace) must be within 1 px of the reference trace, with the cap edge ends at x 298 / 370 within 2 px.
3. Unroll with `bh_m16` / `bh_m15` using the **same** camera. The ribs and lashings must sit at the §4 / §6 azimuths, with 3 wraps each.
4. The band ring must be at ρ 0.365 and the knot at θ 61°. The tails must cross the rim at 31° / 40°, with tips within 6 px of (592, 533) / (643, 520).
5. Check the colour and brightness rows with `bh_m20` on the render, after matching exposure on the front bay.
6. **LOOK:** compare side by side with the reference. If it looks different, it fails, even when every number passes.
