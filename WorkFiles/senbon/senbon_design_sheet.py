"""Senbon design sheet: builds the senbon_spec.json design as quick primitives in headless Blender 5.2,
measures volume / mass / centre of mass on the meshes (cross-checked against an analytic integral),
writes the 'derived' block back into the spec, and renders SENBON_DESIGN_SHEET.png:
orthographic side / top / end views at 1:1 (12 px = 1 mm) with a ruler, 5:1 and 3:1 details,
and a 3/4 sketch render, plus the frozen spike for contrast.

Run:
  "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python WorkFiles/senbon/senbon_design_sheet.py
"""
import json
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/senbon"
SPEC_PATH = ROOT + "/senbon_spec.json"
OUT = ROOT + "/SENBON_DESIGN_SHEET.png"
TMP = ROOT + "/sheet_tmp"
MM = 0.001
STEEL_DENSITY = 7.85e-3   # g / mm3
COTTON_DENSITY = 0.6e-3   # g / mm3 (wound thread layer, effective)

SPEC = json.load(open(SPEC_PATH, encoding="utf-8"))
NEEDLE = SPEC["items"]["SM_Senbon_Needle"]["profile"]
HEAVY = SPEC["items"]["SM_Senbon_Heavy"]["profile"]
SPIKE = SPEC["comparison_reference"]["SM_Shuriken_Spike"]

# ----------------------------------------------------------------------------------------------- profiles
N_L2 = SPEC["items"]["SM_Senbon_Needle"]["overall_length_mm"] / 2.0      # 65
N_SH = NEEDLE["shoulder_abs_x_mm"]                                        # 50
N_DB = NEEDLE["belly_diameter_mm"]                                        # 2.8
N_DS = NEEDLE["shoulder_diameter_mm"]                                     # 2.3


def needle_r(x):
    ax = abs(x)
    if ax <= N_SH:
        return 0.5 * (N_DS + (N_DB - N_DS) * (1.0 - (ax / N_SH) ** 2))
    return 0.5 * N_DS * max(0.0, (N_L2 - ax) / (N_L2 - N_SH))


def needle_profile(n_body=24):
    xs = [-N_L2, -N_SH]
    xs += list(np.linspace(-N_SH, N_SH, 2 * n_body + 1)[1:-1])
    xs += [N_SH, N_L2]
    return [(float(x), needle_r(x)) for x in xs]


H_L = SPEC["items"]["SM_Senbon_Heavy"]["overall_length_mm"]               # 170
H_TAIL_D = HEAVY["tail_steel"]["diameter_mm"]                             # 3.0
H_TAIL_END = HEAVY["tail_steel"]["s_mm"][1]                               # 54
H_BODY_D1 = HEAVY["body"]["diameter_mm"][1]                               # 4.0
H_PT0 = HEAVY["point"]["s_mm"][0]                                         # 148
H_PT_L = HEAVY["point"]["length_mm"]                                      # 22
H_CH = HEAVY["butt"]["chamfer_mm"]                                        # 0.3
H_PHIS = [math.radians(a) for a in HEAVY["point"]["facet_normal_azimuths_deg"]]
H_HBASE = H_BODY_D1 / 2.0                                                 # facet plane 2.0 mm off axis at s = 148


def heavy_profile(n_body=8):
    r0, r1 = H_TAIL_D / 2, H_BODY_D1 / 2
    prof = [(0.0, 0.0), (0.0, r0 - H_CH), (H_CH, r0), (H_TAIL_END, r0)]
    for s in np.linspace(H_TAIL_END, H_PT0, n_body + 1)[1:]:
        prof.append((float(s), r0 + (r1 - r0) * (s - H_TAIL_END) / (H_PT0 - H_TAIL_END)))
    prof += [(H_L, r1), (H_L, 0.0)]
    return prof


def wrap_profile():
    rb, rw = HEAVY["rear_binding"], HEAVY["wrap"]
    fb = HEAVY["front_binding"]
    r0 = H_TAIL_D / 2
    return [(rb["s_mm"][0], r0), (rb["s_mm"][0], rb["outer_diameter_mm"] / 2), (rb["s_mm"][1], rb["outer_diameter_mm"] / 2),
            (rb["s_mm"][1], rw["outer_diameter_mm"] / 2), (fb["s_mm"][0], rw["outer_diameter_mm"] / 2),
            (fb["s_mm"][0], fb["outer_diameter_mm"] / 2), (fb["s_mm"][1], fb["outer_diameter_mm"] / 2), (fb["s_mm"][1], r0)]


# ----------------------------------------------------------------------------------------------- materials
def mat(name, rgb_linear):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb_linear, 1.0)
    return m


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_lin(h):
    h = h.lstrip("#")
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


# ----------------------------------------------------------------------------------------------- mesh builders
def revolve(prof, seg, closed=False, sharp_idx=()):
    """prof [(x_mm, r_mm)]; r = 0 is an apex vertex. Returns a bmesh (metres)."""
    bm = bmesh.new()
    rings = []
    for x, r in prof:
        if r <= 1e-12:
            rings.append([bm.verts.new((x * MM, 0.0, 0.0))])
        else:
            rings.append([bm.verts.new((x * MM, r * MM * math.cos(2 * math.pi * i / seg),
                                        r * MM * math.sin(2 * math.pi * i / seg))) for i in range(seg)])
    pairs = list(zip(rings, rings[1:]))
    if closed:
        pairs.append((rings[-1], rings[0]))
    for a, b in pairs:
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for i in range(seg):
                bm.faces.new((a[0], b[(i + 1) % seg], b[i]))
        elif len(b) == 1:
            for i in range(seg):
                bm.faces.new((a[i], a[(i + 1) % seg], b[0]))
        else:
            for i in range(seg):
                bm.faces.new((a[i], a[(i + 1) % seg], b[(i + 1) % seg], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = True
    bm.verts.ensure_lookup_table()
    # sharp ring edges at the listed profile indices
    for idx in sharp_idx:
        ring = set(rings[idx])
        if len(ring) == 1:
            continue
        for e in bm.edges:
            if e.verts[0] in ring and e.verts[1] in ring:
                e.smooth = False
    return bm


def cut_facets(bm):
    """The Heavy's three ground facets: planes through the tip, 2.0 mm off axis at s = 148."""
    tip = Vector((H_L * MM, 0, 0))
    new_faces = []
    for phi in H_PHIS:
        u = Vector((0, math.cos(phi), math.sin(phi)))
        t = Vector((0, -math.sin(phi), math.cos(phi)))
        p = Vector((H_PT0 * MM, 0, 0)) + u * (H_HBASE * MM)
        n = (p - tip).cross(t).normalized()
        if n.dot(u) < 0:
            n = -n
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        res = bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-10, plane_co=tip, plane_no=n, clear_outer=True)
        cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_valid]
        filled = bmesh.ops.holes_fill(bm, edges=cut_edges, sides=0)
        new_faces += filled["faces"]
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-8)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges[:], dist=1e-9)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    # facet faces: planar faces in the point zone whose normal matches a facet normal
    facet_normals = []
    for phi in H_PHIS:
        u = Vector((0, math.cos(phi), math.sin(phi)))
        t = Vector((0, -math.sin(phi), math.cos(phi)))
        p = Vector((H_PT0 * MM, 0, 0)) + u * (H_HBASE * MM)
        n = (p - tip).cross(t).normalized()
        facet_normals.append(n if n.dot(u) > 0 else -n)
    for f in bm.faces:
        if f.calc_center_median().x > (H_PT0 - 0.5) * MM and max(f.normal.dot(n) for n in facet_normals) > 0.9999:
            f.material_index = 1
            f.smooth = False
            for e in f.edges:
                e.smooth = False
    return bm


def spike_bm():
    L, a, pt, tl, te = SPIKE["length_mm"], 3.0, SPIKE["point_mm"], SPIKE["tail_taper_mm"], SPIKE["tail_end_mm"] / 2
    bm = bmesh.new()

    def sq(x, h):
        return [bm.verts.new((x * MM, sy * h * MM, sz * h * MM)) for sy, sz in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
    r0, r1, r2 = sq(0, te), sq(tl, a), sq(L - pt, a)
    tip = bm.verts.new((L * MM, 0, 0))
    bm.faces.new(r0[::-1])
    for A, B in ((r0, r1), (r1, r2)):
        for i in range(4):
            bm.faces.new((A[i], A[(i + 1) % 4], B[(i + 1) % 4], B[i]))
    for i in range(4):
        bm.faces.new((r2[i], r2[(i + 1) % 4], tip))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.smooth = False
        if f.calc_center_median().x > (L - pt) * MM:
            f.material_index = 1
    return bm


def bm_to_obj(bm, name, mats, coll):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def volume_com(bm):
    """Signed volume (mm3) and centre of mass (mm) of a closed bmesh in metres, by tetrahedra from the origin."""
    b = bm.copy()
    bmesh.ops.triangulate(b, faces=b.faces[:])
    vol = 0.0
    mom = Vector((0, 0, 0))
    for f in b.faces:
        a, c, d = (v.co / MM for v in f.verts)
        v6 = a.dot(c.cross(d)) / 6.0
        vol += v6
        mom += v6 * (a + c + d) / 4.0
    manifold = all(e.is_manifold for e in b.edges)
    b.free()
    return vol, mom / vol, manifold


# ----------------------------------------------------------------------------------------------- analytic checks
def analytic_needle():
    xs = np.linspace(-N_L2, N_L2, 260001)
    r = np.array([needle_r(x) for x in xs[::100]])
    xs = xs[::100]
    a = math.pi * r ** 2
    v = np.trapezoid(a, xs)
    return float(v)


def heavy_area(s):
    r0, r1 = H_TAIL_D / 2, H_BODY_D1 / 2
    if s < H_CH:
        r = (r0 - H_CH) + s
        return math.pi * r * r
    if s <= H_TAIL_END:
        return math.pi * r0 * r0
    if s <= H_PT0:
        r = r0 + (r1 - r0) * (s - H_TAIL_END) / (H_PT0 - H_TAIL_END)
        return math.pi * r * r
    r = r1
    h = (H_L - s) * H_HBASE / H_PT_L
    if h >= r:
        return math.pi * r * r
    if h >= r / 2:
        seg = r * r * math.acos(h / r) - h * math.sqrt(r * r - h * h)
        return math.pi * r * r - 3 * seg
    return 3 * math.sqrt(3) * h * h


def analytic_heavy():
    ss = np.linspace(0, H_L, 170001)
    a = np.array([heavy_area(s) for s in ss])
    v = float(np.trapezoid(a, ss))
    com = float(np.trapezoid(a * ss, ss) / v)
    return v, com


def wrap_volume():
    r0 = H_TAIL_D / 2
    tot = 0.0
    for key in ("rear_binding", "wrap", "front_binding"):
        s0, s1 = HEAVY[key]["s_mm"]
        ro = HEAVY[key]["outer_diameter_mm"] / 2
        tot += math.pi * (ro * ro - r0 * r0) * (s1 - s0)
    return tot


# ----------------------------------------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
os.makedirs(TMP, exist_ok=True)
scene = bpy.context.scene
scene.name = "Sheet"
coll = scene.collection

COAT = mat("coat", tuple(SPEC["finish"]["steel_coat"]["base_colour_linear"]))
GROUND = mat("ground", tuple(SPEC["finish"]["ground_point"]["base_colour_linear"]))
WRAP = mat("wrap", hex_lin(SPEC["finish"]["wrap"]["shipped_colour_srgb_hex"]))
BIND = mat("bind", tuple(min(1.0, c * 1.35) for c in hex_lin(SPEC["finish"]["wrap"]["shipped_colour_srgb_hex"])))
SPIKE_M = mat("spike", (0.16, 0.16, 0.17))
INK = mat("ink", (0.0, 0.0, 0.0))
GREY = mat("grey", (0.30, 0.30, 0.30))
PAPER = mat("paper", (0.93, 0.93, 0.92))

# -------- source meshes (sheet resolution)
SEG = 48
nprof = needle_profile()
n_sharp = [1, len(nprof) - 2]
needle_src = revolve(nprof, SEG, sharp_idx=n_sharp)
for f in needle_src.faces:
    if abs(f.calc_center_median().x) > N_SH * MM:
        f.material_index = 1
hprof = heavy_profile()
heavy_src = cut_facets(revolve(hprof, SEG, sharp_idx=[1, 2]))
wrap_src = revolve(wrap_profile(), SEG, closed=True, sharp_idx=[0, 1, 2, 3, 4, 5, 6, 7])
for f in wrap_src.faces:
    c = f.calc_center_median().x / MM
    f.material_index = 1 if (c < HEAVY["wrap"]["s_mm"][0] or c > HEAVY["wrap"]["s_mm"][1]) else 0
spike_src = spike_bm()

# -------- measurement meshes (high resolution) and the derived block
m_needle = revolve(needle_profile(200), 256)
m_heavy = cut_facets(revolve(heavy_profile(64), 256))
vn, cn, okn = volume_com(m_needle)
vh, ch, okh = volume_com(m_heavy)
van = analytic_needle()
vah, cah = analytic_heavy()
vw = wrap_volume()
wr0 = H_TAIL_D / 2
mass_n = vn * STEEL_DENSITY
mass_h_steel = vh * STEEL_DENSITY
mass_w = vw * COTTON_DENSITY
# CoM of the Heavy including the wrap (wrap centroid at its own volume-weighted s)
w_mom = 0.0
for key in ("rear_binding", "wrap", "front_binding"):
    s0, s1 = HEAVY[key]["s_mm"]
    ro = HEAVY[key]["outer_diameter_mm"] / 2
    w_mom += math.pi * (ro * ro - wr0 * wr0) * (s1 - s0) * COTTON_DENSITY * 0.5 * (s0 + s1)
com_h_total = (ch.x * mass_h_steel + w_mom) / (mass_h_steel + mass_w)
incl = math.degrees(math.atan(H_HBASE / H_PT_L) + math.atan(2 * H_HBASE / H_PT_L))

derived = {
    "generated_by": "WorkFiles/senbon/senbon_design_sheet.py (mesh: tetrahedra over a 256-segment build; analytic: section-area integral)",
    "steel_density_g_cm3": 7.85,
    "cotton_wrap_density_g_cm3": 0.6,
    "SM_Senbon_Needle": {
        "volume_mm3_mesh": round(vn, 2), "volume_mm3_analytic": round(van, 2),
        "mass_g": round(mass_n, 3), "com_x_mm": round(cn.x, 4), "closed_manifold": okn,
        "physics_mass_kg": round(mass_n / 1000, 5),
    },
    "SM_Senbon_Heavy": {
        "steel_volume_mm3_mesh": round(vh, 2), "steel_volume_mm3_analytic": round(vah, 2),
        "wrap_volume_mm3": round(vw, 2),
        "steel_mass_g": round(mass_h_steel, 3), "wrap_mass_g": round(mass_w, 3),
        "mass_g": round(mass_h_steel + mass_w, 3),
        "com_from_butt_mm_steel_mesh": round(ch.x, 3), "com_from_butt_mm_steel_analytic": round(cah, 3),
        "com_from_butt_mm": round(com_h_total, 3),
        "com_note": "pivot = this point (steel + wrap); it lies ahead of the middle (85 mm): front-weighted",
        "socket_x_from_pivot_mm": {"Grip": round(30.0 - com_h_total, 3), "Tip": round(H_L - com_h_total, 3), "Trail": round(-com_h_total, 3)},
        "point_included_deg_facet_to_ridge": round(incl, 3),
        "point_half_angle_facet_deg": round(math.degrees(math.atan(H_HBASE / H_PT_L)), 3),
        "point_half_angle_ridge_deg": round(math.degrees(math.atan(2 * H_HBASE / H_PT_L)), 3),
        "closed_manifold": okh,
        "physics_mass_kg": round((mass_h_steel + mass_w) / 1000, 5),
    },
    "ratios": {
        "spike_mass_over_needle": round(SPIKE["mass_g"] / mass_n, 2),
        "spike_mass_over_heavy": round(SPIKE["mass_g"] / (mass_h_steel + mass_w), 2),
        "needle_length_over_diameter": round(2 * N_L2 / N_DB, 1),
        "heavy_length_over_diameter": round(H_L / H_BODY_D1, 1),
        "spike_length_over_section": round(SPIKE["length_mm"] / 6.0, 1),
    },
}
SPEC["items"]["SM_Senbon_Heavy"]["profile"]["point"]["included_angle_across_facet_and_ridge_deg"] = round(incl, 2)
SPEC["derived"] = derived
with open(SPEC_PATH, "w", encoding="utf-8") as fh:
    json.dump(SPEC, fh, indent=2, ensure_ascii=False)
print("DERIVED", json.dumps(derived, indent=1))
m_needle.free()
m_heavy.free()

# ----------------------------------------------------------------------------------------------- sheet helpers
SHEET_W, SHEET_H = 400.0, 266.6667        # mm on the sheet; 12 px / mm
PX_PER_MM = 12
ann = bmesh.new()
ann_grey = bmesh.new()
Z_ANN = 30.0                                # annotations in front of the parts (mm; 5:1 parts reach 11 mm)


def _quad(bm, pts, z=Z_ANN):
    vs = [bm.verts.new((x * MM, y * MM, z * MM)) for x, y in pts]
    bm.faces.new(vs)


def line(x0, y0, x1, y1, w=0.16, bm=None):
    bm = bm or ann
    d = Vector((x1 - x0, y1 - y0))
    if d.length < 1e-9:
        return
    n = Vector((-d.y, d.x)).normalized() * (w / 2)
    _quad(bm, [(x0 + n.x, y0 + n.y), (x0 - n.x, y0 - n.y), (x1 - n.x, y1 - n.y), (x1 + n.x, y1 + n.y)])


def arrow(x, y, dx, dy, length=1.1, half=0.36):
    d = Vector((dx, dy)).normalized()
    n = Vector((-d.y, d.x))
    tip = Vector((x, y))
    base = tip - d * length
    vs = [ann.verts.new((p.x * MM, p.y * MM, Z_ANN * MM)) for p in (tip, base + n * half, base - n * half)]
    ann.faces.new(vs)


def rect_outline(x0, y0, x1, y1, w=0.2):
    line(x0, y0, x1, y0, w)
    line(x1, y0, x1, y1, w)
    line(x1, y1, x0, y1, w)
    line(x0, y1, x0, y0, w)


TEXTS = []


def text(s, x, y, size=2.4, align="CENTER", m=None, valign="CENTER"):
    cu = bpy.data.curves.new("t%d" % len(TEXTS), "FONT")
    cu.body = s
    cu.size = size * MM
    cu.align_x = align
    cu.align_y = valign
    ob = bpy.data.objects.new(cu.name, cu)
    ob.location = (x * MM, y * MM, Z_ANN * MM)
    cu.materials.append(m or INK)
    coll.objects.link(ob)
    TEXTS.append(ob)
    return ob


def dim_h(x0, x1, y, label, feat_y0=None, feat_y1=None, above=True, size=2.2, text_dx=0.0):
    """Horizontal dimension; extension lines from the feature heights to the dimension line."""
    for x, fy in ((x0, feat_y0), (x1, feat_y1)):
        if fy is not None:
            sgn = 1 if y > fy else -1
            line(x, fy + sgn * 0.6, x, y + sgn * 0.9, 0.11)
    line(x0, y, x1, y, 0.14)
    if abs(x1 - x0) > 2.6:
        arrow(x0, y, -1, 0)
        arrow(x1, y, 1, 0)
    else:                                     # arrows outside for short spans
        arrow(x0, y, 1, 0)
        arrow(x1, y, -1, 0)
        line(x0 - 2.2, y, x0, y, 0.14)
        line(x1, y, x1 + 2.2, y, 0.14)
    text(label, (x0 + x1) / 2 + text_dx, y + (1.7 if above else -1.9), size)


def dim_v(x, y0, y1, label, feat_x=None, right=True, size=2.2):
    if feat_x is not None:
        sgn = 1 if x > feat_x else -1
        line(feat_x + sgn * 0.6, y0, x + sgn * 0.9, y0, 0.11)
        line(feat_x + sgn * 0.6, y1, x + sgn * 0.9, y1, 0.11)
    line(x, y0, x, y1, 0.14)
    if abs(y1 - y0) > 2.6:
        arrow(x, y0, 0, -1 if y0 < y1 else 1)
        arrow(x, y1, 0, 1 if y1 > y0 else -1)
    else:
        lo, hi = min(y0, y1), max(y0, y1)
        arrow(x, lo, 0, 1)
        arrow(x, hi, 0, -1)
        line(x, lo - 2.2, x, lo, 0.14)
        line(x, hi, x, hi + 2.2, 0.14)
    text(label, x + (1.2 if right else -1.2), (y0 + y1) / 2, size, "LEFT" if right else "RIGHT")


def leader(x0, y0, x1, y1, label, size=2.1, align="LEFT"):
    line(x0, y0, x1, y1, 0.11)
    arrow(x0, y0, x0 - x1, y0 - y1, 0.9, 0.3)
    text(label, x1 + (0.8 if align == "LEFT" else -0.8), y1, size, align)


# view rotations (object frame -> sheet frame; the camera looks down -Z of the sheet)
R_SIDE = Matrix.Rotation(-math.pi / 2, 4, "X")              # sees the object's -Y side, object Z up
R_TOP = Matrix.Identity(4)                                  # sees the object's +Z side, object Y up
R_END_TIP = Matrix(((0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0), (0, 0, 0, 1)))   # looking from +X: obj Y right, Z up
R_END_BUTT = Matrix(((0, -1, 0, 0), (0, 0, 1, 0), (-1, 0, 0, 0), (0, 0, 0, 1)))  # looking from -X


def place(src_bm, mats, name, rot, at_xy, ref_x_obj_mm=0.0, scale=1.0, clip=None):
    """Instance a source bmesh into the sheet. ref_x_obj_mm: the object x placed at at_xy. clip=(x_min, x_max) object mm."""
    b = src_bm.copy()
    if clip is not None:
        lo, hi = clip
        for co, no in ((lo, Vector((-1, 0, 0))), (hi, Vector((1, 0, 0)))):
            if co is None:
                continue
            res = bmesh.ops.bisect_plane(b, geom=b.verts[:] + b.edges[:] + b.faces[:], dist=1e-10,
                                         plane_co=Vector((co * MM, 0, 0)), plane_no=no, clear_outer=True)
            ce = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge) and e.is_valid]
            if ce:
                fill = bmesh.ops.holes_fill(b, edges=ce, sides=0)
                for f in fill["faces"]:
                    f.smooth = False
    ob = bm_to_obj(b, name, mats, coll)
    b.free()
    ob.matrix_world = (Matrix.Translation((at_xy[0] * MM, at_xy[1] * MM, 0)) @ Matrix.Scale(scale, 4) @ rot
                       @ Matrix.Translation((-ref_x_obj_mm * MM, 0, 0)))
    return ob


def disc(x, y, r, m, z=0.0, seg=96):
    b = bmesh.new()
    vs = [b.verts.new(((x + r * math.cos(2 * math.pi * i / seg)) * MM, (y + r * math.sin(2 * math.pi * i / seg)) * MM, z * MM))
          for i in range(seg)]
    b.faces.new(vs)
    ob = bm_to_obj(b, "disc", [m], coll)
    b.free()
    return ob


def circle_outline(x, y, r, w=0.14, seg=96):
    for i in range(seg):
        a0, a1 = 2 * math.pi * i / seg, 2 * math.pi * (i + 1) / seg
        line(x + r * math.cos(a0), y + r * math.sin(a0), x + r * math.cos(a1), y + r * math.sin(a1), w)


# ----------------------------------------------------------------------------------------------- layout
X0 = -185.0                     # left end of every 1:1 view and of the ruler
NM = [COAT, GROUND]
HM = [COAT, GROUND]
WM = [WRAP, BIND]
SM = [SPIKE_M, GROUND]

text("SENBON  -  DESIGN SHEET", X0, 124.5, 5.0, "LEFT")
text("Original design for the ninja pack (study 2026-10-03).  Main views 1 : 1 (12 px = 1 mm on this sheet), details at the marked scale.  "
     "All dimensions in mm.  +X = toward the point, Z up.", X0, 118.6, 2.3, "LEFT")

# ---- SM_Senbon_Needle, 1:1
yS, yT = 104.0, 91.0
text("SM_Senbon_Needle   (standard, double-pointed)", X0, 113.0, 2.9, "LEFT")
place(needle_src, NM, "needle_side", R_SIDE, (X0 + N_L2, yS))
place(needle_src, NM, "needle_top", R_TOP, (X0 + N_L2, yT))
text("SIDE, from -Y", X0 + 2 * N_L2 + 4, yS, 1.9, "LEFT", GREY)
text("TOP, from +Z", X0 + 2 * N_L2 + 4, yT, 1.9, "LEFT", GREY)
xc = X0 + N_L2
dim_h(X0, X0 + 2 * N_L2, yS + 6.5, "130", yS + 0.3, yS + 0.3)
dim_h(X0, X0 + 15, yT - 5.5, "15", yT - 1.2, yT - 1.2, above=False)
dim_h(X0 + 15, xc, yT - 5.5, "50", yT - 1.2, yT - 1.4, above=False)
dim_h(xc, xc + 50, yT - 5.5, "50", yT - 1.4, yT - 1.2, above=False)
dim_h(xc + 50, xc + 65, yT - 5.5, "15", yT - 1.2, yT - 1.2, above=False)
leader(xc, yS + 1.6, xc + 10, yS + 3.7, "belly Ø2.8 (x = 0)", 1.9)
leader(X0 + 15, yS + 1.3, X0 + 22, yS + 3.7, "shoulder Ø2.3 = grind line (hard edge)", 1.9)
# sockets / pivot on the top view
for sx, nm in ((0.0, "Grip / pivot"), (65.0, "Tip"), (-65.0, "Trail")):
    arrow(xc + sx, yT + 1.6, 0, -1, 0.9, 0.35)
    text(nm, xc + sx + (0 if abs(sx) < 1 else (-1.5 if sx > 0 else 1.5)), yT + 3.0, 1.7,
         "CENTER" if abs(sx) < 1 else ("RIGHT" if sx > 0 else "LEFT"), GREY)
# end view at 1:1
place(needle_src, NM, "needle_end", R_END_TIP, (25.0, yT + 6.0), ref_x_obj_mm=N_L2)
text("END 1:1", 25.0, yT + 1.0, 1.7, "CENTER", GREY)

# ---- SM_Senbon_Heavy, 1:1
yS2, yT2 = 69.0, 55.0
text("SM_Senbon_Heavy   (single point, three-facet tip, thread-wrapped tail)", X0, 78.5, 2.9, "LEFT")
place(heavy_src, HM, "heavy_side", R_SIDE, (X0, yS2))
place(wrap_src, WM, "wrap_side", R_SIDE, (X0, yS2))
place(heavy_src, HM, "heavy_top", R_TOP, (X0, yT2))
place(wrap_src, WM, "wrap_top", R_TOP, (X0, yT2))
text("SIDE -Y", X0 + H_L + 3, yS2, 1.9, "LEFT", GREY)
text("TOP +Z", X0 + H_L + 3, yT2, 1.9, "LEFT", GREY)
dim_h(X0, X0 + H_L, yS2 + 7.0, "170", yS2 + 0.4, yS2 + 0.4)
dim_h(X0 + 6, X0 + 54, yT2 - 6.0, "48 (wrap 45 + bindings 2 x 1.5)", yT2 - 2.5, yT2 - 2.5, above=False)
dim_h(X0 + 54, X0 + 148, yT2 - 6.0, "94 (Ø%.1f -> Ø%.1f)" % (H_TAIL_D, H_BODY_D1), yT2 - 1.7, yT2 - 2.2, above=False)
dim_h(X0 + 148, X0 + 170, yT2 - 6.0, "22", yT2 - 2.2, yT2 - 0.5, above=False)
com = derived["SM_Senbon_Heavy"]["com_from_butt_mm"]
arrow(X0 + com, yS2 - 2.6, 0, 1, 1.0, 0.4)
text("CoM / pivot  s = %.1f" % com, X0 + com + 1.0, yS2 - 4.6, 1.8, "LEFT", GREY)
line(X0 + 85.0, yS2 - 1.4, X0 + 85.0, yS2 - 2.4, 0.12)
text("mid 85", X0 + 85.0 - 1.0, yS2 - 4.6, 1.6, "RIGHT", GREY)
for sx, nm in ((30.0, "Grip"), (170.0, "Tip"), (0.0, "Trail")):
    arrow(X0 + sx, yT2 + 2.7, 0, -1, 0.9, 0.35)
    text(nm, X0 + sx + (-1.5 if sx > 100 else (1.5 if sx < 1 else 0)), yT2 + 4.0, 1.7,
         "RIGHT" if sx > 100 else ("LEFT" if sx < 1 else "CENTER"), GREY)
place(heavy_src, HM, "heavy_end", R_END_TIP, (25.0, yT2 + 7.0), ref_x_obj_mm=H_L)
place(wrap_src, WM, "wrap_end", R_END_TIP, (25.0, yT2 + 7.0), ref_x_obj_mm=H_L)
text("END 1:1 (from tip)", 25.0, yT2 + 1.0, 1.7, "CENTER", GREY)

# ---- frozen spike, 1:1, for contrast
yK = 33.0
text("for contrast: existing SM_Shuriken_Spike (frozen, not part of this set)  150 mm, 6 mm square, 37 g", X0, yK + 6.6, 2.2, "LEFT", GREY)
place(spike_src, SM, "spike_side", R_SIDE, (X0, yK))
place(spike_src, SM, "spike_end", R_END_TIP, (25.0, yK), ref_x_obj_mm=SPIKE["length_mm"])
text("END 1:1", 25.0, yK - 5.5, 1.7, "CENTER", GREY)

# ---- ruler 0..200 mm at 1:1
yR = 19.0
line(X0, yR, X0 + 200, yR, 0.2)
for mmv in range(0, 201):
    h = 3.0 if mmv % 10 == 0 else (2.0 if mmv % 5 == 0 else 1.1)
    line(X0 + mmv, yR, X0 + mmv, yR + h, 0.12 if mmv % 10 else 0.18)
    if mmv % 10 == 0:
        text(str(mmv), X0 + mmv, yR - 2.2, 1.8)
text("ruler, mm (1 : 1, same scale as the views above)", X0 + 205, yR + 1.0, 1.9, "LEFT", GREY)

# ---- details
rect_outline(-190, -2, 197, -129.5, 0.18)
text("DETAILS", -188, -5.2, 2.6, "LEFT")

# D1 needle point 5:1 (object x 37..65)
S5 = 5.0
yD1 = -20.0
xD1 = -183.0
text("D1  Needle point  5 : 1  (side)", xD1, -9.5, 2.3, "LEFT")
place(needle_src, NM, "d1", R_SIDE, (xD1, yD1), ref_x_obj_mm=37.0, scale=S5, clip=(37.0, None))
x_sh = xD1 + (50 - 37) * S5
x_tip = xD1 + (65 - 37) * S5
dim_h(x_sh, x_tip, yD1 - 9.0, "15", yD1 - N_DS / 2 * S5 - 0.4, yD1 - 0.5, above=False)
leader(x_sh - 0.3, yD1 - N_DS / 2 * S5, x_sh - 14, yD1 - 11.0, "shoulder Ø2.3", 1.8, "RIGHT")
leader(x_sh + 0.2, yD1 + N_DS / 2 * S5, x_sh + 12, yD1 + 9.0, "grind line, hard edge; coat ends, 1.5-2.5 mm worn fade", 1.8)
leader(x_tip - 1.0, yD1 + 0.3, x_tip - 18, yD1 + 6.0, "cone, included 8.8°, tip r 0.05", 1.8, "RIGHT")
text("cut", xD1 - 0.5, yD1 - 9.5, 1.6, "LEFT", GREY)
# needle section at 5:1
cx, cy = -12.0, -20.0
disc(cx, cy, N_DB / 2 * S5, COAT)
circle_outline(cx, cy, N_DS / 2 * S5, 0.14)
dim_h(cx - N_DB / 2 * S5, cx + N_DB / 2 * S5, cy - 10.5, "Ø2.8 belly", cy - 2, cy - 2, above=False)
text("section at x = 0, 5 : 1", cx, cy + 10.5, 1.9)
text("(inner ring = shoulder Ø2.3)", cx, cy + 8.0, 1.6, "CENTER", GREY)

# D2 heavy point 5:1 (object s 140..170), side + top + end
xD2 = 10.0
yD2s, yD2t = -25.0, -55.0
text("D2  Heavy point  5 : 1   (side, top, end from the tip)", xD2, -9.5, 2.3, "LEFT")
place(heavy_src, HM, "d2s", R_SIDE, (xD2, yD2s), ref_x_obj_mm=140.0, scale=S5, clip=(140.0, None))
place(heavy_src, HM, "d2t", R_TOP, (xD2, yD2t), ref_x_obj_mm=140.0, scale=S5, clip=(140.0, None))
text("side", xD2, yD2s - 13.5, 1.7, "LEFT", GREY)
text("top", xD2, yD2t - 13.5, 1.7, "LEFT", GREY)
xp0 = xD2 + (148 - 140) * S5
xr0 = xD2 + (159 - 140) * S5
xpt = xD2 + (170 - 140) * S5
dim_h(xp0, xpt, yD2t - 13.0, "22 point", yD2t - 10.5, yD2t - 1.0, above=False)
dim_h(xr0, xpt, yD2t + 14.5, "11 ridges", yD2t + 8.0, yD2t + 1.0)
dim_v(xD2 - 3.0, yD2s - H_BODY_D1 / 2 * S5, yD2s + H_BODY_D1 / 2 * S5, "Ø%.1f" % H_BODY_D1, feat_x=xD2 + 2, right=False)
leader(xp0 + 60, yD2t + 1.5, xpt + 2.5, yD2t + 5.0, "facet: flat,", 1.7, "LEFT")
text("ground bright,", xpt + 3.3, yD2t + 2.4, 1.7, "LEFT")
text("%.2f° to axis" % math.degrees(math.atan(H_HBASE / H_PT_L)), xpt + 3.3, yD2t - 0.2, 1.7, "LEFT")
leader(xp0 + 30, yD2s + 3.5, xp0 + 95, yD2s + 9.5, "elliptical grind lines, hard edges", 1.7, "LEFT")
# end view from the tip, 5:1
ex, ey = 183.0, -64.0
place(heavy_src, HM, "d2e", R_END_TIP, (ex, ey), ref_x_obj_mm=H_L, scale=S5, clip=(140.0, None))
text("end (from tip)", ex, ey + 13.0, 1.7, "CENTER", GREY)
text("facet normals 90 / 210 / 330°", ex, ey - 13.0, 1.6, "CENTER", GREY)
text("ridges 30 / 150 / 270°", ex, ey - 15.4, 1.6, "CENTER", GREY)

# D3 heavy tail 3:1 (object s -1..62)
S3 = 3.0
xD3, yD3 = -183.0, -84.0
text("D3  Heavy tail and wrap  3 : 1  (side)", xD3, -61.0, 2.3, "LEFT")
place(heavy_src, HM, "d3", R_SIDE, (xD3, yD3), ref_x_obj_mm=0.0, scale=S3, clip=(None, 62.0))
place(wrap_src, WM, "d3w", R_SIDE, (xD3, yD3), ref_x_obj_mm=0.0, scale=S3)


def sx3(s):
    return xD3 + s * S3


top_w = HEAVY["wrap"]["outer_diameter_mm"] / 2 * S3
top_b = HEAVY["front_binding"]["outer_diameter_mm"] / 2 * S3
top_s = H_TAIL_D / 2 * S3
dim_h(sx3(0), sx3(6), yD3 + 12.0, "6", yD3 + top_s + 0.2, yD3 + top_b + 0.2)
dim_h(sx3(6), sx3(7.5), yD3 + 12.0, "1.5", yD3 + top_b + 0.2, yD3 + top_b + 0.2, text_dx=-3.0)
dim_h(sx3(7.5), sx3(52.5), yD3 + 12.0, "45 wrap, cotton thread, pitch 0.6", yD3 + top_b + 0.2, yD3 + top_b + 0.2)
dim_h(sx3(52.5), sx3(54), yD3 + 12.0, "1.5", yD3 + top_b + 0.2, yD3 + top_b + 0.2, text_dx=3.0)
dim_v(sx3(-1.5), yD3 - top_s, yD3 + top_s, "Ø%.1f" % H_TAIL_D, feat_x=sx3(0), right=False)
leader(sx3(30), yD3 - top_w, sx3(36), yD3 - 13.0, "wrap Ø4.2 (thread helix in the normal map)", 1.7)
dim_v(sx3(65.0), yD3 - top_b, yD3 + top_b, "Ø4.6", feat_x=sx3(54), right=True)
leader(sx3(0.2), yD3 - top_s + 0.4, sx3(4), yD3 - 13.0, "butt: flat, 0.3 x 45° chamfer (Trail socket)", 1.7)
text("cut", sx3(62) + 0.5, yD3 - 6.0, 1.6, "LEFT", GREY)
# wrap section 3:1
cx3, cy3 = 25.0, -84.0
disc(cx3, cy3, HEAVY["front_binding"]["outer_diameter_mm"] / 2 * S3, BIND, z=-0.2)
disc(cx3, cy3, HEAVY["wrap"]["outer_diameter_mm"] / 2 * S3, WRAP, z=0.0)
disc(cx3, cy3, H_TAIL_D / 2 * S3, COAT, z=0.2)
text("section s = 30, 3 : 1", cx3, cy3 + 11.0, 1.9)
text("steel Ø%.1f / wrap Ø4.2 / binding Ø4.6 behind" % H_TAIL_D, cx3, cy3 - 11.0, 1.6, "CENTER", GREY)

# notes + swatches
nx, ny = 45.0, -77.0
dn, dh = derived["SM_Senbon_Needle"], derived["SM_Senbon_Heavy"]
notes = [
    ("NEEDLE  130 mm, round, Ø2.8 belly -> Ø2.3 shoulders (parabolic swell), two 15 mm cones.", INK),
    ("   steel %.2f g; pivot = centre; volley of 3, direct throw (no spin)." % dn["mass_g"], GREY),
    ("HEAVY  170 mm, round Ø%.1f tail -> Ø%.1f at the point (front-weighted), 22 mm three-facet" % (H_TAIL_D, H_BODY_D1), INK),
    ("   point, 45 mm cotton wrap Ø4.2 with Ø4.6 bindings.  steel %.2f g + wrap %.2f g = %.2f g;" % (dh["steel_mass_g"], dh["wrap_mass_g"], dh["mass_g"]), GREY),
    ("   CoM / pivot s = %.1f mm from the butt (mid = 85).  Single direct throw." % dh["com_from_butt_mm"], GREY),
    ("SPIKE (frozen) 150 mm, 6 mm square, one 4-facet point, 37 g = %.0fx needle, %.1fx heavy." %
     (derived["ratios"]["spike_mass_over_needle"], derived["ratios"]["spike_mass_over_heavy"]), INK),
    ("Sockets Grip / Tip / Trail (+ Throw, Embed per the build plan); one UCX hull; LOD sides 12 / 8 / 6.", INK),
    ("No tassel, no marks, no crest.  Values: senbon_spec.json (derived block = this sheet).", INK),
]
for i, (s, m) in enumerate(notes):
    text(s, nx, ny - i * 3.5, 1.95, "LEFT", m, valign="TOP")
sw_y = -40.0
SWX = -183.0
for i, (m, lab) in enumerate(((COAT, "blackened steel coat (lin 0.097/0.093/0.103, rough 0.34)"),
                               (GROUND, "ground bright steel at the points (lin 0.42, rough 0.22)"),
                               (WRAP, "cotton wrap #373532 (recolourable, Fabric master)"),
                               (BIND, "bindings (same thread, drawn lighter here only)"))):
    yy = sw_y - i * 4.6
    b = bmesh.new()
    vs = [b.verts.new((x * MM, y * MM, 0)) for x, y in ((SWX, yy - 1.6), (SWX + 7, yy - 1.6), (SWX + 7, yy + 1.6), (SWX, yy + 1.6))]
    b.faces.new(vs)
    bm_to_obj(b, "sw", [m], coll)
    b.free()
    rect_outline(SWX, yy - 1.6, SWX + 7, yy + 1.6, 0.12)
    text(lab, SWX + 9, yy, 1.8, "LEFT")

# 3/4 box (filled later by compositing)
BOX = (35.0, 22.0, 197.0, 114.0)
rect_outline(*BOX, 0.18)
text("3/4 sketch (perspective, not to scale): Needle, Heavy, and the frozen spike", BOX[0] + 1.5, BOX[3] - 3.0, 2.1, "LEFT")
text("close-up: Heavy point (left), Needle point (right)", BOX[0] + 1.5, BOX[1] + 31.5, 1.9, "LEFT", GREY)

for b, m, nm in ((ann, INK, "ann"), (ann_grey, GREY, "ann_grey")):
    if len(b.faces):
        bm_to_obj(b, nm, [m], coll)

# ----------------------------------------------------------------------------------------------- render settings
def setup_workbench(sc, w, h):
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.display.render_aa = "16"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_object_outline = True
    sh.object_outline_color = (0.0, 0.0, 0.0)
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sh.show_specular_highlight = True


setup_workbench(scene, int(SHEET_W * PX_PER_MM), int(round(SHEET_H * PX_PER_MM)))
cam_d = bpy.data.cameras.new("cam")
cam_d.type = "ORTHO"
cam_d.ortho_scale = SHEET_W * MM
cam_d.clip_start, cam_d.clip_end = 0.001, 1.0
cam = bpy.data.objects.new("cam", cam_d)
cam.location = (0, 0, 0.3)
coll.objects.link(cam)
scene.camera = cam
sheet_png = TMP + "/sheet_layout.png"
scene.render.filepath = sheet_png
bpy.ops.render.render(write_still=True, scene=scene.name)

# ----------------------------------------------------------------------------------------------- 3/4 renders
BOX_PX = [int(round((v + (SHEET_W / 2 if i % 2 == 0 else SHEET_H / 2)) * PX_PER_MM)) for i, v in enumerate(BOX)]
inner_w = BOX_PX[2] - BOX_PX[0] - 24


def persp_scene(name, objs, cam_loc, target, lens, w, h):
    sc = bpy.data.scenes.new(name)
    setup_workbench(sc, w, h)
    sc.display.shading.show_shadows = False
    for src_bm, mats, mw in objs:
        ob = bm_to_obj(src_bm.copy(), name + "_o", mats, sc.collection)
        ob.matrix_world = mw
    cd = bpy.data.cameras.new(name + "_cam")
    cd.lens = lens
    cd.clip_start, cd.clip_end = 0.001, 5.0
    c = bpy.data.objects.new(name + "_cam", cd)
    sc.collection.objects.link(c)
    c.location = cam_loc
    d = Vector(target) - Vector(cam_loc)
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = c
    path = TMP + "/%s.png" % name
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return path


T = Matrix.Translation
h_off = -com
overall = persp_scene(
    "q_overall",
    [(needle_src, NM, T((0, 0.020, 0))),
     (heavy_src, HM, T((h_off * MM, 0.0, 0))), (wrap_src, WM, T((h_off * MM, 0.0, 0))),
     (spike_src, SM, T((-75 * MM, -0.022, 0)))],
    (0.135, -0.205, 0.120), (0.004, 0.0, 0.0), 50, inner_w, 690)
close = persp_scene(
    "q_close",
    [(heavy_src, HM, T((-158 * MM, 0.0, 0))), (wrap_src, WM, T((-158 * MM, 0.0, 0))),
     (heavy_src, HM, T((-158 * MM - 0.030, 0.000, 0))), (wrap_src, WM, T((-158 * MM - 0.030, 0.000, 0))),
     (needle_src, NM, T((-55 * MM + 0.026, 0.012, 0)))],
    (0.040, -0.062, 0.034), (0.006, 0.002, 0.0), 50, inner_w, 340)


# ----------------------------------------------------------------------------------------------- composite
def load_rgba(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    a = np.empty(w * h * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def over(dst, src, x0, y0_top):
    """Alpha-over src onto dst (both bottom-up arrays); (x0, y0_top) = top-left of src in top-down pixels."""
    H = dst.shape[0]
    h, w = src.shape[:2]
    y_lo = H - y0_top - h
    region = dst[y_lo:y_lo + h, x0:x0 + w]
    al = src[..., 3:4]
    region[..., :3] = src[..., :3] * al + region[..., :3] * (1 - al)


lay = load_rgba(sheet_png)
H, W = lay.shape[:2]
canvas = np.ones((H, W, 4), dtype=np.float32)
canvas[..., :3] = 0.985
over(canvas, lay, 0, 0)
ov = load_rgba(overall)
cl = load_rgba(close)
bx0 = BOX_PX[0] + 12
box_top_px = H - BOX_PX[3]           # BOX_PX y is bottom-up from the sheet's bottom edge
over(canvas, ov, bx0, box_top_px + 50)
over(canvas, cl, bx0, H - BOX_PX[1] - cl.shape[0] - 8)
canvas[..., 3] = 1.0
out = bpy.data.images.new("SENBON_DESIGN_SHEET", W, H, alpha=False)
out.pixels.foreach_set(canvas.ravel())
out.filepath_raw = OUT
out.file_format = "PNG"
out.save()
print("WROTE", OUT, W, H)
