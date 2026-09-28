# Independent measurer (round 1): render the SHIPPED FBX + textures from the REFERENCE_SPEC section 1 camera.
import bpy, math, sys, json
from mathutils import Vector, Euler, Matrix
argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
roll_sign = float(argv[0]) if argv else 1.0
out = argv[1] if len(argv) > 1 else 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/measure_r1/m1_render.exr'
key_scale = float(argv[2]) if len(argv) > 2 else 1.0
spp = int(argv[3]) if len(argv) > 3 else 256
P = 'C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackHat/'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=P+'SM_BlackHat.fbx')
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name != 'SM_BlackHat_LOD0':
        bpy.data.objects.remove(o, do_unlink=True)
hat = bpy.data.objects['SM_BlackHat_LOD0']
side = json.load(open(P+'SM_BlackHat.sockets.json'))
def img(name, cs):
    i = bpy.data.images.load(P+'Textures/'+name+'.png'); i.colorspace_settings.name = cs; return i
for mname, part in (('M_BlackHat_Straw','Straw'),('M_BlackHat_Cloth','Cloth')):
    m = bpy.data.materials[mname]; m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    tint = side['materials'][mname]['tint_default_linear']
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = hat.data.uv_layers[0].name
    def tex(k, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(f'T_BlackHat_{part}_{k}', cs)
        t.interpolation = 'Cubic'; t.extension = 'REPEAT'
        nt.links.new(uv.outputs[0], t.inputs[0]); return t
    det = tex('Detail','sRGB'); orm = tex('ORM','Non-Color'); nrm = tex('N','Non-Color')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(bs.outputs[0], o.inputs[0])
    sepd = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(det.outputs['Color'], sepd.inputs[0])
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type='RGBA'; mul.blend_type='MULTIPLY'; mul.inputs[0].default_value=1.0
    cmb = nt.nodes.new('ShaderNodeCombineColor')
    for c in range(3): nt.links.new(sepd.outputs[0], cmb.inputs[c])
    nt.links.new(cmb.outputs[0], mul.inputs[6]); mul.inputs[7].default_value = (*tint, 1)
    nt.links.new(mul.outputs[2], bs.inputs['Base Color'])
    sepo = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs['Color'], sepo.inputs[0])
    nt.links.new(sepo.outputs[1], bs.inputs['Roughness'])
    nt.links.new(orm.outputs['Alpha'], bs.inputs['Specular IOR Level'])   # UE Specular = 1 x ORM.A
    bs.inputs['Metallic'].default_value = 0.0
    # DirectX normal -> OpenGL: invert green
    sepn = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(nrm.outputs['Color'], sepn.inputs[0])
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation='SUBTRACT'; inv.inputs[0].default_value=1.0
    nt.links.new(sepn.outputs[1], inv.inputs[1])
    cn = nt.nodes.new('ShaderNodeCombineColor')
    nt.links.new(sepn.outputs[0], cn.inputs[0]); nt.links.new(inv.outputs[0], cn.inputs[1]); nt.links.new(sepn.outputs[2], cn.inputs[2])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = uv.uv_map
    nt.links.new(cn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
R = 0.3
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam)
cam.location = Vector((2.174, 1.205, 0.761)) * R
dirv = (Vector((0,0,0)) - cam.location).normalized()
q = dirv.to_track_quat('-Z','Y')
cam.rotation_euler = q.to_euler()
# roll about view axis
cam.rotation_euler = (Matrix.Rotation(math.radians(0.51*roll_sign), 4, dirv) @ cam.rotation_euler.to_matrix().to_4x4()).to_euler()
cam_d.lens = 42.8; cam_d.sensor_width = 36; cam_d.sensor_fit = 'HORIZONTAL'
cam_d.shift_x = 0.0; cam_d.shift_y = 0.0; cam_d.clip_start = 0.01
sc.camera = cam
sc.render.resolution_x = 670; sc.render.resolution_y = 599
from bpy_extras.object_utils import world_to_camera_view
bpy.context.view_layer.update()
p = world_to_camera_view(sc, cam, Vector((0,0,0)))
px0 = p.x*670; py0 = (1-p.y)*599
# aim: rim centre lands at image (332.97, 291.94) px (REFERENCE_SPEC 1 'Aim'); Blender shift is a fraction of the 670 px width
cam_d.shift_x = (px0 - 332.97)/670.0; cam_d.shift_y = -(py0 - 291.94)/670.0 * -1.0
bpy.context.view_layer.update()
cam_d.shift_y = (py0 - 291.94)/670.0 * -1.0
bpy.context.view_layer.update()
p2 = world_to_camera_view(sc, cam, Vector((0,0,0)))
if abs((1-p2.y)*599 - 291.94) > 0.5: cam_d.shift_y = -cam_d.shift_y
bpy.context.view_layer.update(); p2 = world_to_camera_view(sc, cam, Vector((0,0,0)))
print('AIM', p2.x*670, (1-p2.y)*599, 'shift', cam_d.shift_x, cam_d.shift_y)
sc.render.resolution_x = 670; sc.render.resolution_y = 599; sc.render.resolution_percentage = 100
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = spp; sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[0].default_value = (1,1,1,1); bg.inputs[1].default_value = 0.35
# REFERENCE_SPEC 2 proposed rig; azimuth phi = 29 + theta (deg)
def area(name, theta, elev, power, size=0.9, dist=1.6):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = power; L.size = size
    ob = bpy.data.objects.new(name, L); sc.collection.objects.link(ob)
    phi = math.radians(29 + theta); e = math.radians(elev)
    ob.location = Vector((math.cos(phi)*math.cos(e), math.sin(phi)*math.cos(e), math.sin(e))) * dist
    ob.rotation_euler = (Vector((0,0,0.05)) - ob.location).to_track_quat('-Z','Y').to_euler()
LIGHTS = json.loads(open(argv[4]).read()) if len(argv) > 4 else {'world': 0.35, 'lights': [['key',-110,35,260],['kick',115,25,156],['fill',0,20,52]]}
bg.inputs[1].default_value = LIGHTS['world']
for nm, th, el, pw in LIGHTS['lights']:
    if pw > 0: area(nm, th, el, pw*key_scale)
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.image_settings.color_depth = '32'
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print('RENDERED', out)
