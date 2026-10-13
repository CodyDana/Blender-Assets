# Compact SMG SM-01: materials and colours (Unreal Engine 5.8)

The SMG uses the pack's shared master materials (the same masters as the AR-01, the katana, the fan and the
throwables). This file covers:
- which instance goes on which slot;
- how to import the maps;
- how to change the polymer colour (black, tan, OD green, FDE or any other);
- what the metal tint does, and what to leave alone.

## Slots and instances

| Mesh | Slot | Instance on the mesh | Master | Covers |
|---|---|---|---|---|
| `SK_SMG01`, `SM_SMG01` | 0 `M_SMG01_Metal` | `MI_SMG01_Metal` | `M_Steel_Master` | Manganese-phosphate steel: top and bottom rails, sights, barrel and nut, muzzle device, bolt, charging handle, selector, trigger, release paddle, pins, hinge pin. Bare-steel wear only on rail crests, sight ears, the device rim, the knob crown, the selector tip and the bolt's sliding flanks |
| `SK_SMG01`, `SM_SMG01` | 1 `M_SMG01_Furniture` | `MI_SMG01_Furniture` | `M_Fabric_Master` | The black polymer: upper and lower receiver shells, grip frame and stippled cover, magwell, skeleton stock, butt pad and latch. Moulded matte texture, polish where hands slide, whitening where struck |
| `SM_SMG01` (merged magazine), `SM_SMG01_Mag` | 2 / 0 `M_SMG01_Mag` | `MI_SMG01_Mag` | `M_Fabric_Master` | The black polymer magazine (body, floor plate, follower), with insertion streaks on its upper part and wear at the floor plate |

- Each instance on a mesh has a parent `MI_SMG01_<Part>_Base` (in `MaterialInstances/Base`). The base holds every
  texture and every matched setting. The instance on the mesh overrides only the colour, so *Reset to default* on it
  always brings back the shipped look.
- `SK_SMG01` has slots 0 and 1; the magazine is its own mesh. `SK_SMG01` and `SM_SMG01` share the Metal and Furniture
  instances, and `SM_SMG01` and `SM_SMG01_Mag` share the Mag instance. A colour change therefore shows on all of them.
- On the static twin, each slot's UV0 sits in its own U tile (Metal 0..1, Furniture 1..2, Mag -1..0). Keep the
  textures' address mode on *Wrap* (the default) so every tile reads the same texels. The skeletal mesh keeps every set
  in 0..1.
- Furniture and Mag form one recolour group (`SMG01`): a recolour sets the same Colour on both.

## Import the maps

| Map | Size | Setting |
|---|---|---|
| `T_SMG01_Metal_BC` | 2048 | sRGB on, compression Default (BC1) |
| `T_SMG01_Furniture_BC`, `T_SMG01_Mag_BC` | 4096, 1024 | sRGB on, compression **BC7**. The shipped polymer shows these maps directly, and BC7 keeps the dark wear within 2 levels of the source where BC1 drifts 5-8 (see "Measured") |
| `T_SMG01_*_ORM` | as BC | sRGB off, compression Masks, no alpha (R ambient occlusion, G roughness, B metallic 0 or 1). The pack sets the composite texture to the set's normal map (*Normal Roughness To Green*, power 1): distant mips get rougher where the normals vary, which reduces specular shimmer |
| `T_SMG01_*_N` | as BC | Normal map compression, DirectX convention (green already flipped, *Flip Green Channel* off); 16-bit source |
| `Recolour/T_SMG01_Furniture_Detail16`, `Recolour/T_SMG01_Mag_Detail16` | 2048, 1024 | sRGB off, compression Grayscale (builds as G16, lossless): the detail maps the polymer recolour uses |
| `T_SMG01_*_Masks` | half size | Not used by the pack's materials. sRGB off, compression Masks (R edge-wear propensity, G handling, B cavity, A refinishable), for your own dirt or wear layer |

Keep full mip chains on every map; all of them are square powers of two. The pack imports into the default texture
group. In a game, use group `Weapon` for BC, ORM and Detail16 and `WeaponNormalMap` for N. Memory in Unreal with
mips: 81.0 MiB for the whole set as the pack imports it (the furniture's 4096 BC7, N and ORM are 21.4 + 21.4 + 10.7
MiB).

## Change the polymer colour

The polymer (furniture and magazine) is the SMG's recolourable part. The shipped instances show the baked colour maps
exactly, because the polymer's fine wear (whitening specks, scuffs, polish) is finer than the recolour detail map can
hold. To recolour:

1. Open `MI_SMG01_Furniture` and `MI_SMG01_Mag`. For a variant, duplicate both first and put the copies on their
   slots (slot 1 of `SK_SMG01` / `SM_SMG01`, slot 2 of `SM_SMG01`, slot 0 of `SM_SMG01_Mag`).
2. In **01 Colour**, tick the override of **Use Original Baked Colours** and turn it **off** on both.
3. Set the same **Colour** on both, then save.

What the colour means: **Colour is the average colour of the polymer**, so the gun reads as the colour you pick. The
moulded texture, the grip stipple, the polish and the whitening all follow the new colour. The pack's general rules
apply:
- very light picks are capped at **Lightest Colour** (0.6), so the highlights keep their detail;
- pure black is lifted a little (to about sRGB 25), so the texture stays visible;
- turning **Use Original Baked Colours** back on (or *Reset to default*) returns to the shipped look.

The default Colours are each set's covered-texel mean (furniture linear 0.028 / 0.029 / 0.031, magazine 0.026 /
0.027 / 0.030). Switching the baked colours off at those defaults gives the shipped black with softer wear specks (the finest specks are smaller than the detail map holds).
Leave groups **08 Advanced** and **09 Textures** alone; they are matched to the maps
(`Textures/Recolour/recolour_constants.json`).

## Metal

The metal keeps its baked phosphate finish; it is not designed to be recoloured. Its instance has one colour control,
**Steel Tint** (white = as shipped). It multiplies the base colour, for example to warm or grey the phosphate
slightly. The bare steel comes from the ORM map's metallic channel, so a strong tint also colours the worn edges.

## Measured (Unreal 5.8.3, the pack's validation project)

The pack build `smg01_1013b` passed every pack gate:
- functions, masters, instances, meshes, textures, dependencies and accounting;
- 0 compile failures;
- every other pack entry unchanged.

The numbers below are base-colour captures (one pixel per texel, 8-bit levels) against the maps, from
`WorkFiles/guns/smg/gates/pack_materials.json`:

| Check | Result |
|---|---|
| Shipped furniture / magazine (BC7) vs the BC PNG | p99.9 2 / 2 levels, mean 0.15 / 0.17; colour difference dE00 mean 0.17 / 0.23 |
| The same with BC1 | p99.9 5 / 8 levels, dE00 mean 0.87 / 0.93 |
| Recolour path at the default Colour vs the pack's float model | at most 1 level everywhere, mean 0.12 / 0.03 |
| 13 recolour stress colours on both sets (white, red, blue, cream, black, grey, near-black, blue-grey, green, brown, tan, OD green, FDE) | every texel within 1 level of the model; no clipping, no banding, texture contrast kept |
| Mip drift (mip 4 vs the box-filtered mip 0) | within 1.7 % for every colour (gate 2 %) |
| Metal BC1 vs PNG (reported, as for every pack steel) | p99.9 4 levels |

One metric sits under the pack's bar: at pure black and near-black the rank correlation of the texture with the
default is 0.95-0.97 (bar 0.98). The pack's own float model gives 1.0 there and the same 0.95-0.97 once stored in 8
bits, so this is the 8-bit output at the black floor (the pack's known case, as on the kunai wrap), not the recolour.

The colours were matched to the reference sheet under one physical studio light in Blender (the L5 check in
`WorkFiles/guns/smg/gates/uv_bake_paint.json`: polymer base sRGB 46 / 47 / 49).

## Good to know

- Polymer never shows metal: its wear is polish (smoother, slightly darker) where hands slide and whitening where it is
  struck. Bare steel shows only on the steel parts' real edges and sliding faces.
- No markings, serial numbers or logos are painted anywhere.
- `SK_SMG01.skeletal.json` lists the same masters under `materials` as the pack uses (`M_Steel_Master` for the metal,
  `M_Fabric_Master` with *Metal From ORM* off for the furniture); the magazine's slot is on `SM_SMG01_Mag`.
