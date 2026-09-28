import bpy, numpy as np, json
OUT = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/verify_look/"
FID = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/fidelity/"
REF = r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
TEX = r"C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/Textures/"

def load(p):
    im = bpy.data.images.load(p, check_existing=False); im.colorspace_settings.name = 'Non-Color'
    w, h = im.size; c = im.channels
    a = np.empty(w*h*c, np.float32); im.pixels.foreach_get(a)
    a = a.reshape(h, w, c)[::-1].copy(); bpy.data.images.remove(im)
    return a
def lum(a): return (0.2126*a[..., 0]+0.7152*a[..., 1]+0.0722*a[..., 2])*255
def erode(m, n):
    m = m.copy()
    for _ in range(n):
        m[1:] &= m[:-1].copy(); m[:-1] &= m[1:].copy(); m[:, 1:] &= m[:, :-1].copy(); m[:, :-1] &= m[:, 1:].copy()
    return m
def box(L, r):
    k = 2*r+1; P = np.pad(L, r, mode='edge'); c = P.cumsum(0).cumsum(1); c = np.pad(c, ((1, 0), (1, 0)))
    H, W = L.shape
    return (c[k:k+H, k:k+W]-c[:H, k:k+W]-c[k:k+H, :W]+c[:H, :W])/(k*k)
def stats(v):
    return {'n': int(v.size), 'mean': round(float(v.mean()), 2), 'std': round(float(v.std()), 2),
            'p5': round(float(np.percentile(v, 5)), 1), 'p50': round(float(np.percentile(v, 50)), 1),
            'p95': round(float(np.percentile(v, 95)), 1), 'p99': round(float(np.percentile(v, 99)), 1)}
R = {}
ref = load(REF); L = lum(ref); H, W = L.shape
R['ref_size'] = [W, H]
# background
bg = np.concatenate([L[:20, :60].ravel(), L[:20, -60:].ravel()])
R['ref_bg_corners'] = stats(bg); R['ref_frac_255'] = round(float((L >= 254.5).mean()), 3)
# mask at different thresholds
for th in (235, 200, 150, 100):
    m = L < th; ys, xs = np.nonzero(m)
    R[f'ref_mask_lt{th}'] = {'bbox': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], 'area': int(m.sum())}
# pixels in eroded 235-mask that are bright (shadow / fray / see-through)
m235 = L < 235; e = erode(m235, 4); v = L[e]
R['ref_cloth_eroded4_lt235'] = stats(v)
R['ref_eroded4_frac_gt80'] = round(float((v > 80).mean()), 4)
# where are those bright pixels (rows)
bright = e & (L > 80); yb = np.nonzero(bright)[0]
R['ref_bright_rows_hist'] = np.histogram(yb, bins=[0, 100, 200, 300, 400, 500, 600, 640, 660, 674])[0].tolist()
# robust cloth stats: exclude bottom 30 rows and > 100
core = e.copy(); core[600:] = False
R['ref_cloth_core_y_lt600'] = stats(L[core])
# ours
ours = load(FID+"ours_lod0_front_refframe.png"); Lo = lum(ours)
om = np.load(FID+"ours_lod0_front_mask.npy") > 0.5
eo = erode(om, 4)
R['ours_cloth_eroded4'] = stats(Lo[eo])
coreo = eo.copy(); coreo[600:] = False
R['ours_cloth_core_y_lt600'] = stats(Lo[coreo])
# IoU at different ref thresholds
for th in (235, 150, 100):
    m = L < th
    R[f'iou_ours_vs_ref_lt{th}'] = round(float((m & om).sum()/(m | om).sum()), 4)
ys, xs = np.nonzero(om); R['ours_mask_bbox'] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
# bottom profile: lowest mask row per column, ref (<150) vs ours
def bottom(m):
    return np.array([np.nonzero(m[:, x])[0].max() if m[:, x].any() else -1 for x in range(W)])
bref = bottom(L < 150); bref235 = bottom(L < 235); bo = bottom(om)
R['hem_bottom_max'] = {'ref_lt150': int(bref.max()), 'ref_lt235': int(bref235.max()), 'ours': int(bo.max())}
R['hem_bottom_median_x60_360'] = {'ref_lt150': float(np.median(bref[60:360])), 'ref_lt235': float(np.median(bref235[60:360])), 'ours': float(np.median(bo[60:360]))}
# see-through holes inside ours' hull at the bottom: background pixels enclosed between left/right extents per row y 560-670
holes = 0; holes_ref = 0
for y in range(560, min(H, 674)):
    r = np.nonzero(om[y])[0]
    if r.size: holes += int((~om[y, r.min():r.max()+1]).sum())
    r2 = np.nonzero(L[y] < 150)[0]
    if r2.size: holes_ref += int((L[y, r2.min():r2.max()+1] >= 150).sum())
R['bottom_gap_px_y560_674'] = {'ours': holes, 'ref_lt150': holes_ref}
# diagonal edge probe: vertical luminance profile gradient at given columns, report strongest dark->light / light->dark steps
def edges_col(Lm, x, y0, y1):
    col = box(Lm, 1)[:, x]
    g = np.abs(np.diff(col[y0:y1]))
    idx = np.argsort(g)[::-1][:5]
    return sorted([(int(i+y0), round(float(g[i]), 1)) for i in idx])
R['col_edges'] = {}
for x in (195, 240, 283, 340):
    R['col_edges'][str(x)] = {'ref': edges_col(L, x, 120, 420), 'ours': edges_col(Lo, x, 120, 420)}
# grain: highpass (L - box3) std in flat patches, normalised by local mean too
def hp_patch(Lm, x0, y0, s=48):
    P = Lm[y0:y0+s, x0:x0+s]; hp = P - box(P, 3)
    return {'hp_std': round(float(hp[4:-4, 4:-4].std()), 3), 'mean': round(float(P.mean()), 1), 'hp_rel': round(float(hp[4:-4, 4:-4].std()/max(P.mean(), 1e-3)), 4)}
R['grain'] = {}
for name, (x0, y0) in {'mantle': (220, 230), 'front_panel': (250, 470), 'left_fall': (60, 380), 'centre': (160, 330)}.items():
    R['grain'][name] = {'ref': hp_patch(L, x0, y0), 'ours': hp_patch(Lo, x0, y0)}
# textures
def texinfo(p):
    a = load(p); d = {'shape': list(a.shape)}
    for i, cn in enumerate('RGB'):
        ch = a[..., i]*255
        d[cn] = [round(float(ch.min()), 1), round(float(ch.mean()), 2), round(float(ch.max()), 1)]
    return a, d
bc, R['tex_BC'] = texinfo(TEX+"T_BlackCloak_BaseColor.png")
rg, R['tex_Rough'] = texinfo(TEX+"T_BlackCloak_Roughness.png")
ndx, R['tex_N_DX'] = texinfo(TEX+"T_BlackCloak_Normal_DirectX.png")
ngl, R['tex_N_GL'] = texinfo(TEX+"T_BlackCloak_Normal_OpenGL.png")
R['N_green_sum_dev'] = round(float(np.abs(ndx[..., 1]*255+ngl[..., 1]*255-255).max()), 2)
# integrability sign test: a gradient field n=(-dh/dx, -dh/dy_up) in GL gives dR/drow = -dG/dcol (row down)
def curl_sign(n):
    Rch = n[..., 0]*2-1; G = n[..., 1]*2-1
    # images stored top row first after [::-1]; row index increases downward
    dR_drow = np.roll(Rch, -1, 0)-np.roll(Rch, 1, 0)
    dG_dcol = np.roll(G, -1, 1)-np.roll(G, 1, 1)
    a = dR_drow.ravel(); b = dG_dcol.ravel()
    return round(float(np.corrcoef(a, b)[0, 1]), 4)
R['N_integrability_corr_dRdrow_vs_dGdcol'] = {'DX_file': curl_sign(ndx), 'GL_file': curl_sign(ngl),
    'rule': 'GL (+Y up) -> negative; DX (+Y down) -> positive'}
# roughness linear-ish values
R['rough_values_0_1'] = [round(float(rg[..., 0].min()), 4), round(float(rg[..., 0].max()), 4)]
# BaseColor linear
def s2l(c): return np.where(c <= 0.04045, c/12.92, ((c+0.055)/1.055)**2.4)
bl = s2l(bc[..., 0])
R['BC_linear_R'] = {'min': round(float(bl.min()), 5), 'mean': round(float(bl.mean()), 5), 'max': round(float(bl.max()), 5), 'levels': int(np.unique((bc[..., 0]*255).round()).size)}
# ref cloth linear albedo lower bound if bg white=1.0 lit: p50/p95 sRGB -> linear
R['ref_cloth_linear_p50_p95'] = [round(float(s2l(np.array(R['ref_cloth_core_y_lt600']['p50']/255))), 4), round(float(s2l(np.array(R['ref_cloth_core_y_lt600']['p95']/255))), 4)]
# own creator render (Revision_Front) cloth stats for lighting dependence
try:
    rv = load(r"C:/Users/Cody/Desktop/Blender_Projects/Renders/BlackCloak/ReferenceRevision/Revision_Front.png"); Lr = lum(rv)
    mr = erode(Lr < 200, 6); R['creator_revision_front_cloth'] = stats(Lr[mr])
    ck = load(r"C:/Users/Cody/Desktop/Blender_Projects/Renders/BlackCloak/Recolor/Cloak_Black.png"); Lk = lum(ck)
    bgk = np.median(Lk[:15, :15]); mk = erode(Lk < bgk-25, 6); R['creator_recolor_black_cloth'] = stats(Lk[mk]); R['creator_recolor_black_bg'] = float(bgk)
except Exception as ex:
    R['creator_err'] = str(ex)
json.dump(R, open(OUT+"vl_measure.json", "w"), indent=1)
print(json.dumps(R, indent=1))
