# Compact SMG SM-01: SK_SMG01, SM_SMG01, SM_SMG01_Mag

A compact polymer-framed submachine gun with a side-folding skeleton stock, folding iron sights and a straight
25-round polymer magazine, built for first- and third-person use. It is a rigged skeletal mesh whose bolt, charging
handle, trigger, selector, magazine release, magazine, stock and both sights move. A static twin is included for
pickups and world props, and the magazine is a separate mesh that you swap during reloads. The gun carries no names,
markings or logos.

This folder holds the shipped files. The Unreal Engine 5.8 import was checked on these exact bytes with the settings
below (see "Unreal import notes"). The SMG is also part of the pack's shared materials: its instances
`MI_SMG01_Metal`, `MI_SMG01_Furniture` and `MI_SMG01_Mag` were built and verified with the pack (see "Materials" and
`MATERIALS_README.md`).

## What is in this folder

| File | What it is |
|---|---|
| `SK_SMG01.fbx` | The gun as a skeletal mesh, LOD0 (48,236 triangles, magazine not included). Skeleton `SK_SMG01_Skeleton`: `root` plus 11 bones (`body`, `bolt`, `charging_handle`, `trigger`, `selector`, `mag_release`, `magazine`, `stock`, `sight_rear`, `sight_front`, `muzzle_device`) |
| `SK_SMG01_LOD1.fbx` .. `_LOD3.fbx` | LOD1-3 on the same skeleton (23,832 / 8,844 / 1,420 triangles). Import them as LODs of `SK_SMG01` and do not remove bones |
| `A_SMG01_Fire.fbx` | One shot: the trigger breaks, the bolt runs to the rear stop and back (60 fps, 6 frames) |
| `A_SMG01_Charge.fbx` | The charging handle pushes the bolt to the rear stop and both run forward (30 fps, 22 frames) |
| `A_SMG01_Reload.fbx` | Paddle pressed, magazine straight out, dropped, a new one straight in (30 fps, 55 frames) |
| `A_SMG01_ReloadEmpty.fbx` | Starts with the bolt held open; the reload, then a charge that releases the bolt (30 fps, 80 frames) |
| `A_SMG01_Selector.fbx` | Semi, Safe, Semi, Auto, Semi (30 fps, 30 frames) |
| `A_SMG01_StockFold.fbx` / `A_SMG01_StockUnfold.fbx` | The stock swings 180 degrees to the gun's right side and back (30 fps, 24 frames each). Fold ends folded; Unfold starts folded |
| `A_SMG01_SightFlip.fbx` | Both sights fold flat and come back up (30 fps, 20 frames) |
| `SK_SMG01.skeletal.json` | Sidecar: bones, sockets, LOD sizes, import settings, notifies, physics bodies, materials, mass, the shared long-gun data (`gun`) |
| `SM_SMG01.fbx` (+ `SM_SMG01.sockets.json`) | Static twin (stock extended) with the magazine merged in, LOD0-3 (52,536 / 25,252 / 9,532 / 1,444 triangles) and 8 convex hulls `UCX_SM_SMG01_LOD0_00..07` |
| `SM_SMG01_Mag.fbx` (+ `SM_SMG01_Mag.sockets.json`) | The removable magazine, LOD0-3 (4,300 / 1,420 / 688 / 24 triangles), 1 hull and 5 sockets. At every LOD it is the same mesh as the twin's merged magazine |
| `Physics/SK_SMG01_PhysicsProxy.fbx` | A proxy that rebuilds `PHYS_SMG01` exactly (see Physics below) |
| `Textures/` | `T_SMG01_Metal_*` (2048), `T_SMG01_Furniture_*` (4096), `T_SMG01_Mag_*` (1024): BC, ORM, N and Masks for each set; `Textures/Recolour/` holds the two polymer Detail16 maps, `recolour_maps.json` and `recolour_constants.json` (the pack's matched recolour settings) |

## Import into Unreal Engine 5.8

### Skeletal mesh and clips

1. Import `SK_SMG01.fbx` with **Import Normals**, *Convert Scene* on and *Force Front X Axis* off. Do not create a
   physics asset at import.
2. Import LOD1-3 onto `SK_SMG01` as LODs (`SkeletalMeshEditorSubsystem.import_lod`). They share the skeleton and the
   root. Set the LOD screen sizes to **1.0 / 0.28612 / 0.06082 / 0.03777** (the LOD-pop switch distances 2.3 / 11.0 /
   17.7 m at the mesh's radius including the bounds extension).
3. Import the eight `A_SMG01_*` clips onto `SK_SMG01_Skeleton`, each at its own frame rate, with *Use T0 As Ref Pose*
   off. Set every clip's **bone compression to `/Engine/Animation/DefaultRecorderBoneCompression`**. The project
   default (ACL) moves rigid parts by about 1 mm, which opens visible gaps.
4. The FBX files carry no notifies. Add them at the frames listed in the sidecar's `notifies`:

| Clip | Notifies (frame) |
|---|---|
| `A_SMG01_Fire` | `Fire` 1, `ShellEject` 3 (the bolt at the rear stop), `TriggerReset` 6 |
| `A_SMG01_Charge` | `ChargeRear` 10, `BoltRelease` 14 |
| `A_SMG01_Reload` | `MagRelease` 2, `MagOut` 10, `MagDrop` 17, `MagIn` 48 |
| `A_SMG01_ReloadEmpty` | as Reload, then `ChargeRear` 67, `BoltRelease` 71 |
| `A_SMG01_StockFold` / `A_SMG01_StockUnfold` | `StockUnlock` 1, `StockLocked` 24 |

5. Set the mesh's bounds extension from the sidecar's `import.bounds_extension_cm`: **Positive (0, 24.752, 0.257) cm,
   Negative (0.749, 0, 0) cm**. Unreal stores LOD0's bind-pose box as the bounds, and the folded stock swings 24.9 cm
   past it to the right; with the extension every vertex of every LOD stays inside the bounds on every frame of every
   clip, with the stock in either state and the sights folded.

### Selector state in the clips

The bind pose and the static twin show the selector on **Semi (0 degrees)**, as the design sheet draws it. Safe is
-63.4 degrees and Auto +45 degrees (the detents). `A_SMG01_Fire`, `A_SMG01_Charge` and `A_SMG01_ReloadEmpty` **hold the
selector at Auto from the first frame to the last**, because a safe selector blocks the trigger and the bolt; the
reload and stock clips keep it on Semi. To show the player's real fire mode, blend the `selector` bone per bone in the
weapon's Anim Blueprint (*Layered blend per bone*, branch `selector`) from a pose of `A_SMG01_Selector`.

### Stock states

The stock folds 180 degrees about the hinge to lie along the gun's right side; a moulded lug on the stock clips under
the ejection-port catch. Play `A_SMG01_StockFold` / `A_SMG01_StockUnfold`, or hold the last frame of the fold for a
folded gun. The static twin `SM_SMG01` is the extended state. Folded, the gun is 383.6 mm long and its centre of mass
moves to 100.0 / -10.0 / 83.1 mm (`gun.center_of_mass_folded_mm`).

### Shared long-gun Anim Blueprint

`SK_SMG01_Skeleton` is compatible with the AR-01's skeleton (`gun.compatible_with`: add `SK_AR01_Skeleton` under
*Compatible Skeletons*). One Anim Blueprint authored on `SK_AR01_Skeleton` drove both guns in Unreal (W5 U2b) when it
takes normalized inputs (trigger 0..1, bolt 0..1, selector detent index, release 0..1) and maps them through each
gun's `gun.abp_angle_table` (SMG: trigger 0..13 degrees, bolt 0..67.9 mm, detents Safe -63.4 / Semi 0 / Auto 45,
release 0..-11 degrees). Its node on the SMG-only `stock` bone compiles with the warning "Bone stock not found in
Skeleton" and raises nothing at runtime; for a warning-free class Blueprint drive the SMG-only bones (`stock`,
`sight_front`, `charging_handle`) by clips on the weapon slot or a linked layer.

### First person (UE 5.8 First Person rendering)

Use two components per weapon and per magazine: `FP_Weapon` and `TP_Weapon` (both `SK_SMG01`), and `FP_Mag` and
`TP_Mag` (both `SM_SMG01_Mag`, attached to the `Mag` socket). On every first-person component set
*First Person Primitive Type* = **FirstPerson** and **ForcedLodModel = 1** (always LOD0). The third-person components
keep the normal LOD switching.

### Sockets

The skeletal sidecar lists 21 sockets with their bones (`Grip`, `SupportHand`, `Trigger`, `Muzzle`, `MuzzleSeat`,
`Sight`, `SightFront`, `Mag`, `MagInsertStart`, `ShellEject`, `ChargingHandle`, `Selector`, `MagRelease`, `Rail_Top`,
`Rail_Bottom`, `Stock`, `Shoulder`, `SlingFront`, `SlingRear`, `CenterOfMass`, `Holster`). `Shoulder` and `SlingRear`
ride on the `stock` bone, so they follow the fold. Recreate them from `SK_SMG01.skeletal.json` (locations in cm,
Unreal rotators). For the static meshes, Unreal 5.8 drops the FBX sockets of any file with a LOD group: recreate them
from the `.sockets.json` sidecars with `unreal.new_object(unreal.StaticMeshSocket, outer=mesh)`, and set the LOD
screen sizes from the sidecars too (`SM_SMG01` 1.0 / 0.25 / 0.05314 / 0.033; `SM_SMG01_Mag` 1.0 / 0.08465 / 0.01799 /
0.01117, derived from the gun's so an attached magazine switches with it).

### Magazine and reloads

`SM_SMG01_Mag` snaps to the `Mag` socket with a zero relative transform. The reload path is **straight**:
`MagInsertStart` (68.2 mm below the seat) to `Mag`, a lerp along the magazine's -Z with the rotation constant (no rock).
`A_SMG01_Reload` moves the `magazine` bone along that path, so a magazine attached to that bone follows it. For a
hand-held magazine (on `hand_l`), copy the weapon clip's `MagOut` and `MagIn` frames to the character montage.

## Materials

| Slot | Instance | Master | Colour control |
|---|---|---|---|
| `M_SMG01_Metal` (0 on `SK_SMG01` and `SM_SMG01`) | `MI_SMG01_Metal` | `M_Steel_Master` | Steel Tint (white = as shipped) |
| `M_SMG01_Furniture` (1) | `MI_SMG01_Furniture` | `M_Fabric_Master` | Colour, with *Use Original Baked Colours* turned off |
| `M_SMG01_Mag` (2 on `SM_SMG01`, 0 on `SM_SMG01_Mag`) | `MI_SMG01_Mag` | `M_Fabric_Master` | Colour, with *Use Original Baked Colours* turned off |

Assign the instances by slot name. The shipped polymer shows its baked colour map exactly. To recolour the gun (tan,
OD green, FDE or anything else), turn off *Use Original Baked Colours* on `MI_SMG01_Furniture` and `MI_SMG01_Mag` (or
copies) and set the same **Colour** on both; the moulded texture and the wear follow. The metal parts stay phosphated
steel. Details, map settings and the measured results are in `MATERIALS_README.md`.

## Collision

- `SM_SMG01` collides through 8 convex hulls `UCX_SM_SMG01_LOD0_00..07`, and `SM_SMG01_Mag` through 1,
  `UCX_SM_SMG01_Mag_LOD0_00`. Import with *One Convex Hull per UCX* on and *Auto Generate Collision* off. Every LOD0
  surface point lies inside the hulls (measured in Blender and in Unreal).
- `SK_SMG01` collides through `PHYS_SMG01` (below).
- **In hand:** while the gun and its magazine are attached to the character, set their components to *No Collision*
  (or a query-only weapon profile) and *Simulate Physics* off, so they never push the character's capsule. Turn
  collision and physics on only for a dropped or world pickup (`SM_SMG01`, or `SK_SMG01` with `PHYS_SMG01`).
- **Centre of mass:** 47.5 / 0.7 / 83.1 mm from the `body` origin, stock extended (the `CenterOfMass` socket, computed
  by the build); folded 100.0 / -10.0 / 83.1 mm. `PHYS_SMG01` uses a mass override of 2.5 kg.

## Physics

`PHYS_SMG01` has one body on `body` (2.5 kg) made of the shapes in the sidecar's `physics_bodies`: 8 collision shapes
and one **bounds-envelope box with no collision and no mass**. A skeletal component with physics bodies takes its
bounds from the physics asset, so the envelope (the mesh's extended bounds, both stock states) keeps a dropped gun with
the stock folded inside its own bounds and gives every route the same LOD radius (measured in Unreal: 0 cm outside,
LOD radius 37.54 cm). To rebuild it, import `Physics/SK_SMG01_PhysicsProxy.fbx` onto `SK_SMG01_Skeleton` with
*Create Physics Asset* on (it makes exactly one body on `body`), replace that body's shapes with the sidecar's (keep
each element's collision and mass flags), then rename the asset to `PHYS_SMG01`, assign it to `SK_SMG01` and delete
the proxy mesh. The physics proxy is not a render mesh: it exists only to rebuild the body.

## Textures

| Set | Size | Covers |
|---|---|---|
| Metal | 2048 | Rails, sights, barrel and nut, muzzle device, bolt, charging handle, selector, trigger, paddle, pins |
| Furniture | 4096 | Receiver shells, grip frame and cover, magwell, stock and butt pad (+ Detail16 2048 for the recolour) |
| Mag | 1024 | The magazine (+ Detail16 1024) |

BC is sRGB. ORM is linear (R ambient occlusion, G roughness, B metallic). N is a DirectX-convention normal map, stored
as 16-bit PNG. Masks are linear (R edge wear, G handling, B cavity, A refinishable). All maps are square powers of two.
Keep full mips. Compression: BC Default (BC1) for the metal, **BC7 for `T_SMG01_Furniture_BC` and `T_SMG01_Mag_BC`**
(the shipped polymer shows those maps directly, and BC1 shifted the dark wear by up to 5-8 levels); ORM Masks; N
Normalmap; Detail16 Grayscale (G16). In a game, use texture group `Weapon` for BC and ORM and `WeaponNormalMap` for N.
Materials and colours: see `MATERIALS_README.md`.

## Good to know

- **Bolt travel.** The bolt and the charging handle travel 67.9 mm (`gun.abp_angle_table.bolt_mm`).
- **Lightmaps.** Every LOD carries an authored lightmap UV (UV1, no overlaps at 64 and 128 px). Use it (*Generate
  Lightmap UVs* off) for static lighting.
- **Blender users.** Blender's FBX exporter writes each bone's pose at a clip's first frame as that bone's default. For
  every bone except a selector held at Auto, that pose is the bind pose. Blender's importer reads the defaults as the
  rest pose, so a held selector re-imports at Auto. Unreal plays the baked curves and is not affected. In Blender,
  read a clip's absolute bone matrices (its own armature's `pose.bones[...].matrix`).
- Not tested yet: a full in-game first-person weapon Blueprint (the owner-only visibility of the two components),
  mobile, Nanite (the meshes import and were checked with Nanite off), and the hand fit on the game's player character
  in Unreal (it was fitted on the player MetaHuman in Blender; `gun.hand_offset` records it).

## Unreal import notes (UE 5.8.3, measured)

- Everything above imports as described (W5, 34 of 34 gates, fresh processes, sha256 checked at start and end): 4 LODs
  with triangles equal in Blender, the FBX and Unreal at every LOD; the 21 + 21 + 5 sockets on the right bones at scale
  1 (within 0.001 cm); the eight clips (rigid parts within 0.01 cm / 0.01 degrees of the authored motion, notifies on
  their frames); PHYS_SMG01 (it drops and rests with the stock extended and folded, and the runtime bounds hold every
  vertex); the hulls; full mip chains; the gun's Metal and Furniture maps stay at their top mip at the hip and at ADS
  (the separate magazine's 1024 maps stream at 512 at the hip, Unreal's wanted size); 0 asset warnings at import. First-person components cast no world shadow and stay on LOD0.
- The pack's material build (`run_build.sh smg01_1013b`, the pack's validation project) imported the same bytes with
  the same settings: every pack gate passed, the sockets, 4 LODs, 8 clips and PHYS_SMG01 came through, and every LOD
  section resolves to the pack's instances.
- Unreal's stored copy of the authored UV1 shows 17-22 overlapping pixels at 1024 px on `SM_SMG01` LOD0-2 (0 at 64 and
  128 px, the lightmap's own resolution). Higher lightmap resolutions than 128 px are not recommended.
