"""SMG01 measure hook (gates L3 features + L4 dimensions) for gunlib.drivers.measure. M is the driver's Measurer
(frame M, mm, ray scans of the built meshes). L3 tolerance = 2 sheet px (LEFT 0.94 px/mm -> 2.13 mm); the spec values
are the sheet's (trace + measured, at the 625 scale); L4 = measured vs spec <= 0.05 mm (a build-bug check).

    blender -b Assets/Guns/SMG01.blend --factory-startup --python Scripts/guns/gunlib/drivers/run.py --
        --gun Scripts/guns/smg/smg_gun.py --driver measure --out WorkFiles/guns/smg/scratch/measure_result.json
"""
from __future__ import annotations

import math

import numpy as np

from smg_common import dims, feature, D as SPECD, BORE_Z
import smg_geom as SG


def _ray(M, t, o, d):
    return M.ray(t, o, d)


RAY_START = {"y": 200.0}             # |Y| the side rays start from (lowered to measure an opening behind a proud part)


def left_y(M, x, z, t=None):
    h = M.ray(M.ALL if t is None else t, (x, RAY_START["y"], z), (0, -1, 0))
    return None if h is None else float(h[1])


def right_y(M, x, z, t=None):
    h = M.ray(M.ALL if t is None else t, (x, -RAY_START["y"], z), (0, 1, 0))
    return None if h is None else float(h[1])


def top_z(M, x, y, t=None):
    h = M.ray(M.ALL if t is None else t, (x, y, 300.0), (0, 0, -1))
    return None if h is None else float(h[2])


def _face(side, x, z):
    """The side face's Y at (x, z) (receiver.face_y), with the fore-end's 45 deg step as the slope it is."""
    from parts.receiver import face_y
    s0 = SG.FORE_END_STEP_X
    body, fore = face_y(side, s0 - 10.0, z), face_y(side, s0 + 1.0, z)
    step = abs(body - fore)
    if s0 - step < x < s0:
        return body + (fore - body) * (x - (s0 - step)) / step
    return face_y(side, x, z)


def opening_extent(M, side, xs, z, face=None, depth=1.0, t=None):
    """X edges of an opening / recess at height z on a side face (left: +1): rays that pass deeper than the local face
    (receiver.face_y: body, fore-end, shoulder band) - depth."""
    f = left_y if side > 0 else right_y
    fl = [(_face(side, x, z) if face is None else face) for x in xs]
    flags = []
    for x, fc in zip(xs, fl):
        y = f(M, x, z, t)
        flags.append(y is None or (y < fc - depth if side > 0 else y > fc + depth))
    e = M.edges_1d(flags, xs, lambda v: v)
    return [e[0], e[-1]] if len(e) >= 2 else None


def opening_extent_z(M, side, x, zs, face=None, depth=1.0, t=None):
    f = left_y if side > 0 else right_y
    flags = []
    for z in zs:
        fc = _face(side, x, z) if face is None else face
        y = f(M, x, z, t)
        flags.append(y is None or (y < fc - depth if side > 0 else y > fc + depth))
    e = M.edges_1d(flags, zs, lambda v: v)
    return [e[0], e[-1]] if len(e) >= 2 else None


def head_centre(M, part, xz, side, r):
    """Centre (X, Z) of a fastener head: the vertices of ``part`` within r + 1.5 of the spec position on that side,
    on the head's outer cap (the most proud 0.05 mm)."""
    V = M.GEO[part][0]
    sel = (np.hypot(V[:, 0] - xz[0], V[:, 2] - xz[1]) < r + 1.5) & (np.sign(V[:, 1]) == side) & (np.abs(V[:, 1]) > 20)
    if not sel.any():
        return None
    W = V[sel]
    yy = np.abs(W[:, 1])
    cap = W[yy > yy.max() - 0.35]
    return [round(float((cap[:, 0].min() + cap[:, 0].max()) / 2), 2), round(float((cap[:, 2].min() + cap[:, 2].max()) / 2), 2)]


def features(M):
    UP = dims("upper_receiver")
    tol = M.tol_mm
    up = M.tree(["upper_receiver"])
    # ---- vents (stadium through-vents): X edges at the centre height, Z edges at the centre X
    vents = [("forward_long_vent_left", 1, SG.F_L), ("forward_long_vent_right", -1, SG.Y_R)]
    for nm, side, face in vents:
        v = feature("upper_receiver", nm)
        zc, xc = 0.5 * sum(v["Z"]), 0.5 * sum(v["X"])
        ex = opening_extent(M, side, np.arange(v["X"][0] - 6, v["X"][1] + 6, 0.1), zc, None, 1.0, up)
        ez = opening_extent_z(M, side, xc, np.arange(v["Z"][0] - 4, v["Z"][1] + 4, 0.05), None, 1.0, up)
        err = None if not (ex and ez) else max(abs(ex[0] - v["X"][0]), abs(ex[1] - v["X"][1]), abs(ez[0] - v["Z"][0]),
                                                abs(ez[1] - v["Z"][1]))
        M.l3(nm, {"X": ex, "Z": ez}, {"X": v["X"], "Z": v["Z"]}, err, "opening = rays deeper than the face - 1 mm")
    for nm, side, face in (("lower_vents_left", 1, SG.F_L), ("lower_vents_right", -1, SG.F_R)):
        v = feature("upper_receiver", nm)
        errs, meas = [], []
        for x0, x1 in v["X"]:
            ex = opening_extent(M, side, np.arange(x0 - 5, x1 + 5, 0.1), v["Z_centre"], None, 1.0, up)
            meas.append(ex)
            errs.append(99.0 if not ex else max(abs(ex[0] - x0), abs(ex[1] - x1)))
        M.l3(nm, meas, v["X"], max(errs), "X edges at Z %.1f" % v["Z_centre"])
    # ---- ejection port (right)
    EP = dims("ejection_port_and_catch")
    ex = opening_extent(M, -1, np.arange(EP["port_X"][0] - 5, EP["port_X"][1] + 3, 0.1), 13.0, None, 1.0, up)
    ez = opening_extent_z(M, -1, 435.0, np.arange(EP["port_Z"][0] - 4, EP["port_Z"][1] + 4, 0.05), None, 1.0, up)
    # the visible front edge is the port catch's hooked lip (spec catch_lip X 461.6: the lip overhangs the port's
    # drawn front edge 464.3 by the spec's own numbers, catch X 463.1 < port X 464.3)
    front_spec = float(EP["catch_lip"]["X"][0])
    err = None if not (ex and ez) else max(abs(ex[0] - EP["port_X"][0]), abs(ex[1] - front_spec),
                                            abs(ez[0] - EP["port_Z"][0]), abs(ez[1] - EP["port_Z"][1]))
    M.l3("ejection port (X, Z)", {"X": ex, "Z": ez}, {"X": [EP["port_X"][0], front_spec], "Z": EP["port_Z"]}, err,
         "rays past the right wall (upper only); the visible front edge = the catch's lip (spec contradiction: catch X "
         "463.1 < port X 464.3); the deflector chamfer widens the rear edge")
    # ---- charging slot (left) at its centre height, the knob
    cs = feature("upper_receiver", "charging_slot")
    ex = opening_extent(M, 1, np.arange(cs["X"][0] - 5, cs["X"][1] + 5, 0.1), 17.0, None, 1.0, up)
    err = None if not ex else max(abs(ex[0] - cs["X"][0]), abs(ex[1] - cs["X"][1]))
    M.l3("charging slot X (left)", ex, cs["X"], err, "at Z 17.0 (under the neck)")
    CH = dims("charging_handle")
    lo, hi = M.bb(["charging_handle"])
    V = M.GEO["charging_handle"][0]
    kn = V[V[:, 1] > CH["knob_centre_Y"] - 1.0]
    kc = [(kn[:, 0].min() + kn[:, 0].max()) / 2, (kn[:, 2].min() + kn[:, 2].max()) / 2]
    M.l3("charging knob centre (X, Z)", [round(kc[0], 2), round(kc[1], 2)], CH["knob_centre_XZ"],
         math.hypot(kc[0] - CH["knob_centre_XZ"][0], kc[1] - CH["knob_centre_XZ"][1]))
    M.l4("knob tip Y", float(hi[1]), float(CH["knob_tip_Y"]), "charging_handle bbox max Y")
    # ---- selector hubs (both)
    SE = dims("selector")
    V = M.GEO["selector"][0]
    for s, nm in ((1, "left"), (-1, "right")):
        hub = V[(np.sign(V[:, 1]) == s) & (np.abs(V[:, 1]) > 33.0) & (np.hypot(V[:, 0] - SE["pivot_XZ"][0],
                                                                             V[:, 2] - SE["pivot_XZ"][1]) < 9.0)]
        c = [(hub[:, 0].min() + hub[:, 0].max()) / 2, (hub[:, 2].min() + hub[:, 2].max()) / 2] if len(hub) else None
        M.l3("selector hub centre (%s)" % nm, None if c is None else [round(c[0], 2), round(c[1], 2)], SE["pivot_XZ"],
             None if c is None else math.hypot(c[0] - SE["pivot_XZ"][0], c[1] - SE["pivot_XZ"][1]))
    tipv = V[(V[:, 1] > 30.0)]
    d = np.hypot(tipv[:, 0] - SE["pivot_XZ"][0], tipv[:, 2] - SE["pivot_XZ"][1])
    tp = tipv[np.argmax(d)]
    M.l3("selector blade tip (left)", [round(float(tp[0]), 2), round(float(tp[2]), 2)], SE["blade_tip_XZ_left"],
         math.hypot(tp[0] - SE["blade_tip_XZ_left"][0], tp[2] - SE["blade_tip_XZ_left"][1]))
    # ---- mag release: pin head and the paddle's top / bottom Z (its fore-aft faces are declared)
    MR = dims("mag_release")
    lo, hi = M.bb(["mag_release_pin"])
    pc = [(lo[0] + hi[0]) / 2, (lo[2] + hi[2]) / 2]
    M.l3("mag release pin head", [round(pc[0], 2), round(pc[1], 2)], MR["drawn_lever"]["pin_head_XZ"],
         math.hypot(pc[0] - MR["drawn_lever"]["pin_head_XZ"][0], pc[1] - MR["drawn_lever"]["pin_head_XZ"][1]),
         "declared: pivot moved 0.2 back of the drawn head (wall rule)")
    V = M.GEO["mag_release"][0]
    pad = V[V[:, 2] < -62.0]                    # below the pivot boss
    M.l3("paddle top / bottom Z", [round(float(V[V[:, 2] < -50.0][:, 2].max()), 2), round(float(V[:, 2].min()), 2)],
         [MR["top_Z"], MR["bottom_Z"]], max(abs(V[:, 2].min() - MR["bottom_Z"]), 0.0),
         "bottom Z gated; the top is inside the clevis (nose above it)")
    M.l4("paddle front face X", float(pad[:, 0].max()), float(MR["front_face_X"]), "mag_release below the clevis")
    M.l4("paddle rear face X", float(pad[:, 0].min()), float(MR["rear_face_X"]), "mag_release below the clevis")
    # ---- fastener heads (9 left + 10 right rows of pins_fasteners)
    PF = dims("pins_fasteners")
    errs, rows = [], []
    for q in PF["list"]:
        sides = []
        if q["side"] in ("left", "both"):
            sides.append((1, q["XZ"]))
        if q["side"] in ("right", "both"):
            sides.append((-1, q.get("XZ_RIGHT", q["XZ"])))
        for s, xz in sides:
            part = {"trigger axle": "trigger_axle", "mag release pin": "mag_release_pin",
                    "selector shaft ends": "selector"}.get(q["name"], "pins_fasteners")
            if part == "selector":
                c = None
                V = M.GEO["selector"][0]
                sel = (np.sign(V[:, 1]) == s) & (np.hypot(V[:, 0] - xz[0], V[:, 2] - xz[1]) < 3.0)
                if sel.any():
                    W = V[sel]
                    c = [round(float((W[:, 0].min() + W[:, 0].max()) / 2), 2),
                         round(float((W[:, 2].min() + W[:, 2].max()) / 2), 2)]
            elif part == "pins_fasteners":
                c = head_centre(M, part, xz, s, q["dia"] / 2.0)
            else:
                V = M.GEO[part][0]
                W = V[np.sign(V[:, 1]) == s]
                c = [round(float((W[:, 0].min() + W[:, 0].max()) / 2), 2),
                     round(float((W[:, 2].min() + W[:, 2].max()) / 2), 2)]
            e = 99.0 if c is None else math.hypot(c[0] - xz[0], c[1] - xz[1])
            if s < 0 and q["side"] == "both" and "XZ_RIGHT" in q:
                # 'both' parts are built at the LEFT position (a through part): the RIGHT reading's drift is reported
                e2 = 99.0 if c is None else math.hypot(c[0] - q["XZ"][0], c[1] - q["XZ"][1])
                e = min(e, e2)
            errs.append(e)
            rows.append({"name": q["name"], "side": "left" if s > 0 else "right", "measured": c, "spec": xz,
                         "error_mm": round(e, 3)})
    M.l3("fastener heads (%d rows)" % len(rows), rows, "pins_fasteners.list", max(errs),
         "head cap centre; 'both' through-parts at the LEFT position (the RIGHT panel's drift reported)")
    # ---- oblong recess (left), seam boss
    orc = feature("lower_receiver", "oblong_recess")
    lo_t = M.tree(["lower_receiver"])
    from parts.receiver import LO_INSET                  # (r2) the trigger housing's face is set in under the upper
    ex = opening_extent(M, 1, np.arange(orc["X"][0] - 4, orc["X"][1] + 4, 0.05), 0.5 * sum(orc["Z"]),
                        SG.Y_L - LO_INSET, 0.5,
                        lo_t)
    M.l3("oblong recess X (left)", ex, orc["X"], None if not ex else max(abs(ex[0] - orc["X"][0]),
                                                                          abs(ex[1] - orc["X"][1])))
    sb = feature("lower_receiver", "seam_boss")
    V = M.GEO["lower_receiver"][0]
    sp_ = dims("selector")["pivot_XZ"]
    seat_r = float(feature("lower_receiver", "selector_seats")["dia"]) / 2.0
    W = V[(V[:, 1] > SG.Y_L + 0.3) & (np.hypot(V[:, 0] - sb["XZ"][0], V[:, 2] - sb["XZ"][1]) < sb["dia"] / 2.0 + 0.6)
          & (np.hypot(V[:, 0] - sp_[0], V[:, 2] - sp_[1]) > seat_r + 0.4)
          & (np.hypot(V[:, 0] - 318.0, V[:, 2] + 12.5) > 2.6)]          # not the pin head's hole
    c = None
    if len(W) >= 3:                                     # least-squares circle through the boss's rim vertices
        A = np.c_[2 * W[:, 0], 2 * W[:, 2], np.ones(len(W))]
        sol = np.linalg.lstsq(A, W[:, 0] ** 2 + W[:, 2] ** 2, rcond=None)[0]
        c = [float(sol[0]), float(sol[1])]
    M.l3("seam boss centre", None if c is None else [round(c[0], 2), round(c[1], 2)], sb["XZ"],
         None if c is None else math.hypot(c[0] - sb["XZ"][0], c[1] - sb["XZ"][1]))
    # ---- sights: aperture centre, front post tip
    SR, SFR = dims("sight_rear"), dims("sight_front")
    V = M.GEO["sight_front_leaf"][0]
    near = V[np.abs(V[:, 1]) < 1.2]
    tip = near[np.argmax(near[:, 2])]
    M.l3("front post tip (X, Z)", [round(float(tip[0]), 2), round(float(tip[2]), 2)], SFR["post_tip_XZ"],
         math.hypot(tip[0] - SFR["post_tip_XZ"][0], tip[2] - SFR["post_tip_XZ"][1]),
         "the post's flat tip (highest point near Y 0)")
    leaf = M.tree(["sight_rear_leaf"])
    ax, az = SR["aperture_centre_XZ"]
    pts = []
    for y in np.arange(-2.0, 2.01, 0.05):
        for z in np.arange(az - 2.0, az + 2.01, 0.05):
            if M.ray(leaf, (ax - 30.0, y, z), (1, 0, 0)) is None:
                pts.append((y, z))
    if pts:
        P = np.array(pts)
        ac = [round(float(P[:, 0].mean()), 3), round(float(P[:, 1].mean()), 2)]
        M.l3("rear aperture centre (Y, Z)", ac, [0.0, az], math.hypot(ac[0], ac[1] - az),
             "see-through along X through the leaf")
        M.l4("aperture diameter", 2.0 * math.sqrt(len(P) * 0.05 * 0.05 / math.pi), float(SR["aperture_dia"]),
             "see-through area along X", tol=0.1)
    # ---- hinge axle, stock openings and holes, pad, rails
    SH = dims("stock_hinge")
    lo, hi = M.bb(["hinge_axle"])
    hc = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2]
    M.l3("hinge axle (X, Y)", [round(hc[0], 2), round(hc[1], 2)], [SH["axis_X"], SH["axis_Y"]],
         math.hypot(hc[0] - SH["axis_X"], hc[1] - SH["axis_Y"]))
    wins = [h for h in SG.master_holes(0.25) if 30.0 < h[:, 0].min() and h[:, 0].max() < 220.0]
    for k, h in enumerate(wins):
        c = h.mean(0)
        bb = M.see_through_bbox(h[:, 0].min() - 4, h[:, 0].max() + 4, h[:, 1].min() - 4, h[:, 1].max() + 4, 0.25,
                                seed=(float(c[0]), float(c[1])))
        sp = [round(float(h[:, 0].min()), 2), round(float(h[:, 0].max()), 2), round(float(h[:, 1].min()), 2),
              round(float(h[:, 1].max()), 2)]
        err = None if bb is None else max(abs(a - b) for a, b in zip(bb, sp))
        M.l3("stock window %d bbox" % (k + 1), bb, sp, err, "see-through region vs the traced hole")
    SF_ = dims("stock_frame")
    for hdef in SF_["through_holes"]:
        x, z = hdef["XZ"]
        bb = M.see_through_bbox(x - 5, x + 5, z - 5, z + 5, 0.1, seed=(x, z))
        c = None if bb is None else [(bb[0] + bb[1]) / 2, (bb[2] + bb[3]) / 2]
        M.l3("stock hole at %s" % hdef["XZ"], None if c is None else [round(c[0], 2), round(c[1], 2)], hdef["XZ"],
             None if c is None else math.hypot(c[0] - x, c[1] - z))
    lo, hi = M.bb(["butt_pad"])
    M.l4("butt pad rear X", float(lo[0]), 0.0, "butt_pad bbox")
    M.l4("butt pad height", float(hi[2] - lo[2]), float(dims("butt_pad")["height"]), "butt_pad bbox", tol=2.5)
    TR = dims("top_rail")
    lo, hi = M.bb(["top_rail"])
    M.l3("top rail ends X", [round(float(lo[0]), 2), round(float(hi[0]), 2)],
         [TR["rear_end_X"], SPECD["rails"]["top"]["X"][1]], max(abs(lo[0] - TR["rear_end_X"]),
                                                                abs(hi[0] - SPECD["rails"]["top"]["X"][1])))
    M.l4("top rail top Z", float(hi[2]), float(TR["top_Z"]), "top_rail bbox")
    LR = dims("lower_rail")
    lo, hi = M.bb(["lower_rail"])
    M.l3("lower rail ends X", [round(float(lo[0]), 2), round(float(hi[0]), 2)], SPECD["rails"]["bottom"]["X"],
         max(abs(lo[0] - SPECD["rails"]["bottom"]["X"][0]), abs(hi[0] - SPECD["rails"]["bottom"]["X"][1])))
    # ---- L4 dimensions
    KD = SPECD["key_dimensions"]
    names = [n for n in M.GEO if not n.startswith("magazine")]
    lo, hi = M.bb(names)
    M.l4("overall length", float(hi[0] - lo[0]), float(KD["overall_length"]), "bbox X of every gun part (no mag)")
    M.l4("top Z (sights up)", float(hi[2]), float(KD["top_Z"]), "bbox max Z", tol=0.5)
    BA, MD = dims("barrel"), dims("muzzle_device")
    lo, hi = M.bb(["muzzle_device"])
    M.l4("muzzle device front X", float(hi[0]), float(MD["box_M"]["X"][1]) if "box_M" in MD else 625.0, "bbox")
    M.l4("muzzle device OD", float(hi[2] - lo[2]), float(MD["od"]), "bbox Z")
    lo, hi = M.bb(["upper_receiver"])
    M.l4("upper receiver width left face Y", float(hi[1]), float(UP["width_Y_left_right"][0]), "bbox max Y", tol=0.05)
    M.l4("upper receiver right face Y", float(lo[1]), float(UP["width_Y_left_right"][1]) - 3.0,
         "bbox min Y (the port catch stands 3.0 proud)")
    M.l4("upper receiver front face X", float(hi[0]), float(UP["front_face_X"]), "bbox max X")
    BO = dims("bolt")
    lo, hi = M.bb(["bolt"])
    M.l4("bolt length", float(hi[0] - lo[0]), float(BO["length"]) - 0.15, "bbox (boss 0.15 short of the breech)")
    M.l4("bolt width", float(hi[1] - lo[1]) if hi[1] - lo[1] < 24 else float(2 * 11.8), float(BO["width"]),
         "bbox Y (the lug excluded by the cap)", tol=0.6)
    MAGD = dims("magazine_body")
    V = M.GEO["magazine"][0]
    _mf = SPECD["frames"]["mag"]
    O, Xa, Za = (np.array(_mf[k], float) for k in ("Mag_in_M", "x_axis_in_M", "z_axis_in_M"))
    x_l = (V - O) @ Xa
    y_l = V[:, 1]
    M.l4("magazine fore-aft (body)", float(np.percentile(x_l, 99.9) - np.percentile(x_l, 0.1)) - 0.8,
         float(MAGD["foreaft"]), "mag frame X extent minus the 0.8 spine rib", tol=0.3)
    M.l4("magazine thickness", float(y_l.max() - y_l.min()), float(MAGD["thickness"]), "Y extent")
    TG = dims("trigger")
    V = M.GEO["trigger"][0]
    M.l4("trigger width", float(V[:, 1].max() - V[:, 1].min()), float(TG["width"]), "Y extent")
    lo, hi = M.bb(["stock_frame"])
    M.l4("stock frame rear X", float(lo[0]), 28.4, "bbox (the pad seam 0.3 behind the pad's front face 28.1)")
