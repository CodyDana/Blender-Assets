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
starts and ends, in metres of radius) are read per object from the custom properties
``shuriken_wear_from`` / ``shuriken_wear_to`` through Attribute nodes of type OBJECT.
``tag_object`` writes them; ``build_star_form`` tags every LOD.  An object without the
tags simply gets no tip wear (Map Range returns its To Min for a zero range).
"""
from __future__ import annotations

import bpy

from .spec import Outline

MATERIAL_NAME = "M_Shuriken_Master"
BLACKENED = (0.035, 0.034, 0.033)     # study 4: very dark grey, not pure black, neutral to warm
BARE_STEEL = (0.52, 0.525, 0.53)      # study 3: bright bare metal at the points
WEAR_FROM_PROP = "shuriken_wear_from"
WEAR_TO_PROP = "shuriken_wear_to"
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

    tip_gain = new("ShaderNodeMath")
    tip_gain.operation = "MULTIPLY"
    tip_gain.location = (-420, -40)
    tip_gain.inputs[1].default_value = 0.85
    link(tip_mask.outputs["Result"], tip_gain.inputs[0])
    edge_gain = new("ShaderNodeMath")
    edge_gain.operation = "MULTIPLY"
    edge_gain.location = (-420, -400)
    edge_gain.inputs[1].default_value = 0.80
    link(edge_mask.outputs["Color"], edge_gain.inputs[0])
    wear = new("ShaderNodeMath")
    wear.operation = "MAXIMUM"
    wear.location = (-220, -220)
    link(tip_gain.outputs["Value"], wear.inputs[0])
    link(edge_gain.outputs["Value"], wear.inputs[1])

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

    forge = new("ShaderNodeTexNoise")          # coarse hammer / forge texture underneath
    forge.location = (-220, -900)
    forge.inputs["Scale"].default_value = 110.0
    forge.inputs["Detail"].default_value = 2.0
    forge.inputs["Roughness"].default_value = 0.5
    link(coord.outputs["Object"], forge.inputs["Vector"])

    # --- roughness --------------------------------------------------------------
    grind_rough = new("ShaderNodeMapRange")
    grind_rough.location = (20, -620)
    grind_rough.inputs["From Min"].default_value = 0.30
    grind_rough.inputs["From Max"].default_value = 0.70
    grind_rough.inputs["To Min"].default_value = 0.51
    grind_rough.inputs["To Max"].default_value = 0.60
    link(grind.outputs["Fac"], grind_rough.inputs["Value"])
    forge_rough = new("ShaderNodeMapRange")
    forge_rough.location = (20, -900)
    forge_rough.inputs["From Min"].default_value = 0.35
    forge_rough.inputs["From Max"].default_value = 0.65
    forge_rough.inputs["To Min"].default_value = -0.035
    forge_rough.inputs["To Max"].default_value = 0.035
    link(forge.outputs["Fac"], forge_rough.inputs["Value"])
    coat_rough = new("ShaderNodeMath")
    coat_rough.operation = "ADD"
    coat_rough.location = (240, -760)
    link(grind_rough.outputs["Result"], coat_rough.inputs[0])
    link(forge_rough.outputs["Result"], coat_rough.inputs[1])
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
    link(wear.outputs["Value"], colour_mix.inputs["Factor"])
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
    link(grind.outputs["Fac"], height.inputs["A"])
    link(forge.outputs["Fac"], height.inputs["B"])
    bump = new("ShaderNodeBump")
    bump.location = (940, -900)
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.00035
    link(height.outputs["Result"], bump.inputs["Height"])
    link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


__all__ = ["BARE_STEEL", "BLACKENED", "MATERIAL_NAME", "WEAR_FROM_PROP", "WEAR_TO_PROP",
           "build_material", "tag_object", "wear_range"]
