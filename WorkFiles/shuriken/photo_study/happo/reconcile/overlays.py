import sys, os, numpy as np, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rlib as R
OUT=R.BASE  # overlays go in photo_study/happo/
rgb,w,h=R.load_rgb()
G=json.load(open(R.BASE+"/reconcile/reconciled_geom.json"))
B=json.load(open(R.BASE+"/contour/b7_results.json"))
C=np.array(G['centre']); span=G['span']
tips={int(k):np.array(v['vertex']) for k,v in G['tips'].items()}
notches={int(k):np.array(v['vertex']) for k,v in G['notches'].items()}
# per-notch floor gap (B's floor point measured in the reconciled frame)
def rgap(V,P):
    u=(V-C)/np.linalg.norm(V-C); return float((np.array(P)-V)@u)
gaps={n:rgap(notches[n],B['notches'][str(n)]['bottom_pt']) for n in range(8)}
# ---------- reconciled polygon: tip(t) -> notch(n) ... ; tip t is between notch t-1 and notch t (B naming: T_t-N_t, T_t-N_{t-1})
order=[]
for t in range(8):
    order.append(('T',t)); order.append(('N',t))
pts=[]
for kind,i in order:
    if kind=='T':
        pts.append(tips[i])
    else:
        V=notches[i]; Tp=tips[i]; Tn=tips[(i+1)%8]
        u1=(Tp-V)/np.linalg.norm(Tp-V); u2=(Tn-V)/np.linalg.norm(Tn-V)
        beta=math.acos(np.clip(u1@u2,-1,1)); g=max(gaps[i],0.5)
        rf=g/(1/math.sin(beta/2)-1); dt=rf/math.tan(beta/2)
        bis=(u1+u2)/np.linalg.norm(u1+u2); Cc=V+bis*(rf/math.sin(beta/2))
        A1=V+u1*dt; A2=V+u2*dt
        a1=math.atan2(*(A1-Cc)[::-1]); a2=math.atan2(*(A2-Cc)[::-1])
        da=(a2-a1+math.pi)%(2*math.pi)-math.pi
        for s in np.linspace(0,1,24): 
            a=a1+s*da; pts.append(Cc+rf*np.array([math.cos(a),math.sin(a)]))
poly=np.array(pts)
def densify(P,step=0.4):
    out=[]
    for a,b in zip(P,np.roll(P,-1,0)):
        n=max(2,int(np.linalg.norm(b-a)/step)); out.append(a+np.outer(np.linspace(0,1,n,endpoint=False),b-a))
    return np.vstack(out)
def raster(P,w,h):
    yy,xx=np.mgrid[0:h,0:w]; X=xx+0.5; Y=yy+0.5; inside=np.zeros((h,w),bool)
    for (x1,y1),(x2,y2) in zip(P,np.roll(P,-1,0)):
        if y1==y2: continue
        cond=((y1>Y)!=(y2>Y))
        xint=x1+(Y-y1)*(x2-x1)/(y2-y1)
        inside^=cond&(X<xint)
    return inside
rec_mask=raster(poly,w,h)
R.save_png(np.repeat(rec_mask[:,:,None].astype(np.float32),3,2), OUT+"/happo_reconciled_mask.png")
def stamp(img,P,col,rad=1.6):
    D=densify(P,0.4)
    r=int(math.ceil(rad))
    for dx in range(-r,r+1):
        for dy in range(-r,r+1):
            if dx*dx+dy*dy>rad*rad: continue
            x=np.round(D[:,0]+dx).astype(int); y=np.round(D[:,1]+dy).astype(int)
            ok=(x>=0)&(x<img.shape[1])&(y>=0)&(y<img.shape[0]); img[y[ok],x[ok]]=col
def mark(img,p,col,s=7):
    x,y=int(round(p[0])),int(round(p[1]))
    for d in range(-s,s+1):
        for q in (-1,0,1):
            for (xx,yy) in ((x+d,y+q),(x+q,y+d)):
                if 0<=xx<img.shape[1] and 0<=yy<img.shape[0]: img[yy,xx]=col
# ---------- built outline mapped into photo space (spans matched, centred, rotated to the photo's tips)
bo=json.load(open(R.BASE+"/reconcile/built_outline.json")); bm=np.load(R.BASE+"/reconcile/built_mask_mm.npy")
pol=np.array([G['tips'][str(t)]['polar'] for t in range(8)])
rot=float(np.degrees(np.angle(np.mean(np.exp(1j*np.radians((pol-np.arange(8)*45.0)*8)))))/8)  # circular mean mod 45
rot_built=np.mean(np.array(bo['tip_polar_deg'])-np.arange(8)*45.0)
theta=math.radians(rot-rot_built); s=span/100.0
yy,xx=np.mgrid[0:h,0:w]; X=xx+0.5-C[0]; Y=-(yy+0.5-C[1])      # y-up, px
xm=( math.cos(theta)*X+math.sin(theta)*Y)/s; ym=(-math.sin(theta)*X+math.cos(theta)*Y)/s
ix=np.round((xm-bo['origin_mm'])/bo['res_mm']).astype(int); iy=np.round((ym-bo['origin_mm'])/bo['res_mm']).astype(int)
ok=(ix>=0)&(ix<bo['N'])&(iy>=0)&(iy<bo['N'])
built=np.zeros((h,w),bool); built[ok]=bm[iy[ok],ix[ok]]
def _sh(a,dy,dx,fill):
    p=np.pad(a,1,mode='edge') if fill is None else np.pad(a,1,constant_values=fill)
    return p[1+dy:1+dy+a.shape[0],1+dx:1+dx+a.shape[1]]
def boundary(m,th=1):
    # no wrap-around: pad with edge values so a shape leaving the frame gets no false border
    e=m.copy()
    for _ in range(th):
        e=e&_sh(e,1,0,None)&_sh(e,-1,0,None)&_sh(e,0,1,None)&_sh(e,0,-1,None)
    d=m.copy()
    for _ in range(th):
        d=d|_sh(d,1,0,None)|_sh(d,-1,0,None)|_sh(d,0,1,None)|_sh(d,0,-1,None)
    return d&~e
GREEN=np.array([0.1,1.0,0.2]); MAG=np.array([1.0,0.15,0.85]); RED=np.array([1,0.1,0.1]); CYAN=np.array([0.1,0.9,1.0])
# overlay 1: reconciled
o1=rgb.copy(); stamp(o1,poly,GREEN,1.6)
for t in range(8): mark(o1,tips[t],RED,8)
for n in range(8): mark(o1,notches[n],CYAN,5)
mark(o1,C,RED,10)
R.save_png(o1,OUT+"/happo_overlay_reconciled.png")
# overlay 2: built (spans matched)
o2=rgb.copy(); o2[boundary(built,2)]=MAG; mark(o2,C,MAG,10)
R.save_png(o2,OUT+"/happo_overlay_built.png")
# overlay 3: comparison (photo dimmed)
o3=0.55*rgb+0.45; o3[built&~rec_mask]=o3[built&~rec_mask]*0.6+MAG*0.4
o3[boundary(built,2)]=MAG; stamp(o3,poly,GREEN,1.6)
R.save_png(o3,OUT+"/happo_overlay_compare.png")
# stats
inter=(rec_mask&built).sum(); uni=(rec_mask|built).sum()
# area of the full reconciled polygon (incl. the part of T5 beyond the frame) by shoelace
x,y=poly[:,0],poly[:,1]; A_poly=0.5*abs(np.dot(x,np.roll(y,-1))-np.dot(y,np.roll(x,-1)))
print('rotation photo tips %.3f deg (y-up), built %.3f; scale %.4f px/mm'%(rot,rot_built,s))
print('notch floor gaps (px):',{k:round(v,1) for k,v in gaps.items()})
print('reconciled polygon area %.0f px2 = %.4f span^2; built plan area %.1f mm2 = %.4f span^2'%(A_poly,A_poly/span**2,bo['area_mm2'],bo['area_mm2']/1e4))
print('in-frame IoU reconciled vs built(span-matched): %.3f ; built covers %.3f of photo, photo covers %.3f of built'%(inter/uni, inter/rec_mask.sum(), inter/built.sum()))
json.dump(dict(rotation_photo_deg=rot,scale_px_per_mm=s,gaps_px=gaps,poly_area_px=A_poly,poly_area_span2=A_poly/span**2,
               built_area_span2=bo['area_mm2']/1e4,iou=float(inter/uni)),open(R.BASE+"/reconcile/overlay_stats.json","w"),indent=1)
