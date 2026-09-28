# SM_SnowFlower (revision 4, game-ready)

Hero dao for the player character. Built 2026-09-26 by `Scripts/SnowFlower/v4/` (headless Blender 5.2),
verified in Unreal Engine 5.8.3 on these exact bytes (`WorkFiles/SnowFlower/v4/UnrealCheck/verification_summary.json`).
Revision 3 (`Exports/SnowFlower/*.fbx`, `Assets/SnowFlower/SnowFlower_Master.blend`) is untouched and is the history.

## Files

| File | What |
|---|---|
| `SM_SnowFlower.fbx` | One LodGroup: `SM_SnowFlower_LOD0` 21,310 / `LOD1` 8,594 / `LOD2` 2,698 triangles, 4 convex hulls `UCX_SM_SnowFlower_LOD0_00..03` |
| `SM_SnowFlower.sockets.json` | Sockets + LOD screen sizes (1.0 / 0.5 / 0.25). Apply with `Scripts/pipeline/ue_import_sockets.py` after import: FBX sockets are dropped from a LodGroup file and would import at scale 100 |
| `Textures/T_SnowFlower_Steel_{BC,ORM,N}.png` | 4096 steel atlas (blade, guard, collar, pommel, all silver ornament) |
| `Textures/T_SnowFlower_Wrap_{BC,ORM,N,Detail}.png` | 2048 grip-cord atlas; `Detail` is the full-range greyscale for the pack's colour option |

## Import (Unreal)

Legacy FBX importer, **Import Mesh LODs ON**, Combine Meshes OFF, Auto Generate Collision OFF, One Convex Hull per UCX
ON, Normal Import Method *Import Normals*, MikkTSpace tangents, Generate Lightmap UVs ON (source UV0, destination
UV1, Light Map Coordinate Index 1). Nanite OFF. Then run `ue_import_sockets.py` on the sidecar.

Textures: BC sRGB / TC_Default; ORM **linear** / TC_Masks (R = AO, G = roughness, B = metallic), Composite Texture =
its own N with CTM_NormalRoughnessToGreen; N linear / TC_Normalmap, **flip green OFF - the maps are DirectX (green
down)**; Detail sRGB / TC_Grayscale. All power-of-two with full mip chains.

## Frame and sockets (Unreal cm)

Pivot = `Grip` socket: the primary-hand centre on the grip axis, 4.6 cm below the collar. +Z runs to the tip; +X is the
blade's spine side (the tip sweeps toward +X), the cutting edge faces -X. Sockets: `Grip` (0,0,0), `OffHand`
(0,0,-9.5), `BladeBase` (-0.43,0,12.85) on the guard-seat plane (lowest guard point = where a scabbard mouth sits),
`BladeTip` (3.18,0,104.0). All rotations zero, scale 1.

## Materials

Two slots: `M_SnowFlower_Steel` (for `M_Steel_Master`) and `M_SnowFlower_Wrap` (for `M_Fabric_Master` with the colour
option). Blackened steel, polished bevels and silver ornament all live in the steel maps. Default wrap tint (linear)
0.0173 / 0.0173 / 0.0190; Detail = (albedo luminance - 0.01004) / (0.02719 - 0.01004), stored sRGB-encoded.

## Intentional deviations from the design sheet

- **No tassel.** The sheet draws a cord, charm and tassel on the pommel; the user decided (2026-09-26) that the
  sword has none. The pommel has no cord lug. Do not "restore" it.
- **Tip sweep is half the sheet's** (spine sweeps 9.4 mm at the tip instead of 18.8 mm), so the straight reference
  scabbard can hold the blade. See `WorkFiles/SnowFlower/v4/SWORD_V4_REPORT.md`.
- The sheet's side view draws the blade 23 mm thick; v4 uses a real 6.2 -> 2.3 mm blade (relief up to +-5.8 mm).
