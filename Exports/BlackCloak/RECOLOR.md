# Recolorable cloak — Unreal Engine 5.8

This package includes a native Unreal material with a **CloakColor** control. No texture repainting is needed. Geometry and original Blender/FBX/GLB files retain their existing shape and black default appearance.

## Bring it into your game

1. Open `Unreal/BlackCloakRecolor.uproject` with Unreal Engine 5.8. The supplied assets were saved and reloaded in 5.8.2.
2. In the Content Browser, open `Content/BlackCloak`. Right-click the folder and choose **Migrate**, then choose your game's **Content** folder. This carries the meshes, materials and texture dependencies together.
3. Use `Meshes/SM_BlackCloak` for a static cloak, or `Meshes/SK_BlackCloak` for the existing skeleton attachment version. The cloth slots already use `Materials/MI_Cloak_Black`; the clasp and leather have separate materials.
4. Duplicate `MI_Cloak_Black` (or one of the Crimson, Navy, Ivory presets), open it, enable **CloakColor**, and choose your color.

The prepared Unreal meshes contain LOD0. The separate FBX LOD1/LOD2 files remain in the main package. Cloth simulation and character movement fitting are separate unfinished work.

## Included color assets

| Asset | Purpose |
| --- | --- |
| `M_Cloak_Recolor` | Parent material with adjustable cloth color and fabric detail |
| `MI_Cloak_Black` | Default black cloth |
| `MI_Cloak_Crimson` | Red example |
| `MI_Cloak_Navy` | Blue example |
| `MI_Cloak_Ivory` | Light-colored example |
| `M_Cloak_BlackenedSteel` | Separate clasp material |
| `M_Cloak_CharcoalLeather` | Separate attachment loop material |

## Color controls

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
