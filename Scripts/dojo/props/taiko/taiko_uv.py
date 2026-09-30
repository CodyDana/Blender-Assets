"""Shared UV-layout constants for the taiko set (pure Python: imported by make_taiko_textures.py under system Python
and by build_taiko.py inside Blender). The textures bake position-aware wear (collar edges, the stick grip, the
drumhead rims) at the UV positions the build script maps those places to, so both must agree.

Fix round f1 (2026-09-27).
"""

# --- drum body (lacquer): U = x / LAC_TILE + LAC_U0 along the drum axis; V = WRAPS whole tiles around, seam at -Z
LAC_TILE = 2.0
LAC_U0 = 0.13
LAC_WRAPS = 2            # 2 whole tiles around the barrel: the lathe seam has no V jump (measurer f1)
X_COLLAR = 0.612         # mean x of the torn hide-collar edge (ragged +-0.013)

# --- drumhead (hide): planar disc UV per head, both heads inside one 2 m tile; the lip roll gets its own U strip
HIDE_TILE = 2.0
HEAD_CENTRE = {1: (0.25, 0.25), -1: (0.25, 0.75)}   # UV centre of the +X and the -X head
LIP_U0 = {1: 0.505, -1: 0.755}                      # lip roll strip start (U = LIP_U0 + arc length / HIDE_TILE)
LIP_UW = 0.035                                       # strip width in U (the rim darkening covers it)
HIDE_WRAPS = 2

# --- hide collar: its own strip texture, U across the band from the torn edge (0 = edge), V around
COLLAR_TILE_U = 0.25     # metres of band per U tile (256 px)
COLLAR_U_EDGE = 0.02     # U of the lifted lap edge top; the edge step face spans U 0 .. COLLAR_U_EDGE
COLLAR_WRAPS = 2

# --- stick: U along the stick (1 m tile), V = one whole tile around (texture period 0.25 m), no V seam jump
STICK_TILE_U = 1.0
STICK_TILE_V = 0.25
STICK_U0 = 0.05
STICK_L = 0.78
STICK_GRIP_WEAR = (0.0, 0.26)   # stick-local x range of the darker hand-wear band (grip end)

# --- stand
TIMBER_TILE = 2.0
TIMBER_END_TILE = 0.5

# --- r3 (2026-09-28): the drumsticks (bachi) moved onto a patch of the HIDE atlas (M_DKP_Taiko_Hide), so their own
# smooth oiled mid-brown wood needs no new material slot (the showcase's material recipes are fixed per slot). The
# hide tile's columns U 0.54-0.755 are unused (heads U 0-0.5, lip strips 0.505-0.54 and 0.755-0.79).
# Patch: U = around the stick (BACHI_UPX whole pixels, periodic, so the lathe seam has no step);
#        V = arc length along the turned profile from the grip-end pole, BACHI_V0 + s / HIDE_TILE (rows grow downward).
BACHI_U0_PX = 1168                       # first column of the patch in the 2048 px hide tile
BACHI_UPX = 296                          # patch width in px (one whole wrap round the stick)
BACHI_U0 = BACHI_U0_PX / 2048.0
BACHI_UW = BACHI_UPX / 2048.0
BACHI_V0 = 0.045                         # V of the grip-end pole
BACHI_VLEN = 0.43                        # V span reserved (0.86 m of arc; the stick's pole-to-pole arc is ~0.81 m)
BACHI_GRIP_WEAR = (0.02, 0.24)           # arc-length range of the soft hand-polish band (grip end)
STICK_ARC = 0.8409                       # pole-to-pole arc length of the r3 turned profile (build_taiko.stick_profile)
STICK_DOME_ARC = (0.053, 0.061)          # arc length of the grip / strike dome caps (pole to shoulder)
