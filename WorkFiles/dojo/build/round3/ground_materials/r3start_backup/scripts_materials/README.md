# Dojo shared material library (v1.0.0, 2026-09-28)

Every dojo kit from now on uses this library for timber, stone, iron, rope, plaster, tile, lacquer and the two
emissive surfaces. It is all procedural and our own work. The reference sheets in `References/Dojo` are
AI-generated modelling references: we only measured them. No pixel from them is in any texture.

| File | What |
|---|---|
| `dojo_tex_gen.py` | numpy texture generators (no bpy). Writes `Exports/DojoKit/Materials/Textures/T_DJ_*` and `WorkFiles/dojo/build/materials/textures_report.json` |
| `dojo_materials.py` | Blender API: `make_material`, `grain_uv`, `box_uv`, `round_uv`, `rope_uv`, `unit_uv`, `bake_wear`, `texel_density` (the docstring has the signatures) |
| `ref_crops.py` | reference crop boxes and their measured medians (`WorkFiles/dojo/build/materials/ref_medians.json`) |
| `render_swatches.py` | swatch renders: shapes A and B under the studio rig and the sunset rig |
| `compose_swatches.py` | the swatch sheet (`SWATCH_SHEET_<round>.png`) and `numbers_<round>.json` |

```
"C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" Scripts/dojo/materials/dojo_tex_gen.py      # ~2 min, all sets
blender -b --factory-startup --python Scripts/dojo/materials/render_swatches.py -- --round r4 --samples 128            # ~3 min, GPU
py -3 Scripts/dojo/materials/compose_swatches.py --round r4
```

## Using it from a kit build script
```python
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/dojo/materials")
import dojo_materials as djm
obj.data.materials.append(djm.make_material("M_DJ_TimberDark"))      # slot 0 = side grain
obj.data.materials.append(djm.make_material("M_DJ_TimberDarkEnd"))   # slot 1 = end grain
djm.grain_uv(obj, "TimberDark", end_set="TimberDarkEnd", end_material_index=1)
djm.bake_wear(obj)                                                   # 'Wear' corner colours (R grime, G edge, B dirt)
djm.box_uv(stone, "Granite")                                         # flat-faced stone: box UV, never mirrored
```

- **Add the material slots BEFORE `grain_uv`.** `mesh.materials.clear()` resets every face's material index to 0.
- **UVs are in tile units.** UV 1.0 is one tile, which is `tile_m` in the table below. Every material samples at
  scale 1. `texel_density(obj)` measures each face against its own slot's set.
- **Mapping by shape:**

  | Shape | Helper |
  |---|---|
  | Timber members | `grain_uv`: U along each loose part's long axis (PCA); a random offset per part, so each member reads as a different board |
  | Round posts, barrels | `round_uv` |
  | Flat-faced stone, plaster, tile | `box_uv`: every face is upright and unmirrored. `space='WORLD'` keeps neighbouring pieces continuous |
  | Round stone (lantern caps, finials) | the triplanar path. In Blender use `make_material(name, projection="BOX", box_blend=0.3)`; in Unreal, WorldAlignedTexture. Box UVs on a sphere seam at the 45 degree lines |
  | Rope | `rope_uv(obj, diameter, mode='straight' or 'ring')` |
  | Panes, displays | `unit_uv`: 0-1 per face, so each pane gets its own hotspot |

- **Edge wear.** `bake_wear` writes G = 1 **only on narrow convex bevel faces** (width 3 cm or less). Broad faces
  get 0. The breakup mask and the threshold below leave at most about 40 % of a bevel face worn, with a lift of at
  most +17 %. This is the fix for the judges' "pale bevel band". The swatches measured G on 5-14 % of the surface
  area.

## Texture sets (`Exports/DojoKit/Materials/Textures/`)

All sets are power of two, with full mips. **BC** is sRGB. **N** is DirectX (green = -Y) and linear. **ORM** is R =
AO, G = roughness, B = metallic, all linear. Every tiling set passes the seam test: the wrap-around step is not in
the top 1 % of the interior steps (`seam_rank` < 0.99 in `textures_report.json`).

| Material | Set | px | tile (m) | px/cm | Notes |
|---|---|---|---|---|---|
| M_DJ_TimberDark | TimberDark | 2048 | 4 x 4 | 5.12 | dark umber, deep checks, 40 knots/tile, grime in recesses, raised latewood |
| M_DJ_TimberDarkEnd | TimberDarkEnd | 1024 | 2 x 2 | 5.12 | growth-ring arcs, radial checks. Luminance 0.78 x the face set |
| M_DJ_TimberAged | TimberAged | 2048 | 4 x 4 | 5.12 | the gate's lighter aged timber |
| M_DJ_TimberAgedEnd | TimberAgedEnd | 1024 | 2 x 2 | 5.12 | 0.78 x the face set |
| M_DJ_Granite | Granite | 2048 | 4 x 4 | 5.12 | rough-hewn chipped facets (3.5 and 9 cm), chisel grooves, pits, sparse biotite/feldspar, cavity darkening |
| M_DJ_GraniteRubble | GraniteRubble | 2048 | 4 x 4 | 5.12 | dry-laid polygonal stones, 12 x 16 per tile (about 33 x 25 cm), pillowed, dark rims and joints, moss in the joints |
| M_DJ_Iron | Iron | 1024 | 2 x 2 | 5.12 | bare metal 0.95-1.0 on 87.6 %, rust 0 on 12.4 %, **0 % partial** |
| M_DJ_Rope | Rope | 1024 x 512 | U = 4 lays, V = once round | trim | 3-strand right-hand lay |
| M_DJ_PlasterCream | PlasterCream | 2048 | 4 x 4 | 5.12 | kit 1's plaster generator with the hall's cream: fine veins, soft stains. Albedo cap 0.80 |
| M_DJ_PlasterEarth | PlasterEarth | 2048 | 4 x 4 | 5.12 | kit 1's EarthPlaster generator and parameters, with the base re-measured (below) |
| M_DJ_RoofTile | RoofTile | 2048 | 4 x 4 | 5.12 | **byte-identical** to kit 1's T_DK_RoofTile (charcoal ibushi, its patchy sheen is in B) |
| M_DJ_Lacquer | Lacquer | 2048 | 2 x 2 | 10.24 (hero) | red-brown lacquer: short cracks, crackle network, pale scratches |
| M_DJ_GlassAmber | GlassAmber | 512 | UV 0-1 per pane | - | emissive colour in BC: amber hotspot (2700 K core step, 2200 K rim) |
| M_DJ_VendingPanel | VendingPanel | 512 x 1024 | UV 0-1 over the display | - | blank backlit cyan diffuser: no text, brands or products |
| (weathering) | WearMask `_M` | 512 | 1 x 1 | 5.12 | grey breakup mask, full range |

## Unreal 5.8 recipe

**Import:** BC as TC_Default, sRGB. N as TC_Normalmap with **no green flip** (the maps are already DirectX). ORM
and WearMask as TC_Masks, linear. Import mesh vertex colours ("Replace") so the `Wear` colour arrives.

**Masters.** Three masters cover every material. They are the environment family STYLE_GUIDE section 5 plans
(M_Env_Wood, Stone, Plaster, RoofTile, Emissive). Build them as code in the kit's own folder: the pack masters are
frozen.

1. **M_DJ_Lib_Opaque** (UV0):
   - BaseColor = BC x Tint;
   - Roughness = ORM.g x RoughMult;
   - Metallic = ORM.b;
   - AO = ORM.r;
   - Normal = N, with a FlattenNormal strength parameter;
   - UseWear static switch.
2. **M_DJ_Lib_Triplanar**: the same maths with WorldAlignedTexture (and WorldAlignedNormal):
   - TextureSize = tile_m x 100 cm (400 for granite and plaster);
   - for round stone parts only;
   - a per-actor offset from the position hash is optional.
3. **M_DJ_Lib_Emissive** (UV0):
   - BaseColor = BC x 0.25;
   - Emissive = BC x EmissiveIntensity;
   - Roughness = ORM.g;
   - Metallic = 0.

**Wear maths.** The same in both apps: the Blender node group `DJ_Wear_v1`.
```
m  = WearMask(UV0 * TileM)                       TileM = (tile_m.u, tile_m.v); the mask is 1 m per tile
bc = bc * (1 - 0.40 * VC.r)                      grime / occlusion
e  = saturate((VC.g * (0.35 + m) - 0.55) * 2.5)  broken edge wear
bc = lerp(bc, Desaturate(bc, 0.35) * 1.30, 0.55 * e)
bc = lerp(bc, DUST(sRGB 0.46, 0.41, 0.35), 0.45 * VC.b * m)
rough = saturate(rough + 0.06 * e + 0.08 * VC.b)
```

**Instances** (UV-mapped instances use scale 1, because the UVs are already in tile units):

| Instance | Master | Params |
|---|---|---|
| MI_DJ_TimberDark / _TimberDarkEnd / _TimberAged / _TimberAgedEnd | Opaque | UseWear on, TileM (4, 4) for faces and (2, 2) for ends |
| MI_DJ_Granite | Opaque (flat faces) / Triplanar (round parts) | UseWear on, TileM (4, 4) |
| MI_DJ_GraniteRubble | Opaque | UseWear on, TileM (4, 4) |
| MI_DJ_Iron | Opaque | UseWear off. Never tint the metal channel |
| MI_DJ_Rope | Opaque | UseWear off |
| MI_DJ_PlasterCream / _PlasterEarth | Opaque | UseWear on, TileM (4, 4) |
| MI_DJ_RoofTile | Opaque | UseWear off |
| MI_DJ_Lacquer | Opaque | UseWear on, TileM (2, 2). Optional clear coat 0.3 |
| MI_DJ_GlassAmber | Emissive | EmissiveIntensity **500** (Blender strength 5 x the showcase's K 100) |
| MI_DJ_VendingPanel | Emissive | EmissiveIntensity **160** (1.6 x 100) |

- Retune both emissive values after the sun, sky and post re-grade: the showcase verify found an orange cast.
- The glass lights only the pane. The lamp's point light stays a separate actor (the showcase rule).

## Measured against the references (round 4, `WorkFiles/dojo/build/materials/numbers_r4.json`)

- **What is compared:** the studio renders use render_training's calibrated grey-studio rig. Each render median
  covers the object pixels of shapes A and B. Each reference value is the median of that material's crop medians.
- **dE76:** measured in CIE Lab. As a rule of thumb, under 5 is hard to tell apart in a swatch.

| Material | ref (sRGB) | ours | dE76 | lum x | notes |
|---|---|---|---|---|---|
| TimberDark | 80,59,46 | 74,58,48 | 3.7 | 0.97 | end/face luminance 0.78 |
| TimberAged | 93,65,47 | 81,62,49 | 6.2 | 0.94 | |
| Granite | 120,110,104 | 125,117,109 | 3.0 | 1.06 | |
| GraniteRubble | 100,90,79 | 92,88,80 | 3.4 | 0.96 | |
| Iron | 61,56,58 | 63,60,57 | 3.6 | 1.05 | |
| Rope | 147,108,71 | 147,112,72 | 2.6 | 1.03 | |
| PlasterCream | 190,155,126 | 193,161,136 | 3.4 | 1.04 | |
| PlasterEarth | 190,164,140 | 180,156,130 | 3.4 | 0.95 | |
| RoofTile | 80,80,86 | 85,86,89 | 3.1 | 1.07 | |
| Lacquer | 118,81,74 | 119,72,64 | 5.9 | 0.92 | |
| VendingPanel (glow) | 102,183,198 | 123,179,190 | 6.6 | 1.01 | hue 188.8 vs 188.4 degrees |
| GlassAmber (glow) | 248,204,137 | 233,156,106 | 21.3 | - | hue 23 vs 37 degrees: still too orange under AgX, see open points |

Sunset: the sunset crops come from dojo1_reference2, which has its own grade, so they are a look check, not a match
target. RoofTile is dE 8.0 against it.

## Open points
- **GlassAmber:**
  - It now reads amber with a hotspot, not flat peach.
  - The glowing pixels still sit 14 degrees redder than the sheets under Blender's AgX (hue 23 vs 37). Unreal's
    tonemapper differs, so set the final hue in the Unreal look pass, with the lamp point lights on.
- **Timber:**
  - The large-scale tone band still repeats every 4 m in V; the 3 x 3 swatch shows it.
  - On real members, `grain_uv`'s random per-part offsets hide it.
  - A single surface larger than 4 m across the grain would show it.
- **PlasterEarth:** it departs from kit 1's `#A48B6D` by its base colour only. Kit 1's own `T_DK_EarthPlaster` is
  untouched. Switching kit 1 over is the kit 1 owner's call.
- **Moss:** lichen and moss on stone beyond the rubble joints is not in this library. Kit 1's `T_DK_MossMask`, or a
  later moss set, layers over it.
