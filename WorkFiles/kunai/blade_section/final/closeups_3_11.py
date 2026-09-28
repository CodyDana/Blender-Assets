"""The kunai's two gallery close-ups (Renders/Shuriken/kunai_plain_grip_closeup.png = c03_grip_side_tight,
kunai_plain_neck_closeup.png = c04_neck_3q), re-rendered for the 3.11 section (review round 1: the Sep 19 files still
showed the 3.10.1 shoulder).

A port of the main chat's reviewer script closeups.py (2026-09-19, recovered verbatim from its session transcript; the
shipped close-ups were rendered by it as 'closeups_final.py' = SHIFT -20.5193, half_t 10.0 mm, 160 samples, from
Assets/Shuriken.blend).  Unchanged: the pack's own gallery rig (render.setup_render + build_preview_rig, hero lamps x the
hero's rig scale 2.724318), the cameras (shoot() below, same yaw / target / framing / lens / el 29 / az -22), the steel +
wrap preview materials from the baked maps, 1600 x 900.  Changed: the pivot is read from the kunai report
(measured.pivot_design_x_mm; 3.11: -19.5869), and the texture paths + lettering band from the report's own textures
block (the hard-coded 3.10.0 band rect is gone).  Opens the blend read-only (never saved).

  blender -b Assets/Shuriken.blend --factory-startup --python closeups_3_11.py -- <report.json> <out_dir> [samples] [shot ...]
"""
import sys, math, json
from pathlib import Path
import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
for p in (ROOT / "Scripts" / "shuriken", ROOT / "Scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
from shuriken_lib import render as RN       # noqa: E402
from shuriken_lib import bake as B          # noqa: E402
from shuriken_lib import kunai_wrap as KW   # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
REPORT = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
OUT = Path(argv[1]).resolve()   # absolute: Blender resolves a relative render path against the drive root
SAMPLES = int(argv[2]) if len(argv) > 2 else 160
ONLY = set(argv[3:])
OUT.mkdir(parents=True, exist_ok=True)
RES = (1600, 900)
MM = 0.001
SHIFT = float(REPORT["measured"]["pivot_design_x_mm"])


def ox(design_x_mm):               # design x -> object x (m)
    return (design_x_mm - SHIFT) * MM


class O:                           # the kunai's KunaiRenderInfo, as the rig reads it
    n = 2
    half_t = 10.0 * MM
    x_tip = ox(140.0)
    x_butt = ox(-140.0)
    r_tip = x_tip
    top_frame_height = 0.18
    top_centre_xy = (0.5 * (x_tip + x_butt), 0.0)
    a = 2.5 * MM

    def tip_extents(self):
        return self.x_tip - self.x_butt, 36.0 * MM


scene = bpy.context.scene
lod0 = bpy.data.objects["SM_Kunai_Plain_LOD0"]
for ob in bpy.data.objects:
    ob.hide_render = ob is not lod0

RN.setup_render(SAMPLES, *RES)
o = O()
rig = RN.build_preview_rig(o, RES[0], RES[1])
RIG_SCALE = 2.724318                # the 3.10.1 hero's render_rig.hero_rig_scale, as the shipped close-ups used
for light in rig["hero_lights"]:
    light.location = light.location * RIG_SCALE
    light.data.size *= RIG_SCALE
    light.data.size_y *= RIG_SCALE
    light.data.energy *= RIG_SCALE ** 2

tex = REPORT["textures"]
steel = B.preview_material("REVIEW_Steel", tex["maps"], uv_map=tex["uv_map"])
wrap = KW.wrap_preview_material(tex, name="REVIEW_Wrap")
lod0.data.materials[0] = steel
lod0.data.materials[1] = wrap

cam_data = bpy.data.cameras.new("REVIEW_Cam")
cam = bpy.data.objects.new("REVIEW_Cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
cam_data.dof.use_dof = False
cam_data.clip_start = 0.005


def polar_dir(el, az):
    e, a = math.radians(el), math.radians(az)
    return Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))


def shoot(name, yaw_deg, target_design_x, width_mm, el=29.0, az=-22.0, lens=100.0, lights="hero", ground=True,
          card=True, tz=0.0, ty=0.0):
    if ONLY and name not in ONLY:
        return
    lod0.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
    bpy.context.view_layer.update()
    target = lod0.matrix_world @ Vector((ox(target_design_x), ty, tz))
    d = width_mm * MM * lens / 36.0
    cam_data.lens = lens
    cam_data.sensor_width = 36.0
    cam.location = target + polar_dir(el, az) * d
    direction = target - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    use = rig["hero_lights"] if lights == "hero" else rig["top_lights"]
    for light in rig["hero_lights"] + rig["top_lights"]:
        light.hide_render = light not in use
    rig["ground"].hide_render = not ground
    rig["card"].hide_render = not card
    rig["band"].hide_render = True
    path = OUT / f"{name}.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("SHOT", name, path, flush=True)


shoot("c03_grip_side_tight", 68.0, -40.0, 55.0, lens=135.0)             # tape edges / weave / fray at ~29 px/mm
shoot("c04_neck_3q", 23.0, -2.0, 60.0, lens=135.0)                      # 3/4, shoulder + neck + front collar
print("DONE", json.dumps({"shift_design_x_mm": SHIFT, "samples": SAMPLES, "maps": tex["maps"]}))
