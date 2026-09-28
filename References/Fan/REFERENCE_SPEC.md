# JAPANESE FOLDING FAN (SK_Fan): REFERENCE SPECIFICATION

> **The rule:** the shipped fan must have the shape and mechanism of `fan2.png`: the same number of sticks, the same
> opening, the same guards, the same bare lower ribs fanning into the same pleated leaf, the same rivet and lobe, and the
> same tassel. It must look like fan2 with the painting taken off. **Nothing may be added that the photos do not show.**
> Measure renders of the shipped asset with the same instruments this document used. If the render looks different, it
> fails, even when every number passes.
>
> **No surface design in this job.** The willow, water swirls and red seal (fan2), the sakura, cats and seal (fan1),
> and the **pierced openwork in the ribs** of both fans are design for a later stage. Leaf and ribs are plain black,
> and **the ribs are solid**.

Machine twin: `WorkFiles/fan/reference_metrology/reference_spec.json`. It holds every row below, each with a value, a
tolerance, a status and a method.

Labelled layouts (**DEBUG, NEVER SHIP**):
- `WorkFiles/fan/reference_metrology/debug/DEBUG_NEVER_SHIP_fan2_layout_LABELLED.png`
- `WorkFiles/fan/reference_metrology/debug/DEBUG_NEVER_SHIP_fan1_layout_LABELLED.png`

Legend: cyan = outer leaf edge (fan2: from the camera model), yellow = leaf inner edge, red = the stick axes (bright red
= guards), orange = butt lobe, green dots = edge notches, white = rivet, magenta = cord and knot, blue = tassel skirt.

---

## 0. Authority, instrument, conventions

| | |
|---|---|
| **Primary reference** | `References/Fan/fan2.png`, 800 × 800 RGBA with alpha 1 everywhere, sha256 `45432662…9a5e3d`. It is a retail product photo. The backdrop is a uniform stored grey of 0.9647 (246/255) with a soft, composited elliptical shadow under the fan. The shadow is not part of the asset. |
| **Cross-check** | `References/Fan/fan1.png`, 800 × 800, sha256 `08d39a89…c0f23c`, on a pure white 1.0 backdrop with no shadow. Where the two photos disagree, **fan2 wins**. The differences are listed in section 11. |
| **Status labels** | **MEASURED** means read off the pixels. **INFERRED** means a geometric or physical consequence of measured rows. **DESIGNED** means a proposal for what neither photo shows. |
| **Instrument** | Blender 5.2 headless Python with NumPy 2. The scripts are `WorkFiles/fan/reference_metrology/fm_m00 … fm_m26`, the stage outputs are `fm_s*.json`, and the helpers are in `fm_lib.py`. |
| **Unit L** | **L** is the radius from the pivot (the rivet axis) to the leaf's outer edge. It equals pivot-to-guard-tip, because the two are flush. It is 343 px in fan2 (at the rivet's depth) and 396 px in fan1. The photos have no scale. **DESIGNED: L = 190 mm.** The full stick, including the butt, is then 1.106 L = 210 mm (the common 21 cm silk fan), and the open width is 376 mm. |
| **Image angle φ** | φ is the angle about the rivet image, in degrees, with y up: 0 = image right, counter-clockwise positive. |
| **Design mask** | Every statistic excludes design pixels (bright or saturated, dilated 2 px). Design covers **12.0 %** of fan2's leaf and 29.4 % of fan1's. |
| **Tolerance "–"** | A qualitative row: it must read the same in a side-by-side render. A DESIGNED number may move ±25 % unless that breaks a MEASURED row. |
| **Build input policy** | This spec is numbers and words. The build must never read, sample, project or trace the reference pixels or any debug image. |

---

## 1. CAMERA: reproducing fan2's view

**Verdict: this is a normal-lens perspective shot from about 3 L. The fan plane leans back, top away from the camera,
by 11.5°.** The proof is the outer leaf edge. It is a circle about the rivet in the real fan, but in the photo its radius
falls from 342 px at the two ends to 325 px at the top (5 %), while the rib pitch stays uniform (6.72 / 6.66 / 6.78° by
thirds). A plane tilted about its horizontal axis through the rivet does exactly that: rays through the rivet keep their
angles, and the far top shrinks. The tilted model fits the silhouette at rms **1.00 px**, of which 0.82 px is the pleat
scallop. A fan square to the lens misses by rms **4.52 px**. Distance and tilt trade off weakly (rms 0.96 px at 1.8 L,
1.10 px at 5 L, 1.34 px at 20 L), so 3.0 L was chosen, which corresponds to a 46 mm lens.

| Row | Value | Tolerance | Status / how |
|---|---|---|---|
| Projection | Perspective, with the fan plane tilted top-away | must be tilted: an untilted fan misses the arc by 4.5 px rms | MEASURED (`fm_m04`, `fm_m10`, `fm_m23`) |
| Camera distance to rivet | **3.0 L** | 1.8 – 5.0 L | MEASURED (weak minimum) |
| Fan tilt α | **11.5°**, rotated about the horizontal axis through the rivet, **top away from the camera** | 9.2° (at 1.8 L) – 13.2° (at 5 L), tied to the distance | MEASURED |
| Focal length | f = **1032 px** = **46.4 mm** on a 36 mm sensor, 800 px wide (HFOV 42.4°) | f_px = 344 × distance/L | MEASURED |
| Image scale at the rivet depth | 344.0 px per L | ±1.5 | MEASURED |
| Principal point | Image centre, lens shift 0, sensor upright (optical axis level) | assumed | INFERRED |
| Rivet image position | **(398.2, 547.0) px** (the centre of the metal ring) | ±1.5 px | MEASURED |
| Camera position relative to the rivet | (+0.0060, −3.0, +0.4246) L: X right, camera on −Y looking along +Y, Z up. The rivet sits 0.4246 L below the optical axis. | scales with the distance | INFERRED |
| Roll | The fan is turned **+1.0°** (counter-clockwise as seen). Its bisector lies at φ = 91.0°. | ±1.5° | MEASURED |
| Extents | Leaf corners at x = 58 and 736. Leaf top y = 221. Lobe bottom y = 584. Tassel tip (199, 630). | ±2 px | MEASURED |

**Blender recipe (fan2 view).** Render at 800 × 800 with sensor fit Horizontal, a 36 mm sensor, a 46.4 mm focal length
and shift 0 / 0. Put the rivet at the origin, with the fan plane first in XZ (+Z = bisector, front face toward −Y). Rotate
the fan +1.0° about Y (counter-clockwise as seen from −Y), then 11.5° about X so that the top moves to +Y. Place the camera
at (0.0060, −3.0, 0.4246) × L, level, looking along +Y. The rivet then lands at (398.2, 547.0).

**fan1 view:** front-on. A circle about the rivet fits its outer edge at rms 2.13 px, 1.31 px of which is the scallop. A
free-centre circle lands only 2.2 px from the rivet (rms 1.65 px), so the tilt is ≤ 4°. Rivet at (391.6, 600.3) px, L = 396 px, roll −1.7° (bisector at 88.3°).

## 2. OPENING ANGLE

| Row | Value | Tolerance | Status / how |
|---|---|---|---|
| **fan2, guard axis to guard axis** | **163.2°**: the front guard axis is at φ 9.4° and the rear guard axis at φ 172.6° | ±2° | MEASURED. The outer edge line lies at 8.88°, plus half the guard width. The rear edge is 173.95° at 0.93 L, less half the width. The tilt correction is under 0.4°. |
| fan2, leaf corner to corner | 165.5° (8.25° → 173.8° at 0.99 L) | ±1° | MEASURED |
| fan1, guard axis to guard axis | 142.9° (16.85° → 159.8°) | ±2° | MEASURED. fan1 is opened about 20° less. **Follow fan2.** |

## 3. STICK COUNT

| Row | Value | Tolerance | Status / how |
|---|---|---|---|
| **fan2 total sticks** | **26 = 2 guards + 24 inner ribs** (25 gaps) | exact. Confidence is high (≈ 90 %), and otherwise the count is 25 or 27. | MEASURED four independent ways. (1) There are 25 bare-zone rib boundaries at φ = 11.49 + 6.658 n, and the n = 25 prediction (177.9°) meets the rear guard's outer silhouette (177.3° at r = 140 px). (2) There are 25 lit pleat faces. (3) The edge scallop has one bump per gap: 24 found, plus one at the range end. (4) Pitch × 25 = the opening. The overlay puts 26 axes onto the photo cleanly. |
| fan2 pitch | **6.528°** (163.2 / 25) | ±0.1° | MEASURED. Single methods give: rib boundaries 6.658, lit faces 6.390, scallop 6.511, bare-zone FFT 6.677. |
| fan1 total sticks | **30 = 2 guards + 28 inner ribs** (29 gaps, pitch 4.93°) | exact. Confidence is medium-high, and otherwise the count is 29 or 31. | MEASURED. Boundaries lie at 21.15 + 4.855 n, the scallop period is 4.845 and the leaf period 4.94 over 142.9°. |
| Stacking order | The front guard (image right) is on top. Each stick to its left lies behind the previous one. The leaf lies over all inner ribs and under the front guard, and the rear guard is behind everything. | – | INFERRED from the visible rib edges, from the front guard overlapping the leaf, and from the rear guard being hidden in the leaf zone |

## 4. INNER RIBS (24)

| Row | Value | Tolerance | Status / how |
|---|---|---|---|
| Bare length, pivot to leaf edge | **0.431 L** | ±0.012 L | MEASURED. The leaf inner edge is at 148 ± 4 px. fan1: 0.462 L. |
| Butt below the pivot | **0.106 L** | ±0.005 L | MEASURED. The stacked rounded butts form a lobe of radius 35 – 37.5 px about the rivet (φ 190 – 345°). fan1: 0.08 – 0.09 L. |
| Total rib length | 1.106 L. The part inside the leaf is hidden. | ±0.01 L | INFERRED |
| Width at the leaf inner edge | **0.041 L** | ±0.005 L | MEASURED. The pitch arc there is 16.9 px, less the 2 – 3 px dark boundary line, so the ribs almost touch (fan1: 0.035 L). |
| Width near the pivot | 0.030 L, with straight edges and a linear taper from 0.041 | ±0.006 L | DESIGNED. The ribs overlap there, so it cannot be measured. |
| Shoulder | Rounded shoulders at 0.415 – 0.431 L, just under the leaf edge | ±0.01 L | MEASURED. Rounded rib tops show at r ≈ 146 px, in an un-pierced band 142 – 150 px. |
| Leaf section | Hidden. It continues behind the leaf as a narrow slip to 0.96 L, 0.012 L wide and 0.002 L thick, with a rounded tip. | – | DESIGNED |
| Thickness (bare) | 0.0045 L (0.85 mm). The closed stack at the pivot is 0.128 L (24 mm). | – | DESIGNED |
| Butt | A rounded, semicircular end, 0.030 L wide. The stacked butts make the D-shaped lobe of radius 0.106 L. | ±0.005 L | INFERRED from the lobe, a near-circle about the rivet that falls off only at its ends |
| **Piercing** | **None: the ribs are solid.** fan2's openwork (0.13 – 0.37 L) and fan1's flower cut-outs are design. | – | DESIGNED (job rule) |

## 5. GUARDS (2)

| Row | Value | Tolerance | Status / how |
|---|---|---|---|
| Length | The tip is flush with the leaf edge (1.0 L), plus the 0.106 L butt | ±0.01 L | MEASURED |
| **Visible width** (front guard) | **0.039 L** at 0.17 – 0.29 L, **0.034 L** at 0.47 – 0.58 L, **0.041 L** at 0.76 L, **0.047 L** at 0.93 L. The guard is slightly waisted and widest at the tip. | ±0.006 L | MEASURED from perpendicular profiles between the outer silhouette and the bright inner-edge highlight (`fm_m12`). fan1 is similar: 0.028 → 0.038 → 0.04 – 0.055. |
| Lower grip section | There is no separate grip shape. The guard runs at about the same width down to the rivet, and its outer edge flares about 0.006 L proud of the straight line below 0.45 L. | ±0.003 L | MEASURED |
| Tip | Cut on the leaf arc, square to the axis, with softened corners (fan1's is rounded) | – | MEASURED |
| Long edges | Rounded or chamfered. A continuous highlight runs along the inner edge. | – | MEASURED |
| Thickness | 0.010 L (1.9 mm), about twice an inner rib | – | DESIGNED |
| Rear guard | Identical to the front guard, mirrored. It is hidden behind the leaf in the leaf zone and visible as the leftmost stick in the bare zone. | – | DESIGNED / MEASURED |

## 6. PIVOT AND RIVET

| Row | Value | Tolerance | Status / how |
|---|---|---|---|
| Pivot | At the rib convergence, the rivet centre (398.2, 547.0) px | ±0.015 L | MEASURED. The rib boundary lines converge within 5 px of the ring. |
| **fan2 rivet head** | **Diameter 0.035 L** (12 px): a metal ring with a dark centre 0.017 L across, like a hollow eyelet | ±0.005 L | MEASURED (`debug/g2_rivet_x12.png`) |
| fan1 rivet head | 0.022 L, a solid silver dome | ±0.004 L | MEASURED |
| Metal | Polished silver or nickel, near-neutral and faintly warm (hue ≈ 37°, sat 0.035). Bright-pixel mean lin (0.367, 0.355, 0.335). | – | MEASURED |
| Back of the pin | A matching eyelet head on the back. Each head stands 0.006 L proud of its guard. | – | DESIGNED |

## 7. LEAF

| Row | Value | Tolerance | Status / how |
|---|---|---|---|
| **Inner radius** | **0.431 L**. It is a clean circular arc about the pivot, not scalloped, with no hem band. | ±0.012 L | MEASURED. fan1: 0.462 L. |
| **Outer radius** | **1.000 L**, flush with the guard tips | ±0.01 L | MEASURED |
| **Pleats** | **25 pleats = 50 faces**, one pleat (a lit face and an unlit face) per rib gap. There are 24 rib folds and 25 mid-gap folds, and the two end faces are glued to the guards. | exact, follows the stick count | MEASURED |
| **Alternation** | **Rib folds are valleys seen from the front** (sharp dark creases). **Mid-gap folds are mountains** (soft rounded ridges). | – | INFERRED. Neither photo shows a rib on the front of the leaf, so the ribs lie behind it. The sharp lit → unlit creases coincide with the edge notches within 0.5°. The key light is from the top: face contrast is lowest at φ 65 – 90°. |
| **Alternation: build round 2 correction** | **The ribs carry the MOUNTAINS (soft rounded ridges) and the mid-gap folds are the VALLEYS (sharp dark creases, where the edge notches are).** Leaf lines at stick axis + 1.27° (front guard) falling linearly to −0.30° (rear guard), pitch 6.465° | ±0.55° rms | MEASURED (build round 2, `WorkFiles/fan/FAN_REPORT.md` 1): the round-1 build followed the row above and its pleat shading came out anti-correlated with fan2 in every sector, with its edge notches 3.2° off fan2's. fan2's 24 visible notches sit at 14.35 + 6.49 k deg (image angle); the offsets are a least-squares fit to them with the rear held by the mechanism. The row above is superseded. |
| **Inner edge: build round 3 construction** | **The leaf's VISIBLE inner edge is at 0.437 L** (inside this section's 0.431 L +- 0.012 L, 1.1 mm outward). It is the outer edge of a band of thin rib PRONGS: each stick's rib runs on 5.9 mm past its tip, over the silk's inner margin, shingled like the ribs, and shortens with its gap as the fan closes. The silk itself starts under the band at 0.4060 L; the rib tips (the band's inner step) sit at 0.4054 L, inside the rounded-shoulder row of section 4 (0.415 - 0.431 L +- 0.01 L) | 0.431 L +- 0.012 L (visible edge) | DESIGNED (build round 3, `WorkFiles/fan/FAN_REPORT.md`): with the ribs ending at the leaf's edge, every valley left a notch under the rib tips that showed daylight (the reviews' dotted line). A real leaf is glued over the rib tips. With rigid pleats nothing may sit UNDER a leaf line (the face swings through there as the fan closes), so each prong lies on the + side of its leaf line, over its gap; the band's width is what blocks low oblique views, and 5.9 mm is the most the two tolerances allow. The row "no hem band" above still holds for the silk; the band is rib |
| Face tilt β | **20°** out of the fan plane, so the dihedral at each fold is 140° | 13 – 30° | INFERRED. The lit/unlit face luminance ratio is 3.5 near the inner edge and 2.9 near the outer edge (up to 3.8 depending on angle). Lambert shading with a key 45 – 60° off the normal gives 18 – 30°. The edge-silhouette ripple gives 10 – 20°. |
| **Pleat depth** | **d(ρ) = 0.0572 ρ tan β**: **0.021 L at the outer edge**, 0.009 L at the inner edge. The faces are flat wedges, so depth is proportional to radius. | 0.013 – 0.033 L at the edge | INFERRED. The face contrast is nearly constant along the radius. |
| Unfolded leaf angle | 173.6° (50 × atan(tan 3.264° / cos 20°)) | 170 – 178° | INFERRED |
| Face shape | The faces read slightly convex (soft silk). The creases are sharp at the valleys and softer at the mountains. | – | MEASURED |
| **Edge scallop** | **One per gap, 0.0066 L peak to trough**, near-sinusoidal. It **notches in at the rib (valley) folds** and bulges out mid-gap. | ±0.003 L | MEASURED from the sub-pixel outer radius, detrended (`fm_m20`). fan1: 0.0074 L, sawtooth. |
| Material | A single layer of silk-like fabric with a soft sheen, with the ribs glued behind | – | INFERRED |

## 8. TASSEL (fan2 only; a separate optional piece)

| Row | Value | Tolerance | Status / how |
|---|---|---|---|
| Attachment | The cord emerges from behind the lobe at its lower-left edge, 0.110 L from the rivet, heading φ 215°. It is threaded through the hollow rivet from behind. | ±0.01 L | MEASURED / INFERRED |
| Cord | Visible length 0.079 L. Rivet to knot top 0.19 L. Diameter **0.010 L**. | length ±0.01, diameter ±0.003 L | MEASURED |
| Knot | A round, bead-like decorative knot, 0.047 L long × 0.046 L wide | ±0.006 L | MEASURED |
| Neck binding | 0.017 L long, 0.025 L wide | ±0.005 L | MEASURED |
| Skirt | **0.373 L long.** Width 0.029 L at the top, 0.050 L at 0.06 L down, 0.063 L at mid length, **0.083 L at the end**. The end is ragged thread tips over about 0.015 L. | ±0.008 L | MEASURED |
| Overall | Knot top to tip 0.437 L. Rivet to tip 0.629 L. | ±0.01 L | MEASURED |
| How it hangs in the photo | Straight, lying out at φ −159.7° (20° below horizontal, to the left). **It is not hanging under gravity**: the photo is a flat-lay or posed product shot. | ±2° | MEASURED |
| In engine | It hangs under gravity from the pivot. For the fan2 comparison render, pose it along −160°. | – | DESIGNED |
| Fullness | A round bundle of fine threads, about 0.07 L thick at mid length (laid flat, its width equals its diameter) | – | DESIGNED. The strands cannot be resolved. |

## 9. COLOUR (albedo estimates)

Albedo = observed linear value ÷ (backdrop 0.922 lin × mean shading 0.8), the same method as the black-hat spec. The
absolute level is good to about ±35 % (±50 % for the tassel), and the chromaticity is solid. Design and rib holes are
masked, and the tassel mask is eroded 2 px. Following the pack's material convention, **each default below is the part's
mean colour** and is the value its `Colour` parameter means.

| Part | Albedo (linear RGB, lum) | sRGB | Hue / character | Status |
|---|---|---|---|---|
| **Leaf** | (0.0199, 0.0245, 0.0299), lum **0.024** | **#272B30** | 210°, a cool blue-grey black. Observed lum 0.0176: lit faces 0.0254, unlit 0.0101. | INFERRED |
| **Ribs** (bare) | (0.0151, 0.0191, 0.0213), lum **0.018** | **#212628** | 200°, a slightly greener cool black | INFERRED |
| Guards | (0.0160, 0.0201, 0.0247), lum 0.0195 | #22272C | Same as the ribs within error, so **ribs and guards are one part** | INFERRED |
| **Tassel** | (0.0072, 0.0091, 0.0136), lum **0.009** | **#14181F** | The bluest black (chroma 0.24 / 0.31 / 0.45). It sits at the pack's black floor (0.0097, #191919). | INFERRED |
| Rivet | Polished silver metal | – | Near-neutral | MEASURED |
| fan1 (cross-check) | Leaf #19252E (navy black, sat 0.30). Ribs #39444B and guard #454649 (a lighter grey-black with sheen). | – | – | INFERRED |

## 10. NOT VISIBLE: DESIGNED PROPOSALS

| What | Proposal | Status |
|---|---|---|
| Back of the leaf | Plain black silk. The 24 inner-rib slips are glued along the valley folds up to 0.96 L. The rear guard lies over the leaf's back at the left end, mirroring the front. An eyelet rivet head sits on the back. | DESIGNED |
| **Closed state** | All 26 sticks share one axis; for the rig, close them symmetrically onto the fan bisector. The leaf folds into 50 stacked faces between the guards, its top edge flush with the guard tips. The closed width is the guard width (0.047 L at the tip). The stack is 0.128 L thick at the pivot and about 0.10 L in the leaf zone. | DESIGNED |
| Thicknesses | Inner rib 0.0045 L in the bare zone and 0.002 L in the leaf. Guard 0.010 L. Silk 0.0006 L. | DESIGNED |
| Tassel behaviour | It hangs under gravity. The cord runs through the hollow rivet. The knot is a round, bead-like knot. | DESIGNED |

## 11. fan1 vs fan2 (fan2 followed everywhere)

| Feature | fan1 | fan2 (followed) |
|---|---|---|
| Sticks | 30 (28 + 2) | **26 (24 + 2)** |
| Opening | 143° | **163°** |
| Leaf inner radius | 0.462 L | **0.431 L** |
| Butt lobe | 0.08 – 0.09 L | **0.106 L** |
| Rivet | Solid silver dome, 0.022 L | **Eyelet ring, 0.035 L** |
| Guard tip | Rounded | **Square-cut, softened corners** |
| Rib colour | Lighter grey-black with sheen (≈ 0.056) | **Black (≈ 0.018)** |
| Leaf hue | Navy black, sat 0.30 | **Blue-grey black, sat 0.12** |
| Edge scallop | Sawtooth, 0.0074 L | **Sinusoid, 0.0066 L** |
| Camera | Front-on | **Tilted 11.5° top-away at about 3 L** |
| Tassel | None | **Cord + knot + skirt** |
| Design (masked, not modelled) | Sakura and cats on 29 % of the leaf; pierced ribs | Willow, swirls and seal on 12 %; openwork ribs |
