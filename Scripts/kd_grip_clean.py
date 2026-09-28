import bpy, bmesh, numpy as np, json

W,H=720,1499
with open(r"C:\Users\Cody\Desktop\Blender_Projects\kd_contours.json") as f:
    C=json.load(f)
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

# grip interior y-ranges (junctions at top/bottom left attached) + center guesses
GRIPS={"L":dict(y0=0.150,y1=0.440,cx_guess=200),
       "R":dict(y0=1.060,y1=1.330,cx_guess=487)}
for nm,G in GRIPS.items():
    mask=polymask(C[nm])
    r0=int(H-1-G["y1"]*1000); r1=int(H-1-G["y0"]*1000)
    rows=range(max(0,r0),min(H,r1))
    runs={}
    for r in rows:
        xs=np.nonzero(mask[r])[0]
        if len(xs)==0: continue
        # run containing the center guess
        cg=G["cx_guess"]
        cand=xs[np.argmin(np.abs(xs-cg))]
        x0=x1=cand
        while x0-1 in xs: x0-=1
        while x1+1 in xs: x1+=1
        runs[r]=(x0,x1)
    ws=np.array([x1-x0 for (x0,x1) in runs.values()])
    env_w=float(np.median(np.sort(ws)[:max(3,len(ws)//2)]))   # median of narrow half = true grip width
    # centerline fit from spur-free rows
    good=[(r,(x0+x1)/2) for r,(x0,x1) in runs.items() if (x1-x0)<=env_w*1.15]
    rr=np.array([g[0] for g in good]); cc=np.array([g[1] for g in good])
    A=np.vstack([rr,np.ones_like(rr)]).T
    slope,icept=np.linalg.lstsq(A.astype(np.float64),cc.astype(np.float64),rcond=None)[0]
    print(nm,"grip width px:",round(env_w,1),"| centerline slope:",round(slope,4))
    ob=bpy.data.objects[f"Kamish_{nm}"]; me=ob.data
    n=len(me.vertices)
    co=np.empty(n*3,np.float32); me.vertices.foreach_get("co",co); co=co.reshape(n,3)
    yv=co[:,1]; xv=co[:,0]
    rowv=H-1-yv*1000.0
    cxv=(slope*rowv+icept - 360.0)/1000.0
    hw=(env_w/2.0)/1000.0
    zone=(yv>=G["y0"])&(yv<=G["y1"])
    off=xv-cxv
    out=zone&(np.abs(off)>hw)
    xv2=np.where(out, cxv+np.sign(off)*hw*0.995, xv)
    co[:,0]=xv2
    co[:,2]=np.where(out, np.sign(co[:,2])*0.0012, co[:,2])
    me.vertices.foreach_set("co",co.ravel()); me.update()
    # blend the collapsed seam smooth
    bm=bmesh.new(); bm.from_mesh(me)
    idx=np.nonzero(out)[0]
    outset=set(int(i) for i in idx)
    bm.verts.ensure_lookup_table()
    sel=set()
    for i in outset:
        v=bm.verts[i]; sel.add(v)
        for e in v.link_edges: sel.add(e.other_vert(v))
    sel=list(sel)
    for _ in range(3):
        bmesh.ops.smooth_vert(bm, verts=sel, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(me); bm.free(); me.update()
    print(nm,"side protrusions collapsed:",int(out.sum()),"verts")
bpy.ops.wm.save_mainfile()
print("GRIP_CLEAN_OK")
