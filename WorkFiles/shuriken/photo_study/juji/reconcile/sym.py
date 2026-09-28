import numpy as np
P="C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/juji/"
A=np.load(P+"radial/mask_final.npy"); B=np.load(P+"contour/mask_refined.npy")
H,W=A.shape
yy,xx=np.mgrid[0:H,0:W]
def rot(M,cx,cy,deg):
    a=np.radians(deg); ca,sa=np.cos(a),np.sin(a)
    X=xx-cx; Y=yy-cy
    sx= ca*X - sa*Y + cx; sy= sa*X + ca*Y + cy
    ix=np.round(sx).astype(int); iy=np.round(sy).astype(int)
    ok=(ix>=0)&(ix<W)&(iy>=0)&(iy<H)
    out=np.zeros_like(M); out[ok]=M[iy[ok],ix[ok]]
    return out
def best(M,label):
    ys,xs=np.nonzero(M); c0=(xs.mean(),ys.mean())
    bestv=None
    for dx in np.arange(-6,6.01,0.5):
        for dy in np.arange(-6,6.01,0.5):
            cx,cy=c0[0]+dx,c0[1]+dy
            R=rot(M,cx,cy,90)
            iou=(M&R).sum()/((M|R).sum())
            if bestv is None or iou>bestv[0]: bestv=(iou,cx,cy)
    iou,cx,cy=bestv
    r180=rot(M,cx,cy,180); i180=(M&r180).sum()/(M|r180).sum()
    # exclude the clipped top region (rows<120) from the comparison for a fair test
    valid=np.ones_like(M); valid[:130]=False
    Rv=rot(M,cx,cy,90)
    mv=M&valid; rv=Rv&valid
    iou_v=(mv&rv).sum()/((mv|rv).sum())
    print(f"{label}: area={M.sum()} centre=({cx:.2f},{cy:.2f}) rot90 IoU={iou:.4f} rot180 IoU={i180:.4f} rot90 IoU(excl clipped top)={iou_v:.4f}")
    return cx,cy,iou
best(A,"A radial mask_final")
best(B,"B contour mask_refined")
