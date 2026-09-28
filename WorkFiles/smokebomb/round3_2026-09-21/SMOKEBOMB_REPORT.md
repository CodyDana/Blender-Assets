# SM_SmokeBomb: build report (round 3)

**Date:** 2026-09-21. **Library:** props_lib smokebomb 3.0.0 (smokebomb modules only). **Status:** rebuilt from scratch by
`Scripts/props/build_smoke_bomb.py`.
- All 27 build gates pass, and `qa_check` passes 66 of 66 with **0 boundary edges on every LOD**.
- Unreal 5.8.2 verified the exact exported bytes in fresh processes, 19 of 19 gates, at `/Game/PropsCheck/SmokeBomb_R5`.
- The shuriken pack (78 of 78 files) and the paused paper bomb (6 of 6 exports, the blend, and every paused script)
  match their recorded hashes, at the start and at the end of the round.

> **Fidelity: closer again, still not indistinguishable.** Round 3 answers the round-2 adversary's list:
> - **The outline is the reference's.** Its Fourier shape (harmonics 2-24) is fitted to the reference's, first on the
>   height model and then twice on the LOD0 mesh's own outline. Harmonics n2-n10 now match within 0.06 px.
> - **The top whorl bump** now peaks at 88.75° (+18.4 px). The reference peaks at 88.25° (+18.6 px).
> - **The underside is a wound ball.** No strip is routed through hand-placed back waypoints any more, so the far side
>   is clean bands with no crumpled or pointed ends.
> - **The LOD0 hole is closed.**
> - **No black slits, no square flap, no rope band.**
> - **The cloth is a net of warp floats and weft bars,** with persistent streaks, glints on crossings, and rolled rims
>   that continue down the tape's side.
> - **T4 is geometry,** a hook that crosses the outline at 155°.
>
> Differences a viewer can still see side by side are listed in section 8. The main ones:
> - the whorl's form (a twisted bundle where the reference has a neat pinwheel with a crisp V);
> - a weave that is more regular than the reference's corded floats;
> - softer band-scale shading.

Machine-readable report: `WorkFiles/smokebomb/smokebomb_report.json`. Unreal: `WorkFiles/smokebomb/UnrealCheck/verification_summary.json`.
Round 2's code, report and output hashes are kept in `WorkFiles/smokebomb/build_r3/r2_snapshot/`. Round 2's Unreal
record is kept in `UnrealCheck/r4_archive/`.

---

## 1. The round-2 adversary's list, item by item

Each "now" figure was measured with the round-2 adversary's own instruments, copied unchanged into
`WorkFiles/smokebomb/build_r3/instr/` (`adv2_metrics.py`, `adv2_crevices.py`, `adv2_struct.py`, `adv2_render.py`,
plus `r3_edges.py` = round 2's edge-profile tool).

**The render measured.** `build_r3/ship2/adv2_main.png` is the adversary's independent renderer run on the shipped
FBX and PNGs:
- key light at az 60° / el 64°;
- fill at az −116° / el +4°, at 0.67;
- ambient at 0.42;
- Specular 0.05;
- framing by the spec rule.

The builder's own `Renders/SmokeBomb/smokebomb_reference_view.png` measures the same within a few percent (see
`build_r3/final_crops/measure_builder.txt`).

| Round-2 finding | Round-3 cause and fix | Now (reference → ours) |
|---|---|---|
| **Faceted, polygonal outline.** n9 / n10 were 3-4x the reference; bumpiness +35 %. | **Cause:** a 12-sector core profile plus a degree-8 layer compensation could not hold the outline's shape.<br>**Fix:** new `smokebomb_outline`. The reference outline's Fourier coefficients up to n = 24 are MEASURED with the adversary's instrument and typed in. The core then gets a correction `sum(A_n cos nθ + B_n sin nθ)·(1 − z²)`, solved on the height model's limb and then twice on the LOD0 mesh's own orthographic outline. | n2-n10 (px): 4.58 3.14 1.51 2.44 2.07 1.97 0.67 0.51 0.78 → 4.58 3.13 1.51 2.44 2.04 1.92 0.62 0.45 0.74.<br>rms 1.244 → 1.243 %R.<br>Bumpiness 0.664 → 0.654 %R.<br>Ellipse 1.020 at 125.4° → 1.020 at 125.6°. |
| **No whorl bump at 88°;** the biggest bulge was at 144° instead. | The same outline fit carries the bump. | Top sector (80-100°): +1.30 → +1.18 %R.<br>Largest outward point: +18.6 px at 88.25° → +18.4 px at 88.75°. |
| **Steps in the wrong places;** jagged V-notch at the bottom. | **Causes:**<br>- the outline shape (above);<br>- walls between edge samples 1.5 mm apart projected as ramps at the limb.<br>**Fix:** edge runs are sampled 0.3x finer within 6° of the limb (`EDGE_LIMB_REFINE`), so a step is a jump, not a ramp. The bottom band is now two bands (see "underside" below). | Builder metric (±0.5°): 9 steps (reference 12, gate 8-16) at 11.6, 27.1, 63.2, 92.0, 154.4, 155.0, 197.2, 220.7 and 332.2°. The reference has steps at 11.8, 64.3, 88.4, 155.0, 196.2, 221.2 and 332.0°.<br>Adversary metric (±0.75°): 17 (reference 24).<br>No V-notch or square block at the bottom. |
| **Fewer strips told apart;** 43 deep crevices against 60. | Crevice cores, a plateau crevice and an occlusion ramp are drawn beyond every covering (frayed) edge. The edges of fibres and glints are shaded there too. | Deep crevices (DoG < −0.4): 60 → 58.<br>DoG 3-12 std: −9 %. |
| **Crossings lack occlusion depth.** | As above. | Crevice under BLO: −1.13 → −1.22 (log).<br>CLO: −0.72 → −0.58.<br>ALO: −0.74 → −0.47. |
| **W's twisted edge-on section is smooth.** | The ridge now carries the rolled cord with its thread wraps. It stands half a layer proud (see section 3). | Position unchanged. Wraps visible in 3x crops. |
| **Thin cut sheets, no rolled rims; black slits between rim layers;** p1 +92 %, 1/5 of dark pixels. | **Causes:**<br>- the tape's side (the wall) was painted near-black;<br>- the wall faced the camera on the left limb.<br>**Fixes:**<br>- The wall is now painted as the rolled cord seen from the side, bright at its top and fading down.<br>- Its normal map rolls from the tape's top to the wall's own direction.<br>- The geometry rolls down 0.08 mm into every exposed edge (`HeightModel.roll_mm`).<br>- The rim is the tape's own weave, rolled and brightened, and segmented by thread wraps. | No black slits (3x crop `cmp3x_left.png`).<br>Pixels below 0.03: 2.95 % → 2.10 %.<br>p1: 0.0168 → 0.0244 (+45 %). |
| **Fray too smooth, no loop-wraps.** | **Fix:**<br>- One fray field on the ball: the rim is painted where the edge pulls in, and on the strip beneath where it overhangs.<br>- The rim's segments bulge between wraps.<br>- The wander is 0.2 mm rms at a 1 mm wavelength. | Edge jitter rms (px), reference → ours: WLO 3.0 → 1.6, BLO 2.1 → 1.1, ALO 3.7 → 4.4, CLO 1.1 → 2.0.<br>Wavelength 13-16 → 15-21 px. |
| **T1-T5 dull; T4 absent.** | **Fix:**<br>- T1, T2, T3 and T5 are lighter yarn (0.30 linear), thicker, and lit on the crown, with a soft shadow.<br>- **T4 is a closed 4-sided tube** (`smokebomb_threads`) on LOD0 only: 0.16 mm across, reaching 0.45 mm (6 px) past the outline at 155° and curling back. It has its own island, painted as yarn. | T4 now crosses the outline (`cmp3x_left.png`).<br>T1 and T2 read as light forked threads (`cmp3x_threads.png`). |
| **Weave is a stipple of dashes, not a woven grid.** | **Fix:** the weave is rewritten in `smokebomb_cloth.weave`:<br>- warp floats between over-crossings, with dark breaks where the warp dives under;<br>- weft bars on alternate crossings;<br>- raised knots and glints on under-crossings;<br>- persistent streaks every 0.75 mm along the tape;<br>- curly fibres. | Pitch 3.9-4.0 px (reference 4.0-4.6).<br>hp s3: −7 %. hp s1.2: −14 %.<br>patch p90/p10: 9.79 → 10.05.<br>Sparkle: 9.8 → 9.1 %.<br>p99.9: −11 %. |
| **Colour variation 35-45 % low.** | A two-scale hue mottle on the dye. | Block chroma std: r 0.0070 → 0.0062, b 0.0055 → 0.0051. |
| **Tones:** p10 +14 %, darks lifted. | **Cause:** Specular 0.12 alone lifted the weave's dark cells to stored 0.036 (swatch test).<br>**Fix:** the pin is now **0.05**, in both Blender and `M_SmokeBomb["ue_master"]`. The reference shows no specular (REFERENCE_SPEC 3). | p5 / p10 / p50 / p90: +3 / −2 / 0 / −5 %.<br>Builder metric p10: −5 %. |
| **Strip-to-strip tone:** left rim +39 %, C +28 %, W −11 %. | Tones retuned; walls lit (above). | A +1 %, W −1 %, B −4 %, C +8 %, bottom −8 %, whorl −4 %, U fan −11 %, **left rim +30 %**, centre −16 %. |
| **Quadrant ratios near the limit.** | The fill light at the spec's el +4 (the builder's render too). | UL −11 %, UR −4 %, LL +5 %, LR −4 %. |

**Invented features:**

| Round-2 invented feature | Now |
|---|---|
| **Rope / barber-pole band** on the lower-left limb | **Cause:** wall stripes plus strong rim segments seen obliquely.<br>**Fix:** the wall tone no longer carries segments, and rim segment contrast is reduced.<br>**Left:** where M1 meets the lower-left limb obliquely, the weave's floats still read as coarse bars in 3x crops (section 8). |
| **Square-cut flap** at the left outline (170-200, 510-545) | **Cause:** round 2's waypoints just behind the limb (96° and 158°) bent R2's edge LC across the outline.<br>**Fix:** they are dropped (`smokebomb_layout3.designs`). LC now runs smoothly along the outline. |
| **Black slits** between rim layers | Gone (walls; above). |
| **Bottom notches, V-cut, square block** | Gone.<br>**Cause:** round 2 took D19 and D27 as one edge of one ring. In that ring's frame they form a saw-tooth (phi 19 → 37°, then 27 → 45°).<br>**Fix:** they are now two bands, **Rb1** (D19 as its own edge) and **Rb2** (D27 as its own edge), each on its own great circle, woven under L3/L4 where they climb the front-left. |
| **Faceted silhouette** | Gone (outline fit; finer limb sampling). |
| **See-through hole** in LOD0 | Gone. qa_check reports 0 boundary edges on every LOD. The adversary's own hole check on the shipped FBX finds 0 non-manifold edges and 0 coincident vertices. |
| **Crumpled, pointed tape ends** at the bottom pole | Gone (section 2). The views from below, above and behind (`build_r3/ship1/adv2_{bottom,top,back}.png`, `Renders/SmokeBomb/smokebomb_back.png`) read as clean bands. |
| **Weave as a stipple** | Replaced (above). |

**Engineering regressions:**

| Round-2 regression | Now |
|---|---|
| **Hole** | Fixed. |
| **Constant roughness** | Fixed. ORM.G p5/p50/p95 is 0.847 / 0.878 / 0.902 (fbm plus fibres and rims). |
| **BC mean luminance 0.027** (spec 0.043 ± 0.010) | Now **0.036**, inside the tolerance. |
| **4096 maps chosen without the user** | Still 4096. At 2048 the islands pack at 7.8 px/mm, under the 13.3 px/mm the reference framing needs. **This is the user's call** (study question 3, section 9). |

## 2. The far side (`props_lib/smokebomb_layout3.py`, new)

**The front is round 2's.** It uses the same REFERENCE_SPEC control points, widths, order and woven ranks, with three
changes:
- **R2** no longer has the two waypoints behind the limb.
- **W's** edge-on ridge stands half a layer proud instead of a full layer.
- **Rb** is split into Rb1 and Rb2.

**The far side is new.**
- Every knot on the visible side and just behind the limb (camera z ≥ −0.26) is kept.
- Every far-side waypoint (`back_path` mirror points and limb points) is dropped.
- Across the unseen gap, each edge eases from where it leaves the limb to the strip's own **base circle** (its frame
  circle at its back width) and back.

So behind the ball every strip is a smooth band of near-constant width. The report lists each strip's base under
`layout.far_side`.

**Checks.**
- Analytic top-strip maps from six directions (`build_r3/view/tm3*_*.png`) show no bare core.
- The shell finds 262 runs, 178 junctions and 89 regions, with 0 seams and 0 problems.

## 3. Geometry

**Height model (`smokebomb_spec.height_params`).**
- **t = 0.60 mm** per layer. Round 2 used 0.45 mm plus a 0.08 mm bead.
- A **0.08 mm roll** into every exposed edge over 0.6 mm, with no bead.
- The visible step where an edge crosses the limb square-on is ~0.52 mm, which is 6.9 px (REFERENCE_SPEC 5: 4-8.5 px).
- 0.60 mm is the thickest tape LOD1 can follow within its 1.5 mm budget (0.62 measured 1.51 mm).

**Outline fit (`smokebomb_outline`).**
- Core 34.463 mm.
- The final mesh outline has a mean of 35.000 mm and a harmonic error of 0.001 mm rms up to n = 24.
- The residual above n = 24 (the tape's steps) is 0.125 mm rms.

**Limb sampling.**
- Interior and runs: 0.42x within 17° of the limb (round 2).
- Edge runs: a further 0.3x within 6° of the limb (new).

**LODs.**

| LOD | Triangles | Band | Built as | Two-sided deviation from LOD0 |
|---|---|---|---|---|
| LOD0 | **6,398** | 4,000-6,500 | Shell with 2,230 wall triangles, plus the 44-triangle T4 hook | — |
| LOD1 | **2,000** | 1,200-2,000 | Geodesic frequency 10. Each vertex takes the MEAN height within a third of the vertex spacing, and its UV corners are kept on the tape face. | 1.47 mm (budget 1.5) |
| LOD2 | **500** | 400-800 | Geodesic frequency 5, the same rules | 2.15 mm (budget 3.0) |

**Why LOD1 changed.** Round 2's LOD1 read wall texels where a corner fell past the strip's edge; those were the
adversary's "black ragged blotches". The corner clamp removes them. A few clamped corners show mildly smeared weave
close up.

**Bounds.**
- Screen sizes 1.0 / 0.0746 / 0.0261 (pack rule × 37.305 / 50). They switch at 0.889 m and 2.541 m.
- AABB 69.88 × 70.22 × 71.53 mm. The top stack at the whorl makes Z the longest axis.

## 4. Textures and UVs

| Map | Content |
|---|---|
| **T_SmokeBomb_BC**, 4096, sRGB | The net of floats and weft bars, streaks, fibres and glints. Rolled rims with wraps, plus the rim's side on the wall. Crevice cores, crevices and occlusion beyond covering edges. Loose threads T1, T2, T3 and T5. The T4 tube's own island. Mean linear luma 0.036. |
| **T_SmokeBomb_ORM**, 4096, linear | R = a Cycles AO bake of LOD0 × cavity (p50 0.86), for Unreal's AO input only. G = roughness 0.85-0.90. B = 0. |
| **T_SmokeBomb_N**, 4096, DirectX | Thread relief. The rim's round profile. The wall's roll. Shoulders (0.2 mm) and dips toward covering edges. |

**UV0.** 90 islands at 156.7 px/cm with 32 px padding: 89 regions plus the T4 tube. qa_check reports 0 overlaps, and
there are 0 collapsed or mirrored triangles on every LOD.

**UV1** is generated by Unreal. It has **0 overlapping texels at 1024 and 2048 on every LOD**.

## 5. Collision, sockets, pivot

- **Collision:** `UCX_SM_SmokeBomb_LOD0_00`, a 32-vertex pentakis dodecahedron with all faces tangent to r_max =
  37.603 mm. That is 1.064 × the r_max sphere. It contains every LOD, including the T4 tip.
- **Sockets:** `Grip` and `Burst` at the centre. They are Empties plus the sidecar.
- **Pivot:** the ball centre.

## 6. Unreal 5.8.2 (fresh processes, exact bytes)

- **Harness:** `WorkFiles/smokebomb/UnrealCheck/run_unreal_checks.sh`, unchanged. The log is `run_r5.log`.
- **Run order:**
  - A second Blender process counts the FBX first: 6,398 / 2,000 / 500 triangles and a 60-face hull.
  - Then 5 commandlets run one at a time, each exiting before the next.
  - Every exit code is 0, with **0 Warning or Error lines**.
  - A Blender round trip follows, then the UV1 check.
- **Result:** no Unreal process was left running. None was running before (checked).

| Gate | Result |
|---|---|
| LOD triangles 6,398 / 2,000 / 500 equal the build and the second Blender import | pass |
| One convex hull; contains LOD0 in engine space (round trip) | pass |
| Two sockets at scale 1 | pass |
| Bounds, and bounds sphere 3.73054 cm = the radius the screen sizes used | pass |
| Screen sizes 1.0 / 0.0746 / 0.0261 applied from the sidecar | pass |
| Lightmap UV on every LOD; UV1 overlap 0 at 1024 and 2048 | pass |
| One material slot; Nanite off | pass |
| BC sRGB TC_Default, ORM linear TC_Masks, N TC_Normalmap with flip green OFF; all 4096, **TMGS_FROM_TEXTURE_GROUP**, with mips. Imported with the props importer and verified in a fresh process; the verified hashes equal the shipped PNGs. | pass |
| Round trip: triangles and positions identical on every LOD | pass |
| SHA-256 `619cede7dcb3a39de3a8bcc8843ab175673a25745e2f6b0bd1d0eca14e83256e` is the same in the report and in passes 1, 2 and 3 | pass |

## 7. Fidelity gates (the builder's instrument, `smokebomb_metrics`, on `smokebomb_reference_view.png`)

**The render.**
- LOD0 with the shipped baked maps, through `smokebomb_material`.
- Orthographic camera at 1.351 D, 1254 px, 512 samples, filter 1.5.
- The spec's key and fill (el +4), sun angle 40°, and ambient 0.42.

**Gates F1-F9: all pass.**

| Gate | Result |
|---|---|
| F1 diameter | 927.5 px (−0.1 %) |
| F2 centre | (626.8, 628.4) |
| F3 circularity | 1.24 %R |
| F4 steps | 9 (8-16) |
| F5 p10 / p50 / p90 | −5 / +1 / −4 % |
| F6 quadrants | inside ±15 %: UL −9 %, UR −1 %, LL +11 %, LR −1 % |
| F7 chromaticity | (0.380, 0.324, 0.297) |
| F8 warp pitch | 3.85 px (3.4-5.5) |
| F9 sparkle | 3.7 % (reference 4.2 %; band 3-5.5 %) |

**3x crops.** `WorkFiles/smokebomb/build_r3/final_crops/cmp3x_{belt,whorl,left,bottom,threads,rightlimb}.png`
show [reference | shipped render] at the same crop.

## 8. What still looks different (for the next round)

Judged side by side at 1x and on the 3x crops:

1. **The top whorl.** U1's rolled edge curls over the top as a broad S-band, so the whorl reads as a twisted bundle.
   The reference's is a neat pinwheel with a crisp V apex and a thin rolled ridge. The outline bump matches; the
   surface form does not.
2. **The weave.** It is a clean, regular net of thin lines.
   - The reference reads as denser, corded floats with curly fibres.
   - Anisotropy is 0.54-0.59, against the reference's 0.31-0.57.
   - At the adversary's "bottom" patch (600, 950), where the tape is seen obliquely, the pitch measures 2.7 px, below
     3.4.
   - Fine contrast (hp s1.2) is −14 %.
3. **Band-scale shading.** The reference's bands look thicker and more tube-like, with brighter crowns. Ours are
   flatter.
   - Normal-map shoulders stronger than 0.2 mm painted a dark stripe along every edge, so they were reduced.
   - The upper-right fan is −11 % and the centre patch −16 %.
4. **The left rim family.**
   - Concentric padded arcs with rolled edges; no slits and no flap.
   - One Z-kink remains in R_in's upper boundary near (330-370, 400).
   - The left-rim patch is +30 % lighter than the reference's.
5. **The lower-left limb (330-480, 980-1060).** Where M1 meets the silhouette obliquely, the weave's floats read as
   coarse dark/light bars in 3x crops.
   - This is a much weaker version of round 2's "rope".
   - It is the texture seen obliquely, not a modelled cord; the UV stretch there is ≤ 1.24.
6. **The outline's fine scale.**
   - Steps are fewer on the adversary's ±0.75° metric (17 against 24).
   - Fine 1-3 px scallops remain along the bottom, 250-310°.
7. **Darkest tones.** p1 is +45 %: the reference's deepest gaps are darker.
8. **Edge character.**
   - W's and B's lower edges wander about half as much as the reference's.
   - The crevice under W is deeper (−0.84 against −0.54 log).
   - A's crevice is shallower (−0.47 against −0.74).

## 9. Known gaps and open questions

- **Visual differences:** section 8.
- **Decisions this round that the user should confirm:**
  - **Specular pinned at 0.05.** It was 0.12. The reference shows no specular, and 0.12 lifted the dark cells. The UE
    master spec was updated to match.
  - **T4 as geometry.** This partly answers study question 2: T4 only; T1, T2, T3 and T5 stay in the texture.
  - **LOD0 at 6,398 triangles.** This is study question 4: it is inside the 6,500 ceiling but above the 5k guideline.
- **Study questions still open for the user:**
  - 1: the 70 mm scale.
  - 3: **2048 or 4096 maps.** 4096 was kept because 2048 packs at 7.8 px/mm, under the 13.3 px/mm the reference
    framing needs. This was not settled by the user.
  - 5: AI provenance. No reference pixel reaches a mesh, a UV or a map. The reference is read only by the side-by-side
    and the metrics. The outline's Fourier coefficients are a typed-in MEASUREMENT of it, as the REFERENCE_SPEC control
    points were. The Fab declaration is the user's call.
  - 6: burst on impact, no fuse.
  - 7: the 32-vertex hull tumbles.
  - 8: approve the back view (`Renders/SmokeBomb/smokebomb_back.png`).
- **No Unreal master material asset is authored** (a pack-wide gap). Its spec is `M_SmokeBomb["ue_master"]`: Default
  Lit, BC straight, AO from ORM.R, **Specular 0.05**, no sheen.
- **Physics** (0.12 kg, CCD on) is recorded, not applied.
- **Inward-facing count on LOD0: 24.** One is a shell boundary sliver. The other 23 are T4-tube faces: they face out from the tube, but away from the ball's centre test. The count is informational; qa_check passes.
- **Scratch** in `WorkFiles/smokebomb/build_r3/iter/`, `swatch/` and `dev/` can be regenerated and deleted.

## 10. Frozen assets

**Evidence.** `WorkFiles/smokebomb/build_r3/frozen_check_start.txt` (15:34) and `frozen_check_end.txt` (18:32), also
copied to `build/frozen_check.txt`.

**Shuriken.** All 78 entries of `WorkFiles/shuriken/regression/post_kunai_plain/SHA256SUMS.txt` are identical.

**Paper bomb.**
- `SHA256SUMS_exports.txt` reports 6 of 6 OK.
- `PaperBomb.blend` equals the paused snapshot (`7d520032…`).
- All 17 paused scripts are identical.

**This round changed only smokebomb files.**
- **New modules:** `smokebomb_outline.py`, `smokebomb_layout3.py`, `smokebomb_threads.py`.
- **Edited modules:** `smokebomb_cloth` (rewritten), `_shell`, `_spec`, `_material`, `_render`, `_gallery`, and
  `build_smoke_bomb.py`.
- **Untouched:** `smokebomb_layout` (round 2's front is imported from it unchanged) and the generic modules.

Codex's BlackNunchucks files, any GUI Blender and DemoGame_1 were not touched.

## 11. Files

**Scripts.**
- `Scripts/props/build_smoke_bomb.py`
- `Scripts/props/props_lib/smokebomb_*.py`

**Asset.** `Assets/SmokeBomb.blend` (`b6f8a8a0…`).

**Exports (`Exports/SmokeBomb/`).**
- `SM_SmokeBomb.fbx` (`619cede7dcb3a39de3a8bcc8843ab175673a25745e2f6b0bd1d0eca14e83256e`)
- `SM_SmokeBomb.sockets.json` (`97183ad6…`)
- `Textures/T_SmokeBomb_BC.png` (`cbe6a859…`), `_ORM.png` (`b842d826…`), `_N.png` (`a672afa2…`)

**Renders (`Renders/SmokeBomb/`).** `smokebomb_reference_view.png`, `smokebomb_side_by_side.png`, `smokebomb_back.png`,
`smokebomb_hero.png`, `smokebomb_top.png`, `smokebomb_wire.png` and `smokebomb_lods.png`. All come from the baked
maps.

**Evidence.**
- `WorkFiles/smokebomb/build_r3/logs/build_full_2.log`
- `build_r3/final_crops/` (3x crops, `measure_adv.txt`, `measure_builder.txt`, `regions.txt`, `edges.txt`)
- `build_r3/ship2/` (the independent adversary-style renders of the shipped bytes)
- `build_r3/instr/` (the adversary's instruments, copied)
- `UnrealCheck/verification_summary.json` and `UnrealCheck/run_r5.log`
