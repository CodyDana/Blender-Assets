# Basic katana and saya: materials and colours (Unreal Engine 5.8)

This file covers the katana's and saya's Unreal materials:
- where they are;
- how to change the handle-wrap (ito) colour and the lacquer colour;
- what to leave alone.

The pack's content folder is `/Game/NinjaPack/`. That is a working name: the folder can be renamed, and no asset name
contains it.

## Where things are

| Folder | What is in it |
|---|---|
| `/Game/NinjaPack/Meshes/` | `SM_Katana` and `SM_Katana_Saya`, with their material slots already assigned |
| `/Game/NinjaPack/MaterialInstances/` | **The instances you edit**: `MI_Katana_Blade`, `MI_Katana_Fittings`, `MI_Katana_Grip`, `MI_Katana_Saya_Lacquer`, `MI_Katana_Saya_Fittings` |
| `/Game/NinjaPack/MaterialInstances/Base/` | `MI_Katana_*_Base`: the textures and the settings matched to them. Leave these alone |
| `/Game/NinjaPack/Materials/` | The master materials. You never need to open these |
| `/Game/NinjaPack/Textures/Katana/` | `T_Katana_Steel_{BC,ORM,N}`, `T_Katana_Grip_{BC,ORM,N}`, `T_Katana_Saya_{BC,ORM,N}`, `T_Katana_Grip_Detail16`, `T_Katana_Saya_Lacquer_Detail16` |

The katana and saya only reference their own textures (and the pack's tiny neutral defaults), so they migrate on
their own.

## Slots

| Mesh | Slot | Instance | Master | Covers |
|---|---|---|---|---|
| `SM_Katana` | 0 `M_Katana_Blade` | `MI_Katana_Blade` | `M_Steel_Master` | Blade (polished ji, burnished shinogi-ji and mune, frosted hamon); the blackened-iron tsuba, fuchi and kashira |
| `SM_Katana` | 1 `M_Katana_Fittings` | `MI_Katana_Fittings` | `M_Steel_Master` | Brass habaki, seppa, menuki and kashira eyelets; the bamboo mekugi |
| `SM_Katana` | 2 `M_Katana_Grip` | `MI_Katana_Grip` | `M_Fabric_Master` | The ito (cord) wrap and the ivory same (ray skin) in the diamond windows |
| `SM_Katana_Saya` | 0 `M_Katana_Saya_Lacquer` | `MI_Katana_Saya_Lacquer` | `M_Fabric_Master` | The black gloss lacquer body and the cavity |
| `SM_Katana_Saya` | 1 `M_Katana_Saya_Fittings` | `MI_Katana_Saya_Fittings` | `M_Steel_Master` | Black horn koiguchi, kurikata and kojiri; the brass cord-hole lining |

## The colours you can change

| Part | Instance to edit | Parameter | Shipped colour (Hex sRGB) | Lightest Colour |
|---|---|---|---|---|
| Handle wrap (ito) | `MI_Katana_Grip` | 01 Colour > Colour | `#19191B` (black cord) | `#CBCBCB` |
| Saya lacquer | `MI_Katana_Saya_Lacquer` | 01 Colour > Colour | `#1E1E20` (black roiro) | `#CBCBCB` |

**On the handle, only the cord changes colour.** The ivory same in the windows keeps its baked colour, because the
grip instance has *Metal From ORM* on and the master keeps every texel brighter than the cord. A red, navy or brown
ito over white same is therefore one colour pick.

**Lacquer.** The colour is the lacquer's *average* colour. Its gloss wear (duller where a hand holds the mouth end and
where the obi rubs the flats) and its hairline scratches live in the roughness map, so they stay on every colour. The
horn and brass fittings do not change.

**Steel parts.** The blade, fittings and saya fittings keep their look. They take only the pack's optional
**Steel Tint** (white = as shipped; it multiplies, so it can only darken or shift a colour) and **Roughness Adjust**.
- On `MI_Katana_Fittings`, Steel Tint shifts the brass, for example toward silver-grey or copper. The bamboo mekugi is
  on the same slot and is tinted with it.
- On `MI_Katana_Blade`, Steel Tint also tints the iron tsuba, fuchi and kashira. Leave it white unless you want a
  coloured blade.

## Change the ito or lacquer colour in three steps

1. In the Content Browser, open `/Game/NinjaPack/MaterialInstances/MI_Katana_Grip` (or `MI_Katana_Saya_Lacquer`).
2. In the Details panel's group **01 Colour**, the **Colour** box is already ticked. Click its swatch.
3. Pick a colour, or type a web colour into the picker's **Hex sRGB** field (for example `8E2020` for a red ito or
   `3A1E14` for a brown lacquer). Click OK. The change is live in every level.

**Want a variant and keep the original?** Right-click the instance > **Create Material Instance** (or Duplicate),
change its colour, and assign it to that slot of the placed actor (Details panel > Materials).

## Good to know

- **Very light colours are capped** at **Lightest Colour** (`#CBCBCB`). A pick lighter than that keeps its hue but is
  scaled down, so the cord weave and the lacquer wear keep their detail. Tick **Lightest Colour** and raise it
  (0.9 = no cap) if you want it brighter.
- **Pure black is lifted** slightly (to about `#191919`), so the cord and lacquer stay readable. Near black, the fine
  detail falls on only a few 8-bit levels; this is the same on every recolourable item in the pack.
- **Distance:** both parts keep the same average colour close up and far away. The material compensates for texture
  filtering at a distance; this was fitted on the real mip chain.
- **Window edges under strong recolours.** About 1,000 texels (0.35 % of the same) lie on the edge between cord and
  same. There, the compressed colour map falls into the master's keep ramp, so a very light or saturated ito colour
  tints a fringe about 0.1 mm wide around the windows. It is invisible at game distance.
- **Cloth Sheen** is OFF on both, as on the kunai grip.
- **Textures:**
  - BC: sRGB.
  - ORM: linear, TC_Masks, Texture Group World. Channels: AO, roughness, metallic.
  - N: DirectX, Flip Green OFF.
  - The two `*_Detail16` maps are the lossless 16-bit detail the recolour uses. Import them sRGB OFF, Grayscale;
    they build as G16. Their constants are in `Textures/Recolour/recolour_constants.json`.

## Get the original look back

Click the **reset arrow** next to Colour (or untick it). It goes back to `#19191B` (ito) or `#1E1E20` (lacquer).

## Checked (2026-10-03)

- **Build.** Built from code with the rest of the pack (`run_build.sh`, tag `katana_1003`, materials lock
  `katana-wf`): 0 compile failures, every verify gate true.
  - Added: the ten katana instances (five leaves and their `_Base`), 2 meshes and 11 textures.
  - Unchanged: the 59 instances of the other items, the 3 masters and the 5 functions.
- **Spec.** `material_spec.json` only gained the katana entries: with them removed, it equals the copy taken before.
- **Recolour constants** (`maps/derive_constants_katana.py`): every derive gate passes, both parts.
- **Unreal base-colour captures, ito.** The pack's capture analyser has no Metal From ORM branch, so the grip was
  analysed split by the master's keep weight (`WorkFiles/katana/final/materials/uv_capture_keep_split_katana.json`).
  - Cord texels: default vs the material's reference maths p99.9 1 level, mean 0.05. White, red and black recolours:
    p99.9 1 level.
  - White and red keep the cord detail: rank agreement 0.987 with the detail map.
  - The same keeps its colour: black is identical to the default; white and red as described under "Window edges".
- **Unreal base-colour captures, lacquer.** Default and every recolour within 1 level of the reference maths. White and
  red pass the recolour-quality gates. Black fails only on rank agreement (0.53), the pack's known near-black 8-bit
  trait, as on the kunai grip and the senbon wrap.
- **PS instructions:** steel 165, grip 235, lacquer 227.
- **Not tested:** mobile, Substrate and forward shading with these exact instances (the masters are tested there).
