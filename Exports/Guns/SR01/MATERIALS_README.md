# Sniper Rifle SR-01: materials and colours (Unreal Engine 5.8)

This file covers:
- the texture sets and which slot uses which;
- how to import the maps (colour spaces, compression, channels);
- the pack's material instances;
- the OD-paint recolour (not safe on this item yet; the pack's recolour-quality gate P3b also fails on it).

> **The pack builds the SR-01's material instances** from the shared masters `M_Steel_Master` and `M_Fabric_Master`,
> as on the AR-01 and the SMG. No master was changed for the SR-01.
>
> | Instance (on the mesh) | Holds the settings | Master | Slot |
> |---|---|---|---|
> | `MI_SR01_Metal` | `MI_SR01_Metal_Base` | `M_Steel_Master` | `M_SR01_Metal` |
> | `MI_SR01_Chassis` | `MI_SR01_Chassis_Base` | `M_Fabric_Master` (Metal From ORM ON, *Use Original Baked Colours* ON) | `M_SR01_Chassis` |
> | `MI_SR01_Mag` | `MI_SR01_Mag_Base` | `M_Steel_Master` | `M_SR01_Mag` |
> | `MI_Att_Scope_LongRange_Body` | `MI_Att_Scope_LongRange_Body_Base` | `M_Steel_Master` | `M_Att_Scope_Body` |
> | `MI_Att_Scope_LongRange_Lens` | `MI_Att_Scope_LongRange_Lens_Base` | `M_Steel_Master` | `M_Att_Scope_Lens` |
>
> - The `_Base` instance holds every texture and matched setting. The instance on the mesh overrides only its colour.
>   Reset to default gives back the shipped look.
> - **Every instance shows the baked maps exactly.** The OD ships as baked.
>
> **Build status (2026-10-16):** the spec entries, the recolour maps and constants are done, and every check that
> needs no Unreal passes. The Unreal build and its gates are pending (`WorkFiles/guns/sniper/pack/run_pack_build.sh`;
> results in `WorkFiles/guns/sniper/gates/pack_materials.json`). Until it has run, use the maps with any standard PBR
> material:
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
| `*_BC` | sRGB on. Metal and scope: compression Default (BC1). **Chassis and Mag: BC7** (the pack imports them as BC7). The SMG's dark polymer BCs drifted 5-8 levels with BC1 and 2 with BC7. The pack build measures both on the SR-01. If BC1 is within 2 levels there, the pack may switch to BC1 to save memory |
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

## Colours: the OD ships as baked; recolour is not safe on this item yet

- **Shipped:** `MI_SR01_Chassis_Base` has *Use Original Baked Colours* ON. The default look is the BC itself: the OD
  paint with its peel, rub, chips and polish, the black anodize, the polymer grip and the rubber pad.
- **Do not switch *Use Original Baked Colours* off on the SR-01.** The Chassis set also carries the black anodize, the
  polymer grip and the rubber pad: 28 % of its painted texels. `M_Fabric_Master` has no mask input. With the switch
  off, the recolour path would tint the grip, the pad and the bipod as well as the paint.
- **The recolour will be the OD paint only, and only after a future master switch.** The plan is one static switch
  on `M_Fabric_Master`, default off, that masks the tint with Masks A (option D1-b in
  `WorkFiles/guns/sniper/pack_materials_proposal.md`). It is not built. When it is, the recolour group `SR01` (one
  member, `M_SR01_Chassis`) is ready: the buyer picks one **Colour** for the paint, and the paint's wear follows it.
- **Even with that switch, one Colour cannot hold all of the OD's hue.** On the OD, the default recolour path is
  within 1 level of the BC at p99 and 3 levels at p99.9 (bar 2). That is why the shipped instance keeps the BC.
- **Your own paint colour today:** in your own material, lerp between the BC and your tinted colour with Masks A as
  the mask (A = 1 only on the OD paint).
- **The magazine, the metal and the scope have no OD paint.** They are baked, on `M_Steel_Master`.
- **Measured in the pack build `sr01_1016` (2026-10-16):** the shipped default equals the BC (P1), the recolour path matches the pack's float twin (P2) and the 13-colour stress test passes against the twin (P3a), but the pack's v3 recolour-quality gate (P3b: detail kept, Spearman vs the default >= 0.98) fails on 11 of 13 colours, not only at the 8-bit black floor. A recoloured OD would lose part of its wear detail. One more reason the item ships baked; a recolour needs D1-b plus a recolour-specific detail pass first. Details: `WorkFiles/guns/sniper/gates/pack_materials.json`.

**Recolour files (pack schema).**
- `Recolour/T_SR01_Chassis_Detail16.png` (2048, 16-bit linear): normalised luminance over the OD texels (Masks A = 1),
  written by `WorkFiles/guns/sniper/materials/sr01_recolour_maps.py`.
- `Recolour/recolour_maps.json` (schema `ninjapack.recolour_maps/1`): records the map, the group and the defaults.
- `Recolour/recolour_constants.json`: the matched settings for the master's detail model. Written by the pack's
  `maps/derive_constants_sr01.py`; every gate passes.
- Default Colour (linear): about 0.080 / 0.081 / 0.058.
- These replace the preliminary maps from the surface stage. Only textures and JSON changed; the meshes did not.

## Metal and scope

- **Metal, magazine and scope:** baked finishes, not designed to be recoloured. Their `M_Steel_Master` instances have
  one colour control, **Steel Tint** (white = as shipped), which multiplies the base colour. The magazine is on
  `M_Steel_Master`, as on the AR-01: it has no OD paint, and the steel master shows its BC exactly. The bare-steel wear comes from
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

The Chassis set is the largest: 4096 BC (BC7) + N + ORM. The pack build's render step records the memory in Unreal
(full mips) in `WorkFiles/guns/sniper/gates/pack_materials.json` (R2).
