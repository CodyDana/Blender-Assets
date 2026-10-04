"""Kit 6, taiko set (SEPARATE from the pavilion): drum, stand and one drumstick mesh (placed twice), in Taiko.blend.

Reference: References/Dojo/dojo_drum_pavilion_ref.png (drum close-up panels, bottom right). Sizes: the prompt's
"about 1.2 m across" wins over the sheet; the sheet's proportions are measured (BUILD_NOTES.md, stage BUILD).

Pieces (each its own collection, mesh, UCX and FBX with LOD0-2; real-world metres):
  SM_DKP_Taiko_Drum   pivot at the drum centre; drum axis along local X; ring handles on +-Y
  SM_DKP_Taiko_Stand  pivot at the base centre on the ground; the drum axis runs along local X
  SM_DKP_Taiko_Stick  pivot at the grip end on the stick axis; the stick runs along local +X

Fix round f1 (2026-09-27): LOD0-2 on every piece (pipeline decimate_lods + make_lod_group, UCX_<base>_LOD0_NN);
tacks cut to 30 triangles each (110 per head, jittered, 12 % bigger, zig-zag +-16 mm); lathe UV seam moved to the
underside (-Z) and the wrap made a whole number of tiles; hide collar with its own strip texture, an irregular
torn and lifted edge and folds; rounded lip; rings hang flat against the bulge (1.3x thicker); stand darker with
end-grain faces, heavier sills, kusabi wedge blocks without top pegs, iron L-straps wrapping the rail ends with
round rivets; UCX covers the saddle shoulders; thicker flat-ended sticks leaning at the front-right end, solved
against the real meshes (BVH) with the feet grounded to 0.5 mm.

Fix round t1 (2026-10-02, user): the user overrode the f1/r2 "jittered zig-zag" tacks ("the dots on the side of the
taiko are not aligned correctly"; reference References/Dojo/taiko_tacks_ref_user.webp). Now two regular rows of
identical iron domes per head, as on a real nagado-daiko: TACKS_PER_ROW per row at a constant angular pitch (about
1.1 x the dome's visible diameter, nearly touching), the head-side row offset by exactly half a pitch so each tack
sits in the gap of the row below, a constant row spacing (about 0.86 x the visible diameter, the rows nest), no
random position, size or rotation jitter; 12-sided domes (36 triangles) that all map one dark, even patch of the
iron tile (the reference's tacks are uniform black; the old per-tack UV offsets gave a rusty / grey patchwork). Each tack is seated on the actual collar mesh (BVH ray along the radius)
and oriented normal to the profile. The collar folds no longer run under the band (taut hide there, as the
reference): fold1 moved down to x 0.652, the band rings carry no fold. The build now asserts the "Taiko" lock (the
lock this asset is held under; was "DojoTaiko").

Fix round t2 (2026-10-02, judge round 2 on the user's photo; the user asked whether the stand needs a round seat):
  tacks: smooth ball-like caps (two middle rings, the widest a smooth equator 0.45 H above the hide with a slight
  undercut below it, 18 sides, 90 triangles) on a glossy lacquered-black patch of the hide atlas (taiko_uv.TACK_PATCH:
  BC 0.012 linear, roughness 0.15, flat normal) instead of the pitted library iron;
  band centre X_TACK 0.703 -> 0.690 (more pale hide between the head edge and the band).
  collar: the torn edge is gone; the collar lathe now ends at the flap-root ring X_ROOT and continues as N_TABS
  flared, slit hide tabs (closed 2.5 mm shells, tan; the collar texture is pale above the flap, taiko_uv
  COLLAR_U_FLAP). The tab tips stay at x >= X_TAB_MIN, clear of the cradle beams' outer faces (x 0.58).
  stand: each saddle is lofted between two arcs, radius body_r(0.46) + FELT_T on the beam's inner face and
  body_r(0.58) + FELT_T on its outer face (the seat follows the barrel's taper; one common shoulder height), and a
  3 mm dark red wool felt strip (70 % of the beam width, on the hide atlas's taiko_uv.FELT_PATCH) lines each saddle:
  drum, felt and wood touch with no air.

Fix round t3 (2026-10-02, judge round 3 on the user's photo References/Dojo/taiko_tacks_ref_user.webp):
  tacks: true domes, widest where they meet the hide (rings r/R, z/H = (1.00, 0), (0.93, 0.38), (0.72, 0.74),
  (0.40, 0.95), pole 1.0; a straight 2.5 mm skirt below, no undercut), H 18 mm = 0.42 x the 42.75 mm visible
  diameter; the patch black to the edge (metallic, BC = F0 0.012 linear, roughness 0.29; the Hide material's
  Specular Tint 0.5 damps the metal's grazing Fresnel as Unreal's F90 = 50 x F0 does) and no edge wear or dust on the
  tacks. The golden flap #906622 (rendered 201,157,118 at #8C5E22; #A27A3E rendered pale, 210,178,143), fully gold up
  to about 9 mm above the flap root, roughness 0.55 on the flap.
  Rows 37 -> 40 mm apart (0.935 d: the diagonal gap about equals the in-row gap). Band X_TACK 0.690 -> 0.678.
  collar: the flap root X_ROOT 0.622 -> 0.600; 28-32 tabs per head at a +-20 % jittered pitch, narrow V slits (0.8 mm
  at the root, 6 mm at the hem), each tab's lower edge rolled outward (flare 30-45 deg, curl radius 5-7 mm); the lower
  collar and the flaps golden tan, the head, the rim and the upper collar near white (make_taiko_textures t3); the lip
  roll sampled every 18 deg (was 45) so the rim reads as a roll.
  stand: the cradle beams 25 mm toward the drum's centre (x 0.435-0.555; seat and felt recut there), and with them the
  posts, sills, stop blocks, wedges, strap plates and rivets (the beam keeps its place in the post) and the rail ends
  (the same overhang); the post tops now clear the real drum mesh (tabs and tacks included) by 4 mm.

Fix round t4 (2026-10-03, user: "see how the reference's barrel is wider in the middle? Lets do the same"):
  body: the barrel profile traced from the user's photo with the camera's perspective removed
  (WorkFiles/dojo/build/props/taiko/t4/trace_ref_profile.py; taiko_uv.body_r): belly / collar line 1.057, head (lip
  outline) / belly 0.791. Our head and overall length are kept, so the belly grows 1.20 -> 1.351 m. More body rings
  (8 per half) for the rounder silhouette. Lacquer and collar U by arc length along the profile (taiko_uv.lac_u /
  collar_u; no stretch on the slope). The ring plates sit on the new belly radius; the drum's UCX is a 16-gon hull
  over 8 stations that follows the bulge (was one 16-gon prism). DRUM_Z 1.25 -> 1.30 so the cradle beams keep a
  13 cm section under the bigger barrel.
  tacks (judge r3 items 1-2): 76 per row (was 74), rows 35.5 mm apart (was 40); 18-sided domes with the t3 profile
  (was 24; --tack-sides 24 builds the comparison).
  collar (judge r3 item 3): about 1 d more hide: X_TACK 0.678 -> 0.655, X_ROOT 0.600 -> 0.555, tab tips 0.565 ->
  0.520; the cradle beams, saddles, felt, posts, sills, wedges, straps, rivets and the rail ends 45 mm toward the drum's
  middle (x 0.390-0.510); each saddle seat lofts through three arcs (the beam's faces and its middle) so it follows
  the bulged barrel along the beam.
  flaps (judge r3 item 5): a wavy flared skirt: each tab is a lobe that bellies out 3-6 mm between its slits, its hem
  dips 7-11 mm in the middle and rises to the corners, tilts and sits within +-0.15 d of the mean hem line; the flare
  twists across the tab and the corners (the slit edges) turn out up to 6 deg more; the hem rolls into a tight bead
  (radius 3.5-5 mm, 190-215 deg in the middle, 215-245 deg at the corners, the radius growing toward them: no straight
  tube hem); lobe widths 0.7-1.5 x the mean (the photo's lobes vary about 2x); V slits 0.8 mm at the root opening to
  12.8 mm (0.3 d) at the hem; 7 columns per tab (was 5).

Fix round t5 (2026-10-03, judge t4 item 1 on the user's photo): the flap is ONE continuous, flared, wavy skirt per
  head (skirt()), not separate tabs: the collar lathe ends at X_SK 0.606 (just below the lower tack row) where the skirt tucks under it, so the collar bellies out from right under the tacks as the photo's does; one sheet runs
  on to one continuous rolled hem lip (10.5 mm); 21-23 short V slits per head, irregularly spaced 120-215 mm, cut up
  from the hem only (tips at x 0.5615-0.5665, about 1 d), opening 11-15 mm at the hem and closing to nothing at the
  tip, with a 2-4 mm crease ridge up each side; between slits the hem sags into one broad lobe 9-13 mm deep, lifted
  25-31 mm (centre line; the lip 32-38 mm with the belly) off the wood at its crest, the flare starting 2 mm below X_SK (0.95 x at the slits) and bellying out 4-7 mm in its middle, the lip curling further up and outward at each slit. The
  collar texture darkens the gold toward the hem lip over 1 d and carries a few white streaks (make_taiko_textures t5).
  The drum's length stays 1.554 m (judge t4 item 2 is the user's decision).

Fix round t6 (2026-10-03, user: "see how the reference's barrel is wider in the middle? Lets do the same"; judge t5):
  barrel (item 1): crown half-length / belly 1.149 -> 1.014 (the photo's). The drum is built in DESIGN units and scaled
  uniformly by DRUM_S (taiko_uv.DRUM_SCALE 1.1075) at the end of drum(): the wood alone is D_SHIFT (75.4 mm) shorter per
  half (collar, tacks, skirt and lip keep their distances from the crown), body_r keeps the traced shape in normalised
  length, and its unit is the lip's true outline radius 0.547 (t4/t5: 0.534, which left the body 1.8 % narrow in the
  photo overlay). Real: length 1.554 m, belly 1.531 m, lip outline 1.212 m, tacks 47.3 mm. 81 tacks per row (item 4:
  pitch 1.089 / 1.062 d). Stand: cradle beams x 0.350-0.470, posts x 0.450, rails 0.650, the frame x 1.133 in y,
  DRUM_Z 1.394; stand pieces use body_R (real metres).
  skirt (item 2, skirt()): narrow / wide lobes alternating (110-130 / 230-260 mm), 21 slits; three ears per head at the
  photo camera's silhouette (lip 45-60 mm off the wood, hems raised SK_EAR_RISE), the rest close (lip 10-20 mm); the slits
  are pinched, lapped creases (one side rides 4.8 mm over the other, overlap 3-6 mm, parting 4-8 mm at the hem); the lip
  curls 90-120 deg in the lobes and 250-300 deg within 25 mm of each slit; a 5 mm tangential root tuck (no ledge) and the
  gold ramp >= 15 mm below the root (taiko_uv.X_GOLD). Gold colour (item 3): make_taiko_textures GOLD_HSV, tuned on renders.
  UV1: Smart UV retried down to 5 deg, lightmap pack as the last resort.

Fix round t7 (2026-10-03, judge r6 + user: "also match the ring handle to the reference"):
  skirt (item 1, a NEW METHOD; the parametric lobe generator missed twice): taiko_skirt.py builds each head's skirt from
  a TRACE of the user's photo (skirt_trace_t7.json: the hem column by column and the slits lobe by lobe, unprojected
  through the photo's fitted camera onto our collar; the photo's outline rows for the ears): open V slits (8-13 mm design
  at the lip, opening fast below the tip: slots), the hem rolled OUTWARD into a lip of 18 mm (upper head) / 13 mm (lower
  head) centre-line radius (design), the close lobes lying on the wood (item 2: lip underside median 3.3 / 4.2 mm real)
  and bellying 4-8 mm between their slits, two ears per head plus the shoulder lobe in front of / behind each ear fitted
  to the photo's outline (skirt_ears_t7.json, t7/fit_ears_t7.py). The t6 skirt() is kept for the record, unused.
  The photo camera (t7/photo_cam.py) now looks at the +Y handle (the ring hangs left, as in the photo) and faces lathe
  angle 4.88 deg (the hardware); t4-t6 render_t* gave Blender's lens shift in the wrong units (16 px high).
  tacks (item 4): 46 mm real (t6 47.3), rows 32 mm apart axially (t6 39.3), the collar stepped 6 mm (real) steeper under
  the band (row rings at the two tack rows, +-2.7 mm design): the photo-camera row spacing / tack width target 0.85
  (t7/tack_sim_t7.py); the band's top edge kept (X_TACK 0.5795 -> 0.5835). Item 7 (triangles): 16-sided domes, 2 rings
  (80 triangles, t6 162), smooth normals; the skirt about 14 k (t6 about 40 k).
  ring handles (user): the photo's hardware traced (ring_trace_t7.json, t7/trace_ring_t7.py): a black iron four-point
  plate with stepped notches between the lobes and a domed rivet near each point, a 12-petal pale brass chrysanthemum
  washer, a domed pivot boss and a glossy black ring hanging from it; the plate and washer follow the bulged barrel in
  both directions; the ring hangs in a vertical plane resting on the washer rim (0.8 mm). Black iron = the tacks'
  patch of the hide atlas, brass = taiko_uv.BRASS_PATCH (M_DJ_Iron is no longer on the drum).
  felt (item 5): the felt top follows the barrel's own facets (the lathe's 2.5 deg columns and its rings at the cradle
  faces and middle) 0.1 mm outside them; the wood seat 3.2 mm outside the barrel (SADDLE_GAP), 30 arc segments.
  stand: the cradle beams, posts and rails 20 mm toward the drum's middle (x 0.330-0.450; the traced hems over the cradle
  reach x 0.454 real).

Writes: Assets/Dojo/Taiko.blend (collections Taiko_Drum, Taiko_Stand, Taiko_Stick, Taiko_Layout),
Exports/DojoKit/Props/taiko/SM_DKP_Taiko_*.fbx (through Scripts/pipeline), and in
WorkFiles/dojo/build/props/taiko/: layout_taiko.json, measure.json, qa_report.json, export_report.json.

Run: blender -b --factory-startup --python Scripts/dojo/props/taiko/build_taiko.py -- [--no-export]
     [--tack-sides N] [--blend PATH]   (t4: a comparison build; use with --no-export)
"""
import json
import math
import random
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "Scripts"))
sys.path.insert(0, str(HERE))
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402
from pipeline.lock import assert_owner  # noqa: E402
from pipeline.helpers import decimate_lods, make_lod_group  # noqa: E402
import taiko_uv as UVL  # noqa: E402
import taiko_skirt as SKT  # noqa: E402  (t7: the traced skirt)
sys.path.insert(0, str(ROOT / "Scripts" / "dojo" / "materials"))
import dojo_materials as djm  # noqa: E402  (the shared dojo material library, r2)

EXPORT_DIR = ROOT / "Exports" / "DojoKit" / "Props" / "taiko"
TEX = EXPORT_DIR / "Textures"
WORK = ROOT / "WorkFiles" / "dojo" / "build" / "props" / "taiko"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BLEND = Path(ARGS[ARGS.index("--blend") + 1]) if "--blend" in ARGS else ROOT / "Assets" / "Dojo" / "Taiko.blend"
assert "--blend" not in ARGS or "--no-export" in ARGS, "--blend is for --no-export comparison builds"

# --------------------------------------------------------------------------- dimensions (metres)
# Sheet (front elevation, 112.8 px/m from the 1.8 m silhouette): drum 1.04 m tall, 1.34-1.45 m long, bottom 0.57 m
# above the plinth. Prompt: "about 1.2 m across" -> scale the sheet by 1.2 / 1.04 = 1.154.
R_BELLY = UVL.body_r(0.0)   # t4: 0.6754 (the traced profile, taiko_uv.body_r); f1-t3: 0.600 (the prompt's 1.2 m)
R_BODY_END = 0.548       # (f1-t3 parabola: body radius at |x| = 0.70; retired in t4)
X_BODY = 0.70
X_COLLAR = UVL.X_COLLAR  # mean x of the torn collar edge
COLLAR_T = 0.0045        # hide thickness over the body
# t6 (judge t5 item 1, the user's "wider in the middle"): the drum's x / radius constants below are DESIGN units; the
# finished drum mesh is scaled uniformly by DRUM_S (taiko_uv.DRUM_SCALE, 1.1075) in drum(). Every collar / lip / tack /
# skirt x moved inward by D_SHIFT (the wood alone is D_SHIFT (0.0754 m) shorter per half); the stand works in real metres.
DRUM_S = UVL.DRUM_SCALE
D_SHIFT = UVL.D_SHIFT
LIP_XC, LIP_RC, LIP_RHO = 0.758 - D_SHIFT, 0.528, 0.019   # rolled lip: circle centre (x, r) and radius in the profile plane
X_FACE = 0.771 - D_SHIFT  # the flat head face (recessed about 6 mm inside the lip's crown at x = 0.6858)
R_FACE = 0.505           # the flat face's edge radius (then the lip rolls out to its crown)
# t1 (user, 2026-10-02): two regular rows per head (reference taiko_tacks_ref_user.webp, measured at the front
# centre: pitch 1.09-1.13 x the tack diameter, row spacing about 0.8 x, tack diameter 0.039 x the tack ring diameter)
TACKS_PER_ROW = 81       # t6: 76 -> 81 (judge t5 item 4: in-row pitch 1.07-1.09 d; the judge's 78 assumed the old
#                          collar radii, but the normalised profile on the lip's true outline radius (taiko_uv.BODY_RC)
#                          puts the band 3.5 % wider: 81 gives 1.089 / 1.062 d, the judge's 78-at-the-old-radii
#                          1.094 / 1.068); t4: 74 -> 76 (judge r3 item 1); pitch 46.6-47.8 mm at the two row radii
N_TACKS = 2 * TACKS_PER_ROW   # per head
X_TACK = 0.655 - D_SHIFT + 0.0039   # t7: + 3.9 mm (the head-side row's top edge stays where t6 had it: judge r6
#                          "band top 235 in both"); band centre (t6: design units, shifted) along the axis (the two rows sit +-TACK_ROW_DX / 2 about it); t2: 0.703 -> 0.690;
#                          t3: -> 0.678 (more pale hide above the band, the judge's 1.4-1.6 d; see BUILD_NOTES);
#                          t4: -> 0.655 (judge r3 item 3: 1.94 d of pale hide above the band, 2.4 d from the band to
#                          the lowest tab hem; 0.662 gave 1.76 / 2.57)
TACK_ROW_DX = 0.032 / DRUM_S   # t7 (judge r6 item 4): 32 mm real (t6 39.3; the judge's 36.3 left the photo-camera
#                          row spacing at 0.92 of the tack width in t7/tack_sim_t7.py, the photo 0.85); t6: axial row spacing; t3: 0.037 -> 0.040; t4: -> 0.0355 (judge r3 item 2: the rows nest,
#                          0.83 x the visible diameter; 0.0365 left the front-view outlines overlapping 0.087 d, < 0.1)
TACK_ROW_OFF = 0.5 * 0.006 / DRUM_S   # t7: the collar steps 6 mm (real) more between the rows: the body-side row's
#                          ring sits +2.7 mm (design), the head-side row's -2.7 mm off the profile (radial step 19.4 mm real)
TACK_R, TACK_H = 0.023 / DRUM_S, 0.018 * (0.023 / DRUM_S) / 0.021375   # t7: 46 mm real (t6 47.3, judge r6 item 4)
TACK_R_T6, TACK_H_T6 = 0.021375, 0.018   # t3: the dome's radius where it meets the hide (visible diameter 42.75 mm) and its
#                          height above the hide (0.42 x the visible diameter)
TACK_SIDES = int(ARGS[ARGS.index("--tack-sides") + 1]) if "--tack-sides" in ARGS else 16   # t7 (item 7): 16 sides, 2
#                          rings, 80 triangles (a 12-sided 3-ring dome, 84, showed its 12-gon outline in the 0.6 m macro)
#                          t2: 12 -> 18; t3: 24 (216 tris); t4: back to 18 (162 tris) with the t3 profile (item 6)
TACK_PROF = ((0.70, 0.75), (1.00, 0.0))   # t7: two rings on the t3 dome (item 7), smooth normals
TACK_PROF_T3 = ((0.40, 0.95), (0.72, 0.74), (0.93, 0.38), (1.00, 0.0))   # t3: (r / TACK_R, z / TACK_H) below the pole:
#                          a true dome, widest where it meets the hide (t2: a ball-like cap with an undercut equator)
TACK_BASE_R = 0.90       # t7: the sunk base ring (2.5 mm below the hide) tucked in to 0.90 R: the rows 32 mm apart put
#                          diagonal neighbours' full-radius skirts into each other UNDER the hide (1402 triangle pairs on
#                          the first t7 build; the domes above the hide clear by >= 1 mm); t3-t6: 1.00, a straight skirt
TACK_UV = (0.5 * (UVL.TACK_PATCH[0] + UVL.TACK_PATCH[2]), 0.5 * (UVL.TACK_PATCH[1] + UVL.TACK_PATCH[3]))
# t2: every tack maps the hide atlas's even, glossy lacquered-black patch (M_DKP_Taiko_Hide), each in its own small
# cell of an 18-column grid at 1/10 scale (TACK_UV_TILE): the patch is uniform, so they all look the same, and their
# UVs do not overlap (all 296 on one spot made qa_check's UV overlap test build ~2e8 triangle pairs and run out of
# memory)
TACK_UV_TILE = 20.0
TACK_UV_CELL = (0.0034, 0.0042)
# t2 collar flap (the user's photo): the collar lathe ends at the flap-root ring X_ROOT; below it N_TABS flared hide
# tabs with slits between them run toward the belly (tips clear of the cradle beams' outer faces at x 0.58)
X_ROOT = UVL.X_ROOT      # t3: 0.622 -> 0.600; t4: -> 0.555 (taiko_uv; the collar texture's gold zone is placed from it)
N_TABS = (28, 32)        # t3: tabs per head (random in this range), pitch jittered +-20 % (t2: 40, regular)
X_TAB_TIP = 0.520        # t3: 0.565, the rolled hem's lowest point; t4: the MEAN hem line, each tab's hem varies
HEM_VAR = 0.0064         #     +-HEM_VAR (0.15 d) about it (judge r3 item 5) and stays at x >= X_TAB_MIN
TAB_BURY = 0.012         # the tab root runs this far under the collar surface
TAB_T = 0.0025           # tab thickness (closed shell)
TAB_FLAT = 0.010         # t3: the tabs lie flat on the barrel this far below the root, then bend out
TAB_ALPHA = (26.0, 38.0)     # t3: flare angle from the barrel surface (deg, 30-45); t4: plus a twist across the tab and
#                              up to 6 deg more at the corners (the slit edges turn out)
TAB_RHO = (0.0035, 0.005)    # t3: radius of the rolled hem (5-7 mm); t4: a tighter bead (the photo's hem reads as a
#                              rounded bead, the t3 / first t4 roll as an open tray lip), x (1 + 0.25 ac^2) at the corners
TAB_ROLL = (190.0, 215.0)    # t4: the bead's curl in the tab's middle (deg past the flare angle) ...
TAB_ROLL_CORNER = (215.0, 245.0)   # t4: ... rolling further at the corners (t3: one 170-200 deg tube on every column)
SLIT_TOP, SLIT_TIP = 0.0008, 0.0128  # t3: 0.8 / 6 mm; t4: V slits open to 0.3 d at the hem (judge r3 item 5)
# t5 (judge t4 item 1): ONE continuous flared skirt per head (the t2-t4 tab constants above are retired). The collar
# lathe ends at X_SK; the skirt tucks under it there and runs on as one sheet to a continuous rolled hem lip; short V
# slits are cut up from the hem only (see skirt()).
X_SK = UVL.X_SK          # t6: 0.5344 design (t5: 0.606): the skirt emerges from under the collar lathe here
SK_BURY = 0.005          # t6 (judge t5 item 2, the root ledge): a 5 mm tangential tuck (t5: 12 mm rising 2.4 mm, a hard
SK_TUCK_IN = 0.0006      #     line): the buried edge's outer surface 0.6 mm under the collar's, the emergence ring's
SK_PROUD = 0.0002        #     0.2 mm over it (t5 0.4), so the collar runs on into the sheet; the top edge stays below
#                              the lower tack row's base (x 0.5246)
SK_T = 0.003             # sheet thickness
SK_BEND_A = 0.002        # the flare starts this far below the emergence ring
SK_BEND_P = 1.3          # n(a) = n0 + H t^p: tangent to the collar at the top, steepening a little toward the hem
SK_HEM_X_MIN = 0.5145 - D_SHIFT   # t6: the lowest hem point (outer surface), t5's 0.5145 shifted (band to hem 2.37 d)
# t6 (judge t5 item 2): narrow lobes of 110-130 mm alternate with wide ones of 230-260 mm, 21 slits per head; three
# lobes per head stand out as ears at the photo camera's silhouette (the two lobes either side of slit 0 at -Z, the
# right edge of the standing view, and the wide lobe centred on +Z, the left edge); the rest lie close
SK_N_LOBES = 21
SK_LOBE_NARROW, SK_LOBE_WIDE = (0.110, 0.130), (0.230, 0.260)
SK_SLIT_LEN = (0.045, 0.070)   # t6: slit length along the sheet, tip to the hem lip (t5: 38-48 mm)
SK_LAP = (0.003, 0.006)        # t6: pinched creases, not cut V notches: below the tip the two edges butt, then lap, one
SK_LAP_LIFT = SK_T + 0.0018    #     OVER the other by SK_LAP (the overlap peaks at 0.6 of the way down), the over side
SK_LAP_FLAT = 0.008            #     riding out SK_LAP_LIFT (4.8 mm) within SK_LAP_FLAT of its edge, fading out over
SK_LAP_RAMP = 0.012            #     SK_LAP_RAMP; toward the hem the edges part again and the curled lip tubes
SK_SLIT_W = (0.004, 0.008)     #     ("pockets") sit SK_SLIT_W apart at the hem (t5: a cut V 11-15 mm wide)
SK_NEAR = 0.012                # t6: within this of a slit both sides keep the slit's own flare (H, hem, tip), so they lap cleanly
SK_RIDGE_H = (0.0012, 0.0025)  # crease ridge each side of the slit, outside the lap (t5: 2-4 mm at 6.5 mm)
SK_RIDGE_D, SK_RIDGE_S = 0.009, 0.0025   # ridge centre / gaussian width, measured from the slit's centre line
SK_SAG = (0.006, 0.010)   # hem lobe depth between slits
SK_LIFT = (0.0062, 0.0122)     # t6: centre-line lift at the crests of the close lobes (lip 10-20 mm off the wood; t5 25-31)
SK_LIFT_EAR = (0.041, 0.0495)  # t6: the ears (lip 45-60 mm off the wood)
SK_EAR_RISE = {1: 0.012, -1: 0.028}   # t6 (per head, +X / -X): an ear's hem sits this much higher (toward the root): it stands out steeply from high up,
#                          as the photo's silhouette ears (theirs peak about 25-35 px nearer the heads than a full-length
#                          flare's lip)
SK_LIFT_SLIT = 0.95      # ... x the neighbours' mean at the slits
SK_BULGE = (0.003, 0.006)   # each lobe bellies out between its slits (a cross-wise wave), growing down the flare
SK_RHO = 0.00375         # rolled lip: centre-line radius (outer diameter 2 rho + SK_T = 10.5 mm, 0.25 d)
SK_ROLL = (90.0, 120.0)        # t6: the lip's curl in the lobe middle (deg past the flare angle; t5 200-215: a bead) ...
SK_ROLL_SLIT = (250.0, 300.0)  # ... rolled into a tube only within SK_ROLL_ZONE of each slit
SK_ROLL_ZONE = 0.025
SK_NF, SK_NR = 5, 6      # rows in the flare / round the lip
SK_V_INSET = 0.005       # the skirt's V runs 0.005 .. 1.995 (not 0 .. 2): LOD decimation at the -Z seam slit nudged
#                          V 0.002 past the tile range (qa uv0_tile_range on LOD1/2); 0.25 % texture scale, the
#                          tuck under the collar hides the 5 mm offset
DRUM_Z = 1.394           # drum centre above the stand base; t6: 1.30 -> 1.394 (the 1.53 m barrel: the cradle beams
#                          keep t4's 13.5 cm section under the saddle at the inner face x 0.350); t4: 1.25 -> 1.30 (the bigger barrel; the cradle beams
#                          keep a 13 cm section under the saddle arc)
SIDES = 144              # r2: 96 -> 144 columns, so the torn collar edge can tear in narrow notches
RING_R, RING_T = 0.0673, 0.0080  # t7: the photo's ring (ring_trace_t7.json: outer 151 mm; the tube reads 16 mm design);
#                                  f1-t6: 0.074 / 0.0124

POST_X, POST_Y, POST_W = 0.430, 0.544, 0.18    # t7: x 0.450 -> 0.430 (with the beams); t6: x 0.490 -> 0.450 (with the beams), y 0.48 -> 0.544 (the frame x
#                                                1.133 in y, judge t5 item 1); post centres (+-), section (f1: 0.16 -> 0.18, heavier); t3: x 0.56 ->
#                                                0.535, with the cradle beams; t4: -> 0.490 (45 mm, with them again)
SILL_W, SILL_H, SILL_Y = 0.22, 0.18, 0.816     # t6: SILL_Y 0.72 -> 0.816; foot sills along Y (f1: 0.18 x 0.15 -> 0.22 x 0.18)
RAIL_W, RAIL_X = 0.13, 0.630                   # t7: 0.650 -> 0.630 (the same overhang); t6: 0.690 -> 0.650 (the same overhang past the moved posts); long rails along X, protruding past the posts (t3: 0.76 -> 0.735;
#                                                t4: -> 0.690, the same overhang past the moved posts)
RAIL_LO, RAIL_HI = (0.19, 0.34), (0.47, 0.62)
CRADLE_X0, CRADLE_X1 = 0.330, 0.450   # t7: 20 mm in (the traced skirt's hems over the cradle reach x 0.454 real); t6: 40 mm in (the skirt hem moved in with the shorter wood: real 0.4795); t3: 0.46-0.58 -> 0.435-0.555 (room for the flaps); t4: 45 mm more toward the
#                                       drum's middle (the 45 mm longer collar, judge r3 item 3)
X_TAB_MIN = (CRADLE_X1 + 0.0035) / DRUM_S   # t4: the lowest hem point clears the cradle beams' outer faces (t6: design
#                                            units, the beams are in real metres)
CRADLE_BOTTOM, CRADLE_FLAT_Y = 0.52, 0.453   # t6: the saddle arc's half-width 0.40 -> 0.453 (x 1.133 in y)
CRADLE_Y = 0.782                               # t6: 0.69 -> 0.782; outer end of the cradle beam's wedge block
FELT_T = 0.003           # t2: the saddle felt strip's thickness
FELT_W = 0.70            # t2: felt width as a fraction of the cradle beam's width
SADDLE_GAP = FELT_T + 0.0002   # t7: 3.2 mm (t2-t6 3.0: the seat's chords sagged it under 3 mm); the wood saddle sits
#                                one felt thickness outside the barrel (drum-felt-wood, no air)
FELT_LIFT = 0.0001       # t7 (judge r6 item 5): the felt top 0.1 mm outside the barrel's own facets
RAIL_IRON_T = 0.006                            # r2: rail-end iron wrap thickness

STICK_L, STICK_R_GRIP, STICK_R_TIP = UVL.STICK_L, 0.040, 0.046   # r3: 13 % taper toward the grip (judge: 10-15 %)
STICK_EDGE = 0.008       # (f1/r2 flat-end round-over; r3 ends are domes, see STICK_DOME)
STICK_DOME = (0.62, 2.4)  # r3: dome height / end radius, superellipse exponent (a full round dome, soft shoulder)
RAIL_Y_OUT = (POST_W - RAIL_W) / 2   # r3: rails lap flush on the posts' outer faces (the sheet's joint close-up)
PLATE_T = 0.004                      # r3: flat iron strap plate thickness

# --------------------------------------------------------------------------- materials

# r2 (2026-09-28): the shared dojo library for timber, end grain and iron (M_DJ_*, UVs in library tile units);
# the three taiko-only surfaces (lacquer, hide, collar) are built on the library's own node graph (make_material:
# the DJ_Wear_v1 vertex-colour weathering, the same Unreal recipe M_DJ_Lib_Opaque) with the taiko's own maps.
LAC, HIDE, COLLAR, TIM, TIMEND, STK, IRN = (
    "M_DKP_Taiko_Lacquer", "M_DKP_Taiko_Hide", "M_DKP_Taiko_HideCollar", "M_DJ_TimberDark",
    "M_DJ_TimberDarkEnd", "M_DJ_TimberAged", "M_DJ_Iron")
# name: (texture set, params)
MATERIALS = {
    LAC: ("Lacquer", {"kind": "UNIQUE hero lacquer on the library graph (M_DJ_Lib_Opaque, UseWear on, TileM 2,2)",
                      "finish": "satin (roughness ~0.5), no clear coat"}),
    HIDE: ("Hide", {"kind": "UNIQUE on the library graph (UseWear on)"}),
    COLLAR: ("Collar", {"kind": "UNIQUE strip on the library graph (UseWear on)"}),
    TIM: ("LIBRARY TimberDark", {"kind": "shared library: MI_DJ_TimberDark"}),
    TIMEND: ("LIBRARY TimberDarkEnd", {"kind": "shared library: MI_DJ_TimberDarkEnd"}),
    IRN: ("LIBRARY Iron", {"kind": "shared library: MI_DJ_Iron"}),
}
TILE = {TIM: djm.set_info("TimberDark")["tile_m"][0], TIMEND: djm.set_info("TimberDarkEnd")["tile_m"][0],
        IRN: djm.set_info("Iron")["tile_m"][0], STK: djm.set_info("TimberAged")["tile_m"][0]}
OWN = {LAC: "Lacquer", HIDE: "Hide", COLLAR: "Collar"}


def build_material(name):
    if name.startswith("M_DJ_"):
        return djm.make_material(name, uv_map="UV0")
    # a taiko-only surface on the library graph: register it with the library's 2 m Lacquer tile (the wear mask
    # scale), build the library node tree, then point its three maps at the taiko's own set
    djm.MATERIALS[name] = dict(set="Lacquer", kind="opaque", wear=True, normal_strength=1.0)
    mat = djm.make_material(name, rebuild=True, uv_map="UV0")
    for n in mat.node_tree.nodes:
        if n.type == "TEX_IMAGE" and n.image and n.image.name.startswith("T_DJ_Lacquer_"):
            sfx = n.image.name.split("_")[-1].split(".")[0]
            img = bpy.data.images.load(str(TEX / f"T_DKP_Taiko_{OWN[name]}_{sfx}.png"), check_existing=True)
            img.colorspace_settings.name = "sRGB" if sfx == "BC" else "Non-Color"
            n.image = img
    mat["dj_set"] = "Lacquer"          # wear-mask tile only; the maps are T_DKP_Taiko_<set>
    mat["taiko_set"] = OWN[name]
    if name == HIDE:
        # t3 fix (judge round 3: tacks black to the edge, no rim ring brighter than 60): the only metallic texels of
        # the hide atlas are the tack patch (F0 0.012). Blender's metal Fresnel rises to white at grazing angles, so
        # the domes' steep skirts mirrored the white hide as a grey ring; Unreal damps a low-F0 metal's grazing
        # reflection (F90 = saturate(50 x F0) = 0.6). Specular Tint (the F82 tint of metals) 0.5 gives Blender the
        # same damping; it touches only metallic texels, so the hide and the felt are unchanged.
        bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Specular Tint"].default_value = (0.5, 0.5, 0.5, 1.0)
        mat["tack_f82_tint"] = 0.5
    return mat


def build_material_f1(name):
    """f1 material builder (retired in r2, kept for the record)."""
    tex, _p = MATERIALS[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")

    def img(suffix, noncolor):
        node = nt.nodes.new("ShaderNodeTexImage")
        image = bpy.data.images.load(str(TEX / f"T_DKP_Taiko_{tex}_{suffix}.png"), check_existing=True)
        if noncolor:
            image.colorspace_settings.name = "Non-Color"
        node.image = image
        return node
    bc, orm, nrm = img("BC", False), img("ORM", True), img("N", True)
    nt.links.new(bc.outputs["Color"], bsdf.inputs["Base Color"])
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
    return mat


# --------------------------------------------------------------------------- geometry builder

class Part:
    """Collects closed sub-meshes (verts, faces, per-face loop UVs, per-face materials, smooth flags) for one SM_."""

    def __init__(self, name):
        self.name = name
        self.chunks = []
        self.ucx = []

    def add(self, verts, faces, uvs, mats, smooth=False, M=None):
        if isinstance(mats, str):
            mats = [mats] * len(faces)
        if M is not None:
            verts = [tuple(M @ Vector(v)) for v in verts]
        self.chunks.append((verts, faces, uvs, mats, smooth))
        return self

    def hull(self, points):
        self.ucx.append(points)
        return self

    def scale(self, k):
        """t6: scale every chunk vertex and hull point uniformly about the origin (the drum's design -> real size)."""
        self.chunks = [([(k * x, k * y, k * z) for x, y, z in verts], faces, uvs, mats, smooth)
                       for verts, faces, uvs, mats, smooth in self.chunks]
        self.ucx = [[(k * x, k * y, k * z) for x, y, z in pts] for pts in self.ucx]
        return self

    def build(self, coll):
        mats = []
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UV0")
        for verts, faces, uvs, fmats, smooth in self.chunks:
            vs = [bm.verts.new(v) for v in verts]
            for f_i, (f_idx, fu, m) in enumerate(zip(faces, uvs, fmats)):
                if m not in mats:
                    mats.append(m)
                f = bm.faces.new([vs[i] for i in f_idx])
                f.material_index = mats.index(m)
                f.smooth = smooth if isinstance(smooth, bool) else smooth[f_i]   # t7: per-face flags allowed
                for loop, uv in zip(f.loops, fu):
                    loop[uvl].uv = uv
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in mats:
            mesh.materials.append(bpy.data.materials[m])
        obj = bpy.data.objects.new(self.name, mesh)
        coll.objects.link(obj)
        add_uv1(obj)
        for i, pts in enumerate(self.ucx):
            hm = bpy.data.meshes.new(f"UCX_{self.name}_{i:02d}")
            hb = bmesh.new()
            hv = [hb.verts.new(p) for p in pts]
            bmesh.ops.convex_hull(hb, input=hv)
            loose = [v for v in hb.verts if not v.link_faces]
            if loose:
                bmesh.ops.delete(hb, geom=loose, context="VERTS")
            bmesh.ops.recalc_face_normals(hb, faces=hb.faces[:])
            hb.to_mesh(hm)
            hb.free()
            h = bpy.data.objects.new(hm.name, hm)
            coll.objects.link(h)
            h.parent = obj
            h.hide_render = True
            h.display_type = "WIRE"
        return obj


UV1_SMART = ("SM_DKP_Taiko_Drum",)   # t3: these pieces get a Smart UV Project lightmap (see uv1_smart)


def uv1_smart(obj, angle=45.0):
    """t3: UV1 by Smart UV Project (angle-based charts, packed inside 0-1 with a margin). The t3 drum (77k triangles,
    ~45k quads) made Blender's per-face lightmap pack overlap (7720 triangle pairs) and spill past 0-1."""
    me = obj.data
    if "UV1" not in me.uv_layers:
        me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = me.uv_layers.find("UV1")
    vl = bpy.context.view_layer
    prev = vl.objects.active
    vl.objects.active = obj
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(angle), island_margin=0.002, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
    vl.objects.active = prev
    me.uv_layers.active_index = 0


def add_uv1(obj):
    """UV1 lightmap channel (Fab rule): Blender's lightmap pack, never overlapping, inside 0-1."""
    me = obj.data
    if obj.name in UV1_SMART:
        # t6: retry with tighter charts until UV1 has no overlap (the t6 skirt's lapped slits and curled tubes made the
        # 45 deg charts overlap on LOD0, as t3's decimated LODs did)
        for ang in (45.0, 30.0, 20.0, 12.0, 8.0, 5.0):
            uv1_smart(obj, ang)
            ov = [c for c in qa_check([obj], require_uv1=True, require_ucx=False)["checks"]
                  if c["name"] == "uv1_no_overlap" and not c["passed"]]
            print("UV1 smart", obj.name, ang, "overlap" if ov else "clean")
            if not ov:
                break
        if ov:                           # last resort: Blender's per-face lightmap pack (never overlaps)
            me.uv_layers.active_index = me.uv_layers.find("UV1")
            with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj],
                                           selected_editable_objects=[obj]):
                bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                         PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.3)
            me.uv_layers.active_index = 0
            print("UV1 lightmap pack", obj.name)
        return
    me.uv_layers.new(name="UV1")
    me.uv_layers.active_index = 1
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj],
                                   selected_editable_objects=[obj]):
        bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                 PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.3)
    me.uv_layers.active_index = 0


_JIT = [0]


def cbox(x0, x1, y0, y1, z0, z1, mat, grain="x", c=0.008, uvoff=(0.0, 0.0), end_mat=None, rough=0.0, seed=0):
    """A chamfered box (worn timber edge) as (verts, faces, uvs, mats). Planar tiling UV per face: U along the grain
    axis when it lies in the face plane, else along the face's longer side. end_mat: the material of the two faces
    across the grain (end grain, f1), mapped with its own tile. rough: per-corner random offset (m), which keeps each
    corner's three chamfer vertices together, for the rough kusabi wedges. A tiny unique growth per box keeps abutting
    boxes from sharing coincident vertices (the armory rule)."""
    _JIT[0] += 1
    g = 0.0002 + (_JIT[0] % 211) * 3e-6
    x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
    lo, hi = (x0, y0, z0), (x1, y1, z1)
    c = min(c, (x1 - x0) / 3, (y1 - y0) / 3, (z1 - z0) / 3)
    rng = random.Random(seed or _JIT[0])
    verts, idx = [], {}
    for sx in (0, 1):
        for sy in (0, 1):
            for sz in (0, 1):
                p = [hi[0] if sx else lo[0], hi[1] if sy else lo[1], hi[2] if sz else lo[2]]
                off = [rng.uniform(-rough, rough) for _ in range(3)]
                inset = [(-c if s else c) for s in (sx, sy, sz)]
                for ax in range(3):
                    q = [p[o] + off[o] for o in range(3)]
                    for o in range(3):
                        if o != ax:
                            q[o] += inset[o]
                    idx[(sx, sy, sz, ax)] = len(verts)
                    verts.append(tuple(q))
    faces, fax = [], []
    for ax in range(3):   # main faces
        o1, o2 = [a for a in range(3) if a != ax]
        for s in (0, 1):
            ring = []
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                k = [0, 0, 0]
                k[ax], k[o1], k[o2] = s, a, b
                ring.append(idx[(k[0], k[1], k[2], ax)])
            faces.append(tuple(ring))
            fax.append(ax)
    for ax in range(3):   # edge chamfers along axis ax
        o1, o2 = [a for a in range(3) if a != ax]
        for a in (0, 1):
            for b in (0, 1):
                k0 = [0, 0, 0]
                k0[o1], k0[o2] = a, b
                k1 = list(k0)
                k1[ax] = 1
                faces.append((idx[(*k0, o1)], idx[(*k1, o1)], idx[(*k1, o2)], idx[(*k0, o2)]))
                fax.append(-1)
    for sx in (0, 1):     # corner triangles
        for sy in (0, 1):
            for sz in (0, 1):
                faces.append((idx[(sx, sy, sz, 0)], idx[(sx, sy, sz, 1)], idx[(sx, sy, sz, 2)]))
                fax.append(-1)
    gi = "xyz".index(grain)
    ext = [x1 - x0, y1 - y0, z1 - z0]
    uvs, mats = [], []
    for f, a in zip(faces, fax):
        pts = [Vector(verts[i]) for i in f]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        nax = max(range(3), key=lambda q: abs(n[q]))
        plane = [q for q in range(3) if q != nax]
        is_end = end_mat is not None and a == gi
        m = end_mat if is_end else mat
        tile = TILE[m]
        ua = gi if gi in plane else max(plane, key=lambda q: ext[q])
        va = [q for q in plane if q != ua][0]
        off = (uvoff[0] * 1.7 % 1.0, uvoff[1] * 2.3 % 1.0) if is_end else uvoff
        uvs.append(wrap_uv([(p[ua] / tile + off[0], p[va] / tile + off[1]) for p in pts]))
        mats.append(m)
    return verts, faces, uvs, mats


def pbox(x0, x1, y0, y1, z0, z1, mat=None, uvoff=(0.0, 0.0)):
    """A plain 6-quad box (iron straps: no chamfer, 12 triangles)."""
    mat = mat or IRN
    _JIT[0] += 1
    g = 0.0001 + (_JIT[0] % 97) * 2e-6
    x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
    verts = [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tile = TILE[mat]
    uvs = []
    for f in faces:
        pts = [Vector(verts[i]) for i in f]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        nax = max(range(3), key=lambda q: abs(n[q]))
        a, b = [q for q in range(3) if q != nax]
        uvs.append(wrap_uv([(p[a] / tile + uvoff[0], p[b] / tile + uvoff[1]) for p in pts]))
    return verts, faces, uvs, [mat] * len(faces)


def wrap_uv(face_uv):
    """Shift one face's UVs by whole tiles so its minimum lies in 0..1 (tiling texture: the look is unchanged)."""
    du = math.floor(min(u for u, _v in face_uv))
    dv = math.floor(min(v for _u, v in face_uv))
    return [(u - du, v - dv) for u, v in face_uv]


def lathe(rings, sides, phase, seg_mat, uv_fn, ragged=None):
    """Surface of revolution about X. rings = [(x, r)], r == 0 gives a pole. ragged(k, i) -> (dx, dr) for ring k at
    column i. The angle of column i is 2 pi i / sides + phase, so column 0 (the UV seam) sits at `phase`.
    uv_fn(seg, k, col, pos) -> (u, v) for the corner of segment seg on ring k at the unwrapped column col (0..sides)
    and vertex position pos."""
    verts, vid = [], []
    for k, (x, r) in enumerate(rings):
        if r == 0:
            verts.append((x, 0.0, 0.0))
            vid.append([len(verts) - 1] * sides)
            continue
        row = []
        for i in range(sides):
            th = 2 * math.pi * i / sides + phase
            dx, dr = ragged(k, i) if ragged else (0.0, 0.0)
            verts.append((x + dx, (r + dr) * math.cos(th), (r + dr) * math.sin(th)))
            row.append(len(verts) - 1)
        vid.append(row)
    faces, uvs, mats = [], [], []
    for k in range(len(rings) - 1):
        a, b = vid[k], vid[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            corners = [(k, a[i], i), (k, a[j], i + 1), (k + 1, b[j], i + 1), (k + 1, b[i], i)]
            if rings[k][1] == 0:
                corners = [corners[0], corners[2], corners[3]]
            elif rings[k + 1][1] == 0:
                corners = [corners[0], corners[1], corners[3]]
            faces.append(tuple(c[1] for c in corners))
            uvs.append([uv_fn(k, kk, col, verts[vi]) for kk, vi, col in corners])
            mats.append(seg_mat[k])
    return verts, faces, uvs, mats


def lathe_z(profile, sides, mat, tile=2.0, uoff=(0.37, 0.61)):
    """Small surface of revolution about local Z (tacks, rivets, the boss). profile = [(r, z), ...]; open at the
    bottom when the last ring is not a pole (it sits sunk into the surface below)."""
    verts, rings = [], []
    for (r, z) in profile:
        if r == 0:
            verts.append((0.0, 0.0, z))
            rings.append([len(verts) - 1] * sides)
        else:
            rings.append([len(verts) + i for i in range(sides)])
            for i in range(sides):
                a = 2 * math.pi * (i + 0.5) / sides
                verts.append((r * math.cos(a), r * math.sin(a), z))
    faces, uvs = [], []
    for k in range(len(profile) - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            pu = lambda vi: (verts[vi][0] / tile + uoff[0], verts[vi][1] / tile + uoff[1] + verts[vi][2] / tile)  # noqa
            if profile[k][0] == 0:
                faces.append((a[i], b[j], b[i]))
            elif profile[k + 1][0] == 0:
                faces.append((a[i], a[j], b[i]))
            else:
                faces.append((a[i], a[j], b[j], b[i]))
            uvs.append([pu(v) for v in faces[-1]])
    return verts, faces, uvs, [mat] * len(faces)


def torus(R, r, nu, nv, mat, tile=2.0):
    """Torus about local Z (ring in the XY plane). UV: U along the ring, V around the tube."""
    verts = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        for j in range(nv):
            b = 2 * math.pi * j / nv
            rr = R + r * math.cos(b)
            verts.append((rr * math.cos(a), rr * math.sin(a), r * math.sin(b)))
    faces, uvs = [], []
    for i in range(nu):
        for j in range(nv):
            i2, j2 = (i + 1) % nu, (j + 1) % nv
            faces.append((i * nv + j, i2 * nv + j, i2 * nv + j2, i * nv + j2))
            uvs.append([(R * 2 * math.pi * ii / nu / tile, r * 2 * math.pi * jj / nv / tile)
                        for ii, jj in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))])
    return verts, faces, uvs, [mat] * len(faces)


def frame(origin, t, d, n):
    """Matrix with local X = t, Y = d, Z = n at origin (all unit, orthogonal)."""
    M = Matrix.Identity(4)
    for row in range(3):
        M[row][0], M[row][1], M[row][2], M[row][3] = t[row], d[row], n[row], origin[row]
    return M


# Round domed heads (f1: the joint close-up's round-headed nails and rivets; 6 sides, 18 triangles, open base)
def dome(r, h, sides=6):
    return lathe_z([(0.0, h), (0.70 * r, 0.72 * h), (r, -0.0015)], sides, IRN)


# --------------------------------------------------------------------------- the drum

def body_r(x):
    """t4: the photo's traced barrel profile (taiko_uv.body_r); f1-t3: R_BELLY - 0.052 (x / 0.70)^2."""
    return UVL.body_r(x)


def body_R(x):
    """t6: the REAL barrel radius at the real axial position x (the design profile scaled by DRUM_S): the stand, the
    saddles, the felt and the measurements work in real metres."""
    return DRUM_S * UVL.body_r(x / DRUM_S)


def harmonics(seed, kmin, kmax, amp, power=0.8):
    """A random periodic function of the angle: sum of harmonics kmin..kmax with 1/k^power amplitudes, scaled to
    peak `amp` over the SIDES columns. Returns a list of SIDES values."""
    rng = random.Random(seed)
    terms = [(k, rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 1.0) / k ** power) for k in range(kmin, kmax + 1)]
    vals = [sum(a * math.sin(k * 2 * math.pi * i / SIDES + ph) for k, ph, a in terms) for i in range(SIDES)]
    m = max(abs(v) for v in vals)
    return [amp * v / m for v in vals]


# per head (s = +1 / -1): torn edge offset along the axis, lap-edge lift, collar folds
RAG = {}
for _s in (1, -1):
    _rng = random.Random(77 + _s)
    base = harmonics(100 + _s, 2, 60, 0.012)
    jit = [_rng.uniform(-0.003, 0.003) for _ in range(SIDES)]
    # r2 (judges: torn, irregular): 9 torn-back notches (V tears 2-4 columns wide, 8-14 mm deep) and 4 small
    # proud tabs per head
    for _ in range(9):
        c0 = _rng.randrange(SIDES)
        depth = _rng.uniform(0.008, 0.014)
        half = _rng.choice((1, 1, 2))
        for d_ in range(-half, half + 1):
            jit[(c0 + d_) % SIDES] += depth * (1.0 - abs(d_) / (half + 1))
    for _ in range(4):
        c0 = _rng.randrange(SIDES)
        jit[c0 % SIDES] -= _rng.uniform(0.004, 0.007)
    lift_h = harmonics(200 + _s, 3, 40, 0.0020)
    RAG[_s] = {"dx": [b + j for b, j in zip(base, jit)],
               # r2 (judges: "slightly lifted"): the lap edge stands 1.5-5.5 mm proud, curling up in places
               "lift": [0.0035 + v + (0.0015 if j > 0.006 else 0.0) for v, j in zip(lift_h, jit)],
               "fold": harmonics(300 + _s, 9, 44, 1.0, 0.5),
               "fold_edge": harmonics(400 + _s, 14, 70, 1.0, 0.3)}   # r2: small folds radiating from the edge


def drum():
    p = Part("SM_DKP_Taiko_Drum")
    phase = -math.pi / 2          # f1: UV seam at the underside (-Z), hidden by the cradle
    # ---- profile: (x, r, kind) from the -X pole to the +X pole
    lip_a = [0, 18, 36, 54, 72, 90, 108, 126]   # t3: every 18 deg (t2: 0, 45, 90, 130): the rim reads as a roll
    head = [(X_SK, None, "rag_lo"), (X_SK, None, "rag_hi"),   # t5: skirt root (t2-t4: X_ROOT, the flap root, + fold1 16 mm above)
            (X_TACK - 0.040, "c", "band0"), (X_TACK - 0.5 * TACK_ROW_DX, "c", "row0"),
            (X_TACK + 0.5 * TACK_ROW_DX, "c", "row1"), (X_TACK + 0.040, "c", "band2")]   # t7: a ring under each tack row
    #                                                         (t1-t6: band1 at X_TACK), stepped +-TACK_ROW_OFF
    for a in lip_a:
        ar = math.radians(a)
        head.append((LIP_XC + LIP_RHO * math.sin(ar), LIP_RC + LIP_RHO * math.cos(ar), f"lip{a}"))
    head += [(X_FACE, R_FACE, "face"), (X_FACE + 0.0012, 0.28, "face"), (X_FACE + 0.0020, 0.0, "face")]
    # t6: design units; 0.3089 / 0.4148 are the cradle faces (real 0.350 / 0.470), 0.3619 the felt's middle (real
    # 0.410: the seat lofts through these three); 0.4726 under the skirt (t4/t5: 0.08 .. 0.548, faces 0.39 / 0.51)
    body_x = [0.0, 0.07, 0.14, 0.21, 0.265, CRADLE_X0 / DRUM_S, 0.5 * (CRADLE_X0 + CRADLE_X1) / DRUM_S,
              CRADLE_X1 / DRUM_S, 0.548 - D_SHIFT]
    assert body_x[-1] < X_SK - 0.02
    prof = []
    for x, r, kd in reversed(head):
        prof.append((-x, r, kd, -1))
    for x in reversed(body_x[1:]):
        prof.append((-x, body_r(x), "body", -1))
    for x in body_x:
        prof.append((x, body_r(x), "body", 1))
    for x, r, kd in head:
        prof.append((x, r, kd, 1))
    P = []
    for x, r, kd, s in prof:
        if r is None or r == "c":
            r = body_r(abs(x)) + (0 if kd == "rag_lo" else COLLAR_T)
            r += {"row0": TACK_ROW_OFF, "row1": -TACK_ROW_OFF}.get(kd, 0.0)   # t7: the steeper collar under the band
        P.append((x, r, kd, s))
    kinds = [q[2] for q in P]
    # lip arc length from lip0 per side (for the lip strip U)
    arc = {}
    for s in (1, -1):
        acc, prev = 0.0, None
        for k, (x, r, kd, ss) in (list(enumerate(P)) if s > 0 else list(enumerate(P))[::-1]):
            if ss != s or not (kd.startswith("lip") or kd == "face"):
                continue
            if prev is not None:
                acc += math.hypot(x - prev[0], r - prev[1])
            arc[k] = acc
            prev = (x, r)
            if kd == "face" and r == R_FACE:
                break

    def seg_material(k):
        a, b = kinds[k], kinds[k + 1]
        if a == "body" and b == "body":
            return LAC
        if {a, b} <= {"body", "rag_lo"} and "rag_lo" in (a, b):
            return LAC
        hide_k = lambda q: q.startswith("lip") or q == "face"  # noqa: E731
        if hide_k(a) and hide_k(b):
            return HIDE
        return COLLAR   # includes the short run from the last fold ring onto the lip's first ring
    seg_mat = [seg_material(k) for k in range(len(P) - 1)]
    rings = [(x, r) for x, r, _k, _s in P]

    def ragged(k, i):
        x, r, kd, s = P[k]
        R = RAG[s]
        if kd in ("rag_lo", "rag_hi"):
            return 0.0, 0.0     # t2: the flap-root ring is regular (t5: the skirt tucks under it)
        if kd in ("rag_lo_r2", "rag_hi_r2"):
            xe = X_COLLAR + R["dx"][i]
            lift = R["lift"][i]
            r_here = body_r(xe) + (0.6 * lift if kd == "rag_lo" else COLLAR_T + lift)
            return s * (xe - X_COLLAR), r_here - r
        if kd == "edge_in":     # r2: a ring 10 mm inside the torn edge, following it, half lifted, with small folds
            xe = X_COLLAR + R["dx"][i] + 0.010
            r_here = body_r(xe) + COLLAR_T + 0.45 * R["lift"][i] + 0.0018 * R["fold_edge"][i]
            return s * (xe - (X_COLLAR + 0.010)), r_here - r
        if kd == "fold1":
            return 0.0, 0.0     # t3: no ripple (t2: +-1.0 mm): its folds cut through the tab roots in a zig-zag
        return 0.0, 0.0

    def uv_fn(seg, k, col, pos):
        m = seg_mat[seg]
        x = pos[0]
        s = 1 if x > 0 else -1
        if m == LAC:      # t4: U by arc length along the bulged profile (taiko_uv.lac_u)
            return (UVL.lac_u(P[k][0]), UVL.LAC_WRAPS * col / SIDES)
        if m == COLLAR:   # t2: U = COLLAR_U_FLAP at the flap root, growing toward the head; the root step face below
            if kinds[k] == "rag_lo":
                u = UVL.COLLAR_U_SK - 0.009   # t5 (t2-t4: COLLAR_U_FLAP at X_ROOT)
            else:         # t4: by arc length (taiko_uv.collar_u)
                u = UVL.collar_u(P[k][0])
            return (u, UVL.COLLAR_WRAPS * col / SIDES)
        # hide: the flat face as a planar disc per head, the lip roll as a U strip
        if kinds[seg] == "face" and kinds[seg + 1] == "face":
            cu, cv = UVL.HEAD_CENTRE[s]
            return (s * pos[1] / UVL.HIDE_TILE + cu, pos[2] / UVL.HIDE_TILE + cv)
        return (UVL.LIP_U0[s] + arc.get(k, 0.0) / UVL.HIDE_TILE, UVL.HIDE_WRAPS * col / SIDES)

    v, f, uv, m = lathe(rings, SIDES, phase, seg_mat, uv_fn, ragged)
    p.add(v, f, uv, m, smooth=True)

    # ---- tacks (t1, user): two regular rows of identical iron domes per head, the head-side row offset half a pitch;
    # each tack seated on the collar mesh itself (ray along the radius), oriented normal to the profile
    bvh = BVHTree.FromPolygons([Vector(q) for q in v], f)
    tack_meta = []
    prof_xr = sorted({(round(abs(x), 6), round(r, 6)) for x, r, kd, _s in P if kd in ("fold1", "band0", "row0", "row1",
                                                                                       "band2", "lip0")})
    dome_prof = ([(0.0, TACK_H)] + [(fr * TACK_R, fz * TACK_H) for fr, fz in TACK_PROF]
                 + [(TACK_BASE_R * TACK_R, -0.0025)])     # t3: a straight skirt 2.5 mm into the hide
    for s in (-1, 1):
        for row in (0, 1):                        # 0 = body-side row, 1 = head-side row (offset half a pitch)
            xx = X_TACK + (row - 0.5) * TACK_ROW_DX
            # profile slope of the collar between the rings around xx (the lathe's own chord), for the tack normal
            # t7: each row sits ON a ring (row0 / row1): the mean of the chords either side
            sl_ = [(rb - ra) / (xb - xa) for (xa, ra), (xb, rb) in zip(prof_xr, prof_xr[1:])
                   if xa - 1e-6 <= xx <= xb + 1e-6]
            slope = sum(sl_) / len(sl_)
            for i in range(TACKS_PER_ROW):
                th = 2 * math.pi * (i + 0.5 * row) / TACKS_PER_ROW
                radial = Vector((0.0, math.cos(th), math.sin(th)))
                start = Vector((s * xx, 0.0, 0.0)) + radial * 0.8
                hit, _hn, _fi, _d = bvh.ray_cast(start, -radial, 0.5)
                assert hit is not None, ("tack seat ray missed", s, row, i)
                # profile normal: radial tilted toward the head by the collar slope (the surface narrows toward it)
                n = (radial - Vector((s * slope, 0.0, 0.0))).normalized()
                ax = Vector((1.0, 0.0, 0.0))
                t = (ax - n * ax.dot(n)).normalized()      # along the axis, in the surface (same spin for every tack)
                M = frame(hit, t, n.cross(t), n)
                k_ = len(tack_meta)
                cu_ = TACK_UV[0] + (k_ % 18 - 8.5) * TACK_UV_CELL[0]
                cv_ = TACK_UV[1] + (k_ // 18 - 8.0) * TACK_UV_CELL[1]
                tv, tf, tu, tm = lathe_z(dome_prof, TACK_SIDES, HIDE, tile=TACK_UV_TILE, uoff=(cu_, cv_))
                p.add(tv, tf, tu, tm, smooth=True, M=M)
                tack_meta.append((s, xx, th, TACK_R, row, tuple(hit), tuple(n)))

    # ---- t5: one continuous flared skirt per head below the collar, short V slits up from the hem (the user's photo)
    tab_meta = {}
    SKT.A_LOW_MAX = UVL.X_SK - X_TAB_MIN - 0.5 * SKT.SK_T - 0.001   # the cradle side: hems clear the beams' outer faces
    for s in (-1, 1):
        sv_, sf_, su_, info = SKT.mesh(s)      # t7: traced from the photo (t6: skirt(), retired, kept for the record)
        p.add(sv_, sf_, su_, [COLLAR] * len(sf_), smooth=True)
        info["u_min_max"] = [round(min(u for fu in su_ for u, _v in fu), 4), round(max(u for fu in su_ for u, _v in fu), 4)]
        tab_meta[s] = info

    # ---- ring handles (t7, the user: "also match the ring handle to the reference"; f1-t6: a grey square plate)
    ring_info = ring_handles(p)
    # collision (blocking prop, unwalkable). t4: one convex hull that follows the bulge: 16-gon rings at 8 stations;
    # each station's ring circumscribes every vertex between its two neighbouring stations (+2 mm), so the linear
    # hull between two stations covers everything in that span (t3: one 16-gon prism, r 0.66, over the whole length)
    x_end = LIP_XC + LIP_RHO + 0.004
    allv = [q for verts, _f, _u, _m, _s in p.chunks for q in verts]
    assert max(abs(q[0]) for q in allv) < x_end
    # (no station at x = 0: the ring handles make the +-0.40 rings as wide as the belly, so a middle ring would lie on
    # the hull's faces and leave sliver triangles; the +-0.40 rings already cover x -0.6 .. 0.6 between them)
    xs_ = (0.70 - D_SHIFT, 0.60 - D_SHIFT, 0.345)      # t6: design units (t4/t5: 0.70, 0.60, 0.40)
    stations = [-x_end, -xs_[0], -xs_[1], -xs_[2], xs_[2], xs_[1], xs_[0], x_end]
    pts, ucx_r = [], []
    for k, xs in enumerate(stations):
        lo, hi = stations[max(0, k - 1)], stations[min(len(stations) - 1, k + 1)]
        ucx_r.append(max(math.hypot(q[1], q[2]) for q in allv if lo - 1e-6 <= q[0] <= hi + 1e-6) + 0.002)
    # keep the station profile strictly convex (each ring at least 3 mm outside the chord of its neighbours): nearly
    # collinear rings leave sliver hull triangles whose normals are noise (the t4 coverage check failed on one);
    # growing a ring only adds coverage
    for _pass in range(4):
        for k in range(1, len(stations) - 1):
            t_ = (stations[k] - stations[k - 1]) / (stations[k + 1] - stations[k - 1])
            ucx_r[k] = max(ucx_r[k], ucx_r[k - 1] + (ucx_r[k + 1] - ucx_r[k - 1]) * t_ + 0.003)
    for xs, rmax in zip(stations, ucx_r):
        rc = rmax / math.cos(math.pi / 16)
        for i in range(16):
            a = 2 * math.pi * (i + 0.5) / 16
            pts.append((xs, rc * math.cos(a), rc * math.sin(a)))
    p.hull(pts)
    # t6 (judge t5 item 1): the finished drum, built in design units, scaled uniformly to the real size
    p.scale(DRUM_S)
    tack_meta = [(s_, DRUM_S * xx_, th_, DRUM_S * r_, row_, tuple(DRUM_S * c for c in hit_), n_)
                 for s_, xx_, th_, r_, row_, hit_, n_ in tack_meta]
    for k_ in (1, -1):
        ri = ring_info[k_]
        for key_ in ("ring_plane_y", "ring_centre_z", "ring_top_z"):
            ri[key_] = round(DRUM_S * ri[key_], 4)
    ucx_r = [round(DRUM_S * r_, 4) for r_ in ucx_r]
    p.meta = {"tacks": tack_meta, "rings": ring_info, "tabs": tab_meta, "design_scale": DRUM_S,
              "ucx": {"stations_x": [round(DRUM_S * s, 4) for s in stations], "inscribed_r": ucx_r,
                      "points": len(pts)}}
    return p


# --------------------------------------------------------------------------- t7 ring handles (the user's photo)
# t7/trace_ring_t7.py (ring_trace_t7.json): the photo's hardware unprojected through its fitted camera onto the barrel
# and laid flat about the plate centre (s round the drum toward +Z, t along +X; DESIGN units). The plate's polar outline,
# made 4-fold and mirror symmetric, reads as straight runs: a pointed lobe (tip 195 mm, flanks at about 45 deg to the
# shoulder at 150 / 52 mm), then a stepped notch (in to 121 / 56, up to 115 / 85) and a 45 deg run to the diagonal.
RING_TRACE = json.loads((HERE / "ring_trace_t7.json").read_text(encoding="utf-8"))
PLATE_OCT = ((0.195, 0.0), (0.150, 0.052), (0.121, 0.056), (0.116, 0.064), (0.115, 0.085), (0.1005, 0.1005))
PLATE_T, PLATE_SINK, PLATE_CH = 0.004, 0.0012, 0.0012   # plate top above the wood, sunk depth, top edge chamfer
RIVET_AT, RIVET_R, RIVET_H = 0.159, 0.0158, 0.0135      # traced: 159 mm out on each lobe axis, 32 mm round domes
WASHER_RO, WASHER_RI, WASHER_N, WASHER_T = 0.084, 0.072, 12, 0.003   # traced 172 mm across; 12 broad rounded petals
BOSS_R, BOSS_H = 0.032, 0.034                           # traced 64 mm domed pivot boss
RING_GAP = 0.0008                                       # the hanging ring rests this close on the washer / plate
H_PIVOT = PLATE_T + WASHER_T + RING_T + 0.00314         # the ring's top (centre line) passes through the boss here;
#                                                         set so the plate centre sits PHI 5.68 deg up (t7/photo_cam VIEW_TH)
IRONB_UV = (0.88, 0.09)                                 # black iron: taiko_uv.TACK_PATCH (the tacks' finish)
HW_X = 0.0083                                           # traced: the plate centre sits 8.3 mm (design) toward the +X head
RING_DT = -0.013                                        # traced: the ring hangs 13 mm (design) toward -X of the boss centre
#                                                         (its eye sits low in the boss; the photo's ring centre -25 mm, the
#                                                         boss -12 mm from the plate centre, both raised alike)
BRASS_UV = (0.90, 0.92)                                 # pale brass: taiko_uv.BRASS_PATCH


def plate_outline():
    """the traced four-point plate outline, CCW in (s, t), 40 points"""
    q0 = list(PLATE_OCT) + [(b, a) for a, b in reversed(PLATE_OCT[1:5])]
    out = []
    for k in range(4):
        c_, s_ = round(math.cos(k * math.pi / 2)), round(math.sin(k * math.pi / 2))
        out += [(a * c_ - b * s_, a * s_ + b * c_) for a, b in q0]
    return out


def _inset(poly, d):
    """CCW polygon offset inward by d (mitred)"""
    out, n = [], len(poly)
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = poly[i - 1], poly[i], poly[(i + 1) % n]
        l1, l2 = math.hypot(bx - ax, by - ay), math.hypot(cx - bx, cy - by)
        n1 = ((by - ay) / l1, -(bx - ax) / l1)
        n2 = ((cy - by) / l2, -(cx - bx) / l2)
        m = (n1[0] + n2[0], n1[1] + n2[1])
        lm = math.hypot(*m)
        m = (m[0] / lm, m[1] / lm)
        k = d / max(0.35, m[0] * n1[0] + m[1] * n1[1])
        out.append((bx - m[0] * k, by - m[1] * k))
    return out


def _inside(poly, x, y):
    c = False
    for i in range(len(poly)):
        (ax, ay), (bx, by) = poly[i - 1], poly[i]
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            c = not c
    return c


def washer_r(psi):
    return WASHER_RI + (WASHER_RO - WASHER_RI) * abs(math.cos(0.5 * WASHER_N * psi)) ** 0.4


def hw_surf(sg_y, phi):
    """(s, t, h) -> (point, normal) on the barrel (h along the surface normal) for the +Y (sg_y 1) / -Y handle, the
    plate centre phi above the equator; s runs toward +Z on both"""
    th_c = phi if sg_y > 0 else math.pi - phi
    sg = 1.0 if sg_y > 0 else -1.0

    def surf(s_, t_, h):
        t_ = t_ + HW_X
        r = body_r(t_)
        th = th_c + sg * s_ / r
        dr = (body_r(t_ + 1e-4) - body_r(t_ - 1e-4)) / 2e-4
        nrm = Vector((-dr, math.cos(th), math.sin(th))).normalized()
        return Vector((t_, r * math.cos(th), r * math.sin(th))) + nrm * h, nrm
    return surf


def _cap_mesh(rings, heights, surf, uv_c, uv_k, bottom_h, k_top=None):
    """a closed shell over the (s, t) plane: a centre vertex, then rings of points (each a list, all the same length,
    CCW) at their heights (a float, or a function of the point index), walls down to bottom_h, a bottom fan"""
    verts, uvv, faces = [], [], []

    def add(st, h):
        verts.append(tuple(surf(st[0], st[1], h)[0]))
        uvv.append((uv_c[0] + uv_k * st[0], uv_c[1] + uv_k * st[1]))
        return len(verts) - 1
    n = len(rings[-1])
    c = add((0.0, 0.0), heights[0](0) if callable(heights[0]) else heights[0])
    R = []
    for ring, h in zip(rings, heights[1:]):
        R.append([add(q, h(i) if callable(h) else h) for i, q in enumerate(ring)])
    R.append([add(q, bottom_h) for q in rings[-1]])
    cb = add((0.0, 0.0), bottom_h)
    smooth = []
    k_top = len(rings) if k_top is None else k_top
    for i in range(n):
        j = (i + 1) % n
        faces.append((c, R[0][i], R[0][j]))
        smooth.append(True)
        for a, (A, B) in enumerate(zip(R, R[1:])):
            faces.append((A[i], B[i], B[j], A[j]))
            smooth.append(a + 1 < k_top)          # the top smooth; the chamfer, walls (and bottom) flat: crisp edges
        faces.append((cb, R[-1][j], R[-1][i]))
        smooth.append(False)
    return verts, faces, [[uvv[k] for k in f] for f in faces], smooth


def ring_solve(R0):
    """t7: where the plate sits and where the ring hangs. The ring hangs under gravity in a vertical plane (y const)
    from the pivot in the boss (its top centre line H_PIVOT above the wood, on the plate's centre normal), and rests on
    the washer rim / plate with RING_GAP (the radial clearance of its tube over the hardware, the ring points inside the
    boss excluded); fixed point: phi = acos(y_plane / (R0 + H_PIVOT))."""
    outline = plate_outline()
    phi = math.radians(5.0)
    psi = [2 * math.pi * i / 144 for i in range(144)]

    def clearance(y_plane, phi):
        zc = y_plane * math.tan(phi) - RING_R
        worst, at = 1e9, None
        for a in psi:
            x, z = HW_X + RING_DT + RING_R * math.sin(a), zc + RING_R * math.cos(a)
            rho, th = math.hypot(y_plane, z), math.atan2(z, y_plane)
            s_, t_ = (th - phi) * body_r(x), x - HW_X
            if math.hypot(s_, t_) < BOSS_R + RING_T + 0.003:
                continue
            under = PLATE_T if _inside(outline, s_, t_) else 0.0
            if math.hypot(s_, t_) < washer_r(math.atan2(t_, s_)):
                under = PLATE_T + WASHER_T
            c = rho - body_r(x) - RING_T - under
            if c < worst:
                worst, at = c, (round(s_, 4), round(t_, 4), "washer" if under > PLATE_T else ("plate" if under else "barrel"))
        return worst, at
    for _ in range(12):
        lo, hi = R0, R0 + 0.06
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if clearance(mid, phi)[0] > RING_GAP:
                hi = mid
            else:
                lo = mid
        y_plane = hi
        phi = math.acos(y_plane / (R0 + H_PIVOT))
    return phi, y_plane, clearance(y_plane, phi)


def ring_handles(p):
    """t7: the photo's ring-handle hardware on both handles (+-Y), DESIGN units (the drum is scaled by DRUM_S after):
    the black iron four-point plate (traced outline, chamfered top edge, following the bulged barrel in s and t, its
    underside PLATE_SINK in the wood), a domed rivet near each point, the 16-petal pale brass washer (raised petals with
    the grooves between them), the domed pivot boss and the glossy black ring hanging from it. Black iron on the hide
    atlas's tack patch, brass on BRASS_PATCH."""
    R0 = body_r(HW_X)
    phi, y_plane, (clr, clr_at) = ring_solve(R0)
    outline = plate_outline()
    ins = _inset(outline, PLATE_CH)
    info = {}
    for sg_y in (1, -1):
        surf = hw_surf(sg_y, phi)
        # plate: centre, two interior rings, the chamfer's inner edge (top), the outline (chamfer bottom), walls, bottom
        pv, pf, pu, pu_s = _cap_mesh([[(0.55 * a, 0.55 * b) for a, b in ins], ins, outline],
                                     [PLATE_T, PLATE_T, PLATE_T, PLATE_T - PLATE_CH], surf, IRONB_UV, 0.25,
                                     -PLATE_SINK, k_top=2)
        p.add(pv, pf, pu, HIDE, smooth=pu_s)
        # rivets
        for s_, t_ in ((RIVET_AT, 0.0), (-RIVET_AT, 0.0), (0.0, RIVET_AT), (0.0, -RIVET_AT)):
            o, n = surf(s_, t_, PLATE_T - 0.0006)
            tx = (Vector((1.0, 0.0, 0.0)) - n * n.x).normalized()
            rv, rf, ru, rm = lathe_z([(0.0, RIVET_H), (0.55 * RIVET_R, 0.88 * RIVET_H), (0.88 * RIVET_R, 0.55 * RIVET_H),
                                      (RIVET_R, 0.12 * RIVET_H), (0.96 * RIVET_R, -0.0015)], 10, HIDE, tile=TACK_UV_TILE,
                                     uoff=IRONB_UV)
            p.add(rv, rf, ru, rm, smooth=True, M=frame(o, tx, n.cross(tx), n))
        # chrysanthemum washer: 16 rounded petals (6 points each), raised along each petal, grooved between them
        npt = 6 * WASHER_N
        psis = [2 * math.pi * i / npt for i in range(npt)]
        wo = [(washer_r(q) * math.cos(q), washer_r(q) * math.sin(q)) for q in psis]
        wi = _inset(wo, 0.0012)
        ridge = lambda i: PLATE_T + WASHER_T * (0.62 + 0.38 * abs(math.cos(0.5 * WASHER_N * psis[i])) ** 0.6)   # noqa: E731
        wv, wf, wu, wu_s = _cap_mesh([[(0.30 * a, 0.30 * b) for a, b in wo], [(0.72 * a, 0.72 * b) for a, b in wi], wo],
                                     [PLATE_T + WASHER_T + 0.0004, PLATE_T + WASHER_T, ridge,
                                      lambda i: PLATE_T + 0.0010 + 0.0006 * abs(math.cos(0.5 * WASHER_N * psis[i]))],
                                     surf, BRASS_UV, 0.5, PLATE_T - 0.0008, k_top=3)
        p.add(wv, wf, wu, HIDE, smooth=wu_s)
        # the domed pivot boss on the washer
        o, n = surf(0.0, 0.0, PLATE_T + WASHER_T - 0.0006)
        tx = (Vector((1.0, 0.0, 0.0)) - n * n.x).normalized()
        bv, bf, bu, bm = lathe_z([(0.0, BOSS_H), (0.55 * BOSS_R, 0.93 * BOSS_H), (0.85 * BOSS_R, 0.70 * BOSS_H),
                                  (BOSS_R, 0.36 * BOSS_H), (0.96 * BOSS_R, 0.0), (0.96 * BOSS_R, -0.0015)], 12, HIDE,
                                 tile=TACK_UV_TILE, uoff=IRONB_UV)
        p.add(bv, bf, bu, bm, smooth=True, M=frame(o, tx, n.cross(tx), n))
        # the ring: a vertical plane at y_plane, hanging from the pivot (its top on the boss axis, H_PIVOT up)
        zc = y_plane * math.tan(phi) - RING_R
        centre = Vector((HW_X + RING_DT, sg_y * y_plane, zc))
        gv, gf, gu, gm = torus(RING_R, RING_T, 24, 8, HIDE, tile=TACK_UV_TILE)
        gu = [[(u + IRONB_UV[0] - 0.012, v + IRONB_UV[1]) for u, v in fu] for fu in gu]
        p.add(gv, gf, gu, gm, smooth=True, M=frame(centre, Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, sg_y, 0))))
        info[sg_y] = {"phi_deg": round(math.degrees(phi), 3), "ring_plane_y": round(sg_y * y_plane, 5),
                      "ring_centre_z": round(zc, 5), "ring_top_z": round(zc + RING_R, 5)}
    info["design"] = {
        "plate_width_mm": round(2000 * PLATE_OCT[0][0], 1), "plate_outline_points": len(outline),
        "plate_top_above_wood_mm": 1000 * PLATE_T, "plate_sunk_mm": 1000 * PLATE_SINK,
        "rivets": "4 domes %.0f mm across, %.0f mm out on the lobe axes" % (2000 * RIVET_R, 1000 * RIVET_AT),
        "washer": "%d petals, %.0f mm across (petal roots %.0f mm)" % (WASHER_N, 2000 * WASHER_RO, 2000 * WASHER_RI),
        "boss_mm": [2000 * BOSS_R, 1000 * BOSS_H], "ring_outer_diameter_mm": round(2000 * (RING_R + RING_T), 1),
        "ring_tube_diameter_mm": round(2000 * RING_T, 1),
        "ring_rest_clearance_mm": round(1000 * clr, 3), "ring_rest_contact_s_t_on": clr_at,
        "pivot_height_above_wood_mm": round(1000 * H_PIVOT, 1),
        "photo_proportions": RING_TRACE["proportions_px"],
        "ours_plate_over_belly_d": round(2 * PLATE_OCT[0][0] / (2 * R0), 4),
        "ours_ring_od_over_plate_w": round((RING_R + RING_T) / PLATE_OCT[0][0], 4),
        "ours_washer_d_over_plate_w": round(WASHER_RO / PLATE_OCT[0][0], 4),
        "note": "design units (real = x DRUM_S)"}
    return info


def skirt(s, rng):
    """(retired in t7: taiko_skirt.py builds the skirt from the photo's trace) t6 (judge t5 item 2, the user's photo; DESIGN units, the drum is scaled by DRUM_S afterwards): ONE continuous
    flared hide skirt per head, a closed shell SK_T thick. It tucks SK_BURY under the collar lathe's end ring X_SK
    TANGENTIALLY (its outer surface rises from SK_TUCK_IN under the collar's to SK_PROUD over it: no ledge) and runs on
    as one sheet: flat at first, then a flare n(a) = n0 + H t^SK_BEND_P (a = distance below X_SK along the barrel,
    n = height above the barrel) to the hem, which rolls outward into one continuous lip (centre-line radius SK_RHO).
    SK_N_LOBES lobes per head, narrow (SK_LOBE_NARROW) and wide (SK_LOBE_WIDE) alternating, starting wide at slit 0
    on the lathe's -Z seam; the two lobes either side of slit 0 and the wide lobe centred on +Z are the ears (lifted
    SK_LIFT_EAR, the photo camera's silhouette ears), the rest lie close (SK_LIFT). The slits are pinched creases, not
    cut notches: each runs SK_SLIT_LEN along the sheet up from the hem lip; above its tip the sheet is one piece (the two
    sides share their vertices); below it the two edges butt, then lap: one side (random) rides out SK_LAP_LIFT over the
    other near its edge (fading over SK_LAP_RAMP into its lobe) and both edges run past the slit's centre line until
    they overlap by SK_LAP at the hem; in the lip rows the edges part by SK_LIP_GAP_SLIT so the curled tubes sit side
    by side. A low crease ridge (SK_RIDGE_H) runs up each side. Between two slits the hem sags into one broad lobe
    (SK_SAG), and the lip curls only SK_ROLL in the lobe (a soft turned edge) but SK_ROLL_SLIT within SK_ROLL_ZONE of a
    slit (the photo's little tubes, the "pockets"). Every column's parameters blend from the slit values at its edges to
    the lobe's own in the middle, so the shared columns agree and the skirt is one smooth sheet.
    COLLAR material: U = taiko_uv.COLLAR_U_SK minus the arc length below X_SK (by the centre line), V round the drum
    as the collar lathe's."""
    two_pi = 2 * math.pi
    r_ref = body_r(X_SK - 0.061)               # (t5: body_r(0.545), 61 mm below the t5 root)
    circ = two_pi * r_ref
    nS = SK_N_LOBES
    assert nS % 2 == 1, "odd: lobe 0 and lobe nS-1 (either side of slit 0) are both wide"
    for _try in range(2000):                   # alternating widths; the left ear's centre exactly on +Z
        widths = [rng.uniform(*(SK_LOBE_WIDE if k % 2 == 0 else SK_LOBE_NARROW)) for k in range(nS)]
        kk = circ / sum(widths)
        widths = [w_ * kk for w_ in widths]
        cum = [sum(widths[:k]) for k in range(nS)]
        cand = [k for k in range(2, nS - 2) if k % 2 == 0]
        j_ear = min(cand, key=lambda k: abs(cum[k] + 0.5 * widths[k] - 0.5 * circ))
        need = 0.5 * circ - 0.5 * widths[j_ear]
        fb, fa = need / sum(widths[:j_ear]), need / sum(widths[j_ear + 1:])
        widths = [w_ * (fb if k < j_ear else fa if k > j_ear else 1.0) for k, w_ in enumerate(widths)]
        ok = all((SK_LOBE_WIDE if k % 2 == 0 else SK_LOBE_NARROW)[0] - 0.002 <= w_ <=
                 (SK_LOBE_WIDE if k % 2 == 0 else SK_LOBE_NARROW)[1] + 0.002 for k, w_ in enumerate(widths))
        if ok:
            break
    else:
        raise RuntimeError("no lobe layout in range")
    gaps = widths
    ears = {0, nS - 1, j_ear}
    th0 = -0.5 * math.pi
    slit_th = [th0]
    for g in gaps[:-1]:
        slit_th.append(slit_th[-1] + g / r_ref)
    assert SK_HEM_X_MIN >= X_TAB_MIN, (SK_HEM_X_MIN, X_TAB_MIN)
    a_low_max = X_SK - SK_HEM_X_MIN - 0.5 * SK_T            # the hem's lowest point (outer surface) at SK_HEM_X_MIN
    lobe = [{"H": rng.uniform(*(SK_LIFT_EAR if k in ears else SK_LIFT)),
             "a_low": rng.uniform(a_low_max - 0.0035, a_low_max) - (SK_EAR_RISE[s] if k in ears else 0.0),
             "bulge": rng.uniform(*SK_BULGE), "roll": math.radians(rng.uniform(*SK_ROLL)), "ear": k in ears}
            for k in range(nS)]
    slit = []
    for k in range(nS):
        lo_l, lo_r = lobe[k - 1], lobe[k]                         # lobe k runs from slit k to slit k + 1
        sag = rng.uniform(*SK_SAG)
        slit.append({"H": SK_LIFT_SLIT * 0.5 * (lo_l["H"] + lo_r["H"]),
                     "a_low": 0.5 * (lo_l["a_low"] + lo_r["a_low"]) - sag, "sag": sag,
                     "roll": math.radians(rng.uniform(*SK_ROLL_SLIT)), "len": rng.uniform(*SK_SLIT_LEN),
                     "lap": rng.uniform(*SK_LAP), "over": rng.choice((-1, 1)),   # +1: lobe k (after the slit) on top
                     "w": rng.uniform(*SK_SLIT_W),
                     "ridge": rng.uniform(*SK_RIDGE_H)})
    rho_ph = rng.uniform(0, two_pi)
    n0 = COLLAR_T + SK_PROUD - 0.5 * SK_T                         # centre line at the emergence ring
    n_b = COLLAR_T - SK_TUCK_IN - 0.5 * SK_T                      # ... at the buried top edge
    B_TIP = 4                                                     # rows: buried edge, X_SK, 1/3 and 2/3 of the tip, the tip,
    NB = 5 + SK_NF + SK_NR                                        # SK_NF flare rows, SK_NR lip rows
    B_HEM = B_TIP + SK_NF                                         # the last flare row (the lip starts here)
    FADE = [0.0, 0.0, 0.0, 0.2, 0.5] + [1.0] * SK_NF + [0.7] * SK_NR   # the crease ridge fades out above the slit tips

    def profile(H, a_low, roll, a_tip, rho):
        a_e = a_low - 0.3 * rho
        for _ in range(10):                                       # the lip's lowest point (90 deg) lands on a_low
            al = math.atan(H * SK_BEND_P / (a_e - SK_BEND_A))
            a_e = a_low - rho * (1.0 - math.sin(al))
        al = math.atan(H * SK_BEND_P / (a_e - SK_BEND_A))

        def nn(a):
            t = max(0.0, (a - SK_BEND_A) / (a_e - SK_BEND_A))
            return n0 + H * t ** SK_BEND_P, math.atan(H * SK_BEND_P * t ** (SK_BEND_P - 1) / (a_e - SK_BEND_A))
        st = [(-SK_BURY, n_b, math.atan((n0 - n_b) / SK_BURY)), (0.0, n0, 0.0)]
        for a in [a_tip / 3.0, 2.0 * a_tip / 3.0, a_tip] + [a_tip + (a_e - a_tip) * j / SK_NF for j in range(1, SK_NF + 1)]:
            st.append((a,) + nn(a))
        ae, ne = st[-1][0], st[-1][1]
        ca, cn = ae - rho * math.sin(al), ne + rho * math.cos(al)  # the lip's centre (outward side)
        for j in range(1, SK_NR + 1):
            th = al + roll * j / SK_NR
            st.append((ca + rho * math.sin(th), cn - rho * math.cos(th), th))
        arc = [0.0]
        for q0, q1 in zip(st, st[1:]):
            arc.append(arc[-1] + math.hypot(q1[0] - q0[0], q1[1] - q0[1]))
        arc = [x_ - arc[1] for x_ in arc]                         # arc length from X_SK (negative when buried)
        return st, arc, math.degrees(al)

    def slit_length(st, arc, al_deg, rho):
        """along the sheet from the slit tip to the lip's lowest point (the hem)"""
        return arc[B_HEM] - arc[B_TIP] + rho * math.radians(max(0.0, 90.0 - al_deg))

    # each slit's tip: solved so the slit runs its SK_SLIT_LEN along the sheet
    for k, sp in enumerate(slit):
        rho_k = SK_RHO * (1.0 + 0.06 * math.sin(3 * slit_th[k] + rho_ph))
        lo_a, hi_a = 0.004, sp["a_low"] - 0.012
        for _ in range(40):
            mid = 0.5 * (lo_a + hi_a)
            st_, arc_, al_ = profile(sp["H"], sp["a_low"], sp["roll"], mid, rho_k)
            if slit_length(st_, arc_, al_, rho_k) > sp["len"]:
                lo_a = mid
            else:
                hi_a = mid
        sp["a_tip"] = 0.5 * (lo_a + hi_a)

    def lobe_offsets(W):
        near = [0.0, 0.003, 0.007, 0.012, 0.018, SK_ROLL_ZONE]    # t6: dense near the slits (the lap ramp, the roll zone)
        mid0, mid1 = SK_ROLL_ZONE, W - SK_ROLL_ZONE
        nm = max(1, math.ceil((mid1 - mid0) / 0.030))
        return near + [mid0 + (mid1 - mid0) * j / nm for j in range(1, nm)] + [W - q for q in reversed(near[1:])]

    def frac(b):
        """0 at the slit tip row, 1 at the hem (the last flare row and the lip rows)"""
        return min(1.0, max(0.0, (b - B_TIP) / SK_NF))

    def edge_off(k, b):
        """slit k's edge offset from its centre line at row b, per side (+ = the edge stands back, - = past the line):
        butting to 0.2 of the way down, lapping SK_LAP at 0.6, parting to SK_SLIT_W at the hem and round the lip"""
        f = frac(b)
        if b > B_HEM:
            return 0.5 * slit[k]["w"]
        if f <= 0.2:
            return 0.0004 * f / 0.2        # (0 at the tip; 0.8 mm apart at 0.2: the two edge walls never coincide)
        if f <= 0.6:
            return 0.0004 + (-0.5 * slit[k]["lap"] - 0.0004) * (f - 0.2) / 0.4
        return -0.5 * slit[k]["lap"] + (0.5 * slit[k]["w"] + 0.5 * slit[k]["lap"]) * (f - 0.6) / 0.4

    def lap_lift(k, side_sign, b, d):
        """the over side's outward lift near slit k (side_sign: +1 = lobe k's side, -1 = lobe k-1's), d = distance
        from the slit along the hem"""
        if slit[k]["over"] != side_sign or b <= B_TIP:
            return 0.0
        g = min(1.0, frac(b) / 0.2)
        t = min(1.0, max(0.0, d - SK_LAP_FLAT) / SK_LAP_RAMP)
        return SK_LAP_LIFT * g * (1.0 - t * t * (3.0 - 2.0 * t))

    # column parameters (a slit column takes its slit's values; a lobe column blends them with the lobe's)
    cols = {}
    lobe_cols = []
    for k in range(nS):
        k1 = (k + 1) % nS
        thL, thR = slit_th[k], (slit_th[k1] if k1 else th0 + two_pi)
        W = (thR - thL) * r_ref
        specs = []
        for j, off in enumerate(lobe_offsets(W)):
            cid = ("s", k) if j == 0 else ("i", k, j)
            specs.append((cid, off))
            if cid in cols:
                continue
            rho = SK_RHO * (1.0 + 0.06 * math.sin(3 * (thL + off / r_ref) + rho_ph))
            if j == 0:
                sp = slit[k]
                prm = (sp["H"], sp["a_low"], sp["roll"], sp["a_tip"], rho)
            else:
                u = 2.0 * off / W - 1.0
                wl, wr = 0.5 * (1 - u), 0.5 * (1 + u)
                m = 1.0 - abs(u) ** 2.2
                e = lambda key: slit[k][key] * wl + slit[k1][key] * wr   # noqa: E731
                d_ = min(off, W - off)
                near_k = k if off < 0.5 * W else k1
                tn = min(1.0, max(0.0, (d_ - SK_NEAR) / 0.020))
                fn = tn * tn * (3.0 - 2.0 * tn)                   # t6: 0 within SK_NEAR of the slit (its own flare)
                H_, al_ = (slit[near_k][key] + (e(key) + (lobe[k][key] - e(key)) * m - slit[near_k][key]) * fn
                           for key in ("H", "a_low"))
                atip_ = slit[near_k]["a_tip"] + (e("a_tip") - slit[near_k]["a_tip"]) * fn
                t_ = min(1.0, d_ / SK_ROLL_ZONE)
                sm = t_ * t_ * (3.0 - 2.0 * t_)
                roll_ = slit[near_k]["roll"] + (lobe[k]["roll"] - slit[near_k]["roll"]) * sm
                prm = (H_, al_, roll_, atip_, rho)
            st, arc, al = profile(*prm)
            ridge_k = k if off < 0.5 * W else k1
            dn_ = min(1.0, max(0.0, (min(off, W - off) - SK_NEAR) / 0.020))
            m_b = 0.0 if j == 0 else (1.0 - abs(2.0 * off / W - 1.0) ** 2.0) * dn_ * dn_ * (3.0 - 2.0 * dn_)
            cols[cid] = {"st": st, "arc": arc, "alpha": al, "prm": prm, "ridge_k": ridge_k, "bulge": lobe[k]["bulge"] * m_b,
                         "d": min(off, W - off), "u": 2.0 * off / W - 1.0}
        specs.append((("s", k1), W))                              # the closing slit column (its side L)
        lobe_cols.append({"k": k, "k1": k1, "thL": thL, "thR": thR, "W": W, "specs": specs})

    verts, idx, uvmap = [], {}, {}
    hem_n, lip_u, hem_x = {}, [], []
    lift_max = [0.0]

    def key_of(layer, b, cid, side):
        if cid[0] == "s":
            return (layer, b, cid, 0 if b <= B_TIP else side)
        return (layer, b, cid, 0)

    for L in lobe_cols:
        k, k1, thL, thR, W = L["k"], L["k1"], L["thL"], L["thR"], L["W"]
        for ci, (cid, off) in enumerate(L["specs"]):
            side = "R" if ci == 0 else ("L" if ci == len(L["specs"]) - 1 else 0)
            C = cols[cid]
            for layer in (0, 1):
                for b in range(NB):
                    a, nn_, th = C["st"][b]
                    o = (0.5 if layer == 0 else -0.5) * SK_T
                    a_, n_ = a - o * math.sin(th), nn_ + o * math.cos(th)
                    rs = slit[C["ridge_k"]]["ridge"]
                    n_ += rs * math.exp(-((C["d"] - SK_RIDGE_D) / SK_RIDGE_S) ** 2) * FADE[b]
                    n_ += C["bulge"] * min(1.0, max(0.0, a / C["st"][B_HEM][0]))   # the lobe's belly
                    lift = lap_lift(k, 1, b, off) + lap_lift(k1, -1, b, W - off)
                    n_ += lift
                    lift_max[0] = max(lift_max[0], lift)
                    x = X_SK - a_
                    r = body_r(x) + n_
                    dL = edge_off(k, b) / r
                    dR = edge_off(k1, b) / r
                    ang = thL + dL + (off / W) * ((thR - thL) - dL - dR)
                    key = key_of(layer, b, cid, side)
                    if key not in idx:
                        idx[key] = len(verts)
                        verts.append((s * x, r * math.cos(ang), r * math.sin(ang)))
                    uvmap[(key, k)] = (UVL.COLLAR_U_SK - C["arc"][b] / UVL.COLLAR_TILE_U + 0.01 * layer,
                                       SK_V_INSET + (UVL.COLLAR_WRAPS - 2 * SK_V_INSET) * (ang - th0) / two_pi)
                    hem_x.append(x)
                    if b > B_HEM - 1:
                        hem_n.setdefault(cid, []).append(n_)
            lip_u.append(UVL.COLLAR_U_SK - C["arc"][B_HEM] / UVL.COLLAR_TILE_U)

    faces, fuv = [], []

    def quad(keys, ctx):
        faces.append(tuple(idx[q] for q in keys))
        fuv.append([uvmap[(q, ctx)] for q in keys])

    for L in lobe_cols:
        k = L["k"]
        n_c = len(L["specs"])
        sides = ["R"] + [0] * (n_c - 2) + ["L"]
        o = lambda b, a: key_of(0, b, L["specs"][a][0], sides[a])   # noqa: E731
        i_ = lambda b, a: key_of(1, b, L["specs"][a][0], sides[a])  # noqa: E731
        for b in range(NB - 1):
            for a in range(n_c - 1):
                quad((o(b, a), o(b, a + 1), o(b + 1, a + 1), o(b + 1, a)), k)
                quad((i_(b, a), i_(b + 1, a), i_(b + 1, a + 1), i_(b, a + 1)), k)
        for b in range(B_TIP, NB - 1):                            # the two slit walls (below the slit tips only)
            quad((o(b, 0), o(b + 1, 0), i_(b + 1, 0), i_(b, 0)), k)
            quad((o(b, n_c - 1), i_(b, n_c - 1), i_(b + 1, n_c - 1), o(b + 1, n_c - 1)), k)
        for a in range(n_c - 1):                                  # the buried top edge and the lip's cut edge
            quad((o(0, a), i_(0, a), i_(0, a + 1), o(0, a + 1)), k)
            quad((o(NB - 1, a), o(NB - 1, a + 1), i_(NB - 1, a + 1), i_(NB - 1, a)), k)

    # ---- report (DESIGN units: real = x DRUM_S)
    crest = []
    for L in lobe_cols:
        cid = min((c for c, _o in L["specs"][1:-1]), key=lambda c: abs(cols[c]["u"]))
        hn = hem_n[cid]
        crest.append((min(hn), max(max(q[1] for q in cols[cid]["st"]), max(hn))))
    cr_close = [c for k, c in enumerate(crest) if k not in ears]
    cr_ear = [c for k, c in enumerate(crest) if k in ears]
    slit_len_axial = [sp["a_low"] - sp["a_tip"] for sp in slit]
    slit_len_surf = [slit_length(cols[("s", k)]["st"], cols[("s", k)]["arc"], cols[("s", k)]["alpha"], cols[("s", k)]["prm"][4])
                     for k in range(nS)]
    sags = [lobe[k]["a_low"] - 0.5 * (slit[k]["a_low"] + slit[(k + 1) % nS]["a_low"]) for k in range(nS)]
    roll_mid = [math.degrees(c["prm"][2]) for c in cols.values() if c["d"] >= SK_ROLL_ZONE - 1e-9]
    roll_near = [math.degrees(c["prm"][2]) for c in cols.values() if c["d"] <= 0.003 + 1e-9]
    mm = lambda v: [round(1000 * min(v), 1), round(1000 * max(v), 1)]   # noqa: E731
    narrow = [w_ for k, w_ in enumerate(gaps) if k % 2 == 1]
    wide = [w_ for k, w_ in enumerate(gaps) if k % 2 == 0]
    info = {"construction": "t6: one continuous skirt (closed shell), alternating narrow / wide lobes, pinched lapped "
                            "slits up from the hem, 3 ears at the photo camera's silhouette; DESIGN units (real = x "
                            "%.4f)" % DRUM_S,
            "slits": nS, "columns": len(cols), "rows": NB, "tris": 2 * len(faces),
            "lobe_width_narrow_mm_min_max": mm(narrow), "lobe_width_wide_mm_min_max": mm(wide),
            "slit_spacing_mm_min_max": mm(gaps),
            "ear_lobes": sorted(ears), "ear_centre_angle_deg": [round(math.degrees(
                (slit_th[k] + 0.5 * gaps[k] / r_ref) - th0), 1) for k in sorted(ears)],
            "slit_tip_x_m_min_max": [round(X_SK - max(sp["a_tip"] for sp in slit), 4),
                                     round(X_SK - min(sp["a_tip"] for sp in slit), 4)],
            "slit_length_axial_mm_min_max": mm(slit_len_axial),
            "slit_length_along_sheet_mm_min_max": mm(slit_len_surf),
            "slit_lap_overlap_mm_min_max": mm([sp["lap"] for sp in slit]),
            "slit_over_side_lift_mm": round(1000 * lift_max[0], 2),
            "slit_width_at_hem_and_lip_mm_min_max": mm([sp["w"] for sp in slit]),
            "slit_lap_peaks_at_fraction_of_slit": 0.6,
            "crease_ridge_mm_min_max": mm([sp["ridge"] for sp in slit]),
            "hem_lobe_sag_mm_min_max": mm(sags),
            "hem_lowest_x_m_min_max": [round(min(X_SK - c["prm"][1] for c in cols.values()), 4),
                                       round(max(X_SK - c["prm"][1] for c in cols.values()), 4)],
            "skirt_x_min_m": round(min(hem_x), 4),
            "crest_lip_gap_to_wood_close_lobes_mm_min_max": mm([c[0] for c in cr_close]),
            "crest_lip_gap_to_wood_ears_mm_min_max": mm([c[0] for c in cr_ear]),
            "crest_outer_height_above_wood_mm_min_max": mm([c[1] for c in crest]),
            "crest_centre_line_lift_close_mm_min_max": mm([lb["H"] for lb in lobe if not lb["ear"]]),
            "crest_centre_line_lift_ears_mm_min_max": mm([lb["H"] for lb in lobe if lb["ear"]]),
            "flare_angle_deg_min_max": [round(min(c["alpha"] for c in cols.values()), 1),
                                        round(max(c["alpha"] for c in cols.values()), 1)],
            "lip_outer_diameter_mm": round(1000 * (2 * SK_RHO + SK_T), 1),
            "lip_roll_deg_lobe_middles_min_max": [round(min(roll_mid), 1), round(max(roll_mid), 1)],
            "lip_roll_deg_within_3mm_of_slits_min_max": [round(min(roll_near), 1), round(max(roll_near), 1)],
            "lip_start_u_min_max": [round(min(lip_u), 4), round(max(lip_u), 4)],
            "root_tuck_mm": round(1000 * SK_BURY, 1),
            "u_range": [round(min(q[0] for q in uvmap.values()), 4), round(max(q[0] for q in uvmap.values()), 4)],
            "v_range": [round(min(q[1] for q in uvmap.values()), 4), round(max(q[1] for q in uvmap.values()), 4)]}
    return (verts, faces, fuv, [COLLAR] * len(faces)), info


def flap_tabs(s, rng):
    """(t2-t4 slit tabs, retired in t5: the judge's t4 item 1 wants one continuous skirt; kept for the record)
    t4: see the module docstring (the wavy hem: per-column hem depth, flare twist, curl and radius; V slits to 0.3 d).
    t3 (judge round 3 on the user's photo): 28-32 hide tabs per head below the collar, cut by narrow V slits, each
    tab's lower edge rolled outward. The tab boundaries sit at a +-20 % jittered pitch. Each tab is a closed shell
    TAB_T thick, built round a centre line in the (a, n) plane (a = distance below the root toward the belly, n =
    height above the barrel): buried TAB_BURY under the collar, flat on the barrel for TAB_FLAT (the slits are hairline
    here), one smooth bend to the flare angle alpha (30-45 deg) whose radius is sized so the hem's lowest point
    sits at X_TAB_TIP, then the hem rolls outward round a circle of radius rho (5-7 mm) through 170-200 deg; the
    columns near the slits roll a little further (curled corners). The slits open from SLIT_TOP to SLIT_TIP (6 mm)
    over the tab's length. COLLAR material: U = COLLAR_U_FLAP minus the arc length from the root (the golden-tan zone),
    V round the drum."""
    n_tabs = rng.randint(*N_TABS)
    wts = [rng.uniform(0.7, 1.5) for _ in range(n_tabs)]       # t4: 0.8-1.2 -> 0.7-1.5 (the photo's lobes vary ~2x)
    ph0 = rng.uniform(0, 2 * math.pi / n_tabs)
    bnd = [ph0]
    for w_ in wts:
        bnd.append(bnd[-1] + 2 * math.pi * w_ / sum(wts))
    na, n_roll = 7, 6                                             # t4: 7 columns (t3: 5) for the wavy hem
    out, tips, flares, slit_tip, widths, tips_tab, hem_rng, rolls = [], [], [], [], [], [], [], []
    for j in range(n_tabs):
        b0, b1 = bnd[j], bnd[j + 1]
        thc, half_a = 0.5 * (b0 + b1), 0.5 * (b1 - b0)
        alpha0 = math.radians(rng.uniform(*TAB_ALPHA))
        twist = math.radians(rng.uniform(-8.0, 8.0))              # t4: the flare twists across the tab
        rho0 = rng.uniform(*TAB_RHO)
        roll_mid = math.radians(rng.uniform(*TAB_ROLL))           # t4: little curl in the lobe's middle ...
        roll_cl = math.radians(rng.uniform(*TAB_ROLL_CORNER))     # ... rolled-up corners at the slits
        roll_cr = math.radians(rng.uniform(*TAB_ROLL_CORNER))
        bulge = rng.uniform(0.003, 0.006)                         # t4: the lobe bellies out between its slits
        #                                                           (t3: 1.2-2.8 mm)
        # t4 (judge r3 item 5): the hem as a lobe: lowest in the middle, rising to the corners, tilted, offset; all
        # within +-HEM_VAR (0.15 d) of the mean hem line X_TAB_TIP and never below X_TAB_MIN (the cradle's face)
        off = rng.uniform(-0.002, 0.002)
        depth = rng.uniform(0.006, 0.010)                         # the scallop: the middle hangs this much lower
        tilt = rng.uniform(-0.002, 0.002)
        x_lo = max(X_TAB_MIN, X_TAB_TIP - HEM_VAR)
        cols = []
        for ia in range(na):
            ac = 2.0 * ia / (na - 1) - 1.0
            al = alpha0 + twist * ac + math.radians(6.0) * ac * ac    # the corners (slit edges) flare out most
            rho = rho0 * (1.0 + 0.25 * ac * ac)
            roll = roll_mid + ((roll_cl if ac < 0 else roll_cr) - roll_mid) * abs(ac) ** 1.6
            x_hem = X_TAB_TIP + off + depth * (ac * ac - 0.5) + tilt * ac
            x_hem = min(X_TAB_TIP + HEM_VAR, max(x_lo, x_hem))
            Lc = X_ROOT - x_hem
            # one smooth bend from flat to the flare angle (no planar run: t3's first pass read as flat shingles),
            # its radius sized so the hem's lowest point (the roll passes 90 deg) sits Lc below the root
            Rb = max(0.012, (Lc - TAB_FLAT - rho * (1 - math.sin(al))) / math.sin(al))
            n0 = COLLAR_T + 0.0004 - 0.5 * TAB_T                  # centre line: outer surface 0.4 mm over the collar
            st = [(-TAB_BURY, n0 - 0.0024, 0.0), (0.0, n0, 0.0), (0.5 * TAB_FLAT, n0, 0.0), (TAB_FLAT, n0, 0.0)]
            for f in (1 / 3, 2 / 3, 1.0):                         # the bend: a circle of radius Rb
                th = al * f
                st.append((TAB_FLAT + Rb * math.sin(th), n0 + Rb * (1 - math.cos(th)), th))
            ae, ne = st[-1][0], st[-1][1]
            ca, cn = ae - rho * math.sin(al), ne + rho * math.cos(al)   # the roll's centre (outward side)
            for k in range(1, n_roll + 1):
                th = al + roll * k / n_roll
                st.append((ca + rho * math.sin(th), cn - rho * math.cos(th), th))
            arc = [0.0]
            for q0, q1 in zip(st, st[1:]):
                arc.append(arc[-1] + math.hypot(q1[0] - q0[0], q1[1] - q0[1]))
            arc = [x_ - TAB_BURY for x_ in arc]                   # arc length from the root (negative when buried)
            cols.append((ac, st, arc))
            rolls.append(math.degrees(roll))
        L = X_ROOT - min(X_TAB_TIP + HEM_VAR, max(x_lo, X_TAB_TIP + off - 0.5 * depth))   # the centre column's depth
        nb = len(cols[0][1])
        # slit width per station: by the running maximum depth a of the centre column (it stays open in the roll):
        # t4: a V from SLIT_TOP at the root opening to SLIT_TIP (0.3 d) at the hem
        amax, wsl = 0.0, []
        for b in range(nb):
            amax = max(amax, cols[na // 2][1][b][0])
            f = min(1.0, max(0.0, (amax - TAB_FLAT) / (L - TAB_FLAT)))
            wsl.append(SLIT_TOP + (SLIT_TIP - SLIT_TOP) * f)
        hem_rng.append([X_ROOT - max(c[1][b][0] for b in range(nb)) for c in cols])
        verts, uvo, uvi = [], [], []
        for layer in (0, 1):                                      # 0 = outer (+N), 1 = inner (-N)
            for b in range(nb):
                for ac, st, arc in cols:
                    a, nn, th = st[b]
                    off = (0.5 if layer == 0 else -0.5) * TAB_T
                    a_, n_ = a - off * math.sin(th), nn + off * math.cos(th)
                    if b >= 3:      # below the flat run: a soft belly across the tab (none at the slit edges)
                        n_ += bulge * (1.0 - ac * ac) * min(1.0, (b - 2) / 3.0)
                    x = X_ROOT - a_
                    r = body_r(x) + n_
                    half = half_a - 0.5 * wsl[b] / r
                    ang = thc + ac * half
                    verts.append((s * x, r * math.cos(ang), r * math.sin(ang)))
                    # V as the collar lathe's (its column 0 sits at the -Z seam, phase -pi/2), so the tab root
                    # continues the collar's texture where it emerges from under it
                    uv = (UVL.COLLAR_U_FLAP - arc[b] / UVL.COLLAR_TILE_U + 0.01 * layer,
                          UVL.COLLAR_WRAPS * (ang + 0.5 * math.pi) / (2 * math.pi))
                    (uvi if layer else uvo).append(uv)
                    if layer == 0:
                        tips.append(x)
                        flares.append(n_)
        slit_tip.append(wsl[-1])
        widths.append(2 * half_a * body_r(X_ROOT))
        uvs_all = uvo + uvi
        dv = math.floor(min(v_ for _u, v_ in uvs_all))          # whole tiles: keep V inside 0..2 (qa tile range)
        uvs_all = [(u_, v_ - dv) for u_, v_ in uvs_all]
        tips_tab.append(min(abs(v_[0]) for v_ in verts))
        o = lambda b, a: b * na + a                    # noqa: E731
        i_ = lambda b, a: nb * na + b * na + a         # noqa: E731
        faces = []
        for b in range(nb - 1):
            for a in range(na - 1):
                faces.append((o(b, a), o(b, a + 1), o(b + 1, a + 1), o(b + 1, a)))
                faces.append((i_(b, a), i_(b + 1, a), i_(b + 1, a + 1), i_(b, a + 1)))
        for b in range(nb - 1):                        # the two slit sides
            faces.append((o(b, 0), o(b + 1, 0), i_(b + 1, 0), i_(b, 0)))
            faces.append((o(b, na - 1), i_(b, na - 1), i_(b + 1, na - 1), o(b + 1, na - 1)))
        for a in range(na - 1):                        # the buried root end and the hem's edge
            faces.append((o(0, a), i_(0, a), i_(0, a + 1), o(0, a + 1)))
            faces.append((o(nb - 1, a), o(nb - 1, a + 1), i_(nb - 1, a + 1), i_(nb - 1, a)))
        out.append((verts, faces, [[uvs_all[q] for q in f] for f in faces], [COLLAR] * len(faces)))
    return out, {"tabs": n_tabs, "tip_x_min_max_m": [round(min(tips_tab), 4), round(max(tips_tab), 4)],
                 "tip_offset_above_body_min_max_m": [round(min(flares), 4), round(max(flares), 4)],
                 "tab_width_at_root_mm_min_max": [round(min(widths) * 1000, 1), round(max(widths) * 1000, 1)],
                 "slit_width_at_hem_mm": round(1000 * slit_tip[0], 2),
                 "tris_per_tab": 2 * len(out[0][1]),
                 "hem_lowest_x_per_column_min_max_m": [round(min(min(h) for h in hem_rng), 4),
                                                       round(max(max(h) for h in hem_rng), 4)],
                 "hem_x_range_within_one_tab_mm_max": round(1000 * max(max(h) - min(h) for h in hem_rng), 2),
                 "hem_roll_deg_min_max": [round(min(rolls), 1), round(max(rolls), 1)]}


# --------------------------------------------------------------------------- the stand

def cradle_profile(yend, xabs, nseg=30):   # t7: 30 arc segments (t2-t6 20: 0.46 mm chord sag)
    """t2: saddle top of a cradle crossbeam in (y, z) on the beam face at |x| = xabs: flat outer shoulders at ONE
    common height (set by the inner face, the widest barrel radius), and a polyline arc with its vertices on
    Rs = body_R(xabs) + SADDLE_GAP (the felt thickness), so the two faces' arcs loft into a tapered seat that follows
    the barrel. Same point count on every face."""
    r_in = body_R(CRADLE_X0) + SADDLE_GAP
    h_sh = math.sqrt(r_in * r_in - CRADLE_FLAT_Y ** 2)
    Rs = body_R(xabs) + SADDLE_GAP
    a_max = math.asin(math.sqrt(Rs * Rs - h_sh * h_sh) / Rs)
    step = 2 * a_max / nseg
    pts = [(-yend, DRUM_Z - h_sh)]
    for i in range(nseg + 1):
        a = -a_max + i * step
        pts.append((Rs * math.sin(a), DRUM_Z - Rs * math.cos(a)))
    pts.append((yend, DRUM_Z - h_sh))
    return pts, Rs


def felt_strip(sx, nf=24):
    """t2 (the user's stand question): a FELT_T dark red wool felt strip lining the saddle of cradle sx: FELT_W of
    the beam's width, centred, following the arc to 12 mm short of the narrower (outer) face's shoulder. Its top
    lies on the barrel (vertices 0.3 mm inside body_r: the 144-gon barrel's chords sit up to 0.3 mm inside body_r, so
    the barrel rests on the felt with no air), its underside 0.4 mm
    inside the wood seat. Closed shell, 3 x (nf + 1) per side; on the hide atlas's taiko_uv.FELT_PATCH."""
    xc, hwf = 0.5 * (CRADLE_X0 + CRADLE_X1), 0.5 * FELT_W * (CRADLE_X1 - CRADLE_X0)
    xs = (xc - hwf, xc, xc + hwf)
    r_in = body_R(CRADLE_X0) + SADDLE_GAP
    h_sh = math.sqrt(r_in * r_in - CRADLE_FLAT_Y ** 2)
    r_min = body_R(xs[-1]) + FELT_T
    a_f = math.asin((math.sqrt(r_min * r_min - h_sh * h_sh) - 0.012) / r_min)
    u0, v0 = UVL.FELT_PATCH[0] + 0.01, UVL.FELT_PATCH[1] + 0.02
    # t7 (judge r6 item 5: t6's felt top sat 0.7-1.3 mm INSIDE the barrel, 432 intersecting triangle pairs): the felt
    # top follows the barrel's own facets: the lathe's columns every 2.5 deg (SIDES 144, column 0 at -Z) and its rings
    # at x 0.350 / 0.410 / 0.470 (the body rings at the cradle faces and middle), FELT_LIFT outside them; between two
    # rings the barrel is a chord in x, between two columns a chord in angle (planar trapezoids)
    rings_x = (CRADLE_X0, 0.5 * (CRADLE_X0 + CRADLE_X1), CRADLE_X1)
    step = 2 * math.pi / SIDES
    k_max = int(a_f / step - 1e-9)
    angs = [-a_f] + [k * step for k in range(-k_max, k_max + 1)] + [a_f]
    nf = len(angs) - 1

    def r_chord(x):
        for xa_, xb_ in zip(rings_x, rings_x[1:]):
            if xa_ - 1e-9 <= x <= xb_ + 1e-9:
                return body_R(xa_) + (body_R(xb_) - body_R(xa_)) * (x - xa_) / (xb_ - xa_)
        raise ValueError(x)

    def barrel_pt(x, a):
        k = math.floor(a / step + 1e-9)
        w = a / step - k
        r = r_chord(x)
        p0 = Vector((x, r * math.sin(k * step), -r * math.cos(k * step)))
        p1 = Vector((x, r * math.sin((k + 1) * step), -r * math.cos((k + 1) * step)))
        return p0 * (1 - w) + p1 * w
    verts, uvs_v = [], []
    for layer in (0, 1):                           # 0 = top (on the drum), 1 = underside (in the wood)
        for x in xs:
            for i in range(nf + 1):
                a = angs[i]
                q = barrel_pt(x, a)
                rad = Vector((0.0, q.y, q.z)).normalized()
                q = q + rad * (FELT_LIFT if layer == 0 else FELT_LIFT + FELT_T + 0.0004)
                verts.append((sx * x, q.y, DRUM_Z + q.z))
                uvs_v.append((u0 + (x - xs[0]) / UVL.HIDE_TILE + 0.05 * layer,
                              v0 + body_R(xc) * (a + a_f) / UVL.HIDE_TILE))
    nx = len(xs)
    q = lambda layer, ix, i: (layer * nx + ix) * (nf + 1) + i     # noqa: E731
    faces = []
    for ix in range(nx - 1):
        for i in range(nf):
            faces.append((q(0, ix, i), q(0, ix + 1, i), q(0, ix + 1, i + 1), q(0, ix, i + 1)))
            faces.append((q(1, ix, i), q(1, ix, i + 1), q(1, ix + 1, i + 1), q(1, ix + 1, i)))
    for i in range(nf):                            # the two long edges
        faces.append((q(0, 0, i), q(0, 0, i + 1), q(1, 0, i + 1), q(1, 0, i)))
        faces.append((q(0, nx - 1, i), q(1, nx - 1, i), q(1, nx - 1, i + 1), q(0, nx - 1, i + 1)))
    for ix in range(nx - 1):                       # the two ends
        faces.append((q(0, ix, 0), q(1, ix, 0), q(1, ix + 1, 0), q(0, ix + 1, 0)))
        faces.append((q(0, ix, nf), q(0, ix + 1, nf), q(1, ix + 1, nf), q(1, ix, nf)))
    return verts, faces, [[uvs_v[k] for k in f] for f in faces], [HIDE] * len(faces)


def cradle_profile_r2(yend):
    """(f1-t1 saddle, retired in t2: one radius on both faces, so the barrel touched only the inner edge)
    Saddle top of a cradle crossbeam in (y, z): flat outer shoulders, and a polyline arc whose chords stay just
    outside the drum (vertices on Rs / cos(half step), so each chord's midpoint sits at radius Rs)."""
    Rs = body_r(CRADLE_X0) + 0.003
    a_max = math.asin(CRADLE_FLAT_Y / Rs)
    nseg = 10
    step = 2 * a_max / nseg
    Rv = Rs / math.cos(step / 2)
    pts = [(-yend, DRUM_Z - math.sqrt(Rs * Rs - CRADLE_FLAT_Y ** 2))]
    for i in range(nseg + 1):
        a = -a_max + i * step
        rr = Rs if i in (0, nseg) else Rv
        pts.append((rr * math.sin(a), DRUM_Z - rr * math.cos(a)))
    pts.append((yend, pts[0][1]))
    return pts, Rs


def extrude_heightfield(xa, xb, prof, zb, mat, prof_b=None):
    """Closed solid between x = xa..xb whose Y-Z section is the area under the polyline prof (y ascending) down to
    zb. Built as vertical strips so every face is a convex quad (no n-gons). t2: prof_b (same point count) is the
    section on the x = xb face, so the top lofts between two profiles."""
    verts, faces = [], []
    for x, pr in ((xa, prof), (xb, prof_b or prof)):
        for (y, z) in pr:
            verts.append((x, y, z))
        for (y, z) in pr:
            verts.append((x, y, zb))
    n = len(prof)
    T0, B0, T1, B1 = 0, n, 2 * n, 3 * n
    for i in range(n - 1):
        faces.append((T0 + i, T0 + i + 1, B0 + i + 1, B0 + i))
        faces.append((T1 + i, B1 + i, B1 + i + 1, T1 + i + 1))
        faces.append((T0 + i, T1 + i, T1 + i + 1, T0 + i + 1))
        faces.append((B0 + i, B0 + i + 1, B1 + i + 1, B1 + i))
    faces.append((T0, B0, B1, T1))
    faces.append((T0 + n - 1, T1 + n - 1, B1 + n - 1, B0 + n - 1))
    tile = TILE[mat]
    uvs = []
    for f in faces:
        pts = [Vector(verts[i]) for i in f]
        nrm = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if abs(nrm.x) > max(abs(nrm.y), abs(nrm.z)):
            uvs.append([(q.y / tile + 0.21, q.z / tile) for q in pts])
        elif abs(nrm.y) > abs(nrm.z):
            uvs.append([(q.z / tile, q.x / tile + 0.33) for q in pts])
        else:
            uvs.append([(q.y / tile + 0.21, q.x / tile + 0.33) for q in pts])
    return verts, faces, uvs, [mat] * len(faces)


def extrude_loft(sections, zb, mat):
    """t4: extrude_heightfield over several sections [(x, prof), ...] (x ascending, the same point count each): the
    top lofts through every section, so a saddle seat can follow the bulged barrel's curve between the beam's faces
    (two sections leave the seat's middle up to 1.2 mm too close to the t4 barrel). Vertical strips, convex quads."""
    verts, faces = [], []
    n = len(sections[0][1])
    for x, pr in sections:
        assert len(pr) == n
        verts += [(x, y, z) for (y, z) in pr] + [(x, y, zb) for (y, _z) in pr]
    T = lambda k, i: 2 * n * k + i          # noqa: E731
    B = lambda k, i: 2 * n * k + n + i      # noqa: E731
    K = len(sections) - 1
    for i in range(n - 1):                   # the two end caps (x faces)
        faces.append((T(0, i), T(0, i + 1), B(0, i + 1), B(0, i)))
        faces.append((T(K, i), B(K, i), B(K, i + 1), T(K, i + 1)))
    for k in range(K):
        for i in range(n - 1):               # top and bottom
            faces.append((T(k, i), T(k + 1, i), T(k + 1, i + 1), T(k, i + 1)))
            faces.append((B(k, i), B(k, i + 1), B(k + 1, i + 1), B(k + 1, i)))
        faces.append((T(k, 0), B(k, 0), B(k + 1, 0), T(k + 1, 0)))                 # the two y ends
        faces.append((T(k, n - 1), T(k + 1, n - 1), B(k + 1, n - 1), B(k, n - 1)))
    tile = TILE[mat]
    uvs = []
    for f in faces:
        pts = [Vector(verts[i]) for i in f]
        nrm = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        if abs(nrm.x) > max(abs(nrm.y), abs(nrm.z)):
            uvs.append([(q.y / tile + 0.21, q.z / tile) for q in pts])
        elif abs(nrm.y) > abs(nrm.z):
            uvs.append([(q.z / tile, q.x / tile + 0.33) for q in pts])
        else:
            uvs.append([(q.y / tile + 0.21, q.x / tile + 0.33) for q in pts])
    return verts, faces, uvs, [mat] * len(faces)


_PT = [None]


def post_top(drum_pts=None):
    """Post top 4 mm under the drum surface above the post's inner top corner (the highest drum-bottom point over the
    post's top face). t3: and 4 mm under every drum vertex over the post's top face (the flap tabs and the tacks hang
    over the moved posts); computed once from the drum mesh, then cached."""
    if _PT[0] is not None:
        return _PT[0]
    xin, yin = POST_X - POST_W / 2, POST_Y - POST_W / 2
    r = body_R(xin)
    pt = DRUM_Z - math.sqrt(r * r - yin * yin) - 0.004
    if drum_pts:
        hw, m = POST_W / 2 + 0.003, 0.004
        over = [z for x, y, z in drum_pts if abs(abs(x) - POST_X) <= hw and abs(abs(y) - POST_Y) <= hw]
        if over:
            pt = min(pt, DRUM_Z + min(over) - m)
        _PT[0] = pt
    return pt


def stand(drum_pts=None):
    p = Part("SM_DKP_Taiko_Stand")
    hw = POST_W / 2
    PT = post_top(drum_pts)
    E = dict(end_mat=TIMEND)
    for sx in (-1, 1):
        xc = sx * POST_X
        # foot sill along Y (f1: heavier) with chunky raised stop blocks at both ends
        p.add(*cbox(xc - SILL_W / 2, xc + SILL_W / 2, -SILL_Y, SILL_Y, 0.0, SILL_H, TIM, grain="y", c=0.016,
                    uvoff=(0.1 * sx, 0.37), **E))
        for sy in (-1, 1):
            y0, y1 = sorted((sy * (SILL_Y - 0.145), sy * (SILL_Y - 0.004)))
            p.add(*cbox(xc - 0.125, xc + 0.125, y0, y1, SILL_H - 0.02, SILL_H + 0.11, TIM, grain="x", c=0.016,
                        uvoff=(0.23 * sy, 0.1 * sx), rough=0.003, **E))
        # cradle crossbeam (along Y) with the saddle; its ends run through the posts
        xa, xb = sorted((sx * CRADLE_X0, sx * CRADLE_X1))
        # t2: a tapered seat lofted between two arcs; t4: through three (the faces and the middle), so the seat
        # follows the bulged barrel's curve along the beam (wood >= 2 mm clear of the barrel everywhere)
        secs = [(x_, cradle_profile(POST_Y + hw - 0.01, abs(x_))[0]) for x_ in (xa, 0.5 * (xa + xb), xb)]
        p.add(*extrude_loft(secs, CRADLE_BOTTOM, TIM))
        p.add(*felt_strip(sx), smooth=True)                            # t2: the felt liner
        # f1: chunky kusabi wedge blocks outside the posts (taller than the beam, rough, no peg on top)
        for sy in (-1, 1):
            y0, y1 = sorted((sy * (POST_Y + hw - 0.004), sy * CRADLE_Y))
            wv, wf, wu, wm = cbox(xa - 0.008, xb + 0.008, y0, y1, CRADLE_BOTTOM - 0.025, CRADLE_BOTTOM + 0.195, TIM,
                                  grain="z", c=0.018, uvoff=(0.41, 0.17 * sy), rough=0.006, seed=900 + 10 * sx + sy, **E)
            xm, zb_, zt_ = 0.5 * (xa + xb), CRADLE_BOTTOM - 0.025, CRADLE_BOTTOM + 0.195
            wv = [(xm + (v[0] - xm) * (0.80 + 0.20 * (v[2] - zb_) / (zt_ - zb_)), v[1], v[2]) for v in wv]  # wedge taper
            p.add(wv, wf, wu, wm)
        for sy in (-1, 1):
            yc = sy * POST_Y
            p.add(*cbox(xc - hw, xc + hw, yc - hw, yc + hw, SILL_H - 0.03, PT, TIM, grain="z", c=0.014,
                        uvoff=(0.19 * sx + 0.05 * sy, 0.63), **E))
    # long rails (along X) at two levels on both sides, running out past the posts. r3: each rail laps flush on the
    # posts' outer faces (the sheet's joint close-up: the beam passes the post's outer face and a flat iron strap
    # plate is nailed flush across the joint). The r2 6 mm U-wrap round the rail end read as a black cube (judge r2
    # blocker 2) and is gone: the rail's end grain shows, as on the sheet.
    rivets = []
    for sy in (-1, 1):
        for (z0, z1), off, flush in ((RAIL_LO, 0.29, False), (RAIL_HI, 0.71, True)):
            # the lower rail stays centred through the post (its outer face must clear the sill's stop block,
            # which stands 3 cm outside it); its plate covers only the protruding end
            yc = sy * (POST_Y + (RAIL_Y_OUT if flush else 0.0))
            yo = yc + sy * RAIL_W / 2      # the rail's outer face (flush with the post's for the upper rail)
            p.add(*cbox(-RAIL_X, RAIL_X, yc - RAIL_W / 2, yc + RAIL_W / 2, z0, z1, TIM, grain="x", c=0.012,
                        uvoff=(0.0, off + 0.13 * sy), **E))
            for sx in (-1, 1):
                # a 4 mm flat strap plate: upper rail from just outside the cradle wedge block (x 0.585) across the
                # post's outer corner to 12 mm short of the rail tip; lower rail from the post's face to the tip
                x_in = CRADLE_X1 + 0.005 if flush else POST_X + hw + 0.003   # t3: was 0.585 (beam at 0.58)
                xa_, xb_ = sorted((sx * x_in, sx * (RAIL_X - 0.012)))
                ya_, yb_ = sorted((yo - sy * 0.0008, yo + sy * PLATE_T))
                p.add(*pbox(xa_, xb_, ya_, yb_, z0 + 0.012, z1 - 0.012))
                yn = yo + sy * PLATE_T
                zm, dz = 0.5 * (z0 + z1), 0.5 * (z1 - z0) - 0.030
                nrm = Vector((0, sy, 0))
                xe = RAIL_X - 0.032
                if flush:
                    xr0, xr1 = CRADLE_X1 + 0.027, POST_X + 0.112      # t3: 0.607 / 0.672 before the move
                    rivets += [((sx * xr0, yn, zm + dz), nrm, "small"), ((sx * xr0, yn, zm - dz), nrm, "small"),
                               ((sx * xr1, yn, zm - 0.004), nrm, "big")]
                else:
                    rivets += [((sx * (x_in + 0.022), yn, zm + 0.012), nrm, "big")]
                rivets += [((sx * xe, yn, zm + dz), nrm, "small"), ((sx * xe, yn, zm - dz), nrm, "small")]
    for k, (o, n, kind) in enumerate(rivets):
        big = kind == "big"
        rv, rf, ru, rm = dome(0.0120 if big else 0.0065, 0.0075 if big else 0.0045, 8 if big else 6)
        t = Vector((0, 0, 1)) if abs(n.z) < 0.5 else Vector((1, 0, 0))
        d = n.cross(t)
        p.add(rv, rf, ru, rm, smooth=True, M=frame(Vector(o), t, d, n))

    # ---- collision (blocking prop, unwalkable). f1: the saddle shoulders and wedge blocks are covered
    def box_pts(x0, x1, y0, y1, z0, z1):
        return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for sx in (-1, 1):
        xc = sx * POST_X
        p.hull(box_pts(xc - SILL_W / 2 - 0.01, xc + SILL_W / 2 + 0.01, -SILL_Y - 0.01, SILL_Y + 0.01, 0.0, SILL_H))
        for sy in (-1, 1):
            y0, y1 = sorted((sy * (SILL_Y - 0.145), sy * (SILL_Y + 0.004)))
            p.hull(box_pts(xc - 0.14, xc + 0.14, y0 - 0.005, y1 + 0.005, SILL_H - 0.025, SILL_H + 0.12))
        xa, xb = sorted((sx * CRADLE_X0, sx * CRADLE_X1))
        # t2: the seat's two face profiles and the felt's top surface
        fpts = [tuple(v) for v in felt_strip(sx)[0]]
        sec = [(x, y, z) for x, pr in ((xa, cradle_profile(POST_Y + hw - 0.01, abs(xa))[0]),
                                       (xb, cradle_profile(POST_Y + hw - 0.01, abs(xb))[0])) for y, z in pr]
        cpts = [(x, y, z + 0.002) for x, y, z in sec if abs(y) <= 0.18] + [v for v in fpts if abs(v[1]) <= 0.18]
        p.hull(cpts + [(x, y, CRADLE_BOTTOM) for _x, y, _z in cpts for x in (xa, xb)])   # f1: follows the arc
        for sy in (-1, 1):
            pts = []
            for x_, y, z in sec + fpts:
                if sy * y >= 0.17:
                    pts += [(x, y, z + 0.002) for x in (xa, xb)] + [(x, y, CRADLE_BOTTOM) for x in (xa, xb)]
            y_out = sy * (CRADLE_Y + 0.008)
            pts += [(x, y_out, z) for x in (xa - 0.012, xb + 0.012)
                    for z in (CRADLE_BOTTOM - 0.03, CRADLE_BOTTOM + 0.202)]
            pts += [(x, sy * (POST_Y + hw - 0.004), z) for x in (xa - 0.012, xb + 0.012)
                    for z in (CRADLE_BOTTOM - 0.03, CRADLE_BOTTOM + 0.202)]
            p.hull(pts)
        for sy in (-1, 1):
            yc = sy * POST_Y
            xo = sx * (POST_X + hw + 0.013)
            x0, x1 = sorted((xc - sx * hw, xo))
            p.hull(box_pts(x0, x1, yc - hw, yc + hw, SILL_H - 0.03, PT))
    for sy in (-1, 1):
        for (z0, z1) in (RAIL_LO, RAIL_HI):
            yc = sy * (POST_Y + (RAIL_Y_OUT if (z0, z1) == RAIL_HI else 0.0))   # r3: upper rails lap flush
            p.hull(box_pts(-RAIL_X - 0.004, RAIL_X + 0.004, yc - RAIL_W / 2 - 0.004, yc + RAIL_W / 2 + 0.014,
                           z0 - 0.004, z1 + 0.004) if sy > 0 else
                   box_pts(-RAIL_X - 0.004, RAIL_X + 0.004, yc - RAIL_W / 2 - 0.014, yc + RAIL_W / 2 + 0.004,
                           z0 - 0.004, z1 + 0.004))
    return p


# --------------------------------------------------------------------------- the stick

def stick_r(x):
    """r3: a slight taper toward the grip (x = 0), 13 %."""
    return STICK_R_GRIP + (STICK_R_TIP - STICK_R_GRIP) * max(0.0, min(1.0, x / STICK_L))


def stick_profile():
    """r3 (round-2 judge blocker 1 / delta 1: 'a lathe-turned stick, fully domed ends, no flat caps'): the turned
    profile (x, r) pole to pole. Each end is a superellipse dome (height STICK_DOME[0] x the end radius, exponent
    STICK_DOME[1]): round in silhouette with a soft shoulder, as the sheet's close-up. Returns the rings and the
    arc length of each ring from the grip pole (the UV's V)."""
    k, n = STICK_DOME
    h0, h1 = k * stick_r(0.0), k * stick_r(STICK_L)
    rings = []
    for deg in (0, 14, 26, 38, 50, 62, 74, 90):          # grip dome, pole -> shoulder
        ph = math.radians(deg)
        rings.append((h0 * (1 - math.cos(ph) ** (2 / n)), stick_r(0.0) * math.sin(ph) ** (2 / n)))
    body = [h0 + (STICK_L - h0 - h1) * t for t in (0.08, 0.2, 0.35, 0.5, 0.65, 0.8, 0.92)]
    for x in body:
        rings.append((x, stick_r(x)))
    for deg in (90, 74, 62, 50, 38, 26, 14, 0):          # strike dome, shoulder -> pole
        ph = math.radians(deg)
        rings.append((STICK_L - h1 * (1 - math.cos(ph) ** (2 / n)), stick_r(STICK_L) * math.sin(ph) ** (2 / n)))
    rings[0] = (0.0, 0.0)
    rings[-1] = (STICK_L, 0.0)
    arc = [0.0]
    for a, b in zip(rings[:-1], rings[1:]):
        arc.append(arc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return rings, arc


def stick():
    """r3: the bachi as a turned stick on the HIDE atlas's wood patch (taiko_uv.BACHI_*): U = one whole wrap round
    the stick over the periodic patch (no seam step), V = arc length along the profile from the grip pole, so the
    domes continue the side grain into the pole and carry the patch's end-grain tone (no radial pinwheel)."""
    p = Part("SM_DKP_Taiko_Stick")
    rings, arc = stick_profile()
    sides = 20

    def uv_fn(seg, k, col, pos):
        return (UVL.BACHI_U0 + UVL.BACHI_UW * col / sides, UVL.BACHI_V0 + arc[k] / UVL.HIDE_TILE)
    v, f, uv, m = lathe(rings, sides, -math.pi / 2, [HIDE] * (len(rings) - 1), uv_fn)
    p.add(v, f, uv, m, smooth=True)
    p.meta = {"arc_len_m": round(arc[-1], 4), "sides": sides, "rings": len(rings),
              "dome_heights_m": [round(STICK_DOME[0] * stick_r(0.0), 4), round(STICK_DOME[0] * stick_r(STICK_L), 4)]}
    rc = (STICK_R_TIP + 0.002) / math.cos(math.pi / 8)
    pts = []
    for x in (-0.001, STICK_L + 0.001):
        for i in range(8):
            a = 2 * math.pi * (i + 0.5) / 8
            pts.append((x, rc * math.cos(a), rc * math.sin(a)))
    p.hull(pts)
    return p


def stick_f1_r2():
    """(f1/r2 flat-ended stick on M_DJ_TimberAged, retired in r3)"""
    return None


# --------------------------------------------------------------------------- stick lean solver (f1)

def mesh_world(obj, M):
    me = obj.data
    return [M @ v.co for v in me.vertices], [tuple(pl.vertices) for pl in me.polygons]


def surface_samples(verts, polys, step, near_bvh, margin=0.02):
    """Stick side: points on the mesh surface (a barycentric grid `step` apart, which includes the vertices and
    edges) on the triangles that lie within `margin` of the obstacle (near_bvh), so the sampling stays local."""
    out = []
    for pl in polys:
        for a in range(1, len(pl) - 1):
            tri = (verts[pl[0]], verts[pl[a]], verts[pl[a + 1]])
            ln = max((tri[1] - tri[0]).length, (tri[2] - tri[1]).length, (tri[0] - tri[2]).length)
            c = (tri[0] + tri[1] + tri[2]) / 3
            if near_bvh.find_nearest(c, ln + margin)[0] is None:
                continue
            n = max(1, int(math.ceil(ln / step)))
            for i in range(n + 1):
                for j in range(n + 1 - i):
                    u, w = i / n, j / n
                    out.append(tri[0] * (1 - u - w) + tri[1] * u + tri[2] * w)
    return out


def edge_samples(verts, edges, step, lo, hi):
    """Obstacle side: vertices and edge points `step` apart, clipped to the box lo..hi around the stick. With the
    stick's surface grid this covers the vertex-face, face-vertex and edge-edge contact cases."""
    out = [v for v in verts if all(lo[i] <= v[i] <= hi[i] for i in range(3))]
    for a, b in edges:
        p0, p1 = verts[a], verts[b]
        d = p1 - p0
        t0, t1 = 0.0, 1.0
        for i in range(3):
            if abs(d[i]) < 1e-12:
                if p0[i] < lo[i] or p0[i] > hi[i]:
                    t0, t1 = 1.0, 0.0
                    break
                continue
            ta, tb = (lo[i] - p0[i]) / d[i], (hi[i] - p0[i]) / d[i]
            t0, t1 = max(t0, min(ta, tb)), min(t1, max(ta, tb))
        if t1 <= t0:
            continue
        n = max(1, int(math.ceil((t1 - t0) * d.length / step)))
        out += [p0 + d * (t0 + (t1 - t0) * k / n) for k in range(n + 1)]
    return out


def min_gap(stick_obj, M, obstacles, step=0.003):
    """Minimum surface distance between the stick placed at M and the obstacle meshes (two-way sampled)."""
    sv, sp = mesh_world(stick_obj, M)
    s_bvh = BVHTree.FromPolygons(sv, sp)
    lo = Vector([min(v[i] for v in sv) - 0.01 for i in range(3)])
    hi = Vector([max(v[i] for v in sv) + 0.01 for i in range(3)])
    best = (1e9, None)
    for name, (ov, oe, o_bvh) in obstacles.items():
        for q in surface_samples(sv, sp, step, o_bvh):
            hit = o_bvh.find_nearest(q, 0.05)
            if hit[0] is not None and hit[3] < best[0]:
                best = (hit[3], name)
        for q in edge_samples(ov, oe, step, lo, hi):
            hit = s_bvh.find_nearest(q, 0.05)
            if hit[0] is not None and hit[3] < best[0]:
                best = (hit[3], name)
    return best


def stick_poses(stick_obj, stand_obj, drum_obj):
    """f1 (blind judge + measurer): both sticks stand on the plinth at the front-right (+X, -Y) end of the stand and
    lean 15 and 18.5 degrees toward -X onto the upper front rail's end (its folded iron strap), as in the sheet's
    front view. The tilt is fixed; the stick slides along X until the sampled mesh gap to the stand or drum is
    0.5 mm; the feet are set 0.5 mm above the plinth (the lowest vertex of a polyhedron is its lowest point)."""
    obstacles = {}
    for name, obj, M in (("stand", stand_obj, Matrix.Identity(4)), ("drum", drum_obj,
                                                                    Matrix.Translation((0, 0, DRUM_Z)))):
        v, pl = mesh_world(obj, M)
        obstacles[name] = (v, [tuple(e.vertices) for e in obj.data.edges], BVHTree.FromPolygons(v, pl))
    target = 0.0005
    poses = []
    placed = []
    # r2 (judges: "sticks lean at the far end by the post"): both sticks stand beside the +X/-Y post, just outboard
    # of the sill's stop block, and lean BACK onto the iron wrap of the upper front rail's end (the sheet's 3/4 view:
    # two sticks side by side against the far post). Each stick keeps its tilt and lean azimuth and slides along the
    # lean direction s (horizontal) from well outside until the sampled mesh gap is 0.5 mm.
    #   (foot x at the start, foot y at the start, slide direction s, tilt from vertical, roll)
    specs = ((RAIL_X - 0.015, -1.20, (0.0, 1.0), 11.0, 0.6),     # t3: x 0.745 = RAIL_X - 0.015 before the move
             (RAIL_X + 0.660, -0.50 * POST_Y / 0.48, (-1.0, 0.15), 14.0, 2.3))   # t6: y with the wider frame   # the second leans in on the rail end's iron plate
    for k, (x0, y0, sdir, tilt, roll) in enumerate(specs):
        sv_ = Vector((sdir[0], sdir[1], 0.0)).normalized()
        a = math.radians(tilt)
        D = Vector((-sv_.x * math.sin(a), -sv_.y * math.sin(a), -math.cos(a)))   # grip (top) -> strike end (foot)
        q = Vector((1, 0, 0)).rotation_difference(D)
        R = q.to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, "X")
        zmin = min((R @ v.co).z for v in stick_obj.data.vertices)
        foot_local = min(stick_obj.data.vertices, key=lambda v: (R @ v.co).z).co
        fl = R @ foot_local

        def pose(t, x0=x0, y0=y0, sv_=sv_, R=R, zmin=zmin, fl=fl):
            # t = distance slid along s; the lowest vertex (the foot) sits at (x0, y0) + s t
            return Matrix.Translation((x0 + sv_.x * t - fl.x, y0 + sv_.y * t - fl.y, target - zmin)) @ R
        obs = dict(obstacles)
        for j, Mo in enumerate(placed):
            v, pl = mesh_world(stick_obj, Mo)
            obs[f"stick{j}"] = (v, [tuple(e.vertices) for e in stick_obj.data.edges], BVHTree.FromPolygons(v, pl))
        # march in from outside, then bisect on t for a 0.5 mm gap (t grows toward the stand)
        t_far = 0.0
        g_far = min(0.2, min_gap(stick_obj, pose(t_far), obs, 0.004)[0])
        t_near = t_far
        while True:
            t_try = t_near + max(0.0015, min(0.05, g_far * 0.5))
            g = min(0.2, min_gap(stick_obj, pose(t_try), obs, 0.004)[0])
            if g < target:
                t_near = t_try
                break
            t_far, g_far, t_near = t_try, g, t_try
            if t_try > 1.2:
                raise RuntimeError("stick %d never touched the stand" % k)
        lo_x, hi_x = t_near, t_far      # lo: touching, hi: clear
        for _ in range(16):
            mid = 0.5 * (lo_x + hi_x)
            g = min_gap(stick_obj, pose(mid), obs, 0.001)[0]
            if g > target:
                hi_x = mid
            else:
                lo_x = mid
        M = pose(hi_x)
        gap, who = min_gap(stick_obj, M, obs, 0.001)
        foot = min((M @ v.co).z for v in stick_obj.data.vertices)
        tip = M @ Vector((STICK_L, 0, 0))
        top = M @ Vector((0, 0, 0))
        placed.append(M)
        fw = M @ foot_local
        print(f"stick {k}: gap {gap:.5f} with {who}, foot {foot:.5f}, foot xy {fw.x:.4f} {fw.y:.4f}")
        poses.append((M, {"tilt_from_vertical_deg": tilt, "lean_toward_xy": [round(sv_.x, 3), round(sv_.y, 3)],
                          "roll_rad": roll, "contact_gap_m": round(gap, 5), "contact_with": who,
                          "foot_gap_above_plinth_m": round(foot, 5),
                          "foot_xy_stand_local": [round(fw.x, 4), round(fw.y, 4)],
                          "top_end_centre_stand_local": [round(c, 4) for c in top],
                          "strike_end_centre_stand_local": [round(c, 4) for c in tip],
                          "solver": "BVH: stick surface grid + obstacle vertices/edges, 1 mm samples; bisection "
                                    "on the slide distance"}))
    return poses


def _old_stick_loop_f1():
    """f1 stick loop (retired in r2)."""
    for k, (y, tilt, yaw, roll) in enumerate(()):
        pass


# --------------------------------------------------------------------------- layout

# Spec (DOJO_ARENA_SPEC 4.5, grey-box SM_DGB_Pavilion): pavilion plinth X 39-43, Y 1-5, top +1.0; the drum stands at
# the plinth centre (41, 3), drum axis north-south (local X -> world +Y, rot_z 90): the sheet's front view faces the
# courtyard on the west.
PAV_CENTRE = (41.0, 3.0)
PLINTH_TOP = 1.0
ROT_Z = 90.0


def export_with_lods(name, o, sc, waive):
    """kit 1's pattern: LOD0-2 on temporary copies (pipeline decimate_lods + make_lod_group, UCX renamed
    UCX_<base>_LOD0_NN), QA on the LODs, export the LodGroup through Scripts/pipeline."""
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
    cleaned = {}
    for lo in lods:   # Collapse can leave wire edges / loose verts where a tiny rivet collapses: drop them
        bm = bmesh.new()
        bm.from_mesh(lo.data)
        wire = [e for e in bm.edges if not e.link_faces]
        bmesh.ops.delete(bm, geom=wire, context="EDGES")
        loose = [v for v in bm.verts if not v.link_edges]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(lo.data)
        bm.free()
        cleaned[lo.name] = {"wire_edges_removed": len(wire), "loose_verts_removed": len(loose)}
        # t2: Collapse can fold a lightmap (UV1) island over itself (the stand's thin felt strips did, 2 pairs on
        # LOD1): re-pack UV1 on every LOD, the same lightmap pack as LOD0 (each LOD has its own lightmap UVs in UE)
        me = lo.data
        if name in UV1_SMART:            # t3: retry with tighter charts until the decimated LOD's UV1 has no overlap
            for ang in (45.0, 30.0, 20.0, 12.0, 8.0, 5.0):   # t6: + 8 / 5 (the t6 skirt's LOD2 overlapped at 12)
                uv1_smart(lo, ang)
                ov = [c for c in qa_check([lo], require_uv1=True, require_ucx=False)["checks"]
                      if c["name"] == "uv1_no_overlap" and not c["passed"]]
                cleaned[lo.name]["uv1_smart_angle"] = ang
                if not ov:
                    break
            if ov:                       # t6: last resort, Blender's per-face lightmap pack (never overlaps)
                me.uv_layers.active_index = me.uv_layers.find("UV1")
                with bpy.context.temp_override(active_object=lo, object=lo, selected_objects=[lo],
                                               selected_editable_objects=[lo]):
                    bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                             PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.3)
                me.uv_layers.active_index = 0
                cleaned[lo.name]["uv1_smart_angle"] = "lightmap_pack"
        else:
            me.uv_layers.active_index = me.uv_layers.find("UV1")
            with bpy.context.temp_override(active_object=lo, object=lo, selected_objects=[lo],
                                           selected_editable_objects=[lo]):
                bpy.ops.uv.lightmap_pack(PREF_CONTEXT="ALL_FACES", PREF_PACK_IN_ONE=False, PREF_NEW_UVLAYER=False,
                                         PREF_BOX_DIV=12, PREF_MARGIN_DIV=0.3)
            me.uv_layers.active_index = 0
        cleaned[lo.name]["uv1_repacked"] = True
    grp = make_lod_group(name, [c0] + lods)
    lq = qa_check([c0] + lods, require_uv1=True, require_ucx=False)
    lod_hard = [c for c in lq["checks"] if not c["passed"] and c["name"] not in waive]
    r = export_fbx(str(EXPORT_DIR / f"{name}.fbx"), [grp], kind="static", sidecar=True)
    tris = [lq["triangles"].get(x.name) for x in [c0] + lods]
    rep = {"lods": 3, "lod_tris": tris, "strictly_descending": all(a > b for a, b in zip(tris, tris[1:])),
           "lod_qa_hard_fails": [(c["name"], c["object"], str(c["detail"])[:160]) for c in lod_hard],
           "lod_cleanup": cleaned, "objects": r["objects"], "screen_sizes": r.get("lod_screen_sizes"), "warnings": r["warnings"]}
    for ob in list(tmp.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.collections.remove(tmp)
    return rep


def main():
    assert_owner("Taiko", "claude")   # t1: the lock this asset is held under
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for name in MATERIALS:
        build_material(name)
    dpart = drum()
    dpts = [v for verts, _f, _u, _m, _s in dpart.chunks for v in verts]
    parts = {"SM_DKP_Taiko_Drum": ("Taiko_Drum", dpart), "SM_DKP_Taiko_Stand": ("Taiko_Stand", stand(dpts)),
             "SM_DKP_Taiko_Stick": ("Taiko_Stick", stick())}
    objs = {}
    for name, (cname, part) in parts.items():
        coll = bpy.data.collections.new(cname)
        sc.collection.children.link(coll)
        objs[name] = part.build(coll)
    drum_meta = parts["SM_DKP_Taiko_Drum"][1].meta
    # r2: the stand's timber takes the library's grain_uv (U along each member's long axis, V round the member from
    # its centre, a random per-member offset, end faces planar with TimberDarkEnd): t1's per-face planar V put the
    # two faces of one member on different tone bands of the 4 m tile (a light face next to a dark one)
    st = objs["SM_DKP_Taiko_Stand"]
    mi = {m.name: i for i, m in enumerate(st.data.materials)}
    wood = [pl.index for pl in st.data.polygons if pl.material_index in (mi[TIM], mi[TIMEND])]
    for i in wood:
        st.data.polygons[i].material_index = mi[TIM]
    gstats = djm.grain_uv(st, "TimberDark", end_set="TimberDarkEnd", faces=wood, end_material_index=mi[TIMEND],
                          seed=11, uv_map="UV0")
    print("GRAIN", gstats)
    TIMBER_BAND = {"stand": pin_band_v(st, {TIM}, 0.27, 0.51, seed=5),
                   "stick": "r3: the stick is on the hide atlas's own wood patch (no library band)"}
    print("BAND", TIMBER_BAND)
    # r2: the library's weathering corner colour 'Wear' (R grime / occlusion, G edge wear on narrow convex bevels,
    # B ground dirt), read by every library-graph material here and by M_DJ_Lib_Opaque in Unreal
    wear = {}
    for name, o in objs.items():
        gz = {"SM_DKP_Taiko_Drum": -DRUM_Z, "SM_DKP_Taiko_Stand": 0.0, "SM_DKP_Taiko_Stick": -10.0}[name]
        wear[name] = djm.bake_wear(o, ao_rays=16, ao_dist=0.12, ground_z=gz)
        wear[name + "_regrime"] = regrime(o, dist=0.12, ground_z=(0.0 if name.endswith("Stand") else None))
        o.data.color_attributes.active_color_name = "Wear"
    wear["drum_bulge"] = drum_wear_bulge(objs["SM_DKP_Taiko_Drum"])
    wear["stand_felt"] = felt_wear(objs["SM_DKP_Taiko_Stand"])
    wear["drum_collar"] = felt_wear(objs["SM_DKP_Taiko_Drum"], COLLAR)
    wear["drum_tacks"] = tack_wear(objs["SM_DKP_Taiko_Drum"])
    wear["stick_edges"] = stick_wear_ends(objs["SM_DKP_Taiko_Stick"])
    print("WEAR", wear)

    # ---- layout (assembled at the pavilion's drum position, grey-box frame) as linked instances
    lay = bpy.data.collections.new("Taiko_Layout")
    sc.collection.children.link(lay)
    base = Matrix.Translation((PAV_CENTRE[0], PAV_CENTRE[1], PLINTH_TOP)) @ Matrix.Rotation(math.radians(ROT_Z), 4, "Z")
    local = {"SM_DKP_Taiko_Stand": [(Matrix.Identity(4), {})],
             "SM_DKP_Taiko_Drum": [(Matrix.Translation((0, 0, DRUM_Z)), {})],
             "SM_DKP_Taiko_Stick": stick_poses(objs["SM_DKP_Taiko_Stick"], objs["SM_DKP_Taiko_Stand"],
                                               objs["SM_DKP_Taiko_Drum"])}
    instances = []
    for piece, lst in local.items():
        for k, (ML, info) in enumerate(lst):
            o = bpy.data.objects.new(f"{piece}__{k:02d}", objs[piece].data)
            o.matrix_world = base @ ML
            lay.objects.link(o)
            loc, rot, _s = o.matrix_world.decompose()
            eul = rot.to_euler("XYZ")
            pts = [o.matrix_world @ v.co for v in o.data.vertices]
            instances.append({
                "piece": piece, "name": o.name,
                "loc": [round(c, 4) for c in loc], "rot_xyz_deg": [round(math.degrees(a), 3) for a in eul],
                "stand_local_matrix": [[round(c, 6) for c in row] for row in ML],
                "bbox_min_max": [round(min(q[i] for q in pts), 4) for i in range(3)] +
                                [round(max(q[i] for q in pts), 4) for i in range(3)],
                "unreal_loc_cm": [round(loc.x * 100, 2), round(-loc.y * 100, 2), round(loc.z * 100, 2)],
                **({"pose": info} if info else {})})

    meas = measure(objs, instances, drum_meta)
    WORK.mkdir(parents=True, exist_ok=True)

    coll_classes = {
        "SM_DKP_Taiko_Drum": {"class": "blocking prop, unwalkable (spec 5.2: 'the drum and its stand')",
                               "pawn": "block", "camera": "ignore", "visibility": "block", "gasp_traversal": "none",
                               "can_character_step_up_on": "No", "walkable_slope_override": "Unwalkable",
                               "ucx": "one convex 16-gon prism around barrel + handles"},
        "SM_DKP_Taiko_Stand": {"class": "blocking prop, unwalkable (thin-upright rules: camera and sight ignore)",
                                "pawn": "block", "camera": "ignore", "visibility": "ignore", "gasp_traversal": "none",
                                "can_character_step_up_on": "No", "walkable_slope_override": "Unwalkable",
                                "ucx": "20 hulls: 2 sills, 4 stop blocks, 2 x 3 cradle (centre + 2 shoulders with "
                                       "the wedge blocks), 4 posts (with the strap legs), 4 rails (with the straps)"},
        "SM_DKP_Taiko_Stick": {"class": "small dressing (lean-on prop)", "pawn": "ignore", "camera": "ignore",
                                "visibility": "ignore", "gasp_traversal": "none",
                                "ucx": "one convex 8-gon prism (kept for physics / a later pickup)"},
    }
    data = {"units": "metres, grey-box frame (DOJO_ARENA_SPEC section 1); UE: (x*100, -y*100, z*100), yaw = -rot_z",
            "source_spec": "WorkFiles/world/DOJO_ARENA_SPEC.md 4.5 (drum pavilion plinth X 39-43, Y 1-5, top +1.0)",
            "anchor": {"pavilion_plinth_centre": list(PAV_CENTRE), "plinth_top_z": PLINTH_TOP, "rot_z_deg": ROT_Z,
                       "note": "drum axis north-south; ring-handle side faces the courtyard (west). The pavilion "
                               "itself is not in this run. Sticks lean at the stand's +X/-Y corner (world north-"
                               "west corner)."},
            "pieces": {n: {"fbx": f"Exports/DojoKit/Props/taiko/{n}.fbx", "pivot": pv, "lods": 3,
                           "materials": [m.name for m in objs[n].data.materials], "collision": coll_classes[n]}
                       for n, pv in (("SM_DKP_Taiko_Drum", "drum centre (on the axis, mid-length)"),
                                     ("SM_DKP_Taiko_Stand", "base centre on the ground"),
                                     ("SM_DKP_Taiko_Stick", "grip end, on the stick axis; stick along +X"))},
            "instances": instances,
            "materials": {k: {"texture_set": (f"T_DKP_Taiko_{v[0]}" if k in OWN else
                                              f"T_DJ_{v[0].split()[-1]} (Exports/DojoKit/Materials/Textures)"),
                              "params": v[1]} for k, v in MATERIALS.items()},
            "tris": {k: sum(len(pl.vertices) - 2 for pl in o.data.polygons) for k, o in objs.items()}}
    COMPARE = "--blend" in ARGS     # t4: a comparison build (e.g. --tack-sides 24) writes only its own .blend
    if not COMPARE:
        (WORK / "layout_taiko.json").write_text(json.dumps(data, indent=1), encoding="utf-8")

    # ---- QA (pipeline gates; tiling materials waive UV0 overlap by design, as the armory kit does)
    qa = {}
    waive = {"uv_no_overlap"}
    for name, o in objs.items():
        r = qa_check([o], require_uv1=True)
        fails = [c for c in r["checks"] if not c["passed"]]
        hard = [c for c in fails if c["name"] not in waive]
        qa[name] = {"hard_fails": hard, "waived": [c["name"] for c in fails if c["name"] in waive],
                    "tris": r["triangles"].get(name), "checks_run": len(r["checks"]),
                    "texel": [c["detail"] for c in r["checks"] if c["name"] == "texel_density"]}
    hard_total = sum(len(v["hard_fails"]) for v in qa.values())
    print(f"QA: {len(objs)} pieces, hard fails {hard_total}")
    for k, v in qa.items():
        print("  ", k, "tris", v["tris"], "waived", v["waived"])
        for c in v["hard_fails"]:
            print("  FAIL", k, c["name"], str(c["detail"])[:200])

    if "--no-export" not in ARGS and hard_total == 0:
        lay.hide_viewport = True
        results = {}
        for name, o in objs.items():
            results[name] = export_with_lods(name, o, sc, waive)
            print("  export", name, results[name]["lod_tris"], results[name]["lod_qa_hard_fails"])
        (WORK / "export_report.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
        lay.hide_viewport = False
        for name, rr in results.items():
            qa[name]["lods"] = {"lod_tris": rr["lod_tris"], "strictly_descending": rr["strictly_descending"],
                                "lod_qa_hard_fails": rr["lod_qa_hard_fails"]}
        meas["summary"]["lod_tris"] = {k: v["lod_tris"] for k, v in results.items()}
        print(f"exported {len(results)} FBX to {EXPORT_DIR}")
    if not COMPARE:
        (WORK / "qa_report.json").write_text(json.dumps(qa, indent=1, default=str), encoding="utf-8")
        (WORK / "measure.json").write_text(json.dumps(meas, indent=1), encoding="utf-8")
    BLEND.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    print("saved", BLEND)
    print("MEASURE", json.dumps(meas["summary"]))


def pin_band_v(obj, mat_names, lo, hi, seed=0, uv="UV0"):
    """r2: pin every timber member (a connected island of faces using one of mat_names) into the V range lo..hi of
    the library tile. The library timber sets carry a strong large-scale tone band ACROSS V (TimberDark row means:
    v 0.03-0.2 near black, 12-15; v 0.27-0.51 mid, 43-67; v 0.52-0.97 light, 95-124), so the library's random
    per-member offsets make one member black and its neighbour orange (the judges' 'one member differs' look). The
    reference timber is one even dark brown, so every member of these props samples the same band; U offsets stay
    random. Shifts are rigid (whole-island), so texel density and continuity are unchanged."""
    import bmesh as _bm
    import random as _rnd
    rng = _rnd.Random(seed)
    me = obj.data
    idx = {i for i, m in enumerate(me.materials) if m and m.name in mat_names}
    bm = _bm.new()
    bm.from_mesh(me)
    lay = bm.loops.layers.uv[uv]
    faces = [f for f in bm.faces if f.material_index in idx]
    fset = set(faces)
    seen, n_isl, spans = set(), 0, []
    for f0 in faces:
        if f0.index in seen:
            continue
        stack, isl = [f0], []
        seen.add(f0.index)
        while stack:
            c = stack.pop()
            isl.append(c)
            for e in c.edges:
                for g in e.link_faces:
                    if g in fset and g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        vs = [l[lay].uv.y for f in isl for l in f.loops]
        v0, v1 = min(vs), max(vs)
        span = v1 - v0
        spans.append(round(span, 4))
        c_ = rng.uniform(lo + span / 2, hi - span / 2) if span < hi - lo else 0.5 * (lo + hi)
        d = c_ - 0.5 * (v0 + v1)
        for f in isl:
            for l in f.loops:
                l[lay].uv.y += d
        n_isl += 1
    bm.to_mesh(me)
    bm.free()
    me.update()
    return {"islands": n_isl, "band_v": [lo, hi], "max_span": max(spans) if spans else 0,
            "over_band": sum(1 for s in spans if s > hi - lo)}


def regrime(obj, rays=16, dist=0.15, inset=0.30, ground_z=None, attr="Wear"):
    """r2: re-sample the library Wear R (grime / occlusion) per face CORNER at a point 30 % in from the corner toward
    the face centre, instead of at the vertex. These props are built from interpenetrating members (a rail runs
    through a post, a brace dies into a block), so a vertex buried inside a neighbouring member is fully occluded and
    the library's per-vertex value darkened the whole face toward it (measured: stand R mean 0.61). The formula is the
    library's (cosine hemisphere, hits / rays x 1.4, clamped); an optional ground plane at ground_z occludes too. G and
    B stay exactly as bake_wear wrote them."""
    import math as _m
    import random as _r
    from mathutils import Vector as _V
    from mathutils.bvhtree import BVHTree as _B
    me = obj.data
    Mw = obj.matrix_world
    verts = [Mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    if ground_z is not None:
        n0 = len(verts)
        verts += [_V((-20, -20, ground_z)), _V((20, -20, ground_z)), _V((20, 20, ground_z)), _V((-20, 20, ground_z))]
        polys.append((n0, n0 + 1, n0 + 2, n0 + 3))
    bvh = _B.FromPolygons(verts, polys, epsilon=0.0)
    rnd = _r.Random(7)
    dirs = []
    for i in range(rays):
        u1, u2 = (i + rnd.random()) / rays, rnd.random()
        rr = _m.sqrt(u1)
        th = 2 * _m.pi * u2
        dirs.append(_V((rr * _m.cos(th), rr * _m.sin(th), _m.sqrt(max(0.0, 1 - u1)))))
    ca = me.color_attributes[attr]
    R3 = Mw.to_3x3()
    tot, n = 0.0, 0
    for p in me.polygons:
        nrm = (R3 @ p.normal).normalized()
        if nrm.length < 0.5:
            continue
        cen = Mw @ p.center
        rot = nrm.to_track_quat("Z", "Y").to_matrix()
        for li in p.loop_indices:
            v = verts[me.loops[li].vertex_index]
            q = v + (cen - v) * inset + nrm * 1e-3
            hit = 0
            for d in dirs:
                if bvh.ray_cast(q, rot @ d, dist)[0] is not None:
                    hit += 1
            r = min(1.0, hit / rays * 1.4)
            c = ca.data[li].color
            ca.data[li].color = (r, c[1], c[2], 1.0)
            tot += r
            n += 1
    me.update()
    return {"corners": n, "R_mean": round(tot / max(n, 1), 3)}


def felt_wear(o, mat=None):
    """t2: the saddle felt (hide-atlas faces on the stand) and the hide collar with its flap tabs (whose small faces
    bake_wear reads as narrow bevels, which lifted the tabs pale) have no pale worn arrises: Wear G = 0, grime
    capped at 0.5."""
    me = o.data
    ca = me.color_attributes["Wear"]
    hid = {i for i, m in enumerate(me.materials) if m and m.name == (mat or HIDE)}
    n = 0
    for p in me.polygons:
        if p.material_index in hid:
            n += 1
            for li in p.loop_indices:
                c = ca.data[li].color
                ca.data[li].color = (min(c[0], 0.5), 0.0, c[2], 1.0)
    return {"felt_faces": n}


def tack_wear(o):
    """t3 (judge round 3: brown flecks round the tack edges): the lacquered tacks (hide-atlas faces below the lip,
    |x| < 0.745) carry no edge wear (G) and no ground dust (B); the grime (R) stays, capped at 0.5."""
    me = o.data
    ca = me.color_attributes["Wear"]
    hid = {i for i, m in enumerate(me.materials) if m and m.name == HIDE}
    n = 0
    for p in me.polygons:
        if p.material_index in hid and max(abs(me.vertices[v].co.x) for v in p.vertices) < DRUM_S * (LIP_XC - 0.013):
            n += 1
            for li in p.loop_indices:
                c = ca.data[li].color
                ca.data[li].color = (min(c[0], 0.5), 0.0, 0.0, 1.0)
    return {"tack_faces": n}


def stick_wear_ends(o):
    """r3: a smooth, oiled turned stick has no pale worn arrises (the sheet's close-up): Wear G = 0 everywhere; the
    grime (R) and the ground dirt (B) stay."""
    me = o.data
    ca = me.color_attributes["Wear"]
    for p in me.polygons:
        for li in p.loop_indices:
            c = ca.data[li].color
            ca.data[li].color = (min(c[0], 0.5), 0.0, c[2], 1.0)
    return {"faces_with_edge_wear": 0, "faces": len(me.polygons), "grime_capped": 0.5}


def drum_wear_bulge(o):
    """r2 (judges: 'worn highlights on the bulge'): the lacquer's Wear G across the belly, patchy (3D noise), so the
    library wear maths lifts it by up to +17 % in broken patches; the hide face keeps G = 0 (only grime there)."""
    from mathutils.noise import noise as pn
    me = o.data
    ca = me.color_attributes["Wear"]
    idx = {m.name: i for i, m in enumerate(me.materials)}
    lac, hid = idx.get(LAC), idx.get(HIDE)
    n_lac = n_worn = 0
    for poly in me.polygons:
        if poly.material_index not in (lac, hid):
            continue
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            c = ca.data[li].color
            if poly.material_index == hid:
                ca.data[li].color = (c[0], 0.0, c[2], 1.0)
                continue
            band = math.exp(-(co.x / 0.34) ** 2)
            nz = 0.5 + 0.5 * pn(Vector((co.x * 5.0, co.y * 5.0, co.z * 5.0)))
            nz2 = 0.5 + 0.5 * pn(Vector((co.x * 17.0 + 3.1, co.y * 17.0, co.z * 17.0)))
            g = max(c[1], min(1.0, band * (0.35 + 1.1 * nz) * (0.7 + 0.5 * nz2)))
            ca.data[li].color = (c[0], g, c[2], 1.0)
            n_lac += 1
            n_worn += g > 0.5
    return {"lacquer_corners": n_lac, "corners_G_over_0.5": n_worn}


def measure(objs, instances, drum_meta):
    out = {"pieces": {}}
    for name, o in objs.items():
        me = o.data
        co = [v.co for v in me.vertices]
        by_mat = {}
        for pl in me.polygons:
            by_mat.setdefault(me.materials[pl.material_index].name, set()).update(pl.vertices)
        mm = {}
        for mname, vids in by_mat.items():
            pts = [co[i] for i in vids]
            mm[mname] = {"bbox_min": [round(min(p[i] for p in pts), 4) for i in range(3)],
                         "bbox_max": [round(max(p[i] for p in pts), 4) for i in range(3)]}
        out["pieces"][name] = {
            "bbox_min": [round(min(p[i] for p in co), 4) for i in range(3)],
            "bbox_max": [round(max(p[i] for p in co), 4) for i in range(3)],
            "dims": [round(max(p[i] for p in co) - min(p[i] for p in co), 4) for i in range(3)],
            "verts": len(me.vertices), "tris": sum(len(pl.vertices) - 2 for pl in me.polygons),
            "materials": mm, "ucx_hulls": len([c for c in o.children if c.name.startswith("UCX_")])}
    d = objs["SM_DKP_Taiko_Drum"].data
    mat_v = {}
    for pl in d.polygons:
        mat_v.setdefault(d.materials[pl.material_index].name, set()).update(pl.vertices)
    rr = lambda i: math.hypot(d.vertices[i].co.y, d.vertices[i].co.z)  # noqa: E731
    belly = max(rr(i) for i in mat_v[LAC])
    face_flat = [i for i in mat_v[HIDE] if abs(abs(d.vertices[i].co.x) - DRUM_S * X_FACE) < 0.0006
                 and rr(i) < DRUM_S * R_FACE + 0.002]
    face_r = max(rr(i) for i in face_flat)
    lip_r = max(rr(i) for i in mat_v[HIDE] if abs(d.vertices[i].co.x) > DRUM_S * (LIP_XC - 0.03))   # t7: not the hardware
    collar_x = [abs(d.vertices[i].co.x) for i in mat_v[COLLAR]]
    s = objs["SM_DKP_Taiko_Stand"].data
    felt_v = set()
    for pl in s.polygons:
        if s.materials[pl.material_index].name == HIDE:
            felt_v.update(pl.vertices)
    sad, felt_top = [], []
    for v in s.vertices:
        if CRADLE_X0 - 0.01 < abs(v.co.x) < CRADLE_X1 + 0.01 and abs(v.co.y) < CRADLE_FLAT_Y + 1e-3 and v.co.z > 0.6:
            g = math.hypot(v.co.y, v.co.z - DRUM_Z) - body_R(abs(v.co.x))
            if v.index in felt_v:
                felt_top.append(g)
            else:
                sad.append(g)
    xin, yin = POST_X - POST_W / 2, POST_Y - POST_W / 2
    r_at = body_R(xin)
    post_clear = (DRUM_Z - math.sqrt(r_at * r_at - yin * yin)) - post_top()
    # ring handle clearance to the barrel (min over ring vertices of radius - body radius at their x)
    ring_gap = []      # t7: the hardware is on the hide atlas (M_DJ_Iron is gone from the drum); see ring_handles
    for i in mat_v.get(IRN, ()):
        co = d.vertices[i].co
        if abs(co.x) < 0.1 and abs(co.y) > DRUM_S * R_BELLY - 0.05 and co.z < -0.0:
            ring_gap.append(math.hypot(co.y, co.z) - body_R(abs(co.x)))
    drum_inst = next(i for i in instances if i["piece"] == "SM_DKP_Taiko_Drum")
    stand_inst = next(i for i in instances if i["piece"] == "SM_DKP_Taiko_Stand")
    stk = out["pieces"]["SM_DKP_Taiko_Stick"]
    sv = objs["SM_DKP_Taiko_Stick"].data.vertices
    stick_d = [2 * max(math.hypot(v.co.y, v.co.z) for v in sv if abs(v.co.x - xx) < 0.03) for xx in (0.0, STICK_L)]
    tk = drum_meta["tacks"]
    out["summary"] = {
        "drum_belly_diameter_m": round(2 * belly, 4),
        "drum_head_flat_face_diameter_m": round(2 * face_r, 4),
        "drum_lip_outer_diameter_m": round(2 * lip_r, 4),
        "drum_length_m": out["pieces"]["SM_DKP_Taiko_Drum"]["dims"][0],
        "drum_length_over_belly": round(out["pieces"]["SM_DKP_Taiko_Drum"]["dims"][0] / (2 * belly), 3),
        "collar_x_range_m": [round(min(collar_x), 4), round(max(collar_x), 4)] if collar_x else None,
        "t6_design_scale": DRUM_S, "t6_design_units_note": "x / radius constants and flap_tabs are DESIGN units (real = "
        "x t6_design_scale); every other value here is real metres",
        "flap_root_x_m": round(DRUM_S * X_ROOT, 4), "skirt_root_x_m": round(DRUM_S * X_SK, 4),
        "flap_tabs": drum_meta["tabs"],
        "tacks_total": len(tk), "tacks_per_head": N_TACKS,
        "tack_dome_diameter_range_m": [round(2 * min(t[3] for t in tk), 4), round(2 * max(t[3] for t in tk), 4)],
        "tack_tris_each": TACK_SIDES * (1 + 2 * len(TACK_PROF)), "tacks_per_row": TACKS_PER_ROW, "tack_rows_per_head": 2,
        "tack_row_x_m": [round(DRUM_S * (X_TACK - TACK_ROW_DX / 2), 4), round(DRUM_S * (X_TACK + TACK_ROW_DX / 2), 4)],
        "ring_handles": drum_meta["rings"],
        "ring_outer_diameter_m": round(2 * DRUM_S * (RING_R + RING_T), 4), "ring_tube_diameter_m": round(2 * DRUM_S * RING_T, 4),
        "ring_min_gap_to_barrel_m": round(min(ring_gap), 4) if ring_gap else None,
        "drum_centre_above_stand_base_m": DRUM_Z,
        "drum_bottom_above_stand_base_m": round(DRUM_Z - belly, 4),
        "drum_top_world_z": drum_inst["bbox_min_max"][5],
        "drum_top_above_plinth_m": round(drum_inst["bbox_min_max"][5] - PLINTH_TOP, 4),
        "pavilion_eave_z_spec": 3.25, "clearance_drum_top_to_eave_m": round(3.25 - drum_inst["bbox_min_max"][5], 4),
        "stand_footprint_xy_m": out["pieces"]["SM_DKP_Taiko_Stand"]["dims"][:2],
        "stand_height_m": out["pieces"]["SM_DKP_Taiko_Stand"]["dims"][2],
        "stand_world_bbox": stand_inst["bbox_min_max"],
        "saddle_wood_vertex_gap_min_max_m": [round(min(sad), 4), round(max(sad), 4)] if sad else None,
        "saddle_felt_vertex_gap_min_max_m": [round(min(felt_top), 5), round(max(felt_top), 4)] if felt_top else None,
        "post_top_below_drum_surface_m": round(post_clear, 4), "post_top_z_m": round(post_top(), 4),
        "stick_length_m": stk["dims"][0], "stick_diameter_grip_strike_m": [round(x, 4) for x in stick_d],
        "stick_length_over_diameter": [round(STICK_L / x, 2) for x in stick_d],
        "stick_poses": [i["pose"] for i in instances if i["piece"] == "SM_DKP_Taiko_Stick"],
        "tris": {k: v["tris"] for k, v in out["pieces"].items()},
        "t4_body_profile": {
            "source": "taiko_uv.body_r (traced from References/Dojo/taiko_tacks_ref_user.webp, t4/ref_profile.json)",
            "belly_diameter_mesh_m": round(2 * belly, 4), "head_lip_outline_diameter_m": round(2 * DRUM_S * UVL.BODY_RC, 4),
            "head_over_belly": round(DRUM_S * UVL.BODY_RC / belly, 4),
            "belly_over_body_at_hem_line_real_x%.3f" % (DRUM_S * SK_HEM_X_MIN): round(belly / body_R(DRUM_S * SK_HEM_X_MIN), 4),
            "belly_over_body_at_skirt_root_real_x%.3f" % (DRUM_S * X_SK): round(belly / body_R(DRUM_S * X_SK), 4),
            "t6_crown_half_length_over_belly_radius": round(UVL.BODY_LC / R_BELLY, 4),
            "diameter_over_belly_at_x_over_crown_half_length": {"%.2f" % f: round(body_r(f * UVL.BODY_LC) / R_BELLY, 4)
                                         for f in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)},
            "length_over_belly": round(out["pieces"]["SM_DKP_Taiko_Drum"]["dims"][0] / (2 * belly), 3)},
        "drum_ucx": drum_meta.get("ucx"),
    }
    return out


main()
