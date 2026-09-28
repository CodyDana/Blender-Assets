import numpy as np
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
rgb=np.load(P+"contour/juji_rgb.npy").astype(np.float64)
H,W,_=rgb.shape
def s2l(c): return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
lin=s2l(rgb)
def bil3(A,x,y):
    x=np.clip(x,0,W-1.001); y=np.clip(y,0,H-1.001)
    x0=np.floor(x).astype(int);y0=np.floor(y).astype(int);fx=(x-x0)[...,None];fy=(y-y0)[...,None]
    return (A[y0,x0]*(1-fx)*(1-fy)+A[y0,x0+1]*fx*(1-fy)+A[y0+1,x0]*(1-fx)*fy+A[y0+1,x0+1]*fx*fy)
C=np.array([694.10,651.11])
arms={'right':1.44,'top':91.67,'left':181.93,'bottom':271.77}
tt=np.arange(-140,60.5,0.5)
for name,th in arms.items():
    t=np.radians(th); d=np.array([np.cos(t),-np.sin(t)]); n=np.array([-d[1],d[0]])
    ss=np.arange(150,260,1.0)   # neck run
    for sgn,lab in ((-1,'side-'),(+1,'side+')):
        acc=np.zeros((len(tt),3))
        for s in ss:
            p=C+s*d
            pts=p[None,:]+(sgn*tt)[:,None]*n[None,:]
            acc+=bil3(lin,pts[:,0],pts[:,1])
        acc/=len(ss)
        Y=acc@np.array([0.2126,0.7152,0.0722]); chr=(acc[:,0]-acc[:,2])/(acc.sum(1)+1e-9)
        # outward direction in image coords
        v=sgn*n; dirlab=('+x' if v[0]>0.7 else '-x' if v[0]<-0.7 else '+y' if v[1]>0 else '-y')
        print(f"\n--- {name} {lab} outward={dirlab}  (neck run s=150..260)")
        print("  t    Y(lin)  chrRB")
        for i in range(0,len(tt),4):
            print(f"{tt[i]:+6.1f} {Y[i]:7.4f} {chr[i]:7.4f}")
