#!/usr/bin/env python
"""props_lib.blackhat_geom - SM_BlackHat's geometry, built the way the hat is made.

numpy (+ mathutils.geometry for the tails' constrained triangulation).  Millimetres, the
blackhat_spec frame (+Z up, +X forward, knot on +Y, z = 0 at the rim-tube bottom).

    skin      the woven skin: an OUTER and an INNER straight cone surface 1.8 mm apart, one
              patch per rib bay (its seams lie under the ribs), UV'd in each bay's CONE
              DEVELOPMENT (strand space: a circumferential strand is an arc of constant slant,
              zero stretch); the inner surface at half texel density (never in the reference)
    ribs      13 round rods lying ON the outer skin along its generators (0.4 d centre lift:
              relief 0.9 d); rope twist is texture + normal
    cap       the crown cap: a flat 21 deg conical lid and a hard rolled lip overhanging the skin
    rim       the rolled rim tube (torus) the skin runs into, and the binding cord on its top
    lashings  26 x 3 wraps: each lashing a sleeve of three round cords looped round the tube,
              the cord and the skin edge (reaching 4.5 mm onto the skin)
    band      one turn of cloth round the cone at rho 0.365, lying over the ribs: a twisted
              roll round the back and the front-left, fanning to 0.14 R with folds into the knot
    knot      a gathered lump at theta 61, rho 0.43 on the band's lower edge
    tails     two ribbons (1.2 mm thick) from the knot down the cone (A over B), over the rim
              and hanging, each ending in a long diagonal tear with ragged teeth (B: a notch
              splitting a sliver)

Every part is emitted into a MeshBuilder: a 1 nm position-keyed vertex factory (coincident
positions become ONE vertex), per-corner LOCAL coordinates (mm, in the part's own strand /
tape space) tagged with a UV MEMBER, per-corner normals and a material slot (0 straw, 1 cloth).
blackhat_atlas packs the members and turns local coordinates into UV0; blackhat_paint paints
each member's texels from the SAME local coordinates.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .blackhat_spec import BLACK_HAT, BlackHatSpec, PSI_DEG, lashing_azimuths

D2R = math.pi / 180.0
SIN_A = math.sin(26.0 * D2R)
COS_A = math.cos(26.0 * D2R)


# =========================================================================== frame helpers
def phi_of(theta_deg):
    return (np.asarray(theta_deg, np.float64) + PSI_DEG) * D2R


def rhat(theta_deg):
    p = phi_of(theta_deg)
    return np.stack([np.cos(p), np.sin(p), np.zeros_like(p)], -1)


def that(theta_deg):
    p = phi_of(theta_deg)
    return np.stack([-np.sin(p), np.cos(p), np.zeros_like(p)], -1)


ZHAT = np.array([0.0, 0.0, 1.0])


def cone_n(theta_deg):
    return rhat(theta_deg) * SIN_A + ZHAT * COS_A


def cone_g(theta_deg):
    """Generator direction, apex -> rim (down and out)."""
    return rhat(theta_deg) * COS_A - ZHAT * SIN_A


class Hat:
    """The analytic hat the parts are placed on (all mm)."""

    def __init__(self, spec: BlackHatSpec = BLACK_HAT):
        self.s = spec
        self.R = spec.R
        self.Za = spec.apex_z
        self.rt = spec.rt
        self.Rc = spec.rim_centre_radius
        self.zc = spec.tube_centre_z
        self.t_skin = spec.skin_thickness_R * spec.R
        self.ribs = np.array(spec.ribs.all_deg, np.float64)
        self.d_rib = spec.ribs.diameter_R * spec.R
        self.r_rib = 0.5 * self.d_rib
        self.h_rib = spec.ribs.centre_lift_d * self.d_rib            # rod centre above the skin
        self.h_rib_top = self.h_rib + self.r_rib
        self.r_cord = 0.5 * spec.rim.cord_diameter_R * spec.R
        ac = spec.rim.cord_angle_deg * D2R
        dc = self.rt + 0.8 * self.r_cord
        self.cord_rc = self.Rc + dc * math.cos(ac)                    # binding cord centre (r, z)
        self.cord_zc = self.zc + dc * math.sin(ac)
        self.rw = 0.5 * spec.rim.wrap_cord_R * spec.R                  # lashing wrap cord radius

    # ------------------------------------------------------------ the skin cone
    def s_of_r(self, r):
        return np.asarray(r, np.float64) / COS_A

    def cone_point(self, s, theta, h=0.0):
        """Outer skin point at slant s (mm from the virtual apex), azimuth theta, lifted h
        along the outward normal."""
        s = np.asarray(s, np.float64)
        h = np.asarray(h, np.float64)
        th = np.asarray(theta, np.float64)
        r = s * COS_A + h * SIN_A
        z = self.Za - s * SIN_A + h * COS_A
        p = phi_of(th)
        return np.stack([r * np.cos(p), r * np.sin(p), z + 0.0 * r], -1)

    def skin_z(self, r):
        return self.Za - np.asarray(r, np.float64) * self.s.tan_slope

    # ------------------------------------------------------------ cloth rest height
    def bracket(self, theta):
        th = (np.asarray(theta, np.float64) - self.ribs[0]) % 360.0 + self.ribs[0]
        ribs = np.concatenate([self.ribs, [self.ribs[0] + 360.0]])
        k = np.clip(np.searchsorted(ribs, th, side="right") - 1, 0, len(self.ribs) - 1)
        return th, ribs[k], ribs[k + 1]

    def rest_height(self, theta, s):
        """Normal height above the analytic skin at which cloth lying ACROSS the ribs rests:
        straight (taut) between rib tops, never below 0.25 mm."""
        th, a, b = self.bracket(theta)
        half = 0.5 * (b - a) * D2R
        dev = (th - 0.5 * (a + b)) * D2R
        r = np.asarray(s, np.float64) * COS_A
        sag = r * (1.0 - np.cos(half) / np.cos(dev)) * SIN_A
        return np.maximum(0.25, self.h_rib_top - sag)


# =========================================================================== the builder
@dataclass
class Member:
    """One UV island member: a part patch with its own local 2D coordinates (mm)."""
    key: str
    atlas: str                     # "straw" | "cloth"
    kind: str                      # "wedge" | "rect" | "disc"
    info: Dict[str, object] = field(default_factory=dict)
    density: float = 1.0           # texel density multiplier (inner skin 0.5)
    flip: float = 1.0              # local y sign applied (handedness fix)
    lo: Optional[np.ndarray] = None
    hi: Optional[np.ndarray] = None
    outline: Optional[np.ndarray] = None   # local 2D outline points for packing (after flip)

    def extend(self, L):
        L = np.asarray(L, np.float64).reshape(-1, 2)
        lo, hi = L.min(0), L.max(0)
        self.lo = lo if self.lo is None else np.minimum(self.lo, lo)
        self.hi = hi if self.hi is None else np.maximum(self.hi, hi)


class MeshBuilder:
    def __init__(self):
        self._key: Dict[Tuple[int, int, int], int] = {}
        self.P: List[Tuple[float, float, float]] = []
        self.F: List[Tuple[int, ...]] = []
        self.FL: List[np.ndarray] = []       # per-corner local coords
        self.FN: List[np.ndarray] = []       # per-corner normals
        self.FM: List[str] = []              # member key
        self.FS: List[int] = []              # material slot
        self.members: Dict[str, Member] = {}
        self.part_of_face: List[str] = []
        self.parts: Dict[str, List[int]] = {}

    def vid(self, p) -> int:
        k = (int(round(p[0] * 1e6)), int(round(p[1] * 1e6)), int(round(p[2] * 1e6)))   # 1 nm keys
        i = self._key.get(k)
        if i is None:
            i = len(self.P)
            self._key[k] = i
            self.P.append((k[0] * 1e-6, k[1] * 1e-6, k[2] * 1e-6))
        return i

    def member(self, key, atlas, kind, density=1.0, **info) -> Member:
        m = self.members.get(key)
        if m is None:
            m = Member(key, atlas, kind, dict(info), density)
            self.members[key] = m
        return m

    def face(self, pts, locs, nrms, member: str, slot: int, part: str):
        idx = [self.vid(p) for p in pts]
        keep = []
        for j, i in enumerate(idx):
            if i not in [idx[k] for k in keep]:
                keep.append(j)
        if len(keep) < 3:
            return
        idx = [idx[j] for j in keep]
        P = np.array([self.P[i] for i in idx])
        a = np.cross(P[1] - P[0], P[2] - P[0])
        if len(idx) == 4:
            a = a + np.cross(P[2] - P[0], P[3] - P[0])
        if np.linalg.norm(a) < 1e-7:            # zero-area (mm^2 x 2) - drop
            return
        self.F.append(tuple(idx))
        self.FL.append(np.asarray([locs[j] for j in keep], np.float64))
        self.FN.append(np.asarray([nrms[j] for j in keep], np.float64))
        self.FM.append(member)
        self.FS.append(slot)
        self.parts.setdefault(part, []).append(len(self.F) - 1)
        self.members[member].extend(self.FL[-1])

    def grid(self, P, N, L, member: str, slot: int, part: str, wrap: bool = False, outward=None):
        """Quads over a (n, m) grid.  ``wrap`` closes the m direction.  Faces are wound so their
        normal agrees with N (per corner)."""
        P = np.asarray(P, np.float64)
        N = np.asarray(N, np.float64)
        L = np.asarray(L, np.float64)
        n, m = P.shape[:2]
        mm = m if wrap else m - 1
        for i in range(n - 1):
            for j in range(mm):
                j1 = (j + 1) % m
                c = [(i, j), (i + 1, j), (i + 1, j1), (i, j1)]
                pts = [P[a, b] for a, b in c]
                nr = [N[a, b] for a, b in c]
                lc = [L[a, b] for a, b in c]
                if wrap and j1 == 0:
                    lc = [L[i, j], L[i + 1, j], L[i + 1, m] if L.shape[1] > m else L[i + 1, j1],
                          L[i, m] if L.shape[1] > m else L[i, j1]]
                fn = np.cross(pts[1] - pts[0], pts[2] - pts[0]) + np.cross(pts[2] - pts[0], pts[3] - pts[0])
                if float(fn @ np.mean(nr, 0)) < 0:
                    pts, nr, lc = pts[::-1], nr[::-1], lc[::-1]
                self.face(pts, lc, nr, member, slot, part)

    # ---------------------------------------------------------------- output
    def arrays(self):
        return np.asarray(self.P, np.float64), self.F

    def triangles(self) -> int:
        return int(sum(len(f) - 2 for f in self.F))


def grid_normals(P, wrap=False, flip=False):
    """Smooth vertex normals of a (n, m) grid by central differences."""
    P = np.asarray(P, np.float64)
    if wrap:
        dj = np.roll(P, -1, 1) - np.roll(P, 1, 1)
    else:
        dj = np.gradient(P, axis=1)
    di = np.gradient(P, axis=0)
    n = np.cross(di, dj)
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
    return -n if flip else n


# =========================================================================== LOD tessellation
@dataclass(frozen=True)
class Lod:
    skin_seg_deg: float
    skin_rho: Tuple[float, ...]
    inner_seg_deg: float
    inner_rho: Tuple[float, ...]
    rib_sides: int
    rib_rings: int
    cap_around: int
    cap_lid_rings: Tuple[float, ...]
    cap_lip: bool
    tube_around: int
    tube_sides: int
    cord_sides: int                 # 0 = no binding cord
    lash_path: int
    lash_profile: str               # "wraps" | "sleeve" | "band"
    band_step_fan: float
    band_step_roll: float
    band_prof: int
    knot_grid: Tuple[int, int]
    tail_du: float
    tail_cols: int
    tail_teeth: bool


LODS = {
    0: Lod(5.0, (0.08, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, None), 7.0, (0.0, 0.2, 0.5, 0.8, None),
           8, 3, 64, (0.12, 0.25, 0.45, 0.7, 1.0), True, 120, 10, 4, 12, "wraps", 2.0, 5.0, 14, (36, 10), 10.0, 3, True),
    1: Lod(9.3, (0.08, 0.35, 0.65, None), 14.0, (0.0, 0.5, None),
           5, 2, 32, (0.4, 0.75, 1.0), True, 96, 6, 3, 8, "sleeve", 3.5, 9.0, 8, (12, 6), 22.0, 2, True),
    2: Lod(14.0, (0.08, None), 28.0, (0.0, None),
           3, 2, 16, (1.0,), False, 48, 4, 0, 5, "band", 7.0, 18.0, 5, (8, 4), 45.0, 1, False),
}


# =========================================================================== parts
def _bay_thetas(a, b, seg):
    n = max(1, int(math.ceil((b - a) / seg - 1e-9)))
    return np.linspace(a, b, n + 1)


def build_skin(hat: Hat, mb: MeshBuilder, lod: Lod):
    s_top = hat.s_of_r(0.08 * hat.R)
    s_bot = hat.s_of_r(hat.Rc)
    ribs = list(hat.ribs) + [hat.ribs[0] + 360.0]
    rho = [r if r is not None else hat.Rc / hat.R for r in lod.skin_rho]
    rho_in = [r if r is not None else hat.Rc / hat.R for r in lod.inner_rho]
    s_in_off = hat.t_skin * math.tan(26.0 * D2R)          # inner slant = outer slant - t tan(slope)
    inner_apex = np.array([0.0, 0.0, hat.Za - hat.t_skin / COS_A])
    for k in range(len(hat.ribs)):
        a, b = ribs[k], ribs[k + 1]
        mid = 0.5 * (a + b)
        # ---- outer
        th = _bay_thetas(a, b, lod.skin_seg_deg)
        ss = np.array([hat.s_of_r(r * hat.R) for r in rho])
        ss[0], ss[-1] = s_top, s_bot
        S, T = np.meshgrid(ss, th, indexing="ij")
        P = hat.cone_point(S, T)
        N = np.broadcast_to(cone_n(T), P.shape).copy()
        psi = (T - mid) * D2R * COS_A
        L = np.stack([S * np.cos(psi), S * np.sin(psi)], -1)
        key = f"skin_out_{k:02d}"
        mb.member(key, "straw", "wedge", theta_a=a, theta_b=b, theta_mid=mid, s0=float(ss[0]), s1=float(ss[-1]),
                  surface="outer", bay=k)
        mb.grid(P, N, L, key, 0, "skin_outer")
        # ---- inner (the underside; half texel density)
        th = _bay_thetas(a, b, lod.inner_seg_deg)
        s_in = np.array([r * hat.R / COS_A for r in rho_in]) - np.where(np.array(rho_in) > 0, s_in_off, 0.0)
        s_in[-1] = hat.s_of_r(hat.Rc) - s_in_off
        S, T = np.meshgrid(s_in, th, indexing="ij")
        P = inner_apex + S[..., None] * cone_g(T)
        N = -np.broadcast_to(cone_n(T), P.shape)
        psi = (T - mid) * D2R * COS_A
        L = np.stack([S * np.cos(psi), S * np.sin(psi)], -1)
        key = f"skin_in_{k:02d}"
        mb.member(key, "straw", "wedge", density=0.4, theta_a=a, theta_b=b, theta_mid=mid, s0=0.0,
                  s1=float(s_in[-1]), surface="inner", bay=k)
        mb.grid(P, N, L, key, 0, "skin_inner")


def build_ribs(hat: Hat, mb: MeshBuilder, lod: Lod):
    s0 = hat.s_of_r(0.08 * hat.R)
    s1 = hat.s_of_r(hat.Rc - 0.25 * hat.rt)
    ss = np.linspace(s0, s1, lod.rib_rings)
    n = lod.rib_sides
    # section angle a from the bottom (-90 deg) round through the top; the seam faces the skin
    aa = -0.5 * math.pi + np.arange(n + 1) * 2 * math.pi / n
    for i, th in enumerate(hat.ribs):
        t, nn = that(th), cone_n(th)
        S, A = np.meshgrid(ss, aa, indexing="ij")
        ax = hat.cone_point(S, th, hat.h_rib)
        dirs = np.cos(A)[..., None] * t + np.sin(A)[..., None] * nn
        P = ax + hat.r_rib * dirs
        L = np.stack([S - s0, (A + 0.5 * math.pi) * hat.r_rib], -1)
        key = f"rib_{i:02d}"
        mb.member(key, "straw", "rect", part="rib", theta=float(th), s0=float(s0), r=hat.r_rib)
        mb.grid(P[:, :-1], dirs[:, :-1], L, key, 0, "ribs", wrap=True)


def _revolve(hat: Hat, mb: MeshBuilder, prof_rz, prof_n, prof_len, around: int, key_fn, slot, part,
             theta0: float, local_fn):
    """Surface of revolution about Z from a profile [(r, z)] with normals [(nr, nz)]."""
    th = theta0 + np.linspace(0.0, 360.0, around + 1)
    prof_rz = np.asarray(prof_rz, np.float64)
    prof_n = np.asarray(prof_n, np.float64)
    R_, T = np.meshgrid(prof_rz[:, 0], th, indexing="ij")
    Z = np.broadcast_to(prof_rz[:, 1:2], R_.shape)
    rh = rhat(T)
    P = R_[..., None] * rh + Z[..., None] * ZHAT
    N = prof_n[:, 0:1, None] * rh + prof_n[:, 1:2, None] * ZHAT
    L = local_fn(np.broadcast_to(np.asarray(prof_len)[:, None], R_.shape), T, R_)
    mb.grid(P[:, :-1], N[:, :-1], L, key_fn, slot, part, wrap=True)


#: surface pass: the crown cap is a distinct FLAT conical lid with a hard lipped edge standing proud
#: of the cone (round 1's spherical dome steepened at its edge and blended into the cone)
CAP_LID_SLOPE_DEG = 21.0           # REFERENCE_SPEC 3: "a low conical lid, slope about 20 deg" (+-5)
CAP_TOP_ROUND_MM = 7.0             # the lid's top rounds over this radius (the reference's crown is not a point)


def cap_lid(hat: Hat):
    """The lid: a straight cone of CAP_LID_SLOPE_DEG from the fitted crown top to the cap radius;
    its edge then stands (15.4 - 12.1) = 3.3 mm above the skin, inside REFERENCE_SPEC 3's lip
    band (0.004 - 0.012 R = 1.2 - 3.6 mm)."""
    c = hat.s.cap
    rc = c.radius_R * hat.R
    z_top = hat.Za - c.top_below_apex_R * hat.R
    z_edge = z_top - math.tan(CAP_LID_SLOPE_DEG * D2R) * (math.hypot(rc, CAP_TOP_ROUND_MM) - CAP_TOP_ROUND_MM)
    return rc, z_top, z_edge, CAP_LID_SLOPE_DEG


def build_cap(hat: Hat, mb: MeshBuilder, lod: Lod):
    rc, z_top, z_edge, slope = cap_lid(hat)
    ta = math.tan(slope * D2R)
    rs = np.array([0.0] + [f * rc for f in lod.cap_lid_rings])
    # the top is gently rounded over ~7 mm (a hyperbola: no point, no finial), the crown top height kept
    r0 = CAP_TOP_ROUND_MM
    zz = z_top - ta * (np.sqrt(rs * rs + r0 * r0) - r0)
    prof = np.stack([rs, zz], -1)
    dz = ta * rs / np.sqrt(rs * rs + r0 * r0)
    nrm = np.stack([dz, np.ones_like(dz)], -1)
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    th0 = 180.0                                    # the seam faces the back
    s_max = rc / math.cos(slope * D2R)
    mb.member("cap_lid", "straw", "disc", part="cap_lid", rc=rc, slope_deg=slope, theta0=th0, s_max=s_max)

    def lid_local(slen, T, R_):
        sl = R_ / math.cos(slope * D2R)                          # slant from the top
        psi = (T - th0 - 180.0) * D2R
        return np.stack([sl * np.cos(psi), sl * np.sin(psi)], -1)
    _revolve(hat, mb, prof, nrm, np.zeros(len(prof)), lod.cap_around, "cap_lid", 0, "cap", th0, lid_local)
    if lod.cap_lip:
        # the hard lip: a thick rolled edge dropping from the lid's rim (a HARD crease: the lid and
        # the lip do not share normals), overhanging the skin, with a dark undercut beneath it
        # (the reference's black line under the lip)
        r_in = rc - 1.4
        pr = np.array([(rc, z_edge), (rc + 0.9, z_edge - 0.45), (rc + 1.25, z_edge - 1.5), (rc + 0.9, z_edge - 2.45),
                       (rc + 0.1, z_edge - 2.75), (r_in, float(hat.skin_z(r_in)) - 0.4)])
        nr = np.array([(0.55, 0.83), (0.85, 0.52), (1.0, 0.0), (0.6, -0.8), (0.1, -1.0), (-0.3, -0.95)])
        nr /= np.linalg.norm(nr, axis=1, keepdims=True)
        seg = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pr, axis=0), axis=1))])
        mb.member("cap_lip", "straw", "rect", part="cap_lip", rc=rc, theta0=th0)

        def lip_local(slen, T, R_):
            return np.stack([(T - th0) * D2R * rc, slen], -1)
        _revolve(hat, mb, pr, nr, seg, lod.cap_around, "cap_lip", 0, "cap", th0, lip_local)


def _torus(hat: Hat, mb: MeshBuilder, Rc, zc, rt, around, sides, a0_deg, key, part, chunks=8, theta0=-180.0):
    th = theta0 + np.linspace(0.0, 360.0, around + 1)
    aa = (a0_deg + np.linspace(0.0, 360.0, sides + 1)) * D2R
    per = around // chunks
    for c in range(chunks):
        tt = th[c * per:(c + 1) * per + 1] if c < chunks - 1 else th[c * per:]
        T, A = np.meshgrid(tt, aa, indexing="ij")
        rh = rhat(T)
        dirs = np.cos(A)[..., None] * rh + np.sin(A)[..., None] * ZHAT
        P = (Rc * rh + zc * ZHAT) + rt * dirs
        L = np.stack([(T - tt[0]) * D2R * Rc, (A - aa[0]) * rt], -1)
        k = f"{key}_{c}"
        mb.member(k, "straw", "rect", part=key, theta_a=float(tt[0]), theta_b=float(tt[-1]), Rc=Rc, rt=rt,
                  a0=a0_deg)
        mb.grid(P[:, :-1], dirs[:, :-1], L, k, 0, part, wrap=True)


def build_rim(hat: Hat, mb: MeshBuilder, lod: Lod):
    _torus(hat, mb, hat.Rc, hat.zc, hat.rt, lod.tube_around, lod.tube_sides, 225.0, "tube", "rim_tube")
    if lod.cord_sides:
        _torus(hat, mb, hat.cord_rc, hat.cord_zc, hat.r_cord, lod.tube_around, lod.cord_sides, 225.0, "cord",
               "rim_cord")


# ---------------------------------------------------------------- lashings
def lashing_body_points(hat: Hat):
    """(r, z) points of what a lashing loops round: tube, binding cord and the skin edge."""
    a = np.linspace(0, 2 * math.pi, 96, endpoint=False)
    tube = np.stack([hat.Rc + hat.rt * np.cos(a), hat.zc + hat.rt * np.sin(a)], -1)
    b = np.linspace(0, 2 * math.pi, 24, endpoint=False)
    cord = np.stack([hat.cord_rc + hat.r_cord * np.cos(b), hat.cord_zc + hat.r_cord * np.sin(b)], -1)
    reach = hat.s.rim.lashing_skin_reach_R * hat.R
    r0 = hat.Rc - hat.rt
    rr = np.linspace(r0 - reach, r0, 6)
    top = np.stack([rr, hat.skin_z(rr)], -1)
    bot = np.stack([rr, hat.skin_z(rr) - hat.t_skin / COS_A], -1)
    return np.concatenate([tube, cord, top, bot])


def lashing_path(hat: Hat, n: int):
    """Support points B(beta) of the body and the outward unit u(beta), n directions; the
    first direction points straight down (the seam under the tube)."""
    pts = lashing_body_points(hat)
    beta = -0.5 * math.pi + np.arange(n) * 2 * math.pi / n
    U = np.stack([np.cos(beta), np.sin(beta)], -1)
    proj = pts @ U.T
    B = pts[np.argmax(proj, axis=0)]
    return B, U


WRAP_PROFILES = {
    # (w / rw, h / rw): across the lashing (w along the rim), height above the body along u
    # surface pass: the valleys between the three cords go deeper (0.55 -> 0.30 rw) so the wraps read
    # as separate round cords, not one ribbed strap
    "wraps": [(-3.15, 0.04), (-2.9, 0.35), (-2.0, 1.0), (-1.0, 0.30), (0.0, 1.0), (1.0, 0.30), (2.0, 1.0),
              (2.9, 0.35), (3.15, 0.04)],
    "sleeve": [(-3.15, 0.04), (-2.8, 0.6), (0.0, 0.95), (2.8, 0.6), (3.15, 0.04)],
    "band": [(-3.1, 0.04), (-2.6, 0.75), (2.6, 0.75), (3.1, 0.04)],
}


def wrap_profile(kind: str, rw: float):
    pr = np.array(WRAP_PROFILES[kind], np.float64) * rw
    seg = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pr, axis=0), axis=1))])
    # smooth normals in the (w, h) plane: from the three round cords where that is defined
    nrm = []
    for w, h in pr:
        if kind == "wraps" and h > 0.3 * rw:
            k = min((-2 * rw, 0.0, 2 * rw), key=lambda c: abs(w - c))
            v = np.array([w - k, h - 0.1 * rw])
            if abs(h - rw * 0.30) < 1e-6:
                v = np.array([0.0, 1.0])
        elif h <= 0.1 * rw:
            v = np.array([np.sign(w), 0.2])
        else:
            v = np.array([0.35 * np.sign(w) * (abs(w) > 2.5 * rw), 1.0])
        nrm.append(v / np.linalg.norm(v))
    return pr, np.array(nrm), seg


LASH_REF_PATH = 12


def lashing_local_maps(hat: Hat):
    """LOD-independent local coordinates of a lashing sleeve: x(beta) = arc length along LOD0's
    wrap centre line, y(w) = arc length across LOD0's three-cord profile.  Every LOD samples the
    same texels at the same place on the loop."""
    B, U = lashing_path(hat, LASH_REF_PATH)
    C = B + hat.rw * U
    Cc = np.concatenate([C, C[:1]])
    xs = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(Cc, axis=0), axis=1))])
    beta = -0.5 * math.pi + np.arange(LASH_REF_PATH + 1) * 2 * math.pi / LASH_REF_PATH
    prof, _pn, seg = wrap_profile("wraps", hat.rw)
    return (lambda b: np.interp(b, beta, xs)), (lambda w: np.interp(w, prof[:, 0], seg)), float(xs[-1]), float(seg[-1])


def build_lashings(hat: Hat, mb: MeshBuilder, lod: Lod):
    B, U = lashing_path(hat, lod.lash_path)
    rw = hat.rw
    prof, pn, seg = wrap_profile(lod.lash_profile, rw)
    x_of_beta, y_of_w, path_len, prof_len = lashing_local_maps(hat)
    beta = -0.5 * math.pi + np.arange(lod.lash_path + 1) * 2 * math.pi / lod.lash_path
    for i, (th, kind) in enumerate(lashing_azimuths(hat.s)):
        # surface pass: hand-tied, not neat: each lashing leans and wanders a little round its loop
        # (up to 0.5 rw either way), the same at every LOD
        lr = np.random.default_rng(4711 + i)
        lean, ph0 = lr.uniform(-0.5, 0.5) * rw, lr.uniform(0.0, 2 * math.pi)
        pts = np.zeros((lod.lash_path + 1, len(prof), 3))
        nrm = np.zeros_like(pts)
        loc = np.zeros((lod.lash_path + 1, len(prof), 2))
        for j in range(lod.lash_path + 1):
            jj = j % lod.lash_path
            b, u = B[jj], U[jj]
            for k, ((w, h), (nw, nh)) in enumerate(zip(prof, pn)):
                rz = b + u * h
                ang = th + ((w + lean * math.sin(beta[j] + ph0)) / max(rz[0], 1.0)) / D2R
                rh = rhat(ang)
                pts[j, k] = rz[0] * rh + rz[1] * ZHAT
                nrm[j, k] = nh * (u[0] * rh + u[1] * ZHAT) + nw * that(ang)
                nrm[j, k] /= np.linalg.norm(nrm[j, k])
                loc[j, k] = (float(x_of_beta(beta[j])), float(y_of_w(w)))
        key = f"lash_{i:02d}"
        mb.member(key, "straw", "rect", part="lashing", theta=float(th), lkind=kind, rw=rw, path_len=path_len,
                  prof_len=prof_len)
        mb.grid(pts, nrm, loc, key, 0, "lashings")


# ---------------------------------------------------------------- band
def _interp(tab, x):
    xs, ys = zip(*tab)
    return np.interp(x, xs, ys)


#: the band on the unwrapped azimuth theta' (64 -> 418 = 58 + 360): width (x R, slant), the upper
#: edge rho, roundness (1 = twisted roll), fold amplitude (mm) - REFERENCE_SPEC 7
BAND_W = [(62.0, 0.060), (66.0, 0.042), (72.0, 0.024), (82.0, 0.013), (95.0, 0.011), (330.0, 0.011),
          (340.0, 0.012), (350.0, 0.022), (360.0, 0.040), (375.0, 0.075), (390.0, 0.110), (405.0, 0.130),
          (414.0, 0.140), (419.0, 0.140)]
BAND_RU = [(62.0, 0.380), (70.0, 0.362), (80.0, 0.3595), (330.0, 0.3595), (360.0, 0.347), (390.0, 0.350),
           (405.0, 0.360), (419.0, 0.372)]
BAND_FOLD = [(62.0, 1.0), (70.0, 0.0), (368.0, 0.0), (390.0, 1.0), (405.0, 1.7), (419.0, 2.0)]
#: gathered cloth near the knot: extra section thickness (mm) - the fanned band reads as a soft,
#: bunched roll in the reference, not a flat strip
BAND_PUFF = [(62.0, 2.0), (72.0, 0.0), (368.0, 0.0), (385.0, 1.2), (400.0, 2.5), (412.0, 3.2), (419.0, 3.5)]


def band_section(hat: Hat, thp):
    w = _interp(BAND_W, thp) * hat.R
    ru = _interp(BAND_RU, thp)
    s_u = ru * hat.R / COS_A
    q = np.clip((0.040 * hat.R - w) / ((0.040 - 0.016) * hat.R), 0.0, 1.0)
    fold = _interp(BAND_FOLD, thp)
    puff = _interp(BAND_PUFF, thp)
    # gathered into a soft, rounded bundle toward the knot (the reference's fanned band reads as a
    # thick roll with folds along it, not a flat strip)
    q = np.maximum(q, 0.45 * np.clip(puff / 3.5, 0.0, 1.0))
    return w, s_u + 0.5 * w, q, fold, puff


BAND_T0, BAND_T1 = 62.0, 419.0


def band_profile(hat: Hat, tp: float, tau):
    """The band's cross-section at unwrapped azimuth tp: (x across the slant, y along the
    normal) for profile parameters tau (tau = -pi/2 is the bottom-centre seam), and the
    section's centre slant and lift base."""
    t = hat.s.band.thickness_R * hat.R
    w, sc, q, fold, puff = band_section(hat, tp)
    p = 2.0 + (1.0 - q) * (4.0 - 2.0 * min(1.0, puff / 3.0))
    a = 0.5 * w
    b = (1.0 - q) * (0.5 * t + 0.5 * puff) + q * min(0.5 * w, 0.5 * t + 0.5 * puff + 0.5 * t)
    ct, st = np.cos(tau), np.sin(tau)
    x = a * np.sign(ct) * np.abs(ct) ** (2.0 / p)
    y = b * np.sign(st) * np.abs(st) ** (2.0 / p)
    nf = 3.0
    y = y + fold * np.sin(math.pi * nf * (x / max(a, 1e-6) + 1.0) * 0.5) * (1.0 - (x / max(a, 1e-6)) ** 4)
    return x, y, sc, b + fold + 0.15


_BAND_REF = {}


def band_reference(hat: Hat):
    """LOD-independent band coordinates: x(theta') the arc length of the centre line sampled
    finely, y(theta', tau) the arc length round a fine section, and the chunk boundaries."""
    key = id(hat.s)
    if key in _BAND_REF:
        return _BAND_REF[key]
    th = np.arange(BAND_T0, BAND_T1 + 1e-9, 0.25)
    cen = []
    for tp in th:
        x, y, sc, base = band_profile(hat, tp, np.array([0.0]))
        cen.append(hat.cone_point(sc, tp, hat.rest_height(tp, sc) + base))
    cen = np.array(cen)
    xs = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(cen, axis=0), axis=1))])
    bounds = [BAND_T0]
    last = 0.0
    for i in range(1, len(th)):
        brk = (th[i - 1] < 80.0 <= th[i]) or (th[i - 1] < 345.0 <= th[i])
        if xs[i] - last > 190.0 or brk:
            bounds.append(float(th[i]))
            last = xs[i]
    if bounds[-1] < BAND_T1:
        bounds.append(BAND_T1)
    tau_f = -0.5 * math.pi + np.linspace(0.0, 2 * math.pi, 257)

    def x_of(tp):
        return np.interp(tp, th, xs)

    def y_of(tp, tau):
        x, y, _sc, _b = band_profile(hat, tp, tau_f)
        arc = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
        return np.interp(tau, tau_f, arc)
    ref = (x_of, y_of, bounds)
    _BAND_REF[key] = ref
    return ref


def build_band(hat: Hat, mb: MeshBuilder, lod: Lod):
    x_of, y_of, bounds = band_reference(hat)
    # sections: fine where it fans, coarse on the roll; every chunk boundary is a section
    th = [BAND_T0]
    while th[-1] < BAND_T1:
        step = lod.band_step_fan if (th[-1] < 80.0 or th[-1] > 345.0) else lod.band_step_roll
        th.append(min(BAND_T1, th[-1] + step))
    th = np.unique(np.round(np.concatenate([th, bounds]), 6))
    npf = lod.band_prof
    tau = -0.5 * math.pi + np.arange(npf + 1) * 2 * math.pi / npf
    secs, Ls = [], []
    for tp in th:
        x, y, sc, base = band_profile(hat, tp, tau)
        s_pt = sc + x
        lift = hat.rest_height(tp, s_pt) + base
        secs.append(hat.cone_point(s_pt, tp, lift + y))
        Ls.append(np.stack([np.full(npf + 1, x_of(tp)), y_of(tp, tau)], -1))
    P = np.array(secs)                                   # (sections, npf + 1, 3)
    L = np.array(Ls)
    N = grid_normals(P[:, :-1], wrap=True)
    cen = P[:, :-1].mean(1, keepdims=True)
    if float(np.sum((P[:, :-1] - cen) * N)) < 0:
        N = -N
    for c in range(len(bounds) - 1):
        i0 = int(np.argmin(np.abs(th - bounds[c])))
        i1 = int(np.argmin(np.abs(th - bounds[c + 1])))
        key = f"band_{c}"
        x0 = float(x_of(bounds[c]))
        mb.member(key, "cloth", "rect", part="band", x0=x0, theta0=float(bounds[c]), theta1=float(bounds[c + 1]))
        Lc = L[i0:i1 + 1].copy()
        Lc[..., 0] -= x0
        mb.grid(P[i0:i1 + 1, :-1], N[i0:i1 + 1], Lc, key, 1, "band", wrap=True)
    return {"sections": int(len(th)), "length_mm": float(x_of(BAND_T1)), "chunks": len(bounds) - 1}


# ---------------------------------------------------------------- knot
#: surface pass: the knot's folds twist round it (radians per radian of the polar angle)
KNOT_TWIST = 0.9


def knot_frame(hat: Hat):
    b = hat.s.band
    th = b.knot_theta
    s = b.knot_rho * hat.R / COS_A
    e1, e2, e3 = that(th), cone_g(th), cone_n(th)
    # the knot sits ON the gathered band (whose bundle is ~8 mm thick there)
    base = hat.cone_point(s, th, hat.rest_height(th, s) + 4.5)
    return base, e1, e2, e3


def build_knot(hat: Hat, mb: MeshBuilder, lod: Lod, seed: int = 11):
    base, e1, e2, e3 = knot_frame(hat)
    sz = hat.s.band.knot_size_R
    a1, a2, a3 = 0.55 * sz[1] * hat.R, 0.55 * sz[0] * hat.R, 0.34 * sz[0] * hat.R   # flatter (surface pass)
    nphi, nb = lod.knot_grid
    ph = np.linspace(0.0, 2 * math.pi, nphi + 1)
    be = np.linspace(0.0, math.pi, nb + 1)
    PH, BE = np.meshgrid(ph, be, indexing="ij")
    # surface pass: deeper, sharper gathered folds (round 1's 0.10 bumps read as a rubbery blob),
    # the two lobes of a square knot, and a stronger crossing wrap
    folds = np.array([0.35, 1.05, 1.75, 2.6, 3.3, 3.9, 4.6, 5.3])
    f = np.zeros_like(PH)
    for k, fp in enumerate(folds):
        d = np.angle(np.exp(1j * (PH - fp - KNOT_TWIST * BE)))          # twisted, not a star from the top
        f += (0.17 + 0.09 * ((k * 5) % 3) / 2.0) * np.exp(-(d / 0.14) ** 2)
    f -= 0.10
    f += 0.10 * np.cos(2.0 * (PH - 0.4))
    sb = np.sin(BE)
    rad = 1.0 + f * sb ** 2.5                  # the folds gather on the knot's sides, the top stays smooth
    x = a1 * rad * sb * np.cos(PH)
    y = a2 * rad * sb * np.sin(PH)
    top = np.cos(BE)
    zc = np.where(top >= 0, a3 * top, 0.45 * a3 * top)
    # the crossing wrap: a raised band across the knot (square-knot bulk)
    wrap = np.exp(-((x - 0.15 * a1) / (0.22 * a1)) ** 2) * sb
    zc = zc + 3.0 * wrap * (top > -0.2)
    z = zc + 0.25 * a3
    P = base + x[..., None] * e1 + y[..., None] * e2 + z[..., None] * e3
    N = grid_normals(P, wrap=False)
    N = np.nan_to_num(N)
    cen = base + 0.25 * a3 * e3
    if float(np.sum((P - cen) * N)) < 0:
        N = -N
    # pole normals (beta = 0): straight up
    N[:, 0] = e3
    rm = 0.5 * (a1 + a2)
    L = np.stack([PH * rm, BE * 0.5 * (rm + a3)], -1)
    mb.member("knot", "cloth", "rect", part="knot", rm=float(rm), rb=float(0.5 * (rm + a3)),
              folds=tuple(float(v) for v in folds))
    mb.grid(P, N, L, "knot", 1, "knot")
    return {"centre": (base + 0.25 * a3 * e3).tolist(), "semi_axes_mm": [a1, a2, a3]}


# ---------------------------------------------------------------- tails
def _dev(s, th):
    psi = np.asarray(th) * D2R * COS_A
    return np.stack([s * np.cos(psi), s * np.sin(psi)], -1)


def _undev(p):
    s = np.hypot(p[..., 0], p[..., 1])
    th = np.arctan2(p[..., 1], p[..., 0]) / (D2R * COS_A)
    return s, th


def resample_polyline(P, step):
    P = np.asarray(P, np.float64)
    d = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    n = max(2, int(math.ceil(d[-1] / step)) + 1)
    u = np.linspace(0.0, d[-1], n)
    return np.stack([np.interp(u, d, P[:, k]) for k in range(P.shape[1])], -1), u


def smooth_polyline(P, it=6, keep_ends=True):
    P = np.asarray(P, np.float64).copy()
    for _ in range(it):
        Q = P.copy()
        Q[1:-1] = 0.25 * P[:-2] + 0.5 * P[1:-1] + 0.25 * P[2:]
        P = Q
    return P


def rmf(C, T, W0):
    """Rotation-minimising frame (Wang et al. double reflection) along the polyline C with
    unit tangents T, starting at W0."""
    W = [W0 - (W0 @ T[0]) * T[0]]
    W[0] = W[0] / np.linalg.norm(W[0])
    for i in range(len(T) - 1):
        v1 = C[i + 1] - C[i]
        c1 = v1 @ v1
        w = W[-1]
        if c1 < 1e-18:
            W.append(w)
            continue
        wl = w - (2.0 / c1) * (v1 @ w) * v1
        tl = T[i] - (2.0 / c1) * (v1 @ T[i]) * v1
        v2 = T[i + 1] - tl
        c2 = v2 @ v2
        wn = wl - (2.0 / c2) * (v2 @ wl) * v2 if c2 > 1e-18 else wl
        wn -= (wn @ T[i + 1]) * T[i + 1]
        W.append(wn / np.linalg.norm(wn))
    return np.array(W)


@dataclass
class TailPath:
    name: str
    C: np.ndarray        # centre line (mm)
    u: np.ndarray        # arc length
    T: np.ndarray
    W: np.ndarray        # width direction
    Nn: np.ndarray       # thickness direction
    width: np.ndarray    # per sample
    u_rim: float
    u_leave: float       # where it leaves the tube
    tip: np.ndarray
    outer_sign: float    # +1: +W is the outer (image-right) edge
    info: Dict[str, object]


def tail_tip_world(hat: Hat, cam, tail, tip_px=None) -> np.ndarray:
    """The centre line's end: the reference camera's ray through ``tip_px`` (default the MEASURED
    tip pixel) at the MEASURED hang below the rim (both REFERENCE_SPEC 8).  The torn end's POINT
    lies on the outer edge, half a width from the centre line: solve_tail_paths moves ``tip_px``
    until that point lands on the measured pixel."""
    px = tail.tip_px if tip_px is None else tip_px
    o, d = cam.ray(px[0], px[1])
    z_tip = cam.z_off_mm - tail.hang_R * hat.R
    t = (z_tip - o[2]) / d[2]
    return o + t * d


def build_tail_path(hat: Hat, tail, cam, other: Optional["TailPath"] = None, step=4.0, tip_px=None) -> TailPath:
    R = hat.R
    t_cl = hat.s.band.thickness_R * R
    # 1. on the cone: straight in the development (a taut ribbon on a cone is a geodesic)
    s_start = 0.455 * R / COS_A
    th_start = 62.0
    s_leave = tail.leave_rho * R / COS_A
    r_rim = hat.Rc - 0.35 * hat.rt
    s_rim = hat.s_of_r(r_rim)
    p0, p1, p2 = _dev(s_start, th_start), _dev(s_leave, tail.leave_theta), _dev(s_rim, tail.rim_theta)
    seg1, _ = resample_polyline(np.array([p0, p1]), step)
    # the last stretch runs straight down the generator, so the ribbon crosses the rim square
    # to it and lies flat on the roll (its width along the rim)
    pr = _dev(s_rim - 0.13 * R, tail.rim_theta)
    seg2, _ = resample_polyline(np.array([p1, pr, p2]), step)
    dev = np.concatenate([seg1, seg2[1:]])
    # the ribbon turns out from under the knot smoothly (in the development plane)
    for _ in range(40):
        d2 = dev.copy()
        d2[1:-1] = 0.25 * dev[:-2] + 0.5 * dev[1:-1] + 0.25 * dev[2:]
        dev = d2
    dev, _ = resample_polyline(dev, step)
    s, th = _undev(dev)
    h = hat.rest_height(th, s) + 0.5 * t_cl + 0.2
    ucum = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(dev, axis=0), axis=1))])
    if tail.stand_off_R > 0:                               # B stands off the cone near the rim
        f = np.clip((ucum - 0.45 * ucum[-1]) / (0.55 * ucum[-1]), 0, 1)
        h = h + tail.stand_off_R * R * np.sin(0.5 * math.pi * f) ** 1.5
    on = hat.cone_point(s, th, h)
    # 2. over the tube (clearing the binding cord and the lashings under it)
    rr = hat.rt + 2.0 * hat.rw + 0.6 + 0.5 * t_cl
    aa = np.linspace(105.0, -35.0, 16) * D2R
    rh, zz = rhat(tail.rim_theta), ZHAT
    over = (hat.Rc + rr * np.cos(aa))[:, None] * rh + (hat.zc + rr * np.sin(aa))[:, None] * zz
    # 3. the free fall to the tip (a cubic from the tube to the measured tip)
    tip = tail_tip_world(hat, cam, tail, tip_px)
    q = over[-1]
    tq = over[-1] - over[-2]
    tq /= np.linalg.norm(tq)
    L = np.linalg.norm(tip - q)
    lean = rhat(tail.rim_theta) * math.tan(8.0 * D2R) - ZHAT
    lean /= np.linalg.norm(lean)
    c1 = q + tq * 0.22 * L
    c2 = tip - lean * 0.55 * L
    tt = np.linspace(0, 1, 40)[1:, None]
    fall = ((1 - tt) ** 3) * q + 3 * ((1 - tt) ** 2) * tt * c1 + 3 * (1 - tt) * tt ** 2 * c2 + tt ** 3 * tip
    P = np.concatenate([on, over[1:], fall])
    # keep the on-cone part exactly on the cone: smooth only the joint and the fall
    n_on = len(on)
    Ps = smooth_polyline(P, it=4)
    Ps[:n_on - 3] = P[:n_on - 3]
    Ps[-1] = tip
    C, u = resample_polyline(Ps, step)
    # A over B near the knot
    if other is not None:
        d = np.min(np.linalg.norm(C[:, None, :] - other.C[None, :, :], axis=2), axis=1)
        wsum = 0.5 * (tail.width_R[0] * R + 0.8 * (other.width[:5].mean()))
        lift = np.clip((wsum + 6.0 - d) / 6.0, 0.0, 1.0) * (t_cl + 0.6)
        lift[u > 0.55 * R] = 0.0
        lift = np.convolve(np.pad(lift, 6, mode="edge"), np.ones(13) / 13, "valid")
        # lift along the cone normal of the local azimuth
        ph = np.arctan2(C[:, 1], C[:, 0]) / D2R - PSI_DEG
        C = C + lift[:, None] * cone_n(ph)
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    ph0 = np.arctan2(C[0, 1], C[0, 0]) / D2R - PSI_DEG
    W0 = np.cross(cone_n(ph0), T[0])
    W = rmf(C, T, W0)
    # the twist (A: 60-90 deg for 0.15 R after the knot)
    if tail.twist_deg:
        u0 = np.linalg.norm(_dev(s_leave, tail.leave_theta) - _dev(s_start, th_start))
        tw = np.interp(u, [0, u0, u0 + tail.twist_len_R * R, u0 + (tail.twist_len_R + 0.07) * R],
                       [0.3, 1.0, 1.0, 0.0]) * tail.twist_deg * D2R
        Nn0 = np.cross(T, W)
        W = np.cos(tw)[:, None] * W + np.sin(tw)[:, None] * Nn0
    # the hanging part hangs FACE-ON to the reference camera (REFERENCE_SPEC 8: B face-on; the
    # measured below-rim widths are full widths); over the rim the ribbon creases along the rim
    view = cam.C[None, :] - C
    view /= np.linalg.norm(view, axis=1, keepdims=True)
    Wf = np.cross(T, view)
    Wf /= np.maximum(np.linalg.norm(Wf, axis=1, keepdims=True), 1e-9)
    Wf *= np.sign(np.sum(Wf * W, axis=1))[:, None]
    u_rim0 = float(u[np.argmin(np.linalg.norm(C - over[0], axis=1))])
    u_lv0 = float(u[np.argmin(np.linalg.norm(C - over[-1], axis=1))])
    # B hangs face-on from the knot, standing off the cone (REFERENCE_SPEC 8); A, once flat, half so
    on_w = 0.25 if tail.stand_off_R > 0 else 0.20
    wt = np.interp(u, [0.0, 0.05 * R, u_rim0 - 0.06 * R, u_rim0, u_lv0, u_lv0 + 0.12 * R, u[-1]],
                   [0.0, on_w, on_w, 0.0, 0.0, 1.0, 1.0])
    W = (1.0 - wt)[:, None] * W + wt[:, None] * Wf
    W -= np.sum(W * T, axis=1)[:, None] * T
    W /= np.linalg.norm(W, axis=1, keepdims=True)
    Nn = np.cross(T, W)
    # width: gathered at the knot, then the measured widths near the knot and below the rim
    u_rim = float(u[np.argmin(np.linalg.norm(C - over[0], axis=1))])
    u_leave = float(u[np.argmin(np.linalg.norm(C - over[-1], axis=1))])
    w0, w1 = tail.width_R[0] * R, tail.width_R[1] * R
    width = np.interp(u, [0.0, 0.04 * R, 0.10 * R, u_rim, u[-1]], [0.70 * w0, 0.92 * w0, w0, 0.5 * (w0 + w1), w1])
    # a ribbon turned off the cone surface lifts so its low edge stays on the cone
    ph = np.arctan2(C[:, 1], C[:, 0]) / D2R - PSI_DEG
    ncone = cone_n(ph)
    tilt = np.abs(np.sum(W * ncone, axis=1))
    oncone = u < u_rim0
    C = C + (oncone * 0.5 * width * tilt)[:, None] * ncone
    # which edge is image-right near the tip
    k = max(0, len(C) - 8)
    xa = cam.project(C[k] + W[k] * 5.0)[0]
    xb = cam.project(C[k] - W[k] * 5.0)[0]
    outer = 1.0 if xa > xb else -1.0
    info = {"length_mm": float(u[-1]), "u_rim_mm": u_rim, "u_leave_tube_mm": u_leave,
            "tip_mm": tip.tolist(), "tip_px_target": list(tail.tip_px), "tip_px_model": cam.project(tip).tolist(),
            "on_cone_mm": float(ucum[-1]), "fall_mm": float(L)}
    return TailPath(tail.name, C, u, T, W, Nn, width, u_rim, u_leave, tip, outer, info)


def pointed_tip(tp: TailPath) -> np.ndarray:
    """The torn end's point: on the OUTER edge at the ribbon's end (tail_outline's tip vertex)."""
    return tp.C[-1] + tp.outer_sign * 0.5 * float(tp.width[-1]) * tp.W[-1]


def solve_tail_paths(hat: Hat, spec, cam, iterations: int = 5):
    """Both tails with their POINTED tips (not their centre lines) on REFERENCE_SPEC 8's measured
    tip pixels.  (Round 1 aimed the centre line at the pixel, which put the point half a width,
    15 - 20 px, to image-right; its gate read only y.)  B first; A is laid over it."""
    out = {}
    other = None
    for t in (spec.tails[1], spec.tails[0]):
        target = np.array(t.tip_px, np.float64)
        px = target.copy()
        for _ in range(iterations):
            tp = build_tail_path(hat, t, cam, other=other, tip_px=tuple(px))
            got = np.asarray(cam.project(pointed_tip(tp)), np.float64)[:2]
            px = px + (target - got)
        tp = build_tail_path(hat, t, cam, other=other, tip_px=tuple(px))
        got = np.asarray(cam.project(pointed_tip(tp)), np.float64)[:2]
        tp.info["tip_px_aim_centre_line"] = [round(float(v), 3) for v in px]
        tp.info["pointed_tip_px_model"] = [round(float(v), 3) for v in got]
        tp.info["pointed_tip_px_error"] = round(float(np.linalg.norm(got - target)), 4)
        tp.info["pointed_tip_mm"] = pointed_tip(tp).tolist()
        out[t.name] = tp
        if other is None:
            other = tp
    return [out[spec.tails[0].name], out[spec.tails[1].name]]


def tail_u_samples(tp: TailPath, du: float, lo: float, hi: float, max_turn_deg: Optional[float] = None) -> np.ndarray:
    """Uniform samples every ``du`` in [lo, hi), subdivided wherever the centre line turns more
    than ``max_turn_deg`` between two samples (the bend over the rim roll and the fall), so a
    coarse LOD keeps the tail's silhouette instead of cutting the bend (round 1's LOD pop).
    Default: 15 deg for the coarse LODs; LOD0's 10 mm step already follows the bend (sagitta
    ~1 mm), so it only splits turns over 60 deg and keeps its triangle count."""
    if max_turn_deg is None:
        max_turn_deg = 60.0 if du <= 10.5 else 15.0
    base = list(np.arange(lo, hi, du))
    if not base:
        return np.zeros(0)
    out = [base[0]]

    def tan_at(u):
        i = int(np.clip(np.searchsorted(tp.u, u), 1, len(tp.u) - 1))
        f = (u - tp.u[i - 1]) / max(tp.u[i] - tp.u[i - 1], 1e-9)
        t = tp.T[i - 1] * (1 - f) + tp.T[i] * f
        return t / max(np.linalg.norm(t), 1e-12)
    for a, b in zip(base[:-1], base[1:]):
        ang = math.degrees(math.acos(float(np.clip(tan_at(a) @ tan_at(b), -1.0, 1.0))))
        n = int(math.ceil(ang / max_turn_deg))
        for k in range(1, n):
            out.append(a + (b - a) * k / n)
        out.append(b)
    return np.array(out)


def _seg_cross(p, q, r, s_):
    d = (q[0] - p[0]) * (s_[1] - r[1]) - (q[1] - p[1]) * (s_[0] - r[0])
    if abs(d) < 1e-12:
        return False
    t = ((r[0] - p[0]) * (s_[1] - r[1]) - (r[1] - p[1]) * (s_[0] - r[0])) / d
    v = ((r[0] - p[0]) * (q[1] - p[1]) - (r[1] - p[1]) * (q[0] - p[0])) / d
    return 1e-9 < t < 1 - 1e-9 and 1e-9 < v < 1 - 1e-9


def _simple(pts) -> bool:
    n = len(pts)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            if _seg_cross(p, q, pts[j], pts[(j + 1) % n]):
                return False
    return True


def edge_wobble(u, seed, u0):
    """Surface pass: a woven ribbon's edge is never a ruled line: +-0.5 mm of slow waviness on the
    hanging part (0 on the cone, where the ribbon lies under the band and knot)."""
    k = np.clip((np.asarray(u, np.float64) - u0) / 30.0, 0.0, 1.0)
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * math.pi, 3)
    return k * (0.30 * np.sin(u / 23.0 + ph[0]) + 0.18 * np.sin(u / 9.0 + ph[1]) + 0.08 * np.sin(u / 3.7 + ph[2]))


def tail_outline(tp: TailPath, tail, R: float, teeth: bool, seed: int = 5, du: float = 10.0):
    """See _tail_outline; falls back to fewer tatters / nicks if a random draw self-intersects."""
    for tat, nick in ((True, True), (True, False), (False, False)):
        try:
            return _tail_outline(tp, tail, R, teeth, seed, du, tat, nick)
        except ValueError:
            continue
    raise RuntimeError(f"tail {tail.name}: outline self-intersects")


def _tail_outline(tp: TailPath, tail, R: float, teeth: bool, seed: int, du: float, tatters: bool, nicks: bool):
    """The ribbon's outline in (u, v): v across (+ = +W).  The OUTER (image-right) edge runs to the
    tip; the inner edge stops a tear-length short; the tear runs between them.

    Surface pass: the tear is a long CONCAVE taper (the cut crosses most of the width early, then
    thins slowly into a long point, the reference's claw-like ends, not a straight diagonal), its
    line ragged at two scales (a 0 - 2.5 mm bite walk plus small alternating teeth), with a few
    frayed tatters that taper DOWN the ribbon (round 1's loose fibres stuck out sideways like a
    comb), and both edges wave slightly on the hanging part.  B keeps its deep notch and sliver."""
    rng = np.random.default_rng(seed)
    L = float(tp.u[-1])
    lt = tail.tear_R * R
    sgn = tp.outer_sign
    u0 = tp.u_leave

    def w_at(u):
        return float(np.interp(u, tp.u, tp.width))
    u_in_end = L - lt
    uu = tail_u_samples(tp, du, 0.0, u_in_end)
    inner = [(u, -sgn * (0.5 * w_at(u) + float(edge_wobble(u, seed + 101, u0)))) for u in uu]
    inner += [(u_in_end, -sgn * 0.5 * w_at(u_in_end))]
    tear = []
    n_t = max(3, int(lt / (1.6 if teeth else 25.0)))
    notch_at = int(0.42 * n_t) if tail.notch else -1
    walk = 0.4
    P_EXP = 1.4

    def curve(f):
        w = w_at(u_in_end + f * lt)
        return np.array([u_in_end + f * lt, sgn * w * (0.5 - (1.0 - f) ** P_EXP)])

    for i in range(1, n_t):
        f = i / n_t
        base = curve(f)
        tng = curve(min(1.0, f + 0.01)) - curve(max(0.0, f - 0.01))
        tng /= np.linalg.norm(tng)
        perp = np.array([tng[1], -tng[0]])
        if perp[0] < 0:                                   # away from the cloth (toward larger u)
            perp = -perp
        if teeth:
            walk = float(np.clip(walk + rng.normal(0.0, 0.8), -0.5, 3.5))
            r_s, r_m = rng.uniform(), rng.uniform(-0.5, 1.0)
            small = (r_m ** 3 * 1.6 * (1.0 - 0.7 * f)) if r_s < 0.35 else 0.0      # irregular, not a saw
            p0 = base + perp * (walk * (1.0 - 0.6 * f) + small)
            tear.append(tuple(p0))
            r_t, r_l, r_b = rng.uniform(), rng.uniform(0.006, 0.016) * R, rng.uniform(0.6, 1.0)
            if tatters and r_t < 0.12 and 0.08 < f < 0.66 and i != notch_at:
                # a frayed tatter hanging DOWN the ribbon, tapering to a point
                tip_t = p0 + np.array([r_l, -sgn * 0.12 * r_l])
                back = p0 + np.array([0.3, sgn * r_b])
                tear.append(tuple(tip_t))
                tear.append(tuple(back))
        else:
            tear.append(tuple(base))
        if i == notch_at:
            # a deep narrow notch into the cloth, running back up the ribbon
            # (its sliver ~3.5 mm wide between the notch and the outer edge)
            room = 0.5 * w_at(base[0] - 0.30 * lt) - sgn * base[1]
            deep = np.array([base[0] - 0.30 * lt, base[1] + sgn * max(0.0, room - 3.5)])
            tear.append(tuple(base - perp * 1.5 + np.array([-0.05 * lt, 0.0])))
            tear.append(tuple(deep))
            tear.append(tuple(base - perp * 0.5 + np.array([0.03 * lt, sgn * 1.2])))
    tip = (L, sgn * 0.5 * w_at(L))
    uo = tail_u_samples(tp, du, 0.0, L - du * 0.5)
    uo = np.concatenate([uo[uo > 0.0], [L - du * 0.5]]) if len(uo) else np.array([L - du * 0.5])
    uo = np.unique(uo)[::-1]
    outer = []
    for u in uo:
        v = sgn * (0.5 * w_at(u) + float(edge_wobble(u, seed + 202, u0)) * (1.0 - smooth01((u - (L - 40.0)) / 40.0)))
        f_u = (u - u_in_end) / lt
        room = w_at(u) * (1.0 - np.clip(f_u, 0.0, 1.0)) ** P_EXP
        r_n, r_d = rng.uniform(), rng.uniform(0.5, 1.3)
        if teeth and nicks and L - 0.45 * lt < u < L - 12.0 and r_n < 0.5:
            # small ragged nicks on the outer edge near the point (at most a third of the cloth left)
            dep = min(r_d, 0.33 * room)
            outer.append((u + 1.2, v))
            outer.append((u, v - sgn * dep))
            outer.append((u - 1.2, v))
        else:
            outer.append((u, v))
    outer += [(0.0, sgn * 0.5 * w_at(0.0))]
    poly = inner + tear + [tip] + outer
    pts = np.array(poly, np.float64)
    keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 0.4:
            keep.append(i)
    pts = pts[keep]
    if np.linalg.norm(pts[-1] - pts[0]) < 0.4:
        pts = pts[:-1]
    area = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
    if area < 0:
        pts = pts[::-1]
    if not _simple(pts):
        raise ValueError("self-intersecting outline")
    return pts


def smooth01(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def tail_folds(tp: TailPath, u, v, seed: int):
    """Surface pass: the hanging cloth's creases and twisted folds, as a displacement (mm) along the
    ribbon normal: one long soft fold across the width whose phase drifts down the tail (the
    twist), a finer second crease, 0 on the cone and over the tube, faded to 0 at the torn point
    (the tip stays on its measured pixel)."""
    u = np.asarray(u, np.float64)
    v = np.asarray(v, np.float64)
    rng = np.random.default_rng(seed)
    p = rng.uniform(0, 2 * math.pi, 4)
    w = np.interp(u, tp.u, tp.width)
    L = float(tp.u[-1])
    k = smooth01((u - tp.u_leave) / 35.0) * (1.0 - smooth01((u - (L - 30.0)) / 30.0))
    ph1 = p[0] + u / 38.0
    ph2 = p[1] + u / 17.0
    d = 2.6 * np.sin(2 * math.pi * v / w * 0.9 + ph1) + 0.9 * np.sin(2 * math.pi * v / w * 2.1 + ph2)
    return k * d


def _inside(poly, q):
    x, y = q[:, 0], q[:, 1]
    inside = np.zeros(len(q), bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        c = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-30) + x1)
        inside ^= c
    return inside


def _seg_dist(poly, q):
    d = np.full(len(q), np.inf)
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ab = b - a
        t = np.clip(((q - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        d = np.minimum(d, np.linalg.norm(q - (a + t[:, None] * ab), axis=1))
    return d


def build_tail(hat: Hat, mb: MeshBuilder, lod: Lod, tp: TailPath, tail, idx: int):
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    R = hat.R
    t_cl = hat.s.band.thickness_R * R
    poly = tail_outline(tp, tail, R, lod.tail_teeth, seed=5 + idx, du=lod.tail_du)
    # interior points on a grid
    L = float(tp.u[-1])
    us = tail_u_samples(tp, lod.tail_du, lod.tail_du * 0.5, L)
    inner_pts = []
    for u in us:
        w = float(np.interp(u, tp.u, tp.width))
        # surface pass: two more columns where the cloth hangs free and folds
        nc = lod.tail_cols + (2 if (lod.tail_cols >= 3 and u > tp.u_leave) else 0)
        for c in range(nc):
            v = (-0.5 + (c + 1) / (nc + 1)) * w
            inner_pts.append((u, v))
    inner_pts = np.array(inner_pts) if inner_pts else np.zeros((0, 2))
    if len(inner_pts):
        ok = _inside(poly, inner_pts) & (_seg_dist(poly, inner_pts) > 0.35 * lod.tail_du)
        inner_pts = inner_pts[ok]
    verts = [Vector((float(p[0]), float(p[1]))) for p in np.concatenate([poly, inner_pts])]
    nb = len(poly)
    edges = [(i, (i + 1) % nb) for i in range(nb)]
    out_v, _e, out_f, orig_v, _oe, _of = delaunay_2d_cdt(verts, edges, [list(range(nb))], 1, 1e-5)
    UV2 = np.array([(v.x, v.y) for v in out_v], np.float64)

    def frame_at(u):
        i = np.clip(np.searchsorted(tp.u, u) - 1, 0, len(tp.u) - 2)
        f = np.clip((u - tp.u[i]) / np.maximum(tp.u[i + 1] - tp.u[i], 1e-9), 0, 1)[:, None]
        C = tp.C[i] * (1 - f) + tp.C[i + 1] * f
        W = tp.W[i] * (1 - f) + tp.W[i + 1] * f
        W /= np.linalg.norm(W, axis=1, keepdims=True)
        Nn = tp.Nn[i] * (1 - f) + tp.Nn[i + 1] * f
        Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
        return C, W, Nn
    C, W, Nn = frame_at(UV2[:, 0])
    # the folds: displaced along the ribbon normal, the normal tilted by the fold's slope
    fseed = 900 + idx
    D = tail_folds(tp, UV2[:, 0], UV2[:, 1], fseed)
    e = 0.25
    dDu = (tail_folds(tp, UV2[:, 0] + e, UV2[:, 1], fseed) - tail_folds(tp, UV2[:, 0] - e, UV2[:, 1], fseed)) / (2 * e)
    dDv = (tail_folds(tp, UV2[:, 0], UV2[:, 1] + e, fseed) - tail_folds(tp, UV2[:, 0], UV2[:, 1] - e, fseed)) / (2 * e)
    Tt = np.cross(W, Nn)
    Nn0 = Nn.copy()
    Nn = Nn - dDu[:, None] * Tt - dDv[:, None] * W
    Nn /= np.linalg.norm(Nn, axis=1, keepdims=True)
    mid = C + UV2[:, 1:2] * W + D[:, None] * Nn0
    top = mid + 0.5 * t_cl * Nn
    bot = mid - 0.5 * t_cl * Nn
    kt, kb, kw = f"tail{tail.name}_top", f"tail{tail.name}_bot", f"tail{tail.name}_wall"
    mb.member(kt, "cloth", "rect", part="tail", tail=tail.name, side="top", length=L, outer=tp.outer_sign)
    mb.member(kb, "cloth", "rect", part="tail", tail=tail.name, side="bot", length=L, outer=tp.outer_sign)
    for f in out_f:
        f = list(f)
        if len(f) != 3:
            continue
        a, b, c = f
        # (u, v) is CCW; +u x +v = W-ish x ... the top face normal is +Nn
        pts = [top[a], top[b], top[c]]
        fn = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        order = [a, b, c] if fn @ Nn[a] > 0 else [a, c, b]
        mb.face([top[k] for k in order], [UV2[k] for k in order], [Nn[k] for k in order], kt, 1, "tails")
        order_b = order[::-1]
        mb.face([bot[k] for k in order_b], [UV2[k] * np.array([1.0, -1.0]) for k in order_b],
                [-Nn[k] for k in order_b], kb, 1, "tails")
    # walls along the outline (the first nb output vertices are the outline, in order)
    pos = {tuple(np.round(UV2[i], 6)): i for i in range(len(UV2))}
    ring = [pos.get(tuple(np.round(p, 6))) for p in poly]
    if any(r is None for r in ring):
        # fall back: nearest output vertex
        ring = [int(np.argmin(np.linalg.norm(UV2 - p, axis=1))) for p in poly]
    per = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(np.concatenate([poly, poly[:1]]), axis=0), axis=1))])
    chunk_len = 150.0
    for i in range(nb):
        a, b = ring[i], ring[(i + 1) % nb]
        e = UV2[b] - UV2[a]
        # outward in (u, v) for a CCW polygon: (e_v, -e_u)
        o2 = np.array([e[1], -e[0]])
        o2 /= max(np.linalg.norm(o2), 1e-9)
        ta, tb = tp.T[np.clip(np.searchsorted(tp.u, UV2[a, 0]), 0, len(tp.u) - 1)], None
        on = o2[0] * ta + o2[1] * W[a]
        on /= max(np.linalg.norm(on), 1e-9)
        c = int(per[i] // chunk_len)
        key = f"{kw}{c}"
        mb.member(key, "cloth", "rect", part="tail_wall", tail=tail.name)
        x0 = per[i] - c * chunk_len
        x1 = per[i + 1] - c * chunk_len
        quad = [top[a], bot[a], bot[b], top[b]]
        loc = [(x0, t_cl), (x0, 0.0), (x1, 0.0), (x1, t_cl)]
        fn = np.cross(quad[1] - quad[0], quad[2] - quad[0])
        if fn @ on < 0:
            quad, loc = quad[::-1], loc[::-1]
        mb.face(quad, loc, [on] * 4, key, 1, "tails")
    return {"outline_points": int(nb), "interior_points": int(len(inner_pts)), "triangles_top": len(out_f)}


# =========================================================================== all
def build_lod(spec: BlackHatSpec, lod_i: int, cam, tails: Optional[List[TailPath]] = None):
    hat = Hat(spec)
    lod = LODS[lod_i]
    mb = MeshBuilder()
    info = {}
    build_skin(hat, mb, lod)
    build_ribs(hat, mb, lod)
    build_cap(hat, mb, lod)
    build_rim(hat, mb, lod)
    build_lashings(hat, mb, lod)
    info["band"] = build_band(hat, mb, lod)
    info["knot"] = build_knot(hat, mb, lod)
    if tails is None:
        # B lies on the cone; A is laid over it near the knot (REFERENCE_SPEC 8: A over B); both
        # pointed tips on their measured pixels
        tails = solve_tail_paths(hat, spec, cam)
    info["tails"] = {}
    for i, (tp, t) in enumerate(zip(tails, spec.tails)):
        info["tails"][t.name] = {**tp.info, **build_tail(hat, mb, lod, tp, t, i)}
    return mb, info, tails


__all__ = ["Hat", "MeshBuilder", "Member", "LODS", "Lod", "build_lod", "cone_n", "cone_g", "rhat", "that",
           "phi_of", "build_tail_path", "TailPath", "solve_tail_paths", "pointed_tip", "tail_u_samples", "lashing_path", "wrap_profile", "band_section", "knot_frame",
           "BAND_W", "BAND_RU", "BAND_FOLD", "COS_A", "SIN_A", "D2R"]
