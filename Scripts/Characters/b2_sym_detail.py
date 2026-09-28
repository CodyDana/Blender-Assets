"""b2_sym_detail.py - PRIVATE / DO NOT SHIP. Grey-clay detail renders of the upper body (arms, elbows, neck), to check
the girth after the mirror average (never saves the blend).

  blender -b <rig blend> -P b2_sym_detail.py -- <abs out dir> <prefix>

Writes <prefix>_det_{front,back,side_l,tq}.png: orthographic, grey clay, one key sun from the camera side and above
plus a flat grey world. Garments stay on (clay coloured).
"""
import bpy, os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import enable_gpu, render_to  # noqa
from b2_sym_lib import log, argv  # noqa


def main():
    out, prefix = argv()[0], argv()[1]
    assert os.path.isabs(out), out
    os.makedirs(out, exist_ok=True)
    sc = bpy.context.scene
    enable_gpu()
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    for n in ("SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments"):
        bpy.data.objects[n].hide_render = False
    for o in bpy.data.objects:
        if o.type == 'LIGHT' or o.name == "RIG_Floor":
            o.hide_render = True
    sun_d = bpy.data.lights.new("DET_Sun", 'SUN'); sun_d.energy = 3.4; sun_d.angle = math.radians(6)
    sun = bpy.data.objects.new("DET_Sun", sun_d); sc.collection.objects.link(sun)
    cd = bpy.data.cameras.new("DET_Ortho"); cd.type = 'ORTHO'
    cam = bpy.data.objects.new("DET_Ortho", cd); sc.collection.objects.link(cam)
    sc.camera = cam
    world = sc.world
    if world and world.node_tree:
        wbg = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
        if wbg:
            wbg.inputs[0].default_value = (0.5, 0.5, 0.53, 1.0); wbg.inputs[1].default_value = 0.5
    clay = bpy.data.materials.new("DET_Clay")
    b = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.62, 0.62, 0.64, 1.0); b.inputs["Roughness"].default_value = 0.5
    bpy.context.view_layer.material_override = clay
    sc.render.resolution_x, sc.render.resolution_y = 1000, 1000
    cd.ortho_scale = 1.0
    ctr = (0.0, 0.0, 1.22)
    # (name, camera yaw deg: 0 = looking +Y at her front), sun comes from the camera side, 35 deg to its right, above
    done = []
    for name, yaw in (("front", 0.0), ("back", 180.0), ("side_l", -90.0), ("tq", -35.0)):
        a = math.radians(yaw)
        d = (math.sin(a), math.cos(a))  # viewing direction in XY
        cam.location = (ctr[0] - d[0] * 6, ctr[1] - d[1] * 6, ctr[2])
        cam.rotation_euler = (math.radians(90), 0.0, -a)
        sun.rotation_euler = (math.radians(55), 0.0, -a + math.radians(35))
        p = f"{out}/{prefix}_det_{name}.png"
        render_to(p); done.append(p)
    log("detail renders", done)


main()
