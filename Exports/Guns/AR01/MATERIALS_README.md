# Assault Rifle AR-01: materials and colours (Unreal Engine 5.8)

This file covers the rifle's materials:
- the slots and their texture sets;
- how to import the maps;
- how to change the furniture (wood) colour;
- what to leave alone.

The Unreal material instances are created in the import stage, which has not run yet. The names below are the ones
that stage uses (from `SK_AR01.skeletal.json` and `Textures/Recolour/recolour_maps.json`).

## Slots

| Mesh | Slot | Instance (planned) | Master | Covers |
|---|---|---|---|---|
| `SK_AR01`, `SM_AR01` | 0 `M_AR01_Metal` | `MI_AR01_Metal` | `M_Fabric_Master`, *Metal From ORM* on | Black lacquer over steel (receiver, cover, trunnions, sights, barrel, gas system, brake, guard, butt plate) and the blued small parts (bolt, carrier, selector, trigger, catch, pins, rod), with bare-steel wear on the edges people and gear rub |
| `SK_AR01`, `SM_AR01` | 1 `M_AR01_Furniture` | `MI_AR01_Furniture` | `M_Fabric_Master` | The walnut stock, pistol grip and both handguards, shellac finish, the grip's checkering |
| `SM_AR01` (merged magazine), `SM_AR01_Mag` | 2 / 0 `M_AR01_Mag` | `MI_AR01_Mag` | as the Metal slot | The black lacquered steel magazine, worn at the feed lips, the lugs, the spines at the well and the floor plate |

`SK_AR01` has slots 0 and 1 only; the magazine is its own mesh. On the static twin each slot's UV0 sits in its own U
tile (Metal 0..1, Furniture 1..2, Mag -1..0); the skeletal mesh keeps every set in 0..1.

## Import the maps

| Map | Setting |
|---|---|
| `T_AR01_*_BC` | sRGB on; texture group `Weapon` |
| `T_AR01_*_ORM` | sRGB off (R ambient occlusion, G roughness, B metallic: 0 or 1); texture group `Weapon` |
| `T_AR01_*_N` | Normal map compression, DirectX convention (green already flipped); 16-bit source; texture group `WeaponNormalMap` |
| `T_AR01_*_Masks` | sRGB off (R edge-wear propensity, G handling, B cavity, A refinishable); half size |
| `Recolour/T_AR01_Furniture_Detail16` | sRGB off, Grayscale (builds as G16): the lossless detail the wood recolour uses |

Keep full mip chains on every map (all are square powers of two). Sizes: Metal 4096, Furniture 2048, Mag 1024,
Detail16 1024.

## Change the wood colour

The furniture is one recolourable part. Its walnut stain is one colour times a detail map, so a new colour keeps the
grain, the pores, the handling wear and the checkering.

1. Open `MI_AR01_Furniture` (for a variant, duplicate it first and put the copy on slot 1).
2. In **01 Colour**, change **Colour**. The shipped stain is the parameter's default.
3. Save.

What the colour means: **Colour is the average colour of the furniture**, so the wood reads as the colour you pick.
The four pieces of wood keep their slightly different tones (the reference's furniture is mismatched, as on real
rifles of this pattern); those tone ratios move with your colour. The pack's general rules apply: very light picks
are capped at **Lightest Colour**, pure black is lifted a little so the grain stays visible, and **Use Original Baked
Colours** returns to the shipped look. The recolour constants (Detail Bias, Detail Scale, moments, ...) are in
`Textures/Recolour/recolour_maps.json`; leave groups **08 Advanced** and **09 Textures** alone.

## Metal and magazine

The metal and the magazine keep their baked finish: they are not recolourable in this version. Their instances only
point at their texture sets; leave their parameters as the import stage sets them.

## Good to know

- The colours were matched to the reference sheet under one physical studio light (the L5 check in
  `WorkFiles/guns/rifle/gates/uv_bake_paint.json`: every region within its tolerance).
- Wear is real wear: bare steel only within 0.6 mm of a real convex edge (1.2 mm in the handling zones), never on a
  flat panel; the magazine wears only at its lugs, feed lips, spines at the well and floor plate.
- No markings, serial numbers or logos are painted anywhere.
