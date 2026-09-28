import numpy as np
def warp(src, s, tx, ty, out_shape, order=1):
    """out(x,y) = src((x-tx)/s, (y-ty)/s)  (src pixel coords -> ref coords: x_ref = s*x_src+tx)"""
    H,W=out_shape; yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    sx=(xx+0.5-tx)/s-0.5; sy=(yy+0.5-ty)/s-0.5
    h,w=src.shape[:2]
    if order==0:
        ix=np.clip(np.round(sx).astype(int),0,w-1); iy=np.clip(np.round(sy).astype(int),0,h-1)
        out=src[iy,ix]; inside=(sx>=-0.5)&(sx<w-0.5)&(sy>=-0.5)&(sy<h-0.5)
        return np.where(inside if src.ndim==2 else inside[...,None], out, 0)
    x0=np.floor(sx).astype(int); y0=np.floor(sy).astype(int); fx=sx-x0; fy=sy-y0
    def g(yi,xi):
        v=src[np.clip(yi,0,h-1),np.clip(xi,0,w-1)]; ok=(xi>=0)&(xi<w)&(yi>=0)&(yi<h)
        return np.where(ok if src.ndim==2 else ok[...,None], v, 0)
    if src.ndim==3: fx=fx[...,None]; fy=fy[...,None]
    return (g(y0,x0)*(1-fx)*(1-fy)+g(y0,x0+1)*fx*(1-fy)+g(y0+1,x0)*(1-fx)*fy+g(y0+1,x0+1)*fx*fy)
def iou(a,b): return (a&b).sum()/max(1,(a|b).sum())
def best_align(src_mask, ref_mask):
    ys,xs=np.nonzero(ref_mask); rb=(xs.min(),xs.max(),ys.min(),ys.max())
    ys,xs=np.nonzero(src_mask); sb=(xs.min(),xs.max(),ys.min(),ys.max())
    s0=(rb[3]-rb[2])/(sb[3]-sb[2])
    best=(-1,None)
    srcf=src_mask.astype(np.float32)
    for ds in np.linspace(0.95,1.05,5):
        s=s0*ds
        cx=(rb[0]+rb[1])/2-s*(sb[0]+sb[1])/2; cy=(rb[2]+rb[3])/2-s*(sb[2]+sb[3])/2
        for dx in range(-6,7,3):
            for dy in range(-6,7,3):
                m=warp(srcf,s,cx+dx,cy+dy,ref_mask.shape,0)>0.5; v=iou(m,ref_mask)
                if v>best[0]: best=(v,(s,cx+dx,cy+dy))
    v,(s,tx,ty)=best
    for dx in np.arange(-1,1.5,1):
        for dy in np.arange(-1,1.5,1):
            for ds in (0.99,1,1.01):
                m=warp(srcf,s*ds,tx+dx,ty+dy,ref_mask.shape,0)>0.5; vv=iou(m,ref_mask)
                if vv>best[0]: best=(vv,(s*ds,tx+dx,ty+dy))
    return best
