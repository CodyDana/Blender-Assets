
# Align captures to the reference frame (best IoU over scale+translation) and write aligned images + grid sheets.
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import gap_lib as L

ROOT = 'C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/male'
OUT = ROOT + '/gap/out'
REF = 'C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png'
TH = 115.0

ref = L.load(REF); H, W = ref.shape[:2]
refm = L.lum(ref) < TH

jobs = {
 # name: (primary cloak-only 2x image, init (s,tx,ty), extra images sharing the framing)
 'BL': (ROOT+'/blender/compare/a_ref_cloak_game_refframe_2x.png', (1.0, 0.0, 0.0),
        {'BLbody': ROOT+'/blender/compare/b_ref_body_down_game_refframe_2x.png',
         'BLtiled': ROOT+'/blender/compare/a2_ref_cloak_tiled_refframe_2x.png'}),
 'UE': (ROOT+"/unreal/shots/front_cloak_only_yaw+0.png", (1.0, 0.0, 0.0),
        {'UEbody': ROOT+'/unreal/shots/front_with_body.png',
         'UEsettled': ROOT+'/unreal/shots/front_with_body_cloth_SIE_settled.png',
         'UEp2ev': ROOT+'/unreal/shots/DIAG_front_cloak_only_plus2EV.png'}),
}

def score(m2f, p):
    s, tx, ty = p
    w = L.warp_to_ref(m2f, s, tx, ty) > 0.5
    return L.iou(w, refm)

def bbox(m):
    ys, xs = np.where(m); return xs.min(), ys.min(), xs.max()+1, ys.max()+1

report = {}
aligned = {'REF': ref}
for name, (p2x, init, extra) in jobs.items():
    img2 = L.load(p2x)
    m2f = (L.lum(img2) < TH).astype(np.float32)
    if init is None:
        # bbox init: ours1x = 2x/2
        ob = np.array(bbox(m2f > 0.5), float)/2.0
        rb = np.array(bbox(refm), float)
        s = (rb[3]-rb[1])/(ob[3]-ob[1])
        tx = rb[0] - s*ob[0]; ty = rb[1] - s*ob[1]
        init = (s, tx, ty)
    p = list(init); best = score(m2f, p)
    for step_t, step_s in [(4, 0.02), (2, 0.01), (1, 0.005), (0.5, 0.0025), (0.25, 0.00125)]:
        improved = True
        while improved:
            improved = False
            for d in [(step_s,0,0),(-step_s,0,0),(0,step_t,0),(0,-step_t,0),(0,0,step_t),(0,0,-step_t)]:
                q = [p[0]+d[0], p[1]+d[1], p[2]+d[2]]
                sc = score(m2f, q)
                if sc > best + 1e-6:
                    best, p, improved = sc, q, True
    report[name] = {'init': list(map(float, init)), 's': p[0], 'tx': p[1], 'ty': p[2], 'iou_best': best,
                    'iou_init': score(m2f, init), 'src': p2x}
    print(name, report[name])
    for nm, path in [(name, p2x)] + list(extra.items()):
        im = L.load(path)
        a1 = L.warp_to_ref(im, *p, out_scale=1)
        a2 = L.warp_to_ref(im, *p, out_scale=2)
        L.save(f'{OUT}/aligned_{nm}_1x.png', a1)
        L.save(f'{OUT}/aligned_{nm}_2x.png', a2)
        np.save(f'{OUT}/aligned_{nm}_1x.npy', a1.astype(np.float32))
        np.save(f'{OUT}/aligned_{nm}_2x.npy', a2.astype(np.float32))
        aligned[nm] = a1

np.save(f'{OUT}/ref_1x.npy', ref.astype(np.float32))
# ref 2x (bilinear) for sheets
Y, X = np.mgrid[0:H*2, 0:W*2].astype(np.float64)
ref2 = L.bilinear(ref, (X+0.5)/2-0.5, (Y+0.5)/2-0.5)

def gridded(img2, stretch=False):
    a = img2.copy()
    if stretch:
        l = L.lum(a); m = l < TH
        lo, hi = np.percentile(l[m], 1), np.percentile(l[m], 99.5)
        f = np.clip((l - lo)/(hi-lo+1e-6), 0, 1)*230
        a = np.where(m[..., None], np.stack([f]*3, -1), a)
    for g in range(0, 674*2, 40):
        col = (255, 0, 0) if g % 200 == 0 else (0, 160, 255)
        a[g, :, :] = col
    for g in range(0, 417*2, 40):
        col = (255, 0, 0) if g % 200 == 0 else (0, 160, 255)
        a[:, g, :] = col
    return a

sheets = []
for stretch in (False, True):
    row = [gridded(ref2, stretch)]
    for nm in ['BL', 'UE']:
        row.append(np.full((1348, 8, 3), 128.0))
        row.append(gridded(L.warp_to_ref(L.load(jobs[nm][0]), report[nm]['s'], report[nm]['tx'], report[nm]['ty'], 2), stretch))
    sh = np.concatenate(row, 1)
    L.save(f'{OUT}/sheet_grid_{"stretch" if stretch else "plain"}_REF_BL_UE_2x.png', sh)

json.dump(report, open(ROOT+'/gap/logs/align.json', 'w'), indent=1)
print('done')
