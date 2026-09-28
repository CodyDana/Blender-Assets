from PIL import Image
import numpy as np, json, math
IMG='C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg'
im=np.asarray(Image.open(IMG)).astype(float)
H,W,_=im.shape
# background colour samples around ring (inside hole and outside)
hole=im[228:240,115:128].reshape(-1,3).mean(0)
outs=np.concatenate([im[200:206,95:150].reshape(-1,3),im[266:272,95:150].reshape(-1,3),im[220:250,86:90].reshape(-1,3)]).mean(0)
print('hole bg',hole,'outside bg',outs)
def bilin(img,x,y):
    x0=np.floor(x).astype(int); y0=np.floor(y).astype(int); fx=x-x0; fy=y-y0
    x0=np.clip(x0,0,W-2); y0=np.clip(y0,0,H-2)
    return (img[y0,x0]*(1-fx)*(1-fy)+img[y0,x0+1]*fx*(1-fy)+img[y0+1,x0]*(1-fx)*fy+img[y0+1,x0+1]*fx*fy)
def score(bg):
    d=np.linalg.norm(im-bg,axis=2)
    return d
cx,cy=122.0,234.5
res=[]
for it in range(3):
    inner=[];outer=[]
    for a in np.arange(0,360,2.0):
        t=math.radians(a); dx,dy=math.cos(t),math.sin(t)
        rs=np.arange(0,40,0.1)
        xs=cx+rs*dx; ys=cy+rs*dy
        cols=np.stack([bilin(im[...,k],xs,ys) for k in range(3)],1)
        dh=np.linalg.norm(cols-hole,axis=1); do=np.linalg.norm(cols-outs,axis=1)
        # object-ness: min distance to either bg colour, normalized
        obj=np.minimum(dh,do)
        thr=0.5*np.median(obj[(rs>11)&(rs<22)]) if False else None
        # inner crossing: first r where dh exceeds half of its plateau
        plateau=np.percentile(dh[(rs>14)&(rs<24)],50)
        thr_i=0.5*plateau
        i=np.argmax(dh>thr_i)
        ri=rs[i-1]+(thr_i-dh[i-1])/(dh[i]-dh[i-1])*0.1 if i>0 else np.nan
        # outer crossing: last r (<38) where do exceeds half plateau
        plat_o=np.percentile(do[(rs>14)&(rs<24)],50)
        thr_o=0.5*plat_o
        idx=np.where(do[:380]>thr_o)[0]
        j=idx[-1] if len(idx) else 0
        ro=rs[j]+(do[j]-thr_o)/(do[j]-do[j+1])*0.1 if 0<j<399 else np.nan
        inner.append((a,cx+ri*dx,cy+ri*dy,ri)); outer.append((a,cx+ro*dx,cy+ro*dy,ro))
    res=(inner,outer)
    ins=np.array([p[1:3] for p in inner if not np.isnan(p[3])])
    cx,cy=ins.mean(0)
print('centre',cx,cy)
def fit_ellipse(P):
    x,y=P[:,0],P[:,1]
    D=np.stack([x*x,x*y,y*y,x,y,np.ones_like(x)],1)
    # direct least squares with constraint via SVD (algebraic), then convert
    _,_,V=np.linalg.svd(D); A,B,C,Dd,E,F=V[-1]
    M=np.array([[A,B/2],[B/2,C]])
    c=np.linalg.solve(2*M,[-Dd,-E])
    Fc=F+ (A*c[0]**2+B*c[0]*c[1]+C*c[1]**2+Dd*c[0]+E*c[1]) - (A*c[0]**2+B*c[0]*c[1]+C*c[1]**2)*0
    # value at centre
    f0=A*c[0]**2+B*c[0]*c[1]+C*c[1]**2+Dd*c[0]+E*c[1]+F
    w,v=np.linalg.eigh(M)
    axes=np.sqrt(-f0/w)
    order=np.argsort(-axes)
    axes=axes[order]; v=v[:,order]
    ang=math.degrees(math.atan2(v[1,0],v[0,0]))
    r=np.array([ (p-c)@np.linalg.inv(v@np.diag(axes**2)@v.T)@(p-c) for p in P])
    return dict(cx=c[0],cy=c[1],a=axes[0],b=axes[1],major_angle_deg=ang,aspect=axes[1]/axes[0],resid=float(np.std(np.sqrt(r)-1)*axes.mean()))
inner,outer=res
out={}
# exclude grip side: grip leaves the ring toward upper right (angles ~ -60..+10 in image coords, y down)
for name,pts,excl in [('inner',inner,None),('outer',outer,(-75,20))]:
    P=[]
    for a,x,y,r in pts:
        aa=a if a<=180 else a-360
        if np.isnan(r): continue
        if excl and excl[0]<=aa<=excl[1]: continue
        P.append((x,y))
    P=np.array(P)
    f=fit_ellipse(P)
    # robust refit: drop worst 15%
    c=np.array([f['cx'],f['cy']])
    for k in range(2):
        th=math.radians(f['major_angle_deg']); R=np.array([[math.cos(th),-math.sin(th)],[math.sin(th),math.cos(th)]])
        Q=(P-[f['cx'],f['cy']])@R
        e=np.abs(np.sqrt((Q[:,0]/f['a'])**2+(Q[:,1]/f['b'])**2)-1)
        keep=e<np.percentile(e,85)
        P=P[keep]; f=fit_ellipse(P)
    f['n']=len(P); f['pts']=P.tolist()
    out[name]=f
    print(name,{k:(round(v,3) if isinstance(v,float) else v) for k,v in f.items() if k!='pts'})
json.dump({'inner':out['inner'],'outer':out['outer'],'raw_inner':inner,'raw_outer':outer},open('ring_fit.json','w'),indent=1,default=float)
