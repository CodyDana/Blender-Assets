# Sniper Rifle SR-01 (SR01): study and decisions (2026-10-12, W0)

The W0 package for the SR01 build (`SK_SR01`, `SM_SR01`, `SM_SR01_Mag`, attachment `SM_Att_Scope_LongRange`):
- measurement: `MEASUREMENT_NOTES.md`, `sr01_measured.json`, `trace/`, `SR01_TRACE_OVERLAY.png`;
- craft: `CRAFT_STUDY.md`, `craft_parts.json`;
- plan: `SR01_BUILD_PLAN.md`, `sr01_interface.json`;
- the merged spec **`sr01_spec.json`** (S0 PASS) and **`SR01_DESIGN_SHEET.png`** (both bipod poses drawn).

Regenerate everything after any change (about 20 s, plain Python):

    py -3 -B WorkFiles/guns/sniper/tools/trace_reference.py
    py -3 -B WorkFiles/guns/sniper/tools/make_spec.py
    py -3 -B WorkFiles/guns/sniper/tools/design_sheet.py

**Which role wins:** the measurement on silhouette numbers; the craft study on small-part construction, finishes and
wear; the plan on frames, bones, sockets, slots, budgets, gates and stages. The spec carries every number.

Nothing was built and neither Blender nor Unreal was run. Lock `SR01` is held; `GunLib`, the SMG and rifle folders
and `QUEUE.md` were not touched.

## 1. Decisions on one screen

| Topic | Decision | Res. |
|---|---|---|
| Sides | **The labels are swapped.** The panel labelled LEFT is the gun's RIGHT (bolt handle, muzzle image-right); TOP: knob image-down = right; the 3/4 is from the front right. The tools call the side panels GR / GL | R1 |
| Scale | **1100 mm** overall (the study table's 1270 is an AWM-class figure; the brief asks for .308-class). Sheet anchors: 34 mm tube -> 1097, median of 8 anchors 1049 | R2 |
| Barrel, mass | **559 mm (22 in)**, breech X 505.5, crown 1064.5 inside the compensator; 5.9 kg without scope and mag, 7.5 kg ready | R3 |
| Bore axis | barrel top edge + scope tube (tilt <= 0.06 deg); height = the compensator centre line | R4 |
| **Bipod on the sheet** | **folded in every view, the 3/4 included**; the study's "deployed in the 3/4" is wrong. Folded authority = side views (+ the 3/4 as a second folded check); deployed = real pattern | R5 |
| Butt | fixed (no hinge drawn); "folding-style" is a look only | R6 |
| **Bipod mechanism** | tension-swivel folding pattern: legs on transverse pins at the drawn hub (X 719.6, Z -62.3, Y +-19.5), independent, detents 0 / +90; ext 0..76 in 19 mm notches; cant +-15; drawn knob = tension knob. Deployed bore height 268-344 mm. Every clearance computed (section 5) | R7 |
| Bolt | 3-lug, 60 deg, then 88 mm; the knob clears the scope by 29.9 mm over the cycle | R8, R9 |
| TOP widths | right edges 4-6 mm wide (floor shadow): widths = 2 x the left half; TOP inflates rounds 6-10 % | R10 |
| Magazine | straight 10-round box, vertical, 89.3 x 26.5, top Z -11, straight insertion | R11 |
| Mag release | forward-push paddle; built 3.4 mm behind the drawn edge (declared, < 2 px) so it can move | R12 |
| Grip | the sheet's ~27 deg rake wins over the brief's "vertical" | R13 |
| Rail | `rail_1913`, 15 slots, flat; rings on slots 2 and 12 | R14 |
| Scope | separate attachment `SM_Att_Scope_LongRange` (scope + rings), own `Sight` / `EyePoint` / lens slot; no `Sight` on the gun | R15 |
| Slots | gun 2 (Metal, Chassis with Metal From ORM) so the twin fits 3 tiles with the merged mag; held draws 10 | R16 |
| Riser | adjustable: `cheek_riser` -12.9..+12.0; eye point sits over it | R17 |
| Forend band | plain dovetail, the bipod's seat; no `Rail_Bottom` | R18 |
| Safety | 2-position tang rocker on the right (real pattern) | R19 |
| Muzzle device | linear compensator, bone `muzzle_device` | R20 |
| TOP feet | 76 mm wide as built vs ~60 drawn: declared | R21 |
| Cant folded | allowed (worst 7.7 mm) | R22 |

## 2. Scale ruling, with reasons

The user's brief: a plausible .308-class chassis rifle, measured on a sheet that resolves ~0.5 px/mm. The sheet
gives eight independent size anchors (`MEASUREMENT_NOTES.md` "Scale"). Each one translates into the overall length
at which that feature would be real size:
- scope tube 1097;
- eyepiece 1024-1122;
- objective bell 1098-1205;
- drawn rail pitch 1038 (AI sheets draw rails +6..10 % long: SMG +10 %);
- length of pull 999-1121;
- knob 887-1109;
- magazine 985-1084;
- compensator 914-1097.

**1100 mm** is the tube's figure rounded. It is inside every anchor's range except the rail and the magazine (both
slightly large on AI sheets), and inside the .308 chassis class (1050-1200). The barrel then measures exactly
22 in from the drawn port front to the crown inside the compensator, and the length of pull is 14.3 in. At the
study's 1270 the tube would be 39 mm and the barrel 37-41 mm thick: not plausible. **Q1** asks the user to confirm
(it also updates the study's Q15 row for SR01).

What 0.5 px/mm cannot measure: chamfers, pins, the safety, the magazine thickness, and the rail teeth beyond a
pitch estimate. These come from the real pattern (`CRAFT_STUDY.md` RP1-RP15). Hand-read seams are +-1 px = +-1.9 mm.

## 3. View agreement

- **GR vs mirrored GL (no fit):** IoU 0.968 (gun body 0.969, scope 0.989, folded bipod 0.918, magazine 0.935);
  boundary p90 2.2 mm. GR is the tie-breaker. GL contributes its own left-side features (the riser clamp lever, the
  QD-cup recess on the butt).
- **TOP vs side:** length within 0.4 %. The knob is drawn ~32 mm further back (GR wins X). The right edges carry
  the shadow bias; rounds read 6-10 % wide.
- **3/4:** the only source for the magazine thickness and ribs, the compensator exit, and the scope's front.
  **It shows the bipod folded.** It gets the camera-solved L2 gate at form, for the folded pose.

## 4. Part list (25 records in `sr01_spec.json` `parts`)

| Group | Parts (bone) | Slot |
|---|---|---|
| Chassis and stock | chassis (body: centre + forend + guard + well + dovetail), butt, pad_plate, butt_pad, grip (body); cheek_riser (cheek_riser) | Chassis |
| Action | receiver, rail (body); bolt + bolt_handle (bolt); safety (selector); trigger (trigger); mag_release (mag_release) | Metal |
| Barrel | barrel (body), muzzle_device (muzzle_device) | Metal |
| Magazine | magazine (`SM_SR01_Mag`, merged in the twin) | Mag |
| Bipod | bipod_mount (bipod); bipod_leg_l / _r (legs); bipod_ext_l / _r (ext) | Chassis / Metal |
| Hardware | pins_fasteners (body; count and place from the sheet only) | Metal |
| Scope attachment | scope_body, scope_rings, scope_lens (`SM_Att_Scope_LongRange`) | Scope body / lens |

**Internals modelled at form:**
- the bolt raceway over the full stroke, the lug recesses and the port opened to the stroke;
- the mag well walls, shelf and catch window; the paddle clevis and the magazine's catch notch;
- the riser post bores;
- the bipod hub yoke, the detent disks, the telescoping bores and the collar buttons.

## 5. The bipod (user requirement)

Folded, as on every view of the sheet (side views = authority):
- the legs point forward under the forend;
- the leg tops sit 0.2 mm under the clamp (hinge row);
- the feet sit 4.2 mm under the forend band and 2.0 mm apart.

Deploy = +90 deg about Y at the hub (each leg on its own pin), then extend. The clearances were swept in the spec
at 0.5 deg steps for ext 0 and 76:

| Obstacle | Minimum (mm) |
|---|---|
| clamp | 0.2 |
| forend | 13.0 |
| barrel | 29.8 |
| tension knob (in Y) | 2.8 |
| magazine | 206.7 |

Cant +-15: worst 7.7 folded, 32.4 deployed. Deployed ground at bore height 268 (ext 0) to 344 mm (ext 76).

Clips `A_SR01_BipodDeploy` and `A_SR01_BipodStow` (36 frames each, the legs moving independently, ext to the 38 mm
detent). The bounds extension covers Z -344.3 and |Y| 113.9. Gates F1-F5. Drawn in `SR01_DESIGN_SHEET.png`
panels 2 and 3.

## 6. Materials (summary; values in the spec)

- **Painted metal:** OD ceramic paint over aluminium (sheet 89/89/78 rendered, rough 0.55-0.70) wearing to a dark
  rim, then bare aluminium at the highest corners.
- **Steel:** phosphated steel (barrel, receiver, compensator, small parts) and polished bare steel (bolt, inner legs).
- **Anodized aluminium:** black (rail, bipod body and tubes, scope).
- **Rubber and polymer:** rubber pad, feet and eyecup; polymer grip and floorplate.

Rough-real finishes and a physical light rig from the first look (the SMG "flat clay" lesson).

## 7. Interface (summary)

- **Bones:** 13 (section 2.2 of the plan).
- **Sockets:** 20 gun, 5 mag, 5 scope; `Grip` = M (297.13, 0, -96.13). `SupportHand`, `SupportHandBipod`,
  `CenterOfMass` and `Holster` are provisional (H1 / W1 / W3).
- **Clips:** 7 + 1 optional; the bind pose = bolt closed, FIRE, bipod folded, ext 0, cant 0, riser at the sheet pose.
- **Budgets:** gun 35-45k (50k) without the scope; scope 6-10k; mag 2-3k.

## 8. What the sheet contradicts (and the handling)

1. The labels LEFT/RIGHT are swapped (R1).
2. The study says the 3/4 shows the bipod deployed; it shows it folded (R5).
3. The brief says "vertical pistol grip"; the sheet draws a ~27 deg rake (R13, sheet wins).
4. The brief says "short fixed bipod"; the user wants it to fold, and the drawn hub/knob/collar pattern is a
   folding bipod (R7).
5. The brief says "skeleton/folding-style butt"; no fold mechanism is drawn (R6, Q4).
6. TOP vs GR: knob X (R9); feet width (R21); right-edge shadow (R10).
7. The drawn mag release touches the magazine (R12).
8. The drawn rail pitch is 10.6 mm (R14).

## 9. Open questions (each has a default the build follows)

| # | Question | Default |
|---|---|---|
| Q1 | Scale 1100 mm (.308 class, sheet-anchored) instead of the study's 1270 (AWM class)? | 1100, 22 in barrel, 5.9 kg |
| Q2 | Deployed legs straight down and parallel (real tension-swivel pattern) or splayed? | straight down |
| Q3 | Keep the sheet's chunky heavy barrel (35 -> 32 mm) and 36 mm compensator? | yes (silhouette authority) |
| Q4 | Butt fixed (nothing folding is drawn) or add a side-folding hinge? | fixed |
| Q5 | A second static twin with the bipod deployed, for set dressing? | no |
| Q6 | Scope lens opaque glossy now (study Q19)? | yes |

**Status 2026-10-13 (W1 start): Q1-Q6 ACCEPTED at the defaults** (the user said to continue with the defaults):
1100 mm / 22 in / 5.9 kg; deployed legs straight down; thick barrel + 36 mm device kept; butt fixed; no deployed-bipod
static twin; opaque glossy lens. New user rule the same day: generic markings (safety letters / pictograms, rail
numbers) are allowed, never a real maker / model name or logo (applies from W2).

## 10. Fab-original change list (not applied)

`CRAFT_STUDY.md` section 7: stepped side pockets, lozenge forend slots, a scalloped riser, a reversed butt cut-out,
a hex grip texture, a 4-slot compensator, cleated feet. Nothing buyer-facing names a real pattern or maker.
Deny-list check: every planned asset, material, texture, bone, socket and clip name passes the tokenised gun deny
list (`gunlib.qa_gun`); its negative tests (`SM_AWM01`, `T_Barrett_BC`, `SM_MLok_Slot`) hit as they should.

## 11. Risks

The scale ruling (Q1); the deployed pose has no drawn reference (realism judges on a deployed hero, Q2); the bipod
sweep cost (coarse-step proof); the declared paddle shift; no real photos gathered yet (unattended run: W1 opens
with the photo pass); the gunlib proposals (P1 fallback: a static riser rather than a dummy bone).
