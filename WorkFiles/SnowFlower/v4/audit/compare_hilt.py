"""Hilt close comparison: reference front/side hilt (sheet pixels, 4x upscaled) beside rev-3 export at the same 4x scale.
blender -b --factory-startup --python compare_hilt.py
"""
import bpy
import numpy as np
from pathlib import Path
ROOT = Path(r'C:/Users/Cody/Desktop/Blender_Projects'); AUD = ROOT / 'WorkFiles/SnowFlower/v4/audit'

def load(p):
    im = bpy.data.images.load(str(p)); w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, im.channels)[::-1].copy(); bpy.data.images.remove(im)
    if a.shape[2] == 3: a = np.concatenate([a, np.ones((h, w, 1), np.float32)], 2)
    return a
def save(a, p):
    h, w = a.shape[:2]; im = bpy.data.images.new(p.stem, w, h, alpha=True)
    im.pixels.foreach_set(a[::-1].ravel()); im.filepath_raw = str(p); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
def white(a):
    al = a[..., 3:4]; return np.concatenate([a[..., :3] * al + .996 * (1 - al), np.ones_like(al)], 2)
ref = load(ROOT / 'References/SnowFlower/SnowFlower_user_reference.png')
up = lambda a, k: np.repeat(np.repeat(a, k, 0), k, 1)
panels = []
for view, axis in (('front', 290), ('side', 489)):
    crop = ref[0:400, axis - 70:axis + 70]  # 140 x 400 sheet px
    panels.append(up(crop, 4))
    rv = white(load(AUD / f'renders/rev3_hilt_{view}_4x.png'))  # 560 x 1600, axis at centre
    panels.append(rv)
sep = np.full((1600, 8, 4), .8, np.float32); sep[..., 3] = 1
out = np.concatenate([panels[0], sep, panels[1], sep, panels[2], sep, panels[3]], 1)
save(out, AUD / 'compare_hilt_ref_rev3_4x.png')
save(ref[0:560, 800:1222], AUD / 'ref_crop_guard_detail.png')
save(ref[880:1222, 800:1222], AUD / 'ref_crop_pommel_detail.png')
print('DONE')
