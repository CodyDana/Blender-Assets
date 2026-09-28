"""Hero wall pieces (armory_hero.py hook): the lit wall display niche (hall and platform heights), the kumiko lattice
window and the black lacquer sill ledge, modelled from the user's reference sheets
WorkFiles/armory/reference/wall_alcove.png, window.png and side_wall_bay.png (look: armory3_reference2.png).

Wall frame of the kit: length along local +X, inner face at local y = 0, thickness toward -Y, facing +Y (the room).

  SM_AK_WallPanel_Lit       85 x 29.4 x 240 cm niche bay (hall floor), ledge top +0.90
  SM_AK_WallPanel_Lit_190   the same bay 190 cm tall on the platform, ledge top +0.45 (placed at +0.60)
  SM_AK_Window_Lattice      150 x 4 x 145 cm lattice in the clear opening of SM_AK_WallUpper_Window_2 (mid wall)
  SM_AK_SillLedge_2         2 m run of the black lacquer sill (top +0.05 local = +2.64 world, vases stand on it)

Sheet reading (measured off the orthographic front views; the sheets are not drawn to the stated sizes, so member
sizes are the sheet's ratios fitted to the real sizes):
  wall_alcove: the prompt sets the niche "in a short section of dark timber wall": the wide boards and outer posts with
    plinth blocks are that wall (in the room: the posts and SM_AK_WallLower); the niche itself is the part between the
    narrow inner stiles (239 px = 85 cm): stile 17 px = 6 cm (a stile and a stepped lining), a 73 cm opening, a timber
    head over a lit valance band, the cream back board with LED lines on its side and top edges, a black lacquer ledge
    with a bright arris line, an LED line under its apron, a two-door black lacquer cabinet in a thin bronze reveal,
    and a dark timber base rail (heights from the floor at 0.489 cm/px: rail 9.3, doors 11.2-79.7, LED 80-81.5, apron
    81.5-86.7, slab 86.7-90).
  window: brown timber casing and sash, 15 vertical kumiko bars (bar 25 % of the pitch) and ONE horizontal rail at 44 %
    of the glass height from the top (the prompt said two rails; all four views of the sheet show one), no glazing.
  sill: a 9 cm thick black lacquer slab with a bright chamfered arris, a shadow gap where it meets the wall.

ENABLED stays False: the user reviews images of every piece before anything goes into the armory.
"""
import math

import bmesh
import bpy

ENABLED = False   # REQUIRED: never set True here; the user enables hero modules after reviewing the images

T, LQ, BR, BZ = "M_AK_Timber", "M_AK_Lacquer", "M_AK_Brass", "M_AK_Bronze"
BB, LS, LED = "M_AK_BackBoard", "M_AK_LEDSoft", "M_AK_LED"
SASH = "M_AK_HSash"   # the window sheet's warm brown sash timber (a satin flat colour; no new texture)

MATERIALS = {
    SASH: (None, 1.0, {"color": "#3A2415", "rough": 0.48, "coat": 0.15}),
}

_TILE = {T: 2.0}
_K = [0]   # part counter: a micro growth per part keeps separate parts from sharing vertices (QA coincident check)


# --------------------------------------------------------------------------- mesh helpers

def _grow():
    _K[0] += 1
    return 2e-6 * (_K[0] % 97)


def _box_bm(x0, x1, y0, y1, z0, z1):
    g = _grow()
    x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
    bm = bmesh.new()
    v = [bm.verts.new(c) for c in ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                                   (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for q in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (3, 0, 4, 7), (1, 2, 6, 5)):
        bm.faces.new([v[i] for i in q])
    bm.normal_update()
    return bm


def _ring_bm(x0, x1, z0, z1, wl, wr, wb, wt, y0, y1):
    """A rectangular picture frame in the XZ plane (outer x0-x1 / z0-z1, member widths left/right/bottom/top), y0-y1
    deep: one closed mesh, so the mitred corners share no coincident vertices with anything."""
    g = _grow()
    x0, x1, z0, z1, y0, y1 = x0 - g, x1 + g, z0 - g, z1 + g, y0 - g, y1 + g
    ix0, ix1, iz0, iz1 = x0 + wl + 2 * g, x1 - wr - 2 * g, z0 + wb + 2 * g, z1 - wt - 2 * g
    bm = bmesh.new()
    outer = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    inner = [(ix0, iz0), (ix1, iz0), (ix1, iz1), (ix0, iz1)]
    of = [bm.verts.new((x, y1, z)) for x, z in outer]
    inf = [bm.verts.new((x, y1, z)) for x, z in inner]
    ob = [bm.verts.new((x, y0, z)) for x, z in outer]
    ib = [bm.verts.new((x, y0, z)) for x, z in inner]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([of[i], of[j], inf[j], inf[i]])      # front (+Y)
        bm.faces.new([ob[j], ob[i], ib[i], ib[j]])        # back (-Y)
        bm.faces.new([ob[i], ob[j], of[j], of[i]])        # outer sides
        bm.faces.new([ib[j], ib[i], inf[i], inf[j]])      # inner sides
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def _bevel(bm, w, axes="xyz"):
    """Chamfer the edges running along the given axes by w (one segment: a clean game-res bevel)."""
    if w <= 0:
        return bm
    edges = []
    for e in bm.edges:
        d = e.verts[1].co - e.verts[0].co
        ax = "xyz"[max(range(3), key=lambda i: abs(d[i]))]
        if ax in axes:
            edges.append(e)
    bmesh.ops.bevel(bm, geom=edges, offset=w, offset_type="OFFSET", segments=1, profile=0.5, affect="EDGES",
                    clamp_overlap=True)
    bm.normal_update()
    return bm


def _emit(piece, bm, mat):
    """Append a bmesh to the piece: flat faces, one material, tiling UV0 in metres / tile with U along the face's
    longer extent (the kit's timber grain runs along U, i.e. along each member)."""
    tile = _TILE.get(mat, 1.0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    verts = [tuple(v.co) for v in bm.verts]
    idx = {v: i for i, v in enumerate(bm.verts)}
    faces, uvs = [], []
    for f in bm.faces:
        n = f.normal
        na = max(range(3), key=lambda i: abs(n[i]))
        plane = [i for i in range(3) if i != na]
        cs = [v.co for v in f.verts]
        ext = {i: max(c[i] for c in cs) - min(c[i] for c in cs) for i in plane}
        ua = max(plane, key=lambda i: ext[i])
        va = [i for i in plane if i != ua][0]
        faces.append([idx[v] for v in f.verts])
        uvs.append([(c[ua] / tile, c[va] / tile) for c in cs])
    piece.mesh(verts, faces, uvs, mat, smooth=False)
    bm.free()
    return piece


def box(piece, x0, x1, y0, y1, z0, z1, mat, bev=0.0, axes="xyz"):
    return _emit(piece, _bevel(_box_bm(x0, x1, y0, y1, z0, z1), bev, axes), mat)


def ring(piece, x0, x1, z0, z1, wl, wr, wb, wt, y0, y1, mat, bev=0.0):
    return _emit(piece, _bevel(_ring_bm(x0, x1, z0, z1, wl, wr, wb, wt, y0, y1), bev), mat)


# --------------------------------------------------------------------------- the lit wall niche

W = 0.85            # bay width between the posts (scripted: x 0-0.85)
ST = 0.045          # inner stile (sheet: 9 px of the 17 px stile)
LN = 0.060          # stile + stepped lining: the clear opening is x 0.06-0.79 (73 cm)
HEAD = 0.12         # timber head over the opening


def wall_panel(G, name, NH, DZ):
    p = G["Piece"](name)
    hd = NH - 0.05                  # soffit underside = the scripted lens plane (lights(): the panel spot sits at hd - 0.02)
    hf = NH - HEAD                  # head fascia underside
    top = DZ + 0.05                 # ledge top (scripted counter top)
    o0, o1 = LN, W - LN             # clear opening
    # stiles and their stepped linings, floor to the head
    for a, b, la, lb in ((0.0, ST, ST - 0.002, LN), (W - ST, W, W - LN, W - ST + 0.002)):
        box(p, a, b, 0.0, 0.278, 0.0, NH - 0.006, T, 0.004)
        box(p, la, lb, 0.0, 0.262, 0.0, hf + 0.004, T, 0.0025)
    # head: fascia proud of the stiles, soffit plate behind it carrying the downlight lens
    box(p, 0.0, W, 0.238, 0.285, hf, NH, T, 0.004)
    box(p, 0.004, W - 0.004, 0.0, 0.240, hd, NH - 0.003, T)
    p.cyl(0.425, 0.20, hd - 0.012, hd + 0.002, 0.035, BR, 16)
    p.cyl(0.425, 0.20, hd - 0.016, hd - 0.0115, 0.024, LED, 16)
    # lit valance band under the head (sheet: the warm band between the head and the back board)
    box(p, o0 - 0.002, o1 + 0.002, 0.212, 0.232, hf - 0.045, hf + 0.003, BB, 0.002, "x")
    # cream back board, LED lines on its side edges and along the top edge (under the valance)
    box(p, o0 - 0.004, o1 + 0.004, 0.0, 0.020, top - 0.01, hf - 0.02, BB)
    for a in (o0 + 0.0005, o1 - 0.0065):
        box(p, a, a + 0.006, 0.019, 0.027, top + 0.002, hf - 0.044, LS)
    box(p, o0 + 0.006, o1 - 0.006, 0.019, 0.027, hf - 0.053, hf - 0.045, LS)
    # black lacquer ledge: slab with a bright arris line, apron below, LED line under the apron
    box(p, o0 - 0.003, o1 + 0.003, 0.0, 0.290, top - 0.033, top, LQ, 0.003)
    box(p, o0 + 0.004, o1 - 0.004, 0.2855, 0.2915, top - 0.0080, top - 0.0030, BR)   # brass arris inlay
    box(p, o0 - 0.001, o1 + 0.001, 0.0, 0.282, top - 0.085, top - 0.031, LQ, 0.002, "x")
    box(p, o0 + 0.010, o1 - 0.010, 0.266, 0.275, top - 0.0975, top - 0.0845, LS)
    # the closed cabinet: carcass, bronze reveal frame, two lacquer doors split on the centre line
    dz0, dz1 = 0.112, top - 0.103
    box(p, o0 - 0.001, o1 + 0.001, 0.0, 0.250, 0.090, top - 0.084, LQ)
    ring(p, o0 + 0.0005, o1 - 0.0005, 0.095, dz1 + 0.006, 0.006, 0.006, 0.013, 0.006, 0.244, 0.2565, BZ)
    xm = (o0 + o1) / 2
    for a, b in ((o0 + 0.0055, xm - 0.0015), (xm + 0.0015, o1 - 0.0055)):
        box(p, a, b, 0.238, 0.262, dz0, dz1, LQ, 0.002)
    # dark timber base rail under the cabinet
    box(p, o0 - 0.002, o1 + 0.002, 0.0, 0.262, 0.0, 0.093, T, 0.003)
    p.col(0, 0.85, 0, 0.294, 0, NH)   # the scripted collision, unchanged
    return p


# --------------------------------------------------------------------------- the lattice window

WIN_W, WIN_H = 1.50, 1.45
N_BARS = 15


def window_lattice(G):
    p = G["Piece"]("SM_AK_Window_Lattice")
    W_, H_ = WIN_W, WIN_H
    # casing (front at +0.02), a stepped bead, the sash (front +0.012), then the kumiko (front +0.006)
    ring(p, 0.001, W_ - 0.001, 0.001, H_ - 0.001, 0.024, 0.024, 0.024, 0.026, -0.020, 0.020, SASH, 0.003)
    ring(p, 0.021, W_ - 0.021, 0.021, H_ - 0.023, 0.012, 0.012, 0.012, 0.012, -0.017, 0.016, SASH, 0.002)
    sx0, sx1 = 0.030, W_ - 0.030
    sz0, sz1 = 0.030, H_ - 0.034
    st, rb, rt = 0.052, 0.060, 0.070                      # sash stile, bottom rail, top rail
    ring(p, sx0, sx1, sz0, sz1, st, st, rb, rt, -0.016, 0.012, SASH, 0.0025)
    gx0, gx1 = sx0 + st, sx1 - st                         # the open light (no glazing: the sun shafts pass)
    gz0, gz1 = sz0 + rb, sz1 - rt
    # 16 equal panes between 15 bars; the bar is 25 % of the pitch (sheet: 7 px of 27.9 px)
    pitch = (gx1 - gx0) / (N_BARS + 1 - 0.25)
    bw = 0.25 * pitch
    pane = pitch - bw
    rc = gz1 - 0.44 * (gz1 - gz0)                         # the one horizontal rail, 44 % down the light
    rh = 0.030
    box(p, gx0 - 0.003, gx1 + 0.003, -0.015, 0.006, rc - rh / 2, rc + rh / 2, SASH, 0.0015, "x")
    for i in range(1, N_BARS + 1):
        xc = gx0 + i * pane + (i - 0.5) * bw
        # half-lapped at the rail: each bar runs rail-to-sash in two lengths set 1 mm behind the rail face
        for za, zb in ((gz0 - 0.003, rc - rh / 2 + 0.002), (rc + rh / 2 - 0.002, gz1 + 0.003)):
            box(p, xc - bw / 2, xc + bw / 2, -0.014, 0.005, za, zb, SASH, 0.0012, "z")
    p.col(0, 1.50, -0.02, 0.02, 0, WIN_H)   # the scripted collision, unchanged
    return p


# --------------------------------------------------------------------------- the sill ledge

def sill_ledge(G):
    p = G["Piece"]("SM_AK_SillLedge_2")
    # the 9 cm lacquer slab, chamfered along its length only (the 2 m runs butt into one continuous sill), standing
    # 1 cm off the wall over a recessed backer: the thin shadow gap along the wall line
    bm = _box_bm(0.0, 2.0, 0.010, 0.335, -0.040, 0.050)
    bmesh.ops.bevel(bm, geom=[e for e in bm.edges if abs((e.verts[1].co - e.verts[0].co).x) > 1.0
                              and min(v.co.y for v in e.verts) > 0.2], offset=0.005, offset_type="OFFSET",
                    segments=1, profile=0.5, affect="EDGES", clamp_overlap=True)
    _emit(p, bm, LQ)
    box(p, 0.0, 2.0, 0.0, 0.0125, -0.028, 0.038, LQ)
    p.col(0, 2, 0, 0.335, -0.04, 0.05)   # the scripted collision, unchanged
    return p


# --------------------------------------------------------------------------- hook

def pieces(G):
    _K[0] = 0
    return [wall_panel(G, "SM_AK_WallPanel_Lit", G["NICHE_H_FLOOR"], G["NICHE_DADO_FLOOR"]),
            wall_panel(G, "SM_AK_WallPanel_Lit_190", G["NICHE_H_PLAT"], G["NICHE_DADO_PLAT"]),
            window_lattice(G),
            sill_ledge(G)]
