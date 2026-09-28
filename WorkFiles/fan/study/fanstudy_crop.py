import bpy, numpy as np, sys
def crop(src, dst, x0,y0,x1,y1, scale):
    im = bpy.data.images.load(src)
    w,h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h,w,4)[::-1]  # top-down
    c = a[y0:y1, x0:x1]
    c = np.repeat(np.repeat(c, scale, 0), scale, 1)
    H,W = c.shape[:2]
    out = bpy.data.images.new("c", W, H, alpha=True)
    out.pixels[:] = c[::-1].ravel()
    out.filepath_raw = dst; out.file_format='PNG'; out.save()
    print("size", w, h)
R="C:/Users/Cody/Desktop/Blender_Projects/References/Fan/"
O="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/study/"
crop(R+"fan2.png", O+"fanstudy_fan2_pivot.png", 300,380,520,620, 3)
crop(R+"fan2.png", O+"fanstudy_fan2_leafedge_right.png", 560,300,760,520, 3)
crop(R+"fan2.png", O+"fanstudy_fan2_top.png", 250,210,560,330, 3)
crop(R+"fan1.png", O+"fanstudy_fan1_pivot.png", 280,400,540,640, 3)
