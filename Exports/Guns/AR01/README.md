# Assault Rifle AR-01: SK_AR01, SM_AR01, SM_AR01_Mag

A stamped-receiver 7.62x39 assault rifle with walnut furniture, built for first- and third-person use. It is a rigged
skeletal mesh whose bolt, trigger, selector, magazine catch, rear sight and magazine move. A static twin is included
for pickups and world props, and the magazine is a separate mesh that you swap during reloads. The gun carries no
names, markings or logos.

This folder holds the shipped files. The Unreal Engine 5.8 import was checked with the settings below (see "Unreal
import notes"). The rifle is also part of the pack's shared materials: its instances `MI_AR01_Metal`,
`MI_AR01_Furniture` and `MI_AR01_Mag` were built and verified with the pack (see "Materials" and
`MATERIALS_README.md`).

## What is in this folder

| File | What it is |
|---|---|
| `SK_AR01.fbx` | The rifle as a skeletal mesh, LOD0 (48,386 triangles, magazine not included). Skeleton `SK_AR01_Skeleton`: `root` plus 8 bones (`body`, `bolt`, `trigger`, `selector`, `mag_release`, `magazine`, `sight_rear`, `muzzle_device`) |
| `SK_AR01_LOD1.fbx` .. `_LOD3.fbx` | LOD1-3 on the same skeleton (22,462 / 8,450 / 1,076 triangles). Import them as LODs of `SK_AR01` and do not remove bones |
| `A_AR01_Fire.fbx` | One shot: the trigger breaks, the carrier runs to the rear stop and back (60 fps, 8 frames) |
| `A_AR01_Charge.fbx` | The charging handle is pulled to the rear stop, held, then released (30 fps, 22 frames) |
| `A_AR01_Reload.fbx` | Catch pressed, magazine rocked out, dropped, a new one rocked in (30 fps, 60 frames) |
| `A_AR01_ReloadEmpty.fbx` | The reload followed by a charge (30 fps, 84 frames) |
| `A_AR01_Selector.fbx` | Safe, then Auto, then Semi, then back to Safe (30 fps, 30 frames) |
| `SK_AR01.skeletal.json` | Sidecar: bones, sockets, LOD sizes, import settings, notifies, physics bodies, materials, mass |
| `SM_AR01.fbx` (+ `SM_AR01.sockets.json`) | Static twin with the magazine merged in, LOD0-3 (55,052 / 24,460 / 9,098 / 1,324 triangles) and 7 convex hulls `UCX_SM_AR01_LOD0_00..06` |
| `SM_AR01_Mag.fbx` (+ `SM_AR01_Mag.sockets.json`) | The removable magazine, LOD0-3 (6,666 / 1,998 / 648 / 248 triangles) and 2 hulls. At every LOD it is the same mesh as the twin's merged magazine |
| `Physics/SK_AR01_PhysicsProxy.fbx` | A proxy that rebuilds `PHYS_AR01` exactly (see Physics below) |
| `Textures/` | `T_AR01_Metal_*` (4096), `T_AR01_Furniture_*` (2048), `T_AR01_Mag_*` (1024): BC, ORM, N and Masks for each set; `Textures/Recolour/` holds the walnut Detail16 map, `recolour_maps.json` and `recolour_constants.json` (the pack's matched recolour settings) |

## Import into Unreal Engine 5.8

### Skeletal mesh and clips

1. Import `SK_AR01.fbx` with **Import Normals**, *Convert Scene* on and *Force Front X Axis* off. Do not create a
   physics asset at import.
2. Import LOD1-3 onto `SK_AR01` as LODs (`SkeletalMeshEditorSubsystem.import_lod`). They share the skeleton and the
   root. Set the LOD screen sizes to **1.0 / 0.30 / 0.12 / 0.04**.
3. Import the five `A_AR01_*` clips onto `SK_AR01_Skeleton`, each at its own frame rate, with *Use T0 As Ref Pose* off.
   Set every clip's **bone compression to `/Engine/Animation/DefaultRecorderBoneCompression`**. The project default
   (ACL) moves rigid parts by about 1 mm, which opens visible gaps.
4. The FBX files carry no notifies. Add them at the frames listed in the sidecar's `notifies`:

| Clip | Notifies (frame) |
|---|---|
| `A_AR01_Fire` | `Fire` 1, `ShellEject` 3 (the carrier at the rear stop), `TriggerReset` 8 |
| `A_AR01_Charge` | `ChargeRear` 12, `BoltRelease` 18 |
| `A_AR01_Reload` | `MagRelease` 2, `MagOut` 15, `MagDrop` 20, `MagIn` 53 |
| `A_AR01_ReloadEmpty` | as Reload, then `ChargeRear` 74, `BoltRelease` 80 |
| `A_AR01_Selector` | `SelectorAuto` 4, `SelectorSemi` 12, `SelectorAuto` 22, `SelectorSafe` 28 |

5. Set the mesh's **Negative Bounds Extension** to **(0, 0.378, 0) cm** (the sidecar's `import.bounds_extension_cm`;
   Positive stays 0). Unreal stores LOD0's bind-pose box as the bounds, and LOD2 reaches 2.8 mm past it on the left;
   with the extension every vertex of every LOD stays inside the bounds on every frame of every clip.

### Selector state in the clips

The safety lever blocks the trigger and the carrier on the real rifle. So `A_AR01_Fire`, `A_AR01_Charge`,
`A_AR01_Reload` and `A_AR01_ReloadEmpty` **hold the selector at Auto (16 degrees) from the first frame to the last**.
The bind pose and the static twin keep it on Safe, as the reference draws it. To show the player's real fire mode,
blend the `selector` bone per bone in the weapon's Anim Blueprint (*Layered blend per bone*, branch `selector`) from
a pose taken from `A_AR01_Selector`: frame 0 is Safe, frame 8 Auto, frame 18 Semi.

### First person (UE 5.8 First Person rendering)

Use two components per weapon and per magazine: `FP_Weapon` and `TP_Weapon` (both `SK_AR01`), and `FP_Mag` and
`TP_Mag` (both `SM_AR01_Mag`, attached to the `Mag` socket). On every first-person component set
*First Person Primitive Type* = **FirstPerson** and **ForcedLodModel = 1** (always LOD0). The third-person components
keep the normal LOD switching.

### Sockets

The skeletal sidecar lists 17 sockets with their bones (`Grip`, `SupportHand`, `Trigger`, `Muzzle`, `MuzzleSeat`,
`Sight`, `Mag`, `MagRockStart`, `MagInsertStart`, `ShellEject`, `ChargingHandle`, `Selector`, `MagRelease`,
`Shoulder`, `SlingRear`, `CenterOfMass`, `Holster`). Recreate them from `SK_AR01.skeletal.json` (locations in cm,
Unreal rotators). For the static meshes, Unreal 5.8 drops the FBX sockets of any file with a LOD group: recreate them
from the `.sockets.json` sidecars with `unreal.new_object(unreal.StaticMeshSocket, outer=mesh)`, and set the LOD
screen sizes from the sidecars too.

### Magazine and reloads

`SM_AR01_Mag` snaps to the `Mag` socket with a zero relative transform. A reload goes `MagInsertStart` (lerp) to
`MagRockStart`, then rotates 8 degrees about the front-lug hook into `Mag`. `A_AR01_Reload` moves the `magazine` bone
along that path, so a magazine attached to that bone follows it. For a hand-held magazine (on `hand_l`), copy the
weapon clip's `MagOut` and `MagIn` frames to the character montage.

## Materials

| Slot | Instance | Master | Colour control |
|---|---|---|---|
| `M_AR01_Metal` (0 on `SK_AR01` and `SM_AR01`) | `MI_AR01_Metal` | `M_Steel_Master` | Steel Tint (white = as shipped) |
| `M_AR01_Furniture` (1) | `MI_AR01_Furniture` | `M_Fabric_Master` | Colour, with *Use Original Baked Colours* turned off |
| `M_AR01_Mag` (2 on `SM_AR01`, 0 on `SM_AR01_Mag`) | `MI_AR01_Mag` | `M_Steel_Master` | Steel Tint |

Assign the instances by slot name. The shipped wood shows its baked colour map exactly. To recolour it, turn off *Use
Original Baked Colours* on `MI_AR01_Furniture` (or a copy) and pick **Colour**; the grain and wear follow. Details,
map settings and the measured results are in `MATERIALS_README.md`.

## Collision

- `SM_AR01` collides through 7 convex hulls `UCX_SM_AR01_LOD0_00..06`, and `SM_AR01_Mag` through 2,
  `UCX_SM_AR01_Mag_LOD0_00..01`. Import with *One Convex Hull per UCX* on and *Auto Generate Collision* off. Every
  LOD0 surface point lies inside the hulls (measured in Unreal).
- `SK_AR01` collides through `PHYS_AR01` (below).
- **In hand:** while the rifle and its magazine are attached to the character, set their components to *No Collision*
  (or a query-only weapon profile) and *Simulate Physics* off, so they never push the character's capsule. Turn
  collision and physics on only for a dropped or world pickup (`SM_AR01`, or `SK_AR01` with `PHYS_AR01`).
- **Centre of mass:** 163.0 / 0.1 / 74.9 mm from the `body` origin (the `CenterOfMass` socket, computed by the
  build); `PHYS_AR01` uses a mass override of 3.1 kg.

## Physics

`PHYS_AR01` has one body on `body` (3.1 kg) made of the shapes in the sidecar's `physics_bodies`. To
rebuild it, import `Physics/SK_AR01_PhysicsProxy.fbx` onto `SK_AR01_Skeleton` with *Create Physics Asset* on (it makes
exactly one body on `body`), replace that body's shapes with the sidecar's, then rename the asset to `PHYS_AR01`,
assign it to `SK_AR01` and delete the proxy mesh. The physics proxy is not a render mesh: it exists only to rebuild the body.

## Textures

| Set | Size | Covers |
|---|---|---|
| Metal | 4096 | Receiver, cover, sights, barrel, gas system, bolt and carrier, small parts |
| Furniture | 2048 | Stock, pistol grip, both handguards (+ Detail16 1024 for the walnut recolour) |
| Mag | 1024 | The magazine |

BC is sRGB. ORM is linear (R ambient occlusion, G roughness, B metallic). N is a DirectX-convention normal map, stored
as 16-bit PNG. Masks are linear (R edge wear, G handling, B cavity, A refinishable). All maps are square powers of two.
Keep full mips. Compression: BC Default (BC1), except `T_AR01_Furniture_BC`, which uses **BC7** because the shipped
wood shows that map directly; ORM Masks; N Normalmap; Detail16 Grayscale (G16). In a game, use texture group `Weapon`
for BC and ORM and `WeaponNormalMap` for N. Materials and colours: see `MATERIALS_README.md`.

## Good to know

- **Bolt at full travel.** The carrier slides 103.25 mm. The rotating bolt (with its extractor) rides in it and its head
  runs in a bore in the trunnion up to the barrel's breech. With the bolt back, the port shows the open receiver and the
  trunnion's raised block.
- **Grip checkering** is a crisp normal map baked from modelled cuts, on every LOD. Whether LOD0 should carry the cuts
  as geometry is an open decision for the owner.
- **Blender users.** Blender's FBX exporter writes each bone's pose at a clip's first frame as that bone's default. For
  every bone except a selector held at Auto, that pose is the bind pose. Blender's importer reads the defaults as the
  rest pose, so a held selector re-imports at Safe. Unreal plays the baked curves and is not affected. In Blender,
  read a clip's absolute bone matrices (its own armature's `pose.bones[...].matrix`).
- Not tested yet: a full in-game first-person weapon Blueprint (the owner-only visibility of the two components), mobile,
  Nanite (the meshes import and were checked with Nanite off), and the hand fit on the game's player character.

## Unreal import notes (UE 5.8, measured)

- Everything above imports as described: 4 LODs, the 17 + 17 + 5 sockets on the right bones at scale 1, the five clips
  (rigid parts within 0.0001 mm of the authored motion, notifies on their frames), PHYS_AR01 (it drops and rests), the
  hulls (every LOD0 surface point inside them), full mip chains, and the textures stay at their top mip at the hip and
  at ADS. First-person components cast no world shadow and stay on LOD0.
- With *Remove Degenerates* on (the import default) Unreal drops the static meshes' sub-0.005 mm^2 triangles: 4,584 /
  580 / 122 of `SM_AR01` LOD0-2 and 772 / 33 of `SM_AR01_Mag` LOD0-1 (micro bevel strips; invisible). The skeletal
  import keeps them. Importing the statics logs "nearly zero tangents / bi-normals" and, for `SM_AR01`, "degenerate tangent
  bases" for a few dozen vertices on those strips and on coarse-LOD faces. Both are known open items of this version.
- The pack's material build (`run_build.sh ar01_1009b`, the pack's validation project) imported the same bytes with
  the same settings: every pack gate passed, the 17 + 17 + 5 sockets and 4 LODs came through, and every LOD section
  resolves to the pack's instances.
- *Generate Lightmap UVs* makes a lightmap UV with a few overlapping texels on `SM_AR01` LOD1-3 at the default 64 px
  lightmap resolution. Projects with dynamic lighting only are not affected.
