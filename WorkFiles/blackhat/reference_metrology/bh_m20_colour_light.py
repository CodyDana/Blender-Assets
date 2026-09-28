"""Stage 20: region colour statistics, straw brightness vs azimuth, Lambert+ambient light fit, wear-patch map."""
import sys, os, numpy as np, json, colorsys
sys.path.insert(0, os.path.dirname(__file__)); from bh_lib import *; from bh_cam import *
c = load('bh_s07_joint.json')['2.6']; d = 2.6
H, e, f, u0, v0, roll = c['H'], np.radians(c['e_deg']), c['f'], c['u0'], c['v0'], np.radians(c['roll_deg'])
pr = lambda P: project(np.asarray(P, float), e, d, f, u0, v0, roll)
im = load_srgb(); lin = srgb_to_lin(im); Ll = lum(lin)
out = {}
def stats(name, sel_rgb_lin):
    a = sel_rgb_lin.reshape(-1, 3); l = a @ LW
    m = a.mean(0); chrom = m / m.sum(); s = lin_to_srgb(m)
    hsv = colorsys.rgb_to_hsv(*np.clip(s, 0, 1))
    r = dict(n=int(len(a)), mean_lin=np.round(m, 4).tolist(), mean_srgb=np.round(s, 3).tolist(),
             hex='#%02X%02X%02X' % tuple(int(round(v * 255)) for v in np.clip(s, 0, 1)),
             lum_lin_p10_50_90=np.round(np.percentile(l, [10, 50, 90]), 4).tolist(), lum_lin_mean=round(float(l.mean()), 4),
             chroma=np.round(chrom, 3).tolist(), hue_deg=round(hsv[0] * 360, 1), sat=round(hsv[1], 3))
    out[name] = r; print(name, r)
# cone-space region sampler
def cone_region(t0, t1, r0, r1, step=0.2):
    T, R = np.meshgrid(np.radians(np.arange(t0, t1, step)), np.arange(r0, r1, 0.004))
    uv = pr(np.stack([R * np.sin(T), -R * np.cos(T), H * (1 - R)], -1))
    return bilinear(lin, uv[..., 0], uv[..., 1]), uv
stats('straw_centre_bay', cone_region(-20, 5, 0.62, 0.90)[0])
stats('straw_left_bay_worn', cone_region(-52, -27, 0.60, 0.95)[0])
stats('straw_leftmost_bay', cone_region(-80, -58, 0.55, 0.92)[0])
stats('straw_right_bay', cone_region(62, 82, 0.55, 0.90)[0])
stats('straw_upper_front_above_band', cone_region(-20, 5, 0.16, 0.32)[0])
stats('rim_tube_front', lin[414:429, 270:382])
stats('lashing_front', lin[414:430, 388:401])
stats('band_wide_near_knot', cone_region(12, 32, 0.43, 0.48)[0])
stats('band_thin_left', cone_region(-80, -30, 0.352, 0.366, 0.1)[0])
stats('tailA_below_rim', lin[430:470, 557:576])
stats('tailB_below_rim', lin[404:432, 600:626])
stats('crown_cap_top', lin[147:158, 318:352])
stats('all_hat_pixels', lin[Ll < srgb_to_lin(0.58)])
# ---- straw brightness vs azimuth (p30 and p50 over rho 0.55..0.93, 4-deg bins, rib columns excluded)
S = np.load(os.path.join(D, 'bh_cone_theta_rho.npy')); th = np.arange(-100, 100.001, 0.1); rho = np.arange(0.10, 1.001, 0.0025)
Slin = srgb_to_lin(S)
ribs = [-82, -54.5, -23.5, 7.6, 30, 58, 85]
prof = []
for t in range(-92, 93, 4):
    if 18 <= t <= 70: continue      # tails/knot region
    cs = (th >= t - 2) & (th < t + 2) & np.all([np.abs(th - r) > 1.5 for r in ribs], axis=0)
    rs = (rho >= 0.55) & (rho <= 0.93)
    v = Slin[np.ix_(rs, cs)].ravel()
    prof.append((t, float(np.percentile(v, 30)), float(np.percentile(v, 50)), float(np.percentile(v, 90))))
print('straw lin lum vs theta (t, p30, p50, p90):', [(a, round(b, 4), round(cc, 4), round(dd, 4)) for a, b, cc, dd in prof])
out['straw_theta_profile'] = prof
# Lambert fit on p30: I = amb + k*max(0, n.l), n = cone normal in camera-independent world coords
tt = np.radians([p[0] for p in prof]); I = np.array([p[1] for p in prof])
n = np.stack([H * np.sin(tt), -H * np.cos(tt), np.ones_like(tt)], -1) / np.sqrt(1 + H * H)
best = None
for az in range(-180, 180, 3):
    for el in range(0, 91, 3):
        a, b = np.radians(az), np.radians(el)
        l = np.array([np.sin(a) * np.cos(b), -np.cos(a) * np.cos(b), np.sin(b)])   # az 0 = toward camera side, + = image right
        s = np.maximum(0, n @ l); A = np.stack([np.ones_like(s), s], -1)
        coef, *_ = np.linalg.lstsq(A, I, rcond=None)
        if coef[1] < 0: continue
        r = I - A @ coef; sse = float(r @ r)
        if best is None or sse < best[0]: best = (sse, az, el, coef.tolist())
sse, az, el, coef = best
r2 = 1 - sse / float(((I - I.mean()) ** 2).sum())
print('light fit (az deg from camera side, + right; el deg):', az, el, 'amb, k', np.round(coef, 4), 'R2', round(r2, 3))
out['light_fit'] = dict(az_deg=az, el_deg=el, amb=coef[0], k=coef[1], R2=r2)
dump('bh_s20_colour_light.json', out)
