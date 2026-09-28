import bpy, numpy as np, json, sys
p = r"C:/Users/Cody/Desktop/Blender_Projects/References/SnowFlower/SnowFlower_user_reference.png"
im = bpy.data.images.load(p); im.colorspace_settings.name='sRGB'
w,h = im.size
a = np.array(im.pixels[:],dtype=np.float32).reshape(h,w,4)[::-1,:,:3]
np.save(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_indep/ref_rgb.npy", a)
print("SIZE",w,h)
lum = a.mean(2); sat = a.max(2)-a.min(2)
fg = (lum<0.9)|(sat>0.08)
for name,(x0,x1) in {"front":(180,380),"side":(420,560),"back":(600,800)}.items():
    rows = np.where(fg[:,x0:x1].any(1))[0]
    print(name, "rows", rows.min(), rows.max())
    for r in [15,40,100,150,200,250,280,290,300,320,350,400,500,600,700,800,900,1000,1100,1150,1180,1200,1210]:
        c = np.where(fg[r,x0:x1])[0]
        print("  r",r, (c.min()+x0, c.max()+x0) if len(c) else None)
