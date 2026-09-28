"""Render the SHIPPED revision-3 FBX (Exports/SnowFlower/SM_SnowFlower.fbx) with its own baked textures,
at a fixed pixel-per-metre scale that matches the reference sheet, plus close detail views.
Read-only on the export: nothing is saved. Output PNGs go to WorkFiles/SnowFlower/v4/audit/renders/.
blender -b --factory-startup --python render_rev3_export.py -- [which]
"""
import bpy, sys, json, math, os
from pathlib import Path
from mathutils import Vector, Quaternion, Euler

ROOT = Path(r'C:/Users/Cody/Desktop/Blender_Projects')
EXP = ROOT / 'Exports/SnowFlower'
OUT = ROOT / 'WorkFiles/SnowFlower/v4/audit/renders'
OUT.mkdir(parents=True, exist_ok=True)
which = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
which = which or ['views', 'details']

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
bpy.ops.import_scene.fbx(filepath=str(EXP / 'SM_SnowFlower.fbx'), use_anim=False)
names = sorted(o.name for o in scene.objects)
print('IMPORTED', names)
manifest = json.load(open(EXP / 'material_manifest.json'))
sword = [o for o in scene.objects if o.type == 'MESH' and not o.name.startswith('UCX_')][0]
for o in scene.objects:
    if o.name.startswith('UCX_'):
        o.hide_render = True
# hook baked textures from the manifest
for slot in sword.material_slots:
    m = slot.material
    info = manifest['materials'][m.name]
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(bs.outputs[0], out.inputs[0])
    def tex(rel, cs):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(str(EXP / rel))
        t.image.colorspace_settings.name = cs; return t
    bc = tex(info['base_color'], 'sRGB'); nt.links.new(bc.outputs[0], bs.inputs['Base Color'])
    rg = tex(info['roughness'], 'Non-Color'); nt.links.new(rg.outputs[0], bs.inputs['Roughness'])
    nm = tex(info['normal'], 'Non-Color'); nmap = nt.nodes.new('ShaderNodeNormalMap')
    nt.links.new(nm.outputs[0], nmap.inputs['Color']); nt.links.new(nmap.outputs[0], bs.inputs['Normal'])
    bs.inputs['Metallic'].default_value = info['metallic_value']

# orient: pommel up (rotate 180 deg about world Y)
sword.rotation_euler = (0, math.pi, 0)
for o in scene.objects:
    if o.name.startswith('UCX_'): o.rotation_euler = (0, math.pi, 0)
bpy.context.view_layer.update()
ws = [sword.matrix_world @ v.co for v in sword.data.vertices]
zmax = max(v.z for v in ws); zmin = min(v.z for v in ws)
print('ROTATED_BOUNDS', min(v.x for v in ws), max(v.x for v in ws), min(v.y for v in ws), max(v.y for v in ws), zmin, zmax)

# studio: neutral environment + soft key, white-ish background composite later (film transparent)
world = bpy.data.worlds.new('AuditWorld'); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value = (.62, .63, .65, 1); bg.inputs['Strength'].default_value = .9
for name, loc, energy, size in [('Key', (-1.2, -1.6, .6), 60, 1.4), ('Fill', (1.3, -1.2, -.2), 30, 1.4), ('Rim', (.4, 1.5, .3), 45, 1.2), ('Top', (0, -.5, 1.4), 20, .8)]:
    L = bpy.data.lights.new(name, 'AREA'); L.energy = energy; L.size = size; L.shape = 'SQUARE'
    ob = bpy.data.objects.new(name, L); scene.collection.objects.link(ob); ob.location = loc
    ob.rotation_euler = (Vector((0, 0, -.45)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
scene.render.engine = 'CYCLES'; scene.cycles.samples = 64; scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use = d.type != 'CPU'
    scene.cycles.device = 'GPU'
except Exception as e:
    print('GPU fallback', e)
scene.view_settings.view_transform = 'Standard'
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'; scene.render.image_settings.color_mode = 'RGBA'
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam')); scene.collection.objects.link(cam); scene.camera = cam
cam.data.clip_start = .001; cam.data.clip_end = 20

PXM = 1206 / (zmax - zmin)  # px per metre so total length = 1206 px (reference front view)
print('PX_PER_M', PXM)

def ortho(name, direction, center, w, h, pxm, up=Vector((0, 0, 1))):
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(w, h) / pxm
    d = Vector(direction).normalized(); cam.location = Vector(center) - d * 3
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    scene.render.resolution_x = w; scene.render.resolution_y = h; scene.render.resolution_percentage = 100
    scene.render.filepath = str(OUT / (name + '.png')); bpy.ops.render.render(write_still=True)
    print('RENDERED', name, flush=True)

def persp(name, loc, target, lens, w, h):
    cam.data.type = 'PERSP'; cam.data.lens = lens; cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    scene.render.resolution_x = w; scene.render.resolution_y = h; scene.render.resolution_percentage = 100
    scene.render.filepath = str(OUT / (name + '.png')); bpy.ops.render.render(write_still=True)
    print('RENDERED', name, flush=True)

H = 1287
zc = zmax - (H / 2 - 10) / PXM  # sword top lands on row 10
if 'views' in which:
    ortho('rev3_front_1x', (0, 1, 0), (0, 0, zc), 300, H, PXM)
    ortho('rev3_side_1x', (-1, 0, 0), (0, 0, zc), 300, H, PXM)
    ortho('rev3_back_1x', (0, -1, 0), (0, 0, zc), 300, H, PXM)
if 'details' in which:
    # hilt close-up, front, 4x the sheet scale
    ortho('rev3_hilt_front_4x', (0, 1, 0), (0, 0, zmax - (400 * 4 / 2) / (PXM * 4) + 10 / (PXM * 4)), 560, 1600, PXM * 4)
    ortho('rev3_hilt_side_4x', (-1, 0, 0), (0, 0, zmax - (400 * 4 / 2) / (PXM * 4) + 10 / (PXM * 4)), 560, 1600, PXM * 4)
    # guard detail (perspective, front, slightly above, like the sheet's guard crop)
    gz = -0.135
    persp('rev3_guard_detail', (0.0, -0.36, gz + 0.16), (0, 0, gz - 0.02), 85, 900, 1000)
    # pommel detail: looking at pommel face from front/above
    pz = 0.155
    persp('rev3_pommel_detail', (0.03, -0.20, pz + 0.12), (0, 0, pz - 0.005), 85, 900, 800)
    # blade relief detail near guard, diagonal
    persp('rev3_blade_detail', (0.05, -0.22, -0.30), (0.0, 0, -0.33), 70, 1000, 700)
print('DONE')
