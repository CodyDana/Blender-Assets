"""Trace pilot - render helpers (studio close to the reference sheet: white backdrop seen by the camera, grey-gradient
reflection environment, soft key from the upper left, two vertical strip boxes, low fill, rim).  Numbers follow the
round-1 look-match studio (Scripts_v4/shv4_render.py) so renders are comparable with the failed rounds."""
import bpy, math, os
import numpy as np
from mathutils import Matrix, Vector

K = 0.687
LIGHT_SCALE = 0.25


def settings(samples=64, res=(1024, 1024), transparent=False):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = 'CPU'
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = float(os.environ.get("TP_EXPOSURE", "-0.35"))
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    sc.cycles.max_bounces = 8
    sc.cycles.glossy_bounces = 4


def world_studio(bg=(1, 1, 1), env_top=0.7, env_mid=0.05, env_bot=0.03, strength=1.0):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("TP_Studio"); sc.world = w
    w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld"); lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader"); bgc = nt.nodes.new("ShaderNodeBackground")
    bgc.inputs["Color"].default_value = (*bg, 1)
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (env_bot, env_bot, env_bot * 1.05, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (env_top, env_top, env_top, 1)
    m = ramp.color_ramp.elements.new(0.55); m.color = (env_mid, env_mid, env_mid * 1.03, 1)
    # v2: the sheath frame has +Z toward the chape (DOWN in every view), so the bright part of the gradient goes to -Z
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 1.0; mr.inputs["From Max"].default_value = -1.0
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    env = nt.nodes.new("ShaderNodeBackground"); env.inputs["Strength"].default_value = strength
    nt.links.new(ramp.outputs["Color"], env.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(env.outputs[0], mix.inputs[1]); nt.links.new(bgc.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])


def area(name, loc, target, power, size, color=(1, 1, 1), size_y=None):
    l = bpy.data.lights.new(name, "AREA")
    if size_y is not None:
        l.shape = "RECTANGLE"; l.size = size; l.size_y = size_y
    else:
        l.size = size
    l.energy = power * LIGHT_SCALE; l.color = color
    o = bpy.data.objects.new(name, l); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def lights_sheet(center, size=1.0, rot_z=0.0, key=300.0, strip=45.0):
    """center (m).  rot_z rotates the whole rig about the sheath axis (for the non-front views the light stays
    attached to the camera side, like a photographer's turntable)."""
    c = Vector(center)
    R = Matrix.Rotation(rot_z, 4, 'Z')
    def P(v): return c + (R @ Vector(v))
    # v2: key from the viewer's UPPER LEFT like the reference sheet (+X = viewer's left, -Z = up in the front view);
    # the v1 rig had it at (-1.2, -1.3, +1.0) = lower right
    objs = [area("Key", P((1.2, -1.3, -1.0)), c, key, 0.6 * size, (1.0, 0.99, 0.97)),
            area("StripL", P((-0.9, -1.0, 0.0)), c, strip, 0.12 * size, size_y=2.4 * size),
            area("StripR", P((0.9, -1.0, 0.0)), c, 0.75 * strip, 0.12 * size, size_y=2.4 * size),
            area("Fill", P((-0.8, -1.6, 0.4)), c, 15, 1.6 * size, (0.92, 0.95, 1.0)),
            area("Rim", P((0.3, 1.6, 0.6)), c, 120, 1.4 * size)]
    return objs


def cam_front_ortho(xc_mm, zc_mm, width_mm, res):
    """Reference front view: looking along +Y, image up = -Z (mouth up), image right = -X."""
    cd = bpy.data.cameras.new("front"); cd.type = 'ORTHO'; cd.ortho_scale = width_mm / 1000.0
    cd.clip_start = 0.01; cd.clip_end = 10
    o = bpy.data.objects.new("CamFront", cd); bpy.context.scene.collection.objects.link(o)
    Rm = Matrix(((-1, 0, 0), (0, 0, -1), (0, -1, 0)))
    o.matrix_world = Matrix.Translation((xc_mm / 1000, -1.0, zc_mm / 1000)) @ Rm.to_4x4()
    bpy.context.scene.camera = o
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = res
    return o


def cam_look(name, loc_m, target_m, lens=85.0, ortho_mm=None):
    cd = bpy.data.cameras.new(name)
    if ortho_mm:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho_mm / 1000.0
    else:
        cd.lens = lens
    cd.clip_start = 0.005; cd.clip_end = 20
    o = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(o)
    o.location = loc_m
    # up = -Z world (mouth up in every view)
    d = (Vector(target_m) - Vector(loc_m)).normalized()
    up = Vector((0, 0, -1))
    x = d.cross(up).normalized(); y = x.cross(d).normalized()
    Rm = Matrix((x, y, -d)).transposed()
    o.matrix_world = Matrix.Translation(loc_m) @ Rm.to_4x4()
    bpy.context.scene.camera = o
    return o


def render(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
