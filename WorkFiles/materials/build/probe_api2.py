import json
from pathlib import Path
import unreal
OUT = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/materials/build/probe_api2.json")
MEL = unreal.MaterialEditingLibrary
R = {"outputs": {}}
mat = unreal.Material()
for w in ["VectorParameter", "TextureSampleParameter2D", "TextureSample", "FunctionInput", "StaticSwitchParameter", "If",
          "Multiply", "ComponentMask", "Constant4Vector", "Constant3Vector", "TextureCoordinate", "ScalarParameter",
          "TextureObjectParameter", "ShadingModel", "MakeMaterialAttributes", "AppendVector"]:
    c = getattr(unreal, "MaterialExpression" + w)
    e = MEL.create_material_expression(mat, c, 0, 0)
    try:
        R["outputs"][w] = [str(n) for n in MEL.get_material_expression_output_names(e)]
    except Exception as exc:
        R["outputs"][w] = repr(exc)
    try:
        R.setdefault("input_types", {})[w] = [str(n) for n in MEL.get_material_expression_input_types(e)]
    except Exception as exc:
        R.setdefault("input_types", {})[w] = repr(exc)
EAL = unreal.EditorAssetLibrary
R["assets"] = {p: EAL.does_asset_exist(p) for p in [
    "/Engine/BasicShapes/Plane", "/Engine/BasicShapes/Cube", "/Engine/MapTemplates/Sky/SunsetAmbientCubemap",
    "/Engine/MapTemplates/Sky/DaylightAmbientCubemap", "/Engine/EngineResources/GrayDarkTextureCube",
    "/Engine/EditorMaterials/AssetViewer/EpicQuadPanorama_CC+EV1", "/Engine/EngineMaterials/WorldGridMaterial",
    "/Engine/EngineMaterials/DefaultMaterial", "/Engine/MapTemplates/Sky/M_SimpleSkyDome",
    "/Engine/EditorMaterials/AssetViewer/T_EpicQuadPanorama_CC", "/Engine/EngineSky/SM_SkySphere"]}
R["ar_cubes"] = []
try:
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    flt = unreal.ARFilter(class_paths=[unreal.TopLevelAssetPath("/Script/Engine", "TextureCube")], package_paths=["/Engine"], recursive_paths=True)
    R["ar_cubes"] = [str(a.package_name) for a in ar.get_assets(flt)][:60]
except Exception as exc:
    R["ar_cubes"] = repr(exc)
R["pp"] = [n for n in dir(unreal.PostProcessSettings) if "exposure" in n.lower()][:60]
R["aem"] = [n for n in dir(unreal.AutoExposureMethod) if n.startswith("AEM")]
R["smesub"] = [n for n in dir(unreal.StaticMeshEditorSubsystem) if "material" in n.lower() or "section" in n.lower() or "lod" in n.lower()]
R["sm"] = [n for n in dir(unreal.StaticMesh) if "section" in n.lower() or "lod" in n.lower()]
R["skylight"] = [n for n in dir(unreal.SkyLightComponent) if not n.startswith("_")][:200]
OUT.write_text(json.dumps(R, indent=1, default=str))
print("NP_PROBE_API2_DONE")
