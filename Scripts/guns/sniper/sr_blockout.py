"""SR01 stage 1 blockout: the primary volumes straight from the traced GR part outlines at the ruled scale (frame M,
mm), plain Python (gunlib.mesh). Each traced part ring (Douglas-Peucker 0.5 mm) is extruded across its spec width;
round parts (receiver, bolt shroud, barrel, device, knob) are cylinders / spheres; the folded bipod is the traced
ring across the leg span; the scope is its traced ring across its bell width (W1b replaces it with the attachment).
No bevels, no booleans: this stage proves the volumes and the scale (gate L1).
"""
from __future__ import annotations

import numpy as np

from gunlib import geo2d as G
from gunlib import mesh as MS
from sr_common import box, dims, part_rings, trace, half_at, CHASSIS_HALF, BUTT_HALF

# trace part key -> (object name, Y half-width or (y0, y1))
WIDTH = {
    "butt_pad": ("butt_pad", 30.6),
    "pad_plate": ("pad_plate", 22.0),
    "butt": ("butt", 27.0),
    "cheek_riser": ("cheek_riser", 34.5),
    "chassis_centre": ("chassis_centre", 29.0),
    "chassis_forend": ("chassis_forend", 36.9),
    "trigger_guard": ("trigger_guard", 9.0),
    "grip": ("grip", 16.0),
    "trigger": ("trigger", 3.0),
    "mag_release": ("mag_release", 5.0),
    "magazine": ("magazine", 13.25),
    "rail": ("rail", 10.6),
    "bipod": ("bipod", 29.2),
    "bolt_handle": ("bolt_handle_stem", (-72.0, -12.0)),
}


def scope_revolve(axis_z=57.6, step=2.0):
    """The drawn scope as a revolve: radius(X) = the smaller half of the traced ring's span about the scope axis, plus
    the elevation turret (top), windage (right) and side-focus (left) drums at the drawn turret zone."""
    (r,), _ = part_rings("scope")
    prof = []
    for x in np.arange(r[:, 0].min() + 0.5, r[:, 0].max() - 0.5, step):
        zs = []
        for i in range(len(r)):
            a, b = r[i], r[(i + 1) % len(r)]
            if (a[0] - x) * (b[0] - x) <= 0 and a[0] != b[0]:
                zs.append(a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))
        if len(zs) >= 2:
            prof.append((x, max(min(max(zs) - axis_z, axis_z - min(zs)), 3.0)))
    x0 = prof[0][0]
    m = MS.revolve([(0.0, 0.0)] + [(x - x0, rr) for x, rr in prof] + [(prof[-1][0] - x0, 0.0)], (x0, 0, axis_z),
                   (1, 0, 0), 48)
    m.extend(MS.cylinder((462.0, 0, axis_z), (462.0, 0, 99.4), 16.0, 32))
    m.extend(MS.cylinder((462.0, 0, axis_z), (462.0, -34.0, axis_z), 14.0, 32))
    m.extend(MS.cylinder((488.0, 0, axis_z), (488.0, 50.4, axis_z), 13.0, 32))
    return m


PLAN = {"chassis_centre": CHASSIS_HALF, "chassis_forend": CHASSIS_HALF, "butt": BUTT_HALF}


def parts(tol=0.5):
    out = {}
    for key, (name, w) in WIDTH.items():
        y0, y1 = (-w, w) if not isinstance(w, tuple) else w
        outs, _holes = part_rings(key)
        m = MS.Mesh()
        for r in outs:
            Q = G.ccw(G.dp_simplify(r, tol))
            if len(Q) < 3:
                continue
            if key in PLAN:      # staircase of 10 mm X slabs at the plan half-width (no booleans at this stage)
                xs = np.arange(np.floor(Q[:, 0].min()), Q[:, 0].max() + 10.0, 10.0)
                for a, b in zip(xs[:-1], xs[1:]):
                    S = G.clip_x(Q, a, b)
                    if len(S) >= 3 and abs(G.area(S)) > 1.0:
                        h = half_at(PLAN[key], 0.5 * (a + b))
                        m.extend(MS.prism(S, -h, h, "XZ"))
            else:
                m.extend(MS.prism(Q, y0, y1, "XZ"))
        out[name] = m
    b = dims("barrel")
    out["barrel"] = MS.revolve([(0.0, 0.0), (0.0, b["od_at_forend"] / 2), (836.8 - 505.5, b["od_at_forend"] / 2),
                                (1049.7 - 505.5, b["od_at_device"] / 2), (1049.7 - 505.5, 0.0)], (505.5, 0, 0), (1, 0, 0), 48)
    for x0, x1 in ((401.8, 425.3), (507.1, 528.7)):                # the scope rings (W1b builds them)
        out.setdefault("scope_rings", MS.Mesh()).extend(MS.box(x0, x1, -15.0, 15.0, 29.9, 60.0))
    md = dims("muzzle_device")
    out["muzzle_device"] = MS.cylinder((1049.7, 0, 0), (1100.0, 0, 0), md["od"] / 2, 48)
    out["receiver"] = MS.cylinder((382.0, 0, 0), (567.3, 0, 0), dims("receiver")["dia"] / 2, 48)
    out["bolt_shroud"] = MS.cylinder((345.4, 0, 0), (382.0, 0, 0), 12.0, 32)
    k = dims("bolt_handle")
    out["scope_blockout"] = scope_revolve()
    out["bolt_knob"] = MS.ellipsoid(k["knob_centre_M"], k["knob_dia"] / 2, k["knob_dia"] / 2, k["knob_dia"] / 2, 32, 16)
    return out


def cuts():
    """Blockout's only booleans: the trigger-guard opening (the traced silhouette hole), Y +-20."""
    j = trace("GR")
    holes = [np.array(r, float) for r in j["silhouette"]["mm"] if len(r) > 3]
    from sr_common import signed_area
    hole = [h for h in holes if signed_area(h) < 0 and h[:, 0].min() > 330 and h[:, 0].max() < 400][0]
    return {"trigger_guard": [MS.prism(G.ccw(hole), -20.0, 20.0, "XZ")],
            "chassis_centre": [MS.prism(G.ccw(hole), -40.0, 40.0, "XZ")]}
