import bpy, numpy as np, glob, sys
for f in sorted(glob.glob(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealVerify_Indep\renders*\*.png")):
    im = bpy.data.images.load(f)
    a = np.array(im.pixels[:]).reshape(im.size[1], im.size[0], im.channels)
    print("PNG", f.split("\\")[-1], im.size[:], "rgb max", a[..., :3].max().round(3), "rgb mean", a[..., :3].mean().round(4), "alpha min/max", a[..., 3].min(), a[..., 3].max())
