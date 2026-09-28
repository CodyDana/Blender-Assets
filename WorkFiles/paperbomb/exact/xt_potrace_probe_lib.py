# -*- coding: utf-8 -*-
"""make_image / trace / to_px from xt_potrace_probe.py, importable (no main)."""
import os
import bpy
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
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


