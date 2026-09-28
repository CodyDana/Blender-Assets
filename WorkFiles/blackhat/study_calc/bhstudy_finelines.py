"""bhstudy_finelines.py - fine radial lines (secondary splints / weave seams) between the main ribs.
Profiles of luma along azimuth, averaged over slant fraction 0.40-0.90, band-passed 0.4-2 deg; dark and bright peaks."""
import json, numpy as np, OpenImageIO as oiio
ROOT="C:/Users/Cody/Desktop/Blender_Projects"; OUT=ROOT+"/WorkFiles/blackhat/study_calc"
fit=json.load(open(OUT+"/bhstudy_unwrap.json"))
px=oiio.ImageBuf(ROOT+"/References/BlackHat/blackhat_guide.png").get_pixels(oiio.FLOAT); H,W=px.shape[:2]
L=(0.2126*px[...,0]+0.7152*px[...,1]+0.0722*px[...,2]).astype(np.float64)
xc=fit["centre_x_px"]; xa,ya=fit["virtual_apex_px"]; A=fit["projection"]["A_roll_centre_px"]; B=fit["projection"]["B_px"]; D=fit["projection"]["D_direct_px"]
def bil(x,y):
    x=np.clip(x,0,W-1.001); y=np.clip(y,0,H-1.001); x0=x.astype(int); y0=y.astype(int); fx=x-x0; fy=y-y0
    return L[y0,x0]*(1-fx)*(1-fy)+L[y0,x0+1]*fx*(1-fy)+L[y0+1,x0]*(1-fx)*fy+L[y0+1,x0+1]*fx*fy
st=0.05; ph=np.arange(-72,36,st); P=np.radians(ph)
def prof(f0,f1):
    return np.mean([bil(xc+f*A*np.sin(P), ya+f*(D+B*np.cos(P))) for f in np.linspace(f0,f1,60)],0)
def box(p,h):
    k=int(round(h/st)); pad=np.pad(p,(k,k),mode="edge"); c=np.cumsum(np.insert(pad,0,0)); return (c[2*k+1:]-c[:-2*k-1])/(2*k+1)
out={}
for nm,(f0,f1) in {"upper":(0.40,0.62),"lower":(0.62,0.90)}.items():
    p=prof(f0,f1); bp=box(p,0.2)-box(p,2.0); s=bp.std()
    dk=[]; 
    for i in np.argsort(bp):
        if bp[i]>-2*s: break
        if all(abs(ph[i]-q)>=3 for q in dk): dk.append(float(ph[i]))
    br=[]
    for i in np.argsort(-bp):
        if bp[i]<2*s: break
        if all(abs(ph[i]-q)>=3 for q in br): br.append(float(ph[i]))
    out[nm]={"dark_gt2sd":sorted(round(q,1) for q in dk),"bright_gt2sd":sorted(round(q,1) for q in br)}
json.dump(out,open(OUT+"/bhstudy_finelines.json","w"),indent=1); print(json.dumps(out,indent=1))
