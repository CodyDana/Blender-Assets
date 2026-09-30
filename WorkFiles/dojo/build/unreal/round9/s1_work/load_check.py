"""Round 9 A: DojoLab load check after enabling ProceduralVegetationEditor (read-only: loads L_Dojo, saves nothing).
Reports the enabled plugins of interest, r.Nanite.Foliage, the level's actor count and the UDS actor, then prints
DJ_LOADCHECK <json>. Run by run_ue.sh (-nullrhi commandlet)."""
import json
import unreal

out = {}
try:
    names = set(unreal.PluginBlueprintLibrary.get_enabled_plugin_names())
    out["plugins"] = {n: (n in names) for n in ("ProceduralVegetationEditor", "DynamicWind", "Dataflow", "GeometryScripting",
                                                  "PCG", "PythonScriptPlugin", "EditorScriptingUtilities")}
except Exception as e:  # noqa: BLE001
    out["plugins_err"] = str(e)
for cv in ("r.Nanite.Foliage", "r.Nanite.ProjectEnabled", "r.RayTracing", "r.VolumetricFog.GridPixelSize",
           "r.VolumetricFog.GridSizeZ", "r.ScreenPercentage"):
    try:
        out[cv] = unreal.SystemLibrary.get_console_variable_float_value(cv)
    except Exception as e:  # noqa: BLE001
        out[cv] = "ERR " + str(e)[:80]
try:
    rs = unreal.get_default_object(unreal.RendererSettings)
    out["RendererSettings.enable_nanite_foliage"] = bool(rs.get_editor_property("enable_nanite_foliage"))
except Exception as e:  # noqa: BLE001
    out["RendererSettings_err"] = str(e)[:120]
w = unreal.EditorLoadingAndSavingUtils.load_map("/Game/Dojo/Maps/L_Dojo")
actors = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
out["actors"] = len(actors)
out["uds"] = sum(1 for a in actors if a.get_class().get_name() == "Ultra_Dynamic_Sky_C")
out["managed"] = sum(1 for a in actors if "DJ_Managed" in [str(t) for t in a.tags])
for cls in ("/Script/ProceduralVegetation.ProceduralVegetation", "/Script/DynamicWind.DynamicWindSubsystem"):
    try:
        out["class " + cls] = unreal.load_class(None, cls) is not None
    except Exception as e:  # noqa: BLE001
        out["class " + cls] = "ERR " + str(e)[:80]
unreal.log("DJ_LOADCHECK " + json.dumps(out))
