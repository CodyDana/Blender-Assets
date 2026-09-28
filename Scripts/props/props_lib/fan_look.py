#!/usr/bin/env python
"""props_lib.fan_look - SK_Fan's Blender side: armature, skinned meshes, materials from the BAKED maps,
the AO bake, poses and actions, and the reference-view camera (REFERENCE_SPEC 1's fan2 recipe).

bpy.  Units: the scene is metric at scale 1.0 (metres); every number handed in is millimetres.

MATERIALS (the graph an Unreal material instance of the pack's masters reproduces):
    fabric parts (leaf, sticks, tassel)
        BaseColor = saturate(Tint x (DetailBias + DetailScale x Detail))   (Detail sRGB-encoded)
        Specular  = spec_scale x ORM.A     Roughness = ORM.G     Metallic 0     Normal = N (DirectX)
    rivet (M_Steel_Master: not tintable)
        BaseColor = BC     Metallic = ORM.B     Roughness = ORM.G     Normal = N
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

MM = 0.001


# =========================================================================== scene
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    return sc


# =========================================================================== armature
def make_armature(name: str, bones: Sequence[Tuple[str, Sequence[float], Sequence[float], str, Sequence[float]]]):
    """bones: (name, head_mm, tail_mm, parent ('' = none), up vector for the roll)."""
    arm = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, arm)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.view_layer.objects:
        o.select_set(o == obj)
    bpy.ops.object.mode_set(mode="EDIT")
    made = {}
    for bname, head, tail, parent, up in bones:
        eb = arm.edit_bones.new(bname)
        eb.head = Vector(head) * MM
        eb.tail = Vector(tail) * MM
        eb.align_roll(Vector(up))
        eb.use_deform = True
        eb.use_connect = False
        made[bname] = eb
    for bname, head, tail, parent, up in bones:
        if parent:
            made[bname].parent = made[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in obj.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return obj


def rest_matrices(arm_obj) -> Dict[str, np.ndarray]:
    return {b.name: np.array(b.matrix_local) for b in arm_obj.data.bones}


def _to_m(T: np.ndarray) -> np.ndarray:
    M = np.array(T, np.float64).copy()
    M[:3, 3] *= MM
    return M


def pose(arm_obj, T_by_bone: Dict[str, np.ndarray], rest: Optional[Dict[str, np.ndarray]] = None):
    """Pose every bone so its vertices go from bind to T (mm, bind -> posed, armature space)."""
    rest = rest or rest_matrices(arm_obj)
    for pb in arm_obj.pose.bones:
        T = T_by_bone.get(pb.name)
        if T is None:
            pb.matrix_basis = Matrix.Identity(4)
            continue
        R = rest[pb.name]
        par = pb.parent
        if par is not None:
            # chains (the tassel): basis relative to the parent's pose
            Rp = rest[par.name]
            Tp = _to_m(T_by_bone.get(par.name, np.eye(4)))
            B = np.linalg.inv(np.linalg.inv(Rp) @ R) @ np.linalg.inv(Tp @ Rp) @ _to_m(T) @ R
        else:
            B = np.linalg.inv(R) @ _to_m(T) @ R
        pb.matrix_basis = Matrix(B.tolist())
    bpy.context.view_layer.update()


def key_action(arm_obj, name: str, frames: Sequence[Tuple[int, Dict[str, np.ndarray]]], fps: int = 30):
    """One action, every bone keyed on every given frame (location + quaternion, hemisphere-continuous)."""
    rest = rest_matrices(arm_obj)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    arm_obj.animation_data.action = act
    prev = {}
    for f, Tb in frames:
        pose(arm_obj, Tb, rest)
        for pb in arm_obj.pose.bones:
            q = pb.rotation_quaternion.copy()
            if pb.name in prev and prev[pb.name].dot(q) < 0:
                q.negate()
                pb.rotation_quaternion = q
            prev[pb.name] = q.copy()
            pb.keyframe_insert("location", frame=f, group=pb.name)
            pb.keyframe_insert("rotation_quaternion", frame=f, group=pb.name)
    _linear(act)
    act.frame_range = (frames[0][0], frames[-1][0])
    return act


def _linear(act):
    """Keys are every frame; LINEAR so Blender's own playback between keys matches a plain resample."""
    def fcurves(a):
        try:
            return list(a.fcurves)
        except AttributeError:
            out = []
            for layer in a.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        out.extend(bag.fcurves)
            return out
    for fc in fcurves(act):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


# =========================================================================== meshes
def mesh_object(mb, name: str, materials: Sequence, arm_obj=None, weights=None):
    """FanMesh -> a skinned Blender mesh (metres), UV0, custom split normals, one vertex group per bone."""
    P = np.asarray(mb.P, np.float64) * MM
    T = np.asarray(mb.T, np.int64)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in P], [], [tuple(t) for t in T])
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    uv = np.concatenate([np.asarray(u, np.float64) for u in mb.TUV]).ravel()
    uvl.data.foreach_set("uv", uv)
    me.polygons.foreach_set("material_index", list(mb.TS))
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    for m in materials:
        me.materials.append(m)
    nl = np.concatenate([np.asarray(n, np.float64) for n in mb.TN])
    nl /= np.maximum(np.linalg.norm(nl, axis=1, keepdims=True), 1e-12)
    me.normals_split_custom_set([tuple(n) for n in nl])
    me.validate(verbose=False)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if arm_obj is not None:
        groups = {}
        if weights is None:
            B = np.asarray(mb.B)
            for bi, bname in enumerate(mb.bone_names):
                idx = np.nonzero(B == bi)[0]
                if len(idx):
                    vg = ob.vertex_groups.new(name=bname)
                    vg.add([int(i) for i in idx], 1.0, "REPLACE")
        else:
            for vi, wl in enumerate(weights):
                for bname, w in wl:
                    vg = groups.get(bname) or ob.vertex_groups.get(bname) or ob.vertex_groups.new(name=bname)
                    groups[bname] = vg
                    vg.add([vi], float(w), "REPLACE")
        ob.parent = arm_obj
        mod = ob.modifiers.new("Armature", "ARMATURE")
        mod.object = arm_obj
        mod.use_vertex_groups = True
    return ob


def evaluated_positions(obj) -> np.ndarray:
    """World-space vertex positions of the evaluated (skinned) mesh, mm."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    try:
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        M = np.array(obj.matrix_world)
        co = co @ M[:3, :3].T + M[:3, 3]
        return co / MM
    finally:
        ev.to_mesh_clear()


# =========================================================================== materials
def _tex(nt, uvn, path, cs, pack):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = cs
    im.name = Path(path).stem
    if pack:
        im.pack()
    tn = nt.nodes.new("ShaderNodeTexImage")
    tn.image = im
    tn.interpolation = "Linear"
    tn.extension = "REPEAT"
    nt.links.new(uvn.outputs[0], tn.inputs[0])
    return tn


def make_material(name: str, paths: Dict[str, str], tint_linear=None, detail_bias: float = 0.0,
                  detail_scale: float = 1.0, spec_scale: float = 0.5, metal: bool = False, pack: bool = True):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    orm = _tex(nt, uvn, paths["ORM"], "Non-Color", pack)
    orm.image.alpha_mode = "CHANNEL_PACKED"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(orm.outputs["Color"], sep.inputs[0])
    nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
    if metal:
        bc = _tex(nt, uvn, paths["BC"], "sRGB", pack)
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
    else:
        det = _tex(nt, uvn, paths["Detail"], "sRGB", pack)
        ma = nt.nodes.new("ShaderNodeMath")
        ma.operation = "MULTIPLY_ADD"
        nt.links.new(det.outputs["Color"], ma.inputs[0])
        ma.inputs[1].default_value = float(detail_scale)
        ma.inputs[2].default_value = float(detail_bias)
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type = "RGBA"
        mul.blend_type = "MULTIPLY"
        mul.inputs["Factor"].default_value = 1.0
        mul.clamp_result = True
        nt.links.new(ma.outputs[0], mul.inputs["A"])
        mul.inputs["B"].default_value = (tint_linear[0], tint_linear[1], tint_linear[2], 1.0)
        nt.links.new(mul.outputs["Result"], bsdf.inputs["Base Color"])
        bsdf.inputs["Metallic"].default_value = 0.0
        ms = nt.nodes.new("ShaderNodeMath")
        ms.operation = "MULTIPLY"
        ms.inputs[1].default_value = float(spec_scale)
        nt.links.new(orm.outputs["Alpha"], ms.inputs[0])
        nt.links.new(ms.outputs[0], bsdf.inputs["Specular IOR Level"])
    nrm = _tex(nt, uvn, paths["N"], "Non-Color", pack)
    sepn = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(nrm.outputs["Color"], sepn.inputs[0])
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(sepn.outputs[1], inv.inputs[1])
    comb = nt.nodes.new("ShaderNodeCombineColor")
    nt.links.new(sepn.outputs[0], comb.inputs[0])
    nt.links.new(inv.outputs[0], comb.inputs[1])
    nt.links.new(sepn.outputs[2], comb.inputs[2])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.space = "TANGENT"
    nmap.uv_map = "UVMap"
    nt.links.new(comb.outputs[0], nmap.inputs["Color"])
    nt.links.new(nmap.outputs[0], bsdf.inputs["Normal"])
    bsdf.inputs["IOR"].default_value = 1.5
    for nm, v in (("Sheen Weight", 0.0), ("Coat Weight", 0.0), ("Subsurface Weight", 0.0),
                  ("Diffuse Roughness", 0.0), ("Transmission Weight", 0.0)):
        if nm in bsdf.inputs:
            bsdf.inputs[nm].default_value = v
    if tint_linear is not None:
        mat["tint_linear"] = [float(x) for x in tint_linear]
    mat["detail_bias"] = float(detail_bias)
    mat["detail_scale"] = float(detail_scale)
    mat["spec_scale"] = float(spec_scale)
    return mat


def plain_material(name: str, colour=(0.02, 0.02, 0.02), rough=0.5, metal=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*colour, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return mat


# =========================================================================== AO bake
def _cycles(scene, samples, denoise=False):
    scene.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        scene.cycles.device = "GPU" if any(d.use for d in pr.devices) else "CPU"
    except Exception:
        scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    scene.cycles.use_adaptive_sampling = False
    return scene.cycles.device


def bake_ao(obj, sizes: Dict[int, int], samples: int = 128, distance_m: float = 0.005, margin: int = 16):
    """Cycles AO of ``obj`` into one float image per material slot index (size per slot).  Returns
    {slot: (H, W) array, rows top-down}."""
    scene = bpy.context.scene
    saved = scene.render.engine
    _cycles(scene, samples)
    scene.render.bake.margin = margin
    scene.render.bake.margin_type = "EXTEND"
    try:
        scene.world.light_settings.distance = distance_m
    except Exception:
        pass
    imgs = {}
    for slot, mat in enumerate(obj.data.materials):
        if slot not in sizes:
            continue
        im = bpy.data.images.new(f"__ao_{slot}", sizes[slot], sizes[slot], float_buffer=True, alpha=False)
        nt = mat.node_tree
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = im
        n.name = "__AO_TARGET"
        nt.nodes.active = n
        imgs[slot] = (im, n, mat)
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(o == obj)
    bpy.context.view_layer.objects.active = obj
    if obj not in bpy.context.selected_objects:
        raise RuntimeError(f"could not select {obj.name} for the AO bake")
    bpy.ops.object.bake(type="AO", use_clear=True, margin=margin)
    out = {}
    for slot, (im, n, mat) in imgs.items():
        w, h = im.size
        buf = np.empty(w * h * 4, np.float32)
        im.pixels.foreach_get(buf)
        out[slot] = np.ascontiguousarray(buf.reshape(h, w, 4)[::-1, :, 0]).astype(np.float64)
        mat.node_tree.nodes.remove(n)
        bpy.data.images.remove(im)
    scene.render.engine = saved
    return out


# =========================================================================== PNG io (no colour chunks)
def write_png(path, arr, bits: int = 8) -> str:
    import struct
    import zlib
    a = np.asarray(arr)
    if bits == 16:
        a16 = a.astype(np.uint16)
        if a16.ndim == 2:
            a16 = a16[:, :, None]
        h, w, c = a16.shape
        raw = b"".join(b"\x00" + a16[y].astype(">u2").tobytes() for y in range(h))
        ctype = {1: 0, 3: 2, 4: 6}[c]
        depth = 16
    else:
        if a.dtype != np.uint8:
            a = np.rint(np.clip(a.astype(np.float64), 0, 1) * 255).astype(np.uint8)
        if a.ndim == 2:
            a = a[:, :, None]
        h, w, c = a.shape
        raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))
        ctype = {1: 0, 3: 2, 4: 6}[c]
        depth = 8

    def chunk(tag, payload):
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    ihdr = struct.pack(">IIBBBBB", w, h, depth, ctype, 0, 0, 0)
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 6))
                           + chunk(b"IEND", b""))
    return str(path)


def load_png(path) -> np.ndarray:
    img = bpy.data.images.load(str(path), check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(h, w, 4)[::-1])
    finally:
        bpy.data.images.remove(img)


def png_chunks(path) -> List[str]:
    b = Path(path).read_bytes()
    i, out = 8, []
    while i < len(b):
        n = int.from_bytes(b[i:i + 4], "big")
        out.append(b[i + 4:i + 8].decode("latin1"))
        i += 12 + n
    return out


# =========================================================================== render helpers
def render_exr(exr_path) -> np.ndarray:
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"
    scene.render.filepath = str(exr_path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(exr_path), check_existing=False)
    try:
        w, h = img.size
        buf = np.empty(w * h * 4, np.float32)
        img.pixels.foreach_get(buf)
        return np.ascontiguousarray(buf.reshape(h, w, 4)[::-1]).astype(np.float64)
    finally:
        bpy.data.images.remove(img)


def srgb_encode(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def srgb_decode(x):
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def composite_over(a, backdrop_stored: float) -> np.ndarray:
    bg = srgb_decode(np.array(backdrop_stored))
    lin = a[..., :3] + (1.0 - a[..., 3:4]) * bg
    return srgb_encode(lin)


def hide_all_but(keep):
    keep = set(keep)
    saved = [(o, o.hide_render) for o in bpy.data.objects]
    for o in bpy.data.objects:
        if o.type in {"MESH", "CURVE", "FONT"}:
            o.hide_render = o not in keep
    return saved


def restore(saved):
    for o, was in saved:
        try:
            o.hide_render = was
        except ReferenceError:
            pass


def side_by_side(ref_png, render_png, out_png, gap: int = 12):
    ref = load_png(ref_png)[..., :3]
    ren = load_png(render_png)[..., :3]
    h = max(ref.shape[0], ren.shape[0])
    sheet = np.ones((h, ref.shape[1] + gap + ren.shape[1], 3))
    sheet[:ref.shape[0], :ref.shape[1]] = ref
    sheet[:ren.shape[0], ref.shape[1] + gap:] = ren
    write_png(out_png, sheet)
    return str(out_png)


def crops_sheet(ref_png, render_png, out_png, boxes, scale: int = 3, gap: int = 8):
    ref = load_png(ref_png)[..., :3]
    ren = load_png(render_png)[..., :3]
    rows = []
    for (x0, y0, x1, y1) in boxes:
        a = np.repeat(np.repeat(ref[y0:y1, x0:x1], scale, 0), scale, 1)
        b = np.repeat(np.repeat(ren[y0:y1, x0:x1], scale, 0), scale, 1)
        row = np.ones((a.shape[0], a.shape[1] * 2 + gap, 3))
        row[:, :a.shape[1]] = a
        row[:, a.shape[1] + gap:] = b
        rows.append(row)
    w = max(r.shape[1] for r in rows)
    out = []
    for r in rows:
        pad = np.ones((r.shape[0], w, 3))
        pad[:, :r.shape[1]] = r
        out += [pad, np.ones((gap, w, 3))]
    write_png(out_png, np.concatenate(out[:-1], 0))
    return str(out_png)


__all__ = ["reset_scene", "make_armature", "rest_matrices", "pose", "key_action", "mesh_object", "evaluated_positions",
           "make_material", "plain_material", "bake_ao", "write_png", "load_png", "png_chunks", "render_exr",
           "composite_over", "hide_all_but", "restore", "side_by_side", "crops_sheet", "srgb_encode", "srgb_decode",
           "MM"]
