"""Trace pilot stage 3: build the HIGH-POLY sheath throat from the traced outlines (work/trace.json, blossom_fit.json).

    blender -b --factory-startup --python tp_build.py

Every plate / inset / filigree outline is a traced contour (tp_trace.py); here each becomes a bevelled slab (Blender
2D curve: fill + extrude + bevel), is densified, and is wrapped onto the crown surface (tp_crown) at its stack height,
front AND mirrored back.  Blossom = fitted petals (domed pearl + silver bezel), fitted centre pearl, traced stamen
beads.  Mouth ring = a lofted rounded lip whose front-view top edge is the traced silhouette (saddle), widened only
where the sword's plug forces it.  Output: trace_pilot/work/tp_high.blend (object TP_Throat_HIGH, metres)."""
import bpy, bmesh, sys, os, json, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import tp_crown as C

WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
T = json.load(open(WORK + "/trace.json"))
BF = json.load(open(WORK + "/blossom_fit.json"))
crown = C.Crown(T["silhouette_rows"], T.get("silhouette_sub"))
K = C.K
Z_MOUTH = float(C.zr(31.0))
#: TP_LOWRES=1 builds the GAME mesh with the same construction at game resolution: coarse outlines, no bevels, plate
#: slabs without insets (the normal map carries rims / insets / filigree / stamens), hidden bottom caps dropped.
LOW = os.environ.get("TP_LOWRES") == "1"

bpy.ops.wm.read_factory_settings(use_empty=True)
col = bpy.data.collections.new("TP_HIGH"); bpy.context.scene.collection.children.link(col)
MATS = {}
for nm, rgb in (("TP_Silver", (0.6, 0.6, 0.6)), ("TP_Enamel", (0.02, 0.025, 0.035)), ("TP_Pearl", (0.8, 0.8, 0.82)),
                ("TP_Lacquer", (0.03, 0.035, 0.045))):
    m = bpy.data.materials.new(nm); m.diffuse_color = (*rgb, 1); MATS[nm] = m


# ------------------------------------------------------------------ helpers
def curve_mesh(loops_px, t, bevel, name, max_edge=0.8):
    """2D curve (fill BOTH) from loops in ref px -> bmesh in local (x_front mm, -z mm, w) with w in [0, t]."""
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '2D'; cu.fill_mode = 'BOTH'
    bevel = min(bevel, t / 2 * 0.95)
    cu.extrude = max(t / 2 - bevel, 0.001); cu.bevel_depth = bevel; cu.bevel_resolution = 2
    try:
        cu.offset = -bevel
    except Exception:
        pass
    cu.resolution_u = 1
    n = 0
    if LOW:
        bevel = 0.0; cu.bevel_depth = 0.0; cu.extrude = t / 2
        max_edge = 7.0 if max_edge >= 0.8 else 3.0
    for P in loops_px:
        P = np.asarray(P, float)
        if LOW and len(P) > 24:
            d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1))]
            nseg = max(int(d[-1] / 3.6), 10)
            tt_ = np.linspace(0, d[-1], nseg, endpoint=False)
            Q = np.vstack([P, P[:1]])
            P = np.c_[np.interp(tt_, d, Q[:, 0]), np.interp(tt_, d, Q[:, 1])]
        if len(P) < 4:
            continue
        sp = cu.splines.new('POLY'); sp.points.add(len(P) - 1)
        xs = C.xc(P[:, 0]); ys = -C.zr(P[:, 1])
        co = np.c_[xs, ys, np.zeros(len(P)), np.ones(len(P))]
        sp.points.foreach_set("co", co.ravel()); sp.use_cyclic_u = True; n += 1
    if n == 0:
        bpy.data.curves.remove(cu); return None
    ob = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob); bpy.data.curves.remove(cu)
    bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
    if not bm.verts:
        return None
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    def caps():
        return [f for f in bm.faces if abs(f.normal.z) > 0.999]
    def beautify():
        cf = caps()
        ce = {e for f in cf for e in f.edges if all(abs(g.normal.z) > 0.999 for g in e.link_faces) and len(e.link_faces) == 2}
        if cf and ce:
            bmesh.ops.beautify_fill(bm, faces=cf, edges=list(ce))
    bm.normal_update(); beautify()
    for _ in range(12):
        long = [e for e in bm.edges if e.calc_length() > max_edge]
        if not long:
            break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        bm.normal_update(); beautify()
    zmin = min(v.co.z for v in bm.verts)
    for v in bm.verts:
        v.co.z -= zmin
    bm.normal_update()
    capl = bm.faces.layers.int.new("cap")
    for f in bm.faces:
        f[capl] = 1 if f.normal.z > 0.999 else (-1 if f.normal.z < -0.999 else 0)
    if LOW:     # the bottom cap sits on the crown / the plate below: never seen
        bm.normal_update()
        bot = [f for f in bm.faces if f.normal.z < -0.999 and all(v.co.z < 1e-5 for v in f.verts)]
        bmesh.ops.delete(bm, geom=bot, context='FACES')
    return bm


def wrap_bm(bm, h, back=False, lift=None):
    """local (x, -z, w) -> crown 3D (front or mirrored back) at offset h + w (+ optional lift(V) mm)."""
    V = np.array([v.co[:] for v in bm.verts])
    def S(Vq):
        o = h + Vq[:, 2]
        if lift is not None:
            o = o + lift(Vq)
        return crown.map(Vq[:, 0], C.row_of(-Vq[:, 1]), o, back=back)
    P = S(V)
    # analytic surface normals of the wrapped caps (finite differences of the map in the cap's own x / y): smooth
    # shading from these instead of from the flat triangles removes the triangulation ripple that glossy silver
    # otherwise shows (and that the normal bake would copy into the game mesh)
    capl = bm.faces.layers.int.get("cap")
    if capl is not None and not LOW:
        eps = 0.05
        ex = np.array([eps, 0, 0]); ey = np.array([0, eps, 0])
        dX = S(V + ex) - S(V - ex); dY = S(V + ey) - S(V - ey)
        N = np.cross(dX, dY); N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
        anl = bm.verts.layers.float_vector.new("an")
    bad = (np.abs(P[:, 0]) > 60) | (np.abs(P[:, 1]) > 50) | ~np.isfinite(P).all(1)
    for v, p in zip(bm.verts, P):
        v.co = p
    if bad.any():     # a stray vertex from a degenerate curve fill (seen once: 1 vertex at x -186 mm) - drop it
        bm.verts.ensure_lookup_table()
        print("  dropping stray verts", int(bad.sum()), "local", V[bad][:3].round(2).tolist(), flush=True)
        bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.nonzero(bad)[0]], context='VERTS')
    # the local->crown map is orientation-REVERSING on the front (Jacobian det < 0: x->x, -z->z flips, w->-y) and
    # orientation-preserving on the mirrored back, so only the front copies need their faces reversed (the curve
    # solids come out of Blender with outward normals; recalc_face_normals is not reliable on the non-manifold bits)
    if not back:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    if capl is not None and not LOW:
        bm.normal_update()
        bm.verts.index_update()
        for v in bm.verts:
            fs = [f for f in v.link_faces if f[capl] != 0]
            if not fs:
                continue
            n = N[v.index]
            fn = sum((f.normal for f in fs), fs[0].normal * 0)
            if n @ np.array(fn[:]) < 0:
                n = -n
            v[anl] = n
    return bm


PARTS = []      # (name, bmesh, material)


def add(name, bm, mat):
    if bm is not None and len(bm.faces):
        PARTS.append((name, bm, mat))


def both(name, make, h, mat, lift=None):
    for back in (False, True):
        bm = make()
        if bm is None:
            return
        add(name + ("_B" if back else "_F"), wrap_bm(bm, h, back, lift), mat)


def loops(e, key, min_area=2.0):
    return [l["pts"] for l in e[key] if abs(l["area"]) >= min_area]


# ------------------------------------------------------------------ traced plates (pen-tool trace, tp_plates.py)
TP = json.load(open(WORK + "/trace_plates.json"))["plates"]
BLOSSOM_PX = tuple(BF["centre"])
PL = {  # stack height over the crown (mm), silver thickness, bevel, curl (outward lift at the far tip, mm)
    "sleeve": dict(h=-0.2, t=1.0, bev=0.35, curl=0.0),
    "t2": dict(h=0.0, t=1.4, bev=0.45, curl=0.8),
    "t1": dict(h=0.9, t=1.6, bev=0.5, curl=1.2),
    "drop": dict(h=0.6, t=1.6, bev=0.5, curl=0.0),
    "flare": dict(h=1.6, t=1.6, bev=0.45, curl=0.6),
    "lat": dict(h=2.0, t=1.8, bev=0.55, curl=1.2),
    "crestB": dict(h=2.0, t=0.6, bev=0.2, curl=0.0),
    "crestT": dict(h=1.2, t=0.6, bev=0.2, curl=0.0),
}
RECESS = 0.7


def offset_loop(P, d_px):
    """shift a closed loop along its normals by d_px (positive = inward for the loops' orientation check below)."""
    P = np.asarray(P, float)
    T = np.roll(P, -1, 0) - np.roll(P, 1, 0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    N = np.c_[T[:, 1], -T[:, 0]]
    c = P.mean(0)
    if np.mean(((P - c) * N).sum(1)) > 0:     # normals point outward -> flip so +d is inward
        N = -N
    return P + d_px * N


def curl_fn(loop_px, amount):
    """outward lift growing with the distance from the blossom centre (the plates curl out at their tips)."""
    if amount <= 0:
        return None
    L = np.asarray(loop_px, float)
    d = np.hypot(L[:, 0] - BLOSSOM_PX[0], L[:, 1] - BLOSSOM_PX[1])
    d0, d1 = 22.0, float(d.max())
    def f(V):
        col = C.AXIS - V[:, 0] / K; row = C.row_of(-V[:, 1])
        dd = np.hypot(col - BLOSSOM_PX[0], row - BLOSSOM_PX[1])
        return amount * np.clip((dd - d0) / max(d1 - d0, 1e-3), 0, 1) ** 2
    return f


def keel_fn(amount=0.6, half_mm=9.0):
    def f(V):
        top = V[:, 2] > 0.2
        return np.where(top, amount * np.clip(1 - np.abs(V[:, 0] - (505.5 - 506.0) * K) / half_mm, 0, 1), 0.0)
    return f


for nm, e in TP.items():
    kind = nm.split("_")[0]
    p = PL[kind]
    outer = e["outer"]; inset = e.get("inset")
    cf = curl_fn(outer, p["curl"])
    if kind in ("crestB", "crestT"):
        # filigree crest: dark backing = the traced outline, a silver border band, lace = segmentation (below)
        both(nm + "_backing", lambda o=outer: curve_mesh([o], p["t"], p["bev"], nm), p["h"], "TP_Enamel")
        continue
    loops_s = [outer] + ([inset] if (inset and not LOW) else [])
    both(nm + "_silver", lambda l=loops_s: curve_mesh(l, p["t"], p["bev"], nm), p["h"], "TP_Silver", lift=cf)
    if inset and not LOW:
        lift = cf
        if kind == "drop":
            kf = keel_fn()
            lift = (lambda V, kf=kf: kf(V))
        both(nm + "_inset", lambda i=inset: curve_mesh([i], p["t"] - RECESS, 0.25, nm), p["h"], "TP_Enamel", lift=lift)
    print("plate", nm, "outer", len(outer), "inset", len(inset) if inset else 0, flush=True)

# ------------------------------------------------------------------ filigree from the class segmentation (tp_trace)
FIL = {"crestT": dict(h=1.8, t=0.8, bev=0.3), "crestB": dict(h=2.6, t=0.8, bev=0.3),
       "sprigU": dict(h=2.5, t=1.1, bev=0.4), "sprigL": dict(h=3.8, t=1.1, bev=0.4), "lace": dict(h=-0.1, t=0.7, bev=0.25)}
for e in T["elements"]:
    if LOW or e["kind"] not in FIL:
        continue
    p = FIL[e["kind"]]
    sil_l = loops(e, "silver", 1.5)
    nm = e["name"]
    if nm in TP:      # crest lace: keep only the lace inside the traced crest outline (and below the collar)
        import tp_geom2d as G3
        ol = np.asarray(TP[nm]["outer"], float)
        keep = []
        for l in sil_l:
            c_ = np.asarray(l, float).mean(0)
            if G3.pip(np.array([c_[0]]), np.array([c_[1]]), ol)[0] and c_[1] > 41.5:
                keep.append(l)
        sil_l = keep
    both(nm + "_fil", lambda l=sil_l: curve_mesh(l, p["t"], p["bev"], nm), p["h"], "TP_Silver")
    print("filigree", nm, "loops", len(sil_l), flush=True)

# ------------------------------------------------------------------ blossom
cx, cy = BF["centre"]


def petal_poly(phi, d0, d1, w, q, e, n=96, shrink=0.0):
    s = np.linspace(0, 1, n)
    hw = w / 2 * (2 * np.sqrt(np.clip(s * (1 - s), 0, None))) ** q * (1 + e * (s - 0.5))
    hw = np.maximum(hw - shrink, 0)
    u = d0 + shrink + s * (d1 - d0 - 2 * shrink)
    Q = np.vstack([np.c_[u, hw], np.c_[u[::-1], -hw[::-1]][1:-1]])
    cu, su = np.cos(phi), np.sin(phi)
    return np.c_[cx + Q[:, 0] * cu - Q[:, 1] * su, cy + Q[:, 0] * su + Q[:, 1] * cu]


H_ROSETTE, H_BEZEL, H_PEARL = 3.8, 4.0, 4.3
tt = np.linspace(0, 2 * np.pi, 120, endpoint=False)
ros = [np.c_[cx + 15 * np.cos(tt), cy + 15 * np.sin(tt)]]
both("blossom_backing", lambda: curve_mesh(ros, 0.8, 0.2, "ros"), H_ROSETTE, "TP_Enamel")


def make_dist(inner_mm):
    a = inner_mm; b = np.roll(inner_mm, -1, 0)

    def dist_edge(V):
        p = V[:, None, :2]; ab = (b - a)[None]; ap = p - a[None]
        t = np.clip((ap * ab).sum(-1) / (ab * ab).sum(-1), 0, 1)
        return np.sqrt(((ap - t[..., None] * ab) ** 2).sum(-1)).min(1)
    return dist_edge


import tp_geom2d as G2
for i, pp in enumerate(BF["petals"]):
    outer = petal_poly(pp["phi"], pp["d0"], pp["d1"], pp["w"], pp["q"], pp["e"])
    inner = petal_poly(pp["phi"], pp["d0"], pp["d1"], pp["w"], pp["q"], pp["e"], shrink=1.0)
    if not LOW: both(f"petal{i}_bezel", (lambda o=outer, n=inner: curve_mesh([o, n], 1.3, 0.3, "bz")), H_BEZEL, "TP_Silver")
    inner_mm = np.c_[C.xc(inner[:, 0]), -C.zr(inner[:, 1])]
    de = make_dist(inner_mm)
    gx, gy = np.meshgrid(np.linspace(inner_mm[:, 0].min(), inner_mm[:, 0].max(), 50),
                         np.linspace(inner_mm[:, 1].min(), inner_mm[:, 1].max(), 50))
    ins = G2.pip(gx, gy, inner_mm)
    gp = np.c_[gx[ins], gy[ins], np.zeros(ins.sum())]
    dmax = float(de(gp).max())

    def dome(V, de=de, dm=dmax):
        top = V[:, 2] > 0.5
        d = np.clip(de(V) / dm, 0, 1)
        return np.where(top, 3.2 * np.sqrt(1 - (1 - d) ** 2), 0.0)
    both(f"petal{i}_pearl", (lambda n=inner: curve_mesh([n], 0.8, 0.25, "pl", max_edge=0.45)), H_PEARL, "TP_Pearl", lift=dome)


def sphere(center_px, r_mm, off, back, mat, name, sy=0.85, seg=24):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r_mm)
    c3 = crown.map(np.array([C.xc(center_px[0])]), np.array([center_px[1]]), np.array([off + r_mm * sy]), back=back)[0]
    for v in bm.verts:
        v.co = (v.co.x + c3[0], v.co.y * sy + c3[1], v.co.z + c3[2])
    add(name + ("_B" if back else "_F"), bm, mat)


def rod(p0_px, p1_px, r_mm, off, back, mat, name):
    a = crown.map(np.array([C.xc(p0_px[0])]), np.array([p0_px[1]]), np.array([off]), back=back)[0]
    b = crown.map(np.array([C.xc(p1_px[0])]), np.array([p1_px[1]]), np.array([off]), back=back)[0]
    bm = bmesh.new()
    d = b - a; L = float(np.linalg.norm(d))
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=r_mm, radius2=r_mm * 0.8, depth=L)
    z = np.array([0, 0, 1.0]); dn = d / L
    ax = np.cross(z, dn); s = np.linalg.norm(ax); cth = float(z @ dn)
    if s > 1e-8:
        ax /= s; ang = math.atan2(s, cth)
        Kx = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
        Rm = np.eye(3) + math.sin(ang) * Kx + (1 - math.cos(ang)) * Kx @ Kx
    else:
        Rm = np.eye(3)
    mid = (a + b) / 2
    for v in bm.verts:
        v.co = Rm @ np.array(v.co) + mid
    add(name + ("_B" if back else "_F"), bm, mat)


pr = BF["pearl"]
beads = sorted(BF["stamen_beads"], key=lambda b: -b[2])
keep = []
for b in beads:
    if all(math.hypot(b[0] - k[0], b[1] - k[1]) > 2.4 for k in keep):
        keep.append(b)
keep = keep[:12]
print("stamen beads kept", len(keep))
tt = np.linspace(0, 2 * np.pi, 64, endpoint=False)
for back in (False, True):
    sphere((pr["cx"], pr["cy"]), (pr["r"] + 0.3) * K, 5.3, back, "TP_Pearl", "centre_pearl", sy=0.8, seg=12 if LOW else 32)
    if LOW:
        continue
    ring_o = np.c_[pr["cx"] + (pr["r"] + 1.5) * np.cos(tt), pr["cy"] + (pr["r"] + 1.5) * np.sin(tt)]
    ring_i = np.c_[pr["cx"] + (pr["r"] + 0.2) * np.cos(tt), pr["cy"] + (pr["r"] + 0.2) * np.sin(tt)]
    bm = curve_mesh([ring_o, ring_i], 1.2, 0.4, "pb")
    add("pearl_bezel" + ("_B" if back else "_F"), wrap_bm(bm, 5.0, back), "TP_Silver")
    for j, b in enumerate(keep):
        ang = math.atan2(b[1] - pr["cy"], b[0] - pr["cx"])
        p0 = (pr["cx"] + (pr["r"] + 1.2) * math.cos(ang), pr["cy"] + (pr["r"] + 1.2) * math.sin(ang))
        rod(p0, (b[0], b[1]), 0.22, 5.6, back, "TP_Silver", f"stamen{j}")
        sphere((b[0], b[1]), 0.55, 5.4, back, "TP_Silver", f"bead{j}", sy=1.0, seg=12)

# ------------------------------------------------------------------ mouth ring (lofted rounded lip)
sil = T["silhouette_rows"]


def top_row_for(xa):
    """front-view top edge of the collar: first reference row whose silhouette reaches |x| (traced silhouette)."""
    for r in range(28, 46):
        k = str(r)
        if k in sil:
            hw = max((C.AXIS - sil[k][0]) * K, (sil[k][1] - C.AXIS) * K)
            if hw >= xa:
                return r - 0.5
    return 45.0


xs = np.linspace(0, 37, 75)
tr = np.array([top_row_for(v) for v in xs])
tr = np.maximum.accumulate(tr)                                  # monotone saddle
tr = np.convolve(np.pad(tr, 3, mode='edge'), np.ones(7) / 7, 'valid')
ztop_x = np.maximum(C.zr(tr), Z_MOUTH)                          # never above the mouth plane (the guard seats 0.4 above)
RING_IN = (33.0, 19.2); RING_OUT = (36.0, 22.4); PR = 3.0
Z_RING_BOT = float(C.zr(44.5))
NT = 40 if LOW else 192
th = np.linspace(0, 2 * np.pi, NT, endpoint=False)


def oval(a, b, t):
    c, s = np.cos(t), np.sin(t)
    r = 1.0 / (np.abs(c / a) ** PR + np.abs(s / b) ** PR) ** (1 / PR)
    return np.c_[r * c, r * s]


Pin, Pout = oval(*RING_IN, th), oval(*RING_OUT, th)
prof = [(0.0, "bot"), (0.0, 1.6), (0.05, 0.6), (0.18, 0.12), (0.35, 0.0), (0.65, 0.0), (0.82, 0.12), (0.95, 0.6),
        (1.0, 1.6), (1.12, 3.0), (1.12, 4.4), (1.0, 5.6), (0.98, "bot")]
verts = []
for k in range(NT):
    zt = float(np.interp(abs(Pout[k, 0]), xs, ztop_x))
    for f, d in prof:
        xy = Pin[k] + f * (Pout[k] - Pin[k])
        z = Z_RING_BOT if d == "bot" else min(zt + d, Z_RING_BOT - 0.3)
        verts.append((float(xy[0]), float(xy[1]), float(z)))
if LOW:
    prof = [(0.0, "bot"), (0.0, 1.6), (0.2, 0.1), (0.8, 0.1), (1.0, 1.6), (1.12, 3.6), (1.0, 5.6), (0.98, "bot")]
    verts = []
    for k in range(NT):
        zt = float(np.interp(abs(Pout[k, 0]), xs, ztop_x))
        for f, d in prof:
            xy = Pin[k] + f * (Pout[k] - Pin[k])
            z = Z_RING_BOT if d == "bot" else min(zt + d, Z_RING_BOT - 0.3)
            verts.append((float(xy[0]), float(xy[1]), float(z)))
npf = len(prof)
faces = []
for k in range(NT):
    k2 = (k + 1) % NT
    for j in range(npf):
        j2 = (j + 1) % npf
        faces.append((k * npf + j, k * npf + j2, k2 * npf + j2, k2 * npf + j))
me = bpy.data.meshes.new("ring"); me.from_pydata(verts, [], faces); me.update()
bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
add("mouth_ring", bm, "TP_Silver")

# ------------------------------------------------------------------ base shell (crown surface), rows 42..168
rows = np.arange(42.0, 168.01, 4.0 if LOW else 0.5)
NPH = 13 if LOW else 56
ph = np.linspace(0, np.pi, NPH)
ring_pts = []
for r in rows:
    A_L, B, c, b = crown.params(np.array([r]), np.array([1]))
    A_R, _, _, _ = crown.params(np.array([r]), np.array([-1]))
    xm_L = float(max(A_L[0] - 0.8, c[0])) - 0.03; xm_R = float(max(A_R[0] - 0.8, c[0])) - 0.03
    xf = np.where(np.cos(ph) >= 0, np.cos(ph) * xm_L, np.cos(ph) * xm_R)
    front = crown.map(xf, np.full(NPH, r), np.zeros(NPH))
    back = front[::-1][1:-1].copy(); back[:, 1] *= -1
    ring_pts.append(np.vstack([front, back]))
M = len(ring_pts[0])
verts = np.vstack(ring_pts)
faces = []
for i in range(len(rows) - 1):
    for j in range(M):
        j2 = (j + 1) % M
        faces.append((i * M + j, i * M + j2, (i + 1) * M + j2, (i + 1) * M + j))
base = len(verts)
cap = oval(RING_IN[0] * 1.02, RING_IN[1] * 1.02, np.arctan2(ring_pts[0][:, 1], ring_pts[0][:, 0]))
cap3 = np.c_[cap, np.full(M, float(C.zr(42.0)))]
verts = np.vstack([verts, cap3])
for j in range(M):
    j2 = (j + 1) % M
    faces.append((j, base + j, base + j2, j2))
me = bpy.data.meshes.new("shell"); me.from_pydata(verts.tolist(), [], faces); me.update()
bm = bmesh.new(); bm.from_mesh(me); bpy.data.meshes.remove(me)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
# a closed solid (4 mm wall, inward - thick enough that the decimated LOD keeps two separate sides) so the voxel remesh of the game mesh sees a volume
res_sol = None if LOW else bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=2.6)   # bmesh solidify offsets AGAINST the normals for thickness > 0 (checked: -4 went outward and buried the plates)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
add("base_shell", bm, "TP_Lacquer")
json.dump({"xs_mm": xs.tolist(), "ztop_mm": ztop_x.tolist(), "ring_in": RING_IN, "ring_out": RING_OUT, "p": PR,
           "z_ring_bottom_mm": Z_RING_BOT, "z_mouth_mm": Z_MOUTH}, open(WORK + "/ring_profile.json", "w"), indent=1)

# ------------------------------------------------------------------ assemble
tot = 0
objs = []
for name, bm, mat in PARTS:
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(MATS[mat])
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    ob.scale = (0.001, 0.001, 0.001)
    objs.append(ob); nt_ = sum(len(p.vertices) - 2 for p in me.polygons); tot += nt_
    if LOW: print("  part", name, nt_)
bpy.ops.object.select_all(action='DESELECT')
for o in objs:
    o.select_set(True)
bpy.context.view_layer.objects.active = objs[0]
bpy.ops.object.join()
hp = bpy.context.view_layer.objects.active
hp.name = hp.data.name = "TP_Throat_LOWGEO" if LOW else "TP_Throat_HIGH"
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
for p in hp.data.polygons:
    p.use_smooth = True
me_ = hp.data
if "an" in me_.attributes and "cap" in me_.attributes:
    an = np.zeros(len(me_.vertices) * 3, np.float32); me_.attributes["an"].data.foreach_get("vector", an); an = an.reshape(-1, 3)
    cap = np.zeros(len(me_.polygons), np.int32); me_.attributes["cap"].data.foreach_get("value", cap)
    lv = np.zeros(len(me_.loops), np.int32); me_.loops.foreach_get("vertex_index", lv)
    lp = np.zeros(len(me_.loops), np.int32)
    for p_ in me_.polygons:
        lp[p_.loop_start:p_.loop_start + p_.loop_total] = p_.index
    ln = an[lv].copy()
    ln[cap[lp] == 0] = 0.0                       # zero = keep Blender's own normal (walls, bevels, spheres, ring, shell)
    ln[np.linalg.norm(ln, axis=1) < 0.5] = 0.0
    me_.normals_split_custom_set(ln.tolist())
    me_.attributes.remove(me_.attributes["an"])
    print("custom cap normals set on", int((np.linalg.norm(ln, axis=1) > 0.5).sum()), "loops", flush=True)
if "cap" in me_.attributes:
    me_.attributes.remove(me_.attributes["cap"])
print("HIGH parts", len(PARTS), "tris", tot, "verts", len(hp.data.vertices), "mats", [m.name for m in hp.data.materials], flush=True)
if LOW:
    bm = bmesh.new(); bm.from_mesh(hp.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(hp.data); bm.free()
    print("LOWGEO tris", len(hp.data.polygons), flush=True)
bpy.ops.wm.save_as_mainfile(filepath=WORK + ("/tp_lowgeo.blend" if LOW else "/tp_high.blend"))
