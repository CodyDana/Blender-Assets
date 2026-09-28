# Black Hat Asset Study

**Date:** 2026-09-25
**Status:** Reference for modelling. Nothing has been built. This pass created no asset, blend, export or render. It wrote only this file and `WorkFiles/blackhat/study_calc/` (measurement scripts, their `.json` output, and viewing aids in `views/`).

**Purpose.** Build-to numbers, construction, textures, recolour data, geometry, LODs, collision, the head socket and the Unreal notes for `SM_BlackHat`. The hat is a blackened conical bamboo kasa with a cloth band knotted on one side, built to match `blackhat_guide.png` exactly.

**Flags**, as in `KUNAI_STUDY.md` and `SMOKEBOMB_STUDY.md`:
- **SOURCED:** measured by someone else, with a URL.
- **DERIVED:** computed from sourced or measured figures, in `bhstudy_calc.py` [S1].
- **ESTIMATE:** a design choice.
- **SNIPPET:** seen only in a search summary; the page itself was not read.
- **MEASURED:** measured here from the reference PNG by the `bhstudy_*` scripts [S1].

**Companions.**
- `REFERENCE_SPEC.md`: the metrology agent's element-by-element spec, written in parallel. Where the two disagree about the reference, **REFERENCE_SPEC.md wins**. This study reads the reference coarsely and says so wherever it does.
- `WorkFiles/blackhat/study_calc/bhstudy_*.py` and their `.json` output: every MEASURED and DERIVED number here [S1].

---

## 1. Summary

| Item | Value |
|---|---|
| Asset | `SM_BlackHat`. Two material slots: `M_BlackHat_Straw` (bamboo body, ribs, rim, lashings, cap) and `M_BlackHat_Cloth` (band, knot, tails) |
| Form | A shallow bamboo cone with a **32°** pitch (115.7° apex angle). It has **9** raised half-round ribs, a woven skin with its strands running round the cone, and a **14 mm** rolled rim with a thin hoop along its inner edge. **18** corded lashings bind the rim, and a 50 mm crown cap sits at the apex. A cloth band goes round the cone at about 30 % of the slant, knotted on one side, with two torn tails hanging past the rim |
| Build-to headline | **500 mm** outer diameter, **153 mm** cone height, about **260 g** |
| Colour | Blackened, nearly neutral with a slight warm cast (linear hue 1 : 0.94 : 0.93, MEASURED). Light grey worn patches cover about 5 % of the front. The cloth is a neutral black |
| Recolour | Two tint-ready parts, straw and cloth. Each has a full-range greyscale `_Detail` map (float data, sRGB-encoded, sRGB ON) and a default Tint, so that BaseColor = Detail.R × Tint = BC at every mip (section 7.4) |
| LODs | About **10,300 / 3,700 / 900** triangles. Screen sizes **1.0 / 0.504 / 0.176** (the pack rule at a bounds radius of about 252 mm). LOD1 switches when the hat is **544 px** across at 1080p |
| Collision | **Two** convex hulls: `UCX_SM_BlackHat_LOD0_00` (body, 31 vertices) and `_01` (knot and tails) |
| Sockets | `HEAD` at the head-vertex seat on the axis, **127.6 mm** above the rim-roll centre plane. +Z up out of the crown, +X forward |
| Not built | Chin cord, inner head ring (gotoku), lining, holes, splits, extra damage, decals, crests, colour variants, anything under the brim except a plain inner skin |

**Five facts shape the build:**
1. **The reference has no scale.** 500 mm is reasoned from real kasa of the same proportions (section 2.5). Everything else follows from ratios MEASURED on the PNG.
2. **The camera is close to orthographic, and that fixes the cone.** The rim ellipse gives an elevation of 20.1°. The apex offset and the slope of the side silhouettes give two independent cone heights that agree within 3 %: a pitch of 31.7 to 32.6° (section 3).
3. **The hat is hand-made, and the reference shows it.** The four visible ribs sit 41°, 47.5° and 32° apart, and the lashings 15 to 31° apart. A 9-rib, 18-lashing hat explains the pattern, but the visible half must be built at the MEASURED azimuths, not at a regular spacing (section 3.3).
4. **The skin is a woven mat, and its strands run round the cone.** The long visible floats are circumferential, broken by short cross divisions. The cone is developable, so each rib bay unrolls without distortion into an annular sector. That development is the strand-space chart for UVs and weave (section 7.2).
5. **At the pack's LOD rule, LOD1 must look almost like LOD0.** A 252 mm bounds radius puts the first switch at 0.889 m, where the hat is 544 px across. The ribs, rim roll, lashings and band are all still several pixels wide there (section 6.3).

---

## 2. The real objects: Asian conical hats

### 2.1 The Japanese family

| Hat | Construction | Diameter × height | Mass | Source | Status |
|---|---|---|---|---|---|
| **網代笠 ajiro-gasa** (monk's, pilgrim's) | Radial-grain bamboo splits (柾の竹ヒゴ) in an ajiro twill. A hexagonal-weave (六ツ目) liner inside. The rim is woven in with matching fine splits. The crown is stitched with rattan. Finished with persimmon tannin (柿渋) five times. An oval rattan head ring (五徳) | **46 × 20 cm**; ring 18.5 × 20 cm | **250 g** with the ring | [2] | SOURCED |
| 網代笠 (Vietnamese-made, temple supply) | Bamboo. Head ring sold separately; **no chin cord** | **50 × 20 cm** | n/a | [4] | SOURCED |
| **托鉢笠 takuhatsu-gasa** (mendicant monk's) | Bamboo body, varnished; bamboo frame. Head stand (頭台) 18 cm across, 7 cm tall, 30 g, fixed with four wires; chin cord | **45 × 15 cm** / **40 × 12 cm** | **150 g** / **120 g** | [3] | SOURCED |
| **三度笠 sandogasa** (courier's) | Sedge (カサスゲ) sewn on a bamboo frame; a round head ring (丸輪) or 五徳. Deep enough to shade the face. Cord looped behind the head and tied under the chin | **1 shaku 6 sun ≈ 48 cm**; 46 × 12 cm | n/a | [5][6][9] | SOURCED / SNIPPET for 46 × 12 |
| **菅笠 suge-gasa** (Etchū Fukuoka) | Men build a conical bamboo frame (笠骨) from splits and women sew sedge onto it [8]. An outer rim hoop (外輪骨) is closed with overlapping claws (爪). Frame ribs (中骨) are thinned where they overlap at the crown and tucked into the rim hoop. Hoop bamboo: karatake, madake or mōsōchiku; ribs: medake [7]. Important Intangible Folk Cultural Property, 2009 | Made in 3 cm steps | n/a | [7][8] | SOURCED process [8]; SNIPPET requirements [7] |
| **編笠 amigasa** | Woven from rush (藺草), rice straw, wild rice (真菰), bark or bamboo sheath. Conical, truncated, deep, cylindrical or folded [1]. The **深編笠 fukaamigasa** is deep to hide the face; the komusō's **天蓋 tengai** is its basket form | n/a | n/a | [1] | SOURCED form |
| **塗笠 nurigasa** | Thin shaved hinoki or sugi board (へぎ板) with washi pasted on, then lacquered. From the late Heian period | n/a | n/a | [1] | SOURCED |
| **陣笠 jingasa** (foot soldier's) | Thin iron, hardened leather (煉革) or paper, black-lacquered as a rule. A flat cone; the Edo-period brim turns up. U-shaped side cords tied behind the head and under the chin. Cotton padding inside | **34.0 × 31.0 × 12.0 cm** (24 iron plates, 7 rivets); 36 × 20, 37 × 16 cm | n/a | [10][11][12] | SOURCED / SNIPPET for the last two |

### 2.2 The neighbours

| Hat | Construction | Size | Source | Status |
|---|---|---|---|---|
| **斗笠 dǒulì** (China) | Warp splits (经篾) are thicker and stiffer and carry the frame; weft splits (纬篾) are finer and weave the pattern, in a one-over-one twill. Often two layers, with oil paper or palm leaf between. The weave starts at a palm-sized crown and works outward; the rim flares slightly. Tung oil, 3+ coats. The brim should cover the shoulders | A She-ethnic "flower" douli is **about 40 cm**, two layers of splits with bamboo leaf between, 220 to 240 splits in the top layer, about 40 steps; splits 60 cm × 5 mm × under 1 mm | [17][18][19] | SOURCED; SNIPPET for split sizes |
| 斗笠 (Matsu, Taiwan) | Woven bamboo frame at the crown and rim, bamboo leaf laid over, several layers of bamboo strip; two chin ties | n/a | [20] | SOURCED |
| **nón lá** (Vietnam) | Bamboo bent into hoops of graded diameter, stacked on a mould into a cone; **16 hoops**. Leaves are threaded 24 to 35 per turn, with a dry bamboo-sheath layer between two leaf layers, sewn on, then varnished. Straps are tied between the 3rd and 4th spokes | About **40 × 17 cm** | [14][15][16] | SOURCED; SNIPPET size |
| General | Kept on "by a cloth or fiber chin strap, an inner headband, or both"; the salakot has both | n/a | [13] | SOURCED |

### 2.3 How the reference relates to the real family

- **Ribs outside the skin.** Real frames carry the skin *on* the ribs (suge-gasa, nón lá) or *are* the skin (ajiro). The reference shows **raised round rods on the outside**, tied at the rim. That is a plausible over-rib build, as when a woven ajiro skin is reinforced by external splints lashed at the rim. Build what the reference shows: ribs on top.
- **Only 9 ribs.** A suge-gasa frame has many ribs and a nón lá has 16 hoops [15]. The reference's 9 heavy ribs, with faint thin radial lines between them (section 3.3), read as main splints over a finer frame. The fine lines go in the texture, not the geometry.
- **Rolled rim with lashings.** The rim edge of an ajiro kasa is "woven in" with fine splits [2]; a suge-gasa's rim is a closed bamboo hoop [7]. The reference shows a thick round roll, a thin hoop along its inner edge, and cord lashings binding roll, hoop and rib ends. Build all three.
- **Crown cap.** Real crowns are stitched with rattan [2] or begin as a palm-sized woven disc [19]. The reference has a low cap about 50 mm across, with the rib ends crossing over its top in a star. Build it.
- **No chin cord, no visible head ring.** Every real kasa is worn with a cord, a head ring, or both [2][3][4][5][13]. The reference shows neither; its underside is not visible. **Do not model either** (section 12).

### 2.4 Blackened finishes and how they wear

| Finish | What it is | How it wears | Source | Status |
|---|---|---|---|---|
| 柿渋 kakishibu | Persimmon tannin, brushed on bamboo kasa to waterproof them, often 5 coats; amber to brown | Darkens with sun and age | [2][21] | SOURCED |
| 渋墨 shibuzumi | Kakishibu mixed with pine soot or sumi: a traditional black for wood and fabric | Darkens and develops a patina | [21] | SOURCED (read as a summary) |
| 黒漆 black urushi | Black lacquer, the usual jingasa and nurigasa finish [1][10] | High points and edges abrade first, showing the undercoat or the substrate. Cured urushi is hard, and abrasion dulls it | [22] | SNIPPET |
| Varnish | Modern takuhatsu kasa and nón lá | n/a | [3][14] | SOURCED |

**What the reference shows (MEASURED, section 3.4).** The worn patches are **light, nearly neutral grey** (linear hue 1 : 0.968 : 0.951), not the brown of bare bamboo or tannin. They lie as soft clouds across the bays, with lighter flecks along strand crests, on the rim roll and on the ribs. That fits a soot or ink black over a pale ground, abraded and dusty, better than lacquer over brown bamboo. **Match the reference's grey, not a brown historical wear.** No sourced wear pattern licenses adding scuffs the reference does not show.

### 2.5 A real size for this hat

| Evidence | Diameter | Height / D | Pitch |
|---|---|---|---|
| Ajiro, Taketora [2] | 46 cm | 0.43 | 41° (domed) |
| Ajiro [4] | 50 cm | 0.40 | 39° (domed) |
| Takuhatsu large / small [3] | 45 / 40 cm | 0.33 / 0.30 | 34° / 31° |
| Sandogasa [5][6] | 46–48 cm | 0.26 | 28° |
| Jingasa [11] | 34 cm | 0.35 | 35° |
| Nón lá [16] | 40 cm | 0.43 | 40° |
| Douli [18] | 40 cm | n/a | n/a |
| **Reference (MEASURED)** | n/a | **0.31** (cone only) | **32.2°** |

The reference's cone is as shallow as a takuhatsu or sandogasa kasa. Real kasa in that class run **40 to 51 cm**. The reference's hat also reads **wide**, and the "ronin" silhouette is a broad brim: a brim that covers the shoulders [17] needs roughly the 50 cm class.

**Build to 500 mm outer diameter (ESTIMATE, reasoned):**
- It sits at the top of the SOURCED 40–51 cm range.
- It is 3.3 × the 15.2 cm head breadth [23]. That leaves the brim 17 cm beyond the temples.
- The ribs, lashings and band then land on real material sizes: 2.5 mm rib rods, a 14 mm roll, 3 mm cord, a 17 mm band, 28–34 mm tails (section 4).

The alternative is 450 mm, the takuhatsu size [3]. Every ratio scales with the choice (question 1).

### 2.6 Mass

- **Bamboo body, scaled by area to 500 mm:**
  - 150 g at 45 cm [3] gives 185 g.
  - 250 g at 46 cm [2], minus a 30 g ring [3], gives 260 g.
- **Coat:** +15 % for a heavy soot-and-oil or lacquer finish (ESTIMATE). That makes the body **213 to 299 g**.
- **Band:** 50,000 mm² of cloth counting both faces is about 250 cm² of cotton. At 150 g/m² (ESTIMATE) that is **4 g**.
- **Total: about 0.26 kg** (0.21–0.30), DERIVED [S1].

---

## 3. The reference, measured

`blackhat_guide.png` is 670 × 599 RGBA, 8-bit, SHA-256 `8244fd61…7ec356`. It is byte-identical to `Downloads/blackhat.png` and carries no C2PA credential (`provenance.json`). All pixels were read through OpenImageIO as stored sRGB bytes / 255 [S1].

### 3.1 The projection

The model is orthographic. A rim circle of radius R seen at elevation e is an ellipse with semi-axes A = R and B = R sin e. An apex at height h above the rim plane appears D = h cos e above the ellipse centre.

| Quantity | Value | Status |
|---|---|---|
| Silhouette bbox | x 1–665, y 142–534 (the hat touches the left edge at x = 1 but is not cropped) | MEASURED |
| Outer semi-major (roll outside) | 332.5 px; centre x 333.0 | MEASURED |
| Virtual apex (meeting point of the two side-silhouette lines) | (332.5, 140.8). The cap top is at y 142, so the **cap top sits level with the cone's apex** | MEASURED |
| Side-silhouette lines | slopes −0.474 / +0.484; max residual 2.1 / 2.8 px over 220 px: **straight**. So the skin does not dish between ribs | MEASURED |
| Front rim, lower silhouette | ellipse fit, rms 1.38 px, B = **110.7 px** | MEASURED |
| Ellipse centre (side extremes) | y 328.5 | MEASURED |
| Roll tube radius | about 9.5 px, from a front roll 18–20 px tall | MEASURED by eye |
| **Elevation** | **20.1°** (asin(110.7 / 323.0)) | DERIVED |
| Apex offset D | 187.7 px directly; 194.0 px from the side-line slopes (a tangent-from-apex solution). **They agree within 3.3 %**, so near-orthographic holds | DERIVED |
| **Pitch** | **31.7° (direct) to 32.6° (slope); build 32.2°**. Apex full angle 115.7° | DERIVED |
| Rotation about the view axis | 0.35° (side extremes at y 326.5 and 330.5) | MEASURED, negligible |

### 3.2 Scale at 500 mm

**0.752 mm/px (1.33 px/mm).**

| Feature | Pixels | At 500 mm | Status |
|---|---|---|---|
| Crown cap diameter | 67 | **50 mm** | MEASURED (`zoom_crown`) |
| Cap: a low dome, rib ends crossing on its top as light spokes; a thin lip proud of the cone | n/a | Lip about 2–3 mm proud | MEASURED by eye / ESTIMATE |
| Rib rods | 3–4 wide, highlight plus a shadow line | **2.5 mm** half-round | MEASURED by eye |
| Faint radial lines between the ribs | 1 px, low contrast | About every 10° | MEASURED by eye (`ruler_cone_left`); too faint for the peak detector (`bhstudy_finelines.json`) |
| Rim roll height (front) | 18–20 | **14 mm** | MEASURED by eye |
| Hoop along the roll's inner edge | about 2 | **1.5 mm** | MEASURED by eye |
| Lashing width | 15–19 | **11–14 mm**, 3 turns (sometimes 4) of about **3 mm** cord, wrapping the roll and the hoop | MEASURED by eye |
| Band, flat stretch toward the knot | 20–25 | **15–19 mm** (build 17) | MEASURED by eye |
| Band, far left, twisted narrow | 6–8 | 5–6 mm | MEASURED by eye |
| Knot | about 35 × 40 | about **26 × 30 mm** | MEASURED by eye |
| Tails, width | about 37 (front) / 45 (back) | **28 / 34 mm**, narrowing to the torn ends | MEASURED by eye |
| Tail tips | (585, 530) front, (642, 500) back | Hang **about 100 / 75 mm below the rim** | DERIVED |
| Tail length, knot to tip | n/a | **about 270 / 240 mm** (0.6 of the slant on the cone plus the free hang) | DERIVED |
| Torn ends | 5–8 jagged teeth over the last 40–55 px | Last 30–40 mm | MEASURED by eye |

### 3.3 Ribs, lashings and band, by azimuth

**Unwrap.** `bhstudy_unwrap.py` samples the cone on (φ, f):
- φ = 0 points at the camera, and + is toward image-right.
- f is the slant fraction from the apex (0) to the rim (1).
- The rulers in `views/ruler_*` mark every 5°.

| Element | Azimuths (°) | Status |
|---|---|---|
| **Ribs** (raised rods) | **−77.5, −36.0, +11.5, about +43.5** (the last one is in the tails' shadow). Spacing 41.5 / 47.5 / 32. A regular 9-rib (40°) set fits with one rib 8° off. An 8-rib set fits worse (spread 14.6° against 8.4°) | MEASURED (`bhstudy_ribs_lashings.json` peaks > 3σ, plus a visual read) |
| **Lashings** | **−80.9, −50.1, −35.1, −14.3, +11.5, +27.1, [hidden, about 37–60], +63.8, +83.3**. There is one at each rib end, and one more in each bay but not at mid-bay. Spacing is 15 to 31°, and 20° on average → **18 lashings** round the hat | MEASURED by eye on `ruler_rim_*`; ±3° at |φ| > 70° |
| Band, slant fraction | f **0.33** at −88°, **0.29** at −30°, **0.30** at 0°, **0.33** at +30°, **0.38** at +55°; knot at φ +62 to +75°, f 0.35–0.47 | MEASURED by eye (`ruler_cone_*`) |
| Tails | Leave the knot, lie on the cone and cross the rim at φ about +38 to +60°, then hang free | MEASURED by eye |

The lashings are not evenly spaced. Near the front the gaps are 101, 135 and 87 px, where an even 20° spacing would give about 110 px each. That is far outside the fit's error. **Build the visible half at the MEASURED azimuths.** Continue the back half at an even 20° spacing, lashing on each rib end. The same applies to the ribs. REFERENCE_SPEC.md fixes the final numbers.

### 3.4 Surface, weave and colour

| Quantity | Value | Status |
|---|---|---|
| Weave, by eye | Long **circumferential** floats with fine grain lines along them, broken by short cross divisions into staggered blocks: a twill or ajiro mat of flat splits seen from outside | MEASURED by eye (`crop_weave_x6`, `crop_rimleft_x4`) |
| Weave, courses along the slant | Vertical FFT peak 8.9–10.0 px at the front, divided by sin(pitch + elev) = 0.79 → **about 9 mm** | MEASURED (`bhstudy_weave_fft.json`), coarse (80 px windows) |
| Weave, block length round the cone | Horizontal FFT peak 30–35 px → **23–26 mm** | MEASURED, coarse |
| Fine grain lines inside a float | 2–3 px → **1.5–2.3 mm** | MEASURED by eye |
| Body, stored luma (rim, ribs and lashings included) | p05 0.052, p25 0.133, **p50 0.174**, p75 0.229, **p95 0.326**, p99 0.478 | MEASURED |
| Body, linear | p50 (0.0273, 0.0252, 0.0252); mean hue **1 : 0.942 : 0.928** | MEASURED |
| Worn light patches (top 8 % of the front skin) | linear mean 0.237, hue **1 : 0.968 : 0.951**. Stored luma > 0.35 covers **4.6 %** of the front skin | MEASURED |
| Dark field (p10–p50) | linear mean 0.020, hue 1 : 0.942 : 0.937 | MEASURED |
| Cloth, tails region | stored p05 0.043, **p50 0.136**, p95 0.353; hue **1 : 0.973 : 0.975** (neutral) | MEASURED |
| Backdrop | stored 0.996 (p01 0.984). Pure white, **no cast or contact shadow** | MEASURED |

**What the reference shows, by eye** (from the crops in `views/`, which are viewing aids only):
- The skin's worn clouds are brightest across the lower-left bays and the front-centre bay. Light flecks follow the strand crests.
- The rim roll shows lighter streaks along its length. The lashing cords catch small highlights.
- The ribs are brighter than the skin (a highlight on the rod) with a dark shadow line on their lower side.
- The band is dull cloth with soft folds. It twists to a narrow cord on the far left and opens flat toward the knot. The knot is a bulky wrap with a loop.
- Each tail is a single layer that twists once and ends in ragged, torn teeth. The tails cast dark shadows on the cone.
- **No** holes, splits, broken ribs, missing lashings, stains, crest, lining, chin cord, head ring, or loose straw sticking out.

**Gaps, and how each is closed without inventing:**

| Gap | Closed by |
|---|---|
| Scale | Section 2.5. The ratios are what is matched |
| The back half | 9 ribs at the fitted 40° phase and 18 lashings at 20° (section 3.3). The band continues as a ring at f about 0.31, lowest at the knot. The tails exist only where the reference shows them. **Show the user a back view before texturing** (question 6) |
| Underside | A plain inner skin: the inside of the woven cone, no ring, no cord, no lining (section 12) |
| Albedo, as against lit colour | Calibrate the BC by rendering the reference view (section 10) |

---

## 4. Build-to table

**Frame.**
- The hat axis is **+Z**, up out of the crown.
- **z = 0** is the rim-roll centre plane.
- The **reference view is Blender's Front view raised 20.1°**: the camera is on −Y, looking toward +Y and down, with image-right = **+X**.
- Azimuth φ is measured from −Y toward +X, so the knot is at φ about +62 to +75°, on the +X side and toward the camera.
- Export is Forward −Y / Up Z, as for every file in the pack [S4].

| Dimension | Build to | Basis | Status |
|---|---|---|---|
| **Outer diameter** (over the roll) | **500 mm** | Section 2.5 | ESTIMATE, reasoned |
| Roll tube | **14 mm** round; centreline radius **243 mm** | 18–20 px tall | MEASURED ratio |
| **Pitch** | **32.2°** (31.7–32.6) | Section 3.1 | MEASURED |
| **Cone height**, roll centre plane to apex | **153 mm** (150–155) | 243 × tan 32.2° | DERIVED |
| Slant, rim to apex | **287 mm** | 243 / cos 32.2° | DERIVED |
| Straightness | Straight generators; no dishing between ribs | Side silhouettes straight within 2.8 px | MEASURED |
| Skin thickness | **4 mm** outer to inner surface; the inner surface parallel and plain | Real bamboo splits under 1 mm [19], layered twice [17][18] plus a coat | ESTIMATE |
| Development | Each bay unrolls to a **33.9°** sector (304.8°/9) of radii 30–287 mm | A cone is developable | DERIVED |
| **Crown cap** | **50 mm** across at its lip (f 0.103). A low dome whose top meets the apex height. Lip 2–3 mm proud; 9 rib ends crossing on top in a star | 67 px | MEASURED / ESTIMATE lip |
| **Ribs** | **9** half-round rods, **2.5 mm**, on the outer surface from under the cap lip to the roll, each end under a lashing. Azimuths per section 3.3 | 4 visible, mean spacing 40.3° | MEASURED visible / DERIVED count |
| Rib length | 258 mm | Slant × (1 − f_cap) | DERIVED |
| Fine radial lines | About every 10°, in the texture only (normal + BC) | Faint | MEASURED by eye |
| **Hoop** | **1.5 mm** round rod on the skin, just inside the roll, all the way round | about 2 px | MEASURED by eye |
| **Lashings** | **18**, at the section 3.3 azimuths on the front and 20° on the back. Each is 3 turns of **3 mm** cord, 11–14 mm wide, wrapping roll + hoop (+ the rib end where there is one) | 9 visible | MEASURED / DERIVED |
| Lashing spacing at the rim | 87 mm mean | 2π × 250 / 18 | DERIVED |
| **Weave** | Circumferential floats in courses of **9 mm**, blocks **23–26 mm** long, staggered; grain lines **1.5–2.3 mm**; faint radials at 10° | Section 3.4 | MEASURED, coarse |
| **Band** | Flat cloth **17 mm** wide, **1.0 mm** thick. Centre at f **0.29–0.33** round the front, dropping to **0.38** near the knot. It twists narrow (5–6 mm) over the far-left quarter, as the reference shows | Section 3.3 | MEASURED / ESTIMATE thickness |
| **Knot** | **26 × 30 mm**, at φ +62 to +75°, f 0.35–0.47 | n/a | MEASURED |
| **Tails** | Two, **28 / 34 mm** wide, **1.0 mm** thick, about **270 / 240 mm** from the knot. They lie on the cone to the rim, then hang **100 / 75 mm** below it, one twist each. Torn ends over the last 30–40 mm, 5–8 teeth | Section 3.2 | MEASURED / DERIVED |
| **Mass** | **0.26 kg** (0.21–0.30) | Section 2.6 | DERIVED |
| AABB | x, y ±250 mm; z −95 (tail tips) to +153 mm | n/a | DERIVED |
| **Bounds radius** | **about 252 mm**. The build measures it as the maximum vertex distance from the AABB centre, as Unreal does | Smoke bomb and kunai practice [S3] | DERIVED |

---

## 5. How the real object is built, and how to model it the same way

The smoke bomb improved only once its tape was one continuous wound strip [S3]. The equivalents here:

| Part | Real build | Model |
|---|---|---|
| **Skin** | One woven mat of flat splits, twill or ajiro, strands running round the cone [2][17] | **A shell of two straight-generator cones** (outer and inner, 4 mm apart), closed at the roll and under the cap. The weave is **not** painted in object space. It is generated in each bay's **development** (arc length round the cone × slant distance), where the strands are true arcs of constant pitch. That is "tape space" for a cone |
| **Ribs** | Splints laid over the skin, tucked under the crown, tied at the rim [7] | **Real rods**: a half-round section swept along the generator at each rib azimuth, sitting on the outer skin. Ends: tucked under the cap lip at the top; under a lashing at the bottom, flattening onto the roll |
| **Rim** | A rolled bundle round the edge, a thin hoop inside it, lashed together [2][7] | **A real torus** (14 mm tube) at r 243 mm, plus a **real 1.5 mm hoop** on the skin just inside. The skin's outer and inner surfaces run into the roll, so there is no open edge |
| **Lashings** | Cord wound 3 turns round the roll and hoop (and the rib end) | **Real cord**: 3 closed loops per lashing, 3 mm section, each loop following the roll + hoop outline offset by the cord radius, with a slight pitch between turns |
| **Cap** | A stitched crown disc or knob [2][19] | A low dome with a lip; the 9 rib ends continue over its top as shallow raised spokes |
| **Band** | A cloth strip wrapped once round the cone and knotted | **A real strip with thickness** (1 mm, two faces and edges), swept round the cone at the MEASURED f(φ) with a small lift off the skin. It twists narrow where the reference shows it. It **passes over the ribs** (a 2.5 mm lift at each crossing, where the reference shows the band bridging) |
| **Knot and tails** | A square or half knot; two free ends | A sculpted knot volume merging into the band and both tails. **Each tail is a real strip with thickness**, laid on the cone to the rim, draped over the roll, then hanging. Torn ends are **real geometry teeth** in the outline, not alpha: the pack's materials are opaque [S3] |

**Vertex factory.** All geometry is authored through a **1 nm position-keyed vertex factory**, never `bmesh.ops.bevel` [S4].

**Mirrors.** The hat is **not mirror-symmetric**: the ribs and lashings are irregular and the knot is on one side. Use no Mirror modifier and no mirrored UVs.

---

## 6. Geometry plan

### 6.1 Chordal error

| Radius | Criterion | Segments round |
|---|---|---|
| Rim, R 250 mm | 0.5 px at the reference framing (1.33 px/mm) | **58** |
| Rim | 0.5 px at the LOD1 switch (1.08 px/mm) | 52 |
| Rim | 0.5 px at the LOD2 switch (0.38 px/mm) | 31 |
| Rim | 0.1 mm absolute | 112 |

These are DERIVED [S1]. In first person, looking at another character's hat from 0.5 m, the hat fills the screen, so LOD0 uses **144 segments round the roll and 72 round the skin** (8 per bay).

### 6.2 LOD0 budget

| Part | Construction at LOD0 | Triangles |
|---|---|---|
| Skin, outer + inner | 72 round × 4 rings, two surfaces | ~1,200 |
| Crown cap | Dome + lip + 9 spokes | ~450 |
| Ribs | 9 × half-round (5 facets) × 6 segments, tapered ends | ~600 |
| Rim roll | 144 × 8-sided tube | ~2,300 |
| Hoop | 144 × half-round (3 facets) | ~900 |
| Lashings | 18 × 3 loops × (8 × 3-sided) | ~2,600 |
| Band | 64 along × 3 across × 2 faces + edges | ~650 |
| Knot | Sculpted | ~600 |
| Tails | 2 × (32 along × 5 across × 2 faces + edges + teeth) | ~1,000 |
| **Total** | | **~10,300** (target 9,000–11,500) |

**Why above about 10k.** The hat is 500 mm across, seven times the smoke bomb. It is a wearable that can fill the screen at LOD0: LOD1 only takes over at 544 px across. Its detail is real structure, not noise: 18 lashings × 3 cord turns is 54 loops, and the cord turns are 4 px wide at the reference framing.

**Context:**
- The smoke bomb shipped 16,108 / 2,952 / 1,406 [S3].
- Game-scale kasa on Sketchfab run 380 to 20,260 faces: a free low-poly kasa at 380, bamboo hats at 1,440, 1,892, 4,396 and 14,592 [25][26].
- The guidelines put props at 1–5k and hero weapons at 20–50k [S4].

**The lever** if the user wants under 10k is the lashings: one sleeve with 3 raised bands instead of 3 loops saves about 1,500.

### 6.3 LODs

**The pack rule** is 1.0 / 0.10 / 0.035 × bounds radius / 50 mm [S4]. At 252 mm that is **1.0 / 0.504 / 0.176**, which switches at **0.889 m and 2.54 m** (90° hFOV, 16:9). At 1080p the hat is **544 px** across at the first switch and **190 px** at the second.

Feature sizes at the switches [S1]:

| Feature | At LOD1 switch | At LOD2 switch |
|---|---|---|
| Rib | 2.7 px | 0.9 px |
| Hoop | 1.6 px | 0.6 px |
| Roll | 15 px | 5.3 px |
| Lashing | 14 px | 4.9 px |
| Band | 18 px | 6.4 px |
| Tail | 30 px | 10.6 px |

| LOD | Screen size | Triangles | What changes |
|---|---|---|---|
| LOD0 | 1.0 | **~10,300** | As in 6.2 |
| LOD1 | **~0.504** | **3,300–4,200** | Skin 54 round (6 per bay, ≥ 52 for 0.5 px). Roll 72 × 6. Hoop 72 × 3-sided. Ribs 3 facets × 2 segments. **Each lashing becomes one sleeve** (about 36 tris; the 3 turns go to the normal map). Band 32 along. Knot and tails at half density, **teeth kept in the outline** |
| LOD2 | **~0.176** | **800–1,000** | Skin 36 × 1 ring. Roll 36 × 4. **Hoop dropped** (0.6 px). **Ribs kept** as 3-sided prisms (54 tris: at 0.9 px each still reads as a line, and dropping them would leave the skin unpainted beneath). **Lashings kept** as 8-tri boxes (4.9 px). Band 16 along; tails as 2 × about 60 tris with the outline simplified |

**Faithful at every LOD.**
- Every LOD keeps the same parts, the same azimuths and the **same analytic UV map** (section 7.2), so the one baked texture set serves all three.
- LODs lose relief, not layout.
- Report the **two-sided** Hausdorff distance and the LOD-switch pop at the reference framing, as the smoke bomb did [S3].
- The inner skin, which matters only from below, may drop to 36 round at LOD1.

---

## 7. Texture plan

### 7.1 Slots and maps

| Slot | Maps (all 2048², power of two, full mip chain) | Colourspace |
|---|---|---|
| `M_BlackHat_Straw`: skin, ribs, hoop, roll, lashings, cap | `T_BlackHat_Straw_BC` | sRGB |
| | `T_BlackHat_Straw_ORM`: R AO (baked from LOD0), G roughness, B metallic 0, **A specular mask** (only if calibration needs it, section 7.4) | linear |
| | `T_BlackHat_Straw_N` | linear, **DirectX green** |
| | `T_BlackHat_Straw_Detail` | **sRGB ON**, one channel (G8) |
| `M_BlackHat_Cloth`: band, knot, tails | `T_BlackHat_Cloth_BC / _ORM / _N / _Detail`, same rules | as above |

`props_lib/ue_import_textures.py` classifies a map by the token after the last underscore, so `_Straw_BC` and `_Cloth_Detail` resolve to BC and Detail without an importer change. The Detail intent is already sRGB ON [S5].

**Texel density** [S1]:

| Slot | Area | At 2048 | At 4096 / 1024 |
|---|---|---|---|
| Straw (skin 2,168 cm² + roll + ribs + cap + lashings) | 3,110 cm² | **31 px/cm** at 70 % packing (28.4 with the inner skin at quarter density) | 4096: 62 px/cm |
| Cloth (both faces) | 500 cm² | **74 px/cm** at 65 % packing | 1024: 37 px/cm |

- The reference framing is **13.3 px/cm**, so a reference-view render is never magnified.
- The guidelines' first-person figure is 10.24 px/cm [S4].
- At 31 px/cm, the 1.5–2.3 mm grain lines are **4.6–7 texels**. That is the smoke bomb's moiré zone [S3], so draw them as **irregular streaks**. Only the 9 mm courses (28 texels) and 23–26 mm blocks (74 texels) are periodic, and those with wander.
- **2048 for both** is the rule. Show a visible loss before asking for 4096 on the straw (question 3).

### 7.2 UV0: analytic charts, shared by every LOD

| Part | Chart | Island |
|---|---|---|
| **Skin, outer** | Each rib bay's **development**: polar (arc length along the strand, slant distance) | 9 annular sectors, 33.9° each, radii 30–287 mm; nested alternately up and down to pack. **Strands follow the U direction of each sector's arcs.** Zero stretch: the cone is developable |
| Skin, inner | The same development | Quarter density (question 7) |
| Ribs | (along the rod, round the section) | 9 thin strips |
| Roll, hoop | (φ, round the tube) | Split into 4 quadrant strips so they pack |
| Lashings | (along the cord, round the cord) | 18 small islands, cardinal rotation only |
| Cap | Planar from above | 1 disc |
| Band, tails | (along the strip, across it) | "Tape space" as on the smoke bomb [S3]; the warp runs along the strip |

- **Seams** fall on the rib lines, which are real discontinuities under the rods, and on the roll and cord boundaries.
- **Padding** 16 px at 2K; cardinal rotation; no mirroring [S4].
- **Lightmaps.** Unreal's UV1 gate is 0 overlapping pixels at 1024 and 2048 on every LOD [S3]. Keep the 1.5 mm hoop's and 3 mm cords' charts from becoming sub-texel lightmap charts: unfold each cord's loops onto one island (the smoke bomb's defect-4 lesson [S3]).

### 7.3 Bake source and look

**Bake source.**
- `M_BlackHat_Straw_Source` and `_Cloth_Source` are procedural. They are driven by per-vertex attributes: `part_id`, `bay`, `dev_u_mm`, `dev_v_mm`, `rib_dist_mm`, `strip_u_mm` and `strip_v_mm`.
- They are baked to the maps. The gallery renders **only from the baked maps**, through a preview material that computes exactly the Unreal formula (section 9).
- **Nothing Blender-only survives into the look.** No pointiness, AO or geometry nodes at render time.

**Straw:**
- Dark soot-black base.
- Weave relief in N: floats, cross divisions, grain streaks and faint 10° radials.
- Soft light-grey worn clouds, placed to match the reference bays: the lower-left and front-centre bays, crest flecks, lighter streaks on the roll, highlights on the cords.
- Roughness about 0.45–0.65 (ESTIMATE, calibrated); lighter wear slightly rougher.
- **No** brown bare-bamboo wear, holes, splits or grime lines. The reference shows none.

**Cloth:**
- Neutral black cotton, soft fold relief baked from the geometry, a fine plain weave along the strip, and frayed thread ends on the torn teeth.
- Roughness 0.85–0.92, metallic 0.
- Smoke bomb precedent for the cloth response [S3].

**Calibration.** Render the reference view (section 10). Match, on that render:
- **straw** stored luma p05 / p50 / p95 = **0.052 / 0.174 / 0.326**;
- **cloth** p05 / p50 / p95 = **0.043 / 0.136 / 0.353**;
- the worn-patch area fraction (**4.6 %** above stored 0.35 on the front skin).

Move the albedo, the wear coverage and the roughness, never the lights.

**Never** sample, project or trace reference pixels into any map (section 11).

### 7.4 Recolour data: full-range Detail × Tint, mip-safe

This is the smoke bomb's final method, which measured Detail × Tint against BC at **±0.11 % over mips 0–8** [S3]. It is applied per slot.

1. **Bake linear float albedo** a(x) (RGB, no quantisation) from the source.
2. **Tint.** Pick T (linear RGB) with the slot's hue and luminance Y_T = p99.9 of Y(a). Hue starts at straw 1 : 0.942 : 0.928 and cloth 1 : 0.973 : 0.975 (MEASURED lit hue) and is refined by calibration. Then d(x) = clamp(Y(a) / Y_T, 0, 1) spans **the full range**.
3. **Store** `_Detail` = round(255 · sRGB_encode(d)) from the float d. It is quantised **once**. The sRGB encode spends codes where a dark hat's values are: a linear d with p50 about 0.1 gets about 25 codes below the median; sRGB-encoded it gets about 90.
4. **Derive BC from the stored Detail**, not from a: BC8 = round(255 · sRGB_encode(sRGB_decode(Detail8) · T)). Then Detail × Tint = BC at mip 0 within BC's own 8-bit step, and the hue is exactly T's.
5. **Mip-safe by construction.** Both maps are sRGB, so both are decoded to linear before the mip filter and before texture filtering. T is a constant, so mip(d · T) = mip(d) · T exactly. The smoke bomb proved this on Unreal's SimpleAverage mips [S3].
6. **Anything non-linear is pre-filtered.** A specular mask (the smoke bomb needed Specular = 0.5 × ORM.A because a constant 0.5 greyed its dark cloth by 53 %) is computed per texel from float data, box-filtered down the chain, and stored in **ORM.A**. It is never a pow() of Detail in the material.
   - For the **straw** (a lacquer- or oil-coated dielectric), a constant 0.5 is physically right, so ship ORM.A = 1.0 unless the reference-view render greys the dark field.
   - For the **cloth**, expect to need the mask, as on the smoke bomb.
7. **Gates** (ESTIMATE, from the smoke bomb):
   - Detail uses ≥ 240 of 256 levels, p0.1 ≤ 10, p99.9 ≥ 245.
   - Mip parity of mean, median and p10 within ±2.5 % at every level on the shipped PNGs.
   - BC is reproduced within 0.004 linear.
8. **Sidecar** (`SM_BlackHat.sockets.json`, `material` block, one entry per slot): the formula, the Tint in linear and sRGB, the map names, the ORM.A meaning, and "BaseColor = Detail.R × Tint; use BC or Detail, never both".

**Hue.** One tint per slot means one hue per slot. The reference's worn patches are 2.6 % warmer in G/R than its dark field (0.968 against 0.942). A single-tint model will render them at the field's hue. That is a MEASURED, stated limitation (question 5). The alternative is a second `WearTint` with a wear mask, which is more than "change colours easily" asks.

**Memory** (DXT1 2.7 MiB, BC5 / DXT5 / G8 5.3 MiB at 2048 with mips):
- Fixed colour: BC + ORM + N per slot, **~13 MiB**, 26 MiB for both slots.
- Recolour: Detail instead of BC, **~16 MiB** per slot.

---

## 8. Collision, physics, sockets, pivot

### 8.1 Collision: two hulls

| Hull | Covers | Construction | Vertices |
|---|---|---|---|
| `UCX_SM_BlackHat_LOD0_00` | Skin, cap, ribs, band ring, roll, lashings | A **circumscribed** 15-gon band at the roll's top and bottom planes (vertex radius 255.6 mm, 5.6 mm over) plus one apex raised about 6 mm, so the cone faces clear the 2.5 mm ribs and the band | **31** (cap 32) |
| `UCX_SM_BlackHat_LOD0_01` | Knot and both tails (the part outside the cone) | Hull of the knot and tail vertices, decimated **outward** | 12–24 |

**Why two.**
- The tails hang up to 100 mm below the rim, outside the body's cone. One hull over everything would add a 100 mm wedge under a third of the brim, and a dropped hat would rest tilted on it.
- The round-trip gate needs LOD0 **0.0 cm outside the hull set** [S3][S4]. A body-only hull would fail it at the tails.
- The body hull fills the hollow underside. A dropped hat then lands on its rim like a flat cone, which is how a real one lands.

**Build notes.**
- `pipeline.make_ucx_hull` decimates to an **inscribed** hull and hulls a whole object [S6]. Author both hulls directly, as the kunai and smoke bomb did [S3].
- Name the hulls after the **LOD0 node** (`UCX_SM_BlackHat_LOD0_NN`), or they import with no collision [S4].

**Physics.**
- **Mass in KG 0.26.**
- Expect the centre of mass low on the axis. Check the offset in-engine.
- Linear damping about 1–2 and angular 1–3 (ESTIMATE) for a wide light disc falling through air.
- CCD is not needed: the hat is not thrown.

### 8.2 The HEAD socket (DERIVED)

**Head.**
- Horizontal section: an ellipse with the ANSUR men-p50 length : breadth ratio 19.7 : 15.2 [23], scaled to a **57 cm** circumference [24]. Semi-axes 10.20 × 7.87 cm.
- Crown: an ellipsoid rising **9.0 cm** above that plane to the vertex (ESTIMATE; sellion to top of head is 11.2 cm [23], and the circumference line runs just above the brow).

**Seat.**
- The inner cone is 4 mm under the outer and parallel, with its inner apex 148.1 mm above z = 0.
- It rests where its generator is tangent to the long (front–back) section, which is wider and touches first:
  - the inner apex sits **11.05 cm** above the ellipsoid centre;
  - contact is on a ring of radius 5.7 cm, 7.3 cm up;
  - the vertex is **20.5 mm** below the inner apex.

| Socket | Position | Axes | Use |
|---|---|---|---|
| `HEAD` | **(0, 0, +127.6 mm)** in the build frame (rim-roll centre plane at z = 0), the head-vertex seat | **+Z** up out of the crown. **+X forward = toward the reference camera (Blender −Y)**, so a character wearing it facing the camera shows the product view, with the knot 62–75° toward the wearer's **left** | Attach to a skeletal socket placed at the head vertex. The user can re-aim forward with the socket's yaw; no rebuild is needed |

**Consequence (DERIVED).**
- With no head ring the rim-roll centre sits **127.6 mm below the vertex**, which is **16 mm below the eye line** (sellion is 112 mm below the vertex [23]). The hat is worn low and hides the eyes: the "ronin" look.
- A real kasa rides on a head ring 7 cm tall and 18 cm across [3], or 18.5 × 20 cm [2], so its brim sits about 5–7 cm higher (ESTIMATE).
- The reference shows no ring, so the default is the no-ring seat (question 4).

**Sockets are Empties** via `pipeline.make_socket`, restored after import from `.sockets.json` by `Scripts/pipeline/ue_import_sockets.py`. That avoids the LodGroup socket drop and the FBX scale-100 bug [S4]. Name: `SOCKET_SM_BlackHat_LOD0_HEAD`.

### 8.3 Pivot

The guidelines put props' pivots at floor contact [S4]. **Origin on the axis at the roll's bottom plane (z = −7 mm)**, where a hat set down brim-first touches the floor. The HEAD socket is then **134.6 mm** above the origin. The tails hang below the floor plane in that pose, as a real hat's would drape. The alternative is origin = HEAD seat (question 4).

---

## 9. The Unreal side

1. **Export.** Via `Scripts/pipeline/export_fbx.py` only. `qa_check` clean with `--budget` at the agreed LOD0 ceiling. The LodGroup file carries LODs and UCX; sockets come from the sidecar [S4].
2. **Import.**
   - **Import Mesh LODs ON.** Apply the screen sizes after import, **computed from Unreal's own measured bounds radius**.
   - Generate Lightmap UVs ON, with the UV1 overlap gate at 0 px on every LOD.
   - **Two material slots**, in a fixed order (Straw 0, Cloth 1), as the kunai shipped [S3].
   - **Nanite off** (a hand-LODded 10k prop).
3. **Collision.** Exactly **2** convex elements. They round-trip within 1e-6 cm through the Unreal re-export, and contain every LOD0 vertex [S3][S4].
4. **Socket.** `HEAD` at scale 1, from the sidecar.
5. **Textures**, through the props importer:
   - BC sRGB (TC_Default); ORM linear (TC_Masks, alpha kept if used); N normal map with flip-green OFF (the file is DirectX); Detail sRGB ON (TC_Grayscale).
   - All maps: **MipGenSettings = TMGS_FROM_TEXTURE_GROUP**, set and read back. The power-of-two gate exists because an NPOT PNG silently imports with NoMipmaps [S3].
   - Optional, and **to verify in engine**: Unreal's texture Composite Texture option that folds normal-map variance into roughness could calm weave shimmer at distance [27].
6. **Materials.**
   - `M_BlackHat_Straw`: BaseColor = BC, or Detail.R × Tint (a static switch). AO = ORM.R, Roughness = ORM.G, Metallic 0, Specular = 0.5 (or 0.5 × ORM.A), Normal = N.
   - `M_BlackHat_Cloth`: the same, plus cloth fuzz. Use a **Substrate Slab** (fuzz amount / roughness / colour) in 5.8's default Substrate, or the legacy **Cloth** model [S3].
   - The recolour step builds these and `MI_BlackHat_*` from the sidecar. Like the smoke bomb, the validation import binds WorldGridMaterial, and the material is specified here, not verified [S3].
7. **Verification.**
   - In a **second, fresh** process on the exact exported bytes, bound by SHA-256.
   - Project `WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject`, new content path such as `/Game/PropsCheck/BlackHat`.
   - One commandlet at a time, only after checking that no `UnrealEditor-Cmd` process is running. Use `MSYS_NO_PATHCONV=1` or PowerShell for `/Game` paths.
   - Pass 1 imports with `save=False` and lets the sidecar step do the only save [S3].

---

## 10. Fidelity method: judge by looking, confirm by measuring

**The reference-view render** is a render of the **shipped LOD0 with the shipped baked maps** through the Unreal-formula preview material:
- **Orthographic**, **670 × 599 px**, **0.752 mm/px**.
- Camera elevation **20.1°** above the rim plane, on −Y, looking at the axis.
- Apex image point **(332.5, 140.8)**; rim ellipse centre **(333.0, 328.5)**.
- **Pure white background, no ground, no shadow catcher**; the reference has no contact shadow.
- Key light from the upper left, so the left bays are brighter and the tails throw shadows to the lower left. Lighting may only chase lighting statistics, never the material's.

**Order of judgement:**
1. **Side-by-side and a 50 % flicker against `blackhat_guide.png`, by eye, before any number.**
   - Every rib, lashing, band turn, knot fold and tail tooth must sit where the reference has it.
   - The worn clouds must sit in the same bays.
2. **Then measure, on that render:**
   - the silhouette (bbox, apex, side-line slopes, front-rim ellipse);
   - the rib and lashing azimuths on the same unwrap (`bhstudy_unwrap.py`, `bhstudy_ribs_lashings.py`);
   - the band's f(φ);
   - tail outlines and tips;
   - weave FFT peaks;
   - straw and cloth luma percentiles, hue and worn fraction.
3. **Measure the render, never a source layer, a map or the builder's report.**

**Also render** the pack's gallery hero shot (3/4, on the pack ground) and a **back view** for question 6.

---

## 11. IP and provenance

**Form.** Conical bamboo and straw hats are centuries old and made across East and Southeast Asia [1][13]. A blackened kasa with a knotted cloth band is a generic ronin or ninja costume element, not franchise-specific. Apply the props deny gate to every emitted name as usual [S4], and use no franchise names in the listing.

**The reference's origin is unknown.** There is no C2PA credential, and only the chunks that a re-save leaves (`provenance.json`). It could be a photo, a render of someone else's asset, or an AI image with its metadata stripped. **Safe route, as for every reference in this project:**
- No reference pixel reaches any shipped map, and the build script does not open the PNG.
- What is taken is scalar measurement: proportions, azimuths, band path, tail outline points traced as numbers (for REFERENCE_SPEC), and colour statistics.
- The geometry is our generator's; the maps are our procedural bake.

This is our reading, not legal advice.

---

## 12. Headwear decisions (the orchestrator's defaults, for the user to change)

| Decision | Default | How to change |
|---|---|---|
| HEAD socket | Empty at the head-vertex seat, (0, 0, +127.6 mm) above the roll centre plane. +Z up, +X toward the reference camera | Move or yaw the socket in the sidecar and rebuild, or adjust it in Unreal |
| Seat height | Head in the bare cone; no ring. The rim sits 16 mm below the eye line | A virtual 5–7 cm head ring raises it (question 4) |
| Inner head ring | **Not modelled**: the reference does not show the underside. The underside is a plain inner skin | Add real ring geometry later if wanted |
| Chin cord | **Not modelled**: the reference has none, though every real kasa has a cord, a ring or both [13] | A variant, on request |
| Band and tails | Same static mesh, own slot (`M_BlackHat_Cloth`), rigid in the reference pose | A skeletal or cloth-simulated tail is a later option |

---

## 13. Open questions for the user

1. **Scale.** 500 mm (the top of the real 40–51 cm range, a wide ronin brim) or 450 mm (the takuhatsu size)?
2. **Irregular spacing.** Build the visible ribs and lashings at the MEASURED azimuths (15–31° lashing gaps), with the back regular? Recommended: yes, it is what the reference shows.
3. **Straw maps at 2048 or 4096?** 2048 gives 31 px/cm, with grain lines at 4.6–7 texels. Decide after the first reference-view comparison.
4. **Seat and pivot.** Hat worn low with no ring (default), or raised 5–7 cm as a real kasa sits on its ring? Origin at the roll bottom (floor contact, default) or at the HEAD seat?
5. **Worn-patch hue.** Accept one tint per part, so the grey wear takes the field's hue (a 2.6 % G/R shift), or add a WearTint?
6. **The back.** Approve a back view of the 9-rib, 18-lashing layout and the band's return before texturing.
7. **Underside.** Inner skin at quarter texel density with the plain weave, or a unique bake?
8. **LOD0 budget.** About 10,300, with 2,600 of it in the lashing cords. Accept, or use sleeve lashings (about 8,800)?

---

## 14. Verification of high-stakes claims

Checked 2026-09-25 by WebFetch, WebSearch and local measurement. Nothing was downloaded to the project. One public FAA PDF was cached by the fetch tool in its own session folder and read only by `bhstudy_pdftext.py`, a text grep.

| Claim | Status | Checked against |
|---|---|---|
| Ajiro 46 × 20 cm, 250 g, oval 18.5 × 20 cm rattan ring, kakishibu, rim woven in, crown rattan-stitched | **Verified** | [2] |
| Takuhatsu 45 × 15 cm 150 g; 40 × 12 cm 120 g; head stand 18 × 7 cm 30 g; chin cord | **Verified** | [3] |
| Ajiro 50 × 20 cm, ring and cord sold or omitted separately | **Verified** | [4] |
| Sandogasa 1 shaku 6 sun ≈ 48 cm, sedge and bamboo, round ring | **Verified** | [5]; 46 × 12 cm SNIPPET [6] |
| Suge-gasa: rim hoop with claws, ribs tucked into it, species | **SNIPPET** | [7] could not be fetched (DNS). [8] verifies only the men-frame / women-sewing split |
| Jingasa: thin iron, leather or paper, black lacquer, U cords, padding; 34 × 31 × 12 cm | **Verified** | [10][11]; 36 × 20 / 37 × 16 SNIPPET [12] |
| Nón lá: 16 hoops; 24–35 leaves per turn; varnish; straps between the 3rd and 4th spokes | **Verified** | [14][15]. 40 × 17 cm is SNIPPET [16] |
| Douli: warp and weft splits, twill, double layer with oil paper or leaf, tung oil; 40 cm, 220–240 splits | **Verified** | [17][18]; split sizes SNIPPET [19] |
| Chin strap, inner headband or both | **Verified** | [13] |
| Head: breadth 15.2, length 19.7, sellion to top 11.2, menton to top 23.2 cm (men p50) | **Verified** | [23], Exhibit 14.3.2.1, source Bradtmiller et al. 2008 |
| Head circumference 57 cm (men); 57.2 / 55.2 (Bushby) | **Verified as quoted** | [24]; the article marks the US figure as disputed |
| Shibuzumi = kakishibu + pine soot, darkens with age | **Verified, summary only** | [21] |
| Urushi abrades on high points and edges | **SNIPPET** | [22] |
| Composite Texture folds normal variance into roughness | **SNIPPET, verify in engine** | [27] |
| Pitch 32.2°, elevation 20.1°, near-orthographic | **Measured** | [S1]: two independent D estimates agree within 3.3 % |
| 9 ribs, 18 lashings, irregular spacing | **Measured / derived** | [S1]. Four ribs and nine lashings are visible. REFERENCE_SPEC.md supersedes |
| Kasa game assets 380–20,260 faces | **Verified** | [25][26] |

**Frozen assets, checked at the end of this pass** (this pass wrote only this study and `WorkFiles/blackhat/study_calc/`):
- **Paper bomb:** `sha256sum -c WorkFiles/paperbomb/paused_2026-09-21/SHA256SUMS_exports.txt` returns **OK for all 6**.
- **Smoke bomb:** the 6 `Exports/` lines of `WorkFiles/smokebomb/regression/post_smoke_bomb/SHA256SUMS.txt` return **OK for all 6** (FBX `a428dd21…`, sidecar `f192abcc…`, BC, Detail, ORM, N).
- **Shuriken:** all **40** files under `Exports/Shuriken/` (FBX, sidecars, PNGs) hash to entries in `WorkFiles/shuriken/regression/post_kunai_plain/SHA256SUMS.txt`, with **0 mismatches**.

---

## 15. Sources

**Read 2026-09-25** means the page was fetched in this pass and the figure quoted from it. **SNIPPET** means seen only in a search summary. **Via** means taken from an earlier project study's verified reading. No images or models were downloaded.

### Hats

| # | Source | URL | Used for |
|---|---|---|---|
| 1 | Wikipedia (JA), 笠 | https://ja.wikipedia.org/wiki/笠 | **Read.** Amigasa, harigasa, nurigasa (へぎ板 + washi + urushi), ajiro and take-gasa, jingasa, fukaamigasa, tengai, sandogasa, manjū-gasa |
| 2 | Taketora, 国産竹網代笠 | https://www.taketora.co.jp/c/favorite/sa00870 | **Read.** 46 × 20 cm, 250 g; 柾の竹ヒゴ, 網代編み; 六ツ目 liner; rim woven in; crown rattan-stitched; 五徳 楕円型に籐巻き, W18.5 × D20 cm; 柿渋 ×5 |
| 3 | Kameya Direct (Yahoo! Shopping), 托鉢笠 頭台付 | https://store.shopping.yahoo.co.jp/kameya/npd-6923-26.html | **Read.** 約45cm × 15 cm, 150 g; 約40cm × 12 cm, 120 g; bamboo, varnished; 頭台 直径18cm 高さ7cm 30g; chin cord; 針金4本 |
| 4 | Kōkadō, 網代笠 | https://official-store.kokadou.com/view/item/000000002329 | **Read.** 直径50㎝ 高さ20㎝; made in Vietnam; ごとく sold separately; no chin cord |
| 5 | Etchū Fukuoka Sugegasa Shinkōkai, 三度笠 | https://sugegasa.jp/item/%E4%B8%89%E5%BA%A6%E7%AC%A0/ | **Read.** 1尺6寸（約48㎝）; カサスゲ, 竹; 丸輪 head ring, 五徳 option |
| 6 | Search summary, 三度笠 sizes (Kameya nm-9202t and others) | https://store.shopping.yahoo.co.jp/kameya/nm-9202t.html | **SNIPPET.** 46 × 12 cm; 39 × 12 cm (small) |
| 7 | Takaoka City, 越中福岡の菅笠製作技術 | https://www.city.takaoka.toyama.jp/soshiki/kyoikuiinkai_bunkazaihogokatsuyoka/1/4/6/3756.html | **SNIPPET** (fetch failed: DNS). 外輪骨 closed with 爪; 中骨 thinned at the crown and inserted in the 外輪骨; カラタケ, マダケ or モウソウチク, and メダケ; 3 cm size steps |
| 8 | Bunka Isan Online, 越中福岡の菅笠製作技術 | https://online.bunka.go.jp/heritages/detail/160058 | **Read.** Men build the conical 笠骨 from bamboo splits; women sew the sedge |
| 9 | Wikipedia (JA), 三度笠 | https://ja.wikipedia.org/wiki/三度笠 | **Read.** Bamboo bark or sedge; deep, covering the face; cord behind and under the chin; named for the sandobikyaku couriers |
| 10 | Meihaku, 陣笠とは | https://www.meihaku.jp/art-knowledge/about-jingasa/ | **Read.** 薄い鉄、革、紙, lacquered; flat cone; U-shaped cords tied behind and under the chin; cotton padding |
| 11 | Tokyo Fuji Art Museum, 鉄錆地二十四枚張陣笠 | https://www.fujibi.or.jp/collection/artwork/00609/ | **Read.** 34.0 × 31.0 × 12.0 cm; 24 iron plates, 7 rivets |
| 12 | Search summary, 陣笠 sizes | https://online.bunka.go.jp/heritages/detail/175344 (among others) | **SNIPPET.** 36 × 20 cm; 37 × 16 cm |
| 13 | Wikipedia (EN), Asian conical hat | https://en.wikipedia.org/wiki/Asian_conical_hat | **Read.** Names; "chin strap, an inner headband, or both"; salakot |
| 14 | Wikipedia (EN), Nón lá | https://en.wikipedia.org/wiki/N%C3%B3n_l%C3%A1 | **Read.** Bamboo bent into circles; 24–35 leaves per turn; sheath layer; varnish; straps between the 3rd and 4th spokes |
| 15 | AO Journeys, "Everything about nón lá" | https://aojourneys.com/everything-about-non-la-leaf-hat | **Read.** 16 round bamboo rims |
| 16 | Search summary, nón lá size (Qua Lưu Niệm VN) | https://qualuuniemvn.com/en/product/vietnamese-conical-hat-non-la/leaf-hat-conical-hat-big-size-h-40cm.html | **SNIPPET.** 40 cm × 17 cm. The page itself reads only "H=40cm" |
| 17 | NetEase, 古代竹制斗笠 | https://www.163.com/dy/article/K64MS5E405563IC9.html | **Read.** 经篾 / 纬篾; 斜纹 压一挑一; double layer with oil paper or palm leaf; tung oil ≥ 3 coats; brim covers the shoulders |
| 18 | Sohu, 畲族竹编（斗笠）制作技艺 | https://www.sohu.com/a/810238768_121117461 | **Read.** 直径约40厘米; two layers of splits with 箬叶 between; 220–240 splits; about 40 steps |
| 19 | Search summary, douli strips and crown | (query "斗笠 竹篾 直径 厘米 编织 结构 笠顶 边沿 油") | **SNIPPET.** Splits 60 cm × 0.5 cm × < 1 mm; a palm-sized crown worked outward; the rim flared |
| 20 | Taiwan Cultural Memory Bank, 斗笠 (Matsu) | https://tcmb.culture.tw/zh-tw/detail?indexCode=Culture_Object&id=573743 | **Read.** Woven bamboo frame, bamboo leaves; chin ties |

### Finishes

| # | Source | URL | Used for |
|---|---|---|---|
| 21 | Katsuragi, 渋墨塗り | http://www.katuragi.or.jp/annai/sibuzumi1.htm | **Read** (tool summary). Kakishibu + pine soot or sumi; darkens and patinates |
| 22 | Antique Identifier, urushi | https://www.antiqueidentifier.org/japanese-lacquerware-identifying-genuine-urushi-from-imitations/ | **SNIPPET.** Wear on rims reveals the under-layers or the base |

### Anthropometry

| # | Source | URL | Used for |
|---|---|---|---|
| 23 | FAA Human Factors Design Standard, ch. 14, Exhibit 14.3.2.1 (data: Bradtmiller, Hodge, Kristensen & Mucher, 2008) | https://hf.tc.faa.gov/hfds/download-hfds/hfds_pdfs/Ch14_Anthropometry_and_biomechanics_Oct2009.pdf | **Read** (text streams, `bhstudy_pdftext.py`). Men / women p50: head breadth 15.2 / 14.4; head length 19.7 / 18.7; sellion to top 11.2 / 10.5; menton to top 23.2 / 21.8; bitragion 14.5 / 13.3 cm |
| 24 | Wikipedia (EN), Human head | https://en.wikipedia.org/wiki/Human_head | **Read.** Circumference 57 cm men, 55 cm women (US, disputed); 57.2 / 55.2 cm (Bushby et al. 1992) |

### Asset references and Unreal

| # | Source | URL | Used for |
|---|---|---|---|
| 25 | Sketchfab API search, "kasa hat" | https://api.sketchfab.com/v3/search?type=models&q=kasa%20hat&count=24 | **Read.** Kasa 380 faces (×2); a ronin figure 5,146; 20,260; scans 246k+ |
| 26 | Sketchfab API search, "straw conical hat" | https://api.sketchfab.com/v3/search?type=models&q=straw%20conical%20hat&count=24 | **Read.** 1,440, 1,892, 4,396, 14,592 faces |
| 27 | Epic forum, "Texture Composition" | https://forums.unrealengine.com/t/texture-composition/365729 | **SNIPPET.** Adding normal-map roughness into another channel |
| — | Unreal docs: shading models, Substrate, physics bodies, FBX static mesh pipeline, texture editor | Via `SMOKEBOMB_STUDY.md` [28][29][31][33][34] | Cloth and fuzz, Mass in KG, UCX naming, NPOT → NoMipmaps |

### Project files

| # | File | Used for |
|---|---|---|
| S1 | `WorkFiles/blackhat/study_calc/`: `bhstudy_measure_ref.py/.json`, `bhstudy_unwrap.py/.json`, `bhstudy_ribs_lashings.py/.json`, `bhstudy_finelines.py/.json`, `bhstudy_weave_fft.py/.json`, `bhstudy_calc.py/.json`, `bhstudy_pdftext.py`; viewing aids `bhstudy_ruler_views.py`, `bhstudy_zoom.py` → `views/` (scratch only) | **Measured and derived here.** Silhouette, projection, pitch, elevation, azimuths, weave, colour; scale, cone, development, texel density, mass, bounds, LOD sizes, chordal error, hull, head seat |
| S2 | `References/BlackHat/provenance.json` | File identity, no C2PA, shape-and-style use only |
| S3 | `WorkFiles/smokebomb/SMOKEBOMB_REPORT.md` (sections 2, 4, 5), `References/SmokeBomb/SMOKEBOMB_STUDY.md`, `References/Kunai/KUNAI_STUDY.md` | Detail × Tint mip parity (±0.11 %), ORM.A specular mask, sRGB-encoded Detail, one-continuous-strip lesson, tape-space UVs, two slots (kunai), analytic UVs per LOD, UV1 and defect 4, NPOT, triple-save race, two-sided Hausdorff, LOD pop, 16,108-tri LOD0 |
| S4 | `ASSET_GUIDELINES.md`, `Scripts/props/props_lib/spec.py` | Prop 1–5k tris; 2048 props; padding 16 px; UCX / SOCKET naming; LodGroup drops sockets; Forward −Y / Up Z; floor-contact pivot; pack LOD rule and switch distance; deny gate; 1 nm vertex factory and bevel ban |
| S5 | `Scripts/props/props_lib/ue_import_textures.py` | Suffix = last underscore token; Detail sRGB ON / TC_Grayscale; unknown suffix raises |
| S6 | `Scripts/pipeline/helpers.py` (`make_ucx_hull`, `make_socket`, `make_lod_group`) | Inscribed decimated hull; socket Empties; LOD group |
