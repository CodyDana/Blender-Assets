"""fp_widen2 - LOCAL hidden widening of the fitted passes (final pass, maintainer).

The winder fitted each pass's WIDTH to the strip's VISIBLE width, so a pass whose neighbour
covers one of its edges was made only as wide as what shows (U1 4.8 mm, R_in 6 mm, R3 4.4 mm)
and stood up as a rope with both rolled edges showing - the "tangle of strands" every judge saw
at the whorl.  A real tape keeps its width and the neighbour covers part of it.

For every front-arc sample of every pass (W excepted: its narrow flat part and twisted section are
true widths), each side is extended outward in steps while the extension stays COVERED by a
stretch above the pass there (the original winding's stack, weaves applied), up to FLOOR frac D.
The extensions are held to the covered envelope (running minimum), smoothed, and refitted as the
pass's width / beta B-spline coefficients (the uncovered edge stays where the fit put it).

usage: python fp_widen2.py FLOOR_FRAC_D OUT_FIT_PY [SAFETY]
"""
import sys, time, json, types, re
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import smokebomb_wind as W
import importlib.util
SRC = sys.argv[4] if len(sys.argv) > 4 else r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/final_pass/orig_start/props_lib/smokebomb_wind_fit.py"
spec = importlib.util.spec_from_file_location("fit_src", SRC)
F0 = importlib.util.module_from_spec(spec); spec.loader.exec_module(F0)

SKIP = {"W"} | set(sys.argv[5].split(",") if len(sys.argv) > 5 else [])
floor = float(sys.argv[1]); out_py = sys.argv[2]
safety = float(sys.argv[3]) if len(sys.argv) > 3 else 0.9
t0 = time.time()
wd = W.reference_winding(F0)
g = wd.stack_grid(256)
print("winding", round(time.time() - t0, 1), "s", flush=True)
NSTEP = 16


def covered_ext(i_idx, side):
    """per sample: how far (rad) the tape can extend on ``side`` and stay under a higher stretch."""
    c, b, w = wd.c[i_idx], wd.b[i_idx], wd.w_eff()[i_idx]
    need = np.maximum(2 * floor - w, 0.0)        # full-width shortfall (rad), all on one side at most
    allowed = np.zeros(len(i_idx))
    alive = need > 0
    for j in range(1, NSTEP + 1):
        d = need * j / NSTEP
        a = side * (0.5 * w + d)
        p = W.normalize(np.cos(a)[:, None] * c + np.sin(a)[:, None] * b)
        ek = wd.effective_key(p, i_idx)
        cell = W._cube_index(p, g.n_face)
        K, S = g.keys[cell], g.samples[cell]
        cov = np.any((S >= 0) & (np.abs(S - i_idx[:, None]) > 3 * g.run_len) & (K > ek[:, None] + 1e-9), axis=1)
        alive &= cov
        allowed = np.where(alive, d, allowed)
    return allowed


def runmin(x, k):
    out = x.copy()
    for s in range(1, k + 1):
        out[s:] = np.minimum(out[s:], x[:-s]); out[:-s] = np.minimum(out[:-s], x[s:])
    return out


def smooth(x, k):
    ker = np.ones(2 * k + 1) / (2 * k + 1)
    p = np.pad(x, k, mode="edge")
    return np.convolve(p, ker, mode="valid")


newp, rep = [], {}
for p in F0.PASSES:
    q = dict(p)
    if p["name"] in SKIP:
        newp.append(q); continue
    k = wd.names.index(p["name"])
    idx = np.nonzero((wd.pass_idx == k) & ~np.isnan(wd.phi))[0]
    ph = wd.phi[idx]
    ext = {}
    for side in (+1, -1):
        e = covered_ext(idx, side)
        e = runmin(e, 15)                      # 3 deg each way: the envelope, no spikes
        e = np.minimum(smooth(e, 10), e)       # smooth, never past the covered envelope
        ext[side] = safety * e
    # both sides may extend; together at most the shortfall
    w = wd.w[idx]
    need = np.maximum(2 * floor - w, 0.0)
    tot = ext[1] + ext[-1]
    sc = np.where(tot > need, need / np.maximum(tot, 1e-12), 1.0)
    ep, em = ext[1] * sc, ext[-1] * sc
    ps = W.PassSpec(name=p["name"], shows=tuple(p["shows"]), n=tuple(p["n"]), e1=tuple(p["e1"]), phi_a=p["phi_a"],
                    phi_b=p["phi_b"], beta=tuple(p["beta"]), width=tuple(p["width"]), gather=tuple(p["gather"]))
    wfrac = ps._spl(p["width"], ph) + 0.5 * (ep + em)
    bdeg = ps._spl(p["beta"], ph) + np.degrees(0.5 * (ep - em))
    B = W.bspline_basis(ph, p["phi_a"], p["phi_b"], len(p["width"]))
    cw = np.linalg.lstsq(B, wfrac, rcond=None)[0]
    Bb = W.bspline_basis(ph, p["phi_a"], p["phi_b"], len(p["beta"]))
    cb = np.linalg.lstsq(Bb, bdeg, rcond=None)[0]
    q["width"] = tuple(round(float(x), 6) for x in cw)
    q["beta"] = tuple(round(float(x), 6) for x in cb)
    q["note"] = p["note"] + f" [final pass: hidden widening toward {floor} D]"
    rep[p["name"]] = dict(min_w_before=round(float(np.min(w) / 2), 4), min_w_after=round(float(np.min(wfrac)), 4),
                          mean_ext_left_mm=round(float(np.mean(ep)) * 35, 2), mean_ext_right_mm=round(float(np.mean(em)) * 35, 2))
    newp.append(q)
    print(p["name"], rep[p["name"]], flush=True)

src = open(spec.origin, encoding="utf8").read()
i0 = src.index("PASSES = (")
i1 = src.index("#: the far-side joins")
body = "PASSES = (\n"
for q in newp:
    body += "    dict(" + ", ".join(f"{k}={q[k]!r}" for k in ("name", "shows", "role", "n", "e1", "phi_a", "phi_b",
                                                             "beta", "width", "gather", "note")) + "),\n"
body += ")\n"
src = src[:i0] + body + src[i1:]
src = src.replace("DESIGN = 'final+r2'", f"DESIGN = 'final+r2+fan+hw{floor}'")
src = src.replace('"""props_lib.smokebomb_wind_fit - the FROZEN winding', '"""props_lib.smokebomb_wind_fit - the FROZEN winding (final pass: widths hidden-widened by WorkFiles/smokebomb/final_pass/tools/fp_widen2.py)', 1)
open(out_py, "w", encoding="utf8").write(src)
json.dump(rep, open(out_py.replace(".py", "_widen.json"), "w"), indent=1)
print("wrote", out_py, round(time.time() - t0, 1), "s")
