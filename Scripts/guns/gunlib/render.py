"""Render helpers for gun reviews (import inside Blender): cameras matched to sheet panels, neutral grey and
studio (dark steel + reddish wood placeholder) looks, Workbench previews and Cycles stills.

Frames: objects live in frame B (metres) = (M - Grip) / 1000. Sheet-matched orthographic cameras are framed from the
panel's own px <-> mm mapping, so a render pixel lands on the same panel pixel as the trace.
"""
from __future__ import annotations

import math
from typing import Optional, Sequence

import bpy
import numpy as np
from mathutils import Matrix, Vector


def engine(sc, name, samples=64):
    if name == "WORKBENCH":
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = False
        sh.show_object_outline = False
        sc.display.render_aa = "16"
        return
    sc.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception:  # noqa: BLE001
        sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"


def principled(name, base, metallic=0.0, rough=0.5, spec=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*base, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*base, 1.0)
    return m


def srgb_to_lin(c):
    c = np.asarray(c, float) / 255.0
    return tuple(np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4))


def assign(objs, mat):
    for o in objs:
        if o.type != "MESH":
            continue
        o.data.materials.clear()
        o.data.materials.append(mat)


def world_flat(sc, rgb_lin=(0.5, 0.5, 0.5), strength=1.0, env=None):
    """Flat backdrop seen by the camera; with env set, everything else (lighting, reflections) sees the same colour
    at strength env (keeps the backdrop exact while the studio lights do the shaping)."""
    w = bpy.data.worlds.new("GunWorld")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (*rgb_lin, 1)
    bg.inputs["Strength"].default_value = strength
    if env is not None:
        out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
        bg2 = nt.nodes.new("ShaderNodeBackground")
        bg2.inputs["Color"].default_value = (*rgb_lin, 1)
        bg2.inputs["Strength"].default_value = env
        lp = nt.nodes.new("ShaderNodeLightPath")
        mix = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
        nt.links.new(bg2.outputs["Background"], mix.inputs[1])
        nt.links.new(bg.outputs["Background"], mix.inputs[2])
        nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return w


def area_light(name, loc, target, size, energy, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = energy
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def camera_object(name="Cam"):
    cd = bpy.data.cameras.new(name)
    ob = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera = ob
    return ob


def ortho_side(cam, sc, frame_s, frame_u, frame_p0, shape, grip_M, ss=1, side="right"):
    """Orthographic camera that reproduces a side panel's px <-> mm map (X along u, Z along n) for a W x H panel
    rendered at ss x resolution. side='right' looks from -Y (muzzle to screen right)."""
    H, W = shape
    s = frame_s
    u = np.array(frame_u, float)
    # panel centre (continuous coords) in mm
    cpx = np.array([W / 2.0 - 0.5, H / 2.0 - 0.5])
    d = cpx - np.array(frame_p0, float)
    n = np.array([u[1], -u[0]])
    Xc, Zc = d @ u / s, d @ n / s
    ang = math.atan2(u[1], u[0])          # image rotation of the bore (radians, image y down)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = W / s / 1000.0
    cam.data.sensor_fit = "HORIZONTAL"
    sc.render.resolution_x = W * ss
    sc.render.resolution_y = H * ss
    cB = (np.array([Xc, 0.0, Zc]) - grip_M) / 1000.0
    if side == "right":
        cam.location = (cB[0], -2.0, cB[2])
        R = Matrix.Rotation(math.radians(90), 4, "X")
        R = Matrix.Rotation(ang, 4, "Y") @ R          # bore tilt in the image (tiny)
    else:
        cam.location = (cB[0], 2.0, cB[2])
        R = Matrix.Rotation(math.radians(180), 4, "Z") @ Matrix.Rotation(math.radians(90), 4, "X")
    cam.rotation_euler = R.to_euler()
    cam.data.clip_start = 0.1
    cam.data.clip_end = 10.0


def ortho_top(cam, sc, frame_s, frame_u, frame_p0, shape, grip_M, ss=1):
    """Top panel: X along u, +Y (gun left) image-up."""
    H, W = shape
    s = frame_s
    u = np.array(frame_u, float)
    cpx = np.array([W / 2.0 - 0.5, H / 2.0 - 0.5])
    d = cpx - np.array(frame_p0, float)
    n = np.array([u[1], -u[0]])
    Xc, Yc = d @ u / s, d @ n / s
    ang = math.atan2(u[1], u[0])
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = W / s / 1000.0
    sc.render.resolution_x = W * ss
    sc.render.resolution_y = H * ss
    cB = (np.array([Xc, Yc, 0.0]) - grip_M) / 1000.0
    cam.location = (cB[0], cB[1], 2.0)
    cam.rotation_euler = (Matrix.Rotation(-ang, 4, "Z")).to_euler()
    cam.data.clip_start = 0.1
    cam.data.clip_end = 10.0


def persp_from_solve(cam, sc, camd, grip_M, shape, ss=1):
    """Blender camera from a camsolve.Camera dict (OpenCV axes in frame M)."""
    H, W = shape
    R = np.array(camd["R_rows_cam_axes_in_M"], float)
    C = (np.array(camd["centre_M_mm"], float) - grip_M) / 1000.0
    M = np.eye(4)
    M[:3, 0] = R[0]
    M[:3, 1] = -R[1]
    M[:3, 2] = -R[2]
    M[:3, 3] = C
    cam.matrix_world = Matrix(M.tolist())
    cam.data.type = "PERSP"
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = 36.0
    cam.data.lens = camd["f_px"] * 36.0 / W
    cam.data.shift_x = -(camd["cx"] - (W / 2.0 - 0.5)) / W
    cam.data.shift_y = (camd["cy"] - (H / 2.0 - 0.5)) / W
    sc.render.resolution_x = W * ss
    sc.render.resolution_y = H * ss
    cam.data.clip_start = 0.05
    cam.data.clip_end = 20.0


def still(sc, path, transparent=False):
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
