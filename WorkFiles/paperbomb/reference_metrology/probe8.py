# -*- coding: utf-8 -*-
"""Probe 8 - V2 bottom/right edge, measured directly from luminance."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import lib_metro as L

a = L.load_stored(r"C:/Users/Cody/Desktop/Blender_Projects/References/PaperBomb/paperbomb_guide_v2_real_glyphs.png")
rgb = a[..., :3]; lu = L.lum(rgb); st = L.sat(rgb)
h, w = lu.shape
print("image", w, h)
print("rgb/sat at the last rows, x=150:")
for y in range(644, 653):
    print("  y=%3d rgb=%s lum=%.3f sat=%.4f" % (y, np.round(rgb[y, 150], 4).tolist(), lu[y, 150], st[y, 150]))
print("rgb/sat at the last cols, y=330:")
for x in range(286, 300):
    print("  x=%3d rgb=%s lum=%.3f sat=%.4f" % (x, np.round(rgb[330, x], 4).tolist(), lu[330, x], st[330, x]))
# per-column bottom crossing over the straight middle of the bottom edge
bg = float(np.median(lu[2:6, 100:200]))
print("bg lum (top strip) =", round(bg, 4))
xs = range(90, 210)
cr = []
for x in xs:
    col = lu[600:653, x]
    inside = float(np.median(col[20:35]))
    tgt = 0.5 * (bg + inside)
    idx = None
    for i in range(len(col) - 1, 0, -1):
        if col[i - 1] <= tgt < col[i] or col[i - 1] < tgt <= col[i]:
            idx = 600 + i - 1 + (tgt - col[i - 1]) / max(col[i] - col[i - 1], 1e-6)
            break
    if idx: cr.append(idx)
cr = np.array(cr)
print("bottom-edge crossing: n=%d med=%.3f p10=%.3f p90=%.3f sd=%.3f" %
      (len(cr), np.median(cr), np.percentile(cr, 10), np.percentile(cr, 90), cr.std()))
ys = range(150, 500)
cr2 = []
for y in ys:
    row = lu[y, 260:300]
    inside = float(np.median(row[0:12]))
    tgt = 0.5 * (bg + inside)
    idx = None
    for i in range(1, len(row)):
        if row[i - 1] <= tgt < row[i] or row[i - 1] < tgt <= row[i]:
            idx = 260 + i - 1 + (tgt - row[i - 1]) / max(row[i] - row[i - 1], 1e-6)
            break
    if idx: cr2.append(idx)
cr2 = np.array(cr2)
print("right-edge crossing: n=%d med=%.3f p10=%.3f p90=%.3f sd=%.3f" %
      (len(cr2), np.median(cr2), np.percentile(cr2, 10), np.percentile(cr2, 90), cr2.std()))
# top and left for comparison
cr3 = []
for x in range(90, 210):
    col = lu[0:60, x]
    inside = float(np.median(col[25:40])); tgt = 0.5 * (bg + inside)
    for i in range(1, len(col)):
        if col[i - 1] >= tgt > col[i] or col[i - 1] > tgt >= col[i]:
            cr3.append(i - 1 + (col[i - 1] - tgt) / max(col[i - 1] - col[i], 1e-6)); break
cr3 = np.array(cr3)
print("top-edge crossing: n=%d med=%.3f sd=%.3f" % (len(cr3), np.median(cr3), cr3.std()))
cr4 = []
for y in range(150, 500):
    row = lu[y, 0:40]
    inside = float(np.median(row[25:38])); tgt = 0.5 * (bg + inside)
    for i in range(1, len(row)):
        if row[i - 1] >= tgt > row[i] or row[i - 1] > tgt >= row[i]:
            cr4.append(i - 1 + (row[i - 1] - tgt) / max(row[i - 1] - row[i], 1e-6)); break
cr4 = np.array(cr4)
print("left-edge crossing: n=%d med=%.3f sd=%.3f" % (len(cr4), np.median(cr4), cr4.std()))
W = np.median(cr2) - np.median(cr4); H = np.median(cr) - np.median(cr3)
print("V2 luminance-crossing tag: W=%.3f H=%.3f aspect=%.5f" % (W, H, W / H))
