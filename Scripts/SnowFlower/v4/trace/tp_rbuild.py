"""Trace pilot v2 stage R3: build the HIGH and the game LOW of the throat from the traced relief (work/relief.npz).

    blender -b --factory-startup --python tp_rbuild.py

Surface = the crown (tp_crown: the traced silhouette per row over the round-1 lacquer core) + the relief H displaced
along the crown normal, as ONE structured grid per half (rows x arclength columns) - no curve fills, so no torn edges
or holes.  Registration: each column samples H at x + Hs*nx (Hs = H blurred 2 px), so the front view of the displaced
relief stays on the traced outlines without folding.  The side walls close each half on the y = 0 plane, where the
BACK (mirror of the front: the reference is front-only, nothing new is invented) meets it.
    HIGH: rows every 0.25 px (0.17 mm), columns every ~0.17 mm; relief-domain UV 'REF' -> work/relief_*.png.
    LOW : H blurred 1 px, rows every 1 px, columns ~0.7 mm, collapse-decimated (seam verts weighted) to the budget,
          game UV 'UV0' (front half; the back half mirrors the front and SHARES its UVs).
Mouth ring = the v1 lofted rounded lip (traced saddle top edge, inner 66 x 38.4 mm for the sword's plug).
Outputs: work/tp_high.blend (TP_Throat_HIGH full, TP_Throat_HIGH_F front+ring for the bake),
         work/tp_lowgeo.blend (TP_Throat_LOW_F: front half + front ring half, UV0), work/ring_profile.json."""
import bpy, bmesh, sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import tp_crown as C
import tp_geom2d as G

WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
Z = np.load(WORK + "/relief.npz")
HF = Z["H"].astype(np.float64)
CLSF = Z["CLS"]
SW_SILVER = (419.5, 28.0); SW_LACQUER = (592.5, 28.0)      # tp_rmaps swatches (ref px) for the side bands
R0, R1, C0, C1, S = int(Z["R0"]), int(Z["R1"]), int(Z["C0"]), int(Z["C1"]), int(Z["S"])
T = json.load(open(WORK + "/trace.json"))
crown = C.Crown(T["silhouette_rows"], T.get("silhouette_sub"))
K = C.K; AXIS = C.AXIS
ROW_TOP, ROW_BOT = 42.0, 176.0
LOW_TARGET_HALF = int(os.environ.get("TP_LOW_HALF", "2950"))
SIDE_SILVER_ROW = 148.0
SIDE_FRAC = 0.6          # fraction of the side relief carried round to the back (the rest is taken by the crown)
CONFORM_R0, CONFORM_R1 = 158.0, 176.0     # rows over which the throat's base blends onto the real body surface
RELIEF_OFF_R0 = 168.0                      # relief fades to 0 from here to the bottom edge (flush, no step)

# the round-1 body copy the pilot sits on (snapshot, read-only): lacquer faces only, for the flush bottom
from mathutils.bvhtree import BVHTree
from mathutils import Vector
SNAP = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/lookmatch/r1_snapshot_interrupted/SnowFlower_Sheath.blend"
with bpy.data.libraries.load(SNAP) as (src_, dst_):
    dst_.objects = ["SM_SnowFlower_Sheath_LOD0"]
_bo = dst_.objects[0]; _me = _bo.data
_mw = np.array(_bo.matrix_world)
_V = np.zeros(len(_me.vertices) * 3); _me.vertices.foreach_get("co", _V); _V = _V.reshape(-1, 3)
_V = (np.c_[_V, np.ones(len(_V))] @ _mw.T)[:, :3] * 1000.0
_lac = [i for i, m_ in enumerate(_me.materials) if "Lacquer" in m_.name]
_F = [tuple(p_.vertices) for p_ in _me.polygons if p_.material_index in _lac]
BODY = BVHTree.FromPolygons([Vector(v) for v in _V], _F)
print("body BVH lacquer faces", len(_F), flush=True)


def body_radius(Q, z):
    """distance from the axis to the body's outer lacquer surface along each 2D direction of Q (mm)."""
    out = np.empty(len(Q))
    for i, (x, y) in enumerate(Q):
        d = np.array([x, y]); n = np.linalg.norm(d)
        d = d / n if n > 1e-9 else np.array([0.0, -1.0])
        hit = BODY.ray_cast(Vector((d[0] * 200, d[1] * 200, z)), Vector((-d[0], -d[1], 0.0)))
        out[i] = 200.0 - hit[3] if hit[0] is not None else n
    return out



def field_sampler(F):
    def f(col, row):
        x = (col - C0) * S - 0.5; y = (row - R0) * S - 0.5
        x0 = np.clip(np.floor(x).astype(int), 0, F.shape[1] - 2); y0 = np.clip(np.floor(y).astype(int), 0, F.shape[0] - 2)
        fx = np.clip(x - x0, 0, 1); fy = np.clip(y - y0, 0, 1)
        return (F[y0, x0] * (1 - fx) * (1 - fy) + F[y0, x0 + 1] * fx * (1 - fy) + F[y0 + 1, x0] * (1 - fx) * fy
                + F[y0 + 1, x0 + 1] * fx * fy)
    return f


COS_CLAMP = 0.5          # beyond 60 deg from the viewer the reference shows nothing new: carry the relief seen there


def profile(row, shrinkL=0.0, shrinkR=0.0, nfine=3000):
    """front half-section at a row: polyline (x, y) mm from the right wall foot (y=0) across the front to the left
    wall foot.  shrink* pull the crown's silhouette in by the relief carried round the side, so crown + relief keeps
    the traced silhouette."""
    A_L, B, c, b = crown.params(np.array([row]), np.array([1]))
    A_R, _, _, _ = crown.params(np.array([row]), np.array([-1]))
    A_L = np.maximum(A_L - shrinkL, 1.0); A_R = np.maximum(A_R - shrinkR, 1.0)
    xmL = float(crown.xmax(A_L, c)[0]) - 0.02; xmR = float(crown.xmax(A_R, c)[0]) - 0.02
    x = np.linspace(-xmR, xmL, nfine)
    Aside = np.where(x >= 0, A_L[0], A_R[0])
    y = crown.f(np.abs(x), Aside, B[0], c[0], b[0])
    return np.vstack([[x[0], 0.0], np.c_[x, y], [x[-1], 0.0]])


def normals_of(P):
    Tn = np.gradient(P, axis=0); Tn /= np.linalg.norm(Tn, axis=1, keepdims=True) + 1e-12
    N = np.c_[-Tn[:, 1], Tn[:, 0]]
    if N[len(N) // 2, 1] > 0:
        N = -N
    return N


def clamp_points(P):
    """outermost front points (per side) whose normal is within 60 deg of the viewer: (xR, nR), (xL, nL)."""
    N = normals_of(P)
    ok = -N[:, 1] >= COS_CLAMP
    ok[0] = ok[-1] = False
    iL = np.nonzero(ok & (P[:, 0] > 0))[0].max(); iR = np.nonzero(ok & (P[:, 0] < 0))[0].min()
    return (P[iR], N[iR]), (P[iL], N[iL])


def resample(P, n):
    d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    t = np.linspace(0, d[-1], n)
    Q = np.c_[np.interp(t, d, P[:, 0]), np.interp(t, d, P[:, 1])]
    N = normals_of(P)
    Nq = np.c_[np.interp(t, d, N[:, 0]), np.interp(t, d, N[:, 1])]
    Nq /= np.linalg.norm(Nq, axis=1, keepdims=True) + 1e-12
    s0 = float(np.interp(0.0, P[1:-1, 0], d[1:-1]))
    return Q, Nq, t - s0, d[-1]


def side_relief(rows, Hs_f):
    """relief carried round each side per row (sampled at the 60-deg clamp point), smoothed over ~2 px of rows."""
    hL = []; hR = []
    for r in rows:
        (pR, nR), (pL, nL) = clamp_points(profile(r, nfine=1500))
        hR.append(float(Hs_f(np.array([AXIS - pR[0] / K]), np.array([r]))[0]))
        hL.append(float(Hs_f(np.array([AXIS - pL[0] / K]), np.array([r]))[0]))
    step = rows[1] - rows[0]
    sig = 4.0 / step; n = int(3 * sig) + 1
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / sig) ** 2); k /= k.sum()
    sm = lambda a: np.convolve(np.pad(np.asarray(a), n, mode='edge'), k, 'valid')
    return SIDE_FRAC * np.maximum(sm(hL), 0.0), SIDE_FRAC * np.maximum(sm(hR), 0.0)


def side_silver(rows):
    """fraction of silver at each side's clamp column, smoothed over ~3 px of rows."""
    fl = []; fr = []
    for r in rows:
        (pR, nR), (pL, nL) = clamp_points(profile(r, nfine=1500))
        for p_, lst in ((pL, fl), (pR, fr)):
            c = int(np.clip(((AXIS - p_[0] / K) - C0) * S, 0, CLSF.shape[1] - 1)); q = int(np.clip((r - R0) * S, 0, CLSF.shape[0] - 1))
            lst.append(float(CLSF[q, max(c - S, 0):c + S].__eq__(1).mean()))
    step = rows[1] - rows[0]
    sig = 3.0 / step; n = int(3 * sig) + 1
    k = np.exp(-0.5 * (np.arange(-n, n + 1) / sig) ** 2); k /= k.sum()
    sm = lambda a: np.convolve(np.pad(np.asarray(a), n, mode='edge'), k, 'valid')
    return sm(fl), sm(fr)


def build_half(rows, ncol, Hs_f, H_f, cap=True):
    """structured grid (front half). returns verts (mm), faces, per-vertex (col,row) and (s,row)."""
    hL, hR = side_relief(rows, Hs_f)
    silL, silR = side_silver(rows)
    V = []; CR = []; SR = []
    for ri, r in enumerate(rows):
        P = profile(r, hL[ri], hR[ri])
        (pR, nR), (pL, nL) = clamp_points(P)
        Q, N, s, Ltot = resample(P, ncol)
        rr = np.full(ncol, r)
        hs = Hs_f(AXIS - Q[:, 0] / K, rr)
        xs_ = Q[:, 0] + hs * N[:, 0]
        # the side bands: beyond the clamp points the relief is the row-smoothed value seen at the clamp (the same
        # value the crown was pulled in by, so crown + relief = the traced silhouette), blended in over 60-45 deg;
        # colour/UV samples the registered clamp column
        hsL = float(Hs_f(np.array([AXIS - pL[0] / K]), np.array([r]))[0]); hsR = float(Hs_f(np.array([AXIS - pR[0] / K]), np.array([r]))[0])
        xcL = pL[0] + hsL * nL[0]; xcR = pR[0] + hsR * nR[0]
        beyondL = (Q[:, 0] > pL[0]) | ((Q[:, 0] >= pL[0] - 1e-6) & (Q[:, 1] > pL[1]))
        beyondR = (Q[:, 0] < pR[0]) | ((Q[:, 0] <= pR[0] + 1e-6) & (Q[:, 1] > pR[1]))
        xs_ = np.where(beyondL, xcL, np.where(beyondR, xcR, xs_))
        col_s = AXIS - xs_ / K
        h = H_f(col_s, rr)
        # side-band colour: flat satin silver where the rim seen at the clamp is (mostly) silver, else lacquer
        col_uv = col_s.copy(); row_uv = rr.copy()
        for beyond, sil_ in ((beyondL, silL[ri]), (beyondR, silR[ri])):
            sw = SW_SILVER if r < SIDE_SILVER_ROW else SW_LACQUER     # plates form the silhouette above it, the body below
            col_uv[beyond] = sw[0]; row_uv[beyond] = sw[1]
        cosang = -N[:, 1]
        wside = np.clip((0.75 - cosang) / (0.75 - COS_CLAMP), 0, 1)
        wside = np.where(beyondL | beyondR, 1.0, wside * wside * (3 - 2 * wside))
        hside = np.where(Q[:, 0] > 0, hL[ri], hR[ri])
        h = h * (1 - wside) + hside * wside
        # bottom: base blends onto the real body surface (0.12 mm under it at the last row) and the relief fades out
        wc = np.clip((r - CONFORM_R0) / (CONFORM_R1 - CONFORM_R0), 0, 1); wc = wc * wc * (3 - 2 * wc)
        if wc > 0:
            rb = body_radius(Q, float(C.zr(r))) - 0.12
            nQ = np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9
            Q = Q * (1 - wc) + Q / nQ * rb[:, None] * wc
        wh = np.clip((r - RELIEF_OFF_R0) / (CONFORM_R1 - RELIEF_OFF_R0), 0, 1)
        h = h * (1 - wh * wh * (3 - 2 * wh))
        Pv = Q + h[:, None] * N
        V.append(np.c_[Pv, np.full(ncol, C.zr(r))]); CR.append(np.c_[col_uv, row_uv]); SR.append(np.c_[s, rr])
    V = np.vstack(V); CR = np.vstack(CR); SR = np.vstack(SR)
    nr = len(rows)
    faces = []
    for i in range(nr - 1):
        for j in range(ncol - 1):
            a = i * ncol + j
            faces.append((a, a + 1, a + ncol + 1, a + ncol))
    if cap:   # top cap: the top row runs inward to the mouth-ring's inner oval at the same height
        top = V[:ncol]
        ang = np.arctan2(top[:, 1], top[:, 0])
        ov = oval(RING_IN[0] * 1.02, RING_IN[1] * 1.02, ang)
        base = len(V)
        V = np.vstack([V, np.c_[ov, top[:, 2]]])
        CR = np.vstack([CR, np.c_[CR[:ncol, 0], np.full(ncol, 40.0)]])
        SR = np.vstack([SR, np.c_[SR[:ncol, 0], np.full(ncol, ROW_TOP - 2.0)]])
        for j in range(ncol - 1):
            faces.append((base + j, base + j + 1, j + 1, j))
    return V, faces, CR, SR


# ------------------------------------------------------------------ mouth ring (v1 loft, traced saddle)
sil = T["silhouette_rows"]
Z_MOUTH = float(C.zr(31.0))


def top_row_for(xa):
    for r in range(28, 46):
        k = str(r)
        if k in sil:
            hw = max((AXIS - sil[k][0]) * K, (sil[k][1] - AXIS) * K)
            if hw >= xa:
                return r - 0.5
    return 45.0


xs_r = np.linspace(0, 37, 75)
tr = np.array([top_row_for(v) for v in xs_r])
tr = np.maximum.accumulate(tr)
tr = np.convolve(np.pad(tr, 3, mode='edge'), np.ones(7) / 7, 'valid')
ztop_x = np.maximum(C.zr(tr), Z_MOUTH)
RING_IN = (33.0, 19.2); RING_OUT = (36.0, 22.4); PR = 3.0
Z_RING_BOT = float(C.zr(44.5))


def oval(a, b, t):
    c_, s_ = np.cos(t), np.sin(t)
    r = 1.0 / (np.abs(c_ / a) ** PR + np.abs(s_ / b) ** PR) ** (1 / PR)
    return np.c_[r * c_, r * s_]


PROF_HIGH = [(0.0, "bot"), (0.0, 1.6), (0.05, 0.6), (0.18, 0.12), (0.35, 0.0), (0.65, 0.0), (0.82, 0.12), (0.95, 0.6),
             (1.0, 1.6), (1.12, 3.0), (1.12, 4.4), (1.0, 5.6), (0.98, "bot")]
PROF_LOW = [(0.0, "bot"), (0.0, 1.6), (0.2, 0.1), (0.8, 0.1), (1.0, 1.6), (1.12, 3.6), (1.0, 5.6), (0.98, "bot")]


def ring(th, prof, closed_theta):
    Pin, Pout = oval(*RING_IN, th), oval(*RING_OUT, th)
    V = []
    for k in range(len(th)):
        zt = float(np.interp(abs(Pout[k, 0]), xs_r, ztop_x))
        for f, d in prof:
            xy = Pin[k] + f * (Pout[k] - Pin[k])
            z = Z_RING_BOT if d == "bot" else min(zt + d, Z_RING_BOT - 0.3)
            V.append((float(xy[0]), float(xy[1]), float(z)))
    npf = len(prof); nt = len(th)
    F = []
    for k in range(nt if closed_theta else nt - 1):
        k2 = (k + 1) % nt
        for j in range(npf):
            j2 = (j + 1) % npf
            F.append((k * npf + j, k * npf + j2, k2 * npf + j2, k2 * npf + j))
    return np.array(V), F


json.dump({"xs_mm": xs_r.tolist(), "ztop_mm": ztop_x.tolist(), "ring_in": RING_IN, "ring_out": RING_OUT, "p": PR,
           "z_ring_bottom_mm": Z_RING_BOT, "z_mouth_mm": Z_MOUTH}, open(WORK + "/ring_profile.json", "w"), indent=1)


# ------------------------------------------------------------------ blender helpers
def make_obj(name, V, F, coll, mat=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata((np.asarray(V) * 0.001).tolist(), [], F); me.update()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    if mat:
        me.materials.append(mat)
    return ob


def set_uv(ob, name, per_vertex_uv):
    me = ob.data
    uvl = me.uv_layers.new(name=name)
    lv = np.zeros(len(me.loops), np.int64); me.loops.foreach_get("vertex_index", lv)
    uvl.data.foreach_set("uv", per_vertex_uv[lv].astype(np.float32).ravel())


def orient_out(ob):
    """make the faces point away from the axis (checked on the mean over faces)."""
    me = ob.data
    n = np.zeros(len(me.polygons) * 3); me.polygons.foreach_get("normal", n); n = n.reshape(-1, 3)
    c = np.zeros(len(me.polygons) * 3); me.polygons.foreach_get("center", c); c = c.reshape(-1, 3)
    radial = (n[:, :2] * c[:, :2]).sum(1)
    if np.median(radial) < 0:
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    me.update()


def mirror_copy(ob, name, coll):
    me = ob.data.copy(); me.name = name
    V = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3); V[:, 1] *= -1
    me.vertices.foreach_set("co", V.ravel())
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.reverse_faces(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o2 = bpy.data.objects.new(name, me); coll.objects.link(o2)
    return o2


def join(objs, name):
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active; o.name = o.data.name = name
    return o


def weld(ob, dist=1e-5):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=dist * 0.5)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# ------------------------------------------------------------------ HIGH
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
colH = bpy.data.collections.new("TP_HIGH"); sc.collection.children.link(colH)
mat_rel = bpy.data.materials.new("TP_Relief"); mat_ring = bpy.data.materials.new("TP_RingSilver")
Hs_f = field_sampler(G.gauss(HF, 2.0 * S))
H_f = field_sampler(HF)
rows_h = np.arange(ROW_TOP, ROW_BOT + 1e-6, 0.25)
V, F, CR, SR = build_half(rows_h, 720, Hs_f, H_f)
hiF = make_obj("TP_Throat_HIGH_Fgrid", V, F, colH, mat_rel)
uv_ref = np.c_[(CR[:, 0] - C0) / (C1 - C0), 1.0 - (CR[:, 1] - R0) / (R1 - R0)]
set_uv(hiF, "REF", uv_ref)
orient_out(hiF)
thH = np.linspace(0, 2 * np.pi, 192, endpoint=False)
Vr, Fr = ring(thH, PROF_HIGH, True)
rgH = make_obj("TP_Ring_HIGH", Vr, Fr, colH, mat_ring)
rgH.data.uv_layers.new(name="REF")
bm = bmesh.new(); bm.from_mesh(rgH.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(rgH.data); bm.free()
hiB = mirror_copy(hiF, "TP_Throat_HIGH_Bgrid", colH)
for o in (hiF, hiB, rgH):
    for p in o.data.polygons:
        p.use_smooth = True
# bake source = front grid + ring (ring kept separate object in the full too)
full = join([hiF.copy() if False else hiF, hiB], "TP_Throat_HIGH_grid")
weld(full, 1e-6)
rg2 = rgH.copy(); rg2.data = rgH.data.copy(); colH.objects.link(rg2)
full2 = join([full, rg2], "TP_Throat_HIGH")
print("HIGH tris", tris(full2), flush=True)
# the front-only bake source
V, F, CR, SR = build_half(rows_h, 720, Hs_f, H_f)
hf = make_obj("TP_Throat_HIGH_F", V, F, colH, mat_rel)
set_uv(hf, "REF", np.c_[(CR[:, 0] - C0) / (C1 - C0), 1.0 - (CR[:, 1] - R0) / (R1 - R0)])
orient_out(hf)
for p in hf.data.polygons:
    p.use_smooth = True
hf2 = join([hf, rgH], "TP_Throat_HIGH_F")
bpy.ops.wm.save_as_mainfile(filepath=WORK + "/tp_high.blend")
print("saved tp_high.blend", flush=True)

# ------------------------------------------------------------------ LOW (front half + front ring half)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
colL = bpy.data.collections.new("TP_LOW"); sc.collection.children.link(colL)
HL = G.gauss(HF, 1.0 * S)
rows_l = np.arange(ROW_TOP, ROW_BOT + 1e-6, 1.0)
V, F, CR, SR = build_half(rows_l, 170, field_sampler(G.gauss(HF, 2.0 * S)), field_sampler(HL))
lo = make_obj("TP_LOW_grid", V, F, colL)
orient_out(lo)
# UV0 layout (mm -> uv): grid island top, ring half-island below
SMIN, SMAX = SR[:, 0].min(), SR[:, 0].max()
VMIN, VMAX = ROW_TOP - 2.0, ROW_BOT
Wmm = SMAX - SMIN; Hmm = (VMAX - VMIN) * K
ring_half_len = None
thL = np.pi + np.linspace(0, np.pi, 33)                  # front half (y < 0)
Vr, Fr = ring(thL, PROF_LOW, False)
# ring param: u = arclength along the outer oval, v = profile index arclength
Pout = oval(*RING_OUT, thL)
su = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Pout, axis=0), axis=1))]
prof_len = np.r_[0, np.cumsum([1.6, 1.5, 3.0, 1.5, 2.1, 2.0, 2.0])]           # approx mm along PROF_LOW
ring_half_len = su[-1]
MARG = 3.0
TOT_W = max(Wmm, ring_half_len) + 2 * MARG
TOT_H = Hmm + prof_len[-1] + 3 * MARG
SCL = 1.0 / max(TOT_W, TOT_H)
uv_grid = np.c_[(SR[:, 0] - SMIN + MARG) * SCL, 1.0 - (MARG + (SR[:, 1] - VMIN) * K) * SCL]
set_uv(lo, "UV0", uv_grid)
rgL = make_obj("TP_LOW_ring", Vr, Fr, colL)
bm = bmesh.new(); bm.from_mesh(rgL.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(rgL.data); bm.free()
npf = len(PROF_LOW)
uv_r = np.array([[(su[k] + MARG) * SCL, (MARG + prof_len[j]) * SCL] for k in range(len(thL)) for j in range(npf)])
# the closed profile's last face wraps j=npf-1 -> 0: give it its own loop UVs (v = prof_len[-1] for the wrap)
me = rgL.data
uvl = me.uv_layers.new(name="UV0")
lv = np.zeros(len(me.loops), np.int64); me.loops.foreach_get("vertex_index", lv)
uvs = uv_r[lv].copy()
for p in me.polygons:
    js = [lv[li] % npf for li in p.loop_indices]
    if 0 in js and (npf - 1) in js:
        for li in p.loop_indices:
            if lv[li] % npf == 0:
                uvs[li, 1] = (MARG + prof_len[-1]) * SCL
uvl.data.foreach_set("uv", uvs.astype(np.float32).ravel())
# decimate the grid half, seam feet weighted so the y=0 boundary and the top/bottom edges survive
me = lo.data
vg = lo.vertex_groups.new(name="keep")
Vc = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", Vc); Vc = Vc.reshape(-1, 3) * 1000
bnd = np.nonzero(np.abs(Vc[:, 1]) < 0.02)[0].tolist()
vg.add(bnd, 1.0, 'REPLACE')
n0 = tris(lo)
target = LOW_TARGET_HALF - len(Fr) * 2
for o in sc.objects: o.select_set(False)
bpy.context.view_layer.objects.active = lo; lo.select_set(True)
m = lo.modifiers.new("dec", 'DECIMATE'); m.decimate_type = 'COLLAPSE'; m.ratio = target / n0
m.use_collapse_triangulate = True; m.vertex_group = "keep"; m.vertex_group_factor = 1000.0; m.invert_vertex_group = True
bpy.ops.object.modifier_apply(modifier="dec")
# snap the seam feet exactly onto y = 0 (the mirrored back meets them there)
Vc = np.zeros(len(lo.data.vertices) * 3); lo.data.vertices.foreach_get("co", Vc); Vc = Vc.reshape(-1, 3)
seam = np.abs(Vc[:, 1]) < 0.00005
Vc[seam, 1] = 0.0; lo.data.vertices.foreach_set("co", Vc.ravel()); lo.data.update()
print("LOW grid tris", n0, "->", tris(lo), "seam verts", int(seam.sum()), "ring half tris", tris(rgL), flush=True)
lowF = join([lo, rgL], "TP_Throat_LOW_F")
lowF.vertex_groups.clear()
bpy.ops.object.shade_smooth_by_angle(angle=math.radians(55))
json.dump({"uv_scale_per_mm": SCL, "grid_w_mm": Wmm, "grid_h_mm": Hmm, "ring_half_mm": float(ring_half_len)},
          open(WORK + "/low_uv.json", "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=WORK + "/tp_lowgeo.blend")
print("saved tp_lowgeo.blend  LOW_F tris", tris(lowF), "uv px/mm @2048 %.2f" % (SCL * 2048), flush=True)
