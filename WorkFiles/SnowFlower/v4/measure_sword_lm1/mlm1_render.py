# mlm1: independent render of the SHIPPED SM_SnowFlower.fbx (LOD0) with the shipped baked maps.
# usage: blender -b --factory-startup --python mlm1_render.py -- view1,view2 samples [camjson]
import bpy, math, sys, json, os
from mathutils import Vector, Matrix
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_lm1"
EXP = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/SnowFlower/v4"
argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
only = set(argv[0].split(',')) if argv and argv[0] != 'all' else None
samples = int(argv[1]) if len(argv) > 1 else 96
camover = json.loads(argv[2]) if len(argv) > 2 else {}
LOD = os.environ.get("MLM1_LOD", "0")

for o in list(bpy.data.objects): bpy.data.objects.remove(o)
bpy.ops.import_scene.fbx(filepath=EXP + "/SM_SnowFlower.fbx")
sw = bpy.data.objects["SM_SnowFlower_LOD" + LOD]
for o in list(bpy.data.objects):
    if o is not sw: bpy.data.objects.remove(o)
sw.parent = None
sw.matrix_world = Matrix.Rotation(math.pi, 4, 'Y')   # pommel -> +Z', spine(+x) -> -X'

def img(n, nc):
    i = bpy.data.images.load(EXP + "/Textures/" + n, check_existing=True)
    i.colorspace_settings.name = 'Non-Color' if nc else 'sRGB'
    return i
def mat(name, pre):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
    uv = N.new('ShaderNodeUVMap'); uv.uv_map = 'UV0'
    bc = N.new('ShaderNodeTexImage'); bc.image = img(pre + "_BC.png", False)
    orm = N.new('ShaderNodeTexImage'); orm.image = img(pre + "_ORM.png", True)
    nm = N.new('ShaderNodeTexImage'); nm.image = img(pre + "_N.png", True)
    for t in (bc, orm, nm): L.new(uv.outputs[0], t.inputs[0])
    sep = N.new('ShaderNodeSeparateColor'); L.new(orm.outputs[0], sep.inputs[0])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs[0].default_value = 0.75
    L.new(bc.outputs[0], mul.inputs[6]); L.new(sep.outputs[0], mul.inputs[7])
    L.new(mul.outputs[2], bsdf.inputs['Base Color'])
    L.new(sep.outputs[1], bsdf.inputs['Roughness']); L.new(sep.outputs[2], bsdf.inputs['Metallic'])
    sn = N.new('ShaderNodeSeparateColor'); L.new(nm.outputs[0], sn.inputs[0])
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
    L.new(sn.outputs[1], inv.inputs[1])   # DirectX -> OpenGL green
    cn = N.new('ShaderNodeCombineColor'); L.new(sn.outputs[0], cn.inputs[0]); L.new(inv.outputs[0], cn.inputs[1]); L.new(sn.outputs[2], cn.inputs[2])
    nmap = N.new('ShaderNodeNormalMap'); nmap.uv_map = 'UV0'; L.new(cn.outputs[0], nmap.inputs['Color'])
    L.new(nmap.outputs[0], bsdf.inputs['Normal'])
    return m
steel = mat("mlm1_steel", "T_SnowFlower_Steel"); wrap = mat("mlm1_wrap", "T_SnowFlower_Wrap")
for s in sw.material_slots:
    s.material = wrap if "Grip" in s.material.name or "Wrap" in s.material.name else steel
print("SLOTS", [s.material.name for s in sw.material_slots])

sc = bpy.context.scene
sc.render.engine = 'CYCLES'
try:
    pr = bpy.context.preferences.addons['cycles'].preferences
    pr.compute_device_type = 'OPTIX'; pr.get_devices()
    for d in pr.devices: d.use = True
    sc.cycles.device = 'GPU'
except Exception as e:
    print("GPUFAIL", e)
sc.cycles.samples = samples; sc.cycles.use_denoising = True
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.use_stamp = False
# studio world: dark floor band, white upper dome (soft reflections for polished metal)
w = bpy.data.worlds.new("mlm1_w"); sc.world = w; w.use_nodes = True
N = w.node_tree.nodes; L = w.node_tree.links
bg = next(n for n in N if n.type == 'BACKGROUND')
tc = N.new('ShaderNodeTexCoord'); sepx = N.new('ShaderNodeSeparateXYZ'); L.new(tc.outputs['Generated'], sepx.inputs[0])
ramp = N.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.05, 0.05, 0.055, 1)
ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
L.new(sepx.outputs[2], ramp.inputs[0]); L.new(ramp.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.45

def area(name, loc, energy, size):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size
    o = bpy.data.objects.new(name, l); sc.collection.objects.link(o); o.location = loc
    d = Vector((0, 0, -0.4)) - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return o
area("k_f", (-0.6, -1.2, 0.8), 30, 1.2); area("k_b", (0.6, 1.2, 0.8), 30, 1.2)
area("f_f", (0.9, -1.0, -0.8), 10, 1.5); area("f_b", (-0.9, 1.0, -0.8), 10, 1.5)
area("s1", (1.4, 0, 0), 8, 1.5); area("s2", (-1.4, 0, 0), 8, 1.5)

cam_d = bpy.data.cameras.new("mlm1_cam"); cam = bpy.data.objects.new("mlm1_cam", cam_d)
sc.collection.objects.link(cam); sc.camera = cam

def orient(view_dir, axis, screen):
    f = -Vector(view_dir).normalized()
    a = Vector(axis); a = (a - a.dot(f) * f).normalized()
    c = f.cross(a).normalized()
    sx, sy = screen; n = math.hypot(sx, sy); sx /= n; sy /= n
    for s in (1, -1):
        cc = c * s
        r = (sx * a - sy * cc); u = (sy * a + sx * cc)
        if r.cross(u).dot(-f) > 0.99: break
    return Matrix((r, u, -f)).transposed().to_4x4()

MMPP = 1256.3 / 1205.0 / 4.0      # 4x the sheet scale
def go(name):
    sc.render.filepath = OUT + "/mlm1_ours_" + name + ".png"
    bpy.ops.render.render(write_still=True); print("WROTE", name)
def ortho(name, view_dir, W, H, cz):
    if only and name not in only: return
    cam_d.type = 'ORTHO'; cam_d.ortho_scale = max(W, H) * MMPP / 1000.0
    M = orient(view_dir, (0, 0, 1), (0, 1))
    M.translation = Vector((0, 0, cz / 1000.0)) + Vector(view_dir).normalized() * 2.0
    cam.matrix_world = M; cam_d.clip_end = 10
    sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    go(name)
def persp(name, target, view_dir, axis, screen, dist, lens, W, H):
    if only and name not in only: return
    c = camover.get(name, {})
    target = c.get("target", target); view_dir = c.get("view_dir", view_dir); screen = c.get("screen", screen)
    dist = c.get("dist", dist); lens = c.get("lens", lens)
    cam_d.type = 'PERSP'; cam_d.lens = lens; cam_d.sensor_fit = 'HORIZONTAL'; cam_d.sensor_width = 36
    M = orient(view_dir, axis, screen); M.translation = Vector(target) / 1000.0 + Vector(view_dir).normalized() * dist / 1000.0
    cam.matrix_world = M; cam_d.clip_start = 0.01
    sc.render.resolution_x = W; sc.render.resolution_y = H; sc.render.resolution_percentage = 100
    go(name + c.get("suffix", ""))

cz = -(-216.3 + 1040.0) / 2.0
ortho("front", (0, -1, 0), 640, 5000, cz)
ortho("back", (0, 1, 0), 640, 5000, cz)
ortho("side_px", (-1, 0, 0), 640, 5000, cz)
ortho("side_mx", (1, 0, 0), 640, 5000, cz)
e = math.radians(35)
persp("guard", (0, 0, -110), (0, -math.cos(e), math.sin(e)), (0, 0, 1), (0, 1), 560, 100, 1176, 1545)
e = math.radians(28)
persp("pommel", (0, 0, 200), (0.25 * math.sin(e), -math.sin(e), math.cos(e)), (0, 0, -1), (-0.6, -1), 520, 100, 1176, 870)
e = math.radians(10)
persp("blade", (4, 0, -250), (math.sin(e), -math.cos(e), 0), (0, 0, -1), (0.84, -0.54), 520, 100, 1176, 828)
