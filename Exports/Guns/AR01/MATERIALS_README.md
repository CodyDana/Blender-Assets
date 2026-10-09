# Assault Rifle AR-01: materials and colours (Unreal Engine 5.8)

The rifle uses the pack's shared master materials (the same masters as the katana, the fan and the throwables). This
file covers:
- which instance goes on which slot;
- how to import the maps;
- how to change the wood colour;
- what the metal tint does, and what to leave alone.

## Slots and instances

| Mesh | Slot | Instance on the mesh | Master | Covers |
|---|---|---|---|---|
| `SK_AR01`, `SM_AR01` | 0 `M_AR01_Metal` | `MI_AR01_Metal` | `M_Steel_Master` | Black lacquer over steel (receiver, dust cover, trunnions, sights, barrel, gas system, brake, trigger guard, butt plate) and the blued small parts (bolt, carrier, selector, trigger, catch, pins, rod), with bare-steel wear on the edges that hands and gear rub |
| `SK_AR01`, `SM_AR01` | 1 `M_AR01_Furniture` | `MI_AR01_Furniture` | `M_Fabric_Master` | The walnut buttstock, pistol grip and both handguards: shellac finish, grip checkering, handling wear |
| `SM_AR01` (merged magazine), `SM_AR01_Mag` | 2 / 0 `M_AR01_Mag` | `MI_AR01_Mag` | `M_Steel_Master` | The black lacquered steel magazine, worn at the feed lips, the lugs, the spines at the well and the floor plate |

- Each instance on a mesh has a parent `MI_AR01_<Part>_Base` (in `MaterialInstances/Base`). The base holds every
  texture and every matched setting. The instance on the mesh overrides only the colour, so *Reset to default* on it
  always brings back the shipped look.
- `SK_AR01` has slots 0 and 1; the magazine is its own mesh. `SK_AR01` and `SM_AR01` share the Metal and Furniture
  instances, and `SM_AR01` and `SM_AR01_Mag` share the Mag instance. A colour change therefore shows on all of them.
- On the static twin, each slot's UV0 sits in its own U tile (Metal 0..1, Furniture 1..2, Mag -1..0). Keep the
  textures' address mode on *Wrap* (the default) so every tile reads the same texels. The skeletal mesh keeps every set
  in 0..1.

## Import the maps

| Map | Size | Setting |
|---|---|---|
| `T_AR01_Metal_BC`, `T_AR01_Mag_BC` | 4096, 1024 | sRGB on, compression Default (BC1) |
| `T_AR01_Furniture_BC` | 2048 | sRGB on, compression **BC7**. The shipped wood shows this map directly, and BC7 keeps its grain about three times closer to the source than BC1 (see "Measured") |
| `T_AR01_*_ORM` | as BC | sRGB off, compression Masks, no alpha (R ambient occlusion, G roughness, B metallic 0 or 1). The pack sets the composite texture to the set's normal map (*Normal Roughness To Green*, power 1): distant mips get rougher where the normals vary, which reduces specular shimmer |
| `T_AR01_*_N` | as BC | Normal map compression, DirectX convention (green already flipped, *Flip Green Channel* off); 16-bit source |
| `Recolour/T_AR01_Furniture_Detail16` | 1024 | sRGB off, compression Grayscale (builds as G16, lossless): the detail map the wood recolour uses |
| `T_AR01_*_Masks` | half size | Not used by the pack's materials. sRGB off, compression Masks (R edge-wear propensity, G handling, B cavity, A refinishable), for your own dirt or wear layer |

Keep full mip chains on every map; all of them are square powers of two. The pack imports into the default texture
group. In a game, use group `Weapon` for BC, ORM and Detail16 and `WeaponNormalMap` for N: those groups were measured
in the rifle's own Unreal check, and every map stayed at its top mip at the hip and at ADS.

## Change the wood colour

The furniture is the rifle's one recolourable part. The shipped instance shows the baked colour map exactly, because
the four wood pieces have slightly different hues (the reference's furniture is mismatched, as on real rifles of this
pattern), and the recolour detail map stores brightness only. To recolour:

1. Open `MI_AR01_Furniture`. For a variant, duplicate it first and put the copy on slot 1.
2. In **01 Colour**, tick the override of **Use Original Baked Colours** and turn it **off**.
3. Change **Colour**, then save.

What the colour means: **Colour is the average colour of the furniture**, so the wood reads as the colour you pick.
The grain, the pores, the handling wear and the checkering all follow the new colour. The four pieces move together:
they keep their brightness differences, but their small hue differences stay with the baked map. The pack's general
rules apply:
- very light picks are capped at **Lightest Colour**, so the highlights keep their detail;
- pure black is lifted a little, so the grain stays visible;
- turning **Use Original Baked Colours** back on (or *Reset to default*) returns to the shipped look.

The default Colour (the walnut's covered-texel mean) is the parameter's value, so the switch-off view at the default
colour is the shipped walnut with one shared hue. Leave groups **08 Advanced** and **09 Textures** alone; they are
matched to the maps (`Textures/Recolour/recolour_constants.json`).

## Metal and magazine

The metal and the magazine keep their baked finish; they are not designed to be recoloured in this version. Their
instances have one colour control, **Steel Tint** (white = as shipped). It multiplies the base colour, for example to
warm or grey the lacquer slightly. The bare and blued steel come from the ORM map's metallic channel, so a strong tint
also colours the worn edges.

## Measured (Unreal 5.8.3, the pack's validation project)

The pack build `ar01_1009b` passed every pack gate:
- functions, masters, instances, meshes, textures, dependencies and accounting;
- 0 compile failures;
- every other pack entry unchanged.

The numbers below are base-colour captures (one pixel per texel, 8-bit levels) against the maps, from
`WorkFiles/guns/rifle/gates/pack_materials.json`:

| Check | Result |
|---|---|
| Shipped wood (BC7) vs the BC PNG | p99.9 4 levels, mean 0.49; colour difference dE00 mean 0.23, p99 0.92 |
| The same with BC1 | p99.9 12 levels, dE00 mean 0.71, p99 2.26 |
| Recolour path at the default Colour vs the pack's float model | at most 1 level everywhere, mean 0.10 |
| 10 recolour stress colours (white, red, blue, cream, black, grey, near-black, blue-grey, green, brown) | every texel within 1 level of the model; grain kept (rank correlation with the default >= 0.98), no clipping, no banding |
| Mip drift (mip 4 vs the box-filtered mip 0) | within 0.08 % for every colour (gate 2 %) |
| Metal / magazine BC1 vs PNG (reported, as for every pack steel) | p99.9 7 / 6 levels |

The colours were matched to the reference sheet under one physical studio light in Blender (the L5 check in
`WorkFiles/guns/rifle/gates/uv_bake_paint.json`).

## Good to know

- Wear is real wear: bare steel only within 0.6 mm of a real convex edge (1.2 mm in the handling zones), never on a
  flat panel; the magazine wears only at its lugs, feed lips, spines at the well and floor plate.
- No markings, serial numbers or logos are painted anywhere.
- `SK_AR01.skeletal.json` still lists `M_Fabric_Master` with *Metal From ORM* under `materials` for the metal set. That
  was the export's plan; the pack uses `M_Steel_Master` (as for the katana's steel), which gives the same base colour,
  metallic and roughness. No importer reads that block, and the next re-export corrects it.
