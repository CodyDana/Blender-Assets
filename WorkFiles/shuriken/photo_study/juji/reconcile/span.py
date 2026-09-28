import numpy as np
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
rgb=np.load(P+"contour/juji_rgb.npy").astype(np.float64); H,W,_=rgb.shape
def s2l(c): return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
lin=s2l(rgb)
def bil3(M,x,y):
    x=np.clip(x,0,W-1.001);y=np.clip(y,0,H-1.001)
    x0=np.floor(x).astype(int);y0=np.floor(y).astype(int);fx=(x-x0)[...,None];fy=(y-y0)[...,None]
    return (M[y0,x0]*(1-fx)*(1-fy)+M[y0,x0+1]*fx*(1-fy)+M[y0+1,x0]*(1-fx)*fy+M[y0+1,x0+1]*fx*fy)
C=np.array([694.10,651.11]); arms={'right':1.44,'top':91.67,'left':181.93,'bottom':271.77}
tt=np.arange(560,720.25,0.25)
print("tip apex by chromaticity half-contrast, averaged over a +-8px strip about the arm axis:")
Rs={}
for name,th in arms.items():
    t=np.radians(th); d=np.array([np.cos(t),-np.sin(t)]); n=np.array([-d[1],d[0]])
    acc=np.zeros((len(tt),3))
    offs=np.arange(-8,8.1,1.0)
    for o in offs:
        pts=C[None,:]+tt[:,None]*d[None,:]+o*n[None,:]
        acc+=bil3(lin,pts[:,0],pts[:,1])
    acc/=len(offs)
    ch=(acc[:,0]-acc[:,2])/(acc.sum(1)+1e-9)
    inl=np.median(ch[(tt>580)&(tt<620)]); outl=np.median(ch[tt>700]); h=0.5*(inl+outl)
    cr=np.nan
    for i in range(1,len(tt)):
        if ch[i]<h<=ch[i-1]: cr=tt[i-1]+0.25*(ch[i-1]-h)/(ch[i-1]-ch[i]); break
    Rs[name]=cr
    print(f"  {name:6s} chr50 R = {cr:7.2f} px   (in {inl:.3f} out {outl:.3f})")
print()
print(f"horizontal span (right+left) = {Rs['right']+Rs['left']:.1f} px")
print(f"vertical   span (top+bottom) = {Rs['top']+Rs['bottom']:.1f} px  [top clipped -> lower bound]")
print("A: 1329.9 horiz;  B: 1321.3 horiz")
