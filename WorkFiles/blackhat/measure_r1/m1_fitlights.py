# Fit light powers (NNLS, relative error) of basis renders to reference region medians (linear luminance).
import bpy, numpy as np, json
M = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/measure_r1/'
names = ['key','kick','fill','left','right','top','back','world']
def load(p):
    i = bpy.data.images.load(p)
    return np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1]
def s2l(s): return np.where(s <= 0.04045, s/12.92, ((s+0.055)/1.055)**2.4)
ref = s2l(load('C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png')[..., :3])
lw = np.array([0.2126, 0.7152, 0.0722]); Lr = ref @ lw
refcov = (Lr < 0.35)
basis = {}; alpha = None
for n in names:
    a = load(M+f'fit_{n}.exr'); basis[n] = a[..., :3] @ lw; alpha = a[..., 3]
both = refcov & (alpha > 0.99)
# erode both by 3 px to avoid edges
from functools import reduce
e = both.copy()
for dy in (-3, 0, 3):
    for dx in (-3, 0, 3):
        e &= np.roll(np.roll(both, dy, 0), dx, 1)
rows = []; tgt = []
Hh, Ww = Lr.shape
for y0 in range(140, 540, 16):
    for x0 in range(0, 670, 20):
        sel = e[y0:y0+16, x0:x0+20]
        if sel.sum() < 150: continue
        tgt.append(np.median(Lr[y0:y0+16, x0:x0+20][sel]))
        rows.append([np.median(basis[n][y0:y0+16, x0:x0+20][sel]) for n in names])
A = np.array(rows); t = np.array(tgt); w = 1/np.maximum(t, 0.004)
Aw = A*w[:, None]; tw = t*w
# simple NNLS by projected coordinate descent
x = np.zeros(len(names))
for it in range(20000):
    for j in range(len(names)):
        r = tw - Aw @ x + Aw[:, j]*x[j]
        x[j] = max(0.0, (Aw[:, j] @ r)/(Aw[:, j] @ Aw[:, j] + 1e-12))
pred = A @ x
rel = (pred - t)/t
print('FIT', dict(zip(names, x.round(5).tolist())), 'rows', len(t), 'rel_rms', float(np.sqrt(np.mean(rel**2))))
cfg = {'world': float(x[-1]), 'lights': [[n, th, el, float(100*x[i])] for i, (n, th, el) in enumerate(
    [('key',-110,35),('kick',115,25),('fill',0,20),('left',-60,30),('right',70,30),('top',0,80),('back',180,40)])]}
open(M+'lt_fit.json', 'w').write(json.dumps(cfg))
