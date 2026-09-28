import bpy, numpy as np, sys
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/paperbomb/exact/blind")
ROOT = "C:/Users/Cody/Desktop/Blender_Projects/"
def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; c = im.channels; a = np.empty(w*h*c, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, c)[::-1, :, :3].copy(); bpy.data.images.remove(im); return a
def save(a, p):
    a = np.clip(a, 0, 1).astype(np.float32); h, w = a.shape[:2]
    rgba = np.concatenate([a, np.ones((h, w, 1), np.float32)], -1)[::-1]
    im = bpy.data.images.new("o", w, h, alpha=False); im.colorspace_settings.name = 'Non-Color'
    im.pixels.foreach_set(rgba.ravel()); im.filepath_raw = p; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
r = load(ROOT + "References/PaperBomb/paperbomb_guide_v2_real_glyphs.png")
u = r.repeat(3, 0).repeat(3, 1)
for i in range(0, 653, 10):
    u[i*3, :] = [0, 0.6, 1] if i % 50 else [0, 0, 1]
for j in range(0, 300, 10):
    u[:, j*3] = [0, 0.6, 1] if j % 50 else [0, 0, 1]
save(u[:980], ROOT + "WorkFiles/paperbomb/exact/blind/grid_top.png")
save(u[980:], ROOT + "WorkFiles/paperbomb/exact/blind/grid_bot.png")
