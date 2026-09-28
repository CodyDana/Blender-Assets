"""Stage 13: lobe below the rivet (stacked rib butts): silhouette radius about the rivet for theta 180..360 (image, y up)."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json")))
res = {}
for i in (1, 2):
    cx, cy = S2[str(i)]["rivet_bright_centroid"]
    sil = np.load(os.path.join(OUT, f"fm_sil{i}.npy")); H, W = sil.shape
    tab = {}
    for t in range(170, 371, 5):
        rr = np.arange(9, 120, 0.25)
        x = np.clip(np.round(cx + rr*np.cos(np.radians(t))).astype(int), 0, W-1)
        y = np.clip(np.round(cy - rr*np.sin(np.radians(t))).astype(int), 0, H-1)
        m = sil[y, x]
        # first False after start (contiguous dark run from the rivet)
        k = np.argmin(m) if not m.all() else len(m)-1
        tab[t % 360 if t >= 360 else t] = float(rr[k])
    # bbox of the dark region connected to the rivet below the rivet line (rows > cy)
    ys, xs = np.nonzero(sil[int(cy):int(cy)+80, int(cx)-80:int(cx)+80])
    res[i] = dict(r_by_theta=tab)
    # horizontal width of the lobe at rows below the rivet
    wid = {}
    for dy in (0, 5, 10, 15, 20, 25, 30, 35, 40):
        row = sil[int(round(cy))+dy, :]
        # contiguous run around cx
        a = int(round(cx)); b = a
        if not row[a]: wid[dy] = 0; continue
        while row[a-1]: a -= 1
        while row[b+1]: b += 1
        wid[dy] = [a - cx, b - cx]
    res[i]['row_extent_rel_rivet'] = {k: (v if v == 0 else [round(v[0], 1), round(v[1], 1)]) for k, v in wid.items()}
json.dump(res, open(os.path.join(OUT, "fm_s13_lobe.json"), "w"), indent=0)
print("FMRES", json.dumps(res))
