import bpy, numpy as np, json

img=bpy.data.images["Kamish_Daggers.webp"]; W,H=img.size
a=np.empty(W*H*4,dtype=np.float32); img.pixels.foreach_get(a)
a=a.reshape(H,W,4)
rgb=a[...,:3].copy()
val=rgb.max(axis=2)

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
def ero(m,k):
    out=m.copy()
    for dy in range(-k,k+1):
        for dx in range(-k,k+1):
            if dx or dy: out &= np.roll(np.roll(m,dy,0),dx,1)
    return out
def dil(m,k):
    out=m.copy()
    for dy in range(-k,k+1):
        for dx in range(-k,k+1):
            if dx or dy: out |= np.roll(np.roll(m,dy,0),dx,1)
    return out
mask=polymask(C["L"])|polymask(C["R"])
yy,xx=np.mgrid[0:H,0:W]; ytop=H-1-yy
def box(x0,x1,y0,y1): return (xx>=x0)&(xx<=x1)&(ytop>=y0)&(ytop<=y1)

# 1) outer silhouette contour ring (the sketch outline) - everywhere
ring=mask&~ero(mask,6)
line_ring=ring&(val<0.50)
# 2) internal linework in the BLADE zones only (thin dark structures)
blades=(box(120,370,70,650)|box(350,708,930,1380)|box(395,610,25,260))&mask
dark=(val<0.42)&blades
thin=dark&~ero(dark,3)
lines=line_ring|thin
print("outline px to remove:",int(lines.sum()))

# inpaint: pull colors inward from valid dagger pixels
valid=mask&~lines
work=rgb.copy()
for it in range(14):
    if not lines.any(): break
    acc=np.zeros_like(work); cnt=np.zeros((H,W),np.float32)
    for dy in (-1,0,1):
        for dx in (-1,0,1):
            if dx==0 and dy==0: continue
            sv=np.roll(np.roll(valid,dy,0),dx,1)
            sc=np.roll(np.roll(work,dy,0),dx,1)
            m=lines&sv
            acc[m]+=sc[m]; cnt[m]+=1
    fill=lines&(cnt>0)
    work[fill]=acc[fill]/cnt[fill][:,None]
    valid|=fill; lines&=~fill
out=a.copy(); out[...,:3]=work
new=bpy.data.images.get("Kamish_Clean")
if new: bpy.data.images.remove(new)
new=bpy.data.images.new("Kamish_Clean",W,H,alpha=True,float_buffer=True)
new.colorspace_settings.name='Linear Rec.709'
new.pixels.foreach_set(out.ravel())
new.pack()

# swap texture in both dagger materials
for mn in ("Kamish_Art_L","Kamish_Art_R"):
    mt=bpy.data.materials[mn]
    for n in mt.node_tree.nodes:
        if n.bl_idname=='ShaderNodeTexImage':
            n.image=new
bpy.ops.wm.save_mainfile()
print("OUTLINES_REMOVED")
