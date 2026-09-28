# SM_BlackHat: build report (surface pass + close-out)

**Date:** 2026-09-26. **Library:** props_lib blackhat **1.2.1** (1.2.0 was the surface pass, 1.2.1 is the close-out).
**Build:** `Scripts/props/build_black_hat.py`, run from scratch with no arguments (Blender 5.2.0 LTS, headless,
`--factory-startup`, 64 s). It rebuilt `Assets/BlackHat.blend`, `Exports/BlackHat/` and `Renders/BlackHat/`.
Log: `WorkFiles/blackhat/build_closeout_2.log`. The surface-pass state (bytes `d959d2f1...`) is kept in
`WorkFiles/blackhat/pre_closeout/`, and the final-pass state before it in `WorkFiles/blackhat/pre_surface_pass/`.

## Status

- **Surface pass: done and closed.** It was the ONE targeted pass on the blind judge's surface and finish tells
  (section 0). The blind score went from **20 / 20** to **19 / 20** (7 of them confident). Section 0.2 lists what still
  differs. No further fidelity round was started.
- **Close-out (section 0.1):** removed the three things the measurer listed as INVENTED, and fixed the two stale-text
  minors the Unreal verifier raised. That changed bytes, so everything was rebuilt and re-verified.
- **Engineering (these bytes):**
  - **Build gates: 25 of 25 pass** (`WorkFiles/blackhat/blackhat_report.json`, `gates`), including the recolour
    (9b), mip parity (9c), roughness floors (9d), single hull (7b), frozen assets (10) and the fidelity gates F1-F8.
  - **qa_check: 76 of 76 pass.**
  - **Unreal 5.8.3: VERIFIED 20 / 20** on these exact bytes (`/Game/PropsCheck/BlackHat_CloseOut_0926l`, 0 Warning /
    Error lines in all six commandlets, section 6).
- **Frozen assets unchanged:** shuriken **78 of 78** (and 78 of 78 against the snapshot's own copies), smoke bomb
  **30 of 30**, paper bomb **6 of 6** (`regression/post_black_hat/compare_black_hat.py`, run after the final build).
  The build's own start / end check agrees (41 / 29 / 6 lines of its lists).

**Bytes (shipped, close-out):**
- FBX `719248e4cc44bff4bba698345fba78017b913c1c8e15ca01f0a88388fa7031eb`
- sidecar `6a8d03c1e8d4c9dd2dca6e36e9fb08119d5fda564da2acd4206bf31a2f0e295d`
- blend `02c22e7a236d942e98cd46e107befaa78e1e10ff8515c01e7039611321a61ca5`

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

| | Before (final pass) | After (surface pass, `d959d2f1...`) |
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


The "After (surface pass)" column above is the surface-pass build (`d959d2f1...`). The shipped close-out values of
these rows (tints, bias / scale, LODs, hull, mips, fidelity) are in sections 0.1 and 3-7.

### 0.1 Close-out (library 1.2.1)

**Scope.** The pass was closed as it stood. The close-out did three things:
- removed what the round-2 measurer listed as **invented** (things the reference does not show);
- fixed the Unreal verifier's minors (it raised no blockers and no majors);
- refreshed the snapshot, the backup and this report.

No fidelity item was re-opened.

| Invented (measure_r2) | What was changed (module) | Result |
|---|---|---|
| **The knot and the fanned band read as an even stack of parallel horizontal pleats.** | `geom.build_knot`: six uneven folds with uneven depths (was eight near-even ones). There are now **two lobes, each with its own fold set twisting in the opposite sense**, so the folds cross like a square knot's two loops, and the crossing wrap lies diagonally over the join (`knot_fold_field`, `knot_lobe`). `geom.band_profile`: the band's three folds wander across it along its length (`drift`), so they are not parallel pleats. `paint.paint_cloth`: the regular fold lines painted every 6.5 mm across the fanned band are **gone**. There is only soft uneven shading, plus the pale rubbed highlight where the band enters the knot, which the reference shows. | Crossed loops, no pleat stack (`closeout/closeout_old_vs_new.png`, row 3). |
| **Rectangular, tile-aligned edges on the dark smudge and the pale wear patches.** | `paint.paint_skin`. The smudge is now a **soft irregular blotch**: a domain-warped ellipse in millimetres round REFERENCE_SPEC 9's zone (theta -38.5, rho 0.72) with a wide soft falloff and patchy inside. Before, it was bounded by straight theta / rho edges. The wear-zone borders are domain-warped (+-7 deg, +-0.05 rho), so they are no longer radial lines along the seams. The patch threshold is softer (0.16 wide, was 0.07), and the smudge thins the wear less (x 0.25, was x 0.6). | The EEVEE game-distance view no longer shows the dark vertical bar or the blocky patch outline (`closeout/closeout_game_distance_old_vs_new.png`, old left, new right). The per-tile tone differences of the plank grid stay; the measurer counted those as a match. |
| **A wide dark trough between the rim tube and the cone at the sides, with the lashings reading as flat straps bridging it.** | `geom.Hat._fillet` / `fillet_rows`, `build_skin`. The skin now **rolls onto the tube in a 6 mm concave fillet**: tangent to the skin at r = 281.5 mm and to the tube at 137 deg, just inside the binding cord at 112 deg. Before, it ran straight into the tube below the tube's equator. The groove left between the roll and the cord is about 2 mm. The lashings wrap the fillet (`lashing_body_points`), so they hug the roll. The tails ride over it (`build_tail_path` lifts them by `fillet_lift`): every cloth vertex over the fillet is **2.5 mm or more** above it on every LOD, and cloth faces are straight chords over a convex profile. | The trough is a narrow groove (`closeout/closeout_old_vs_new.png`, rows 1-2). |

**Triangles.** The skin is a straight cone, and rows along a generator are collinear. So LOD0 dropped its 0.35 / 0.65
rows, and LOD1's 0.35 / 0.65 rows became one row at 0.5. That paid for the fillet's rows.
- **LOD0: 16,504, unchanged** (straw 11,468, cloth 5,036).
- LOD1: 6,306 (-8, from the tails' re-solved bend).
- LOD2: 2,033 (+56: the fillet's one row, 52, and the tails, 4).
- LOD deviation p99 (LOD0 to LODn): 1.59 / 3.93 mm (was 1.62 / 3.96).

**Unreal minors.**
1. **Hull wording.** The sidecar's `collision_note` now says that the hull holds the straw body (every straw vertex of
   every LOD is inside it, by at least 0.99 mm). It also says the cloth tails have no collision from where they leave
   the band over the rim edge, so a few tail vertices on the rim roll lie outside it as well as the hanging tails.
   Measured on these bytes (`closeout/co_hull_cloth.py`):
   - vertices outside: LOD0 320, LOD1 243, LOD2 44, all of them cloth;
   - of those, above the hull floor: 10 / 19 / 4, by at most 3.75 / 4.19 / 3.75 mm.
2. **Stale sections 3-6.** They are rewritten below with these bytes' numbers.
3. **Mips.** The mip count is still INFERRED, not measured (`-nullrhi`), as before. Measuring it needs an RHI session,
   and none was opened while the other session's editors are in use.

**One regression found and fixed on the way.** The first close-out build (`af1b827e...`, run
`UnrealCheck/archive_0926e_tangent_warning/`) passed every gate except "0 Warning / Error lines". Unreal logged
"nearly zero tangents / bi-normals" on import. Diagnostic imports were run with pass 1's exact options
(`closeout/co_diag_*.py`, `closeout/diag_tangent/*.log`; no content saved). They traced it to the LOD0 knot: blending
the fold TWIST between the two lobes squeezed the folds at the join. Blending two whole fold SETS instead cured it.
The shipped bytes import with 0 warnings.

**Shimmer (not a close-out item, measured so this pass is honest about it).** On the measurer's probe (EEVEE, 1
sample, 3.2 m, 85 mm, 16 frames x 0.25 deg, `closeout/co_turn.py` + `co_flicker.py`), second-difference flicker is
0.00887 for the surface-pass bytes and **0.00887** for the close-out bytes. The close-out neither fixed nor worsened it.
The ribs and lashings are still the main flicker lines (`closeout/closeout_flicker_old_new.png`).

**Fidelity gates on these bytes.** All pass.
- Generator lines: -1.66 / -1.22 px.
- Rim bottom / crown: +0.07 / +0.07 px.
- Mask IoU: 0.964.
- Tail tips: A (-1, -4), B (-1, -1) px.
- Object luminance p10 / p50 / p90: 0.0116 / 0.0226 / 0.0538, against the reference's 0.0086 / 0.0242 / 0.0601.

### 0.2 Blind scores and what still differs

| Round | Bytes | Picked correctly | Confident and correct |
|---|---|---|---|
| 1 (before the pass, `blind_r1/`) | final pass `fa35264c...` | **20 / 20** | 20 |
| 2 (after the surface pass, `blind_r2/`) | `d959d2f1...` | **19 / 20** | **7** |
| close-out | `719248e4...` | not re-judged (the user asked for one pass, then move on) | - |

**What still differs from the reference.** This is the round-2 measurer's list (`WorkFiles/blackhat/measure_r2/`),
minus the three invented items fixed above.
- **Tone.** Ours is darker and flatter over the straw: object p50 0.019 vs 0.024 linear under the 7-light fit. The right
  bay is 0.023 vs 0.043, and the tails below the rim 0.009 vs 0.016, so the tails read near-black.
- **Micro-contrast.** About 40-60 % of the reference in every region: rim front 0.013 vs 0.028, right bay 0.0096 vs
  0.021, band 0.013 vs 0.025, tails 0.007 vs 0.010.
- **Wear.**
  - Ours is short, bright, evenly scattered dashes; the reference has a broad greyish scuffed film with dashes inside it.
  - The far-left bays are weaker: p95 0.088 vs 0.18, coverage 16 % vs 26 %.
  - The upper cone and the band have almost no pale wear: 1.6 % vs 16 %, and 2.6 % vs 19 %.
  - The close-out made the patch and smudge edges soft; it did not add wear.
- **Weave.** At grazing angles on the far-left and right bays, fine regular course lines still read like record
  grooves. On the right bays, the reference shows strips running along the generators.
- **Rim.** The trough is gone, but the tube's silhouette is smooth. The reference has shaggy frayed fibres along its
  outline, and a paler worn crest than ours.
- **Ribs, band cord and lashings.** They stay dark rods with a fine twist texture. The reference has pale highlighted
  cores and worn crests (rim front p95 / p50: 2.0 vs 4.25).
- **Knot.** The pleat stack is gone, and it now reads as two crossed lobes with a diagonal wrap. It is still a smooth
  modelled lump, not the reference's clearly separate twisted loops.
- **Tails.** The silhouettes are smooth vector curves and the tears are too clean. The reference ends have stepped,
  ragged teeth along the whole tear.
- **Crown.** The lid shape is right. The reference lid shows pale worn radial lines and a pale speckled rim; ours is
  darker and cleaner (cap p95 / p50 1.85 vs 2.99).
- **Shimmer.** Not fixed. The ribs and lashings are still the dominant flicker lines at game distance (see above).
- **Silhouette (minor, carried over).** The left generator is flatter than the reference: slope -0.443 vs -0.472, up to
  3 px.

**Process notes.**
- **Snapshot.** `WorkFiles/blackhat/regression/post_black_hat/` was re-snapshotted with `--write` on the close-out bytes
  after the Unreal check passed. `compare_black_hat.py` now also tracks this report. The run after the snapshot is all
  OK: the black hat, shuriken 78 / 78 (plus 78 / 78 against the snapshot's copies), smoke bomb 30 / 30 and paper bomb
  6 / 6.
- **Backup.** `Backups/BlackHat_2026-09-25/` was refreshed to these bytes (its `SHA256SUMS.txt` was rewritten).
- **State before the close-out.** `WorkFiles/blackhat/pre_closeout/` holds the surface-pass scripts, exports, renders,
  blend, report and report JSON.
- **Close-out work files.** `WorkFiles/blackhat/closeout/` holds:
  - the dev render `d01/`;
  - the comparison sheets `closeout_*.png`;
  - the probes `co_*.py`;
  - the tangent diagnosis `diag_tangent/`.
- **Build logs.** `build_closeout_1.log` (the tangent warning) and `build_closeout_2.log` (shipped). The surface pass's
  are `build_surface_1.log` to `build_surface_4.log`.

**Renders (all from the baked maps):**
- `Renders/BlackHat/blackhat_side_by_side.png` (reference | render), `blackhat_reference_view.png` (512 spp, filter
  1.0) and `blackhat_crops_3x.png`;
- the gallery set: `blackhat_hero.png`, `blackhat_raking.png`, `blackhat_top.png`, `blackhat_underside.png`,
  `blackhat_wire.png`, `blackhat_lods.png`, `blackhat_lod_switch.png` and `blackhat_linesheet.png`.

Sections 1-2 are the final pass's decisions, kept as history. Sections 3-6 are current for these bytes.

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

## 3. Textures, recolour and mip safety (these bytes)

Two sets at **2048**: `T_BlackHat_Straw_{BC,ORM,N,Detail}` and `T_BlackHat_Cloth_{BC,ORM,N,Detail}`. Straw is
21.95 px/cm, cloth 62.3 px/cm. The cloth's UV0 is in the second tile (U + 1); keep the textures on Wrap. Every
texel is painted from its own part's coordinates; nothing reads the reference.

**Recolour, per part** (the sidecar's `materials` block holds all of it):

| | Straw | Cloth |
|---|---|---|
| **Tint** (the part's MEAN colour, linear) | (0.049758, 0.045438, 0.044183) | (0.039551, 0.038501, 0.038618) |
| **DetailBias / DetailScale** | 0.058461 / 6.879606 | 0.239278 / 3.800177 |
| Detail codes used | 0-255, 256 levels (p1 / p50 / p99 = 36 / 96 / 197) | 0-255, 256 levels (49 / 115 / 210) |
| mean(Bias + Scale x Detail) | 0.999994 | 1.000007 |
| BC vs graph at defaults, max linear error (8-bit source) | 0.0023 | 0.0015 |
| Graph vs BC, worst mean over mips 0-8 | within **0.41 %** | within **0.59 %** |

- **Encoding.** Detail is `d = (albedo - a_lo) / (a_hi - a_lo)`, sRGB-encoded linear, imported sRGB ON. Unreal
  decodes before filtering, and the affine `Bias + Scale x d` commutes with the filter, so every mip is correct.
- **Specular mask.** It is linear in ORM.A: straw 0.08-1.0, cloth 0.50-0.70.
- **Which parameter a buyer edits.** Edit **Tint**. For a light recolour whose flecks should not clip, lower
  DetailScale and raise DetailBias together, keeping `Bias + Scale x mean(d)` at 1.
- **BC1 caveat.** In Unreal the fixed-colour BC is BC1-compressed, so it differs from the recolour path by BC1 block
  error. Equality holds at the 8-bit source only.

**Material:**
- Specular = 0.65 x ORM.A (straw), 0.5 x ORM.A (cloth);
- Roughness = ORM.G, with the Composite Texture = `_N`, NormalRoughnessToGreen (Toksvig);
- Metallic 0;
- N is DirectX, flip green OFF.

**Roughness as shipped.** Straw min 0.322, p50 0.526, max 0.874. Cloth 0.851-0.949. ORM.R is the analytic cavities x a
Cycles AO bake of LOD0.

## 4. LODs and triangles (these bytes)

| LOD | Triangles | Screen size | Switch | LOD0 -> LODn p99 / 1 px at switch |
|---|---|---|---|---|
| 0 | **16,504** (straw 11,468 + cloth 5,036) | 1.0 | - | - |
| 1 | **6,306** | 0.695 | 0.89 m | 1.59 mm / 0.93 mm |
| 2 | **2,033** | 0.2432 | 2.54 m | 3.93 mm / 2.65 mm |

The bounds radius is 347.48 mm. The screen sizes follow the pack rule (0.69496 / 0.24324 from that radius).

**LOD0 by part:**

| Part | Triangles |
|---|---|
| lashings | 4,992 |
| band | 2,800 |
| rim tube | 2,400 |
| tails | 1,588 |
| cap | 1,216 |
| outer skin (now with the fillet) | 1,106 |
| binding cord | 960 |
| knot | 648 |
| ribs | 416 |
| inner skin | 378 |

LOD0 is not above the surface pass's 16,504. The budget sits in the 26 three-cord lashings and the rim tube; cutting
them is fidelity work and was not started.

## 5. Collision (these bytes)

**UCX_SM_BlackHat_LOD0_00**, one hull with **48 vertices** and 92 faces. It is the intersection of support planes,
each **1.0 mm** outside the body:
- straight down;
- straight up (the crown);
- 13 horizontal planes (the rim);
- 13 planes at the cone's normal elevation;
- greedy planes at the band and knot when needed (none on these bytes).

The hull was fitted with `max_vertices=49`, under Chaos's 50.

**Fit, measured:**
- 1.0 mm above the crown and below the rim;
- 9.9 mm beyond the widest radius at the 13-gon's corners;
- mean 8.1 mm (p95 12.3, max 18.2) proud of the points' exact convex hull.

**What it holds.** Every straw vertex of every LOD is inside, the worst by 0.99 mm (LOD0) / 1.0 mm. The cloth tails
have **no collision by design** from where they leave the band over the rim edge. Outside the hull are:
- 320 LOD0 vertices (243 on LOD1, 44 on LOD2), all cloth;
- of those, 10 / 19 / 4 sit on the rim roll above the hull floor (z -2.8 mm), by at most 3.75 / 4.19 / 3.75 mm;
- the rest hang below the floor, down to z = -91.6 mm.

The sidecar's `collision_note` says the same.

## 6. Unreal verification (`/Game/PropsCheck/BlackHat_CloseOut_0926l`, bytes `719248e4...`)

UE **5.8.3**. The harness is `WorkFiles/blackhat/UnrealCheck/run_unreal_checks.sh`, which refuses to start while any
UnrealEditor-Cmd is running. Each step ran in a fresh process, one commandlet at a time, and none was left running.

**Steps:**
1. Blender FBX count;
2. pass 1 import (legacy FBX, Import Mesh LODs ON) + sidecar (`Scripts/pipeline/ue_import_sockets.py`, unchanged);
3. props texture import (`ue_import_textures.py`, unchanged);
4. ORM composite = N;
5. fresh texture verify;
6. pass 2 reload + gates;
7. pass 3 Unreal FBX export;
8. Blender round trip;
9. UV1 overlap.

**VERIFIED 20 / 20:**
- **Warnings:** 0 Warning / Error lines in all six commandlet logs, and empty stderr.
- **LODs:** 16,504 / 6,306 / 2,033, identical in Blender, in the FBX, in Unreal and in Unreal's own re-export.
  Positions round-trip exactly.
- **Collision:** 1 convex hull, whose vertices come back within 1e-5 cm. It contains the LOD0 body in engine space.
- **Socket:** HEAD at (0, 0, 13.4833) cm, scale 1, owned by the asset.
- **Screen sizes:** from the sidecar (1.0 / 0.695 / 0.2432), with the bounds sphere radius (34.748 cm) matching.
- **Lightmap:** UV1 generated, 0 overlap at 1024 and 2048 on every LOD.
- **Material slots:** 2 (straw, cloth).
- **Nanite:** off.
- **Texture flags:** all 8 persisted in a fresh process.
- **ORM composite:** its `_N`, NormalRoughnessToGreen, persisted.
- **Bytes:** the same bytes everywhere.

Records are in `UnrealCheck/verification_summary.json` and the pass JSONs. The failed first close-out run (the tangent
warning, section 0.1) is in `UnrealCheck/archive_0926e_tangent_warning/`, and the final pass's run in
`archive_0926d/`. The independent verifier's run on the surface-pass bytes (`d959d2f1...`) is in
`UnrealVerify_indep_v2/`.

**Mip count: INFERRED, not measured.** A `-nullrhi` commandlet builds no platform data. The 12-mip chain follows from:
- 2048 power-of-two sources;
- TMGS_FromTextureGroup;
- LOD bias 0 and max size 0.

Measuring it needs a render-capable session. None was opened, because the other session's editors are in use on this
machine.

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

**Measured on the shipped render** (`blackhat_report.json`, `fidelity`, close-out bytes):

| Measure | Result |
|---|---|
| Generator lines | -1.66 / -1.22 px (REFERENCE_SPEC 11 asks for 1 px; the left is still 0.66 px over) |
| Rim bottom | +0.07 px |
| Crown | +0.07 px |
| x extent | exact |
| Mask IoU | 0.964 |
| Object luminance p10 / p50 / p90 | 0.0116 / 0.0226 / 0.0538 vs 0.0086 / 0.0242 / 0.0601 |
| Chroma | (0.347, 0.329, 0.324) vs (0.349, 0.328, 0.323) |
| Tail tips | A (-1, -4) px, B (-1, -1) px |

## 8. Blind-test history

| Round | Bytes | Pairs | Picked correctly | Confident and correct | Outcome |
|---|---|---|---|---|---|
| 1 | final pass `fa35264c...` | 20, sides randomised, non-image PNG chunks stripped, no key on disk (`blind_r1/`) | **20 / 20** | 20 | Failed decisively. It led to the one targeted surface pass. |
| 2 | surface pass `d959d2f1...` | 20, same protocol (`blind_r2/`) | **19 / 20** | **7** | Still found almost every time, but with far less confidence (7 confident, was 20). |
| - | close-out `719248e4...` | not run | - | - | The user asked for one pass, then move on. |

Section 0.2 lists what still differs, from the round-2 measurer.

## 9. Per-element fidelity: historical (final pass, BEFORE the surface pass)

**This table is superseded by sections 0 and 0.2.** It is kept only to show where the surface pass started.


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
| `Scripts/props/props_lib/blackhat_{spec,camera,geom,atlas,paint,look,gallery}.py` | The library (1.2.1). Close-out: `geom.Hat._fillet` / `fillet_z` / `fillet_lift` / `fillet_rows`, `knot_fold_field` / `knot_lobe`, the band fold drift; `paint.paint_skin` (soft smudge, warped wear zones) and `paint_cloth` (no fan fold lines) |
| `Assets/BlackHat.blend` | Rebuilt from scratch; textures packed |
| `Exports/BlackHat/` | `SM_BlackHat.fbx`, `SM_BlackHat.sockets.json`, `Textures/` (8 maps, 2048) |
| `WorkFiles/blackhat/UnrealCheck/` | Harness, run `0926l` (these bytes, VERIFIED 20 / 20), archives `archive_0926d/` and `archive_0926e_tangent_warning/` |
| `WorkFiles/blackhat/regression/post_black_hat/` | Snapshot of the close-out bytes (this report included), `SHA256SUMS.txt`, `compare_black_hat.py`, `compare_result.json` (black hat plus all three frozen lists) |
| `WorkFiles/blackhat/pre_final_pass/` | Round 1's scripts, exports, renders, blend and report, kept for comparison |
| `WorkFiles/blackhat/final_pass/` | The final pass's patch scripts, hull prototypes and dev-build logs |
| `WorkFiles/blackhat/surface_pass/`, `pre_surface_pass/` | The surface pass's dev loop and iterations, and the state before it |
| `WorkFiles/blackhat/closeout/`, `pre_closeout/` | The close-out's dev render, comparison sheets, probes and tangent diagnosis, and the surface-pass state before it |
| `WorkFiles/blackhat/blind_r1/`, `blind_r2/`, `measure_r1/`, `measure_r2/`, `craft_r1/`, `UnrealVerify_indep_v2/` | The judges', measurers', craft reviewer's and independent verifier's records |
| `Backups/BlackHat_2026-09-25/` | Backup of the close-out: blend, `Exports/BlackHat`, `Renders/BlackHat`, the modules and build script, this report, the report JSON, the Unreal summary, `References/BlackHat` |
| `References/BlackHat/REFERENCE_SPEC.md` | Now with the camera-shift erratum |

**Not touched:**
- the shuriken pack, the smoke bomb (its line sheet was only **read** for the backdrop gradient) and the paused
  paper bomb;
- the generic props_lib modules;
- `ue_import_textures.py` and `Scripts/pipeline/**`;
- the locks (BlackHat is held by claude, and was read only);
- the Unreal editors of the other session (only one-at-a-time commandlets on the validation project, none left running).

No GUI Blender, blender-mcp or running editor was used, and nothing was downloaded.
