# Shimmer probe: EEVEE, 1 sample, shipped FBX + textures (sidecar material contract), game-distance view,
# N frames at a small rotation step; writes EXR frames. args: export_dir outdir step_deg nframes dist
import bpy, math, sys, json, os
from mathutils import Vector
a = sys.argv[sys.argv.index('--')+1:]
P, OUT, step, nf, dist = a[0].rstrip('/')+'/', a[1], float(a[2]), int(a[3]), float(a[4])
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=P+'SM_BlackHat.fbx')
sc = bpy.context.scene
for o in list(bpy.data.objects):
    if o.type == 'MESH' and o.name != 'SM_BlackHat_LOD0': bpy.data.objects.remove(o, do_unlink=True)
hat = bpy.data.objects['SM_BlackHat_LOD0']
side = json.load(open(P+'SM_BlackHat.sockets.json'))
for mname in ('M_BlackHat_Straw', 'M_BlackHat_Cloth'):
    md = side['materials'][mname]; part = mname.split('_')[-1]
    m = bpy.data.materials[mname]; m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = hat.data.uv_layers[0].name
    def tex(k, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); i = bpy.data.images.load(P+f'Textures/T_BlackHat_{part}_{k}.png')
        i.colorspace_settings.name = cs; t.image = i; t.interpolation = 'Linear'; nt.links.new(uv.outputs[0], t.inputs[0]); return t
    bc = tex('BC', 'sRGB'); orm = tex('ORM', 'Non-Color'); nrm = tex('N', 'Non-Color')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(bs.outputs[0], o.inputs[0]); nt.links.new(bc.outputs['Color'], bs.inputs['Base Color'])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(orm.outputs['Color'], sep.inputs[0]); nt.links.new(sep.outputs[1], bs.inputs['Roughness'])
    sm = nt.nodes.new('ShaderNodeMath'); sm.operation = 'MULTIPLY'; sm.inputs[1].default_value = float(md.get('specular_scale', 1.0))
    nt.links.new(orm.outputs['Alpha'], sm.inputs[0]); nt.links.new(sm.outputs[0], bs.inputs['Specular IOR Level'])
    sn = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(nrm.outputs['Color'], sn.inputs[0])
    inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; nt.links.new(sn.outputs[1], inv.inputs[1])
    cn = nt.nodes.new('ShaderNodeCombineColor')
    nt.links.new(sn.outputs[0], cn.inputs[0]); nt.links.new(inv.outputs[0], cn.inputs[1]); nt.links.new(sn.outputs[2], cn.inputs[2])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = uv.uv_map; nt.links.new(cn.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
root = bpy.data.objects.new('turn_root', None); sc.collection.objects.link(root)
mw = hat.matrix_world.copy(); hat.parent = root; hat.matrix_world = mw
for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
    try: sc.render.engine = eng; break
    except TypeError: pass
sc.eevee.taa_render_samples = 1
sc.view_settings.view_transform = 'Standard'; sc.render.film_transparent = True
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND'); bg.inputs[0].default_value = (0.9, 0.9, 0.9, 1); bg.inputs[1].default_value = 0.6
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 4.0; sun.data.angle = math.radians(3); sun.rotation_euler = (math.radians(45), 0, math.radians(140))
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
tgt = Vector((0, 0, 0.07)); e = math.radians(18); az = math.radians(29)
cam.location = tgt + Vector((math.cos(az)*math.cos(e), math.sin(az)*math.cos(e), math.sin(e)))*dist
cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler(); cam.data.lens = 85
sc.render.resolution_x, sc.render.resolution_y = 960, 540
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_mode = 'RGBA'; sc.render.image_settings.color_depth = '32'
print('ENGINE', sc.render.engine)
for i in range(nf):
    root.rotation_euler = (0, 0, math.radians(i*step))
    sc.render.filepath = os.path.join(OUT, f'f_{i:02d}.exr'); bpy.ops.render.render(write_still=True)
print('TURN_DONE', OUT)
