"""Stage 2: rivet highlight centroid, silhouette mask, polar unwrap about the rivet (debug images + npy)."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
res = {}
guess = {1: (391, 600), 2: (398, 546)}
for i in (1, 2):
    a = load(i); H, W = a.shape[:2]
    lum = a @ LUMW.astype(np.float32)
    gx, gy = guess[i]
    win = lum[gy-14:gy+15, gx-14:gx+15]
    # rivet = metal: bright pixels inside a dark neighbourhood
    ys, xs = np.nonzero(win > 0.45)
    wts = win[ys, xs]
    cx = gx-14 + (xs*wts).sum()/wts.sum(); cy = gy-14 + (ys*wts).sum()/wts.sum()
    # bright-blob extent
    ext = dict(x=[int(xs.min()+gx-14), int(xs.max()+gx-14)], y=[int(ys.min()+gy-14), int(ys.max()+gy-14)], n=int(len(xs)))
    bg = float(np.median(lum[:30, :30]))
    # silhouette: darker than bg by a margin
    sil = lum < bg - 0.12
    np.save(os.path.join(OUT, f"fm_sil{i}.npy"), sil)
    res[i] = dict(rivet_bright_centroid=[round(cx, 2), round(cy, 2)], bright_extent=ext, bg_lum=bg,
                  sil_bbox=dict(x=[int(np.nonzero(sil.any(0))[0].min()), int(np.nonzero(sil.any(0))[0].max())],
                                y=[int(np.nonzero(sil.any(1))[0].min()), int(np.nonzero(sil.any(1))[0].max())]))
    # polar unwrap: theta from -20 to 200 deg (math convention, y up), 0.1 deg/px; r 0..420 px
    th = np.radians(np.arange(-20, 200, 0.1)); r = np.arange(0, 420, 1.0)
    T, R = np.meshgrid(th, r)
    X = cx + R*np.cos(T); Y = cy - R*np.sin(T)
    Xi = np.clip(X, 0, W-1.001); Yi = np.clip(Y, 0, H-1.001)
    x0 = np.floor(Xi).astype(int); y0 = np.floor(Yi).astype(int); fx = Xi-x0; fy = Yi-y0
    P = (a[y0, x0]*((1-fx)*(1-fy))[..., None] + a[y0, x0+1]*(fx*(1-fy))[..., None] +
         a[y0+1, x0]*((1-fx)*fy)[..., None] + a[y0+1, x0+1]*(fx*fy)[..., None])
    np.save(os.path.join(OUT, f"fm_polar{i}.npy"), P.astype(np.float32))
    save_png(np.clip(P[::-1]*3, 0, 1), f"dbg_polar{i}_th-20to200_x10_r0to420_gain3")
json.dump(res, open(os.path.join(OUT, "fm_s02_rivet.json"), "w"), indent=1)
print("FMRES", json.dumps(res))
