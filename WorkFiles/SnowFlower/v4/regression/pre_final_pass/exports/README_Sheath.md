# SM_SnowFlower_Sheath - the Snow Flower sword's scabbard

Built 2026-09-26 in Blender 5.2 by `Scripts/SnowFlower/v4/build_sheath.py` (rebuild everything:
`bash Scripts/SnowFlower/v4/run_sheath_all.sh`, about 20 minutes). Full report: `WorkFiles/SnowFlower/v4/SHEATH_REPORT.md`.

## Files

| File | What |
|---|---|
| `SM_SnowFlower_Sheath.fbx` | One LodGroup: LOD0 10,912 / LOD1 4,924 / LOD2 2,624 triangles, 3 convex hulls `UCX_SM_SnowFlower_Sheath_LOD0_00..02` |
| `SM_SnowFlower_Sheath.sockets.json` | Sockets and LOD screen sizes (1.0 / 0.5 / 0.25). Unreal drops FBX sockets from a LodGroup file: apply this sidecar after import with `Scripts/pipeline/ue_import_sockets.py` |
| `Textures/T_SnowFlower_Sheath_BC.png` | 4096, base colour, sRGB |
| `Textures/T_SnowFlower_Sheath_ORM.png` | 4096, linear: R ambient occlusion, G roughness, B metallic |
| `Textures/T_SnowFlower_Sheath_N.png` | 4096, tangent-space normal, **DirectX** (green down): import with Flip Green OFF |
| `Textures/T_SnowFlower_Sheath_Lacquer_Detail.png` | 4096, sRGB-encoded normalised lacquer luminance for a colour tint (same convention as the sword's wrap Detail): a_lo 0.00893, a_hi 0.77169 |

Material slots: `M_SnowFlower_Sheath_Lacquer` (the lacquer body and cavity) and `M_SnowFlower_Sheath_Silver` (fittings,
vine, blossoms). Both slots use the one texture set. Metallic and roughness come from the ORM, so plate insets and
pearl petals shade correctly in either slot.

## Import (Unreal 5.8, legacy FBX importer, verified)

Static Mesh, **Import Mesh LODs ON**, Auto Generate Collision OFF, One Convex Hull Per UCX ON, normals imported, and
Generate Lightmap UVs into channel 1. Then apply the sidecar. The sheath is part of the same verification as the sword
(`WorkFiles/SnowFlower/v4/UnrealCheck_Sheath/verification_summary.json`, 22 of 22 gates).

## Frame and sockets

The pivot is the centre of the mid band (the belt mount) on the sheath axis. +Z points toward the chape point, the
same direction as the sword's +Z toward its tip. +X is the blade's spine side, and -Y is the front (vine) face.

| Socket | Location (cm, Unreal) | Rotation | Use |
|---|---|---|---|
| `Holster` | (0.10, 0, -31.66) | pitch 0.6 | Attach the sword (its pivot = its `Grip` socket) here with **zero relative transform**. The blade then sits fully inside the cavity |
| `Mouth` | (-0.035, 0, -18.76) | pitch 0.6 | Where the sword axis crosses the mouth plane. **Draw axis = this socket's -Z.** The cavity is the blade swept along that axis, so a straight draw never touches the sheath |
| `BeltMount` | (0, -1.34, 0) | 0 | Back-face centre of the belt band. Hang the sheath from a hip socket here, or attach the actor root with an offset of minus this location |

The sword sits 0.6 degrees tilted in the holster. This is by design: a coaxial sword cannot fit the reference outline
(see the report). The tilt is invisible in play.

While the sword is sheathed, set the sword's collision to NoCollision or query-only. The sheath hulls are solid, and
the blade is inside them.

## Decisions to know

- **No tassel and no cord**, as decided.
- The mouth collar is 73.7 mm wide, where the reference draws a 44 mm collar. That collar cannot pass the 53.5 mm v4
  blade. It is hidden under the guard when the sword is sheathed.
- IP: the sword sheet's title names the protagonist of *The Legend of the Northern Blade*. The user has stated the
  design is original. Use a neutral product name if this ever goes to Fab.
