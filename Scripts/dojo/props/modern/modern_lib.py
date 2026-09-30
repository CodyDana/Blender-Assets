"""Geometry + material library for the dojo MODERN PROPS kit (kit 10). Imported by build_modern_props.py and
render_modern.py; runs inside Blender (bpy, bmesh).

Asset: one render mesh built in a single BMesh from primitives (bevelled boxes, swept tubes, lathes, convex hulls,
plates with a round hole), each primitive shifted by a unique sub-10-micron offset so no two primitives share a
vertex position (the pipeline's no_coincident_vertices gate), material slots by name, UV0 in metres divided by the
material's tile size (tiling sets) or explicit 0-1 (unique maps), UV1 by lightmap pack, and UCX_ convex hulls.

UV0 conventions (the textures follow them): box projection puts world Z on V for every side face, so paint streaks,
drips and grime run downward; a part can put its own long axis on V instead (timber grain along a crossarm). Tubes
and lathes map the circumference on U and the length along the path on V (pole grain runs along the pole).
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

TEX_DIR = None   # set by the build script (Exports/DojoKit/Props/modern/Textures)
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2] / "materials"))
import dojo_materials as djm  # noqa: E402


# --------------------------------------------------------------------------- colour helpers

def srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hexcol(h):
    return tuple(srgb_to_lin(int(h[i:i + 2], 16) / 255.0) for i in (1, 3, 5)) + (1.0,)


# --------------------------------------------------------------------------- materials
# name: (texture set or None, tile in metres (None = unique 0-1 UV), params)
MATERIALS = {
    # paint sets are HEIGHT-ANCHORED (tile along U; V = 0..2 m above the prop's painted base, see Asset.vbase)
    "M_DKP_Modern_PaintTeal": ("PaintTeal", 2.0, {"family": "M_Env_PaintedMetal", "generic": False, "anchored": True}),
    "M_DKP_Modern_PaintWhite": ("PaintWhite", 2.0, {"family": "M_Env_PaintedMetal", "generic": False, "anchored": True}),
    "M_DKP_Modern_PaintGrey": ("PaintGrey", 2.0, {"family": "M_Env_PaintedMetal", "generic": True, "anchored": True}),
    "M_DKP_Modern_Galvanised": ("Galvanised", 2.0, {"family": "M_Env_PaintedMetal (galvanised mode)", "generic": True}),
    "M_DKP_Modern_IronDark": ("IronDark", 2.0, {"family": "M_Steel_Master instance or M_Env_PaintedMetal", "generic": True}),
    "M_DKP_Modern_PoleWood": ("PoleWood", 2.0, {"family": "M_Env_Wood", "generic": True}),
    "M_DKP_Modern_Concrete": ("Concrete", 2.0, {"family": "M_Env_Concrete", "generic": True}),
    "M_DKP_Modern_CoilFins": ("CoilFins", 0.25, {"family": "M_Env_PaintedMetal", "generic": False}),
    # blank backlit display panel: BC doubles as the emissive colour (Unreal: M_Env_Emissive, BC x scalar)
    "M_DKP_Modern_VendPanel": ("VendPanel", None, {"emit_tex": 0.7, "family": "M_Env_Emissive", "generic": False}),
    # seeded amber lantern glass (about 2400 K), one pane 0-1: BC doubles as the emissive colour with a falloff from
    # the bulb hotspot; semi-clear (transmission) so the bulb reads through it in Blender. Unreal: M_Env_Emissive
    # (opaque, the hotspot is in the map) or a translucent glass instance.
    "M_DKP_Modern_LampGlass": ("LampGlass", None, {"emit_tex": 2.2, "transmission": 0.45, "rough": 0.3,
                                                   "family": "M_Env_Emissive", "generic": True}),
    # the lamp bulb / mantle inside each lantern: small, bright, warm (the light source the glass shows)
    "M_DKP_Modern_BulbLit": (None, 1.0, {"color": "#FFE2B0", "emit": 14.0, "emit_color": "#FFB25E",
                                         "family": "M_Env_Emissive", "generic": True}),
    # condenser fan guard: alpha-masked wire grille (Unreal: masked material, two-sided)
    "M_DKP_Modern_FanGrille": ("FanGrille", None, {"alpha": True, "family": "M_Env_PaintedMetal (masked)",
                                                   "generic": False}),
    "M_DKP_Modern_Rust": (None, 1.0, {"color": "#5E3520", "rough": 0.92, "family": "flat", "generic": True}),
    "M_DKP_Modern_ButtonLit": (None, 1.0, {"color": "#D8D0BC", "emit": 0.5, "emit_color": "#FFD9A6",
                                           "family": "M_Env_Emissive", "generic": False}),
    "M_DKP_Modern_Porcelain": (None, 1.0, {"color": "#4A2A1C", "rough": 0.16, "coat": 0.6, "family": "flat", "generic": True}),
    "M_DKP_Modern_Rubber": (None, 1.0, {"color": "#201F1D", "rough": 0.85, "family": "flat", "generic": True}),
    "M_DKP_Modern_PlasticDark": (None, 1.0, {"color": "#232628", "rough": 0.22, "family": "flat", "generic": False}),
    "M_DKP_Modern_PlasticCream": (None, 1.0, {"color": "#CBC4B0", "rough": 0.5, "family": "flat", "generic": True}),
    "M_DKP_Modern_Chrome": (None, 1.0, {"color": "#B4B5B2", "rough": 0.24, "metal": 1.0, "family": "flat", "generic": True}),
    "M_DKP_Modern_FanDark": (None, 1.0, {"color": "#303335", "rough": 0.55, "family": "flat", "generic": False}),
    "M_DKP_Modern_Cable": (None, 1.0, {"color": "#1B1B1A", "rough": 0.55, "family": "flat", "generic": True}),
    "M_DKP_Modern_PipeInsul": (None, 1.0, {"color": "#B9B4A6", "rough": 0.8, "family": "flat", "generic": False}),
    "M_DKP_Modern_Copper": (None, 1.0, {"color": "#9A6A45", "rough": 0.35, "metal": 1.0, "family": "flat", "generic": True}),
}


# r2: the shared dojo material library (Scripts/dojo/materials) replaces the kit's own iron, timber, lamp glass and
# vending display. "LIB" entries: UV0 comes from the library's helpers after the mesh is built (build_modern_props
# .apply_library): grain_uv for timber (with the end-grain slot), box_uv for iron; the glass panes and the vending
# display keep their explicit 0-1 UVs (the library's unit-pane convention).
MATERIALS.update({
    "M_DJ_Iron": ("LIB", 2.0, {"family": "library M_DJ_Lib_Opaque (MI_DJ_Iron)", "generic": True}),
    "M_DJ_TimberAged": ("LIB", 4.0, {"family": "library M_DJ_Lib_Opaque (MI_DJ_TimberAged)", "generic": True}),
    "M_DJ_TimberAgedEnd": ("LIB", 2.0, {"family": "library M_DJ_Lib_Opaque (MI_DJ_TimberAgedEnd)", "generic": True}),
    "M_DJ_TimberDark": ("LIB", 4.0, {"family": "library M_DJ_Lib_Opaque (MI_DJ_TimberDark)", "generic": True}),
    "M_DJ_TimberDarkEnd": ("LIB", 2.0, {"family": "library M_DJ_Lib_Opaque (MI_DJ_TimberDarkEnd)", "generic": True}),
    "M_DJ_GlassAmber": ("LIB", None, {"family": "library M_DJ_Lib_Emissive (MI_DJ_GlassAmber)", "generic": True}),
    "M_DJ_VendingPanel": ("LIB", None, {"family": "library M_DJ_Lib_Emissive (MI_DJ_VendingPanel)", "generic": False}),
})
END_OF = {"M_DJ_TimberAged": "M_DJ_TimberAgedEnd", "M_DJ_TimberDark": "M_DJ_TimberDarkEnd"}


def tile_of(mat):
    return MATERIALS[mat][1]


def build_material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    tex, _tile, p = MATERIALS[name]
    if tex == "LIB":
        return djm.make_material(name, uv_map="UV0")
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def img(suffix, noncolor):
        node = nt.nodes.new("ShaderNodeTexImage")
        image = bpy.data.images.load(str(TEX_DIR / f"T_DKP_Modern_{tex}_{suffix}.png"), check_existing=True)
        if noncolor:
            image.colorspace_settings.name = "Non-Color"
        node.image = image
        return node

    if tex:
        bc = img("BC", False)
        nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
        orm, nrm = img("ORM", True), img("N", True)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(orm.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs[1], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs[2], bsdf.inputs["Metallic"])
        # the maps are DirectX (UE); flip green back to OpenGL for Blender's review renders
        sep_n = nt.nodes.new("ShaderNodeSeparateColor")
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
        if "emit_tex" in p:
            nt.links.new(bc.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = p["emit_tex"]
        if "transmission" in p:
            bsdf.inputs["Transmission Weight"].default_value = p["transmission"]
            nt.links.remove(next(lk for lk in nt.links if lk.to_socket == bsdf.inputs["Roughness"]))
            bsdf.inputs["Roughness"].default_value = p.get("rough", 0.3)
            bsdf.inputs["IOR"].default_value = 1.5
        if p.get("alpha"):
            nt.links.new(bc.outputs["Alpha"], bsdf.inputs["Alpha"])
            bc.image.alpha_mode = "STRAIGHT"
    else:
        bsdf.inputs["Base Color"].default_value = hexcol(p["color"])
        bsdf.inputs["Roughness"].default_value = p.get("rough", 0.8 if "emit" in p else 0.5)
        bsdf.inputs["Metallic"].default_value = p.get("metal", 0.0)
        if "coat" in p:
            bsdf.inputs["Coat Weight"].default_value = p["coat"]
            bsdf.inputs["Coat Roughness"].default_value = 0.05
        if "emit" in p:
            bsdf.inputs["Emission Color"].default_value = hexcol(p.get("emit_color", p["color"]))
            bsdf.inputs["Emission Strength"].default_value = p["emit"]
    return mat


# --------------------------------------------------------------------------- path helpers

def V(*a):
    return Vector(a[0]) if len(a) == 1 else Vector(a)


def bend_path(points, radius, seg=6):
    """Round every interior corner of a polyline with an arc of `radius` (clamped to half the shorter leg)."""
    pts = [V(p) for p in points]
    if len(pts) < 3:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, p, b = pts[i - 1], pts[i], pts[i + 1]
        d1, d2 = (a - p), (b - p)
        l1, l2 = d1.length, d2.length
        d1.normalize()
        d2.normalize()
        cosang = max(-1.0, min(1.0, d1.dot(d2)))
        theta = math.acos(cosang)
        if theta > math.pi - 1e-3 or theta < 1e-3:
            out.append(p)
            continue
        t = radius / math.tan(theta / 2)
        t = min(t, 0.49 * l1, 0.49 * l2)
        r = t * math.tan(theta / 2)
        t1, t2 = p + d1 * t, p + d2 * t
        bis = (d1 + d2).normalized()
        c = p + bis * (r / math.sin(theta / 2))
        v1, v2 = (t1 - c), (t2 - c)
        ang = v1.angle(v2)
        axis = v1.cross(v2).normalized()
        for k in range(seg + 1):
            q = Matrix.Rotation(ang * k / seg, 3, axis) @ v1
            out.append(c + q)
    out.append(pts[-1])
    return out


def arc(center, radius, a0, a1, n, u_axis=(1, 0, 0), v_axis=(0, 0, 1)):
    c, u, v = V(center), V(u_axis), V(v_axis)
    return [c + u * (radius * math.cos(a0 + (a1 - a0) * k / n)) + v * (radius * math.sin(a0 + (a1 - a0) * k / n))
            for k in range(n + 1)]


# --------------------------------------------------------------------------- the asset builder

class Asset:
    """One prop: a render mesh + UCX hulls (+ optional sockets)."""

    def __init__(self, name, cls, note):
        self.name, self.cls, self.note = name, cls, note
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UV0")
        self.mode = self.bm.faces.layers.int.new("uvmode")   # 0 box (V = z), 1 explicit, 2/3 box with V = x / y
        self.mats = []
        self.k = 0
        self.ucx = []        # lists of points (convex hulls)
        self.sockets = []    # (name, location, rotation_euler)
        self.info = {}
        self.vbase = 0.0     # z of the painted base: height-anchored paint sets put v = 0 here

    # ---- internals
    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _jit(self):
        self.k += 1
        k = self.k
        return Vector((2.3e-6 * (k % 7 + 1), 2.9e-6 * ((k // 7) % 7 + 1), 3.1e-6 * ((k // 49) % 7 + 1)))

    def _add(self, verts, faces, mat, uvs=None, smooth=False, mode=0, xf=None, sharp_edges=()):
        """verts: coordinates; faces: index tuples; uvs: per-face list of (u, v) in METRES (explicit) or None."""
        j = self._jit()
        m = xf if xf is not None else Matrix.Identity(4)
        bv = [self.bm.verts.new(m @ V(c) + j) for c in verts]
        mi = self._mi(mat)
        made = []
        for fi, f in enumerate(faces):
            face = self.bm.faces.new([bv[i] for i in f])
            face.material_index = mi
            face.smooth = smooth if not isinstance(smooth, (list, tuple)) else smooth[fi]
            if uvs is not None and uvs[fi] is not None:
                face[self.mode] = 1
                for loop, uv in zip(face.loops, uvs[fi]):
                    loop[self.uv].uv = uv
            else:
                face[self.mode] = mode
            made.append(face)
        for a, b in sharp_edges:
            e = self.bm.edges.get((bv[a], bv[b]))
            if e:
                e.smooth = False
        return made

    # ---- primitives
    def box(self, x0, x1, y0, y1, z0, z1, mat, bevel=0.0, xf=None, vaxis="z", seg=1):
        tmp = bmesh.new()
        vs = [tmp.verts.new(c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
        for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)):
            tmp.faces.new([vs[i] for i in q])
        if bevel > 0:
            lim = 0.45 * min(x1 - x0, y1 - y0, z1 - z0)
            bmesh.ops.bevel(tmp, geom=list(tmp.verts) + list(tmp.edges), offset=min(bevel, lim),
                            offset_type="OFFSET", segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)
        self._from_tmp(tmp, mat, xf, {"z": 0, "x": 2, "y": 3}[vaxis])
        return self

    def _from_tmp(self, tmp, mat, xf, mode, smooth=False):
        verts = [v.co.copy() for v in tmp.verts]
        idx = {v: i for i, v in enumerate(tmp.verts)}
        faces = [tuple(idx[v] for v in f.verts) for f in tmp.faces]
        tmp.free()
        return self._add(verts, faces, mat, None, smooth, mode, xf)

    def hull(self, points, mat, xf=None, vaxis="z"):
        tmp = bmesh.new()
        for p in points:
            tmp.verts.new(V(p))
        res = bmesh.ops.convex_hull(tmp, input=list(tmp.verts))
        bmesh.ops.delete(tmp, geom=list({*res["geom_interior"], *res["geom_unused"]}), context="VERTS")
        bmesh.ops.dissolve_limit(tmp, angle_limit=0.001, verts=list(tmp.verts), edges=list(tmp.edges))
        big = [f for f in tmp.faces if len(f.verts) > 4]
        if big:
            bmesh.ops.triangulate(tmp, faces=big)
        bmesh.ops.recalc_face_normals(tmp, faces=list(tmp.faces))
        self._from_tmp(tmp, mat, xf, {"z": 0, "x": 2, "y": 3}[vaxis])
        return self

    def bar(self, p0, p1, w, t, mat, up=(0, 0, 1)):
        """A flat bar / strap of width w and thickness t from p0 to p1 (a box along an arbitrary line)."""
        p0, p1 = V(p0), V(p1)
        d = (p1 - p0).normalized()
        u = V(up)
        side = d.cross(u)
        if side.length < 1e-6:
            side = d.cross(V(1, 0, 0))
        side.normalize()
        nrm = side.cross(d).normalized()
        pts = []
        for p in (p0, p1):
            for a in (-1, 1):
                for b in (-1, 1):
                    pts.append(p + side * (a * w / 2) + nrm * (b * t / 2))
        return self.hull(pts, mat)

    def tube(self, path, r, mat, sides=8, caps=True, smooth=True, closed=False, radii=None, phase=0.0):
        pts = [V(p) for p in path]
        if closed and (pts[0] - pts[-1]).length < 1e-9:
            pts = pts[:-1]
        n = len(pts)
        rr = radii if radii is not None else [r] * n
        tans = []
        for i in range(n):
            if closed:
                t = (pts[(i + 1) % n] - pts[i - 1])
            elif i == 0:
                t = pts[1] - pts[0]
            elif i == n - 1:
                t = pts[-1] - pts[-2]
            else:
                t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
            tans.append(t.normalized())
        # rotation-minimising frames (double reflection)
        t0 = tans[0]
        ref = V(0, 0, 1) if abs(t0.z) < 0.9 else V(1, 0, 0)
        nrm = (ref - t0 * ref.dot(t0)).normalized()
        frames = [nrm]
        for i in range(1, n):
            v1 = pts[i] - pts[i - 1]
            c1 = v1.dot(v1)
            if c1 < 1e-18:
                frames.append(frames[-1])
                continue
            rl = frames[-1] - (2 / c1) * v1.dot(frames[-1]) * v1
            tl = tans[i - 1] - (2 / c1) * v1.dot(tans[i - 1]) * v1
            v2 = tans[i] - tl
            c2 = v2.dot(v2)
            ni = rl - (2 / c2) * v2.dot(rl) * v2 if c2 > 1e-18 else rl
            frames.append(ni.normalized())
        verts, faces, uvs, sm = [], [], [], []
        lens = [0.0]
        for i in range(1, n):
            lens.append(lens[-1] + (pts[i] - pts[i - 1]).length)
        rings = []
        for i in range(n):
            t, nn = tans[i], frames[i]
            b = t.cross(nn).normalized()
            # scale the ring at a corner so the wall keeps its thickness
            ring = []
            for s in range(sides):
                a = phase + 2 * math.pi * s / sides
                verts.append(pts[i] + (nn * math.cos(a) + b * math.sin(a)) * rr[i])
                ring.append(len(verts) - 1)
            rings.append(ring)
        segs = n if closed else n - 1
        total = lens[-1] + ((pts[0] - pts[-1]).length if closed else 0)
        for i in range(segs):
            i2 = (i + 1) % n
            v0 = lens[i]
            v1_ = lens[i2] if i2 > i else total
            for s in range(sides):
                s2 = (s + 1) % sides
                faces.append((rings[i][s], rings[i][s2], rings[i2][s2], rings[i2][s]))
                circ = 2 * math.pi * max(rr[i], rr[i2])
                u0, u1 = circ * s / sides, circ * (s + 1) / sides
                uvs.append([(u0, v0), (u1, v0), (u1, v1_), (u0, v1_)])
                sm.append(smooth)
        sharp = []
        if caps and not closed:
            for end, ring, flip in ((0, rings[0], True), (n - 1, rings[-1], False)):
                verts.append(pts[end].copy())
                c = len(verts) - 1
                t, nn = tans[end], frames[end]
                b = t.cross(nn)
                for s in range(sides):
                    s2 = (s + 1) % sides
                    f = (c, ring[s2], ring[s]) if flip else (c, ring[s], ring[s2])
                    faces.append(f)
                    uvs.append([((verts[k] - pts[end]).dot(nn), (verts[k] - pts[end]).dot(b)) for k in f])
                    sm.append(False)
                    sharp.append((ring[s], ring[s2]))
        self._add(verts, faces, mat, uvs, sm, sharp_edges=sharp)
        return self

    def lathe(self, profile, mat, sides=16, center=(0, 0, 0), xf=None, smooth=True, phase=0.0, sharp_rings=()):
        """Surface of revolution about local Z from an (r, z) profile running bottom-centre -> outside up -> top."""
        verts, rings = [], []
        for (r, z) in profile:
            if r <= 0:
                verts.append((0.0, 0.0, z))
                rings.append([len(verts) - 1] * sides)
            else:
                ring = []
                for s in range(sides):
                    a = phase + 2 * math.pi * s / sides
                    verts.append((r * math.cos(a), r * math.sin(a), z))
                    ring.append(len(verts) - 1)
                rings.append(ring)
        rref = max(p[0] for p in profile)
        lens = [0.0]
        for k in range(1, len(profile)):
            lens.append(lens[-1] + math.dist(profile[k - 1], profile[k]))
        faces, uvs = [], []
        for k in range(len(profile) - 1):
            a, b = rings[k], rings[k + 1]
            for s in range(sides):
                s2 = (s + 1) % sides
                u0, u1 = rref * 2 * math.pi * s / sides, rref * 2 * math.pi * (s + 1) / sides
                q = [(a[s], (u0, lens[k])), (a[s2], (u1, lens[k])), (b[s2], (u1, lens[k + 1])), (b[s], (u0, lens[k + 1]))]
                if profile[k][0] <= 0:
                    q = [q[0], q[2], q[3]]
                elif profile[k + 1][0] <= 0:
                    q = [q[0], q[1], q[2]]
                faces.append(tuple(i for i, _ in q))
                uvs.append([uv for _, uv in q])
        m = Matrix.Translation(V(center))
        if xf is not None:
            m = xf @ m
        sharp = []
        for k in sharp_rings:
            ring = rings[k]
            sharp += [(ring[s], ring[(s + 1) % sides]) for s in range(sides)]
        self._add(verts, faces, mat, uvs, smooth, xf=m, sharp_edges=sharp)
        return self

    def plate_hole(self, s0, s1, t0, t1, cs, ct, r, mat, origin, s_axis, t_axis, n=48):
        """A flat rectangle [s0,s1] x [t0,t1] with a round hole (centre cs, ct; radius r) in a plane given by origin and
        two axes; the face normal is s_axis x t_axis. Quads between the circle and the rectangle, corner sectors split
        into triangles (no n-gons)."""
        o, su, tu = V(origin), V(s_axis), V(t_axis)
        P = lambda s, t: o + su * s + tu * t
        verts, faces, uvs = [], [], []
        circ, rect = [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            dx, dy = math.cos(a), math.sin(a)
            circ.append((cs + r * dx, ct + r * dy))
            ts = []
            if dx > 1e-9:
                ts.append((s1 - cs) / dx)
            if dx < -1e-9:
                ts.append((s0 - cs) / dx)
            if dy > 1e-9:
                ts.append((t1 - ct) / dy)
            if dy < -1e-9:
                ts.append((t0 - ct) / dy)
            tt = min(ts)
            rect.append((cs + tt * dx, ct + tt * dy))
        corners = [(s1, t1), (s0, t1), (s0, t0), (s1, t0)]
        cang = [math.atan2(c[1] - ct, c[0] - cs) % (2 * math.pi) for c in corners]

        def add(p):
            verts.append(P(*p))
            uvs_pt.append(p)
            return len(verts) - 1
        uvs_pt = []
        ci = [add(p) for p in circ]
        ri = [add(p) for p in rect]
        for i in range(n):
            j = (i + 1) % n
            a0 = 2 * math.pi * i / n
            a1 = 2 * math.pi * (i + 1) / n
            inside = [k for k in range(4) if a0 < cang[k] < a1 or (j == 0 and cang[k] > a0)]
            if inside:
                K = add(corners[inside[0]])
                for f in ((K, ri[j], ci[j]), (K, ci[j], ci[i]), (K, ci[i], ri[i])):
                    faces.append(f)
            else:
                faces.append((ci[i], ri[i], ri[j], ci[j]))
        self._add(verts, faces, mat, [[uvs_pt[k] for k in f] for f in faces], False)
        return self

    def plate_poly(self, s0, s1, t0, t1, inner, cs, ct, mat, origin, s_axis, t_axis):
        """A flat rectangle [s0,s1] x [t0,t1] with an opening given by `inner`, a polygon of (s, t) points that is
        star-shaped about (cs, ct) (e.g. an arch-topped window). Quads between the opening and rays to the
        rectangle, rectangle corners fanned in as triangles (no n-gons). The face normal is s_axis x t_axis."""
        o, su, tu = V(origin), V(s_axis), V(t_axis)
        P = lambda s, t: o + su * s + tu * t
        pts = sorted(inner, key=lambda p: math.atan2(p[1] - ct, p[0] - cs) % (2 * math.pi))
        n = len(pts)
        verts, uvs_pt, faces = [], [], []

        def add(p):
            verts.append(P(*p))
            uvs_pt.append(p)
            return len(verts) - 1
        ang = [math.atan2(p[1] - ct, p[0] - cs) % (2 * math.pi) for p in pts]
        rect = []
        for (ps, pt) in pts:
            dx, dy = ps - cs, pt - ct
            ln = math.hypot(dx, dy)
            dx, dy = dx / ln, dy / ln
            ts = []
            if dx > 1e-9:
                ts.append((s1 - cs) / dx)
            if dx < -1e-9:
                ts.append((s0 - cs) / dx)
            if dy > 1e-9:
                ts.append((t1 - ct) / dy)
            if dy < -1e-9:
                ts.append((t0 - ct) / dy)
            tt = min(ts)
            rect.append((cs + tt * dx, ct + tt * dy))
        corners = [(s1, t1), (s0, t1), (s0, t0), (s1, t0)]
        cang = [math.atan2(c[1] - ct, c[0] - cs) % (2 * math.pi) for c in corners]
        ci = [add(p) for p in pts]
        ri = [add(p) for p in rect]
        for i in range(n):
            j = (i + 1) % n
            a0, a1 = ang[i], ang[j] if j else ang[j] + 2 * math.pi
            inside = [k for k in range(4) if a0 < cang[k] < a1 or a0 < cang[k] + 2 * math.pi < a1]
            if inside:
                K = add(corners[inside[0]])
                faces += [(K, ri[j], ci[j]), (K, ci[j], ci[i]), (K, ci[i], ri[i])]
            else:
                faces.append((ci[i], ri[i], ri[j], ci[j]))
        self._add(verts, faces, mat, [[uvs_pt[k] for k in f] for f in faces], False)
        return self

    def quad(self, pts, mat, uv01=False, uvs=None):
        """One quad (winding sets the normal). uv01: explicit 0-1 mapping in point order (0,0),(1,0),(1,1),(0,1)."""
        if uv01:
            uvs = [[(0, 0), (1, 0), (1, 1), (0, 1)]]
        self._add(pts, [(0, 1, 2, 3)], mat, uvs, False)
        return self

    def col_box(self, x0, x1, y0, y1, z0, z1):
        self.ucx.append([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
        return self

    def col_hull(self, points):
        self.ucx.append([tuple(p) for p in points])
        return self

    def socket(self, name, loc, rot=(0, 0, 0)):
        self.sockets.append((name, tuple(loc), tuple(rot)))
        return self

    # ---- finalise
    def build(self, coll):
        bm = self.bm
        # closed islands must face outward: flip any island whose signed volume is negative
        self._orient_islands()
        bm.normal_update()
        for f in bm.faces:
            mode = f[self.mode]
            tile = tile_of(self.mats[f.material_index])
            if mode != 1:
                n = f.normal
                ax = max(range(3), key=lambda i: abs(n[i]))
                plane = [i for i in range(3) if i != ax]
                va = {0: 2, 2: 0, 3: 1}[mode]
                if va in plane:
                    ua = plane[0] if plane[1] == va else plane[1]
                else:
                    ua, va = plane[0], plane[1]
                sgn = 1.0
                if (ax == 1 and n[ax] > 0) or (ax == 0 and n[ax] < 0):
                    sgn = -1.0   # read left to right from outside the face
                voff = 0.0
                if MATERIALS[self.mats[f.material_index]][2].get("anchored"):
                    # side faces: v = height above the painted base; top / bottom faces: the clean mid band
                    voff = -self.vbase if va == 2 else 1.0
                for loop in f.loops:
                    co = loop.vert.co
                    loop[self.uv].uv = (sgn * co[ua], co[va] + voff)
            if tile:
                for loop in f.loops:
                    u, v = loop[self.uv].uv
                    loop[self.uv].uv = (u / tile, v / tile)
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in self.mats:
            mesh.materials.append(build_material(m))
        obj = bpy.data.objects.new(self.name, mesh)
        coll.objects.link(obj)
        add_uv1(obj)
        for i, pts in enumerate(self.ucx):
            hb = bmesh.new()
            for p in pts:
                hb.verts.new(V(p))
            res = bmesh.ops.convex_hull(hb, input=list(hb.verts))
            bmesh.ops.delete(hb, geom=list({*res["geom_interior"], *res["geom_unused"]}), context="VERTS")
            bmesh.ops.recalc_face_normals(hb, faces=list(hb.faces))
            hm = bpy.data.meshes.new(f"UCX_{self.name}_{i:02d}")
            hb.to_mesh(hm)
            hb.free()
            h = bpy.data.objects.new(f"UCX_{self.name}_{i:02d}", hm)
            coll.objects.link(h)
            h.parent = obj
            h.hide_render = True
            h.display_type = "WIRE"
        for (sname, loc, rot) in self.sockets:
            e = bpy.data.objects.new(f"SOCKET_{self.name}_{sname}", None)
            e.empty_display_type = "ARROWS"
            e.empty_display_size = 0.1
            e.location = loc
            e.rotation_euler = rot
            coll.objects.link(e)
            e.parent = obj
        return obj

    def _orient_islands(self):
        bm = self.bm
        bm.faces.index_update()
        bm.faces.ensure_lookup_table()
        seen = set()
        for f0 in bm.faces:
            if f0.index in seen:
                continue
            stack, isl = [f0], []
            seen.add(f0.index)
            while stack:
                f = stack.pop()
                isl.append(f)
                for e in f.edges:
                    for g in e.link_faces:
                        if g.index not in seen:
                            seen.add(g.index)
                            stack.append(g)
            closed = all(len(e.link_faces) == 2 for f in isl for e in f.edges)
            if not closed:
                continue
            vol = 0.0
            for f in isl:
                vs = [v.co for v in f.verts]
                for k in range(1, len(vs) - 1):
                    vol += vs[0].dot(vs[k].cross(vs[k + 1])) / 6.0
            if vol < 0:
                bmesh.ops.reverse_faces(bm, faces=isl, flip_multires=False)


def add_uv1(obj):
    """UV1 lightmap channel (Fab rule): Blender's lightmap pack (non-overlapping, inside 0-1)."""
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=16, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0
