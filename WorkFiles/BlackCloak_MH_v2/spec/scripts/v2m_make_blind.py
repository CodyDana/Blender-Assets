"""Blind A/B pairs for BlackCloak_MH_v2: PHOTO DETAILS ONLY (fabric, edges/fray, hem, outline below the cowl).
Adapted copy of WorkFiles/BlackCloak_Review/male/blind_tools/make_blind_male.py.

blender -b --factory-startup --python v2m_make_blind.py -- <render_dir> <tag> <pairs_out_dir> <keyfile_in_scratchpad>
Needs <tag>_refframe.npy + <tag>_aligned_mask.npy (from v2m_silhouette_score.py + v2m_fabric_score.py on a photo-view
render made with --mult 2 or more). Ours is already box-downsampled in linear light to the photo's pixel density and
aligned; one global exposure curve f(x) = g x / (1 + (g-1) x) in linear light matches the garment medians (fair: it
keeps 0 and 1 and contrast shape). Silhouettes = luma < 0.45 masks. The collar (rows < 120), the clasp and the front
layering are NOT shown: v2 follows Jin_Cloak there by the user's decision. 20 pairs; side key from OS entropy, written
ONLY to <keyfile> (keep it away from the judge). Pass = the judge picks the photo in 13 or fewer of 20."""
import sys, os, json, random
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import bpy
import v2m_lib as L

a = sys.argv[sys.argv.index("--") + 1:]
RD, TAG, OUT, KEY = os.path.abspath(a[0]), a[1], os.path.abspath(a[2]), os.path.abspath(a[3])
REF = "C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/blackcloak.png"
ref = L.load(REF) / 255.0; H, W = ref.shape[:2]
ours = np.load(os.path.join(RD, TAG + "_refframe.npy")).astype(np.float64) / 255.0
THR = 0.45
lum = lambda x: 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]
refm = lum(ref) < THR; om = lum(ours) < THR
rl = L.srgb_to_lin01(ref); ol = L.srgb_to_lin01(ours)
target = float(np.median(lum(rl)[refm])); base = float(np.median(lum(ol)[om]))
def curve(x, g): return g * x / (1 + (g - 1) * x)
lo, hi = 0.05, 20.0
for _ in range(60):
    g = 0.5 * (lo + hi)
    if np.median(lum(curve(ol, g))[om]) < target: lo = g
    else: hi = g
g = 0.5 * (lo + hi)
ours_e = L.lin_to_srgb01(curve(ol, g))
both = refm & om
# fabric patches: the 6 flattest 48x48 windows inside both garments, rows 150..600
lf = L.blur2d(lum(ref) * 255, 9); cands = []
for y in range(150, 600 - 48, 8):
    for x in range(20, 397 - 48, 8):
        if not both[y:y + 48, x:x + 48].all(): continue
        w = lf[y:y + 48, x:x + 48]; gy, gx = np.gradient(w); cands.append((float(np.hypot(gx, gy).mean()), x, y))
cands.sort(); fab = []
for c in cands:
    if all(abs(c[1] - q[1]) >= 48 or abs(c[2] - q[2]) >= 48 for q in fab): fab.append(c)
    if len(fab) == 6: break
regions = [("img", (x, y, x + (48 if i < 3 else 24), y + (48 if i < 3 else 24)), 0) for i, (_, x, y) in enumerate(fab)]
regions += [
    ("img", (0, 520, 185, 674), 0), ("img", (230, 520, 417, 674), 0), ("img", (115, 540, 305, 674), 0),
    ("img", (310, 560, 417, 674), 0), ("img", (0, 560, 110, 674), 0),                       # hem
    ("img", (0, 220, 150, 480), 0), ("img", (285, 250, 417, 480), 0), ("img", (20, 410, 115, 560), 0),
    ("img", (330, 420, 417, 600), 0), ("img", (300, 120, 417, 260), 0),                     # outer edges / fray
    ("sil", (0, 120, 417, 674), 520), ("sil", (0, 400, 417, 674), 440),                      # outline below the cowl
    ("img", (0, 400, 208, 674), 0), ("img", (208, 400, 417, 674), 0),                        # lower quadrants (drape + hem)
]
while len(regions) < 20:
    regions.append(("img", (150, 300, 270, 420), 0))
regions = regions[:20]
sil_r = np.where(refm, 0.0, 1.0)[..., None].repeat(3, 2); sil_o = np.where(lum(ours_e) < THR, 0.0, 1.0)[..., None].repeat(3, 2)


def crop_up(img, box, target):
    x0, y0, x1, y1 = box; c = img[y0:y1, x0:x1]; w, h = x1 - x0, y1 - y0
    k = (target or 440) / max(w, h); Wn, Hn = int(round(w * k)), int(round(h * k))
    Y, X = np.mgrid[0:Hn, 0:Wn].astype(np.float64)
    return np.clip(L.bilinear(c, (X + 0.5) / k - 0.5, (Y + 0.5) / k - 0.5, 1.0), 0, 1)


os.makedirs(OUT, exist_ok=False)
rng = random.Random(int.from_bytes(os.urandom(16), "little")); key = []
for i, (kind, box, t) in enumerate(regions, 1):
    A_, B_ = (crop_up(sil_r, box, t), crop_up(sil_o, box, t)) if kind == "sil" else (crop_up(ref, box, t), crop_up(ours_e, box, t))
    side = rng.choice(("left", "right")); key.append(side)
    Lp, Rp = (B_, A_) if side == "left" else (A_, B_)
    gap = np.full((A_.shape[0], 16, 3), 0.5)
    L.save(os.path.join(OUT, "pair_%02d.png" % i), np.concatenate([Lp, gap, Rp], 1) * 255)
with open(KEY, "w") as f: json.dump(key, f)
del key, rng
meta = {"source_ours": os.path.join(RD, TAG + ".png"), "source_ref": REF, "exposure_gain_linear": g, "garment_median_lin_ref": target,
        "garment_median_lin_ours_raw": base, "regions": [[k, list(b), t] for k, b, t in regions], "key": "not stored here",
        "judge_prompt": "Each image has two crops of a black cloak side by side. One is from a real product photo, one is a render. For each pair say which side is the PHOTO (left/right) and how confident (sure/guess), and name the tell."}
json.dump(meta, open(os.path.join(OUT, "blind_params.json"), "w"), indent=1)
print("V2M BLIND pairs=20", OUT)
