"""Finalise step 3: edit WorkFiles/kunai/KUNAI_PLAIN_REPORT.md (status line, header note, section 14 heading, 14.0,
the 14.7 independent-check note, 14.10-14.12).  Each replacement must match exactly once.
    py -3 edit_report_md.py"""
from pathlib import Path

p = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\kunai\KUNAI_PLAIN_REPORT.md")
s = p.read_text(encoding="utf-8")


def rep(old, new):
    global s
    assert s.count(old) == 1, (old[:70], s.count(old))
    s = s.replace(old, new)


rep("**Date:** 2026-09-19. **Library:** shuriken_lib 3.10.1. **Status:** built, reviewed (geometry / Unreal / visual), the review's blocker and majors fixed and rebuilt; all gates pass and all seven forms are verified in Unreal 5.8 on the exact exported bytes.",
    "**Date:** 2026-09-19 (library 3.10), **updated 2026-09-27**. **Library:** shuriken_lib **3.11.1**. **Status:** the blade section was reworked to the user's option C (a 7 mm full diamond over a 0.3 mm edge), with the knife coat rule and the 3/4 diagonal as the hero (section 14). It was reviewed twice (geometry / visual / Unreal); round 1's two majors were fixed in 3.11.1 and round 2 passed. All gates pass. The kunai is verified in Unreal 5.8.3 on the exact exported bytes, independently, in a fresh content path. `/Game/NinjaPack` has been rebuilt. The six other forms are byte-identical. New regression baseline: `WorkFiles/shuriken/regression/post_blade_section`.")
rep("> **Library 3.11.0 (2026-09-27): section 14 is the blade-section rework (option C: a 7 mm diamond over a 0.3 mm edge, the knife coat rule, the 3/4 hero); its numbers win over sections 1-13.**",
    "> **Library 3.11.1 (2026-09-27): section 14 is the blade-section rework (option C: a 7 mm diamond over a 0.3 mm edge, the knife coat rule, the 3/4 hero; 3.11.1 is round 1's material fix at the point). Its numbers win over sections 1-13. 14.11 lists every number that moved, and 14.12 gives the shipped SHA-256s.**")
rep("## 14. Blade-section rework, option C (library 3.11.0, 2026-09-27)",
    "## 14. Blade section rework (3.11.0), option C - shipped as 3.11.1 (2026-09-26/27)")

SEC140 = """### 14.0 Why, the measurement, and the options

**Why.** Next to the reference photo (`References/Kunai/kunai_reference2.jpg`), the 3.10.1 blade read as a flat dark plate with a wide bright bevel. The photo's blade reads as a proud centre ridge, with one facet catching the light and the other falling dark. The 3.10.1 section was a 5.0 mm ridge over a 1.5 mm edge flat, which is nearly a plate over the front 40 % of the blade (face angle 4-5°).

**The measurement** (`WorkFiles/kunai/blade_section/ours/`, `photo_A/`, `photo_B/`; result `ours/photo_reconciled.json`). The metric is the face slope, (ridge half-thickness - edge half-thickness) / half-width, measured at seven stations along the visible blade.
- Two measurers worked independently, then a reconciliation stage ran:
  - It fits a parametric matcap to the forged ring through the pixel footprint and a 0.3 px PSF.
  - It inverts the facet contrast without needing the albedo.
  - It takes the roll from the measured ridge offset.
- **Validated** on our own renders at the photo's probe scale: it recovers the known slope at 0.98-1.08x (0.87-1.33x per station; `ours/validate/final_check.json`). One measurer's kernel method read 2.1x on the same test and was rejected as biased.
- **Result:** front face slope **0.215** (range 0.153-0.266), rear 0.281, about 10.5° mid-blade. 3.10.1 had **0.088**, 0.41x the photo.

**Research** (`WorkFiles/kunai/blade_section/research/section_research.md`). Every kunai that states a figure has a 4-8 mm ridge or stock: mass-market 4.0-5.1 mm, hand-forged 6.35 mm and 6 mm, and a hand-made thrower at 8 mm.

**The options** (`WorkFiles/kunai/blade_section/options/OPTIONS.md`). Each was built as a full prototype, with the bake and every gate, in a copy of the library (`options/proto_tree/`):

| | A | B | **C (picked)** |
|---|---|---|---|
| Section | 5.0 mm held to x 63.6, 0.6 mm edge | 9.0 mm ridge, tip 2.7 mm, 1.5 mm edge | **7.0 mm ridge, 0.3 mm edge** |
| Front face slope vs the photo | 0.158 (0.73x) | 0.207 (0.96x) | **0.186 (0.87x)** |
| Assembled mass / pivot | 157.5 g / -22.1 mm | 195.0 g / **-8.1 mm** (at the grip's front edge) | **164.9 g / -19.6 mm** |
| Cost | still reads shallow | heaviest; balance moves 12.4 mm; apex moves 4.7 mm back | the 1.1 mm grind band becomes a 0.15 mm line |

The user picked **C** on 2026-09-26, with the knife-specific hero coat rule (14.3) and the 3/4 diagonal as the hero (14.4).

"""
rep("### 14.1 The section\n", SEC140 + "### 14.1 The section\n")
rep("> **Re-run for 3.11.1 (review round 1, section 14.9).**",
    "> **Independent re-check (review round 2, 14.10).** An independent reviewer ran the same harness, unchanged, on the shipped 3.11.1 bytes in a fresh path. KunaiBladeC2 had already been used by the fix, so this run used `/Game/ShurikenCheck9/KunaiBladeC3` (`asset_existed_before_import` false; evidence in `WorkFiles/shuriken/UnrealCheck6/blade_section_c3/`). The result: **all seven forms VERIFIED**, 23 guarded launches, with 3 waits on other chats' Unreal commandlets and never an overlap. There were 0 Warning/Error lines, and the kunai's figures and round trip equal the C2 run's. The kunai's `engine_check` now cites the C3 evidence.\n>\n"
    "> **Re-run for 3.11.1 (review round 1, section 14.9).**")

TAIL = """
### 14.10 Review round 2 (library 3.11.1, 2026-09-27): passed

Three independent reviews ran on copies of the shipped 3.11.1 bytes (blend `abb558fef12a`, FBX `a2d464722c30`).

- **Geometry: PASS.**
  - Sections at 29 stations on every LOD follow option C. LOD0 is at most +0.146 mm over the analytic ridge (the ramp starts at the plunge station) and -0.005 mm under it.
  - The face slope matches the analytic EDGE_T 0.3 diamond to within 1e-4 from x 13.8 to 128.
  - All 148 LOD0 grind facets are at 35.000°, and the land is 0.150 mm on LOD0 and LOD1.
  - **LOD2's ridge is 0.000 mm against LOD0 at x 25** (the prototype had -0.63). Its worst difference is +0.079 mm at x 14.
  - Masses by the reviewer's own integration: study-definition un-ground 154.060 g, finished 151.968 g, assembled 164.855 g. The mass centre is 0.003 mm from the file pivot.
  - The hulls are convex and exactly symmetric, and contain every vertex of all three LODs. UVs: 0 collapsed, 0 mirrored, 0 overlapping pixels. Every shell is watertight and manifold. The FBX loop set equals the blend's.
  - The six other forms: 66/66 byte-identical, and compare_frozen passes.
- **Visual: PASS, no blockers.**
  - The hero's ridge split is clearly visible: the near facet has a median of 0.53 and the far facet 0.30, against a background of 0.40.
  - The 0.15 mm edge reads as one continuous line that runs into the point, with no detached speck and no aliasing.
  - The neck close-up shows the 7 mm ridge and the 0.3 mm edge.
  - Minors:
    - The style comparison's footer still said "Unreal 5.8: pending" and its banner "3.11". **Fixed at finalise:** the sheet was regenerated.
    - In the LOD grind macro, LOD2 has a wider dark band along the near edge; this follows from its land-0 edge line, by design.
    - Texel steps show at the grind band's inner edge near the apex, but only at 4x zoom.
    - The top ortho shows no ridge, as expected under overhead light.
    - None of these needed a change.
- **Unreal: PASS**, in the independent fresh path `/Game/ShurikenCheck9/KunaiBladeC3` (14.7).

The pack materials were rebuilt after the round (14.8).

### 14.11 Numbers that moved

| | 3.10.1 | 3.11.1 (shipped) |
|---|---|---|
| Ridge | 5.0 mm to x 35, then to 1.6 mm at x 135 | 5.0 mm at x 5, rising to **7.0 mm** at x 24.42, held to x 35, then to 1.6 mm at x 135 |
| Un-ground edge `EDGE_T` / max blade thickness | 1.5 mm / 5.0 mm | **0.3 mm / 7.0 mm** |
| Front face slope, median (photo 0.215) | 0.088 (0.41x) | **0.186 (0.87x)** |
| Face angle mid-blade, x 56.7 (photo 10.5°) | 5.2° | **10.43°** |
| Knife grind width in plan | 1.06-1.35 mm | **0.15-0.23 mm** (the 35° grind to a 0.15 mm land is unchanged; apex x 135.2) |
| Polished edge band | ~1 mm (0.7 mm polished + satin) | the whole 0.15-0.23 mm facet, roughness 0.22 up to the point; no aliasing |
| Mass-gate target (study basis, `plain_calc`) | 153.02 g (19,492.6 mm³) | **154.06 g** (19,625.3 mm³) |
| Steel un-ground (error) / finished | 151.89 g (-1.13) / 149.04 g | **153.34 g (-0.72) / 151.96 g** |
| Assembled / physics override | 161.93 g / 0.1619 kg | **164.85 g / 0.1648 kg** |
| Pivot (mass centre, design x) | -20.52 mm | **-19.59 mm** |
| Head hull; two hulls | 10,356 mm³, 26 v; 60,316 mm³ | **10,739 mm³, 30 v; 60,699 mm³** |
| Unreal COM offset | +3.04 cm | **+3.10 cm** |
| LOD triangles | 2,182 / 696 / 366 | **2,182 / 736 / 382** |
| LOD base stations (LOD0 / 1 / 2) | 3 / 1 / 1 | **3 / 3 / 2** |
| M_Shuriken_Master nodes | 1,192 | **1,195** (`RUNOUT_CONTOUR_PROP`, kunai only; a bitwise no-op on the six) |
| Hero | end-on, yaw -25, averaged all-coat rule | **3/4 diagonal, yaw 35**, with a glossy-only blade key and the **knife coat rule** (flat coat 0.565 / 0.564 against the anchor's 0.560 / 0.550) |
| Unchanged | | two-sided LOD deviation 0.63 / 1.18 mm; bounds 28.0 x 3.6 x 2.0 cm; sockets; screen sizes; lettering rectangle; sidecar bytes |

### 14.12 Shipped bytes, baseline, backup

| File | 3.10.1 (pre_blade_section) | **3.11.1, shipped** |
|---|---|---|
| `Exports/Shuriken/SM_Kunai_Plain.fbx` | `ebb6612b58e0...` | `a2d464722c30ef440e166e1032965bb2b828b9f15794d79ca96d4cf2eb019d7b` |
| `SM_Kunai_Plain.sockets.json` | `589bc324df35...` | `bf6990550357363ddf674ece92dbf1d1114ba70e1798f19015a0e8b3c5a53e5e` |
| `Assets/Shuriken.blend` | `f712b421bacb...` | `abb558fef12a3365434f200d66c4fb7949ddaf26bd3eccaa83829c97d6209fd5` |
| `T_Kunai_Plain_BC / _ORM / _N` | `c2775b5331ef / 87d7f5a25164 / 8d49b547b760` | `78b01dee6b25... / 7c487fb86722... / f7516ac8f431...` |
| `T_Kunai_Wrap_BC / _ORM / _N` | `718e4b68cc65 / 6e39cca3953e / b414bf094a5d` | `e60400fd1a26... / 62f0839dfd19... / b1a3f6367fc2...` |
| `T_Kunai_Wrap_Natural_BC` | `312c611d4cbb` | `40dc3ebd3efe...` |
| `T_Kunai_Lettering` | `0dd8d2a47004` | unchanged |
| `Recolour/T_Kunai_Wrap_Detail16`, `recolour_maps.json`, `recolour_constants.json` | `497d66bfee39`, `9aa0eee7432d`, `a5917ae68c77` | `a69e7f0826ea...`, `900f982095d3...`, `5ec770810bdd...` |
| `Renders/Shuriken/kunai_plain_persp.png` = `kunai_plain_3q.png` | `70272096b04b` / `7618fb0cf097` | `a0364e7637f2...` (both) |
| `modern_line_sheet.png` / `style_comparison.png` | `40a0f25f047f` / `070821fe3ea3` | `752b8ddaf5b7...` / `940d65d3ce14...` |
| `WorkFiles/shuriken/kunai_plain_report.json` / `pack_report.json` | `851a8ed6f291` / `da2d590681ed` | `8f48244e83e4...` / `048060f78528...` |

The full 64-character hashes of every shipped kunai and pack-level file are in the report's `blade_section.release.shipped_sha256`. The machine-readable report also gained `blade_section.photo_measurement`, `research`, `options_considered` and `release`.

- **Sheets (finalise).** `modern_line_sheet.png` regenerates byte-identical. `style_comparison.png` was regenerated for 3.11.1 / Unreal verified. The lettering proof was re-rendered from a copy of the 3.11.1 blend; its ink footprint is identical to Sep 19's.
  - Against the pre_blade_section snapshot, the six forms' line-sheet panels are pixel-identical.
  - Their style-sheet columns (and the reference column) are identical except for **one** anti-aliased footer-text pixel in the spike column, 7 levels, with the same text. Two controls show this is not a content change. The original 3.10.1 sheet script, run on the snapshot's inputs, reproduces the snapshot sheet exactly (0 px). Run on today's inputs, where only the kunai column differs, it gives the same single pixel. So the pixel comes from Cycles sampling the changed kunai column, and it is not a change to the six (`WorkFiles/kunai/blade_section/finalise/sheets/`).
- **Regression baseline:** `WorkFiles/shuriken/regression/post_blade_section/` holds the seven forms (113 files, library 3.11.1) plus `extras/` (the 3/4 and close-up renders, both sheets, the Recolour files and the materials README). It was taken after the Unreal result was attached. Its self-check passed: `compare_frozen.py --snapshot post_blade_section` on all seven forms (`regression_post_blade_section_selfcheck.json`), and all 122 files equal the live files. The next job runs `--snapshot post_blade_section --forms four_point,eight_point,square_plate,six_point,spike,hooked_cross,kunai_plain` and builds with `--frozen-maps WorkFiles/shuriken/regression/post_blade_section/textures`.
- **Backup:** `Backups/Shuriken_after_kunai_blade_section_2026-09-26/`, laid out like `Shuriken_after_kunai_plain_2026-09-19/`, hash-verified.
- **Change log:** `WorkFiles/kunai/blade_section/LIVE_CHANGES.md` lists every live write with its time, and ends with the final list of changed files.
"""
s = s.rstrip("\r\n") + "\n" + TAIL
p.write_text(s, encoding="utf-8")
print("ok", len(s))
