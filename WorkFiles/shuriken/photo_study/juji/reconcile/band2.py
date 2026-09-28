import numpy as np
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
rgb=np.load(P+"contour/juji_rgb.npy").astype(np.float64); H,W,_=rgb.shape
def s2l(c): return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
lin=s2l(rgb)
def bil3(A,x,y):
    x=np.clip(x,0,W-1.001); y=np.clip(y,0,H-1.001)
    x0=np.floor(x).astype(int);y0=np.floor(y).astype(int);fx=(x-x0)[...,None];fy=(y-y0)[...,None]
    return (A[y0,x0]*(1-fx)*(1-fy)+A[y0,x0+1]*fx*(1-fy)+A[y0+1,x0]*(1-fx)*fy+A[y0+1,x0+1]*fx*fy)
C=np.array([694.10,651.11]); arms={'right':1.44,'top':91.67,'left':181.93,'bottom':271.77}
tt=np.arange(-60,120.5,0.5)
res={}
for name,th in arms.items():
    t=np.radians(th); d=np.array([np.cos(t),-np.sin(t)]); n=np.array([-d[1],d[0]])
    ss=np.arange(150,261,1.0)
    for sgn in (+1,-1):
        v=sgn*n
        dirlab=('+x' if v[0]>0.7 else '-x' if v[0]<-0.7 else '+y' if v[1]>0 else '-y')
        acc=np.zeros((len(tt),3))
        for s in ss:
            p=C+s*d; pts=p[None,:]+tt[:,None]*v[None,:]
            acc+=bil3(lin,pts[:,0],pts[:,1])
        acc/=len(ss)
        Y=acc@np.array([0.2126,0.7152,0.0722]); ch=(acc[:,0]-acc[:,2])/(acc.sum(1)+1e-9)
        res[(name,dirlab)]=(Y.copy(),ch.copy())
        # 50% crossings
        inY=np.median(Y[(tt>-50)&(tt<-20)]); inC=np.median(ch[(tt>-50)&(tt<-20)])
        outY=np.median(Y[(tt>80)]); outC=np.median(ch[(tt>80)])
        def cross(prof,a,b):
            h=0.5*(a+b); idx=np.where(tt>0)[0]
            for i in idx:
                if (prof[i]-h)*(a-h)<0:
                    j=i-1; f=(h-prof[j])/(prof[i]-prof[j]+1e-12); return tt[j]+f*0.5
            return np.nan
        cy=cross(Y,inY,outY); cc=cross(ch,inC,outC)
        print(f"{name:7s} out={dirlab}  in(Y={inY:.3f},chr={inC:.3f}) out(Y={outY:.3f},chr={outC:.3f})  50%Y at t={cy:+6.2f}  50%chr at t={cc:+6.2f}")
np.save("prof_res.npy",np.array([tt]),allow_pickle=True)
import pickle; pickle.dump((tt,res),open("prof_res.pkl","wb"))
print()
# print the -y sides in detail (the disputed ones) and one control
for k in [('right','-y'),('left','-y'),('right','+y'),('top','-x'),('top','+x')]:
    Y,ch=res[k]; print(f"\n=== {k}"); print("  t     Ylin    chrRB")
    for i in range(0,len(tt),4):
        if -20<=tt[i]<=110: print(f"{tt[i]:+6.1f} {Y[i]:7.4f} {ch[i]:7.4f}")
