"""b2_rig_solve.py - PRIVATE / DO NOT SHIP. Step C1 stage 3a: bone orientations, A-pose skeleton, heat weights.

  blender -b rig_work/c1_stage1_mesh.blend -P Scripts/Characters/b2_rig_solve.py

* appends the MetaHuman armature object "root" (metahuman_base_skel) from MH_PlayerDefault_FitBody.blend and deletes
  every bone that is not in KEEP (twist / corrective / toe / helper bones)
* per bone: the world delta rotation R_b that takes the MH rest orientation Q_b onto HER posed body
  (swing onto the child joint + twist from a secondary landmark or inherited from the parent; Kabsch for
  pelvis / spine_05-less / hand / foot / head), twist spread over neck_01/02 and half of the wrist twist into the forearm
* A-pose skeleton = MH rest orientations Q_b with HER bone offsets (symmetrised left/right: hands from the right
  hand, feet from the left foot, everything else averaged), posed skeleton p' consistent with it
* heat (bone-segment) weights on the posed skin with a helper armature WGT_Posed whose segments run joint -> child
Writes rig_work/c1_rig_solve.json and rig_work/c1_stage3a_heat.blend.
"""
import bpy, os, sys, json, math, time
from mathutils import Vector, Matrix, Quaternion
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import *  # noqa

STAGE3A = WORK + "/c1_stage3a_heat.blend"
SOLVE = WORK + "/c1_rig_solve.json"
HAND_SRC = "r"   # the right hand is open and clean, the left is a loose fist -> left hand = mirror of right
FOOT_SRC = "l"   # the right foot is crushed by the boot -> right foot = mirror of left
FIN = ("thumb", "index", "middle", "ring", "pinky")
HEAT_MERGE = 0.0003


def mirror(v):
    return Vector((-v.x, v.y, v.z))


def other(n):
    return n[:-2] + ("_r" if n.endswith("_l") else "_l")


def kabsch(pairs):
    import numpy as np
    Hm = np.zeros((3, 3))
    for u, v, w in pairs:
        Hm += w * np.outer(np.array(u), np.array(v))
    U, S, Vt = np.linalg.svd(Hm)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    return Matrix((Vt.T @ np.diag([1, 1, d]) @ U.T).tolist())


def swing(a, b):
    return a.normalized().rotation_difference(b.normalized()).to_matrix()


def signed_angle(a, b, axis):
    return math.atan2(a.cross(b).dot(axis), a.dot(b))


def twist_angle(Rrel, axis):
    q = Rrel.to_quaternion()
    return 2 * math.atan2(Vector(q[1:]).dot(axis), q[0])


def append_mh_root():
    with bpy.data.libraries.load(MH_BLEND, link=False) as (src, dst):
        dst.objects = ["root"]
    root = dst.objects[0]
    assert root.name == "root", root.name
    coll = bpy.data.collections.get("C1_Game")
    coll.objects.link(root)
    return root


def main():
    t0 = time.time()
    data = json.load(open(JOINTS))
    P = {k: Vector(v) for k, v in data["joints"].items()}
    X = data["extra"]
    Xv = {k: Vector(v) for k, v in X.items() if isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) for x in v)}
    root = append_mh_root()
    arm = root.data
    Q = {b.name: b.matrix_local.to_3x3().normalized() for b in arm.bones}
    H = {b.name: b.head_local.copy() for b in arm.bones}
    TAILLEN = {b.name: b.length for b in arm.bones}
    PAR = {b.name: (b.parent.name if b.parent else None) for b in arm.bones}
    mh_tips = {k: Vector(v) for k, v in X["mh_tips"].items()}
    all_bones = [b.name for b in arm.bones]
    removed = [n for n in all_bones if n not in KEEP]
    for n in KEEP:
        assert n in H, n
        p = PAR[n]
        assert p is None or p in KEEP, (n, p)
    order = [n for n in all_bones if n in KEEP]  # armature order = parents first

    def children(n):
        return [c for c in order if PAR[c] == n]

    # ---------------------------------------------------------------- delta rotations
    R = {}
    info = {}
    tip_her = {}
    for s in ("l", "r"):
        for f in FIN:
            tip_her[f"{f}_03_{s}"] = Xv[f"{f}_tip_{s}"]
            tip_mh = mh_tips[f"{f}_tip_{s}"]
            H[f"__tip_{f}_{s}"] = tip_mh
        tip_her[f"ball_{s}"] = Xv[f"toe_tip_{s}"]
        H[f"__tip_ball_{s}"] = Vector(X[f"mh_toe_tip_{s}"])

    def primary(n):
        """(MH target point, HER target point) the bone must point at."""
        if n in tip_her:
            key = f"__tip_{n.split('_')[0]}_{n[-1]}" if n.startswith(FIN) else f"__tip_ball_{n[-1]}"
            return H[key], tip_her[n]
        main = {"spine_05": "neck_01", "neck_02": "head", "clavicle_l": "upperarm_l", "clavicle_r": "upperarm_r"}
        if n in main:
            c = main[n]
        else:
            ch = children(n)
            assert len(ch) == 1, (n, ch)
            c = ch[0]
        return H[c], P[c]

    SECOND = {}  # bone -> list of (MH point, HER point) used for twist
    for s in ("l", "r"):
        SECOND[f"upperarm_{s}"] = [(H[f"hand_{s}"], P[f"hand_{s}"])]
        SECOND[f"thigh_{s}"] = [(H[f"foot_{s}"], P[f"foot_{s}"])]
    SECOND["spine_05"] = [(H["clavicle_l"], P["clavicle_l"]), (H["clavicle_r"], P["clavicle_r"])]

    def kab_spec(n):
        if n == "pelvis":
            mt = (H["thigh_l"] + H["thigh_r"]) / 2; ht = (P["thigh_l"] + P["thigh_r"]) / 2
            return [((H["spine_02"] - mt), (P["spine_02"] - ht), 1.0), ((H["thigh_l"] - H["thigh_r"]), (P["thigh_l"] - P["thigh_r"]), 1.0)]
        if n == "head":
            mem = (Xv["mh_eye_l"] + Xv["mh_eye_r"]) / 2; mam = (Xv["mh_ear_l"] + Xv["mh_ear_r"]) / 2
            em = (Xv["eye_l"] + Xv["eye_r"]) / 2; am = (Xv["ear_l"] + Xv["ear_r"]) / 2
            return [(mem - mam, em - am, 1.0), (Xv["mh_eye_l"] - Xv["mh_eye_r"], Xv["eye_l"] - Xv["eye_r"], 1.0)]
        if n.startswith("hand_"):
            s = n[-1]
            mm = sum((H[f"{f}_01_{s}"] for f in FIN[1:]), Vector()) / 4
            pm = sum((P[f"{f}_01_{s}"] for f in FIN[1:]), Vector()) / 4
            return [(mm - H[n], pm - P[n], 1.0), (H[f"index_01_{s}"] - H[f"pinky_01_{s}"], P[f"index_01_{s}"] - P[f"pinky_01_{s}"], 1.0)]
        if n.startswith("foot_"):
            # forward = ankle -> toe tips; lateral = ankle hinge axis = shin x forward (the toe-branch labels are not
            # reliable enough on the curled / crushed toes)
            s = n[-1]
            fm = H[f"__tip_ball_{s}"] - H[n]; fh = Xv[f"toe_tip_{s}"] - P[n]
            sm = H[n] - H[f"calf_{s}"]; sh = P[n] - P[f"calf_{s}"]
            return [(fm, fh, 1.0), (sm.cross(fm), sh.cross(fh), 1.0)]
        return None

    def solve_R():
        R = {}
        info = {}
        INHERIT_W = 0.05
        for n in order:
            par = PAR[n]
            Rp = R[par] if par else Matrix.Identity(3)
            ks = kab_spec(n)
            if ks:
                pairs = []
                for u, w, wt in ks:
                    # orthogonalise the 2nd pair against the 1st so the main direction is matched exactly-ish
                    pairs.append((u.normalized(), w.normalized(), wt))
                u1, w1 = pairs[0][0], pairs[0][1]
                u2 = (pairs[1][0] - u1 * pairs[1][0].dot(u1)).normalized(); w2 = (pairs[1][1] - w1 * pairs[1][1].dot(w1)).normalized()
                R[n] = kabsch([(u1, w1, 1.0), (u2, w2, 1.0), (u1.cross(u2).normalized(), w1.cross(w2).normalized(), 1.0)])
                info[n] = {"method": "kabsch", "resid_deg": [round(math.degrees(math.acos(max(-1, min(1, (R[n] @ a).dot(b))))), 2) for a, b, _ in pairs]}
                continue
            mt, ht = primary(n)
            u = (mt - H[n]); w = (ht - P[n])
            R0 = swing(Rp @ u, w) @ Rp
            th = 0.0
            if n in SECOND:
                axis = w.normalized()
                sw = 0.0; ss = 0.0; sc = 0.0
                for mh_p, her_p in SECOND[n]:
                    a = R0 @ (mh_p - H[n]); b = (her_p - P[n])
                    ap = a - axis * a.dot(axis); bp = b - axis * b.dot(axis)
                    wt = (ap.length / a.length) * (bp.length / b.length)
                    if wt < 1e-6:
                        continue
                    ang = signed_angle(ap, bp, axis)
                    ss += wt * math.sin(ang); sc += wt * math.cos(ang); sw += wt
                sc += INHERIT_W  # inherit-parent twist (angle 0) as a weak prior
                th = math.atan2(ss, sc)
                R0 = Matrix.Rotation(th, 3, axis) @ R0
            R[n] = R0
            info[n] = {"method": "swing" + ("+twist" if n in SECOND else "+inherit"), "twist_deg": round(math.degrees(th), 2)}

        # twist distribution: head turn over neck_01 / neck_02, half the wrist twist into the forearm
        a = (P["head"] - P["neck_02"]).normalized()
        th = twist_angle(R["head"] @ R["neck_02"].transposed(), a)
        R["neck_02"] = Matrix.Rotation(th * 2 / 3, 3, a) @ R["neck_02"]
        a1 = (P["neck_02"] - P["neck_01"]).normalized()
        R["neck_01"] = Matrix.Rotation(th / 3, 3, a1) @ R["neck_01"]
        info["head"]["neck_twist_spread_deg"] = round(math.degrees(th), 2)
        for s in ("l", "r"):
            a = (P[f"hand_{s}"] - P[f"lowerarm_{s}"]).normalized()
            th = twist_angle(R[f"hand_{s}"] @ R[f"lowerarm_{s}"].transposed(), a)
            R[f"lowerarm_{s}"] = Matrix.Rotation(th / 2, 3, a) @ R[f"lowerarm_{s}"]
            info[f"lowerarm_{s}"]["wrist_twist_deg"] = round(math.degrees(th), 2)
            info[f"lowerarm_{s}"]["half_moved_into_forearm"] = True


        return R, info

    # pass 1, then make the clavicle / thigh heads symmetric about their parent (the torso-slice map is noisy there),
    # keep every other measured joint, pass 2
    R, info = solve_R()
    sym_heads = {}
    for base, par in (("clavicle", "spine_05"), ("thigh", "pelvis")):
        dl = R[par].transposed() @ (P[base + "_l"] - P[par]); dr = R[par].transposed() @ (P[base + "_r"] - P[par])
        avg = (dl + mirror(dr)) / 2
        sym_heads[base] = [round((R[par] @ avg + P[par] - P[base + "_l"]).length * 1000, 1),
                           round((R[par] @ mirror(avg) + P[par] - P[base + "_r"]).length * 1000, 1)]
        P[base + "_l"] = P[par] + R[par] @ avg
        P[base + "_r"] = P[par] + R[par] @ mirror(avg)
    # equal clavicle lengths: slide both shoulder joints along their clavicle to the mean length (her pose raises
    # one shoulder, which otherwise leaves a 2 cm wider left shoulder in the A-pose)
    Lc = ((P["upperarm_l"] - P["clavicle_l"]).length + (P["upperarm_r"] - P["clavicle_r"]).length) / 2
    for s_ in ("l", "r"):
        new = P[f"clavicle_{s_}"] + (P[f"upperarm_{s_}"] - P[f"clavicle_{s_}"]).normalized() * Lc
        sym_heads[f"shoulder_{s_}"] = round((new - P[f"upperarm_{s_}"]).length * 1000, 1)
        P[f"upperarm_{s_}"] = new
    R, info = solve_R()
    info["_symmetrised_heads_moved_mm"] = sym_heads

    # ---------------------------------------------------------------- A-pose offsets (world, A frame), symmetrised
    dA = {}
    for n in order:
        par = PAR[n]
        if par is None:
            continue
        # child offset in the parent's local frame, re-expressed with the MH rest orientation of the parent
        dA[n] = R[par].transposed() @ (P[n] - P[par])
    dA_raw = {k: v.copy() for k, v in dA.items()}
    hand_chain = {n for n in order if n.startswith(FIN)}
    LIMB = ("upperarm", "lowerarm", "hand", "calf", "foot")  # equal limb lengths on both sides
    for n in list(dA):
        if not n.endswith("_l"):
            if not n.endswith("_r"):
                dA[n].x = 0.0  # midline chain (already ~0: MH spine directions)
            continue
        m = other(n)
        if n in hand_chain:          # left hand skeleton = mirror of the right hand's
            dA[n] = mirror(dA[m])
        elif n.startswith("ball_"):  # right foot = mirror of the left foot's
            dA[m] = mirror(dA[n])
        elif n.startswith(LIMB):     # same limb lengths on both sides, directions untouched
            L = (dA[n].length + dA[m].length) / 2
            dA[n] = dA[n].normalized() * L; dA[m] = dA[m].normalized() * L
    hA = {"pelvis": Vector((0.0, P["pelvis"].y, P["pelvis"].z))}
    for n in order:
        if PAR[n]:
            hA[n] = hA[PAR[n]] + dA[n]
    # the posed (bind) joints stay exactly on HER mesh joints (P): each bone maps its own mesh joint onto its A-pose
    # joint, so the symmetric bone lengths are reached by stretching the mesh inside the joint blend zones instead of
    # leaving a bone joint off its mesh joint. Report the length change each bone imposes (mm).
    Pp = {n: P[n].copy() for n in order}
    dev = {n: round(abs(dA[n].length - dA_raw[n].length) * 1000, 1) for n in order if n in dA}
    # posed tips / ends for the helper segments
    ends = {}
    for s in ("l", "r"):
        for f in FIN:
            ends[f"{f}_03_{s}"] = Pp[f"{f}_03_{s}"] + R[f"{f}_03_{s}"] @ (H[f"__tip_{f}_{s}"] - H[f"{f}_03_{s}"]) * (
                (Xv[f"{f}_tip_{s}"] - P[f"{f}_03_{s}"]).length / (H[f"__tip_{f}_{s}"] - H[f"{f}_03_{s}"]).length)
        ends[f"ball_{s}"] = Pp[f"ball_{s}"] + (Xv[f"toe_tip_{s}"] - P[f"ball_{s}"])
    out = {"order": order, "parent": {n: PAR[n] for n in order}, "removed_bones": removed,
           "Q": {n: [list(r) for r in Q[n]] for n in order}, "R": {n: [list(r) for r in R[n]] for n in order},
           "hA": {n: list(hA[n]) for n in order}, "Pp": {n: list(Pp[n]) for n in order},
           "P_measured": {n: list(P[n]) for n in order}, "ends_posed": {k: list(v) for k, v in ends.items()},
           "mh_head": {n: list(H[n]) for n in order}, "mh_taillen": {n: TAILLEN[n] for n in order},
           "info": info, "posed_consistency_dev_mm": dev,
           "dA_raw": {k: list(v) for k, v in dA_raw.items()}}
    save_json(SOLVE, out)
    log("solve done; max bone length change mm", max(dev.values()), sorted(dev.items(), key=lambda kv: -kv[1])[:8])

    # ---------------------------------------------------------------- final armature: delete unused bones, pose the rest
    bpy.context.view_layer.objects.active = root
    for o in bpy.context.view_layer.objects:
        o.select_set(o == root)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for n in removed:
        eb.remove(eb[n])
    bpy.ops.object.mode_set(mode='OBJECT')
    log("bones kept", len(arm.bones))

    # ---------------------------------------------------------------- helper armature for heat weights (posed)
    wd = bpy.data.armatures.new("WGT_Posed")
    wgt = bpy.data.objects.new("WGT_Posed", wd)
    bpy.data.collections["C1_Game"].objects.link(wgt)
    bpy.context.view_layer.objects.active = wgt
    for o in bpy.context.view_layer.objects:
        o.select_set(o == wgt)
    bpy.ops.object.mode_set(mode='EDIT')
    up_head = R["head"] @ Vector((0, 0, 1))

    def seg_end(n):
        if n in ends:
            return ends[n]
        if n == "pelvis":
            return Pp["spine_01"]
        if n == "head":
            return Pp["head"] + up_head * 0.17
        if n.startswith("hand_"):
            s = n[-1]
            return Pp[n].lerp(sum((Pp[f"{f}_metacarpal_{s}"] for f in FIN[1:]), Vector()) / 4, 0.8)
        if n == "spine_05":
            return Pp["neck_01"]
        if n.startswith("clavicle_"):
            return Pp[f"upperarm_{n[-1]}"]
        if n == "neck_02":
            return Pp["head"]
        ch = children(n)
        return Pp[ch[0]]

    segs = {}
    for n in order:
        b = wd.edit_bones.new(n)
        hd = Pp[n].copy(); tl = seg_end(n)
        if n == "pelvis":
            hd = Pp["pelvis"] - (Pp["spine_02"] - Pp["pelvis"]) * 0.9  # reach down into the pelvis bowl
        if (tl - hd).length < 0.004:
            tl = hd + (tl - hd).normalized() * 0.004 if (tl - hd).length > 0 else hd + Vector((0, 0, 0.004))
        b.head = hd; b.tail = tl
        segs[n] = (list(hd), list(tl))
    bpy.ops.object.mode_set(mode='OBJECT')
    save_json(WORK + "/c1_wgt_segments.json", segs)

    skin = bpy.data.objects["SK_2B_Body"]
    # heat proxy: the L1 shell has 778 sub-0.1 mm nail-rim edges that make the heat solve singular, so the weights
    # are solved on a copy with those collapsed (merge 0.3 mm) and copied back vertex by vertex (nearest proxy vertex)
    import bmesh
    from mathutils.kdtree import KDTree
    pm = skin.data.copy(); pm.name = "TMP_HeatProxy"
    bm = bmesh.new(); bm.from_mesh(pm)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=HEAT_MERGE)
    bmesh.ops.dissolve_degenerate(bm, dist=HEAT_MERGE, edges=bm.edges)
    bm.to_mesh(pm); bm.free()
    proxy = bpy.data.objects.new("TMP_HeatProxy", pm)
    bpy.data.collections["C1_Game"].objects.link(proxy)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (proxy, wgt))
    bpy.context.view_layer.objects.active = wgt
    th = time.time()
    r = bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    log("heat weights on proxy", len(pm.vertices), "verts", r, round(time.time() - th, 1), "s; groups", len(proxy.vertex_groups))
    kd = KDTree(len(pm.vertices))
    for v in pm.vertices:
        kd.insert(v.co, v.index)
    kd.balance()
    gname = {g.index: g.name for g in proxy.vertex_groups}
    pw = [[(gname[g.group], g.weight) for g in v.groups] for v in pm.vertices]
    for n in order:
        skin.vertex_groups.new(name=n)
    per_group = {n: ([], []) for n in order}
    for v in skin.data.vertices:
        co, idx, d = kd.find(v.co)
        for gn, w in pw[idx]:
            if w > 0:
                per_group[gn][0].append(v.index); per_group[gn][1].append(w)
    for gn, (ids, ws) in per_group.items():
        g = skin.vertex_groups[gn]
        for i, w in zip(ids, ws):
            g.add([i], w, 'REPLACE')
    bpy.data.objects.remove(proxy, do_unlink=True); bpy.data.meshes.remove(pm)
    # coverage report
    import numpy as np
    nv = len(skin.data.vertices)
    tot = np.zeros(nv)
    for v in skin.data.vertices:
        tot[v.index] = sum(g.weight for g in v.groups)
    unweighted = int((tot < 1e-4).sum())
    log("unweighted verts after heat", unweighted, "of", nv)
    save_json(WORK + "/c1_heat_info.json", {"unweighted": unweighted, "groups": len(skin.vertex_groups),
                                            "secs": round(time.time() - th, 1)})
    bpy.ops.wm.save_as_mainfile(filepath=STAGE3A, compress=True)
    log("saved", STAGE3A, round(time.time() - t0, 1), "s")


main()
