"""BlackCloak_MH_v2 stage 2, step 1: cut the flat pattern pieces, sew and drape them with Blender 5.2 cloth on the male.

    blender -b --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_drape.py -- --tag r1 [--frames 240]

Scene (fresh, never saved over anything): the locked fitting body appended read-only (garment_helpers.append_fitbody,
hash-checked), posed ARMS_DOWN_V2; the body is baked to a static, slightly inflated collider (air to the skin), the
head and hair proxy to static colliders, a floor at z = 0.

Pieces (TARGET_SPEC 4.1, the pilot technique of WorkFiles/BlackCloak_Review/male/path):
* FUNNEL (skinned, stiff): built by bcv2_geom.Funnel around the head with a rolled rim; a static collider here.
* MANTLE: one ~330-degree circle cut. Its neck edge is sewn (pinned) along the funnel wall from his right-front
  (PHI_EDGE) round the back to his left-front (PHI_WRAP_START); from there the WRAP continues across his front with a
  free top edge whose last GATHER_LEN is gathered into a rosette under the button on his right shoulder
  (animated pins: a shape key moves those edge vertices into the rosette over frames 5-45). The open edge (right
  panel) hangs from PHI_EDGE; the wrap's front edge hangs from the button.
* LINING: a flared front panel pinned under the funnel, hanging in front of the legs, inside the mantle.
Mantle + lining are one cloth object (self-collision separates them). Triangulation: isotropic, size field (2 cm in
the skinned yoke round the button, ~3 cm near the button, ~4 cm along the neck, ~6.5 cm elsewhere) so the cloth part
already meets the 6,000-triangle cloth budget with no decimation.

Writes WorkFiles/BlackCloak_MH_v2/build/drape_<tag>.npz + drape_<tag>.json + preview PNGs.
"""
import sys, os, json, math, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcv2_common as C
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from pipeline import garment_helpers as gh
from pipeline import garment_qa as gq
import bcv2_geom as G

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="r1")
ap.add_argument("--frames", type=int, default=240)
ap.add_argument("--h-far", type=float, default=0.0, help="coarse edge length; 0 = solve for the sim budget")
ap.add_argument("--sim-target", type=int, default=4700, help="mantle cloth-part triangles to aim for")
ap.add_argument("--inflate", type=float, default=0.008)
ap.add_argument("--mass", type=float, default=0.5)
ap.add_argument("--bending", type=float, default=1.5)
ap.add_argument("--no-sim", action="store_true")
ap.add_argument("--edge-buttoned", type=float, default=0.10, help="right panel edge pinned under the button down to this pattern depth")
ap.add_argument("--lin-phi0", type=float, default=-100.0, help="lining's right end (azimuth)")
ap.add_argument("--gather-len", type=float, default=C.GATHER_LEN, help="wrap top edge length gathered under the button")
ap.add_argument("--arc-start", type=float, default=C.GATHER_ARC_DEG[0], help="rosette arc start angle (deg; 90 = up)")
ap.add_argument("--fine", type=float, default=0.0, help="drape on a fine working mesh with this edge (m), then carry the "
                "drape onto the budget mesh through the shared flat-pattern domain; 0 = drape the budget mesh itself")
ap.add_argument("--k-cone", type=float, default=0.0, help="override C.K_CONE (pattern angle / body azimuth)")
ap.add_argument("--k-wrap", type=float, default=0.0, help="pattern angle per body azimuth in the WRAP (fullness of "
                "the part that crosses his front to the button); 0 = same as the mantle's K_CONE")
ap.add_argument("--wrap-start", type=float, default=-999.0, help="override C.PHI_WRAP_START (azimuth where the neck seam ends)")
ap.add_argument("--yoke-start", type=float, default=-999.0, help="override C.PHI_YOKE_START")
ap.add_argument("--place-natural", action="store_true", help="start the wrap on the isometric cone (K_CONE) so its "
                "corner starts where it would hang and the gather pins pull it across to the button")
ap.add_argument("--wrap-len-add", type=float, default=0.0, help="extra fabric length (m) below the wrap's top edge "
                "(the pull up to the button lifts the wrap's hem); ramps in over the first 30% of the wrap")
ap.add_argument("--fan-h0", type=float, default=0.030, help="budget-mesh edge at the button (fold fan zone)")
ap.add_argument("--fan-k", type=float, default=0.075, help="budget-mesh edge growth per metre of pattern distance from the button")
ap.add_argument("--fan-r", type=float, default=99.0, help="pattern radius of the fan zone (beyond it the fan term is off)")
ap.add_argument("--pleats", type=int, default=0, help="pressed pleats radiating from the wrap corner (the button): count; "
                "0 = none. They live in the cloth's rest shape (steam-pressed wool), so the drape keeps them as a fold fan")
ap.add_argument("--pleat-amp", type=float, default=0.02, help="pleat half-depth (m) from 35 cm out")
ap.add_argument("--pleat-len", type=float, default=0.9, help="pattern distance from the corner where the pleats have faded out")
ap.add_argument("--pleat-margin", type=float, default=12.0, help="degrees kept pleat-free next to the top and front edges")
ap.add_argument("--wrap-rise", type=float, default=-1.0, help="override C.WRAP_TOP_RISE")
ap.add_argument("--no-preview", action="store_true")
A = ap.parse_args(argv)
C.GATHER_LEN = A.gather_len
if A.k_cone > 0:
    C.K_CONE = A.k_cone
if A.wrap_start > -900:
    C.PHI_WRAP_START = A.wrap_start
if A.yoke_start > -900:
    C.PHI_YOKE_START = A.yoke_start
K_WRAP = A.k_wrap if A.k_wrap > 0 else C.K_CONE
if A.wrap_rise >= 0:
    C.WRAP_TOP_RISE = A.wrap_rise
C.GATHER_ARC_DEG = (A.arc_start, C.GATHER_ARC_DEG[1])
T0 = time.time()
os.makedirs(C.WORK_DIR, exist_ok=True)
REPORT = {"tag": A.tag, "args": vars(A)}


def log(*a):
    print("BCV2", *a, flush=True)


# ------------------------------------------------------------------ scene, body, pose
bpy.ops.wm.read_factory_settings(use_empty=True)
fit = gh.append_fitbody()
for o in list(bpy.data.objects):
    if o.name.endswith("HairCards"):
        bpy.data.objects.remove(o, do_unlink=True)
arm = fit["armature"]
gq.apply_pose(arm, C.ARMS_DOWN_V2)
sc = bpy.context.scene


def evaluated_np(o):
    c, polys = gq.evaluated_world(o)
    return c, polys


def static_copy(o, name, inflate=0.0):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    me.transform(o.matrix_world)
    if inflate:
        bm = bmesh.new(); bm.from_mesh(me); bm.normal_update()
        for v in bm.verts:
            v.co += v.normal * inflate
        bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob


body_c, _ = evaluated_np(fit["body"])
head_c, _ = evaluated_np(fit["head"])
hair_c, _ = evaluated_np(fit["hair_proxy"])
profile = G.RadialProfile(np.concatenate([body_c, head_c, hair_c]))
col_body = static_copy(fit["body"], "BCV2_COL_Body", A.inflate)
col_head = static_copy(fit["head"], "BCV2_COL_Head", A.inflate)
real_body = static_copy(fit["body"], "BCV2_REAL_Body")
real_head = static_copy(fit["head"], "BCV2_REAL_Head")
real_body.hide_render = real_head.hide_render = True
for o in (col_body, col_head):
    m = o.modifiers.new("Collision", "COLLISION")
    o.collision.thickness_outer = 0.004
    o.collision.cloth_friction = 5.0
    o.hide_render = True
# BVH of the real skin (arms-down) for checks and for the pre-shape lift
skin_bm = bmesh.new()
for o in (real_body, real_head):
    tmp = bmesh.new(); tmp.from_mesh(o.data); tmp.verts.ensure_lookup_table()
    me2 = bpy.data.meshes.new("tmp"); tmp.to_mesh(me2); tmp.free()
    skin_bm.from_mesh(me2); bpy.data.meshes.remove(me2)
skin_tree = BVHTree.FromBMesh(skin_bm)
colbm = bmesh.new(); colbm.from_mesh(col_body.data)
col_tree = BVHTree.FromBMesh(colbm)

# ------------------------------------------------------------------ funnel
F = G.Funnel(profile)
fme = bpy.data.meshes.new("BCV2_Funnel")
fme.from_pydata(F.verts.tolist(), [], [list(f) for f in F.faces])
fob = bpy.data.objects.new("BCV2_Funnel", fme)
sc.collection.objects.link(fob)
fcol = fob.modifiers.new("Collision", "COLLISION")
fob.collision.thickness_outer = 0.003
fob.collision.cloth_friction = 5.0
REPORT["funnel"] = {"verts": len(F.verts), "quads": len(F.faces), "z_bottom_min_max": [float(F.zb.min()), float(F.zb.max())],
                    "rim_boundary_front_back": [G.rim_boundary_z(0), G.rim_boundary_z(180)],
                    "bottom_perimeter_m": F.row_len_bottom}
log("funnel", REPORT["funnel"])

# ------------------------------------------------------------------ mantle neck curve (on the funnel wall)
Z_NECK = [(-180, 1.600), (-110, 1.605), (-90, 1.606), (-70, 1.578), (-40, 1.552), (0, 1.536), (30, 1.536),
          (60, 1.572), (90, 1.606), (135, 1.600)]


def z_neck(phi):
    z = C.interp_table(Z_NECK, C.wrap180(phi), periodic=360.0)
    f = ((phi + 180.0) % 360.0) / 360.0 * F.ncol
    i = int(round(f)) % F.ncol
    return max(z, float(F.zb[i]) + 0.02)


def neck_point(phi):
    return F.wall_point(phi, z_neck(phi), offset=C.SEAM_OFFSET)


# sewn part: phi from PHI_EDGE decreasing through the back to PHI_WRAP_START (- 360)
body_span_sewn = 360.0 - (C.PHI_WRAP_START - C.PHI_EDGE)
phis = np.linspace(0, body_span_sewn, 400)
pts = np.array([neck_point(C.PHI_EDGE - a) for a in phis])
neck_len = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
alpha_s = math.radians(body_span_sewn * C.K_CONE)
r_in = neck_len / alpha_s
alpha_e = alpha_s + math.radians((C.PHI_WRAP_START - C.PHI_CLASP) * K_WRAP)
alpha_b = alpha_s + math.radians((C.PHI_WRAP_START - C.PHI_YOKE_START) * K_WRAP)   # skinned yoke: wrap from PHI_YOKE_START on
REPORT["pattern"] = {"neck_len_m": neck_len, "r_in": r_in, "alpha_s_deg": math.degrees(alpha_s), "alpha_e_deg": math.degrees(alpha_e)}
log("pattern", REPORT["pattern"])


def phi_of_alpha(a):
    if a <= alpha_s:
        return C.PHI_EDGE - math.degrees(a) / C.K_CONE
    return C.PHI_WRAP_START - math.degrees(a - alpha_s) / K_WRAP


def phi_place(a):
    """Azimuth where pattern angle a starts (the rolled cone); with --place-natural the whole mantle uses K_CONE."""
    if A.place_natural:
        return C.PHI_EDGE - math.degrees(a) / C.K_CONE
    return phi_of_alpha(a)


def k_of_alpha(a):
    """Local pattern-angle / azimuth ratio for the start cone: K_CONE on the sewn mantle, blending to K_WRAP over the
    first 20 pattern degrees of the wrap."""
    if A.place_natural:
        return C.K_CONE
    t = C.smoothstep(alpha_s, alpha_s + math.radians(20.0), a)
    return C.K_CONE + (K_WRAP - C.K_CONE) * t


def r_top(a):
    if a <= alpha_s:
        return r_in
    u = (a - alpha_s) / (alpha_e - alpha_s)
    return r_in + C.WRAP_TOP_RISE * u ** 1.4


def r_hem(a):
    extra = 0.0
    if A.wrap_len_add and a > alpha_s:
        extra = A.wrap_len_add * C.smoothstep(0.0, 0.3, (a - alpha_s) / (alpha_e - alpha_s))
    return r_top(a) + C.fabric_length_from_top(phi_of_alpha(a)) + extra


def s_pin(a):
    """Depth of the yoke (skinned) below the top edge, for alpha in [alpha_b, alpha_e]."""
    u = (a - alpha_b) / (alpha_e - alpha_b)
    return 0.19 - 0.02 * u


def pol(r, a):
    return np.array([r * math.cos(a), r * math.sin(a)])


# gather-edge midpoint in pattern space (size field centre)
def top_edge_dense():
    aa = np.linspace(alpha_s, alpha_e, 600)
    return np.array([pol(r_top(a), a) for a in aa])


ted = top_edge_dense()
seglen = np.linalg.norm(np.diff(ted, axis=0), axis=1)
cum_from_end = np.concatenate([np.cumsum(seglen[::-1])[::-1], [0.0]])
gather_mid = ted[np.argmin(np.abs(cum_from_end - C.GATHER_LEN / 2))]
REPORT["pattern"]["wrap_top_edge_len_m"] = float(seglen.sum())

# seam (yoke boundary) polyline: column at alpha_b from the neck to s_pin, then the row to the front edge
seam_dense = [pol(r_top(alpha_b) + t, alpha_b) for t in np.linspace(0, s_pin(alpha_b), 60)]
seam_dense += [pol(r_top(a) + s_pin(a), a) for a in np.linspace(alpha_b, alpha_e, 400)[1:]]
seam_dense = np.array(seam_dense)


def dist_to(poly, p):
    d = poly - np.asarray(p)[None, :]
    return float(np.sqrt((d * d).sum(1)).min())


def in_yoke(p):
    r = math.hypot(p[0], p[1])
    a = math.atan2(p[1], p[0]) % (2 * math.pi)
    return alpha_b <= a <= alpha_e + 1e-9 and r <= r_top(a) + s_pin(a)


H_FINE = 0.02
RIGHT_EDGE_BUTTONED = A.edge_buttoned
LIN_PHI0 = A.lin_phi0
EST_FACTOR = 0.65          # measured: the Poisson + CDT mesh has ~0.65 of the ideal equilateral count


def make_hfun(h_far):
    def h(p):
        p = np.asarray(p, float)
        r = math.hypot(p[0], p[1])
        a = math.atan2(p[1], p[0]) % (2 * math.pi)
        if a > alpha_e + 1e-9:
            a -= 2 * math.pi
        s = max(0.0, r - r_top(a))
        hh = h_far
        hh = min(hh, 0.040 + 0.08 * (s / 0.6))                        # along the neck / top edge
        dc = float(np.hypot(*(p - gather_mid)))
        if dc <= A.fan_r:
            hh = min(hh, A.fan_h0 + A.fan_k * dc)                      # round the button (fold fan)
        if in_yoke(p):
            hh = min(hh, H_FINE + 0.01 * min(1.0, dc / 0.35))
        else:
            hh = min(hh, H_FINE + 0.012 + 0.35 * dist_to(seam_dense[::8], p))
        return max(H_FINE, min(h_far, hh))
    return h


# ---- boundary loop (CCW): right edge out, hem, front edge in, wrap top edge back, neck arc back to start
def build_loop(hfun):
    """Boundary loop with the yoke seam's two ends as break points (so they are exact loop vertices)."""
    kinds = []
    parts = []
    ends = {}
    re = resample(np.array([pol(t, 0.0) for t in np.linspace(r_in, r_hem(0.0), 200)]), hfun)
    parts.append(re[:-1]); kinds += [5] * (len(re) - 1)
    hem = resample(np.array([pol(r_hem(a), a) for a in np.linspace(0.0, alpha_e, 2400)]), hfun)
    parts.append(hem[:-1]); kinds += [4] * (len(hem) - 1)
    r_e1 = r_top(alpha_e) + s_pin(alpha_e)
    fe1 = resample(np.array([pol(t, alpha_e) for t in np.linspace(r_hem(alpha_e), r_e1, 200)]), hfun)
    parts.append(fe1[:-1]); kinds += [3] * (len(fe1) - 1)
    ends["e1"] = sum(len(p_) for p_ in parts)
    fe2 = resample(np.array([pol(t, alpha_e) for t in np.linspace(r_e1, r_top(alpha_e), 100)]), hfun)
    parts.append(fe2[:-1]); kinds += [9] + [3] * (len(fe2) - 2)
    te1 = resample(np.array([pol(r_top(a), a) for a in np.linspace(alpha_e, alpha_b, 800)]), hfun)
    parts.append(te1[:-1]); kinds += [2] * (len(te1) - 1)
    ends["e0"] = sum(len(p_) for p_ in parts)
    te2 = resample(np.array([pol(r_top(a), a) for a in np.linspace(alpha_b, alpha_s, 400)]), hfun)
    parts.append(te2[:-1]); kinds += [8] + [2] * (len(te2) - 2)
    nk = resample(np.array([pol(r_in, a) for a in np.linspace(alpha_s, 0.0, 1600)]), hfun)
    parts.append(nk[:-1]); kinds += [1] * (len(nk) - 1)
    loop = np.vstack(parts)
    return loop, np.array(kinds), ends


def resample(dense, hfun):
    return G.resample_polyline(dense, hfun)


def estimate_tris(hfun, region="sim"):
    """Triangles an isotropic mesh with edge h would have over the pattern (grid integration)."""
    rr = np.linspace(r_in, max(r_hem(a) for a in np.linspace(0, alpha_e, 50)), 80)
    aa = np.linspace(0, alpha_e, 160)
    tot = 0.0
    dr, da = rr[1] - rr[0], aa[1] - aa[0]
    for a in aa:
        for r in rr:
            if r < r_top(a) or r > r_hem(a):
                continue
            p = pol(r, a)
            if (region == "sim") == in_yoke(p):
                continue
            h = hfun(p)
            tot += r * dr * da / (0.433 * h * h)
    return tot


if A.h_far > 0:
    H_FAR = A.h_far
else:
    lo, hi = 0.04, 0.10
    for _ in range(10):
        mid = 0.5 * (lo + hi)
        if EST_FACTOR * estimate_tris(make_hfun(mid)) > A.sim_target:
            lo = mid
        else:
            hi = mid
    H_FAR = 0.5 * (lo + hi)
hfun = make_hfun(H_FAR)
REPORT["pattern"]["h_far"] = H_FAR
REPORT["pattern"]["est_sim_tris"] = estimate_tris(hfun)
REPORT["pattern"]["est_yoke_tris"] = estimate_tris(hfun, "yoke")
log("h_far", H_FAR, REPORT["pattern"]["est_sim_tris"], REPORT["pattern"]["est_yoke_tris"])

loop, loop_kind, ends = build_loop(hfun)
seam_pts = resample(seam_dense, hfun)
seam_inner = seam_pts[1:-1]        # its ends are loop vertices (top edge at alpha_b, front edge at s_pin)
e0, e1 = ends["e0"], ends["e1"]
log("seam ends snap error", float(np.linalg.norm(loop[e0] - seam_pts[0])), float(np.linalg.norm(loop[e1] - seam_pts[-1])))
t1 = time.time()
P2, TRI, nfixed = G.triangulate_pattern(loop, [(seam_inner, e0, e1)], hfun, seed=11, smooth_iters=6)
# the seam polyline was passed without its ends; connect its ends to the snapped loop points
log("mantle mesh", len(P2), len(TRI), "in", round(time.time() - t1, 1), "s")
nloop = len(loop)
vkind = np.zeros(len(P2), int)
vkind[:nloop] = loop_kind
vkind[nloop:nloop + len(seam_inner)] = 7
vkind[e0] = 8; vkind[e1] = 9     # seam ends on the neck / front edge
cen = P2[TRI].mean(1)
fregion = np.array([1 if in_yoke(c) else 0 for c in cen])
ang = G.tri_min_angles(P2, TRI)
REPORT["mantle_mesh"] = {"verts": int(len(P2)), "tris": int(len(TRI)), "yoke_tris": int(fregion.sum()),
                         "sim_tris": int((fregion == 0).sum()), "min_angle_lt10": int((ang < 10).sum()),
                         "min_angle_lt20": int((ang < 20).sum()), "min_angle_min": float(ang.min())}
log("mantle mesh", REPORT["mantle_mesh"])
Pr = np.hypot(P2[:, 0], P2[:, 1])
Pa = np.arctan2(P2[:, 1], P2[:, 0]) % (2 * math.pi)
Pa[(Pa > alpha_e + 0.05)] -= 2 * math.pi      # points just below alpha=0 (right edge) wrap to negative

# gather vertices: top-edge loop verts within GATHER_LEN (along the edge) of the front corner, ordered free end -> corner
def gather_of(P, kinds, nl):
    te_idx = [i for i in range(nl) if kinds[i] == 2]                # ordered from alpha_e towards alpha_s
    g = [te_idx[0]]                                                   # first top-edge point = the corner at alpha_e
    acc = 0.0
    for a_, b_ in zip(te_idx, te_idx[1:]):
        acc += float(np.linalg.norm(P[a_] - P[b_]))
        if acc > C.GATHER_LEN + 1e-6:
            break
        g.append(b_)
    return g[::-1]      # free end first, corner last


gather = gather_of(P2, loop_kind, nloop)
vkind[gather] = 6
REPORT["gather_verts"] = len(gather)

# ------------------------------------------------------------------ lining pattern (flared front panel)
Z_LIN = [(-82, 1.430), (-65, 1.445), (-40, 1.470), (0, 1.470), (45, 1.470)]
lin_phis = np.linspace(LIN_PHI0, 80, 160)


LIN_BRANCH = []


def lining_top_point(phi):
    """The lining is sewn into the neckline seam: 2 mm outside the funnel wall, just under the mantle's seam where
    the mantle is sewn (his right shoulder round to the right panel's edge, and his left from the wrap start), and
    along the funnel's lower edge across the front (under the wrap)."""
    fi = int(round(((phi + 180.0) % 360.0) / 360.0 * F.ncol)) % F.ncol
    zb = float(F.zb[fi])
    sewn = C.wrap180(phi) <= C.PHI_EDGE or C.wrap180(phi) >= C.PHI_WRAP_START
    z = (z_neck(phi) - 0.010) if sewn else (zb + 0.008)
    z = max(z, zb + 0.006)
    p = F.wall_point(phi, z, offset=0.002)
    LIN_BRANCH.append((round(phi, 1), "sewn" if sewn else "rim", round(z, 3)))
    return p


lt = np.array([lining_top_point(p) for p in lin_phis])
REPORT["lining_top_branches"] = LIN_BRANCH[::6]
# smooth the top curve
for _ in range(8):
    lt[1:-1] = 0.25 * lt[:-2] + 0.5 * lt[1:-1] + 0.25 * lt[2:]
Lc = float(np.linalg.norm(np.diff(lt, axis=0), axis=1).sum())
LEN_L = 1.37
BOT_W = 0.84
thetaL = (BOT_W - Lc) / LEN_L
rL = Lc / thetaL
hL = 0.072


def build_lining(h_):
    def hL_fun(p):
        return h_
    lin_loop_parts, lin_kind = [], []
    # aL0, aL1 = math.pi / 2 - thetaL / 2, math.pi / 2 + thetaL / 2          # symmetric about +Y in pattern space
    seg = G.resample_polyline(np.array([pol(rL, a) for a in np.linspace(aL1, aL0, 200)]), hL_fun)      # top (right to left)
    lin_loop_parts.append(seg[:-1]); lin_kind += [1] * (len(seg) - 1)
    seg = G.resample_polyline(np.array([pol(t, aL0) for t in np.linspace(rL, rL + LEN_L, 200)]), hL_fun)
    lin_loop_parts.append(seg[:-1]); lin_kind += [5] * (len(seg) - 1)
    seg = G.resample_polyline(np.array([pol(rL + LEN_L, a) for a in np.linspace(aL0, aL1, 400)]), hL_fun)
    lin_loop_parts.append(seg[:-1]); lin_kind += [4] * (len(seg) - 1)
    seg = G.resample_polyline(np.array([pol(t, aL1) for t in np.linspace(rL + LEN_L, rL, 200)]), hL_fun)
    lin_loop_parts.append(seg[:-1]); lin_kind += [5] * (len(seg) - 1)
    lloop = np.vstack(lin_loop_parts)
    # make CCW
    area2 = np.sum(lloop[:, 0] * np.roll(lloop[:, 1], -1) - np.roll(lloop[:, 0], -1) * lloop[:, 1])
    lin_kind = np.array(lin_kind)
    if area2 < 0:
        lloop = lloop[::-1].copy(); lin_kind = lin_kind[::-1].copy()
    LP2, LTRI, lnf = G.triangulate_pattern(lloop, [], hL_fun, seed=5, smooth_iters=6)
    lvkind = np.zeros(len(LP2), int); lvkind[:len(lloop)] = lin_kind
    return LP2, LTRI, lvkind


aL0, aL1 = math.pi / 2 - thetaL / 2, math.pi / 2 + thetaL / 2          # symmetric about +Y in pattern space
LP2, LTRI, lvkind = build_lining(hL)
lang = G.tri_min_angles(LP2, LTRI)
REPORT["lining_mesh"] = {"verts": int(len(LP2)), "tris": int(len(LTRI)), "min_angle_lt10": int((lang < 10).sum()),
                         "top_len": Lc, "theta_deg": math.degrees(thetaL), "r_in": rL}
log("lining", REPORT["lining_mesh"])

# ------------------------------------------------------------------ fine working mesh (the drape is simulated on it)
COARSE = dict(P2=P2, TRI=TRI, vkind=vkind, Pr=Pr, Pa=Pa, loop_kind=loop_kind, nloop=nloop, gather=gather,
              LP2=LP2, LTRI=LTRI, lvkind=lvkind)
if A.fine > 0:
    def hfun_f(p):
        return max(0.8 * A.fine, min(A.fine, hfun(p)))
    t1 = time.time()
    loop_f, kind_f, _ends_f = build_loop(hfun_f)
    P2, TRI, _nf = G.triangulate_pattern(loop_f, [], hfun_f, seed=13, smooth_iters=4)
    nloop = len(loop_f); loop_kind = kind_f
    vkind = np.zeros(len(P2), int); vkind[:nloop] = kind_f
    Pr = np.hypot(P2[:, 0], P2[:, 1])
    Pa = np.arctan2(P2[:, 1], P2[:, 0]) % (2 * math.pi)
    Pa[(Pa > alpha_e + 0.05)] -= 2 * math.pi
    gather = gather_of(P2, loop_kind, nloop)
    vkind[gather] = 6
    LP2, LTRI, lvkind = build_lining(A.fine)
    _fa = G.tri_min_angles(P2, TRI)
    REPORT["fine_mesh"] = {"h": A.fine, "verts": int(len(P2)), "tris": int(len(TRI)), "lining_tris": int(len(LTRI)),
                           "gather_verts": len(gather), "min_angle_lt10": int((_fa < 10).sum()), "seconds": round(time.time() - t1, 1)}
    log("fine mesh", REPORT["fine_mesh"])

# ------------------------------------------------------------------ 3-D placement (rolled cone + lift)
BETA = math.acos(C.K_CONE)


def outward_h(phi):
    pr = math.radians(phi)
    return np.array([math.sin(pr), -math.cos(pr), 0.0])


def place_mantle():
    X = np.zeros((len(P2), 3))
    for i, (r, a) in enumerate(zip(Pr, Pa)):
        phi = phi_place(a)
        base = neck_point(phi)
        s0 = r - r_in
        bet = math.acos(min(0.97, k_of_alpha(a)))
        X[i] = base + s0 * (math.cos(bet) * outward_h(phi) + np.array([0, 0, -math.sin(bet)]))
        if a > alpha_s:            # the wrap's end lies over the right panel: start it one layer outside
            w = C.smoothstep(-38.0, -50.0, C.wrap180(phi))
            X[i] += w * 0.04 * (math.sin(BETA) * outward_h(phi) + np.array([0, 0, math.cos(BETA)]))
    return X


def lift(X, pinned, clear=0.03):
    dz = np.zeros(len(X))
    for i, p in enumerate(X):
        if pinned[i]:
            continue
        hit = col_tree.ray_cast(Vector((p[0], p[1], 2.2)), Vector((0, 0, -1)), 3.0)
        if hit[0] is not None and hit[0].z + clear > p[2]:
            dz[i] = hit[0].z + clear - p[2]
        # also clear the funnel from outside
    return dz


X_m = place_mantle()
pinned_m = np.zeros(len(P2), bool)
pinned_m[vkind == 1] = True
pinned_m[[0]] = True              # the right panel's top corner (on the neck)
dz = lift(X_m, pinned_m)
# smooth the lift over the mesh (max of raw and smoothed) so the pre-shape stays a smooth surface
adj = [[] for _ in range(len(P2))]
for t in TRI:
    for a_, b_ in ((0, 1), (1, 2), (2, 0)):
        adj[t[a_]].append(t[b_]); adj[t[b_]].append(t[a_])
dzs = dz.copy()
for _ in range(15):
    dzs = np.array([0.5 * dzs[i] + 0.5 * np.mean(dzs[adj[i]]) if adj[i] else dzs[i] for i in range(len(dzs))])
    dzs = np.maximum(dzs, dz)
dzs[pinned_m] = 0.0
X_m[:, 2] += dzs
REPORT["preshape_lift_max_m"] = float(dzs.max())

# lining placement: top curve, rows scaled about the axis
lt_len = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(lt, axis=0), axis=1))])
# the lining starts as a flat vertical panel in front of the legs (the flat pattern itself); its top edge is then
# carried onto the chest curve by the same animated pins as the gather
ltop = np.nonzero(lvkind == 1)[0]
ltop = ltop[np.argsort(LP2[ltop, 0])]            # his right (-X) first, matching lt (phi = -80 first)
lx0, lx1 = LP2[ltop, 0].min(), LP2[ltop, 0].max()
X_l = np.zeros((len(LP2), 3))
for i in range(len(LP2)):
    rr_, aa_ = math.hypot(LP2[i, 0], LP2[i, 1]), math.atan2(LP2[i, 1], LP2[i, 0])
    t = (aL1 - aa_) / thetaL                          # 0 at his right edge .. 1 at his left edge (along the top)
    t = min(max(t, 0.0), 1.0)
    pt = np.array([np.interp(t * Lc, lt_len, lt[:, k]) for k in range(3)])
    s_ = rr_ - rL                                      # depth below the top
    spread = (t - 0.5) * (rr_ * thetaL - Lc)          # the gore widens downwards (row length minus top length)
    j = min(int(t * (len(lt) - 1)), len(lt) - 2)
    tang = lt[j + 1] - lt[j]; tang[2] = 0.0; tang /= max(np.linalg.norm(tang), 1e-9)
    outw = np.array([pt[0], pt[1] - G.CY, 0.0]); outw /= max(np.linalg.norm(outw), 1e-9)
    X_l[i] = pt + np.array([0.0, 0.0, -s_]) + tang * spread + outw * (0.06 * s_)
lin_tgt = {}
pinned_l = lvkind == 1

# ------------------------------------------------------------------ gather rosette targets
# aim so that the finished button's centroid (~4.2 cm out along the surface normal) lands on CLASP_TARGET
x0, z0 = C.CLASP_TARGET
for _ in range(3):
    hit = col_tree.ray_cast(Vector((x0, -0.6, z0)), Vector((0, 1, 0)), 1.0)
    skin_pt = np.array(hit[0]); nrm = np.array(hit[1]); nrm /= np.linalg.norm(nrm)
    if nrm[1] > 0:
        nrm = -nrm
    x0 = C.CLASP_TARGET[0] - nrm[0] * 0.0575
    z0 = C.CLASP_TARGET[1] - nrm[2] * 0.0575
ring_c = skin_pt + nrm * 0.042            # in front of the right panel's top (it bridges off the funnel base)
ez = np.array([0, 0, 1.0]) - nrm[2] * nrm; ez /= np.linalg.norm(ez)
ex = np.array([1.0, 0, 0]) - nrm[0] * nrm - ez[0] * ez; ex /= np.linalg.norm(ex)
a0, a1 = C.GATHER_ARC_DEG
tgt = {}
glen = np.concatenate([[0], np.cumsum([np.linalg.norm(P2[gather[k + 1]] - P2[gather[k]]) for k in range(len(gather) - 1)])])
for k, vi in enumerate(gather):
    u = glen[k] / max(glen[-1], 1e-9)
    ang_ = math.radians(a0 + (a1 - a0) * u)
    depth = (0.006 if k % 2 else -0.006)
    tgt[vi] = ring_c + C.GATHER_RING_R * (math.cos(ang_) * ex + math.sin(ang_) * ez) + depth * nrm
# the right panel's edge is buttoned too: its edge vertices 5-11 cm below the neck go just behind the rosette
redge = [i for i in range(nloop) if loop_kind[i] == 5 and 0.025 <= Pr[i] - r_in <= RIGHT_EDGE_BUTTONED]
redge = sorted(redge, key=lambda i: Pr[i])
for k, vi in enumerate(redge):
    tgt[vi] = ring_c - nrm * 0.013 + ez * (0.008 - 0.012 * k)
pinned_m[redge] = True
REPORT["right_edge_buttoned"] = len(redge)
# the button itself (stage-1 kit mesh) is a collider from frame 1, seated where the assemble step puts it
with bpy.data.libraries.load(C.CLASP_BLEND, link=False) as (_src, _dst):
    _dst.objects = [C.CLASP_OBJECT]
clasp_col = _dst.objects[0]
sc.collection.objects.link(clasp_col)
_back = ring_c + nrm * 0.011
_xa = ex.copy()
if np.dot(np.cross(_xa, ez), nrm) < 0:
    _xa = -_xa
clasp_col.matrix_world = Matrix(((_xa[0], ez[0], nrm[0], _back[0]), (_xa[1], ez[1], nrm[1], _back[1]),
                                 (_xa[2], ez[2], nrm[2], _back[2]), (0, 0, 0, 1)))
clasp_col.modifiers.new("Collision", "COLLISION")
clasp_col.collision.thickness_outer = 0.002
clasp_col.collision.cloth_friction = 5.0
REPORT["ring"] = {"centre": ring_c.tolist(), "normal": nrm.tolist(), "skin_pt": skin_pt.tolist()}
pinned_m[gather] = True

# ------------------------------------------------------------------ cloth object (mantle + lining)
NM = len(P2)
XV = np.vstack([X_m, X_l])
FACES = [list(t) for t in TRI] + [list(t + NM) for t in LTRI]
me = bpy.data.meshes.new("BCV2_Drape")
me.from_pydata(XV.tolist(), [], FACES)
me.update()
ob = bpy.data.objects.new("BCV2_Drape", me)
sc.collection.objects.link(ob)
pin = ob.vertex_groups.new(name="PIN")
pin.add([int(i) for i in np.nonzero(pinned_m)[0]], 1.0, "REPLACE")
pin.add([int(i) + NM for i in np.nonzero(pinned_l)[0]], 1.0, "REPLACE")
ob.shape_key_add(name="Basis")
kb = ob.shape_key_add(name="Gather")
for vi, p in tgt.items():
    kb.data[vi].co = Vector(p)
for vi, p in lin_tgt.items():
    kb.data[vi + NM].co = Vector(p)
if A.pleats > 0:
    # rest shape = start shape + pressed pleats: a corrugation along the surface normal, periodic in the angle around
    # the wrap corner (pattern space), so the cloth's bending springs keep folds that radiate from the button
    Pc = pol(r_top(alpha_e), alpha_e)
    u_r = np.array([math.cos(alpha_e), math.sin(alpha_e)])
    da = 1e-4
    t_e = pol(r_top(alpha_e - da), alpha_e - da) - Pc; t_e /= np.linalg.norm(t_e)
    ang_r, ang_t = math.atan2(u_r[1], u_r[0]), math.atan2(t_e[1], t_e[0])
    span = (ang_t - ang_r + math.pi) % (2 * math.pi) - math.pi            # signed angle front edge -> top edge
    mg = math.radians(A.pleat_margin) * (1 if span > 0 else -1)
    a0_, a1_ = ang_r + mg, ang_r + span - mg
    VNm = np.zeros((NM, 3))
    for t in TRI:
        fn = np.cross(X_m[t[1]] - X_m[t[0]], X_m[t[2]] - X_m[t[0]])
        VNm[t] += fn
    VNm /= np.maximum(np.linalg.norm(VNm, axis=1, keepdims=True), 1e-12)
    pl_disp = np.zeros(NM)
    for i in range(NM):
        rel = P2[i] - Pc; d = float(np.hypot(*rel))
        if d < 0.03 or d > A.pleat_len or pinned_m[i]:
            continue
        th = math.atan2(rel[1], rel[0])
        u = ((th - a0_ + math.pi) % (2 * math.pi) - math.pi) / (a1_ - a0_)
        if not 0.0 <= u <= 1.0:
            continue
        amp = A.pleat_amp * min(1.0, d / 0.35) * (1.0 - C.smoothstep(0.6 * A.pleat_len, A.pleat_len, d)) * math.sin(math.pi * u) ** 0.5
        amp *= C.smoothstep(0.03, 0.10, d)
        pl_disp[i] = amp * math.sin(2 * math.pi * A.pleats * u)
    rk = ob.shape_key_add(name="Rest", from_mix=False)
    for i in range(NM):
        rk.data[i].co = Vector(tuple(X_m[i] + VNm[i] * pl_disp[i]))
    rk.value = 0.0
    REPORT["pleats"] = {"n": A.pleats, "amp": A.pleat_amp, "len": A.pleat_len, "sector_deg": math.degrees(abs(a1_ - a0_)),
                        "verts": int((pl_disp != 0).sum())}
    log("pleats", REPORT["pleats"])
kb.value = 0.0; kb.keyframe_insert("value", frame=5)
kb.value = 1.0; kb.keyframe_insert("value", frame=45)
# floor
flm = bpy.data.meshes.new("BCV2_Floor"); bmf = bmesh.new(); bmesh.ops.create_grid(bmf, x_segments=1, y_segments=1, size=4); bmf.to_mesh(flm); bmf.free()
floor = bpy.data.objects.new("BCV2_Floor", flm); sc.collection.objects.link(floor); floor.location = (0, 0, -0.004)
floor.modifiers.new("Collision", "COLLISION"); floor.collision.thickness_outer = 0.001; floor.collision.cloth_friction = 8.0
floor.hide_render = True

cm = ob.modifiers.new("Cloth", "CLOTH")
s = cm.settings
s.quality = 8; s.mass = A.mass; s.air_damping = 1.0
s.tension_stiffness = 40; s.compression_stiffness = 40; s.shear_stiffness = 20; s.bending_stiffness = A.bending
s.vertex_group_mass = "PIN"; s.pin_stiffness = 1.0
if A.pleats > 0:
    s.rest_shape_key = ob.data.shape_keys.key_blocks["Rest"]
cc = cm.collision_settings
cc.distance_min = 0.006; cc.collision_quality = 5
cc.use_self_collision = True; cc.self_distance_min = 0.004; cc.self_friction = 5.0
cm.point_cache.frame_start = 1; cm.point_cache.frame_end = A.frames
sc.frame_start = 1; sc.frame_end = A.frames
per = []
if not A.no_sim:
    t1 = time.time()
    for f in range(1, A.frames + 1):
        ts = time.time(); sc.frame_set(f); per.append(time.time() - ts)
        if f % 40 == 0:
            log("frame", f, round(time.time() - t1, 1), "s")
    REPORT["sim_seconds"] = round(time.time() - t1, 1)
dg = bpy.context.evaluated_depsgraph_get()
ev = ob.evaluated_get(dg)
res = ev.to_mesh()
XR = np.array([v.co[:] for v in res.vertices])
ev.to_mesh_clear()
XR = XR @ np.array(ob.matrix_world)[:3, :3].T + np.array(ob.matrix_world)[:3, 3]

# ------------------------------------------------------------------ carry a fine drape onto the budget mesh
def map_pattern(Pc, Pf, Tf, Xf):
    """Position of each coarse pattern point in the fine drape: barycentric in the fine triangle containing it (the
    flat pattern space is shared), clamped to the nearest triangle for points on the boundary."""
    A_, B_, C_ = Pf[Tf[:, 0]], Pf[Tf[:, 1]], Pf[Tf[:, 2]]
    lo = np.minimum(np.minimum(A_, B_), C_); hi = np.maximum(np.maximum(A_, B_), C_)
    cell = 0.05
    bins = {}
    for t in range(len(Tf)):
        for ix in range(int(math.floor(lo[t, 0] / cell)), int(math.floor(hi[t, 0] / cell)) + 1):
            for iy in range(int(math.floor(lo[t, 1] / cell)), int(math.floor(hi[t, 1] / cell)) + 1):
                bins.setdefault((ix, iy), []).append(t)
    out = np.zeros((len(Pc), 3)); worst = 0.0
    for i, p in enumerate(Pc):
        k = (int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell)))
        cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                cand += bins.get((k[0] + dx, k[1] + dy), [])
        cand = np.array(sorted(set(cand)))
        a, b, c = A_[cand], B_[cand], C_[cand]
        v0, v1, v2 = b - a, c - a, p[None, :] - a
        d00 = (v0 * v0).sum(1); d01 = (v0 * v1).sum(1); d11 = (v1 * v1).sum(1); d20 = (v2 * v0).sum(1); d21 = (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        w1 = (d11 * d20 - d01 * d21) / den; w2 = (d00 * d21 - d01 * d20) / den; w0 = 1 - w1 - w2
        mn = np.minimum(np.minimum(w0, w1), w2)
        mn = np.where(np.isfinite(mn) & (np.abs(den) > 1e-14), mn, -1e9)
        j = int(np.argmax(mn))
        worst = min(worst, float(mn[j]))
        w = np.clip(np.array([w0[j], w1[j], w2[j]]), 0, None); w /= w.sum()
        t = Tf[cand[j]]
        out[i] = w[0] * Xf[t[0]] + w[1] * Xf[t[1]] + w[2] * Xf[t[2]]
    return out, worst


def foldover_of(Xv, faces):
    bm_ = bmesh.new()
    for p in Xv: bm_.verts.new(p)
    bm_.verts.ensure_lookup_table()
    for f in faces:
        try: bm_.faces.new([bm_.verts[i] for i in f])
        except ValueError: pass
    bm_.normal_update()
    ar = np.array([f.calc_area() for f in bm_.faces]); nr = np.array([f.normal[:] for f in bm_.faces]); ce = np.array([f.calc_center_median()[:] for f in bm_.faces])
    bm_.free()
    sel = (ce[:, 2] > 0.3) & (ce[:, 2] < 1.3) & (ce[:, 1] < -0.092)
    mj = np.sign((nr[sel, 1] * ar[sel]).sum())
    return float(ar[sel][np.sign(nr[sel, 1]) == -mj].sum() / max(ar[sel].sum(), 1e-9))


if A.fine > 0:
    NMf = NM
    XRf = XR
    FACES_f = FACES
    Pf_m, Tf_m, Pf_l, Tf_l = P2, TRI, LP2, LTRI
    P2, TRI, vkind, Pr, Pa = COARSE["P2"], COARSE["TRI"], COARSE["vkind"], COARSE["Pr"], COARSE["Pa"]
    loop_kind, nloop, gather = COARSE["loop_kind"], COARSE["nloop"], COARSE["gather"]
    LP2, LTRI, lvkind = COARSE["LP2"], COARSE["LTRI"], COARSE["lvkind"]
    Xc_m, wm = map_pattern(P2, Pf_m, Tf_m, XRf[:NMf])
    Xc_l, wl = map_pattern(LP2, Pf_l, Tf_l, XRf[NMf:])
    REPORT["fine_drape"] = {"front_foldover": foldover_of(XRf, FACES_f), "carry_worst_bary": [wm, wl]}
    log("fine drape", REPORT["fine_drape"])
    NM = len(P2)
    XR = np.vstack([Xc_m, Xc_l])
    FACES = [list(t) for t in TRI] + [list(t + NM) for t in LTRI]
    X_m = place_mantle()
    X_l = np.zeros((len(LP2), 3))
    np.savez_compressed(os.path.join(C.WORK_DIR, "drape_%s_fine.npz" % A.tag), P2=Pf_m, TRI=Tf_m, LP2=Pf_l, LTRI=Tf_l, XR=XRf,
                        NM=NMf)

# ------------------------------------------------------------------ checks on the drape
d_in = []
for p in XR:
    h_ = skin_tree.find_nearest(Vector(p), 0.3)
    if h_[0] is None:
        d_in.append(1.0); continue
    sd = (Vector(p) - h_[0]).dot(h_[1])
    d_in.append(h_[3] if sd >= 0 else -h_[3])
d_in = np.array(d_in)
tri_all = np.array(FACES)
rbm = bmesh.new()
for p in XR: rbm.verts.new(p)
rbm.verts.ensure_lookup_table()
for f in FACES:
    try: rbm.faces.new([rbm.verts[i] for i in f])
    except ValueError: pass
rbm.faces.ensure_lookup_table(); rbm.normal_update()
tree = BVHTree.FromBMesh(rbm)
fv = [set(v.index for v in f.verts) for f in rbm.faces]
selfx = [(i, j) for i, j in tree.overlap(tree) if i < j and not (fv[i] & fv[j])]
# strain vs the flat pattern
P_all2 = np.vstack([P2, LP2])
E = set()
for f in FACES:
    for a_, b_ in ((0, 1), (1, 2), (2, 0)):
        E.add((min(f[a_], f[b_]), max(f[a_], f[b_])))
E = np.array(sorted(E))
flat = np.linalg.norm(P_all2[E[:, 0]] - P_all2[E[:, 1]], axis=1)
drp = np.linalg.norm(XR[E[:, 0]] - XR[E[:, 1]], axis=1)
strain = drp / np.maximum(flat, 1e-9)
_w = int(np.argmax(strain))
REPORT["worst_strain_edge"] = {"verts": E[_w].tolist(), "pos": XR[E[_w][0]].tolist(), "kinds": [int(vkind[v]) if v < NM else 100 + int(lvkind[v - NM]) for v in E[_w]]}
_nt = len(TRI)
REPORT["selfx_detail"] = {"mm": sum(1 for i, j in selfx if i < _nt and j < _nt), "ml": sum(1 for i, j in selfx if (i < _nt) != (j < _nt)),
                          "ll": sum(1 for i, j in selfx if i >= _nt and j >= _nt),
                          "where_ml": [[list(map(float, rbm.faces[i].calc_center_median())), list(map(float, rbm.faces[j].calc_center_median()))] for i, j in selfx if (i < _nt) != (j < _nt)][:8],
                          "where_mm": [list(map(float, rbm.faces[i].calc_center_median())) for i, j in selfx if i < _nt and j < _nt][:6],
                          "where": [cenf_ for cenf_ in [list(map(float, rbm.faces[i].calc_center_median())) for i, j in selfx[:6]]]}
# front fold-over (the pilot / v2m metric) on mantle faces
area = np.array([f.calc_area() for f in rbm.faces]); nrmf = np.array([f.normal[:] for f in rbm.faces]); cenf = np.array([f.calc_center_median()[:] for f in rbm.faces])
selz = (cenf[:, 2] > 0.3) & (cenf[:, 2] < 1.3) & (cenf[:, 1] < -0.042 - 0.05)
ny = nrmf[selz, 1]; fa = area[selz]; mj = np.sign((ny * fa).sum())
fold = float(fa[np.sign(ny) == -mj].sum() / max(fa.sum(), 1e-9))
hem_z = XR[:NM][vkind == 4][:, 2]
_hp = XR[:NM][vkind == 4]
_az = np.degrees(np.arctan2(_hp[:, 0], -(_hp[:, 1] + 0.01)))
REPORT["hem_z_by_az30"] = {int(a0): float(np.median(_hp[(_az >= a0) & (_az < a0 + 30), 2])) if ((_az >= a0) & (_az < a0 + 30)).any() else None for a0 in range(-180, 180, 30)}
REPORT["drape"] = {"inside_skin_gt1mm": int((d_in < -0.001).sum()), "min_dist_cm": float(d_in.min() * 100),
                   "air_cm_p5_p50": [float(np.percentile(d_in[d_in < 0.05] * 100, 5)) if (d_in < 0.05).any() else None,
                                     float(np.percentile(d_in[d_in < 0.05] * 100, 50)) if (d_in < 0.05).any() else None],
                   "self_intersections": len(selfx), "strain_p5_p50_p95_max": [float(np.percentile(strain, q)) for q in (5, 50, 95, 100)],
                   "front_foldover": fold, "hem_z_min_p50": [float(hem_z.min()), float(np.median(hem_z))],
                   "hem_on_floor_frac": float((hem_z < 0.006).mean()), "zmax": float(XR[:, 2].max()),
                   "sec_per_frame_mean_max": [float(np.mean(per)) if per else 0, float(np.max(per)) if per else 0]}
log("drape", json.dumps(REPORT["drape"]))

# ------------------------------------------------------------------ save
out_npz = os.path.join(C.WORK_DIR, "drape_%s.npz" % A.tag)
np.savez_compressed(out_npz, P2=P2, TRI=TRI, vkind=vkind, fregion=fregion, XR_m=XR[:NM], X0_m=X_m, Pr=Pr, Pa=Pa,
                    LP2=LP2, LTRI=LTRI, lvkind=lvkind, XR_l=XR[NM:], X0_l=X_l,
                    F_verts=F.verts, F_faces=np.array(F.faces), F_u=F.ucoord, F_v=F.vcoord, F_ncol=F.ncol, F_rows=F.nrows_total,
                    gather=np.array(gather), ring_c=ring_c, ring_n=nrm, ring_ex=ex, ring_ez=ez,
                    seam=seam_pts, loop_n=nloop, e0=e0, e1=e1)
REPORT["npz"] = out_npz
REPORT["total_seconds"] = round(time.time() - T0, 1)
json.dump(REPORT, open(os.path.join(C.WORK_DIR, "drape_%s.json" % A.tag), "w"), indent=1, default=float)

if not A.no_preview:
    res_me = bpy.data.meshes.new("BCV2_DrapeResult"); res_me.from_pydata(XR.tolist(), [], FACES)
    for p in res_me.polygons: p.use_smooth = True
    rob = bpy.data.objects.new("BCV2_DrapeResult", res_me); sc.collection.objects.link(rob)
    ob.hide_render = True
    sc.render.engine = "BLENDER_WORKBENCH"; sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 600, 900
    for o in bpy.data.objects:
        if o.type == "MESH":
            o.color = (0.16, 0.16, 0.18, 1)
    for o in (fit["body"], fit["head"]):
        o.color = (0.8, 0.68, 0.6, 1)
    fit["hair_proxy"].color = (0.1, 0.08, 0.07, 1)
    if fit.get("head_parts"): fit["head_parts"].hide_render = True
    fob.color = (0.2, 0.2, 0.23, 1)
    camd = bpy.data.cameras.new("BCV2_Cam"); camd.type = "ORTHO"; camd.ortho_scale = 2.05
    cam = bpy.data.objects.new("BCV2_Cam", camd); sc.collection.objects.link(cam); sc.camera = cam
    shots = {}
    for name, yaw, zc, osc in (("front", 0, 0.97, 2.05), ("q34", -40, 0.97, 2.05), ("side", -90, 0.97, 2.05), ("back", 180, 0.97, 2.05),
                               ("q34l", 40, 0.97, 2.05), ("jin", 12, 1.36, 1.10)):
        a = math.radians(yaw)
        camd.ortho_scale = osc
        cam.location = (5 * math.sin(a), -5 * math.cos(a), zc); cam.rotation_euler = (math.radians(90), 0, a)
        p = os.path.join(C.WORK_DIR, "preview_%s_%s.png" % (A.tag, name)); sc.render.filepath = p
        bpy.ops.render.render(write_still=True); shots[name] = p
    if A.fine > 0:
        fme_ = bpy.data.meshes.new("BCV2_DrapeFine"); fme_.from_pydata(XRf.tolist(), [], FACES_f)
        for p in fme_.polygons: p.use_smooth = True
        fob_ = bpy.data.objects.new("BCV2_DrapeFine", fme_); sc.collection.objects.link(fob_); fob_.color = (0.16, 0.16, 0.18, 1)
        rob.hide_render = True
        for name, yaw, zc, osc in (("jinfine", 12, 1.36, 1.10), ("frontfine", 0, 0.97, 2.05)):
            a = math.radians(yaw); camd.ortho_scale = osc
            cam.location = (5 * math.sin(a), -5 * math.cos(a), zc); cam.rotation_euler = (math.radians(90), 0, a)
            p = os.path.join(C.WORK_DIR, "preview_%s_%s.png" % (A.tag, name)); sc.render.filepath = p
            bpy.ops.render.render(write_still=True); shots[name] = p
    REPORT["previews"] = shots
    # fold-fan proxy (bcv2_fanscore = the v2m_jin_score detector) on the v2m 'jin' camera, cloak only, workbench
    import bcv2_fanscore as FS
    from bpy_extras.object_utils import world_to_camera_view
    camp = bpy.data.cameras.new("BCV2_CamP"); camp.lens = 85.0; camp.sensor_fit = "VERTICAL"; camp.sensor_height = 24
    cop = bpy.data.objects.new("BCV2_CamP", camp); sc.collection.objects.link(cop); sc.camera = cop
    tgt_ = Vector((0.0, 0.0, 1.358)); dist_ = 1.10 / (24.0 / 85.0); yw, pt = math.radians(12.0), math.radians(3.0)
    dv = Vector((math.sin(yw) * math.cos(pt), -math.cos(yw) * math.cos(pt), math.sin(pt))) * dist_
    cop.location = tgt_ + dv; cop.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
    sc.render.resolution_x, sc.render.resolution_y = 605, 908
    sc.render.film_transparent = True
    for o in bpy.data.objects:
        if o.type == "MESH" and o.name not in ("BCV2_DrapeResult", "BCV2_DrapeFine", "BCV2_Funnel", clasp_col.name):
            o.hide_render = True
    bpy.context.view_layer.update()
    cpt = Vector(tuple(ring_c + nrm * 0.02))
    ndc = world_to_camera_view(sc, cop, cpt); cx_, cy_ = ndc.x * 605, (1 - ndc.y) * 908
    ppm = 908 * 85.0 / (24.0 * (cpt - cop.location).length)
    fan = {}
    for which in (("coarse", "BCV2_DrapeResult"), ("fine", "BCV2_DrapeFine")):
        ob_ = bpy.data.objects.get(which[1])
        if ob_ is None:
            continue
        for nm_ in ("BCV2_DrapeResult", "BCV2_DrapeFine"):
            if bpy.data.objects.get(nm_):
                bpy.data.objects[nm_].hide_render = nm_ != which[1]
        pth = os.path.join(C.WORK_DIR, "preview_%s_jinp_%s.png" % (A.tag, which[0])); sc.render.filepath = pth
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(pth); w_, h_ = im.size; px = np.empty(w_ * h_ * 4, np.float32); im.pixels.foreach_get(px)
        px = px.reshape(h_, w_, 4)[::-1].astype(np.float64); bpy.data.images.remove(im)
        lum_ = (px[..., 0] * 0.2126 + px[..., 1] * 0.7152 + px[..., 2] * 0.0722) * 255
        fan[which[0]] = FS.fan_score(lum_, px[..., 3] > 0.5, cx_, cy_, ppm)
    REPORT["fan_proxy"] = fan
    log("fan", json.dumps({k: {r: (v[r]["cross_-50_10"], v[r]["fan_15_120"], round(v[r]["fan_spread_deg"])) for r in v} for k, v in fan.items()}))
    json.dump(REPORT, open(os.path.join(C.WORK_DIR, "drape_%s.json" % A.tag), "w"), indent=1, default=float)
log("DONE", round(time.time() - T0, 1), "s")
