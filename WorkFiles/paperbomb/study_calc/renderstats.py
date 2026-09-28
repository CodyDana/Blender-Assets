import bpy, numpy as np, os, json
R=r"C:/Users/Cody/Desktop/Blender_Projects/Renders/Shuriken"
out={}
for fn in ("four_point_persp.png","spike_persp.png","kunai_plain_3q.png","hooked_cross_top.png"):
    img=bpy.data.images.load(os.path.join(R,fn)); img.colorspace_settings.name="Non-Color"
    w,h=img.size; buf=np.empty(w*h*4,dtype=np.float32); img.pixels.foreach_get(buf)
    a=buf.reshape(h,w,4)[::-1,:,:3].astype(np.float64); bpy.data.images.remove(img)
    L=0.2126*a[:,:,0]+0.7152*a[:,:,1]+0.0722*a[:,:,2]
    # background estimate: median of each row's outer 6% columns, broadcast
    k=int(0.06*w)
    bg=np.median(np.concatenate([L[:,:k],L[:,-k:]],axis=1),axis=1)[:,None]
    diff=np.abs(L-bg)
    obj=diff>0.035
    # drop the shadow: shadow is darker than bg AND low saturation; keep only pixels far from bg
    sel=L[obj]
    out[fn]={"size":[w,h],"bg_p50":round(float(np.median(bg)),4),
             "bg_top":round(float(np.median(bg[:20])),4),"bg_bottom":round(float(np.median(bg[-20:])),4),
             "obj_frac":round(float(obj.mean()),4),
             "obj_p05":round(float(np.percentile(sel,5)),4),
             "obj_p50":round(float(np.percentile(sel,50)),4),
             "obj_mean":round(float(sel.mean()),4),
             "obj_p95":round(float(np.percentile(sel,95)),4),
             "frame_mean":round(float(L.mean()),4)}
    print(fn,out[fn])
json.dump(out,open("render_band.json","w"),indent=1)
