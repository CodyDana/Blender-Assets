# Recoloring the cloak in Unreal Engine

Change the **CloakColor** vector parameter in the cloak's material instance. The cloth keeps its weave, roughness, and normal detail while the clasp and leather keep their own materials. **CloakColor represents the brightest yarn color**; the finished cloth will look darker in parts and will respond to your scene lighting.

## Choose a fixed color

1. Duplicate a supplied cloak material instance in the Content Browser and open the duplicate.
2. Enable the override beside **CloakColor**, then choose a color. When entering a color copied from a paint program or web hex code, use the color picker's **Hex sRGB** field. Leave alpha at 1.
3. Keep **FabricDetail = 1** for the supplied woven dye variation. Lower it for a more uniform color; **0** removes that color variation while preserving the normal map and roughness.
4. Assign the instance to every cloth material slot on the cloak mesh. Keep the clasp and leather slots assigned to their own materials. Select cloth slots by material/slot name rather than assuming that cloth is always index 0.

Unreal material instances expose parameters from their parent material, so changing a duplicated instance does not require editing the parent shader. [Epic: Material Instances](https://dev.epicgames.com/documentation/unreal-engine/instanced-materials-in-unreal-engine)

White, ivory, and pastel colors are supported. The material bounds its fabric variation before applying your color, so white does not erase the brighter parts of the weave through clipping. Use the color picker for a dye color; do not expect the viewport to display that exact flat swatch under every light. The picker distinguishes linear and sRGB inputs. [Epic: Color Picker](https://dev.epicgames.com/documentation/en-us/unreal-engine/color-picker?application_version=4.27)

## Change color during gameplay with Blueprint

1. In the character or cloak Actor's **BeginPlay**, drag from the cloak mesh component and add **Create Dynamic Material Instance**. Use the version whose target is the mesh/Primitive Component, set its **Element Index** to a cloth slot, and set **Source Material** to your cloak material instance.
2. Store the returned Material Instance Dynamic in a variable such as **CloakMID**. This component version creates and assigns the instance to that slot. If cloth occupies additional slots, assign that same **CloakMID** to those slots with **Set Material**; do not assign it to the metal or leather slots. A cloak split among several mesh components can share the same MID across its cloth components.
3. When the player chooses a color, drag from **CloakMID** and call **Set Vector Parameter Value**, using **CloakColor** for Parameter Name and the chosen Linear Color for Value. The node's target must be **Material Instance Dynamic**. The similarly named Material Parameter Collection node controls a different system.
4. Create one MID per character/cloak that needs an independent color. Reuse it for later changes instead of creating a new instance each time. Use **Set Scalar Parameter Value** on that MID if you also want to change **FabricDetail**.

The mesh component API creates a dynamic instance for a specified material element, and MID vector parameters accept an `FLinearColor`. [Epic: UPrimitiveComponent](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/UPrimitiveComponent), [Epic: SetVectorParameterValue](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/Engine/UMaterialInstanceDynamic/SetVectorParameterValue)

## Texture settings when rebuilding the material

| Texture | sRGB | Sampling / connection |
| --- | --- | --- |
| `T_BlackCloak_BaseColor` | On | Color sampler; red channel supplies the cloth variation |
| `T_BlackCloak_Roughness` | Off | Linear grayscale to Roughness |
| `T_BlackCloak_Normal_DirectX` | Off | Normalmap compression and Normal sampler to Normal; Flip Green Channel off |

Use the supplied DirectX normal for Unreal. Its green channel is already inverted from the Blender/OpenGL normal. Keep the supplied mesh UVs: the FBX/GLB export already includes the fabric repeat, so an additional 7.8125 UV scale would apply the repeat scale a second time. Unreal's texture settings expose color-space and green-channel controls. [Epic: Texture Asset Editor](https://dev.epicgames.com/documentation/en-us/unreal-engine/texture-asset-editor-in-unreal-engine)

---

## Internal implementation review — remove before publishing if not needed

Reviewed formula:

```text
DetailMask = Saturate(SampledBaseColor.R / 0.013702083)
Detail = Lerp(1, DetailMask, Saturate(FabricDetail))
BaseColor = Saturate(CloakColor.rgb) * Detail
```

The sampled texture must be decoded from sRGB to linear by the texture sampler before this division. The denominator is the linear sRGB value of the highest source red byte, 31/255. It is not a gamma-encoded brightness value and should not receive an additional manual gamma correction.

Measured directly from `Exports/BlackCloak/Textures/T_BlackCloak_BaseColor.png` on 2026-09-22:

- Source red bytes: 21–31.
- Mean linear RGB: `(0.00997249218, 0.00992928370, 0.00976078147)`.
- Bounded mask range: approximately `0.54729139–1.0`.
- With FabricDetail in 0–1 and CloakColor RGB in 0–1, the formula cannot clip any positive weave variation at white or pastel colors.
- At FabricDetail 1, the black preset `(0.013702083, 0.013642715, 0.013411195, 1)` preserves the original red channel and approximates its mean green/blue ratios. Individual green/blue source quantization cannot be reconstructed exactly from one red-channel mask.
- At FabricDetail 0, BaseColor is exactly the linear color parameter; normal and roughness detail are independent.
- Negative/HDR tint entries are bounded by Saturate. Alpha does not drive opacity.

This approach corrects the clipping found in the earlier mean-normalized proposal (`R/0.010025825`): that proposal would clip 46.36% of source texels at pure white and full detail. The bounded mask changes the parameter's meaning from average dye color to brightest yarn color, which the public instructions above state explicitly.

Runtime instructions were checked against official Epic documentation and the installed Unreal 5.8 source:

- `Engine/Source/Runtime/Engine/Private/Components/PrimitiveComponent.cpp`, lines 2620–2643: component `CreateDynamicMaterialInstance` gets/creates the MID and calls `SetMaterial` on its selected element.
- `Engine/Source/Runtime/Engine/Public/Materials/MaterialInstanceDynamic.h`, lines 107–109: `SetVectorParameterValue` is BlueprintCallable and accepts `FName` plus `FLinearColor`.

This independent review checked the source texture math and API usage. Actual `.uasset` compilation, slot assignment, and in-editor rendering belong to the export agent's validation; those checks are not claimed here.
