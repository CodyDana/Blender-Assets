"""BlackCloak_MH_v2 stage 2: pattern geometry (flat pieces, size-field triangulation), the funnel collar and body profiles.

Pure numpy + mathutils (runs inside Blender 5.2). No bpy scene access except where an object is passed in.
"""
import math
import numpy as np
from mathutils import Vector
import mathutils.geometry as MG

import bcv2_common as C

CY = -0.01          # neck axis centre (x = 0, y = CY) used for azimuths / radii


# ============================================================ body radial profile
class RadialProfile:
    """Max radial extent of skin points around (0, CY) per (azimuth, z) bin: prof(phi_deg, z) -> metres."""

    def __init__(self, points, dphi=2.0, dz=0.005, zlo=1.30, zhi=1.90):
        self.dphi, self.dz, self.zlo = dphi, dz, zlo
        nphi = int(round(360 / dphi))
        nz = int(round((zhi - zlo) / dz)) + 1
        tab = np.zeros((nphi, nz))
        p = points[(points[:, 2] >= zlo - dz) & (points[:, 2] <= zhi + dz)]
        phi = np.degrees(np.arctan2(p[:, 0], -(p[:, 1] - CY)))
        rr = np.hypot(p[:, 0], p[:, 1] - CY)
        ip = np.floor((phi + 180.0) / dphi).astype(int) % nphi
        iz = np.clip(np.round((p[:, 2] - zlo) / dz).astype(int), 0, nz - 1)
        np.maximum.at(tab, (ip, iz), rr)
        # widen: each bin takes the max of +-2 azimuth bins and +-1 z bins (thin-slab sampling gaps)
        t2 = tab.copy()
        for s in (-2, -1, 1, 2):
            t2 = np.maximum(t2, np.roll(tab, s, axis=0))
        t3 = t2.copy()
        t3[:, 1:] = np.maximum(t3[:, 1:], t2[:, :-1])
        t3[:, :-1] = np.maximum(t3[:, :-1], t2[:, 1:])
        self.tab = t3
        self.nphi, self.nz = nphi, nz

    def __call__(self, phi_deg, z):
        ip = int(math.floor((phi_deg + 180.0) / self.dphi)) % self.nphi
        iz = int(round((z - self.zlo) / self.dz))
        if iz < 0 or iz >= self.nz:
            return 0.0
        return float(self.tab[ip, iz])


# ============================================================ funnel collar
def _t(table, phi):
    return C.interp_table(table, C.wrap180(phi), periodic=360.0)


RHO_TOP = [(-180, .140), (-135, .133), (-90, .128), (-45, .136), (0, .145), (45, .136), (90, .128), (135, .133)]
RHO_BOT = [(-180, .136), (-135, .130), (-90, .126), (-75, .165), (-58, .186), (-38, .180), (0, .170), (38, .180), (58, .186), (75, .165), (90, .126), (135, .130)]
Z_BOT = [(-180, 1.582), (-135, 1.590), (-90, 1.586), (-72, 1.530), (-60, 1.468), (-45, 1.452), (-30, 1.446), (0, 1.440),
         (30, 1.452), (50, 1.492), (70, 1.552), (90, 1.586), (135, 1.590)]
RIM_FRONT, RIM_BACK = 1.690, 1.746      # the rolled rim's INNER boundary heights (what a boundary probe reads)
ROLL_R = 0.0025
ROLL_DROP = 0.003


def rim_boundary_z(phi):
    s = abs(math.sin(math.radians(phi) / 2.0))
    e = 0.06
    g = (math.sqrt(s * s + e * e) - e) / (math.sqrt(1 + e * e) - e)
    return RIM_FRONT + (RIM_BACK - RIM_FRONT) * g ** 0.8


class Funnel:
    """Smooth stand-up funnel: a loft between a bottom ring and a rim ring around (0, CY), kept >= CLEAR off the
    skin (body + head + hair proxy, arms-down), finished with a rolled rim (the fabric curls inward over the top
    edge and ends 3 mm down the inside: a soft 5 mm thick rim whose inner edge is the garment boundary)."""

    CLEAR = 0.018

    def __init__(self, profile, ncol=84, nrow=22):
        self.ncol, self.nrow = ncol, nrow
        phis = np.array([-180.0 + 360.0 * i / ncol for i in range(ncol)])     # column 0 = centre back
        self.phis = phis
        zb = np.array([_t(Z_BOT, p) for p in phis])
        apex = np.array([rim_boundary_z(p) + ROLL_DROP + ROLL_R for p in phis])
        ztop = apex - ROLL_R
        rb = np.array([_t(RHO_BOT, p) for p in phis])
        rt = np.array([_t(RHO_TOP, p) for p in phis])
        # raise the bottom where the skin comes within CLEAR+0.004 of the bottom ring (shoulders / pecs)
        for i, p in enumerate(phis):
            for _ in range(60):
                bad = any(profile(p, zb[i] + dz) > rb[i] - self.CLEAR - 0.004 for dz in np.linspace(0, 0.03, 7))
                if not bad:
                    break
                zb[i] += 0.004
        zb = self._smooth_ring(zb, 3)
        V = np.zeros((nrow, ncol))
        for j in range(nrow):
            V[j] = j / (nrow - 1)
        Z = zb[None, :] + V * (ztop - zb)[None, :]
        R = rb[None, :] + (rt - rb)[None, :] * (V ** 0.9)
        # clearance: push the wall out where the skin is closer than CLEAR, then smooth and re-check
        for it in range(6):
            need = np.zeros_like(R)
            for j in range(nrow):
                for i in range(ncol):
                    need[j, i] = profile(phis[i], Z[j, i]) + self.CLEAR
            R = np.maximum(R, need)
            R = self._smooth_grid(R, 2)
        R = np.maximum(R, need)
        self.Z, self.R, self.zb, self.ztop = Z, R, zb, ztop
        self._build_mesh()

    @staticmethod
    def _smooth_ring(a, n):
        a = a.copy()
        for _ in range(n):
            a = 0.25 * np.roll(a, 1) + 0.5 * a + 0.25 * np.roll(a, -1)
        return a

    @staticmethod
    def _smooth_grid(R, n):
        R = R.copy()
        for _ in range(n):
            Rs = 0.25 * np.roll(R, 1, axis=1) + 0.5 * R + 0.25 * np.roll(R, -1, axis=1)
            Rv = Rs.copy()
            Rv[1:-1] = 0.25 * Rs[:-2] + 0.5 * Rs[1:-1] + 0.25 * Rs[2:]
            R = Rv
        return R

    def point(self, i, j):
        p = math.radians(self.phis[i % self.ncol])
        r = self.R[j, i % self.ncol]
        return np.array([r * math.sin(p), CY - r * math.cos(p), self.Z[j, i % self.ncol]])

    def wall_point(self, phi, z, offset=0.0):
        """Point on the funnel's outer wall at azimuth phi (deg) and height z (clamped to the wall), pushed
        ``offset`` along the horizontal outward normal."""
        f = ((phi + 180.0) % 360.0) / 360.0 * self.ncol
        i0 = int(math.floor(f)) % self.ncol
        i1 = (i0 + 1) % self.ncol
        t = f - math.floor(f)
        out = []
        for i in (i0, i1):
            zc = self.Z[:, i]
            zz = min(max(z, zc[0]), zc[-1])
            j = int(np.searchsorted(zc, zz)) - 1
            j = min(max(j, 0), self.nrow - 2)
            u = (zz - zc[j]) / max(zc[j + 1] - zc[j], 1e-9)
            out.append(((1 - u) * self.R[j, i] + u * self.R[j + 1, i], zz))
        r = (1 - t) * out[0][0] + t * out[1][0]
        zz = (1 - t) * out[0][1] + t * out[1][1]
        pr = math.radians(phi)
        r += offset
        return np.array([r * math.sin(pr), CY - r * math.cos(pr), zz])

    def _build_mesh(self):
        nc, nr = self.ncol, self.nrow
        rows = [[self.point(i, j) for i in range(nc)] for j in range(nr)]
        # rolled rim: the top row curls inward over a semicircle of radius ROLL_R and runs ROLL_DROP down the inside
        top = np.array(rows[-1])
        below = np.array(rows[-2])
        up = top - below
        up /= np.linalg.norm(up, axis=1, keepdims=True)
        tang = np.roll(top, -1, axis=0) - np.roll(top, 1, axis=0)
        nout = np.cross(tang, up)
        nout /= np.linalg.norm(nout, axis=1, keepdims=True)
        # make sure nout points away from the axis
        radial = top[:, :2] - np.array([0.0, CY])
        flip = (nout[:, :2] * radial).sum(1) < 0
        nout[flip] *= -1
        centre = top - ROLL_R * nout
        for ang in (45, 90, 135, 180):
            a = math.radians(ang)
            rows.append(list(centre + ROLL_R * (math.cos(a) * nout + math.sin(a) * up)))
        rows.append(list(centre - ROLL_R * nout - ROLL_DROP * up))
        self.rows = [np.array(r) for r in rows]
        self.nrows_total = len(rows)
        V = np.concatenate(self.rows)
        F = []
        for j in range(len(rows) - 1):
            for i in range(nc):
                a = j * nc + i
                b = j * nc + (i + 1) % nc
                c = (j + 1) * nc + (i + 1) % nc
                d = (j + 1) * nc + i
                F.append((a, b, c, d))
        self.verts = V
        self.faces = F
        # pattern coordinates: v = arc length up the column, u = signed arc length along the row from the centre front
        vcoord = np.zeros((len(rows), nc))
        for j in range(1, len(rows)):
            vcoord[j] = vcoord[j - 1] + np.linalg.norm(self.rows[j] - self.rows[j - 1], axis=1)
        ucoord = np.zeros((len(rows), nc))
        for j in range(len(rows)):
            seg = np.linalg.norm(np.roll(self.rows[j], -1, axis=0) - self.rows[j], axis=1)
            cum = np.concatenate([[0.0], np.cumsum(seg)])          # from column 0 (centre back) around, length nc+1
            ucoord[j] = cum[:nc] - cum[nc] / 2.0
        self.ucoord, self.vcoord = ucoord, vcoord
        self.row_len_bottom = float(np.sum(np.linalg.norm(np.roll(self.rows[0], -1, axis=0) - self.rows[0], axis=1)))

    def uv_of_corner(self, face_index, corner):
        """Pattern coordinate of a face corner (the CB column is split: faces on the seam use +L/2)."""
        nc = self.ncol
        j = face_index // nc
        i = face_index % nc
        ii = [i, (i + 1) % nc, (i + 1) % nc, i][corner]
        jj = [j, j, j + 1, j + 1][corner]
        u = self.ucoord[jj, ii]
        if i == nc - 1 and corner in (1, 2):   # wrapped column: continue past the seam
            seg = np.linalg.norm(self.rows[jj][0] - self.rows[jj][nc - 1])
            u = self.ucoord[jj, nc - 1] + seg
        return (u, self.vcoord[jj, ii])


# ============================================================ size-field triangulation of flat pattern pieces
def point_in_polygon(pts, poly):
    """Vectorised even-odd test; pts (N,2), poly (M,2) closed implicitly."""
    x, y = pts[:, 0], pts[:, 1]
    inside = np.zeros(len(pts), bool)
    px, py = poly[:, 0], poly[:, 1]
    qx, qy = np.roll(px, -1), np.roll(py, -1)
    for x0, y0, x1, y1 in zip(px, py, qx, qy):
        cond = ((y0 > y) != (y1 > y))
        with np.errstate(divide="ignore", invalid="ignore"):
            xin = (x1 - x0) * (y - y0) / (y1 - y0 + 1e-300) + x0
        inside ^= cond & (x < xin)
    return inside


def resample_polyline(pts, hfun, closed=False, keep_ends=True):
    """Resample a dense polyline with local spacing hfun(p); returns (K,2) including both ends."""
    pts = np.asarray(pts, float)
    if closed:
        pts = np.vstack([pts, pts[:1]])
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    total = cum[-1]
    # integrate 1/h along the curve
    dense_n = max(int(total / 0.002), 10)
    s = np.linspace(0, total, dense_n + 1)
    dp = np.array([np.interp(s, cum, pts[:, k]) for k in range(2)]).T
    inv = np.array([1.0 / hfun(p) for p in dp])
    w = np.concatenate([[0], np.cumsum(0.5 * (inv[1:] + inv[:-1]) * np.diff(s))])
    n = max(int(round(w[-1])), 1)
    targets = np.linspace(0, w[-1], n + 1)
    ss = np.interp(targets, w, s)
    out = np.array([np.interp(ss, cum, pts[:, k]) for k in range(2)]).T
    if closed:
        out = out[:-1]
    return out


def triangulate_pattern(loop, constraints, hfun, seed=7, smooth_iters=5):
    """Isotropic triangulation of a flat pattern piece.

    loop: (M,2) boundary polygon (already resampled, CCW); constraints: list of (K,2) polylines inside (resampled);
    hfun: local edge length (metres) at a 2-D point. Returns (points (N,2), triangles (T,3), nfixed) where the first
    nfixed points are the boundary + constraint points in input order (loop first)."""
    rng = np.random.default_rng(seed)
    constraints = [c if isinstance(c, tuple) else (c, None, None) for c in constraints]
    fixed = [loop] + [c[0] for c in constraints]
    fixed_pts = np.vstack(fixed)
    nfixed = len(fixed_pts)
    lo, hi = loop.min(0), loop.max(0)
    hmin = min(hfun(p) for p in fixed_pts)
    cands = []
    CB = 0.10
    for cx in np.arange(lo[0], hi[0] + CB, CB):
        for cy in np.arange(lo[1], hi[1] + CB, CB):
            hc = min(hfun((cx + dx * CB, cy + dy * CB)) for dx in (0.0, 0.5, 1.0) for dy in (0.0, 0.5, 1.0))
            st = 0.45 * hc
            n = max(int(math.ceil(CB / st)), 1)
            g = (np.arange(n) + 0.5) / n * CB
            gg = np.array(np.meshgrid(cx + g, cy + g)).reshape(2, -1).T
            gg = gg + rng.uniform(-0.5, 0.5, gg.shape) * (CB / n)
            cands.append(gg)
    G = np.vstack(cands)
    G = G[point_in_polygon(G, loop)]
    hmin = min(hmin, 0.02)
    rng.shuffle(G)
    H = np.array([hfun(p) for p in G])
    # spatial hash of accepted points
    cell = 0.02
    grid = {}
    acc = []

    def add(p, h):
        k = (int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell)))
        grid.setdefault(k, []).append((p[0], p[1], h))

    for p in fixed_pts:
        add(p, hfun(p))
    hmax = max(H.max() if len(H) else hmin, hmin)
    reach = int(math.ceil(hmax / cell)) + 1
    for p, h in zip(G, H):
        kx, ky = int(math.floor(p[0] / cell)), int(math.floor(p[1] / cell))
        ok = True
        rr = int(math.ceil(h / cell)) + 1
        for dx in range(-rr, rr + 1):
            if not ok:
                break
            for dy in range(-rr, rr + 1):
                for (qx, qy, hq) in grid.get((kx + dx, ky + dy), ()):
                    lim = 0.88 * 0.5 * (h + hq)
                    if (p[0] - qx) ** 2 + (p[1] - qy) ** 2 < lim * lim:
                        ok = False
                        break
                if not ok:
                    break
        if ok:
            acc.append(p)
            add(p, h)
    pts = np.vstack([fixed_pts, np.array(acc)]) if acc else fixed_pts.copy()
    # constraint edges (loop closed + each polyline open)
    edges = []
    off = 0
    m = len(loop)
    edges += [(i, (i + 1) % m) for i in range(m)]
    off = m
    for c, cs, ce in constraints:
        idx = list(range(off, off + len(c)))
        if cs is not None:
            idx = [cs] + idx
        if ce is not None:
            idx = idx + [ce]
        edges += [(idx[i], idx[i + 1]) for i in range(len(idx) - 1)]
        off += len(c)

    def cdt(points):
        vin = [Vector((float(x), float(y))) for x, y in points]
        res = MG.delaunay_2d_cdt(vin, edges, [], 0, 1e-9)
        vout, _e, faces, orig_v = res[0], res[1], res[2], res[3]
        # map output verts back to input indices (drop verts created by the CDT: should not happen)
        mapping = {}
        for k, ov in enumerate(orig_v):
            if ov:
                mapping[k] = ov[0]
        tris = []
        for f in faces:
            if len(f) != 3 or any(v not in mapping for v in f):
                continue
            tris.append([mapping[v] for v in f])
        tris = np.array(tris, int)
        cen = points[tris].mean(1)
        tris = tris[point_in_polygon(cen, loop)]
        return tris

    tris = cdt(pts)
    for _ in range(smooth_iters):
        # Laplacian (neighbour average, weighted by 1/h^2 of the neighbour) of free points, then re-triangulate
        n = len(pts)
        acc_p = np.zeros((n, 2))
        acc_w = np.zeros(n)
        for a, b in ((0, 1), (1, 2), (2, 0), (1, 0), (2, 1), (0, 2)):
            np.add.at(acc_p, tris[:, a], pts[tris[:, b]])
            np.add.at(acc_w, tris[:, a], 1.0)
        newp = pts.copy()
        free = np.arange(n) >= nfixed
        mv = free & (acc_w > 0)
        newp[mv] = 0.5 * pts[mv] + 0.5 * acc_p[mv] / acc_w[mv, None]
        ok = point_in_polygon(newp, loop)
        newp[~ok] = pts[~ok]
        pts = newp
        tris = cdt(pts)
    # orient CCW
    a, b, c = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    tris[cross < 0] = tris[cross < 0][:, [0, 2, 1]]
    # drop unreferenced points (should be none) keeping the fixed block order
    used = np.zeros(len(pts), bool)
    used[tris.ravel()] = True
    if not used.all():
        remap = -np.ones(len(pts), int)
        keep = np.nonzero(used | (np.arange(len(pts)) < nfixed))[0]
        remap[keep] = np.arange(len(keep))
        pts = pts[keep]
        tris = remap[tris]
    return pts, tris, nfixed


def tri_min_angles(P, T):
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]

    def ang(p, q, r):
        u, v = q - p, r - p
        cs = (u * v).sum(1) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-12)
        return np.degrees(np.arccos(np.clip(cs, -1, 1)))
    return np.minimum(np.minimum(ang(a, b, c), ang(b, c, a)), ang(c, a, b))
