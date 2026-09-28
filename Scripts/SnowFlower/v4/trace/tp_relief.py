"""Trace pilot v2 stage R1: TRACED RELIEF of the sheath throat (front view) - heights + material classes per sample.

    blender -b --factory-startup --python tp_relief.py

Why v2: the v1 build (tp_build.py) made every traced outline a separate bevelled curve slab wrapped onto the crown.
Its front compare showed torn plate edges / holes at the crown top (curve-fill failures on the traced loops), petals
that read as round pebbles (3.2 mm domes, shrunk 1 px inside separate bezels), flat grey insets and a 1.2 mm step at
the throat bottom.  v2 keeps the SAME traces (work/trace_plates.json pen-tool plates snapped to the reference edges,
work/blossom_fit.json petals / pearl / stamen beads, the traced silhouette) but builds them as ONE layered relief:

    H(col, row)  = height (mm) over the crown surface, on a grid of S samples per reference pixel.
    Plates are painted in the reference's overlap order; each plate DRAPES over what is already painted under it
    (support = smoothed max-filter of the current relief) + its own thickness profile:
        silver band between the traced outer edge and the traced inset edge = a rounded bar (0.55 t at both edges,
        t at the middle, bevelled outer wall), inset = recessed concave enamel dish, tips curl outward.
    Blossom: fitted petals = raised silver bezel + low pearl cushion (2 mm) cupped outward, centre pearl + bezel,
    radiating stamens with beads.  Filigree (crests, sprigs, the lace fringe) = heights inferred from the reference
    SHADING (bright = raised silver; the lace uses a local high-pass so lacquer sheen is not mistaken for lace).
    Relief fades to 0 over the last 2.5 px at the silhouette (the plates turn away there and meet their mirrored back
    copies) and the whole throat sinks flush into the body over rows 160-176 (no step at the bottom).
Outputs work/relief.npz (H mm, CLS, maps inputs) and previews work/relief_*.png."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import tp_img, tp_geom2d as G
import tp_crown as C

WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
R0, R1, C0, C1 = 26, 178, 415, 597
S = 8
K = C.K
AXIS = C.AXIS
ref = np.load(WORK + "/ref_full.npy")[..., :3]
lum1 = ref @ np.array([0.2126, 0.7152, 0.0722])
NR, NC = (R1 - R0) * S, (C1 - C0) * S
xs = C0 + (np.arange(NC) + 0.5) / S
ys = R0 + (np.arange(NR) + 0.5) / S
X, Y = np.meshgrid(xs, ys)


def bilinear(F, px, py, f0r=0, f0c=0, s=1):
    """sample 1x field F (full image index) at ref px coords (pixel centres at +0.5)."""
    x = px * s - 0.5 - f0c; y = py * s - 0.5 - f0r
    x0 = np.clip(np.floor(x).astype(int), 0, F.shape[1] - 2); y0 = np.clip(np.floor(y).astype(int), 0, F.shape[0] - 2)
    fx = np.clip(x - x0, 0, 1); fy = np.clip(y - y0, 0, 1)
    return (F[y0, x0] * (1 - fx) * (1 - fy) + F[y0, x0 + 1] * fx * (1 - fy) + F[y0 + 1, x0] * (1 - fx) * fy
            + F[y0 + 1, x0 + 1] * fx * fy)


LUM = bilinear(lum1, X, Y)
LUM = G.gauss(LUM, 0.35 * S)


def sstep(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)


def box(poly, pad=4.0):
    P = np.asarray(poly, float)
    c0 = int(max((P[:, 0].min() - pad - C0) * S, 0)); c1 = int(min((P[:, 0].max() + pad - C0) * S, NC))
    r0 = int(max((P[:, 1].min() - pad - R0) * S, 0)); r1 = int(min((P[:, 1].max() + pad - R0) * S, NR))
    return slice(r0, r1), slice(c0, c1)


def sdist(poly, sl=None, pad=4.0):
    """signed distance (ref px, + inside) to a closed polygon, on the box sl (default: polygon bbox + pad)."""
    P = G.resample_closed(np.asarray(poly, float), 0.25)
    if sl is None:
        sl = box(P, pad)
    x = X[sl].ravel(); y = Y[sl].ravel()
    a = P; b = np.roll(P, -1, 0)
    d = np.full(x.shape, 1e9)
    for k in range(0, len(a), 96):
        A = a[k:k + 96]; B = b[k:k + 96]; AB = B - A
        apx = x[:, None] - A[None, :, 0]; apy = y[:, None] - A[None, :, 1]
        t = np.clip((apx * AB[None, :, 0] + apy * AB[None, :, 1]) / ((AB ** 2).sum(1)[None] + 1e-12), 0, 1)
        dx = apx - t * AB[None, :, 0]; dy = apy - t * AB[None, :, 1]
        d = np.minimum(d, np.sqrt(dx * dx + dy * dy).min(1))
    ins = G.pip(x, y, P)
    return sl, np.where(ins, d, -d).reshape(X[sl].shape)


def maxfilt(A, r):
    out = A.copy()
    for ax in (0, 1):
        B = out.copy()
        for k in range(1, r + 1):
            if ax == 0:
                B[k:] = np.maximum(B[k:], out[:-k]); B[:-k] = np.maximum(B[:-k], out[k:])
            else:
                B[:, k:] = np.maximum(B[:, k:], out[:, :-k]); B[:, :-k] = np.maximum(B[:, :-k], out[:, k:])
        out = B
    return out


def support(sl, r_px=2.5, s_px=2.0):
    """what a plate drapes over: smoothed max-filter of the relief painted so far (on the box)."""
    pad = int((r_px + 3 * s_px) * S) + 2
    rs = slice(max(sl[0].start - pad, 0), min(sl[0].stop + pad, NR)); cs = slice(max(sl[1].start - pad, 0), min(sl[1].stop + pad, NC))
    A = maxfilt(H[rs, cs], int(r_px * S))
    A = G.gauss(A, s_px * S)
    return A[sl[0].start - rs.start: sl[0].stop - rs.start, sl[1].start - cs.start: sl[1].stop - cs.start]


H = np.zeros((NR, NC))
CLS = np.zeros((NR, NC), np.int8)        # 0 dark base (lacquer/enamel ground), 1 silver, 2 enamel inset, 3 pearl
FOOT = np.zeros((NR, NC), bool)          # covered by a traced plate / crest / blossom (no lace there)
LAYER = np.zeros((NR, NC), np.int16)     # paint order index (for the previews)
CLS_NAMES = ["base", "silver", "enamel", "pearl"]

TP = json.load(open(WORK + "/trace_plates.json"))["plates"]
BF = json.load(open(WORK + "/blossom_fit.json"))
BC_ = np.array(BF["centre"], float)
GAP = 0.3
RIM_E = 0.35                                # rim height at its two edges (fraction of t): a rounded bar
PL = {  # thickness t (mm), tip curl (mm)
    "sleeve": dict(t=1.6, curl=0.0), "t2": dict(t=3.0, curl=1.0), "t1": dict(t=3.4, curl=1.6),
    "drop": dict(t=3.0, curl=0.0), "flare": dict(t=3.0, curl=1.2), "lat": dict(t=3.6, curl=1.6)}
ORDER = ["sleeve_L", "sleeve_R", "t2_L", "t2_R", "crestT", "t1_L", "t1_R", "drop", "crestB", "flare_L", "flare_R",
         "lat_L", "lat_R"]


def curl_lift(sl, outer, amount):
    if amount <= 0:
        return 0.0
    L = np.asarray(outer, float)
    dmax = float(np.hypot(L[:, 0] - BC_[0], L[:, 1] - BC_[1]).max())
    dd = np.hypot(X[sl] - BC_[0], Y[sl] - BC_[1])
    return amount * np.clip((dd - 22.0) / max(dmax - 22.0, 1e-3), 0, 1) ** 2


def filigree(sl, inside, base, amp, thr=0.30, span=0.30, cls_bg=2, highpass=False):
    """heights inferred from the reference shading: bright = raised silver."""
    L = LUM[sl]
    F = np.clip((L - thr) / span, 0, 1)
    if highpass:
        F = F * np.clip((L - G.gauss(LUM, 3.0 * S)[sl] - 0.02) / 0.10, 0, 1)
    F = G.gauss(F, 0.3 * S)
    z = base + amp * F ** 0.8
    Hs = H[sl]; Cs = CLS[sl]
    Hs[inside] = z[inside]
    Cs[inside] = np.where(F[inside] > 0.33, 1, cls_bg)
    return F


for li, nm in enumerate(ORDER):
    e = TP[nm]
    kind = nm.split("_")[0]
    outer = G.smooth_closed(G.resample_closed(np.asarray(e["outer"], float), 0.4), 10)
    sl, do = sdist(outer)
    inside = do > 0
    sup = support(sl, r_px=4.0, s_px=4.0)          # rigid plates: they bridge small details underneath
    if kind in ("crestT", "crestB"):
        base = sup + (0.35 if kind == "crestT" else 0.25)
        filigree(sl, inside, base, 1.2, thr=0.30, span=0.30, cls_bg=2)
        FOOT[sl] |= inside; LAYER[sl][inside] = li + 1
        print("crest", nm, int(inside.sum()), flush=True)
        continue
    p = PL[kind]; t = p["t"]
    if "inset" in e:
        inset = G.smooth_closed(G.resample_closed(np.asarray(e["inset"], float), 0.4), 40)
        _, di = sdist(inset, sl)
        dI = -di                                   # > 0 outside the inset (in the band)
    else:
        di = np.full(do.shape, -1e3); dI = np.full(do.shape, 1e3)
    band = inside & (di <= 0)
    ins = inside & (di > 0)
    if "inset" in e:
        w = np.maximum(do + dI, 1e-3)
        u = np.clip(do / w, 0, 1)
        dedge = np.minimum(do, dI)
        # flat-topped strap with rounded 1 px bevels on both edges and a slight crown
        prof = RIM_E + (1 - RIM_E - 0.08) * np.sqrt(np.clip(dedge / 1.0, 0, 1)) + 0.08 * np.sin(np.pi * u)
    else:
        prof = RIM_E + (1 - RIM_E) * np.sqrt(np.clip(do / 1.0, 0, 1))
    lift = curl_lift(sl, e["outer"], p["curl"])
    wall = sstep(do / 0.2)                             # crisp outer wall (0.2 px ~ 0.14 mm)
    zb = sup + (GAP + t * prof) * wall + lift * wall
    # inset: recessed enamel dish, deepest ~3 px inside its rim
    zi = sup + GAP + t * 0.10 - 0.5 * sstep(np.maximum(di, 0) / 3.0) + lift
    Hs = H[sl]; Cs = CLS[sl]
    Hs[band] = zb[band]; Cs[band] = 1
    Hs[ins] = zi[ins]; Cs[ins] = 2
    FOOT[sl] |= inside; LAYER[sl][inside] = li + 1
    print("plate", nm, "t", t, "band px", int(band.sum()), "inset px", int(ins.sum()),
          "z range %.2f..%.2f" % (float(zb[band].min()), float(zb[band].max())), flush=True)

# ------------------------------------------------------------------ sprigs (silver bud clusters between the petals)
for (cx, cy) in ((487.0, 66.0), (480.5, 99.0)):
    for sx in (cx, 2 * AXIS - cx):
        tt = np.linspace(0, 2 * np.pi, 64, endpoint=False)
        poly = np.c_[sx + 6.0 * np.cos(tt), cy + 6.0 * np.sin(tt)]
        sl, d = sdist(poly)
        sup = support(sl)
        F = np.clip((LUM[sl] - 0.34) / 0.30, 0, 1)
        m = (d > 0) & (G.gauss(F, 0.4 * S) > 0.2)
        z = sup + 0.3 + 1.7 * G.gauss(F, 0.35 * S) ** 0.8 * sstep(d / 1.5)
        H[sl][m] = np.maximum(H[sl][m], z[m]); CLS[sl][m] = 1
        FOOT[sl] |= m

# ------------------------------------------------------------------ blossom
cx, cy = BC_


def petal_poly(phi, d0, d1, w, q, e, n=160):
    s = np.linspace(0, 1, n)
    hw = w / 2 * (2 * np.sqrt(np.clip(s * (1 - s), 0, None))) ** q * (1 + e * (s - 0.5))
    u = d0 + s * (d1 - d0)
    Q = np.vstack([np.c_[u, hw], np.c_[u[::-1], -hw[::-1]][1:-1]])
    cu, su = np.cos(phi), np.sin(phi)
    return np.c_[cx + Q[:, 0] * cu - Q[:, 1] * su, cy + Q[:, 0] * su + Q[:, 1] * cu]


bl_poly = np.c_[cx + 37 * np.cos(np.linspace(0, 2 * np.pi, 90, endpoint=False)),
                cy + 37 * np.sin(np.linspace(0, 2 * np.pi, 90, endpoint=False))]
slB = box(bl_poly, 1.0)
supB = support(slB, r_px=3.0, s_px=3.0)
baseB = supB + 1.0
RB = np.hypot(X[slB] - cx, Y[slB] - cy)
cup = 1.5 * np.clip((RB - 8.0) / 27.0, 0, 1) ** 2        # cupped: petals rise outward
PET = np.full(RB.shape, -1e9); PCL = np.zeros(RB.shape, np.int8); PIN = np.zeros(RB.shape, bool)
petals_px = json.load(open(WORK + "/petals_traced.json"))["petals"]     # tp_petals.py: traced PEARL edges
BEZ = 1.1                                   # silver bezel width outside the traced pearl edge (px)
for i, poly in enumerate(petals_px):
    _, d = sdist(poly, slB)
    inside = d > -BEZ
    dm = float(d.max())
    # silver bezel: rounded rim hugging the pearl; the pearl is a low cushion inside it
    db_ = d + BEZ                                           # 0 at the bezel's outer edge
    bz = 1.3 + 0.6 * np.sin(np.pi * np.clip(db_ / (BEZ + 0.25), 0, 1)) * sstep(db_ / 0.3)
    q = np.clip(d / (0.85 * dm), 0, 1)
    pearl = 1.1 + 4.2 * np.sqrt(np.clip(1 - (1 - q) ** 2, 0, 1))
    z = np.where(d < 0, bz, np.maximum(pearl, bz * (d < 0.25)))
    z = baseB + z + cup
    cl = np.where(d < 0, 1, 3)
    upd = inside & (z > PET)
    PET[upd] = z[upd]; PCL[upd] = cl[upd]; PIN |= inside
Hs = H[slB]; Cs = CLS[slB]
# dark rosette ground between the petals and the pearl ring
ros = (RB < 11.5) & ~PIN
Hs[ros] = baseB[ros] + 0.2; Cs[ros] = 2
Hs[PIN] = PET[PIN]; Cs[PIN] = PCL[PIN]
FOOT[slB] |= PIN | ros
# centre pearl with its bezel
pr = BF["pearl"]
rp = pr["r"] + 0.3
Rp = np.hypot(X[slB] - pr["cx"], Y[slB] - pr["cy"])
ring = (Rp >= rp) & (Rp < rp + 1.4)
Hs[ring] = baseB[ring] + 2.0 + 0.6 * np.sin(np.pi * (Rp[ring] - rp) / 1.4); Cs[ring] = 1
pm = Rp < rp
Rmm = rp * K
Hs[pm] = baseB[pm] + 2.2 + np.sqrt(np.clip(Rmm ** 2 - (Rp[pm] * K) ** 2, 0, None)) * 1.05; Cs[pm] = 3
# stamens: rods from the pearl bezel to the traced beads + beads
beads = sorted(BF["stamen_beads"], key=lambda b: -b[2])
keep = []
for b in beads:
    if all(math.hypot(b[0] - k[0], b[1] - k[1]) > 2.4 for k in keep):
        keep.append(b)
keep = keep[:12]
for b in keep:
    ang = math.atan2(b[1] - pr["cy"], b[0] - pr["cx"])
    p0 = np.array([pr["cx"] + (rp + 1.2) * math.cos(ang), pr["cy"] + (rp + 1.2) * math.sin(ang)])
    p1 = np.array(b[:2])
    ab = p1 - p0
    tq = np.clip(((X[slB] - p0[0]) * ab[0] + (Y[slB] - p0[1]) * ab[1]) / (ab @ ab), 0, 1)
    dl = np.hypot(X[slB] - p0[0] - tq * ab[0], Y[slB] - p0[1] - tq * ab[1])
    rod = (dl < 0.42) & ~PIN
    zr_ = baseB + 1.8 + 0.4 * np.sqrt(np.clip(1 - (dl / 0.42) ** 2, 0, 1))
    Hs[rod] = np.maximum(Hs[rod], zr_[rod]); Cs[rod] = 1
    db = np.hypot(X[slB] - p1[0], Y[slB] - p1[1])
    bead = db < 0.95
    zbd = baseB + 2.0 + np.sqrt(np.clip((0.95 * K) ** 2 - (db * K) ** 2, 0, None))
    upd = bead & (zbd > Hs)
    Hs[upd] = zbd[upd]; Cs[upd] = 1
print("blossom petals", len(BF["petals"]), "stamens", len(keep), "pearl r px", rp, flush=True)

# ------------------------------------------------------------------ lace fringe / body filigree (rows >= 124, off-plate)
lace_zone = (Y >= 124.0) & ~FOOT
F = np.clip((LUM - 0.27) / 0.22, 0, 1) * np.clip((LUM - G.gauss(LUM, 3.0 * S) - 0.015) / 0.10, 0, 1)
F = G.gauss(F, 0.3 * S)
lace_up = sstep((Y - 124.0) / 4.0)
zl = 0.75 * F ** 0.8 * lace_up
H[lace_zone] = zl[lace_zone]
CLS[lace_zone] = np.where(F[lace_zone] > 0.3, 1, 0)

# ------------------------------------------------------------------ silhouette fade + bottom flush
sub = json.load(open(WORK + "/trace.json"))["silhouette_sub"]
crown = C.Crown(None, sub)
rows_s = np.asarray(sub["rows"]); Ls = np.asarray(sub["left"]); Rs = np.asarray(sub["right"])
# the crown's smoothed silhouette (what the mesh edge actually follows), in ref px
aL = np.interp(ys, crown.rows, crown.aL); aR = np.interp(ys, crown.rows, crown.aR)
colL = AXIS - aL / K; colR = AXIS + aR / K
ds = np.minimum(X - colL[:, None], colR[:, None] - X)
FADE = sstep(ds / 2.5)
# v2b: no fade - the side band carries the relief seen just inside the silhouette around to the back (tp_rbuild clamp)
if os.environ.get("TP_FADE") == "1":
    H = H * FADE
# v2b: the bottom now CONFORMS to the real r1 body surface in tp_rbuild (rows 158-176); the old uniform sink is off
DOWN = -(C.standoff(Y) + 0.25) * sstep((Y - 160.0) / 16.0) if os.environ.get("TP_DOWN") == "1" else 0.0 * Y
Hf = H + DOWN
print("H range %.2f..%.2f mm" % (float(Hf.min()), float(Hf.max())), flush=True)
np.savez_compressed(WORK + "/relief.npz", H=Hf.astype(np.float32), H_relief=H.astype(np.float32), CLS=CLS,
                    FOOT=FOOT, LAYER=LAYER, R0=R0, R1=R1, C0=C0, C1=C1, S=S)
json.dump({"petals_px": petals_px, "pearl": pr, "stamens": keep}, open(WORK + "/relief_blossom.json", "w"))

# ------------------------------------------------------------------ previews (x4 of the reference = S/2 downsample)
def down(A, f):
    h, w = A.shape[:2]
    return A[:h - h % f, :w - w % f].reshape(h // f, f, w // f, f, *A.shape[2:]).mean((1, 3))
gy, gx = np.gradient(G.gauss(H, 0.5), 1.0 / S * K)
nx_, ny_ = -gx, gy
nz_ = np.ones_like(H)
nn = np.sqrt(nx_ ** 2 + ny_ ** 2 + nz_ ** 2)
Ld = np.array([-0.5, 0.55, 0.67]); Ld /= np.linalg.norm(Ld)
shade = np.clip((nx_ * Ld[0] + ny_ * Ld[1] + nz_ * Ld[2]) / nn, 0, 1)
pal = np.array([[0.10, 0.11, 0.13], [0.72, 0.72, 0.74], [0.05, 0.06, 0.09], [0.93, 0.93, 0.96]])
alb = pal[CLS]
img = alb * (0.25 + 0.9 * shade[..., None])
refc = ref[R0:R1, C0:C1]
r4 = tp_img.resize(refc, 4, kind='linear')
i4 = down(img, 2)
h4 = down(np.repeat((0.15 + 0.85 * shade)[..., None], 3, 2), 2)
gap = np.ones((r4.shape[0], 10, 3))
tp_img.save(WORK + "/relief_preview.png", np.concatenate([r4, gap, i4, gap, h4], 1))
# class-boundary overlay on the reference (x6): what was traced where
V = 6
big = tp_img.resize(refc, V, kind='linear')
cl6 = CLS[::max(S // V, 1)] if False else None
from_idx_r = ((np.arange(big.shape[0]) + 0.5) / V * S).astype(int).clip(0, NR - 1)
from_idx_c = ((np.arange(big.shape[1]) + 0.5) / V * S).astype(int).clip(0, NC - 1)
cl6 = CLS[from_idx_r][:, from_idx_c]
e6 = (np.diff(cl6, axis=0, prepend=cl6[:1]) != 0) | (np.diff(cl6, axis=1, prepend=cl6[:, :1]) != 0)
colr = np.array([[0.2, 1.0, 0.2], [1.0, 0.9, 0.1], [1.0, 0.2, 1.0], [0.1, 0.9, 1.0]])
big[e6] = colr[np.maximum(cl6, np.roll(cl6, 1, 0))[e6]]
tp_img.save(WORK + "/relief_overlay_x6.png", big)
print("saved relief_preview", flush=True)
