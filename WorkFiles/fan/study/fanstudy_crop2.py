import bpy, numpy as np
def crop(src, dst, x0,y0,x1,y1, scale):
    im = bpy.data.images.load(src); w,h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h,w,4)[::-1]
    c = np.repeat(np.repeat(a[y0:y1, x0:x1], scale, 0), scale, 1)
    H,W = c.shape[:2]; out = bpy.data.images.new("c", W, H, alpha=True)
    out.pixels[:] = c[::-1].ravel(); out.filepath_raw = dst; out.file_format='PNG'; out.save()
R="C:/Users/Cody/Desktop/Blender_Projects/References/Fan/"; O="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/study/"
crop(R+"fan2.png", O+"fanstudy_fan2_tassel.png", 150,520,420,700, 3)
