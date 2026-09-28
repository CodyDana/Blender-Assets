import bpy, numpy as np, json
T=r"C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/Textures/"
def load(p):
    im=bpy.data.images.load(p,check_existing=False); im.colorspace_settings.name='Non-Color'
    w,h=im.size;c=im.channels;a=np.empty(w*h*c,np.float32);im.pixels.foreach_get(a);bpy.data.images.remove(im);return a.reshape(h,w,c)
bc=load(T+"T_BlackCloak_BaseColor.png")[...,0]
lin=np.where(bc<=0.04045,bc/12.92,((bc+0.055)/1.055)**2.4)
n=load(T+"T_BlackCloak_Normal_DirectX.png")
nx=n[...,0]*2-1; ny=n[...,1]*2-1; nz=n[...,2]*2-1
R={}
for m in (0,2,3,4,5):
    k=2**m; H=lin.shape[0]//k
    L=lin[:H*k,:H*k].reshape(H,k,H,k).mean((1,3))
    X=nx.reshape(H,k,H,k).mean((1,3)); Y=ny.reshape(H,k,H,k).mean((1,3)); Z=nz.reshape(H,k,H,k).mean((1,3))
    tilt=np.degrees(np.arctan2(np.hypot(X,Y),Z))
    R[f'mip{m}']={'bc_std_over_mean':round(float(L.std()/L.mean()),4),'n_mean_tilt_deg':round(float(tilt.mean()),3)}
print(json.dumps(R))
json.dump(R,open(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/verify_look/vl_mips.json","w"),indent=1)
