import sys
sys.argv = [sys.argv[0], "0", "0"] + sys.argv[1:]
exec(open("solve_row2.py").read().split("M = float")[0])
def ev(c4, cg, cs, sw=1.2, sd=0.9, TD=0.85, TW=1.0, sf=(2.30, 3.10, 3.15, 4.35)):
    SF = shape(*sf, 0.40, 0.50)
    A = {"5": SF, "4": shape(c4[0], c4[0] + TD, c4[1], c4[1] + TW, 0.5, 1.7), "G3": shape(cg[0], cg[0] + TD, cg[1], cg[1] + TW, 0.5, 1.7),
         "G1": shape(cs[0], cs[0] + sd, cs[1], cs[1] + sw, 0.55, 0.70)}
    out = {}
    L = list(A)
    for a in range(4):
        for b in range(a + 1, 4):
            out[L[a] + "-" + L[b]] = round(float(sgap(A[L[a]][:2], A[L[b]][:2])))
    for c in ("4", "G3", "G1"):
        for k in KEEPS: out[c + "~" + k] = round(float(sgap(A[c][:2], KEEPS[k])))
        for k in CEN: out[c + "~c" + k] = round(float(sgap(A[c][:2], CEN[k])))
    pts = {k: [round(float(A[k][2][1])), round(float(A[k][2][3]))] for k in A}
    bbs = {k: [round(float(v)) for v in A[k][2]] for k in A}
    return out, pts, bbs
if __name__ == "__main__":
    o, p, b = ev((1.13, 7.85), (1.15, 11.95), (2.05, 13.70))
    print(o); print(p); print(b)
