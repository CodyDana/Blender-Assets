# Shell Casing 7.62x39: SM_Casing_762x39

A spent 7.62x39 steel cartridge case with a lacquer finish, made as the ejected-casing mesh for the gun line (first
user: the Assault Rifle AR-01, shooting prototype step G1). It has the real case profile, an open mouth with wall
thickness, a struck Berdan primer and a little firing wear. It carries no headstamp, names or markings.

## What is in this folder

| File | What it is |
|---|---|
| `SM_Casing_762x39.fbx` | Static mesh with an FBX LodGroup: LOD0 528 / LOD1 112 / LOD2 48 triangles. One material slot, `M_Casing_762x39`. No collision hull (Niagara collides with scene depth or distance fields) |
| `SM_Casing_762x39.sockets.json` | Sidecar: sockets `Base` and `Mouth`, plus the LOD screen sizes |
| `Textures/T_Casing_762x39_BC.png` | Base colour, 512, sRGB |
| `Textures/T_Casing_762x39_ORM.png` | R = AO, G = roughness, B = metallic, 512, linear |
| `Textures/T_Casing_762x39_N.png` | Normal map, 512, **DirectX** (green down) |

Source: `Assets/Guns/Casing_762x39.blend`. Build: `Scripts/guns/casing/build_casing.py`, which runs every gate and then
exports through `Scripts/pipeline`. Check of the exported bytes in a fresh process: `Scripts/guns/casing/verify_casing.py`.
Reports: `WorkFiles/guns/casing/casing_build.json`, `casing_verify.json`.

## Frame, pivot, sockets

- The case axis is **+X** in Unreal and in Blender. The base is at -X and the mouth at +X.
- The **pivot is the centre of mass** of the real hollow case, 12.23 mm from the base on the axis. A Niagara mesh
  particle therefore tumbles about the right point. The estimated mass is 7.0 g of steel.
- Sockets, with X along the axis toward the mouth and no rotation:

| Socket | Location (cm) | Use |
|---|---|---|
| `Base` | (-1.2234, 0, 0) | the head centre (primer) |
| `Mouth` | (2.6466, 0, 0) | the mouth centre |

Unreal 5.8 drops FBX sockets from a file that has LODs, so apply the sidecar after import with
`Scripts/pipeline/ue_import_sockets.py`.

## Dimensions (C.I.P., checked within 0.05 mm)

Every case dimension comes from the cartridge (maximum) column of C.I.P. TAB. I "7,62 x 39" (1989, revised 2002). The
build checks LOD0 against these numbers, and `verify_casing.py` checks them again on the re-imported FBX. Every
measured error is below 0.001 mm and below 0.001 deg.

| Symbol | Value | Where |
|---|---|---|
| L3 | 38.70 | case length |
| R1 / P1 | 11.35 | rim diameter; body diameter at E = 3.20 |
| R | 1.50 | base to the extractor-groove floor |
| E1 | 9.56 | extractor-groove diameter; floor width e = 1.00 |
| f | 0.25 | 45 deg base chamfer |
| beta / delta | 45 deg / 51deg58' | rim front cone; groove front flank |
| P2 | 10.07 at L1 = 30.50 | shoulder start |
| H1 / H2 | 8.60 at L2 = 33.00 / at L3 | neck / mouth |
| alpha | 32deg46' | shoulder, included angle |

The C.I.P. sheet does not give these values, so they come from common 7.62x39 practice:

| Detail | Value | How it is modelled |
|---|---|---|
| Neck bore | 7.92 mm (the projectile diameter), wall 0.34 mm at the mouth | geometry |
| Berdan primer | 5.50 mm | texture |
| Firing-pin dimple | 1.6 mm wide, 0.30 mm deep | geometry |

The case is not shown expanded from firing. A fired steel case springs back to within about 0.1 mm of these numbers,
so the model keeps the cartridge values the plan gives.

**Facets:** the diameters are measured at the profile vertices. LOD0 has 24 segments, so the width across two flat
faces is 0.10 mm smaller (cos 7.5 deg). In a studio close-up you can see the 24-sided outline at the rim and the
mouth. At game sizes you cannot.

**Fillets:** the r1 4.0 / r2 3.0 fillets at the shoulder are shaded, not modelled. The custom normals keep the body
flat-shaded and make the shoulder band shade round, so P2 and H1 stay exact.

**Bore:** the bore is a soot-black cone from the mouth down to the web. Looking into a 7.9 mm mouth you see a dark
hole either way, and it saves two rings of triangles.

## LODs and screen sizes

| LOD | Triangles | Segments | What it keeps |
|---|---|---|---|
| 0 | 528 | 24 | full profile: dimple, chamfer, rim, groove, body, shoulder, neck, lip, bore |
| 1 | 112 | 8 | rim and V groove, body, shoulder, neck; the mouth is a shallow dark cone |
| 2 | 48 | 6 | body, shoulder, neck, dark mouth |

The sidecar's screen sizes are **1.0 / 0.05 / 0.015**, chosen for this object instead of the house 1.0 / 0.5 / 0.25.
The case's bounds sphere is about 0.09 of the screen at 0.4 m (ADS, FOV 55) and about 0.04 at 1 m. So LOD0 shows
inside about 0.8 m, LOD1 out to about 2.5 m, and LOD2 beyond. The house sizes would keep a casing on its 6-sided LOD2
everywhere except a few centimetres from the lens.

Triangle budget: the plan (4.2) estimated about 400 / 120 / 40 at 24 segments. The C.I.P. head profile with 24
segments needs 528, made of 10 bands and 2 caps. This build's budget is 540 / 130 / 50. LOD1 and LOD2 meet the plan's
figures.

Unreal degenerate rule: no triangle at any LOD is under 0.005 mm2, and none is under the 0.01 mm2 margin. The smallest
triangles are 0.089 / 1.31 / 5.55 mm2 (LOD0 / 1 / 2). There are no edges under 0.05 mm, no needles and no strips.
Blender's MikkTSpace finds 0 collapsed, zero-angle or edge-on tangent corners. Unreal's own import is checked at
prototype step G2.

## Material

There is one texture set, laid out as the revolve UV: U is the angle around the axis, and V runs along the profile
from the base centre to the bore. Unreal settings: BC sRGB; ORM linear (Compression *Masks*); N as a DirectX normal
map. All three are power of two with full mips.

| Area | Base colour (sRGB) | Roughness | Metallic |
|---|---|---|---|
| Lacquered steel (body, rim, groove, head face) | 0.30, 0.295, 0.20 | 0.26 | 0.9 |
| Primer cup | 0.70, 0.52, 0.34 | 0.34 | 1.0 |
| Primer sealant ring | 0.47, 0.10, 0.13 | 0.42 | 0.0 |
| Bare steel (extractor bite, ejector scuff, rim wear) | 0.50, 0.49, 0.47 | 0.27 | 1.0 |
| Soot (shoulder and neck, uneven around the case) | 0.115, 0.11, 0.105 | 0.78 | 0.15 |
| Bore | 0.055, 0.053, 0.05 | 0.92 | 0.0 |

If the textures are not used (plan 4.2's "3-parameter material"), use the lacquer row as constants: base colour,
roughness and metallic. A **brass variant** is a single colour change: base colour about (0.78, 0.60, 0.30) sRGB,
roughness 0.3, metallic 1.0. Pack recolouring (`M_Steel_Master`) can be wired later by the game-side import, as plan
option O2 allows.

## Unreal import (UE 5.8)

1. Import `SM_Casing_762x39.fbx` with **Import Mesh LODs ON**, Import Normals, no collision (*Auto Generate Collision*
   off), and Combine Meshes off.
2. Apply the sidecar with `ue_import_sockets.py`. It adds the `Base` and `Mouth` sockets and the LOD screen sizes.
3. Import the three textures with the settings above.
4. In the casing Niagara system (`NS_Gun_CasingEject`, plan 4.2), use this mesh in a Mesh Renderer. The pivot is
   already the centre of mass.

## Files as built (sha256, 2026-10-09)

| File | sha256 |
|---|---|
| `SM_Casing_762x39.fbx` | `33eba7693209ff8034b3e726297e9b831ecbb122a2a3a95051c4350dfeb77e6f` |
| `SM_Casing_762x39.sockets.json` | `7056252705c22b338ba3e91d7b0b4f2ccdf48f00ff6f7b9f4c67438b679af65b` |
| `Textures/T_Casing_762x39_BC.png` | `5c47768e69eacc3f9c8ac6783f11542efe6e0aea4a9ae5f91b0f5c0a304b1252` |
| `Textures/T_Casing_762x39_ORM.png` | `064231928813d6ef198e4b21357f782e6e87ae5b3d6c80b0112ff6381fc023e7` |
| `Textures/T_Casing_762x39_N.png` | `e61a6791118d3034dae2efe276809cfd0b89f7db5f8c4c041323e9c1b17981fe` |

A rebuild rewrites the FBX timestamp, so `WorkFiles/guns/casing/casing_build.json` always holds the current hashes.
