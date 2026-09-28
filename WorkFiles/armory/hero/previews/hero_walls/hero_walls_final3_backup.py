"""Hero wall pieces (armory_hero.py hook): the lit wall display niche (hall and platform heights), the kumiko lattice
window and the black lacquer sill ledge, modelled from the user's reference sheets
WorkFiles/armory/reference/wall_alcove.png, window.png and side_wall_bay.png (look: armory3_reference2.png).

Wall frame of the kit: length along local +X, inner face at local y = 0, thickness toward -Y, facing +Y (the room).

  SM_AK_WallPanel_Lit       85 x 29.4 x 240 cm niche bay (hall floor), ledge top +0.90
  SM_AK_WallPanel_Lit_190   the same bay 190 cm tall on the platform, ledge top +0.45 (placed at +0.60)
  SM_AK_Window_Lattice      150 x 8 x 145 cm window in the clear opening of SM_AK_WallUpper_Window_2 (mid wall)
  SM_AK_SillLedge_2         2 m bay of the black lacquer sill (top +0.05 local = +2.64 world, vases stand on it)

Final round 3 (judge: niche 5, window 4, sill 7, bay 3):
  niche: the 85 cm bay width is fixed by the layout, so the lit opening is made BROAD, as wall_alcove.png's: 55 x 110 cm
    (2 : 1, was 41.7 x 138, 3.3 : 1; 65 % of the width) with the same opening in both heights. Slim outer posts (4.5 cm)
    with plinth blocks and end blocks (square sinkings), 8.5 cm wood-grain stiles with their own plinth blocks, a 2 cm
    black lacquer reveal round the opening and down beside the doors, a timber frieze (lintel) over the opening from
    post to post and a CAPPING BLOCK over the whole unit projecting 2-3.5 cm in front of the posts and stiles (the
    sheet's side / 3/4 views). The frieze is a fascia: the interior ceiling (and the downlight lens, where lights() puts
    the spot) stays at the head underside behind it. The back is pale cream washi (T_AK_HNicheWashi, tex_walls.py: an
    unlit emissive picture, even, the glow of the LED lines baked in next to them); continuous 9.5 mm LED lines down
    both back corners and across the top, their outer edges tucked under the reveal (the dashed edge of round 2: a 6 mm line
    sub-pixel wide, half under the reveal). A black ledge with an LED line under its nose, two black lacquer doors, a
    recessed toe kick with a down-facing LED strip (the warm line and the pool on the floor under the base).
  timber: M_AK_HWallOak (T_AK_HWallOak, tex_walls.py, 1 m tile): the sheets' subtle dark oak (fine straight grain, no
    copper streaks), end grain on the end faces of posts, blocks and beams. Every member gets its own grain offset.
  window: window.png's massing within the ~2 cm bbox tolerance: 15 x 8 cm posts (were 4 cm deep), a 17 cm head beam and a
    5 cm bottom rail 6 cm deep, a walnut sash set 2.8 cm back with a stepped inner bead 1.2 cm further back; the lattice
    now fills the scripted 1.50 x 1.45 frame (no plain board over the head: the frame and the see-through clear opening
    are the layout's), 17 kumiko bars (29 % of the pitch) and one rail 45 % down. Open: no pane (fixed decision).
  sill: a 5.5 cm gloss black lacquer board, its nose thinned to 3 cm by a raked underside (a light line along the front
    underside) with a 2.5 mm arris on the top front edge, on a 10 cm dark oak bearer: the board cantilevers 23.5 cm.
    Top +0.05 (vases), bbox and collision as scripted.

ENABLED stays False: the user reviews images of every piece before anything goes into the armory.
"""
import bmesh
import bpy  # noqa: F401  (the hook contract: the kit's materials live in bpy.data)

ENABLED = False   # REQUIRED: never set True here; the user enables hero modules after reviewing the images

T, LQ, BR, BZ = "M_AK_Timber", "M_AK_Lacquer", "M_AK_Brass", "M_AK_Bronze"
LED = "M_AK_LED"
OAK = "M_AK_HWallOak"         # the wall pieces' dark oak: T_AK_HWallOak (tex_walls.py), 1 m tile, end-grain band V >= 0.875
LE = "M_AK_HLEDEdge"          # the niche's golden LED lines (the kit's amber LEDs tone-map salmon here)
LD = "M_AK_HLEDDown"          # the down-facing toe-kick strip under the niche (a warm pool on the floor)
PAPER = "M_AK_HNicheWashi"    # the lit washi back panel: T_AK_HNicheWashi (tex_walls.py), unlit emissive picture
LINING = "M_AK_ScreenPanel"   # dark matte side linings of the lit niche
SASH = "M_AK_Plank"           # the kit's walnut board set: mid-brown sash timber with grain
GLOSS = "M_AK_Glaze"          # the kit's high-gloss black (vases): the sill's gloss lacquer

MATERIALS = {
    PAPER: ("HNicheWashi", None, {"emit_image": True, "emit": 1.95, "unlit": True}),
    OAK: ("HWallOak", 1.0, {}),
    LE: (None, 1.0, {"color": "#FFB347", "emit": 6.0}),
    LD: (None, 1.0, {"color": "#FFB65C", "emit": 30.0}),
}

_TILE = {T: 2.0, SASH: 4.0, OAK: 1.0}
_K = [0]   # part counter: a micro growth per part keeps separate parts from sharing vertices (QA coincident check)
END_V0 = 0.875   # T_AK_HWallOak: V 0.875-1.0 is the end-grain band

# T_AK_Plank_BC: 20 boards across V (0.05 each), one end joint per board per tile. (board centre v, joint u) of the
# brighter boards: each walnut member is mapped along one board, starting just past its joint (no seam on any member)
_BOARDS = ((0.4746, 0.6436), (0.3745, 0.4214), (0.5745, 0.0078), (0.3245, 0.8062), (0.7744, 0.4712),
           (0.4246, 0.0337), (0.6746, 0.2407))


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
    """A rectangular frame in the XZ plane (outer x0-x1 / z0-z1, member widths left/right/bottom/top), y0-y1 deep: one
    closed mesh (no internal faces, nothing coincident)."""
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


def _prism_x_bm(x0, x1, prof):
    """A straight extrusion along X of a convex YZ profile [(y, z), ...] (counter-clockwise seen from +X)."""
    bm = bmesh.new()
    a = [bm.verts.new((x0, y, z)) for y, z in prof]
    b = [bm.verts.new((x1, y, z)) for y, z in prof]
    n = len(prof)
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([a[i], a[j], b[j], b[i]])
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def _bevel_front(bm, w, yf):
    """Chamfer (one segment) the sharp edges lying in the front face plane y = yf."""
    if w <= 0:
        return bm
    edges = [e for e in bm.edges if len(e.link_faces) == 2
             and e.link_faces[0].normal.angle(e.link_faces[1].normal) > 0.5
             and all(abs(v.co.y - yf) < 1e-3 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=edges, offset=w, offset_type="OFFSET", segments=1, profile=0.5, affect="EDGES",
                    clamp_overlap=True)
    bm.normal_update()
    return bm


def _emit(piece, bm, mat, uvfn=None):
    """Append a bmesh to the piece: flat faces, one material, tiling UV0 in metres / tile with U along the face's
    longer extent (the kit's timber grain runs along U, i.e. along each member). uvfn(co, normal) overrides UV0."""
    tile = _TILE.get(mat, 1.0)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    verts = [tuple(v.co) for v in bm.verts]
    idx = {v: i for i, v in enumerate(bm.verts)}
    faces, uvs = [], []
    for f in bm.faces:
        n = f.normal
        cs = [v.co for v in f.verts]
        faces.append([idx[v] for v in f.verts])
        if uvfn:
            uvs.append([uvfn(c, n) for c in cs])
            continue
        na = max(range(3), key=lambda i: abs(n[i]))
        plane = [i for i in range(3) if i != na]
        ext = {i: max(c[i] for c in cs) - min(c[i] for c in cs) for i in plane}
        ua = max(plane, key=lambda i: ext[i])
        va = [i for i in plane if i != ua][0]
        uvs.append([(c[ua] / tile, c[va] / tile) for c in cs])
    piece.mesh(verts, faces, uvs, mat, smooth=False)
    bm.free()
    return piece


def box(piece, x0, x1, y0, y1, z0, z1, mat, bev=0.0):
    """A box; bev chamfers only its front (+Y) edges (the back and hidden faces stay square)."""
    return _emit(piece, _bevel_front(_box_bm(x0, x1, y0, y1, z0, z1), bev, y1), mat)


def ring(piece, x0, x1, z0, z1, wl, wr, wb, wt, y0, y1, mat, bev=0.0):
    return _emit(piece, _bevel_front(_ring_bm(x0, x1, z0, z1, wl, wr, wb, wt, y0, y1), bev, y1), mat)


def wood(piece, x0, x1, y0, y1, z0, z1):
    """A square walnut member (M_AK_Plank) with its grain mapped along one joint-free board run."""
    lo, hi = (x0, y0, z0), (x1, y1, z1)
    ax = max(range(3), key=lambda i: hi[i] - lo[i])
    mid = [(lo[i] + hi[i]) / 2 for i in range(3)]
    vc, uj = _BOARDS[_K[0] % len(_BOARDS)]
    tile = _TILE[SASH]

    def uv(c, n):
        na = max(range(3), key=lambda i: abs(n[i]))
        oth = [i for i in range(3) if i != na]
        if na == ax:   # end grain: a small patch on the same board
            return (uj + 0.03 + (c[oth[0]] - mid[oth[0]]) / tile, vc + (c[oth[1]] - mid[oth[1]]) / tile)
        acr = [i for i in oth if i != ax][0]
        return (uj + 0.02 + (c[ax] - lo[ax]) / tile, vc + (c[acr] - mid[acr]) / tile)
    return _emit(piece, _box_bm(x0, x1, y0, y1, z0, z1), SASH, uv)




def oak(piece, x0, x1, y0, y1, z0, z1, bev=0.0, grain=None):
    """A dark oak member (M_AK_HWallOak, 1 m tile) with its own grain offset. The grain runs along U, along the member:
    `grain` (0/1/2) or, by default, its longest extent in X / Z (the wall depth Y is never the grain of a block).
    The faces across the grain (end faces) map onto the texture's end-grain band (V >= END_V0)."""
    k = _K[0] + 1
    ou = (k * 0.618034) % 1.0
    ov = 0.02 + ((k * 0.381966) % 1.0) * 0.42          # long grain stays in V 0.02-0.86 (widest face across: 0.40)
    eu = 0.125 + 0.25 * (k % 4)                        # one of the end-grain band's four ring patches
    lo, hi = (x0, y0, z0), (x1, y1, z1)
    ext = [hi[i] - lo[i] for i in range(3)]
    ax = grain if grain is not None else max((0, 2), key=lambda i: ext[i])
    mid = [(lo[i] + hi[i]) / 2 for i in range(3)]
    bm = _bevel_front(_box_bm(x0, x1, y0, y1, z0, z1), bev, y1)

    def uv(c, n):
        na = max(range(3), key=lambda i: abs(n[i]))
        oth = [i for i in range(3) if i != na]
        if na == ax:     # end grain
            a, b = sorted(oth, key=lambda i: -ext[i])
            dv = max(-0.06, min(0.06, c[b] - mid[b]))
            return (eu + (c[a] - mid[a]), END_V0 + 0.0625 + dv)
        acr = [i for i in oth if i != ax][0]
        return (ou + (c[ax] - lo[ax]), ov + (c[acr] - lo[acr]))
    return _emit(piece, bm, OAK, uv)


# --------------------------------------------------------------------------- the lit wall niche

W = 0.85        # bay width between the room posts (scripted: x 0-0.85)
F = 0.294       # the unit's front face (scripted depth): the capping block's front
PO = 0.045      # outer post (inner edge): 4.5 cm
ST = 0.130      # wood-grain stile inner edge (8.5 cm stile)
RV = 0.150      # black lacquer reveal inner edge (2 cm): the lit opening is x 0.15-0.70 (55 cm)
OPEN_H = 1.10   # the lit opening, ledge top to the reveal band (tex_walls.py OPEN_W x OPEN_H: 55 x 110 cm, 2 : 1)
CAP = 0.050     # capping block: its underside is the interior ceiling (hd) that carries the lens
EB = 0.13       # end blocks under the cap on the post tops
# faces, back from the cap's front F: end blocks 0.6 cm, plinth blocks 1.2, posts 2.0, frieze 3.0, stiles 3.5,
# ledge 4.0, reveal 4.5, doors 5.0 cm; the toe kick 8 cm
Y_EB, Y_PB, Y_PO, Y_FR, Y_ST, Y_LG, Y_RV, Y_DR, Y_TK = (F - d for d in (0.006, 0.012, 0.020, 0.030, 0.035, 0.040,
                                                                         0.045, 0.050, 0.080))


def wall_panel(G, name, NH, DZ):
    p = G["Piece"](name)
    hd = NH - 0.05                  # interior ceiling = the scripted lens plane (lights(): the panel spot sits at hd - 0.02)
    top = DZ + 0.05                 # ledge top (scripted counter top)
    zl = top - 0.035                # ledge underside (a 3.5 cm black ledge)
    zo = top + OPEN_H               # the visible top of the lit opening (the reveal band's underside)
    zc = NH - CAP                   # the capping block's underside
    xm = W / 2
    L = lambda x: W - x             # noqa: E731  mirror across the bay

    # the capping block over the whole unit (projects 2-3.5 cm in front of the posts and stiles)
    oak(p, 0.0, W, 0.0, F, zc, NH, 0.003)
    # outer posts, their plinth blocks and end blocks (with small square sinkings)
    for a, b in ((0.0, PO), (L(PO), W)):
        oak(p, a, b, 0.0, Y_PO, 0.105, zc - EB + 0.002, 0.002)
    for a, b in ((0.0, PO + 0.006), (L(PO + 0.006), W)):
        oak(p, a, b, 0.0, Y_PB, 0.0, 0.11, 0.003, grain=2)
        oak(p, a, b, 0.0, Y_EB, zc - EB, zc + 0.001, 0.003, grain=2)
    for a, b in ((0.014, 0.036), (L(0.036), L(0.014))):
        box(p, a, b, Y_EB - 0.004, Y_EB + 0.0002, zc - EB / 2 - 0.011, zc - EB / 2 + 0.011, LQ)
    # the wood-grain stiles (up to the frieze) with their own plinth blocks
    for a, b in ((PO - 0.001, ST), (L(ST), L(PO - 0.001))):
        oak(p, a, b, 0.0, Y_ST, 0.070, zo + 0.021, 0.002)
    for a, b in ((PO - 0.001, ST + 0.002), (L(ST + 0.002), L(PO - 0.001))):
        oak(p, a, b, 0.0, Y_ST + 0.007, 0.0, 0.075, 0.002, grain=2)
    # the frieze (lintel fascia) post to post over the opening; behind it the cavity up to the cap (the lens)
    oak(p, PO - 0.001, L(PO - 0.001), Y_RV - 0.030, Y_FR, zo + 0.020, zc + 0.001, 0.002, grain=0)
    # the black lacquer reveal: 2 cm each side from the base to the frieze, and a 2 cm band under the frieze
    for a, b in ((ST - 0.001, RV), (L(RV), L(ST - 0.001))):
        box(p, a, b, Y_RV - 0.030, Y_RV, 0.060, zo + 0.021, LQ)
    box(p, RV - 0.0005, L(RV - 0.0005), Y_RV - 0.030, Y_RV - 0.0005, zo, zo + 0.0205, LQ)
    # dark matte side linings from the ledge to the interior ceiling
    for a, b in ((RV - 0.0105, RV), (L(RV), L(RV - 0.0105))):
        box(p, a, b, 0.012, Y_RV - 0.0295, zl, hd + 0.0005, LINING)
    # the cream washi back panel (unique 0-1 UV: T_AK_HNicheWashi is laid out on this face, tex_walls.py), a dark board
    # above it behind the frieze
    px0, px1, pz0, pz1 = RV - 0.0045, L(RV - 0.0045), top - 0.010, zo + 0.030

    def puv(c, n):
        return ((c.x - px0) / (px1 - px0), (c.z - pz0) / (pz1 - pz0))
    _emit(p, _box_bm(px0, px1, 0.001, 0.019, pz0, pz1), PAPER, puv)
    box(p, RV - 0.010, L(RV - 0.010), 0.001, 0.0185, pz1 + 0.0005, hd + 0.0005, LINING)
    # the LED lines: 9.5 mm showing, down both back corners and across the top; their outer edges tuck under the reveal
    # and the band (no sub-pixel slit of paper beside them)
    for a, b in ((RV - 0.002, RV + 0.010), (L(RV + 0.010), L(RV - 0.002))):
        box(p, a, b, 0.0195, 0.026, top + 0.0005, zo + 0.003, LE)
    box(p, RV + 0.0105, L(RV + 0.0105), 0.0195, 0.026, zo - 0.0095, zo + 0.003, LE)
    # the niche downlight lens under the interior ceiling (lights() places the spot here), behind the frieze
    p.cyl(0.425, 0.20, hd - 0.012, hd + 0.002, 0.035, BR, 16)
    p.cyl(0.425, 0.20, hd - 0.016, hd - 0.0115, 0.024, LED, 16)
    # the black lacquer ledge over the opening and its reveals, an LED line under its nose
    box(p, ST + 0.0005, L(ST + 0.0005), 0.012, Y_LG, zl, top, LQ, 0.0015)
    box(p, RV + 0.001, L(RV + 0.001), Y_DR - 0.004, Y_RV - 0.001, zl - 0.009, zl - 0.0005, LE)
    # the closed cabinet: carcass, two black lacquer doors split on the centre line
    box(p, RV - 0.001, L(RV - 0.001), 0.012, Y_DR - 0.006, 0.058, zl + 0.001, LQ)
    for a, b in ((RV + 0.001, xm - 0.0015), (xm + 0.0015, L(RV + 0.001))):
        box(p, a, b, Y_DR - 0.008, Y_DR, 0.064, zl - 0.0095, LQ, 0.0015)
    # the recessed toe kick and the down-facing LED strip under the carcass's front edge (warm line, pool on the floor)
    box(p, ST + 0.001, L(ST + 0.001), 0.0, Y_TK, 0.0, 0.0585, LQ)
    box(p, RV + 0.006, L(RV + 0.006), Y_TK + 0.002, Y_TK + 0.016, 0.051, 0.0575, LD)
    p.col(0, 0.85, 0, 0.294, 0, NH)   # the scripted collision, unchanged
    return p


# --------------------------------------------------------------------------- the lattice window

WIN_W, WIN_H = 1.50, 1.45
N_BARS = 17          # window.png: 17-19 vertical kumiko bars, evenly spaced
BAR_F = 0.29         # window.png: a bar is ~29 % of the pitch
RAIL_AT = 0.45       # window.png: the one rail 45 % down the opening


def window_lattice(G):
    p = G["Piece"]("SM_AK_Window_Lattice")
    W_, H_ = WIN_W, WIN_H
    CJ, CB, CH = 0.150, 0.050, 0.170      # window.png (scaled to the 1.50 m frame): posts, bottom rail, head beam
    S, ST_, SB = 0.050, 0.055, 0.045      # walnut sash: stiles, top rail, bottom rail
    B = 0.014                              # the stepped inner bead
    sz1 = H_ - CH                          # sash top = head beam underside
    gx0, gx1 = CJ + S + B, W_ - CJ - S - B
    gz0, gz1 = CB + SB + B, sz1 - ST_ - B
    # the casing: full-height 15 x 8 cm posts (end grain on top), the head beam and the bottom rail between them
    for a, b in ((0.0, CJ), (W_ - CJ, W_)):
        oak(p, a, b, -0.040, 0.040, 0.0, H_, 0.003, grain=2)
    oak(p, CJ - 0.0005, W_ - CJ + 0.0005, -0.034, 0.034, sz1, H_ - 0.0005, 0.003, grain=0)
    oak(p, CJ - 0.0005, W_ - CJ + 0.0005, -0.030, 0.030, 0.0005, CB, 0.002, grain=0)
    # the walnut sash, set 2.8 cm back: full-height stiles, rails between them
    sx0, sx1, sz0 = CJ + 0.0005, W_ - CJ - 0.0005, CB + 0.0005
    for a, b in ((sx0, sx0 + S), (sx1 - S, sx1)):
        wood(p, a, b, -0.026, 0.012, sz0, sz1 - 0.0005)
    wood(p, sx0 + S - 0.0005, sx1 - S + 0.0005, -0.0256, 0.0116, sz0 + 0.0002, sz0 + SB)
    wood(p, sx0 + S - 0.0005, sx1 - S + 0.0005, -0.0256, 0.0116, sz1 - ST_, sz1 - 0.0007)
    # the stepped inner bead, 1.2 cm behind the sash face
    bx0, bx1, bz0, bz1 = gx0 - B, gx1 + B, gz0 - B, gz1 + B
    for a, b in ((bx0 - 0.0005, bx0 + B), (bx1 - B, bx1 + 0.0005)):
        wood(p, a, b, -0.022, 0.0, bz0 - 0.0005, bz1 + 0.0005)
    for a, b in ((bz0 - 0.0003, bz0 + B), (bz1 - B, bz1 + 0.0003)):
        wood(p, bx0 + B - 0.0005, bx1 - B + 0.0005, -0.0215, -0.0005, a, b)
    # the open kumiko field: 17 bars evenly spaced, one rail 45 % down, bars half-lapped behind it
    pitch = (gx1 - gx0) / (N_BARS + 1)
    bw = BAR_F * pitch
    rc = gz1 - RAIL_AT * (gz1 - gz0)
    rh = 0.022
    wood(p, gx0 - 0.0005, gx1 + 0.0005, -0.021, -0.003, rc - rh / 2, rc + rh / 2)
    for i in range(1, N_BARS + 1):
        xc = gx0 + i * pitch
        for za, zb in ((gz0 - 0.002, rc - rh / 2 + 0.002), (rc + rh / 2 - 0.002, gz1 + 0.002)):
            wood(p, xc - bw / 2, xc + bw / 2, -0.020, -0.004, za, zb)
    p.col(0, 1.50, -0.02, 0.02, 0, WIN_H)   # the scripted collision, unchanged
    return p


# --------------------------------------------------------------------------- the sill ledge

def sill_ledge(G):
    p = G["Piece"]("SM_AK_SillLedge_2")
    # a 5.5 cm gloss black lacquer board over the full 2 m module (square ends: the next module abuts it), square at the
    # wall; the nose thinned to 3 cm by a raked underside (a light line along the front underside), a 2.5 mm arris on the
    # top front edge (a fine line of light)
    D, zb, zt, a = 0.335, -0.005, 0.050, 0.0025
    prof = [(0.0, zb), (D - 0.070, zb), (D - 0.004, 0.016), (D, 0.020), (D, zt - a), (D - a, zt), (0.0, zt)]
    _emit(p, _prism_x_bm(0.0, 2.0, prof), GLOSS)
    # the dark oak bearer under its back: the board cantilevers 23.5 cm from the bearer's face
    oak(p, 0.0005, 1.9995, 0.0005, 0.100, -0.040, zb + 0.001, 0.002, grain=0)
    p.col(0, 2, 0, 0.335, -0.04, 0.05)   # the scripted collision, unchanged
    return p


# --------------------------------------------------------------------------- hook

def pieces(G):
    _K[0] = 0
    return [wall_panel(G, "SM_AK_WallPanel_Lit", G["NICHE_H_FLOOR"], G["NICHE_DADO_FLOOR"]),
            wall_panel(G, "SM_AK_WallPanel_Lit_190", G["NICHE_H_PLAT"], G["NICHE_DADO_PLAT"]),
            window_lattice(G),
            sill_ledge(G)]
