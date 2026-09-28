"""Build helpers for garments on the locked character base (ASSET_GUIDELINES.md 12.10).

Everything here runs inside Blender, returns what it made and never saves. The gates live in ``garment_qa``; the
command-line tools that string these together live in ``Scripts/garments/``. The algorithms are the ones the
BlackCloak MetaHuman fit proved (DemoGame_1 ``Tools/Claude/Blender/fit_cloak_mh.py`` / ``build_cloak_mh.py``,
2026-09-26), generalised by garment type:

* ``append_fitbody`` - the locked body/head/hair proxy/``root`` armature, appended (not linked: the gates pose the
  armature, and linked data cannot be posed) and made unselectable; ``garment_qa`` re-hashes it before export.
* skinning - ``skin_cloak`` (spine chain; tight pieces blended by height between the two spine bones that bracket
  each vertex, simulated panels rigid on the chest bone at their top edge, clamped to spine_03..spine_05:
  Outfit_Pipeline traps 3 and 4), ``transfer_body_weights`` (fitted: the body's own weights interpolated from the
  nearest body triangle, top 8, normalised), ``skin_rigid`` (hats, sockets).
* ``bake_pin_mask`` - the sculpt's ``CLOTH_Pin`` groups into the red ``PinMask`` corner colour Unreal reads.
* ``decimate_group`` - one Collapse ratio per group (the simulated panels and the skinned pieces get separate
  budgets, trap 5 and the cloak's hood lesson); ``garment_hard`` pieces (metal hardware) are never decimated.
* ``clearance_pass`` - push garment vertices out of the skin to a clearance (sim 1.5 cm, tight 1.0 cm), spreading
  each push in space so neighbours move together (trap 15), arms ignored.
* ``refit_warp`` - legacy garments sculpted on another body (Manny): a thin-plate-spline warp on skeleton landmarks
  (neck, head, clavicles, arms, crown; floor pinned; not the spine bones), then ``clearance_pass`` with the "hug"
  rule for tight pieces.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

_PACKAGE_PARENT = str(Path(__file__).resolve().parents[1])
if _PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, _PACKAGE_PARENT)

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from mathutils.geometry import barycentric_transform  # noqa: E402

from pipeline import garment_qa as gq  # noqa: E402
from pipeline.helpers import apply_modifier  # noqa: E402

GARMENT_COLLECTION = "GARMENT"
SIM_COLLECTION = "GARMENT_SIM"
HELPER_COLLECTION = "GARMENT_HELPERS"
HARD_PROP = "garment_hard"
PIN_GROUP = "CLOTH_Pin"
BUILD_MODIFIERS = {"SOLIDIFY", "SUBSURF"}
# Scene properties a garment work file carries (written by new_garment.py / refit_garment.py).
SCENE_PROPS = ("garment_name", "garment_type", "garment_base", "garment_socket_bone",
               "garment_sim_target_tris", "garment_skin_target_tris")
DEFAULT_TARGETS = {"cloak": (gq.SIM_TRIANGLE_BUDGET, 20000), "fitted": (0, 20000), "rigid_head": (0, 10000),
                   "rigid_socket": (0, 5000)}
CLEAR_TIGHT = 0.010
CLEAR_SIM = 0.015
CLEAR_FACE = 0.015
HUG = 0.035
SPREAD_RADIUS = 0.05
MAX_STEP = 0.03
CLEARANCE_ROUNDS = 12
LANDMARKS = ("neck_01", "neck_02", "head", "clavicle_l", "clavicle_r", "upperarm_l", "upperarm_r", "lowerarm_l",
             "lowerarm_r", "hand_l", "hand_r")


# --------------------------------------------------------------------------- the work file

def append_fitbody(base: str = gq.DEFAULT_BASE, verify_file: bool = True) -> Dict[str, "bpy.types.Object"]:
    """Append the locked fitting body collection into the current file and return its objects by role."""
    lock = gq.load_base_lock(base)
    path = gq.ROOT / lock["blend"]
    if verify_file:
        got = gq.file_sha256(path)
        if got != lock["blend_sha256"]:
            raise RuntimeError(f"{path} sha256 {got} does not match base_lock.json {lock['blend_sha256']}")
    name = lock["collection"]
    if bpy.data.collections.get(name) is not None:
        raise RuntimeError(f"{name} is already in this file")
    if bpy.data.objects.get(lock["armature_object"]) is not None:
        raise RuntimeError(f"an object named {lock['armature_object']!r} already exists; the base armature needs "
                           f"that exact name (Unreal's root bone)")
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.collections = [name]
    collection = target.collections[0]
    bpy.context.scene.collection.children.link(collection)
    objects = {role: bpy.data.objects[obj_name] for role, obj_name in lock["objects"].items()}
    objects["armature"] = bpy.data.objects[lock["armature_object"]]
    for obj in collection.all_objects:
        obj.hide_select = True
    collection.hide_select = True
    bpy.context.view_layer.update()
    return objects


def ensure_collections() -> Dict[str, "bpy.types.Collection"]:
    """GARMENT (skinned pieces), GARMENT_SIM (cloth panels), GARMENT_HELPERS (never exported)."""
    made = {}
    for name in (GARMENT_COLLECTION, SIM_COLLECTION, HELPER_COLLECTION):
        collection = bpy.data.collections.get(name)
        if collection is None:
            collection = bpy.data.collections.new(name)
            bpy.context.scene.collection.children.link(collection)
        made[name] = collection
    return made


def move_to(obj: "bpy.types.Object", collection: "bpy.types.Collection") -> None:
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    collection.objects.link(obj)


def garment_pieces() -> Tuple[List["bpy.types.Object"], List["bpy.types.Object"]]:
    """(skinned pieces, simulated pieces) - the meshes in GARMENT and GARMENT_SIM, in name order."""
    skinned = bpy.data.collections.get(GARMENT_COLLECTION)
    sim = bpy.data.collections.get(SIM_COLLECTION)
    return (sorted([o for o in (skinned.objects if skinned else []) if o.type == "MESH"], key=lambda o: o.name),
            sorted([o for o in (sim.objects if sim else []) if o.type == "MESH"], key=lambda o: o.name))


def scene_settings() -> Dict[str, Any]:
    scene = bpy.context.scene
    return {key: scene.get(key) for key in SCENE_PROPS}


def tris(obj: "bpy.types.Object") -> int:
    return sum(max(len(p.vertices) - 2, 0) for p in obj.data.polygons)


# --------------------------------------------------------------------------- geometry prep

def strip_build_modifiers(objects: Iterable["bpy.types.Object"]) -> Dict[str, List[str]]:
    """Remove SOLIDIFY / SUBSURF (cloth simulates one layer; thickness comes from a two-sided material)."""
    kept = {}
    for obj in objects:
        for modifier in list(obj.modifiers):
            if modifier.type in BUILD_MODIFIERS:
                obj.modifiers.remove(modifier)
        if obj.modifiers:
            kept[obj.name] = [m.type for m in obj.modifiers]
    return kept


def decimate_group(objects: Sequence["bpy.types.Object"], target_tris: int) -> Dict[str, Any]:
    """Apply one Collapse Decimate ratio (target / current, capped at 1) to every object in the group."""
    before = sum(tris(o) for o in objects)
    ratio = min(1.0, float(target_tris) / max(before, 1)) if target_tris else 1.0
    if ratio < 1.0:
        for obj in objects:
            modifier = obj.modifiers.new("Decimate", "DECIMATE")
            modifier.ratio = ratio
            modifier.use_collapse_triangulate = True
            apply_modifier(obj, modifier)
    return {"pieces": len(objects), "before": before, "after": sum(tris(o) for o in objects), "ratio": ratio}


def bake_pin_mask(obj: "bpy.types.Object") -> int:
    """``CLOTH_Pin`` weight -> red channel of a ``PinMask`` corner colour; return the vertices pinned above 0.5."""
    mesh = obj.data
    layer = mesh.color_attributes.new(name=gq.PIN_MASK, type="BYTE_COLOR", domain="CORNER")
    group = obj.vertex_groups.get(PIN_GROUP)
    for polygon in mesh.polygons:
        for index in polygon.loop_indices:
            vertex = mesh.loops[index].vertex_index
            weight = 0.0
            if group:
                try:
                    weight = group.weight(vertex)
                except RuntimeError:
                    weight = 0.0
            layer.data[index].color = (weight, 0.0, 0.0, 1.0)
    return sum(1 for v in mesh.vertices if group and any(g.group == group.index and g.weight > 0.5 for g in v.groups))


# --------------------------------------------------------------------------- skinning

def spine_anchors(arm: "bpy.types.Object") -> List[Tuple[str, float]]:
    """The spine chain (pelvis .. head) with each bone's rest head height, lowest first."""
    anchors = [(name, (arm.matrix_world @ arm.data.bones[name].head_local).z) for name in gq.SPINE_CHAIN
               if arm.data.bones.get(name)]
    return sorted(anchors, key=lambda a: a[1])


def skin_cloak(obj: "bpy.types.Object", arm: "bpy.types.Object", rigid: bool) -> str:
    """Spine-chain skinning: ``rigid`` rides one chest bone (clamped to spine_03..05), else a height blend."""
    anchors = spine_anchors(arm)
    hang_lo = next(i for i, a in enumerate(anchors) if a[0] == gq.CLOAK_HANG_BONES[0])
    hang_hi = next(i for i, a in enumerate(anchors) if a[0] == gq.CLOAK_HANG_BONES[-1])
    for group in list(obj.vertex_groups):
        obj.vertex_groups.remove(group)
    groups = {name: obj.vertex_groups.new(name=name) for name, _ in anchors}
    indices = [v.index for v in obj.data.vertices]
    if rigid:
        top = max((obj.matrix_world @ v.co).z for v in obj.data.vertices)
        index = min(range(len(anchors)), key=lambda i: abs(anchors[i][1] - top))
        index = max(hang_lo, min(hang_hi, index))
        groups[anchors[index][0]].add(indices, 1.0, "REPLACE")
        return anchors[index][0]
    for vertex in obj.data.vertices:
        z = (obj.matrix_world @ vertex.co).z
        if z <= anchors[0][1]:
            groups[anchors[0][0]].add([vertex.index], 1.0, "REPLACE")
        elif z >= anchors[-1][1]:
            groups[anchors[-1][0]].add([vertex.index], 1.0, "REPLACE")
        else:
            for (lower, lz), (upper, uz) in zip(anchors, anchors[1:]):
                if lz <= z <= uz:
                    t = (z - lz) / max(uz - lz, 1e-6)
                    groups[lower].add([vertex.index], 1.0 - t, "REPLACE")
                    groups[upper].add([vertex.index], t, "REPLACE")
                    break
    return "height blend"


def transfer_body_weights(obj: "bpy.types.Object", sources: Sequence["bpy.types.Object"],
                          max_influences: int = 8) -> Dict[str, Any]:
    """Fitted garments: each vertex takes the body weights interpolated at its nearest body triangle.

    Right for a garment that genuinely follows the limbs (shirt, trousers, gloves); wrong for loose fabric, where
    it puts a hem on the feet (Outfit_Pipeline trap 3) - use ``skin_cloak`` there.
    """
    verts: List[Vector] = []
    tri_list: List[Tuple[int, int, int]] = []
    vertex_weights: List[Dict[str, float]] = []
    for source in sources:
        names = {g.index: g.name for g in source.vertex_groups}
        base = len(verts)
        verts.extend(source.matrix_world @ v.co for v in source.data.vertices)
        vertex_weights.extend({names[g.group]: g.weight for g in v.groups if g.weight > 0.0}
                              for v in source.data.vertices)
        source.data.calc_loop_triangles()
        tri_list.extend(tuple(base + i for i in t.vertices) for t in source.data.loop_triangles)
    tree = BVHTree.FromPolygons(verts, tri_list)
    per_vertex = []
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        hit, _normal, index, _dist = tree.find_nearest(point)
        a, b, c = tri_list[index]
        # barycentric weights of the hit point in the triangle
        wa = barycentric_transform(hit, verts[a], verts[b], verts[c], Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
        blend: Dict[str, float] = {}
        for corner, factor in zip((a, b, c), (max(wa.x, 0.0), max(wa.y, 0.0), max(wa.z, 0.0))):
            for bone, weight in vertex_weights[corner].items():
                blend[bone] = blend.get(bone, 0.0) + weight * factor
        top = sorted(blend.items(), key=lambda kv: -kv[1])[:max_influences]
        total = sum(w for _b, w in top) or 1.0
        per_vertex.append([(bone, w / total) for bone, w in top])
    for group in list(obj.vertex_groups):
        if group.name != PIN_GROUP:
            obj.vertex_groups.remove(group)
    groups: Dict[str, Any] = {}
    for index, weights in enumerate(per_vertex):
        for bone, weight in weights:
            group = groups.get(bone) or obj.vertex_groups.new(name=bone)
            groups[bone] = group
            group.add([index], weight, "REPLACE")
    return {"bones": sorted(groups), "max_influences": max((len(w) for w in per_vertex), default=0)}


def skin_rigid(obj: "bpy.types.Object", bone: str) -> None:
    for group in list(obj.vertex_groups):
        if group.name != PIN_GROUP:
            obj.vertex_groups.remove(group)
    obj.vertex_groups.new(name=bone).add([v.index for v in obj.data.vertices], 1.0, "REPLACE")


def make_sim_material(sim_pieces: Sequence["bpy.types.Object"]) -> Optional["bpy.types.Material"]:
    """Give the simulated pieces their own copy of their material, named ``<material>_Sim`` (one cloth section)."""
    if not sim_pieces:
        return None
    sources = {slot.material.name for obj in sim_pieces for slot in obj.material_slots if slot.material}
    if len(sources) != 1:
        raise ValueError(f"simulated pieces must share one material (one cloth section), found {sorted(sources)}")
    source = bpy.data.materials[sources.pop()]
    sim = source.copy()
    sim.name = source.name + gq.SIM_SUFFIX
    for obj in sim_pieces:
        for index in range(len(obj.data.materials)):
            obj.data.materials[index] = sim
    return sim


def join(first: "bpy.types.Object", others: Sequence["bpy.types.Object"], name: str) -> "bpy.types.Object":
    """Join ``others`` into ``first`` (which keeps its material slots first) and rename it ``name``."""
    everything = [first] + [o for o in others if o is not first]
    if len(everything) == 1:  # a one-piece garment: object.join cancels with nothing to join
        first.name = name
        first.data.name = name
        return first
    view_layer = bpy.context.view_layer
    for obj in view_layer.objects:
        obj.select_set(False)
    for obj in everything:  # helpers.selection() cannot be used: it would restore objects the join consumed
        obj.hide_set(False)
        obj.hide_select = False
        obj.select_set(True)
    view_layer.objects.active = first
    with bpy.context.temp_override(active_object=first, object=first, selected_objects=everything,
                                   selected_editable_objects=everything):
        result = bpy.ops.object.join()
    first.select_set(False)
    if "FINISHED" not in result:
        raise RuntimeError(f"join failed: {result}")
    first.name = name
    first.data.name = name
    return first


def triangulate_ngons(obj: "bpy.types.Object") -> int:
    """Triangulate n-gons only (house rule: no n-gons), with the FBX exporter's own BEAUTY method."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    ngons = [face for face in bm.faces if len(face.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(obj.data)
        obj.data.update()
    bm.free()
    return len(ngons)


def bind(obj: "bpy.types.Object", arm: "bpy.types.Object") -> None:
    """Armature modifier + parent to the (identity-transform) base armature, keeping the mesh where it is."""
    for modifier in [m for m in obj.modifiers if m.type == "ARMATURE"]:
        obj.modifiers.remove(modifier)
    obj.modifiers.new("Armature", "ARMATURE").object = arm
    world = obj.matrix_world.copy()
    obj.parent = arm
    obj.matrix_parent_inverse = arm.matrix_world.inverted()
    obj.matrix_world = world


def set_active_pin_mask(obj: "bpy.types.Object") -> None:
    attributes = obj.data.color_attributes
    layer = attributes.get(gq.PIN_MASK)
    if layer is not None:
        attributes.active_color = layer
        attributes.render_color_index = list(attributes).index(layer)


def unpack_textures(out_dir: Path) -> List[str]:
    """Write every packed image as ``<name>.png`` (the extension forced: Outfit_Pipeline trap 12)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for image in bpy.data.images:
        if image.packed_file and image.name != "Render Result":
            name = image.name if os.path.splitext(image.name)[1].lower() == ".png" else image.name + ".png"
            path = out_dir / name
            image.file_format = "PNG"
            image.filepath_raw = str(path)
            image.save()
            written.append(str(path))
    return written


# --------------------------------------------------------------------------- clearance and refit

def _coords(obj: "bpy.types.Object") -> np.ndarray:
    array = np.empty(len(obj.data.vertices) * 3)
    obj.data.vertices.foreach_get("co", array)
    return array.reshape(-1, 3)


def _set_coords(obj: "bpy.types.Object", array: np.ndarray) -> None:
    obj.data.vertices.foreach_set("co", array.reshape(-1).astype(np.float64))
    obj.data.update()


class SkinTree:
    """BVH of skin meshes (world space, rest) with a per-polygon "on an arm" flag, as the cloak fit used it."""

    def __init__(self, objects: Sequence["bpy.types.Object"], arm_regions: Set[str] = frozenset({"arm"})):
        verts, polys, arm = [], [], []
        for obj in objects:
            names = {g.index: g.name for g in obj.vertex_groups}
            vert_arm = []
            for vertex in obj.data.vertices:
                best = max(vertex.groups, key=lambda g: g.weight, default=None)
                vert_arm.append(bool(best) and gq.bone_region(names.get(best.group, "")) in arm_regions)
            base = len(verts)
            verts += [obj.matrix_world @ v.co for v in obj.data.vertices]
            for polygon in obj.data.polygons:
                polys.append(tuple(base + i for i in polygon.vertices))
                arm.append(sum(vert_arm[i] for i in polygon.vertices) * 2 > len(polygon.vertices))
        self.tree = BVHTree.FromPolygons(verts, polys)
        self.arm = np.array(arm, bool)
        self.top = max(v.z for v in verts)

    def signed(self, points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """(signed distance, normal, found, nearest-is-arm) per point; negative = under the skin."""
        d = np.zeros(len(points))
        n = np.zeros((len(points), 3))
        ok = np.zeros(len(points), bool)
        on_arm = np.zeros(len(points), bool)
        for i, point in enumerate(points):
            hit, normal, index, dist = self.tree.find_nearest(Vector(point), 0.5)
            if hit is None:
                continue
            ok[i] = True
            on_arm[i] = self.arm[index]
            d[i] = dist if (Vector(point) - hit).dot(normal) >= 0 else -dist
            n[i] = normal
        return d, n, ok, on_arm


def spread(points: np.ndarray, displacement: np.ndarray, active: np.ndarray,
           radius: float = SPREAD_RADIUS) -> np.ndarray:
    """Gaussian-weighted average of the active pushes in SPACE, faded with distance, so neighbours move together."""
    src_p = points[active]
    src_d = displacement[active]
    out = np.zeros_like(points)
    if not len(src_p):
        return out
    sigma = radius / 2.0
    for start in range(0, len(points), 2000):
        chunk = points[start:start + 2000]
        dist = np.linalg.norm(chunk[:, None, :] - src_p[None, :, :], axis=2)
        weight = np.exp(-(dist / sigma) ** 2)
        weight[dist > radius] = 0.0
        total = weight.sum(axis=1)
        average = (weight @ src_d) / np.maximum(total, 1e-12)[:, None]
        fade = np.exp(-(dist.min(axis=1) / sigma) ** 2)
        fade[total <= 0] = 0.0
        out[start:start + 2000] = average * fade[:, None]
    return out


def edge_array(obj: "bpy.types.Object") -> np.ndarray:
    edges = np.empty(len(obj.data.edges) * 2, dtype=np.int64)
    obj.data.edges.foreach_get("vertices", edges)
    return edges.reshape(-1, 2)


def clearance_pass(obj: "bpy.types.Object", skin: SkinTree, clear: float,
                   hug: Optional[np.ndarray] = None, target: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """Push ``obj`` out until no vertex is closer than ``clear`` to the skin (arms ignored).

    ``hug`` / ``target`` (refits only): tight-piece vertices that hugged the source body keep that offset, which
    also pulls them IN where the new body is slimmer.
    """
    count = len(obj.data.vertices)
    hug = np.zeros(count, bool) if hug is None else hug
    target = np.full(count, clear) if target is None else target
    rounds = 0
    for rounds in range(1, CLEARANCE_ROUNDS + 1):
        points = _coords(obj)
        d, n, ok, on_arm = skin.signed(points)
        need = np.where(hug, target - d, np.maximum(target - d, 0.0))
        need[on_arm] = 0.0
        need[~ok] = 0.0
        need[np.abs(need) < 0.0005] = 0.0
        if not np.any(need > 0.0005) and not np.any(hug & (np.abs(need) > 0.002)):
            break
        need = np.clip(need, -MAX_STEP, MAX_STEP)
        active = np.abs(need) > 0.0005
        _set_coords(obj, points + spread(points, n * need[:, None], active))
    d, _n, ok, on_arm = skin.signed(_coords(obj))
    counted = ok & ~on_arm
    return {"rounds": rounds, "inside": int(np.sum(counted & (d < 0))),
            "min_clearance_cm": round(100.0 * float(d[counted].min()), 3) if np.any(counted) else None}


def tps_fit(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Thin-plate spline (phi(r) = r, the 3-D biharmonic kernel) mapping ``src`` landmarks onto ``dst``."""
    n = len(src)
    kernel = np.linalg.norm(src[:, None, :] - src[None, :, :], axis=2)
    affine = np.hstack([np.ones((n, 1)), src])
    system = np.zeros((n + 4, n + 4))
    system[:n, :n] = kernel
    system[:n, n:] = affine
    system[n:, :n] = affine.T
    rhs = np.zeros((n + 4, 3))
    rhs[:n] = dst
    return np.linalg.solve(system, rhs)


def tps_apply(weights: np.ndarray, src: np.ndarray, points: np.ndarray) -> np.ndarray:
    n = len(src)
    kernel = np.linalg.norm(points[:, None, :] - src[None, :, :], axis=2)
    return kernel @ weights[:n] + weights[n] + points @ weights[n + 1:]


def landmark_pairs(source_arm: "bpy.types.Object", target_arm: "bpy.types.Object", source_top: float,
                   target_top: float, landmarks: Sequence[str] = LANDMARKS) -> Tuple[np.ndarray, np.ndarray]:
    """Bone-head landmarks on both skeletons, plus the crown and eight pinned floor points."""
    def head(arm, name):
        return np.array(arm.matrix_world @ arm.data.bones[name].head_local)

    src = [head(source_arm, b) for b in landmarks] + [np.array([0.0, -0.01, source_top])]
    dst = [head(target_arm, b) for b in landmarks] + [np.array([0.0, -0.01, target_top])]
    for k in range(8):
        angle = 2 * math.pi * k / 8
        point = np.array([0.7 * math.cos(angle), 0.7 * math.sin(angle), 0.0])
        src.append(point)
        dst.append(point.copy())
    return np.array(src), np.array(dst)


def refit_warp(pieces: Sequence["bpy.types.Object"], sim_names: Set[str], source_skin: SkinTree,
               target_skin: SkinTree, source_arm: "bpy.types.Object", target_arm: "bpy.types.Object",
               hug_max_bone: str = "neck_02") -> Dict[str, Any]:
    """Warp pieces sculpted on ``source`` onto the target body, then clear them (see the module docstring).

    ``garment_hard`` pieces move rigidly (translation of their centre), so rings stay round. Pieces must have
    identity transforms (local = world).
    """
    src, dst = landmark_pairs(source_arm, target_arm, source_skin.top, target_skin.top)
    weights = tps_fit(src, dst)
    report: Dict[str, Any] = {"landmarks": {name: round(float(np.linalg.norm(t - s)) * 100.0, 2)
                                            for name, s, t in zip(list(LANDMARKS) + ["crown"], src, dst)},
                              "tps_residual_m": float(np.abs(tps_apply(weights, src, src) - dst).max()),
                              "pieces": {}}
    original = {}
    for obj in pieces:
        if not gq._is_identity(obj.matrix_world):
            raise ValueError(f"{obj.name} has a transform; apply it before a refit")
        points = _coords(obj)
        original[obj.name] = points.copy()
        if obj.get(HARD_PROP):
            centre = points.mean(axis=0)
            moved = points + (tps_apply(weights, src, centre[None])[0] - centre)
        else:
            moved = tps_apply(weights, src, points)
        _set_coords(obj, moved)
    hug_max_z = float((source_arm.matrix_world @ source_arm.data.bones[hug_max_bone].head_local).z)
    for obj in pieces:
        if obj.get(HARD_PROP):
            report["pieces"][obj.name] = {"mode": "rigid"}
            continue
        sim = obj.name in sim_names
        clear = CLEAR_SIM if sim else CLEAR_TIGHT
        d0, _n0, ok0, _arm0 = source_skin.signed(original[obj.name])
        below_jaw = original[obj.name][:, 2] < hug_max_z
        hug = (~np.array([sim] * len(d0))) & ok0 & (d0 < HUG) & below_jaw
        target = np.where(hug, np.maximum(d0, clear), clear)
        if not sim:
            target = np.where(below_jaw, target, np.maximum(target, CLEAR_FACE))
        result = clearance_pass(obj, target_skin, clear, hug=hug, target=target)
        result.update({"mode": "sim" if sim else "tight", "hugging": int(hug.sum())})
        report["pieces"][obj.name] = result
    return report


def fit_report(pieces: Sequence["bpy.types.Object"], skin: SkinTree) -> Dict[str, Any]:
    """Per piece: vertices under the skin (arms ignored), deepest, and those within 5 mm."""
    out = {}
    total = 0
    for obj in pieces:
        points = _coords(obj) @ np.array(obj.matrix_world)[:3, :3].T + np.array(obj.matrix_world)[:3, 3]
        d, _n, ok, arm = skin.signed(points)
        inside = int(np.sum(ok & (d < 0) & ~arm))
        total += inside
        masked = np.where(arm, 1.0, d)
        out[obj.name] = {"vertices": len(d), "inside": inside, "deepest_cm": round(-100 * min(0.0, float(masked.min())), 2),
                         "inside_arm": int(np.sum(ok & (d < 0) & arm))}
    return {"pieces": out, "total_inside": total}
