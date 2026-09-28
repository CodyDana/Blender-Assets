"""Skeletal PROPS (a rigged prop such as the folding fan): QA gates, the multi-file export and the sidecar.

NEW module (2026-09-26, SK_Fan).  The static pipeline - ``export_fbx``, ``qa_check``, ``helpers`` - is used exactly
as it is and is not changed: this module only calls ``export_fbx(kind="skeletal")`` and
``export_fbx(kind="animation")`` and adds what a skeletal prop needs on top.

Why not ``qa_check``'s skeletal item: it requires ONE top-level bone.  A prop rigged the way the project measured
for Unreal (ASSET_GUIDELINES 12.10: the armature OBJECT is named ``root`` so Unreal's root bone is that node and no
extra bone appears above it) has its moving bones as top-level bones under that object.  ``qa_skeletal`` checks
that convention instead, plus the geometry gates a deforming prop needs:

    skeleton    armature object named ``root``, identity transform, no bone also called ``root``, no "." in names,
                every bone deforms (``export_fbx`` writes deform bones only), bone count within a budget
    skin        every mesh parented to the armature with an Armature modifier; every vertex weighted; weights
                sum to 1; at most ``max_influences``; every vertex group is a deform bone
    geometry    triangles only, no stray (unused) vertices, no zero-area faces, no zero-length edges, every edge
                used by at most two faces (edge-manifold) with consistent winding; the ``closed_groups`` named by
                the caller (each a set of faces that must be a closed solid) have no boundary edges
    uv          UV0 present, finite, inside 0..1, no collapsed triangles
    materials   at most ``max_slots`` slots, every material named M_* / MI_*

``export_skeletal_set`` writes the mesh FBX (per LOD) and one FBX per action (Unreal imports one animation per
file) and returns what it wrote.  ``write_skeletal_sidecar`` writes ``<name>.skeletal.json``: sockets on bones,
physics-asset bodies, LOD files and screen sizes, animations and materials, all in Blender armature space (mm and
a 3x3) AND in Unreal component space (cm, left-handed: y flipped), for the Unreal-side import script.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import bpy
import numpy as np

from pipeline.export_fbx import export_fbx

UE_ROOT_OBJECT = "root"
MAX_INFLUENCES = 4
WEIGHT_TOLERANCE = 1e-5
MIN_AREA_M2 = 1e-12          # 1e-6 mm^2
MIN_EDGE_M = 1e-7            # 0.1 um
VERSION = "1.0.0"


def _check(name: str, obj: Optional[str], passed: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "object": obj, "passed": bool(passed), "detail": detail}


def _identity(obj, tol=1e-6) -> bool:
    M = np.array(obj.matrix_world)
    return bool(np.abs(M - np.eye(4)).max() < tol)


def skeleton_checks(arm, bone_budget: Optional[int] = None) -> List[Dict[str, Any]]:
    bones = arm.data.bones
    names = [b.name for b in bones]
    out = [
        _check("armature_object_named_root", arm.name, arm.name == UE_ROOT_OBJECT,
               f"object {arm.name!r} (Unreal's root bone is this node; any other name adds a bone above it)"),
        _check("armature_identity_transform", arm.name, _identity(arm), "matrix_world == identity"),
        _check("no_bone_named_root", arm.name, UE_ROOT_OBJECT not in names, "the object is the root"),
        _check("bone_names_without_dots", arm.name, not any("." in n for n in names),
               ", ".join(n for n in names if "." in n)[:200] or "clean"),
        _check("every_bone_deforms", arm.name, all(b.use_deform for b in bones),
               ", ".join(b.name for b in bones if not b.use_deform)[:200] or f"{len(bones)} deform bones"),
    ]
    if bone_budget is not None:
        out.append(_check("bone_budget", arm.name, len(bones) + 1 <= bone_budget,
                          f"{len(bones)} bones + the root node = {len(bones) + 1} (budget {bone_budget})"))
    return out


def _mesh_arrays(obj):
    me = obj.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    polys = [tuple(p.vertices) for p in me.polygons]
    return co, polys


def geometry_checks(obj, closed_groups: Optional[Dict[str, Sequence[int]]] = None) -> List[Dict[str, Any]]:
    co, polys = _mesh_arrays(obj)
    out = []
    ngons = sum(1 for p in polys if len(p) != 3)
    out.append(_check("triangles_only", obj.name, ngons == 0, f"{ngons} non-triangles of {len(polys)}"))
    used = np.zeros(len(co), bool)
    for p in polys:
        used[list(p)] = True
    out.append(_check("no_stray_vertices", obj.name, bool(used.all()), f"{int((~used).sum())} unused of {len(co)}"))
    tri = np.array([p for p in polys if len(p) == 3])
    if len(tri):
        a, b, c = co[tri[:, 0]], co[tri[:, 1]], co[tri[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        e = np.concatenate([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)])
        out.append(_check("no_zero_area_faces", obj.name, bool(area.min() > MIN_AREA_M2),
                          f"min area {area.min() * 1e6:.6f} mm^2 (limit {MIN_AREA_M2 * 1e6:g})"))
        out.append(_check("no_zero_length_edges", obj.name, bool(e.min() > MIN_EDGE_M),
                          f"min edge {e.min() * 1e3:.5f} mm"))
    # edge use and winding
    edge_faces: Dict[tuple, List[tuple]] = {}
    for fi, p in enumerate(polys):
        n = len(p)
        for k in range(n):
            u, v = p[k], p[(k + 1) % n]
            edge_faces.setdefault((min(u, v), max(u, v)), []).append((fi, u, v))
    over = sum(1 for f in edge_faces.values() if len(f) > 2)
    flipped = sum(1 for f in edge_faces.values() if len(f) == 2 and f[0][1] == f[1][1])
    boundary = sum(1 for f in edge_faces.values() if len(f) == 1)
    out.append(_check("edge_manifold", obj.name, over == 0, f"{over} edges used by more than two faces"))
    out.append(_check("consistent_winding", obj.name, flipped == 0, f"{flipped} edges walked the same way twice"))
    out.append(_check("boundary_edges_reported", obj.name, True,
                      f"{boundary} boundary edges (open sheets such as the leaf layers are expected)"))
    for gname, faces in (closed_groups or {}).items():
        fs = set(int(f) for f in faces)
        cnt: Dict[tuple, int] = {}
        for fi in fs:
            p = polys[fi]
            n = len(p)
            for k in range(n):
                u, v = p[k], p[(k + 1) % n]
                key = (min(u, v), max(u, v))
                cnt[key] = cnt.get(key, 0) + 1
        open_edges = sum(1 for v in cnt.values() if v != 2)
        out.append(_check(f"closed_solid:{gname}", obj.name, open_edges == 0,
                          f"{len(fs)} faces, {open_edges} edges not shared by exactly two of them"))
    return out


def skin_checks(obj, arm, max_influences: int = MAX_INFLUENCES) -> List[Dict[str, Any]]:
    out = []
    bound = obj.parent == arm and any(m.type == "ARMATURE" and m.object == arm for m in obj.modifiers)
    out.append(_check("parented_with_armature_modifier", obj.name, bound, f"parent {obj.parent.name if obj.parent else None}"))
    deform = {b.name for b in arm.data.bones if b.use_deform}
    foreign = [g.name for g in obj.vertex_groups if g.name not in deform]
    out.append(_check("vertex_groups_are_deform_bones", obj.name, not foreign, ", ".join(foreign)[:200] or "all"))
    worst, unweighted, err = 0, 0, 0.0
    gi = {g.index: g.name in deform for g in obj.vertex_groups}
    for v in obj.data.vertices:
        w = [g.weight for g in v.groups if gi.get(g.group) and g.weight > 0]
        worst = max(worst, len(w))
        s = sum(w)
        if s <= 0:
            unweighted += 1
        else:
            err = max(err, abs(s - 1.0))
    out += [_check("max_influences", obj.name, worst <= max_influences, f"max {worst} (limit {max_influences})"),
            _check("no_unweighted_vertices", obj.name, unweighted == 0, f"{unweighted} of {len(obj.data.vertices)}"),
            _check("weights_normalised", obj.name, err < WEIGHT_TOLERANCE, f"max |sum-1| {err:.2e}")]
    out.append(_check("mesh_identity_transform", obj.name, _identity(obj), "matrix_world == identity"))
    return out


def uv_material_checks(obj, max_slots: int = 4) -> List[Dict[str, Any]]:
    me = obj.data
    out = []
    if not me.uv_layers:
        return [_check("uv0_present", obj.name, False, "no UV layer")]
    uv = np.empty(len(me.loops) * 2)
    me.uv_layers[0].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    fin = bool(np.isfinite(uv).all())
    inside = bool((uv >= -1e-6).all() and (uv <= 1 + 1e-6).all())
    out.append(_check("uv0_present_finite", obj.name, fin, f"{len(uv)} loops"))
    out.append(_check("uv0_inside_0_1", obj.name, inside, f"range {uv.min(0).round(4).tolist()} .. {uv.max(0).round(4).tolist()}"))
    collapsed = 0
    for p in me.polygons:
        if p.loop_total != 3:
            continue
        a, b, c = (uv[p.loop_start + k] for k in range(3))
        if abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) < 1e-14:
            collapsed += 1
    out.append(_check("no_collapsed_uv_triangles", obj.name, collapsed == 0, f"{collapsed}"))
    mats = [m.name if m else None for m in me.materials]
    out.append(_check("material_slots", obj.name, 0 < len(mats) <= max_slots and all(
        m and (m.startswith("M_") or m.startswith("MI_")) for m in mats), ", ".join(str(m) for m in mats)))
    return out


def qa_skeletal(meshes: Iterable, armature, max_influences: int = MAX_INFLUENCES, bone_budget: Optional[int] = None,
                closed_groups: Optional[Dict[str, Dict[str, Sequence[int]]]] = None, max_slots: int = 4) -> Dict[str, Any]:
    """All gates above; returns {"passed", "checks", "objects"}.  ``closed_groups``: {mesh name: {group: faces}}."""
    checks = skeleton_checks(armature, bone_budget)
    names = []
    for obj in meshes:
        names.append(obj.name)
        checks += skin_checks(obj, armature, max_influences)
        checks += geometry_checks(obj, (closed_groups or {}).get(obj.name))
        checks += uv_material_checks(obj, max_slots)
    return {"passed": all(c["passed"] for c in checks), "checks": checks, "objects": names, "version": VERSION}


# =========================================================================== export
#: MEASURED on UE 5.8.3 (2026-09-26, SK_Fan).  Blender's FBX exporter never scales BONE translations: with every
#: apply_scale_options value (UNITS - the house static setting -, NONE, ALL, CUSTOM) the bones are written in
#: metres and the metre->cm factor lands either on the root node (Lcl Scaling 100) or in the file's
#: UnitScaleFactor, and Unreal's Convert Scene Unit then puts it on the root bone: root at scale 100, every
#: translation in metres.  It renders right, but sockets, physics bodies and anything attached to a bone inherit
#: the 100x.  So a skeletal prop is exported from a CENTIMETRE COPY: armature, meshes and the actions' location
#: keys scaled x100 in a throwaway copy that carries the original names, written with "FBX All" at global scale
#: 0.01 (the exporter folds scale x unit into the file's UnitScaleFactor only: 0.01 x 100 = 1, no node scale; the
#: file says 1 unit = 1 cm).  Unreal then gets a root at scale 1 and translations in cm; Blender's importer reads
#: the same file back at the right size (it applies 0.01 on the imported armature object).
SKELETAL_FBX_OVERRIDES = {"apply_unit_scale": True, "global_scale": 0.01, "apply_scale_options": "FBX_SCALE_ALL"}
CM_PER_BU = 100.0


def action_fcurves(act) -> List[Any]:
    """F-curves of a legacy or a layered (Blender 4.4+) action."""
    try:
        return list(act.fcurves)
    except AttributeError:
        out = []
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out


class _CentimetreCopy:
    """Context manager: throwaway x100 copies of the armature, its meshes and actions under the ORIGINAL names
    (the originals are renamed aside and restored, untouched, on exit)."""
    SUFFIX = "__metre_src"

    def __init__(self, armature, meshes, actions):
        self.arm, self.meshes, self.actions = armature, list(meshes), list(actions)

    def __enter__(self):
        import mathutils
        S = mathutils.Matrix.Scale(CM_PER_BU, 4)
        scene = bpy.context.scene
        self.names = {}
        for ob in [self.arm] + self.meshes:
            self.names[ob] = ob.name
            ob.name = ob.name + self.SUFFIX
        self.act_names = {}
        for act in self.actions:
            self.act_names[act] = act.name
            act.name = act.name + self.SUFFIX
        arm = self.arm.copy()
        arm.data = self.arm.data.copy()
        arm.animation_data_clear()
        arm.name = self.names[self.arm]
        scene.collection.objects.link(arm)
        arm.matrix_world = S @ self.arm.matrix_world
        for ob in bpy.context.view_layer.objects:
            ob.select_set(False)
        arm.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        self.arm_copy = arm
        self.mesh_copies = []
        for src in self.meshes:
            ob = src.copy()
            ob.data = src.data.copy()
            ob.name = self.names[src]
            ob.data.transform(S)
            ob.parent = arm
            ob.matrix_parent_inverse.identity()
            ob.matrix_world = mathutils.Matrix.Identity(4)
            for md in ob.modifiers:
                if md.type == "ARMATURE":
                    md.object = arm
            scene.collection.objects.link(ob)
            self.mesh_copies.append(ob)
        self.action_copies = {}
        for act in self.actions:
            c = act.copy()
            c.name = self.act_names[act]
            for fc in action_fcurves(c):
                if fc.data_path.endswith(".location") or fc.data_path == "location":
                    for kp in fc.keyframe_points:
                        kp.co[1] *= CM_PER_BU
                        kp.handle_left[1] *= CM_PER_BU
                        kp.handle_right[1] *= CM_PER_BU
            self.action_copies[act] = c
        bpy.context.view_layer.update()
        return self

    def __exit__(self, *exc):
        arm_data = self.arm_copy.data
        for ob in self.mesh_copies:
            me = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            bpy.data.meshes.remove(me)
        bpy.data.objects.remove(self.arm_copy, do_unlink=True)
        bpy.data.armatures.remove(arm_data)
        for c in self.action_copies.values():
            bpy.data.actions.remove(c)
        for ob, name in self.names.items():
            ob.name = name
        for act, name in self.act_names.items():
            act.name = name
        return False


def export_skeletal_set(out_dir: str, armature, lod_meshes: Sequence, mesh_name: str,
                        actions: Sequence[Any] = (), frame_rate: int = 30,
                        fps_by_action: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """<mesh_name>.fbx (LOD0 + armature), <mesh_name>_LOD<n>.fbx per further LOD, and A_*.fbx per action,
    all written in centimetres from a throwaway copy (see SKELETAL_FBX_OVERRIDES).

    Unreal imports one animation per FBX, and a skeletal LOD file must carry the same skeleton (same root), so
    every file holds the whole armature.  The armature is left in its rest pose with no action afterwards."""
    out_dir = str(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    scene = bpy.context.scene
    scene.render.fps = frame_rate
    scene.render.fps_base = 1.0
    written: Dict[str, Any] = {"meshes": [], "animations": [], "units": "cm (1 FBX unit = 1 cm, root scale 1)"}
    ad = armature.animation_data
    saved_action = ad.action if ad else None
    if ad:
        ad.action = None
    for pb in armature.pose.bones:
        pb.matrix_basis.identity()
    with _CentimetreCopy(armature, lod_meshes, actions) as cc:
        arm = cc.arm_copy
        for i, mesh in enumerate(cc.mesh_copies):
            path = os.path.join(out_dir, f"{mesh_name}.fbx" if i == 0 else f"{mesh_name}_LOD{i}.fbx")
            res = export_fbx(path, [arm.name, mesh.name], kind="skeletal", **SKELETAL_FBX_OVERRIDES)
            written["meshes"].append({"lod": i, "fbx": path, "objects": res["objects"], "warnings": res["warnings"]})
        for src in actions:
            act = cc.action_copies[src]
            if arm.animation_data is None:
                arm.animation_data_create()
            arm.animation_data.action = act
            f0, f1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
            scene.frame_start, scene.frame_end = f0, f1
            fps = int((fps_by_action or {}).get(act.name, frame_rate))
            scene.render.fps = fps
            path = os.path.join(out_dir, f"{act.name}.fbx")
            res = export_fbx(path, [arm.name], kind="animation", **SKELETAL_FBX_OVERRIDES)
            written["animations"].append({"action": act.name, "fbx": path, "frames": [f0, f1], "fps": fps,
                                          "warnings": res["warnings"]})
            arm.animation_data.action = None
    scene.render.fps = frame_rate
    if armature.animation_data:
        armature.animation_data.action = saved_action
    return written


# =========================================================================== Unreal space
UE_MIRROR = np.diag([1.0, -1.0, 1.0])


def ue_component_transform(matrix_mm_3x3: np.ndarray, location_mm: Sequence[float]) -> Dict[str, Any]:
    """Blender armature space (right-handed, mm) -> Unreal component space (left-handed, cm): y is flipped, the
    rotation is conjugated by the mirror.  Returns location_cm, the rotation matrix (columns = the transformed
    axes) and the quaternion (x, y, z, w)."""
    R = UE_MIRROR @ np.asarray(matrix_mm_3x3, np.float64) @ UE_MIRROR
    loc = np.asarray(location_mm, np.float64) * 0.1
    loc = [float(loc[0]), float(-loc[1]), float(loc[2])]
    # quaternion from R (proper rotation after the double mirror)
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, 0.25 * s]
    else:
        i = int(np.argmax(np.diag(R)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = math.sqrt(1.0 + R[i, i] - R[j, j] - R[k, k]) * 2
        q = [0.0, 0.0, 0.0, 0.0]
        q[i] = 0.25 * s
        q[j] = (R[j, i] + R[i, j]) / s
        q[k] = (R[k, i] + R[i, k]) / s
        q[3] = (R[k, j] - R[j, k]) / s
    return {"location_cm": [round(v, 5) for v in loc], "rotation_matrix": np.round(R, 7).tolist(),
            "quaternion_xyzw": [round(float(v), 7) for v in q]}


def write_skeletal_sidecar(fbx_path: str, payload: Dict[str, Any]) -> str:
    path = str(Path(fbx_path).with_suffix("")) + ".skeletal.json"
    body = {"schema": "ninjapack.skeletal_prop/1", "fbx": os.path.basename(fbx_path), "pipeline_module": VERSION,
            "axes": {"blender": "armature space, mm, right-handed, Z up",
                     "unreal": "component space, cm, left-handed (Blender y flipped), Z up"}}
    body.update(payload)
    Path(path).write_text(json.dumps(body, indent=2), encoding="utf-8")
    return path


__all__ = ["SKELETAL_FBX_OVERRIDES", "CM_PER_BU", "action_fcurves", "qa_skeletal", "skeleton_checks", "geometry_checks", "skin_checks", "uv_material_checks",
           "export_skeletal_set", "write_skeletal_sidecar", "ue_component_transform", "VERSION"]
