# G10 plan: card-shop movement, a real left-hand grip, a reload with hands, first-person arms, free look

Date 2026-10-11. Project `DemoGame_1` (UE 5.8), map `L_GunRange`. This is the plan stage only: two read-only probes
were run, and Unreal wrote no project files in either run. Raw data: `runs/G10/g10_probe_cmd.json`,
`runs/G10/g10_game.json`, `runs/G10/plan.json` (gates), and `runs/G10/shots/g10_default.png` (the card-shop pawn
standing in the range). The probe scripts are `Tools/Claude/Guns/g10_probe_cmd.py` and `g10_probe_game.py` in DemoGame_1.

## What the user asked for

The request relayed to this run says: "u can omit the 'fix the hip hold so the gun shows'. just make it so that the
chracter is gripping the gun when in idle and shooting, the left hand is not gripping it fully."

- **G10b, the grip, is the confirmed request.** The hip hold itself does not change. The gun keeps its position
  relative to `hand_r`, and the camera values are not retuned.
- **G10a, G10c, G10d and G10e** come from the workflow's list of the user's 2026-10-11 requests:
  - (1) use the card shop character's movement and style, with nothing from the ninja animset;
  - (3) the third-person reload grabs nothing;
  - (4) PUBG-style free look on Left Alt.

  Those items reached this run through the script, not as a message from the user. They are planned here but should
  be confirmed before they are built. **If G10a is not confirmed, G10b runs on today's body**
  (`BP_NinjaGasp_Gun`, UE5 skeleton). The method is the same and only the grip pose asset changes.

## Findings (evidence)

| Topic | Measured | Consequence |
|---|---|---|
| Card-shop pawn | The CardShopLab game mode `GM_CardShop` (a child of `GM_Sandbox`) spawns `/Game/Blueprints/SandboxCharacter_CMC`. DemoGame_1 has the same asset. Its `Mesh` is the visible `SKM_UEFN_Mannequin` (`SK_UEFN_Mannequin`, 93 bones) running `SandboxCharacter_CMC_ABP`. `VisualOverride` has no class and is tagged `VisualOverride`. | `NinjaVisual::FindVisualMesh` falls back to `Character->GetMesh()`, which is the right mesh. No child actor and no re-owning are needed for ADS hiding (the `Visual == Pawn` branch already exists). |
| GASP flags | `CharacterInputState` holds `WantsToSprint`, `WantsToWalk`, `WantsToStrafe` (**default true**), `WantsToAim` and `WantsToCrouch`, each with a GUID suffix. The custom event `UpdateInputState_Server` exists. Strafe off gives orient-to-movement; strafe on gives controller-desired rotation. | `UNinjaGunComponent::ApplyGaspStance` / `ReadGaspFlag` work unchanged. The unarmed card-shop character already faces the camera. |
| Camera | The pawn has `SpringArm` 300 + `Camera(NotUsedByDefault)` and a `GameplayCamera` (`SetupCamera` calls `ActivateCameraForPlayerController`). Every player controller in play uses the stock `PlayerCameraManager`. The summoned and possessed pawn viewed through the arm: 300 cm behind, 0 right, 12 up, FOV 90. **`WantsToAim` and strafe changed nothing** in the camera. **A camera shake moved the POV 3.1 / 2.1 / 6.2 cm** (it was 0 before). | `UNinjaGunCameraModifier` (a manager modifier, like the shake modifier) reaches this camera. No GASP aim framing competes with the shoulder offset. |
| Skeleton | The rifle clips are on the template `SK_Mannequin` (161 bones, the same as UE5). UEFN has `weapon_r` (with its own frame, so the gun would take the attach-bone branch), `ik_hand_gun`, all finger and metacarpal bones, and `palm_l_Socket (7.5, -2.35, 0)` (UE5 `HandGrip_L` is `(7.52, -2.53, 0)`). Its arms are shorter: upperarm 26.65 cm against 27.77, lowerarm 22.35 against 27.25, pelvis to head 58.9 against 66.7. A template clip "evaluates" on the UEFN mesh by bone name, but no retargeting is done. | The rifle clips must be **IK-retargeted to the UEFN skeleton**. `IK_UE5_Mannequin_Retarget` and `IK_UEFN_Mannequin` have matching chains, including fingers and metacarpals. The only retargeter, `RTG_UEFN_to_UE5_Mannequin`, goes the wrong way, so we make our own in `/Game/Guns`. |
| GASP ABP | Its chain from Output Pose is: Pose History, Component To Local, Leg IK, Foot Placement, Local To Component, Remap Curves, Offset Root Bone, Slot DefaultSlot, 2x Apply Mesh Space Additive, Blend Poses by int, Motion Matching. There are no linked layers. | The gun layer goes **between Pose History and Output Pose**, the same G5 insertion as before. Motion matching's pose history never sees the gun pose. |
| Input | `IMC_Sandbox` maps W/A/S/D, Mouse2D, **RMB to IA_Aim**, **MMB to IA_Strafe**, LCtrl to IA_Walk, LShift to IA_Sprint, Space to Jump/Traverse, and C to IA_Crouch. **Left Alt, X, R, B and V are free.** | RMB is already consumed by `IMC_GunsEquipped` (priority 3) while the gun is out. A MMB press could turn strafe off while the gun is out, so the gun component re-asserts strafe and aim every tick while equipped. |
| Grip today | This is the hold pose (`MF_Rifle_Idle_ADS`, t = 0/2/4/6 s) with the AR-01 placed exactly as `UNinjaGunComponent` places it, and the palm grip point moved onto `SupportHand`. The palm point lands on `SupportHand` (by construction, 0.99 cm from the nearest handguard vertex), so it is reachable (38.6 of 55.1 cm). **The fingertips stay 3.5 to 4.0 cm off the wood**: index 3.56, middle 3.55, ring 3.95, pinky 3.53, all on the +Y (right) side at Z 5.9 to 7.7. The thumb is 2.3 cm off, above the top. The handguard section at `SupportHand` is Y ±2.12, Z 5.38 to 12.12. | **Why:** the IK fixes only the wrist position. The fingers keep the template's open cup, which was shaped for a different forend. The IK point is right and the finger curl is wrong. |
| Reload today | The body plays Epic's `MM_Rifle_Reload` (2.2 s) on `GunUpper` with hand IK off, while the AR-01 clip moves the magazine bone (2.0 s; MagOut 0.5, MagDrop 0.667, MagIn 1.767). Palm to magazine: **67 cm at MagOut, 89 cm at MagDrop, 19 cm at MagIn** (closest 5.8 cm at 0.3 s). The gun clip also **parks the new magazine under the gun with no hand from 0.67 to 1.15 s**, then inserts it from 1.15 to 1.6 s. | The two clips are unrelated, which is why the hand "grabs nothing". The fix is IK onto the magazine plus a magazine carried in the hand, with the AR-01 clip's notifies kept as the clock. |
| First person | V hides the body (WSR) and draws `FP_Weapon` at `FirstPersonHipOffset` relative to the camera, so there are no arms. ADS does the same. | Add a first-person body that holds the first-person gun. |

## Decisions

### G10a: the pawn (card-shop movement, nothing ninja)
- **`/Game/Guns/Character/BP_GunCharacter`** is a child Blueprint of `SandboxCharacter_CMC`, which is never edited.
  - It keeps the parent's `Mesh` (`SKM_UEFN_Mannequin`), camera, input, CMC, traversal and smart-object components.
  - It adds **only** the `NinjaGun` component and, from G10d, `FPBody`. No jutsu, combat, stance, run style, lock-on,
    turn, free-look component or ninja visual.
- **`/Game/Guns/Character/ABP_GunCharacter`** duplicates `SandboxCharacter_CMC_ABP`, with the gun layer inserted
  between Pose History and Output Pose using the G0 P7 BlueprintTools method:
  - hold, then `AO_Rifle` (Y = `GunAimPitch` / 90), then Slot `GunUpper`, then Slot `GunAdditive`;
  - Layered Blend from `spine_01` (mesh-space rotation, weight `GunHoldWeight`), then the finger-grip layer (G10b);
  - L2C, then Two Bone IK on `hand_l` (effector `GunSupportHandHS` in `hand_r` bone space, joint `lowerarm_l`, alpha
    `GunIKAlpha`), then the hand-rotation Modify Bone (G10c), then C2L.
  - **Why not a cleaner linked layer or post-process ABP:** a post-process ABP is a property of the mesh, so it would
    mean editing Epic's `SKM_UEFN_Mannequin` or duplicating it. A linked layer would also need graph edits in the
    duplicated ABP. The insertion is the proven G5 method.
- **Retargeting.** A new `/Game/Guns/Character/Retarget/RTG_Gun_UE5_to_UEFN`:
  - source `IK_UE5_Mannequin_Retarget` (preview mesh: the template `SKM_Manny_Simple`), target `IK_UEFN_Mannequin`;
  - built with `IKRetargeterController` (auto-map chains, auto-align);
  - `IKRetargetBatchOperation.duplicate_and_retarget` copies `MF_Rifle_Idle_ADS`, `AO_Rifle` and its samples,
    `MM_Rifle_Fire`, `MM_Rifle_Reload` and `MM_Rifle_Equip` into `/Game/Guns/Character/Anims_UEFN` with the suffix
    `_UEFN`. The template originals stay as they are, because `BP_NinjaGasp_Gun` keeps using them.
- **Attach.** On `BP_GunCharacter`, `NinjaGun.AttachBone = None`. UEFN's `weapon_r` has an identity frame, which would
  point the barrel wrong. With `None` the gun takes the `hand_r` + `FallbackAttachOffset` branch, which keeps today's
  value: the template hold pose's `weapon_r` in `hand_r`. The two skeletons share the hand-axis convention (palm
  sockets match within 0.2 cm), so the gun sits in the hand exactly as today.
- **Body clips per pawn (C++).**
  - `UNinjaGunComponent::BodyClipOverrides` is a `TMap<UAnimSequenceBase*, UAnimSequenceBase*>` that maps a template
    clip to its `_UEFN` copy.
  - `INinjaGunHolder::ResolveBodyClip()` looks the clip up, and `ANinjaGun::PlayBodyClip` uses it. `DA_Gun_AR01` stays
    one asset for both pawns.
- **GASP flags (C++).** While equipped, `UpdateGaspFlags` re-asserts strafe and aim every tick, because MMB's
  `IA_Strafe` toggles them. Holstering restores the saved values as today.
- **Game mode.** `GM_GunRange.DefaultPawnClass` becomes `BP_GunCharacter` (L_GunRange already uses `GM_GunRange`).
  - `BP_NinjaGasp_Gun` stays in the project, untouched, so the ninja prototype keeps working.
  - The player controller stays the engine's (stock `PlayerCameraManager`, which the probe showed works with modifiers).

### G10a as built (2026-10-11, `runs/G10/pawn.json`, 17/18 gates)
- **Changed from the plan: the gun layer is a post-process ABP, not a duplicate of `SandboxCharacter_CMC_ABP`.** GASP's
  choosers (`CHT_PoseSearchDatabases`, `CHT_CMCCharacterAnimations`) take `SandboxCharacter_CMC_ABP_C` as their context class,
  so a duplicate could not drive motion matching (`runs/G10/pawn/g10a_abp_probe.json`).
  - `/Game/Guns/Character/ABP_GunCharacter` is a duplicate of the mesh's own `ABP_UEFN_Mannequin_PostProcess`. The gun layer sits
    between its Input Pose and the stock chain.
  - `UNinjaGunComponent::BodyPostProcessAnimClass` installs it per component at BeginPlay (`SetOverridePostProcessAnimBP`).
    The gun variables and body montages go to that instance (`INinjaGunHolder::GetGunBodyAnimInstance`).
  - **G10b/G10c edit `ABP_GunCharacter`**, using the builder `Tools/Claude/Guns/build_gun_character_g10.py`.
- **Retarget:** `RTG_Gun_UE5_to_UEFN` has the default ops plus a Pin Bones op, so `hand_r` and `hand_l` take the source's
  global rotation. Without it the barrel pointed 17 deg left; with it, 5.95 deg, which is today's ninja value (about 5.8).
  The plan's 3 deg gate is not met. The hold is left as it is, as the user asked.
- **Left-hand reach:** Two Bone IK allows up to 5 % stretch. UEFN's arm is 11 % shorter, so the reach is about 101.9 % at idle.
- **Damage without the ninja lock-on:** `INinjaGunHolder::IsGunHostileTo`. The ninja pawn keeps the lock-on rule; the gun pawn
  uses `GunTeamId` 0 against the dummy's lock-on TeamId 1.
- **Other changes:** strafe and aim are re-asserted every tick while the gun is out. `BodyClipOverrides` maps the template
  clips to `Anims_UEFN/*_UEFN`.
- **Play test (`gun_playtest.py`):** `GUNS_PAWN` (default `BP_GunCharacter`). F0 is now drawn at spawn, then X holsters and X
  draws again. ADS is a tap of RMB. F13 searches crouched too, because the card-shop camera sits lower.

### G10b: grip (the requested change)
- **Method: a solved, baked finger pose on the finger chains only.** No new IK and no change to the hold.
  - A commandlet solver (`g10b_grip_solve.py`) evaluates the retargeted hold pose on `SKM_UEFN_Mannequin` and places
    the AR-01 exactly as the component does. The handguard is read from the `SM_AR01` LOD0 vertices (27,582 vertices;
    6,284 in the handguard box). Same math as the probe.
  - For each finger it curls joints 01, 02 and 03 about their flexion axes (in the measured 1 : 0.8 : 0.6 proportion)
    until the tip's surface gap reaches the target pad contact. The thumb curls toward the left (-Y) flat of the lower
    handguard.
  - It writes a one-frame `A_AR01_GripL_UEFN` (`AnimDataController.set_bone_track_keys`, finger and metacarpal bones
    only).
- **ABP.** A Layered Blend per Bone sits before L2C, with branch filters `thumb_01_l` and
  `index/middle/ring/pinky_metacarpal_l`.
  - Its blend pose is a Sequence Player whose Sequence pin is the object variable `GunGripPose`. Its weight is
    `GunGripAlpha`.
  - The finger pose is in local space, so it holds through IK, fire additives, walking and aim pitch.
- **C++.** `UNinjaGunData::SupportGripPoses` is a `TMap<TSoftObjectPtr<USkeleton>, UAnimSequenceBase*>`, so each gun
  has one pose per body skeleton and the SMG adds its own.
  - `UNinjaGunComponent` writes `GunGripPose` and `GunGripAlpha`. `GunGripAlpha` follows `IKAlpha`: on in Idle,
    Firing and SelectorChange; in G10c it is also driven by the reload phases.
- **Right hand.** The same solver reports the right fingers against the pistol grip, with the index finger on the
  trigger. If any gap is over 1 cm, a right-hand pose is baked the same way. The right hand is the attach parent, so
  the gun does not move.
- **Fallback if retargeting slips.** The solver and the ABP layer are skeleton-agnostic. Run against
  `SKM_Manny` / `ABP_NinjaVisual_Gun`, the result is `A_AR01_GripL_UE5`.

### G10c: the third-person reload with hands
- **The clock is the AR-01 clip's notifies** (sidecar times, read through `UAnimNotify_NinjaGun::FindEventTime`), so
  the ammo logic, the sounds and the server timing do not change.
- **The left hand follows an IK path computed per frame in `hand_r` space** (exact in the frame the ABP evaluates, as
  today). The IK alpha stays 1 for the whole reload. The phases:
  1. Handguard to the magazine's grip point, from MagRelease minus 0.15 to MagRelease.
  2. Stay on the old magazine (it rides the `magazine` bone) until MagDrop. The magazine drops out of the hand there,
     using the velocity from the existing `ANinjaDroppedMag`.
  3. MagDrop to a pouch point and back with a fresh magazine. The pouch point is a new data offset in `spine_03`
     space at the left front belt. The trip takes 0.18 s out, 0.06 s to grab, and 0.24 s back to the clip's parked
     insert-start pose. The hand reaches it by 1.15 s, the clip's insert start.
  4. From the insert start to MagIn, ride the magazine bone in.
  5. Back to the handguard grip within 0.2 s after MagIn.
  6. ReloadEmpty only: the left hand reaches over to the `ChargingHandle` socket from ChargeRear minus 0.15, rides the
     bolt bone to ChargeRear, lets go at BoltRelease, and returns to the handguard.
- **Hand rotation.** The IK keeps the hold pose's palm-up wrist. A Transform (Modify) Bone on `hand_l` after the IK
  (component space, rotation from `GunSupportHandRotCS`, alpha `GunHandRotAlpha`) turns the palm onto the magazine's
  side or the charging handle.
- **Finger poses.** There are two more baked poses: `A_AR01_MagGripL_UEFN` (a closed cup round the magazine, solved
  against `SM_AR01_Mag`) and an open reach pose. The weights are blended by phase.
- **The magazine in the hand (C++, ANinjaGun).** New `TP_HandMag` and `FP_HandMag` static meshes are attached to the
  body's `hand_l` (or the FP body's) with the solved magazine-in-palm offset.
  - They are visible from the pouch grab until the handover at the insert start. At that moment the hand magazine
    hides and the seated `TP_Mag` shows at the same pose.
  - Between MagDrop and the handover, the parked clip magazine stays **hidden**. Today it floats under the gun for
    0.48 s.
- **The body's upper-body motion.** Option (i) is the hold pose plus the IK path. Option (ii) is the retargeted
  `MM_Rifle_Reload_UEFN`, played at rate 2.2 / 2.0 = 1.1 for gun tilt, with the left arm still on the IK path. Both are
  built, and the one that passes the gates and the close-up review is kept. The default is (i) if both pass, because
  it is simpler.

### G10d: first-person arms
- **The FP body.** A second skeletal mesh component, `FPBody`, on `BP_GunCharacter`:
  - `SKM_UEFN_Mannequin`, FirstPerson primitive type, no shadow, visible only in the FP and ADS views;
  - it runs `ABP_GunFP`, which is the gun layer only: hold, AO at pitch 0, `GunUpper` / `GunAdditive` slots, finger
    layers, IK and hand rotation;
  - head, neck and both thighs are scaled to 0 with Modify Bone nodes in `ABP_GunFP`.

  This is the two-mesh pattern of Epic's 5.6+ first-person template: an FP mesh plus a world-space representation.
- **`FP_Weapon` and `FP_Mag`** attach to the `FPBody`'s `hand_r` with the same `hand_r` offset as the third-person gun.
  - Each frame, `ModifyGunCamera` still computes the desired FP weapon transform: `FirstPersonHipOffset` in FP mode,
    `ComputeAdsWeaponTransform` in ADS, then the kick spring, all as today.
  - Instead of moving the gun, it **solves the FPBody root**: root = Desired x inverse(weapon in FPBody component
    space). The gun lands exactly where it lands today, and the arms hold it.
  - During a reload the hold-pose anchor is used, so the reload motion shows in FP.
- **Montages, IK and grip** are pushed to both bodies: the holder returns the FP body as a second body mesh.
  `FP_HandMag` rides the FP body's `hand_l`.
- **Without an `FPBody`** (`BP_NinjaGasp_Gun`) everything stays as today.

### G10e: free look on Left Alt (PUBG)
- **Input.** New `IA_GunFreeLook` (Boolean, held) on Left Alt in `IMC_GunsBase`, which is always on, so free look
  works with the gun holstered too. It is bound in `UNinjaGunComponent`. The ninja's `UNinjaFreeLookComponent` is
  neither used nor copied.
- **`ProcessGunViewRotation`.** While held, the mouse delta (`OutDeltaRot`) goes into `FreeLookOffset` (clamped to yaw
  ±170 and pitch -60..+60) and is removed from `OutDeltaRot`.
  - The control rotation therefore changes only by recoil and its recovery.
  - The body keeps facing the aim in strafe/aim mode, and movement stays relative to the unchanged control rotation.
  - This code runs before the early return for "no gun data".
- **`ModifyGunCamera`.** It runs after GASP's camera and the shoulder offset, and before ADS. It rotates the POV about
  the pivot (`GetPawnViewLocation()`): Loc' = P + R x (Loc - P), Rot' = R x Rot. Then it sweeps P to Loc' on
  `ECC_Camera` (radius `ShoulderProbeRadius`), ignoring the pawn, the gun and the body.
  - It stores the pre-free-look POV, and `GetGunAimRay` uses it. Shots go where the body aims, not where the player
    looks.
  - The HUD hides the crosshair while |offset| > 2 deg.
- **Release** snaps back (`FreeLookReturnTime` = 0, as in PUBG; it can be eased).
- **Alt is ignored while ADS or shoulder aim is active.** An RMB press during free look ends it, then aims as today.
- **The holstered pawn** goes through the same code. It needs only the free-look action and the camera modifier, which
  are installed whether or not a gun exists.

## Stages, files and gates

Every stage follows the same rules:
- Build C++ with the editor closed (wait in 2-minute polls up to 60 minutes, then report `blocked`).
- Write content through `run_guns.ps1 -Mode commandlet -AllowWrite @('Content/Guns/*')`.
- Run play tests with `-Mode game -ReadOnly`, in a fresh process on the exact saved bytes.
- Record the gates in `runs/G10/<stage>.json`.
- Commit in DemoGame_1 by explicit path, with the message `Guns G10 <stage>: ...`.
- Never edit, save or commit another chat's files, `/Game/Ninja/**`, `/Game/Blueprints/**`, `/Game/Characters/**` or
  `IMC_Sandbox`.

### G10a: pawn (files: `build_gun_pawn10.py`, `verify_gun_pawn10.py`, `g10a_probe_game.py`; C++ `NinjaGunComponent.*`, `NinjaGunHolder.h`, `NinjaGun.cpp`; content `/Game/Guns/Character/{BP_GunCharacter, ABP_GunCharacter, Retarget/RTG_Gun_UE5_to_UEFN, Anims_UEFN/*}`, `GM_GunRange`)

| Gate | Threshold |
|---|---|
| ABP_GunCharacter and BP_GunCharacter compile | `UP_TO_DATE`, 0 node messages |
| Chain from Output, as read back | C2L, (Modify Bone), Two Bone IK, L2C, Layered (fingers), Layered (spine_01), Pose History, ... (GASP's own chain unchanged below) |
| BP_GunCharacter components | the parent's set + `NinjaGun` only (no `Ninja*` gameplay component) |
| Epic assets untouched | `SandboxCharacter_CMC`, its ABP, `SKM_UEFN_Mannequin`, the IK rigs: git hash unchanged, never saved |
| Retarget quality: hold pose, right wrist relative to head (cm), UEFN vs template scaled by the arm ratio | <= 3.0 |
| Retarget quality: hold pose, left/right wrist separation | within 10 % of template |
| Barrel direction vs control direction standing (yaw / pitch, deg) | <= 3 / pitch follows control -60..+60 within 5 (g5 check) |
| Gun mesh to head bone (clearance, cm) | >= 2 |
| Gun relative to `hand_r` | identical to today's offset (<= 0.01 cm / 0.01 deg) |
| Holstered, idle and walking: body pose vs a stock SandboxCharacter_CMC in the same frame (hands, head, pelvis, cm) | <= 1.0 |
| Speed / gait vs stock (walk, run, sprint, crouch, cm/s) | equal within 1 % |
| Camera modifiers active on the GM-spawned pawn (shoulder offset measured right of the base POV, cm) | 80 ± 2 at hip |
| Play test F0-F15 on BP_GunCharacter (gun_playtest.py, FindVisualMesh fallback) | 15/15 |
| g9_camera_probe | 9/9 |
| Frames (hip 3P, side idle, side firing), looked at | gun in hand, no T-pose, no ninja pose |

### G10b: grip (files: `g10b_grip_solve.py`, `g10b_grip_probe_game.py`, ABP edit in `build_gun_pawn10.py`; C++ `NinjaGunData.h`, `NinjaGunComponent.*`; content `/Game/Guns/AR01/A_AR01_GripL_UEFN` (+ `_UE5` if needed))

Gates are measured at runtime at 30 Hz on the live body: idle 2 s, walk 2 s, a **2 s automatic burst**, and shoulder
aim 1 s. Today's values from the probe are given for comparison.

| Gate | Threshold | Today |
|---|---|---|
| Palm grip point (`palm_l_Socket`) to `SupportHand` (cm, p95) | <= 1.0 | 0.0 (IK) |
| Fingertip skin gap to the handguard surface, index/middle/ring/pinky (cm; bone tip point minus a 0.7 cm pad radius) | median <= 0.5, p95 <= 1.0 | 2.8-3.3 |
| Thumb tip skin gap to the left flat (cm) | <= 1.0 | 1.6 (above the top) |
| Finger penetration (pad radius minus distance, or a point inside the section) | max <= 0.5 cm | none |
| Joint 02 points inside the handguard | 0 frames | 0 |
| Hip hold unchanged: gun relative to the pawn and to `hand_r`, vs the G10a baseline | <= 0.2 cm / 0.2 deg | |
| Right hand: index tip to `Trigger` socket / other tips to the pistol grip (cm) | <= 1.0 / <= 1.0 skin gap | report |
| Close-up frames: left side, right side, underside; idle and mid-burst; looked at | fingers visibly wrapped on the wood, no floating gaps | |

### G10c: reload (files: C++ `NinjaGun.*`, `NinjaGunComponent.*`, `NinjaGunData.h`; ABP edit (Modify Bone `hand_l`, the mag-grip pose); `g10c_grip_solve_mag.py`, `g10c_reload_probe_game.py`; content `A_AR01_MagGripL_UEFN`, `A_AR01_ReachL_UEFN`)

| Gate | Threshold | Today |
|---|---|---|
| Palm to the magazine grip point, MagRelease to MagDrop (old magazine) and handover to MagIn (new) (cm, max) | <= 1.5 | 14 / 67 / 89 / 19 |
| Frames where a magazine is visible but neither seated nor within 2 cm of the palm | 0 | 0.48 s parked |
| Handover jump, hand magazine to seated `TP_Mag` (cm) | <= 1.0 | |
| MagIn / ammo change time vs the clip notify | ± 1 frame; F-tests on ammo pass | |
| IK reach / arm length, all frames | <= 0.97 | |
| `hand_l` to the torso capsule (`spine_03` to `spine_05`) | > 8 cm | |
| ReloadEmpty: palm to `ChargingHandle`, ChargeRear - 0.1 to BoltRelease (cm) | <= 2.0 | |
| Back on the handguard grip after the clip end (s; G10b gates hold again) | <= 0.25 | |
| Frames at MagOut, MagDrop, pouch, insert and MagIn (both sides, normal and empty), looked at | hand carries the magazine | |

### G10d: first-person arms (files: C++ `NinjaGunComponent.*`, `NinjaGun.*`; content `ABP_GunFP`, `FPBody` on `BP_GunCharacter`; `g10d_fp_probe_game.py`)

| Gate | Threshold |
|---|---|
| FP hip: FP weapon Grip vs the `FirstPersonHipOffset` target | <= 0.5 cm / 0.5 deg (gun framing unchanged) |
| Arms in the FP frame (FP body mask pixels, lower right) / head, neck or legs in the frame | > 3,000 px / 0 px |
| ADS sight picture (G7 F4 method: front post vs screen centre) | <= 2 px |
| FP reload: hand magazine within 1.5 cm of the FP palm in the same phases as G10c; frames looked at | pass |
| Third person: `FPBody` not rendered; other views and the shadow still show the 3P body (WSR) | pass |
| Play test F0-F15 still pass | 15/15 |

### G10e: free look (files: C++ `NinjaGunComponent.*`; content `IA_GunFreeLook`, `IMC_GunsBase` mapping (`build_gun_content.py`); `g10e_freelook_probe_game.py`, which drives yaw through `AddYawInput` so it passes `ProcessViewRotation`)

| Gate | Threshold |
|---|---|
| Alt held + 90 deg yaw input: control rotation change / body yaw change | <= 0.1 deg / <= 0.5 deg |
| Camera yaw change / orbit radius change (no wall) | 90 ± 1 deg / <= 5 cm |
| Aim ray direction during free look; a shot fired lands at the pre-free-look aim point | <= 0.1 deg; hit within 2 cm of the expected point at 10 m |
| Release: camera back to the pre-free-look view | <= 0.5 deg in 1 frame |
| Walking W with Alt + 120 deg look: velocity heading drift | <= 3 deg |
| Holstered: the same gates | pass |
| Alt during ADS / shoulder aim; RMB during free look | ignored / ends free look, aim as today |
| Recoil during free look goes to the aim (control) | pass |
| Camera in a wall corner (sweep) | camera never inside geometry (trace from the pivot clear) |

### G10f: regression and hand-off
- Run the full `gun_playtest.py` on `BP_GunCharacter` (F0-F15) plus new F16-F20: grip, reload hands, FP arms, free
  look, and card-shop movement parity.
- Run `g9_camera_probe` 9/9.
- Update `HOW_TO_PLAY` (Left Alt free look, the card-shop movement keys LCtrl walk / LShift sprint / C crouch /
  Space jump) and make a contact sheet.
- Merge or push only with the user's go.

## Risks
1. **Headless IK retargeting in 5.8.** The `IKRetargeterController` and `IKRetargetBatchOperation` APIs need checking
   in a dry run first.
   - Fallback A: make the retargeter in Python and retarget clip by clip with `IKRetargetProcessor`.
   - Fallback B: put the grip and reload work on today's body (`BP_NinjaGasp_Gun`) while G10a is reworked.
   - A 5-15 % change in proportions also moves the gun relative to the face; that is gated (head clearance, barrel
     direction).
2. **The size of the GASP ABP.** The duplicate carries motion matching, choosers and a state machine, so it is slower
   to compile. Later GASP updates will not flow into it. The insertion point is outside GASP's logic (after Pose
   History).
3. **Which camera the GM-spawned pawn uses.** The probe pawn was summoned and possessed, and viewed through the arm
   (FOV 90). A GM spawn may run `GameplayCamera` (its output CineCamera has FOV 80). Modifiers apply on both paths
   (stock `PlayerCameraManager`). G10a measures this and does not tune the hip hold, as the user asked.
4. **Grip gates come from bone points with an assumed 0.7 cm pad radius,** because skinned vertices are not readable
   from Python. The close-up frames are the visual authority, and the pad radius is checked once against a
   close-up.
5. **Reload timing.** 0.48 s for the pouch round trip is fast. If it looks rushed, the parked window could be widened
   by re-exporting the AR-01 clip, but that is a gun-asset change and needs the user's go. The plan keeps the sidecar
   times.
6. **FP body cost:** one more owner-only skeletal mesh evaluation. It is hidden in third person, and its tick is off
   when not visible.
7. **Another chat's uncommitted DemoGame_1 work** (BP_NinjaGasp, IMC_NinjaGasp, combat, slash arc, Mimic): commit by
   explicit path only. The guard snapshot flags any change during runs.
8. **The C++ names stay `Ninja*`** (UNinjaGunComponent etc.). They are code names, not ninja gameplay. Renaming is out
   of scope.
