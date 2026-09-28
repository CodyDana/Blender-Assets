"""M_Shuriken_Master: the one material every form shares.

Knife-grind pass, second round (style pass 2 maintenance, 2026-09-18).  The first knife-grind
round fixed the stepped edge, the face band, the cloud mottle and the loud scratches, but the
same-rig review still found it unlike the reference the user brought ("a sharp shuriken with
some wear n tear"):

* the stars' ground bevels are 2-3x wider than the reference's (its plate is 1.26 mm thick at
  100 mm, ours 3.0 / 2.5 / 1.9 mm, and no grind angle in decision A's 25-35 deg range changes
  that), and the whole width was bright bare steel - a wide chrome / white frame and a white
  arrowhead at every star tip instead of the reference's thin bright line;
* the cavity grime overshot into a speckled soot ring around the hole (3-6x the reference's in
  the top view) while the rest of the face was too clean, and the reference's soft halo in the
  hero comes from SHADING (the plate dishes toward the hole), not from paint;
* the bare bevel was frosted grain plus loud wheel marks; the scratches were bright-dominant.

The recipe (decision C, re-tuned against the reference rendered through the pack's own rig,
ref_rig_scaled100_persp/top, with WorkFiles/shuriken/restyle_pass2/maint/visual_metrics.py):

    coat        linear ~0.10, faintly violet, metallic 1.0, roughness 0.34; a whisper of cast grain
    grind       the knife facets are TWO finishes.  A polished band POLISH_W (0.7 mm) wide next to
                the edge land - the land itself included - is bright, smooth steel (BARE_POLISH,
                roughness POLISH_ROUGHNESS): the reference's thin bright line, ~5 px in the top view.
                The rest of the grind, out to the plate line, is satin, grimy steel near the coat's
                tone (SATIN, roughness SATIN_ROUGHNESS) with soft grime mottling and faint wheel marks,
                so the wide facets of a thick plate no longer read as a chrome frame.  The polished
                band's inner edge wanders +-POLISH_WOBBLE (hand-honed, not machined).  Where the grind
                is not full width - the root run-out into the scallop - the band fades out, so no
                bright sliver ends mid-facet at the arm roots.
    tips        the last TIP_WEAR (2.5 mm) of every point polished, feathered, on the grind only
    nicks       narrow (0.15-0.6 mm) irregular chips into the face along the grind's plate line
    scallops    the scallop chamfers and the hole's deburr lightly brightened; their walls carry
                value / roughness variation and a light brightening along their top edge
    grime       soft, irregular, low-contrast smears (2-6 mm) spread over the whole face at one
                density per unit area on every form (SMEAR_*), a little denser toward the cavities;
                the painted cavity darkening is only CAVITY_DARKEN (the soot ring is gone).  The
                halo round the hole and the notch arcs is SHAPE: a shallow dish (DISH_*) baked into
                the normal map, so it reads in the hero (view-dependent) and not in the top view
    scratches   many fine (0.05-0.12 mm wide) short (2-8 mm) micro-scratches in every direction,
                mostly dirt-filled (dark) and clustered, low individual contrast; a few longer ones
    pits        near-invisible
    rust        at most two sub-pixel, desaturated specks per piece
    normal      the dish, plus the scratches and pits as a faint bump

Bar mode (library 3.8, the throwing spike).  A bar is not a plate: its four long faces are all
coat (the plate formulas would call the vertical ones walls), its cutting part is the point, and
wear runs along the long axis, not out from a centre.  An object that carries
``shuriken_wear_axis`` = 1 (``tag_bar``) switches a handful of INPUTS, never the recipe:

    classes     the surface classes come from the generator's FACE attribute ``shuriken_ground``
                (1 on the arris round, the point facets and the tip flat) instead of |N.z|: the
                ground surfaces are 'knife' (the pack's grind) and every flat face, tail facet and
                the butt is 'plate' (the coat)
    point       the point's cutting edges are its four ridges, so on a point facet the 'distance to
                the outline' is the distance to the nearest ridge: the 0.7 mm polished band runs
                along the ridges and the satin grind fills the rest of the facet (the stars'
                two-finish read; a fully polished 25 mm facet renders as the white arrowhead the
                pass-2 review rejected); the tip is polished over its last BAR_TIP_POLISH (10 mm);
                the arris round and the tip flat are polished
    grind line  computed in object space: distance on a face to the nearest arris-round edge
                (half width - round - |across|) or to the point's grind line (x_point_base - x);
                the nicks sit along it exactly as they sit along a star's grind line
    radius      the tip polish and the wheel marks read x (along the bar) instead of the radius
    scratches   the scratch / pit / speck cells are laid in each face's own plane (x and the
                across coordinate), so a side face gets the same scratch character as the top
    axial wear  ``shuriken_bar_wear0`` .. the point base: toward the point the nick noise rises
                (NICK_AXIAL) and a worn, polished band along the arris edges widens from
                ARRIS_BAND[0] to ARRIS_BAND[0] + ARRIS_BAND[1] (the polished highlight)

Every switch is a Mix with the mode as factor (a * (1 - 0) + b * 0 = a exactly) or an addition of
mode x (...) (x + 0 = x), and an absent property reads 0, so the plate forms bake exactly what they
baked before; only the bar objects carry the new properties.

Everything is procedural in OBJECT space so the bake captures it on LOD0's UV0 and every LOD
agrees.  Form-dependent numbers are read per object: custom properties through Attribute
nodes of type OBJECT (``tag_common``) and four float point attributes the generator writes on
every LOD (``geometry.EDGE_ATTR`` / ``HOLE_ATTR`` / ``SCALLOP_ATTR`` / ``GRIND_ATTR``).  An
object without them gets no nicks and no cavity terms (a missing attribute reads 0).

This material is the bake SOURCE: shuriken_lib.bake writes it into T_Shuriken_<Form>_BC /
_ORM / _N on LOD0's UV0, and the gallery beauty shots render from those textures only.
None of it reaches the FBX, which carries only the Principled scalars.
"""
from __future__ import annotations

import math

import bpy

from .geometry import EDGE_ATTR, GRIND_ATTR, HOLE_ATTR, SCALLOP_ATTR
from .spec import Outline

MATERIAL_NAME = "M_Shuriken_Master"
COAT = (0.097, 0.093, 0.103)          # STYLE_TARGET: linear 0.09-0.11; faintly violet, as the reference renders through the rig
BARE_POLISH = (0.42, 0.425, 0.435)    # the polished band next to the edge land (stored ~0.68)
SATIN = (0.100, 0.098, 0.104)         # the rest of the grind: satin, grimy steel near the coat's tone
BARE_NICK = (0.165, 0.168, 0.176)     # a chip into the face (stored ~0.45: worn steel, not chalk)
BARE_CREST = BARE_POLISH              # (kept for importers of the old names)
BARE_GRIND = SATIN
BARE_INNER = BARE_NICK
BARE_RIM = BARE_POLISH
SCALLOP_LIFT = 0.30                   # scallop / hole chamfers: this far from the coat toward bare steel
RUST = (0.070, 0.050, 0.040)          # dark, desaturated rust (no saturated orange fleck)
COAT_ROUGHNESS = 0.34
POLISH_ROUGHNESS = 0.22
SATIN_ROUGHNESS = 0.47
WALL_ROUGHNESS_GAIN = 0.04
POLISH_W = 0.0007                     # m: the polished band next to the land (the reference's bright line)
POLISH_WOBBLE = 0.00012               # m: +- wander of its inner edge
POLISH_FEATHER = 0.00008              # m: half width of its soft inner edge
TIP_WEAR = 0.0025                     # m: the last 2.5 mm of every point polished (on the grind only)
NICK_DEPTH = (0.00015, 0.0006)        # m: 0.15-0.6 mm into the face (decision C: 0.2-0.8 mm nominal chips)
NICK_SCALE = 420.0                    # 1/m: ~2.4 mm noise features along the grind line
NICK_THRESHOLD = 0.60                 # noise level above which a spot is chipped (~22 % of the line)
CAVITY_DARKEN = 0.0                   # painted darkening at the hole / notch edge (was 0.50: the soot ring)
CAVITY_ROUGH = 0.03                   # roughness added there
GRIME_HOLE_REACH = 0.0045             # m from the hole edge
GRIME_SCALLOP_REACH = 0.0030          # m from the notch arcs
SMEAR_SCALE = (280.0, 110.0)          # 1/m: the smears' two noise scales (~3.5 mm patches, ~9 mm grouping)
SMEAR_COVER = (0.52, 0.66)            # noise window of a smear (lower = more smear)
SMEAR_DARKEN = 0.16                   # the coat x 0.84 at a smear's core
SMEAR_ROUGH = 0.04
SMEAR_CAVITY_BOOST = 0.3              # smear density x (1 + this) at the cavities
FLECK_COVER = (0.61, 0.68)            # fine dirt flecks, one density everywhere (x FLECK_CAVITY at the cavities)
FLECK_DARKEN = 0.30
SPECK = {"scale": 400.0, "presence": 0.55, "r": (0.00006, 0.00015), "darken": 0.50}   # dirt specks, ~1 per 20 mm2
FLECK_CAVITY = 0.3                    # fleck density x (1 + this) at the cavities
DISH_HOLE = (0.00022, 0.0026)         # (depth m, reach m): the plate rolls off toward the hole (quadratic)
DISH_SCALLOP = (0.00020, 0.0026)      # ... and toward the notch arcs
SATIN_MOTTLE = 0.28                   # +-14 % soft grime mottling on the satin grind
GRIND_STREAK = 0.04                   # +-2 % wheel marks across the grind (was 0.10)
WALL_VARIATION = 0.22                 # +-11 % value on the scallop / hole walls
WALL_EDGE_LIFT = 0.35                 # brightening along the walls' top edge, toward worn steel
SCRATCH_AA = 0.00002                  # m: stroke anti-aliasing ramp
SCRATCH_JITTER = 1.1                  # rad: spread of directions inside one scratch cluster
# short micro-scratches: (cell scale 1/m, half-length m, half-width m, presence per cell)
SHORT_SCRATCH = {"scale": 300.0, "half_len": (0.0006, 0.0025), "half_w": (0.000025, 0.000060), "presence": 0.95,
                 "layers": 8, "gain": 0.07, "dark_fraction": 0.62, "dark_gain": 0.34, "cluster": 70.0}
LONG_SCRATCH = {"scale": 36.0, "half_len": (0.0060, 0.0110), "half_w": (0.000030, 0.000050), "presence": 0.16,
                "layers": 1, "gain": 0.10, "dark_fraction": 0.5, "dark_gain": 0.28, "cluster": 0.0}
PIT_FACTOR = 0.85                     # multiplies the local colour
WEAR_FROM_PROP = "shuriken_wear_from"
WEAR_TO_PROP = "shuriken_wear_to"
POINTS_PROP = "shuriken_points"
HUB_PROP = "shuriken_hub_r"
TIP_R_PROP = "shuriken_tip_r"
CHAMFER_PROP = "shuriken_chamfer"     # the knife grind's plan width (m)
SCALLOP_PROP = "shuriken_scallop_w"   # the scallop chamfer's plan width (m; 0 without scallops)
HOLE_W_PROP = "shuriken_hole_w"       # the hole deburr's plan width (m)
CENTRE_PROP = "shuriken_centre_r"     # reach of the centre grime (m)
LAND_PROP = "shuriken_land"           # the edge land (m)
HALF_T_PROP = "shuriken_half_t"       # half the plate thickness (m)
WALL_TOP_PROP = "shuriken_wall_top"   # depth of the scallop / hole wall tops below the face (m)
RUST_PROPS = tuple(f"shuriken_rust{i}_{k}" for i in (1, 2) for k in ("x", "y", "z", "r"))
PROPS = (WEAR_FROM_PROP, WEAR_TO_PROP, POINTS_PROP, HUB_PROP, TIP_R_PROP, CHAMFER_PROP, SCALLOP_PROP, HOLE_W_PROP,
         CENTRE_PROP, LAND_PROP, HALF_T_PROP, WALL_TOP_PROP) + RUST_PROPS
RUST_R = (0.00011, 0.00009)           # m: sub-pixel at the gallery's ~7 px/mm
# Bar mode (library 3.8): see the module docstring.
WEAR_AXIS_PROP = "shuriken_wear_axis"  # 1.0 = a bar along +X (absent / 0 = the plate forms' radial wear)
BAR_A_PROP = "shuriken_bar_a"          # half the section (m)
BAR_ROUND_PROP = "shuriken_bar_round"  # arris round radius (m)
BAR_POINT_PROP = "shuriken_bar_point"  # object x of the point base (the point's grind line)
BAR_BUTT_PROP = "shuriken_bar_butt"    # object x of the butt
BAR_TAIL_PROP = "shuriken_bar_tail"    # object x of the tail taper's base
BAR_END_PROP = "shuriken_bar_end"      # half the butt square (m)
BAR_WEAR0_PROP = "shuriken_bar_wear0"  # object x where the axial wear starts ramping toward the point
BAR_PROPS = (WEAR_AXIS_PROP, BAR_A_PROP, BAR_ROUND_PROP, BAR_POINT_PROP, BAR_BUTT_PROP, BAR_TAIL_PROP, BAR_END_PROP,
             BAR_WEAR0_PROP)
GROUND_ATTR = "shuriken_ground"        # float, FACE: 1 on a bar's ground surfaces (arris round, point facets, tip flat)
ARRIS_BAND = (0.00008, 0.00022)        # m: worn polished band on the faces along the arris edges (+ this toward the point)
ARRIS_WOBBLE = 0.00005                 # m: +- wander of that band's edge
BAR_TIP_POLISH = 0.010                 # m: a bar's point is polished over its last 10 mm (a star's tip: TIP_WEAR)
NICK_AXIAL = 0.06                      # nick noise raised by up to this toward the point (more chips at the business end)


def wear_range(o: Outline):
    """(from, to) radius in metres over which the points are polished."""
    return o.r_tip - TIP_WEAR, o.r_tip


def tag_common(obj, points: int, r_tip: float, r_hub: float, chamfer_w: float, scallop_w: float = 0.0,
               hole_w: float = 0.0, centre_r: float = 0.0, land: float = 0.00015, rust=(), half_t: float = 0.0,
               wall_top: float = 0.0) -> None:
    """Write the per-form numbers the material reads (metres, floats) on ``obj``.

    ``rust`` is up to two (x, y, face, radius) specks in object space; face +1 = top, -1 = bottom.
    """
    obj[WEAR_FROM_PROP] = float(r_tip - TIP_WEAR)
    obj[WEAR_TO_PROP] = float(r_tip)
    obj[POINTS_PROP] = float(points)
    obj[HUB_PROP] = float(r_hub)
    obj[TIP_R_PROP] = float(r_tip)
    obj[CHAMFER_PROP] = float(chamfer_w)
    obj[SCALLOP_PROP] = float(scallop_w)
    obj[HOLE_W_PROP] = float(hole_w)
    obj[CENTRE_PROP] = float(centre_r)
    obj[LAND_PROP] = float(land)
    obj[HALF_T_PROP] = float(half_t)
    obj[WALL_TOP_PROP] = float(wall_top)
    specks = list(rust)[:2] + [(0.0, 0.0, 0.0, 0.0)] * (2 - len(list(rust)[:2]))
    for i, (x, y, face, radius) in enumerate(specks, start=1):
        obj[f"shuriken_rust{i}_x"] = float(x)
        obj[f"shuriken_rust{i}_y"] = float(y)
        obj[f"shuriken_rust{i}_z"] = float(face)
        obj[f"shuriken_rust{i}_r"] = float(radius)


def tag_object(obj, o: Outline) -> None:
    """A radial star's tags: two sub-pixel rust specks, one on the top face of arm 1's plate, one on
    the bottom face of the hub between arms 2 and 3."""
    n = o.n
    x1, y1 = 0.5 * (o.x_run + o.x_taper), 0.35 * (o.half_w - o.chamfer_w)
    a1 = 2.0 * math.pi / n
    r2 = 0.5 * (o.r_hole + o.hole_chamfer.width + o.r_hub - o.scallop.width)
    a2 = 2.0 * math.pi * 2 / n + math.pi / n
    rust = ((x1 * math.cos(a1) - y1 * math.sin(a1), x1 * math.sin(a1) + y1 * math.cos(a1), 1.0, RUST_R[0]),
            (r2 * math.cos(a2), r2 * math.sin(a2), -1.0, RUST_R[1]))
    wall_top = 0.5 * (o.scallop.wall_top_drop + o.hole_chamfer.wall_top_drop)
    tag_common(obj, o.n, o.r_tip, o.r_hub, o.chamfer_w, scallop_w=o.scallop.width, hole_w=o.hole_chamfer.width,
               centre_r=o.r_hub + 0.005, land=o.edge_land, rust=rust, half_t=o.half_t, wall_top=wall_top)


def tag_bar(obj, o) -> None:
    """A bar's tags (bar_spec.BarOutline ``o``): the common set with the point on +X as the 'tip', no hole,
    no scallop and no knife width (the bar's grind is its ground faces), two sub-pixel rust specks (one on the
    top face toward the point, one on the bottom face toward the butt), and the bar-mode properties."""
    rust = ((o.x_point_base - 0.038, 0.0009, 1.0, RUST_R[0]), (o.x_butt + 0.055, -0.0012, -1.0, RUST_R[1]))
    tag_common(obj, 4, o.x_tip, o.a, 0.0, scallop_w=0.0, hole_w=0.0, centre_r=0.0, land=2.0 * o.tau, rust=rust,
               half_t=o.a, wall_top=0.0)
    obj[WEAR_AXIS_PROP] = 1.0
    obj[BAR_A_PROP] = float(o.a)
    obj[BAR_ROUND_PROP] = float(o.rho)
    obj[BAR_POINT_PROP] = float(o.x_point_base)
    obj[BAR_BUTT_PROP] = float(o.x_butt)
    obj[BAR_TAIL_PROP] = float(o.x_tail_base)
    obj[BAR_END_PROP] = float(o.e)
    obj[BAR_WEAR0_PROP] = float(o.x_point_base - o.axial_wear)
    obj[WEAR_FROM_PROP] = float(o.x_tip - BAR_TIP_POLISH)       # the point's polished tip ramps in over its last 10 mm


class _Tree:
    """Small helpers over one node tree: math, ranges, noises, hashes - each call one node."""

    def __init__(self, tree):
        self.tree = tree
        self.count = 0

    def _place(self, node):
        self.count += 1
        node.location = (200 * (self.count % 12) - 1400, -160 * (self.count // 12))
        return node

    def new(self, kind: str):
        return self._place(self.tree.nodes.new(kind))

    def link(self, a, b):
        self.tree.links.new(a, b)

    def math(self, op: str, a, b=None, c=None, clamp: bool = False):
        node = self.new("ShaderNodeMath")
        node.operation = op
        node.use_clamp = clamp
        for socket, value in zip(node.inputs, (a, b, c)):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                socket.default_value = float(value)
            else:
                self.link(value, socket)
        return node.outputs["Value"]

    def vmath(self, op: str, a, b=None):
        node = self.new("ShaderNodeVectorMath")
        node.operation = op
        self.link(a, node.inputs[0])
        if b is not None:
            if isinstance(b, tuple):
                node.inputs[1].default_value = b
            else:
                self.link(b, node.inputs[1])
        return node.outputs["Vector"] if op not in ("LENGTH", "DOT_PRODUCT", "DISTANCE") else node.outputs["Value"]

    def combine(self, x, y, z):
        node = self.new("ShaderNodeCombineXYZ")
        for socket, value in zip(node.inputs, (x, y, z)):
            if isinstance(value, (int, float)):
                socket.default_value = float(value)
            else:
                self.link(value, socket)
        return node.outputs["Vector"]

    def separate(self, vector):
        node = self.new("ShaderNodeSeparateXYZ")
        self.link(vector, node.inputs["Vector"])
        return node.outputs["X"], node.outputs["Y"], node.outputs["Z"]

    def range(self, value, from_min, from_max, to_min=0.0, to_max=1.0, smooth: bool = False, clamp: bool = True):
        node = self.new("ShaderNodeMapRange")
        node.interpolation_type = "SMOOTHSTEP" if smooth else "LINEAR"
        node.clamp = clamp
        for name, v in (("Value", value), ("From Min", from_min), ("From Max", from_max),
                        ("To Min", to_min), ("To Max", to_max)):
            if isinstance(v, (int, float)):
                node.inputs[name].default_value = float(v)
            else:
                self.link(v, node.inputs[name])
        return node.outputs["Result"]

    def attribute(self, name: str, kind: str = "OBJECT"):
        node = self.new("ShaderNodeAttribute")
        node.attribute_type = kind
        node.attribute_name = name
        return node.outputs["Fac"]

    def noise(self, vector, scale: float, detail: float = 2.0, roughness: float = 0.5, dims: str = "3D", w=None):
        node = self.new("ShaderNodeTexNoise")
        node.noise_dimensions = dims
        node.inputs["Scale"].default_value = scale
        node.inputs["Detail"].default_value = detail
        node.inputs["Roughness"].default_value = roughness
        if vector is not None:
            self.link(vector, node.inputs["Vector"])
        if w is not None:
            if isinstance(w, (int, float)):
                node.inputs["W"].default_value = float(w)
            else:
                self.link(w, node.inputs["W"])
        return node.outputs["Fac"]

    def white(self, vector, w: float):
        """White Noise (4D) of a vector plus a constant W: an independent hash per W."""
        node = self.new("ShaderNodeTexWhiteNoise")
        node.noise_dimensions = "4D"
        self.link(vector, node.inputs["Vector"])
        node.inputs["W"].default_value = w
        return node.outputs["Value"]

    def voronoi_cells(self, vector, scale: float):
        """The two nearest Voronoi feature points (F1, F2) of ``vector``, in input space."""
        points = []
        for feature in ("F1", "F2"):
            node = self.new("ShaderNodeTexVoronoi")
            node.voronoi_dimensions = "3D"
            node.feature = feature
            node.inputs["Scale"].default_value = scale
            node.inputs["Randomness"].default_value = 1.0
            self.link(vector, node.inputs["Vector"])
            points.append(node.outputs["Position"])
        return points

    def voronoi_cell(self, vector, scale: float):
        """(local offset from the F1 cell's feature point, the feature point), input space."""
        node = self.new("ShaderNodeTexVoronoi")
        node.voronoi_dimensions = "3D"
        node.feature = "F1"
        node.inputs["Scale"].default_value = scale
        self.link(vector, node.inputs["Vector"])
        local = self.vmath("SUBTRACT", vector, node.outputs["Position"])
        return local, node.outputs["Position"]

    def scale_colour(self, colour: tuple, factor):
        """A constant colour times a scalar socket (Vector Math SCALE; a vector feeds a colour socket)."""
        node = self.new("ShaderNodeVectorMath")
        node.operation = "SCALE"
        node.inputs[0].default_value = colour
        self.link(factor, node.inputs["Scale"])
        return node.outputs["Vector"]

    def scale_socket(self, vector, factor):
        """A colour / vector socket times a scalar (socket or constant)."""
        node = self.new("ShaderNodeVectorMath")
        node.operation = "SCALE"
        self.link(vector, node.inputs[0])
        if isinstance(factor, (int, float)):
            node.inputs["Scale"].default_value = float(factor)
        else:
            self.link(factor, node.inputs["Scale"])
        return node.outputs["Vector"]

    def mix_rgb(self, factor, a, b):
        node = self.new("ShaderNodeMix")
        node.data_type = "RGBA"
        node.clamp_factor = True
        if isinstance(factor, (int, float)):
            node.inputs["Factor"].default_value = float(factor)
        else:
            self.link(factor, node.inputs["Factor"])
        for index, value in ((6, a), (7, b)):
            if isinstance(value, tuple):
                node.inputs[index].default_value = (*value, 1.0)
            else:
                self.link(value, node.inputs[index])
        return node.outputs[2]

    def mix_f(self, factor, a, b):
        node = self.new("ShaderNodeMix")
        node.data_type = "FLOAT"
        node.clamp_factor = True
        for name, value in (("Factor", factor), ("A", a), ("B", b)):
            if isinstance(value, (int, float)):
                node.inputs[name].default_value = float(value)
            else:
                self.link(value, node.inputs[name])
        return node.outputs["Result"]


def _stroke(t: _Tree, lx, ly, angle, half_len, half_w):
    """One straight stroke through the cell frame's origin: a 0..1 mask faded toward its ends.

    ``angle``, ``half_len`` and ``half_w`` are sockets (per cell); the stroke has a
    SCRATCH_AA anti-aliasing ramp across it, and its value falls off smoothly over the last
    45 % of its length, so a scratch thins out rather than stopping dead.
    """
    ca, sa = t.math("COSINE", angle), t.math("SINE", angle)
    along = t.math("ADD", t.math("MULTIPLY", lx, ca), t.math("MULTIPLY", ly, sa))
    across = t.math("SUBTRACT", t.math("MULTIPLY", ly, ca), t.math("MULTIPLY", lx, sa))
    line = t.range(t.math("ABSOLUTE", across), t.math("ADD", half_w, SCRATCH_AA), t.math("SUBTRACT", half_w, SCRATCH_AA))
    fade = t.range(t.math("ABSOLUTE", along), half_len, t.math("MULTIPLY", half_len, 0.55), smooth=True)
    return t.math("MULTIPLY", line, fade)


def _scratch_family(t: _Tree, x, y, z, seed: float, cfg: dict):
    """One family of straight scratches: (light, dark) 0..1 masks.

    Each Voronoi cell that is "on" carries one stroke through its feature point at a random
    angle, length, width and strength; the strokes of BOTH nearest cells are drawn, so a
    stroke that reaches into the neighbouring cell is not cut at the border.  A per-cell hash
    makes ``dark_fraction`` of them darker (dirt-filled) instead of lighter.  With a
    ``cluster`` scale the presence of a cell is modulated by a slow noise at its feature
    point, so the scratches gather in clusters instead of an even field.
    """
    vec = t.combine(x, y, t.math("MULTIPLY_ADD", z, 8.0, seed))
    light, dark = None, None
    for cell in t.voronoi_cells(vec, cfg["scale"]):
        local = t.vmath("SUBTRACT", vec, cell)
        lx, ly, _lz = t.separate(local)
        if cfg.get("cluster"):
            # scratches of one patch share a direction (a wipe, a sheath, a pocket), +-SCRATCH_JITTER
            base = t.math("MULTIPLY", t.noise(cell, 0.5 * cfg["cluster"], 1.0, 0.5, dims="4D", w=seed), 4.0 * math.pi)
            angle = t.math("MULTIPLY_ADD", t.math("SUBTRACT", t.white(cell, 1.0 + seed), 0.5), SCRATCH_JITTER, base)
        else:
            angle = t.math("MULTIPLY", t.white(cell, 1.0 + seed), math.pi)
        lo, hi = cfg["half_len"]
        half_len = t.math("MULTIPLY_ADD", t.white(cell, 2.0 + seed), hi - lo, lo)
        wlo, whi = cfg["half_w"]
        half_w = t.math("MULTIPLY_ADD", t.white(cell, 3.0 + seed), whi - wlo, wlo)
        strength = t.math("MULTIPLY_ADD", t.white(cell, 4.0 + seed), 0.6, 0.4)
        presence = cfg["presence"]
        if cfg.get("cluster"):
            presence = t.math("MULTIPLY", presence,
                              t.range(t.noise(cell, cfg["cluster"], 1.0, 0.5), 0.38, 0.62))
        on = t.math("LESS_THAN", t.white(cell, 5.0 + seed), presence)
        mask = t.math("MULTIPLY", t.math("MULTIPLY", _stroke(t, lx, ly, angle, half_len, half_w), strength), on)
        is_dark = t.math("LESS_THAN", t.white(cell, 6.0 + seed), cfg["dark_fraction"])
        l_mask = t.math("MULTIPLY", mask, t.math("SUBTRACT", 1.0, is_dark))
        d_mask = t.math("MULTIPLY", mask, is_dark)
        light = l_mask if light is None else t.math("MAXIMUM", light, l_mask)
        dark = d_mask if dark is None else t.math("MAXIMUM", dark, d_mask)
    return light, dark


def _scratches(t: _Tree, x, y, z, cfg: dict, seed0: float):
    light, dark = None, None
    for layer in range(cfg["layers"]):
        l_mask, d_mask = _scratch_family(t, x, y, z, seed0 + 37.0 * layer, cfg)
        light = l_mask if light is None else t.math("MAXIMUM", light, l_mask)
        dark = d_mask if dark is None else t.math("MAXIMUM", dark, d_mask)
    return light, dark


def _speck_layer(t: _Tree, x, y, z, seed: float, scale: float, presence, r_min: float, r_max: float,
                 soft: float = 0.00002):
    """Sparse round specks: one per Voronoi cell with probability ``presence``, radius r_min..r_max."""
    vec = t.combine(x, y, t.math("MULTIPLY_ADD", z, 8.0, seed))
    local, cell = t.voronoi_cell(vec, scale)
    lx, ly, _lz = t.separate(local)
    dist = t.math("SQRT", t.math("ADD", t.math("MULTIPLY", lx, lx), t.math("MULTIPLY", ly, ly)))   # in-plane
    radius = t.math("MULTIPLY_ADD", t.white(cell, 6.0 + seed), r_max - r_min, r_min)
    inside = t.range(dist, t.math("ADD", radius, soft), t.math("SUBTRACT", radius, soft))
    on = t.math("LESS_THAN", t.white(cell, 5.0 + seed), presence)
    return t.math("MULTIPLY", inside, on)


def _rust_speck(t: _Tree, x, y, z, index: int, ragged):
    """One placed rust speck (object custom properties shuriken_rust<i>_x/_y/_z/_r); z is the face."""
    cx, cy = t.attribute(f"shuriken_rust{index}_x"), t.attribute(f"shuriken_rust{index}_y")
    face, radius = t.attribute(f"shuriken_rust{index}_z"), t.attribute(f"shuriken_rust{index}_r")
    dx, dy = t.math("SUBTRACT", x, cx), t.math("SUBTRACT", y, cy)
    dist = t.math("SQRT", t.math("ADD", t.math("MULTIPLY", dx, dx), t.math("MULTIPLY", dy, dy)))
    dist = t.math("MULTIPLY", dist, t.math("MULTIPLY_ADD", ragged, 0.9, 0.55))          # a blotch, not a disc
    inside = t.range(dist, t.math("ADD", radius, 0.00003), t.math("SUBTRACT", radius, 0.00003))
    on_face = t.math("GREATER_THAN", t.math("MULTIPLY", z, face), 0.0)
    return t.math("MULTIPLY", inside, on_face)


def build_material():
    """Create (or rebuild in place) M_Shuriken_Master and return it."""
    mat = bpy.data.materials.get(MATERIAL_NAME) or bpy.data.materials.new(MATERIAL_NAME)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    t = _Tree(tree)

    out = t.new("ShaderNodeOutputMaterial")
    out.location = (2400, 0)
    bsdf = t.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (2100, 0)
    # Kept as defaults as well as linked: the FBX exporter reads default_value.
    bsdf.inputs["Base Color"].default_value = (*COAT, 1.0)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = COAT_ROUGHNESS
    t.link(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # --- inputs: object position, radius, shading normal, the generator's attributes, the form's props
    coord = t.new("ShaderNodeTexCoord")
    obj = coord.outputs["Object"]
    x, y, z = t.separate(obj)
    flat = t.combine(x, y, 0.0)
    radius = t.vmath("LENGTH", flat)
    abs_z = t.math("ABSOLUTE", z)
    geom = t.new("ShaderNodeNewGeometry")
    _nx, _ny, nz_raw = t.separate(geom.outputs["Normal"])
    nz = t.math("ABSOLUTE", nz_raw)
    edge = t.attribute(EDGE_ATTR, "GEOMETRY")
    hole = t.attribute(HOLE_ATTR, "GEOMETRY")
    scallop = t.attribute(SCALLOP_ATTR, "GEOMETRY")
    grind = t.attribute(GRIND_ATTR, "GEOMETRY")
    knife_w = t.attribute(CHAMFER_PROP)
    scallop_w = t.attribute(SCALLOP_PROP)
    hole_w = t.attribute(HOLE_W_PROP)
    land = t.attribute(LAND_PROP)
    half_t = t.attribute(HALF_T_PROP)
    wall_top = t.attribute(WALL_TOP_PROP)
    wear_from = t.attribute(WEAR_FROM_PROP)
    tip_r = t.attribute(TIP_R_PROP)

    # --- bar mode (library 3.8): switch the INPUTS a bar reads differently.  mode is 0 on every plate
    # form (the property is absent), and each switch is exact there: mix(a, b, 0) = a, x + 0 x (...) = x.
    mode = t.attribute(WEAR_AXIS_PROP)
    _tnx, tny, tnz = t.separate(geom.outputs["True Normal"])
    side_raw = t.math("GREATER_THAN", t.math("ABSOLUTE", tny), t.math("ABSOLUTE", tnz))   # a +-Y face of the bar
    side = t.math("MULTIPLY", mode, side_raw)
    ground = t.attribute(GROUND_ATTR, "GEOMETRY")
    nz = t.mix_f(mode, nz, t.math("MULTIPLY_ADD", ground, -0.5, 1.0))        # ground 0.5 -> 'facet', else 1 -> 'plate'
    bar_a, bar_round = t.attribute(BAR_A_PROP), t.attribute(BAR_ROUND_PROP)
    bar_point, bar_butt = t.attribute(BAR_POINT_PROP), t.attribute(BAR_BUTT_PROP)
    bar_tail, bar_end = t.attribute(BAR_TAIL_PROP), t.attribute(BAR_END_PROP)
    across = t.mix_f(side_raw, t.math("ABSOLUTE", y), abs_z)                  # |z| on a +-Y face, |y| elsewhere
    slope = t.math("DIVIDE", t.math("SUBTRACT", bar_a, bar_end), t.math("SUBTRACT", bar_tail, bar_butt))
    half_w = t.math("MINIMUM", bar_a, t.math("MULTIPLY_ADD", t.math("SUBTRACT", x, bar_butt), slope, bar_end))
    grind_bar = t.math("MINIMUM", t.math("SUBTRACT", t.math("SUBTRACT", half_w, bar_round), across),
                       t.math("SUBTRACT", bar_point, x))
    grind = t.mix_f(mode, grind, grind_bar)
    # the point's cutting edges are its four ridges: 'distance to the outline' on a point facet is the distance
    # to the nearest ridge (the facet's half width at x minus |across|), so the pack's 0.7 mm polished band runs
    # along the ridges and the rest of each facet is the satin grind - the stars' two-finish read, not a white
    # arrowhead; 0 on the round and the tip flat (polished)
    point_slope = t.math("DIVIDE", t.math("SUBTRACT", bar_a, t.math("MULTIPLY", land, 0.5)),
                         t.math("SUBTRACT", tip_r, bar_point))
    point_half = t.math("MINIMUM", bar_a, t.math("MULTIPLY_ADD", t.math("SUBTRACT", x, bar_point),
                                                 t.math("MULTIPLY", point_slope, -1.0), bar_a))
    edge = t.mix_f(mode, edge, t.math("MAXIMUM", t.math("SUBTRACT", point_half, across), 0.0))
    radius = t.mix_f(mode, radius, x)                                         # the tip polish runs along the bar
    ys = t.mix_f(side, y, z)                                                  # scratch cells in each face's plane
    zs = t.mix_f(side, z, y)
    axial = t.math("MULTIPLY", mode, t.range(x, t.attribute(BAR_WEAR0_PROP), bar_point, smooth=True))

    # --- surface classes.  The plate is exactly |N.z| = 1 (hard-edged flat faces), the walls 0,
    # every ground facet in between.  Which facet is which comes from the distance attributes:
    # the scallop chamfer lies within its width of the notch arcs, the hole deburr within its width
    # of the hole, everything else is knife grind.
    facet = t.math("MULTIPLY", t.range(nz, 0.02, 0.06), t.range(nz, 0.995, 0.975))
    wall = t.range(nz, 0.05, 0.01)
    plate = t.range(nz, 0.975, 0.995)
    has_scallop = t.math("GREATER_THAN", scallop_w, 0.0)
    near_scallop = t.math("MULTIPLY", t.range(scallop, t.math("ADD", scallop_w, 0.00015),
                                              t.math("ADD", scallop_w, 0.00004)), has_scallop)
    near_hole = t.range(hole, t.math("ADD", hole_w, 0.00015), t.math("ADD", hole_w, 0.00004))
    cutter = t.math("MULTIPLY", t.math("SUBTRACT", 1.0, near_scallop), t.math("SUBTRACT", 1.0, near_hole))
    knife = t.math("MULTIPLY", facet, cutter)
    # The grind is FULL width where the plan distance to the outline plus the distance to the grind's
    # plate line adds up to the knife width; on the root run-out (the grind narrowing into the scallop
    # chamfer) it is less, and the polished band and the land highlight fade out there.
    local_w = t.math("ADD", edge, t.math("ABSOLUTE", grind))
    full = t.range(local_w, t.math("SUBTRACT", knife_w, 0.00030), t.math("SUBTRACT", knife_w, 0.00012))
    on_outline = t.range(edge, 0.00003, 0.000005)
    low = t.range(abs_z, t.math("ADD", t.math("MULTIPLY", land, 0.5), 0.00006),
                  t.math("ADD", t.math("MULTIPLY", land, 0.5), 0.00002))
    crest = t.math("MULTIPLY", t.math("MULTIPLY", wall, on_outline), t.math("MULTIPLY", low, cutter))
    crest = t.math("MULTIPLY", crest, full)
    lifted = t.math("MULTIPLY", facet, t.math("MAXIMUM", near_scallop, near_hole))
    side_wall = t.math("MULTIPLY", wall, t.math("SUBTRACT", 1.0, crest))   # scallop, hole and run-out walls

    # --- noises
    grain = t.range(t.noise(obj, 2600.0, 3.0, 0.6), 0.30, 0.70)                 # ~0.4 mm cast grain
    fine = t.range(t.noise(obj, 1800.0, 3.0, 0.55), 0.30, 0.70)                 # ~0.55 mm
    patch = t.range(t.noise(obj, 520.0, 2.0, 0.5), 0.35, 0.65)                  # ~1.9 mm patchiness
    mottle = t.range(t.noise(obj, 650.0, 3.0, 0.55), 0.25, 0.75)                # ~1.5 mm grime mottle (satin grind)
    nick_noise = t.math("MULTIPLY_ADD", axial, NICK_AXIAL, t.noise(obj, NICK_SCALE, 3.0, 0.55))
    wobble = t.noise(obj, 900.0, 2.0, 0.5)                                       # the polished band's inner edge
    # wheel marks on the grind: fast along the radius, slow around it - fine lines across a facet
    streak = t.range(t.noise(t.combine(t.math("MULTIPLY", radius, 2600.0), t.math("MULTIPLY", x, 60.0),
                                       t.math("MULTIPLY", y, 60.0)), 1.0, 2.0, 0.55), 0.30, 0.70)
    # smears: soft, irregular 2-6 mm patches over the whole face - a detailed noise through a window,
    # its density grouped by a slower noise so the face is neither even nor a cloud
    smear_raw = t.math("MULTIPLY_ADD", t.noise(obj, SMEAR_SCALE[0], 5.0, 0.66), 0.75,
                       t.math("MULTIPLY", t.noise(obj, SMEAR_SCALE[1], 2.0, 0.5), 0.25))
    fleck_raw = t.noise(obj, 3400.0, 4.0, 0.7)
    wall_noise = t.range(t.noise(obj, 1100.0, 3.0, 0.6), 0.28, 0.72)

    # --- nicks: chips into the face along the grind's plate line.  GRIND_ATTR is 0 on the line and
    # grows into the face; where the slow nick noise rises past its threshold the face is chipped
    # to a depth of 0.15-0.6 mm, the chip's outline broken by the fine noise.
    chip = t.range(nick_noise, NICK_THRESHOLD, NICK_THRESHOLD + 0.16)
    present = t.math("GREATER_THAN", nick_noise, NICK_THRESHOLD)
    depth = t.math("MULTIPLY", present, t.math("MULTIPLY_ADD", t.math("POWER", chip, 0.8),
                                               NICK_DEPTH[1] - NICK_DEPTH[0], NICK_DEPTH[0]))
    depth = t.math("MULTIPLY", depth, t.math("MULTIPLY_ADD", fine, 0.5, 0.75))
    nick = t.math("MULTIPLY", plate, t.range(grind, t.math("ADD", depth, 0.00002), t.math("SUBTRACT", depth, 0.00002)))
    nick = t.math("MULTIPLY", nick, t.math("GREATER_THAN", grind, -0.0005))

    # --- the grind's two finishes: a polished band next to the land, satin steel beyond it
    band_edge = t.math("MULTIPLY_ADD", t.math("SUBTRACT", wobble, 0.5), 2.0 * POLISH_WOBBLE, POLISH_W)
    polish = t.range(edge, t.math("ADD", band_edge, POLISH_FEATHER), t.math("SUBTRACT", band_edge, POLISH_FEATHER),
                     smooth=True)
    polish = t.math("MULTIPLY", t.math("MULTIPLY", polish, knife), full)
    # tips: the last TIP_WEAR of every point polished, feathered, on the grind only (past the apex the
    # point is all grind, so the mask follows the grind boundary and never steps onto the face)
    tip = t.range(radius, wear_from, t.math("SUBTRACT", tip_r, 0.0010), smooth=True)
    tip = t.math("MULTIPLY", tip, t.math("MAXIMUM", knife, crest))
    polish = t.math("MAXIMUM", t.math("MAXIMUM", polish, crest), tip, clamp=True)
    # bar mode: a worn, polished band on the faces along the arris edges (and round the point's grind line),
    # widening toward the point - the arris's polished highlight.  0 x (...) = 0 on the plate forms.
    band_w = t.math("MULTIPLY_ADD", axial, ARRIS_BAND[1], ARRIS_BAND[0])
    band_w = t.math("MULTIPLY_ADD", t.math("SUBTRACT", wobble, 0.5), 2.0 * ARRIS_WOBBLE, band_w)
    worn = t.range(grind, t.math("ADD", band_w, POLISH_FEATHER), t.math("SUBTRACT", band_w, POLISH_FEATHER), smooth=True)
    worn = t.math("MULTIPLY", t.math("MULTIPLY", worn, plate), mode)
    polish = t.math("MAXIMUM", polish, worn)
    satin = t.math("MULTIPLY", knife, t.math("SUBTRACT", 1.0, polish))
    bare = t.math("MAXIMUM", knife, crest)

    # --- grime: smears over the whole face (one density per unit area on every form), a little denser
    # toward the cavities; the painted cavity darkening itself is small - the halo is the dish below
    hole_term = t.range(hole, 0.0, GRIME_HOLE_REACH, 1.0, 0.0, smooth=True)
    scallop_term = t.math("MULTIPLY", t.range(scallop, 0.0, GRIME_SCALLOP_REACH, 1.0, 0.0, smooth=True), has_scallop)
    cavity = t.math("MAXIMUM", hole_term, scallop_term)
    cavity = t.math("MULTIPLY", cavity, t.math("SUBTRACT", 1.0, wall))
    cover_lo = t.math("MULTIPLY_ADD", cavity, -0.06, SMEAR_COVER[0])
    smear = t.range(smear_raw, cover_lo, t.math("ADD", cover_lo, SMEAR_COVER[1] - SMEAR_COVER[0]), smooth=True)
    smear = t.math("MULTIPLY", smear, t.math("MULTIPLY_ADD", cavity, SMEAR_CAVITY_BOOST, 1.0))
    smear = t.math("MINIMUM", smear, 1.0)
    fleck_lo = t.math("MULTIPLY_ADD", cavity, -0.03, FLECK_COVER[0])
    fleck = t.range(fleck_raw, fleck_lo, t.math("ADD", fleck_lo, FLECK_COVER[1] - FLECK_COVER[0]))
    fleck = t.math("MINIMUM", t.math("MULTIPLY", fleck, t.math("MULTIPLY_ADD", cavity, FLECK_CAVITY, 1.0)), 1.0)

    # --- scratches (short micro-scratches everywhere, mostly dirt-filled and clustered; a few long ones),
    # pits, rust
    s_light, s_dark = _scratches(t, x, ys, zs, SHORT_SCRATCH, 0.0)
    l_light, l_dark = _scratches(t, x, ys, zs, LONG_SCRATCH, 211.0)
    on_grind = t.math("MULTIPLY_ADD", bare, -0.55, 1.0)                           # quieter on the grind
    scratch_up = t.math("MULTIPLY", t.math("MAXIMUM", t.math("MULTIPLY", s_light, SHORT_SCRATCH["gain"]),
                                           t.math("MULTIPLY", l_light, LONG_SCRATCH["gain"])), on_grind)
    scratch_down = t.math("MULTIPLY", t.math("MAXIMUM", t.math("MULTIPLY", s_dark, SHORT_SCRATCH["dark_gain"]),
                                             t.math("MULTIPLY", l_dark, LONG_SCRATCH["dark_gain"])), on_grind)
    pits = _speck_layer(t, x, ys, zs, 11.0, 350.0, 0.10, 0.00004, 0.00009)
    specks = _speck_layer(t, x, ys, zs, 29.0, SPECK["scale"], SPECK["presence"], SPECK["r"][0], SPECK["r"][1],
                          soft=0.00003)
    specks = t.math("MULTIPLY", specks, t.math("MULTIPLY", plate, t.math("SUBTRACT", 1.0, bare)))
    rag = t.range(t.noise(obj, 2200.0, 3.0, 0.6), 0.30, 0.70)
    rust = t.math("MAXIMUM", _rust_speck(t, x, y, z, 1, rag), _rust_speck(t, x, y, z, 2, rag))
    rust = t.math("MULTIPLY", rust, plate)

    # --- base colour
    coat_k = t.math("MULTIPLY_ADD", grain, 0.06, 0.97)
    coat_k = t.math("MULTIPLY", coat_k, t.math("MULTIPLY_ADD", cavity, -CAVITY_DARKEN, 1.0))
    coat_k = t.math("MULTIPLY", coat_k, t.math("MULTIPLY_ADD", smear, -SMEAR_DARKEN, 1.0))
    coat_k = t.math("MULTIPLY", coat_k, t.math("MULTIPLY_ADD", fleck, -FLECK_DARKEN, 1.0))
    coat_k = t.math("MULTIPLY", coat_k, t.math("MULTIPLY_ADD", specks, -SPECK["darken"], 1.0))
    # scallop / hole walls: value variation and a light brightening along their top edge
    wall_k = t.math("MULTIPLY_ADD", t.math("SUBTRACT", wall_noise, 0.5), WALL_VARIATION, 1.0)
    coat_k = t.math("MULTIPLY", coat_k, t.mix_f(side_wall, 1.0, wall_k))
    coat_c = t.scale_colour(COAT, coat_k)
    top_edge = t.range(abs_z, t.math("SUBTRACT", t.math("SUBTRACT", half_t, wall_top), 0.00025),
                       t.math("SUBTRACT", half_t, wall_top), smooth=True)
    wall_lift = t.math("MULTIPLY", t.math("MULTIPLY", side_wall, top_edge),
                       t.math("MULTIPLY_ADD", patch, 0.6 * WALL_EDGE_LIFT, 0.7 * WALL_EDGE_LIFT))
    coat_c = t.mix_rgb(wall_lift, coat_c, BARE_NICK)
    satin_k = t.math("MULTIPLY_ADD", t.math("SUBTRACT", mottle, 0.5), SATIN_MOTTLE, 1.0)
    satin_k = t.math("MULTIPLY", satin_k, t.math("MULTIPLY_ADD", streak, GRIND_STREAK, 1.0 - 0.5 * GRIND_STREAK))
    satin_k = t.math("MULTIPLY", satin_k, t.math("MULTIPLY_ADD", smear, -0.5 * SMEAR_DARKEN, 1.0))
    satin_c = t.scale_colour(SATIN, satin_k)
    polish_c = t.scale_colour(BARE_POLISH, t.math("MULTIPLY_ADD", streak, 0.5 * GRIND_STREAK, 1.0 - 0.25 * GRIND_STREAK))
    lift_c = t.mix_rgb(t.math("MULTIPLY", SCALLOP_LIFT, t.math("MULTIPLY_ADD", patch, 0.6, 0.7)), coat_c,
                       t.scale_colour(BARE_NICK, t.math("MULTIPLY_ADD", grain, 0.1, 0.95)))
    nick_c = t.scale_colour(BARE_NICK, t.math("MULTIPLY_ADD", fine, 0.2, 0.9))
    base = t.mix_rgb(lifted, coat_c, lift_c)
    base = t.mix_rgb(satin, base, satin_c)
    base = t.mix_rgb(polish, base, polish_c)
    base = t.mix_rgb(nick, base, nick_c)
    base = t.scale_socket(base, t.math("ADD", t.math("SUBTRACT", 1.0, scratch_down), scratch_up))
    base = t.mix_rgb(pits, base, t.scale_socket(base, PIT_FACTOR))
    base = t.mix_rgb(rust, base, RUST)
    t.link(base, bsdf.inputs["Base Color"])

    # --- roughness
    # Dirt is rougher than the clean coat: in the hero the plate mirrors the key strip, so a
    # rougher smear spreads that highlight and reads a touch darker.
    coat_r = t.math("MULTIPLY_ADD", t.math("SUBTRACT", grain, 0.5), 0.02,
                    t.math("MULTIPLY_ADD", cavity, CAVITY_ROUGH, COAT_ROUGHNESS))
    coat_r = t.math("MULTIPLY_ADD", smear, SMEAR_ROUGH, coat_r)
    coat_r = t.math("MULTIPLY_ADD", fleck, 0.05, coat_r)
    coat_r = t.math("MULTIPLY_ADD", t.math("MULTIPLY", side_wall, t.math("SUBTRACT", wall_noise, 0.5)), 0.10, coat_r)
    satin_r = t.math("MULTIPLY_ADD", t.math("SUBTRACT", mottle, 0.5), 0.08, SATIN_ROUGHNESS)
    satin_r = t.math("MULTIPLY_ADD", t.math("SUBTRACT", streak, 0.5), 0.02, satin_r)
    polish_r = t.math("MULTIPLY_ADD", t.math("SUBTRACT", streak, 0.5), 0.01, POLISH_ROUGHNESS)
    rough = t.mix_f(t.math("MAXIMUM", nick, t.math("MULTIPLY", lifted, 0.5)), coat_r, 0.33)
    rough = t.mix_f(satin, rough, satin_r)
    rough = t.mix_f(polish, rough, polish_r)
    rough = t.math("MULTIPLY_ADD", side_wall, WALL_ROUGHNESS_GAIN, rough)
    rough = t.math("MULTIPLY_ADD", t.math("ADD", s_light, l_light), -0.03, rough)
    rough = t.math("MULTIPLY_ADD", t.math("ADD", s_dark, l_dark), 0.04, rough)
    rough = t.math("MULTIPLY_ADD", pits, 0.08, rough)
    rough = t.mix_f(rust, rough, 0.75)
    t.link(t.math("MINIMUM", t.math("MAXIMUM", rough, 0.05), 1.0), bsdf.inputs["Roughness"])

    # --- metallic: 1.0 everywhere except the rust
    t.link(t.math("SUBTRACT", 1.0, rust), bsdf.inputs["Metallic"])

    # --- shape: the dish.  The plate dishes shallowly toward the hole and rolls off toward the notch
    # arcs (a real hand-finished plate is never dead flat there); the height is in metres, so the bump
    # tilts the normal by depth / reach (~1-2 deg) - what makes the soft halo round the hole in the hero
    # while the straight-down top view barely changes.
    dish_hole = t.math("MULTIPLY", t.math("POWER", t.range(hole, 0.0, DISH_HOLE[1], 1.0, 0.0), 2.0), -DISH_HOLE[0])
    dish_scallop = t.math("MULTIPLY", t.math("POWER", t.range(scallop, 0.0, DISH_SCALLOP[1], 1.0, 0.0), 2.0),
                          t.math("MULTIPLY", has_scallop, -DISH_SCALLOP[0]))
    dish = t.math("MINIMUM", dish_hole, dish_scallop)
    dish_bump = t.new("ShaderNodeBump")
    dish_bump.location = (1600, -600)
    dish_bump.inputs["Strength"].default_value = 1.0
    dish_bump.inputs["Distance"].default_value = 1.0
    t.link(dish, dish_bump.inputs["Height"])

    # --- micro relief: scratches and pits as faint grooves, the grain as a whisper
    height = t.math("MULTIPLY_ADD", t.math("MAXIMUM", t.math("MAXIMUM", s_light, s_dark), t.math("MAXIMUM", l_light, l_dark)),
                    -0.25, t.math("MULTIPLY_ADD", pits, -0.6, t.math("MULTIPLY", t.math("SUBTRACT", grain, 0.5), 0.10)))
    bump = t.new("ShaderNodeBump")
    bump.location = (1800, -600)
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.0002
    t.link(height, bump.inputs["Height"])
    t.link(dish_bump.outputs["Normal"], bump.inputs["Normal"])
    t.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


__all__ = ["ARRIS_BAND", "BAR_PROPS", "GROUND_ATTR", "WEAR_AXIS_PROP", "tag_bar", "BARE_CREST", "BARE_GRIND", "BARE_INNER", "BARE_NICK", "BARE_POLISH", "BARE_RIM", "CHAMFER_PROP", "COAT",
           "HALF_T_PROP", "HUB_PROP", "MATERIAL_NAME", "POINTS_PROP", "POLISH_W", "PROPS", "SATIN", "TIP_R_PROP",
           "TIP_WEAR", "WALL_TOP_PROP", "WEAR_FROM_PROP", "WEAR_TO_PROP", "build_material", "tag_common",
           "tag_object", "wear_range"]
