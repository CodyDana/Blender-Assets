"""Garment gates: skeletal clothing built on the locked character base (ASSET_GUIDELINES.md 12.10).

``qa_garment`` returns the same shape as ``qa_check`` (``{"passed", "checks": [{"name", "object", "passed",
"detail"}], ...}``), never prints, and leaves the scene as it found it (the pose it sets is cleared). It runs
``qa_check``'s core items on the garment meshes (transforms, topology, UV0, images, names, skin) with the garment
type's influence limit, then the garment gates:

1. skeleton - exactly one armature, the object named ``root`` (Unreal's root bone becomes the Blender armature
   object; any other name grows an extra root bone), identity transform, in its rest pose, and every bone name,
   parent and rest transform equal to ``base_lock.json`` (0.01 mm / 0.001 deg; the SHA-256 skeleton hash is
   reported). The full bone set must be present: ``export_fbx(kind="garment")`` writes every bone, which is the
   ``ik_*`` policy (metahuman_base_skel has none; the lock records that).
2. fitting body intact - the FITBODY meshes in the file hash to the lock (an edited reference fits nothing).
3. intersection - signed distance of every garment vertex to the fitting body's skin (body + head skin section)
   at rest and in four test poses set on the armature (arms up, deep crouch, long stride, arms forward).
   Rest: no vertex more than 1 mm under the skin. Poses: at most 1 % of the checked vertices more than 5 mm under
   the skin. Which vertices and which body regions count depends on the type (``TYPE_RULES``): a cloak's
   simulated section is checked at rest only (Chaos Cloth moves it in game) and the arms are ignored (they hang
   under the cloak and collide with the cloth); a rigid head piece is also checked against the closed hair proxy.
4. weights - per type: cloak = spine chain only (pelvis .. head), at most 2 influences, the simulated section
   rigid (one influence) on spine_03..05; fitted = only bones the body itself is weighted to, at most 8
   influences (the MetaHuman body's own maximum, measured 2026-09-26); rigid_head / rigid_socket = one bone.
5. budgets - the garment's triangles per type, the cloth section (<= 6,000 triangles, the BlackCloak lesson) and
   the whole character (base LOD0 + this garment + any ``extra_loadout_tris`` <= 120,000, section 2). The
   character budget is the only waivable check: a waiver keeps it failed, records the reason and lets the rest
   decide ``passed``.
6. sections - at most 4 material slots, every slot an ``M_``/``MI_`` material, a cloak has exactly one ``*_Sim``
   slot (the cloth section) and nothing else has one, and a cloak's ``PinMask`` colour is the active one (the FBX
   exporter writes the active colour; Outfit_Pipeline trap 9).

CLI (prints JSON, exit 1 when not passed)::

    blender -b work.blend --factory-startup --python Scripts/pipeline/garment_qa.py -- \
        --objects SK_Name --type cloak|fitted|rigid_head|rigid_socket [--socket-bone thigh_l] \
        [--base MH_PlayerDefault] [--extra-loadout-tris N] [--waive character_triangle_budget="reason"] [--json out]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

_PACKAGE_PARENT = str(Path(__file__).resolve().parents[1])
if _PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, _PACKAGE_PARENT)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

from pipeline.helpers import ObjectLike, resolve_objects  # noqa: E402

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
CHARACTERS = ROOT / "References" / "Characters"
DEFAULT_BASE = "MH_PlayerDefault"
ROOT_BONE = "root"
POSE_SET_VERSION = 1
GARMENT_TYPES = ("cloak", "fitted", "rigid_head", "rigid_socket")
SIM_SUFFIX = "_Sim"
PIN_MASK = "PinMask"

SPINE_CHAIN = ("pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head")
CLOAK_HANG_BONES = ("spine_03", "spine_04", "spine_05")
MAX_SECTIONS = 4
SKELETON_TOLERANCE_M = 1e-5          # 0.01 mm
SKELETON_TOLERANCE_DEG = 1e-3
REST_TOLERANCE_M = 0.001             # deeper than 1 mm under the skin at rest fails
REST_MAX_VERTS = 0
POSE_TOLERANCE_M = 0.005             # deeper than 5 mm in a test pose counts
POSE_MAX_FRACTION = 0.01             # ... and more than 1 % of the checked vertices fails
SIM_TRIANGLE_BUDGET = 6000
CHARACTER_TRIANGLE_BUDGET = 160000   # ASSET_GUIDELINES section 2: MetaHuman player LOD0 160k (Cody, 2026-09-26)
WAIVABLE = ("character_triangle_budget",)
# qa_check's UV0 layout items were written for static meshes with baked, unique textures. Garments usually tile a
# fabric texture (the BlackCloak's wool runs to u 2.55 and overlaps everywhere), and a skeletal mesh has no lightmap,
# so these are reported but do not fail unless the garment declares unique_uvs (baked AO / hand-painted detail).
TILING_UV_CHECKS = ("uv_no_overlap", "uv0_tile_range")

# How each type is skinned, budgeted and intersection-tested. "ignore" = body regions whose nearest surface does
# not count; "pose_verts" = which garment vertices the pose tests look at.
TYPE_RULES: Dict[str, Dict[str, Any]] = {
    "cloak": {"max_influences": 2, "bones": SPINE_CHAIN, "triangles": 30000, "sim": True,
              "rest_ignore": {"arm"}, "pose_ignore": {"arm"}, "pose_verts": "skinned", "hair": False},
    "fitted": {"max_influences": 8, "bones": "body", "triangles": 20000, "sim": False,
               "rest_ignore": set(), "pose_ignore": set(), "pose_verts": "all", "hair": False},
    "rigid_head": {"max_influences": 1, "bones": ("head",), "triangles": 10000, "sim": False,
                   "rest_ignore": {"arm"}, "pose_ignore": {"arm", "head"}, "pose_verts": "all", "hair": True},
    "rigid_socket": {"max_influences": 1, "bones": "socket", "triangles": 5000, "sim": False,
                     "rest_ignore": set(), "pose_ignore": {"arm"}, "pose_verts": "all", "hair": False},
}

# Test poses on metahuman_base_skel, applied in order in armature space (identity object transform, facing -Y,
# +X = the character's left). ("aim", bone, joint, direction) swings the bone about its head until the vector to
# ``joint``'s head points along ``direction``; ("rot", bone, axis, degrees) rotates about an armature axis.
POSES: Dict[str, List[Tuple]] = {
    "arms_up": [
        ("rot", "clavicle_l", (0.0, -1.0, 0.0), 20.0), ("rot", "clavicle_r", (0.0, 1.0, 0.0), 20.0),
        ("aim", "upperarm_l", "lowerarm_l", (0.25, 0.0, 1.0)), ("aim", "upperarm_r", "lowerarm_r", (-0.25, 0.0, 1.0)),
        ("aim", "lowerarm_l", "hand_l", (0.15, -0.15, 1.0)), ("aim", "lowerarm_r", "hand_r", (-0.15, -0.15, 1.0)),
    ],
    "deep_crouch": [
        ("rot", "spine_01", (1.0, 0.0, 0.0), 15.0), ("rot", "spine_03", (1.0, 0.0, 0.0), 10.0),
        ("aim", "thigh_l", "calf_l", (0.30, -0.93, -0.20)), ("aim", "thigh_r", "calf_r", (-0.30, -0.93, -0.20)),
        ("aim", "calf_l", "foot_l", (0.05, 0.65, -0.76)), ("aim", "calf_r", "foot_r", (-0.05, 0.65, -0.76)),
        ("aim", "upperarm_l", "lowerarm_l", (0.35, -0.75, -0.55)), ("aim", "upperarm_r", "lowerarm_r", (-0.35, -0.75, -0.55)),
        ("aim", "lowerarm_l", "hand_l", (0.10, -0.98, 0.10)), ("aim", "lowerarm_r", "hand_r", (-0.10, -0.98, 0.10)),
    ],
    "long_stride": [
        ("aim", "thigh_l", "calf_l", (0.05, -0.60, -0.80)), ("aim", "calf_l", "foot_l", (0.02, -0.05, -1.0)),
        ("aim", "thigh_r", "calf_r", (-0.05, 0.45, -0.89)), ("aim", "calf_r", "foot_r", (-0.02, 0.75, -0.66)),
        ("rot", "spine_03", (0.0, 0.0, 1.0), 8.0),
        ("aim", "upperarm_r", "lowerarm_r", (-0.20, -0.45, -0.87)), ("aim", "upperarm_l", "lowerarm_l", (0.20, 0.40, -0.90)),
    ],
    "arms_forward": [
        ("aim", "upperarm_l", "lowerarm_l", (0.15, -1.0, 0.0)), ("aim", "upperarm_r", "lowerarm_r", (-0.15, -1.0, 0.0)),
        ("aim", "lowerarm_l", "hand_l", (0.05, -1.0, 0.05)), ("aim", "lowerarm_r", "hand_r", (-0.05, -1.0, 0.05)),
    ],
}


# --------------------------------------------------------------------------- base lock

def base_dir(base: str = DEFAULT_BASE) -> Path:
    """``References/Characters/<base>``."""
    return CHARACTERS / base


def fitbody_collection(base: str = DEFAULT_BASE) -> str:
    return f"FITBODY_{base}"


def load_base_lock(base: str = DEFAULT_BASE) -> Dict[str, Any]:
    """Read ``base_lock.json``; raise FileNotFoundError when the base has not been built."""
    path = base_dir(base) / "base_lock.json"
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def bone_region(name: str) -> str:
    """Body region of a bone: arm, leg, neck, head or torso (toes before fingers: ``indextoe`` is a toe)."""
    lower = name.lower()
    if "toe" in lower or lower.startswith(("thigh", "calf", "foot", "ball", "ankle")):
        return "leg"
    if lower.startswith(("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky", "wrist", "elbow")):
        return "arm"
    if lower.startswith("neck"):
        return "neck"
    if lower.startswith(("head", "facial")):
        return "head"
    return "torso"


# --------------------------------------------------------------------------- records and hashes

def triangle_count(obj: "bpy.types.Object") -> int:
    return sum(len(polygon.vertices) - 2 for polygon in obj.data.polygons)


def _local_rest(bone: "bpy.types.Bone") -> Matrix:
    return bone.matrix_local if bone.parent is None else bone.parent.matrix_local.inverted() @ bone.matrix_local


def skeleton_record(arm: "bpy.types.Object") -> Dict[str, Any]:
    """Bone names, parents and local rest transforms (metres, w-positive quaternions) plus their SHA-256."""
    bones = []
    for bone in sorted(arm.data.bones, key=lambda b: b.name):
        local = _local_rest(bone)
        quat = local.to_quaternion()
        if quat.w < 0.0:
            quat.negate()
        bones.append({"name": bone.name, "parent": bone.parent.name if bone.parent else arm.name,
                      "t": [round(v, 6) for v in local.translation], "q": [round(v, 6) for v in quat]})
    canonical = json.dumps([[b["name"], b["parent"], [round(v, 5) for v in b["t"]], [round(v, 4) for v in b["q"]]]
                            for b in bones], separators=(",", ":"))
    return {"root_object": arm.name, "bone_count_including_root": len(bones) + 1, "bones": bones,
            "hash": hashlib.sha256(canonical.encode("ascii")).hexdigest(),
            "hash_rounding": "translation 1e-5 m, quaternion 1e-4, bones sorted by name"}


def mesh_record(obj: "bpy.types.Object") -> Dict[str, Any]:
    """Vertex count and SHA-256 of the rest coordinates (float32) and of the polygon vertex indices."""
    mesh = obj.data
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    indices = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", indices)
    return {"vertices": len(mesh.vertices), "polygons": len(mesh.polygons), "triangles": triangle_count(obj),
            "coords_sha256": hashlib.sha256(coords.tobytes()).hexdigest(),
            "topology_sha256": hashlib.sha256(indices.tobytes()).hexdigest()}


def compare_skeleton(arm: "bpy.types.Object", locked: Dict[str, Any], tolerance_m: float = SKELETON_TOLERANCE_M,
                     tolerance_deg: float = SKELETON_TOLERANCE_DEG) -> Tuple[bool, str, Dict[str, Any]]:
    """Compare ``arm`` with a ``skeleton_record``; return (ok, detail, numbers).

    The gate uses the tight default: an appended copy of the locked armature is bit-identical. A skeleton re-imported
    from a garment FBX is float-close instead (measured 0.003 mm / 0.003 deg), so round-trip tests pass 0.01 deg.
    """
    record = skeleton_record(arm)
    mine = {b["name"]: b for b in record["bones"]}
    theirs = {b["name"]: b for b in locked["bones"]}
    missing = sorted(set(theirs) - set(mine))
    extra = sorted(set(mine) - set(theirs))
    reparented = sorted(n for n in set(mine) & set(theirs) if mine[n]["parent"] != theirs[n]["parent"])
    worst_t, worst_r, worst_bone = 0.0, 0.0, None
    for name in set(mine) & set(theirs):
        dt = float(np.linalg.norm(np.array(mine[name]["t"]) - np.array(theirs[name]["t"])))
        qa_, qb = np.array(mine[name]["q"]), np.array(theirs[name]["q"])
        dot = abs(float(np.dot(qa_ / np.linalg.norm(qa_), qb / np.linalg.norm(qb))))  # imported quats are ~4e-7 off unit
        dr = math.degrees(2.0 * math.acos(min(1.0, dot)))
        if dt > worst_t or dr > worst_r:
            worst_bone = name if (dt > tolerance_m or dr > tolerance_deg) else worst_bone
        worst_t, worst_r = max(worst_t, dt), max(worst_r, dr)
    ok = (not missing and not extra and not reparented and worst_t <= tolerance_m and worst_r <= tolerance_deg)
    detail = (f"hash {record['hash'][:16]} vs lock {locked['hash'][:16]}; {len(mine)} bones; missing {missing[:5]}, "
              f"extra {extra[:5]}, reparented {reparented[:5]}; max rest delta {worst_t * 1000:.4f} mm / "
              f"{worst_r:.4f} deg" + (f" (e.g. {worst_bone})" if worst_bone else ""))
    return ok, detail, {"hash": record["hash"], "hash_equal": record["hash"] == locked["hash"],
                        "max_delta_mm": worst_t * 1000.0, "max_delta_deg": worst_r}


# --------------------------------------------------------------------------- posing

def clear_pose(arm: "bpy.types.Object") -> None:
    for pose_bone in arm.pose.bones:
        pose_bone.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


def apply_pose(arm: "bpy.types.Object", ops: Sequence[Tuple]) -> None:
    """Set one of ``POSES`` on ``arm`` (armature space; see the POSES comment)."""
    clear_pose(arm)
    for op in ops:
        kind, bone = op[0], op[1]
        pose_bone = arm.pose.bones[bone]
        head = pose_bone.head.copy()
        if kind == "aim":
            current = (arm.pose.bones[op[2]].head - head).normalized()
            rotation = current.rotation_difference(Vector(op[3]).normalized()).to_matrix().to_4x4()
        elif kind == "rot":
            rotation = Matrix.Rotation(math.radians(op[3]), 4, Vector(op[2]).normalized())
        else:
            raise ValueError(f"unknown pose op {kind!r}")
        pose_bone.matrix = Matrix.Translation(head) @ rotation @ Matrix.Translation(-head) @ pose_bone.matrix
        bpy.context.view_layer.update()


def in_rest_pose(arm: "bpy.types.Object", tolerance: float = 1e-6) -> Tuple[bool, str]:
    moved = [pb.name for pb in arm.pose.bones if not _is_identity(pb.matrix_basis, tolerance)]
    return not moved, (f"{len(moved)} posed bone(s): {moved[:5]}" if moved else "all pose bones at rest")


def _is_identity(matrix: Matrix, tolerance: float = 1e-6) -> bool:
    return all(abs(matrix[i][j] - (1.0 if i == j else 0.0)) <= tolerance for i in range(4) for j in range(4))


# --------------------------------------------------------------------------- geometry

def evaluated_world(obj: "bpy.types.Object") -> Tuple[np.ndarray, List[Tuple[int, ...]]]:
    """World-space vertex positions and polygons of ``obj`` with its modifiers (the current pose) applied."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        coords = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", coords)
        coords = coords.reshape(-1, 3)
        matrix = np.array(obj.matrix_world)
        coords = coords @ matrix[:3, :3].T + matrix[:3, 3]
        polygons = [tuple(p.vertices) for p in mesh.polygons]
    finally:
        evaluated.to_mesh_clear()
    return coords, polygons


def dominant_regions(obj: "bpy.types.Object") -> np.ndarray:
    """Per-vertex body region from the heaviest deforming vertex group."""
    names = {group.index: group.name for group in obj.vertex_groups}
    regions = []
    for vertex in obj.data.vertices:
        best = max(vertex.groups, key=lambda g: g.weight, default=None)
        regions.append(bone_region(names.get(best.group, "")) if best is not None else "torso")
    return np.array(regions)


class Collider:
    """A BVH over one or more (posed) meshes with a body region per polygon."""

    def __init__(self, objects: Sequence["bpy.types.Object"], regions: Optional[Sequence[np.ndarray]] = None):
        verts: List[Tuple[float, float, float]] = []
        polys: List[Tuple[int, ...]] = []
        poly_region: List[str] = []
        for index, obj in enumerate(objects):
            coords, polygons = evaluated_world(obj)
            vert_region = regions[index] if regions is not None else None
            base = len(verts)
            verts.extend(map(tuple, coords))
            for polygon in polygons:
                polys.append(tuple(base + i for i in polygon))
                if vert_region is None:
                    poly_region.append("torso")
                else:
                    labels, counts = np.unique(vert_region[list(polygon)], return_counts=True)
                    poly_region.append(str(labels[np.argmax(counts)]))
        self.tree = BVHTree.FromPolygons(verts, polys)
        self.poly_region = np.array(poly_region)

    def signed(self, points: np.ndarray, max_distance: float = 0.5) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Signed distance (negative = inside), whether a surface was found, and the nearest polygon's region."""
        distance = np.full(len(points), np.inf)
        found = np.zeros(len(points), dtype=bool)
        region = np.full(len(points), "", dtype=object)
        for i, point in enumerate(points):
            hit, normal, index, dist = self.tree.find_nearest(Vector(point), max_distance)
            if hit is None:
                continue
            found[i] = True
            region[i] = self.poly_region[index]
            distance[i] = dist if (Vector(point) - hit).dot(normal) >= 0.0 else -dist
        return distance, found, region


def fraction_inside(points_obj: "bpy.types.Object", volume_obj: "bpy.types.Object") -> Dict[str, float]:
    """How much of ``points_obj`` lies inside the closed mesh ``volume_obj`` (used to validate the hair proxy)."""
    collider = Collider([volume_obj])
    coords, _ = evaluated_world(points_obj)
    distance, found, _ = collider.signed(coords, max_distance=1.0)
    inside = found & (distance <= 0.0)
    outside = distance[found & (distance > 0.0)]
    return {"fraction": round(float(np.mean(inside)), 4), "vertices": int(len(coords)),
            "max_outside_cm": round(float(outside.max() * 100.0) if len(outside) else 0.0, 3)}


# --------------------------------------------------------------------------- the gate

def _check(name: str, obj: Optional[str], passed: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "object": obj, "passed": bool(passed), "detail": detail}


def _single_armature(meshes: Sequence["bpy.types.Object"]) -> Tuple[Optional["bpy.types.Object"], List[str]]:
    found = []
    for obj in meshes:
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE" and modifier.object is not None and modifier.object not in found:
                found.append(modifier.object)
    return (found[0] if len(found) == 1 else None), [a.name for a in found]


def _fitbody_objects(base: str, lock: Dict[str, Any]) -> Dict[str, "bpy.types.Object"]:
    return {role: bpy.data.objects.get(name) for role, name in lock["objects"].items()}


def _section_vertices(obj: "bpy.types.Object") -> Tuple[np.ndarray, List[str]]:
    """Boolean mask of vertices used by a ``*_Sim`` section, and the sim slot names."""
    mesh = obj.data
    sim_slots = [i for i, m in enumerate(mesh.materials) if m is not None and m.name.endswith(SIM_SUFFIX)]
    mask = np.zeros(len(mesh.vertices), dtype=bool)
    for polygon in mesh.polygons:
        if polygon.material_index in sim_slots:
            mask[list(polygon.vertices)] = True
    return mask, [mesh.materials[i].name for i in sim_slots]


def _weights(obj: "bpy.types.Object", bone_names: Set[str]) -> List[Dict[str, float]]:
    names = {group.index: group.name for group in obj.vertex_groups}
    return [{names[g.group]: g.weight for g in v.groups if g.weight > 0.0 and names.get(g.group) in bone_names}
            for v in obj.data.vertices]


def _weight_checks(obj, rules, garment_type, socket_bone, body_bones, arm, sim_mask) -> List[Dict[str, Any]]:
    bone_names = {bone.name for bone in arm.data.bones}
    per_vertex = _weights(obj, bone_names)
    used: Dict[str, int] = {}
    for weights in per_vertex:
        for name in weights:
            used[name] = used.get(name, 0) + 1
    allowed_spec = rules["bones"]
    if allowed_spec == "body":
        allowed = set(body_bones)
        label = f"bones the fitting body is weighted to ({len(allowed)})"
    elif allowed_spec == "socket":
        allowed = {socket_bone} if socket_bone else set()
        label = f"the socket bone {socket_bone!r}"
    else:
        allowed = set(allowed_spec)
        label = ", ".join(allowed_spec)
    outside = {name: count for name, count in used.items() if name not in allowed}
    checks = [_check(f"{garment_type}_weight_bones", obj.name, not outside and bool(used),
                     (f"{sum(outside.values())} weight(s) on {sorted(outside)[:8]}; allowed: {label}" if outside
                      else f"bones used {sorted(used)} (allowed: {label})"))]
    counts = [len(weights) for weights in per_vertex]
    limit = rules["max_influences"]
    worst = max(counts, default=0)
    checks.append(_check("garment_max_influences", obj.name, worst <= limit,
                         f"max {worst} influence(s) (limit {limit} for {garment_type})"))
    if limit == 1:
        partial = sum(1 for weights in per_vertex if len(weights) != 1 or abs(sum(weights.values()) - 1.0) > 1e-6)
        checks.append(_check("rigid_single_bone", obj.name, partial == 0 and len(used) == 1,
                             f"{len(used)} bone(s) used, {partial} vertex/vertices not rigid on one bone"))
    if rules["sim"]:
        sim_indices = np.nonzero(sim_mask)[0]
        bad = [i for i in sim_indices
               if len(per_vertex[i]) != 1 or next(iter(per_vertex[i])) not in CLOAK_HANG_BONES]
        hang = sorted({next(iter(per_vertex[i])) for i in sim_indices if len(per_vertex[i]) == 1})
        checks.append(_check("cloak_sim_rigid_on_chest", obj.name, len(sim_indices) > 0 and not bad,
                             f"{len(sim_indices)} simulated vertices ride {hang}; {len(bad)} not rigid on "
                             f"{'/'.join(CLOAK_HANG_BONES)} (Outfit_Pipeline trap 4)"))
    return checks


def _intersection_checks(garments, rules, fit, arm, sim_masks, report_metrics) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    skin = [fit["body"], fit["head"]]
    skin_regions = [dominant_regions(obj) for obj in skin]
    stages = [("rest", None)] + [(name, ops) for name, ops in POSES.items()]
    metrics: Dict[str, Any] = {}
    try:
        for stage, ops in stages:
            if ops is None:
                clear_pose(arm)
            else:
                apply_pose(arm, ops)
            collider = Collider(skin, skin_regions)
            ignore = rules["rest_ignore"] if ops is None else rules["pose_ignore"]
            tolerance = REST_TOLERANCE_M if ops is None else POSE_TOLERANCE_M
            checked = inside = inside_any = 0
            deepest = 0.0
            for obj in garments:
                coords, _ = evaluated_world(obj)
                select = np.ones(len(coords), dtype=bool)
                if ops is not None and rules["pose_verts"] == "skinned":
                    select &= ~sim_masks[obj.name]
                distance, found, region = collider.signed(coords[select])
                counted = found & ~np.isin(region, list(ignore))
                depth = np.where(counted, -distance, 0.0)
                checked += int(np.count_nonzero(select))
                inside += int(np.count_nonzero(depth > tolerance))
                inside_any += int(np.count_nonzero(depth > 0.0))
                deepest = max(deepest, float(depth.max()) if len(depth) else 0.0)
            fraction = inside / checked if checked else 0.0
            metrics[stage] = {"checked": checked, "inside": inside, "inside_any_depth": inside_any,
                              "deepest_cm": round(deepest * 100.0, 2), "fraction": round(fraction, 5)}
            if ops is None:
                passed = inside <= REST_MAX_VERTS
                limit = f"limit {REST_MAX_VERTS} deeper than {REST_TOLERANCE_M * 1000:.0f} mm"
            else:
                passed = fraction <= POSE_MAX_FRACTION
                limit = f"limit {POSE_MAX_FRACTION:.0%} deeper than {POSE_TOLERANCE_M * 1000:.0f} mm"
            ignored = f", ignoring {sorted(ignore)}" if ignore else ""
            what = "skinned vertices" if (ops is not None and rules["pose_verts"] == "skinned") else "vertices"
            checks.append(_check(f"intersection_{stage}", ",".join(o.name for o in garments), passed,
                                 f"{inside} of {checked} {what} inside the skin ({fraction:.2%}); deepest "
                                 f"{deepest * 100:.2f} cm; {inside_any} at any depth{ignored}; {limit}"))
        if rules["hair"]:
            clear_pose(arm)
            hair = Collider([fit["hair_proxy"]])
            inside = checked = 0
            deepest = 0.0
            for obj in garments:
                coords, _ = evaluated_world(obj)
                distance, found, _ = hair.signed(coords)
                depth = np.where(found, -distance, 0.0)
                checked += len(coords)
                inside += int(np.count_nonzero(depth > REST_TOLERANCE_M))
                deepest = max(deepest, float(depth.max()) if len(depth) else 0.0)
            metrics["hair"] = {"checked": checked, "inside": inside, "deepest_cm": round(deepest * 100.0, 2)}
            checks.append(_check("hair_clearance", ",".join(o.name for o in garments), inside == 0,
                                 f"{inside} of {checked} vertices inside the hair proxy (deepest {deepest * 100:.2f} cm); "
                                 f"limit 0 deeper than {REST_TOLERANCE_M * 1000:.0f} mm"))
    finally:
        clear_pose(arm)
    report_metrics["intersection"] = metrics
    return checks


def qa_garment(objects: Iterable[ObjectLike], garment_type: str, base: str = DEFAULT_BASE,
               socket_bone: Optional[str] = None, extra_loadout_tris: int = 0,
               waive: Optional[Dict[str, str]] = None, core: bool = True,
               triangle_budget: Optional[int] = None, unique_uvs: bool = False) -> Dict[str, Any]:
    """Run the garment gates on ``objects`` (the garment meshes, skinned to the base armature).

    ``unique_uvs`` makes qa_check's UV0 overlap / tile-range items blocking (baked textures); by default a garment
    may tile its fabric and those items are informational (``TILING_UV_CHECKS``).
    """
    from pipeline.qa_check import evaluated_triangles, qa_check  # local import: qa_check imports helpers too

    if garment_type not in GARMENT_TYPES:
        raise ValueError(f"garment_type must be one of {GARMENT_TYPES}, got {garment_type!r}")
    waive = dict(waive or {})
    bad_waivers = sorted(set(waive) - set(WAIVABLE))
    if bad_waivers:
        raise ValueError(f"only {WAIVABLE} can be waived, not {bad_waivers}")
    rules = TYPE_RULES[garment_type]
    if rules["bones"] == "socket" and not socket_bone:
        raise ValueError("rigid_socket needs socket_bone")
    garments = [obj for obj in resolve_objects(objects) if obj.type == "MESH"]
    if not garments:
        raise ValueError("no garment meshes")
    lock = load_base_lock(base)
    checks: List[Dict[str, Any]] = []
    metrics: Dict[str, Any] = {"type": garment_type, "base": base, "skeleton_hash_lock": lock["skeleton_hash"]}

    if core:
        core_result = qa_check(garments, require_ucx=False, max_influences=rules["max_influences"])
        for check in core_result["checks"]:
            if check["name"] in TILING_UV_CHECKS and not unique_uvs and not check["passed"]:
                check["passed"] = True
                check["detail"] = "informational (tiling fabric UVs allowed on a garment): " + check["detail"]
        checks.extend(core_result["checks"])

    # 1. skeleton
    arm, armatures = _single_armature(garments)
    checks.append(_check("single_armature", None, arm is not None,
                         f"armature modifier targets: {armatures or 'none'}"))
    if arm is None:
        return _finish(checks, waive, metrics)
    checks.append(_check("armature_object_name", arm.name, arm.name == lock["armature_object"],
                         f"armature object {arm.name!r}; Unreal turns the armature object into the root bone, so it "
                         f"must be {lock['armature_object']!r} (anything else adds a bone above it)"))
    checks.append(_check("armature_transform_identity", arm.name, _is_identity(arm.matrix_world),
                         "armature matrix_world must be identity (the fitting body is baked to metres)"))
    rest_ok, rest_detail = in_rest_pose(arm, tolerance=1e-4)
    checks.append(_check("armature_rest_pose", arm.name, rest_ok, rest_detail))
    ok, detail, numbers = compare_skeleton(arm, lock["skeleton"])
    metrics["skeleton"] = numbers
    checks.append(_check("skeleton_matches_base", arm.name, ok, detail))
    for obj in garments:
        checks.append(_check("garment_parented_to_armature", obj.name,
                             obj.parent == arm and _is_identity(obj.matrix_world),
                             f"parent {obj.parent.name if obj.parent else None}; matrix_world identity "
                             f"{_is_identity(obj.matrix_world)}"))

    # 2. fitting body intact
    fit = _fitbody_objects(base, lock)
    missing = [role for role in ("body", "head", "hair_proxy") if fit.get(role) is None]
    if missing:
        checks.append(_check("fitbody_intact", None, False, f"fitting body object(s) missing: {missing}"))
        return _finish(checks, waive, metrics)
    changed = [obj.name for obj in (fit["body"], fit["head"], fit["hair_proxy"])
               if mesh_record(obj)["coords_sha256"] != lock["meshes"][obj.name]["coords_sha256"]
               or mesh_record(obj)["topology_sha256"] != lock["meshes"][obj.name]["topology_sha256"]]
    rigged = all(any(m.type == "ARMATURE" and m.object == arm for m in fit[r].modifiers) for r in ("body", "head", "hair_proxy"))
    checks.append(_check("fitbody_intact", None, not changed and rigged,
                         f"changed vs lock: {changed or 'none'}; fitting body driven by {arm.name!r}: {rigged}"))

    # 3. sections and materials
    sim_masks: Dict[str, np.ndarray] = {}
    for obj in garments:
        mask, sim_slots = _section_vertices(obj)
        sim_masks[obj.name] = mask
        slots = [m.name if m else None for m in obj.data.materials]
        checks.append(_check("section_count", obj.name, 0 < len(slots) <= MAX_SECTIONS,
                             f"{len(slots)} material slot(s) {slots} (limit {MAX_SECTIONS})"))
        if rules["sim"]:
            checks.append(_check("cloth_section", obj.name, len(sim_slots) == 1 and len(slots) > 1,
                                 f"sim slots {sim_slots}; a cloak needs exactly one *{SIM_SUFFIX} section beside "
                                 f"its skinned ones (Outfit_Pipeline trap 5)"))
            active = obj.data.color_attributes.active_color
            checks.append(_check("pin_mask_active", obj.name, active is not None and active.name == PIN_MASK,
                                 f"active colour {active.name if active else None!r}; the FBX exporter writes the active "
                                 f"colour and Unreal's cloth mask reads it (trap 9)"))
        else:
            checks.append(_check("cloth_section", obj.name, not sim_slots,
                                 f"sim slots {sim_slots or 'none'} ({garment_type} garments carry no cloth section)"))

    # 4. weights
    body_bones = set()
    for role in ("body", "head"):
        body_bones |= {g.name for g in fit[role].vertex_groups}
    for obj in garments:
        checks.extend(_weight_checks(obj, rules, garment_type, socket_bone, body_bones, arm, sim_masks[obj.name]))

    # 5. budgets
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tris = sum(evaluated_triangles(obj, depsgraph) for obj in garments)
    budget = triangle_budget if triangle_budget is not None else rules["triangles"]
    sim_tris = 0
    sim_verts = 0
    for obj in garments:
        mesh = obj.data
        sim_slots = {i for i, m in enumerate(mesh.materials) if m is not None and m.name.endswith(SIM_SUFFIX)}
        sim_tris += sum(len(p.vertices) - 2 for p in mesh.polygons if p.material_index in sim_slots)
        sim_verts += int(np.count_nonzero(sim_masks[obj.name]))
    base_tris = int(lock["triangles"]["base_lod0_total"])
    total = base_tris + tris + int(extra_loadout_tris)
    metrics["triangles"] = {"garment": tris, "sim": sim_tris, "sim_vertices": sim_verts, "base_lod0": base_tris,
                            "extra_loadout": int(extra_loadout_tris), "character_total": total}
    checks.append(_check("garment_triangle_budget", None, tris <= budget,
                         f"{tris} triangles (budget {budget} for {garment_type})"))
    if rules["sim"]:
        checks.append(_check("sim_triangle_budget", None, 0 < sim_tris <= SIM_TRIANGLE_BUDGET,
                             f"{sim_tris} simulated triangles / {sim_verts} cloth particles "
                             f"(budget {SIM_TRIANGLE_BUDGET} triangles)"))
    checks.append(_check("character_triangle_budget", None, total <= CHARACTER_TRIANGLE_BUDGET,
                         f"base LOD0 {base_tris} + garment {tris} + other worn {int(extra_loadout_tris)} = {total} "
                         f"(budget {CHARACTER_TRIANGLE_BUDGET}; the base alone is {base_tris})"))

    # 6. intersection (poses the armature; always restored)
    checks.extend(_intersection_checks(garments, rules, fit, arm, sim_masks, metrics))
    return _finish(checks, waive, metrics)


def _finish(checks: List[Dict[str, Any]], waive: Dict[str, str], metrics: Dict[str, Any]) -> Dict[str, Any]:
    for check in checks:
        if not check["passed"] and check["name"] in waive:
            check["waived"] = waive[check["name"]]
    blocking = [c for c in checks if not c["passed"] and "waived" not in c]
    return {"passed": not blocking, "checks": checks, "metrics": metrics,
            "waived": [{"name": c["name"], "reason": c["waived"]} for c in checks if "waived" in c],
            "failed": sorted({c["name"] for c in blocking})}


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(prog="garment_qa.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--objects", required=True)
    parser.add_argument("--type", required=True, choices=GARMENT_TYPES)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--socket-bone", default=None)
    parser.add_argument("--extra-loadout-tris", type=int, default=0)
    parser.add_argument("--waive", action="append", default=[], help='name="reason" (only character_triangle_budget)')
    parser.add_argument("--json", default=None)
    return parser.parse_args(argv)


def parse_waivers(items: Iterable[str]) -> Dict[str, str]:
    waivers = {}
    for item in items:
        name, _, reason = item.partition("=")
        if not reason.strip():
            raise ValueError(f"waiver {name!r} needs a reason: --waive {name}=\"why\"")
        waivers[name.strip()] = reason.strip().strip('"')
    return waivers


def main() -> int:
    args = _parse_args()
    try:
        result = qa_garment([n.strip() for n in args.objects.split(",") if n.strip()], args.type, base=args.base,
                            socket_bone=args.socket_bone, extra_loadout_tris=args.extra_loadout_tris,
                            waive=parse_waivers(args.waive))
    except Exception as exc:  # noqa: BLE001 - the CLI contract is JSON on stdout plus exit 1
        result = {"passed": False, "checks": [], "error": f"{type(exc).__name__}: {exc}"}
    text = json.dumps(result, indent=2, default=str)
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
