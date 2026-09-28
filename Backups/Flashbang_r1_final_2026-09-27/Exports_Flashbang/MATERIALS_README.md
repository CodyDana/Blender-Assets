# Flashbang: materials and colours (Unreal Engine 5.8)

This file explains the item's Unreal materials: where they are, how to change the paint colour, and what to leave
alone. The pack's content folder is `/Game/NinjaPack/` (a working name: the folder can be renamed, no asset name
contains it).

## Where things are

| Folder | What is in it |
|---|---|
| `/Game/NinjaPack/Meshes/` | `SM_Flashbang`, `SM_Flashbang_Body`, `SM_Flashbang_PullRing`, `SM_Flashbang_Lever`, with their material slots already assigned |
| `/Game/NinjaPack/MaterialInstances/` | **The instances you edit**: `MI_Flashbang_Paint` and `MI_Flashbang_Steel` |
| `/Game/NinjaPack/MaterialInstances/Base/` | `MI_Flashbang_Paint_Base`, `MI_Flashbang_Steel_Base`: the textures and the settings matched to them. Leave these alone |
| `/Game/NinjaPack/Materials/` | The master materials. You never need to open these |
| `/Game/NinjaPack/Textures/Flashbang/` | `T_Flashbang_BC`, `T_Flashbang_ORM`, `T_Flashbang_N`, `T_Flashbang_Paint_Detail16` |

The flashbang only references its own textures (and the pack's tiny neutral defaults), so it migrates on its own.

## Slots

| Slot | Instance | Master | Covers |
|---|---|---|---|
| 0 `M_Flashbang_Paint` | `MI_Flashbang_Paint` | `M_Fabric_Master`, with **Metal From ORM** on | The painted canister and upper band, their chipped edges and scratches, and the hole walls |
| 1 `M_Flashbang_Steel` | `MI_Flashbang_Steel` | `M_Steel_Master` | Base cap, collar, fuze housing and hinge, lever, ring and pin, and the brass charge cans |

The part meshes (`SM_Flashbang_PullRing`, `SM_Flashbang_Lever`) have only the Steel slot (slot 0). All four meshes use
the same two instances, so one colour change covers every piece.

## The colour you can change

| Part | Instance to edit | Parameter | Shipped colour (Hex sRGB) | Lightest Colour |
|---|---|---|---|---|
| Paint | `MI_Flashbang_Paint` | 01 Colour > Colour | `#494932` (olive) | `#CBCBCB` |

The steel parts keep their steel look; they only take the pack's optional **Steel Tint** (white = as shipped).

## Change the paint colour in three steps

1. In the Content Browser, open `/Game/NinjaPack/MaterialInstances/MI_Flashbang_Paint` (double-click).
2. At the top of the Details panel, in the group **01 Colour**, the **Colour** box is already ticked. Click its colour swatch.
3. Pick a colour, or type a web colour into the picker's **Hex sRGB** field (for example `B89B6A` for desert tan).
   Click OK. The change is live in every level.

**Want a variant and keep the original?** Right-click `MI_Flashbang_Paint` > **Create Material Instance** (or
Duplicate), change its colour, and assign it to slot 0 of the placed actor (Details panel > Materials).

**What the colour means.** It is the paint's *average* colour. The mottling, grime and wear follow the new colour
automatically. The chips, scratches and bare steel around the holes keep their metal colour whatever you pick: the
material reads them from the texture's metallic channel (**Metal From ORM**), so they stay steel on every colour.

## Good to know

- **Very light colours are capped** at the paint's **Lightest Colour** (`#CBCBCB`). A pick lighter than that keeps its
  hue but is scaled down to it, so the highlights keep their detail. Tick **Lightest Colour** and raise it (0.9 = no
  cap) if you want it brighter.
- **Pure black is lifted** slightly, so the paint's wear stays visible.
- **Distance:** the paint keeps the same average colour close up and far away (the material compensates for texture
  filtering at a distance).
- The textures are shared by both instances: BC (sRGB), ORM (linear: AO, roughness, metallic), N (DirectX). The ORM's
  roughness is combined with the normal map's detail at each mip (Composite Texture: Normal Roughness To Green), as on
  the pack's other hard-surface items.
- `Textures/Recolour/T_Flashbang_Paint_Detail16.png` is the lossless 16-bit paint detail the recolour uses (import it
  sRGB OFF, Grayscale: it builds as G16). Its constants are in `Textures/Recolour/recolour_constants.json`.

## Get the original look back

- Click the **reset arrow** next to Colour (or untick it): it goes back to `#494932`.
