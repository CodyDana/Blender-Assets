
# Relative vertical-gradient edge maps (lighter above -> darker below = a layer edge casting shadow), gridded, per source.
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import gap_lib as L
OUT = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male/gap/out'

def edge_map(l, d=2, blur=3):
    b = L.blur2d(l, blur)
    e = np.zeros_like(b)
    e[d:-d] = (b[:-2*d] - b[2*d:])
    loc = L.blur2d(b, 15) + 4.0
    return e/loc

tiles = []
for s in ['REF', 'BL', 'UE']:
    img = np.load(f'{OUT}/ref_1x.npy') if s == 'REF' else np.load(f'{OUT}/aligned_{s}_2x.npy')
    if s == 'REF':
        Y, X = np.mgrid[0:1348, 0:834].astype(np.float64)
        img = L.bilinear(img, (X+0.5)/2-0.5, (Y+0.5)/2-0.5)
    l = L.lum(img); m = L.blur2d((l < 115).astype(float), 5) > 0.99
    e = edge_map(l, d=3, blur=5)
    e[~m] = 0
    np.save(f'{OUT}/edge_{s}_2x.npy', e.astype(np.float32))
    v = np.clip(e/0.6, 0, 1)*255
    rgb = np.stack([v]*3, -1)
    rgb[~m] = (40, 40, 60)
    for g in range(0, 1348, 20):
        rgb[g, :] = (200, 0, 0) if g % 100 == 0 else (0, 90, 150)
    for g in range(0, 834, 20):
        rgb[:, g] = (200, 0, 0) if g % 100 == 0 else (0, 90, 150)
    L.save(f'{OUT}/edgemap_{s}_2x.png', rgb)
print('ok')
