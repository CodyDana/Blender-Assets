# Smoke bomb: materials and colours (Unreal Engine 5.8)

This file explains the item's Unreal materials: where they are, how to change a colour, and what to leave alone.
The pack's content folder is `/Game/NinjaPack/` (a working name: the folder can be renamed, no asset name contains it).

## Where things are

| Folder | What is in it |
|---|---|
| `/Game/NinjaPack/Meshes/` | The static meshes, with their material slots already assigned |
| `/Game/NinjaPack/MaterialInstances/` | **The instances you edit**: one per material slot, named `MI_<Item>_<Part>` |
| `/Game/NinjaPack/MaterialInstances/Base/` | `MI_<Item>_<Part>_Base`: holds the textures and the settings matched to them. Leave these alone |
| `/Game/NinjaPack/MaterialInstances/Presets/` | Ready-made alternatives (for example the kunai's undyed grip) |
| `/Game/NinjaPack/Materials/` | The three master materials (`M_Steel_Master`, `M_Fabric_Master`, `M_PaperInk_Master`) and `Functions/`. You never need to open these |
| `/Game/NinjaPack/Textures/` | The textures, one folder per item, plus `Default/` (tiny neutral textures the masters use as placeholders) |

Every item only references its own textures, so you can migrate a single item to another project without dragging
the others along.

## The colours you can change

| Part | Instance to edit | Parameter | Shipped colour (Hex sRGB) | Lightest Colour |
|---|---|---|---|---|
| Cloth wrap | `MI_SmokeBomb_Cloth` | 01 Colour > Colour | `#3F3A37` | `#C5C5C5` |

## Change a colour in three steps

1. In the Content Browser, open `/Game/NinjaPack/MaterialInstances/MI_SmokeBomb_Cloth` (double-click).
2. At the top of the Details panel, in the group **01 Colour**, the **Colour** box is already ticked. Click its colour swatch.
3. Pick a colour, or type a web colour into the picker's **Hex sRGB** field (for example `8B1A1A`). Click OK. The change is live in every level.

**Want a variant and keep the original?** Editing `MI_SmokeBomb_Cloth` recolours every copy of the item in your project. For a
second colour, right-click `MI_SmokeBomb_Cloth` > **Create Material Instance** (or Duplicate), give it a name, change its colour, and
assign it to the mesh's material slot on the placed actor (Details panel > Materials).

**What the colour means.** It is the part's *average* colour. The threads, weave and wear are built into the material and follow
the new colour automatically, so you do not need to edit any texture. The picker's R/G/B numbers are linear values;
the Hex sRGB field is the one that matches colours from the web or from an image editor.

## Good to know

- **Very light colours are capped** at the part's **Lightest Colour** (group 01 Colour, `#C5C5C5` for this
  part). A pick lighter than that keeps its hue but is scaled down to it, so the bright threads keep their detail
  instead of turning into flat white. Want it brighter and accept softer highlights? Tick **Lightest Colour** and
  raise it (0.9 = no cap).
- **Pure black is lifted** to about `#191919`, so the threads and weave stay visible. Any colour with a channel above that is
  used as picked.
- **Distance:** the part keeps the same average colour close up and far away (the material compensates for texture
  filtering at a distance).
- **Detail Strength** (02 Detail): 1 = as shipped, 0 = flat colour. On very light colours the highlight detail is
  limited automatically, so values above 1 mainly deepen the darker weave.
- The smoke bomb's cloth has very bright single threads on a dark weave. On light colours the brightest threads
  are softened towards a gentle ceiling rather than cut off, so no flat white areas appear.
- The material shows the item's texture maps exactly. The original Blender preview renders reported the cloth a little
  darker (about 7 %) than its own maps, because of how Cycles filters 8-bit textures; Unreal shows the maps' true
  colour. If you prefer the darker preview tone, set the Colour about 7 % darker.

## Get the original look back

- Click the **reset arrow** next to a parameter (or untick it): it goes back to the value the item shipped with.
- Tick the box of **Use Original Baked Colours** (01 Colour) and switch it on to show the original baked colour map exactly as shipped,
  ignoring the colour settings.

## Leave these alone

- The `_Base` instances in `MaterialInstances/Base/`: they hold the textures and the settings matched to them.
- The group **08 Advanced (matched to the detail map - do not change)**: these numbers are computed from the item's textures.
  Changing them shifts the average colour and the detail.
- The textures in **09 Textures**: swap a detail map only together with its matched 08 Advanced settings.

## Supported setups

| Setup | Status |
|---|---|
| Unreal Engine 5.8, Windows, DirectX 12 desktop renderer, deferred shading | **Built and tested** (every material compiles; colours, recolours and the look measured) |
| Substrate enabled (`r.Substrate=True`) | **Tested**: compiles; base colour identical to deferred, lit result within 2 % (default and recoloured, all recolourable parts) |
| Forward shading (`r.ForwardShading=True`, for example VR) | **Tested**: compiles; lit result within 0.2 % of deferred |
| Optional Cloth Sheen switched on, under Substrate or forward shading | Not tested |
| Mobile (Android / iOS, ES3.1) | **Not tested.** The fabric and paper materials already use full float precision; their detail maps are 16-bit, which some mobile texture formats reduce to 8-bit |
| Instanced meshes, foliage, PCG scattering | Supported (the masters are flagged for instanced static meshes) |
| Nanite | Not flagged or tested; enable Nanite on the meshes and let the engine add the usage flag if you need it |
