"""Rig helpers for the gun line (GUN_BUILDING_STUDY 4.6, 4.9, 5.2; import inside Blender except the pure-numpy parts).

The study's pipeline gaps, closed here (gunlib, not Scripts/pipeline):
- rigid_skin_checks: every vertex of a gun mesh has EXACTLY one influence at weight 1.0 (qa_skeletal only checks
  "at most n" and "sums to 1");
- skeleton_standard_checks: bone names from the 5.2 table, parents as the table, every bone deforms, rest rotation =
  root's (identity), the armature object 'root' at identity;
- fbx_skeleton (call it in a FRESH Blender process on the exported bytes): the bones an FBX really carries (names,
  parents, rest heads in mm, vertex-group sizes), so a bone with no weighted vertices (the gun's 'magazine' attach bone)
  is proven to survive the export.

Bones are built the way the fan measured for Unreal: the armature OBJECT is 'root' (Unreal's root bone), every bone's
tail points along +Y from its head with roll 0 about +Z up, so its rest matrix has the identity rotation (bone axes =
armature axes = weapon axes) and a pose rotation "about Y" is a rotation about the weapon's transverse axis through the
bone head (the pivot).
"""
from __future__ import annotations

import math
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

MM = 0.001
BONE_LEN_MM = 20.0

#: GUN_BUILDING_STUDY 5.2: bone -> allowed parents (None = top-level bone under the root object)
STANDARD_BONES: Dict[str, Tuple[Optional[str], ...]] = {
    "body": (None,),
    "trigger": ("body",), "hammer": ("body",), "selector": ("body", "slide"), "mag_release": ("body",),
    "bolt_catch": ("body",), "slide_stop": ("body",), "bolt": ("body",), "charging_handle": ("body",),
    "slide": ("body",), "barrel": ("slide",), "dust_cover": ("body",), "magazine": ("body",),
    "muzzle_device": ("body",), "stock": ("body",), "stock_ext": ("stock",), "cheek_riser": ("stock",),
    "sight_front": ("body",), "sight_rear": ("body",), "bipod": ("body",), "bipod_leg_l": ("bipod",),
    "bipod_leg_r": ("bipod",), "bipod_leg_l_ext": ("bipod_leg_l",), "bipod_leg_r_ext": ("bipod_leg_r",),
    "pump": ("body",),
}


def _check(name, obj, passed, detail):
    return {"name": name, "object": obj, "passed": bool(passed), "detail": detail}


# ====================================================================== build
def make_armature(name: str, bones: Sequence[Tuple[str, Sequence[float], Optional[str]]], coll=None):
    """bones: (name, head_mm (armature space), parent or None). Tail = head + 20 mm along +Y, roll so +Z is up:
    every rest matrix has the identity rotation."""
    import bpy
    from mathutils import Vector
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    (coll or bpy.context.scene.collection).objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.view_layer.objects:
        o.select_set(o == obj)
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    for bname, head, parent in bones:
        eb = arm.edit_bones.new(bname)
        h = Vector(head) * MM
        eb.head = h
        eb.tail = h + Vector((0.0, BONE_LEN_MM * MM, 0.0))
        eb.align_roll(Vector((0.0, 0.0, 1.0)))
        eb.use_deform = True
        eb.use_connect = False
        made[bname] = eb
    for bname, head, parent in bones:
        if parent:
            made[bname].parent = made[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in obj.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return obj


def join_rigid(name: str, parts: Sequence[Tuple[object, str]], arm, mats: Sequence, slot_of, coll):
    """Copies of the part objects joined into one skinned mesh: each part's vertices in ONE vertex group (its bone)
    at weight 1.0; material slots `mats` (slot_of(ob) -> index); parented to `arm` with an Armature modifier.
    Custom split normals and UV0 are kept."""
    import bpy
    cops = []
    for ob, bone in parts:
        c = ob.copy()
        c.data = ob.data.copy()
        for k in list(c.keys()):
            del c[k]
        coll.objects.link(c)
        c.parent = None
        c.matrix_world = ob.matrix_world.copy()
        c.data.materials.clear()
        for m in mats:
            c.data.materials.append(m)
        k = slot_of(ob)
        c.data.polygons.foreach_set("material_index", [k] * len(c.data.polygons))
        c.vertex_groups.clear()
        vg = c.vertex_groups.new(name=bone)
        vg.add(list(range(len(c.data.vertices))), 1.0, "REPLACE")
        cops.append(c)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for c in cops:
        c.select_set(True)
    bpy.context.view_layer.objects.active = cops[0]
    bpy.ops.object.join()
    ob = cops[0]
    ob.name = name
    ob.data.name = name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for an in ("pid", "cls", "isl"):
        a = ob.data.attributes.get(an)
        if a is not None:
            ob.data.attributes.remove(a)
    for lay in list(ob.data.uv_layers):
        if lay.name != "UV0":
            ob.data.uv_layers.remove(lay)
    ob.parent = arm
    ob.matrix_parent_inverse.identity()
    md = ob.modifiers.new("Armature", "ARMATURE")
    md.object = arm
    return ob


def fix_collapsed_uvs(ob, delta=4e-6, limit=1e-14, layer="UV0", passes=4) -> dict:
    """qa_skeletal fails a UV0 triangle of area < 1e-14 (the coarse LODs project their faces onto the LOD0 islands, and
    a sliver can land on an island edge). Open each such triangle by `delta` UV units (0.016 px at 4096) perpendicular
    to its UV line, moving every loop that shares the moved corner's vertex AND UV (welds kept), on the side that
    matches the slot's dominant UV winding. Returns counts before / after."""
    me = ob.data
    lay = me.uv_layers[layer]
    uv = np.empty(len(lay.data) * 2)
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    lv = np.empty(len(me.loops), int)
    me.loops.foreach_get("vertex_index", lv)
    ls = np.empty(len(me.polygons), int)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(len(me.polygons), int)
    me.polygons.foreach_get("loop_total", lt)
    mi = np.empty(len(me.polygons), int)
    me.polygons.foreach_get("material_index", mi)
    tri = ls[lt == 3]
    L = np.c_[tri, tri + 1, tri + 2]

    def areas():
        a, b, c = uv[L[:, 0]], uv[L[:, 1]], uv[L[:, 2]]
        return 0.5 * ((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
    A = areas()
    before = int((np.abs(A) < limit).sum())
    mt = mi[lt == 3]
    sign = {k: (1.0 if (A[mt == k] > 0).sum() >= (A[mt == k] < 0).sum() else -1.0) for k in np.unique(mt)}
    key = {}
    for i in range(len(lv)):
        key.setdefault((lv[i], round(uv[i, 0], 9), round(uv[i, 1], 9)), []).append(i)
    for _ in range(passes):
        A = areas()
        bad = np.nonzero(np.abs(A) < limit)[0]
        if not len(bad):
            break
        for t in bad:
            l0, l1, l2 = L[t]
            a, b, c = uv[l0], uv[l1], uv[l2]
            s = sign[mt[t]]
            moves = []
            if np.linalg.norm(b - a) < 1e-9 and np.linalg.norm(c - a) < 1e-9:
                moves = [(l1, np.array([delta, 0.0])), (l2, np.array([0.0, delta * s]))]
            else:
                # the corner farthest from the opposite edge's midpoint direction: move the apex off the line
                e = [(np.linalg.norm(b - c), l0, b, c), (np.linalg.norm(c - a), l1, c, a), (np.linalg.norm(a - b), l2, a, b)]
                e.sort(key=lambda r: -r[0])
                _, apex, p, q = e[0]
                d = (q - p) / max(np.linalg.norm(q - p), 1e-12)
                n = np.array([-d[1], d[0]])
                moves = [(apex, n * delta)]
            for li, off in moves:
                k = (lv[li], round(uv[li, 0], 9), round(uv[li, 1], 9))
                trial = uv.copy()
                for lj in key.get(k, [li]):
                    trial[lj] = trial[lj] + off
                a2 = trial[L[t]]
                ar = 0.5 * ((a2[1, 0] - a2[0, 0]) * (a2[2, 1] - a2[0, 1]) - (a2[2, 0] - a2[0, 0]) * (a2[1, 1] - a2[0, 1]))
                if ar * s < 0:
                    for lj in key.get(k, [li]):
                        trial[lj] = uv[lj] - off
                uv[:] = trial
        key = {}
        for i in range(len(lv)):
            key.setdefault((lv[i], round(uv[i, 0], 9), round(uv[i, 1], 9)), []).append(i)
    uv = np.clip(uv, 0.0, 1.0)
    lay.data.foreach_set("uv", uv.ravel())
    A = areas()
    return {"collapsed_before": before, "collapsed_after": int((np.abs(A) < limit).sum()), "delta_uv": delta}


# ====================================================================== pose / keys
def rot_y(deg: float) -> np.ndarray:
    a = math.radians(deg)
    M = np.eye(4)
    M[0, 0], M[0, 2], M[2, 0], M[2, 2] = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    return M


def trans(x=0.0, y=0.0, z=0.0) -> np.ndarray:
    M = np.eye(4)
    M[:3, 3] = (x, y, z)
    return M


def key_action(arm, name: str, frames: Sequence[Tuple[int, Dict[str, np.ndarray]]]):
    """One action keyed on every listed frame for every bone (location + quaternion, LINEAR). frames:
    (frame, {bone: 4x4 BASIS in mm}) - with identity rest rotations the basis is the bone's motion about its own head
    in weapon axes; bones not listed are at rest."""
    import bpy
    from mathutils import Matrix
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    prev = {}
    for f, basis in frames:
        for pb in arm.pose.bones:
            B = np.array(basis.get(pb.name, np.eye(4)), float).copy()
            B[:3, 3] *= MM
            pb.matrix_basis = Matrix(B.tolist())
        bpy.context.view_layer.update()
        for pb in arm.pose.bones:
            q = pb.rotation_quaternion.copy()
            if pb.name in prev and prev[pb.name].dot(q) < 0:
                q.negate()
                pb.rotation_quaternion = q
            prev[pb.name] = q.copy()
            pb.keyframe_insert("location", frame=f, group=pb.name)
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    from pipeline.skeletal_prop import action_fcurves
    for fc in action_fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    act.frame_range = (frames[0][0], frames[-1][0])
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    return act


def bone_matrices_mm(arm, basis: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """Armature-space vertex transform (mm) of every bone for a basis dict (parents composed): v' = M v."""
    rest = {b.name: np.array(b.matrix_local) for b in arm.data.bones}
    for k in rest:
        rest[k][:3, 3] *= 1000.0
    out = {}
    for b in arm.data.bones:          # parents come first in Blender's list order for a freshly built armature
        R = rest[b.name]
        B = np.array(basis.get(b.name, np.eye(4)), float)
        local = R @ B @ np.linalg.inv(R)
        out[b.name] = (out[b.parent.name] @ local) if b.parent else local
    return out


# ====================================================================== checks
def rigid_skin_checks(obj, arm) -> List[dict]:
    """Exactly one influence per vertex, weight exactly 1.0, on a deform bone of `arm`."""
    deform = {b.name for b in arm.data.bones if b.use_deform}
    gi = {g.index: g.name for g in obj.vertex_groups}
    counts = np.zeros(len(obj.data.vertices), int)
    bad_w = 0
    foreign = 0
    for v in obj.data.vertices:
        gs = [g for g in v.groups if g.weight > 0.0]
        counts[v.index] = len(gs)
        for g in gs:
            if abs(g.weight - 1.0) > 0.0:
                bad_w += 1
            if gi.get(g.group) not in deform:
                foreign += 1
    per_bone = {}
    for g in obj.vertex_groups:
        per_bone[g.name] = 0
    for v in obj.data.vertices:
        for g in v.groups:
            if g.weight > 0:
                per_bone[gi[g.group]] += 1
    return [
        _check("rigid_one_influence_per_vertex", obj.name, int((counts != 1).sum()) == 0,
               f"{int((counts == 0).sum())} with none, {int((counts > 1).sum())} with more than one, of {len(counts)}"),
        _check("rigid_weight_exactly_1", obj.name, bad_w == 0, f"{bad_w} influences != 1.0"),
        _check("rigid_on_deform_bones", obj.name, foreign == 0, f"{foreign} influences on non-deform groups"),
        _check("rigid_vertices_per_bone", obj.name, True, ", ".join(f"{k} {v}" for k, v in sorted(per_bone.items()))),
    ]


def skeleton_standard_checks(arm, table: Dict[str, Tuple[Optional[str], ...]] = STANDARD_BONES,
                             expect: Optional[Dict[str, Optional[str]]] = None, tol=1e-6) -> List[dict]:
    names = [b.name for b in arm.data.bones]
    out = []
    M = np.array(arm.matrix_world)
    out.append(_check("root_object_identity", arm.name, arm.name == "root" and np.abs(M - np.eye(4)).max() < tol,
                      f"object {arm.name!r}, |M - I| {np.abs(M - np.eye(4)).max():.2e}"))
    unknown = [n for n in names if n not in table]
    out.append(_check("bone_names_from_standard", arm.name, not unknown, ", ".join(unknown) or f"{len(names)} bones"))
    badpar = [f"{b.name}<-{b.parent.name if b.parent else None}" for b in arm.data.bones
              if b.name in table and (b.parent.name if b.parent else None) not in table[b.name]]
    out.append(_check("parents_from_standard", arm.name, not badpar, ", ".join(badpar) or "all"))
    if expect is not None:
        miss = sorted(set(expect) - set(names))
        extra = sorted(set(names) - set(expect))
        out.append(_check("bones_as_spec", arm.name, not miss and not extra, f"missing {miss}, extra {extra}"))
    out.append(_check("every_bone_deforms", arm.name, all(b.use_deform for b in arm.data.bones),
                      ", ".join(b.name for b in arm.data.bones if not b.use_deform) or "all"))
    worst = max(float(np.abs(np.array(b.matrix_local)[:3, :3] - np.eye(3)).max()) for b in arm.data.bones)
    out.append(_check("rest_rotation_equals_root", arm.name, worst < tol, f"max |R - I| {worst:.2e}"))
    return out


# ====================================================================== FBX read-back (fresh process)
def fbx_skeleton(path: str) -> dict:
    """Import an FBX into the CURRENT (fresh) scene and report its armature: bones, parents, rest heads (mm, after
    the importer's object transform), the armature object's scale, and vertex-group sizes per mesh."""
    import bpy
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(path), use_custom_normals=True, ignore_leaf_bones=False,
                             automatic_bone_orientation=False)
    new = [o for o in bpy.data.objects if o not in before]
    arms = [o for o in new if o.type == "ARMATURE"]
    meshes = [o for o in new if o.type == "MESH"]
    rep = {"objects": [o.name for o in new], "armatures": [a.name for a in arms], "meshes": {}}
    if arms:
        a = arms[0]
        Mw = np.array(a.matrix_world)
        rep["armature_scale"] = [round(float(v), 6) for v in a.matrix_world.to_scale()]
        rep["bones"] = {}
        for b in a.data.bones:
            h = Mw @ np.r_[np.array(b.head_local), 1.0]
            R = (Mw[:3, :3] / np.linalg.norm(Mw[:3, 0])) @ np.array(b.matrix_local)[:3, :3]
            rep["bones"][b.name] = {"parent": b.parent.name if b.parent else None,
                                    "head_mm": [round(float(v) * 1000.0, 4) for v in h[:3]],
                                    "rest_rot_dev": round(float(np.abs(R - np.eye(3)).max()), 6)}
    for m in meshes:
        gi = {g.index: g.name for g in m.vertex_groups}
        cnt = {g.name: 0 for g in m.vertex_groups}
        for v in m.data.vertices:
            for g in v.groups:
                if g.weight > 0:
                    cnt[gi[g.group]] += 1
        tris = sum(len(p.vertices) - 2 for p in m.data.polygons)
        rep["meshes"][m.name] = {"triangles": tris, "vertex_groups": cnt,
                                 "materials": [s.material.name if s.material else None for s in m.material_slots]}
    rep["_new_objects"] = new
    return rep
