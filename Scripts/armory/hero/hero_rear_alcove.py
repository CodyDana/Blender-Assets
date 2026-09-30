"""Hero piece: SM_AK_RearAlcove, the two backlit alcoves flanking the painting on the rear platform.

Modelled from the user's reference sheet WorkFiles/armory/reference/rear_alcove.png (front / side / top / 3/4) with the
ornamental lattice grille above the lit panel as back_wall.png and the look reference armory3_reference2.png show it
over the rear alcoves (the rear_alcove sheet alone has no grille; the plan's as-built rear platform has the "lattice
screen above"). Set the environment variable AK_RA_NO_GRILLE=1 before a preview to see the rear_alcove.png variant: one
tall uninterrupted lit panel from the cabinet top to the soffit (a user decision; the default keeps the grille).

Kit frame (unchanged from the scripted piece): X 0..1.8 (width), Y 0..0.6 with the back at y = 0 against the rear wall
and the open front at y = 0.6 (layout() places it at rot 180, so local +Y faces the room), Z 0..3.2 from the platform
top. lights() is unchanged: AlcoveSpot_* (local x 0.55 / 1.25, y 0.36, z 2.33) and RackLight_* (y 0.5, z 2.25) hang free
in front of the grille; their two downlight lenses sit in the soffit under the lintel (z 2.95).

Design read off the front view of rear_alcove.png:
  * two heavy dark-timber posts (27.4 cm crisp capitals flush with the lintel top with a thin incised X on the flat
    front, top and outer faces (final4: a narrow V-groove along each diagonal, no pyramid facets), over a brass collar; one clean 20.5 cm shaft face with only a thin bronze reveal line at its
    inner edge; the casing between the shaft and the opening is set 6.6 cm back so it reads as a shadowed reveal, not a
    second board (final3); a single 48 cm base block (no split groove) under a brass band, brass band and plinth at the
    foot), a timber lintel between the capitals over the lit opening, a thin dark-bronze inner reveal round the sides
    and head of the opening, a hidden LED strip along the soffit front and three soffit lenses
  * TIMBER GRAIN: T_AK_HTimber (hero_shared) runs its grain along U, so every timber face here maps U along the member
    (final3; the old kit timber ran along V and the posts showed cross grain)
  * the niche cheeks behind the posts rise flush with the lintel top. final4: the -X cheek (the side rear_alcove.png's
    side view shows) has an OPEN tall slot between the post and a rear column that looks into the lit interior: the
    nearest rack upright and its hook, a splayed light-timber soffit at its head, the cabinet end with a lit top edge
    at its foot (10 cm below the cabinet top); dark timber walls, so from the 3/4 it reads as a shadowed recess, not a
    glowing strip. The +X cheek is plain (no see-through). Their inner returns are light warm timber with clear
    vertical grain (M_AK_HAlcoveReturn, T_AK_HAlcoveReturn from tex_rear_alcove.py)
  * the backlit panel (M_AK_HAlcovePanel, one emissive picture T_AK_HAlcovePanel from tex_rear_alcove.py on a unique
    0-1 UV: golden-beige parchment with very faint soft marbling (final4), a hot yellow-gold LED halo inside every visible
    edge and a hot spot at the top centre) with LED glow lines (M_AK_HLEDEdge) round all four sides; above the slim
    grille rail, up to the soffit and across the full opening, the ornamental grille (final3): an interlocking kumiko
    fretwork after back_wall.png, a square grid of thin bars with a diamond ring in every cell, large and small in a
    checkerboard (the large ones reach into the neighbouring cells and interlock), so the openings are varied
    (diamonds of two sizes, small triangles and lozenges round the grid points). final4: heavier bars (~25 % open),
    near-black (M_AK_HGrilleMetal) over a bright saturated gold backlight picture with a hot spot at the top centre
    (M_AK_HGrilleGlow, T_AK_HAlcoveGrille), so it reads as back_wall.png's dark screen with small bright gold openings
  * the EMPTY upright rack for five standing swords: a two-step satin black lacquer base bar on a recessed plinth with a
    warm LED under-glow; five plain 10 x 10 x 14 cm lacquer foot blocks with a thin brass collar at the upright; square
    uprights 1.20 m over the bar, each with a plain dark lacquer sleeve carrying a slim upturned black hook sweeping
    out to the viewer's right and 35 deg back (final4: the upturn in 10-degree steps; final3: no brass on the hooks,
    no inlay on the blocks). No swords.
  * the black lacquer base cabinet, 72 cm (final3, ~23 % of the height as rear_alcove.png): plinth, carcass, stiles and
    rails round a recessed drawer field with a brass inlay line, slim brass top line on the top slab, the user's
    emblem medallion (20.6 cm bezel) centred on the front (M_AK_Emblem, unique 0-1 UV on the disc face)
ENABLED stays False: the user reviews the images before anything goes into the armory.
"""
import math
import os

import bmesh
from mathutils import Vector

ENABLED = True          # the user reviews images of every piece BEFORE anything goes into the armory
GRILLE = os.environ.get("AK_RA_NO_GRILLE", "0") != "1"   # preview-only switch (see the docstring); default: grille
MATERIALS = {
    # final3 (judge: pale cream / peach, a cream-white halo, veins barely visible; rear_alcove.png is a warmer golden
    # amber with faint marbled veins and a hot yellow-gold edge line): the picture is re-toned in tex_rear_alcove.py
    # (a golden beige body with a fine crackle of veins and a saturated amber-gold halo at a moderate emission, 2.2, so
    # AgX keeps the halo gold instead of blowing it to cream)
    # calibration pass 1 (room judge: the rear alcove backs near-white in the room; reference 2: warm amber-beige): 2.2 -> 0.70
    "M_AK_HAlcovePanel": ("HAlcovePanel", None, {"emit_image": True, "emit": 0.90, "unlit": True}),   # calibration pass 2: 0.70 -> 0.90 (C1 rear alcove 0.26, reference 0.37)
    # final4 (judge: the grille read as a uniform orange-tan mesh with bronze-brown bars; back_wall.png's grille is a
    # dark, near-black screen with small bright gold openings): near-black bars that no longer mirror the room, over a
    # brighter saturated gold backlight picture (T_AK_HAlcoveGrille, hot spot at the top centre)
    # calibration pass 1 (room judge: reference 2's lattice over each rear alcove is a DARK screen with small gold
    # openings; ours read as a bright gold panel, C1 L0.56 against 0.18): 1.35 -> 0.10
    # calibration pass 2 (room judge: the lattice over each rear alcove went missing, a flat dark panel): 0.10 -> 0.16, so
    # the small gold openings read in the dark screen
    "M_AK_HGrilleGlow": ("HAlcoveGrille", None, {"emit_image": True, "emit": 0.16, "unlit": True}),
    "M_AK_HGrilleMetal": (None, 1.0, {"color": "#0A0705", "rough": 0.7, "metal": 0.0}),
    # final3 (judge: flat cream-tan with no grain; rear_alcove.png 3/4 shows light timber with visible grain): a light
    # warm timber picture (grain along U, 1 m tile) on the returns' inner faces
    "M_AK_HAlcoveReturn": ("HAlcoveReturn", 1.0, {}),
    "M_AK_HRackLacquer": (None, 1.0, {"color": "#090706", "rough": 0.34}),
    "M_AK_HHookLacquer": (None, 1.0, {"color": "#070605", "rough": 0.58}),
    # final3 (judge: the edge halo read cream-white, not a hot yellow-gold line): a more saturated amber-yellow strip
    "M_AK_HLEDEdge": (None, 1.0, {"color": "#FFD040", "emit": 3.0}),
    # rear dais (2026-09-28): the corner showcases' cream backlit panel (T_AK_HShowcasePanel, tex_rear_alcove.showcase),
    # at the alcove panel's emission
    # b4 (blind judge delta 4: over-bright white slots from the entrance): 0.90 -> 0.22
    # b7 (blind judge delta 5: from the entrance the b6 niches read as flat blank light boxes): 0.22 -> 0.12, so the
    # lit lining and the shelf read in front of it
    # r16 niches (C1 against reference 2: its niche back is a bright cream, near the rack alcove panel; the framed r16
    # niche read a dim ochre box behind the tall case's glass; reference 2's is hot at the head, graded down): 0.12 ->
    # 0.08 and no longer unlit, so the niche spot under the head grades it (base colour on; at 0.16 AgX bleached it to
    # a pale cream, C1 golden mean 0.83 against the reference's 0.55 amber)
    # r17 fix round (blind judge 7/10 on r17/final, delta d: "the reference alcove is ... lit over the full height of
    # its back panel; r17 lights only the upper half"): 0.08 -> 0.12, with a second (fill) spot on the lower half
    "M_AK_HShowcasePanel": ("HShowcasePanel", None, {"emit_image": True, "emit": 0.12}),   # r17 fix round: 0.08
    # b7 (judge delta 5): the niche's lining (side returns, floor, shelf top): a warm pale satin that the soffit spot
    # grades from bright at the head to shadow at the counter, so the recess depth reads
    "M_AK_HShowcaseLining": (None, 1.0, {"color": "#A57D50", "rough": 0.5}),   # b9: #8C6A44 -> #A57D50
    # r16 fix round (blind judge 7/10, point 3 / delta 4: the corner niche's black casing on the dark wall barely showed
    # from C1, so it read as a lit slot more than a framed alcove): the casing in a warm mid-brown timber (the kit's
    # T_AK_Timber lifted 2.6x, ~(88,73,62) against the block's ~(34,28,24)), a wider brass bead and a gold LED line
    # down the opening's front arrises and under its head (as the wall bays' lit edges)
    "M_AK_HNicheFrame": ("Timber", 2.0, {"tint": 2.6}),
}

T, LQ, BR, BZ = "M_AK_Timber", "M_AK_Lacquer", "M_AK_Brass", "M_AK_Bronze"
LIT, GG, EM, LED = "M_AK_HAlcovePanel", "M_AK_HGrilleGlow", "M_AK_Emblem", "M_AK_LED"
RL, HK, LE, LB, RT = "M_AK_HRackLacquer", "M_AK_HHookLacquer", "M_AK_HLEDEdge", "M_AK_HGrilleMetal", "M_AK_HAlcoveReturn"
GRAIN_U = (T, RT)        # grain-along-U timber pictures: U follows the member (final3)

W, D, H = 1.8, 0.6, 3.2
CX = W / 2
CT = 0.72                # cabinet top (final3: was 0.60)
_count = [0]
def _grow():
    """A tiny unique growth per part (as Piece.box does): parts that touch never share a vertex position."""
    _count[0] += 1
    return 0.00005 + (_count[0] % 199) * 1.5e-6


def _emit(P, bm, tile_of, grain=None):
    """bmesh -> Piece mesh part: n-gons triangulated, UV0 box-projected per face (the wood grain of the timber texture
    pictures in GRAIN_U (T_AK_HTimber, T_AK_HAlcoveReturn) run their grain along U, so U follows the part's long axis
    `grain` on those faces (final3); every other material keeps V along `grain` as before), one material per face from
    the face's material slot."""
    ng = [f for f in bm.faces if len(f.verts) > 4]
    if ng:
        bmesh.ops.triangulate(bm, faces=ng)
    bm.normal_update()
    bm.verts.index_update()
    verts = [tuple(v.co) for v in bm.verts]
    faces, uvs, mats = [], [], []
    for f in bm.faces:
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        plane = [i for i in range(3) if i != ax]
        va = grain if grain in plane else plane[-1]
        ua = [i for i in plane if i != va][0]
        m = tile_of[f.material_index]
        tile = m[1]
        faces.append([v.index for v in f.verts])
        if m[0] in GRAIN_U:
            uvs.append([(l.vert.co[va] / tile, l.vert.co[ua] / tile) for l in f.loops])
        else:
            uvs.append([(l.vert.co[ua] / tile, l.vert.co[va] / tile) for l in f.loops])
        mats.append(m[0])
    bm.free()
    P.mesh(verts, faces, uvs, mats, smooth=False)


def _incise_x(bm, faces, w, d):
    """final4 (judge: the poked pyramid shaded as four distinct triangles, a hipped-pyramid read; rear_alcove.png shows
    thin incised X lines on flat faces): each face stays FLAT except a narrow V-groove along both diagonals (2w wide,
    d deep over most of its length, rising to the surface at the corners so the box edges are never notched)."""
    s2 = math.sqrt(2.0)
    for f in faces:
        n = f.normal.copy()
        P = list(f.verts)
        C = sum((v.co for v in P), Vector()) / 4
        mi = f.material_index
        Fv, Lv = [], []
        for i in range(4):
            a, b = P[i], P[(i + 1) % 4]
            e = next(ed for ed in a.link_edges if b in ed.verts)
            t = w * s2 / (b.co - a.co).length
            pa, pb = a.co.copy(), b.co.copy()
            _, v1 = bmesh.utils.edge_split(e, a, 0.3)
            rest = next(ed for ed in v1.link_edges if b in ed.verts)
            _, v2 = bmesh.utils.edge_split(rest, v1, 0.5)
            v1.co, v2.co = pa + (pb - pa) * t, pb + (pa - pb) * t
            Fv.append(v1)
            Lv.append(v2)
        bmesh.ops.delete(bm, geom=[f], context="FACES_ONLY")
        cb = bm.verts.new(C - n * d)
        I = [bm.verts.new(C + (((P[i].co + P[(i + 1) % 4].co) / 2) - C).normalized() * w * s2) for i in range(4)]
        D = [bm.verts.new(P[i].co + (C - P[i].co) * 0.12 - n * d) for i in range(4)]
        new = []
        for i in range(4):
            j = (i - 1) % 4
            new += [bm.faces.new([Fv[i], Lv[i], I[i]]),
                    bm.faces.new([Lv[j], P[i], D[i]]), bm.faces.new([Lv[j], D[i], cb, I[j]]),
                    bm.faces.new([P[i], Fv[i], D[i]]), bm.faces.new([Fv[i], I[i], cb, D[i]])]
        for nf in new:
            nf.material_index = mi
            nf.normal_update()
            if nf.normal.dot(n) < 0:
                nf.normal_flip()


def box(G, P, x0, x1, y0, y1, z0, z1, mat, bev=0.0, grain=None, front=None, poke=None, poke_depth=0.0, recess=None,
        shape=None, ftol=0.99):
    """A box, its edges bevelled by `bev` (one segment: a crisp chamfer that catches the light). front = (dir, mat), or a
    list of them, puts another material on the face pointing that way (e.g. ("+y", BR); ftol = the normal tolerance, so
    a sloped face can be picked). poke = face directions ("+y", "+z", "-x" ...) whose face gets a thin incised X
    (_incise_x, `poke_depth` deep: the mitred X of the capitals, final4). shape(co) -> co moves the box corners before
    the bevel (the splayed head of the side slot). recess = (dir, [(inset, depth, mat), ...]): the face
    pointing `dir` is inset step by step (each step a ring `inset` wide, pushed `depth` in, in `mat`), e.g. a flat rim, a
    recess wall, a margin and a thin brass inlay line round a sunk field (the rack foot blocks); an optional third item
    is the sunk field's material."""
    g = _grow()
    x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
    bm = bmesh.new()
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    if shape:
        c = [tuple(shape(Vector(p))) for p in c]
    v = [bm.verts.new(p) for p in c]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)):
        bm.faces.new([v[i] for i in q])
    if bev > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bev, offset_type="OFFSET", segments=1, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
    if poke:
        bm.normal_update()
        sel = []
        for d in poke:
            axis, sgn = "xyz".index(d[1]), (1 if d[0] == "+" else -1)
            sel += [f for f in bm.faces if f.normal[axis] * sgn > 0.999]
        _incise_x(bm, sel, 0.0032, poke_depth)
    ext = (x1 - x0, y1 - y0, z1 - z0)
    if grain is None:
        grain = max(range(3), key=lambda i: ext[i])
    tiles = [(mat, G["TILE"].get(mat) or 1.0)]
    if front:
        bm.normal_update()
        for fd, fm in ([front] if isinstance(front[0], str) else front):
            if fm not in [q[0] for q in tiles]:
                tiles.append((fm, G["TILE"].get(fm) or 1.0))
            mi = [q[0] for q in tiles].index(fm)
            axis, sgn = "xyz".index(fd[1]), (1 if fd[0] == "+" else -1)
            for f in bm.faces:
                if f.normal[axis] * sgn > ftol:
                    f.material_index = mi
    if recess:
        axis, sgn = "xyz".index(recess[0][1]), (1 if recess[0][0] == "+" else -1)
        bm.normal_update()
        face = next(f for f in bm.faces if f.normal[axis] * sgn > 0.999)
        for t, d, m in recess[1]:
            if m not in [q[0] for q in tiles]:
                tiles.append((m, G["TILE"].get(m) or 1.0))
            mi = [q[0] for q in tiles].index(m)
            res = bmesh.ops.inset_individual(bm, faces=[face], thickness=t, depth=-d, use_even_offset=True)
            for f in res["faces"]:      # the new ring
                f.material_index = mi
            face.material_index = mi
        if len(recess) > 2:             # the sunk field left inside the last ring
            if recess[2] not in [q[0] for q in tiles]:
                tiles.append((recess[2], G["TILE"].get(recess[2]) or 1.0))
            face.material_index = [q[0] for q in tiles].index(recess[2])
    _emit(P, bm, tiles, grain)


def mirror_box(G, P, x0, x1, *rest, **kw):
    """The left part and its mirror about the centre line."""
    box(G, P, x0, x1, *rest, **kw)
    box(G, P, W - x1, W - x0, *rest, **kw)


def sweep(P, G, pts, w, side, mat, h=None, taper=None):
    """A bar along the polyline pts, w across (along `side`, a unit vector normal to the plane of the path) by h in the
    plane (default w: square); taper = per-point scale of the section (the hook narrows toward its tip). Mitred joints,
    capped ends: the J cradle hooks of the rack."""
    h = w if h is None else h
    taper = taper or [1.0] * len(pts)
    pts = [Vector(p) for p in pts]
    n = Vector(side).normalized()
    rings = []
    for k, p in enumerate(pts):
        t_in = (p - pts[k - 1]).normalized() if k > 0 else None
        t_out = (pts[k + 1] - p).normalized() if k < len(pts) - 1 else None
        t = (t_in + t_out).normalized() if (t_in and t_out) else (t_in or t_out)
        b = t.cross(n).normalized()
        sc = 1.0 / max(0.5, (t_in.dot(t) if t_in else 1.0))
        hw, hb = w / 2 * taper[k], h / 2 * sc * taper[k]
        rings.append([p + n * sn * hw + b * sb * hb for sn, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    verts = [tuple(v) for r in rings for v in r]
    faces = []
    for k in range(len(rings) - 1):
        for i in range(4):
            j = (i + 1) % 4
            faces.append([4 * k + i, 4 * k + j, 4 * (k + 1) + j, 4 * (k + 1) + i])
    faces.append([3, 2, 1, 0])
    last = 4 * (len(rings) - 1)
    faces.append([last, last + 1, last + 2, last + 3])
    out = faces   # by construction: side quads wind toward -b of their edge (outward), caps -t / +t
    tile = G["TILE"].get(mat) or 1.0
    uvs = [[(verts[i][0] / tile + verts[i][1] / tile, verts[i][2] / tile) for i in f] for f in out]
    P.mesh(verts, out, uvs, mat)




def kumiko(P, G, x0, x1, z0, z1, y, nc, nr, mat, bar=0.012, ring=0.0108, reach=(0.68, 0.50)):
    """The pierced ornamental grille of back_wall.png (final3: the judge read final2's regular hexagonal honeycomb as a
    perforated plate; the reference is an irregular, interlocking geometric fretwork with smaller, varied openings):
    a square grid of thin flat bars (nc x nr cells) with a diamond ring in every cell, in a checkerboard of two sizes:
    the large rings reach `reach[0]` of the pitch from the cell centre, past the cell edges into the neighbouring
    cells, so they interlock with the small rings (`reach[1]`, corners on the cell edges) over the grid bars. The
    openings come out varied: large and small diamonds, small triangles in the cell corners and lozenges where the rings
    cross. Flat single-sided strips facing +Y in three layers 0.8 mm apart
    (rings in a checkerboard on two layers, bars in front), so overlapping strips never share a plane. 8 tris per ring,
    2 per bar."""
    cw, ch = (x1 - x0) / nc, (z1 - z0) / nr
    verts, faces = [], []

    def quad(pts):
        """A quad facing +Y; its corners are shared with any earlier corner at the same point (no coincident verts)."""
        q = []
        for pt in pts:
            key = tuple(round(c, 7) for c in pt)
            if key not in index:
                index[key] = len(verts)
                verts.append(pt)
            q.append(index[key])
        p = [Vector(verts[i]) for i in q]
        if (p[1] - p[0]).cross(p[2] - p[0]).y < 0:
            q = q[::-1]
        faces.append(q)
    index = {}
    s2 = math.sqrt(2.0)
    for j in range(nr):
        for i in range(nc):
            cx, cz = x0 + (i + 0.5) * cw, z0 + (j + 0.5) * ch
            r = reach[(i + j) % 2]
            ax, az = r * cw, r * ch                             # outer half-diagonals
            bx, bz = ax - ring * s2, az - ring * s2              # inner
            yy = y + (0.0008 if (i + j) % 2 else 0.0)
            # clip the outer corners at the frame so no ring pokes past the grille edge
            def cl(px, pz):
                return (min(max(px, x0), x1), yy, min(max(pz, z0), z1))
            o = [cl(cx + ax, cz), cl(cx, cz + az), cl(cx - ax, cz), cl(cx, cz - az)]
            n = [cl(cx + bx, cz), cl(cx, cz + bz), cl(cx - bx, cz), cl(cx, cz - bz)]
            for k in range(4):
                m = (k + 1) % 4
                quad([o[k], o[m], n[m], n[k]])
    yb = y + 0.0016
    for i in range(1, nc):
        xb = x0 + i * cw
        quad([(xb - bar / 2, yb, z0), (xb + bar / 2, yb, z0), (xb + bar / 2, yb, z1), (xb - bar / 2, yb, z1)])
    for j in range(1, nr):
        zb = z0 + j * ch
        quad([(x0, yb + 0.0006, zb - bar / 2), (x1, yb + 0.0006, zb - bar / 2), (x1, yb + 0.0006, zb + bar / 2),
              (x0, yb + 0.0006, zb + bar / 2)])
    tile = G["TILE"].get(mat) or 1.0
    uvs = [[(verts[i][0] / tile, verts[i][2] / tile) for i in f] for f in faces]
    P.mesh(verts, faces, uvs, mat)


def pieces(G):
    P = G["Piece"]("SM_AK_RearAlcove")
    _count[0] = 0

    # ---- the two posts (left one at x 0..0.28, mirrored), front face of the plinth flush with the piece front y = 0.6
    # final3: one clean shaft face (the casing beside it is set back into shadow, with a thin bronze reveal line between
    # them), a single base block (no split groove), the base band raised with the taller cabinet
    BB = 0.56                                                                               # base block top
    mirror_box(G, P, 0.0, 0.28, 0.32, 0.60, 0.0, 0.045, T, bev=0.006, grain=0)            # foot plinth
    mirror_box(G, P, 0.012, 0.268, 0.332, 0.588, 0.045, 0.078, BR, grain=0)                # brass foot band
    mirror_box(G, P, 0.006, 0.268, 0.332, 0.588, 0.078, BB, T, bev=0.005, grain=2)        # base block
    mirror_box(G, P, 0.010, 0.264, 0.336, 0.584, BB, BB + 0.05, BR, grain=0)              # brass band over the base
    mirror_box(G, P, 0.041, 0.246, 0.35, 0.556, BB + 0.05, 2.95, T, bev=0.007, grain=2)   # shaft
    mirror_box(G, P, 0.036, 0.251, 0.345, 0.561, 2.944, 2.977, BR, grain=0)               # brass collar
    for x0, x1, outer in ((0.0065, 0.2805, "-x"), (W - 0.2805, W - 0.0065, "+x")):
        box(G, P, x0, x1, 0.32, 0.5935, 2.975, 3.1935, T, bev=0.003, grain=2, poke=("+y", "+z", outer),
            poke_depth=0.004)                                                                # capital (incised X)
    # the niche cheeks behind the posts, flush with the lintel top. final4 (judge: the side slot read as a flat lit
    # plane; rear_alcove.png's side view looks THROUGH it into the lit interior: a rack upright and its hook, the sloped
    # soffit at its head, the lacquer cabinet side with a lit top edge at its foot; its 3/4 shows the other outer face
    # as plain dark timber): an OPEN slot through the -X cheek only (the side the reference's side view shows), its
    # walls dark timber, its head splayed (a light-timber sloped soffit), its foot 10 cm below the cabinet top so the
    # cabinet end and its brass top line show; the +X cheek is plain (no see-through, no lit strip)
    SY0, SY1, SZ1, SB, SPL = 0.09, 0.30, 2.90, CT - 0.10, 0.075
    xa, xb = 0.04, 0.345
    for y0, y1, z0, z1 in ((0.0, SY0, 0.0, 3.1917), (SY1, 0.352, 0.0, 3.1917), (SY0, SY1, 0.0, SB)):
        box(G, P, xa, xb, y0, y1, z0, z1, T, grain=2 if z1 - z0 > 0.5 else 1, front=("+x", RT))
    box(G, P, xa, xb, SY0, SY1, SZ1, 3.1917, T, grain=1, front=[("+x", RT), ("-z", RT)], ftol=0.9,
        shape=lambda co: Vector((co.x, co.y, co.z + SPL * (xb - co.x) / (xb - xa) if co.z < 3.0 else co.z)))
    box(G, P, W - 0.345, W - 0.04, 0.0, 0.352, 0.0, 3.1917, T, grain=2, front=("-x", RT))   # +X cheek, plain
    box(G, P, 0.2605, 0.2655, 0.03, 0.34, CT - 0.022, CT - 0.010, LE, grain=1)             # lit top edge, cabinet end

    # ---- lintel straight over the lit opening, the side casings (final3: set 6.6 cm back behind the shaft face, in
    # shadow) with the thin bronze reveal line at the shaft's inner edge, and the dark-bronze inner reveal
    box(G, P, 0.279, W - 0.279, 0.34, 0.57, 2.95, 3.1925, T, bev=0.005, grain=0)          # lintel, set back 2.35 cm
    box(G, P, 0.25, W - 0.25, 0.0, 0.345, 3.09, 3.191, T, grain=0)                         # closes the top behind it
    mirror_box(G, P, 0.245, 0.32, 0.34, 0.49, BB, 2.955, T, bev=0.004, grain=2)            # side casings (recessed)
    mirror_box(G, P, 0.2455, 0.2525, 0.48, 0.549, BB + 0.05, 2.944, BZ, grain=2)          # thin bronze reveal line
    box(G, P, 0.315, 0.346, 0.33, 0.50, CT, 2.955, BZ, bev=0.003, grain=2, front=("+x", RT))
    box(G, P, W - 0.346, W - 0.315, 0.33, 0.50, CT, 2.955, BZ, bev=0.003, grain=2, front=("-x", RT))
    box(G, P, 0.34, W - 0.34, 0.3315, 0.5235, 2.938, 2.952, BZ, bev=0.003, grain=0)       # head reveal
    box(G, P, 0.345, W - 0.345, 0.0, 0.345, 2.956, 3.095, T, grain=0)                       # niche ceiling (soffit)
    for xl, yl in ((0.55, 0.25), (1.25, 0.25), (CX, 0.10)):
        P.cyl(xl, yl, 2.9495, 2.958, 0.036, BR, 12).cyl(xl, yl, 2.9455, 2.95, 0.025, LED, 12)
    box(G, P, 0.35, W - 0.35, 0.29, 0.325, 2.947, 2.958, LE, grain=0)                       # soffit LED strip

    # ---- the backlit panel with its LED edge lines round ALL FOUR sides; one quad carrying the whole T_AK_HAlcovePanel
    # picture (unique 0-1 UV). With the grille (default) it stops under the grille rail; without it (AK_RA_NO_GRILLE=1)
    # it runs up to the soffit.
    ztop = 2.34 if GRILLE else 2.945
    px0, px1, pz0, pz1, py = 0.345, W - 0.345, CT - 0.05, ztop, 0.02
    P.mesh([(px0, py, pz0), (px1, py, pz0), (px1, py, pz1), (px0, py, pz1)], [[0, 3, 2, 1]],
           [[(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]], LIT)
    mirror_box(G, P, 0.345, 0.360, 0.02, 0.034, CT, ztop - 0.018, LE, grain=2)
    box(G, P, 0.345, W - 0.345, 0.02, 0.048, ztop - 0.018, ztop - 0.007, LE, grain=0)      # glow line at the head
    box(G, P, 0.355, W - 0.355, 0.021, 0.036, CT - 0.002, CT + 0.062, LE, grain=0)          # glow line at the foot
    if GRILLE:
        box(G, P, 0.345, W - 0.345, 0.0, 0.056, 2.333, 2.36, T, bev=0.003, grain=0)       # slim dark grille rail
        # ---- the ornamental grille over its gold backlight, full opening width, up to the soffit
        # final4: the gold backlight is one quad carrying T_AK_HAlcoveGrille (unique 0-1 UV, hot spot at the top centre)
        gx0, gx1, gz0, gz1 = 0.345, W - 0.345, 2.355, 2.96
        P.mesh([(gx0, 0.02, gz0), (gx1, 0.02, gz0), (gx1, 0.02, gz1), (gx0, 0.02, gz1)], [[0, 3, 2, 1]],
               [[(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]], GG)
        box(G, P, 0.345, W - 0.345, 0.02, 0.05, 2.358, 2.376, T, grain=0)
        box(G, P, 0.345, W - 0.345, 0.02, 0.05, 2.91, 2.926, T, grain=0)
        box(G, P, 0.345, W - 0.345, 0.021, 0.046, 2.926, 2.957, LE, grain=0)               # head glow line
        mirror_box(G, P, 0.345, 0.365, 0.02, 0.05, 2.376, 2.91, T, grain=2)
        kumiko(P, G, 0.365, W - 0.365, 2.376, 2.91, 0.040, 24, 12, LB)

    # ---- the black lacquer base cabinet (final3: 72 cm, every height scaled 1.2x from the 60 cm one)
    s = CT / 0.60
    box(G, P, 0.27, W - 0.27, 0.03, 0.55, 0.0, 0.10 * s, LQ, bev=0.005, grain=0)
    box(G, P, 0.28, W - 0.28, 0.03, 0.54, 0.10 * s, CT - 0.034, LQ, grain=0)
    box(G, P, 0.265, W - 0.265, 0.02, 0.556, CT - 0.035, CT, LQ, bev=0.004, grain=0)
    box(G, P, 0.27, W - 0.27, 0.553, 0.559, CT - 0.024, CT - 0.012, BR, grain=0)             # slim brass top line
    mirror_box(G, P, 0.28, 0.335, 0.53, 0.55, 0.10 * s, CT - 0.034, LQ, bev=0.003, grain=2)  # stiles
    box(G, P, 0.335, W - 0.335, 0.53, 0.55, CT - 0.085, CT - 0.034, LQ, bev=0.003, grain=0)  # top rail
    box(G, P, 0.335, W - 0.335, 0.53, 0.55, 0.10 * s, 0.17, LQ, bev=0.003, grain=0)          # bottom rail
    zf0, zf1 = 0.18, CT - 0.095
    box(G, P, 0.345, W - 0.345, 0.53, 0.546, zf0, zf1, LQ, bev=0.003, grain=0)              # recessed drawer field
    box(G, P, 0.363, W - 0.363, 0.545, 0.5475, zf0 + 0.018, zf0 + 0.022, BR, grain=0)        # brass inlay line
    box(G, P, 0.363, W - 0.363, 0.545, 0.5475, zf1 - 0.022, zf1 - 0.018, BR, grain=0)
    mirror_box(G, P, 0.363, 0.367, 0.545, 0.5475, zf0 + 0.022, zf1 - 0.022, BR, grain=2)
    zc = (zf0 + zf1) / 2
    P.mesh(*G["disc_y"](CX, 0.5515, zc, 0.103, 0.0075, BR, BR, 40, +1))                    # brass bezel
    P.mesh(*G["disc_y"](CX, 0.558, zc, 0.095, 0.0135, EM, BR, 40, +1))                      # the user's emblem

    # ---- the EMPTY rack for five standing swords (rear_alcove.png): a stepped base bar, five plain black lacquer foot
    # blocks with a thin brass collar, square uprights 19.5 cm apart, each with a plain dark sleeve carrying a slim
    # upturned black hook that sweeps out to the viewer's right. final3: no brass on the hooks, no inlay on the blocks,
    # everything raised with the cabinet (uprights 1.20 m over the bar, hooks at 0.90 m). No swords.
    ZP = CT + 0.01                                  # bar bottom
    ZS, ZB = ZP + 0.03, ZP + 0.047                  # step, bar top
    ZF, ZT, ZH = ZB + 0.14, ZB + 1.20, ZB + 0.90    # foot-block top, upright top, hook root
    box(G, P, 0.405, W - 0.405, 0.15, 0.31, ZP, ZS, RL, bev=0.004, grain=0)                # lower step
    box(G, P, 0.417, W - 0.417, 0.162, 0.298, ZS - 0.001, ZB, RL, bev=0.003, grain=0)       # upper step
    box(G, P, 0.43, W - 0.43, 0.17, 0.29, CT - 0.002, ZP + 0.0015, RL, grain=0)            # recessed plinth
    box(G, P, 0.44, W - 0.44, 0.2895, 0.296, CT + 0.0005, CT + 0.009, LE, grain=0)         # under-glow strip
    # final4: the hooks sweep out to the viewer's right AND a little back (35 deg), so the side view through the slot
    # shows the hook's profile pointing back as rear_alcove.png's side view does (was 15 deg toward the front)
    out = Vector((-math.cos(math.radians(35)), -math.sin(math.radians(35)), 0.0))
    side = out.cross(Vector((0, 0, 1))).normalized()
    up = Vector((0, 0, 1))
    # the hook in its plane (u out from the upright axis, v up): straight out of the sleeve, a round upturn, the tip
    # rising and turning back in a little; it narrows toward the tip (1.6 x 1.9 cm at the root, all dark)
    # final4 (judge: ~5 visible facets on the curve): the upturn in 10-degree steps (14 segments on the curve)
    arc = [(0.0, 0.0), (0.024, 0.0), (0.036, 0.0)]
    for a in range(-80, 51, 10):                   # the upturn: radius 2.8 cm about (0.036, 0.028), tip turning in
        arc.append((0.036 + 0.028 * math.cos(math.radians(a)), 0.028 + 0.028 * math.sin(math.radians(a))))
    taper = [1.0, 1.0] + [1.0 - 0.45 * k / (len(arc) - 3) for k in range(len(arc) - 2)]
    for k in range(-2, 3):
        xc, yc = CX + k * 0.195, 0.23
        box(G, P, xc - 0.05, xc + 0.05, yc - 0.05, yc + 0.05, ZB - 0.001, ZF, RL, bev=0.004, grain=2)  # foot block
        box(G, P, xc - 0.022, xc + 0.022, yc - 0.022, yc + 0.022, ZF - 0.002, ZF + 0.010, BR,
            grain=0)                                                                        # thin brass collar
        box(G, P, xc - 0.016, xc + 0.016, yc - 0.016, yc + 0.016, ZF + 0.006, ZT, RL, bev=0.004, grain=2)
        box(G, P, xc - 0.021, xc + 0.021, yc - 0.021, yc + 0.021, ZH - 0.02, ZH + 0.04, RL, bev=0.003,
            grain=2)                                                                        # plain dark sleeve
        p0 = Vector((xc, yc, ZH))
        sweep(P, G, [tuple(p0 + out * u + up * v) for u, v in arc], 0.016, side, HK, h=0.019, taper=taper)

    P.col(0, 1.8, 0, 0.6, 0, 3.2)   # the scripted piece's collision, unchanged
    return [P, corner_niche(G, "W"), corner_niche(G, "E")]


# ------------------------------------------------------------------------------------------------ corner showcases
# rear dais (2026-09-28, the user: "a showcase on both left and right corners"): armory3_reference2.png shows, in each
# rear corner outboard of the rack alcove, a small backlit showcase niche facing the entrance (left x 380-417, right
# x 1035-1070; opening y 170-234 on a dark base cabinet y 234-255, its counter about level with the rack tansu; a cream
# backlit panel, a dark head band with a warm downlight; the reference shows a small figure in it, which we do NOT copy:
# it stays EMPTY, no stand or placeholder). The top-down (armory3_reference.png) has one lit fixture per side there.
# NEW piece SM_AK_H_CornerShowcase, in the alcove's materials: 0.70 wide x 0.55 deep x 1.96 m on the +0.90 deck (counter
# +1.65, level with the tansu top +1.62; opening 0.54 x 1.00 m, +1.65 to +2.65; head band to +2.86). Local frame as the
# alcove: x 0..0.70, back at y 0 (wall side), open front at y 0.55, placed rot 180 (local +Y faces the room).
# b2 (C1 against reference 2, both measured against the neighbouring rack alcove): the opening is 0.46x the alcove's
# lit height there (b1 1.14 m: 0.53x) -> 1.00 m; the showcase stands against the alcove's outer post (reference 2: only
# the ~20 px dark pilaster between them; b1 left a second 0.12 m gap): X 0.49-1.19 / 10.81-11.51
# b4 (blind judge delta 4: from the entrance the b3 units read as tall, over-bright white slots, "lit doorways, not
# glazed cases"; reference 2's are modest dim niches): shorter and wider - 0.80 wide, the opening 0.66 x 0.72 m (+1.65
# to +2.37 on the deck; was 0.56 x 1.00), a 15 cm head band (top +2.52, now under the sill ledge's +2.549), a glazed
# front in a thin polished brass frame, the panel at under half the emission, no LED edge lines down the sides. The
# east unit is the mirror of the west (b3 had it 10 cm further in): X 0.39-1.19 / 10.81-11.61
# b8 (C1 against reference 2, 2x zoom: its corner niche is a tall recess, ~0.5 : 1, the b7 unit read square and low):
# 0.70 wide, the counter at +0.62 on the deck (+1.52 world, 10 cm under the rack tansu's top), the opening 0.56 x
# 1.00 m to +1.62 (+2.52), the 15 cm head band to +2.67. The sill ledge (X 0-0.335) stays 15.5 cm clear in plan.
# r20 rear round (2026-09-28, task delta 3: the b4-b9 unit read as a freestanding glass cabinet; reference 2's corner
# pieces are SHALLOW LIT WALL NICHES, backlit, recessed into the wall and facing the entrance, with a dark pilaster between
# each and the rack alcove; C1 zoom x 330-570 / y 140-400: the opening x ~381-412 (0.45 m at the back wall), ~0.48 : 1,
# its sill ~0.1 m over the rack tansu's top, its height ~0.47x the alcove's lit span; the dark band between it and the
# alcove's lit panel ~28 px, 0.41 m = the alcove's 0.28 m post + a 0.10 m pilaster): NEW pieces SM_AK_H_CornerNiche_W /
# _E (mirror images) replace SM_AK_H_CornerShowcase. A dark wall block fills the corner between the side wall's sill
# ledge and the rack alcove's outer post (X 0.34-1.50 / 10.50-11.66; the alcoves moved 0.30 m inboard, build_armory_kit
# REAR_ALCOVE_X), flush with the alcove fronts (Y 19.40), from the deck to the alcove's top (+4.10); a shallow niche is
# sunk 0.25 m into it next to the alcove (a 0.10 m pilaster between, the wide dark pilaster toward the side wall),
# 0.45 x 1.00 m, sill +0.85 on the deck (+1.75 world): a backlit cream panel (T_AK_HShowcasePanel) at its back, a warm
# pale lining on its returns, a hidden glow line and a lens under its head, a thin lacquer sill with a brass nose. Under
# it an inset panel field. EMPTY: no stand, figure or placeholder. Placed rot 180 like the alcove (local x 0..NB_W,
# back at y 0 = NB_BACK_Y, the face at y NB_D = Y 19.40).
# r16 niches round (2026-09-29, task (3): from C1 the r20 niches read as narrow lit slits beside the banners, partly
# hidden by them; reference 2's are framed display alcoves with a lit back and a plinth). Measured with the C1 camera
# (level shift lens, WorkFiles/armory/hero/room_preview/r16/niches/work/proj.py): the banners' cloth ends at y 145.7 and
# their gold tassels hang to y 164.6 (x 349-395 / 1053-1099 of 1448), right over the r20 opening (x 380-410, y 130-190),
# so its upper-left third sat behind the cloth and the right tassel. Reference 2's niche is x 382-412, y 170-235, its
# head just under the banner's foot, a dark surround, a lit cream back hot at the head, a small plinth at its foot.
# NOW: the opening sits under the tassels in the reference's pixel box, 0.50 m wide, 0.30 m deep. Its head is tied to
# the banners (niche_z: BANNER_Z - 0.20 = +2.20 world, C1 y ~168, the frame head's top meeting the tassel foot, as
# reference 2's niche head meets its banner's foot), its sill 2 cm over the rack alcove's cabinet top (as reference 2),
# so with the 4-riser deck (DECK_Z +0.60) the opening is 0.86 m tall, sill +0.74 / head +1.60 on the deck (+1.34 / +2.20
# world; C1 x ~379-413, y ~168-227 against reference 2's 382-412 / 170-235); on a higher deck the sill drops so the
# opening keeps 0.85 m under the banners. A black lacquer casing frame (6 cm face,
# 3.5 cm proud) with a brass bead round its sides and head; a lacquer plinth under it (12 cm tall, projecting 8 cm,
# 2 cm past the frame each side, its top the warm lining so it reads as a lit ledge, a brass nose line) whose top is the
# niche floor. The 0.10 m pilaster (with the frame in it) stays between the opening and the rack alcove's post. EMPTY.
# r17 niche round (2026-09-29, room judge: the framed r16 niches float high on the pier with no sill or plinth under
# them and little visible depth, so they read as lightboxes; reference 2 shows a lit shelf and a black lacquer cabinet
# under each corner alcove): the 12 cm lacquer plinth is replaced by
#   * a SILL SHELF in the casing's warm timber (NF), 4.5 cm thick, its top the warm lining (the lit niche floor), running
#     from the niche back out 8 cm past the block face (world Y 19.32: walk_check's niche routes reach 19.30) and 2 cm
#     past the frame each side; a brass nose line on its front edge; the frame stiles stand on it
#   * a BLACK LACQUER BASE CABINET under it, deck to the shelf, the frame's outer width (0.62 m), its front 4 cm proud of
#     the block face, set into a 1.5 cm shadow-gap bay cut 5 cm into the block: a recessed toe kick with a soft warm
#     under-glow on the deck, stiles and rails round a shallow drawer and a door field, each with a thin brass inlay
#     line, and the slim brass line on its top slab (as the rack alcove's tansu); no emblem (the tansu carries it)
#   * visible DEPTH: the recess 0.30 -> 0.38 m; the returns and soffit in the casing's warm timber (was the pale lining,
#     so they merged with the back), with a dark-bronze inner reveal (1.2 cm, 2 cm deep) round the sides and head just
#     behind the frame (as the rack alcove's), replacing the r16 gold LED arris lines that outlined it like a lightbox;
#     only the hidden glow line at the back panel's head and the head spot stay, so the back is hot at the head and
#     falls off toward the shelf
NB_W, NB_D, NB_H = 1.16, 0.545, 3.20
NB_X = (1.50, 11.66)               # instance x (rot 180: the piece spans x - NB_W .. x): X 0.34-1.50 / 10.50-11.66
NB_BACK_Y = 19.945                 # the back face: 5 cm clear of the north wall's upper base rail (Y 19.95-20.0)
# r17 fix round (blind judge 7/10 on r17/final, delta d: in CN_WestNiche_golden "the frame and cabinet stand out from
# the wall panel like a hutch rather than sitting recessed into it. Pull the surround flush with the wall so only the
# interior depth shows. The reference alcove is also a little wider"): the opening 0.50 -> 0.58 m wide; the casing frame
# flush with the block face (FR_P 0.035 -> 0), the sill shelf a 2 cm lip (PL_P 0.08 -> 0.02), the base cabinet's face
# 8 mm INSIDE its shadow-gap bay (CB_P 0.04 -> -0.008): nothing stands proud of the wall but the lip
NO_W, NO_PIL = 0.58, 0.10          # the niche opening's width (r17 fix round: 0.50); the pilaster beside the alcove
NO_H_MAX, NO_H_MIN = 0.88, 0.85    # the opening's height (niche_z)
HEAD_BELOW_BANNER = 0.20           # the head sits this far under the banners' tassel foot (BANNER_Z), world
NO_DEPTH = 0.38                    # sunk into the block (its back panel at local y NB_D - NO_DEPTH); r17: 0.30 -> 0.38
FR, FR_P = 0.06, 0.0               # the casing frame's face width and how far it stands proud of the block face (r17 fix: 0.035)
PL_H, PL_P, PL_X = 0.045, 0.02, 0.02  # r17: the sill shelf: thickness (was the 12 cm plinth), projection past the block (r17 fix: 0.08)
                                    # face (walk_check's niche routes stop 0.45 m before the face with a 0.35 m capsule,
                                    # so 0.10 m is the limit), overhang past the frame each side
CB_P, CB_GAP, CB_BAY = -0.008, 0.015, 0.05   # r17 base cabinet: front vs the block face (r17 fix: 0.04 proud), shadow gap, bay depth
CB_KICK, CB_KICK_IN = 0.07, 0.025          # its recessed toe kick: height, set-back
LIN = "M_AK_HShowcaseLining"
LITS = "M_AK_HShowcasePanel"
NF = "M_AK_HNicheFrame"            # r16 fix round: the casing frame's warm mid-brown timber


def niche_x(side):
    """The niche opening's local x range: rot 180 maps local x to world X = instance x - local x, so on the west piece
    local 0 is its alcove side (X 1.50), on the east piece its side-wall side (X 11.66)."""
    return (NO_PIL, NO_PIL + NO_W) if side == "W" else (NB_W - NO_PIL - NO_W, NB_W - NO_PIL)


def niche_z(G):
    """The opening's sill (the plinth top) and head, deck-relative: the head under the banners' tassels, the sill 2 cm
    over the rack alcove's cabinet top (CT), both as reference 2; if that leaves under NO_H_MIN (a higher deck), the sill
    drops instead."""
    z1 = G["BANNER_Z"] - HEAD_BELOW_BANNER - G["DECK_Z"]
    z0 = CT + 0.02
    z1 = min(z1, z0 + NO_H_MAX)
    if z1 - z0 < NO_H_MIN:
        z0 = z1 - NO_H_MIN
    return round(z0, 4), round(z1, 4)


def corner_niche(G, side):
    P = G["Piece"]("SM_AK_H_CornerNiche_" + side)
    assert abs(G["ROOM_L"] - 0.055 - NB_BACK_Y) < 1e-6, "hero_rear_alcove: NB_BACK_Y must follow ROOM_L (r20)"
    assert abs(G["REAR_ALCOVE_X"][0] - NB_X[0]) < 1e-6 and abs(G["REAR_ALCOVE_X"][1] + 1.8 - (NB_X[1] - NB_W)) < 1e-6, \
        "hero_rear_alcove: the niche blocks must meet the rear alcoves (REAR_ALCOVE_X)"
    assert NO_PIL >= FR + 0.03, "hero_rear_alcove: the frame must fit inside the pilaster beside the alcove"
    assert PL_P <= 0.10 and CB_P < PL_P, "hero_rear_alcove: the sill and cabinet must stay clear of the niche routes"
    W, D, H = NB_W, NB_D, NB_H
    (x0, x1), (z0, z1) = niche_x(side), niche_z(G)
    zs = z0 - PL_H                                                                           # the shelf's underside
    assert zs > 0.45, "hero_rear_alcove: the base cabinet must be a cabinet, not a step"
    yb = D - NO_DEPTH                                                                        # the niche's back plane
    ox0, ox1 = x0 - FR, x1 + FR                                                              # the frame's outer edges
    sx0, sx1 = ox0 - PL_X, ox1 + PL_X                                                        # the sill shelf
    cx0, cx1 = ox0, ox1                                                                      # the base cabinet
    bx0, bx1 = cx0 - CB_GAP, cx1 + CB_GAP                                                    # its shadow-gap bay
    assert bx0 > 0.0 and bx1 < W, "hero_rear_alcove: the cabinet bay must stay inside the block"
    # ---- the dark block: full-height piers outside the bay, the pier strips between the bay edge and the opening
    # above the shelf, the part over the head, the bay's set-back wall under the shelf, the fill behind the back panel
    box(G, P, 0.0, bx0, 0.0, D, 0.0, H, T, bev=0.004, grain=2)
    box(G, P, bx1, W, 0.0, D, 0.0, H, T, bev=0.004, grain=2)
    box(G, P, bx0 - 0.001, x0, 0.0, D, zs, H, T, bev=0.004, grain=2)
    box(G, P, x1, bx1 + 0.001, 0.0, D, zs, H, T, bev=0.004, grain=2)
    box(G, P, x0 - 0.001, x1 + 0.001, 0.0, D, z1, H, T, bev=0.004, grain=0)
    box(G, P, bx0 - 0.001, bx1 + 0.001, 0.0, D - CB_BAY, 0.0, zs + 0.002, T, grain=0)       # bay wall (set back)
    box(G, P, x0, x1, 0.0, yb, zs, z1, T, grain=2)                                           # fill behind the back
    # ---- the backlit cream panel (one quad, unique 0-1 UV: T_AK_HShowcasePanel), a hidden glow line along its head
    P.mesh([(x0, yb + 0.001, z0), (x1, yb + 0.001, z0), (x1, yb + 0.001, z1), (x0, yb + 0.001, z1)], [[0, 3, 2, 1]],
           [[(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0)]], LITS)
    box(G, P, x0 + 0.01, x1 - 0.01, yb, yb + 0.012, z1 - 0.016, z1 - 0.004, LE, grain=0)      # glow line at the head
    # ---- r17: the returns and the soffit in the casing's warm timber (they take the head spot's graze and fall into
    # shadow toward the front, so the recess depth reads against the lit back), a dark-bronze inner reveal just behind
    # the frame round the sides and head
    box(G, P, x0, x0 + 0.008, yb, D, z0, z1, NF, grain=2)
    box(G, P, x1 - 0.008, x1, yb, D, z0, z1, NF, grain=2)
    box(G, P, x0, x1, yb, D, z1 - 0.006, z1, NF, grain=0)
    box(G, P, x0 + 0.006, x0 + 0.018, D - 0.030, D - 0.008, z0, z1 - 0.004, BZ, bev=0.002, grain=2)
    box(G, P, x1 - 0.018, x1 - 0.006, D - 0.030, D - 0.008, z0, z1 - 0.004, BZ, bev=0.002, grain=2)
    box(G, P, x0 + 0.018, x1 - 0.018, D - 0.030, D - 0.008, z1 - 0.018, z1 - 0.004, BZ, bev=0.002, grain=0)
    # the lens under the head, 12 cm in front of the back panel
    P.cyl((x0 + x1) / 2, yb + 0.12, z1 - 0.0125, z1 - 0.005, 0.030, BR, 12)
    P.cyl((x0 + x1) / 2, yb + 0.12, z1 - 0.0165, z1 - 0.012, 0.021, LED, 12)
    # ---- r17: the sill shelf in the casing timber, its top the warm lining (the lit niche floor and the ledge in front
    # of the opening), from the back panel out PL_P past the block face; a brass nose line on its front edge
    box(G, P, sx0, sx1, yb, D + PL_P, zs, z0, NF, bev=0.004, grain=0, front=("+z", LIN))
    box(G, P, sx0 + 0.006, sx1 - 0.006, D + PL_P - 0.001, D + PL_P + 0.0025, zs + 0.016, zs + 0.026, BR, grain=0)
    # ---- r17: the black lacquer base cabinet in its bay, deck to the shelf (as the rack alcove's tansu: toe kick,
    # carcass, top slab with the slim brass line, stiles and rails round recessed fields with a brass inlay line)
    yf = D + CB_P                                                                            # the cabinet's face
    yc = D - CB_BAY                                                                          # its back (the bay wall)
    zt = zs - 0.003                                                                          # its top, under the shelf
    box(G, P, cx0 + CB_KICK_IN, cx1 - CB_KICK_IN, yc, yf - CB_KICK_IN, 0.0, CB_KICK, LQ, grain=0)   # recessed toe kick
    # (no toe-kick under-glow: at LE's emission it mirrored in the glossy deck as a hard gold line from C1)
    # a hidden LED strip under the shelf, just behind its nose: it washes down the cabinet's top slab, brass line and
    # fields, so the cabinet reads under the lit shelf (the shelf's underside never shows from C1)
    box(G, P, cx0 + 0.02, cx1 - 0.02, D + PL_P - 0.024, D + PL_P - 0.012, zs - 0.005, zs - 0.001, LE, grain=0)
    box(G, P, cx0, cx1, yc, yf - 0.018, CB_KICK, zt - 0.032, LQ, grain=0)                  # carcass
    box(G, P, cx0 - 0.004, cx1 + 0.004, yc, yf + 0.004, zt - 0.032, zt, LQ, bev=0.004, grain=0)   # top slab
    box(G, P, cx0 + 0.004, cx1 - 0.004, yf + 0.0035, yf + 0.0065, zt - 0.022, zt - 0.011, BR, grain=0)  # brass top line
    box(G, P, cx0, cx1, yf - 0.02, yf, CB_KICK, CB_KICK + 0.035, LQ, bev=0.003, grain=0)   # bottom rail
    box(G, P, cx0 + 0.04, cx1 - 0.04, yf - 0.02, yf, zt - 0.070, zt - 0.032, LQ, bev=0.003, grain=0)   # top rail
    for a0, a1 in ((cx0, cx0 + 0.04), (cx1 - 0.04, cx1)):
        box(G, P, a0, a1, yf - 0.02, yf, CB_KICK + 0.034, zt - 0.031, LQ, bev=0.003, grain=2)   # stiles
    # a shallow drawer over a door field, split by a mid rail; each field recessed 4 mm with a brass inlay line
    zd0, zd1 = CB_KICK + 0.035, zt - 0.070                                                  # between the rails
    zm = zd1 - 0.13                                                                          # the mid rail's top
    box(G, P, cx0 + 0.039, cx1 - 0.039, yf - 0.02, yf, zm - 0.03, zm, LQ, bev=0.003, grain=0)   # mid rail
    fx0, fx1 = cx0 + 0.04, cx1 - 0.04
    for f0, f1 in ((zd0, zm - 0.03), (zm, zd1)):
        box(G, P, fx0, fx1, yf - 0.022, yf - 0.004, f0, f1, LQ, grain=0)                   # recessed field
        e0, e1, g0, g1 = fx0 + 0.022, fx1 - 0.022, f0 + 0.022, f1 - 0.022
        box(G, P, e0, e1, yf - 0.0045, yf - 0.002, g0, g0 + 0.004, BR, grain=0)
        box(G, P, e0, e1, yf - 0.0045, yf - 0.002, g1 - 0.004, g1, BR, grain=0)
        box(G, P, e0, e0 + 0.004, yf - 0.0045, yf - 0.002, g0 + 0.004, g1 - 0.004, BR, grain=2)
        box(G, P, e1 - 0.004, e1, yf - 0.0045, yf - 0.002, g0 + 0.004, g1 - 0.004, BR, grain=2)
    # ---- the casing frame: two stiles standing on the shelf and a head rail across them (warm mid-brown NF)
    for a0, a1 in ((ox0, x0), (x1, ox1)):
        box(G, P, a0, a1, D - 0.010, D + FR_P, z0, z1, NF, bev=0.004, grain=2)
    box(G, P, ox0, ox1, D - 0.010, D + FR_P, z1, z1 + FR, NF, bev=0.004, grain=0)
    # a brass bead on the frame's face along its inner edge (both stiles and the head)
    bz = D + FR_P
    box(G, P, x0 - 0.018, x0 - 0.006, bz - 0.001, bz + 0.002, z0 + 0.006, z1 + 0.018, BR, grain=2)
    box(G, P, x1 + 0.006, x1 + 0.018, bz - 0.001, bz + 0.002, z0 + 0.006, z1 + 0.018, BR, grain=2)
    box(G, P, x0 - 0.006, x1 + 0.006, bz - 0.001, bz + 0.002, z1 + 0.006, z1 + 0.018, BR, grain=0)
    P.col(0, W, 0, D, 0, H)
    P.col(sx0, sx1, D, D + PL_P, zs, z0)
    if yf + 0.004 > D + 0.001:                    # r17 fix round: a cabinet set into its bay adds no collision
        P.col(cx0, cx1, D, yf + 0.004, 0.0, zs)
    return P


def instances():
    import armory_hero as AH
    z = AH.G["DECK_Z"]
    return [("SM_AK_H_CornerNiche_" + side, x, NB_BACK_Y, z, 180.0) for side, x in zip("WE", NB_X)]


def lights():
    """One warm spot at each corner niche's lens, down the backlit panel (role alcove, as the rack alcoves' lens spots;
    the b9 showcase's 0.8 power for the smaller niche; r16: it follows the lowered 0.50 x 0.85 m opening and, now the
    panel takes light, runs warmer (3200 -> 2500 K before the room's KELVIN_SHIFT): reference 2's niche back is a
    saturated amber, C1 mean RGB (0.82, 0.50, 0.23), where the 3200 K spot left ours a pale cream (0.95, 0.81, 0.69)), at 0.5 power
    (was 0.8: the spot now falls on the panel as well as the lining)."""
    import armory_hero as AH
    z = AH.G["DECK_Z"]
    z0, z1 = niche_z(AH.G)
    out = []
    for side, x in zip("WE", NB_X):
        xc = x - sum(niche_x(side)) / 2                                     # world X of the niche's centre
        yb = NB_BACK_Y - (NB_D - NO_DEPTH)                                   # world Y of the niche's back panel
        out.append({"type": "spot", "name": f"NicheSpot_{side}", "loc": [round(xc, 3), round(yb - 0.12, 3),
                    round(z + z1 - 0.02, 3)], "angle_deg": 90, "blend": 0.6, "kelvin": 2500, "role": "alcove",
                    "shadows": True, "power_scale": 0.5, "aim": [round(xc, 3), round(yb - 0.01, 3),
                                                                  round(z + z0, 3)]})
        # r17 fix round (delta d: the back panel lit over its full height, as reference 2's): a fill spot hidden just
        # behind the frame head, aimed at the lower half of the back panel
        out.append({"type": "spot", "name": f"NicheFill_{side}", "loc": [round(xc, 3), round(NB_BACK_Y - NB_D + 0.04, 3),
                    round(z + z1 - 0.03, 3)], "angle_deg": 60, "blend": 0.8, "kelvin": 2500, "role": "alcove",
                    "shadows": False, "power_scale": 0.35, "aim": [round(xc, 3), round(yb - 0.01, 3),
                                                                    round(z + z0 + 0.22 * (z1 - z0), 3)]})
    return out
