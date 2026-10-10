"""Magazine fit at the FORM stage (the AR-01's R51 loop-back): the M-gates' geometry runs on the built LOD0 parts (frame
M), so a well / catch / notch change is proven before the UV, rig and export stages. Inside Blender. Promoted from the
AR-01's rifle_magfit_check.py (gunlib 0.2.0).

    blender -b <gun>.blend --factory-startup --python <shim> -- [--out json] [--collection name]

Two path kinds:
- "rock" (AK family, the AR-01): the gun's own hook ``cfg.magfit["gates"](S)`` builds the F-gates (the R51 rock path,
  its lug / tab selections and the catch window are gun data; rifle_gun_magfit.py);
- "straight" (SMG, carbine, pistol, sniper): the generic set below, from config data only.

The generic straight set (SMG_BUILD_PLAN 12.2 adapted to form time; the mag is placed by its seated frame and moved
along its own -Z, the catch rotates about its pin):
  M1  seated: 0 intersecting triangle pairs, magazine vs the gun (LOD0);
  M2  the catch nose to the notch's bearing face (the mag dropped along -Z until it bears: 0.0-0.3 mm); the overtravel
      to the top shelf (rays up the insert axis from the mag's top, catch excluded: 1.0-2.0 mm); the visible seam at
      the well's lower edge (mag surface within +-1 mm of the lip plane to the well parts, per side: <= 0.6 mm);
  M3  lateral per side and fore-aft (mag samples inside the well band to the gun, catch excluded: 0.2-0.6 mm); the
      catch engagement depth (the least rearward shift of the catch that lets the mag drop past it: >= 1.5 mm);
  M4  insert MagInsertStart -> Mag in 0.5 mm steps, catch at rest: 0 intersections except the declared allowance (the
      catch nose riding the mag's rear face / ramp: contacts with the catch part only, depth <= engagement + 0.3 mm,
      within the last catch_zone_mm of travel when set; the travel over which the nose rides is reported);
  M4b the same path with the catch at its release angle: 0 intersections;
  M5  removal (reverse) with the catch released: 0 intersections; M5b (info) removal with the catch at rest (expected
      to collide: proves retention);
  F5  catch sweep rest -> release with the mag seated: 0 intersections except the nose leaving the notch (depth <= the
      engagement, reported).
Config ``cfg.magfit`` (straight): mag_parts, catch, catch_pivot_M, catch_axis, release_deg, mag_origin_M,
mag_axes_M ({"x": .., "z": ..}: the mag frame's +X forward and +Z out of the well, in M), insert_mm (Mag ->
MagInsertStart), well_band ([z0, z1] in the mag frame: the part of the mag inside the well), lip_z (mag-frame Z of
the well's lower edge), well_parts (the parts forming the well's lower edge), catch_zone_mm, half_thickness,
half_length (mag-frame half sizes of the body at the well), out.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .. import fit as F
from .. import game as GM
from .. import gateutil as GU


class MagFitScene:
    """The gun's LOD0 parts split into the magazine and the rest (frame M, mm), with the trees the gates share."""

    def __init__(self, cfg, coll, mag_parts, catch=None):
        import bpy
        self.cfg = cfg
        objs = [o for o in bpy.data.collections[coll].objects if o.type == "MESH"]
        self.parts = {o.name: GU.mesh_np(o, cfg.grip) for o in objs}
        self.mag_parts = tuple(mag_parts)
        mV = [self.parts[n] for n in self.mag_parts if n in self.parts]
        off = 0
        Vs, Ts = [], []
        for V, T in mV:
            Vs.append(V)
            Ts.append(T + off)
            off += len(V)
        self.MV, self.MT = np.vstack(Vs), np.vstack(Ts)
        self.rn = [n for n in self.parts if n not in self.mag_parts]
        RV, RT, RL = [], [], []
        off = 0
        for i, n in enumerate(self.rn):
            V, T = self.parts[n]
            RV.append(V)
            RT.append(T + off)
            RL += [i] * len(T)
            off += len(V)
        self.RV, self.RT, self.RL = np.vstack(RV), np.vstack(RT), np.array(RL)
        self.rtree = GU.tree(self.RV, self.RT)
        self.catch = catch
        self.ci = self.rn.index(catch) if catch in self.rn else -1
        self.cV, self.cT = self.parts.get(catch, (np.zeros((0, 3)), np.zeros((0, 3), int)))
        self.ctree = GU.tree(self.cV, self.cT) if len(self.cT) else None

    def hits(self, V, MT=None):
        """(n gun tri pairs, n with the catch, n with other parts, other part names)."""
        pairs = self.rtree.overlap(GU.tree(V, self.MT if MT is None else MT))
        if not pairs:
            return 0, 0, 0, []
        labs = self.RL[[p[0] for p in pairs]]
        nc = int((labs == self.ci).sum())
        other = sorted({self.rn[k] for k in labs if k != self.ci})
        return len(pairs), nc, len(pairs) - nc, other


# ====================================================================== the generic straight-insert set
def _mag_frame(C):
    z = np.asarray(C["mag_axes_M"]["z"], float)
    z /= np.linalg.norm(z)
    x = np.asarray(C["mag_axes_M"]["x"], float)
    x = x - (x @ z) * z
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.asarray(C["mag_origin_M"], float), x, y, z


def straight_gates(S, C):
    o, ax, ay, az = _mag_frame(C)
    MV, MT = S.MV, S.MT
    piv = np.asarray(C["catch_pivot_M"], float)
    cax = np.asarray(C["catch_axis"], float)
    rel = float(C["release_deg"])
    gates = []
    # gun without the catch (the catch is tested on its own)
    keep = S.RL != S.ci
    gtree = GU.tree(S.RV, S.RT[keep])

    def mag_at(s):
        return MV - s * az                                                 # s mm down the insert axis

    def catch_at(deg, shift=0.0):
        Vc = F.apply(F.rot_matrix(piv, cax, deg), S.cV) if deg else S.cV.copy()
        return Vc - shift * ax                                             # + shift = rearward (out of the notch)

    def n_hits(Vm, Vc=None, with_gun=True):
        mt = GU.tree(Vm, MT)
        ng = len(gtree.overlap(mt)) if with_gun else 0
        nc = len(GU.tree(Vc, S.cT).overlap(mt)) if (Vc is not None and len(S.cT)) else 0
        return ng, nc

    # ---------------------------------------------------------------- M1 seated
    ng, nc = n_hits(MV, catch_at(0.0))
    gates.append(GU.gate("M1 seated: intersecting triangle pairs, magazine vs the gun (LOD0)",
                         {"gun": ng, "catch": nc}, "0", ng == 0 and nc == 0))
    # ---------------------------------------------------------------- M2 bearing gap, overtravel, seam
    bear = None
    for s in np.arange(0.0, 3.0001, 0.01):
        if n_hits(mag_at(s), catch_at(0.0), with_gun=False)[1]:
            bear = round(float(s - 0.01), 3) if s > 0 else 0.0
            break
    from mathutils import Vector
    Sm = GM.dense_samples(MV, MT, 0.25)
    Lm = np.c_[(Sm - o) @ ax, (Sm - o) @ ay, (Sm - o) @ az]
    top = Sm[Lm[:, 2] > Lm[:, 2].max() - 3.0]
    over = 1e9
    for p in top:
        h = gtree.ray_cast(Vector(p) + Vector(az * 1e-4), Vector(az), 30.0)
        if h[0] is not None:
            over = min(over, h[3])
    lip = float(C["lip_z"])
    band = (Lm[:, 2] > lip - 1.0) & (Lm[:, 2] < lip + 1.0)
    wp = [i for i, n in enumerate(S.rn) if n in C.get("well_parts", S.rn) and i != S.ci]
    wtree = GU.tree(S.RV, S.RT[np.isin(S.RL, wp)])
    seam = {}
    hx, hy = float(C["half_length"]), float(C["half_thickness"])
    for side, sel in (("front", Lm[:, 0] > hx - 1.0), ("rear", Lm[:, 0] < -hx + 1.0),
                      ("left", Lm[:, 1] > hy - 1.0), ("right", Lm[:, 1] < -hy + 1.0)):
        pts = Sm[band & sel]
        seam[side] = round(GU.nearest(pts, wtree, 5.0), 4) if len(pts) else None
    ok2 = bear is not None and 0.0 <= bear <= 0.3 and over < 1e8 and 1.0 <= over <= 2.0 and \
        all(v is not None and v <= 0.6 for v in seam.values())
    gates.append(GU.gate("M2 seat: catch nose to the notch bearing face; overtravel to the top shelf; visible seam at the "
                         "well's lower edge", {"bearing_gap_mm": bear, "overtravel_mm": None if over > 1e8 else
                                              round(float(over), 4), "seam_mm": seam},
                         "0.0-0.3; 1.0-2.0; <= 0.6 mm", ok2))
    # ---------------------------------------------------------------- M3 lateral, fore-aft, engagement
    w0, w1 = C["well_band"]
    inw = (Lm[:, 2] > w0) & (Lm[:, 2] < w1)
    cl = {}
    for side, sel in (("left", Lm[:, 1] > hy - 0.5), ("right", Lm[:, 1] < -hy + 0.5),
                      ("front", Lm[:, 0] > hx - 0.5), ("rear", Lm[:, 0] < -hx + 0.5)):
        pts = Sm[inw & sel]
        cl[side] = round(GU.nearest(pts, gtree, 3.0), 4) if len(pts) else None
    eng = None
    for e in np.arange(0.0, 6.0001, 0.05):
        Vc = catch_at(0.0, e)
        clear = all(not n_hits(mag_at(s), Vc, with_gun=False)[1] for s in np.arange(0.0, 6.0001, 0.25))
        if clear:
            eng = round(float(e), 3)
            break
    ok3 = all(v is not None and 0.2 - 1e-4 <= v <= 0.6 for v in cl.values()) and eng is not None and eng >= 1.5
    gates.append(GU.gate("M3 lateral per side; fore-aft; catch engagement depth", {"clearance_mm": cl,
                         "engagement_mm": eng}, "0.2-0.6; 0.2-0.6; >= 1.5 mm", ok3))
    # ---------------------------------------------------------------- M4 / M4b / M5 / M5b path
    ins = float(C["insert_mm"])
    s_vals = np.arange(ins, -1e-9, -0.5)
    if s_vals[-1] > 1e-9:
        s_vals = np.r_[s_vals, 0.0]
    zone = float(C.get("catch_zone_mm") or ins)          # travel window the ride is allowed in (default: the path)
    Vc0, Vcr = catch_at(0.0), catch_at(rel)
    ctree0, ctreer = GU.tree(Vc0, S.cT), GU.tree(Vcr, S.cT)
    lo0, hi0 = Vc0.min(0), Vc0.max(0)
    rec = {"rest": [], "released": []}
    allow = []
    other = []
    for s in s_vals:
        Q = mag_at(s)
        mt = GU.tree(Q, MT)
        ng = len(gtree.overlap(mt))
        n0 = len(ctree0.overlap(mt))
        nr = len(ctreer.overlap(mt))
        rec["rest"].append((round(float(s), 3), ng, n0))
        rec["released"].append((round(float(s), 3), ng, nr))
        if ng:
            other.append(round(float(s), 3))
        if n0:
            dep = GU.depth_inside(GM.dense_samples(Q, MT, 0.4), ctree0, lo0, hi0)
            allow.append({"insert_mm": round(float(s), 3), "pairs": n0, "depth_mm": round(dep, 3),
                          "in_zone": bool(s <= zone + 1e-9)})
    lim = (eng or 0.0) + 0.3
    ok4 = not other and all(a["in_zone"] and a["depth_mm"] <= lim for a in allow)
    ride = [a["insert_mm"] for a in allow]
    gates.append(GU.gate("M4 insert path MagInsertStart -> Mag (0.5 mm steps, catch at rest)",
                         {"steps": len(s_vals), "gun_contacts_at": other[:12], "catch_ride_mm": [min(ride), max(ride)]
                          if ride else None, "catch_contacts": len(allow),
                          "worst_catch_depth_mm": max((a["depth_mm"] for a in allow), default=0.0)},
                         "0 intersections except the catch nose riding the mag (depth <= engagement + 0.3 mm, last "
                         "%.2f mm only)" % zone, ok4))
    n4b = sum(1 for _, ng, nr in rec["released"] if ng or nr)
    gates.append(GU.gate("M4b insert path with the catch released (%.1f deg)" % rel,
                         {"steps": len(s_vals), "intersecting_steps": n4b}, "0", n4b == 0))
    gates.append(GU.gate("M5 removal path (reverse) with the catch released", {"steps": len(s_vals),
                         "intersecting_steps": n4b}, "0", n4b == 0,
                         "the same pose set traversed backwards: identical intersection record"))
    n5b = sum(1 for _, ng, n0 in rec["rest"] if n0)
    gates.append(GU.gate("M5b (info) removal with the catch at rest", {"colliding_steps": n5b},
                         "reported (expected to collide: the catch retains)", True))
    # ---------------------------------------------------------------- F5 catch sweep, mag seated
    mtree = GU.tree(MV, MT)
    lo_m, hi_m = MV.min(0), MV.max(0)
    sweep, worst = [], 0.0
    sgn = 1.0 if rel >= 0 else -1.0
    for a in np.arange(0.0, abs(rel) + 1e-4, 0.25):
        Vc = catch_at(sgn * a)
        n = len(GU.tree(Vc, S.cT).overlap(mtree))
        if n:
            worst = max(worst, GU.depth_inside(GM.dense_samples(Vc, S.cT, 0.25), mtree, lo_m, hi_m))
        sweep.append((round(float(sgn * a), 2), n))
    ok5 = worst <= (eng or 0.0) + 1e-6
    gates.append(GU.gate("F5 catch sweep rest -> release with the magazine seated",
                         {"steps": len(sweep), "intersecting_steps": sum(1 for _, n in sweep if n),
                          "worst_depth_mm": round(worst, 4)},
                         "0 intersections except the nose leaving the notch (depth <= the engagement)", ok5))
    return gates


def main(cfg, argv=None):
    import bpy
    argv = GU.argv_after_dashes() if argv is None else argv
    C = cfg.magfit
    out_path = Path(GU.opt(argv, "--out") or C.get("out") or cfg.gates / "form_magfit.json")
    coll = GU.opt(argv, "--collection", cfg.parts_collection)
    S = MagFitScene(cfg, coll, C["mag_parts"], C.get("catch"))
    out = C["header"](S) if "header" in C else {"stage": "form: magazine fit (%s path)" % C.get("path", "straight")}
    out.setdefault("blend", bpy.data.filepath)
    gates = C["gates"](S) if "gates" in C else straight_gates(S, C)
    out["gates"] = gates
    out["failed"] = [g["name"] for g in gates if not g["pass"]]
    out["status"] = "pass" if not out["failed"] else "fail"
    out_path.write_text(json.dumps(out, indent=1, default=str))
    tag = "[%s-magfit]" % cfg.log_tag
    for g in gates:
        print(tag, "PASS" if g["pass"] else "FAIL", g["name"], json.dumps(g["value"], default=str)[:400], flush=True)
    print(tag, "MAGFIT", out["status"], out["failed"], flush=True)
    return out
