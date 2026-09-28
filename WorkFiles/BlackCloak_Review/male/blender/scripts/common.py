import bpy, math, mathutils, numpy as np, json, os
from mathutils import Vector
D = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/blender/"
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
REF_W, REF_H = 417, 674


def cloak():
    return bpy.data.objects["SKM_BlackCloak_MH"]


def body_objs():
    return list(bpy.data.collections["REV_Body"].all_objects)


def eval_bbox(objs):
    dg = bpy.context.evaluated_depsgraph_get(); pts = []
    for o in objs:
        e = o.evaluated_get(dg); m = e.to_mesh()
        pts += [o.matrix_world @ v.co for v in m.vertices]; e.to_mesh_clear()
    a = np.array([tuple(p) for p in pts])
    return a.min(0), a.max(0)


def make_camera(target, yaw, pitch, focal, dist, name="REV_Cam"):
    for o in list(bpy.data.objects):
        if o.name.startswith(name): bpy.data.objects.remove(o, do_unlink=True)
    cam = bpy.data.cameras.new(name); cam.lens = focal; cam.sensor_fit = "VERTICAL"; cam.sensor_height = 24
    cam.clip_start = 0.05; cam.clip_end = 100
    co = bpy.data.objects.new(name, cam); bpy.context.scene.collection.objects.link(co)
    y, p = math.radians(yaw), math.radians(pitch)
    d = Vector((math.sin(y) * math.cos(p), -math.cos(y) * math.cos(p), math.sin(p))) * dist
    co.location = Vector(target) + d
    co.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = co
    return co


def set_visible(cloak_on=True, body_on=True):
    lc = bpy.context.view_layer.layer_collection.children
    lc["REV_Cloak"].exclude = not cloak_on
    lc["REV_Body"].exclude = not body_on
    lc["REV_Rig"].exclude = False
    bpy.data.objects["root"].hide_render = True


def pose_arms_down(arm):
    """Rotate ONLY upperarm/lowerarm so the arms hang at the sides like the reference mannequin (world-space aim)."""
    import mathutils as mu
    bpy.context.view_layer.update()
    targets = {  # side: (upper arm direction, forearm direction) in world, character faces -Y, his left = +X
        "l": (Vector((0.16, 0.02, -1.0)), Vector((0.10, -0.22, -1.0))),
        "r": (Vector((-0.16, 0.02, -1.0)), Vector((-0.10, -0.22, -1.0))),
    }
    out = {}
    for side, (du, df) in targets.items():
        for bname, want in (("upperarm_" + side, du), ("lowerarm_" + side, df)):
            pb = arm.pose.bones[bname]
            bpy.context.view_layer.update()
            M = arm.matrix_world @ pb.matrix
            headw = M.translation.copy()
            child = {"upperarm": "lowerarm_", "lowerarm": "hand_"}[bname.split("_")[0]] + side
            tailw = arm.matrix_world @ arm.pose.bones[child].head
            cur = (tailw - headw).normalized()
            q = cur.rotation_difference(want.normalized())
            R = mu.Matrix.Translation(headw) @ q.to_matrix().to_4x4() @ mu.Matrix.Translation(-headw)
            pb.matrix = arm.matrix_world.inverted() @ R @ M
            bpy.context.view_layer.update()
            out[bname] = math.degrees(q.angle)
    return out


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def resize(a, h, w):
    """area-average downsample (or bilinear up) of HxWxC float image to h x w"""
    H, W = a.shape[:2]
    if H % h == 0 and W % w == 0 and H >= h:
        fy, fx = H // h, W // w
        return a.reshape(h, fy, w, fx, -1).mean((1, 3)).reshape(h, w, *a.shape[2:])
    ys = (np.arange(h) + 0.5) * H / h - 0.5; xs = (np.arange(w) + 0.5) * W / w - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, H - 1); x0 = np.clip(np.floor(xs).astype(int), 0, W - 1)
    y1 = np.clip(y0 + 1, 0, H - 1); x1 = np.clip(x0 + 1, 0, W - 1)
    fy = (ys - y0)[:, None]; fx = (xs - x0)[None, :]
    if a.ndim == 3: fy = fy[..., None]; fx = fx[..., None]
    return (a[y0][:, x0] * (1 - fy) * (1 - fx) + a[y0][:, x1] * (1 - fy) * fx + a[y1][:, x0] * fy * (1 - fx) + a[y1][:, x1] * fy * fx)
