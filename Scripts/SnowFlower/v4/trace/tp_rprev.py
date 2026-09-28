"""Trace pilot v2: quick look-dev preview of the HIGH relief with its relief-domain maps (NOT a deliverable - the
deliverables render only the baked game mesh).  blender -b work/tp_high.blend --factory-startup --python tp_rprev.py -- tag [views]"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import tp_render as R, tp_img
from mathutils import Vector, Matrix

WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
tag = argv[0] if argv else "a"
views = set(argv[1:]) or {"front", "q34"}
K = 0.687
def zr(row): return (row - 304.0) * K
sc = bpy.context.scene
for o in list(sc.objects):
    if o.name != "TP_Throat_HIGH":
        bpy.data.objects.remove(o)


def img(name, noncolor):
    im = bpy.data.images.load(WORK + f"/relief_{name}.png", check_existing=False)
    im.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    return im


m = bpy.data.materials["TP_Relief"]; m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputMaterial"); bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
nt.links.new(bs.outputs[0], out.inputs["Surface"])
uvn = nt.nodes.new("ShaderNodeUVMap"); uvn.uv_map = "REF"
for key, inp, nc in (("BC", "Base Color", False), ("R", "Roughness", True), ("M", "Metallic", True)):
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img(key, nc); t.interpolation = 'Linear'
    nt.links.new(uvn.outputs[0], t.inputs[0]); nt.links.new(t.outputs["Color"], bs.inputs[inp])
m2 = bpy.data.materials["TP_RingSilver"]; m2.use_nodes = True
b2 = next(n for n in m2.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
b2.inputs["Base Color"].default_value = (0.25, 0.24, 0.24, 1); b2.inputs["Metallic"].default_value = 1.0
b2.inputs["Roughness"].default_value = 0.3
if os.environ.get("TP_CLAY") == "1":
    for mm in (m, m2):
        nt_ = mm.node_tree; nt_.nodes.clear(); o_ = nt_.nodes.new("ShaderNodeOutputMaterial"); d_ = nt_.nodes.new("ShaderNodeBsdfDiffuse")
        d_.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1); nt_.links.new(d_.outputs[0], o_.inputs["Surface"])
R.settings(int(os.environ.get("TP_SAMPLES", "32")), (728, 680))
R.world_studio()
if "front" in views:
    R.lights_sheet((0, 0, zr(105) / 1000))
    R.cam_front_ortho((505.5 - 506.0) * K, zr(105), 182 * K, (728, 680))
    R.render(WORK + f"/rprev_{tag}_front.png")
    ref = np.load(WORK + "/ref_full.npy")[20:190, 415:597, :3]
    ours = tp_img.load(WORK + f"/rprev_{tag}_front.png")[..., :3]
    r4 = tp_img.resize(ref, 4, kind='linear')
    tp_img.save(WORK + f"/rprev_{tag}_sbs.png", np.concatenate([r4, np.ones((680, 8, 3)), ours], 1))
for o in list(bpy.data.objects):
    if o.type in ('LIGHT', 'CAMERA'):
        bpy.data.objects.remove(o)
if "q34" in views:
    zc = zr(100) / 1000
    a = math.radians(40)
    R.lights_sheet((0, 0, zc), rot_z=a)
    loc = Vector((0.40 * math.sin(a), -0.40 * math.cos(a), zc - 0.06))
    cd = bpy.data.cameras.new("c"); cd.lens = 85
    o = bpy.data.objects.new("c", cd); sc.collection.objects.link(o)
    d = (Vector((0, 0, zc)) - loc).normalized(); up = Vector((0, 0, -1))
    x = d.cross(up).normalized(); y = x.cross(d).normalized()
    o.matrix_world = Matrix.Translation(loc) @ Matrix((x, y, -d)).transposed().to_4x4(); sc.camera = o
    sc.render.resolution_x, sc.render.resolution_y = 800, 800
    R.render(WORK + f"/rprev_{tag}_q34.png")
# per-class display-luminance stats on the front view (classes from the traced relief, 1x reference grid)
if "front" in views:
    import json
    Zr = np.load(WORK + "/relief.npz"); CL = Zr["CLS"]; S_ = int(Zr["S"])
    cl1 = CL[S_ // 2::S_, S_ // 2::S_]                   # rows 26.., cols 415..
    ref1 = np.load(WORK + "/ref_full.npy")[26:178, 415:597, :3] @ np.array([0.2126, 0.7152, 0.0722])
    o4 = tp_img.load(WORK + f"/rprev_{tag}_front.png")[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
    o1 = o4.reshape(170, 4, 182, 4).mean((1, 3))[6:158]
    st = {}
    for k, nm in enumerate(["base", "silver", "enamel", "pearl"]):
        mk = cl1 == k
        mk[:16] = False
        st[nm] = {"ref": np.percentile(ref1[mk], [10, 50, 90]).round(3).tolist(), "ours": np.percentile(o1[mk], [10, 50, 90]).round(3).tolist()}
    print("CLASSSTATS", json.dumps(st))
