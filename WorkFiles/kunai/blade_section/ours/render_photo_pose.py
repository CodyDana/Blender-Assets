"""Render SM_Kunai_Plain LOD0 in the reference photo's pose (kunai blade-section study, phase 1).

Headless only, never saves the .blend it opens:

  blender.exe -b --factory-startup --python render_photo_pose.py -- --blend <copy.blend> --out <out.png> [options]

Options
  --blend PATH          a COPY of Assets/Shuriken.blend (or an option prototype); opened read-only, never saved
  --out PATH            output PNG (RGBA, film transparent; composite later).  A sidecar <out>.json holds the camera,
                        the pose and the projected key points (pixel coords) for the measurement procedure.
  --object NAME         default SM_Kunai_Plain_LOD0
  --mode gallery|validate
                        gallery : the shipped look - T_<stem>_BC/_ORM/_N on slot 0, the wrap maps + sheen on slot 1
                                  (the gallery's preview materials, rebuilt here; nothing imported from Scripts/)
                        validate: one uniform metal on the steel + a round-section probe torus (the photo measurers
                                  used the photo's ring as a round-tube light probe; our shipped ring is a flat forged
                                  ring, so the validation adds a true round tube of known material)
  --tex-dir DIR         baked maps folder (default: the live Exports/Shuriken/Textures, read only)
  --steel-stem STEM     default T_Kunai_Plain ; --wrap-stem default T_Kunai_Wrap
  --zscale K            scale the object's thickness (local Z) by K (validation: a known steeper section)
  --probe-albedo A      validate: probe base colour (blade is 0.60); default 0.60
  --roll DEG            roll about the kunai axis (+ = top edge away from camera, upper facet toward the sky); 5.0
  --inplane DEG         image-plane angle of the axis (tip rising to the right); 23.8
  --pitch DEG           tip toward (+) / away from the camera; 0
  --res W H             default 1000 666 (2x the 500x333 photo; the photo's framing is reproduced at this scale)
  --samples N           default 256
  --focal MM            default 200 (the photo is a long lens; the procedure assumes orthographic)

The pose (reconciled from the two blind photo measurers and this stage's re-measurement, see
WorkFiles/kunai/blade_section/ours/photo_reconciled.json): the blade is seen nearly FACE-ON - roll +5 deg (A 2 +-4, B 4.9
[-4, 10], ours 3-12 depending on the ridge-offset estimator), axis rising to the right at 23.8 deg, no pitch.  The photo's ring reads
0.92 elliptical, but a 23 deg roll is rejected by the facet shading (both measurers), so the photo's ring is taken to be
oval/twisted - ours is circular and is NOT forced to match the photo's ellipse.

Framing: the photo's shoulder (262.7, 176.9) and its extrapolated tip (428.2, 103.8) on the 500x333 frame, i.e. 180.9 px
for the 140 mm shoulder->tip; the render reproduces that at --res scale.

Lighting (a photo-like outdoor environment, all in the WORLD so it is distant and the matcap assumption holds): an
overcast sky above a dark forest horizon (+6 deg, 4 deg soft) and a broad soft key from the upper LEFT behind the camera,
which is what the photo's ring shows (its upper-left rim carries the highlight) and what splits the ridge: upper facets
lit, lower facets dark.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

LIVE_TEX = "C:/Users/Cody/Desktop/Blender_Projects/Exports/Shuriken/Textures"
PHOTO = {"w": 500, "h": 333, "shoulder": (262.727, 176.862), "tip": (428.198, 103.802)}   # measurer A's fit
DESIGN_TIP = 0.140


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--blend", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--object", default="SM_Kunai_Plain_LOD0")
    p.add_argument("--mode", default="gallery", choices=("gallery", "validate"))
    p.add_argument("--tex-dir", default=LIVE_TEX)
    p.add_argument("--steel-stem", default="T_Kunai_Plain")
    p.add_argument("--wrap-stem", default="T_Kunai_Wrap")
    p.add_argument("--zscale", type=float, default=1.0)
    p.add_argument("--probe-albedo", type=float, default=0.60)
    p.add_argument("--blade-albedo", type=float, default=0.60)
    p.add_argument("--roughness", type=float, default=0.35)
    p.add_argument("--roll", type=float, default=5.0)
    p.add_argument("--inplane", type=float, default=23.8)
    p.add_argument("--pitch", type=float, default=0.0)
    p.add_argument("--res", type=int, nargs=2, default=(1000, 666))
    p.add_argument("--samples", type=int, default=256)
    p.add_argument("--focal", type=float, default=200.0)
    p.add_argument("--exposure", type=float, default=None, help="view exposure (default: gallery 0.6, validate 0)")
    p.add_argument("--ridge", default="5.0,1.6,135.0",
                   help="design ridge THICKNESS: base mm (to x 35), tip mm, tip_at x mm - for the projected ridge line "
                        "in the sidecar only (options A/B/C pass their own)")
    p.add_argument("--cpu", action="store_true")
    return p.parse_args(argv)


# ----------------------------------------------------------------------------------------------- materials
def _img(path, colour):
    im = bpy.data.images.load(str(path), check_existing=False)
    im.colorspace_settings.name = colour
    return im


def _data_space():
    for name in ("Non-Color", "Non-Colour Data", "Raw"):
        try:
            bpy.data.images.new("_probe_cs", 4, 4).colorspace_settings.name = name
            return name
        except TypeError:
            continue
    return "Non-Color"


def baked_material(name, bc, orm, nrm, uv_map="UVMap", sheen=None):
    """Same graph as shuriken_lib.bake.preview_material (+ the wrap preview's sheen): BC sRGB -> base, ORM G -> rough,
    ORM B -> metal, N (DirectX, green flipped) -> tangent normal map.  AO unused (Cycles computes it)."""
    ds = _data_space()
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    t = mat.node_tree
    t.nodes.clear()
    new, link = t.nodes.new, t.links.new
    out = new("ShaderNodeOutputMaterial")
    bsdf = new("ShaderNodeBsdfPrincipled")
    link(bsdf.outputs["BSDF"], out.inputs["Surface"])
    uv = new("ShaderNodeUVMap")
    uv.uv_map = uv_map

    def tex(path, cs):
        n = new("ShaderNodeTexImage")
        n.image = _img(path, cs)
        n.interpolation = "Linear"
        link(uv.outputs["UV"], n.inputs["Vector"])
        return n
    link(tex(bc, "sRGB").outputs["Color"], bsdf.inputs["Base Color"])
    o = tex(orm, ds)
    sp = new("ShaderNodeSeparateColor")
    link(o.outputs["Color"], sp.inputs["Color"])
    link(sp.outputs["Green"], bsdf.inputs["Roughness"])
    link(sp.outputs["Blue"], bsdf.inputs["Metallic"])
    nn = tex(nrm, ds)
    ns = new("ShaderNodeSeparateColor")
    link(nn.outputs["Color"], ns.inputs["Color"])
    flip = new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1.0
    link(ns.outputs["Green"], flip.inputs[1])
    nc = new("ShaderNodeCombineColor")
    link(ns.outputs["Red"], nc.inputs["Red"])
    link(flip.outputs["Value"], nc.inputs["Green"])
    link(ns.outputs["Blue"], nc.inputs["Blue"])
    nm = new("ShaderNodeNormalMap")
    nm.space = "TANGENT"
    nm.uv_map = uv_map
    link(nc.outputs["Color"], nm.inputs["Color"])
    link(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if sheen:
        for k, v in (("Sheen Weight", sheen), ("Sheen Roughness", 0.35)):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = v
        if "Sheen Tint" in bsdf.inputs:
            bsdf.inputs["Sheen Tint"].default_value = (0.62, 0.60, 0.56, 1.0)
    return mat


def flat_metal(name, albedo, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (albedo, albedo, albedo, 1.0)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    return mat


def flat_dielectric(name, albedo, rough):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (albedo, albedo * 0.97, albedo * 0.93, 1.0)
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Roughness"].default_value = rough
    return mat


# ----------------------------------------------------------------------------------------------- world
def photo_world():
    """Distant lighting: overcast sky above a dark forest horizon (+6 deg, soft 4 deg) and a broad key blob from the
    upper left behind the camera (camera at -Y looking +Y, up +Z)."""
    w = bpy.data.worlds.new("W_PhotoPose")
    bpy.context.scene.world = w
    w.use_nodes = True
    t = w.node_tree
    t.nodes.clear()
    new, link = t.nodes.new, t.links.new
    out = new("ShaderNodeOutputWorld")
    bg = new("ShaderNodeBackground")
    link(bg.outputs["Background"], out.inputs["Surface"])
    tc = new("ShaderNodeTexCoord")
    nrm = new("ShaderNodeVectorMath")
    nrm.operation = "NORMALIZE"
    link(tc.outputs["Generated"], nrm.inputs[0])
    sep = new("ShaderNodeSeparateXYZ")
    link(nrm.outputs["Vector"], sep.inputs["Vector"])
    # sky / ground split on elevation
    horizon = new("ShaderNodeMapRange")
    horizon.interpolation_type = "SMOOTHSTEP"
    horizon.inputs["From Min"].default_value = math.sin(math.radians(2.0))
    horizon.inputs["From Max"].default_value = math.sin(math.radians(10.0))
    link(sep.outputs["Z"], horizon.inputs["Value"])
    # sky brightens a little toward the zenith
    zen = new("ShaderNodeMapRange")
    zen.inputs["From Min"].default_value = 0.0
    zen.inputs["From Max"].default_value = 1.0
    zen.inputs["To Min"].default_value = 0.55
    zen.inputs["To Max"].default_value = 1.0
    link(sep.outputs["Z"], zen.inputs["Value"])
    sky = new("ShaderNodeMath")
    sky.operation = "MULTIPLY"
    link(horizon.outputs["Result"], sky.inputs[0])
    link(zen.outputs["Result"], sky.inputs[1])
    # key blob: upper left, behind the camera
    kd = Vector((-0.55, -0.55, 0.62)).normalized()
    dot = new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    link(nrm.outputs["Vector"], dot.inputs[0])
    dot.inputs[1].default_value = tuple(kd)
    key = new("ShaderNodeMapRange")
    key.interpolation_type = "SMOOTHSTEP"
    key.inputs["From Min"].default_value = math.cos(math.radians(40.0))
    key.inputs["From Max"].default_value = 1.0
    link(dot.outputs["Value"], key.inputs["Value"])
    kmul = new("ShaderNodeMath")
    kmul.operation = "MULTIPLY"
    kmul.inputs[1].default_value = 2.2
    link(key.outputs["Result"], kmul.inputs[0])
    tot = new("ShaderNodeMath")
    tot.operation = "ADD"
    link(sky.outputs[0], tot.inputs[0])
    link(kmul.outputs[0], tot.inputs[1])
    ground = new("ShaderNodeMath")
    ground.operation = "ADD"
    ground.inputs[1].default_value = 0.035          # dark forest floor / trunks
    link(tot.outputs[0], ground.inputs[0])
    col = new("ShaderNodeMix")
    col.data_type = "RGBA"
    col.inputs["Factor"].default_value = 1.0
    col.inputs[6].default_value = (0, 0, 0, 1)
    col.inputs[7].default_value = (0.92, 0.95, 1.0, 1.0)
    rgb = new("ShaderNodeCombineColor")
    link(ground.outputs[0], rgb.inputs["Red"])
    link(ground.outputs[0], rgb.inputs["Green"])
    link(ground.outputs[0], rgb.inputs["Blue"])
    tint = new("ShaderNodeMix")
    tint.data_type = "RGBA"
    tint.blend_type = "MULTIPLY"
    tint.inputs["Factor"].default_value = 1.0
    link(rgb.outputs["Color"], tint.inputs[6])
    tint.inputs[7].default_value = (0.96, 0.97, 1.0, 1.0)
    link(tint.outputs[2], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    return {"horizon_deg": [2.0, 10.0], "key_dir": list(kd), "key_halfangle_deg": 40.0, "key_gain": 2.2,
            "ground": 0.035}


# ----------------------------------------------------------------------------------------------- pose
def pose_matrix(roll, inplane, pitch):
    """Object frame (X tip, Y across, Z thickness toward the camera) -> world.  Camera at -Y looking +Y, up +Z."""
    m0 = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))          # columns: X->X, Y->Z(up), Z->-Y (toward camera)
    r_roll = Matrix.Rotation(math.radians(-roll), 3, "X")    # + roll: the camera-facing normal tilts up
    r_pitch = Matrix.Rotation(math.radians(pitch), 3, "Z")   # + pitch: tip toward the camera
    r_in = Matrix.Rotation(math.radians(-inplane), 3, "Y")   # tip rises to the right
    return r_in @ r_pitch @ r_roll @ m0


def main():
    a = parse()
    bpy.ops.wm.open_mainfile(filepath=a.blend, load_ui=False)
    scene = bpy.context.scene
    obj = bpy.data.objects[a.object]
    shift = float(obj.get("kunai_shift_m", -0.0205193))
    # isolate: only the chosen object renders
    for o in scene.objects:
        o.hide_render = True
    obj.hide_render = False
    obj.hide_viewport = False
    for c in bpy.data.collections:
        c.hide_render = False
    mw = obj.matrix_world.copy()
    obj.parent = None
    R = pose_matrix(a.roll, a.inplane, a.pitch)
    S = Matrix.Diagonal((1.0, 1.0, a.zscale))
    obj.matrix_world = R.to_4x4() @ S.to_4x4()

    if a.mode == "gallery":
        td = Path(a.tex_dir)
        steel = baked_material("M_PP_Steel", td / f"{a.steel_stem}_BC.png", td / f"{a.steel_stem}_ORM.png",
                               td / f"{a.steel_stem}_N.png")
        wrap = baked_material("M_PP_Wrap", td / f"{a.wrap_stem}_BC.png", td / f"{a.wrap_stem}_ORM.png",
                              td / f"{a.wrap_stem}_N.png", sheen=0.35)
        mats = [steel, wrap]
    else:
        mats = [flat_metal("M_PP_Steel", a.blade_albedo, a.roughness), flat_dielectric("M_PP_Wrap", 0.05, 0.8)]
    obj.data.materials.clear()
    for m in mats:
        obj.data.materials.append(m)

    world_info = photo_world()

    # camera: long lens, framing from the photo (shoulder + tip), scaled to --res
    W, H = a.res
    k = W / PHOTO["w"]
    px_per_m = k * math.dist(PHOTO["shoulder"], PHOTO["tip"]) / DESIGN_TIP
    cam_d = bpy.data.cameras.new("PP_Cam")
    cam_d.lens = a.focal
    cam_d.sensor_fit = "HORIZONTAL"
    cam_d.sensor_width = 36.0
    cam = bpy.data.objects.new("PP_Cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    dist = (a.focal / 36.0) * W / px_per_m
    shoulder_w = obj.matrix_world @ Vector((0.0 - shift, 0.0, 0.0))      # design x = 0 -> object x = -shift
    sx, sy = PHOTO["shoulder"][0] * k, PHOTO["shoulder"][1] * k
    cam.location = (shoulder_w.x - (sx - W / 2) / px_per_m, shoulder_w.y - dist, shoulder_w.z + (sy - H / 2) / px_per_m)
    cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)

    probe = None
    if a.mode == "validate":
        # a round-section torus (R 13 mm, tube r 3 mm) in the blade plane, lower right of the frame, same distance
        bpy.ops.mesh.primitive_torus_add(major_radius=0.013, minor_radius=0.003, major_segments=128,
                                         minor_segments=48)
        probe = bpy.context.active_object
        probe.name = "PP_Probe"
        bpy.ops.object.shade_smooth()
        px, py = 0.80 * W, 0.78 * H
        centre = Vector((cam.location.x + (px - W / 2) / px_per_m, shoulder_w.y,
                         cam.location.z - (py - H / 2) / px_per_m))
        probe.matrix_world = Matrix.Translation(centre) @ (R @ Matrix(((1, 0, 0), (0, 1, 0), (0, 0, 1)))).to_4x4()
        probe.data.materials.append(flat_metal("M_PP_Probe", a.probe_albedo, a.roughness))
        probe.hide_render = False

    r = scene.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = W, H
    r.resolution_percentage = 100
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = a.exposure if a.exposure is not None else (0.6 if a.mode == "gallery" else 0.0)
    scene.cycles.samples = a.samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    if not a.cpu:
        try:
            prefs = bpy.context.preferences.addons["cycles"].preferences
            prefs.compute_device_type = "OPTIX"
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            scene.cycles.device = "GPU"
        except Exception as e:  # noqa: BLE001
            print("GPU setup failed, CPU:", e)
    r.filepath = a.out
    bpy.context.view_layer.update()

    # projected key points (design mm -> object -> world -> pixel, y down)
    from bpy_extras.object_utils import world_to_camera_view

    def px(design_xyz_mm):
        x, y, z = design_xyz_mm
        wp = obj.matrix_world @ Vector((x / 1000.0 - shift, y / 1000.0, z / 1000.0))
        c = world_to_camera_view(scene, cam, wp)
        return [c.x * W, (1.0 - c.y) * H]

    def hb(x):
        if x <= 35.0:
            return 8.0 + 10.0 * x / 35.0
        u = (x - 35.0) / 105.0
        return 18.0 * (1.0 - u) * (1.0 + 0.25 * u)
    pts = {"shoulder_axis": px((0, 0, 0)), "shoulder_top": px((0, 8.0, 0)), "shoulder_bot": px((0, -8.0, 0)),
           "top_corner": px((35.0, 18.0, 0)), "bot_corner": px((35.0, -18.0, 0)), "J": px((35.0, 0, 0)),
           "tip": px((140.0, 0, 0)), "ring_centre": px((-124.0, 0, 0))}
    edge_top = [[x, *px((x, hb(x), 0))] for x in range(0, 141, 5)]
    edge_bot = [[x, *px((x, -hb(x), 0))] for x in range(0, 141, 5)]
    rb, rt, rat = (float(v) for v in a.ridge.split(","))

    def ridge_half(x):   # design ridge half-thickness (kunai_spec ridge_blade), before --zscale (the matrix applies it)
        t = rb if x <= 35.0 else max(rt, rb + (rt - rb) * (x - 35.0) / (rat - 35.0))
        return 0.5 * t
    ridge_top = [[x, *px((x, 0.0, ridge_half(x)))] for x in range(0, 141, 5)]
    axis_dir = Vector(pts["tip"]) - Vector(pts["shoulder_axis"])
    meta = {"args": vars(a), "shift_m": shift, "px_per_m": px_per_m, "camera_distance_m": dist,
            "camera_location": list(cam.location), "pose_matrix": [list(r_) for r_ in R],
            "points_px": pts, "ridge_top_px": ridge_top, "edge_top_px": edge_top, "edge_bot_px": edge_bot,
            "axis_angle_img_deg": math.degrees(math.atan2(axis_dir.y, axis_dir.x)), "world": world_info}
    if probe is not None:
        # probe centreline ellipse in the image: sample the torus centre circle and the tube's outer/inner
        pc = []
        for i in range(72):
            t = 2 * math.pi * i / 72
            wp = probe.matrix_world @ Vector((0.013 * math.cos(t), 0.013 * math.sin(t), 0.0))
            c = world_to_camera_view(scene, cam, wp)
            pc.append([c.x * W, (1.0 - c.y) * H])
        cc = world_to_camera_view(scene, cam, probe.matrix_world.translation)
        meta["probe"] = {"centre_px": [cc.x * W, (1.0 - cc.y) * H], "centreline_px": pc,
                         "tube_r_px": 0.003 * px_per_m, "ring_r_px": 0.013 * px_per_m}
    bpy.ops.render.render(write_still=True)
    Path(a.out + ".json").write_text(json.dumps(meta, indent=1))
    print("RENDERED", a.out)


main()
