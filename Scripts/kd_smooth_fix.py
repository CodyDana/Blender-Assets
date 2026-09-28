import bpy, bmesh, numpy as np, json

# ---------- A) material: damp chitin mirror (rougher, less coat) ----------
for mn in ("Kamish_Art_L","Kamish_Art_R"):
    m=bpy.data.materials[mn]; nt=m.node_tree
    for n in nt.nodes:
        if n.bl_idname=='ShaderNodeMath' and n.operation=='MULTIPLY' and abs(n.inputs[1].default_value-0.28)<0.001:
            # distinguish: roughness-cut feeds a SUBTRACT; coat feeds an ADD
            outs=[l.to_node.operation if l.to_node.bl_idname=='ShaderNodeMath' else '' for l in nt.links if l.from_node==n]
            if 'SUBTRACT' in outs: n.inputs[1].default_value=0.15
            elif 'ADD' in outs:    n.inputs[1].default_value=0.14
    # widen/retune blade zone ramps (sharp, close to the guard)
    sep=[x for x in nt.nodes if x.bl_idname=='ShaderNodeSeparateXYZ'][-1]
    for l in nt.links:
        if l.from_node==sep and l.from_socket.name=='Y' and l.to_node.bl_idname=='ShaderNodeMapRange':
            zf=l.to_node
            if mn.endswith("_L"):
                zf.inputs['From Min'].default_value=0.872; zf.inputs['From Max'].default_value=0.882
            else:
                zf.inputs['From Min'].default_value=0.760; zf.inputs['From Max'].default_value=0.725
    print(mn,"material damped + zone tightened")

# ---------- B) geometry: re-flatten with extended sharp ramps ----------
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
def ero1(mm):
    out=mm.copy()
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dx or dy: out &= np.roll(np.roll(mm,dy,0),dx,1)
    return out
def blur(f,k=1):
    out=f.astype(np.float32)
    for _ in range(k):
        acc=np.zeros_like(out)
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                acc+=np.roll(np.roll(out,dy,0),dx,1)
        out=acc/9.0
    return out
PARAMS={"L":dict(zone=(0.872,0.882), taper=lambda y: np.clip((y-0.878)/(1.408-0.878),0,1)),
        "R":dict(zone=(0.760,0.725), taper=lambda y: np.clip((0.738-y)/(0.738-0.145),0,1))}
for nm in ("L","R"):
    mask=polymask(C[nm])
    d=np.zeros((H,W),np.float32); cur=mask.copy()
    for i in range(1,61):
        cur=ero1(cur)
        if not cur.any(): break
        d[cur]=i
    d=blur(d,5)
    ob=bpy.data.objects[f"Kamish_{nm}"]; me=ob.data
    n=len(me.vertices)
    co=np.empty(n*3,np.float32); me.vertices.foreach_get("co",co); co=co.reshape(n,3)
    px=np.clip((co[:,0]*1000+360).astype(int),0,W-1)
    rw=np.clip((co[:,1]*1000).astype(int),0,H-1)
    dpx=d[rw,px]/1000.0
    yv=co[:,1]
    f=PARAMS[nm]["taper"](yv)
    TMAXB=0.024-(0.024-0.008)*f
    t=np.clip(dpx*(TMAXB/0.014), 0.0022, TMAXB)
    ideal=np.where(co[:,2]>=0,1.0,-1.0)*t/2.0
    y0,y1=PARAMS[nm]["zone"]
    zfv=np.clip((yv-y0)/(y1-y0),0,1)
    co[:,2]=co[:,2]*(1-zfv)+ideal*zfv
    me.vertices.foreach_set("co",co.ravel()); me.update()
    print(nm,"re-flattened to the guard")

# ---------- C) smooth the chitin guard ripple (L demon mass region) ----------
ob=bpy.data.objects["Kamish_L"]; me=ob.data
bm=bmesh.new(); bm.from_mesh(me)
sel=[v for v in bm.verts if 0.48<=v.co.y<=0.94]
for _ in range(4):
    bmesh.ops.smooth_vert(bm, verts=sel, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
bm.to_mesh(me); bm.free(); me.update()
print("L guard chitin smoothed,",len(sel),"verts")
bpy.ops.wm.save_mainfile()
print("SMOOTH_FIX_OK")
