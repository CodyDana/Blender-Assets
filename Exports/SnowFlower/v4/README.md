# Snow Flower sword + sheath (revision 4, game-ready)

`SM_SnowFlower` is the character's signature dao. `SM_SnowFlower_Sheath` is its scabbard. Both were built in
headless Blender 5.2 by `Scripts/SnowFlower/v4/` and finished on 2026-09-27. Both are verified in Unreal Engine 5.8.3
on these exact bytes, and both are wired into the pack materials (`/Game/NinjaPack`).

Revision 3 (`Exports/SnowFlower/*.fbx|glb`, `Assets/SnowFlower/SnowFlower_Master.blend`, `SnowFlower_Game.blend`) is
untouched. It is the history, and the master is the bake source.

Full reports:
- `WorkFiles/SnowFlower/v4/SWORD_V4_REPORT.md`
- `WorkFiles/SnowFlower/v4/SHEATH_REPORT.md`

## 1. Files

| File | What |
|---|---|
| `SM_SnowFlower.fbx` | One LodGroup: LOD0 21,310 / LOD1 8,850 / LOD2 2,778 triangles. 5 convex hulls `UCX_SM_SnowFlower_LOD0_00..04` (blade, tip, guard, grip, pommel). 3 material slots |
| `SM_SnowFlower.sockets.json` | Sword sockets and LOD screen sizes (1.0 / 0.5 / 0.25) |
| `SM_SnowFlower_Sheath.fbx` | One LodGroup: LOD0 11,424 / LOD1 5,600 / LOD2 3,292 triangles. 3 convex hulls `UCX_SM_SnowFlower_Sheath_LOD0_00..02`. 2 material slots |
| `SM_SnowFlower_Sheath.sockets.json` | Sheath sockets and LOD screen sizes (1.0 / 0.5 / 0.25) |
| `Textures/T_SnowFlower_Steel_{BC,ORM,N}.png` | 4096 sword steel atlas: blade, guard, collar, pommel and all silver ornament |
| `Textures/T_SnowFlower_Wrap_{BC,ORM,N}.png` | 2048 grip-cord atlas |
| `Textures/T_SnowFlower_Sheath_{BC,ORM,N}.png` | 4096 sheath atlas: lacquer, fittings, vine, blossoms |
| `Textures/Recolour/T_SnowFlower_Wrap_Detail16.png` (1024), `T_SnowFlower_Sheath_Lacquer_Detail16.png` (2048) | 16-bit linear detail maps that drive the colour options. **Import these, not the 8-bit ones** |
| `Textures/Recolour/recolour_maps.json`, `recolour_constants.json` | The colour options' matched constants, generated. Do not edit by hand |
| `Textures/T_SnowFlower_Wrap_Detail.png`, `T_SnowFlower_Sheath_Lacquer_Detail.png` | 8-bit sRGB reference copies. **Do not import them into the game:** an sRGB greyscale PNG builds as uncompressed BGRA8 in Unreal. The pack imports the `Detail16` copies (G16, 2.8 MB and 11.2 MB with mips) |

Every map is a power of two with a full mip chain:
- **BC**: sRGB, TC_Default.
- **ORM**: linear, TC_Masks. R = AO, G = roughness, B = metallic. Composite Texture = its own `_N`, with CTM_NormalRoughnessToGreen.
- **N**: linear, TC_Normalmap. **DirectX (green down): import with Flip Green OFF.**

## 2. Import (Unreal 5.8)

**Easiest: the pack build.** Run `bash Scripts/unreal/materials/run_build.sh <tag>` from the project root. It imports both meshes and every texture with the right flags, applies the sidecars, builds all instances, assigns the slots and verifies the result (tag `sf_final_0927`: every gate passed).

**By hand.** Use the legacy FBX importer with these settings:
- Static Mesh, **Import Mesh LODs ON**, Combine Meshes OFF.
- Auto Generate Collision OFF, One Convex Hull per UCX ON.
- Normals: *Import Normals*, MikkTSpace tangents.
- Nanite OFF.
- Generate Lightmap UVs ON: source 0, destination 1, Light Map Coordinate Index 1. This is the pack's setting.

Then apply each sidecar with `Scripts/pipeline/ue_import_sockets.py`. Unreal drops FBX sockets from a LodGroup file and would import them at scale 100. Unreal also computes its own LOD thresholds; the sidecar sets the shipped 1.0 / 0.5 / 0.25.

Lightmaps: both FBX files also ship an authored, non-overlapping `UV1_Lightmap`. The recipe above regenerates channel 1 and never uses it. To use the authored layout instead, import with Generate Lightmap UVs OFF. For a held or movable weapon, lightmaps do not matter.

## 3. Frames and sockets (Unreal cm)

**Sword.** The pivot is the `Grip` socket, the primary-hand centre on the grip axis. +Z runs to the tip, +X is the spine side (the tip sweeps toward +X), the cutting edge faces -X, and -Y is the front.

| Sword socket | Location | Rotation | Use |
|---|---|---|---|
| `Grip` | (0, 0, 0) | 0 | The pivot. Attach it to the hand bone or hand socket |
| `OffHand` | (0, 0, -9.5) | 0 | Second hand on the grip |
| `BladeBase` | (-0.43, 0, 12.85) | 0 | Blade root at the guard's seat plane (VFX, trails) |
| `BladeTip` | (3.18, 0, 104.0) | 0 | The point (trails, hit traces from BladeBase to BladeTip) |

**Sheath.** The pivot is the centre of the mid band (the belt mount) on the sheath axis. +Z points to the chape, the same direction as the sword's +Z. +X is the blade's spine side, and -Y is the front (vine) face.

| Sheath socket | Location | Rotation | Use |
|---|---|---|---|
| `Holster` | (0.15, 0, -29.78) | pitch 0.65 | Where the sword's pivot sits when sheathed |
| `Mouth` | (0.025, 0, -18.76) | pitch 0.65 | The sword axis at the mouth plane. **Draw axis = this socket's -Z** |
| `BeltMount` | (0, -1.34, 0) | 0 | The band's belt face. Attach the sheath to a hip socket here |

## 4. Sheathe and unsheathe

**Sheathe.**
1. Set the sword's collision to NoCollision, or QueryOnly.
2. Attach the sword actor or component to the sheath mesh at socket `Holster`, using SnapToTarget for location and rotation (zero relative transform).

The blade then sits fully inside the cavity, and the guard's leaf body rests on the throat collar. Verified in Unreal: the attached sword's sockets land on the Blender positions.

Collision must be off while sheathed because the hulls overlap by design. The guard's pendant leaves go into the mouth like a habaki, and the blade lies inside the sheath hulls.

**Unsheathe.**
1. Detach the sword.
2. Move it along the `Mouth` socket's -Z axis. The blade clears the mouth after about 93 cm of travel.
3. Attach the sword's `Grip` to the hand socket.
4. Restore the sword's collision.

The cavity is the blade swept along that axis with at least 0.41 mm of clearance, so a straight draw never touches the sheath. This was checked on all 9 LOD pairs: 0 intersections at every 1 cm step.

**Wearing the sheath.** Attach the sheath to the character's hip or belt socket with a relative location of **minus** the `BeltMount` location, (0, +1.34, 0), so the band's belt face lands on the socket. The sheath has no modelled belt hanger. The reference shows only the front, so the rig or a belt asset supplies the hanger.

The sword sits tilted 0.65 degrees in the holster. This is by design: the shipped dao blade cannot fit coaxially in the reference's straight outline. The tilt is invisible in play.

## 5. Changing colours (pack instances, `/Game/NinjaPack/MaterialInstances`)

| Slot | Instance on the mesh | Master | What you change |
|---|---|---|---|
| Sword `M_SnowFlower_Blade` | `MI_SnowFlower_Blade` | `M_Steel_Master` | `Steel Tint` multiplies the blade steel. White = as shipped |
| Sword `M_SnowFlower_Fittings` | `MI_SnowFlower_Fittings` | `M_Steel_Master` | `Steel Tint` recolours the silver guard, collar, pommel and grip sprigs (for example a warm gold) |
| Sword `M_SnowFlower_Grip` | `MI_SnowFlower_Grip` | `M_Fabric_Master` | `01 Colour > Colour`: the cord wrap's colour. Default is the shipped near-black silk |
| Sheath `M_SnowFlower_Sheath_Lacquer` | `MI_SnowFlower_Sheath_Lacquer` | `M_Fabric_Master`, **Metal From ORM on** | `01 Colour > Colour`: the marbled lacquer's colour. The baked silver twigs and pearl buds on the body keep their baked colour |
| Sheath `M_SnowFlower_Sheath_Fittings` | `MI_SnowFlower_Sheath_Fittings` | `M_Steel_Master` | `Steel Tint` recolours the silver throat, band, chape and vine. The pearl petals are part of this map too, so a tint shifts them as well |

To change a colour:
1. Open the instance on the mesh, not its `_Base`.
2. Tick the colour parameter and pick a colour. Colour means "the average colour this part reads as".
3. For variants, duplicate the instance first and assign the copy.

Reset (untick) returns to the shipped look. Very light picks are capped at `Lightest Colour` (about `#CBCBCB`) so the marble and cord detail survives. Raise it to trade detail for brightness. `02 Detail` and `03 Surface` hold the detail strength, roughness and normal-strength sliders. Leave `08 Advanced` alone: it holds generated constants.

The Blade and Fittings slots share one steel atlas, and the sheath's two slots share one atlas.

## 6. Collision

**Sword:** 5 convex hulls: blade, tip, guard, grip (fitted to the wrap, stops under the guard) and pommel.

**Sheath:** 3 convex hulls: throat (cut at the mouth plane), body and chape.

## 7. Intentional choices (do not "fix")

- **No tassel on either asset** (user decision, 2026-09-26). The pommel has no cord lug.
- **The tip sweep is half the sheet's.** The spine sweeps 9.4 mm, not 18.8 mm, so the straight reference scabbard can hold the blade.
- **The blade is a real blade:** 6.2 mm thinning to 2.3 mm, with relief up to ±5.8 mm. The sheet's side view draws it about 23 mm thick.
- **The mouth collar is 73.7 mm wide**, where the reference draws 44 mm. It has to pass the 53.5 mm blade. The guard covers it when the sword is sheathed.
- **Parts the reference does not show are DESIGNED.** This covers the sheath's back face, depth, cavity and throat depth: the throat is 44 mm deep front to back at the mouth so the guard's pendant leaves can enter.

## 8. Name and IP

The user states the Snow Flower design is **original**. Only the name was inspired by a manhwa, and the user considers
that name generic.

## 9. Texture size for games (one setting, no re-import)

The steel (sword) and sheath maps ship at 4096 so the ornament holds up in hero close-ups. For normal play you can load
them at 2048 to cut their texture memory to about a quarter: open each 4096 texture (`T_SnowFlower_Steel_*`,
`T_SnowFlower_Sheath_*`) and set **Maximum Texture Size** to `2048` (or **LOD Bias** to `1`), then save. The full 4096
data stays in the asset, so you can set it back at any time; only extreme close-ups of the ornament look softer.
Unreal's low texture-quality settings drop the top size automatically for players on weaker hardware.
