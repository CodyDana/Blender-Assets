# Flashbang: materials and colours (Unreal Engine 5.8)

This file explains the item's Unreal materials: where they are, how to change the paint colour, and what to leave
alone. It follows the pack's other items (see the smoke bomb's `MATERIALS_README.md` for the folder layout).

## Slots

| Slot | Instance | Master | Covers |
|---|---|---|---|
| 0 `M_Flashbang_Paint` | `MI_Flashbang_Paint` | `M_Fabric_Master`, with **Metal From ORM** on | The painted body and upper band, the chipped edges and the hole walls |
| 1 `M_Flashbang_Steel` | `MI_Flashbang_Steel` | `M_Steel_Master` | Base cap, collar, fuze housing, hinge, lever, ring and pin, and the brass inner tube |

The part meshes (`SM_Flashbang_PullRing`, `SM_Flashbang_Lever`) have only the Steel slot. All four meshes use the same
two instances, so one colour change covers every piece.

## The colour you can change

| Part | Instance to edit | Parameter | Shipped colour (Hex sRGB) |
|---|---|---|---|
| Paint | `MI_Flashbang_Paint` | 01 Colour > Colour | `#4C4C34` (olive) |

The steel parts keep their steel look; they only take the pack's optional **Steel Tint** (white = as shipped).

## Change the paint colour in three steps

1. In the Content Browser, open `MI_Flashbang_Paint` (double-click).
2. In the group **01 Colour**, click the **Colour** swatch.
3. Pick a colour, or type a web colour into **Hex sRGB**, and click OK.

The chips, scratches and bare steel around the holes keep their metal colour whatever paint colour you pick: the
material reads them from the texture's metallic channel (Metal From ORM). The grime and mottling follow the new colour.

## Good to know

- The textures are shared by both instances: BC (sRGB), ORM (linear: AO, roughness, metallic), N (DirectX).
- `Textures/Recolour/T_Flashbang_Paint_Detail16.png` is the lossless 16-bit paint detail the recolour uses; its
  constants are in `Textures/Recolour/recolour_maps.json`.
- The pack's material instances for this item are built by the pack's materials build step (the lightest-colour and
  mip constants are derived there).
