"""Shared UV-layout constants for the taiko set (pure Python: imported by make_taiko_textures.py under system Python
and by build_taiko.py inside Blender). The textures bake position-aware wear (collar edges, the stick grip, the
drumhead rims) at the UV positions the build script maps those places to, so both must agree.

Fix round f1 (2026-09-27). t4 (2026-10-03): the body profile lives here too (body_r, body_arc), so the build's
lathe UVs (by arc length along the bulged profile) and the textures' position-aware bands agree.
"""
import math

# --- t4 (user 2026-10-03: "see how the reference's barrel is wider in the middle? Lets do the same"): the barrel
# profile traced from References/Dojo/taiko_tacks_ref_user.webp (WorkFiles/dojo/build/props/taiko/t4/
# trace_ref_profile.py -> ref_profile.json: a pinhole camera fitted to the two lip-crown outlines, rms 0.8 px, then
# every left / right body-edge pixel between the collars inverted to (z, r) on the surface of revolution). In the
# photo's crown radii: r(z) = 1.26487 - 0.13844 z^2 - 0.02606 z^4 (left / right / symmetric fits agree to 0.004; the
# belly sits at the mid-length), crown half-length 1.2826. Applied to ours by the fraction of the length (our head
# and overall length are kept): z = |x| / BODY_LC * REF_LC, r = BODY_RC * f(z). BODY_RC is our lip roll's outline
# radius seen from the photo's ~18 deg (the lip point whose normal is 71.5 deg from radial: 0.528 + 0.019 cos 71.5).
REF_F = (1.26487, -0.13844, -0.02606)
REF_LC = 1.2826
BODY_RC = 0.547          # t6: the lip roll's OUTERMOST radius LIP_RC + LIP_RHO (t4/t5: 0.534). The photo's camera fit
#                          takes the crown outline's semi-major (its left / right extremes) as the unit Rc, and at
#                          those extremes the silhouette is the roll's outermost point, so Rc <-> 0.547: with 0.534 the
#                          t6 overlay showed the body a constant 7 px per side (1.8 %) too narrow at the same head width
# t6 (2026-10-03, user: "see how the reference's barrel is wider in the middle? Lets do the same"; judge t5 item 1):
# the drum was 13 % too long for its width (crown half-length / belly 1.149, the photo 1.014). The drum is now built
# in DESIGN units: the wood alone is shortened by D_SHIFT per half (the collar, tacks, skirt and lip keep their
# distances from the crown and move inward with it: crown 0.777 -> 0.6858), body_r keeps the traced shape in
# normalised length (BODY_LC = the new crown half-length), and build_taiko scales the finished drum mesh uniformly by
# DRUM_SCALE, so the real drum is 1.554 m long again with a 1.531 m belly. Every x / radius constant here and in
# build_taiko's drum() is in design units (real = DRUM_SCALE x design); the stand works in real metres
# (build_taiko.body_R).
D_SHIFT = 0.777 - REF_LC * BODY_RC   # 0.0754: the design crown sits at the photo's 1.2826 Rc (0.7016)
BODY_LC = 0.776 - D_SHIFT          # t4: 0.776
DRUM_SCALE = 0.777 / (0.777 - D_SHIFT)   # 1.1075: the design crown 0.7016 -> the real 0.777 (length 1.554 m)


def body_r(x):
    """t4: the barrel's radius at axial position x (metres), the photo's traced profile (see above)."""
    z = abs(x) * REF_LC / BODY_LC
    return BODY_RC * (REF_F[0] + REF_F[1] * z * z + REF_F[2] * z ** 4)


_ARC_DX = 0.0005
_ARC = [0.0]
for _i in range(1, 1700):
    _x0, _x1 = (_i - 1) * _ARC_DX, _i * _ARC_DX
    _ARC.append(_ARC[-1] + math.hypot(_ARC_DX, body_r(_x1) - body_r(_x0)))


def body_arc(x):
    """t4: signed arc length along the body profile from the mid-plane x = 0 to x (metres)."""
    t = min(abs(x) / _ARC_DX, len(_ARC) - 1.001)
    i = int(t)
    a = _ARC[i] + (_ARC[i + 1] - _ARC[i]) * (t - i)
    return a if x >= 0 else -a


# --- drum body (lacquer): U = LAC_U0 + arc length along the profile / LAC_TILE (t4: was x / LAC_TILE; the bulged
# profile's slope reaches 0.33, 5 % stretch at the collar); V = WRAPS whole tiles around, seam at -Z
LAC_TILE = 2.0
LAC_U0 = 0.13
LAC_WRAPS = 2            # 2 whole tiles around the barrel: the lathe seam has no V jump (measurer f1)
X_COLLAR = 0.555 - D_SHIFT   # t6: design units, shifted with the collar; t4: the hide collar's lower edge = the flap-root ring X_ROOT (t3 0.600; r2-t2: 0.612, the
#                          torn edge); the lacquer's darkening band and its clean zone sit here


def lac_u(x):
    """t4: the lacquer's U at axial position x."""
    return LAC_U0 + body_arc(x) / LAC_TILE

# --- drumhead (hide): planar disc UV per head, both heads inside one 2 m tile; the lip roll gets its own U strip
HIDE_TILE = 2.0
HEAD_CENTRE = {1: (0.25, 0.25), -1: (0.25, 0.75)}   # UV centre of the +X and the -X head
LIP_U0 = {1: 0.505, -1: 0.755}                      # lip roll strip start (U = LIP_U0 + arc length / HIDE_TILE)
LIP_UW = 0.035                                       # strip width in U (the rim darkening covers it)
HIDE_WRAPS = 2

# --- hide collar: its own strip texture, U across the band from the torn edge (0 = edge), V around
COLLAR_TILE_U = 0.50     # metres of band per U tile; t4: 0.25 (256 px) -> 0.50 (512 px, the same 0.98 mm / px): the
#                          45 mm longer collar and the deeper tabs need about 0.33 m of band (t3 0.22 m)
COLLAR_U_EDGE = 0.02     # U of the lifted lap edge top; the edge step face spans U 0 .. COLLAR_U_EDGE
COLLAR_WRAPS = 2
# t2 (2026-10-02, the user's tack photo): the collar no longer ends in a torn edge but in a flared, slit flap (tabs).
# U 0 .. COLLAR_U_FLAP is the tan flap (the tabs' visible length, from their edge at U ~0.03 to their root); above it
# the pale hide that carries the tack band. The collar lathe starts at U = COLLAR_U_FLAP at the flap-root ring.
COLLAR_U_FLAP = 0.18     # t3: 0.16 -> 0.24: the rolled tabs' U runs by arc length down from the root; t4: 0.18 of the
#                          0.5 m tile = 90 mm of arc for the buried root, the deeper tabs and their curled hems
# t3 (judge round 3): the flap-root ring and the top of the golden-tan zone (the lower collar and the flaps are golden
# tan, fading into the white hide about 0.5 tack diameters below the tack band)
# t4 (judge round 3 item 3, about 1 tack diameter more hide): X_ROOT 0.600 -> 0.555; X_GOLD is the TOP of the
# white-to-gold ramp (0.5 d below the band's lower edge, x 0.6159 with X_TACK 0.655), the ramp runs GOLD_RAMP (0.4 d)
# down to full gold
X_ROOT = 0.555 - D_SHIFT   # t6: design units (every collar x moves inward by D_SHIFT with the crown)
# t6 (judge t5 item 2, the root ledge): the gold ramp starts at least 15 mm below the skirt root X_SK everywhere (its
# low-frequency wave peaks GOLD_WAVE above X_GOLD), so the white runs onto the sheet; band to the ramp top 0.49-0.63 d
GOLD_WAVE = 0.0030         # t4/t5: 0.0043
X_GOLD_T6 = 0.6098 - D_SHIFT - 0.015 - GOLD_WAVE - 0.0001   # t6: X_SK - 18.1 mm (t5: 0.5945, 21.5 mm below the t5 root)
# t7 (judge r6 items 3-4): the tack band moved (build_taiko X_TACK 0.5835, rows 28.9 mm apart, tacks 41.5 mm design =
# 46 mm real): its lower edge sits at X_BAND_LO. The white-to-gold ramp now STARTS 0.12 d below that edge (t6: 0.56 d)
# and runs GOLD_RAMP = 2.0 d of arc down to full gold (t6: 0.4 d), mostly on the skirt sheet, like the photo's upper
# collar (a warm tint right under the band, full gold about 2.2 tack widths lower; on the lower collar the gold runs up
# to the tacks). The ramp line waves GOLD_WAVE at low frequency; the white breaks up in low-frequency mottled patches
# (make_taiko_textures collar), no vertical drip streaks.
TACK_D_T7 = 2 * 0.020767
X_BAND_LO = 0.5835 - 0.5 * 0.028894 - 0.5 * TACK_D_T7
X_GOLD = X_BAND_LO - 0.12 * TACK_D_T7
GOLD_WAVE = 0.0020
GOLD_RAMP = 2.0 * TACK_D_T7


def collar_u(x):
    """t4: the collar's U at axial position x (>= X_ROOT): arc length along the profile from the flap-root ring."""
    return COLLAR_U_FLAP + (body_arc(abs(x)) - body_arc(X_ROOT)) / COLLAR_TILE_U


COLLAR_U_GOLD = collar_u(X_GOLD)                 # top of the ramp
COLLAR_U_GOLD_FULL = COLLAR_U_GOLD - GOLD_RAMP / COLLAR_TILE_U   # t7: full gold below this (by arc, on the sheet)
# t5 (judge t4 item 1): the collar lathe ends at X_SK, where ONE continuous flared skirt (build_taiko.skirt) tucks
# under it; the skirt's U runs on from collar_u(X_SK) downward by arc length along its own centre line (X_ROOT stays
# the U datum only). Its rolled hem lip starts at U COLLAR_U_LIP_LO (lobe crests, the longest arc) .. COLLAR_U_LIP_HI
# (at the slits), measured on the t5 build (measure.json flap_tabs "lip_start_u_min_max"); the texture darkens the
# gold toward the lip over LIP_FADE (1 d) above COLLAR_U_LIP_HI.
X_SK = 0.6098 - D_SHIFT   # t6: design units; t5 0.606 (shifted); 3.8 mm higher, so the gold ramp can start 15 mm
#                   below the root (the skirt's 6 mm tuck still ends below the lower tack row's base, x 0.5246)
COLLAR_U_SK = collar_u(X_SK)
COLLAR_U_LIP_LO, COLLAR_U_LIP_HI = 0.107, 0.156   # t6: the t6 skirt (ears have the longest arc); t5: 0.100, 0.132
COLLAR_U_LIP_LO, COLLAR_U_LIP_HI = 0.060, 0.170   # t7: the traced skirt's roll starts (taiko_skirt; the build reports
#                                                   "lip_start_u_min_max"); the roll keeps the full gold, a touch darker
LIP_FADE = 0.020   # t6: 0.5 d (t5: 0.043, 1 d): the gold ramp now starts 15 mm below the root, so the full gold
#                    zone above the lip is shorter; with 1 d the darkening stops would overrun the full-gold stop

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

# --- t2 (2026-10-02): two more patches on the hide atlas's unused right-hand columns (U 0.80-1.0; heads U 0-0.5, lip
# strips 0.505-0.54 / 0.755-0.79, bachi 0.570-0.715). (U0, V0, U1, V1) in UV; V up (row 0 of the PNG is V = 1).
TACK_PATCH = (0.82, 0.03, 0.94, 0.15)    # lacquered-black tack domes (t3: metallic, BC = F0 0.012 linear, roughness 0.29, flat N)
FELT_PATCH = (0.82, 0.20, 0.98, 0.84)    # dark red wool felt (the stand's saddle liners)
# t7 (user: "also match the ring handle to the reference"): the ring hardware's black iron maps TACK_PATCH (the same
# lacquered black iron as the tacks); the chrysanthemum washer a new pale brass patch
BRASS_PATCH = (0.82, 0.86, 0.98, 0.98)
# t8 (judge r7 item 2: the plate, ring and boss rendered grey and matte on the tacks' patch, luminance 32-42 against the
# photo's 5-25): the ring hardware's own near-black iron patch in the free columns between the bachi patch and the -X
# lip strip (U 0.715-0.755)
HWIRON_PATCH = (0.722, 0.50, 0.748, 0.71)     # the plate's broad faces: near-black, low F0 (no grey sheen)
HWGLOSS_PATCH = (0.722, 0.74, 0.748, 0.95)    # the plate's bevel and walls, the rivets, the boss and the ring: glossier, so
#                                               the edges, domes and the rod carry the photo's thin bright highlights
