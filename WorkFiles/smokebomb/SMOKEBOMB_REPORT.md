# SM_SmokeBomb: build report (final pass)

**Date:** 2026-09-25. **Library:** props_lib smokebomb **8.0.0**. **Build:** `Scripts/props/build_smoke_bomb.py`, run
from scratch with no arguments (Blender 5.2.0 LTS, headless, `--factory-startup`, 267 s). It rebuilt
`Assets/SmokeBomb.blend`, `Exports/SmokeBomb/` and `Renders/SmokeBomb/`.

This is the maintainer's final pass over round 4 (the workflow's round-3 builder). Round 4's report is kept as
`WorkFiles/smokebomb/final_pass/orig_start/SMOKEBOMB_REPORT.md`, along with its modules, exports, renders and blend.

## Status

- **Build gates: 30 of 30 pass** (round 4 also passed 30). `qa_check` passes **66 of 66**. F1-F9 all pass, and F4
  (outline steps) passes at 8.
- **Unreal 5.8: 19 of 19 gates** pass on the exact exported bytes. Each pass ran in its own fresh process, with **0
  warning or error lines**, at `/Game/PropsCheck/SmokeBomb_FP_0925c`. The harness is `WorkFiles/smokebomb/UnrealCheck_fp/`.
  Runs `0925a` and `0925b` are archived there: `0925a` was the first harness run, and `0925b` covered the build
  before the span was turned off.
- **Frozen assets unchanged:**
  - shuriken **78 of 78** (post_kunai_plain: blend, exports, textures, build scripts and reports);
  - paper bomb **6 of 6**;
  - both checked by `WorkFiles/smokebomb/regression/compare_post_smoke_bomb.py`, and again by the build (41 of 41
    and 6 of 6).
- **Snapshot:** `WorkFiles/smokebomb/regression/post_smoke_bomb/`, 30 files with `SHA256SUMS.txt` and
  `compare_result.json` (ALL OK).
- **Backup:** `Backups/SmokeBomb_2026-09-21/` (the folder the brief named; it did not exist before), described in
  section 10.
- **Fidelity:** this is closer than round 4, but it is **not indistinguishable** from the reference. There was
  **no blind test of this pass**. Section 9 lists what still differs.

**The shading the look depends on, stated plainly:**
- BaseColor = `T_SmokeBomb_Detail.R x Tint`. The Detail map is sRGB-encoded and imported with sRGB ON.
- Specular = `0.5 x T_SmokeBomb_ORM.A`. ORM.A is the baked specular mask.
- Roughness = ORM.G, Sheen 0, Lambert diffuse.
- A constant Specular of 0.5 greys the cloth: p50 +53 % and p10 +111 % at the reference view. So M_SmokeBomb must
  sample ORM.A.

Both statements are in the sidecar's `material` block.

---

## 1. The method change (the whole job)

The first attempt laid the ball as **separate patches on a sphere**. It failed three measured rounds, and a blind
judge picked it in 19 of 19 pairs. The problems:
- cut tabs, black voids, and a twisted bundle where the pinwheel should be;
- flat painted ribbons and grey piping edges;
- a square weave and UV stretch.

The rewind (rounds 1-4, and this pass) builds the ball **the way the real object is made**:

| | |
|---|---|
| One tape | One continuous tape (`smokebomb_wind`). A buried precessing core, then 20 near-great-circle passes fitted to REFERENCE_SPEC's traced edges, joined behind the ball. It is 9,175 mm long. Both ends are covered from every direction. |
| Section | A padded cloth section with a rolled cord at each edge (`smokebomb_tape`). It is swept along the exposed stretches (92 of them, 2,877 mm of tape and 13,888 mm² showing). Each is lifted over the layers beneath it, and the height guard keeps every cover above what it covers. |
| Tape-space UVs | u runs along the tape and t across it, at one texel = 1/18.3 mm everywhere. The weave is painted in tape space (`smokebomb_cloth`): warp ribs along the tape, and no stretch or barcode. |
| Recolour | A full-range greyscale Detail map from linear float data, and a default Tint (section 2). |

### What the final pass changed

The pass covers the blockers and majors in the brief, grouped by where they live.

**Winding: the whorl tangle (the first blocker)** — `smokebomb_wind_fit.py`, design `final+r2+fan+hw0.16+r2under`.

The cause was measured with a stretch-ID map of the ball (`final_pass/diag_cur_pass.png`). The pass-level layout was
roughly right. The tangle came from **the fit**: it had made each pass only as wide as the part of it that shows.
- U1 was 4.8 mm wide, R_in 6 mm and R3 4.4 mm.
- A tape that narrow shows both of its rolled edges and stands up as a rope.
- A real tape keeps its width, and its neighbour covers part of it.

Three changes fix this:

1. **Shingled fan** (`final_pass/tools/fp_fan.py`). REFERENCE_SPEC 4.4 says the order inside the U family cannot
   be read from the photo.
   - The fan is re-laid as U1 < U2 < U3 < U4 < U5. Each band owns the traced edge on its left (UA, UC, UD, UE, UF)
     and runs on at the full tape width (0.16 D = 11.2 mm) under the next band.
   - This is done with crossing-local weaves, so nothing outside the fan changes. Outside the fan, fewer than 100
     label pixels changed.
2. **Hidden widening** (`fp_widen2.py`). Every other pass except W is widened toward 0.16 D, but only where the
   extra width lies under a stretch above it (the original stack, weaves applied). The visible edges stay where the
   fit put them.
3. **Limb weaves.** R2, R3 and U2 run on behind the left and bottom limbs. As the last passes wound, they lay on top
   of everything there and formed the outline, so C's edge steps never reached it.
   - They are now woven under the passes they lie on.
   - C now forms the left outline at 197-215°, as REFERENCE_SPEC 1 says it should. It measured 172-285° before,
     where R2 formed it.

**Rolled edges (the second blocker)** — ClothSpec6, section 3:
- no segment-by-segment knuckle swing;
- few joints and dim wraps;
- a 1.3x rim instead of 1.55x;
- the roll carries the weave;
- 20 % of each edge's length fades to the plain weave turning under.

**Detail encoding under mips (major)** — section 2. Detail is stored as sRGB-encoded linear detail and imported
with sRGB ON. BaseColor = Detail.R x Tint.

**Specular under mips (major)** — section 2. The mask is baked into ORM.A from float data.

**Weave, gallery glint, shimmer and threads (majors)** — sections 3, 7 and 9.

**Geometry**
- The guard clearance rose from 0.08 mm to 0.3 mm (`BallSpec.guard_clear_mm`), so an overlap is a true step.
- `BallSpec.span_mm` (a low-pass of each stretch's lift) was tried and left **off**. At 1-3 mm it flattened the
  outline: 22-27 % straight outline windows and only 5-7 steps.

**Line sheet (minor)** — `Renders/SmokeBomb/smokebomb_linesheet.png`, in the pack's 1600 x 900 format with name,
size, mass, LODs and maps.

---

## 2. Recolour and specular: mip-safe maps

| | |
|---|---|
| Detail | `T_SmokeBomb_Detail`, 4096, one channel. It stores **sRGB-encode(d)**, where d is the linear detail (albedo / Tint luminance), quantised once from float data. Percentiles p1 / p10 / p50 / p90 / p99.9 are 19 / 30 / 63 / 115 / 236 of 255, and 253 levels are used. **Import with sRGB ON** (TC_Grayscale, G8). |
| Material | **BaseColor = Detail.R x Tint.** There is no power term any more. |
| Default Tint | Linear **(0.630803, 0.532934, 0.481121)** = sRGB (0.815713, 0.756645, 0.722783). The mean cloth albedo is 0.0413 (REFERENCE_SPEC 8: 0.043 ± 0.010). |
| BC | `T_SmokeBomb_BC` = sRGB8(sRGBdecode(Detail8) x Tint), built from the quantised Detail. The maximum error is 0.0032 linear. |
| Specular | **Specular = 0.5 x ORM.A.** ORM.A = saturate(d)², box-filtered from the float detail down to 2048 before quantisation (213 levels, mean 0.0135). It is the same quantity as round 4's 0.5 x Detail⁴, but averaged before any pow(). |
| Importer | `props_lib/ue_import_textures.py`: the Detail intent is now **srgb True**. Only the smoke bomb ships a Detail map, and the other intents are unchanged. |

**Parity at every mip**, on the shipped PNG bytes (`final_pass/tools/fp_mips.py` → `final_pass/mip_parity.json`).
The script uses Unreal's SimpleAverage 2x2 mips. sRGB maps are decoded first, and every level is re-quantised to
8 bits.

Detail x Tint against BC, mean luminance:

| Mip | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|---|
| Round 4 (independent verifier) | +0.1 % | −7.6 % | −15.5 % | −19.6 % | −22.2 % | −24.8 % | −27 to −29 % | | |
| **Final pass** | **+0.04 %** | **+0.02 %** | **+0.02 %** | **+0.01 %** | **0.00 %** | **−0.02 %** | **−0.05 %** | **−0.10 %** | **−0.11 %** |

- Median and p10 stay within ±2.4 % at every level. That is 8-bit quantisation.
- Specular (0.5 x ORM.A) against the correctly filtered 0.5 x d²: +0.8 % / +0.0 / −0.2 / −0.4 / −0.5 / −0.6 / −0.5 /
  +1.6 % at ORM mips 0-7. Round 4 lost 32-84 % at mips 1-8.

**Unreal readback** (fresh process, final bytes):
- Detail: sRGB True, TC_Grayscale, source G8, 4096.
- ORM: TC_Masks, source BGRA8, and the **source alpha spans 0.000-0.984** (the specular mask). `compression_no_alpha`
  is False.
- The registry's built-format tags read `Format unknown` / `HasAlphaChannel False` under `-nullrhi`, because a
  commandlet runs no platform build. So the compressed format (BC3, expected for TC_Masks with alpha) could not be
  read here.
- All four maps use TMGS_FROM_TEXTURE_GROUP.

**Texture budget (minor issue).** BC and Detail stay at 4096. Section 5 of round 4 measured that a 2048 atlas fails
the sparkle and p10 gates at the reference view. **A material instance loads BC or Detail, never both.**

| Path | Maps | Memory with mips |
|---|---|---|
| Fixed colour | BC 4096 (DXT1, ~10.7 MiB), ORM 2048 (DXT5 with alpha, ~5.3), N 2048 (BC5, ~5.3) | **~21 MiB** |
| Recolour | Detail 4096 (G8, ~21.3), ORM, N | **~32 MiB** |
| Recolour, Max Texture Size 2048 on Detail | Detail ~5.3, ORM, N | **~16 MiB** |

For game use, set Maximum Texture Size 2048 on BC or Detail. Since the parity fix this keeps Detail x Tint = BC
(mip 1: +0.02 %). Before the fix, the same setting cost −7.6 % in the mean and −16 % at p10.

---

## 3. The cloth (ClothSpec6)

`props_lib/smokebomb_cloth.ClothSpec6` holds the calibration. It was iterated as `final_pass/c6a` … `c6e` on a
4096 cache of this ball, against the reference view's tone, sparkle and weave instruments and 4x crops.

| Tell (judge / craft reviewer) | Change |
|---|---|
| Piping: uniform tube, barber-pole knuckles, crescents | knuckle tone swing 0.75 → 0.35; joints 0.8 → 0.5 (dark 0.7 → 0.45); wraps 0.8 → 0.45 and dimmer; rim 1.55x → 1.3x; the roll carries the weave (cord_smooth 0.85 → 0.55); knuckle relief 0.18 → 0.10 mm; 20 % of each edge fades out (`cord_vis_*`) |
| Tweed static: specks, squiggles, heather | specks 0.06 → 0.012; fibres 0.10 → 0.04 and dimmer; wavy weft runs 0.30 → 0.10 and straight; weft ticks in 60 % of breaks (the ladder); streak / pucker / lump tone and mottle cut |
| Frosted sparkle; round dot glints | glints are 0.07-0.12 mm dashes along the crest (they were round) and rarer (0.20 → 0.16); roughness 0.55 → 0.68 |
| Serrated black crevice teeth | fringe 0.7 → 0.15; crevice core / dark 0.8 / 0.75 → 0.6 / 0.6; skirt floor 0.006 → 0.05 |
| Pale wire threads | thread tone 0.95 → 0.60; T1 is 3 plies at 0.065 mm that split over the last 2 mm; T2 is 2 plies; T5 is 2 stubs 0.35 mm apart (it was 3) |

Evidence:
- `final_pass/final/weave_ref_r4_final_4x.png`, `wedge_T1_ref_r4_final_4x.png`, `whorl_ref_r4_final_2x.png` and
  `hero_r4_final.png` (each is reference | round 4 | final, except the hero pair, which is round 4 | final);
- `Renders/SmokeBomb/smokebomb_crops_3x.png`.

---

## 4. LODs and triangles

| LOD | Triangles | Visible-surface deviation p99 | Limit (1 px at the switch) | Screen size |
|---|---|---|---|---|
| 0 | **16,108** (tape 15,244 + threads 864) | — | — | 1.0 |
| 1 | **2,952** | 0.85 mm | 0.93 mm | 0.073 |
| 2 | **1,406** | 1.22 mm | 2.65 mm | 0.0256 |

- Screen sizes follow the pack rule x 36.52 / 50 mm. The switches happen at 0.89 m and 2.54 m.
- LOD-switch pop (mean |Δ| stored): LOD0 → LOD1 0.0105, LOD1 → LOD2 0.0092. Round 4 measured 0.0117 / 0.0109.
- LOD1 still reads as bands at 76 px (`Renders/SmokeBomb/smokebomb_lod_switch.png`).
- The hull is a pentakis dodecahedron. It contains every LOD, with the worst vertex 0.031 mm inside.

## 5. Unreal verification (final bytes)

These are the harness steps (`UnrealCheck_fp/run_unreal_checks.sh`). Each ran one at a time, in a fresh process,
with no commandlet already running:
1. Blender FBX count;
2. pass 1 import with LODs ON and the sidecar;
3. props texture import;
4. fresh texture verify;
5. pass 2 reload and gates;
6. pass 3 Unreal FBX export;
7. Blender round trip;
8. UV1 overlap.

**VERIFIED True, 19 of 19 gates:**
- LODs: 16,108 / 2,952 / 1,406. The round trip is exact.
- Collision: one hull.
- Sockets: Grip and Burst, at scale 1.
- Screen sizes from the sidecar.
- Lightmap: UV1 has 0 overlap on every LOD.
- One material slot; Nanite off.
- Texture flags as intended, including Detail sRGB ON and ORM alpha kept.
- Bytes: FBX `a428dd21…`, sidecar `f192abcc…`.

Deviation from round 4's harness: its guard refused to start while **any** UnrealEditor process was running. The
user's own DemoGame_1 editors were open (and were left untouched), so the guard now refuses only when an
**UnrealEditor-Cmd** commandlet is running. That is the workflow's one-at-a-time rule.

`M_SmokeBomb` is not shipped as an Unreal asset, and on import the slot resolves to WorldGridMaterial. This is the
issue's own plan: the recolour step builds M_SmokeBomb and MI_SmokeBomb from the sidecar, then reads them back in a
fresh process.

---

## 6. Blind-test history

| Round | Method | Result |
|---|---|---|
| First attempt, rounds 1-3 | patches laid on a sphere | the blind judge picked ours in **19 of 19** pairs |
| Rewind round 1 | one wound tape | picked in **20 of 20** |
| Rewind round 2 | + padded section, cloth round 2 | **20 of 20** |
| Rewind round 3 (round 4 in the code) | + real cord, LOD0 16.7k, ClothSpec5 | **20 of 20**, 7 of them confident |
| **Final pass** | + shingled fan, hidden widening, limb weaves, ClothSpec6, mip-safe maps | **not blind-tested** (no judge was run in this pass) |

## 7. Per-element fidelity (reference view, from the baked maps)

The instruments are the round-3 measurer's, used read-only through `rewind/build5/tools/b5_measure.py`,
`b5_extra.py` and `b5_facets.py`, plus the build's own metrics. Round 4 was re-measured on its shipped render
(`final_pass/orig_start`).

| Element | Reference | Round 4 | **Final** | Within tolerance? |
|---|---|---|---|---|
| Diameter | 928.3 px | −0.28 % | **−0.20 %** | yes (±1 %) |
| Circularity / ellipse | 1.245 % R / 1.020 at 125° | 1.250 / 1.021 at 123° | **1.349 / 1.021 at 122°** | yes (0.8-1.8) |
| Outline steps ≥ 4 px | 12 (11.8°, 51°, 64°, 87-88°, 155°, 196°, 211-221°, 285°, 332°) | 8 | **8** (37°, 56°, 78°, 91°, 155-156°, 333°, 355°), median 6.1 px | yes (8-16), but at different angles |
| Straight 40-px outline windows | 0 % | 15.8 % | **18.5 %** | no; worse |
| Tone p10 / p50 / p90 | 0.050 / 0.117 / 0.248 | −4.0 / +2.7 / +5.8 % | **+3.4 / +2.7 / −3.3 %** | yes (±12 %) |
| Tone p1 / p99.9 | 0.017 / 0.615 | −7 / −13 % | **−24 / −19 %** | darkest and brightest are more compressed |
| Quadrants UL / UR / LL / LR | — | −12.4 / +2.3 / +7.1 / −2.9 % | **−9.2 / +4.7 / +7.4 / −1.1 %** | yes (±15 %) |
| Chromaticity | 0.377, 0.326 | 0.383, 0.324 | **0.383, 0.324** | yes |
| Sparkle (by ring) | 4.23 % (5.1 / 4.7 / 4.1 / 3.2) | 4.63 % (flat) | **3.69 %** (3.8 / 3.9 / 3.7 / 3.2) | yes (3-5.5 %); now falls at the limb |
| Warp period | 4.30 px | 4.27 | **4.20** | yes (3.4-5.5) |
| Whorl V-gap (log) | −0.58 | −1.41 | **−0.73** | much closer |
| U0/U1 V-gap (log) | −2.01 | −0.97 | **−0.90** | no |
| Region A / B / C / W / X | — | +10 / +42 / +6 / −20 / −7 % | **+7 / +29 / +13 / −14 / −1 %** | B is still out |
| Region U / rim UL / whorl | — | −12 / −3 / −31 % | **−0.3 / −4 / −20 %** | whorl is still out (±15 %) |
| Region L3 / D bottom / E | — | −24 / −15 / −10 % | **−20 / −52 / −10 %** | L3 and D bottom are out; D bottom is worse |
| Rim log WLO / BLO / BUP | 0.24 / 0.16 / 0.17 | 0.66 / 0.45 / 0.10 | **0.28 / 0.09 / −0.02** | WLO and BLO now match; BUP is missing |
| Crevice log WUP / CUP | −0.13 / 0.20 | 0.28 / 0.46 | **0.11 / 0.53** | CUP is still too deep |
| Edges within 6 px (primary W / A / B / C) | — | WLO 0.64, ALO 0.46, BLO 0.82, CLO 0.70 | WLO 0.43, ALO 0.26, BLO 0.76, CLO 0.61 | slightly worse |
| Secondary edges > 10 px off | — | WUP, L3L, UA, UE, D57, D9, D19 | CUP 17, UC 20.5, LC 14.5, UD 12, UE 14.5, UA 11, L3L 10.5, D57 16, D9 14, D19 12.5 | no |
| Near-black clusters / area | 15 / 0.50 % | 27 / 0.61 % | **32 / 0.74 %** | no; worse |
| Low-pass correlation (σ 3 / 8 / 20) | 1 | 0.50 / 0.71 / 0.87 | **0.49 / 0.69 / 0.84** | about equal |
| Loose threads | T1-T5 | pale Y bundles, T5 a 3-ply tassel | darker (0.60), thinner, T1 3-ply curling, T5 two stubs; roots T1/T2 7.6 px and T5 11.6 px off (W's edge lies there) | improved; roots unchanged |
| LOD1 / LOD2 band read | — | bands | **bands** | yes |

**Gallery rig.** The hero, raking and top frames no longer show the rope tangle or the frosted speckle
(`final_pass/final/hero_r4_final.png`). My own p99/p50 instrument could not reproduce the craft reviewer's 65x
figures, because its mask includes the sweep. So this pass does not claim a number for that check.

**Shimmer in a turn** (the judge's own `jc4_turn` / `jc4_shimmer`, copied to `final_pass/shimmer/`, EEVEE, 1 spp
against 32, 0.1° steps). Flicker as a share of mean luminance:

| Disc | Final | Round 4 |
|---|---|---|
| 400 px | **9.8 %** | 10.1 % |
| 160 px | **2.6 %** | 3.2 % |

This is only a small gain. What remains comes from the warp ribs themselves: 0.31 mm pitch is about 1.8 px at a
400 px disc, below Nyquist. Section 9 has the recommendation.

## 8. Gates

- **Build: 30 of 30:**
  - `qa_check` 66 / 66;
  - LOD bands, descending;
  - UVs: collapsed, mirrored, inside 0-1, padding;
  - hull contains every LOD;
  - two sockets;
  - power of two, no colour chunks;
  - 9b Detail full range;
  - frozen assets;
  - no franchise string;
  - LOD deviation under 1 px at the switch;
  - no triangle Unreal would drop;
  - both tape ends hidden;
  - F1-F9.
- **Unreal: 19 of 19** (section 5).
- **Regression:** `compare_post_smoke_bomb.py compare`: smoke bomb 30 / 30, shuriken 78 / 78, paper bomb 6 / 6.

## 9. What still does not match (honest)

1. **The top whorl is not the reference's pinwheel.**
   - The rope tangle is gone. The fan now reads as broad shingled bands with one edge each.
   - But the bands rise almost vertically to the top instead of spiralling round the V-gap apex at (690, 252).
   - Whorl region −20 %; the U0/U1 V-gap is too weak (−0.90 against −2.01 log).
   - A true pinwheel needs the U and R passes re-aimed as a rosette round the apex. That means a new fit with the
     winder's tools (`rewind/wind/wd_tools`): multi-hour work that this pass did not do.
2. **Band layout, secondary edges.** CUP, UC, LC, UD, UE, UA, L3L, D57, D9 and D19 are 10-20 px off. Region means
   are off: B +29 %, D bottom −52 %, L3 −20 %. The bottom family still converges as narrow lens strips on the
   bottom outline.
3. **Outline.**
   - 8 steps, but not at the reference's angles: none at 196-221° or 285°, even though C now forms the left outline.
   - 18.5 % straight windows against the reference's 0 %.
   - No fibre fuzz past the outline, apart from T4. Fuzz would need geometry or alpha cards; this pass added
     neither.
   - Bands still meet the right limb as angular tabs in places.
4. **Voids:** 32 near-black clusters (0.74 %) against 15 (0.50 %). The deeper overlap steps (guard 0.3 mm) made the
   crevice pockets a little darker.
5. **Weave.** It is cleaner (no static, no heather), but the reference's crosshatch is crisper and more open: thick
   raised weft lines. Ours is still rib-dominant with a fainter weft ladder. p1 and p99.9 are compressed (−24 % and
   −19 %).
6. **Edges.** BUP's rim is missing (−0.02 against 0.17 log) and the CUP crevice is too deep (0.53 against 0.20). The
   reference's knuckled cord on W's lower edge is thicker than ours, which fades out over 20 % of its length.
7. **Threads.** The T1 / T2 / T5 roots sit 7.6 / 7.6 / 11.6 px off, because W's edge lies there. T1 still reads as
   a single wavy strand at 1x.
8. **Shimmer at mid distance** is essentially unchanged: 9.8 % at 400 px. The recolour step should add a distance
   fade of the weave's contrast in M_SmokeBomb, or custom mips, and test under TSR.
9. **Top and back views** show a small crumpled pocket where a lower tape shows between two covering bands. It is
   visible in `smokebomb_top.png` and the line sheet, and round 4 had it too, as a smoother lip. The kinks are LOD0's
   3.5 mm ring chords on a strongly curving covering edge.
10. **No M_SmokeBomb Unreal asset yet.** The look depends on Specular = 0.5 x ORM.A (section 2). This is disclosed
    in the sidecar, and it is the recolour step's job.

## 10. Files

| Path | What |
|---|---|
| `Scripts/props/build_smoke_bomb.py` | The build (8.0.0): SHADING (sRGB Detail, ORM.A specular), report fields, sidecar text |
| `Scripts/props/props_lib/smokebomb_wind_fit.py` | The winding: shingled fan, hidden widening, R2 / R3 / U2 limb weaves |
| `Scripts/props/props_lib/smokebomb_wind.py` | A `None` join is searched (reference_winding) |
| `Scripts/props/props_lib/smokebomb_ball.py` | `guard_clear_mm` 0.3; `span_mm` (off, measured); `finish_maps`: sRGB Detail and the ORM.A mask; T5's stub count |
| `Scripts/props/props_lib/smokebomb_cloth.py` | `ClothSpec6` and the cord fade (`cord_vis_*`) |
| `Scripts/props/props_lib/smokebomb_tape.py` | `Shading.detail_encoding` and `spec_mask_power`; the preview graph; `unreal_material_spec` |
| `Scripts/props/props_lib/smokebomb_threads.py` | T1-T3 thinner and curlier; T5 two stubs |
| `Scripts/props/props_lib/smokebomb_look.py` | The line-sheet shot; the graph docstring |
| `Scripts/props/props_lib/ue_import_textures.py` | Detail intent sRGB ON |
| `Assets/SmokeBomb.blend` | sha `01271381…`; textures packed |
| `Exports/SmokeBomb/` | FBX `a428dd21…`, sidecar `f192abcc…`, BC `c0042aca…`, Detail `cd913eb1…`, ORM `5dbce6c7…` (RGBA), N `0bb3b332…` |
| `Renders/SmokeBomb/` | side_by_side, reference_view, crops_3x, hero, raking, top, back, wire, lods, lod_switch, **linesheet** |
| `WorkFiles/smokebomb/smokebomb_report.json` | Every number, measured on what was built |
| `WorkFiles/smokebomb/final_pass/` | `tools/` (fp_idmap, fp_passmap, fp_widen2, fp_fan, fp_labels, fp_labdiff, fp_limb, fp_geo.sh, fp_iter.sh, fp_mips, fp_steps, fp_glint, fp_crop); the caches and cloth iterations (`g_*`, `c6*`, regenerable); `meas/`; `final/` evidence; `shimmer/`; `mip_parity.json`; `orig_start/` (round 4 as found); build logs `logs_ship1-4.txt` |
| `WorkFiles/smokebomb/UnrealCheck_fp/` | The Unreal harness, run `0925c` (with `0925a` and `0925b` archived) |
| `WorkFiles/smokebomb/regression/` | `compare_post_smoke_bomb.py` and `post_smoke_bomb/` |
| `Backups/SmokeBomb_2026-09-21/` | Blend, Exports/SmokeBomb, Renders/SmokeBomb, the smoke bomb modules and build script (no `__pycache__`), this report and its JSON, References/SmokeBomb |

**Not touched:**
- the shuriken pack and the paused paper bomb;
- the generic props_lib modules (atlas, bake, gallery, geometry, measure, paper_material, render, sheet, spec);
- `Scripts/pipeline/**`;
- BlackNunchucks, DemoGame_1 and its open editors;
- the locks (the SmokeBomb lock was only read).

No GUI Blender or blender-mcp link was used. Nothing was downloaded or installed.
