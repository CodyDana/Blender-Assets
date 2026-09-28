"""M_Shuriken_Master: the one material every form shares.

Knife-grind pass (style pass 2, 2026-09-18).  The first restyle passed every gate but did not
look like the reference the user brought ("a sharp shuriken with wear and tear"): measured
through the same rig, its wear was a wide chalky band torn 1-3 mm into the face, its grime a
free-floating cloudy mottle, its scratches few, long and loud and its pits visible dots.  The
reference keeps the bright bare steel ON the ground bevels, chips the face only in small nicks
where the bevel meets it, gathers soft dirt in the cavities and covers the face in many faint
micro-scratches.  This recipe (decision C) does exactly that, tuned by eye and by image_stats
against the reference rendered through the pack's own rig (ref_rig_scaled100_persp/top):

    coat        linear ~0.10 (stored ~0.34), faintly violet (R and B a touch over G, as the
                reference renders through the rig), metallic 1.0, roughness 0.34; a fine cast
                grain - no free-floating cloud mottle
    grind       100 % bare steel on every knife facet and the edge land (the crest): brightest
                at the crest (BARE_CREST, stored ~0.58), falling to BARE_GRIND (~0.46) at the plate
                line, so the bright line is the edge, as on the reference; faint wheel marks, oily
                smudges and small dark chips; roughness 0.33 (the 35 deg facets then catch the rig's
                top ring in the spec view and the overhead panel in the hero)
    nicks       narrow (0.15-0.6 mm) irregular chips into the face along the grind's plate line on
                ~22 % of its length: a threshold on GRIND_ATTR (the generator's signed distance from
                that line) whose depth a ~2.4 mm noise sets per spot - worn steel, not chalk
    scallops    the scallop chamfers and the hole's deburr chamfer only lightly brightened
                (SCALLOP_LIFT of the way from the coat to bare steel, patchy)
    tips        bare over the last TIP_WEAR of each point (past the apex the point is all grind)
    grime       CAVITY driven: the hole edge (HOLE_ATTR), the concave notch arcs (SCALLOP_ATTR) and
                the centre (radius, CENTRE_PROP), gently modulated; up to -50 % value and +0.14
                roughness (in the hero the plate mirrors the key strip, so rougher dirt reads darker
                - the reference's BC spread is small, its roughness rises in the dirt); on the faces
                only, the walls stay light.  Inside it: fine dirt flecks, irregular dried-dirt stains
                (0.5-3 mm) and a soft smudge, all sparse on the open face and dense in the cavity
    scratches   many fine (0.05-0.12 mm wide) short (2-8 mm) micro-scratches in every direction
                (8 families, two Voronoi cells each so none is cut at a cell border), low individual
                contrast (+14 %, a fifth of them darker); a handful of longer (12-26 mm) ones at
                +24 %; faint grooves in the normal
    pits        near-invisible: 0.04-0.09 mm, -15 %
    rust        exactly two tiny specks per piece, placed by the form (object custom properties)
    normal      flat plates; the scratches and pits as a faint bump

Everything is procedural in OBJECT space so the bake captures it on LOD0's UV0 and every LOD
agrees.  Form-dependent numbers are read per object: custom properties through Attribute
nodes of type OBJECT (``tag_common``) and four float point attributes the generator writes on
every LOD (``geometry.EDGE_ATTR`` / ``HOLE_ATTR`` / ``SCALLOP_ATTR`` / ``GRIND_ATTR``).  An
object without them gets no nicks and no cavity grime (a missing attribute reads 0).

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
BARE_CREST = (0.300, 0.305, 0.315)    # the edge land and the grind at the crest (stored ~0.58)
BARE_GRIND = (0.175, 0.178, 0.186)    # the grind toward its plate line (stored ~0.46): the bright line is the crest
BARE_NICK = (0.165, 0.168, 0.176)     # a chip into the face (stored ~0.45: worn steel, not chalk)
BARE_INNER = BARE_NICK                # (kept for importers of the old name)
BARE_RIM = BARE_CREST
SCALLOP_LIFT = 0.30                   # scallop / hole chamfers: this far from the coat toward bare steel
RUST = (0.13, 0.052, 0.022)           # warm rust, non-metal
COAT_ROUGHNESS = 0.34
BARE_ROUGHNESS = 0.33
WALL_ROUGHNESS_GAIN = 0.04
TIP_WEAR = 0.006                      # m: bare over the last 6 mm of every point
NICK_DEPTH = (0.00015, 0.0006)        # m: 0.15-0.6 mm into the face (decision C: 0.2-0.8 mm nominal chips)
NICK_SCALE = 420.0                    # 1/m: ~2.4 mm noise features along the grind line
NICK_THRESHOLD = 0.60                 # noise level above which a spot is chipped (~22 % of the line)
GRIME_DARKEN = 0.50                   # the coat's value in the deepest cavity grime (x 0.50)
GRIME_ROUGH = 0.14                    # roughness added in the deepest cavity grime
FLECK_ROUGH = 0.10                    # ... at a fleck's core
SMUDGE_ROUGH = 0.06                   # +-0.03 with the soft value smudge (darker = rougher)
GRIME_HOLE_REACH = 0.0055             # m from the hole edge
GRIME_SCALLOP_REACH = 0.0032          # m from the notch arcs
GRIME_CENTRE_WEIGHT = 0.70            # the soft darkening toward the centre (hub) at its strongest
FLECK_DARKEN = 0.32                   # fine dark dirt flecks: the coat x 0.68 at a fleck's core
FLECK_COVER = (0.58, 0.66)            # noise window of the fine flecks (lower = more flecks)
FLECK_OPEN = 0.40                     # fleck density on the open face, against 1.6 in the deepest grime
SMUDGE_GAIN = 0.07                    # +-7 % soft 2-4 mm value variation of the coat (not a cloud mottle)
STAIN_COVER = (0.56, 0.62)            # noise window of the dried dirt stains (lower = more stain)
STAIN_OPEN = 0.20                     # stain density on the open face, against 1.3 in the deepest grime
STAIN_DARKEN = 0.36                   # the coat x 0.64 at a stain's core
STAIN_ROUGH = 0.08
GRIND_STREAK = 0.10                   # +-5 % wheel marks across the grind
GRIND_CHIP_DARKEN = 0.42              # small dark chips / dirt on the bare grind (x 0.58)
SCRATCH_AA = 0.00002                  # m: stroke anti-aliasing ramp
# short micro-scratches: (cell scale 1/m, half-length m, half-width m, presence per cell)
SHORT_SCRATCH = {"scale": 190.0, "half_len": (0.0010, 0.0040), "half_w": (0.000025, 0.000060), "presence": 0.90,
                 "layers": 8, "gain": 0.14, "dark_fraction": 0.22, "dark_gain": 0.10}
LONG_SCRATCH = {"scale": 36.0, "half_len": (0.0060, 0.0130), "half_w": (0.000035, 0.000060), "presence": 0.35,
                "layers": 1, "gain": 0.24, "dark_fraction": 0.0, "dark_gain": 0.0}
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
RUST_PROPS = tuple(f"shuriken_rust{i}_{k}" for i in (1, 2) for k in ("x", "y", "z", "r"))
PROPS = (WEAR_FROM_PROP, WEAR_TO_PROP, POINTS_PROP, HUB_PROP, TIP_R_PROP, CHAMFER_PROP, SCALLOP_PROP, HOLE_W_PROP,
         CENTRE_PROP, LAND_PROP) + RUST_PROPS


def wear_range(o: Outline):
    """(from, to) radius in metres over which the points are bare."""
    return o.r_tip - TIP_WEAR, o.r_tip


def tag_common(obj, points: int, r_tip: float, r_hub: float, chamfer_w: float, scallop_w: float = 0.0,
               hole_w: float = 0.0, centre_r: float = 0.0, land: float = 0.00015, rust=()) -> None:
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
    specks = list(rust)[:2] + [(0.0, 0.0, 0.0, 0.0)] * (2 - len(list(rust)[:2]))
    for i, (x, y, face, radius) in enumerate(specks, start=1):
        obj[f"shuriken_rust{i}_x"] = float(x)
        obj[f"shuriken_rust{i}_y"] = float(y)
        obj[f"shuriken_rust{i}_z"] = float(face)
        obj[f"shuriken_rust{i}_r"] = float(radius)


def tag_object(obj, o: Outline) -> None:
    """A radial star's tags: two rust specks, one on the top face of arm 1's plate, one on the
    bottom face of the hub between arms 2 and 3."""
    n = o.n
    x1, y1 = 0.5 * (o.x_run + o.x_taper), 0.35 * (o.half_w - o.chamfer_w)
    a1 = 2.0 * math.pi / n
    r2 = 0.5 * (o.r_hole + o.hole_chamfer.width + o.r_hub - o.scallop.width)
    a2 = 2.0 * math.pi * 2 / n + math.pi / n
    rust = ((x1 * math.cos(a1) - y1 * math.sin(a1), x1 * math.sin(a1) + y1 * math.cos(a1), 1.0, 0.00030),
            (r2 * math.cos(a2), r2 * math.sin(a2), -1.0, 0.00022))
    tag_common(obj, o.n, o.r_tip, o.r_hub, o.chamfer_w, scallop_w=o.scallop.width, hole_w=o.hole_chamfer.width,
               centre_r=o.r_hub + 0.005, land=o.edge_land, rust=rust)


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
    makes ``dark_fraction`` of them darker instead of lighter.
    """
    vec = t.combine(x, y, t.math("MULTIPLY_ADD", z, 8.0, seed))
    light, dark = None, None
    for cell in t.voronoi_cells(vec, cfg["scale"]):
        local = t.vmath("SUBTRACT", vec, cell)
        lx, ly, _lz = t.separate(local)
        angle = t.math("MULTIPLY", t.white(cell, 1.0 + seed), math.pi)
        lo, hi = cfg["half_len"]
        half_len = t.math("MULTIPLY_ADD", t.white(cell, 2.0 + seed), hi - lo, lo)
        wlo, whi = cfg["half_w"]
        half_w = t.math("MULTIPLY_ADD", t.white(cell, 3.0 + seed), whi - wlo, wlo)
        strength = t.math("MULTIPLY_ADD", t.white(cell, 4.0 + seed), 0.6, 0.4)
        on = t.math("LESS_THAN", t.white(cell, 5.0 + seed), cfg["presence"])
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
    inside = t.range(dist, t.math("ADD", radius, 0.00004), t.math("SUBTRACT", radius, 0.00004))
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
    centre_r = t.attribute(CENTRE_PROP)
    land = t.attribute(LAND_PROP)
    wear_from = t.attribute(WEAR_FROM_PROP)
    tip_r = t.attribute(TIP_R_PROP)

    # --- surface classes.  The plate is exactly |N.z| = 1 (hard-edged flat faces), the walls 0,
    # every ground facet in between.  Which facet is which comes from the distance attributes:
    # the scallop chamfer lies within its width of the notch arcs, the hole deburr within its width
    # of the hole, everything else is knife grind.  The land is the wall on the outline within the
    # land's height of the mid-plane (the tall run-out walls at the root keep the coat).
    facet = t.math("MULTIPLY", t.range(nz, 0.02, 0.06), t.range(nz, 0.995, 0.975))
    wall = t.range(nz, 0.05, 0.01)
    plate = t.range(nz, 0.975, 0.995)
    near_scallop = t.range(scallop, t.math("ADD", scallop_w, 0.00015), t.math("ADD", scallop_w, 0.00004))
    near_scallop = t.math("MULTIPLY", near_scallop, t.math("GREATER_THAN", scallop_w, 0.0))
    near_hole = t.range(hole, t.math("ADD", hole_w, 0.00015), t.math("ADD", hole_w, 0.00004))
    cutter = t.math("MULTIPLY", t.math("SUBTRACT", 1.0, near_scallop), t.math("SUBTRACT", 1.0, near_hole))
    knife = t.math("MULTIPLY", facet, cutter)
    on_outline = t.range(edge, 0.00003, 0.000005)
    low = t.range(abs_z, t.math("ADD", t.math("MULTIPLY", land, 0.5), 0.00006),
                  t.math("ADD", t.math("MULTIPLY", land, 0.5), 0.00002))
    crest = t.math("MULTIPLY", t.math("MULTIPLY", wall, on_outline), t.math("MULTIPLY", low, cutter))
    lifted = t.math("MULTIPLY", facet, t.math("MAXIMUM", near_scallop, near_hole))

    # --- noises
    grain = t.range(t.noise(obj, 2600.0, 3.0, 0.6), 0.30, 0.70)                 # ~0.4 mm cast grain
    fine = t.range(t.noise(obj, 1800.0, 3.0, 0.55), 0.30, 0.70)                 # ~0.55 mm
    slow = t.range(t.noise(obj, 150.0, 3.0, 0.55), 0.28, 0.72)                  # ~6.7 mm grime modulation
    patch = t.range(t.noise(obj, 520.0, 2.0, 0.5), 0.35, 0.65)                  # ~1.9 mm patchiness
    nick_noise = t.noise(obj, NICK_SCALE, 3.0, 0.55)
    # wheel marks on the grind: fast along the radius, slow around it - fine lines across a facet
    streak = t.range(t.noise(t.combine(t.math("MULTIPLY", radius, 2600.0), t.math("MULTIPLY", x, 60.0),
                                       t.math("MULTIPLY", y, 60.0)), 1.0, 2.0, 0.55), 0.30, 0.70)
    smudge = t.range(t.noise(obj, 300.0, 4.0, 0.6), 0.60, 0.76)                 # oily smudges on the grind
    # fine dirt flecks in the coat (0.2-0.8 mm), sparse; a second, coarser and sparser family
    fleck = t.math("MAXIMUM", t.range(t.noise(obj, 3400.0, 4.0, 0.7), FLECK_COVER[0], FLECK_COVER[1]),
                   t.math("MULTIPLY", t.range(t.noise(obj, 1300.0, 4.0, 0.7), 0.68, 0.74), 0.5))
    coat_smudge = t.range(t.noise(obj, 330.0, 2.0, 0.5), 0.30, 0.70)            # ~3 mm soft value variation
    stain = t.range(t.noise(obj, 650.0, 6.0, 0.72), STAIN_COVER[0], STAIN_COVER[1])
    grind_chip = t.range(t.noise(obj, 1100.0, 3.0, 0.6), 0.64, 0.71)             # dark chips on the grind

    # --- nicks: chips into the face along the grind's plate line.  GRIND_ATTR is 0 on the line and
    # grows into the face; where the slow nick noise rises past its threshold the face is chipped
    # to a depth of 0.2-0.8 mm, the chip's outline broken by the fine noise.
    chip = t.range(nick_noise, NICK_THRESHOLD, NICK_THRESHOLD + 0.16)
    present = t.math("GREATER_THAN", nick_noise, NICK_THRESHOLD)
    depth = t.math("MULTIPLY", present, t.math("MULTIPLY_ADD", t.math("POWER", chip, 0.8),
                                               NICK_DEPTH[1] - NICK_DEPTH[0], NICK_DEPTH[0]))
    depth = t.math("MULTIPLY", depth, t.math("MULTIPLY_ADD", fine, 0.5, 0.75))
    nick = t.math("MULTIPLY", plate, t.range(grind, t.math("ADD", depth, 0.00002), t.math("SUBTRACT", depth, 0.00002)))
    nick = t.math("MULTIPLY", nick, t.math("GREATER_THAN", grind, -0.0005))

    # --- tips: bare over the last TIP_WEAR, the boundary broken into chips
    tip_ramp = t.range(radius, wear_from, t.math("SUBTRACT", tip_r, 0.0025))
    tip = t.range(t.math("MULTIPLY_ADD", t.math("SUBTRACT", patch, 0.5), 0.8, tip_ramp), 0.45, 0.55)

    bare = t.math("MAXIMUM", t.math("MAXIMUM", knife, crest), tip, clamp=True)

    # --- cavity grime: the hole edge, the notch arcs, the centre; soft, modulated, never free-floating
    hole_term = t.range(hole, 0.0, GRIME_HOLE_REACH, 1.0, 0.0, smooth=True)
    scallop_term = t.math("MULTIPLY", t.range(scallop, 0.0, GRIME_SCALLOP_REACH, 1.0, 0.0, smooth=True),
                          t.math("GREATER_THAN", scallop_w, 0.0))
    centre_term = t.math("MULTIPLY", t.range(radius, 0.0, centre_r, 1.0, 0.0, smooth=True), GRIME_CENTRE_WEIGHT)
    cavity = t.math("MAXIMUM", t.math("MAXIMUM", hole_term, scallop_term), centre_term)
    cavity = t.math("POWER", cavity, 1.2)
    grime = t.math("MULTIPLY", cavity, t.math("MULTIPLY", t.math("MULTIPLY_ADD", slow, 0.45, 0.55),
                                                 t.math("MULTIPLY_ADD", fine, 0.4, 0.8)), clamp=True)
    wall_grime = t.math("MULTIPLY", wall, t.math("SUBTRACT", 1.0, crest))
    # the flecks gather where the grime is (x1.8 in the deepest cavity), and stay off the bare steel
    # grime settles on the faces, not on the walls (the reference's scallop and hole walls read light)
    grime = t.math("MULTIPLY", grime, t.math("SUBTRACT", 1.0, wall))
    fleck = t.math("MULTIPLY", fleck, t.range(grime, 0.0, 0.6, FLECK_OPEN, 1.6))
    # dried dirt stains: irregular 0.5-3 mm patches (a detailed noise over a narrow window), sparse on
    # the open face and denser where the grime is - edges torn by the noise octaves, never a soft cloud
    stain = t.math("MULTIPLY", stain, t.range(grime, 0.0, 0.5, STAIN_OPEN, 1.3))
    stain = t.math("MINIMUM", stain, 1.0)

    # --- scratches (short micro-scratches everywhere, a handful of long ones), pits, rust
    s_light, s_dark = _scratches(t, x, y, z, SHORT_SCRATCH, 0.0)
    l_light, _l_dark = _scratches(t, x, y, z, LONG_SCRATCH, 211.0)
    on_grind = t.math("MULTIPLY_ADD", bare, -0.55, 1.0)                           # quieter on bare steel
    scratch_up = t.math("MULTIPLY", t.math("MAXIMUM", t.math("MULTIPLY", s_light, SHORT_SCRATCH["gain"]),
                                           t.math("MULTIPLY", l_light, LONG_SCRATCH["gain"])), on_grind)
    scratch_down = t.math("MULTIPLY", t.math("MULTIPLY", s_dark, SHORT_SCRATCH["dark_gain"]), on_grind)
    pits = _speck_layer(t, x, y, z, 11.0, 350.0, 0.10, 0.00004, 0.00009)
    rag = t.range(t.noise(obj, 2200.0, 3.0, 0.6), 0.30, 0.70)
    rust = t.math("MAXIMUM", _rust_speck(t, x, y, z, 1, rag), _rust_speck(t, x, y, z, 2, rag))
    rust = t.math("MULTIPLY", rust, plate)

    # --- base colour
    coat_k = t.math("MULTIPLY", t.math("MULTIPLY_ADD", grain, 0.10, 0.95),
                    t.math("SUBTRACT", 1.0, t.math("MULTIPLY", grime, GRIME_DARKEN)))
    # the soft smudge lives in the grime (a fifth of its amplitude on the open face): no free cloud
    smudge_amp = t.math("MULTIPLY_ADD", grime, 0.8, 0.2)
    smudge_dev = t.math("MULTIPLY", t.math("SUBTRACT", coat_smudge, 0.5), smudge_amp)
    coat_k = t.math("MULTIPLY", coat_k, t.math("MULTIPLY_ADD", smudge_dev, 2.0 * SMUDGE_GAIN, 1.0))
    coat_k = t.math("MULTIPLY", coat_k, t.math("MULTIPLY_ADD", t.math("MINIMUM", fleck, 1.0), -FLECK_DARKEN, 1.0))
    coat_k = t.math("MULTIPLY", coat_k, t.math("MULTIPLY_ADD", stain, -STAIN_DARKEN, 1.0))
    coat_k = t.math("MULTIPLY", coat_k, t.math("MULTIPLY_ADD", wall_grime, -0.04, 1.0))
    coat_c = t.scale_colour(COAT, coat_k)
    across = t.range(t.math("DIVIDE", edge, t.math("MAXIMUM", knife_w, 0.0001)), 0.0, 1.0)
    grind_base = t.mix_rgb(t.math("POWER", across, 0.6), BARE_CREST, BARE_GRIND)
    grind_k = t.math("MULTIPLY", t.math("MULTIPLY_ADD", streak, GRIND_STREAK, 1.0 - 0.5 * GRIND_STREAK),
                     t.math("MULTIPLY_ADD", grain, 0.08, 0.96))
    grind_k = t.math("MULTIPLY", grind_k, t.math("MULTIPLY_ADD", smudge, -0.22, 1.0))
    grind_k = t.math("MULTIPLY", grind_k, t.math("MULTIPLY_ADD", grind_chip, -GRIND_CHIP_DARKEN, 1.0))
    grind_c = t.scale_socket(grind_base, grind_k)
    lift_c = t.mix_rgb(t.math("MULTIPLY", SCALLOP_LIFT, t.math("MULTIPLY_ADD", patch, 0.6, 0.7)), coat_c,
                       t.scale_colour(BARE_GRIND, t.math("MULTIPLY_ADD", grain, 0.1, 0.95)))
    nick_c = t.scale_colour(BARE_NICK, t.math("MULTIPLY_ADD", fine, 0.2, 0.9))
    base = t.mix_rgb(lifted, coat_c, lift_c)
    base = t.mix_rgb(bare, base, grind_c)
    base = t.mix_rgb(nick, base, nick_c)
    base = t.scale_socket(base, t.math("ADD", t.math("SUBTRACT", 1.0, scratch_down), scratch_up))
    base = t.mix_rgb(pits, base, t.scale_socket(base, PIT_FACTOR))
    base = t.mix_rgb(rust, base, RUST)
    t.link(base, bsdf.inputs["Base Color"])

    # --- roughness
    # Dirt is rougher than the clean coat: in the hero the plate mirrors the key strip, so a
    # rougher spot spreads that highlight and reads darker - which is how the reference's
    # grime shows (its BC spread is small, its roughness rises to ~0.39 in the dirt).
    coat_r = t.math("MULTIPLY_ADD", t.math("SUBTRACT", grain, 0.5), 0.04,
                    t.math("MULTIPLY_ADD", grime, GRIME_ROUGH, COAT_ROUGHNESS))
    coat_r = t.math("MULTIPLY_ADD", t.math("MINIMUM", fleck, 1.0), FLECK_ROUGH, coat_r)
    coat_r = t.math("MULTIPLY_ADD", stain, STAIN_ROUGH, coat_r)
    coat_r = t.math("MULTIPLY_ADD", smudge_dev, -SMUDGE_ROUGH, coat_r)
    bare_r = t.math("MULTIPLY_ADD", t.math("SUBTRACT", streak, 0.5), 0.05,
                    t.math("MULTIPLY_ADD", smudge, 0.05, BARE_ROUGHNESS))
    rough = t.mix_f(t.math("MAXIMUM", bare, t.math("MAXIMUM", nick, t.math("MULTIPLY", lifted, 0.5))), coat_r, bare_r)
    rough = t.math("MULTIPLY_ADD", wall_grime, WALL_ROUGHNESS_GAIN, rough)
    rough = t.math("MULTIPLY_ADD", t.math("ADD", t.math("MULTIPLY", s_light, 1.0), l_light), -0.035, rough)
    rough = t.math("MULTIPLY_ADD", pits, 0.08, rough)
    rough = t.mix_f(rust, rough, 0.75)
    t.link(t.math("MINIMUM", t.math("MAXIMUM", rough, 0.05), 1.0), bsdf.inputs["Roughness"])

    # --- metallic: 1.0 everywhere except the rust
    t.link(t.math("SUBTRACT", 1.0, rust), bsdf.inputs["Metallic"])

    # --- micro relief: flat plates; scratches and pits as faint grooves, the grain as a whisper
    height = t.math("MULTIPLY_ADD", t.math("MAXIMUM", t.math("MAXIMUM", s_light, s_dark), l_light), -0.25,
                    t.math("MULTIPLY_ADD", pits, -0.6, t.math("MULTIPLY", t.math("SUBTRACT", grain, 0.5), 0.12)))
    bump = t.new("ShaderNodeBump")
    bump.location = (1800, -600)
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.0002
    t.link(height, bump.inputs["Height"])
    t.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


__all__ = ["BARE_CREST", "BARE_GRIND", "BARE_INNER", "BARE_NICK", "BARE_RIM", "CHAMFER_PROP", "COAT", "HUB_PROP",
           "MATERIAL_NAME", "POINTS_PROP", "PROPS", "TIP_R_PROP", "TIP_WEAR", "WEAR_FROM_PROP", "WEAR_TO_PROP",
           "build_material", "tag_common", "tag_object", "wear_range"]
