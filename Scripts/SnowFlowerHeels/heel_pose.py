"""Snow Flower heels: measure the fitting body's feet, solve the heel pose, write foot_posed.blend + heel_pose.json.

    blender -b References/Characters/MH_PlayerFemale/MH_PlayerFemale_FitBody.blend --factory-startup \
        --python Scripts/SnowFlowerHeels/heel_pose.py -- [--base MH_PlayerFemale] [--heel-mm 90] [--out-blend ...]
        [--out-json ...] [--render-dir ...]

The fitting body file is opened read-only (its SHA-256 is checked against base_lock.json before and after; the result
is saved as a COPY under WorkFiles/SnowFlowerHeels/).

The pose is the same algorithm the in-game correction runs every frame (HEEL_POSE.md section 4), applied to the rest
pose (the barefoot "animation"):

1. per foot, rotate ``foot_*`` about the ball contact point P (the lowest skin under the ball) by the heel pitch
   theta around the foot's lateral axis ``a = up x f`` (f = horizontal heel->ball direction), then lift it by the
   forefoot sole ``dz`` (outsole + insole under the ball);
2. ``ball_*`` keeps its world orientation (toes flat on the insole) plus the toe spring ``tau`` (toes up);
3. the pelvis rises by ``min`` over both legs of the reach-preserving lift (the lift that keeps hip->ankle distance
   equal to the animation's), so no leg ever has to stretch further than the animation had it;
4. a two-bone IK (thigh, calf) per leg puts the ankle on its new position, keeping the knee's bend plane.

theta and dz are solved on the SKINNED MESH (not on bones) so the lowest heel skin sits on the heel seat and the lowest
ball skin on the forefoot insole to 0.1 mm.

Helpers the shoe builder can import (``sys.path`` must contain Scripts/):

    from SnowFlowerHeels.heel_pose import apply_heel_pose, clear_heel_pose, unpose_points, load_pose
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
SCRIPTS = ROOT / "Scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from pipeline import garment_qa as gq  # noqa: E402

UP = Vector((0.0, 0.0, 1.0))
SIDES = {"l": 1.0, "r": -1.0}          # +X is the character's left (facing -Y)
TOES = ("bigtoe", "indextoe", "middletoe", "ringtoe", "littletoe")
MIRROR = np.diag([1.0, -1.0, 1.0])     # Blender world <-> Unreal component space (and metres <-> cm)

# ---- design values (HEEL_POSE.md section 3 derives them from the reference)
HEEL_HEIGHT_MM = 90.0          # standard heel height: ground to the heel seat at the back
HEEL_INSOLE_MM = 2.0           # insole + sock lining over the heel seat board
HEEL_SEAT_DROP_MM = 2.0        # the seat under the heel's weight-bearing point sits this much below its rear edge
FOREFOOT_OUTSOLE_MM = 4.0      # leather outsole under the ball (thin pump sole)
FOREFOOT_INSOLE_MM = 2.0       # insole under the ball
TOE_SPRING_MM = 8.0            # outsole toe tip above the ground
TOE_SPRING_TOES_DEG = 3.0      # the toes follow the insole's rise over their first ~5 cm


# --------------------------------------------------------------------------- small math

def v3(a) -> np.ndarray:
    return np.array([a[0], a[1], a[2]], dtype=float)


def horizontal(v: Vector) -> Vector:
    h = Vector((v.x, v.y, 0.0))
    return h.normalized() if h.length > 1e-9 else Vector((0.0, -1.0, 0.0))


def rot_about(pivot: Vector, axis: Vector, angle: float) -> Matrix:
    return Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-pivot)


def frame(u: Vector, n: Vector) -> Matrix:
    """Orthonormal 3x3 basis (u, n', u x n') with n' = n made perpendicular to u."""
    u = u.normalized()
    n = (n - u * n.dot(u))
    n = n.normalized() if n.length > 1e-9 else u.orthogonal().normalized()
    w = u.cross(n)
    return Matrix((u, n, w)).transposed()


def ue_rotator(r: np.ndarray) -> dict:
    """Unreal FRotator (degrees) of a column-vector rotation matrix given in Unreal component axes (FMatrix::Rotator)."""
    x, y, z = r[:, 0], r[:, 1], r[:, 2]
    pitch = math.atan2(x[2], math.hypot(x[0], x[1]))
    yaw = math.atan2(x[1], x[0])
    sy_axis = np.array([-math.sin(yaw), math.cos(yaw), 0.0])
    roll = math.atan2(float(np.dot(z, sy_axis)), float(np.dot(y, sy_axis)))
    return {"roll": round(math.degrees(roll), 4), "pitch": round(math.degrees(pitch), 4), "yaw": round(math.degrees(yaw), 4)}


def quat_xyzw(r: np.ndarray) -> list:
    q = Matrix(r.tolist()).to_quaternion()
    if q.w < 0:
        q.negate()
    return [round(q.x, 6), round(q.y, 6), round(q.z, 6), round(q.w, 6)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# --------------------------------------------------------------------------- scene access

def fitbody(base: str):
    arm = bpy.data.objects[gq.ROOT_BONE]
    body = bpy.data.objects[f"FIT_{base}_Body"]
    return arm, body


def rest_head(arm, name: str) -> Vector:
    return arm.matrix_world @ arm.data.bones[name].head_local


def body_coords(body) -> np.ndarray:
    bpy.context.view_layer.update()
    return gq.evaluated_world(body)[0]


def foot_group_mass(body, side: str) -> np.ndarray:
    """Per body vertex: summed weight on the foot's own bones (foot, ball, toes, ankle correctives)."""
    names = {f"foot_{side}", f"ball_{side}", f"ankle_bck_{side}", f"ankle_fwd_{side}"}
    names |= {f"{t}_0{i}_{side}" for t in TOES for i in (1, 2)}
    index = {g.index for g in body.vertex_groups if g.name in names}
    mass = np.zeros(len(body.data.vertices))
    for vertex in body.data.vertices:
        mass[vertex.index] = sum(e.weight for e in vertex.groups if e.group in index)
    return mass


# --------------------------------------------------------------------------- measuring (rest)

def measure_foot(arm, body, coords: np.ndarray, side: str) -> dict:
    sign = SIDES[side]
    ankle = rest_head(arm, f"foot_{side}")
    ball = rest_head(arm, f"ball_{side}")
    mass = foot_group_mass(body, side)
    below = (coords[:, 0] * sign > 0.0) & (coords[:, 2] < ankle.z + 0.02)
    foot = below & (mass > 0.5)
    f = horizontal(ball - ankle)
    lateral = UP.cross(f).normalized()          # the pitch axis: rotating +theta about it lifts the heel
    along = coords @ v3(f)
    across = coords @ v3(lateral)
    z0 = float(coords[below, 2].min())
    lo, hi = float(along[foot].min()), float(along[foot].max())
    length = hi - lo
    ball_along = float(v3(ball) @ v3(f))
    low = below & (coords[:, 2] < 0.045)
    width = float(across[low].max() - across[low].min())
    width_pts = (coords[low][np.argmin(across[low])], coords[low][np.argmax(across[low])])
    sole = foot & (coords[:, 2] < z0 + 0.004)
    heel_zone = sole & (along < lo + 0.25 * length)
    ball_zone = sole & (np.abs(along - ball_along) < 0.02)
    if not ball_zone.any():
        near = foot & (np.abs(along - ball_along) < 0.02)
        ball_zone = near & (coords[:, 2] <= coords[near, 2].min() + 0.002)
    heel_c = coords[heel_zone].mean(axis=0)
    ball_c = coords[ball_zone].mean(axis=0)
    # the exact skin points used as contact references: the lowest vertex of each zone
    # the heel PAD (not the arch in front of it): within 35 mm of the rest heel contact and 15 mm of the floor; when
    # the foot pitches, its lowest point rolls to the back of the pad, which is what sits on the heel seat
    heel_region = foot & (np.linalg.norm((coords - heel_c)[:, :2], axis=1) < 0.035) & (coords[:, 2] < z0 + 0.015)
    ball_region = foot & (np.abs(along - ball_along) < 0.025) & (coords[:, 2] < z0 + 0.012)
    toe_region = foot & (along > ball_along + 0.02) & (coords[:, 2] < z0 + 0.025)
    toe_tip = coords[foot][np.argmax(along[foot])]
    heel_back = coords[foot][np.argmin(along[foot])]
    return {
        "side": side,
        "forward_axis": list(f), "lateral_axis": list(lateral),
        "toe_out_deg": round(math.degrees(math.atan2(f.x * sign, -f.y)), 3),
        "floor_z_mm": round(z0 * 1000, 3),
        "length_mm": round(length * 1000, 2),
        "width_mm": round(width * 1000, 2),
        "width_points_m": [list(np.round(p, 5)) for p in width_pts],
        "heel_back_m": list(np.round(heel_back, 5)), "toe_tip_m": list(np.round(toe_tip, 5)),
        "ankle_height_mm": round((ankle.z - z0) * 1000, 2),
        "ankle_head_m": list(np.round(v3(ankle), 5)),
        "ball_joint_height_mm": round((ball.z - z0) * 1000, 2),
        "ball_head_m": list(np.round(v3(ball), 5)),
        "ball_from_heel_back_mm": round((ball_along - lo) * 1000, 2),
        "ankle_from_heel_back_mm": round((float(v3(ankle) @ v3(f)) - lo) * 1000, 2),
        "heel_contact_m": list(np.round(heel_c, 5)), "ball_contact_m": list(np.round(ball_c, 5)),
        "heel_contact_to_ball_contact_mm": round(float(np.linalg.norm((heel_c - ball_c)[:2])) * 1000, 2),
        "sole_vertices": int(sole.sum()),
        "_regions": {"heel": np.where(heel_region)[0], "ball": np.where(ball_region)[0],
                     "heel_zone": np.where(heel_zone)[0], "ball_zone": np.where(ball_zone)[0],
                     "toe": np.where(toe_region)[0], "foot": np.where(foot)[0]},
        "_pivot": Vector(ball_c), "_heel": Vector(heel_c), "_f": f, "_a": lateral,
    }


def bone_record(arm, name: str) -> dict:
    bone = arm.data.bones[name]
    m = arm.matrix_world @ bone.matrix_local
    return {"head_m": list(np.round(v3(m.translation), 6)), "tail_m": list(np.round(v3(arm.matrix_world @ bone.tail_local), 6)),
            "matrix_local_rows": [list(np.round(row, 6)) for row in np.array(m)]}


def ue_component_rest(reference: dict) -> dict:
    """Unreal component-space rest transforms (3x3 rotation, cm translation) of every bone from ue_reference.json."""
    bones = {b["name"]: b for b in reference["body_ref_skeleton"]}
    cache = {}

    def comp(name):
        if name in cache:
            return cache[name]
        b = bones[name]
        x, y, z, w = b["rotation_xyzw"]
        local = Matrix.Translation(Vector(b["location_cm"])) @ Quaternion((w, x, y, z)).to_matrix().to_4x4()
        cache[name] = local if b["parent"] is None else comp(b["parent"]) @ local
        return cache[name]

    return {name: comp(name) for name in bones}, bones


# --------------------------------------------------------------------------- the pose

def clear_heel_pose(arm) -> None:
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def _set(arm, name: str, matrix: Matrix) -> None:
    arm.pose.bones[name].matrix = matrix
    bpy.context.view_layer.update()


def apply_heel_pose(arm, feet: dict, params: dict) -> dict:
    """Pose ``arm`` (from rest) into the heel pose. ``feet[side]`` needs the rest pivot/heel/axis entries from
    ``measure_foot`` (or ``load_pose``); ``params[side]`` = {"theta_deg", "dz_mm"}, plus params["toe_deg"] and
    optionally params["lift_mm"] (else the reach-preserving min). Returns what it did."""
    clear_heel_pose(arm)
    bones = arm.data.bones
    out = {"legs": {}}
    targets = {}
    for side, foot in feet.items():
        theta = math.radians(params[side]["theta_deg"])
        dz = params[side]["dz_mm"] / 1000.0
        a = Vector(foot["_a"])
        about = Matrix.Translation(UP * dz) @ rot_about(Vector(foot["_pivot"]), a, theta)
        f0 = bones[f"foot_{side}"].matrix_local.copy()
        b0 = bones[f"ball_{side}"].matrix_local.copy()
        f1 = about @ f0
        toe = Matrix.Rotation(-math.radians(params["toe_deg"]), 4, a)
        b1 = Matrix.Translation((about @ b0).translation) @ toe @ b0.to_3x3().to_4x4()
        hip0 = bones[f"thigh_{side}"].head_local.copy()
        ankle0 = f0.translation.copy()
        ankle1 = f1.translation.copy()
        reach = (hip0 - ankle0).length
        horiz = Vector((hip0.x - ankle1.x, hip0.y - ankle1.y)).length
        lift_i = ankle1.z - hip0.z + math.sqrt(max(reach * reach - horiz * horiz, 0.0))
        targets[side] = (f1, b1, ankle0, ankle1, hip0, lift_i)
        out["legs"][side] = {"ankle_rise_mm": round((ankle1.z - ankle0.z) * 1000, 3),
                             "ankle_forward_mm": round((ankle1 - ankle0).dot(Vector(foot["_f"])) * 1000, 3),
                             "reach_preserving_lift_mm": round(lift_i * 1000, 3)}
    lift = params.get("lift_mm")
    lift = max(0.0, min(t[5] for t in targets.values())) if lift is None else lift / 1000.0
    out["pelvis_lift_mm"] = round(lift * 1000, 3)
    pelvis0 = bones["pelvis"].matrix_local.copy()
    _set(arm, "pelvis", Matrix.Translation(UP * lift) @ pelvis0)
    for side, (f1, b1, ankle0, ankle1, hip0, _lift_i) in targets.items():
        thigh0 = bones[f"thigh_{side}"].matrix_local.copy()
        calf0 = bones[f"calf_{side}"].matrix_local.copy()
        knee0 = calf0.translation.copy()
        hip1 = hip0 + UP * lift
        l1, l2 = (knee0 - hip0).length, (ankle0 - knee0).length
        pole0 = (knee0 - hip0) - (ankle0 - hip0).normalized() * (knee0 - hip0).dot((ankle0 - hip0).normalized())
        if pole0.length < 1e-6:
            pole0 = Vector((0.0, -1.0, 0.0))
        d = ankle1 - hip1
        dist = min(d.length, l1 + l2 - 1e-7)
        x = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
        h = math.sqrt(max(l1 * l1 - x * x, 0.0))
        n1 = pole0 - d.normalized() * pole0.dot(d.normalized())
        n1 = n1.normalized() if n1.length > 1e-9 else pole0.normalized()
        knee1 = hip1 + d.normalized() * x + n1 * h
        rt = frame(knee1 - hip1, n1) @ frame(knee0 - hip0, pole0).transposed()
        _set(arm, f"thigh_{side}", Matrix.Translation(hip1) @ rt.to_4x4() @ Matrix.Translation(-hip0) @ thigh0)
        ankle_fk = knee1 + (rt @ (ankle0 - knee0))
        rc = frame(ankle1 - knee1, n1) @ frame(ankle_fk - knee1, n1).transposed()
        _set(arm, f"calf_{side}", Matrix.Translation(knee1) @ rc.to_4x4() @ Matrix.Translation(-knee1)
             @ Matrix.Translation(hip1) @ rt.to_4x4() @ Matrix.Translation(-hip0) @ calf0)
        _set(arm, f"foot_{side}", f1)
        _set(arm, f"ball_{side}", b1)
        reached = (arm.pose.bones[f"foot_{side}"].matrix.translation - ankle1).length
        out["legs"][side].update({"knee_move_mm": round((knee1 - knee0).length * 1000, 3),
                                  "ik_reach_error_mm": round(reached * 1000, 5),
                                  "knee_bend_rest_deg": round(math.degrees((knee0 - hip0).angle(ankle0 - knee0)), 3),
                                  "knee_bend_posed_deg": round(math.degrees((knee1 - hip1).angle(ankle1 - knee1)), 3)})
    return out


def unpose_points(points: np.ndarray, weights: list, arm) -> np.ndarray:
    """Map world points modelled on the POSED foot back to the rest (bind) pose. ``weights[i]`` = {bone: w}
    (normalised). v_rest = (sum_b w_b * P_b @ R_b^-1)^-1 v_posed with P_b the posed and R_b the rest bone matrix."""
    skin = {}
    for pb in arm.pose.bones:
        skin[pb.name] = np.array(arm.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted() @ arm.matrix_world.inverted())
    out = np.empty_like(points)
    for i, (p, w) in enumerate(zip(points, weights)):
        m = sum(weight * skin[name] for name, weight in w.items())
        out[i] = (np.linalg.inv(m) @ np.append(p, 1.0))[:3]
    return out


def load_pose(path: Path = ROOT / "WorkFiles/SnowFlowerHeels/heel_pose.json") -> tuple:
    """(feet, params) from heel_pose.json in the form ``apply_heel_pose`` takes."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    feet = {s: {"_pivot": d["pivot_ball_contact_m"], "_a": d["lateral_axis"], "_f": d["forward_axis"]}
            for s, d in data["solve"]["per_foot"].items()}
    params = {s: {"theta_deg": d["theta_deg"], "dz_mm": d["dz_mm"]} for s, d in data["solve"]["per_foot"].items()}
    params["toe_deg"] = data["design"]["toe_spring_toes_deg"]
    params["lift_mm"] = data["solve"]["pelvis_lift_mm"]
    return feet, params


# --------------------------------------------------------------------------- solving on the mesh

def contact_heights(body, feet: dict) -> dict:
    coords = body_coords(body)
    out = {}
    for side, foot in feet.items():
        r = foot["_regions"]
        heel = coords[r["heel"]]
        ball = coords[r["ball"]]
        toe = coords[r["toe"]]
        # the tracked weight-bearing points: the centroids of the rest contact patches (the same skin, posed)
        heel_c = coords[r["heel_zone"]].mean(axis=0)
        ball_c = coords[r["ball_zone"]].mean(axis=0)
        # forefoot: its LOWEST skin (ball + toes) rests on the flat forefoot insole; heel: the pad centroid on the seat
        out[side] = {"heel_z": float(heel_c[2]), "ball_z": float(min(ball[:, 2].min(), toe[:, 2].min())),
                     "ball_contact_z": float(ball_c[2]),
                     "heel_pad_min_z": float(heel[:, 2].min()), "ball_min_z": float(ball[:, 2].min()),
                     "toe_z": float(toe[:, 2].min()), "foot_min_z": float(coords[r["foot"], 2].min()),
                     "heel_pt": heel_c, "ball_pt": ball_c,
                     "heel_pad_low_pt": heel[np.argmin(heel[:, 2])], "toe_pt": toe[np.argmin(toe[:, 2])]}
    return out


def solve(arm, body, feet: dict, heel_target: float, ball_target: float, toe_deg: float) -> tuple:
    """Newton on (theta, dz) per foot so min heel skin z = heel_target and min ball skin z = ball_target."""
    params = {"toe_deg": toe_deg}
    for side, foot in feet.items():
        d = foot["_heel"] - foot["_pivot"]
        run = Vector((d.x, d.y)).length
        params[side] = {"theta_deg": math.degrees(math.asin(min(0.95, (heel_target - ball_target) / max(run, 1e-3)))),
                        "dz_mm": ball_target * 1000.0}
    history = []
    for iteration in range(12):
        apply_heel_pose(arm, feet, params)
        h = contact_heights(body, feet)
        err = {s: (h[s]["heel_z"] - heel_target, h[s]["ball_z"] - ball_target) for s in feet}
        history.append({"iteration": iteration, **{s: {"theta_deg": round(params[s]["theta_deg"], 4),
                                                       "dz_mm": round(params[s]["dz_mm"], 4),
                                                       "heel_err_mm": round(err[s][0] * 1000, 4),
                                                       "ball_err_mm": round(err[s][1] * 1000, 4)} for s in feet}})
        if all(abs(e[0]) < 5e-5 and abs(e[1]) < 5e-5 for e in err.values()):
            break
        new = {}
        for side in feet:
            jac = np.zeros((2, 2))
            base = np.array(err[side])
            for k, (key, step) in enumerate((("theta_deg", 0.2), ("dz_mm", 0.5))):
                trial = {s: dict(params[s]) for s in feet}
                trial["toe_deg"] = toe_deg
                trial[side][key] += step
                apply_heel_pose(arm, feet, trial)
                hh = contact_heights(body, feet)[side]
                jac[:, k] = (np.array([hh["heel_z"] - heel_target, hh["ball_z"] - ball_target]) - base) / step
            delta = np.linalg.solve(jac, -base)
            new[side] = {"theta_deg": params[side]["theta_deg"] + float(delta[0]),
                         "dz_mm": params[side]["dz_mm"] + float(delta[1])}
        params.update(new)
    apply_heel_pose(arm, feet, params)
    return params, history


# --------------------------------------------------------------------------- output helpers

def ue_pose_numbers(arm, reference: dict, names: list) -> dict:
    """Posed bones in Unreal terms: component-space delta rotation (axis/angle), and the posed LOCAL transform
    (relative to the parent, cm / quat xyzw / FRotator) next to the rest local transform."""
    comp_rest, bones = ue_component_rest(reference)
    posed_cs = {}

    def cs_posed(name):
        if name in posed_cs:
            return posed_cs[name]
        pb = arm.pose.bones.get(name)
        rest = comp_rest[name]
        if pb is None:  # root: not an armature bone
            posed_cs[name] = rest
            return rest
        w_rest = arm.matrix_world @ pb.bone.matrix_local
        w_pose = arm.matrix_world @ pb.matrix
        d_b = np.array(w_pose.to_3x3()) @ np.array(w_rest.to_3x3()).T
        d_ue = MIRROR @ d_b @ MIRROR
        rot = d_ue @ np.array(rest.to_3x3())
        t = MIRROR @ v3(w_pose.translation) * 100.0
        m = Matrix.Identity(4)
        m = Matrix(rot.tolist()).to_4x4()
        m.translation = Vector(t)
        posed_cs[name] = m
        return m

    out = {}
    for name in names:
        parent = bones[name]["parent"]
        cs = cs_posed(name)
        rest = comp_rest[name]
        d = np.array(cs.to_3x3()) @ np.array(rest.to_3x3()).T
        angle = math.degrees(math.acos(max(-1.0, min(1.0, (np.trace(d) - 1.0) / 2.0))))
        axis = Matrix(d.tolist()).to_quaternion().axis
        local_pose = (cs_posed(parent).inverted() @ cs) if parent else cs
        local_rest = (comp_rest[parent].inverted() @ rest) if parent else rest
        dl = local_rest.to_3x3().inverted() @ local_pose.to_3x3()
        out[name] = {
            "component_delta_angle_deg": round(angle, 4),
            "component_delta_axis_ue": [round(v, 5) for v in axis],
            "component_translation_delta_cm": [round(v, 4) for v in (cs.translation - rest.translation)],
            "local_rest": {"location_cm": [round(v, 4) for v in local_rest.translation],
                           "rotation_xyzw": quat_xyzw(np.array(local_rest.to_3x3())),
                           "rotator": ue_rotator(np.array(local_rest.to_3x3()))},
            "local_posed": {"location_cm": [round(v, 4) for v in local_pose.translation],
                            "rotation_xyzw": quat_xyzw(np.array(local_pose.to_3x3())),
                            "rotator": ue_rotator(np.array(local_pose.to_3x3()))},
            "local_delta_rotation_xyzw": quat_xyzw(np.array(dl)),
            "local_delta_angle_deg": round(math.degrees(dl.to_quaternion().angle), 4),
        }
    return out, cs_posed, comp_rest


def to_ue_point(p) -> list:
    return [round(float(v), 4) for v in (MIRROR @ v3(p) * 100.0)]


def cut_posed_feet(arm, body, collection, ankle_z: float) -> dict:
    """Applied (posed) copies of the body below mid-shin, one per side, for modelling the shoe around."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(body.evaluated_get(depsgraph), depsgraph=depsgraph)
    import bmesh
    out = {}
    for side, sign in SIDES.items():
        m = mesh.copy()
        bm = bmesh.new()
        bm.from_mesh(m)
        doomed = [f for f in bm.faces if not all((v.co.z < ankle_z + 0.16) and (v.co.x * sign > 0.0) for v in f.verts)]
        bmesh.ops.delete(bm, geom=doomed, context="FACES")
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.to_mesh(m)
        bm.free()
        name = f"HEEL_FootPosed_{side.upper()}"
        m.name = name
        obj = bpy.data.objects.new(name, m)
        obj.matrix_world = arm.matrix_world @ Matrix.Identity(4)
        collection.objects.link(obj)
        obj.hide_select = True
        obj["heel_pose_reference"] = True
        out[side] = {"object": name, "vertices": len(m.vertices), "triangles": sum(len(p.vertices) - 2 for p in m.polygons)}
    bpy.data.meshes.remove(mesh)
    return out


def empty(collection, name: str, location, size: float = 0.01, kind: str = "SPHERE"):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = kind
    obj.empty_display_size = size
    obj.location = Vector(location)
    collection.objects.link(obj)
    obj.hide_select = True
    return obj


def render_views(out_dir: Path, feet_objs: list, tag: str) -> list:
    """Workbench side / front / 3-4 views of the posed feet on a floor grid (orthographic, mm-readable)."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 900
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("HEEL_W") if not scene.world else scene.world
    scene.world = world
    visible = set(feet_objs)
    hidden = []
    for obj in scene.objects:
        if obj.type in {"MESH", "ARMATURE"} and obj not in visible and not obj.name.startswith("HEEL_Floor"):
            if not obj.hide_render:
                obj.hide_render = True
                hidden.append(obj)
    cam_data = bpy.data.cameras.new("HEEL_Cam")
    cam_data.type = "ORTHO"
    cam = bpy.data.objects.new("HEEL_Cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    paths = []
    views = {"side_L": ((1.0, 0.0, 0.0), 0.36, (0.09, -0.07, 0.10)),
             "front": ((0.0, -1.0, 0.0), 0.46, (0.0, -0.10, 0.10)),
             "threequarter_L": ((0.8, -0.8, 0.35), 0.46, (0.05, -0.08, 0.08))}
    for label, (direction, scale, target) in views.items():
        d = Vector(direction).normalized()
        cam.location = Vector(target) + d * 2.0
        cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
        cam_data.ortho_scale = scale
        path = out_dir / f"heelpose_{tag}_{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path))
    for obj in hidden:
        obj.hide_render = False
    bpy.data.objects.remove(cam, do_unlink=True)
    return paths


# --------------------------------------------------------------------------- main

def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="heel_pose.py")
    ap.add_argument("--base", default="MH_PlayerFemale")
    ap.add_argument("--heel-mm", type=float, default=HEEL_HEIGHT_MM)
    ap.add_argument("--out-blend", default=str(ROOT / "WorkFiles/SnowFlowerHeels/foot_posed.blend"))
    ap.add_argument("--out-json", default=str(ROOT / "WorkFiles/SnowFlowerHeels/heel_pose.json"))
    ap.add_argument("--render-dir", default=str(ROOT / "WorkFiles/SnowFlowerHeels/heel_pose_renders"))
    ap.add_argument("--no-render", action="store_true")
    args = ap.parse_args(argv)

    base = args.base
    lock = gq.load_base_lock(base)
    blend = ROOT / lock["blend"]
    if Path(bpy.data.filepath).resolve() != blend.resolve():
        raise RuntimeError(f"open {blend} with -b first (got {bpy.data.filepath})")
    sha_before = sha256(blend)
    if sha_before != lock["blend_sha256"]:
        raise RuntimeError("the fitting body .blend does not match base_lock.json")
    reference = json.loads((gq.base_dir(base) / "source/ue_reference.json").read_text(encoding="utf-8"))

    arm, body = fitbody(base)
    clear_heel_pose(arm)
    rest = body_coords(body)
    feet = {side: measure_foot(arm, body, rest, side) for side in SIDES}

    heel_target = (args.heel_mm - HEEL_SEAT_DROP_MM + HEEL_INSOLE_MM) / 1000.0
    ball_target = (FOREFOOT_OUTSOLE_MM + FOREFOOT_INSOLE_MM) / 1000.0
    params, history = solve(arm, body, feet, heel_target, ball_target, TOE_SPRING_TOES_DEG)
    pose_info = apply_heel_pose(arm, feet, params)
    posed = contact_heights(body, feet)
    posed_coords = body_coords(body)

    per_foot = {}
    for side, foot in feet.items():
        p = posed[side]
        hp, bp_ = Vector(p["heel_pt"]), Vector(p["ball_pt"])
        run = Vector((hp.x - bp_.x, hp.y - bp_.y)).length
        incline = math.degrees(math.atan2(hp.z - bp_.z, run))
        region = foot["_regions"]["foot"]
        ankle_now = arm.pose.bones[f"foot_{side}"].matrix.translation
        per_foot[side] = {
            "theta_deg": round(params[side]["theta_deg"], 4), "dz_mm": round(params[side]["dz_mm"], 4),
            "pivot_ball_contact_m": [round(v, 6) for v in foot["_pivot"]],
            "pivot_ball_contact_ue_cm": to_ue_point(foot["_pivot"]),
            "heel_contact_rest_ue_cm": to_ue_point(foot["_heel"]),
            "lateral_axis": [round(v, 6) for v in foot["_a"]], "forward_axis": [round(v, 6) for v in foot["_f"]],
            "lateral_axis_ue": [round(float(v), 6) for v in MIRROR @ v3(foot["_a"])],
            "posed_heel_contact_z_mm": round(p["heel_z"] * 1000, 3),
            "posed_forefoot_min_z_mm": round(p["ball_z"] * 1000, 3),
            "posed_ball_contact_z_mm": round(p["ball_contact_z"] * 1000, 3),
            "posed_heel_pad_min_z_mm": round(p["heel_pad_min_z"] * 1000, 3),
            "posed_heel_pad_lowest_point_m": [round(float(v), 5) for v in p["heel_pad_low_pt"]],
            "posed_ball_skin_min_z_mm": round(p["ball_min_z"] * 1000, 3),
            "posed_toe_skin_min_z_mm": round(p["toe_z"] * 1000, 3),
            "posed_foot_min_z_mm": round(p["foot_min_z"] * 1000, 3),
            "posed_heel_point_m": [round(float(v), 5) for v in p["heel_pt"]],
            "posed_ball_point_m": [round(float(v), 5) for v in p["ball_pt"]],
            "posed_toe_point_m": [round(float(v), 5) for v in p["toe_pt"]],
            "posed_heel_to_ball_run_mm": round(run * 1000, 2),
            "posed_heel_to_ball_incline_deg": round(incline, 3),
            "posed_ankle_head_m": [round(v, 5) for v in ankle_now],
            "posed_ankle_height_mm": round(ankle_now.z * 1000, 2),
            "posed_foot_bbox_m": {"min": list(np.round(posed_coords[region].min(axis=0), 5)),
                                  "max": list(np.round(posed_coords[region].max(axis=0), 5))},
            "heel_skin_above_floor_rest_mm": round(float(rest[foot["_regions"]["heel"], 2].min()) * 1000, 3),
        }
    ue_bones = ["pelvis", "thigh_l", "calf_l", "foot_l", "ball_l", "thigh_r", "calf_r", "foot_r", "ball_r"]
    ue_numbers, cs_posed, comp_rest = ue_pose_numbers(arm, reference, ue_bones)

    def local_point(cs: Matrix, p) -> list:
        return [round(v, 4) for v in cs.inverted() @ Vector(to_ue_point(p))]

    # contact points in bone-local Unreal coordinates (cm), the constants the in-game correction needs
    contacts = {}
    for side, foot in feet.items():
        foot_rest, ball_rest = comp_rest[f"foot_{side}"], comp_rest[f"ball_{side}"]
        foot_pose, ball_pose = cs_posed(f"foot_{side}"), cs_posed(f"ball_{side}")
        hp, bpnt = posed[side]["heel_pt"], posed[side]["ball_pt"]
        contacts[side] = {
            "barefoot_heel_contact_in_foot_cm": local_point(foot_rest, foot["_heel"]),
            "barefoot_ball_contact_in_foot_cm": local_point(foot_rest, foot["_pivot"]),
            "barefoot_ball_contact_in_ball_cm": local_point(ball_rest, foot["_pivot"]),
            "shoe_heel_tip_floor_in_foot_cm": local_point(foot_pose, (hp[0], hp[1], 0.0)),
            "shoe_ball_sole_floor_in_ball_cm": local_point(ball_pose, (bpnt[0], bpnt[1], 0.0)),
            "shoe_ball_sole_floor_in_foot_cm": local_point(foot_pose, (bpnt[0], bpnt[1], 0.0)),
            "heel_contact_in_foot_cm_posed": local_point(foot_pose, hp),
        }

    # ---- the file for the builder: a COPY of the fitting body in the heel pose + applied feet + markers
    collection = bpy.data.collections.new("HEEL_POSE_REF")
    bpy.context.scene.collection.children.link(collection)
    lowest_ankle = min(arm.pose.bones[f"foot_{s}"].matrix.translation.z for s in SIDES)
    cut = cut_posed_feet(arm, body, collection, lowest_ankle)
    for side, foot in feet.items():
        S = side.upper()
        empty(collection, f"HEEL_BallContact_{S}", posed[side]["ball_pt"])
        empty(collection, f"HEEL_HeelContact_{S}", posed[side]["heel_pt"])
        empty(collection, f"HEEL_ToeLowest_{S}", posed[side]["toe_pt"], 0.006)
        pivot_floor = Vector(foot["_pivot"])
        empty(collection, f"HEEL_Pivot_{S}", (pivot_floor.x, pivot_floor.y, 0.0), 0.015, "PLAIN_AXES")
        hp = posed[side]["heel_pt"]
        empty(collection, f"HEEL_HeelTipFloor_{S}", (hp[0], hp[1], 0.0), 0.012, "CIRCLE")
    floor = bpy.data.meshes.new("HEEL_Floor")
    fv = [(x, y, z) for z in (-0.002, 0.0) for (x, y) in ((-0.4, -0.5), (0.4, -0.5), (0.4, 0.3), (-0.4, 0.3))]
    floor.from_pydata(fv, [], [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
    floor_obj = bpy.data.objects.new("HEEL_Floor", floor)
    collection.objects.link(floor_obj)
    floor_obj.hide_select = True
    floor_obj.display_type = "WIRE"
    for obj in collection.objects:
        obj["heel_pose_version"] = 1

    design = {
        "heel_height_mm": args.heel_mm, "heel_insole_mm": HEEL_INSOLE_MM, "heel_seat_drop_mm": HEEL_SEAT_DROP_MM,
        "forefoot_outsole_mm": FOREFOOT_OUTSOLE_MM, "forefoot_insole_mm": FOREFOOT_INSOLE_MM,
        "heel_contact_target_z_mm": round(heel_target * 1000, 3), "ball_contact_target_z_mm": round(ball_target * 1000, 3),
        "toe_spring_mm": TOE_SPRING_MM, "toe_spring_toes_deg": TOE_SPRING_TOES_DEG,
    }
    result = {
        "created": datetime.now().astimezone().isoformat(timespec="seconds"),
        "script": "Scripts/SnowFlowerHeels/heel_pose.py",
        "base": base, "fitbody_blend": lock["blend"], "fitbody_sha256": sha_before,
        "base_lock_skeleton_hash": lock["skeleton_hash"],
        "units": "Blender: metres, Z up, facing -Y, +X = her left. *_ue_cm: Unreal component space (cm, Y mirrored).",
        "feet_rest": {s: {k: v for k, v in f.items() if not k.startswith("_")} for s, f in feet.items()},
        "bones_rest": {n: bone_record(arm, n) for n in ue_bones},
        "design": design,
        "solve": {"per_foot": per_foot, "pelvis_lift_mm": pose_info["pelvis_lift_mm"], "legs": pose_info["legs"],
                  "history": history},
        "ue_bones": ue_numbers,
        "ue_contacts_local_cm": contacts,
        "posed_feet_objects": cut,
    }
    bpy.context.scene["heel_pose_json"] = json.dumps({"design": design, "per_foot": {s: {k: per_foot[s][k] for k in
                                                     ("theta_deg", "dz_mm")} for s in per_foot},
                                                     "pelvis_lift_mm": pose_info["pelvis_lift_mm"]})
    renders = []
    if not args.no_render:
        out_dir = Path(args.render_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        feet_objs = [bpy.data.objects[c["object"]] for c in cut.values()] + [floor_obj]
        floor_obj.hide_render = False
        renders = render_views(out_dir, feet_objs, base)
    result["renders"] = renders
    out_blend = Path(args.out_blend)
    out_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend), copy=True, compress=True)
    sha_after = sha256(blend)
    result["fitbody_unchanged"] = sha_after == sha_before
    result["foot_posed_blend"] = str(out_blend)
    result["foot_posed_blend_sha256"] = sha256(out_blend)
    Path(args.out_json).write_text(json.dumps(result, indent=1, default=lambda o: list(o) if hasattr(o, "__iter__") else str(o)),
                                   encoding="utf-8")
    print("HEELPOSE_OK", json.dumps({s: {k: per_foot[s][k] for k in ("theta_deg", "dz_mm", "posed_heel_contact_z_mm",
                                                                   "posed_forefoot_min_z_mm", "posed_ball_contact_z_mm", "posed_heel_pad_min_z_mm",
                                                                   "posed_ball_skin_min_z_mm", "posed_toe_skin_min_z_mm",
                                                                   "posed_heel_to_ball_incline_deg")} for s in per_foot}),
          "lift_mm", pose_info["pelvis_lift_mm"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("HEELPOSE_FAILED")
        sys.exit(1)
