"""b2_sym_check.py - PRIVATE / DO NOT SHIP. Independent adversarial checker of the symmetry fix (never saves any blend).

  blender -b <rig blend> -P b2_sym_check.py -- geo <abs out json>
      skin mirror asymmetry via geometric nearest-surface correspondence (not the builder's map), skeleton,
      weights, eyes / teeth / lashes, garments at rest and in walk / run / squat, midline crease, mesh quality.
      When the open blend is the sym blend, the step C1 rig blend is linked read-only for before/after mesh quality.
  blender -b --factory-startup -P b2_sym_check.py -- fbx <abs fbx> <abs out json>
  blender -b <rig blend> -P b2_sym_check.py -- render <abs out dir> <prefix>
"""
import bpy, bmesh, os, sys, json, math, time
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = "C:/Users/Cody/Desktop/Blender_Projects"
OUT = ROOT + "/WorkFiles/Characters/2B_private"
RIG_BLEND = OUT + "/2B_private_rig.blend"
MH_BLEND = ROOT + "/References/Characters/MH_PlayerDefault/MH_PlayerDefault_FitBody.blend"
SHELL = ["Body", "Face", "Lips", "Head", "Ears", "Legs", "Arms", "Fingernails", "Toenails", "EyeSocket", "Mouth"]
MID = ["pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01", "neck_02", "head"]
M3 = np.array([-1.0, 1.0, 1.0])


def log(*a):
    print("[chk]", *a, flush=True)


def args():
    return sys.argv[sys.argv.index("--") + 1:]


def save(path, data):
    assert os.path.isabs(path), path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1, default=float)


def co(me):
    a = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def st(d, scale=1000.0):
    d = np.asarray(d, dtype=float)
    if len(d) == 0:
        return None
    return {"mean": round(float(d.mean()) * scale, 4), "p95": round(float(np.percentile(d, 95)) * scale, 4),
            "p99": round(float(np.percentile(d, 99)) * scale, 4), "max": round(float(d.max()) * scale, 4), "n": int(len(d))}


def polys_of(me, sel=None):
    return [tuple(p.vertices) for p in me.polygons if sel is None or sel(p)]


def bvh(X, polys):
    return BVHTree.FromPolygons([Vector(c) for c in X], polys)


def near_dist(tree, P):
    out = np.zeros(len(P))
    for i, p in enumerate(P):
        loc, n, fi, d = tree.find_nearest(Vector(p))
        out[i] = d if d is not None else 1e9
    return out


def face_src(me):
    src = np.zeros(len(me.polygons), dtype=int)
    me.attributes["src"].data.foreach_get("value", src)
    return src


def vert_src_sets(me):
    src = face_src(me)
    vs = [set() for _ in range(len(me.vertices))]
    for p, s in zip(me.polygons, src):
        for v in p.vertices:
            vs[v].add(SHELL[s])
    return vs


def weights(obj, names):
    idx = {n: i for i, n in enumerate(names)}
    gi = {g.index: idx.get(g.name) for g in obj.vertex_groups}
    W = np.zeros((len(obj.data.vertices), len(names)))
    ninf = np.zeros(len(obj.data.vertices), dtype=int)
    for v in obj.data.vertices:
        for g in v.groups:
            j = gi.get(g.group)
            if j is not None and g.weight > 0:
                W[v.index, j] = g.weight
                ninf[v.index] += 1
    return W, ninf


def swap_lr(n):
    if n.endswith("_l"):
        return n[:-2] + "_r"
    if n.endswith("_r"):
        return n[:-2] + "_l"
    return n


def mirror_twin(X, tol=None):
    kd = KDTree(len(X))
    for i, p in enumerate(X):
        kd.insert(Vector(p), i)
    kd.balance()
    tw = np.zeros(len(X), dtype=int); dd = np.zeros(len(X))
    for i, p in enumerate(X):
        q, j, d = kd.find(Vector(p * M3))
        tw[i] = j; dd[i] = d
    return tw, dd


# ================================================================================================ GEO
def rot_angle(Ra, Rb):
    R = Ra.transposed() @ Rb
    c = (R[0][0] + R[1][1] + R[2][2] - 1) / 2
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def skeleton(arm, mh):
    Mm = Matrix.Diagonal((-1, 1, 1))
    B = arm.data.bones
    mid = {}
    for n in MID:
        b = B[n]
        R = b.matrix_local.to_3x3().normalized()
        # a sagittal bone: its Y and one of X/Z lie in the plane (x comp 0) and the remaining axis is +-X
        mid[n] = {"head_x_mm": round(b.head_local.x * 1000, 4), "tail_x_mm": round(b.tail_local.x * 1000, 4),
                  "axes_x": [round(R.col[k].x, 5) for k in range(3)]}
    pairs = {}
    for b in B:
        if not b.name.endswith("_l"):
            continue
        r = B[swap_lr(b.name)]
        Rl = b.matrix_local.to_3x3().normalized(); Rr = r.matrix_local.to_3x3().normalized()
        Rrm = Mm @ Rr @ Mm  # mirrored rotation (det +1): axes of the reflected frame with x-axis sign conventions
        # compare each axis up to sign (UE mirrors by flipping axis signs)
        dev = 0.0
        for k in range(3):
            a = Rl.col[k]; m = Mm @ Rr.col[k]
            dev = max(dev, math.degrees(math.acos(min(1.0, abs(a.dot(m))))))
        pairs[b.name[:-2]] = {"head_mm": round((b.head_local - Mm @ r.head_local).length * 1000, 4),
                              "tail_mm": round((b.tail_local - Mm @ r.tail_local).length * 1000, 4),
                              "axis_dev_deg": round(dev, 4), "roll_l": round(math.degrees(b.matrix_local.to_3x3().to_euler().y), 3)}
    out = {"n_bones": len(B), "midline": mid,
           "midline_max_abs_x_mm": max(max(abs(v["head_x_mm"]), abs(v["tail_x_mm"])) for v in mid.values()),
           "pairs_max_head_mm": max(v["head_mm"] for v in pairs.values()),
           "pairs_max_tail_mm": max(v["tail_mm"] for v in pairs.values()),
           "pairs_max_axis_dev_deg": max(v["axis_dev_deg"] for v in pairs.values()),
           "worst_pairs": sorted(pairs.items(), key=lambda kv: -max(kv[1]["head_mm"], kv[1]["axis_dev_deg"]))[:5]}
    if mh is not None:
        MB = mh.data.bones
        devs = {}
        for b in B:
            if b.name not in MB:
                devs[b.name] = None
                continue
            m = MB[b.name]
            Ra = (arm.matrix_world.to_3x3() @ b.matrix_local.to_3x3()).normalized()
            Rb = (mh.matrix_world.to_3x3() @ m.matrix_local.to_3x3()).normalized()
            ya = Ra.col[1]; yb = Rb.col[1]
            ydev = math.degrees(math.acos(max(-1, min(1, ya.dot(yb)))))
            devs[b.name] = {"full_deg": round(rot_angle(Ra, Rb), 3), "dir_deg": round(ydev, 3),
                            "parent_match": (b.parent.name if b.parent else None) == (m.parent.name if m.parent else None)}
        vals = [v for v in devs.values() if v]
        out["vs_mh"] = {"missing": [k for k, v in devs.items() if v is None],
                        "parents_all_match": all(v["parent_match"] for v in vals),
                        "full_deg_max": max(v["full_deg"] for v in vals), "full_deg_mean": round(float(np.mean([v["full_deg"] for v in vals])), 3),
                        "dir_deg_max": max(v["dir_deg"] for v in vals),
                        "per_bone": devs}
    return out


def eye_fit(H, polys):
    vs = sorted({v for p in polys for v in p})
    P = H[vs]
    # algebraic sphere fit
    A = np.c_[2 * P, np.ones(len(P))]
    b = (P ** 2).sum(1)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    c = sol[:3]; r = math.sqrt(sol[3] + c @ c)
    return c, r, vs


def geo(outp):
    t0 = time.time()
    res = {"blend": bpy.data.filepath}
    body = bpy.data.objects["SK_2B_Body"]; hp = bpy.data.objects["SK_2B_HeadParts"]; gar = bpy.data.objects["SK_2B_Garments"]
    arm = bpy.data.objects["root"]
    for o in (body, hp, gar):
        assert o.matrix_world == Matrix.Identity(4) or np.allclose(np.array(o.matrix_world), np.eye(4)), o.name
    me = body.data
    X = co(me)
    polys = polys_of(me)
    tree = bvh(X * M3, polys)  # the MIRRORED skin surface
    # ---- (1) skin asymmetry: nearest point on the mirrored surface
    d = near_dist(tree, X)
    names = [b.name for b in arm.data.bones]
    W, ninf = weights(body, names)
    head_i = names.index("head")
    vsrc = vert_src_sets(me)
    face_sel = np.array([bool(s & {"Face", "Lips", "EyeSocket", "Mouth", "Ears"}) or (W[i, head_i] > 0.5 and X[i, 2] > 1.45)
                         for i, s in enumerate(vsrc)])
    res["skin_surface_asym_mm"] = {"all": st(d), "face": st(d[face_sel]), "body_nonface": st(d[~face_sel]),
                                   "worst_verts": [[int(i), [round(float(x), 4) for x in X[i]], round(float(d[i]) * 1000, 3)]
                                                   for i in np.argsort(-d)[:5]]}
    tw, dd = mirror_twin(X)
    res["skin_vertex_twin_mm"] = {"all": st(dd), "face": st(dd[face_sel]),
                                  "involution_fraction": float((tw[tw] == np.arange(len(X))).mean()),
                                  "self_twins": int((tw == np.arange(len(X))).sum())}
    selfm = tw == np.arange(len(X))
    res["skin_midline_abs_x_mm"] = st(np.abs(X[selfm, 0]))
    log("skin done", round(time.time() - t0, 1))
    # ---- (2) skeleton
    mh = None
    try:
        with bpy.data.libraries.load(MH_BLEND, link=True) as (src, dst):
            dst.objects = ["root"]
        mh = dst.objects[0]
    except Exception as e:  # noqa
        res["mh_load_error"] = str(e)
    res["skeleton"] = skeleton(arm, mh)
    # ---- (3) weights
    sums = W.sum(1)
    swap = np.array([names.index(swap_lr(n)) for n in names])
    Wt = W[tw][:, swap]
    good = dd < 1e-5
    wdiff = np.abs(W - Wt).max(1)
    res["weights"] = {"sum_min": float(sums.min()), "sum_max": float(sums.max()), "unweighted": int((sums < 1e-6).sum()),
                      "max_influences": int(ninf.max()), "verts_over_8": int((ninf > 8).sum()),
                      "mirror_twin_exact_verts": int(good.sum()), "mirror_max_abs_diff": float(wdiff[good].max()),
                      "mirror_verts_diff_gt_0.01": int((wdiff[good] > 0.01).sum())}
    # face / eye region: shell surfaces Face / Lips / EyeSocket / Mouth (ears reported apart)
    fz = np.array([bool(s & {"Face", "Lips", "EyeSocket", "Mouth"}) and not (s - {"Face", "Lips", "EyeSocket", "Mouth"}) for s in vsrc])
    hw = W[:, head_i]
    bad = np.nonzero(fz & (hw < 0.999))[0]
    res["weights"]["face_zone"] = {"verts": int(fz.sum()), "not_100_head": int(len(bad)),
                                   "min_head_w": float(hw[fz].min()),
                                   "not_100_head_z_range": [float(X[bad, 2].min()), float(X[bad, 2].max())] if len(bad) else None,
                                   "not_100_head_samples": [[int(i), [round(float(x), 4) for x in X[i]], round(float(hw[i]), 4), sorted(vsrc[i])] for i in bad[:12]]}
    # eye-socket / lids: everything within 3 cm of an eye centre must be 100% head
    Hh = co(hp.data)
    mats = [m.name for m in hp.data.materials]
    mi = np.zeros(len(hp.data.polygons), dtype=int); hp.data.polygons.foreach_get("material_index", mi)
    eye_ids = {mats.index("M_2B_Sclera"), mats.index("M_2B_Cornea")}
    eyes = {}
    for side, sg in (("l", 1), ("r", -1)):
        ps = [tuple(p.vertices) for p in hp.data.polygons if p.material_index in eye_ids and sg * Hh[p.vertices[0], 0] > 0]
        c, r, vs = eye_fit(Hh, ps)
        eyes[side] = (c, r, ps, vs)
    for side in ("l", "r"):
        c = eyes[side][0]
        near = np.linalg.norm(X - c, axis=1) < 0.03
        res["weights"][f"eye_{side}_3cm_verts"] = int(near.sum())
        res["weights"][f"eye_{side}_3cm_not_100_head"] = int((near & (hw < 0.999)).sum())
    HW, hninf = weights(hp, names)
    res["weights"]["headparts_min_head_w"] = float(HW[:, head_i].min())
    GW, gninf = weights(gar, names)
    gs = GW.sum(1)
    res["weights"]["garments"] = {"sum_min": float(gs.min()), "sum_max": float(gs.max()), "max_influences": int(gninf.max())}
    log("weights done", round(time.time() - t0, 1))
    # ---- (4) eyes / teeth / lashes
    cl, rl, psl, vsl = eyes["l"]; cr, rr, psr, vsr = eyes["r"]
    Pl = Hh[vsl]; Pr = Hh[vsr] * M3
    trr = bvh(Hh * M3, psr); tll = bvh(Hh, psl)
    ch = np.r_[near_dist(trr, Pl), near_dist(tll, Pr)]
    eo = {"centre_l_mm": (cl * 1000).round(3).tolist(), "centre_r_mm": (cr * 1000).round(3).tolist(),
          "radius_mm": [round(rl * 1000, 3), round(rr * 1000, 3)],
          "centre_mirror_err_mm": round(float(np.linalg.norm(cl - cr * M3)) * 1000, 4), "surface_chamfer_mm": st(ch)}
    # lid intersection: skin polys of Face/EyeSocket that dip inside the eyeball sphere IN FRONT of the eye (visible zone)
    fsrc = face_src(me)
    for side in ("l", "r"):
        c, r, ps, vs = eyes[side]
        dv = np.linalg.norm(X - c, axis=1)
        # the front cap: vertices ahead of the eye centre by more than 0.6 r (cornea side, the part the lids cover/uncover)
        front = (c[1] - X[:, 1]) > 0.6 * r
        inside = (dv < r - 0.0002) & front
        # classify the skin verts by surface
        cls = {}
        for i in np.nonzero(inside)[0]:
            k = "+".join(sorted(vsrc[i]))
            cls[k] = cls.get(k, 0) + 1
        eo[f"skin_inside_eyeball_front_{side}"] = {"n": int(inside.sum()), "depth_max_mm": round(float((r - dv[inside]).max()) * 1000, 3) if inside.any() else 0.0,
                                                  "by_surface": cls}
        # visible sclera/cornea check: ray from the eye verts straight forward (-Y); count front eye verts whose ray hits
        # skin within 1 mm... (not a defect metric; skipped)
    tv = [i for i, p in enumerate(hp.data.polygons) if mats[p.material_index] == "M_2B_Teeth"]
    tverts = sorted({v for i in tv for v in hp.data.polygons[i].vertices})
    skin_tree = bvh(X, polys)
    sd = []
    for i in tverts:
        loc, n, fi, dist = skin_tree.find_nearest(Vector(Hh[i]))
        sd.append((Vector(Hh[i]) - loc).dot(n))
    sd = np.array(sd)
    # skin normals: outward. teeth outside the skin = positive
    T = Hh[tverts]
    eo["teeth"] = {"verts": len(tverts), "outside_skin": int((sd > 0).sum()), "max_outside_mm": round(float(sd.max()) * 1000, 3),
                   "centroid_x_mm": round(float(T[:, 0].mean()) * 1000, 3), "x_range_mm": [round(float(T[:, 0].min()) * 1000, 2), round(float(T[:, 0].max()) * 1000, 2)]}
    # lashes: per connected lash card, the min distance of the card to the skin (root on the lid)
    lv = [p for p in hp.data.polygons if mats[p.material_index] == "M_2B_Eyelashes"]
    lverts = sorted({v for p in lv for v in p.vertices})
    parent = {v: v for v in lverts}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for p in lv:
        vs_ = list(p.vertices)
        for v in vs_[1:]:
            ra, rb = find(vs_[0]), find(v)
            if ra != rb:
                parent[ra] = rb
    comps = {}
    for v in lverts:
        comps.setdefault(find(v), []).append(v)
    ld = near_dist(skin_tree, Hh[lverts])
    ldm = dict(zip(lverts, ld))
    cm = []
    for k, vs_ in comps.items():
        cm.append((min(ldm[v] for v in vs_), float(Hh[vs_, 0].mean()), len(vs_)))
    cm = np.array(cm)
    eo["lashes"] = {"components": int(len(cm)), "left": int((cm[:, 1] > 0).sum()), "right": int((cm[:, 1] < 0).sum()),
                    "root_gap_mm": st(cm[:, 0]), "cards_root_gap_gt_1mm": int((cm[:, 0] > 0.001).sum()),
                    "cards_root_gap_gt_2mm": int((cm[:, 0] > 0.002).sum())}
    # head parts mirror chamfer overall
    alltree = bvh(Hh * M3, polys_of(hp.data))
    hd = near_dist(alltree, Hh)
    eo["headparts_mirror_chamfer_mm"] = st(hd)
    # sharp faces on head parts
    sf = hp.data.attributes.get("sharp_face")
    if sf:
        a = np.zeros(len(hp.data.polygons), dtype=bool); sf.data.foreach_get("value", a)
        eo["headparts_sharp_faces"] = int(a.sum())
    else:
        eo["headparts_sharp_faces"] = "no attribute (all smooth)"
    sfb = me.attributes.get("sharp_face")
    if sfb:
        a = np.zeros(len(me.polygons), dtype=bool); sfb.data.foreach_get("value", a)
        eo["skin_sharp_faces"] = int(a.sum())
    res["headparts"] = eo
    log("headparts done", round(time.time() - t0, 1))
    # ---- garments mirror + rest poke
    G = co(gar.data)
    gpolys = polys_of(gar.data)
    gmi = np.zeros(len(gar.data.polygons), dtype=int); gar.data.polygons.foreach_get("material_index", gmi)
    gd = near_dist(bvh(G * M3, gpolys), G)
    res["garments_mirror_mm"] = st(gd)
    res["garment_poke_rest"] = poke(X, polys, G, gpolys, gmi, [m.name for m in gar.data.materials])
    log("rest poke done", round(time.time() - t0, 1))
    # ---- midline crease: dihedral across midline edges (both verts self-twins) vs the other edges nearby
    bm = bmesh.new(); bm.from_mesh(me); bm.edges.ensure_lookup_table(); bm.normal_update()
    mid_dih = []; mid_where = []
    for e in bm.edges:
        a, b = e.verts
        if selfm[a.index] and selfm[b.index] and len(e.link_faces) == 2:
            f1, f2 = e.link_faces
            ang = math.degrees(f1.normal.angle(f2.normal, 0.0))
            mid_dih.append(ang); mid_where.append((ang, [round(x, 4) for x in ((a.co + b.co) / 2)]))
    nb_dih = []
    for e in bm.edges:
        a, b = e.verts
        if len(e.link_faces) == 2 and (abs(a.co.x) < 0.03) and not (selfm[a.index] and selfm[b.index]):
            f1, f2 = e.link_faces
            nb_dih.append(math.degrees(f1.normal.angle(f2.normal, 0.0)))
    bnd_mid = sum(1 for e in bm.edges if e.is_boundary and abs(e.verts[0].co.x) < 1e-4 and abs(e.verts[1].co.x) < 1e-4)
    mid_where.sort(key=lambda t: -t[0])
    res["midline_crease"] = {"midline_edges": len(mid_dih), "midline_dihedral_deg": st(mid_dih, 1.0),
                             "near_midline_other_edges_dihedral_deg": st(nb_dih, 1.0), "worst": mid_where[:8],
                             "boundary_edges_on_midline": bnd_mid}
    N = np.zeros(len(me.vertices) * 3); me.vertex_normals.foreach_get("vector", N); N = N.reshape(-1, 3)
    res["midline_normal_abs_nx"] = st(np.abs(N[selfm, 0]), 1.0)
    bm.free()
    # ---- mesh quality vs step C1 rig skin (only for the sym blend)
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(os.path.abspath(RIG_BLEND)):
        with bpy.data.libraries.load(RIG_BLEND, link=True) as (src, dst):
            dst.meshes = ["SK_2B_Body"]
        me0 = dst.meshes[0]
        X0 = co(me0)
        assert len(X0) == len(X)
        mv = np.linalg.norm(X - X0, axis=1)
        qa = {"moved_mm": st(mv)}
        fl = []; ar = []; worst = []
        for p0, p1 in zip(me0.polygons, me.polygons):
            vs_ = list(p1.vertices)
            assert vs_ == list(p0.vertices)
            n0 = Vector(np.cross(X0[vs_[1]] - X0[vs_[0]], X0[vs_[2]] - X0[vs_[0]]))
            n1 = Vector(np.cross(X[vs_[1]] - X[vs_[0]], X[vs_[2]] - X[vs_[0]]))
            a0 = p0.area; a1 = p1.area
            r_ = a1 / a0 if a0 > 1e-12 else 1.0
            ar.append(r_)
            if n0.length > 1e-12 and n1.length > 1e-12:
                fl.append(math.degrees(n0.angle(n1)))
            else:
                fl.append(0.0)
        ar = np.array(ar); fl = np.array(fl)
        # edge length ratios
        ev = np.zeros(len(me.edges) * 2, dtype=int); me.edges.foreach_get("vertices", ev); ev = ev.reshape(-1, 2)
        l0 = np.linalg.norm(X0[ev[:, 0]] - X0[ev[:, 1]], axis=1); l1 = np.linalg.norm(X[ev[:, 0]] - X[ev[:, 1]], axis=1)
        er = l1 / np.maximum(l0, 1e-9)
        cen = np.array([np.mean(X[list(p.vertices)], axis=0) for p in me.polygons])
        big = np.argsort(-np.abs(np.log(np.maximum(ar, 1e-9))))[:8]
        qa.update({"face_area_ratio_p0.1_p99.9": [round(float(np.percentile(ar, 0.1)), 3), round(float(np.percentile(ar, 99.9)), 3)],
                   "face_area_ratio_min_max": [round(float(ar.min()), 3), round(float(ar.max()), 3)],
                   "faces_area_ratio_outside_0.67_1.5": int(((ar < 0.67) | (ar > 1.5)).sum()),
                   "faces_normal_turn_gt_45": int((fl > 45).sum()), "faces_normal_turn_gt_90": int((fl > 90).sum()),
                   "edge_ratio_p0.1_p99.9": [round(float(np.percentile(er, 0.1)), 3), round(float(np.percentile(er, 99.9)), 3)],
                   "edge_ratio_min_max": [round(float(er.min()), 3), round(float(er.max()), 3)],
                   "worst_area_faces": [[int(i), round(float(ar[i]), 3), [round(float(x), 4) for x in cen[i]], SHELL[face_src(me)[i]]] for i in big]})
        # texture stretching proxy per region: area ratio stats on the face surfaces vs the rest
        fsr = face_src(me)
        facep = np.isin(fsr, [SHELL.index(s) for s in ("Face", "Lips", "EyeSocket", "Mouth")])
        qa["face_area_ratio_faces"] = {"p1": round(float(np.percentile(ar[facep], 1)), 3), "p99": round(float(np.percentile(ar[facep], 99)), 3)}
        res["quality_vs_c1"] = qa
    # feet on the floor
    res["min_z_mm"] = {"l": round(float(X[X[:, 0] > 0.02, 2].min()) * 1000, 3), "r": round(float(X[X[:, 0] < -0.02, 2].min()) * 1000, 3)}
    res["height_m"] = round(float(max(X[:, 2].max(), Hh[:, 2].max())), 4)
    # ---- (5) poses
    res["garment_poke_poses"] = pose_pokes(arm, body, gar, gmi)
    res["secs"] = round(time.time() - t0, 1)
    save(outp, res)
    log("saved", outp)


def poke(X, polys, G, gpolys, gmi, gmats, max_d=0.010):
    """Skin vertices that come out through a garment: for skin verts within max_d of a garment face whose (outward
    oriented) normal agrees with the skin normal, signed distance along the garment normal (> 0 = skin outside)."""
    skin_tree = bvh(X, polys)
    gt = bvh(G, gpolys)
    # outward orientation of each garment face: agree with the nearest skin normal
    gn = []
    for p in gpolys:
        a, b, c = G[p[0]], G[p[1]], G[p[2]]
        n = np.cross(b - a, c - a); n /= (np.linalg.norm(n) + 1e-15)
        cen = G[list(p)].mean(0)
        loc, sn, fi, d = skin_tree.find_nearest(Vector(cen))
        if sn is not None and n @ np.array(sn) < 0:
            n = -n
        gn.append(n)
    gn = np.array(gn)
    # skin vertex normals (area weighted)
    SN = np.zeros_like(X)
    for p in polys:
        a, b, c = X[p[0]], X[p[1]], X[p[2]]
        n = np.cross(b - a, c - a)
        for v in p:
            SN[v] += n
    SN /= (np.linalg.norm(SN, axis=1)[:, None] + 1e-15)
    out = {}
    for mi, mn in enumerate(gmats):
        sds = []; where = []
        for i in range(len(X)):
            loc, n, fi, d = gt.find_nearest(Vector(X[i]), max_d)
            if loc is None or gmi[fi] != mi:
                continue
            fn = gn[fi]
            if fn @ SN[i] < 0.5:
                continue
            s = float((X[i] - np.array(loc)) @ fn)
            sds.append(s)
            if s > 0:
                where.append((round(s * 1000, 3), int(i), [round(float(x), 4) for x in X[i]]))
        a = np.array(sds) if sds else np.zeros(1)
        where.sort(key=lambda t: -t[0])
        out[mn] = {"covered_skin_verts": len(sds), "skin_through": int((a > 0).sum()), "skin_through_gt_0.5mm": int((a > 0.0005).sum()),
                   "skin_through_gt_1mm": int((a > 0.001).sum()), "max_through_mm": round(float(a.max()) * 1000, 3),
                   "closest_gap_median_mm": round(float(-np.median(a)) * 1000, 3), "worst": where[:6]}
    return out


def pose_pokes(arm, body, gar, gmi):
    src = open(ROOT + "/Scripts/Characters/b2_sym_posetest.py").read()
    src = src[: src.rindex("\nmain()")]
    ns = {"__file__": ROOT + "/Scripts/Characters/b2_sym_posetest.py", "__name__": "posetest_lib"}
    sys.path.insert(0, ROOT + "/Scripts/Characters")
    exec(compile(src, "b2_sym_posetest_lib", "exec"), ns)
    ns["ARM"] = arm
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='POSE')
    out = {}
    gmats = [m.name for m in gar.data.materials]
    for name in ("walk", "run", "squat", "twist45", "arms_up"):
        fn = dict(ns["POSES"])[name]
        ns["pose_reset"](); fn(); bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        eb = body.evaluated_get(dg); m1 = eb.to_mesh(); X = co(m1); P = polys_of(m1); eb.to_mesh_clear()
        eg = gar.evaluated_get(dg); m2 = eg.to_mesh(); G = co(m2); GP = polys_of(m2); eg.to_mesh_clear()
        mw = np.array(body.matrix_world)
        X = X @ mw[:3, :3].T + mw[:3, 3]; G = G @ mw[:3, :3].T + mw[:3, 3]
        out[name] = poke(X, P, G, GP, gmi, gmats)
        log("pose", name, {k: (v["skin_through_gt_1mm"], v["max_through_mm"]) for k, v in out[name].items()})
    ns["pose_reset"]()
    bpy.ops.object.mode_set(mode='OBJECT')
    return out


# ================================================================================================ FBX
def fbx(path, outp):
    res = {"fbx": path}
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=path)
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    res["objects"] = [(o.name, o.type) for o in bpy.data.objects]
    a = arms[0]
    res["armature_object"] = a.name
    res["bones"] = len(a.data.bones)
    res["bones_plus_armature_root_node"] = len(a.data.bones) + 1
    res["bone_names_head"] = [b.name for b in a.data.bones][:5]
    zs = []; tris = 0; maxinf = 0
    dg = bpy.context.evaluated_depsgraph_get()
    for o in meshes:
        me = o.data
        X = co(me); mw = np.array(o.matrix_world)
        Xw = X @ mw[:3, :3].T + mw[:3, 3]
        zs.append((Xw[:, 2].min(), Xw[:, 2].max(), Xw[:, 0].min(), Xw[:, 0].max()))
        tris += sum(len(p.vertices) - 2 for p in me.polygons)
        for v in me.vertices:
            maxinf = max(maxinf, sum(1 for g in v.groups if g.weight > 0))
    zmin = min(z[0] for z in zs); zmax = max(z[1] for z in zs)
    res["height_m_blender_units"] = round(zmax - zmin, 4)
    res["scene_unit_scale"] = bpy.context.scene.unit_settings.scale_length
    res["mesh_scale"] = [tuple(round(x, 4) for x in o.matrix_world.to_scale()) for o in meshes]
    res["arm_scale"] = tuple(round(x, 4) for x in a.matrix_world.to_scale())
    res["x_range"] = [round(min(z[2] for z in zs), 4), round(max(z[3] for z in zs), 4)]
    res["tris"] = tris; res["max_influences"] = maxinf
    res["meshes"] = [(o.name, len(o.data.vertices)) for o in meshes]
    imgs = []
    for im in bpy.data.images:
        if im.source != 'FILE':
            continue
        fp = bpy.path.abspath(im.filepath)
        ok = os.path.exists(fp)
        try:
            loaded = im.size[0] > 0
        except Exception:  # noqa
            loaded = False
        imgs.append({"name": im.name, "path": fp, "exists": ok, "in_export_sym": "export_sym" in fp.replace("\\", "/"), "size": list(im.size)})
    res["images"] = imgs
    res["images_all_ok"] = all(i["exists"] and i["in_export_sym"] and i["size"][0] > 0 for i in imgs) and len(imgs) > 0
    # midline symmetry in the imported mesh (surface)
    body = max(meshes, key=lambda o: len(o.data.vertices))
    X = co(body.data); mw = np.array(body.matrix_world); Xw = X @ mw[:3, :3].T + mw[:3, 3]
    # FBX import may rotate the axes; find the lateral axis as the one with the smallest |mean| and a symmetric range
    res["body_bbox_min"] = Xw.min(0).round(4).tolist(); res["body_bbox_max"] = Xw.max(0).round(4).tolist()
    save(outp, res)
    log("fbx", json.dumps({k: res[k] for k in ("bones", "height_m_blender_units", "tris", "max_influences", "images_all_ok")}))


# ================================================================================================ RENDER
def render(outd, prefix):
    sys.path.insert(0, ROOT + "/Scripts/Characters")
    from b2_rig_common import enable_gpu, look_at, render_to  # noqa
    sc = bpy.context.scene
    enable_gpu()
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    for n in ("SK_2B_Body", "SK_2B_HeadParts", "SK_2B_Garments"):
        bpy.data.objects[n].hide_render = False
    cam = sc.camera or bpy.data.objects["RIG_Camera"]
    sc.camera = cam
    cam.data.type = 'PERSP'
    shots = [
        ("front", (0, -1, 0.02), (0, 0, 0.86), 5.2, 55, (900, 1500)),
        ("face", (0, -1, 0.0), (0, -0.02, 1.54), 1.05, 85, (1000, 1000)),
        ("face_tq", (0.55, -1, 0.05), (0, -0.02, 1.54), 1.05, 85, (1000, 1000)),
        ("eyes", (0, -1, 0.05), (0, -0.05, 1.56), 0.55, 85, (1400, 700)),
        ("mouth", (0, -1, 0.0), (0, -0.06, 1.475), 0.4, 85, (1000, 700)),
        ("chest_graze", (0.0, -1, -0.35), (0, -0.06, 1.25), 1.1, 70, (1000, 1000)),
        ("back", (0, 1, 0.05), (0, 0.05, 1.05), 3.2, 55, (900, 1300)),
        ("neck_side", (1, -0.35, 0.05), (0, 0, 1.47), 1.0, 85, (1000, 1000)),
    ]
    for name, dvec, c, dist, lens, resn in shots:
        sc.render.resolution_x, sc.render.resolution_y = resn
        cam.data.lens = lens
        look_at(cam, Vector(c), Vector(dvec), dist)
        render_to(f"{outd}/{prefix}_{name}.png")
    # grazing clay pass for the midline crease (key light from the side at a low angle)
    clay = bpy.data.materials.new("CHK_Clay")
    b = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (0.6, 0.6, 0.62, 1.0); b.inputs["Roughness"].default_value = 0.45
    bpy.context.view_layer.material_override = clay
    for name, dvec, c, dist, lens, resn in (("clay_face", (0, -1, 0.0), (0, -0.02, 1.54), 1.05, 85, (1000, 1000)),
                                             ("clay_torso", (0, -1, 0.0), (0, -0.05, 1.1), 2.2, 70, (900, 1100)),
                                             ("clay_back", (0, 1, 0.0), (0, 0.05, 1.1), 2.2, 70, (900, 1100))):
        sc.render.resolution_x, sc.render.resolution_y = resn
        cam.data.lens = lens
        look_at(cam, Vector(c), Vector(dvec), dist)
        render_to(f"{outd}/{prefix}_{name}.png")
    bpy.context.view_layer.material_override = None


def main():
    a = args()
    mode = a[0]
    if mode == "geo":
        geo(a[1])
    elif mode == "fbx":
        fbx(a[1], a[2])
    elif mode == "render":
        assert os.path.isabs(a[1])
        os.makedirs(a[1], exist_ok=True)
        render(a[1], a[2])


main()
