"""Trace pilot stage 6: renders of the pilot blend (traced throat LOD0 with its BAKED maps only + the r1 body copy).
    blender -b trace_pilot/SnowFlower_Sheath_TracePilot.blend --factory-startup --python tp_views.py -- [which...]
which: front (reference crop, 4x + full sheath 1x), q34l, q34r, side, back, top, hero  (default: all)"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import tp_render as R
from mathutils import Vector, Matrix

PILOT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot"
OUT = PILOT + "/renders"
os.makedirs(OUT, exist_ok=True)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
which = set(argv) if argv else {"front", "q34l", "q34r", "side", "back", "top", "hero"}
K = 0.687
def zr(row): return (row - 304.0) * K
SAMPLES = int(os.environ.get("TP_SAMPLES", "96"))
sc = bpy.context.scene


def clear_rig():
    for o in list(bpy.data.objects):
        if o.type in ('LIGHT', 'CAMERA'):
            bpy.data.objects.remove(o)


def cam_look_up(name, loc, target, up, lens=85.0):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_start = 0.005; cd.clip_end = 20
    o = bpy.data.objects.new(name, cd); sc.collection.objects.link(o)
    d = (Vector(target) - Vector(loc)).normalized(); up = Vector(up)
    x = d.cross(up).normalized(); y = x.cross(d).normalized()
    o.matrix_world = Matrix.Translation(loc) @ Matrix((x, y, -d)).transposed().to_4x4()
    sc.camera = o
    return o


R.settings(SAMPLES, (1000, 1000))
R.world_studio()
zc = zr(108) / 1000.0
C = Vector((0, 0, zc))

if "front" in which:
    clear_rig()
    R.lights_sheet((0, 0, zr(105) / 1000))
    R.cam_front_ortho((505.5 - 506.0) * K, zr(105), 182 * K, (728, 680))
    R.render(OUT + "/front_throat_x4.png")
    clear_rig()
    R.lights_sheet((0, 0, zr(767.5) / 1000), size=1.0)
    R.cam_front_ortho((505.5 - 512.0) * K, zr(768), 1024 * K, (1024, 1536))
    R.render(OUT + "/front_full_ref_scale.png")

def turntable(tag, az_deg, dist=0.40, elev=0.035, lens=85):
    clear_rig()
    a = math.radians(az_deg)
    R.lights_sheet((0, 0, zc), rot_z=a)
    loc = (dist * math.sin(a), -dist * math.cos(a), zc - elev)
    cam_look_up(tag, loc, (0, 0, zc), (0, 0, -1), lens)
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1000
    R.render(OUT + f"/{tag}.png")

if "q34l" in which: turntable("q34_left", 45)
if "q34r" in which: turntable("q34_right", -45)
if "side" in which: turntable("side", 90)
if "back" in which: turntable("back", 180)
if "top" in which:
    clear_rig()
    zm = zr(31) / 1000
    R.lights_sheet((0, 0, zm), rot_z=0.0)
    R.area("TopKey", (-0.3, -0.4, zm - 0.9), (0, 0, zm), 260, 1.0)
    cam_look_up("top_down", (0, -0.07, zm - 0.30), (0, 0.0, zm + 0.005), (0, 1, 0), 70)
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1000
    R.render(OUT + "/top_down_mouth.png")
if "hero" in which:
    clear_rig()
    zb = zr(88) / 1000
    # raking light: one small hard key skimming the front from the +X side, very low fill
    R.area("RakeKey", (0.34, -0.06, zb - 0.05), (0, -0.01, zb), 160, 0.05)
    R.area("Fill", (-0.5, -0.8, zb - 0.2), (0, 0, zb), 25, 1.5, (0.9, 0.95, 1.0))
    R.area("Rim", (-0.2, 0.6, zb - 0.4), (0, 0, zb), 80, 1.0)
    w = sc.world.node_tree.nodes
    for n in w:
        if n.type == 'BACKGROUND' and n.inputs["Strength"].default_value == 1.0 and not n.inputs["Color"].is_linked:
            n.inputs["Color"].default_value = (0.08, 0.085, 0.095, 1)
    a = math.radians(28)
    cam_look_up("hero", (0.2 * math.sin(a), -0.2 * math.cos(a), zb - 0.04), (0.0, -0.012, zb + 0.004), (0, 0, -1), 100)
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
    R.render(OUT + "/hero_closeup_raking.png")
