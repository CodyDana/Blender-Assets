"""Fasteners with real head shapes (gunlib 0.2.0; GUN_BUILDING_STUDY 3.2, spec fastener_rule; generalized from the
AR-01's rivets, butt screws and pins). Plain Python (numpy). UD-safe by construction: every chamfer / socket wall
>= 0.1 mm, no boolean: each head is a revolve or a hand-built ring mesh, so no run-out strip can form.

Real patterns (gun_standard.json ``hardware``, proportions of the nominal diameter d):
- flush pin / inset ring (moulded receivers: steel pins seated flush in the polymer, a 0.3 mm chamfer on the end, 0.1-0.2
  mm proud or sunk as the sheet reads): ``flush_pin``; the host's hole is ``pin_hole_cutter`` (pin + running gap);
- roll (spring) pin, ISO 8752: a split tube, wall ~0.2 d, slit ~0.2 d, chamfered ends: ``roll_pin``;
- domed rivet / flat rivet: ``rivet``;
- socket head cap screw, ISO 4762: head dia 1.5 d, height d, hex socket 0.75-0.8 d across flats, top edge chamfered:
  ``socket_cap``;
- button head hexagon socket, ISO 7380-1: head dia 1.9 d, height 0.55 d, socket 0.6-0.67 d (M5: 9.5 / 2.75 / 3):
  ``button_head``;
- countersunk hexagon socket, ISO 10642: 90 deg head, head dia 1.9-2.2 d (M5: 9.43 actual min, 11.2 theoretical),
  socket 0.6 d: ``countersunk`` (2 d);
- (no slotted head: a slot booleaned across a revolved head leaves near-tangent slivers; none is drawn on the
  line's guns so far. Build one by construction when a sheet shows it.)
Sizes are written in mm (never "M" + number in any name or text: IP / deny rule).

Frame: every head is built in its own frame (+Z out of the surface, origin at the seat-plane centre) and placed with
``place(mesh, centre_M, normal_M, ref_M)``; ``ref`` sets the socket / slot rotation.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from .. import lod as _lod
from ..mesh import Mesh, revolve

MIN_FEATURE = 0.1


def place(m: Mesh, centre, normal, ref=None) -> Mesh:
    """Local (+Z = normal) -> gun frame: origin to ``centre``, +Z to ``normal``, +X toward ``ref`` (projected)."""
    z = np.asarray(normal, float)
    z /= np.linalg.norm(z)
    r = np.array([1.0, 0.0, 0.0]) if ref is None else np.asarray(ref, float)
    if abs(r @ z) > 0.95:
        r = np.array([0.0, 1.0, 0.0]) if abs(z[1]) < 0.95 else np.array([1.0, 0.0, 0.0])
    x = r - (r @ z) * z
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    M = np.eye(4)
    M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = x, y, z, np.asarray(centre, float)
    return m.transformed(M)


def _c(c, size):
    return max(MIN_FEATURE, min(c, 0.45 * size))


def flush_pin(d: float, length: float, proud: float = 0.1, chamfer: float = 0.3, nseg: int = 24) -> Mesh:
    """A pin seated flush: its end face ``proud`` mm above the seat plane (negative = sunk), the outer end chamfered;
    the body runs ``length`` into the host (hidden, it fills the hole)."""
    r = d / 2.0
    c = _c(chamfer, r)
    return revolve([(-length, 0.0), (-length, r - c), (-length + c, r), (proud - c, r), (proud, r - c), (proud, 0.0)],
                   (0, 0, 0), (0, 0, 1), nseg)


def pin_hole_cutter(d: float, depth: float, gap: float = 0.15, nseg: int = 24) -> Mesh:
    """The host's hole for a flush pin: radius d/2 + gap (a visible ring), ``depth`` deep, 1 mm above the seat."""
    r = d / 2.0 + gap
    return revolve([(-depth, 0.0), (-depth, r), (1.0, r), (1.0, 0.0)], (0, 0, 0), (0, 0, 1), nseg)


def roll_pin(d: float, length: float, proud: float = 0.1, wall: Optional[float] = None, slit: Optional[float] = None,
             chamfer: float = 0.2, nseg: int = 24) -> Mesh:
    """ISO 8752 roll pin: a split tube along Z from -length to proud: wall ~0.2 d, slit ~0.2 d (on +X), chamfered
    outer edge at the visible end. Built ring by ring (a C-section loft), closed."""
    r = d / 2.0
    w = max(MIN_FEATURE * 3, wall if wall is not None else 0.2 * d)
    s = max(MIN_FEATURE * 3, slit if slit is not None else 0.2 * d)
    c = _c(chamfer, w)
    nseg = _lod.ring(nseg)
    half = math.asin(min(0.95, s / 2.0 / r))
    th = np.linspace(half, 2 * math.pi - half, nseg)
    ri = r - w
    m = Mesh()

    def ring(z, rad):
        return m.add_verts(np.c_[rad * np.cos(th), rad * np.sin(th), np.full(len(th), z)])
    zs = [(-length, r, ri), (proud - c, r, ri), (proud, r - c, ri)]
    outer = [ring(z, ro) for z, ro, _ in zs]
    inner = [ring(z, rin) for z, _, rin in zs]
    n = len(th)
    for a, b in zip(outer[:-1], outer[1:]):
        for k in range(n - 1):
            m.face((a[k], a[k + 1], b[k + 1], b[k]))
    for a, b in zip(inner[:-1], inner[1:]):
        for k in range(n - 1):
            m.face((b[k], b[k + 1], a[k + 1], a[k]))
    # ends (annular C) and the slit walls
    for o, i in ((outer[0], inner[0]), (outer[-1], inner[-1])):
        for k in range(n - 1):
            m.face((o[k], i[k], i[k + 1], o[k + 1]))
    for k in (0, n - 1):
        for j in range(len(zs) - 1):
            m.face((outer[j][k], outer[j + 1][k], inner[j + 1][k], inner[j][k]))
    return m


def rivet(d_head: float, h: float, shank_d: float, shank_len: float, domed: bool = True, nseg: int = 24) -> Mesh:
    """Domed (or flat with a 45 deg edge) rivet head on its shank; the head sits on the seat plane (Z 0 up)."""
    R = d_head / 2.0
    rs = shank_d / 2.0
    if domed:
        Rs = (R * R + h * h) / (2 * h)
        nr = _lod.count(5, 2)
        prof = [(-shank_len, 0.0), (-shank_len, rs), (0.0, rs), (0.0, R)]
        for j in range(1, nr + 1):
            z = h * j / nr
            rr = math.sqrt(max(Rs * Rs - (Rs - h + z) ** 2, 0.0))
            prof.append((z, rr if j < nr else 0.0))
    else:
        c = _c(0.3, h)
        prof = [(-shank_len, 0.0), (-shank_len, rs), (0.0, rs), (0.0, R), (h - c, R), (h, R - c), (h, 0.0)]
    return revolve(prof, (0, 0, 0), (0, 0, 1), nseg)


def _hex(s_af: float, phase: float = 0.0) -> np.ndarray:
    """Hexagon across flats s_af, corners at phase + 30 + 60 k deg (6 x 2D)."""
    rc = s_af / math.sqrt(3.0)
    t = np.radians(phase + 30.0 + 60.0 * np.arange(6))
    return np.c_[rc * np.cos(t), rc * np.sin(t)]


def _socket_head(prof_outer, z_top: float, r_top: float, s_af: float, depth: float, nseg: int, drill_deg=118.0):
    """A head = the revolved outer profile up to the top face's circle (radius r_top at z_top) + a hex socket built by
    construction: the top annulus from that circle to the hexagon (4 ring points per hex side), the socket's six
    walls ``depth`` deep and a drill-point cone at its bottom. Closed manifold, no boolean."""
    n6 = max(12, 6 * int(round(_lod.ring(nseg) / 6)))
    per = n6 // 6
    with _lod.hold(3):                                   # the ring count is already the level's (a multiple of 6)
        m = revolve(prof_outer, (0, 0, 0), (0, 0, 1), n6)
    # the revolve ends at (z_top, r_top) open (the profile's last point is not on the axis): find that ring
    V = m.verts()
    top_idx = [i for i in range(len(V)) if abs(V[i, 2] - z_top) < 1e-9 and abs(math.hypot(V[i, 0], V[i, 1]) - r_top) < 1e-6]
    top_idx = sorted(top_idx, key=lambda i: math.atan2(V[i, 1], V[i, 0]) % (2 * math.pi))
    # remove the cap face mesh.revolve put on that ring (an n-gon with exactly those vertices)
    ring_set = set(top_idx)
    m.F = [f for f in m.F if not (len(f) == len(top_idx) and set(f) == ring_set)]
    hx = _hex(s_af)
    pts = []
    for k in range(6):
        a, b = hx[k], hx[(k + 1) % 6]
        for j in range(per):
            pts.append(a + (b - a) * (j / per))
    pts = np.array(pts)
    # rotate the hex ring so its point 0 has the angle of the circle's point 0
    ang0 = math.atan2(V[top_idx[0], 1], V[top_idx[0], 0])
    angs = np.arctan2(pts[:, 1], pts[:, 0])
    k0 = int(np.argmin(np.abs(((angs - ang0) + math.pi) % (2 * math.pi) - math.pi)))
    pts = np.roll(pts, -k0, axis=0)
    h_top = m.add_verts(np.c_[pts, np.full(len(pts), z_top)])
    h_bot = m.add_verts(np.c_[pts, np.full(len(pts), z_top - depth)])
    cone = (s_af / 2.0) / math.tan(math.radians(drill_deg / 2.0))
    tip = m.add_verts([(0.0, 0.0, z_top - depth - cone)])[0]
    n = len(pts)
    for k in range(n):
        k2 = (k + 1) % n
        m.face((top_idx[k], top_idx[k2], h_top[k2], h_top[k]))          # annulus
        m.face((h_top[k], h_top[k2], h_bot[k2], h_bot[k]))              # socket walls
        m.face((h_bot[k], h_bot[k2], tip))                               # drill point
    return m


def socket_cap(d: float, shank_len: float = 4.0, nseg: int = 36) -> Mesh:
    """ISO 4762 socket head cap screw head: dia 1.5 d, height d, socket 0.8 d across flats (depth 0.5 d), 0.1 d top
    chamfer; the shank below the seat (hidden)."""
    R, H = 0.75 * d, 1.0 * d
    c = _c(0.1 * d, R)
    s, dep = 0.8 * d, 0.5 * d
    r_top = R - c
    prof = [(-shank_len, 0.0), (-shank_len, d / 2.0), (0.0, d / 2.0), (0.0, R), (H - c, R), (H, r_top)]
    return _socket_head(prof, H, r_top, min(s, 1.6 * (r_top - MIN_FEATURE * 3)), dep, nseg)


def button_head(d: float, shank_len: float = 4.0, nseg: int = 36) -> Mesh:
    """ISO 7380-1 button head: dia 1.9 d, height 0.55 d (M5: dk 9.5, k 2.75, s 3, t 1.56), a domed top to a flat round
    the 0.6 d socket (depth 0.35 d)."""
    R, H = 0.95 * d, 0.55 * d
    s, dep = 0.6 * d, 0.35 * d
    r_flat = s / math.sqrt(3.0) + max(MIN_FEATURE * 3, 0.06 * d)
    edge = max(MIN_FEATURE, 0.08 * H)
    nr = _lod.count(5, 2)
    prof = [(-shank_len, 0.0), (-shank_len, d / 2.0), (0.0, d / 2.0), (0.0, R), (edge, R)]
    for j in range(1, nr + 1):
        u = j / nr
        rr = R + (r_flat - R) * u
        z = edge + (H - edge) * math.sin(u * math.pi / 2.0)
        prof.append((z, rr))
    return _socket_head(prof, H, r_flat, s, dep, nseg)


def countersunk(d: float, shank_len: float = 4.0, proud: float = 0.0, nseg: int = 36) -> Mesh:
    """ISO 10642 countersunk head: 90 deg cone, head dia 2 d, top flush with the seat (``proud`` up), socket 0.6 d."""
    R = 1.0 * d
    hcone = R - d / 2.0
    c = _c(0.2, R)                                       # the land at the rim (>= 2 x the 0.1 mm strip rule)
    s, dep = 0.6 * d, 0.4 * d
    prof = [(-shank_len, 0.0), (-shank_len, d / 2.0), (-hcone + proud, d / 2.0), (proud - c, R - c), (proud, R - c)]
    return _socket_head(prof, proud, R - c, s, dep, nseg)
