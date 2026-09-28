"""Viewing aid only: the reference with a pixel grid (red every 100 px, cyan every 50 px), written to the scratch dir.
Never shipped, never read by a build.  Run: blender -b --factory-startup --python sbstudy_grid_view.py -- <scratch_dir>"""
import bpy, numpy as np, os, sys
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png"
SCR = sys.argv[sys.argv.index("--") + 1]
img = bpy.data.images.load(REF); img.colorspace_settings.name = 'Non-Color'
w, h = img.size
px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)[::-1, :, :3].copy()
bpy.data.images.remove(img)
g = px.copy()
for k in range(0, w, 50):
    col = (1, 0, 0) if k % 100 == 0 else (0, 0.8, 0.8)
    g[:, k] = col; g[k, :] = col
def save(name, a):
    hh, ww = a.shape[:2]
    im = bpy.data.images.new(name, ww, hh, alpha=False); im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(np.concatenate([a[::-1], np.ones((hh, ww, 1), np.float32)], 2).ravel())
    im.filepath_raw = os.path.join(SCR, name + '.png'); im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
save('sbstudy_grid_full', g)
# brightened quadrant views (x2.2 gain, to see the band edges in the dark cloth)
b = np.clip(px * 2.6, 0, 1)
for k in range(0, w, 50):
    col = (1, 0, 0) if k % 100 == 0 else (0, 0.8, 0.8)
    b[:, k] = col; b[k, :] = col
save('sbstudy_grid_bright_TL', b[100:700, 100:700])
save('sbstudy_grid_bright_TR', b[100:700, 600:1200])
save('sbstudy_grid_bright_BL', b[600:1150, 100:700])
save('sbstudy_grid_bright_BR', b[600:1150, 600:1200])
