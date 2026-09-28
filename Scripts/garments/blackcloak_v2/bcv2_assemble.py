"""BlackCloak_MH_v2 stage 2, step 2: turn the drape into the garment work file's pieces (Blender 5.2 headless).

    blender -b Assets/Garments/BlackCloak_MH_v2.blend --factory-startup --python Scripts/garments/blackcloak_v2/bcv2_assemble.py -- --tag r1

Opens the work file made by Scripts/garments/new_garment.py (lock BlackCloak_MH_v2 must be held by claude), removes
every earlier BCV2 piece and rebuilds from WorkFiles/BlackCloak_MH_v2/build/drape_<tag>.npz:

GARMENT (skinned):   BCV2_Yoke   - the wrap round the button above the pin line (+ one face ring overlapping the
                                   cloth part 3 mm outside it, so the seam never opens and no vertex is shared)
                     BCV2_Funnel - the stand-up funnel with its rolled rim
                     BCV2_Clasp  - the stage-1 button (garment_hard), seated on the gathered rosette
GARMENT_SIM (cloth): BCV2_Sim    - the mantle below the pin line + the lining (one material, one section)
Every visible cut edge gets a 1.1-2.4 cm fray fringe row (UV1 "UV1_Fray": U along the edge in 0.45 m tiles, V from
the cut into the stage-1 fray strip; the wool material reads its alpha there). UV0 = flat pattern metres / 5.85 m
(unique, non-overlapping; garment_unique_uvs = True). CLOTH_Pin: 1.0 within 9 cm (pattern distance) of the neck seam /
the yoke seam / the lining top, then a linear ramp to 0 over 30 cm (-> PinMask -> Unreal MaxDistance).
The armature is left at rest and the file is saved (the build never saves it).
"""
import sys, os, json, math, argparse, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bcv2_common as C
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from pipeline import garment_helpers as gh
from pipeline import garment_qa as gq
from pipeline.lock import assert_owner
import bcv2_material as BM

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="r1")
ap.add_argument("--no-save", action="store_true")
A = ap.parse_args(argv)
T0 = time.time()
assert_owner("BlackCloak_MH_v2", "claude")
if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(os.path.abspath(C.WORK_BLEND)):
    raise RuntimeError("open %s, not %s" % (C.WORK_BLEND, bpy.data.filepath))
D = np.load(os.path.join(C.WORK_DIR, "drape_%s.npz" % A.tag))
REPORT = {"tag": A.tag}
rng = np.random.default_rng(20260927)


def log(*a):
    print("BCV2A", *a, flush=True)


sc = bpy.context.scene
lock = gq.load_base_lock()
arm = bpy.data.objects[lock["armature_object"]]
gq.clear_pose(arm)
cols = gh.ensure_collections()

# ------------------------------------------------------------------ clear earlier pieces
for cname in (gh.GARMENT_COLLECTION, gh.SIM_COLLECTION, gh.HELPER_COLLECTION):
    for o in list(cols[cname].objects):
        if cname == gh.HELPER_COLLECTION and not o.name.startswith("BCV2_"):
            continue
        bpy.data.objects.remove(o, do_unlink=True)
for m in list(bpy.data.meshes):
    if m.users == 0:
        bpy.data.meshes.remove(m)
for m in list(bpy.data.materials):
    if m.name.startswith("M_BlackCloakV2") and m.users == 0:
        bpy.data.materials.remove(m)

# ------------------------------------------------------------------ materials (work-file copies of the stage-1 look)
P = BM.load_params()


def wool_material():
    m = BM.cloth_material(P, name=C.MAT_WOOL, uv_map=C.UV0, overrides={"uv_scale": C.UV_SCALE})
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = C.UV1
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(os.path.join(C.TEX_DIR, P["textures"]["fray_bca"]), check_existing=True)
    t.image.alpha_mode = "STRAIGHT"
    nt.links.new(uv.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
    try:
        m.surface_render_method = "DITHERED"
    except Exception:
        pass
    m["bcv2_fray_alpha"] = "UV1_Fray -> T_BlackCloakV2_Fray_BCA.A (Masked, clip 0.5 in Unreal)"
    return m


MW = wool_material()
MCL = BM.clasp_material(P, name=C.MAT_CLASP)
for img in bpy.data.images:
    if img.packed_file is None and img.name.startswith("T_BlackCloakV2"):
        stem = os.path.splitext(img.name)[0].lower()
        if stem.endswith(("_orm", "_n")):
            img.colorspace_settings.name = "Non-Color"

# ------------------------------------------------------------------ helpers


def vertex_normals(X, F):
    n = np.zeros_like(X)
    for f in F:
        a, b, c = X[f[0]], X[f[1]], X[f[2]]
        fn = np.cross(b - a, c - a)
        for v in f:
            n[v] += fn
    L = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(L, 1e-12)


def outward_sign(X, F):
    """+1 if face normals mostly point away from the neck axis / body, else -1."""
    s = 0.0
    for f in F:
        a, b, c = X[f[0]], X[f[1]], X[f[2]]
        fn = np.cross(b - a, c - a)
        cen = (a + b + c) / 3
        rad = np.array([cen[0], cen[1] + 0.01, 0.0])
        s += float(np.dot(fn, rad))
    return 1.0 if s >= 0 else -1.0


def boundary_edges(F):
    cnt = {}
    for fi, f in enumerate(F):
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            key = (min(a, b), max(a, b))
            cnt.setdefault(key, []).append((fi, a, b))
    return {k: v[0] for k, v in cnt.items() if len(v) == 1}


def chains_from_edges(edges):
    """edges: list of (a, b) directed along the face; returns ordered chains (lists of vertex ids)."""
    nxt = {a: b for a, b in edges}
    prv = {b: a for a, b in edges}
    seen = set()
    chains = []
    starts = [a for a in nxt if a not in prv] + [a for a in nxt]
    for s in starts:
        if s in seen:
            continue
        ch = [s]; seen.add(s)
        while ch[-1] in nxt and nxt[ch[-1]] not in seen:
            ch.append(nxt[ch[-1]]); seen.add(ch[-1])
        if ch[-1] in nxt and nxt[ch[-1]] == ch[0]:
            ch.append(ch[0])
        chains.append(ch)
    return chains


def add_fringe(X, F, UVp, kinds, allowed, face_ok=None, seed=0):
    """Append a fray fringe row outside the boundary edges whose two vertices have kinds in ``allowed``.
    X (n,3) coords, F list of tris, UVp (n,2) pattern metres, kinds (n,). Returns new X, F, UVp, uv1 (n,2),
    parent (n,) (fringe vertex -> its edge vertex, -1 otherwise), fringe face flags."""
    bnd = boundary_edges(F)
    use = []
    for key, (fi, a, b) in bnd.items():
        if kinds[a] in allowed and kinds[b] in allowed and (face_ok is None or face_ok[fi]):
            use.append((fi, a, b))
    edges = [(a, b) for fi, a, b in use]
    face_of = {(a, b): fi for fi, a, b in use}
    X = list(map(np.array, X)); UVp = list(map(np.array, UVp)); F = [list(f) for f in F]
    n0 = len(X)
    uv1 = [np.array([0.0, C.FRAY_BODY_V]) for _ in range(n0)]
    parent = [-1] * n0
    fringe_face = [False] * len(F)
    r = np.random.default_rng(seed)
    for ch in chains_from_edges(edges):
        closed = ch[0] == ch[-1]
        verts = ch[:-1] if closed else ch
        # per-vertex outward direction (in the surface) in 3-D and in the pattern
        d3 = {v: np.zeros(3) for v in verts}; d2 = {v: np.zeros(2) for v in verts}
        for a, b in zip(ch, ch[1:]):
            fi = face_of.get((a, b))
            if fi is None:
                continue
            c = [v for v in F[fi] if v not in (a, b)][0]
            e = X[b] - X[a]; mid = 0.5 * (X[a] + X[b])
            w = mid - X[c]; perp = w - e * np.dot(w, e) / max(np.dot(e, e), 1e-12)
            perp /= max(np.linalg.norm(perp), 1e-12)
            e2 = UVp[b] - UVp[a]; w2 = 0.5 * (UVp[a] + UVp[b]) - UVp[c]; p2 = w2 - e2 * np.dot(w2, e2) / max(np.dot(e2, e2), 1e-12)
            p2 /= max(np.linalg.norm(p2), 1e-12)
            for v in (a, b):
                if v in d3:
                    d3[v] += perp; d2[v] += p2
        arc = 0.0
        newid = {}
        for k, v in enumerate(verts):
            if k > 0:
                arc += float(np.linalg.norm(X[v] - X[verts[k - 1]]))
            dd = d3[v]
            if X[v][2] < 0.012:                     # hem on the floor: fray lies on the floor
                dd = np.array([dd[0], dd[1], 0.0])
            dd /= max(np.linalg.norm(dd), 1e-12)
            f_len = float(r.uniform(0.011, 0.024))
            p = X[v] + dd * f_len
            if X[v][2] < 0.012:
                p[2] = max(X[v][2], 0.002)
            q = UVp[v] + d2[v] / max(np.linalg.norm(d2[v]), 1e-12) * f_len
            X.append(p); UVp.append(q)
            uv1[v] = np.array([arc / C.TILE_M, C.FRAY_EDGE_V])
            uv1.append(np.array([arc / C.TILE_M, C.FRAY_EDGE_V - f_len / C.FRAY_CARD_M]))
            parent.append(v)
            newid[v] = len(X) - 1
        for a, b in zip(ch, ch[1:]):
            if (a, b) not in face_of:
                continue
            a2, b2 = newid[a], newid[b]
            # keep the orientation of the adjacent face (it runs a -> b): the fringe runs b -> a
            if np.linalg.norm(X[b] - X[a2]) <= np.linalg.norm(X[a] - X[b2]):
                F += [[b, a, a2], [b, a2, b2]]
            else:
                F += [[b, a, b2], [a, a2, b2]]
            fringe_face += [True, True]
    return np.array(X), F, np.array(UVp), np.array(uv1), np.array(parent), np.array(fringe_face)


def make_object(name, X, F, collection, uv0, uv1, material, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in X], [], [list(map(int, f)) for f in F])
    me.update()
    l0 = me.uv_layers.new(name=C.UV0)
    l1 = me.uv_layers.new(name=C.UV1)
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.loops[li].vertex_index
            l0.data[li].uv = uv0(poly.index, li, v)
            l1.data[li].uv = uv1(poly.index, li, v)
        poly.use_smooth = smooth
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    return ob


# ------------------------------------------------------------------ mantle: split yoke / cloth
P2 = D["P2"]; TRI = D["TRI"]; vkind = D["vkind"].copy(); freg = D["fregion"]; XM = D["XR_m"]
nloop = int(D["loop_n"])
vkind[0] = 1               # the right panel's top corner sits on the neck seam
seam_v = set(np.nonzero(np.isin(vkind, [7, 8, 9]))[0].tolist())
sgn = outward_sign(XM, TRI)
if sgn < 0:
    TRI = TRI[:, [0, 2, 1]]
VN = vertex_normals(XM, TRI)
Fy = [list(t) for t, r_ in zip(TRI, freg) if r_ == 1]
Fs = [list(t) for t, r_ in zip(TRI, freg) if r_ == 0]
# the yoke and the cloth part meet on the seam; the yoke's copies of the seam vertices float 0.02 mm off the
# surface (no shared or coincident vertices, no overlap to intersect). The seam runs at z ~1.36-1.40, where the
# yoke's height blend is (almost) all spine_05, the bone the cloth part rides, so it stays closed in game.
Fyall = Fy
yv = sorted(set(v for f in Fyall for v in f))
ymap = {v: i for i, v in enumerate(yv)}
XY = np.array([XM[v] + VN[v] * (2e-5 if v in seam_v else 0.0) for v in yv])
FY = [[ymap[v] for v in f] for f in Fyall]
UY = np.array([P2[v] for v in yv])
KY = np.array([vkind[v] for v in yv])
face_in_fy = np.array([True] * len(Fy))
# yoke fringe: the wrap's free top edge and the front edge (not the gathered part, not the neck, not the overlap)
XY2, FY2, UY2, U1Y, parY, frY = add_fringe(XY, FY, UY, KY, {2, 3, 8, 9}, face_ok=face_in_fy, seed=1)

# cloth part: mantle below the pin line (+ fringe) + lining
sv = sorted(set(v for f in Fs for v in f))
smap = {v: i for i, v in enumerate(sv)}
XS = np.array([XM[v] for v in sv])
FS = [[smap[v] for v in f] for f in Fs]
US = np.array([P2[v] for v in sv])
KS = np.array([vkind[v] for v in sv])
XS2, FS2, US2, U1S, parS, frS = add_fringe(XS, FS, US, KS, {2, 3, 4, 5, 8, 9}, seed=2)
LP2 = D["LP2"]; LTRI = D["LTRI"]; XL = D["XR_l"]; lvk = D["lvkind"]
if outward_sign(XL, LTRI) < 0:
    LTRI = LTRI[:, [0, 2, 1]]
nS = len(XS2)
S = C.S_UV
MANTLE_OFF = np.array([0.33, 0.33])
YOKE_OFF = MANTLE_OFF + np.array([1.0, 0.0])
LIN_OFF = np.array([-0.20, -0.05])

# ---- CLOTH_Pin weights (pattern-space distance from the attachments: neck seam, yoke seam, lining top)
att = [P2[v] for v in range(len(P2)) if vkind[v] in (1, 7, 8, 9)]
for f in TRI:
    for a_, b_ in ((0, 1), (1, 2), (2, 0)):
        if vkind[f[a_]] in (1, 7, 8, 9) and vkind[f[b_]] in (1, 7, 8, 9):
            for t in (0.25, 0.5, 0.75):
                att.append(P2[f[a_]] * (1 - t) + P2[f[b_]] * t)
att = np.array(att)
PIN_FULL, PIN_RAMP = 0.09, 0.30


def pin_w(d):
    return 1.0 if d <= PIN_FULL else max(0.0, 1.0 - (d - PIN_FULL) / PIN_RAMP)


wS = []
for i in range(nS):
    src = parS[i] if parS[i] >= 0 else i
    wS.append(pin_w(float(np.sqrt(((att - US2[src]) ** 2).sum(1)).min())))
ltop = LP2[lvk == 1]
for i in range(len(XL)):
    wS.append(pin_w(float(np.sqrt(((ltop - LP2[i]) ** 2).sum(1)).min())))

PIECE = {
    "Y": {"X": XY2.copy(), "F": [list(f) for f in FY2], "UV0": UY2 / S + YOKE_OFF, "UV1": U1Y,
          "fringe": list(frY), "lining": np.zeros(len(XY2), bool)},
    "S": {"X": np.vstack([XS2, XL]), "F": [list(f) for f in FS2] + [[int(v) + nS for v in f] for f in LTRI],
          "UV0": np.vstack([US2 / S + MANTLE_OFF, LP2 / S + LIN_OFF]),
          "UV1": np.vstack([U1S, np.tile([0.0, C.FRAY_BODY_V], (len(XL), 1))]),
          "fringe": list(frS) + [False] * len(LTRI), "lining": np.concatenate([np.zeros(nS, bool), np.ones(len(XL), bool)]),
          "pin": np.array(wS)},
}

# ------------------------------------------------------------------ funnel arrays
FV = D["F_verts"]; FF = D["F_faces"]; ncol = int(D["F_ncol"]); Fu = D["F_u"]; Fv = D["F_v"]
fun_tris = [[f[0], f[1], f[2]] for f in FF] + [[f[0], f[2], f[3]] for f in FF]
fun_tree = BVHTree.FromPolygons([tuple(map(float, p)) for p in FV], [tuple(f) for f in FF])
fun_zb = FV[:ncol, 2]


def funnel_signed(p):
    h_ = fun_tree.find_nearest(Vector(p), 0.1)
    if h_[0] is None:
        return None, None
    n = np.array(h_[1])
    c = np.array(h_[0])
    rad = np.array([c[0], c[1] + 0.01, 0.0])
    if np.dot(n, rad) < 0:
        n = -n
    return float(np.dot(np.array(p) - c, n)), n


# ------------------------------------------------------------------ seam allowance along the sewn neck
SEAM_ALLOWANCE = False   # r1: off (it grazed the funnel's faceted wall: 32 intersecting pairs)
# (a 1.4 cm band of the mantle turned up against the funnel wall above the seam: a real seam allowance; it also
#  closes the sight line between the funnel wall and the mantle's neck edge, which sits 4 mm off the wall)
kS = np.concatenate([KS, np.full(len(XS2) - len(XS), 20), np.full(len(XL), 30)])
bndS = boundary_edges(PIECE["S"]["F"])
neck_edges = [(fi, a_, b_) for (fi, a_, b_) in bndS.values() if kS[a_] == 1 and kS[b_] == 1] if SEAM_ALLOWANCE else []
new_id = {}
Xs_ = list(PIECE["S"]["X"]); U0s = list(PIECE["S"]["UV0"]); U1s = list(PIECE["S"]["UV1"])
pin_ = list(PIECE["S"]["pin"]); lin_ = list(PIECE["S"]["lining"])
for fi, a_, b_ in neck_edges:
    for v in (a_, b_):
        if v in new_id:
            continue
        p_ = PIECE["S"]["X"][v]
        d_, n_ = funnel_signed(p_)
        if d_ is None:
            continue
        up = np.array([0.0, 0.0, 1.0]) - n_ * n_[2]; up /= max(np.linalg.norm(up), 1e-9)
        q_ = p_ - n_ * (d_ - 0.0012) + up * 0.014
        uvp = PIECE["S"]["UV0"][v]
        c_uv = MANTLE_OFF                      # the pattern centre (before the atlas shift): pull the UV towards it
        dirv = (c_uv - uvp); dirv /= max(np.linalg.norm(dirv), 1e-9)
        Xs_.append(q_); U0s.append(uvp + dirv * 0.014 / S); U1s.append(np.array([0.0, C.FRAY_BODY_V]))
        pin_.append(1.0); lin_.append(False)
        new_id[v] = len(Xs_) - 1
sa_faces = []
for fi, a_, b_ in neck_edges:
    if a_ in new_id and b_ in new_id:
        sa_faces += [[b_, a_, new_id[a_]], [b_, new_id[a_], new_id[b_]]]
PIECE["S"]["X"] = np.array(Xs_); PIECE["S"]["UV0"] = np.array(U0s); PIECE["S"]["UV1"] = np.array(U1s)
PIECE["S"]["pin"] = np.array(pin_); PIECE["S"]["lining"] = np.array(lin_, bool)
PIECE["S"]["F"] += sa_faces
PIECE["S"]["fringe"] += [False] * len(sa_faces)
REPORT["seam_allowance_tris"] = len(sa_faces)
SA_SET = set(new_id.values())

# ------------------------------------------------------------------ clasp: the stage-1 button on the rosette
with bpy.data.libraries.load(C.CLASP_BLEND, link=False) as (src, dst):
    dst.objects = [C.CLASP_OBJECT]
cl = dst.objects[0]
cl.data.materials.clear()
cl.data.materials.append(MCL)
for m in list(bpy.data.materials):
    if m.users == 0 and m.name.startswith("M_BlackCloakV2_Clasp") and m is not MCL:
        bpy.data.materials.remove(m)
rc = np.array(D["ring_c"]); rn = np.array(D["ring_n"]); rex = np.array(D["ring_ex"]); rez = np.array(D["ring_ez"])
CLASP_R = C.CLASP_DIAM / 2
back = rc + rn * 0.011           # above the rosette's pleats (+-6 mm)
xa, ya, za = rex.copy(), rez.copy(), rn.copy()
if np.dot(np.cross(xa, ya), za) < 0:
    xa = -xa
Mx = Matrix(((xa[0], ya[0], za[0], back[0]), (xa[1], ya[1], za[1], back[1]), (xa[2], ya[2], za[2], back[2]), (0, 0, 0, 1)))
cl.matrix_world = Mx
cl.data.transform(cl.matrix_world)
cl.matrix_world = Matrix.Identity(4)
CLV = np.array([v.co[:] for v in cl.data.vertices])
CLF = [list(p.vertices) for p in cl.data.polygons]


def cyl(p):
    rel = np.asarray(p) - back
    h = rel @ rn
    r = np.linalg.norm(rel - np.outer(h, rn) if rel.ndim > 1 else rel - h * rn, axis=-1)
    return r, h


# (the button was a collider in the drape; the few faces next to the pinned rosette that still cross it are
#  handled below by seating the button just far enough out)
# ------------------------------------------------------------------ mantle outside the funnel
pushed = 0
for key in ("Y", "S"):
    X = PIECE[key]["X"]
    for i in range(len(X)):
        if PIECE[key]["lining"][i] or X[i][2] < fun_zb.min() - 0.01 or (key == "S" and i in SA_SET):
            continue
        d, n = funnel_signed(X[i])
        if d is not None and d < 0.004 and d > -0.03:
            X[i] = X[i] + n * (0.004 - d)
            pushed += 1
REPORT["mantle_verts_pushed_off_funnel"] = pushed
# the lining's top edge ends tucked 6 mm inside the funnel's lower edge (hidden; never through the wall)
_fphi = np.degrees(np.arctan2(FV[:ncol, 0], -(FV[:ncol, 1] + 0.01)))
tucked = 0
XS_ = PIECE["S"]["X"]
for i in np.nonzero(PIECE["S"]["lining"])[0]:
    p_ = XS_[i]
    ph = math.degrees(math.atan2(p_[0], -(p_[1] + 0.01)))
    k_ = int(np.argmin(np.abs(((_fphi - ph) + 180) % 360 - 180)))
    if p_[2] < fun_zb[k_] - 0.004:
        continue
    d, n = funnel_signed(p_)
    if d is not None and d > -0.006:
        XS_[i] = p_ + n * (-0.006 - d)
        tucked += 1
REPORT["lining_verts_kept_inside_funnel"] = tucked


# ------------------------------------------------------------------ no vertex inside the skin in the look pose (arms included)
fit = {r: bpy.data.objects.get(n) for r, n in lock["objects"].items()}
gq.apply_pose(arm, C.ARMS_DOWN_V2)
_skin = gq.Collider([fit["body"], fit["head"]], [gq.dominant_regions(fit["body"]), gq.dominant_regions(fit["head"])])
_sk_bvh = _skin.tree
pushed_skin = 0
for key in ("Y", "S"):
    X = PIECE[key]["X"]
    for _round in range(3):
        moved = 0
        for i in range(len(X)):
            h_ = _sk_bvh.find_nearest(Vector(X[i]), 0.05)
            if h_[0] is None:
                continue
            n = np.array(h_[1]); d = float(np.dot(X[i] - np.array(h_[0]), n))
            if d < 0.006:
                X[i] = X[i] + n * (0.006 - d)
                moved += 1
        pushed_skin += moved
        if not moved:
            break
gq.clear_pose(arm)
REPORT["verts_pushed_off_skin"] = pushed_skin

# ------------------------------------------------------------------ seat the button: the smallest lift that clears the fabric
def clasp_hits(lift):
    V_ = [tuple(map(float, p)) for p in (CLV + rn * lift)]
    T_ = []
    for f in CLF:
        for k in range(1, len(f) - 1):
            T_.append((f[0], f[k], f[k + 1]))
    t1 = BVHTree.FromPolygons(V_, T_)
    n = 0
    for key in ("Y", "S"):
        X_ = PIECE[key]["X"]
        r_, h_ = cyl(X_)
        near = (r_ < 0.06) & (np.abs(h_) < 0.06)
        idx = np.nonzero(near)[0]
        if not len(idx):
            continue
        m_ = {v: k for k, v in enumerate(idx)}
        F_ = [tuple(m_[v] for v in f) for f in PIECE[key]["F"] if all(v in m_ for v in f)]
        if not F_:
            continue
        t2 = BVHTree.FromPolygons([tuple(map(float, X_[v])) for v in idx], F_)
        n += len(t1.overlap(t2))
    return n


lift_used = None
for lift in [0.0, 0.002, 0.004, 0.006, 0.008, 0.010, 0.013, 0.016, 0.020]:
    if clasp_hits(lift) == 0:
        lift_used = lift
        break
if lift_used is None:
    lift_used = 0.020
CLV = CLV + rn * lift_used
back = back + rn * lift_used
REPORT["clasp_lift_m"] = lift_used
for v_, p_ in zip(cl.data.vertices, CLV):
    v_.co = Vector(p_)

# ------------------------------------------------------------------ intersection resolution
def all_tris():
    V = []; T = []; own = []; fidx = []
    for key in ("Y", "S"):
        off = len(V)
        V += [tuple(map(float, p)) for p in PIECE[key]["X"]]
        for fi, f in enumerate(PIECE[key]["F"]):
            T.append(tuple(off + v for v in f)); own.append(key); fidx.append(fi)
    off = len(V)
    V += [tuple(map(float, p)) for p in FV]
    for fi, f in enumerate(fun_tris):
        T.append(tuple(off + v for v in f)); own.append("F"); fidx.append(fi)
    off = len(V)
    V += [tuple(map(float, p)) for p in CLV]
    for fi, f in enumerate(CLF):
        for k in range(1, len(f) - 1):
            T.append((off + f[0], off + f[k], off + f[k + 1])); own.append("C"); fidx.append(fi)
    return V, T, own, fidx


def intersect_pairs():
    V, T, own, fidx = all_tris()
    tree = BVHTree.FromPolygons(V, T)
    tv = [set(t) for t in T]
    pairs = [(i, j) for i, j in tree.overlap(tree) if i < j and not (tv[i] & tv[j])]
    return [(own[i], fidx[i], own[j], fidx[j]) for i, j in pairs], V, T


def piece_vnormals(key):
    return vertex_normals(PIECE[key]["X"], PIECE[key]["F"])


hist = []
def skin_safety():
    """Push fabric out of the skin: arms-down (every region) and rest (arms ignored), 6 mm."""
    moved = 0
    for ops, ign in ((C.ARMS_DOWN_V2, set()), (None, {"arm"})):
        if ops:
            gq.apply_pose(arm, ops)
        else:
            gq.clear_pose(arm)
        col_ = gq.Collider([fit["body"], fit["head"]], [gq.dominant_regions(fit["body"]), gq.dominant_regions(fit["head"])])
        for key in ("Y", "S"):
            X = PIECE[key]["X"]
            for i in range(len(X)):
                h_ = col_.tree.find_nearest(Vector(X[i]), 0.05)
                if h_[0] is None or col_.poly_region[h_[2]] in ign:
                    continue
                n = np.array(h_[1]); d = float(np.dot(X[i] - np.array(h_[0]), n))
                if d < 0.005:
                    X[i] = X[i] + n * (0.006 - d)
                    moved += 1
    gq.clear_pose(arm)
    return moved


skin_moves = []
for outer in range(3):
    for it in range(10):
        pairs, V, T = intersect_pairs()
        kinds = {}
        for a, fa, b, fb in pairs:
            k = "|".join(sorted((a, b)))
            kinds[k] = kinds.get(k, 0) + 1
        hist.append({"iter": it, "pairs": len(pairs), "by": kinds})
        if not pairs:
            break
        delete = {"Y": set(), "S": set()}
        push = {"Y": {}, "S": {}}
        sep = []
        lin_in = set()
        clasp_fix = set()
        delete_lin = set()
        for a, fa, b, fb in pairs:
            for (p, fp), (q, fq) in (((a, fa), (b, fb)), ((b, fb), (a, fa))):
                if p in ("Y", "S") and PIECE[p]["fringe"][fp]:
                    delete[p].add(fp)
            # a lining face that pokes through an outer layer: drop it (the lining is an under-layer; a missing
            # triangle at its edge is never seen)
            lin_a = a == "S" and all(PIECE["S"]["lining"][v] for v in PIECE["S"]["F"][fa])
            lin_b = b == "S" and all(PIECE["S"]["lining"][v] for v in PIECE["S"]["F"][fb])
            if lin_a != lin_b and (b == "F" if lin_a else a == "F") and it >= 6:
                lf = fa if lin_a else fb                       # stubborn ones: deeper inside, else drop the facet
                ok_all = True
                for v in PIECE["S"]["F"][lf]:
                    d_, n_ = funnel_signed(PIECE["S"]["X"][v])
                    if d_ is None:
                        continue
                    cand = PIECE["S"]["X"][v] + n_ * (-0.010 - d_)
                    hs = _sk_bvh.find_nearest(Vector(cand), 0.05)
                    if hs[0] is None or float(np.dot(cand - np.array(hs[0]), np.array(hs[1]))) > 0.004:
                        PIECE["S"]["X"][v] = cand
                    else:
                        ok_all = False
                if it >= 8:                                    # still through: bring it out under the funnel's edge
                    for v in PIECE["S"]["F"][lf]:
                        p_ = PIECE["S"]["X"][v]
                        ph_ = math.degrees(math.atan2(p_[0], -(p_[1] + 0.01)))
                        k_ = int(np.argmin(np.abs(((_fphi - ph_) + 180) % 360 - 180)))
                        if p_[2] > fun_zb[k_] - 0.006:
                            rad_ = np.array([p_[0], p_[1] + 0.01, 0.0]); rr0 = np.linalg.norm(rad_)
                            wall_r = float(np.hypot(FV[k_, 0], FV[k_, 1] + 0.01))
                            newr = max(rr0, wall_r + 0.004)
                            PIECE["S"]["X"][v] = np.array([rad_[0] / rr0 * newr, rad_[1] / rr0 * newr - 0.01, fun_zb[k_] - 0.006])
                continue
            if lin_a != lin_b and (b == "F" if lin_a else a == "F"):
                vv = PIECE["S"]["F"][fa if lin_a else fb]
                if all(PIECE["S"]["X"][v][2] > fun_zb.min() - 0.005 for v in vv):
                    for v in vv:
                        lin_in.add(v)
                continue
            if lin_a != lin_b and (b in ("Y", "S", "C") if lin_a else a in ("Y", "S", "C")):
                delete["S"].add(fa if lin_a else fb)
                continue
            fr_a = a in ("Y", "S") and PIECE[a]["fringe"][fa]
            fr_b = b in ("Y", "S") and PIECE[b]["fringe"][fb]
            if fr_a or fr_b:
                continue
            pr = {a: fa, b: fb} if a != b else None
            if pr and "C" in pr:
                o_ = "Y" if "Y" in pr else ("S" if "S" in pr else None)
                if o_:
                    for v in PIECE[o_]["F"][pr[o_]]:
                        clasp_fix.add((o_, v))
                continue
            if pr and "F" in pr:
                continue                      # (the pre-pass keeps the mantle off the funnel; report what remains)
            if pr and set(pr) == {"Y", "S"}:
                for v in PIECE["Y"]["F"][pr["Y"]]:
                    push["Y"][v] = push["Y"].get(v, 0) + 0.0008
                continue
            # same piece
            if a == b == "Y":
                cs_ = [np.mean([PIECE["Y"]["X"][v] for v in PIECE["Y"]["F"][fx]], axis=0) for fx in (fa, fb)]
                if all(cyl(c_[None])[0][0] < CLASP_R + 0.012 for c_ in cs_):
                    delete["Y"].update((fa, fb))
                else:                              # separate the two yoke faces a little
                    u = cs_[1] - cs_[0]; u /= max(np.linalg.norm(u), 1e-9)
                    for v in PIECE["Y"]["F"][fa]:
                        PIECE["Y"]["X"][v] = PIECE["Y"]["X"][v] - u * 0.0015
                    for v in PIECE["Y"]["F"][fb]:
                        PIECE["Y"]["X"][v] = PIECE["Y"]["X"][v] + u * 0.0015
                continue
            if a == b == "S" and not (fr_a or fr_b) and not (lin_a or lin_b):
                ca = np.mean([PIECE["S"]["X"][v] for v in PIECE["S"]["F"][fa]], axis=0)
                cb = np.mean([PIECE["S"]["X"][v] for v in PIECE["S"]["F"][fb]], axis=0)
                u = cb - ca; u /= max(np.linalg.norm(u), 1e-9)
                sep.append((PIECE["S"]["F"][fa], PIECE["S"]["F"][fb], u))
                continue
            if a == b == "S" and False:
                # separate the two faces along the local normal (the lining goes inward, else the outer layer out)
                nS_ = piece_vnormals("S")
                ca = np.mean([PIECE["S"]["X"][v] for v in PIECE["S"]["F"][fa]], axis=0)
                cb = np.mean([PIECE["S"]["X"][v] for v in PIECE["S"]["F"][fb]], axis=0)
                na = np.mean([nS_[v] for v in PIECE["S"]["F"][fa]], axis=0)
                out_face = fa if np.dot(ca - cb, na) > 0 else fb
                in_face = fb if out_face == fa else fa
                for v in PIECE["S"]["F"][out_face]:
                    push["S"][v] = push["S"].get(v, 0) + 0.0012
                for v in PIECE["S"]["F"][in_face]:
                    push["S"][v] = push["S"].get(v, 0) - 0.0012
        for v in lin_in:                      # lining through the funnel's lower edge: tuck it inside the wall
            d_, n_ = funnel_signed(PIECE["S"]["X"][v])
            if d_ is not None and d_ > -0.006:
                cand = PIECE["S"]["X"][v] + n_ * (-0.006 - d_)
                hs = _sk_bvh.find_nearest(Vector(cand), 0.05)
                if hs[0] is None or float(np.dot(cand - np.array(hs[0]), np.array(hs[1]))) > 0.007:
                    PIECE["S"]["X"][v] = cand
                else:                          # no room inside: pass just outside the funnel's lower edge instead
                    PIECE["S"]["X"][v] = PIECE["S"]["X"][v] + n_ * (0.006 - d_)
        for o_, v in clasp_fix:               # fabric through the button: under its back, or out past its rim
            rr_, hh_ = cyl(PIECE[o_]["X"][v][None])
            rr_, hh_ = float(rr_[0]), float(hh_[0])
            if rr_ < CLASP_R + 0.002:
                PIECE[o_]["X"][v] = PIECE[o_]["X"][v] - rn * (hh_ + 0.004)
            elif -0.004 < hh_ < 0.016:
                rel_ = PIECE[o_]["X"][v] - back
                radial_ = rel_ - rn * np.dot(rel_, rn)
                PIECE[o_]["X"][v] = back + rn * np.dot(rel_, rn) + radial_ / max(np.linalg.norm(radial_), 1e-9) * (CLASP_R + 0.005)
        if delete_lin:
            for fi, f in enumerate(PIECE["S"]["F"]):
                if any(v in delete_lin for v in f) and all(PIECE["S"]["lining"][v] for v in f):
                    delete["S"].add(fi)
        for fa_, fb_, u in sep:
            for v in fa_:
                if PIECE["S"]["pin"][v] < 0.999:
                    PIECE["S"]["X"][v] = PIECE["S"]["X"][v] - u * 0.0025
            for v in fb_:
                if PIECE["S"]["pin"][v] < 0.999:
                    PIECE["S"]["X"][v] = PIECE["S"]["X"][v] + u * 0.0025
        for key in ("Y", "S"):
            if push[key]:
                nn = piece_vnormals(key)
                for v, amt in push[key].items():
                    if key == "S" and PIECE["S"]["pin"][v] >= 0.999 and not PIECE["S"]["lining"][v]:
                        amt *= 0.5
                    PIECE[key]["X"][v] = PIECE[key]["X"][v] + nn[v] * amt
            if delete[key]:
                keepf = [fi not in delete[key] for fi in range(len(PIECE[key]["F"]))]
                PIECE[key]["F"] = [f for f, k in zip(PIECE[key]["F"], keepf) if k]
                PIECE[key]["fringe"] = [f for f, k in zip(PIECE[key]["fringe"], keepf) if k]
    m_ = skin_safety()
    skin_moves.append(m_)
    if m_ == 0 and hist and hist[-1]["pairs"] == 0:
        break
REPORT["skin_safety_moves"] = skin_moves
REPORT["intersection_resolution"] = hist


def compact(key):
    pc = PIECE[key]
    used = sorted(set(v for f in pc["F"] for v in f))
    m = {v: i for i, v in enumerate(used)}
    pc["F"] = [[m[v] for v in f] for f in pc["F"]]
    for k in ("X", "UV0", "UV1", "lining", "pin"):
        if k in pc:
            pc[k] = np.asarray(pc[k])[used]
    return len(used)


compact("Y"); compact("S")
# ---- UV0 atlas (all true scale, unique): mantle cloth part at the origin, the yoke exactly +1 U from it (13 whole
# slub tiles, so the texture phase is continuous across the seam), lining and funnel at negative U, button in a corner
_lin = PIECE["S"]["lining"]
_m = PIECE["S"]["UV0"][~_lin]
_shift = np.array([0.005, 0.005]) - np.minimum(_m.min(0), PIECE["Y"]["UV0"].min(0) - np.array([1.0, 0.0]))
PIECE["S"]["UV0"][~_lin] += _shift
PIECE["Y"]["UV0"] += _shift
_l = PIECE["S"]["UV0"][_lin]
PIECE["S"]["UV0"][_lin] += np.array([-0.01 - _l[:, 0].max(), 0.005 - _l[:, 1].min()])
FUN_ANCHOR = np.array([-0.01, float(PIECE["S"]["UV0"][_lin][:, 1].max()) + 0.02])   # funnel: right edge / bottom
REPORT["uv_islands"] = {"mantle": [PIECE["S"]["UV0"][~_lin].min(0).tolist(), PIECE["S"]["UV0"][~_lin].max(0).tolist()],
                        "yoke": [PIECE["Y"]["UV0"].min(0).tolist(), PIECE["Y"]["UV0"].max(0).tolist()],
                        "lining": [PIECE["S"]["UV0"][_lin].min(0).tolist(), PIECE["S"]["UV0"][_lin].max(0).tolist()]}

# ------------------------------------------------------------------ objects
sim_ob = make_object("BCV2_Sim", PIECE["S"]["X"], PIECE["S"]["F"], cols[gh.SIM_COLLECTION],
                     lambda pi, li, v: tuple(PIECE["S"]["UV0"][v]), lambda pi, li, v: tuple(PIECE["S"]["UV1"][v]), MW)
grp = sim_ob.vertex_groups.new(name=gh.PIN_GROUP)
for i, w in enumerate(PIECE["S"]["pin"]):
    if w > 0:
        grp.add([i], float(w), "REPLACE")
yoke_ob = make_object("BCV2_Yoke", PIECE["Y"]["X"], PIECE["Y"]["F"], cols[gh.GARMENT_COLLECTION],
                      lambda pi, li, v: tuple(PIECE["Y"]["UV0"][v]), lambda pi, li, v: tuple(PIECE["Y"]["UV1"][v]), MW)

FUN_OFF = np.array([0.33, 0.70])
fme = bpy.data.meshes.new("BCV2_Funnel")
fme.from_pydata([tuple(map(float, p)) for p in FV], [], [list(map(int, f)) for f in FF])
fme.update()
fl0 = fme.uv_layers.new(name=C.UV0); fl1 = fme.uv_layers.new(name=C.UV1)
for poly in fme.polygons:
    j = poly.index // ncol; i = poly.index % ncol
    for corner, li in enumerate(poly.loop_indices):
        ii = [i, (i + 1) % ncol, (i + 1) % ncol, i][corner]
        jj = [j, j, j + 1, j + 1][corner]
        u = Fu[jj, ii]
        if i == ncol - 1 and corner in (1, 2):
            u = Fu[jj, ncol - 1] + float(np.linalg.norm(FV[jj * ncol] - FV[jj * ncol + ncol - 1]))
        fl0.data[li].uv = tuple(np.array([u, Fv[jj, ii]]) / S + FUN_OFF)
        fl1.data[li].uv = (0.0, C.FRAY_BODY_V)
    poly.use_smooth = True
fme.materials.append(MW)
fun_ob = bpy.data.objects.new("BCV2_Funnel", fme)
cols[gh.GARMENT_COLLECTION].objects.link(fun_ob)
# UV0 of the funnel: an angle-based unwrap with its seam at the centre back (the pattern's CB seam), scaled to
# true size (pattern metres / S) and moved into its own corner of the atlas
for e in fme.edges:
    a_, b_ = e.vertices
    if {a_ % ncol, b_ % ncol} == {0} and a_ // ncol != b_ // ncol:
        e.use_seam = True
fme.uv_layers.active = fl0
for o_ in bpy.context.view_layer.objects:
    o_.select_set(False)
bpy.context.view_layer.objects.active = fun_ob
fun_ob.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.0)
bpy.ops.object.mode_set(mode="OBJECT")
fun_ob.select_set(False)
fme = fun_ob.data
fl0 = fme.uv_layers[C.UV0]; fl1 = fme.uv_layers[C.UV1]     # edit mode reallocates the layers: fetch them again
_uv = np.array([d_.uv[:] for d_ in fl0.data])
_a3 = sum(p_.area for p_ in fme.polygons)
_a2 = 0.0
for p_ in fme.polygons:
    q_ = _uv[list(p_.loop_indices)]
    _a2 += 0.5 * abs(sum(q_[k, 0] * q_[(k + 1) % len(q_), 1] - q_[(k + 1) % len(q_), 0] * q_[k, 1] for k in range(len(q_))))
_k = math.sqrt(_a3 / max(_a2, 1e-12)) / S
_uv = (_uv - _uv.min(0)) * _k
_uv = _uv + np.array([FUN_ANCHOR[0] - _uv[:, 0].max(), FUN_ANCHOR[1]])
for d_, q_ in zip(fl0.data, _uv):
    d_.uv = tuple(q_)
REPORT["funnel_uv_extent"] = (_uv.max(0) - _uv.min(0)).tolist()
bmf = bmesh.new(); bmf.from_mesh(fme); bmf.faces.ensure_lookup_table(); bmf.normal_update()
out = sum((f.normal.x * f.calc_center_median().x + f.normal.y * (f.calc_center_median().y + 0.01)) for f in list(bmf.faces)[:ncol * 5])
bmf.free()
if out < 0:
    for poly in fme.polygons:
        poly.flip()

cols[gh.GARMENT_COLLECTION].objects.link(cl)
cl.name = "BCV2_Clasp"; cl.data.name = "BCV2_Clasp"
cl[gh.HARD_PROP] = True
if len(cl.data.uv_layers) == 0:
    cl.data.uv_layers.new(name=C.UV0)
cl.data.uv_layers[0].name = C.UV0
while len(cl.data.uv_layers) > 1:
    cl.data.uv_layers.remove(cl.data.uv_layers[1])
for d_ in cl.data.uv_layers[0].data:
    d_.uv = (1.88 + 0.08 * d_.uv[0], 1.88 + 0.08 * d_.uv[1])
cu1 = cl.data.uv_layers.new(name=C.UV1)
for d_ in cu1.data:
    d_.uv = (0.0, C.FRAY_BODY_V)
for g in list(cl.vertex_groups):
    cl.vertex_groups.remove(g)
for mo in list(cl.modifiers):
    cl.modifiers.remove(mo)
cl.parent = None
REPORT["clasp"] = {"back_centre": back.tolist(), "normal": rn.tolist(), "centroid": CLV.mean(0).tolist()}

# ------------------------------------------------------------------ report + checks (rest == drape for spine-weighted pieces)
pieces = [sim_ob, yoke_ob, fun_ob, cl]
for o in pieces:
    o.data.update()
REPORT["tris"] = {o.name: sum(len(p.vertices) - 2 for p in o.data.polygons) for o in pieces}
REPORT["tris"]["total"] = sum(REPORT["tris"].values())
REPORT["sim_fringe_tris"] = int(sum(PIECE["S"]["fringe"]))
REPORT["yoke_fringe_tris"] = int(sum(PIECE["Y"]["fringe"]))
wS = PIECE["S"]["pin"]
REPORT["pin"] = {"sim_verts": int(len(wS)), "full": int((wS >= 0.999).sum()), "partial": int(((wS > 0) & (wS < 0.999)).sum())}


def world_tris(objs):
    V = []; T = []; owner = []
    for k, o in enumerate(objs):
        me = o.data; me.calc_loop_triangles()
        off = len(V)
        V += [tuple(o.matrix_world @ v.co) for v in me.vertices]
        T += [tuple(off + i for i in t.vertices) for t in me.loop_triangles]
        owner += [k] * len(me.loop_triangles)
    return np.array(V), np.array(T), np.array(owner)


V, T, own = world_tris(pieces)
tree = BVHTree.FromPolygons([tuple(p) for p in V], [tuple(t) for t in T])
tv = [set(t) for t in T]
selfx = [(i, j) for i, j in tree.overlap(tree) if i < j and not (tv[i] & tv[j])]
names = [o.name for o in pieces]
by = {}
_ex = {}
for i, j in selfx:
    k = "%s|%s" % tuple(sorted((names[own[i]], names[own[j]])))
    by[k] = by.get(k, 0) + 1
    _ex.setdefault(k, []).append([V[T[i]].mean(0).round(3).tolist(), V[T[j]].mean(0).round(3).tolist()])
REPORT["self_intersections"] = {"total": len(selfx), "by_pair": by, "examples": {k: v[:5] for k, v in _ex.items()}}
# sliver check (min angle) per piece
for o in pieces:
    me = o.data; me.calc_loop_triangles()
    co = np.array([v.co[:] for v in me.vertices])
    tt = np.array([t.vertices[:] for t in me.loop_triangles])
    a, b, c = co[tt[:, 0]], co[tt[:, 1]], co[tt[:, 2]]

    def ang(p, q, r):
        u, v = q - p, r - p
        cs = (u * v).sum(1) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-12)
        return np.degrees(np.arccos(np.clip(cs, -1, 1)))
    mins = np.minimum(np.minimum(ang(a, b, c), ang(b, c, a)), ang(c, a, b))
    REPORT.setdefault("slivers", {})[o.name] = {"lt10": int((mins < 10).sum()), "lt5": int((mins < 5).sum()), "tris": int(len(tt))}


def clearance(ops, ignore):
    if ops:
        gq.apply_pose(arm, ops)
    else:
        gq.clear_pose(arm)
    col = gq.Collider([fit["body"], fit["head"]], [gq.dominant_regions(fit["body"]), gq.dominant_regions(fit["head"])])
    out = {}
    for o in pieces:
        co = np.array([tuple(o.matrix_world @ v.co) for v in o.data.vertices])
        d, found, reg = col.signed(co, 0.25)
        cnt = found & ~np.isin(reg, list(ignore))
        depth = np.where(cnt, -d, 0.0)
        out[o.name] = {"inside_gt1mm": int((depth > 0.001).sum()), "min_dist_cm": float(d[found].min() * 100) if found.any() else None}
        if o is sim_ob or o is yoke_ob:
            sel = found & np.isin(reg, ["torso", "neck"]) & (d > -0.001) & (d < 0.05)
            if sel.any():
                out[o.name]["air_torso_neck_cm_p5_p50"] = [float(np.percentile(d[sel] * 100, 5)), float(np.percentile(d[sel] * 100, 50))]
    gq.clear_pose(arm)
    return out


REPORT["clearance_arms_down_all"] = clearance(C.ARMS_DOWN_V2, set())
REPORT["clearance_rest_arms_ignored"] = clearance(None, {"arm"})
# per-vertex cloth data for the Unreal side (the build turns CLOTH_Pin into the PinMask red; this adds the proposal)
MAXD_CM, DRIVE_TOP, DRIVE_HEM = 50.0, 0.4, 0.08
cp = {"note": "BCV2_Sim vertices at rest (Blender metres, and Unreal cm: x, -y, z). pin = CLOTH_Pin = PinMask red. "
              "Proposed Chaos per-vertex MaxDistance = (1 - pin) * %.0f cm (0 on the pinned rows), AnimDrive = %.2f at pin 1 "
              "falling to %.2f at pin 0; self-collision ON (the drape is intersection-free), CollisionThickness 1.0-1.5 cm, "
              "density 0.5-0.7 kg/m2. Not applied anywhere (DemoGame_1 is read-only in this job)." % (MAXD_CM, DRIVE_TOP, DRIVE_HEM),
      "settings_proposal": {"self_collision": True, "collision_thickness_cm": 1.2, "density_kg_m2": 0.6,
                            "max_distance_cm_at_pin0": MAXD_CM, "anim_drive_top": DRIVE_TOP, "anim_drive_hem": DRIVE_HEM},
      "vertices": []}
for i, p_ in enumerate(PIECE["S"]["X"]):
    w_ = float(PIECE["S"]["pin"][i])
    cp["vertices"].append([round(float(p_[0]), 5), round(float(p_[1]), 5), round(float(p_[2]), 5), round(w_, 4),
                           round((1 - w_) * MAXD_CM, 2), round(DRIVE_HEM + (DRIVE_TOP - DRIVE_HEM) * w_, 3)])
cp["columns"] = ["x_m", "y_m", "z_m", "pin", "max_distance_cm", "anim_drive"]
json.dump(cp, open(os.path.join(C.WORK_DIR, "cloth_pins_%s.json" % A.tag), "w"))
sc["garment_unique_uvs"] = True
sc["bcv2_build"] = json.dumps({"tag": A.tag, "script": "Scripts/garments/blackcloak_v2/bcv2_assemble.py"})
REPORT["seconds"] = round(time.time() - T0, 1)
log(json.dumps({k: REPORT[k] for k in ("tris", "self_intersections", "slivers", "clearance_arms_down_all", "clasp")}, default=float))
json.dump(REPORT, open(os.path.join(C.WORK_DIR, "assemble_%s.json" % A.tag), "w"), indent=1, default=float)
if not A.no_save:
    bpy.ops.wm.save_mainfile()
    log("SAVED", bpy.data.filepath)
