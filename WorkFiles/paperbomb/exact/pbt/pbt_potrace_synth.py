"""Blender's built-in tracer (grease_pencil.trace_image = potrace) on the SAME synthetic
observations as pbt_bench_synth.py (x8 B-spline field, thresholded by the operator at 0.5).
blender -b --factory-startup --python pbt_potrace_synth.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, os.path.dirname(HERE))
import bpy
import numpy as np
from props_lib import trace as T
import xt_potrace_probe_lib as PL
bpy.ops.wm.read_factory_settings(use_empty=True)
z = np.load(os.path.join(HERE, "pbt_synth_obs.npz"))
cases = sorted({k.split("__")[0] for k in z.files})
out = {}
for c in cases:
    obs = z[c + "__obs"]; region = z[c + "__region"]; x0, y0, x1, y1 = [int(v) for v in z[c + "__win"]]
    f = np.where(region, obs / 0.986, 0.0)
    fine, gx0, gy0, st = T.upsample_window(f, x0, y0, x1, y1, 8, "bspline")
    img = PL.make_image("synth_" + c, fine)
    loops, emp = PL.trace(img)
    h, w = fine.shape
    px = PL.to_px(loops, emp, w, h, gx0, gy0, st)
    arr = np.empty(len(px), dtype=object)
    for i, p in enumerate(px):
        arr[i] = p
    out["loops_" + c] = arr
    print("POTRACE", c, len(px))
np.savez(os.path.join(HERE, "pbt_potrace_synth.npz"), **out)
