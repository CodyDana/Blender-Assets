"""Median C4 + mirror width profile of the reconciled juji contour (method B edge, validated by the reconciler).
Run: blender -b --factory-startup --python s1_juji_profile.py
Writes synthesis/juji_profile.json and juji_profile.npy (u/R, h/R columns)."""
import numpy as np, json
P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
cont = np.load(P + "juji/contour/contour_refined.npy").astype(float)   # (N,2) x,y image px
C = np.array([694.10, 651.11])
arms = {'right': 1.44, 'top': 91.67, 'left': 181.93, 'bottom': 271.77}
Rt = {'right': 660.3, 'top': 663.0, 'left': 664.5, 'bottom': 662.0}
print("contour pts", cont.shape)
grid = np.linspace(0.0, 1.0, 1001)          # u / R
prof = {}
for name, th in arms.items():
    t = np.radians(th)
    d = np.array([np.cos(t), -np.sin(t)]); n = np.array([-d[1], d[0]])
    q = cont - C
    u = q @ d; v = q @ n
    R = Rt[name]
    for side in (+1, -1):
        sel = (u > 0) & (side * v > 0) & (np.abs(v) <= u * 1.02)
        uu = u[sel] / R; hh = np.abs(v[sel]) / R
        o = np.argsort(uu); uu = uu[o]; hh = hh[o]
        # bin to grid by max |v| within +-0.0025 R (outer envelope of the side)
        h = np.full(grid.shape, np.nan)
        for i, g in enumerate(grid):
            m = np.abs(uu - g) < 0.0025
            if m.any(): h[i] = np.median(hh[m])
        prof[(name, side)] = h
keys = list(prof)
M = np.array([prof[k] for k in keys])
med_all = np.nanmedian(M, 0)
M6 = np.array([prof[k] for k in keys if k[0] != 'top'])
med6 = np.nanmedian(M6, 0)
spread = np.nanstd(M, 0)
# report stations in the reconciled convention: full width / span, span = 2R
st = [0.12, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.53, 0.55, 0.6, 0.65, 0.67, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 1.0]
rows = []
for s in st:
    i = int(round(s * 1000))
    rows.append(dict(uR=s, w_span_all8=float(med_all[i]), w_span_6=float(med6[i]),
                     sd8=float(spread[i]), n=int(np.isfinite(M[:, i]).sum())))
    print("u/R %.2f  width/span all8 %.4f  excl-top %.4f  sd %.4f  n %d" % (s, med_all[i], med6[i], spread[i], np.isfinite(M[:, i]).sum()))
# note: width/span = 2h / 2R = h/R
np.save(P + "synthesis/juji_profile_raw.npy", np.stack([grid, med_all, med6], 1))
json.dump(dict(stations=rows, keys=[f"{a}{'+' if b > 0 else '-'}" for a, b in keys]),
          open(P + "synthesis/juji_profile_raw.json", "w"), indent=1)
print("done")
