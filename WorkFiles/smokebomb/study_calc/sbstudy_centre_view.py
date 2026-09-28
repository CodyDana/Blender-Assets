"""Viewing aid only: brightened centre of the reference with a 25 px grid (red every 100 px), for reading band widths
by eye.  Never shipped.  Run: blender -b --factory-startup --python sbstudy_centre_view.py -- <scratch_dir>"""
import bpy, numpy as np, os, sys
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
SCR = sys.argv[sys.argv.index("--") + 1]
img = bpy.data.images.load(REF); img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3].copy()
bpy.data.images.remove(img)
b = np.clip(px * 2.6, 0, 1)
for k in range(0, w, 25):
    col = (1, 0, 0) if k % 100 == 0 else ((1, 1, 0) if k % 50 == 0 else (0, 0.7, 0.7))
    b[:, k] = col; b[k, :] = col
def save(name, a, s=1):
    a = np.repeat(np.repeat(a, s, 0), s, 1)
    hh, ww = a.shape[:2]
    im = bpy.data.images.new(name, ww, hh, alpha=False); im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.concatenate([a[::-1], np.ones((hh, ww, 1), np.float32)], 2).ravel())
    im.filepath_raw = os.path.join(SCR, name + '.png'); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
save('sbstudy_centre_A', b[400:800, 400:800], 2)
save('sbstudy_centre_B', b[350:750, 600:1000], 2)
save('sbstudy_limb_R', b[500:800, 950:1110], 3)
save('sbstudy_limb_T', b[140:300, 480:800], 3)
