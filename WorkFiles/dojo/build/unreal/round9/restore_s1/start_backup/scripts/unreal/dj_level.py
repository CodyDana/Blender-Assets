"""DojoLab step (pythonscript commandlet, -nullrhi): assemble /Game/Dojo/Maps/L_Dojo from layout.json and save it.

- One StaticMeshActor per layout.json instance, labelled <piece>__<nnn>, location (x*100, -y*100, z*100) cm, yaw -rot_z,
  in Outliner folders Dojo/<folder>. Collision per the instance's class (spec 5.3, layout.json collision_classes): Pawn /
  Camera / Visibility block or ignore; the 1v1 boundary is Pawn-only and hidden in game.
- GASP traversal marking (GASP_TRAVERSAL.md): one LevelBlock_Traversable (GASP's own Blueprint, copied from the sample,
  not edited) per layout.json traversal marker, placed and scaled so its 100 cm cube fills the marker box: its four ledge
  splines then lie on the box's top edges, normals outward. Invisible in game; collision = the Traversable channel only
  (query only), so it never blocks a pawn, the camera or the Visibility room checks - our meshes do that.
- PlayerStart_P1 / _P2 at the spec spawns (tags P1 / P2), facing each other.
- Sunset: a low directional sun from the west-north-west (layout.json "sun", atmosphere sun), SkyAtmosphere, SkyLight
  (real-time capture), ExponentialHeightFog, an unbound PostProcessVolume; one CineCameraActor per layout.json camera.
- World settings: game mode GM_Dojo, KillZ -1000 cm (spec 5.4 safety net: 10 m below the courtyard).
- GATE: every mesh actor's world bounds equal the Blender Assembly bounds converted, within 1 cm.
Idempotent: a re-run destroys only the actors tagged DJ_Managed. Result: WorkFiles/dojo/build/unreal/level.json
"""
import json
import math
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import unreal  # noqa: E402
import dj_common as C  # noqa: E402

EAL = unreal.EditorAssetLibrary
EAS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REP = {"engine": unreal.SystemLibrary.get_engine_version(), "notes": [], "setp_failed": []}
TOL_CM = 1.0
CH = unreal.CollisionChannel
RESP = {"block": unreal.CollisionResponseType.ECR_BLOCK, "ignore": unreal.CollisionResponseType.ECR_IGNORE}


def rot(pitch=0.0, yaw=0.0, roll=0.0):
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


def tag(actor, label, folder, *extra):
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    actor.tags = [unreal.Name(C.MANAGED_TAG)] + [unreal.Name(t) for t in extra]
    return actor


def open_level():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    REP["level_existed"] = EAL.does_asset_exist(C.LEVEL)
    if REP["level_existed"]:
        ok = les.load_level(C.LEVEL)
    else:
        ok = les.new_level(C.LEVEL, False)
    REP["open_ok"] = bool(ok)
    removed = 0
    for a in EAS.get_all_level_actors():
        if unreal.Name(C.MANAGED_TAG) in list(a.tags):
            EAS.destroy_actor(a)
            removed += 1
    REP["managed_actors_removed"] = removed
    REP["unmanaged_actors_kept"] = sorted(a.get_actor_label() for a in EAS.get_all_level_actors())


def apply_collision(comp, cls, classes):
    c = classes[cls]
    comp.set_collision_profile_name("BlockAll")
    comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
    if cls == "boundary":
        comp.set_collision_response_to_all_channels(RESP["ignore"])
    comp.set_collision_response_to_channel(CH.ECC_PAWN, RESP[c["pawn"]])
    comp.set_collision_response_to_channel(CH.ECC_CAMERA, RESP[c["camera"]])
    comp.set_collision_response_to_channel(CH.ECC_VISIBILITY, RESP[c["visibility"]])


def place_meshes(layout):
    placed, meshes = {}, {}
    for n, inst in enumerate(layout["instances"]):
        piece = inst["piece"]
        if piece not in meshes:
            meshes[piece] = unreal.load_asset(f"{C.MESH_DEST}/{piece}")
        if meshes[piece] is None:
            REP["notes"].append(f"missing mesh {piece}")
            continue
        a = EAS.spawn_actor_from_class(unreal.StaticMeshActor, V(C.loc_cm(inst["loc"])), rot(yaw=C.yaw_deg(inst["rot_z"])))
        smc = a.static_mesh_component
        smc.set_static_mesh(meshes[piece])
        smc.set_mobility(unreal.ComponentMobility.STATIC)
        apply_collision(smc, inst["collision_class"], layout["collision_classes"])
        if layout["collision_classes"][inst["collision_class"]].get("hidden_in_game"):
            a.set_actor_hidden_in_game(True)
            setp(smc, "cast_shadow", False)
        tag(a, f"{piece}__{n:03d}", C.folder_of(inst), "DGB_" + inst["collision_class"])
        placed[n] = a
    return placed


def bounds_gate(placed, layout):
    bb = json.loads(C.BLENDER_BOUNDS.read_text(encoding="utf-8"))["instances"]
    rows, worst = {}, 0.0
    for n, a in placed.items():
        o, e = a.get_actor_bounds(False)
        u = [o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z]
        b = bb[str(n)]
        wmin, wmax = C.bbox_bl_to_ue(b["min"], b["max"])
        err = max(abs(p - q) for p, q in zip(u, wmin + wmax))
        worst = max(worst, err)
        rows[n] = {"label": a.get_actor_label(), "err_cm": round(err, 4)}
    gate = {"tolerance_cm": TOL_CM, "n_checked": len(rows), "n_layout": len(layout["instances"]),
            "max_err_cm_all": round(worst, 4), "failures": {k: v for k, v in rows.items() if v["err_cm"] > TOL_CM}}
    gate["passed"] = len(rows) == len(layout["instances"]) and not gate["failures"]
    return gate


def expected_ledges(x0, x1, y0, y1, z1):
    """GASP's four ledge splines on a box (read from the Blueprint: Ledge_1 on local y 0 facing -Y, Ledge_2 on y 100
    facing +Y, Ledge_3 on x 0 facing -X, Ledge_4 on x 100 facing +X), in Unreal cm: start, end, outward normal."""
    X0, X1, Y0, Y1, Z = x0 * 100.0, x1 * 100.0, -y1 * 100.0, -y0 * 100.0, z1 * 100.0
    return {"Ledge_1": [[X0, Y0, Z], [X1, Y0, Z], [0.0, -1.0, 0.0]], "Ledge_2": [[X0, Y1, Z], [X1, Y1, Z], [0.0, 1.0, 0.0]],
            "Ledge_3": [[X0, Y0, Z], [X0, Y1, Z], [-1.0, 0.0, 0.0]], "Ledge_4": [[X1, Y0, Z], [X1, Y1, Z], [1.0, 0.0, 0.0]]}


def place_markers(layout):
    cls = EAL.load_blueprint_class(C.TRAVERSABLE_BLOCK)
    out = []
    for m in layout["traversal_markers"]:
        x0, x1, y0, y1, z0, z1 = m["box"]
        # the Blueprint's cube spans local 0..100 cm on every axis from the actor origin: origin = (x0, -y1, z0) in UE
        a = EAS.spawn_actor_from_class(cls, V((x0 * 100.0, -y1 * 100.0, z0 * 100.0)), rot())
        a.set_actor_scale3d(V((x1 - x0, y1 - y0, z1 - z0)))
        for comp in a.get_components_by_class(unreal.PrimitiveComponent):
            if isinstance(comp, unreal.StaticMeshComponent):
                comp.set_collision_enabled(unreal.CollisionEnabled.QUERY_ONLY)
                comp.set_collision_response_to_all_channels(RESP["ignore"])
                comp.set_collision_response_to_channel(CH.ECC_TRAVERSABLE, RESP["block"])
                setp(comp, "cast_shadow", False)
        a.set_actor_hidden_in_game(True)
        tag(a, "TRV_" + m["name"], "Dojo/Traversal", "DJ_Traversal", "route_" + m["route"])
        splines, ledge_err = {}, 0.0
        want = expected_ledges(x0, x1, y0, y1, z1)
        for sp in a.get_components_by_class(unreal.SplineComponent):
            p0 = sp.get_location_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
            p1 = sp.get_location_at_spline_point(1, unreal.SplineCoordinateSpace.WORLD)
            up = sp.get_up_vector_at_spline_point(0, unreal.SplineCoordinateSpace.WORLD)
            got = [[round(p0.x, 1), round(p0.y, 1), round(p0.z, 1)], [round(p1.x, 1), round(p1.y, 1), round(p1.z, 1)],
                   [round(up.x, 3), round(up.y, 3), round(up.z, 3)]]
            splines[sp.get_name()] = got
            w = want.get(sp.get_name())
            if w is None:
                ledge_err = 1e9
                continue
            ledge_err = max(ledge_err, max(abs(g - q) for g, q in zip(got[0] + got[1], w[0] + w[1])),
                            100.0 * max(abs(g - q) for g, q in zip(got[2], w[2])))
        mesh_err = 0.0
        want_min, want_max = C.bbox_bl_to_ue([x0, y0, z0], [x1, y1, z1])
        for comp in a.get_components_by_class(unreal.StaticMeshComponent):
            o, e, _r = unreal.SystemLibrary.get_component_bounds(comp)
            got = [o.x - e.x, o.y - e.y, o.z - e.z, o.x + e.x, o.y + e.y, o.z + e.z]
            mesh_err = max(mesh_err, max(abs(p - q) for p, q in zip(got, want_min + want_max)))
        out.append({"name": m["name"], "route": m["route"], "ledges": splines, "n_ledges": len(splines),
                    "ledge_err_cm": round(ledge_err, 3), "bounds_err_cm": round(mesh_err, 3),
                    "top_z_cm": round(z1 * 100.0, 1)})
    return out


def environment(layout):
    env = {}
    s = layout["sun"]
    d = C.dir_bl_to_ue(s["travel_dir"])
    pitch, yaw = C.pitch_yaw_of(d)
    a = EAS.spawn_actor_from_class(unreal.DirectionalLight, V((2200.0, -1800.0, 1500.0)), rot(pitch, yaw))
    comp = a.get_editor_property("directional_light_component")
    setp(comp, "mobility", unreal.ComponentMobility.MOVABLE)
    setp(comp, "intensity", float(s["lux"]))
    r, g, b = C.kelvin_rgb(s["kelvin"])
    comp.set_light_color(unreal.LinearColor(r, g, b, 1.0), True)
    setp(comp, "atmosphere_sun_light", True)
    setp(comp, "light_source_angle", 0.53)
    setp(comp, "cast_shadows", True)
    tag(a, "Sun_Sunset", "Dojo/Lighting")
    f = a.get_actor_forward_vector()
    env["sun"] = {"pitch": round(pitch, 3), "yaw": round(yaw, 3), "lux": s["lux"], "kelvin": s["kelvin"],
                  "forward_ue": [round(f.x, 4), round(f.y, 4), round(f.z, 4)], "expected": [round(v, 4) for v in d]}
    a = EAS.spawn_actor_from_class(unreal.SkyAtmosphere, V((0, 0, 0)), rot())
    tag(a, "SkyAtmosphere", "Dojo/Lighting")
    a = EAS.spawn_actor_from_class(unreal.SkyLight, V((2200.0, -1800.0, 1200.0)), rot())
    slc = a.get_editor_property("light_component")
    setp(slc, "mobility", unreal.ComponentMobility.MOVABLE)
    setp(slc, "source_type", unreal.SkyLightSourceType.SLS_CAPTURED_SCENE)
    setp(slc, "real_time_capture", True)
    tag(a, "SkyLight", "Dojo/Lighting")
    a = EAS.spawn_actor_from_class(unreal.ExponentialHeightFog, V((2200.0, -1800.0, 0.0)), rot())
    fc = a.get_editor_property("component")
    for k, v in (("fog_density", 0.012), ("fog_height_falloff", 0.15), ("enable_volumetric_fog", True),
                 ("volumetric_fog_scattering_distribution", 0.6), ("volumetric_fog_extinction_scale", 0.6)):
        setp(fc, k, v)
    tag(a, "ExponentialHeightFog", "Dojo/Lighting")
    a = EAS.spawn_actor_from_class(unreal.PostProcessVolume, V((2200.0, -1800.0, 300.0)), rot())
    setp(a, "unbound", True)
    pp = a.get_editor_property("settings")
    for k, v in (("override_auto_exposure_bias", True), ("auto_exposure_bias", 1.0),
                 ("override_vignette_intensity", True), ("vignette_intensity", 0.2)):
        setp(pp, k, v)
    setp(a, "settings", pp)
    tag(a, "PostProcess_Dojo", "Dojo/Lighting")
    env["player_starts"] = []
    for ps in layout["player_starts"]:
        x, y, _z = C.loc_cm(ps["loc"])
        a = EAS.spawn_actor_from_class(unreal.PlayerStart, V((x, y, 95.0)), rot(yaw=C.yaw_deg(ps["rot_z"])))
        setp(a, "player_start_tag", unreal.Name(ps["tag"]))
        tag(a, ps["name"], "Dojo/Gameplay", ps["tag"])
        f = a.get_actor_forward_vector()
        env["player_starts"].append({"name": ps["name"], "loc_cm": [x, y, 95.0], "yaw": C.yaw_deg(ps["rot_z"]),
                                     "forward": [round(f.x, 3), round(f.y, 3), round(f.z, 3)]})
    return env


def cameras(layout):
    out = {}
    for c in layout["cameras"]:
        loc = C.loc_cm(c["loc"])
        d = C.dir_bl_to_ue([a - b for a, b in zip(c["look_at"], c["loc"])])
        pitch, yaw = C.pitch_yaw_of(d)
        a = EAS.spawn_actor_from_class(unreal.CineCameraActor, V(loc), rot(pitch, yaw))
        cc = a.get_cine_camera_component()
        w, h = c["out_wh"]
        fb = cc.get_editor_property("filmback")
        fb.set_editor_property("sensor_width", 36.0)
        fb.set_editor_property("sensor_height", 36.0 * h / w)
        setp(cc, "filmback", fb)
        setp(cc, "current_focal_length", 18.0 / math.tan(math.radians(c["hfov_deg"]) / 2.0))
        fs = cc.get_editor_property("focus_settings")
        fs.set_editor_property("focus_method", unreal.CameraFocusMethod.DISABLE)
        setp(cc, "focus_settings", fs)
        tag(a, c["name"], "Dojo/Cameras")
        out[c["name"]] = {"loc_cm": loc, "pitch": round(pitch, 3), "yaw": round(yaw, 3), "hfov": c["hfov_deg"]}
    return out


def world_settings():
    ws = world().get_world_settings()
    gm = EAL.load_blueprint_class(C.DOJO_GAME_MODE)
    ok = setp(ws, "default_game_mode", gm) and setp(ws, "kill_z", -1000.0)
    return {"game_mode": gm.get_path_name() if gm else None, "kill_z": -1000.0, "ok": ok}


def save():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    try:
        if les.save_current_level():
            return True
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"save_current_level: {exc}")
    return bool(unreal.EditorLoadingAndSavingUtils.save_map(world(), C.LEVEL))


def main():
    t0 = time.time()
    layout = C.load_layout()
    try:
        open_level()
        placed = place_meshes(layout)
        REP["mesh_actors"] = len(placed)
        REP["bounds_gate"] = bounds_gate(placed, layout)
        REP["markers"] = place_markers(layout)
        REP["marker_max_bounds_err_cm"] = max(m["bounds_err_cm"] for m in REP["markers"])
        REP["marker_max_ledge_err_cm"] = max(m["ledge_err_cm"] for m in REP["markers"])
        REP["environment"] = environment(layout)
        REP["cameras"] = cameras(layout)
        REP["world_settings"] = world_settings()
        REP["folders"] = sorted({str(a.get_folder_path()) for a in EAS.get_all_level_actors()})
        REP["n_actors"] = len(EAS.get_all_level_actors())
        REP["saved"] = save()
        sun = REP["environment"]["sun"]
        REP["sun_direction_ok"] = max(abs(p - q) for p, q in zip(sun["forward_ue"], sun["expected"])) < 1e-3
        REP["passed"] = (REP["bounds_gate"]["passed"] and REP["saved"] and REP["sun_direction_ok"]
                         and REP["marker_max_bounds_err_cm"] <= TOL_CM
                         and REP["marker_max_ledge_err_cm"] <= TOL_CM and REP["world_settings"]["ok"]
                         and not REP["setp_failed"])
    except Exception:  # noqa: BLE001
        REP["error"] = traceback.format_exc()[-3000:]
        REP["passed"] = False
    REP["sec"] = round(time.time() - t0, 1)
    C.write_json(C.OUT / "level.json", REP)
    g = REP.get("bounds_gate", {})
    unreal.log(f"DJ_STEP_DONE level passed={REP['passed']} meshes={REP.get('mesh_actors')} "
               f"markers={len(REP.get('markers', []))} gate_max_err_cm={g.get('max_err_cm_all')} saved={REP.get('saved')}")


main()
