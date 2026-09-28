"""b2_sym_render.py - PRIVATE / DO NOT SHIP. BEFORE / AFTER symmetry renders of a 2B rig blend (never saves the blend).

  blender -b <rig blend> -P b2_sym_render.py -- <abs out dir> <prefix>

Writes <prefix>_front_ortho.png / _face_ortho.png (textured, orthographic front, camera on x = 0 so the image centre
column IS the midline x = 0), <prefix>_front_clay.png / _face_clay.png (uniform grey material, same cameras, for the
mirror-half comparison) and <prefix>_apose_tq.png (3/4 perspective with the step C1 render rig).
The ortho / clay shots use a symmetric light (a front sun on the x = 0 plane + a flat world) so a left/right
difference in the image is a difference in the model, not in the lighting. Garments stay visible in every shot.
"""
import bpy, os, sys, json, math
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import enable_gpu, frame_camera, view_dir, render_to, world_bbox  # noqa
from b2_sym_lib import log, argv, save_json  # noqa


def main():
    out, prefix = argv()[0], argv()[1]
    assert os.path.isabs(out), out
    os.makedirs(out, exist_ok=True)
    sc = bpy.context.scene
    enable_gpu()
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.film_transparent = False
    game = [bpy.data.objects[n] for n in ("SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments")]
    for o in game:
        o.hide_render = False
    rig_lights = [o for o in bpy.data.objects if o.type == 'LIGHT' and o.name.startswith("RIG_")]
    floor = bpy.data.objects.get("RIG_Floor")
    cam0 = sc.camera or bpy.data.objects["RIG_Camera"]
    done = []

    # ---------------------------------------------------------------- symmetric light + ortho camera
    sun_d = bpy.data.lights.new("SYM_Sun", 'SUN'); sun_d.energy = 3.2; sun_d.angle = math.radians(8)
    sun = bpy.data.objects.new("SYM_Sun", sun_d); sc.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(58), 0.0, 0.0)  # from the front (-Y), above, exactly in the x = 0 plane
    sun.hide_render = True
    cd = bpy.data.cameras.new("SYM_Ortho"); cd.type = 'ORTHO'
    cam = bpy.data.objects.new("SYM_Ortho", cd); sc.collection.objects.link(cam)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)  # looks along +Y at her front, image right = +X = her left
    world = sc.world
    wbg = None
    if world and world.node_tree:
        wbg = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
    old_bg = (tuple(wbg.inputs[0].default_value), wbg.inputs[1].default_value) if wbg else None
    clay = bpy.data.materials.new("SYM_Clay")
    b = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.62, 0.62, 0.64, 1.0); b.inputs["Roughness"].default_value = 0.55

    def sym_setup(on):
        for L in rig_lights:
            L.hide_render = on
        sun.hide_render = not on
        if wbg:
            if on:
                wbg.inputs[0].default_value = (0.55, 0.55, 0.58, 1.0); wbg.inputs[1].default_value = 0.55
            else:
                wbg.inputs[0].default_value = old_bg[0]; wbg.inputs[1].default_value = old_bg[1]

    shots = [("front", 900, 1600, 1.86, (0.0, -6.0, 0.855)), ("face", 900, 900, 0.30, (0.0, -6.0, 1.545))]
    sym_setup(True)
    sc.camera = cam
    for clay_on in (False, True):
        bpy.context.view_layer.material_override = clay if clay_on else None
        if floor:
            floor.hide_render = clay_on
        for name, w, h, osc, loc in shots:
            sc.render.resolution_x, sc.render.resolution_y = w, h
            cd.ortho_scale = osc
            cam.location = loc
            p = f"{out}/{prefix}_{name}_{'clay' if clay_on else 'ortho'}.png"
            render_to(p); done.append(p)
    bpy.context.view_layer.material_override = None
    if floor:
        floor.hide_render = False
    sym_setup(False)
    # ---------------------------------------------------------------- 3/4 A-pose, step C1 look
    sc.camera = cam0
    sc.render.resolution_x, sc.render.resolution_y = 800, 1100
    mn, mx = world_bbox(game)
    pts = [Vector((x, y, z)) for x in (mn.x, mx.x) for y in (mn.y, mx.y) for z in (mn.z, mx.z)]
    frame_camera(cam0, (mn + mx) / 2, view_dir("tq"), pts, 1.08)
    p = f"{out}/{prefix}_apose_tq.png"; render_to(p); done.append(p)
    frame_camera(cam0, (mn + mx) / 2, view_dir("front"), pts, 1.08)
    p = f"{out}/{prefix}_apose_front.png"; render_to(p); done.append(p)
    save_json(f"{out}/_{prefix}_renders.json", {"blend": bpy.data.filepath, "renders": done,
                                                 "ortho": {"front_scale_m": 1.86, "face_scale_m": 0.30,
                                                           "midline": "image centre column = x 0"}})
    log("renders", done)


main()
