# Sniper Rifle SR-01: materials and colours (Unreal Engine 5.8)

This file covers:
- the texture sets and which slot uses which;
- how to import the maps (colour spaces, compression, channels);
- the planned OD-paint recolour.

> **The pack's material instances for the SR-01 are not built yet.** The pack's shared masters are `M_Steel_Master`
> and `M_Fabric_Master`, as on the AR-01 and the SMG. The instances `MI_SR01_Metal`, `MI_SR01_Chassis`,
> `MI_SR01_Mag`, `MI_Att_Scope_LongRange_Body` and `MI_Att_Scope_LongRange_Lens` (each with its `_Base`) are
> specified, not built. The maps below are complete and work with any standard PBR material:
> - BaseColor = BC;
> - AO / Roughness / Metallic = ORM R / G / B;
> - Normal = N.

## Texture sets and slots

| Mesh | Slot | Set | Size | Covers |
|---|---|---|---|---|
| `SK_SR01`, `SM_SR01` | 0 `M_SR01_Metal` | `T_SR01_Metal_*` | 2048 | The steel: receiver, 15-slot rail, fluted barrel and compensator, bolt (bead-blasted satin body, phosphate shroud) and handle, trigger, safety, release paddle, pins and socket-head screws. Phosphate and black finishes with bare-steel wear only where parts rub |
| `SK_SR01`, `SM_SR01` | 1 `M_SR01_Chassis` | `T_SR01_Chassis_*` | 4096 | The chassis set: the **OD painted** aluminium chassis, forend, butt and cheek riser (orange-peel finish, edge rub, chips to dark anodize, handling polish, recess dust); the **black anodized** bipod and hardware; the **polymer** grip (hot-iron stipple); the **rubber** butt pad |
| `SM_SR01` (merged magazine), `SM_SR01_Mag` | 2 / 0 `M_SR01_Mag` | `T_SR01_Mag_*` | 1024 | The 10-round magazine: phosphated steel body and polymer parts. No OD paint |
| `SM_Att_Scope_LongRange` | 0 `M_Att_Scope_Body` | `T_Att_Scope_LongRange_Scope_Body_*` | 2048 | Black anodized tube, rings, turrets (generic tick and numeral markings, no brand), eyepiece and objective bell |
| `SM_Att_Scope_LongRange` | 1 `M_Att_Scope_Lens` | `T_Att_Scope_LongRange_Scope_Lens_*` | 512 | The lenses: opaque, glossy, a dark green-black centre with a violet / amber coating ring and a convex normal. The lenses are not transparent. A game's scope view is its own material or render target |

- **UV tiles:** on the static twin, each slot's UV0 sits in its own U tile (Metal 0..1, Chassis 1..2, merged
  magazine -1..0). The scope's Body is in 0..1 and its Lens in 1..2. Keep the address mode on *Wrap* (the default) so
  every tile reads the same texels. The skeletal mesh keeps both sets in 0..1.
- **Shared slots:** `SK_SR01` and `SM_SR01` share the Metal and Chassis slots; `SM_SR01` and `SM_SR01_Mag` share
  the Mag slot.

## Import the maps

| Map | Setting |
|---|---|
| `*_BC` | sRGB on. Compression Default (BC1). For the Chassis and Mag BC, BC7 is recommended if the dark wear must match exactly (the SMG's polymer BCs drifted 5-8 levels with BC1 and 2 with BC7; not yet measured on the SR-01) |
| `*_ORM` | sRGB off, compression Masks, no alpha. R ambient occlusion, G roughness, B metallic (0 or 1). Optional: set the composite texture to the set's normal map (*Normal Roughness To Green*, power 1) to cut specular shimmer at distance |
| `*_N` | Normal map compression, **DirectX** convention (green already flipped, *Flip Green Channel* off). 16-bit source. Group `WeaponNormalMap` in a game |
| `*_Masks` (half size) | sRGB off, compression Masks. **Not used by the pack's materials**; for your own wear or dirt layer. Channels below |
| `Recolour/T_SR01_Chassis_Detail16` (2048) | sRGB off, compression Grayscale (builds as G16, lossless): the OD paint's detail map for the recolour |

- Every map is a square power of two. Keep full mip chains (the 4096 maps have 13 mips).
- Measured in Unreal 5.8.3, with streaming on: the Metal and Chassis BC and N were at the top mip both at the hip and
  at ADS.
- **Texture group:** `Weapon` for BC, ORM and Detail16 in a game.

### Masks channels (`*_Masks`)

| Channel | Meaning |
|---|---|
| R | Edge-wear propensity (convex edges and corners) |
| G | Handling (where hands and gear rub) |
| B | Cavity (recesses that collect dust) |
| A | Refinishable: **1 only on the OD paint**, 0 on anodize, polymer, rubber and steel (on the Metal, Mag and scope sets A is 0 everywhere) |

## The recolour plan (OD paint = the user colour)

- **What is planned:** one recolour group `SR01` with one member, `M_SR01_Chassis`. The buyer picks one **Colour**
  for the OD paint (tan, black, grey, FDE...). The paint's peel, rub, chips and polish then follow the new colour.
  The metal, the magazine and the scope stay baked.
- **The shipped instance shows the baked colours** (*Use Original Baked Colours* ON). The OD's chip and rub hue is
  finer than one Colour can hold: the default recolour path is within 1 level at p99 and 4 levels at p99.9 of the BC,
  against the pack's 2-level bar.

**Open point before the instances are built.** The Chassis set also carries the black anodize, the polymer grip and
the rubber pad: 28 % of its painted texels. The pack's `M_Fabric_Master` has no mask input, so switching off the baked
colours would tint those parts too. Masks A already marks exactly the OD paint. The fix is either:
- a small mask switch on the master; or
- keeping the SR-01 baked-only until that switch exists.

The proposal and its gates are in `WorkFiles/guns/sniper/pack_materials_proposal.md`. Until then, **do not switch
off the baked colours on the Chassis**. For a different paint colour in your own material, use Masks A as the lerp
mask between the BC and your tinted colour.

`Recolour/recolour_maps.json` and `Recolour/T_SR01_Chassis_Detail16.png` are the preliminary maps from the surface
stage. They use the same OD texels (Masks A) and the same default Colour (linear about 0.080 / 0.082 / 0.058). The
pack build rewrites them in the pack's schema and adds `recolour_constants.json`, the matched settings for the
master's detail model.

## Metal and scope

- **Metal and scope:** baked finishes, not designed to be recoloured. The planned `M_Steel_Master` instances have one
  colour control, **Steel Tint** (white = as shipped), which multiplies the base colour. The bare-steel wear comes from
  the ORM's metallic channel, so a strong tint also colours the worn edges.
- **Lens:** stays dark and glossy.

## Memory (source maps)

The sets are:
- Metal 2048;
- Chassis 4096;
- Mag 1024;
- Scope Body 2048 and Lens 512;
- Masks at half size;
- Detail16 2048.

In Unreal with BC1 / Masks / normal compression and full mips, the Chassis set is the largest: 4096 BC + N + ORM.
Measure the total with the pack build; it is not recorded here.
