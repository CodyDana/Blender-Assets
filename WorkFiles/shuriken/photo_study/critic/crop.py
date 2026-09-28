import bpy, numpy as np, os, sys
P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
O = P + "critic/"
def load(path):
    img = bpy.data.images.load(path); W, H = img.size
    b = np.empty(W*H*4, np.float32); img.pixels.foreach_get(b)
    a = b.reshape(H, W, 4)[::-1, :, :3].copy(); bpy.data.images.remove(img); return a
def save(a, path):
    h, w, _ = a.shape
    img = bpy.data.images.new(os.path.basename(path), width=w, height=h, alpha=False)
    buf = np.ones((h, w, 4), np.float32); buf[..., :3] = np.clip(a, 0, 1)
    img.pixels.foreach_set(buf[::-1].ravel()); img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img); print("wrote", path)
jobs = [
 (P+"synthesis/juji_photo_matched.png", (680, 480, 860, 660), 4, "juji_crotch_TR.png"),
 (P+"synthesis/juji_photo_matched.png", (540, 640, 720, 820), 4, "juji_crotch_BL.png"),
 (P+"synthesis/juji_photo_matched.png", (1180, 560, 1370, 720), 4, "juji_tip_R.png"),
]
for src, (x0,y0,x1,y1), s, name in jobs:
    a = load(src)[y0:y1, x0:x1]
    a = np.repeat(np.repeat(a, s, 0), s, 1)
    save(a, O + name)
