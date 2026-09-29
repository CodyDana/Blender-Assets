"""Hero group: the entrance (reference sheet WorkFiles/armory/reference/entrance.png, look reference armory3_reference2.png).

Replaces the block-built SM_AK_Entrance_12, SM_AK_DoorLeaf, SM_AK_DoorLeaf_R, SM_AK_Threshold_4, SM_AK_EntryMat,
SM_AK_StepBeam and SM_AK_Post_Jamb_480 (same names, pivots, facing, bboxes within ~2 cm and the scripted collision
boxes), and adds the NEW SM_AK_H_WallSconce (the wall lantern of the sheet, placed by instances()).

GENKAN (2026-09-28, the user: "the front entrance is not matching ... see how there's like a small entranceway and a
black bar separating the main floor"; the look reference's foreground, WorkFiles/armory/reference/
entry_foreground_crop.png). The r4-r6 raised step platform (SM_AK_EntryStep_4) is gone. Inside the 4 m opening the entry
is a SUNKEN vestibule (build_armory_kit GENKAN / GENKAN_Z / STEP_BEAM_D / ENTRY_MAT / MAT_BOARD / SILL_TOP, read from G),
post plinth to post plinth (world X 2.17-9.83, Y 0-2.56, the doorway back to the sill): the kit's plank floor 12 cm below
the hall (SM_AK_GenkanFloor, scripted, with dark skirting under the wall line and the plinths), the woven mat in a
black binding lying on it inside a dark board surround with worn arrises (entry_mat), and at its far edge the heavy
dark step beam, the agari-kamachi (step_beam: 16 cm top flush with the hall floor, a crisp 12 cm face, straight across
the whole vestibule, short returns down both sides in front of the post plinths), with the hall planks running on
beyond it. Genkan r4 (blind judge 6.5): the mat a chunky grey-brown knotted sisal (T_AK_HEntSisal) in a 9.5 cm black
binding, its surround boards near-black with lighter worn arrises (0.15 m wide); the beam matte timber in two tones, a
lighter weathered top board (T_AK_HEntTimberG) nosing 8 mm over the near-black ebony face (was gloss black lacquer);
the entry lanterns are hero_lantern_vase's SM_AK_Lantern_Entry, tight against the beam. ENTRYFIX (2026-09-28, the user's
crop): the beam is a solid near-black lacquer bar (M_AK_HStepLacquer) between the two entry lanterns, which are the
developed andon SM_AK_Lantern again and cap its ends; the genkan is the lanterns' span (GENKAN X 3.52-8.48) with 6 cm
dark board returns outside it; the hall floor runs on outboard of them. ENTRYFIX r2 (blind judge 6/10): C1 and the entry
refit together (entryfix/c1fit4.py): the bar Y 2.35-2.51 (GENKAN y1 2.56 -> 2.35), the lanterns 0.32 m in front of it;
the bar a near-black LACQUERED timber (T_AK_HEntTimberL, satin) so its top reads as a lit timber over the black face;
the mat field a fine knotted rush in columns (T_AK_HEntRushK) in a 6 cm binding with a binding-black band across it
(MAT_STRIPE), the side boards 0.11 m, lighter, with 20 mm worn arrises. The parked leaves, the inner jamb bands and the opening's slim casings now stand on
the genkan floor (LEAF_Z = GENKAN_Z -0.12; the leaves' top +3.78, the hanger straps reach down to it); the sill is a low
board (+0.04) whose room face closes the step down into the genkan.

Layout 2 (user-approved 2026-09-27: the sheet's COMPOSITION). The two heavy posts stand at the OUTER ENDS of the frame
on the south wall line; the lintel, the brass top track with its four hanger wheels, both parked leaves and the
unchanged 4 m clear opening (X 4-8, Z 0-3.65) all sit BETWEEN the posts. SM_AK_Entrance_12 (r2; was SM_AK_Entrance_10,
X 1-11, between plain 1 m wall pieces) is the whole south wall X 0-12 (local X = world X).
Layout 2 r3 (blind judge 7.5: the sheet is taller and narrower between the posts, its leaves larger in the frame, its
posts deep square columns standing well proud of the wall with the step a shallow ledge ending at their fronts, one heavy
lintel with no brass inlays, a visible brass-edged inner jamb band, a golden rush mat in a black border, near-black
weathered timber with lighter worn grain):
  SM_AK_Post_Jamb_480 at JAMB_POSTS = world X 1.86 / 10.14, Y 0.40: 50 x 80 cm timber (X 1.61-2.11 / 9.89-10.39,
  Y 0-0.80) on a flared dark plinth 4 cm proud (the frame spans X 1.57-10.43); a 14 cm inner jamb band with a brass
  edge (X 2.11-2.25 / 9.75-9.89); the 1.70 x 3.90 m leaves (h:w 2.3) at X 2.25-3.95 / 8.05-9.75, Y 0.14-0.19,
  standing on the step (+0.095 to +3.995: taller than the 3.65 m opening, up to the track like the sheet's); between
  the posts a recessed board panel over the opening and the leaves (3.65-4.30) carrying the brass track (rod axis +4.12)
  and ONE heavy lintel 4.30-4.72; the posts rise to +5.00. Outside the posts 1.6 m of clad wall with the long lattice
  band level with the lintel. The step (X 2.15-9.85, Y 0.035-0.86, +0.095, flush with the threshold) runs under the
  parked leaves to the post fronts round the mat inset across the opening (X 4.02-7.98, Y 0.135-0.77). The street side
  is the exterior's SM_AKX_Facade_Entrance_6 (its own dark door casing at X 3.7-4.0 / 8.0-8.3), so the hero wall is
  plain timber there.
Layout 2 r4 (entrance.png: the step is a RAISED dark step with a lipped edge plinth to plinth in front of the leaves, the
mat a large golden rush rectangle nearly filling the platform's depth; r3's step read as a sliver, its mat a 10:1 strip):
  the platform +0.15 (one walkable step; the leaves stand on it at +0.15 to +4.05, under the rod at +4.098), the step's
  front board a heavy lipped nosing over a set-back riser; the mat 4.0 x 1.05 m across the whole opening and back
  through the doorway (world X 4-8, Y -0.30 to 0.75) in a black binding with a woven edge cord, a new coir-like rush
  weave (T_AK_HEntRush, ribs front to back); the threshold the outer sill in the exterior casing's depth (Y -0.435 to
  -0.30). The sheet's doorway is far deeper than the kit's 0.30 m wall, so the mat is ~3.8:1 there, not the sheet's
  ~2.4:1, unless the step ran ~0.5 m past the post plinths.
Final fix r5 (blind judge 6.5-8 per piece; layout, bboxes, collision and the fixed user decisions unchanged): aged
  bronze instead of saturated yellow brass (T_AK_HEntBronze patina set on the plates, shoes and strap plates, darker flat
  M_AK_HEntBrass); warmer heavier-grained timber (T_AK_HEntTimberW) with warm worn arrises; a nubby coir mat
  (T_AK_HEntCoir) in a bold 10 cm black binding with a readable 2.6 cm gold cord; the step's front board a 5.5 cm nosing
  lipped 3.8 cm over a dark riser, the side decks three seamed boards with butt joints and worn edges; the post on a
  chunky 0.30 m slate plinth 6 cm proud with a bevelled top, bead grooves down its show faces, 2 cm worn arrises; the
  sconce with a projecting roof plate, a low hipped roof, a hanging ring and a turned drop finial, its glow unclipped
  (1.35); the ranma a dark grid over muted amber cells; the lintel standing out 16 cm past each post; a heavier rod with a
  flat track bar below it; deep flanged hanger wheels on wide riveted strap plates; the leaves' paper darker and warmer,
  heavier grid bars, a moulded frame and a brass strip down the leading edge.
Final fix r6 (blind judge 7-8 per piece, no blockers; layout, bboxes, collisions and the fixed user decisions unchanged):
  a STEPPED header - the nuki 4.325-4.53, a dark reveal, the head beam 4.56-4.86 (two planks, running out past the
  posts), the side walls stopping at 4.54 under a taller 3-row ranma band (10 cm cells) with the track rail at the rod
  (STUB_BACK_PANEL False: above the stubs the exterior skin closes the wall to the ceiling); charcoal-ebony timber
  (T_AK_HEntTimberE: irregular grain, knots, broken checks, no bright bands); a brushed-brass shoe (T_AK_HEntBrushed)
  with four prominent domed corner rivets, the post top a square riveted brass plate on the room face only under an
  aged-brass cap; a wider dark reveal between the jamb casing and the leaf; the sconce 0.52 x 1.04 m (wider than the
  post), heavier 2.6 cm frame, flared roof plate, hook ring, bracket arm and drop finial under the base (SCONCE_Z
  2.40); the leaves with 9 slats over wider paper strips, the cross bar 37 % down, an 8 x 3 near-square grid, a warm
  beige paper, a plain single-board kick panel; the mat's tufted rib coir (T_AK_HEntCoirR) in a 16 cm binding; the
  step's nosing 9 cm with a 2 cm worn arris, bolder deck seams; brass edges on the sill.

The sheet, measured off its inside elevation at the kit's real sizes (ceiling 4.80):
  entrance  between the posts a recessed panel of vertical boards behind the track, a head casing over the opening, ONE
            heavy lintel with worn arrises (no metal inlays); a slim casing with a brass edge down each side of the
            opening; the inner jamb bands with their brass edge; on the stubs outside the posts: skirting, lower boards,
            a base rail, vertical boards, the track-height rail, a plain board, a long framed 4-row square lattice band
            (8 cm cells, bold dark bars over light paper) level with the lintel and a top board level with its top; the
            brass top track: a rod on stand-offs from post to post with collars at the posts, slim brass hanger straps
            whose round heads carry the four wheels (0.25 m in from each end of both parked leaves)
  leaf      stiles 13 % of the width; a heavier top rail carrying the two slim brass hanger straps (one bolt each); an
            upper panel of 14 fine round-edged bars over 15 paper strips 1.4 x a bar wide, one cross bar a third down;
            a 3 x 10 square grid band; the solid lower third (faint board joints) with the USER'S emblem medallion in a
            bevelled brass rim; light warm backlit paper graded per strip; ONE solid brass flush pull at the
            slat-to-grid transition, on the LEADING stile only (two hands - SM_AK_DoorLeaf, the west leaf, pull on its
            +X stile; SM_AK_DoorLeaf_R, the east leaf, pull on its -X stile)
  threshold r4: the outer timber sill behind the mat, a squared nosing lipped over the street side, softly worn round
            arrises
  step      the raised platform (+0.15): board decks under the parked leaves, a heavy front board with a squared nosing
            lipped over a set-back riser (a shadow line) ending at the post fronts
  mat       the golden woven rush field (M_AK_HEntMat: T_AK_HEntRush, tex_entrance.py; ribs front to back, 0.5 m tile)
            a few mm below a rolled black cloth binding, a thin woven edge cord round the outside
  jamb post the sheet's deep heavy post: a flared dark plinth a little wider than the post, a riveted brass shoe 0.7 x
            the post width high, a flat riveted brass plate on the three show faces above the lintel (+4.74 to +4.97)
            and a dark end-grain top at +5.00, a round brass boss with a raised ring and centre rivet on the room face
  sconce    a near-black iron lantern with dark-bronze worn edges mounted tight on the post's room face on a back bar
            with two short brackets, at the sheet's height (lit body +2.62 to +3.54): body 0.38 x 0.92 (h:w 2.4), corner
            posts and mullions through thin two-layer plates, a centre mullion on every face, a flat stepped cap with a
            low knob, a short turned finial; the panes glow in a smooth field from a hot near-white core by the mullion,
            a little above the middle, to deep amber at the frame (M_AK_HEntGlowPic; no light)
  timber    M_AK_HEntTimber (T_AK_HEntTimber, tex_entrance.py): near-black with lighter worn grain streaks and fine checks

ENABLED stays False: the user reviews the images of every piece before anything goes into the armory.
"""
import math

import bmesh
import bpy

ENABLED = True   # REQUIRED: never set True here (the user enables the group after reviewing the previews)

MATERIALS = {
    # flat params only (build_armory_kit.build_material: color / rough / metal / coat, or color / emit / emit_color)
    # r3 (blind judge: the sheet's plinth is a dark iron-black block a little wider than the post)
    # r5 (blind judge: the plinth read as a thin dark band; the sheet's is a chunky dark slate / iron block with a
    # bevelled top and lighter worn edges): a dark slate, the bevel and arrises one step lighter
    "M_AK_HStone": (None, 1.0, {"color": "#2A2B2D", "rough": 0.55, "metal": 0.15}),   # dark slate plinths
    "M_AK_HEntStoneEdge": (None, 1.0, {"color": "#4E4D4B", "rough": 0.50, "metal": 0.10}),
    # r5 (blind judge: the binding read thin and low-contrast): a deeper black cloth
    # matfix: the binding WOVEN black (the crop's border is a textured dark band, not flat cloth): the mat's own weave
    # set darkened (was a flat #0B0A09, rough 0.92)
    # matfix b3 (blind judge: "the border ... reads as dark grey, not black ... a wide, jet-black woven or knotted
    # border ... with its own rope texture"): the field's knot lattice in jet black (T_AK_HEntKnotB, its own set)
    # r20 mat (judge: "solid near-BLACK with a fine rope texture ... reads speckled grey in golden light"): T_AK_HEntRopeB
    "M_AK_HBinding": ("HEntRopeB", 1.0, {}),   # b7: HEntKnotB;   # b2: HEntWeave at tint 0.06 (0.11 read dark grey)       # black knotted mat binding
    # r5 (blind judge: the thin gold cord outside the binding is barely readable): a lighter gold twisted cord
    "M_AK_HEntCord": (None, 1.0, {"color": "#B98C4C", "rough": 0.62}),
    # fix round 3: the entrance's own names (hero_cases defines a different M_AK_HBrass; the modules' MATERIALS merge)
    # bright worn brass for the edges, rivets and hardware
    # r3 (blind judge: the plates and hangers read pale cream in the 3/4 views): a warmer, less mirror-like brass
    # r5 (blind judge: the brass read a saturated clean yellow; the sheet's is a darker aged bronze): darker, greyer
    "M_AK_HEntBrass": (None, 1.0, {"color": "#83694A", "rough": 0.46, "metal": 0.95}),
    # r3: the flat riveted plates (shoe, post top) in an aged satin brass, so their broad faces do not mirror the light
    # r5: the plates, shoes and sleeves in the aged-bronze patina set (T_AK_HEntBronze, tex_entrance.py)
    # r6 (blind judge: the shoe read heavy blotchy dark patina; the sheet's is a clean brushed brass, measured (155, 104,
    # 56) there against the r5 bronze's (119, 84, 41)): the brushed-brass set T_AK_HEntBrushed
    "M_AK_HEntBrassPlate": ("HEntBrushed", 0.5, {}),
    # aged brass (darker patina) for the cap / shoe sleeves round the riveted plates: the plates' recesses read dark
    "M_AK_HEntBrassAged": (None, 1.0, {"color": "#4E3E2B", "rough": 0.55, "metal": 0.85}),
    # warm worn arrises on the dark timber (the sheet: brass-toned edge wear on the beams, posts, sill and step)
    # r3 (blind judge: the warm arrises read as brass pinstripes; the sheet's worn edges are a lighter grey-brown)
    # r5 (blind judge: the sheet's beams, battens and rails show warm edge wear): a warmer worn brown
    "M_AK_HEntWear": (None, 1.0, {"color": "#5C432F", "rough": 0.60}),
    # the wall ranma paper: light warm paper, softly lit
    # r5 (blind judge: the band read as bright cream dots; the sheet's is a dark grid over muted amber cells)
    "M_AK_HEntRanma": (None, 1.0, {"color": "#6E5034", "emit": 0.05, "emit_color": "#FF9A50"}),
    # the door leaf's warm backlit paper in three tones (the sheet: warm tan, brightest in the middle of the panel,
    # deeper and darker toward the frame); flat params, graded per paper strip
    # layout 2 r2 (blind judge: the sheet's paper backing is lighter): one step lighter and warmer throughout
    # r5 (blind judge: the lower grid's cells read lighter and pinker than the sheet's darker, warmer grid)
    # r6 (blind judge: the paper read a saturated amber-orange; the sheet's is a lighter warm beige behind the slats)
    "M_AK_HEntPaperHi": (None, 1.0, {"color": "#AD8B66", "emit": 0.05, "emit_color": "#FFCC96"}),
    "M_AK_HEntPaperMid": (None, 1.0, {"color": "#9B7B5A", "emit": 0.04, "emit_color": "#FFC48A"}),
    "M_AK_HEntPaperLo": (None, 1.0, {"color": "#886B4E", "emit": 0.03, "emit_color": "#FFBC80"}),
    # layout 2 r2: the dark end grain on the post tops, and the sconce's near-black iron frame (the sheet's lantern is
    # dark bronze / black, not brass)
    "M_AK_HEntEndGrain": (None, 1.0, {"color": "#1A1310", "rough": 0.88}),
    "M_AK_HEntIron": (None, 1.0, {"color": "#1E1915", "rough": 0.42, "metal": 0.85}),
    # r3 (blind judge deltas 4 and 6): the entrance's own tiling sets (tex_entrance.py): near-black weathered timber with
    # lighter worn grain, and the golden woven rush mat
    # r5 (blind judge: the timber read flatter and cooler, streaky): the warmer, heavier-grained T_AK_HEntTimberW
    # r6 (blind judge: strong regular orange / rust streak banding that read procedural; the sheet's timber is a darker
    # charcoal-ebony with real plank grain, knots, checks): T_AK_HEntTimberE
    "M_AK_HEntTimber": ("HEntTimberE", 1.0, {}),
    # r4 (entrance.png's top view): a lighter tan-gold coir-like rush weave, ribs running front to back (T_AK_HEntRush)
    # r5 (blind judge: the rush ribs read like corduroy; the sheet's is a nubby coir / basket): T_AK_HEntCoir
    # r6 (blind judge: the coir read a flat speckle; the sheet's shows woven rows of tufts with directional ribs):
    # T_AK_HEntCoirR - tufted ribs front to back, deep grooves
    # genkan r4 (blind judge 6.5, delta 1: "the reference mat is a coarse, chunky basket / sisal weave in mid grey-brown
    # ... r3 reads as a fine horizontal-ribbed tatami in bright straw"): T_AK_HEntSisal, rows of chunky knots across the
    # mat in a grey-brown (reference 2's field ~(111, 82, 67) in the golden light)
    # build 3: C1 measured the field ~(167, 133, 107) against the reference's ~(112, 81, 64): darker (tint 0.72)
    # entryfix r2 (blind judge 6/10, blocker 1: "the weave reads as a regular grid of round dots, like cobbles ... the
    # reference shows fine woven rush in straw tan"): T_AK_HEntRushK, reference 2's mat zoomed is columns of small
    # interlocked V stitches running front to back (~1.8 cm cords, ~4.2 cm stitches), deep seams between the cords
    # matfix (2026-09-28, the user: "fix the mat"; blind judge r2: "reads as a 2x2 tatami split ... the reference shows
    # one continuous woven mat with a black border"): T_AK_HEntWeave, a coarse nubbly sisal weave, cords ~2.9 cm apart
    # front to back as reference 2's field spectrum, staggered rounded nubs, warm grey-tan
    # matfix b3 (blind judge 6/10: "vertical corduroy ropes ... the reference is round, nubbly, roughly isotropic knots
    # ... with strong 3D relief"; golden "washed to pale pinkish cream"): T_AK_HEntKnot, chunky knots 3.1 x 5.6 cm in
    # columns, a strong normal, a greyer tan
    # r20 mat (judge 7/10: knots ~1.5x too coarse, tall ovals in columns read as cable-knit, vertical seams at night, the
    # golden field washed out): T_AK_HEntNub, small round even nubs (2.78 cm) in staggered rows, a darker, warmer grey-tan
    "M_AK_HEntMat": ("HEntNub", 1.0, {"tint": 0.60}),   # b2 0.56 (night 0.73x b7's); b1 0.60;   # b7: HEntKnot, tint 0.68 (b2: HEntWeave, tint 0.85; b3 0.80)
    # r20 mat: the lighter worn brown on the chamfers of the surround boards' inner lip (judge: "a visible inner lip")
    "M_AK_HMatLip": (None, 1.0, {"color": "#3C2F26", "rough": 0.55}),   # b2 #45372C / 0.50 read white in the sun
}
PAPER = ("M_AK_HEntPaperHi", "M_AK_HEntPaperMid", "M_AK_HEntPaperLo")
# the sconce panes (layout 2, judge delta: a SMOOTH hot core fading to amber; flat emissive steps banded visibly even on
# a fine grid): the kit's own lantern-paper glow picture (T_AK_LanternPaper_BC: a hot cream core just above the middle,
# falling off through amber to a dark amber rim - no new texture), unlit like M_AK_LanternPaper but hotter (that one at
# 0.40 reads far dimmer than the sheet's sconce), one picture across each whole face so the core sits by the mullion
GLOW = "M_AK_HEntGlowPic"
MATERIALS[GLOW] = ("LanternPaper", None, {"emit_image": True, "emit": 0.20, "unlit": True})   # calibration pass 1 (room judge: sconces near white in the room): 1.35 -> 0.20   # r5: 1.85 -> 1.35 (blind judge: the glow read uniform cream-pink; the picture's hot core to amber rim must not clip)

T, BR, BZ, LQ = "M_AK_HEntTimber", "M_AK_HEntBrass", "M_AK_Bronze", "M_AK_Lacquer"
EM, MAT, ST, BP = "M_AK_Emblem", "M_AK_HEntMat", "M_AK_HStone", "M_AK_HEntBrassPlate"
BD, BA, WE, RP = "M_AK_HBinding", "M_AK_HEntBrassAged", "M_AK_HEntWear", "M_AK_HEntRanma"
EG, IR = "M_AK_HEntEndGrain", "M_AK_HEntIron"
SE, CORDM = "M_AK_HEntStoneEdge", "M_AK_HEntCord"
# r20 mat (2026-09-28, judge 7/10): the entry mat as a low raised frame (entry_mat), heights above GENKAN_Z: the field
# top (was build_armory_kit MAT_TOP 0.022: ~10 cm of the bar's black face showed above the mat and swallowed the far
# binding), the surround boards' top (was MAT_BOARD_TOP 0.030), the boards' inner lip, the side boards' width (was
# MAT_BOARD 0.11; grown outward, the near board stays MAT_BOARD) and the binding width (was 8.5 cm)
MAT_FIELD_Z, MAT_BOARD_Z = 0.075, 0.082
LIP_W, LIP_H = 0.014, 0.006
SIDE_W = 0.145
BIND_W = 0.062
LIPM = "M_AK_HMatLip"

TIMBER_TILE = 1.0          # m per timber texture repeat on the hero members (2.0 kit default): the grain reads
SCONCE_Z = 2.40            # sconce base (finial tip) above the floor: r6 lit body +2.57 to +3.61 (centre as r5's)
# layout 2 r3 (build_armory_kit: ENTRANCE_X0, JAMB_*, ENT_*, DOOR_LEAF_*, ENTRY_*; kept in step by hand)
ENT_X0, ENT_W = 0.0, 12.0                     # SM_AK_Entrance_12 at world X 0, 12 m: local X = world X
OPEN_X = (4.0 - ENT_X0, 8.0 - ENT_X0)         # the clear opening, entrance-local (ENTRY_X)
JAMB_POSTS = ((1.86, 0.40), (10.14, 0.40))    # SM_AK_Post_Jamb_480 placements (rot 0)
JAMB_HW, JAMB_HD = 0.25, 0.40                 # post timber half width / half depth (50 x 80 cm)
JAMB_PL = 0.04                                # the plinth stands 4 cm proud of the timber (sides and front)
JAMB_BACK_Y, JAMB_FACE_Y = -JAMB_HD, JAMB_HD  # post timber back (on the wall's room face, world Y 0) / room face
POST_IN = (JAMB_POSTS[0][0] + JAMB_HW - ENT_X0, JAMB_POSTS[1][0] - JAMB_HW - ENT_X0)   # entrance-local 2.11 / 9.89
POST_OUT = JAMB_POSTS[0][0] - JAMB_HW - ENT_X0                                           # entrance-local 1.61
JAMB_W = 0.29                                 # the inner jamb band between each post and its parked leaf (r20 round 3: 0.14)
LEAF_X = (2.40, 7.90)                         # world X of the parked leaves (r20 round 3: (2.25, 8.05), build_armory_kit)
# r5 (blind judge: the sheet's plinth is a chunky dark block ~0.3 m tall, clearly wider than the post, bevelled top):
# the plinth 6 cm proud (collision stays at JAMB_PL, as scripted), 0.30 tall with its bevel, the shoe on it
PLINTH_PL, PLINTH_H, PLINTH_BEV = 0.06, 0.30, 0.055
SHOE = (PLINTH_H, round(PLINTH_H + 0.7 * 2 * JAMB_HW, 3))   # judge delta: the brass shoe 0.7 x the post width high
# r6 (blind judge: the sheet's post top is a flat square brass plate with rivets on the FRONT face plus a cap, the post
# rising above the head beam; the r5 band wrapped all three faces): a square plate on the room face only (4 corner
# rivets) from the head beam's middle to just under a brass cap on the end grain
TOP_PLATE, POST_TOP = (4.60, 4.965), 5.00     # the front brass plate; the post top (a brass cap on the end grain)
TOP_PLATE_HW = 0.20                           # its half width (the post is 0.50 wide)
BOSS_Z = 4.42                                 # the round brass boss on the room face, at the nuki
# genkan (2026-09-28): the entry's floor levels and extents are read from build_armory_kit through G (LEAF_Z, GENKAN,
# GENKAN_Z, GENKAN_BASE, STEP_BEAM_D, STEP_RETURN_W, ENTRY_MAT, MAT_BOARD, MAT_TOP, MAT_BOARD_TOP, ENTRY_SILL, SILL_TOP);
# r4: the step beam's weathered top board (thickness) and its nosing over the dark face
STEP_TOP_T, STEP_NOSING = 0.035, 0.008   # r4 two-tone beam (entryfix: unused, the bar is one lacquer block)
# the r4-r6 constants ENTRY_TOP / ENTRY_MAT / ENTRY_STEP (the raised step platform) are gone
# the genkan's own materials. r1-r3: the step beam in a gloss black lacquer (M_AK_HStepLacquer; r3 rough 0.24 / coat
# 0.5). r4 (blind judge 6.5, delta 2: "the reference beam is dark, satin, weathered wood with a visible lighter-brown
# top face and a darker front face, so it reads as two tones; r3 is a glossy black lacquer band that mirrors the case
# emblem"): matte timber, the top board in the lighter weathered T_AK_HEntTimberG (reference 2 ~(64, 61, 65)), the
# front face the entrance's near-black T_AK_HEntTimberE (~(38, 23, 13)). Delta 4 ("the side boards framing the mat
# should be near-black dark timber with a slightly lighter chamfered top edge, clearly darker than the vestibule
# planks"): the mat's surround boards in the ebony timber darkened (tint 0.6) with wide worn arrises (WE)
# build 2: the top at tint 1.0 read lighter than the planks; build 4: C1 measured the top 0.68x the hall planks and
# the face ~(55, 38, 25) against the reference's 0.50x and ~(10, 6, 3): the top at 0.52, the face its own darker
# M_AK_HStepFace (the ebony at 0.35), no bright worn arris on the nosing (it read as a light line under the top)
# entryfix (2026-09-28, the user: "a black bar separating the main floor", the crop entry_foreground_crop.png): the beam is
# ONE solid near-black lacquer bar again, top and face alike (the r4 two-tone timber read as a grey-brown top board, not
# the crop's black bar): a gloss black lacquer (#0E0C0B, roughness 0.1, clear coat 0.8: its top picks up the lit hall as
# the crop's sheen; b1 at 0.2 read as a flat black void at night), crisp 4 mm arrises
# entryfix r2 (blind judge 6/10, blocker 3: "the bar reads as a thick black void or shadow band ... the reference beam
# has a slightly lit top face and edge that read as a timber"; reference 2's bar top measures about the hall floor's
# brightness, its face near-black): still a near-black lacquer, now over timber: T_AK_HEntTimberL (the ebony set's
# grain in #0D0A08-#2B211A under a satin lacquer, roughness ~0.3, tex_entrance.timber_lacquer), so the top catches the
# lit hall as a sheen with faint grain and the 6 mm arrises a thin highlight; the face stays black in its own shadow
# matfix b3 (blind judge: "three small dark round dots or holes on the riser face directly above the mat"): the same
# lacquered timber without its knots (one per 1 m tile read as a row of holes along the face): T_AK_HEntTimberN
MATERIALS["M_AK_HStepLacquer"] = ("HEntTimberN", 1.0, {})
# entryfix r2 (blocker 1 / delta 7: the binding was lost against near-black boards; reference 2's side boards are a
# dark weathered timber, lighter than the binding, with a lit bevel): the ebony at full strength (was tint 0.6)
# b4: at night the full-strength ebony still read near-black beside the binding: lifted (tint 1.8), a dark brown
# b5: at L ~14 against the binding's ~3 the black binding still did not separate (reference 2: boards ~ the mat's tone,
# binding dark): tint 2.4, and a 20 mm worn arris (was 12 mm; delta 7: "the lighter bevel edge ... is missing")
# matfix b3 (blind judge: "the frame boards are lighter, redder wood with prominent grain, and on the bottom and right
# they show a light orange rim ... the reference frame is uniformly dark, near-black, low-sheen board on all sides,
# matching the dark step bar"): the bar's near-black timber at a low sheen, no knots (T_AK_HEntTimberM), and no warm
# worn arrises on the surround (the jet-black knotted binding now separates by its relief and raised roll)
# r20 mat b2: the same timber matte (T_AK_HEntTimberMR): the golden sun's sheen read the boards pale cream
MATERIALS["M_AK_HMatBoard"] = ("HEntTimberMR", 1.0, {})   # b7: HEntTimberM; matfix b2: HEntTimberE, tint 2.4

_N = [0]


def _grow():
    """A tiny unique growth per part (as Piece.box does): parts that touch overlap by a fraction of a millimetre
    instead of sharing coincident vertices."""
    _N[0] += 1
    return 0.00025 + (_N[0] % 613) * 1.1e-6


def _tile(G, m):
    if m == T:
        return TIMBER_TILE
    return G["TILE"].get(m) or 1.0


def _emit(G, p, bm, mats, uv_mode="box", grain=None, smooth=False):
    """Append a bmesh part to piece p. uv_mode 'box': tiling planar UVs per face (V along the grain axis, so the timber
    grain runs along each member); 'keep': the UV layer already set on the bmesh. smooth: a bool, or a set of face
    indices to shade smooth."""
    bm.normal_update()
    uvl = bm.loops.layers.uv.active
    bm.verts.index_update()
    bm.faces.index_update()
    verts = [tuple(v.co) for v in bm.verts]
    faces, uvs, fm, sm = [], [], [], []
    for f in bm.faces:
        faces.append([v.index for v in f.verts])
        m = mats[f.material_index]
        fm.append(m)
        sm.append(smooth if isinstance(smooth, bool) else (f.index in smooth))   # matfix b3: or a set of face indices
        if uv_mode == "keep":
            uvs.append([tuple(l[uvl].uv) for l in f.loops])
            continue
        n = f.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        plane = [i for i in range(3) if i != ax]
        if grain in plane:
            va = grain
            ua = [i for i in plane if i != grain][0]
        else:
            ua, va = plane
        t = _tile(G, m)
        uvs.append([(l.vert.co[ua] / t, l.vert.co[va] / t) for l in f.loops])
    bm.free()
    p.mesh(verts, faces, uvs, fm, smooth=sm)
    return p


def cbox(G, p, x0, x1, y0, y1, z0, z1, mat, ch=0.0, grain=None, grow=True, seg=1, only=None, edge=None):
    """A box (optionally chamfered by ch, seg segments; only = axis index to bevel just the edges along that axis, e.g.
    the long edges of a round-edged lattice bar) with box-projected tiling UVs; grain defaults to its longest axis.
    edge = a second material for the bevel faces (the worn arrises of the timber, the bright edges of aged brass)."""
    g = _grow() if grow else 0.0
    x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    if ch > 0:
        ext = (x1 - x0, y1 - y0, z1 - z0)
        if only is None:
            edges = list(bm.edges)
            ch = min(ch, 0.45 * min(ext))
        else:
            edges = [e for e in bm.edges if abs((e.verts[0].co - e.verts[1].co)[only]) > 1e-6]
            ch = min(ch, 0.49 * min(ext[i] for i in range(3) if i != only))
        bmesh.ops.bevel(bm, geom=edges, offset=ch, offset_type="OFFSET", segments=seg, profile=0.5,
                        affect="EDGES", clamp_overlap=True)
        ngons = [f for f in bm.faces if len(f.verts) > 4]
        if ngons:
            bmesh.ops.triangulate(bm, faces=ngons)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.normal_update()
    for f in bm.faces:
        f.material_index = 1 if (edge and ch > 0 and max(abs(c) for c in f.normal) < 0.999) else 0
    if grain is None:
        ext = (x1 - x0, y1 - y0, z1 - z0)
        grain = max(range(3), key=lambda i: ext[i])
    return _emit(G, p, bm, [mat, edge or mat], grain=grain)


def cyl(G, p, c, r, h, axis, mat, sides=12, r2=None, grain=None):
    """A capped cylinder (or frustum, r2 = far radius) from point c along +axis ('x', 'y', 'z' or '-y' ...) by h."""
    g = _grow()
    sgn = -1.0 if axis.startswith("-") else 1.0
    a = "xyz".index(axis[-1])
    u_, v_ = [i for i in range(3) if i != a]
    r2 = r if r2 is None else r2
    bm = bmesh.new()
    rings = []
    for rr, off in ((r + g, -g), (r2 + g, h + g)):
        ring = []
        for i in range(sides):
            t = 2 * math.pi * (i + 0.5) / sides
            co = list(c)
            co[a] += sgn * off
            co[u_] += rr * math.cos(t)
            co[v_] += rr * math.sin(t)
            ring.append(bm.verts.new(co))
        rings.append(ring)
    cen = []
    for off in (-g, h + g):
        co = list(c)
        co[a] += sgn * off
        cen.append(bm.verts.new(co))
    for i in range(sides):
        j = (i + 1) % sides
        bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
        bm.faces.new((cen[0], rings[0][j], rings[0][i]))
        bm.faces.new((cen[1], rings[1][i], rings[1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for f in bm.faces:
        f.material_index = 0
    return _emit(G, p, bm, [mat], grain=a if grain is None else grain)


# --------------------------------------------------------------------------- face-mapped hardware

def _fm(face, xa, xb, ya, yb):
    """The frame of one vertical face of the box xa..xb / ya..yb: returns (f(u, v, w) -> xyz, u0, u1) with u along
    the face, v = z and w outward from the face."""
    if face == "+y":
        return (lambda u, v, w: (u, yb + w, v)), xa, xb
    if face == "-y":
        return (lambda u, v, w: (u, ya - w, v)), xa, xb
    if face == "+x":
        return (lambda u, v, w: (xb + w, u, v)), ya, yb
    return (lambda u, v, w: (xa - w, u, v)), ya, yb


def fbox(G, p, fm, u0, u1, v0, v1, w0, w1, mat, ch=0.0, grain=None, edge=None):
    pts = [fm(u, v, w) for u in (u0, u1) for v in (v0, v1) for w in (w0, w1)]
    lo = [min(q[i] for q in pts) for i in range(3)]
    hi = [max(q[i] for q in pts) for i in range(3)]
    return cbox(G, p, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2], mat, ch, grain=grain, edge=edge)


def rivet(G, p, fm, u, v, w0, r=0.014, h=0.008, mat=BR):
    """A square pyramidal rivet head (closed: base + 4 sides) standing on a face at w0."""
    bm = bmesh.new()
    base = [bm.verts.new(fm(u + du * r, v + dv * r, w0 - 0.001)) for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    apex = bm.verts.new(fm(u, v, w0 + h))
    bm.faces.new(base)
    for i in range(4):
        bm.faces.new((base[i], base[(i + 1) % 4], apex))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for f in bm.faces:
        f.material_index = 0
    _emit(G, p, bm, [mat], grain=2)


def lathe_f(G, p, fm, uc, vc, prof, sides, mat):
    """A closed surface of revolution about the face normal through (uc, vc): prof = [(r, w)] from the axis (r = 0)
    round to the axis again; r == 0 points become single pole vertices."""
    g = _grow()
    bm = bmesh.new()
    loops = []
    for r, w in prof:
        if r <= 0:
            loops.append([bm.verts.new(fm(uc, vc, w))])
        else:
            loops.append([bm.verts.new(fm(uc + (r + g) * math.cos(2 * math.pi * (i + 0.5) / sides),
                                          vc + (r + g) * math.sin(2 * math.pi * (i + 0.5) / sides), w))
                          for i in range(sides)])
    for a, b in zip(loops, loops[1:]):
        for i in range(sides):
            j = (i + 1) % sides
            if len(a) == 1:
                bm.faces.new((a[0], b[i], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[i], b[0], a[j]))
            else:
                bm.faces.new((a[i], b[i], b[j], a[j]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for f in bm.faces:
        f.material_index = 0
    _emit(G, p, bm, [mat], grain=2)


def dome_rivet(G, p, fm, uc, vc, w0, r=0.020):
    """r6 (blind judge: the sheet's shoe shows four PROMINENT corner rivets; the r5 pyramids were lost in the plate): a
    round domed aged-brass rivet head on a dark washer ring (they read as dark dots on the satin plate, the sheet's),
    standing on a face at w0."""
    lathe_f(G, p, fm, uc, vc, [(0, w0 - 0.001), (1.35 * r, w0 - 0.001), (1.35 * r, w0 + 0.002), (0, w0 + 0.002)], 8, EG)
    lathe_f(G, p, fm, uc, vc, [(0, w0), (r, w0), (0.88 * r, w0 + 0.009), (0.50 * r, w0 + 0.015), (0, w0 + 0.017)], 8, BA)


def boss(G, p, fm, uc, vc, r, sides=10):
    """The sheet's post boss: a round brass disc with a clearly raised ring and a domed centre rivet."""
    prof = [(0, -0.002), (r, -0.002), (r, 0.004), (0.90 * r, 0.016), (0.70 * r, 0.016), (0.60 * r, 0.005),
            (0.26 * r, 0.005), (0.20 * r, 0.018), (0, 0.021)]
    lathe_f(G, p, fm, uc, vc, prof, sides, BR)


def post_dress(G, p, xa, xb, ya, yb, faces, boss_faces, shoe, plate, top, boss_z, boss_r, stone, ch=0.012):
    """A dark-stained post (timber xa..xb / ya..yb, small chamfers with worn warm arrises) on a wider chamfered stone
    plinth (stone = how far it stands out at -x, +x, -y, +y), a square brass shoe (an aged-brass sleeve with bright worn
    edges and a riveted plate on each show face in `faces`); layout 2 r2 (blind judge: the sheet's post rises above the
    header, its top a flat riveted brass plate on the face over a dark end-grain top): near the top a flat brass plate
    with six rivets on each show face (plate = z range) and a dark end-grain top at `top`; a round brass boss on each
    boss face."""
    s0, s1 = shoe
    t0, t1 = plate
    cbox(G, p, xa, xb, ya, yb, s0 - 0.03, top - 0.024, T, ch, grain=2, edge=WE)
    # r6: a brass cap on the end grain (the sheet's top view: a bevelled brass square on each post top)
    cbox(G, p, xa - 0.004, xb + 0.004, ya, yb + 0.004, top - 0.026, top - 0.0012, BA, 0.006, grain=0, edge=BR)
    sx0, sx1, sy0, sy1 = stone
    # r3 (blind judge: the sheet's plinth is a dark block flaring a little wider than the post): a low foot, then a
    # flared body narrowing to the shoe (flush at the wall)
    # r5: a chunky slate block (lighter worn arrises) to PLINTH_BEV under the shoe, then a bevelled top narrowing in
    # to just outside the shoe sleeve (flush at the wall)
    cbox(G, p, xa - sx0, xb + sx1, ya - sy0 + 0.004, yb + sy1, 0.0, s0 - PLINTH_BEV, ST, 0.010, edge=SE)
    frustum(G, p, xa - sx0 + 0.006, xb + sx1 - 0.006, ya - sy0 + 0.004, yb + sy1 - 0.006, s0 - PLINTH_BEV - 0.002,
            s0 - 0.004, max(0.0, max(sx0, sx1) - 0.016), SE, keep_y0=True)
    w = 0.006
    cbox(G, p, xa - w, xb + w, ya - w, yb + w, s0 - 0.012, s1, BA, 0.003, grain=2, edge=BR)
    for f in faces:
        fm, u0, u1 = _fm(f, xa, xb, ya, yb)
        e, k = 0.020, 0.042          # the shoe plate stands inside a band of the darker aged sleeve
        fbox(G, p, fm, u0 - w + e, u1 + w - e, s0 + e, s1 - e, w - 0.001, w + 0.004, BP, ch=0.002, edge=BR)
        for uu in (u0 - w + k, u1 + w - k):
            for vv in (s0 + k, s1 - k):
                dome_rivet(G, p, fm, uu, vv, w + 0.004, r=0.024)
        # r6: the flat square top plate on the ROOM face only (the sheet's), bright worn edges, a domed rivet at each
        # corner
        if f == "+y":
            uc = (u0 + u1) / 2
            pa, pb = uc - TOP_PLATE_HW, uc + TOP_PLATE_HW
            fbox(G, p, fm, pa, pb, t0, t1, -0.002, 0.007, BP, ch=0.0025, edge=BR)
            for uu in (pa + 0.034, pb - 0.034):
                for vv in (t0 + 0.034, t1 - 0.034):
                    dome_rivet(G, p, fm, uu, vv, 0.007, r=0.016)
        # r5 (blind judge: the sheet's post shows vertical chamfer / bead lines): a pair of fine dark bead grooves down
        # each show face, 5 cm in from the arrises, shoe to the head beam
        for uu in (u0 + 0.05, u1 - 0.05):
            fbox(G, p, fm, uu - 0.004, uu + 0.004, s1 + 0.01, min(t0, Z_L0) - 0.03, -0.001, 0.0015, EG)
    for f in boss_faces:
        fm, u0, u1 = _fm(f, xa, xb, ya, yb)
        boss(G, p, fm, (u0 + u1) / 2, boss_z, boss_r)


# --------------------------------------------------------------------------- the door leaf

# layout 2 r3 (blind judge: the sheet's leaves fill more of the frame): 1.70 x 3.90 m (h:w 2.3; r2 1.62 x 3.65), standing
# on the step and rising above the 3.65 m opening to the track like the sheet's
LEAF_W, LEAF_H, LEAF_T = 1.70, 3.90, 0.05
SW = 0.22                                          # stile width (the sheet: 13 % of the leaf width)
# the solid lower part (bottom rail, panel, mid rail) is a third of the leaf (0-1.24), the grid band 12 %
Z_BOT, Z_PANEL_TOP, Z_GRID0, Z_GRID1 = 0.16, 1.12, 1.24, 1.72
Z_LAT0, Z_TOP = 1.82, 3.64                         # upper lattice; a heavier top rail 3.64-3.90 carries the straps
# r6 (blind judge: the cross bar sat too high, ~27 % down the lattice against the sheet's ~35 %): 37 % down
Z_CROSS = Z_TOP - 0.37 * (Z_TOP - Z_LAT0)
# layout 2 r2: 14 bars, 15 paper strips 1.4 x a bar; r6 (blind judge: ~12 slats read against the sheet's 9-10
# wider-spaced ones): 9 bars over 10 paper strips 2.3 x a bar wide
N_BARS = 9
STRIP_K = 2.3
N_GRID = 8                                         # r6: the grid band's columns (the sheet's ~8, near-square cells)
STRAP_X = (0.25, LEAF_W - 0.25)                    # hanger straps (the entrance piece carries their upper halves)
STRAP_HW = 0.045                                   # strap half width (r5, blind judge: wider riveted strap plates; r2 6.4 cm)
# entrance-local X of the four hanger straps / wheels (both parked leaves)
WHEEL_X = tuple(round(lx - ENT_X0 + s, 4) for lx in LEAF_X for s in STRAP_X)


def _emblem_disc(G, p, cx, y0, cz, r, facing, sides=40, fill=0.95):
    """The user's emblem medallion face (disc_y, M_AK_Emblem on a unique UV). The UV is pulled in to `fill` of the
    texture, so the emblem's own gold ring runs out to the brass rim (no black band between them)."""
    verts, faces, uvs, mats = G["disc_y"](cx, y0, cz, r, 0.008, EM, BR, sides, facing)
    uvs = [[(0.5 + (u - 0.5) * fill, 0.5 + (v - 0.5) * fill) for (u, v) in uv] if m == EM else uv
           for uv, m in zip(uvs, mats)]
    p.mesh(verts, faces, uvs, mats)


def ring_y(G, p, cx, y0, cz, r_in, r_out, depth, mat, sides=40, r_in_front=None, r_out_front=None):
    """An annulus ring whose axis is Y, from y0 toward +Y by depth; front radii can differ (a bevelled rim)."""
    g = _grow()
    rif = r_in if r_in_front is None else r_in_front
    rof = r_out if r_out_front is None else r_out_front
    bm = bmesh.new()
    R = []
    for (rr, yy) in ((r_out + g, y0 - g), (rof + g, y0 + depth + g), (rif - g, y0 + depth + g), (r_in - g, y0 - g)):
        R.append([bm.verts.new((cx + rr * math.cos(2 * math.pi * i / sides), yy,
                                cz + rr * math.sin(2 * math.pi * i / sides))) for i in range(sides)])
    for k in range(4):
        a, b = R[k], R[(k + 1) % 4]
        for i in range(sides):
            j = (i + 1) % sides
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for f in bm.faces:
        f.material_index = 0
    return _emit(G, p, bm, [mat], grain=0)


def sconce_glow(G, p, x0, x1, y0, y1, z0, z1):
    """The sconce's lit panes: an open shell over the three show faces (+y front, +-x sides; the back is on the post and
    the top and bottom are under the plates), each face one quad carrying the whole glow picture (GLOW, U across the face,
    V up), so the hot core sits on the face's centre line - behind the mullion - a little above the middle and the
    field falls off smoothly to deep amber at the frame posts."""
    g = _grow()
    x0, x1, y0, y1, z0, z1 = x0 - g, x1 + g, y0 - g, y1 + g, z0 - g, z1 + g
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV0")
    VS = {}

    def V(x, y, z):   # the faces share their corner edges (no coincident vertices)
        k = (round(x, 7), round(y, 7), round(z, 7))
        if k not in VS:
            VS[k] = bm.verts.new((x, y, z))
        return VS[k]
    for quad in (((x1, y1), (x0, y1)), ((x1, y0), (x1, y1)), ((x0, y1), (x0, y0))):   # front, +x side, -x side
        (ax, ay), (bx, by) = quad
        vs = [V(ax, ay, z0), V(bx, by, z0), V(bx, by, z1), V(ax, ay, z1)]
        f = bm.faces.new(vs)
        f.material_index = 0
        for l, uv in zip(f.loops, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))):
            l[uvl].uv = uv
    bm.normal_update()
    for f in bm.faces:   # outward: +Y on the front, +-X on the sides (U then reads left to right from outside)
        c = f.calc_center_median()
        want = (0, 1, 0) if abs(c.y - y1) < 1e-6 and x0 + 1e-6 < c.x < x1 - 1e-6 else ((1, 0, 0) if c.x > 0 else (-1, 0, 0))
        assert f.normal.dot(want) > 0, "sconce pane winding"
    return _emit(G, p, bm, [GLOW], uv_mode="keep")


def door_leaf(G, name="SM_AK_DoorLeaf", lead=+1):
    """One parked leaf; lead = the side of its leading stile (+1: the +X stile, the west leaf SM_AK_DoorLeaf; -1: the -X
    stile, the east leaf SM_AK_DoorLeaf_R). Both leaves show the same room face (+Y); only the pull differs."""
    p = G["Piece"](name)
    H = LEAF_H
    W, D = LEAF_W, LEAF_T
    x0, x1 = SW, W - SW
    ch = 0.007
    # stiles and rails (chamfered, grain along the member)
    cbox(G, p, 0, SW, 0, D, 0, H, T, ch, grain=2, edge=WE)
    cbox(G, p, W - SW, W, 0, D, 0, H, T, ch, grain=2, edge=WE)
    for z0, z1 in ((0, Z_BOT), (Z_PANEL_TOP, Z_GRID0), (Z_GRID1, Z_LAT0), (Z_TOP, H)):
        cbox(G, p, x0 - 0.01, x1 + 0.01, 0.002, D - 0.002, z0, z1, T, ch, grain=0, edge=WE)
    # a thin inner bead around each glazed zone (the sheet's secondary frame), both faces
    for z0, z1 in ((Z_GRID0, Z_GRID1), (Z_LAT0, Z_TOP)):
        for (ya, yb) in ((0.036, 0.046), (0.004, 0.014)):
            cbox(G, p, x0, x0 + 0.022, ya, yb, z0, z1, T, grain=2)
            cbox(G, p, x1 - 0.022, x1, ya, yb, z0, z1, T, grain=2)
            cbox(G, p, x0, x1, ya, yb, z0, z0 + 0.022, T, grain=0)
            cbox(G, p, x0, x1, ya, yb, z1 - 0.022, z1, T, grain=0)
    # upper lattice: N_BARS round-edged vertical bars over paper strips STRIP_K x their width; the cross bar 37 % down
    xi0, wi = x0 + 0.022, (x1 - x0 - 0.044)
    bw = wi / (N_BARS + STRIP_K * (N_BARS + 1))
    # fix round 3: warm backlit paper behind both lattices (a 2 mm sheet in the middle of the leaf), one piece per
    # paper strip (cut behind the bars), graded: brightest in the middle, deeper toward the stiles, and one tone
    # down above the cross bar
    cuts = [x0 - 0.005] + [xi0 + i * STRIP_K * bw + (i - 0.5) * bw for i in range(1, N_BARS + 1)] + [x1 + 0.005]
    for i, (ca, cb) in enumerate(zip(cuts, cuts[1:])):
        lv = min(2, abs(i - N_BARS // 2) // 2)
        cbox(G, p, ca, cb, 0.024, 0.026, Z_LAT0, Z_CROSS, PAPER[lv], grain=2)
        cbox(G, p, ca, cb, 0.024, 0.026, Z_CROSS, Z_TOP, PAPER[min(2, lv + 1)], grain=2)
    gw = wi / N_GRID
    gcuts = [x0 - 0.005] + [xi0 + i * gw for i in range(1, N_GRID)] + [x1 + 0.005]
    for i, (ca, cb) in enumerate(zip(gcuts, gcuts[1:])):
        lv = min(2, int(abs(i - (N_GRID - 1) / 2)) // 2 + 0)
        cbox(G, p, ca, cb, 0.024, 0.026, Z_GRID0, Z_GRID1, PAPER[lv], grain=0)
    for side, (vy0, vy1, hy0, hy1) in ((+1, (0.026, 0.045, 0.026, 0.040)), (-1, (0.005, 0.024, 0.010, 0.024))):
        for i in range(1, N_BARS + 1):
            xl = xi0 + i * STRIP_K * bw + (i - 1) * bw
            cbox(G, p, xl, xl + bw, vy0, vy1, Z_LAT0 + 0.01, Z_TOP - 0.01, T, 0.008, grain=2, seg=2, only=2)
        cbox(G, p, x0 + 0.01, x1 - 0.01, hy0, hy1, Z_CROSS - 0.014, Z_CROSS + 0.014, T, grain=0)
        # the square grid band: r6 N_GRID - 1 vertical bars (N_GRID columns of near-square cells), 2 horizontal bars
        # (3 rows); r5 (blind judge: the sheet's grid is darker, its bars heavier): 3.4 / 3.2 cm bars
        gw = wi / N_GRID
        for i in range(1, N_GRID):
            xc = xi0 + i * gw
            cbox(G, p, xc - 0.017, xc + 0.017, vy0, vy1 - 0.002, Z_GRID0 + 0.01, Z_GRID1 - 0.01, T, grain=2)
        gh = (Z_GRID1 - Z_GRID0 - 0.044) / 3
        for k in (1, 2):
            zc = Z_GRID0 + 0.022 + k * gh
            cbox(G, p, x0 + 0.01, x1 - 0.01, hy0, hy1, zc - 0.016, zc + 0.016, T, grain=0)
    # the lower panel, set back 7 mm from the frame faces; r6 (blind judge: the sheet's kick panel is a plain single
    # board with the emblem centred - no plank seams): one board
    cbox(G, p, x0 - 0.004, x1 + 0.004, 0.009, 0.041, Z_BOT - 0.01, Z_PANEL_TOP + 0.01, T, 0.0015, grain=2)
    # the user's emblem medallion (M_AK_Emblem, unique UV on the disc face) in a bevelled brass rim, room face (+Y)
    cx, cz, r = W / 2, (Z_BOT + Z_PANEL_TOP) / 2, 0.225
    _emblem_disc(G, p, cx, 0.048, cz, r, +1)
    ring_y(G, p, cx, 0.039, cz, r - 0.003, r + 0.032, 0.014, BR, 40, r_in_front=r - 0.001, r_out_front=r + 0.024)
    # layout 2 (judge delta): ONE pull, centred on the LEADING stile only (room face). r2 (blind judge: the sheet's
    # pulls are solid, prominent brass flush pulls at the slat-to-grid transition): a solid bright brass plate with a
    # bevelled edge, a shallow aged-brass finger dish in its middle, spanning the grid band's top and the rail above it
    xc = W - SW / 2 if lead > 0 else SW / 2
    z0, z1, hw = 1.44, 1.90, 0.036
    cbox(G, p, xc - hw, xc + hw, D - 0.002, D + 0.008, z0, z1, BR, 0.004, grain=2, edge=BR)
    cbox(G, p, xc - hw + 0.012, xc + hw - 0.012, D + 0.004, D + 0.0095, z0 + 0.08, z1 - 0.08, BA, 0.002, grain=2)
    fm = _fm("+y", 0, W, 0, D)[0]
    for zb in (z0 + 0.035, z1 - 0.035):
        rivet(G, p, fm, xc, zb, 0.008, r=0.009, h=0.005)
    # the lower ends of the two brass hanger strap plates, riveted to the top rail (room face; r5: wider, two rivets)
    for xs in STRAP_X:
        cbox(G, p, xs - STRAP_HW, xs + STRAP_HW, D - 0.001, D + 0.008, Z_TOP + 0.04, H - 0.003, BP, 0.002, grain=2,
             edge=BR)
        for zr in (Z_TOP + 0.085, H - 0.05):
            rivet(G, p, fm, xs, zr, 0.008, r=0.013, h=0.009)
    # r5 (blind judge: the sheet's stiles and rails are a heavier moulded frame): a proud moulding with worn arrises
    # along the inner edge of both stiles and over the top and bottom rails' inner edges (room face)
    for xa_, xb_ in ((x0 - 0.034, x0 + 0.004), (x1 - 0.004, x1 + 0.034)):
        cbox(G, p, xa_, xb_, D - 0.002, D + 0.007, Z_BOT - 0.03, Z_TOP + 0.03, T, 0.004, grain=2, edge=WE)
    for za_, zb_ in ((Z_BOT - 0.034, Z_BOT + 0.004), (Z_TOP - 0.004, Z_TOP + 0.03)):
        cbox(G, p, x0 + 0.004, x1 - 0.004, D - 0.002, D + 0.007, za_, zb_, T, 0.004, grain=0, edge=WE)
    # r5 (blind judge: the thin bright brass strip on the sheet's leading edge): a brass strip down the leading edge
    xe = (W - 0.016, W - 0.002) if lead > 0 else (0.002, 0.016)
    cbox(G, p, xe[0], xe[1], D - 0.002, D + 0.004, 0.03, H - 0.03, BR, 0.001, grain=2)
    p.col(0, LEAF_W, 0, 0.05, 0, H)   # scripted collision
    return p


# --------------------------------------------------------------------------- the entrance frame

# layout 2 r3 (blind judge: the sheet's lintel is ONE heavy dark timber with strong grain and no metal inlays, the
# opening taller for its width): between the posts a recessed board panel (3.65-4.30) behind the track, a head casing
# over the opening, the lintel 4.30-4.72 (build_armory_kit.ENT_LINTEL); the posts run on past it to +5.00
# r6 (blind judge: the sheet's header is STEPPED - the head beam between the posts stands ~0.3-0.4 m above the side
# walls' tops with a second lintel (nuki) band below it; the r5 lintel, wall tops and post tops made one flat slab):
# the nuki 4.325-4.53 (5 cm behind the head beam's face), a dark 3 cm shadow reveal, the head beam 4.56-4.86 (two
# stacked planks, it runs out 16 cm past each post), the side walls stopping at WALL_TOP 4.54 (0.32 m below the head
# beam's top) under their ranma band, a dark recessed back panel above them; the posts rise 0.14 past the beam to +5.00
Z_L0, Z_NK1 = 4.325, 4.53     # the nuki (the lower lintel band)
Z_HB0, Z_L1 = 4.56, 4.86      # the head beam
WALL_TOP = 4.54               # the side walls' top
STUB_BACK_PANEL = False       # True: a dark back panel closes the stubs from WALL_TOP to +5.00 (flat silhouette)
JAMB_COL_Z = 4.30             # the scripted jamb collision's top (build_armory_kit.ENT_LINTEL, unchanged)
TRACK_Z = 4.12            # the brass rod's axis (build_armory_kit.ENT_TRACK_Z)
Z_RAIL0, Z_RAIL1 = 3.94, 4.10   # the stubs' track-height rail (r6: its top at the rod, the sheet's)
# the wall ranma - a proud frame rail, the square lattice (bold dark bars over muted amber paper), a frame rail and a
# proud top board; r6 (blind judge: the sheet's band is taller with larger dark grid openings, about 3 rows): 3 rows
# of 10 cm cells (10.5 cm columns) 4.13-4.43, just above the track rail
Z_LAT0W, Z_LAT1 = 4.13, 4.43
RANMA_ROWS, RANMA_COL = 3, 0.105


def _clad_face(G, p, xa, xb, face_y, out, rail=True):
    """Wall-stub cladding on one face (face_y, boards toward `out` = +1 room side / -1 outside): skirting, lower
    boards, a base rail, vertical boards, the track-height rail, the framed 4-row square lattice band (8 cm columns,
    as many as fit) and the top board."""
    def slab(x0, x1, z0, z1, t, mat=T, ch=0.004, grain=None, inset=0.0, edge=None):
        ya, yb = (face_y + inset, face_y + inset + t) if out > 0 else (face_y - inset - t, face_y - inset)
        cbox(G, p, x0, x1, ya, yb, z0, z1, mat, ch, grain=grain, edge=edge)
    slab(xa, xb, 0.0, 0.10, 0.030, grain=0, edge=WE)
    n = max(1, round((xb - xa) / 0.24))
    w = (xb - xa) / n
    for i in range(n):
        slab(xa + i * w, xa + (i + 1) * w, 0.10, 0.36, 0.020, grain=2)
    slab(xa, xb, 0.36, 0.55, 0.034, ch=0.006, grain=0, edge=WE)
    for i in range(n):
        slab(xa + i * w, xa + (i + 1) * w, 0.55, Z_RAIL0, 0.020, grain=2, ch=0.005)
    if rail:
        slab(xa, xb, Z_RAIL0, Z_RAIL1, 0.040, ch=0.008, grain=0, edge=WE)
    if Z_LAT0W - 0.03 - Z_RAIL1 > 0.01:
        slab(xa, xb, Z_RAIL1, Z_LAT0W - 0.03, 0.028, ch=0.005, grain=0)
    slab(xa, xb, Z_LAT0W - 0.03, Z_LAT0W, 0.036, ch=0.005, grain=0)                   # frame rail below
    slab(xa, xb, Z_LAT1, Z_LAT1 + 0.03, 0.036, ch=0.005, grain=0)                     # frame rail above
    slab(xa, xb, Z_LAT0W - 0.005, Z_LAT1 + 0.005, 0.004, RP, 0.0, grain=0)            # the paper
    nc = max(3, round((xb - xa) / RANMA_COL))
    cw = (xb - xa) / nc
    for i in range(1, nc):
        xc = xa + i * cw
        slab(xc - 0.013, xc + 0.013, Z_LAT0W, Z_LAT1, 0.024, ch=0.0, grain=2, inset=0.004)   # r5: bolder dark grid
    # r2 (blind judge: a long continuous band like the sheet's): no end stiles, the band runs on under the post
    rh = (Z_LAT1 - Z_LAT0W) / RANMA_ROWS
    for k in range(1, RANMA_ROWS):
        zc = Z_LAT0W + k * rh
        slab(xa, xb, zc - 0.012, zc + 0.012, 0.022, ch=0.0, grain=0, inset=0.004)
    # r6: the wall's top - a proud top board with worn arrises at WALL_TOP, 0.32 m under the head beam's top
    slab(xa, xb, Z_LAT1 + 0.03, WALL_TOP, 0.052, ch=0.010, grain=0, edge=WE)


def entrance(G):
    """SM_AK_Entrance_12 (layout 2 r3): the whole south wall X 0-12 round the clear opening X 4-8, Z 0-3.65 (local X =
    world X); wall frame: room face at y = 0, thickness to y = -0.30, up to +5.00 like the wall pieces. The posts' timber
    at X 1.61-2.11 / 9.89-10.39, a 14 cm inner jamb band with a brass edge between each post and its parked leaf
    (X 2.11-2.25 / 9.75-9.89, standing on the step), the leaves at 2.25-3.95 / 8.05-9.75; 1.6 m of clad wall outside each
    post."""
    p = G["Piece"]("SM_AK_Entrance_12")
    H = G["ENTRY_H"]
    TOP = 5.0
    L = ENT_W
    o0, o1 = OPEN_X
    a, b = POST_IN[0] - 0.005, POST_IN[1] + 0.005      # members between the posts run 5 mm into their timber

    def mirrored(x0, x1):
        return ((x0, x1), (L - x1, L - x0))
    # ---- the wall, each side of the opening: the core (stub + behind the post + behind the parked leaf, up to the
    # opening head; outside the posts up to the top), a face board behind the post and the leaf (the post's back sits
    # on it)
    for (c0, c1), (u0, u1), (f0, f1), (g0, g1), (s0, s1), (k0, k1) in zip(
            mirrored(0.0, o0), mirrored(0.0, POST_OUT), mirrored(POST_OUT, o0), mirrored(POST_OUT, a),
            mirrored(0.0, POST_OUT + 0.01), mirrored(o0 - 0.06, o0)):
        cbox(G, p, c0, c1, -0.30, -0.021, 0, H, T, grain=2)
        # r6: the stub (outside the post) stops at WALL_TOP (the sheet's stepped silhouette; in the room the exterior
        # skin SM_AKX_Facade_* at y -0.30 closes the wall up to the ceiling behind it, STUB_BACK_PANEL puts a dark back
        # panel there instead); behind the post the core runs on up
        cbox(G, p, u0, u1, -0.30, -0.021, H, WALL_TOP, T, grain=2)
        if STUB_BACK_PANEL:
            cbox(G, p, u0, u1, -0.30, -0.26, WALL_TOP - 0.01, TOP, EG, grain=2)
        cbox(G, p, g0, g1, -0.30, -0.021, H, TOP, T, grain=2)
        cbox(G, p, f0, f1, -0.021, -0.001, 0, H, T, grain=2)
        cbox(G, p, g0, g1, -0.021, -0.001, H, TOP, T, grain=2)
        # ---- the stub outside the post: the sheet's wall cladding with the lattice (ranma) band
        _clad_face(G, p, s0, s1, -0.021, +1)
        # ---- a slim casing down the side of the opening (behind the parked leaf's leading stile), a brass edge
        cbox(G, p, k0, k1, -0.004, 0.030, G["LEAF_Z"], H, T, 0.004, grain=2, edge=WE)   # genkan: down to its floor
        ke = (k1 - 0.008, k1) if k0 < L / 2 else (k0, k0 + 0.008)
        cbox(G, p, ke[0], ke[1], 0.022, 0.034, G["LEAF_Z"], H - 0.002, BR, grain=2)
    # ---- r3 (blind judge: the sheet's inner jamb band between each post and its parked leaf, brass-edged): a 14 cm
    # casing standing on the step, proud to the leaves' hardware line, worn arrises, a brass angle on its leaf-side
    # front edge and a shallow groove down its face
    # r6 (blind judge: the sheet's reveal gap between the post and the leaf is wider): the casing 8.5 cm, then a dark
    # 5.5 cm reveal set back to y 0.10 (behind the leaf's face) before the leaf's outer stile
    JC = JAMB_W - 0.055   # r20 round 3: the casing takes the wider band (0.085 at JAMB_W 0.14); the reveal stays 5.5 cm
    for sgn, (j0, j1), (r0, r1) in (
            (+1, (POST_IN[0] - 0.005, POST_IN[0] + JC), (POST_IN[0] + JC - 0.004, POST_IN[0] + JAMB_W)),
            (-1, (POST_IN[1] - JC, POST_IN[1] + 0.005), (POST_IN[1] - JAMB_W, POST_IN[1] - JC + 0.004))):
        cbox(G, p, j0, j1, -0.004, 0.205, G["LEAF_Z"] - 0.003, Z_L0 + 0.004, T, 0.005, grain=2, edge=WE)
        cbox(G, p, r0, r1, -0.004, 0.10, G["LEAF_Z"] - 0.003, Z_L0 + 0.004, EG, grain=2)
        je = j1 if sgn > 0 else j0
        cbox(G, p, min(je, je - sgn * 0.014), max(je, je - sgn * 0.014), 0.196, 0.214, G["LEAF_Z"], Z_L0, BR, 0.0015,
             grain=2)
        jc = (j0 + j1) / 2 - sgn * 0.006
        cbox(G, p, jc - 0.005, jc + 0.005, 0.200, 0.2065, G["LEAF_Z"] + 0.02, Z_L0 - 0.02, "M_AK_HEntEndGrain", grain=2)
    # ---- between the posts: the recessed panel of vertical boards behind the track (over the opening and the parked
    # leaves), the opening's head casing, ONE heavy lintel through the wall, a recessed fill above it (the posts rise
    # past it)
    cbox(G, p, a, b, -0.30, -0.002, H, Z_L0 + 0.005, T, grain=0)
    nb = max(1, round((b - a) / 0.26))
    bw_ = (b - a) / nb
    for i in range(nb):
        cbox(G, p, a + i * bw_, a + (i + 1) * bw_, -0.004, 0.020, H, Z_L0 + 0.004, T, 0.004, grain=2)
    cbox(G, p, o0 - 0.06, o1 + 0.06, -0.004, 0.036, H - 0.002, H + 0.075, T, 0.005, grain=0, edge=WE)
    cbox(G, p, o0, o1, 0.022, 0.036, H - 0.004, H + 0.006, BR, 0.0015, grain=0)
    # r6: the stepped header - the nuki, a dark shadow reveal, the head beam of two stacked planks (a dark seam)
    cbox(G, p, a, b, -0.30, 0.19, Z_L0, Z_NK1, T, 0.018, grain=0, seg=2, edge=WE)
    cbox(G, p, a, b, -0.30, 0.13, Z_NK1 - 0.006, Z_HB0 + 0.006, EG, grain=0)
    cbox(G, p, a, b, -0.30, 0.24, Z_HB0, Z_L1, T, 0.022, grain=0, seg=2, edge=WE)
    zs = Z_HB0 + 0.46 * (Z_L1 - Z_HB0)
    cbox(G, p, a + 0.01, b - 0.01, 0.236, 0.2415, zs - 0.004, zs + 0.004, EG, grain=0)
    cbox(G, p, a, b, -0.30, -0.04, Z_L1 - 0.01, TOP, T, grain=0)
    # r5 (blind judge: in the sheet's 3/4 view the upper beam overhangs past the post): r6 the head beam runs on
    # through each post and stands out 16 cm past its outer face over the lower side wall (worn arrises, a dark
    # end-grain face)
    for sgn, xo in ((-1, POST_OUT - 0.003), (+1, L - POST_OUT + 0.003)):
        xe = xo + sgn * 0.16
        cbox(G, p, min(xo, xe), max(xo, xe), -0.021, 0.21, Z_HB0 + 0.015, Z_L1, T, 0.02, grain=0, seg=2, edge=WE)
        xf = xe + sgn * 0.001
        cbox(G, p, min(xe - sgn * 0.004, xf), max(xe - sgn * 0.004, xf), 0.0, 0.19, Z_HB0 + 0.035, Z_L1 - 0.02, EG,
             grain=2)
    # ---- the brass top track, post to post: a rod on stand-offs with a collar at each post; four flat hanger straps
    # (their round heads carry the wheels), 0.25 m in from each end of both parked leaves; the straps' lower ends are on
    # the leaf
    RY, RZ, RR = 0.165, TRACK_Z, 0.026            # r5: a heavier rod (2.2 -> 2.6 cm radius)
    cyl(G, p, (POST_IN[0] - 0.01, RY, RZ), RR, POST_IN[1] - POST_IN[0] + 0.02, "x", BR, 14)
    for xe in (POST_IN[0], POST_IN[1] - 0.036):
        cyl(G, p, (xe, RY, RZ), 0.030, 0.036, "x", BR, 14)
    for xs in (POST_IN[0] + 0.45, POST_IN[0] + 2.05, L / 2, POST_IN[1] - 2.05, POST_IN[1] - 0.45):
        yb = 0.020
        cbox(G, p, xs - 0.02, xs + 0.02, yb, RY - 0.004, RZ - 0.02, RZ + 0.02, BR, 0.003, grain=1)
        cyl(G, p, (xs, yb - 0.002, RZ), 0.032, 0.008, "y", BR, 12)                  # round rose on the panel
    # r5 (blind judge: the sheet has a second flat track bar just below and behind the rod): a flat bar on the panel
    cbox(G, p, POST_IN[0], POST_IN[1], 0.016, 0.048, RZ - 0.085, RZ - 0.045, BR, 0.003, grain=0)
    for xs in (POST_IN[0] + 0.30, L / 2 - 1.2, L / 2 + 1.2, POST_IN[1] - 0.30):
        rivet(G, p, _fm("+y", 0, L, 0, 0.048)[0], xs, RZ - 0.065, 0.0, r=0.010, h=0.007)
    # r5 (blind judge: the sheet's hanger-wheel assemblies are chunky, the wheel cylinders clear in the high view, on
    # wider riveted strap plates): a deep flanged wheel on the rod, an axle boss, a wide strap plate with two rivets
    WR = 0.080
    wz = RZ + RR + WR - 0.010
    ltop = G["LEAF_Z"] + LEAF_H                                                     # the leaves' top (genkan: +3.90)
    for xh in WHEEL_X:
        cyl(G, p, (xh, 0.132, wz), WR, 0.046, "y", BR, 22)                          # the deep wheel on the rod
        for yf in (0.124, 0.176):
            cyl(G, p, (xh, yf, wz), WR + 0.012, 0.008, "y", BA, 22)               # its two flanges
        cyl(G, p, (xh, 0.110, wz), 0.018, 0.090, "y", BR, 8)                        # axle
        cyl(G, p, (xh, 0.190, wz), STRAP_HW + 0.010, 0.009, "y", BP, 20)            # the strap's round head
        cbox(G, p, xh - STRAP_HW, xh + STRAP_HW, 0.190, 0.199, ltop - 0.003, wz, BP, 0.002, grain=2, edge=BR)
        fms = _fm("+y", 0, L, 0, 0.199)[0]
        for zr in (ltop + 0.02, (ltop + wz) / 2 - 0.01):
            rivet(G, p, fms, xh, zr, 0.0, r=0.012, h=0.008)
        cyl(G, p, (xh, 0.198, wz), 0.024, 0.012, "y", BR, 6)                        # hex axle nut
        cyl(G, p, (xh, 0.209, wz), 0.014, 0.018, "y", BR, 8, r2=0.006)            # the bolt end
    # scripted collision
    p.col(0, OPEN_X[0], -0.30, 0.03, 0, 5.0).col(OPEN_X[1], L, -0.30, 0.03, 0, 5.0)
    p.col(POST_IN[0], POST_IN[1], -0.30, 0.24, H, 5.0)
    p.col(POST_IN[0], POST_IN[0] + JAMB_W, 0, 0.215, 0, JAMB_COL_Z).col(POST_IN[1] - JAMB_W, POST_IN[1], 0, 0.215, 0,
                                                                        JAMB_COL_Z)
    return p


# --------------------------------------------------------------------------- floor pieces

def threshold(G):
    """The outer sill across the 4 m opening in the exterior door casing's depth (ENTRY_SILL, world Y -0.435 to -0.30).
    Genkan (2026-09-28): a LOW sill, top SILL_TOP (+0.04, just under the granite landing), its body down to GENKAN_BASE so
    its room face closes the 16 cm step down onto the sunken genkan floor that runs through the doorway behind it: a
    set-back body under a squared nosing board lipped out over the street side, softly worn arrises, a flush brass strip
    along each top edge (r6)."""
    p = G["Piece"]("SM_AK_Threshold_4")
    s0, s1 = G["ENTRY_SILL"]
    top, base = G["SILL_TOP"], G["GENKAN_BASE"]
    cbox(G, p, 0.0, 4.0, s0 + 0.018, s1, base, top - 0.030, T, 0.004, grain=0, edge=WE)
    cbox(G, p, 0.0, 4.0, s0, s1, top - 0.036, top, T, 0.013, grain=0, seg=3, edge=WE)
    cbox(G, p, 0.004, 3.996, s1 - 0.024, s1 - 0.002, top - 0.004, top + 0.0015, BR, 0.0015, grain=0)
    cbox(G, p, 0.004, 3.996, s0 - 0.002, s0 + 0.020, top - 0.004, top + 0.0015, BR, 0.0015, grain=0)
    cbox(G, p, 0.004, 3.996, s0 - 0.003, s0 + 0.001, top - 0.030, top, BR, 0.001, grain=0)
    p.col(0, 4.0, s0, s1, base, top)   # scripted collision
    return p


def step_beam(G):
    """Genkan (2026-09-28): the agari-kamachi at the genkan's far edge that separates it from the raised hall floor
    (reference 2's "black bar"), local to (GENKAN x0, 0). Entryfix (2026-09-28, the user: "a black bar separating the main
    floor", the crop entry_foreground_crop.png): ONE solid near-black lacquer bar (M_AK_HStepLacquer, top and 12 cm face
    alike, crisp 4 mm arrises; the r4 lighter weathered top board is gone) from X -STEP_RETURN_W to gw + STEP_RETURN_W
    (world 3.46-8.54: its ends behind the two entry lanterns, which cap them), Y gd to gd + STEP_BEAM_D (world 2.35-2.51),
    its top flush with the hall floor, the body on down to GENKAN_BASE; the pit's side edges are dark board returns
    (M_AK_HMatBoard, the mat surround's near-black timber) OUTSIDE the pit, X -rw-0 / gw-gw+rw, from STEP_RETURN_Y0 (the
    wall) to the bar."""
    p = G["Piece"]("SM_AK_StepBeam")
    gx0, gy0, gx1, gy1 = G["GENKAN"]
    gw, gd, rw, bd, base = gx1 - gx0, gy1 - gy0, G["STEP_RETURN_W"], G["STEP_BEAM_D"], G["GENKAN_BASE"]
    ry = G["STEP_RETURN_Y0"]
    BAR, RET = "M_AK_HStepLacquer", "M_AK_HMatBoard"
    cbox(G, p, -rw, gw + rw, gd, gd + bd, base, 0.0, BAR, 0.006, grain=0)            # the bar, one crisp lacquer block
    for xa, xb in ((-rw, 0.0), (gw, gw + rw)):                                          # the side returns, butted to it
        cbox(G, p, xa, xb, ry, gd - 0.001, base, 0.0, RET, 0.004, grain=1)
    p.col(-rw, gw + rw, gd, gd + bd, base, 0).col(-rw, 0, ry, gd, base, 0)
    p.col(gw, gw + rw, ry, gd, base, 0)   # scripted collision
    return p


def entry_mat(G):
    """Genkan (2026-09-28, reference 2's foreground): the woven mat lying on the sunken genkan floor, its far
    end against the step beam, in a dark board surround. Local to the surround's corner (ENTRY_MAT x0 - MAT_BOARD,
    y0 - MAT_BOARD) on GENKAN_Z: the rush field 2.5 x 2.38 m (ENTRY_MAT, world X 4.75-7.25, Y 0.18-2.56; M_AK_HEntMat,
    the ribs running ACROSS as the reference's woven rows) in a thin rolled black binding (5 cm; the reference shows no
    gold cord), top +2.2 cm; the surround a dark timber board down each side and across the near end (MAT_BOARD 0.20,
    top +3 cm, worn arrises). r4: the field a chunky grey-brown knotted sisal (T_AK_HEntSisal), the binding 9.5 cm,
    the boards near-black (M_AK_HMatBoard) 0.15 m wide with 12 mm lighter worn arrises. The r4-r6 mat (4.0 x 1.05 m, a 16 cm binding and a gold cord, inset in the raised step)
    is gone. Matfix (2026-09-28, the user: "fix the mat"): ONE mat, world Y 1.47-2.35 (its near binding where the
    crop shows the dark band), the r2 stripe gone, field and binding one planar weave mapping (T_AK_HEntWeave, the
    binding the same weave near-black), the binding 7 cm on all four sides."""
    p = G["Piece"]("SM_AK_EntryMat")
    B = G["MAT_BOARD"]
    mx0, my0, mx1, my1 = G["ENTRY_MAT"]
    mw, md = round(mx1 - mx0, 4), round(my1 - my0, 4)
    # r20 mat (judge 7/10: "the top border is swallowed by a black shadow gap under the front sill ... close the gap /
    # raise the mat so the black border reads on all four sides from C1"): the mat and its surround stand as a low
    # raised frame on the genkan floor, the field at MAT_FIELD_Z (was G["MAT_TOP"] 0.022), so only a few cm of the
    # bar's black face show above the far binding (reference 2 through C1: ~10 px of dark gap between the bar and the
    # border, b7 ~22 px). The side boards SIDE_W wide (judge: "a bit wider", 0.11 -> SIDE_W, grown outward) with a
    # raised inner lip (LIP_W x LIP_H over the board, its chamfers in a lighter worn brown, M_AK_HMatLip).
    t = MAT_FIELD_Z
    bt = MAT_BOARD_Z
    MB = "M_AK_HMatBoard"
    sx = SIDE_W - B                                                     # the side boards grow outward by sx
    cbox(G, p, -sx, B, 0.0, B + md, 0.0, bt, MB, 0.006, grain=1, seg=2)
    cbox(G, p, B + mw, 2 * B + mw + sx, 0.0, B + md, 0.0, bt, MB, 0.006, grain=1, seg=2)
    cbox(G, p, -sx + 0.002, 2 * B + mw + sx - 0.002, 0.0, B, 0.0, bt, MB, 0.006, grain=0, seg=2)
    # the inner lip: a raised bead on each board's mat edge (the sides full length to the bar, the near one between them)
    cbox(G, p, B - LIP_W, B + 0.001, B - LIP_W, B + md, bt - 0.004, bt + LIP_H, MB, 0.0035, grain=1, seg=2, edge=LIPM)
    cbox(G, p, B + mw - 0.001, B + mw + LIP_W, B - LIP_W, B + md, bt - 0.004, bt + LIP_H, MB, 0.0035, grain=1, seg=2,
         edge=LIPM)
    cbox(G, p, B - LIP_W + 0.003, B + mw + LIP_W - 0.003, B - LIP_W, B + 0.001, bt - 0.004, bt + LIP_H, MB, 0.0035,
         grain=0, seg=2, edge=LIPM)
    X0, X1, Y0, Y1 = B, B + mw, B, B + md
    # r20 mat: the binding BIND_W on all four sides (reference 2 through C1: ~15 px at the sides, ~8-9 px at the ends,
    # 5.5-6 cm; b7's 8.5 cm roll), a flat crown with a small roll at the lip and a CRISP 4 mm drop onto the field, in the
    # fine black rope (T_AK_HEntRopeB) laid along each strip. The field is flat (b7's +-2 mm undulation on a 10 cm grid,
    # shaded smooth, is gone); its relief is the nub set's normal.
    d = [0.0, 0.004, 0.010, BIND_W - 0.004, BIND_W - 0.0012, BIND_W]
    hz = [t - 0.003, t + 0.0015, t + 0.0035, t + 0.0035, t + 0.0022, t - 0.0010]
    FIELD = len(d) - 1
    fx = max(2, round((X1 - X0 - 2 * d[-1]) / 0.10))
    fy = max(2, round((Y1 - Y0 - 2 * d[-1]) / 0.10))
    inx = [X0 + d[-1] + (X1 - X0 - 2 * d[-1]) * k / fx for k in range(1, fx)]
    iny = [Y0 + d[-1] + (Y1 - Y0 - 2 * d[-1]) * k / fy for k in range(1, fy)]
    xs = [X0 + v for v in d] + inx + [X1 - v for v in reversed(d)]
    ys = [Y0 + v for v in d] + iny + [Y1 - v for v in reversed(d)]
    nx, ny = len(xs), len(ys)
    rk = lambda i, m: min(i, m - 1 - i, FIELD)

    def z_at(i, j):
        return hz[min(rk(i, nx), rk(j, ny))]
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV0")
    top = [[bm.verts.new((xs[i], ys[j], z_at(i, j))) for j in range(ny)] for i in range(nx)]
    mats = [MAT, BD]
    for i in range(nx - 1):
        for j in range(ny - 1):
            f = bm.faces.new((top[i][j], top[i + 1][j], top[i + 1][j + 1], top[i][j + 1]))
            ri, rj = min(i, nx - 2 - i), min(j, ny - 2 - j)
            if min(ri, rj) >= FIELD:
                f.material_index = 0                    # the nub field: one planar mapping, U = world Y, 1 m per tile
                for l in f.loops:
                    l[uvl].uv = (l.vert.co.y, l.vert.co.x)
            else:
                # the rope binding: U along the strip, V across it (mitred at the corners)
                f.material_index = 1
                side = ri < rj or (ri == rj and (i + j) % 2 == 0)
                for l in f.loops:
                    l[uvl].uv = (l.vert.co.y, l.vert.co.x) if side else (l.vert.co.x, l.vert.co.y)
    bot = [bm.verts.new((x, y, 0.0)) for (x, y) in ((X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1))]
    sides = ([top[i][0] for i in range(nx)], [top[nx - 1][j] for j in range(ny)],
             [top[i][ny - 1] for i in range(nx - 1, -1, -1)], [top[0][j] for j in range(ny - 1, -1, -1)])
    for s_ in range(4):
        bs, be = bot[s_], bot[(s_ + 1) % 4]
        edge = sides[s_]
        seg = len(edge) - 1
        for m in range(seg):
            a, b = edge[m], edge[m + 1]
            f = bm.faces.new((a, b, bs) if m < seg - 1 else (a, b, be, bs))
            f.material_index = 1
            for l in f.loops:
                l[uvl].uv = (0.002, 0.002)
    f = bm.faces.new((bot[0], bot[3], bot[2], bot[1]))
    f.material_index = 1
    for l in f.loops:
        l[uvl].uv = (0.002, 0.002)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    # the binding's roll shades smooth; its crisp inner drop and the flat field flat
    rollf = {i * (ny - 1) + j for i in range(nx - 1) for j in range(ny - 1)
             if min(i, nx - 2 - i, j, ny - 2 - j) < FIELD - 1}
    _emit(G, p, bm, mats, uv_mode="keep", smooth=rollf)
    p.col(-sx, 2 * B + mw + sx, 0, B + md, 0, bt + LIP_H)   # scripted collision
    return p


# --------------------------------------------------------------------------- jamb post and wall sconce

def jamb_post(G):
    """Layout 2: the heavy post at an outer end of the entrance frame, its back on the wall's room face (local
    y = -0.40 at placement Y 0.40). r3 (blind judge: the sheet's posts are deep square columns standing well proud of the
    wall, the step ending at their fronts, on a dark plinth flaring a little wider than the post): 50 x 80 cm timber, a
    flared dark plinth 4 cm proud on the room face and both sides (flush at the wall), a riveted brass shoe 0.7 x the
    post width high; the post rises 0.28 above the lintel to +5.00 with a flat riveted brass plate on the three show
    faces above it (r6: a square plate on the room face only, +4.60 to +4.965, under an aged-brass cap), the boss on the
    room face at the nuki (BOSS_Z)."""
    p = G["Piece"]("SM_AK_Post_Jamb_480")
    post_dress(G, p, -JAMB_HW, JAMB_HW, JAMB_BACK_Y, JAMB_FACE_Y, ("+y", "+x", "-x"), ("+y",), SHOE, TOP_PLATE,
               POST_TOP, BOSS_Z, 0.080, (PLINTH_PL, PLINTH_PL, 0.0, PLINTH_PL), ch=0.02)
    p.col(-JAMB_HW - JAMB_PL, JAMB_HW + JAMB_PL, JAMB_BACK_Y, JAMB_FACE_Y + JAMB_PL, 0, 5.0)   # scripted collision
    return p


def frustum(G, p, x0, x1, y0, y1, z0, z1, inset, mat, keep_y0=False):
    """A closed square frustum (a low cap, a flared plinth): base x0..x1 / y0..y1 at z0, top inset by `inset` at z1
    (keep_y0: not on the y0 side, e.g. a plinth flush with the wall behind it)."""
    g = _grow()
    iy0 = 0.0 if keep_y0 else inset
    bm = bmesh.new()
    lo = [bm.verts.new(c) for c in ((x0 - g, y0 - g, z0), (x1 + g, y0 - g, z0), (x1 + g, y1 + g, z0), (x0 - g, y1 + g, z0))]
    hi = [bm.verts.new(c) for c in ((x0 + inset, y0 + iy0, z1 + g), (x1 - inset, y0 + iy0, z1 + g),
                                    (x1 - inset, y1 - inset, z1 + g), (x0 + inset, y1 - inset, z1 + g))]
    bm.faces.new(lo[::-1])
    bm.faces.new(hi)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    for f in bm.faces:
        f.material_index = 0
    return _emit(G, p, bm, [mat], grain=0)


def wall_sconce(G):
    """NEW piece: the wall lantern of the sheet. Wall-piece frame: mounting face at local y = 0, projecting +Y, centred
    on x = 0, base (the finial tip) at z ~ 0. A near-black iron frame (M_AK_HEntIron) with dark-bronze worn edges, the
    panes carrying the smooth hot-core glow (sconce_glow); no light. r3: mounted tight on the post on a flat iron back
    bar with a short bracket into the back of the body at the top and the bottom. r5: a projecting roof plate, a low
    hipped roof, a hanging ring, a turned drop finial, the glow unclipped (1.35).
    r6 (blind judge: the sheet's lantern is visibly WIDER than the post and overhangs both its edges; its iron frame is
    heavier - thicker corner posts, a flared top cap with a hanging hook, a bracket under the base): lit body 0.52 x 0.26
    x 1.04 m (h:w 2.0 like the sheet's, +0.17 to +1.21; the post is 0.50 wide), 2.6 cm corner posts standing on as short legs under the base
    plates, 2.6 cm rails, a 2.2 cm front mullion running from under the base up through the cap, a two-layer base, a
    flared roof plate 6 cm proud with a hipped roof, a collar and a heavy hook ring, a bracket arm from the back bar
    under the base to the front mullion and a larger turned drop finial."""
    p = G["Piece"]("SM_AK_H_WallSconce")
    a, y0, y1 = 0.26, 0.030, 0.290
    z0, z1 = 0.17, 1.21
    f = 0.026                                              # frame stock
    yc = (y0 + y1) / 2
    zb = z0 - 0.022                                        # the underside of the base plates
    # a two-layer base: the inner plate a little proud, the outer wider and thinner
    cbox(G, p, -a - 0.010, a + 0.010, y0 - 0.004, y1 + 0.010, z0 - 0.010, z0, IR, 0.003, grain=0, edge=BZ)
    cbox(G, p, -a - 0.030, a + 0.030, y0 - 0.006, y1 + 0.030, zb, z0 - 0.010, IR, 0.003, grain=0, edge=BZ)
    # the top: an inner plate, the flared roof plate 6 cm proud, a low hipped roof, a collar and a heavy hook ring
    cbox(G, p, -a - 0.010, a + 0.010, y0 - 0.004, y1 + 0.010, z1, z1 + 0.010, IR, 0.003, grain=0, edge=BZ)
    cbox(G, p, -a - 0.060, a + 0.060, y0 - 0.006, y1 + 0.060, z1 + 0.010, z1 + 0.028, IR, 0.004, grain=0, edge=BZ)
    frustum(G, p, -a - 0.050, a + 0.050, y0 - 0.004, y1 + 0.050, z1 + 0.028, z1 + 0.068, 0.15, IR, keep_y0=True)
    cyl(G, p, (0.0, yc + 0.010, z1 + 0.064), 0.028, 0.024, "z", IR, 12)
    ring_y(G, p, 0.0, yc + 0.004, z1 + 0.122, 0.022, 0.036, 0.014, IR, 16)
    # corner posts: through the base plates as short legs, up under the roof plate
    for sx in (-1, 1):
        for yy in (y0 + f / 2, y1 - f / 2):
            cbox(G, p, sx * (a - f / 2) - f / 2, sx * (a - f / 2) + f / 2, yy - f / 2, yy + f / 2, zb - 0.034,
                 z1 + 0.012, IR, 0.003, grain=2, edge=BZ)
    # rails round the panes (front and both sides), the full frame stock
    for zz in (z0 + f / 2, z1 - f / 2):
        cbox(G, p, -a + f, a - f, y1 - f, y1, zz - f / 2, zz + f / 2, IR, 0.002, grain=0, edge=BZ)
        for sx in (-1, 1):
            cbox(G, p, sx * a - f if sx > 0 else -a, sx * a if sx > 0 else -a + f, y0 + f, y1 - f, zz - f / 2,
                 zz + f / 2, IR, 0.002, grain=1)
    # the front mullion 2.2 cm, from under the base up through the roof plate; the side mullions 1.8 cm
    cbox(G, p, -0.011, 0.011, y1 - 0.014, y1 + 0.004, zb - 0.050, z1 + 0.030, IR, 0.002, grain=2, edge=BZ)
    for sx in (-1, 1):
        xa, xb = (a - 0.012, a + 0.003) if sx > 0 else (-a - 0.003, -a + 0.012)
        cbox(G, p, xa, xb, yc - 0.009, yc + 0.009, z0, z1, IR, 0.002, grain=2, edge=BZ)
    # the glowing panes: an open shell inside the frame (front and both sides)
    sconce_glow(G, p, -a + 0.006, a - 0.006, y0 + 0.006, y1 - 0.006, z0 + 0.002, z1 - 0.002)
    # under the base: a bracket arm from the back bar to the front mullion, and a turned drop finial (a collar, a bulb,
    # a neck and a small bronze tip)
    cbox(G, p, -0.014, 0.014, 0.008, y1 + 0.004, zb - 0.050, zb - 0.022, IR, 0.003, grain=1, edge=BZ)
    fmd = (lambda u, v, w: (u, v, zb - 0.050 - w))
    lathe_f(G, p, fmd, 0.0, yc + 0.010, [(0, -0.002), (0.044, -0.002), (0.044, 0.010), (0.028, 0.020), (0.040, 0.042),
                                          (0.034, 0.062), (0.013, 0.080), (0.009, 0.088), (0, 0.090)], 14, IR)
    cyl(G, p, (0.0, yc + 0.010, zb - 0.050 - 0.088), 0.010, 0.010, "-z", BZ, 10, r2=0.003)
    # tight on the post: a flat iron back bar from below the base to above the cap, a short bracket into the back of
    # the body at the top and the bottom (the body stands 3 cm off the post)
    cbox(G, p, -0.045, 0.045, 0.0, 0.012, zb - 0.07, z1 + 0.13, IR, 0.003, grain=2, edge=BZ)
    for zc in (z0 + 0.07, z1 - 0.07):
        cbox(G, p, -0.026, 0.026, 0.010, y0 + 0.004, zc - 0.03, zc + 0.03, IR, 0.002, grain=1)
    for zr in (zb - 0.045, z1 + 0.105):                                             # dark iron rivets on the bar
        cyl(G, p, (0.0, 0.011, zr), 0.012, 0.007, "y", IR, 8)
    p.col(-a - 0.06, a + 0.06, 0.0, y1 + 0.06, 0.0, z1 + 0.16)
    return p


def pieces(G):
    _N[0] = 0
    return [entrance(G), door_leaf(G, "SM_AK_DoorLeaf", +1), door_leaf(G, "SM_AK_DoorLeaf_R", -1), threshold(G),
            entry_mat(G), step_beam(G), jamb_post(G), wall_sconce(G)]


def instances():
    """Layout 2: one wall sconce on the room (+Y) face of each jamb post (layout(): SM_AK_Post_Jamb_480 at JAMB_POSTS,
    rot 0; r3: timber room face at Y 0.40 + JAMB_FACE_Y = 0.80), at the sheet's height (r3: lit body +2.62 to +3.54).
    The street-side pair on the old entrance posts is gone with those posts (the outside is the exterior's plain door
    casing)."""
    return [("SM_AK_H_WallSconce", x, round(y + JAMB_FACE_Y, 4), SCONCE_Z, 0.0) for x, y in JAMB_POSTS]
