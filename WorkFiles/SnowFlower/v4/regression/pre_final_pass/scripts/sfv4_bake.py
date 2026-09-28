"""Snow Flower v4 bake: Cycles selected-to-active from the high-poly onto each LOD0 part, per part
into its own float image, composited into the atlas through the part's own UV coverage mask
(a Blender margin would overwrite neighbouring parts' islands), then edge-extended over the
padding so every mip level stays clean."""
from __future__ import annotations

import math
import time

import numpy as np


# ---------------------------------------------------------------------- cycles device

def setup_cycles(samples=8):
    import bpy
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        pr = bpy.context.preferences.addons["cycles"].preferences
        pr.compute_device_type = "OPTIX"
        pr.get_devices()
        for d in pr.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as exc:  # noqa: BLE001
        print("GPU unavailable, CPU bake:", exc)
        sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    return sc.cycles.device


# ---------------------------------------------------------------------- coverage

def uv_triangles_px(obj, size, u_offset=0.0):
    """(T, 3, 2) pixel-space UV0 triangles of ``obj`` (row 0 = v 0, i.e. Blender's bottom row)."""
    me = obj.data
    me.calc_loop_triangles()
    uvl = me.uv_layers["UV0"].data
    uv = np.zeros((len(me.loops), 2))
    uvl.foreach_get("uv", uv.ravel())
    tri = np.zeros((len(me.loop_triangles), 3), int)
    me.loop_triangles.foreach_get("loops", tri.ravel())
    t = uv[tri]
    t[..., 0] -= u_offset
    return t * size


def rasterize(tris_px, size, dilate=1):
    """Boolean coverage of pixel centres by the triangles (row index = v pixel)."""
    mask = np.zeros((size, size), bool)
    for tr in tris_px:
        x0 = max(int(math.floor(tr[:, 0].min())) - 1, 0)
        x1 = min(int(math.ceil(tr[:, 0].max())) + 1, size)
        y0 = max(int(math.floor(tr[:, 1].min())) - 1, 0)
        y1 = min(int(math.ceil(tr[:, 1].max())) + 1, size)
        if x1 <= x0 or y1 <= y0:
            continue
        xs = np.arange(x0, x1) + 0.5
        ys = np.arange(y0, y1) + 0.5
        X, Y = np.meshgrid(xs, ys)
        (ax, ay), (bx, by), (cx, cy) = tr
        d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(d) < 1e-12:
            continue
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / d
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / d
        l3 = 1 - l1 - l2
        eps = -0.02
        inside = (l1 >= eps) & (l2 >= eps) & (l3 >= eps)
        mask[y0:y1, x0:x1] |= inside
    for _ in range(dilate):
        m = mask.copy()
        m[1:] |= mask[:-1]
        m[:-1] |= mask[1:]
        m[:, 1:] |= mask[:, :-1]
        m[:, :-1] |= mask[:, 1:]
        mask = m
    return mask


def edge_extend(img, valid, iters=None):
    """Fill invalid texels by pull-push (mip pyramid of valid-weighted averages): every hole gets the
    smooth continuation of its surrounding islands, so mip levels never pull in a foreign colour."""
    img = np.asarray(img, np.float32)
    w = valid.astype(np.float32)
    pyr = [(img * w[..., None], w)]
    while pyr[-1][1].shape[0] > 1:
        a, ww = pyr[-1]
        h2, w2 = a.shape[0] // 2, a.shape[1] // 2
        a2 = a[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2, -1).sum(axis=(1, 3))
        w2_ = ww[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).sum(axis=(1, 3))
        pyr.append((a2, w2_))
    # normalise each level
    lev = []
    for a, ww in pyr:
        with np.errstate(invalid="ignore", divide="ignore"):
            lev.append((np.where(ww[..., None] > 0, a / np.maximum(ww[..., None], 1e-12), 0.0), ww > 0))
    filled = lev[-1][0]
    for k in range(len(lev) - 2, -1, -1):
        col, ok = lev[k]
        up = np.repeat(np.repeat(filled, 2, axis=0), 2, axis=1)[:col.shape[0], :col.shape[1]]
        filled = np.where(ok[..., None], col, up)
    out = img.copy()
    out[~valid] = filled[~valid]
    return out


# ---------------------------------------------------------------------- bake one part

def bake_part(low, highs, channel, size, cage_mm, samples, img_name="SF4_BAKE_TMP"):
    """Bake ``channel`` ('NORMAL' | 'AO' | 'EMIT') from ``highs`` onto ``low`` into a fresh float
    image; return its pixels (size, size, 4) float32 (row 0 = bottom)."""
    import bpy
    sc = bpy.context.scene
    old = bpy.data.images.get(img_name)
    if old is not None:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(img_name, size, size, alpha=False, float_buffer=True, is_data=True)
    mat = low.data.materials[0]
    nt = mat.node_tree
    node = nt.nodes.get("bake_target")
    node.image = img
    nt.nodes.active = node
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for h in highs:
        h.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    sc.cycles.samples = samples
    bk = sc.render.bake
    bk.use_selected_to_active = True
    bk.use_cage = False
    bk.cage_extrusion = cage_mm / 1000.0
    bk.max_ray_distance = (cage_mm + 3.5) / 1000.0
    bk.margin = 2
    bk.margin_type = "EXTEND"
    bk.use_clear = True
    bk.target = "IMAGE_TEXTURES"
    kw = dict(type=channel, use_selected_to_active=True, cage_extrusion=cage_mm / 1000.0,
              max_ray_distance=(cage_mm + 3.5) / 1000.0, margin=2, margin_type="EXTEND", use_clear=True)
    if channel == "NORMAL":
        kw.update(normal_space="TANGENT", normal_r="POS_X", normal_g="POS_Y", normal_b="POS_Z")
    t = time.time()
    res = bpy.ops.object.bake(**kw)
    if "FINISHED" not in res:
        raise RuntimeError(f"bake {channel} on {low.name} failed: {res}")
    px = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    print(f"  baked {channel:6s} {low.name:20s} {time.time() - t:6.1f}s", flush=True)
    return px.reshape(size, size, 4)
