import bpy, numpy as np
def load(p):
    im = bpy.data.images.load(p); w,h = im.size
    return np.array(im.pixels[:], dtype=np.float32).reshape(h,w,4)[::-1]
def save(arr, dst):
    H,W = arr.shape[:2]
    out = bpy.data.images.new("s", W, H, alpha=True)
    rgba = np.ones((H,W,4),np.float32); rgba[...,:3]=arr
    out.pixels[:] = rgba[::-1].ravel(); out.filepath_raw=dst; out.file_format='PNG'; out.save()
R="C:/Users/Cody/Desktop/Blender_Projects/References/Fan/"; O="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/study/"
for name,(cx,cy),r0,r1 in [("fan2",(398,546),60,160),("fan1",(391,600),60,200)]:
    a = load(R+name+".png")
    th = np.linspace(np.pi, 0, 2400); rr = np.linspace(r1, r0, 120)
    T,Rr = np.meshgrid(th, rr)
    X = cx + Rr*np.cos(T); Y = cy - Rr*np.sin(T)
    x0=np.floor(X).astype(int); y0=np.floor(Y).astype(int); fx=X-x0; fy=Y-y0
    x0=np.clip(x0,0,798); y0=np.clip(y0,0,798)
    P = (a[y0,x0,:3]*((1-fx)*(1-fy))[...,None] + a[y0,x0+1,:3]*(fx*(1-fy))[...,None] + a[y0+1,x0,:3]*((1-fx)*fy)[...,None] + a[y0+1,x0+1,:3]*(fx*fy)[...,None])
    P = np.clip((P-P.min())/(np.percentile(P,99)-P.min()),0,1)**0.6
    for i in range(3):
        save(P[:, i*800:(i+1)*800], O+f"fanstudy_{name}_gorge_{i}.png")
