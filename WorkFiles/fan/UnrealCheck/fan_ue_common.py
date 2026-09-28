"""Shared helpers for SK_Fan's Unreal import and verification (UE 5.8 pythonscript commandlet).

Runs in the shuriken validation project under a NEW content path per run (FAN_DEST), never DemoGame_1.
Everything expected is read from the BUILD's outputs, never typed twice:
    Exports/Fan/SK_Fan.skeletal.json        bones, sockets, physics bodies, LOD files and screen sizes,
                                            animations, the fold-check corners
    Exports/Fan/SK_Fan_Tassel.skeletal.json the tassel's chain and bodies
    WorkFiles/fan/fan_report.json           triangle counts, openness per frame
"""
import hashlib
import json
import math
import os
from pathlib import Path

import unreal

PROJ = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = PROJ / "WorkFiles" / "fan" / "UnrealCheck"
EXPORTS = Path(os.environ.get("FAN_EXPORTS", str(PROJ / "Exports" / "Fan")))
REPORT_PATH = Path(os.environ.get("FAN_REPORT", str(PROJ / "WorkFiles" / "fan" / "fan_report.json")))
DEST = os.environ.get("FAN_DEST", "/Game/FanCheck/Fan")
OUT = Path(os.environ.get("FAN_OUT", str(HERE)))
SIDECAR = json.loads((EXPORTS / "SK_Fan.skeletal.json").read_text(encoding="utf-8"))
TSIDECAR = json.loads((EXPORTS / "SK_Fan_Tassel.skeletal.json").read_text(encoding="utf-8"))
REPORT = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
MESH = f"{DEST}/SK_Fan"
TASSEL = f"{DEST}/SK_Fan_Tassel"
PHYS = f"{DEST}/PHYS_Fan"
TPHYS = f"{DEST}/PHYS_Fan_Tassel"
ANIMS = [Path(a["file"]).stem for a in SIDECAR["animations"]]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe(fn, default=None):
    try:
        return fn()
    except Exception as exc:                                    # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"[:300]} if default is None else default


def vec(v, nd=4):
    return [round(v.x, nd), round(v.y, nd), round(v.z, nd)]


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    r = unreal.Rotator()
    r.pitch, r.yaw, r.roll = float(pitch), float(yaw), float(roll)
    return r


def quat(xyzw):
    return unreal.Quat(float(xyzw[0]), float(xyzw[1]), float(xyzw[2]), float(xyzw[3]))


def tf(loc_cm, q_xyzw=(0.0, 0.0, 0.0, 1.0)):
    t = unreal.Transform()
    t.translation = unreal.Vector(*[float(v) for v in loc_cm])
    t.rotation = quat(q_xyzw)
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def component_space_ref(mesh):
    """{bone: (component-space ref Transform, parent)} from a transient SkeletalMeshComponent."""
    comp = unreal.new_object(unreal.SkeletalMeshComponent)
    if hasattr(comp, "set_skinned_asset_and_update"):
        comp.set_skinned_asset_and_update(mesh)
    else:
        comp.set_skeletal_mesh_asset(mesh)
    local, parent = {}, {}
    for i in range(comp.get_num_bones()):
        name = str(comp.get_bone_name(i))
        local[name] = comp.get_ref_pose_transform(i)
        p = str(comp.get_parent_bone(name))
        parent[name] = None if p in ("None", "") else p
    world = {}

    def resolve(n):
        if n not in world:
            t = local[n]
            world[n] = t if parent[n] is None else unreal.MathLibrary.compose_transforms(t, resolve(parent[n]))
        return world[n]
    for n in local:
        resolve(n)
    return world, parent, local


def compose_pose(local_by_bone, parent):
    world = {}

    def resolve(n):
        if n not in world:
            t = local_by_bone[n]
            world[n] = t if parent[n] is None else unreal.MathLibrary.compose_transforms(t, resolve(parent[n]))
        return world[n]
    for n in local_by_bone:
        resolve(n)
    return world


def xform_point(t, p):
    v = unreal.MathLibrary.transform_location(t, unreal.Vector(*[float(c) for c in p]))
    return [v.x, v.y, v.z]


def inv_xform_point(t, p):
    v = unreal.MathLibrary.inverse_transform_location(t, unreal.Vector(*[float(c) for c in p]))
    return [v.x, v.y, v.z]


def dist(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def write(name, payload):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")


def asset_exists(path):
    return unreal.EditorAssetLibrary.does_asset_exist(path)


def find_bodies(pa, limit=64):
    """{bone: SkeletalBodySetup} - the asset's body list is not exposed to Python (UE 5.8.3); the bodies are
    subobjects named SkeletalBodySetup_<n>."""
    out = {}
    miss = 0
    for i in range(limit):
        o = unreal.find_object(pa, f"SkeletalBodySetup_{i}")
        if o is None:
            miss += 1
            if miss > 8:
                break
            continue
        out[str(o.get_editor_property("bone_name"))] = o
    return out
