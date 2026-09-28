"""M_Shuriken_Master: the one material every form shares.

Blackened steel with bare metal worn through at the points.  Metallic 0.9 on the
coating is a deliberate exception to the project's 0.95-1.0 rule (ASSET_GUIDELINES.md
section 3): study 4 calls for 0.85-0.95 on a *coated* surface, and this finish is a
blackened oxide coating, not bare ground steel.  The worn areas go to 1.0, which is
the same section's value for worn steel.

No texture is baked (out of scope for the first pieces), so the wear is driven by
radius and by the ground-facet normal: study 2.2 records "some loss of the black
coating on the points" as the wear to reproduce and study 4 asks for it "driven hard
on point tips and ground bevels".  None of this reaches the FBX, which carries only
the Principled scalars, so the shipped asset is unaffected.

One material for every form: the only form-dependent numbers (where the tip wear
starts and ends, in metres of radius; the point count; the hub radius) are read per
object from custom properties through Attribute nodes of type OBJECT.  ``tag_object``
writes them on every LOD.  An object without the tags simply gets no tip wear (Map Range
returns its To Min for a zero range).

Maintenance pass (visual review): the tip wear was one smooth radial ramp, identical on
every point - an airbrushed gradient stamped n times.  It is now broken up by chip noise
(an irregular coating edge with islands of black left on bare steel), varied per point
(the arm index, from the angle and ``shuriken_points``, hashed through White Noise into a
start offset and a strength), and biased toward the chisel edge.  The ground bevels were
near-white strokes on every point; their bare-steel gain drops and varies with noise.
The radial grind no longer dominates a large hub: its contrast fades inside
``shuriken_hub_r``, and three families of straight, non-radial scratches cross the whole
plate so it reads as used, scratched plate (study 3) rather than a spun disc.
This material is the bake SOURCE: shuriken_lib.bake writes it into T_Shuriken_<Form>_BC /
_ORM / _N on LOD0's UV0, and the gallery beauty shots render from those textures only.
"""
from __future__ import annotations

import math

import bpy

from .spec import Outline

MATERIAL_NAME = "M_Shuriken_Master"
BLACKENED = (0.035, 0.034, 0.033)     # study 4: very dark grey, not pure black, neutral to warm
BARE_STEEL = (0.52, 0.525, 0.53)      # study 3: bright bare metal at the points
WEAR_FROM_PROP = "shuriken_wear_from"
WEAR_TO_PROP = "shuriken_wear_to"
POINTS_PROP = "shuriken_points"
HUB_PROP = "shuriken_hub_r"
EDGE_WEAR_GAIN = 0.45                 # ground-bevel bare steel (was 0.80: near-white outline strokes)
TIP_WEAR_GAIN = 0.90
# Study 2.2 records "some loss of the black coating on the points", not a polished
# point: the coating survives most of the taper and goes over the last part of it.
WEAR_START_OF_TAPER = 0.45


def wear_range(o: Outline):
    """(from, to) radius in metres over which the tip wear ramps in."""
    return o.x_taper + WEAR_START_OF_TAPER * o.taper_len, o.r_tip


def tag_object(obj, o: Outline) -> None:
    start, end = wear_range(o)
    obj[WEAR_FROM_PROP] = float(start)
    obj[WEAR_TO_PROP] = float(end)
    obj[POINTS_PROP] = float(o.n)
    obj[HUB_PROP] = float(o.r_hub)


def build_material():
    """Create (or rebuild in place) M_Shuriken_Master and return it."""
    mat = bpy.data.materials.get(MATERIAL_NAME) or bpy.data.materials.new(MATERIAL_NAME)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    new = tree.nodes.new
    link = tree.links.new

    out = new("ShaderNodeOutputMaterial")
    out.location = (1500, 0)
    bsdf = new("ShaderNodeBsdfPrincipled")
    bsdf.location = (1200, 0)
    # Kept as defaults as well as linked: the FBX exporter reads default_value.
    bsdf.inputs["Base Color"].default_value = (*BLACKENED, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.9
    bsdf.inputs["Roughness"].default_value = 0.55
    link(bsdf.outputs["BSDF"], out.inputs["Surface"])

    coord = new("ShaderNodeTexCoord")
    coord.location = (-1400, 0)
    sep = new("ShaderNodeSeparateXYZ")
    sep.location = (-1200, 0)
    link(coord.outputs["Object"], sep.inputs["Vector"])

    flat = new("ShaderNodeCombineXYZ")           # object position with z removed
    flat.location = (-1000, -120)
    link(sep.outputs["X"], flat.inputs["X"])
    link(sep.outputs["Y"], flat.inputs["Y"])
    radius = new("ShaderNodeVectorMath")
    radius.operation = "LENGTH"
    radius.location = (-820, -120)
    link(flat.outputs["Vector"], radius.inputs[0])

    # --- wear masks -------------------------------------------------------------
    tip_mask = new("ShaderNodeMapRange")
    tip_mask.interpolation_type = "SMOOTHSTEP"
    tip_mask.location = (-620, -40)
    link(radius.outputs["Value"], tip_mask.inputs["Value"])
    # Per-form radii, read from the object (see module docstring).
    for prop, socket, y in ((WEAR_FROM_PROP, "From Min", 160), (WEAR_TO_PROP, "From Max", 60)):
        attr = new("ShaderNodeAttribute")
        attr.attribute_type = "OBJECT"
        attr.attribute_name = prop
        attr.location = (-820, y)
        link(attr.outputs["Fac"], tip_mask.inputs[socket])

    # The ground facet is the only surface whose normal is neither the plate's +Z nor
    # the rim wall's horizontal, so a band on |N.z| isolates it exactly.  Pointiness
    # cannot: it is a vertex attribute, so on a 4-column arm it smears the wear across
    # a quarter of the arm width and the plate stops reading as flat.
    geom = new("ShaderNodeNewGeometry")
    geom.location = (-1400, -400)
    normal_sep = new("ShaderNodeSeparateXYZ")
    normal_sep.location = (-1200, -400)
    link(geom.outputs["Normal"], normal_sep.inputs["Vector"])
    normal_abs = new("ShaderNodeMath")
    normal_abs.operation = "ABSOLUTE"
    normal_abs.location = (-1000, -400)
    link(normal_sep.outputs["Z"], normal_abs.inputs[0])
    edge_mask = new("ShaderNodeValToRGB")
    edge_mask.location = (-820, -420)
    stops = edge_mask.color_ramp.elements
    stops[0].position = 0.02
    stops[0].color = (0.0, 0.0, 0.0, 1.0)
    stops[1].position = 0.12
    stops[1].color = (1.0, 1.0, 1.0, 1.0)
    hold = edge_mask.color_ramp.elements.new(0.97)
    hold.color = (1.0, 1.0, 1.0, 1.0)
    fall = edge_mask.color_ramp.elements.new(0.995)
    fall.color = (0.0, 0.0, 0.0, 1.0)
    link(normal_abs.outputs["Value"], edge_mask.inputs["Fac"])

    def math_node(operation, a=None, b=None, x=0, y=0, value_b=None, value_a=None, clamp=False):
        node = new("ShaderNodeMath")
        node.operation = operation
        node.use_clamp = clamp
        node.location = (x, y)
        if a is not None:
            link(a, node.inputs[0])
        elif value_a is not None:
            node.inputs[0].default_value = value_a
        if b is not None:
            link(b, node.inputs[1])
        elif value_b is not None:
            node.inputs[1].default_value = value_b
        return node.outputs["Value"]

    # Per-point variation: arm index k = round(angle / (2 pi / n)) mod n, hashed.
    points_attr = new("ShaderNodeAttribute")
    points_attr.attribute_type = "OBJECT"
    points_attr.attribute_name = POINTS_PROP
    points_attr.location = (-1400, 360)
    angle = math_node("ARCTAN2", sep.outputs["Y"], sep.outputs["X"], -1200, 300)
    per_turn = math_node("DIVIDE", angle, None, -1000, 300, value_b=2.0 * 3.141592653589793)
    turns = math_node("MULTIPLY", per_turn, points_attr.outputs["Fac"], -820, 300)
    arm = math_node("ROUND", turns, None, -640, 300)
    arm_hash = new("ShaderNodeTexWhiteNoise")
    arm_hash.noise_dimensions = "1D"
    arm_hash.location = (-460, 300)
    link(math_node("ADD", arm, None, -560, 380, value_b=17.0), arm_hash.inputs["W"])
    # Chip noise: irregular coating edge, sampled in object space so every LOD agrees.
    chips = new("ShaderNodeTexNoise")
    chips.location = (-820, 180)
    chips.inputs["Scale"].default_value = 520.0
    chips.inputs["Detail"].default_value = 6.0
    chips.inputs["Roughness"].default_value = 0.62
    link(coord.outputs["Object"], chips.inputs["Vector"])
    # ramp + per-arm offset (+-0.18 of the ramp) + chip breakup, then a steep threshold
    offset = math_node("MULTIPLY_ADD", arm_hash.outputs["Value"], None, -300, 300, value_b=0.36)
    offset.node.inputs[2].default_value = -0.18
    shifted = math_node("ADD", tip_mask.outputs["Result"], offset, -300, 120)
    chip_term = math_node("MULTIPLY_ADD", chips.outputs["Fac"], None, -500, 120, value_b=0.9)
    chip_term.node.inputs[2].default_value = -0.45
    # chips only inside the transition (window 4 r (1 - r)), so the plate never gets spots
    one_minus = math_node("SUBTRACT", None, tip_mask.outputs["Result"], -500, 40, value_a=1.0)
    window = math_node("MULTIPLY", tip_mask.outputs["Result"], one_minus, -400, 40)
    window4 = math_node("MULTIPLY", window, None, -300, 40, value_b=4.0)
    chip_windowed = math_node("MULTIPLY", chip_term, window4, -200, 60)
    broken = math_node("ADD", shifted, chip_windowed, -120, 120)
    tip_threshold = new("ShaderNodeMapRange")
    tip_threshold.location = (60, 120)
    tip_threshold.clamp = True
    tip_threshold.inputs["From Min"].default_value = 0.30
    tip_threshold.inputs["From Max"].default_value = 0.62
    link(broken, tip_threshold.inputs["Value"])
    arm_strength = math_node("MULTIPLY_ADD", arm_hash.outputs["Value"], None, -120, 300, value_b=0.2)
    arm_strength.node.inputs[2].default_value = TIP_WEAR_GAIN - 0.1
    tip_gain = math_node("MULTIPLY", tip_threshold.outputs["Result"], arm_strength, 240, 120)
    # Ground bevels: bare steel, but not a uniform white stroke - noise-modulated gain.
    edge_noise = new("ShaderNodeMapRange")
    edge_noise.location = (-420, -520)
    edge_noise.inputs["From Min"].default_value = 0.30
    edge_noise.inputs["From Max"].default_value = 0.70
    edge_noise.inputs["To Min"].default_value = EDGE_WEAR_GAIN - 0.25
    edge_noise.inputs["To Max"].default_value = EDGE_WEAR_GAIN + 0.25
    link(chips.outputs["Fac"], edge_noise.inputs["Value"])
    edge_gain = math_node("MULTIPLY", edge_mask.outputs["Color"], edge_noise.outputs["Result"], -220, -400)
    wear_node = new("ShaderNodeMath")
    wear_node.operation = "MAXIMUM"
    wear_node.use_clamp = True
    wear_node.location = (420, -220)
    link(tip_gain, wear_node.inputs[0])
    link(edge_gain, wear_node.inputs[1])
    wear = wear_node

    # --- directional grind ------------------------------------------------------
    # Marks run radially, i.e. along each arm, with no seam: the noise is sampled on
    # a circle (the normalised in-plane direction) so it is periodic in the angle.
    unit = new("ShaderNodeVectorMath")
    unit.operation = "NORMALIZE"
    unit.location = (-1000, -600)
    link(flat.outputs["Vector"], unit.inputs[0])
    unit_sep = new("ShaderNodeSeparateXYZ")
    unit_sep.location = (-820, -600)
    link(unit.outputs["Vector"], unit_sep.inputs["Vector"])

    def scaled(node_in, factor, x, y):
        node = new("ShaderNodeMath")
        node.operation = "MULTIPLY"
        node.location = (x, y)
        node.inputs[1].default_value = factor
        link(node_in, node.inputs[0])
        return node.outputs["Value"]

    grind_vec = new("ShaderNodeCombineXYZ")
    grind_vec.location = (-420, -620)
    link(scaled(unit_sep.outputs["X"], 90.0, -620, -560), grind_vec.inputs["X"])
    link(scaled(unit_sep.outputs["Y"], 90.0, -620, -660), grind_vec.inputs["Y"])
    link(scaled(radius.outputs["Value"], 150.0, -620, -760), grind_vec.inputs["Z"])
    grind = new("ShaderNodeTexNoise")
    grind.noise_dimensions = "4D"
    grind.location = (-220, -620)
    grind.inputs["Scale"].default_value = 1.0
    grind.inputs["Detail"].default_value = 3.0
    grind.inputs["Roughness"].default_value = 0.55
    link(grind_vec.outputs["Vector"], grind.inputs["Vector"])
    link(scaled(sep.outputs["Z"], 320.0, -420, -820), grind.inputs["W"])

    # Hub mask: 0 well inside the hub, 1 on the arms - the radial grind fades on the hub.
    hub_attr = new("ShaderNodeAttribute")
    hub_attr.attribute_type = "OBJECT"
    hub_attr.attribute_name = HUB_PROP
    hub_attr.location = (-820, -980)
    hub_lo = math_node("MULTIPLY", hub_attr.outputs["Fac"], None, -620, -980, value_b=0.75)
    hub_hi = math_node("MULTIPLY", hub_attr.outputs["Fac"], None, -620, -1040, value_b=1.15)
    hub_mask = new("ShaderNodeMapRange")
    hub_mask.interpolation_type = "SMOOTHSTEP"
    hub_mask.location = (-420, -980)
    hub_mask.inputs["To Min"].default_value = 0.22
    hub_mask.inputs["To Max"].default_value = 1.0
    link(radius.outputs["Value"], hub_mask.inputs["Value"])
    link(hub_lo, hub_mask.inputs["From Min"])
    link(hub_hi, hub_mask.inputs["From Max"])

    # Straight scratches in three fixed directions (object space, not radial): long thin
    # noise streaks, thresholded so only the sparse tops survive.
    scratch_max = None
    for index, (degrees, seed) in enumerate(((17.0, 3.0), (71.0, 11.0), (128.0, 29.0))):
        theta = math.radians(degrees)
        c, s_ = math.cos(theta), math.sin(theta)
        along = math_node("ADD", math_node("MULTIPLY", sep.outputs["X"], None, -1000, -1200 - 160 * index, value_b=c),
                          math_node("MULTIPLY", sep.outputs["Y"], None, -1000, -1260 - 160 * index, value_b=s_),
                          -820, -1200 - 160 * index)
        across = math_node("SUBTRACT", math_node("MULTIPLY", sep.outputs["Y"], None, -1000, -1320 - 160 * index,
                                                 value_b=c),
                           math_node("MULTIPLY", sep.outputs["X"], None, -1000, -1380 - 160 * index, value_b=s_),
                           -820, -1260 - 160 * index)
        vec = new("ShaderNodeCombineXYZ")
        vec.location = (-640, -1230 - 160 * index)
        link(math_node("MULTIPLY", along, None, -700, -1180 - 160 * index, value_b=60.0), vec.inputs["X"])
        link(math_node("MULTIPLY", across, None, -700, -1240 - 160 * index, value_b=3400.0), vec.inputs["Y"])
        vec.inputs["Z"].default_value = seed
        streak = new("ShaderNodeTexNoise")
        streak.location = (-460, -1230 - 160 * index)
        streak.inputs["Scale"].default_value = 1.0
        streak.inputs["Detail"].default_value = 1.0
        streak.inputs["Roughness"].default_value = 0.4
        link(vec.outputs["Vector"], streak.inputs["Vector"])
        mask = new("ShaderNodeMapRange")
        mask.location = (-280, -1230 - 160 * index)
        mask.inputs["From Min"].default_value = 0.69
        mask.inputs["From Max"].default_value = 0.76
        link(streak.outputs["Fac"], mask.inputs["Value"])
        scratch_max = mask.outputs["Result"] if scratch_max is None else math_node(
            "MAXIMUM", scratch_max, mask.outputs["Result"], -120, -1230 - 160 * index)
    scratches = math_node("MULTIPLY", scratch_max, None, 60, -1300, value_b=0.6)

    forge = new("ShaderNodeTexNoise")          # coarse hammer / forge texture underneath
    forge.location = (-220, -900)
    forge.inputs["Scale"].default_value = 110.0
    forge.inputs["Detail"].default_value = 2.0
    forge.inputs["Roughness"].default_value = 0.5
    link(coord.outputs["Object"], forge.inputs["Vector"])

    # --- roughness --------------------------------------------------------------
    # grind contrast scaled by the hub mask: 0.5 +- (0.5 * hub_mask) around the mean
    grind_centred = math_node("SUBTRACT", grind.outputs["Fac"], None, -120, -700, value_b=0.5)
    wall_fade = math_node("MULTIPLY_ADD", normal_abs.outputs["Value"], None, -120, -780, value_b=0.65)
    wall_fade.node.inputs[2].default_value = 0.35
    grind_amount = math_node("MULTIPLY", hub_mask.outputs["Result"], wall_fade, -40, -760)
    grind_faded = math_node("MULTIPLY_ADD", grind_centred, grind_amount, 20, -700)
    grind_faded.node.inputs[2].default_value = 0.5
    grind_rough = new("ShaderNodeMapRange")
    grind_rough.location = (20, -620)
    grind_rough.inputs["From Min"].default_value = 0.30
    grind_rough.inputs["From Max"].default_value = 0.70
    grind_rough.inputs["To Min"].default_value = 0.51
    grind_rough.inputs["To Max"].default_value = 0.60
    link(grind_faded, grind_rough.inputs["Value"])
    forge_rough = new("ShaderNodeMapRange")
    forge_rough.location = (20, -900)
    forge_rough.inputs["From Min"].default_value = 0.35
    forge_rough.inputs["From Max"].default_value = 0.65
    forge_rough.inputs["To Min"].default_value = -0.035
    forge_rough.inputs["To Max"].default_value = 0.035
    link(forge.outputs["Fac"], forge_rough.inputs["Value"])
    coat_rough_base = math_node("ADD", grind_rough.outputs["Result"], forge_rough.outputs["Result"], 240, -760)
    # a scratch cuts through the coating: a little glossier, a little brighter
    coat_rough_node = new("ShaderNodeMath")
    coat_rough_node.operation = "MULTIPLY_ADD"
    coat_rough_node.location = (400, -760)
    link(scratches, coat_rough_node.inputs[0])
    coat_rough_node.inputs[1].default_value = -0.10
    link(coat_rough_base, coat_rough_node.inputs[2])
    coat_rough = coat_rough_node
    rough_mix = new("ShaderNodeMix")
    rough_mix.data_type = "FLOAT"
    rough_mix.location = (700, -500)
    rough_mix.inputs["B"].default_value = 0.30       # ground steel, study 4: 0.25 to 0.4
    link(wear.outputs["Value"], rough_mix.inputs["Factor"])
    link(coat_rough.outputs["Value"], rough_mix.inputs["A"])
    link(rough_mix.outputs["Result"], bsdf.inputs["Roughness"])

    # --- base colour and metallic ----------------------------------------------
    colour_mix = new("ShaderNodeMix")
    colour_mix.data_type = "RGBA"
    colour_mix.location = (700, 160)
    colour_mix.inputs[6].default_value = (*BLACKENED, 1.0)
    colour_mix.inputs[7].default_value = (*BARE_STEEL, 1.0)
    # scratches expose a little steel through the coating (at most 12 %)
    colour_factor = math_node("MULTIPLY_ADD", scratches, None, 560, 160, value_b=0.06)
    link(wear.outputs["Value"], colour_factor.node.inputs[2])
    colour_clamp = math_node("MINIMUM", colour_factor, None, 620, 220, value_b=1.0)
    link(colour_clamp, colour_mix.inputs["Factor"])
    link(colour_mix.outputs[2], bsdf.inputs["Base Color"])

    metal_mix = new("ShaderNodeMapRange")
    metal_mix.location = (700, -160)
    metal_mix.inputs["To Min"].default_value = 0.90
    metal_mix.inputs["To Max"].default_value = 1.00
    link(wear.outputs["Value"], metal_mix.inputs["Value"])
    link(metal_mix.outputs["Result"], bsdf.inputs["Metallic"])

    # --- micro relief -----------------------------------------------------------
    height = new("ShaderNodeMix")
    height.data_type = "FLOAT"
    height.location = (460, -1000)
    height.inputs["Factor"].default_value = 0.35
    link(grind_faded, height.inputs["A"])
    link(forge.outputs["Fac"], height.inputs["B"])
    scratched = math_node("MULTIPLY_ADD", scratches, None, 640, -1060, value_b=-0.18)
    link(height.outputs["Result"], scratched.node.inputs[2])
    bump = new("ShaderNodeBump")
    bump.location = (940, -900)
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.00035
    link(scratched, bump.inputs["Height"])
    link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


__all__ = ["BARE_STEEL", "BLACKENED", "HUB_PROP", "MATERIAL_NAME", "POINTS_PROP", "WEAR_FROM_PROP", "WEAR_TO_PROP",
           "build_material", "tag_object", "wear_range"]
