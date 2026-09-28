"""Orthographic top view, mirror material, environment colour = reflected direction.
A flat face must render as ONE uniform colour; any gradient on a flat knife facet is bent shading normals.
Runs on a COPY of the blend; never saves."""
import bpy, math, sys, bmesh
from mathutils import Vector
out_dir = sys.argv[sys.argv.index("--") + 1]
keep = {"SM_Shuriken_FourPoint_LOD0", "SM_Shuriken_FourPoint_LOD1"}
for o in list(bpy.data.objects):
    if o.name not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
scene = bpy.context.scene
mat = bpy.data.materials.new("Mirror"); mat.use_nodes = True
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Base Color"].default_value = (1, 1, 1, 1)
bsdf.inputs["Metallic"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.0
for o in bpy.data.objects:
    o.data.materials.clear(); o.data.materials.append(mat)
world = bpy.data.worlds.new("W"); scene.world = world; world.use_nodes = True
nt = world.node_tree
bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
tc = nt.nodes.new("ShaderNodeTexCoord")
# colour = 0.5 + 0.5 * direction, amplified contrast around the facet's reflection direction
mad = nt.nodes.new("ShaderNodeVectorMath"); mad.operation = "MULTIPLY_ADD"
mad.inputs[1].default_value = (2.0, 2.0, 2.0); mad.inputs[2].default_value = (0.5, 0.5, 0.5)
nt.links.new(tc.outputs["Generated"], mad.inputs[0])
nt.links.new(mad.outputs[0], bg.inputs["Color"])
cam_data = bpy.data.cameras.new("C"); cam_data.type = "ORTHO"; cam_data.ortho_scale = 0.044
cam = bpy.data.objects.new("C", cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam.location = (0.0285, 0.0, 0.2); cam.rotation_euler = (0, 0, 0)
scene.render.engine = "CYCLES"; scene.cycles.samples = 4; scene.cycles.use_denoising = False
scene.render.resolution_x, scene.render.resolution_y = 1600, 300
scene.view_settings.view_transform = "Standard"
scene.render.film_transparent = False

def mark(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data); n = 0
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.smooth:
            f1, f2 = e.link_faces
            s1 = math.degrees(math.acos(min(1, abs(f1.normal.z)))); s2 = math.degrees(math.acos(min(1, abs(f2.normal.z))))
            if 30 < s1 < 40 and 30 < s2 < 40 and math.degrees(f1.normal.angle(f2.normal)) > 2.0:
                e.smooth = False; n += 1
    bm.to_mesh(obj.data); bm.free(); obj.data.update(); return n

def shot(name, tag):
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.hide_render = o.name != name
    scene.render.filepath = f"{out_dir}/refl_{name[-4:]}_{tag}.png"
    bpy.ops.render.render(write_still=True)

shot("SM_Shuriken_FourPoint_LOD0", "asbuilt"); shot("SM_Shuriken_FourPoint_LOD1", "asbuilt")
print("marked", mark(bpy.data.objects["SM_Shuriken_FourPoint_LOD0"]), mark(bpy.data.objects["SM_Shuriken_FourPoint_LOD1"]))
shot("SM_Shuriken_FourPoint_LOD0", "sharp"); shot("SM_Shuriken_FourPoint_LOD1", "sharp")
print("REFL DONE")
