"""ref vs iteration: hole crops (3x), body crops (2x) and close-ups p2/p4.  usage: r2_look3.py ITERDIR OUTPNG"""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/r2/tools")
from r2png import *
import numpy as np
ref = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology/fb_ref_srgb.npy")[..., :3].astype(np.float32) * 255
d = sys.argv[1]
o = read_png(f"{d}/row.png")[..., :3]
def up(a, k): return np.repeat(np.repeat(a, k, 0), k, 1)
rows = []
t = []
for (cx, cy) in ((467, 451), (745, 339), (1103, 560)):
    for im in (ref, o):
        t.append(up(im[cy - 45:cy + 45, cx - 45:cx + 45], 3)); t.append(np.full((270, 4, 3), 230.))
rows.append(np.concatenate(t[:-1], 1))
t = []
for b in ((380, 180, 560, 420), (650, 280, 840, 520)):
    for im in (ref, o):
        t.append(im[b[1]:b[3], b[0]:b[2]]); t.append(np.full((b[3] - b[1], 4, 3), 230.))
r2 = np.concatenate(t[:-1], 1)
r2 = up(r2, 2)[:, :rows[0].shape[1]]
pad = rows[0].shape[1] - r2.shape[1]
if pad > 0: r2 = np.concatenate([r2, np.full((r2.shape[0], pad, 3), 230.)], 1)
rows.append(r2)
import os
PAN = {'p1': (6, 756, 318, 1220), 'p2': (323, 756, 629, 1220), 'p3': (634, 756, 939, 1220), 'p4': (946, 756, 1249, 1220)}
t = []
for k, b in PAN.items():
    if not os.path.exists(f"{d}/{k}.png"): continue
    a = ref[b[1]:b[3], b[0]:b[2]]; oo = read_png(f"{d}/{k}.png")[..., :3][:a.shape[0], :a.shape[1]]
    t += [a, np.full((a.shape[0], 4, 3), 230.), oo, np.full((a.shape[0], 8, 3), 230.)]
if t:
    r3 = np.concatenate(t[:-1], 1)
    W = rows[0].shape[1]
    if r3.shape[1] > W: r3 = r3[:, :W]
    else: r3 = np.concatenate([r3, np.full((r3.shape[0], W - r3.shape[1], 3), 230.)], 1)
    rows.append(r3)
out = []
for r in rows: out += [r, np.full((6, r.shape[1], 3), 230.)]
write_png(sys.argv[2], np.concatenate(out[:-1], 0))
