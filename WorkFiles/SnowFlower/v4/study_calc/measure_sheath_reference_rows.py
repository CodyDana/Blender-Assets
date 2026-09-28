import bpy, numpy as np
img = bpy.data.images.load(r"C:/Users/Cody/Desktop/Blender_Projects/References/SnowFlower/SnowFlower_sheath_reference.png")
w,h = img.size
px = np.array(img.pixels[:],dtype=np.float32).reshape(h,w,4)[::-1]  # row 0 = top
lum = px[:,:,:3].mean(2)
mask = lum < 0.85
rows = np.where(mask.any(1))[0]
print("SFSTUDY size",w,h,"top",rows.min(),"bottom",rows.max())
for y in list(range(rows.min(), rows.max()+1, 20)) + [rows.max()-5, rows.max()]:
    xs = np.where(mask[y])[0]
    if len(xs)==0: print("SFSTUDY y",y,"none"); continue
    print("SFSTUDY y=%d x[%d,%d] w=%d mid=%.1f" % (y, xs.min(), xs.max(), xs.max()-xs.min()+1, (xs.min()+xs.max())/2))
