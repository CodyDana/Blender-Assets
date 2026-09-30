import unreal, json
out = {}
EAL = unreal.EditorAssetLibrary
out["cloud_assets"] = [str(p) for p in EAL.list_assets("/Engine/EngineSky/VolumetricClouds", True, False)][:40]
cdo = unreal.VolumetricCloudComponent.get_default_object()
try:
    m = cdo.get_editor_property("material"); out["cloud_default_material"] = m.get_path_name() if m else None
except Exception as e:
    out["cloud_default_material"] = str(e)
props = []
for k in ("layer_bottom_altitude", "layer_height", "tracing_start_max_distance", "tracing_max_distance",
          "view_sample_count_scale", "reflection_sample_count_scale", "shadow_view_sample_count_scale",
          "sky_light_cloud_shadow_on_atmosphere_strength", "shadow_tracing_distance", "ground_albedo"):
    try:
        v = cdo.get_editor_property(k); props.append([k, str(v)])
    except Exception as e:
        props.append([k, "ERR " + str(e)[:80]])
out["cloud_props"] = props
for path in ("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst", "/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud"):
    a = unreal.load_asset(path)
    if a:
        try:
            out[path] = {"scalars": [str(x) for x in unreal.MaterialEditingLibrary.get_scalar_parameter_names(a)],
                         "vectors": [str(x) for x in unreal.MaterialEditingLibrary.get_vector_parameter_names(a)],
                         "textures": [str(x) for x in unreal.MaterialEditingLibrary.get_texture_parameter_names(a)]}
            vals = {}
            for n in out[path]["scalars"]:
                try:
                    vals[n] = unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(a, n) if isinstance(a, unreal.MaterialInstance) else unreal.MaterialEditingLibrary.get_material_default_scalar_parameter_value(a, n)
                except Exception as e:
                    vals[n] = str(e)[:60]
            out[path]["scalar_values"] = vals
        except Exception as e:
            out[path] = str(e)
    else:
        out[path] = None
pp = unreal.PostProcessSettings()
out["pp"] = {}
for k in ("film_grain_intensity", "film_grain_intensity_shadows", "film_toe", "film_slope", "film_shoulder", "film_black_clip",
          "white_temp", "color_gamma", "color_contrast", "tone_curve_amount", "local_exposure_shadow_contrast_scale",
          "local_exposure_highlight_contrast_scale", "sky_light_cloud_shadow"):
    try:
        out["pp"][k] = str(pp.get_editor_property(k))
    except Exception as e:
        out["pp"][k] = "ERR " + str(e)[:80]
sac = unreal.SkyAtmosphereComponent.get_default_object()
out["sky"] = {}
for k in ("rayleigh_scattering_scale", "rayleigh_scattering", "mie_scattering_scale", "mie_anisotropy", "multi_scattering_factor",
          "sky_luminance_factor", "aerial_pespective_view_distance_scale", "height_fog_contribution", "ozone" , "other_absorption_scale", "other_absorption"):
    try:
        out["sky"][k] = str(sac.get_editor_property(k))
    except Exception as e:
        out["sky"][k] = "ERR " + str(e)[:80]
dl = unreal.DirectionalLightComponent.get_default_object()
out["dl"] = {}
for k in ("cast_cloud_shadows", "cloud_scattered_luminance_scale", "cast_shadows_on_clouds", "cast_shadows_on_atmosphere", "per_pixel_atmosphere_transmittance"):
    try:
        out["dl"][k] = str(dl.get_editor_property(k))
    except Exception as e:
        out["dl"][k] = "ERR " + str(e)[:80]
open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\unreal\round3\f1_work\probe_api.json", "w").write(json.dumps(out, indent=1))
unreal.log("PROBE_DONE")
