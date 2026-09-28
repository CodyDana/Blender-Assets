"""pd_diagnose.py -- live isolation tests for the MH_PlayerDefault cleanup (UE 5.8.3, MetaHumanCharacter).

Runs INSIDE UnrealEditor on Exports/CharacterLab/Unreal/CharacterLab.uproject; launch with
Scripts/MetaHuman/pd_run_diagnose.ps1 (one editor at a time, RAM preflight, SHA-256 of the protected assets
before/after, waits for exit).

SAVES NOTHING in the project. Every character used here is an in-memory duplicate under /Game/PlayerDefault/Scratch
(never saved): MH_PlayerBase_FaceC and MH_MaleBase (Kelvin) are only read by duplicate_asset. Never signs in; never
calls request_auto_rigging / request_texture_sources / build_meta_human.

Same studio light rig, backdrop, capture settings and face cameras as pb_conform.py / pb_face_design.py, so the
'lit' captures are directly comparable with faces/captures/FaceC_Face_*.png.

PD_DIAG_MODE=defects   jaw line + ear patch isolation (lighting / base colour / world normal / hidden components /
                       material switches) on FaceC and Kelvin; material + component inventory.
PD_DIAG_MODE=wardrobe  shoulder slivers: outfit on / off / outfit without its body hidden-face map; body triangle
                       counts; the outfit's hidden-face-map textures exported.
PD_DIAG_MODE=identity  identity API: groom / preset / eye / skin / makeup inventories and quick renders
                       (short hairstyles, brows, lashes, eye colours, skin texture variants).

Outputs: WorkFiles/MetaHuman/player_default/diagnose/ (diag_<mode>_<attempt>.json, diagnose.log, captures/*.png,
mesh_dump/*.obj, textures/*.png).
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
OUT = ROOT / "WorkFiles/MetaHuman/player_default/diagnose"
CAPTURES = OUT / "captures"
DUMPS = OUT / "mesh_dump"
TEXTURES = OUT / "textures"
MODE = os.environ.get("PD_DIAG_MODE", "defects").strip().lower()
ATTEMPT = os.environ.get("PD_ATTEMPT", "1").strip()
REPORT_PATH = OUT / f"diag_{MODE}_{ATTEMPT}.json"
STEP_LOG = OUT / "diagnose.log"
CONTENT = ROOT / "Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
PROTECTED = ["MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase"]

CHAR_DIR = "/Game/Characters/MetaHumans"
FACEC_PATH = f"{CHAR_DIR}/MH_PlayerBase_FaceC"
KELVIN_PATH = f"{CHAR_DIR}/MH_MaleBase"
SCRATCH = "/Game/PlayerDefault/Scratch"
PRESET_SRC = "/MetaHumanCharacter/Optional/Presets"
GROOM_ROOT = "/MetaHumanCharacter/Optional/Grooms/Bindings"
GARMENT_WI = "/MetaHumanCharacter/Optional/Clothing/WI_DefaultGarment"
FORBIDDEN_TOKENS = ("jinmuwon", "muwon", "mu-won", "mu_won")
MAX_SECONDS = float(os.environ.get("PD_MAX_MINUTES", "45")) * 60.0

# ---- cameras / lights: identical to pb_conform.py / pb_face_design.py ----------------------------------------
LIGHT_RIG = [(-27.0, -117.0, 0.0, 4.0, (1, .95, .9), True),
             (-12.0, -58.0, 0.0, 2.0, (.9, .94, 1), False),
             (-37.0, 90.0, 0.0, 2.0, (1, 1, 1), False)]
SKY_INTENSITY = 1.5
SIMPLE_RENDER_CVARS = ["r.DynamicGlobalIlluminationMethod 0", "r.ReflectionMethod 0", "r.AmbientOcclusionLevels 0",
                       "r.DistanceFieldAO 0", "r.RayTracing.ForceAllRayTracingEffects 0", "r.AntiAliasingMethod 2"]
LUMEN_RENDER_CVARS = ["r.DynamicGlobalIlluminationMethod 1", "r.ReflectionMethod 1", "r.AmbientOcclusionLevels -1",
                      "r.DistanceFieldAO 1", "r.AntiAliasingMethod 2"]   # = pb_conform.py LUMEN_RENDER_CVARS
SOURCE_MESH = "/Game/PlayerBase/ConformInput/SM_PlayerBase_ConformInput"   # pb_conform's target mesh (read only)
BASE_PATH = f"{CHAR_DIR}/MH_PlayerBase"
SHOT_W, SHOT_H = 1000, 1200
FACE_CAM_DIST = 70.0
FACEC_CENTER = (0.0, 5.959721088409424, 173.6)          # conform_report.json mh_face_center (builder's camera)
KELVIN_CENTER = (-0.009335443037974917, 7.088297037776513, 167.1292)  # face_probe_report_1.json
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
    return h.hexdigest()


def protected_hashes() -> dict:
    return {n: sha256(CONTENT / f"{n}.uasset") for n in PROTECTED}


REPORT: dict = {"script": "Scripts/MetaHuman/pd_diagnose.py", "mode": MODE, "attempt": ATTEMPT,
                "engine": ue.SystemLibrary.get_engine_version(), "status": "starting", "started_utc": _now(),
                "steps": [], "captures": [], "warnings": []}


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
    ue.log("PD_DIAG " + line)
    REPORT["steps"].append({"t_s": t, "msg": msg, **extra})
    write_report()


def warn(msg: str) -> None:
    REPORT["warnings"].append(msg)
    step("WARNING " + msg)


def assert_clean(*names: str) -> None:
    for name in names:
        low = str(name).lower()
        bad = [t for t in FORBIDDEN_TOKENS if t in low]
        if bad:
            raise ValueError(f"Refusing name {name!r}: contains {bad}")


def assert_locks() -> None:
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock  # stdlib only
    for name in PROTECTED + ["MH_PlayerDefault"]:
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
# Scene (same lights, backdrop, capture settings as pb_conform.py) + isolation variants
# ---------------------------------------------------------------------------------------------------------------
class Scene:
    def __init__(self):
        ue.EditorLoadingAndSavingUtils.new_blank_map(False)  # untitled, never saved
        self.world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.lights = []
        for _ in LIGHT_RIG:
            self.lights.append(self.spawn(ue.DirectionalLight))
        # extra light, OFF (intensity 0) except in the 'bounce' variant: from the front and below, unshadowed
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
        self.camera = self.spawn(ue.SceneCapture2D)
        self.capture = self.camera.get_component_by_class(ue.SceneCaptureComponent2D)
        self.rt = ue.RenderingLibrary.create_render_target2d(self.world, SHOT_W, SHOT_H,
                                                             ue.TextureRenderTargetFormat.RTF_RGBA8)
        self.rt.set_editor_property("target_gamma", 2.2)
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
        self.render_mode = None
        self.set_render_mode("simple")
        self.hidden = []            # actors hidden from the capture
        self.base_hide = []         # components always hidden (e.g. Kelvin's beard for jaw shots)
        self.hidden_comps = []      # extra components hidden for one variant
        self.forced_lod = []        # skinned components forced to LOD0 for one variant
        self.set_variant("lit")

    def set_render_mode(self, mode: str) -> bool:
        if mode == self.render_mode:
            return False
        for command in (SIMPLE_RENDER_CVARS if mode == "simple" else LUMEN_RENDER_CVARS):
            ue.SystemLibrary.execute_console_command(self.world, command)
        self.render_mode = mode
        return True

    def spawn(self, cls, location=(0, 0, 0)):
        return self.actors.spawn_actor_from_class(cls, ue.Vector(*location), ue.Rotator())

    def show_only(self, keep, all_actors) -> None:
        self.hidden = [a for a in all_actors if a is not None and a != keep]
        self.apply_hidden()

    def apply_hidden(self) -> None:
        self.capture.clear_hidden_components()
        for actor in self.hidden:
            self.capture.hide_actor_components(actor, True)
        for comp in list(self.base_hide) + list(self.hidden_comps):
            self.capture.hide_component(comp)

    def reset_lights(self) -> None:
        for light, (pitch, yaw, roll, intensity, color, shadows) in zip(self.lights, LIGHT_RIG):
            light.set_actor_rotation(ue.Rotator(roll=roll, pitch=pitch, yaw=yaw), False)
            light.light_component.set_intensity(intensity)
            light.light_component.set_light_color(ue.LinearColor(*color, 1))
            light.light_component.set_cast_shadows(shadows)
        self.sky.light_component.set_intensity(SKY_INTENSITY)
        if getattr(self, "bounce_light", None) is not None:
            self.bounce_light.light_component.set_intensity(0.0)

    def set_flags(self, flags: dict) -> None:
        settings = []
        for name, enabled in flags.items():
            s = ue.EngineShowFlagsSetting()
            s.set_editor_property("show_flag_name", name)
            s.set_editor_property("enabled", bool(enabled))
            settings.append(s)
        self.capture.set_editor_property("show_flag_settings", settings)

    def set_variant(self, variant: str, comps_to_hide=()) -> None:
        """lit        studio rig as in pb_conform.py (key casts shadows, sky 1.5)
        noshadow   studio rig, no light casts shadows, dynamic + contact shadows + AO show flags off
        frontbelow ONE directional light from the front and below (pitch +35, yaw -90), no shadows, sky off
        skyonly    directional lights off, sky light 1.5 only (indirect: material AO/cavity act here)
        keyonly    key light only, no shadows, sky off (direct light only)
        base       GBuffer base colour (unlit albedo)
        normal     GBuffer world normal
        lumen      studio rig with pb_conform's Lumen GI / reflections / AO console settings
        lod0:*     studio rig with the given skinned components forced to LOD0
        hide:*     studio rig with extra components hidden (comps_to_hide)"""
        self.reset_lights()
        for comp in self.forced_lod:
            comp.set_forced_lod(0)
        self.forced_lod = []
        self.set_render_mode("lumen" if variant == "lumen" else "simple")
        cap = self.capture
        cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        flags = {}
        if variant == "noshadow":
            for light in self.lights:
                light.light_component.set_cast_shadows(False)
            flags = {"DynamicShadows": False, "ContactShadows": False, "AmbientOcclusion": False}
        elif variant == "frontbelow":
            self.lights[0].set_actor_rotation(ue.Rotator(roll=0.0, pitch=35.0, yaw=-90.0), False)
            self.lights[0].light_component.set_intensity(5.0)
            self.lights[0].light_component.set_light_color(ue.LinearColor(1, 1, 1, 1))
            self.lights[0].light_component.set_cast_shadows(False)
            for light in self.lights[1:]:
                light.light_component.set_intensity(0.0)
            self.sky.light_component.set_intensity(0.0)
        elif variant == "skyonly":
            for light in self.lights:
                light.light_component.set_intensity(0.0)
        elif variant == "keyonly":
            self.lights[0].light_component.set_cast_shadows(False)
            for light in self.lights[1:]:
                light.light_component.set_intensity(0.0)
            self.sky.light_component.set_intensity(0.0)
        elif variant in ("fillonly", "rimonly"):
            keep = 1 if variant == "fillonly" else 2
            for j, light in enumerate(self.lights):
                if j != keep:
                    light.light_component.set_intensity(0.0)
            self.sky.light_component.set_intensity(0.0)
        elif variant == "bounce":
            # studio rig + a weak, unshadowed up-light standing in for the ambient / ground bounce that this
            # offscreen rig lacks (the sky light and Lumen contribute ~nothing to the MetaHuman skin here)
            self.lights[1].set_actor_rotation(ue.Rotator(roll=0.0, pitch=-12.0, yaw=-58.0), False)
            self.bounce_light.light_component.set_intensity(0.8)
            self.bounce_light.light_component.set_light_color(ue.LinearColor(1, .95, .9, 1))
        elif variant == "base":
            cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_BASE_COLOR)
        elif variant == "normal":
            cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_NORMAL)
        self.set_flags(flags)
        self.hidden_comps = list(comps_to_hide)
        self.apply_hidden()
        self.variant = variant

    def aim(self, location, look_at, fov_deg: float = 30.0) -> None:
        loc = ue.Vector(*location)
        self.camera.set_actor_location_and_rotation(
            loc, ue.MathLibrary.find_look_at_rotation(loc, ue.Vector(*look_at)), False, False)
        self.capture.set_editor_property("fov_angle", float(fov_deg))

    def export(self, name: str) -> str:
        CAPTURES.mkdir(parents=True, exist_ok=True)
        ue.RenderingLibrary.export_render_target(self.world, self.rt, str(CAPTURES), name)
        path = str(CAPTURES / name)
        REPORT["captures"].append(path)
        return path


def orbit(target, dist, az_deg, el_deg):
    """Camera position around target: az 0 = in front (+Y), az>0 towards +X (character's left), el>0 above."""
    az, el = math.radians(az_deg), math.radians(el_deg)
    return (target[0] + dist * math.cos(el) * math.sin(az),
            target[1] + dist * math.cos(el) * math.cos(az),
            target[2] + dist * math.sin(el))


def face_views(center):
    """name -> (location, look_at, fov). Front / ThreeQuarter are identical to pb_face_design.face_shots."""
    fx, fy, fz = center
    c = (fx, fy, fz)
    jaw = (fx + 2.0, fy + 1.0, fz - 10.0)
    jaw_l = (fx + 4.5, fy - 1.0, fz - 9.5)
    ear_r = (fx - 7.9, fy - 1.5, fz - 1.2)     # image-left ear in the front shot (character's right, -X)
    return {
        "Front": (orbit(c, FACE_CAM_DIST, 0, 0), c, 30.0),
        "ThreeQuarter": (orbit(c, FACE_CAM_DIST, 35, 0), c, 30.0),
        "Low": (orbit(jaw, 60.0, 35, -28), jaw, 30.0),
        "JawClose": (orbit(jaw_l, 32.0, 40, -8), jaw_l, 22.0),
        "EarR": (orbit(ear_r, 32.0, 0, 0), ear_r, 20.0),
        "EarRSide": (orbit(ear_r, 32.0, -80, 5), ear_r, 20.0),
    }


def body_views():
    sh = (0.0, 0.0, 150.0)
    return {
        "Body_Front": ((0.0, 380.0, 93.0), (0.0, 0.0, 93.0), 30.0),
        "Shoulders_Front": ((0.0, 115.0, 156.0), sh, 26.0),
        "Shoulders_High": (orbit(sh, 110.0, 0, 42), sh, 26.0),
        "ShoulderL_TQ": (orbit((15.0, 0.0, 150.0), 75.0, 40, 12), (15.0, 0.0, 150.0), 26.0),
        "ShoulderR_TQ": (orbit((-15.0, 0.0, 150.0), 75.0, -40, 12), (-15.0, 0.0, 150.0), 26.0),
        "Shoulders_Back": ((0.0, -115.0, 156.0), sh, 26.0),
    }


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
    scene.export(name)
    step("captured " + name, variant=scene.variant)


def shoot_matrix(scene: Scene, prefix: str, views: dict, view_names, variants, comps=None):
    """Every (variant, view) pair; 'hide:<key>' hides comps[<key>], 'lod0:<key>' forces comps[<key>] to LOD0."""
    comps = comps or {}
    for variant in variants:
        if variant.startswith("hide:"):
            scene.set_variant("lit", comps.get(variant[5:], []))
        elif variant.startswith("lod0:"):
            scene.set_variant("lit")
            scene.forced_lod = list(comps.get(variant[5:], []))
            for comp in scene.forced_lod:
                comp.set_forced_lod(1)
            yield from warmup(30, 1.0)
        else:
            switched = scene.render_mode != ("lumen" if variant == "lumen" else "simple")
            scene.set_variant(variant)
            if switched:
                yield from warmup(120, 6.0)
        for vn in view_names:
            yield from shoot(scene, f"{prefix}{vn}_{variant.replace(':', '-')}.png", views[vn])
    if scene.render_mode != "simple" or scene.forced_lod:
        scene.set_variant("lit")
        yield from warmup(60, 3.0)
    scene.set_variant("lit")


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
    if obj is None:
        raise RuntimeError(f"duplicate {src} -> {dst} failed")
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


def components(actor) -> dict:
    out = {}
    for comp in actor.get_components_by_class(ue.ActorComponent):
        out[comp.get_name()] = comp
    return out


def comp_inventory(actor) -> list:
    rows = []
    for name, comp in components(actor).items():
        row = {"name": name, "class": comp.get_class().get_name()}
        if isinstance(comp, ue.PrimitiveComponent):
            row["visible"] = bool(comp.is_visible())
        if isinstance(comp, ue.SkinnedMeshComponent):
            try:
                row["asset"] = pth(comp.get_skinned_asset())
            except Exception:  # noqa: BLE001
                pass
        if isinstance(comp, ue.GroomComponent):
            try:
                row["groom"] = pth(comp.get_editor_property("groom_asset"))
                row["binding"] = pth(comp.get_editor_property("binding_asset"))
            except Exception:  # noqa: BLE001
                pass
        rows.append(row)
    return rows


def mid_get(mid, kind: str, name: str):
    """MaterialInstanceDynamic getters (Python names differ between engine versions: get_* vs k2_get_*)."""
    for attr in (f"get_{kind}_parameter_value", f"k2_get_{kind}_parameter_value"):
        fn = getattr(mid, attr, None)
        if fn is not None:
            return fn(name)
    raise AttributeError(f"no {kind} getter on {mid}")


def mat_params(m) -> dict:
    """Parameter names + values of a material interface (MID / MIC)."""
    out = {"path": pth(m), "class": m.get_class().get_name()}
    try:
        out["base"] = pth(m.get_base_material())
    except Exception:  # noqa: BLE001
        pass
    lib = ue.MaterialEditingLibrary
    for kind, getter in (("scalar", "get_scalar_parameter_names"), ("texture", "get_texture_parameter_names"),
                         ("vector", "get_vector_parameter_names"), ("switch", "get_static_switch_parameter_names")):
        try:
            names = [str(n) for n in unwrap(getattr(lib, getter)(m))]
        except Exception as exc:  # noqa: BLE001
            out[kind + "_error"] = repr(exc)
            continue
        vals = {}
        for n in names:
            try:
                if isinstance(m, ue.MaterialInstanceDynamic):
                    if kind == "scalar":
                        vals[n] = round(float(mid_get(m, "scalar", n)), 4)
                    elif kind == "texture":
                        vals[n] = pth(mid_get(m, "texture", n))
                    elif kind == "vector":
                        vals[n] = struct_dict(mid_get(m, "vector", n))
                    else:
                        vals[n] = None
                elif isinstance(m, ue.MaterialInstanceConstant):
                    if kind == "scalar":
                        vals[n] = round(float(lib.get_material_instance_scalar_parameter_value(m, n)), 4)
                    elif kind == "texture":
                        vals[n] = pth(lib.get_material_instance_texture_parameter_value(m, n))
                    elif kind == "vector":
                        vals[n] = struct_dict(lib.get_material_instance_vector_parameter_value(m, n))
                    else:
                        vals[n] = bool(lib.get_material_instance_static_switch_parameter_value(m, n))
                else:
                    vals[n] = None
            except Exception as exc:  # noqa: BLE001
                vals[n] = "ERR " + repr(exc)[:80]
        out[kind] = vals
    return out


def material_inventory(comp) -> list:
    rows = []
    try:
        slots = [str(s) for s in comp.get_material_slot_names()]
    except Exception:  # noqa: BLE001
        slots = []
    for i in range(comp.get_num_materials()):
        m = comp.get_material(i)
        row = {"index": i, "slot": slots[i] if i < len(slots) else None}
        if m is not None:
            row.update(mat_params(m))
        rows.append(row)
    return rows


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


def collection_inventory(ch) -> dict:
    """Slot selections and items of the preview collection (what the preview actor is built from)."""
    out = {}
    col = mhs().get_preview_collection(ch)
    lib = ue.MetaHumanCollectionBlueprintLibrary
    try:
        out["slot_names"] = [str(s) for s in lib.get_slot_names(col)]
    except Exception as exc:  # noqa: BLE001
        out["slot_names"] = "ERR " + repr(exc)[:120]
    items = []
    try:
        for key in lib.get_all_item_keys(col):
            row = {"key": str(ue.MetaHumanPaletteKeyBlueprintLibrary.to_asset_name_string(key))}
            try:
                row["slot"] = str(lib.get_item_slot_name(col, key))
                row["display"] = str(lib.get_item_display_name(col, key))
            except Exception:  # noqa: BLE001
                pass
            items.append(row)
    except Exception as exc:  # noqa: BLE001
        items = "ERR " + repr(exc)[:200]
    out["items"] = items
    sels = []
    inst = col.get_editor_property("default_instance")
    for data in inst.get_slot_selection_data():
        sel = data.get_editor_property("selection")
        sels.append({"slot": str(sel.get_editor_property("slot_name")),
                     "item": str(ue.MetaHumanPaletteKeyBlueprintLibrary.to_asset_name_string(
                         sel.get_editor_property("selected_item")))})
    out["selections"] = sels
    internal = ch.get_editor_property("internal_collection")
    try:
        out["internal_selections"] = [
            {"slot": str(d.get_editor_property("selection").get_editor_property("slot_name")),
             "item": str(ue.MetaHumanPaletteKeyBlueprintLibrary.to_asset_name_string(
                 d.get_editor_property("selection").get_editor_property("selected_item")))}
            for d in internal.get_editor_property("default_instance").get_slot_selection_data()]
    except Exception as exc:  # noqa: BLE001
        out["internal_selections"] = "ERR " + repr(exc)[:120]
    return out


def select_item(ch, slot: str, wardrobe_item):
    """Add a wardrobe item to the PREVIEW collection and select it for `slot` (None clears the slot)."""
    col = mhs().get_preview_collection(ch)
    inst = col.get_editor_property("default_instance")
    if wardrobe_item is None:
        inst.set_single_slot_selection(slot, ue.MetaHumanPaletteItemKey())
        key = None
    else:
        key = col.try_add_item_from_wardrobe_item(slot, wardrobe_item)
        if key is None:
            existing = ue.MetaHumanCollectionBlueprintLibrary.get_item_keys_for_wardrobe_item(col, wardrobe_item)
            key = existing[0] if existing else None
        if key is None:
            raise RuntimeError(f"could not add {pth(wardrobe_item)} to slot {slot}")
        inst.set_single_slot_selection(slot, key)
    mhs().on_edit_preview_collection(ch)
    mhs().assemble_for_preview(ch)
    return key


def instance_params(ch, key) -> dict:
    col = mhs().get_preview_collection(ch)
    inst = col.get_editor_property("default_instance")
    path = ue.MetaHumanPaletteItemPath(item_key=key)
    out = {}
    for p in inst.get_instance_parameters(item_path=path):
        t = enum_s(p.get_editor_property("type")) if hasattr(p, "get_editor_property") else "?"
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
        out[str(p.get_editor_property("name"))] = {"type": t, "value": v}
    return out


def set_instance_param(ch, key, name: str, value) -> bool:
    col = mhs().get_preview_collection(ch)
    inst = col.get_editor_property("default_instance")
    for p in inst.get_instance_parameters(item_path=ue.MetaHumanPaletteItemPath(item_key=key)):
        if str(p.get_editor_property("name")) == name:
            if isinstance(value, bool):
                p.set_bool(value)
            elif isinstance(value, (int, float)):
                p.set_float(float(value))
            else:
                p.set_color(value)
            mhs().on_edit_preview_collection(ch)
            return True
    return False


def dump_mesh(component, stem: str):
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


def export_texture(tex, stem: str) -> dict:
    """Texture metadata only. The PNG exporter hard-crashed the editor (ImageCoreUtils.cpp:110 assertion inside
    Exporter.RunAssetExportTask) on a synthesized face texture in defects attempt 2, so no pixel export here."""
    res = {"texture": pth(tex)}
    if tex is None:
        return res
    try:
        res["size"] = [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()]
        res["class"] = tex.get_class().get_name()
    except Exception:  # noqa: BLE001
        pass
    return res


def _export_texture_png_UNSAFE(tex, stem: str) -> dict:  # kept for reference; do not call (crashes the editor)
    TEXTURES.mkdir(parents=True, exist_ok=True)
    res = {"texture": pth(tex)}
    try:
        task = ue.AssetExportTask()
        task.set_editor_property("object", tex)
        task.set_editor_property("filename", str(TEXTURES / f"{stem}.png"))
        task.set_editor_property("automated", True)
        task.set_editor_property("prompt", False)
        task.set_editor_property("replace_identical", True)
        task.set_editor_property("exporter", ue.TextureExporterPNG())
        ok = ue.Exporter.run_asset_export_task(task)
        if ok and (TEXTURES / f"{stem}.png").exists():
            res["png"] = str(TEXTURES / f"{stem}.png")
            return res
        res["png_exporter"] = f"failed ({ok})"
    except Exception as exc:  # noqa: BLE001
        res["png_exporter"] = repr(exc)[:160]
    try:
        ue.RenderingLibrary.export_texture2d(ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world(),
                                             tex, str(TEXTURES), stem)
        found = [p.name for p in TEXTURES.glob(stem + "*")]
        res["export_texture2d"] = found
    except Exception as exc:  # noqa: BLE001
        res["export_texture2d"] = repr(exc)[:160]
    return res


def asset_list(package_path: str, cls) -> list:
    reg = ue.AssetRegistryHelpers.get_asset_registry()
    flt = ue.ARFilter(package_paths=[package_path], recursive_paths=True,
                      class_paths=[cls.static_class().get_class_path_name()])
    return sorted(str(a.package_name) for a in reg.get_assets(flt))


# ---------------------------------------------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------------------------------------------
def skin_mids(face_comp) -> list:
    """(index, MID) of the Face component's skin sections (materials that have a 'Cavity' or 'Use Cavity' param)."""
    out = []
    for i in range(face_comp.get_num_materials()):
        m = face_comp.get_material(i)
        if m is None:
            continue
        try:
            scal = [str(n) for n in unwrap(ue.MaterialEditingLibrary.get_scalar_parameter_names(m))]
            texn = [str(n) for n in unwrap(ue.MaterialEditingLibrary.get_texture_parameter_names(m))]
        except Exception:  # noqa: BLE001
            continue
        if "Use Cavity" in scal or any(t.startswith("Cavity") for t in texn):
            if not isinstance(m, ue.MaterialInstanceDynamic):
                m = face_comp.create_dynamic_material_instance(i, m)
            out.append((i, m, scal, texn))
    return out


def material_switch_tests(scene, prefix, actor, views, view_names):
    """Transient MID edits on the Face skin sections: cavity off, flat normal map, both. Restored afterwards."""
    face = components(actor).get("Face")
    res = {}
    mids = skin_mids(face)
    res["skin_sections"] = [i for i, *_ in mids]
    if not mids:
        warn("no skin MID with Cavity params found on Face")
        return res
    flat = ue.load_asset("/Engine/EngineMaterials/FlatNormal")
    white = ue.load_asset("/Engine/EngineResources/WhiteSquareTexture")
    saved = []
    for i, mid, scal, texn in mids:
        saved.append((mid, {n: mid_get(mid, "scalar", n) for n in scal},
                      {n: mid_get(mid, "texture", n) for n in texn}))
    tests = [("nocavity", {"Use Cavity": 0.0}, {}),
             ("flatnormal", {}, {"Normal": flat}),
             ("whitecavity", {}, {"Cavity": white}),
             ("nocav_flatnrm", {"Use Cavity": 0.0}, {"Normal": flat})]
    for label, scalars, textures in tests:
        applied = []
        for mid, s0, t0 in saved:
            for n, v in scalars.items():
                if n in s0:
                    mid.set_scalar_parameter_value(n, v)
                    applied.append(n)
            for n, tex in textures.items():
                if n in t0 and tex is not None:
                    mid.set_texture_parameter_value(n, tex)
                    applied.append(n)
        res[label] = sorted(set(applied))
        if not applied:
            warn(f"material test {label}: none of its parameters exist (VT names?)")
            continue
        yield from warmup(40, 1.5)
        scene.set_variant("lit")
        for vn in view_names:
            yield from shoot(scene, f"{prefix}{vn}_mat-{label}.png", views[vn])
        for mid, s0, t0 in saved:
            for n, v in s0.items():
                mid.set_scalar_parameter_value(n, v)
            for n, tex in t0.items():
                if tex is not None:
                    mid.set_texture_parameter_value(n, tex)
    REPORT.setdefault("material_tests", {})[prefix] = res
    write_report()


def release_actor(scene: Scene, actor, ch=None) -> None:
    """Destroy a spawned editor actor (hidden actors still cast shadows into captures) and stop editing."""
    if actor is not None:
        try:
            scene.actors.destroy_actor(actor)
        except Exception as exc:  # noqa: BLE001
            warn(f"destroy_actor: {exc!r}")
    if ch is not None:
        close_edit(ch)


def hide_sets(actor) -> dict:
    comps = components(actor)
    grooms = [c for c in comps.values() if isinstance(c, ue.GroomComponent)]
    others = [c for n, c in comps.items() if isinstance(c, ue.PrimitiveComponent)
              and n not in ("Face", "Body") and not isinstance(c, ue.GroomComponent)]
    return {"body": ([comps["Body"]] if "Body" in comps else []) + others,
            "face": [comps["Face"]] if "Face" in comps else [],
            "grooms": grooms, "others": others,
            "skel": [c for n, c in comps.items() if n in ("Face", "Body")]}


def export_face_textures(ch, label: str) -> dict:
    tex_res = {}
    try:
        texmap = ch.get_editor_property("synthesized_face_textures")
        for k, tex in texmap.items():
            kn = enum_s(k)
            if kn.upper() in ("BASECOLOR", "NORMAL", "CAVITY") or str(k) in ("0", "4", "8"):
                tex_res[kn] = export_texture(tex, f"{label}_face_{kn}")
    except Exception as exc:  # noqa: BLE001
        tex_res["error"] = repr(exc)[:200]
    step(f"{label} textures", **{k: (v.get("png") or v.get("export_texture2d") or v.get("png_exporter"))
                                   if isinstance(v, dict) else v for k, v in tex_res.items()})
    return tex_res


def open_subject(label: str, src: str, dup_name: str, res: dict):
    ch = scratch_dup(src, dup_name)
    open_edit(ch)
    res[label] = {"source": src, "scratch": ch.get_path_name(), "settings": character_settings(ch)}
    try:
        res[label]["collection"] = collection_inventory(ch)
    except Exception as exc:  # noqa: BLE001
        warn(f"{label} collection inventory: {exc!r}")
    step(f"{label} scratch duplicate opened", scratch=ch.get_path_name())
    return ch


def defects_job(scene: Scene):
    """ONE MetaHuman actor in the world at a time (run 1 showed hidden actors still cast shadows)."""
    res = REPORT.setdefault("defects", {})
    # ---------------- FaceC alone ----------------
    ch = open_subject("FaceC", FACEC_PATH, "PD_Diag_FaceC", res)
    actor = spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup()
    res["FaceC"]["components"] = comp_inventory(actor)
    comps = components(actor)
    for cname in ("Face", "Body"):
        if cname in comps:
            res["FaceC"][f"materials_{cname}"] = material_inventory(comps[cname])
    write_report()
    hide = hide_sets(actor)
    views = face_views(FACEC_CENTER)
    p = "FaceC_"
    yield from shoot_matrix(scene, p, views, ["ThreeQuarter", "Low", "JawClose"],
                            ["lit", "noshadow", "frontbelow", "skyonly", "keyonly", "base", "normal",
                             "hide:body", "lumen"], hide)
    yield from shoot_matrix(scene, p, views, ["Front"], ["lit", "base", "normal", "noshadow", "lumen"], hide)
    yield from shoot_matrix(scene, p, views, ["EarR", "EarRSide"],
                            ["lit", "noshadow", "frontbelow", "base", "normal", "lumen"], hide)
    yield from material_switch_tests(scene, p, actor, views, ["ThreeQuarter", "JawClose", "EarR"])

    # shadow-caster reproduction: an extra actor hidden from the capture still casts shadows
    sc = {}
    try:
        mesh = ue.load_asset(SOURCE_MESH)
        src_actor = scene.actors.spawn_actor_from_object(mesh, ue.Vector(0, 0, 0), ue.Rotator())
        scene.show_only(actor, [actor, src_actor])
        yield from warmup(60, 3.0)
        for vn in ("ThreeQuarter", "JawClose", "Front", "EarR"):
            yield from shoot(scene, f"{p}{vn}_withHiddenSourceMesh.png", views[vn])
        scene.actors.destroy_actor(src_actor)
        scene.show_only(actor, [actor])
        sc["source_mesh"] = SOURCE_MESH
    except Exception as exc:  # noqa: BLE001
        warn(f"source-mesh shadow test: {exc!r}")
    try:
        ref = scratch_dup(BASE_PATH, "PD_Diag_Ref")
        open_edit(ref)
        ref_actor = spawn(ref)
        scene.show_only(actor, [actor, ref_actor])
        yield from warmup(120, 6.0)
        for vn in ("ThreeQuarter", "JawClose", "Front"):
            yield from shoot(scene, f"{p}{vn}_withHiddenRefMH.png", views[vn])
        release_actor(scene, ref_actor, ref)
        scene.show_only(actor, [actor])
        sc["ref_mh"] = BASE_PATH
    except Exception as exc:  # noqa: BLE001
        warn(f"ref-MH shadow test: {exc!r}")
    res["shadow_caster_tests"] = sc
    # sky light re-captured now that the backdrop has rendered (does the rig then have any ambient?)
    try:
        scene.sky.light_component.recapture_sky()
        yield from warmup(60, 3.0)
        for variant in ("skyonly", "lit"):
            scene.set_variant(variant)
            for vn in ("ThreeQuarter", "JawClose"):
                yield from shoot(scene, f"{p}{vn}_{variant}-skyrecaptured.png", views[vn])
        scene.set_variant("lit")
    except Exception as exc:  # noqa: BLE001
        warn(f"sky recapture: {exc!r}")
    res["FaceC"]["face_textures"] = export_face_textures(ch, "FaceC")
    release_actor(scene, actor, ch)
    yield from warmup(30, 1.0)

    # ---------------- Kelvin alone (beard / hair hidden in every jaw shot) ----------------
    kch = open_subject("Kelvin", KELVIN_PATH, "PD_Diag_Kelvin", res)
    kactor = spawn(kch)
    scene.show_only(kactor, [kactor])
    yield from warmup()
    res["Kelvin"]["components"] = comp_inventory(kactor)
    kcomps = components(kactor)
    for cname in ("Face", "Body"):
        if cname in kcomps:
            res["Kelvin"][f"materials_{cname}"] = material_inventory(kcomps[cname])
    write_report()
    khide = hide_sets(kactor)
    kviews = face_views(KELVIN_CENTER)
    yield from shoot(scene, "Kelvin_Front_lit-withgrooms.png", kviews["Front"])
    scene.base_hide = khide["grooms"]
    try:
        yield from shoot_matrix(scene, "Kelvin_", kviews, ["ThreeQuarter", "Low", "JawClose"],
                                ["lit", "noshadow", "frontbelow", "keyonly", "base", "normal", "lumen"], khide)
        yield from shoot_matrix(scene, "Kelvin_", kviews, ["Front"], ["lit", "base"], khide)
        yield from shoot_matrix(scene, "Kelvin_", kviews, ["EarR", "EarRSide"], ["lit", "base", "normal"], khide)
        yield from material_switch_tests(scene, "Kelvin_", kactor, kviews, ["ThreeQuarter", "JawClose"])
    finally:
        scene.base_hide = []
    res["Kelvin"]["face_textures"] = export_face_textures(kch, "Kelvin")
    release_actor(scene, kactor, kch)
    step("defects done")


def wardrobe_job(scene: Scene):
    """Shoulder slivers. FaceC has NO wardrobe items (run 1): the grey tank top / briefs are the skin material's
    painted underwear (skin.show_top_underwear). Tests: seam (face vs body components, forced LOD0), underwear flag,
    and what an actual outfit (WI_DefaultGarment, with / without its body hidden-face map) does."""
    res = REPORT.setdefault("wardrobe", {})
    ch = scratch_dup(FACEC_PATH, "PD_Diag_FaceC_W")
    open_edit(ch)
    res["collection_start"] = collection_inventory(ch)
    res["skin_start"] = struct_dict(ch.get_editor_property("skin_settings").get_editor_property("skin"))
    actor = spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup()
    views = body_views()
    names = list(views)
    hide = hide_sets(actor)
    comps = components(actor)
    res["components_start"] = comp_inventory(actor)
    res["lods"] = {}
    for cname in ("Face", "Body"):
        comp = comps.get(cname)
        if comp is None:
            continue
        info = {}
        for attr in ("get_num_lods", "get_predicted_lod_level", "get_forced_lod"):
            try:
                info[attr] = getattr(comp, attr)()
            except Exception as exc:  # noqa: BLE001
                info[attr] = "ERR " + repr(exc)[:60]
        try:
            info["leader_pose_component"] = pth(comp.get_editor_property("leader_pose_component"))
        except Exception:  # noqa: BLE001
            pass
        res["lods"][cname] = info
    for cname in ("Face", "Body"):
        try:
            res[f"dump_{cname}"] = dump_mesh(comps[cname], f"W_start_{cname}")
        except Exception as exc:  # noqa: BLE001
            warn(f"dump {cname}: {exc!r}")
    write_report()
    yield from shoot_matrix(scene, "W_", views, names, ["lit"], hide)
    yield from shoot_matrix(scene, "W_", views, ["Shoulders_Front", "ShoulderL_TQ", "ShoulderR_TQ", "Shoulders_High"],
                            ["base", "normal", "hide:face", "hide:body", "lod0:skel", "noshadow"], hide)
    # skin underwear flag off (is the tank top the painted underwear? do the slivers follow it?)
    try:
        skin = ch.get_editor_property("skin_settings")
        sp = skin.get_editor_property("skin")
        before = bool(sp.get_editor_property("show_top_underwear"))
        sp.set_editor_property("show_top_underwear", not before)
        skin.set_editor_property("skin", sp)
        t0 = time.monotonic()
        mhs().commit_skin_settings(ch, skin)
        res["show_top_underwear_toggle"] = {"from": before, "to": not before, "commit_s": round(time.monotonic() - t0, 2)}
        yield from warmup(90, 4.0)
        tag = f"W_underwearTop{int(not before)}_"
        yield from shoot_matrix(scene, tag, views, ["Body_Front", "Shoulders_Front", "ShoulderL_TQ"], ["lit"], hide)
        yield from shoot_matrix(scene, tag, views, ["Shoulders_Front"], ["base"], hide)
        sp.set_editor_property("show_top_underwear", before)
        skin.set_editor_property("skin", sp)
        mhs().commit_skin_settings(ch, skin)
        yield from warmup(60, 3.0)
    except Exception as exc:  # noqa: BLE001
        warn(f"underwear toggle: {exc!r}")

    # the garment's hidden face maps (inventory; nothing modified on the plugin asset)
    wi = ue.load_asset(GARMENT_WI)
    gar = {"wardrobe_item": pth(wi)}
    try:
        pipe = wi.get_editor_property("pipeline")
        gar["pipeline"] = pth(pipe)
        ep = pipe.get_editor_property("editor_pipeline")
        gar["editor_pipeline"] = pth(ep)
        for prop in ("body_hidden_face_map_texture", "head_hidden_face_map_texture"):
            hfm = ep.get_editor_property(prop)
            tex = hfm.get_editor_property("texture")
            gar[prop] = {"texture": pth(tex), "settings": struct_dict(hfm.get_editor_property("settings"))}
            if tex is not None:
                gar[prop]["export"] = export_texture(tex, f"garment_{prop}")
    except Exception as exc:  # noqa: BLE001
        gar["error"] = repr(exc)[:300]
    res["garment"] = gar
    step("garment hidden-face maps", **gar)

    # add the real default outfit (as Kelvin has it)
    try:
        key = select_item(ch, "Outfits", wi)
        res["outfit_added"] = {"key": str(ue.MetaHumanPaletteKeyBlueprintLibrary.to_asset_name_string(key)),
                               "collection": collection_inventory(ch)}
        yield from warmup(200, 10.0)
        res["components_outfit"] = comp_inventory(actor)
        comps = components(actor)
        try:
            res["dump_Body_outfit"] = dump_mesh(comps["Body"], "W_outfit_Body")
        except Exception as exc:  # noqa: BLE001
            warn(f"dump body (outfit): {exc!r}")
        hide = hide_sets(actor)
        yield from shoot_matrix(scene, "W_outfit_", views, names, ["lit"], hide)
        yield from shoot_matrix(scene, "W_outfit_", views, ["Shoulders_Front", "ShoulderL_TQ"], ["hide:others"], hide)
    except Exception as exc:  # noqa: BLE001
        warn(f"outfit add: {exc!r}\n{traceback.format_exc()[-600:]}")
    # same outfit from a scratch copy of the wardrobe item WITHOUT its body hidden-face map
    try:
        wi2 = scratch_dup(GARMENT_WI, "WI_PD_DefaultGarment_NoBodyMask")
        ep2 = wi2.get_editor_property("pipeline").get_editor_property("editor_pipeline")
        hfm = ep2.get_editor_property("body_hidden_face_map_texture")
        hfm.set_editor_property("texture", None)
        ep2.set_editor_property("body_hidden_face_map_texture", hfm)
        res["nomask_wi"] = {"path": pth(wi2), "pipeline": pth(wi2.get_editor_property("pipeline")),
                            "body_map_now": pth(ep2.get_editor_property("body_hidden_face_map_texture").get_editor_property("texture")),
                            "original_body_map_still": pth(wi.get_editor_property("pipeline").get_editor_property("editor_pipeline")
                                                           .get_editor_property("body_hidden_face_map_texture").get_editor_property("texture"))}
        select_item(ch, "Outfits", wi2)
        yield from warmup(200, 10.0)
        comps = components(actor)
        try:
            res["dump_Body_outfit_nomask"] = dump_mesh(comps["Body"], "W_outfit_nomask_Body")
        except Exception as exc:  # noqa: BLE001
            warn(f"dump body (nomask): {exc!r}")
        hide = hide_sets(actor)
        yield from shoot_matrix(scene, "W_outfit_nomask_", views, ["Body_Front", "Shoulders_Front", "ShoulderL_TQ"],
                                ["lit", "hide:others"], hide)
    except Exception as exc:  # noqa: BLE001
        warn(f"no-mask outfit test: {exc!r}\n{traceback.format_exc()[-800:]}")
    # outfit removed again -> back to the start state
    try:
        select_item(ch, "Outfits", None)
        yield from warmup(120, 6.0)
        comps = components(actor)
        res["dump_Body_outfit_removed"] = dump_mesh(comps["Body"], "W_outfit_removed_Body")
        yield from shoot_matrix(scene, "W_outfit_removed_", views, ["Body_Front", "Shoulders_Front"], ["lit"], hide_sets(actor))
    except Exception as exc:  # noqa: BLE001
        warn(f"outfit remove: {exc!r}")
    release_actor(scene, actor, ch)
    step("wardrobe done")


MAT_TESTS = [   # (label, {scalar: value}) applied to every skin MID of the Face AND Body components
    ("nrm0", {"Normal Global Strength": 0.0}),
    ("fakeao0", {"Fake AO Strength": 0.0}),
    ("matao0", {"Material AO Power": 0.0}),
    ("spec0", {"Specular Global Multiply": 0.0}),
    ("concav0", {"Specular Concavity Multiply": 0.0, "Roughness Concavity Multiply": 0.0,
                 "Specular Micro Cavity Multiply": 0.0, "Roughness Micro Cavity Multiply": 0.0}),
    ("hider_off", {"HideMaskMaxCullValue": 0.0, "HideMaskMinKeepValue": 0.0, "HideMaskMaxShrinkDistance": 0.0}),
    ("extrashadow_eyelash_mouth0", {"Eyelashes Shadow": 0.0, "Mouth Occlusion": 0.0}),
]


def all_skin_mids(actor) -> list:
    out = []
    comps = components(actor)
    for cname in ("Face", "Body"):
        comp = comps.get(cname)
        if comp is None:
            continue
        for i in range(comp.get_num_materials()):
            m = comp.get_material(i)
            if m is None:
                continue
            try:
                base = pth(m.get_base_material())
            except Exception:  # noqa: BLE001
                base = ""
            if "M_skin_unified" not in (base or ""):
                continue
            if not isinstance(m, ue.MaterialInstanceDynamic):
                m = comp.create_dynamic_material_instance(i, m)
            out.append((cname, i, m))
    return out


def scalar_tests(scene, prefix, actor, views, view_names, tests=MAT_TESTS):
    mids = all_skin_mids(actor)
    res = {"mids": [(c, i) for c, i, _ in mids], "tests": {}}
    for label, scalars in tests:
        saved = []
        for cname, i, mid in mids:
            for n, v in scalars.items():
                try:
                    old = mid_get(mid, "scalar", n)
                except Exception:  # noqa: BLE001
                    continue
                saved.append((mid, n, old))
                mid.set_scalar_parameter_value(n, v)
        res["tests"][label] = {"n_set": len(saved), "old_values": sorted({(n, round(float(o), 4)) for _, n, o in saved})}
        if not saved:
            warn(f"scalar test {label}: parameters not found")
            continue
        yield from warmup(30, 1.2)
        scene.set_variant("lit")
        for vn in view_names:
            yield from shoot(scene, f"{prefix}{vn}_s-{label}.png", views[vn])
        for mid, n, old in saved:
            mid.set_scalar_parameter_value(n, old)
        write_report()
    REPORT.setdefault("scalar_tests", {})[prefix] = res
    write_report()


def mattests_job(scene: Scene):
    """Scalar switches on the live skin MIDs (Face + Body) of FaceC, then Kelvin (grooms hidden), one actor at a time."""
    res = REPORT.setdefault("mattests", {})
    ch = open_subject("FaceC", FACEC_PATH, "PD_Diag_FaceC_M", res)
    actor = spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup()
    views = dict(face_views(FACEC_CENTER))
    views.update(body_views())
    names = ["ThreeQuarter", "JawClose", "Low", "EarR", "Shoulders_Front", "ShoulderL_TQ"]
    hide = hide_sets(actor)
    res["FaceC"]["materials_Face"] = material_inventory(components(actor)["Face"])
    yield from shoot_matrix(scene, "M_FaceC_", views, names, ["lit"], hide)
    yield from shoot_matrix(scene, "M_FaceC_", views, ["ThreeQuarter", "JawClose", "Low", "Front"], ["bounce"], hide)
    yield from shoot_matrix(scene, "M_FaceC_", views, ["EarR", "EarRSide"], ["keyonly", "fillonly", "rimonly"], hide)
    yield from scalar_tests(scene, "M_FaceC_", actor, views, names)
    release_actor(scene, actor, ch)
    yield from warmup(30, 1.0)
    kch = open_subject("Kelvin", KELVIN_PATH, "PD_Diag_Kelvin_M", res)
    kactor = spawn(kch)
    scene.show_only(kactor, [kactor])
    yield from warmup()
    kviews = face_views(KELVIN_CENTER)
    khide = hide_sets(kactor)
    res["Kelvin"]["components"] = comp_inventory(kactor)
    yield from shoot(scene, "M_Kelvin_Front_lit-withgrooms.png", kviews["Front"])
    yield from shoot(scene, "M_Kelvin_ThreeQuarter_lit-withgrooms.png", kviews["ThreeQuarter"])
    scene.base_hide = khide["grooms"]
    try:
        yield from shoot_matrix(scene, "M_Kelvin_", kviews, ["ThreeQuarter", "Low", "JawClose", "Front"],
                                ["lit", "noshadow", "frontbelow", "keyonly", "base", "normal", "bounce"], khide)
        yield from shoot_matrix(scene, "M_Kelvin_", kviews, ["EarR", "EarRSide"],
                                ["lit", "keyonly", "fillonly", "rimonly", "base", "normal"], khide)
        kn = ["ThreeQuarter", "JawClose", "EarR"]
        yield from scalar_tests(scene, "M_Kelvin_", kactor, kviews, kn,
                                [t for t in MAT_TESTS if t[0] in ("nrm0", "fakeao0", "matao0", "spec0")])
    finally:
        scene.base_hide = []
    release_actor(scene, kactor, kch)
    step("mattests done")


def groom_state(actor) -> list:
    rows = []
    for c in actor.get_components_by_class(ue.GroomComponent):
        row = {"name": c.get_name(), "groom": pth(c.get_editor_property("groom_asset")),
               "binding": pth(c.get_editor_property("binding_asset")), "visible": bool(c.is_visible())}
        for prop in ("hidden_in_game", "visible"):
            try:
                row[prop + "_prop"] = bool(c.get_editor_property(prop))
            except Exception:  # noqa: BLE001
                pass
        try:
            o, e, _r = unwrap(ue.SystemLibrary.get_component_bounds(c))
            row["bounds_origin"] = struct_dict(o)
            row["bounds_extent"] = struct_dict(e)
        except Exception as exc:  # noqa: BLE001
            row["bounds_error"] = repr(exc)[:100]
        try:
            row["attach_parent"] = c.get_attach_parent().get_name() if c.get_attach_parent() else None
            row["world_location"] = struct_dict(c.get_world_location())
        except Exception:  # noqa: BLE001
            pass
        rows.append(row)
    return rows


def set_hair_shown(actor) -> str:
    """AMetaHumanCharacterEditorActor::Blueprint_SetHairVisibilityState (BlueprintImplementableEvent)."""
    try:
        enum = getattr(ue, "MetaHumanHairVisibilityState")
        state = enum.SHOWN
    except Exception as exc:  # noqa: BLE001
        return "enum ERR " + repr(exc)[:100]
    for name in ("blueprint_set_hair_visibility_state", "set_hair_visibility_state"):
        fn = getattr(actor, name, None)
        if fn is not None:
            try:
                fn(state)
                return f"called {name}"
            except Exception as exc:  # noqa: BLE001
                return f"{name} ERR {exc!r}"[:160]
    try:
        actor.call_method("Blueprint_SetHairVisibilityState", (state,))
        return "call_method Blueprint_SetHairVisibilityState"
    except Exception as exc:  # noqa: BLE001
        return "call_method ERR " + repr(exc)[:160]


def eye_mid_params(actor) -> dict:
    face = components(actor).get("Face")
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
        out[slot] = {"material": pth(m), "params": vals}
    return out


def hairprobe_job(scene: Scene):
    res = REPORT.setdefault("hairprobe", {})
    ch = open_subject("FaceC", FACEC_PATH, "PD_Diag_FaceC_H", res)
    actor = spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup()
    v = face_views(FACEC_CENTER)
    fx, fy, fz = FACEC_CENTER
    eyes_view = ((fx, fy + 45.0, fz + 0.8), (fx, fy, fz + 0.8), 16.0)
    wide = ((0.0, 260.0, 120.0), (0.0, 0.0, 120.0), 40.0)
    res["actor_class"] = actor.get_class().get_path_name()
    # ---- eyes: one preset, long settle, repeated captures, material read-back
    res["eyes_start_mid"] = eye_mid_params(actor)
    yield from shoot(scene, "H_eyes_start.png", eyes_view)
    for pname in ("Kelvin", "Trey"):
        pc = ue.load_asset(f"{PRESET_SRC}/{pname}")
        mhs().commit_eyes_settings(ch, pc.get_editor_property("eyes_settings"))
        got = ch.get_editor_property("eyes_settings")
        res[f"eyes_{pname}_settings_after_commit"] = {
            "left": struct_dict(got.get_editor_property("eye_left").get_editor_property("iris")),
            "right": struct_dict(got.get_editor_property("eye_right").get_editor_property("iris"))}
        for k, (n, s) in enumerate(((5, 0.2), (60, 2.0), (150, 6.0))):
            yield from warmup(n, s)
            yield from shoot(scene, f"H_eyes_{pname}_t{k}.png", eyes_view)
        res[f"eyes_{pname}_mid"] = eye_mid_params(actor)
        write_report()
    # ---- hair on FaceC: bounds, late appearance, visibility state
    wi = ue.load_asset(f"{GROOM_ROOT}/Hair/WI_Hair_S_Messy")
    select_item(ch, "Hair", wi)
    for k, (n, s) in enumerate(((60, 3.0), (300, 20.0), (300, 20.0))):
        yield from warmup(n, s)
        yield from shoot(scene, f"H_FaceC_hair_Messy_t{k}_Front.png", v["Front"])
        res[f"groom_state_t{k}"] = groom_state(actor)
        write_report()
    yield from shoot(scene, "H_FaceC_hair_Messy_Wide.png", wide)
    res["set_hair_shown"] = set_hair_shown(actor)
    yield from warmup(90, 4.0)
    yield from shoot(scene, "H_FaceC_hair_Messy_afterShown_Front.png", v["Front"])
    yield from shoot(scene, "H_FaceC_hair_Messy_afterShown_ThreeQuarter.png", v["ThreeQuarter"])
    res["groom_state_after_shown"] = groom_state(actor)
    # hair also in base colour (GBuffer) and with the Face hidden (is it inside the head?)
    hide = hide_sets(actor)
    yield from shoot_matrix(scene, "H_FaceC_hair_Messy_", v, ["Front"], ["base", "hide:face"], hide)
    release_actor(scene, actor, ch)
    yield from warmup(30, 1.0)
    # ---- the same hairstyle on Kelvin (does it render on Epic's own head?)
    kch = open_subject("Kelvin", KELVIN_PATH, "PD_Diag_Kelvin_H", res)
    kactor = spawn(kch)
    scene.show_only(kactor, [kactor])
    yield from warmup()
    kv = face_views(KELVIN_CENTER)
    res["kelvin_groom_state_start"] = groom_state(kactor)
    yield from shoot(scene, "H_Kelvin_hair_CurlyFade_Front.png", kv["Front"])
    select_item(kch, "Hair", wi)
    yield from warmup(300, 20.0)
    res["kelvin_groom_state_messy"] = groom_state(kactor)
    yield from shoot(scene, "H_Kelvin_hair_Messy_Front.png", kv["Front"])
    yield from shoot(scene, "H_Kelvin_hair_Messy_ThreeQuarter.png", kv["ThreeQuarter"])
    release_actor(scene, kactor, kch)
    step("hairprobe done")


LOOK_HAIR = [h.strip() for h in os.environ.get(
    "PD_LOOK_HAIR", "S_Messy,S_Casual,S_BrushCut,S_SweptUp,S_SideSweptFringe,S_PulledBack,S_Updo,S_UpdoBuns").split(",") if h.strip()]
LOOK_BROWS = os.environ.get("PD_LOOK_BROWS", "WI_Eyebrows_M_SlightArch")
LOOK_LASHES = os.environ.get("PD_LOOK_LASHES", "WI_Eyelashes_S_Fine")
LOOK_EYES = os.environ.get("PD_LOOK_EYES", "Kelvin")


def add_to_internal(ch, slot: str, wi) -> str:
    """Epic's example_add_grooms.py pattern: add + select on the INTERNAL collection before the character is
    opened for editing (the preview collection is then built from it)."""
    ic = ch.get_editor_property("internal_collection")
    key = ic.try_add_item_from_wardrobe_item(slot, wi)
    if key is None:
        raise RuntimeError(f"try_add_item_from_wardrobe_item({slot}, {pth(wi)}) failed")
    sel = ue.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=key)
    if not ic.get_editor_property("default_instance").try_add_slot_selection(sel):
        raise RuntimeError(f"try_add_slot_selection({slot}) failed")
    return str(ue.MetaHumanPaletteKeyBlueprintLibrary.to_asset_name_string(key))


def hairlook_job(scene: Scene):
    """One fresh FaceC scratch duplicate per hairstyle (hair first, then brows + lashes, all on the internal
    collection before editing; Kelvin's preset eyes; makeup none), captured front / 3-4 / back 3-4."""
    res = REPORT.setdefault("hairlook", {"brows": LOOK_BROWS, "lashes": LOOK_LASHES, "eyes_from": LOOK_EYES, "looks": {}})
    eyes = ue.load_asset(f"{PRESET_SRC}/{LOOK_EYES}").get_editor_property("eyes_settings")
    v = dict(face_views(FACEC_CENTER))
    fx, fy, fz = FACEC_CENTER
    head = (fx, fy - 2.0, fz + 3.0)
    v["Back34"] = (orbit(head, 75.0, 145, 10), head, 30.0)
    v["Top"] = (orbit(head, 70.0, 20, 50), head, 30.0)
    for h in LOOK_HAIR:
        name = f"WI_Hair_{h}"
        assert_clean(name)
        look = {}
        ch = None
        actor = None
        try:
            ch = scratch_dup(FACEC_PATH, f"PD_Look_{h}")
            look["hair_key"] = add_to_internal(ch, "Hair", ue.load_asset(f"{GROOM_ROOT}/Hair/{name}"))
            look["brows_key"] = add_to_internal(ch, "Eyebrows", ue.load_asset(f"{GROOM_ROOT}/Eyebrows/{LOOK_BROWS}"))
            look["lashes_key"] = add_to_internal(ch, "Eyelashes", ue.load_asset(f"{GROOM_ROOT}/Eyelashes/{LOOK_LASHES}"))
            ch.set_editor_property("eyes_settings", eyes)
            ch.set_editor_property("makeup_settings", ue.MetaHumanCharacterMakeupSettings())
            open_edit(ch)
            look["collection"] = collection_inventory(ch)["selections"]
            actor = spawn(ch)
            scene.show_only(actor, [actor])
            yield from warmup(240, 12.0)
            look["grooms"] = [r for r in groom_state(actor) if r["groom"]]
            look["eyes_mid"] = eye_mid_params(actor)
            for vn in ("Front", "ThreeQuarter", "Back34", "Top"):
                yield from shoot(scene, f"L_{h}_{vn}.png", v[vn])
            if h == LOOK_HAIR[0]:
                yield from shoot(scene, f"L_{h}_Body_Front.png", body_views()["Body_Front"])
        except Exception as exc:  # noqa: BLE001
            warn(f"look {h}: {exc!r}")
        finally:
            release_actor(scene, actor, ch)
        res["looks"][h] = look
        write_report()
        yield from warmup(20, 0.5)
    step("hairlook done")


HAIR_CANDIDATES = ["WI_Hair_S_Messy", "WI_Hair_S_Casual", "WI_Hair_S_BrushCut", "WI_Hair_S_SweptUp",
                   "WI_Hair_S_SideSweptFringe", "WI_Hair_S_PulledBack", "WI_Hair_S_Updo"]
BROW_CANDIDATES = ["WI_Eyebrows_M_Natural", "WI_Eyebrows_M_Fine", "WI_Eyebrows_M_SlightArch"]
LASH_CANDIDATES = ["WI_Eyelashes_S_Fine", "WI_Eyelashes_L_SlightCurl"]
FACE_TEX_CANDIDATES = [int(x) for x in os.environ.get("PD_FACE_TEX", "7,36,58,99").split(",") if x.strip()]


def identity_job(scene: Scene):
    res = REPORT.setdefault("identity", {})
    # 1) inventories (read-only)
    inv = {}
    for sub in ("Hair", "Eyebrows", "Eyelashes", "Beards", "Mustaches", "Peachfuzz"):
        inv[sub] = asset_list(f"{GROOM_ROOT}/{sub}", ue.MetaHumanWardrobeItem)
    inv["Clothing"] = asset_list("/MetaHumanCharacter/Optional/Clothing", ue.MetaHumanWardrobeItem)
    inv["Presets"] = asset_list(PRESET_SRC, ue.MetaHumanCharacter)
    res["inventory"] = inv
    step("wardrobe inventory", **{k: len(v) for k, v in inv.items()})
    presets = {}
    for pkg in inv["Presets"]:
        try:
            pc = ue.load_asset(pkg)
            presets[pkg.split("/")[-1]] = {
                "iris": struct_dict(pc.get_editor_property("eyes_settings").get_editor_property("eye_left").get_editor_property("iris")),
                "skin": struct_dict(pc.get_editor_property("skin_settings").get_editor_property("skin")),
                "freckles": struct_dict(pc.get_editor_property("skin_settings").get_editor_property("freckles")),
                "eyelashes": struct_dict(pc.get_editor_property("head_model_settings").get_editor_property("eyelashes"))}
        except Exception as exc:  # noqa: BLE001
            presets[pkg] = "ERR " + repr(exc)[:120]
        yield
    res["presets"] = presets
    try:
        ep = ue.load_asset("/MetaHumanCharacter/Tools/EyePresets/EyePresets")
        res["eye_presets_asset"] = {"loaded": pth(ep)}
        try:
            res["eye_presets_asset"]["presets"] = [
                {"name": str(p.get_editor_property("preset_name")),
                 "iris": struct_dict(p.get_editor_property("eyes_settings").get_editor_property("eye_left").get_editor_property("iris"))}
                for p in ep.get_editor_property("presets")]
        except Exception as exc:  # noqa: BLE001
            res["eye_presets_asset"]["presets_error"] = repr(exc)[:200]
    except Exception as exc:  # noqa: BLE001
        res["eye_presets_asset"] = "ERR " + repr(exc)[:200]
    write_report()

    # 2) scratch duplicate of FaceC
    ch = scratch_dup(FACEC_PATH, "PD_Diag_FaceC_I")
    open_edit(ch)
    res["start_settings"] = character_settings(ch)
    res["start_collection"] = collection_inventory(ch)
    actor = spawn(ch)
    scene.show_only(actor, [actor])
    yield from warmup()
    v = face_views(FACEC_CENTER)
    fx, fy, fz = FACEC_CENTER
    eyes_view = ((fx, fy + 45.0, fz + 0.8), (fx, fy, fz + 0.8), 16.0)
    yield from shoot(scene, "I_start_Front.png", v["Front"])

    # 3) makeup: everything off
    try:
        mk = ue.MetaHumanCharacterMakeupSettings()
        mhs().commit_makeup_settings(ch, mk)
        res["makeup_after"] = struct_dict(ch.get_editor_property("makeup_settings"))
        step("makeup cleared", makeup=res["makeup_after"])
    except Exception as exc:  # noqa: BLE001
        warn(f"makeup: {exc!r}")

    # 4) eyes: every preset's iris on FaceC (material only)
    eyes0 = ch.get_editor_property("eyes_settings")
    yield from shoot(scene, "I_eyes_start.png", eyes_view)
    eye_tests = {}
    for pname, pdata in presets.items():
        if not isinstance(pdata, dict):
            continue
        try:
            pc = ue.load_asset(f"{PRESET_SRC}/{pname}")
            es = pc.get_editor_property("eyes_settings")
            mhs().commit_eyes_settings(ch, es)
            yield from warmup(20, 0.6)
            yield from shoot(scene, f"I_eyes_{pname}.png", eyes_view)
            eye_tests[pname] = pdata["iris"]
        except Exception as exc:  # noqa: BLE001
            warn(f"eyes {pname}: {exc!r}")
    mhs().commit_eyes_settings(ch, eyes0)
    res["eye_tests"] = eye_tests

    # 5) skin: face texture variants at the character's current tone and at 0.5/0.5, freckles off
    skin0 = ch.get_editor_property("skin_settings")
    sp0 = skin0.get_editor_property("skin")
    res["skin_start"] = struct_dict(skin0)
    skin_tests = {}
    for idx in FACE_TEX_CANDIDATES:
        for tone in (("cur", sp0.get_editor_property("u"), sp0.get_editor_property("v")), ("mid", 0.5, 0.5)):
            if tone[0] == "cur" and idx != FACE_TEX_CANDIDATES[0]:
                continue
            try:
                s = ch.get_editor_property("skin_settings")
                sp = s.get_editor_property("skin")
                sp.set_editor_property("face_texture_index", idx)
                sp.set_editor_property("u", float(tone[1]))
                sp.set_editor_property("v", float(tone[2]))
                s.set_editor_property("skin", sp)
                fr = s.get_editor_property("freckles")
                fr.set_editor_property("mask", ue.MetaHumanCharacterFrecklesMask.NONE)
                s.set_editor_property("freckles", fr)
                t0 = time.monotonic()
                mhs().commit_skin_settings(ch, s)
                dt = round(time.monotonic() - t0, 2)
                got = ch.get_editor_property("skin_settings").get_editor_property("skin")
                skin_tests[f"tex{idx}_{tone[0]}"] = {"commit_s": dt, "face_texture_index": got.get_editor_property("face_texture_index"),
                                                    "u": round(got.get_editor_property("u"), 3), "v": round(got.get_editor_property("v"), 3)}
                yield from warmup(60, 3.0)
                yield from shoot(scene, f"I_skin_tex{idx}_{tone[0]}_Front.png", v["Front"])
                if idx == FACE_TEX_CANDIDATES[0]:
                    yield from shoot(scene, f"I_skin_tex{idx}_{tone[0]}_JawClose.png", v["JawClose"])
            except Exception as exc:  # noqa: BLE001
                warn(f"skin tex {idx}/{tone[0]}: {exc!r}")
    res["skin_tests"] = skin_tests
    write_report()

    # 6) brows + lashes (grooms) and head-model eyelashes
    groom_tests = {}
    for wi_name in BROW_CANDIDATES:
        try:
            wi = ue.load_asset(f"{GROOM_ROOT}/Eyebrows/{wi_name}")
            key = select_item(ch, "Eyebrows", wi)
            yield from warmup(90, 5.0)
            groom_tests[wi_name] = instance_params(ch, key)
            yield from shoot(scene, f"I_brows_{wi_name}.png", eyes_view)
        except Exception as exc:  # noqa: BLE001
            warn(f"brows {wi_name}: {exc!r}")
    for wi_name in LASH_CANDIDATES:
        try:
            wi = ue.load_asset(f"{GROOM_ROOT}/Eyelashes/{wi_name}")
            key = select_item(ch, "Eyelashes", wi)
            yield from warmup(90, 5.0)
            groom_tests[wi_name] = instance_params(ch, key)
            yield from shoot(scene, f"I_lashes_{wi_name}.png", eyes_view)
        except Exception as exc:  # noqa: BLE001
            warn(f"lashes {wi_name}: {exc!r}")
    try:
        hm = ch.get_editor_property("head_model_settings")
        el = hm.get_editor_property("eyelashes")
        res["head_model_eyelashes_before"] = struct_dict(el)
        el.set_editor_property("type", ue.MetaHumanCharacterEyelashesType.SHORT_FINE)
        hm.set_editor_property("eyelashes", el)
        mhs().commit_head_model_settings(ch, hm)
        res["head_model_eyelashes_after"] = struct_dict(ch.get_editor_property("head_model_settings").get_editor_property("eyelashes"))
        yield from warmup(60, 3.0)
        yield from shoot(scene, "I_lashes_headmodel_ShortFine.png", eyes_view)
    except Exception as exc:  # noqa: BLE001
        warn(f"head model eyelashes: {exc!r}")
    res["groom_tests"] = groom_tests
    write_report()

    # 7) short hairstyles
    hair_tests = {}
    for wi_name in HAIR_CANDIDATES:
        try:
            wi = ue.load_asset(f"{GROOM_ROOT}/Hair/{wi_name}")
            t0 = time.monotonic()
            key = select_item(ch, "Hair", wi)
            params = instance_params(ch, key)
            hair_tests[wi_name] = {"select_s": round(time.monotonic() - t0, 2), "params": params}
            yield from warmup(150, 8.0)
            for vn in ("Front", "ThreeQuarter"):
                yield from shoot(scene, f"I_hair_{wi_name}_{vn}.png", v[vn])
            hair_tests[wi_name]["components"] = [r for r in comp_inventory(actor) if r["class"] == "GroomComponent"]
        except Exception as exc:  # noqa: BLE001
            warn(f"hair {wi_name}: {exc!r}")
        write_report()
    res["hair_tests"] = hair_tests
    # dark-brown melanin test on the last hairstyle that worked
    try:
        last = [n for n in HAIR_CANDIDATES if n in hair_tests][0]
        wi = ue.load_asset(f"{GROOM_ROOT}/Hair/{last}")
        key = select_item(ch, "Hair", wi)
        ok = set_instance_param(ch, key, "Melanin", 0.8)
        res["melanin_test"] = {"hair": last, "set": ok, "params_after": instance_params(ch, key)}
        mhs().assemble_for_preview(ch)
        yield from warmup(120, 6.0)
        yield from shoot(scene, f"I_hair_{last}_melanin08_Front.png", v["Front"])
    except Exception as exc:  # noqa: BLE001
        warn(f"melanin test: {exc!r}")
    res["end_collection"] = collection_inventory(ch)
    step("identity done")


# ---------------------------------------------------------------------------------------------------------------
def main() -> None:
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n===== pd_diagnose.py mode={MODE} attempt={ATTEMPT} {_now()} =====\n")
    assert_locks()
    if not REPORT["engine"].startswith("5.8"):
        raise RuntimeError(f"expected UE 5.8.x, got {REPORT['engine']}")
    REPORT["sha_start"] = protected_hashes()
    scene = Scene()
    step("scene ready")
    jobs = {"defects": defects_job, "wardrobe": wardrobe_job, "identity": identity_job, "mattests": mattests_job,
            "hairprobe": hairprobe_job, "hairlook": hairlook_job}
    if MODE not in jobs:
        raise ValueError(f"unknown PD_DIAG_MODE {MODE}")
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
        step("STATUS " + REPORT["status"] + " (nothing saved)", protected_unchanged=REPORT["protected_assets_unchanged"])
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
