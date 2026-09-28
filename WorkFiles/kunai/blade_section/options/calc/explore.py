import json, math, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import secmod
PHOTO = {13.4: 0.325, 26.7: 0.237, 39.4: 0.175, 56.7: 0.185, 74.1: 0.215, 91.4: 0.217, 108.7: 0.228}
def evaluate(opt):
    path = None
    if opt:
        fd, path = tempfile.mkstemp(suffix=".json"); os.write(fd, json.dumps(opt).encode()); os.close(fd)
    K = secmod.load(path)
    plan = K.KunaiPlan()
    rows = []
    for x, ph in PHOTO.items():
        h = K.h_blade(x); R = K.ridge_blade(x); E = K.EDGE_T
        rows.append((x, round(R, 2), round((R - E) / 2 / h, 3), ph))
    gw = {x: round(plan.grind_width(x), 2) for x in (plan.x_plunge + 0.5, 35.0, 90.0, 130.0)}
    return rows, gw, round(plan.x_apex, 1)
cands = json.loads(sys.argv[1])
for name, opt in cands.items():
    rows, gw, apex = evaluate(opt)
    print(f"{name:10s} slopes " + " ".join(f"{r[2]:.3f}" for r in rows) + "  R " + " ".join(f"{r[1]:.2f}" for r in rows) + f"  grind {list(gw.values())} apex {apex}")
print("photo      slopes " + " ".join(f"{v:.3f}" for v in PHOTO.values()))
