"""pf_common.py -- shared UE-side helpers for the female player variant MH_PlayerFemale (imported by pf_female.py).

Adapted from pd_r2_common.py (MH_PlayerDefault round 2): same light rig (key/fill/rim + sky), same backdrop and
capture settings, and the 'ambient' evaluation variant (sky light captures the grey backdrop all round = real
ambient; the plain studio rig has no working ambient, so the under-jaw band is black there). Cameras are aimed from
the character's own face landmarks (face centre = landmark centroid + the offset the male builder camera used) and
its height, because the female head sits lower than the 185.6 cm male's.

No side effects on import apart from reading the environment. Never signs in; never calls request_auto_rigging,
request_texture_sources or build_meta_human.
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
OUT = ROOT / "WorkFiles/MetaHuman/player_female"
MODE = os.environ.get("PF_MODE", "explore1").strip().lower()
ATTEMPT = os.environ.get("PF_ATTEMPT", "1").strip()
CAPTURES = OUT / (f"{MODE}_captures")
REPORT_PATH = OUT / f"pf_{MODE}_{ATTEMPT}.json"
STEP_LOG = OUT / "player_female.log"
CONTENT = ROOT / "Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
PROTECTED = ["MH_PlayerDefault", "MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB",
             "MH_PlayerBase_FaceC", "MH_MaleBase"]

CHAR_DIR = "/Game/Characters/MetaHumans"
PF_NAME = "MH_PlayerFemale"
PF_PATH = f"{CHAR_DIR}/{PF_NAME}"
SCRATCH = "/Game/PlayerFemale/Scratch"
PRESET_SRC = "/MetaHumanCharacter/Optional/Presets"
GROOM_ROOT = "/MetaHumanCharacter/Optional/Grooms/Bindings"
MAX_SECONDS = float(os.environ.get("PF_MAX_MINUTES", "45")) * 60.0

sys.path.insert(0, str(ROOT / "Scripts/MetaHuman"))
import pb_face_build as PFB  # noqa: E402  (blend, layout, REGION_GROUPS; imports unreal only)

# ---- light rig: identical to pb_conform.py / pd_r2_common.py ----------------------------------------------------
LIGHT_RIG = [(-27.0, -117.0, 0.0, 4.0, (1, .95, .9), True),    # key: front-right, above, shadows
             (-12.0, -58.0, 0.0, 2.0, (.9, .94, 1), False),    # fill: front-left, low
             (-37.0, 90.0, 0.0, 2.0, (1, 1, 1), False)]        # rim: behind, above
SKY_INTENSITY = 1.5
SIMPLE_RENDER_CVARS = ["r.DynamicGlobalIlluminationMethod 0", "r.ReflectionMethod 0", "r.AmbientOcclusionLevels 0",
                       "r.DistanceFieldAO 0", "r.RayTracing.ForceAllRayTracingEffects 0", "r.AntiAliasingMethod 2"]
SHOT_W, SHOT_H = 1000, 1200
BODY_CAM_DIST = 380.0
FACE_CAM_DIST = 58.0
# male builder camera: FACE_CENTER (0, 5.9597, 173.6) = landmark centroid of MH_PlayerDefault + this offset
FACE_CENTER_OFFSET = (0.0, -1.1749, 2.2657)
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
    return {n: sha256(CONTENT / f"{n}.uasset") for n in PROTECTED}


REPORT: dict = {"script": "Scripts/MetaHuman/pf_female.py", "mode": MODE, "attempt": ATTEMPT,
                "engine": ue.SystemLibrary.get_engine_version(), "status": "starting", "started_utc": _now(),
                "steps": [], "captures": [], "warnings": [], "checks": {}}


def write_report() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(REPORT, indent=1, default=str), encoding="utf-8")


def step(msg: str, **extra) -> None:
    t = round(time.monotonic() - T0, 1)
    line = f"{_now()}  +{t:7.1f}s  [pf {MODE}/{ATTEMPT}] {msg}"
    if extra:
        line += "  " + json.dumps(extra, default=str)[:3000]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    ue.log("PF " + line)
    REPORT["steps"].append({"t_s": t, "msg": msg, **extra})
    write_report()


def warn(msg: str) -> None:
    REPORT["warnings"].append(msg)
    step("WARNING " + msg)


def check(name: str, ok: bool, **detail) -> bool:
    REPORT["checks"][name] = {"ok": bool(ok), **detail}
    step(f"CHECK {name}: {'OK' if ok else 'FAIL'}", **detail)
    return bool(ok)


def assert_locks(extra=()) -> None:
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock  # stdlib only
    for name in [PF_NAME] + list(extra):
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
    if depth > 5:
        return str(s)
    if isinstance(s, (bool, int, float, str)) or s is None:
        return s
    if isinstance(s, ue.LinearColor):
        return [round(s.r, 4), round(s.g, 4), round(s.b, 4), round(s.a, 4)]
    if isinstance(s, ue.Vector) or type(s).__name__ in ("Vector3f", "Vector3d", "Vector2f", "Vector2D"):
        return [round(getattr(s, a), 4) for a in ("x", "y", "z") if hasattr(s, a)]
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
# Scene
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
        self.sky_default = {p: self.sky.light_component.get_editor_property(p)
                            for p in ("sky_distance_threshold", "lower_hemisphere_is_black")}
        self.sky_ambient = None
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
        for command in SIMPLE_RENDER_CVARS:
            ue.SystemLibrary.execute_console_command(self.world, command)
        self.hidden = []
        self.variant = None
        self.set_variant("ambient")

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
        if self.sky_ambient is not None and bool(on) == self.sky_ambient:
            return False
        comp = self.sky.light_component
        if on:
            comp.set_editor_property("sky_distance_threshold", 1000.0)
            comp.set_editor_property("lower_hemisphere_is_black", False)
        else:
            comp.set_editor_property("sky_distance_threshold", float(self.sky_default["sky_distance_threshold"]))
            comp.set_editor_property("lower_hemisphere_is_black", bool(self.sky_default["lower_hemisphere_is_black"]))
        comp.recapture_sky()
        self.sky_ambient = bool(on)
        return True

    def set_variant(self, variant: str) -> bool:
        """ambient = studio key/fill/rim + the sky light capturing the 0.18-grey backdrop (the judging rig)
        studio  = the pb_conform rig exactly (no working ambient)"""
        for light, (pitch, yaw, roll, intensity, color, shadows) in zip(self.lights, LIGHT_RIG):
            light.set_actor_rotation(ue.Rotator(roll=roll, pitch=pitch, yaw=yaw), False)
            light.light_component.set_intensity(intensity)
            light.light_component.set_light_color(ue.LinearColor(*color, 1))
            light.light_component.set_cast_shadows(shadows)
            set_specular(light, 1.0)
        self.sky.light_component.set_intensity(SKY_INTENSITY)
        changed = self.set_sky_ambient(variant == "ambient")
        self.variant = variant
        return changed

    def aim(self, location, look_at, fov_deg: float = 30.0) -> None:
        loc = ue.Vector(*location)
        rot = ue.MathLibrary.find_look_at_rotation(loc, ue.Vector(*look_at))
        self.camera.set_actor_location_and_rotation(loc, rot, False, False)
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


def face_center_from_landmarks(lm) -> tuple:
    n = len(lm)
    c = [sum(p[i] for p in lm) / n for i in range(3)]
    return (0.0, c[1] + FACE_CENTER_OFFSET[1], c[2] + FACE_CENTER_OFFSET[2])


def views(fc, height: float) -> dict:
    """Camera set (location, look-at, horizontal fov). fc = face centre, height = body height (cm)."""
    d = FACE_CAM_DIST
    v = {"Face_Front": (orbit(fc, d, 0, 0), fc, 30.0),
         "Face_TQ_L": (orbit(fc, d, 35, 0), fc, 30.0),     # camera on the character's left (+X)
         "Face_TQ_R": (orbit(fc, d, -35, 0), fc, 30.0),
         "Face_Profile_L": (orbit(fc, d, 90, 0), fc, 30.0),
         "Face_Profile_R": (orbit(fc, d, -90, 0), fc, 30.0),
         "Face_Close": (orbit(fc, 40.0, 0, 0), (fc[0], fc[1], fc[2] + 0.5), 22.0),
         "Face_Close_TQ": (orbit(fc, 40.0, 30, 0), (fc[0], fc[1], fc[2] + 0.5), 22.0),
         "Face_Low": (orbit(fc, d, 20, -20), fc, 30.0)}
    bz = height * 0.5
    v["Body_Front"] = ((0.0, BODY_CAM_DIST, bz), (0.0, 0.0, bz), 30.0)
    v["Body_Side"] = ((BODY_CAM_DIST, 0.0, bz), (0.0, 0.0, bz), 30.0)
    v["Body_Back"] = ((0.0, -BODY_CAM_DIST, bz), (0.0, 0.0, bz), 30.0)
    v["Body_TQ"] = (orbit((0.0, 0.0, bz), BODY_CAM_DIST, 35, 0), (0.0, 0.0, bz), 30.0)
    head = (fc[0], fc[1] - 3.0, fc[2] + 2.0)
    v["Hair_Back34_L"] = (orbit(head, 70.0, 140, 10), head, 32.0)
    v["Hair_Back34_R"] = (orbit(head, 70.0, -140, 10), head, 32.0)
    v["Hair_Back"] = (orbit(head, 75.0, 180, 5), head, 34.0)
    v["Hair_Side_L"] = (orbit(head, 70.0, 90, 8), head, 32.0)
    v["Hair_Top"] = (orbit(head, 70.0, 20, 50), head, 32.0)
    v["Hair_Front_High"] = (orbit(head, 70.0, 0, 25), head, 32.0)
    v["Eyes"] = (orbit((fc[0], fc[1], fc[2] + 1.0), 32.0, 0, 0), (fc[0], fc[1], fc[2] + 1.0), 16.0)
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
    scene.export(name)
    step("captured " + name, variant=scene.variant)


def switch(scene: Scene, variant: str):
    if scene.set_variant(variant):
        yield from warmup(90, 3.0)   # sky recapture
    else:
        yield from warmup(20, 0.8)


def region_luma(scene: Scene, x0, x1, y0, y1, step_px=20) -> float:
    lum = []
    for x in range(x0, x1 + 1, step_px):
        for y in range(y0, y1 + 1, step_px):
            c = ue.RenderingLibrary.read_render_target_pixel(scene.world, scene.rt, x, y)
            lum.append(0.299 * c.r + 0.587 * c.g + 0.114 * c.b)
    lum.sort()
    return lum[len(lum) // 2]


# ---------------------------------------------------------------------------------------------------------------
# MetaHuman helpers
# ---------------------------------------------------------------------------------------------------------------
def mhs():
    return ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)


EDITED: list = []


def scratch_dup(src: str, name: str):
    """In-memory duplicate under /Game/PlayerFemale/Scratch (never saved)."""
    dst = f"{SCRATCH}/{name}"
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
    """moves = [{"idx": [...], "d": [dx,dy,dz]} or {"idx": [...], "d_per": [[dx,dy,dz], ...]}]; UE cm
    (x lateral: -X = character's right, y forward, z up)."""
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


def set_groom_param(col, key, name: str, value) -> bool:
    inst = col.get_editor_property("default_instance")
    for p in inst.get_instance_parameters(item_path=ue.MetaHumanPaletteItemPath(item_key=key)):
        if str(p.get_editor_property("name")) == name:
            if isinstance(value, bool):
                p.set_bool(value)
            else:
                p.set_float(float(value))
            return True
    return False


def set_internal_slot(ch, slot: str, wi_path: str) -> str:
    """Put a wardrobe item in the character's INTERNAL collection and select it (replacing any selection)."""
    wi = ue.load_asset(wi_path)
    if wi is None:
        raise RuntimeError(f"wardrobe item {wi_path} not found")
    ic = ch.get_editor_property("internal_collection")
    key = ic.try_add_item_from_wardrobe_item(slot, wi)
    if key is None:
        raise RuntimeError(f"try_add_item_from_wardrobe_item({slot}, {wi_path}) failed")
    inst = ic.get_editor_property("default_instance")
    try:
        inst.set_single_slot_selection(slot, key)
    except Exception:  # noqa: BLE001
        sel = ue.MetaHumanPipelineSlotSelection(slot_name=slot, selected_item=key)
        if not inst.try_add_slot_selection(sel):
            raise
    return key_name(key)


def set_preview_slot(ch, slot: str, wi_path: str) -> str:
    """Same on the PREVIEW collection of a character that is open for edit (then on_edit_preview_collection)."""
    col = mhs().get_preview_collection(ch)
    key = col.try_add_item_from_wardrobe_item(slot, ue.load_asset(wi_path))
    if key is None:
        raise RuntimeError(f"preview try_add_item_from_wardrobe_item({slot}, {wi_path}) failed")
    col.get_editor_property("default_instance").set_single_slot_selection(slot, key)
    mhs().on_edit_preview_collection(ch)
    return key_name(key)


def groom_state(actor) -> list:
    rows = []
    for c in actor.get_components_by_class(ue.GroomComponent):
        rows.append({"name": c.get_name(), "groom": pth(c.get_editor_property("groom_asset")),
                     "binding": pth(c.get_editor_property("binding_asset")), "visible": bool(c.is_visible())})
    return rows


def skin_readback(ch) -> dict:
    s = ch.get_editor_property("skin_settings")
    sp = s.get_editor_property("skin")
    out = {"u": round(float(sp.get_editor_property("u")), 4), "v": round(float(sp.get_editor_property("v")), 4),
           "face_texture_index": int(sp.get_editor_property("face_texture_index")),
           "body_texture_index": int(sp.get_editor_property("body_texture_index")),
           "roughness": round(float(sp.get_editor_property("roughness")), 4),
           "show_top_underwear": bool(sp.get_editor_property("show_top_underwear")),
           "freckles_mask": enum_s(s.get_editor_property("freckles").get_editor_property("mask"))}
    for prop in ("body_bias", "body_gain"):
        try:
            out[prop] = struct_dict(sp.get_editor_property(prop))
        except Exception as exc:  # noqa: BLE001
            out[prop] = "ERR " + repr(exc)[:80]
    try:
        b = out["body_bias"]
        out["tone_srgb_from_bias"] = [round((x / 256.0) ** (1 / 2.2), 4) for x in b]
    except Exception:  # noqa: BLE001
        pass
    return out


def commit_skin(ch, u=None, v=None, face_texture_index=None, freckles_none=True, roughness=None,
                show_top_underwear=True, accents=None) -> dict:
    s = ch.get_editor_property("skin_settings")
    sp = s.get_editor_property("skin")
    if u is not None:
        sp.set_editor_property("u", float(u))
    if v is not None:
        sp.set_editor_property("v", float(v))
    if face_texture_index is not None:
        sp.set_editor_property("face_texture_index", int(face_texture_index))
    if roughness is not None:
        sp.set_editor_property("roughness", float(roughness))
    sp.set_editor_property("show_top_underwear", bool(show_top_underwear))
    s.set_editor_property("skin", sp)
    if freckles_none:
        fr = s.get_editor_property("freckles")
        fr.set_editor_property("mask", ue.MetaHumanCharacterFrecklesMask.NONE)
        s.set_editor_property("freckles", fr)
    if accents:
        acc = s.get_editor_property("accents")
        for region, vals in accents.items():
            r = acc.get_editor_property(region)
            for k, val in vals.items():
                r.set_editor_property(k, float(val))
            acc.set_editor_property(region, r)
        s.set_editor_property("accents", acc)
    s.set_editor_property("enable_texture_overrides", False)
    mhs().commit_skin_settings(ch, s)
    return skin_readback(ch)


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
        REPORT["protected_assets_unchanged"] = REPORT.get("sha_start") == REPORT["sha_end"]
        REPORT["status"] = "done" if success else "failed"
        REPORT["finished_utc"] = _now()
        step("STATUS " + REPORT["status"], protected_unchanged=REPORT["protected_assets_unchanged"])
        ue.SystemLibrary.quit_editor()
