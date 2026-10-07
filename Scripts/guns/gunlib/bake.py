"""Cycles bakes of a gun's LOD0 parts into its texture sets (import inside Blender).

Every texel of a set gets the surface it belongs to as raw data, so the painter (gunlib.paint, numpy) can paint
per texel from 3D (GUN_BUILDING_STUDY 4.5):
  pos    world position (frame B, metres, stored + 1.0 so the emission stays positive)
  nrm    world shading normal (custom split normals included) as n * 0.5 + 0.5
  ids    face attributes: R part index, G texel class code, B island id (exact small integers in float)
  edge   R: 1 - N_bevel(0.6 mm) . N, G: 1 - N_bevel(2.0 mm) . N (both convex and concave edges), B: pointiness
  ao     Cycles AO (the assembled LOD0 at rest; every other part occludes)
  nmap   (selected-to-active) tangent-space normal of a high-detail bake source onto its low part, + a hit mask
Bakes run one pass at a time into float images (margin EXTEND fills the gutters with the border values) and are saved
as .npy (rows bottom-up, Blender's pixel order).
"""
from __future__ import annotations

import time
from pathlib import Path

import bpy
import numpy as np


def setup_cycles(samples=64):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    dev = "CPU"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                pr.compute_device_type = kind
                pr.get_devices()
                ok = [d for d in pr.devices if d.type == kind]
                if ok:
                    for d in pr.devices:
                        d.use = d.type == kind
                    sc.cycles.device = "GPU"
                    dev = kind
                    break
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    try:
        sc.cycles.use_adaptive_sampling = False
    except Exception:  # noqa: BLE001
        pass
    return dev


def set_face_attr(ob, name, values):
    me = ob.data
    a = me.attributes.get(name)
    if a is not None:
        me.attributes.remove(a)
    a = me.attributes.new(name, "FLOAT", "FACE")
    a.data.foreach_set("value", np.asarray(values, np.float32))


def bake_material(name, image):
    """A material with every bake source wired to named nodes; `route(mat, source)` picks what the Emission shows."""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.name = "EM"
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    geo.name = "GEO"
    # position + 1
    add = nt.nodes.new("ShaderNodeVectorMath")
    add.operation = "ADD"
    add.inputs[1].default_value = (1.0, 1.0, 1.0)
    add.name = "POS"
    nt.links.new(geo.outputs["Position"], add.inputs[0])
    # normal * 0.5 + 0.5
    mad = nt.nodes.new("ShaderNodeVectorMath")
    mad.operation = "MULTIPLY_ADD"
    mad.inputs[1].default_value = (0.5, 0.5, 0.5)
    mad.inputs[2].default_value = (0.5, 0.5, 0.5)
    mad.name = "NRM"
    nt.links.new(geo.outputs["Normal"], mad.inputs[0])
    # ids
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    comb.name = "IDS"
    for k, nm in enumerate(("pid", "cls", "isl")):
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_type = "GEOMETRY"
        at.attribute_name = nm
        nt.links.new(at.outputs["Fac"], comb.inputs[k])
    # edges: 1 - N_bevel . N at two radii, pointiness
    ecomb = nt.nodes.new("ShaderNodeCombineXYZ")
    ecomb.name = "EDGE"
    for k, r in enumerate((0.0006, 0.002)):
        bv = nt.nodes.new("ShaderNodeBevel")
        bv.samples = 16
        bv.inputs["Radius"].default_value = r
        dot = nt.nodes.new("ShaderNodeVectorMath")
        dot.operation = "DOT_PRODUCT"
        nt.links.new(bv.outputs["Normal"], dot.inputs[0])
        nt.links.new(geo.outputs["Normal"], dot.inputs[1])
        sub = nt.nodes.new("ShaderNodeMath")
        sub.operation = "SUBTRACT"
        sub.inputs[0].default_value = 1.0
        nt.links.new(dot.outputs["Value"], sub.inputs[1])
        nt.links.new(sub.outputs["Value"], ecomb.inputs[k])
    nt.links.new(geo.outputs["Pointiness"], ecomb.inputs[2])
    white = nt.nodes.new("ShaderNodeRGB")
    white.name = "WHITE"
    white.outputs[0].default_value = (1.0, 1.0, 1.0, 1.0)
    img = nt.nodes.new("ShaderNodeTexImage")
    img.name = "TARGET"
    img.image = image
    nt.nodes.active = img
    return m


def route(mat, source):
    nt = mat.node_tree
    em = nt.nodes["EM"]
    for l in list(em.inputs["Color"].links):
        nt.links.remove(l)
    src = {"pos": nt.nodes["POS"].outputs[0], "nrm": nt.nodes["NRM"].outputs[0], "ids": nt.nodes["IDS"].outputs[0],
           "edge": nt.nodes["EDGE"].outputs[0], "white": nt.nodes["WHITE"].outputs[0]}[source]
    nt.links.new(src, em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    nt.nodes.active = nt.nodes["TARGET"]


def new_image(name, size):
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    return bpy.data.images.new(name, size, size, alpha=False, float_buffer=True, is_data=True)


def read_image(img):
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)


def select_only(objs, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or objs[0]


def bake_pass(objs, mats, image, kind, source=None, samples=1, margin=16, **kw):
    """One bake of `objs` (each with its set material in `mats`) into `image`."""
    sc = bpy.context.scene
    sc.cycles.samples = samples
    for m in mats:
        if source is not None:
            route(m, source)
        m.node_tree.nodes["TARGET"].image = image
        m.node_tree.nodes.active = m.node_tree.nodes["TARGET"]
    select_only(objs, kw.pop("active", None))
    t = time.time()
    res = bpy.ops.object.bake(type=kind, margin=margin, margin_type="EXTEND", use_clear=True, **kw)
    if "FINISHED" not in res:
        raise RuntimeError(f"bake {kind}/{source} failed: {res}")
    return time.time() - t


def dump_tris(objs, pids, path, offset_mm):
    """The bake objects' evaluated triangles for the geometric edge masks (gunlib.edgemask): V (n, 3, 3) float32 in
    the paint frame (world metres x 1000 + offset_mm, i.e. frame M mm), pid (n,) = each object's part index (the ids
    bake's R). Plain data, read by the numpy painter."""
    dg = bpy.context.evaluated_depsgraph_get()
    Vs, Ps = [], []
    off = np.asarray(offset_mm, np.float32)
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        M = np.array(o.matrix_world, np.float32)
        co = co @ M[:3, :3].T + M[:3, 3]
        tri = np.empty(len(me.loop_triangles) * 3, np.int32)
        me.loop_triangles.foreach_get("vertices", tri)
        Vs.append(co[tri.reshape(-1, 3)] * 1000.0 + off)
        Ps.append(np.full(len(tri) // 3, pids[o.name], np.int32))
        ev.to_mesh_clear()
    np.savez_compressed(path, V=np.concatenate(Vs).astype(np.float32), pid=np.concatenate(Ps))
