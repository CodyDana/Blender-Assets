"""pd_r2_common.py -- shared UE-side helpers for the round-2 MH_PlayerDefault fix (imported by pd_r2.py; no side
effects on import apart from reading the environment).

Copied from pd_player_default.py (round 1) so both rounds use the SAME studio light rig, backdrop, capture settings
and camera set as pb_conform.py / pb_face_design.py (before/after captures stay comparable). Additions: a
'headlight' evaluation variant (from pd_ic_verify.py) and the face-coefficient helpers of pb_face_build.py
(blend / layout / REGION_GROUPS are imported from pb_face_build.py so the FaceC recipe is re-applied bit-exactly).
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
MODE = os.environ.get("PD_MODE", "explore").strip().lower()
ATTEMPT = os.environ.get("PD_ATTEMPT", "1").strip()
CAPTURES = OUT / ("captures" if MODE in ("build", "verify") else f"r2_{MODE}_captures")
DUMPS = OUT / "mesh_dump"
REPORT_PATH = OUT / f"pd_r2_{MODE}_{ATTEMPT}.json"
STEP_LOG = OUT / "player_default_r2.log"
CONTENT = ROOT / "Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
PROTECTED = ["MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase"]
FACE_PROBE_REPORT = ROOT / "WorkFiles/MetaHuman/player_base/faces/face_probe_report_1.json"
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

sys.path.insert(0, str(ROOT / "Scripts/MetaHuman"))
import pb_face_build as PFB  # noqa: E402  (blend, layout, REGION_GROUPS; imports unreal only)

# ---- cameras / lights: identical to pb_conform.py / pb_face_design.py / pd_player_default.py ---------------------
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
HAND_CENTERS = {"xneg": (-54.65, 19.959, 102.01), "xpos": (54.6305, 19.952, 102.031)}
WARMUP_FRAMES = 150
SETTLE_FRAMES = 45
SETTLE_SECONDS = 1.5

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
    out = {n: sha256(CONTENT / f"{n}.uasset") for n in PROTECTED}
    pd = CONTENT / f"{PD_NAME}.uasset"
    out[PD_NAME] = sha256(pd) if pd.exists() else None
    return out


REPORT: dict = {"script": "Scripts/MetaHuman/pd_r2.py", "mode": MODE, "attempt": ATTEMPT,
                "engine": ue.SystemLibrary.get_engine_version(), "status": "starting", "started_utc": _now(),
                "steps": [], "captures": [], "warnings": [], "checks": {}}


def write_report() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(REPORT, indent=1, default=str), encoding="utf-8")


def step(msg: str, **extra) -> None:
    t = round(time.monotonic() - T0, 1)
    line = f"{_now()}  +{t:7.1f}s  [r2 {MODE}/{ATTEMPT}] {msg}"
    if extra:
        line += "  " + json.dumps(extra, default=str)[:3000]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    ue.log("PD_R2 " + line)
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
def set_specular(light, value: float) -> None:
    comp = light.light_component
    try:
        comp.set_specular_scale(float(value))
    except Exception:  # noqa: BLE001
        comp.set_editor_property("specular_scale", float(value))


class Scene:
    def __init__(self):
        ue.EditorLoadingAndSavingUtils.new_blank_map(False)  # untitled, never saved
        self.world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.lights = [self.spawn(ue.DirectionalLight) for _ in LIGHT_RIG]
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
        """ambient: the SAME sky light made to capture the unlit 0.18-grey backdrop all around (threshold 1000 cm <
        backdrop radius 2500 cm, lower hemisphere not forced black) = uniform grey-studio ambient."""
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
        """studio     pb_conform rig exactly (key shadows, fill + rim unshadowed, sky 1.5 = adds nothing)
        ambient    studio lights unchanged + the sky light capturing the grey backdrop (real ambient)
        bounce     studio + weak unshadowed up-light (pitch +50, yaw -90, 0.8)
        rimshadow  studio with the rim light casting shadows
        rimspec0   studio with the rim light's specular scale 0
        norim      studio without the rim light
        eval       bounce + rim casts shadows + rim specular 0.3
        headlight  one unshadowed diffuse light along the view direction (geometry-only shading), no sky
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
        key, fill, rim = self.lights
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
        if variant == "headlight":
            fill.light_component.set_intensity(0.0)
            rim.light_component.set_intensity(0.0)
            key.light_component.set_intensity(3.0)
            key.light_component.set_light_color(ue.LinearColor(1, 1, 1, 1))
            key.light_component.set_cast_shadows(False)
            set_specular(key, 0.0)
            self.sky.light_component.set_intensity(0.0)
        if variant == "base":
            self.capture.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_BASE_COLOR)
        sky_changed = self.set_sky_ambient(variant == "ambient")
        self.variant = variant
        return sky_changed

    def aim(self, location, look_at, fov_deg: float = 30.0) -> None:
        loc = ue.Vector(*location)
        rot = ue.MathLibrary.find_look_at_rotation(loc, ue.Vector(*look_at))
        self.camera.set_actor_location_and_rotation(loc, rot, False, False)
        self.capture.set_editor_property("fov_angle", float(fov_deg))
        if self.variant == "headlight":
            self.lights[0].set_actor_rotation(rot, False)

    def export(self, rt, name: str) -> str:
        CAPTURES.mkdir(parents=True, exist_ok=True)
        ue.RenderingLibrary.export_render_target(self.world, rt, str(CAPTURES), name)
        path = str(CAPTURES / name)
        REPORT["captures"].append(path)
        return path


def orbit(target, dist, az_deg, el_deg):
    """Camera position around target: az 0 = in front (+Y), az>0 towards +X (character's left), el>0 above."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return (target[0] + dist * math.cos(el) * math.sin(az),
            target[1] + dist * math.cos(el) * math.cos(az),
            target[2] + dist * math.sin(el))


def all_views():
    """Identical to pd_player_default.all_views (round 1) plus JawRamus (side view of the jaw angle/ramus)."""
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
    ear_r = (fx - 7.9, fy - 1.5, fz - 1.2)
    v["JawClose"] = (orbit(jaw_l, 32.0, 40, -8), jaw_l, 22.0)
    v["JawLow"] = (orbit(jaw, 60.0, 35, -28), jaw, 30.0)
    v["JawRamus"] = (orbit((fx + 5.5, fy - 1.0, fz - 7.5), 36.0, 70, -3), (fx + 5.5, fy - 1.0, fz - 7.5), 22.0)
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
    v["Head_Back_Far"] = (orbit(head, 250.0, 180, 12), head, 30.0)   # third-person-ish distance from behind
    return v


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


def switch(scene: Scene, variant: str):
    if scene.set_variant(variant):
        yield from warmup(90, 3.0)   # sky recapture
    else:
        yield from warmup(20, 0.8)


def shoot_ortho(scene: Scene, prefix: str):
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
    if actor is not None:
        try:
            scene.actors.destroy_actor(actor)
        except Exception as exc:  # noqa: BLE001
            warn(f"destroy_actor: {exc!r}")
    if ch is not None:
        close_edit(ch)


def find_component(actor, name: str):
    for comp in actor.get_components_by_class(ue.SkeletalMeshComponent):
        if comp.get_name() == name:
            return comp
    return None


def coeffs(ch) -> list:
    return [float(x) for x in unwrap(mhs().get_face_model_coefficients(ch))]


def set_coeffs(ch, values) -> None:
    arr = ue.Array(float)
    arr.extend([float(x) for x in values])
    mhs().set_face_model_coefficients(ch, arr)


def landmarks(ch) -> list:
    return [v3(v) for v in unwrap(mhs().get_face_landmarks(ch))]


def translate_landmarks(ch, moves) -> list:
    """moves = [{"idx": [...], "d": [dx,dy,dz]} or {"idx": [i], "d_per": [[dx,dy,dz], ...]}]; UE cm."""
    idx = ue.Array(int)
    deltas = ue.Array(ue.Vector)
    flat = []
    for mv in moves:
        per = mv.get("d_per")
        for k, i in enumerate(mv["idx"]):
            d = per[k] if per else mv["d"]
            idx.append(int(i))
            deltas.append(ue.Vector(float(d[0]), float(d[1]), float(d[2])))
            flat.append([int(i)] + [float(x) for x in d])
    if flat:
        mhs().translate_face_landmarks(ch, idx, deltas)
    return flat


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
    inst = col.get_editor_property("default_instance")
    for p in inst.get_instance_parameters(item_path=ue.MetaHumanPaletteItemPath(item_key=key)):
        if str(p.get_editor_property("name")) == name:
            p.set_float(float(value))
            return True
    return False


def add_to_internal(ch, slot: str, wi_path: str) -> str:
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
    body = find_component(actor, "Body")
    res = {}
    if body is None:
        return res
    n = body.get_num_bones()
    for i in range(n):
        name = str(body.get_bone_name(i))
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


def max_abs_diff(a, b):
    if len(a) != len(b):
        return f"len mismatch {len(a)} vs {len(b)}"
    return max((abs(x - y) for x, y in zip(a, b)), default=0.0)


def offline_coeff_data() -> dict:
    """Base (MH_PlayerBase) + preset coefficients (face_probe_report_1) and FaceC's recipe/coefficients
    (face_build_report_2 / face_recipes_v2)."""
    probe = json.loads(FACE_PROBE_REPORT.read_text(encoding="utf-8"))["probe"]
    build = json.loads(FACE_BUILD_REPORT.read_text(encoding="utf-8"))["build"]
    fc = build["candidates"]["MH_PlayerBase_FaceC"]
    recipes = json.loads(FACE_RECIPES.read_text(encoding="utf-8"))
    return {"base": probe["base"]["coeffs"], "presets": {k: v["coeffs"] for k, v in probe["presets"].items()},
            "facec_coeffs": fc["coeffs"], "facec_after_blend": fc["coeffs_after_blend"],
            "facec_landmarks": fc["landmarks"], "facec_eval": fc["eval"], "facec_constraints": fc["constraints"],
            "facec_recipe": recipes["candidates"]["MH_PlayerBase_FaceC"], "blend_start": int(recipes.get("blend_start", 1)),
            "ref_constraints": build["reference"]["constraints"], "ref_landmarks": build["reference"]["landmarks"]}


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
        prot_start = {k: v for k, v in (REPORT.get("sha_start") or {}).items() if k in PROTECTED}
        prot_end = {k: v for k, v in REPORT["sha_end"].items() if k in PROTECTED}
        REPORT["protected_assets_unchanged"] = prot_start == prot_end
        REPORT["status"] = "done" if success else "failed"
        REPORT["finished_utc"] = _now()
        step("STATUS " + REPORT["status"], protected_unchanged=REPORT["protected_assets_unchanged"])
        ue.SystemLibrary.quit_editor()
