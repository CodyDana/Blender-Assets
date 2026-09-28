"""Iteration 1 patch (spike maintenance, 3.8.1): bar-mode speck damping (material) and hero placement for a
lens shift equal to the anchor forms' (render)."""
from pathlib import Path

root = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\shuriken_lib")
s = ""
name = ""


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:90], s.count(old))
    s = s.replace(old, new)


name = "material.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''    pits        (3.8.1) BAR_PIT_SCALE of the plate forms' pits (colour, roughness and normal depth): a
                bar's vertical side faces mirror the pale floor card beside them, where a pit's dent
                tilts the reflection off it and read as black pepper in the hero (8.3 dots / 10k px
                against the stars' 0.03-0.08 and the reference's 0.74)''',
    '''    specks      (3.8.1) the dirt specks and the pits at BAR_SPECK_SCALE / BAR_PIT_SCALE of the plate forms':
                on the hero's side face - seen nearly face-on at ~10 px/mm, where a star's plate is
                foreshortened to half - the 0.12-0.3 mm specks (50 % darker) rendered as round 2 px black
                pepper (8.3 dots / 10k px against the stars' plates' 0.03-0.08 and the reference's 0.74).
                A bar is C4 and seen from every side in the game, so the damping is on all four faces''')
rep('''BAR_PIT_SCALE = 0.33                   # 3.8.1: a bar's pits at a third of the plate forms' (colour, roughness, bump)''',
    '''BAR_PIT_SCALE = 0.33                   # 3.8.1: a bar's pits at a third of the plate forms' (colour, roughness, bump)
BAR_SPECK_SCALE = 0.35                 # 3.8.1: a bar's dirt specks darken at this fraction of the plate forms' SPECK''')
rep('''    specks = t.math("MULTIPLY", specks, t.math("MULTIPLY", plate, t.math("SUBTRACT", 1.0, bare)))''',
    '''    specks = t.math("MULTIPLY", specks, t.math("MULTIPLY", plate, t.math("SUBTRACT", 1.0, bare)))
    specks = t.math("MULTIPLY", specks, t.mix_f(mode, 1.0, BAR_SPECK_SCALE))    # 1 exactly on the plate forms''')
rep('''__all__ = ["ARRIS_BAND", "BAR_PIT_SCALE", "BAR_PROPS", "BAR_ROUND_ROUGHNESS",''',
    '''__all__ = ["ARRIS_BAND", "BAR_PIT_SCALE", "BAR_PROPS", "BAR_ROUND_ROUGHNESS", "BAR_SPECK_SCALE",''')
p.write_text(s, encoding="utf-8")

name = "render.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''  forms (scale 1, nothing touched) render exactly as before.  The lamps are restored after the hero.''',
    '''  forms (scale 1, nothing touched) render exactly as before.  The lamps are restored after the hero.
  Before that the object is slid on the floor (with its hero yaw, for the hero only) until the lens
  shift the framing needs equals the anchor forms' mean (HERO_SHIFT_TARGET): the yawed bar's near end
  projects larger, so centring it needed shift_x +0.067 against the stars' -0.036..+0.012, which moved
  the frame 0.1 of its width right, past the end of the key's floor reflection.''')
rep('''HERO_RIG_REFERENCE_M = 0.215697''', '''HERO_RIG_REFERENCE_M = 0.215697
# ... and slides the object on the floor until its framing needs this lens shift: the anchor forms' mean
# (render_rig.hero_composition.shift of the 3.8.0 build: four-point (-0.0356, -0.0273), eight-point
# (-0.0009, -0.0213), senban (-0.0356, -0.0273)).
HERO_SHIFT_TARGET = (-0.0240, -0.0253)''')
rep('''def solve_depth_of_field(camera, objects, res_x: int, max_coc_px: float = HERO_MAX_COC_PX,''',
    '''def place_for_shift(camera, obj, res_x: int, res_y: int, target=HERO_SHIFT_TARGET, steps: int = 6) -> dict:
    """Slide ``obj`` on the floor until the dolly fit + centring need the lens shift ``target`` (3.8.1).

    A shift of d frame widths moves the image by d; the object moved by d x W along the camera's
    (horizontal) right vector does the same, W the frame width at the camera's distance; a move of
    d x W / sin(elevation) along the horizontal view direction moves it up the frame by d.
    """
    info = {}
    for step in range(steps):
        fit_perspective(camera, [obj], 0.90, 0.86)
        info = centre_perspective(camera, [obj], res_x, res_y)
        dx, dy = camera.data.shift_x - target[0], camera.data.shift_y - target[1]
        if max(abs(dx), abs(dy)) < 0.001:
            break
        rot = camera.matrix_world.to_3x3()
        view = rot @ Vector((0.0, 0.0, -1.0))
        right = rot @ Vector((1.0, 0.0, 0.0))
        right.z = 0.0
        right.normalize()
        forward = Vector((view.x, view.y, 0.0)).normalized()
        elevation = math.asin(max(1e-3, -view.z))
        width = camera.location.length * camera.data.sensor_width / camera.data.lens
        obj.location = obj.location - right * (dx * width) - forward * (dy * width / math.sin(elevation))
        bpy.context.view_layer.update()
    info.update({"object_offset_mm": [round(v * 1000.0, 3) for v in obj.location], "target_shift": list(target),
                 "steps": step + 1})
    return info


def solve_depth_of_field(camera, objects, res_x: int, max_coc_px: float = HERO_MAX_COC_PX,''')
rep('''    saved_rotation = lod0.rotation_euler.copy()
    try:''', '''    saved_rotation = lod0.rotation_euler.copy()
    saved_location = lod0.location.copy()
    try:''')
rep('''        fit_perspective(rig["cam_persp"], [lod0], 0.90, 0.86)
        composition = centre_perspective(rig["cam_persp"], [lod0], res_x, res_y)
        dof = solve_depth_of_field(rig["cam_persp"], [lod0], res_x)
        rig_scale, saved_lamps = 1.0, []
        if getattr(o, "hero_rig_match", False):''', '''        fit_perspective(rig["cam_persp"], [lod0], 0.90, 0.86)
        composition = centre_perspective(rig["cam_persp"], [lod0], res_x, res_y)
        placement = None
        if getattr(o, "hero_rig_match", False):
            placement = place_for_shift(rig["cam_persp"], lod0, res_x, res_y)   # 3.8.1: the anchor forms' lens shift
            composition = centre_perspective(rig["cam_persp"], [lod0], res_x, res_y, steps=1)
        dof = solve_depth_of_field(rig["cam_persp"], [lod0], res_x)
        rig_scale, saved_lamps = 1.0, []
        if getattr(o, "hero_rig_match", False):''')
rep('''        if yaw:
            lod0.rotation_euler = saved_rotation
            bpy.context.view_layer.update()
        shoot(f"{form}_top"''', '''        if yaw or placement is not None:
            lod0.rotation_euler = saved_rotation
            lod0.location = saved_location
            bpy.context.view_layer.update()
        shoot(f"{form}_top"''')
rep('''            "hero_rig_scale": round(rig_scale, 6),''', '''            "hero_rig_scale": round(rig_scale, 6),
            "hero_placement": placement,''')
rep('''    finally:
        lod0.rotation_euler = saved_rotation''', '''    finally:
        lod0.rotation_euler = saved_rotation
        lod0.location = saved_location''')
p.write_text(s, encoding="utf-8")
print("iteration 1 patched")
