# ------------------------------------------------------------------ 7 environment (r8, UDS): one sun / sky light / fog, no dome, no fills, one exposure owner
SKY_WORDS = ("skysphere", "sky_sphere", "skydome", "sky_dome", "sunsetsky", "djs_sky", "sunsetclouds", "skyclouds")
EXPO_KEYS = ("auto_exposure_method", "auto_exposure_bias", "auto_exposure_min_brightness", "auto_exposure_max_brightness",
             "auto_exposure_apply_physical_camera_exposure", "histogram_log_min", "histogram_log_max",
             "auto_exposure_bias_curve", "auto_exposure_meter_mask", "auto_exposure_low_percent", "auto_exposure_high_percent",
             "auto_exposure_speed_up", "auto_exposure_speed_down", "camera_iso", "camera_shutter_speed", "depth_of_field_fstop")


def pp_exposure(s):
    out = {}
    for k in EXPO_KEYS:
        try:
            if s.get_editor_property("override_" + k):
                out[k] = str(s.get_editor_property(k))[:80]
        except Exception:  # noqa: BLE001
            pass
    return out


def comp_row(a, c):
    r = {"actor": a.get_actor_label(), "actor_class": a.get_class().get_name(), "comp": c.get_name(),
         "class": c.get_class().get_name()}
    for k in ("intensity", "visible", "affects_world", "cast_shadows"):
        try:
            v = c.get_editor_property(k)
            r[k] = round(float(v), 4) if isinstance(v, float) else bool(v) if isinstance(v, bool) else str(v)
        except Exception:  # noqa: BLE001
            pass
    try:
        r["hidden_in_game"] = bool(c.get_editor_property("hidden_in_game"))
    except Exception:  # noqa: BLE001
        pass
    return r


def active(r):
    return (r.get("visible", True) and r.get("affects_world", True) is not False and r.get("intensity", 1.0) > 0
            and not r.get("hidden_in_game", False))


def check_env(actors):
    kinds = {"directional": unreal.DirectionalLightComponent, "skylight": unreal.SkyLightComponent,
             "fog": unreal.ExponentialHeightFogComponent, "atmosphere": unreal.SkyAtmosphereComponent,
             "cloud": unreal.VolumetricCloudComponent, "point": unreal.PointLightComponent,
             "spot": unreal.SpotLightComponent, "rect": unreal.RectLightComponent,
             "postprocess_comp": unreal.PostProcessComponent}
    comps = {k: [] for k in kinds}
    for a in actors:
        for k, cls in kinds.items():
            for c in a.get_components_by_class(cls):
                if k == "point" and isinstance(c, unreal.SpotLightComponent):
                    continue   # spot derives from point
                comps[k].append(comp_row(a, c))
    classes = Counter(a.get_class().get_name() for a in actors)
    uds = [a for a in actors if a.get_class().get_name() == "Ultra_Dynamic_Sky_C"]
    udw = [a for a in actors if "Ultra_Dynamic_Weather" in a.get_class().get_name()]
    engine_env_actors = {c: classes.get(c, 0) for c in ("DirectionalLight", "SkyLight", "ExponentialHeightFog",
                                                        "SkyAtmosphere", "VolumetricCloud")}
    dome = []
    for a in actors:
        if a in uds:
            continue
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            sm = c.get_editor_property("static_mesh")
            names = [sm.get_path_name() if sm else ""] + [m.get_path_name() for m in c.get_materials() if m]
            if any(w in n.lower() for n in names for w in SKY_WORDS):
                dome.append({"actor": a.get_actor_label(), "names": names[:4], "hidden": bool(a.get_editor_property("hidden"))})
    fills = [a.get_actor_label() for a in actors
             if "fill" in a.get_actor_label().lower() and "light" in a.get_actor_label().lower()]
    ppv = []
    for a in actors:
        if isinstance(a, unreal.PostProcessVolume):
            s = a.get_editor_property("settings")
            ppv.append({"label": a.get_actor_label(), "unbound": bool(a.get_editor_property("unbound")),
                        "enabled": bool(a.get_editor_property("enabled")), "priority": float(a.get_editor_property("priority")),
                        "blend_weight": float(a.get_editor_property("blend_weight")), "exposure": pp_exposure(s)})
    ppc = []
    for a in actors:
        if isinstance(a, unreal.PostProcessVolume):
            continue
        for c in a.get_components_by_class(unreal.PostProcessComponent):
            s = c.get_editor_property("settings")
            ppc.append({"actor": a.get_actor_label(), "comp": c.get_name(), "enabled": bool(c.get_editor_property("enabled")),
                        "unbound": bool(c.get_editor_property("unbound")), "priority": float(c.get_editor_property("priority")),
                        "blend_weight": float(c.get_editor_property("blend_weight")), "exposure": pp_exposure(s)})
    cams = []
    for a in actors:
        for c in a.get_components_by_class(unreal.CameraComponent):
            try:
                w = float(c.get_editor_property("post_process_blend_weight"))
                ex = pp_exposure(c.get_editor_property("post_process_settings"))
            except Exception as e:  # noqa: BLE001
                w, ex = None, {"err": str(e)[:60]}
            if ex and (w or 0) > 0:
                cams.append({"actor": a.get_actor_label(), "weight": w, "exposure": ex})
    owners = ([("PPV " + p["label"]) for p in ppv if p["enabled"] and p["blend_weight"] > 0 and p["exposure"]]
              + [("PPC " + p["actor"] + "/" + p["comp"]) for p in ppc if p["enabled"] and p["blend_weight"] > 0 and p["exposure"]]
              + [("CAM " + c["actor"]) for c in cams])
    udsv = {}
    for k in ("Apply Exposure Settings", "Animate Time of Day", "Time of Day", "Dusk Time", "Dawn Time", "Project Mode",
              "Sky Mode", "Volumetric Cloud Rendering Mode", "Color Mode", "Sky Light Mode", "Simulate Real Sun",
              "Use Volumetric Fog", "Half Rate Tick", "Sun Yaw", "Sun Source Angle Scale", "Cloud Coverage", "Cloud Speed",
              "Randomize Cloud Formation on Run", "Clouds Move with Time of Day", "Exposure Metering Mode"):
        for u in uds[:1]:
            try:
                udsv[k] = str(u.get_editor_property(k))[:100]
            except Exception as e:  # noqa: BLE001
                udsv[k] = "ERR " + str(e)[:60]
    act = {k: [r for r in v if active(r)] for k, v in comps.items()}
    sun = None
    for a in uds[:1]:
        for c in a.get_components_by_class(unreal.DirectionalLightComponent):
            f = c.get_forward_vector()
            if c.get_name() == "Sun":
                sun = {"elev_deg": round(math.degrees(math.asin(max(-1.0, min(1.0, -f.z)))), 3),
                       "az_from_x_blender_deg": round(math.degrees(math.atan2(f.y, -f.x)) % 360, 3),
                       "source_angle": round(float(c.get_editor_property("light_source_angle")), 4),
                       "contact_shadow_length": round(float(c.get_editor_property("contact_shadow_length")), 4)}
    loc = uds[0].get_actor_location() if uds else None
    res = {"actor_classes_env": engine_env_actors, "uds_actors": [a.get_actor_label() for a in uds],
           "uds_location_cm": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)] if loc else None,
           "weather_actors": [a.get_actor_label() for a in udw], "components": comps,
           "active_counts": {k: len(v) for k, v in act.items()}, "painted_dome": dome, "fill_lights": fills,
           "ppv": ppv, "postprocess_components": ppc, "camera_exposure_overrides": cams, "exposure_owners": owners,
           "uds_vars": udsv, "uds_sun": sun}
    lay_sun = L.get("sun", {})
    if sun:
        res["sun_vs_layout_deg"] = [round(sun["elev_deg"] - lay_sun.get("elev_deg", 0), 3),
                                    round(((sun["az_from_x_blender_deg"] - lay_sun.get("azimuth_deg_from_x", 0) + 180) % 360) - 180, 3)]
    why = []
    if len(uds) != 1:
        why.append(f"{len(uds)} UDS actors")
    if any(engine_env_actors.values()):
        why.append(f"engine env actors left {engine_env_actors}")
    if len(act["directional"]) != 1:
        why.append(f"{len(act['directional'])} active directional lights")
    if len(act["skylight"]) != 1:
        why.append(f"{len(act['skylight'])} active sky lights")
    if len(act["fog"]) != 1:
        why.append(f"{len(act['fog'])} active height fogs")
    if len(comps["atmosphere"]) > 1 or len(comps["cloud"]) > 1:
        why.append("more than one atmosphere / cloud component")
    if dome:
        why.append("painted dome present")
    if fills:
        why.append("fill lights present")
    if len(owners) != 1:
        why.append(f"exposure owners {owners}")
    if udsv.get("Animate Time of Day") != "False":
        why.append("time of day animates")
    if udsv.get("Apply Exposure Settings") != "False" and any(o.startswith("PPV") for o in owners):
        why.append("UDS exposure AND a PPV exposure")
    res["fail"] = why
    res["passed"] = not why
    return res
