"""Side-by-side and silhouette comparison: reference sheet views vs rev-3 export renders at the same scale.
Runs in Blender (numpy). Writes composites + a JSON of measured profiles.
blender -b --factory-startup --python compare_views.py
"""
import bpy, json
import numpy as np
from pathlib import Path

ROOT = Path(r'C:/Users/Cody/Desktop/Blender_Projects')
AUD = ROOT / 'WorkFiles/SnowFlower/v4/audit'
REN = AUD / 'renders'

def load(path):
    im = bpy.data.images.load(str(path)); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1].copy()
    bpy.data.images.remove(im)
    if a.shape[2] == 3: a = np.concatenate([a, np.ones((h, w, 1), np.float32)], 2)
    return a

def save(arr, path):
    h, w = arr.shape[:2]
    im = bpy.data.images.new(path.stem, w, h, alpha=True)
    rgba = np.ones((h, w, 4), np.float32); rgba[..., :arr.shape[2]] = arr
    im.pixels.foreach_set(rgba[::-1].ravel()); im.filepath_raw = str(path); im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)

ref = load(ROOT / 'References/SnowFlower/SnowFlower_user_reference.png')
REF_BG = 0.996
lum = lambda a: a[..., :3] @ np.array([.2126, .7152, .0722], np.float32)
ref_mask_full = lum(ref) < REF_BG - 0.10

def on_white(a):
    al = a[..., 3:4]
    rgb = a[..., :3] * al + REF_BG * (1 - al)
    return np.concatenate([rgb, np.ones_like(al)], 2)

W = 240
views = {'front': 290, 'side': 489, 'back': 677}  # reference blade-axis column near the guard (row 400)
out = {}
panels = []
for v, axis in views.items():
    rv = load(REN / f'rev3_{v}_1x.png')
    rmask = rv[..., 3] > 0.5
    # rev3 axis: centre of blade run at row 400
    def run_at(mask, row, x):
        r = mask[row]
        if not r[x]:
            idx = np.nonzero(r)[0]
            if not len(idx): return None
            x = idx[np.argmin(abs(idx - x))]
        l = x
        while l > 0 and r[l - 1]: l -= 1
        rr = x
        while rr < len(r) - 1 and r[rr + 1]: rr += 1
        return int(l), int(rr)
    l, r = run_at(rmask, 400, 150); raxis = (l + r) / 2
    # crops aligned so both axes sit at W/2
    x0 = int(round(axis - W / 2)); refc = ref[:, x0:x0 + W]; refm = ref_mask_full[:, x0:x0 + W]
    x1 = int(round(raxis - W / 2)); pad = np.zeros((rv.shape[0], W, 4), np.float32)
    lo = max(0, x1); hi = min(rv.shape[1], x1 + W); pad[:, lo - x1:hi - x1] = rv[:, lo:hi]
    rv_c = on_white(pad); rm = pad[..., 3] > 0.5
    # profile via run containing axis
    prof = {'ref': [], 'rev3': []}
    for name, m in (('ref', refm), ('rev3', rm)):
        for row in range(m.shape[0]):
            rr = run_at(m, row, W // 2)
            prof[name].append(None if rr is None else [rr[0] - W / 2, rr[1] - W / 2])
    out[v] = prof
    # overlay: ref silhouette red, rev3 cyan, overlap dark grey
    ov = np.full((ref.shape[0], W, 4), 1.0, np.float32)
    ov[refm & ~rm] = (0.9, 0.15, 0.15, 1); ov[rm & ~refm] = (0.1, 0.65, 0.9, 1); ov[refm & rm] = (0.25, 0.25, 0.25, 1)
    panels += [refc, rv_c, ov]
sep = np.full((ref.shape[0], 6, 4), 1.0, np.float32); sep[..., :3] = .8
strip = np.concatenate(sum([[p, sep] for p in panels], [])[:-1], 1)
save(strip, AUD / 'compare_views_ref_rev3_overlay.png')
json.dump(out, open(AUD / 'compare_profiles.json', 'w'))
print('DONE', strip.shape)
