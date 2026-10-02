# DojoKit FX (SM_DKF_*, T_DKF_*)

This folder holds the cherry-petal and river-water FX for the sunset mountain dojo (landscape round, 2026-09-30):
- Yoshino petal meshes;
- fallen-petal drift clusters and a scatter decal;
- mist, spray and haze flipbooks for Niagara;
- a tileable foam texture for the river water material.

Built headless in Blender 5.2 by `Scripts/dojo/fx/` (`run_all.sh`). Exported only through
`Scripts/pipeline/export_fbx.py` (kind static, metres, -Y forward, Z up, triangulated). **Not yet imported into
Unreal.** The import, material and Niagara recipe is in `WorkFiles/dojo/build/fx/fx_catalog.json`, and the numbers and
deviations are in `WorkFiles/dojo/build/fx/BUILD_NOTES.md`.

## Meshes

| Mesh | Tris | Size (mm) | Use |
|---|---|---|---|
| `SM_DKF_Petal_A` / `_B` / `_D` / `_F` | 56 each | 13-14.5 long | flat and cupped petals (sheet petals 1, 2, 4, 6) |
| `SM_DKF_Petal_C` | 84 | 13.5 long | curled petal (crescent from above) |
| `SM_DKF_Petal_E` | 84 | 12.5 long | folded into a cone |
| `SM_DKF_PetalOld_A` | 84 | 12.5 long | browned, crumpled old petal |
| `SM_DKF_PetalDrift_A` / `_B` / `_C` | 1596 / 3052 / 5544 | r 0.18 / 0.28 / 0.40 m | fallen clusters (about 1 in 8 old) |

Petal meshes:
- The origin is at the area centroid (Niagara mesh particles spin about it).
- The front face points +Z before the bends, and the length runs along +Y.
- They are two-sided masked cards: no collision, Nanite OFF.

Drift clusters:
- The origin is on the ground; the lowest petal sits 0.3 mm above it.
- Slot 0 is `MI_DKF_Petal`, slot 1 is `MI_DKF_PetalOld`.

UVs:
- UV0 is the petal texture frame. It overlaps by design on the drifts, because every petal shares the texture.
- UV1 is inside 0-1.

## Textures

| Texture | Size | Colour space / compression |
|---|---|---|
| `T_DKF_Petal_BC` (A = opacity), `T_DKF_PetalBack_BC` | 1024 | sRGB, BC7 |
| `T_DKF_Petal_N` | 1024 | Normalmap, DirectX (Flip Green OFF) |
| `T_DKF_Petal_ORM` | 1024 | Masks |
| `T_DKF_Petal_SSS` (white = thin) | 1024 | Grayscale |
| `T_DKF_PetalOld_BC` / `_N` / `_ORM` / `_SSS` | 1024 | as above |
| `T_DKF_PetalScatter_BC` / `_N` / `_ORM` (2x2 decal atlas, 0.35 m cells) | 2048 | as above |
| `T_DKF_MistPuff_SixWayP` / `_SixWayN` (8x8 flipbook) | 4096 | linear (sRGB OFF), BC7 |
| `T_DKF_MistWisp_SixWayP` / `_SixWayN` (8x8) | 4096 | linear, BC7 |
| `T_DKF_SprayBurst_SixWayP` / `_SixWayN` (8x8) | 4096 | linear, BC7 |
| `T_DKF_Haze_M` (R opacity, G top-lit, B back-lit) | 2048 x 1024 | Masks |
| `T_DKF_Foam_M` (R coverage, G lace, B flow streaks) / `T_DKF_Foam_N`, tileable | 2048 | Masks / Normalmap DX |

**Six-way maps.** Every flipbook is colour-neutral and is lit in engine from its two maps:
- `SixWayP` holds the lighting from +X (right), +Z (top) and +Y (from behind the sprite), with A = opacity.
- `SixWayN` holds the lighting from -X, -Z and -Y (the camera side), with A = opacity.

The frames are 8 x 8, row-major from the top left, and play over the particle's normalised age. The flipbooks are:
- `MistPuff`: a billow is born, grows, rises and erodes;
- `MistWisp`: a streaky wisp drifts up and to the right and thins;
- `SprayBurst`: a Mantaflow FLIP sim of a river surge slamming a boulder. The sheet runs up the rock face, tears into
  fingers and droplets, falls and fades. The water line is 4 % above the cell bottom (pivot 0.5, 0.96).

## Provenance

This is our own procedural and simulation work. The reference sheets (`References/Dojo/dojo_petals_ref.png`,
`dojo_mist_ref.png`) are AI-generated. They were only measured, and the petal outline was traced; no pixel of them is
in any texture. Disclose the use of AI references for Fab (ASSET_GUIDELINES 11).
