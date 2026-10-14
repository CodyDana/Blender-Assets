# HP01 (Heavy Pistol HP-01): reference measurement and tracing

This is the 2D outline authority for `SK_HP01`, `SM_HP01` and `SM_HP01_Mag`.

**Source:** `References/Guns/Pistol/pistol_sheetA.webp`. The sheet is 1254 x 1254 px, AI-generated, with four labelled
panels: LEFT, RIGHT, TOP and 3/4 FRONT LEFT. Every number below comes back in about 10 s from:

    py -3 -B WorkFiles/guns/pistol/tools/trace_reference.py   # tracer + stage2.py (reads, profiles, outlines, overlay)
    py -3 -B WorkFiles/guns/pistol/tools/make_spec.py         # spec + interface + S0
    py -3 -B WorkFiles/guns/pistol/tools/design_sheet.py      # HP01_DESIGN_SHEET.png

The tools use numpy, scipy and Pillow only, and find their paths from their own location:
- `tools/refimg.py` is copied unchanged from the carbine.
- `tools/gridzoom.py` (also from the carbine) made the gridded zooms that the hand reads came from (`scratch/g_*.png`).

I ran the chain twice and got the same numbers both times.

| Output | What |
|---|---|
| `hp01_measured.json` | Everything measured: panels, ruler, scale ruling, mirror test, self-consistency, key dimensions, serrations, rail, TOP width profile, the features in frame F, and the raw reads in px |
| `traces/LEFT_outline.json` | LEFT silhouette (px and mm, frame F), plus the holes (trigger-guard opening, hammer gap) |
| `traces/RIGHT_outline.json` | RIGHT silhouette, mirrored and aligned onto LEFT |
| `traces/TOP_outline.json` | TOP silhouette (px; mm in X and Y, where +Y = gun left) |
| `traces/*_silhouette.png`, `HP01_TRACE_OVERLAY.png` | Masks and the QA overlay (local only: `WorkFiles/**/*.png` is ignored by git) |

**Frame F (mm):**
- +X = muzzle, +Z = up.
- X = 0 at the front of the crown.
- Z = 0 on the bore axis, which is the centre of the crown boss in the side view (sheet y 212).

The build frame B (origin = `Grip`) is derived from F in `make_spec.py`.

## Panels and sides

The panel finder found the four panels at (0, 23, 624, 616), (630, 23, 1253, 616), (0, 643, 624, 1253) and
(630, 643, 1253, 1253).

**RIGHT is a mirrored redraw of LEFT.** It carries no handed feature at all:
- The silhouette IoU of RIGHT, flipped, against LEFT is **0.9952**, with a 0.02 px shift.
- The interior luma correlates at 0.93 and differs by a median of 9 levels: the surface texture was re-rendered, the
  design was not.
- Neither side shows an ejection port or a magazine-release button.
- Both sides show the same slide stop, the same flank tab and the same guard pin.
- TOP agrees: the levers and tabs stand out symmetrically on both sides.

So the panel labels cannot be checked against handed features, which is the usual way (study 4.2). They are taken as
labelled, for two reasons:
1. A LEFT view of a gun has the muzzle to the image left, and so does this one.
2. The 3/4 FRONT LEFT view shows the side with the slide stop, which must be the left by its camera geometry (the
   muzzle comes toward the camera on the image left).

The handed parts of the real pattern are the ejection window (right), the magazine release (left) and the slide stop
(left only). The study's rulings R2, R5, R7 and R8 handle them.

## Scale

| Item | Value |
|---|---|
| Rule | Real overall length of the class: **273 mm** (study 3.5, [E49]). The rulers are reported only |
| Sheet length (LEFT, sub-pixel contour) | 575.95 px, so **2.1097 px/mm** (1 sheet px = 0.47 mm) |
| Ruler (major ticks every 5 cm) | 1.9275 px/mm, which makes the gun 298.8 mm: the **ruler is +9.5 %** (study: +9 %). Its minor ticks are 6 per 5 cm: an AI ruler |
| TOP length | 570 px, against 576 on LEFT (-1.0 %). TOP is used at the side-view scale |
| Height (rear-sight top to mag base) | **170.6 mm**, against ~159 mm for the class [K]. The sheet is **+7 % taller** in proportion (H/L 0.625 against 0.582) |
| Width (TOP) | slide **46.9 mm**, 55.0 mm at the levers; the class is ~32 mm [K]. The sheet is **~45 % wider**. See the next section |

## Width: the TOP view against the 3/4 view

The 3/4 view gives an independent check, using its crown ellipse:
- The ellipse is 36 x 60 px, so the face plane is seen at cos theta = 0.60.
- Corrected by that, the front plate's width-to-height ratio is **0.73**.
- TOP and side together give **0.88** for the same plate.
- The camera's pitch would push the 3/4 figure lower still.

So the 3/4 draws the gun about 17 % narrower than TOP does. That is a disagreement in proportion, not in design: no
part differs. HP01_STUDY Q1 holds the width decision. The default is the TOP view as drawn, and one parameter, `K_Y`,
gives the alternatives.

## Key dimensions (frame F, mm; 1 sheet px = 0.47 mm, reads +-1 px)

| Dimension | Value | How |
|---|---|---|
| Overall | 273.0 | scale rule |
| Crown boss proud of the front plate | 7.8 (X -7.8..0); diameter 19.0 | read |
| Front plate | X -7.8..-3.0, Z -18.0..+17.1 | read |
| Slide length (front plate to rear face at the seam) | 250.7 | read |
| Slide height at mid-length (rib top to the slide/frame seam) | 40.3 (53.6 including the lower band) | read |
| Top line | **rises 2.2 deg toward the rear** (Z +19.4 at X -25, +24.2 at X -150) | read, 3 points |
| Front sight | X -26.8..-9.2, top Z +31.8 | read |
| Rail recess | X -217.3..-153.3. Caps Z +26.1, floor Z +19.9 | read |
| Rail crossbars | **6** in the side views (centres X -158.8 ... -212.1), at a pitch of **10.66 +-0.5**: the 1913 10.01 within the reading error. **TOP draws 5** | read, 6 bars |
| Rear sight | X -241.5..-226.8, ears top Z +34.1 | read |
| Sight radius / sight line | 217.6 / 32.7 above the bore | derived |
| Serrations | **7 grooves**, pitch 4.27 along X, **4.09 normal**, leaning **16.6 deg top-forward**. Field X -204.5..-242.9, Z -17.1..+14.7 | measured on 4 rows |
| Upper facet run-out (end of the barrel hood's flank) | diagonal from (-177.5, +7.1) to (-203.6, +12.8) | read |
| Slide/frame seam | Z -18.0. The frame starts at X -112.1 (front of the dust-cover block) | read |
| Trigger-guard opening | 43.1 x 32.7. Guard pin at (-123.5, -33.7), dia 3.8 | read |
| Trigger pivot (read) | (-167.1, -32.7). Trigger reach to the backstrap: **79.6** | read / measured |
| Grip axis | **17.4 deg** from vertical (front strap 17.8, backstrap groove 17.0) | read |
| Slide stop | X -216.8..-249.5, Z -19.0..-28.4 | read |
| Flank tab (on the slide) | X -165.6..-192.7, Z -4.7..-14.7; 3.8 proud (TOP) | read |
| Beavertail tip | (-271.8, -27.5) | read |
| Mag base plate | 63.0 long, 4.7 tall, bottom Z -136.5 | read |
| Grip origin (B frame) | F (-215.9, -78.5): the tang web line, then 46 mm down the 17.4 deg axis (standard depth, provisional for pistols) | derived |

## Method notes

- **Silhouettes.** The steel flats of the slide top match the backdrop's luma (about 120-135 against 120). So the soft
  field alone misses them; it caught the slide top only down to the facet line.

  The silhouette is therefore the union of two masks: the soft field, and a luma-gradient envelope (Sobel > 6,
  closed, filled, eroded back one pixel). Enclosed backdrop regions are opened again afterwards: these are the guard
  opening and the hammer gap.

  The outline hugs the edges everywhere I looked: front sight, rail caps, hammer spur, beavertail, guard, mag plate.
  The shadow under the mag base adds about 2 px at the bottom, so height comes from the reads, not from the mask.
- **TOP edges** are the outer luma-gradient hits per column (+-1 px). The plain soft field failed on TOP: its contour
  ran along the facet lines.
- **Read error.** The first rear reads used zoom pixels where they should have used grid labels. I caught it on the
  overlay, re-zoomed (`g_rear2.png`, `g_grip2.png`), re-read the values and re-ran the chain.

## What the sheet does not show (each is ruled in HP01_STUDY)

- No ejection port.
- No magazine-release button.
- No pins except the guard pin. At 2.1 px/mm a 3-4 mm pin would be 6-8 px across, so their absence is real evidence.
- No grip screw.
- No markings at all.
- No rifling or thread at the crown.
- The safety block is too dark to show any detail.
