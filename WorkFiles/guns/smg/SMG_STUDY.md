# Compact SMG SM-01 (SMG01): study and decisions (2026-10-09)

This merges the three study roles into one package for the SMG01 build (`SK_SMG01`, `SM_SMG01`, `SM_SMG01_Mag`):
- the measurement (`MEASUREMENT_NOTES.md`, `smg_measured.json`, `trace/`);
- the craft study (`CRAFT_STUDY.md`, `craft_parts.json`);
- the game and tech plan (`SMG_BUILD_PLAN.md`, `smg_interface.json`).

The build reads **`smg_spec.json`**. It is written by `tools/make_spec.py`, which computes every derived number from
the traced outlines. Read it together with **`SMG_DESIGN_SHEET.png`**, drawn by `tools/design_sheet.py`. Re-run both
after any change to the trace or to a decision:

    py -3 -B WorkFiles/guns/smg/tools/make_spec.py
    py -3 -B WorkFiles/guns/smg/tools/design_sheet.py

**Which role wins:**
- The measurement wins on silhouette dimensions and positions.
- The craft study wins on how small parts are built (rulings RP1-RP22), on finishes and on wear.
- The plan wins on frames, bones, sockets, slots, budgets, LODs, gates and stage order.

Where a role's number came from a misreading, this merge re-read the sheet at 4-10x zoom (crops in `scratch/merge/`,
local only) and says so. The spec lists every conflict and its resolution as R1-R25. A checker then reviewed the
merge; its 16 findings (C1-C16) were verified on the sheet and fixed in the trace tool, the spec generator, the plan
and this study (section 12; spec `check_findings`).

Nothing was built, locked, committed or run in Blender or Unreal.

## 1. Decisions on one screen

| Topic | Decision | Res. |
|---|---|---|
| Scale | 690.0 mm overall at the measured px/mm: LEFT 0.85114, RIGHT 0.85196, TOP 0.84613. The sheet's ruler is wrong (86.8 cm). | R1 |
| Panels | The labels are true. LEFT is the gun's left (knob), RIGHT is the right (port and catch). TOP has the muzzle image-left and the gun's left image-down. The 3/4 view is the left side. No panel is mirrored. | R3 |
| Frame M (all numbers) | +X toward the muzzle, +Z up, +Y = gun left. X = 0 at the butt-pad rear with the stock extended. Z = 0 is the measurer's datum; **the bore is at Z_M +1.87**. | R2 |
| Frame B (Blender) | Origin `Grip` = M (335.67, 0, -96.49), which is **46 mm** down the traced grip axis (21.87 deg) from the web line. B = M - Grip. Unreal cm = (Bx, -By, Bz) / 10. | R4 |
| Bore and muzzle | The device outer diameter is **25.5** (side) and 26.2 (TOP), so the two views agree. The measurer's 20.8 was a see-through slot sliver. The bore is the device's outer-edge centre line. | R2, R15 |
| TOP view | Usable for widths (receiver 68.8, fore-end 62.7) everywhere **except the stock (X < 245)**, which is drawn obliquely. There, the frame width is 29.5 and the pad width is 58. | R2, R18 |
| Breech / barrel | Breech at X 503: the chamber must sit ahead of the magazine's top round. Crown at X 659, inside the device collar. Hidden barrel **156 mm** (real 200, Q2). | R8 |
| Bolt and charging handle | Both travel **75 mm**. Bolt face X 503 -> 428. The knob is **dia 18.5 at (549.3, 21.0)**, re-read at 8x; the measurer's 12.9 was an under-read. The slot X 470.8-552.6 runs behind the knob and ends in a lock notch (rise 4.0). The arm rides on the wall (TOP: block 3.3 proud). The lock: the lever pivots 15 deg on a roll pin in the slide at **(Y 22.0, Z 27.0)**; the slide does not rotate; the arm swings outward. | R5, R6, C4 |
| Right upper slot | A moulded through-vent, X 530.1-595.8. It is not a mirror of the left one. | R7 |
| Port boss | The traced boss X 511.3-527.9 is the integral **stock catch**: 3 mm proud, a hooked lip on its rear edge. Folded, the barb of a moulded **lug on the stock's rear upright** sits under it (engagement 1.3 mm). | R11, C3 |
| Magwell | Flared lip on the traced lip line (10.9 deg), 1 deg draft, a **4.0 rear wall** (+0.3) parallel to the magazine, catch window, top shelf, **no guide ribs** | R12, C1 |
| Mag release | The lever is drawn **inside the guard's front leg** (re-traced). Built: a paddle 9.0 x 3.5, X 444.2-447.7, pin **(445.95, -63.6)** in a clevis of the lower; its nose reaches the notch (Z -44) through the catch window; -11 deg moves the nose 3.9 mm back. It sits 3.9 mm behind the drawn lever (declared): the wall needs the space. | C1 |
| Magazine | Straight, rake **8.27 deg** (floor forward; straight-body fit), section 46.6 x **29.0**, 242.4 long along its axis (180 exposed). Two 12.5 mm recessed ladder channels with ties at Z -143.4 / -178.7 / -214.5. Solid, no cartridge. | R13, R14, C2 |
| Top rail | 1913 profile at the 10.01 pitch, cut only where the sheet draws teeth: **21 teeth, slots 2-23**. Plus hidden lug slots 0 (rear sight, X 328.42 = `Rail_Top`) and 27 (front sight). Slot depth 3.0, not the drawn 6.0. The drawn flats stay. | R9 |
| Lower rail | 7 slots at 10.01, centred on the 76.2 mm rail (end webs 5.5; 6 drawn) | R9, C8 |
| Sights | Aperture centre **(330.0, 76.0)**, the drawn ring. The post tip is on the same line, 7.9 below the ear tops. Sight radius **268.6**, sight line **74.1** above the bore. The rear leaf is pinned at its front-lower corner (336.3, 53.6) and folds forward to Z 65.7. The rear windage drum is on the **left**, and the front clamp knob is on the right (both from TOP). | R17, C6, C9 |
| Selector | One shaft at the LEFT pivot (363.4, -28.5); hub 20.7 on both sides. Bind pose = sheet pose = SEMI. Rotation about Y: SAFE -63.4 deg, AUTO +45 deg. These detents are a **design call**, not real figures (Q16). | R10, R23, C11 |
| Trigger | Axle at the drawn head **(402.2, -40.2)**; pull **0..+13 deg** about Y (the lower end rearward, as the AR-01's 0..+12). | C5, C7 |
| Stock fold | Folds to the right, +180 deg about a vertical axle at **(272.4, -33.95)**. The knuckles stand ~5 mm proud of the right side in TOP (Q6). Folded, the mid-plane is at Y -67.9, the pad sits 1 mm outboard of the catch, and the folded length is **423.6** (real 450). The folded envelope reaches **Y -100.7** (the latch housing and button). Extended, a necked push-button bolt sits 2.0 mm into a lug on the end block's left rear, above the drawn gap. | R19, R20, R25, C10, C14 |
| Bolt catch | Not built (no bone) | R24 |
| Materials | The craft study's sheet-calibrated values (section 6). The plan's slots and masters are unchanged. | R21 |
| Contract | The plan's bones, sockets, budgets, LODs, gates and stages are kept, with the numbers filled in. The craft gates are added as F1-F5; the check adds F6 (stock latch) and F7 (handle lock). The shared ABP drives normalized inputs mapped by each gun's sidecar angle table. | R22, C5, C16 |

## 2. Scale and the sheet's proportions

690 mm is the user's figure, the real pattern's and the line rule's (study 3.5). At 690 mm the sheet is chunkier than
the real gun:

| Check | Sheet at 690 | Real |
|---|---|---|
| Trigger reach | 90.5 | ~70 |
| Height with magazine | 338.3 | 280-326 |
| Receiver width | 68.8 | 61-63.5 |
| Side rail pitch | 11.05 | 10.01 |
| Folded length | 423.6 | 450 |

These checks would match an overall length anywhere from 534 to 744 mm, so no single scale fits all of them. The
silhouette gates keep the sheet's design. H1 early reports the hand fit. If it fails, the user is offered the ~625 mm
alternative (Q1), at which the side rail pitch and the width become real.

## 3. View agreement

- **LEFT vs mirrored RIGHT, frame-aligned:** silhouette IoU 0.947 (0.950 with a free fit). Boundary distance median
  1.2 mm, p90 2.4 mm. The panels are near mirror copies, so LEFT is the tie-breaker.
- **RIGHT's own detail:** the port, the catch, the longer upper vent and the right selector lever.
- **RIGHT drift:** RIGHT draws the selector 5.5 mm further forward and the magazine's rear-top corner 8.7 mm further
  back. LEFT wins both.
- **TOP vs side:** they agree on length (0.994) and on the device diameter (within 3 %).
- **TOP offsets:** TOP draws the knob about 9 mm further back and the hinge about 15 mm further back. Its stock zone is
  oblique (the lower strut shows beside the top strut, and the pad's side adds width). The TOP L2 gate is computed on
  X >= 245 only, and the stock is checked by its two widths.
- **3/4 view:** the only source for the magazine thickness (30.7 +- 5.7), the magwell width (48.9 +- 7.3) and the
  front face (sling eyelet at the upper left). It gets the camera-solved L2 gate.
- **Design-sheet QA:** spec drawing vs traced LEFT silhouette, IoU 0.993. The magazine from spec numbers alone 0.970
  (0.954 before the rake refit, C2). TOP (X >= 245) 0.932.

## 4. Part list (24 records in `smg_spec.json` `parts`)

Each record gives: dimensions in mm (frame M), construction, ruling, material slot and finish, texel class, joint
row, bone, the trace keys it must match (with pixel areas for the L2 per-part rule) and a simplified side profile.

| Part | Bone | Slot | Trace / authority |
|---|---|---|---|
| upper_receiver (vents, long vents, charging slot, eyelet, ledge, inside rails and guides) | body | Furniture | `receiver_upper` + `handguard_area`; RIGHT for right features; TOP width |
| lower_receiver, magwell, trigger_guard, pistol_grip, end_block (one moulding) | body | Furniture | `receiver_lower`, `mag_well`, `trigger_guard`, `grip`, `hinge_block` |
| charging_handle (knob, arm, slide) | charging_handle | Metal | face features + merge re-read |
| bolt (extractor, thumb recess, lug, guide grooves) | bolt | Metal | RIGHT port + real pattern |
| ejection_port_and_catch | body | Furniture | RIGHT face features |
| barrel, muzzle_device | body / muzzle_device | Metal | `barrel`, `muzzle_device` |
| top_rail, lower_rail | body | Metal | `top_rail`, `lower_rail` |
| sight_rear, sight_front | sight_rear / sight_front | Metal | `sight_rear`, `sight_front` (+TOP drum and knob) |
| selector, trigger, mag_release | own bones | Metal | face features, `trigger`, `mag_release` (re-traced: the lever in the guard's front leg) |
| stock_hinge (axle, knuckles, latch housing, button) | stock / body | Furniture + Metal | `stock_hinge_knuckle` |
| stock_frame, butt_pad | stock | Furniture | five strut keys, `butt_pad` |
| magazine_body, magazine_floor_plate | magazine (SM_SMG01_Mag) | Mag | `magazine` |
| pins_fasteners | body | Metal | face features: 12 rows, 9 heads on the LEFT and 10 on the RIGHT, both panels read at 10x |

**Internals modelled at form:**
- the bolt's steel guide rails and its travel space;
- the charging slide, its guide and the bolt's lug;
- the magwell walls (the 4.0 rear wall), shelf and catch window;
- the paddle, its clevis and pin;
- the hinge knuckles and axle; the necked latch bolt and the end block's latch lug (bore, exit slot);
- the port catch's rear lip and the stock's retention lug;
- the charging lever's roll pin in the slide and the lock notch;
- the sight pins (the rear at the leaf's front-lower corner) and detents.

## 5. Real-pattern rulings (craft RP1-RP22, adjusted by this merge)

The full table is in `CRAFT_STUDY.md` section 4; the spec carries it with a `merge_adjustment` field.

**Adjusted by this merge:**
- **RP2:** the axle Y position (R19).
- **RP3:** the merge's knob and slot numbers, with no recess.
- **RP5:** the breech is at X 503, not 485.
- **RP7:** the hubs are equal size on both sides; the selector angles are computed.
- **RP10:** the magazine is 29 thick and the ladder is re-read.
- **RP14:** slots are cut only in the drawn toothed zone.
- **RP15:** the windage drum is on the left; the front clamp knob is on the right.
- **RP16:** the muzzle device OD is 25.5.

**Unchanged:**
- right fold (RP1);
- the forward slots built as vents (RP4);
- the port catch (RP6);
- the centred paddle pushed forward (RP8);
- no bolt catch (RP9);
- steel trigger, integral guard (RP11, RP12);
- grip cover and stipple border (RP13);
- the 6-slot device timed one slot per side (RP16);
- sling points (RP17);
- support bolt and locking pin heads (RP18);
- the seam (RP19);
- the end block as the lower's backplate (RP20);
- the magwell without ribs (RP21);
- nothing the sheet does not draw (RP22): no cheek piece, no side-rail bosses, no housing screws.

**The plan's R1-R20 are answered:**
- R4 -> RP3;
- R5 -> RP5 (75 mm);
- R9 -> RP9;
- R10 -> RP1/RP2 (the port catch, not a stud);
- R12 -> RP15;
- R16/R17 -> RP10/RP21 (no guide ribs);
- R18 -> RP4 (vent, not a plain wall);
- the rest are confirmed.

The real-pattern evidence (operator's manual figures, two Wikimedia images; URLs in the spec `realref`) is in
`scratch/realref/craft/`. It is **local reference only**: the manual figures are copyrighted and one image is CC BY-SA.
Never commit or ship them.

## 6. Materials

| Finish | Where | Values |
|---|---|---|
| Black glass-filled polymer | upper, lower, grip, guard, stock frame | metallic 0, base sRGB (46, 47, 50), roughness 0.58-0.66 (0.52 hand zones), moulded matte micro-texture 0.05-0.15 mm; wear: polish (rough -0.10..-0.18) or whitening (+15..+35 levels), never metal |
| Grip stipple | grip panels | roughness 0.78-0.88, pebbles 0.5-0.8 pitch in the normal map; geometric border |
| Magazine polymer | magazine | base (41, 42, 45), roughness 0.55-0.65 |
| Rubber | butt pad | base (42, 42, 44), roughness 0.82-0.92 |
| Manganese phosphate steel | barrel, device, rails, sights, knob, selector, trigger, paddle, pins | metallic 0, base (48-54), roughness 0.66-0.80 (oiled 0.55-0.65); wears to bare steel (metallic 1, 0.53-0.56 linear, 0.25-0.40) |
| Bolt | bolt | phosphate with bare sliding flanks and face (0.15-0.25) |
| Soot | device slots, crown, port | 0.02-0.03 linear, roughness 0.85-0.95 |

**Slots (plan):**
- `M_SMG01_Metal` on `M_Steel_Master`;
- `M_SMG01_Furniture` and `M_SMG01_Mag` on `M_Fabric_Master` with Metal From ORM off.

The user colour is the polymer colour, in one recolour group. The polymer/steel luminance ratio must stay at 1.3-1.5:
on the sheet the steel reads darker than the polymer.

## 7. Interface (summary; numbers in the spec)

- **Bones (11):**
  - `body`;
  - `bolt` (-X, 0..75);
  - `charging_handle` (-X 0..75, then a lock of 0..+15 deg about X through the slide's roll pin, Y 22.0, Z 27.0);
  - `trigger` (Y, 0..+13, axle at the drawn head);
  - `selector` (Y: SAFE -63.4 / SEMI 0 / AUTO +45);
  - `mag_release` (Y, 0..-11, pin at (445.95, -63.6));
  - `magazine` (head = `Mag`);
  - `stock` (Z, 0..180, head on the axle);
  - `sight_rear` (Y, 0..+90, folds forward);
  - `sight_front` (Y, 0..-90, folds rearward);
  - `muzzle_device`.

  The 8 AR-01 bones keep their names and axes, so `ABP_Gun_LongGun` drives the SMG (U2b) through normalized inputs
  (trigger 0..1, selector detent index, release 0..1, bolt 0..1) that each gun's sidecar `abp_angle_table` maps to
  its own angles.
- **Sockets:**
  - 21 on the gun: the plan's 19 plus `SlingFront` (front-left eyelet) and `SlingRear` (lower stock hole), both shown
    on the sheet. `SupportHand` is provisional until H1; `CenterOfMass` and `Holster` are computed at W1.
  - 5 on the magazine.
  - `Mag` = M (478.67, 0, -78.48), tilted -8.267 deg about Y. `MagInsertStart` is 75.2 mm down the axis.
  - `MagRelease` = the paddle's rear face, M (444.2, 0, -78.6). `Sight` / `SightFront` at Z 76.0.
- **Clips:** the bind pose = SEMI. Fire, Charge and ReloadEmpty hold AUTO. The Selector clip runs
  SEMI -> SAFE -> SEMI -> AUTO -> SEMI. StockFold/Unfold run 0 <-> 180 (button pressed, then the lug snaps under the
  catch lip). ReloadEmpty starts with the bolt on the internal hold-open and the handle forward, and ends with a full
  handle pull and release.
- **Bounds:** gun radius 0.371 m extended, 0.258 m folded (min Y -100.7); magazine 0.131 m. Magazine LOD sizes are
  derived as 1.0 / 0.088 / 0.0352 / 0.0116.

## 8. Gates (all in the spec `gates`)

- **S0:** the spec validator (in the spec: PASS, 0 missing fields, 0 inconsistencies). It now also checks the text
  and the numbers: stale mechanism words in the parts, bones, clips, gates and fold sections, and 14 cross-checks
  (trigger and paddle angles part = bone = clip, sight sockets on the aperture line, paddle-to-wall, nose travel,
  arm motion, neck seat, lug engagement, folded envelope, rail counts and end webs).
- **Look (L1-L8):** sides >= 0.95 at blockout and >= 0.96 at form. TOP (X >= 245) >= 0.92 / 0.93. The 3/4 view is
  camera-solved: IoU >= 0.93 and contour P95 <= 3 px. Per part as the AR-01. The rail notch depth is exempt from L3,
  and so are the paddle's fore-aft faces (declared; its pin head and Z range are gated). L3 lists every drawn head
  (9 LEFT, 10 RIGHT), the oblong recess, the seam boss and the TOP end-block frame.
  Early realism review per part group at form (L8): PASS = at most 1 single-judge fake call per group; a decisive
  fail (both judges call a group fake) stops and goes to the user.
- **Blender:** B1-B11, G5, H1 early/full. B4c: the rear leaf folded <= Z 66.0 (rail top + 15.9), the front
  <= 56.7. H1 early PASS = reach <= 80 mm and grip girth <= real + 10 %; a FAIL puts Q1 to the user (the sheet's
  reach 90.5 is expected to fail).
- **UD1-UD4 from form:**
  - `unreal_drops() == 0` and min triangle area >= 0.01 mm2 at every LOD;
  - no edge under 0.05 mm and no bevel under 0.1 mm;
  - zero-tangent checks and the authored UV1 from W2.
- **Craft F1-F7:**
  - F1: selector sweep >= 0.10 mm;
  - F2: folded length 423.6 +- 3;
  - F3: the stock lug's barb under the catch lip, engagement >= 1.0 mm (spec 1.3);
  - F4: charging handle and arm sweep (the arm >= 0.10 off the wall; it moves outward);
  - F5: catch sweep with the magazine seated, and the bolt's thumb recess visible in the port;
  - F6: stock latch bolt >= 1.5 mm in the lug released (spec 2.0), 0 with the button pressed 2.0;
  - F7: the handle's neck seated >= 2.0 mm in the lock notch at 15 deg (spec 2.4).
- **Magazine:** M1-M10 (straight path; M4b clean with the paddle pressed; no rib rows).
- **Unreal and pack:** U1-U12 incl. U2b (now covering trigger direction, selector detents and release direction on
  both guns); P1-P4.

## 9. Open questions (each has a default the build follows)

| # | Question | Default |
|---|---|---|
| Q1 | Scale 690 (chunky middle: reach 90.5, height 338, width 68.8, folded 424) or ~625? | 690; rescale offered only if H1 fails |
| Q2 | Hidden barrel 156 mm (sheet feed geometry) instead of the real 200? | follow the sheet |
| Q3 | Charging handle: knob as drawn, real 75 mm slot behind it, drawn slots as vents? | yes |
| Q4 | Selector index groove painted white? | plain groove, no paint, no dots |
| Q5 | The folded top strut crosses the port (the real gun fires folded): accept, or raise the strut? | accept (folded = carry) |
| Q6 | Hinge axle at the right-rear corner, so the knuckles stand ~5 mm proud of the right side in TOP (needed for a flat fold), or keep the axle inside and splay the fold? | corner axle |
| Q7 | Mass 2.5 kg (line) or 2.26 kg (manual)? | 2.5 |
| Q8 | Magazine thickness 29 (3/4 view 31 +- 6, real minimum 27)? | 29; checked by the 3/4 gate at blockout |
| Q9 | Standard rail pitch in the drawn toothed zone (21 teeth for the 19 drawn)? | yes |
| Q10-Q15 | Plan Q3-Q6, Q8, Q9: merged magazine in the twin; no folded static; SightFlip clip; authored UV1; one physics body; Fab changes listed, not applied | as stated |
| Q16 | Selector detents: the design call (the sheet's pose = SEMI, SAFE 45 deg below forward, AUTO 45 deg further rearward) or the real figures (SAFE ~25 deg below forward, SEMI and AUTO ~15-20 deg below rearward, so the drawn lever would sit in no detent)? | design call |
| Q17 | Folded-stock retention: a moulded lug on the rear upright's right face (X 35.3-41.3, 3.7 mm beyond the pad's side; not drawn), or a joggled stock arm that brings the frame in (changes the TOP view)? | the lug |

Closed by the merge:
- plan Q1 (right slot: a vent);
- plan Q2 (folds right);
- plan Q7 (no bolt catch);
- measure Q5 (the boss is the catch);
- measure Q6 (RP3).

## 10. Fab-original change list (not applied; the user decides)

From the craft study:
1. three stepped, tapered fore-end vents;
2. a chevron rib on the magwell flank;
3. one long rounded-trapezoid stock opening with a reversed web and a thumb notch;
4. a chevron butt-pad tread with a centre hex screw;
5. a hex-cell grip stipple with a thumb ledge;
6. a 4-port compensator;
7. a magazine with one offset rib, three short grip ribs and a finger-pull floor plate;
8. a mushroom charging knob with three flats;
9. a squared selector tip with a scalloped face;
10. a triangular rear-sight frame.

Any five of vents, stock, grip, muzzle and magazine move the read clearly away from the real pattern. Nothing
buyer-facing names the real pattern or a maker.

## 11. Risks

- **Hand fit (H1):** the sheet's grip group is 13-29 % larger than real, so H1 may fail and force the Q1 rescale.
- **Fold geometry (R19):** derived here, not drawn. The corner axle changes the TOP silhouette by ~5 mm over ~12 mm
  of X (Q6). The retention lug (C3) is a small part the sheet does not draw (Q17); its snap is a declared allowance
  (<= 1.5 mm in the last 3 deg).
- **Paddle position (C1):** the sheet draws the release lever where the magwell's rear wall must be; the paddle is
  built 3.9 mm further back (declared). L8 judges whether it still reads as the sheet's lever.
- **Values that are re-reads or estimates (+-1.5 mm) for L3:**
  - the knob, arm, right vent, aperture height, ladder and sling holes (merge re-reads);
  - the vent outlines, which are dark-feature boxes + 0.6 mm;
  - the paddle pin (the drawn head, moved 0.35 mm by the wall rule) and the trigger axle (the drawn head); form may
    move either by <= 1 mm.
- **Low-confidence widths:** the magazine thickness and magwell width rest on the 3/4 view (+-20 %), and the grip
  width (32) is unseen (real norm).
- **Selector angles:** a design call (Q16): the saved manual figures (72 x 48 px) show SAFE ~25 deg below forward
  and SEMI / AUTO ~15-20 deg below rearward, which the sheet's pose matches neither.

## 12. Check findings and resolutions (2026-10-09)

A checker reviewed the merged spec (its crops and scripts are in `scratch/checker/`, local only). Each finding was
re-verified before anything changed, either on the sheet (gridded 10-20x zooms of the panel crops) or by recomputing
the geometry. All 16 are real. Two fixes differ from the checker's suggestion; the table says where. The fixes live in:
- `tools/trace_reference.py` (trace config and the magazine fit);
- `tools/make_spec.py` (derived numbers, parts, gates, clips, S0 checks; spec `check_findings`);
- `tools/design_sheet.py`, `SMG_BUILD_PLAN.md`, `MEASUREMENT_NOTES.md` and this study.

S0 passes with 0 missing fields and 0 inconsistencies.

| # | Sev. | Area | Verified | Resolution |
|---|---|---|---|---|
| C1 | major | Mag release paddle | Yes. The old trace box X 449-462 is the magwell's rear corner: the lip-band lines run through it. The lever is drawn inside the guard's front leg (panel px x 217-226, y 245-268), with its pin head at (446.3, -63.6). The magazine's rear face is at X 451.3 at Z -52, so the old pivot sat inside the magazine. | **Fixed.** Trace: the old box is relabelled `mag_well`, and the drawn lever is traced as `mag_release`. Built: the magwell's rear wall is 4.0 thick, 0.3 off the magazine and parallel to it. The paddle is 9.0 x 3.5 at X 444.2-447.7, Z -84.6..-58.9. Its pin is at (445.95, -63.6), 0.35 mm behind the drawn head, in a two-ear clevis of the lower. The front face keeps 0.3 to the wall at rest and >= 0.10 over the -11 deg swing down to the lip. The nose tip sits at (451.73, -44.0) in the notch (engagement 1.5) and moves 3.9 mm back when pressed. The paddle stands 3.9 mm behind the drawn lever's front edge: a declared deviation (L3 gates the pin head and the Z range). The `MagRelease` socket, the L2 part areas, the magwell box and the guard's front leg (2.3 mm) are recomputed. |
| C2 | major | Magazine rake | Yes. Over the straight body (Z -240..-90), LEFT reads 8.23 deg at the rear edge and 8.26-8.34 at the front. The old window took in the lip cut and the floor flare. | **Fixed.** `measure_mag` now fits Z0+14 .. Z1-14: **8.27 deg** (LEFT; RIGHT 7.81). `Mag` is (478.67, -78.48) at -8.267 deg. `MagInsertStart`, the magwell axis, the mag frame and the socket rotations are regenerated. The design-sheet magazine IoU rose from 0.954 to 0.970. |
| C3 | major | Folded-stock retention | Yes. Folded, the pad's inner face is at Y -38.9 and the catch's outer face at -37.9; the frame's inner face is at -53.15. Nothing engages. | **Fixed (option A).** The catch gets a hooked lip on its rear edge (1.5 overhang, 1.5 thick). A moulded lug on the rear upright's right face (extended X 35.3-41.3, Z -14.1..2.8, tip Y -32.7) puts its barb under that lip when folded: engagement **1.3 mm**. The snap is a declared allowance (<= 1.5 mm in the last 3 deg), and F3 now has numbers. The lug stands 3.7 mm beyond the pad's side and the sheet does not draw it: **Q17**. |
| C4 | major | Charging-handle lock axis | Yes. About (Y 20, Z 21), +15 deg drives the arm's upper inner edge to Y 32.76, 1.24 mm through the wall. | **Fixed with the real-pattern variant, not the checker's outer-wall axis.** An axis on the outer wall line would drop the neck 0.4 mm, so it could not enter a notch. Instead the lever pivots on a roll pin in the slide's upper inboard corner at **(Y 22.0, Z 27.0)**; the 12 x 12 slide does not rotate (real pattern). Every arm point moves outward (min +0.02). The neck rises 2.40 at the wall's inner face and 3.31 at its outer face (notch rise 4.0); the knob rises 5.7. F4 is restated, and F7 is added (neck seated >= 2.0). |
| C5 | major | Trigger sign, shared ABP | Yes. With Blender R_y, + moves points below the pivot rearward; the AR-01 ships 0..+12. | **Fixed.** The trigger is now 0..**+13**. The ABP drives normalized inputs (trigger 0..1, selector detent index, release 0..1, bolt 0..1), and each skeletal sidecar's `gun.abp_angle_table` maps them per gun (AR-01: 0..12, detents 0/16/32, catch 0..10). U2b now proves the trigger direction, the selector detents and the release direction on both guns. |
| C6 | major | Rear flip-sight fold | Yes. With the pin at the leaf's rear face, the folded head reaches Z 42.2, 7.9 mm into the rail. | **Fixed; B4c is recomputed rather than set to +13.5.** The pin moves to the leaf's front-lower corner, **(336.3, 53.6)**, in a U-channel base whose floor is 2.0 above the rail; the folded top is at Z 65.7. A 12.6 mm head folding forward on a 3.0 pin above the rail cannot stay under rail top + 13.5. So B4c becomes: rear <= Z **66.0** (rail top + 15.9), front <= 56.7, and nothing below the rail top. The front sight was already fine. |
| C7 | major | Missing or mislocated drawn features | Yes, on both panels. The ring head is at (442.1, -38.9), not (433.3, -40.1). Also found: a small head (440.3, -25.4), the oblong recess (409.8, -25.1), the axle head (402.2, -40.2), the seam boss (352.8, -16.8, dia 16.4) with its pin, the end-block head (299.3, -13.3) and the TOP D-frame (X 283.5-310.4). The RIGHT panel has its own set: two seam heads and a head behind its selector instead of the boss, plus a square locking-pin end. | **Fixed.** 12 fastener rows (9 heads LEFT, 10 RIGHT); the recess and seam boss go in `lower_receiver`, the TOP frame in `end_block`. The trigger pivot moves to the drawn axle head. L3 lists every head. The RIGHT read is done now instead of at form. |
| C8 | minor | Lower rail | Yes. round(76.2 / 10.01) = 8 slots, which left 0.45 mm end walls. | **Fixed.** 7 slots centred on the rail (542.97-603.03), with 5.5 mm end webs. The count comes from a formula and S0 checks it. |
| C9 | minor | Sight line | Yes. The drawn ring sits at panel px (320.7, 130.5), which is Z 76.0 (my read: 75.4-76.0). | **Fixed.** Aperture at (330.0, **76.0**), with the post tip on the same line (7.9 under the ear tops). The line is **74.1** above the bore; sight radius 268.6. `Sight` and `SightFront` are recomputed. |
| C10 | minor | Folded envelope | Yes. The latch housing folds furthest out. | **Fixed.** `fold.folded_min_Y` is computed from every stock-bone part: **-100.7** (the latch housing's TOP-read face at 31.8, plus the 1.0 button). Folded radius 0.2581 m. The plan's LOD note is updated. |
| C11 | minor | Selector detents | Yes. Only the manual's SAFE figure is usable: SEMI and AUTO look alike, and the sheet's pose matches neither. | **Fixed as a declared design call** (sheet pose = SEMI, SAFE -63.4, AUTO +45): **Q16**. The clip text is now one sequence from and to the bind pose. |
| C12 | minor | Stale clip text | Yes: the stud, `bolt_catch under R9`, `safe -> semi -> auto -> safe`. | **Fixed.** StockFold/Unfold, ReloadEmpty, Selector, Fire and Reload are rewritten. ReloadEmpty now starts on the internal hold-open with the handle forward and ends with a full pull and release. S0 scans the live sections for stale words and runs 14 number cross-checks. |
| C13 | minor | Rail screws | Yes. 8.5 mm heads cut 1.6 mm into the neighbouring tooth flanks. | **Fixed.** Low button heads, dia 4.8, inside the 5.24 slots. |
| C14 | minor | Stock latch | Yes. Nothing on the receiver took the latch, and the drawn see-through gap at X 272.4 (Z -12.8..+14.2) rules out the old position. | **Fixed.** A lug projects rearward from the end block's left rear, above the gap (X 264.0-272.7, Y 22-28, Z 15-22). It has a dia 4.3 Y-bore at (266.4, 18.5) and a 2.8 rearward exit slot. A dia 4.0 bolt with a dia 2.5 x 6.4 neck sits 2.0 mm in the bore; the button stroke is 2.0. Gate F6. |
| C15 | minor | Texel classes and budgets | Yes. | **Fixed.** Class A covers the sights only; the rail is class B at X < 400 and class C forward. The x2.3 factor applies to every set: Metal ~2.4 M (2048 likely), Furniture ~7.1 M (4096), Mag ~0.8 M (1024-2048). The top-rail floor is 3,500 and the LOD0 floor 26,150. |
| C16 | minor | Gates without numbers | Yes. | **Fixed.** L8: PASS = at most 1 single-judge fake call per group; a decisive fail = both judges. H1 early: PASS = reach <= 80 and girth <= real + 10 %; a FAIL offers Q1 and does not stop the build. F6: the latch (>= 1.5 released, 0 pressed). F7: the handle lock (neck >= 2.0). |

**Not done here:** nothing was built, locked, committed or run in Blender or Unreal. The two new questions, Q16 and
Q17, have defaults the build follows.
