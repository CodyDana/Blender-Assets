"""Stage 11: silhouette end edges (straight edges at both ends of the open fan): polar edge angle vs r, image-space line fit, opening angle."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json")))
res = {}
for i in (1, 2):
    cx, cy = S2[str(i)]["rivet_bright_centroid"]
    sil = np.load(os.path.join(OUT, f"fm_sil{i}.npy")); H, W = sil.shape
    # dense polar of the mask at 0.05 deg
    th = np.arange(-20, 200, 0.05); rows = {}
    for r in range(30, 400, 2):
        x = np.clip(np.round(cx + r*np.cos(np.radians(th))).astype(int), 0, W-1)
        y = np.clip(np.round(cy - r*np.sin(np.radians(th))).astype(int), 0, H-1)
        m = sil[y, x]
        # outermost dark samples scanning in from both ends (holes from design/piercing ignored)
        nz = np.nonzero(m)[0]
        if len(nz) < 10: continue
        a, b = nz.min(), nz.max()
        rows[r] = (float(th[a]), float(th[b]))
    R = np.array(sorted(rows)); lo = np.array([rows[r][0] for r in R]); hi = np.array([rows[r][1] for r in R])
    tab = {int(r): [round(rows[r][0], 2), round(rows[r][1], 2)] for r in R if r % 20 == 0}
    # image-space points of edges
    def line_fit(rsel, ang):
        x = cx + rsel*np.cos(np.radians(ang)); y = cy - rsel*np.sin(np.radians(ang))
        p = np.polyfit(x, y, 1)
        # distance of rivet to the line
        a_, b_ = p; d = (a_*cx - cy + b_)/np.sqrt(a_*a_+1)
        dirdeg = np.degrees(np.arctan2(-(a_), 1))  # direction of line (image, y up) for increasing x
        res_ = y - np.polyval(p, x)
        return dict(slope=round(float(a_), 5), icpt=round(float(b_), 2), dir_deg_yup=round(float(dirdeg), 3),
                    rivet_signed_dist_px=round(float(d), 2), rms=round(float(np.sqrt((res_**2).mean())), 3))
    rmax = {1: 380, 2: 320}[i]
    s = (R >= 150) & (R <= rmax)
    right = line_fit(R[s], lo[s]); sl = s & (hi < 190) & (R >= (220 if i == 2 else 150)); left = line_fit(R[sl], hi[sl])
    res[i] = dict(edge_theta_every20=tab, right_end_line_r150=right, left_end_line_r150=left)
json.dump(res, open(os.path.join(OUT, "fm_s11_ends.json"), "w"), indent=1)
print("FMRES", json.dumps(res))
