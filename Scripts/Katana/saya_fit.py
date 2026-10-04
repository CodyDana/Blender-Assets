"""Saya FIT stage: seat the SHIPPED katana (the exact exported FBX bytes, read-only) and derive the saya's inner cavity.

Adapted from the Snow Flower sheath fit (Scripts/SnowFlower/v4/shv4_fit.py, read-only; its suffix_extremes /
swept-support / support_polygon / chord-domination logic is copied here, never imported) to a CURVED blade:

* Every sword point is mapped to arc coordinates (s, rho, y) about the blade's mune arc centre (saya_spec). The draw is
  a rotation about that centre (= DrawPivot), i.e. a translation toward smaller s. So the cavity section at station s
  must hold every sword point with s' >= s (it passes through s on the way out): the SWEPT support, a suffix maximum
  over s' of each point's projection onto the section directions - exactly the Snow Flower straight-sweep code, in
  unbent coordinates.
* The swept set = vertices of ALL THREE katana LODs inside the mouth plane, plus samples every 0.5 mm along every
  edge (the Snow Flower lesson: vertex support alone missed a long LOD2 edge by 0.24 mm).
* Required support per direction = max(habaki swept support + 0.12, blade swept support + clearance(direction));
  clearance = 1.0 at the edge and the sides, 0.5 at the mune (spec saya.cavity.rule).
* Each saya LOD gets its own knot stations and direction count; knots are lifted until every chord dominates the
  dense required support (the loft interpolates linearly between stations).

    blender -b --factory-startup --python Scripts/Katana/build_saya.py -- --stage fit
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

import saya_spec as S
import katana_spec as K

OUT = S.ROOT / "WorkFiles" / "katana" / "saya_build" / "fit"


def log(*a):
    print("[SAYA-FIT]", *a, flush=True)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------- katana bytes
def load_katana(fbx=None, edge_step=S.EDGE_STEP, clear=True):
    """Import the shipped katana FBX. Returns {lod: dict(V (N,3) mm sword frame, T (M,3), tslot (M,) slot names,
    E edge samples (K,3), ES slot name per edge sample)} and the imported objects."""
    import bpy
    fbx = Path(fbx or S.KATANA_FBX)
    if clear:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    new = [o for o in bpy.data.objects if o not in before]
    out = {}
    for o in new:
        if o.type != "MESH" or o.name.startswith("UCX_"):
            continue
        lv = 0 if "LOD0" in o.name else (1 if "LOD1" in o.name else 2)
        me = o.data
        M = np.array(o.matrix_world)
        V = np.array([v.co[:] for v in me.vertices])
        V = (np.c_[V, np.ones(len(V))] @ M.T)[:, :3] * 1000.0
        slots = [m.name.split(".")[0] if m else "" for m in me.materials]
        me.calc_loop_triangles()
        T = np.array([lt.vertices[:] for lt in me.loop_triangles], int)
        tslot = np.array([slots[lt.material_index] for lt in me.loop_triangles])
        # edge samples, slot of the edge = slot of one adjacent face
        eslot = {}
        for p in me.polygons:
            for ek in p.edge_keys:
                eslot.setdefault(ek, slots[p.material_index])
        E = np.array(list(eslot.keys()), int)
        es = np.array(list(eslot.values()))
        a, b = V[E[:, 0]], V[E[:, 1]]
        L = np.linalg.norm(b - a, axis=1)
        k = np.maximum(np.ceil(L / edge_step).astype(int), 1)
        rep = np.repeat(np.arange(len(E)), k - 1)
        t = np.concatenate([np.arange(1, m) / m for m in k]) if len(rep) else np.zeros(0)
        out[lv] = {"V": V, "T": T, "tslot": tslot, "E": a[rep] + (b[rep] - a[rep]) * t[:, None], "ES": es[rep],
                   "name": o.name, "obj": o}
    return out, new


def vertex_slots(d):
    """Slot name per vertex (any adjacent triangle's slot; habaki/blade never share vertices)."""
    vs = np.empty(len(d["V"]), dtype=d["tslot"].dtype)
    for k in range(3):
        vs[d["T"][:, k]] = d["tslot"]
    return vs


def inside_sets(kat):
    """Sword points that enter the saya (s > the mouth plane), split into habaki (Fittings slot) and blade (Blade
    slot). Vertices + edge samples of all three LODs."""
    hab, bla = [], []
    for lv, d in kat.items():
        vs = vertex_slots(d)
        for P, sl in ((d["V"], vs), (d["E"], d["ES"])):
            s, rho, y = S.xyz_to_arc(P)
            inn = s > S.S_MO - 1e-6
            hab.append(P[inn & (sl == "M_Katana_Fittings")])
            bla.append(P[inn & (sl == "M_Katana_Blade")])
    hab, bla = np.vstack(hab), np.vstack(bla)
    return hab, bla


# ---------------------------------------------------------------------------------------------- Snow Flower logic
def suffix_extremes(zs, vals, zq):
    """For query stations zq: max over points with z >= zq of vals (copied from shv4_fit)."""
    order = np.argsort(zs)
    z_sorted = zs[order]
    v_sorted = vals[order]
    suf = np.maximum.accumulate(v_sorted[::-1], axis=0)[::-1]
    idx = np.searchsorted(z_sorted, zq, side="left")
    out = np.full((len(zq),) + vals.shape[1:], -np.inf)
    ok = idx < len(z_sorted)
    out[ok] = suf[idx[ok]]
    return out


def swept_support_arc(P, dirs, sq):
    """Swept support of points P (sword frame) at stations sq in the (rho, y) section plane."""
    s, rho, y = S.xyz_to_arc(P)
    proj = np.c_[rho, y] @ dirs.T
    return suffix_extremes(s, proj, sq)


def _clip(poly, n, h):
    out = []
    m = len(poly)
    for k in range(m):
        P, Q = poly[k], poly[(k + 1) % m]
        dp, dq = P @ n - h, Q @ n - h
        if dp <= 0:
            out.append(P)
        if (dp < 0) != (dq < 0) and dp != dq:
            out.append(P + (Q - P) * (dp / (dp - dq)))
    return np.array(out)


def support_polygon(h, dirs, sup, min_edge=0.05):
    """Polygon {x : n_i . x <= h_i} with exactly one vertex between consecutive directions (copied from shv4_fit;
    min_edge 0.15 -> 0.05 so corner shaving eats less of the 0.12 habaki clearance). Returns (vertices, min over
    directions of h_final - sup)."""
    M = len(dirs)
    h = np.asarray(h, float).copy()

    def X(i, j):
        return np.linalg.solve(np.array([dirs[i], dirs[j]]), np.array([h[i], h[j]]))

    for _ in range(600):
        poly = np.array([[-1e4, -1e4], [1e4, -1e4], [1e4, 1e4], [-1e4, 1e4]], float)
        for i in range(M):
            poly = _clip(poly, dirs[i], h[i])
        h = np.array([float((poly @ dirs[i]).max()) for i in range(M)])
        V = np.array([X(i, (i + 1) % M) for i in range(M)])
        bad = []
        for i in range(M):
            t = np.array([-dirs[i][1], dirs[i][0]])
            if float((V[i] - V[i - 1]) @ t) < min_edge:
                bad.append(i)
        if not bad:
            return V, float(np.min(h - sup))
        for i in bad:
            h[i] -= 0.01
    raise RuntimeError("support polygon did not converge")


def directions(M):
    ang = 2 * math.pi * np.arange(M) / M + math.pi      # M divisible by 4: faces normal to -rho (mune), +-y, +rho
    return np.stack([np.cos(ang), np.sin(ang)], 1)


def clearance(dirs):
    nr = dirs[:, 0]
    return np.where(nr >= 0, S.CLR_EDGE, S.lerp(S.CLR_SIDE, S.CLR_MUNE, -nr))


def knots(level):
    st = {0: (2.0, 40.0, 4.0), 1: (4.0, 80.0, 8.0), 2: (9.0, 85.0, 13.0)}[level]
    pk = list(np.arange(S.S_MO, 27.51, st[0]))
    if pk[-1] < 27.49:
        pk.append(27.5)
    pk.append(S.S_POCKET_END)
    first = {0: 30.0, 1: 31.0, 2: 33.0}[level]
    bl = [first]
    n = int(math.ceil((K.S_Y - first) / st[1]))
    bl += [first + (K.S_Y - first) * i / n for i in range(1, n + 1)]
    m = int(math.ceil((K.S_TIP - K.S_Y) / st[2]))
    ki = [K.S_Y + (K.S_TIP - K.S_Y) * i / m for i in range(1, m + 1)]
    return np.array(pk + bl + ki + [S.S_CAV_END])


def required(hab, bla, dirs, sq):
    clr = clearance(dirs)
    Hh = swept_support_arc(hab, dirs, sq)
    Hb = swept_support_arc(bla, dirs, sq)
    req = np.maximum(Hh + S.CLR_HABAKI, Hb + clr[None, :])
    fin = np.isfinite(req).all(axis=1)
    last = int(np.nonzero(fin)[0].max())
    req[last + 1:] = req[last]                     # past the tip: keep the tip section (to the cavity end cap)
    return req, Hh, Hb


def cavity_polygons(hab, bla, level):
    M = S.CAV_DIRS[level]
    dirs = directions(M)
    st = knots(level)
    s_hab = S.xyz_to_arc(hab)[0]
    sq = np.unique(np.round(np.concatenate([np.arange(S.S_MO, S.S_CAV_END + 1e-9, 0.25),
                                            np.arange(S.S_MO, S.S_POCKET_END + 2.0, 0.05), s_hab, st]), 6))
    sq = sq[(sq >= S.S_MO) & (sq <= S.S_CAV_END)]
    req, Hh, Hb = required(hab, bla, dirs, sq)
    # knot values: the pocket holds the habaki support up to S_POCKET_END ("0.5 below the habaki top")
    def req_at(s):
        return req[np.argmin(np.abs(sq - s))]
    # the pocket keeps the habaki section at s 27.0 (below the habaki's 0.4 mm top round, which starts at s 27.37 on
    # the edge side) out to its end, so the round never meets a chord
    V = np.array([req_at(min(s, 27.0)) if s <= S.S_POCKET_END + 1e-9 else req_at(s) for s in st])
    lift_total = np.zeros_like(V)
    for _ in range(4):
        for k in range(len(st) - 1):
            sel = (sq >= st[k] - 1e-6) & (sq <= st[k + 1] + 1e-6)
            tt = ((sq[sel] - st[k]) / (st[k + 1] - st[k]))[:, None]
            chord = (1 - tt) * V[k] + tt * V[k + 1]
            viol = np.maximum((req[sel] - chord).max(axis=0), 0.0)
            V[k] += viol
            V[k + 1] += viol
            lift_total[k] += viol
            lift_total[k + 1] += viol
    # the 3D loft joins stations with straight chords; between stations s_k, s_k+1 a chord of the arc dips toward the
    # centre (smaller rho) by (R + rho) (1 - cos(ds / 2R)): on the edge side (+rho) that is toward the blade. Both knots
    # of the segment are pushed out by that sagitta in the +rho directions (0.05 mm at 40 mm steps, 0.25 at 85 mm).
    nr = np.maximum(dirs[:, 0], 0.0)
    sag_add = np.zeros_like(V)
    for k in range(len(st) - 1):
        ds = st[k + 1] - st[k]
        sag = (S.R + 40.0) * (1 - math.cos(ds / (2 * S.R)))
        sag_add[k] = np.maximum(sag_add[k], nr * sag)
        sag_add[k + 1] = np.maximum(sag_add[k + 1], nr * sag)
    V = V + sag_add
    polys, cuts = [], []
    clr = clearance(dirs)
    for k, s in enumerate(st):
        hab_like = s <= S.S_POCKET_END + 1e-9
        sup = V[k] - (S.CLR_HABAKI if hab_like else clr)
        P, c = support_polygon(V[k], dirs, sup)
        polys.append(P)
        cuts.append(c)
    return st, np.array(polys), dirs, float(min(cuts)), (float(lift_total.max()), float(st[int(np.argmax(lift_total.max(axis=1)))]))


def poly_dist_inside(inner, outer):
    """Min distance from the inner polygon's vertices to the outer convex polygon's edges, and vice versa
    (outer vertices to inner edges); both positive when nested."""
    def pt_edges(p, Q):
        best = np.inf
        n = len(Q)
        for i in range(n):
            a, b = Q[i], Q[(i + 1) % n]
            e = b - a
            t = np.clip(((p - a) @ e) / (e @ e), 0, 1)
            best = min(best, float(np.linalg.norm(a + t * e - p)))
        return best
    d1 = min(pt_edges(p, outer) for p in inner)
    d2 = min(pt_edges(p, inner) for p in outer)
    return min(d1, d2)


# ---------------------------------------------------------------------------------------------- stage
def run():
    OUT.mkdir(parents=True, exist_ok=True)
    sha = sha256(S.KATANA_FBX)
    if sha != S.KATANA_FBX_SHA:
        raise RuntimeError(f"SM_Katana.fbx changed ({sha}); the saya must be refitted to the new katana interface")
    kat, _ = load_katana()
    log("katana LODs", {k: (len(v["V"]), len(v["T"]), len(v["E"])) for k, v in kat.items()})
    hab, bla = inside_sets(kat)
    s_h, rho_h, y_h = S.xyz_to_arc(hab)
    s_b, rho_b, y_b = S.xyz_to_arc(bla)
    log(f"swept set: habaki {len(hab)} pts (s {s_h.min():.2f}..{s_h.max():.2f}, rho {rho_h.min():.2f}..{rho_h.max():.2f}, "
        f"|y| {np.abs(y_h).max():.2f}); blade {len(bla)} pts (s {s_b.min():.2f}..{s_b.max():.2f}, rho "
        f"{rho_b.min():.2f}..{rho_b.max():.2f})")
    # hilt (everything that stays outside): its lowest point vs the mouth plane
    hilt_s = []
    for d in kat.values():
        s, _, _ = S.xyz_to_arc(d["V"])
        vs = vertex_slots(d)
        habaki = (vs == "M_Katana_Fittings") & (d["V"][:, 2] > 57.999)
        hilt_s.append(s[(s <= S.S_MO) & ~habaki])
    hilt_max_s = float(np.concatenate(hilt_s).max())
    tip_s = float(s_b.max())
    res = {"katana_fbx_sha256": sha, "habaki_s_range": [float(s_h.min()), float(s_h.max())],
           "blade_tip_s": tip_s, "hilt_max_s": hilt_max_s, "seat_gap_mm_on_arc": S.S_MO - hilt_max_s,
           "tip_to_cavity_end_mm": S.S_CAV_END - tip_s, "levels": {}}
    for lv in (0, 1, 2):
        st, polys, dirs, cut, lift = cavity_polygons(hab, bla, lv)
        walls = []
        for s, P in zip(st, polys):
            outer = S.outer_ring(s, S.OUTER_N[lv])
            walls.append(poly_dist_inside(P, outer))
        walls = np.array(walls)
        pocket = st <= S.S_POCKET_END + 1e-9
        np.savez(OUT / f"cavity_L{lv}.npz", stations=st, polys=polys, dirs=dirs)
        res["levels"][lv] = {"stations": int(len(st)), "dirs": int(len(dirs)),
                             "min_design_clearance_after_shave_mm": round(cut, 4), "max_chord_lift_mm": round(lift[0], 4), "max_lift_at_s": round(lift[1], 2),
                             "min_wall_mm": round(float(walls.min()), 3), "min_wall_at_s": round(float(st[walls.argmin()]), 2),
                             "min_wall_pocket_mm": round(float(walls[pocket].min()), 3),
                             "min_wall_body_mm": round(float(walls[~pocket].min()), 3),
                             "pocket_rho_range": [round(float(polys[0][:, 0].min()), 3), round(float(polys[0][:, 0].max()), 3)],
                             "pocket_half_y": round(float(np.abs(polys[0][:, 1]).max()), 3)}
        log(f"cavity L{lv}: {res['levels'][lv]}")
    (OUT / "fit.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    log("fit saved", OUT / "fit.json", f"tip s {tip_s:.2f}, seat gap {res['seat_gap_mm_on_arc']:.3f}")
    return res
