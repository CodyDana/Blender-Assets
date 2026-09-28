import bpy, numpy as np, sys, glob
for f in sorted(glob.glob(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\SnowFlower\v4\UnrealVerify_Indep\renders\*.exr")):
    im = bpy.data.images.load(f); im.colorspace_settings.name = "Non-Color"
    a = np.array(im.pixels[:]).reshape(im.size[1], im.size[0], im.channels)
    print("EXR", f[-25:], im.size[:], a[..., 0].min(), a[..., 0].max(), np.unique(a[..., 0])[:5])
