# Flashbang (stun grenade): Unreal Engine 5.8 static meshes

A throwable stun grenade: an olive-painted perforated steel canister (three rows of holes with a brass charge can
behind each hole column), a dark steel base cap with a notched end face, a collar and a square fuze housing with a
raised front panel, a channel-section spoon lever and a pull ring on a pin. Real-world scale (body 44 mm across,
165 mm tall), built in Blender 5.2 and checked in Unreal 5.8.3.

## Files

| File | What it is |
|---|---|
| `SM_Flashbang.fbx` | **The main asset**: the whole grenade in one mesh (3 LODs, 4 collision hulls, 2 material slots) |
| `SM_Flashbang_Body.fbx` | Everything except the ring, pin and lever: the grenade in the hand, and the spent canister after it goes off |
| `SM_Flashbang_PullRing.fbx` | The pull ring and pin. Its pivot is the body's `Pin` socket |
| `SM_Flashbang_Lever.fbx` | The spoon lever. Its pivot is the body's `LeverHinge` socket |
| `*.sockets.json` | Sockets, LOD screen sizes and gameplay values for each mesh (see Import, step 2) |
| `Textures/T_Flashbang_BC.png` | Base colour, sRGB, 2048 |
| `Textures/T_Flashbang_ORM.png` | Linear: R ambient occlusion, G roughness, B metallic (exactly 0 or 1), 2048 |
| `Textures/T_Flashbang_N.png` | Normal map, **DirectX** (leave Flip Green Channel OFF), 2048 |
| `Textures/Recolour/T_Flashbang_Paint_Detail16.png` | The paint's 16-bit linear recolour detail (import sRGB OFF, Grayscale), 2048 |
| `Textures/Recolour/recolour_maps.json`, `recolour_constants.json` | The paint material's constants (used by the pack's material build) |
| `MATERIALS_README.md` | How to change the paint colour |

All four meshes share one texture set and the same two material instances.

## Size, triangles, LODs

| Mesh | LOD0 / LOD1 / LOD2 triangles | LOD screen sizes |
|---|---|---|
| `SM_Flashbang` | 5,602 / 3,938 / 1,662 | 1.0 / 0.1768 / 0.0619 |
| `SM_Flashbang_Body` | 4,622 / 3,214 / 1,146 | 1.0 / 0.1693 / 0.0593 |
| `SM_Flashbang_PullRing` | 584 / 440 / 432 | 1.0 / 0.0612 / 0.0214 |
| `SM_Flashbang_Lever` | 396 / 284 / 84 | 1.0 / 0.1268 / 0.0444 |

The screen sizes follow the pack rule, so every piece switches LOD at the same distance (about 0.89 m and 2.54 m at
90 degrees horizontal field of view). The LODs are built from the same parts, not decimated: the holes stay open
and the ring keeps its shape at every LOD (measured: under 1 % of the grenade's pixels change at either switch).
Nanite is off (a small hard-surface prop with authored LODs).

## Import (legacy FBX importer)

1. Import each FBX as a Static Mesh with these settings (the pack's standard):
   - **Convert Scene ON**, **Force Front XAxis OFF**, **Convert Scene Unit ON**, **Import Uniform Scale 1.0**
     (the FBX is written in metres: with Convert Scene Unit OFF, Unreal's default, the meshes import 100 times too
     small and the pull ring is rejected as degenerate);
   - **Import Mesh LODs ON**, Combine Meshes OFF;
   - Normal Import Method **Import Normals**, Normal Generation Method **MikkTSpace**;
   - Auto Generate Collision **OFF**, **One Convex Hull Per UCX ON** (the FBX carries its hulls);
   - **Generate Lightmap UVs ON** (the FBX also carries a clean second UV set, used as the source if you turn it off);
   - Import Materials OFF, Import Textures OFF (the pack's material instances are assigned in step 3).
2. FBX files with LODs cannot carry sockets into Unreal, so run the pack's `ue_import_sockets.py` with each mesh's
   `.sockets.json`: it adds the sockets at scale 1 and sets the LOD screen sizes above.
3. Assign `MI_Flashbang_Paint` to slot 0 and `MI_Flashbang_Steel` to slot 1 (the ring and lever have only the Steel
   slot, slot 0). The pack's content folder already has all four meshes with these assigned.

Textures, if you import them yourself: BC sRGB ON (Default), ORM sRGB OFF (Masks), N sRGB OFF (Normalmap, Flip Green
OFF), Detail16 sRGB OFF (Grayscale). All are power-of-two with full mip chains.

## Sockets (on `SM_Flashbang` and `SM_Flashbang_Body`)

| Socket | Where | Use |
|---|---|---|
| `Grip` | On the axis, 7.0 cm up (the palm centre, 4.2 cm below the upper band) | Attach to the hand with the component's relative transform = inverse(Grip) |
| `Throw` | The centre of mass (0.08, 0.03, 7.22) cm | Launch point and spin centre |
| `Pin` | At the pin's head, where the ring passes through it; +X points along the pull | Attach `SM_Flashbang_PullRing` here with an identity transform. Pull it along its local +X by 2.3 cm |
| `LeverHinge` | On the lever's hinge axis; +X out through the lever, +Y along the hinge | Attach `SM_Flashbang_Lever` here with an identity transform. It opens with a **positive pitch** |
| `Flash` | On the axis at the middle row of holes | Spawn the flash, light and smoke effects |

## Using the parts in gameplay

1. **Equip**: spawn `SM_Flashbang_Body` in the hand, attach the PullRing at `Pin` and the Lever at `LeverHinge`
   (identity). It looks exactly like `SM_Flashbang` (checked in Unreal: the parts land on the assembled mesh within
   0.00002 mm).
2. **Pull the pin**: move the ring along its local +X by `pin_travel_mm` (23.1 mm), then attach it to the other hand
   or drop it with physics (mass 0.008 kg). The lever stays held.
3. **Throw**: detach the body with the throw velocity at `Throw`, and turn on **Continuous Collision Detection (CCD)**:
   at 15-20 m/s the grenade moves several times its own size per frame. Rotate the lever to about +100 deg pitch over
   0.05-0.08 s, then drop it with physics (mass 0.015 kg).
4. **Go off**: after the fuze delay, spawn the effects at `Flash`. The body stays in the world as the spent canister.

## Physics

- Mass: 0.30 kg for the whole grenade (a design value; the lever is 0.015 kg and the ring 0.008 kg).
- Collision: `SM_Flashbang` has 4 convex hulls (canister, fuze head, lever arm, and a thin one around the ring so it
  cannot sink into the floor). `SM_Flashbang_Body` has 2, each part mesh has 1.
- **Centre of mass**: Unreal computes it from the hulls, which puts it about 0.7 cm higher than the real grenade's
  (the steel cap is heavy and the head is mostly empty). For a truer tumble set the body's **Center Of Mass Offset**
  to about (0, 0, -0.7) cm.

## No markings

The grenade carries no text, numbers or logos, as in its reference.
