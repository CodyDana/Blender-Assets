# Bevel-band measurement: inward edge-normal profiles of luminance L and warmth (R-B) from each fitted edge.
# A band is a strip that starts at the silhouette and ends at a step to the face colour; reported per edge.
import sys, json, math
sys.path.insert(0, "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/contour/scripts")
from common import *

px = np.load(BASE + "/manji_pixels.npy"); H, W = px.shape[:2]
L = px @ np.array([0.2126, 0.7152, 0.0722], np.float32)
Wm = (px[:, :, 0] - px[:, :, 2]).astype(np.float32)
st = np.load(BASE + "/fit_state.npy", allow_pickle=True).item()
m = np.load(BASE + "/mask_final.npy")
SPAN = st["SPAN"]
ts = np.arange(0, 80.01, 0.5)
sig = 1.2; dt = 0.5; r = int(4 * sig / dt); kk = np.arange(-r, r + 1) * dt
gk = -kk * np.exp(-0.5 * (kk / sig) ** 2); gk /= np.sum(np.abs(gk) * np.abs(kk))
res = {}
samples_out = {}
for name, e in st["edges"].items():
    curved = name.endswith("hook_back")
    P0, P1 = e["P0"], e["P1"]
    n_s = int(np.hypot(*(P1 - P0)) // 6)
    rows = []
    for k in range(n_s + 1):
        f = k / max(n_s, 1)
        if curved:
            a0 = math.atan2(P0[1] - e["c"][1], P0[0] - e["c"][0]); a1 = math.atan2(P1[1] - e["c"][1], P1[0] - e["c"][0])
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            ang = a0 + f * da
            q = e["c"] + e["R"] * np.array([math.cos(ang), math.sin(ang)])
            nin = -np.array([math.cos(ang), math.sin(ang)])          # toward the circle centre
        else:
            q = e["p"] + ((P0 + f * (P1 - P0)) - e["p"]) @ e["d"] * e["d"]
            nin = np.array([-e["d"][1], e["d"][0]])
        # inward = into the piece
        probe = q + 8 * nin
        if not m[int(round(np.clip(probe[1], 0, H - 1))), int(round(np.clip(probe[0], 0, W - 1)))]:
            nin = -nin
        # need at least 90 px of metal along the inward normal
        pp = q[None, :] + np.arange(3, 90)[:, None] * nin[None, :]
        inside = m[np.clip(np.round(pp[:, 1]).astype(int), 0, H - 1), np.clip(np.round(pp[:, 0]).astype(int), 0, W - 1)]
        if inside.mean() < 0.98:
            continue
        tg = np.array([-nin[1], nin[0]])
        lp = np.zeros(len(ts)); wp = np.zeros(len(ts))
        for dtan in np.arange(-4, 4.01, 1.0):
            X = q[0] + dtan * tg[0] + ts * nin[0]; Y = q[1] + dtan * tg[1] + ts * nin[1]
            lp += bilinear(L, X, Y); wp += bilinear(Wm, X, Y)
        lp /= 9; wp /= 9
        rows.append((q, nin, lp, wp))
    if not rows:
        res[name] = dict(n=0); continue
    LP = np.array([r_[2] for r_ in rows]); WP = np.array([r_[3] for r_ in rows])
    tb_list = []; dl_list = []; dw_list = []
    for lp, wp in zip(LP, WP):
        gl = np.convolve(lp, gk[::-1], mode="same") / dt; gw = np.convolve(wp, gk[::-1], mode="same") / dt
        score = np.abs(gl) + 1.5 * np.abs(gw)
        win = (ts >= 5) & (ts <= 50)
        i = int(np.argmax(np.where(win, score, -1))); tb = ts[i]
        band = (ts >= 2) & (ts <= tb - 2); face = (ts >= tb + 2) & (ts <= tb + 18)
        dl = float(lp[band].mean() - lp[face].mean()) if band.any() else 0.0
        dw = float(wp[band].mean() - wp[face].mean()) if band.any() else 0.0
        tb_list.append(tb); dl_list.append(dl); dw_list.append(dw)
    tb_a = np.array(tb_list); dl_a = np.array(dl_list); dw_a = np.array(dw_list)
    has = (np.abs(dl_a) > 0.03) | (np.abs(dw_a) > 0.025)
    # mean profiles (for reporting)
    mean_L = LP.mean(0); mean_W = WP.mean(0)
    # band width from the mean profile: face level = median over t 45..75; the band is the strip next to the edge whose
    # excess over the face level decays to 25 % of its peak. Uses whichever channel shows the larger excess.
    def band_from_profile(p):
        face = float(np.median(p[(ts >= 45) & (ts <= 75)]))
        seg = (ts >= 1.5) & (ts <= 45)
        ex = p - face
        i_pk = int(np.argmax(np.abs(np.where(seg, ex, 0))))
        pk = ex[i_pk]
        if abs(pk) < 1e-6: return None, 0.0, face
        thr = 0.25 * pk
        k = i_pk
        while k < len(ts) - 1 and ((ex[k] > thr) if pk > 0 else (ex[k] < thr)): k += 1
        return float(ts[k]), float(pk), face
    wL, pkL, faceL = band_from_profile(mean_L); wW, pkW, faceW = band_from_profile(mean_W)
    use = "warm" if abs(pkW) * 1.6 > abs(pkL) else "L"
    per_sample = []
    for lp, wp in zip(LP, WP):
        f = float(np.median((wp if use == "warm" else lp)[(ts >= 45) & (ts <= 75)]))
        p = (wp if use == "warm" else lp)
        seg = (ts >= 1.5) & (ts <= 45); ex = p - f
        i_pk = int(np.argmax(np.abs(np.where(seg, ex, 0)))); pk = ex[i_pk]
        if abs(pk) < 1e-6: continue
        thr = 0.25 * pk; k = i_pk
        while k < len(ts) - 1 and ((ex[k] > thr) if pk > 0 else (ex[k] < thr)): k += 1
        per_sample.append(float(ts[k]))
    ps = np.array(per_sample)
    res[name] = dict(n=int(len(rows)), band_fraction=float(has.mean()),
                     band_width_px_median=float(np.median(tb_a[has])) if has.any() else None,
                     band_width_px_p25=float(np.percentile(tb_a[has], 25)) if has.any() else None,
                     band_width_px_p75=float(np.percentile(tb_a[has], 75)) if has.any() else None,
                     band_width_px_all_median=float(np.median(tb_a)),
                     band_minus_face_L_median=float(np.median(dl_a)), band_minus_face_warm_median=float(np.median(dw_a)),
                     band_decay_width_px=dict(L=wL, warm=wW, used=use, peak_excess_L=pkL, peak_excess_warm=pkW,
                                              face_L=faceL, face_warm=faceW,
                                              per_sample_median=float(np.median(ps)) if len(ps) else None,
                                              per_sample_p10=float(np.percentile(ps, 10)) if len(ps) else None,
                                              per_sample_p90=float(np.percentile(ps, 90)) if len(ps) else None,
                                              per_sample_sd=float(ps.std()) if len(ps) else None),
                     mean_profile_L_every2px=[round(float(v), 3) for v in mean_L[::4][:30]],
                     mean_profile_warm_every2px=[round(float(v), 3) for v in mean_W[::4][:30]])
    samples_out[name] = dict(q=[r_[0].tolist() for r_ in rows], nin=[r_[1].tolist() for r_ in rows], tb=tb_a.tolist(), has=has.tolist())
    rr = res[name]
    bd = rr["band_decay_width_px"]
    print(f"{name:20s} n={rr['n']:3d} | decay-band {bd['used']}: mean-prof {bd['L'] if bd['used']=='L' else bd['warm']} px, "
          f"per-sample med {bd['per_sample_median']} p10-p90 ({bd['per_sample_p10']},{bd['per_sample_p90']}) sd {None if bd['per_sample_sd'] is None else round(bd['per_sample_sd'],1)} "
          f"| peak excess L {bd['peak_excess_L']:+.3f} warm {bd['peak_excess_warm']:+.3f} | face L {bd['face_L']:.3f} warm {bd['face_warm']:.3f}")
    print("      L:", rr["mean_profile_L_every2px"][:20])
    print("      W:", rr["mean_profile_warm_every2px"][:20])
json.dump(res, open(BASE + "/bevel_raw.json", "w"), indent=1)
json.dump(samples_out, open(BASE + "/bevel_samples.json", "w"))
