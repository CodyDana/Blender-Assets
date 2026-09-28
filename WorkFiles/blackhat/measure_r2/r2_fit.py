# Fit powers of the REFERENCE_SPEC 2 rig (key/kick/fill + world) to reference block medians (linear lum, relative error).
import bpy, numpy as np, json, sys
D = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/measure_r2/'
names = sys.argv[sys.argv.index('--')+1:] or ['key', 'kick', 'fill', 'world']
dirs = {'key': (-110, 35), 'kick': (115, 25), 'fill': (0, 20), 'left': (-60, 30), 'right': (70, 30), 'top': (0, 80), 'back': (180, 40)}
def load(p):
    i = bpy.data.images.load(p); i.colorspace_settings.name = 'Non-Color'
    x = np.array(i.pixels[:], dtype=np.float32).reshape(i.size[1], i.size[0], i.channels)[::-1]; bpy.data.images.remove(i); return x
def s2l(s): return np.where(s <= 0.04045, s/12.92, ((s+0.055)/1.055)**2.4)
lw = np.array([0.2126, 0.7152, 0.0722])
Lr = s2l(load('C:/Users/Cody/Desktop/Blender_Projects/References/BlackHat/blackhat_guide.png')[..., :3]) @ lw
B = {}; al = None
for n in names:
    x = load(D+f'r2_basis_{n}.exr'); B[n] = x[..., :3] @ lw; al = x[..., 3]
both = (Lr < 0.35) & (al > 0.99); e = both.copy()
for dy in (-3, 0, 3):
    for dx in (-3, 0, 3): e &= np.roll(np.roll(both, dy, 0), dx, 1)
rows, tgt = [], []
for y0 in range(140, 540, 16):
    for x0 in range(0, 670, 20):
        s = e[y0:y0+16, x0:x0+20]
        if s.sum() < 150: continue
        tgt.append(np.median(Lr[y0:y0+16, x0:x0+20][s])); rows.append([np.median(B[n][y0:y0+16, x0:x0+20][s]) for n in names])
A = np.array(rows); t = np.array(tgt); w = 1/np.maximum(t, 0.004); Aw = A*w[:, None]; tw = t*w
x = np.zeros(len(names))
for it in range(5000):
    for j in range(len(names)):
        r = tw - Aw @ x + Aw[:, j]*x[j]; x[j] = max(0.0, (Aw[:, j] @ r)/(Aw[:, j] @ Aw[:, j] + 1e-12))
rel = (A @ x - t)/t
print('FIT', dict(zip(names, x.round(5).tolist())), 'rows', len(t), 'rel_rms', round(float(np.sqrt(np.mean(rel**2))), 4))
cfg = {'world': float(x[names.index('world')]) if 'world' in names else 0.0,
       'lights': [[n, dirs[n][0], dirs[n][1], float(100*x[i])] for i, n in enumerate(names) if n != 'world']}
open(D+'r2_lt_fit_' + '_'.join(names) + '.json', 'w').write(json.dumps(cfg)); print(json.dumps(cfg))
