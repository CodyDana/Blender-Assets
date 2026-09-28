# -*- coding: utf-8 -*-
"""Candidate tracer: Blender 5.2's built-in grease_pencil.trace_image (Potrace inside).

Headless.  Traces (a) V2's black-ink field at 1x and (b) the same field resampled 8x with a
cubic B-spline, both thresholded at 0.5 by the operator, and writes the stroke points
(mapped back to V2 continuous pixels) to exact/potrace_loops.npz for scoring.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "Scripts", "props"))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from props_lib import trace as T  # noqa: E402
import xt_emblem_bench as EB  # noqa: E402


def make_image(name, field):
    h, w = field.shape
    import xt_io
    path = os.path.join(HERE, "_potrace_in_%s.png" % name)
    v = 1.0 - np.clip(field, 0, 1)      # the operator traces DARK pixels: ink -> 0
    xt_io.write(path, np.stack([v, v, v], -1))
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"
    return img


def trace(img, threshold=0.5):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    emp = bpy.data.objects.new("IMG", None)
    emp.empty_display_type = "IMAGE"
    emp.data = img
    emp.empty_display_size = 1.0
    bpy.context.scene.collection.objects.link(emp)
    bpy.context.view_layer.objects.active = emp
    emp.select_set(True)
    before = set(bpy.data.objects)
    r = bpy.ops.grease_pencil.trace_image(target="NEW", threshold=threshold,
                                          turnpolicy="MINORITY", mode="SINGLE")
    new = [o for o in bpy.data.objects if o not in before]
    print("trace result", r, [o.name for o in new])
    loops = []
    gp = new[0]
    mw = gp.matrix_world
    for layer in gp.data.layers:
        for fr in layer.frames:
            dr = fr.drawing
            n = len(dr.attributes["position"].data)
            pos = np.array([tuple(d.vector) for d in dr.attributes["position"].data])
            hl = np.array([tuple(d.vector) for d in dr.attributes["handle_left"].data])
            hr = np.array([tuple(d.vector) for d in dr.attributes["handle_right"].data])
            start = 0
            for st in dr.strokes:
                m = len(st.points)
                P = pos[start:start + m]; L = hl[start:start + m]; R = hr[start:start + m]
                start += m
                t = np.linspace(0, 1, 24, endpoint=False)[:, None]
                seg = []
                for i in range(m):
                    j = (i + 1) % m
                    a, b, c, d = P[i], R[i], L[j], P[j]
                    seg.append((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d)
                loops.append(np.vstack(seg))
    return loops, emp


def to_px(loops, emp, w, h, gx0, gy0, step):
    # calibrate: the image empty spans display_size in its larger dimension, centred with
    # offset (-0.5, -0.5): x in [-0.5, 0.5] * aspect, y likewise, +y up
    s = emp.empty_display_size
    big = max(w, h)
    out = []
    for p in loops:
        # object XZ or XY?  find the plane with spread
        xs = p[:, 0]
        ys = p[:, 2] if np.ptp(p[:, 2]) > np.ptp(p[:, 1]) else p[:, 1]
        u = (xs / s + 0.5 * w / big) * big            # 0..w in fine pixels
        v = (0.5 * h / big - ys / s) * big            # 0..h, top-down
        out.append(np.stack([gx0 - 0.5 * step + u * step, gy0 - 0.5 * step + v * step], 1))
    return out


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    src = T.read_source()
    fit = T.fit_card(src)
    ak, behind, unm = T.ink_layers(src, fit)
    x0, y0, x1, y1 = EB.WIN
    keep = EB.component_mask(ak, EB.WIN)
    region = np.zeros_like(ak, bool)
    region[y0:y1, x0:x1] = T.dilate(keep, 2)
    field = np.where(region, ak, 0.0)
    res = {}
    for tag, factor in (("x1", 1), ("x8", 8)):
        if factor == 1:
            fine = field[y0:y1, x0:x1]; gx0, gy0, st = x0 + 0.5, y0 + 0.5, 1.0
        else:
            fine, gx0, gy0, st = T.upsample_window(field, x0, y0, x1, y1, 8, "bspline")
        img = make_image("F" + tag, fine)
        loops, emp = trace(img)
        h, w = fine.shape
        px = to_px(loops, emp, w, h, gx0, gy0, st)
        print(tag, len(px), [len(p) for p in px][:10])
        res[tag] = px
    np.savez(os.path.join(HERE, "potrace_loops.npz"),
             **{"%s_%d" % (k, i): p for k, v in res.items() for i, p in enumerate(v)})


main()
