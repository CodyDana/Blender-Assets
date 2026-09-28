"""pb_face_design.py -- original-face candidates for the conformed MH_PlayerBase (UE 5.8.3, MetaHumanCharacter).

Runs INSIDE UnrealEditor on Exports/CharacterLab/Unreal/CharacterLab.uproject; launch with
Scripts/MetaHuman/pb_run_face.ps1 (one editor at a time, RAM preflight, waits for exit).

MH_PlayerBase and MH_MaleBase are NEVER opened for edit or saved here: MH_PlayerBase is only read through
duplicates, MH_MaleBase is not loaded at all. Presets are read through in-memory duplicates under
/Game/PlayerBase/Scratch (never saved). Never signs in; never calls request_auto_rigging /
request_texture_sources / build_meta_human.

PB_FACE_MODE=probe   learn the face API on a scratch duplicate of MH_PlayerBase (never saved):
                     coefficient layout, landmarks, what a 100% preset coefficient swap does, captures.
PB_FACE_MODE=build   read PB_FACE_RECIPES (json), duplicate MH_PlayerBase into each candidate asset, apply the
                     recipe to the FACE only, commit, save, measure (body constraints, bones, body vertices,
                     face landmarks) and capture face front / 3-4 / body front with the builder's cameras.

Outputs: WorkFiles/MetaHuman/player_base/faces/ (face_<mode>_report.json, face_design.log, captures/*.png,
mesh_dump/*.obj).
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
import types
from pathlib import Path

import unreal as ue

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
PB_OUT = ROOT / "WorkFiles/MetaHuman/player_base"
FACES = PB_OUT / "faces"
CAPTURES = FACES / "captures"
DUMPS = FACES / "mesh_dump"
MODE = os.environ.get("PB_FACE_MODE", "probe").strip().lower()
RECIPES = os.environ.get("PB_FACE_RECIPES", "").strip()
ATTEMPT = os.environ.get("PB_ATTEMPT", "1").strip()
REPORT_PATH = FACES / f"face_{MODE}_report_{ATTEMPT}.json"
STEP_LOG = FACES / "face_design.log"
CONTENT = ROOT / "Exports/CharacterLab/Unreal/Content"
BASELINE_UASSET = CONTENT / "Characters/MetaHumans/MH_MaleBase.uasset"
BASE_UASSET = CONTENT / "Characters/MetaHumans/MH_PlayerBase.uasset"

CHAR_DIR = "/Game/Characters/MetaHumans"
BASE_PATH = f"{CHAR_DIR}/MH_PlayerBase"
BASELINE_PATH = f"{CHAR_DIR}/MH_MaleBase"
PRESET_SRC = "/MetaHumanCharacter/Optional/Presets"
SCRATCH = "/Game/PlayerBase/Scratch"
FORBIDDEN_TOKENS = ("jinmuwon", "muwon", "mu-won", "mu_won")
MAX_SECONDS = float(os.environ.get("PB_MAX_MINUTES", "50")) * 60.0

# ---- cameras / lights: identical to pb_conform.py (the builder) ----------------------------------------------
LIGHT_RIG = [(-27.0, -117.0, 0.0, 4.0, (1, .95, .9), True),
             (-12.0, -58.0, 0.0, 2.0, (.9, .94, 1), False),
             (-37.0, 90.0, 0.0, 2.0, (1, 1, 1), False)]
SIMPLE_RENDER_CVARS = ["r.DynamicGlobalIlluminationMethod 0", "r.ReflectionMethod 0", "r.AmbientOcclusionLevels 0",
                       "r.DistanceFieldAO 0", "r.RayTracing.ForceAllRayTracingEffects 0", "r.AntiAliasingMethod 2"]
SHOT_W, SHOT_H = 1000, 1200
BODY_CAM_DIST = 380.0
BODY_CAM_Z = 93.0
FACE_CAM_DIST = 70.0
PB_FACE_CENTER = (0.0, 5.959721088409424, 173.6)   # conform_report.json mh_face_center
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
    return h.hexdigest()


REPORT: dict = {"script": "Scripts/MetaHuman/pb_face_design.py", "mode": MODE, "attempt": ATTEMPT,
                "engine": ue.SystemLibrary.get_engine_version(), "status": "starting", "started_utc": _now(),
                "steps": [], "captures": [], "warnings": []}


def write_report() -> None:
    FACES.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(REPORT, indent=1, default=str), encoding="utf-8")


def step(msg: str, **extra) -> None:
    t = round(time.monotonic() - T0, 1)
    line = f"{_now()}  +{t:7.1f}s  [{MODE}/{ATTEMPT}] {msg}"
    if extra:
        line += "  " + json.dumps(extra, default=str)[:2000]
    FACES.mkdir(parents=True, exist_ok=True)
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    ue.log("PB_FACE " + line)
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


def assert_locks(extra=()) -> None:
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock  # stdlib only
    lock.assert_owner("MH_PlayerBase", "claude")
    lock.assert_owner("MH_MaleBase", "claude")
    for name in extra:
        lock.assert_owner(name, "claude")


def v3(v) -> list:
    return [round(float(v.x), 4), round(float(v.y), 4), round(float(v.z), 4)]


def unwrap(result):
    if isinstance(result, tuple) and len(result) == 1:
        return result[0]
    return result


# ---------------------------------------------------------------------------------------------------------------
# Scene (same lights, backdrop, capture settings as pb_conform.py)
# ---------------------------------------------------------------------------------------------------------------
class Scene:
    def __init__(self):
        ue.EditorLoadingAndSavingUtils.new_blank_map(False)
        self.world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.lights = []
        for pitch, yaw, roll, intensity, color, shadows in LIGHT_RIG:
            light = self.spawn(ue.DirectionalLight)
            light.set_actor_rotation(ue.Rotator(roll=roll, pitch=pitch, yaw=yaw), False)
            light.light_component.set_intensity(intensity)
            light.light_component.set_light_color(ue.LinearColor(*color, 1))
            light.light_component.set_cast_shadows(shadows)
            self.lights.append(light)
        backdrop = self.spawn(ue.StaticMeshActor)
        backdrop.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Sphere"))
        backdrop.set_actor_scale3d(ue.Vector(50, 50, 50))
        backdrop.static_mesh_component.set_cast_shadow(False)
        mat = ue.new_object(ue.Material)
        mat.set_editor_property("two_sided", True)
        mat.set_editor_property("shading_model", ue.MaterialShadingModel.MSM_UNLIT)
        node = ue.MaterialEditingLibrary.create_material_expression(mat, ue.MaterialExpressionConstant3Vector)
        node.set_editor_property("constant", ue.LinearColor(.18, .18, .18, 1))
        ue.MaterialEditingLibrary.connect_material_property(node, "", ue.MaterialProperty.MP_EMISSIVE_COLOR)
        ue.MaterialEditingLibrary.recompile_material(mat)
        backdrop.static_mesh_component.set_material(0, mat)
        self.backdrop = backdrop
        sky = self.spawn(ue.SkyLight)
        sky.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        sky.light_component.set_intensity(1.5)
        sky.light_component.recapture_sky()
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

    def spawn(self, cls, location=(0, 0, 0)):
        return self.actors.spawn_actor_from_class(cls, ue.Vector(*location), ue.Rotator())

    def show_only(self, keep, all_actors) -> None:
        self.hidden = [a for a in all_actors if a is not None and a != keep]
        self.apply_hidden()

    def apply_hidden(self) -> None:
        self.capture.clear_hidden_components()
        for actor in self.hidden:
            self.capture.hide_actor_components(actor, True)

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


def face_shots(prefix: str, center, which=("Front", "ThreeQuarter")):
    fx, fy, fz = center
    d = FACE_CAM_DIST
    a = math.radians(35.0)
    table = {"Front": (fx, fy + d, fz),
             "ThreeQuarter": (fx + d * math.sin(a), fy + d * math.cos(a), fz),
             "Profile": (fx + d, fy, fz)}
    return [(f"{prefix}Face_{w}.png", table[w], (fx, fy, fz)) for w in which]


def body_front(prefix: str):
    return [(f"{prefix}Body_Front.png", (0.0, BODY_CAM_DIST, BODY_CAM_Z), (0.0, 0.0, BODY_CAM_Z))]


# ---------------------------------------------------------------------------------------------------------------
# Generator helpers (one yield == one editor frame; the scene is re-rendered every frame)
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


def take(scene: Scene, shots):
    for name, loc, look in shots:
        scene.aim(loc, look, 30.0)
        scene.apply_hidden()
        yield from settle()
        scene.capture.capture_scene()
        scene.export(name)
        step("captured " + name)


# ---------------------------------------------------------------------------------------------------------------
# MetaHuman helpers
# ---------------------------------------------------------------------------------------------------------------
def mhs():
    return ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)


EDITED: list = []


def scratch_dup(src: str, dst: str):
    """In-memory duplicate (never saved). Loads it if an earlier step of this run made it."""
    assert_clean(dst)
    assert dst.startswith(SCRATCH + "/")
    if ue.EditorAssetLibrary.does_asset_exist(dst):
        obj = ue.load_asset(dst)
    else:
        obj = ue.EditorAssetLibrary.duplicate_asset(src, dst)
    if not isinstance(obj, ue.MetaHumanCharacter):
        raise RuntimeError(f"duplicate {src} -> {dst} did not give a MetaHumanCharacter ({obj})")
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


def coeffs(ch) -> list:
    return [float(x) for x in unwrap(mhs().get_face_model_coefficients(ch))]


def landmarks(ch) -> list:
    return [v3(v) for v in unwrap(mhs().get_face_landmarks(ch))]


def eval_settings(ch) -> dict:
    s = ch.get_editor_property("face_evaluation_settings")
    return {k: round(float(s.get_editor_property(k)), 5) for k in ("global_delta", "high_frequency_delta", "head_scale")}


def constraints(ch) -> dict:
    return {str(c.name): round(float(c.target_measurement), 3) for c in mhs().get_body_constraints(ch, False)}


def set_coeffs(ch, values) -> None:
    arr = ue.Array(float)
    arr.extend([float(x) for x in values])
    mhs().set_face_model_coefficients(ch, arr)


def save_asset(asset) -> None:
    path = asset.get_path_name()
    if "/MH_PlayerBase." in path or "/MH_MaleBase." in path:
        raise RuntimeError(f"refusing to save protected asset {path}")
    if not ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {path}")


def find_component(actor, name: str):
    for comp in actor.get_components_by_class(ue.SkeletalMeshComponent):
        if comp.get_name() == name:
            return comp
    return None


def bone_positions(actor) -> dict:
    body = find_component(actor, "Body")
    res = {}
    if body is None:
        return res
    for name in MH_BONES:
        if body.does_socket_exist(name):
            res[name] = v3(body.get_socket_location(name))
    return res


def dump_component(component, stem: str):
    dm = ue.new_object(ue.DynamicMesh)
    opts = ue.GeometryScriptCopyMeshFromComponentOptions()
    opts.set_editor_property("want_normals", False)
    opts.set_editor_property("want_tangents", False)
    ue.GeometryScript_SceneUtils.copy_mesh_from_component(component, dm, opts, True)
    pos = ue.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
    pos_list = next(x for x in (pos if isinstance(pos, tuple) else (pos,))
                    if isinstance(x, ue.GeometryScriptVectorList))
    tri = ue.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
    tri_list = next(x for x in (tri if isinstance(tri, tuple) else (tri,))
                    if isinstance(x, ue.GeometryScriptTriangleList))
    verts = ue.GeometryScript_List.convert_vector_list_to_array(pos_list)
    tris = ue.GeometryScript_List.convert_triangle_list_to_array(tri_list)
    pts = [(float(v.x), float(v.y), float(v.z)) for v in verts]
    DUMPS.mkdir(parents=True, exist_ok=True)
    with open(DUMPS / f"{stem}.obj", "w", encoding="utf-8") as fh:
        fh.write("# UE world space, cm, Z up, character faces +Y\n")
        for p in pts:
            fh.write(f"v {p[0]:.4f} {p[1]:.4f} {p[2]:.4f}\n")
        for t in tris:
            fh.write(f"f {int(t.x) + 1} {int(t.y) + 1} {int(t.z) + 1}\n")
    return len(pts), len(tris)


def spawn(ch):
    actor = mhs().spawn_meta_human_actor(ch, True)
    if actor is None:
        raise RuntimeError(f"spawn_meta_human_actor returned None for {ch.get_name()}")
    mhs().assemble_for_preview(ch)
    return actor


def centroid(pts):
    n = float(len(pts))
    return [sum(p[i] for p in pts) / n for i in range(3)]


# ---------------------------------------------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------------------------------------------
PROBE_PRESETS = [p.strip() for p in os.environ.get(
    "PB_PROBE_PRESETS", "Kelvin,Bo,Aoi,Lani,Tuya,Aera,Mateo,Victor,Orlando,Jorge,Trey,Mikel").split(",") if p.strip()]


def probe_job(scene: Scene):
    m = mhs()
    data = REPORT.setdefault("probe", {})
    # 1) presets: coefficients / landmarks / evaluation settings (in-memory duplicates, released right away)
    presets = {}
    for name in PROBE_PRESETS:
        try:
            dup = scratch_dup(f"{PRESET_SRC}/{name}", f"{SCRATCH}/PRE_{name}")
            open_edit(dup)
            presets[name] = {"coeffs": coeffs(dup), "landmarks": landmarks(dup), "eval": eval_settings(dup),
                             "height": constraints(dup).get("Height")}
            close_edit(dup)
            step(f"preset {name} read", n_coeffs=len(presets[name]["coeffs"]), n_lm=len(presets[name]["landmarks"]),
                 eval=presets[name]["eval"], height=presets[name]["height"])
        except Exception as exc:  # noqa: BLE001
            warn(f"preset {name}: {exc!r}")
        yield
    data["presets"] = presets
    write_report()

    # 2) scratch duplicate of MH_PlayerBase (never saved)
    probe = scratch_dup(BASE_PATH, f"{SCRATCH}/PB_FaceProbe")
    open_edit(probe)
    base_c = coeffs(probe)
    base_lm = landmarks(probe)
    data["base"] = {"coeffs": base_c, "landmarks": base_lm, "eval": eval_settings(probe),
                    "constraints": constraints(probe)}
    step("probe base read", n_coeffs=len(base_c), n_lm=len(base_lm), eval=data["base"]["eval"])
    tests = {}

    def run_test(label, values):
        set_coeffs(probe, values)
        lm = landmarks(probe)
        got = coeffs(probe)
        tests[label] = {"landmarks": lm, "coeff_roundtrip_maxdiff": max(abs(a - b) for a, b in zip(got, values))}
        step(f"test {label}", roundtrip=tests[label]["coeff_roundtrip_maxdiff"])

    kel = presets.get("Kelvin", {}).get("coeffs")
    if kel and len(kel) == len(base_c):
        run_test("kelvin_full", kel)
        run_test("kelvin_keep_head10", base_c[:10] + kel[10:])
        run_test("kelvin_half", [b + 0.5 * (k - b) for b, k in zip(base_c, kel)])
    run_test("restore", base_c)
    # sculpt API: nudge landmark 0 by +0.5 cm X
    try:
        idx = ue.Array(int)
        idx.append(0)
        dl = ue.Array(ue.Vector)
        dl.append(ue.Vector(0.5, 0.0, 0.0))
        m.translate_face_landmarks(probe, idx, dl)
        after = coeffs(probe)
        tests["translate_lm0"] = {"landmarks": landmarks(probe),
                                  "n_coeff_changed": sum(1 for a, b in zip(after, base_c) if abs(a - b) > 1e-6),
                                  "coeffs": after}
        step("translate_face_landmarks probe", n_changed=tests["translate_lm0"]["n_coeff_changed"])
        set_coeffs(probe, base_c)
    except Exception as exc:  # noqa: BLE001
        warn(f"translate_face_landmarks probe: {exc!r}")
    data["tests"] = tests
    write_report()

    # 3) captures of the probe in several coefficient states + the Kelvin preset for comparison
    actor = spawn(probe)
    data["probe_body_constraints_after_tests"] = constraints(probe)
    scene.show_only(actor, [actor])
    yield from warmup()
    yield from take(scene, face_shots("probe_base_", PB_FACE_CENTER))
    if kel and len(kel) == len(base_c):
        for label, values in (("kelvin_full", kel), ("kelvin_keep_head10", base_c[:10] + kel[10:]),
                              ("kelvin_half", [b + 0.5 * (k - b) for b, k in zip(base_c, kel)])):
            set_coeffs(probe, values)
            yield from warmup(90, 4.0)
            yield from take(scene, face_shots(f"probe_{label}_", PB_FACE_CENTER))
        set_coeffs(probe, base_c)
    # Kelvin preset itself: face centre from its landmarks with the offset that maps the base landmark centroid
    # onto the builder's face centre
    if "Kelvin" in presets and presets["Kelvin"]["landmarks"] and base_lm:
        cb, ck = centroid(base_lm), centroid(presets["Kelvin"]["landmarks"])
        off = [PB_FACE_CENTER[i] - cb[i] for i in range(3)]
        kc = (ck[0] + off[0], ck[1] + off[1], ck[2] + off[2])
        data["kelvin_face_center"] = kc
        kdup = scratch_dup(f"{PRESET_SRC}/Kelvin", f"{SCRATCH}/PRE_Kelvin")
        open_edit(kdup)
        kactor = spawn(kdup)
        scene.show_only(kactor, [actor, kactor])
        yield from warmup()
        yield from take(scene, face_shots("probe_preset_Kelvin_", kc))
    step("probe done")


def main() -> None:
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n===== pb_face_design.py mode={MODE} attempt={ATTEMPT} {_now()} =====\n")
    assert_locks()
    if not REPORT["engine"].startswith("5.8"):
        raise RuntimeError(f"expected UE 5.8.x, got {REPORT['engine']}")
    REPORT["sha_start"] = {"MH_MaleBase": sha256(BASELINE_UASSET), "MH_PlayerBase": sha256(BASE_UASSET)}
    scene = Scene()
    step("scene ready")
    if MODE == "probe":
        gen = probe_job(scene)
    elif MODE == "build":
        from pb_face_build import build_job  # noqa: E402 (sibling module, same folder)
        gen = build_job(scene, types.SimpleNamespace(**globals()))
    elif MODE == "verify":
        from pb_face_build import verify_job  # noqa: E402
        gen = verify_job(scene, types.SimpleNamespace(**globals()))
    elif MODE == "explore":
        from pb_face_build import explore_job  # noqa: E402
        gen = explore_job(scene, types.SimpleNamespace(**globals()))
    else:
        raise ValueError(f"unknown PB_FACE_MODE {MODE}")
    Runner(scene, gen).start()


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
        REPORT["sha_end"] = {"MH_MaleBase": sha256(BASELINE_UASSET), "MH_PlayerBase": sha256(BASE_UASSET)}
        REPORT["protected_assets_unchanged"] = REPORT["sha_end"] == REPORT.get("sha_start")
        REPORT["status"] = "done" if success else "failed"
        REPORT["finished_utc"] = _now()
        step("STATUS " + REPORT["status"], protected_unchanged=REPORT["protected_assets_unchanged"])
        ue.SystemLibrary.quit_editor()


try:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
except NameError:
    sys.path.insert(0, str(ROOT / "Scripts/MetaHuman"))

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
