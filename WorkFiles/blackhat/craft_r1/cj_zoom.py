import bpy, numpy as np
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/craft_r1/r/"
def load(n):
    im=bpy.data.images.load(D+n+".png"); a=np.array(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],im.channels)[::-1]; return a[...,:3]
def save(a,n):
    h,w=a.shape[:2]; im=bpy.data.images.new(n,w,h); px=np.ones((h,w,4),np.float32); px[...,:3]=a; im.pixels[:]=px[::-1].ravel(); im.filepath_raw=D+n+".png"; im.file_format='PNG'; im.save()
ims=[load(f"lod{l}_648") for l in range(3)]
m=(np.abs(ims[0]-ims[0][2,2]).sum(-1)>0.03); ys,xs=np.where(m); print(xs.min(),xs.max(),ys.min(),ys.max())
cr=[a[ys.min()-5:ys.max()+5, xs.min()-5:xs.max()+5] for a in ims]
save(np.concatenate(cr[1:],0).repeat(2,0).repeat(2,1),"zoom_lod12_648")
ims=[load(f"lod{l}_227") for l in range(3)]
m=(np.abs(ims[0]-ims[0][2,2]).sum(-1)>0.03); ys,xs=np.where(m); print(xs.min(),xs.max(),ys.min(),ys.max())
cr=[a[ys.min()-5:ys.max()+5, xs.min()-5:xs.max()+5] for a in ims]
save(np.concatenate(cr,1).repeat(4,0).repeat(4,1),"zoom_lod_227")
