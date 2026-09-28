"""pd_ic2_verify.py -- INDEPENDENT round-2 integrity check of /Game/Characters/MetaHumans/MH_PlayerDefault (UE 5.8.3).

Runs INSIDE UnrealEditor (CharacterLab.uproject), launched by Scripts/MetaHuman/pd_ic2_run.ps1. SAVES NOTHING.
Never signs in; never calls request_auto_rigging / request_texture_sources / build_meta_human.

Checks:
  * MH_PlayerDefault loads from disk as a MetaHumanCharacter (FIRST MetaHuman of the session so its grooms render);
    identity read back (skin, eyes, lashes, makeup, internal + preview collections, groom instance params, groom and
    all other actor components, eye material parameters); FaceA/B/C skin settings read (load only) for comparison
  * unrigged: can_build_meta_human(pd, True) logs its refusal reason into the engine log (grep offline)
  * hair: time until the BrushCut is drawn on this fresh load (crown luma probe, NO re-assembly for 150 s)
  * face: coefficients vs player_default_recipe.json coeffs_final, vs pd_r2_build_1.json, vs FaceC (face_build_report_2)
    and per face-model region; INDEPENDENT reproduction: scratch dup of FaceC + the recipe's jaw-fix landmark moves +
    commit_face_state -> coefficients and face mesh must equal MH_PlayerDefault's
  * body: compare_body_state vs MH_PlayerBase dup, constraints, all bones, full body vertex compare; negative control
    vs MH_MaleBase dup
  * captures: same light rig + cameras as pd_r2_common.py (studio, ambient, headlight, eval, bounce, rimspec0, norim,
    chroma see-through, base colour); FaceC dup = before; Epic preset Kelvin (grooms hidden) as the jaw reference
Scratch duplicates live in /Game/PlayerDefault/Scratch as IC2_* and are never saved.
Outputs: WorkFiles/MetaHuman/player_default/integrity_check_r2/ (ic2_report.json, ic2.log, captures/ic2_*.png, mesh/)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import sys
import time
import traceback
from pathlib import Path

import unreal as ue

sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/MetaHuman")
import pd_r2_common as C  # noqa: E402  (only all_views / FACE_CENTER / PFB.layout are used: identical cameras)

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/MetaHuman/player_default/integrity_check_r2"
CAP = OUT / "captures"
MESH = OUT / "mesh"
REPORT_PATH = OUT / "ic2_report.json"
LOG = OUT / "ic2.log"
CONTENT = ROOT / "Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
HASHED = ["MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase",
          "MH_PlayerDefault"]
RECIPE = ROOT / "WorkFiles/MetaHuman/player_default/player_default_recipe.json"
BUILD_REPORT = ROOT / "WorkFiles/MetaHuman/player_default/pd_r2_build_1.json"
FACE_BUILD_REPORT = ROOT / "WorkFiles/MetaHuman/player_base/faces/face_build_report_2.json"
FACE_PROBE_REPORT = ROOT / "WorkFiles/MetaHuman/player_base/faces/face_probe_report_1.json"
CHAR_DIR = "/Game/Characters/MetaHumans"
PD_PATH = f"{CHAR_DIR}/MH_PlayerDefault"
FACEC_PATH = f"{CHAR_DIR}/MH_PlayerBase_FaceC"
BASE_PATH = f"{CHAR_DIR}/MH_PlayerBase"
MALE_PATH = f"{CHAR_DIR}/MH_MaleBase"
KELVIN_PRESET = "/MetaHumanCharacter/Optional/Presets/Kelvin"
SCRATCH = "/Game/PlayerDefault/Scratch"
MAX_SECONDS = 40 * 60.0

# ---- light rig: identical to pb_conform.py / pd_r2_common.py ----------------------------------------------------
LIGHT_RIG = C.LIGHT_RIG
SKY_INTENSITY = C.SKY_INTENSITY
CVARS = C.SIMPLE_RENDER_CVARS
SHOT_W, SHOT_H = C.SHOT_W, C.SHOT_H
VIEWS = C.all_views()

T0 = time.monotonic()
REPORT: dict = {"script": "Scripts/MetaHuman/pd_ic2_verify.py", "engine": ue.SystemLibrary.get_engine_version(),
                "status": "starting", "steps": [], "checks": {}, "warnings": [], "captures": []}


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def write_report() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(REPORT, indent=1, default=str), encoding="utf-8")


def step(msg: str, **extra) -> None:
    t = round(time.monotonic() - T0, 1)
    line = f"{now()} +{t:7.1f}s {msg}"
    if extra:
        line += "  " + json.dumps(extra, default=str)[:2500]
    OUT.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    ue.log("PD_IC2 " + line)
    REPORT["steps"].append({"t": t, "msg": msg, **extra})
    write_report()


def check(name: str, ok: bool, **detail) -> None:
    REPORT["checks"][name] = {"ok": bool(ok), **detail}
    step(f"CHECK {name}: {'OK' if ok else 'FAIL'}", **detail)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def hashes() -> dict:
    return {n: sha(CONTENT / f"{n}.uasset") for n in HASHED}


def un(r):
    return r[0] if isinstance(r, tuple) and len(r) == 1 else r


def es(v) -> str:
    return str(v).split(".")[-1].split(":")[0].strip("<> ")


def pth(o):
    try:
        return o.get_path_name() if o is not None else None
    except Exception:  # noqa: BLE001
        return str(o)


def vec(v):
    return (float(v.x), float(v.y), float(v.z))


def sdump(s, depth=0):
    if depth > 5:
        return str(s)
    if isinstance(s, (bool, int, float, str)) or s is None:
        return s
    if isinstance(s, ue.LinearColor):
        return [round(s.r, 4), round(s.g, 4), round(s.b, 4), round(s.a, 4)]
    if isinstance(s, ue.EnumBase):
        return es(s)
    if isinstance(s, ue.Object):
        return pth(s)
    if isinstance(s, ue.StructBase):
        out = {}
        for n in dir(s):
            if n.startswith("_") or callable(getattr(type(s), n, None)):
                continue
            try:
                out[n] = sdump(s.get_editor_property(n), depth + 1)
            except Exception:  # noqa: BLE001
                pass
        return out
    if isinstance(s, (list, tuple, ue.Array)):
        return [sdump(x, depth + 1) for x in s]
    if isinstance(s, (dict, ue.Map)):
        return {str(k): sdump(v, depth + 1) for k, v in s.items()}
    return str(s)


def mhs():
    return ue.get_editor_subsystem(ue.MetaHumanCharacterEditorSubsystem)


OPEN: list = []


def open_edit(ch):
    if not mhs().is_object_added_for_editing(ch):
        if not mhs().try_add_object_to_edit(ch):
            raise RuntimeError(f"try_add_object_to_edit failed: {pth(ch)}")
    if ch not in OPEN:
        OPEN.append(ch)


def close_edit(ch):
    try:
        if mhs().is_object_added_for_editing(ch):
            mhs().remove_object_to_edit(ch)
    finally:
        if ch in OPEN:
            OPEN.remove(ch)


def scratch_dup(src: str, name: str):
    dst = f"{SCRATCH}/{name}"
    if ue.EditorAssetLibrary.does_asset_exist(dst):
        raise RuntimeError(f"{dst} already exists (must not: scratch is never saved)")
    obj = ue.EditorAssetLibrary.duplicate_asset(src, dst)
    if not isinstance(obj, ue.MetaHumanCharacter):
        raise RuntimeError(f"duplicate {src} -> {dst} failed: {obj}")
    return obj


# ---------------------------------------------------------------------------------------------------------------
def unlit_material(rgb):
    mat = ue.new_object(ue.Material)
    mat.set_editor_property("two_sided", True)
    mat.set_editor_property("shading_model", ue.MaterialShadingModel.MSM_UNLIT)
    node = ue.MaterialEditingLibrary.create_material_expression(mat, ue.MaterialExpressionConstant3Vector)
    node.set_editor_property("constant", ue.LinearColor(*rgb, 1))
    ue.MaterialEditingLibrary.connect_material_property(node, "", ue.MaterialProperty.MP_EMISSIVE_COLOR)
    ue.MaterialEditingLibrary.recompile_material(mat)
    return mat


def spec(lc, value):
    try:
        lc.set_specular_scale(float(value))
    except Exception:  # noqa: BLE001
        lc.set_editor_property("specular_scale", float(value))


class Scene:
    def __init__(self):
        ue.EditorLoadingAndSavingUtils.new_blank_map(False)
        self.world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        self.eas = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.lights = [self.spawn(ue.DirectionalLight) for _ in LIGHT_RIG]
        self.bounce = self.spawn(ue.DirectionalLight)
        self.bounce.set_actor_rotation(ue.Rotator(roll=0.0, pitch=50.0, yaw=-90.0), False)
        self.bounce.light_component.set_cast_shadows(False)
        self.bounce.light_component.set_intensity(0.0)
        self.grey = self.sphere(50.0, unlit_material((.18, .18, .18)))
        self.green = self.sphere(52.0, unlit_material((0.0, 1.0, 0.0)))   # outside the grey one: seen only in chroma
        self.sky = self.spawn(ue.SkyLight)
        self.sky.light_component.set_mobility(ue.ComponentMobility.MOVABLE)
        self.sky.light_component.set_intensity(SKY_INTENSITY)
        self.sky.light_component.recapture_sky()
        self.sky_default = {p: self.sky.light_component.get_editor_property(p)
                            for p in ("sky_distance_threshold", "lower_hemisphere_is_black")}
        REPORT["sky_default"] = {k: str(v) for k, v in self.sky_default.items()}
        self.sky_ambient = False
        self.cam = self.spawn(ue.SceneCapture2D)
        self.cap = self.cam.get_component_by_class(ue.SceneCaptureComponent2D)
        self.rt = ue.RenderingLibrary.create_render_target2d(self.world, SHOT_W, SHOT_H,
                                                             ue.TextureRenderTargetFormat.RTF_RGBA8)
        self.rt.set_editor_property("target_gamma", 2.2)
        c = self.cap
        c.set_editor_property("texture_target", self.rt)
        c.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        c.set_editor_property("capture_every_frame", False)
        c.set_editor_property("always_persist_rendering_state", True)
        c.set_editor_property("projection_type", ue.CameraProjectionMode.PERSPECTIVE)
        pp = c.get_editor_property("post_process_settings")
        for k, v in [("override_auto_exposure_method", True), ("auto_exposure_method", ue.AutoExposureMethod.AEM_MANUAL),
                     ("override_auto_exposure_bias", True), ("auto_exposure_bias", 0.0),
                     ("override_auto_exposure_apply_physical_camera_exposure", True),
                     ("auto_exposure_apply_physical_camera_exposure", False),
                     ("override_vignette_intensity", True), ("vignette_intensity", 0.0)]:
            pp.set_editor_property(k, v)
        c.set_editor_property("post_process_settings", pp)
        for cmd in CVARS:
            ue.SystemLibrary.execute_console_command(self.world, cmd)
        self.extra_hidden_components = []
        self.variant = None
        self.set_variant("studio")

    def spawn(self, cls):
        return self.eas.spawn_actor_from_class(cls, ue.Vector(0, 0, 0), ue.Rotator())

    def sphere(self, scale, mat):
        a = self.spawn(ue.StaticMeshActor)
        a.static_mesh_component.set_static_mesh(ue.load_asset("/Engine/BasicShapes/Sphere"))
        a.set_actor_scale3d(ue.Vector(scale, scale, scale))
        a.static_mesh_component.set_cast_shadow(False)
        a.static_mesh_component.set_material(0, mat)
        return a

    def apply_hidden(self):
        self.cap.clear_hidden_components()
        self.cap.hide_actor_components(self.grey if self.variant == "chroma" else self.green, True)
        for comp in self.extra_hidden_components:
            self.cap.hide_component(comp)

    def set_sky(self, ambient: bool) -> bool:
        if ambient == self.sky_ambient:
            return False
        comp = self.sky.light_component
        if ambient:
            comp.set_editor_property("sky_distance_threshold", 1000.0)
            comp.set_editor_property("lower_hemisphere_is_black", False)
        else:
            comp.set_editor_property("sky_distance_threshold", float(self.sky_default["sky_distance_threshold"]))
            comp.set_editor_property("lower_hemisphere_is_black", bool(self.sky_default["lower_hemisphere_is_black"]))
        comp.recapture_sky()
        self.sky_ambient = ambient
        return True

    def set_variant(self, variant: str) -> bool:
        """studio | ambient | headlight | bounce | eval | rimspec0 | norim | chroma | base (as pd_r2_common + chroma)"""
        for light, (pitch, yaw, roll, inten, col, shadows) in zip(self.lights, LIGHT_RIG):
            light.set_actor_rotation(ue.Rotator(roll=roll, pitch=pitch, yaw=yaw), False)
            lc = light.light_component
            lc.set_intensity(inten)
            lc.set_light_color(ue.LinearColor(*col, 1))
            lc.set_cast_shadows(shadows)
            spec(lc, 1.0)
        self.sky.light_component.set_intensity(SKY_INTENSITY)
        self.bounce.light_component.set_intensity(0.0)
        self.cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        key, fill, rim = self.lights
        if variant in ("bounce", "eval"):
            self.bounce.light_component.set_intensity(0.8)
            self.bounce.light_component.set_light_color(ue.LinearColor(1, .95, .9, 1))
        if variant == "eval":
            rim.light_component.set_cast_shadows(True)
            spec(rim.light_component, 0.3)
        if variant == "rimspec0":
            spec(rim.light_component, 0.0)
        if variant == "norim":
            rim.light_component.set_intensity(0.0)
        if variant == "headlight":
            fill.light_component.set_intensity(0.0)
            rim.light_component.set_intensity(0.0)
            key.light_component.set_intensity(3.0)
            key.light_component.set_light_color(ue.LinearColor(1, 1, 1, 1))
            key.light_component.set_cast_shadows(False)
            spec(key.light_component, 0.0)
            self.sky.light_component.set_intensity(0.0)
        if variant == "base":
            self.cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_BASE_COLOR)
        changed = self.set_sky(variant == "ambient")
        self.variant = variant
        return changed

    def aim(self, loc, look, fov):
        l = ue.Vector(*loc)
        rot = ue.MathLibrary.find_look_at_rotation(l, ue.Vector(*look))
        self.cam.set_actor_location_and_rotation(l, rot, False, False)
        self.cap.set_editor_property("fov_angle", float(fov))
        if self.variant == "headlight":
            self.lights[0].set_actor_rotation(rot, False)

    def export(self, name):
        CAP.mkdir(parents=True, exist_ok=True)
        ue.RenderingLibrary.export_render_target(self.world, self.rt, str(CAP), name)
        REPORT["captures"].append(str(CAP / name))


def warmup(n=120, min_s=5.0):
    t0 = time.monotonic()
    i = 0
    while i < n or time.monotonic() - t0 < min_s:
        if i in (30, n - 15):
            ue.AutomationLibrary.finish_loading_before_screenshot()
        i += 1
        yield


def settle():
    t0 = time.monotonic()
    f = 0
    while f < 45 or time.monotonic() - t0 < 1.5:
        f += 1
        yield


def shoot(scene, name, view):
    scene.aim(*view)
    scene.apply_hidden()
    yield from settle()
    scene.cap.capture_scene()
    scene.export(name)
    step("captured " + name, variant=scene.variant)


def shoot_plan(scene, prefix, plan):
    for variant, names in plan:
        if scene.set_variant(variant):
            yield from warmup(90, 3.0)
        else:
            yield from warmup(20, 0.8)
        for n in names:
            yield from shoot(scene, f"{prefix}{variant}_{n}.png", VIEWS[n])
    if scene.set_variant("studio"):
        yield from warmup(90, 3.0)


PD_PLAN = [
    ("studio", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "JawLow", "JawRamus", "EarR", "EarRSide",
                "Shoulders_Front", "Shoulders_High", "ShoulderL_TQ", "ShoulderR_TQ", "Shoulders_Back", "Body_Front",
                "Body_Side", "Body_Back", "Eyes", "Head_Back34", "Head_Top", "Head_Back_Far"]),
    ("ambient", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "JawLow", "JawRamus", "EarR",
                 "Body_Back", "Head_Back_Far"]),
    ("headlight", ["Face_Front", "Face_ThreeQuarter", "JawClose", "JawRamus"]),
    ("eval", ["Face_ThreeQuarter", "JawClose"]),
    ("bounce", ["Face_ThreeQuarter", "JawClose"]),
    ("rimspec0", ["Face_Front", "EarR"]),
    ("norim", ["EarR", "Head_Back_Far"]),
    ("chroma", ["Face_ThreeQuarter", "Shoulders_Front", "Shoulders_High", "ShoulderL_TQ", "ShoulderR_TQ",
                "Shoulders_Back", "Body_Front", "Body_Back"]),
    ("base", ["Face_Front", "Face_ThreeQuarter", "JawClose", "EarR", "Shoulders_Front", "ShoulderL_TQ",
              "ShoulderR_TQ"]),
]
FACEC_PLAN = [("studio", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "JawRamus"]),
              ("ambient", ["Face_ThreeQuarter", "JawClose", "JawRamus"]),
              ("headlight", ["Face_ThreeQuarter", "JawClose"]),
              ("chroma", ["Shoulders_Front", "ShoulderL_TQ", "ShoulderR_TQ"])]
KELVIN_PLAN = [("studio", ["Face_ThreeQuarter", "JawClose", "JawRamus"]),
               ("ambient", ["Face_ThreeQuarter", "JawClose", "JawRamus"])]


# ---------------------------------------------------------------------------------------------------------------
def find_comp(actor, name):
    for c in actor.get_components_by_class(ue.SkeletalMeshComponent):
        if c.get_name() == name:
            return c
    return None


def comp_inventory(actor):
    rows = []
    for c in actor.get_components_by_class(ue.ActorComponent):
        row = {"name": c.get_name(), "class": c.get_class().get_name()}
        for prop in ("skeletal_mesh_asset", "groom_asset", "static_mesh"):
            try:
                row[prop] = pth(c.get_editor_property(prop))
            except Exception:  # noqa: BLE001
                pass
        try:
            row["visible"] = bool(c.is_visible())
        except Exception:  # noqa: BLE001
            pass
        rows.append(row)
    return rows


def dump_verts(comp, stem=None):
    dm = ue.new_object(ue.DynamicMesh)
    opts = ue.GeometryScriptCopyMeshFromComponentOptions()
    opts.set_editor_property("want_normals", False)
    opts.set_editor_property("want_tangents", False)
    ue.GeometryScript_SceneUtils.copy_mesh_from_component(comp, dm, opts, True)
    pos = ue.GeometryScript_MeshQueries.get_all_vertex_positions(dm, False)
    pl = next(x for x in (pos if isinstance(pos, tuple) else (pos,)) if isinstance(x, ue.GeometryScriptVectorList))
    tri = ue.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
    tl = next(x for x in (tri if isinstance(tri, tuple) else (tri,)) if isinstance(x, ue.GeometryScriptTriangleList))
    verts = [vec(v) for v in ue.GeometryScript_List.convert_vector_list_to_array(pl)]
    tris = [(int(t.x), int(t.y), int(t.z)) for t in ue.GeometryScript_List.convert_triangle_list_to_array(tl)]
    if stem:
        MESH.mkdir(parents=True, exist_ok=True)
        with open(MESH / f"{stem}.obj", "w", encoding="utf-8") as fh:
            fh.write("# UE world space (GeometryScript CPU copy), cm, Z up, character faces +Y\n")
            for v in verts:
                fh.write(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
            for t in tris:
                fh.write(f"f {t[0] + 1} {t[1] + 1} {t[2] + 1}\n")
    return verts, tris


def mesh_diff(a, b, tol=1e-3):
    va, ta = a
    vb, tb = b
    out = {"verts": [len(va), len(vb)], "tris": [len(ta), len(tb)], "tris_identical": ta == tb}
    if len(va) != len(vb):
        return out
    moved = []
    mx, arg = 0.0, -1
    for i, (p, q) in enumerate(zip(va, vb)):
        d = math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2)
        if d > mx:
            mx, arg = d, i
        if d > tol:
            moved.append(i)
    out["max_dist_cm"] = mx
    out["max_at"] = [round(x, 3) for x in va[arg]] if arg >= 0 else None
    out["moved_gt_tol"] = len(moved)
    if moved:
        zs = [va[i][2] for i in moved]
        out["moved_z_range"] = [round(min(zs), 2), round(max(zs), 2)]
    return out


def bones(actor):
    body = find_comp(actor, "Body")
    res = {}
    for i in range(body.get_num_bones()):
        name = str(body.get_bone_name(i))
        res[name] = vec(body.get_socket_location(name))
    return res


def coeffs(ch):
    return [float(x) for x in un(mhs().get_face_model_coefficients(ch))]


def landmarks(ch):
    return [vec(v) for v in un(mhs().get_face_landmarks(ch))]


def maxdiff(a, b):
    if len(a) != len(b):
        return f"len {len(a)} vs {len(b)}"
    return max((abs(x - y) for x, y in zip(a, b)), default=0.0)


def region_diffs(a, b, lay):
    out = {}
    for r, (i0, n) in enumerate(lay):
        d = max(abs(a[i] - b[i]) for i in range(i0, i0 + 9 + n))
        if d > 1e-9:
            out[str(r)] = round(d, 6)
    return out


def constraints(ch):
    return {str(c.name): (float(c.target_measurement), bool(c.get_editor_property("is_active")))
            for c in mhs().get_body_constraints(ch, False)}


def key_str(k):
    return str(ue.MetaHumanPaletteKeyBlueprintLibrary.to_asset_name_string(k))


def coll_state(col):
    inst = col.get_editor_property("default_instance")
    sel = {}
    params = {}
    for data in inst.get_slot_selection_data():
        s = data.get_editor_property("selection")
        k = s.get_editor_property("selected_item")
        slot = str(s.get_editor_property("slot_name"))
        sel[slot] = key_str(k)
        try:
            ps = {}
            for p in inst.get_instance_parameters(item_path=ue.MetaHumanPaletteItemPath(item_key=k)):
                t = es(p.get_editor_property("type"))
                nm = str(p.get_editor_property("name"))
                if t == "FLOAT":
                    ps[nm] = round(float(p.get_float()), 4)
                elif t == "BOOL":
                    ps[nm] = bool(p.get_bool())
                elif t == "COLOR":
                    ps[nm] = sdump(p.get_color())
            params[slot] = ps
        except Exception as exc:  # noqa: BLE001
            params[slot] = "ERR " + repr(exc)[:120]
    items = []
    lib = ue.MetaHumanCollectionBlueprintLibrary
    try:
        for k in lib.get_all_item_keys(col):
            items.append({"key": key_str(k), "slot": str(lib.get_item_slot_name(col, k))})
    except Exception as exc:  # noqa: BLE001
        items = "ERR " + repr(exc)[:120]
    return {"items": items, "selections": sel, "instance_params": params}


def identity(ch):
    s = ch.get_editor_property("skin_settings")
    sk = s.get_editor_property("skin")
    eyes = ch.get_editor_property("eyes_settings")
    hm = ch.get_editor_property("head_model_settings")
    el = hm.get_editor_property("eyelashes")
    mk = ch.get_editor_property("makeup_settings")
    iris = {}
    for side in ("eye_left", "eye_right"):
        ir = eyes.get_editor_property(side).get_editor_property("iris")
        iris[side] = {k: (es(ir.get_editor_property(k)) if k == "pattern" else round(float(ir.get_editor_property(k)), 4))
                      for k in ("pattern", "primary_color_u", "primary_color_v", "secondary_color_u", "secondary_color_v")}
    out = {"face_texture_index": int(sk.get_editor_property("face_texture_index")),
           "body_texture_index": int(sk.get_editor_property("body_texture_index")),
           "u": round(float(sk.get_editor_property("u")), 4), "v": round(float(sk.get_editor_property("v")), 4),
           "roughness": round(float(sk.get_editor_property("roughness")), 4),
           "show_top_underwear": bool(sk.get_editor_property("show_top_underwear")),
           "freckles_mask": es(s.get_editor_property("freckles").get_editor_property("mask")),
           "enable_texture_overrides": bool(s.get_editor_property("enable_texture_overrides")),
           "iris": iris,
           "eyelashes": sdump(el),
           "makeup": sdump(mk),
           "skin_settings_full": sdump(s),
           "head_model_full": sdump(hm),
           "eval": {k: round(float(ch.get_editor_property("face_evaluation_settings").get_editor_property(k)), 5)
                    for k in ("global_delta", "high_frequency_delta", "head_scale")}}
    for prop in ("has_high_resolution_textures", "fixed_body_type", "template_type", "has_face_dna_blendshapes"):
        try:
            out[prop] = sdump(ch.get_editor_property(prop))
        except Exception as exc:  # noqa: BLE001
            out[prop] = "ERR " + repr(exc)[:80]
    return out


def eye_mids(actor):
    face = find_comp(actor, "Face")
    out = {}
    for i, slot in enumerate(str(s) for s in face.get_material_slot_names()):
        if slot.startswith("eyeLeft") or slot.startswith("eyeRight"):
            m = face.get_material(i)
            vals = {"material": pth(m)}
            for n in ("Iris Primary Color Hue", "Iris Primary Color Value", "Iris Secondary Color Hue",
                      "Iris Secondary Color Value"):
                v = "n/a"
                for attr in ("k2_get_scalar_parameter_value", "get_scalar_parameter_value"):
                    fn = getattr(m, attr, None)
                    if fn is not None:
                        try:
                            v = round(float(fn(n)), 4)
                            break
                        except Exception as exc:  # noqa: BLE001
                            v = "ERR " + repr(exc)[:60]
                vals[n] = v
            out[slot] = vals
    return out


def spawn(ch, assemble=True):
    a = mhs().spawn_meta_human_actor(ch, True)
    if a is None:
        raise RuntimeError(f"spawn failed {pth(ch)}")
    if assemble:
        mhs().assemble_for_preview(ch)
    return a


def crown_probe(scene) -> dict:
    """Face_Front studio capture; median luma of the crown (hair = dark ~50-65, bald scalp = lit skin ~130)."""
    loc, look, fov = VIEWS["Face_Front"]
    scene.aim(loc, look, fov)
    scene.apply_hidden()
    scene.cap.capture_scene()
    lum = []
    for x in range(400, 601, 25):
        for y in range(275, 336, 15):
            c = ue.RenderingLibrary.read_render_target_pixel(scene.world, scene.rt, x, y)
            lum.append(0.299 * c.r + 0.587 * c.g + 0.114 * c.b)
    lum.sort()
    med = lum[len(lum) // 2]
    return {"crown_luma_median": round(med, 1), "hair": med < 95.0}


def groom_rows(actor):
    rows = []
    for c in actor.get_components_by_class(ue.GroomComponent):
        rows.append({"name": c.get_name(), "groom": pth(c.get_editor_property("groom_asset")),
                     "binding": pth(c.get_editor_property("binding_asset")), "visible": bool(c.is_visible())})
    return rows


# ---------------------------------------------------------------------------------------------------------------
def job(scene: Scene):
    R = REPORT.setdefault("results", {})
    recipe = json.loads(RECIPE.read_text(encoding="utf-8"))
    build = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))["build"]
    fbr = json.loads(FACE_BUILD_REPORT.read_text(encoding="utf-8"))["build"]
    facec_ref = fbr["candidates"]["MH_PlayerBase_FaceC"]
    probe = json.loads(FACE_PROBE_REPORT.read_text(encoding="utf-8"))["probe"]
    lay = C.PFB.layout(probe["base"]["coeffs"])
    R["layout_n_regions"] = len(lay)

    # ===== A) MH_PlayerDefault from disk (first MetaHuman of the session) =====
    check("pd_exists", ue.EditorAssetLibrary.does_asset_exist(PD_PATH))
    pd = ue.load_asset(PD_PATH)
    check("pd_is_metahumancharacter", isinstance(pd, ue.MetaHumanCharacter), cls=type(pd).__name__)
    R["pd_identity_disk"] = identity(pd)
    R["pd_internal_collection_disk"] = coll_state(pd.get_editor_property("internal_collection"))
    # skin of the other candidates (load only, nothing edited)
    R["other_skins"] = {}
    for n in ("MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC"):
        o = ue.load_asset(f"{CHAR_DIR}/{n}")
        idn = identity(o)
        R["other_skins"][n] = {k: idn[k] for k in ("face_texture_index", "body_texture_index", "u", "v",
                                                   "freckles_mask", "iris")}
        R["other_skins"][n]["internal_collection"] = coll_state(o.get_editor_property("internal_collection"))["selections"]
    open_edit(pd)
    step("IC2_MARK can_build_meta_human(pd, log=True) BEGIN")
    R["pd_can_build"] = bool(mhs().can_build_meta_human(pd, True))
    step("IC2_MARK can_build_meta_human END", result=R["pd_can_build"])
    pd_c = coeffs(pd)
    R["pd_coeffs"] = pd_c
    R["pd_coeffs_maxdiff_vs_recipe_final"] = maxdiff(pd_c, recipe["face"]["coeffs_final"])
    R["pd_coeffs_maxdiff_vs_build_final"] = maxdiff(pd_c, build["coeffs_final"])
    check("coeffs_equal_recipe_final", R["pd_coeffs_maxdiff_vs_recipe_final"] == 0.0,
          maxdiff=R["pd_coeffs_maxdiff_vs_recipe_final"], vs_build=R["pd_coeffs_maxdiff_vs_build_final"])
    R["pd_coeffs_maxdiff_vs_facec_report"] = maxdiff(pd_c, facec_ref["coeffs"])
    R["pd_regions_vs_facec_report"] = region_diffs(pd_c, facec_ref["coeffs"], lay)
    check("coeff_changes_only_regions_19_20_21", set(R["pd_regions_vs_facec_report"]) <= {"19", "20", "21"},
          regions=R["pd_regions_vs_facec_report"], maxdiff=R["pd_coeffs_maxdiff_vs_facec_report"])
    pd_lm = landmarks(pd)
    R["pd_landmarks"] = pd_lm
    R["pd_landmark_deltas_vs_facec_report"] = {str(i): [round(a - b, 4) for a, b in zip(p, q)]
                                              for i, (p, q) in enumerate(zip(pd_lm, facec_ref["landmarks"]))
                                              if max(abs(a - b) for a, b in zip(p, q)) > 1e-3}
    R["pd_eval"] = R["pd_identity_disk"]["eval"]
    check("eval_settings_equal_facec_report", R["pd_eval"] == facec_ref["eval"], got=R["pd_eval"], want=facec_ref["eval"])
    pd_con = constraints(pd)
    R["pd_constraints_n"] = len(pd_con)
    yield

    actor = spawn(pd)
    t_spawn = time.monotonic()
    # hair probe on this fresh load: NO re-assembly for the first 150 s
    probes = []
    first_saved = False
    reassembled = False
    while True:
        yield from settle()
        pr = crown_probe(scene)
        pr["t_since_spawn_s"] = round(time.monotonic() - t_spawn, 1)
        pr["reassembled_before"] = reassembled
        pr["grooms"] = {g["name"]: bool(g["groom"]) for g in groom_rows(actor)}
        probes.append(pr)
        if not first_saved:
            scene.export("ic2_probe_first_Face_Front.png")
            first_saved = True
        if pr["hair"]:
            scene.export("ic2_probe_hair_drawn_Face_Front.png")
            break
        el = time.monotonic() - t_spawn
        if el > 150 and not reassembled:
            mhs().assemble_for_preview(pd)
            reassembled = True
            step("hair not drawn after 150 s: re-assembled the preview")
        if el > 330:
            scene.export("ic2_probe_hair_never_drawn_Face_Front.png")
            break
        yield from warmup(40, 2.0)
    R["hair_probes"] = probes
    check("hair_drawn_on_fresh_load", probes[-1]["hair"], t_s=probes[-1]["t_since_spawn_s"],
          reassembled=reassembled, n=len(probes))
    yield from warmup(200, 10.0)
    R["pd_preview_collection"] = coll_state(mhs().get_preview_collection(pd))
    R["pd_internal_collection_after_assembly"] = coll_state(pd.get_editor_property("internal_collection"))
    R["pd_components"] = comp_inventory(actor)
    R["pd_grooms"] = groom_rows(actor)
    R["pd_eye_mids"] = eye_mids(actor)
    R["pd_bones"] = bones(actor)
    pd_body = dump_verts(find_comp(actor, "Body"), "ic2_PD_Body")
    pd_face = dump_verts(find_comp(actor, "Face"), "ic2_PD_Face")
    R["pd_mesh_sizes"] = {"body": [len(pd_body[0]), len(pd_body[1])], "face": [len(pd_face[0]), len(pd_face[1])]}
    write_report()
    yield from shoot_plan(scene, "ic2_pd_", PD_PLAN)
    R["hair_probe_after_captures"] = crown_probe(scene)
    scene.eas.destroy_actor(actor)
    yield from warmup(30, 1.0)

    # ===== B) FaceC scratch duplicate = BEFORE; then independent re-application of the recipe's jaw fix =====
    fc = scratch_dup(FACEC_PATH, "IC2_FaceC")
    open_edit(fc)
    fc_c = coeffs(fc)
    R["facec_dup_coeffs_maxdiff_vs_report"] = maxdiff(fc_c, facec_ref["coeffs"])
    check("facec_asset_equals_face_build_report", R["facec_dup_coeffs_maxdiff_vs_report"] == 0.0,
          maxdiff=R["facec_dup_coeffs_maxdiff_vs_report"])
    R["facec_identity"] = {k: v for k, v in identity(fc).items() if k in ("face_texture_index", "u", "v", "freckles_mask",
                                                                          "iris", "eval")}
    R["compare_face_state_pd_vs_facec"] = {str(t): bool(mhs().compare_face_state(pd, fc, t)) for t in (0.0, 1e-3, 0.1)}
    R["compare_body_state_pd_vs_facec"] = {str(t): bool(mhs().compare_body_state(pd, fc, t)) for t in (0.0, 1e-3)}
    fa = spawn(fc)
    yield from warmup(200, 10.0)
    fc_face = dump_verts(find_comp(fa, "Face"), "ic2_FaceC_Face")
    fc_body = dump_verts(find_comp(fa, "Body"))
    R["face_mesh_pd_vs_facec"] = mesh_diff(pd_face, fc_face)
    R["body_mesh_pd_vs_facec"] = mesh_diff(pd_body, fc_body)
    step("mesh compare vs FaceC", face=R["face_mesh_pd_vs_facec"], body=R["body_mesh_pd_vs_facec"])
    yield from shoot_plan(scene, "ic2_facec_", FACEC_PLAN)
    # --- reproduce the jaw fix from the RECIPE on the FaceC duplicate ---
    moves = recipe["face"]["jaw_fix"]["moves"]
    idx = ue.Array(int)
    deltas = ue.Array(ue.Vector)
    flat = []
    for mv in moves:
        for k, i in enumerate(mv["idx"]):
            d = mv["d_per"][k]
            idx.append(int(i))
            deltas.append(ue.Vector(float(d[0]), float(d[1]), float(d[2])))
            flat.append([int(i)] + [float(x) for x in d])
    R["repro_moves"] = flat
    mhs().translate_face_landmarks(fc, idx, deltas)
    mhs().commit_face_state(fc)
    yield from warmup(60, 3.0)
    rc = coeffs(fc)
    R["repro_coeffs_maxdiff_vs_pd"] = maxdiff(rc, pd_c)
    R["repro_regions_vs_pd"] = region_diffs(rc, pd_c, lay)
    check("jaw_fix_reproduces_pd_coeffs", isinstance(R["repro_coeffs_maxdiff_vs_pd"], float)
          and R["repro_coeffs_maxdiff_vs_pd"] < 1e-5, maxdiff=R["repro_coeffs_maxdiff_vs_pd"],
          regions=R["repro_regions_vs_pd"])
    R["repro_landmarks_maxdiff_vs_pd"] = max(max(abs(a - b) for a, b in zip(p, q)) for p, q in zip(landmarks(fc), pd_lm))
    repro_face = dump_verts(find_comp(fa, "Face"), "ic2_Repro_Face")
    R["face_mesh_repro_vs_pd"] = mesh_diff(repro_face, pd_face)
    check("jaw_fix_reproduces_pd_face_mesh", R["face_mesh_repro_vs_pd"].get("max_dist_cm", 1.0) < 1e-3,
          detail=R["face_mesh_repro_vs_pd"])
    mhs().commit_skin_settings(fc, pd.get_editor_property("skin_settings"))
    mhs().commit_head_model_settings(fc, pd.get_editor_property("head_model_settings"))
    yield from warmup(30, 1.0)
    R["compare_face_state_pd_vs_repro_with_pd_identity"] = {str(t): bool(mhs().compare_face_state(pd, fc, t))
                                                           for t in (0.0, 1e-5, 1e-3)}
    step("face state compare vs reproduced fix", detail=R["compare_face_state_pd_vs_repro_with_pd_identity"])
    scene.eas.destroy_actor(fa)
    close_edit(fc)
    yield from warmup(30, 1.0)

    # ===== C) MH_PlayerBase scratch duplicate: body reference =====
    pb = scratch_dup(BASE_PATH, "IC2_PlayerBase")
    open_edit(pb)
    R["compare_body_state_pd_vs_playerbase"] = {str(t): bool(mhs().compare_body_state(pd, pb, t)) for t in (0.0, 1e-5, 1e-3)}
    check("body_state_equals_playerbase", R["compare_body_state_pd_vs_playerbase"]["0.0"],
          detail=R["compare_body_state_pd_vs_playerbase"])
    pb_con = constraints(pb)
    R["constraints_keys_equal"] = sorted(pb_con) == sorted(pd_con)
    R["constraints_maxdiff_vs_playerbase"] = max((abs(pd_con[k][0] - pb_con[k][0]) for k in pd_con if k in pb_con), default=None)
    R["constraints_active_equal"] = all(pd_con[k][1] == pb_con[k][1] for k in pd_con if k in pb_con)
    check("constraints_equal_playerbase", R["constraints_keys_equal"] and R["constraints_active_equal"]
          and R["constraints_maxdiff_vs_playerbase"] == 0.0, n=len(pd_con), maxdiff=R["constraints_maxdiff_vs_playerbase"])
    pa = spawn(pb)
    yield from warmup(200, 10.0)
    pb_bones = bones(pa)
    bd = [max(abs(a - b) for a, b in zip(R["pd_bones"][k], pb_bones[k])) for k in R["pd_bones"] if k in pb_bones]
    R["bones_n_pd"], R["bones_n_pb"], R["bones_compared"] = len(R["pd_bones"]), len(pb_bones), len(bd)
    R["bones_maxdiff_vs_playerbase"] = max(bd) if bd else None
    check("bones_equal_playerbase", bool(bd) and len(bd) == len(R["pd_bones"]) == len(pb_bones) and max(bd) < 1e-4,
          n=len(bd), maxdiff=R["bones_maxdiff_vs_playerbase"])
    pb_body = dump_verts(find_comp(pa, "Body"))
    R["body_mesh_pd_vs_playerbase"] = mesh_diff(pd_body, pb_body)
    check("body_mesh_equals_playerbase", R["body_mesh_pd_vs_playerbase"].get("max_dist_cm") == 0.0
          and R["body_mesh_pd_vs_playerbase"]["tris_identical"], detail=R["body_mesh_pd_vs_playerbase"])
    pb_face = dump_verts(find_comp(pa, "Face"), "ic2_PlayerBase_Face")
    R["face_mesh_pd_vs_playerbase"] = mesh_diff(pd_face, pb_face)
    scene.eas.destroy_actor(pa)
    yield from warmup(30, 1.0)

    # ===== D) negative control: MH_MaleBase dup =====
    mb = scratch_dup(MALE_PATH, "IC2_MaleBase")
    open_edit(mb)
    R["negative_control_body_vs_malebase"] = {str(t): bool(mhs().compare_body_state(pd, mb, t)) for t in (0.1, 1.0)}
    R["negative_control_face_vs_malebase"] = {str(t): bool(mhs().compare_face_state(pd, mb, t)) for t in (0.1, 1.0)}
    check("negative_control_detects_difference", not R["negative_control_body_vs_malebase"]["0.1"]
          and not R["negative_control_face_vs_malebase"]["0.1"],
          body=R["negative_control_body_vs_malebase"], face=R["negative_control_face_vs_malebase"])
    close_edit(mb)
    close_edit(pb)
    yield

    # ===== E) Epic preset Kelvin (grooms hidden), moved so its face centre = the camera target (as the fixer) =====
    try:
        kd = scratch_dup(KELVIN_PRESET, "IC2_Kelvin")
        open_edit(kd)
        ka = spawn(kd)
        kc = probe["kelvin_face_center"]
        off = [C.FACE_CENTER[i] - kc[i] for i in range(3)]
        ka.set_actor_location(ue.Vector(*off), False, False)
        R["kelvin_offset"] = off
        yield from warmup(200, 10.0)
        scene.extra_hidden_components = list(ka.get_components_by_class(ue.GroomComponent))
        yield from shoot_plan(scene, "ic2_kelvin_", KELVIN_PLAN)
        scene.extra_hidden_components = []
        scene.eas.destroy_actor(ka)
        close_edit(kd)
    except Exception as exc:  # noqa: BLE001
        REPORT["warnings"].append("kelvin reference failed: " + traceback.format_exc()[-600:])
        step("WARNING kelvin reference failed", err=repr(exc)[:300])
    close_edit(pd)
    R["pd_dirty_at_end"] = None
    try:
        R["pd_dirty_at_end"] = bool(pd.get_outermost().is_dirty())
    except Exception as exc:  # noqa: BLE001
        R["pd_dirty_at_end"] = "n/a " + repr(exc)[:80]
    step("job done (nothing saved)")


class Runner:
    def __init__(self, scene, gen):
        self.scene, self.gen, self.busy, self.done, self.h = scene, gen, False, False, None

    def start(self):
        self.h = ue.register_slate_post_tick_callback(self.tick)
        ue.EditorPythonScripting.set_keep_python_script_alive(True)

    def tick(self, _dt):
        if self.busy or self.done:
            return
        self.busy = True
        try:
            if time.monotonic() - T0 > MAX_SECONDS:
                raise TimeoutError("run exceeded time budget")
            self.scene.cap.capture_scene()
            next(self.gen)
        except StopIteration:
            self.finish(True)
        except Exception:  # noqa: BLE001
            REPORT["error"] = traceback.format_exc()
            step("ERROR", error=REPORT["error"][-1500:])
            self.finish(False)
        finally:
            self.busy = False

    def finish(self, ok):
        if self.done:
            return
        self.done = True
        if self.h is not None:
            ue.unregister_slate_post_tick_callback(self.h)
        for ch in list(OPEN):
            try:
                close_edit(ch)
            except Exception:  # noqa: BLE001
                REPORT.setdefault("teardown_errors", []).append(traceback.format_exc()[-400:])
        REPORT["sha_end"] = hashes()
        REPORT["hashes_unchanged_in_session"] = REPORT["sha_end"] == REPORT.get("sha_start")
        REPORT["scratch_on_disk_end"] = (ROOT / "Exports/CharacterLab/Unreal/Content/PlayerDefault").exists()
        REPORT["status"] = "done" if ok else "failed"
        step("STATUS " + REPORT["status"], unchanged=REPORT["hashes_unchanged_in_session"])
        ue.SystemLibrary.quit_editor()


def main():
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"\n===== pd_ic2_verify.py {now()} =====\n")
    if not REPORT["engine"].startswith("5.8"):
        raise RuntimeError("expected UE 5.8")
    REPORT["sha_start"] = hashes()
    scene = Scene()
    step("scene ready")
    Runner(scene, job(scene)).start()


try:
    OUT.mkdir(parents=True, exist_ok=True)
    main()
except Exception:  # noqa: BLE001
    REPORT["error"] = traceback.format_exc()
    REPORT["status"] = "failed"
    write_report()
    for _c in list(OPEN):
        try:
            close_edit(_c)
        except Exception:  # noqa: BLE001
            pass
    ue.SystemLibrary.quit_editor()
