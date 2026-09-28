"""Final-pass check renders of the SHIPPED Snow Flower sword + sheath (their game blends, shipped PNG maps only).
Adapted from the craft review's render script (same cameras, lights and jobs) so before/after pairs line up.

    blender -b Assets/SnowFlower/SnowFlower_Game_v4.blend --factory-startup --python mfp_render.py -- <job> <out> <sheath.blend> [only]
jobs: set | hero | close | lod | lodzoom
"""
import bpy, sys, math, os
from mathutils import Vector, Matrix
argv = sys.argv[sys.argv.index('--') + 1:]
JOB = argv[0]; OUT = argv[1]; SHEATH = argv[2]
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
with bpy.data.libraries.load(SHEATH, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n.startswith(('SM_SnowFlower_Sheath', 'SOCKET_SM_SnowFlower_Sheath'))]
for o in dst.objects:
    sc.collection.objects.link(o)
O = bpy.data.objects
sw = O['SM_SnowFlower_LodGroup']; sh = O['SM_SnowFlower_Sheath_LodGroup']
keep = {f'SM_SnowFlower_LOD{i}' for i in range(3)} | {f'SM_SnowFlower_Sheath_LOD{i}' for i in range(3)}
for o in list(O):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o); continue
    if o.name.startswith(('UCX', 'SOCKET')):
        o.hide_render = True
    elif o.type in ('MESH', 'CURVE') and o.name not in keep:
        o.hide_render = True
bpy.context.view_layer.update()
hol = O['SOCKET_SM_SnowFlower_Sheath_LOD0_Holster'].matrix_world.copy()
grip = O['SOCKET_SM_SnowFlower_LOD0_Grip'].matrix_local.copy()
print('HOLSTER', hol, 'GRIP', grip)

def layout(mode):
    if mode == 'sheathed':
        sw.matrix_world = hol @ grip.inverted()
    else:
        sw.matrix_world = Matrix.Translation((-0.17, 0, -0.3166))
    bpy.context.view_layer.update()

def lods(swl=0, shl=0):
    for i in range(3):
        O[f'SM_SnowFlower_LOD{i}'].hide_render = True if swl is None else (i != swl)
        O[f'SM_SnowFlower_Sheath_LOD{i}'].hide_render = True if shl is None else (i != shl)

sc.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
    for d in prefs.devices: d.use = (d.type == 'OPTIX')
    sc.cycles.device = 'GPU'
except Exception as e:
    print('GPUERR', e)
sc.cycles.samples = 128; sc.cycles.use_denoising = True
sc.view_settings.view_transform = 'AgX'
sc.render.image_settings.file_format = 'PNG'
w = bpy.data.worlds.new('cjw'); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs[1].default_value = -1; mr.inputs[2].default_value = 1
nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], mr.inputs[0]); nt.links.new(mr.outputs[0], ramp.inputs[0])
ramp.color_ramp.elements[0].color = (0.02, 0.02, 0.022, 1); ramp.color_ramp.elements[1].color = (0.9, 0.92, 0.95, 1)
e = ramp.color_ramp.elements.new(0.5); e.color = (0.18, 0.18, 0.19, 1)
bgA = nt.nodes.new('ShaderNodeBackground'); nt.links.new(ramp.outputs[0], bgA.inputs[0]); bgA.inputs[1].default_value = 0.6
bgB = nt.nodes.new('ShaderNodeBackground'); bgB.inputs[0].default_value = (0.16, 0.165, 0.17, 1); bgB.inputs[1].default_value = 1
lp = nt.nodes.new('ShaderNodeLightPath'); mix = nt.nodes.new('ShaderNodeMixShader'); outw = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0]); nt.links.new(bgA.outputs[0], mix.inputs[1]); nt.links.new(bgB.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], outw.inputs[0])
cam_d = bpy.data.cameras.new('cjcam'); cam = bpy.data.objects.new('cjcam', cam_d); sc.collection.objects.link(cam); sc.camera = cam
cam_d.clip_start = 0.005; cam_d.clip_end = 20
LB = [('key', 70, 0.8, Vector((-0.9, 0.9, 0.1)), (1, 0.98, 0.95)), ('fill', 18, 1.2, Vector((1.0, -0.2, 0.2)), (0.85, 0.9, 1.0)), ('rim', 80, 0.5, Vector((0.6, 0.9, -2.0)), (1, 1, 1))]
L = []
for nm, en, sz, loc, col in LB:
    ld = bpy.data.lights.new(nm, 'AREA'); ld.color = col
    lo = bpy.data.objects.new(nm, ld); sc.collection.objects.link(lo); lo.parent = cam; L.append(lo)

def look(eye, target, up=(0, 0, -1), ortho=None, lens=85, res=(1200, 1200)):
    eye = Vector(eye); target = Vector(target); f = (target - eye).normalized(); upv = Vector(up)
    r = f.cross(upv).normalized(); u = r.cross(f)
    M = Matrix(((r.x, u.x, -f.x), (r.y, u.y, -f.y), (r.z, u.z, -f.z))).to_4x4(); M.translation = eye
    cam.matrix_world = M
    if ortho:
        cam_d.type = 'ORTHO'; cam_d.ortho_scale = ortho
    else:
        cam_d.type = 'PERSP'; cam_d.lens = lens
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    D = (target - eye).length
    if ortho: D = max(1.5, ortho * 1.2)
    for lo, (nm, en, sz, loc, col) in zip(L, LB):
        lo.location = loc * D
        lo.data.energy = en * (D / 1.5) ** 2; lo.data.size = sz * D / 1.5
    bpy.context.view_layer.update()
    for lo in L:
        d = target - lo.matrix_world.translation
        q = d.to_track_quat('-Z', 'Y')
        lo.matrix_world = Matrix.LocRotScale(lo.matrix_world.translation, q, None)
    bpy.context.view_layer.update()

def shoot(name):
    sc.render.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True); print('WROTE', name)

orig = {}
for mname in [m.name for m in bpy.data.materials if m.name.startswith('M_SnowFlower') and not m.name.endswith('_CLAY')]:
    m = bpy.data.materials[mname]; c = m.copy(); c.name = mname + '_CLAY'
    b = next(n for n in c.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    for inp in ('Base Color', 'Metallic', 'Roughness'):
        for l in list(b.inputs[inp].links): c.node_tree.links.remove(l)
    b.inputs['Base Color'].default_value = (0.55, 0.55, 0.55, 1); b.inputs['Metallic'].default_value = 0; b.inputs['Roughness'].default_value = 0.5
    orig[mname] = (m, c)

def set_clay(on):
    for o in O:
        if o.type == 'MESH' and o.name in keep:
            for s in o.material_slots:
                if s.material is None: continue
                base = s.material.name.replace('_CLAY', '')
                if base in orig: s.material = orig[base][1] if on else orig[base][0]

UPH = (0, 0, -1)
if JOB == 'set':
    layout('sheathed'); lods(0, 0)
    zc = (-0.533 + 0.819) / 2
    for nm, eye in [('front', (0, -5, zc)), ('back', (0, 5, zc)), ('spine', (5, 0, zc)), ('edge', (-5, 0, zc))]:
        look(eye, (0, 0, zc), UPH, ortho=1.40, res=(700, 2000)); shoot('set_ortho_' + nm)
    look((0.9, -1.9, zc - 0.5), (0, 0, zc), UPH, lens=50, res=(1400, 2000)); shoot('set_persp_34front')
    look((-1.0, 1.8, zc - 0.4), (0, 0, zc), UPH, lens=50, res=(1400, 2000)); shoot('set_persp_34back')
    zm = -0.20
    for nm, eye in [('front', (0, -2, zm)), ('back', (0, 2, zm)), ('spine', (2, 0, zm)), ('edge', (-2, 0, zm))]:
        look(eye, (0, 0, zm), UPH, ortho=0.30, res=(1000, 1000)); shoot('mouth_ortho_' + nm)
    look((0.15, -0.28, -0.32), (0, 0, -0.20), UPH, lens=85, res=(1200, 1200)); shoot('mouth_persp_34front_high')
    look((-0.2, 0.22, -0.08), (0, 0, -0.20), UPH, lens=85, res=(1200, 1200)); shoot('mouth_persp_34back_low')
    look((0.02, -0.03, -1.2), (0, 0, -0.4), (0, -1, 0), lens=85, res=(1000, 1000)); shoot('end_pommel_down')
    look((0.02, -0.03, 1.6), (0, 0, 0.8), (0, -1, 0), lens=85, res=(1000, 1000)); shoot('end_chape_up')
elif JOB == 'hero':
    layout('drawn'); lods(0, 0)
    look((1.1, -2.2, -0.9), (-0.08, 0, 0.0), (0.3, 0, -1), lens=55, res=(2400, 1350)); shoot('drawn_hero')
    for W, H in ((256, 144), (128, 72)):
        look((1.1, -2.2, -0.9), (-0.08, 0, 0.0), (0.3, 0, -1), lens=55, res=(W, H)); shoot(f'thumb_drawn_{W}')
    layout('sheathed')
    look((1.0, -2.3, -0.7), (0, 0, 0.14), (0.4, 0, -1), lens=55, res=(2400, 1350)); shoot('sheathed_hero')
    for W, H in ((256, 144), (128, 72)):
        look((1.0, -2.3, -0.7), (0, 0, 0.14), (0.4, 0, -1), lens=55, res=(W, H)); shoot(f'thumb_sheathed_{W}')
elif JOB == 'close':
    layout('drawn'); lods(0, 0)
    X = -0.17
    shots = [('sw_pommel_end', (X + 0.10, -0.14, -0.70), (X, 0, -0.525)),
             ('sw_pommel_side', (X + 0.05, -0.30, -0.56), (X, 0, -0.505)),
             ('sw_grip', (X + 0.03, -0.40, -0.40), (X, 0, -0.40)),
             ('sw_guard_front34', (X + 0.18, -0.26, -0.10), (X, 0, -0.19)),
             ('sw_guard_back34', (X - 0.18, 0.26, -0.10), (X, 0, -0.19)),
             ('sw_guard_under', (X + 0.05, -0.20, -0.36), (X, 0, -0.20)),
             ('sw_blade_upper', (X + 0.10, -0.35, -0.02), (X, 0, -0.04)),
             ('sw_blade_upper_graze', (X + 0.30, -0.18, -0.02), (X, 0, -0.04)),
             ('sw_blade_lower', (X + 0.12, -0.35, 0.40), (X + 0.01, 0, 0.38)),
             ('sw_blade_tip', (X + 0.12, -0.35, 0.66), (X + 0.02, 0, 0.64)),
             ('sh_throat_34', (0.12, -0.26, -0.28), (0, 0, -0.15)),
             ('sh_throat_graze', (0.26, -0.14, -0.20), (0, 0, -0.15)),
             ('sh_band', (0.10, -0.28, -0.02), (0, 0, 0.0)),
             ('sh_vine_mid', (0.10, -0.35, 0.32), (0, 0, 0.30)),
             ('sh_vine_low', (0.10, -0.35, 0.60), (0, 0, 0.60)),
             ('sh_chape', (0.10, -0.28, 0.84), (0, 0, 0.76)),
             ('sh_back_band', (-0.10, 0.28, 0.02), (0, 0, 0.0))]
    only = argv[3].split(',') if len(argv) > 3 else None
    for nm, eye, tg in shots:
        if only and nm not in only: continue
        look(eye, tg, UPH, lens=85, res=(1100, 1100))
        set_clay(False); shoot(nm)
        set_clay(True); shoot(nm + '_clay')
    set_clay(False)
elif JOB == 'lod':
    for which in ('sw', 'sh'):
        for s in (1.0, 0.5, 0.25):
            res = int(1080 * s)
            for li in range(3):
                if which == 'sw':
                    layout('drawn'); lods(li, None); tg = Vector((-0.17, 0, 0.1)); Ln = 1.257
                else:
                    lods(None, li); tg = Vector((0, 0, 0.316)); Ln = 1.007
                look(tg + Vector((0.6, -3.0, 0.0)), tg, UPH, ortho=Ln * 1.03, res=(max(64, int(res * 0.5)), res))
                shoot(f'lod_{which}_s{int(s * 100):03d}_LOD{li}')
elif JOB == 'lodzoom':
    layout('drawn')
    for li in range(3):
        lods(li, None)
        look((-0.17 + 0.6, -3.0, 0.35), (-0.17, 0, 0.35), UPH, ortho=0.5, res=(600, 1000)); shoot(f'lodz_sw_blade_LOD{li}')
        look((-0.17 + 0.2, -1.0, -0.30), (-0.17, 0, -0.30), UPH, ortho=0.45, res=(700, 1000)); shoot(f'lodz_sw_hilt_LOD{li}')
