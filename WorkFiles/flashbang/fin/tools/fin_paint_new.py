# =============================================================================== calibration (albedo targets)
@dataclass
class Look:
    """FINALISE (craft + blind review): darker oxidised steel with bright BROKEN arrises and straight scratch strokes,
    chips with a dark oxidised core and a thin warm bright edge (not pale flecks), heavy dark grime blotches, a wider
    paint tonal range, a hammered paint surface, brighter pitted brass cans, a stamped cross-hatch on the lever."""
    paint_lin: Tuple[float, float, float] = (0.080, 0.080, 0.038)     # olive (lit p50 71,71,54 in the reference)
    paint_mottle: float = 0.30
    paint_fine: float = 0.10
    paint_light: float = 0.55          # lighter worn / dusty patches (the reference's p90 101-116)
    paint_grime: float = 0.62          # dark grime blotches (p10 40-44)
    paint_rough: float = 0.52
    chip_frac: float = 0.143           # spec 9
    chip_near_hole_frac: float = 0.577
    chip_core_lin: Tuple[float, float, float] = (0.034, 0.030, 0.026)  # oxidised dark steel (sRGB ~50)
    chip_edge_lin: Tuple[float, float, float] = (0.26, 0.20, 0.135)    # warm bright bronze-steel rim (sRGB ~125)
    chip_rough: float = 0.55
    steel_lin: Tuple[float, float, float] = (0.040, 0.037, 0.034)      # dark antiqued steel (housing p50 42-50)
    steel_edge_lin: Tuple[float, float, float] = (0.50, 0.40, 0.29)
    steel_rough: float = 0.55
    steel_edge_rough: float = 0.36
    lever_lin: Tuple[float, float, float] = (0.055, 0.052, 0.048)
    ring_lin: Tuple[float, float, float] = (0.050, 0.047, 0.043)       # darker antiqued ring wire (sRGB ~60-75 lit)
    inner_lin: Tuple[float, float, float] = (0.020, 0.019, 0.018)
    brass_lin: Tuple[float, float, float] = (0.80, 0.60, 0.33)
    brass_rough: float = 0.40
    wall_lin: Tuple[float, float, float] = (0.045, 0.041, 0.037)       # hole walls: dark cut steel, grimy
    edge_wear_steel: float = 0.95
    seed: int = 20260927


LOOK = Look()


# =============================================================================== noise
def _hash3(ix, iy, iz, seed):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) ^ seed
    h = (h ^ (h >> 13)) * 1274126177
    h = h ^ (h >> 16)
    return ((h & 0xFFFFFF).astype(np.float32) / float(0xFFFFFF))


def value_noise(p, scale, seed=0):
    """Trilinear value noise in [0, 1] at points p (N, 3) (mm), feature size ``scale`` mm."""
    q = p / scale
    i = np.floor(q)
    f = q - i
    f = f * f * (3 - 2 * f)
    i = i.astype(np.int64)
    out = np.zeros(len(p), np.float32)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * _hash3(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out


def fbm(p, scale, octaves=4, seed=0, gain=0.5):
    tot = np.zeros(len(p), np.float32)
    amp, norm, s = 1.0, 0.0, scale
    for o in range(octaves):
        tot += amp * value_noise(p, s, seed + 101 * o)
        norm += amp
        amp *= gain
        s *= 0.5
    return tot / norm


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def strokes(p, n, cell, density, length, width, seed, vertical=0.0):
    """FINALISE: straight scratch STROKES (no closed loops, no lens shapes - the round-1 level-set scratches drew a
    vesica on the housing).  A 3-D grid of ``cell`` mm cells; each cell holds one stroke with probability
    ``density``: a random centre, direction (``vertical`` biases it toward +-Z), length in ``length`` mm and width
    ``width`` x (0.6 .. 1.4) mm.  Evaluated in each point's tangent plane (the offset along the surface normal only
    gates it), so a stroke marks the surface it passes near.  Returns 0..1 (Gaussian across, tapered ends)."""
    out = np.zeros(len(p), np.float32)
    if len(p) == 0:
        return out
    base = np.floor(p / cell).astype(np.int64)
    lim = 0.5 * cell
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = base + np.array([dx, dy, dz], np.int64)
                present = _hash3(c[:, 0], c[:, 1], c[:, 2], seed) < density
                idx = np.nonzero(present)[0]
                if not len(idx):
                    continue
                cc = c[idx]
                hs = [_hash3(cc[:, 0], cc[:, 1], cc[:, 2], seed + k) for k in range(1, 8)]
                centre = (cc + np.stack(hs[:3], 1)) * cell
                a1 = hs[3] * (2 * math.pi)
                a2 = hs[4] * 2.0 - 1.0
                sq = np.sqrt(np.clip(1.0 - a2 * a2, 0, 1))
                d = np.stack([sq * np.cos(a1), sq * np.sin(a1), a2], 1)
                if vertical:
                    d = d * (1.0 - vertical) + np.array([0.0, 0.0, 1.0]) * vertical * np.where(a2 >= 0, 1.0, -1.0)[:, None]
                    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
                L = length[0] + hs[5] * (length[1] - length[0])
                w = width * (0.6 + 0.8 * hs[6])
                v = p[idx] - centre
                nn = n[idx]
                vn = (v * nn).sum(1)
                vt = v - vn[:, None] * nn
                dt = d - (d * nn).sum(1)[:, None] * nn
                dl = np.linalg.norm(dt, axis=1)
                dt = dt / np.maximum(dl, 1e-9)[:, None]
                along = (vt * dt).sum(1)
                perp = np.linalg.norm(vt - along[:, None] * dt, axis=1)
                taper = np.clip(1.0 - (along / (0.5 * L)) ** 2, 0.0, 1.0)
                val = np.exp(-(perp / w) ** 2) * taper * (dl > 0.35) * (np.abs(vn) < lim)
                out[idx] = np.maximum(out[idx], val.astype(np.float32))
    return out
