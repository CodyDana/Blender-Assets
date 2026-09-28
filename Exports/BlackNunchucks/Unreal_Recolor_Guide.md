# Recoloring Black Nunchucks in Unreal

The asset has 16 independent color regions on one material. You can recolor one grip, one cap, one connector, one chain link, or a weld seam without recoloring the others. The original black-and-silver appearance is the default. Geometry, UVs, skin weights, and the three mesh LODs are unchanged.

## Use the included Unreal assets

Open `UnrealDemo/BlackNunchucksRecolor.uproject` in Unreal Engine 5.8. In the Content Browser, migrate the `BlackNunchucks` folder to your game's `Content` folder using **Asset Actions → Migrate**. This carries the mesh, materials, and texture dependencies together.

Assign `MI_BlackNunchucks_Default` to material slot 0 of the skeletal mesh. Open the material instance to inspect the controls. Duplicate this instance outside the importer-owned `/Game/BlackNunchucks` folder to save your own presets. `MI_BlackNunchucks_Demo` is an example preset.

Alternatively, enable Python Editor Script Plugin and Editor Scripting Utilities in your project and run `Scripts/BlackNunchucks/unreal_recolor_setup.py` from the extracted package. This imports the source FBX and PNG files and builds `/Game/BlackNunchucks`. Re-running the script rebuilds the supplied master and demo instances, so keep your custom presets elsewhere.

## Change colors in the material editor

Each region has two parameters:

- `Amount_<Part>`: 0 keeps the original texture; 1 applies the selected color. Values between 0 and 1 blend the appearances.
- `Color_<Part>`: the new color. This can be white or another bright color; the shader removes the original black pigment while retaining the texture detail.

For example, set `Amount_Grip_L` to **1**, then choose a red `Color_Grip_L`. The right grip and metal remain unchanged. Set the amount back to **0** to restore the original grip.

| Region | Parameter suffix |
|---|---|
| Left grip | `Grip_L` |
| Right grip | `Grip_R` |
| Left silver cap | `Cap_L` |
| Right silver cap | `Cap_R` |
| Left attachment eye | `Eye_L` |
| Right attachment eye | `Eye_R` |
| Seven chain links, left to right | `Chain_01` through `Chain_07` |
| Weld seam on links 3, 4, and 5 | `Weld_03`, `Weld_04`, `Weld_05` |

For a uniform color across a welded link, set the link and its corresponding weld parameters to the same color and amount.

## Change colors during gameplay

In your actor's Blueprint:

1. On BeginPlay, call **Create Dynamic Material Instance** on the mesh, using element index **0** and `MI_BlackNunchucks_Default` as the source. Store the returned instance in a variable, such as `NunchucksMaterial`.
2. On the returned instance, call **Set Scalar Parameter Value** with name `Amount_Grip_L` and value **1**.
3. Call **Set Vector Parameter Value** with name `Color_Grip_L` and the player's chosen color.
4. Repeat the parameter calls for any other regions the player changes. Reuse the same dynamic instance; do not recreate it for each color change.

Each weapon should have its own dynamic instance so one player's choices do not recolor other weapons. Save the player's colors and amounts in your game's save data and reapply them when spawning the weapon. The asset supplies the material controls; your game supplies the customization UI and save logic.

## Full reskins

`Texture_BaseColor`, `Texture_Normal`, and `Texture_ORM` are texture parameters. Swap them for another texture set using the same UV layout, either in a saved material instance or with **Set Texture Parameter Value** on the dynamic instance. Keep all `Amount_*` values at 0 to display a replacement skin exactly as authored.

If you want to tint a replacement skin too, supply its matching neutral modulation texture using `Texture_TintDetail`. Otherwise the recolored regions will keep the supplied grip-grain modulation. The four `Texture_PartMask0` through `Texture_PartMask3` parameters define the region boundaries and normally stay unchanged.

Normal maps use DirectX convention in Unreal: `blacknunchucks_normal.png`, normal-map compression, sRGB off, green flip off. ORM is linear data with R=AO, G=roughness, B=metallic. Recoloring changes base color and preserves the existing surface finish; swap the ORM map to change rubber/metal behavior for a new skin.

## Blender and exchange files

The Blender file includes an optional `M_BlackNunchucks_RecolorPreview` material with matching color and amount controls. The default assigned material remains the simple baked PBR material, so FBX/GLB retain the original appearance. FBX and GLB do not carry Unreal's runtime material graph: use the native Unreal material or the included setup script.

## Mask layout

All four masks are 4096×4096 RGBA data textures. Their alpha channels are independent masks, not transparency. Keep sRGB off, use masks compression, and preserve alpha. The setup script configures these settings.

| Texture | R | G | B | A |
|---|---|---|---|---|
| `partmask0` | Grip_L | Grip_R | Cap_L | Cap_R |
| `partmask1` | Eye_L | Eye_R | Chain_01 | Chain_02 |
| `partmask2` | Chain_03 | Chain_04 | Chain_05 | Chain_06 |
| `partmask3` | Chain_07 | Weld_03 | Weld_04 | Weld_05 |

The masks cover UV islands from all three LODs and include padding around the islands. `recolor_parameters.json` contains the exact mapping and sample coordinates.

Epic references: [Material instances](https://dev.epicgames.com/documentation/unreal-engine/instanced-materials-in-unreal-engine) and [texture masks](https://dev.epicgames.com/documentation/unreal-engine/using-texture-masks-in-unreal-engine).
