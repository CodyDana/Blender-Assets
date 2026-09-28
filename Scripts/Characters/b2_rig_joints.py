"""b2_rig_joints.py - PRIVATE / DO NOT SHIP. Step C1 stage 2: fit metahuman_base_skel joint centres to HER posed body.

  blender -b rig_work/c1_stage1_mesh.blend -P Scripts/Characters/b2_rig_joints.py

Method (everything measured on the posed L1 skin shell SK_2B_Body, step A space, facing -Y, left = +X):
  * axial joints (pelvis, spine_01-05, neck_01/02, head, clavicles, hips): the MetaHuman fitting body (A-pose) is
    sliced horizontally at each MH joint height; the joint is stored relative to that torso slice (x / half width,
    y between front and back) and mapped onto her slice at the corresponding height (heights mapped linearly
    between crotch and top of head).
  * limbs: geodesic distance from the Arms/Body and Legs/Body surface seams, level-set rings every few mm, ring
    centroids = medial axis.  Wrist / ankle = narrowest ring + an offset calibrated on the MH body the same way;
    elbow / knee = best two-line fit (bend) between shoulder and wrist / hip and ankle, else the MH length ratio;
    shoulder = upper-arm axis at the mapped MH shoulder height.
  * hands: the finger branches of the ring tree; DIP / PIP / MCP placed from each fingertip along its medial curve
    with the MH phalanx lengths scaled to her hand; metacarpal heads and thumb CMC from the MH hand frame.
  * feet: toe split ring -> ball (MTP) just behind it, foot lateral axis from big / little toe branches.
Writes rig_work/c1_joints_posed.json (and MH reference data) - no blend is saved.
"""
import bpy, os, sys, json, math
from collections import defaultdict
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from b2_rig_common import *  # noqa
from b2_rig_geo import *  # noqa

B = SHELL.index
FNAMES = ["thumb", "index", "middle", "ring", "pinky"]


def V(x):
    return Vector(x)


# ------------------------------------------------------------------------------------------------ MH reference
def load_mh():
    names = ("root", "FIT_MH_PlayerDefault_Body", "FIT_MH_PlayerDefault_Head", "FIT_MH_PlayerDefault_HeadParts")
    with bpy.data.libraries.load(MH_BLEND, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n in names]
    objs = {o.name: o for o in dst.objects}
    arm = objs["root"]
    bones = {b.name: {"head": b.head_local.copy(), "tail": b.tail_local.copy(), "mat": b.matrix_local.copy(),
                      "parent": b.parent.name if b.parent else None} for b in arm.data.bones}
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(objs["FIT_MH_PlayerDefault_Body"].data)
    bm.from_mesh(objs["FIT_MH_PlayerDefault_Head"].data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
    both = bpy.data.meshes.new("TMP_MH_BodyHead"); bm.to_mesh(both); bm.free()
    body = Mesh(both, None, weld=True)
    head = Mesh(objs["FIT_MH_PlayerDefault_Head"].data, None, weld=True)
    return bones, body, head, objs


def slice_frame(mesh, z, near, max_off=0.15):
    loops = slice_loops(mesh, (0, 0, 0), (0, 0, 1), [z])[z]
    l = pick_loop(loops, (near[0], near[1], z), max_off) or pick_loop(loops, (near[0], near[1], z), max_off, False)
    if l is None:
        return None
    xs = [p.x for p in l["pts"]]
    cx = (min(xs) + max(xs)) / 2; hw = (max(xs) - min(xs)) / 2
    mid = [p for p in l["pts"] if abs(p.x - cx) < 0.25 * hw]
    return {"cx": cx, "hw": hw, "front": min(p.y for p in mid), "back": max(p.y for p in mid), "c": l["c"], "len": l["len"]}


def crotch_z(mesh, xtol, zmin, vset=None):
    best = None
    for i, c in enumerate(mesh.co):
        if vset is not None and i not in vset:
            continue
        if abs(c.x) < xtol and c.z > zmin and (best is None or c.z < best.z):
            best = c
    return best


def narrowest_offset(mesh, a, b, lo=0.5, hi=1.0, step=0.003):
    """Perpendicular slices along a->b; return (s_min / L, r_min, L) of the narrowest loop around the axis."""
    ax = (b - a); L = ax.length; ax.normalize()
    ts = [L * lo + i * step for i in range(int((hi - lo) * L / step) + 1)]
    sl = slice_loops(mesh, a, ax, ts)
    best = None
    for t in ts:
        l = pick_loop(sl[t], a + ax * t, 0.06)
        if l is None:
            continue
        r = l["len"] / (2 * math.pi)
        if best is None or r < best[1]:
            best = (t, r)
    return best[0] / L, best[1], L


def mh_tips(mesh, bones):
    """MH fingertip / thumb tip = farthest body vertex along the 02->03 direction near the 03 joint."""
    tips = {}
    for s in ("l", "r"):
        for f in FNAMES:
            h3 = bones[f"{f}_03_{s}"]["head"]; h2 = bones[f"{f}_02_{s}"]["head"]
            d = (h3 - h2).normalized()
            best = None
            for c in mesh.co:
                q = c - h3
                if q.length < 0.035 and q.dot(d) > 0 and (q - d * q.dot(d)).length < 0.009:
                    if best is None or q.dot(d) > best[0]:
                        best = (q.dot(d), c)
            tips[f"{f}_tip_{s}"] = best[1].copy()
    return tips


# ------------------------------------------------------------------------------------------------ her limbs
def branch_tip(M, comp, dist, last):
    """Tip of one branch: flood fill beyond the branch's last ring (verts with dist >= t), from the vertex nearest to
    the ring centre, and take the farthest vertex. Touching neighbour fingers are not reached (they only connect
    through the webs, which are closer than t)."""
    t = last["t"]
    beyond = [v for v in comp if dist.get(v, -1) >= t]
    if not beyond:
        return None
    seed = min(beyond, key=lambda v: (M.co[v] - last["c"]).length)
    bset = set(beyond); seen = {seed}; st = [seed]
    while st:
        v = st.pop()
        for w, _ in M.adj[v]:
            if w in bset and w not in seen:
                seen.add(w); st.append(w)
    return max(seen, key=lambda v: dist[v])


def limb_components(M, mats):
    vset = set(v for i, s in enumerate(M.fsrc) if s in mats for v in M.faces[i])
    seen = set(); out = []
    for s0 in vset:
        if s0 in seen:
            continue
        c = []; st = [s0]; seen.add(s0)
        while st:
            v = st.pop(); c.append(v)
            for w, _ in M.adj[v]:
                if w in vset and w not in seen:
                    seen.add(w); st.append(w)
        out.append(set(c))
    return out


def limb_tree(M, vset, step):
    seam = [v for v in vset if B("Body") in M.vsrc[v]]
    dist = dijkstra(M, seam, vset)
    faces = [i for i, f in enumerate(M.faces) if all(v in vset for v in f)]
    # iso skeleton restricted to limb faces
    maxd = max(dist.values())
    nodes = []; prev = []
    t = step * 0.5
    while t < maxd:
        cur = []
        for comp in iso_contours(M, dist, t, faces):
            if comp["len"] < 0.004:
                continue
            comp["id"] = len(nodes); comp["children"] = []; comp["parent"] = None; comp["r"] = comp["len"] / (2 * math.pi)
            if prev:
                p = min(prev, key=lambda q: (nodes[q]["c"] - comp["c"]).length)
                comp["parent"] = p; nodes[p]["children"].append(comp["id"])
            nodes.append(comp); cur.append(comp["id"])
        prev = cur if cur else prev
        t += step
    roots = [n for n in nodes if n["parent"] is None]
    root = max(roots, key=lambda n: n["len"])
    return nodes, root["id"], dist


def subtree_sizes(nodes):
    size = {}
    for n in reversed(nodes):
        size[n["id"]] = 1 + sum(size[c] for c in n["children"])
    return size


def trunk(nodes, root, size, min_branch=4):
    """Heaviest path + index of the first significant split."""
    path = [root]
    first_split = None
    while nodes[path[-1]]["children"]:
        ch = nodes[path[-1]]["children"]
        sig = [c for c in ch if size[c] >= min_branch]
        if first_split is None and len(sig) >= 2:
            first_split = len(path) - 1
        path.append(max(ch, key=lambda c: size[c]))
    return path, first_split


def arcs(pts):
    a = [0.0]
    for i in range(1, len(pts)):
        a.append(a[-1] + (pts[i] - pts[i - 1]).length)
    return a


def at_arc(pts, ac, s):
    for i in range(len(pts) - 1):
        if ac[i + 1] >= s:
            w = (s - ac[i]) / max(ac[i + 1] - ac[i], 1e-9)
            return pts[i].lerp(pts[i + 1], w)
    return pts[-1].copy()


def project_arc(pts, ac, p):
    best = None
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
        d = (a + ab * t - p).length
        if best is None or d < best[0]:
            best = (d, ac[i] + t * (ac[i + 1] - ac[i]))
    return best[1]


def bend_joint(pts, ac, a0, a1, lo, hi, ratio, min_deg=10.0):
    """Two-line fit between arcs a0..a1; breakpoint searched in [lo, hi] fraction. Returns (arc, bend_deg, used)."""
    L = a1 - a0
    best = None
    for k in range(int((hi - lo) * 100) + 1):
        f = lo + k / 100.0
        s = a0 + f * L
        A = [p for p, x in zip(pts, ac) if a0 + 0.08 * L < x < s - 0.03]
        Bp = [p for p, x in zip(pts, ac) if s + 0.03 < x < a1 - 0.05 * L]
        if len(A) < 3 or len(Bp) < 3:
            continue
        ca, da = fit_line(A); cb, db = fit_line(Bp)
        res = sum(((p - ca) - da * (p - ca).dot(da)).length ** 2 for p in A) + \
            sum(((p - cb) - db * (p - cb).dot(db)).length ** 2 for p in Bp)
        if best is None or res < best[0]:
            ang = math.degrees(math.acos(min(1.0, abs(da.dot(db)))))
            best = (res, s, ang)
    if best is None or best[2] < min_deg:
        return a0 + ratio * L, (best[2] if best else 0.0), "ratio"
    return best[1], best[2], "bend"


# ------------------------------------------------------------------------------------------------ main
def main():
    t0 = time.time() if 'time' in globals() else None
    skin = bpy.data.objects["SK_2B_Body"]
    M = Mesh(skin.data)
    bones, mh_body, mh_head, mh_objs = load_mh()
    H = {n: b["head"] for n, b in bones.items()}
    out = {"joints": {}, "extra": {}, "diag": {}}
    J = out["joints"]; X = out["extra"]; D = out["diag"]

    # ---------------- vertical landmarks
    mh_cr = crotch_z(mh_body, 0.01, 0.4)
    her_body_v = {v for v in range(M.n) if M.vsrc[v] == {B("Body")}}
    her_cr = crotch_z(M, 0.035, 0.5, her_body_v)
    mh_top = max(c.z for c in mh_head.co)
    her_top = max(c.z for c in M.co)
    k_up = (her_top - her_cr.z) / (mh_top - mh_cr.z)
    D["crotch"] = {"mh": list(mh_cr), "her": list(her_cr)}; D["top"] = {"mh": mh_top, "her": her_top, "k_up": k_up}

    def zmap(z):
        return her_cr.z + (z - mh_cr.z) * k_up

    # torso centre (x, y) near the waist, used to pick her torso loop
    her_waist = slice_frame(M, zmap(1.10), (0.0, 0.0), 0.2)
    near_her = (her_waist["cx"], (her_waist["front"] + her_waist["back"]) / 2)
    D["near_her"] = near_her

    def map_axial(name):
        h = H[name]
        mesh_mh = mh_body  # body + head welded
        fm = slice_frame(mesh_mh, h.z, (0.0, h.y), 0.2)
        zh = zmap(h.z)
        mesh_h = M
        # her torso loop near the torso centre; for the neck / head, follow the previous slice centre
        fh = slice_frame(mesh_h, zh, map_axial.near, 0.2)
        x = fh["cx"] + (h.x - fm["cx"]) / fm["hw"] * fh["hw"]
        fy = (h.y - fm["front"]) / (fm["back"] - fm["front"])
        y = fh["front"] + fy * (fh["back"] - fh["front"])
        map_axial.near = (fh["cx"], (fh["front"] + fh["back"]) / 2)
        D.setdefault("axial", {})[name] = {"mh_slice": {k: fm[k] for k in ("cx", "hw", "front", "back")},
                                           "her_slice": {k: fh[k] for k in ("cx", "hw", "front", "back")},
                                           "fx": (h.x - fm["cx"]) / fm["hw"], "fy": fy}
        return Vector((x, y, zh))
    map_axial.near = near_her

    for n in ["pelvis", "thigh_l", "thigh_r", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05",
              "clavicle_l", "clavicle_r", "neck_01", "neck_02", "head"]:
        if n.startswith("thigh") or n.startswith("clavicle"):
            keep = map_axial.near
            J[n] = map_axial(n)
            map_axial.near = keep
        else:
            J[n] = map_axial(n)

    # ---------------- MH calibrations
    cal = {}
    for s in ("l", "r"):
        f, r, L = narrowest_offset(mh_body, H[f"lowerarm_{s}"], H[f"hand_{s}"], 0.45, 1.0)
        cal[f"wrist_{s}"] = {"frac": f, "r": r, "L": L}
        f, r, L = narrowest_offset(mh_body, H[f"calf_{s}"], H[f"foot_{s}"], 0.5, 1.0)
        cal[f"ankle_{s}"] = {"frac": f, "r": r, "L": L}
    D["mh_cal"] = cal
    tips = mh_tips(mh_body, bones)
    X["mh_tips"] = {k: list(v) for k, v in tips.items()}

    def mh_len(a, b):
        return (H[b] - H[a]).length

    # ---------------- arms
    arm_comps = limb_components(M, {B("Arms"), B("Fingernails")})
    leg_comps = limb_components(M, {B("Legs"), B("Toenails")})
    hands = {}
    for comp in arm_comps:
        s = "l" if sum(M.co[v].x for v in comp) > 0 else "r"
        nodes, root, dist = limb_tree(M, comp, 0.004)
        size = subtree_sizes(nodes)
        path, split = trunk(nodes, root, size)
        pts = smooth_poly([nodes[i]["c"] for i in path], 3)
        ac = arcs(pts)
        radii = [nodes[i]["r"] for i in path]
        a_split = ac[split]
        # wrist: narrowest ring in [0.55, 1.0] of the seam -> first split arc
        cand = [(radii[i], i) for i in range(len(path)) if 0.55 * a_split < ac[i] <= a_split]
        rmin, imin = min(cand)
        # shoulder: upper-arm axis at the mapped MH shoulder height
        up = [pts[i] for i in range(len(path)) if 0.18 * a_split < ac[i] < 0.42 * a_split]
        c_up, d_up = fit_line(up)
        zs = zmap(H[f"upperarm_{s}"].z)
        if abs(d_up.z) > 0.2:
            sh = c_up + d_up * ((zs - c_up.z) / d_up.z)
        else:
            sh = c_up
        sh_slice = map_axial_point = None
        a_sh = project_arc(pts, ac, sh)
        # wrist offset calibrated on MH (hand joint is distal of the narrowest forearm section)
        mh_fore = mh_len(f"lowerarm_{s}", f"hand_{s}"); mh_up = mh_len(f"upperarm_{s}", f"lowerarm_{s}")
        scale_arm = (ac[imin] - a_sh) / (mh_up + cal[f"wrist_{s}"]["frac"] * mh_fore)
        a_w = ac[imin] + (1 - cal[f"wrist_{s}"]["frac"]) * mh_fore * scale_arm
        wrist = at_arc(pts, ac, a_w)
        ratio_e = mh_up / (mh_up + mh_fore)
        a_e, bend, used = bend_joint(pts, ac, a_sh, a_w, 0.40, 0.64, ratio_e, 12.0)
        L_ = a_w - a_sh
        if used == "bend" and not (0.43 * L_ < a_e - a_sh < 0.61 * L_):
            a_e, used = a_sh + ratio_e * L_, "ratio (bend at search edge)"
        elbow = at_arc(pts, ac, a_e)
        J[f"upperarm_{s}"] = sh; J[f"lowerarm_{s}"] = elbow; J[f"hand_{s}"] = wrist
        D[f"arm_{s}"] = {"trunk_nodes": len(path), "a_split": a_split, "a_shoulder": a_sh, "a_narrow": ac[imin],
                         "r_narrow": rmin, "a_wrist": a_w, "a_elbow": a_e, "elbow_bend_deg": bend, "elbow_method": used,
                         "scale_arm": scale_arm, "up_axis": list(d_up)}
        # ---------- fingers
        leaves = [n["id"] for n in nodes if not n["children"]]
        fingers = []
        for lf in leaves:
            chain = [lf]
            while nodes[chain[-1]]["parent"] is not None:
                p = nodes[chain[-1]]["parent"]
                sig = [c for c in nodes[p]["children"] if size[c] >= 4]
                if len(sig) >= 2:
                    break
                chain.append(p)
            own = list(reversed(chain))  # proximal -> tip
            fpts = [nodes[i]["c"] for i in own]
            if len(own) < 5 or polyline_len(fpts) < 0.015:
                continue
            # tip: the farthest skin vertex of this finger beyond the last ring
            tipring = nodes[own[-1]]
            fingers.append({"own": own, "pts": fpts, "r": sum(nodes[i]["r"] for i in own[:6]) / min(6, len(own)),
                            "t0": nodes[own[0]]["t"], "tip_t": tipring["t"]})
        # fingertip = max-distance vertex (seam geodesic) inside the finger
        for f in fingers:
            last = nodes[f["own"][-1]]
            tipv = branch_tip(M, comp, dist, last)
            f["tip"] = M.co[tipv].copy() if tipv is not None else last["c"].copy()
        D[f"fingers_found_{s}"] = [{"n": len(f["own"]), "r": f["r"], "t0": f["t0"], "len": polyline_len(f["pts"])} for f in fingers]
        if len(fingers) != 5:
            log("WARNING", s, "fingers found", len(fingers))
        # thumb = thickest finger; others ordered by distance of their base from the thumb base
        # the thumb splits from the palm first (thenar web); ties -> the thicker branch
        t_first = min(f["t0"] for f in fingers)
        thumb = max([f for f in fingers if f["t0"] <= t_first + 0.0041], key=lambda f: f["r"])
        rest = sorted([f for f in fingers if f is not thumb], key=lambda f: (f["pts"][0] - thumb["pts"][0]).length)
        named = dict(zip(FNAMES, [thumb] + rest))
        # hand scale: her wrist -> middle tip (medial curve) vs MH hand -> middle joints -> tip
        mid = named["middle"]
        wrist_node = min(path, key=lambda i: (nodes[i]["c"] - wrist).length)
        chain = []
        i = mid["own"][0]
        while i is not None and i != wrist_node and nodes[i]["t"] > nodes[wrist_node]["t"]:
            chain.append(i); i = nodes[i]["parent"]
        palm_pts = [wrist] + [nodes[k]["c"] for k in reversed(chain)] + mid["pts"][1:] + [mid["tip"]]
        her_hand_len = polyline_len(palm_pts)
        mh_hand_len = (mh_len(f"hand_{s}", f"middle_metacarpal_{s}") + mh_len(f"middle_metacarpal_{s}", f"middle_01_{s}") +
                       mh_len(f"middle_01_{s}", f"middle_02_{s}") + mh_len(f"middle_02_{s}", f"middle_03_{s}") +
                       (tips[f"middle_tip_{s}"] - H[f"middle_03_{s}"]).length)
        s_hand = her_hand_len / mh_hand_len
        D[f"hand_{s}"] = {"her_len": her_hand_len, "mh_len": mh_hand_len, "scale": s_hand}
        # palm vertices: geodesic band between the wrist ring and the first finger split
        t_w = nodes[wrist_node]["t"]
        palm_v = [v for v in comp if t_w + 0.004 < dist.get(v, -1) < t_first - 0.002]
        hands[s] = (named, wrist, s_hand, palm_v, thumb)
    # one hand scale for both hands (curled fingers under-measure): the larger of the two
    s_hand_all = max(h[2] for h in hands.values())
    D["hand_scale_used"] = s_hand_all
    import numpy as np
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons(M.co, M.faces)
    for s, (named, wrist, _, palm_v, thumb) in hands.items():
        s_hand = s_hand_all
        # posed palm frame: w1 = wrist -> palm centre, normal = thinnest PCA axis of the palm, w2 towards the thumb side
        P = np.array([list(M.co[v]) for v in palm_v]); pc = Vector(P.mean(axis=0).tolist())
        _, _, vt = np.linalg.svd(P - P.mean(axis=0))
        nrm = Vector(vt[2].tolist()).normalized()
        bases = {fn: named[fn]["pts"][0] for fn in ("index", "middle", "ring", "pinky")}
        bc = sum(bases.values(), Vector()) / 4
        w1 = (bc - wrist); w1 = (w1 - nrm * w1.dot(nrm)).normalized()
        w2 = bases["index"] - bases["pinky"]; w2 = (w2 - nrm * w2.dot(nrm) - w1 * w2.dot(w1)).normalized()
        mcps_mh = sum((H[f"{f}_01_{s}"] for f in ("index", "middle", "ring", "pinky")), Vector()) / 4
        u1 = (mcps_mh - H[f"hand_{s}"]).normalized()
        u2 = (H[f"index_01_{s}"] - H[f"pinky_01_{s}"]); u2 = (u2 - u1 * u2.dot(u1)).normalized()
        R = kabsch([(u1, w1, 1.0), (u2, w2, 1.0), (u1.cross(u2).normalized(), w1.cross(w2).normalized(), 1.0)])
        X[f"hand_frame_{s}"] = [list(r) for r in R]
        X[f"palm_centre_{s}"] = list(pc)
        D[f"palm_{s}"] = {"n": len(palm_v), "pc": list(pc), "nrm": list(nrm), "w1": list(w1), "w2": list(w2),
                          "wrist": list(wrist)}

        def tmpl(name):
            return wrist + R @ ((H[name] - H[f"hand_{s}"]) * s_hand)
        for fn in ("index", "middle", "ring", "pinky"):
            J[f"{fn}_metacarpal_{s}"] = tmpl(f"{fn}_metacarpal_{s}")
            q = tmpl(f"{fn}_01_{s}")
            # keep the knuckle in line with its own finger across the hand (w2)
            q += w2 * (bases[fn] - q).dot(w2)
            J[f"{fn}_01_{s}"] = q
        J[f"thumb_01_{s}"] = tmpl(f"thumb_01_{s}")
        # centre the template knuckles in the hand thickness: shoot from the dorsal side along the palm normal
        dorsal = (w2.cross(w1) if s == "l" else w1.cross(w2)).normalized()
        moved = {}
        for n in [f"{fn}_{k}_{s}" for fn in ("index", "middle", "ring", "pinky") for k in ("metacarpal", "01")] + [f"thumb_01_{s}"]:
            q = centre_in_thickness(bvh, J[n], dorsal)
            if q is not None:
                moved[n] = round((q - J[n]).length * 1000, 1)
                J[n] = q
        D[f"knuckle_centering_mm_{s}"] = moved
        for fn, f in named.items():
            p = f["pts"] + [f["tip"]]
            rp = list(reversed(p)); ra = arcs(rp)  # tip -> finger base ring
            # MH phalanx proportions (distal incl. tip, middle, proximal) spread along HER tip -> knuckle path
            segs = [(tips[f"{fn}_tip_{s}"] - H[f"{fn}_03_{s}"]).length, mh_len(f"{fn}_02_{s}", f"{fn}_03_{s}"),
                    mh_len(f"{fn}_01_{s}", f"{fn}_02_{s}")]
            anchor = J[f"{fn}_01_{s}"]  # template MCP (thumb: template CMC)
            ext = rp + [anchor]; ea = arcs(ext)
            tot = sum(segs)
            pos = [at_arc(ext, ea, ea[-1] * segs[0] / tot), at_arc(ext, ea, ea[-1] * (segs[0] + segs[1]) / tot)]
            J[f"{fn}_03_{s}"] = pos[0]; J[f"{fn}_02_{s}"] = pos[1]
            X[f"{fn}_tip_{s}"] = list(f["tip"])
            D.setdefault(f"finger_{s}", {})[fn] = {"visible_len": ra[-1], "mh_segs": segs, "path_len": ea[-1],
                                                    "base_r": f["r"]}

    # ---------------- legs
    leg_curves = {}
    for comp in leg_comps:
        s = "l" if sum(M.co[v].x for v in comp) > 0 else "r"
        nodes, root, dist = limb_tree(M, comp, 0.008)
        size = subtree_sizes(nodes)
        path, split = trunk(nodes, root, size, 3)
        pts = smooth_poly([nodes[i]["c"] for i in path], 3)
        ac = arcs(pts)
        radii = [nodes[i]["r"] for i in path]
        a_split = ac[split] if split is not None else ac[-1]
        hip = J[f"thigh_{s}"]
        # prepend the hip so arcs start there
        a_hip = project_arc(pts, ac, hip)
        cand = [(radii[i], i) for i in range(len(path)) if 0.55 * a_split < ac[i] <= 0.85 * a_split]
        rmin, imin = min(cand)
        mh_th = mh_len(f"thigh_{s}", f"calf_{s}"); mh_sh = mh_len(f"calf_{s}", f"foot_{s}")
        # her hip is off the ring path (above the seam): use the straight hip distance for the first part
        seg0 = (hip - pts[0]).length
        scale_leg = (seg0 + ac[imin]) / (mh_th + cal[f"ankle_{s}"]["frac"] * mh_sh)
        a_ank = ac[imin] + (1 - cal[f"ankle_{s}"]["frac"]) * mh_sh * scale_leg
        ankle = at_arc(pts, ac, a_ank)
        ratio_k = mh_th / (mh_th + mh_sh)
        lpts = [hip] + pts; lac = [0.0] + [seg0 + a for a in ac]
        a_k, bend, used = bend_joint(lpts, lac, 0.0, seg0 + a_ank, 0.42, 0.62, ratio_k)
        knee = at_arc(lpts, lac, a_k)
        J[f"calf_{s}"] = knee; J[f"foot_{s}"] = ankle
        leg_curves[s] = (lpts, lac)
        # ball: 1.4 cm (scaled) behind the toe split, at the ring centroid
        a_ball = a_split - 0.014 * scale_leg
        ball = at_arc(pts, ac, a_ball)
        J[f"ball_{s}"] = ball
        # toes: leaves after the split
        toes = []
        for lf in [n["id"] for n in nodes if not n["children"]]:
            chain = [lf]
            while nodes[chain[-1]]["parent"] is not None:
                p = nodes[chain[-1]]["parent"]
                if len([c for c in nodes[p]["children"] if size[c] >= 2]) >= 2:
                    break
                chain.append(p)
            own = list(reversed(chain))
            if nodes[own[0]]["t"] < nodes[path[split]]["t"] - 1e-6 if split is not None else True:
                continue
            last = nodes[own[-1]]
            tipv = branch_tip(M, comp, dist, last)
            toes.append({"base": nodes[own[0]]["c"], "r": max(nodes[i]["r"] for i in own), "n": len(own),
                         "tip": M.co[tipv].copy() if tipv is not None else last["c"].copy()})
        toes = [t for t in toes if t["n"] >= 1]
        big = max(toes, key=lambda t: t["r"]) if toes else None
        little = max(toes, key=lambda t: (t["base"] - big["base"]).length) if toes else None
        tip_c = sum((t["tip"] for t in toes), Vector()) / len(toes) if toes else pts[-1]
        X[f"toe_tip_{s}"] = list(tip_c)
        # heel: the foot vertex farthest from the ball (foot = beyond the ankle ring)
        ank_node = min(path, key=lambda i: (nodes[i]["c"] - ankle).length)
        foot_v = [v for v in comp if dist.get(v, -1) >= nodes[ank_node]["t"] - 0.01]
        heel = max(foot_v, key=lambda v: (M.co[v] - ball).length)
        X[f"heel_{s}"] = list(M.co[heel])
        mh_foot = [c for c in mh_body.co if c.z < 0.12 and abs(c.x - H[f"foot_{s}"].x) < 0.12]
        X[f"mh_heel_{s}"] = list(max(mh_foot, key=lambda c: (c - H[f"ball_{s}"]).length))
        X[f"mh_sole_min_z_{s}"] = min(c.z for c in mh_foot)
        X[f"bigtoe_{s}"] = list(big["base"]) if big else None
        X[f"littletoe_{s}"] = list(little["base"]) if little else None
        D[f"leg_{s}"] = {"trunk_nodes": len(path), "a_split": a_split, "a_hip": a_hip, "seg0": seg0, "a_narrow": ac[imin],
                         "r_narrow": rmin, "a_ankle": a_ank, "knee_arc_from_hip": a_k, "knee_bend_deg": bend,
                         "knee_method": used, "scale_leg": scale_leg, "toes": len(toes)}
    # ---------------- right leg re-placed with the LEFT leg's segment lengths along its own medial curve
    # (the right knee is bent 45 deg and its crushed foot makes the ankle unreliable; the left leg is clean)
    def point_at_dist(pts, start_idx_pt, origin, L):
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            if (a - origin).length <= L <= (b - origin).length or (b - origin).length >= L > (a - origin).length:
                lo, hi = 0.0, 1.0
                for _ in range(40):
                    m = (lo + hi) / 2
                    if (a.lerp(b, m) - origin).length < L:
                        lo = m
                    else:
                        hi = m
                return a.lerp(b, lo), i
        return pts[-1].copy(), len(pts) - 2
    Lth = (J["calf_l"] - J["thigh_l"]).length; Lsh = (J["foot_l"] - J["calf_l"]).length
    rp, _ = leg_curves["r"]
    old_r = (J["calf_r"].copy(), J["foot_r"].copy())
    knee, ki = point_at_dist(rp, 0, J["thigh_r"], Lth)
    rest_pts = [knee] + rp[ki + 1:]
    ankle, _ = point_at_dist(rest_pts, 0, knee, Lsh)
    J["calf_r"] = knee; J["foot_r"] = ankle
    D["right_leg_from_left_lengths"] = {"thigh_mm": round(Lth * 1000, 1), "shin_mm": round(Lsh * 1000, 1),
                                        "knee_moved_mm": round((knee - old_r[0]).length * 1000, 1),
                                        "ankle_moved_mm": round((ankle - old_r[1]).length * 1000, 1)}

    # ---------------- eyes (head frame)
    hp = bpy.data.objects["SK_2B_HeadParts"].data
    ir_i = [i for i, m in enumerate(hp.materials) if m.name == "M_2B_Irises"][0]
    vs = {s: [] for s in ("l", "r")}
    for p in hp.polygons:
        if p.material_index == ir_i:
            c = p.center
            vs["l" if c.x > -0.0115 else "r"].append(c.copy())
    for s in ("l", "r"):
        X[f"iris_{s}"] = list(sum(vs[s], Vector()) / len(vs[s]))
    # eyeball centres (sclera centroids) and ear centres: the head frame and the head joint come from these
    sc_i = [i for i, m in enumerate(hp.materials) if m.name == "M_2B_Sclera"][0]
    vs = {s: [] for s in ("l", "r")}
    for p in hp.polygons:
        if p.material_index == sc_i:
            c = p.center
            vs["l" if c.x > -0.0115 else "r"].append(c.copy())
    for s in ("l", "r"):
        X[f"eye_{s}"] = list(sum(vs[s], Vector()) / len(vs[s]))
    ear_v = [v for v in range(M.n) if M.vsrc[v] == {B("Ears")}]
    for s in ("l", "r"):
        pts_e = [M.co[v] for v in ear_v if (M.co[v].x > -0.0115) == (s == "l")]
        X[f"ear_{s}"] = list(sum(pts_e, Vector()) / len(pts_e))
    # MH: eyeballs from the HeadParts eye clusters, ears = lateral-most head cluster at ear height
    hpm = mh_objs["FIT_MH_PlayerDefault_HeadParts"].data
    for s, sg in (("l", 1), ("r", -1)):
        cs = [p.center.copy() for p in hpm.polygons if 0.02 < sg * p.center.x < 0.05 and 1.72 < p.center.z < 1.77 and p.center.y < -0.06]
        X[f"mh_eye_{s}"] = list(sum(cs, Vector()) / len(cs))
        hv = [c for c in mh_head.co if sg * c.x > 0.05 and 1.68 < c.z < 1.80 and -0.04 < c.y < 0.06]
        xm = max(sg * c.x for c in hv)
        cl = [c for c in hv if sg * c.x > xm - 0.012]
        X[f"mh_ear_{s}"] = list(sum(cl, Vector()) / len(cl))
    # head joint from the ears/eyes (the torso-scaled slice map puts it too high on her bigger head)
    em = (Vector(X["eye_l"]) + Vector(X["eye_r"])) / 2; am = (Vector(X["ear_l"]) + Vector(X["ear_r"])) / 2
    mem = (Vector(X["mh_eye_l"]) + Vector(X["mh_eye_r"])) / 2; mam = (Vector(X["mh_ear_l"]) + Vector(X["mh_ear_r"])) / 2
    fw_h = (em - am); fw_m = (mem - mam)
    lat_h = (Vector(X["eye_l"]) - Vector(X["eye_r"])); lat_m = (Vector(X["mh_eye_l"]) - Vector(X["mh_eye_r"]))
    Rh = kabsch([(lat_m.normalized(), lat_h.normalized(), 1.0), (fw_m.normalized(), fw_h.normalized(), 1.0),
                 (lat_m.cross(fw_m).normalized(), lat_h.cross(fw_h).normalized(), 1.0)])
    s_head = fw_h.length / fw_m.length
    old_head = J["head"].copy()
    J["head"] = am + Rh @ ((H["head"] - mam) * s_head)
    t2 = (H["neck_02"] - H["neck_01"]).length / ((H["neck_02"] - H["neck_01"]).length + (H["head"] - H["neck_02"]).length)
    J["neck_02"] = J["neck_01"].lerp(J["head"], t2)
    D["head_fix"] = {"s_head": s_head, "old_head": list(old_head), "new_head": list(J["head"]),
                     "ear_mid": list(am), "eye_mid": list(em), "mh_ear_mid": list(mam), "mh_eye_mid": list(mem)}
    # MH extras for the solver
    X["mh_toe_tip_l"] = list(sum((H[f"{t}toe_02_l"] for t in ("big", "index", "middle", "ring", "little")), Vector()) / 5)
    X["mh_toe_tip_r"] = list(sum((H[f"{t}toe_02_r"] for t in ("big", "index", "middle", "ring", "little")), Vector()) / 5)
    for s in ("l", "r"):
        X[f"mh_bigtoe_{s}"] = list(H[f"bigtoe_01_{s}"]); X[f"mh_littletoe_{s}"] = list(H[f"littletoe_01_{s}"])
    out["joints"] = {k: [round(x, 6) for x in v] for k, v in J.items()}
    out["missing"] = [b for b in KEEP if b not in J]
    save_json(JOINTS, out)
    log("joints", len(J), "missing", out["missing"])
    log(json.dumps(D, indent=1, default=lambda o: list(o) if hasattr(o, "__len__") else str(o))[:6000])


def centre_in_thickness(bvh, p, n, reach=0.05):
    """Midpoint of the first solid span met by the line p + n*t, entering from the +n side."""
    o = p + n * reach
    hit = bvh.ray_cast(o, -n, 2 * reach)
    if hit[0] is None:
        return None
    a = hit[0]
    hit2 = bvh.ray_cast(a - n * 1e-4, -n, 2 * reach)
    if hit2[0] is None:
        return None
    return (a + hit2[0]) / 2


def kabsch(pairs):
    """Rotation R minimising sum w |R u - v|^2 (u, v unit vectors)."""
    import numpy as np
    Hm = np.zeros((3, 3))
    for u, v, w in pairs:
        Hm += w * np.outer(np.array(u), np.array(v))
    U, S, Vt = np.linalg.svd(Hm)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    Dm = np.diag([1, 1, d])
    R = Vt.T @ Dm @ U.T
    return Matrix(R.tolist())


import time  # noqa
main()
