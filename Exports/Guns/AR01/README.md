# Assault Rifle AR-01: SK_AR01, SM_AR01, SM_AR01_Mag

A stamped-receiver 7.62x39 assault rifle with walnut furniture, built for first- and third-person use. It is a rigged
skeletal mesh whose bolt, trigger, selector, magazine catch, rear sight and magazine move. A static twin is included
for pickups and world props, and the magazine is a separate mesh that you swap during reloads. The gun carries no
names, markings or logos.

This folder holds the shipped files. The Unreal import, its checks and the material instances come in a later stage,
so this file describes the FBX files and the settings they need.

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
| `Textures/` | `T_AR01_Metal_*` (4096), `T_AR01_Furniture_*` (2048), `T_AR01_Mag_*` (1024): BC, ORM, N and Masks for each set; `Textures/Recolour/` holds the walnut Detail16 map and the recolour data |

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

5. The bounds do not need an extension: every vertex stays inside the bind-pose box on every frame of every clip.

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

## Physics

`PHYS_AR01` has one body on `body` (3.1 kg) made of the shapes in the sidecar's `physics_bodies`. To
rebuild it, import `Physics/SK_AR01_PhysicsProxy.fbx` onto `SK_AR01_Skeleton` with *Create Physics Asset* on (it makes
exactly one body on `body`), replace that body's shapes with the sidecar's, then rename the asset to `PHYS_AR01`,
assign it to `SK_AR01` and delete the proxy mesh. The static twin collides through its 7 `UCX` hulls and the magazine
through its 2.

## Textures

| Set | Size | Covers |
|---|---|---|
| Metal | 4096 | Receiver, cover, sights, barrel, gas system, bolt and carrier, small parts |
| Furniture | 2048 | Stock, pistol grip, both handguards (+ Detail16 1024 for the walnut recolour) |
| Mag | 1024 | The magazine |

BC is sRGB. ORM is linear (R ambient occlusion, G roughness, B metallic). N is a DirectX-convention normal map, stored
as 16-bit PNG. Masks are linear (R edge wear, G handling, B cavity, A refinishable). All maps are square powers of two.
Use texture group `Weapon` for BC and ORM and `WeaponNormalMap` for N, and keep full mips. Materials and colours:
see `MATERIALS_README.md`.

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
- Not tested yet: the Unreal import itself and the in-game first-person setup (the next stage), mobile, Nanite.
