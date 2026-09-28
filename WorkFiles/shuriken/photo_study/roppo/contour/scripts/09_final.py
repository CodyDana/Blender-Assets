# Final method-B measurement: shadow-corrected contour, primitive fits, all measurements -> final.pkl (+ printout).
import sys, os, json, pickle
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from util import *
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
seg = np.load(os.path.join(OUT, "seg.npz"))
Hh, Ww = seg["L"].shape
cz = np.load(os.path.join(OUT, "contours.npz"))
outer_raw, hole_raw = cz["outer"], cz["hole"]
SH = pickle.load(open(os.path.join(OUT, "shadow.pkl"), "rb"))
sdir = np.array([np.cos(np.radians(SH["shadow_dir_deg"])), np.sin(np.radians(SH["shadow_dir_deg"]))]); Ls = SH["Ls"]
n_out = len(outer_raw)
onborder = outer_raw[:, 1] >= Hh - 1


def normals(P, win=5):
    t = np.roll(P, -win, 0) - np.roll(P, win, 0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    return np.c_[t[:, 1], -t[:, 0]]  # outward for a clockwise (y-down) trace of a region


N_out = normals(outer_raw)
N_hole_mat = -normals(hole_raw)  # material's outward normal on the hole wall (points into the hole)


def shadow_off(N):
    return -Ls * np.clip(N @ sdir, 0, None)


PIX = 0.5  # traced pixel centres sit ~0.5 px inside the region they belong to
outer_cor = outer_raw + (PIX + shadow_off(N_out))[:, None] * N_out
# hole-region boundary pixels sit 0.5 px inside the hole; cast shadow pushed the boundary INTO the hole by |off|.
hole_cor = hole_raw + (PIX - shadow_off(N_hole_mat))[:, None] * (-N_hole_mat)


def cidx(a_, b_):
    return np.arange(a_, b_ + 1) if b_ >= a_ else np.r_[np.arange(a_, n_out), np.arange(0, b_ + 1)]


def analyse(outer, hole):
    R = {}
    hf = fit_circle(hole)
    C0 = np.array([hf["cx"], hf["cy"]])
    r = np.hypot(*(outer - C0).T)
    k = 7
    rs = np.convolve(np.r_[r[-k:], r, r[:k]], np.ones(2 * k + 1) / (2 * k + 1), 'valid')
    w = 150
    peaks = [i for i in range(n_out) if rs[i] == max(rs[(i + j) % n_out] for j in range(-w, w + 1)) and rs[i] > np.percentile(rs, 80)]
    mins = sorted(i for i in range(n_out) if rs[i] == min(rs[(i + j) % n_out] for j in range(-w, w + 1)))
    assert len(peaks) == 6 and len(mins) == 6
    Rh0 = float(np.median(r[mins]))
    pts = []
    for t in peaks:
        before = max([m for m in mins if m < t], default=mins[-1]); after = min([m for m in mins if m > t], default=mins[0])
        p = dict(tip_idx=int(t))
        for nm, idx in (("A", cidx(before, t)), ("B", cidx(t, after))):
            rr = r[idx]; rtip = r[t]
            sel = idx[(rr > Rh0 + 0.15 * (rtip - Rh0)) & (rr < Rh0 + 0.92 * (rtip - Rh0)) & ~onborder[idx]]
            cen, dv, rms, mx = fit_line(outer[sel])
            if np.dot(outer[t] - cen, dv) < 0: dv = -dv
            p[nm] = dict(sel=sel, cen=cen, dir=dv, rms=rms, maxres=mx, all_idx=idx, n=int(len(sel)))
        p["apex"] = line_intersect(p["A"]["cen"], p["A"]["dir"], p["B"]["cen"], p["B"]["dir"])
        p["angle"] = float(np.degrees(np.arccos(np.clip(np.dot(p["A"]["dir"], p["B"]["dir"]), -1, 1))))
        bis = -(p["A"]["dir"] + p["B"]["dir"]); bis /= np.linalg.norm(bis); p["bis"] = bis
        for nm in ("A", "B"):
            dv = p[nm]["dir"]; nv = np.array([-dv[1], dv[0]])
            if np.dot(p[nm]["cen"] - (p["apex"] + np.dot(p[nm]["cen"] - p["apex"], bis) * bis), nv) < 0: nv = -nv
            p[nm]["nrm"] = nv
        pts.append(p)
    gaps = []
    for gi in range(6):
        pa, pb = pts[gi], pts[(gi + 1) % 6]
        idx = cidx(pa["tip_idx"], pb["tip_idx"])
        P = outer[idx]
        da = (P - pa["B"]["cen"]) @ pa["B"]["nrm"]; db = (P - pb["A"]["cen"]) @ pb["A"]["nrm"]
        sel = idx[(da > 12) & (db > 12) & (r[idx] < Rh0 + 40)]
        gaps.append(dict(between=(gi, (gi + 1) % 6), idx=sel, full_idx=idx))
    allarc = np.concatenate([g["idx"] for g in gaps])
    hub = fit_circle(outer[allarc]); CH = np.array([hub["cx"], hub["cy"]]); RH = hub["r"]
    for g in gaps:
        P = outer[g["idx"]]; rr = np.hypot(*(P - CH).T)
        g["r_mean"] = float(rr.mean()); g["r_sd"] = float(rr.std()); g["n"] = int(len(P))
        g["free_fit"] = fit_circle(P)
    for i, p in enumerate(pts):
        ax = p["apex"] - CH; ax /= np.linalg.norm(ax); p["axis"] = ax
        axp = np.array([-ax[1], ax[0]])
        idx_all = np.r_[p["A"]["all_idx"], p["B"]["all_idx"]]
        p["clipped"] = bool(onborder[idx_all].any())
        idx_all = idx_all[~onborder[idx_all]]
        proj = (outer[idx_all] - CH) @ ax
        j = idx_all[np.argmax(proj)]
        p["obs_tip"] = outer[j]; p["obs_tip_rho"] = float(proj.max())
        p["apex_rho"] = float((p["apex"] - CH) @ ax)
        roots = []
        for nm in ("A", "B"):
            cen, dv = p[nm]["cen"], p[nm]["dir"]
            b = np.dot(cen - CH, dv); cc = np.dot(cen - CH, cen - CH) - RH * RH
            disc = b * b - cc
            tr = -b + np.sqrt(disc) if disc > 0 else -b
            roots.append(cen + tr * dv); p[nm]["root"] = roots[-1]
        p["base_width"] = float(np.linalg.norm(roots[0] - roots[1]))
        angf = lambda v: np.arctan2(-(v - CH)[1], (v - CH)[0])
        p["base_angle_deg"] = float(abs(np.degrees(np.angle(np.exp(1j * (angf(roots[0]) - angf(roots[1])))))))
        p["axis_offset"] = float(abs(np.cross(p["bis"], CH - p["apex"])))
        p["axis_deg"] = float(np.degrees(np.arctan2(-ax[1], ax[0])))
        for nm in ("A", "B"):
            idx = p[nm]["all_idx"]; idx = idx[~onborder[idx]]
            P = outer[idx]; cen, dv, nv = p[nm]["cen"], p[nm]["dir"], p[nm]["nrm"]
            s = (P - cen) @ dv; res = (P - cen) @ nv
            rho = (P - CH) @ ax
            s_root = np.dot(p[nm]["root"] - cen, dv)
            m = (s > s_root + 5) & (rho < p["obs_tip_rho"] - 15)
            cq = np.polyfit(s[m], res[m], 2)
            Lseg = float(np.ptp(s[m]))
            p[nm]["sagitta_px"] = float(-cq[0] * (Lseg / 2) ** 2)  # + = mid-length bulges outward
            lin = np.polyfit(s[m], res[m], 1)
            p[nm]["full_rms"] = float(np.sqrt(((res[m] - np.polyval(lin, s[m])) ** 2).mean()))
            p[nm]["full_max"] = float(np.abs(res[m] - np.polyval(lin, s[m])).max())
            p[nm]["full_len"] = Lseg
            p[nm]["len_root_to_apex"] = float(np.linalg.norm(p["apex"] - p[nm]["root"]))
        g = p["apex_rho"] - p["obs_tip_rho"]; beta = np.radians(p["angle"] / 2)
        p["tip_gap"] = float(g); p["tip_radius_from_gap"] = float(g / (1 / np.sin(beta) - 1)) if g > 0 else 0.0
        cap = idx_all[proj > p["obs_tip_rho"] - 5]
        p["cap_circle_r"] = fit_circle(outer[cap])["r"] if (len(cap) >= 5 and not p["clipped"]) else None

        def width_at_rho(rr0):
            qa = []
            for nm in ("A", "B"):
                idx = p[nm]["all_idx"]; idx = idx[~onborder[idx]]
                P = outer[idx]; rho = (P - CH) @ ax; q = (P - CH) @ axp
                mm = np.abs(rho - rr0) < 1.0
                qa.append(np.median(q[mm]) if mm.any() else np.nan)
            return float(abs(qa[0] - qa[1]))
        p["width_near_tip"] = {str(d_): width_at_rho(p["obs_tip_rho"] - d_) for d_ in (2, 5, 10, 20, 40)}
        rr_lo, rr_hi = RH + 5, p["obs_tip_rho"] - 15
        gridr = np.arange(rr_lo, rr_hi, 2.0)
        ws = np.array([width_at_rho(g0) for g0 in gridr]); ok = ~np.isnan(ws)
        Lr = rr_hi - rr_lo

        def seg_angle(f0, f1):
            m = ok & (gridr >= rr_lo + f0 * Lr) & (gridr <= rr_lo + f1 * Lr)
            sl = np.polyfit(gridr[m], ws[m], 1)[0]
            return float(np.degrees(2 * np.arctan(abs(sl) / 2)))
        p["taper_inner40"] = seg_angle(0, 0.4); p["taper_mid"] = seg_angle(0.3, 0.7); p["taper_outer40"] = seg_angle(0.6, 1.0); p["taper_all"] = seg_angle(0, 1.0)
        p["width_linear_rms"] = float(np.sqrt(((ws[ok] - np.polyval(np.polyfit(gridr[ok], ws[ok], 1), gridr[ok])) ** 2).mean()))
        p["width_profile"] = dict(rho=gridr[ok].tolist(), w=ws[ok].tolist())
        p["width_at_hub_plus"] = {str(d_): width_at_rho(RH + d_) for d_ in (5, 10, 20)}
    gaps_unclipped = [p["tip_gap"] for p in pts if not p["clipped"]]
    for p in pts:
        p["obs_tip_rho_est"] = p["apex_rho"] - float(np.mean(gaps_unclipped)) if p["clipped"] else p["obs_tip_rho"]
    tip_pt = lambda p: CH + p["obs_tip_rho_est"] * p["axis"]
    pairs = [(i, i + 3) for i in range(3)]
    span_obs = {f"{i}-{j}": float(np.linalg.norm(tip_pt(pts[i]) - tip_pt(pts[j]))) for i, j in pairs}
    span_apex = {f"{i}-{j}": float(np.linalg.norm(pts[i]["apex"] - pts[j]["apex"])) for i, j in pairs}
    complete = [span_obs[f"{i}-{j}"] for i, j in pairs if not (pts[i]["clipped"] or pts[j]["clipped"])]
    span = float(np.mean(complete))
    tipc = fit_circle(np.array([tip_pt(p) for p in pts]))
    apexc = fit_circle(np.array([p["apex"] for p in pts]))
    # hole roundness: conic fit about fitted centre
    x, y = hole[:, 0] - hf["cx"], hole[:, 1] - hf["cy"]
    D = np.c_[x * x, x * y, y * y, x, y, np.ones_like(x)]
    _, _, vt = np.linalg.svd(D); A_, B_, C_, D_, E_, F_ = vt[-1]
    M = np.array([[A_, B_ / 2], [B_ / 2, C_]]); ev, evec = np.linalg.eigh(M)
    x0 = np.linalg.solve(2 * M, [-D_, -E_]); Fc = F_ + 0.5 * np.dot([D_, E_], x0)
    axes = np.sqrt(-Fc / ev)
    rres = np.hypot(*(hole - C0).T) - hf["r"]
    hang = np.degrees(np.arctan2(-(hole - C0)[:, 1], (hole - C0)[:, 0]))
    R.update(dict(hole=hf, hole_ellipse_axes=sorted(axes.tolist()), hole_ellipse_ratio=float(min(axes) / max(axes)),
                  hole_radial_ptp=float(np.ptp(rres)), hole_resid=rres, hole_ang=hang, hub=hub, gaps=gaps, pts=pts, span=span,
                  span_obs=span_obs, span_apex=span_apex, tip_circle=tipc, apex_circle=apexc, CH=CH, peaks=peaks, mins=mins))
    return R


RAW = analyse(outer_raw, hole_raw)
COR = analyse(outer_cor, hole_cor)
pickle.dump(dict(RAW=RAW, COR=COR, outer_cor=outer_cor, hole_cor=hole_cor, N_out=N_out, sdir=sdir, Ls=Ls),
            open(os.path.join(OUT, "final.pkl"), "wb"))


def summary(R, name):
    sp = R["span"]
    so = ", ".join(f"{k}:{v:.1f}" for k, v in R["span_obs"].items()); sa = ", ".join(f"{k}:{v:.1f}" for k, v in R["span_apex"].items())
    print(f"===== {name}: span(obs tips, complete pairs) {sp:.1f} px; obs pairs [{so}]; apex pairs [{sa}]")
    h = R["hole"]; hb = R["hub"]
    print(f"hole c({h['cx']:.1f},{h['cy']:.1f}) r {h['r']:.2f} rms {h['rms']:.2f} max {h['maxres']:.2f} | D/span {2*h['r']/sp:.4f} | ellipse axes {np.round(R['hole_ellipse_axes'],2)} ratio {R['hole_ellipse_ratio']:.4f} radial p-p {R['hole_radial_ptp']:.2f}")
    print(f"hub  c({hb['cx']:.1f},{hb['cy']:.1f}) r {hb['r']:.2f} rms {hb['rms']:.2f} max {hb['maxres']:.2f} | D/span {2*hb['r']/sp:.4f}")
    print("   arcs r about hub centre:", [(g['between'], round(g['r_mean'], 1), round(g['r_sd'], 2), g['n']) for g in R['gaps']])
    print("   arcs free-fit r:", [(g['between'], round(g['free_fit']['r'], 1)) for g in R['gaps']])
    tc = R["tip_circle"]; ac = R["apex_circle"]
    print(f"tip circle c({tc['cx']:.1f},{tc['cy']:.1f}) r {tc['r']:.1f} rms {tc['rms']:.2f}; apex circle c({ac['cx']:.1f},{ac['cy']:.1f}) r {ac['r']:.1f} rms {ac['rms']:.2f}")
    print(f"centre offsets: hole-hub {np.hypot(h['cx']-hb['cx'], h['cy']-hb['cy']):.2f} px, tipcircle-hub {np.hypot(tc['cx']-hb['cx'], tc['cy']-hb['cy']):.2f} px, hole-tipcircle {np.hypot(h['cx']-tc['cx'], h['cy']-tc['cy']):.2f}")
    for i, p in enumerate(R["pts"]):
        print(f" pt{i} axis {p['axis_deg']:7.2f} angle {p['angle']:.2f} base_w {p['base_width']:.1f} ({p['base_width']/sp:.4f}) base_ang {p['base_angle_deg']:.2f} obs_rho {p['obs_tip_rho_est']:.1f} apex_rho {p['apex_rho']:.1f} gap {p['tip_gap']:.1f} rtip_gap {p['tip_radius_from_gap']:.1f} cap_r {p['cap_circle_r']} clipped {p['clipped']} axis_off {p['axis_offset']:.2f}")
        print(f"      lineA n{p['A']['n']} rms {p['A']['rms']:.2f} max {p['A']['maxres']:.2f} sag {p['A']['sagitta_px']:+.2f} fullrms {p['A']['full_rms']:.2f} fullmax {p['A']['full_max']:.2f} len {p['A']['full_len']:.0f} | lineB n{p['B']['n']} rms {p['B']['rms']:.2f} max {p['B']['maxres']:.2f} sag {p['B']['sagitta_px']:+.2f} fullrms {p['B']['full_rms']:.2f} fullmax {p['B']['full_max']:.2f} len {p['B']['full_len']:.0f}")
        print(f"      taper inner40 {p['taper_inner40']:.2f} mid {p['taper_mid']:.2f} outer40 {p['taper_outer40']:.2f} all {p['taper_all']:.2f} width lin rms {p['width_linear_rms']:.2f} near_tip {  {k: round(v,1) for k,v in p['width_near_tip'].items()} } at_hub+ { {k: round(v,1) for k,v in p['width_at_hub_plus'].items()} }")


summary(RAW, "RAW (Otsu mask boundary)")
summary(COR, "SHADOW-CORRECTED")
