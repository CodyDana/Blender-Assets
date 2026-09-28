import bpy, numpy as np, sys
p=sys.argv[-1]; im=bpy.data.images.load(p); im.colorspace_settings.name='Non-Color'
a=np.array(im.pixels[:]).reshape(im.size[1],im.size[0],im.channels)[::-1]
al=a[...,3]; part=(al>0.01)&(al<0.98)
ys,xs=np.nonzero(part); print("PARTIAL", part.sum(), "rows", np.percentile(ys,[5,50,95]) if len(ys) else None)
print("ALPHA rows 640-674 max-min", [round(float(al[y].max()),3) for y in range(640,674,4)])
