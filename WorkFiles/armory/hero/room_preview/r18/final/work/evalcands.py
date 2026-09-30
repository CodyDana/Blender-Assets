import sys, numpy as np
exec(open("solve_row2.py").read().split("M = float")[0])
def cam_proj(loc, look, lens, W=1600, H=900, shift_y=0.0):
    loc = np.array(loc, float); f = np.array(look, float) - loc; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1]); r /= np.linalg.norm(r); u = np.cross(r, f)
    Fp = W * lens / 36.0
    def P(pts):
        d = pts - loc; z = d @ f
        return np.stack([W / 2 + Fp * (d @ r) / z, H / 2 - shift_y * W - Fp * (d @ u) / z], -1)
    return P
def poly_gap(qa, qb):
    pa, pb = qa @ DIRS.T, qb @ DIRS.T
    return float(np.maximum(pb.min(0) - pa.max(0), pa.min(0) - pb.max(0)).max())
def evaluate(C, TD, TW, sfw=1.2, sfg=0.50, sw=1.2, sd=0.9):
    c4, cg, cs = C
    boxes = {"5": (2.30, 3.10, 3.75 - sfw / 2, 3.75 + sfw / 2, 0.40, sfg), "4": (c4[0], c4[0] + TD, c4[1], c4[1] + TW, 0.5, 1.7),
             "G3": (cg[0], cg[0] + TD, cg[1], cg[1] + TW, 0.5, 1.7), "G1": (cs[0], cs[0] + sd, cs[1], cs[1] + sw, 0.55, 0.70),
             "1": (5.1, 6.9, 3.35, 4.65, 0.72, 0.48), "2": (5.1, 6.9, 8.1, 9.3, 0.72, 0.53), "3": (5.2, 6.8, 12.9, 13.9, 0.72, 0.48)}
    A = {k: shape(*v) for k, v in boxes.items()}
    out = {}
    for a, b in (("5", "4"), ("4", "G3"), ("G3", "G1"), ("4", "G1"), ("5", "G3")):
        out[a + "-" + b] = round(float(sgap(A[a][:2], A[b][:2])))
    for c in ("4", "G3", "G1"):
        out[c + "~kmin"] = min(round(float(sgap(A[c][:2], KEEPS[k]))) for k in KEEPS)
        out[c + "~niche"] = round(float(sgap(A[c][:2], KEEPS["niche"])))
    out["G1~lantern"] = round(float(sgap(A["G1"][:2], KEEPS["foot_lantern"])))
    pts = [[round(float(A[k][2][1])), round(float(A[k][2][3]))] for k in ("5", "4", "G3", "G1")]
    # CX (from the platform): west row silhouettes
    P = cam_proj((6.0, 19.4, 2.4), (6.0, 1.0, 0.8), 24)
    q = {k: P(corners(*boxes[k]).reshape(-1, 3)) for k in ("5", "4", "G3", "G1")}
    cx = {a + "-" + b: round(poly_gap(q[a], q[b])) for a, b in (("G1", "G3"), ("G3", "4"), ("4", "5"), ("G1", "4"))}
    return out, pts, cx
if __name__ == "__main__":
    print("current", evaluate(((1.13, 7.85), (1.15, 11.95), (2.05, 13.70)), 0.85, 1.0))
