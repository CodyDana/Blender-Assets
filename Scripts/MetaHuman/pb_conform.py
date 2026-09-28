"""pb_conform.py -- build /Game/Characters/MetaHumans/MH_PlayerBase from our own body mesh with the
MetaHuman "From Custom Mesh" solver (UE 5.8.3, UMetaHumanCharacterEditorSubsystem::ConformToTargetMeshes),
then capture real SceneCapture previews and dump measurable geometry.

Runs INSIDE UnrealEditor on Exports/CharacterLab/Unreal/CharacterLab.uproject. Launch it with
Scripts/MetaHuman/pb_run_conform.ps1 (preflight: no other UnrealEditor, >= 8 GB RAM free; waits for exit).

What it does (every step goes to WorkFiles/MetaHuman/player_base/conform.log + conform_report.json):
  1. imports conform_input/PB_Body_ForConform.fbx as StaticMesh /Game/PlayerBase/ConformInput/SM_PlayerBase_ConformInput
     (+ albedo texture + a plain lit preview material so the face tracker sees brows/lips/eyes)
  2. creates /Game/Characters/MetaHumans/MH_PlayerBase (MetaHumanCharacterFactoryNew), preview material = Skin
  3. renders the input head from +Y (the tool's auto-framing geometry) and runs TrackFaceLandmarksFromImage
  4. ConformToTargetMeshes: Combined head+body, auto solve, pipeline "combined", Epic's default solver
     settings, bEstimateBodyJointsFromMesh=False (UI tool default), no keypoints unless PB_KEYPOINTS_JSON
  5. exports the posed DNA to disk, spawns the MetaHuman in the solved (posed) state for side-by-side shots and
     a vertex dump, then CommitPosedStateAsAPose (what the tool does on Shutdown), saves the asset
  6. captures the conformed MetaHuman (body front/side/back, face front/3-4/profile, hands), dumps its A-pose
     mesh + bone positions, measures, then captures a scratch DUPLICATE of MH_MaleBase (never saved) with the
     same body camera for comparison. MH_MaleBase itself is only read (duplicated), never opened for edit or saved.

Never signs in, never calls request_auto_rigging / request_texture_sources / build_meta_human (cloud).

ENV (optional): PB_TRACK_FACE=1  PB_TRACK_RES=2048  PB_ESTIMATE_JOINTS=0  PB_KEYPOINTS_JSON=<file>
                PB_RENDER=simple|lumen (default simple = Codex's proven console settings)  PB_BASELINE=1
                PB_RECREATE=1 (delete a MH_PlayerBase left by an earlier failed attempt of THIS script)
                PB_FBX=<path>  PB_ATTEMPT=<label>  PB_MAX_MINUTES=50  PB_INTERACTIVE=0
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

# --------------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------------
ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/MetaHuman/player_base"
INPUT_DIR = OUT / "conform_input"
CAPTURES = OUT / "captures"
DUMPS = OUT / "mesh_dump"
REPORT_PATH = OUT / "conform_report.json"
STEP_LOG = OUT / "conform.log"
BASELINE_UASSET = ROOT / "Exports/CharacterLab/Unreal/Content/Characters/MetaHumans/MH_MaleBase.uasset"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


FBX_PATH = Path(_env("PB_FBX", str(INPUT_DIR / "PB_Body_ForConform.fbx")))
ALBEDO_PATH = INPUT_DIR / "PB_Body_Albedo.png"
TRACK_FACE = _env("PB_TRACK_FACE", "1") == "1"
TRACK_RES = int(_env("PB_TRACK_RES", "2048"))
ESTIMATE_JOINTS = _env("PB_ESTIMATE_JOINTS", "0") == "1"
KEYPOINTS_JSON = _env("PB_KEYPOINTS_JSON", "")
RENDER_MODE = _env("PB_RENDER", "simple").lower()
DO_BASELINE = _env("PB_BASELINE", "1") == "1"
RECREATE = _env("PB_RECREATE", "1") == "1"
ATTEMPT = _env("PB_ATTEMPT", "1")
INTERACTIVE = _env("PB_INTERACTIVE", "0") == "1"
MAX_SECONDS = float(_env("PB_MAX_MINUTES", "50")) * 60.0

CHAR_DIR = "/Game/Characters/MetaHumans"
CHAR_NAME = "MH_PlayerBase"
CHAR_PATH = f"{CHAR_DIR}/{CHAR_NAME}"
BASELINE_PATH = f"{CHAR_DIR}/MH_MaleBase"            # read-only baseline
BASELINE_DUP = "/Game/PlayerBase/Scratch/MH_BaselineCompare"  # in-memory duplicate, never saved
INPUT_PKG = "/Game/PlayerBase/ConformInput"
MESH_NAME = "SM_PlayerBase_ConformInput"
TEX_NAME = "T_PlayerBase_ConformAlbedo"
MAT_NAME = "M_PlayerBase_ConformPreview"
POSED_DNA_NAME = "PB_PlayerBase_Posed"
FORBIDDEN_TOKENS = ("jinmuwon", "muwon", "mu-won", "mu_won")

WARMUP_FRAMES = 150
# (pitch, yaw, roll, intensity lux, colour, casts shadows); characters face +Y, front camera sits on +Y
LIGHT_RIGS = {
    "studio": [(-27.0, -117.0, 0.0, 4.0, (1, .95, .9), True),    # key: from front-right, above
               (-12.0, -58.0, 0.0, 2.0, (.9, .94, 1), False),    # fill: from front-left, low
               (-37.0, 90.0, 0.0, 2.0, (1, 1, 1), False)],       # rim: from behind, above
    "codex": [(-125.0, 0.0, -30.0, 5.0, (1, .94, .88), True),
              (-30.0, 0.0, -15.0, 3.0, (.88, .93, 1), False),
              (90.0, 0.0, -30.0, 2.0, (1, 1, 1), False)],
}
LIGHT_RIG = os.environ.get("PB_RIG", "studio").strip()
ORTHO_RES = 1200
ORTHO_WIDTH = 240.0
ORTHO_CAM_Z = 95.0
CAPTURE_STAGES = ("warmup_target", "track", "shots", "warmup_posed", "warmup_apose", "warmup_baseline")
SETTLE_FRAMES = 45
SETTLE_SECONDS = 1.5
SHOT_W, SHOT_H = 1000, 1200
BODY_CAM_DIST = 380.0
BODY_CAM_Z = 93.0
FACE_CAM_DIST = 70.0
SIMPLE_RENDER_CVARS = ["r.DynamicGlobalIlluminationMethod 0", "r.ReflectionMethod 0", "r.AmbientOcclusionLevels 0",
                       "r.DistanceFieldAO 0", "r.RayTracing.ForceAllRayTracingEffects 0", "r.AntiAliasingMethod 2"]
LUMEN_RENDER_CVARS = ["r.DynamicGlobalIlluminationMethod 1", "r.ReflectionMethod 1", "r.AmbientOcclusionLevels -1",
                      "r.DistanceFieldAO 1", "r.AntiAliasingMethod 2"]

MH_BONES = ["root", "pelvis", "spine_05", "neck_01", "head", "clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r",
            "lowerarm_l", "lowerarm_r", "hand_l", "hand_r", "middle_03_l", "middle_03_r", "thigh_l", "thigh_r",
            "calf_l", "calf_r", "foot_l", "foot_r", "ball_l", "ball_r"]

T0 = time.monotonic()


# --------------------------------------------------------------------------------------------
# Logging / report
# --------------------------------------------------------------------------------------------
def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


REPORT: dict = {
    "script": "Scripts/MetaHuman/pb_conform.py",
    "attempt": ATTEMPT,
    "engine": ue.SystemLibrary.get_engine_version(),
    "input_fbx": str(FBX_PATH),
    "character": CHAR_PATH,
    "options": {"track_face": TRACK_FACE, "track_res": TRACK_RES, "estimate_joints": ESTIMATE_JOINTS,
                "keypoints_json": KEYPOINTS_JSON, "render_mode": RENDER_MODE, "baseline": DO_BASELINE},
    "status": "starting",
    "started_utc": _now(),
    "steps": [],
    "captures": [],
    "warnings": [],
}


def step(msg: str, **extra) -> None:
    """One line in conform.log + the engine log, plus a step entry in the JSON report."""
    t = round(time.monotonic() - T0, 1)
    line = f"{_now()}  +{t:7.1f}s  {msg}"
    if extra:
        line += "  " + json.dumps(extra, default=str)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    ue.log("PB_CONFORM " + line)
    REPORT["steps"].append({"t_s": t, "msg": msg, **extra})
    write_report()


def checkpoint(status: str, **extra) -> None:
    REPORT["status"] = status
    REPORT.update(extra)
    step("STATUS " + status)


def warn(msg: str) -> None:
    REPORT["warnings"].append(msg)
    step("WARNING " + msg)


def write_report() -> None:
    REPORT_PATH.write_text(json.dumps(REPORT, indent=2, default=str), encoding="utf-8")


def assert_clean_names(*names: str) -> None:
    for name in names:
        low = str(name).lower()
        bad = [t for t in FORBIDDEN_TOKENS if t in low]
        if bad:
            raise ValueError(f"Refusing name {name!r}: contains {bad}")


def assert_locks() -> None:
    sys.path.insert(0, str(ROOT / "Scripts"))
    from pipeline import lock  # stdlib-only outside Blender
    lock.assert_owner("MH_PlayerBase", "claude")
    lock.assert_owner("MH_MaleBase", "claude")


def unwrap(result):
    if isinstance(result, tuple) and len(result) == 1:
        return result[0]
    return result


def v3(v) -> list:
    return [round(float(v.x), 3), round(float(v.y), 3), round(float(v.z), 3)]


# --------------------------------------------------------------------------------------------
# Geometry measurement (identical code for the source mesh and the MetaHuman dump)
# --------------------------------------------------------------------------------------------
def _slice_width(pts, z0, z1, xlim=None):
    xs = [p[0] for p in pts if z0 <= p[2] < z1 and (xlim is None or abs(p[0]) < xlim)]
    if len(xs) < 4:
        return None
    return max(xs) - min(xs)


def measure_points(pts, shoulder_z=None) -> dict:
    """pts: list of (x, y, z) in cm, Z up, character faces +Y, X lateral. Returns vertex-derived measures."""
    zs = [p[2] for p in pts]
    zmin, zmax = min(zs), max(zs)
    h = zmax - zmin
    out = {"vertex_count": len(pts), "zmin": round(zmin, 2), "zmax": round(zmax, 2), "height": round(h, 2),
           "x_extent": round(max(p[0] for p in pts) - min(p[0] for p in pts), 2),
           "y_extent": round(max(p[1] for p in pts) - min(p[1] for p in pts), 2)}
    # crotch height (inside-leg length): lowest midline vertex of the torso
    mid = [p[2] for p in pts if abs(p[0]) < 1.0 and zmin + 0.3 * h < p[2] < zmin + 0.65 * h]
    out["crotch_height"] = round(min(mid) - zmin, 2) if mid else None
    # hip breadth: widest 1 cm slice between 44% and 56% of height, arms excluded (|x| < 30 cm)
    best = None
    z = zmin + 0.44 * h
    while z < zmin + 0.56 * h:
        w = _slice_width(pts, z, z + 1.0, xlim=30.0)
        if w is not None and (best is None or w > best[0]):
            best = (w, z)
        z += 0.5
    out["hip_breadth"] = round(best[0], 2) if best else None
    out["hip_breadth_z"] = round(best[1] - zmin, 2) if best else None
    # waist: narrowest slice between 57% and 66% of height, arms excluded (|x| < 25)
    narrow = None
    z = zmin + 0.57 * h
    while z < zmin + 0.66 * h:
        w = _slice_width(pts, z, z + 1.0, xlim=25.0)
        if w is not None and (narrow is None or w < narrow[0]):
            narrow = (w, z)
        z += 0.5
    out["waist_breadth"] = round(narrow[0], 2) if narrow else None
    # shoulder breadth at the shoulder-joint height (bideltoid-ish; arms included on purpose)
    if shoulder_z is not None:
        widths = [w for w in (_slice_width(pts, zz, zz + 1.0) for zz in
                              [shoulder_z - 2.0 + 0.5 * i for i in range(12)]) if w is not None]
        out["shoulder_breadth_at_joint_z"] = round(max(widths), 2) if widths else None
    # head: top-of-head to menton (chin bottom found as the largest front-profile drop into the neck)
    band = [p for p in pts if abs(p[0]) < 1.5 and zmax - 34.0 < p[2] < zmax - 14.0]
    bins = {}
    for p in band:
        k = int((p[2] - (zmax - 34.0)) / 0.5)
        if k not in bins or p[1] > bins[k]:
            bins[k] = p[1]
    keys = sorted(bins)
    best_drop = None
    for i in range(len(keys)):
        upper = [bins[k] for k in keys if keys[i] < k <= keys[i] + 2]  # up to 1 cm above
        lower = [bins[k] for k in keys if keys[i] - 2 <= k < keys[i]]  # up to 1 cm below
        if not upper or not lower:
            continue
        drop = max(upper) - max(lower)
        if best_drop is None or drop > best_drop[0]:
            best_drop = (drop, zmax - 34.0 + keys[i] * 0.5)
    if best_drop:
        out["menton_z"] = round(best_drop[1] - zmin, 2)
        out["head_height_top_to_chin"] = round(zmax - best_drop[1], 2)
        out["chin_neck_profile_drop"] = round(best_drop[0], 2)
    top = [p for p in pts if p[2] > zmax - 22.0 and abs(p[0]) < 12.0]
    if top:
        out["head_breadth_incl_ears"] = round(max(p[0] for p in top) - min(p[0] for p in top), 2)
        out["head_depth_incl_nose"] = round(max(p[1] for p in top) - min(p[1] for p in top), 2)
    return out


def head_frame(pts) -> dict:
    """Head centre/size from the top 13% of the vertices (A-pose hands sit far below that)."""
    zs = [p[2] for p in pts]
    zmin, zmax = min(zs), max(zs)
    head = [p for p in pts if p[2] >= zmax - 0.13 * (zmax - zmin)]
    xs, ys, hz = [p[0] for p in head], [p[1] for p in head], [p[2] for p in head]
    return {"center": [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(hz) + max(hz)) / 2],
            "size": [max(xs) - min(xs), max(ys) - min(ys), max(hz) - min(hz)],
            "front_y": max(ys), "top_z": zmax, "zmin": zmin}


def hand_centers(pts) -> dict:
    """Bounding-box centres of the outermost 18 cm of each arm (the hands in an A-pose)."""
    xmax = max(p[0] for p in pts)
    xmin = min(p[0] for p in pts)
    res = {}
    for label, sel in (("xpos", [p for p in pts if p[0] > xmax - 18.0]),
                       ("xneg", [p for p in pts if p[0] < xmin + 18.0])):
        if sel:
            res[label] = [(min(p[i] for p in sel) + max(p[i] for p in sel)) / 2 for i in range(3)]
    return res


def write_obj(path: Path, pts, tris) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# UE world space, cm, Z up, character faces +Y\n")
        for p in pts:
            fh.write(f"v {p[0]:.4f} {p[1]:.4f} {p[2]:.4f}\n")
        for t in tris:
            fh.write(f"f {t[0] + 1} {t[1] + 1} {t[2] + 1}\n")


def dump_component(component, stem: str):
    """World-space vertices + triangles of a (skinned) mesh component via GeometryScript."""
    dm = ue.new_object(ue.DynamicMesh)
    opts = ue.GeometryScriptCopyMeshFromComponentOptions()
    opts.set_editor_property("want_normals", False)
    opts.set_editor_property("want_tangents", False)
    res = ue.GeometryScript_SceneUtils.copy_mesh_from_component(component, dm, opts, True)
    if isinstance(res, tuple):
        outcome = res[-1]
        if "fail" in str(outcome).lower():
            raise RuntimeError(f"copy_mesh_from_component failed for {component.get_name()}: {outcome}")
    # these UFUNCTIONs return (UDynamicMesh*, out list, out bHasGaps) -> pick the list by type
    pos = ue.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
    pos_list = next(x for x in (pos if isinstance(pos, tuple) else (pos,))
                    if isinstance(x, ue.GeometryScriptVectorList))
    tri = ue.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
    tri_list = next(x for x in (tri if isinstance(tri, tuple) else (tri,))
                    if isinstance(x, ue.GeometryScriptTriangleList))
    gaps = [x for x in (pos if isinstance(pos, tuple) else ()) if isinstance(x, bool)]
    if gaps and gaps[0]:
        raise RuntimeError(f"{component.get_name()}: dynamic mesh has vertex-ID gaps; OBJ indices would be wrong")
    verts = ue.GeometryScript_List.convert_vector_list_to_array(pos_list)
    tris = ue.GeometryScript_List.convert_triangle_list_to_array(tri_list)
    pts = [(float(v.x), float(v.y), float(v.z)) for v in verts]
    tl = [(int(t.x), int(t.y), int(t.z)) for t in tris]
    DUMPS.mkdir(parents=True, exist_ok=True)
    write_obj(DUMPS / f"{stem}.obj", pts, tl)
    return pts, tl


# --------------------------------------------------------------------------------------------
# Content helpers
# --------------------------------------------------------------------------------------------
def save(asset) -> None:
    if not ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"save failed: {asset.get_path_name()}")


def import_fbx_static(fbx: Path, dest_pkg: str, name: str):
    ue.SystemLibrary.execute_console_command(None, "Interchange.FeatureFlags.Import.FBX 0")
    ui = ue.FbxImportUI()
    for key, value in dict(automated_import_should_detect_type=False, import_as_skeletal=False, import_mesh=True,
                           import_materials=False, import_textures=False, import_animations=False,
                           create_physics_asset=False).items():
        ui.set_editor_property(key, value)
    ui.set_editor_property("mesh_type_to_import", ue.FBXImportType.FBXIT_STATIC_MESH)
    data = ui.get_editor_property("static_mesh_import_data")
    for key, value in dict(combine_meshes=True, auto_generate_collision=False, generate_lightmap_u_vs=False,
                           import_mesh_lods=False, normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                           convert_scene=True, convert_scene_unit=True, force_front_x_axis=False,
                           import_uniform_scale=1.0).items():
        data.set_editor_property(key, value)
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(fbx), destination_path=dest_pkg, destination_name=name, automated=True,
                           replace_existing=True, replace_existing_settings=True, save=True,
                           factory=ue.FbxFactory(), options=ui).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = ue.load_asset(f"{dest_pkg}/{name}")
    if not isinstance(mesh, ue.StaticMesh):
        raise RuntimeError(f"FBX import did not produce a StaticMesh at {dest_pkg}/{name}")
    return mesh


def import_texture(png: Path, dest_pkg: str, name: str):
    task = ue.AssetImportTask()
    for key, value in dict(filename=str(png), destination_path=dest_pkg, destination_name=name, automated=True,
                           replace_existing=True, save=True).items():
        task.set_editor_property(key, value)
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex = ue.load_asset(f"{dest_pkg}/{name}")
    if not isinstance(tex, ue.Texture2D):
        raise RuntimeError(f"texture import failed: {png}")
    tex.set_editor_property("srgb", True)
    save(tex)
    return tex


def make_preview_material(tex):
    path = f"{INPUT_PKG}/{MAT_NAME}"
    if ue.EditorAssetLibrary.does_asset_exist(path):
        mat = ue.load_asset(path)
    else:
        mat = ue.AssetToolsHelpers.get_asset_tools().create_asset(MAT_NAME, INPUT_PKG, ue.Material,
                                                                  ue.MaterialFactoryNew())
    mel = ue.MaterialEditingLibrary
    mel.delete_all_material_expressions(mat)
    node = mel.create_material_expression(mat, ue.MaterialExpressionTextureSample, -400, 0)
    node.set_editor_property("texture", tex)
    mel.connect_material_property(node, "RGB", ue.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, ue.MaterialExpressionConstant, -400, 250)
    rough.set_editor_property("r", 0.6)
    mel.connect_material_property(rough, "", ue.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    save(mat)
    return mat


def load_keypoints() -> dict:
    if not KEYPOINTS_JSON:
        return {}
    raw = json.loads(Path(KEYPOINTS_JSON).read_text(encoding="utf-8"))
    return {int(k): ue.Vector3f(float(v[0]), float(v[1]), float(v[2])) for k, v in raw.items()}


def create_character():
    assert CHAR_PATH != BASELINE_PATH
    if ue.EditorAssetLibrary.does_asset_exist(CHAR_PATH):
        if not RECREATE:
            raise RuntimeError(f"{CHAR_PATH} already exists and PB_RECREATE=0")
        # only ever our own asset (MH_PlayerBase, locked by claude) left by an earlier attempt of this script
        step(f"deleting previous attempt's {CHAR_PATH} for a clean conform")
        if not ue.EditorAssetLibrary.delete_asset(CHAR_PATH):
            raise RuntimeError(f"could not delete old {CHAR_PATH}")
    character = ue.AssetToolsHelpers.get_asset_tools().create_asset(
        asset_name=CHAR_NAME, package_path=CHAR_DIR, asset_class=ue.MetaHumanCharacter,
        factory=ue.new_object(type=ue.MetaHumanCharacterFactoryNew))
    if not isinstance(character, ue.MetaHumanCharacter):
        raise RuntimeError(f"could not create {CHAR_PATH}")
    character.set_editor_property("preview_material_type", ue.MetaHumanCharacterSkinPreviewMaterial.EDITABLE)
    return character


def find_component(actor, name: str):
    for comp in actor.get_components_by_class(ue.SkeletalMeshComponent):
        if comp.get_name() == name:
            return comp
    return None


def bone_positions(actor) -> dict:
    body = find_component(actor, "Body")
    if body is None:
        return {}
    res = {}
    for name in MH_BONES:
        if body.does_socket_exist(name):
            res[name] = v3(body.get_socket_location(name))
    return res


def joint_measures(b: dict) -> dict:
    def d(a, c):
        if a not in b or c not in b:
            return None
        return math.dist(b[a], b[c])

    out = {}
    if "upperarm_l" in b and "upperarm_r" in b:
        out["shoulder_width_joints"] = round(d("upperarm_l", "upperarm_r"), 2)
    if "thigh_l" in b and "thigh_r" in b:
        out["hip_joint_width"] = round(d("thigh_l", "thigh_r"), 2)
    for s in ("l", "r"):
        ua, fa = d(f"upperarm_{s}", f"lowerarm_{s}"), d(f"lowerarm_{s}", f"hand_{s}")
        th, cf = d(f"thigh_{s}", f"calf_{s}"), d(f"calf_{s}", f"foot_{s}")
        if ua and fa:
            out[f"arm_{s}_shoulder_elbow_wrist"] = round(ua + fa, 2)
            out[f"upperarm_{s}"] = round(ua, 2)
            out[f"forearm_{s}"] = round(fa, 2)
        if th and cf:
            out[f"leg_{s}_hip_knee_ankle"] = round(th + cf, 2)
            out[f"thigh_{s}"] = round(th, 2)
            out[f"shin_{s}"] = round(cf, 2)
    return out


# --------------------------------------------------------------------------------------------
# Scene / capture
# --------------------------------------------------------------------------------------------
class Scene:
    def __init__(self):
        ue.EditorLoadingAndSavingUtils.new_blank_map(False)  # untitled, never saved
        self.world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        self.actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self._lights_and_backdrop()
        self.camera = self.spawn(ue.SceneCapture2D)
        self.capture = self.camera.get_component_by_class(ue.SceneCaptureComponent2D)
        self.rt_track = ue.RenderingLibrary.create_render_target2d(
            self.world, TRACK_RES, TRACK_RES, ue.TextureRenderTargetFormat.RTF_RGBA8)
        self.rt_track.set_editor_property("target_gamma", 2.2)
        self.rt_shot = ue.RenderingLibrary.create_render_target2d(
            self.world, SHOT_W, SHOT_H, ue.TextureRenderTargetFormat.RTF_RGBA8)
        self.rt_shot.set_editor_property("target_gamma", 2.2)
        self.rt_ortho = ue.RenderingLibrary.create_render_target2d(
            self.world, ORTHO_RES, ORTHO_RES, ue.TextureRenderTargetFormat.RTF_RGBA8)
        cap = self.capture
        cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        # capture_every_frame does NOT render in an editor world under -RenderOffscreen (attempt 2 exported stale
        # frames from the spawn position); render explicitly with capture_scene() every tick instead (Codex's
        # working script also called capture_scene() right before each export).
        cap.set_editor_property("capture_every_frame", False)
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
        self.use_target(self.rt_shot)
        self.set_render_mode(RENDER_MODE)

    def spawn(self, cls, location=(0, 0, 0), rotation=(0, 0, 0)):
        return self.actors.spawn_actor_from_class(cls, ue.Vector(*location), ue.Rotator(*rotation))

    def _lights_and_backdrop(self) -> None:
        self.lights = [self.spawn(ue.DirectionalLight) for _ in range(3)]
        self.set_rig(LIGHT_RIG)
        backdrop = self.spawn(ue.StaticMeshActor)
        self.backdrop = backdrop
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
        sky.light_component.set_intensity(1.5)
        sky.light_component.recapture_sky()
        self.sky = sky

    def set_rig(self, rig: str) -> None:
        """'studio' = frontal key (casts shadows) + front fill + back rim. 'codex' = the rig Codex's scripts
        (and attempt 3) actually produced: they passed (pitch, yaw, roll) tuples POSITIONALLY to unreal.Rotator,
        whose positional order is (roll, pitch, yaw), so the lights came from the sides and from below."""
        spec = LIGHT_RIGS[rig]
        for light, (pitch, yaw, roll, intensity, color, shadows) in zip(self.lights, spec):
            light.set_actor_rotation(ue.Rotator(roll=roll, pitch=pitch, yaw=yaw), False)
            light.light_component.set_intensity(intensity)
            light.light_component.set_light_color(ue.LinearColor(*color, 1))
            light.light_component.set_cast_shadows(shadows)
        self.rig = rig

    def set_render_mode(self, mode: str) -> None:
        for command in (SIMPLE_RENDER_CVARS if mode == "simple" else LUMEN_RENDER_CVARS):
            ue.SystemLibrary.execute_console_command(self.world, command)
        self.render_mode = mode

    def use_target(self, rt) -> None:
        self.capture.set_editor_property("texture_target", rt)

    def configure(self, mode: str) -> None:
        """'lit' = perspective final colour; 'base_ortho' = orthographic GBuffer base colour (unlit albedo on a
        black, geometry-free background) for silhouette measurements."""
        cap = self.capture
        if mode == "base_ortho":
            cap.set_editor_property("projection_type", ue.CameraProjectionMode.ORTHOGRAPHIC)
            cap.set_editor_property("ortho_width", ORTHO_WIDTH)
            cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_BASE_COLOR)
            self.use_target(self.rt_ortho)
        else:
            cap.set_editor_property("projection_type", ue.CameraProjectionMode.PERSPECTIVE)
            cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
            self.use_target(self.rt_shot)
        self.mode = mode
        self.apply_hidden()

    def hide_only(self, actors) -> None:
        # HiddenActors cannot be set from Python on this component ("cannot be edited on templates"), so use
        # the component-list UFUNCTIONs; re-applied before every shot so late-added components are hidden too.
        self.hidden = [a for a in actors if a is not None]
        self.apply_hidden()

    def apply_hidden(self) -> None:
        self.capture.clear_hidden_components()
        hidden = list(getattr(self, "hidden", []))
        if getattr(self, "mode", "lit") == "base_ortho":
            hidden.append(self.backdrop)
        for actor in hidden:
            self.capture.hide_actor_components(actor, True)

    def aim(self, location, look_at, fov_deg: float) -> None:
        loc = ue.Vector(*location)
        target = ue.Vector(*look_at)
        self.camera.set_actor_location_and_rotation(loc, ue.MathLibrary.find_look_at_rotation(loc, target),
                                                    False, False)
        self.capture.set_editor_property("fov_angle", float(fov_deg))

    def view_info(self, width: int, height: int):
        info = ue.MinimalViewInfo()
        info.location = self.camera.get_actor_location()
        info.rotation = self.camera.get_actor_rotation()
        info.fov = self.capture.get_editor_property("fov_angle")
        info.aspect_ratio = float(width) / float(height)
        info.projection_mode = ue.CameraProjectionMode.PERSPECTIVE
        return info

    def export(self, rt, name: str) -> str:
        CAPTURES.mkdir(parents=True, exist_ok=True)
        ue.RenderingLibrary.export_render_target(self.world, rt, str(CAPTURES), name)
        path = str(CAPTURES / name)
        REPORT["captures"].append(path)
        return path


def shot(name, loc, look, fov=30.0, mode="lit"):
    return {"name": name, "loc": tuple(loc), "look": tuple(look), "fov": fov, "mode": mode}


def body_shots(prefix: str, height_center: float = BODY_CAM_Z):
    z = height_center
    d = BODY_CAM_DIST
    return [shot(prefix + "Body_Front.png", (0.0, d, z), (0.0, 0.0, z)),
            shot(prefix + "Body_Side.png", (d, 0.0, z), (0.0, 0.0, z)),
            shot(prefix + "Body_Back.png", (0.0, -d, z), (0.0, 0.0, z))]


def ortho_shots(prefix: str):
    """Orthographic base-colour silhouettes, 1200 px over 240 cm (0.2 cm/px), centred at z=95, x=0 / y=0."""
    z = ORTHO_CAM_Z
    return [shot(prefix + "Ortho_Front.png", (0.0, 600.0, z), (0.0, 0.0, z), mode="base_ortho"),
            shot(prefix + "Ortho_Side.png", (600.0, 0.0, z), (0.0, 0.0, z), mode="base_ortho")]


def face_shots(prefix: str, face_center):
    fx, fy, fz = face_center
    d = FACE_CAM_DIST
    a = math.radians(35.0)
    return [shot(prefix + "Face_Front.png", (fx, fy + d, fz), (fx, fy, fz)),
            shot(prefix + "Face_ThreeQuarter.png", (fx + d * math.sin(a), fy + d * math.cos(a), fz), (fx, fy, fz)),
            shot(prefix + "Face_Profile.png", (fx + d, fy, fz), (fx, fy, fz))]


def hand_shots(prefix: str, hands: dict):
    shots = []
    for label, c in sorted(hands.items()):
        s = 1.0 if c[0] > 0 else -1.0
        shots.append(shot(f"{prefix}Hand_{label}_Front.png", (c[0], c[1] + 45.0, c[2] + 10.0), c))
        shots.append(shot(f"{prefix}Hand_{label}_Outer.png", (c[0] + s * 45.0, c[1], c[2] + 5.0), c))
    return shots


# --------------------------------------------------------------------------------------------
# Tick-driven runner
# --------------------------------------------------------------------------------------------
class Runner:
    def __init__(self, mhs, character, mesh, verts, tris, pts, scene, target_actor):
        self.mhs = mhs
        self.character = character
        self.mesh = mesh
        self.verts = verts
        self.tris = tris
        self.pts = pts
        self.scene = scene
        self.target_actor = target_actor
        self.head = head_frame(pts)
        self.hands = hand_centers(pts)
        self.mh_actor = None
        self.baseline = None
        self.baseline_actor = None
        self.key = None
        self.tracking = None
        self.handle = None
        self.busy = False
        self.done = False
        self.stage = ""
        self.stage_frame = 0
        self.stage_t0 = time.monotonic()
        self.shots: list = []
        self.shot_index = 0
        self.after_shots = ""
        self.mh_face_center = None

    # -- plumbing ------------------------------------------------------------------------
    def start(self) -> None:
        self.goto("warmup_target")
        self.handle = ue.register_slate_post_tick_callback(self.tick)
        ue.EditorPythonScripting.set_keep_python_script_alive(True)

    def goto(self, stage: str) -> None:
        self.stage = stage
        self.stage_frame = 0
        self.stage_t0 = time.monotonic()
        step("stage -> " + stage)

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
            if self.stage in CAPTURE_STAGES:
                self.scene.capture.capture_scene()  # immediate render; builds TAA history while settling
            getattr(self, "stage_" + self.stage)()
        except Exception:
            REPORT["error"] = traceback.format_exc()
            step("ERROR in stage " + self.stage, error=REPORT["error"])
            ue.log_error(REPORT["error"])
            self.finish(success=False)
        finally:
            self.busy = False

    def warmup(self) -> bool:
        if self.stage_frame in (30, WARMUP_FRAMES - 15):
            ue.AutomationLibrary.finish_loading_before_screenshot()
        if self.stage_frame == WARMUP_FRAMES:
            ue.AutomationLibrary.finish_loading_before_screenshot()
        return self.stage_frame >= WARMUP_FRAMES and time.monotonic() - self.stage_t0 >= 8.0

    def begin_shots(self, shots: list, after: str) -> None:
        self.shots = shots
        self.shot_index = 0
        self.after_shots = after
        self.aim_shot(shots[0])
        self.goto("shots")

    def aim_shot(self, s: dict) -> None:
        self.scene.configure(s["mode"])
        self.scene.aim(s["loc"], s["look"], s["fov"])
        if s["mode"] == "base_ortho":
            REPORT.setdefault("ortho_cameras", {})[s["name"]] = {
                "loc": list(s["loc"]), "look": list(s["look"]), "ortho_width_cm": ORTHO_WIDTH, "res": ORTHO_RES}

    def stage_shots(self) -> None:
        if not self.settled():
            return
        name = self.shots[self.shot_index]["name"]
        self.scene.capture.capture_scene()
        self.scene.export(self.scene.rt_ortho if self.scene.mode == "base_ortho" else self.scene.rt_shot, name)
        step("captured " + name)
        self.shot_index += 1
        if self.shot_index < len(self.shots):
            self.aim_shot(self.shots[self.shot_index])
            self.stage_frame = 0
            self.stage_t0 = time.monotonic()
        else:
            self.goto(self.after_shots)

    # -- target mesh ---------------------------------------------------------------------
    def stage_warmup_target(self) -> None:
        if not self.warmup():
            return
        if TRACK_FACE:
            self.aim_tracking_camera()
            self.goto("track")
        else:
            self.target_shots()

    def aim_tracking_camera(self) -> None:
        """UMeshTargetContourMechanic::TrackFaceWithAutoFraming geometry (camera on +Y, raised by 0.2*HeadSize,
        FOV clamped to [35,110]) but with the frame sized like the tool's real combined-mesh case: the head box
        comes from the real head vertices and the frame is ~2x the head height, as Epic's fill ratio intends."""
        cx, cy, cz = self.head["center"]
        sx, sy, sz = self.head["size"]
        head_size = math.sqrt((sx / 2) ** 2 + (sy / 2) ** 2 + (sz / 2) ** 2)
        fov = 35.0
        frame = 2.0 * max(sx, sz)
        dist = (frame * 0.5) / math.tan(math.radians(fov * 0.5))
        self.scene.hide_only([])
        self.scene.configure("lit")
        self.scene.use_target(self.scene.rt_track)
        self.scene.aim((cx, cy + dist, cz + 0.2 * head_size), (cx, cy, cz), fov)
        REPORT["tracking_camera"] = {"distance_cm": round(dist, 2), "fov": fov, "frame_cm": round(frame, 2),
                                     "head_center": [round(c, 2) for c in self.head["center"]],
                                     "head_size": [round(c, 2) for c in self.head["size"]]}

    def stage_track(self) -> None:
        if not self.settled():
            return
        scene = self.scene
        scene.capture.capture_scene()
        path = scene.export(scene.rt_track, "target_TrackInput.png")
        pixels = unwrap(ue.RenderingLibrary.read_render_target(scene.world, scene.rt_track, True))
        n = 0 if pixels is None else len(pixels)
        curves = None
        if n == TRACK_RES * TRACK_RES:
            curves = unwrap(self.mhs.track_face_landmarks_from_image(pixels, TRACK_RES, TRACK_RES))
        method = "render_target_pixels"
        if not curves:
            # Epic's example path: load the portrait PNG from disk
            try:
                size, disk_pixels = ue.PromotedFrameUtils.get_promoted_frame_as_pixel_array_from_disk(path)
                if size.x > 0:
                    curves = unwrap(self.mhs.track_face_landmarks_from_image(disk_pixels, size.x, size.y))
                    method = "png_from_disk"
            except Exception as exc:  # noqa: BLE001
                warn(f"PNG tracking fallback raised {exc!r}")
        if curves:
            info = scene.view_info(TRACK_RES, TRACK_RES)
            self.tracking = (curves, info, ue.IntPoint(TRACK_RES, TRACK_RES))
            REPORT["face_tracking"] = {"status": "ok", "method": method, "pixels_read": n,
                                       "curves": {str(k): len(v.tracking_points) for k, v in curves.items()},
                                       "camera": {"location": v3(info.location),
                                                  "rotation": [info.rotation.pitch, info.rotation.yaw,
                                                               info.rotation.roll], "fov": info.fov}}
            step("face tracking ok", curves=len(curves))
        else:
            if self.scene.rig != "codex":
                warn(f"face tracking found no face under rig '{self.scene.rig}'; retrying under the attempt-3 rig")
                self.scene.set_rig("codex")
                self.stage_frame = 0
                self.stage_t0 = time.monotonic()
                return
            REPORT["face_tracking"] = {"status": "failed_or_no_face", "pixels_read": n}
            warn("face tracking found no face; conform continues without 2D landmarks (as the UI tool does)")
        REPORT.setdefault("face_tracking", {})["rig"] = self.scene.rig
        self.scene.set_rig(LIGHT_RIG)
        self.target_shots()

    def target_shots(self) -> None:
        cx, cy, _ = self.head["center"]
        fz = self.head["top_z"] - 12.0
        self.face_center_target = (cx, cy, fz)
        self.scene.hide_only([self.mh_actor])
        shots = body_shots("target_") + face_shots("target_", self.face_center_target) + \
            hand_shots("target_", self.hands) + ortho_shots("target_")
        self.target_cams = shots
        self.begin_shots(shots, "conform")

    # -- conform -------------------------------------------------------------------------
    def stage_conform(self) -> None:
        mhs = self.mhs
        character = self.character
        ue.SystemLibrary.execute_console_command(None, "mh.Character.FromCustomMeshImportShowIterations 0")
        key = ue.MetaHumanCharacterTargetMeshKey()
        key.combined_mesh = self.mesh
        self.key = key
        preset = mhs.get_preset_body_key_points(character)
        REPORT["preset_body_keypoints"] = {str(k): int(v) for k, v in preset.items()}
        keypoints = load_keypoints()

        variants = []
        if self.tracking:
            variants.append(("with_face_tracking", True))
        variants.append(("without_face_tracking", False))
        ok = False
        for label, use_tracking in variants:
            target = ue.ConformTargetMesh()
            target.target_parts_type = ue.TargetPartsType.COMBINED
            target.body_vertices = self.verts
            target.body_vertex_indices = self.tris
            solve = ue.BodyConformSolveSettings()  # C++ defaults == the tool's defaults
            solve.pipeline_name = "combined"       # MeshImportTool.cpp auto-solve name for Combined
            params = ue.ConformTargetParams()
            params.conform_target_mesh = target
            params.auto_solve = True
            params.estimate_body_joints_from_mesh = ESTIMATE_JOINTS
            params.body_conform_solve_settings = solve
            if keypoints:
                params.key_point_targets = keypoints
            if use_tracking:
                curves, info, size = self.tracking
                params.curve_tracking_points = curves
                params.camera_view_info = info
                params.image_size = size
            REPORT.setdefault("conform_attempts", []).append({
                "label": label, "auto_solve": True, "pipeline": "combined", "parts": "COMBINED",
                "estimate_joints": ESTIMATE_JOINTS, "keypoints": len(keypoints),
                "face_curves": len(self.tracking[0]) if use_tracking else 0,
                "solver_defaults": {k: str(solve.get_editor_property(k)) for k in
                                    ("iterations", "face_iterations", "solve_pose", "symmetrical_solve",
                                     "apply_neck_seam_smoothing")}})
            write_report()
            step(f"conform_to_target_meshes START ({label}) verts={len(self.verts)} tris={len(self.tris) // 3}")
            t = time.monotonic()
            ok = bool(mhs.conform_to_target_meshes(character, key, params))
            secs = round(time.monotonic() - t, 1)
            REPORT["conform_attempts"][-1].update({"ok": ok, "seconds": secs})
            step(f"conform_to_target_meshes END ({label}) ok={ok} in {secs}s")
            if ok:
                REPORT["conform_used"] = label
                break
        if not ok:
            raise RuntimeError("conform_to_target_meshes returned False for every variant "
                               "(see LogMetaHumanCoreTechLib / LogMetaHumanCharacterEditor in conform_engine.log)")
        checkpoint("conform_solved")

        try:
            dna = ue.MetaHumanPosedDNAExportParams()
            dna.target_mesh_key = key
            dna.external_path = str(OUT)
            dna.asset_name = POSED_DNA_NAME
            dna.overwrite_existing_assets = True
            ue.MetaHumanCharacterExportBlueprintLibrary.export_posed_dna(character, dna)
            dna_file = OUT / (POSED_DNA_NAME + ".dna")
            REPORT["posed_dna"] = {"path": str(dna_file), "exists": dna_file.is_file(),
                                   "bytes": dna_file.stat().st_size if dna_file.is_file() else 0}
            step("posed DNA exported", **REPORT["posed_dna"])
        except Exception as exc:  # noqa: BLE001
            warn(f"export_posed_dna failed: {exc!r}")

        REPORT["constraints_posed"] = self.constraints()
        self.mh_actor = mhs.spawn_meta_human_actor(character, True)
        if self.mh_actor is None:
            raise RuntimeError("spawn_meta_human_actor returned None")
        mhs.assemble_for_preview(character)
        REPORT["mh_actor_components"] = [f"{c.get_name()}:{c.get_class().get_name()}" for c in
                                         self.mh_actor.get_components_by_class(ue.ActorComponent)]
        self.scene.hide_only([self.target_actor])
        self.goto("warmup_posed")

    def constraints(self) -> dict:
        res = {}
        for c in self.mhs.get_body_constraints(self.character, False):
            res[str(c.name)] = {"value": round(float(c.target_measurement), 2),
                                "active": bool(c.get_editor_property("is_active")),
                                "min": round(float(c.min_measurement), 2), "max": round(float(c.max_measurement), 2)}
        return res

    def dump_mh(self, actor, stem: str) -> dict:
        info = {}
        pts_all = []
        for comp_name in ("Body", "Face"):
            comp = find_component(actor, comp_name)
            if comp is None:
                warn(f"{stem}: no {comp_name} component")
                continue
            try:
                pts, tris = dump_component(comp, f"{stem}_{comp_name}")
                info[comp_name] = {"verts": len(pts), "tris": len(tris), "obj": str(DUMPS / f"{stem}_{comp_name}.obj")}
                pts_all.extend(pts)
            except Exception as exc:  # noqa: BLE001
                warn(f"{stem}: vertex dump of {comp_name} failed: {exc!r}")
        info["pts"] = pts_all
        return info

    def stage_warmup_posed(self) -> None:
        if not self.warmup():
            return
        origin, extent = self.mh_actor.get_actor_bounds(False)
        REPORT["mh_bounds_posed"] = {"origin": v3(origin), "extent": v3(extent)}
        # NOTE: socket positions / CPU-skinned vertex copies of the editor actor in the solved pose do NOT match
        # what renders (attempt 3: ~12 cm low). Kept for the record only; the posed ortho silhouettes are used.
        REPORT["mh_bones_posed_UNRELIABLE"] = bone_positions(self.mh_actor)
        shots = [dict(sh, name=sh["name"].replace("target_", "posed_")) for sh in self.target_cams
                 if "_Outer" not in sh["name"] and "Back" not in sh["name"] and "Profile" not in sh["name"]]
        self.begin_shots(shots, "commit")

    def stage_commit(self) -> None:
        mhs = self.mhs
        mhs.commit_posed_state_as_a_pose(self.character, self.key)
        step("commit_posed_state_as_a_pose done")
        REPORT["constraints_apose"] = self.constraints()
        try:
            REPORT["face_model_coefficient_count"] = len(mhs.get_face_model_coefficients(self.character))
        except Exception as exc:  # noqa: BLE001
            warn(f"get_face_model_coefficients: {exc!r}")
        save(self.character)
        REPORT["character_saved_after_commit"] = True
        checkpoint("conform_committed_and_saved")
        mhs.assemble_for_preview(self.character)
        self.goto("warmup_apose")

    def stage_warmup_apose(self) -> None:
        if not self.warmup():
            return
        origin, extent = self.mh_actor.get_actor_bounds(False)
        REPORT["mh_bounds_apose"] = {"origin": v3(origin), "extent": v3(extent)}
        bones = bone_positions(self.mh_actor)
        REPORT["mh_bones_apose"] = bones
        REPORT["measure_mh_apose_joints"] = joint_measures(bones)
        # Body only: the Face component's CPU-skinned copy is offset/deformed vs. the render (attempt 3: neck
        # ring +10.4 cm, 7.6 mm residual after translation), while Kelvin's matched exactly.
        body = find_component(self.mh_actor, "Body")
        pts = []
        try:
            pts, tris = dump_component(body, "mh_apose_Body")
            REPORT["mh_dump_apose"] = {"Body": {"verts": len(pts), "tris": len(tris),
                                                "obj": str(DUMPS / "mh_apose_Body.obj")}}
        except Exception as exc:  # noqa: BLE001
            warn(f"mh_apose body dump failed: {exc!r}")
        sh_z = None
        if "upperarm_l" in bones and "upperarm_r" in bones:
            sh_z = (bones["upperarm_l"][2] + bones["upperarm_r"][2]) / 2
        if pts:
            REPORT["measure_mh_apose_body_vertices"] = measure_points(pts, shoulder_z=sh_z)
        height = REPORT.get("constraints_apose", {}).get("Height", {}).get("value", 185.6)
        self.mh_face_center = (0.0, self.head["center"][1], height - 12.0)
        mh_hands = {}
        if bones.get("hand_l") and bones.get("middle_03_l"):
            mh_hands = {}
            for s in ("l", "r"):
                h, m = bones[f"hand_{s}"], bones[f"middle_03_{s}"]
                c = [(h[i] + m[i]) / 2 for i in range(3)]
                mh_hands["xpos" if c[0] > 0 else "xneg"] = c
        REPORT["mh_face_center"] = self.mh_face_center
        REPORT["mh_hand_centers"] = mh_hands
        step("A-pose MetaHuman measured", verts=len(pts))
        write_report()
        shots = body_shots("mh_") + face_shots("mh_", self.mh_face_center) + hand_shots("mh_", mh_hands) + \
            ortho_shots("mh_")
        self.begin_shots(shots, "render_ab")

    def stage_render_ab(self) -> None:
        # A/B for Codex's black-eye issue: same face shot with the other render mode
        other = "lumen" if self.scene.render_mode == "simple" else "simple"
        self.scene.set_render_mode(other)
        f0 = face_shots("mh_", self.mh_face_center)[0]
        b0 = body_shots("mh_")[0]
        shots = [dict(f0, name=f0["name"].replace(".png", f"_{other}.png")),
                 dict(b0, name=b0["name"].replace(".png", f"_{other}.png"))]
        self.begin_shots(shots, "render_restore")

    def stage_render_restore(self) -> None:
        self.scene.set_render_mode(RENDER_MODE)
        save(self.character)
        step("MH_PlayerBase saved (post-capture)")
        if DO_BASELINE:
            self.goto("baseline_open")
        else:
            self.goto("finish")

    # -- baseline (scratch duplicate of MH_MaleBase, never saved) -------------------------
    def stage_baseline_open(self) -> None:
        if ue.EditorAssetLibrary.does_asset_exist(BASELINE_DUP):
            dup = ue.load_asset(BASELINE_DUP)
        else:
            dup = ue.EditorAssetLibrary.duplicate_asset(BASELINE_PATH, BASELINE_DUP)
        if not isinstance(dup, ue.MetaHumanCharacter):
            warn("could not duplicate MH_MaleBase for the comparison shot")
            self.goto("finish")
            return
        dup.set_editor_property("preview_material_type", ue.MetaHumanCharacterSkinPreviewMaterial.EDITABLE)
        if not self.mhs.try_add_object_to_edit(dup):
            warn("try_add_object_to_edit failed for the baseline duplicate")
            self.goto("finish")
            return
        self.baseline = dup
        self.baseline_actor = self.mhs.spawn_meta_human_actor(dup, True)
        self.mhs.assemble_for_preview(dup)
        self.scene.hide_only([self.target_actor, self.mh_actor])
        step("baseline duplicate opened + spawned (MH_MaleBase itself untouched)")
        self.goto("warmup_baseline")

    def stage_warmup_baseline(self) -> None:
        if not self.warmup():
            return
        bones = bone_positions(self.baseline_actor)
        REPORT["baseline_bones"] = bones
        REPORT["measure_baseline_joints"] = joint_measures(bones)
        dump = self.dump_mh(self.baseline_actor, "baseline_apose")
        pts = dump.pop("pts")
        REPORT["baseline_dump"] = dump
        if pts:
            sh_z = None
            if "upperarm_l" in bones and "upperarm_r" in bones:
                sh_z = (bones["upperarm_l"][2] + bones["upperarm_r"][2]) / 2
            REPORT["measure_baseline_vertices"] = measure_points(pts, shoulder_z=sh_z)
            hf = head_frame(pts)
            fc = (hf["center"][0], hf["center"][1], hf["top_z"] - 12.0)
        else:
            fc = self.mh_face_center
        try:
            REPORT["baseline_constraints"] = {str(c.name): round(float(c.target_measurement), 2)
                                              for c in self.mhs.get_body_constraints(self.baseline, False)}
        except Exception as exc:  # noqa: BLE001
            warn(f"baseline constraints: {exc!r}")
        shots = body_shots("baseline_")[:2] + face_shots("baseline_", fc)[:1] + ortho_shots("baseline_")
        self.begin_shots(shots, "baseline_close")

    def stage_baseline_close(self) -> None:
        if self.baseline is not None and self.mhs.is_object_added_for_editing(self.baseline):
            self.mhs.remove_object_to_edit(self.baseline)
        step("baseline duplicate released (not saved)")
        self.goto("finish")

    def stage_finish(self) -> None:
        self.finish(success=True)

    # -- teardown ------------------------------------------------------------------------
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
            if self.baseline is not None and self.mhs.is_object_added_for_editing(self.baseline):
                self.mhs.remove_object_to_edit(self.baseline)
        except Exception:
            REPORT["teardown_error"] = traceback.format_exc()
            success = False
        REPORT["baseline_uasset_sha256_end"] = sha256(BASELINE_UASSET)
        REPORT["baseline_uasset_unchanged"] = (REPORT["baseline_uasset_sha256_end"] ==
                                               REPORT.get("baseline_uasset_sha256_start"))
        checkpoint("done" if success else "failed", finished_utc=_now())
        if not INTERACTIVE:
            ue.SystemLibrary.quit_editor()


# --------------------------------------------------------------------------------------------
# Entry
# --------------------------------------------------------------------------------------------
def main() -> None:
    with open(STEP_LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n===== pb_conform.py attempt {ATTEMPT} {_now()} =====\n")
    assert_locks()
    assert_clean_names(CHAR_PATH, INPUT_PKG, MESH_NAME, TEX_NAME, MAT_NAME, POSED_DNA_NAME, BASELINE_DUP)
    if not REPORT["engine"].startswith("5.8"):
        raise RuntimeError(f"expected UE 5.8.x, got {REPORT['engine']}")
    if not FBX_PATH.is_file():
        raise FileNotFoundError(FBX_PATH)
    REPORT["baseline_uasset_sha256_start"] = sha256(BASELINE_UASSET)
    REPORT["input_fbx_sha256"] = sha256(FBX_PATH)
    checkpoint("preflight_ok")

    mhs = ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
    scene = Scene()
    step("blank map + lights + capture ready", render_mode=RENDER_MODE)

    mesh = import_fbx_static(FBX_PATH, INPUT_PKG, MESH_NAME)
    data = unwrap(ue.MetaHumanCharacterEditorSubsystem.get_mesh_data_for_conforming(mesh))
    if not data:
        raise RuntimeError("get_mesh_data_for_conforming returned nothing")
    verts, tris = data[0], data[1]
    if not verts or not tris or len(tris) % 3:
        raise RuntimeError(f"bad mesh data: {len(verts)} verts, {len(tris)} indices")
    pts = [(float(v.x), float(v.y), float(v.z)) for v in verts]
    hf = head_frame(pts)
    zmin = hf["zmin"]
    sole = [p[1] for p in pts if p[2] < zmin + 4.0]
    shin = [p[1] for p in pts if zmin + 18.0 < p[2] < zmin + 26.0]
    shin_mean = sum(shin) / len(shin)
    facing = "+Y" if (max(sole) - shin_mean) > (shin_mean - min(sole)) else "-Y"
    REPORT["input_mesh"] = {"asset": mesh.get_path_name(), "vertex_count": len(verts),
                            "triangle_count": len(tris) // 3,
                            "bounds_min": [round(min(p[i] for p in pts), 3) for i in range(3)],
                            "bounds_max": [round(max(p[i] for p in pts), 3) for i in range(3)],
                            "facing": facing, "toe_front_cm": round(max(sole) - shin_mean, 2),
                            "heel_back_cm": round(shin_mean - min(sole), 2),
                            "head_center": [round(c, 2) for c in hf["center"]],
                            "nose_front_y": round(hf["front_y"], 2)}
    REPORT["measure_source_vertices"] = measure_points(pts, shoulder_z=150.0034 - 2.06514)
    DUMPS.mkdir(parents=True, exist_ok=True)
    write_obj(DUMPS / "source_input.obj", pts, [(tris[i], tris[i + 1], tris[i + 2]) for i in range(0, len(tris), 3)])
    step("mesh imported", **{k: REPORT["input_mesh"][k] for k in ("vertex_count", "triangle_count", "facing",
                                                                   "bounds_min", "bounds_max")})
    if not 150.0 <= REPORT["measure_source_vertices"]["height"] <= 220.0:
        raise RuntimeError("input height out of range: wrong units?")
    if facing != "+Y":
        raise RuntimeError("input faces -Y; MetaHuman conform expects +Y")

    tex = import_texture(ALBEDO_PATH, INPUT_PKG, TEX_NAME)
    material = make_preview_material(tex)
    target_actor = scene.actors.spawn_actor_from_object(mesh, ue.Vector(0, 0, 0), ue.Rotator(0, 0, 0))
    component = target_actor.static_mesh_component
    for index in range(component.get_num_materials()):
        component.set_material(index, material)
    step("albedo + preview material applied to the input mesh actor")

    character = create_character()
    save(character)
    step("MH_PlayerBase created + saved (factory new)")
    if not mhs.try_add_object_to_edit(character):
        raise RuntimeError("try_add_object_to_edit failed")
    checkpoint("character_open_for_editing")
    REPORT["constraints_initial"] = {str(c.name): round(float(c.target_measurement), 2)
                                     for c in mhs.get_body_constraints(character, False)}
    Runner(mhs, character, mesh, verts, tris, pts, scene, target_actor).start()


try:
    main()
except Exception:
    REPORT["error"] = traceback.format_exc()
    try:
        step("ERROR in main", error=REPORT["error"])
    except Exception:  # noqa: BLE001
        pass
    ue.log_error(REPORT["error"])
    try:
        _mhs = ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)
        if ue.EditorAssetLibrary.does_asset_exist(CHAR_PATH):
            _char = ue.load_asset(CHAR_PATH)
            if _char is not None and _mhs.is_object_added_for_editing(_char):
                _mhs.remove_object_to_edit(_char)
    except Exception:  # noqa: BLE001
        pass
    try:
        REPORT["baseline_uasset_sha256_end"] = sha256(BASELINE_UASSET)
    except Exception:  # noqa: BLE001
        pass
    checkpoint("failed")
    if not INTERACTIVE:
        ue.SystemLibrary.quit_editor()
