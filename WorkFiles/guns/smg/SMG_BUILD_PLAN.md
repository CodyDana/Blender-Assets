# Compact SMG SM-01 (SMG01): game and tech build plan

**Date:** 2026-10-09. **Role:** game + tech planning only. Nothing was built, no lock was taken, and neither Blender
nor Unreal was run. The machine-readable twin of this plan is `smg_interface.json` (same folder).

**Scope.** The second gun of the line, for the UE 5.8 ninja game (1v1 duel MVP, battle royale later; first- and
third-person use) and the Fab gun pack. One build ships three assets (GUN_BUILDING_STUDY 1.1 #1):
- `SK_SMG01`: the rigged skeletal SMG (+ `_LOD1..3`, `SK_SMG01_Skeleton`, `PHYS_SMG01`, 7 clips `A_SMG01_*`).
- `SM_SMG01`: the static twin, stock **extended**, magazine merged (study Q3 default, AR-01 precedent).
- `SM_SMG01_Mag`: the straight 25-round polymer magazine.

**Reference:** `References/Guns/SMG/smg_sheetA.webp` (Sheet A only: LEFT, RIGHT, TOP, 3/4 FRONT (LEFT); Sheet B was
refused by the generator, so unseen details stay plain). The labels are consistent with handed features (checked
here: the charging-handle knob protrudes on the gun's left in the TOP view, where screen-down = +Y = the gun's left).
The cm ruler is unreliable; scale is the real pattern's (GUN_BUILDING_STUDY 3.5).

**Authority order.** `smg_spec.json` wins over every number in this plan.
- It was merged on 2026-10-09 (W0) by `tools/make_spec.py` from the measurement, the craft study and this plan.
  `SMG_STUDY.md` lists the decisions and `SMG_DESIGN_SHEET.png` draws them.
- **This plan was updated to the spec** in the same step. The layout (section 4), bone heads, rulings, sockets,
  magazine fit, clips, gates and open questions now carry the spec's numbers.
- All numbers are in the spec's frame M: X from the butt-pad rear toward the muzzle, Z up, the bore at Z_M +1.87,
  +Y = the gun's left.
- Where this plan and the spec still differ, the spec wins.
- Everything else here (assets, names, slots, budgets, gates, stage order) is the contract the spec filled.

**Read for this plan:** `CLAUDE.md`; `GUN_BUILDING_STUDY.md` (all, esp. 3.1, 3.3, 3.6, 3.7, 4.1, 4.6, 4.9, 4.10,
5.1-5.10, 6, 7, 8); `WorkFiles/guns/rifle/RIFLE_REPORT.md` (all, esp. 9 and 10), `RIFLE_BUILD_PLAN.md`,
`rifle_spec.json`, `gates/*.json`; `Scripts/guns/rifle/run_rifle.sh`, `run_game.sh`, `run_rig_mag.sh`,
`run_detail.sh`; `Scripts/guns/gunlib/*` (incl. `tspace.py`); `Exports/Guns/AR01/SK_AR01.skeletal.json`;
`WorkFiles/guns/GUN_REFERENCE_PROMPTS.md` (the SMG prompt); the sheet itself.

---

## 0. The plan on one screen

| Item | `SK_SMG01` / `SM_SMG01` | `SM_SMG01_Mag` |
|---|---|---|
| Real scale (study 3.5) | **690 mm** stock extended, **450 mm** folded, barrel **200 mm**, **2.5 kg** without magazine | empty 0.17 kg (manual), loaded = empty + 25 x ~21 g (.45-class round) |
| Triangles LOD0 / 1 / 2 / 3 | **target 25-40k (ceiling 50k)** / ~45 % / ~15 % / 1.2-2k (study 5.7) | **target 2.5-4k (ceiling 5k)** / ~40 % / ~15 % / 150-250 |
| LOD screen sizes | start **1.0 / 0.25 / 0.10 / 0.033** (the AR-01's switch distances at r 0.371 m, spec), fixed by the **measured** LOD-pop gate on the **final engine bounds incl. the bounds extension** (both stock states) | derived: size_mag = size_gun x r_mag / r_gun (SK's engine bounds) |
| Slots | 2: `M_SMG01_Metal` (steel: barrel, rails, sights, muzzle device, bolt, small parts), `M_SMG01_Furniture` (all polymer: receiver, grip frame, stock, buttpad) | 1: `M_SMG01_Mag` (polymer) |
| Masters (pack) | Metal on **`M_Steel_Master`** (the AR-01's shipped choice, Steel Tint) ; Furniture on `M_Fabric_Master`, Metal From ORM **off** | `M_Fabric_Master`, MFO off |
| User colour | **the polymer colour** (`Colour` on Furniture and Mag, one recolour group, default = the shipped black; tan/OD safe because MFO is off) | same group |
| Texture sets | Metal 2048 likely, Furniture 4096, each the smallest power of two that holds its classes at the fill target with the AR-01's x2.3 estimate factor on every set (packer decides; section 9) + Detail16 + Masks | Mag 1024-2048 + Detail16 |
| Texel classes | **A 80-100 px/cm: the sights only (rear diopter, front post + ears)**; B 60-80: top rail X < 400, rear receiver, charging handle, selector, grip top, stock comb/hinge; C 30-40 (top rail forward, lower rail, paddle, trigger); D 25-30; E 8-15 (check fix C15) | C; E inside |
| Bones (11) | `body`, `bolt`, `charging_handle`, `trigger`, `selector`, `mag_release`, `magazine`, `stock`, `sight_front`, `sight_rear`, `muzzle_device` (no `bolt_catch`: RP9, spec R24) | - |
| Skeleton sharing | the 8 AR-01 bones keep their names, parent (`body`), axes and rest rotation; `SK_SMG01_Skeleton` lists `SK_AR01_Skeleton` as compatible, so `ABP_Gun_LongGun` drives both through **normalized inputs** mapped by each gun's sidecar `abp_angle_table` (gate U2b, first proof of the line) | - |
| Clips | `A_SMG01_Fire`, `_Charge`, `_Reload`, `_ReloadEmpty`, `_Selector`, `_StockFold`, `_StockUnfold` (+ `_SightFlip`, open question Q5, default yes) | - |
| Sockets | **21** on the gun (5.3 names + `Rail_Top`, `Rail_Bottom`, `Stock`, `SightFront`, `SlingFront`, `SlingRear`; `Shoulder` and `SlingRear` on the `stock` bone) | 5: `Mag`, `HandReload`, `Feed`, `Base`, `CenterOfMass` |
| Collision (twin) | **8 hulls** `UCX_SM_SMG01_LOD0_00..07` | **1 hull** `UCX_SM_SMG01_Mag_LOD0_00` |
| Physics (SK) | `PHYS_SMG01`: one body on `body` (extended-state stock elements; Q8) | mass + CoM in the sidecar |
| Reload path | straight: `MagInsertStart` -> (lerp along the mag's -Z) -> `Mag`; no rock | |
| Nanite | off on all three | |

**Stage workflows (each a fresh workflow from a commit, section 15):** W1 form -> W2 surface -> W3 rig + mag ->
W4 review + fix -> W5 Unreal -> W6 finish. Each ends in a commit with its gate file passing.

---

## 1. AR-01 lessons, and where this plan applies them

| AR-01 lesson (RIFLE_REPORT 9-10, gates) | Applied here |
|---|---|
| Small parts drifted toward the sheet's close-ups and lost the real pattern; rulings came late (spec R36, R50, R52) | **Real-pattern rulings up front** (section 3), each with its authority; the form stage builds to them |
| Micro bevel / boolean run-out strips: Unreal dropped 4,584 triangles (U5) and logged zero tangents (U10); three post-process fixes broke other gates | **Gate UD1-UD3 from the form stage** (section 14): `gunlib.tspace.unreal_drops()` = 0 on every part at every LOD, min triangle area >= 0.01 mm2 (2x Unreal's 0.005), no edge < 0.05 mm, no needle < 0.02 mm; generators built so they never make strips (4.1); `tspace.collapsed(unreal=True)` = 0 at the UV stage. Patching export meshes is forbidden |
| 16 px per-object bake margin overwrote neighbours (wedges, lines, stipple) | **Bake margin 0**, fill afterwards per island (W2) |
| Magazine AO baked seated printed the receiver's shadow | **Bake the magazine's AO alone** (W2); the twin's merged mag reuses the mag's own maps |
| Edge masks by 3D distance printed through thin walls | **Same-side edge masks** (`gunlib.edgemask.same_side`) from the first paint |
| Bounds extension covered LOD0 only at first | **Bounds extension over LOD0-3 x every clip frame x both stock states x sights up/down** (gate B11) |
| Clips moving the bolt left the selector on safe | **Fire, Charge, ReloadEmpty hold the selector at a firing position** (Auto); gate in rig_export |
| Blender's FBX writes a clip's first frame as node defaults | Review tools pose from absolute matrices (copy `export_review_job.py`); `ReloadEmpty` starts with the bolt held open, so its sidecar flag is `starts_at_rest: false` |
| Per-part blind loops against the sheet cost rounds and judged design, not realism | **Per-part early realism review in the ROUGH LOOK** at the form stage (two realism judges per part group, real photos beside), not per-part blind loops; the blind test is reported once at W4 |
| Sight picture gated late; the realism judge flagged the ADS | **B4 sight picture from the blockout on** (aperture + post), re-run at every stage and every LOD (S2) |
| U8: Unreal's generated lightmap UV overlapped by 1-4 texels on LOD1-3 | Decided before the build: authored UV1 imported as-is (Q6 default), gated in Blender at 64 and 128 px |
| Sidecar `materials` block said `M_Fabric_Master` where the pack used `M_Steel_Master` | Metal slot planned on `M_Steel_Master` from day one; the sidecar writer reads the slot table in the spec |
| Metal estimate was 2.4 M texels, the packer needed 5.57 M (2.3x) | Texture sets sized by the packer only; the estimate here is for memory planning, with the 2.3x factor shown |
| LOD3 ~1.1k accepted after the fact; LOD-pop measured late | LOD3 targets set now; LOD-pop on both stock states at W3 |
| Wood per-piece hues broke the scalar recolour | Polymer is one hue by construction (one stain x luminance detail); P1 measured, BC7 fallback recorded |
| Pack build from a worktree needs a short-path mirror root | W6 reuses the AR-01 mirror method; MAX_PATH-safe paths |
| Each later stage worked best as a fresh workflow from a commit | Section 15 |

---

## 2. Frames, skeleton and skeleton sharing

### 2.1 Frame (study 5.1)

- Blender metres, modelled in mm. **+X = muzzle** (bore exactly parallel to X at Y = 0), **+Z up**, **-Y = the gun's
  right side** (ejection port side). Unreal: +X forward, +Y right, +Z up.
- **Origin = `Grip`**: on the grip's centre axis in Y = 0, 46 mm down the grip axis from the web line (the AR-01's H1
  value; H1 early confirms or moves it).
  - **Grip = M (335.67, 0, -96.49).**
  - Grip axis **21.87 deg** from vertical (the traced midline over Z -70..-140), written in the sidecar as
    `grip_axis_deg`.
  - B = M - Grip; the bore is at B Z +98.36.
- Blender front view (from -Y) shows the RIGHT side, muzzle to screen right: it matches the sheet's RIGHT panel
  directly. The LEFT panel (muzzle to screen left) is the Blender back view.

### 2.2 Bones (study 5.2; lowercase snake; rest rotation = root's; every bone deforms except `magazine`)

| Bone | Parent | Head on | Motion (spec sets numbers) | Joint row (3.7) |
|---|---|---|---|---|
| `body` | (root object) | Grip origin | fixed parts; the physics body | - |
| `bolt` | body | bolt face centre at rest, M (503.0, 0, 1.87) | translate -X, 0..75 | sliding 0.15-0.40 |
| `charging_handle` | body | knob centre at rest, M (549.3, 43.15, 21.0) | translate -X 0..75; at full travel a lock rotation about X 0..+15 deg about the lever's **roll pin in the slide (Y 22.0, Z 27.0)**; the slide does not rotate (real pattern; check fix C4); pushes the bolt via its slide | sliding 0.15-0.40 |
| `trigger` | body | trigger axle = the drawn head, M (402.2, 0, -40.2) | rotate about Y, **0..+13 deg** (+ = the lower end rearward, as the AR-01's 0..+12; check fix C5) | hinge 0.10-0.30 |
| `selector` | body | selector shaft axis, M (363.4, 0, -28.5) | rotate about **Y** (as the AR-01's lever); bind = sheet pose = SEMI, SAFE -63.4, AUTO +45 deg | hinge 0.10-0.30 |
| `mag_release` | body | paddle pin, M (445.95, 0, -63.6) (the drawn pin head moved 0.35 back by the wall rule; check fix C1) | rotate about Y, 0..-11 deg (- = the lower end forward, the nose rearward) | hinge 0.10-0.30 |
| `magazine` | body | **well-entry centre** (= `Mag`), M (478.67, 0, -78.48), tilted -8.267 deg about Y (straight-body rake fit, check fix C2) | attach only, no weighted vertices | seated-mag row |
| `stock` | body | **on the hinge axle** (vertical), M (272.4, -33.95, 1.87) | rotate about Z, 0 (extended) .. +180 deg (to the right) | hinge 0.10-0.30 |
| `sight_rear` | body | rear leaf pin at the leaf's **front-lower corner**, M (336.3, 0, 53.6) (check fix C6) | rotate about Y, 0 (up, as drawn) .. +90 deg (folds forward) | hinge 0.10-0.30 |
| `sight_front` | body | front leaf pin, M (600.0, 0, 54.1) | rotate about Y, 0 (up) .. -90 deg (folds rearward) | hinge 0.10-0.30 |
| `muzzle_device` | body | barrel shoulder (`MuzzleSeat`), M (644.1, 0, 1.87) | none (hidden when a suppressor mounts) | - |

- 11 bones (study range 10-11). No `bolt_catch` (RP9).
- **Same bones on every LOD** (study 1.4); `magazine` survives the FBX unweighted (B1).
- **Skeleton sharing (study 5.2, U2b).** `SK_AR01_Skeleton` has `body, bolt, trigger, selector, mag_release, magazine,
  sight_rear, muzzle_device`, all children of `body`. The SMG keeps those eight names, the same parent, the same
  rest rotation (identity) and the same motion axes (bolt -X, selector about Y, sight_rear about Y), and adds
  `charging_handle`, `stock`, `sight_front` as leaves of `body`. So the SMG skeleton is a strict superset: listing
  `SK_AR01_Skeleton` as compatible lets `ABP_Gun_LongGun` (authored on the pilot) drive the SMG's bolt, trigger,
  selector and release; nodes naming the AR-only bones do nothing on either. Bone head positions differ per gun and
  do not matter to Transform Modify Bone in bone space.
- **Normalized ABP inputs (check fix C5).** The two guns differ in angles: the AR-01 ships trigger 0..+12, selector
  detents 0 / 16 / 32, catch 0..+10; the SMG has trigger 0..+13, selector SAFE -63.4 / SEMI 0 / AUTO +45, paddle
  0..-11. The ABP therefore drives normalized inputs (bolt 0..1, trigger pull 0..1, selector detent index, release
  0..1) and each skeletal sidecar's `gun.abp_angle_table` maps them to that gun's angles; U2b proves the direction of
  every one on both guns.

---

## 3. Real-pattern rulings for the small parts (decided now; the real-pattern study confirms with photos)

**Status after the W0 merge.** The craft study (`CRAFT_STUDY.md` section 4, RP1-RP22) answered every *confirm*
below. The build follows the RP rulings as adjusted in `smg_spec.json` (`real_pattern_rulings`). The table below is
kept as the plan's original record. Changed rows:
- **R4 -> RP3:** the knob stays where drawn, with a 75 mm slot BEHIND it and the lock notch at the slot's rear.
- **R5:** travel 75 mm, breech at X 503.
- **R9:** the bolt catch is not built.
- **R10:** the stock folds right about a right-rear corner axle and is held folded by the port's integral catch (no
  stud): a moulded lug on the stock's rear upright snaps under the catch's rear lip (check fix C3, Q17).
- **R12:** aperture 2.0 mm; the rear sight folds forward and the front rearward; the windage drum is on the left.
- **R16/R17:** no guide ribs or channels (the ladder is recessed).
- **R18:** the right-side slot is built as a vent, as drawn (it is not a mirror).

The pattern is a modern boxy polymer .45 blowback SMG with a side-folding skeleton stock. Main views decide the
silhouette and positions; the real pattern decides how each small part is built. The real-pattern study saves the
photos it uses under `WorkFiles/guns/smg/scratch/realref/` and lists their URLs in the spec (`realref` block). A
ruling marked *confirm* is the default the build follows unless that study finds the real pattern differs; any
design-level disagreement goes to the user (study Q11).

| # | Part | Ruling (construction) | Authority / note |
|---|---|---|---|
| R1 | Receiver | Two moulded polymer shells (upper with the sight rail seat, lower with the integral grip, guard and magwell), **P-round edges 0.6-2 mm, 1-2 deg draft on walls, a parting line on the mould split**, moulded reinforcement ribs as geometry, the 2 x 2 oblong side vents as through-openings with wall thickness, fastening pins as flush inset rings | sheet main views (outline, vents, ribs, pins); real pattern (wall thickness ~3 mm, draft, parting line) |
| R2 | Top rail | Separate steel 1913-profile rail from `gunlib.rail_1913` (true dims, section 5); length from the sheet, slot count = round(length / 10.01); butt joint 0.01-0.05 mm to the receiver, screws only where the sheet shows heads | sheet (length, ends); line standard (profile) |
| R3 | Lower rail | Short 1913 section under the front, same module; slot count from its sheet length | sheet LEFT/RIGHT |
| R4 | Charging handle | **Non-reciprocating, left side front**: knob + arm outside, a slide inside a guide in the upper shell that pushes a lug on the bolt; rests forward, pulled to the rear for charging, returns forward on its own spring. The slot through the left wall is cut for the full travel. *Confirm:* the sheet draws the open slot AHEAD of the knob; if the real pattern rests the handle at the slot's rear end, the travel direction stays -X and the slot is extended behind the knob only as far as the sheet's arm outline allows (a design conflict otherwise: ask) | position from LEFT + TOP; construction from the real pattern |
| R5 | Bolt | Blowback bolt: one heavy steel block with the bolt face, extractor, firing-pin hole and a charging lug; rides two guide rails moulded/inserted in the upper; visible through the right-side ejection port; travel = real figure (*rough* 60-70 mm, never less than a .45-class round's 32.4 mm + feed clearance); port cut for the whole travel | RIGHT panel (port); real pattern (bolt shape, travel) |
| R6 | Ejection port | Right side only, through the upper wall with ~3 mm wall reveal, dark interior, breech face of the barrel and the mag's feed lips visible behind it with the bolt back | RIGHT panel; real pattern |
| R7 | Selector | **Ambidextrous: one transverse shaft with a lever on each side**, one part on one bone; positions safe / semi / auto (the burst position only if the real pattern's lever arc shows it); no markings (no letters, no pictograms, no dots: study 3.2). The sheet's small red dots are not built | both side views (lever shape, hub); real pattern (shaft, arc, detents) |
| R8 | Mag release | **Ambidextrous paddle behind the magwell**, pivoting about Y; its nose engages a notch on the mag's rear face; the paddle can be swept forward to release | sheet (small lever ahead of the guard); real pattern (paddle, notch) |
| R9 | Bolt catch | The real pattern has a bolt hold-open with a release catch on the left. Build it **only if the sheet's LEFT view shows the catch** (the measurer checks the feature near the guard); then a `bolt_catch` bone (rotate about Y). Otherwise the bolt still holds open in `ReloadEmpty` (internal catch, not modelled) and the charging handle releases it | invent nothing the sheet does not show |
| R10 | Stock | Side-folding skeleton polymer stock: two-knuckle hinge with a vertical steel pin at the rear of the receiver; a spring detent holds it extended; a hook/lip at the stock's front snaps over a stud on the receiver to hold it folded. **Fold side and fold angle from the real pattern** (*confirm*; the sheet's TOP view shows the knuckle block toward screen-up = the gun's right). The folded stock must leave the ejection port's throw path clear (real-pattern behaviour: it fires folded) | sheet (outline, hinge block, holes); real pattern (hinge, latch, side) |
| R11 | Buttpad | Polymer/rubber pad with its serrated rear face as geometry (the serration shows in the silhouette); the two round holes in the stock frame as through-holes | sheet LEFT/RIGHT/TOP |
| R12 | Flip sights | **Rail-clamp flip sights** from one `gunlib.sights_flip` design shared with CB01: a clamp base whose recoil lug sits in a rail slot (integer slot index), a spring-detented leaf on a transverse pin. Rear: diopter aperture disc (aperture size from the real pattern, *rough* 2.0-2.6 mm, ghost-ring outer); front: post inside protective ears/hood. Both modelled UP (as drawn) with a folded state (bones). No windage/elevation markings | sheet (positions, outline); real pattern (clamp, detent, aperture) |
| R13 | Grip | Moulded polymer grip integral with the lower; the stipple panel as a **border in geometry** + stipple in the normal map (class B, 0.75-0.90 roughness); a finger-groove-free front strap as the sheet draws | sheet; study 3.2 |
| R14 | Trigger and guard | Steel trigger blade (C-fillet), polymer guard integral with the lower (no separate guard part unless the sheet shows a seam) | sheet |
| R15 | Barrel + muzzle | Phosphated steel barrel (R ~ the sheet's diameter at the collar), bore >= 2 calibres deep with a chamfered crown; slotted cage muzzle device with real through-slots on `muzzle_device`; `muzzle_class` = ".45-class pistol calibre" kept as data only (study 5.5) | sheet (device outline, slot count); real pattern (bore, crown) |
| R16 | Magazine | Straight double-stack polymer magazine; the side "ladder" grooves and ribs as geometry; floor plate with its retaining tab; feed lips + follower modelled (seen in the reload), **no cartridge** (the sheet shows none; AR-01 precedent); a catch notch on the rear face; no witness holes or numbers | sheet; real pattern |
| R17 | Mag well internals | Flared polymer well, two internal guide channels matching the mag's guide ribs, a hard top contact (feed-ramp shelf) above the seated mag, the catch window at the rear | real pattern; fitted to the mag (section 12) |
| R18 | Right-side upper slot | The sheet's RIGHT panel draws a long slot near the top front that mirrors the left charging-handle slot (an AI mirror, like the AR-01's mirrored selector, R1 there). **Default: the real pattern decides** (a plain wall if the real pattern has no right-side slot); Q1 | sheet self-contradiction |
| R19 | Fasteners | Count and position from the sheet only; sizes from norms when a head spans < 4 sheet px (pins 3-5 mm, screws 5.5-8.5 mm heads, written in mm, never "M"+number) | study 3.2 |
| R20 | Markings | None anywhere (no logo, serial, selector letters, calibre, "SAFE"/"FIRE") | IP rule |

---

## 4. Layout (from `smg_spec.json`, frame M: X from the butt-pad rear, Z up; the bore is at Z +1.87)

| Feature | Spec |
|---|---|
| Overall / folded | 690.0 / 423.6 (the folded rearmost point is the hinge knuckles at X 266.4; real 450, spec R20) |
| Muzzle device | X 644.1-690.0 (cage 652.2-690), OD 25.5; `MuzzleSeat` X 644.1 |
| Barrel | exposed X 621.9-644.1 (collar ring dia 24.8, neck 22.6); breech X 503, crown X 659: 156 mm (Q2) |
| Receiver | X 292.8-621.9 (329.1); top under the rail Z 39.9; upper/lower seam Z -18.5; width 68.8 (fore-end 62.7) |
| Top rail | X 292.8-618.1, top Z 50.1; 21 teeth / slots 2-23 at 10.01 in the drawn toothed zone; lug slots 0 (X 328.42 = `Rail_Top`) and 27 |
| Lower rail | X 534.9-611.1, bottom Z -41.1, 7 slots centred (542.97-603.03, end webs 5.5) |
| Sights | rear base X 309.9-339.9, aperture (330.0, 76.0) (the drawn ring, check fix C9); front base X 587.7-612.2, post tip (598.6, 76.0), ear tops 83.9; sight radius 268.6; sight line 74.1 above the bore |
| Charging knob (left) | dia 18.5 at (549.3, 21.0), tip Y +52.4; slot X 470.8-552.6 behind it |
| Ejection port (right) + catch | port X 449.1-512.6, Z 2.5-26.1; catch X 511.3-527.9, Z -16.1..26.2, 3 mm proud |
| Magwell / magazine | magwell X 449.1-539.2, lip line (505.1, -73.4)-(455.7, -82.9), rear wall 4.0 (+0.3) parallel to the magazine; magazine X 456.3-527.3, floor Z -253.9, rake 8.27 deg, 46.6 x 29.0 |
| Mag release | paddle 9.0 wide x 3.5 deep, X 444.2-447.7, Z -84.6..-58.9, pin (445.95, -63.6) in a clevis of the lower; nose to the notch at (451.73, -44.0); 3.9 mm behind the drawn lever (declared, check fix C1) |
| Trigger guard / trigger | guard X 357.7-450.2, bottom Z -121.4; trigger finger face X 409.4 at Z -77.9; reach 90.5; trigger axle (402.2, -40.2) |
| Selector | pivot (363.4, -28.5), hub 20.7 |
| Grip | X 283.3-375.0, bottom Z -167.8, rake 21.87 deg; `Grip` (335.67, -96.49) |
| End block / hinge | end block X 272.7-295.1; stock knuckle X 244.6-272.9; axle (272.4, -33.95) |
| Stock + butt pad | frame X 31-244.7 (29.5 wide); pad X 0-31.0, Z -87.6..25.7 (113.3), 58 wide |
| Heights | 338.3 with the magazine (Z 84.3..-253.9), 252.1 without |
| Length of pull | 409.4 (butt rear to the trigger face; H1 reports it against the real pattern) |

Bounding radius (box half-diagonal): 0.371 m extended without the magazine, 0.258 m folded (min Y -100.7 at the
latch housing + button, check fix C10), magazine 0.131 m.

---

### 4.1 Construction rules (tech side; generator mid-poly, study 4.4)

- Every moving part a separate closed solid with pivot, axis, limits and joint row in the spec (study 11.2):
  bolt, charging handle (knob + arm + slide), trigger, selector, mag release, stock (+ its hinge knuckles and latch
  lip), both flip sights (leaf + aperture/post), muzzle device. Fixed parts are separate solids too (rails, shells,
  pins), joined only at the rig and twin steps.
- **Internals the moving parts touch are modelled at form** (task rule): the bolt's guide rails and the space it
  travels in; the charging handle's guide slot and slide; the bolt's charging lug the slide pushes; the magwell's
  rear wall, top shelf and catch window (no guide channels: RP21); the paddle, its clevis and pin; the hinge
  knuckles and axle; the latch bolt (necked, dia 4.0 / 2.5) and the end block's latch lug with its bore and exit slot;
  the stock's retention lug and the port catch's rear lip; the flip sights' pins and detent bosses. Hidden surfaces get class E texels, never
  deletion, wherever a motion reveals them (port interior with the bolt back, the well with the mag out, hinge faces
  with the stock folded).
- **Degenerate-safe generators (UD gates, section 14).** No bevel narrower than 0.1 mm (sub-visibility edges get no
  bevel, not a 0.02 mm one); bevels clamped so no run-out strip forms where a bevel meets a boolean cut; boolean
  cutters kept >= 0.1 mm from existing edges and faces (no coplanar or near-tangent cuts); the polymer ribs and vents
  cut into the outline/loft where possible (study 4.4) rather than booleaned. Each part generator runs
  `tspace.unreal_drops()` and the micro-edge / needle checks on its own output, at every LOD level, before the part
  is accepted. `tspace.unreal_safe` and friends stay diagnostics only.
- Butt joints 0.01-0.05 mm modelled gap (no shared vertex positions); B6a on the joined twin from the form stage.
- Polymer: P-round radii, 1-2 deg draft, parting line along the mould split, sink only where the sheet shows it,
  ejector circles only on hidden faces (study 3.1, G19).
- LOD1-3 from the same generators through `gunlib.lod` (no Decimate); LOD3 = the blockout generator per part group.

---

## 5. Rails (shared gunlib geometry) and the attachment interface

- **New `Scripts/guns/gunlib/parts/rail_1913.py`** (W1a, lock `GunLib`): `rail_1913(n_slots, pad_front, pad_rear,
  height, lod)` -> closed solid in the rail's own frame (X along the slots, Z out of the rail top), plus a record of
  slot centres.
  - Profile (study 5.4, MIL-STD-1913): width across the dovetail **21.2 mm**, flanks **45 deg**, slot width
    **5.24 mm** (5.23-5.26) with square bottoms, pitch **10.01 mm**, slot depth **3.00 mm**, height ~9.5 mm (the
    SMG's from the sheet), crisp M-chamfer 0.3-0.5 mm (never under 0.1: UD rule).
  - LOD1 keeps every slot (silhouette in the side view), halves bevel segments; LOD2 keeps slots as single-face cuts;
    LOD3 = the rail's box.
  - Slot geometry built into the profile/loft, not booleaned (clean topology, no run-out strips).
  - Unit test (plain Python + one headless run): slot pitch and width within 0.01 mm, `unreal_drops` = 0 at every
    LOD, closed manifold.
- **On the SMG:** `Rail_Top` on the top rail, `Rail_Bottom` on the lower rail: each at the centre of slot 0
  (rearmost) on the rail-top plane, +X along the slots, +Z out of the rail (so `Rail_Bottom` is rolled 180 deg: its
  +Z points down). The sidecar records `rail_slots` per rail (count and the slots the flip sights occupy).
- **Attachment snap:** an attachment's `Mount` goes to `Rail_X + k x 10.01 mm` along +X, integer k. The flip sights
  themselves are placed this way (R12), which proves the snap on our own parts first.
- **Optic clearance gate (B4c):** the folded rear leaf stays under Z 66.0 (rail top + 15.9: its 12.6 mm head folds
  forward about a pin at its front-lower corner, so +12 was unreachable; check fix C6) and the front under Z 56.7;
  the attachments kit's lowest optic window bottom replaces these when that kit has a spec.

---

## 6. Sights: bones, not static

- **Decision: `sight_rear` and `sight_front` are bones** (hinge about Y), modelled UP as the sheet draws them.
  Reasons: the top rail exists to take optics, and the real flip sights fold under an optic; Compatible Skeletons
  already share `sight_rear` with the AR-01; the CB01 inherits the same module and bones (study 2.4 "one flip-sight
  design for SMG + Carbine"); the cost is two bones and one optional clip.
- **B4 sight picture (from the blockout on):** camera at the `gun_standard` ADS (55 deg, 2560 x 1440), eye 0.25 m
  behind `Sight` along -X; `Sight` sits at the **aperture centre**, +X toward the front post tip. Pass: the post tip
  at the aperture centre within 0.5 px laterally and vertically; the front ears/hood ring concentric with the
  aperture within 1 px (reported); nothing between (rail, charging knob, hinge block) occludes the post; post visible
  >= 1 mm. **B4b (reported):** the same at the real cheek-weld eye point (from the stock comb and H1, *rough*
  ~80-100 mm behind the aperture), where the aperture becomes the ghost ring. **B4c:** the optic clearance above.
- S2 repeats B4 at LOD0-3 on the twin and the SK.

---

## 7. Budgets

### 7.1 Gun per part: floor allocation (LOD0 / LOD1 / LOD2)

Extra triangles up to the 25-40k target go to bevel rings where the early look shows faceting (study 5.7).

| Part | LOD0 | LOD1 | LOD2 | Notes |
|---|---|---|---|---|
| Upper receiver shell (flat sides, ribs, 2 x 2 vents, port with walls, charging slot, rail seat) | 3,500 | 1,500 | 500 | |
| Lower receiver (grip frame, integral guard, magwell flare + guides + catch window, stipple border) | 3,600 | 1,500 | 500 | |
| Top rail (1913, 24 cut slots: 22 in the toothed zone + 2 hidden lug slots) | 3,500 | 1,300 | 400 | class B (X < 400) / C; ~140 per chamfered slot (check fix C15); slots kept at LOD1 |
| Lower rail (short) | 800 | 350 | 100 | |
| Rear flip sight (clamp, leaf, aperture disc, pin) | 1,800 | 800 | 200 | class A |
| Front flip sight (clamp, ears/hood, post, pin) | 1,500 | 650 | 180 | class A |
| Barrel (exposed) + bore + collar | 1,000 | 450 | 120 | 48 / 24 / 12 sides |
| Muzzle device (slotted cage, real slots) | 1,200 | 500 | 150 | bone `muzzle_device` |
| Bolt (+ extractor, face, lug) + guide rails | 1,100 | 450 | 120 | seen through the port |
| Charging handle (knob, arm, slide) | 800 | 350 | 100 | |
| Selector (ambi shaft + 2 levers) | 700 | 300 | 80 | |
| Trigger | 350 | 150 | 40 | |
| Mag release paddle | 400 | 160 | 40 | |
| Hinge (end block, knuckles, axle, latch housing + button, latch bolt and lug), port catch + lip | 1,800 | 750 | 200 | |
| Skeleton stock frame (2 openings, holes) + retention lug | 2,400 | 1,000 | 300 | |
| Buttpad with serrations | 900 | 400 | 120 | serration is silhouette |
| Pins, screws (sheet count) | 800 | 250 | 0 | |
| **Total (floor)** | **~26,150** | **~10,860** | **~3,150** | target 25-40k, ceiling 50k; LOD3 1.2-2k |

The twin's `qa_check --budget` = 50,000 + the mag ceiling 5,000 = **55,000** (AR-01 used 57,000 = 50k + 7k).

### 7.2 Magazine

| Part | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| Body with the ladder channels and ties (real geometry), spine rib, catch notch | 1,900 | 750 | 250 |
| Floor plate + retaining tab | 450 | 180 | 60 |
| Feed lips + follower (seen in the reload) | 650 | 250 | 70 |
| **Total** | **~3,000** | **~1,180** | **~380** |

`qa_check --budget 5000`; LOD3 150-250.

---

## 8. LODs and the bounds extension

- Unreal's screen size ~ 1.78 r / d at 16:9, 90 deg hFOV (rifle plan 2.4). Starting sizes keep the AR-01's switch
  distances (0.8 / 2.7 / 6.7 / 20 m): with r ~0.37 m that is **1.0 / 0.25 / 0.10 / 0.033**. FP components force LOD0.
- **The LOD-pop gate fixes them** (B8: mean <= 1 px, max <= 3 px at 2560 x 1440, 90 deg, 4 headings), run on **both
  stock states** (a third-person or dropped SMG may be folded) and with the sights up.
- **The bounds extension changes the radius Unreal uses for LOD selection** on the SK (the skeletal mesh's bounds
  include the extension) [J: confirmed or refuted by U5]. A folded stock reaches Y -100.7 (the latch housing and its
  button; the pad's outer face is at -96.9; check fix C10), 49.6 mm beyond the front sight knob's -51.1 (spec `fold`). So the SK's
  sizes are converted from the measured switch distances with the **final engine bounds radius**, and the twin (no
  extension, stock extended) gets its own sizes from its own radius. The mag's derived sizes use the SK's engine
  radius (the mag rides the SK); `SM_SMG01_Mag` dropped on its own uses the same sizes (the AR-01 precedent).
- **Bounds extension (gate B11):** posed envelope of LOD0-3 over every frame of every clip (incl. StockFold /
  StockUnfold and SightFlip) and the static folded state, minus the bind AABB, rounded up to 0.1 mm; 0 vertices
  outside at U5 (sampled at clip rate).

---

## 9. Materials, texture sets, texel density, recolour

### 9.1 Finishes (study 3.3; L5 calibrates against sheet crops)

The spec carries the craft study's sheet-calibrated values (spec R21: polymer sRGB (46, 47, 50), roughness
0.58-0.66; phosphate steel sRGB 48-54, roughness 0.66-0.80; rubber 42 / 0.82-0.92; magazine polymer 41-45 / 0.55-0.65).
The ranges below are the plan's original envelope.

| Finish | Where | Metallic | Base (sRGB) | Roughness | Wears to |
|---|---|---|---|---|---|
| Glass-filled black polymer | receiver shells, grip frame, stock, magwell | 0 | 40-55 | 0.50-0.70; stipple 0.75-0.90 | itself, **polished** (rough -0.10 to -0.20, a touch lighter), never metal (G8) |
| Rubber-like buttpad | buttpad | 0 | 35-45 | 0.70-0.90 | barely; dust |
| Manganese phosphate steel | barrel, rails, sights, muzzle device, trigger, pins, selector shaft | 0 | 50-70 | 0.65-0.85 (oiled 0.55-0.70) | bare steel (metallic 1, 190-196, 0.25-0.40) on edges in sharp chips |
| Bolt | bolt | 0 (phosphate) with polished bare-steel rails/face (metallic 1) | 50-70 / 190-196 | 0.65 / 0.15-0.25 sliding | - |
| Polymer magazine | mag | 0 | 40-50 | 0.55-0.75 | polished at spine, floor plate corners, lips |
| Soot | muzzle slots, port, bolt face | 0 | ~0.025 lin | 0.80-0.95 | gradient |

Wear by cause (study 3.4): support hand on the magwell and lower rail, firing hand on the grip, thumb arc of both
selector levers, charging-handle knob, insertion streaks into the well and on the mag spine, stock edges and buttpad
heel/toe, sight ears, rail edges. Moderate, as the sheet.

### 9.2 Slots, masters, recolour

| Asset | Slot (index) | Master | Buyer / user control |
|---|---|---|---|
| SK + SM twin | `M_SMG01_Metal` (0) | `M_Steel_Master` (Steel Tint; the AR-01's shipped `MI_AR01_Metal` precedent) | Steel Tint (subtle on dark phosphate) |
| SK + SM twin | `M_SMG01_Furniture` (1) | `M_Fabric_Master`, Metal From ORM **off** | **`Colour` = the polymer colour (the user colour)** |
| Mag | `M_SMG01_Mag` (0) | `M_Fabric_Master`, MFO off | `Colour` (same recolour group as Furniture) |

- One recolour group `SMG01` (Furniture + Mag), default = the shipped black: the default capture must equal the
  shipped BC (P1); light colours (tan, OD, FDE) are safe because no slot that carries polymer has MFO on (study 5.9
  brightness trap). P2 stress set incl. `FFFFFF FF0000 0000FF F2E8D5 000000` + tan/OD/FDE.
- Polymer is one hue by construction (one colour x the luminance detail), so the AR-01's per-piece wood-hue problem
  does not arise; measure P1 at BC1 first, BC7 for the polymer BC if BC1 misses (AR-01: 12 -> 4 levels).
- Draw calls per held gun: 2 x 2 (gun) + 2 x 1 (mag) = 6.

### 9.3 Texture sets (each = smallest power of two holding its classes at fill >= 70 % Metal / 65 % others)

| Set | Content | Classes | Rough need (texels) | Expected size |
|---|---|---|---|---|
| `T_SMG01_Metal_{BC,ORM,N}` + `_Masks` | rails, sights, barrel, device, bolt, handle, selector, trigger, paddle, pins | **A: the sights only** (~40 cm2 at 90), B: top rail X < 400 (~53 cm2 at 70), bolt, handle, selector (~25 cm2 at 70), C: top rail forward (~107 cm2 at 35), lower rail, trigger, paddle (~40 cm2 at 35), D: barrel, device (~80 cm2 at 28), E | ~1.0 M at estimate; x2.3 (AR-01's estimate error) = ~2.4 M | **2048 likely** (holds 2.94 M at 70 %); 4096 if the packer needs it |
| `T_SMG01_Furniture_{BC,ORM,N}` + `_Masks` + `Recolour/T_SMG01_Furniture_Detail16` | all polymer | B: rear receiver behind the magwell, grip top, stock comb + hinge (~450 cm2 at 65), C: the rest (~900 cm2 at 35), E: well and port interiors, hinge faces | ~3.1 M at estimate; x2.3 = ~7.1 M | **4096** (holds ~10.9 M at 65 %) |
| `T_SMG01_Mag_{BC,ORM,N}` + `_Masks` + Detail16 | the magazine | C (~270 cm2 at 35), E inside | ~0.35 M; x2.3 = ~0.8 M | **1024** at the estimate (0.68 M at 65 %); 2048 if the x2.3 factor holds |

- No UDIM, no trim sheets; no mirrored or stacked islands; SK UV0 in 0..1 per slot; the SM twin moves slot k to U
  tile k (Metal 0, Furniture 1, merged mag -1; study 5.8).
- Maps: BC sRGB, ORM linear (R AO, G rough, B metal), N DirectX, power of two, full mips; `TEXTUREGROUP_Weapon` /
  `WeaponNormalMap`; Masks R edge, G handling, B cavity, A refinishable (polymer and coating = 1; bare steel, sights'
  bare edges = 0).
- **Bake rules (AR-01 lessons):** margin 0 then per-island fill; the magazine's AO baked **alone** (no gun around it);
  the gun's AO baked at rest, stock extended, magazine **out** where the well interior is class-E visible, then the
  seated-mag contact shadow added only on the gun side if the review asks for it; same-side edge masks; wear masks
  analytic (bevel parameter + spec handling zones + cavity from AO).

---

## 10. Sockets

All values come from the spec; this table fixes names, bones and axes. Blender mm -> Unreal cm = (x, -y, z) / 10.

### 10.1 Gun `SK_SMG01` / `SM_SMG01` (21)

| Socket | Bone | Place and axes | Use |
|---|---|---|---|
| `Grip` | body | origin, weapon axes | attach to `weapon_r` |
| `SupportHand` | body | off-hand palm on the **magwell front** (study 5.3 SMG default; H1 may move it to the lower rail), +X along the bore | hand_l IK |
| `Trigger` | trigger | trigger face | index finger |
| `Muzzle` | muzzle_device | bore exit, +X out | flash, tracer |
| `MuzzleSeat` | body | barrel shoulder, +X forward | suppressor seat |
| `Sight` | sight_rear | aperture centre, +X toward the post tip | ADS (eye relief = game data) |
| `Mag` | magazine | well-entry centre, +Z = out of the well along the insertion axis | `SM_SMG01_Mag`, zero relative transform |
| `MagInsertStart` | body | `Mag` moved along its -Z by the insert depth + 10 mm (mag top clear of the well lip) | straight path start |
| `ShellEject` | body | port centre, +X = throw direction (right, forward/up per the real pattern) | casing spawn |
| `ChargingHandle` | charging_handle | knob centre | hand target |
| `Selector` | selector | left lever tab (the thumb side) | thumb target |
| `MagRelease` | mag_release | the paddle's rear face 6 mm above its bottom, M (444.2, 0, -78.6) | finger target (the trigger finger pushes it forward) |
| `Rail_Top` | body | top rail, slot 0 centre on the rail-top plane, +X along slots, +Z up | attachments |
| `Rail_Bottom` | body | lower rail, slot 0 centre, +X along slots, +Z out of the rail (down; roll 180 deg) | grip / light |
| `Stock` | body | hinge face on the receiver | modular stocks |
| `Shoulder` | **stock** | buttpad centre, +X = pad normal reversed | TP aim offsets; follows the fold |
| `Holster` | body | stowed hang point (= CoM until the game sets it) | stowed |
| `CenterOfMass` | body | computed, stock extended (the folded CoM is reported in the sidecar) | physics |
| `SightFront` | sight_front | post tip | optional: the folded-state check and the review camera (study 5.3 dropped it on the AR-01 because `Sight` +X carries the line; kept here because the front sight is its own bone) |
| `SlingFront`, `SlingRear` | body / stock | the sheet shows both: the front-left eyelet on the receiver face, M (621.9, 24.0, 31.0) (3/4 view); the stock's lower rear through-hole, M (40.1, 0, -65.5) | sling |

The count is **21**; positions and rotations are in `smg_spec.json` `sockets.gun`.

### 10.2 Magazine `SM_SMG01_Mag` (5)

`Mag` (origin = the well-entry centre when seated; +X forward, +Z up the insertion axis), `HandReload` (left palm on
the body), `Feed` (top centre of the lips), `Base` (floor plate centre, +X = outward normal), `CenterOfMass`.

**Gates:** S1 (exported sidecar = build values within 0.001 mm / 0.001 deg), B4 (sockets on their bones, `Muzzle` on
the bore within 0.5 mm / 0.05 deg).

---

## 11. Collision and physics

| Twin hull | Covers | Why split there |
|---|---|---|
| 00 | upper + lower receiver body, top rail | box-like |
| 01 | rear flip sight | a receiver hull reaching both sights would fill the 260 mm gap above the rail |
| 02 | front flip sight | same |
| 03 | fore-end: front receiver below the bore, lower rail | |
| 04 | barrel + muzzle device | thin; keeps the receiver's height out of it |
| 05 | grip + trigger guard | the raked grip would fill the guard bay |
| 06 | merged magazine (twin only) | straight: one hull |
| 07 | stock frame + buttpad (extended) | the skeleton's openings fill in its hull (acceptable: physics only) |

- Mag: 1 hull `UCX_SM_SMG01_Mag_LOD0_00` (straight mag; study 5.6).
- Method (AR-01, worked): dense surface samples <= 1 mm at LOD0, dilated 0.2 mm, neighbours overlap 3 mm, <= 32
  vertices. Gates C1 (build: 0 jittered 0.5 mm samples and 0 LOD vertices outside), C2 (Unreal: 0 of 300k), C3
  (counts 8 / 1).
- `PHYS_SMG01`: one body on `body` (boxes/capsules: receiver, grip, barrel, extended stock), mass 2.5 kg, CoM from part
  volumes x densities (polymer ~1.4 g/cm3 glass-filled, steel 7.85) scaled to the total. A dropped folded SK keeps the
  extended-state stock shapes (Q8 default); U7 reports a folded drop. In hand: NoCollision / QueryOnly.

---

## 12. Magazine: straight insertion and the fit gates (adapted M1-M9)

### 12.1 Construction

1. Built in W3 from the **shipped** `SM_SMG01` bytes (sha256 guard; the mag rebuilds when the gun is re-exported),
   but its fit geometry is already proven at form (W1 `form_magfit`) on the LOD0 parts, as the AR-01's R51 loop did.
2. The mag's outside comes from the sheet (both side views, the 3/4) for the visible part; the part inside the well
   is fitted to the well: lateral 0.3 mm per side, fore-aft 0.3 mm. No guide ribs (RP21: the ladder is recessed).
3. **Retention, real-pattern way:** the paddle's nose reaches through the catch window in the magwell's 4.0 rear wall
   into the mag's rear notch (Z -44.0 seated, engagement 1.5, notch depth 2.5); the seated stop is the nose on the
   notch's bearing face; above the seated mag there is a small **overtravel** to the well's top shelf (the real mag is
   pushed past the catch so it can snap in). Pressed (-11 deg) the nose moves 3.9 mm rearward.

### 12.2 Gates (exported bytes; the mag placed from the exported sidecar `Mag`)

| # | Gate | Threshold |
|---|---|---|
| M1 | Seated, co-visible gun/mag LOD pairs (k, k) and (k, k+-1) | 0 intersecting triangles (LOD0-1); LOD2-3 depth < 1 px at the switch distance |
| M2 | Seat: catch nose to the notch bearing face; overtravel to the top shelf; visible seam at the well's lower edge (side + front views) | 0.0-0.3 mm; 1.0-2.0 mm; seam <= 0.6 mm |
| M3 | Lateral per side; fore-aft; catch engagement depth | 0.2-0.6 mm; 0.2-0.6 mm; >= 1.5 mm |
| M4 | Insert path `MagInsertStart` -> `Mag` in 0.5 mm steps, catch at rest | 0 intersections except the declared allowance: the catch nose riding the mag's rear face/ramp, <= engagement depth + 0.3 mm, only in the catch zone (the last engagement + overtravel mm); reported per step |
| M4b | The same path with `mag_release` at its release angle | **0 intersections** (proves the cam geometry is clean, not just tolerated) |
| M5 | Removal path (reverse), `mag_release` at its release angle | 0 intersections |
| M5b (info) | Removal with the catch at rest | reported; expected to collide (proves the catch retains) |
| M6 | `Mag`, `MagInsertStart` (gun) and `Mag` (mag) from the exported sidecars vs the fit | <= 0.001 mm, <= 0.001 deg |
| M7 | Gun bytes = the shipped sha256 | equal |
| M8 (info) | The Reload clip's drop and re-entry of the `magazine` bone below `MagInsertStart` | reported (0 expected) |
| M9 (Unreal) | Mag at `Mag` in engine; composed sockets; seated fit on read-back geometry | <= 0.001 cm; 0 intersections |
| M10 | Twin's merged mag = `SM_SMG01_Mag` at every LOD (AR-01 stage-7 fix) | equal triangles; vertices within 0.001 mm |
| F5 | Catch sweep 0..release with the mag seated (form_magfit) | 0 intersections except the nose leaving the notch |

---

## 13. Clips and notifies

- All clips start and end at rest unless stated.
- Rest = the bind pose = the sheet pose, which puts the selector at SEMI (spec R10).
- **Every clip that moves the bolt holds the selector at Auto from its first frame to its last** (AR-01 lesson). Frame counts are starting values; the rig stage
records the final keys and the sidecar carries the notifies (study 4.6; the harness adds them, U9).

| Clip | fps / frames | Motion | Notifies |
|---|---|---|---|
| `A_SMG01_Fire` | 60 / 0-6 | trigger pull 0 -> +13 deg; bolt 0 -> full travel -> 0 (blowback, ~600 rpm *rough* from the real pattern); the charging handle **does not move** (non-reciprocating) | `Fire` f1, `ShellEject` at the bolt's rear stop, `TriggerReset` last |
| `A_SMG01_Charge` | 30 / 0-22 | charging handle back to full travel pushing the bolt (pusher-lug contact), release: both forward | `ChargeRear`, `BoltRelease` |
| `A_SMG01_Reload` | 30 / 0-55 | paddle 0 -> -11 deg (nose out of the notch); `magazine` straight down out of the well along -Z, drop, new mag up the path (lerp), paddle back, the nose snaps into the notch | `MagRelease`, `MagOut`, `MagDrop`, `MagIn` |
| `A_SMG01_ReloadEmpty` | 30 / 0-80 | **starts with the bolt held open** by the internal hold-open (not modelled, no `bolt_catch` bone, R24) and the charging handle **forward** (`starts_at_rest: false`); Reload, then the charging handle pulled fully back (75) and released: the hold-open lets go and the bolt runs forward | `MagRelease`, `MagOut`, `MagDrop`, `MagIn`, `BoltRelease` |
| `A_SMG01_Selector` | 30 / 0-30 | SEMI (bind) -> SAFE -> SEMI -> AUTO -> SEMI (Y: 0, -63.4, 0, +45, 0 deg); starts and ends at the bind pose; the detents are a design call (Q16) | - |
| `A_SMG01_StockFold` | 30 / 0-24 | button pressed (latch bolt in 2.0, its neck spans the end-block lug); stock 0 -> +180 deg about Z (to the right); the stock lug's barb snaps under the port catch's rear lip; button released | `StockUnlock` f1-2, `StockLocked` at the end |
| `A_SMG01_StockUnfold` | 30 / 0-24 | the stock pulled outboard (the lug flexes over the lip), 180 -> 0 deg; the latch bolt rides over the end-block lug and snaps into its bore | `StockUnlock`, `StockLocked` |
| `A_SMG01_SightFlip` (Q5) | 30 / 0-20 | both sights up -> folded -> up | - |

- Bone compression `DefaultRecorderBoneCompression` (rigid parts; ACL cracked them on the fan), U9 <= 0.1 mm.
- Clips read back within 0.01 mm / 0.01 deg (rig_export); B3 coverage: every clip value inside its swept range.

---

## 14. Gate list (copy into `smg_spec.json` `gates`; thresholds from GUN_BUILDING_STUDY 7 unless noted)

### 14.1 Look (L)

| # | Gate | Threshold |
|---|---|---|
| L1 | Blockout IoU vs the traced panels | sides >= 0.95; top >= 0.92 on X >= 245 only (the sheet draws the stock obliquely, spec R18); **< 0.90 = stop and change the method** |
| L2 | Form IoU | authority sides >= 0.96 (the LEFT panel for left-handed features, the RIGHT for the port side; both sides are authority views here: the labels are consistent), top >= 0.93 on X >= 245 (the stock is checked by its widths, 29.5 / 58 +-1 mm); **3/4 FRONT (LEFT), camera solved: IoU >= 0.93, contour P95 <= 3 px** (the AR-01's documented-exception rule applies only to regions the study proves are 3/4-panel contradictions); per part IoU >= 0.95 for masks >= 400 px, thin parts P95 <= 1 px / max <= 2 px |
| L3 | Contour + features | side P95 <= 2 sheet px; features (vents, port, knob, selector hub, the paddle's pin head and top/bottom Z (its fore-aft faces are a declared deviation), every drawn fastener head (9 LEFT + 10 RIGHT rows in `pins_fasteners`), the oblong recess, the seam boss, the TOP end-block frame, sight posts, aperture, hinge knuckle, stock openings and holes, buttpad serration ends, rail ends) <= 2 sheet px; angles <= 1 deg |
| L4 | Dimensions | measured vs spec <= 0.05 mm (build-bug check) |
| L5 | Colour | crop-matched hue, R/B and median luma within the stone S16 tolerances, physical light (AR-01 method) |
| L6 | Fake checklist G1-G20 | 0 major (the polymer tells first: G8, G19, G15) |
| L7 | Blind + realism | design judge >= 12 pairs: **reported, not blocking** (user bar); realism: 2 judges, 4 views (FP 35 cm, ADS, TP 3 m, hero 3/4) + a folded-stock hero: at most 1 single-judge fake call |
| L8 (early) | Per-part early realism review at form (rough look) | per part group (receiver + rails, sights, grip + lower, stock + hinge, front end, magazine): 2 realism judges with real-pattern photos beside. **PASS** per group = at most 1 single-judge fake call; 2 single-judge calls = fix and re-judge once; **decisive fail** = both judges call the same group fake (or the re-judge fails): stop and show the user |

### 14.2 Blender (B, G, H, UD)

| # | Gate | Threshold |
|---|---|---|
| B1 | Skeleton | `root` identity; the 11 (12) names; every bone deforms but `magazine`; rest = root's; parents = `body` |
| B2 | Rigid skin | `qa_skeletal(max_influences=1)` |
| B3 | Motion sweeps (LOD0, LOD1) | bolt, charging handle (+ pusher-lug contact 0.0-0.05 mm during the push, no penetration), trigger, selector (full arc, both levers), paddle, **stock 0..fold** (step min(1 deg, 0.10 / r_max) ~0.023 deg at r 250 mm, or 0.25 deg steps that each prove a min distance >= r_max x 0.25 deg / 2 ~0.55 mm outside the latch zone; the fine step inside it), both sights 0..folded: 0 intersections and each joint inside its 3.7 row (trigger 0..+13, paddle 0..-11, handle lock about the slide's roll pin); declared allowances only: the port catch's lip over the stock lug's barb (<= 1.5 mm in the last <= 3 deg of the fold and the first of the unfold: the snap, polymer flex) and the sights' detents (<= 0.3 mm in the last <= 2 deg); LOD2-3 < 1 px at the switch distance |
| B3b | Folded state | folded stock: 0 intersections with the selector, knob, port, grip; the casing throw cone (ShellEject +X, 15 deg half-angle, 150 mm) clear of it (real-pattern behaviour; reported if the real pattern differs) |
| B4 / B4b / B4c | Sockets + sight picture | section 6 and 10 |
| B5 | Sidecar | <= 0.001 mm / 0.001 deg |
| B6 / B6a | Twin `qa_check` / joined-twin topology from form | pass; 0 coincident, 0 non-manifold, 0 UV0 overlaps once UVs exist |
| B7 | Geometry | closed manifold parts; flat-face deviation < 1 deg; facet <= 7.5 deg at LOD0; bevel widths = spec +-0.05 mm and >= the visibility minimum |
| B8 | Budgets / LOD-pop | section 7, 8 |
| B9 | Textures | section 9 (classes within +-15 % P5-median, fill, metallic 0/1, BC ranges) |
| B10 | Names | tokenised gun deny list (no `ump`, `hk`, `heckler`, `koch`...) on every name and the shipped text; `qa_check` deny list |
| B11 | Bounds extension | every LOD vertex at every clip frame and both stock states inside the bind AABB + extension; the folded envelope from every stock-bone part (the latch housing and button fold furthest out) |
| G5 | Contact | 0 static intersections LOD0-1; butt gaps >= 0.01 mm; LOD2-3 < 1 px |
| H1 early (W1) | Hand fit, first look | **PASS = trigger reach <= 80 mm and grip girth <= real polymer SMG grips + 10 %**; `Grip` depth from the fit body's palm (within 1 mm); `SupportHand` on the magwell reachable (<= 1.5 mm); length of pull (409.4 vs real 350-370) and cheek-weld eye height vs the sight line (feeds B4b) reported. A FAIL does not stop the build: it puts Q1 to the user with the numbers (the sheet's reach 90.5 is expected to fail) |
| H1 full (W3) | Posed hand fit on `MH_PlayerDefault` | study 7.2 H1 numbers; 0 hand-gun intersections at rest and at clip extremes **incl. stock folded and mag out**; records `hand_offset` |
| **UD1** (W1 on, every LOD) | Unreal's degenerate rule | `gunlib.tspace.unreal_drops(ob)` = **0** on every part object (after `bl.finish`) at LOD0-3, on the joined twin and on each SK LOD mesh; min triangle area >= **0.01 mm2** (2x margin) |
| **UD2** (W1 on) | Micro strips / needles | 0 edges < 0.05 mm; 0 triangles with height < 0.02 mm over their longest edge; 0 bevel strips < 0.1 mm wide (generator report) |
| **UD3** (W2 on) | Zero tangents | `tspace.collapsed(me, "UV0", unreal=True)` = 0 on every export mesh LOD0-3 (SK and twin, mag); `float32_zero_corners` = 0; `edge_on_corners` = 0 (conservative detectors; Unreal's import at U10 is the authority) |
| **UD4** (W2 on) | Lightmap UV | authored UV1 inside 0..1, 0 overlap at 64 and 128 px with 2 px padding on every LOD (Q6 default) |
| **F1** (W1 on; craft study) | Selector sweep | swept minimum >= 0.10 mm |
| **F2** | Folded length | 423.6 +-3 mm (the real 450 is reported) |
| **F3** | Stock folded | the stock lug's barb under the port catch's rear lip: engagement >= 1.0 mm in X (spec 1.3), barb-to-lip gap 0.2-0.4 in Y; 0 intersections seated; swept minimum >= 0.10 mm outside the declared snap allowance |
| **F4** | Charging handle (75 mm, then the 15 deg lock about the slide's roll pin; the slide does not rotate) | the neck clear of the slot and notch by 0.15-0.40 mm; the outer arm >= 0.10 mm off the wall at every frame (every arm point moves outward) |
| **F6** | Stock latch (extended) | the bolt's full diameter >= 1.5 mm into the end-block lug's bore released (spec 2.0); 0 with the button pressed 2.0; the fold sweep with the button pressed clears the lug's exit slot by >= 0.10 |
| **F7** | Charging-handle lock | at 15 deg the neck seated in the rear notch >= 2.0 mm above the slot top (spec 2.4 at the wall's inner face); knob rise 5.7 |
| **F5** | Magazine catch, bolt | catch sweep with the mag seated; the bolt's thumb recess visible in the port at rest |

### 14.3 Unreal (U, W5; fresh processes on exact bytes)

U1 skeleton dump; U2 procedural bolt -X and selector about Y; **U2b** `ABP_Gun_LongGun` on `SK_AR01_Skeleton` drives
`SK_SMG01` and `SK_AR01` through Compatible Skeletons with normalized inputs mapped by each sidecar's
`abp_angle_table`: bolts within 0.01 cm, both triggers pull their lower end rearward, the selector detent index reaches
each gun's SAFE / SEMI / AUTO, each release moves its own release way; no error on the missing bones (first proof of
the line; check fix C5); U3 sockets on bones within 0.001 cm; U4 FP/WSR full component set (gun, mag); U5 LOD counts,
**triangles equal Blender/FBX/Unreal (expected PASS this time, thanks to UD1)**, screen sizes, bounds containing every
clip vertex incl. both stock states, and whether the extension enters the LOD radius (records it); U6 mag composition;
U7 physics (extended drop + folded drop reported); U8 lightmap per Q6; U9 clips + notifies; **U10 0 asset warnings
(expected PASS: UD1-UD3)**; U11 if a player MetaHuman exists in the verification project (else reported); U12 top-mip
residency at hip and ADS; C2 hulls; M9.

### 14.4 Pack (P, W6)

P1 default capture = shipped BC (p99.9 <= 2 levels; BC7 fallback for the polymer), P2 recolour path + 10-colour
stress (+ tan/OD/FDE), P3 mip drift <= 2 %, P4 additions only.

---

## 15. Staged build: separate fresh workflows, each from a commit

Every workflow: starts from a named commit on the gun branch; reads `smg_spec.json` + this plan; holds asset lock
`SMG01` (`py -3 -B Scripts/pipeline/lock.py claim SMG01 --agent claude --blend Assets/Guns/SMG01.blend`), and
`GunLib` while it edits `Scripts/guns/gunlib/`; one Blender process per step; never leaves a process running; writes
`WorkFiles/guns/smg/gates/<stage>.json` with `status` and `failed`; ends with a commit (heavy scratch stays in
`scratch/`, gitignored). Stop and show the user on a decisive fail (L1 < 0.90, an early-realism round both judges
fail, a design conflict R4/R10/R18).

| Workflow | Starts from | Does | Gate file(s) | Ends with |
|---|---|---|---|---|
| **W0 plan + spec** (merged 2026-10-09: `smg_spec.json` S0 PASS, `SMG_STUDY.md`, `SMG_DESIGN_SHEET.png`) | `9c1df845` | measurement + traces (other agent), real-pattern study with photos (other agent), this plan; `smg_spec.json` merged from all three; S0 validator | spec S0: 0 missing fields, 0 unresolved *rough* values that a stage needs | commit "SMG01 study, spec and plan" |
| **W1 form** | W0 commit | **W1a** gunlib extraction (lock GunLib, bump `LIB_VERSION` to 0.2.0): `parts/rail_1913.py`, `parts/mag_box.py`, `parts/hinge.py`, `parts/sights_flip.py`, `parts/hardware.py`, `WorkFiles/guns/gunlib/gun_standard.json` + `standard.py`, gun-agnostic drivers promoted from `Scripts/guns/rifle/` (b3, b4, b6a, measure, magfit-check, viewgates, g5_lods, rig_verify, mag_fit) with a per-gun config; **AR-01 regression**: its stage-2/4/5 gates re-run with the promoted code reproduce the committed values, and the AR-01 export sha256s stay unchanged. **W1b** `Scripts/guns/smg/` (`build_smg.py` staged, lock asserted; `smg_parts.py`; `parts/`; `run_smg.sh` = the AR-01 `run_rifle.sh` chain): blockout (L1, B4 at blockout) -> form (all R1-R20, internals, both stock states, sights up/down) -> L2-L4, B3 (incl. stock fold), B3b, B4/B4b/B4c, B6a, B7, B8, G5, B10, **UD1-UD2**, H1 early, form_magfit (M1-M5b, F5 on LOD0 parts), grey renders, **L8 early realism per part group** | `gates/form.json`, `gates/form_magfit.json`, `gates/gunlib_regression.json` | commit; `scratch/SMG01_form_stage.blend` kept |
| **W2 surface** | W1 commit | `run_game.sh --from uv` equivalent up to paint: UV (packer by class, slot tiles), bakes (**margin 0**, **mag AO alone**), paint (same-side edge masks, analytic wear, polymer polish), Masks, Detail16 + recolour pre-check through the pack's derive step; renders only from the baked maps; L5 | `gates/uv_bake_paint.json` (qa_check, B9, fill, densities, overlaps, mirrored 0, L5, wear audits, **UD1 re-run, UD3, UD4**) | commit |
| **W3 rig + mag** | W2 commit | LOD1-3 (same generators), twin (hulls, sockets, UV tiles), LOD-pop on both stock states -> screen sizes on engine-equivalent radii, S1/S2 at LOD0-3, G5 LOD2-3; rig (`gunlib.rig`), 7 (8) clips, bounds extension (B11), `export_skeletal_set` + twin export; fresh-process verify (B1-B5, clips read back, sha256); `SM_SMG01_Mag` from the shipped twin bytes (sha guard), mag LODs, hull, sockets, derived sizes, M1-M10; H1 full; look check from exported bytes | `gates/game.json`, `gates/rig_export.json`, `gates/mag.json` | commit with `Exports/Guns/SMG01/` |
| **W4 review + fix** | W3 commit | review sets from exported bytes under the physical light: L6 craft review, L7 blind (reported), 2 realism judges; tech review; `review/FIX_LOG.md`; every fix in the generators, then the full chain from nothing (`run_smg.sh` -> `run_game.sh` -> `run_rig_mag.sh`) | `gates/review_fixes.json` (all stage files pass + the review items) | commit |
| **W5 Unreal** | W4 commit | harness copied from `WorkFiles/guns/rifle/UnrealCheck/` into `WorkFiles/guns/smg/UnrealCheck/` (`sm_common`, passes A, A2, B, C, D, E, F), content `/Game/GunCheck/SMG01_<run>`; machine guard; sha256 at start and end; U1-U12, U2b, C2, M9 | `UnrealCheck/verification_summary.json` | commit |
| **W6 finish** | W5 commit | pack materials under `PackMaterials` (`np_lock.py claim`, `run_build.sh` from a short-path mirror root): spec items `SMG01`, `SMG01_Static`, `SMG01_Mag`, recolour group, `maps/derive_constants_smg01.py`, P1-P4; `Exports/Guns/SMG01/README.md` + `MATERIALS_README.md` (frames, sockets, straight reload path, stock states and bounds, FP pattern, collision in hand, CoM, colour, measured Unreal notes); `showcase/CompactSMG_SM01/` via `studio.py` + one `ASSET_LIST.md` row (re-read just before editing; the AR-01 row went in on main directly because another chat had uncommitted edits there); release lock `SMG01` | `gates/pack_materials.json`, `gates/docs_showcase.json` | commit; ask before merge/push |

The run chain mirrors the AR-01's: `Scripts/guns/smg/run_smg.sh` (stages 1-2) -> `run_game.sh` (3-4) ->
`run_rig_mag.sh` (5-6), each step resumable with `--from`, logs in `WorkFiles/guns/smg/scratch/logs/`.

---

## 16. Export and Unreal notes (deltas from the AR-01 only)

- Paths: `Assets/Guns/SMG01.blend`, `Assets/Guns/SMG01_Mag.blend`; `Exports/Guns/SMG01/` (`SK_SMG01*.fbx`,
  `SK_SMG01.skeletal.json`, `A_SMG01_*.fbx`, `SM_SMG01.fbx` + `.sockets.json`, `SM_SMG01_Mag.fbx` + `.sockets.json`,
  `Physics/`, `Textures/` (+ `Recolour/`), READMEs); `Renders/Guns/SMG01/`; `WorkFiles/guns/smg/`.
- The skeletal sidecar's `gun` block: `class: long_gun` (SMG is in the long-gun class for the ABP), `compatible_with:
  SK_AR01_Skeleton`, `grip_axis_deg`, `rail_slots` (top, bottom, occupied by the sights), `muzzle_class`,
  `mag_family: SMG01 straight 25`, `stock_states` (extended 0, folded angle), `abp_angle_table` (trigger, selector
  detents, release, bolt), `texel_classes`, `hand_offset`.
- The sidecar's `materials` block comes from the spec slot table (Metal -> `M_Steel_Master`), not a literal.
- Static import: if Q6 keeps the default, the importer sets Generate Lightmap UVs **off** for `SM_SMG01` and
  `SM_SMG01_Mag` and U8 reads the authored channel; the README states it.
- FBX absolute source path (AR-01 N1) is pipeline-wide: not fixed here; reported again.

---

## 17. Risks

| Risk | Mitigation |
|---|---|
| Sheet self-contradictions on small parts (right-side slot R18; knob ahead/behind its slot R4; red dots) | rulings up front; design-level conflicts asked once (Q1), not discovered in review |
| Fold side and fold angle not visible in Sheet A | Decided: right, 180 deg about a right-rear corner axle (spec R19/R25). A rigid fold about an axle inside the drawn outline would put the folded pad inside the receiver, so the knuckles stand ~5 mm proud in TOP (Q6). B3/B3b/F3 gate both states |
| Black polymer reads as CG plastic (the realism judges' first target) | P-round edges by process, draft and parting lines, stipple as normal detail with a geometry border, polish-only wear, physical light in every review; L8 early per part |
| Texture sets go to 4096 (both) | expected (2.3x lesson); memory ~ +36 MB per 4096 set; LOD bias for TP documented |
| Stock fold sweep is slow at the study's fine step | the coarse-step-with-proof method (B3) |
| The bounds extension inflates the SK's LOD radius | sizes from the final engine bounds; U5 records the effect |
| Folded-stock physics | Q8 default + U7 report |
| Flip sights obstruct an optic | B4c clearance |
| Shared ABP fails (U2b) | the bone-axis contract (2.2) plus the normalized inputs and per-gun angle tables are the fix point; Template ABP for bone-free logic remains the fallback (study 5.2) |
| The paddle is built 3.9 mm behind the drawn lever (the magwell wall needs the space) | declared deviation in the spec; L3 gates the pin head and the paddle's Z range; L8 judges the look |
| gunlib extraction changes the AR-01 | W1a regression gate: AR-01 gate values and export sha256 unchanged |
| Unreal or the materials lock busy | wait and retry; never force a live holder |
| Repeat of the U5/U10 failure | UD1-UD3 from form; no export-time conditioning |

---

## 18. Open questions (only the user decides; each has a default the build follows)

This is the merged list (spec `open_questions`; `SMG_STUDY.md` section 9; Q16-Q17 from the check, section 12). The W0 merge closed three of the plan's
earlier questions:
- old Q1: the right-side slot is a vent; it is not a mirror;
- old Q2: the stock folds right;
- old Q7: no bolt catch.

| # | Question | Default |
|---|---|---|
| Q1 | Scale 690 (the sheet's chunky middle: reach 90.5, height 338, width 68.8, folded 424) or ~625? | 690; rescale offered only if H1 fails (H1 now has numbers: reach <= 80, girth <= real + 10 %) |
| Q2 | Hidden barrel 156 mm (sheet feed geometry) instead of the real 200? | follow the sheet |
| Q3 | Charging handle: knob as drawn, a 75 mm slot behind it, the drawn slots as vents? | yes |
| Q4 | Selector index groove painted white? | plain groove, no paint |
| Q5 | The folded top strut crosses the port: accept (folded = carry) or raise the strut? | accept |
| Q6 | Hinge axle at the right-rear corner (knuckles ~5 mm proud of the right side in TOP) so the stock folds flat? | corner axle |
| Q7 | Mass 2.5 kg or 2.26 kg? | 2.5 |
| Q8 | Magazine thickness 29 mm? | 29; 3/4 gate at blockout |
| Q9 | Standard 10.01 rail pitch in the drawn toothed zone (21 teeth for 19 drawn)? | yes |
| Q10 | Keep the merged magazine in `SM_SMG01` | yes (AR-01 precedent) |
| Q11 | Also ship a folded static `SM_SMG01_Folded` | no (the SK shows folded) |
| Q12 | Ship `A_SMG01_SightFlip` as an 8th clip | yes |
| Q13 | Lightmap UV: authored UV1, Generate off on the statics | yes, gated UD4 + U8 |
| Q14 | Folded-stock physics: one body with the extended shapes | yes; U7 reports a folded drop |
| Q15 | Fab design changes (craft list of 10) | listed in the spec, not applied |
| Q16 | Selector detents: the design call (the sheet pose = SEMI, SAFE 45 deg below forward, AUTO 45 deg further rearward) or the real figures (SAFE ~25 deg below forward, SEMI/AUTO ~15-20 deg below rearward, so the drawn lever would sit in no detent)? | design call |
| Q17 | Folded-stock retention: a moulded lug on the rear upright's right face (3.7 mm beyond the pad's side, not drawn) or a joggled stock arm (changes the TOP view)? | the lug |

---

## 19. Sources checked for this plan

- Real-pattern figures: https://en.wikipedia.org/wiki/Heckler_%26_Koch_UMP (690 / 450 mm, 200 mm barrel, 2.5 kg for
  the .45 version, 25-round straight magazine, the bolt locks open after the last round with a left-side release,
  aperture rear sight with a ringed front post, four rail positions). The fold side is not stated there; the
  real-pattern study decides R10 from photos.
- Everything else comes from the repo: GUN_BUILDING_STUDY.md, the AR-01 plan, report, spec, gates, scripts and
  shipped sidecar.
