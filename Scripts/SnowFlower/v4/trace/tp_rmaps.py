"""Trace pilot v2 stage R2: material maps in the RELIEF domain (reference rows 26-178, cols 415-597, 8 samples/px).

    blender -b --factory-startup --python tp_rmaps.py

Colours are the reference's SAMPLED tones (work/tones.json, tp_tones.py), turned into an antiqued finish from the
traced relief itself: recesses (relief below its 1.2 px blur) collect grime (darker, rougher), crests and edges (relief
above its 0.6 px blur) are polished (brighter, smoother).  Classes: 0 dark ground (lacquer), 1 silver, 2 enamel inset,
3 pearl.  Output: work/relief_BC.png (sRGB), relief_R.png, relief_M.png (linear), used ONLY as the high-poly
bake source (the game mesh gets its own baked maps)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img, tp_geom2d as G

WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
Z = np.load(WORK + "/relief.npz")
H = Z["H_relief"].astype(np.float64); CLS = Z["CLS"]; S = int(Z["S"])
tones = json.load(open(WORK + "/tones.json"))
T = tones["albedo_linear"]
CAL = json.load(open(WORK + "/rmaps_cal.json")) if os.path.exists(WORK + "/rmaps_cal.json") else {}
k_sil = CAL.get("silver", 1.0); k_pearl = CAL.get("pearl", 1.0); k_en = CAL.get("enamel", 1.0); k_lac = CAL.get("lacquer", 1.0)

cav = G.gauss(H, 1.2 * S) - H
conv = H - G.gauss(H, 0.6 * S)
def sstep(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)
grime = sstep(cav / 0.35)
edge = sstep(conv / 0.10)
# low-frequency antiquing variation (deterministic value noise)
rng = np.random.default_rng(7)
nz = G.gauss(rng.standard_normal((H.shape[0] // 8 + 1, H.shape[1] // 8 + 1)), 2.0)
nz = np.kron(nz, np.ones((8, 8)))[:H.shape[0], :H.shape[1]]
nz = (nz - nz.mean()) / (nz.std() + 1e-9)

onehot = np.stack([(CLS == k).astype(np.float64) for k in range(4)], -1)
onehot = np.stack([G.gauss(onehot[..., k], 0.25 * S) for k in range(4)], -1)
onehot /= onehot.sum(-1, keepdims=True) + 1e-9

sil = np.array(T["silver"]) * k_sil
en = np.array(T["enamel"]) * k_en
pe = np.array(T["pearl"]) * k_pearl
la = np.array(T["lacquer"]) * k_lac
g3 = grime[..., None]; e3 = edge[..., None]
bc_sil = sil * (1.15 + 0.06 * nz[..., None]) * (1 - 0.65 * g3) + e3 * (np.minimum(sil * 2.5, 0.8) - sil * 1.15) * (1 - g3)
bc_en = en * (1 + 0.6 * g3) + 0 * e3
bc_pe = pe * 1.5 * (1 - 0.35 * g3) * np.array([0.98, 0.99, 1.02])
bc_la = la * 0.55 * (1 - 0.3 * g3)
BC = onehot[..., 0:1] * bc_la + onehot[..., 1:2] * bc_sil + onehot[..., 2:3] * bc_en + onehot[..., 3:4] * bc_pe
r_sil = 0.48 + 0.05 * nz - 0.16 * edge + 0.2 * grime
R = onehot[..., 0] * (0.26 + 0.1 * grime) + onehot[..., 1] * r_sil + onehot[..., 2] * (0.14 + 0.15 * grime) + onehot[..., 3] * (0.12 + 0.1 * grime)
M = onehot[..., 1] * (1.0 - 0.35 * grime)
# swatches for the side bands (tp_rbuild): two flat patches in the unused top corners of the relief domain
R0_, C0_ = int(Z["R0"]), int(Z["C0"])
def patch(c0, c1):
    return slice((26 - R0_) * S, (30 - R0_) * S), slice((c0 - C0_) * S, (c1 - C0_) * S)
ps = patch(415, 424); pl = patch(588, 597)
BC[ps] = sil * 1.1; R[ps] = 0.46; M[ps] = 1.0
BC[pl] = la * 0.55; R[pl] = 0.30; M[pl] = 0.0
def srgb(c):
    c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)
tp_img.save(WORK + "/relief_BC.png", srgb(BC))
tp_img.save(WORK + "/relief_R.png", np.clip(R, 0, 1))
tp_img.save(WORK + "/relief_M.png", np.clip(M, 0, 1))
print("maps", BC.shape, "silver bc range", float(bc_sil.min()), float(bc_sil.max()), flush=True)
