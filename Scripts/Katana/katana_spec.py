"""Basic katana: every number and form rule, read from WorkFiles/katana/katana_spec.json (the authority).

Pure Python + numpy (no bpy): the builder, the texture painter, the measurer and the saya fit all import this.
Units: millimetres in the SWORD FRAME (origin = Grip socket, +Z toward the blade along the tsuka axis, +X mune,
-Y omote). Blender objects are built in metres (divide by 1000).

The blade rules (section points, width/thickness taper, kissaki fukura, hamon line) and the tsuka-ito path model are
the study's own formulas (WorkFiles/katana/study/make_design_sheet.py), re-implemented here so the build and the
design sheet share one definition.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
KDIR = ROOT / "WorkFiles" / "katana"
SPEC_PATH = KDIR / "katana_spec.json"
SP = json.load(open(SPEC_PATH, encoding="utf-8"))

NAME = "SM_Katana"
B = SP["blade"]
R = B["mune_arc_radius"]
CX, CZ = B["mune_arc_centre_xz"]
S_TIP = B["mune_arc_length_machi_to_tip"]
S_Y = B["kissaki"]["yokote_station_on_mune_arc"]
Z_M = B["mune_machi_xz"][1]

# ---------------------------------------------------------------------------------------------- slots / atlases
SLOT_NAMES = ["M_Katana_Blade", "M_Katana_Fittings", "M_Katana_Grip"]
SLOT_BLADE, SLOT_FIT, SLOT_GRIP = 0, 1, 2
SLOT_TEX = {"M_Katana_Blade": "T_Katana_Steel", "M_Katana_Fittings": "T_Katana_Steel", "M_Katana_Grip": "T_Katana_Grip"}
STEEL_MAP = 2048
GRIP_MAP = 2048
LOD_SCREEN_SIZES = (1.0, 0.35, 0.15)   # KATANA_BUILD_PLAN.md 2.3 proposal (the plan governs LOD screen sizes)


def lerp(a, b, t):
    return a + (b - a) * t


def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexlin(h):
    h = h.lstrip("#")
    return np.array([srgb2lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)])


MAT = {k: dict(v) for k, v in SP["materials"].items() if isinstance(v, dict)}
# ---------------------------------------------------------------------------------------------- finaliser revisions
# 2026-10-03, from the craft review (WorkFiles/katana/KATANA_REPORT.md section "Revisions to the spec"). The study's
# values read as dark gunmetal / painted slate (ji linear 0.16, far under polished steel's F0 ~0.5) and the hardened
# zone as a flat sharpening bevel; the bamboo mekugi read as a brass rivet and the menuki as a shiny gold bean.
# These values REPLACE the spec's for the paint; katana_spec.json itself is left as the study wrote it.
REV_MATERIALS = {
    "blade_ji": {"hex": "#A7ACB0", "rough": 0.10, "metal": 1.0},                    # polished ji, sRGB ~0.66
    "blade_shinogi_ji_and_mune": {"hex": "#B9BDC0", "rough": 0.05, "metal": 1.0},   # burnished: sharper, not darker
    "blade_hamon": {"hex": "#D6D9DB", "rough": 0.36, "metal": 1.0},                 # frosted: brightest + roughest
    "menuki": {"hex": "#8C6E3C", "rough": 0.35, "metal": 1.0},                      # darker antique patina
    "mekugi": {"hex": "#8A6E45", "rough": 0.62, "metal": 0.0},                      # bamboo: browner, matte
    # the pack's recolourable lacquer cannot go below M_Fabric_Master's black floor (linear 0.01, sRGB ~#1A1A1A; the
    # derive gate 'colour_above_floor'); #0C0C0D (linear 0.0037) is also below any real black lacquer's albedo
    "saya_lacquer": {"hex": "#1D1D1F", "rough": 0.12, "metal": 0.0},
}
for _k, _v in REV_MATERIALS.items():
    MAT[_k].update(_v)
REV_HAMON = {"amplitude": 1.5, "nioi_band": 2.0, "ripple_amplitude": 0.35, "ripple_wavelength": 41.0}
COL = {k: hexlin(v["hex"]) for k, v in MAT.items()}
ROUGH = {k: v["rough"] for k, v in MAT.items()}
METAL = {k: v["metal"] for k, v in MAT.items()}


# ---------------------------------------------------------------------------------------------- blade
def mune_pt(s, rho=None):
    a = s / R
    rr = R if rho is None else rho
    return (CX - rr * math.cos(a), CZ + rr * math.sin(a))


def normal(s):
    a = s / R
    return (-math.cos(a), math.sin(a))


def tangent(s):
    a = s / R
    return (math.sin(a), math.cos(a))


def polar(rho, a):
    return (CX - rho * math.cos(a), CZ + rho * math.sin(a))


def blade_params(s):
    """(w, k, roof, niku, e) at mune-arc station s (study rule)."""
    if s <= S_Y:
        t = s / S_Y
        w = lerp(B["motohaba"], B["sakihaba_at_yokote"], t)
        k = lerp(B["motokasane"], B["sakikasane_at_yokote"], t)
        rf = lerp(B["iori_mune_roof_height"]["machi"], B["iori_mune_roof_height"]["yokote"], t)
        nk = lerp(B["hira_niku"]["machi"], B["hira_niku"]["yokote"], t)
    else:
        q = min(1.0, (s - S_Y) / (S_TIP - S_Y))
        w = B["sakihaba_at_yokote"] * max(0.0, 1.0 - q ** 1.8) ** 0.7
        k = lerp(B["sakikasane_at_yokote"], B["tip_thickness"], q)
        rf = lerp(B["iori_mune_roof_height"]["yokote"], 0.0, q)
        nk = lerp(B["hira_niku"]["yokote"], 0.0, q)
    e = lerp(B["edge_thickness"]["machi"], B["edge_thickness"]["tip"], s / S_TIP)
    return w, k, rf, nk, e


SECTION_F = {0: (0.25, 0.5, 0.75), 1: (0.5,), 2: (0.5,)}


def blade_section_uv(s, lod=0):
    """Section points (u from the mune peak toward the edge, y thickness) for ONE side (y <= 0, omote), from the
    peak to the edge mid point, with a region code per point and the unfolded across-distance V.
    Returns list of (u, y, region, V). Regions: 0 mune roof, 1 shinogi-ji, 2 hira (ji), 3 edge land.
    The ura side is the mirror (y -> -y)."""
    w, k, rf, nk, e = blade_params(s)
    sj = B["shinogi_ji_ratio"] * w
    rf = min(rf, sj * 0.6)
    ts = B["mune_shoulder_thickness_ratio"] * k / 2.0
    e = min(e, k * 0.5)
    pts = [(0.0, 0.0)]
    if lod < 2:
        pts.append((rf, -ts))
    pts.append((sj, -k / 2))
    for f in SECTION_F[lod]:
        pts.append((lerp(sj, w, f), -(lerp(k / 2, e / 2, f) + nk * 4 * f * (1 - f))))
    pts += [(w, -e / 2), (w, 0.0)]
    # unfolded across distance: true section arclength (keeps texel density even on the steep mune roof)
    out = []
    V = 0.0
    for i, (u, y) in enumerate(pts):
        if i:
            V += math.hypot(u - pts[i - 1][0], y - pts[i - 1][1])
        out.append((u, y, V))
    return out, (rf, ts, sj, w, k, e)


def blade_xyz(s, u, y):
    mx, mz = mune_pt(s)
    nx, nz = normal(s)
    return (mx + u * nx, y, mz + u * nz)


def blade_stations(lod):
    """Mune-arc stations from the machi (s 0) to just before the tip (the tip is a single vertex)."""
    step = {0: 12.0, 1: 26.0, 2: 60.0}[lod]
    nk = {0: 26, 1: 12, 2: 5}[lod]
    st = []
    n = int(math.ceil(S_Y / step))
    for i in range(n):
        st.append(S_Y * i / n)
    st.append(S_Y)
    for i in range(1, nk):
        st.append(S_Y + (S_TIP - S_Y) * (1 - (1 - i / nk) ** 1.5))
    return st


def hamon_dist(s, phase=0.0):
    hd = SP["hamon"]["distance_from_edge"]
    base = lerp(hd["machi"], hd["yokote"], min(1.0, s / S_Y))
    wl = SP["hamon"]["undulation"]["wavelengths"]
    amp = REV_HAMON["amplitude"]              # spec 1.0 -> 1.5 (finaliser revision: the wave read as a straight line)
    x = s + phase
    # a faint secondary ripple of a different period keeps the notare from repeating evenly (still quiet)
    rip = REV_HAMON["ripple_amplitude"] * math.sin(2 * math.pi * x / REV_HAMON["ripple_wavelength"] + 1.3) \
        * (0.6 + 0.4 * math.sin(2 * math.pi * x / 173.0))
    acc = 0.0
    i = 0
    while True:
        L = wl[i % len(wl)]
        if x < acc + L:
            t = (x - acc) / L
            sign = 1 if i % 2 == 0 else -1
            return base + sign * amp * math.sin(math.pi * t) + rip
        acc += L
        i += 1


def edge_xz(s):
    w = blade_params(s)[0]
    mx, mz = mune_pt(s)
    nx, nz = normal(s)
    return (mx + w * nx, mz + w * nz)


def u_xz(s, u):
    mx, mz = mune_pt(s)
    nx, nz = normal(s)
    return (mx + u * nx, mz + u * nz)


def hamon_polygon(phase=0.0):
    """Hardened zone outline in the side (x, z) plane: the study's construction (ko-notare + ko-maru boshi)."""
    s0 = 0.0
    ss = []
    s = s0
    while s < S_Y:
        ss.append(s)
        s += 1.0
    kis = [S_Y + (S_TIP - S_Y) * i / 200.0 for i in range(201)]
    E = [edge_xz(s) for s in ss] + [edge_xz(s) for s in kis]
    H = [u_xz(s, blade_params(s)[0] - hamon_dist(s, phase)) for s in ss]
    F = [edge_xz(s) for s in kis]
    Bo = []
    off_b = SP["hamon"]["boshi"]["offset_inside_fukura"]
    h_y = hamon_dist(S_Y, phase)
    for i in range(len(F) - 1):
        (x0, z0), (x1, z1) = F[i], F[i + 1]
        tx, tz = x1 - x0, z1 - z0
        L = math.hypot(tx, tz) or 1e-9
        nx, nz = -tz / L, tx / L
        mx, mz = mune_pt(kis[i])
        if (mx - x0) * nx + (mz - z0) * nz < 0:
            nx, nz = -nx, -nz
        q = i / 200.0
        off = lerp(h_y, off_b, min(1.0, q / 0.25))
        bx, bz = x0 + off * nx, z0 + off * nz
        dist_to_mune = math.hypot(bx - CX, bz - CZ) - R
        Bo.append((bx, bz))
        if dist_to_mune <= off_b:
            break
    bx, bz = Bo[-1]
    a_t = math.atan2(bz - CZ, CX - bx)
    kaeri = SP["hamon"]["boshi"]["kaeri_along_mune"]
    a_ke = a_t - kaeri / R
    P0 = (bx, bz)
    P1 = polar(R + 2.0, a_t + 3.5 / R)
    P2 = polar(R + 2.0, a_t - 0.5 / R)
    maru = []
    for i in range(1, 13):
        t = i / 12.0
        maru.append(((1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * P1[0] + t * t * P2[0],
                     (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * P1[1] + t * t * P2[1]))
    kaer = [polar(R + 2.0, lerp(a_t - 0.5 / R, a_ke, i / 8.0)) for i in range(1, 9)]
    kaer.append(polar(R + 0.05, a_ke))
    mune_back = [polar(R + 0.05, lerp(S_TIP / R, a_ke, i / 30.0)) for i in range(0, 31)]
    poly = E + mune_back + list(reversed(kaer)) + list(reversed(maru)) + list(reversed(Bo)) + list(reversed(H))
    # the visible boundary (hamon line + boshi), for the nioi band
    line = list(H) + list(Bo) + list(maru) + list(kaer[:-1])
    return np.array(poly), np.array(line)


# ---------------------------------------------------------------------------------------------- tsuka
TS = SP["tsuka"]["wrapped_silhouette"]
Z_FB, Z_KT = TS["z_range"]          # 37 (fuchi lower edge) .. -204 (kashira top)
INSET = SP["tsuka"]["same_core_inset"]
NT = 2.8
IT = SP["ito"]
PITCH = IT["wrap_pitch"]
OMOTE_X = IT["omote_crossing_z"]
URA_X = IT["ura_crossing_z"]
MEN = SP["menuki"]
ITO_EDGE_W = 12.4   # finaliser: half a pitch - 0.99 (was - 0.2: neighbouring edge folds intersected where they abut)


def tsuka_dims(z):
    """(centre x, depth D, width W) of the WRAPPED silhouette at z (study rule; haichi taper on the ha side)."""
    t = (Z_FB - z) / (Z_FB - Z_KT)
    t = min(max(t, -0.2), 1.2)
    mune = TS["mune_x"]
    ha = lerp(TS["ha_x"]["at_fuchi"], TS["ha_x"]["at_kashira"], t)
    W = lerp(TS["width_y"]["at_fuchi"], TS["width_y"]["at_kashira"], t)
    return (mune + ha) / 2, mune - ha, W


def core_axes(z):
    cx, D, W = tsuka_dims(z)
    return cx, D / 2 - INSET, W / 2 - INSET


def se_radial(a, b, n, alpha):
    """Superellipse |x/a|^n + |y/b|^n = 1: point and unit outward normal along direction angle alpha."""
    c, s = math.cos(alpha), math.sin(alpha)
    r = (abs(c / a) ** n + abs(s / b) ** n) ** (-1.0 / n)
    x, y = r * c, r * s
    gx = n * abs(x / a) ** (n - 1) * math.copysign(1, x) / a if abs(x) > 1e-12 else 0.0
    gy = n * abs(y / b) ** (n - 1) * math.copysign(1, y) / b if abs(y) > 1e-12 else 0.0
    gl = math.hypot(gx, gy) or 1.0
    return x, y, gx / gl, gy / gl


def se_param(a, b, n, phi):
    """Superellipse point by the study's parameter phi (x = a sgn(c)|c|^(2/n), y = b sgn(s)|s|^(2/n))."""
    c, s = math.cos(phi), math.sin(phi)
    x = a * math.copysign(abs(c) ** (2.0 / n), c)
    y = b * math.copysign(abs(s) ** (2.0 / n), s)
    return x, y


def core_point(z, alpha, h=0.0):
    """Point on the tsuka core surface at height z, direction angle alpha (about the core centre), offset h along the
    surface normal. Returns (p, n) as numpy arrays (mm)."""
    cx, a, b = core_axes(z)
    x, y, nx, ny = se_radial(a, b, NT, alpha)
    return np.array([cx + x + h * nx, y + h * ny, z]), np.array([nx, ny, 0.0])


# ---- kashira end (finaliser revision 2026-10-03). With 9 crossings per face over 9 pitches, the study's path left the
# omote face with no cord between its last edge pass (z -190.6) and the kashira lip (-204): a full-width band of ray skin
# and two loose cord slivers tucked into the lip. Below the LAST ura crossing the wrap's phase now advances faster
# (C1-smooth ramp), so the final half pitch ends with an omote crossing exactly AT the kashira lip: the last omote
# window closes to a point at the lip like a real tight wrap. Above the last ura crossing nothing changes (every spec
# crossing keeps its z). The kashira band over the end is dropped (reviewer's option B: the wrap ends under the lip).
Z_WARP0 = URA_X[-1]                         # -197.31: last ura crossing (identity above)
Z_LIP = Z_KT                                # -204.0: kashira lip = final omote crossing
_WL = Z_WARP0 - Z_LIP                       # 6.69 real mm for half a pitch
_WK = ((PITCH / 2) / _WL - 1.0) / 0.75      # rate(t) = 1 + k smoothstep(0, 0.5, t), mean rate = (PITCH/2) / _WL
# the mirror case at the fuchi: the URA face had the same open band between the fuchi (37) and its first edge pass
# (23.6). Above the FIRST omote crossing the phase advances the same way, so the wrap starts with an ura crossing
# exactly at the fuchi lip (where a real wrap starts: the ito's centre laid under the fuchi).
Z_WARP1 = OMOTE_X[0]                        # 30.31: first omote crossing (identity below)
_WL1 = Z_FB - Z_WARP1                       # 6.69
_WK1 = ((PITCH / 2) / _WL1 - 1.0) / 0.75
OMOTE_X_WRAP = list(OMOTE_X) + [Z_LIP]      # over/under alternation includes the crossings at the lips
URA_X_WRAP = list(URA_X) + [Z_FB]           # (index 9: the alternation rule gives B at -204 and A at 37, as in space)
ITO_END_W = 7.4                             # cord width cap on the compressed passes (their edge passes are ~10.5 mm apart)


def _warp_int(t):
    if t <= 0.5:
        u = t / 0.5
        return 0.5 * (u ** 3 - 0.5 * u ** 4)
    return 0.25 + (t - 0.5)


def warp_z(z):
    """Wrap-phase coordinate z' for the real z (identity between the first omote and the last ura crossing)."""
    if z < Z_WARP0:
        t = (Z_WARP0 - z) / _WL
        if t <= 1.0:
            return Z_WARP0 - _WL * (t + _WK * _warp_int(t))
        return Z_WARP0 - _WL * (1.0 + _WK * 0.75) - (Z_LIP - z) * (1.0 + _WK)
    if z > Z_WARP1:
        t = (z - Z_WARP1) / _WL1
        if t <= 1.0:
            return Z_WARP1 + _WL1 * (t + _WK1 * _warp_int(t))
        return Z_WARP1 + _WL1 * (1.0 + _WK1 * 0.75) + (z - Z_FB) * (1.0 + _WK1)
    return z


def unwarp_z(zp):
    """Inverse of warp_z (bisection; warp_z is strictly increasing)."""
    if Z_WARP0 <= zp <= Z_WARP1:
        return zp
    lo, hi = Z_LIP - 30.0, Z_FB + 30.0
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        if warp_z(mid) > zp:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def cord_phi(z, sign):
    z0 = Z_FB - 0.25 * PITCH
    return -math.pi / 2 + sign * 2 * math.pi * (z0 - warp_z(z)) / PITCH


def eff_phi(phi_l):
    """Study rule: linear helix angle -> superellipse parameter so the cord's lateral position is a triangle wave
    of z (straight diagonals in the side view). Returns (phi_eff, ell)."""
    w = math.atan2(math.sin(phi_l), math.cos(phi_l))
    ell = 1.0 - abs(w) / (math.pi / 2)
    face = -1.0 if math.sin(phi_l) < 0 else 1.0
    c = math.copysign(abs(ell) ** (NT / 2.0), ell)
    s_ = face * math.sqrt(max(0.0, 1.0 - c * c))
    return math.atan2(s_, c), ell


def cord_centre(z, sign):
    """Cord centre line on the core: (point on core, alpha direction, ell lateral, face sign (-1 omote))."""
    phi_e, ell = eff_phi(cord_phi(z, sign))
    cx, a, b = core_axes(z)
    x, y = se_param(a, b, NT, phi_e)
    alpha = math.atan2(y, x)
    return alpha, ell, (-1.0 if y < 0 else 1.0)


def top_cord_at(z, face):
    """Which cord ('A' or 'B') is on top at the crossing nearest z on this face (alternates), and |dz|."""
    xs = OMOTE_X_WRAP if face < 0 else URA_X_WRAP
    k = min(range(len(xs)), key=lambda i: abs(xs[i] - z))
    first = "A" if face < 0 else "B"
    return (first if k % 2 == 0 else ("B" if first == "A" else "A")), abs(xs[k] - z), k


def smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def cord_width(ell):
    """Spec width rule lerp(8, 16, |l|^1.5), capped at half a pitch minus 0.2 mm: at the edge fold the passes of the
    two cords lie side by side half a pitch (13.39 mm) apart, so a 16 mm solid ribbon would cut 2.6 mm into its
    neighbour. The cap leaves a 0.2 mm seam between passes (the core under the edges is painted cord-dark)."""
    w = lerp(IT["cord_width_visible"], IT["cord_width_at_edge_fold"], abs(ell) ** 1.5)
    return min(w, ITO_EDGE_W)


def cord_width_cap(z):
    """Width cap along the wrap: ITO_EDGE_W everywhere, easing to ITO_END_W on the two compressed end passes (below the
    last ura crossing and above the first omote crossing: their edge passes are ~10.5 mm from the neighbours)."""
    return lerp(ITO_EDGE_W, ITO_END_W, max(smoothstep(Z_WARP0 - 0.5, Z_WARP0 - 2.6, z),
                                           smoothstep(Z_WARP1 + 0.5, Z_WARP1 + 2.6, z)))


CORD_THICK = 1.25          # finaliser polish: spec 1.4 read as thick rubber straps up close (review: 1.0-1.2)


def hineri_pinch(z, cname, face):
    """Width factor of the UPPER cord at a face crossing: pinched to ~76 % at the twist so it reads as a fold, not a
    lump (finaliser polish)."""
    top, dz, k = top_cord_at(z, face)
    if top != cname:
        return 1.0
    return 1.0 - 0.24 * (1.0 - smoothstep(1.0, 4.2, dz))


def cord_heights(z, cname, ell, face, x_lat):
    """Bottom / top height above the core and the twist ridge for cord ``cname`` at z.
    Over/under at the face crossings (the upper cord lifts and flattens with a hineri fold ridge, the lower one is
    pressed down), hishigami lift at the edges, rise over the menuki."""
    hb, ht, ridge = -0.3, CORD_THICK, 0.0
    top, dz, k = top_cord_at(z, face)
    g = 1.0 - smoothstep(4.6, 6.2, dz)
    g2 = 1.0 - smoothstep(1.2, 3.6, dz)
    if top == cname:
        hb += 1.12 * g
        ht += 0.32 * g
        ridge = 0.22 * g2
    else:
        ht -= 0.55 * g
        hb -= 0.55 * g
    hish = 0.8 * abs(ell) ** 1.5
    hb += hish
    ht += hish
    # menuki: the cords rise over both ends of the menuki on that face
    zm = MEN["omote"]["z_centre"] if face < 0 else MEN["ura"]["z_centre"]
    dzm = abs(z - zm)
    tz = 1.0 - smoothstep(14.0, 22.0, dzm)
    tx = 1.0 - smoothstep(6.5, 12.0, abs(x_lat))
    m = 3.55 * tz * tx
    hb += m
    ht += m
    return hb, ht, ridge


# ---------------------------------------------------------------------------------------------- fittings
def se_pts(a, b, n, N=64, phase=0.0):
    out = []
    for i in range(N):
        t = 2 * math.pi * i / N + phase
        c, s = math.cos(t), math.sin(t)
        out.append((a * math.copysign(abs(c) ** (2.0 / n), c), b * math.copysign(abs(s) ** (2.0 / n), s)))
    return out


def socket_positions():
    S = SP["sockets"]
    d = dict(S["katana_mm"])
    d.update({k: v for k, v in S["katana_mm_extra"].items() if k != "note"})
    return {k: tuple(float(x) for x in v) for k, v in d.items()}


TIP_PITCH_DEG = SP["blade"]["tip_tangent_deg_from_Z"]
