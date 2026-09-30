"""Round 8 probe 1 (commandlet, -nullrhi, READ-ONLY: nothing is saved): load L_Dojo, spawn Ultra_Dynamic_Sky, read which
property names Python accepts, list its components, and read the sun component's direction for a sweep of Time of Day
and Sun Yaw. Result: probe/uds_probe1.json"""
import json
import math
import traceback
from pathlib import Path

import unreal

OUT = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal\round8\s1_work\probe\uds_probe1.json")
REP = {"engine": unreal.SystemLibrary.get_engine_version()}
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
NAMES = ["Time of Day", "Animate Time of Day", "Dawn Time", "Dusk Time", "Sun Yaw", "Simulate Real Sun",
         "Manually Position Sun Target", "Apply Exposure Settings", "Exposure Metering Mode", "Sky Mode", "Project Mode",
         "Volumetric Cloud Rendering Mode", "Cloud Coverage", "Cloud Speed", "Color Mode", "Sky Light Mode",
         "Sun Light Intensity", "Sun Source Angle Scale", "Half Rate Tick", "Randomize Cloud Formation on Run",
         "Clouds Move with Time of Day", "Fog", "Dust Amount", "Base Fog Density", "Lighting Brightness (Dawn/Dusk)",
         "Lighting Brightness (Day)", "Volumetric Fog", "Use Sky Mode Scalability Map", "Sun Lens Flare",
         "Exposure Bias Dawn/Dusk", "Exposure Brightness Range", "Contrast", "Saturation", "Cloud Phase",
         "Bottom Altitude", "Volumetric Clouds Scale", "Sky Light Intensity", "Sun Contact Shadow Length"]


def try_get(a, n):
    for cand in (n, n.lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")):
        try:
            v = a.get_editor_property(cand)
            return cand, str(v)[:120], type(v).__name__
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[:120]
    return None, last, None


def sun_dir(a):
    out = []
    for c in a.get_components_by_class(unreal.DirectionalLightComponent):
        f = c.get_forward_vector()
        elev = math.degrees(math.asin(max(-1.0, min(1.0, -f.z))))
        az = math.degrees(math.atan2(-f.y, -f.x))   # direction TO the light, UE frame
        out.append({"name": c.get_name(), "fwd": [round(f.x, 4), round(f.y, 4), round(f.z, 4)],
                    "elev_deg": round(elev, 2), "az_to_sun_ue_deg": round(az, 2),
                    "az_to_sun_blender_deg": round(-az, 2),
                    "intensity": round(float(c.get_editor_property("intensity")), 4),
                    "visible": bool(c.get_editor_property("visible")),
                    "source_angle": round(float(c.get_editor_property("light_source_angle")), 4)})
    return out


def main():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["open"] = bool(les.load_level("/Game/Dojo/Maps/L_Dojo"))
    cls = unreal.EditorAssetLibrary.load_blueprint_class("/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky")
    REP["class"] = cls.get_path_name() if cls else None
    a = EAS.spawn_actor_from_class(cls, unreal.Vector(2200.0, -1800.0, 0.0), unreal.Rotator())
    REP["props"] = {n: try_get(a, n) for n in NAMES}
    REP["components"] = sorted(f"{c.get_class().get_name()}:{c.get_name()}" for c in a.get_components_by_class(unreal.ActorComponent))
    REP["sun_default"] = sun_dir(a)
    sweep = []
    tod_name = REP["props"]["Time of Day"][0]
    yaw_name = REP["props"]["Sun Yaw"][0]
    for yaw in (0.0, 90.0):
        for tod in (1200.0, 1700.0, 1800.0, 1830.0, 1900.0):
            try:
                a.set_editor_property(tod_name, tod)
                a.set_editor_property(yaw_name, yaw)
                try:
                    a.rerun_construction_scripts()
                except Exception as exc:  # noqa: BLE001
                    REP["rerun_err"] = str(exc)[:200]
                sweep.append({"tod": tod, "yaw": yaw, "sun": sun_dir(a)})
            except Exception as exc:  # noqa: BLE001
                sweep.append({"tod": tod, "yaw": yaw, "error": str(exc)[:200]})
    REP["sweep"] = sweep
    comp_vals = {}
    for c in a.get_components_by_class(unreal.ActorComponent):
        cn = c.get_class().get_name()
        if cn == "SkyLightComponent":
            comp_vals[c.get_name()] = {k: str(c.get_editor_property(k))[:80] for k in
                                       ("intensity", "real_time_capture", "source_type", "mobility")}
        elif cn == "ExponentialHeightFogComponent":
            comp_vals[c.get_name()] = {k: str(c.get_editor_property(k))[:80] for k in
                                       ("fog_density", "fog_height_falloff", "enable_volumetric_fog", "start_distance")}
        elif cn == "PostProcessComponent":
            s = c.get_editor_property("settings")
            comp_vals[c.get_name()] = {"unbound": str(c.get_editor_property("unbound")),
                                       "priority": str(c.get_editor_property("priority")),
                                       "override_ae_method": str(s.get_editor_property("override_auto_exposure_method")),
                                       "ae_method": str(s.get_editor_property("auto_exposure_method")),
                                       "override_bias": str(s.get_editor_property("override_auto_exposure_bias")),
                                       "bias": str(s.get_editor_property("auto_exposure_bias"))}
        elif cn == "VolumetricCloudComponent":
            comp_vals[c.get_name()] = {k: str(c.get_editor_property(k))[:80] for k in
                                       ("layer_bottom_altitude", "layer_height", "material", "visible")}
        elif cn == "SkyAtmosphereComponent":
            comp_vals[c.get_name()] = {k: str(c.get_editor_property(k))[:80] for k in
                                       ("sky_luminance_factor", "height_fog_contribution", "transform_mode")}
    REP["component_values"] = comp_vals


try:
    main()
except Exception:  # noqa: BLE001
    REP["error"] = traceback.format_exc()[-3000:]
OUT.write_text(json.dumps(REP, indent=1), encoding="utf-8")
unreal.log("DJ_PROBE_DONE uds_probe1")
