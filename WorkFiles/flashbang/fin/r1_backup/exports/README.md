# Flashbang (stun grenade): Unreal Engine 5.8 static meshes

A throwable stun grenade: an olive-painted perforated steel canister with a brass inner tube, a dark steel base cap,
collar and square fuze housing, a spoon lever and a pull ring. Real-world scale (body 44 mm across, 166 mm tall), built
in Blender 5.2 and checked in Unreal 5.8.3.

## Files

| File | What it is |
|---|---|
| `SM_Flashbang.fbx` | **The main asset**: the whole grenade in one mesh (3 LODs, 4 collision hulls, 2 material slots) |
| `SM_Flashbang_Body.fbx` | Everything except the ring, pin and lever: the grenade in the hand, and the spent canister after it goes off |
| `SM_Flashbang_PullRing.fbx` | The pull ring and pin. Its pivot is the body's `Pin` socket |
| `SM_Flashbang_Lever.fbx` | The spoon lever. Its pivot is the body's `LeverHinge` socket |
| `*.sockets.json` | Sockets, LOD screen sizes and gameplay values for each mesh (see Import) |
| `Textures/T_Flashbang_BC.png` | Base colour, sRGB, 2048 |
| `Textures/T_Flashbang_ORM.png` | Linear: R ambient occlusion, G roughness, B metallic (0 or 1), 2048 |
| `Textures/T_Flashbang_N.png` | Normal map, **DirectX** (leave Flip Green Channel OFF), 2048 |
| `Textures/T_Flashbang_Paint_Detail.png` | The paint's recolour detail (sRGB, greyscale), 2048 |
| `Textures/Recolour/` | The 16-bit recolour detail and its data (used by the pack's paint material) |
| `MATERIALS_README.md` | How to change the paint colour |

All four meshes share one texture set and the same two material instances.

## Size, triangles, LODs

| Mesh | LOD0 / LOD1 / LOD2 triangles | LOD screen sizes |
|---|---|---|
| `SM_Flashbang` | 5,718 / 3,205 / 1,120 | 1.0 / 0.174 / 0.061 |
| `SM_Flashbang_Body` | 4,994 / 2,765 / 932 | 1.0 / 0.169 / 0.059 |
| `SM_Flashbang_PullRing` | 408 / 188 / 120 | 1.0 / 0.057 / 0.020 |
| `SM_Flashbang_Lever` | 316 / 252 / 68 | 1.0 / 0.128 / 0.045 |

The screen sizes follow the pack rule, so every piece switches LOD at the same distance (about 0.9 m and 2.5 m).
Nanite is off (a small hard-surface prop with authored LODs). UV0 is the texture atlas; UV1 is a separate lightmap
layout that ships in the FBX (Lightmap Coordinate Index 1).

## Import (legacy FBX importer)

1. Import each FBX with **Import Mesh LODs ON**, Auto Generate Collision OFF, One Convex Hull Per UCX ON,
   **Generate Lightmap UVs OFF** (the FBX brings its own UV1), Import Normals, Import Materials OFF.
2. FBX files with LODs cannot carry sockets into Unreal, so run the pack's `ue_import_sockets.py` with each mesh's
   `.sockets.json`: it adds the sockets at scale 1 and sets the LOD screen sizes.
3. Assign `MI_Flashbang_Paint` to slot 0 and `MI_Flashbang_Steel` to slot 1 (the ring and lever have only the Steel slot).

## Sockets (on `SM_Flashbang` and `SM_Flashbang_Body`)

| Socket | Where | Use |
|---|---|---|
| `Grip` | On the axis, 4.2 cm below the upper band (the palm centre) | Attach to the hand with the component's relative transform = inverse(Grip) |
| `Throw` | The centre of mass | Launch point and spin centre |
| `Pin` | At the pin's eye; +X points along the pull | Attach `SM_Flashbang_PullRing` here with an identity transform. Pull it along its local +X by 2.3 cm |
| `LeverHinge` | On the lever's hinge axis; +X out through the lever, +Y along the hinge | Attach `SM_Flashbang_Lever` here with an identity transform. It opens with a **positive pitch** |
| `Flash` | On the axis at the middle row of holes | Spawn the flash, light and smoke effects |

## Using the parts in gameplay

1. **Equip**: spawn `SM_Flashbang_Body` in the hand, attach the PullRing at `Pin` and the Lever at `LeverHinge`
   (identity). It looks exactly like `SM_Flashbang` (checked in Unreal: the parts land within 0.00002 mm).
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
- **Centre of mass**: Unreal computes it from the hulls, which puts it about 0.8 cm higher than the real grenade's
  (the steel cap is heavy and the head is mostly empty). For a truer tumble set the body's **Center Of Mass Offset**
  to about (0, 0, -0.8) cm.

## No markings

The grenade carries no text, numbers or logos, as in its reference.
