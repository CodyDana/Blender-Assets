"""Kit 8: courtyard stone + wooden climb props (DOJO_QUEUE #8; sheet References/Dojo/dojo_courtyard_stone_ref.png).

Every prop is its OWN asset (user rule, 2026-09-27): its own mesh + UCX, its own FBX, its own collection in
Assets/Dojo/CourtyardStone.blend, pivot at the base centre on the ground (exceptions: the pulley pivots on its axle, the
bucket on its bail grip, the rope at its top where it leaves the pulley), real-world metres, nothing merged.

Pieces (SM_DKP_Stone_*): LanternTall (2.00 m), LanternShort (1.20 m), Well (granite ring 1.2 x 0.8 m), WellFrame
(plank-roofed timber frame), WellFrameGable (the lighter gable variant), WellCover, WellPulley, WellBucket, WellRope
(one rope serves both frames), Cistern (1.2 x 1.2 x 1.25 climb prop), Crate (1.0 x 1.0 x 1.25 climb prop), CrateHalf (1.0 x 1.0 x 0.625,
stacks to +1.25).

Frame: Blender metres, +Z up, the FRONT of every prop faces -Y (the front view looks along +Y). In the grey-box frame the
lanterns and cisterns face south (-Y) toward the fight floor, so their layout rot_z is 0.

Writes: WorkFiles/dojo/build/props/stone/{layout_stone.json, measure.json, qa_report.json, export_report.json},
Exports/DojoKit/Props/stone/SM_DKP_Stone_*.fbx (through Scripts/pipeline), Assets/Dojo/CourtyardStone.blend.
Run: blender -b --factory-startup --python Scripts/dojo/props/stone/build_stone_props.py -- [--no-export]
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(HERE))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
import stone_geo as G  # noqa: E402
from stone_geo import Part, R, T, box, cbox, lathe, prism, rough_tier, sq_loft, sq_tier, square_ring, tube  # noqa: E402

TEX = ROOT / "Exports" / "DojoKit" / "Props" / "stone" / "Textures"
EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Props" / "stone"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "stone"
BLEND = ROOT / "Assets" / "Dojo" / "CourtyardStone.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# --------------------------------------------------------------------------- materials (r2: the shared dojo library)
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_materials as djm  # noqa: E402

# Library materials (Scripts/dojo/materials, v1.0.0). Round / carved stone (lanterns, well blocks) uses the library
# granite on the TRIPLANAR path: in Blender make_material(projection="BOX", box_blend=0.3) in object space, in Unreal
# M_DJ_Lib_Triplanar (WorldAlignedTexture, TextureSize 400) -> slot M_DJ_Granite_Tri = MI_DJ_Granite on the triplanar
# master. Flat dressed stone (the cistern feet) uses M_DJ_Granite with box_uv (upright, unmirrored).
GRT, GR = "M_DJ_Granite_Tri", "M_DJ_Granite"
TB, TBE = "M_DJ_TimberDark", "M_DJ_TimberDarkEnd"
TG, TGE = TB, TBE          # r2: the sheet's well roofs are the same dark weathered timber (TimberAged read orange)
IR, RP, GL = "M_DJ_Iron", "M_DJ_Rope", "M_DJ_GlassAmber"
# kit-own materials (the library has no moss, mortar or water)
MS, MO, WA = "M_DKP_Stone_Moss", "M_DKP_Stone_Mortar", "M_DKP_Stone_WellWater"
MW = "M_DKP_Stone_WellMortar"
ROPE_TILE_U = 4 * 3.2 * 0.022          # library rope: U = 4 lays of 3.2 x the diameter (22 mm rope), V = once round
# name: (texture set, tile (m) or (u, v) or None for explicit UVs, params, note)
MATERIALS = {
    GRT: ("LIB", 4.0, {"lib": "M_DJ_Granite", "projection": "BOX"}, "library granite, triplanar (round / carved stone)"),
    GR: ("LIB", 4.0, {"lib": GR}, "library granite, box UV (flat dressed stone)"),
    TB: ("LIB", 4.0, {"lib": TB}, "library dark weathered timber (side grain)"),
    TBE: ("LIB", 2.0, {"lib": TBE}, "library dark timber end grain"),
    IR: ("LIB", 2.0, {"lib": IR}, "library iron: bare metal 0.95-1.0, rust 0, no partial metal"),
    RP: ("LIB", (ROPE_TILE_U, 1.0), {"lib": RP}, "library rope (tube UVs: U along, V once round)"),
    GL: ("LIB", None, {"lib": GL}, "library amber emissive glass, 0-1 per pane (hotspot core)"),
    MS: ("Moss", 1.0, {}, "kit-own moss cushion surface (T_DKP_Stone_Moss, 1.0 m tile) on the modelled moss pads"),
    MO: (None, 2.0, {"color": "#2B2825", "rough": 0.97}, "kit-own flat dark mortar / tank liner (r2: darker joints)"),
    WA: (None, 2.0, {"color": "#0A0D0C", "rough": 0.06}, "kit-own flat dark well water"),
    MW: (None, 2.0, {"color": "#7B766E", "rough": 0.95}, "kit-own flat light lime mortar in the well-ring joints (r3)"),
}
G.TILES.update({k: v[1] for k, v in MATERIALS.items()})
END_OF = {TB: TBE}
import timber_bands  # noqa: E402


def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h):
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (1, 3, 5)) + (1.0,)


def build_material(name):
    tex, _tile, p, _note = MATERIALS[name]
    if tex == "LIB":
        if p.get("projection") == "BOX":
            # the triplanar variant of a library material: build it, then give it its own slot name (built FIRST, so
            # the plain UV material of the same library name is created fresh afterwards)
            m = djm.make_material(p["lib"], rebuild=True, projection="BOX", box_blend=0.3)
            m.name = name
            return m
        return djm.make_material(p["lib"], uv_map="UV0")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def img(suffix, noncolor):
        node = nt.nodes.new("ShaderNodeTexImage")
        image = bpy.data.images.load(str(TEX / f"T_DKP_Stone_{tex}_{suffix}.png"), check_existing=True)
        if noncolor:
            image.colorspace_settings.name = "Non-Color"
        node.image = image
        return node

    if tex and "emit" in p:        # emissive pane: dark albedo, the picture drives the emission colour
        bc = img("BC", False)
        bsdf.inputs["Base Color"].default_value = (0.02, 0.015, 0.01, 1)
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = p["emit"]
        bsdf.inputs["Roughness"].default_value = 0.9
        return mat
    if tex:
        bc, orm, nrm = img("BC", False), img("ORM", True), img("N", True)
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
        sep_n = nt.nodes.new("ShaderNodeSeparateColor")          # DirectX maps: flip green back for Blender
        nt.links.new(nrm.outputs["Color"], sep_n.inputs["Color"])
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        nt.links.new(sep_n.outputs[1], inv.inputs[1])
        comb = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(sep_n.outputs[0], comb.inputs[0])
        nt.links.new(inv.outputs[0], comb.inputs[1])
        nt.links.new(sep_n.outputs[2], comb.inputs[2])
        nmap = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(comb.outputs["Color"], nmap.inputs["Color"])
        nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
        return mat
    bsdf.inputs["Base Color"].default_value = hexcol(p["color"])
    bsdf.inputs["Roughness"].default_value = p.get("rough", 0.5)
    return mat


# --------------------------------------------------------------------------- small shared parts

def rivet(p, x, y, z, facing, r=0.011, h=0.008, sides=6):
    """A domed iron rivet / bolt head on a face; facing = '-y', '+y', '-x', '+x', '+z'. f1: 18 triangles (open base
    against the plate, flat-topped dome) instead of 48 (the measurer's tri budget: the cistern's rivets were 1888 faces)."""
    geo = lathe([(r, 0), (r * 0.62, h), (0, h)], sides=sides, axis="y")        # ring -> ring -> pole: open base
    rot = {"-y": Matrix.Identity(4), "+y": R(180, "Z"), "-x": R(-90, "Z"), "+x": R(90, "Z"), "+z": R(-90, "X"),
           "-z": R(90, "X")}[facing]
    p.add(geo, IR, T(x, y, z) @ rot, smooth=True)


def nail(p, x, y, z, facing, s=0.007, h=0.003):
    """A square forged nail head: a 4-sided pyramid, open base (4 triangles)."""
    geo = lathe([(s, 0), (0, h)], sides=4, axis="y")
    rot = {"-y": Matrix.Identity(4), "+y": R(180, "Z"), "-x": R(-90, "Z"), "+x": R(90, "Z"), "+z": R(-90, "X")}[facing]
    p.add(geo, IR, T(x, y, z) @ rot @ R(45, "Y"))


def board(p, x0, x1, y0, y1, z0, z1, mat=TB, bevel=0.004, jitter=0.002, grain=None, M=None):
    j = lambda: (G.rnd() - 0.5) * 2 * jitter   # noqa: E731
    p.add(box(x0 + j(), x1 + j(), y0 + j(), y1 + j(), z0 + j() * 0.5, z1 + j() * 0.5, bevel), mat, M, grain=grain)


def band_rect(p, hx, hy, z0, z1, t=0.006, mat=IR):
    """An iron band wrapped round a rectangle of half sizes hx, hy (outer faces of the frame)."""
    p.add(box(-hx - t, hx + t, -hy - t, -hy, z0, z1, 0.0015), mat)
    p.add(box(-hx - t, hx + t, hy, hy + t, z0, z1, 0.0015), mat)
    p.add(box(-hx - t, -hx, -hy, hy, z0, z1, 0.0015), mat)
    p.add(box(hx, hx + t, -hy, hy, z0, z1, 0.0015), mat)


def widths(total, n, lo=0.8, hi=1.25):
    """n random widths (relative lo..hi) summing to total."""
    w = [lo + (hi - lo) * G.rnd() for _ in range(n)]
    s = sum(w)
    return [total * x / s for x in w]


def section_loft(sections, cap=True):
    """Loft a list of 4-point cross-sections (each in order round the section) into a closed prism strip; the winding is
    checked once so the normals point out."""
    vs, fs = [], []
    for sec in sections:
        vs.extend(tuple(q) for q in sec)
    n = len(sections)
    for i in range(n - 1):
        for k in range(4):
            k2 = (k + 1) % 4
            fs.append((i * 4 + k, i * 4 + k2, (i + 1) * 4 + k2, (i + 1) * 4 + k))
    if cap:
        fs.append((3, 2, 1, 0))
        b = (n - 1) * 4
        fs.append((b, b + 1, b + 2, b + 3))
    c0 = sum((Vector(q) for q in sections[0]), Vector()) / 4
    c1 = sum((Vector(q) for q in sections[1]), Vector()) / 4
    f = fs[0]
    pts = [Vector(vs[i]) for i in f]
    nrm = G._newell(pts)
    mid = sum(pts, Vector()) / 4
    if nrm.dot(mid - (c0 + c1) / 2) < 0:
        fs = [tuple(reversed(q)) for q in fs]
    return vs, fs


# --------------------------------------------------------------------------- stone lanterns

def section_loft_n(sections):
    """Loft closed N-point cross-sections (same N, each in order round the section) into a closed tube with end caps
    (fans from each end section's centroid, so no n-gons). The winding is checked once so the normals point out."""
    n = len(sections[0])
    vs, fs = [], []
    for sec in sections:
        vs.extend(tuple(q) for q in sec)
    m = len(sections)
    for i in range(m - 1):
        for k in range(n):
            k2 = (k + 1) % n
            fs.append((i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k))
    c0 = len(vs)
    vs.append(tuple(sum((Vector(q) for q in sections[0]), Vector()) / n))
    c1 = len(vs)
    vs.append(tuple(sum((Vector(q) for q in sections[-1]), Vector()) / n))
    b = (m - 1) * n
    for k in range(n):
        k2 = (k + 1) % n
        fs.append((c0, k2, k))
        fs.append((c1, b + k, b + k2))
    pts = [Vector(vs[i]) for i in fs[0]]
    mid = sum(pts, Vector()) / 4
    cen = (Vector(vs[c0]) * 0 + sum((Vector(q) for q in sections[0]), Vector()) / n +
           sum((Vector(q) for q in sections[1]), Vector()) / n) / 2
    if G._newell(pts).dot(mid - cen) < 0:
        fs = [tuple(reversed(q)) for q in fs]
    return vs, fs


def cap_dims(k):
    """r2 cap numbers (tall lantern k = 1), measured on the stone sheet's tall lantern front view (331 px = its 2.0 m)
    and scaled to our cap / base ratio 1.45: fascia 7 cm at the centre of each side (sheet 11-12 px = 6.6-7.2 cm),
    fascia half-width 0.47, corner tips flaring to 0.545 (cap 1.09 m = 1.45 x the 0.75 m base; sheet 1.52 front,
    1.58 side, 1.41 short), roof face rising 0.28 from the fascia top to a 0.21 half-width top (sheet: roof top
    half-width about 0.23, rise 0.22-0.24 above the fascia; total cap fascia bottom -> roof top 0.34 front / 0.38 side,
    ours 0.36), concave from about 28 degrees at the eave to about 68 degrees under the collar."""
    return dict(E=0.46 * k, tb=0.07 * k, Ub=0.012 * k, Fb=0.018 * k, Ut=0.048 * k, Ft=0.040 * k, lip=0.012 * k,
                rise=0.285 * k, b=0.21 * k, q=1.35)   # r3: q 1.8 -> 1.35 (judge B: 'top view reads as a funnel')


def square_ring_2(h, z, segs, upturn, flare):
    """square_ring with separate fall-offs: upturn |t|^5, flare |t|^8 (straight sides, the tip only at the corner)."""
    pts = []
    corners = [(-h, -h), (h, -h), (h, h), (-h, h)]
    for s_ in range(4):
        (x0, y0), (x1, y1) = corners[s_], corners[(s_ + 1) % 4]
        for kk in range(segs):
            f = 0.5 - 0.5 * math.cos(math.pi * kk / segs)
            t = 2 * f - 1
            x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            sc = 1 + flare * abs(t) ** 8 / h
            pts.append((x * sc, y * sc, z + upturn * abs(t) ** 5))
    return pts


def kasa(p, z1, k, top):
    """r2 cap (judges: 'the sheet's steep curved HIPPED roof'): a thick SQUARED fascia (a vertical outer face, 7 cm on
    the tall lantern) whose corners sweep up and out into thick upturned tips; a concave hipped roof whose faces run
    steep under the collar and shallow at the eave (x(s) = b + (a - b)(1 - s)^1.8); four thick ROUND hip rolls from a
    curled tip beyond each fascia corner up the hips to the collar, converging on the finial; a small square collar
    tier, a round ring and a plain ball. Returns (zb, zt, ball bottom, top, tip half-width)."""
    c = cap_dims(k)
    E, tb, Ub, Fb, Ut, Ft, lip, b, q = c["E"], c["tb"], c["Ub"], c["Fb"], c["Ut"], c["Ft"], c["lip"], c["b"], c["q"]
    zb = z1 + 0.03 * k
    p.add(sq_tier(0.29 * k, z1 - 0.004, zb + 0.012 * k, ch=0.006, ch_bottom=0.006), GRT)      # band under the eaves
    ze = zb + tb + 0.004 * k
    zt = ze + c["rise"]
    a = E - lip
    segs = 16

    def ring(h, z, upf, flf, up=Ut, fl=Ft):
        # r2b: the sheet's TOP view keeps the cap a near-square with straight edges (the tips flare only at the very
        # corner): the flare falls off with |t|^8, the upturn with |t|^5
        return square_ring_2(h, z, segs, up * upf, fl * flf)

    ss = [0.08, 0.18, 0.30, 0.43, 0.56, 0.69, 0.81, 0.91, 1.0]
    xf = lambda s: b + (a - b) * (1 - s) ** q          # noqa: E731  concave hipped face
    fade = lambda s: max(0.0, 1 - s / 0.55) ** 2          # noqa: E731  the corner curl dies out up the roof
    rings = [[(0.0, 0.0, zb + 0.02 * k)],
             ring(0.30 * k, zb + 0.014 * k, 0.0, 0.0),
             ring(0.44 * k, zb + 0.003 * k, 0.35, 0.35, Ub, Fb),
             ring(E, zb, 1.0, 1.0, Ub, Fb),                          # fascia bottom edge: a small lift, some flare
             ring(E + 0.002 * k, zb + tb, 1.0, 1.0),                  # fascia top edge: the tips sweep up and out
             ring(a, ze, 0.97, 0.95)]                                 # the lip steps in onto the roof
    for s in ss[:-1]:
        rings.append(ring(xf(s), ze + (zt - ze) * s, 0.97 * fade(s), 0.95 * fade(s)))
    rings.append(ring(b, zt, 0.0, 0.0))
    rings.append([(0.0, 0.0, zt)])
    p.add(G.ring_loft(rings), GRT)
    # hip rolls: 7-point rounded sections along each hip, from a curled tip beyond the fascia corner to the collar
    tip_h = E + 0.002 * k + Ft                                        # fascia top corner (plan half-width)
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        d = Vector((sx, sy, 0)).normalized()
        perp = Vector((-sy, sx, 0)).normalized()
        up = Vector((0, 0, 1))
        r2 = math.sqrt(2)
        st = [(d * (tip_h + 0.030 * k) * r2 + up * (zb + tb + Ut + 0.030 * k), 0.046 * k, 0.040 * k),   # curled tip
              (d * (tip_h + 0.012 * k) * r2 + up * (zb + tb + Ut + 0.012 * k), 0.064 * k, 0.056 * k),
              (d * (tip_h - 0.004 * k) * r2 + up * (zb + tb + Ut * 0.98), 0.070 * k, 0.058 * k)]
        for s in ss[:-1]:
            hh = xf(s) + 0.95 * fade(s) * Ft
            st.append((d * hh * r2 + up * (ze + (zt - ze) * s + 0.97 * fade(s) * Ut),
                       0.066 * k * (1 - 0.25 * s), 0.050 * k * (1 - 0.25 * s)))
        st.append((d * (b * 0.92) * r2 + up * (zt + 0.006 * k), 0.046 * k, 0.034 * k))
        st.append((d * (b * 0.55) * r2 + up * (zt + 0.012 * k), 0.036 * k, 0.026 * k))
        secs = []
        for cc, w, hgt in st:
            dn = 0.014 * k + 0.5 * w / 2
            prof = [(-0.5, -dn), (-0.47, 0.25 * hgt), (-0.33, 0.72 * hgt), (0.0, hgt), (0.33, 0.72 * hgt),
                    (0.47, 0.25 * hgt), (0.5, -dn)]
            secs.append([cc + perp * (u * w) + up * v for u, v in prof])
        p.add(section_loft_n(secs), GRT, smooth=lambda n_: True)
    # small square collar tier, a second step, a round ring and the plain ball, scaled to finish at `top`
    zc1 = zt + 0.040 * k
    zc2 = zc1 + 0.026 * k
    p.add(rough_tier(0.165 * k, zt - 0.012 * k, zc1, ch=0.008 * k, ch_bottom=0.0, segs=2, jit=0.003), GRT)
    p.add(rough_tier(0.120 * k, zc1 - 0.002, zc2, ch=0.006 * k, ch_bottom=0.0, segs=2, jit=0.002), GRT)
    zr0, zr1 = zc2 - 0.002, zc2 + 0.02 * k
    p.add(lathe([(0, zr0), (0.072 * k, zr0), (0.078 * k, zr0 + 0.006 * k), (0.078 * k, zr1 - 0.006 * k),
                 (0.070 * k, zr1), (0, zr1)], sides=20), GRT, uv="cylbox", radius=0.07 * k,
          smooth=lambda n: abs(n.z) < 0.9)
    # r3 (judge B delta 10: 'give the hoju a pointed onion tip instead of a near-sphere; enlarge the finial slightly
    # so it reads in the top view'): a wider bulb (1.2 x the vertical radius) whose upper half draws in along an ogee
    # to a pointed tip, the sheet's hoju; total height unchanged (it still finishes at `top`)
    zb0 = zr1 - 0.004 * k
    r = (top - zb0) / 2.25                    # vertical radius of the bulb; the tip rises 1.25 r above its centre
    rw = 1.2 * r                              # horizontal radius
    zcen = zb0 + r
    prof = [(0.0, zb0)] + [(rw * math.cos(math.radians(an)), zcen + r * math.sin(math.radians(an)))
                           for an in (-75, -60, -45, -30, -15, 0, 15)]
    prof += [(0.93 * rw, zcen + 0.42 * r), (0.80 * rw, zcen + 0.66 * r), (0.60 * rw, zcen + 0.86 * r),
             (0.40 * rw, zcen + 0.99 * r), (0.22 * rw, zcen + 1.10 * r), (0.09 * rw, zcen + 1.19 * r), (0.0, top)]
    p.add(lathe(prof, sides=24), GRT, uv="box", smooth=True)
    p.cap_info = {"zb": zb, "ze": ze, "zt": zt, "tip_half": tip_h + 0.030 * k, "E": E, "b": b, "a": a,
                  "xf": xf, "fade": fade, "Ut": Ut, "Ft": Ft, "ball_d": 2 * rw, "hoju": "pointed onion (r3)"}
    return zb, zt, zb0, top, tip_h + 0.030 * k



def moss_pads(p, spots, seed=1, ns=10, tol=0.012):
    """r2: moss as REAL geometry (the sheet's moss tufts on ledges, plinth steps, cap valleys and at the ground): each
    spot becomes a low lobed cushion whose vertices are ray-cast straight down onto the part's own surface (BVH of the
    geometry built so far) and pushed out along the hit normal by a domed thickness; the rim is tucked 2 mm into the
    surface. A ray that leaves the ledge (the hit is off the spot's tangent plane by more than `tol`, or hits a face
    that does not look up) pulls that vertex inward, so a cushion never hangs over an arris. spots: dicts with x, y,
    z0 (ray start height, below any overhang), r (radius), h (thickness), ground (a miss lands on z = 0)."""
    from mathutils.bvhtree import BVHTree
    p.bm.normal_update()
    bvh = BVHTree.FromBMesh(p.bm)
    rng = __import__("random").Random(seed)
    down = Vector((0, 0, -1))
    made = 0

    def cast(x, y, z0, ground):
        hit = bvh.ray_cast(Vector((x, y, z0)), down, z0 + 1.0)
        if hit[0] is not None and (not ground or hit[0].z > 1e-4):
            return hit[0], hit[1]
        if ground and (hit[0] is None or hit[0].z <= 1e-4):
            return Vector((x, y, 0.0)), Vector((0, 0, 1))
        return None, None

    for sp in spots:
        x, y, z0, r, h, gnd = sp["x"], sp["y"], sp["z0"], sp["r"], sp["h"], sp.get("ground", False)
        c, n = cast(x, y, z0, gnd)
        if c is None or n.z < 0.45:
            continue
        ph1, ph2, a1, a2 = rng.uniform(0, 6.3), rng.uniform(0, 6.3), rng.uniform(0.12, 0.28), rng.uniform(0.08, 0.2)
        ts = [0.36, 0.66, 0.88, 1.0]
        verts = [tuple(c + n * h * rng.uniform(0.9, 1.15))]
        rows = []
        ok = True
        for j in range(ns):
            th = 2 * math.pi * j / ns + rng.uniform(-0.12, 0.12)
            rad = r * (1 + a1 * math.sin(3 * th + ph1) + a2 * math.sin(7 * th + ph2))
            dirv = Vector((math.cos(th), math.sin(th), 0))
            col = []
            for t in ts:
                rr = rad * t
                got = None
                for _ in range(6):
                    q = c + dirv * rr
                    hp, hn = cast(q.x, q.y, z0, gnd)
                    if hp is not None and hn.z > 0.45:
                        exp_z = c.z - (n.x * (hp.x - c.x) + n.y * (hp.y - c.y)) / max(n.z, 0.3)
                        if abs(hp.z - exp_z) < tol and hn.dot(n) > 0.7:
                            got = (hp, hn)
                            break
                    rr *= 0.75
                if got is None:
                    got = (c + (dirv * rr * 0.2), n)
                hp, hn = got
                thick = h * max(0.0, 1 - t ** 2) ** 0.55 * rng.uniform(0.8, 1.15) if t < 1.0 else -0.002
                col.append(len(verts))
                verts.append(tuple(hp + hn * thick))
            rows.append(col)
        if not ok:
            continue
        faces = []
        nr = len(ts)
        for j in range(ns):
            j2 = (j + 1) % ns
            faces.append((0, rows[j][0], rows[j2][0]))
            for i in range(nr - 1):
                faces.append((rows[j][i], rows[j][i + 1], rows[j2][i + 1], rows[j2][i]))
        # outward (up) winding
        v0, v1, v2 = (Vector(verts[i]) for i in faces[0])
        if (v1 - v0).cross(v2 - v0).dot(n) < 0:
            faces = [tuple(reversed(f)) for f in faces]
        ou, ov = rng.random(), rng.random()
        uvs = []
        for f in faces:                                 # per face, projected on its dominant plane (no zero-area UVs)
            fn = G._newell([Vector(verts[i]) for i in f])
            ax = max(range(3), key=lambda i_: abs(fn[i_]))
            u_, v_ = [(1, 2), (0, 2), (0, 1)][ax]
            uvs.append([(verts[i][u_] + ou, verts[i][v_] + ov) for i in f])
        p.add((verts, faces, uvs), MS, smooth=True)
        made += 1
    p.moss_count = getattr(p, "moss_count", 0) + made
    return made


def moss_cluster(spots, rng, x, y, z0, tang, n, rmin, rmax, hmm, spread, ground=False):
    """A clump of n small overlapping cushions round (x, y), strung along the tangent `tang` (the riser line)."""
    for i in range(n):
        t = rng.uniform(-1, 1) * spread
        o = rng.uniform(-0.35, 0.35) * rmax
        nx, ny = -tang[1], tang[0]
        spots.append(dict(x=x + tang[0] * t + nx * o, y=y + tang[1] * t + ny * o, z0=z0, r=rng.uniform(rmin, rmax),
                          h=hmm * rng.uniform(0.7, 1.25), ground=ground))


def lantern_moss_spots(d, k):
    """Where the sheet's lanterns carry moss (r2: clumps of small domed cushions, not flat patches): tucked into the
    inner corner of every ledge where it meets the riser above (plinth top the heaviest, tiers and the collar
    lighter), round the foot on the ground, and in the cap's valleys along the fascia lip and beside the hip rolls."""
    import random
    rng = random.Random(int(d["top"] * 777))
    spots = []
    sides = {0: ((1, 0), lambda u, dd: (u, -dd)), 1: ((0, 1), lambda u, dd: (dd, u)),
             2: ((1, 0), lambda u, dd: (u, dd)), 3: ((0, 1), lambda u, dd: (-dd, u))}

    def ledge(z, hi, ho, clusters, hmm, box=None):
        for _ in range(clusters):
            side = rng.randrange(4)
            inner = box[side % 2] if box else hi
            depth = ho - inner
            u = rng.uniform(-0.9, 0.9) * inner
            dd = inner + depth * rng.uniform(0.15, 0.35)
            tang, f = sides[side]
            x, y = f(u, dd)
            moss_cluster(spots, rng, x, y, z + 0.10 * k, tang, rng.randint(3, 6), 0.35 * depth, 0.6 * depth, hmm,
                         spread=0.05 * k + 0.4 * depth)

    hb, zb0, zb1 = d["base"]
    tiers = d["tiers"]
    ledge(zb1, tiers[0][0], hb, 9, 0.016 * k)                                   # plinth top: the thickest moss
    for i, (h, z0, z1) in enumerate(tiers):
        nxt = tiers[i + 1][0] if i + 1 < len(tiers) else d["post"][0][0]
        ledge(z1, nxt, h, 5 if i == 0 else 3, 0.011 * k)
    hc, cz0, cz1 = d["collars"][-1]
    bx, by = d["box"][0], d["box"][1]
    ledge(cz1, bx, hc, 3, 0.008 * k, box=(by, bx))
    for _ in range(10):                                                          # ground round the foot
        side = rng.randrange(4)
        tang, f = sides[side]
        x, y = f(rng.uniform(-1.0, 1.0) * hb, hb + rng.uniform(0.005, 0.025))
        moss_cluster(spots, rng, x, y, 0.06, tang, rng.randint(2, 5), 0.02, 0.045, 0.016 * k, 0.08, ground=True)
    c = cap_dims(k)
    zb = d["box"][3] + 0.03 * k
    ze = zb + c["tb"] + 0.004 * k
    zt = ze + c["rise"]
    for _ in range(7):                                                           # cap valleys
        s = rng.uniform(0.0, 0.12)
        half = c["b"] + (c["E"] - c["lip"] - c["b"]) * (1 - s) ** c["q"]
        side = rng.randrange(4)
        tang, f = sides[side]
        u = rng.uniform(-0.8, 0.8) * half
        x, y = f(u, half - 0.015 * k)
        moss_cluster(spots, rng, x, y, zt + 0.3, tang, rng.randint(2, 4), 0.015 * k, 0.03 * k, 0.012 * k, 0.06 * k)
    return spots


def lantern(name, d):
    """A granite lantern (sheet top row): stepped base with chipped arrises, waisted post with a raised panel, collars,
    light box with four-pane front and back windows and single-pane sides (library amber glass with its hotspot core),
    the r2 hipped cap (kasa()), all stone in the library granite on the triplanar path (no stretched or mirrored UVs),
    and modelled moss cushions on the ledge tops, plinth steps, cap valleys and at the ground (moss_pads())."""
    p = Part(name, "thin_upright", d["note"])
    G.seed(8001 + int(d["top"] * 100))
    hb, zb0, zb1 = d["base"]
    if d.get("base_split"):
        # r3 (round-2 judge B delta 10: 'split the tall lantern's base block into two stones with a visible seam'):
        # two dressed stones side by side along X, a 5 mm joint off-centre, a recessed stone core behind the joint
        xs, g_ = d["base_split"], 0.0025
        for x0, x1 in ((-hb, xs - g_), (xs + g_, hb)):
            hx_ = (x1 - x0) / 2
            p.add(rough_tier(hx_, zb0, zb1, ch=0.024, ch_bottom=0.0, segs=4, jit=0.013, hy=hb), GRT,
                  T((x0 + x1) / 2, 0, 0))
        p.add(box(xs - 0.004, xs + 0.004, -hb + 0.022, hb - 0.022, zb0 + 0.004, zb1 - 0.026), MO)
    else:
        p.add(rough_tier(hb, zb0, zb1, ch=0.024, ch_bottom=0.0, segs=5, jit=0.013), GRT)
    for (h, z0, z1) in d["tiers"]:
        p.add(rough_tier(h, z0, z1, ch=0.018, ch_bottom=0.005, segs=5, jit=0.011), GRT)
    post = d["post"]
    p.add(sq_loft([(0, 0, post[0][1])] + [(h, h, z) for h, z in post] + [(0, 0, post[-1][1])]), GRT)
    px, pz0, pz1, ph = d["panel"]                                                   # raised panel, front and back
    for s in (-1, 1):
        y0, y1 = (s * (ph + 0.008), s * (ph - 0.004))
        p.add(box(-px, px, min(y0, y1), max(y0, y1), pz0, pz1, 0.003), GRT)
    for (h, z0, z1) in d["collars"]:
        p.add(rough_tier(h, z0, z1, ch=0.016, ch_bottom=0.012, segs=4, jit=0.009), GRT)
    # light box
    hx, hy, z0, z1, ox, oy = d["box"]
    rail = d["rail"]
    col = d["pillar"]
    p.add(box(-hx, hx, -hy, hy, z0, z0 + rail, 0.004), GRT)                          # sill
    p.add(box(-hx, hx, -hy, hy, z1 - rail, z1, 0.005), GRT)                          # head
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.add(box(min(sx * hx, sx * (hx - col)), max(sx * hx, sx * (hx - col)),
                      min(sy * hy, sy * (hy - col)), max(sy * hy, sy * (hy - col)), z0 + rail, z1 - rail, 0.004), GRT)
    wz0, wz1 = z0 + rail, z1 - rail
    for sx in (-1, 1):                                                               # side jambs: narrow side windows
        for sy in (-1, 1):
            ya, yb = sorted((sy * oy, sy * (hy - col)))
            p.add(box(min(sx * (hx - 0.03), sx * hx), max(sx * (hx - 0.03), sx * hx), ya, yb, wz0, wz1, 0.003), GRT)
    fr, bar = d["muntin"]
    recess = 0.03

    def pane_y(sy):
        yv = sy * (hy - recess)
        vs, fs = box(-ox, ox, yv - 0.003, yv + 0.003, wz0, wz1)
        uvs = []
        for f in fs:
            pts = [Vector(vs[i]) for i in f]
            n = G._newell(pts)
            if abs(n.y) > 0.5 * n.length:
                uvs.append([((q.x + ox) / (2 * ox) if n.y < 0 else (ox - q.x) / (2 * ox), (q.z - wz0) / (wz1 - wz0))
                            for q in pts])
            else:
                uvs.append(G.plane_uv(pts, n, 0.25))       # thin pane edges: a real planar patch
        p.add((vs, fs, uvs), GL)

    def pane_x(sx):
        xv = sx * (hx - recess)
        vs, fs = box(xv - 0.003, xv + 0.003, -oy, oy, wz0, wz1)
        uvs = []
        for f in fs:
            pts = [Vector(vs[i]) for i in f]
            n = G._newell(pts)
            if abs(n.x) > 0.5 * n.length:
                uvs.append([((q.y + oy) / (2 * oy), (q.z - wz0) / (wz1 - wz0)) for q in pts])
            else:
                uvs.append(G.plane_uv(pts, n, 0.25))       # thin pane edges: a real planar patch
        p.add((vs, fs, uvs), GL)

    for s in (-1, 1):
        pane_y(s)
        pane_x(s)
        ya, yb = sorted((s * (hy - recess + 0.004), s * (hy - recess + 0.022)))    # front / back lattice: frame + cross
        zm = (wz0 + wz1) / 2
        p.add(box(-ox, ox, ya, yb, wz0, wz0 + fr), TB)
        p.add(box(-ox, ox, ya, yb, wz1 - fr, wz1), TB)
        p.add(box(-ox, -ox + fr, ya, yb, wz0 + fr, wz1 - fr), TB)
        p.add(box(ox - fr, ox, ya, yb, wz0 + fr, wz1 - fr), TB)
        p.add(box(-bar / 2, bar / 2, ya, yb, wz0 + fr, wz1 - fr), TB)
        p.add(box(-ox + fr, -bar / 2, ya, yb, zm - bar / 2, zm + bar / 2), TB)
        p.add(box(bar / 2, ox - fr, ya, yb, zm - bar / 2, zm + bar / 2), TB)
        xa, xb = sorted((s * (hx - recess + 0.004), s * (hx - recess + 0.022)))    # side lattice: frame + one bar
        p.add(box(xa, xb, -oy, oy, wz0, wz0 + fr), TB)
        p.add(box(xa, xb, -oy, oy, wz1 - fr, wz1), TB)
        p.add(box(xa, xb, -oy, -oy + fr, wz0 + fr, wz1 - fr), TB)
        p.add(box(xa, xb, oy - fr, oy, wz0 + fr, wz1 - fr), TB)
        p.add(box(xa, xb, -bar / 2, bar / 2, wz0 + fr, wz1 - fr), TB)
    k = d["cap_k"]
    zb, zt, zball, top, hc = kasa(p, z1, k, d["top"])
    moss_pads(p, lantern_moss_spots(d, k), seed=int(d["top"] * 1000))
    # UCX (thin upright class, spec R8 deviation recorded in BUILD_NOTES): base, tiers, post, collars + light box, cap
    p.hull_box(-hb, hb, -hb, hb, zb0, zb1)
    tz0 = d["tiers"][0][1]
    ht = d["tiers"][0][0]
    p.hull_box(-ht, ht, -ht, ht, tz0, d["tiers"][-1][2])
    pm = max(h for h, _ in post)
    p.hull_box(-pm, pm, -pm, pm, post[0][1], post[-1][1])
    hcl = max(h for h, _, _ in d["collars"])
    p.hull_box(-hcl, hcl, -hcl, hcl, d["collars"][0][1], z1)
    e = cap_dims(k)["E"]
    p.hull([(sx * e, sy * e, zb) for sx in (-1, 1) for sy in (-1, 1)] +
           [(sx * e, sy * e, zb + cap_dims(k)["tb"]) for sx in (-1, 1) for sy in (-1, 1)] +
           [(sx * 0.165 * k, sy * 0.165 * k, zt + 0.040 * k) for sx in (-1, 1) for sy in (-1, 1)] + [(0, 0, top)])
    return p


LANTERN_TALL = {
    "note": "tall granite lantern, 2.00 m (sheet about 2.08 m by its 1.8 m figure; spec wins)",
    "base": (0.375, 0.0, 0.29), "tiers": [(0.30, 0.29, 0.38), (0.25, 0.38, 0.48)],
    "post": [(0.18, 0.48), (0.16, 0.53), (0.145, 0.60), (0.14, 0.62), (0.14, 0.84), (0.15, 0.89), (0.17, 0.93)],
    "panel": (0.085, 0.645, 0.815, 0.14),
    "collars": [(0.20, 0.925, 0.98), (0.27, 0.98, 1.08)],
    "box": (0.20, 0.17, 1.08, 1.37, 0.145, 0.07), "rail": 0.03, "pillar": 0.055, "muntin": (0.02, 0.016),
    "cap_k": 1.0, "top": 2.00, "base_split": 0.045,
}
LANTERN_SHORT = {
    "note": "short granite lantern, 1.20 m (sheet variant about 1.77 m by its figure; prompt and task: about 1.2 m)",
    "base": (0.265, 0.0, 0.16), "tiers": [(0.19, 0.16, 0.25)],
    "post": [(0.13, 0.25), (0.115, 0.29), (0.105, 0.32), (0.105, 0.42), (0.115, 0.445), (0.125, 0.465)],
    "panel": (0.055, 0.315, 0.405, 0.105),
    "collars": [(0.19, 0.46, 0.53)],
    "box": (0.14, 0.125, 0.53, 0.745, 0.10, 0.05), "rail": 0.022, "pillar": 0.04, "muntin": (0.015, 0.012),
    "cap_k": 0.70, "top": 1.20,
}


# --------------------------------------------------------------------------- well ring

WELL_R, WELL_H, WELL_RIN = 0.60, 0.80, 0.41
COURSE_H = (0.205, 0.195, 0.21, 0.19)
COURSE_N = (13, 14, 13, 14)


def orient(face, vs, expect):
    pts = [Vector(vs[i]) for i in face]
    return face if G._newell(pts).dot(expect) >= 0 else tuple(reversed(face))


def pillow_block(a0, a1, ri, ro, zb, zt, ch, bulge, nu=7, nv=5, rough=0.004):
    """r2: a rough-faced, PILLOWED ashlar block of the ring (judges: 'pillowed, rough-faced, varied'). The outer face is
    an nu x nv grid: its border rolls back by `ch` into a deep joint (the arris is rounded over two rows), the field
    bulges out by up to `bulge` with a domed profile that differs per block (off-centre crown, uneven fall-off), and
    every interior vertex carries a hammer-dressed jitter of up to `rough` metres. Flat top, bottom, ends, inner face."""
    us = [i / (nu - 1) for i in range(nu)]
    arc = (a1 - a0) * ro
    cu = min(0.22, ch * 1.3 / arc)
    us[1], us[-2] = cu, 1 - cu
    vz = [j / (nv - 1) for j in range(nv)]
    cz = min(0.25, ch * 1.3 / (zt - zb))
    vz[1], vz[-2] = cz, 1 - cz
    cu0, cv0 = 0.5 + (G.rnd() - 0.5) * 0.3, 0.5 + (G.rnd() - 0.5) * 0.3     # off-centre crown
    pw = 1.2 + 1.6 * G.rnd()                                                  # flat-topped or peaked pillow
    vs = []
    idx = {}
    for i, u in enumerate(us):
        for j, v in enumerate(vz):
            edge = i in (0, nu - 1) or j in (0, nv - 1)
            ring2 = i in (1, nu - 2) or j in (1, nv - 2)
            if edge:
                r = ro - ch
            else:
                du = abs(u - cu0) / max(cu0, 1 - cu0)
                dv = abs(v - cv0) / max(cv0, 1 - cv0)
                w = max(0.0, 1 - max(du, dv) ** pw)
                r = ro - (0.45 * ch if ring2 else 0.0) + bulge * (0.35 + 0.65 * w) + (G.rnd() - 0.5) * 2 * rough
            a = a0 + (a1 - a0) * (u + ((G.rnd() - 0.5) * 0.03 if not edge else 0.0))
            z = zb + (zt - zb) * (v + ((G.rnd() - 0.5) * 0.04 if not edge else 0.0))
            idx[i, j] = len(vs)
            vs.append((r * math.cos(a), r * math.sin(a), z))
    ib0 = len(vs)
    vs += [(ri * math.cos(a0), ri * math.sin(a0), zb), (ri * math.cos(a1), ri * math.sin(a1), zb),
           (ri * math.cos(a1), ri * math.sin(a1), zt), (ri * math.cos(a0), ri * math.sin(a0), zt)]
    ib_a0, ib_a1, it_a1, it_a0 = ib0, ib0 + 1, ib0 + 2, ib0 + 3
    am = (a0 + a1) / 2
    rad = Vector((math.cos(am), math.sin(am), 0))
    fs = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            fs.append(orient((idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]), vs, rad))
    zu, zd = Vector((0, 0, 1)), Vector((0, 0, -1))
    for i in range(nu - 1):                                    # top and bottom: fans from the inner corner
        fs.append(orient((it_a0, idx[i, nv - 1], idx[i + 1, nv - 1]), vs, zu))
        fs.append(orient((ib_a0, idx[i, 0], idx[i + 1, 0]), vs, zd))
    fs.append(orient((it_a0, idx[nu - 1, nv - 1], it_a1), vs, zu))
    fs.append(orient((ib_a0, idx[nu - 1, 0], ib_a1), vs, zd))
    t0 = Vector((math.sin(a0), -math.cos(a0), 0))               # end faces: fans from the inner corners
    t1 = Vector((-math.sin(a1), math.cos(a1), 0))
    for j in range(nv - 1):
        fs.append(orient((ib_a0, idx[0, j], idx[0, j + 1]), vs, t0))
        fs.append(orient((ib_a1, idx[nu - 1, j], idx[nu - 1, j + 1]), vs, t1))
    fs.append(orient((ib_a0, idx[0, nv - 1], it_a0), vs, t0))
    fs.append(orient((ib_a1, idx[nu - 1, nv - 1], it_a1), vs, t1))
    fs.append(orient((ib_a0, ib_a1, it_a1, it_a0), vs, -rad))
    return (vs, fs), rad


def well():
    """r2: rough-faced, pillowed granite ashlar in the library granite (triplanar); course heights, block lengths,
    set-back and bulge all vary per block; 1.0 cm joints rolled back 2.0 cm at the arrises over a DARK mortar core
    set 4.5 cm behind the faces (the sheet's dark, deep joints); per-block tone variation goes into the Wear colour's
    grime channel after the bake (Unreal reads the same vertex colour)."""
    p = Part("SM_DKP_Stone_Well", "low_cover", "round granite-block well ring, 1.20 m across x 0.80 m (spec)")
    G.seed(8101)
    gap = 0.010
    z = 0.0
    for c, (ch_, n) in enumerate(zip(COURSE_H, COURSE_N)):
        z0, z1 = z, z + ch_
        z = z1
        w = widths(2 * math.pi, n, 0.6, 1.6)          # r3: more irregular lengths
        a = (0.5 * (c % 2) + 0.2 * G.rnd()) * 2 * math.pi / n
        for i in range(n):
            a0, a1 = a + gap / WELL_R / 2, a + w[i] - gap / WELL_R / 2
            a += w[i]
            zb = z0 + (gap / 2 if c else 0.0) + 0.004 * G.rnd()
            zt = z1 - (gap / 2 if c < len(COURSE_H) - 1 else 0.0) - (0.012 * G.rnd() if c == len(COURSE_H) - 1 else 0.004 * G.rnd())
            # r3 (judge B delta 6): a slightly barrelled ring (the middle courses 1.2 cm proud of the top and bottom
            # ones), more pillowed and hammer-chipped faces
            barrel = (0.0, 0.012, 0.012, 0.002)[c]
            ro = WELL_R - 0.024 - 0.008 * G.rnd() + barrel
            geo, rad = pillow_block(a0, a1, WELL_RIN, ro, zb, zt, 0.018, 0.026 + 0.022 * G.rnd(), rough=0.008)
            sm = (lambda rr: (lambda nn: abs(nn.z) < 0.75 and nn.dot(rr) > 0.35))(rad)
            p.add(geo, GRT, uv="cylbox", axis="z", radius=WELL_R, smooth=sm)
    # dark mortar core behind the joints (a closed annulus) and dark water 0.68 m below the rim
    # r3 (judge B delta 6: 'replace the black recessed mortar lines with lighter, shallower mortar'): the core sits
    # 3.2 cm behind the nominal face (r2 4.5) in a light grey lime mortar (M_DKP_Stone_WellMortar)
    prof = [(WELL_RIN + 0.012, 0.002), (WELL_R - 0.032, 0.002), (WELL_R - 0.032, WELL_H - 0.02),
            (WELL_RIN + 0.012, WELL_H - 0.02)]
    nseg = 28
    rings = [[(r * math.cos(2 * math.pi * i / nseg), r * math.sin(2 * math.pi * i / nseg), zz) for i in range(nseg)]
             for r, zz in prof]
    vs, fs = G.ring_loft(rings + [rings[0]])
    last = len(vs) - nseg
    fs = [tuple(i - last if i >= last else i for i in f) for f in fs]
    p.add((vs[:last], fs), MW, uv="cylbox", radius=WELL_R)
    circ = [(0.425 * math.cos(2 * math.pi * i / 24), 0.425 * math.sin(2 * math.pi * i / 24)) for i in range(24)]
    p.add(prism(circ, 0.09, 0.12), WA)
    # moss in the bottom joints and round the foot (the sheet's well has green at its base)
    import random
    rng = random.Random(8102)
    spots = []
    for _ in range(9):
        th = rng.uniform(0, 2 * math.pi)
        rr = WELL_R + rng.uniform(0.0, 0.02)
        moss_cluster(spots, rng, rr * math.cos(th), rr * math.sin(th), 0.05, (-math.sin(th), math.cos(th)),
                     rng.randint(2, 5), 0.02, 0.045, 0.015, 0.09, ground=True)
    moss_pads(p, spots, seed=8103)
    p.hull_cyl(0, 0, WELL_R, 0.0, WELL_H, sides=16)
    return p


BEAM_HALF, BEAM_Z0, BEAM_Z1 = 0.065, 0.036, 0.166       # the cover's crossbeam (cover space)
BEAM_X = 0.62                                            # beam ends butt against the frame posts' inner faces


def well_cover():
    """Round plank cover with a HEAVY squared crossbeam (f1, the judge): 13 x 13 cm, spanning the full width past the
    ring to butt against both frame posts (inner faces at X +-0.62 on both frames), iron end straps with bolts; the rope
    is tied round it. Pivot: the underside centre (sits on the rim, +0.80)."""
    p = Part("SM_DKP_Stone_WellCover", "low_cover", "round plank cover with a heavy crossbeam; sits on the rim (+0.80)")
    G.seed(8201)
    r = 0.50
    ws = widths(0.96, 6, 0.8, 1.2)
    x = -0.48
    for i in range(6):
        xa, xb = x + 0.004, x + ws[i] - 0.004
        x += ws[i]
        m = 7
        bot = [(xa + (xb - xa) * kk / m, -math.sqrt(max(r * r - (xa + (xb - xa) * kk / m) ** 2, 0))) for kk in range(m + 1)]
        top = [(xx, -yy) for xx, yy in reversed(bot)]
        t = 0.034 + 0.004 * G.rnd()
        p.add(prism(bot + top, 0.0, t), TB, grain=1)
    p.add(box(-BEAM_X, BEAM_X, -BEAM_HALF, BEAM_HALF, BEAM_Z0, BEAM_Z1, 0.010), TB, grain=0)
    for s in (-1, 1):                                                               # iron end straps (U round the beam)
        xa, xb = sorted((s * (BEAM_X - 0.005), s * (BEAM_X - 0.105)))
        t = 0.006
        p.add(box(xa, xb, -BEAM_HALF - t, BEAM_HALF + t, BEAM_Z1, BEAM_Z1 + t), IR)
        p.add(box(xa, xb, -BEAM_HALF - t, -BEAM_HALF, BEAM_Z0 + 0.01, BEAM_Z1), IR)
        p.add(box(xa, xb, BEAM_HALF, BEAM_HALF + t, BEAM_Z0 + 0.01, BEAM_Z1), IR)
        xm = s * (BEAM_X - 0.055)
        for zz in (BEAM_Z0 + 0.045, BEAM_Z1 - 0.035):
            rivet(p, xm, -BEAM_HALF - t, zz, "-y", r=0.012, h=0.008)
            rivet(p, xm, BEAM_HALF + t, zz, "+y", r=0.012, h=0.008)
        rivet(p, xm, 0.0, BEAM_Z1 + t, "+z", r=0.012, h=0.008)
    for xx in (-0.30, 0.30):                                                        # bolts through beam into planks
        rivet(p, xx, 0.0, BEAM_Z1, "+z", r=0.011, h=0.007)
    p.hull_cyl(0, 0, r, 0.0, 0.038, sides=16)
    p.hull_box(-BEAM_X, BEAM_X, -BEAM_HALF, BEAM_HALF, BEAM_Z0, BEAM_Z1)
    return p


# --------------------------------------------------------------------------- well frames

AXLE_Z = 1.54           # pulley axle height above the ground (both frames); the yoke top meets the tie beam at +1.70
YOKE_TOP = 0.16
SHEAVE_R, GROOVE_R = 0.124, 0.103
BUCKET_BOTTOM, BUCKET_GRIP = 0.92, 0.36      # grip = bail top above the bucket bottom
ROPE_R = 0.011
BUCKET_X = GROOVE_R + ROPE_R


def post_irons(p, x, half, z_list=(0.22, 0.62)):
    for z in z_list:
        band_rect_at(p, x, half, z, z + 0.05)
        rivet(p, x, -half - 0.005, z + 0.025, "-y", r=0.012)
        rivet(p, x, half + 0.005, z + 0.025, "+y", r=0.012)


def band_rect_at(p, cx, half, z0, z1, t=0.005):
    p.add(box(cx - half - t, cx + half + t, -half - t, -half, z0, z1), IR)
    p.add(box(cx - half - t, cx + half + t, half, half + t, z0, z1), IR)
    p.add(box(cx - half - t, cx - half, -half, half, z0, z1), IR)
    p.add(box(cx + half, cx + half + t, -half, half, z0, z1), IR)


def plank_slope(p, M, across, length, t_rng, gap, lap, grain, along="y", sgn=1, seed_len=0.04):
    """Loose roof boards on one slope (slope frame M: the board runs along `along`, from the ridge out). across =
    (a0, a1): the span the boards cover; boards alternate low / lapped high (board-and-batten look), with irregular
    widths, lengths, thickness, tilt and yaw (f1: 3.5-4.3 cm thick, the sheet's chunky roof)."""
    a0, a1 = across
    n = max(3, round((a1 - a0) / 0.155))
    ws = widths(a1 - a0, n, 0.75, 1.3)
    x = a0
    for i in range(n):
        c0, c1 = x + gap / 2, x + ws[i] - gap / 2
        x += ws[i]
        hi = i % 2 == 1
        if hi:
            c0, c1 = c0 - lap, c1 + lap
        t = t_rng[0] + (t_rng[1] - t_rng[0]) * G.rnd()
        z0 = (t_rng[0] * 0.8) if hi else 0.0
        ll = length + seed_len * G.rnd()
        tilt = (G.rnd() - 0.5) * 3.0
        yaw = (G.rnd() - 0.5) * 1.6
        if along == "y":
            ya, yb = sorted((-sgn * 0.012, sgn * ll))
            Mb = M @ T((c0 + c1) / 2, 0, 0) @ R(tilt, "Y") @ R(yaw, "Z")
            p.add(box(-(c1 - c0) / 2, (c1 - c0) / 2, ya, yb, z0, z0 + t, 0.005), TG, Mb, grain=1)
        else:
            xa, xb = sorted((-sgn * 0.012, sgn * ll))
            Mb = M @ T(0, (c0 + c1) / 2, 0) @ R(tilt, "X") @ R(yaw, "Z")
            p.add(box(xa, xb, -(c1 - c0) / 2, (c1 - c0) / 2, z0, z0 + t, 0.005), TG, Mb, grain=0)


def well_frame():
    """Plank-roofed frame (sheet, middle row left): two heavy posts strapped to the ring, a tie beam with knee blocks,
    rafters on two purlins a side, a ridge beam, a two-slope roof of THICK irregular lapped boards laid down the slope
    (silver-grey TimberGrey), a fascia board along each eave and ridge boards on top."""
    p = Part("SM_DKP_Stone_WellFrame", "thin_upright", "plank-roofed timber well frame; origin = the well centre")
    G.seed(8301)
    px, ph = 0.68, 0.06
    for s in (-1, 1):
        board(p, s * px - ph, s * px + ph, -ph, ph, 0.0, 2.10, bevel=0.008, jitter=0.0)
        post_irons(p, s * px, ph)
        kx = sorted((s * (px - ph), s * (px - ph - 0.12)))
        board(p, kx[0], kx[1], -0.05, 0.05, 1.60, 1.70, bevel=0.006)            # knee blocks under the tie
    board(p, -0.86, 0.86, -0.055, 0.055, 1.70, 1.82, bevel=0.008, jitter=0.0)   # tie beam
    for x in (-0.60, 0.60):
        rivet(p, x, -0.055, 1.76, "-y", r=0.012)
    zr, run, rise = 2.18, 0.70, 0.24
    th = math.degrees(math.atan2(rise, run))
    L = math.hypot(run, rise)
    board(p, -0.92, 0.92, -0.045, 0.045, 2.03, 2.15, bevel=0.006, jitter=0.0)   # ridge beam
    for s, a in ((-1, th), (1, -th)):
        M = T(0, 0, zr) @ R(a, "X")
        for x in (-px, 0.0, px):                                                  # rafters under the boards
            ya, yb = sorted((0.0, s * (L - 0.02)))
            p.add(box(x - 0.035, x + 0.035, ya, yb, -0.075, 0.0, 0.005), TB, M, grain=1)
        for yy in (0.30, 0.60):                                                   # purlins under the rafters
            ya, yb = sorted((s * (yy - 0.035), s * (yy + 0.035)))
            p.add(box(-0.90, 0.90, ya, yb, -0.14, -0.075, 0.005), TB, M, grain=0)
        plank_slope(p, M, (-0.94, 0.94), L + 0.03, (0.035, 0.043), 0.012, 0.018, 1, along="y", sgn=s)
        ya, yb = sorted((s * (L - 0.005), s * (L + 0.03)))                        # fascia along the eave
        p.add(box(-0.95, 0.95, ya, yb, -0.11, 0.005, 0.005), TB, M, grain=0)
        ya, yb = sorted((0.0, s * 0.12))
        p.add(box(-0.95, 0.95, ya, yb, 0.070, 0.095, 0.005), TG, M, grain=0)    # ridge boards
    for s in (-1, 1):
        p.hull_box(s * px - ph, s * px + ph, -ph, ph, 0.0, 2.10)
    p.hull_box(-0.86, 0.86, -0.055, 0.055, 1.70, 1.82)
    ze = zr - rise
    p.hull([(x, y, z) for x in (-0.95, 0.95) for (y, z) in ((-run - 0.06, ze - 0.06), (run + 0.06, ze - 0.06),
                                                           (0, zr + 0.10), (0, zr - 0.12))])
    return p


def well_frame_gable():
    """The lighter gable variant (sheet, middle row centre): slimmer posts, a tie beam on the post heads, a king post, a
    steep gable roof (ridge front-to-back) of separate thick boards with gaps, a ridge board, barge rafters, two more
    rafters and a purlin a side underneath (the underside is no longer bare)."""
    p = Part("SM_DKP_Stone_WellFrameGable", "thin_upright", "lighter gable-frame variant; origin = the well centre")
    G.seed(8401)
    px, ph = 0.665, 0.045
    for s in (-1, 1):
        board(p, s * px - ph, s * px + ph, -ph, ph, 0.0, 1.80, bevel=0.006, jitter=0.0)
        post_irons(p, s * px, ph)
    board(p, -0.80, 0.80, -0.055, 0.055, 1.70, 1.82, bevel=0.006, jitter=0.0)   # tie beam (r3: = the plank frame's)
    zr, run = 2.30, 0.86
    rise = zr - 1.80
    th = math.degrees(math.atan2(rise, run))
    L = math.hypot(run, rise)
    board(p, -0.04, 0.04, -0.04, 0.04, 1.82, zr - 0.02, bevel=0.005, jitter=0.0)  # king post
    board(p, -0.035, 0.035, -0.56, 0.56, zr - 0.10, zr - 0.02, bevel=0.005, jitter=0.0)   # ridge beam (along Y)
    for s, a in ((-1, -th), (1, th)):
        M = T(0, 0, zr) @ R(a, "Y")
        for y in (-0.47, -0.16, 0.16, 0.47):                                      # rafters (outer two = barge)
            xa, xb = sorted((0.0, s * (L + 0.02)))
            p.add(box(xa, xb, y - 0.03, y + 0.03, -0.07, 0.0, 0.005), TB, M, grain=0)
        xa, xb = sorted((s * 0.42, s * 0.49))
        p.add(box(xa, xb, -0.52, 0.52, -0.13, -0.07, 0.005), TB, M, grain=1)     # purlin under the rafters
        plank_slope(p, M, (-0.54, 0.54), L + 0.05, (0.035, 0.042), 0.016, 0.0, 0, along="x", sgn=s)
        xa, xb = sorted((0.0, s * 0.10))
        p.add(box(xa, xb, -0.56, 0.56, 0.042, 0.068, 0.005), TG, M, grain=1)    # ridge boards
    for s in (-1, 1):
        p.hull_box(s * px - ph, s * px + ph, -ph, ph, 0.0, 1.80)
    p.hull_box(-0.80, 0.80, -0.055, 0.055, 1.70, 1.82)
    ze = zr - rise
    p.hull([(x, y, z) for y in (-0.57, 0.57) for (x, z) in ((-run - 0.08, ze - 0.06), (run + 0.08, ze - 0.06),
                                                           (0, zr + 0.09), (0, zr - 0.12))])
    return p


def well_pulley():
    """f1 pulley: a 32-segment sheave with bevelled rims, dished sides, a round rope groove and smooth normals (r0's
    24-segment wheel showed facets and a cyl-UV split on its flat sides); a hub boss; an iron axle pin with caps; a
    yoke of two wooden cheek blocks and an iron head plate that bolts to the tie-beam underside 0.16 m above the axle.
    Pivot = the axle centre (the wheel turns about local Y)."""
    p = Part("SM_DKP_Stone_WellPulley", "thin_upright", "pulley; pivot on the axle (local Y)")
    R_ = SHEAVE_R
    g = GROOVE_R
    wheel = [(0, -0.030), (0.045, -0.030), (0.07, -0.024), (0.098, -0.024), (R_ - 0.010, -0.030), (R_ - 0.003, -0.030),
             (R_, -0.026), (R_, -0.019), (g + 0.012, -0.013), (g + 0.004, -0.007), (g, 0.0), (g + 0.004, 0.007),
             (g + 0.012, 0.013), (R_, 0.019), (R_, 0.026), (R_ - 0.003, 0.030), (R_ - 0.010, 0.030), (0.098, 0.024),
             (0.07, 0.024), (0.045, 0.030), (0, 0.030)]
    # lathe's profile runs bottom -> top along its own z (= -Y after the turn); smooth everywhere but the flat faces
    p.add(lathe(wheel, sides=32, axis="y"), TB, uv="cylbox", axis="y", radius=R_ * 0.9,
          smooth=lambda n: abs(n.y) < 0.97)
    p.add(lathe([(0, -0.036), (0.034, -0.036), (0.038, -0.032), (0.038, 0.032), (0.034, 0.036), (0, 0.036)], sides=20,
                axis="y"), TB, uv="cylbox", axis="y", radius=0.036, smooth=lambda n: abs(n.y) < 0.97)
    p.add(lathe([(0, -0.068), (0.020, -0.068), (0.020, -0.060), (0.010, -0.060), (0.010, 0.060), (0.020, 0.060),
                 (0.020, 0.068), (0, 0.068)], sides=10, axis="y"), IR, uv="cylbox", axis="y", radius=0.02,
          smooth=lambda n: abs(n.y) < 0.97)
    for s in (-1, 1):                                                                # yoke cheeks + iron cheek plates
        ya, yb = sorted((s * 0.038, s * 0.060))
        p.add(box(-0.034, 0.034, ya, yb, -0.050, YOKE_TOP - 0.012, 0.004), TB, grain=2)
        yc = s * 0.060
        ya, yb = sorted((yc, yc + s * 0.004))
        p.add(box(-0.022, 0.022, ya, yb, -0.035, YOKE_TOP - 0.02), IR)
    # r3 (round-2 judge B delta 6: 'hang the pulley from a rope lashing around the crossbar, as in the reference,
    # instead of the iron strap with a black square cap'): a wooden crosshead on the cheeks, and three turns of rope
    # each side lashing it up round the tie beam (the beam: 11 cm deep, 12 cm tall, its underside at the yoke top)
    ch0, ch1 = 0.136, YOKE_TOP - 0.002
    p.add(box(-0.092, 0.092, -0.066, 0.066, ch0, ch1, 0.006), TB, grain=0)
    rl = 0.0075
    bt = YOKE_TOP + 0.12                                                             # the tie beam's top
    for sx in (-1, 1):
        for kx, xo in enumerate((0.050, 0.066, 0.082)):
            x = sx * xo
            pts = []
            # a rounded rectangle in the YZ plane: over the beam top, down its sides, under the crosshead
            for (cy, cz, a0) in ((0.055, bt, 0), (-0.055, bt, 90), (-0.066, ch0, 180), (0.066, ch0, 270)):
                for kk in range(5):
                    an = math.radians(a0 + 90 * kk / 4)
                    pts.append((x + 0.0012 * math.sin(3 * an + kx), cy + (rl + 0.0005) * math.cos(an),
                                cz + (rl + 0.0005) * math.sin(an)))
            pts.append(pts[0])
            pts.append(pts[1])
            p.add(tube(pts, rl, sides=6, u_tile=ROPE_TILE_U, v_tile=2 * math.pi * rl), RP, smooth=True)
    p.hull_box(-R_ - 0.002, R_ + 0.002, -0.068, 0.068, -R_ - 0.002, YOKE_TOP)
    return p


def well_bucket():
    """f1 bucket: 20 staves (was 12, facets showed), a bevelled rim, two iron hoops, two tall wooden LUGS (ears) on the
    staves carrying the iron bail on pins. Pivot = the bail grip (the rope's hook point)."""
    p = Part("SM_DKP_Stone_WellBucket", "prop_small", "staved bucket; pivot at the bail grip")
    g = BUCKET_GRIP
    M = T(0, 0, -g)
    nS = 20
    staves = [(0, 0.0), (0.118, 0.0), (0.126, 0.008), (0.130, 0.02), (0.1445, 0.255), (0.1445, 0.262), (0.141, 0.266),
              (0.134, 0.266), (0.1305, 0.262), (0.119, 0.04), (0, 0.04)]
    p.add(lathe(staves, sides=nS), TB, M, uv="cylbox", swap=True, radius=0.14, smooth=lambda n: abs(n.z) < 0.9)
    for (z0, z1) in ((0.045, 0.075), (0.195, 0.225)):
        rr = lambda zz: 0.130 + (0.1445 - 0.130) * (zz - 0.02) / 0.235   # noqa: E731  stave radius at zz
        ri0, ri1 = rr(z0) - 0.001, rr(z1) - 0.001
        rings = [[(r * math.cos(2 * math.pi * i / nS), r * math.sin(2 * math.pi * i / nS), zz) for i in range(nS)]
                 for r, zz in ((ri0, z0), (ri0 + 0.006, z0), (ri1 + 0.006, z1), (ri1, z1))]
        vs, fs = G.ring_loft(rings + [rings[0]])
        last = len(vs) - nS
        fs = [tuple(i - last if i >= last else i for i in f) for f in fs]
        p.add((vs[:last], fs), IR, M, uv="cylbox", radius=0.14, smooth=lambda n: abs(n.z) < 0.9)
    zp = 0.305                                                                        # bail pin height
    for s in (-1, 1):                                                                 # lugs: taller staves, rounded top
        x0, x1 = sorted((s * 0.140, s * 0.162))
        p.add(box(x0, x1, -0.022, 0.022, 0.15, zp + 0.030, 0.006), TB, M, grain=2)
        rivet(p, s * 0.162, 0.0, zp - g, "+x" if s > 0 else "-x", r=0.010, h=0.006)     # pin heads (pivot space)
    path = [(0.170 * math.cos(math.radians(a)), 0.0, zp + (g - zp) * math.sin(math.radians(a)))
            for a in range(180, -1, -10)]
    # r3 (judge B delta 6: 'make the bucket bail a knotted rope loop, not an iron handle'): a rope bail through the
    # lugs, knotted outside each lug
    rb_ = 0.0085
    p.add(tube(path, rb_, sides=6, u_tile=ROPE_TILE_U, v_tile=2 * math.pi * rb_), RP, M, smooth=True)
    for s in (-1, 1):
        knot = [(0, 0.0), (0.016, 0.004), (0.019, 0.016), (0.014, 0.028), (0, 0.032)]
        p.add(lathe([(r_, z_) for r_, z_ in knot], sides=8, axis="y"), RP,
              M @ T(s * 0.170, 0.0, zp) @ R(90 * s, "Z") @ T(0, 0.010, 0), uv="cyl", radius=0.016, smooth=True)
    p.hull_cyl(0, 0, 0.146, -g, 0.266 - g, sides=12)
    return p


def rope_path():
    """The rope in well space: over the wheel groove; the right strand down to the bucket bail (a loop round the grip and
    a knot); the left strand straight down to the cover's heavy crossbeam, round it in two tight turns and a short tail
    (the sheet ties the rope to the beam). Both frames hang the pulley at the same height, so one rope serves both."""
    rc = GROOVE_R + ROPE_R
    over = [(rc * math.cos(math.radians(a)), 0.0, AXLE_Z + rc * math.sin(math.radians(a))) for a in range(180, -1, -10)]
    grip = BUCKET_BOTTOM + BUCKET_GRIP
    right = [(rc, 0, AXLE_Z - 0.05), (rc, 0, grip + 0.06), (BUCKET_X, 0, grip + 0.03)]
    loop = [(BUCKET_X, 0.018 * math.sin(math.radians(a)), grip + 0.012 * math.cos(math.radians(a)) + 0.018)
            for a in range(0, 331, 30)]
    main = list(reversed(right)) + list(reversed(over))       # bail -> up the right strand -> over the wheel
    zc = WELL_H + (BEAM_Z0 + BEAM_Z1) / 2                     # beam centre (well space), beam along X
    a_ = BEAM_HALF + ROPE_R + 0.002                            # superellipse half size round the square beam
    left = [(-rc, 0, AXLE_Z - 0.06), (-rc, 0, zc + a_ + 0.08)]
    wrap = []
    turns, steps = 2.0, 16
    for i in range(int(turns * steps) + 5):
        th = math.pi / 2 + 2 * math.pi * i / steps            # start on top, go over to -y (front) and round
        c, s = math.cos(th), math.sin(th)
        y = a_ * math.copysign(abs(c) ** 0.45, c)
        z = a_ * math.copysign(abs(s) ** 0.45, s)
        x = -rc + 0.032 * i / steps
        wrap.append((x, -y, zc + z))
    tail_x = wrap[-1][0]
    tail = [(tail_x + 0.01, -a_ - 0.01, zc - 0.03), (tail_x + 0.02, -a_ - 0.012, zc - 0.10)]
    return loop, main + left + wrap + tail


def well_rope(name):
    p = Part(name, "no_collision", "hemp rope; pivot at the top of the wheel groove (0, 0, axle + groove + rope radius)")
    top = AXLE_Z + GROOVE_R + ROPE_R
    M = T(0, 0, -top)
    loop, path = rope_path()
    p.add(tube(path, ROPE_R, sides=6, u_tile=ROPE_TILE_U, v_tile=2 * math.pi * ROPE_R), RP, M, smooth=True)
    p.add(tube(loop, ROPE_R * 0.9, sides=6, u_tile=ROPE_TILE_U, v_tile=2 * math.pi * ROPE_R * 0.9), RP, M, smooth=True)
    grip = BUCKET_BOTTOM + BUCKET_GRIP
    knot = [(0, 0.0), (0.02, 0.004), (0.024, 0.02), (0.018, 0.036), (0, 0.04)]
    p.add(lathe([(r, grip + 0.045 + z) for r, z in knot], sides=8), RP, M @ T(BUCKET_X, 0, 0), uv="cyl", radius=0.02,
          smooth=True)
    p.hull_box(BUCKET_X - 0.02, BUCKET_X + 0.02, -0.02, 0.02, grip - top, AXLE_Z - top)
    return p


# --------------------------------------------------------------------------- cistern and crates

def board_tank(p, H, hw, n_boards, bands, n_lid, seed, foot=0.20, rail_rivets=6, band_rivets=8):
    """r3: the sheet's board tank (bottom row: the cistern) as one parametric construction, shared by the cistern and
    both crates (round-2 judge B: 'Crate / Crate_half is a different design from the reference box ... vertical
    planks, two full-width riveted iron bands, corner posts standing on stone feet, lid cleats'; the crate has no
    sheet of its own, so it now IS the sheet's box at crate size). Corner posts 3.5 cm PROUD of the boards from foot
    to lid on dressed granite feet; vertical boards of uneven width with gaps over a dark liner; rails top and bottom,
    nailed; two iron bands stepped round the posts, densely riveted (judge: 'the cistern bands also need denser
    rivets'); a thick plank lid over a rim that overhangs the walls, and two chunky cleats standing proud and
    overhanging front and back. Flat top at H = the lid planks (collision); the cleats rise 7 cm above it."""
    G.seed(seed)
    ph = 0.05
    pc = hw - ph                          # post centre: outer face at hw
    wo, wt = hw - 0.035, 0.028            # board outer face: posts 3.5 cm proud
    span = pc - ph                        # post inner faces
    zf, zl0 = 0.09, H - 0.085             # foot top, lid rim bottom
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.add(cbox(sx * (pc - 0.01), sy * (pc - 0.01), zf / 2, foot, foot, zf, 0.014), GR)
            board(p, sx * pc - ph, sx * pc + ph, sy * pc - ph, sy * pc + ph, zf, zl0, bevel=0.008, jitter=0.0, grain=2)
    for side in range(4):
        ws = widths(2 * span, n_boards, 0.75, 1.3)
        a = -span
        for i in range(n_boards):
            a0, a1 = a + 0.003 + 0.003 * G.rnd(), a + ws[i] - 0.003 - 0.003 * G.rnd()
            a += ws[i]
            z0, z1 = 0.13, H - 0.10 + 0.01 * G.rnd()
            if side == 0:
                board(p, a0, a1, -wo, -wo + wt, z0, z1, grain=2)
            elif side == 1:
                board(p, a0, a1, wo - wt, wo, z0, z1, grain=2)
            elif side == 2:
                board(p, -wo, -wo + wt, a0, a1, z0, z1, grain=2)
            else:
                board(p, wo - wt, wo, a0, a1, z0, z1, grain=2)
    ro = wo + 0.018
    qs = [-span + 0.08 + (2 * span - 0.16) * k / (rail_rivets - 1) for k in range(rail_rivets)]
    for (z0, z1) in ((0.12, 0.19), (H - 0.16, H - 0.09)):                           # rails, nailed to every board
        board(p, -span, span, -ro, -wo, z0, z1, bevel=0.004, jitter=0.0, grain=0)
        board(p, -span, span, wo, ro, z0, z1, bevel=0.004, jitter=0.0, grain=0)
        board(p, -ro, -wo, -span, span, z0, z1, bevel=0.004, jitter=0.0, grain=1)
        board(p, wo, ro, -span, span, z0, z1, bevel=0.004, jitter=0.0, grain=1)
        zm = (z0 + z1) / 2
        for q in qs:
            nail(p, q, -ro, zm, "-y")
            nail(p, q, ro, zm, "+y")
            nail(p, -ro, q, zm, "-x")
            nail(p, ro, q, zm, "+x")
    p.add(box(-span - 0.02, span + 0.02, -span - 0.02, span + 0.02, 0.14, 0.16), TB)   # floor (closes the tank)
    p.add(box(-wo + 0.031, wo - 0.031, -wo + 0.031, wo - 0.031, 0.15, H - 0.11), MO)  # dark liner behind the gaps
    t = 0.006
    bq = [-span + 0.06 + (2 * span - 0.12) * k / (band_rivets - 1) for k in range(band_rivets)]
    for (z0, z1) in bands:                                                           # iron bands, stepped round the posts
        zm = (z0 + z1) / 2
        for s_ in (-1, 1):
            f = s_ * wo
            ya, yb = sorted((f, f + s_ * t))
            p.add(box(-span, span, ya, yb, z0, z1), IR)                              # on the boards (front / back)
            p.add(box(ya, yb, -span, span, z0, z1), IR)                              # on the boards (sides)
            for q in bq:
                rivet(p, q, f + s_ * t, zm, "+y" if s_ > 0 else "-y", r=0.010)
                rivet(p, f + s_ * t, q, zm, "+x" if s_ > 0 else "-x", r=0.010)
            for sx in (-1, 1):                                                       # round each post corner
                yo = s_ * hw
                ya, yb = sorted((yo, yo + s_ * t))
                xa, xb = sorted((sx * span, sx * (hw + t)))
                p.add(box(xa, xb, ya, yb, z0, z1), IR)                               # post front / back face
                p.add(box(ya, yb, xa, xb, z0, z1), IR)                               # post side face
                ya, yb = sorted((s_ * wo, s_ * hw))
                xa, xb = sorted((sx * span, sx * (span + t)))
                p.add(box(xa, xb, ya, yb, z0, z1), IR)                               # step onto the board line
                p.add(box(ya, yb, xa, xb, z0, z1), IR)
                rivet(p, sx * pc, s_ * (hw + t), zm, "+y" if s_ > 0 else "-y")
                rivet(p, s_ * (hw + t), sx * pc, zm, "+x" if s_ > 0 else "-x")
    lo = hw + 0.02                                                                   # lid overhang: 5.5 cm past the boards
    for s_ in (-1, 1):                                                               # lid rim (fascia frame)
        ya, yb = sorted((s_ * lo, s_ * (lo - 0.035)))
        board(p, -lo, lo, ya, yb, zl0, H - 0.044, bevel=0.006, jitter=0.0, grain=0)
        board(p, ya, yb, -lo + 0.035, lo - 0.035, zl0, H - 0.044, bevel=0.006, jitter=0.0, grain=1)
    p.add(box(-lo + 0.03, lo - 0.03, -lo + 0.03, lo - 0.03, zl0 + 0.01, H - 0.044), TB)   # lid underlay
    ws = widths(2 * lo, n_lid, 0.8, 1.25)
    y = -lo
    for i in range(n_lid):                                                           # lid planks, top = H (collision)
        board(p, -lo - 0.004 * G.rnd(), lo + 0.004 * G.rnd(), y + 0.003, y + ws[i] - 0.003, H - 0.045,
              H - 0.003 * G.rnd(), bevel=0.007, jitter=0.0, grain=0)
        y += ws[i]
    cx = round(0.733 * hw, 3)
    for x in (-cx, cx):                                                              # chunky cleats, proud + overhanging
        board(p, x - 0.0375, x + 0.0375, -lo - 0.035, lo + 0.035, H - 0.002, H + 0.07, bevel=0.009, jitter=0.0, grain=1)
        for yy in (-0.75 * hw, 0.0, 0.75 * hw):
            nail(p, x, yy, H + 0.07, "+z", s=0.009, h=0.004)
    p.hull_box(-hw, hw, -hw, hw, 0.0, H)
    return {"posts_proud_m": 0.035, "boards_per_side": n_boards, "bands_z": [list(b) for b in bands],
            "rivets_per_band_face": band_rivets + 2, "lid_planks": n_lid, "cleat_x": cx, "stone_feet_m": foot}


def cistern():
    """The sheet's board water tank (1.2 x 1.2 x 1.25 m, climb prop, flat walkable lid). r3: built by board_tank (the
    same construction as f1/r2), with denser rivets on the bands."""
    p = Part("SM_DKP_Stone_Cistern", "climb_prop", "wooden water cistern 1.2 x 1.2 x 1.25 m, flat walkable lid")
    p.tank = board_tank(p, 1.25, 0.60, 6, ((0.29, 0.355), (0.93, 0.995)), 7, 8501)
    return p


def crate(name, H, note):
    """r3: the crate in the sheet's box design (the cistern's construction at 1.0 x 1.0 m; no own sheet exists):
    vertical boards, corner posts on stone feet, two riveted iron bands, lid with overhanging cleats. Flat top at H."""
    p = Part(name, "climb_prop", note)
    bands = ((0.29, 0.355), (0.93, 0.995)) if H > 1.0 else ((0.225, 0.28), (0.385, 0.44))
    p.tank = board_tank(p, H, 0.50, 5, bands, 6, 8601 + int(H * 100), foot=0.18, rail_rivets=5, band_rivets=6)
    return p


# --------------------------------------------------------------------------- layout (grey-box frame)

WELL_C = (41.0, 22.0)
ROPE_TOP = AXLE_Z + GROOVE_R + ROPE_R
ROUTES_NOTE = ("f1 (measurer): the cistern back edges sit 1.0 m short of the lower-roof eave line (Y 21.5) and the "
               "pavilion crate 1.05 m short of the pavilion roof edge (X 38.4). NOT moved: these positions are the "
               "grey-box owner's own SM_DGB_Cistern (X 13.05-14.25 / 29.75-30.95, Y 19.3-20.5) and SM_DGB_Crate "
               "(X 36.35-37.35, Y 2.5-3.5) boxes, and the grey-box adds flat landing pads at the eaves "
               "(SM_DGB_Landing_EavePad Y 20.75-21.5 at +3.0; SM_DGB_Landing_PavilionPad X 37.65-38.4 at +3.25) because "
               "GASP cannot mantle onto a 25 deg eave. Its climb check (WorkFiles/dojo/build/climb_check_greybox.json, "
               "GASP's steps replayed on the UCX hulls) passes route 4 (cistern 125 cm, then pad 174.8 cm, depth 85.6) "
               "and route 7 (crate 125 cm, then pavilion pad 199.8 cm, depth 85.9). Gaps actually crossed: 0.25 m "
               "(cistern back edge 20.5 -> pad 20.75) and 0.30 m (crate 37.35 -> pad 37.65). Moving the pavilion crate "
               "to X 37.9 would put it under the pad and block the mantle. For the grey-box owner to confirm in Unreal "
               "(no Unreal in this run).")
LAYOUT = [
    # piece, loc (grey-box metres), rot_z, source
    ("SM_DKP_Stone_LanternTall", (19.0, 19.75, 0.0), 0,  # r3 f1: Y 20.5 -> 19.75 (judges, ref 2)
     "spec 4.3: two stone lanterns in front of the hall (X 19 and 25); grey-box SM_DGB_StoneLantern"),
    ("SM_DKP_Stone_LanternTall", (25.0, 19.75, 0.0), 0, "spec 4.3 (as above)"),
    ("SM_DKP_Stone_Well", (WELL_C[0], WELL_C[1], 0.0), 0, "spec 4.3: a well in the east yard (41, 22); grey-box SM_DGB_Well"),
    ("SM_DKP_Stone_WellFrame", (WELL_C[0], WELL_C[1], 0.0), 0, "same origin as the well"),
    ("SM_DKP_Stone_WellCover", (WELL_C[0], WELL_C[1], WELL_H), 0, "on the rim; its crossbeam butts against both frame posts"),
    ("SM_DKP_Stone_WellPulley", (WELL_C[0], WELL_C[1], AXLE_Z), 0, "axle 0.16 m under the tie beam (yoke head plate on its underside)"),
    ("SM_DKP_Stone_WellBucket", (WELL_C[0] + BUCKET_X, WELL_C[1], BUCKET_BOTTOM + BUCKET_GRIP), 0, "hanging from the rope"),
    ("SM_DKP_Stone_WellRope", (WELL_C[0], WELL_C[1], ROPE_TOP), 0, "top of the wheel groove"),
    ("SM_DKP_Stone_Cistern", (13.65, 19.9, 0.0), 0, "spec 5.1 route 4: cistern at the west front corner of the hall; = grey-box SM_DGB_Cistern (see routes_note)"),
    ("SM_DKP_Stone_Cistern", (30.35, 19.9, 0.0), 0, "spec 5.1 route 4: east front corner (see routes_note)"),
    ("SM_DKP_Stone_Crate", (3.0, 5.8, 0.0), 0, "spec 5.1 route 7: crate at the training shed; = grey-box SM_DGB_Crate"),
    ("SM_DKP_Stone_Crate", (36.85, 3.0, 0.0), 0, "spec 5.1 route 7: crate at the drum pavilion; = grey-box Crate_Pavilion (see routes_note)"),
    # r3 (user decision 2026-09-28: 'drop the invented lamps'): the short lanterns are NOT placed. The references
    # show no lanterns inside the gate (the round-2 final judge flagged them as invented); the short lantern
    # stays an imported, unplaced spare (see UNPLACED)
]
UNPLACED = {
    "SM_DKP_Stone_LanternShort": "SPARE (user decision 2026-09-28: drop the invented lamps; no short lanterns inside the gate): imported, not placed. The r2 positions (20.6, 3.3) / (23.4, 3.3) are withdrawn",
    "SM_DKP_Stone_WellFrameGable": "SPARE (user decision 2026-10-02: imported, not placed; for the BR village): swap for SM_DKP_Stone_WellFrame at the well origin (same pulley, bucket, rope and cover placements)",
    "SM_DKP_Stone_CrateHalf": "dressing / stacking: on the ground (top +0.625) or two stacked = +1.25 (the route-7 height)",
}
ASSEMBLY = {   # relative placements for the review renders (well space)
    "well": [("SM_DKP_Stone_Well", (0, 0, 0)), ("SM_DKP_Stone_WellFrame", (0, 0, 0)),
             ("SM_DKP_Stone_WellCover", (0, 0, WELL_H)), ("SM_DKP_Stone_WellPulley", (0, 0, AXLE_Z)),
             ("SM_DKP_Stone_WellBucket", (BUCKET_X, 0, BUCKET_BOTTOM + BUCKET_GRIP)),
             ("SM_DKP_Stone_WellRope", (0, 0, ROPE_TOP))],
    "well_gable": [("SM_DKP_Stone_Well", (0, 0, 0)), ("SM_DKP_Stone_WellFrameGable", (0, 0, 0)),
                   ("SM_DKP_Stone_WellCover", (0, 0, WELL_H)), ("SM_DKP_Stone_WellPulley", (0, 0, AXLE_Z)),
                   ("SM_DKP_Stone_WellBucket", (BUCKET_X, 0, BUCKET_BOTTOM + BUCKET_GRIP)),
                   ("SM_DKP_Stone_WellRope", (0, 0, ROPE_TOP))],
}
COLLISION_CLASSES = {
    "thin_upright": "Pawn block, Camera ignore, Visibility ignore, GASP: low items vault (spec 5.3 thin uprights)",
    "climb_prop": "Pawn block, Camera ignore, Visibility block, GASP block; flat top >= 1.0 m deep (spec 5.3, R3)",
    "low_cover": "block all (low cover <= 1.25 m, R8)",
    "prop_small": "Pawn ignore (hanging bucket), Camera ignore, Visibility ignore",
    "no_collision": "NoCollision in Unreal (rope; the UCX exists only because every SM_ must carry one)",
}
TRI_BUDGET = 5000          # ASSET_GUIDELINES: prop 1-5k
NANITE_OVER = 2000         # user decision 2026-10-02: Nanite for props over about 2k tris; the 5k budget is waived for them


def budget_for(tris):
    return None if tris > NANITE_OVER else TRI_BUDGET


# --------------------------------------------------------------------------- the library pass (r2)

GROUND_Z = {"SM_DKP_Stone_WellCover": -10.0, "SM_DKP_Stone_WellPulley": -10.0, "SM_DKP_Stone_WellBucket": -10.0,
            "SM_DKP_Stone_WellRope": -10.0}        # pieces that never touch the ground: no ground dirt


def mesh_islands(me, faces):
    """Edge-connected face islands among `faces` (polygon indices)."""
    fset = set(faces)
    by_edge = {}
    for f in faces:
        for ek in me.polygons[f].edge_keys:
            by_edge.setdefault(ek, []).append(f)
    seen, out = set(), []
    for f0 in faces:
        if f0 in seen:
            continue
        stack, isl = [f0], []
        seen.add(f0)
        while stack:
            f = stack.pop()
            isl.append(f)
            for ek in me.polygons[f].edge_keys:
                for g in by_edge[ek]:
                    if g in fset and g not in seen:
                        seen.add(g)
                        stack.append(g)
        out.append(isl)
    return out


def apply_library(o):
    """UV0 by the library's own helpers for every library slot (timber: grain_uv with the end-grain slot; flat
    granite and iron: box_uv, upright and unmirrored; triplanar granite: box_uv for the exported UV0, Blender and
    Unreal sample it by position), then the library 'Wear' corner colours (bake_wear). Rope, glass panes and moss keep
    the Part's explicit UVs (library rope / unit-pane conventions)."""
    me = o.data
    names = [m.name for m in me.materials]
    for side, end in END_OF.items():
        if side in names and end not in names:
            me.materials.append(bpy.data.materials[end])
    names = [m.name for m in me.materials]
    stats = {}

    def faces_of(mn):
        i = names.index(mn)
        return [pl.index for pl in me.polygons if pl.material_index == i]

    for side, end in END_OF.items():
        if side in names and faces_of(side):
            # split the members: truly round ones (lathes: >= 10 distinct normals square to the long axis) wrap V round
            # the axis; bevelled boards (only 8 such normals; their 45-degree end bevels fooled grain_uv's 'auto')
            # take the planar side mapping
            rnd_f, box_f = [], []
            for isl in mesh_islands(me, faces_of(side)):
                pts = [o.matrix_world @ me.vertices[v].co for f in isl for v in me.polygons[f].vertices]
                _c, ax, _s = djm._pca(pts)
                dist = []
                for f in isl:
                    nn = me.polygons[f].normal
                    if abs(nn.dot(ax)) < 0.3 and all(nn.dot(m_) < 0.985 for m_ in dist):
                        dist.append(nn.copy())
                (rnd_f if len(dist) >= 10 else box_f).extend(isl)
            st = {}
            for fl, mode in ((rnd_f, True), (box_f, False)):
                if fl:
                    r_ = djm.grain_uv(o, bpy.data.materials[side]["dj_set"], end_set=bpy.data.materials[end]["dj_set"],
                                      faces=fl, end_material_index=names.index(end), uv_map="UV0", round_mode=mode)
                    for kk, vv in r_.items():
                        st[kk] = st.get(kk, 0) + vv
            stats[side] = st
    for side in END_OF:
        if side in names and faces_of(side):
            stats[side + "_bands"] = timber_bands.calm_bands(o, side, bpy.data.materials[side]["dj_set"])
    for mn in (GR, GRT, IR):
        if mn in names and faces_of(mn):
            djm.box_uv(o, bpy.data.materials[mn]["dj_set"], faces=faces_of(mn), uv_map="UV0")
    # drop an end-grain slot nobody uses (keeps the FBX slot list honest)
    for end in END_OF.values():
        if end in names and not faces_of(end):
            idx = names.index(end)
            if idx == len(names) - 1:
                me.materials.pop(index=idx)
                names.pop()
    # timber assemblies: grime from occlusion within 6 cm (the library default 15 cm blackened whole members of the
    # tightly stacked well roofs, rafters under boards read R 0.98); stone keeps the default
    ao = 0.15 if any(n_ in (GRT, GR) for n_ in names) else 0.06
    stats["wear"] = djm.bake_wear(o, ground_z=GROUND_Z.get(o.name), ao_dist=ao)
    return stats


def vary_block_tone(o, amount=0.30, seed=8111):
    """Per-block tone variation for the well ring: each loose granite block gets its own grime offset in the Wear
    colour's R channel (both Blender and Unreal darken base colour by 0.4 x R), so neighbouring blocks read as
    different stones under the continuous triplanar granite."""
    import random
    rng = random.Random(seed)
    me = o.data
    gi = [m.name for m in me.materials].index(GRT)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    lay = bm.loops.layers.color.get("Wear") or bm.loops.layers.float_color.get("Wear")
    faces = [f for f in bm.faces if f.material_index == gi]
    seen = set()
    n = 0
    for f0 in faces:
        if f0.index in seen:
            continue
        stack, isl = [f0], []
        seen.add(f0.index)
        while stack:
            f = stack.pop()
            isl.append(f)
            for e in f.edges:
                for g in e.link_faces:
                    if g.index not in seen and g.material_index == gi:
                        seen.add(g.index)
                        stack.append(g)
        off = rng.uniform(0.0, amount)
        for f in isl:
            for lp in f.loops:
                c = lp[lay]
                lp[lay] = (min(1.0, c[0] + off), c[1], c[2], c[3])
        n += 1
    bm.to_mesh(me)
    bm.free()
    return n


# --------------------------------------------------------------------------- measure

def texel_stats(o):
    """Per material on the mesh: area-weighted texel density (px/cm, from the material's own BC size, like qa_check),
    the share of its area under half the 5.12 target (2.56 px/cm, the measurer's stretch test), and faces whose UV area
    is zero (f1: the r0 bucket bail had 120)."""
    me = o.data
    uv = me.uv_layers[0].data
    per = {}
    for pl in me.polygons:
        mat = me.materials[pl.material_index]
        img = None
        if mat.use_nodes:
            for nd in mat.node_tree.nodes:
                if nd.type == "TEX_IMAGE" and nd.image and nd.image.name.endswith("_BC.png"):
                    img = nd.image
        if img is None:
            continue
        W, H_ = img.size
        pts = [uv[li].uv for li in pl.loop_indices]
        ua = 0.0
        for i in range(len(pts)):
            a_, b_ = pts[i], pts[(i + 1) % len(pts)]
            ua += a_.x * b_.y - b_.x * a_.y
        ua = abs(ua) * 0.5 * W * H_
        ar = pl.area
        rec = per.setdefault(mat.name, {"uv_px2": 0.0, "area_m2": 0.0, "low_area": 0.0, "zero_uv_faces": 0, "faces": 0})
        rec["uv_px2"] += ua
        rec["area_m2"] += ar
        rec["faces"] += 1
        if ar > 1e-8:
            d = math.sqrt(ua / ar) / 100.0
            if ua < 1e-6:
                rec["zero_uv_faces"] += 1
            if d < 2.56:
                rec["low_area"] += ar
    out = {}
    for m, r in per.items():
        out[m] = {"px_per_cm": round(math.sqrt(r["uv_px2"] / r["area_m2"]) / 100.0, 3) if r["area_m2"] else 0.0,
                  "area_below_2.56_pct": round(100 * r["low_area"] / r["area_m2"], 2) if r["area_m2"] else 0.0,
                  "zero_uv_faces": r["zero_uv_faces"], "faces": r["faces"]}
    return out


def measure(objs, parts):
    out = {}
    for name, o in objs.items():
        vs = [v.co for v in o.data.vertices]
        lo = [min(v[i] for v in vs) for i in range(3)]
        hi = [max(v[i] for v in vs) for i in range(3)]
        tris = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
        hulls = []
        for ch in o.children:
            hv = [v.co for v in ch.data.vertices]
            hl = [round(min(v[i] for v in hv), 4) for i in range(3)]
            hh = [round(max(v[i] for v in hv), 4) for i in range(3)]
            hulls.append({"name": ch.name, "min": hl, "max": hh, "verts": len(hv)})
        hmin = [min(h["min"][i] for h in hulls) for i in range(3)]
        hmax = [max(h["max"][i] for h in hulls) for i in range(3)]
        rec = {"bbox_min": [round(x, 4) for x in lo], "bbox_max": [round(x, 4) for x in hi],
               "size_xyz_m": [round(hi[i] - lo[i], 4) for i in range(3)], "tris": tris,
               "tri_budget": budget_for(tris), "nanite": tris > NANITE_OVER,
               "within_budget": budget_for(tris) is None or tris <= TRI_BUDGET,
               "materials": [m.name for m in o.data.materials], "collision_class": parts[name].klass,
               "ucx_count": len(hulls), "ucx_size_xyz_m": [round(hmax[i] - hmin[i], 4) for i in range(3)],
               "ucx": hulls, "texel": texel_stats(o)}
        if parts[name].klass == "climb_prop":
            top = max(h["max"][2] for h in hulls)
            tops = [h for h in hulls if abs(h["max"][2] - top) < 1e-3]
            rec["climb_top_z"] = round(top, 4)
            rec["climb_top_depth_min_m"] = round(min(min(h["max"][0] - h["min"][0], h["max"][1] - h["min"][1])
                                                      for h in tops), 4)
            rec["R3_flat_top_ge_1m"] = rec["climb_top_depth_min_m"] >= 1.0 - 1e-6
            rec["visual_above_collision_top_m"] = round(hi[2] - top, 4)
        out[name] = rec
    out["_texture_nominal_px_per_cm"] = {k: (djm.set_info(bpy.data.materials[k]["dj_set"])["px_per_cm"]
                                             if v[0] == "LIB" and "dj_set" in bpy.data.materials[k] else
                                             5.12 if v[0] else None) for k, v in MATERIALS.items()
                                         if k in bpy.data.materials}
    return out


# --------------------------------------------------------------------------- export (LOD0-2, kit 1 / taiko pattern)

WAIVE = {"uv0_tile_range", "uv_no_overlap"}


def export_with_lods(name, o, sc):
    """LOD0-2 on temporary copies (pipeline decimate_lods 0.5 / 0.25 + make_lod_group; the UCX becomes
    UCX_<base>_LOD0_NN), QA on the LODs, export the LodGroup through Scripts/pipeline (screen sizes 1.0 / 0.5 / 0.25 go in
    the sidecar). The blend keeps the plain LOD0 mesh."""
    tmp = bpy.data.collections.new("TmpLOD")
    sc.collection.children.link(tmp)
    c0 = o.copy()
    c0.data = o.data.copy()
    c0.name = f"{name}_LOD0"
    tmp.objects.link(c0)
    for h in o.children:
        hc = h.copy()
        hc.data = h.data.copy()
        hc.name = h.name.replace(f"UCX_{name}_", f"UCX_{name}_LOD0_")
        tmp.objects.link(hc)
        hc.parent = c0
    lods = decimate_lods(c0, (0.5, 0.25))
    for lo_ in lods:
        # the collapse can fold a tiny closed part (a nail head) into loose wire edges, and it moves UV1 islands:
        # drop wire edges / loose vertices and re-pack the lightmap channel on each LOD (f1)
        bm = bmesh.new()
        bm.from_mesh(lo_.data)
        wire = [e for e in bm.edges if not e.link_faces]
        if wire:
            bmesh.ops.delete(bm, geom=wire, context="EDGES")
        loose = [v for v in bm.verts if not v.link_edges]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(lo_.data)
        bm.free()
        lo_.data.uv_layers.active_index = 1
        with bpy.context.temp_override(active_object=lo_, object=lo_, selected_objects=[lo_],
                                       selected_editable_objects=[lo_]):
            bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                     PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
        lo_.data.uv_layers.active_index = 0
    grp = make_lod_group(name, [c0] + lods)
    lq = qa_check([c0] + lods, budget_tris=budget_for(len(c0.data.polygons)), require_uv1=True, require_ucx=False)
    lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in WAIVE]
    r = export_fbx(str(EXPORT_DIR / f"{name}.fbx"), [grp], kind="static", sidecar=True)
    tris = [lq["triangles"].get(x.name) for x in [c0] + lods]
    rep = {"lods": 3, "lod_tris": tris, "strictly_descending": all(a > b for a, b in zip(tris, tris[1:])),
           "lod_qa_hard_fails": [(c["name"], c["object"], str(c["detail"])[:160]) for c in lod_hard],
           "ucx_names": sorted(ch.name for ch in c0.children),
           "objects": r["objects"], "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"],
           "sidecar": r.get("sidecar")}
    for ob in list(tmp.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(tmp)
    return rep


# --------------------------------------------------------------------------- main

def main():
    assert_owner("DojoCourtyardStone", "claude")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    build_material(GRT)                  # the triplanar granite first (it is renamed from the library name)
    for name in MATERIALS:
        if name != GRT:
            build_material(name)
    G.seed(777)
    parts = [lantern("SM_DKP_Stone_LanternTall", LANTERN_TALL), lantern("SM_DKP_Stone_LanternShort", LANTERN_SHORT),
             well(), well_frame(), well_frame_gable(), well_cover(), well_pulley(), well_bucket(),
             well_rope("SM_DKP_Stone_WellRope"),
             cistern(),
             crate("SM_DKP_Stone_Crate", 1.25, "wooden crate 1.0 x 1.0 x 1.25 m, flat walkable lid (climb prop)"),
             crate("SM_DKP_Stone_CrateHalf", 0.625, "half-height crate 1.0 x 1.0 x 0.625 m; two stack to +1.25")]
    pmap = {p.name: p for p in parts}
    objs = {}
    for p in parts:
        coll = bpy.data.collections.new(p.name.replace("SM_DKP_Stone_", "Stone_"))
        sc.collection.children.link(coll)
        objs[p.name] = p.build(coll)
        lib = apply_library(objs[p.name])
        if p.name == "SM_DKP_Stone_Well":
            lib["blocks_toned"] = vary_block_tone(objs[p.name], amount=0.14)   # r3: lighter stone (judge B)
        print("built", p.name, sum(len(pl.vertices) - 2 for pl in objs[p.name].data.polygons), "tris",
              "moss pads", getattr(p, "moss_count", 0), {k: v for k, v in lib.items() if k != "wear"}, lib["wear"])

    WORK.mkdir(parents=True, exist_ok=True)
    meas = measure(objs, pmap)
    layout = {
        "units": "metres, grey-box frame (spec section 1: origin = inside SW corner, X east, Y north, Z up; "
                 "UE: x*100, -y*100, z*100, yaw = -rot_z)",
        "front": "every prop's front faces -Y (south, toward the fight floor) at rot_z 0",
        "pieces": sorted(objs),
        "instances": [{"piece": pc, "loc": list(loc), "rot_z": rz, "collision_class": pmap[pc].klass, "source": src}
                      for pc, loc, rz, src in LAYOUT],
        "routes_note": ROUTES_NOTE,
        "unplaced": UNPLACED,
        "assembly_offsets_well_space": ASSEMBLY,
        "pivots": {n: ("axle centre" if "Pulley" in n else "bail grip" if "Bucket" in n else
                       "top of the wheel groove" if "Rope" in n else "base centre on the ground (cover: its underside)")
                   for n in objs},
        "collision_classes": COLLISION_CLASSES,
        "materials": {k: {"texture": v[0], "tile_m": v[1], "params": v[2], "note": v[3]} for k, v in MATERIALS.items()},
    }
    (WORK / "layout_stone.json").write_text(json.dumps(layout, indent=1), encoding="utf-8")

    qa = {}
    for name, o in objs.items():
        tris0 = sum(len(pl.vertices) - 2 for pl in o.data.polygons)
        r = qa_check([o], budget_tris=budget_for(tris0), require_uv1=True)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in WAIVE]
        qa[name] = {"hard_fails": hard, "waived": sorted({c["name"] for c in fails if c["name"] in WAIVE}),
                    "tris": r["triangles"].get(name), "budget_tris": budget_for(tris0), "nanite": tris0 > NANITE_OVER}
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA: {len(objs)} pieces, hard fails {hard_total}")
    for k, v in qa.items():
        print("  ", k, v["tris"], "tris")
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], str(c["detail"])[:200])

    if "--no-export" not in ARGS and hard_total == 0:
        results = {}
        for name, o in objs.items():
            results[name] = export_with_lods(name, o, sc)
            qa[name]["lods"] = {kk: results[name][kk] for kk in ("lod_tris", "strictly_descending", "lod_qa_hard_fails")}
            meas[name]["lod_tris"] = results[name]["lod_tris"]
            print("  export", name, results[name]["lod_tris"], results[name]["lod_qa_hard_fails"])
        (WORK / "export_report.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
        print(f"exported {len(results)} FBX (LOD0-2) to {EXPORT_DIR}")
    (WORK / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
    (WORK / "measure.json").write_text(json.dumps(meas, indent=1), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND)


main()
