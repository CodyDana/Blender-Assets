# G0 probes (shooting prototype, plan section 10): results

Date 2026-10-09. Engine 5.8, project `DemoGame_1`, map `/Game/Maps/L_NinjaTest` (pawn `BP_NinjaGasp`, game mode
`BP_ThirdPersonGameMode`, dummy `BP_TrainingDummy_C_0`). **Read-only:** in every run the runner's guard 4 found
0 project files written by Unreal and no git-status or hash changes. The one exit-6 run was caused by my own edits to
the probe scripts while it ran; Unreal changed nothing. No Unreal process was left running.

Raw data next to this file: `G0_commandlet.json`, `G0_game.json` (the full -game run), `G0_game_p6b.json` (the P6
follow-up), `G0_analysis.json` (frame measurements), `G0_expected_poses.json` (AnimPose expectations),
`G0_*.guard.txt` (guard logs), `G0_shots/*.png` (frames; PNGs are gitignored).
Scripts (game repo, commit `d9a322b`): `Tools/Claude/Guns/run_guns.ps1`, `g0_probe_cmd.py`, `g0_probe_game.py`,
`g0_analyse.py`.

## Answers at a glance

| Probe | Answer | Plan impact |
|---|---|---|
| P1 collision | Visibility and Camera traces pass straight through both the player and the dummy at pelvis, chest and head height (no hit). The capsule (r 30, hh 86, profile `Custom`, object Pawn) and the hidden GASP `CharacterMesh0` (`SKM_UEFN_Mannequin`, QueryAndPhysics, object Pawn, `PA_UEFN_Mannequin` bodies) both block Pawn-object queries. The visible Manny, cloak and the dummy's visual are NoCollision. | The `Weapon` trace channel (3.3) is needed, as planned. With default Block, both the capsule and the hidden mesh block it, and the capsule is hit first (270 vs 290 cm). Per-bone v2 works on the hidden mesh's bodies, which use UEFN bone names (spine_04/05, head, ...). |
| P2 `weapon_r` | On the skeleton it is a **bone** (child of `hand_r`), not a socket. But **the visible body mesh is `SKM_Manny_Simple` (89 bones) and does not contain `weapon_r`**: `does_socket_exist` is false and bone index is -1. `ik_hand_gun` is present. Reference frame of `weapon_r` in `hand_r`: loc (-1.163, 1.317, -0.520) cm, rot P 15.81 / Y -8.52 / R -11.62 deg. | **Correction to plan 0/8.1:** `TP_Weapon` cannot attach to `weapon_r` on the visible Manny. Attach to `hand_r`, with `HandOffset` = the weapon_r-in-hand_r transform above composed with the gun's grip offset. The alternatives (a socket added to the GASP skeleton or mesh, or swapping in the 161-bone `SKM_Manny`) would edit GASP assets. |
| P3 template rifle clips | They play on the UE5 Manny **with no compatible-skeleton entry**, both at runtime and through an ABP compile. The skeletons have the same 161 bones in the same order and an identical reference pose (0.0000 cm deltas). Single-node playback on `SKM_Manny_Simple` matches the AnimPose expectation within 0.011 to 0.018 cm (MF_Rifle_Idle_ADS at 0 and 0.5 s; MM_Rifle_Reload at 1.0 s). An `MM_Rifle_Reload` dynamic montage on the visible Manny's DefaultSlot matches within 0.014 cm. An ABP on the UE5 skeleton with a template-clip Sequence Player compiles `BS_UP_TO_DATE` with no messages. | No Compatible Skeletons edit is needed. One is useful only for the editor's asset pickers, because compatibility is used by pickers and drag-drop only (engine source). **New finding:** `MM_Rifle_Fire` is a mesh-space rotation additive (`AAT_ROTATION_OFFSET_MESH_SPACE`, 16 frames). Played through a normal slot it moves the hands only 3.6 cm, so the gun layer needs an additive slot plus Apply Mesh Space Additive, not a plain `GunUpper` slot. |
| P4 GASP aim flag | With the spring-arm camera, WantsToAim changes **rotation only**. The rotation mode becomes controller-desired, the capsule snaps to the camera yaw within 0.2 s, and the visible body turns in place to face the camera. It changes **no camera** (FOV 85, arm 375, offsets 0, 369 cm behind and 135 cm above in every state), **no speed** (MaxWalkSpeed 575, walks at 575) and **no pose** (hands within 2.6 cm of baseline). WantsToStrafe alone also switches the capsule, but the standing visible body does not turn in place: its hands rotate about 90 deg in pelvis space. | Setting strafe and aim together while a gun is out (plan 7) is right. Aim alone already does the turning. The hold pose must come from our layer. The "closer over-the-shoulder framing" note in the game's CLAUDE.md is stale for the spring-arm setup (reported only; not our file). |
| P5 FirstPerson Niagara | **Yes.** World FOV 85 with FirstPersonFieldOfView 40 predicts a 2.518x offset for FirstPerson primitives. Cube pair: 2.532 (control 1.010). FountainLightweight: emitter offset 2.91x, cloud centroid 2.15x (control 0.89 / 0.99; the FP cloud is clipped at the frame top). NS_MuzzleFlash: the FP copy's sprites and shell meshes are drawn about 2.5x larger and farther out (frames); the centroid ratio is not usable because the two flashes overlap. The Niagara components spawned attached to the pawn's camera are owned by the pawn. | FP flash and FP casing as FirstPerson Niagara (4.1, 8.2) work as planned. The stock NS_MuzzleFlash at 1 m covers about half the frame at FOV 85, so the restyle in G4 must scale it down. |
| P6 owner-no-see through the child actor | **No.** The visual child actor's Owner is **None** (owner chain = itself), so the pawn is not in it. With WSR on the visible Manny, 1,041 px differ from base and OwnerNoSee 966 px, against a noise floor of 1,334 px: the owner still sees the body. A pawn-owned prop behaves as documented: WSR removes its silhouette (9,224 px) and keeps its shadow (15,503 px still differ from the hidden frame), and OwnerNoSee hides it and its shadow (24 px). **Follow-up P6b:** after `SetOwner(pawn)` on the visual child actor at runtime, WSR on the Manny and its attached primitives hides the body from the owner (43,458 px removed) and keeps its shadow (28,972 px). | **Correction to plan 5.1 ("the body WSR too"):** `UNinjaGunComponent` must re-own the visual child actor (`VisualOverride->GetChildActor()->SetOwner(Pawn)`) after BeginPlay and whenever the child actor is re-created (construction script, MetaHuman switch). WSR must then go on the Manny **and** the primitives attached under it (cloak, MetaHuman parts). Otherwise ADS shows the body. |
| P7 BlueprintTools in a commandlet | **Yes**, `editor_toolset.toolsets.blueprint.BlueprintTools` works in a DemoGame_1 `-run=pythonscript` commandlet with no extra plugin flag. A transient ABP on the UE5 skeleton was built with Sequence Player, Sequence Evaluator (ExplicitTime pin from a float variable), Layered Blend Per Bone (spine_01 branch filter, mesh-space rotation), Slot, Local To Component, Transform (Modify) Bone (hand_r, additive bone-space translation, Alpha and Translation pins from variables), Two Bone IK (hand_l, world-space effector from a vector variable), Component To Local and Output. All properties were set by JSON and read back exactly, the full chain was verified from Output back to the source, and it compiled `BS_UP_TO_DATE` with 0 messages. Renaming the slot to `GunUpper` also compiles, and the skeleton was not dirtied. A child Blueprint of BP_NinjaGasp compiles. Overriding the inherited `VisualOverride` child-actor class sticks on the child and leaves the parent's value (`BP_NinjaVisual`) unchanged. Adding a StaticMeshComponent works. | The headless ABP route (plan 8b, risk 3) works, including the layer, modify-bone and IK nodes. Two notes: `try_create_connection` does **not** insert space conversions (the LocalToComponent and ComponentToLocal nodes must be added explicitly), and `read_graph_dsl` returns nothing for anim graphs. G5's child-BP route works. Building a child BP or gathering subobjects marks BP_NinjaGasp dirty in memory, so build scripts must save **only their own packages**. |

## Details

### P1: collision (runtime, `G0_game.json` P1)
- Player and dummy: `CollisionCylinder` QueryAndPhysics, object Pawn. It blocks WorldStatic, WorldDynamic, Vehicle
  and Destructible, and ignores Pawn, Visibility, Camera and PhysicsBody. Profile name at runtime: `Custom`.
- Hidden `CharacterMesh0` (`SKM_UEFN_Mannequin`, `SandboxCharacter_CMC_ABP`, AlwaysTickPoseAndRefreshBones, not
  visible): QueryAndPhysics, object Pawn. It blocks WorldStatic, WorldDynamic, PhysicsBody and Destructible, and ignores
  Pawn, Visibility, Camera and Vehicle. Physics asset `PA_UEFN_Mannequin`.
- Visual child actors (`BP_NinjaVisual` / `BP_DummyVisual`, component tag `NinjaVisual`): `Manny`
  (`SKM_Manny_Simple`, `PA_Mannequin`, `ABP_NinjaVisual`), `Cloak`, `CloakMH`: all NoCollision.
- Traces from 3 m in front through each actor:
  - Visibility and Camera, simple and complex: no hit at any height.
  - Object query Pawn: capsule at 270 cm, then hidden-mesh bodies at 290 to 303 cm (pelvis, spine_01, thigh_r;
    spine_05, spine_04, clavicle_r; head).
  - PhysicsBody and WorldDynamic queries: nothing.

### P2: `weapon_r` (`G0_commandlet.json` P2, `G0_game.json` P2)
- `/Game/Characters/UE5_Mannequins/Meshes/SK_Mannequin`: 161 bones. `weapon_r` and `weapon_l` are bones (parents
  `hand_r` / `hand_l`). `ik_hand_gun`'s parent is `ik_hand_root`. Skeleton sockets: `weapon_r_muzzle` on `weapon_r`
  at (45, 0, 25), and foot sockets. There is no `HandGrip_R` (the template skeleton has `HandGrip_R` on `hand_r`:
  (-7.01, 2.05, 0), yaw 90).
- `weapon_r` in `hand_r` (reference pose): loc (-1.1634, 1.3171, -0.5195), rot P 15.8084 / Y -8.5171 / R -11.6176.
  Its axes in the hand frame: x (0.952, -0.143, 0.272), y (0.091, 0.977, 0.194), z (-0.294, -0.160, 0.943).
- Runtime, visible Manny (`SKM_Manny_Simple`, 89 bones): `weapon_r`, `weapon_l` and `HandGrip_R` are absent.
  `ik_hand_gun` is bone 84 and sits at its reference transform while idling.
- Runtime, hidden UEFN mesh: its own `weapon_r` (bone 59, parent `hand_r`), loc (0.197, 3.411, -0.381) with an
  identity rotation. This is a different frame from the UE5 skeleton's.

### P3: template rifle clips (`G0_commandlet.json` P3, `G0_game.json` P3)
- Clips (skeleton `/Game/Characters/Mannequins/Meshes/SK_Mannequin`):

  | Clip | Length | Frames | Type |
  |---|---|---|---|
  | MF_Rifle_Idle_ADS | 8.0 s | 240 | not additive |
  | MM_Rifle_Fire | 0.533 s | 16 | mesh-space rotation additive |
  | MM_Rifle_Reload | 2.2 s | 66 | not additive |
  | MM_Rifle_Equip | 1.667 s | 50 | not additive |
  | MM_Rifle_DryFire | 0.8 s | 24 | not additive |
  | AO_Rifle | | | AimOffsetBlendSpace |

  None has root motion.
- CompatibleSkeletons: the UE5 skeleton lists the BareNinja and MuayThai copies; the template skeleton lists nothing.
  Nothing was added.
- Compatibility checks in 5.8 source are only in the editor: action filtering in `AnimGraphNode_AssetPlayerBase`,
  drag-drop in `AnimationGraphSchema`, and `BlendSpace` sample validation. They are not in compile validation
  (`ValidateAnimNodeDuringCompilationHelper` checks only that a skeleton exists) or at runtime. The reverse entry is
  read from the on-disk asset-registry tag.

### P4: GASP aim / strafe (`G0_game.json` P4; frames `p4_*`)
- The flags were written as `CharacterInputState` text (`WantsToAim_7_3A4A...`, `WantsToStrafe_5_64E8...`) with
  `PropertyAccessChangeNotifyMode.NEVER`. The child actor was unchanged throughout, and the initial values were
  restored at the end.
- `UpdateRotation_PreCMC` (DSL): `if (input-state A or B)` sets UseControllerDesiredRotation true and
  OrientRotationToMovement false, otherwise the reverse. The runtime results identify A and B as strafe and aim.
  `GetDesiredGait`'s input-state branch does not respond to aim, since walking under aim stayed at 575 cm/s.
- Visible Manny `hand_r` in pelvis space, standing with the camera 90 deg off the original facing:

  | State | hand_r (cm) |
  |---|---|
  | baseline | (-31.0, -12.8, -4.0) |
  | aim | (-29.6, -14.9, -3.8) |
  | strafe | (-21.3, 24.5, -4.3) |
  | aim + strafe | (-29.6, -14.9, -3.8) |

### P5: FirstPerson rendering (`G0_analysis.json` P5; frames `p5_*`)
- Layout: mirrored pairs attached to the player camera in front of a black unlit backdrop, rendered with
  `ShowFlag.Lighting 0`, eye adaptation and bloom off, AA off. Niagara was frozen with slomo 0.0001 right after
  activation.
- Cube: the FP copy is offset 266.1 px (expected 263.8) and the world copy 105.1 px (expected 104.8). The size ratio
  is 2.466, against the expected 2.518.

### P6 / P6b: owner-no-see (`G0_analysis.json` P6, P6b; frames `p6_*`, `p6b_*`)
- The prop is a StaticMeshActor spawned with the cheat manager's `summon` and given `SetOwner(pawn)`, lit by a spawned
  low directional light.
- The P6b follow-up re-toggled the visibility of every primitive attached under the Manny to force new scene proxies.
  The dummy is visible in those frames because the camera framing was different. This does not affect the
  conclusion: the body and cloak vanish under WSR while their shadow stays (`p6b_10_reowned_wsr.png`).

## Harness notes for G2 onward
- Python cannot spawn actors into a `-game` world through `GameplayStatics.begin_deferred_actor_spawn_from_class`,
  because it is BlueprintInternalUseOnly and not exposed. What works: `EnableCheats` + `summon <Class>`, then
  `SetOwner` and moving the actor; and `NiagaraFunctionLibrary.spawn_system_attached`.
- K2_ functions use their script names in Python (`set_actor_location_and_rotation`, `attach_to_component`,
  `destroy_actor`). `ChildActorComponent.get_child_actor` is not exposed; use `get_editor_property("child_actor")`.
- `AssetTools.create_asset` into `/Temp` returns None. The transient probe assets went to
  `/Game/__ClaudeGunProbe_UNSAVED`, in memory only and never saved; the guard confirmed nothing was written.
- HighResShot re-runs overwrite the same file names, so the committed `shot()` checks file time, not new names.
  Final run 5 used the older name check: every frame waited its 40 s timeout, so the run took 1040 s, though the frames
  are valid. The committed `g0_probe_game.py` differs from the run-5 copy only in that check and in the P6b phase.

## Runs (honest log)
- **Commandlet: 3 runs** (189, 151 and 160 s).
  - Run 1 failed on a wrong Quat API call and the missing `reconstruct_node`.
  - Run 2 completed, but the gun-layer chain was disconnected (no automatic space conversion) and the DSL search hid
    member names.
  - Run 3 was the final run, with 0 errors.
- **-game: 6 runs.**
  - Run 1 failed at setup (child-actor accessor).
  - Run 2 failed P3, P5 and P6, because there is no Python deferred spawn.
  - Run 3 failed on the K2 function name.
  - Run 4 completed, but the P3 montage only covered the additive Fire clip.
  - Run 5 is the final full run: all phases, 0 errors, 1040 s. The runner exited 6 because I edited
    `g0_analyse.py` and `g0_probe_game.py` and `py_compile` wrote a `__pycache__` during the run; that was my editing,
    not Unreal.
  - Run 6 is the P6b follow-up only (61 s).
- Every run passed guards 1 to 3: no editor had DemoGame_1 open, the MCP port 8000 was closed, the machine was free,
  and the DLL (2026-10-06 22:07) was newer than all Source files (22:04).
