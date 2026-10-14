# SR01 (Sniper Rifle SR-01): reference measurement and tracing notes

The 2D outline authority for the SR01 build (`SK_SR01`, `SM_SR01`, `SM_SR01_Mag`, attachment
`SM_Att_Scope_LongRange`). Source: `References/Guns/Sniper/sniper_sheetA.webp` (1254 x 1254, AI-generated, Sheet A
only, no ruler). Everything below is regenerated in about 10 s by:

    py -3 -B WorkFiles/guns/sniper/tools/trace_reference.py

The tool is new for the sniper (the SMG tracer's config is SMG-specific). It uses the same helpers
(`tools/refimg.py`, copied unchanged from the SMG) and numpy/scipy/Pillow only, and takes its paths from its own
location. `tools/gridzoom.py` (copied) makes the gridded zooms the hand-read seams come from (`scratch/zoom/`, local only).

| Output | What |
|---|---|
| `sr01_measured.json` | All numbers: px/mm per view, panel boxes, axis fits, view agreement, scale anchors, dimensions |
| `trace/GR_outline.json` | Gun right side (sheet "LEFT"): silhouette, sub-outlines (scope, folded bipod, magazine, gun body), 20 labelled parts, face features; px and mm |
| `trace/GL_outline.json` | Gun left side (sheet "RIGHT", mirrored): silhouette and the same sub-outlines; px and mm in its own frame |
| `trace/TOP_outline.json` | TOP silhouette (px, mm with Y = gun left) and the width profile at every column |
| `trace/Q34_outline.json` | 3/4 silhouette in px, for the camera-solved gate at form |
| `trace/*.png` | Masks and the GR part index image (local only; `WorkFiles/**/*.png` is ignored by git) |
| `SR01_TRACE_OVERLAY.png` | QA overlay: GR parts tinted and labelled; GL with GR's silhouette (no fit); TOP; 3/4 |

## Sides (handed features): the labels are swapped

| Evidence | Panel labelled LEFT | Panel labelled RIGHT | TOP | 3/4 FRONT RIGHT |
|---|---|---|---|---|
| Bolt handle + round knob (right-handed bolt action: right side) | yes, knob centre X 367.9, Z -33.6 | none | knob protrudes image-down with the muzzle image-right = the gun's right | yes |
| Muzzle direction | image-right | image-left | image-right | front right |

A right-side view of a gun has its muzzle to the viewer's right. So **the panel labelled LEFT is the gun's RIGHT
side (called GR in the tools) and the panel labelled RIGHT is the gun's LEFT side (GL)**, as the study warned. The
3/4 view is from the front right, consistent with GR. GL is mirrored before tracing so both side views have the
muzzle image-right.

## Frame

- **mm (frame M):** +X toward the muzzle, +Z up, +Y = the gun's left (line standard, study 5.1). **X = 0 at the
  rearmost point of the butt pad, Z = 0 on the bore axis, Y = 0 on the mid-plane.**
- **Bore axis direction:** the barrel's straight top edge (x 470-575, rms 0.13 px) and the scope tube's centre line
  (rms 0.05 px) are both horizontal; tilt -0.06 deg (GR), -0.16 deg (GL). The barrel tapers on its lower edge only
  (35 -> 32 mm), so the barrel centre line is not used for direction.
- **Bore height:** the muzzle-device centre line (GR y 238.13, GL 238.12 px). The barrel centre at the device agrees
  within 0.12 mm.
- Each view has its own frame (own X = 0, own scale to 1100 mm). Views are compared in mm without fitting.
- The build origin `Grip` (study 5.1) is computed in the spec: M (297.13, 0, -96.13), 46 mm down the traced grip axis
  (27.15 deg from vertical) from the web line Z -55.2. Provisional until H1.

## Method

1. **Panels** by pixel analysis: LEFT (4,4)-(622,566), RIGHT (630,4)-(1249,566), TOP (4,595)-(622,1205),
   3/4 (630,595)-(1249,1205).
2. **Backdrop:** robust degree-4 polynomial fit; residual sd 2.15 / 2.32 / 1.57 / 2.63 grey levels.
3. **Side silhouettes:** soft field (40 levels darker, chroma 24, or 24 brighter), every component kept (the bipod
   is drawn detached from the forend), the studio floor line (components starting below y 318) dropped, holes
   filled except backdrop-coloured ones (the trigger-guard opening, the gaps under the riser plate and between the
   scope and the rail: 3 per side). The olive paint is low-chroma (sat 0.12) and close to the backdrop in highlights,
   so hole filling matters.
4. **TOP:** the backdrop above the gun is clean, but a soft floor shadow lies on the gun's right (image-down). The
   upper edge is the soft-field crossing; the lower edge is the last >= 20-level step scanning up from the bottom
   (the shadow ramp changes <= 3 levels per px).
5. **3/4:** a stricter threshold (62 levels) for the neutral floor shadow; px only (perspective).
6. **Sub-outlines and parts (GR):** the scope (above the rail top, y 222.2), the folded bipod (below the forend band)
   and the magazine (below the mag-well edge, y 274.7) are split first. The gun body is split into parts by hand
   boxes read off 6-8x zooms (+-1 px): muzzle device, barrel, rail, bolt handle, bolt shroud, receiver, cheek riser,
   butt pad, pad plate, trigger, mag release, trigger guard, grip, butt, chassis forend, chassis centre. 0 px
   unassigned.
7. **Measurements** on sub-pixel edges (column/row crossings of the soft field), never on pixel masks.

QA: I looked at the overlay and the 4-8x zooms of every zone. The trace hugs the edges everywhere, including the
riser plate, the rail teeth, the bipod hub and feet, the guard opening, the flutes and the compensator's chamfer.

## Scale

**Chosen: 1100 mm overall** (butt-pad rear to the compensator face). GR 0.53173 px/mm (1.881 mm/px), GL 0.53092,
TOP 0.53364.

There is no ruler. The study's table gives 1270 mm, an AWM-class (.300 WM / .338 LM) figure; the brief for this run
asks for a .308-class chassis rifle. The sheet's own anchors decide inside that class:

| Anchor | Sheet at 1100 | Real class | Overall that would match |
|---|---|---|---|
| **Scope main tube** (18.1 px on both sides, rms 0.05) | 34.1 | 34 mm tube | **1097** |
| Eyepiece | 45.1 | 42-46 | 1024-1122 |
| Objective bell (side) | 62.1 | 62-68 (56 mm objective) | 1098-1205 |
| Rail slot pitch (drawn, 8 dips) | 10.61 | 10.01 | 1038 |
| Length of pull (pad rear to trigger face) | 363.2 | 330-370 | 999-1121 |
| Bolt knob | 24.8 | 20-25 | 887-1109 |
| Magazine fore-aft | 89.3 | 80-88 | 985-1084 |
| Compensator OD | 36.1 | 30-36 | 914-1097 |

Median 1049, spread 998-1151. The tube is the sharpest anchor (a 30 mm tube would mean 970 mm, a 36 mm tube 1165).
At 1270 mm the tube would be 39 mm (no such class) and the barrel 37-41 mm thick. 1100 is inside the .308 chassis
range (1050-1200) and the barrel then measures out at exactly 22 in (spec R3). `unc` values in the JSON are
measurement uncertainty only; the scale choice is on top.

## How well the views agree

| Check | Result |
|---|---|
| Overall length in px | GR 584.9, GL 584.0 (0.9985), TOP 587.0 (1.0036) |
| GR vs mirrored GL, frame-aligned (no fitting) | silhouette IoU **0.968**; gun body 0.969, scope 0.989, folded bipod 0.918, magazine 0.935; boundary distance median 0.0, p90 2.2, p99 16.9 mm (the p99 is the riser/bolt-shroud detail and the bipod hub) |
| Diameters, side vs TOP | compensator 36.1 vs 38.1; barrel at the device 31.8 vs 35.2: TOP inflates round parts 6-10 % |
| TOP left vs right edges | the right (image-down) edges sit 4-6 mm wider than the left (soft floor shadow): symmetric widths are taken as 2 x the left half-width |
| TOP knob | drawn ~32 mm further back than GR (X ~336 vs 367.9) |
| Perspective | none measurable in the side views (barrel and tube lines rms <= 0.13 px; equal lengths to 0.15 %) |
| **3/4 bipod** | **folded**: the legs run forward under the barrel, nearly parallel to it, feet side by side about 60 % of the way to the muzzle. The study's note "deployed in the 3/4" is wrong; no view shows the deployed pose |

## Authority per dimension

| Dimension | Authority | Why |
|---|---|---|
| X lengths, Z heights, profiles, grip and mag angles, the folded bipod | **GR** (GL agrees to IoU 0.968; tie-breaker GR) | all parts traced; handed side |
| Gun-left features (riser clamp lever, butt QD-cup recess, its own fastener heads) | **GL** | only view |
| Widths (Y) | **TOP**, left half x 2, +-8 % | only view; shadow bias on the right edges |
| Knob outboard reach | **TOP** (right edge less 5 mm bias) | only view; its X comes from GR |
| Diameters (barrel, compensator, scope) | **GR + GL** | TOP inflates rounds |
| Magazine thickness, mag ribs, compensator exit, scope objective face | **3/4** | only view; +-20 % |
| Folded bipod pose | **GR + GL**, checked again on the 3/4 (camera-solved at form) | user rule |
| Deployed bipod pose | **real pattern** | not drawn anywhere |
| Small-part construction | **real pattern** (user rule) | the sheet resolves ~1.9 mm/px |

## Dimensions (mm at 1100; GR unless noted)

| Part | Value |
|---|---|
| Overall | 1100.0 (definition). Height with scope 265.2 (scope top Z 99.0 to grip bottom -166.4); without scope 197.5 (riser top +32.0 to grip bottom) |
| Bore, scope, rail | bore Z 0; scope axis **Z 57.6**; rail top Z 30.0 (ring centre height 27.6: medium 34 mm rings) |
| Scope | X 271.1-690.5 (419.4 long); tube 34.1, eyepiece 45.1, bell 62.1 (side); elevation turret top Z 99.4 (X 446-478); rings X 401.8-425.3 and 507.1-528.7; TOP: side-focus knob reaches Y +50.4 (left), windage ~-35 (right, bias corrected) |
| Rail (scope base) | X 385.8-546.6, top Z 30.0; drawn tooth pitch 5.64 px = 10.61 mm (8 dips on row y 222) |
| Receiver | X 382-567 (under the rail, top Z 19-20), port X 422.5-507.1, Z 4.9-14.3 (drawn) |
| Bolt shroud | rear X 345.4, dia ~24 |
| Bolt knob | centre (367.9, -33.6), dia 24.8; TOP outboard edge Y -85.0 (raw) |
| Chassis | top Z -13.8 behind the action; forend top Z 15.9, bottom band Z -40.2..-25.1 (X 582-831), front X 836.8; three side slots X 662-698, 715-752, 768-811 at Z -12.9..-3.5; width at the mag 65 (TOP left x 2), forend 74 |
| Butt | joint to the chassis X ~244 (no hinge drawn), top Z -16.7, heel step, two clamp knobs (99.0 / 129.1, -67.5) dia 15 |
| Butt pad | X 0-52.9 (incl. its spacer plate to 68.9), Z -153.7..16.4 (170 tall), width 61 |
| Cheek riser | plate X 68.9-179.9, Z -3.5..32.0 (35.5 thick), posts exposed Z -16.7..-3.5 (13.2), width 69 |
| Grip | rear strap 30.7 deg, front strap 24.9 deg from vertical (fit rms 0.81 / 0.30 px); fore-aft 54.3 at mid height; bottom Z -166.4 |
| Trigger guard opening | X 340.7-395.2 (54.5) x Z -94.7..-62.8 (32.0) |
| Trigger | X 348.2-385.8, Z -98.5..-60.9; face X 363.2 at mid height; **length of pull 363.2** (14.3 in) |
| Mag release (drawn) | a 2.5 px lever X ~409.3-414.0, Z -71..-114, directly behind the magazine (1 px gap) |
| Magazine | X 414.1-503.3 (89.3 fore-aft), well edge Z -68.8, bottom Z -132.3 (63.5 exposed); edges -0.9 / +1.3 deg (GL rear +3.4): vertical |
| Barrel | visible X 841-1049.7: OD 35.2 at the forend, 32.9 mid, 31.8 at the device; 6 straight flutes (3 visible per side) X ~841-1036 |
| Compensator | X 1049.7-1100 (50.3), OD 36.1, rear collar step, front chamfer; front exit hole ~12 mm (3/4) |
| Bipod (folded) | hub (pivot) centre (719.6, -61.8), dia 36.9; clamp X 747.8-812.7, Z -52.4..-39.6; leg tube X 747.8-883.2 dia ~20.7; lock collar X 877.6-896.4 (28 tall); foot X 896.4-925.6, 38.5 tall; knob under the hub X 717.7-746.0, Z -85.3..-71.2; whole bipod X 684.8-929.3, Z -83.4..-38.3 |

## Not shown anywhere (build from the real pattern, keep plain)

The deployed bipod, the receiver internals and bolt face, the magazine top, the chassis underside apart from the
mag well, the inside of the forend, the scope underside, the left side of the bolt, the riser at other heights, any
hinge or latch on the butt, the trigger housing. No markings are drawn and none are built.
