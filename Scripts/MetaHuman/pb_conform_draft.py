"""pb_conform_draft.py -- UNTESTED DRAFT. Written by the API-scout pass and never executed.

Turns our own PlayerBase body mesh into /Game/Characters/MetaHumans/MH_PlayerBase with the
MetaHuman "From Custom Mesh" solver (UMetaHumanCharacterEditorSubsystem::ConformToTargetMeshes),
then renders real SceneCapture previews of both the input mesh and the conformed MetaHuman.

Sources this follows (UE 5.8.3, read on disk):
  * Epic's example  Engine/Plugins/MetaHuman/MetaHumanCharacter/Content/Python/examples/
                    example_conform_from_custom_mesh.py  (+ test_conform_from_custom_mesh.py)
  * Subsystem       MetaHumanCharacterEditor/Public/MetaHumanCharacterEditorSubsystem.h  (L1786-1869)
  * UI tool flow    MetaHumanCharacterEditor/Private/Tools/MetaHumanCharacterEditorMeshImportTool.cpp
                    (StartMeshConform L716, auto-solve pipeline names L763-786, Shutdown L1120)
  * Auto framing    Tools/MetaHumanCharacterEditorMeshTargetContourMechanic.cpp (L382-430, L762-828)
  * FBX import      the legacy-FBX pattern already proven in Scripts/BlackCloak/unreal_recolor_setup.py

Nothing here signs in or calls Epic's cloud. It never calls request_auto_rigging or
request_texture_sources (those are the only cloud calls; they need an Epic sign-in).
It never loads or edits /Game/Characters/MetaHumans/MH_MaleBase (the comparison baseline).

LAUNCH (by the launching agent, one UnrealEditor process on CharacterLab at a time):
  preflight (PowerShell):
    Get-Process UnrealEditor* -ErrorAction SilentlyContinue      # must return nothing
    (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1MB  # GB free, must be >= 8
  run:
    & "C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" `
      "C:/Users/Cody/Desktop/Blender_Projects/Exports/CharacterLab/Unreal/CharacterLab.uproject" `
      -ExecutePythonScript="C:/Users/Cody/Desktop/Blender_Projects/Scripts/MetaHuman/pb_conform_draft.py" `
      -RenderOffscreen -Unattended -NoSplash -NoSound -NoTextureStreaming `
      -NoMetaHumanAccountPortalLoginFallback `
      -abslog="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base/pb_conform.log"
  afterwards: Get-Process UnrealEditor* must be empty again (the script calls quit_editor).
  Do NOT use -nullrhi: face tracking and preview captures need a real RHI (-RenderOffscreen is
  the configuration Codex's runs already proved for try_add_object_to_edit + SceneCapture2D).

ENVIRONMENT OPTIONS (all optional)
  PB_MODE            combined (default) | body_only. body_only needs PB_FBX = a headless body mesh;
                     the head then stays MetaHuman-generic (most IP-distant option).
  PB_FBX             input FBX (default WorkFiles/MetaHuman/player_base/conform_input/PB_Body_ForConform.fbx)
  PB_ALBEDO          albedo PNG for the input mesh's preview material (helps face tracking)
  PB_TRACK_FACE      1 (default) = render the input head and run TrackFaceLandmarksFromImage
  PB_TRACK_RES       square tracking image size in px (default 1024; Epic's default is 2048)
  PB_TRACK_FILL      frame size / head size for tracking framing (default 2.0, Epic's value)
  PB_ESTIMATE_JOINTS 1 = bEstimateBodyJointsFromMesh (Epic's example uses 1, the UI tool uses 0)
  PB_KEYPOINTS_JSON  JSON {"<MetaHuman body vertex index>": [x, y, z] (UE cm, mesh space)}
  PB_EXPORT_POSED_DNA 1 (default) = write PB_PlayerBase_Posed.dna next to the report
  PB_SHOW_ITERATIONS 1 = keep mh.Character.FromCustomMeshImportShowIterations on (default off)
  PB_LUMEN           1 = keep project Lumen/AO settings for preview shots (default 0 = Codex's
                     proven simple-lighting console settings). Use for the black-eye A/B test.
  PB_INTERACTIVE     1 = do not quit the editor at the end
  PB_MAX_MINUTES     wall-clock cap for the whole run (default 40)
"""
from __future__ import annotations

import datetime
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import unreal as ue

# --------------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------------
ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/MetaHuman/player_base"
INPUT_DIR = OUT / "conform_input"
CAPTURES = OUT / "captures"
REPORT_PATH = OUT / "pb_conform_report.json"


def _env_flag(name: str, default: bool) -> bool:
    return os.environ.get(name, "1" if default else "0").strip() == "1"


MODE = os.environ.get("PB_MODE", "combined").strip().lower()
if MODE not in ("combined", "body_only"):
    raise ValueError(f"PB_MODE must be 'combined' or 'body_only', got {MODE!r}")
if MODE == "body_only" and not os.environ.get("PB_FBX"):
    raise ValueError("PB_MODE=body_only needs PB_FBX pointing at a headless body mesh")

FBX_PATH = Path(os.environ.get("PB_FBX", str(INPUT_DIR / "PB_Body_ForConform.fbx")))
ALBEDO_PATH = Path(os.environ.get("PB_ALBEDO", str(INPUT_DIR / "PB_Body_Albedo.png")))
TRACK_FACE = _env_flag("PB_TRACK_FACE", True) and MODE == "combined"
TRACK_RES = int(os.environ.get("PB_TRACK_RES", "1024"))
TRACK_FILL = float(os.environ.get("PB_TRACK_FILL", "2.0"))
ESTIMATE_JOINTS = _env_flag("PB_ESTIMATE_JOINTS", False)
KEYPOINTS_JSON = os.environ.get("PB_KEYPOINTS_JSON", "").strip()
EXPORT_POSED_DNA = _env_flag("PB_EXPORT_POSED_DNA", True)
SHOW_ITERATIONS = _env_flag("PB_SHOW_ITERATIONS", False)
KEEP_LUMEN = _env_flag("PB_LUMEN", False)
INTERACTIVE = _env_flag("PB_INTERACTIVE", False)
MAX_SECONDS = float(os.environ.get("PB_MAX_MINUTES", "40")) * 60.0

CHAR_DIR = "/Game/Characters/MetaHumans"
CHAR_NAME = "MH_PlayerBase"
CHAR_PATH = f"{CHAR_DIR}/{CHAR_NAME}"
BASELINE_PATH = f"{CHAR_DIR}/MH_MaleBase"  # comparison baseline: never loaded, never touched
INPUT_PKG = "/Game/PlayerBase/ConformInput"
MESH_NAME = "SM_PlayerBase_ConformInput" + ("" if MODE == "combined" else "_BodyOnly")
TEX_NAME = "T_PlayerBase_ConformAlbedo"
MAT_NAME = "M_PlayerBase_ConformPreview"
POSED_DNA_NAME = "PB_PlayerBase_Posed"
FORBIDDEN_TOKENS = ("jinmuwon", "muwon", "mu-won", "mu_won")

WARMUP_FRAMES = 120
SETTLE_FRAMES = 45
SETTLE_SECONDS = 1.5
SHOT_W, SHOT_H = 1000, 1200

T0 = time.monotonic()


# --------------------------------------------------------------------------------------------
# Report / guards
# --------------------------------------------------------------------------------------------
def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


REPORT: dict = {
    "script": "Scripts/MetaHuman/pb_conform_draft.py",
    "untested_draft": True,
    "engine": ue.SystemLibrary.get_engine_version(),
    "mode": MODE,
    "input_fbx": str(FBX_PATH),
    "character": CHAR_PATH,
    "status": "starting",
    "started_utc": _now(),
    "events": [],
    "captures": [],
}


def checkpoint(status: str, **extra) -> None:
    REPORT["status"] = status
    REPORT.update(extra)
    REPORT["events"].append({"utc": _now(), "t_s": round(time.monotonic() - T0, 2), "status": status})
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(REPORT, indent=2, default=str), encoding="utf-8")
    ue.log("PB_CONFORM " + status)


def assert_clean_names(*names: str) -> None:
    """New asset names must use 'PlayerBase' and never reference the third-party character."""
    for name in names:
        low = str(name).lower()
        bad = [t for t in FORBIDDEN_TOKENS if t in low]
        if bad:
            raise ValueError(f"Refusing name {name!r}: contains {bad}")


def assert_locks() -> None:
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock  # stdlib-only outside Blender (see Scripts/pipeline/__init__.py)

    lock.assert_owner("MH_PlayerBase", "claude")


def unwrap(result):
    """UFUNCTIONs returning bool + out-params come back as None (false) or the out value(s).

    PyGenUtil.cpp L1161: 'the main return value is a bool, we return None (for false) or the
    (potentially packed) return value without the bool'. Epic's example also tolerates a 1-tuple.
    """
    if isinstance(result, tuple) and len(result) == 1:
        return result[0]
    return result


# --------------------------------------------------------------------------------------------
# Content helpers
# --------------------------------------------------------------------------------------------
def save(asset) -> None:
    if not ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {asset.get_path_name()}")


def import_fbx_static(fbx: Path, dest_pkg: str, name: str) -> ue.StaticMesh:
    """Legacy FBX importer (Interchange FBX off), static mesh, no materials. The conform only
    needs LOD0 MeshDescription positions + triangles (GetMeshDataForConforming), so a
    StaticMesh is enough; a SkeletalMesh is also accepted but adds nothing for arbitrary topology."""
    ue.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    ui = ue.FbxImportUI()
    for key, value in dict(automated_import_should_detect_type=False, import_as_skeletal=False,
                           import_mesh=True, import_materials=False, import_textures=False,
                           import_animations=False, create_physics_asset=False).items():
        ui.set_editor_property(key, value)
    ui.set_editor_property("mesh_type_to_import", ue.FBXImportType.FBXIT_STATIC_MESH)
    data = ui.get_editor_property("static_mesh_import_data")
    for key, value in dict(combine_meshes=True, auto_generate_collision=False,
                           generate_lightmap_u_vs=False, import_mesh_lods=False,
                           normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                           convert_scene=True, convert_scene_unit=True, force_front_x_axis=False,
                           import_uniform_scale=1.0).items():
        data.set_editor_property(key, value)
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(fbx), destination_path=dest_pkg, destination_name=name,
                           automated=True, replace_existing=True, replace_existing_settings=True,
                           save=True, factory=ue.FbxFactory(), options=ui).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = ue.load_asset(f"{dest_pkg}/{name}")
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError(f"FBX import did not produce a StaticMesh at {dest_pkg}/{name}")
    return mesh


def import_texture(png: Path, dest_pkg: str, name: str):
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(png), destination_path=dest_pkg, destination_name=name,
                           automated=True, replace_existing=True, save=True).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = ue.load_asset(f"{dest_pkg}/{name}")
    if not isinstance(tex, ue.Texture2D):
        raise RuntimeError(f"texture import failed: {png}")
    tex.set_editor_property("srgb", True)
    save(tex)
    return tex


def make_preview_material(tex):
    """Plain lit material for the INPUT mesh only (so the face tracker sees brows/lips/eyes)."""
    path = f"{INPUT_PKG}/{MAT_NAME}"
    if ue.EditorAssetLibrary.does_asset_exist(path):
        mat = ue.load_asset(path)
    else:
        mat = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            MAT_NAME, INPUT_PKG, ue.Material, ue.MaterialFactoryNew())
    mel = ue.MaterialEditingLibrary
    mel.delete_all_material_expressions(mat)
    if tex is not None:
        node = mel.create_material_expression(mat, ue.MaterialExpressionTextureSample, -400, 0)
        node.set_editor_property("texture", tex)
        mel.connect_material_property(node, "RGB", ue.MaterialProperty.MP_BASE_COLOR)
    else:
        node = mel.create_material_expression(mat, ue.MaterialExpressionConstant3Vector, -400, 0)
        node.set_editor_property("constant", ue.LinearColor(0.45, 0.32, 0.26, 1.0))
        mel.connect_material_property(node, "", ue.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, ue.MaterialExpressionConstant, -400, 250)
    rough.set_editor_property("r", 0.6)
    mel.connect_material_property(rough, "", ue.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    save(mat)
    return mat


def mesh_stats(verts) -> dict:
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    zs = [v.z for v in verts]
    zmin, zmax = min(zs), max(zs)
    height = zmax - zmin
    # facing: toes stick out further in front of the shin than the heel sticks out behind it
    sole = [v.y for v in verts if v.z < zmin + 0.02 * height]
    shin = [v.y for v in verts if zmin + 0.10 * height < v.z < zmin + 0.14 * height]
    facing = "unknown"
    if sole and shin:
        shin_mean = sum(shin) / len(shin)
        facing = "+Y" if (max(sole) - shin_mean) > (shin_mean - min(sole)) else "-Y"
    # head = everything in the top 13% (A-pose hands sit far below that)
    head = [v for v in verts if v.z >= zmax - 0.13 * height]
    hx = [v.x for v in head]
    hy = [v.y for v in head]
    hz = [v.z for v in head]
    return {
        "vertex_count": len(verts),
        "bounds_min": [min(xs), min(ys), zmin],
        "bounds_max": [max(xs), max(ys), zmax],
        "height_cm": height,
        "facing": facing,
        "head_center": [(min(hx) + max(hx)) / 2, (min(hy) + max(hy)) / 2, (min(hz) + max(hz)) / 2],
        "head_size": [max(hx) - min(hx), max(hy) - min(hy), max(hz) - min(hz)],
    }


def load_keypoints() -> dict:
    if not KEYPOINTS_JSON:
        return {}
    raw = json.loads(Path(KEYPOINTS_JSON).read_text(encoding="utf-8"))
    return {int(k): ue.Vector3f(float(v[0]), float(v[1]), float(v[2])) for k, v in raw.items()}


def get_or_create_character() -> ue.MetaHumanCharacter:
    assert CHAR_PATH != BASELINE_PATH
    if ue.EditorAssetLibrary.does_asset_exist(CHAR_PATH):
        character = ue.load_asset(CHAR_PATH)
        REPORT["character_created"] = False
    else:
        character = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            asset_name=CHAR_NAME, package_path=CHAR_DIR, asset_class=ue.MetaHumanCharacter,
            factory=ue.new_object(type=ue.MetaHumanCharacterFactoryNew))
        REPORT["character_created"] = True
    if not isinstance(character, ue.MetaHumanCharacter):
        raise RuntimeError(f"could not create/load {CHAR_PATH}")
    # "Skin" preview material instead of the default "Topology" guide material. It is read when
    # the character is added for edit (MetaHumanCharacterEditorSubsystem.cpp L1142), so set it first.
    character.set_editor_property("preview_material_type", ue.MetaHumanCharacterSkinPreviewMaterial.EDITABLE)
    return character


# --------------------------------------------------------------------------------------------
# Scene / capture helpers
# --------------------------------------------------------------------------------------------
class Scene:
    def __init__(self):
        self.world = ue.EditorLoadingAndSavingUtils.new_blank_map(False)  # untitled, never saved
        if self.world is None:
            self.world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self._lights_and_backdrop()
        self.camera = self.spawn(ue.SceneCapture2D)
        self.capture = self.camera.get_component_by_class(ue.SceneCaptureComponent2D)
        self.rt_track = ue.RenderingLibrary.create_render_target2d(
            self.world, TRACK_RES, TRACK_RES, ue.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        self.rt_shot = ue.RenderingLibrary.create_render_target2d(
            self.world, SHOT_W, SHOT_H, ue.TextureRenderTargetFormat.RTF_RGBA8)
        self.rt_shot.set_editor_property("target_gamma", 2.2)
        cap = self.capture
        cap.set_editor_property("capture_every_frame", True)          # TAA/TSR history converges
        cap.set_editor_property("always_persist_rendering_state", True)
        pp = cap.get_editor_property("post_process_settings")
        for key, value in [("override_auto_exposure_method", True),
                           ("auto_exposure_method", ue.AutoExposureMethod.AEM_MANUAL),
                           ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0),
                           ("override_auto_exposure_apply_physical_camera_exposure", True),
                           ("auto_exposure_apply_physical_camera_exposure", False),
                           ("override_vignette_intensity", True), ("vignette_intensity", 0.0)]:
            pp.set_editor_property(key, value)
        cap.set_editor_property("post_process_settings", pp)
        self.use_shot_target()

    def spawn(self, cls, location=(0, 0, 0), rotation=(0, 0, 0)):
        return self.actors.spawn_actor_from_class(cls, ue.Vector(*location), ue.Rotator(*rotation))

    def _lights_and_backdrop(self) -> None:
        # Same rig as Codex's create_male_preview.py (it rendered), key light now casts shadows.
        for i, (rot, intensity, color) in enumerate([((-30, -125, 0), 5, (1, .94, .88)),
                                                     ((-15, -30, 0), 3, (.88, .93, 1)),
                                                     ((-30, 90, 0), 2, (1, 1, 1))]):
            light = self.spawn(ue.DirectionalLight, rotation=rot)
            light.light_component.set_intensity(intensity)
            light.light_component.set_light_color(ue.LinearColor(*color, 1))
            light.light_component.set_cast_shadows(i == 0)
        backdrop = self.spawn(ue.StaticMeshActor)
        backdrop.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Sphere"))
        backdrop.set_actor_scale3d(ue.Vector(50, 50, 50))
        backdrop.static_mesh_component.set_cast_shadow(False)
        mat = ue.new_object(ue.Material)  # transient, never saved
        mat.set_editor_property("two_sided", True)
        mat.set_editor_property("shading_model", ue.MaterialShadingModel.MSM_UNLIT)
        node = ue.MaterialEditingLibrary.create_material_expression(mat, ue.MaterialExpressionConstant3Vector)
        node.set_editor_property("constant", ue.LinearColor(.18, .18, .18, 1))
        ue.MaterialEditingLibrary.connect_material_property(node, "", ue.MaterialProperty.MP_EMISSIVE_COLOR)
        ue.MaterialEditingLibrary.recompile_material(mat)
        backdrop.static_mesh_component.set_material(0, mat)
        sky = self.spawn(ue.SkyLight)
        sky.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        sky.light_component.set_intensity(2)
        sky.light_component.recapture_sky()
        if not KEEP_LUMEN:
            for command in ["r.DynamicGlobalIlluminationMethod 0", "r.ReflectionMethod 0",
                            "r.AmbientOcclusionLevels 0", "r.DistanceFieldAO 0",
                            "r.RayTracing.ForceAllRayTracingEffects 0", "r.AntiAliasingMethod 2"]:
                ue.SystemLibrary.execute_console_command(self.world, command)

    def use_track_target(self) -> None:
        # Mirrors UMeshTargetContourMechanic::Setup: sRGB 8-bit target + FinalToneCurveHDR.
        self.capture.set_editor_property("texture_target", self.rt_track)
        self.capture.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_TONE_CURVE_HDR)

    def use_shot_target(self) -> None:
        self.capture.set_editor_property("texture_target", self.rt_shot)
        self.capture.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)

    def hide_only(self, actors) -> None:
        self.capture.set_editor_property("hidden_actors", [a for a in actors if a is not None])

    def aim(self, location, look_at, fov_deg: float) -> None:
        loc = ue.Vector(*location)
        target = ue.Vector(*look_at)
        self.camera.set_actor_location_and_rotation(
            loc, ue.MathLibrary.find_look_at_rotation(loc, target), False, False)
        self.capture.set_editor_property("fov_angle", float(fov_deg))

    def view_info(self, width: int, height: int) -> ue.MinimalViewInfo:
        info = ue.MinimalViewInfo()
        info.location = self.camera.get_actor_location()
        info.rotation = self.camera.get_actor_rotation()
        info.fov = self.capture.get_editor_property("fov_angle")  # horizontal FOV, like the tool
        info.aspect_ratio = float(width) / float(height)
        info.projection_mode = ue.CameraProjectionMode.PERSPECTIVE
        return info

    def export(self, rt, name: str) -> str:
        CAPTURES.mkdir(parents=True, exist_ok=True)
        ue.RenderingLibrary.export_render_target(self.world, rt, str(CAPTURES), name)
        path = str(CAPTURES / name)
        REPORT["captures"].append(path)
        return path


def shot_list(prefix: str, height: float, face_center) -> list:
    """(name, camera location, look-at, horizontal fov). Characters face +Y in UE mesh space."""
    fx, fy, fz = face_center
    d = 110.0
    a = math.radians(35.0)
    return [
        (prefix + "Body.png", (0.0, 390.0, height * 0.5), (0.0, 0.0, height * 0.5), 30.0),
        (prefix + "Face.png", (fx, fy + d, fz), (fx, fy, fz - 4.0), 30.0),
        (prefix + "FaceThreeQuarter.png", (fx - d * math.sin(a), fy + d * math.cos(a), fz), (fx, fy, fz - 4.0), 30.0),
        (prefix + "FaceProfile.png", (fx - d, fy, fz), (fx, fy, fz - 4.0), 30.0),
    ]


# --------------------------------------------------------------------------------------------
# Tick-driven runner (rendering needs real frames between steps)
# --------------------------------------------------------------------------------------------
class Runner:
    def __init__(self, subsystem, character, mesh, verts, tris, stats, scene, target_actor):
        self.mhs = subsystem
        self.character = character
        self.mesh = mesh
        self.verts = verts
        self.tris = tris
        self.stats = stats
        self.scene = scene
        self.target_actor = target_actor
        self.mh_actor = None
        self.tracking = None  # (curves, view_info, image_size)
        self.handle = None
        self.busy = False  # re-entrancy guard: slow tasks inside save etc. pump Slate
        self.done = False
        self.stage = ""
        self.stage_frame = 0
        self.stage_t0 = time.monotonic()
        self.shots: list = []
        self.shot_index = 0
        self.after_shots = ""

    # -- plumbing ------------------------------------------------------------------------
    def start(self) -> None:
        self.goto("warmup_target")
        self.handle = ue.register_slate_post_tick_callback(self.tick)
        ue.EditorPythonScripting.set_keep_python_script_alive(True)

    def goto(self, stage: str) -> None:
        self.stage = stage
        self.stage_frame = 0
        self.stage_t0 = time.monotonic()
        checkpoint(stage)

    def settled(self) -> bool:
        return self.stage_frame >= SETTLE_FRAMES and time.monotonic() - self.stage_t0 >= SETTLE_SECONDS

    def tick(self, _delta: float) -> None:
        if self.busy or self.done:
            return
        self.busy = True
        try:
            self.stage_frame += 1
            if time.monotonic() - T0 > MAX_SECONDS:
                raise TimeoutError(f"run exceeded {MAX_SECONDS / 60:.0f} min in stage {self.stage}")
            getattr(self, "stage_" + self.stage)()
        except Exception:
            REPORT["error"] = traceback.format_exc()
            ue.log_error(REPORT["error"])
            self.finish(success=False)
        finally:
            self.busy = False

    def begin_shots(self, shots: list, after: str) -> None:
        self.shots = shots
        self.shot_index = 0
        self.after_shots = after
        self.scene.use_shot_target()
        name, loc, look, fov = shots[0]
        self.scene.aim(loc, look, fov)
        self.goto("shots")

    # -- stages --------------------------------------------------------------------------
    def stage_warmup_target(self) -> None:
        if self.stage_frame in (30, WARMUP_FRAMES - 10):
            ue.AutomationLibrary.finish_loading_before_screenshot()
        if self.stage_frame < WARMUP_FRAMES:
            return
        if TRACK_FACE:
            self.aim_tracking_camera()
            self.goto("track")
        else:
            self.target_shots()

    def aim_tracking_camera(self) -> None:
        """Head auto-framing like TrackFaceWithAutoFraming, but with the head box taken from the
        real vertices (top 13%) instead of Epic's 15%-of-bounds heuristic (their X extent includes
        the A-pose arms). Camera sits on +Y looking at the face."""
        cx, cy, cz = self.stats["head_center"]
        sx, sy, sz = self.stats["head_size"]
        fov = 35.0  # Epic clamps the auto-framing FOV to [35, 110]
        frame = TRACK_FILL * max(sx, sz)
        dist = (frame * 0.5) / math.tan(math.radians(fov * 0.5)) + sy * 0.5
        head_size = math.sqrt((sx / 2) ** 2 + (sy / 2) ** 2 + (sz / 2) ** 2)
        self.scene.hide_only([self.mh_actor])
        self.scene.use_track_target()
        self.scene.aim((cx, cy + dist, cz + 0.2 * head_size), (cx, cy, cz), fov)
        REPORT["tracking_camera"] = {"distance_cm": dist, "fov": fov, "frame_cm": frame}

    def stage_track(self) -> None:
        if not self.settled():
            return
        scene = self.scene
        scene.export(scene.rt_track, "track_input.png")
        pixels = unwrap(ue.RenderingLibrary.read_render_target(scene.world, scene.rt_track, True))
        curves = None
        if pixels is not None and len(pixels) == TRACK_RES * TRACK_RES:
            curves = unwrap(self.mhs.track_face_landmarks_from_image(pixels, TRACK_RES, TRACK_RES))
        if curves:
            info = scene.view_info(TRACK_RES, TRACK_RES)
            self.tracking = (curves, info, ue.IntPoint(TRACK_RES, TRACK_RES))
            REPORT["face_tracking"] = {"status": "ok",
                                       "curves": {str(k): len(v.tracking_points) for k, v in curves.items()}}
        else:
            # The UI tool also continues without tracking when auto-tracking fails (L729-735).
            REPORT["face_tracking"] = {"status": "failed_or_no_face",
                                       "pixels_read": 0 if pixels is None else len(pixels)}
        checkpoint("tracked")
        self.target_shots()

    def target_shots(self) -> None:
        cx, cy, cz = self.stats["head_center"]
        self.scene.hide_only([self.mh_actor])
        self.begin_shots(shot_list("target_", self.stats["height_cm"], (cx, cy, cz - 3.0)), "conform")

    def stage_shots(self) -> None:
        if not self.settled():
            return
        name, _loc, _look, _fov = self.shots[self.shot_index]
        self.scene.export(self.scene.rt_shot, name)
        self.shot_index += 1
        if self.shot_index < len(self.shots):
            _name, loc, look, fov = self.shots[self.shot_index]
            self.scene.aim(loc, look, fov)
            self.stage_frame = 0
            self.stage_t0 = time.monotonic()
        else:
            self.goto(self.after_shots)

    def stage_conform(self) -> None:
        mhs = self.mhs
        character = self.character
        if not SHOW_ITERATIONS:
            ue.SystemLibrary.execute_console_command(None, "mh.Character.FromCustomMeshImportShowIterations 0")

        target = ue.ConformTargetMesh()
        target.target_parts_type = (ue.TargetPartsType.COMBINED if MODE == "combined"
                                    else ue.TargetPartsType.BODY_ONLY)
        target.body_vertices = self.verts
        target.body_vertex_indices = self.tris

        solve = ue.BodyConformSolveSettings()  # C++ defaults == the tool's Advanced defaults
        solve.pipeline_name = "combined" if MODE == "combined" else "body_only"  # tool L763-786

        params = ue.ConformTargetParams()
        params.conform_target_mesh = target
        params.auto_solve = True
        params.estimate_body_joints_from_mesh = ESTIMATE_JOINTS
        params.body_conform_solve_settings = solve
        keypoints = load_keypoints()
        if keypoints:
            params.key_point_targets = keypoints
        if self.tracking:
            curves, info, size = self.tracking
            params.curve_tracking_points = curves
            params.camera_view_info = info
            params.image_size = size

        key = ue.MetaHumanCharacterTargetMeshKey()
        if MODE == "combined":
            key.combined_mesh = self.mesh
        else:
            key.body_mesh = self.mesh

        REPORT["preset_body_keypoints"] = {str(k): int(v) for k, v in
                                           mhs.get_preset_body_key_points(character).items()}
        REPORT["conform_params"] = {"auto_solve": True, "pipeline": solve.pipeline_name,
                                    "estimate_joints": ESTIMATE_JOINTS, "keypoints": len(keypoints),
                                    "face_curves": 0 if not self.tracking else len(self.tracking[0])}
        checkpoint("conform_running")
        t = time.monotonic()
        # Blocking: runs the titan solver on a worker thread and pumps the game-thread task graph
        # + FTSBackgroundableTicker until done (MetaHumanCharacterEditorSubsystem.cpp L7794-7801).
        ok = mhs.conform_to_target_meshes(character, key, params)
        REPORT["conform_seconds"] = round(time.monotonic() - t, 1)
        if not ok:
            raise RuntimeError("conform_to_target_meshes returned False (see LogMetaHumanCoreTechLib /"
                               " LogMetaHumanCharacterEditor lines in the log)")
        checkpoint("conform_solved")

        if EXPORT_POSED_DNA:
            dna = ue.MetaHumanPosedDNAExportParams()
            dna.target_mesh_key = key
            dna.external_path = str(OUT)  # .dna file on disk only; project_path left empty
            dna.asset_name = POSED_DNA_NAME
            dna.overwrite_existing_assets = True
            ue.MetaHumanCharacterExportBlueprintLibrary.export_posed_dna(character, dna)
            REPORT["posed_dna"] = str(OUT / (POSED_DNA_NAME + ".dna"))

        # What the tool does on Shutdown (L1120-1123): body back to MetaHuman A-pose, face refit.
        mhs.commit_posed_state_as_a_pose(character, key)
        constraints = mhs.get_body_constraints(character, False)
        REPORT["measurements_after"] = {str(c.name): round(float(c.target_measurement), 2)
                                        for c in constraints}
        REPORT["face_model_coefficient_count"] = len(mhs.get_face_model_coefficients(character))
        REPORT["face_landmark_count"] = len(mhs.get_face_landmarks(character))
        save(character)
        checkpoint("conform_committed_and_saved")

        mhs.assemble_for_preview(character)
        self.mh_actor = mhs.spawn_meta_human_actor(character, True)
        if self.mh_actor is None:
            raise RuntimeError("spawn_meta_human_actor returned None")
        self.scene.hide_only([self.target_actor])
        self.goto("warmup_mh")

    def stage_warmup_mh(self) -> None:
        if self.stage_frame in (30, WARMUP_FRAMES - 10):
            ue.AutomationLibrary.finish_loading_before_screenshot()
        if self.stage_frame < WARMUP_FRAMES:
            return
        origin, extent = self.mh_actor.get_actor_bounds(False)
        top = origin.z + extent.z
        height = float(REPORT.get("measurements_after", {}).get("Height", top))
        cx, cy, _ = self.stats["head_center"]
        face_z = top - 0.085 * height
        REPORT["mh_bounds"] = {"origin": [origin.x, origin.y, origin.z], "extent": [extent.x, extent.y, extent.z]}
        self.begin_shots(shot_list("mh_", height, (cx, cy, face_z)), "finish")

    def stage_finish(self) -> None:
        self.finish(success=True)

    # -- teardown --------------------------------------------------------------------------
    def finish(self, success: bool) -> None:
        if self.done:
            return
        self.done = True
        if self.handle is not None:  # unregister FIRST so nested Slate ticks cannot re-enter
            ue.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        try:
            if success:
                save(self.character)
            if self.mhs.is_object_added_for_editing(self.character):
                self.mhs.remove_object_to_edit(self.character)
            ue.EditorLoadingAndSavingUtils.new_blank_map(False)  # drop the dirty untitled map
        except Exception:
            REPORT["teardown_error"] = traceback.format_exc()
            success = False
        checkpoint("done" if success else "failed", finished_utc=_now())
        if not INTERACTIVE:
            ue.SystemLibrary.quit_editor()


# --------------------------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------------------------
def main() -> None:
    assert_locks()
    assert_clean_names(CHAR_PATH, INPUT_PKG, MESH_NAME, TEX_NAME, MAT_NAME, POSED_DNA_NAME)
    if not REPORT["engine"].startswith("5.8"):
        raise RuntimeError(f"expected UE 5.8.x, got {REPORT['engine']}")
    if not FBX_PATH.is_file():
        raise FileNotFoundError(FBX_PATH)
    checkpoint("preflight_ok")

    mhs = ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
    scene = Scene()

    mesh = import_fbx_static(FBX_PATH, INPUT_PKG, MESH_NAME)
    data = unwrap(mhs.get_mesh_data_for_conforming(mesh))
    if not data:
        raise RuntimeError("get_mesh_data_for_conforming returned nothing")
    verts, tris = data[0], data[1]
    if not verts or not tris or len(tris) % 3:
        raise RuntimeError(f"bad mesh data: {len(verts)} verts, {len(tris)} indices")
    stats = mesh_stats(verts)
    stats["triangle_count"] = len(tris) // 3
    REPORT["input_mesh"] = {"asset": mesh.get_path_name(), **stats}
    if not 150.0 <= stats["height_cm"] <= 220.0:
        raise RuntimeError(f"input height {stats['height_cm']:.1f} cm: wrong units? (expected ~185.8)")
    if abs(stats["bounds_min"][2]) > 3.0:
        REPORT.setdefault("warnings", []).append("soles are not at Z=0 in mesh space")
    if stats["facing"] != "+Y":
        REPORT.setdefault("warnings", []).append(
            f"input seems to face {stats['facing']}; MetaHumans face +Y. Tracking camera assumes +Y.")
    checkpoint("mesh_imported")

    tex = import_texture(ALBEDO_PATH, INPUT_PKG, TEX_NAME) if ALBEDO_PATH.is_file() else None
    material = make_preview_material(tex)
    target_actor = scene.actors.spawn_actor_from_object(mesh, ue.Vector(0, 0, 0), ue.Rotator(0, 0, 0))
    component = target_actor.static_mesh_component
    for index in range(component.get_num_materials()):
        component.set_material(index, material)

    character = get_or_create_character()
    save(character)
    if not mhs.try_add_object_to_edit(character):
        raise RuntimeError("try_add_object_to_edit failed (already open elsewhere, or Core Data missing?)")
    checkpoint("character_open_for_editing")

    Runner(mhs, character, mesh, verts, tris, stats, scene, target_actor).start()


try:
    main()
except Exception:
    REPORT["error"] = traceback.format_exc()
    ue.log_error(REPORT["error"])
    try:
        _mhs = ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
        if ue.EditorAssetLibrary.does_asset_exist(CHAR_PATH):
            _char = ue.load_asset(CHAR_PATH)
            if _char is not None and _mhs.is_object_added_for_editing(_char):
                _mhs.remove_object_to_edit(_char)
    except Exception:
        pass
    checkpoint("failed")
    if not INTERACTIVE:
        ue.SystemLibrary.quit_editor()
