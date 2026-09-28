import bpy, bmesh, numpy as np, json

W,H=720,1499
BASE=r"C:\Users\Cody\Desktop\Blender_Projects"
with open(BASE+r"\WorkFiles\kd_contours.json") as f:
    C=json.load(f)
# artwork values for the chitin-sparing test
img=bpy.data.images.get("Kamish_Daggers.webp")
if img is None:
    img=bpy.data.images.load(BASE+r"\References\Kamish_Daggers.webp")
a=np.empty(W*H*4,dtype=np.float32); img.pixels.foreach_get(a)
VAL=a.reshape(H,W,4)[...,:3].max(axis=2)

def polymask(poly):
    mm=np.zeros((H,W),bool)
    pts=[(p[0],H-1-p[1]) for p in poly]; n=len(pts)
    for row in range(H):
        xs=[]
        for i in range(n):
            x0,r0=pts[i]; x1,r1=pts[(i+1)%n]
            if (r0<=row<r1) or (r1<=row<r0):
                t=(row-r0)/(r1-r0); xs.append(x0+t*(x1-x0))
        xs.sort()
        for j in range(0,len(xs)-1,2):
            mm[row,int(np.ceil(xs[j])):int(np.floor(xs[j+1]))+1]=True
    return mm
def run_at(maskrow, cx):
    xs=np.nonzero(maskrow)[0]
    if len(xs)==0: return None
    cand=xs[np.argmin(np.abs(xs-cx))]
    if abs(cand-cx)>25: return None
    x0=x1=int(cand)
    while x0-1>=0 and maskrow[x0-1]: x0-=1
    while x1+1<W and maskrow[x1+1]: x1+=1
    return (x0,x1)

GRIPS={"L":dict(y0=0.150,y1=0.440,seed_y=0.30,seed_cx=195),
       "R":dict(y0=1.060,y1=1.330,seed_y=1.20,seed_cx=490)}
for nm,G in GRIPS.items():
    mask=polymask(C[nm])
    r_lo=int(G["y0"]*1000); r_hi=int(G["y1"]*1000)
    seed_r=int(G["seed_y"]*1000)
    run=run_at(mask[seed_r],G["seed_cx"])
    w_ref=run[1]-run[0]
    env={seed_r:((run[0]+run[1])/2,(run[1]-run[0])/2)}
    for direc in (-1,1):
        prev_c=env[seed_r][0]; prev_w=w_ref
        r=seed_r+direc
        while r_lo<=r<=r_hi:
            rn=run_at(mask[r],prev_c)
            if rn:
                c=(rn[0]+rn[1])/2; w=rn[1]-rn[0]
                if abs(c-prev_c)<=4 and 0.6*prev_w<=w<=1.35*prev_w:
                    env[r]=(c,w/2); prev_c=c; prev_w=0.8*prev_w+0.2*w
                else:
                    env[r]=(prev_c,prev_w/2)
            else:
                env[r]=(prev_c,prev_w/2)
            r+=direc
    ob=bpy.data.objects[f"Kamish_{nm}"]; me=ob.data
    n=len(me.vertices)
    co=np.empty(n*3,np.float32); me.vertices.foreach_get("co",co); co=co.reshape(n,3)
    yv=co[:,1]; xv=co[:,0]
    rowv=np.clip((yv*1000.0).astype(int),0,H-1)
    pxv=np.clip((xv*1000+360).astype(int),0,W-1)
    zone=(yv>=G["y0"])&(yv<=G["y1"])
    cxv=np.zeros(n,np.float32); hwv=np.zeros(n,np.float32)
    for i in np.nonzero(zone)[0]:
        c,hw=env.get(int(rowv[i]),(None,None))
        if c is None: zone[i]=False; continue
        cxv[i]=(c-360.0)/1000.0; hwv[i]=hw/1000.0
    off=xv-cxv
    beyond=zone&(np.abs(off)>(hwv+0.003))
    chitin=VAL[rowv,pxv]<0.28          # dark demon material -> KEEP
    out=beyond&(~chitin)
    print(nm,f"beyond {int(beyond.sum())} | spared chitin {int((beyond&chitin).sum())} | collapsing {int(out.sum())}")
    if out.sum()/max(1,zone.sum())>0.45:
        print(nm,"ABORT"); continue
    co[:,0]=np.where(out, cxv+np.sign(off)*hwv*0.995, xv)
    co[:,2]=np.where(out, np.sign(co[:,2])*0.0012, co[:,2])
    me.vertices.foreach_set("co",co.ravel()); me.update()
    bm=bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    sel=set()
    for i in np.nonzero(out)[0]:
        v=bm.verts[int(i)]; sel.add(v)
        for e in v.link_edges: sel.add(e.other_vert(v))
    sel=list(sel)
    for _ in range(3):
        bmesh.ops.smooth_vert(bm, verts=sel, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(me); bm.free(); me.update()
bpy.ops.wm.save_mainfile()
print("GRIP_CLEAN3_OK")
