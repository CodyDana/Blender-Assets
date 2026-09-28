from PIL import Image
import numpy as np, json
IMG='C:/Users/Cody/Desktop/Blender_Projects/References/Kunai/kunai_reference2.jpg'
im=np.asarray(Image.open(IMG)).astype(float)
L=im.mean(2); q=im[...,0]-im[...,2]
def colprof(x):  # column profile, integer x
    return L[:,x], q[:,x]
def cross_up(p,y0,y1,thr):
    # first index in [y0,y1) where p goes from <thr to >=thr, subpixel
    for y in range(y0,y1-1):
        if p[y]<thr<=p[y+1]: return y+(thr-p[y])/(p[y+1]-p[y])
    return np.nan
def cross_dn(p,y0,y1,thr):
    for y in range(y0,y1-1):
        if p[y]>=thr>p[y+1]: return y+(p[y]-thr)/(p[y]-p[y+1])
    return np.nan
pts={'top_front':[],'ridge_front':[],'bot_front':[],'bot_rear':[],'ridge_rear':[]}
for x in range(262,404):
    p=L[:,x]
    # guesses from eyeballed lines
    yt=131.7-0.182*(x-287.5); yr=159.2-0.413*(x-300); yb=189.2-0.826*(x-314.2)
    if x>=291:
        # top edge: moving down from bg into steel; threshold halfway between bg (median 3-6 px above) and max within 2px below
        y0=int(yt)-4
        bg=np.median(p[y0-4:y0]); pk=p[y0:y0+7].max()
        pts['top_front'].append((x,cross_up(p,y0,y0+7,(bg+pk)/2)))
    if x>=303:
        y0=int(yr)-4
        lit=np.median(p[y0-6:y0]); dk=np.median(p[y0+5:y0+10])
        pts['ridge_front'].append((x,cross_dn(p,y0,y0+8,(lit+dk)/2)))
    if x>=318:
        y0=int(yb)-4
        dk=np.median(p[y0-8:y0-2]); bg=np.median(p[y0+6:y0+11])
        # last crossing going down from dark to bg
        pts['bot_front'].append((x,cross_up(p,y0,y0+9,(dk+bg)/2)))
    if 268<=x<=310:
        y0=184
        dk=np.median(p[176:183]); bg=np.median(p[192:197])
        pts['bot_rear'].append((x,cross_up(p,y0,y0+8,(dk+bg)/2)))
    if 266<=x<=296:
        yr2=171.7-0.375*(x-260)
        y0=int(yr2)-4
        lit=np.median(p[y0-6:y0]); dk=np.median(p[y0+5:y0+10])
        pts['ridge_rear'].append((x,cross_dn(p,y0,y0+8,(lit+dk)/2)))
# top rear edge: steep, use rows
pts['top_rear']=[]
for y in range(136,166):
    p=L[y,:]
    xg=287.5-(y-131.7)/1.3
    x0=int(xg)-5
    bg=np.median(p[x0-5:x0]); pk=p[x0:x0+9].max()
    pts['top_rear'].append((cross_up(p,x0,x0+9,(bg+pk)/2),y))
def fitline(P,robust=True):
    P=np.array([p for p in P if not np.any(np.isnan(p))],float)
    keep=np.ones(len(P),bool)
    for it in range(4):
        Q=P[keep]; c=Q.mean(0); _,s,V=np.linalg.svd(Q-c); d=V[0]; n=np.array([-d[1],d[0]])
        r=(P-c)@n
        sd=np.std(r[keep])
        keep=np.abs(r)<max(2.5*sd,0.6)
    return dict(c=c.tolist(),d=d.tolist(),n=n.tolist(),rms=float(np.std(r[keep])),n_used=int(keep.sum()),n_total=len(P),resid=r.tolist(),pts=P.tolist(),keep=keep.tolist())
fits={k:fitline(v) for k,v in pts.items()}
for k,f in fits.items():
    ang=np.degrees(np.arctan2(f['d'][1],f['d'][0]))
    print(k,'c',np.round(f['c'],2),'angle',round(ang,2),'rms',round(f['rms'],3),f['n_used'],'/',f['n_total'])
json.dump(fits,open('blade_lines.json','w'))
