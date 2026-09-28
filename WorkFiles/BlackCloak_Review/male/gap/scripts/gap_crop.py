
# Crop the same ref-frame box from REF/BL/UE (stretched, gridded every 10 ref px) and stack side by side.
# args: name x0 y0 x1 y1 scale [stretch 0/1]
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import gap_lib as L
OUT = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/gap/out'
a = sys.argv[sys.argv.index('--')+1:]
name = a[0]; x0, y0, x1, y1 = map(int, a[1:5]); sc = int(a[5]); stretch = int(a[6]) if len(a) > 6 else 1
srcs = a[7].split(',') if len(a) > 7 else ['REF', 'BL', 'UE']
panels = []
for s in srcs:
    img = np.load(f'{OUT}/ref_1x.npy') if s == 'REF' else np.load(f'{OUT}/aligned_{s}_2x.npy')
    f = 1 if s == 'REF' else 2
    c = img[y0*f:y1*f, x0*f:x1*f]
    k = sc//f
    c = np.repeat(np.repeat(c, k, 0), k, 1) if k > 1 else c
    if stretch:
        l = L.lum(c); m = l < 115
        if m.sum() > 10:
            lo, hi = np.percentile(l[m], 1), np.percentile(l[m], 99.5)
            v = np.clip((l-lo)/(hi-lo+1e-6), 0, 1)*235
            c = np.where(m[..., None], np.stack([v]*3, -1), c)
    c = c.copy()
    for g in range(0, c.shape[0], 10*sc):
        c[g, :] = (255, 0, 0) if ((g//sc + y0) % 50 == 0) else (0, 160, 255)
    for g in range(0, c.shape[1], 10*sc):
        c[:, g] = (255, 0, 0) if ((g//sc + x0) % 50 == 0) else (0, 160, 255)
    panels.append(c); panels.append(np.full((c.shape[0], 6, 3), 255.0))
L.save(f'{OUT}/crop_{name}.png', np.concatenate(panels[:-1], 1))
print('ok')
