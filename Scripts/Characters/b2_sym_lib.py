"""b2_sym_lib.py - PRIVATE / DO NOT SHIP. Shared helpers of the 2B symmetry step (b2_sym_*.py). Blender 5.2 headless.

Paths (all absolute), the topological mirror map of the skin (copied from b2_rig_apose.mirror_map / walk, which
cannot be imported because that module runs its build on import), region labels and the asymmetry metrics.
Writes nothing by itself.
"""
import bpy, bmesh, os, sys, json, math, time
from collections import deque, Counter
import numpy as np
from mathutils import Vector, Matrix

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
OUT = ROOT + "/WorkFiles/Characters/2B_private"
RIG_BLEND = OUT + "/2B_private_rig.blend"            # read-only input
SYM_BLEND = OUT + "/2B_private_rig_sym.blend"        # output
EXPORT_DIR = OUT + "/export_sym"
FBX = EXPORT_DIR + "/SK_2B_Private.fbx"
TEX_DIR = EXPORT_DIR + "/textures"
RENDERS = OUT + "/sym_renders"
CHECKS = OUT + "/checks_sym"
REPORT = OUT + "/stepSym_report.json"
MH_BLEND = ROOT + "/References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend"  # read-only
SHELL = ["Body", "Face", "Lips", "Head", "Ears", "Legs", "Arms", "Fingernails", "Toenails", "EyeSocket", "Mouth"]
MESHES = ["SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments"]
MIDLINE_BONES = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head"]
FIN = ("thumb", "index", "middle", "ring", "pinky")
M3 = np.array([-1.0, 1.0, 1.0])


def log(*a):
    print("[sym]", *a, flush=True)


def argv():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)


def other(n):
    if n.endswith("_l"):
        return n[:-2] + "_r"
    if n.endswith("_r"):
        return n[:-2] + "_l"
    return n


def co_array(me):
    X = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", X)
    return X.reshape(-1, 3)


def set_co(me, X):
    me.vertices.foreach_set("co", np.ascontiguousarray(X, dtype=np.float64).reshape(-1).astype(np.float32))
    me.update()


# ------------------------------------------------------------------------------------------------ topology mirror
def walk(bm, e):
    """Face walk from edge e: the two faces of e are each other's mirror (copied from b2_rig_apose.walk)."""
    fa, fb = e.link_faces
    v0, v1 = e.verts
    la = next(l for l in fa.loops if l.vert == v0 and l.link_loop_next.vert == v1) if any(
        l.vert == v0 and l.link_loop_next.vert == v1 for l in fa.loops) else None
    if la is None:
        la = next(l for l in fa.loops if l.vert == v1 and l.link_loop_next.vert == v0)
        v0, v1 = v1, v0
    lb = next((l for l in fb.loops if l.vert == v0), None)
    if lb is None:
        return None
    mv = [-1] * len(bm.verts)
    fmap = {}
    q = deque([(la, lb)])
    fmap[fa.index] = fb.index
    fmap[fb.index] = fa.index
    while q:
        l, m = q.popleft()
        if len(l.face.verts) != len(m.face.verts):
            return None
        a, b = l, m
        for _ in range(len(l.face.verts)):
            vi, wi = a.vert.index, b.vert.index
            if mv[vi] == -1:
                mv[vi] = wi
            elif mv[vi] != wi:
                return None
            if mv[wi] == -1:
                mv[wi] = vi
            elif mv[wi] != vi:
                return None
            r = a.link_loop_radial_next
            rb = b.link_loop_prev.link_loop_radial_next
            if r.face.index not in fmap:
                rb2 = rb.link_loop_next
                if rb2.face.index in fmap and fmap[rb2.face.index] != r.face.index:
                    return None
                fmap[r.face.index] = rb2.face.index
                fmap[rb2.face.index] = r.face.index
                q.append((r, rb2))
            a = a.link_loop_next; b = b.link_loop_prev
    return mv, fmap


def mirror_map(me, zlo, zhi, max_tries=400):
    """Topological mirror map of a closed, mirror-symmetric quad shell. Seeds: near-vertical edges close to the
    torso centre line (per-height midpoint of the torso slice, the shell's midline wanders), each tried by a face walk;
    the walk that reaches every face, is an involution and has the smallest geometric mirror error wins.
    Returns dict(mv, fmap, med_err, seeds_tried)."""
    X = co_array(me)
    bm = bmesh.new(); bm.from_mesh(me)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()
    zs = np.linspace(zlo, zhi, 11)
    cxs = []
    for z in zs:
        sel = np.abs(X[:, 2] - z) < 0.01
        sel &= np.abs(X[:, 0]) < 0.2
        cxs.append((X[sel, 0].min() + X[sel, 0].max()) / 2 if sel.any() else 0.0)

    def cx(z):
        return float(np.interp(z, zs, cxs))
    cands = []
    for e in bm.edges:
        a, b = e.verts
        if zlo < a.co.z < zhi and zlo < b.co.z < zhi and len(e.link_faces) == 2:
            da = abs(a.co.x - cx(a.co.z)); db = abs(b.co.x - cx(b.co.z))
            if da < 0.015 and db < 0.015 and abs(a.co.z - b.co.z) > abs(a.co.x - b.co.x):
                cands.append((da + db, e.index))
    cands.sort()
    best = None
    tried = 0
    for _, ei in cands[:max_tries]:
        e = bm.edges[ei]
        tried += 1
        res = walk(bm, e)
        if res is None:
            continue
        mv, fmap = res
        if len(fmap) != len(bm.faces) or min(mv) < 0:
            continue
        mv = np.array(mv)
        if not (mv[mv] == np.arange(len(mv))).all():
            continue
        sel = np.nonzero((X[:, 2] > zlo) & (X[:, 2] < zhi))[0]
        err = np.abs(X[sel, 0] - cx_arr(X[sel, 2], zs, cxs) + X[mv[sel], 0] - cx_arr(X[mv[sel], 2], zs, cxs)) + np.abs(X[sel, 2] - X[mv[sel], 2])
        med = float(np.median(err))
        selfm = int((mv == np.arange(len(mv))).sum())
        if selfm > 100 and (best is None or med < best["med_err"]):
            best = {"mv": mv, "fmap": dict(fmap), "med_err": med}
            if med < 0.01:
                break
    bm.free()
    if best:
        best["seeds_tried"] = tried
    return best


def cx_arr(z, zs, cxs):
    return np.interp(z, zs, cxs)


# ------------------------------------------------------------------------------------------------ regions / metrics
def weights_matrix(obj, names):
    idx = {n: i for i, n in enumerate(names)}
    gi = {g.index: idx.get(g.name) for g in obj.vertex_groups}
    W = np.zeros((len(obj.data.vertices), len(names)))
    for v in obj.data.vertices:
        for g in v.groups:
            j = gi.get(g.group)
            if j is not None:
                W[v.index, j] = g.weight
    return W


def vert_src(me):
    src = np.zeros(len(me.polygons), dtype=int)
    me.attributes["src"].data.foreach_get("value", src)
    vs = [set() for _ in range(len(me.vertices))]
    for p, s in zip(me.polygons, src):
        for v in p.vertices:
            vs[v].add(SHELL[s])
    return vs


def skin_regions(X, W, order, vsrc):
    """Region label per skin vertex: face / neck / torso / breasts / pelvis / arms / hands / legs / feet.
    Dominant bone decides; face = Face/Lips/EyeSocket/Mouth/Ears surfaces or head-dominant; breasts = front chest
    skin (spine_03..05 dominant, in front of the ribcage, 1.12..1.32 m, 1.5..15 cm off the midline)."""
    dom = np.array(order)[W.argmax(axis=1)]
    reg = np.array(["torso"] * len(X), dtype=object)
    for i, b in enumerate(dom):
        s = vsrc[i]
        if s & {"Face", "Lips", "EyeSocket", "Mouth", "Ears"} or b == "head":
            reg[i] = "face"
        elif b.startswith("neck"):
            reg[i] = "neck"
        elif b.startswith(("hand", "thumb", "index", "middle", "ring", "pinky")) or s & {"Fingernails"}:
            reg[i] = "hands"
        elif b.startswith(("clavicle", "upperarm", "lowerarm")) or "Arms" in s:
            reg[i] = "arms" if not b.startswith("clavicle") or "Arms" in s else "torso"
        elif b.startswith(("foot", "ball")) or s & {"Toenails"}:
            reg[i] = "feet"
        elif b.startswith(("thigh", "calf")):
            reg[i] = "legs"
        elif b in ("pelvis", "spine_01"):
            reg[i] = "pelvis"
    # breasts: front chest
    chest = (reg == "torso") & (X[:, 2] > 1.12) & (X[:, 2] < 1.32) & (np.abs(X[:, 0]) > 0.015) & (np.abs(X[:, 0]) < 0.15)
    if chest.any():
        yfront = np.percentile(X[chest, 1], 50)
        reg[chest & (X[:, 1] < yfront)] = "breasts"
    return reg


def stats(d):
    if len(d) == 0:
        return None
    return {"mean_mm": round(float(d.mean()) * 1000, 3), "p95_mm": round(float(np.percentile(d, 95)) * 1000, 3),
            "max_mm": round(float(d.max()) * 1000, 3), "n": int(len(d))}


def sym_error(X, mv):
    """Per vertex |p - M p_twin| (M: x -> -x about x = 0)."""
    return np.linalg.norm(X - X[mv] * M3, axis=1)


def fit_plane(X, mv, sel=None):
    """Best-fit sagittal plane from twin pairs: normal = principal direction of (p - p_twin), offset = mean n.midpoint.
    Returns (n, d, yaw_deg, roll_deg, residual_mean_mm)."""
    idx = np.arange(len(X)) if sel is None else np.nonzero(sel)[0]
    idx = idx[mv[idx] != idx]
    P = X[idx]; Q = X[mv[idx]]
    D = P - Q
    C = D.T @ D
    w, V = np.linalg.eigh(C)
    n = V[:, -1]
    if n[0] < 0:
        n = -n
    mid = (P + Q) / 2
    d = float((mid @ n).mean())
    # reflect P about the plane and compare with Q
    refl = P - 2 * ((P @ n) - d)[:, None] * n[None, :]
    res = np.linalg.norm(refl - Q, axis=1)
    yaw = math.degrees(math.atan2(n[1], n[0]))   # rotation about Z
    roll = math.degrees(math.atan2(n[2], n[0]))  # tilt about Y
    return n, d, yaw, roll, float(res.mean())


def plane_report(X, mv, sel=None, z_ref=None):
    n, d, yaw, roll, res = fit_plane(X, mv, sel)
    idx = np.arange(len(X)) if sel is None else np.nonzero(sel)[0]
    zc = float(X[idx, 2].mean()) if z_ref is None else z_ref
    yc = float(X[idx, 1].mean())
    # x of the plane at the region centre (y = yc, z = zc): n.x*x + n.y*yc + n.z*zc = d
    x_at = (d - n[1] * yc - n[2] * zc) / n[0]
    return {"normal": [round(float(v), 5) for v in n], "yaw_deg": round(yaw, 3), "roll_deg": round(roll, 3),
            "x_offset_at_region_centre_mm": round(x_at * 1000, 2), "centre_z_m": round(zc, 3),
            "mean_residual_after_best_plane_mm": round(res * 1000, 3)}


def measure_skin(X, mv, reg):
    d = sym_error(X, mv)
    out = {"all": stats(d)}
    for r in ("face", "neck", "torso", "breasts", "pelvis", "arms", "hands", "legs", "feet"):
        out[r] = stats(d[reg == r])
    selfm = mv == np.arange(len(X))
    out["midline_abs_x"] = stats(np.abs(X[selfm, 0]))
    return out, d


def bone_asym(arm):
    """Joint asymmetry of the rest skeleton: midline heads/tails |x|, pairs |h_l - M h_r| (and tails), and the
    orientation difference of each pair after mirroring (deg), midline bones' axis tilt off the sagittal plane."""
    bones = arm.data.bones
    out = {"midline": {}, "pairs": {}}
    Mm = Matrix.Diagonal((-1, 1, 1))
    for b in bones:
        n = b.name
        if n == other(n):
            R = b.matrix_local.to_3x3()
            # a bone lies in the sagittal plane when its Y (length) axis and X/Z axes are either in it or normal to it:
            # measure how far the mirrored rest matrix is from itself with axes reinterpreted (M R M vs R with x-axis flip)
            Rm = Mm @ R @ Mm
            # in the MH convention the midline bone Z axis is +-X world (normal to the plane): Rm then equals R with its
            # X and Y columns unchanged and Z negated... compare the Y axis and the normal-direction column
            ydev = math.degrees(math.asin(min(1.0, abs(R.col[1].x))))
            out["midline"][n] = {"head_x_mm": round(b.head_local.x * 1000, 3), "tail_x_mm": round(b.tail_local.x * 1000, 3),
                                 "y_axis_off_plane_deg": round(ydev, 4)}
        elif n.endswith("_l"):
            r = bones[other(n)]
            dh = (b.head_local - Mm @ r.head_local).length
            dt = (b.tail_local - Mm @ r.tail_local).length
            out["pairs"][n[:-2]] = {"head_mm": round(dh * 1000, 3), "tail_mm": round(dt * 1000, 3)}
    hs = [v["head_mm"] for v in out["pairs"].values()]
    out["pairs_head_max_mm"] = max(hs)
    out["pairs_head_mean_mm"] = round(float(np.mean(hs)), 3)
    out["midline_head_max_abs_x_mm"] = max(abs(v["head_x_mm"]) for v in out["midline"].values())
    return out


# ------------------------------------------------------------------------------------------------ fit checks
from mathutils.bvhtree import BVHTree  # noqa: E402
from mathutils.kdtree import KDTree  # noqa: E402


def vertex_normals(me):
    n = np.zeros(len(me.vertices) * 3)
    me.vertex_normals.foreach_get("vector", n)
    return n.reshape(-1, 3)


def garment_clearance(skin_me, gar, under_i):
    """signed distance of every garment vertex to the skin (skin normal side); boundary lip vertices listed apart."""
    X = co_array(skin_me)
    polys = [tuple(p.vertices) for p in skin_me.polygons]
    tree = BVHTree.FromPolygons([Vector(c) for c in X], polys)
    gme = gar.data
    gbm = bmesh.new(); gbm.from_mesh(gme)
    gbm.verts.ensure_lookup_table()
    res = {"bandeau": [], "briefs": [], "lip": []}
    under = set()
    for p in gme.polygons:
        if p.material_index == under_i:
            under.update(p.vertices)
    top_b = set()
    for v in gbm.verts:
        if v.is_boundary and v.index not in under:
            top_b.add(v.index)
            for e in v.link_edges:
                top_b.add(e.other_vert(v).index)
    gbm.free()
    for v in gme.vertices:
        loc, nrm, fi, d = tree.find_nearest(v.co)
        sd = (v.co - loc).dot(nrm)
        key = "briefs" if v.index in under else ("lip" if v.index in top_b else "bandeau")
        res[key].append(sd)
    out = {}
    for k, a in res.items():
        a = np.array(a)
        out[k] = {"min_mm": round(float(a.min()) * 1000, 2), "p1_mm": round(float(np.percentile(a, 1)) * 1000, 2),
                  "median_mm": round(float(np.median(a)) * 1000, 2), "below_1mm": int((a < 0.001).sum()),
                  "inside_skin": int((a < 0).sum()), "n": int(len(a))}
    return out


def skin_poke(skin_me, gar):
    """skin vertices under a garment footprint (within 8 mm, same facing) and their depth below the garment."""
    X = co_array(skin_me)
    N = vertex_normals(skin_me)
    gme = gar.data
    gX = co_array(gme)
    gpolys = [tuple(p.vertices) for p in gme.polygons]
    gtree = BVHTree.FromPolygons([Vector(c) for c in gX], gpolys)
    sds = []
    where = []
    for i in range(len(X)):
        loc, gn, fi, d = gtree.find_nearest(Vector(X[i]), 0.008)
        if loc is None:
            continue
        vs = gpolys[fi]
        fn = (Vector(gX[vs[1]]) - Vector(gX[vs[0]])).cross(Vector(gX[vs[2]]) - Vector(gX[vs[0]])).normalized()
        if fn.dot(Vector(N[i])) < 0.6:
            continue
        sds.append((Vector(X[i]) - loc).dot(fn))
        if sds[-1] > 0:
            where.append([int(i), [round(float(x), 4) for x in X[i]], round(sds[-1] * 1000, 3), int(fi)])
    a = np.array(sds)
    return {"through_list": where, "covered_skin_verts": int(len(a)), "min_gap_mm": round(float(-a.max()) * 1000, 3),
            "verts_closer_than_1.9mm": int((a > -0.0019).sum()), "verts_through_garment": int((a > 0).sum())}


def eye_lid_check(skin_me, hp):
    """Eyelid / eyeball fit per side: skin vertices of the front half of the eye region (y < eye centre) that lie INSIDE
    the eyeball (sclera + cornea): a ray from the vertex to the eye centre that does not cross the eye surface first."""
    X = co_array(skin_me)
    me = hp.data
    mats = [m.name for m in me.materials]
    ids = {mats.index("M_2B_Sclera"), mats.index("M_2B_Cornea")}
    H = co_array(me)
    polys = [tuple(p.vertices) for p in me.polygons if p.material_index in ids]
    out = {}
    for side, sgn in (("l", 1), ("r", -1)):
        ps = [p for p in polys if sgn * H[p[0], 0] > 0]
        vs = sorted({v for p in ps for v in p})
        c = H[vs].mean(axis=0)
        r = float(np.linalg.norm(H[vs] - c, axis=1).max())
        tree = BVHTree.FromPolygons([Vector(x) for x in H], ps)
        d = np.linalg.norm(X - c, axis=1)
        cand = np.nonzero((d < r + 0.003) & (X[:, 1] < c[1]))[0]
        inside = []
        for i in cand:
            p = Vector(X[i]); dirv = Vector(c) - p
            L = dirv.length
            hit = tree.ray_cast(p, dirv.normalized(), L)
            if hit[0] is None:
                inside.append(i)
        out[side] = {"eye_centre_mm": [round(float(x) * 1000, 2) for x in c], "front_skin_verts_checked": int(len(cand)),
                     "skin_verts_inside_eyeball": len(inside)}
    return out


def feet_check(X, reg, arm):
    """heel / ball contact per foot: lowest heel vertex (behind the ankle) and lowest forefoot vertex (around the ball
    joint), in mm above z = 0."""
    out = {}
    for s_, sel in (("l", X[:, 0] > 0), ("r", X[:, 0] < 0)):
        f = (reg == "feet") & sel
        ank = arm.data.bones[f"foot_{s_}"].head_local
        P = X[f]
        heel = P[P[:, 1] > ank.y - 0.01]
        ball = P[np.abs(P[:, 1] - arm.data.bones[f"ball_{s_}"].head_local.y) < 0.025]
        out[s_] = {"heel_min_z_mm": round(float(heel[:, 2].min()) * 1000, 3), "ball_min_z_mm": round(float(ball[:, 2].min()) * 1000, 3),
                   "sole_tilt_deg": round(math.degrees(math.atan2(float(heel[:, 2].min() - ball[:, 2].min()),
                                                                  float(heel[:, 1].mean() - ball[:, 1].mean()))), 3)}
    return out
