"""b2_rig_common.py - PRIVATE / DO NOT SHIP (2B private experiment, step C1: playable bare base).

Shared paths and helpers for the b2_rig_*.py stages. Blender 5.2, headless only.
Writes only inside WorkFiles/Characters/2B_private/.
"""
import bpy, os, sys, json, math, time
from mathutils import Vector, Matrix

ROOT = r"C:/Users/Cody/Desktop/Blender_Projects"
OUT = ROOT + "/WorkFiles/Characters/2B_private"
BASE_BLEND = OUT + "/2B_private_base.blend"          # step A result, read-only
MH_BLEND = ROOT + "/References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend"  # read-only
WORK = OUT + "/rig_work"                              # intermediate blends / json / debug renders
STAGE1 = WORK + "/c1_stage1_mesh.blend"
JOINTS = WORK + "/c1_joints_posed.json"
RIG_BLEND = OUT + "/2B_private_rig.blend"
RENDERS = OUT + "/rig_renders"
EXPORT_DIR = OUT + "/export"
FBX = EXPORT_DIR + "/SK_2B_Private.fbx"
REPORT = OUT + "/stepC1_report.json"

# welded skin shell surface order (index = value of the "src" face attribute, from b2_import_split.SHELL)
SHELL = ["Body", "Face", "Lips", "Head", "Ears", "Legs", "Arms", "Fingernails", "Toenails", "EyeSocket", "Mouth"]
EYE_PARTS = ["Sclera", "Irises", "Pupils", "Cornea", "EyeMoisture", "Tear"]

# bones kept from metahuman_base_skel (body bones actually needed by a retargeted player)
SPINE = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head"]
FINGERS = ["thumb", "index", "middle", "ring", "pinky"]


def side_bones(s):
    b = [f"clavicle_{s}", f"upperarm_{s}", f"lowerarm_{s}", f"hand_{s}"]
    for f in FINGERS:
        if f != "thumb":
            b.append(f"{f}_metacarpal_{s}")
        b += [f"{f}_0{i}_{s}" for i in (1, 2, 3)]
    b += [f"thigh_{s}", f"calf_{s}", f"foot_{s}", f"ball_{s}"]
    return b


KEEP = SPINE + side_bones("l") + side_bones("r")


def log(*a):
    print("[c1]", *a, flush=True)


def argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def tris_of(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def enable_gpu():
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for t in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = t
            prefs.get_devices()
            ok = False
            for d in prefs.devices:
                d.use = d.type != 'CPU'
                ok = ok or d.use
            if ok:
                bpy.context.scene.cycles.device = 'GPU'
                return t
        except Exception as e:  # noqa
            log("gpu", t, e)
    bpy.context.scene.cycles.device = 'CPU'
    return 'CPU'


def look_at(cam, target, direction, dist):
    d = Vector(direction).normalized()
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    cam.location = Vector(target) + d * dist


def frame_camera(cam, center, direction, pts, margin=1.06):
    """Perspective camera looking along -direction at center so all pts fit (from b2_import_split)."""
    sc = bpy.context.scene
    d = Vector(direction).normalized()
    rot = (-d).to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot.to_euler()
    R = rot.to_matrix()
    right = R @ Vector((1, 0, 0)); up = R @ Vector((0, 1, 0))
    cd = cam.data
    aspect = sc.render.resolution_x / sc.render.resolution_y
    fov_w = 2 * math.atan(cd.sensor_width / 2 / cd.lens)
    if aspect < 1:
        tan_v = math.tan(fov_w / 2); tan_h = tan_v * aspect
    else:
        tan_h = math.tan(fov_w / 2); tan_v = tan_h / aspect
    need = 0
    for p in pts:
        q = p - center
        x = q.dot(right); y = q.dot(up); z = q.dot(d)
        need = max(need, z + abs(x) * margin / tan_h, z + abs(y) * margin / tan_v)
    cam.location = center + d * need


def view_dir(view):
    ang = {"front": 0, "tq": 35, "side": 90, "back": 180, "rside": -90, "rtq": -35}[view]
    a = math.radians(ang)
    return Vector((math.sin(a), -math.cos(a), 0.0))  # character faces -Y, its left is +X


def render_to(path):
    bpy.context.scene.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    log("rendered", os.path.basename(path), round(time.time() - t, 1), "s")


def world_bbox(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9,) * 3); mx = Vector((-1e9,) * 3)
    for o in objs:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        for v in me.vertices:
            c = mw @ v.co
            for k in range(3):
                mn[k] = min(mn[k], c[k]); mx[k] = max(mx[k], c[k])
        ev.to_mesh_clear()
    return mn, mx


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)
