"""pd_ic_verify.py -- INDEPENDENT integrity check of /Game/Characters/MetaHumans/MH_PlayerDefault (UE 5.8.3).

Runs INSIDE UnrealEditor (CharacterLab.uproject), launched by Scripts/MetaHuman/pd_ic_run.ps1. SAVES NOTHING.
Never signs in; never calls request_auto_rigging / request_texture_sources / build_meta_human.

Checks (written independently of pd_player_default.py; only the studio light rig + camera constants are copied from
pb_conform.py / pd_player_default.py so captures are comparable):
  * MH_PlayerDefault loads from disk as a MetaHumanCharacter; identity settings read back (skin, eyes, lashes, makeup,
    collections, groom instance params, groom components, eye MIDs, all actor components)
  * unrigged: can_build_meta_human(pd, True) logs its refusal reason into the engine log (grep offline)
  * face coefficients / landmarks / eval settings vs face_build_report_2.json FaceC AND vs a fresh scratch dup of FaceC
  * compare_face_state vs FaceC before / after copying PD's skin + head-model settings onto the FaceC dup
  * body: compare_body_state vs MH_PlayerBase dup, constraints, all bones, full body vertex compare; negative
    control compare_*_state vs MH_MaleBase dup (must be False)
  * captures: studio rig (same cameras), plus headlight (geometry-only shading), ambient, rimspec0, rimshadow,
    chroma (green backdrop -> see-through test), base colour; Epic preset Kelvin (grooms hidden) as a reference
Scratch duplicates live in /Game/PlayerDefault/Scratch as IC_* and are never saved.
Outputs: WorkFiles/MetaHuman/player_default/integrity_check/ (ic_report.json, ic.log, captures/ic_*.png)
"""
from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import time
import traceback
from pathlib import Path

import unreal as ue

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/MetaHuman/player_default/integrity_check"
CAP = OUT / "captures"
REPORT_PATH = OUT / "ic_report.json"
LOG = OUT / "ic.log"
CONTENT = ROOT / "Exports/CharacterLab/Unreal/Content/Characters/MetaHumans"
PROTECTED = ["MH_PlayerBase", "MH_PlayerBase_FaceA", "MH_PlayerBase_FaceB", "MH_PlayerBase_FaceC", "MH_MaleBase",
             "MH_PlayerDefault"]
FACE_BUILD_REPORT = ROOT / "WorkFiles/MetaHuman/player_base/faces/face_build_report_2.json"
CHAR_DIR = "/Game/Characters/MetaHumans"
PD_PATH = f"{CHAR_DIR}/MH_PlayerDefault"
FACEC_PATH = f"{CHAR_DIR}/MH_PlayerBase_FaceC"
BASE_PATH = f"{CHAR_DIR}/MH_PlayerBase"
MALE_PATH = f"{CHAR_DIR}/MH_MaleBase"
KELVIN_PRESET = "/MetaHumanCharacter/Optional/Presets/Kelvin"
SCRATCH = "/Game/PlayerDefault/Scratch"
MAX_SECONDS = 35 * 60.0

# ---- studio rig + cameras: values identical to pb_conform.py / pd_player_default.py --------------------------
LIGHT_RIG = [(-27.0, -117.0, 0.0, 4.0, (1, .95, .9), True),
             (-12.0, -58.0, 0.0, 2.0, (.9, .94, 1), False),
             (-37.0, 90.0, 0.0, 2.0, (1, 1, 1), False)]
SKY_INTENSITY = 1.5
CVARS = ["r.DynamicGlobalIlluminationMethod 0", "r.ReflectionMethod 0", "r.AmbientOcclusionLevels 0",
         "r.DistanceFieldAO 0", "r.RayTracing.ForceAllRayTracingEffects 0", "r.AntiAliasingMethod 2"]
SHOT_W, SHOT_H = 1000, 1200
FACE_CAM_DIST = 70.0
FACE_CENTER = (0.0, 5.959721088409424, 173.6)
BODY_CAM_DIST, BODY_CAM_Z = 380.0, 93.0

T0 = time.monotonic()
REPORT: dict = {"script": "Scripts/MetaHuman/pd_ic_verify.py", "engine": ue.SystemLibrary.get_engine_version(),
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
    ue.log("PD_IC " + line)
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
    return {n: sha(CONTENT / f"{n}.uasset") for n in PROTECTED}


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


class Scene:
    def __init__(self):
        ue.EditorLoadingAndSavingUtils.new_blank_map(False)
        self.world = ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_editor_world()
        self.eas = ue.get_editor_subsystem(ue.EditorActorSubsystem)
        self.lights = [self.spawn(ue.DirectionalLight) for _ in LIGHT_RIG]
        self.grey = self.sphere(50.0, unlit_material((.18, .18, .18)))
        self.green = self.sphere(52.0, unlit_material((0.0, 1.0, 0.0)))   # outside the grey one: never seen unless grey hidden
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
        REPORT.setdefault("sky_switches", []).append(
            {"ambient": ambient, "threshold": comp.get_editor_property("sky_distance_threshold"),
             "lower_black": comp.get_editor_property("lower_hemisphere_is_black")})
        self.sky_ambient = ambient
        return True

    def set_variant(self, variant: str) -> bool:
        """studio | ambient | headlight | rimspec0 | rimshadow | chroma | base"""
        for light, (pitch, yaw, roll, inten, col, shadows) in zip(self.lights, LIGHT_RIG):
            light.set_actor_rotation(ue.Rotator(roll=roll, pitch=pitch, yaw=yaw), False)
            lc = light.light_component
            lc.set_intensity(inten)
            lc.set_light_color(ue.LinearColor(*col, 1))
            lc.set_cast_shadows(shadows)
            spec(lc, 1.0)
        self.sky.light_component.set_intensity(SKY_INTENSITY)
        self.cap.set_editor_property("capture_source", ue.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        key, fill, rim = self.lights
        if variant == "headlight":
            # one unshadowed, diffuse-only light travelling along the camera's view direction (aimed per shot):
            # every surface the camera sees gets N.L = N.V > 0, so a crisp black line can only be geometry/normals/albedo
            fill.light_component.set_intensity(0.0)
            rim.light_component.set_intensity(0.0)
            key.light_component.set_intensity(3.0)
            key.light_component.set_light_color(ue.LinearColor(1, 1, 1, 1))
            key.light_component.set_cast_shadows(False)
            spec(key.light_component, 0.0)
            self.sky.light_component.set_intensity(0.0)
        if variant == "rimspec0":
            spec(rim.light_component, 0.0)
        if variant == "rimshadow":
            rim.light_component.set_cast_shadows(True)
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


def spec(lc, value):
    try:
        lc.set_specular_scale(float(value))
    except Exception:  # noqa: BLE001
        lc.set_editor_property("specular_scale", float(value))
    try:
        REPORT.setdefault("spec_readback", {})[lc.get_owner().get_name()] = float(lc.get_editor_property("specular_scale"))
    except Exception:  # noqa: BLE001
        pass


def orbit(t, dist, az, el):
    a, e = math.radians(az), math.radians(el)
    return (t[0] + dist * math.cos(e) * math.sin(a), t[1] + dist * math.cos(e) * math.cos(a), t[2] + dist * math.sin(e))


def views(center=FACE_CENTER, body_offset=(0.0, 0.0, 0.0)):
    fx, fy, fz = center
    c = center
    d = FACE_CAM_DIST
    a = math.radians(35.0)
    v = {"Face_Front": ((fx, fy + d, fz), c, 30.0),
         "Face_ThreeQuarter": ((fx + d * math.sin(a), fy + d * math.cos(a), fz), c, 30.0),
         "Face_Profile": ((fx + d, fy, fz), c, 30.0)}
    ox, oy, oz = body_offset
    z = BODY_CAM_Z + oz
    v["Body_Front"] = ((ox, BODY_CAM_DIST, z), (ox, 0.0, z), 30.0)
    v["Body_Back"] = ((ox, -BODY_CAM_DIST, z), (ox, 0.0, z), 30.0)
    jaw = (fx + 2.0, fy + 1.0, fz - 10.0)
    jaw_l = (fx + 4.5, fy - 1.0, fz - 9.5)
    ear_r = (fx - 7.9, fy - 1.5, fz - 1.2)
    v["JawClose"] = (orbit(jaw_l, 32.0, 40, -8), jaw_l, 22.0)
    v["JawLow"] = (orbit(jaw, 60.0, 35, -28), jaw, 30.0)
    v["EarR"] = (orbit(ear_r, 32.0, 0, 0), ear_r, 20.0)
    sh = (0.0, 0.0, 150.0)
    v["Shoulders_Front"] = ((0.0, 115.0, 156.0), sh, 26.0)
    v["Shoulders_High"] = (orbit(sh, 110.0, 0, 42), sh, 26.0)
    v["ShoulderL_TQ"] = (orbit((15.0, 0.0, 150.0), 75.0, 40, 12), (15.0, 0.0, 150.0), 26.0)
    v["ShoulderR_TQ"] = (orbit((-15.0, 0.0, 150.0), 75.0, -40, 12), (-15.0, 0.0, 150.0), 26.0)
    v["Shoulders_Back"] = ((0.0, -115.0, 156.0), sh, 26.0)
    v["Eyes"] = ((fx, fy + 45.0, fz + 0.8), (fx, fy, fz + 0.8), 16.0)
    head = (fx, fy - 2.0, fz + 3.0)
    v["Head_Back34"] = (orbit(head, 75.0, 145, 10), head, 30.0)
    v["Head_Back"] = (orbit(head, 70.0, 180, 12), head, 30.0)
    v["Head_Top"] = (orbit(head, 70.0, 20, 50), head, 30.0)
    return v


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


def shoot_plan(scene, prefix, vset, plan):
    for variant, names in plan:
        if scene.set_variant(variant):
            yield from warmup(90, 3.0)
        else:
            yield from warmup(20, 0.8)
        for n in names:
            yield from shoot(scene, f"{prefix}{variant}_{n}.png", vset[n])
    if scene.set_variant("studio"):
        yield from warmup(90, 3.0)


PD_PLAN = [
    ("studio", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "JawLow", "EarR", "Shoulders_Front",
                "Shoulders_High", "ShoulderL_TQ", "ShoulderR_TQ", "Shoulders_Back", "Body_Front", "Body_Back", "Eyes",
                "Head_Back34", "Head_Back", "Head_Top"]),
    ("headlight", ["Face_Front", "Face_ThreeQuarter", "Face_Profile", "JawClose", "JawLow", "EarR"]),
    ("rimspec0", ["Face_Front", "EarR"]),
    ("rimshadow", ["Face_Front", "EarR", "Body_Back", "Head_Back", "Head_Back34"]),
    ("chroma", ["Face_Front", "Face_ThreeQuarter", "Shoulders_Front", "Shoulders_High", "ShoulderL_TQ", "ShoulderR_TQ",
                "Shoulders_Back", "Body_Front", "Body_Back"]),
    ("base", ["Face_Front", "Face_ThreeQuarter", "JawClose", "EarR"]),
    ("ambient", ["Face_Front", "Face_ThreeQuarter", "JawClose", "JawLow", "EarR", "Body_Back", "Head_Back"]),
]


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


def dump_verts(comp):
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
    return verts, tris


def mesh_diff(a, b, tol=1e-3):
    va, ta = a
    vb, tb = b
    out = {"verts": [len(va), len(vb)], "tris": [len(ta), len(tb)], "tris_identical": ta == tb}
    if len(va) != len(vb):
        return out
    moved = []
    mx = 0.0
    for i, (p, q) in enumerate(zip(va, vb)):
        d = math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2)
        mx = max(mx, d)
        if d > tol:
            moved.append(i)
    out["max_dist_cm"] = mx
    out["moved_gt_tol"] = len(moved)
    if moved:
        out["moved_index_range"] = [moved[0], moved[-1]]
        zs = [va[i][2] for i in moved]
        out["moved_z_range"] = [round(min(zs), 2), round(max(zs), 2)]
    return out


def bones(actor):
    body = find_comp(actor, "Body")
    res = {}
    n = body.get_num_bones()
    for i in range(n):
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
           "show_top_underwear": bool(sk.get_editor_property("show_top_underwear")),
           "freckles_mask": es(s.get_editor_property("freckles").get_editor_property("mask")),
           "enable_texture_overrides": bool(s.get_editor_property("enable_texture_overrides")),
           "iris": iris,
           "eyelashes": sdump(el),
           "makeup": sdump(mk),
           "skin_settings_full": sdump(s),
           "head_model_full": sdump(hm)}
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


def spawn(ch):
    a = mhs().spawn_meta_human_actor(ch, True)
    if a is None:
        raise RuntimeError(f"spawn failed {pth(ch)}")
    mhs().assemble_for_preview(ch)
    return a


def head_bone(actor):
    return vec(find_comp(actor, "Body").get_socket_location("head"))


# ---------------------------------------------------------------------------------------------------------------
def job(scene: Scene):
    R = REPORT.setdefault("results", {})
    ref = json.loads(FACE_BUILD_REPORT.read_text(encoding="utf-8"))["build"]["candidates"]["MH_PlayerBase_FaceC"]

    # ===== A) MH_PlayerDefault from disk =====
    check("pd_exists", ue.EditorAssetLibrary.does_asset_exist(PD_PATH))
    pd = ue.load_asset(PD_PATH)
    check("pd_is_metahumancharacter", isinstance(pd, ue.MetaHumanCharacter), cls=type(pd).__name__)
    R["pd_identity_disk"] = identity(pd)
    R["pd_internal_collection_disk"] = coll_state(pd.get_editor_property("internal_collection"))
    open_edit(pd)
    step("IC_MARK can_build_meta_human(pd, log=True) BEGIN")
    R["pd_can_build"] = bool(mhs().can_build_meta_human(pd, True))
    step("IC_MARK can_build_meta_human END", result=R["pd_can_build"])
    for fn in ("is_auto_rigging_face", "is_requesting_high_resolution_textures"):
        if hasattr(mhs(), fn):
            try:
                R[fn] = bool(getattr(mhs(), fn)(pd))
            except Exception as exc:  # noqa: BLE001
                R[fn] = "ERR " + repr(exc)[:80]
    pd_c = coeffs(pd)
    R["pd_coeffs_len"] = len(pd_c)
    R["pd_coeffs_maxdiff_vs_report"] = maxdiff(pd_c, ref["coeffs"])
    check("coeffs_equal_facec_report", R["pd_coeffs_maxdiff_vs_report"] == 0.0, maxdiff=R["pd_coeffs_maxdiff_vs_report"])
    pd_lm = landmarks(pd)
    R["pd_landmarks_maxdiff_vs_report"] = max(max(abs(a - b) for a, b in zip(p, q)) for p, q in zip(pd_lm, ref["landmarks"]))
    check("landmarks_equal_facec_report", R["pd_landmarks_maxdiff_vs_report"] < 1e-3,
          maxdiff=R["pd_landmarks_maxdiff_vs_report"])
    ev = pd.get_editor_property("face_evaluation_settings")
    R["pd_eval"] = {k: round(float(ev.get_editor_property(k)), 5) for k in ("global_delta", "high_frequency_delta", "head_scale")}
    check("eval_settings_equal_facec_report", R["pd_eval"] == ref["eval"], got=R["pd_eval"], want=ref["eval"])
    pd_con = constraints(pd)
    R["pd_constraints_n"] = len(pd_con)
    yield

    actor = spawn(pd)
    yield from warmup(300, 15.0)
    R["pd_preview_collection"] = coll_state(mhs().get_preview_collection(pd))
    try:
        R["pd_internal_collection_after_assembly"] = coll_state(pd.get_editor_property("internal_collection"))
    except Exception as exc:  # noqa: BLE001
        R["pd_internal_collection_after_assembly"] = "ERR " + repr(exc)[:120]
    R["pd_components"] = comp_inventory(actor)
    R["pd_eye_mids"] = eye_mids(actor)
    R["pd_bones"] = bones(actor)
    pd_head = head_bone(actor)
    R["pd_head_bone"] = pd_head
    pd_body = dump_verts(find_comp(actor, "Body"))
    pd_face = dump_verts(find_comp(actor, "Face"))
    R["pd_mesh_sizes"] = {"body": [len(pd_body[0]), len(pd_body[1])], "face": [len(pd_face[0]), len(pd_face[1])]}
    write_report()
    yield from shoot_plan(scene, "ic_pd_", views(), PD_PLAN)
    scene.eas.destroy_actor(actor)
    yield from warmup(30, 1.0)

    # ===== B) FaceC scratch duplicate =====
    fc = scratch_dup(FACEC_PATH, "IC_FaceC")
    open_edit(fc)
    fc_c = coeffs(fc)
    R["facec_dup_coeffs_maxdiff_vs_report"] = maxdiff(fc_c, ref["coeffs"])
    R["pd_vs_facec_dup_coeffs_maxdiff"] = maxdiff(pd_c, fc_c)
    check("coeffs_equal_facec_asset", R["pd_vs_facec_dup_coeffs_maxdiff"] == 0.0,
          maxdiff=R["pd_vs_facec_dup_coeffs_maxdiff"], facec_vs_report=R["facec_dup_coeffs_maxdiff_vs_report"])
    R["pd_vs_facec_dup_landmarks_maxdiff"] = max(max(abs(a - b) for a, b in zip(p, q)) for p, q in zip(pd_lm, landmarks(fc)))
    R["facec_dup_identity"] = identity(fc)
    R["compare_face_state_pd_vs_facec"] = {str(t): bool(mhs().compare_face_state(pd, fc, t)) for t in (0.0, 1e-3, 0.1)}
    R["compare_body_state_pd_vs_facec"] = {str(t): bool(mhs().compare_body_state(pd, fc, t)) for t in (0.0, 1e-3)}
    step("state compare vs FaceC", face=R["compare_face_state_pd_vs_facec"], body=R["compare_body_state_pd_vs_facec"])
    fa = spawn(fc)
    yield from warmup(200, 10.0)
    fc_face = dump_verts(find_comp(fa, "Face"))
    fc_body = dump_verts(find_comp(fa, "Body"))
    R["face_mesh_pd_vs_facec"] = mesh_diff(pd_face, fc_face)
    R["body_mesh_pd_vs_facec"] = mesh_diff(pd_body, fc_body)
    step("mesh compare vs FaceC", face=R["face_mesh_pd_vs_facec"], body=R["body_mesh_pd_vs_facec"])
    R["facec_bones_maxdiff_vs_pd"] = max(max(abs(a - b) for a, b in zip(p, R["pd_bones"][k]))
                                         for k, p in bones(fa).items() if k in R["pd_bones"])
    yield from shoot_plan(scene, "ic_facec_", views(), [("studio", ["Face_ThreeQuarter", "JawClose", "ShoulderL_TQ"]),
                                                        ("headlight", ["Face_ThreeQuarter", "JawClose", "JawLow"]),
                                                        ("chroma", ["Shoulders_Front", "ShoulderL_TQ", "Shoulders_Back"])])
    scene.eas.destroy_actor(fa)
    yield from warmup(30, 1.0)
    # copy PD's identity settings (skin + head model: texture variant, lashes) onto the FaceC dup, then compare states
    mhs().commit_skin_settings(fc, pd.get_editor_property("skin_settings"))
    mhs().commit_head_model_settings(fc, pd.get_editor_property("head_model_settings"))
    yield from warmup(30, 1.0)
    R["compare_face_state_pd_vs_facec_with_pd_identity"] = {str(t): bool(mhs().compare_face_state(pd, fc, t))
                                                           for t in (0.0, 1e-5, 1e-3)}
    check("face_state_equals_facec_plus_identity", R["compare_face_state_pd_vs_facec_with_pd_identity"]["0.0"],
          detail=R["compare_face_state_pd_vs_facec_with_pd_identity"])
    close_edit(fc)
    yield

    # ===== C) MH_PlayerBase scratch duplicate: body reference =====
    pb = scratch_dup(BASE_PATH, "IC_PlayerBase")
    open_edit(pb)
    R["compare_body_state_pd_vs_playerbase"] = {str(t): bool(mhs().compare_body_state(pd, pb, t)) for t in (0.0, 1e-5, 1e-3)}
    check("body_state_equals_playerbase", R["compare_body_state_pd_vs_playerbase"]["0.0"],
          detail=R["compare_body_state_pd_vs_playerbase"])
    pb_con = constraints(pb)
    R["constraints_keys_equal"] = sorted(pb_con) == sorted(pd_con)
    R["constraints_maxdiff_vs_playerbase"] = max((abs(pd_con[k][0] - pb_con[k][0]) for k in pd_con if k in pb_con), default=None)
    R["constraints_active_equal"] = all(pd_con[k][1] == pb_con[k][1] for k in pd_con if k in pb_con)
    check("constraints_equal_playerbase", R["constraints_keys_equal"] and R["constraints_active_equal"]
          and R["constraints_maxdiff_vs_playerbase"] is not None and R["constraints_maxdiff_vs_playerbase"] < 1e-4,
          n=len(pd_con), maxdiff=R["constraints_maxdiff_vs_playerbase"])
    pa = spawn(pb)
    yield from warmup(200, 10.0)
    pb_bones = bones(pa)
    bd = [max(abs(a - b) for a, b in zip(R["pd_bones"][k], pb_bones[k])) for k in R["pd_bones"] if k in pb_bones]
    R["bones_n_pd"], R["bones_n_pb"], R["bones_compared"] = len(R["pd_bones"]), len(pb_bones), len(bd)
    R["bones_maxdiff_vs_playerbase"] = max(bd) if bd else None
    check("bones_equal_playerbase", bd and len(bd) == len(R["pd_bones"]) == len(pb_bones) and max(bd) < 1e-3,
          n=len(bd), maxdiff=R["bones_maxdiff_vs_playerbase"])
    R["body_mesh_pd_vs_playerbase"] = mesh_diff(pd_body, dump_verts(find_comp(pa, "Body")))
    check("body_mesh_equals_playerbase", R["body_mesh_pd_vs_playerbase"].get("max_dist_cm") == 0.0
          and R["body_mesh_pd_vs_playerbase"]["tris_identical"], detail=R["body_mesh_pd_vs_playerbase"])
    scene.eas.destroy_actor(pa)
    yield from warmup(30, 1.0)

    # ===== D) negative control: MH_MaleBase dup (a different body/face must compare False) =====
    mb = scratch_dup(MALE_PATH, "IC_MaleBase")
    open_edit(mb)
    R["negative_control_body_vs_malebase"] = {str(t): bool(mhs().compare_body_state(pd, mb, t)) for t in (0.1, 1.0)}
    R["negative_control_face_vs_malebase"] = {str(t): bool(mhs().compare_face_state(pd, mb, t)) for t in (0.1, 1.0)}
    check("negative_control_detects_difference", not R["negative_control_body_vs_malebase"]["0.1"]
          and not R["negative_control_face_vs_malebase"]["0.1"],
          body=R["negative_control_body_vs_malebase"], face=R["negative_control_face_vs_malebase"])
    close_edit(mb)
    close_edit(pb)
    yield

    # ===== E) Epic preset Kelvin (grooms hidden) under the same rig =====
    try:
        kp = ue.load_asset(KELVIN_PRESET)
        if not isinstance(kp, ue.MetaHumanCharacter):
            raise RuntimeError(f"{KELVIN_PRESET} is {type(kp).__name__}")
        kd = scratch_dup(KELVIN_PRESET, "IC_Kelvin")
        open_edit(kd)
        ka = spawn(kd)
        yield from warmup(200, 10.0)
        kh = head_bone(ka)
        off = (FACE_CENTER[0] - pd_head[0], FACE_CENTER[1] - pd_head[1], FACE_CENTER[2] - pd_head[2])
        kcenter = (kh[0] + off[0], kh[1] + off[1], kh[2] + off[2])
        R["kelvin"] = {"head_bone": kh, "center": kcenter, "components": comp_inventory(ka)}
        scene.extra_hidden_components = list(ka.get_components_by_class(ue.GroomComponent))
        yield from shoot_plan(scene, "ic_kelvin_", views(kcenter), [("studio", ["Face_Front", "Face_ThreeQuarter", "JawClose", "EarR"]),
                                                                  ("headlight", ["Face_ThreeQuarter", "JawClose"]),
                                                                  ("rimspec0", ["EarR"]),
                                                                  ("ambient", ["Face_ThreeQuarter", "JawClose"])])
        scene.extra_hidden_components = []
        scene.eas.destroy_actor(ka)
        close_edit(kd)
    except Exception as exc:  # noqa: BLE001
        REPORT["warnings"].append("kelvin reference failed: " + traceback.format_exc()[-600:])
        step("WARNING kelvin reference failed", err=repr(exc)[:300])
    close_edit(pd)
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
        fh.write(f"\n===== pd_ic_verify.py {now()} =====\n")
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
