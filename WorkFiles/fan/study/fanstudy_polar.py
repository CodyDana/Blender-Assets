import bpy, numpy as np, json
def load(p):
    im = bpy.data.images.load(p); w,h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h,w,4)[::-1]
    return a
def save(arr, dst):
    H,W = arr.shape[:2]
    out = bpy.data.images.new("s", W, H, alpha=True)
    rgba = np.ones((H,W,4),np.float32); rgba[...,:3]=arr[...,:3] if arr.ndim==3 else arr[...,None]
    out.pixels[:] = rgba[::-1].ravel(); out.filepath_raw=dst; out.file_format='PNG'; out.save()
R="C:/Users/Cody/Desktop/Blender_Projects/References/Fan/"
O="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/study/"
for name,(cx,cy) in {"fan2":(398,546),"fan1":(390,598)}.items():
    a = load(R+name+".png")
    # polar unwrap: angle 0..180 (left to right over the top), radius 20..380, y image down
    th = np.linspace(np.pi, 0, 1440); rr = np.arange(10, 400)
    T,Rr = np.meshgrid(th, rr)
    X = cx + Rr*np.cos(T); Y = cy - Rr*np.sin(T)
    Xi = np.clip(X.round().astype(int),0,799); Yi=np.clip(Y.round().astype(int),0,799)
    P = a[Yi,Xi,:3]
    save(P[::-1], O+f"fanstudy_{name}_polar.png")
    print(name, "polar saved")
