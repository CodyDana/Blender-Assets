"""fp_widen - HIDDEN WIDENING of the fitted passes (final pass, maintainer).

The round-1 winder fitted each pass's WIDTH to the strip's VISIBLE width, so passes whose
neighbour covers one edge were made as narrow as what shows (U1 4.8 mm, R_in 6 mm, R3 4.4 mm):
a narrow tape shows both its rolled edges and stands up as a rope - the "tangle of strands".
A real tape is one width; a neighbour covers part of it.  Here each pass is widened toward a
floor width on ONE side at a time, the other edge held where the fit put it, and the side is
kept only if the front label render barely changes (the widened part lies under a later pass).

usage: python fp_widen.py FLOOR_FRAC_D [MAX_GROW_PX] [OUTJSON]
"""
import sys, time, json, copy, types
from multiprocessing import Pool
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
import numpy as np
from props_lib import smokebomb_wind as W
from props_lib import smokebomb_wind_fit as F0

SIZE = 627
SKIP = {"W"}             # W's narrow flat part and twisted section are measured true widths


def fitmod(passes):
    m = types.SimpleNamespace(**{k: getattr(F0, k) for k in dir(F0) if k.isupper()})
    m.PASSES = tuple(passes)
    return m


def widen(p, side, floor, frac=1.0):
    q = dict(p)
    w = np.array(p["width"], float)
    w2 = w + frac * np.maximum(floor - w, 0.0)
    b = np.array(p["beta"], float)
    # +side = +lam (the pass's left); the edge on -side stays: beta' = beta + side*(w'-w) (rad = frac D)
    b2 = b + side * np.degrees(w2 - w)
    q["width"] = tuple(float(x) for x in w2)
    q["beta"] = tuple(float(x) for x in b2)
    return q


def labels(passes):
    wd = W.reference_winding(fitmod(passes))
    lab = W.render_labels(wd, "front", size=SIZE)
    return lab["pass_"], wd.names


def trial(args):
    i, side, floor, frac, base_passes, base_lab = args
    ps = list(base_passes)
    ps[i] = widen(ps[i], side, floor, frac)
    lab, names = labels(ps)
    core = names.index("core") if "core" in names else -99
    ch = lab != base_lab
    pi = names.index(ps[i]["name"])
    grow = int(np.sum(ch & (lab == pi) & (base_lab != core)))
    other = int(np.sum(ch & (lab != pi) & (base_lab != core)))
    covered_core = int(np.sum(ch & (base_lab == core)))
    return dict(i=i, name=ps[i]["name"], side=side, frac=frac, grow=grow, other=other, core_covered=covered_core)


if __name__ == "__main__":
    floor = float(sys.argv[1])
    maxg = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    out = sys.argv[3] if len(sys.argv) > 3 else None
    t0 = time.time()
    passes = [dict(p) for p in F0.PASSES]
    base, names = labels(passes)
    print("names", names, flush=True)
    idx = [i for i, p in enumerate(passes) if p["name"] not in SKIP and np.min(p["width"]) < floor]
    jobs = [(i, s, floor, 1.0, passes, base) for i in idx for s in (+1, -1)]
    with Pool(12) as pool:
        res = pool.map(trial, jobs)
    for r in res:
        print(r, flush=True)
    # accept per pass the better side if under the limit; else try half
    acc = {}
    half_jobs = []
    for i in idx:
        rs = sorted([r for r in res if r["i"] == i], key=lambda r: r["grow"] + r["other"])
        if rs[0]["grow"] + rs[0]["other"] <= maxg:
            acc[i] = (rs[0]["side"], 1.0)
        else:
            half_jobs += [(i, s, floor, 0.5, passes, base) for s in (+1, -1)]
    if half_jobs:
        with Pool(12) as pool:
            res2 = pool.map(trial, half_jobs)
        for r in res2:
            print("half", r, flush=True)
        for i in {j[0] for j in half_jobs}:
            rs = sorted([r for r in res2 if r["i"] == i], key=lambda r: r["grow"] + r["other"])
            if rs[0]["grow"] + rs[0]["other"] <= maxg:
                acc[i] = (rs[0]["side"], 0.5)
    print("accepted", {passes[i]["name"]: v for i, v in acc.items()}, flush=True)
    ps = list(passes)
    for i, (s, f) in acc.items():
        ps[i] = widen(ps[i], s, floor, f)
    lab, names = labels(ps)
    core = names.index("core") if "core" in names else -99
    ch = (lab != base)
    print("combined: changed px", int(ch.sum()), "non-core", int((ch & (base != core)).sum()),
          "core px before/after", int((base == core).sum()), int((lab == core).sum()), "s", round(time.time() - t0))
    if out:
        json.dump({"floor": floor, "accepted": {passes[i]["name"]: v for i, v in acc.items()},
                   "trials": res}, open(out, "w"), indent=1)
        np.save(out.replace(".json", "_lab.npy"), lab)
        np.save(out.replace(".json", "_base.npy"), base)
