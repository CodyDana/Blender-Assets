"""Viewing aid only: brightened, gamma-lifted crops of the reference without a grid (for reading relief by eye).
Never shipped.  Run: blender -b --factory-startup --python sbstudy_clean_view.py -- <scratch_dir>"""
import bpy, numpy as np, os, sys
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
SCR = sys.argv[sys.argv.index("--") + 1]
img = bpy.data.images.load(REF); img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3].copy()
bpy.data.images.remove(img)
b = np.clip(px, 0, 1) ** 0.55
def save(name, a, s=1):
    a = np.repeat(np.repeat(a, s, 0), s, 1)
    hh, ww = a.shape[:2]
    im = bpy.data.images.new(name, ww, hh, alpha=False); im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.concatenate([a[::-1], np.ones((hh, ww, 1), np.float32)], 2).ravel())
    im.filepath_raw = os.path.join(SCR, name + '.png'); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
save('sbstudy_clean_full', b)
save('sbstudy_clean_centre', b[380:860, 380:1000])
