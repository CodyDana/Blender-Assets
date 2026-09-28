"""BlackCloak v2 fabric maps: tileable, true-scale, procedural (numpy on a periodic domain, so every map tiles exactly).

Look target (References/BlackCloak/blackcloak.png, a product shot; no pixels are copied from it): matte slubby
linen/wool, irregular isotropic thick-thin slub + heather mottling at 1-4 cm, fine fibre noise, no directional weave,
a few thicker slub threads, charcoal-black, very slightly warm.

Writes (Exports/Garments/BlackCloak_MH_v2/Textures/):
  T_BlackCloakV2_Cloth_BC.png        8-bit sRGB RGB
  T_BlackCloakV2_Cloth_ORM.png       8-bit linear RGB  (R cavity AO, G roughness, B metal 0)
  T_BlackCloakV2_Cloth_N.png         8-bit linear RGB  DirectX (green down); sign-tested
  T_BlackCloakV2_Cloth_Detail16.png  16-bit linear grey, full range (pack convention, MATERIAL_PLAN 5.1 step 3-4)
  T_BlackCloakV2_Fray_BCA.png        8-bit RGBA (RGB sRGB, A linear coverage) edge-fray strip, tiles along U
and T_BlackCloakV2_maps.json (every parameter, the recolour constants, sha256 of each file, mip statistics).

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python make_fabric_maps.py -- \
        [--median 34] [--gain 1.0] [--out <dir>] [--seed 20260927]
"""
import sys, os, json, math, time, hashlib, argparse
from pathlib import Path

sys.dont_write_bytecode = True
import numpy as np

PROJECT = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(PROJECT / "Scripts/unreal/materials/maps"))
import recolour_common as rc  # noqa: E402  (read-only use: sRGB maths, PNG writer, pack fabric constants)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--median", type=float, default=32.0, help="BC median luminance target, 8-bit sRGB")
ap.add_argument("--gain", type=float, default=1.3, help="global multiplier on every albedo log-contrast term")
ap.add_argument("--out", default=str(PROJECT / "Exports/Garments/BlackCloak_MH_v2/Textures"))
ap.add_argument("--seed", type=int, default=20260927)
ap.add_argument("--size", type=int, default=2048)
ap.add_argument("--set", action="append", default=[], help="key=json override of a look parameter")
A = ap.parse_args(argv)

N = A.size
TILE_M = 0.45                      # metres per tile (UV 0..1)
TEX_MM = TILE_M * 1000.0 / N       # mm per texel (0.2197 at 2048)
HUE = np.array([1.030, 1.000, 0.972])   # linear rgb ratios; photo garment mean R/G 1.026, R/B 1.036
OUT = Path(A.out)
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(A.seed)
t0 = time.time()


def log(m):
    print(f"[fabric_v2 {time.time() - t0:6.1f}s] {m}", flush=True)


# ------------------------------------------------------------------ periodic helpers
fy = np.fft.fftfreq(N)[:, None]
fx = np.fft.fftfreq(N)[None, :]
FR = np.hypot(fx, fy)                                  # cycles per texel


def band(lo_mm, hi_mm, soft=0.35):
    """Isotropic periodic noise with power between wavelengths lo..hi mm (smooth log-gaussian edges), std 1."""
    w = rng.standard_normal((N, N))
    F = np.fft.fft2(w)
    f_hi = TEX_MM / lo_mm                              # cycles per texel at the short wavelength
    f_lo = TEX_MM / hi_mm
    lf = np.log(np.maximum(FR, 1e-9))
    filt = np.exp(-0.5 * np.maximum(0, np.log(f_lo) - lf) ** 2 / soft ** 2) * \
        np.exp(-0.5 * np.maximum(0, lf - np.log(f_hi)) ** 2 / soft ** 2)
    filt[0, 0] = 0
    r = np.real(np.fft.ifft2(F * filt))
    return r / r.std()


def blur_periodic(a, sigma_px):
    F = np.fft.fft2(a)
    g = np.exp(-2 * (math.pi * sigma_px) ** 2 * FR ** 2)
    return np.real(np.fft.ifft2(F * g))


def stamp(field, cx, cy, half_w, half_h, fn):
    """Evaluate fn(dx, dy) on a wrapped box around (cx, cy) and add it into field (periodic)."""
    xs = np.arange(int(cx - half_w), int(cx + half_w) + 1)
    ys = np.arange(int(cy - half_h), int(cy + half_h) + 1)
    DX = xs[None, :] - cx
    DY = ys[:, None] - cy
    v = fn(DX.astype(np.float64), DY.astype(np.float64))
    np.add.at(field, (np.mod(ys, N)[:, None], np.mod(xs, N)[None, :]), v)


# ------------------------------------------------------------------ components
P = {  # every look parameter (albedo terms are log-luminance std; height in mm)
    "tile_m": TILE_M, "size": N, "texel_mm": TEX_MM, "seed": A.seed, "gain": A.gain,
    # tuned 2026-09-27 (rounds r1-r9, WorkFiles/BlackCloak_MH_v2/surface/logs): rendered at the photo's 2.73 mm/px in
    # the calibrated studio these give the photo's flat-patch contrast per band (5-10 / 10-20 / 20-45 mm)
    "mottle_10_45mm_logstd": 0.060, "grain_3_10mm_logstd": 0.180, "fibre_0p6_3mm_logstd": 0.120,
    "micro_0p25_0p6mm_logstd": 0.060, "mottle_band_mm": [25, 80], "mottle_soft": 0.25,
    "dash_count": 2600, "dash_len_mm": [6, 28], "dash_width_mm": [1.0, 2.6], "dash_logamp": [0.15, 0.40],
    "dash_dark_frac": 0.4,
    "slub_threads": 26, "slub_len_mm": [30, 65], "slub_width_mm": [1.0, 1.7], "slub_logamp": [0.20, 0.38],
    "slub_axis_jitter_deg": 7.0, "neps": 700, "nep_logamp": [-0.35, 0.35],
    "weave_pitch_texels": 4, "weave_height_mm": 0.025, "weave_logamp": 0.025,
    "height_mm": {"mottle": 0.05, "grain": 0.035, "fibre": 0.030, "slub_peak": 0.16},
    "rough": {"base": 0.865, "slub": -0.07, "fibre": 0.022, "mottle": 0.018, "min": 0.74, "max": 0.93},
    "ao_cavity": {"blur_mm": 0.9, "k_per_mm": 1.4, "floor": 0.86},
}
for kv in A.set:
    k_, v_ = kv.split("=", 1)
    P[k_] = json.loads(v_)
log("noise bands")
mottle = band(*P["mottle_band_mm"], soft=P["mottle_soft"])   # broad edges: heather, not a cellular pattern
grain = band(3, 10)
fibre = band(0.6, 3)
micro = band(0.25, 0.6)

# slub: yarn is thick-thin along its length, so slub shows as short dashes along the two weave axes (half warp, half
# weft: isotropic in aggregate), lighter where the yarn is thick, darker where thin; plus a few long thick threads
def draw_threads(field, count, len_mm, width_mm, logamp, dark_frac, jitter_deg):
    for i in range(count):
        cx, cy = rng.uniform(0, N, 2)
        ang = (0.0 if i % 2 == 0 else math.pi / 2) + math.radians(rng.normal(0, jitter_deg))
        L = rng.uniform(*len_mm) / TEX_MM
        wd = rng.uniform(*width_mm) / TEX_MM
        amp = rng.uniform(*logamp) * (-0.8 if rng.uniform() < dark_frac else 1.0)
        wav_a, wav_l, ph = rng.uniform(0.1, 0.5) * wd, rng.uniform(8, 20) / TEX_MM, rng.uniform(0, 6.28)
        tw = rng.uniform(1.0, 1.6) / TEX_MM                 # twist period
        ca, sa = math.cos(ang), math.sin(ang)
        hb = L / 2 + 3 * wd

        def fn(dx, dy, ca=ca, sa=sa, L=L, wd=wd, amp=amp, wav_a=wav_a, wav_l=wav_l, ph=ph, tw=tw):
            s_ = dx * ca + dy * sa
            t = -dx * sa + dy * ca
            u = np.clip(s_ / L + 0.5, 0, 1)
            prof = np.sin(math.pi * u) ** 0.8 * (np.abs(s_) < L / 2)
            wloc = wd * (0.55 + 0.45 * prof)                # thick in the middle, thinning to the thread
            t2 = t - wav_a * np.sin(2 * math.pi * s_ / wav_l + ph)
            across = np.exp(-(t2 / (0.5 * wloc)) ** 2)
            twist = 0.8 + 0.2 * np.cos(2 * math.pi * (s_ + 0.6 * t2) / tw)
            return amp * prof * across * twist
        stamp(field, cx, cy, abs(ca) * hb + abs(sa) * 3 * wd + 2, abs(sa) * hb + abs(ca) * 3 * wd + 2, fn)


log("slub dashes + threads")
slub = np.zeros((N, N))
draw_threads(slub, P["dash_count"], P["dash_len_mm"], P["dash_width_mm"], P["dash_logamp"], P["dash_dark_frac"],
             P["slub_axis_jitter_deg"])
draw_threads(slub, P["slub_threads"], P["slub_len_mm"], P["slub_width_mm"], P["slub_logamp"], 0.0,
             P["slub_axis_jitter_deg"])

log("neps")
nep = np.zeros((N, N))
for i in range(P["neps"]):
    cx, cy = rng.uniform(0, N, 2)
    r = rng.uniform(0.25, 0.8) / TEX_MM
    a = rng.uniform(*P["nep_logamp"])
    stamp(nep, cx, cy, 3 * r + 1, 3 * r + 1, lambda dx, dy, r=r, a=a: a * np.exp(-(dx * dx + dy * dy) / (r * r)))

# fine plain weave (height only + a trace in albedo), pitch 4 texels = 0.88 mm: averages away exactly by mip 2, so it
# cannot alias into the directional streaks of the old map; its phase wanders with the grain so it is not a grid
log("weave")
p = P["weave_pitch_texels"]
Y_, X_ = np.mgrid[0:N, 0:N].astype(np.float64)
ph1 = 0.9 * band(4, 20)
ph2 = 0.9 * band(4, 20)
warp = np.cos(2 * math.pi * X_ / p + ph1)
weft = np.cos(2 * math.pi * Y_ / p + ph2)
weave = 0.5 * (np.maximum(warp, 0) ** 0.6 * (weft < 0.2) + np.maximum(weft, 0) ** 0.6 * (warp < 0.2))
weave = weave - weave.mean()
weave /= max(weave.std(), 1e-9)
del ph1, ph2, warp, weft, X_, Y_

# ------------------------------------------------------------------ albedo luminance multiple n (mean 1)
g = A.gain
logY = g * (P["mottle_10_45mm_logstd"] * mottle + P["grain_3_10mm_logstd"] * grain + P["fibre_0p6_3mm_logstd"] * fibre
            + P["micro_0p25_0p6mm_logstd"] * micro + slub + nep + P["weave_logamp"] * weave)
Y = np.exp(logY)
n = Y / Y.mean()

# colour: scale so the stored BC median luminance lands on --median (8-bit sRGB)
target_med_lin = float(rc.s2l(A.median / 255.0))
lum_hue = float(HUE @ rc.LUM)
colour = HUE / lum_hue * target_med_lin / float(np.median(n))
albedo = colour[None, None, :] * n[..., None]
bc8 = rc.q8_srgb(albedo)
log(f"BC median lum8 {np.median(rc.l2s(albedo @ rc.LUM) * 255):.2f}  colour {colour}")

# ------------------------------------------------------------------ height, normal (DirectX), ORM
hm = P["height_mm"]
H = (hm["mottle"] * mottle + hm["grain"] * grain + hm["fibre"] * fibre + P["weave_height_mm"] * weave
     + hm["slub_peak"] * slub / max(P["slub_logamp"][1], 1e-6) + 0.02 * nep / 0.35)
# gradient in mm/mm with periodic central differences; image row 0 is the TOP of the texture (V = 1)
dHdx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) / (2 * TEX_MM)
dHdy_down = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) / (2 * TEX_MM)     # d/d(row) = -d/dV
dHdv = -dHdy_down
nx_, ny_gl, nz_ = -dHdx, -dHdv, np.ones_like(H)                        # OpenGL tangent space (+V up)
ln = np.sqrt(nx_ ** 2 + ny_gl ** 2 + 1)
nx_, ny_gl, nz_ = nx_ / ln, ny_gl / ln, nz_ / ln
ny_dx = -ny_gl                                                         # DirectX: green down
nrm8 = np.stack([np.rint((nx_ * 0.5 + 0.5) * 255), np.rint((ny_dx * 0.5 + 0.5) * 255),
                 np.rint((nz_ * 0.5 + 0.5) * 255)], -1).astype(np.int16)
tilt = np.degrees(np.arccos(np.clip(nz_, -1, 1)))

rg = P["rough"]
slub_n = slub / max(P["slub_logamp"][1], 1e-6)
rough = np.clip(rg["base"] + rg["slub"] * np.clip(slub_n, 0, 1) + rg["fibre"] * fibre + rg["mottle"] * mottle,
                rg["min"], rg["max"])
ac = P["ao_cavity"]
cav = np.maximum(blur_periodic(H, ac["blur_mm"] / TEX_MM) - H, 0)
ao = np.clip(1 - ac["k_per_mm"] * cav, ac["floor"], 1)
orm8 = np.stack([np.rint(ao * 255), np.rint(rough * 255), np.zeros_like(ao)], -1).astype(np.int16)

# ------------------------------------------------------------------ Detail16 (pack convention) + recolour constants
Ylum = n                                                               # grey: luminance multiple == n
ylo, yhi, ymean = float(Ylum.min()), float(Ylum.max()), float(Ylum.mean())
d = (Ylum - ylo) / (yhi - ylo)
d16 = rc.q16_linear(d)
dq = d16 / 65535.0
bias, scale = ylo / ymean, (yhi - ylo) / ymean
colour_mean = colour * ymean                                           # Colour = mean linear rgb
n_model = bias + scale * dq
k = rc.fabric_constants(n_model)
model8 = rc.q8_srgb(np.clip(colour_mean[None, None, :] * n_model[..., None], 0, 1))
contract = rc.level_diff_stats(model8, bc8)
mips_contract = []
bc_lin_q = rc.s2l(bc8 / 255.0)
for f in rc.mip_factors(N, N)[:8]:
    bcm = rc.q8_srgb(rc.block_mean(bc_lin_q, f))
    dm = rc.q16_linear(rc.block_mean(dq, f)) / 65535.0
    mm = rc.q8_srgb(np.clip(colour_mean[None, None, :] * (bias + scale * dm)[..., None], 0, 1))
    mips_contract.append({"mip": len(mips_contract), **rc.level_diff_stats(mm, bcm)})
h_def = float(math.log(rc.ALBEDO_CEILING / colour_mean.max()) / math.log(k["highlight_ratio"]))
stress = rc.stress_fabric(n_model.ravel()[::7], k, {**rc.STRESS, **rc.REPORT_ONLY}, colour_mean)

# ------------------------------------------------------------------ fray strip (tiles along U; row 0 = cloth side)
log("fray strip")
FW, FH = N, 256                                                        # 0.45 m x 5.6 cm at the same texel size
fr_edge = np.zeros((FH, FW))
xs = np.arange(FW)
e1 = np.real(np.fft.ifft(np.fft.fft(rng.standard_normal(FW)) * np.exp(-(np.fft.fftfreq(FW) * FW / 30) ** 2)))
e2 = np.real(np.fft.ifft(np.fft.fft(rng.standard_normal(FW)) * np.exp(-(np.fft.fftfreq(FW) * FW / 400) ** 2)))
edge_row = 70 + 4 * e1 / e1.std() + 3 * e2 / e2.std()                 # ragged cut line, ~15 mm below the top
alpha = np.zeros((FH, FW))
rows = np.arange(FH)[:, None]
alpha += np.clip(edge_row[None, :] - rows + 0.5, 0, 1)                 # cloth body above the cut (soft 1-texel AA)
frng = np.random.default_rng(A.seed + 1)


def line_alpha(x0, y0, x1, y1, w, curve=0.0, taper=True):
    """Anti-aliased thread from (x0,y0) to (x1,y1) (x wraps), width w texels, optional sideways bow."""
    L = math.hypot(x1 - x0, y1 - y0)
    steps = max(int(L * 2), 2)
    out = []
    for i in range(steps + 1):
        t = i / steps
        bx = (y1 - y0) / max(L, 1e-6) * curve * math.sin(math.pi * t)
        by = -(x1 - x0) / max(L, 1e-6) * curve * math.sin(math.pi * t)
        out.append((x0 + (x1 - x0) * t + bx, y0 + (y1 - y0) * t + by, w * ((1 - 0.6 * t) if taper else 1)))
    for (x, y, ww) in out:
        r = int(math.ceil(ww + 1))
        for yy in range(int(y) - r, int(y) + r + 1):
            if yy < 0 or yy >= FH:
                continue
            for xx in range(int(x) - r, int(x) + r + 1):
                dd = math.hypot(xx - x, yy - y)
                a = np.clip(ww / 2 + 0.5 - dd, 0, 1)
                if a > 0:
                    xm = xx % FW
                    alpha[yy, xm] = max(alpha[yy, xm], a)


# short weft-thread fringe: every ~1.1 mm along the edge, 0.5-7 mm long, near-perpendicular
x = 0.0
nfringe = 0
while x < FW:
    x += frng.uniform(2.0, 5.0)                        # ~0.8 mm between loose weft ends
    L = frng.gamma(2.2, 1.4) / TEX_MM
    L = min(L, 8 / TEX_MM)
    ang = math.radians(frng.normal(0, 9))
    y0 = edge_row[int(x) % FW] - 1
    line_alpha(x, y0, x + L * math.sin(ang), y0 + L * math.cos(ang), frng.uniform(1.0, 1.6), curve=frng.normal(0, 1.2))
    nfringe += 1
# a few long loose threads (2-4 cm) that curl
nloose = 6
for i in range(nloose):
    xa = frng.uniform(0, FW)
    L = frng.uniform(20, 40) / TEX_MM
    L = min(L, FH - edge_row[int(xa) % FW] - 4)
    ang = math.radians(frng.normal(0, 22))
    y0 = edge_row[int(xa) % FW] - 1
    line_alpha(xa, y0, xa + L * math.sin(ang), y0 + L * math.cos(ang), 1.6, curve=frng.uniform(-14, 14), taper=False)
fray_n = n[:FH, :FW] * (1.0 + 0.10 * (1 - np.clip(edge_row[None, :] - rows, 0, 1)))  # fibre ends a touch lighter
fray_rgb = rc.q8_srgb(colour[None, None, :] * fray_n[..., None])
fray_a = np.rint(np.clip(alpha, 0, 1) * 255).astype(np.int16)
fray = np.concatenate([fray_rgb, fray_a[..., None]], -1)

# ------------------------------------------------------------------ write
files = {"BC": "T_BlackCloakV2_Cloth_BC.png", "ORM": "T_BlackCloakV2_Cloth_ORM.png", "N": "T_BlackCloakV2_Cloth_N.png",
         "Detail16": "T_BlackCloakV2_Cloth_Detail16.png", "Fray_BCA": "T_BlackCloakV2_Fray_BCA.png"}
rc.png_write(OUT / files["BC"], bc8, 8)
rc.png_write(OUT / files["ORM"], orm8, 8)
rc.png_write(OUT / files["N"], nrm8, 8)
rc.png_write(OUT / files["Detail16"], d16, 16)
rc.png_write(OUT / files["Fray_BCA"], fray, 8)

# ------------------------------------------------------------------ checks
# (1) normal sign test on the real map: correlate stored green with the height slope along V.
#     DirectX: G encodes -N_y(GL); a surface rising towards +V (image top) tilts its normal to -V, GL N_y < 0,
#     so DX green > 0.5  =>  corr(G_dx, dH/dV) must be POSITIVE; for OpenGL it would be negative.
g_dx = nrm8[..., 1] / 255.0 - 0.5
corr_g = float(np.corrcoef(g_dx.ravel()[::5], dHdv.ravel()[::5])[0, 1])
corr_r = float(np.corrcoef((nrm8[..., 0] / 255.0 - 0.5).ravel()[::5], dHdx.ravel()[::5])[0, 1])
# (2) synthetic dome sign test through the same code path: a bump in the middle of the image
yy, xx = np.mgrid[0:64, 0:64].astype(np.float64)
dome = np.exp(-((xx - 32) ** 2 + (yy - 32) ** 2) / 100.0)
ddv = -(np.roll(dome, -1, 0) - np.roll(dome, 1, 0)) / 2
ny_gl_d = -ddv / np.sqrt(1 + ddv ** 2)
g_dx_d = (-ny_gl_d) * 0.5 + 0.5
dome_test = {"texel_above_centre_row24_G": float(g_dx_d[24, 32]), "texel_below_centre_row40_G": float(g_dx_d[40, 32]),
             "rule": "DirectX: the upper flank of a bump (towards image top, +V) faces up in GL (+Y), so stored "
                     "green there is < 0.5 (green down)",
             "pass": bool(g_dx_d[24, 32] < 0.5 < g_dx_d[40, 32])}


def mip_stats():
    out = []
    bl = rc.s2l(bc8 / 255.0) @ rc.LUM
    nx = nrm8[..., 0] / 127.5 - 1
    ny = nrm8[..., 1] / 127.5 - 1
    nz = nrm8[..., 2] / 127.5 - 1
    for m in range(0, 8):
        f = 2 ** m
        L = rc.block_mean(bl, f)
        X, Yv, Z = rc.block_mean(nx, f), rc.block_mean(ny, f), rc.block_mean(nz, f)
        tl = np.degrees(np.arctan2(np.hypot(X, Yv), Z))
        texel = TEX_MM * f
        # slub/heather band (10-45 mm) amplitude visible at this mip: box-high-pass at ~45 mm
        hp = L - gauss_periodic(L, 45.0 / texel / 2.5)
        out.append({"mip": m, "size": L.shape[0], "texel_mm": round(texel, 3),
                    "bc_lum_std_over_mean": round(float(L.std() / L.mean()), 4),
                    "bc_lum_hp45mm_std_over_mean": round(float(hp.std() / L.mean()), 4),
                    "bc_lum_mean": round(float(L.mean()), 6),
                    "n_mean_tilt_deg": round(float(tl.mean()), 3),
                    "rough_mean": round(float(rc.block_mean(orm8[..., 1] / 255.0, f).mean()), 4),
                    "rough_std": round(float(rc.block_mean(orm8[..., 1] / 255.0, f).std()), 4)})
    return out


def gauss_periodic(a, sigma_px):
    n0, n1 = a.shape
    f2 = np.fft.fftfreq(n0)[:, None] ** 2 + np.fft.fftfreq(n1)[None, :] ** 2
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (math.pi * sigma_px) ** 2 * f2)))


mips = mip_stats()


def photo_scale_bands():
    """Albedo-only amplitudes at the product photo's scale (~2.73 mm/px): BC linear luminance box-averaged over
    12 x 12 texels (2.64 mm), 32 x 32 windows, the same radial bands as the photo probe (sv2_imgmetrics)."""
    f = 12
    bl = rc.s2l(bc8 / 255.0) @ rc.LUM
    n0 = (N // f) * f
    L = bl[:n0, :n0].reshape(n0 // f, f, n0 // f, f).mean((1, 3))
    mm = TEX_MM * f
    out = {"5.4_10": [], "10_20": [], "20_45": [], "v_over_h": [], "axes_over_diag": []}
    fy_ = np.fft.fftfreq(32)[:, None] * np.ones((1, 32))
    fx_ = np.ones((32, 1)) * np.fft.fftfreq(32)[None, :]
    fr_ = np.hypot(fx_, fy_)
    wl = np.where(fr_ > 0, mm / np.maximum(fr_, 1e-12), np.inf)
    ang = np.degrees(np.arctan2(np.abs(fy_), np.abs(fx_)))
    for y in range(0, L.shape[0] - 32, 32):
        for x in range(0, L.shape[1] - 32, 32):
            a = L[y:y + 32, x:x + 32]
            a = a / a.mean() - 1
            F = np.abs(np.fft.fft2(a)) ** 2 / 32 ** 4
            for key, (lo, hi) in {"5.4_10": (5.4, 10), "10_20": (10, 20), "20_45": (20, 45)}.items():
                out[key].append(float(np.sqrt(F[(wl >= lo) & (wl < hi)].sum())))
            sel = (wl >= 3) & (wl < 80)
            v, h, d = F[sel & (ang > 70)].sum(), F[sel & (ang < 20)].sum(), F[sel & (ang > 25) & (ang < 65)].sum()
            out["v_over_h"].append(float(v / max(h, 1e-30)))
            out["axes_over_diag"].append(float((v + h) / max(d, 1e-30)))
    return {k_: round(float(np.mean(v_)), 4) for k_, v_ in out.items()}


photo_bands = photo_scale_bands()
seam = {"BC_max_wrap_step_vs_interior": [float(np.abs(np.diff(bc8[..., 1].astype(float), axis=1)).mean()),
                                         float(np.abs(bc8[:, 0, 1].astype(float) - bc8[:, -1, 1]).mean())],
        "N_wrap_step_vs_interior": [float(np.abs(np.diff(nrm8[..., 0].astype(float), axis=1)).mean()),
                                    float(np.abs(nrm8[:, 0, 0].astype(float) - nrm8[:, -1, 0]).mean())]}
alpha_cov = []
for m in range(0, 6):
    f = 2 ** m
    a = rc.block_mean(np.clip(alpha, 0, 1)[:FH // f * f, :FW // f * f], f)
    alpha_cov.append({"mip": m, "coverage_at_0.5": round(float((a >= 0.5).mean()), 4), "mean_alpha": round(float(a.mean()), 4)})

rep = {
    "generator": "Scripts/garments/blackcloak_v2/make_fabric_maps.py", "date": time.strftime("%Y-%m-%d %H:%M"),
    "params": P, "hue_linear": HUE.tolist(), "median_target_srgb8": A.median,
    "tile": {"metres_per_tile": TILE_M, "texels": N, "mm_per_texel": TEX_MM,
             "uv_convention": "UV0 = pattern metres / 0.45 (1 UV unit = one 0.45 m tile); material UV Scale 1.0. If UVs "
                              "are authored in plain metres set UV Scale = 1/0.45 = 2.2222"},
    "stats": {
        "bc_median_lum_srgb8": float(np.median(rc.l2s(rc.s2l(bc8 / 255.0) @ rc.LUM) * 255)),
        "bc_median_rgb_srgb8": [float(np.median(bc8[..., c])) for c in range(3)],
        "bc_p1_p99_lum_srgb8": [float(v) for v in np.percentile(rc.l2s(rc.s2l(bc8 / 255.0) @ rc.LUM) * 255, [1, 99])],
        "bc_mean_linear_rgb": [float(v) for v in rc.s2l(bc8 / 255.0).reshape(-1, 3).mean(0)],
        "n_std": float(n.std()), "n_p1_p99": [float(v) for v in np.percentile(n, [1, 99])],
        "rough_mean": float(rough.mean()), "rough_p1_p99": [float(v) for v in np.percentile(rough, [1, 99])],
        "ao_mean": float(ao.mean()), "ao_min": float(ao.min()),
        "normal_tilt_mean_deg": float(tilt.mean()), "normal_tilt_p99_deg": float(np.percentile(tilt, 99)),
    },
    "normal_sign_test": {"format": "DirectX (green down)", "corr_G_vs_dH_dV_expect_positive": corr_g,
                         "corr_R_vs_dH_dU_expect_negative": corr_r, "dome": dome_test,
                         "pass": bool(corr_g > 0.5 and corr_r < -0.5 and dome_test["pass"])},
    "mips": mips,
    "albedo_bands_at_photo_scale_2p64mm": photo_bands,
    "tiling_seam": seam,
    "detail16": {"file": files["Detail16"], "convention": "d = (Y - Ylo)/(Yhi - Ylo) of the linear luminance multiple; "
                 "BaseColor = Colour x (Bias + Scale x d) (MATERIAL_PLAN 5.1, MF_TintDetail)",
                 "Colour_linear": colour_mean.tolist(), "Bias": bias, "Scale": scale,
                 "DetailMean": k["mean"], "DetailHighlightRatio": k["highlight_ratio"],
                 "DetailMomentsLow": k["moments_low"], "DetailMomentsHigh": k["moments_high"],
                 "H_default": h_def, "G_H1_pass": bool(h_def >= 1.0 and colour_mean.max() * k["n_max"] <= rc.KNEE),
                 "contract_model_vs_BC_levels": contract, "contract_every_mip": mips_contract,
                 "contract_pass": bool(contract["max"] <= 1 and max(m_["max"] for m_ in mips_contract) <= 1),
                 "recolour_stress_subsample7": {kk: {"pass": v["pass"], "clip_frac": v["clip_frac"],
                                                     "std_ratio_logL": v["std_ratio_logL"],
                                                     "dE00_mean_vs_target": v["dE00_mean_vs_target"]}
                                                for kk, v in stress.items()}},
    "fray": {"file": files["Fray_BCA"], "size": [FW, FH], "metres": [TILE_M, FH * TEX_MM / 1000],
             "layout": "row 0 (V=1) = cloth side, opaque down to a ragged cut ~15 mm from the top (+-3 mm), then "
                       "a weft fringe (~0.8 mm apart, 1-8 mm long) and %d long loose threads 2-4 cm; tiles along U" % nloose,
             "fringe_threads": nfringe, "alpha_coverage_by_mip": alpha_cov},
    "files": {},
}
for kk, fn in files.items():
    rep["files"][kk] = {"name": fn, "sha256": hashlib.sha256((OUT / fn).read_bytes()).hexdigest(),
                        "bytes": (OUT / fn).stat().st_size}
json.dump(rep, open(OUT / "T_BlackCloakV2_maps.json", "w"), indent=1)
log(json.dumps({"stats": rep["stats"], "normal": rep["normal_sign_test"]["pass"],
                "contract": rep["detail16"]["contract_pass"], "G_H1": rep["detail16"]["G_H1_pass"],
                "mips": [(m_["mip"], m_["bc_lum_std_over_mean"], m_["n_mean_tilt_deg"]) for m_ in mips], "photo_bands": photo_bands}))
