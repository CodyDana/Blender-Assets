"""Stage 1 blockout: primary volumes straight from the traced side profiles at spec scale (frame M, mm).

Each traced part is extruded across its spec width (TOP authority); the stock follows the TOP width profile; the
rear sight block narrows above Z 30 (the leaf bed); round parts (barrel, gas tube, rod) are cylinders; the magazine is
the traced magazine ring extruded to the 28 mm thickness under test. No bevels, no booleans: this stage only proves
the volumes and the scale (gate L1).
"""
from __future__ import annotations

import json

import numpy as np

from rifle_common import SPEC, TRACE
from gunlib import geo2d as G
from gunlib import mesh as MS


def _wfun_stock():
    w = SPEC.dims("buttstock")["width_by_X_TOP"]
    xs = np.array(sorted(float(k) for k in w))
    ws = np.array([w[str(int(x))] if str(int(x)) in w else w[str(x)] for x in xs])
    return lambda x: np.interp(x, xs, ws) / 2.0


def scaled_prism(P2, half_w_fun):
    m = MS.prism(P2, -1.0, 1.0, "XZ")
    V = m.verts()
    V[:, 1] *= half_w_fun(V[:, 0])
    out = MS.Mesh()
    out.add_verts(V)
    out.F = m.F
    return out


def parts(mag_thickness=None):
    S = SPEC
    if mag_thickness is None:
        mag_thickness = float(S.key["magazine"]["thickness"])
    out = {}

    def prof(pid, tol=0.35):
        return G.ccw(G.dp_simplify(S.profile(pid), tol))

    def yr(pid):
        b = S.box(pid)["Y"]
        return b[0], b[1]

    for pid in ("receiver", "dust_cover", "gas_tube_rear_cap", "upper_handguard", "lower_handguard",
                "handguard_front_band", "gas_block", "muzzle_brake", "trigger", "trigger_guard", "mag_catch",
                "pistol_grip", "butt_plate", "sling_swivel_rear"):
        y0, y1 = yr(pid)
        out[pid] = MS.prism(prof(pid), y0, y1)
    # rear sight block + leaf: full base width below Z 30, the leaf bed (+-10) above
    P = prof("rear_sight_block")
    lo = G.clip_y(P, None, 30.0)
    hi = G.clip_y(P, 30.0, None)
    out["rear_sight_block"] = MS.prism(lo, -21.75, 21.75).extend(MS.prism(hi, -10.0, 10.0))
    # front sight block: collar (+-11) below Z 11, ears (+-10.7) above
    P = prof("front_sight_block")
    out["front_sight_block"] = MS.prism(G.clip_y(P, None, 11.0), -11.0, 11.0).extend(
        MS.prism(G.clip_y(P, 11.0, None), -10.7, 10.7))
    out["buttstock"] = scaled_prism(G.ccw(G.dp_simplify(S.profile("buttstock"), 0.35)), _wfun_stock())
    d = S.dims("barrel")
    out["barrel"] = MS.cylinder((d["chamber_face_X"], 0, 0), (d["crown_X"], 0, 0), d["dia"] / 2, 32)
    g = S.dims("gas_tube")
    out["gas_tube"] = MS.cylinder((524.0, 0, g["axis_Z"]), (691.0, 0, g["axis_Z"]), g["dia"] / 2, 32)
    r = S.dims("cleaning_rod")
    out["cleaning_rod"] = MS.cylinder((647.0, 0, r["axis_Z"]), (812.0, 0, r["axis_Z"]), r["dia"] / 2, 16)
    sel = np.array(S.feature("selector", "face_outline_M")["XZ"], float)
    out["selector"] = MS.prism(G.ccw(sel), -25.25, -20.75)
    ch = S.dims("bolt_carrier")["charging_handle"]
    out["bolt_carrier"] = MS.box(ch["X"][0], ch["X"][1], ch["tip_Y"], -20.75, ch["Z"][0], ch["Z"][1])
    j = json.loads((TRACE / "LEFT_outline.json").read_text())
    ring = max(j["magazine"], key=lambda r: r["area_px"])
    M = G.ccw(G.dp_simplify(np.array(ring["mm"], float), 0.35))
    M = G.clip_y(M, None, -12.0)          # the hidden top up to the lips is not in the trace; the visible part is
    top = M[:, 1].max()
    out["magazine"] = MS.prism(M, -mag_thickness / 2, mag_thickness / 2)
    return out
