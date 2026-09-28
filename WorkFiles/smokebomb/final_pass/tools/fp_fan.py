"""fp_fan - the U fan re-laid as SHINGLES (final pass, maintainer).

The winder laid the fan U1 > U2 > U3 > U4 > U5 (U1 on top), each owning its RIGHT edge, and
fitted each tape to its VISIBLE width (U1 4.8 mm, U2..U5 ~7 mm), so every U band showed both
rolled edges and stood up as a rope.  REFERENCE_SPEC 4.4 says the order inside the U family
cannot be resolved from the photo; so here it is reversed - U1 < U2 < U3 < U4 < U5, each band
owning its LEFT edge (UA, UC, UD, UE, UF: the same traced edges) and running on at the full
tape width under the next band, the way a winder's successive passes shingle into a pinwheel.

    python fp_fan.py SRC_FIT.py OUT_FIT.py WIDTH_FRAC_D
"""
import sys, importlib.util, json
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/wd_tools")
import numpy as np
from props_lib import smokebomb_wind as W
import wd_fitlib as FL

src, out, WT = sys.argv[1], sys.argv[2], float(sys.argv[3])
spec = importlib.util.spec_from_file_location("fsrc", src)
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
P = {p["name"]: dict(p) for p in F.PASSES}
OWN = {"U1": "UA", "U2": "UC", "U3": "UD", "U4": "UE", "U5": "UF"}


def ps_of(p):
    return W.PassSpec(name=p["name"], shows=tuple(p["shows"]), n=tuple(p["n"]), e1=tuple(p["e1"]), phi_a=p["phi_a"],
                      phi_b=p["phi_b"], beta=tuple(p["beta"]), width=tuple(p["width"]), gather=tuple(p["gather"]))


rep = {}
for name, edge in OWN.items():
    p = P[name]
    ps = ps_of(p)
    E = FL.px2cam(FL.edge_px(edge, step=4.0))
    ph, lam = ps.coords(E)
    o = np.argsort(ph); ph, lam = ph[o], lam[o]
    # which side is the traced edge on (must be +1 = left)?
    side = np.sign(np.median(lam - ps.beta_rad(ph)))
    phs = np.linspace(p["phi_a"], p["phi_b"], 400)
    b0 = ps.beta_rad(phs)
    w0 = ps.width_rad(phs) / 2.0             # half width, rad
    # the new band: its LEFT edge on the traced edge where traced, full width WT
    lam_e = np.interp(phs, ph, lam)          # held flat past the traced ends
    d_in = np.minimum(np.abs(phs - ph[0]), np.abs(phs - ph[-1]))
    inside = (phs >= ph[0]) & (phs <= ph[-1])
    # past the traced range: blend back to the old left edge over 25 deg
    old_left = b0 + side * w0
    wgt = np.where(inside, 1.0, np.clip(1.0 - d_in / 25.0, 0.0, 1.0))
    wgt = wgt * wgt * (3 - 2 * wgt)
    left = wgt * lam_e + (1 - wgt) * old_left
    # full width over the fan and on past the whorl; back to the fitted width below it (B side)
    ww = np.clip((phs - (ph[0] - 35.0)) / 25.0, 0.0, 1.0)
    ww = ww * ww * (3 - 2 * ww)
    wnew = ww * max(WT, 0.0) + (1 - ww) * w0
    wnew = np.maximum(wnew, w0)
    beta_new = left - side * wnew
    B = W.bspline_basis(phs, p["phi_a"], p["phi_b"], len(p["beta"]))
    cb = np.linalg.lstsq(B, np.degrees(beta_new), rcond=None)[0]
    p["beta"] = tuple(round(float(x), 6) for x in cb)
    Bw = W.bspline_basis(phs, p["phi_a"], p["phi_b"], len(p["width"]))
    cw = np.linalg.lstsq(Bw, wnew, rcond=None)[0]
    p["width"] = tuple(round(float(x), 6) for x in cw)
    p["note"] = p["note"] + f" [final pass: shingled fan, owns {edge} on its left, {WT} D wide]"
    rep[name] = dict(edge=edge, side=float(side), phi_range=[round(float(ph[0]), 1), round(float(ph[-1]), 1)],
                     old_w_mean=round(float(np.mean(w0)), 4))
    print(name, rep[name])

MODE = sys.argv[4] if len(sys.argv) > 4 else "weave"
order = [p["name"] for p in F.PASSES]
passes = [P[n] for n in order]
newc = list(F.CONNECTORS)
weaves = list(F.WEAVES)
fan = sorted(OWN)                       # U1..U5, left to right
for lo, up in zip(fan[:-1], fan[1:]):
    r = rep[lo]["phi_range"]
    weaves.insert(0, dict(lower=lo, lower_range=(r[0] - 15.0, P[lo]["phi_b"] + 1.0), upper=up, upper_range=None,
                          lower_where="front", upper_where="front", extend=True, stop_hidden=True,
                          why="final pass: the shingled fan - each U band runs on under the next one to its right"))
txt = open(src, encoding="utf8").read()
i0 = txt.index("PASSES = ("); i1 = txt.index("#: the far-side joins")
body = "PASSES = (\n"
for q in passes:
    body += "    dict(" + ", ".join(f"{k}={q[k]!r}" for k in ("name", "shows", "role", "n", "e1", "phi_a", "phi_b",
                                                             "beta", "width", "gather", "note")) + "),\n"
body += ")\n"
txt = txt[:i0] + body + txt[i1:]
j0 = txt.index("CONNECTORS = ("); j1 = txt.index("#: the free end")
txt = txt[:j0] + "CONNECTORS = (\n" + "".join(f"    {c!r},\n" for c in newc) + ")\n" + txt[j1:]
if MODE == "weave":
    added = weaves[:len(weaves) - len(F.WEAVES)]
    txt += ("\n#: final pass (maintainer): the SHINGLED FAN - each U band runs on under the next one to its right\n"
            "#: (REFERENCE_SPEC 4.4: the order inside the U family cannot be resolved from the photo)\n"
            "WEAVES = (\n" + "".join("    dict(" + ", ".join(f"{k}={v!r}" for k, v in w.items()) + "),\n" for w in added)
            + ") + WEAVES\n")
open(out, "w", encoding="utf8").write(txt)
json.dump(rep, open(out.replace(".py", "_fan.json"), "w"), indent=1)
print("wrote", out)
