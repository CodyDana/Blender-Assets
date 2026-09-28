"""pd_player_default.py -- build + verify /Game/Characters/MetaHumans/MH_PlayerDefault (UE 5.8.3, MetaHumanCharacter).

Runs INSIDE UnrealEditor on Exports/CharacterLab/Unreal/CharacterLab.uproject; launch with
Scripts/MetaHuman/pd_run_player_default.ps1 (one editor at a time, RAM preflight, SHA-256 of the protected assets
before/after, waits for exit).

PD_MODE=build   duplicate MH_PlayerBase_FaceC -> MH_PlayerDefault (face + body geometry untouched: the FaceC recipe
                is carried over exactly by the duplicate), apply the identity (skin texture variant, neutral tone,
                no freckles, dark-brown eyes, natural brows + lashes, short hair, no beard / moustache / makeup /
                outfit) and SAVE MH_PlayerDefault. Nothing else is saved.
PD_MODE=verify  fresh session, saves NOTHING: reload the saved MH_PlayerDefault, read every setting back, compare
                the face coefficients with FaceC's build report and the body state with MH_PlayerBase
                (compare_body_state / compare_face_state + vertex dumps + bones + constraints), and capture
                after_* (MH_PlayerDefault) and before_* (scratch duplicate of FaceC, never saved) with the pb_conform
                studio rig + cameras, plus the evaluation-rig variants that isolate the capture artefacts.

Never signs in; never calls request_auto_rigging / request_texture_sources / build_meta_human. MH_PlayerBase,
FaceA/B/C and MH_MaleBase are only read (FaceC / MH_PlayerBase through in-memory duplicates under
/Game/PlayerDefault/Scratch that are never saved).

Outputs: WorkFiles/MetaHuman/player_default/ (pd_<mode>_<attempt>.json, player_default.log, captures/*.png,
mesh_dump/*.obj, player_default_recipe.json).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import unreal as ue

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/MetaHuman/player_default"
CAPTURES = OUT / "captures"
DUMPS = OUT / "mesh_dump"
MODE = os.environ.get("PD_MODE", "build").strip().lower()
ATTEMPT = os.environ.get("PD_ATTEMPT", "1").strip()
REPORT_PATH = OUT / f"pd_{MODE}_{ATTEMPT}.json"
STEP_LOG = OUT / "player_default.log"
RECIPE_PATH = OUT / "player_default_recipe.json"
CONTENT = ROOT / "Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
PROTECTED = ["MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase"]
FACE_BUILD_REPORT = ROOT / "WorkFiles/MetaHuman/player_base/faces/face_build_report_2.json"
FACE_RECIPES = ROOT / "WorkFiles/MetaHuman/player_base/faces/face_recipes_v2.json"

CHAR_DIR = "/Game/Characters/MetaHumans"
FACEC_PATH = f"{CHAR_DIR}/MH_PlayerBase_FaceC"
BASE_PATH = f"{CHAR_DIR}/MH_PlayerBase"
PD_NAME = "MH_PlayerDefault"
PD_PATH = f"{CHAR_DIR}/{PD_NAME}"
SCRATCH = "/Game/PlayerDefault/Scratch"
PRESET_SRC = "/MetaHumanCharacter/Optional/Presets"
GROOM_ROOT = "/MetaHumanCharacter/Optional/Grooms/Bindings"
FORBIDDEN_TOKENS = ("jinmuwon", "muwon", "mu-won", "mu_won")
MAX_SECONDS = float(os.environ.get("PD_MAX_MINUTES", "45")) * 60.0

# ---- identity recipe (what MH_PlayerDefault gets on top of the FaceC duplicate) --------------------------------
IDENTITY = {
    "source_asset": FACEC_PATH,
    "face_and_body_geometry": "unchanged duplicate of MH_PlayerBase_FaceC (FaceC recipe = face_recipes_v2.json "
                              "candidate MH_PlayerBase_FaceC; coefficients = face_build_report_2.json)",
    "skin": {"face_texture_index": 36, "u": 0.5, "v": 0.5, "show_top_underwear": True,
             "body_texture_index": "kept (0)", "roughness": "kept (1.06)", "accents": "kept (all 0.5 = neutral)",
             "freckles_mask": "NONE", "enable_texture_overrides": False,
             "why": "TS-1.3 face texture 36: wrinkles Low, stubble None, marks Low (FaceC had index 0 = marks Medium, "
                    "the red moles); tone u/v 0.5/0.5 = MetaHuman neutral mid tone (players retint at runtime)"},
    "eyes": {"from_preset": "Kelvin", "iris_pattern": "IRIS006", "primary_color_uv": [0.9003, 0.0755],
             "secondary_color_uv": [0.9753, 0.0964], "why": "natural dark brown (FaceC was amber U0.90 V0.56)"},
    "eyelashes_head_model": {"type": "SHORT_FINE", "enable_grooms": True, "melanin": 0.9,
                             "why": "Creator path: sets the eyelash variant and auto-selects groom WI_Eyelashes_S_Fine "
                                    "(Editor.ini EyelashesTypeToAssetPath); melanin 0.9 colours the LOD0 eyelash cards "
                                    "(default 0.3 rendered pale tips in build attempt 1)"},
    "grooms": {"Hair": "WI_Hair_S_BrushCut", "Eyebrows": "WI_Eyebrows_M_SlightArch",
               "Eyelashes": "WI_Eyelashes_S_Fine (via head-model eyelashes)",
               "Beard": None, "Mustache": None, "Peachfuzz": None, "Outfits": None,
               "groom_colour": "instance parameter Melanin 0.9 on Hair, Eyebrows and Eyelashes (other parameters "
                               "at wardrobe defaults: Redness 0.25, Roughness 0.37, Lightness 0.5) = natural dark "
                               "brown; the default Melanin 0.8 rendered blond-looking brows in build attempt 1"},
    "makeup": "none (MetaHumanCharacterMakeupSettings() defaults: every type NONE, foundation off)",
    "outfit": "none; tank top + briefs are the skin material's painted underwear (show_top_underwear=True keeps "
              "the body decent); no wardrobe outfit item exists or is added",
}
HAIR_WI = f"{GROOM_ROOT}/Hair/WI_Hair_S_BrushCut"
BROWS_WI = f"{GROOM_ROOT}/Eyebrows/WI_Eyebrows_M_SlightArch"
LASHES_WI = f"{GROOM_ROOT}/Eyelashes/WI_Eyelashes_S_Fine"
EYES_PRESET = f"{PRESET_SRC}/Kelvin"
FACE_TEXTURE_INDEX = 36
GROOM_MELANIN = 0.9
LASH_CARD_MELANIN = 0.9
EMPTY_SLOTS = ("Beard", "Mustache", "Peachfuzz", "Outfits", "Top Garment", "Bottom Garment")

# ---- cameras / lights: identical to pb_conform.py / pb_face_design.py / pd_diagnose.py -------------------------
LIGHT_RIG = [(-27.0, -117.0, 0.0, 4.0, (1, .95, .9), True),    # key: front-right, above, shadows
             (-12.0, -58.0, 0.0, 2.0, (.9, .94, 1), False),    # fill: front-left, low
             (-37.0, 90.0, 0.0, 2.0, (1, 1, 1), False)]        # rim: behind, above
SKY_INTENSITY = 1.5
SIMPLE_RENDER_CVARS = ["r.DynamicGlobalIlluminationMethod 0", "r.ReflectionMethod 0", "r.AmbientOcclusionLevels 0",
                       "r.DistanceFieldAO 0", "r.RayTracing.ForceAllRayTracingEffects 0", "r.AntiAliasingMethod 2"]
SHOT_W, SHOT_H = 1000, 1200
ORTHO_RES, ORTHO_WIDTH, ORTHO_CAM_Z = 1200, 240.0, 95.0
BODY_CAM_DIST, BODY_CAM_Z = 380.0, 93.0
FACE_CAM_DIST = 70.0
FACE_CENTER = (0.0, 5.959721088409424, 173.6)          # conform_report.json mh_face_center (builder's camera)
HAND_CENTERS = {"xneg": (-54.65, 19.959, 102.01), "xpos": (54.6305, 19.952, 102.031)}  # conform_report mh_hand_centers
WARMUP_FRAMES = 150
SETTLE_FRAMES = 45
SETTLE_SECONDS = 1.5
MH_BONES = ["root", "pelvis", "spine_05", "neck_01", "head", "clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r",
            "lowerarm_l", "lowerarm_r", "hand_l", "hand_r", "middle_03_l", "middle_03_r", "thigh_l", "thigh_r",
            "calf_l", "calf_r", "foot_l", "foot_r", "ball_l", "ball_r"]

T0 = time.monotonic()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def protected_hashes() -> dict:
    return {n: sha256(CONTENT / f"{n}.uasset") for n in PROTECTED}


REPORT: dict = {"script": "Scripts/MetaHuman/pd_player_default.py", "mode": MODE, "attempt": ATTEMPT,
                "engine": ue.SystemLibrary.get_engine_version(), "status": "starting", "started_utc": _now(),
                "steps": [], "captures": [], "warnings": [], "checks": {}}


def write_report() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(REPORT, indent=1, default=str), encoding="utf-8")


def step(msg: str, **extra) -> None:
    t = round(time.monotonic() - T0, 1)
    line = f"{_now()}  +{t:7.1f}s  [{MODE}/{ATTEMPT}] {msg}"
    if extra:
        line += "  " + json.dumps(extra, default=str)[:3000]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    ue.log("PD_PLAYERDEFAULT " + line)
    REPORT["steps"].append({"t_s": t, "msg": msg, **extra})
    write_report()


def warn(msg: str) -> None:
    REPORT["warnings"].append(msg)
    step("WARNING " + msg)


def check(name: str, ok: bool, **detail) -> bool:
    REPORT["checks"][name] = {"ok": bool(ok), **detail}
    step(f"CHECK {name}: {'OK' if ok else 'FAIL'}", **detail)
    return bool(ok)


def assert_clean(*names: str) -> None:
    for name in names:
        low = str(name).lower()
        bad = [t for t in FORBIDDEN_TOKENS if t in low]
        if bad:
            raise ValueError(f"Refusing name {name!r}: contains {bad}")


def assert_locks() -> None:
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock  # stdlib only
    for name in PROTECTED + [PD_NAME]:
        lock.assert_owner(name, "claude")


def unwrap(result):
    if isinstance(result, tuple) and len(result) == 1:
        return result[0]
    return result


def pth(obj):
    try:
        return obj.get_path_name() if obj is not None else None
    except Exception:  # noqa: BLE001
        return str(obj)


def enum_s(v):
    return str(v).split(".")[-1].split(":")[0].strip("<> ")


def v3(v) -> list:
    return [round(float(v.x), 4), round(float(v.y), 4), round(float(v.z), 4)]


def struct_dict(s, depth: int = 0):
    """Best-effort dump of an unreal struct (editor properties) to plain json."""
    if depth > 4:
        return str(s)
    if isinstance(s, (bool, int, float, str)) or s is None:
        return s
    if isinstance(s, ue.LinearColor):
        return [round(s.r, 4), round(s.g, 4), round(s.b, 4), round(s.a, 4)]
    if isinstance(s, ue.Vector) or type(s).__name__ in ("Vector3f", "Vector3d"):
        return [round(s.x, 4), round(s.y, 4), round(s.z, 4)]
    if isinstance(s, ue.EnumBase):
        return enum_s(s)
    if isinstance(s, ue.Object):
        return pth(s)
    if isinstance(s, ue.StructBase):
        out = {}
        for name in dir(s):
            if name.startswith("_") or callable(getattr(type(s), name, None)):
                continue
            try:
                out[name] = struct_dict(s.get_editor_property(name), depth + 1)
            except Exception:  # noqa: BLE001
                continue
        return out
    if isinstance(s, (list, tuple, ue.Array)):
        return [struct_dict(x, depth + 1) for x in s]
    if isinstance(s, (dict, ue.Map)):
        return {str(k): struct_dict(v, depth + 1) for k, v in s.items()}
    return str(s)


# ---------------------------------------------------------------------------------------------------------------
# Scene: pb_conform studio rig + backdrop + capture settings, plus evaluation-rig variants
# ---------------------------------------------------------------------------------------------------------------
class Scene:
    def __init__(self):
        ue.EditorLoadingAndSavingUtils.new_blank_map(False)  # untitled, never saved
        self.world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.lights = [self.spawn(ue.DirectionalLight) for _ in LIGHT_RIG]
        # evaluation-rig extra light (pd_diagnose 'bounce'): weak, unshadowed, from the front and BELOW, standing in
        # for the ambient / ground bounce this offscreen rig lacks. Intensity 0 = off in the studio rig.
        self.bounce_light = self.spawn(ue.DirectionalLight)
        self.bounce_light.set_actor_rotation(ue.Rotator(roll=0.0, pitch=50.0, yaw=-90.0), False)
        self.bounce_light.light_component.set_cast_shadows(False)
        self.bounce_light.light_component.set_intensity(0.0)
        backdrop = self.spawn(ue.StaticMeshActor)
        backdrop.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Sphere"))
        backdrop.set_actor_scale3d(ue.Vector(50, 50, 50))
        backdrop.static_mesh_component.set_cast_shadow(False)
        mat = ue.new_object(ue.Material)  # transient
        mat.set_editor_property("two_sided", True)
        mat.set_editor_property("shading_model", ue.MaterialShadingModel.MSM_UNLIT)
        node = ue.MaterialEditingLibrary.create_material_expression(mat, ue.MaterialExpressionConstant3Vector)
        node.set_editor_property("constant", ue.LinearColor(.18, .18, .18, 1))
        ue.MaterialEditingLibrary.connect_material_property(node, "", ue.MaterialProperty.MP_EMISSIVE_COLOR)
        ue.MaterialEditingLibrary.recompile_material(mat)
        backdrop.static_mesh_component.set_material(0, mat)
        self.backdrop = backdrop
        self.sky = self.spawn(ue.SkyLight)
        self.sky.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        self.sky.light_component.set_intensity(SKY_INTENSITY)
        self.sky.light_component.recapture_sky()
        # studio sky = pb_conform sky: default SkyDistanceThreshold (150000 cm) means the backdrop sphere (r 2500 cm)
        # is NOT captured and the lower hemisphere is black -> the sky light adds nothing (pd_diagnose 'sky only' = black)
        self.sky_default = {}
        for prop in ("sky_distance_threshold", "lower_hemisphere_is_black"):
            try:
                self.sky_default[prop] = self.sky.light_component.get_editor_property(prop)
            except Exception as exc:  # noqa: BLE001
                self.sky_default[prop] = "ERR " + repr(exc)[:80]
        REPORT["sky_default"] = {k: str(v) for k, v in self.sky_default.items()}
        self.sky_ambient = False
        self.camera = self.spawn(ue.SceneCapture2D)
        self.capture = self.camera.get_component_by_class(ue.SceneCaptureComponent2D)
        self.rt = ue.RenderingLibrary.create_render_target2d(self.world, SHOT_W, SHOT_H,
                                                             ue.TextureRenderTargetFormat.RTF_RGBA8)
        self.rt.set_editor_property("target_gamma", 2.2)
        self.rt_ortho = ue.RenderingLibrary.create_render_target2d(self.world, ORTHO_RES, ORTHO_RES,
                                                                   ue.TextureRenderTargetFormat.RTF_RGBA8)
        cap = self.capture
        cap.set_editor_property("texture_target", self.rt)
        cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cap.set_editor_property("capture_every_frame", False)
        cap.set_editor_property("always_persist_rendering_state", True)
        cap.set_editor_property("projection_type", ue.CameraProjectionMode.PERSPECTIVE)
        pp = cap.get_editor_property("post_process_settings")
        for key, value in [("override_auto_exposure_method", True),
                           ("auto_exposure_method", ue.AutoExposureMethod.AEM_MANUAL),
                           ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0),
                           ("override_auto_exposure_apply_physical_camera_exposure", True),
                           ("auto_exposure_apply_physical_camera_exposure", False),
                           ("override_vignette_intensity", True), ("vignette_intensity", 0.0)]:
            pp.set_editor_property(key, value)
        cap.set_editor_property("post_process_settings", pp)
        for command in SIMPLE_RENDER_CVARS:
            ue.SystemLibrary.execute_console_command(self.world, command)
        self.hidden = []
        self.variant = None
        self.set_variant("studio")

    def spawn(self, cls, location=(0, 0, 0)):
        return self.actors.spawn_actor_from_class(cls, ue.Vector(*location), ue.Rotator())

    def show_only(self, keep, all_actors) -> None:
        self.hidden = [a for a in all_actors if a is not None and a != keep]
        self.apply_hidden()

    def apply_hidden(self) -> None:
        self.capture.clear_hidden_components()
        for actor in self.hidden:
            self.capture.hide_actor_components(actor, True)

    def set_sky_ambient(self, on: bool) -> bool:
        """ambient: the SAME sky light, made to actually capture the unlit 0.18-grey backdrop all around (threshold
        1000 cm < backdrop radius 2500 cm, lower hemisphere not forced black) = uniform grey-studio ambient, the
        light any real level provides. Returns True when the sky state changed (a recapture was requested)."""
        if bool(on) == self.sky_ambient:
            return False
        comp = self.sky.light_component
        try:
            if on:
                comp.set_editor_property("sky_distance_threshold", 1000.0)
                comp.set_editor_property("lower_hemisphere_is_black", False)
            else:
                comp.set_editor_property("sky_distance_threshold", float(self.sky_default["sky_distance_threshold"]))
                comp.set_editor_property("lower_hemisphere_is_black", bool(self.sky_default["lower_hemisphere_is_black"]))
            comp.recapture_sky()
            REPORT.setdefault("sky_switches", []).append(
                {"ambient": bool(on), "sky_distance_threshold": comp.get_editor_property("sky_distance_threshold"),
                 "lower_hemisphere_is_black": comp.get_editor_property("lower_hemisphere_is_black")})
        except Exception as exc:  # noqa: BLE001
            REPORT["warnings"].append(f"sky ambient switch {on}: {exc!r}")
        self.sky_ambient = bool(on)
        return True

    def set_variant(self, variant: str) -> bool:
        """studio     pb_conform rig exactly (key shadows, fill + rim unshadowed, sky 1.5)
        ambient    studio lights unchanged + the sky light capturing the grey backdrop (real ambient) (jaw test)
        bounce     studio + weak unshadowed up-light (pitch +50, yaw -90, 0.8) = the ambient this rig lacks (jaw test)
        rimshadow  studio with the rim light casting shadows (ear-glint test)
        rimspec0   studio with the rim light's specular scale 0 (diffuse rim kept) (ear-glint test)
        norim      studio without the rim light (ear-glint test)
        eval       bounce + rim casts shadows + rim specular scale 0.3 (recommended evaluation rig)
        base       GBuffer base colour (unlit albedo)"""
        for light, (pitch, yaw, roll, intensity, color, shadows) in zip(self.lights, LIGHT_RIG):
            light.set_actor_rotation(ue.Rotator(roll=roll, pitch=pitch, yaw=yaw), False)
            light.light_component.set_intensity(intensity)
            light.light_component.set_light_color(ue.LinearColor(*color, 1))
            light.light_component.set_cast_shadows(shadows)
            set_specular(light, 1.0)
        self.sky.light_component.set_intensity(SKY_INTENSITY)
        self.bounce_light.light_component.set_intensity(0.0)
        self.capture.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        rim = self.lights[2]
        if variant in ("bounce", "eval"):
            self.bounce_light.light_component.set_intensity(0.8)
            self.bounce_light.light_component.set_light_color(ue.LinearColor(1, .95, .9, 1))
        if variant in ("rimshadow", "eval"):
            rim.light_component.set_cast_shadows(True)
        if variant == "eval":
            set_specular(rim, 0.3)
        if variant == "rimspec0":
            set_specular(rim, 0.0)
        if variant == "norim":
            rim.light_component.set_intensity(0.0)
        if variant == "base":
            self.capture.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_BASE_COLOR)
        sky_changed = self.set_sky_ambient(variant == "ambient")
        self.variant = variant
        return sky_changed

    def aim(self, location, look_at, fov_deg: float = 30.0) -> None:
        loc = ue.Vector(*location)
        self.camera.set_actor_location_and_rotation(
            loc, ue.MathLibrary.find_look_at_rotation(loc, ue.Vector(*look_at)), False, False)
        self.capture.set_editor_property("fov_angle", float(fov_deg))

    def export(self, rt, name: str) -> str:
        CAPTURES.mkdir(parents=True, exist_ok=True)
        ue.RenderingLibrary.export_render_target(self.world, rt, str(CAPTURES), name)
        path = str(CAPTURES / name)
        REPORT["captures"].append(path)
        return path


def set_specular(light, value: float) -> None:
    comp = light.light_component
    try:
        comp.set_specular_scale(float(value))
    except Exception:  # noqa: BLE001
        comp.set_editor_property("specular_scale", float(value))


def orbit(target, dist, az_deg, el_deg):
    """Camera position around target: az 0 = in front (+Y), az>0 towards +X (character's left), el>0 above."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return (target[0] + dist * math.cos(el) * math.sin(az),
            target[1] + dist * math.cos(el) * math.cos(az),
            target[2] + dist * math.sin(el))


def all_views():
    """name -> (location, look_at, fov). Face_* = pb_face_design.face_shots, Body_* = pb_conform.body_shots,
    Hand_* = pb_conform.hand_shots (MH_PlayerBase hand centres), close-ups = pd_diagnose.face_views/body_views."""
    fx, fy, fz = FACE_CENTER
    c = FACE_CENTER
    d = FACE_CAM_DIST
    a = math.radians(35.0)
    v = {"Face_Front": ((fx, fy + d, fz), c, 30.0),
         "Face_ThreeQuarter": ((fx + d * math.sin(a), fy + d * math.cos(a), fz), c, 30.0),
         "Face_Profile": ((fx + d, fy, fz), c, 30.0)}
    z = BODY_CAM_Z
    v["Body_Front"] = ((0.0, BODY_CAM_DIST, z), (0.0, 0.0, z), 30.0)
    v["Body_Side"] = ((BODY_CAM_DIST, 0.0, z), (0.0, 0.0, z), 30.0)
    v["Body_Back"] = ((0.0, -BODY_CAM_DIST, z), (0.0, 0.0, z), 30.0)
    for label, hc in sorted(HAND_CENTERS.items()):
        s = 1.0 if hc[0] > 0 else -1.0
        v[f"Hand_{label}_Front"] = ((hc[0], hc[1] + 45.0, hc[2] + 10.0), hc, 30.0)
        v[f"Hand_{label}_Outer"] = ((hc[0] + s * 45.0, hc[1], hc[2] + 5.0), hc, 30.0)
    jaw = (fx + 2.0, fy + 1.0, fz - 10.0)
    jaw_l = (fx + 4.5, fy - 1.0, fz - 9.5)
    ear_r = (fx - 7.9, fy - 1.5, fz - 1.2)     # image-left ear in the front shot (character's right, -X)
    v["JawClose"] = (orbit(jaw_l, 32.0, 40, -8), jaw_l, 22.0)
    v["JawLow"] = (orbit(jaw, 60.0, 35, -28), jaw, 30.0)
    v["EarR"] = (orbit(ear_r, 32.0, 0, 0), ear_r, 20.0)
    v["EarRSide"] = (orbit(ear_r, 32.0, -80, 5), ear_r, 20.0)
    sh = (0.0, 0.0, 150.0)
    v["Shoulders_Front"] = ((0.0, 115.0, 156.0), sh, 26.0)
    v["Shoulders_High"] = (orbit(sh, 110.0, 0, 42), sh, 26.0)
    v["ShoulderL_TQ"] = (orbit((15.0, 0.0, 150.0), 75.0, 40, 12), (15.0, 0.0, 150.0), 26.0)
    v["ShoulderR_TQ"] = (orbit((-15.0, 0.0, 150.0), 75.0, -40, 12), (-15.0, 0.0, 150.0), 26.0)
    v["Shoulders_Back"] = ((0.0, -115.0, 156.0), sh, 26.0)
    v["Eyes"] = ((fx, fy + 45.0, fz + 0.8), (fx, fy, fz + 0.8), 16.0)
    head = (fx, fy - 2.0, fz + 3.0)
    v["Head_Back34"] = (orbit(head, 75.0, 145, 10), head, 30.0)
    v["Head_Top"] = (orbit(head, 70.0, 20, 50), head, 30.0)
    return v


STUDIO_VIEWS = ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "Body_Front", "Body_Side", "Body_Back",
                "Hand_xneg_Front", "Hand_xneg_Outer", "Hand_xpos_Front", "Hand_xpos_Outer",
                "JawClose", "JawLow", "EarR", "EarRSide", "Shoulders_Front", "Shoulders_High", "ShoulderL_TQ",
                "ShoulderR_TQ", "Shoulders_Back", "Eyes", "Head_Back34", "Head_Top"]
VARIANT_VIEWS = [("bounce", ["Face_Front", "Face_ThreeQuarter", "JawClose", "JawLow"]),
                 ("rimshadow", ["Face_Front", "EarR"]),
                 ("rimspec0", ["Face_Front", "EarR"]),
                 ("norim", ["Face_Front", "EarR"]),
                 ("eval", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "EarR", "Shoulders_Front",
                           "Body_Front", "Head_Back34"]),
                 ("ambient", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "JawLow", "EarR",
                              "Body_Front"]),
                 ("base", ["Face_Front", "Face_ThreeQuarter", "JawClose", "EarR", "EarRSide", "Shoulders_Front",
                           "Shoulders_High", "ShoulderL_TQ", "ShoulderR_TQ", "Shoulders_Back"])]


# ---------------------------------------------------------------------------------------------------------------
# Generator helpers (one yield == one editor frame; capture_scene() is called every tick by the Runner)
# ---------------------------------------------------------------------------------------------------------------
def warmup(n: int = WARMUP_FRAMES, min_seconds: float = 8.0):
    t0 = time.monotonic()
    i = 0
    while i < n or time.monotonic() - t0 < min_seconds:
        if i in (30, n - 15):
            ue.AutomationLibrary.finish_loading_before_screenshot()
        i += 1
        yield


def settle():
    t0 = time.monotonic()
    f = 0
    while f < SETTLE_FRAMES or time.monotonic() - t0 < SETTLE_SECONDS:
        f += 1
        yield


def shoot(scene: Scene, name: str, view):
    loc, look, fov = view
    scene.aim(loc, look, fov)
    scene.apply_hidden()
    yield from settle()
    scene.capture.capture_scene()
    scene.export(scene.rt, name)
    step("captured " + name, variant=scene.variant)


def shoot_set(scene: Scene, prefix: str):
    views = all_views()
    if scene.set_variant("studio"):
        yield from warmup(90, 3.0)     # sky recapture back to the studio (black) sky
    for vn in STUDIO_VIEWS:
        yield from shoot(scene, f"{prefix}{vn}.png", views[vn])
    for variant, names in VARIANT_VIEWS:
        if scene.set_variant(variant):
            yield from warmup(90, 3.0)  # sky recapture
        else:
            yield from warmup(20, 0.8)
        for vn in names:
            yield from shoot(scene, f"{prefix}{vn}_{variant}.png", views[vn])
    if scene.set_variant("studio"):
        yield from warmup(90, 3.0)


def shoot_ortho(scene: Scene, prefix: str):
    """pb_face_build.take_ortho: orthographic GBuffer base colour, backdrop hidden (silhouettes)."""
    cap = scene.capture
    shots = [(prefix + "Ortho_Front.png", (0.0, 600.0, ORTHO_CAM_Z), (0.0, 0.0, ORTHO_CAM_Z)),
             (prefix + "Ortho_Side.png", (600.0, 0.0, ORTHO_CAM_Z), (0.0, 0.0, ORTHO_CAM_Z))]
    cap.set_editor_property("projection_type", ue.CameraProjectionMode.ORTHOGRAPHIC)
    cap.set_editor_property("ortho_width", ORTHO_WIDTH)
    cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_BASE_COLOR)
    cap.set_editor_property("texture_target", scene.rt_ortho)
    saved_hidden = list(scene.hidden)
    scene.hidden = saved_hidden + [scene.backdrop]
    try:
        for name, loc, look in shots:
            scene.aim(loc, look, 30.0)
            scene.apply_hidden()
            yield from settle()
            cap.capture_scene()
            scene.export(scene.rt_ortho, name)
            step("captured " + name, variant="base_ortho")
    finally:
        cap.set_editor_property("projection_type", ue.CameraProjectionMode.PERSPECTIVE)
        cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cap.set_editor_property("texture_target", scene.rt)
        scene.hidden = saved_hidden
        scene.apply_hidden()
        scene.set_variant("studio")


# ---------------------------------------------------------------------------------------------------------------
# MetaHuman helpers
# ---------------------------------------------------------------------------------------------------------------
def mhs():
    return ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)


EDITED: list = []


def scratch_dup(src: str, name: str):
    """In-memory duplicate under /Game/PlayerDefault/Scratch (never saved)."""
    dst = f"{SCRATCH}/{name}"
    assert_clean(dst)
    if ue.EditorAssetLibrary.does_asset_exist(dst):
        return ue.load_asset(dst)
    obj = ue.EditorAssetLibrary.duplicate_asset(src, dst)
    if not isinstance(obj, ue.MetaHumanCharacter):
        raise RuntimeError(f"duplicate {src} -> {dst} failed ({obj})")
    return obj


def open_edit(ch) -> None:
    ch.set_editor_property("preview_material_type", ue.MetaHumanCharacterSkinPreviewMaterial.EDITABLE)
    if not mhs().is_object_added_for_editing(ch):
        if not mhs().try_add_object_to_edit(ch):
            raise RuntimeError(f"try_add_object_to_edit failed for {ch.get_path_name()}")
    if ch not in EDITED:
        EDITED.append(ch)


def close_edit(ch) -> None:
    if mhs().is_object_added_for_editing(ch):
        mhs().remove_object_to_edit(ch)
    if ch in EDITED:
        EDITED.remove(ch)


def spawn(ch):
    actor = mhs().spawn_meta_human_actor(ch, True)
    if actor is None:
        raise RuntimeError(f"spawn_meta_human_actor returned None for {ch.get_name()}")
    mhs().assemble_for_preview(ch)
    return actor


def release_actor(scene: Scene, actor, ch=None) -> None:
    """Destroy a spawned editor actor (hidden actors still cast shadows into captures) and stop editing."""
    if actor is not None:
        try:
            scene.actors.destroy_actor(actor)
        except Exception as exc:  # noqa: BLE001
            warn(f"destroy_actor: {exc!r}")
    if ch is not None:
        close_edit(ch)


def components(actor) -> dict:
    return {c.get_name(): c for c in actor.get_components_by_class(ue.ActorComponent)}


def find_component(actor, name: str):
    for comp in actor.get_components_by_class(ue.SkeletalMeshComponent):
        if comp.get_name() == name:
            return comp
    return None


def coeffs(ch) -> list:
    return [float(x) for x in unwrap(mhs().get_face_model_coefficients(ch))]


def landmarks(ch) -> list:
    return [v3(v) for v in unwrap(mhs().get_face_landmarks(ch))]


def eval_settings(ch) -> dict:
    s = ch.get_editor_property("face_evaluation_settings")
    return {k: round(float(s.get_editor_property(k)), 5) for k in ("global_delta", "high_frequency_delta", "head_scale")}


def constraints(ch) -> dict:
    res = {}
    for c in mhs().get_body_constraints(ch, False):
        res[str(c.name)] = {"value": round(float(c.target_measurement), 4),
                            "active": bool(c.get_editor_property("is_active")),
                            "min": round(float(c.min_measurement), 4), "max": round(float(c.max_measurement), 4)}
    return res


def character_settings(ch) -> dict:
    out = {}
    for prop in ("skin_settings", "eyes_settings", "makeup_settings", "head_model_settings",
                 "face_evaluation_settings", "preview_material_type", "has_high_resolution_textures",
                 "fixed_body_type", "template_type"):
        try:
            out[prop] = struct_dict(ch.get_editor_property(prop))
        except Exception as exc:  # noqa: BLE001
            out[prop] = "ERR " + repr(exc)[:120]
    return out


def key_name(key) -> str:
    return str(ue.MetaHumanPaletteKeyBlueprintLibrary.to_asset_name_string(key))


def selections(col) -> dict:
    """slot -> (key string, key object) of a collection's default instance."""
    out = {}
    inst = col.get_editor_property("default_instance")
    for data in inst.get_slot_selection_data():
        sel = data.get_editor_property("selection")
        key = sel.get_editor_property("selected_item")
        out[str(sel.get_editor_property("slot_name"))] = (key_name(key), key)
    return out


def collection_inventory(col) -> dict:
    lib = ue.MetaHumanCollectionBlueprintLibrary
    items = []
    try:
        for key in lib.get_all_item_keys(col):
            row = {"key": key_name(key)}
            try:
                row["slot"] = str(lib.get_item_slot_name(col, key))
                row["display"] = str(lib.get_item_display_name(col, key))
            except Exception:  # noqa: BLE001
                pass
            items.append(row)
    except Exception as exc:  # noqa: BLE001
        items = "ERR " + repr(exc)[:200]
    return {"items": items, "selections": {k: v[0] for k, v in selections(col).items()}}


def instance_params(col, key) -> dict:
    inst = col.get_editor_property("default_instance")
    out = {}
    for p in inst.get_instance_parameters(item_path=ue.MetaHumanPaletteItemPath(item_key=key)):
        t = enum_s(p.get_editor_property("type"))
        try:
            if t == "FLOAT":
                v = round(float(p.get_float()), 4)
            elif t == "BOOL":
                v = bool(p.get_bool())
            elif t == "COLOR":
                v = struct_dict(p.get_color())
            else:
                v = None
        except Exception as exc:  # noqa: BLE001
            v = "ERR " + repr(exc)[:60]
        out[str(p.get_editor_property("name"))] = v
    return out


def set_groom_param(col, key, name: str, value: float) -> bool:
    """Epic's example_add_grooms.py: instance parameter objects write through to the collection's default instance."""
    inst = col.get_editor_property("default_instance")
    for p in inst.get_instance_parameters(item_path=ue.MetaHumanPaletteItemPath(item_key=key)):
        if str(p.get_editor_property("name")) == name:
            p.set_float(float(value))
            return True
    return False


def groom_melanin_ok(params: dict) -> dict:
    out = {}
    for slot in ("Hair", "Eyebrows", "Eyelashes"):
        v = params.get(slot, {}).get("Melanin") if isinstance(params, dict) else None
        out[slot] = isinstance(v, float) and abs(v - GROOM_MELANIN) < 1e-3
    return out


def add_to_internal(ch, slot: str, wi_path: str) -> str:
    """Epic's example_add_grooms.py pattern: add + select on the INTERNAL collection before the character is opened
    for editing (the preview collection is duplicated from it on open). Hair must be the first hair groom of the
    session (pd_diagnose: later hair grooms bind but do not render)."""
    wi = ue.load_asset(wi_path)
    if wi is None:
        raise RuntimeError(f"wardrobe item {wi_path} not found")
    ic = ch.get_editor_property("internal_collection")
    key = ic.try_add_item_from_wardrobe_item(slot, wi)
    if key is None:
        raise RuntimeError(f"try_add_item_from_wardrobe_item({slot}, {wi_path}) failed")
    sel = ue.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=key)
    if not ic.get_editor_property("default_instance").try_add_slot_selection(sel):
        raise RuntimeError(f"try_add_slot_selection({slot}) failed")
    return key_name(key)


def groom_state(actor) -> list:
    rows = []
    for c in actor.get_components_by_class(ue.GroomComponent):
        row = {"name": c.get_name(), "groom": pth(c.get_editor_property("groom_asset")),
               "binding": pth(c.get_editor_property("binding_asset")), "visible": bool(c.is_visible())}
        try:
            o, e, _r = unwrap(ue.SystemLibrary.get_component_bounds(c))
            row["bounds_origin"] = struct_dict(o)
            row["bounds_extent"] = struct_dict(e)
        except Exception as exc:  # noqa: BLE001
            row["bounds_error"] = repr(exc)[:100]
        rows.append(row)
    return rows


def mid_get(mid, kind: str, name: str):
    for attr in (f"get_{kind}_parameter_value", f"k2_get_{kind}_parameter_value"):
        fn = getattr(mid, attr, None)
        if fn is not None:
            return fn(name)
    raise AttributeError(f"no {kind} getter on {mid}")


def eye_mid_params(actor) -> dict:
    face = find_component(actor, "Face")
    out = {}
    if face is None:
        return out
    slots = [str(s) for s in face.get_material_slot_names()]
    for i, slot in enumerate(slots):
        if not slot.startswith("eyeLeft") and not slot.startswith("eyeRight"):
            continue
        m = face.get_material(i)
        vals = {}
        for n in ("Iris Primary Color Hue", "Iris Primary Color Value", "Iris Secondary Color Hue",
                  "Iris Secondary Color Value", "Iris Color Blend", "Iris Global Saturation"):
            try:
                vals[n] = round(float(mid_get(m, "scalar", n)), 4)
            except Exception as exc:  # noqa: BLE001
                vals[n] = "ERR " + repr(exc)[:60]
        out[slot] = vals
    return out


def bone_positions(actor) -> dict:
    """World positions of EVERY bone of the Body component (A-pose preview actor at the origin)."""
    body = find_component(actor, "Body")
    res = {}
    if body is None:
        return res
    try:
        n = body.get_num_bones()
        names = [str(body.get_bone_name(i)) for i in range(n)]
    except Exception:  # noqa: BLE001
        names = MH_BONES
    for name in names:
        if body.does_socket_exist(name):
            res[name] = v3(body.get_socket_location(name))
    return res


def dump_mesh(component, stem: str) -> dict:
    dm = ue.new_object(ue.DynamicMesh)
    opts = ue.GeometryScriptCopyMeshFromComponentOptions()
    opts.set_editor_property("want_normals", False)
    opts.set_editor_property("want_tangents", False)
    ue.GeometryScript_SceneUtils.copy_mesh_from_component(component, dm, opts, True)
    pos = ue.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
    pos_list = next(x for x in (pos if isinstance(pos, tuple) else (pos,)) if isinstance(x, ue.GeometryScriptVectorList))
    gaps = [x for x in (pos if isinstance(pos, tuple) else ()) if isinstance(x, bool)]
    if gaps and gaps[0]:
        raise RuntimeError(f"{component.get_name()}: dynamic mesh has vertex-ID gaps")
    tri = ue.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
    tri_list = next(x for x in (tri if isinstance(tri, tuple) else (tri,)) if isinstance(x, ue.GeometryScriptTriangleList))
    verts = ue.GeometryScript_List.convert_vector_list_to_array(pos_list)
    tris = ue.GeometryScript_List.convert_triangle_list_to_array(tri_list)
    DUMPS.mkdir(parents=True, exist_ok=True)
    with open(DUMPS / f"{stem}.obj", "w", encoding="utf-8") as fh:
        fh.write("# UE world space (GeometryScript CPU copy), cm, Z up, character faces +Y\n")
        for v in verts:
            fh.write(f"v {v.x:.4f} {v.y:.4f} {v.z:.4f}\n")
        for t in tris:
            fh.write(f"f {int(t.x) + 1} {int(t.y) + 1} {int(t.z) + 1}\n")
    return {"verts": len(verts), "tris": len(tris), "obj": str(DUMPS / f"{stem}.obj")}


def save_asset(asset) -> None:
    path = asset.get_path_name()
    if not path.startswith(PD_PATH + "."):
        raise RuntimeError(f"refusing to save {path}: only {PD_PATH} may be saved by this script")
    if not ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {path}")


def max_abs_diff(a, b):
    if len(a) != len(b):
        return f"len mismatch {len(a)} vs {len(b)}"
    return max((abs(x - y) for x, y in zip(a, b)), default=0.0)


def facec_reference() -> dict:
    rep = json.loads(FACE_BUILD_REPORT.read_text(encoding="utf-8"))["build"]
    c = rep["candidates"]["MH_PlayerBase_FaceC"]
    return {"coeffs": c["coeffs"], "constraints": c["constraints"], "eval": c["eval"], "landmarks": c["landmarks"],
            "recipe": c["recipe"], "ref_constraints": rep["reference"]["constraints"],
            "ref_bones": rep["reference"]["measure"]["bones"], "facec_bones": c["measure"]["bones"]}


def identity_readback(ch) -> dict:
    """The identity-relevant settings of a character, as stored on the asset."""
    s = ch.get_editor_property("skin_settings")
    sp = s.get_editor_property("skin")
    fr = s.get_editor_property("freckles")
    eyes = ch.get_editor_property("eyes_settings")
    el = ch.get_editor_property("head_model_settings").get_editor_property("eyelashes")
    mk = ch.get_editor_property("makeup_settings")
    iris = {}
    for side in ("eye_left", "eye_right"):
        ir = eyes.get_editor_property(side).get_editor_property("iris")
        iris[side] = {"pattern": enum_s(ir.get_editor_property("pattern")),
                      "primary_u": round(float(ir.get_editor_property("primary_color_u")), 4),
                      "primary_v": round(float(ir.get_editor_property("primary_color_v")), 4),
                      "secondary_u": round(float(ir.get_editor_property("secondary_color_u")), 4),
                      "secondary_v": round(float(ir.get_editor_property("secondary_color_v")), 4)}
    return {"face_texture_index": int(sp.get_editor_property("face_texture_index")),
            "body_texture_index": int(sp.get_editor_property("body_texture_index")),
            "u": round(float(sp.get_editor_property("u")), 4), "v": round(float(sp.get_editor_property("v")), 4),
            "roughness": round(float(sp.get_editor_property("roughness")), 4),
            "show_top_underwear": bool(sp.get_editor_property("show_top_underwear")),
            "freckles_mask": enum_s(fr.get_editor_property("mask")),
            "iris": iris,
            "eyelashes_type": enum_s(el.get_editor_property("type")),
            "eyelashes_enable_grooms": bool(el.get_editor_property("enable_grooms")),
            "eyelashes_card_melanin": round(float(el.get_editor_property("melanin")), 4),
            "makeup_types": {k: enum_s(mk.get_editor_property(k).get_editor_property("type"))
                             for k in ("blush", "eyes", "lips")},
            "foundation": bool(mk.get_editor_property("foundation").get_editor_property("apply_foundation"))}


def identity_ok(r: dict, sel: dict) -> dict:
    want_sel = {"Hair": "WI_Hair_S_BrushCut", "Eyebrows": "WI_Eyebrows_M_SlightArch", "Eyelashes": "WI_Eyelashes_S_Fine"}
    res = {
        "face_texture_index": r["face_texture_index"] == FACE_TEXTURE_INDEX,
        "tone_neutral": abs(r["u"] - 0.5) < 1e-3 and abs(r["v"] - 0.5) < 1e-3,
        "freckles_none": r["freckles_mask"] == "NONE",
        "underwear_top_on": r["show_top_underwear"] is True,
        "iris_both_IRIS006": all(r["iris"][s]["pattern"] == "IRIS006" for s in ("eye_left", "eye_right")),
        "iris_both_dark": all(abs(r["iris"][s]["primary_v"] - 0.0755) < 2e-3 for s in ("eye_left", "eye_right")),
        "eyelashes_short_fine": r["eyelashes_type"] == "SHORT_FINE",
        "eyelash_card_melanin": abs(r["eyelashes_card_melanin"] - LASH_CARD_MELANIN) < 1e-3,
        "makeup_none": all(v == "NONE" for v in r["makeup_types"].values()) and not r["foundation"],
    }
    for slot, want in want_sel.items():
        got = sel.get(slot, ("", None))[0] if isinstance(sel.get(slot), tuple) else sel.get(slot, "")
        res[f"slot_{slot}"] = str(got).startswith(want)
    for slot in EMPTY_SLOTS:
        got = sel.get(slot)
        got = got[0] if isinstance(got, tuple) else got
        res[f"slot_{slot}_empty"] = (got is None) or got in ("", "None", "none")
    return res


# ---------------------------------------------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------------------------------------------
def build_job(scene: Scene):
    ref = facec_reference()
    res = REPORT.setdefault("build", {"identity_recipe": IDENTITY})
    assert_clean(PD_PATH)
    if ue.EditorAssetLibrary.does_asset_exist(PD_PATH):
        # only ever an earlier attempt of THIS script (MH_PlayerDefault is locked by claude and made only here)
        step(f"deleting earlier {PD_PATH} (made by an earlier attempt of this script)")
        if not ue.EditorAssetLibrary.delete_asset(PD_PATH):
            raise RuntimeError(f"could not delete old {PD_PATH}")
    ch = ue.EditorAssetLibrary.duplicate_asset(FACEC_PATH, PD_PATH)
    if not isinstance(ch, ue.MetaHumanCharacter):
        raise RuntimeError(f"duplicate_asset({FACEC_PATH}, {PD_PATH}) -> {ch}")
    step("MH_PlayerDefault duplicated from FaceC")
    res["settings_at_duplicate"] = character_settings(ch)
    res["internal_collection_at_duplicate"] = collection_inventory(ch.get_editor_property("internal_collection"))

    # grooms on the INTERNAL collection before editing; hair first
    res["grooms_added"] = {"Hair": add_to_internal(ch, "Hair", HAIR_WI),
                           "Eyebrows": add_to_internal(ch, "Eyebrows", BROWS_WI)}
    step("hair + brows added to the internal collection", **res["grooms_added"])
    open_edit(ch)
    c0 = coeffs(ch)
    res["coeffs_at_open_vs_facec_build_maxdiff"] = max_abs_diff(c0, ref["coeffs"])
    res["constraints_at_open"] = constraints(ch)
    yield

    # skin: texture variant 36, neutral tone, no freckles, painted top underwear kept on
    s = ch.get_editor_property("skin_settings")
    sp = s.get_editor_property("skin")
    sp.set_editor_property("face_texture_index", FACE_TEXTURE_INDEX)
    sp.set_editor_property("u", 0.5)
    sp.set_editor_property("v", 0.5)
    sp.set_editor_property("show_top_underwear", True)
    s.set_editor_property("skin", sp)
    fr = s.get_editor_property("freckles")
    fr.set_editor_property("mask", ue.MetaHumanCharacterFrecklesMask.NONE)
    s.set_editor_property("freckles", fr)
    s.set_editor_property("enable_texture_overrides", False)
    t0 = time.monotonic()
    mhs().commit_skin_settings(ch, s)
    step("skin committed", seconds=round(time.monotonic() - t0, 2))
    yield from warmup(30, 1.0)

    # eyes: Kelvin preset's eyes (IRIS006 dark brown), ONE commit then settle
    eyes = ue.load_asset(EYES_PRESET).get_editor_property("eyes_settings")
    mhs().commit_eyes_settings(ch, eyes)
    step("eyes committed (Kelvin preset eyes_settings)")
    yield from warmup(60, 2.5)

    # makeup: everything off
    mhs().commit_makeup_settings(ch, ue.MetaHumanCharacterMakeupSettings())
    step("makeup committed (defaults = none)")
    yield

    # eyelashes: head-model type SHORT_FINE (+ auto-selected groom WI_Eyelashes_S_Fine)
    hm = ch.get_editor_property("head_model_settings")
    el = hm.get_editor_property("eyelashes")
    el.set_editor_property("type", ue.MetaHumanCharacterEyelashesType.SHORT_FINE)
    el.set_editor_property("enable_grooms", True)
    el.set_editor_property("melanin", LASH_CARD_MELANIN)
    hm.set_editor_property("eyelashes", el)
    mhs().commit_head_model_settings(ch, hm)
    step("head model eyelashes committed (SHORT_FINE)")
    yield from warmup(30, 1.0)

    # make sure the eyelash groom is selected and every other slot is empty
    col = mhs().get_preview_collection(ch)
    sel = selections(col)
    if not sel.get("Eyelashes", ("", None))[0].startswith("WI_Eyelashes_S_Fine"):
        warn(f"eyelash groom not auto-selected ({sel.get('Eyelashes')}); selecting WI_Eyelashes_S_Fine explicitly")
        key = col.try_add_item_from_wardrobe_item("Eyelashes", ue.load_asset(LASHES_WI))
        col.get_editor_property("default_instance").set_single_slot_selection("Eyelashes", key)
    for slot in EMPTY_SLOTS:
        got = sel.get(slot)
        if got is not None and got[0] not in ("", "None"):
            warn(f"slot {slot} had {got[0]}: clearing")
            col.get_editor_property("default_instance").set_single_slot_selection(slot, ue.MetaHumanPaletteItemKey())
    mhs().on_edit_preview_collection(ch)

    actor = spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup(240, 12.0)
    # groom colour: Melanin instance parameter on hair, brows and lashes (preview collection -> internal collection)
    col = mhs().get_preview_collection(ch)
    sel_prev = selections(col)
    res["groom_params_before_set"] = {slot: instance_params(col, k[1]) for slot, k in sel_prev.items()
                                      if slot in ("Hair", "Eyebrows", "Eyelashes")}
    res["groom_melanin_set"] = {slot: set_groom_param(col, sel_prev[slot][1], "Melanin", GROOM_MELANIN)
                                for slot in ("Hair", "Eyebrows", "Eyelashes") if slot in sel_prev}
    mhs().on_edit_preview_collection(ch)
    mhs().assemble_for_preview(ch)
    step("groom Melanin set", **res["groom_melanin_set"])
    yield from warmup(150, 8.0)
    col = mhs().get_preview_collection(ch)
    sel_prev = selections(col)
    sel_int = selections(ch.get_editor_property("internal_collection"))
    try:
        ic = ch.get_editor_property("internal_collection")
        res["groom_params_internal"] = {slot: instance_params(ic, k[1]) for slot, k in sel_int.items()
                                        if slot in ("Hair", "Eyebrows", "Eyelashes")}
    except Exception as exc:  # noqa: BLE001
        res["groom_params_internal"] = "ERR " + repr(exc)[:200]
    res["preview_collection"] = collection_inventory(col)
    res["internal_collection"] = collection_inventory(ch.get_editor_property("internal_collection"))
    res["groom_params"] = {slot: instance_params(col, k[1]) for slot, k in sel_prev.items()
                           if slot in ("Hair", "Eyebrows", "Eyelashes")}
    res["grooms"] = groom_state(actor)
    res["eye_mids"] = eye_mid_params(actor)
    rb = identity_readback(ch)
    res["identity_readback"] = rb
    c1 = coeffs(ch)
    res["coeffs_after_identity_vs_facec_build_maxdiff"] = max_abs_diff(c1, ref["coeffs"])
    res["constraints_after"] = constraints(ch)
    res["eval_settings"] = eval_settings(ch)
    res["settings_before_save"] = character_settings(ch)
    oks = identity_ok(rb, sel_int)
    check("build_identity", all(oks.values()), detail=oks)
    gm = groom_melanin_ok(res["groom_params"])
    check("build_groom_melanin_preview", all(gm.values()), detail=gm)
    if isinstance(res.get("groom_params_internal"), dict):
        gmi = groom_melanin_ok(res["groom_params_internal"])
        check("build_groom_melanin_internal", all(gmi.values()), detail=gmi)
    check("build_face_coeffs_equal_facec", res["coeffs_after_identity_vs_facec_build_maxdiff"] == 0.0,
          maxdiff=res["coeffs_after_identity_vs_facec_build_maxdiff"])
    same_c = {k: v["value"] for k, v in res["constraints_after"].items()} == \
        {k: round(float(v), 4) for k, v in ref["constraints"].items()} or \
        max(abs(res["constraints_after"][k]["value"] - float(v)) for k, v in ref["constraints"].items()) < 2e-3
    check("build_constraints_equal_facec", same_c)
    write_report()

    save_asset(ch)
    res["saved"] = True
    res["saved_uasset"] = str(CONTENT / f"{PD_NAME}.uasset")
    step("MH_PlayerDefault SAVED")
    # recipe file (the settings as applied + read back)
    recipe = {"asset": PD_PATH, "built_utc": _now(), "build_script": "Scripts/MetaHuman/pd_player_default.py (PD_MODE=build)",
              "identity": IDENTITY, "readback_at_build": rb,
              "collection_selections_at_build": {k: v[0] for k, v in sel_int.items()},
              "groom_instance_params_at_build": res["groom_params"],
              "face_recipe": {"file": str(FACE_RECIPES), "candidate": "MH_PlayerBase_FaceC", "recipe": ref["recipe"],
                              "coeffs_source": str(FACE_BUILD_REPORT),
                              "coeffs_maxdiff_vs_facec_build": res["coeffs_after_identity_vs_facec_build_maxdiff"]},
              "not_called": ["request_auto_rigging", "request_texture_sources", "build_meta_human"]}
    RECIPE_PATH.write_text(json.dumps(recipe, indent=1, default=str), encoding="utf-8")
    step("recipe written", path=str(RECIPE_PATH))

    # build-session captures (reference only; the verdict uses the fresh-session verify captures)
    views = all_views()
    for vn in ("Face_Front", "Face_ThreeQuarter", "Body_Front", "Eyes", "Shoulders_Front"):
        yield from shoot(scene, f"build_{vn}.png", views[vn])
    release_actor(scene, actor, ch)
    step("build done")


def verify_job(scene: Scene):
    ref = facec_reference()
    res = REPORT.setdefault("verify", {})
    # ---------------- A) MH_PlayerDefault as saved ----------------
    if not ue.EditorAssetLibrary.does_asset_exist(PD_PATH):
        raise RuntimeError(f"{PD_PATH} does not exist")
    pd = ue.load_asset(PD_PATH)
    if not isinstance(pd, ue.MetaHumanCharacter):
        raise RuntimeError(f"{PD_PATH} did not load as a MetaHumanCharacter")
    res["disk_settings"] = character_settings(pd)
    res["disk_internal_collection"] = collection_inventory(pd.get_editor_property("internal_collection"))
    rb = identity_readback(pd)
    res["disk_identity"] = rb
    oks = identity_ok(rb, selections(pd.get_editor_property("internal_collection")))
    check("disk_identity", all(oks.values()), detail=oks)
    open_edit(pd)
    c = coeffs(pd)
    res["coeffs_len"] = len(c)
    res["coeffs_maxdiff_vs_facec_build"] = max_abs_diff(c, ref["coeffs"])
    check("face_coeffs_equal_facec_build", res["coeffs_maxdiff_vs_facec_build"] == 0.0,
          maxdiff=res["coeffs_maxdiff_vs_facec_build"])
    res["eval_settings"] = eval_settings(pd)
    check("face_eval_settings_equal_facec", res["eval_settings"] == ref["eval"], got=res["eval_settings"], want=ref["eval"])
    lm = landmarks(pd)
    res["landmarks_maxdiff_vs_facec_build"] = max(max(abs(a - b) for a, b in zip(p, q)) for p, q in zip(lm, ref["landmarks"]))
    res["constraints"] = constraints(pd)
    dcon = max(abs(res["constraints"][k]["value"] - float(v)) for k, v in ref["ref_constraints"].items())
    res["constraints_maxdiff_vs_playerbase_build_ref"] = dcon
    check("body_constraints_equal_playerbase", dcon < 2e-3, maxdiff=dcon)
    res["rigging_state"] = str(mhs().get_rigging_state(pd)) if hasattr(mhs(), "get_rigging_state") else "n/a"
    res["can_build_meta_human"] = bool(mhs().can_build_meta_human(pd, False))
    write_report()

    actor = spawn(pd)
    scene.show_only(actor, [actor])
    yield from warmup(300, 15.0)
    col = mhs().get_preview_collection(pd)
    sel = selections(col)
    res["preview_collection"] = collection_inventory(col)
    res["groom_params"] = {slot: instance_params(col, k[1]) for slot, k in sel.items()
                           if slot in ("Hair", "Eyebrows", "Eyelashes")}
    res["grooms"] = groom_state(actor)
    res["eye_mids"] = eye_mid_params(actor)
    gm = groom_melanin_ok(res["groom_params"])
    check("groom_melanin_persisted", all(gm.values()), detail=gm)
    vis = {r["name"]: r["visible"] for r in res["grooms"] if r["groom"]}
    check("grooms_bound_and_visible", len(vis) >= 3 and all(vis.values()), grooms=vis)
    em = res["eye_mids"]
    check("eye_materials_match", len(em) == 2 and len({json.dumps(v, sort_keys=True) for v in em.values()}) == 1, eye_mids=em)
    res["bones"] = bone_positions(actor)
    res["dump_Body"] = dump_mesh(find_component(actor, "Body"), "PD_Body")
    res["dump_Face"] = dump_mesh(find_component(actor, "Face"), "PD_Face")
    write_report()
    yield from shoot_set(scene, "after_")
    yield from shoot_ortho(scene, "after_")
    release_actor(scene, actor, None)   # keep PD open for the state comparisons below
    yield from warmup(30, 1.0)

    # ---------------- B) FaceC (scratch duplicate, never saved) = BEFORE ----------------
    fc = scratch_dup(FACEC_PATH, "PD_Before_FaceC")
    open_edit(fc)
    res["facec_dup_coeffs_maxdiff_vs_build"] = max_abs_diff(coeffs(fc), ref["coeffs"])
    res["facec_dup_identity"] = identity_readback(fc)
    for tol in (0.0, 1e-5, 1e-3, 1e-2, 0.1):
        res.setdefault("compare_face_state_pd_vs_facec", {})[str(tol)] = bool(mhs().compare_face_state(pd, fc, tol))
        res.setdefault("compare_body_state_pd_vs_facec", {})[str(tol)] = bool(mhs().compare_body_state(pd, fc, tol))
    step("state comparisons vs FaceC", face=res["compare_face_state_pd_vs_facec"], body=res["compare_body_state_pd_vs_facec"])
    fa = spawn(fc)
    scene.show_only(fa, [fa])
    yield from warmup(240, 12.0)
    res["facec_bones"] = bone_positions(fa)
    res["facec_dump_Body"] = dump_mesh(find_component(fa, "Body"), "FaceC_Body")
    res["facec_dump_Face"] = dump_mesh(find_component(fa, "Face"), "FaceC_Face")
    res["facec_eye_mids"] = eye_mid_params(fa)
    yield from shoot_set(scene, "before_")
    yield from shoot_ortho(scene, "before_")
    release_actor(scene, fa, fc)
    yield from warmup(30, 1.0)

    # ---------------- C) MH_PlayerBase (scratch duplicate, never saved): body reference ----------------
    pb = scratch_dup(BASE_PATH, "PD_Ref_PlayerBase")
    open_edit(pb)
    res["playerbase_constraints"] = constraints(pb)
    for tol in (0.0, 1e-5, 1e-3, 1e-2, 0.1):
        res.setdefault("compare_body_state_pd_vs_playerbase", {})[str(tol)] = bool(mhs().compare_body_state(pd, pb, tol))
    step("body state comparison vs MH_PlayerBase", body=res["compare_body_state_pd_vs_playerbase"])
    check("compare_body_state_pd_vs_playerbase_tol0", res["compare_body_state_pd_vs_playerbase"]["0.0"],
          detail=res["compare_body_state_pd_vs_playerbase"])
    pa = spawn(pb)
    scene.show_only(pa, [pa])
    yield from warmup(150, 8.0)
    res["playerbase_bones"] = bone_positions(pa)
    res["playerbase_dump_Body"] = dump_mesh(find_component(pa, "Body"), "PlayerBase_Body")
    bd = [max(abs(a - b) for a, b in zip(res["bones"][k], res["playerbase_bones"][k]))
          for k in res["bones"] if k in res["playerbase_bones"]]
    res["bones_compared"] = len(bd)
    res["bones_maxdiff_vs_playerbase_cm"] = max(bd) if bd else None
    check("bones_equal_playerbase", bool(bd) and len(bd) == len(res["bones"]) and max(bd) < 1e-3,
          n=len(bd), maxdiff=res["bones_maxdiff_vs_playerbase_cm"])
    yield from shoot(scene, "ref_PlayerBase_Body_Front.png", all_views()["Body_Front"])
    release_actor(scene, pa, pb)
    close_edit(pd)
    step("verify done (nothing saved)")


# ---------------------------------------------------------------------------------------------------------------
def main() -> None:
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n===== pd_player_default.py mode={MODE} attempt={ATTEMPT} {_now()} =====\n")
    assert_locks()
    if not REPORT["engine"].startswith("5.8"):
        raise RuntimeError(f"expected UE 5.8.x, got {REPORT['engine']}")
    REPORT["sha_start"] = protected_hashes()
    scene = Scene()
    step("scene ready")
    jobs = {"build": build_job, "verify": verify_job}
    if MODE not in jobs:
        raise ValueError(f"unknown PD_MODE {MODE}")
    Runner(scene, jobs[MODE](scene)).start()


class Runner:
    def __init__(self, scene: Scene, gen):
        self.scene = scene
        self.gen = gen
        self.busy = False
        self.done = False
        self.handle = None

    def start(self) -> None:
        self.handle = ue.register_slate_post_tick_callback(self.tick)
        ue.EditorPythonScripting.set_keep_python_script_alive(True)

    def tick(self, _dt: float) -> None:
        if self.busy or self.done:
            return
        self.busy = True
        try:
            if time.monotonic() - T0 > MAX_SECONDS:
                raise TimeoutError(f"run exceeded {MAX_SECONDS / 60:.0f} min")
            self.scene.capture.capture_scene()
            next(self.gen)
        except StopIteration:
            self.finish(True)
        except Exception:  # noqa: BLE001
            REPORT["error"] = traceback.format_exc()
            step("ERROR", error=REPORT["error"])
            ue.log_error(REPORT["error"])
            self.finish(False)
        finally:
            self.busy = False

    def finish(self, success: bool) -> None:
        if self.done:
            return
        self.done = True
        if self.handle is not None:
            ue.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        for ch in list(EDITED):
            try:
                close_edit(ch)
            except Exception:  # noqa: BLE001
                REPORT.setdefault("teardown_errors", []).append(traceback.format_exc())
        REPORT["sha_end"] = protected_hashes()
        REPORT["protected_assets_unchanged"] = REPORT["sha_end"] == REPORT.get("sha_start")
        REPORT["status"] = "done" if success else "failed"
        REPORT["finished_utc"] = _now()
        step("STATUS " + REPORT["status"], protected_unchanged=REPORT["protected_assets_unchanged"])
        ue.SystemLibrary.quit_editor()


try:
    main()
except Exception:  # noqa: BLE001
    REPORT["error"] = traceback.format_exc()
    try:
        step("ERROR in main", error=REPORT["error"])
    except Exception:  # noqa: BLE001
        pass
    ue.log_error(REPORT["error"])
    for _ch in list(EDITED):
        try:
            close_edit(_ch)
        except Exception:  # noqa: BLE001
            pass
    REPORT["status"] = "failed"
    write_report()
    ue.SystemLibrary.quit_editor()
