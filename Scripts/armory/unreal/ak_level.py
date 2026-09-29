"""ArmoryLab step 3 (pythonscript commandlet, -nullrhi): assemble /Game/Armory/Maps/L_Armory from layout.json and save it.

- Every layout.json instance becomes a StaticMeshActor labelled <piece>__<nnn> (the Blender Assembly object name), with
  location (x*100, -y*100, z*100) cm and yaw = -rot_z, in Outliner folders Architecture/... and Casework/...
- The layout.json light table in Unreal units (ak_common: K lux per Blender W/m2, the golden preset read from
  render_armory.py), in Lights/<role>: two directional lights (the sun, and the f2 window fill on lighting channel 1 that
  only the room kit receives), rect / spot / point lights in candela, shadows where the table says (minus the Unreal-only
  UE_SHADOW_OFF_ROLES), specular hidden where Blender hid the lamp from glossy rays, volumetric scattering only from the
  real sun.
- Environment: SkyAtmosphere, SkyLight (real-time capture), ExponentialHeightFog with volumetric fog (the Blender haze
  density, only the sun scatters), an unbound PostProcessVolume (manual exposure), and a PlayerStart in the courtyard
  on the path, facing the entrance (layout.json "player_start", exterior stage). Cameras: one CameraActor per layout.json camera (horizontal FOV from the lens, 36 mm sensor).
- GATE (Blender -> Unreal conversion): every mesh actor's world bounds must equal the Blender Assembly bounds converted
  (blender_bounds.json) within 1 cm; the south-wall door piece and an east-wall piece are named in the result.

Idempotent: the level is created once; a re-run loads it and destroys only the actors tagged AK_Managed, then respawns.
Night + genkan (2026-09-28): the lighting follows ak_common.PRESET (env AK_PRESET, default "night"; "golden" rebuilds
the golden-hour level). Night: ONE directional light, the moon (ak_common.directional_specs; SkyAtmosphere light,
priority 1, no scattering), the night practical powers and downlight 3500 K, the night sky (UE_SKY_BY_PRESET,
SKYLIGHT_INTENSITY), no height / volumetric fog, the night exposure bias; the scenery-card dimming is in the materials.
Result: WorkFiles/armory/build/unreal/level.json (in-process; ak_verify.py re-checks the saved level in a fresh process).
Env: AK_PRESET night|golden; AK_EXPOSURE_BIAS overrides the exposure bias (EV).
"""
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import ak_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "preset": C.PRESET, "notes": [], "setp_failed": []}
BIAS = float(os.environ.get("AK_EXPOSURE_BIAS", str(round(C.EXPOSURE_BIAS, 3))))
TOL_CM = 1.0
ATTEN_CM = 2000.0


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    """unreal.Rotator's positional order is (roll, pitch, yaw): always build it by name."""
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def V(t):
    return unreal.Vector(float(t[0]), float(t[1]), float(t[2]))


def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        REP["setp_failed"].append(f"{type(obj).__name__}.{k}: {str(exc)[:160]}")
        return False


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def open_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    exists = EAL.does_asset_exist(C.LEVEL)
    REP["level_existed"] = exists
    if exists:
        ok = les.load_level(C.LEVEL) if les else unreal.EditorLoadingAndSavingUtils.load_map(C.LEVEL)
    else:
        try:
            ok = les.new_level(C.LEVEL, False)
        except TypeError:
            ok = les.new_level(C.LEVEL)
    REP["open_ok"] = bool(ok)
    REP["world"] = world().get_path_name()
    removed = 0
    for a in EAS.get_all_level_actors():
        if unreal.Name(C.MANAGED_TAG) in list(a.tags):
            EAS.destroy_actor(a)
            removed += 1
    REP["managed_actors_removed"] = removed
    REP["unmanaged_actors_kept"] = sorted(a.get_actor_label() for a in EAS.get_all_level_actors())


def tag(actor, label, folder):
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.tags = [unreal.Name(C.MANAGED_TAG)]
    return actor


def channels(c0, c1, c2=False):
    lc = unreal.LightingChannels()
    lc.set_editor_property("channel0", bool(c0))
    lc.set_editor_property("channel1", bool(c1))
    lc.set_editor_property("channel2", bool(c2))
    return lc


def color_of(kelvin):
    r, g, b = C.kelvin_rgb(kelvin)
    return unreal.LinearColor(r, g, b, 1.0)


# ------------------------------------------------------------------------------------------------ meshes
def place_meshes(layout):
    placed = {}
    meshes = {}
    for n, inst in enumerate(layout["instances"]):
        piece = inst["piece"]
        if piece not in meshes:
            meshes[piece] = unreal.load_asset(f"{C.MESH_DEST}/{piece}")
        mesh = meshes[piece]
        if mesh is None:
            REP["notes"].append(f"missing mesh {piece}")
            continue
        # spawn_actor_from_object spawns nothing in a commandlet (no actor factory context): class + set_static_mesh
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(C.loc_cm(inst["loc"])), rot(yaw=C.yaw_deg(inst["rot_z"])))
        if a is None:
            raise RuntimeError(f"spawn failed for instance {n} {piece}")
        a.static_mesh_component.set_static_mesh(mesh)
        folder = C.folder_of(piece)
        if folder == "Architecture/Walls" and C.wall_side(inst):
            folder += "/" + C.wall_side(inst)
        tag(a, f"{piece}__{n:03d}", folder)
        a.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
        if inst.get("cast_shadow") is False:   # exterior stage: the scenery never shades the windows or the courtyard
            setp(a.static_mesh_component, "cast_shadow", False)
        if C.is_interior_piece(piece):   # f2 window fill sun: the room kit is on lighting channels 0 + 1
            setp(a.static_mesh_component, "lighting_channels", channels(True, True))
        placed[n] = a
    return placed


def place_items(layout):
    """Items on display (layout.json "items", written by build_armory_items.py): the pack's own assets under
    /Game/NinjaPack, at the Blender placement converted like every kit piece (x*100, -y*100, z*100; yaw = -rot_z).
    Flat items only rotate about Z; scale is always +1 (the HookedCross must never be mirrored)."""
    out = []
    for it in layout.get("items", []):
        mesh = unreal.load_asset(it["ue_asset"])
        if mesh is None:
            REP["notes"].append(f"missing item asset {it['ue_asset']}")
            out.append({"name": it["name"], "missing": True})
            continue
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(C.loc_cm(it["loc"])), rot(yaw=C.yaw_deg(it["rot_z"])))
        a.static_mesh_component.set_static_mesh(mesh)
        tag(a, f"ITEM_{it['name']}", f"Items/Case_{it['case']}")
        a.static_mesh_component.set_mobility(unreal.ComponentMobility.STATIC)
        setp(a.static_mesh_component, "lighting_channels", channels(True, True))
        a.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        out.append({"name": it["name"], "asset": it["ue_asset"], "loc_cm": [round(v, 3) for v in C.loc_cm(it["loc"])],
                    "yaw": round(C.yaw_deg(it["rot_z"]), 3)})
    return out


def bounds_gate(placed, layout):
    bb = json.loads(C.BLENDER_BOUNDS.read_text(encoding="utf-8"))["instances"]
    rows, worst = {}, 0.0
    for n, a in placed.items():
        o, e = a.get_actor_bounds(False)
        umin = [o.x - e.x, o.y - e.y, o.z - e.z]
        umax = [o.x + e.x, o.y + e.y, o.z + e.z]
        b = bb[str(n)]
        wmin, wmax = C.bbox_bl_to_ue(b["min"], b["max"])
        err = max(abs(p - q) for p, q in zip(umin + umax, wmin + wmax))
        worst = max(worst, err)
        rows[n] = {"label": a.get_actor_label(), "err_cm": round(err, 4), "ue_min": [round(v, 3) for v in umin],
                   "ue_max": [round(v, 3) for v in umax], "blender_converted_min": [round(v, 3) for v in wmin],
                   "blender_converted_max": [round(v, 3) for v in wmax]}
    door = next(n for n, i in enumerate(layout["instances"]) if i["piece"].startswith("SM_AK_Entrance_"))
    east = next(n for n, i in enumerate(layout["instances"])
                if i["piece"] == "SM_AK_WallLower_2" and float(i["rot_z"]) == 90.0)
    gate = {"tolerance_cm": TOL_CM, "n_checked": len(rows), "n_layout": len(layout["instances"]),
            "max_err_cm_all": round(worst, 4), "door_piece": rows.get(door), "east_wall_piece": rows.get(east),
            "failures": {k: v for k, v in rows.items() if v["err_cm"] > TOL_CM}}
    gate["passed"] = (len(rows) == len(layout["instances"]) and not gate["failures"]
                      and rows.get(door, {}).get("err_cm", 99) <= TOL_CM and rows.get(east, {}).get("err_cm", 99) <= TOL_CM)
    return gate


# ------------------------------------------------------------------------------------------------ lights
def local_light(L):
    t = L["type"]
    cls = {"rect": unreal.RectLight, "point": unreal.PointLight, "spot": unreal.SpotLight}[t]
    loc = C.loc_cm(L["loc"])
    if "aim" in L:
        d = C.dir_bl_to_ue([a - b for a, b in zip(L["aim"], L["loc"])])
        pitch, yaw = C.pitch_yaw_of(d)
    elif t in ("rect", "spot"):
        pitch, yaw = -90.0, C.yaw_deg(L.get("rot_z", 0.0))   # Blender area / spot lights point down (-Z)
    else:
        pitch, yaw = 0.0, 0.0
    a = EAS.spawn_actor_from_class(cls, V(loc), rot(pitch, yaw))
    comp = a.get_editor_property({"rect": "rect_light_component", "point": "point_light_component",
                                  "spot": "spot_light_component"}[t])
    cd = C.light_candela(L)
    setp(comp, "mobility", unreal.ComponentMobility.MOVABLE)
    setp(comp, "intensity_units", unreal.LightUnits.CANDELAS)
    setp(comp, "intensity", cd)
    comp.set_light_color(color_of(C.light_kelvin(L)), True)   # night: the downlights at 3500 K (PRESET_KELVIN)
    setp(comp, "attenuation_radius", ATTEN_CM)
    setp(comp, "cast_shadows", C.light_shadows(L))   # Unreal-only: the alcove spots give up theirs (shadow budget 12)
    setp(comp, "volumetric_scattering_intensity", 0.0)      # Blender: only the sun scatters in the haze
    if L["role"] in ("glow", "panel", "rack", "case") or L["role"] in C.UE_SPEC_OFF_ROLES:
        # render_armory.py visible_glossy False roles; Unreal-only: the lantern points (the opaque paper hides them in
        # Blender, here they cast no shadow, so their highlight would show on the glossy floor)
        setp(comp, "specular_scale", 0.0)
    if t == "rect":
        w, h = L["size"]
        if "aim" in L:    # Blender track -Z / up Y: size_x is horizontal (Unreal local Y), size_y is local Z
            setp(comp, "source_width", w * 100.0)
            setp(comp, "source_height", h * 100.0)
        else:             # pointing down with yaw -rot_z: Blender local X lies along Unreal local Z
            setp(comp, "source_height", w * 100.0)
            setp(comp, "source_width", h * 100.0)
        # f2: a narrowed area light (the hero table's). Blender's spread is a per-point cone (a honeycomb grid); Unreal
        # has only barn doors. Flared doors never block rays leaving past the near edge, so the doors stand straight
        # (angle 0) and are as long as puts the half-spread cone's edge ray from the rect centre at the door tip:
        # L = (short side / 2) / tan(spread / 2). Glow round (night): the under-glow rects get Unreal-only doors too
        # (ak_common.light_barn_door_cm)
        door = C.light_barn_door_cm(L)
        if door > 0.0:
            setp(comp, "barn_door_angle", 0.0)
        setp(comp, "barn_door_length", door)
    elif t == "spot":
        half = L["angle_deg"] / 2.0
        setp(comp, "outer_cone_angle", half)
        setp(comp, "inner_cone_angle", half * (1.0 - float(L.get("blend", C.SPOT_BLEND))))
        setp(comp, "source_radius", C.SPOT_SOFT_M * 100.0)
    elif t == "point":
        setp(comp, "source_radius", L.get("radius", 0.1) * 100.0)
    folder = "Lights/" + {"case": "CaseLights", "glow": "UnderGlow", "panel": "WallPanels", "rack": "CornerRacks",
                          "lantern": "Lanterns", "down": "Downlights", "wash": "PaintingWash",
                          "banner": "BannerSpots", "alcove": "RearAlcoves", "sill": "SillVases"}.get(L["role"], L["role"])
    tag(a, L["name"], folder)
    return {"name": L["name"], "type": t, "role": L["role"], "candela": round(cd, 2), "kelvin": C.light_kelvin(L),
            "barn_door_cm": round(C.light_barn_door_cm(L), 3) if t == "rect" else None,
            "shadows": C.light_shadows(L),
            "loc_cm": [round(v, 2) for v in loc], "pitch": round(pitch, 3), "yaw": round(yaw, 3)}


def sun(S, index):
    """A directional light from ak_common.directional_specs (the active preset).
    Golden (f2): two directional lights share the golden-hour heading. The real sun (first) drives the SkyAtmosphere and
    scatters in the volumetric fog. The window fill (layout.json "link": "interior") lights, and is shadowed by, the room
    only: lighting channel 1 alone (the room kit is on 0 + 1, the exterior on 0), no atmosphere, no fog scattering.
    Night (2026-09-28): ONE light, the moon (render_armory MOON): it drives the SkyAtmosphere, lights everything on
    channel 0, does not scatter (no volumetric fog, no shafts), forward shading priority 1."""
    d = C.dir_bl_to_ue(S["travel_dir"])
    pitch, yaw = C.pitch_yaw_of(d)
    interior = S["interior"]
    a = EAS.spawn_actor_from_class(unreal.DirectionalLight, V((400.0 + 100.0 * index, -600.0, 800.0)), rot(pitch, yaw))
    comp = a.get_editor_property("directional_light_component")
    lux = S["lux"]
    setp(comp, "mobility", unreal.ComponentMobility.MOVABLE)
    setp(comp, "intensity", lux)
    comp.set_light_color(color_of(S["kelvin"]), True)
    setp(comp, "light_source_angle", S["angle_deg"])
    setp(comp, "atmosphere_sun_light", S["atmosphere"])
    setp(comp, "cast_shadows", True)
    setp(comp, "volumetric_scattering_intensity", S["scatter"])
    setp(comp, "cast_volumetric_shadow", S["volumetric_shadow"])
    # golden has two directional lights: the real sun wins forward shading / translucency / volumetric fog (the editor
    # warned "Multiple directional lights are competing ... adjust their ForwardShadingPriority" with both at 0);
    # night's single moon also carries 1
    fsp_ok = setp(comp, "forward_shading_priority", S["priority"])
    if interior:
        setp(comp, "lighting_channels", channels(False, True))
    tag(a, S["name"], "Lights/Sun" if not C.NIGHT else "Lights/Moon")
    fwd = a.get_actor_forward_vector()
    try:
        fsp = int(comp.get_editor_property("forward_shading_priority"))
    except Exception as exc:  # noqa: BLE001
        fsp = f"readback failed: {str(exc)[:120]}"
    return {"name": S["name"], "lux": lux, "kelvin": S["kelvin"], "pitch": round(pitch, 3), "yaw": round(yaw, 3),
            "interior_only": interior, "atmosphere_sun_light": S["atmosphere"], "scatter": S["scatter"],
            "forward_shading_priority": fsp, "forward_shading_priority_set": fsp_ok,
            "forward_shading_priority_ok": fsp_ok and fsp == S["priority"],
            "forward_ue": [round(fwd.x, 4), round(fwd.y, 4), round(fwd.z, 4)],
            "travel_dir_blender": S["travel_dir"], "expected_forward_ue": [round(v, 4) for v in d]}


def pp_tweaks():
    """Unreal-only grade (ak_common.UE_PP, tuned against the Blender golden renders) as (override flag, value) pairs."""
    for k, v in C.UE_PP.items():
        yield "override_" + k, True
        if isinstance(v, (tuple, list)):
            v = unreal.Vector4(*[float(x) for x in v])
        yield k, v


def environment():
    env = {}
    a = EAS.spawn_actor_from_class(unreal.SkyAtmosphere, V((0, 0, 0)), rot())
    sac = a.get_component_by_class(unreal.SkyAtmosphereComponent)
    for k, v in C.UE_SKY.items():   # Unreal-only: the warm golden-hour sky of the Blender review world
        setp(sac, k, unreal.LinearColor(*[float(x) for x in v], 1.0) if isinstance(v, (tuple, list)) else v)
    env["sky_atmosphere"] = {k: list(v) if isinstance(v, (tuple, list)) else v for k, v in C.UE_SKY.items()}
    tag(a, "SkyAtmosphere", "Lights/Sky")
    a = EAS.spawn_actor_from_class(unreal.SkyLight, V((400.0, -600.0, 700.0)), rot())
    slc = a.get_editor_property("light_component")
    setp(slc, "mobility", unreal.ComponentMobility.MOVABLE)
    setp(slc, "source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    setp(slc, "real_time_capture", True)
    setp(slc, "intensity", C.SKYLIGHT_INTENSITY)   # golden 1.0; night lower (ak_common SKYLIGHT_INTENSITY)
    setp(slc, "volumetric_scattering_intensity", C.SKY_SCATTER)
    tag(a, "SkyLight", "Lights/Sky")
    env["skylight"] = {"real_time_capture": bool(slc.get_editor_property("real_time_capture")),
                       "intensity": C.SKYLIGHT_INTENSITY}
    a = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, V((400.0, -600.0, 0.0)), rot())
    fc = a.get_editor_property("component")
    # night: render_armory FOG["night"] is 0 (the moon does not scatter): density 0 and no volumetric fog (no shafts);
    # the actor stays so the golden preset is one flag away
    fog = {"fog_density": C.FOG_DENSITY_PER_M * 10.0, "fog_height_falloff": 0.001, "fog_max_opacity": 1.0,
           "start_distance": 0.0, "fog_cutoff_distance": 3000.0,
           "enable_volumetric_fog": C.FOG_DENSITY_PER_M > 0.0, "volumetric_fog_scattering_distribution": C.FOG_ANISO,
           "volumetric_fog_extinction_scale": 1.0, "volumetric_fog_distance": 3000.0,
           "volumetric_fog_start_distance": 0.0}
    for k, v in fog.items():
        setp(fc, k, v)
    r_, g_, b_ = (int(round(c * 255)) for c in C.FOG_ALBEDO)
    setp(fc, "volumetric_fog_albedo", unreal.Color(r=r_, g=g_, b=b_, a=255))
    black = unreal.LinearColor(0.0, 0.0, 0.0, 1.0)
    for k in ("fog_inscattering_luminance", "directional_inscattering_luminance",
              "sky_atmosphere_ambient_contribution_color_scale"):
        setp(fc, k, black)
    tag(a, "ExponentialHeightFog", "Lights/Sky")
    env["fog"] = fog
    a = EAS.spawn_actor_from_class(unreal.PostProcessVolume, V((400.0, -600.0, 250.0)), rot())
    setp(a, "unbound", True)
    pp = a.get_editor_property("settings")
    for k, v in (("override_auto_exposure_method", True), ("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                 ("override_auto_exposure_bias", True), ("auto_exposure_bias", BIAS),
                 ("override_auto_exposure_apply_physical_camera_exposure", True),
                 ("auto_exposure_apply_physical_camera_exposure", False),
                 # Lumen reflections on the case glass (translucent): without them the panes reflect the unoccluded sky
                 ("override_lumen_front_layer_translucency_reflections", True),
                 ("lumen_front_layer_translucency_reflections", True),
                 # the Blender review renders have no vignette (UE default 0.4 darkens the frame corners)
                 ("override_vignette_intensity", True), ("vignette_intensity", 0.0)) + tuple(pp_tweaks()):
        setp(pp, k, v)
    setp(a, "settings", pp)
    tag(a, "PostProcess_Armory", "Lights/PostProcess")
    env["post_process"] = {"unbound": bool(a.get_editor_property("unbound")), "exposure": "manual",
                           "auto_exposure_bias": float(a.get_editor_property("settings").get_editor_property("auto_exposure_bias"))}
    # exterior stage: the PlayerStart stands in the courtyard on the stepping-stone path, facing the entrance
    # (layout.json "player_start"; Blender rot_z 90 = +Y = into the hall)
    ps_loc, ps_yaw = C.player_start(C.load_layout())
    a = EAS.spawn_actor_from_class(unreal.PlayerStart, V(ps_loc), rot(yaw=ps_yaw))
    tag(a, "PlayerStart_Courtyard", "Gameplay")
    f = a.get_actor_forward_vector()
    env["player_start"] = {"loc_cm": list(ps_loc), "yaw": ps_yaw,
                           "forward_ue": [round(f.x, 4), round(f.y, 4), round(f.z, 4)]}
    return env


def cameras(layout):
    """One camera actor per layout.json camera. Unreal rebuild: CineCameraActors with the Blender lens on a 36 x 20.25 mm
    (16:9) filmback, so a shift-lens camera (f1: C1 is a LEVEL camera with shift_y) keeps its framing through the
    filmback's vertical sensor offset (= shift_y x 36 mm: Blender shifts in units of the sensor width; a negative Unreal
    offset moves the view down, CameraStackTypes.cpp). Depth of field off. A camera with its own review exposure
    (layout.json "exposure_ev", the garden) carries it as an exposure-bias override in its post-process settings."""
    out = {}
    for c in layout["cameras"]:
        loc = C.loc_cm(c["loc"])
        d = C.dir_bl_to_ue([a - b for a, b in zip(c["look_at"], c["loc"])])
        pitch, yaw = C.pitch_yaw_of(d)
        a = EAS.spawn_actor_from_class(unreal.CineCameraActor, V(loc), rot(pitch, yaw))
        cc = a.get_cine_camera_component()
        fb = cc.get_editor_property("filmback")
        fb.set_editor_property("sensor_width", 36.0)
        fb.set_editor_property("sensor_height", 36.0 * 9.0 / 16.0)
        fb.set_editor_property("sensor_vertical_offset", float(c.get("shift_y", 0.0)) * 36.0)
        setp(cc, "filmback", fb)
        setp(cc, "current_focal_length", float(c["lens_mm"]))
        fs = cc.get_editor_property("focus_settings")
        fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        setp(cc, "focus_settings", fs)
        setp(cc, "constrain_aspect_ratio", False)
        off = C.camera_exposure_offset(c)
        if off:
            pp = cc.get_editor_property("post_process_settings")
            pp.set_editor_property("override_auto_exposure_bias", True)
            pp.set_editor_property("auto_exposure_bias", BIAS + off)
            setp(cc, "post_process_settings", pp)
            setp(cc, "post_process_blend_weight", 1.0)
        tag(a, "CAM_" + c["name"], "Cameras")
        fov = C.hfov_deg(c["lens_mm"])
        got = cc.get_editor_property("filmback")
        out[c["name"]] = {"loc_cm": loc, "pitch": round(pitch, 3), "yaw": round(yaw, 3), "hfov_deg": round(fov, 3),
                          "hfov_actor": round(float(cc.get_editor_property("field_of_view")), 3),
                          "lens_mm": c["lens_mm"], "shift_y": c.get("shift_y", 0.0),
                          "sensor_vertical_offset_mm": round(float(got.get_editor_property("sensor_vertical_offset")), 3),
                          "exposure_offset_ev": off}
    return out


def save():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    ok = False
    try:
        ok = bool(les.save_current_level())
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"save_current_level: {exc}")
    if not ok:
        ok = bool(unreal.EditorLoadingAndSavingUtils.save_map(world(), C.LEVEL))
    return ok


def main():
    t0 = time.time()
    layout = C.load_layout()
    try:
        open_level()
        placed = place_meshes(layout)
        REP["mesh_actors"] = len(placed)
        REP["bounds_gate"] = bounds_gate(placed, layout)
        lights = [L for L in layout["lights"] if L["type"] != "sun"]
        suns = C.directional_specs(layout)   # golden: the two layout suns; night: the moon alone
        REP["suns"] = [sun(S, i) for i, S in enumerate(suns)]
        REP["local_lights"] = [local_light(L) for L in lights]
        REP["n_local_lights"] = len(REP["local_lights"])
        REP["n_shadowed_local"] = sum(1 for L in REP["local_lights"] if L["shadows"])
        REP["environment"] = environment()
        REP["cameras"] = cameras(layout)
        REP["items"] = place_items(layout)
        REP["exposure_bias"] = BIAS
        REP["folders"] = sorted({str(a.get_folder_path()) for a in EAS.get_all_level_actors()})
        REP["saved"] = save()
        sun_ok = len(REP["suns"]) == len(suns) and all(
            all(abs(p - q) < 1e-3 for p, q in zip(sf["forward_ue"], sf["expected_forward_ue"])) for sf in REP["suns"])
        REP["sun_direction_ok"] = sun_ok
        # hero round: the real sun must win forward shading (1) over the window fill (0), read back from the component;
        # night: the single moon reads 1, and there is exactly one directional light in the level
        REP["n_directional"] = sum(1 for a in EAS.get_all_level_actors() if isinstance(a, unreal.DirectionalLight))
        REP["n_directional_want"] = len(suns)
        REP["forward_shading_priority_ok"] = all(sf.get("forward_shading_priority_ok") for sf in REP["suns"])
        REP["passed"] = (REP["bounds_gate"]["passed"] and REP["saved"] and sun_ok
                         and REP["n_shadowed_local"] <= C.MAX_SHADOWED_LOCAL and not REP["setp_failed"]
                         and REP["forward_shading_priority_ok"] and REP["n_directional"] == REP["n_directional_want"])
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        REP["passed"] = False
    REP["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "level.json", REP)
    g = REP.get("bounds_gate", {})
    unreal.log(f"AK_STEP_DONE level passed={REP['passed']} meshes={REP.get('mesh_actors')} "
               f"gate_max_err_cm={g.get('max_err_cm_all')} lights={REP.get('n_local_lights')} saved={REP.get('saved')}")


main()
