# Sniper Rifle SR-01: SK_SR01, SM_SR01, SM_SR01_Mag, SM_Att_Scope_LongRange

A bolt-action precision rifle with:
- an olive chassis and an adjustable cheek riser;
- a folding, extending, canting bipod;
- a detachable 10-round box magazine;
- a separate long-range scope.

The rifle is a rigged skeletal mesh. The bolt, trigger, safety, magazine release, magazine, cheek riser and bipod move.
A static twin is included for pickups and world props. The magazine and the scope are separate static meshes. The gun
carries generic markings only (S / F at the safety): no names, serials or logos.

> **Status (W6, 2026-10-14): verified in Unreal Engine 5.8.3; pack materials not built yet.**
> - These exact bytes (sha256 in `WorkFiles/guns/sniper/UnrealCheck/SHA256_at_start.json` / `_at_end.json`) were
>   imported and checked in fresh Unreal processes: 37 of 37 gates pass
>   (`WorkFiles/guns/sniper/UnrealCheck/verification_summary.json`).
> - The hand fit on a player MetaHuman (U11) was not run: there is no player MetaHuman in the verification project.
> - The pack's recolourable material instances (`MI_SR01_*`) are proposed but not built
>   (`MATERIALS_README.md`, `WorkFiles/guns/sniper/pack_materials_proposal.md`). The maps here work with any PBR
>   material.

## What is in this folder

| File | What it is |
|---|---|
| `SK_SR01.fbx` | The rifle as a skeletal mesh, LOD0 (40,518 triangles; no scope, no magazine). Skeleton `SK_SR01_Skeleton`: `root` + 13 rigid bones (`body`, `bolt`, `trigger`, `selector`, `mag_release`, `magazine`, `muzzle_device`, `cheek_riser`, `bipod`, `bipod_leg_l`, `bipod_leg_l_ext`, `bipod_leg_r`, `bipod_leg_r_ext`); one influence per vertex |
| `SK_SR01_LOD1.fbx` .. `_LOD3.fbx` | LOD1-3 on the same skeleton (18,202 / 6,028 / 2,490 triangles). Import them as LODs of `SK_SR01` and do not remove bones |
| `A_SR01_Fire.fbx` | The trigger breaks and resets; the bolt does not move (60 fps, 8 frames) |
| `A_SR01_BoltCycle.fbx` | The bolt lifts 60 degrees, runs 88 mm back, holds, runs forward and turns down (30 fps, 30 frames) |
| `A_SR01_Reload.fbx` | Paddle pressed, magazine straight out, dropped, a new one straight in, catch snaps (30 fps, 60 frames) |
| `A_SR01_ReloadEmpty.fbx` | Starts with the bolt open; the reload, then the bolt forward and down (30 fps, 90 frames) |
| `A_SR01_Selector.fbx` | Safety: Fire, Safe, Fire (30 fps, 20 frames) |
| `A_SR01_BipodDeploy.fbx` / `A_SR01_BipodStow.fbx` | The legs swing down (the left leads by 2 frames) and extend 38 mm; Stow reverses it (30 fps, 36 frames each). Deploy ends deployed; Stow starts deployed |
| `A_SR01_CheekRiser.fbx` | Optional: the riser goes up 12 mm, down to -12.9 mm and back (30 fps, 24 frames) |
| `SK_SR01.skeletal.json` | Sidecar: bones, 20 sockets, LOD sizes, import settings, bounds extension, notifies, physics bodies, materials, mass, the gun data (`gun`: frames, bipod, scope, angle table) |
| `Physics/SK_SR01_PhysicsProxy.fbx` | A proxy that rebuilds `PHYS_SR01` exactly (see Physics) |
| `SM_SR01.fbx` (+ `.sockets.json`) | Static twin (bipod folded, magazine merged in), LOD0-3 (41,396 / 18,596 / 6,178 / 2,552 triangles), 10 convex hulls `UCX_SM_SR01_LOD0_00..09`, 20 sockets |
| `SM_SR01_Mag.fbx` (+ `.sockets.json`) | The removable magazine, LOD0-3 (878 / 394 / 150 / 62 triangles), 1 hull, 5 sockets. At every LOD it is the same mesh as the twin's merged magazine |
| `SM_Att_Scope_LongRange.fbx` (+ `.sockets.json`) | The long-range scope with its rings, LOD0-2 (9,938 / 4,464 / 1,454 triangles), 3 hulls, 5 sockets. Its origin is the `Mount` |
| `Textures/` | `T_SR01_Metal_*` (2048), `T_SR01_Chassis_*` (4096), `T_SR01_Mag_*` (1024), `T_Att_Scope_LongRange_Scope_Body_*` (2048), `_Scope_Lens_*` (512): BC, ORM, N, and Masks (half size) per set. `Recolour/` holds the OD paint's Detail16 map (2048) and `recolour_maps.json` |

## Frames and units

- **Blender / sidecar frame:** millimetres, +X toward the muzzle, +Z up, +Y the gun's left. The bolt handle is on the
  right (-Y).
- **Origin:** the `Grip` socket (`body` bone head), on the traced grip axis (27.15 degrees). The bore runs at
  Z +96.13 mm, the butt-pad rear is at X -297.13 mm and the muzzle at X +802.87 mm. Overall length is 1,100 mm.
- **Unreal:** component space in centimetres with Y flipped: (X, -Y, Z) / 10. The sidecars give both (`*_mm` and
  `location_cm` / `unreal_rotation_deg`).
- **Import:** *Convert Scene* on, *Force Front X Axis* off.

## Import into Unreal Engine 5.8

### Skeletal mesh and clips

1. Import `SK_SR01.fbx` with **Import Normals**, *Convert Scene* on, *Force Front X Axis* off, Import Mesh LODs on.
   Do not create a physics asset at import.
2. Import LOD1-3 onto `SK_SR01` (`SkeletalMeshEditorSubsystem.import_lod`, same skeleton and root). Set the LOD
   screen sizes to **1.0 / 0.27301 / 0.07165 / 0.03604**: the LOD-pop switch distances in both bipod poses, at the
   mesh's radius including the bounds extension. First-person components force LOD0.
3. Import the eight `A_SR01_*` clips onto `SK_SR01_Skeleton`, each at its own frame rate, with *Use T0 As Ref Pose*
   off. Set every clip's **bone compression to `/Engine/Animation/DefaultRecorderBoneCompression`**. The project
   default (ACL) moves rigid parts by about 1 mm.
4. Set the **bounds extension** from the sidecar (`import.bounds_extension_cm`): Positive (0, 8.681, 2.31) cm,
   Negative (0, 12.877, 18.386) cm. The bind box covers the folded rifle; the extension holds every vertex at every
   frame of every clip and at the extreme poses (bipod deployed, extended 76 mm, canted 15 degrees; bolt open and back;
   riser up). Measured in Unreal: 0 vertices outside.
5. The FBX files carry no notifies. Add them at these frames (also in the sidecar's `notifies`):

| Clip | Notifies (frame) |
|---|---|
| `A_SR01_Fire` | `Fire` 2, `TriggerReset` 8 |
| `A_SR01_BoltCycle` | `BoltUnlock` 1, `ShellEject` 13, `BoltForward` 16, `BoltLock` 30 |
| `A_SR01_Reload` | `MagRelease` 2, `MagOut` 9, `MagDrop` 18, `MagIn` 50 |
| `A_SR01_ReloadEmpty` | as Reload, then `BoltForward` 62, `BoltLock` 76 |
| `A_SR01_BipodDeploy` | `BipodLegOut_L` 10, `BipodLegOut_R` 12, `BipodLocked` 30 |
| `A_SR01_BipodStow` | `BipodRetracted` 14, `BipodStowed` 32 |

- **Bolt action:** `Fire` does not cycle the bolt. The game chains `Fire` -> `BoltCycle` (or skips it).
- **Safety held:** `Fire`, `BoltCycle` and `ReloadEmpty` hold the safety at Fire.
- **Clips that do not start or end at rest:** `ReloadEmpty` starts with the bolt open, `BipodDeploy` ends deployed
  and `BipodStow` starts deployed at 38 mm extension. Every other clip starts and ends at the bind pose.

### Bones and the angle table

| Bone | Motion (from the bind pose) |
|---|---|
| `bolt` | rotate about X 0..-60 degrees, then translate -X 0..88 mm (it only slides at -60 and only turns at 0) |
| `trigger` | rotate about Y 0..+6 degrees |
| `selector` | rotate about Y: Fire 0 (bind), Safe -12 degrees |
| `mag_release` | rotate about Y 0..-4.5 degrees (paddle forward, hook back) |
| `magazine` | carries the magazine along the reload path (unweighted; attach `SM_SR01_Mag` here) |
| `cheek_riser` | translate Z -12.9..+12.0 mm |
| `bipod` | cant: rotate about X -15..+15 degrees (0 in every clip) |
| `bipod_leg_l` / `_r` | rotate 0 (folded forward) .. +90 degrees (deployed down) about the leg pin. The pin is rolled 12 degrees about X (left +12, right -12), so a deployed leg leans 12 degrees outward |
| `bipod_leg_l_ext` / `_r_ext` | translate +X in the leg's rest frame 0..76 mm (detents every 19 mm) |

The sidecar's `abp_angle_table` lists these ranges for an Anim Blueprint. `SK_SR01_Skeleton` is compatible with
`SK_AR01_Skeleton`: add it under *Compatible Skeletons*.
- One ABP authored on the AR-01 skeleton drove the SR-01's bolt, trigger, selector and release in Unreal (W5 U2b).
- Nodes on the sniper-only bones (`cheek_riser`, `bipod*`) compile there with "bone not found" and do nothing. For a
  warning-free Blueprint, drive those bones by the clips or by a sniper-only linked layer.

## The bipod in use

- **Deploy / stow:** play `A_SR01_BipodDeploy` (legs 0 -> 90 degrees, then extension 0 -> 38 mm) and
  `A_SR01_BipodStow` (the reverse, ending at the bind pose). The legs are independent, with detents at 0 and 90
  degrees.
- **Splay:** each deployed leg leans **12 degrees** outward (measured in Unreal: 12.0 degrees), so the feet stand wider
  than the hub.
- **Extension:** 0..76 mm in five detents (0 / 19 / 38 / 57 / 76). The ground height below the bore at each detent,
  with both legs deployed and no cant:

| Extension (mm) | 0 | 19 | 38 | 57 | 76 |
|---|---|---|---|---|---|
| Ground below the bore (mm) | 266.7 | 285.3 | 303.9 | 322.5 | 341.1 |

- **Prone placement:** set both legs to 90 degrees and pick the extension (a scalar per leg, no IK chain) so that
  `BipodFoot_L` and `BipodFoot_R` (on the extension bones, at the foot end faces) reach the ground. The rear rests on
  `SupportHandBipod` (the off hand under the butt) or a rear bag.
- **Cant:** rotate the `bipod` bone about X up to +-15 degrees, folded or deployed. Clearance is at least 7.7 mm
  folded and 32.4 mm deployed.
- **Bounds:** the bounds extension in step 4 covers deployed + 76 mm + 15 degrees of cant. Do not shrink it.
- **Physics:** `PHYS_SR01` uses the folded pose. Fold the legs (`BipodStow`, or snap them to 0) before dropping the
  gun. While the gun is held, the deployed legs are kinematic.
- The static twin `SM_SR01` has the bipod folded. For a deployed world prop, use `SK_SR01` posed at the last frame of
  `BipodDeploy`. The showcase's `*_BipodDeployed_*` images are that pose.

## The scope (`SM_Att_Scope_LongRange`)

- **Attach:** put the scope's origin (`Mount`, the rear ring's recoil lug on the rail-top plane) on the gun's
  `Rail_Top` socket **+ 2 slots: X +20.02 mm** (2.002 cm), with zero rotation. `Rail_Top` is the centre of slot 0 of
  15; slot k is at +k x 10.01 mm. In Unreal the scope lands within 0.001 cm of the Blender build.
- **Aim sockets:** the rifle has no iron sights and no `Sight` socket; the scope's sockets are the aim sockets.
  - `Sight`: the scope axis at the eyepiece face, 57.6 mm above the bore and parallel to it (within 0.05 degrees);
  - `EyePoint`: 95 mm eye relief behind `Sight`, over the cheek riser. Put the ADS camera here;
  - `Lens_Front`: the objective face;
  - `CenterOfMass`.
- **No zero is built in:** at 10 m the bore sits 5.76 cm below the cross. A game applies its own zero.
- **Clearance:** the bolt knob clears the mounted scope by 29.9 mm over the whole cycle.
- **Mass:** 1.15 kg with the rings (spec).
- LOD screen sizes 1.0 / 0.09516 / 0.02497 (`.sockets.json`). The scope has its own FP and TP components (below).

## First person (UE 5.8 First Person rendering)

Use two components per part, both attached as listed:

| Components | Mesh | Attach to |
|---|---|---|
| `FP_Weapon`, `TP_Weapon` | `SK_SR01` | the hand |
| `FP_Mag`, `TP_Mag` | `SM_SR01_Mag` | the `Mag` socket |
| `FP_Scope`, `TP_Scope` | `SM_Att_Scope_LongRange` | `Rail_Top` + 2 slots |

- On every first-person component set *First Person Primitive Type* = **FirstPerson** and **ForcedLodModel = 1**
  (always LOD0). The third-person components keep normal LOD switching.
- Measured in Unreal: the TP ground shadow is present and the FP components cast none.
- Hiding the TP components from the owner needs the weapon Blueprint on a possessed pawn (game side); that part was
  not verified here.

## Sockets

`SK_SR01.skeletal.json` lists 20 sockets with their bones (mm, Blender frame):

| Socket | Bone | Where |
|---|---|---|
| `Grip` | body | origin, on the grip axis |
| `SupportHand` | body | forend belly behind the bipod clamp (342.9, 0, 50.5); provisional until the full hand fit |
| `SupportHandBipod` | body | off hand under the butt when prone (-179.1, 0, 4.1); provisional |
| `Trigger` / `Selector` / `MagRelease` | their bones | trigger face, safety lever tip, paddle |
| `BoltHandle` | bolt | the knob centre (hand target for the bolt cycle) |
| `Muzzle` | muzzle_device | the muzzle face (802.9, 0, 96.1) |
| `MuzzleSeat` | body | where a muzzle device seats (752.6, 0, 96.1) |
| `ShellEject` | body | port centre; +X = the throw direction (right, up, slightly back) |
| `Mag` | magazine | the well entry; the magazine snaps here |
| `MagInsertStart` | body | 67.8 mm straight below `Mag` |
| `Rail_Top` | body | centre of rail slot 0 (99.0, 0, 126.1) |
| `SlingFront` / `SlingRear` | body | the bipod clamp front / the QD cup on the butt's left |
| `Shoulder` | body | butt-pad rear centre |
| `CenterOfMass` / `Holster` | body | (200.2, -0.3, 68.7) |
| `BipodFoot_L` / `_R` | bipod_leg_*_ext | the foot end faces: the ground contacts when deployed |

- **Static meshes:** Unreal 5.8 drops the FBX sockets of any file with a LOD group. Recreate them from the
  `.sockets.json` sidecars (`Scripts/pipeline/ue_import_sockets.py`, or `unreal.new_object(unreal.StaticMeshSocket,
  outer=mesh)`). Set the LOD screen sizes from the sidecars too: `SM_SR01` 1.0 / 0.25 / 0.06561 / 0.033;
  `SM_SR01_Mag` 1.0 / 0.03448 / 0.00905 / 0.00455.
- **Magazine sockets:** `Mag`, `Feed`, `Base`, `HandReload`, `CenterOfMass`.
- **Scope sockets:** see the scope section.
- **Twin sockets:** the twin's `BipodFoot_*` are the folded positions.

## Magazine and reloads

- `SM_SR01_Mag` snaps to the `Mag` socket with a zero relative transform (SnapToTarget; measured error 1.6e-14 cm).
- The reload path is **straight**: from `MagInsertStart` (67.8 mm below the seat) to `Mag`, a lerp along +Z with the
  rotation constant.
- The release catch is spring-loaded: the magazine cams it back and it snaps into the notch. On the reload clips
  only the catch nose touches the magazine, 0.09 mm deep for one frame.
- `A_SR01_Reload` moves the `magazine` bone along the path, so a magazine attached to that bone follows it. For a
  hand-held magazine (on `hand_l`, socket `HandReload`), copy the clip's `MagOut` and `MagIn` frames to the character
  montage.

## Collision

- **Static meshes:** `SM_SR01` collides through 10 convex hulls `UCX_SM_SR01_LOD0_00..09`, the magazine through 1 and
  the scope through 3. All hulls have 32 vertices or fewer.
  - Import with *One Convex Hull per UCX* on and *Auto Generate Collision* off.
  - Every LOD0 surface sample lies inside the hulls (measured in Unreal: 0 of 320,744 / 300,443 / 305,003).
- **Skeletal mesh:** `SK_SR01` collides through `PHYS_SR01` (below).
- **In hand:** while the gun, magazine and scope are attached to the character, set their components to
  *No Collision* (or a query-only weapon profile) with *Simulate Physics* off, so they never push the capsule. Turn
  collision and physics on only for a dropped gun or a world pickup.
- **Centre of mass:** 200.2 / -0.3 / 68.7 mm from the `body` origin (the `CenterOfMass` socket; bipod folded).
- **Mass:**
  - the rifle 5.9 kg without the scope and magazine, bipod included (`PHYS_SR01` mass override);
  - the magazine 0.20 kg empty, 0.45 kg with 10 rounds;
  - the scope 1.15 kg;
  - ready to fire about 7.5 kg.

## Physics

- **`PHYS_SR01`:** one body on `body` (5.9 kg) made of the sidecar's `physics_bodies`:
  - 7 boxes: butt, grip, action, trigger guard, magazine well, forend with clamp, folded bipod;
  - 1 capsule: the barrel;
  - one **bounds-envelope box with no collision and no mass** (the mesh's extended bounds). A skeletal component takes
    its bounds from the physics asset, so the envelope keeps the deployed bipod and the open bolt inside the bounds.
- **Measured in Unreal:** SM_SR01 (level and rolled), the magazine and SK_SR01 dropped from 1 m come to rest with no
  tunnelling.
- **To rebuild `PHYS_SR01`:**
  1. Import `Physics/SK_SR01_PhysicsProxy.fbx` onto `SK_SR01_Skeleton` with *Create Physics Asset* on. It makes one
     body on `body`.
  2. Replace that body's shapes with the sidecar's, keeping each element's collision and mass flags.
  3. Rename the asset `PHYS_SR01`, assign it to `SK_SR01` and delete the proxy mesh.

## Materials and textures

| Slot | Mesh(es) | Texture set | Proposed pack instance (not built) |
|---|---|---|---|
| `M_SR01_Metal` | 0 on `SK_SR01` and `SM_SR01` | Metal 2048 | `MI_SR01_Metal` (`M_Steel_Master`) |
| `M_SR01_Chassis` | 1 on `SK_SR01` and `SM_SR01` | Chassis 4096 | `MI_SR01_Chassis` (`M_Fabric_Master`, Metal From ORM on) |
| `M_SR01_Mag` | 2 on `SM_SR01`, 0 on `SM_SR01_Mag` | Mag 1024 | `MI_SR01_Mag` (`M_Fabric_Master`, Metal From ORM on) |
| `M_Att_Scope_Body` / `M_Att_Scope_Lens` | 0 / 1 on the scope | Scope Body 2048 / Lens 512 | `MI_Att_Scope_LongRange_Body` / `_Lens` (`M_Steel_Master`) |

- Maps, colour spaces, Masks channels and the recolour plan are in `MATERIALS_README.md`.
- **Draw calls in hand:** 10 (gun 2 x 2 + magazine 2 x 1 + scope 2 x 2, FP and TP).
- **UV tiles:** the twin's UV0 sits in tiles (Metal 0, Chassis 1, merged magazine -1) and the scope's (Body 0,
  Lens 1). Keep Wrap addressing.
- **Lightmap UVs:** UV1 is authored (index 1). Generate Lightmap UVs off.
- **Nanite:** off on every mesh.

## Good to know

- **Triangles:** LOD0 for the held set is 51,334 (gun 40,518 + magazine 878 + scope 9,938). The gun alone is within
  the plan's 35-45k target (50k ceiling).
- **Close-up realism is not signed off.** The two realism judges did not pass the close views (FP 35 cm, the scope
  view, a 3x crop) after one W4b round. The game views (TP 3 m, hero) are the intended use; see
  `WorkFiles/guns/sniper/SR01_REPORT.md`.
- **Hand pose:** `Grip` and `SupportHand` are provisional until a player-MetaHuman hand fit (U11) runs in Unreal.
  The Blender hand fit on `MH_PlayerDefault` has run (H1 full, `WorkFiles/guns/sniper/H1_REPORT.md`). Both hands seat
  with 0 intersections at every clip extreme, and the index rests 0.7 mm from the trigger. Known follow-ups, measured
  but not applied (the exports are unchanged):
  - `SupportHand` (B 342.87, 0, 50.53 mm) is out of the left arm's reach by 83 mm when the body stands square to the
    target. It is reachable with the shoulders turned 23 deg (a bladed stance), or at X 259.9 or nearer in the square
    stance.
  - `SupportHand` sits 9.6 mm inside the forend: the palm rests on the band's underside at Z 40.90.
  - `SupportHandBipod` sits 38.1 mm inside the butt: the palm rests at Z -33.99.
  - The cheek riser at full drop leaves the eye 38.4 mm above the comb. The fit body's upright face needs about
    40 mm under the eye, so the riser is 1.6 mm short of travel there; at the riser's rear it would need 41 mm.
  - The thumb cannot wrap the grip's left side with this body's rest thumb, so the engine hand pose needs its own
    thumb.

## Measured in Unreal 5.8.3 (W5, run `/Game/GunCheck/SR01_1014b`)

- Import: the legacy FBX importer with the settings above. Triangles per LOD are identical in Blender, the FBX and
  Unreal: SK_SR01 40,518 / 18,202 / 6,028 / 2,490; SM_SR01 41,396 / 18,596 / 6,178 / 2,552; SM_SR01_Mag
  878 / 394 / 150 / 62; the scope 9,938 / 4,464 / 1,454. LOD screen sizes match the sidecars: SK 1 / 0.273 / 0.0717 /
  0.0360, SM 1 / 0.25 / 0.0656 / 0.033, Mag 1 / 0.0345 / 0.00905 / 0.00455. Nanite off.
- Textures: BaseColor sRGB `TC_Default`; ORM and Masks linear `TC_Masks`; Normal `TC_Normalmap` with flip green OFF
  (DirectX), group `WeaponNormalMap`; Detail16 builds `PF_G16`. Full mip chains (4096 maps: 13 mips). With streaming on,
  the Metal and Chassis BC / N are resident at the top mip both at the hip and at ADS.
- Lightmap: index 1, Generate Lightmap UVs OFF on every LOD; the authored UV1 has 0 overlapping texels at 64 and 128 px
  as Unreal stores it (UV1 is snapped to the half-float grid at build time, so the stored UVs match the shipped ones).
- Collision: 10 hulls on SM_SR01, 1 on the magazine, 3 on the scope, all 32 vertices or fewer. Every LOD0 surface
  sample lies inside them.
- Sockets: 20 on SK_SR01 (on their bones), 20 on SM_SR01, 5 on the magazine, 5 on the scope; all within 0.001 cm /
  0.001 deg of the sidecars after `ue_import_sockets.py`.
- Scope: `SM_Att_Scope_LongRange` attached by its Mount at `Rail_Top` (+2 slots, +20.02 mm) lands where Blender
  puts it (error 0.001 cm or less). Sight is 57.6 mm above the bore and parallel to it (no zero built in: at 10 m the bore
  sits 5.76 cm under the cross).
- Clips: 8 clips with the sidecar frame counts; with `DefaultRecorderBoneCompression`, the runtime poses match the
  authored clips (0.0 mm on every rigid part). BipodDeploy ends / BipodStow starts with the legs at +90 deg on the
  12 deg splayed pins and 38 mm of extension. Bounds (+ the sidecar extension) hold every vertex at every frame of
  every clip.
- Skeleton: the SR01 skeleton is set compatible with `SK_AR01_Skeleton`. One ABP authored on the AR-01 skeleton drives
  the SR-01's bolt, trigger, selector and release. Nodes on the sniper-only bones (cheek riser, bipod) compile with a
  "bone not found" warning on the AR-01 skeleton and are ignored there.
- Magazine: SnapToTarget on `Mag` composes exactly. Seated fit: 0 intersecting triangles at LOD0-1. On the reload
  clips, only the catch nose touches the magazine (frame 2, while the paddle releases), 0.09 mm deep: within the
  Blender rule.
- Physics: `PHYS_SR01` = one body on `body`, 7 boxes + 1 capsule colliding plus a no-collision, no-mass bounds box,
  5.9 kg. Dropped 1 m in a ticking game world, SM_SR01 (level and rolled), the magazine and SK_SR01 come to rest
  without tunnelling.
- Asset warnings: 0 in every import / read-back / render / game log.

> **Branch claude/sniper-sr01-realism (realism round 2, 2026-10-14):** these files were re-exported with the rim-slab
> edges. The bytes fail form G5 / F1 (bipod clamp 0.003 mm into the seat) and have **not** been verified in Unreal. W5
> must be re-run on the final bytes before merging. See `WorkFiles/guns/sniper/REALISM_R2_REPORT.md`.
