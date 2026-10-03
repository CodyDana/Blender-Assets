# Throwing Needles (senbon): materials and colours (Unreal Engine 5.8)

This file explains the needles' Unreal materials: where they are, how to change the heavy needle's wrap colour, and
what to leave alone. The pack's content folder is `/Game/NinjaPack/` (a working name: the folder can be renamed, no
asset name contains it).

## Where things are

| Folder | What is in it |
|---|---|
| `/Game/NinjaPack/Meshes/` | `SM_Senbon_Needle`, `SM_Senbon_Heavy`, with their material slots already assigned |
| `/Game/NinjaPack/MaterialInstances/` | **The instances you edit**: `MI_Senbon_Needle_Steel`, `MI_Senbon_Heavy_Steel`, `MI_Senbon_Heavy_Wrap` |
| `/Game/NinjaPack/MaterialInstances/Base/` | `MI_Senbon_*_Base`: the textures and the settings matched to them. Leave these alone |
| `/Game/NinjaPack/Materials/` | The master materials. You never need to open these |
| `/Game/NinjaPack/Textures/Senbon/` | `T_Senbon_Needle_{BC,ORM,N}`, `T_Senbon_Heavy_{BC,ORM,N}`, `T_Senbon_Heavy_Wrap_{BC,ORM,N}`, `T_Senbon_Heavy_Wrap_Detail16` |

The needles only reference their own textures (and the pack's tiny neutral defaults), so they migrate on their own.

## Slots

| Mesh | Slot | Instance | Master | Covers |
|---|---|---|---|---|
| `SM_Senbon_Needle` | 0 `M_Senbon_Needle_Steel` | `MI_Senbon_Needle_Steel` | `M_Steel_Master` | The whole needle: blackened shaft, bright ground cones |
| `SM_Senbon_Heavy` | 0 `M_Senbon_Heavy_Steel` | `MI_Senbon_Heavy_Steel` | `M_Steel_Master` | Butt, body and the three-facet ground point |
| `SM_Senbon_Heavy` | 1 `M_Senbon_Heavy_Wrap` | `MI_Senbon_Heavy_Wrap` | `M_Fabric_Master` | The cotton thread wrap and its two bindings |

## The colour you can change

| Part | Instance to edit | Parameter | Shipped colour (Hex sRGB) | Lightest Colour |
|---|---|---|---|---|
| Heavy needle wrap | `MI_Senbon_Heavy_Wrap` | 01 Colour > Colour | `#373532` (the kunai grip's dark cotton) | `#CBCBCB` |

The steel keeps its steel look on both needles; it only takes the pack's optional **Steel Tint** (white = as
shipped), and **Roughness Adjust** if you want a brighter, more polished needle.

## Change the wrap colour in three steps

1. In the Content Browser, open `/Game/NinjaPack/MaterialInstances/MI_Senbon_Heavy_Wrap` (double-click).
2. At the top of the Details panel, in the group **01 Colour**, the **Colour** box is already ticked. Click its colour
   swatch.
3. Pick a colour, or type a web colour into the picker's **Hex sRGB** field (for example `8E2020` for a red cord).
   Click OK. The change is live in every level.

**Want a variant and keep the original?** Right-click `MI_Senbon_Heavy_Wrap` > **Create Material Instance** (or
Duplicate), change its colour, and assign it to slot 1 of the placed actor (Details panel > Materials).

**What the colour means.** It is the thread's *average* colour. The thread turns, the ply twist, the grooves and the
binding ends follow the new colour automatically.

## Good to know

- **Very light colours are capped** at the wrap's **Lightest Colour** (`#CBCBCB`). A pick lighter than that keeps its
  hue but is scaled down to it, so the thread keeps its detail. Tick **Lightest Colour** and raise it (0.9 = no cap)
  if you want it brighter.
- **Pure black is lifted** slightly (to about `#191919`), so the thread stays visible. Near black, the thread's fine
  detail falls on only a few 8-bit levels, the same as on the kunai grip.
- **Distance:** the wrap keeps the same average colour close up and far away (the material compensates for texture
  filtering at a distance; fitted on the real mip chain).
- **Cloth Sheen** is OFF, as on the kunai grip (Default Lit measured closer to the preview). Turning it on gives a soft
  fuzz at grazing angles.
- Textures: BC (sRGB), ORM (linear: AO, roughness, metallic), N (DirectX). `T_Senbon_Heavy_Wrap_Detail16` is the
  lossless 16-bit thread detail the recolour uses (import it sRGB OFF, Grayscale: it builds as G16). Its constants
  are in `Textures/Recolour/recolour_constants.json`.

## Get the original look back

- Click the **reset arrow** next to Colour (or untick it): it goes back to `#373532`.

## Checked (2026-10-03)

- Built from code with the rest of the pack (`run_build.sh`, tag `senbon_1003b`): 0 compile failures, every verify
  gate true. The six senbon instances were added; the 53 instances of the other items, the 3 masters and the 5
  functions are unchanged.
- The wrap's default look equals the shipped colour map (the pack's default-look gate passes) and every recolour
  capture (default, white, red, black) matches the material's reference maths within 1 level.
- PS instructions: steel 165, wrap 227 (the same as the kunai grip).
- Not tested: mobile, Substrate and forward shading with these exact instances (the masters are tested there).
