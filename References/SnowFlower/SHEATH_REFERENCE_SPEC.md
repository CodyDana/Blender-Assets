# SNOW FLOWER SHEATH (SM_SnowFlower_Sheath): REFERENCE SPECIFICATION

> **The rule:** the shipped sheath must look like `SnowFlower_sheath_reference.png`. That means the same straight
> faceted scabbard in dark marbled lacquer, the same eight-plate silver throat around a blossom, one blossom band, the
> same pointed chape and the same single sinuous vine with three blossom clusters. **It has no tassel and no cord**
> (decided). Nothing may be added that the reference does not show, except the parts marked DESIGNED below. Measure
> renders of the shipped asset with the same instruments. If the render looks different, it fails, even when every
> number passes.
>
> **The sheath must hold the sword.** Section 9 shows that the reference sheath and the sword conflict at the tip.
> This needs a **user decision** (9.4).

Machine twin: `WorkFiles/SnowFlower/v4/sheath_spec.json`. It has 69 rows, each with a value, a tolerance, a status and a
method.
Labelled layout (**DEBUG, NEVER SHIP**): `WorkFiles/SnowFlower/v4/sheath_metrology/debug/DEBUG_NEVER_SHIP_sheath_layout_LABELLED.png`.
Legend: orange = fitting boundaries, cyan = mid band, yellow = facet lines, red = vine path, magenta = blossoms, green = pods.

---

## 0. Authority, instrument, conventions

| | |
|---|---|
| **Reference** | `References/SnowFlower/SnowFlower_sheath_reference.png`, 1024 × 1536 RGBA with alpha 1, sha256 `ef794fb1…6a5b7`, on a flat near-white backdrop (0.994) with no shadow. It is a single front view: the sheath is vertical with the mouth up, and the top face of the mouth collar shows as a thin ellipse. |
| **Sword reference** | `References/SnowFlower/SnowFlower_user_reference.png`, 1222 × 1287, sha256 `2ee8af4b…58a8`. The rev-3 geometry comes from `Assets/SnowFlower/SnowFlower_Master.blend`, opened read-only and never saved. |
| **Instrument** | Blender 5.2 headless Python with NumPy 2. The scripts are `WorkFiles/SnowFlower/v4/sheath_metrology/sm_m00 … sm_m21`, the stage outputs are `sm_s*.json`, and the helpers are in `sm_lib.py`. |
| **Coordinates** | Image **row** (0 = top) and **x** px. **t** = (row − 31) / 1465, where 0 is the mouth top and 1 is the chape point. **u** runs from −1 at the left silhouette edge to +1 at the right edge of that row. |
| **Status** | **MEASURED** means read off the pixels (by algorithm, or by visual read on zoomed crops with pixel-grid ticks, marked "visual"). **INFERRED** means a consequence of measured rows. **DESIGNED** means a proposal for what the reference does not show, or a change the fit forces. |
| **Design scale** | **k = 0.687 mm per reference px** (DESIGNED, from the fit in §9). The sheath is then **1.008 m** long. |
| **Build input policy** | This spec is numbers and words. The build must never read, sample, project or trace the reference pixels or any debug image. |

## 1. Overall

| Row | Value | Tolerance | Status |
|---|---|---|---|
| Length | **1466 px**: row 31 (mouth collar top) to row 1496 (chape point) → 1.008 m | ±2 px | MEASURED |
| Axis | Vertical, centre x 505.5. Lean −0.12° (2.4 px of drift over the length), so it **reads straight** | total drift ≤ 3 px | MEASURED |
| Max width | 147 px (the throat's lateral plates, row 89) → 101 mm | ±2 | MEASURED |
| Length / body width | 1466 / 97 = **15.1** | ±0.3 | MEASURED |
| Length / max width | 9.97 | ±0.2 | MEASURED |

## 2. Body: taper and cross-section

| Row | Value | Tolerance | Status |
|---|---|---|---|
| Width below the throat (rows 169–286) | **97 px** constant → 66.6 mm | ±2 | MEASURED |
| Taper | Linear: 96 px (row 322) → 72 px (rows 1250–1292) = **ratio 0.74**. Symmetric: the edges slope +0.0104 and −0.0146 px/row. Samples: 93 px @ row 450, 88 @ 700, 83 @ 900, 78 @ 1100, 74 @ 1200. | ±2 px per row, ratio ±0.03 | MEASURED |
| Front face | Flat, **0.51 of the silhouette width** (facet lines at u −0.52 / +0.51). The lines taper with the silhouette (constant u). | u ±0.04 | MEASURED (median of lacquer luminance with the metal masked) |
| Other visible faces | Two chamfer faces (u 0.51 → ~0.92), **brighter** than the front face (lum 0.21–0.25 against 0.13–0.20), and a 2–4 px bright rim at each silhouette edge (lum 0.44), which is a narrow side face or rounded arris | – | MEASURED |
| Section shape | **Flattened octagon**: front face 50 % of the width, chamfers 21 % each in projection, side faces 4 %. The back mirrors the front. | – | DESIGNED (depth cannot be seen) |
| Depth | **22 mm at the throat → 17 mm at the chape collar** (depth/width 0.33). The chamfers meet the side faces at 35–40 % of the depth. | depth ≥ cavity + 2 × 2.5 mm | DESIGNED (set by §9) |

## 3. Throat (mouth fitting), rows 31–167 (137 px = 9.3 %, 94 mm)

| Row | Value | Tolerance | Status |
|---|---|---|---|
| Top collar ring | Rows 31–40, outer width **63–64 px (0.66 of the body)**. Its top face is visible as an ellipse. | ±2 | MEASURED. **Widened in §9.5.** |
| Tier 1, upper plates | Rows 41–63, silhouette 112 px | ±2 | MEASURED |
| Tier 2 | Rows 65–80, 117 px | ±2 | MEASURED |
| Tier 3, lateral flare | Rows 81–141, **147 px max at row 89**, 115 px at rows 127–139 | ±2 | MEASURED |
| Sleeve | Rows 143–167, 102 px (2.5 px proud of the body per side) | ±2 | MEASURED |
| Plates | **8 pointed leaf/petal plates** radiate from the blossom at ~45° steps: 1 small up (behind the top petal); 2 upper, pointing up and out (tips at row 44, x 450/561); 2 lateral, the largest (tips at row 86, x 432/576); 2 lower, pointing down and out (lower edge at row ~140); 1 central drop plate (point at row 165, x 507, lying on the body). Each plate is a 3–4 px silver rim around a **dark lacquer inset**. | count 8 ± 1 | MEASURED (visual, 4×) |
| Central blossom | 5 petals, **one pointing up**, centre (505, 87), t 0.038. Diameter **~60 px** (41 mm). Domed stamen boss ~10 px. | centre ±3, Ø ±6 | MEASURED (visual + peaks) |
| Filigree | Thorn/lace sprigs between the petals and above the drop plate, in low relief | – | MEASURED (visual) |
| Lace drips | Short pointed silver sprigs on the lacquer at rows 150–178, beside the drop plate | ±4 | MEASURED (visual) |

## 4. Mid band (belt mount), rows 287–321 (35 px, 24 mm), centre row 304, t 0.186 (188 mm below the mouth)

| Row | Value | Tolerance | Status |
|---|---|---|---|
| Structure | Upper ring (rows 284–292), then an **engraved leaf-scroll frieze on a dark ground** (rows 292–308) whose pointed ends bulge at the sides, then the lower ring (rows 308–317) | ±2 | MEASURED (visual, 5×) |
| Width | The rings are 104–106 px (4 px proud of the body per side). The frieze ends reach 117 px (10 px proud). | ±2 | MEASURED |
| Blossom | 5 petals, centre (504, 300), **~50 px wide × ~40 px tall**, overlapping both rings | ±3 / ±6 | MEASURED (visual) |
| Count | **Exactly one** band. No loop, ring or cord is shown. | 1 | MEASURED |

## 5. Chape, rows 1265–1496 (231 px = 15.8 %, 159 mm)

| Row | Value | Tolerance | Status |
|---|---|---|---|
| Silhouette | Collar at body width with no step (rows 1250–1292, 72 px). Side plates at rows 1293–1387, 75–84 px, **max 84 at row 1344**. Ogive: 68 px @ row 1388, 60 @ 1420, 50 @ 1440, 38 @ 1460, 21 @ 1480, 3 @ 1496. | ±2 | MEASURED |
| Point | Ogive. Half-angle ~10° at row 1388, steepening to ~33° over the last 16 px. Very slightly blunt. | ±3° | MEASURED |
| Plates | An up-pointing lancet frame (tip at row ~1268) through which the vine enters. Then the blossom. 2 lateral plates (tips at x 465/545, row 1346). 2 lower-lateral plates (tips at x 475/538, row 1383, giving the step to 68 px). 1 central down plate (tip at row ~1397). The point is made of **2 nested silver lancet outlines around a dark lacquer inset** (the inset ends at row ~1457). | count ±1 | MEASURED (visual, 3×) |
| Blossom | 5 petals, one up, centre (505, 1330), t 0.887, **Ø ~54 px** (37 mm) | ±3 / ±6 | MEASURED (visual + peaks) |

## 6. Vine (raised silver, front face only)

| Row | Value | Tolerance | Status |
|---|---|---|---|
| Path | **One continuous stem.** It leaves the throat under the drop plate (row 167), makes an S-bend right (x 527, row 193), and returns to the band blossom. Below the band it is sinuous, with lateral extremes at rows ~460 (u −0.66), ~660 (+0.66), ~800 (−0.55), ~920 (+0.66), ~1140 (−0.40) and ~1245 (+0.33). The half-wavelength is 150–230 px. A thinner second stem twines around it at rows ~930–1000 and runs beside it at rows 1060–1200. It enters the chape lancet at row ~1262. The waypoint table is in the JSON. | ±4 px lateral, extremes ±15 rows | MEASURED (visual, agrees with the algorithmic metal runs within 3 px at 12 rows) |
| Stem width | Trunk (rows 170–286): **9 px** (0.09 W). Rows 322–700: 6–7 px. Rows 700–1100: 4–6 px. Rows 1100–1262: 4–5 px. Side twigs 2–3 px. Half-round, polished, outline-shaded. | ±2 px | MEASURED (noisy) |
| Open blossoms | **11**, all with 5 petals and a stamen. **Cluster A** (rows 450–605): (486, 495) Ø42, (515, 503) Ø20, (508, 544) Ø43, (532, 570) Ø26, (502, 592) Ø25. **Cluster B** (rows 630–750): (525, 693) Ø42, (498, 718) Ø28, (523, 740) Ø20. **Cluster C** (rows 1005–1140): (518, 1043) Ø39, (495, 1077) Ø38, (513, 1127) Ø27. The t/u of each is in the JSON. | count 11 ± 1; centre ±5 px; Ø ±20 % | MEASURED (visual, 3×) |
| Blossom sizes | Large 38–43 px (0.45–0.50 of the local body width), medium 25–28 px, small ~20 px. Fittings: throat 60, band 50, chape 54. **Total: 14 blossoms.** | ±20 % | MEASURED |
| Buds | Round closed buds, 5–9 px, on short stalks: rows 215–225 (2, above the band), 355–365 (2–3), 452–458 (2), 523 (1, leafy), 558 (1), 635–685 (4), 1008–1023 (3), 1093–1100 (2) | count 18 ± 4 | MEASURED (visual) |
| Teardrop pods | 2 large pointed white pods on thin curved stalks, at (506, 820) and (501, 919), ~12 × 22 px. Rows 750–1000 hold only the stem and these pods. | ±5 px | MEASURED (visual) |
| Leaves | A few small pointed silver leaves, e.g. at (472, 523) and (482, 1125) | – | MEASURED (visual) |
| Etched twigs | **Flat**, faint grey engraved twigs in the lacquer along both chamfers (rows 420–470 left, 550–600 right, 1100–1230 both). They go into the albedo and normal maps only. | – | MEASURED (visual) |

## 7. Marble lacquer

| Row | Value | Tolerance | Status |
|---|---|---|---|
| Tone | Display luminance percentiles of metal-free body pixels: p1 0.057, p5 0.096, p25 0.140, **p50 0.178**, p75 0.218, p95 0.291, p99 0.351 | p50 ±0.03, p5/p95 ±0.04 | MEASURED |
| Colour | **Cool blue-grey black.** Mean sRGB (0.169, 0.184, 0.205), dark quartile (0.101, 0.113, 0.129), bright decile (0.286, 0.303, 0.330). Saturation 0.18. | ±0.03 per channel | MEASURED |
| Veins | Thin (1–2 px ≈ 1 mm) light-grey wisps (lum 0.30–0.45) over soft cloudy mottling, about 7 % of the lacquer. **They run mostly lengthwise**: 66 % of the vein edge energy lies within ±30° of the sheath axis, with diagonal branches. | direction ±15°, fraction 4–10 % | MEASURED (structure tensor, facet lines excluded) |
| Mottling scale | Clouds of 15–40 px (10–27 mm). The autocorrelation length is ~11 px along the sheath and ~4 px across. | ±50 % | MEASURED (weak: 6 patches) |
| Finish | Glossy. The chamfers carry a broad soft sheen and the rims are bright. Roughness 0.15–0.25, non-metal. | – | INFERRED |

## 8. Metal

| Row | Value | Tolerance | Status |
|---|---|---|---|
| Value | Metal pixels (L > 0.30): p50 0.486 (throat), 0.469 (chape); p95 0.93 | ±0.05 | MEASURED |
| Hue | Neutral silver, saturation 0.047 | sat < 0.07 | MEASURED |
| Sheen | Polished. Near-white highlights on 3–6 % of the fitting pixels and dark insets on 16–25 %. **Petals are brightest** (sRGB 0.88) with soft gradients. | – | MEASURED |
| Suggested PBR | Silver base ~0.80–0.85 sRGB, metallic 1. Roughness 0.25–0.35 on plates and stems, 0.15–0.20 on petals. Cavity AO in the engraving. Plate insets are the lacquer material. | – | INFERRED |

## 9. FIT: the sheath must hold the sword

### 9.1 The blade, measured

| | Sheet (front view) | Rev-3 export (master, sliced every 10 mm) |
|---|---|---|
| Scale / frame | 960 px/m (rev-3 overall 1.2563 m over pommel row 10 → tip row 1216) | Blade along +Z (tip at z 1.085), width X, thickness Y |
| Seat → tip | Guard seat at row 338 → **0.915 m** | Guard under-leaf face z 0.1628 → **0.922 m** |
| Width | **53 mm** at the seat → 40.6 mm at 70 % (**23 % taper**, close to the sheath's 26 %) | **46.0 mm** → 43.6 mm at z 0.80 (5 % taper) |
| Thickness | The side view shows 23 → 10 mm, which is not credible (45 % of the width). It is stylised and **not used**. | Steel 6.0 → 2.0 mm. With relief the half-thickness is **max 6.2 mm**, 3.2 at 50 %, 1.9 at 85 %; the relief ends at z 1.008. |
| Tip curve | The back edge is straight to ~63 %, then **bows 19.8 mm** outward. The tip is 44.9 mm off the base axis, on the viewer's **left**. | The −X edge sweeps up from z ~0.80. The back edge **bows 8.2 mm**. The tip is at x **+30.5 mm**. |
| Guard below seat | – | Pendant 24.8 × 18.4 mm, 7.8 mm deep (z 0.1628 → 0.1708) |
| Note | – | **Rev-3 is mirrored** relative to the sheet's front view (tip and tassel toward +X seen from −Y), so the rev-3 "front" is the sheet's back view. |

### 9.2 The conflict

The reference sheath is **straight and symmetric with a centred point**, and its body **tapers 26 %**. The sword is a
single-edged dao. Its tip sits on the back-edge line (rev-3) or beyond it (sheet), **30–45 mm off the blade's base
axis**. At a natural length, with the tip resting 65–80 mm above the chape point, a straight symmetric sheath cannot
hold either blade, even with the best cavity offset. The static margin is −1 to −3 mm for rev-3 and −10 to −12 mm for
the sheet (walls 2.5–3 mm, clearance 1–1.5 mm per side; `sm_m12`, `sm_m15`). Tilting the blade 1° inside gains
little and puts the guard 8 mm off-centre.

### 9.3 Trade-off: blade back-edge sweep against sheath bow

These figures are for a natural length of ~1.0 m, 2.5 mm walls and 1.0 mm clearance, with the tip resting at ref row
1380 (`sm_m16`).

| Back-edge sweep | Bow needed in the sheath's lower part | Reads straight? |
|---|---|---|
| **0 mm** | 0 (cavity offset +2.4 mm) | **yes** |
| **2 mm** | 1.7 mm = 2.4 ref px, from row ~840 | **yes** (≤ 3 px) |
| 4 mm | 5.5 mm = 8 px | borderline |
| 6–8.2 mm (rev-3) | 8.1 mm = 11.7 px, from row ~860 | no: a slight sori, with the chape ~12 px off-axis |
| 19.8 mm (sheet) | 21 mm = 31 px, from row ~440 (sheet outline, `sm_m16b`) | no: visibly curved |

Long straight alternative: a straight sheath holds the rev-3 blade only if its tip rests at row ≤ ~1225. That makes
the sheath **≥ 1.14 m**, with ≥ 21 cm hollow past the tip. The sheet blade needs a bow of ≥ 16 mm at any length up to
1.2 m.

### 9.4 RECOMMENDED resolution (a USER DECISION)

- **Sheath exactly as the reference**: straight, symmetric, centred point. k = 0.687 mm/px gives **1.008 m** overall,
  66.6 mm wide below the throat, 49.5 mm at the chape collar, a 101 mm throat and a 159 mm chape.
- **Tip rest**: the blade tip rests at **ref row 1380**, just above the lower-lateral chape plates, leaving 80 mm of
  solid ogive below. The tip clearance to the cavity end is 5 mm.
- **Cavity**: the blade outline plus **1.0 mm** clearance per side, with **2.5 mm** walls. The cavity axis is offset
  **2.5 mm toward the blade's back edge**. A hidden bow of ≤ 2 mm (≤ 3 ref px) is allowed from ref row ~840 down.
- **What this requires**: the v4 blade's back edge must stay **straight to the tip** (sweep ≤ 2 mm). The curved-tip
  look must come from the cutting edge sweeping up to a straight back. This conflicts with rev-3 (8.2 mm) and with the
  sheet (19.8 mm).
- **Fallbacks, if the blade keeps its sweep**:
  - Keep the rev-3 sweep and give the sheath's lower part an 8 mm bow toward the back edge from row ~860 (a slight
    sori).
  - Keep the sheet sweep with a 21 mm bow (visibly curved; no longer the reference).
  - Engine-side: hide the blade while sheathed (a hilt-only mesh, or a masked blade section) so nothing can poke
    through.

### 9.5 Mouth, cavity, sockets (DESIGNED)

| Row | Value |
|---|---|
| Mouth collar | The measured 64 px is 44 mm, less than the rev-3 blade's 46 mm. **Widen the collar to ≥ blade width + 5 mm**: 51 mm (74 px, 0.77 of the body) for rev-3, or ≥ 58 mm for a 53 mm sheet-width blade. It is hidden under the guard when sheathed. |
| Mouth interior | The opening is the blade section + 1 mm. **Pendant pocket 27 × 21 × 9 mm**, so that the guard's under-leaves (rev-3 z 0.1628) seat on the collar top. It is lined in black lacquer. |
| Cavity thickness | 2 × (blade half-thickness incl. relief + 1 mm): **14.4 mm** near the mouth, 8.4 at 50 %, 5.8 at 85 %. The outer depth of 22 → 17 mm leaves walls of ≥ 2.5 mm. |
| Static vs swept | A game needs only the **static** (sheathed-pose) fit. Straight insertion is not required. |
| **SOCKET_Holster** | At the collar-top plane, on the **cavity axis** (2.5 mm toward the blade's back edge). +Z points out of the mouth and +X toward the blade's back edge. The sword's matching point is the centre of its guard seat plane on the blade axis. The blade runs along −Z and is fully inside. |
| **SOCKET_Hip** | At the mid band (row 304, 188 mm below the mouth), on the **back face** centre. +Z points toward the mouth. |

## 10. Not shown in the reference (DESIGNED)

- **The back face** is plain marbled lacquer. The fittings continue around it as plain rings and plates, and blossoms
  appear only on the front.
- **The depth** and cross-section, including the side faces.
- **The mouth interior**, the cavity and the pendant pocket.
- **Belt hardware**: none is shown, so there is only the hip socket.
- **Tassel and cord: NONE** (decided).

## 11. IP note (record only)

The sword sheet is titled **"JIN MUWON – SNOW FLOWER BLADE"**. Jin Mu-won is the protagonist of the Korean webtoon
*The Legend of the Northern Blade*. That is fine for the personal project. If the design derives from that franchise,
it must not be sold on Fab under that name or design. **The user decides.**
