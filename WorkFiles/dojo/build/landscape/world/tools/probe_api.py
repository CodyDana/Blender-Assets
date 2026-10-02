"""LANDSCAPE ROUND world stage, probe 1 (read-only): does DojoLab load with the Water plugin, and which Python API does
UE 5.8 offer for Landscape creation / heightmap import, Water bodies and their spline metadata? Writes json/probe_api.json.
Nothing is saved."""
import json
import traceback
from pathlib import Path

import unreal

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\landscape\world\json\probe_api.json")
R = {"engine": unreal.SystemLibrary.get_engine_version()}


def members(cls, pat=None):
    try:
        names = [m for m in dir(cls) if not m.startswith("_")]
    except Exception as exc:  # noqa: BLE001
        return f"ERR {exc}"
    if pat:
        names = [m for m in names if any(p in m.lower() for p in pat)]
    return names


try:
    R["unreal_landscape_names"] = [n for n in dir(unreal) if "landscape" in n.lower()]
    R["unreal_water_names"] = [n for n in dir(unreal) if "water" in n.lower()]
    R["unreal_pcg_names"] = [n for n in dir(unreal) if n.lower().startswith("pcg")][:40]
    for cname in ("Landscape", "LandscapeProxy", "LandscapeEditorSubsystem", "LandscapeSubsystem",
                  "LandscapeBlueprintBrushBase", "LandscapeImportHelper", "LandscapeEditorLibrary",
                  "WaterBodyRiver", "WaterBody", "WaterBodyComponent", "WaterSplineComponent", "WaterSplineMetadata",
                  "WaterZone", "WaterBodyRiverComponent", "WaterEditorSubsystem", "WaterSubsystem",
                  "LocalFogVolume", "InstancedStaticMeshComponent", "HierarchicalInstancedStaticMeshComponent",
                  "ProceduralMeshComponent", "DynamicMeshComponent", "LandscapeLayerInfoObject",
                  "LandscapeGrassType", "EditorLevelLibrary", "EditorAssetSubsystem", "NiagaraComponent"):
        cls = getattr(unreal, cname, None)
        R[cname] = members(cls) if cls is not None else None
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    R["load_level"] = bool(les.load_level("/Game/Dojo/Maps/L_Dojo"))
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    ws = w.get_world_settings()
    R["world_settings_members_partition"] = members(ws, ["partition", "kill", "bounds", "world"])
    try:
        R["world_partition"] = str(ws.get_editor_property("world_partition"))
    except Exception as exc:  # noqa: BLE001
        R["world_partition"] = "ERR " + str(exc)[:200]
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    acts = eas.get_all_level_actors()
    R["n_actors"] = len(acts)
    cls_count = {}
    for a in acts:
        k = a.get_class().get_name()
        cls_count[k] = cls_count.get(k, 0) + 1
    R["actor_classes"] = cls_count
    # plugin check
    try:
        R["water_plugin_river_material"] = bool(unreal.EditorAssetLibrary.does_asset_exist(
            "/Water/Materials/WaterSurface/Water_Material_River"))
    except Exception as exc:  # noqa: BLE001
        R["water_plugin_river_material"] = "ERR " + str(exc)[:200]
    for p in ("/Water/Materials/WaterSurface/Water_Material_River", "/Water/Materials/WaterSurface/Water_Material_Lake",
              "/Water/Textures/Foam/T_WaterFlow_01_Foam_Tiled"):
        try:
            a = unreal.load_asset(p)
            R.setdefault("water_assets", {})[p] = type(a).__name__ if a else None
        except Exception as exc:  # noqa: BLE001
            R.setdefault("water_assets", {})[p] = "ERR " + str(exc)[:120]
    # scalar params of the river material
    try:
        m = unreal.load_asset("/Water/Materials/WaterSurface/Water_Material_River")
        MEL = unreal.MaterialEditingLibrary
        R["river_scalar_params"] = [str(x) for x in MEL.get_scalar_parameter_names(m)]
        R["river_vector_params"] = [str(x) for x in MEL.get_vector_parameter_names(m)]
        R["river_texture_params"] = [str(x) for x in MEL.get_texture_parameter_names(m)]
    except Exception as exc:  # noqa: BLE001
        R["river_params_err"] = str(exc)[:300]
except Exception:  # noqa: BLE001
    R["error"] = traceback.format_exc()[-3000:]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
unreal.log(f"DJ_STEP_DONE probe_api passed={'error' not in R}")
