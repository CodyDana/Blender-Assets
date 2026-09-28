"""Stage 22: colour per part (design masked and dilated): leaf, bare ribs (holes excluded), right guard face, lobe (butt stack),
tassel (fan2), rivet. Stored sRGB -> linear; stats; chroma/hue. Also leaf light-face vs dark-face levels and design coverage."""
import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/fan/reference_metrology")
from fm_lib import *
import json, colorsys
S2 = json.load(open(os.path.join(OUT, "fm_s02_rivet.json"))); S11 = json.load(open(os.path.join(OUT, "fm_s11_ends.json")))
def dilate(m, k):
    for _ in range(k):
        g = m.copy(); g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]; m = g
    return m
def stats(lin):
    lum = lin @ LUMW
    mean = lin.mean(0); med = np.median(lin, 0)
    s = mean.sum(); chroma = mean/s
    h, l_, sat = colorsys.rgb_to_hls(*(lin2srgb(mean)))
    return dict(n=int(len(lin)), mean_lin=[round(float(v), 5) for v in mean], median_lin=[round(float(v), 5) for v in med],
                lum_mean=round(float(lum.mean()), 5), lum_p10_p50_p90=[round(float(np.percentile(lum, q)), 5) for q in (10, 50, 90)],
                mean_srgb=[round(float(v), 4) for v in lin2srgb(mean)], chroma_rgb=[round(float(v), 4) for v in chroma],
                hue_deg=round(h*360, 1), hls_sat=round(sat, 3))
res = {}
params = {1: dict(L=396.0, rl=(186, 385), rr=(45, 175), th=(20, 157), bg=1.0), 2: dict(L=343.0, rl=(152, 322), rr=(45, 138), th=(16, 168), bg=0.9647)}
for i in (1, 2):
    p = params[i]; cx, cy = S2[str(i)]["rivet_bright_centroid"]
    a = load(i); H, W = a.shape[:2]; lin = srgb2lin(a); L = a @ LUMW
    mx = a.max(2); mn = a.min(2); sat = (mx-mn)/(mx+1e-4)
    design = (L > (0.30 if i == 2 else 0.45)) | ((sat > (0.30 if i == 2 else 0.45)) & (mx > (0.12 if i == 2 else 0.25)))
    design_d = dilate(design, 2)
    yy, xx = np.mgrid[0:H, 0:W]; r = np.hypot(xx-cx, yy-cy); t = np.degrees(np.arctan2(cy-yy, xx-cx))
    sector = (t > p['th'][0]) & (t < p['th'][1])
    leaf = sector & (r > p['rl'][0]) & (r < p['rl'][1])
    ribs = sector & (r > p['rr'][0]) & (r < p['rr'][1])
    out = {}
    out['design_coverage_leaf'] = round(float((design & leaf).sum()/leaf.sum()), 4)
    out['design_coverage_ribzone'] = round(float((design & ribs).sum()/ribs.sum()), 4)
    out['leaf'] = stats(lin[leaf & ~design_d])
    # leaf light vs dark faces: split by local median of luminance
    Lleaf = L[leaf & ~design_d]; thr = np.median(Lleaf)
    out['leaf_light_faces'] = stats(lin[leaf & ~design_d & (L > thr)]); out['leaf_dark_faces'] = stats(lin[leaf & ~design_d & (L <= thr)])
    holes = dilate(L > (0.30 if i == 2 else 0.45), 1)
    out['ribs_bare'] = stats(lin[ribs & ~holes & ~design_d])
    out['rib_zone_hole_fraction'] = round(float((ribs & (L > (0.30 if i == 2 else 0.35))).sum()/ribs.sum()), 4)
    # right guard face: band offset 2..9 px inward from the right end line, s in [180, 0.93L]
    ln = S11[str(i)]['right_end_line_r150']; m_, b_ = ln['slope'], ln['icpt']
    u = np.array([1.0, m_]); u /= np.linalg.norm(u); nrm = np.array([-u[1], u[0]]);
    if nrm[1] > 0: nrm = -nrm
    off = (xx - 0)*nrm[0] + (yy - b_)*nrm[1]   # signed distance from line y = m x + b along nrm
    guard = (off > 2) & (off < 9) & (r > 180) & (r < 0.93*p['L']) & (xx > cx) & ~design_d
    out['right_guard_face'] = stats(lin[guard])
    lobe = (r > 9) & (r < 30) & (t < -25) & (t > -155)
    out['lobe_butts'] = stats(lin[lobe])
    riv = (r < 7) & (L > 0.25)
    out['rivet_metal_bright'] = stats(lin[riv]) if riv.sum() > 3 else None
    out['background_lin'] = round(float(srgb2lin(p['bg'])), 4)
    res[i] = out
json.dump(res, open(os.path.join(OUT, "fm_s22_colour.json"), "w"), indent=1)
for i in (1, 2):
    print(f"FAN{i}", "design leaf", res[i]['design_coverage_leaf'], "ribzone", res[i]['design_coverage_ribzone'], "holes", res[i]['rib_zone_hole_fraction'])
    for k in ('leaf', 'leaf_light_faces', 'leaf_dark_faces', 'ribs_bare', 'right_guard_face', 'lobe_butts', 'rivet_metal_bright'):
        v = res[i][k]
        if v: print(f"  {k:18s} n={v['n']:6d} meanlin={v['mean_lin']} lum={v['lum_mean']} p10/50/90={v['lum_p10_p50_p90']} sRGB={v['mean_srgb']} hue={v['hue_deg']} sat={v['hls_sat']}")
