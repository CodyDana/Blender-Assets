"""Geometry helpers for kit 8 (courtyard stone + wooden climb props). Blender-side only (bmesh).

A Part is one asset: it collects closed primitives (bevelled hexahedra, square lofts, lathes, tubes, extruded
polygons), each with a material and a UV rule, and builds one mesh with UV0, UV1 (lightmap pack) and UCX_ convex hulls.

UV rules (UV0, metres / material tile):
  box   - per face, projected in the primitive's OWN frame (before its transform) on the face's dominant plane; U runs
          along the primitive's longest in-plane axis, so timber grain follows every board; a random offset per
          primitive keeps neighbouring boards from repeating.
  trim  - ground-contact trim (GraniteMoss): side faces get U = horizontal position, V = height above the asset's
          ground (z / 1.0 m); faces pointing up or down fall back to the `alt` material with box UV.
  cyl   - around an axis: U = angle x radius / tile, V = height / tile (swap=True puts the grain along the height).
  given - explicit per-face loop UVs (rope, glow panes).
  cylbox - (f1) cyl on the faces around the axis, box on the faces that look along it (wheel and bucket sides, the
          well blocks' tops): r0 put cyl UVs on flat discs, which collapsed them to zero area.
Per-face extras (f1): smooth may be a callable(local normal) -> bool; up_mat puts a material on faces whose world normal
points up (moss on ledges).
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

TILES = {}          # material name -> (tile_u_m, tile_v_m) or None (filled by the build script)
_RNG_STATE = [12345]


def rnd():
    """Deterministic LCG in [0, 1), so every build writes the same file."""
    _RNG_STATE[0] = (1103515245 * _RNG_STATE[0] + 12345) % (2 ** 31)
    return _RNG_STATE[0] / 2 ** 31


def seed(s):
    _RNG_STATE[0] = s


# --------------------------------------------------------------------------- primitives -> (verts, faces)

def _bm_out(bm):
    bm.verts.index_update()
    verts = [tuple(v.co) for v in bm.verts]
    faces = [tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free()
    return verts, faces


def hexa(c8, bevel=0.0, segs=1):
    """Closed hexahedron from 8 corners (0-3 bottom counter-clockwise seen from above, 4-7 the top above them), edges
    bevelled by `bevel` metres."""
    bm = bmesh.new()
    v = [bm.verts.new(c) for c in c8]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([v[i] for i in q])
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, offset_type="OFFSET", segments=segs, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    return _bm_out(bm)


def box(x0, x1, y0, y1, z0, z1, bevel=0.0, segs=1):
    return hexa([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                 (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], bevel, segs)


def cbox(cx, cy, cz, sx, sy, sz, bevel=0.0, segs=1):
    """Box by centre and full size."""
    return box(cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, cz - sz / 2, cz + sz / 2, bevel, segs)


def ring_loft(rings, cap_bottom=None, cap_top=None):
    """Loft closed rings (lists of equal length, counter-clockwise from above, running upward on the outside). A ring
    given as a single point is a pole. Returns (verts, faces)."""
    verts, idx = [], []
    for r in rings:
        if len(r) == 1:
            idx.append(len(verts))            # a pole: one vertex index
            verts.append(tuple(r[0]))
        else:
            base = len(verts)
            verts.extend(tuple(p) for p in r)
            idx.append(list(range(base, base + len(r))))
    n = max(len(r) for r in rings)
    faces = []
    for k in range(len(rings) - 1):
        a, b = idx[k], idx[k + 1]
        for i in range(n):
            j = (i + 1) % n
            if isinstance(a, int):
                faces.append((a, b[j], b[i]))
            elif isinstance(b, int):
                faces.append((a[i], a[j], b))
            else:
                faces.append((a[i], a[j], b[j], b[i]))
    return verts, faces


def square_ring(hx, hy, z, segs=1, upturn=0.0, ridge=(0.0, 0.0), upturn_pow=3.0, flare=0.0, cluster=False):
    """Rectangle ring, counter-clockwise from (-hx, -hy), `segs` points per side. upturn lifts the corners (curved
    eaves: dz = upturn * |t|^p with t = -1..1 along each side); flare pushes the corner points outward in plan by the
    same falloff; cluster=True spaces the points by a cosine so they gather at the corners (where the curl is);
    ridge = (height, width) raises a hip ridge on the diagonals (points within `width` of a corner)."""
    pts = []
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    for s in range(4):
        (x0, y0), (x1, y1) = corners[s], corners[(s + 1) % 4]
        L = math.hypot(x1 - x0, y1 - y0)
        for k in range(segs):
            f = k / segs
            if cluster:
                f = 0.5 - 0.5 * math.cos(math.pi * f)
            t = 2 * f - 1                    # -1 at the start corner .. +1 at the next
            x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            w = abs(t) ** upturn_pow
            dz = upturn * w
            if flare:
                sc = 1 + flare * w / max(hx, hy)
                x, y = x * sc, y * sc
            d = (1 - abs(t)) * L / 2         # distance along the side to the nearest corner
            if ridge[0] and ridge[1] > 0:
                dz += ridge[0] * max(0.0, 1 - d / ridge[1]) ** 2
            pts.append((x, y, z + dz))
    return pts


def sq_loft(profile, segs=1):
    """Square (rectangular) solid of revolution: profile = [(hx, hy, z, upturn, ridge_h, ridge_w)...] from the bottom
    centre (hx = 0 is a pole) up the outside to the top centre."""
    rings = []
    for p in profile:
        hx, hy, z = p[0], p[1], p[2]
        up = p[3] if len(p) > 3 else 0.0
        rid = (p[4], p[5]) if len(p) > 5 else (0.0, 0.0)
        if hx == 0:
            rings.append([(0.0, 0.0, z)])
        else:
            rings.append(square_ring(hx, hy, z, segs, up, rid))
    return ring_loft(rings)


def sq_tier(h, z0, z1, ch=0.0, hy=None, ch_bottom=0.0):
    """A square slab / block with optional chamfer on the top (ch) and bottom (ch_bottom) edges."""
    hy = h if hy is None else hy
    prof = [(0, 0, z0)]
    if ch_bottom:
        prof += [(h - ch_bottom, hy - ch_bottom, z0), (h, hy, z0 + ch_bottom)]
    else:
        prof += [(h, hy, z0)]
    if ch:
        prof += [(h, hy, z1 - ch), (h - ch, hy - ch, z1)]
    else:
        prof += [(h, hy, z1)]
    prof += [(0, 0, z1)]
    return sq_loft(prof)


def rough_tier(h, z0, z1, ch=0.012, ch_bottom=0.004, segs=4, jit=0.006, hy=None):
    """A square block like sq_tier, with `segs` points per side and the chamfer rings jittered inward / downward by up
    to `jit` metres (deterministic): chipped, hand-dressed arrises instead of machine-straight edges (f1)."""
    hy = h if hy is None else hy
    rings = [[(0.0, 0.0, z0)]]

    def ring(hh, hhy, z, j_in, j_z):
        pts = square_ring(hh, hhy, z, segs)
        out = []
        for (x, y, zz) in pts:
            a = rnd() * j_in
            sx = 1 - a / max(abs(x), 1e-6) if abs(x) > 1e-6 else 1
            sy = 1 - a / max(abs(y), 1e-6) if abs(y) > 1e-6 else 1
            out.append((x * (sx if abs(x) >= hh - 1e-6 else 1), y * (sy if abs(y) >= hhy - 1e-6 else 1),
                        zz + (rnd() - 0.5) * 2 * j_z))
        return out

    if ch_bottom:
        rings.append(ring(h - ch_bottom, hy - ch_bottom, z0, 0.0, 0.0))
        rings.append(ring(h, hy, z0 + ch_bottom, jit * 0.3, jit * 0.2))
    else:
        rings.append(ring(h, hy, z0, 0.0, 0.0))
    rings.append(ring(h, hy, z1 - ch, jit * 0.35, jit * 0.35))
    rings.append(ring(h - ch, hy - ch, z1, jit, jit * 0.3))
    rings.append([(0.0, 0.0, z1)])
    return ring_loft(rings)


def lathe(profile, sides=16, axis="z"):
    """Surface of revolution about Z (then optionally turned onto X or Y) from (r, z) points bottom pole -> top pole."""
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([(0.0, 0.0, z)])
        else:
            rings.append([(r * math.cos(2 * math.pi * i / sides), r * math.sin(2 * math.pi * i / sides), z)
                          for i in range(sides)])
    verts, faces = ring_loft(rings)
    if axis == "y":      # z -> -y ... rotate +90 about X: (x, y, z) -> (x, -z, y)
        verts = [(x, -z, y) for (x, y, z) in verts]
    elif axis == "x":    # rotate about Y: (x, y, z) -> (z, y, -x)
        verts = [(z, y, -x) for (x, y, z) in verts]
    return verts, faces


def prism(poly, z0, z1):
    """Extrude a convex counter-clockwise polygon [(x, y)...] from z0 to z1; caps are fans from the centroid."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    verts = [(x, y, z0) for x, y in poly] + [(x, y, z1) for x, y in poly] + [(cx, cy, z0), (cx, cy, z1)]
    c0, c1 = 2 * n, 2 * n + 1
    faces = []
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
        faces.append((c0, j, i))
        faces.append((c1, n + i, n + j))
    return verts, faces


def tube(path, radius, sides=8, closed_ends=True, u_tile=0.25, v_tile=None):
    """A round tube along a polyline with parallel-transport frames. Returns (verts, faces, uvs): U = arc length /
    u_tile, V = 0..1 around (or circumference / v_tile around when v_tile is given: real texel density on the iron
    bail, f1). End caps get a small real planar patch instead of a collapsed point UV."""
    P = [Vector(p) for p in path]
    T = []
    for i in range(len(P)):
        a = P[max(i - 1, 0)]
        b = P[min(i + 1, len(P) - 1)]
        T.append((b - a).normalized())
    ref = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
    N = [T[0].cross(ref).normalized()]
    for i in range(1, len(P)):
        n = N[-1] - T[i] * N[-1].dot(T[i])
        N.append(n.normalized() if n.length > 1e-9 else N[-1])
    verts, faces, uvs = [], [], []
    s = [0.0]
    for i in range(1, len(P)):
        s.append(s[-1] + (P[i] - P[i - 1]).length)
    for i, p in enumerate(P):
        b = T[i].cross(N[i])
        for k in range(sides):
            a = 2 * math.pi * k / sides
            verts.append(tuple(p + radius * (math.cos(a) * N[i] + math.sin(a) * b)))
    for i in range(len(P) - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            a0, a1 = i * sides + k, i * sides + k2
            b0, b1 = (i + 1) * sides + k, (i + 1) * sides + k2
            faces.append((a0, a1, b1, b0))
            vs_ = (2 * math.pi * radius / v_tile) if v_tile else 1.0
            uvs.append([(s[i] / u_tile, k / sides * vs_), (s[i] / u_tile, (k + 1) / sides * vs_),
                        (s[i + 1] / u_tile, (k + 1) / sides * vs_), (s[i + 1] / u_tile, k / sides * vs_)])
    if closed_ends:
        for end, sign in ((0, -1), (len(P) - 1, 1)):
            c = len(verts)
            verts.append(tuple(P[end]))
            for k in range(sides):
                k2 = (k + 1) % sides
                a0, a1 = end * sides + k, end * sides + k2
                faces.append((c, a1, a0) if sign < 0 else (c, a0, a1))
                cu = radius / (v_tile or u_tile)
                ang = [2 * math.pi * kk / sides for kk in (k, k2)]
                pa = [(0.5 + cu * math.cos(q), 0.5 + cu * math.sin(q)) for q in ang]
                uvs.append([(0.5, 0.5), pa[1], pa[0]] if sign < 0 else [(0.5, 0.5), pa[0], pa[1]])
    # check winding once: the first side quad's normal must point away from the axis
    v0, v1, v2 = (Vector(verts[i]) for i in faces[0][:3])
    nrm = (v1 - v0).cross(v2 - v0)
    if nrm.dot(v0 - P[0]) < 0:
        faces = [tuple(reversed(f)) for f in faces]
        uvs = [list(reversed(u)) for u in uvs]
    return verts, faces, uvs


def arc(center, r, a0, a1, n, plane="xz"):
    """Points on a circular arc (angles in degrees) in the given plane through center."""
    out = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        c, s = math.cos(a) * r, math.sin(a) * r
        if plane == "xz":
            out.append((center[0] + c, center[1], center[2] + s))
        elif plane == "yz":
            out.append((center[0], center[1] + c, center[2] + s))
        else:
            out.append((center[0] + c, center[1] + s, center[2]))
    return out


# --------------------------------------------------------------------------- the Part (one asset)

def plane_uv(pts, n, tile):
    """Project points on the face's dominant plane, metres / tile (a real, non-degenerate UV patch)."""
    ax = max(range(3), key=lambda i: abs(n[i]))
    a, b = [i for i in range(3) if i != ax]
    return [(0.5 + q[a] / tile, 0.5 + q[b] / tile) for q in pts]


def _newell(pts):
    n = Vector((0, 0, 0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


class Part:
    def __init__(self, name, klass, note=""):
        self.name, self.klass, self.note = name, klass, note
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UV0")
        self.mats = []
        self.hulls = []          # lists of points (asset space) -> convex UCX
        self.count = 0

    def _mi(self, m):
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def add(self, geom, mat, M=None, uv="box", alt=None, smooth=False, swap=False, axis="z", radius=None,
            tile=None, face_uvs=None, grain=None, up_mat=None, up_thr=0.55, trim_radius=None):
        """Add one primitive. geom = (verts, faces) or (verts, faces, uvs). M = Matrix placing it in asset space."""
        verts, faces = geom[0], geom[1]
        if len(geom) > 2 and face_uvs is None:
            face_uvs = geom[2]
            uv = "given"
        self.count += 1
        # tiny unique growth about the primitive's centre: abutting primitives never share exact coincident vertices
        # (an absolute outward growth plus a sub-0.1 mm shift, both unique per primitive)
        k = 1 + self.count % 97
        cen = Vector([sum(v[i] for v in verts) / len(verts) for i in range(3)])
        shift = Vector((0.7e-6 * k, 0.5e-6 * ((k * 7) % 97 + 1), 0.3e-6 * ((k * 13) % 97 + 1)))
        loc = []
        for v in verts:
            d = Vector(v) - cen
            loc.append(Vector(v) + (d.normalized() * 2e-6 * k if d.length > 1e-9 else Vector()) + shift)
        M = M or Matrix.Identity(4)
        world = [M @ v for v in loc]
        lo = Vector([min(v[i] for v in loc) for i in range(3)])
        hi = Vector([max(v[i] for v in loc) for i in range(3)])
        ext = hi - lo
        bvs = [self.bm.verts.new(w) for w in world]
        ou, ov = rnd() * 0.5, rnd() * 0.5
        for fi, f in enumerate(faces):
            face_mat = mat
            fl = [loc[i] for i in f]
            fw = [world[i] for i in f]
            nl = _newell(fl)
            nw = _newell(fw)
            coords = None
            mode = uv
            if mode == "cylbox":
                ai = "xyz".index(axis)
                pl_ = [i for i in range(3) if i != ai]
                cen_f = sum(fl, Vector()) / len(fl)
                rad = Vector([cen_f[i] if i in pl_ else 0.0 for i in range(3)])
                radial = rad.length > 1e-6 and abs(nl.dot(rad.normalized())) > 0.5 * nl.length
                # faces looking along the axis, or sideways (the radial end cuts of a well block): box; else cyl
                mode = "cyl" if (abs(nl[ai]) <= 0.8 * nl.length and radial) else "box"
            if mode == "trim":
                if abs(nw.z) > 0.6 * nw.length:
                    face_mat, mode = alt, "box"
                else:
                    tu = self._tile(mat)
                    cen_w = sum(fw, Vector()) / len(fw)
                    rad_w = Vector((cen_w.x, cen_w.y, 0.0))
                    is_radial = rad_w.length > 1e-6 and abs(nw.dot(rad_w.normalized())) > 0.5 * nw.length
                    if trim_radius and is_radial:                 # round pieces: U = arc length round the Z axis
                        angs = [math.atan2(w.y, w.x) for w in fw]
                        if max(angs) - min(angs) > math.pi:
                            angs = [a + 2 * math.pi if a < 0 else a for a in angs]
                        coords = [(a * trim_radius / tu[0] + ou, w.z / tu[1]) for a, w in zip(angs, fw)]
                    else:
                        hor = 1 if abs(nw.x) > abs(nw.y) else 0      # normal along X -> U = y, else U = x
                        coords = [(w[hor] / tu[0] + ou, w.z / tu[1]) for w in fw]
            if mode == "box":
                tu = self._tile(face_mat)
                ax = max(range(3), key=lambda i: abs(nl[i]))
                plane = [i for i in range(3) if i != ax]
                if grain is not None and grain in plane:
                    ua = grain
                else:
                    ua = max(plane, key=lambda i: ext[i])
                va = [i for i in plane if i != ua][0]
                coords = [((p[ua] - lo[ua]) / tu[0] + ou, (p[va] - lo[va]) / tu[1] + ov) for p in fl]
            elif mode == "cyl":
                tu = self._tile(face_mat)
                ai = "xyz".index(axis)
                pl = [i for i in range(3) if i != ai]
                R = radius or 0.1
                angs = [math.atan2(p[pl[1]], p[pl[0]]) for p in fl]
                if max(angs) - min(angs) > math.pi:
                    angs = [a + 2 * math.pi if a < 0 else a for a in angs]
                coords = []
                for p, a in zip(fl, angs):
                    uu, vv = a * R / tu[0], p[ai] / tu[1]
                    coords.append((vv + ou, uu + ov) if swap else (uu + ou, vv + ov))
            elif mode == "given":
                coords = face_uvs[fi]
            if up_mat and nw.length > 0 and nw.z > up_thr * nw.length:
                face_mat = up_mat
            bf = self.bm.faces.new([bvs[i] for i in f])
            bf.material_index = self._mi(face_mat)
            bf.smooth = bool(smooth(nl.normalized() if nl.length else nl)) if callable(smooth) else bool(smooth)
            for loop, c in zip(bf.loops, coords):
                loop[self.uv].uv = c
        return self

    def _tile(self, m):
        t = TILES.get(m)
        if t is None:
            return (1.0, 1.0)
        return t if isinstance(t, tuple) else (t, t)

    def hull(self, pts, M=None):
        M = M or Matrix.Identity(4)
        self.hulls.append([M @ Vector(p) for p in pts])
        return self

    def hull_box(self, x0, x1, y0, y1, z0, z1, M=None):
        return self.hull([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)], M)

    def hull_cyl(self, cx, cy, r, z0, z1, sides=12):
        pts = []
        for i in range(sides):
            a = 2 * math.pi * i / sides
            for z in (z0, z1):
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a), z))
        return self.hull(pts)

    def build(self, coll):
        bm = self.bm
        bm.normal_update()
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        for m in self.mats:
            me.materials.append(bpy.data.materials[m])
        obj = bpy.data.objects.new(self.name, me)
        coll.objects.link(obj)
        add_uv1(obj)
        for i, pts in enumerate(self.hulls):
            hb = bmesh.new()
            for p in pts:
                hb.verts.new(p)
            res = bmesh.ops.convex_hull(hb, input=list(hb.verts))
            dead = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
            if dead:
                bmesh.ops.delete(hb, geom=list(dead), context="VERTS")
            bmesh.ops.triangulate(hb, faces=[f for f in hb.faces if len(f.verts) > 4])
            hm = bpy.data.meshes.new(f"UCX_{self.name}_{i:02d}")
            hb.to_mesh(hm)
            hb.free()
            h = bpy.data.objects.new(f"UCX_{self.name}_{i:02d}", hm)
            coll.objects.link(h)
            h.parent = obj
            h.hide_render = True
            h.display_type = "WIRE"
        return obj


def add_uv1(obj):
    """UV1 lightmap channel (Fab rule): Blender's lightmap pack, no overlaps, inside 0-1 (as the armory kit)."""
    me = obj.data
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.2)
    me.uv_layers.active_index = 0


def T(x=0.0, y=0.0, z=0.0):
    return Matrix.Translation((x, y, z))


def R(deg, axis):
    return Matrix.Rotation(math.radians(deg), 4, axis)
