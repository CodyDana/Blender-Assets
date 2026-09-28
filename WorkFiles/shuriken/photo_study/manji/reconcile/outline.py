"""Reconciled manji outline (from Manjiken.JPG) and the study 2.6 spec outline.
All coordinates are ratios of the tip-to-tip span S = 1, in an arm frame:
  u = outward along the arm axis, v = perpendicular, +v = the counter-clockwise (hook) side.
Handedness: for the arm along +X the hook lies at +Y, which is the left-facing manji.
"""
import numpy as np, math

P = dict(
    half_w0      = 0.05620,   # arm half-width on the arm axis at u = 0
    taper_per_edge_deg = 2.275,
    u_hook       = 0.34410,   # hook inner corner, axial position
    tip_r        = 0.50000,
    tip_off_deg  = 35.00,
    arc_R        = 0.980,     # hook back-edge arc radius
    u_axis_back  = 0.41460,   # back arc crossing of the arm axis
)
T = math.tan(math.radians(P["taper_per_edge_deg"]))
lead_v  = lambda u:  P["half_w0"] - T * u
trail_v = lambda u: -P["half_w0"] + T * u

tip_u = P["tip_r"] * math.cos(math.radians(P["tip_off_deg"]))
tip_v = P["tip_r"] * math.sin(math.radians(P["tip_off_deg"]))
v_hook = lead_v(P["u_hook"])
TIP = np.array([tip_u, tip_v]); HK = np.array([P["u_hook"], v_hook])

def _arc_centre():
    p1 = np.array([P["u_axis_back"], 0.0]); p2 = TIP
    m = (p1 + p2) / 2; d = p2 - p1; L = np.linalg.norm(d)
    h = math.sqrt(max(P["arc_R"] ** 2 - (L / 2) ** 2, 0))
    n = np.array([-d[1], d[0]]) / L
    c1, c2 = m + h * n, m - h * n
    return c1 if c1[0] < c2[0] else c2
C = _arc_centre()

def _elbow():
    lo, hi = 0.30, 0.45
    for _ in range(90):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if np.linalg.norm(np.array([mid, trail_v(mid)]) - C) < P["arc_R"] else (lo, mid)
    return lo
u_elb = _elbow(); ELB = np.array([u_elb, trail_v(u_elb)])

# junction corner: arm 0's trailing edge meets arm 3's leading edge
_jy = (-P["half_w0"] + T * P["half_w0"]) / (1 - T * T)
J_IN  = np.array([P["half_w0"] + T * _jy, _jy])      # v < 0
J_OUT = np.array([-J_IN[1], J_IN[0]])                # = rotate(J_IN, +90)

FILLET = dict(junction=0.0056, hook_inner=0.0056, elbow=0.0018, tip=0.0014)

def _fillet(pPrev, pV, pNext, r, n=16):
    pPrev, pV, pNext = map(np.asarray, (pPrev, pV, pNext))
    d1 = pPrev - pV; d2 = pNext - pV
    n1, n2 = np.linalg.norm(d1), np.linalg.norm(d2)
    if n1 < 1e-9 or n2 < 1e-9 or r <= 0: return [pV]
    d1 /= n1; d2 /= n2
    ang = math.acos(np.clip(d1 @ d2, -1, 1))
    if ang > 3.10 or ang < 0.03: return [pV]
    t = r / math.tan(ang / 2)
    if t > 0.8 * min(n1, n2): return [pV]
    bis = d1 + d2; bis /= np.linalg.norm(bis)
    cen = pV + bis * (r / math.sin(ang / 2))
    q1, q2 = pV + d1 * t, pV + d2 * t
    a1 = math.atan2(q1[1] - cen[1], q1[0] - cen[0])
    a2 = math.atan2(q2[1] - cen[1], q2[0] - cen[0])
    while a2 - a1 >  math.pi: a2 -= 2 * math.pi
    while a1 - a2 >  math.pi: a2 += 2 * math.pi
    return [cen + r * np.array([math.cos(a), math.sin(a)]) for a in np.linspace(a1, a2, n)]

def _arc(p_from, p_to, n=110):
    a1 = math.atan2(p_from[1] - C[1], p_from[0] - C[0])
    a2 = math.atan2(p_to[1] - C[1], p_to[0] - C[0])
    while a2 < a1: a2 += 2 * math.pi
    return [C + P["arc_R"] * np.array([math.cos(a), math.sin(a)]) for a in np.linspace(a1, a2, n)]

def _run(p0, p1, n=40):
    return [p0 + (p1 - p0) * t for t in np.linspace(0, 1, n)]

def reconciled_arm():
    """arm-0 boundary, counter-clockwise, starting inside the J_IN fillet.
    The leading edge after the hook-inner fillet is closed by the NEXT arm's J_IN fillet."""
    prev_on_arm3_lead = np.array([lead_v(0.15), -0.15])     # a point on arm 3's leading edge
    arc0 = _arc(ELB, TIP)
    pts = []
    pts += _fillet(prev_on_arm3_lead, J_IN, ELB, FILLET["junction"])
    pts += _run(np.array(pts[-1]), ELB, 40)[1:-1]
    pts += _fillet(J_IN, ELB, np.array(arc0[2]), FILLET["elbow"])
    pts += arc0[2:-2]
    pts += _fillet(np.array(arc0[-3]), TIP, HK, FILLET["tip"])
    pts += _run(np.array(pts[-1]), HK, 40)[1:-1]
    pts += _fillet(TIP, HK, J_OUT, FILLET["hook_inner"])
    return np.array(pts)

SPEC_MM = dict(square=13.0, arm_w=13.0, arm_len=36.0, hook_len=20.0, hook_w=13.0)
def spec_arm():
    h = SPEC_MM["arm_w"] / 2.0
    u0 = SPEC_MM["square"] / 2.0
    u1 = u0 + SPEC_MM["arm_len"]
    hw, hl = SPEC_MM["hook_w"], SPEC_MM["hook_len"]
    S = 2.0 * math.hypot(h + hl, u1)
    pts = [(u0, -h), (u1, -h), (u1, h + hl), (u1 - hw, h + hl), (u1 - hw, h), (h, h)]
    out = []
    for i in range(len(pts)):
        a, b = np.array(pts[i]), np.array(pts[(i + 1) % len(pts)])
        out += _run(a, b, 30)[:-1]
    return np.array(out) / S

def full_polygon(kind="reconciled"):
    seg = reconciled_arm() if kind == "reconciled" else spec_arm()
    out = []
    for k in range(4):
        a = k * math.pi / 2
        R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
        out.append(seg @ R.T)
    return np.vstack(out)

if __name__ == "__main__":
    for kind in ("reconciled", "spec"):
        p = full_polygon(kind)
        x, y = p[:, 0], p[:, 1]
        A = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
        d = p - np.roll(p, -1, 0); per = np.hypot(d[:, 0], d[:, 1]).sum()
        r = np.hypot(x, y)
        print("%-11s n=%4d  span=%.5f  area/S^2=%.5f  perim/S=%.4f  rmin=%.5f"
              % (kind, len(p), 2 * r.max(), A, per, r.min()))
    print("junction r %.5f  square side %.5f  hook corner (%.5f,%.5f)  tip (%.5f,%.5f)"
          % (np.linalg.norm(J_IN), 2 * abs(J_IN[1]), *HK, *TIP))
    print("elbow (%.5f,%.5f)  arc centre (%.4f,%.4f)  arm w: u0 %.5f  hook %.5f"
          % (*ELB, *C, 2 * P["half_w0"], 2 * v_hook))
    print("overhang past leading edge %.5f   inner edge angle %.3f deg   across-arms %.5f"
          % ((tip_v - lead_v(tip_u)) * math.cos(math.radians(P["taper_per_edge_deg"])),
             math.degrees(math.atan2(tip_v - v_hook, tip_u - P["u_hook"])), 2 * P["u_axis_back"]))
    print("spec extreme point off-axis %.2f deg" % math.degrees(math.atan2(
        SPEC_MM['arm_w'] / 2 + SPEC_MM['hook_len'], SPEC_MM['square'] / 2 + SPEC_MM['arm_len'])))
