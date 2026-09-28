"""b2_rig_jointviz.py - PRIVATE / DO NOT SHIP. Debug render of the fitted posed joints over a see-through body.

  blender -b rig_work/c1_stage1_mesh.blend -P b2_rig_jointviz.py -- <joints.json> <out_prefix> [views...]
Never saves the blend.
"""
import bpy, bmesh, os, sys, json, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import *  # noqa

PARENT = {}


def mh_parents():
    with bpy.data.libraries.load(MH_BLEND, link=False) as (src, dst):
        dst.armatures = ["metahuman_base_skel"]
    arm = dst.armatures[0]
    return {b.name: (b.parent.name if b.parent else None) for b in arm.bones}


def main():
    a = argv()
    data = json.load(open(a[0]))
    prefix = a[1]
    views = a[2:] or ["front", "side"]
    J = {k: Vector(v) for k, v in data["joints"].items()}
    extra = {k: Vector(v) for k, v in data.get("extra", {}).items() if isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v) and not k.startswith("mh_")}
    par = mh_parents()
    sc = bpy.context.scene
    enable_gpu()
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 16
    sc.render.resolution_x, sc.render.resolution_y = 800, 1100
    # see-through skin
    ghost = bpy.data.materials.new("GHOST")
    nt = ghost.node_tree
    b = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.8, 0.75, 0.7, 1); b.inputs["Alpha"].default_value = 0.22
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith("SK_"):
            o.data.materials.clear(); o.data.materials.append(ghost)
    red = bpy.data.materials.new("J"); red.node_tree.nodes.clear()
    em = red.node_tree.nodes.new("ShaderNodeEmission"); out = red.node_tree.nodes.new("ShaderNodeOutputMaterial")
    em.inputs["Color"].default_value = (1, 0.05, 0.02, 1); em.inputs["Strength"].default_value = 3
    red.node_tree.links.new(em.outputs[0], out.inputs[0])
    blu = red.copy(); blu.node_tree.nodes["Emission"].inputs["Color"].default_value = (0.05, 0.3, 1, 1)
    grn = red.copy(); grn.node_tree.nodes["Emission"].inputs["Color"].default_value = (0.1, 1, 0.1, 1)
    bm = bmesh.new()
    for n, p in J.items():
        rad = 0.006 if any(f in n for f in ("thumb", "index", "middle", "ring", "pinky")) else 0.012
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=rad, matrix=__import__("mathutils").Matrix.Translation(p))
    me = bpy.data.meshes.new("JV"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("JV", me); sc.collection.objects.link(o); me.materials.append(red)
    # bones as thin cylinders parent->child
    bm = bmesh.new()
    for n, p in J.items():
        pn = par.get(n)
        while pn and pn not in J:
            pn = par.get(pn)
        if pn:
            q = J[pn]
            d = p - q
            if d.length < 1e-4:
                continue
            m = __import__("mathutils").Matrix.Translation((p + q) / 2) @ d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0025, radius2=0.0025, depth=d.length, matrix=m)
    me2 = bpy.data.meshes.new("JL"); bm.to_mesh(me2); bm.free()
    o2 = bpy.data.objects.new("JL", me2); sc.collection.objects.link(o2); me2.materials.append(blu)
    bm = bmesh.new()
    for n, p in extra.items():
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=5, radius=0.005, matrix=__import__("mathutils").Matrix.Translation(p))
    me3 = bpy.data.meshes.new("JX"); bm.to_mesh(me3); bm.free()
    o3 = bpy.data.objects.new("JX", me3); sc.collection.objects.link(o3); me3.materials.append(grn)
    cam = sc.camera
    labels = []
    wht = red.copy(); wht.node_tree.nodes["Emission"].inputs["Color"].default_value = (0, 0, 0, 1)
    short = {"thumb": "t", "index": "i", "middle": "m", "ring": "r", "pinky": "p"}
    for n, p in list(J.items()) + [(k, v) for k, v in extra.items() if "_tip_" in k]:
        f = n.split("_")[0]
        if f in short:
            lab = short[f] + (n.split("_")[1][-1] if "_tip_" not in n else "T")
            if "metacarpal" in n:
                lab = short[f] + "M"
            cu = bpy.data.curves.new("L_" + n, 'FONT'); cu.body = lab; cu.size = 0.006
            t = bpy.data.objects.new("L_" + n, cu); sc.collection.objects.link(t)
            t.location = p; cu.materials.append(wht)
            labels.append(t)
    body = [bpy.data.objects["SK_2B_Body"]]
    mn, mx = world_bbox(body)
    pts = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    for v in views:
        if v.startswith("hand") or v.startswith("foot") or v.startswith("head"):
            kind, side, vd = v.split("_")
            key = {"hand": f"hand_{side}", "foot": f"foot_{side}", "head": "head"}[kind]
            c = J[key] if kind != "hand" else (J[f"hand_{side}"] + J[f"middle_02_{side}"]) / 2
            if kind == "foot":
                c = (J[f"foot_{side}"] + J[f"ball_{side}"]) / 2
            if kind == "head":
                c = J["head"] + Vector((0, 0, 0.03))
            look_at(cam, c, view_dir(vd), 0.45 if kind != "head" else 0.6)
        else:
            frame_camera(cam, (mn + mx) / 2, view_dir(v), pts)
        for t in labels:
            t.rotation_euler = cam.rotation_euler
            t.location = J.get(t.name[2:], extra.get(t.name[2:])) + (cam.location - t.location).normalized() * 0.012
        render_to(f"{prefix}_{v}.png")


main()
