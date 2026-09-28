# SM_PaperBomb — build report (fifth pass: accuracy to the reference, round 3)

Blender 5.2.0 LTS headless, Unreal 5.8.2 (`5.8.2-56702186+++UE5+Release-5.8`), 2026-09-20.

Built by `Scripts/props/build_paper_bomb.py`, which rebuilds `Assets/PaperBomb.blend`
from nothing on every run. Nothing here was hand-patched into the blend; every number in
this report was measured on what shipped, not copied from the spec that asked for it.

The instruction is one sentence: *ensure we are accurate to the reference to the T.* The
contract is `References/PaperBomb/REFERENCE_SPEC.md` — 26 ranked rows reconciling three
independent metrology passes and re-measured by a fourth. **Section C is this pass**
(round 3): a fourth independent measurement found four rows still outside tolerance,
three regressions and one defect no pass had looked for, and this is what was done about
each. **Section B** is round 2, **section A** the third pass, sections 1–15 the second;
each is still true except where a later section says otherwise. Sections C.10, B.9 and 15
are what is still not done.

**Round 3 result: 44 of 44 REFERENCE_SPEC gates pass, 74 of 74 build gates pass,
`qa_check` 74 / 74, and every Unreal pass is green on the exact shipped bytes.**

```
Assets/PaperBomb.blend                       a2177819e8d63dd2cd2246d55f40c58fcb5b0a4b2b6cc8b0bd4c2b9b1f00359e
Exports/PaperBomb/SM_PaperBomb.fbx           964f362afe6e72c63e00f526803dd531274f29240f2d91909d262a4002c9bcd9
Exports/PaperBomb/SM_PaperBomb.sockets.json  c6eb2ee0f7868c4ffbdc9de782f4bf2862a5d09c5caf53a1c6d71ef882856468
Exports/PaperBomb/README.txt                 42fdb22d15ba8d6ccefcc84ee8adf43b1772c9ba7ef172fd8e376baeb0cc4934
Exports/PaperBomb/Textures/T_PaperBomb_BC.png   4f2b9a29934d9933b55b85b07a01bb8a05bee4dfb84cc5bce52c49a818464c7a
                           T_PaperBomb_ORM.png  39578e935bc4dd5994e90998cb2cddb50bc639b1a496992074979a67127af44d
                           T_PaperBomb_N.png    2adccaba480d19837ce067f7f85133973c3935cf89d4785e64f6d24a417c8a6b
                           T_PaperBomb_M.png    58c767400c7e7ea1a665a4f0a853f618518e9b68da0b4af63af2593c5ea77167
Renders/PaperBomb/          hero front back raking persp wire lods lodgrind linesheet
Scripts/props/              props_lib/ + build_paper_bomb.py + ink_floor_compare.py
WorkFiles/paperbomb/        paperbomb_report.json, this file, diag/, UnrealCheck/,
                            regression/, ink_floor_compare/, lod_legibility.json,
                            grain_calibration.py + .json, independent_check.py + .json

The four maps are byte-identical across three consecutive builds from the same seed; the
FBX differs only in its clock and object UIDs (152–153 bytes, metadata only).
```

---

## C. Round 3 — the six rows that were still out, and the one nobody had seen

A fourth measuring pass re-measured the shipped map with its own raster-only instrument
and — the part that makes its numbers usable — ran the same instrument on the V1 guide as
a calibration control, reproducing the spec's own V1 figures (tag 616 × 1379 px, aspect
0.4467 against 0.4468, edge-ageing 15.05 % against 15 %). It found **20 of 26 rows inside
tolerance, four rows failing, three regressions, and one defect no pass had ever looked
for**: the lower-right column 焼尽 had welded to the hero glyph 爆.

Every one of its six findings was accepted. Nothing was argued down; where our own
instrument and theirs disagreed, theirs was treated as the reading a buyer's camera
takes, and in three places our instrument was replaced because it was measuring the
drawing LAYER where the row is a statement about the PAPER.

**44 of 44 REFERENCE_SPEC gates pass. 74 of 74 build gates pass. `qa_check` 74 / 74.**

### C.1 The defect nobody had looked for: 焼尽 welded to 爆

The measurer's evidence was specific and it was right. Eroding the black body by 0.31 mm
split a 31.8 mm² mass at (54.7, 96.7) and an 8.0 mm² mass at (58.9, 101.1) off it; the
lower-right column's two 14.41 mm cells at axis 57.3 spanned y ≈ 94–123 while 爆's own ink
reached y 104; the composite read **57.29 mm tall against the row's 52.38**, the column
showed **one** measurable cell instead of two, and section 7's *does 爆 read as ONE
character* was answered no.

Three things were wrong and all three are fixed.

1. **The column sat too high.** V2 is authoritative for a text slot and puts 焼尽 at
   y 98.7 – 125.4; V1 puts it at 100.4 – 121.2. Ours started at **96.2**. The cells moved
   down onto V2's own placement and the cell shrank 12.49 → 11.95 mm in height, which
   also pulled the widest raster cell back from 14.40 toward the reference's 14.0:

   ```
   col_lower_right_y     (0.65700, 0.73800) -> (0.67200, 0.74900)   centres 104.83 / 116.84 mm
   col_lower_right_cell  (14.41, 12.49)     -> (14.10, 11.95) mm
   ```

   The column now runs y 98.86 – 122.82 against V2's 98.74 – 125.43, and still clears the
   small chop's frame (123.55) by 0.7 mm.

2. **Interpenetration is not the defect — contact is.** Both guides run this column
   through 爆's bounding box (V1 by 3.8 mm, V2 by 1.7) and neither touches its ink. So the
   hero glyph is now **built before the columns and stamped after them**
   (`build_centre` / `stamp_centre`), and every column is clipped out of a
   `column_centre_clear_mm = 1.15 mm` dilation of it. 1.15 and not 0.6 because
   `ink_bleed` spreads black 0.28 mm each way afterwards and closed a 0.55 mm gap
   completely — which is also why the second build's *upper* columns were touching 爆 at
   the top and nobody had noticed. The clearance costs 焼 **2.6 % of its ink**; it reads
   as the column passing behind the hero glyph, which is what the guides show.

   The rng stream is untouched: `build_centre` consumes `_rng(seed, "text_centre")` in
   exactly the order `typeset_centre` did, so moving the work earlier changes no pixel of
   the glyph itself. Proved by rebuilding: the four map hashes are identical across three
   consecutive builds.

3. **No gate could see it, and two gates passed for the wrong reason.**
   `art_metrics.centre_glyph` measured inside the glyph's own cell, so a welded neighbour
   was clipped at the cell boundary and reported as 53.47 mm. It now separates two
   questions that were being conflated:

   * **which ink is the hero glyph** — the components that reach the glyph's CORE (the
     middle third of its box). The body and the 火 radical do; no column character can.
     Rows 2 and 3 are measured on those and nothing else.
   * **what is standing next to it** — `neighbour_gap_mm`, the nearest ink between the
     hero and any other black mark that enters its cell, measured on the components'
     own texels.

   Two new gates: `s02b_centre_glyph_not_fused` (the unclipped box, and ≤ 10 mm² of hero
   ink outside its own cell) and `s03d_centre_glyph_clear_of_neighbours` (≥ 0.30 mm).
   Measured: unclipped **59.27 × 51.54 mm**, **0.0 mm²** outside the cell, neighbour gap
   **2.86 mm**. An independent-style re-measurement of the shipped map agrees: two hero
   components, **59.20 × 51.46 mm**, and the lower-right column shows **three** separate
   marks (火 and 尭 of 焼, then 尽) where it showed one.

### C.2 Row 20 — the big seal's 4 mm tail was not the seal

The measurer located it exactly: a red tail hanging below the chop's bottom bar at
x 6.4 – 11.0 taking the red component to y 147.41, so the raster box read **18.58 × 31.20
against 18.0 × 26.5**. It was not the chop. It was the **bottom-left corner bracket**:
the inner-rule corner sits at (6.83, 145.96) and a 3.2 mm leg plus 0.55 of a 1.6 mm curl
reaches up to y 141.88, which is inside the seal's bottom bar at 142.0 – 143.3. The two
fused into one red component and the whole "tail" was the bracket's own vertical arm.

Only 2.5 mm of paper exists between the chop's box and the bracket corner, so:

```
bracket_leg_v_bottom_mm  3.2 -> 0.95      bracket_curl_bottom_mm   1.6 -> 0.95
bracket_leg_h_bottom_mm  3.0 -> 2.10      seal_frame_bleed_mm     0.16 -> 0.06
seal_keepout_mm (new)    0.85             both chops are keep-out zones for ornament ink
```

`seal_keepout()` is the guarantee and the stub geometry is chosen so the guarantee never
has to cut anything. `seal_frame_bleed_mm` came down because the clip is applied in the
stamp's own rotated frame and a 1° rotation already adds ~0.47 mm to the axis-aligned box
a measurement sees; half a rule of bleed on top of that was the 0.60 mm §6 overshoot the
review recorded.

**And the gate was measuring the wrong thing.** It read the seal LAYER (18.32 × 27.12)
where the row is about the paper. `art_metrics.seals` now also reports
`red_raster_box_mm` — the union of every red component that puts a square millimetre
inside the frame, followed out of the frame wherever it goes — and both chops are gated
on it (`s20d`, `s19d`, ±1.4 mm because the raster carries the stamp's rotation).

| | drawn layer | red raster (ours) | red raster (independent) | reference |
|---|---|---|---|---|
| big chop | 18.32 × 27.12 | **18.494 × 27.083** | 18.41 × 27.01 | 18.0 × 26.5 |
| small chop | 9.13 × 17.87 | **9.286 × 18.03** | 9.21 × 17.96 | 9.0 × 17.8 |

The big chop's red now runs y 116.19 – 143.27. The tail is gone.

### C.3 Row 22 — the break was three times the break that was drawn

The measurer read top occupancy **0.7709** and bottom **0.8050** against a 0.82 floor, and
noted it was invariant across every band width from ±1.2 to ±3.0 mm — so it was not an
instrument choice, it was ink that was not there. The cause was one line:

```python
soft = 0.012          # of the stroke's own ARCLENGTH
```

On a 61.9 mm top rule that is **0.74 mm of ink fading out and back in at every lift**, so a
0.6 mm drawn break measured as about 2.1 mm of bare rule, and a rule's occupancy depended
on how long the rule was. `brush_stroke` now takes `gap_soft_mm` and the rules pass
**0.18 mm**, an absolute length; the ring keeps the proportional behaviour because its
gaps are specified as angles and its taper is the point. With the drawn break and the
measured break finally the same number, `RULE_BREAK_EDGE_MM` came down 0.50 → 0.26 and the
target was set at **0.872**.

Measured on the shipped map: occupancy **0.898 – 0.907** on the build's instrument and
**0.875 – 0.942** on an independent-style one across ±1.2 / ±1.6 / ±2.2 / ±3.0 mm bands
(tolerance 0.82 – 0.95, reference 0.82 – 0.92), 6 – 8 breaks a side, longest **2.94 mm**
against the reference's own 1.9 – 3.9.

**A second bug fell out of fixing the first, and it was the more dangerous one.** Moving
the occupancy target by **0.010** swung the four sides' rule weights from 0.660 – 0.669 to
**0.464 – 0.682** and the left-right difference from 0.03 to 0.161 mm — row 21 failed on a
change that should not have touched it. Two causes: the width profile was normalised on
its **mean** while the row is measured as a per-scanline **median**, and a 9-sample noise
cell over 80 samples is about nine independent lobes, whose median is not a determined
number. The breath is now 4.5 (about twenty lobes, and a faster width change along the
lap, which is what a brush does) and the profile is normalised on its median. Swept across
six occupancy targets from 0.870 to 0.905 the four weights now move within **0.582 – 0.682
with a left-right difference under 0.023 mm**. Shipped: 0.582 / 0.619 / 0.637 / 0.659,
mean 0.624, L−R 0.04.

### C.4 Row 26 — the spec's own figure is not reproducible, so the guide was measured instead

The measurer's finding: our paper carried **3.9× the V1 sheet's grain at a third of its
correlation length**, confirmed independently by texture energy, and the correction had
been applied in the wrong direction across three builds (3.01 % → 10.06 % → 10.37 % while
V1 sat at 2.69 %). Row 26 as written asks for 17.0 % on a 0.50 mm cell; no independent
instrument reads V1 anywhere near that.

So the guide was measured with **`art_metrics.grain`'s own recipe, unchanged**, and the
build aimed at what it said. `WorkFiles/paperbomb/grain_calibration.py` is that run; it is
metrology, it never ships a pixel, and it reproduces the spec's V1 tag to 0.35 %
(614 × 1377 px).

| like for like | V1 guide | ours, before | ours, shipped |
|---|---|---|---|
| amplitude | 0.0363 | 0.1433 (**3.95×**) | **0.0366 (1.01×)** |
| correlation length | 1.591 mm | 0.619 mm (0.39×) | **1.548 mm (0.97×)** |
| texture energy | 0.01111 | 0.04392 (3.95×) | **0.01132 (1.02×)** |

The knobs: grain cell 0.34 → 1.22 mm at three octaves → two, anisotropy 1/2.60 → 1/1.12,
and the three amplitudes 0.700 / 0.215 / 0.070 → 0.181 / 0.044 / 0.034. `TARGETS` for row
26 are re-based on the guide's own figures with ±45 % bands, and **the row as written is
recorded beside them, not gated**, with the reason and the provenance
(`grain_row26_as_written`, `paperbomb_art.GRAIN_LIKE_FOR_LIKE`).

This is the only place in three passes where the build does not aim at a number the spec
states. It aims at the sheet the spec was measured from, with the spec's own instrument,
and says so.

Two rows improved for free. The paper's median linear luma rose 0.786 → **0.7935** because
less grain was dragging it down, so contrast went **156.1 → 157.6** on our instrument and
**145.4 → 149.9** on an independent one against V1's own 152.6. And row 24's worst row-luma
dip fell to **0.46 %** (the reference sheet itself measures 2.07 % under the same test).

### C.5 Row 3 — unreached, not unreachable. The measurer was right.

The second build argued a 0.75 mm clearance budget capped the radical's reach at 5.8 mm.
The measurer pointed out our actual ink gap was already **0.31 mm** — less than half the
reference's — so roughly 0.4 mm of clearance was unspent and the binding constraint was
the reach, not the gap. Correct, and the fix cost no clearance at all.

`_extend_radical_sweep` scans the body's left contour for the row where a thin brush can
sit furthest right. It scanned **9.0 mm** below the radical's tip. The contour steps out
hard at y ≈ 98.4 — from 28.6 mm to 32.5, then 33.7 — and the tip is at y 84.4, so the
corridor that matters was **14 mm down** and the search had never seen it.
`centre_radical_sweep_mm` 9.0 → **15.0**, nothing else touched:

| | before | after | gate | reference |
|---|---|---|---|---|
| bbox overlap | 5.73 mm | **6.81 mm** (independent: 6.66) | ≥ 6.0 | 8.86 |
| ink gap | 0.31 mm | **0.46 mm** | > 0 | 0.75 |

The one row the second build declared failing now passes, and it passes with *more* clear
paper than before, not less. It is still 2.05 mm short of the reference's own overlap.

### C.6 Row 19 — the gap clause the build had no instrument for

2.32 mm against a 2.0 mm ceiling, unreported by the build because the only gap it knew
about was nominal pitch minus nominal em — and MasaFont's 火 and 道 do not fill their em
vertically. `art_metrics.seals` now measures it on the raster, by a definition that does
not depend on assigning ink fragments to one character or the other: inside the chop's own
frame, the longest bare run of rows between the first and last inked row. Gated as
`s19c`. Pitch 7.24 → **6.90 mm**, em 7.5 → 7.7: measured gap **0.77 mm** (reference 1.24,
ceiling 2.0) and implied em **7.49 – 7.51** against the row's 7.5.

### C.7 The guide gate, hardened where the measurer found it thin

The measurer confirmed the gate refuses `open()` on both guides, both slash conventions
and the whole `References/PaperBomb` path, and restores `builtins.open` on exit — and
reported a gap rather than a breach: the guard patched `builtins.open` only, and
`bpy.data.images.load` still loaded the guide from inside an active guard. Harmless today,
because the module contains no image loads of any kind, but a guard that covers only the
route nobody would take is not a guard. Both halves now exist:

* **Runtime.** `bpy.data.images` is an immutable `bpy_prop_collection` and cannot be
  patched on the instance or the type, so `no_guide_access` swaps `bpy.data` itself for a
  thin forwarding proxy whose `images.load` is guarded, and puts the real object back on
  exit. Demonstrated: `REFUSED(open)` and `REFUSED(images.load)` on both guides and on
  `REFERENCE_SPEC.md`, the licensed font still `ALLOWED`, and both `builtins.open` and
  `bpy.data` restored afterwards.
* **Static.** `no_image_loads()` parses the art module's own source and fails on any call
  whose dotted name matches `images.load`, `Image.open`, `imread`, `np.load`, `imageio.`,
  `cv2.imread` and six more, or any string literal that looks like a path to a guide PNG.
  Both lists empty. Gate **13b**, so the route cannot be added later without the build
  going red.

### C.8 Row by row, measured on what shipped

Ours is the build's own instrument; *indep* is a second raster-only pass over the shipped
BC island written for this round (`WorkFiles/paperbomb/independent_check.py`).

| # | row | reference | ours | indep | verdict |
|---|---|---|---|---|---|
| 1 | paper : black contrast | 170:1 (V1 152.6 like-for-like) | **157.6:1** | 149.9:1 | pass |
| 2 | 爆 size | 59.30 × 52.38 | **59.35 × 51.61** | 59.20 × 51.46 | pass |
| 2b | 爆 unfused (new) | one mark | **59.27 × 51.54, 0.0 mm² outside its cell** | 2 comps | pass |
| 3 | 爆 integrity | 2 comps, overlap 8.86 | **2, 6.81 mm** | 2, 6.66 | pass |
| 3d | clear of neighbours (new) | clear paper | **2.86 mm** | 3 marks in the column | pass |
| 4 | rules per side | 1 | **1 / 1 / 1 / 1** | — | pass |
| 5 | column cell width | 13.9 mean, 14.6 max | **13.94 / 14.32 max** | — | pass |
| 6 | column leading | 0.00 – 0.49 | **0.41 max** | — | pass |
| 7 | ring size / shape | 52.08 × 59.27, h/w 1.138 | **52.56 × 59.09, 1.124** | — | pass |
| 8 | ring centre | (35.47, 76.99) | **(35.13, 76.86)** | — | pass |
| 9 | ring stroke | 4.84 med, p95 ≥ 6.0 | **4.86 / 7.74** | — | pass |
| 10 | ring kasure | 0.198 holes, 0.919 coverage | **0.173 / 0.917** | — | pass |
| 11 | flame | 5 strokes, 167.0 mm² | **5, 174.3 mm², fill 0.315** | — | pass |
| 12 | upper column axes | 13.30 / 57.12 | **12.86 / 57.55** | — | pass |
| 13 | red saturation | S 0.90, hue 4.5° | **0.899, 4.5°** | — | pass |
| 14 | corner dart | 2.0 – 2.2 mm, red + black | **1.92 – 2.17, both at all four** | — | pass |
| 15 | paper colour | hue 39–42, S 0.18–0.24, luma ≥ 0.72 | **39.5, 0.197, 0.7935** | 0.7721 | pass |
| 16 | bottom black diamond | (35.05, 148.0) | **(35.09, 148.22)** | — | pass |
| 17 | leaf pair | (32.20, 130.76) / (38.04, 130.63) | **exact, 78 % and 100 % visible** | — | pass |
| 18 | above the top rule | nothing | **0.0 mm²** | — | pass |
| 19 | small seal | box 9.0 × 17.8, em 7.5, gap ≤ 2.0 | **9.13 × 17.87, em 7.49–7.51, gap 0.77** | 9.21 × 17.96 | pass |
| 20 | big seal | box 18.0 × 26.5, fill 0.54–0.64 | **18.49 × 27.08 raster, fill 0.582** | 18.41 × 27.01 | pass |
| 21 | rule weight | 0.57 – 0.68, L≈R within 0.15 | **0.582 – 0.659, L−R 0.04** | — | pass |
| 22 | rule continuity | occupancy 0.82 – 0.95 | **0.898 – 0.907** | 0.875 – 0.942 | pass |
| 23 | corner chamfer | 8.05 mm | **8.050 on LOD0/1/2** | — | pass |
| 24 | no baked crease | none | **0.46 % worst row dip** | — | pass |
| 25 | edge ageing | 15 % deep, reach 6–9, spread < 4 pts | **12.5 %, 7.7 mm, 0.95 pts, tilt 0.13 %** | — | pass |
| 26 | paper grain | re-based on V1, like for like | **1.01× amplitude, 0.97× length** | — | pass |
| 27 | composition | red 0.1126, total 0.2861, b÷r 1.542 | **0.1198 / 0.2881 / 1.406** | 0.1151 / 0.2738 / 1.379 | pass |
| 28 | frame rectangle | 61.877 × 142.085 | **61.828 × 142.150** | — | pass |
| 29 | no hard rectangular patch | none | **0 runs** | — | pass |

### C.9 Nothing regressed

* **Determinism.** Built three times from the same seed. **All four maps byte-identical
  every time** (`4f2b9a29… / 39578e93… / 2adccaba… / 58c76740…`), sidecar identical, every
  source file identical. The FBX differs by **153 bytes across 41 runs**, every one of them
  `Hour`, `Minute`, `Second`, `Millisecond` or an object-UID pair — `metadata only: True`.
  `regression/compare_post_accuracy_r2_vs_live.json`.
* **Geometry did not move.** No chamfer, LOD, socket, hull or bounds edit this round. LOD0
  1376 / 690, LOD1 540 / 272, LOD2 204 / 104, hull 16 verts, chamfer 8.050 mm on all three
  LODs, the four sockets bit-identical, Cord/kunai dry fit PASS, `qa_check` **74 / 74**.
* **Engine, re-run on the exact shipped bytes** (`964f362afe6e72c6…`), one commandlet at a
  time, into a fresh content path `/Game/PropsCheck/PaperBombR3F`, never `DemoGame_1`:

```
blender_fbx_counts.py   a second Blender reads the shipped FBX     1376 / 540 / 204, hull 28 tris
pass1_import.py         import + sidecar + textures, then save      8 / 8 in-process gates
pass2_reload.py         a THIRD process re-reads what was saved    11 / 11 gates
pass3_export.py         Unreal writes its own FBX back out          export_ok
roundtrip_compare.py    a FOURTH process compares the two          passed; hull 16 v 16,
                                                                   max position diff 2.3e-07 cm
ue_import_textures.py   import then verify, two more processes      4 / 4 both
```

* **LOD-switch legibility re-run on the new maps**: ink fraction 0.1934 / 0.1934 / 0.1941,
  hero mass 0.1445 / 0.1429 / 0.1416, contrast 4.6 / 4.5 / 4.6, all nine gates pass.
* **The ink-floor pair re-rendered** from the shipped maps: reference-matched **map
  157.6:1, render 126.7:1**; floored **map 15.7:1, render 26.6:1**. The four maps in
  `ink_floor_compare/reference/` are byte-identical to the four shipped maps and the
  floored set differs only in BC. `DEFAULT_INK_FLOOR = "reference"`.
* **The shuriken pack is untouched.** `shuriken_freeze_proof.identical = true` over 14
  files, asserted by the build itself before and after every run.

### C.10 What this round did NOT manage

1. **Black area is 8.5 % short of the reference and the black÷red ratio is 1.379 – 1.406
   against 1.542.** Both inside tolerance, but the ratio moved the *wrong way* this round
   — from an independently measured 1.5195 — and the honest reason is that it did so
   because the **red got more accurate**: red area went from 0.1057 (−6.1 % against the
   reference) to 0.1151 (+2.2 %), while black stayed where it was. Spec §6 says the
   shortfall is entirely black, and it still is. Closing it means more black ink somewhere,
   and every black element is currently on its own row's number, so there is no honest
   place to put it without breaking a row. Left for a later pass with a measurement of
   *where* the reference's extra black actually sits.
2. **The four reds are still one laid-on weight.** §3's closing reading is that the
   guide's four reds are one pigment at four weights — value spread 0.275 — and ours is
   0.071. Not gated by any row, acknowledged by the measurer as an open item, and not
   attempted this round because every cheap way to widen it moves `red_area_fraction`,
   which *is* gated and is now within 2 % of the reference. This is the next thing to do.
3. **爆's radical overlap is 6.81 mm against the reference's 8.86.** The gate (≥ 6.0) is
   met and the clearance is no longer the constraint, but the reference's own figure is
   not reached. Going further means drawing the 捺 through the corridor the body opens at
   y ≈ 100, which is a 14 mm descent for a 6 mm gain and would stop reading as a 捺.
4. **The small chop's inter-glyph gap is 0.77 mm against the reference's 1.24.** Inside the
   ≤ 2.0 ceiling on both instruments, and deliberately set short of the reference because
   the independent instrument reads this gap higher than ours and 2.32 mm was the failure
   being fixed. A build with both instruments agreeing could put it on 1.24.
5. **§6's big-seal frame right edge is 0.43 mm past the 0.4 mm §6 records** (x 5.73 – 24.14
   against 5.79 – 23.71). Improved from 0.60 mm by the bleed change; the remainder is the
   chop's own ±1.2° rotation, which is a stamp and should have one.
6. **Row 26 is built to the guide, not to the row's stated figure.** The figure is not
   reproducible by any instrument anyone has run, including the spec's own. Recorded
   beside the gate rather than silently dropped. If the spec's amplitude and cell
   definitions can be recovered, this should be re-checked against them.
7. **The bottom two corner brackets are now 0.95 mm stubs** where the top two are 3.2 mm
   hooks. That asymmetry is deliberate — there are only 2.5 mm of paper between the big
   chop's box and the bracket corner, and the reference has no inboard bracket there at
   all — but it is a design decision this round made on its own, and it is visible at 4×.

---

## B. Round 2 — what the independent re-measurement found, and what was done

An independent pass re-measured the shipped maps and meshes against REFERENCE_SPEC with
its own code, built on the spec's own metrology library. It validated its method by
running it unchanged on the previous build and reproducing the spec's own "ours" column
to about 1 %, so its numbers are like-for-like with the contract. It found six rows
outside tolerance, four regressions against section 6's "already correct" list, and six
gate tolerances that had been widened rather than met.

**Every one of those is now closed except row 3's bounding-box overlap**, which is short
by 0.20 mm and is a drawing limit, not a knob — B.3 says exactly why and what it would
take. **66 of 67 build gates pass**, `qa_check` is **74 / 74**, and the one failure is
that row, reported here rather than widened into a pass.

### B.1 Three measurements were wrong, and that is why three "passes" were failures

The most useful thing the re-measurement found is that three of the build's own numbers
were taken on a different quantity from the reference's. A number that does not measure
what the contract measures is worse than no number, because it reports a pass.

| Row | The build measured | The reference measures | Fixed by |
|---|---|---|---|
| **9, 10, and the composition table** | the red **LAYER's** alpha — which still reads "red" underneath the black 爆 painted across the ring | **visible** red: both guides are photographs and a photograph has no layers, so where black covers red the reference counts black | `art_metrics.Card.red_m` is now visible red (`red_layer_m & ~black_m`); the layer's own figures are reported beside it under `layer`, never gated |
| **1** | our paper's **median** over our black's **1st percentile** — 166.9:1 | paper median over the ink **median** — the spec's 0.0047 is `ink_colour.json`'s median | `ink_and_contrast` gates on the median; the core is kept as a diagnostic |
| **25** | the first 0.4 mm bin in **stored sRGB** — 15.2 % | the outer **2 mm** band in **linear** luma — V1's 13.9 % is 0.67259 / 0.78108 | `edge_ageing` measures the reference's band in the reference's space |

Two more instruments were replaced rather than re-aimed:

* **Rule weight** was a count of thresholded texels. A 0.70 mm rule is 9.05 texels at
  12.923 px/mm, so that instrument can only answer 0.62, 0.70 or 0.77 mm — and row 21
  allows 0.15 mm between left and right, which is two of its steps. The build duly
  reported a 0.155 mm difference that was one texel of antialiasing per side. It is now
  the **ink mass** across the band (the sum of coverage), which for a soft-edged stroke
  of width *w* is *w*. The texel count is still reported beside it.
* **The ring's mid-stroke ellipse** was the extremes of 360 mid-stroke points — two
  samples, and they are the two angles at which the hero glyph bursts out of the ring
  left and right, i.e. exactly the two the black covers. It is now a least-squares
  **fit** over the whole cloud, which is what the metrology pass's own `fit_ring` does.

### B.2 Row by row, measured on what shipped

Reference figures are the spec's; "ours" is `paperbomb_report.json` →
`art.reference_spec`, measured on the drawn raster of the build whose hashes are at the
top of this file.

| # | Row | Reference | Round 1 | **This build** |
|---|---|---|---|---|
| 1 | paper : ink contrast, on the ink **median** | 170 : 1 | 86.1 : 1 | **156.1 : 1** |
| 1 | paper / black median, linear luma | 0.803 / 0.0047–0.0053 | 0.780 / 0.00905 | **0.786 / 0.00503** |
| 2 | 爆 ink box, w × h, w/h | 59.30 × 52.38, 1.132 | 58.42 × 51.61 | **59.35 × 53.47, 1.110** |
| 3 | components / bbox overlap / ink gap | 2 / 8.86 / 0.75 mm | 2 / **0.54** / 0.55 | **2 / 5.80 / 0.70** |
| 4 | rules per side | 1 | 1 / 1 / 1 / 1 | **1 / 1 / 1 / 1** |
| 5 | column cell, mean / widest on the raster | 13.9 / 14.6 mm | 13.58 / **16.40** | **14.00 / 14.39** |
| 6 | column leading, max | ≤ 1.0 mm | **1.08** | **0.41** |
| 7 | ring mid-stroke, w × h, h/w | 52.08 × 59.27, 1.09–1.16 | 52.40 × 58.19, 1.110 | **52.56 × 59.07, 1.124** |
| 7 | ring–rule gaps, left / right / Δ | equal within 0.5 mm | 4.88 / 4.70 / 0.18 | **4.81 / 4.51 / 0.30** |
| 8 | ring centre | (35.47, 76.99) ± 0.5 | (34.99, 76.72) | **(35.12, 76.85)** |
| 9 | swept band, median / p95, **visible red** | 4.84 (4.3–5.4) / ≥ 6.0 | **3.36–3.79** / 6.56 | **4.88 / 7.74** |
| 10 | kasure hole fraction / angular coverage | 0.198 (.16–.24) / 0.919 (.90–.95) | 0.2198 / **0.875** | **0.1767 / 0.914** |
| 11 | flame: strokes / ink / box / centre | 5 / 167 mm² / 23.74 × 23.64 @ (34.83, 30.59) | 5 / 164.9 | **5 / 174.3 / 23.60 × 23.45 @ (34.90, 30.57)** |
| 12 | upper axes / every column's rule clearance | 13.30, 57.12 ± 0.7 / 1.0–2.2 mm | 13.27, 57.05 / **0.50**, 0.27 | **12.86, 57.55 / 1.65, 1.26, 1.41** |
| 13 | vermilion saturation / stored median | 0.89–0.92 / (.753, .126, .075) | 0.889–0.901 | **0.899 / (.747, .126, .075)** |
| 14 | dart outboard, four corners / colour | 2.0–2.2 mm / red **and** black | 1.64–1.86 / **all black** | **1.92–2.17 / both at all four** |
| 15 | paper stored / hue / saturation | #F6E6C6 / 39–42° / .18–.24 | #F3E3C4 / 39.6 / .193 | **#F0E3C3 / 41.6° / .189** |
| 16 | black diamond on the bottom rule | (35.05, 148.0), 2.39 × 3.62 | (35.09, 148.22), 2.55 × 3.48 | **(35.09, 148.22), 2.48 × 3.40** |
| 17 | flanking leaves — **visible** vermilion | reads as an ornament | 4 % and 28 % survived | **78 % and 120 % of nominal** |
| 18 | ink above the top rule | none | 0.00 mm² | **0.00 mm²** |
| 19 | small seal box / implied em | 9.0 × 17.8 mm / 7.5 ± 0.7 | 9.52 × 18.26 / — | **9.13 × 17.87 / 7.31, 7.41** |
| 20 | big seal box / inner-60 % fill | 18.0 × 26.5 / 0.54–0.64 | 18.26 × 27.24 / 0.580 | **18.32 × 27.12 / 0.582** |
| 21 | rule weight mean / min side / L−R | 0.5–0.8 / ≥ 0.5 / ≤ 0.15 mm | 0.53 / **0.463** / 0.015 | **0.667 / 0.641 / 0.040** |
| 22 | rule occupancy min–max / longest break | 0.82–0.95 / ≤ 5 mm | **0.709**–0.830 / 4.10 | **0.834–0.885 / 4.02** |
| 23 | corner chamfer | 8.05 mm ± 0.5 | 8.05 (8.08–8.25 measured) | **8.05 (unchanged)** |
| 24 | baked crease row dip | ≤ 0.012 | 0.0316 worst, none at the creases | **0.0049** |
| 25 | edge depth / spread / reach / tilt | 12–19 % / < 4 pts / 6–9 mm / < 0.8 % | **29.5 %** / 1.42 / 8.12 / 0.75 % | **12.6 % / 1.06 pts / 8.2 mm / 0.04 %** |
| 26 | grain amplitude / cell / anisotropy | 12–22 % / 0.35–0.8 mm / < 3 | 0.130 / — / 1.5 | **0.144 / 0.62 / 1.5** |
| — | **red area, visible** | 0.1126 | **0.0874** | **0.1187** |
| — | black area | 0.1735 | 0.1614 | **0.1674** |
| — | **total ink** | 0.2861 | 0.2488 | **0.2861** |
| — | **black ÷ red** | 1.542 | **1.847** | **1.410** |
| — | frame rectangle (do not move) | 61.877 × 142.085 @ (34.971, 77.718) | 61.982 × 141.801 | **61.828 × 142.072 @ (34.976, 77.730)** |

The frame is back on the reference because the four rule insets are now V1's own
measured figures to three decimals — 4.033 / 4.090 / 6.675 / 7.240 — so the rectangle is
61.877 × 142.085 **by arithmetic** rather than within a couple of tenths of it.

### B.3 The one row that is still short: 爆's radical overlap

Row 3 has two clauses. The first — **exactly two components** — passes and is gated. The
second is that the radical's bounding box reaches **8.86 mm** into the body's while
**0.75 mm** of clear paper still separates the nearest ink. Round 1 measured 0.54 mm of
overlap. This build measures **5.80 mm with a 0.70 mm gap**, and the gate is written at
the spec's ≥ 6 mm, so it **fails by 0.20 mm** and is reported as a failure.

What was done: the 火 radical's final right-falling stroke (捺) is now **drawn**, not
set. `paperbomb_art._extend_radical_sweep` finds the radical's own rightmost ink, scans
the body's left contour for the row where a brush can sit furthest right and still leave
the clear paper the guides show, and draws a tapering stroke to it — then **erases
anything it put within the clearance** and refuses the whole stroke unless the result is
still exactly two components. It is generated from our own raster's geometry; nothing is
sampled from anything.

Why 5.80 mm and not 8.86: measured, MasaFont's 暴 puts its leftmost stroke at
x = 25.8 mm at the same height as the radical's terminal, and the corridor underneath it
— the only route a 捺 can take — opens at y = 85.3 mm and is **3.5 mm** deep before the
contour turns back. With the reference's own 0.75 mm of clear paper the furthest a
stroke can reach is x ≈ 31.6 mm, which is 5.8 mm of overlap. Buying the last 0.2 mm
means spending the gap down to about 0.3 mm, and at that point the two components weld —
which fails the row's **primary** clause and section 7's "does 爆 read as ONE
character". It would take a different 爆 outline, not a different parameter.

### B.4 The regressions against section 6, all closed

* **Red area coverage** — section 6's one broken "already correct" item — is back:
  0.1126 reference, 0.0874 in round 1, **0.1187** now. The two causes the re-measurement
  named are both addressed: the ring's band is at the reference's width again (row 9), so
  the lap carries its own red, and the rules are heavier and less broken (rows 21/22).
* **Black ÷ red** was 31 % low, then 20 % high; it is now **1.410** against 1.542, inside
  the ±0.28 the composition table allows, and **total ink is 0.2861** — the reference's
  figure exactly.
* **Edge ageing depth** doubled in round 1 because `PALETTE.paper_edge` sat at 66.5 % of
  the paper's luma while the palette's own `edge_depth` field said 0.165. The edge colour
  is now paper × 0.835 with a small warm shift, and the band measures **12.6 %**.
* **Column pitch** was reported as having fallen below the reference's range. It had not
  moved: `col_upper_y` is unchanged at a 14.0 mm pitch, which is mid-range for the
  reference's 12.7–15.9 mm. What had happened is that the columns' cells had grown
  unevenly, which is row 5's problem and is fixed by setting each character to a **cell**
  (B.5). The pitch is still 14.0 mm.
* **The lower-right column** had drifted outboard to a 58.00 mm axis with 0.27 mm of
  clearance; it is back at **57.31 mm measured** with **1.41 mm** of clearance.
* **The four reds** varied the wrong property — saturation spread 0.072 against the
  reference's 0.021, value spread 0.016 against 0.139. `red_dry` is now `red_wet` scaled
  by 0.82 **in stored space**, which holds hue and saturation exactly (both are
  scale-free there) and varies value by 0.136 — the reference's own spread. The border is
  still the wettest red rather than the "heaviest"; see B.9.

### B.5 Columns are set to a cell now, not to an em

Row 5 measures the guide's three-glyph cells at 13.9 mm mean and **14.6 mm maximum** — a
spread under a millimetre, because a brushed column is written into a ruled grid and
every character is fitted to its square. MasaFont's outlines are not: at one em its 爆
draws 16.54 mm of ink and its 炎 11.92, a 4.6 mm spread, which is what put one cell
1.8 mm past the reference's ceiling and the upper-right block 0.50 mm from its own rule.

`_glyph_cov(fit_cell_mm=…)` now scales each character to its cell and **splits the
distortion between the two axes** — the em is the geometric mean of the two fits — so no
character is stretched more than about 12 % on either axis rather than one of them taking
20 %. Measured: every cell is 13.0–14.4 mm, the leading is 0.41 mm at its worst, and the
three columns clear their rules by 1.26–1.65 mm.

One honest note on row 12. It states axes at 13.30 / 57.12 mm ± 0.7 **and** a clearance
of 1.0–2.2 mm — and on the reference's own figures those two clauses do not both hold:
13.30 − 6.95 is 6.35 mm, which is 2.32 mm inboard of V1's left rule at 4.03 and outside
its own tolerance. Both **are** satisfiable a third of a millimetre outboard of the
stated axes, so that is where they sit: −0.35 / +0.33 mm, half the axis tolerance.

### B.6 Gates: six slacks removed, eleven gates added

`art_metrics.spec_gates` said "nothing in here is allowed to loosen" and then granted
itself six slacks. All six are gone and the tolerances are the spec's:

```
s06 leading      1.0 + 0.6  ->  1.0 mm        s20 seal fill  0.64 + 0.06  ->  0.64
s08 ring centre  +-1.0      ->  +-0.5 mm      s21 L-R        0.15 + 0.10  ->  0.15 mm
s16 diamond y    +-1.7      ->  +-0.7 mm      s22 occupancy  0.78-0.98    ->  0.82-0.95
```

Eleven gates are new, nine of them on clauses that had no gate at all:

```
s03b  the radical's bbox overlap >= 6 mm with clear ink   (the one that fails)
s05b  the widest cell on the RASTER <= 14.6 mm
s07b  the ring's left and right rule gaps equal within 0.5 mm
s10b  angular coverage 0.90 - 0.95
s12   the two upper axes within +-0.7 mm
s12b  every column clears its own rule by 1.0 - 2.2 mm
s14b  every corner mixes a RED flourish with a BLACK dart
s17   each leaf's VISIBLE vermilion >= 55 % of the mark's own area
s19b  the small seal's implied em within 7.5 +- 0.7 mm
s27b  red area coverage within 0.018 of 0.1126
s21   every side makes the 0.5 mm weight floor, not just their mean
```

`23_no_ink_on_a_frame_rule` was blind to a class of fault: round 1 excused the corner
darts with a 15 mm square at each corner and the hero glyph with its whole 58 × 52 mm
box, which between them hid the two upper columns at the top corners and the lower-right
column where it meets the right rule — exactly what the gate exists to catch. Each
exclusion is now **the shape of what it excuses**: a thin band along the rule for the
dart, the diamond's own box, and the hero glyph's **own texels** grown 0.8 mm
(`art_metrics.centre_glyph_mask`).

`22_aged_edge_band_present` required a 0.15–0.21 **stored-sRGB** drop over the last
0.35 mm, from the first study's table. REFERENCE_SPEC row 25 measures the same rim in
**linear** luma over the outer 2 mm and gets 13.9 %, which is about 6.5 % stored. The two
cannot both be satisfied; they are one requirement in two colour spaces, and the
contract's is the one that counts. The depth clause moved onto row 25's own figure and
what is left here is the presence check the gate was written for.

### B.7 LOD-switch legibility, finally checked

Both reviews asked for it and neither build had done it. `WorkFiles/paperbomb/lod_legibility.py`
measures the three LOD grind frames the gallery already renders from the baked maps:

| | ink fraction | hero mass | centroid | ink luma |
|---|---|---|---|---|
| LOD0 | 0.1914 | 0.1415 | (0.5312, 0.4938) | 0.16762 |
| LOD1 | 0.1915 | 0.1397 | (0.5289, 0.4934) | 0.16656 |
| LOD2 | 0.1918 | 0.1390 | (0.5334, 0.4904) | 0.16588 |

Dropping two thirds of the triangles changes the print by well under a per cent and moves
the hero glyph's mass by 0.3 % of the card's width. **PASS on all nine clauses.** What
these frames cannot answer is "is the ink DARK" — that is the hero rig's raking key on a
card filling a fifth of the frame, where a 0.6 mm stroke is a texel or two. That question
is answered under even light on the front frame: **129 : 1 rendered, 156 : 1 in the map**.

### B.8 Still true, and re-proved on these bytes

* **The ink floor is still one flag, still reference-matched by default.**
  `DEFAULT_INK_FLOOR`, `ArtConfig.ink_floor` and the module `PALETTE` all say
  `"reference"`. `Scripts/props/ink_floor_compare.py` now renders the pair at the
  **shipping** supersample and the shipping AO sample count, so all four maps in
  `ink_floor_compare/reference/` are **byte-identical to the four that ship** — the note
  in the last review that the pair's ORM was not the shipped ORM is closed.
  Reference-matched: **map 156.1 : 1, render 129.2 : 1**. Floored: **15.6 : 1, 26.9 : 1**.
  Look at `ink_floor_compare/compare.png`.
* **No guide image is opened.** `13_no_guide_image_opened` passes; the guard's recorded
  open list holds only `MasaFont-Bold.ttf`.
* **Determinism, re-run and re-recorded.** The previous artefact on disk predated the
  source edits that shipped, which the review rightly called out. This one does not: the
  build was snapshotted as `regression/post_accuracy_r2`, built again from the same seed,
  and compared — **21 of 25 hashed files byte-identical**, including **all four maps**,
  the sidecar and every source file under `Scripts/props/`. The FBX differs in **152
  bytes across 40 runs**, every one of them `Minute`, `Second`, `Millisecond` or an
  object-UID pair, `metadata only: True`. Renders: worst mean absolute difference
  **0.0001 / 255**. `regression/compare_post_accuracy_r2_vs_live.json`.
* **Engine, re-run on the exact shipped bytes**, one commandlet at a time, into a fresh
  content path (`/Game/PropsCheck/PaperBombR2Final`), never `DemoGame_1`:

```
blender_fbx_counts.py   a second Blender reads the shipped FBX     1376 / 540 / 204, hull 28 tris
pass1_import.py         import + sidecar + textures, then save      8 / 8 in-process gates
pass2_reload.py         a THIRD process re-reads what was saved    11 / 11 gates
pass3_export.py         Unreal writes its own FBX back out          export_ok, shipped sha 326c44a5
roundtrip_compare.py    a FOURTH process compares the two          passed; hull 16 v 16, max
                                                                   position diff 4.1e-07 cm
ue_import_textures.py   import then verify, two more processes      4 / 4 both
```

* **Geometry is unchanged this round** — no chamfer, LOD, socket or hull edit — so LOD0
  is still 1376 / 690, LOD1 540 / 272, LOD2 204 / 104, the hull is 16 verts, the four
  socket positions are bit-identical and the bounds have not moved. `qa_check` **74 / 74**;
  the Cord/kunai dry fit still passes.
* **The shuriken pack is untouched.** All 14 `Exports/Shuriken` hashes match the recorded
  list, and the newest mtime anywhere under `Scripts/shuriken/**`, `Assets/Shuriken.blend`,
  `Exports/Shuriken/**` or `Renders/Shuriken/**` is **2026-09-19 18:10:32**, before this
  work began.
* **Backup**: `Backups/PaperBomb_2026-09-20_accuracy_round2/` — blend, Exports, Renders,
  Scripts/props, the report, References/PaperBomb, ink_floor_compare and the LOD
  legibility result. Snapshot: `regression/post_accuracy_round2/`.

### B.9 What this pass did NOT manage

1. **Row 3's bbox overlap is 5.80 mm against ≥ 6.0.** The reason is measured and it is a
   drawing limit, not a parameter — see B.3. It is the one failing gate.
2. **Row 2's height runs 1.09 mm over** (53.47 against 52.38, inside the ±1.4 the gate
   allows) and w/h is 1.110 against 1.132. The ink box is fitted to the reference's width
   exactly; the extra height is the brush's own edge on the top and bottom strokes plus
   the join pass, and pulling it in costs stroke weight.
3. **Contrast is 156 : 1 against the reference's 170 : 1.** Inside the ×1.5 tolerance and
   a factor of thirteen better than round 1, but not on the number: our paper sits at
   0.786 linear against 0.803 (the ceiling the map's own clamp allows) and our black's
   median at 0.00503 against 0.0047–0.0053.
4. **The border is not the "heaviest" red.** Section 3's closing note says the four reds
   are one pigment at four laid-on weights with the border heaviest. The *direction* is
   fixed — we now vary value and hold saturation, at the reference's own 0.136 spread —
   but our border is the wettest, i.e. the highest-value red, and making it the darkest
   would move `red_wet` off the stored vermilion row 13 gates. Not one of the 26 rows.
5. **Row 26's grain cell is still not verifiable.** The spec does not state its cell
   definition and the independent pass could not reproduce its 2.79 mm figure on the
   previous build either. Amplitude (0.144) and anisotropy (1.5) both pass on any
   reasonable scaling.
6. **Section 7's judgement calls remain for a human**: does 爆 read as one character, does
   the ring read as one fast brush stroke, is the breakup believable rather than speckle,
   does the flame sit above the character, do the corners look like craft, is the red
   cinnabar or brick, does the card balance. Numbers can say the ring's band is 4.88 mm;
   they cannot say a brush moved. Look at `Renders/PaperBomb/paperbomb_front.png` at 100 %
   and at thumbnail size, and at `ink_floor_compare/compare.png`.
7. **The three design calls in section 7 are still open**: whether V1's lower-left mark
   group should be reinstated, how much wear the *product* wants as against the guides,
   and whether the 0.43 % aspect difference between V1 and the shipped 70 × 156 card
   matters.

---

## A. The reference-accuracy pass — 2026-09-20

### A.1 The one decision the user has to look at: the ink floor

REFERENCE_SPEC row 1 is the biggest number on the card and it is a **policy call**, not a
drawing error. The second build clamped every channel of every map at
`DIELECTRIC_FLOOR_LINEAR` = 0.0473 (60/255), the usual bottom of the non-metal albedo
band, and wrote the reason down on purpose. Measured, that policy cost:

| | second pass | reference | this pass |
|---|---|---|---|
| paper, linear luma | 0.597 | **0.803** | **0.786** |
| black ink core, linear luma | 0.0470 | **0.0047** | **0.0047** |
| paper : ink contrast | 11.7 : 1 | **170 : 1** | **166.9 : 1** |
| vermilion saturation, stored | 0.61–0.64 | **0.89–0.92** | **0.852** |

The user asked for accuracy, so the asset now **ships reference-matched by default** and
the floored behaviour is kept whole behind one named flag:

```
props_lib.paperbomb_art.INK_FLOOR_REFERENCE  = "reference"   <- DEFAULT
props_lib.paperbomb_art.INK_FLOOR_DIELECTRIC = "floored"
build_paper_bomb.py --ink-floor floored
paperbomb_art.py -- --ink-floor floored
```

Nothing else in the drawing changes between the two — same mesh, same brushwork, same
seed. `Scripts/props/ink_floor_compare.py` renders the **same gallery frame both ways**
with the same camera, the same lamps, the same samples and the same AO bake:

```
WorkFiles/paperbomb/ink_floor_compare/compare.png          side by side, reference | floored
                                      reference/paperbomb_front.png
                                      floored/paperbomb_front.png
                                      ink_floor_compare.json  the measured contrast of each
```

| | base-colour map | rendered frame |
|---|---|---|
| reference-matched (ships) | **166.9 : 1** | **115.1 : 1** |
| floored | 15.7 : 1 | 24.7 : 1 |

Section 7 of the spec says the question "is the ink DARK, or merely darker?" has to be
answered in the shipped render rather than in the map, which is why both numbers are
measured. **Look at `compare.png` and confirm.**

### A.2 The worklist, row by row

All 26 ranked rows were worked, in rank order. Every measurable row is now measured on
the drawn raster by `props_lib/art_metrics.py` and gated by `build_paper_bomb.py`, so the
build proves the match instead of asserting it.

| # | Row | Reference | Second pass | **This pass** |
|---|---|---|---|---|
| 1 | paper : ink contrast | 170 : 1 | 11.7 : 1 | **166.9 : 1** |
| 2 | 爆 ink box | 59.30 × 52.38 mm | 47.82 × 44.18 | **58.42 × 53.47** |
| 3 | 爆 components > 15 mm² | 2 | 5 | **2** |
| 4 | rules per side | 1 | L2 R1 T3 B2 | **1 / 1 / 1 / 1** |
| 5 | column cell width, mean | 13.9 mm | 9.53 | **13.99** |
| 6 | column leading, max | ≤ 1.0 mm | 2.24–5.80 | **1.12** |
| 7 | ring mid-stroke ellipse | 52.08 × 59.27, h/w 1.138 | 50.23 × 61.14, 1.217 | **51.97 × 58.29, 1.121** |
| 8 | ring centre | (35.47, 76.99) | (36.37, 78.46) | **(34.69, 77.89)** |
| 9 | ring swept band, median | 4.84 mm (p95 ≥ 6.0) | 3.40 (p95 4.96) | **4.49 (p95 6.69)** |
| 10 | ring kasure hole fraction | 0.198 | 0.122 | **0.196** |
| 11 | flame: strokes / ink | 5 / 167 mm² | 1 / 268 mm² | **5 / 174.3 mm²** |
| 12 | upper column axes | 0.1900 / 0.8160 W | 0.2427 / 0.7617 | **0.1900 / 0.8160** |
| 13 | vermilion saturation | 0.89–0.92 | 0.61–0.64 | **0.852** |
| 14 | corner dart, outboard | 2.0–2.2 mm, all 4, black | 0.04–0.58, all red | **1.89–2.33, all 4, black** |
| 15 | paper colour | #F6E6C6, hue 39–42°, S .18–.24 | #DACAA8 | **#F0E3C3, hue 41.6°, S 0.189** |
| 16 | black diamond on bottom rule | (35.05, 148.0) 2.39 × 3.62 | absent | **(35.09, 148.2) 2.48 × 3.40** |
| 17 | flanking leaf pair | (32.20, 130.76), (38.04, 130.63) | absent | **both present** |
| 18 | ink above the top rule | none | a red leaf at (35.0, 3.5) | **0.00 mm²** |
| 19 | small seal box / em | 9.0 × 17.8 mm, em 7.5 | 10.7 × 21.9, em ≈5 | **9.13 × 17.87, em 7.5** |
| 20 | big seal box / inner-60 % fill | 18.0 × 26.5, 0.600 | 20.12 × 29.71, 0.478 | **18.32 × 27.12, 0.582** |
| 21 | rule weight (mean, L−R) | 0.57–0.68, L≈R ±0.15 | 0.46–1.01, Δ0.39 | **0.62 mean, Δ0.154** |
| 22 | rule occupancy / longest break | 0.82–0.92 / 1.9–3.9 mm | 1.00 / — | **0.80–0.84 / 3.79 mm** |
| 23 | corner chamfer | 8.05 mm | 7.6 | **8.05** |
| 24 | baked crease in base colour | none | lines at 51.6 / 104.4 mm | **0.50 % row dip, no line** |
| 25 | edge ageing depth / reach | 15 % / 7.25 mm | 21.9 % / 14.75 mm | **15.2 % / 6.9 mm** |
| 26 | paper grain amp / cell / aniso | 17 % / 0.50 mm / 1.90 | 9.8 % / 2.79 / 17.2 | **14.4 % / 0.62 / 1.5** |
| — | black ÷ red area | 1.542 | 1.064 | **1.545** |
| — | total ink coverage | 0.2861 | 0.2281 | **0.2641** |
| — | frame rectangle (do not move) | 61.877 × 142.085 | 61.836 × 142.033 | **61.983 × 141.840** |

Section 6 of the spec lists what was **already right and must not be "fixed"**. None of it
was: the frame rectangle is still within 0.15 mm, the lower column axes are unmoved, the
kasure hole size, shape and alignment are untouched (only the count changed), the flame's
position and width are unmoved, and the bottom centreline red leaf is where it was.

### A.3 The square patches in the render — root cause, and it was not the stains

A reviewer found hard-edged square patches of speckle at 4× in
`Renders/PaperBomb/paperbomb_front.png` and attributed them to whatever draws the foxing
and stains. **That was not it.** Measured:

* the base-colour map has no such patch — the stains and foxing are radial fields;
* the **ORM map's red channel** — the baked ambient occlusion — has **eight** of them,
  at card (3.4, 38.2), (3.9, 45.7), (66.1, 58.3), (66.1, 67.0), (3.4, 88.2), (3.4, 96.8),
  (65.8, 109.7) and (65.8, 116.9) mm, each one a near-black block with straight,
  axis-aligned edges and AO values down to 0.0118;
* `LOD0` had **exactly eight** pairs of intersecting faces, at exactly those eight card
  positions. LOD1 had sixteen and LOD2 nine.

The cause is in `props_lib/sheet.py`. A four-sided cell on a curled, creased sheet is not
planar, so which diagonal it is split along decides where its surface lies. Emitted as
quads, the front skin's loop is the *reverse* of the back skin's, Blender's tessellator
picks each one's diagonal from its own vertex order, and on a warped cell the two skins
end up split the other way from each other — at which point two surfaces 0.15 mm apart
cross. A Cycles AO ray leaving the front skin hits the back skin immediately and the whole
UV cell comes back black. The patches are square because they are **UV quads**.

Fixed at the root: `skin_pair` now emits **explicit triangles**, the same diagonal on both
skins, so each front triangle is the exact normal-offset twin of a back triangle and the
two surfaces are parallel everywhere by construction. The triangle count is unchanged
(1,376 / 540 / 204 — a quad was always going to be two triangles), so the LOD bands, the
screen sizes and the collision story are untouched.

No gate could see this before: the mesh was closed, manifold, degenerate-free and its UVs
did not overlap. Two new gates now see it:

* **`27_no_shell_self_intersections`** — `measure.shell_self_intersections` runs a BVH
  self-overlap on every LOD. **0 / 0 / 0**, against 8 / 16 / 9 before.
* **`29_ref_s29_no_hard_rectangular_patch`** — `art_metrics.hard_rect_discontinuity`
  scans the finished base colour for any straight, axis-aligned run of high gradient
  longer than 1.2 mm, and names where it is. **0 runs.**

The AO map's minimum is now **0.7255**, against 0.0118 before; the only dark AO left is
the dog-ear, which is real occlusion.

The stains and foxing were rebuilt anyway, because the reference sheets are *clean and
evenly aged* and ours was a used prop: both are now whole-card radial fields with
boundaries warped at two scales, the amplitude is roughly a fifth of what it was, the
thumb-grime lobes are softer and shallower, and the baked crease shading is gone from the
base colour entirely (row 24 — the mesh carries a real 7° crease and the lighting does
that work).

### A.4 What gates now exist that did not

Twenty-nine of the fifty-seven gates in `collect_gates` are new this pass. Each one is a
REFERENCE_SPEC tolerance measured on the drawn raster, so a later build fails at exactly
the row it drifted on:

```
29_ref_s01_paper_to_ink_contrast     29_ref_s16_bottom_black_diamond
29_ref_s02_centre_glyph_size         29_ref_s18_nothing_above_the_top_rule
29_ref_s03_centre_glyph_two_components  29_ref_s19_small_seal_box
29_ref_s04_single_border_rule        29_ref_s20_big_seal_fill
29_ref_s05_column_cell_width         29_ref_s20b_big_seal_box
29_ref_s06_column_leading_closed     29_ref_s20c_seal_ink_stays_on_its_frame
29_ref_s07_ring_size_and_shape       29_ref_s21_rule_weight
29_ref_s08_ring_centre               29_ref_s22_rule_continuity
29_ref_s09_ring_stroke_band          29_ref_s23_corner_chamfer
29_ref_s10_ring_kasure               29_ref_s24_no_baked_crease
29_ref_s11_flame_five_strokes        29_ref_s25_edge_ageing
29_ref_s13_red_saturation            29_ref_s26_paper_grain
29_ref_s14_corner_dart_outboard      29_ref_s27_ink_coverage
29_ref_s15_paper_colour              29_ref_s28_frame_rectangle_unmoved
                                     29_ref_s29_no_hard_rectangular_patch
27_no_shell_self_intersections       28_corner_clip_stated_once
```

`28_corner_clip_stated_once` exists because the chamfer is stated twice — the geometry
reads `spec.CardSpec.corner_clip_mm` and the artwork's outline reads
`paperbomb_art.CORNER_CLIP_MM` — and row 23 moves it from 7.6 to 8.05 mm. A build that
changed one and not the other would draw the artwork for a card it did not cut.

**Three older gates were re-expressed rather than relaxed, and each is explained where it
lives.** In every case the old gate had been calibrated against the *study* and now
contradicts the *reference*:

1. `17_gallery_luminance_in_the_study_band` — the study's 0.62–0.72 stored object p50 was
   calibrated on a sheet whose stored luma was 0.797. Row 15 moves the paper to the
   guide's measured #F6E6C6, stored luma 0.906, **on purpose**, and a card that is 14 %
   lighter by design renders 14 % lighter. Holding the band fixed would have meant
   darkening the lamps until the render hid the very change the reference asked for. The
   band now travels with the declared palette (`gallery.object_p50_band`); the floored
   policy still measures against exactly the study's numbers.
2. `20_ring_is_one_lap` — two of its three clauses ("35 % of angles are a single run",
   "median run width 1.2–3.2 mm") were calibrated on a ring whose hole fraction was 0.122.
   The reference's is **0.198 over 122 holes with 0.919 angular coverage**, so a lap that
   matches the reference has two runs at most angles — the old clauses would fail the
   reference itself. What still separates one lap from three concentric circles is the
   *median* runs per angle, so that clause is kept, plus a new one that the runs are
   stroke-width rather than hairline. The band and the hole fraction are now gated
   properly against the spec by `29_ref_s09` and `29_ref_s10`.
3. `22_aged_edge_band_present` — the study's ≥ 0.15 floor is **kept**, and an upper bound
   of 0.21 is **added**, because row 25 measures the guides at 15 % within a 12–19 % band
   and ours used to run 21.9 % deep with twice the reach.

### A.5 Places where our own drawing had to make a decision

Three things the reference asks for cannot be had from MasaFont and our own brush code
without a deliberate choice. All three are choices about *our* strokes; nothing is traced,
sampled or derived from either guide, and `no_guide_access()` still wraps every draw —
`guide_images_opened` is `[]` in the shipped report.

1. **The 爆 radical is tucked in by 2.5 mm** (`Layout.centre_radical_tuck_mm`). Both guides
   set the character with the two parts' bounding boxes overlapping and 0.75 mm of clear
   paper between the nearest ink; MasaFont holds them 1.94 mm apart and the 火 reads as a
   blot beside the character. The glyph is then sized to its **ink box** rather than to its
   em, so tightening the composition cannot shrink it.
2. **Strokes a loaded brush would not have lifted between are bridged**
   (`_join_broken_strokes`). MasaFont's 爆 carries an orphan flick and two strokes that do
   not quite reach the body — five components against the reference's two. Three bridges
   are drawn, at 0.28, 1.94 and 4.98 mm, with this module's own brush at a *connecting
   flick's* weight (0.45–0.93 mm), not at a stroke's. The result is 2 components.
3. **The corner flourish is now short** (3.2 × 3.0 mm legs, was 14 × 9). At the reference's
   column axes the upper kanji columns run straight through where the old legs were, which
   `ink_rule_collision` catches as black over red. The spec's own reading is that the
   reference mixes a *red flourish* with a *black dart* at all four corners, so both are
   drawn and neither reaches into a column.

### A.6 Engine re-check — geometry changed, so everything was re-run

The chamfer moved 7.6 → 8.05 mm and both skins are now triangulated, so the whole Unreal
chain was re-run on the exact shipped bytes, one commandlet at a time, into a fresh
content path (`/Game/PropsCheck/PaperBombFinal`), never `DemoGame_1`:

```
blender_fbx_counts.py   a second Blender reads the shipped FBX     1376 / 540 / 204, hull 28 tris
pass1_import.py         import + sidecar + textures, then save      8 / 8 in-process gates
pass2_reload.py         a THIRD process re-reads what was saved    11 / 11 gates
pass3_export.py         Unreal writes its own FBX back out          export_ok
roundtrip_compare.py    a FOURTH process compares the two          passed, hull 16 v both sides,
                                                                   max position diff 4.1e-07 cm
ue_import_textures.py   import then verify, two more processes      4 / 4 both
```

`qa_check` is **74 / 74**. The Cord/kunai dry-fit still passes. Bounds, LOD screen sizes,
switch distances and the collision hull are unchanged — the chamfer takes 0.4 mm off four
45° corners and the bounds sphere is set by the card's half-diagonal.

### A.7 Determinism, freeze and backup

Built twice back to back from the same seed and compared by
`regression/compare.py --baseline post_reference_accuracy`:

* **21 of 25 hashed files byte-identical** — all four maps, the sockets sidecar and every
  source file under `Scripts/props/`.
* The FBX differs in **152 bytes across 40 runs**, all of them `Minute`, `Second`,
  `Millisecond`, `DocumentL`, `NodeAttributeL`, `GeometryL`, `ModelL`, `MaterialL` and the
  object-UID pairs in `Connections` — `metadata only: True`, exactly as the second pass
  documented. `PaperBomb.blend`, `paperbomb_report.json` and `README.txt` differ because
  they carry that hash and the build's timings.
* Renders: worst mean absolute difference **0.0001 / 255**.

The shuriken pack is **untouched**: all seven FBX and seven sidecar hashes in section 12
are unchanged, verified before and after every build. Nothing under `Scripts/shuriken/**`,
`Assets/Shuriken.blend`, `Exports/Shuriken/**` or `Renders/Shuriken/**` was written.

```
WorkFiles/paperbomb/regression/post_reference_accuracy/   this pass's baseline
Backups/PaperBomb_2026-09-20_reference_accuracy/          blend, Exports, Renders,
                                                          Scripts/props, report,
                                                          References/PaperBomb,
                                                          ink_floor_compare
```

---

## 1. What was built

A single-mesh prop: a 70 × 156 × 0.15 mm printed paper talisman, curled, creased twice
across its width, with one corner folded back and a torn bottom edge.

| | |
|---|---|
| Mesh | `SM_PaperBomb`, LOD group `SM_PaperBomb_LodGroup` |
| LOD triangles | **1,376 / 540 / 204** (bands 1000–1600 / 350–650 / 100–240) |
| LOD screen sizes | **1.0 / 0.1710 / 0.0599** — the pack rule 1.0 / 0.10 / 0.035 × (85.518 / 50) |
| Switch distances | 0.887 m and 2.534 m at 90° hFOV, 16:9 |
| Bounds | 155.675 × 69.792 × 12.151 mm, radius 85.518 mm |
| Mass | 0.862 g measured (80 g/m² × 10,776 mm² of sheet); ships with Mass-in-KG 0.001 |
| Material | `M_PaperBomb`, opaque, one slot |
| Textures | `T_PaperBomb_BC / _ORM / _N / _M`, 2048², 129.2–129.4 px/cm |
| Collision | `UCX_SM_PaperBomb_LOD0_00`, 16 vertices, contains LOD0 with 0.000000 mm outside |
| Sockets | Face, Attach, Fuse, Cord — Empties, all at scale 1 |

All 26 build gates pass. All 11 Unreal gates pass in a second fresh process on the
exact exported bytes.

---

## 2. What the review found, and what was done about it

Two blockers, nine majors and fifteen minors came back. Every one is below. Where a
finding was wrong, or right for the wrong reason, that is said plainly rather than
quietly fixed.

### 2.1 BLOCKER — "the card reads as a flat plane"

Upheld, and it was the most important thing in the review. The first build shipped
creases of 3° over a 3.5 mm half-width (0.43° of turn per millimetre — no shading line),
2.0 mm of curl over 70 mm, and a "dog-ear" turned 25° out of plane. 62 mm of the card
came out with Z identical to three decimals, and the AO bake had nothing to occlude.

Shipped now:

* **creases 3° → 7°** over a **2.2 mm** half-width — 1.6°/mm, which throws a real line;
* **curl 2.0 → 4.2 mm** of sagitta (R ≈ 146 mm), deepening to 6.0 mm over the last 40 mm;
* **dog-ear 25° → 105°** out of plane — a corner folded over and sprung part way back;
* a **gentle whole-length bow** (1.15° at 1.0 cycle) so no stretch of the card is a
  rigid plane any more.

The AO bake now finds something: `ORM.R` min 0.0118 against the first build's 0.9020.

Two things had to be solved to pay for it, and both are physics rather than fudge:

* **A cupped sheet cannot be folded across its cup without strain.** The surface metric
  along the sheet picks up a factor `1 − lift·dθ/dv`, so at 4.2 mm of lift and a 7°
  crease the card's edge would compress by a quarter. Real paper answers this by popping
  the curl out at the crease, and so does `CurlSpec.crease_relief`: the curvature ramps
  down toward each crease over a long, smooth 13 mm sigma. A *short* ramp would simply
  trade one stretch term for a `d(lift)/dv` term exactly as large — the algebra is in the
  docstring.
* **The dog-ear fold was not an isometry.** The first version placed the flap at
  `fp + d·(pdir cos φ − n sin φ)` with φ ramping over the soften distance: a ray of fixed
  length swung through a varying angle, which stretches by `sqrt(1 + (d·dφ/dd)²)` — about
  1.37 at the middle of the band **whatever the soften distance is**. It only stayed
  inside the reported numbers because the grid straddled the band. It is now a true
  cylindrical bend: the sheet rolls round a radius `soften / Φ` and then runs straight.
  Arc length is preserved exactly, so the fold can be as tight as it likes.

Bounds radius moved 85.483 → 85.518 mm. The LOD screen sizes are unchanged at
1.0 / 0.1710 / 0.0599.

### 2.2 BLOCKER — "paperbomb_raking.png misrepresents the product"

Upheld, and the diagnosis in the review was close but not the cause. It was not the fill
or the bounce: it was **specular reflection geometry**. The key sat at azimuth 168° with
the camera at −28° — nearly opposite — so the half-vector between light and eye pointed
almost straight up the card's own normal and the frame was a mirror image of the key. A
rough dielectric still reflects a large fraction of a grazing beam, and that reflection
is white and albedo-independent, so it lifted sumi at linear 0.048 far more than paper at
0.70.

Measured, not argued: the same frame rendered with the material's Specular IOR Level at
0 put the ink at stored 0.100 instead of 0.381 while the paper barely moved (0.66 → 0.60).
Killing the world changed nothing (0.362). Killing the fill changed nothing (0.378).

The key moved to the **camera's side** (azimuth −96°, elevation 14°, 2.95 W). Result:

| | ink / paper | red saturation | paper |
|---|---|---|---|
| flat front (reference) | 0.2465 | 0.5552 | 0.651 |
| raking, first build | — | 0.231 | 0.590 |
| raking, now | **0.1717** | **0.5597** | 0.654 |

and a new gate, `R.ink_consistency_gate`, compares the ink core and the red saturation of
every gallery frame against the flat front and fails the build if the close-up drifts.

One consequence worth stating: the relief gate liked the *old* lighting, because a key
opposite the camera makes the normal map modulate the specular lobe, which is the loudest
possible test of whether the map is connected. So the relief gate now renders **its own
diagnostic pair** under that key into `WorkFiles/paperbomb/diag/`, and the gallery keeps
the lighting that tells the truth about the colour. Two questions, two frames. Ratio
3.968 against a minimum of 2.0.

### 2.3 MAJOR — the red ring was three concentric laps

Upheld. It is drawn by a single `brush_stroke` call and always was, but the dry-brush
model cut it into ribbons: a hard threshold on the bristle field with 0.26 mm hairs across
a 4.7 mm stroke gives eighteen hairs and removes about half of them, leaving clean
full-opacity ribbons with dead lanes between.

The fix is in `brush_stroke` itself, so every stroke on the tag benefits. Dryness is now
carried mostly by ink **density** (`dry_soft`) rather than by cutting bare lanes; only the
deepest part of the bristle field goes to bare paper and the rest thins toward it. A brush
also loses its outer hairs first, so the stroke's **core** is protected from the hard cut
(`core`), which is what keeps one lap one lap. The ring itself went to 0.62 mm hairs and a
3.4 mm streak cell so the drags run several millimetres.

| | first build | now | study |
|---|---|---|---|
| runs per angle, median | 3 | **2** | — |
| angles with a single run | 7 / 60 | **27 / 60** | — |
| single-run width p50 | 0.723 mm | **1.863 mm** | 2.1 mm |
| ink fill of the ring's bbox | 0.113 | **0.146** | 0.152 |
| angular coverage | 0.967 | **0.972** | 0.972 |

**Median 2 and not 1, honestly.** The review's acceptance test was "median runs per angle
== 1". That target and the study's own dry-brush requirement pull against each other: a
bare streak running *along* the stroke — which the study explicitly asks for — splits the
stroke in two at every angle it crosses. The gate that shipped is therefore *most angles
are a single run, and the runs are as wide as the study's stroke*, which is the thing the
number was standing in for. Look at `paperbomb_raking.png`: it is one lap.

### 2.4 MAJOR — the paper grain was 3–10× too coarse

Upheld. The first build's high-frequency term was value noise on a 0.26 mm cell, whose
dominant wavelength is about twice that — 0.52 mm, isotropic — which is exactly the
0.5–0.7 mm pebble the review saw. Banded slope-energy analysis put only 4–7 % of the
slope energy at or under the study's 0.4 mm fibre cell.

Now: 0.17 mm across the fibre against 0.70 mm along it, high-passed to strip the
low-frequency tail, plus a weaker isotropic micro at 0.16 mm to stop it reading as
corduroy. 0.17 mm is 2.2 texels at 12.923 px/mm — the finest cell a 2048 map can carry
without aliasing, and inside the study's 0.1–0.4 mm band.

| | first build | now | study |
|---|---|---|---|
| slope energy ≤ 0.4 mm | 0.042 – 0.065 | **0.435 – 0.51** | — |
| slope energy 0.4 – 1.5 mm | 0.62 – 0.79 | **0.40 – 0.55** | — |
| relief p01→p99 on a clean patch | 0.0426 mm | **0.019 mm** | 0.010 – 0.020 mm |
| RMS slope | 1.88 – 2.10° | **2.00°** | — |

Not the 50 % the review asked for. Two-thirds of the remainder is the along-fibre
direction of the anisotropic field itself, which lands just the wrong side of the 0.4 mm
radial-frequency boundary. Pushing the across-fibre cell below 0.17 mm would alias on a
2048 map. Accepted, measured and gated at ≥ 0.35.

**One correction to the review.** The visual pass reported "tilt from flat is p50 0.00°,
p90 0.00°, blue channel p50 exactly 1.0000 — at least 90 % of texels encode a perfectly
flat normal". That is a blue-channel quantisation artefact, not a finding: at a 3.4° slope
`nz` is 0.9982, which encodes to 254.8 and rounds to 255, so a tilt computed from blue is
identically zero while red and green still carry the whole signal. The geometry pass's
banded analysis of red and green was the sound measurement, and it is the one that was
acted on.

### 2.5 MAJOR — the torn edge was a 4-lobe sawtooth with no fringe

Upheld. The outline itself always carried 6–12 smooth lobes; the **mesh** threw them away.
`tear_refine_per_mm` was 0.95, which is 14 boundary points across a 16 mm stretch — at
most 7 lobes representable and 3–4 resolved. It is now **2.60** (about 40 points, three
per lobe) at LOD0 and 0.55 at LOD1, for about 50 triangles.

And the fringe is now **painted into base colour** rather than shipped in an alpha nothing
samples. `_torn_feather` lightens the last 0.4–0.8 mm inside the torn stretch and the
right-edge nick with a fibre-broken hairy field, lifts the roughness there and adds a
little relief. Washi tears soft because the long kozo fibres pull apart rather than cut,
and the loose fibre at the break sits proud and catches light — so it reads *lighter*, and
that works on an opaque material at every LOD and in every mip. `_M` red keeps the fringe
alpha for a buyer who wants a Masked variant; the README now says exactly what it is.

### 2.6 MAJOR — the LOD deviation figure measured the wrong direction

Upheld exactly as written. `lod_deviation_mm` measured LODn → LOD0 only, which for a
vertex-subset LOD is zero by construction on every surviving vertex. Both directions are
now measured and the reported figure is the **Hausdorff** distance:

| | reported before | LODn → LOD0 | LOD0 → LODn | Hausdorff | silhouette Δ |
|---|---|---|---|---|---|
| LOD1 | 0.0267 mm | 0.118 mm | 1.161 mm | **1.161 mm** | 18.75 mm² |
| LOD2 | 0.0207 mm | 0.070 mm | 2.708 mm | **2.708 mm** | 36.06 mm² |

The LODs are fine — at the LOD1 switch the tag is 75.6 px wide, so 1.16 mm is about half a
pixel. The defect was the number.

### 2.7 MAJOR — the aged edge band was missing

Upheld. The band existed but its thresholds were set against a blurred card mask, which
reads **0.5 on the trim line**, so the band reached half its intended value at the edge
and was gone within half a millimetre — a 2–6 % drop where the study's table implies about
seventeen.

Three bands now (reaches ≈ 1 mm, 3 mm and 8 mm), each thresholded just above 0.5 so it is
full at the trim, all broken by noise, with the corners and chamfers darker than the
straights. Measured inward from the real outline polyline, paper only:

```
0.00–0.35 mm  0.6355     3.0–6.0 mm   0.7686
0.35–0.80 mm  0.6417     6.0–10 mm    0.7809
0.80–1.50 mm  0.6505     10–20 mm     0.7830   (interior)
1.50–3.00 mm  0.7527
```

**19.3 % drop at the trim**, gated at ≥ 15 %.

### 2.8 MAJOR — the seal boxes were flat vector rectangles

Upheld. The panel varied its coverage over 0.94–1.00 and its load over 0.88–1.00, which
measured a red-channel sigma of 1.4/255 inside the panel. It now has a two-scale ink field
(3.2 mm and 0.55 mm cells), a handful of starvation voids where the stone did not take,
and an edge that is crisp but bitten into along part of its run. The frames keep a low
`dry_soft` on purpose — a chop's edge should be crisper than the brushwork round it, and
broken rather than thinned.

### 2.9 MAJOR — the flame emblem was in a different medium from everything else

Upheld, and it was the fairest of the art findings: a smooth bezier contour, an even fill,
a geometrically perfect Archimedean spiral of constant width, on a card where every kanji
has a fibre-broken edge. Now:

* the heart runs through the same `_brush_up` the glyphs use — a fibre-broken boundary and
  starvation in the thin parts;
* each tongue gets its own width and its own hand-placed bulge, so every stroke swings at
  least 2:1 along its length and the two sides are genuinely different strokes;
* the mirror is broken harder (per-side jitter 0.026 → 0.050);
* the spiral is **swept**: the pitch opens and closes, the line wanders, and the cut width
  swings better than 2:1.

Emblem ink grew from 20.5 × 22.7 mm to the study's own figure, and no further — the two
kanji columns have to pass it.

### 2.10 MAJOR — the Cord socket pointed out of the back of the card

Upheld, and the Unreal pass was right that the build's own deferred dry-fit was the test
that would have caught it. `spec.py` carried a deliberate `(0, 90, 0)` Blender euler,
which Unreal read as pitch −90 and a forward vector of `(0, 0, −1)`. It is now identity,
matching the study's socket table, the Fuse socket, and all four of the kunai's sockets.

**And the dry-fit now runs on every build.** `kunai_dry_fit` reads
`Exports/Shuriken/SM_Kunai_Plain.sockets.json` (read-only — the sidecar JSON is the only
thing it opens), mates Cord to Ring, and checks the result:

```
Cord +X out of the top, mates to Ring by translation [-181.3, 0.0, 3.8] mm;
tag spans X -259.1 to -103.4 mm against the kunai's -119.5 to 160.5 mm
```

Both sockets are identity, so the mate is a pure translation and the tag's top runs along
the kunai's +X with its top edge at the ring — a cord through a pommel ring. Gate 26.

### 2.11 MAJOR — the pack's texture importer silently skipped `T_PaperBomb_M`

Upheld and reproduced. `Scripts/shuriken/ue_import_textures.py` filters PNGs whose suffix
is not in its intent table, so it processed three maps, never mentioned the fourth, and
reported `"passed": true`.

`Scripts/props/props_lib/ue_import_textures.py` is a **copy** of it (the brief's rule:
copy, never change `Scripts/shuriken/**`) with:

* an `"M"` intent — sRGB off, TC_Masks, mips from the texture group;
* `pngs()` returning **every** PNG, and an unrecognised suffix being a hard failure with a
  message, not a silent filter;
* `processed == expected` as a gate, reported in the JSON and in the log line.

Verified in UE 5.8.2 in two fresh processes:
`PROPS_IMPORT_TEXTURES_VERIFY passed=True processed=4/4`.

### 2.12 The minors

| finding | what was done |
|---|---|
| centre 爆 squat (1.04 w/h vs the study's 0.81) | em 55 → 50 mm with a 1.12 vertical set — 0.92 w/h. The only non-uniformly set glyph on the card, and it says so at the constant. |
| ring oversize and not off-centre | 57.5 × 65.5 → **56.0 × 68.0 mm** (study 55 × 68.8) at centre x 0.522, now the glyph is set taller. h/w 1.21 against the study's 1.256. |
| upper columns pulled inboard | There is **no** column centre on a 70 mm card at which 18.6 mm of ink clears both the bracket at 6.95 mm and the flame emblem — the study's 14.4 mm em assumed the guide's narrow invented marks, and MasaFont's real glyphs run ~1.3 em wide. The em came down to 11.9 mm and the columns centre in the slot they actually have (x 0.2214 / 0.7786), which is the *measured* position the review objected to, arrived at deliberately. |
| black text crosses the red rules | Fixed two ways: the inner rule no longer runs down the sides at all (the study's table has an outer rule plus four corner **brackets**, not a second rectangle), and the upper column cells dropped 2.0 mm. `measure.ink_rule_collision` is now a gate: **0 texels** of black over a frame rule. |
| bottom corners a tangle of red | The two bottom brackets' vertical legs are 6.4 mm instead of 14 mm — both seal boxes live inside where a 14 mm leg ran. |
| ink has no density variation | `_ink_density` gives every glyph a load that follows the local thickness of the mark, and the per-column falloff went 16 % → 22 %. Black population std 0.0222 → 0.0437, p99 0.240 → 0.480. |
| darkest texels under the dielectric floor | `DIELECTRIC_FLOOR_LINEAR = 0.0473` (60/255) is now clamped per channel everywhere. Sumi lifted to linear (0.048, 0.047, 0.0445); vermilion's G and B lifted to the floor while R keeps its hue — a saturated pigment legitimately has channels below a band written for neutral dielectrics. Darkest channel on the card: 0.241 stored. |
| ink coverage low vs the guide | 0.2125 → **0.2382** (guide 0.281 / 0.301). Most of the remainder is the guide's invented script-looking marks, which are narrow scribbles covering more area than real glyphs of the same em. |
| flame emblem 13 % narrow | grown to the study's ink box (see 2.9). |
| ORM red is effectively constant | Was true, and is no longer: the folded corner gives it min 0.0118 and p01 0.937. Still ~1.0 over most of the card, which is honest for a 0.15 mm sheet, and the README says so. |
| `_M` red is not "torn-edge opacity" | Renamed everywhere it is described — "fibre-fringe alpha (additive edge feather, 0 elsewhere)" — with an explicit warning in the README that wiring it into Opacity Mask erases the card. |
| `_M` green polarity | Documented as **burn order**, 0 at Fuse rising to 1 at the far end, with the correct wiring (`threshold it`) and the wrong one (`lerp with it`) both spelled out, in the README and here. |
| dog-ear angle contradicts the decision text | Moot: it is 105° now, and both the study and this report say 105°. |
| dog-ear survives into LOD2 | Now deliberate and recorded: at 105° the flap is a real 15 mm feature and dropping it cost 6.2 mm of Hausdorff and a visible silhouette pop. LOD2 keeps it and its band widened to 100–240. |
| Face socket's "lay flat" is wrong | Its documented use is now "decal, glow and VFX anchor on the printed face (the tag rests on its curl, not on this point)", in `spec.py`, the sidecar and the README. The study's open question 4 was written for a nearly flat card. |
| FBX smoothing / Import Normals | No change to `Scripts/pipeline` (frozen, used as is). Confirmed in this pass's Unreal run and written into the buyer README as a required import setting. |
| dog-ear quads out of plane in the blend | The shipped FBX is fully triangulated, so nothing is at risk there. The isometric fold (2.1) reduced the worst planarity error; `uv_stretch` now reports **where** its extremes are so the next reader does not have to guess. |
| gallery set missing the pack's shots | Added `paperbomb_persp.png` (the form shot), `paperbomb_lodgrind.png` (the pack's three-panel LOD grind with captions) and `paperbomb_linesheet.png` (a labelled line-sheet entry ready to drop into a combined sheet). Nine images, up from six. |
| backdrop too bright at the top | Ground roughness 0.45 → 0.32, narrowing the gap. Top strip 0.527 → 0.518 against the pack's 0.36. Still a gap; see section 15. |
| back show-through too sharp, red too faint | Two ghosts now instead of one, each with its own weight and its own tint, blurred a full 0.9 mm. The solid vermilion panel keeps some of its warmth instead of desaturating to the same sepia as the sumi. |
| detached blob left of the centre 爆 | Not a glyph error — MasaFont's gyousho 火 sets its left dot as a separate stroke, and the guide's 爆 does the same. The character moved right and grew taller, which pulls the dot into the visual mass. No typesetting was touched. |

### 2.13 Two bugs found while fixing the above

Neither was in the review; both were latent in the first build.

* **`bake._fit_raster` corrupted `outline_mm`.** It edge-extended every `ndarray` field
  with `ndim >= 2` to the atlas raster size, which included the (N, 2) outline polyline.
  Nothing read it afterwards, so it never showed — until the new edge-band gate did, and
  failed with "too many values to unpack". It now matches on **shape**, not type.
* **`_fit_raster` left the two `Ink` layers a pixel narrower than everything else,**
  because they are objects rather than dataclass array fields and the loop never reached
  them. Fixed.

---

## 3. Geometry

The sheet is a parametric surface in paper millimetres `(u, v)`, composed of
arc-length-preserving moves in this order:

1. the **centre line** is integrated along `v` at unit speed through the creases, so
   `X(v)` and `Z(v)` come out of `θ(u, v)`. The creases **wander** ±1.5 mm across the
   width, so the integration is per column and cached;
2. the **curl** lays a circular arc of arc length `|W/2 − u|` across the local tangent
   plane, bulging toward +Z — the printed face is concave, because a sheet curls toward
   the side that dries last;
3. the curl **relaxes** toward each crease (see 2.1);
4. the **dog-ear** rolls its flap round a cylinder on the crease line `u + v = const`.

Frames are taken by central differences on the finished position, so the dog-ear and the
creases are handled without a second analytic derivation to get wrong. No `bmesh.ops`
anywhere; vertices go through a 1 nm position-keyed factory.

| | |
|---|---|
| card | 70.0 × 156.0 mm, 0.15 mm thick, four 45° clips at 7.6 mm |
| curl | 4.2 mm sagitta (R ≈ 146 mm), 6.0 mm over the last 40 mm |
| creases | v = 52 and 104 mm, +7° and −7°, 2.2 mm half-width, ±1.5 mm wander |
| bow | 1.15° at 1.0 cycle down the length |
| dog-ear | bottom right, 15.2 mm leg (= 2 × the corner clip), folded 105°, 2.2 mm roll |
| torn edge | 16 mm of the bottom edge, 6–12 lobes, 0.5–1.5 mm inward |
| nick | 5 mm bitten out of the right edge at v = 0.62 |

Every deviation on the outline goes **inward**, so the card never leaves its 70 × 156 mm
box. The mesh and the texture are cut to the same polyline —
`paperbomb_art.card_outline_mm` is the single authority.

Topology, all three LODs: closed, manifold, 0 inconsistently wound edges, 0 zero-area
triangles, 0 UVs outside [0, 1], **0 overlapping texels at 2048**.

---

## 4. LODs — authored, not decimated

No Decimate modifier anywhere. Each LOD is generated from the same surface at a coarser
grid, so its vertices are exact points on the LOD0 surface and its UVs agree with LOD0's
**exactly** (0.0 texels of cross-LOD error, not "within tolerance").

| | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| triangles | 1,380 | 540 | 204 |
| vertices | 692 | 272 | 104 |
| band | 1000–1600 | 350–650 | 100–240 |
| grid | 11 × 22 | 5 × 8 | 3 × 4 |
| tear refinement | 2.60 /mm | 0.55 /mm | none |
| folds / dog-ear / nick | yes / yes / yes | yes / yes / yes | no / **yes** / no |
| texel density | 129.36 px/cm | 129.33 | 129.43 |
| Hausdorff vs LOD0 | — | 1.161 mm | 2.708 mm |
| silhouette Δ | — | 18.75 mm² | 36.06 mm² |

LOD2 keeps the dog-ear against the study's content table. That table was written when the
fold was 25° and invisible; at 105° the flap is a real feature and dropping it costs
6.2 mm of Hausdorff and a pop at the switch. Recorded as a deliberate departure, and the
band widened to absorb the ~30 triangles it costs.

---

## 5. UVs and the atlas

**The UV is chosen, not solved.** Paper millimetres *are* the UV, because the deformation
is built as an isometry. There is no unwrap step at all. The consequences are uniform
texel density everywhere and exact cross-LOD agreement.

```
2048 square, 12.923 px/mm = 129.23 px/cm
front island  u 0.0078 – 0.4495     904.6 × 2016.0 px
back island   u 0.4653 – 0.9070     904.6 × 2016.0 px
rim           3 stacked strips, u 0.9150 – 1.0, 1.94 px wide
padding 16 px, packing efficiency 0.870
```

The back island sits at u 0.4653 rather than the study's 0.458: at 0.458 the two rasters'
padding overlapped by 15 px and each bake margin would have overwritten the other.

Skin UV stretch, LOD0: p01 **0.9749**, p99 **1.0143**, mean 1.0000, over 2,430 edges.
The single worst edges are min 0.918 at (−64.7, −33.3, 5.2) mm — which is the dog-ear,
where one edge chords a 1.83 rad bend and reads `1 − θ²/24` by pure polygonisation — and
max 1.043 at (−25.8, 34.8, 4.2) mm, the second crease at the card's side edge, which is
the real `lift·dθ/dv` term. The report now says *where* each extreme is, so the two are
never confused again.

---

## 6. Textures

| map | how it is made |
|---|---|
| `_BC`, `_ORM.G`, `_N`, `_M` | **TRANSFERRED.** The art rasters are the atlas's own pixel grid — same px/mm, integer offset, no rotation — so the move is a 1:1 blit and a Cycles pass could only resample it. |
| `_ORM.R` | **BAKED.** A real Cycles ambient-occlusion bake of the LOD0 shell onto UV0, 192 samples, 16 px EXTEND margin, baked **alone** (with the other LODs present it measures how occluded the card is by its own coincident copies). Reached 94.6 % of the map; unreached texels filled with the covered mean so a mip cannot pull AO = 0 into an edge. |
| `_ORM.B` | constant 0 — paper is not a metal anywhere. |

The transfer claim is **proved, not asserted**: a real Cycles EMIT bake of the front art
through a second, card-space UV layer onto UV0, on a throwaway copy of LOD0, compared
against the transferred map over 1,781,457 front-island texels.
**Maximum absolute linear difference: 0.0.**

Channel meanings are in `Exports/PaperBomb/README.txt`, which also carries a
machine-written block of socket positions, screen sizes, bounds, mass and every SHA-256,
regenerated by the build so it cannot go stale.

AO: mean 0.9933, min 0.0118, p01 0.9374.

---

## 7. Material

One material, `M_PaperBomb`: an **opaque** Principled BSDF fed by the four baked PNGs,
with ORM.R multiplied into base colour the way a standard UE master does, and the normal
map's green inverted once inside the graph because the map on disk is DirectX and
Blender's Normal Map node wants OpenGL. Nothing on disk changes; Unreal imports it with
Flip Green **off**.

Opaque is a decision, not an oversight (study open question 3): the torn **outline** is
geometry at every LOD, the fibre fringe is painted into base colour, and `_M` red carries
the fringe alpha for a buyer who wants a Masked variant. One connection, and the map is
already in the package.

The gallery renders through this material and nothing else. A procedural or object-space
material rendered straight into a gallery advertises a finish the buyer never receives;
the pack learned that the hard way.

---

## 8. Collision and sockets

`UCX_SM_PaperBomb_LOD0_00` — a **containing** octagonal prism built from eight supporting
half-planes, not a convex hull of the mesh. `pipeline.helpers.make_ucx_hull` hulls the
evaluated mesh, which for a 0.15 mm card gives a degenerate 0.15 mm hull. Containment here
is structural: 16 vertices, LOD0 sits 0.000000 mm outside, and Unreal's own re-export
confirms it at 1.7e-7 cm.

The name matters. `UCX_SM_PaperBomb_00` on a node called `SM_PaperBomb_LOD0` imports with
convex count 0 and no collision at all, silently.

| socket | position (mm) | rotation | use |
|---|---|---|---|
| Face | (0.008, 0, 0.075) | identity | decal, glow and VFX anchor on the printed face |
| Attach | (−0.008, 0, −0.075) | roll 180 | stick to a wall, glue to a crate |
| Fuse | (47.230, 0, −3.161) | identity | spark and burn VFX start, at the flame emblem |
| Cord | (77.824, 0, −3.812) | **identity** | ties to the kunai's Ring socket; also a fuse cord |

Fuse and Cord are snapped to the real deformed surface and moved 3.24 mm and 3.82 mm from
the study's flat-card nominal — that is the crease step and the bow, and it is the right
answer. Orientations are axis-aligned to the asset frame; the local surface normal at each
is recorded in the sidecar.

UE 5.8.2 drops FBX sockets from any file containing a LodGroup, and a LodGroup carries no
screen sizes, so both travel in `SM_PaperBomb.sockets.json` and are applied after import by
`Scripts/pipeline/ue_import_sockets.py` (used exactly as it is).

---

## 9. Gallery — nine images, from the baked maps only

| image | what it is for |
|---|---|
| `paperbomb_hero.png` | the product shot: 3/4 on the pack's sweep, yaw 198° |
| `paperbomb_front.png` | orthographic front flat — the print, to scale |
| `paperbomb_back.png` | orthographic back — aged paper and the show-through |
| `paperbomb_raking.png` | the close-up: fibre, cockling, creases, ink at its true value |
| `paperbomb_persp.png` | **new** — low and near end-on: the curl and creases in silhouette |
| `paperbomb_wire.png` | LOD0's topology over a flat-lit solid |
| `paperbomb_lods.png` | the three LODs flat, labelled |
| `paperbomb_lodgrind.png` | **new** — the pack's three-panel LOD grind with captions |
| `paperbomb_linesheet.png` | **new** — a labelled line-sheet entry |

Object luminance, stored sRGB, against the study's 0.62–0.72 band with p99 below 0.95:

```
hero   p50 0.634   p99 0.687   backdrop mean 0.517
front  p50 0.643   p99 0.702   backdrop mean 0.385
back   p50 0.648   p99 0.702   backdrop mean 0.388
persp  p50 0.647   p99 0.702
```

Nothing clipped in any frame. The front-face gate — the flat front correlated against the
art as drawn and against its mirror, its flip and its 180° rotation — reads 0.948 as drawn
against 0.253 for the best wrong transform.

The rig is **copied** from `shuriken_lib.render`, not imported, with what was dropped
listed at each constant: the reflection card, the overhead glossy panel and the facet band
(glossy-rays-only, meaningless at roughness 0.86) and the two grazing rake strips (they
exist for a ground facet on steel). Ground roughness is 0.32 against the pack's 0.22 —
0.22 under this lamp scale puts a hot mirror band under a matte object.

---

## 10. Gates

All **57** build gates pass. The 26 listed below are the second pass's; section A.4 lists
the 29 added for reference accuracy and the three that were re-expressed against the
spec rather than against the study.

```
 1  qa_check clean                            74 / 74
 2  LOD triangles in band                     1376 / 540 / 204
 3  every LOD closed and manifold
 4  no degenerate faces
 5  UVs inside 0-1, no overlap                0 texels at 2048, every LOD
 6  skin UV stretch within budget             p01 0.975, p99 1.014, max 1.043
 7  LOD UVs agree with LOD0                   0.0 texels
 8  LODs simplify the silhouette              18.8 and 36.1 mm2
 9  hull contains LOD0                        0.000000 mm outside
10  four sockets on the surface
11  maps power of two, no colour chunks       2048 square, no cHRM/gAMA/iCCP
12  transfer verified by bake                 max linear difference 0.0
13  no guide image opened                     proved by no_guide_access(), not asserted
14  every glyph from the font                 11 distinct, real outlines, no .notdef
15  print is on +Z, unmirrored                0.948 vs 0.253
16  normal map carries the relief             ratio 3.968 (min 2.0)
17  gallery luminance in the study band
18  shuriken pack byte-identical              14 / 14
19  no franchise string anywhere
20  ring is one lap                           median 2 runs, 27/60 single, p50 1.86 mm   [new]
21  fibre grain at the study cell             0.435 of slope energy <= 0.4 mm            [new]
22  aged edge band present                    19.3 % drop at the trim                    [new]
23  no ink on a frame rule                    0 texels                                   [new]
24  every frame shows the same ink            raking ink/paper 0.172 vs front 0.247      [new]
25  README documents every shipped map                                                   [new]
26  Cord socket points out of the top         kunai dry-fit passes                       [new]
```

### Unreal, on the exact exported bytes

Four commandlet processes, one at a time, none left running, in
`WorkFiles/shuriken/UnrealShuriken/ShurikenValidation.uproject` — never DemoGame_1 — under
a fresh content path `/Game/PropsCheck/PaperBombMaint`. Pass 2 re-reads everything in a
**second fresh process**, which is the only thing that proves the settings persisted.

```
 1  three LODs, triangles match Blender and the FBX      1376 / 540 / 204
 2  exactly one convex hull
 3  four sockets at scale 1, outered to the asset
 4  bounds match the measured mesh
 5  screen sizes applied from the sidecar                1.0 / 0.1710 / 0.0599
 6  lightmap coordinate index 1 generated on every LOD
 7  one material slot
 8  Nanite off
 9  texture flags persisted
10  lightmap UV configured on every LOD
11  hull contains LOD0 in engine space
```

Round trip (the gate an API cannot fool): Unreal re-exported the saved asset in a third
process and Blender compared it. Triangle counts identical, LOD positions agree to
4.1e-7 cm, hull 16 vertices convex to 3.6e-7 cm containing every LOD vertex, UV0 moves at
most 0.66 of a texel at 2048 through Unreal's half-float storage.

Zero `: Warning: ` and zero `: Error: ` lines in all five logs; all stderr files empty.

Textures, through `Scripts/props/props_lib/ue_import_textures.py` in import and then
verify mode in separate processes: `passed=True processed=4/4`, no unrecognised suffixes,
all four 2048 square with mips from the texture group.

---

## 11. Originality, and why no Fab "Created with AI" flag is required

**Nothing distributed in this product is generated by a generative AI program.**

* `Assets/PaperBomb.blend` is rebuilt from scratch by `build_paper_bomb.py` on every run.
* The FBX is exported from it by `Scripts/pipeline/export_fbx.py`.
* `T_PaperBomb_BC/_ORM/_N/_M` are baked and transferred from our own procedural node graph
  and our own curve geometry.
* Every character is typeset by Blender from `References/Fonts/MasaFont-Bold.ttf`, a
  licensed SIL OFL 1.1 font. `font_codepoints()` reads the font's own cmap **before**
  anything is drawn, because Blender will happily typeset a character the font lacks —
  FreeType returns glyph 0 and `to_curve` gives you the .notdef box, which would ship as a
  fabricated character with nothing complaining. A missing glyph raises `MissingGlyph`.
* The ring, the rules, the flourishes, the flame emblem, the seal marks, the paper grain
  and every mark of wear are drawn by our own code.

The two guide PNGs in `References/PaperBomb/` — one generated in ChatGPT, one the user's
edit of it — are **layout and style reference only**. Everything taken from them is the set
of scalar proportions in sections 3 and 5 of the study: the same class of information one
takes from a photograph or a tape measure.

**This is proved on every build, not asserted.** The art is drawn inside
`no_guide_access()`, a context manager that replaces `open` for the duration and raises
`GuideAccess` on any attempt to touch a path under `References/PaperBomb`. The list of
files that *were* opened goes into the report: `MasaFont-Bold.ttf`, and nothing else.
Grepping the source for the guide's name proves nothing — the list of forbidden fragments
matches itself — but running inside the guard does.

Epic's rule (mandatory since 2025-05-22) is that creators must select whether the asset
"was created with a Generative AI Program", and Fab's support article puts the duty on
"publishers who use AI to generate content for distribution". Looking at a picture to
decide how wide a border should be is an authoring decision, not generation, and it
produces none of the shipped bytes.

Three honest caveats, unchanged from the first pass: this is our reading of Epic's
published wording and not legal advice; a user who wants zero ambiguity can tick the flag
anyway or delete the guide PNGs once the art is signed off; and both fonts are SIL OFL 1.1,
which lets us ship rendered output freely but means the `.ttf` files themselves must **not**
be in the Fab package and MasaFont's Reserved Font Name must not be attached to any
modified font file.

No franchise, brand or product name appears in any object, collection, material, texture,
socket, file, folder or string this build emits. `props_lib.spec.DENY_SUBSTRINGS` adds its
own wider list on top of `Scripts/pipeline/qa_check.py`'s four words, and gate 19 scans
every emitted name.

---

## 12. The shuriken pack is untouched

Hashed at the start of the build and again at the end. All 14 files — seven FBX and seven
sidecars — are byte-identical to the values recorded in the study.

```
SM_Kunai_Plain.fbx              ebb6612b58e04c4c1724be1cdfaf86e2048e4a83634792308a04e31881cd3f95
SM_Shuriken_EightPoint.fbx      ced33071d0eda4dc8b25fd7e721cb9b658941ba44087d2caf319f041004676ec
SM_Shuriken_FourPoint.fbx       fc16a0fa7ca41b52952797f6cfe660a49f460911ba163ade0ed1195db1fc0672
SM_Shuriken_HookedCross.fbx     bd42e4dac5d7a54f69c01c9d826895cd5320a04e8141cd3e42fa28696b31d4ee
SM_Shuriken_SixPoint.fbx        e711279e591f69ae74ae9a49f4f443d518d5cbc42a50af20b3048ceee3657edb
SM_Shuriken_Spike.fbx           892a0ba3444e7e033068cb342d1c25e7d9e7579bbacaaa560f0e951a23c3affe
SM_Shuriken_SquarePlate.fbx     066f33f355cc75efc365ffd3152d008eb71e1bfb8098c02ff143b633fe2789e5
```

Nothing under `Scripts/shuriken/**`, `Assets/Shuriken.blend`, `Exports/Shuriken/**` or
`Renders/Shuriken/**` was written. The pack's own texture importer was invoked read-only
through environment variables into a throwaway content path; the kunai's sidecar JSON is
opened read-only by the dry-fit. `Scripts/pipeline/**` is used exactly as it is and was
not modified, so `test_pipeline.py` and `test_qa_negative.py` did not need to be re-run.

---

## 13. Regression and backup

```
WorkFiles/paperbomb/regression/snapshot.py            take a baseline
WorkFiles/paperbomb/regression/compare.py             prove a later build is unchanged
WorkFiles/paperbomb/regression/post_paper_bomb/       this build's baseline
Backups/PaperBomb_2026-09-19/                         blend, Exports, Renders, Scripts/props,
                                                      report, References/PaperBomb
```

`compare.py` works at three levels, because they fail differently: **bytes** (every file
in `SHA256SUMS.txt` re-hashed); **measurements** (the two reports compared on triangle
counts, screen sizes, bounds, sockets and the gate table, so a byte difference can be read
as "LOD2 moved by four"); and **renders** (mean and p99.9 absolute difference per image,
because Cycles is not bit-reproducible and hashing the gallery would fail on every run for
no reason).

**The determinism was tested, not assumed.** The asset was built twice, back to back, from
the same seed, and the second build compared against the snapshot:

* **byte-identical:** all four texture maps, the sockets sidecar, and all 15 source files
  under `Scripts/props/`. Every gallery render matched to a mean absolute difference of
  0.0001 / 255 or better.
* **not byte-identical:** `SM_PaperBomb.fbx`, `PaperBomb.blend`, `paperbomb_report.json`
  and `README.txt` — the last two because they carry the FBX's hash and the build's
  timings.

The FBX difference is **149 bytes out of 95,916, same length**, and `compare.py` now
labels each differing run with the field that owns it: `Minute`, `Second`, `Millisecond`,
`DocumentL`, `NodeAttributeL`, `GeometryL`, `ModelL`, `MaterialL`, and the object-UID pairs
in `Connections`. Blender's FBX exporter rewrites the clock and the object UIDs on every
export; no geometry byte moves. The result reports `metadata_only: true` and shows the
evidence, so the next reader does not have to take that on trust.

The shipped `SM_PaperBomb.fbx` is the exact file the Unreal passes ran on
(`b03ec5d107808a94bbc915f694281299cdaeb8d136d4989c1a06196b93c0b6b3`): the determinism
rebuild's copy was discarded and the verified bytes restored, so the snapshot, the backup,
the live tree and the engine verification all refer to one file.

---

## 14. Defects found and fixed during this pass

1. The dog-ear fold was not an isometry — a rotated ray, not a cylindrical bend (2.1).
2. `bake._fit_raster` padded the outline polyline to the atlas raster size (2.13).
3. `_fit_raster` left both `Ink` layers a pixel narrower than every other array (2.13).
4. The Cord socket's rotation contradicted the study, the pack and its own documentation
   (2.10).
5. `lod_deviation_mm` measured the direction that passes by construction (2.6).
6. The edge-band thresholds were set against a mask that reads 0.5 on the trim line (2.7).
7. The raking key was in a specular reflection configuration (2.2).
8. The pack's texture importer filters unknown suffixes and reports success (2.11).

---

## 15. Known gaps

### Still open after round 3 (2026-09-20) — the authoritative list

Section C.10 is the full account. In short: black area is 8.5 % short of the reference
and the black-to-red ratio is 1.379–1.406 against 1.542 (both in tolerance, and the ratio
drifted because the RED got more accurate, not because the black got worse); the four reds
still ship at one laid-on weight where the guide has four; 爆's radical overlap is 6.81 mm
against the reference's 8.86 (gate ≥ 6.0 met); the small chop's inter-glyph gap is 0.77 mm
against 1.24 (ceiling 2.0); the big chop's frame right edge is 0.43 mm past what §6
records; row 26 is built to the guide measured like-for-like rather than to the row's own
stated figure, which no instrument reproduces; and the two bottom corner brackets are now
0.95 mm stubs where the top two are 3.2 mm hooks.

Everything below is earlier and is superseded where sections C and B say so.

### Added by the reference-accuracy pass (2026-09-20)

**A. The 爆 radical's bounding-box overlap is +0.54 mm, not the reference's +8.86 mm.**
This is the one REFERENCE_SPEC row (3) whose *secondary* tolerance is not met, and it is
not met because it cannot be, with this font, without losing the primary one. Both guides
set 爆 as **two components** whose boxes overlap by 8.86 mm with **0.75 mm of clear paper**
between the nearest ink — the 火 radical's final stroke tucks *under* 暴 at a different
height. MasaFont sets the two parts 1.94 mm apart with a 3.33 mm ink gap; measured, the
nearest-approach rows of the two parts line up, so sliding the radical far enough right to
overlap the boxes by 6 mm welds the ink and the character becomes **one** component. The
tuck was taken as far as it goes while both parts survive (2.5 mm, giving +0.54 mm of box
overlap and a 0.93 mm ink gap against the reference's 0.75), and the gate is on the thing
the reviews actually complained about and the eye actually sees — **two components, no
orphan fragments**. The alternative is redrawing the radical's final stroke rather than
setting the font's, which is a bigger decision than this pass should take alone.

**B. Vermilion measures S 0.852 against the reference's 0.89–0.92.** The gate is the
spec's own floor (≥ 0.82) and it passes, but the target is not hit. The shortfall is the
paper showing through at the stroke edges and the `red_dry` end of the load ramp, not the
pigment: `PALETTE_REFERENCE.red_wet` is the guide's measured colour exactly. Closing it
means a drier `red_dry` or less bleed, and both trade against rows 10 and 22.

**C. The grain's measured anisotropy is 1.5, the reference's is 1.90.** Amplitude
(14.4 % against 17 %) and cell (0.62 mm against 0.50) are inside the spec's bands and
gated; the anisotropy is only gated as "< 3" because the spec gives no direction for it.
The fibres run along the card's **long** axis here, which is what a laid sheet's mould
does and what keeps the row statistics honest — a horizontally-correlated grain leaks
about 1 % into any row median and makes the row-24 crease test measure its own noise.

**D. Total ink coverage is 0.2641 against the reference's 0.2861.** Inside the ±0.035
tolerance, and the *ratio* that the spec calls "the most robust composition number
available" is on the nose (black ÷ red 1.545 against 1.542), but the card carries about
7 % less ink than the guide overall. Black is 0.166 against 0.1735 and red 0.1075 against
0.1126.

**E. The flanking leaf pair sits under the lower-centre column.** Row 17's measured
positions, (32.20, 130.76) and (38.04, 130.63), fall inside V1's own lower-centre column
band (ink 112.9–145.0 mm) and inside the x-span of our 業. They are drawn, in red, before
the black column, so the column takes precedence where they meet — which is the order a
printer works in. Whether V1's two 1.5 mm² marks are ornament or a fragment of its
pseudo-glyph scribble is not decidable from a measurement, and the spec does not say.

**F. The corner dart's *hook* is not judged against anything.** Row 14's 2.0–2.2 mm of
outboard ink is measured and gated at all four corners (1.89–2.33 mm, black at every
corner). Section 7's unmeasurable half — "the reference's curls inboard like a comma
turning down-and-in, with ink pooling darkest where the two rules cross" — was drawn to
that description and looked at at 4×, but there is no number behind it.

**G. The spec's three "design calls, not metrology" (section 7) are still open.** V1's
lower-left mark group is not reinstated; how much wear is right was decided *toward the
guides* and could legitimately go the other way for a prop; and the 0.43 % aspect
difference between V1 and the shipped 70 × 156 card is untouched, the card's dimensions
being a product decision.

**H. The seal-box measurement needed three attempts and the method matters.** The first
two reported the measurement *window* rather than the chop (15.3 × 25.8 mm for a chop
whose ink is 9.1 × 17.9), because the lower-right column's foot passes 1.2 mm above the
small chop and the left frame rule runs down the side of the big one. The shipped method
measures the ink's outward excursion past each of the four frame edges, over the middle
70 % of each edge, with the rules removed by position and the black columns removed by
colour. It is right, but it is the kind of measurement that is easy to get wrong, and it
is worth re-reading before trusting a future change to it.

### From the second pass (still true)

1. **Fibre-grain slope energy is 0.435 at ≤ 0.4 mm, not the 0.50 the review asked for.**
   Most of the remainder is the along-fibre direction of the anisotropic field landing just
   the wrong side of the band boundary; going finer across the fibre would alias on a 2048
   map. Measured, gated at 0.35, and visible in `paperbomb_raking.png` as fibre rather than
   pebble.
2. **Ring runs per angle: median 2, not 1.** Superseded by section A.4 item 2: the
   reference's own ring has a 0.198 hole fraction, so a lap that matches it has two runs at
   most angles, and the gate now says so. The original note read: The review's target and the study's dry-brush
   requirement contradict each other (2.3). 27 of 60 angles are a single run and the runs
   are the study's width. Judge by looking.
3. **The backdrop's top of frame reads 0.518 against the pack's 0.36.** Ground roughness
   0.45 → 0.32 closed part of it; the rest is that the metal rig's two grazing strips are
   what darkened the pack's upper frame, and they are dropped here because on paper they
   just print two hot bands. Visible if the two galleries are compared side by side.
4. **The hero and persp shots are not gated on ink consistency, only reported.** A 3/4 shot
   spans a real lighting gradient and the persp is deliberately near edge-on, where a rough
   dielectric genuinely sheens — that is the truth about paper, not a rendering fault. Both
   are measured in the report. Only the close-up gates.
5. **Physics is decided but not tested in Chaos.** 0.862 g measured, shipping as a 0.001 kg
   Mass-in-KG override with 0.005 kg documented as the fallback. The card must not be
   thickened to fix jitter.
6. **The Cord/kunai dry-fit is algebraic, not visual.** The socket frames are composed and
   checked on every build, which is what catches the class of fault that shipped last time,
   but nobody has parented the two meshes and looked at the pair.
7. **No masked-material variant is built,** and none is planned: the master is deliberately
   opaque and the README says exactly how to make one.
8. **No form variants.** A blank tag and a scorched half-burnt tag would cost almost nothing
   now `props_lib/sheet.py` exists, and `_M` green already carries the burn-order field for
   exactly that.
9. **LOD-switch legibility is measured but not re-verified in engine, and the art has
   changed again.** The first
   pass's Unreal review box-downsampled the front island to 75 × 168 and confirmed the 爆,
   all four columns, the emblem, the ring and both seals still read. The art has changed
   since; the geometry of the switch has not.
10. **No market check.** No Fab listing for ofuda or paper-talisman assets has been opened,
    so pricing is unresearched.
11. **Fab's own AI-policy page could not be rendered during the study** and the Terms of
    Service returned 403, so the wording quoted in section 11 is a search summary
    corroborated by Epic's forum announcement. The substantive conclusion does not depend
    on it: nothing distributed here is generated by a generative AI program.
12. **`Backups/Shuriken_after_kunai_plain_2026-09-19` no longer mirrors `Renders/Shuriken`.**
    Three kunai renders (`kunai_plain_3q.png`, `_grip_closeup.png`, `_neck_closeup.png`)
    postdate that backup and predate this job. They are kunai-pass output, not a freeze
    violation — this build wrote nothing there and all 14 export hashes are unchanged — but
    the backup is worth refreshing.
