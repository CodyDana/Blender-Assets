# Paper bomb (explosive tag): materials and colours (Unreal Engine 5.8)

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

All three are in the one instance `MI_PaperBomb_Tag`, group **01 Colour**, and all three are already ticked.

| Colour | What it changes | Shipped (Hex sRGB) |
|---|---|---|
| **Paper Colour** | The paper, with its grain, ageing, stains and the show-through on the back | `#F3E3C3` |
| **Black Ink Colour** | The brushed text and emblem; the dry-brush strokes follow it | `#0F0F0E` |
| **Red Ink Colour** | The border, ring and seals; the dry and pooled strokes follow it | `#D5180B` |

## Change a colour in three steps

1. In the Content Browser, open `/Game/NinjaPack/MaterialInstances/MI_PaperBomb_Tag` (double-click).
2. At the top of the Details panel, in the group **01 Colour**, the **Paper Colour**, **Black Ink Colour** and **Red Ink Colour** boxes are already ticked. Click the swatch of the one you want to change.
3. Pick a colour, or type a web colour into the picker's **Hex sRGB** field (for example `8B1A1A`). Click OK. The change is live in every level.

**Want a variant and keep the original?** Editing `MI_PaperBomb_Tag` recolours every copy of the item in your project. For a
second colour, right-click `MI_PaperBomb_Tag` > **Create Material Instance** (or Duplicate), give it a name, change its colour, and
assign it to the mesh's material slot on the placed actor (Details panel > Materials).

**What the colour means.** It is the part's *average* colour. The paper grain, ink edges and dry-brush strokes are built into the material and follow
the new colour automatically, so you do not need to edit any texture. The picker's R/G/B numbers are linear values;
the Hex sRGB field is the one that matches colours from the web or from an image editor.

## Good to know

- **The lightest paper is about `#F4F4F4`.** A lighter Paper Colour keeps its hue but is scaled down to it, so the
  grain never turns into flat white. **Pure black paper is lifted** to about `#191919` so the grain stays visible;
  very dark papers show the grain only faintly (that is the limit of 8-bit colour, not a fault).
- **Inks are flat colour inside solid strokes**, as painted ink is; their edges, dry-brush strokes and pools carry the
  texture. A white or very light ink therefore reads as a flat light shape inside the strokes.
- **Pooled red ink is always darker** than the Red Ink Colour (ink pools dry dark). A neutral red-ink colour (grey,
  white, black) pools neutral.
- **Baked AO In Colour** (03 Surface): 1 = the original look, where the baked shading also darkens the colour; 0 = none.

## Get the original look back

- Click the **reset arrow** next to a parameter (or untick it): it goes back to the value the item shipped with.
- Tick the box of **Use Original Baked Colours** (01 Colour) and switch it on to show the original baked colour map exactly as shipped,
  ignoring the colour settings.

## Leave these alone

- The `_Base` instances in `MaterialInstances/Base/`: they hold the textures and the settings matched to them.
- The group **08 Advanced (matched to the paper maps - do not change)**: these numbers are computed from the item's textures.
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
