"""AR-01 magazine interface (stage-2 loop-back after the stage-6 M2 / M3 fail, 2026-10-06): the reload path, the
magazine's interface silhouettes and the swept envelopes the receiver's well, front-trunnion lug pocket and the catch
are cut from. Plain Python (numpy only); imported by parts/receiver_right.py and parts/magazine.py (the part modules
never import each other, so the interface lives here) and by the fit checks.

The real stamped-receiver 7.62x39 pattern: the front trunnion (a machined block riveted in the receiver's front) has a
ledge at its lower rear; the magazine's front lug goes up behind it, then the magazine rocks back about its front and
the lug's hook moves forward over the ledge (it sits on the ledge, under the trunnion: the front top stop) while the
rear lug comes up past the spring catch and snaps over its nose.

The reload path (rifle_spec sockets, R51): MagInsertStart -> MagRockStart is a straight move of INSERT_D along the
tilted magazine's -Z, then a pure rotation of ROCK_DEG about PIVOT (the Mag socket = the magazine origin) back to the
seat. Everything the magazine can touch on that path is cut from the swept envelope of the magazine's silhouettes
(per Y band, in the XZ plane: every motion is a rotation about Y plus an XZ move) plus the clearance of its row in the
clearance table (GUN_BUILDING_STUDY 3.7), the way the saya cavity was fitted to the katana.

Why the pivot sits low on the front spine (R51): the visible seam at the well's front edge is the distance the front
spine moves at the receiver's bottom sheet over the path; with the old hook (429, -16) 15 mm above the sheet and an
18 deg rock that is 5.3 mm (the measured 4.89 mm front seam). On the front spine 1.85 mm above the sheet's inside face
an 8 deg rock moves it 0.4 mm, while the lug's hook, 11.5 mm higher, still swings 1.6 mm forward over the ledge.
"""
from __future__ import annotations

import math

import numpy as np

from rifle_common import SPEC

# ------------------------------------------------------------------------------------------------ magazine arcs
MAG_C = np.array([604.8, 3.3])      # concentric arcs about M (604.8, 3.3) (spec magazine_body)
R_F, R_R = 180.8, 239.0
MAG_HT = float(SPEC.key["magazine"]["thickness"]) / 2       # 13.0 (R32)
FRONT_TOP_Z = -17.0                 # the magazine's front zone top (u > 0.745)
LIP_Z = -12.0
WELL_REAR_X = 369.3                 # the magazine's flat rear face inside the well
# R51: under the receiver's ledge the rear face steps back to 0.4 from the trigger guard's front tab (was a chamfer from
# (369.3, -30.4) to (367.6, -33.5), 0.74 from the tab); below Z -31 the rear spine arc (the trace) takes over
REAR_STEP = [(368.0, -33.5), (368.3, -31.0), (368.3, -29.6), (WELL_REAR_X, -29.36)]


def front_x(z):
    """The magazine's front spine (front arc) at height z (frame M)."""
    return float(MAG_C[0] - math.sqrt(R_F ** 2 - (z - MAG_C[1]) ** 2))


def rear_x(z):
    return float(MAG_C[0] - math.sqrt(R_R ** 2 - (z - MAG_C[1]) ** 2))


# ------------------------------------------------------------------------------------------------ the reload path
def _sock(name):
    return next(s for s in SPEC.sockets["rifle"] if s["socket"] == name)


_m, _r, _i = _sock("Mag"), _sock("MagRockStart"), _sock("MagInsertStart")
PIVOT = np.array([_m["M_mm"][0], _m["M_mm"][2]], float)      # the Mag socket (M frame, XZ)
ROCK_DEG = float(_r["unreal_rotation_deg"]["pitch"])           # Unreal pitch + = the base swings forward
INSERT_D = float(np.hypot(_i["M_mm"][0] - PIVOT[0], _i["M_mm"][2] - PIVOT[1]))
ROCK = math.radians(ROCK_DEG)


def pose_xz(P, phi, s=0.0):
    """Points P (n x 2, XZ seated) at rock angle phi (rad, base forward) and insert offset s (mm along the tilted -Z)."""
    P = np.asarray(P, float)
    d = P - PIVOT
    c, sn = math.cos(phi), math.sin(phi)
    x = PIVOT[0] + d[:, 0] * c - d[:, 1] * sn + s * sn
    z = PIVOT[1] + d[:, 0] * sn + d[:, 1] * c - s * c
    return np.c_[x, z]


APPROACH = 14.0          # the straight approach from under the receiver, continued along the insert line (every point
#                          that ends above the bottom sheet starts below it)


def path(n_insert=33, n_rock=65, approach=APPROACH):
    """(phi, s) poses of the reload path: the approach from below and the insert along the tilted -Z at the rock angle,
    then the rock to the seat. The cuts use the approach too: the magazine has to arrive at MagInsertStart from under
    the receiver (the M4 gate checks MagInsertStart -> Mag)."""
    n_app = int(round(approach / 0.25))
    out = [(ROCK, float(s)) for s in np.linspace(INSERT_D + approach, INSERT_D, n_app + 1)[:-1]] if n_app else []
    out += [(ROCK, float(s)) for s in np.linspace(INSERT_D, 0.0, n_insert)]
    out += [(ROCK * (1.0 - u), 0.0) for u in np.linspace(0.0, 1.0, n_rock)[1:]]
    return out


# ------------------------------------------------------------------------------------------------ interface shapes
# front lug (seated, frame M). The HOOK is the lug's top tab: it stands TAB_PROUD in front of the spine and, at the
# seat, sits on the trunnion's ledge under the trunnion (the front top stop). The lug BODY below it tapers back into
# the spine; every part that stands in front of the spine stays above the receiver's bottom sheet over the whole path
# (its lowest point at MagInsertStart clears the sheet's inside face), so the well opening never has to pass it.
TAB_Z = (-17.6, -15.4)
TAB_X0, TAB_TIP = 422.6, 428.6
TAB_HW = 4.0
LUG_HW = 5.2                        # c5: the lug ~10.4 wide
LUG_SIDE = [(421.0, -17.6), (426.1, -17.6), (425.95, -21.3), (421.0, -21.3)]   # 0.9 / 0.26 in front of the spine
LUG_WIN = ((425.6, 431.0), (-18.3, -19.6), 2.4)   # c5's U-loop: a window pocket in the lug body's front
KNOB_Z, KNOB_R = (-19.6, -23.6), 1.3
KNOB_IN = 1.4                       # knob centre this far behind the spine: the pin heads stand on the side face only
SPINE_BEAD_TOP_Z = -31.8            # the front spine beads start under the sheet's reach over the whole path
# rear catch lug: a block on the rear spine just under the trigger guard's front tang; its flat bottom rests over the
# catch's nose (an arc about the catch pin: rotation-invariant, so the release never lifts the magazine)
REAR_LUG_X0, REAR_LUG_X1 = 367.3, 373.0
REAR_LUG_Z = (-37.85, -35.2)
REAR_LUG_HW = 3.3                   # between the trigger guard's catch cheeks (the catch is +-3.5 wide)
CATCH_NOSE_R = 13.0                 # catch top in front of the notch: arc about the catch pin (r 15.0 behind it)
CATCH_NOTCH_X = 367.1               # notch back wall (0.2 behind the lug's rear face)

# clearance table rows (GUN_BUILDING_STUDY 3.7) used here
C_SEAM = 0.06                       # visible seam: added to the swept motion at the sheet (seam = sweep + 0.06)
C_LUG = 0.2                         # seated mag: lug in its recess 0.1-0.4
C_TOP = 0.25                        # seated mag: top stop 0.1-0.5 (the path lifts the tab's front up to 0.09)
C_REAR = 0.15
C_MIN = 0.26                        # floor: never closer than this to the seated magazine (the outline chords stand
#                                    up to 0.04 in front of the true arcs)


def body_front_sil():
    """Body silhouette (XZ) for the front envelope, |Y| <= MAG_HT + 0.3 (body, plates, front block)."""
    zs = np.linspace(-70.0, FRONT_TOP_Z, 160)
    P = [(front_x(z), z) for z in zs]
    return np.array(P + [(395.0, FRONT_TOP_Z), (395.0, -70.0)])


def tab_sil():
    return np.array([(TAB_X0, TAB_Z[0]), (TAB_TIP, TAB_Z[0]), (TAB_TIP, TAB_Z[1]), (TAB_X0, TAB_Z[1])])


def lug_sils():
    """Lug body + hook tab silhouettes (XZ): the body |Y| <= LUG_HW, the tab |Y| <= TAB_HW."""
    return [np.array(LUG_SIDE, float), tab_sil()]


def rear_sil():
    """Rear face silhouette (XZ) for the rear envelope: the rear arc below the chamfer, the chamfer, the flat face to
    the lips."""
    P = [(rear_x(z), z) for z in np.linspace(-70.0, -31.0, 60)]
    P += REAR_STEP[1:] + [(WELL_REAR_X, LIP_Z)]
    return np.array(P + [(395.0, LIP_Z), (395.0, -70.0)])


def rear_lug_sil():
    return np.array([(REAR_LUG_X0, REAR_LUG_Z[0]), (REAR_LUG_X1, REAR_LUG_Z[0]), (REAR_LUG_X1, REAR_LUG_Z[1]),
                     (REAR_LUG_X0, REAR_LUG_Z[1])])


# ------------------------------------------------------------------------------------------------ envelopes
def _xcuts(P, z):
    """x of every crossing of the closed polygon P with the line Z = z."""
    out = []
    A, B = P, np.roll(P, -1, 0)
    m = (A[:, 1] - z) * (B[:, 1] - z) <= 0
    m &= A[:, 1] != B[:, 1]
    for a, b in zip(A[m], B[m]):
        out.append(a[0] + (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]))
    return out


def envelope(polys, zs, side="front", poses=None):
    """Swept envelope over the path: per height z, the largest (front) / smallest (rear) x any polygon reaches.
    NaN where nothing passes."""
    poses = poses or path()
    zs = np.asarray(zs, float)
    E = np.full(len(zs), -np.inf if side == "front" else np.inf)
    for phi, s in poses:
        for P in polys:
            Q = pose_xz(P, phi, s)
            A, B = Q, np.roll(Q, -1, 0)
            dz = B[:, 1] - A[:, 1]
            ok = dz != 0
            A, B, dz = A[ok], B[ok], dz[ok]
            t = (zs[:, None] - A[None, :, 1]) / dz[None, :]
            m = (t >= 0) & (t <= 1)
            x = A[None, :, 0] + (B[None, :, 0] - A[None, :, 0]) * t
            if side == "front":
                E = np.maximum(E, np.where(m, x, -np.inf).max(1))
            else:
                E = np.minimum(E, np.where(m, x, np.inf).min(1))
    E[~np.isfinite(E)] = np.nan
    return E


def _dilate(zs, E, c, dz=None):
    """Clearance c in every direction (Minkowski in Z over dz (default c), plus c in X):
    x(z) = max over |z' - z| <= dz of E(z') + c."""
    dz = c if dz is None else dz
    out = np.full(len(zs), np.nan)
    for i, z in enumerate(zs):
        w = E[np.abs(zs - z) <= dz + 1e-9]
        w = w[~np.isnan(w)]
        if len(w):
            out[i] = w.max() + c
    return out


def _dp(P, tol):
    """Douglas-Peucker on an open polyline (x, z)."""
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    d = b - a
    n = np.hypot(*d) or 1.0
    dist = np.abs(d[0] * (P[:, 1] - a[1]) - d[1] * (P[:, 0] - a[0])) / n
    i = int(np.argmax(dist))
    if dist[i] <= tol:
        return np.array([a, b])
    return np.vstack([_dp(P[:i + 1], tol)[:-1], _dp(P[i:], tol)])


DP_TOL = 0.006          # the simplified cut line is pushed DP_TOL further out, so it still holds the dense envelope


def _profile(polys, z0, z1, c, step=0.05, side="front", clamp=None, floor=True, dz=None):
    zs = np.arange(z0, z1 + 1e-9, step)
    sg = 1.0 if side == "front" else -1.0
    E = sg * _dilate(zs, sg * envelope(polys, zs, side=side), c, dz)
    if floor:
        seat = sg * _dilate(zs, sg * envelope(polys, zs, side=side, poses=[(0.0, 0.0)]), C_MIN)   # C_MIN all round
        E = np.where(np.isnan(seat), E, sg * np.fmax(sg * E, sg * seat))
    if clamp is not None:
        E = np.where(np.isnan(E), E, (np.fmax if side == "front" else np.fmin)(E, clamp + sg * DP_TOL * 0))
    ok = ~np.isnan(E)
    P = np.c_[E[ok] + sg * DP_TOL, zs[ok]]
    return [(float(x), float(z)) for x, z in _dp(P, DP_TOL)]


def zmax_over_path(polys, poses=None):
    poses = poses or path()
    return max(float(pose_xz(P, phi, s)[:, 1].max()) for phi, s in poses for P in polys)


# ------------------------------------------------------------------------------------------------ receiver cutters
SHEET_OUT_Z, SHEET_IN_Z = -30.85, -29.85      # the receiver's bottom sheet at the well (outer / inner face)
_cache = {}


def well_front_profile(z0=-46.0):
    """Front boundary of the well cut in the body band (|Y| <= well half width): (x, z) points from z0 up to the body
    roof (the body's highest point on the path + C_TOP: the trunnion's underside over the front zone), x = the body's
    swept envelope + C_SEAM."""
    if "front" in _cache:
        return _cache["front"]
    roof = zmax_over_path([body_front_sil()]) + C_TOP
    prof = _profile([body_front_sil()], z0, roof - 0.01, C_SEAM)
    _cache["front"] = (prof, roof)
    return prof, roof


def pocket_profile(z0=-46.0):
    """Lug pocket in the front trunnion, two bands. Lug band (|Y| <= LUG_HW + C_LUG): x = the (lug body + body) swept
    envelope + C_LUG (in every direction) up to the roof. Tab band (|Y| <= TAB_HW + C_LUG): adds the hook tab, whose
    approach from under the receiver needs a channel up the trunnion's lower rear face (the real pattern's lug slot at
    the front of the well); the channel's front wall ends in the LEDGE C_LUG under the seated tab (the rock swings the
    tab forward over it). Roof = the tab's highest point on the path + C_TOP (the front top stop).
    Returns (lug-band profile, tab-band profile, roof)."""
    if "pocket" in _cache:
        return _cache["pocket"]
    roof = zmax_over_path(lug_sils()) + C_TOP
    body = body_front_sil()
    lug = _profile([np.array(LUG_SIDE, float), body], z0, roof - 0.01, C_LUG)
    tab = _profile(lug_sils() + [body], z0, roof - 0.01, C_LUG)
    _cache["pocket"] = (lug, tab, roof)
    return _cache["pocket"]


def well_rear_profile(z0=-29.35, z1=-27.9, x_max=368.75):
    """Rear boundary of the well cut through the bottom sheet behind the opening (the ledge sheet, Z -29.28 .. -28.28),
    |Y| <= well half width: x = min(x_max, the rear face's swept envelope - C_REAR), from z1 down to z0; below z0 the
    edge drops straight at x_max (no vertex near the ledge's outer face: a slanted cut there left slivers). The
    rock-start pose's tilted rear face (its top leans back) passes the sheet there; the opening's rear edge moved from
    368.8 to x_max."""
    if "rear_prof" in _cache:
        return _cache["rear_prof"]
    # (no C_MIN floor: under the ledge's outer face there is no receiver behind the magazine's rear step)
    # (Z dilation 0.05 only: the magazine's rear step tucks 0.2-0.3 under the ledge's outer face, in front of nothing)
    prof = _profile([rear_sil()], z0, z1, C_REAR, side="rear", clamp=x_max + DP_TOL, floor=False, dz=0.05)
    pts = [(float(x), float(z)) for x, z in prof]
    _cache["rear_prof"] = pts[::-1]           # descending z (the polygon runs down the rear edge)
    return _cache["rear_prof"]


def report():
    """Numbers for the record: swept motion of the front spine at the sheet, the hook's overlap of the ledge, the lug
    channel."""
    zs = np.array([SHEET_OUT_Z, -30.35, SHEET_IN_Z])
    E = envelope([body_front_sil()], zs)
    seat = np.array([max(_xcuts(body_front_sil(), z)) for z in zs])
    _lug, prof, roof = pocket_profile()
    z_ledge = TAB_Z[0] - C_LUG - 0.05
    x_ledge = float(np.interp(z_ledge, [p[1] for p in prof], [p[0] for p in prof]))
    return {"pivot_M": PIVOT.tolist(), "rock_deg": ROCK_DEG, "insert_mm": round(INSERT_D, 4),
            "front_sweep_at_sheet_mm": dict(zip(("outer", "mid", "inner"), np.round(E - seat, 4).tolist())),
            "front_seam_at_sheet_mm": dict(zip(("outer", "mid", "inner"), np.round(E - seat + C_SEAM, 4).tolist())),
            "pocket_roof_Z": round(roof, 3), "ledge_top_Z": round(z_ledge, 3), "ledge_rear_X": round(x_ledge, 3),
            "hook_over_ledge_mm": round(TAB_TIP - x_ledge, 3),
            "body_roof_Z": round(well_front_profile()[1], 3), "well_front_points": len(well_front_profile()[0]),
            "pocket_points": len(prof),
            "channel_front_at_sheet_X": round(float(np.interp(SHEET_OUT_Z, [p[1] for p in prof], [p[0] for p in prof])), 3),
            "spine_at_sheet_X": round(front_x(SHEET_OUT_Z), 3)}


if __name__ == "__main__":
    import json
    print(json.dumps(report(), indent=1))
