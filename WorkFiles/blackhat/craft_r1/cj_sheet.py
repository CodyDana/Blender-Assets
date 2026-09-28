import bpy, numpy as np, json
D="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/craft_r1/r/"
def load(n):
    im=bpy.data.images.load(D+n+".png"); a=np.array(im.pixels[:],dtype=np.float32).reshape(im.size[1],im.size[0],im.channels)[::-1]; bpy.data.images.remove(im); return a[...,:3]
def save(a,n):
    h,w=a.shape[:2]; im=bpy.data.images.new(n,w,h); px=np.ones((h,w,4),np.float32); px[...,:3]=a; im.pixels[:]=px[::-1].ravel(); im.filepath_raw=D+n+".png"; im.file_format='PNG'; im.save()
hero=[load(f"turn_hero_{i:02d}") for i in range(12)]
th=[load(f"turn_thumb_{i:02d}") for i in range(12)]
# thumbnail grid 4x3
g=np.concatenate([np.concatenate(th[r*4:(r+1)*4],1) for r in range(3)],0); save(g,"sheet_thumb_turn")
# find hat bbox in hero 0
m=(np.abs(hero[0]-hero[0][2,2]).sum(-1)>0.03); ys,xs=np.where(m); print("bbox",xs.min(),xs.max(),ys.min(),ys.max())
x0,x1,y0,y1=xs.min(),xs.max(),ys.min(),ys.max()
# crops: left grazing side, front centre
L=[h[y0+ (y1-y0)//3: y0+(y1-y0)//3+140, x0+10:x0+230] for h in hero[:6]]
C=[h[(y0+y1)//2-70:(y0+y1)//2+70, (x0+x1)//2-110:(x0+x1)//2+110] for h in hero[:6]]
up=lambda a: a.repeat(2,0).repeat(2,1)
sheet=np.concatenate([np.concatenate([up(a) for a in L],1),np.concatenate([up(a) for a in C],1)],0); save(sheet,"sheet_hero_crops")
# flicker metric: per-frame high-pass energy in crops
def hp(a):
    l=a.mean(-1); b=(l[:-2,1:-1]+l[2:,1:-1]+l[1:-1,:-2]+l[1:-1,2:])/4; return float((l[1:-1,1:-1]-b).std())
out={"left_hp":[hp(a) for a in L],"centre_hp":[hp(a) for a in C]}
# whole hat mean luminance per frame (thumb) to detect pumping
out["thumb_mean"]=[float(t[(np.abs(t-t[2,2]).sum(-1)>0.03)].mean()) for t in th]
out["hero_mean"]=[float(h[(np.abs(h-h[2,2]).sum(-1)>0.03)].mean()) for h in hero]
print("CJS"+json.dumps(out))
# LOD sheet
rows=[]
for s in ("648","227"):
    ims=[load(f"lod{l}_{s}") for l in range(3)]
    m=(np.abs(ims[0]-ims[0][2,2]).sum(-1)>0.03)|(np.abs(ims[2]-ims[2][2,2]).sum(-1)>0.03); ys,xs=np.where(m)
    cr=[a[ys.min()-5:ys.max()+5, xs.min()-5:xs.max()+5] for a in ims]
    d01=np.clip(np.abs(cr[0]-cr[1])*4,0,1); d12=np.clip(np.abs(cr[1]-cr[2])*4,0,1)
    row=np.concatenate(cr+[d01,d12],1)
    if s=="227": row=row.repeat(2,0).repeat(2,1)
    rows.append(row)
W=max(r.shape[1] for r in rows)
rows=[np.pad(r,((0,4),(0,W-r.shape[1]),(0,0)),constant_values=1) for r in rows]
save(np.concatenate(rows,0),"sheet_lods")
