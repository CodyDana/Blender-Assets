"""Dimensioned design sheet for the basic katana + saya, built from katana_spec.json.

Headless:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
      --python WorkFiles/katana/study/make_design_sheet.py -- [--out PNG] [--blend BLEND] [--res 7000]

Every part is a quick primitive built in the SWORD FRAME (mm, see the spec's frame_sword), then
copied into orthographic views on one sheet at a common 1:1 scale (details at stated scales, each
with its own ruler). Workbench render, one orthographic camera. Writes sheet_measures.json
(diamond opening etc., measured on this model).
"""
import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.normpath(os.path.join(HERE, ".."))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return argv[argv.index(name) + 1] if name in argv else default


OUT = arg("--out", os.path.join(KDIR, "KATANA_DESIGN_SHEET.png"))
BLEND = arg("--blend", "")
RES_X = int(arg("--res", "7000"))
SP = json.load(open(os.path.join(KDIR, "katana_spec.json"), encoding="utf-8"))

B = SP["blade"]
R = B["mune_arc_radius"]
CX, CZ = B["mune_arc_centre_xz"]
S_TIP = B["mune_arc_length_machi_to_tip"]
S_Y = B["kissaki"]["yokote_station_on_mune_arc"]
Z_M = B["mune_machi_xz"][1]

# ------------------------------------------------------------------ scene
bpy.ops.wm.read_factory_settings(use_empty=True)
SC = bpy.context.scene
SRC = bpy.data.collections.new("SRC")   # part meshes live here, unlinked from the scene


def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h):
    h = h.lstrip("#")
    return tuple(srgb2lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (1.0,)


M = SP["materials"]
COL = {
    "ji": hexcol(M["blade_ji"]["hex"]), "mune": hexcol(M["blade_shinogi_ji_and_mune"]["hex"]),
    "hamon": hexcol(M["blade_hamon"]["hex"]), "habaki": hexcol(M["habaki"]["hex"]), "seppa": hexcol(M["seppa"]["hex"]),
    "iron": hexcol(M["iron_fittings"]["hex"]), "menuki": hexcol(M["menuki"]["hex"]), "brass": hexcol(M["eyelets_and_shitodome"]["hex"]),
    "ito": hexcol(M["ito"]["hex"]), "same": hexcol(M["same"]["hex"]), "mekugi": hexcol(M["mekugi"]["hex"]),
    "lacquer": hexcol("#1A1A1C"),  # sheet only: a touch lighter than #0C0C0D so the horn seams read
    "horn": hexcol("#2E241C"), "ink": (0.0, 0.0, 0.0, 1.0), "dim": hexcol("#1F4E9A"), "line": hexcol("#30363C"),
    "hole": hexcol("#050505"), "grid": hexcol("#B9C2CC"), "red": hexcol("#B0302A"),
}
PARTS = {}   # name -> (mesh, colour)


def new_mesh(name, verts, faces, smooth=False, recalc=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate()
    if recalc:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    if smooth:
        me.shade_smooth()
    return me


def part(name, verts, faces, colour, smooth=False, recalc=True):
    PARTS[name] = (new_mesh(name, verts, faces, smooth, recalc), colour)


def loft(rings, cap0=True, cap1=True):
    n = len(rings[0])
    verts = [v for ring in rings for v in ring]
    faces = []
    for i in range(len(rings) - 1):
        for j in range(n):
            a, b = i * n + j, i * n + (j + 1) % n
            faces.append((a, b, b + n, a + n))
    if cap0:
        faces.append(tuple(reversed(range(n))))
    if cap1:
        faces.append(tuple(range((len(rings) - 1) * n, len(rings) * n)))
    return verts, faces


def se_pts(a, b, n, N=64):
    """superellipse half-axes a (x), b (y), exponent n; returns list of (x, y)."""
    out = []
    for i in range(N):
        t = 2 * math.pi * i / N
        c, s = math.cos(t), math.sin(t)
        out.append((a * math.copysign(abs(c) ** (2.0 / n), c), b * math.copysign(abs(s) ** (2.0 / n), s)))
    return out


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ blade geometry (sword frame)
def mune_pt(s, rho=None):
    a = s / R
    rr = R if rho is None else rho
    return (CX - rr * math.cos(a), CZ + rr * math.sin(a))


def normal(s):
    a = s / R
    return (-math.cos(a), math.sin(a))


def polar(rho, a):
    return (CX - rho * math.cos(a), CZ + rho * math.sin(a))


def blade_params(s):
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


def blade_section(s):
    w, k, rf, nk, e = blade_params(s)
    sj = B["shinogi_ji_ratio"] * w
    rf = min(rf, sj * 0.6)
    ts = B["mune_shoulder_thickness_ratio"] * k / 2.0
    e = min(e, k * 0.5)
    pts = [(0.0, 0.0), (rf, -ts), (sj, -k / 2)]
    for f in (0.25, 0.5, 0.75):
        pts.append((lerp(sj, w, f), -(lerp(k / 2, e / 2, f) + nk * 4 * f * (1 - f))))
    pts += [(w, -e / 2), (w, e / 2)]
    for f in (0.75, 0.5, 0.25):
        pts.append((lerp(sj, w, f), (lerp(k / 2, e / 2, f) + nk * 4 * f * (1 - f))))
    pts += [(sj, k / 2), (rf, ts)]
    mx, mz = mune_pt(s)
    nx, nz = normal(s)
    return [(mx + u * nx, y, mz + u * nz) for (u, y) in pts], pts


def build_blade():
    stations = []
    s = 0.0
    while s < S_Y:
        stations.append(s)
        s += 6.0
    stations.append(S_Y)
    for i in range(1, 60):
        stations.append(S_Y + (S_TIP - S_Y) * (1 - (1 - i / 60.0) ** 1.5))
    rings = [blade_section(s)[0] for s in stations]
    verts, faces = loft(rings, cap0=True, cap1=False)
    tip = mune_pt(S_TIP)
    verts.append((tip[0], 0.0, tip[1]))
    n = len(rings[0])
    base = (len(rings) - 1) * n
    ti = len(verts) - 1
    for j in range(n):
        faces.append((base + j, base + (j + 1) % n, ti))
    part("blade", verts, faces, COL["ji"])


# ------------------------------------------------------------------ hamon / lines (2D in the side plane)
def hamon_dist(s, phase=0.0):
    hd = SP["hamon"]["distance_from_edge"]
    base = lerp(hd["machi"], hd["yokote"], min(1.0, s / S_Y))
    wl = SP["hamon"]["undulation"]["wavelengths"]
    amp = SP["hamon"]["undulation"]["amplitude"]
    x = s + phase
    acc = 0.0
    i = 0
    while True:
        L = wl[i % len(wl)]
        if x < acc + L:
            t = (x - acc) / L
            sign = 1 if i % 2 == 0 else -1
            return base + sign * amp * math.sin(math.pi * t)
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
    s0 = SP["habaki"]["length"]
    ss = []
    s = s0
    while s < S_Y:
        ss.append(s)
        s += 2.0
    kis = [S_Y + (S_TIP - S_Y) * i / 200.0 for i in range(201)]
    E = [edge_xz(s) for s in ss] + [edge_xz(s) for s in kis]
    H = [u_xz(s, blade_params(s)[0] - hamon_dist(s, phase)) for s in ss]
    # boshi: fukura offset inward, blending 5.0 -> 4.0 over the first quarter of the kissaki
    F = [edge_xz(s) for s in kis]
    Bo = []
    off_b = SP["hamon"]["boshi"]["offset_inside_fukura"]
    h_y = hamon_dist(S_Y, phase)
    turn_i = None
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
            turn_i = i
            break
    bx, bz = Bo[-1]
    a_t = math.atan2(bz - CZ, CX - bx)
    kaeri = SP["hamon"]["boshi"]["kaeri_along_mune"]
    a_ke = a_t - kaeri / R
    # maru turn: Bezier from the turn point to the kaeri line (2 mm inside the mune)
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
    # remove the duplicated final kaeri / mune point ordering: mune_back ends at a_ke, kaer reversed starts there
    return poly, H, Bo, maru, kaer


def flat_poly(name, pts2, y, colour):
    verts = [(x, y, z) for (x, z) in pts2]
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in verts]
    try:
        f = bm.faces.new(vs)
    except ValueError:
        pass
    bm.to_mesh(me)
    bm.free()
    PARTS[name] = (me, colour)


def strip(pts2, width):
    """2D polyline -> quad strip vertices (x, z) pairs."""
    L, Rr = [], []
    for i in range(len(pts2)):
        a = pts2[max(0, i - 1)]
        b = pts2[min(len(pts2) - 1, i + 1)]
        tx, tz = b[0] - a[0], b[1] - a[1]
        l = math.hypot(tx, tz) or 1e-9
        nx, nz = -tz / l * width / 2, tx / l * width / 2
        L.append((pts2[i][0] + nx, pts2[i][1] + nz))
        Rr.append((pts2[i][0] - nx, pts2[i][1] - nz))
    return L, Rr


def line_part(name, pts2, y, width, colour):
    L, Rr = strip(pts2, width)
    verts = [(x, y, z) for (x, z) in L] + [(x, y, z) for (x, z) in Rr]
    n = len(pts2)
    faces = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1)]
    part(name, verts, faces, colour, recalc=False)


def build_overlays():
    yo = -4.3
    for side, phase, ysg in (("omote", 0.0, -1), ("ura", 15.0, 1)):
        poly, H, Bo, maru, kaer = hamon_polygon(phase)
        flat_poly("hamon_" + side, poly, ysg * 4.3, COL["hamon"])
        line_part("nioi_" + side, list(H) + list(Bo) + list(maru) + list(kaer[:-1]), ysg * 4.35, 0.5, COL["line"])
    # shinogi + ko-shinogi, yokote, mune shoulder lines (both faces)
    s0 = SP["habaki"]["length"]
    ss = [s0 + i * (S_Y - s0) / 200 for i in range(201)]
    kis = [S_Y + (S_TIP - S_Y) * i / 80.0 for i in range(81)]
    shin = [u_xz(s, B["shinogi_ji_ratio"] * blade_params(s)[0]) for s in ss + kis[1:]]
    w_y = blade_params(S_Y)[0]
    yok = [u_xz(S_Y, B["shinogi_ji_ratio"] * w_y), u_xz(S_Y, w_y)]
    sh = [u_xz(s, min(blade_params(s)[2], B["shinogi_ji_ratio"] * blade_params(s)[0] * 0.6)) for s in ss + kis[1:-1]]
    for side, ysg in (("omote", -1), ("ura", 1)):
        line_part("shinogi_" + side, shin, ysg * 4.4, 0.55, COL["line"])
        line_part("yokote_" + side, yok, ysg * 4.4, 0.55, COL["line"])
        line_part("muneline_" + side, sh, ysg * 4.4, 0.35, COL["line"])


# ------------------------------------------------------------------ koshirae parts
def build_habaki():
    H = SP["habaki"]
    z0, z1 = H["z"]
    rings = []
    for z, sec in ((z0, H["section_base"]), (z1 - 0.4, H["section_top"]), (z1, H["section_top"])):
        xa, xb = sec["x"]
        yh = sec["y_half"]
        if z == z1:
            xa, xb, yh = xa + 0.4, xb - 0.4, yh - 0.4
        cx = (xa + xb) / 2
        rings.append([(cx + x, y, z) for (x, y) in se_pts((xb - xa) / 2, yh, 4.0, 64)])
    part("habaki", *loft(rings), COL["habaki"], smooth=True)


def build_seppa():
    S = SP["seppa"]
    o = S["outline"]
    for nm, (z0, z1) in (("seppa_blade", S["z_blade_side"]), ("seppa_tsuka", S["z_tsuka_side"])):
        rings = [[(x, y, z) for (x, y) in se_pts(o["depth_x"] / 2, o["width_y"] / 2, o["superellipse_n"], 64)] for z in (z0, z1)]
        part(nm, *loft(rings), COL["seppa"], smooth=True)


def revolve(profile, N=96):
    rings = []
    for i in range(N):
        a = 2 * math.pi * i / N
        rings.append([(r * math.cos(a), r * math.sin(a), z) for (r, z) in profile])
    n = len(profile)
    verts = [v for ring in rings for v in ring]
    faces = []
    for i in range(N):
        i2 = (i + 1) % N
        for j in range(n - 1):
            faces.append((i * n + j, i * n + j + 1, i2 * n + j + 1, i2 * n + j))
    return verts, faces


def build_tsuba():
    T = SP["tsuba"]
    R0 = T["diameter"] / 2
    zp0, zp1 = T["z_plate"]
    zr0, zr1 = T["mimi"]["z"]
    rw = T["mimi"]["width"]
    ri = R0 - rw
    zc = (zr0 + zr1) / 2
    hz = (zr1 - zr0) / 2
    prof = [(0.0, zp0), (ri - 0.6, zp0), (ri, zr0 + 0.15), (ri + 0.6, zr0)]
    for i in range(1, 12):
        a = -math.pi / 2 + math.pi * i / 12
        prof.append((R0 - 1.2 + 1.2 * math.cos(a), zc + hz * math.sin(a) * 1.0 if abs(math.sin(a)) > 0.99 else zc + (hz) * math.sin(a)))
    prof += [(ri + 0.6, zr1), (ri, zr1 - 0.15), (ri - 0.6, zp1), (0.0, zp1)]
    verts, faces = revolve(prof, 128)
    part("tsuba", verts, faces, COL["iron"], smooth=True)


def build_fuchi():
    F = SP["fuchi"]
    z0, z1 = F["z"]
    ob, ot = F["outline_bottom"], F["outline_top"]
    n = F["superellipse_n"]
    secs = [(z0, ob["depth_x"] - 1.0, ob["width_y"] - 1.0), (z0 + 0.6, ob["depth_x"], ob["width_y"]),
            (z1 - 0.5, ot["depth_x"], ot["width_y"]), (z1, ot["depth_x"] - 1.0, ot["width_y"] - 1.0)]
    rings = [[(x, y, z) for (x, y) in se_pts(d / 2, w / 2, n, 64)] for (z, d, w) in secs]
    part("fuchi", *loft(rings), COL["iron"], smooth=True)


TS = SP["tsuka"]["wrapped_silhouette"]
Z_FB, Z_KT = TS["z_range"]
INSET = SP["tsuka"]["same_core_inset"]
NT = 2.8


def tsuka_dims(z):
    t = (Z_FB - z) / (Z_FB - Z_KT)
    mune = TS["mune_x"]
    ha = lerp(TS["ha_x"]["at_fuchi"], TS["ha_x"]["at_kashira"], t)
    W = lerp(TS["width_y"]["at_fuchi"], TS["width_y"]["at_kashira"], t)
    return (mune + ha) / 2, mune - ha, W


def build_tsuka_core():
    rings = []
    z = Z_FB
    while z > Z_KT - 0.01:
        cx, D, W = tsuka_dims(z)
        rings.append([(cx + x, y, z) for (x, y) in se_pts(D / 2 - INSET, W / 2 - INSET, NT, 64)])
        z -= 4.0
    part("same_core", *loft(rings), COL["same"], smooth=True)


IT = SP["ito"]
PITCH = IT["wrap_pitch"]
OMOTE_X = IT["omote_crossing_z"]
URA_X = IT["ura_crossing_z"]
MEN = SP["menuki"]


def se_point(cx, a, b, n, phi):
    c, s = math.cos(phi), math.sin(phi)
    x = a * math.copysign(abs(c) ** (2.0 / n), c)
    y = b * math.copysign(abs(s) ** (2.0 / n), s)
    gx = (abs(x / a) ** (n - 1)) * math.copysign(1, x) / a if abs(x) > 1e-12 else 0.0
    gy = (abs(y / b) ** (n - 1)) * math.copysign(1, y) / b if abs(y) > 1e-12 else 0.0
    gl = math.hypot(gx, gy) or 1.0
    return Vector((cx + x, y, 0.0)), Vector((gx / gl, gy / gl, 0.0))


def cord_phi(z, sign):
    z0 = Z_FB - 0.25 * PITCH
    return -math.pi / 2 + sign * 2 * math.pi * (z0 - z) / PITCH


def top_cord_at(z, face):
    """which cord ('A' or 'B') is on top at the crossing nearest z on this face; alternates."""
    xs = OMOTE_X if face == "omote" else URA_X
    k = min(range(len(xs)), key=lambda i: abs(xs[i] - z))
    first = "A" if face == "omote" else "B"
    return (first if k % 2 == 0 else ("B" if first == "A" else "A")), abs(xs[k] - z)


def eff_phi(phi_l):
    """linear helix angle -> superellipse parameter such that, in the side view, the cord's lateral position
    x / (D/2) is a triangle wave of z: straight diagonals from each crossing to the edges."""
    w = math.atan2(math.sin(phi_l), math.cos(phi_l))
    ell = 1.0 - abs(w) / (math.pi / 2)
    face = -1.0 if math.sin(phi_l) < 0 else 1.0
    c = math.copysign(abs(ell) ** (NT / 2.0), ell)
    s_ = face * math.sqrt(max(0.0, 1.0 - c * c))
    return math.atan2(s_, c), ell


def cord_lift(z, phi, cname, ell=None):
    s = math.sin(phi)
    face = "omote" if s < 0 else "ura"
    facew = abs(s) ** 6
    top, dz = top_cord_at(z, face)
    lift = 0.0
    if top == cname and dz < 7.0:
        lift += 0.45 * math.cos(math.pi / 2 * dz / 7.0) ** 2 * facew
    edge = abs(math.cos(phi)) ** 4 if ell is None else abs(ell) ** 1.5
    lift += 0.8 * edge   # hishigami
    zm = MEN["omote"]["z_centre"] if face == "omote" else MEN["ura"]["z_centre"]
    dzm = abs(z - zm)
    if dzm < 25.0:
        t_ = 1.0 if dzm <= 14.0 else 1.0 - (dzm - 14.0) / 11.0
        t_ = t_ * t_ * (3 - 2 * t_)          # smoothstep: no kink where the rise starts
        lift += 3.6 * t_ * abs(s) ** 3
    return lift, edge


def build_cord(cname, sign):
    w_face = IT["cord_width_visible"]
    w_edge = IT["cord_width_at_edge_fold"]
    th = IT["thickness"]
    pts = []
    z = Z_FB
    step = 0.1
    while z >= Z_KT:
        cx, D, W = tsuka_dims(z)
        phi, ell = eff_phi(cord_phi(z, sign))
        p, nrm = se_point(cx, D / 2 - INSET, W / 2 - INSET, NT, phi)
        lift, edge = cord_lift(z, phi, cname, ell)
        c = p + nrm * (th + lift)
        c.z = z
        pts.append((c, nrm, lerp(w_face, w_edge, edge)))
        z -= step
    verts, faces = [], []
    for i, (c, nrm, w) in enumerate(pts):
        a = pts[max(0, i - 1)][0]
        b = pts[min(len(pts) - 1, i + 1)][0]
        t = (b - a).normalized()
        wd = nrm.cross(t).normalized()
        verts.append(c + wd * (w / 2))
        verts.append(c - wd * (w / 2))
    for i in range(len(pts) - 1):
        faces.append((2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2))
    me = new_mesh("cord_" + cname, verts, faces, smooth=True, recalc=False)
    # orient normals outward
    me.calc_loop_triangles() if hasattr(me, "calc_loop_triangles") else None
    p0 = me.polygons[len(me.polygons) // 2]
    cen = p0.center
    cx, D, W = tsuka_dims(cen.z)
    if Vector((cen.x - cx, cen.y, 0)).dot(p0.normal) < 0:
        me.flip_normals()
    PARTS["cord_" + cname] = (me, COL["ito"])
    return pts


def build_menuki2():
    """domed lozenge: superellipse outline in (x, z), dome height with a low centre ridge."""
    for face, ysg in (("omote", -1), ("ura", 1)):
        zc = MEN[face]["z_centre"]
        cx, D, W = tsuka_dims(zc)
        y0 = ysg * (W / 2 - INSET - 0.3)
        L, Wd, Hh, rg = MEN["size"]["length"], MEN["size"]["width"], MEN["size"]["height"], MEN["size"]["ridge"]
        rings = []
        NR = 10
        for i in range(NR + 1):
            t = i / NR
            sc = math.cos(t * math.pi / 2) if i < NR else 0.02
            hgt = Hh * math.sin(t * math.pi / 2)
            ring = []
            for (ox, oz) in se_pts(Wd / 2, L / 2, 1.6, 48):
                xr = ox * sc
                zr = oz * sc
                ridge = rg * max(0.0, 1 - abs(xr) / (Wd * 0.18)) * t
                ring.append((cx + xr, y0 + ysg * (hgt + ridge), zc + zr))
            rings.append(ring)
        verts, faces = loft(rings, cap0=True, cap1=True)
        part("menuki_" + face, verts, faces, COL["menuki"], smooth=True)


def build_mekugi():
    K = SP["mekugi"]
    zc = K["z"]
    cx, D, W = tsuka_dims(zc)
    r = K["diameter"] / 2
    yh = W / 2 - INSET + 0.3
    rings = []
    for y in (-yh, yh):
        rings.append([(cx + K["x"] + r * math.cos(2 * math.pi * i / 32), y, zc + r * math.sin(2 * math.pi * i / 32)) for i in range(32)])
    part("mekugi", *loft(rings), COL["mekugi"], smooth=False)


def build_kashira():
    Kd = SP["kashira"]
    z_end, z_top = Kd["z"]
    o = Kd["base_outline"]
    cx = Kd["centre_x"]
    D, W, n = o["depth_x"], o["width_y"], o["superellipse_n"]
    secs = [(z_top, D - 0.8, W - 0.8), (z_top - 0.5, D, W), (z_end + 4.0, D, W)]
    for i in range(1, 9):
        t = i / 8.0
        shrink = 1 - (1 - math.cos(t * math.pi / 2)) * 0.62
        secs.append((z_end + 4.0 - 3.5 * math.sin(t * math.pi / 2) - 0.5 * t, D * shrink, W * shrink))
    rings = [[(cx + x, y, z) for (x, y) in se_pts(d / 2, w / 2, n, 64)] for (z, d, w) in secs]
    part("kashira", *loft(rings), COL["iron"], smooth=True)
    # eyelets (flat brass rings on omote / ura)
    E = Kd["eyelets"]
    ro, ri = E["diameter_outer"] / 2, E["diameter_inner"] / 2
    for face, ysg in (("omote", -1), ("ura", 1)):
        y = ysg * (W / 2 + 0.25)
        outer = [(cx + ro * math.cos(2 * math.pi * i / 32), y, E["z"] + ro * math.sin(2 * math.pi * i / 32)) for i in range(32)]
        inner = [(cx + ri * math.cos(2 * math.pi * i / 32), y, E["z"] + ri * math.sin(2 * math.pi * i / 32)) for i in range(32)]
        verts = outer + inner
        faces = [(i, (i + 1) % 32, 32 + (i + 1) % 32, 32 + i) for i in range(32)]
        part("eyelet_" + face, verts, faces, COL["brass"], recalc=False)
        part("eyelet_hole_" + face, [(cx + ri * math.cos(2 * math.pi * i / 32), y + ysg * -0.05, E["z"] + ri * math.sin(2 * math.pi * i / 32)) for i in range(32)], [tuple(range(32))], COL["hole"], recalc=False)
    # double band over the end: the kashira's Y-Z outline from the omote eyelet, over the end, to the ura eyelet
    half = [(-(W / 2), E["z"]), (-(W / 2), z_end + 4.0)]
    for (z, d, w) in secs[3:]:
        half.append((-(w / 2), z))
    half.append((0.0, secs[-1][0] - 0.05))
    path = half + [(-y, z) for (y, z) in reversed(half[:-1])]
    off = []
    for i in range(len(path)):
        a_ = path[max(0, i - 1)]
        b_ = path[min(len(path) - 1, i + 1)]
        ty, tz = b_[0] - a_[0], b_[1] - a_[1]
        l = math.hypot(ty, tz) or 1e-9
        ny, nz = tz / l, -ty / l          # outward for this traversal direction
        if (path[i][0] * ny + (path[i][1] - (z_end + 5.0)) * nz) < 0:
            ny, nz = -ny, -nz
        off.append((path[i][0] + 0.9 * ny, path[i][1] + 0.9 * nz))
    wb = 2 * IT["cord_width_visible"]
    verts, faces = [], []
    for (y, z) in off:
        verts.append((cx - wb / 2, y, z))
        verts.append((cx + wb / 2, y, z))
    for i in range(len(off) - 1):
        faces.append((2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1))
    part("kashira_band", verts, faces, COL["ito"], smooth=True, recalc=False)


# ------------------------------------------------------------------ saya (built seated, sword frame)
SY = SP["saya"]
RS = SY["mune_outer_radius"]
S_MO = SY["s_mouth"]
S_EN = SY["s_end"]


def saya_dims(s):
    t = (s - S_MO) / (S_EN - S_MO)
    return lerp(SY["depth_x"]["mouth"], SY["depth_x"]["kojiri_end"], t), lerp(SY["width_y"]["mouth"], SY["width_y"]["kojiri_end"], t)


def saya_ring(s, shrink=0.0, N=72):
    D, W = saya_dims(s)
    a = s / R
    nx, nz = -math.cos(a), math.sin(a)
    rc = RS + D / 2
    out = []
    for (u, v) in se_pts(D / 2 - shrink, W / 2 - shrink, 2.4, N):
        rho = rc + u
        out.append((CX + rho * nx, v, CZ + rho * nz))
    return out


def build_saya():
    kg = SY["koiguchi"]["s"]
    kj = SY["kojiri"]["s"]
    # body
    ss = [kg[1]]
    s = kg[1]
    while s < kj[0]:
        s = min(kj[0], s + 8.0)
        ss.append(s)
    part("saya_body", *loft([saya_ring(s) for s in ss]), COL["lacquer"], smooth=True)
    # koiguchi with the habaki pocket
    Hb = SP["habaki"]["section_base"]
    pocket = [(x, y) for (x, y) in se_pts((Hb["x"][1] - Hb["x"][0]) / 2 + 0.1, Hb["y_half"] + 0.1, 4.0, 72)]
    pcx = (Hb["x"][0] + Hb["x"][1]) / 2
    outer0 = saya_ring(kg[0], 0.4)
    outer1 = saya_ring(kg[0] + 0.4)
    outer2 = saya_ring(kg[1])
    a0 = kg[0] / R
    inner0 = [(pcx + x, y, Z_M + kg[0]) for (x, y) in pocket]
    inner1 = [(pcx + x, y, Z_M + kg[0] + 3.0) for (x, y) in pocket]
    verts = outer0 + outer1 + outer2 + inner0 + inner1
    N = 72
    faces = []
    for ring in range(2):
        for j in range(N):
            a, b = ring * N + j, ring * N + (j + 1) % N
            faces.append((a, b, b + N, a + N))
    for j in range(N):   # mouth annulus
        faces.append((3 * N + j, 3 * N + (j + 1) % N, (j + 1) % N, j))
    for j in range(N):   # pocket wall
        faces.append((3 * N + (j + 1) % N, 3 * N + j, 4 * N + j, 4 * N + (j + 1) % N))
    faces.append(tuple(range(4 * N, 5 * N)))  # pocket floor (dark plug below)
    faces.append(tuple(reversed(range(2 * N, 3 * N))))
    part("koiguchi", verts, faces, COL["horn"], smooth=True)
    part("pocket_floor", [(pcx + x, y, Z_M + kg[0] + 2.9) for (x, y) in pocket], [tuple(range(N))], COL["hole"], recalc=False)
    # kojiri with round-over at the end
    rings = []
    ss = [kj[0] + i * (kj[1] - 4.0 - kj[0]) / 6 for i in range(7)]
    for s in ss:
        rings.append(saya_ring(s))
    for i in range(1, 9):
        t = i / 8.0
        rings.append(saya_ring(kj[1] - 4.0 + 4.0 * math.sin(t * math.pi / 2), shrink=4.0 * (1 - math.cos(t * math.pi / 2))))
    part("kojiri", *loft(rings), COL["horn"], smooth=True)
    # kurikata
    K = SY["kurikata"]
    sk = K["s_centre"]
    D, W = saya_dims(sk)
    a = sk / R
    nx, nz = -math.cos(a), math.sin(a)
    tx, tz = math.sin(a), math.cos(a)
    rc = RS + D / 2 + K["radial_offset_toward_ha"]
    base = -(W / 2) + 1.5
    prof = K["size"]
    rings = []
    for (hh, sc) in ((0.0, 1.0), (prof["proud_of_face"] * 0.55, 1.0), (prof["proud_of_face"] * 0.8, 0.93),
                     (prof["proud_of_face"] * 0.93, 0.78), (prof["proud_of_face"], 0.5)):
        ring = []
        for (al, ra) in se_pts(prof["along"] / 2 * sc, prof["radial_x"] / 2 * (0.6 + 0.4 * sc), 2.2, 48):
            rho = rc + ra
            px, pz = CX + rho * nx + al * tx, CZ + rho * nz + al * tz
            ring.append((px, base - hh - (1.5 if hh > 0 else 0.0), pz))
        rings.append(ring)
    part("kurikata", *loft(rings), COL["horn"], smooth=True)
    # shitodome rings on both radial faces of the knob (oval 18 x 8 outer, 14 x 4.5 hole)
    Sd = K["shitodome"]
    hz = base - 1.5 - prof["proud_of_face"] * 0.45
    for side, sg in (("ha", 1), ("mune", -1)):
        rho = rc + sg * (prof["radial_x"] / 2 + 0.35)
        def pt(al, yy):
            return (CX + rho * nx + al * tx, yy, CZ + rho * nz + al * tz)
        outer = [pt(x, hz + y) for (x, y) in se_pts(Sd["outer"][0] / 2, Sd["outer"][1] / 2, 2.0, 40)]
        inner = [pt(x, hz + y) for (x, y) in se_pts(K["hole"]["slot"][0] / 2, K["hole"]["slot"][1] / 2, 2.0, 40)]
        faces = [(i, (i + 1) % 40, 40 + (i + 1) % 40, 40 + i) for i in range(40)]
        part("shitodome_" + side, outer + inner, faces, COL["brass"], recalc=False)
        rho2 = rho + sg * 0.05
        hole = [(CX + rho2 * nx + x * tx, hz + y, CZ + rho2 * nz + x * tz) for (x, y) in se_pts(K["hole"]["slot"][0] / 2, K["hole"]["slot"][1] / 2, 2.0, 40)]
        part("shitodome_hole_" + side, hole, [tuple(range(40))], COL["hole"], recalc=False)


# ------------------------------------------------------------------ build all parts
build_blade()
build_overlays()
build_habaki()
build_seppa()
build_tsuba()
build_fuchi()
build_tsuka_core()
ptsA = build_cord("A", +1)
ptsB = build_cord("B", -1)
build_menuki2()
build_mekugi()
build_kashira()
build_saya()

SWORD = ["blade", "habaki", "seppa_blade", "seppa_tsuka", "tsuba", "fuchi", "same_core", "cord_A", "cord_B",
         "menuki_omote", "menuki_ura", "mekugi", "kashira", "eyelet_omote", "eyelet_ura", "eyelet_hole_omote",
         "eyelet_hole_ura", "kashira_band"]
OMOTE_OV = ["hamon_omote", "nioi_omote", "shinogi_omote", "yokote_omote", "muneline_omote"]
URA_OV = ["hamon_ura", "nioi_ura", "shinogi_ura", "yokote_ura", "muneline_ura"]
SAYA = ["saya_body", "koiguchi", "pocket_floor", "kojiri", "kurikata", "shitodome_ha", "shitodome_mune",
        "shitodome_hole_ha", "shitodome_hole_mune"]

# ------------------------------------------------------------------ measurements on the model
def measure_diamond():
    """omote face, 4th diamond (between omote crossings 3 and 4); side-view projection (x, z), y < 0."""
    za, zb = OMOTE_X[3], OMOTE_X[4]
    quads = []
    for pts in (ptsA, ptsB):
        for i in range(len(pts) - 1):
            c0, n0, w0 = pts[i]
            if c0.z > za + 2 or c0.z < zb - 2 or c0.y > 0:
                continue
            c1, n1, w1 = pts[i + 1]
            t = (c1 - c0).normalized()
            wd0 = n0.cross(t).normalized() * (w0 / 2)
            wd1 = n1.cross(t).normalized() * (w1 / 2)
            quads.append([(c0 + wd0).xz, (c0 - wd0).xz, (c1 - wd1).xz, (c1 + wd1).xz])

    def covered(x, z):
        for q in quads:
            inside = False
            j = 3
            for i in range(4):
                xi, zi = q[i]
                xj, zj = q[j]
                if ((zi > z) != (zj > z)) and (x < (xj - xi) * (z - zi) / ((zj - zi) or 1e-12) + xi):
                    inside = not inside
                j = i
            if inside:
                return True
        return False

    zc = (za + zb) / 2
    cx, D, W = tsuka_dims(zc)
    # along: on the face centre line x = cx
    zs = [za - i * 0.05 for i in range(int((za - zb) / 0.05) + 1)]
    free = [z for z in zs if not covered(cx, z)]
    along = (max(free) - min(free)) if free else 0.0
    # across: at the diamond's mid z, x from the centre outwards until covered (side view silhouette)
    xs = [cx - D / 2 + i * 0.05 for i in range(int(D / 0.05) + 1)]
    freex = [x for x in xs if not covered(x, zc)]
    across = (max(freex) - min(freex)) if freex else 0.0
    edge_gap = 0.0
    return {"diamond_along_mm": round(along, 2), "diamond_across_mm": round(across, 2), "diamond_mid_z": round(zc, 2),
            "silhouette_depth_at_mid_mm": round(D, 2), "note": "side-view projection of the cords on the omote face; the across value reaches the silhouette where the opening touches the face edges"}


MEAS = measure_diamond()
MEAS["blade_tip_xz"] = list(mune_pt(S_TIP))
MEAS["yokote_station"] = S_Y
MEAS["sheet_res_px"] = RES_X
json.dump(MEAS, open(os.path.join(HERE, "sheet_measures.json"), "w"), indent=2)
print("MEASURE", MEAS)

# ------------------------------------------------------------------ views
SHEET = bpy.data.collections.new("SHEET")
SC.collection.children.link(SHEET)


def place(names, rot, scale, off, tag):
    """rot: 3x3 Matrix sword->sheet (proper rotation). sheet = off + scale * rot @ p"""
    m = Matrix.Translation(Vector(off)) @ Matrix.Diagonal((scale, scale, scale, 1.0)) @ rot.to_4x4()
    for n in names:
        me, colr = PARTS[n]
        ob = bpy.data.objects.new(tag + "_" + n, me)
        ob.matrix_world = m
        ob.color = colr
        SHEET.objects.link(ob)


def rotm(cols):
    """cols = images of sword X, Y, Z axes in sheet coords."""
    return Matrix(((cols[0][0], cols[1][0], cols[2][0]), (cols[0][1], cols[1][1], cols[2][1]), (cols[0][2], cols[1][2], cols[2][2])))


SIDE = rotm(((0, -1, 0), (0, 0, -1), (1, 0, 0)))      # from -Y (omote), handle left, edge up
TOP = rotm(((0, 0, -1), (0, 1, 0), (1, 0, 0)))        # from the ha edge (above, edge-up), ura up
END = rotm(((0, -1, 0), (1, 0, 0), (0, 0, 1)))        # from the tip end (right view)
MOUTHV = rotm(((0, -1, 0), (-1, 0, 0), (0, 0, -1)))   # looking into the koiguchi (from -Z), omote right
URAV = rotm(((0, -1, 0), (0, 0, 1), (-1, 0, 0)))      # from +Y (ura), handle right, edge up

for r_ in (SIDE, TOP, END, MOUTHV, URAV):
    assert abs(r_.determinant() - 1.0) < 1e-9, r_


def side_pt(off, scale, x, z):
    p = SIDE @ Vector((x, 0, z))
    return (off[0] + scale * p.x, off[1] + scale * p.y)


def top_pt(off, scale, y, z):
    p = TOP @ Vector((0, y, z))
    return (off[0] + scale * p.x, off[1] + scale * p.y)


# ---- annotation primitives (sheet coords, z = 60)
ZA = 60.0
ANN = []


def ann_mesh(name, verts2, faces, colour, z=ZA):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x, y, z) for (x, y) in verts2], [], faces)
    ob = bpy.data.objects.new(name, me)
    ob.color = colour
    SHEET.objects.link(ob)
    return ob


def seg(p, q, w=0.5, colour=None, name="seg"):
    colour = colour or COL["dim"]
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy) or 1e-9
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    ann_mesh(name, [(p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny), (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)], [(0, 1, 2, 3)], colour)


def arrow(tip, dirv, size=3.2, colour=None):
    colour = colour or COL["dim"]
    dx, dy = dirv
    L = math.hypot(dx, dy) or 1e-9
    dx, dy = dx / L, dy / L
    bx, by = tip[0] - dx * size, tip[1] - dy * size
    nx, ny = -dy * size * 0.33, dx * size * 0.33
    ann_mesh("arrow", [tip, (bx + nx, by + ny), (bx - nx, by - ny)], [(0, 1, 2)], colour)


def text(body, pos, size=7.0, align="CENTER", colour=None, rot=0.0, name="txt", valign="CENTER"):
    colour = colour or COL["ink"]
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = body
    cu.size = size
    cu.align_x = align
    cu.align_y = valign
    ob = bpy.data.objects.new(name, cu)
    ob.location = (pos[0], pos[1], ZA + 1)
    ob.rotation_euler = (0, 0, rot)
    ob.color = colour
    SHEET.objects.link(ob)
    return ob


def dim(p, q, offset, label, size=6.0, ext=True, colour=None, txt_off=4.0):
    """linear dimension between sheet points p and q, offset perpendicular (signed)."""
    colour = colour or COL["dim"]
    dx, dy = q[0] - p[0], q[1] - p[1]
    L = math.hypot(dx, dy) or 1e-9
    ux, uy = dx / L, dy / L
    nx, ny = -uy, ux
    p2 = (p[0] + nx * offset, p[1] + ny * offset)
    q2 = (q[0] + nx * offset, q[1] + ny * offset)
    if ext:
        sg = 1 if offset >= 0 else -1
        seg((p[0] + nx * sg * 1.5, p[1] + ny * sg * 1.5), (p2[0] + nx * sg * 2.5, p2[1] + ny * sg * 2.5), 0.3, colour)
        seg((q[0] + nx * sg * 1.5, q[1] + ny * sg * 1.5), (q2[0] + nx * sg * 2.5, q2[1] + ny * sg * 2.5), 0.3, colour)
    seg(p2, q2, 0.4, colour)
    arrow(p2, (-ux, -uy), colour=colour)
    arrow(q2, (ux, uy), colour=colour)
    ang = math.atan2(uy, ux)
    if ang > math.pi / 2 + 1e-6:
        ang -= math.pi
    if ang < -math.pi / 2 - 1e-6:
        ang += math.pi
    sg = 1 if offset >= 0 else -1
    mx, my = (p2[0] + q2[0]) / 2, (p2[1] + q2[1]) / 2
    tx, ty = -math.sin(ang), math.cos(ang)
    text(label, (mx + tx * txt_off * (1 if sg > 0 else -1), my + ty * txt_off * (1 if sg > 0 else -1)), size, rot=ang, colour=colour)


def leader(p, q, label, size=6.0, align="LEFT", colour=None):
    colour = colour or COL["ink"]
    seg(p, q, 0.3, colour)
    ann_mesh("dot", [(p[0] + 0.9 * math.cos(i * math.pi / 4), p[1] + 0.9 * math.sin(i * math.pi / 4)) for i in range(8)], [tuple(range(8))], colour)
    text(label, (q[0] + (1.5 if align == "LEFT" else -1.5), q[1]), size, align=align, colour=colour)


def ruler(x0, y0, length_mm, scale, label, major=100, minor=10):
    """ruler of real length length_mm drawn at the given scale."""
    seg((x0, y0), (x0 + length_mm * scale, y0), 0.6, COL["ink"])
    n = int(length_mm / minor)
    for i in range(n + 1):
        v = i * minor
        x = x0 + v * scale
        h = 6.0 if v % major == 0 else (3.5 if v % (major / 2) == 0 else 2.0)
        seg((x, y0), (x, y0 + h), 0.35, COL["ink"])
        if v % major == 0:
            text("%d" % v, (x, y0 + h + 4.0), 4.5)
    text(label, (x0 + length_mm * scale + 4, y0 + 2), 5.0, align="LEFT")


def title(pos, body, size=10.0):
    text(body, pos, size, align="LEFT", valign="BOTTOM")


# ---------------------------------------------------------------- LAYOUT (sheet mm, sheet is 1400 x 1200)
SW = 1400.0
X0 = 70.0                                   # kashira end of the 1:1 views sits at sheet X = X0
OX = X0 - SP["overall"]["kashira_end_z"]    # sheet X of sword z = 0
END_X = 1180.0
ROW_A_TOP, ROW_A = 1100.0, 990.0
ROW_B_TOP, ROW_B = 777.0, 735.0
ROW_C_TOP, ROW_C = 550.0, 465.0
tip_x, tip_z = SP["blade"]["tip_xz"]
kend = SP["overall"]["kashira_end_z"]

# ---- Row A: katana, drawn
place(SWORD + OMOTE_OV, SIDE, 1.0, (OX, ROW_A, 0), "A_side")
place(SWORD, TOP, 1.0, (OX, ROW_A_TOP, 0), "A_top")
place(SWORD, END, 1.0, (END_X, ROW_A, 0), "A_end")
title((30, 1140), "1  KATANA (drawn)  -  1:1: side (omote, edge up), top (seen from the ha), end (from the tip)", 8.0)

pA = lambda x, z: side_pt((OX, ROW_A), 1.0, x, z)
dim(pA(0, kend), pA(0, tip_z), -150, "overall %.1f along the tsuka axis (chord kashira-tip %.1f)" % (SP["overall"]["length_along_Z"], SP["overall"]["length_chord_kashira_to_tip"]), 6.0)
dim(pA(0, kend), pA(0, SP["fuchi"]["z"][1]), -120, "tsuka %.0f (fuchi top - kashira end)" % SP["tsuka"]["length_fuchi_top_to_kashira_end"], 5.0)
mm_ = pA(B["mune_machi_xz"][0], B["mune_machi_xz"][1])
tp_ = pA(tip_x, tip_z)
seg(mm_, tp_, 0.3, COL["red"])
dim(mm_, tp_, -40, "nagasa %.1f (straight chord, mune-machi to tip)" % B["nagasa_chord"], 5.5)
mid_s = S_TIP / 2
mx_, mz_ = mune_pt(mid_s)
# foot of the perpendicular from the mid mune point onto the chord
ax, az = B["mune_machi_xz"]
dx_, dz_ = tip_x - ax, tip_z - az
tt = ((mx_ - ax) * dx_ + (mz_ - az) * dz_) / (dx_ * dx_ + dz_ * dz_)
fx, fz = ax + tt * dx_, az + tt * dz_
seg(pA(mx_, mz_), pA(fx, fz), 0.4, COL["red"])
text("sori %.1f" % B["sori"], (pA(fx, fz)[0] + 14, (pA(fx, fz)[1] + pA(mx_, mz_)[1]) / 2), 5.0, colour=COL["red"])
w0e, w0m = edge_xz(34.0), mune_pt(34.0)
dim(pA(*w0m), pA(*w0e), -14, "motohaba %.1f" % B["motohaba"], 4.5)
wye, wym = edge_xz(S_Y), mune_pt(S_Y)
dim(pA(*wym), pA(*wye), 14, "sakihaba %.1f" % B["sakihaba_at_yokote"], 4.5)
leader(pA(*u_xz(250, 0.7)), (pA(250, 250)[0] + 10, ROW_A - 62), "iori-mune (peaked spine)", 5.0)
leader(pA(*u_xz(330, 4.5)), (pA(330, 330)[0] + 40, ROW_A - 62), "shinogi-ji (burnished)", 5.0)
leader(pA(*u_xz(420, 0.27 * blade_params(420)[0])), (pA(0, 420)[0] + 6, ROW_A + 44), "shinogi ridge 0.27 w from the mune", 5.0)
leader(pA(*u_xz(520, blade_params(520)[0] - 2.5)), (pA(0, 520)[0] + 40, ROW_A + 32), "hamon: plain ko-notare 6.5 -> 5.0 from the edge, +-1.0 wave; frosted ha", 5.0)
leader(pA(*u_xz(S_Y, 15.0)), (pA(0, S_Y)[0] - 10, ROW_A + 52), "yokote; chu-kissaki %.0f; ko-maru boshi" % B["kissaki"]["length_on_mune_arc"], 5.0, align="RIGHT")
leader(pA(-8, 72), (pA(0, 72)[0] + 10, ROW_A + 62), "habaki 28, brass", 5.0)
leader(pA(-30, 54), (pA(0, 54)[0] - 4, ROW_A + 62), "tsuba 76 round, plain iron", 5.0, align="RIGHT")
leader(pA(-15, 44), (pA(0, 44)[0] - 12, ROW_A + 50), "fuchi 13, iron; seppa 1.5 x2, brass", 5.0, align="RIGHT")
leader(pA(-4, MEN["omote"]["z_centre"]), (pA(0, MEN["omote"]["z_centre"])[0] - 12, ROW_A + 38), "omote menuki (3rd diamond from the fuchi)", 5.0, align="RIGHT")
leader(pA(0, SP["mekugi"]["z"]), (pA(0, SP["mekugi"]["z"])[0] + 6, ROW_A - 45), "mekugi 6, bamboo", 5.0)
leader(pA(-12, -100), (pA(0, -100)[0] - 6, ROW_A + 26), "black ito, hineri-maki: 9 crossings, 8 diamonds per face", 5.0, align="RIGHT")
leader(pA(0, -212), (pA(0, -212)[0] + 4, ROW_A - 35), "kashira 11, iron; ito over the end", 5.0)
dim((END_X - 38, ROW_A - 95), (END_X + 38, ROW_A - 95), 0, "tsuba %.0f" % SP["tsuba"]["diameter"], 4.5, ext=False)
text("end view, from the tip", (END_X, ROW_A + 50), 5.0)
pT = lambda y, z: top_pt((OX, ROW_A_TOP), 1.0, y, z)
text("kasane (thickness) 7.0 at the machi -> 5.0 at the yokote; habaki 12.0 -> 9.8 thick", (pT(0, 330)[0], ROW_A_TOP + 14), 5.0)
Wf = SP["tsuka"]["wrapped_silhouette"]["width_y"]
dim(pT(-Wf["at_fuchi"] / 2, 30), pT(Wf["at_fuchi"] / 2, 30), 18, "%.1f" % Wf["at_fuchi"], 4.5)
dim(pT(-Wf["at_kashira"] / 2, -190), pT(Wf["at_kashira"] / 2, -190), 18, "%.1f" % Wf["at_kashira"], 4.5)
text("top view (from the ha)", (pT(0, -120)[0], ROW_A_TOP + 26), 5.0)
ruler(X0, 818, 1000, 1.0, "mm (1:1 for rows 1-3)")

# ---- Row B: saya
place(SAYA, SIDE, 1.0, (OX, ROW_B, 0), "B_side")
place(SAYA, TOP, 1.0, (OX, ROW_B_TOP, 0), "B_top")
place(SAYA, END, 1.0, (END_X, ROW_B, 0), "B_end")
title((30, 800), "2  SAYA  -  1:1: side (omote), top (from the ha), end (from the kojiri). Black roiro lacquer; horn koiguchi, kurikata, kojiri; no sageo", 8.0)
pB = lambda x, z: side_pt((OX, ROW_B), 1.0, x, z)
kg = SY["koiguchi"]["s"]
kj = SY["kojiri"]["s"]
D0, W0 = saya_dims(kg[0])
D1, W1 = saya_dims(S_EN)
dim(pB(*mune_pt(kg[0], RS)), pB(*mune_pt(S_EN, RS)), -34, "saya %.1f along the blade's mune arc, mouth to kojiri end" % SY["length_on_blade_mune_arc"], 5.5)
dim(pB(*mune_pt(kg[0] + 0.5, RS)), pB(*mune_pt(kg[0] + 0.5, RS + D0)), 10, "%.1f" % D0, 4.5)
dim(pB(*mune_pt(S_EN - 0.5, RS)), pB(*mune_pt(S_EN - 0.5, RS + D1)), -10, "%.1f" % D1, 4.5)
dim(pB(*mune_pt(kg[0], RS + D0)), pB(*mune_pt(kg[1], RS + D0)), 8, "koiguchi 20", 4.5)
dim(pB(*mune_pt(kj[0], RS + D1)), pB(*mune_pt(kj[1], RS + D1)), 8, "kojiri 28", 4.5)
dim(pB(*mune_pt(kg[0], RS)), pB(*mune_pt(SY["kurikata"]["s_centre"], RS)), -12, "kurikata 80", 4.5)
kk = pB(*mune_pt(SY["kurikata"]["s_centre"], RS + D0 / 2 + 3))
leader(kk, (300, ROW_B + 30), "kurikata: horn knob 30 x 11, 9 proud, brass shitodome; sageo omitted", 5.0, align="RIGHT")
pBT = lambda y, z: top_pt((OX, ROW_B_TOP), 1.0, y, z)
dim(pBT(-W0 / 2, Z_M + kg[0] + 3), pBT(W0 / 2, Z_M + kg[0] + 3), -14, "%.1f" % W0, 4.5)
dim(pBT(-W1 / 2, Z_M + S_EN - 30), pBT(W1 / 2, Z_M + S_EN - 30), 14, "%.1f" % W1, 4.5)
text("end view, from the kojiri", (END_X, ROW_B + 40), 5.0)

# ---- Row C: sheathed
place(SWORD + SAYA, SIDE, 1.0, (OX, ROW_C, 0), "C_side")
place(SWORD + SAYA, TOP, 1.0, (OX, ROW_C_TOP, 0), "C_top")
title((30, 590), "3  SHEATHED  -  1:1: seppa 0.3 from the koiguchi, habaki fully inside, tip 10 short of the cavity end; draw = rotation about the arc centre", 8.0)
pC = lambda x, z: side_pt((OX, ROW_C), 1.0, x, z)
leader(pC(-20, Z_M + 0.15), (pC(0, Z_M)[0] - 30, ROW_C + 52), "seat gap 0.3", 5.0, align="RIGHT")
for line in (mune_pt, edge_xz):
    pts = [pC(*line(s)) for s in [SP["habaki"]["length"] + i * (S_TIP - SP["habaki"]["length"]) / 300 for i in range(301)]]
    for i in range(0, 300, 4):
        seg(pts[i], pts[i + 2], 0.45, COL["red"])
tipc = pC(tip_x, tip_z)
leader(tipc, (tipc[0] - 70, ROW_C - 90), "blade inside (dashed): tip 10 short of the cavity end", 5.0, align="RIGHT")
place(SWORD + SAYA, END, 1.0, (END_X, ROW_C, 0), "C_end")

# ---- Row D: details
title((30, 345), "4  DETAILS", 8.0)
SC2 = 2.0
OX2 = 90.0 + 215 * SC2
WRAP_Y, WRAP_EDGE_Y = 270.0, 140.0
WRAP = ["fuchi", "seppa_tsuka", "same_core", "cord_A", "cord_B", "menuki_omote", "menuki_ura", "mekugi", "kashira",
        "eyelet_omote", "eyelet_ura", "eyelet_hole_omote", "eyelet_hole_ura", "kashira_band"]
place(WRAP, SIDE, SC2, (OX2, WRAP_Y, 0), "D_wrap")
text("4a  tsuka wrap, omote, 2:1 (crossings numbered from the fuchi)", (60, 332), 5.5, align="LEFT")
pW = lambda x, z: side_pt((OX2, WRAP_Y), SC2, x, z)
for k, zc in enumerate(OMOTE_X):
    p = pW(-18.5, zc)
    seg((p[0], p[1] + 3), (p[0], p[1] + 9), 0.3, COL["dim"])
    text(str(k + 1), (p[0], p[1] + 13), 4.0, colour=COL["dim"])
dim(pW(18.5, OMOTE_X[3]), pW(18.5, OMOTE_X[4]), 0, "", 4.0, ext=False)
text("pitch %.2f" % PITCH, (pW(18.5, (OMOTE_X[3] + OMOTE_X[4]) / 2)[0], pW(18.5, 0)[1] - 7), 4.5, colour=COL["dim"])
dmz = (OMOTE_X[3] + OMOTE_X[4]) / 2
leader(pW(0, dmz), (pW(0, dmz)[0] + 30, WRAP_Y - 52), "diamond opening %.1f along x %.1f across" % (MEAS["diamond_along_mm"], MEAS["diamond_across_mm"]), 4.5)
leader(pW(0, MEN["omote"]["z_centre"]), (pW(0, MEN["omote"]["z_centre"])[0] + 20, WRAP_Y - 62), "menuki 30 x 10 x 3.2 (ito rises over its ends)", 4.5)
leader(pW(0, SP["mekugi"]["z"]), (pW(0, SP["mekugi"]["z"])[0] + 14, WRAP_Y - 52), "mekugi", 4.5)
ruler(60, 195, 100, SC2, "mm at 2:1", major=50, minor=5)
place(WRAP, TOP, SC2, (OX2, WRAP_EDGE_Y, 0), "D_wrapedge")
text("4b  the same tsuka seen from the ha edge, 2:1: a cord crosses each edge every half pitch, over a hishigami", (60, 100), 5.0, align="LEFT")

# 4c kissaki 3:1
SC3 = 3.0
s_k0 = S_TIP - 75.0
KIS = ["blade_kis"] + [n + "_kis" for n in OMOTE_OV]
anchor = mune_pt(S_TIP - 37.0)
pa = SIDE @ Vector((anchor[0], 0, anchor[1]))
KOFF = (815.0 - SC3 * pa.x, 250.0 - SC3 * pa.y, 0)


def cut_blade(s0):
    stations = [s0 + i * (S_Y - s0) / 20 for i in range(21)] + [S_Y + (S_TIP - S_Y) * (1 - (1 - i / 60.0) ** 1.5) for i in range(1, 60)]
    rings = [blade_section(s)[0] for s in stations]
    verts, faces = loft(rings, cap0=True, cap1=False)
    tip = mune_pt(S_TIP)
    verts.append((tip[0], 0.0, tip[1]))
    n = len(rings[0])
    base = (len(rings) - 1) * n
    for j in range(n):
        faces.append((base + j, base + (j + 1) % n, len(verts) - 1))
    part("blade_kis", verts, faces, COL["ji"])
    a = s0 / R
    tx, tz = math.sin(a), math.cos(a)
    mx, mz = mune_pt(s0)
    for name in OMOTE_OV:
        me, colr = PARTS[name]
        bm = bmesh.new()
        bm.from_mesh(me)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(mx, 0, mz), plane_no=(-tx, 0, -tz), clear_outer=True)
        me2 = bpy.data.meshes.new(name + "_kis")
        bm.to_mesh(me2)
        bm.free()
        PARTS[name + "_kis"] = (me2, colr)


cut_blade(s_k0)
place(KIS, SIDE, SC3, KOFF, "D_kis")
text("4c  kissaki, omote, 3:1", (690, 332), 5.5, align="LEFT")
pK = lambda x, z: side_pt(KOFF, SC3, x, z)
dim(pK(*mune_pt(S_Y)), pK(*mune_pt(S_TIP)), -14, "kissaki %.0f on the mune arc" % B["kissaki"]["length_on_mune_arc"], 4.5)
leader(pK(*u_xz(S_Y, 16.0)), (pK(*u_xz(S_Y, 16.0))[0] - 25, 318), "yokote", 4.5, align="RIGHT")
leader(pK(*u_xz(S_TIP - 9, 2.6)), (pK(*u_xz(S_TIP - 9, 2.6))[0] + 8, 300), "ko-maru boshi, kaeri 5", 4.5)
leader(pK(*u_xz(S_TIP - 20, 0.27 * blade_params(S_TIP - 20)[0])), (pK(*u_xz(S_TIP - 20, 3))[0] + 18, 205), "ko-shinogi", 4.5)
ruler(700, 165, 50, SC3, "mm at 3:1", major=10, minor=2)

# 4d sections
SECX = 1010.0
text("4d  sections (mune left)", (SECX - 10, 332), 5.5, align="LEFT")
for i, (s, lab) in enumerate(((0.0, "machi"), (S_Y / 2, "mid"), (S_Y, "yokote"))):
    _, uv = blade_section(s)
    cxs, cys = SECX, 312 - i * 26
    pts2 = [(cxs + 3.0 * u, cys + 3.0 * y) for (u, y) in uv]
    ann_mesh("sec", pts2, [tuple(range(len(pts2)))], COL["ji"], z=ZA - 5)
    for j in range(len(pts2)):
        seg(pts2[j], pts2[(j + 1) % len(pts2)], 0.3, COL["ink"])
    w, k, rf, nk, e = blade_params(s)
    text("%s 3:1  w %.1f  k %.1f" % (lab, w, k), (cxs + 3.0 * w + 6, cys), 4.5, align="LEFT")
cxs, cys = SECX + 38, 215
cx_, D_, W_ = tsuka_dims(Z_FB)
ann_mesh("tsec", [(cxs + 2 * x, cys + 2 * y) for (x, y) in se_pts(D_ / 2, W_ / 2, NT, 64)], [tuple(range(64))], COL["ito"], z=ZA - 5)
ann_mesh("tsec2", [(cxs + 2 * x, cys + 2 * y) for (x, y) in se_pts(D_ / 2 - INSET, W_ / 2 - INSET, NT, 64)], [tuple(range(64))], COL["same"], z=ZA - 4)
text("tsuka at the fuchi, 2:1: %.1f x %.1f over the ito" % (D_, W_), (cxs + 44, cys), 4.5, align="LEFT")
cxs2, cys2 = SECX + 40, 130
ann_mesh("ssec", [(cxs2 + 2 * x, cys2 + 2 * y) for (x, y) in se_pts(D0 / 2, W0 / 2, 2.4, 72)], [tuple(range(72))], COL["horn"], z=ZA - 5)
Hb = SP["habaki"]["section_base"]
pcx_ = (Hb["x"][0] + Hb["x"][1]) / 2
ann_mesh("ssec2", [(cxs2 + 2 * (pcx_ + x), cys2 + 2 * y) for (x, y) in se_pts((Hb["x"][1] - Hb["x"][0]) / 2 + 0.1, Hb["y_half"] + 0.1, 4.0, 72)], [tuple(range(72))], COL["hole"], z=ZA - 4)
text("koiguchi 2:1: %.1f x %.1f, habaki pocket %.1f x %.1f" % (D0, W0, Hb["x"][1] - Hb["x"][0] + 0.2, 2 * Hb["y_half"] + 0.2), (cxs2 + 46, cys2), 4.5, align="LEFT")

# 4e tsuba from the blade side, 4f into the koiguchi
place(["tsuba", "seppa_blade", "habaki"], END, 1.5, (1320, 270, 0), "D_tsuba")
text("4e  tsuba, from the blade side, 1.5:1", (1255, 336), 5.0, align="LEFT")
place(["koiguchi", "pocket_floor", "kurikata", "shitodome_ha", "shitodome_mune", "shitodome_hole_ha", "shitodome_hole_mune"],
      MOUTHV, 1.5, (1325, 80, -300), "D_mouth")
text("4f  into the koiguchi, 1.5:1 (kurikata right)", (1255, 30), 5.0, align="LEFT")

# ---- header
title((30, 1172), "BASIC KATANA + SAYA  -  DESIGN SHEET  (the reference for SM_Katana and SM_Katana_Saya)", 12.0)
text("All dimensions mm, from katana_spec.json v%s (%s). Frame: Grip socket at the origin, +Z toward the blade, +X mune, -Y omote. Shinogi-zukuri, iori-mune, chu-kissaki, torii-zori (circular mune arc R %.1f), no hi." % (
    SP["meta"]["version"], SP["meta"]["date"], R), (30, 1160), 5.0, align="LEFT")
text("Finishes: steel (polished ji, burnished shinogi-ji and mune, frosted hamon); brass habaki and seppa; blackened iron tsuba, fuchi, kashira; antique-brass menuki; black ito over white same; black roiro saya with black horn fittings.", (30, 1151), 5.0, align="LEFT")

# ------------------------------------------------------------------ camera, render
W_SHEET, H_SHEET = SW, 1200.0
cam_d = bpy.data.cameras.new("cam")
cam_d.type = "ORTHO"
cam_d.ortho_scale = W_SHEET
cam_d.clip_start = 1.0
cam_d.clip_end = 5000.0
cam = bpy.data.objects.new("cam", cam_d)
cam.location = (W_SHEET / 2, H_SHEET / 2, 1500.0)
SC.collection.objects.link(cam)
SC.camera = cam
SC.render.resolution_x = RES_X
SC.render.resolution_y = int(RES_X * H_SHEET / W_SHEET)
SC.render.resolution_percentage = 100
SC.render.engine = "BLENDER_WORKBENCH"
sh = SC.display.shading
sh.light = "STUDIO"
sh.color_type = "OBJECT"
sh.show_cavity = True
sh.cavity_type = "WORLD"
sh.show_object_outline = True
sh.object_outline_color = (0.0, 0.0, 0.0)
sh.show_specular_highlight = True
try:
    SC.display.render_aa = "16"
except Exception:
    pass
wd = bpy.data.worlds.new("w")
wd.color = (1.0, 1.0, 1.0)
SC.world = wd
SC.view_settings.view_transform = "Standard"
SC.render.image_settings.file_format = "PNG"
SC.render.filepath = OUT
if BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.render.render(write_still=True)
print("WROTE", OUT)
