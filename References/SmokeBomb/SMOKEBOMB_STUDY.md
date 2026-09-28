# Smoke Bomb Asset Study

**Date:** 2026-09-21
**Status:** Reference for modelling. Nothing has been built. No asset, blend, export or render was created in this pass.

**Purpose.** Build-to numbers, construction, texture, geometry, collision, sockets and Unreal notes for `SM_SmokeBomb`. It is a ball wrapped in overlapping strips of dark brown-black woven cloth tape, built to match `smokebomb.png` exactly.

**Flags**, as in `KUNAI_STUDY.md` and `PAPERBOMB_STUDY.md`:
- **SOURCED:** measured by someone else, with a URL.
- **DERIVED:** computed from sourced or measured figures.
- **ESTIMATE:** a design choice.
- **SNIPPET:** seen only in a search summary; the page itself was not read.
- **MEASURED:** measured here from the reference PNG by the scripts in `WorkFiles/smokebomb/study_calc/` [S1].

**Companions.**
- `REFERENCE_SPEC.md`: the metrology agent's band-by-band layout and over/under order, written in parallel. Where the two documents disagree about the reference, REFERENCE_SPEC.md wins, because it measures each band and this study only reads the reference coarsely.
- `WorkFiles/smokebomb/study_calc/sbstudy_*.py`, with their `.json` output: every MEASURED and DERIVED number here [S1].

---

## 1. Summary

| Item | Value |
|---|---|
| Asset | `SM_SmokeBomb`. Material `M_SmokeBomb`. Maps `T_SmokeBomb_BC / _ORM / _N`, all 2048 |
| Form | A slightly out-of-round ball wound with flat, plain-woven cotton tape. Bands run along great circles, stack up to three deep and meet at "poles". The tape has a selvedge bead and a light fray on its edges, plus a few loose threads |
| Build-to headline | **70 mm** mean diameter; outline 69.4 × 70.7 mm. **10 mm** tape, **0.5 mm** thick; about **4 layers** mean, 5.8 m of tape. About **120 g** |
| Colour | Dark warm brown-black. Linear hue 1 : 0.85 : 0.80 (MEASURED); albedo about 0.040 linear luma (ESTIMATE, calibrated by render) |
| LODs | About 5,000 / 1,500 / 600 triangles. Screen sizes about 1.0 / 0.073 / 0.0255 (pack rule, bounds radius about 36.4 mm) |
| Collision | **One** convex hull: `UCX_SM_SmokeBomb_LOD0_00`, a 32-vertex circumscribed pentakis dodecahedron |
| Sockets | `Grip` and `Burst`, both at the centre. **No fuse**: the reference has none |
| Not built | Fuse, knot, tag, cord, paper, scorch, dirt, grime, faded patches, stains, damage, a free tape end, colour variants |
| Fab AI flag | The reference carries an OpenAI C2PA manifest. If no reference pixel reaches a shipped map, nothing needs declaring. The user decides (section 11) |

**Four facts shape the build:**
1. **The reference has no scale.** 70 mm is reasoned from ball sizes people can throw with one hand, and from a standard 10 mm tape at the reference's measured tape-to-diameter ratio of 0.12 to 0.17 (section 4).
2. **The bands are great circles, and that fixes the back.** A flat tape can only lie on a sphere along a geodesic. Every great circle has exactly half of itself in the visible hemisphere. So the front view decides every band's path all the way round. One global winding order then decides every crossing on the back (section 6.1).
3. **The reference's finest weave is below what a 2048 map can draw cleanly.** The warp ribs repeat every 0.30 to 0.37 mm, which is 4 to 5 texels. The kunai showed that a periodic weave that fine moirés. Ribs are drawn as irregular streaks; only the 0.79 mm cross-threads and the 1.3 to 2.0 mm slubs are periodic (section 7).
4. **The overlap must be geometry.** This is the kunai lesson. At the reference framing, one 0.5 mm tape step is 6.6 px, and the reference's outline shows 46 such steps (section 3).

---

## 2. The real object: smoke and blinding balls

No historical smoke ball wrapped in cloth tape is documented. What is documented is a family of hand-thrown smoke, blinding and fire balls, plus two cloth-wrapped balls that are not weapons. The reference is a design in that family. It should be built as a plausible real object, but copied from the reference, not from history.

| Object | Construction | Size / mass | Source | Status |
|---|---|---|---|---|
| **鳥の子 torinoko** (Bansenshukai, 1676 [6]) | Saltpetre and a smoke agent, wrapped in many layers of torinoko washi and hardened into an **egg shape**. Thrown after lighting; bang and smoke | "Egg-shaped". No dimension found | [1][2][3] | SOURCED construction; size not found |
| **卵目潰し egg metsubushi** | An eggshell filled with blinding powder (ash, pepper, sand, flour) and thrown at the face | Hen's egg, about 56–61 × 43–45 mm | [1][4][14] | SOURCED construction, SNIPPET egg size |
| Metsubushi (general) | Powder in hollowed eggs, bamboo tubes or small boxes; blown or thrown | none | [4] | SOURCED (the eggshell line is uncited in [4]) |
| 取火方 toribikata | **Not a ball**: a copper tube on a handle. The 2018 test gave sparks to 3 m and reddish smoke for about 20 s | n/a | [5] | SOURCED. Kept out of the design |
| てつはう tetsuhau (1281, Takashima wreck) | Hollow ceramic sphere with gunpowder, metal and ceramic shards | **13 cm** | [7] | SOURCED |
| 焙烙玉 hōroku-dama | Earthenware grenade with a fuse; thrown by hand or swung on a rope. No original survives | Museum replica about 15 cm, 2 kg | [8][9] | SNIPPET size |
| Blendkörper 1H (1940s) | Glass smoke bulb, thrown by hand | **64 mm** diameter, 150 mm long, **370 g** | [10] | SOURCED |
| M67 grenade | The modern standard for a ball thrown by hand | **64 mm**, **400 g**, 35 m thrown | [11] | SOURCED |
| Consumer "smoke balls" (fireworks) | Small coloured cardboard ball, fuse at the top, smoke about 10–15 s | No size found | [15] | SOURCED form, SNIPPET time |
| Baseball | Cork or rubber centre **wound with yarn**, then a cover. Wound-ball construction | **73–75 mm, 142–149 g** | [12] | SOURCED |
| Tennis ball | n/a | **65.4–68.6 mm, 56.0–59.4 g** | [13] | SOURCED |
| 手毬 temari | Wadded silk core **wrapped with strips of fabric**, then thread. A historical Japanese cloth-wrapped ball | Between a softball and a handball | [16][17] | SOURCED form |

**What this means for the build:**
- **Size.** The balls meant for one hand cluster at **64 to 75 mm** (grenades, Blendkörper, tennis ball, baseball). The ceramic grenades are two to three times larger and cannot be carried in a sleeve. A torinoko is described as egg-shaped, about 45 to 60 mm. The reference is round, not egg-shaped, which puts it with the 64 to 75 mm group.
- **Construction.** Every historical smoke ball is a thin shell (washi, eggshell or pottery) around a dry fill. Cloth over the shell is the reference's own addition. The wound-ball method (baseball, temari) is the right physical model for how the tape lies.
- **No fuse.** Historical smoke balls had fuses; the reference has none. The asset is an impact-burst prop. A fuse would be a variant, and only if the user asks for one.

---

## 3. The reference, measured

`smokebomb.png` is 1254 × 1254 RGB, 8-bit, SHA-256 `813105ec…7b6e1c2`. It is byte-identical to `Downloads/smokebomb.png`. All pixels were read in Blender 5.2 with the colourspace forced to Non-Color, so values are the stored sRGB bytes divided by 255 [S1].

**Provenance (MEASURED from the file's `caBX` chunk).** The PNG carries a C2PA manifest. Its fields:
- `softwareAgent` ChatGPT, version `gpt-image`
- `digitalSourceType` `trainedAlgorithmicMedia`
- claim generator "OpenAI Media Service API"
- created 2026-09-19T08:47:57Z; actions `c2pa.created`, `c2pa.converted`, `c2pa.watermarked.unbound`

The image is an AI-generated product shot, not a photograph. It is still the reference of record: match it (section 11 covers the consequence).

**Scale.** At the design diameter of 70 mm, the mean outline radius of 463.92 px gives **0.07544 mm/px (13.255 px/mm)**. The whole frame spans 94.61 mm.

| Quantity | Value (px) | At 70 mm | Status |
|---|---|---|---|
| Silhouette bbox | 926 × 948 | 69.9 × 71.5 mm | MEASURED |
| Outline, fitted ellipse | semi-axes 459.6 / 468.2 | **69.35 × 70.65 mm, ratio 1.019**. Long axis 124.6° counter-clockwise from image-right, i.e. tilted 35° left of vertical | MEASURED |
| Outline radius, min–max | 449.9–482.9 | 33.94–36.43 mm; the maximum is the pole stack at the top | MEASURED |
| Outline lumpiness (30° high-pass) | σ 3.3, p05/p95 ±5.1 | σ 0.25 mm, ±0.38 mm | MEASURED |
| **Steps in the outline** (tape edges crossing the limb) | 46 steps ≥ 2 px/°; median 3.5, p75 5.5, max 10.3 | **median 0.26, p75 0.41, max 0.78 mm** | MEASURED |
| Band width, across single tapes | 110–160 | **8.3–12.1 mm; w/D 0.12–0.17** | MEASURED coarsely, from profiles and gridded views. REFERENCE_SPEC.md refines it |
| Weave: fine rib along the tape (FFT peak) | 4.0–4.9 | **0.30–0.37 mm, 27–33 ends/cm** | MEASURED at 7 patches |
| Weave: lighter cross-threads | 10.4 | **0.79 mm** | MEASURED |
| Weave: slubby banding | 17.8–26.6 | **1.3–2.0 mm** | MEASURED |
| Selvedge bead along each edge | about 6–8 wide | about 0.45–0.6 mm | MEASURED by eye |
| Cloth, inner 80 % of the disc, stored sRGB | p05 (0.043, 0.035, 0.035), p50 (0.122, 0.110, 0.106), p95 (0.318, 0.298, 0.282) | n/a | MEASURED |
| Same, linear | p50 (0.0137, 0.0116, 0.0110), mean (0.0246, 0.0214, 0.0194), p99 (0.171, 0.156, 0.138) | **hue 1 : 0.847 : 0.800**, warm | MEASURED |
| Cloth stored luma | p01 0.017, p05 0.036, p25 0.073, **p50 0.111**, p75 0.169, **p95 0.302**, p99 0.433 | n/a | MEASURED |
| Lighting, sector means (stored luma, 0.3–0.92 R) | top and upper-right 0.18, right 0.146, left 0.138, lower-left 0.109, **bottom 0.097**, lower-right 0.113 | Key from top / upper-right; bottom at 0.54 × top | MEASURED |
| Rim | ring 0.95–1.0 R mean 0.195, against 0.124 at the centre | 1.57 × brighter at grazing angles: a cloth sheen signature | MEASURED |
| Backdrop | stored 0.996 everywhere; directly below the ball, min 0.988 | Pure white, **no cast or contact shadow** | MEASURED |

**What the reference shows, by eye.** These were read from brightened crops (viewing aids only, written to scratch).
- **Bands run in groups.** Several parallel turns lie side by side, partly overlapping. Near the left limb, the exposed strips of partly covered tapes are 4 to 7 mm wide.
- **Groups cross at shallow and steep angles.** A wide band crosses the middle from the centre-left to the right limb, over the others. A second wide band crosses the lower half.
- **The top is a pole.** Many bands converge there in a swirl and stack up, which is where the outline peaks (+1.43 mm, about three layers). The swirl and the fan of bands running down both sides from it are what you get from winding a ball of yarn: the turns of one group share a near-common axis and cross at its two ends.
- **Tape edges.** Each edge is a slightly rolled selvedge bead with short crossing threads (a "ladder") and small weft loops. A few loose threads hang off. By eye, four to six cross the silhouette: upper-left limb, lower-left, right limb, bottom-left. REFERENCE_SPEC.md should count and place them.
- **No dirt, wear, stain, fuse, tag, knot, cord, free tape end or visible core.**

**What the reference does not tell us, and how each gap is closed without inventing:**

| Gap | Closed by |
|---|---|
| Scale | Section 4 reasoning. The ratios are what is matched |
| The back of the ball | Great-circle continuation plus one winding order (section 6.1) |
| Albedo, as opposed to lit colour | Calibrate the BC by rendering the reference view (section 10), inside the dielectric band |
| The interior | Not modelled. It only sets the mass (section 4) |

---

## 4. Build-to table

**Frame.** Ball centre at the origin. The **reference view is Blender's Front view**: camera on -Y looking toward +Y, image-up = **+Z**, image-right = **+X**. Export is Forward -Y / Up Z, as for every file in the pack [S6]. The pivot is the ball centre, which is also the centre of mass (section 8).

| Dimension | Build to | Basis | Status |
|---|---|---|---|
| **Mean outline diameter** | **70.0 mm** | One-hand balls 64–75 mm [10][11][12][13]; 10 mm tape at w/D 0.12–0.17 gives 59–83 mm, centred on 71 mm; the kunai's tape is 10 mm (pack consistency) | ESTIMATE, reasoned |
| Out-of-round | Base surface a spheroid **69.35 × 70.65 mm** as seen from -Y, long axis tilted 35° left of +Z in the XZ plane. Depth axis 70.0 mm | Outline ellipse 1.019 [S1] | MEASURED shape, ESTIMATE depth |
| Outline lumpiness | ±0.38 mm (p05–p95) comes from the tape stack alone. Do not add noise on top | [S1] | MEASURED |
| **Tape width** | **10.0 mm**, constant on every band | Reference 8.3–12.1 mm at 70 mm; 10 mm cotton plain tape is a stock width [21]; sanada-himo 3-bu is about 9 mm and 4-bu about 12 mm [20] | DERIVED from MEASURED + SOURCED |
| **Tape thickness** | **0.50 mm** per layer | Cotton plain tape "about 0.5 mm" [21], tubular tape 2 mm [22]; reference limb steps median 0.26, p75 0.41, max 0.78 mm [S1]; kunai 0.5 mm [S3] | SOURCED; the reference agrees |
| Visible stack | Only the **top three layers** carry height: +0, +0.5, +1.0, +1.5 mm over the base. Everything deeper is the base spheroid | Outline max +1.43 mm at the pole; high-pass ±0.38 mm | DERIVED |
| Band paths | **Great circles**, each within **≤ 4°** of one | A flat tape follows a geodesic [26][27]. A small circle β off a great circle strains the edges ±w·tanβ/2r: 1.0 % at 4°, 2.5 % at 10° [S1] | DERIVED |
| Edge ease | A great-circle band's edges are **1.03 % shorter** than its centreline; they stay slightly slack, which reads as the soft rolled edge | cos(w/2r) at r 34.75 mm [S1] | DERIVED |
| Drape ramp | Where a band crosses the edge of the band beneath, it ramps 0.5 mm over **2.0 mm** (4 t) across that edge | Tensioned tape bridging a step | ESTIMATE; check against the reference-view render |
| Selvedge bead | Wall lip rounded to r 0.20 mm, plus a +0.06 mm bead over the outer 0.5 mm of each edge (height map, baked) | Reference bead 0.45–0.6 mm wide | ESTIMATE from MEASURED |
| Fray | Weft loops 0.2–0.6 mm along each exposed edge, in BC and N, lying on the tape below. Loose threads only where the reference has them (REFERENCE_SPEC.md count) | Reference, by eye | MEASURED intent, ESTIMATE size |
| Weave | Warp ribs along the tape, 0.30–0.37 mm, **irregular streaks**. Cross-threads 0.79 mm, lighter, periodic with wander. Slubs 1.3–2.0 mm | [S1] | MEASURED |
| Mean layers / tape length | **4 layers**, 27 passes, **5.8 m**. A random-pass model leaves 1.3 % uncovered; a real yarn-ball winding covers fully | Coverage 1 − (1 − w/D)ⁿ [S1] | DERIVED |
| Hidden interior | 64 mm washi shell 1 mm thick, dry powder fill. **Not modelled** | torinoko construction [1][2] | ESTIMATE |
| **Mass** | **121 g** (98–139 g) | Tape 14.5 g (250 g/m² [25], 5.8 m), shell 10.6 g (0.8 g/cm³), fill 96.1 g (137 cm³ at 0.70 g/cm³; ash 0.56–0.72, flour 0.48–0.56, powder 0.80 [24]) | DERIVED from ESTIMATE densities |
| Overall density | 0.675 g/cm³; a baseball is 0.64–0.73 [12] | [S1] | DERIVED |
| Bounds radius | **~36.4 mm**: maximum vertex distance from the AABB centre, the pole stack. The build measures it | Unreal uses the maximum vertex distance: the kunai's 140.008 mm, not its 141.5 mm half-diagonal [S3] | DERIVED |
| AABB | About 70–73 mm per axis | n/a | DERIVED |

**Cross-check.** At 70 mm and 121 g, the ball sits between a tennis ball (67 mm, 58 g) and a baseball (74 mm, 145 g). It is a third the mass of an M67 at about its size (64 mm, 400 g). That is right for a thrown prop of paper, powder and cloth.

---

## 5. Cloth tape: realistic width, thickness, weave and layers

| Tape | Width | Thickness | Weave | Source | Status |
|---|---|---|---|---|---|
| Japanese cotton plain tape (綿平テープ) | 10, 15, 20, 25, 30 mm | **about 0.5 mm** | Plain weave, 100 % cotton | [21] | SOURCED |
| Cotton-blend tubular tape (袋とじ織) | 20–50 mm | about 2 mm | Tubular | [22] | SOURCED |
| 真田紐 sanada-himo | 12, 18, 24 … 60 mm; 2-bu ≈ 6, 3-bu ≈ 9, 4-bu ≈ 12 mm | Denser than plain cloth; tubular grades are thicker | Flat narrow woven tape on a loom; cotton or silk; resists stretch. The 12 mm size is sold for wrapping calves | [18][19][20] | SOURCED / SNIPPET for the bu widths |
| Archival cotton tapes | 1/4 to 2 in | "thin" (no figure) | Loose, tight, twill | [23] | SOURCED form |

**Choice: 10 mm × 0.5 mm plain-woven cotton, dyed dark brown-black.** It is the reference's proportion, a stock width, and the kunai's tape. Sanada-himo, the cotton tape woven narrow on a loom, is the period-correct Japanese name for it and good listing vocabulary. The reference's weave (27–33 warp ends/cm, 0.8 mm cross-threads, slubs) is an open, slubby plain weave, looser than a dense sanada-himo. Match the reference, not the product.

**Layers.** Four layers mean over a 66 mm core, as above. Only the top one to three layers are ever seen. At the pole, three stack visibly, which is the +1.43 mm peak.

**Why great circles.** A straight flat tape has no in-plane curvature. Laid flat on a surface without stretching its edges, its centreline is a geodesic. On a sphere the geodesics are the great circles [26][27]. A small-circle band would have to stretch one edge and bunch the other: 1 % strain at 4° from a great circle, 5 % at 20° [S1]. Woven cotton would pucker. The reference shows no puckers, so every band is a great circle.

---

## 6. Geometry plan

### 6.1 Construction: an ordered list of great-circle bands

The model **is** a list, and the list is what gets fitted to the reference.

1. **Each band** i is a unit normal nᵢ (its great circle), the width 10 mm, and a winding rank kᵢ. Later means on top. Optionally a tilt of up to 4° off the great circle.
2. **Fitting.** Seen from -Y, a great circle projects to an ellipse centred on the disc centre, with semi-major axis R. Its minor axis is R·|nᵢ·ŷ| and lies along the image projection of nᵢ. Which half of the ellipse is visible decides the sign of nᵢ·ŷ. So each band's centreline, traced in REFERENCE_SPEC.md, gives nᵢ by a two-parameter fit. **Report the residual per band.** A band that will not fit a great circle within 4° is a finding, not something to force.
3. **Order.** A single winding order puts band i above band j at **both** of their antipodal crossings. The reference's over/under pairs must therefore form an acyclic order. If REFERENCE_SPEC.md finds a cycle (A over B over C over A), that is weaving, not winding: stop and ask.
4. **The back.** Every great circle has exactly half its length in the front hemisphere, so every band's back half is fixed by its front half. Crossings on the back follow the same order. The one free input is bands that are wholly buried on the front but surface on the back. Add none unless coverage demands it, and show the user a back view before texturing (question 8).
5. **Poles.** Each winding group shares a near-common axis, and its turns cross near the two ends of that axis. The top swirl is one such pole; its antipode is on the back, on the lower limb, where no invention is needed.

### 6.2 The surface: one closed height-field shell

The mesh is **not** a pile of ribbons: stacked ribbons waste their hidden faces, z-fight and are never watertight. It is **one closed surface**:
- **Radius.** Base spheroid + 0.5 mm × (number of the top three layers present at that point).
- **Walls.** An explicit wall wherever an exposed tape edge lies on the tape beneath: 0.5 mm tall, lip rounded to r 0.2 mm.
- **Ramps.** A 2 mm ramp wherever a band crosses a buried edge.

Every **exposed piece** of every band is a polygon in that band's own chart: u = arc length along its great circle, v = offset across it, −5 to +5 mm. Pieces are cut by the edges of later bands (2-D polygon clipping in the chart), triangulated by CDT (the kunai's plateau method), and mapped to the sphere analytically. Vertices come from the pack's **1 nm position-keyed vertex factory**, never `bmesh.ops.bevel` [S3][S6]. Per-vertex attributes: `band_id`, `band_u_mm`, `band_v_mm`, `layer`, `dist_to_edge_mm`. The bake-source material reads them (section 7).

**Chordal error.** The sagitta of a segment on R 35 mm:

| Segment | Sagitta | At the reference view |
|---|---|---|
| 3.5 mm | 0.044 mm | 0.58 px |
| 4.5 mm | 0.072 mm | 0.96 px |
| 8 mm | 0.23 mm | 3.0 px |
| 14 mm | 0.70 mm | 9.3 px |

So LOD0 uses **3.5 to 4.0 mm** along bands and edges (63 to 55 segments round the ball) [S1].

### 6.3 LODs

The screen sizes are the pack rule: 1.0 / 0.10 / 0.035, scaled by the bounds radius over 50 mm [S5]. At 36.4 mm that is **1.0 / 0.0728 / 0.0255**, switching at the pack's **0.889 m / 2.54 m** (90° hFOV, 16:9). At 1080p the ball is **76 px** across at the first switch and **27 px** at the second. One tape step is 0.54 px and 0.19 px there [S1]. In first person, 0.35 to 0.6 m away, the ball is 112 to 192 px across, on LOD0.

| LOD | Screen size | Triangles | Contents |
|---|---|---|---|
| LOD0 | 1.0 | **4,000–6,500**, target about 5,000 | 3.5–4.0 mm segments; walls with a lip row on every exposed edge; 2 mm drape ramps; out-of-round spheroid; pole stacks; loose-thread strands only if question 2 says geometry (≤ 300 tris) |
| LOD1 | ~0.073 | **1,200–2,000** | 8–10 mm segments. **Walls removed:** each step becomes a slope, boundary vertices at mid-height (0.25 mm error, 0.27 px). Ramps dropped. Strands dropped. Every piece boundary kept as a UV seam. Spheroid and pole stacks kept (the pole's 1.4 mm is 1.5 px) |
| LOD2 | ~0.0255 | **400–800** | 14–16 mm segments. Pieces under 20 mm² (about 3 px² at the switch) merge into the band covering them, keeping that band's UVs. The remaining boundaries stay seams. The spheroid can go (1.9 % is 0.5 px) |

**Budget.** The estimate for LOD0 is 2,900 tris of surface at 3.5 mm, 1,950 of walls and 490 of ramps: **5,330**. At 4.0 mm it is **4,350** [S1]. The 1,700 mm of exposed edge is an ESTIMATE (about 850 mm on the front, doubled); the built piece set fixes it. LOD1 and LOD2 are dominated by the piece count: a few triangles per exposed piece, times 100 to 200 pieces.

**Context.**
- `ASSET_GUIDELINES.md` sets a prop at 1,000–5,000 tris and a hero weapon at 20–50k [S6].
- The kunai shipped 2,182 / 696 / 366 after its wrap became geometry [S3].
- Game-scale yarn balls on Sketchfab run 320 to 12,044 faces; scanned or strand-modelled ones run 27k to 1M [38]. A low-poly smoke bomb there is 300 faces [39].

LOD0 may pass 5,000 (question 4). The lever is the along-edge segment length.

**Faithful at every LOD.** Every LOD keeps the same bands, the same order and the same UV map (the analytic chart). LOD1 and LOD2 lose relief, not layout. Report the two-sided Hausdorff distance, not the one-sided one: LODn to LOD0 is zero by construction for a vertex subset (paper bomb, study 13) [S4].

---

## 7. Texture plan

| Map | Size | Colourspace | Contents |
|---|---|---|---|
| `T_SmokeBomb_BC` | 2048² | sRGB | Dyed cotton, cross-threads, fibre flecks, the selvedge's lighter crossing threads, fray loops |
| `T_SmokeBomb_ORM` | 2048² | linear | R = AO baked from LOD0 (the crevice at every step, the pole stack, the drape shadows). G = roughness. B = 0 |
| `T_SmokeBomb_N` | 2048² | linear, normal | Weave, rib streaks, slubs, selvedge bead, fray. **DirectX green** |

No `_M`. The material is opaque, as the paper bomb's is; the reason is in `paper_material.py` [S4]. No colour variant: the reference shows one dye.

**Texel density.**
- The surface is 15,394 mm². Walls add about 850 mm² (1,700 mm × 0.5 mm).
- At 2048 with 75 % packing: **13.9 px/mm = 139 px/cm**. That is inside the pack's 134–170 px/cm [S3], and just above the reference framing's **13.26 px/mm**, so a reference-view render is never magnified.
- At 70 % packing: 134 px/cm.
- At 4096: 278 px/cm (question 3).
- At 139 px/cm: the ribs are **4.2–5.2 texels** and the cross-threads **10.9 texels** [S1].

**UV0: the analytic band chart, packed.** This follows the kunai's analytic UVs on every LOD [S3].
- **Islands.** Each exposed piece is an island at its chart coordinates, with **u along the tape**. The warp and weft then lie on the texel axes, which is what keeps a fine weave from aliasing. Cardinal rotation only; no mirroring.
- **Packing.** Pieces go in rows 10 mm high plus 16 px of padding [S6]. Target ≥ 75 % packing.
- **Walls.** Each wall is **unfolded onto its piece's island**, as the kunai's knife lands were. As their own islands, 0.5 mm walls become sub-texel lightmap charts, which Unreal's UV1 packer lays across other charts. That was kunai defect 4 [S3].
- **Seams.** They fall on tape edges and walls: real discontinuities, where the guidelines want hard edges [S6].

**Bake source.** `M_SmokeBomb_Source` is procedural, in object space, driven by the band attributes, and baked into the three maps. The gallery renders only from the baked maps [S3][S4]. Because the source knows the distance to the nearest upper edge at every point, fray loops can lie across the edge onto the tape below, which is a different island, with no seam.

**What to copy from the kunai's `M_Kunai_Wrap` [S2][S3], and what not to:**

| Kunai feature | Smoke bomb |
|---|---|
| Overlap as geometry; the material carries only what geometry cannot | **Copy** |
| Irregular weave: two thread families that wander, with slubs (`WEAVE_WANDER`, `SLUB`) | **Copy**, re-tuned to the reference: ribs 0.30–0.37 mm as non-periodic streaks, cross-threads 0.79 mm, slubs 1.3–2.0 mm |
| Fibre fuzz (`FUZZ`), lifted fibre flecks | **Copy**, calibrated to the reference's p95/p99 light threads |
| Fray along every exposed edge | **Copy** as weft loops on a selvedge, not raw cut fibres |
| Cloth sheen in the preview material (`SHEEN`) | **Copy**. The reference's rim is 1.57 × brighter than its centre |
| Hand grime, faded patches, burnished crowns, a dirt line at the foot of each step, darker fibrous cut ends | **Do not copy.** The reference shows none (rule 1). The step's dark foot is AO from geometry, not paint |
| Natural (undyed) BC variant, lettering band | **Do not copy** |

**Colour and roughness (ESTIMATE, then calibrated).**
- **BC base.** Linear **(0.046, 0.039, 0.037)**, luma 0.040, hue 1 : 0.85 : 0.80 as MEASURED. Stored that is sRGB (60, 56, 54). That sits beside the kunai's shipped dark tape (0.042, 0.039, 0.036). It is at the bottom of the 60–240 sRGB non-metal band and well above its "never below 30–50 sRGB" floor [S4].
- **BC flecks and cross-threads.** Up to linear 0.10–0.12.
- **Roughness.** 0.85–0.92. Metallic 0.
- **Calibration.** Render the reference view (section 10) and match the cloth's stored luma **p05 / p50 / p95 = 0.036 / 0.111 / 0.302**. Move the albedo, the fleck density and the sheen, and never the lights, to get there.

**Never** sample, project or trace reference pixels into any map (section 11).

---

## 8. Collision, physics, sockets, pivot

**Collision: one convex hull, confirmed.** The ball is convex apart from sub-millimetre steps, so one hull is right. The kunai needed two only because of its blade.
- **Name.** `UCX_SM_SmokeBomb_LOD0_00`. It must be keyed to the render node name after `make_lod_group`, or it imports with no collision [S6][33].
- **Why not the pipeline helper.** `pipeline.helpers.make_ucx_hull` decimates the mesh's own hull to ≤ 32 vertices [S7]. On a sphere that gives an *inscribed* hull that cuts through the tape, and it would fail the "LOD0 0.0 cm outside the hull" round-trip gate [S6].
- **Author a circumscribed hull**, as the kunai (supporting lines) and the paper bomb (containing prism) did [S3][S4].

| Hull (faces tangent to r_max = 36.0 mm) | Vertices | Vertex radius | Volume / sphere(r_max) | Volume / 70 mm ball |
|---|---|---|---|---|
| Icosahedron | 12 | 45.3 mm | 1.207 | 1.314 |
| **Pentakis dodecahedron (all 60 faces tangent)** | **32** | 38.3–39.3 mm | **1.064** | **1.158** |
| Geodesic, frequency 2 | 42 (over the cap) | 38.5 mm | 1.072 | 1.166 |

The build scales the hull to the built mesh's measured maximum radius. **32 vertices** stays inside the project's hull cap (`props_lib/geometry.py` treats 32 as Unreal's ceiling [S7]; a secondary source agrees [37]). A USP_ sphere primitive would roll perfectly, but `qa_check` requires a UCX_ child [S7] and USP_ is not engine-verified in this project. Treat it as an optional in-editor addition, not a shipped helper.

**Physics.**
- **Mass in KG 0.12.** The range is 0.098–0.139 [31].
- **Centre-of-mass offset.** Expect 0, because the hull is centred on the pivot. Check it in-engine.
- **Tunnelling.** A one-hand throw is about 18.5 m/s: √(g · 35 m), from the M67's 35 m [11]. At 60 Hz that is 0.31 m per step, 4.4 ball diameters. Turn on **Use CCD** [31], or keep ProjectileMovement's `sweep_collision` and lower `max_simulation_time_step` [32].
- **Bounce.** A cloth-covered powder ball barely bounces: bounciness 0.1–0.2, friction 0.6–0.8 (ESTIMATE) [32]. Angular damping stops the 60-facet hull tumbling on.

**Sockets.** These are Empties via `pipeline.make_socket`, restored after import from `.sockets.json`. That works around the FBX socket scale-100 bug and the rule that a LodGroup file drops sockets [S6]. Names follow the kunai: `SOCKET_SM_SmokeBomb_LOD0_<Name>`.

| Socket | Position | Axes | Use |
|---|---|---|---|
| `Grip` | (0, 0, 0), the ball centre | Build frame: reference face toward -Y, +Z up | The hand socket places the ball's centre in the palm. The rotation decides which face the player sees |
| `Burst` | (0, 0, 0) | +Z up | Spawn point for the smoke system. Spawn it with **absolute (world) rotation**, so smoke rises whichever way the ball lands |

No `Fuse`, `Tip` or `Impact` socket. The reference has no fuse, and impact is the whole surface.

**Pivot.** The ball centre. For a symmetric ball the mass-weighted centre equals the geometric centre to about 0.1 mm, so the kunai's warning about Origin to Center of Mass (Volume) does not bite here. Still set the origin explicitly, not with that operator.

---

## 9. The Unreal side

1. **Import.** FBX from `Scripts/pipeline/export_fbx.py`; `qa_check` clean with `--budget` set to the agreed LOD0 ceiling (question 4). **Import Mesh LODs ON.** A LodGroup carries no thresholds, so apply the screen sizes after import from the sidecar, **computed from Unreal's own measured bounds radius**. Generate Lightmap UVs ON, and gate UV1 at 0 overlapping pixels at 1024 and 2048 on every LOD, as the kunai does [S3]. Nanite off: a hand-LODded prop of about 5k tris.
2. **Collision.** Exactly 1 convex element. It round-trips within 1e-6 cm and contains LOD0 at 0.0 cm.
3. **Sockets.** Two, at scale 1, restored from the sidecar by `Scripts/pipeline/ue_import_sockets.py`.
4. **Textures**, through the props importer (`props_lib/ue_import_textures.py`, which raises on an unrecognised suffix):
   - BC: sRGB.
   - ORM: linear.
   - N: normal map, DirectX green.
   - All three: **MipGenSettings = TMGS_FROM_TEXTURE_GROUP**, set and verified. All three are 2048², but the gate exists because a non-power-of-two PNG silently imports with NoMipmaps, and that has bitten this project twice [S3][34].
5. **Material.** UE 5.8 enables **Substrate by default in new projects**; legacy shading models are converted at compile time [29]. Both routes carry cloth fuzz:
   - **Substrate:** a Slab with **Fuzz Amount / Fuzz Roughness / Fuzz Color** [29]. For cotton, use higher fuzz roughness and a lower fuzz amount (tutorial summary [30]). Start at amount 0.3–0.5, roughness 0.6–0.8.
   - **Legacy:** the **Cloth** shading model with **Fuzz Color** and **Cloth** inputs [28], for a project that has not opted into Substrate.

   Calibrate either route against the reference's 1.57 × rim. The pack still has no Unreal master materials (a known kunai gap [S3]). The validation import binds WorldGridMaterial, and the material is specified here, not verified.
6. **Verification.** In a **second, fresh process** on the exact exported bytes, bound by SHA-256:
   - Project: `WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject`, new content path `/Game/PropsCheck/SmokeBomb`.
   - One commandlet at a time, never left running.
   - `MSYS_NO_PATHCONV=1` or PowerShell for `/Game` paths. Never DemoGame_1.
   - Pass 1 imports with `save=False` and lets `apply_sidecar` do the only save; the kunai's triple save raced the changelist scan [S3].

---

## 10. Fidelity method: judge by looking, confirm by measuring

This is the paper bomb's bar: "accurate to the reference to the T". It has three rules. **Invent nothing.** **A passing number with a different look is a failure.** **Measure what a viewer sees.**

**The reference-view render** is a render of the **shipped LOD0 with the shipped baked maps** through the preview material (the sheen preview included, labelled as such):
- Orthographic camera on -Y looking +Y, ortho scale **94.61 mm**, **1254 × 1254 px**.
- Ball centre at pixel **(627.3, 629.1)**, so the ball is 13.255 px/mm, 928 px across.
- **Pure white background, no ground, no shadow**.
- Key from the top / upper-right, and fill such that the bottom sector renders about 0.54 × the top (section 3). A lighting tweak may only chase the *lighting* statistics, never the cloth's.

**Order of judgement:**
1. **Side-by-side and 50 % flicker against `smokebomb.png`, by eye, before any number.** Every band must be where the reference has it, the same width, crossing in the same order.
2. **Then measure, on that render, the same statistics as section 3 and REFERENCE_SPEC.md:**
   - Outline r(θ) and its ellipse ratio and tilt.
   - The count and size of limb steps.
   - Each band's edges and centreline against the reference's.
   - Over/under at every crossing.
   - Cloth luma p05 / p50 / p95 and the sector gradient.
   - Weave FFT peaks: rib, cross-thread, slub.
   - Fleck fraction.
   - The count and position of loose threads.
3. **Measure the render, never the source material, a map layer or the builder's report.**

**Also render in the pack's gallery rig**, the hero 3/4 on the pack's ground from `props_lib.render`, so the smoke bomb sits in the product line. A white-background fidelity shot is not a Fab thumbnail.

---

## 11. IP, provenance and the Fab AI flag

**Form.** A ball wrapped in cloth tape is generic: temari, yarn balls, wound balls [12][16][17]. So is a smoke ball as a ninja tool [1][2]. Nothing in the reference is franchise-specific. The names `SmokeBomb`, `smoke ball`, `torinoko` and `sanada-himo` are generic. Apply the props deny gate (`naruto`, `konoha`, `shippuden`, …) to every emitted name as usual [S4].

**The reference is AI-generated.** Its C2PA manifest says so: gpt-image, `trainedAlgorithmicMedia` (section 3). This is the situation the paper bomb study resolved before the user took ownership of that design [S4]:
- **Safe route (recommended default).** No pixel of `smokebomb.png` reaches any shipped map, and the build script does not open it. What is taken from it is scalar measurement plus fitted band parameters: proportions, band normals and widths, crossing order, colour statistics. The geometry is our generator's, and the maps are our procedural bake. Under Epic's published wording ("Created with AI" is for content generated with AI for distribution [35][36]), that reads as nothing to declare. This is our reading, not legal advice, and Epic publishes no threshold for AI used earlier in a workflow [35].
- **The paper bomb precedent went the other way at the user's word** ("i wrote it … match it exactly"), and tracing became the method there [S4]. **Do not assume that carries over.** For the smoke bomb, the manifest names ChatGPT as the creator. Ask the user (question 5). Until they answer, keep the safe route. The fidelity bar is met by fitting geometry and calibrating the procedural material, which needs no reference pixels in a shipped file.

---

## 12. Open questions for the user

1. **Scale.** Is 70 mm right, between a tennis ball and a baseball, about 120 g? Everything else scales with it.
2. **Loose threads past the silhouette.** Model them as thin geometry strands at LOD0 (≤ 300 tris, dropped at LOD1), or keep them in texture only (opaque, cheaper, but they cannot cross the outline)? Recommendation: geometry, only the ones the reference has.
3. **2048 or 4096?** 2048 is the guideline and meets the reference framing at 13.9 px/mm, but the ribs are 4–5 texels. 4096 draws them cleanly (9–10 texels). Decide after the first reference-view comparison.
4. **LOD0 budget.** Up to 6,500 tris, above the guideline's 5,000 for a prop, if the built edge length needs it?
5. **AI provenance.** Keep "measure only, no reference pixels shipped" (no Fab AI flag), or does the user claim this design as with the paper bomb?
6. **Gameplay.** Confirm the burst is triggered on impact (no fuse), with a single `Burst` socket at the centre.
7. **Collision.** Is the 32-vertex hull, which tumbles to a stop, acceptable, or add an in-editor sphere for rolling?
8. **The back.** Approve a back view of the fitted winding before texturing. It is determined by the front, but it is the one view nobody has seen.

---

## 13. Verification of high-stakes claims

Checked 2026-09-21 by WebFetch, WebSearch and local measurement. Nothing was downloaded. The reference PNG was read only by the `sbstudy_*` scripts, which write numbers and scratch viewing aids.

| Claim | Status | Checked against |
|---|---|---|
| Reference is gpt-image output, C2PA `trainedAlgorithmicMedia`, created 2026-09-19 | **Verified** | The `caBX` chunk strings [S1] |
| Reference is byte-identical to `Downloads/smokebomb.png` | **Verified** | SHA-256 `813105ec…7b6e1c2` for both |
| Torinoko: layered torinoko washi, egg-shaped, filled with saltpetre and a smoke agent, fuse | **Verified, two sources** | [1][2]; [3] lists it among the Bansenshukai fire weapons. No dimension found anywhere |
| Egg metsubushi thrown as a grenade | **Verified as quoted** | [1] (卵目潰し); [4] mentions eggs, but that line is uncited |
| Toribikata is a tube, not a ball | **Verified** | [5] |
| Tetsuhau 13 cm | **Verified** | [7] |
| Hōroku-dama 15 cm, 2 kg replica | **SNIPPET** | [8]; [9] gives no size |
| Blendkörper 64 mm / 370 g; M67 64 mm / 400 g / 35 m; baseball 73–75 mm / 142–149 g; tennis 65.4–68.6 mm / 56–59.4 g | **Verified** | [10][11][12][13] |
| Cotton plain tape about 0.5 mm; tubular 2 mm; stock widths 10–30 mm | **Verified** | [21][22] |
| Sanada-himo: narrow loom-woven cotton or silk tape; 12–60 mm sold; 12 mm for wrapping calves | **Verified** | [18][19]. The 2/3/4-bu mm figures are SNIPPET [20] |
| Great circles are the sphere's geodesics; geodesics have zero geodesic curvature | **Verified** | [26][27]. The flat-tape consequence and the strain table are DERIVED [S1] |
| Bulk densities: ash 561–721, flour 480–560, charcoal 240–480, gunpowder 801 kg/m³ | **Verified** | [24], converted from lb/ft³ |
| UE 5.8: Substrate on by default for new projects; Slab fuzz inputs; Cloth model has Fuzz Color | **Verified** | [28][29] |
| Use CCD, Mass in KG, COM offset, damping; ProjectileMovement bounciness / friction / sweep | **Verified** | [31][32] |
| Unreal bounds radius = maximum vertex distance, not the AABB half-diagonal | **Verified on project data** | The kunai measured 140.008 mm against a 141.5 mm half-diagonal [S3] |
| Imported convex hull cap of 32 vertices | **Project convention, weak external support** | `props_lib/geometry.py` [S7]; [37] is secondary. The 32-vertex hull avoids the question |
| Reference scale, outline, steps, weave, colour, lighting | **Measured** | [S1], at 70 mm |
| Band width 8.3–12.1 mm | **Coarse** | Read from profiles and gridded views. REFERENCE_SPEC.md supersedes it |

**Frozen assets, checked at the end of this pass** (this pass wrote only `References/SmokeBomb/SMOKEBOMB_STUDY.md` and `WorkFiles/smokebomb/study_calc/`):
- **Shuriken pack:** `sha256sum` over `Exports/Shuriken/*.fbx *.sockets.json` gives exactly the 14 hashes recorded in `PAPERBOMB_STUDY.md` section 12. Kunai `ebb6612b…`, eight-point `ced33071…`, four-point `fc16a0fa…`, hooked cross `bd42e4da…`, six-point `e711279e…`, spike `892a0ba3…`, square plate `066f33f3…`; sidecars `589bc324…`, `65d769aa…`, `1f838d0b…`, `a643a2fe…`, `b4b89bd0…`, `9f2e9728…`, `5f54797c…`. **Unchanged.**
- **Paper bomb:** `sha256sum -c WorkFiles/paperbomb/paused_2026-09-21/SHA256SUMS_exports.txt` returns **OK for all 6** (FBX, sidecar, BC, ORM, N, M). **Unchanged.**

---

## 14. Sources

**Read 2026-09-21** means the page was fetched in this pass and the figure quoted from it. **SNIPPET** means seen only in a search summary. **Via** means taken from an earlier project study's verified reading. Nothing was downloaded.

### Smoke, blinding and fire balls

| # | Source | URL | Used for |
|---|---|---|---|
| 1 | Wikipedia (JA), 忍具 | https://ja.wikipedia.org/wiki/忍具 | **Read.** 鳥の子: 焔硝と発煙剤を鳥の子和紙で何重にも包み、卵型に固めた手投げ弾. 卵目潰し: an eggshell of powder thrown at the face |
| 2 | Touken World, 火器 | https://www.touken-world.jp/tips/51520/ | **Read.** 鳥の子 = a round container of layered torinoko washi, filled with powder, 火縄 fuse; bang and smoke to cover escape |
| 3 | Mie University, Iga ninja lecture 2015 (荒木利芳), 忍者と火術・火器 | https://www.human.mie-u.ac.jp/kenkyu/ken-prj/iga/kouza/2015/2015-11.html | **Read.** Bansenshukai fire weapons, including 鳥の子 (smoke ball); fire weapons as fundamental to ninjutsu; no dimensions |
| 4 | Wikipedia (EN), Metsubushi | https://en.wikipedia.org/wiki/Metsubushi | **Read.** Hollowed eggs, bamboo tubes, small containers; ash, pepper, mud, flour, dirt. The egg line is uncited |
| 5 | Critical Ninja Theory (Rob Tuck), "Lethal Ninja Combat Firework of DEATH" | https://criticalninjatheory.substack.com/p/lethal-ninja-combat-firework-of-death | **Read.** Toribikata = copper tube on a handle; Bansenshukai 1676; Araki's 2018 test: sparks 3 m, reddish smoke, about 20 s |
| 6 | Wikipedia (EN), Bansenshūkai | https://en.wikipedia.org/wiki/Bansensh%C5%ABkai | Via `KUNAI_STUDY.md` [4]. 1676 compilation |
| 7 | Nippon.com, "The Battle of Bun'ei" | https://www.nippon.com/en/japan-topics/c13702/the-battle-of-bun%E2%80%99ei-the-first-mongol-invasion-of-japan.html | **Read.** Tetsuhau from the 1281 Takashima wreck: hollow ceramic sphere, 13 cm; Kyushu University CT |
| 8 | Yahoo! Chiebukuro, 焙烙玉の威力 | https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/q11267097006 | **SNIPPET.** Museum replica about 15 cm, 2 kg; no originals found |
| 9 | Wikipedia (JA), 焙烙火矢 | https://ja.wikipedia.org/wiki/焙烙火矢 | **Read.** Earthenware, gunpowder, fuse; thrown or swung on a rope; no size; flagged as poorly sourced |
| 10 | Wikipedia (EN), Blendkörper 1H | https://en.wikipedia.org/wiki/Blendk%C3%B6rper_1H | **Read.** 64 mm × 150 mm, 370 g glass smoke bulb (cites the 1944 Lone Sentry bulletin) |
| 11 | Wikipedia (EN), M67 grenade | https://en.wikipedia.org/wiki/M67_grenade | **Read.** 64 mm, 400 g, thrown 35 m by an average soldier |
| 12 | Wikipedia (EN), Baseball (ball) | https://en.wikipedia.org/wiki/Baseball_(ball) | **Read.** 73–75 mm, 142–149 g; rubber or cork centre wrapped in yarn |
| 13 | Wikipedia (EN), Tennis ball | https://en.wikipedia.org/wiki/Tennis_ball | **Read.** ITF 6.54–6.86 cm, 56.0–59.4 g |
| 14 | Hen's egg dimensions: Joubrane et al. 2019 (ResearchGate table); "Novel approaches in mathematical description of hen egg geometry" (T&F) | https://www.researchgate.net/figure/Internal-and-external-dimensions-of-white-and-brown-eggs_tbl1_336785082 ; https://www.tandfonline.com/doi/pdf/10.1080/10942912.2011.595028 | **SNIPPET.** 55.8–61.2 × 43.3–45.2 mm |
| 15 | Phantom Fireworks, "Smoke Balls" | https://fireworks.com/safety/fireworks-university/smoke-balls | **Read.** Coloured ball, fuse at the top, smoke of the same colour. Smoke time 10–15 s is SNIPPET |
| 16 | Wikipedia (EN), Temari (toy) | https://en.wikipedia.org/wiki/Temari_(toy) | **Read.** Wadded silk core wrapped with strips of fabric |
| 17 | Wikipedia (JA), 手毬 | https://ja.wikipedia.org/wiki/手毬 | **Read.** A core wound with ぜんまい綿 and thread; between a softball and a handball in size |

### Cloth tape

| # | Source | URL | Used for |
|---|---|---|---|
| 18 | Wikipedia (JA), 真田紐 | https://ja.wikipedia.org/wiki/真田紐 | **Read.** Flat, narrow warp-and-weft fabric woven on a loom; cotton or silk; dense, resists stretch; peddler and shinobi lore (unverified folklore) |
| 19 | Asakusa Hantenya, 真田紐 | https://www.hantenya.com/shopdetail/000000001076/ | **Read.** 12, 18, 24, 30, 36, 48, 60 mm; cotton 100 %; 12 mm for wrapping calves |
| 20 | Search summary, 真田紐 widths | (query "真田紐 幅 厚さ mm 規格 木綿 平織"; e.g. https://itokumihimoten.com/?mode=cate&csid=0&cbid=160317) | **SNIPPET.** 2-bu ≈ 6 mm, 3-bu ≈ 9 mm, 4-bu ≈ 12 mm; 袋織 thicker than single |
| 21 | Tape Senmonten 102 (Yahoo! Shopping), 綿平テープ | https://store.shopping.yahoo.co.jp/toji102tape/cotton-hira.html | **Read.** 10/15/20/25/30 mm, **about 0.5 mm thick**, cotton plain weave, 50 m roll |
| 22 | Narukawa Shoten, 綿平テープ(混紡) | https://www.narukawa-co.com/item/5411/ | **Read.** Plain and 袋とじ weave, about 2 mm thick, 20–50 mm |
| 23 | TALAS, cotton tapes | https://www.talasonline.com/Cotton-Tape | **Read.** Loose, tight and twill weaves, 1/4 to 2 in; no thickness figures |
| 24 | Engineering ToolBox, densities of materials | https://www.engineeringtoolbox.com/density-materials-d_1652.html | **Read.** Coal ash dry 35–45, flour 30–35, charcoal 15–30, gunpowder 50, sand 80–100 lb/ft³ |
| 25 | ScienceDirect Topics, fabric weight | https://www.sciencedirect.com/topics/engineering/fabric-weight | **SNIPPET.** Medium fabrics 150–350 g/m²; cotton fibre about 1.52 g/cm³ (tape at 250 g/m² is inside it) |

### Geometry

| # | Source | URL | Used for |
|---|---|---|---|
| 26 | Wikipedia (EN), Geodesic curvature | https://en.wikipedia.org/wiki/Geodesic_curvature | **Read.** Geodesics have zero geodesic curvature; small-circle formula |
| 27 | Wikipedia (EN), Great circle | https://en.wikipedia.org/wiki/Great_circle | **Read.** Arcs of great circles are geodesics; a great circle halves the sphere; it passes through antipodes |

### Unreal, Fab and asset references

| # | Source | URL | Used for |
|---|---|---|---|
| 28 | Epic, Shading Models (UE 5.8) | https://dev.epicgames.com/documentation/en-us/unreal-engine/shading-models-in-unreal-engine | **Read.** Cloth model: a thin fuzz layer; inputs include Fuzz Color and Cloth |
| 29 | Epic, Overview of Substrate Materials (UE 5.8) | https://dev.epicgames.com/documentation/en-us/unreal-engine/overview-of-substrate-materials-in-unreal-engine | **Read.** On by default for new projects; legacy converted at compile time; Slab Fuzz Roughness / Amount / Color; platform support "incomplete" |
| 30 | daily.dev, summary of "Substrate Fuzz – Unreal Substrate – Episode 6" | https://daily.dev/posts/substrate-fuzz---unreal-substrate---episode-6-bktduupof | **SNIPPET.** Cotton = higher fuzz roughness, lower fuzz amount |
| 31 | Epic, Physics Bodies Reference | https://dev.epicgames.com/documentation/en-us/unreal-engine/physics-bodies-reference-for-unreal-engine | **Read.** Use CCD, Mass in KG, Center Of Mass Offset, Linear and Angular Damping, Phys Material Override |
| 32 | Epic Python API, ProjectileMovementComponent | https://dev.epicgames.com/documentation/en-us/unreal-engine/python-api/class/ProjectileMovementComponent?application_version=5.4 | **Read.** should_bounce, bounciness, friction, bounce stop threshold, max_simulation_time_step, sweep_collision |
| 33 | Epic, FBX Static Mesh Pipeline | https://dev.epicgames.com/documentation/unreal-engine/fbx-static-mesh-pipeline-in-unreal-engine | Via `PAPERBOMB_STUDY.md` [33]. `UCX_<render mesh>_##`, Import LODs |
| 34 | Epic, Texture Asset Editor | https://dev.epicgames.com/documentation/en-us/unreal-engine/texture-asset-editor-in-unreal-engine | Via `PAPERBOMB_STUDY.md` [34]. NPOT imports as NoMipmaps; measured twice by the kunai [S3] |
| 35 | Epic forum, "Update on products generated with AI" (2025-05-22) | https://forums.unrealengine.com/t/update-on-products-generated-with-ai/2523501 | Via `PAPERBOMB_STUDY.md` [38]. The "Created with AI" declaration is mandatory; no threshold published |
| 36 | Fab Support, NoAI meta tags and Created with AI | https://support.fab.com/s/article/Introducing-NoAI-meta-tags-and-Created-with-AI-self-declaration | Via `PAPERBOMB_STUDY.md` [39], SNIPPET. For publishers "who use AI to generate content for distribution" |
| 37 | StraySpark, "Blender Collision Meshes for Game Engines" | https://www.strayspark.studio/blog/blender-collision-meshes-game-engines-ucx | **SNIPPET.** Hull vertex limit "commonly capped around 32" |
| 38 | Sketchfab API search, "yarn ball" | https://api.sketchfab.com/v3/search?type=models&q=yarn%20ball&count=24 | **Read.** 96 to 1,059,284 faces; game-scale 320, 2,436, 4,080, 7,336, 12,044 |
| 39 | Sketchfab API search, "smoke bomb ninja" | https://api.sketchfab.com/v3/search?type=models&q=smoke%20bomb%20ninja&count=24 | **Read.** A low-poly smoke bomb at 300 faces |

### Project files

| # | File | Used for |
|---|---|---|
| S1 | `WorkFiles/smokebomb/study_calc/`: `sbstudy_chunks.py`, `sbstudy_measure_ref.py/.json`, `sbstudy_limb_steps.py/.json`, `sbstudy_profiles.py/.json`, `sbstudy_weave_fft.py/.json`, `sbstudy_light.py/.json`, `sbstudy_calc.py/.json`, `sbstudy_hull32.py`; viewing aids `sbstudy_grid_view.py`, `sbstudy_centre_view.py`, `sbstudy_clean_view.py` (scratch output only) | **Measured here.** Provenance, silhouette, ellipse, limb steps, band profiles, weave spectrum, colour, lighting, backdrop; all DERIVED arithmetic (scale, strain, coverage, mass, texel, LOD, chordal error, triangles, hulls) |
| S2 | `Scripts/shuriken/shuriken_lib/kunai_wrap.py` (read-only) | The 3.10.1 tape recipe: WEAVE 1.15 / 0.94 mm, WEAVE_WANDER, SLUB, FUZZ, CREST, FRAY, DARK (0.042, 0.039, 0.036), roughness 0.90, SHEEN 0.35 |
| S3 | `WorkFiles/kunai/KUNAI_PLAIN_REPORT.md`, `References/Kunai/KUNAI_STUDY.md` | The overlap-as-geometry fix (13.1), moiré at 5 texels, sheen / Cloth model, lightmap chart defect 4, NoMipmaps on NPOT (13.2), the triple-save race, analytic UVs per LOD, bounds 140.008 mm, pack texel band 134–170 px/cm, LOD 2,182 / 696 / 366 |
| S4 | `References/PaperBomb/PAPERBOMB_STUDY.md` (sections 7, 8, 10, 13), `Scripts/props/props_lib/paper_material.py` | The opaque-material decision, the AI-flag reasoning, the invented-damage lesson, two-sided Hausdorff, the props deny gate, the 30–50 / 60–240 sRGB bands |
| S5 | `Scripts/props/props_lib/spec.py`, `Scripts/shuriken/shuriken_lib/spec.py` | Pack LOD rule 1.0 / 0.10 / 0.035 × radius / 50 mm; switch distance d = R / (S · tan(v/2)) at 90° hFOV, 16:9 |
| S6 | `ASSET_GUIDELINES.md` | Prop 1–5k, hero weapon 20–50k tris; 2048 props / 4096 hero; padding 16 px at 2K; UCX / SOCKET literal naming; LodGroup drops sockets; Forward -Y / Up Z; the 1 nm vertex factory and bevel ban (via S3) |
| S7 | `Scripts/pipeline/helpers.py` (`make_ucx_hull`), `Scripts/pipeline/qa_check.py` (`ucx_present`), `Scripts/props/props_lib/geometry.py` | The helper decimates to ≤ 32 vertices, so its hull is inscribed; qa requires a UCX_ child; the project treats 32 as Unreal's hull ceiling |
