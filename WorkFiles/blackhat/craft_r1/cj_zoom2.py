import bpy, numpy as np
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/craft_r1/r/"
def load(n):
    im=bpy.data.images.load(D+n+".png"); a=np.array(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],im.channels)[::-1]; return a[...,:3]
def save(a,n):
    h,w=a.shape[:2]; im=bpy.data.images.new(n,w,h); px=np.ones((h,w,4),np.float32); px[...,:3]=a; im.pixels[:]=px[::-1].ravel(); im.filepath_raw=D+n+".png"; im.file_format='PNG'; im.save()
fr=[load(f"turn_hero_{i:02d}")[216:470,267:692] for i in (0,1,2,3)]
top=np.concatenate(fr[:2],1); bot=np.concatenate(fr[2:],1)
save(np.concatenate([top,bot],0).repeat(2,0).repeat(2,1),"zoom_turn4")
