"""DojoLab COLOUR PROBE (diagnostic, read-only: never saves anything). Runs inside the offscreen editor like
dj_sc_capture.py (run_sc_capture.ps1 -Script dj_sc_colour_probe.py -LogName colour_probe).

Question it answers: is a colour cast in the captures from the MATERIALS or from the LIGHTING / POST chain?
In memory only, beside the path in the east sand field (Blender frame, metres), it spawns probe cards (thin engine cubes):
  lit row   (face -X, toward the low W sun): grey 0.18, tile BC card, plaster BC card
  shade row (face -Y, away from the sun, lit by sky + bounce only): grey 0.18, tile card, plaster card
  unlit     emissive neutral grey at three strengths (black base): the post chain alone (tonemapper, grade)
Tile / plaster cards use M_DJ_Prop_Master (no vertex-colour weathering) with the kit's own T_DK_RoofTile_BC /
T_DK_EarthPlaster_BC, so the texture decode path is the shipped one.
For each VARIANT in the spec (env DJ_PROBE_SPEC, a JSON list; every variant starts from the saved level's values):
  post (PPV settings overrides), sky_factor, sun_kelvin (null = temperature off), sun_lux, lamp_scale,
  skylight_intensity, fog (bool), recapture (sky light: one-off capture instead of real time), sun_atmosphere,
  settle (ticks), cams (PROBE_LIT / PROBE_SHADE and/or showcase cameras)
it captures FINAL_COLOR_LDR PNGs; measure_probe.py reads the card boxes (projected here) from them.
Out: <DJ_PROBE_OUT>/<variant>/<cam>.png + probe.json (card pixel boxes per probe camera)
"""
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\dojo\unreal")))
import unreal as ue  # noqa: E402
import dj_common as C  # noqa: E402
import dj_sc_common as S  # noqa: E402

EAS = ue.get_editor_subsystem(ue.EditorActorSubsystem)
RL = ue.RenderingLibrary
LAYOUT = S.load()
CAMS = {c["name"]: c for c in LAYOUT["cameras"]}
SPEC = json.loads(Path(os.environ["DJ_PROBE_SPEC"]).read_text(encoding="utf-8"))
OUT = Path(os.environ.get("DJ_PROBE_OUT", str(S.SC_OUT.parent / "round2_polish" / "probe")))
FRAMES = int(os.environ.get("DJ_FRAMES", "72"))
WARM = int(os.environ.get("DJ_WARM", "300"))
SETTLE = int(os.environ.get("DJ_SETTLE", "90"))    # ticks after a variant change (sky light recapture, Lumen)
REP = {"engine": ue.SystemLibrary.get_engine_version(), "frames": FRAMES, "variants": {}, "cards": {}, "errors": [],
       "notes": []}
T0 = time.time()
# probe cameras (Blender frame). LIT: west of a row of cards facing the low W sun (-X). SHADE: horizontal cards in the
# west wall's shadow (the sun ray from (<=6.0, 12, 0.3) passes the wall at <= +1.73, under its +2.0 top), so they see
# the sky and the bounce only; the unlit emissive cards stand behind them facing the camera.
PROBES = {
    "PROBE_LIT": {"loc": (31.2, 10.4, 1.35), "look_at": (34.0, 10.4, 1.15), "hfov_deg": 55.0, "out_wh": (1600, 1000)},
    "PROBE_SHADE": {"loc": (4.8, 9.4, 1.8), "look_at": (4.8, 12.4, 0.45), "hfov_deg": 60.0, "out_wh": (1600, 1000)},
}
CARD = 0.8   # card width / height (m)
# (name, centre (Blender m), facing normal (Blender), kind, params, probe cam)
CARDS = [
    ("lit_grey18", (34.0, 9.45, 1.2), (-1, 0, 0), "flat", {"Base Colour": (0.18, 0.18, 0.18)}, "PROBE_LIT"),
    ("lit_tile", (34.0, 10.4, 1.2), (-1, 0, 0), "tex", {"BC": "T_DK_RoofTile_BC"}, "PROBE_LIT"),
    ("lit_plaster", (34.0, 11.35, 1.2), (-1, 0, 0), "tex", {"BC": "T_DK_EarthPlaster_BC"}, "PROBE_LIT"),
    ("shade_grey18", (3.8, 12.0, 0.3), (0, 0, 1), "flat", {"Base Colour": (0.18, 0.18, 0.18)}, "PROBE_SHADE"),
    ("shade_tile", (4.8, 12.0, 0.3), (0, 0, 1), "tex", {"BC": "T_DK_RoofTile_BC"}, "PROBE_SHADE"),
    ("shade_plaster", (5.8, 12.0, 0.3), (0, 0, 1), "tex", {"BC": "T_DK_EarthPlaster_BC"}, "PROBE_SHADE"),
    ("unlit_grey_lo", (3.8, 13.3, 0.8), (0, -1, 0), "unlit", {"k": 4.0}, "PROBE_SHADE"),
    ("unlit_grey_mid", (4.8, 13.3, 0.8), (0, -1, 0), "unlit", {"k": 16.0}, "PROBE_SHADE"),
    ("unlit_grey_hi", (5.8, 13.3, 0.8), (0, -1, 0), "unlit", {"k": 64.0}, "PROBE_SHADE"),
]


def log(*a):
    ue.log("[DJ_PROBE] " + " ".join(str(x) for x in a))


def save_rep():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "probe.json").write_text(json.dumps(REP, indent=1, default=str), encoding="utf-8")


def world():
    return ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()


def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        REP["notes"].append(f"setp {type(obj).__name__}.{k}: {str(exc)[:160]}")
        return False


def V(t):
    return ue.Vector(float(t[0]), float(t[1]), float(t[2]))


def rot_look(loc_bl, look_bl):
    pitch, yaw = C.pitch_yaw_of(C.dir_bl_to_ue([a - b for a, b in zip(look_bl, loc_bl)]))
    r = ue.Rotator()
    r.pitch, r.yaw, r.roll = pitch, yaw, 0.0
    return r


def spawn_cards():
    cube = ue.load_asset("/Engine/BasicShapes/Cube")
    masters = {"flat": ue.load_asset(f"{S.MASTER_DIR}/M_DJ_Flat_Master"),
               "tex": ue.load_asset(f"{S.MASTER_DIR}/M_DJ_Prop_Master"),
               "unlit": ue.load_asset(f"{S.MASTER_DIR}/M_DJ_EmissiveFlat_Master")}
    out = []
    for name, c, n, kind, prm, _cam in CARDS:
        # engine cube: 100 cm, pivot at the centre; thin along the facing axis
        sc = (0.02, CARD, CARD) if n[0] else ((CARD, 0.02, CARD) if n[1] else (CARD, CARD, 0.02))
        a = EAS.spawn_actor_from_class(ue.StaticMeshActor, V(C.loc_cm(c)), ue.Rotator())
        a.set_actor_scale3d(V(sc))
        smc = a.static_mesh_component
        smc.set_mobility(ue.ComponentMobility.MOVABLE)
        smc.set_static_mesh(cube)
        mid = ue.MaterialLibrary.create_dynamic_material_instance(world(), masters[kind])
        if kind == "flat":
            mid.set_vector_parameter_value("Base Colour", ue.LinearColor(*prm["Base Colour"], 1.0))
            mid.set_scalar_parameter_value("Roughness", 0.9)
            mid.set_scalar_parameter_value("Specular", 0.5)
        elif kind == "tex":
            mid.set_texture_parameter_value("Base Colour Map", ue.load_asset(S.tex_path(LAYOUT, prm["BC"])))
            orm = prm["BC"].replace("_BC", "_ORM")
            nm = prm["BC"].replace("_BC", "_N")
            if orm in LAYOUT["textures"]:
                mid.set_texture_parameter_value("ORM Map", ue.load_asset(S.tex_path(LAYOUT, orm)))
            if nm in LAYOUT["textures"]:
                mid.set_texture_parameter_value("Normal Map", ue.load_asset(S.tex_path(LAYOUT, nm)))
        else:
            mid.set_vector_parameter_value("Base Colour", ue.LinearColor(0.0, 0.0, 0.0, 1.0))
            mid.set_vector_parameter_value("Emissive Colour", ue.LinearColor(0.18, 0.18, 0.18, 1.0))
            mid.set_scalar_parameter_value("Emissive Intensity", float(prm["k"]))
            smc.set_editor_property("cast_shadow", False)
        smc.set_material(0, mid)
        a.set_actor_label("PROBE_" + name)
        out.append((name, c, n, a, _cam))
    return out


def project(cam_loc_ue, cam_rot, hfov, w, h, p_ue):
    f = cam_rot.get_forward_vector()
    r = cam_rot.get_right_vector()
    u = cam_rot.get_up_vector()
    d = p_ue - cam_loc_ue
    z = d.dot(f)
    t = math.tan(math.radians(hfov) / 2.0)
    x = d.dot(r) / z / t
    y = d.dot(u) / z / t * (w / h)
    return ((x + 1.0) / 2.0 * w, (1.0 - y) / 2.0 * h)


def card_boxes(cards, cam, cam_loc_ue, cam_rot, hfov, w, h):
    boxes = {}
    for name, c, n, _a, pc in cards:
        if pc != cam:
            continue
        half = CARD * 0.30   # inner 60 % of the face
        face_c = (c[0] + n[0] * 0.011, c[1] + n[1] * 0.011, c[2] + n[2] * 0.011)
        if n[0]:
            corners = [(face_c[0], face_c[1] + sy * half, face_c[2] + sz * half) for sy in (-1, 1) for sz in (-1, 1)]
        elif n[1]:
            corners = [(face_c[0] + sx * half, face_c[1], face_c[2] + sz * half) for sx in (-1, 1) for sz in (-1, 1)]
        else:
            corners = [(face_c[0] + sx * half, face_c[1] + sy * half, face_c[2]) for sx in (-1, 1) for sy in (-1, 1)]
        pts = [project(cam_loc_ue, cam_rot, hfov, w, h, V(C.loc_cm(p))) for p in corners]
        centre = project(cam_loc_ue, cam_rot, hfov, w, h, V(C.loc_cm(face_c)))
        boxes[name] = {"centre_px": [round(centre[0], 1), round(centre[1], 1)],
                       "box_px": [round(min(p[0] for p in pts)), round(min(p[1] for p in pts)),
                                  round(max(p[0] for p in pts)), round(max(p[1] for p in pts))]}
    return boxes


PP_KEYS = ("auto_exposure_bias", "color_gain", "color_saturation", "color_contrast", "color_gamma", "white_temp",
           "white_tint", "bloom_intensity", "color_saturation_shadows", "color_gain_shadows", "color_offset_shadows",
           "color_saturation_highlights", "color_gain_highlights", "vignette_intensity", "film_slope", "film_toe",
           "film_shoulder", "film_black_clip", "film_white_clip", "tone_curve_amount", "expand_gamut", "blue_correction")


class Env:
    def __init__(self, actors):
        self.sun = actors["Sun_Sunset"].get_editor_property("directional_light_component")
        self.sky = actors["SkyAtmosphere"].get_component_by_class(ue.SkyAtmosphereComponent)
        self.skyl = actors["SkyLight"].get_editor_property("light_component")
        self.fog = actors["ExponentialHeightFog"].get_editor_property("component")
        self.ppv = actors["PostProcess_Dojo"]
        self.lamps = [a.get_editor_property("point_light_component") for lab, a in actors.items()
                      if lab.startswith("Light_") and isinstance(a, ue.PointLight)]
        self.base = {"sun_use_temp": self.sun.get_editor_property("use_temperature"),
                     "sun_kelvin": self.sun.get_editor_property("temperature"),
                     "sun_lux": self.sun.get_editor_property("intensity"),
                     "sky_factor": self.sky.get_editor_property("sky_luminance_factor"),
                     "skyl": self.skyl.get_editor_property("intensity"),
                     "lamps": [c.get_editor_property("intensity") for c in self.lamps],
                     "pp": self.ppv.get_editor_property("settings")}
        pp = self.base["pp"]
        self.base_pp = {}
        for k in PP_KEYS:
            try:
                self.base_pp[k] = (pp.get_editor_property(k), pp.get_editor_property("override_" + k))
            except Exception as exc:  # noqa: BLE001
                REP["notes"].append(f"pp key {k}: {str(exc)[:120]}")
        self.base_pp_dump = {k: [str(v[0]), bool(v[1])] for k, v in self.base_pp.items()}

    def apply(self, v):
        b = self.base
        k = v.get("sun_kelvin", "base")
        if k == "base":
            setp(self.sun, "use_temperature", b["sun_use_temp"])
            setp(self.sun, "temperature", b["sun_kelvin"])
        elif k is None:
            setp(self.sun, "use_temperature", False)
        else:
            setp(self.sun, "use_temperature", True)
            setp(self.sun, "temperature", float(k))
        setp(self.sun, "intensity", float(v.get("sun_lux", b["sun_lux"])))
        sf = v.get("sky_factor")
        setp(self.sky, "sky_luminance_factor", ue.LinearColor(*sf, 1.0) if sf else b["sky_factor"])
        setp(self.skyl, "intensity", float(v.get("skylight_intensity", b["skyl"])))
        _c = [int(x) for x in v.get("skylight_color", (255, 255, 255))]
        setp(self.skyl, "light_color", ue.Color(r=_c[0], g=_c[1], b=_c[2], a=255))
        ls = float(v.get("lamp_scale", 1.0))
        for c, i0 in zip(self.lamps, b["lamps"]):
            setp(c, "intensity", float(i0) * ls)
        self.fog.set_visibility(bool(v.get("fog", True)))
        pp = self.ppv.get_editor_property("settings")
        for key, (val, ov) in self.base_pp.items():      # every variant starts from the saved grade
            setp(pp, key, val)
            setp(pp, "override_" + key, ov)
        for key, val in (v.get("post") or {}).items():
            if key not in self.base_pp:
                raise KeyError(f"post key {key} not in PP_KEYS")
            if isinstance(val, list):
                val = ue.Vector4(*val)
            setp(pp, "override_" + key, True)
            setp(pp, key, val)
        setp(self.ppv, "settings", pp)
        # "recapture": switch the sky light to a one-off capture of the current sky (real time again otherwise);
        # tells whether the offscreen editor's real-time capture follows the changes
        if v.get("recapture"):
            setp(self.skyl, "real_time_capture", False)
            try:
                self.skyl.recapture_sky()
            except Exception as exc:  # noqa: BLE001
                REP["notes"].append(f"recapture_sky: {exc}")
        else:
            setp(self.skyl, "real_time_capture", True)
        setp(self.sun, "atmosphere_sun_light", bool(v.get("sun_atmosphere", True)))


def make_capture(loc_ue, rot_ue, hfov, w, h, hidden, gi="LUMEN"):
    cap = EAS.spawn_actor_from_class(ue.SceneCapture2D, loc_ue, rot_ue)
    cc = cap.get_editor_property("capture_component2d")
    rt = RL.create_render_target2d(world(), w, h, ue.TextureRenderTargetFormat.RTF_RGBA8)
    src = ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR
    for k, v in (("texture_target", rt), ("capture_source", src), ("capture_every_frame", False),
                 ("capture_on_movement", False), ("always_persist_rendering_state", True), ("fov_angle", float(hfov))):
        setp(cc, k, v)
    for a in hidden:
        cc.hide_actor_components(a, True)
    pp = cc.get_editor_property("post_process_settings")
    for k, v in (("override_dynamic_global_illumination_method", True),
                 ("dynamic_global_illumination_method", getattr(ue.DynamicGlobalIlluminationMethod, gi)),
                 ("override_reflection_method", True), ("reflection_method", ue.ReflectionMethod.LUMEN),
                 ("override_lumen_surface_cache_resolution", True), ("lumen_surface_cache_resolution", 1.0)):
        setp(pp, k, v)
    setp(cc, "post_process_settings", pp)
    setp(cc, "post_process_blend_weight", 1.0)
    return cap, cc, rt


def program():
    les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
    for _ in range(5):
        yield
    REP["level_loaded"] = bool(les.load_level(C.LEVEL))
    cards = spawn_cards()
    t = time.time()
    n = 0
    while n < WARM or time.time() - t < 15:
        n += 1
        yield
    actors = {a.get_actor_label(): a for a in EAS.get_all_level_actors()}
    env = Env(actors)
    REP["base"] = {"sun_kelvin": env.base["sun_kelvin"], "sun_use_temp": env.base["sun_use_temp"],
                   "sun_lux": env.base["sun_lux"], "sky_factor": str(env.base["sky_factor"]), "skylight": env.base["skyl"],
                   "lamps": len(env.lamps), "pp": env.base_pp_dump}
    hidden = [a for lab, a in actors.items() if lab.startswith("TRV_") or lab.startswith("SM_DGB_Boundary_1v1")]
    views = {}
    for pn, pcfg in PROBES.items():
        loc, r_ = V(C.loc_cm(pcfg["loc"])), rot_look(pcfg["loc"], pcfg["look_at"])
        views[pn] = (loc, r_, pcfg["hfov_deg"], pcfg["out_wh"])
        REP["cards"][pn] = card_boxes(cards, pn, loc, r_, pcfg["hfov_deg"], *pcfg["out_wh"])
    for v in SPEC:
        vname = v["name"]
        env.apply(v)
        for _ in range(int(v.get("settle", SETTLE))):
            yield
        rec = {"spec": v, "captures": {}}
        for cam in v.get("cams", list(PROBES)):
            if cam in views:
                loc, rt_, hf, (w, h) = views[cam]
            else:
                ca = actors.get(cam)
                lay = CAMS[cam]
                loc, rt_, hf, (w, h) = ca.get_actor_location(), ca.get_actor_rotation(), lay["hfov_deg"], lay["out_wh"]
            cap, cc, rt = make_capture(loc, rt_, hf, w, h, hidden, v.get("gi", "LUMEN"))
            for _ in range(FRAMES):
                cc.capture_scene()
                yield
            folder = OUT / vname
            folder.mkdir(parents=True, exist_ok=True)
            RL.export_render_target(world(), rt, str(folder), f"{cam}.png")
            rec["captures"][cam] = str(folder / f"{cam}.png")
            EAS.destroy_actor(cap)
        REP["variants"][vname] = rec
        save_rep()
        log("VARIANT", vname)
    for _n, _c, _nn, a, _pc in cards:
        EAS.destroy_actor(a)
    REP["passed"] = not REP["errors"]
    REP["sec"] = round(time.time() - T0, 1)
    save_rep()
    ue.log(f"DJ_STEP_DONE sc_colour_probe passed={REP['passed']} variants={len(REP['variants'])}")


GEN = program()
STATE = {}


def tick(dt):
    if STATE.get("busy") or STATE.get("finished"):
        return
    STATE["busy"] = True
    try:
        next(GEN)
    except StopIteration:
        STATE["finished"] = True
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        ue.SystemLibrary.quit_editor()
    except Exception:  # noqa: BLE001
        STATE["finished"] = True
        REP["errors"].append(traceback.format_exc()[-3000:])
        REP["passed"] = False
        save_rep()
        ue.log("DJ_STEP_DONE sc_colour_probe passed=False")
        ue.unregister_slate_post_tick_callback(STATE["cb"])
        ue.SystemLibrary.quit_editor()
    finally:
        STATE["busy"] = False


STATE["cb"] = ue.register_slate_post_tick_callback(tick)
try:
    ue.EditorPythonScripting.set_keep_python_script_alive(True)
except Exception:  # noqa: BLE001
    pass
log("registered; variants", [v["name"] for v in SPEC])
