"""Stage 21: fan2 tassel. Connected dark region grown from a seed on the knot (below the fan's lower-left edge, outside the lobe):
axis, length, width profile along the axis (cord / knot / skirt), and its colour."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
a = load(2); L = a @ LUMW.astype(np.float32); H, W = L.shape
yy, xx = np.mgrid[0:H, 0:W]
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json"))); cx, cy = S2["2"]["rivet_bright_centroid"]
edge_y = 508 + (xx - 58)*(547-508)/(398-58) + 10
cand = (yy > edge_y) & (np.hypot(xx-cx, yy-cy) > 38.5) & (xx < 380) & (yy < 700) & (L < 0.9647*0.75)
reg = np.zeros_like(cand); reg[583, 334] = True
assert cand[583, 334]
for _ in range(400):
    g = reg.copy()
    g[1:] |= reg[:-1]; g[:-1] |= reg[1:]; g[:, 1:] |= reg[:, :-1]; g[:, :-1] |= reg[:, 1:]
    g &= cand
    if g.sum() == reg.sum(): break
    reg = g
ys, xs = np.nonzero(reg)
pts = np.c_[xs, ys].astype(float); c0 = pts.mean(0); U, S, Vt = np.linalg.svd(pts-c0); d = Vt[0]
if d[0] > 0: d = -d   # direction pivot -> tassel tip points left
n = np.array([-d[1], d[0]])
s = (pts-c0) @ d; t = (pts-c0) @ n
smin, smax = s.min(), s.max()
near = c0 + smin*d; far = c0 + smax*d      # near = end closest to the pivot
prof = []
for k in np.arange(np.floor(smin), np.ceil(smax)+1, 2.0):
    m = (s >= k) & (s < k+2)
    prof.append((float(k - smin), float(t[m].max()-t[m].min()+1) if m.sum() else 0.0))
ang = float(np.degrees(np.arctan2(-d[1], d[0])))
lin = srgb2lin(a[reg]); lum = lin @ LUMW
res = dict(n_px=int(reg.sum()), axis_dir_deg_yup=round(ang, 2), near_end_px=[round(float(v), 1) for v in near], far_tip_px=[round(float(v), 1) for v in far],
           length_px=round(float(smax-smin), 1), near_end_to_rivet_px=round(float(np.hypot(*(near-[cx, cy]))), 1),
           far_tip_to_rivet_px=round(float(np.hypot(*(far-[cx, cy]))), 1),
           width_profile_from_near_end=[[round(p[0]), round(p[1], 1)] for p in prof],
           mean_lin_rgb=[round(float(v), 4) for v in lin.mean(0)], median_lin_rgb=[round(float(v), 4) for v in np.median(lin, 0)],
           lum_lin_p10_p50_p90=[round(float(np.percentile(lum, q)), 4) for q in (10, 50, 90)])
json.dump(res, open(os.path.join(OUT, "fm_s21_tassel.json"), "w"), indent=0)
print("FMRES", json.dumps(res))
dbg = a.copy(); dbg[reg] = dbg[reg]*0.3 + np.array([0.9, 0.2, 0.2])*0.7
save_png(dbg[520:700, 170:420], "dbg_tassel_mask_x3", 3)
# interior colour (mask eroded 2 px so background-blended edge pixels are excluded)
er = reg.copy()
for _ in range(2):
    g = er.copy(); g[1:] &= er[:-1]; g[:-1] &= er[1:]; g[:, 1:] &= er[:, :-1]; g[:, :-1] &= er[:, 1:]; er = g
li = srgb2lin(a[er]); lu = li @ LUMW
col = dict(n=int(er.sum()), mean_lin=[round(float(v), 5) for v in li.mean(0)], median_lin=[round(float(v), 5) for v in np.median(li, 0)],
           lum_mean=round(float(lu.mean()), 5), lum_p10_p50_p90=[round(float(np.percentile(lu, q)), 5) for q in (10, 50, 90)],
           chroma=[round(float(v), 4) for v in li.mean(0)/li.mean(0).sum()])
res['interior_colour'] = col
json.dump(res, open(os.path.join(OUT, "fm_s21_tassel.json"), "w"), indent=0)
print("FMCOL", json.dumps(col))
