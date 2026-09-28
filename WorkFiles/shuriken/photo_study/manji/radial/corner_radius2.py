"""Corner rounding by the chord-sagitta method, with a synthetic self-test.
At Euclidean distance D from the corner on each side, take points A,B on the contour; h = max deviation of
the contour from chord AB (measured toward the vertex). For a sharp corner of interior angle alpha,
h0 = D*cos(alpha/2); a fillet of radius r reduces it by r*(1/sin(alpha/2)-1)."""
import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import common as C
from corner_radius import synth_corner


def sagitta_radius(cont, i, alpha_deg, D=40.0):
    P = cont.astype(float)
    n = len(P)
    c = P[i]
    d = np.hypot(P[:, 0] - c[0], P[:, 1] - c[1])
    # walk forward / backward until distance >= D
    def walk(step):
        j = i
        for _ in range(4 * int(D) + 40):
            j = (j + step) % n
            if d[j] >= D:
                return j
        return j
    A = P[walk(-1)]; B = P[walk(+1)]
    ch = B - A; L = np.hypot(*ch)
    if L < 1e-6:
        return float('nan'), float('nan')
    nrm = np.array([-ch[1], ch[0]]) / L
    # contour points between A and B (short way through i)
    idx = []
    j = walk(-1)
    while True:
        idx.append(j)
        if j == walk(+1):
            break
        j = (j + 1) % n
    Q = P[idx]
    dev = (Q - A) @ nrm
    s = float(np.max(np.abs(dev)))
    a = math.radians(alpha_deg)
    h0 = D * math.cos(a / 2)
    r = (h0 - s) / (1 / math.sin(a / 2) - 1)
    return r, s


if __name__ == "__main__":
    for D in (30.0, 45.0):
        print("SELF TEST D=%.0f (alpha 95)" % D)
        for rt in (0, 5, 10, 15, 20, 25, 30):
            cont, i, m = synth_corner(rt, 95.0)
            r, s = sagitta_radius(cont, i, 95.0, D)
            print("   r_true %5.1f -> r_est %6.2f (sag %.2f)" % (rt, r, s))
    R1 = json.load(open(os.path.join(C.OUT, "measure_raw.json")))
    cont = np.load(os.path.join(C.OUT, "contour_final.npy"))
    alpha = {}
    for c in R1["corners"]:
        alpha.setdefault(c["kind"], []).append(c["angle_between_edges_deg"])
    alpha = {k: float(np.mean(v)) for k, v in alpha.items()}
    print("mean interior angles", {k: round(v, 2) for k, v in alpha.items()})
    out = []
    for c in R1["corners"]:
        row = dict(kind=c["kind"])
        for D in (25.0, 40.0, 55.0):
            r, s = sagitta_radius(cont, c["contour_i"], alpha[c["kind"]], D)
            row["r_D%d" % D] = r
        out.append(row)
        print("%-20s " % c["kind"], " ".join("D%2.0f r=%6.2f" % (D, row["r_D%d" % D]) for D in (25.0, 40.0, 55.0)))
    json.dump(dict(angles=alpha, corners=out), open(os.path.join(C.OUT, "corner_radius2.json"), "w"), indent=1)
