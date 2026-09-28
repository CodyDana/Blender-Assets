import bpy, numpy as np, sys
for p,cs in [(sys.argv[-2],'Non-Color'),(sys.argv[-1],'Non-Color')]:
    im=bpy.data.images.load(p); im.colorspace_settings.name=cs
    a=np.array(im.pixels[:]).reshape(im.size[1],im.size[0],im.channels)
    print(p, im.size, im.is_float, im.depth, 'mean',a[...,:3].mean(), 'median', np.median(a[...,0]), 'center', a[a.shape[0]//2, a.shape[1]//2])
