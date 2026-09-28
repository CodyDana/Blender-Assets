"""Independent bevel check. Sample luminance inward from the reconciled outline along the
inward normal, separately for each of the 16 edges, and flag which edges are scanner-crisp
(outward normal pointing left or down in image space) versus shadowed (up / right)."""
import bpy, numpy as np, math, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from outline import TIP, HK, ELB, J_IN, J_OUT, P, lead_v, trail_v, C

D = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/manji/"
SRC = "C:/Users/Cody/Desktop/Blender_Projects/References/Shuriken/images/Manjiken.JPG"
CEN = np.array([1305.2, 1317.9]); SPAN = 2842.8; ROT = -0.47
img = bpy.data.images.load(SRC); W, H = img.size
buf = np.empty(W * H * 4, np.float32); img.pixels.foreach_get(buf)
rgb = buf.reshape(H, W, 4)[::-1, :, :3].copy()
L = rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)

def to_img(p, k):
    a = math.radians(ROT + 90 * k)
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    q = np.asarray(p, float) @ R.T * SPAN
    return np.array([CEN[0] + q[0], CEN[1] - q[1]])

def sample(pt, d, ts):
    x = pt[0] + d[0] * ts; y = pt[1] + d[1] * ts
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
    x0 = np.clip(x0, 0, W - 2); y0 = np.clip(y0, 0, H - 2)
    v = (L[y0, x0][:, None] * (1 - fx) * (1 - fy) + L[y0, x0 + 1][:, None] * fx * (1 - fy)
         + L[y0 + 1, x0][:, None] * (1 - fx) * fy + L[y0 + 1, x0 + 1][:, None] * fx * fy)
    return v[:, 0]

EDGES = {
    "arm_lead":  (lambda t: np.array([0.10 + 0.22 * t, lead_v(0.10 + 0.22 * t)]), +1),
    "arm_trail": (lambda t: np.array([0.10 + 0.27 * t, trail_v(0.10 + 0.27 * t)]), -1),
    "hook_back": (None, 0),
    "hook_inner": (lambda t: HK + (TIP - HK) * (0.08 + 0.84 * t), 0),
}

def arc_pt(t):
    a1 = math.atan2(ELB[1] - C[1], ELB[0] - C[0]); a2 = math.atan2(TIP[1] - C[1], TIP[0] - C[0])
    if a2 < a1: a2 += 2 * math.pi
    a = a1 + (a2 - a1) * (0.06 + 0.88 * t)
    return C + P["arc_R"] * np.array([math.cos(a), math.sin(a)])

ts_prof = np.arange(0.0, 80.0, 0.5)
out = {}
for k, armname in enumerate(("right", "top", "left", "bottom")):
    for ename in ("arm_lead", "arm_trail", "hook_back", "hook_inner"):
        widths, normals, prof_stack, frac_from_tip = [], [], [], []
        for t in np.linspace(0.05, 0.95, 26):
            if ename == "hook_back":
                p = arc_pt(t); nvec = (p - C) / np.linalg.norm(p - C)
            elif ename == "hook_inner":
                p = EDGES[ename][0](t); dirv = (TIP - HK) / np.linalg.norm(TIP - HK)
                nvec = np.array([dirv[1], -dirv[0]])
            else:
                p = EDGES[ename][0](t)
                du = 1e-4
                p2 = EDGES[ename][0](t + du / 0.25)
                dirv = (p2 - p) / np.linalg.norm(p2 - p)
                nvec = np.array([-dirv[1], dirv[0]]) * EDGES[ename][1]
            pi_ = to_img(p, k); pn = to_img(p + nvec * 1e-3, k) - to_img(p, k)
            pn /= np.linalg.norm(pn)
            prof = sample(pi_, -pn, ts_prof)           # inward
            face = np.median(prof[int(45 / 0.5):])     # face level 45-80 px in
            noise = 1.4826 * np.median(np.abs(prof[int(45 / 0.5):] - face))
            # band = run from the metal edge until the profile first falls to the face level
            start = int(6 / 0.5)
            excess = prof[start:] - face
            thr = max(2.5 * noise, 0.015)
            below = np.argmax(excess < thr)
            widths.append(ts_prof[start + below] if excess[0] > thr else 0.0)
            normals.append(pn); prof_stack.append(prof); frac_from_tip.append(1 - t)
        pn_mean = np.mean(normals, 0)
        # crisp edges: outward normal points left (-x) or down (+y in image space)
        crisp = (pn_mean[0] < -0.5) or (pn_mean[1] > 0.5)
        out["%s_%s" % (armname, ename)] = dict(
            widths=[float(w) for w in widths], median=float(np.median(widths)),
            inboard_end=float(np.median(widths[:6])), outboard_or_tip_end=float(np.median(widths[-6:])),
            normal=[float(x) for x in pn_mean], crisp=bool(crisp))

print("edge                    crisp   med_px  inboard  tip-end   normal(x,y)")
for k2, v in out.items():
    print("%-22s %s   %6.1f  %7.1f  %7.1f   (%+.2f,%+.2f)"
          % (k2, "YES" if v["crisp"] else " no", v["median"], v["inboard_end"], v["outboard_or_tip_end"], *v["normal"]))

print("\n--- crisp (shadow-free) edges only, by edge type ---")
for ename in ("hook_back", "hook_inner", "arm_lead", "arm_trail"):
    sel = [v for k2, v in out.items() if k2.endswith(ename) and v["crisp"]]
    if not sel:
        print("%-12s : no crisp copy"); continue
    med = np.array([s["median"] for s in sel]); nt = np.array([s["inboard_end"] for s in sel]); fr = np.array([s["outboard_or_tip_end"] for s in sel])
    print("%-12s n=%d  median %5.1f px (%.4f span)   inboard-end %5.1f   tip-end %5.1f"
          % (ename, len(sel), med.mean(), med.mean() / SPAN, nt.mean(), fr.mean()))
json.dump(out, open(D + "reconcile/bevel.json", "w"), indent=1)
