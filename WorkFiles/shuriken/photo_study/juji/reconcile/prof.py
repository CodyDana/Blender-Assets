import numpy as np, json
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
rgb=np.load(P+"contour/juji_rgb.npy").astype(np.float64)   # (1363,1370,3) sRGB stored
H,W,_=rgb.shape
def srgb2lin(c):
    return np.where(c<=0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
lin=srgb2lin(rgb)
L=0.2126*lin[...,0]+0.7152*lin[...,1]+0.0722*lin[...,2]
S=lin.sum(2)+1e-9
chrRB=(lin[...,0]-lin[...,2])/S      # warm chromaticity, shading-invariant
Lsrgb=rgb.mean(2)

def bil(A,x,y):
    x=np.clip(x,0,W-1.001); y=np.clip(y,0,H-1.001)
    x0=np.floor(x).astype(int); y0=np.floor(y).astype(int)
    fx=x-x0; fy=y-y0
    return (A[y0,x0]*(1-fx)*(1-fy)+A[y0,x0+1]*fx*(1-fy)+A[y0+1,x0]*(1-fx)*fy+A[y0+1,x0+1]*fx*fy)

C=np.array([694.10,651.11])
arms={'right':1.44,'top':91.67,'left':181.93,'bottom':271.77}
maskA=np.load(P+"radial/mask_final.npy"); maskB=np.load(P+"contour/mask_refined.npy")

for name,th in arms.items():
    t=np.radians(th)
    d=np.array([np.cos(t),-np.sin(t)])      # along arm (image coords, y down)
    n=np.array([-d[1],d[0]])                # perpendicular
    for s in ([200,460] if name in('right','left') else [200,420]):
        p=C+s*d
        tt=np.arange(-130,130.25,0.5)
        pts=p[None,:]+tt[:,None]*n[None,:]
        Lp=bil(Lsrgb,pts[:,0],pts[:,1]); Cp=bil(chrRB,pts[:,0],pts[:,1])
        Ap=bil(maskA.astype(float),pts[:,0],pts[:,1]); Bp=bil(maskB.astype(float),pts[:,0],pts[:,1])
        def edges(prof):
            idx=np.where(prof>0.5)[0]
            return (tt[idx[0]],tt[idx[-1]]) if len(idx) else (np.nan,np.nan)
        ea=edges(Ap); eb=edges(Bp)
        print(f"\n=== {name} s={s}  A edges {ea[0]:+.1f},{ea[1]:+.1f} (w {ea[1]-ea[0]:.1f})   B edges {eb[0]:+.1f},{eb[1]:+.1f} (w {eb[1]-eb[0]:.1f})")
        print("   t     Lsrgb   chrRB   |   t     Lsrgb   chrRB")
        sel=np.arange(0,len(tt),4)
        half=len(sel)//2
        for i in range(half):
            a=sel[i]; b=sel[i+half]
            print(f"{tt[a]:+7.1f} {Lp[a]:7.3f} {Cp[a]:7.4f}   | {tt[b]:+7.1f} {Lp[b]:7.3f} {Cp[b]:7.4f}")
