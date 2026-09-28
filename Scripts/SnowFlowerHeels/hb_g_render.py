"""Stage G: deliverable renders from the BAKED game mesh (SK_SnowFlowerHeels LODs, baked BC/ORM/N), posed by the
heel-pose correction on the rest-bound skeleton.

    blender -b Assets/SnowFlowerHeels/SnowFlowerHeels_Build.blend --factory-startup --python Scripts/SnowFlowerHeels/hb_g_render.py -- [--samples 128] [--tag r1]

Writes Renders/SnowFlowerHeels/:
  <tag>_refcam_viewA.png        right shoe, reference camera (white studio)
  <tag>_side_by_side_viewA.png  reference | render | 50 % overlay
  <tag>_pair_34.png, <tag>_pair_side.png, <tag>_pair_back.png, <tag>_pair_top.png   both shoes
  <tag>_worn_34.png, <tag>_worn_side.png        on her posed feet
  <tag>_lod_strip.png           LOD0 / LOD1 / LOD2 at the same framing
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import hb_common as C  # noqa: E402
import hb_camrender as CR  # noqa: E402
import hb_look as LK  # noqa: E402
import metro_png as P  # noqa: E402
from pipeline import garment_qa as gq  # noqa: E402
from SnowFlowerHeels.heel_pose import apply_heel_pose, load_pose  # noqa: E402


def only_side(src, side, name):
    c = src.copy()
    c.data = src.data.copy()
    c.name = name
    bpy.context.scene.collection.objects.link(c)
    bm = bmesh.new()
    bm.from_mesh(c.data)
    sgn = -1 if side == "r" else 1
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.x * sgn < 0], context="VERTS")
    bm.to_mesh(c.data)
    bm.free()
    return c


def render(path, samples):
    sc = bpy.context.scene
    sc.render.filepath = str(path)
    sc.cycles.samples = samples
    bpy.ops.render.render(write_still=True)


def white(path_rgba, path_out):
    return LK.composite_white(path_rgba, path_out)


def cam_look(ob_cam, loc, target, ortho=None, lens=85):
    ob_cam.location = loc
    d = Vector(target) - Vector(loc)
    ob_cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    if ortho:
        ob_cam.data.type = "ORTHO"
        ob_cam.data.ortho_scale = ortho
    else:
        ob_cam.data.type = "PERSP"
        ob_cam.data.lens = lens
    ob_cam.data.clip_start = 0.01
    ob_cam.data.clip_end = 20


def clear_lights():
    for o in list(bpy.data.objects):
        if o.type == "LIGHT":
            bpy.data.objects.remove(o, do_unlink=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    samples = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 128
    tag = argv[argv.index("--tag") + 1] if "--tag" in argv else "r1"
    out = C.RENDER_DIR
    out.mkdir(parents=True, exist_ok=True)
    sc = bpy.context.scene
    LK.studio(sc, samples)
    lock = gq.load_base_lock("MH_PlayerFemale")
    arm = bpy.data.objects[lock["armature_object"]]
    feet, params = load_pose()
    apply_heel_pose(arm, feet, params)
    bpy.context.view_layer.update()
    # hide everything, then show what each shot needs
    for o in bpy.data.objects:
        o.hide_render = True
    lods = [bpy.data.objects[n] for n in ("SK_SnowFlowerHeels", "SK_SnowFlowerHeels_LOD1", "SK_SnowFlowerHeels_LOD2")]
    right = only_side(lods[0], "r", "RENDER_R")
    right.hide_render = False
    plane = LK.shadow_catcher()
    plane.location = (0, -0.1, 0)
    plane.hide_render = False
    # ---- reference camera, right shoe
    cam = CR.load_cam()
    L = C.local_matrix("r")
    CR.setup_camera(cam, L)
    center = C.local_to_world(np.array([110.0, 5.0, 100.0]), "r")
    cdir, right_v, up_v = cam.basis()
    Rw = L[:3, :3] * 1000.0
    LK.lights_for_cam((Rw @ cdir, Rw @ right_v, Rw @ up_v), tuple(center))
    rp = out / f"{tag}_refcam_viewA_rgba.png"
    render(rp, samples)
    white(rp, out / f"{tag}_refcam_viewA.png")
    rp.replace(C.R1 / f"{tag}_refcam_viewA_rgba.png")
    CR.composite(out / f"{tag}_refcam_viewA.png", out / f"{tag}_side_by_side_viewA.png")
    # ---- pair shots
    right.hide_render = True
    lods[0].hide_render = False
    camo = bpy.data.objects["REFCAM"]
    mid = Vector((0.0, -0.08, 0.1))
    shots = {
        "pair_34": (Vector((0.42, -0.62, 0.34)), 0.52),
        "pair_side": (Vector((-0.8, -0.08, 0.14)), 0.46),
        "pair_back": (Vector((0.0, 0.8, 0.22)), 0.5),
        "pair_top": (Vector((0.0, -0.12, 0.9)), 0.5),
        "pair_front": (Vector((0.0, -0.9, 0.18)), 0.5),
    }
    for name, (loc, osc) in shots.items():
        clear_lights()
        cam_look(camo, mid + loc, mid, ortho=osc)
        d = (mid + loc - mid).normalized()
        r_ = d.cross(Vector((0, 0, 1))).normalized() if abs(d.z) < 0.95 else Vector((1, 0, 0))
        LK.lights_for_cam((tuple(d), tuple(-r_), (0, 0, 1)), tuple(mid))
        rp = out / f"{tag}_{name}_rgba.png"
        render(rp, samples)
        white(rp, out / f"{tag}_{name}.png")
        rp.unlink()
    # ---- worn on her posed feet
    body = bpy.data.objects[lock["objects"]["body"]]
    body.hide_render = False
    skin = bpy.data.materials.new("preview_skin")
    b = next(n for n in skin.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.55, 0.42, 0.36, 1)
    b.inputs["Roughness"].default_value = 0.5
    body.data.materials.clear() if False else None
    body_mats = list(body.data.materials)
    for i in range(len(body.data.materials)):
        body.data.materials[i] = skin
    for name, (loc, osc) in {"worn_34": (Vector((0.5, -0.75, 0.3)), 0.7),
                             "worn_side": (Vector((-0.9, -0.05, 0.12)), 0.62)}.items():
        clear_lights()
        m2 = Vector((0.0, -0.08, 0.2))
        cam_look(camo, m2 + loc, m2, ortho=osc)
        d = loc.normalized()
        r_ = d.cross(Vector((0, 0, 1))).normalized()
        LK.lights_for_cam((tuple(d), tuple(-r_), (0, 0, 1)), tuple(m2))
        rp = out / f"{tag}_{name}_rgba.png"
        render(rp, samples)
        white(rp, out / f"{tag}_{name}.png")
        rp.unlink()
    for i, m in enumerate(body_mats):
        body.data.materials[i] = m
    body.hide_render = True
    # ---- LOD strip (right shoe, 3/4)
    lods[0].hide_render = True
    strip = []
    clear_lights()
    tgt = Vector(tuple(C.local_to_world(np.array([110.0, 5.0, 90.0]), "r")))
    loc = tgt + Vector((-0.3, -0.45, 0.25))
    cam_look(camo, loc, tgt, ortho=0.36)
    d = (loc - tgt).normalized()
    LK.lights_for_cam((tuple(d), tuple(-d.cross(Vector((0, 0, 1))).normalized()), (0, 0, 1)), tuple(tgt))
    for i, lo in enumerate(lods):
        o = only_side(lo, "r", f"RENDER_LOD{i}")
        o.hide_render = False
        rp = out / f"{tag}_lod{i}_rgba.png"
        render(rp, max(32, samples // 2))
        strip.append(white(rp, out / f"{tag}_lod{i}.png"))
        rp.unlink()
        (out / f"{tag}_lod{i}.png").unlink()
        o.hide_render = True
    P.write(str(out / f"{tag}_lod_strip.png"), (np.clip(np.concatenate(strip, 1), 0, 1) * 255).astype(np.uint8))
    print("RENDER_OK", out)


main()
