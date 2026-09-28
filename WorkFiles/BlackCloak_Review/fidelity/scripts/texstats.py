import bpy,numpy as np
T=r"C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/Textures/"
for n,cs in (("T_BlackCloak_BaseColor.png","sRGB"),("T_BlackCloak_Roughness.png","Non-Color"),("T_BlackCloak_Normal_OpenGL.png","Non-Color"),("T_BlackCloak_Normal_DirectX.png","Non-Color")):
    im=bpy.data.images.load(T+n); im.colorspace_settings.name='Non-Color'
    a=np.array(im.pixels[:],np.float32).reshape(im.size[1],im.size[0],im.channels)
    print(n,im.size[:],im.channels,im.depth,"mean",a[...,:3].reshape(-1,3).mean(0).round(4),"min",a[...,:3].min().round(4),"max",a[...,:3].max().round(4),"std",a[...,0].std().round(4), "p1,50,99 R", np.percentile(a[...,0],[1,50,99]).round(4))
