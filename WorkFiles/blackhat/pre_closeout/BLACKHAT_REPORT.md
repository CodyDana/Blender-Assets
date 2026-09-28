# SM_BlackHat: build report (surface pass)

**Date:** 2026-09-26. **Library:** props_lib blackhat **1.2.0**. **Build:** `Scripts/props/build_black_hat.py`, run
from scratch with no arguments (Blender 5.2.0 LTS, headless, `--factory-startup`, 91 s). It rebuilt
`Assets/BlackHat.blend`, `Exports/BlackHat/` and `Renders/BlackHat/`. Log: `WorkFiles/blackhat/build_surface_4.log`.
The previous (final-pass) state is kept in `WorkFiles/blackhat/pre_surface_pass/`.

## Status

- **Surface pass: done, ONE targeted pass** on the blind judge's surface and finish tells (section 0 below).
  No new blind round was run: that is the verifier's / your call.
- **Engineering (this build):**
  - **Build gates: 25 of 25 pass** (`WorkFiles/blackhat/blackhat_report.json`, `gates`), including the recolour
    (9b), mip parity (9c), roughness floors (9d), single hull (7b), frozen assets (10) and the fidelity gates F1-F8.
  - **qa_check: 76 of 76 pass.**
- **Unreal 5.8: NOT yet re-verified for these bytes.** Section 6 below is the final pass's run on the OLD bytes
  (`fa35264c...`). A verifier runs the Unreal check next; nothing here ran a commandlet.
- **Frozen assets unchanged:** shuriken **78 of 78** (and 78 of 78 against the snapshot's own copies), smoke bomb
  **30 of 30**, paper bomb **6 of 6** (`regression/post_black_hat/compare_black_hat.py`, run after the build; the
  build's own start / end check agrees: 41 / 29 / 6 lines of its lists).

**Bytes (this build):**
- FBX `d959d2f1ddfcd76cb9b88da90681aaf15aac79532c4dd7b52a1ca1d40b7cc4c3`
- sidecar `45eb5f38...0eae7ecf7`
- blend `5eb24d61...5c661eda`

---

## 0. Surface pass (2026-09-26)

**Brief.** The shape already read right; the blind judge picked our render in 20 of 20 pairs on SURFACE and FINISH
tells only. The user chose one targeted pass on six items, then move on whatever the result. It was iterated on
fast reference-view renders (`WorkFiles/blackhat/surface_pass/sp_dev.py`, iterations `d00`-`d33`, each with the
side-by-side, the 3x crops and region metrics against the reference), then rebuilt through `build_black_hat.py`.
Every render below is from the BAKED maps. Nothing reads the reference while painting; the zones and sizes are
REFERENCE_SPEC's numbers.

| # | Item | What changed (module) | Result on the reference view |
|---|---|---|---|
| 1 | **Wear** | `paint.paint_skin`, `wear_cover`, `scratches`. Pale grey rubbed-through strand tops (albedo 0.14-0.36: a streak is 0.6 mm of a 1.8 mm strand, under half a screen pixel across) in ragged fbm patches whose cover follows REFERENCE_SPEC 9's zones (left theta -72..-25, rho > 0.45 the heaviest, with a greyer scuffed film; the streak band theta -18..-5, rho .70-.82; front 7 %; right 13 %), only 3 % on the far side ("nowhere else"). Fine scratches: straight thin pale lines 4-22 mm, 95 % along the strands. The one dark smudge (theta -45..-35) is now 16 % darker (spec: ~15 %), keeps its gloss and still shows wear through it; round 1's was 50 % darker and dull, and read as a soft dark blotch. | The left bays read as a paler worn band with crisp streaks; left region p50 0.050 vs the reference's 0.052 (round 1: 0.043). |
| 2 | **Weave** | `paint.weave_table`, `paint_skin`. Irregular courses 6-12.6 mm (mean 9.3 = 0.031 R) that wander round the cone, 4-6 unequal strands each, plank runs 16-52 mm between radial seams (fresh per course), a tone and a small gloss offset PER TILE, the course line broken tile by tile. **The record grooves were gloss, not albedo**: per-strand specular and roughness lines at the strand gaps read as concentric rings at grazing views. The gaps now touch the gloss by 15 % (was 60 %); the course camber and strand relief were cut to 0.02-0.07 and 0.01 mm. | No concentric rings on the grazing bays; a tile grid of irregular planks with pale streaks. |
| 3 | **Rim, lashings, ribs, band cord** | `paint.paint_tube`, `paint_lashing`, `paint_rib`, `_fibres`; `geom.WRAP_PROFILES`, `build_lashings`. Rim tube: frayed split-cane fibre strips of uneven tone, frayed pale fibre ends, the rolled crest rubbed pale all round (the edge highlight), fibre-aligned scuffs on the front face. The binding cord is now LIGHT (REFERENCE_SPEC 6; round 1's was dark). Lashings: three-ply twisted cord, ply crests worn pale, deep dark valleys (profile valley 0.55 -> 0.30 rw, so the three wraps read as separate cords); each lashing leans and wanders up to 0.5 rw round its loop (the same at every LOD, no new triangles). Ribs: a two-ply twisted cord with a pale worn core in ALBEDO (a bug fixed: round 1's "top" pointed at the skin). Band roll: pale twist ridges. | Rims read fibrous with a pale crest; lashings read as wound cord; ribs show twist and a light core. |
| 4 | **Crown** | `geom.cap_lid`, `build_cap`; `paint.paint_cap`. The spherical dome (steep at its edge, blending into the cone) is replaced by a straight 21 deg conical lid (REFERENCE_SPEC 3: ~20 deg), its top rounded over 7 mm (no point, no finial), and a HARD lipped edge (separate normals, a crease) standing 3.3 mm proud with a rolled bead and a dark undercut. Pale rib lines on the lid and a rubbed pale lip crest. Crown top unchanged (F3 +0.07 px). | A distinct flat cap with a hard lip. |
| 5 | **Cloth** | `geom._tail_outline` (with a fallback), `edge_wobble`, `tail_folds`, `build_tail`, `build_knot`; `paint.paint_cloth`, `_grain`. Tails: the tear is a long CONCAVE taper (a claw-like point, not a straight diagonal), ragged at two scales, with frayed tatters that taper DOWN the ribbon (round 1's loose fibres stuck out sideways like a comb); the edges wave +-0.5 mm on the hanging part, with small nicks near the point; soft longitudinal folds whose phase drifts (a twist) displace the hanging cloth by up to ~3.5 mm with the true tilted normals, faded to 0 at the torn point so the tips stay on their pixels (two more columns only where it hangs). Knot: eight deeper, sharper gathered folds that twist round it (no star seen from above), flatter, a stronger crossing wrap, its top smooth. Texture: uneven warp streaks, crushed crease lines, fuzzy dust, frayed pale fibres near the tears, pale fold ridges on the knot and the fanned band. The cloth stays matte (roughness 0.85-0.95, Specular 0.25-0.35). | The tails read as worn fabric with folds and ragged tapering ends; the knot reads as gathered cloth, not a blob. |
| 6 | **Micro-detail and shimmer** | `paint_skin`: fibre-scale albedo speckle and, because the lacquer's sheen dominates black straw, fibre-scale SPECULAR-mask and roughness variation (linear channels, so every mip is their average; the normal map carries none of it). Ribs are rough (0.66+) with low specular and the light core in albedo, so there is no glint to break into dashes. `look.FILTER_WIDTH` 1.5 -> 1.0 for the reference view (the comparison shows the maps' pixel detail instead of a 1.5 px blur the reference does not have). | The EEVEE 1-sample turn the craft review used (`surface_pass/sp_turn.py`, 12 frames x 3 deg, old vs new: `surface_pass/turnsheet_final.png`) shows the ribs as continuous lines in every frame; round 1's show beaded highlights. Judged by eye, not measured. |

**Engineering after the pass (all measured on this build):**

| | Before (final pass) | After (surface pass) |
|---|---|---|
| LOD triangles | 16,816 / 6,290 / 1,977 | **16,504** / 6,314 / 1,977. LOD0 is down 312: the rim tube went from 144 to 120 segments round, which paid for the knot's 36 x 10 grid, the lid rings and the tails' hanging columns |
| LOD0 by part | tube 2,880, cord 1,152, cap 1,088, knot 432, tails 1,572 | tube 2,400, cord 960, cap 1,216, knot 648, tails 1,588 (the rest unchanged) |
| LOD deviation p99 (LOD1 / LOD2) | 1.43 / 3.77 mm | 1.62 / 3.96 mm (1 px at the switch: 0.93 / 2.65 mm) |
| Collision | 1 hull, 49 vertices | 1 hull, **48** vertices, 1.0 mm over the crown and under the rim, mean gap 8.1 mm. `support_hull` is now called with `max_vertices=49` (the new lid made the greedy fit land exactly on Chaos's 50) |
| HEAD socket | (0, 0, 134.833) mm | unchanged |
| Tint (linear, the mean colour) | straw (0.0428, 0.0391, 0.0380), cloth (0.0350, 0.0341, 0.0342) | straw **(0.0496, 0.0453, 0.0441)**, cloth **(0.0394, 0.0384, 0.0385)** (REFERENCE_SPEC 9: 0.042 +- 0.015 and 0.030 +- 0.010 lum) |
| DetailBias / DetailScale | straw 0.1228 / 5.2564, cloth 0.1336 / 2.4446 | straw **0.05858 / 6.853311**, cloth **0.199741 / 3.847832** |
| Detail range | 0-255, 256 levels | 0-255, 256 levels on both parts; mean(Bias + Scale x Detail) 1.000005 / 0.999994 |
| BC vs graph (8-bit source, max linear error) | 0.0017 / 0.0010 | 0.0022 / 0.0015 (gate 0.0035) |
| Mip parity, graph vs BC, mips 0-8 | within 0.38 / 0.82 % | within **0.57 / 0.24 %** (gate 1 %) |
| Roughness (straw / cloth) | min 0.251, p50 0.580 / 0.851-0.933 | min 0.322, p50 0.526 / 0.851-0.945 (the 0.25 and 0.85-0.95 floors hold) |
| Specular | straw 0.8 x ORM.A | straw **0.65 x ORM.A** (the sheen veiled the wear); cloth 0.5 x ORM.A. The sidecar's `specular_scale` is updated |
| Maps | 8 x 2048, full mips, no colour chunks | unchanged contract; ORM composite = _N (Toksvig) unchanged |
| Reference view: generator lines / rim bottom / crown | -1.55 / -1.41 / -0.02 / +0.01 px | -1.65 / -1.21 / +0.06 / +0.07 px |
| Mask IoU / tail tips A, B | 0.959 / (-1, -1), (-5, -1) px | **0.964** / (-1, -4), (-1, -1) px (gate 6 px) |
| Object luminance p10 / p50 / p90 (reference 0.0086 / 0.0242 / 0.0601) | 0.0109 / 0.0205 / 0.0485 | 0.0111 / **0.0224** / 0.0520 |
| Chroma (reference 0.349, 0.328, 0.323) | (0.343, 0.330, 0.327) | (0.346, 0.329, 0.324) |

**What still does not match (honest).**
- The worn pale streaks are finer and fewer than the reference's at the far-left bays (left region p95 0.09 vs
  0.13). Our pixel-level contrast on the straw is still about 60 % of the reference's (high-pass std 0.011-0.018 vs
  0.016-0.034): the reference looks sharpened, and the lacquer sheen dominates black straw.
- The reference's right bays show strips along the generators. Ours keeps REFERENCE_SPEC 5's circumferential strands
  (radial seams only); changing that would contradict the spec's measured strand direction.
- The knot is a gathered fold mass, partly hidden by the band and tail A. It is not modelled as a square knot's two
  crossed loops.
- The tails' fold relief is modest, to keep the tips on their pixels and clear of the tube.
- The rim tube is still 13 mm (REFERENCE_SPEC 6). It reads thinner through the pale crest and the groove, not through
  geometry. The lashings are not tied off with a separate knot.
- No new blind round was run.

**Process notes.**
- `WorkFiles/blackhat/regression/post_black_hat/compare_result.json` was overwritten by the frozen-asset run of
  `compare_black_hat.py` after this build. It now records black-hat MISMATCHES (expected for new bytes) and all three
  frozen lists OK. The snapshot itself (`SHA256SUMS.txt` and its copies) was NOT rewritten: re-snapshot with `--write`
  only once this build is accepted (after the Unreal check).
- Pre-pass state: `WorkFiles/blackhat/pre_surface_pass/` (scripts, exports, renders, blend, report and report JSON).
- Build logs: `WorkFiles/blackhat/build_surface_1.log` to `build_surface_4.log` (4 is the shipped build).

**Renders (all from the baked maps):** `Renders/BlackHat/blackhat_reference_view.png` (512 spp, filter 1.0),
`blackhat_side_by_side.png`, `blackhat_crops_3x.png`, and the gallery set `blackhat_hero.png`, `blackhat_raking.png`,
`blackhat_top.png`, `blackhat_underside.png`, `blackhat_wire.png`, `blackhat_lods.png`, `blackhat_lod_switch.png` and
`blackhat_linesheet.png`. Sections 1-10 below are the final pass's report; where their numbers differ from this
section (tints, bias and scale, triangles, hull, bytes, Unreal), this section is current.

---

## 1. Headwear decisions (the orchestrator's defaults; change any of these)

| Decision | What was built |
|---|---|
| **HEAD socket** | An Empty (`SOCKET_SM_BlackHat_LOD0_HEAD`), applied in Unreal from the sidecar. It sits on the axis at **z = 134.83 mm**, rotation 0: +Z points up out of the crown, +X forward. This is where the top of a 57 cm head (a sphere of r = 90.72 mm) touches the **inner** cone (half-angle 64°), 10.22 mm below the inner apex (z 145.05 mm). Unreal reads it at (0, 0, 13.4833) cm, scale 1. |
| Orientation | +X is forward. The knot is on the wearer's **left (+Y)**. |
| Pivot | On the axis at the bottom of the rim tube (z = 0). The tails hang 92 mm below it. |
| Headband ring / lining / chin cord | **None.** The reference never shows the underside, so it is the plain inner woven skin. Near the apex it now fades into a plain seat disc. **A head ring is an option** if you want one; buyers should be told the underside is plain. |
| Band and tails | Same static mesh, own slot `M_BlackHat_Cloth`, hanging in the reference pose. A cloth-sim or skeletal tail is a later option. |
| **Collision (new)** | **One** convex hull round the hat's body. The hanging tails have **no collision**, so a limp tail on a worn hat cannot block or snag the wearer. |
| Size | D = 600 mm, mass 300 g (both DESIGNED). |

## 2. What this pass changed (issue by issue)

| Issue (severity) | Decision | What was done / why not |
|---|---|---|
| Recolour tint semantics (minor) + recolour ergonomics (major) + detail range (minor) | **Applied** | The Tint is now the part's **mean colour**. `BaseColor = saturate(Tint x (DetailBias + DetailScale x Detail))`. Detail is **full range at both ends** (codes 0-255, 256 levels, both parts), quantised once from float. The defaults are in the sidecar (section 3). `mean(Bias + Scale x Detail)` = 1.000004 (straw) and 0.999992 (cloth), so a buyer who types a colour gets that colour as the part's average and at the far mips. |
| BC-vs-recolour equality under BC1 (minor) | **Applied** (documented) | The sidecar, the material spec and this report now say that equality holds at the **source / 8-bit** level. In Unreal, BC is BC1 and Detail is uncompressed G8, so the two paths differ by BC1 block error. |
| Second tint for the warmer rim and lashings (optional) | **Declined** | It needs a mask channel (ORM.B is free). But `lerp(TintA, TintB, mask) x Detail` is a product of two filtered terms, so the per-mip identity breaks along every mask border. The rim's warmth difference is within REFERENCE_SPEC's ±0.03. |
| Straw near-mirror roughness (part of the rim blocker) | **Applied** | Straw roughness is clipped to **≥ 0.25** (round 1 reached 0.05). Floors on the painted parts: **ribs 0.58**, **rim tube and lashings 0.52**, **crown cap 0.58**. |
| Specular levels | **Applied** | Straw Specular = **0.8 x ORM.A**, so F0 is at most 0.064 on the polished strand tops and about 0.04 on a typical texel (round 1: 1.0, F0 0.08). Straw 0.6 was tried first: it dropped the reference view's object p50 23 % below the reference (gate F6), so 0.8 was kept. |
| Cloth sheen (part of the cloth blocker) | **Applied** | Cloth roughness is **0.85-0.95**. Specular is **0.25-0.35** (mask 0.50-0.70 x 0.5); round 1 was mask 0.35-0.90 x 1.0. |
| Weave moire and shimmer at distance (part of the weave blocker) | **Applied (engineering part)** | Each ORM names its part's `_N` as **Composite Texture**, mode **CTM_NormalRoughnessToGreen**. That is Unreal's per-mip Toksvig: roughness widens by the normal map's variance at each mip, so distant weave goes rough instead of ringing. Unreal step `bhu_tex_composite.py` sets it; pass 2 re-reads it in a fresh process (gate 19). It is also recorded in the sidecar (`orm_texture_settings`) for buyers. |
| Weave look: record-groove rings, soft streaks, missing brick seams and flecks | **Not done: fidelity** | The rings are the authored course dome (a 0.30 mm height bump every 9.3 mm course) seen at grazing angles, not a UV stretch: the UVs are the cone's development, with zero stretch. Re-authoring the strands (4-6 texel pitch, brick runs, flecks) is a fidelity round. |
| Rib sparkle and crawl (major) | **Applied (engineering part)** | Rib roughness went 0.30 → 0.58-0.83, so a highlight spreads along the rod instead of breaking into dashes. The lighter worn core in BC and a twist in geometry are fidelity work and **not done**. |
| Crown cap metallic look (major) | **Applied (material)** | Cap roughness is 0.58+ and its mask is 0.4-0.8 x 0.8. The flat lipped lid geometry is fidelity work and **not done**. |
| Collision fit (minor) | **Applied** | See section 5. Round 1's hulls stood 15 mm above the crown and 30 mm below the tail tips, with a tail box. Now one hull, **1.0 mm** above the crown and below the rim, no tail box. |
| Triangle budget (minor) | **Justified, kept** | See section 4. The breakdown is also written into the sidecar (`triangle_budget`). |
| Mip count not measured (minor) | **Reported as INFERRED** | See section 6. |
| LOD tail pops (minor) | **Applied (partly)** | Coarse LODs now subdivide the tail outline wherever the centre line turns more than 15° between samples (the bend over the rim roll and the fall). The shaded pop went from 0.0039 / 0.0072 to **0.0030 / 0.0057** (mean stored difference at the switch). LOD2's tear is still cut straight: its teeth are 1-3 mm, sub-pixel at LOD2's 2.54 m switch. |
| Tail placement (minor) | **Applied (a real bug)** | Round 1 aimed the tail's **centre line** at the measured tip pixel. The torn point sits on the outer edge, half a width to image-right, which is exactly the measurer's 15-20 px. Now the **pointed tip** is solved onto the pixel, and gate F8 checks **x and y** on the render. Tip A lands at (591, 532) vs (592, 533); tip B at (638, 519) vs (643, 520). Tolerance is 6 px. The tails' width on the cone is fidelity and unchanged. |
| Underside (minor) | **Applied** | The inner weave fades into a plain seat disc at the apex (rho < 0.13); the swirl is gone. The underside shot is re-lit (lamp scale 0.45 vs 1.2); with the cloth's satin specular fixed, the tails read dark. |
| Product-line fit (major) | **Applied (presentation)** | New line sheet in the house framing: a 3/4 view at the hero angle on the left, a top view at the right, the caption at the smoke bomb's line pitch, and the smoke bomb sheet's own backdrop gradient composited behind (read only). The hat is fully in frame. The wire render was a real bug: it reused the camera the underside shot had moved below the rim. It is now a 3/4 view from 40° above, showing ribs, band and rim topology. The top view is lit at 0.5 (was 1.2). |
| Spec camera shift signs (measurer) | **Applied** | REFERENCE_SPEC 1 now carries an erratum: `+0.0030 / −0.0113`, with the aim point as the authority. The build was never affected: `blackhat_camera.py` derives its shift from the aim point, and the render's rim bottom and crown land within 0.02 px. |
| Rim roll / lashings rebuild, band / knot / tails as cloth, crown lid, wear in strand space, torn-end shapes (the craft blockers and majors) | **Not done: fidelity** | These are model and texture rebuilds, a new match round, which the brief reserves for your decision. They are listed in section 9. |

## 3. Textures, recolour and mip safety

Two sets at **2048**: `T_BlackHat_Straw_{BC,ORM,N,Detail}` and `T_BlackHat_Cloth_{BC,ORM,N,Detail}`. Straw is
21.7 px/cm, cloth 62.2 px/cm. The cloth's UV0 is in the second tile (U + 1); keep the textures on Wrap. Every
texel is painted from its own part's coordinates; nothing reads the reference.

**Recolour, per part** (the sidecar's `materials` block holds all of it):

| | Straw | Cloth |
|---|---|---|
| **Tint** (the part's MEAN colour, linear) | (0.042821, 0.039103, 0.038023) | (0.035018, 0.034089, 0.034192) |
| Tint (sRGB) | (0.2289, 0.2183, 0.2152) | (0.2060, 0.2031, 0.2035) |
| **DetailBias / DetailScale** | 0.122772 / 5.256401 | 0.133561 / 2.444596 |
| Detail codes used | 0-255, 256 levels (p1 / p50 / p99 = 27 / 96 / 212) | 0-255, 256 levels (60 / 156 / 236) |
| BC vs graph at defaults, max linear error (8-bit source) | 0.0017 | 0.0010 |
| Graph vs BC, mean over mips 0-8 | within **0.38 %** | within **0.82 %** |

- **Encoding.** Detail is `d = (albedo − a_lo) / (a_hi − a_lo)`, sRGB-encoded linear, imported sRGB ON. Unreal
  decodes before filtering, and the affine `Bias + Scale x d` commutes with the filter, so every mip is correct.
- **Specular mask.** It is linear in ORM.A.
- **Which parameter a buyer edits.** Edit **Tint**. For a light recolour whose flecks should not clip, lower
  DetailScale and raise DetailBias together, keeping `Bias + Scale x mean(d)` at 1.
- **BC1 caveat.** In Unreal the fixed-colour BC is BC1-compressed, so it differs from the recolour path by BC1
  block error. Equality holds at the 8-bit source only.

**Material:**
- Specular = 0.8 x ORM.A (straw), 0.5 x ORM.A (cloth);
- Roughness = ORM.G, with the Composite Texture = `_N`, NormalRoughnessToGreen;
- Metallic 0;
- N is DirectX, flip green OFF.

**Roughness as shipped:**
- straw min 0.251, p50 0.580;
- cloth 0.851-0.933.

ORM.R is the analytic cavities x a Cycles AO bake of LOD0 (256 samples).

## 4. LODs and triangles

| LOD | Triangles | Screen size | Switch | LOD0 → LODn p99 / 1 px at switch |
|---|---|---|---|---|
| 0 | **16,816** (straw 12,012 + cloth 4,804) | 1.0 | - | - |
| 1 | **6,290** | 0.695 | 0.89 m | 1.43 mm / 0.93 mm |
| 2 | **1,977** | 0.2432 | 2.54 m | 3.77 mm / 2.65 mm |

The bounds radius is 347.5 mm (it moved from 351.8 mm because the tails moved). The screen sizes follow the pack rule.

**Why LOD0 is 16.8k and not ~10k.** It is a 600 mm hat, the pack's largest prop, and its signature details are real
geometry:

| Part | LOD0 triangles |
|---|---|
| 26 lashings of three cords | 4,992 |
| rim tube | 2,880 |
| band | 2,800 |
| tails with walls | 1,572 |
| binding cord | 1,152 |
| cap | 1,088 |
| outer skin | 1,106 |
| ribs | 416 |
| knot | 432 |
| inner skin | 378 |

- **Where the budget could come down.** The reviewer is right that it sits in smooth tubes and rings. Moving
  triangles from the rim tube and lashing segments into the cap lip, knot folds and tail ends belongs with the
  fidelity rebuild of those parts; doing it now would only reshuffle geometry that is going to be remodelled.
- **What this pass added.** The tail change added 28 triangles to LOD0, 248 to LOD1 and 128 to LOD2.

## 5. Collision

**UCX_SM_BlackHat_LOD0_00**, one hull with **49 vertices** and 94 faces. It is the intersection of support planes,
each **1.0 mm** outside the body:
- straight down;
- straight up (the crown);
- 13 horizontal planes (the rim);
- 13 planes at the cone's normal elevation (64°);
- 2 greedy planes at the band and knot.

It contains the body of every LOD by construction; the worst body vertex is 1.0 mm inside.

**Fit, measured:**
- 1.0 mm above the crown and below the rim;
- 9.9 mm beyond the widest radius at the 13-gon's corners;
- mean 7.8 mm (max 13.5) proud of the points' exact convex hull.

Round 1 was mean 11.7 / max 27.8 mm, plus a 326 cm³ box round the tails.

**Why 49 vertices.** The cap is Chaos's own geometry-complexity threshold (`p.Chaos.ConvexParticlesWarningThreshold`
= 50; its check is off by default). A 20-azimuth hull would fit to a 4.7 mm mean, but needs 79 vertices.

**The hanging tails have no collision, by design.** That is 379 LOD0 vertices, down to z = −91.6 mm. Unreal's round trip:
- the hull's 49 vertices come back within 1.6e-6 cm;
- all 8,605 LOD0 body vertices are inside;
- the 379 tail vertices are excluded by the same rule the build uses.

## 6. Unreal verification (`/Game/PropsCheck/BlackHat_0926d`, bytes `fa35264c…`)

Each step ran in a fresh process, one commandlet at a time. The harness refuses to start if any UnrealEditor-Cmd is
running.

**Steps:**
1. Blender FBX count;
2. pass 1 import (legacy FBX, Import Mesh LODs ON) + sidecar (`Scripts/pipeline/ue_import_sockets.py`, unchanged);
3. props texture import (`ue_import_textures.py`, unchanged);
4. **new:** `bhu_tex_composite.py` (ORM composite = N);
5. fresh texture verify;
6. pass 2 reload + gates;
7. pass 3 Unreal FBX export;
8. Blender round trip;
9. UV1 overlap.

**VERIFIED 20 / 20:**
- **LODs:** 16,816 / 6,290 / 1,977, identical in Blender, in the FBX re-import and in Unreal. Positions round-trip
  exactly; no triangle was dropped.
- **Collision:** 1 hull, round trip within 1.6e-6 cm, and it contains the LOD0 body.
- **Socket:** HEAD at (0, 0, 13.4833) cm, scale 1, owned by the asset.
- **Screen sizes:** from the sidecar, with the bounds radius matching.
- **Lightmap:** UV1 generated, 0 overlap at 1024 and 2048 on every LOD.
- **Material slots:** 2.
- **Nanite:** off.
- **Texture flags:** all 8 persisted.
- **ORM:**
  - Composite = its `_N`, NormalRoughnessToGreen (gate 19, re-read in a fresh process);
  - alpha kept, with the source alpha equal to the shipped mask's range (straw 0.024-1.0, cloth 0.502-0.698).

**Gate-rule change.** Run `0926c` failed gate 9 only on the old rule "ORM alpha spread > 0.5", which the matte cloth
mask (0.50-0.70) no longer meets. The rule now compares against the shipped range. That run is archived in
`UnrealCheck/archive_0926c_gate9_alpha_rule/`; round 1's run `0926b` is in `archive_0926b/`.

**Mip count: INFERRED, not measured.** A `-nullrhi` commandlet builds no platform data: ListTextures reads 1x1 with
0 mips, and Texture2D has no mip-count accessor in 5.8. The 12-mip chain follows from:
- 2048² power-of-two sources;
- TMGS_FROM_TEXTURE_GROUP, with the World / WorldNormalMap groups on SimpleAverage;
- LOD bias 0 and max size 0;
- no streaming VT.

**Why it was not measured.** Measuring needs a render-capable process or a cook. Neither was run, because other
Unreal editors were open on this machine.

## 7. Renders (all from the baked maps; `Renders/BlackHat/`)

- **Reference view:** `blackhat_side_by_side.png` (reference | render); `blackhat_reference_view.png` (670 x 599,
  the spec camera, 512 spp); `blackhat_crops_3x.png`.
- **Gallery:**
  - `blackhat_hero.png` and `blackhat_raking.png`;
  - `blackhat_underside.png` (re-lit);
  - `blackhat_top.png`;
  - `blackhat_wire.png` (3/4 from above; was the underside);
  - `blackhat_lods.png` and `blackhat_lod_switch.png`;
  - **`blackhat_linesheet.png`** (house framing).

**Measured on the shipped render** (`blackhat_report.json`, `fidelity`):

| Measure | Result |
|---|---|
| Generator lines | −1.55 / −1.41 px (REFERENCE_SPEC 11 asks for 1 px; still 0.5 px over) |
| Rim bottom | −0.02 px |
| Crown | +0.01 px |
| x extent | exact |
| Mask IoU | 0.959 |
| Object luminance p10 / p50 / p90 | 0.0109 / 0.0205 / 0.0485 vs 0.0086 / 0.0242 / 0.0601 |
| Chroma | (0.343, 0.330, 0.327) vs (0.349, 0.328, 0.323) |
| Tail tips | A (−1, −1) px, B (−5, −1) px |

## 8. Blind-test history

| Round | Pairs | Picked correctly | Confident and correct | Outcome |
|---|---|---|---|---|
| 1 (2026-09-26) | 20, sides randomised, non-image PNG chunks stripped, no key on disk (`WorkFiles/blackhat/blind_r1/`) | **20 / 20** | 20 | **Failed decisively.** The loop stopped early, and no round 2 was run. |

**The judges' tells**, consistent across all 20 pairs:
- **Straw skin:** vinyl-record rings or smeared streaks where the reference has a plank weave.
- **Wear:** no pale scuffed patches, only soft dark blotches.
- **Rim:** a thick glossy tube.
- **Lashings:** neat smooth loops.
- **Ribs and band:** smooth dark rods.
- **Crown:** a soft dome instead of a flat capped lid.
- **Knot:** a rubbery blob.
- **Cloth:** flat vector-black, with blunt comb-like torn ends.
- **Overall:** a soft, plastic, clean look.

**What this pass removes from that list.** Only the glossy tube and the plastic sheen, partly, through the roughness
and specular fixes. The rest needs the fidelity rebuild.

## 9. Per-element fidelity (after this pass) and what still does not match

**Status key.** Every row is from the round-1 measurement unless it says otherwise.
- "Within tolerance" is against REFERENCE_SPEC.
- "Looks different" is the round-1 judgement. This pass did not re-judge by eye with a new blind round.

| Element | Within tolerance | Looks different | After this pass |
|---|---|---|---|
| Camera / frame | yes (spec erratum fixed) | no | Unchanged. |
| Cone silhouette / generator lines | no (−1.5 / −1.4 px vs 1 px) | yes | Unchanged: the far rim tube and lashings stand proud at the side tips. |
| Crown cap | no | yes | Matte now, no metal highlight. It is still a dome with no flat lid and no lip line. |
| Ribs | yes (count / place) | yes | Rougher, so there are no crawling dashes. They are still smooth dark rods, with no light twisted core. |
| Woven skin / weave | no | yes | There is a per-mip roughness fold in Unreal. The course bands still read as rings at grazing angles. There are no crisp strand lines, brick seams or flecks at the reference's contrast (40-60 %). |
| Rim (rolled tube, cord, groove) | no | yes | Less glossy. It is still a thick pipe with a trench at the side tips, and no visible light binding cord. |
| Lashings | yes (count / place) | yes | Unchanged: smooth, uniform, dark, bridging the trench like staples. |
| Band | yes (path / height) | yes | Matte now. It is still a thin strip that turns into a sausage roll at the knot. |
| Knot | no | yes | Unchanged: a smooth lump that bumps the top-right silhouette. |
| Tails: position | **yes now** (A −1 / −1 px, B −5 / −1 px) | partly | The torn points are on the measured pixels in x and y. |
| Tails: width / drape / cloth | no | yes | Matte now, no satin. They are still narrow and diagonal on the cone, about 1.9 mm thick, with no weave read. |
| Torn ends | no | yes | Unchanged: blunt, with hair-like spikes; B's notch is not the reference's split sliver. |
| Wear / worn patches | no | yes | Unchanged: a dark diagonal stripe plus soft mottling, with no bright scratched streaks. |
| Colour / tone | yes (p50 −15 %, chroma within 0.006) | no | Slightly darker than round 1 (−8 %) because the sheen is lower. One tint per part, so there is no warmer rim. |
| Underside / invented nothing | yes | no | Plain, with a seat disc at the apex. Nothing is invented: no chin cord, lining, decal or colour. |

**Honest summary.** The hat's shape, layout and engineering are right, and it recolours and imports cleanly. Its
surface and cloth do not yet look like the reference: the blind test found it every time. Closing that gap is a
new fidelity round built the way the object is built:
- the skin rolled over a core hoop, with a light binding cord;
- 2-ply crossed lashings;
- a flat lipped lid;
- the band as a folded twisted strip;
- a 3-4 layer knot;
- broad draped tails with hems and long ragged points;
- strand-space weave with brick runs and flecks, and strand-aligned bright wear.

Nothing was started. It is your decision.

## 10. Files

| Path | What |
|---|---|
| `Scripts/props/build_black_hat.py` | The build: stages, measure, gates (25), sidecar material, budget and collision blocks, fidelity |
| `Scripts/props/props_lib/blackhat_{spec,camera,geom,atlas,paint,look,gallery}.py` | The library (1.1.0). New: `geom.solve_tail_paths` / `tail_u_samples`, `paint.finish` (mean-colour recolour), `look.support_hull`, `gallery._line_sheet` |
| `Assets/BlackHat.blend` | Rebuilt from scratch; textures packed |
| `Exports/BlackHat/` | `SM_BlackHat.fbx`, `SM_BlackHat.sockets.json`, `Textures/` (8 maps, 2048) |
| `WorkFiles/blackhat/UnrealCheck/` | Harness (new `bhu_tex_composite.py`), run `0926d`, archives |
| `WorkFiles/blackhat/regression/post_black_hat/` | Snapshot (36 files), `SHA256SUMS.txt`, `compare_black_hat.py`, `compare_result.json` (black hat plus all three frozen lists) |
| `WorkFiles/blackhat/pre_final_pass/` | Round 1's scripts, exports, renders, blend and report, kept for comparison |
| `WorkFiles/blackhat/final_pass/` | This pass's patch scripts, hull prototypes and dev-build logs (`build_dev/fp1`-`fp4`) |
| `Backups/BlackHat_2026-09-25/` | Backup: blend, `Exports/BlackHat`, `Renders/BlackHat`, the modules and build script, this report, `References/BlackHat` |
| `References/BlackHat/REFERENCE_SPEC.md` | Now with the camera-shift erratum |

**Not touched:**
- the shuriken pack, the smoke bomb (its line sheet was only **read** for the backdrop gradient) and the paused
  paper bomb;
- the generic props_lib modules;
- `ue_import_textures.py` and `Scripts/pipeline/**`;
- the locks (BlackHat is held by claude, and was read only).

No GUI Blender, blender-mcp or running editor was used, and nothing was downloaded.
