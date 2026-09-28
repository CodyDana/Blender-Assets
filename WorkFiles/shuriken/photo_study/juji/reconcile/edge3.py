import numpy as np, json
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
rgb=np.load(P+"contour/juji_rgb.npy").astype(np.float64); H,W,_=rgb.shape
def s2l(c): return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
lin=s2l(rgb)
A=np.load(P+"radial/mask_final.npy").astype(float); B=np.load(P+"contour/mask_refined.npy").astype(float)
def bil3(M,x,y):
    x=np.clip(x,0,W-1.001);y=np.clip(y,0,H-1.001)
    x0=np.floor(x).astype(int);y0=np.floor(y).astype(int);fx=(x-x0)[...,None];fy=(y-y0)[...,None]
    return (M[y0,x0]*(1-fx)*(1-fy)+M[y0,x0+1]*fx*(1-fy)+M[y0+1,x0]*(1-fx)*fy+M[y0+1,x0+1]*fx*fy)
def bil1(M,x,y): return bil3(M[...,None],x,y)[...,0]
C=np.array([694.10,651.11]); arms={'right':1.44,'top':91.67,'left':181.93,'bottom':271.77}
tt=np.arange(0,140.25,0.25)
rows=[]
for region,(s0,s1) in (("neck",(150,261)),("blade",(400,500))):
    for name,th in arms.items():
        t=np.radians(th); d=np.array([np.cos(t),-np.sin(t)]); n=np.array([-d[1],d[0]])
        ss=np.arange(s0,s1,1.0)
        for sgn in (+1,-1):
            v=sgn*n
            dirlab=('+x' if v[0]>0.7 else '-x' if v[0]<-0.7 else '+y' if v[1]>0 else '-y')
            acc=np.zeros((len(tt),3)); ea=[]; eb=[]
            for s in ss:
                p=C+s*d; pts=p[None,:]+tt[:,None]*v[None,:]
                acc+=bil3(lin,pts[:,0],pts[:,1])
                pa=bil1(A,pts[:,0],pts[:,1]); pb=bil1(B,pts[:,0],pts[:,1])
                ia=np.where(pa<0.5)[0]; ib=np.where(pb<0.5)[0]
                if len(ia): ea.append(tt[ia[0]])
                if len(ib): eb.append(tt[ib[0]])
            acc/=len(ss)
            Y=acc@np.array([0.2126,0.7152,0.0722]); ch=(acc[:,0]-acc[:,2])/(acc.sum(1)+1e-9)
            mA=np.mean(ea); mB=np.mean(eb); g=0.5*(mA+mB)
            inl=np.median(ch[(tt>max(3,g-40))&(tt<g-12)])
            outl=np.median(ch[(tt>g+35)&(tt<g+70)])
            h=0.5*(inl+outl)
            cr=np.nan
            for i in range(1,len(tt)):
                if ch[i]<h<=ch[i-1] and tt[i]>g-30:
                    cr=tt[i-1]+0.25*(ch[i-1]-h)/(ch[i-1]-ch[i]); break
            # Y crossing too
            inY=np.median(Y[(tt>max(3,g-40))&(tt<g-12)]); outY=np.median(Y[(tt>g+35)&(tt<g+70)]); hY=0.5*(inY+outY)
            crY=np.nan
            for i in range(1,len(tt)):
                if (Y[i]-hY)*(Y[i-1]-hY)<=0 and tt[i]>g-30 and Y[i]>Y[i-1]:
                    crY=tt[i-1]+0.25*(hY-Y[i-1])/(Y[i]-Y[i-1]+1e-12); break
            rows.append((region,name,dirlab,mA,mB,cr,crY,inl,outl,inY,outY))
            print(f"{region:5s} {name:6s} out={dirlab}  A={mA:6.1f} B={mB:6.1f} | chr50={cr:6.1f} (in{inl:.3f}/out{outl:.3f})  Y50={crY:6.1f} (in{inY:.3f}/out{outY:.3f})")
json.dump([list(map(lambda z: z if isinstance(z,str) else float(z),r)) for r in rows],open("edge3.json","w"),indent=1)
print()
for region in ("neck","blade"):
    R=[r for r in rows if r[0]==region]
    dA=np.mean([r[5]-r[3] for r in R]); dB=np.mean([r[5]-r[4] for r in R])
    print(f"{region}: mean(chr50 - A) = {dA:+.2f} px ; mean(chr50 - B) = {dB:+.2f} px ; mean width A={2*np.mean([r[3] for r in R]):.1f} B={2*np.mean([r[4] for r in R]):.1f} chr50={2*np.mean([r[5] for r in R]):.1f}")
