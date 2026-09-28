# Independent measurer r2: render the SHIPPED FBX + baked textures from the REFERENCE_SPEC section 1 camera.
# Material = sidecar contract: BaseColor = T_*_BC (equals Tint x (Bias + Scale x Detail)), Roughness = ORM.G,
# Specular = specular_scale x ORM.A, Metallic 0, Normal = N (DirectX -> green flipped for Blender).
# args: out.exr  lights.json|'-'  spp  aim_x aim_y  roll_deg  [filter_px] [mode: rgb|alpha]
import bpy, math, sys, json
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
a = sys.argv[sys.argv.index('--')+1:]
out, lights_js, spp = a[0], a[1], int(a[2])
aim_x, aim_y, roll = float(a[3]), float(a[4]), float(a[5])
filt = float(a[6]) if len(a) > 6 else 1.5
P = 'C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackHat/'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=P+'SM_BlackHat.fbx')
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type != 'MESH' or o.name != 'SM_BlackHat_LOD0':
        if o.type == 'MESH': bpy.data.objects.remove(o, do_unlink=True)
hat = bpy.data.objects['SM_BlackHat_LOD0']
print('LOD0_TRIS', sum(len(p.vertices)-2 for p in hat.data.polygons), 'dims', tuple(round(v, 4) for v in hat.dimensions),
      'loc', tuple(hat.matrix_world.translation), 'mats', [m.name for m in hat.data.materials])
side = json.load(open(P+'SM_BlackHat.sockets.json'))
for mname in ('M_BlackHat_Straw', 'M_BlackHat_Cloth'):
    md = side['materials'][mname]; part = mname.split('_')[-1]
    m = bpy.data.materials[mname]; m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = hat.data.uv_layers[0].name
    def tex(k, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); i = bpy.data.images.load(P+f'Textures/T_BlackHat_{part}_{k}.png')
        i.colorspace_settings.name = cs; t.image = i; t.interpolation = 'Linear'
        nt.links.new(uv.outputs[0], t.inputs[0]); return t
    bc = tex('BC', 'sRGB'); orm = tex('ORM', 'Non-Color'); nrm = tex('N', 'Non-Color')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(bs.outputs[0], o.inputs[0]); nt.links.new(bc.outputs['Color'], bs.inputs['Base Color'])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[1], bs.inputs['Roughness'])
    sm = nt.nodes.new('ShaderNodeMath'); sm.operation = 'MULTIPLY'; sm.inputs[1].default_value = float(md.get('specular_scale', 1.0))
    nt.links.new(orm.outputs['Alpha'], sm.inputs[0]); nt.links.new(sm.outputs[0], bs.inputs['Specular IOR Level'])
    bs.inputs['Metallic'].default_value = 0.0
    sn = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(nrm.outputs['Color'], sn.inputs[0])
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    nt.links.new(sn.outputs[1], inv.inputs[1])
    cn = nt.nodes.new('ShaderNodeCombineColor')
    nt.links.new(sn.outputs[0], cn.inputs[0]); nt.links.new(inv.outputs[0], cn.inputs[1]); nt.links.new(sn.outputs[2], cn.inputs[2])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = uv.uv_map
    nt.links.new(cn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
    print('MAT', mname, 'spec_scale', md.get('specular_scale'))
R = 0.3; W, H = 670, 599
cd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cd); sc.collection.objects.link(cam)
cam.location = Vector((2.174, 1.205, 0.761))*R
dv = (-cam.location).normalized()
base = dv.to_track_quat('-Z', 'Y').to_matrix().to_4x4()
cam.matrix_world = Matrix.Translation(cam.location) @ Matrix.Rotation(math.radians(roll), 4, dv) @ base
cd.lens = 42.8; cd.sensor_width = 36; cd.sensor_fit = 'HORIZONTAL'; cd.clip_start = 0.01
sc.camera = cam; sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
bpy.context.view_layer.update()
def proj(v):
    p = world_to_camera_view(sc, cam, v); return p.x*W, (1-p.y)*H
for it in range(4):
    px, py = proj(Vector((0, 0, 0)))
    # shift_x moves image content left when positive
    cd.shift_x += (px - aim_x)/W
    cd.shift_y -= (py - aim_y)/W
    bpy.context.view_layer.update()
px, py = proj(Vector((0, 0, 0)))
print('AIM', round(px, 3), round(py, 3), 'shift', round(cd.shift_x, 5), round(cd.shift_y, 5))
# roll check: rim left/right extreme points
import numpy as np
pts = [proj(Vector((R*math.cos(t), R*math.sin(t), 0))) for t in np.linspace(0, 2*math.pi, 720)]
xl = min(pts); xr = max(pts); print('RIM_EXTREMES', [round(v, 2) for v in xl], [round(v, 2) for v in xr])
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = spp
sc.cycles.use_denoising = False; sc.cycles.use_adaptive_sampling = False
sc.cycles.filter_width = filt
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[0].default_value = (1, 1, 1, 1)
L = json.load(open(lights_js)) if lights_js != '-' else {'world': 0.35, 'lights': [['key', -110, 35, 260], ['kick', 115, 25, 156], ['fill', 0, 20, 52]]}
bg.inputs[1].default_value = L['world']
def area(name, theta, elev, power, size=0.9, dist=1.6):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = power; ld.size = size
    ob = bpy.data.objects.new(name, ld); sc.collection.objects.link(ob)
    phi = math.radians(29 + theta); e = math.radians(elev)
    ob.location = Vector((math.cos(phi)*math.cos(e), math.sin(phi)*math.cos(e), math.sin(e)))*dist
    ob.rotation_euler = (Vector((0, 0, 0.05)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
for nm_, th, el, pw in L['lights']:
    if pw > 0: area(nm_, th, el, pw)
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.image_settings.color_depth = '32'
sc.render.filepath = out
import time; t0 = time.time()
bpy.ops.render.render(write_still=True)
print('RENDERED', out, 'sec', round(time.time()-t0, 1))
