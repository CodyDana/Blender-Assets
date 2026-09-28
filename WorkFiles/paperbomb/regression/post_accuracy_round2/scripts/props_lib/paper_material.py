#!/usr/bin/env python
"""props_lib.paper_material - M_PaperBomb, and the node graph the gallery renders through.

One material ships: ``M_PaperBomb``, an OPAQUE Principled BSDF fed by the four baked
maps.  It is the same graph the gallery renders, because the pack's rule is that a
gallery image shows what the maps carry and nothing else.

    T_PaperBomb_BC    sRGB        base colour - paper, ink, seals, wear
    T_PaperBomb_ORM   linear      R ambient occlusion, G roughness, B metallic (0)
    T_PaperBomb_N     linear      tangent-space normal, DIRECTX green
    T_PaperBomb_M     linear      R torn-edge fibre fringe, G scorch from the Fuse
                                  socket, B ink mask for recolouring

WHY THE SHIPPING MATERIAL IS OPAQUE
-----------------------------------
Study open question 3 asks whether the torn edge ships as geometry plus a masked fringe
or as a clean cut with the fringe painted in.  Answered here: the OUTLINE is geometry
(so the tear is in the silhouette at every LOD and in the shadow), and the fibre fringe
is shipped in ``_M`` red but not wired, so the master material stays opaque.  An opaque
material keeps early-Z, costs nothing on mobile and cannot shimmer; the fringe is
0.4 - 0.8 mm, which is a tenth of a pixel at the LOD1 switch and only reads in a
close-up.  A buyer who wants it switches the blend mode to Masked and drags ``_M`` red
into Opacity Mask - one connection, and the map is already in the package.  The report
says this in as many words so nobody has to guess.

AO IN THE BASE COLOUR
---------------------
Unreal's material graph is the buyer's business, but the GALLERY must not show a finish
the maps do not carry, so ``gallery_material`` multiplies ORM red into base colour the
way a standard UE master does.  ``ue_reference_material`` is the same graph; there is
only one, and that is the point.

GREEN CHANNEL
-------------
The ``_N`` map on disk is DirectX (green down), which is what Unreal wants and imports
with Flip Green OFF.  Blender's Normal Map node wants OpenGL, so the green channel is
inverted INSIDE this graph, once, with a comment on the node.  Nothing on disk changes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import bpy

DATA_COLORSPACE = "Non-Color"


def _image(path, name: str, data: bool) -> "bpy.types.Image":
    existing = bpy.data.images.get(name)
    if existing is not None:
        bpy.data.images.remove(existing)
    image = bpy.data.images.load(str(path), check_existing=False)
    image.name = name
    image.colorspace_settings.name = DATA_COLORSPACE if data else "sRGB"
    image.alpha_mode = "NONE"
    return image


def _tex(tree, image, location, interpolation: str = "Linear"):
    node = tree.nodes.new("ShaderNodeTexImage")
    node.image = image
    node.interpolation = interpolation
    node.location = location
    return node


def gallery_material(name: str, maps: Dict[str, str], uv_map: str = "UVMap",
                     specular: float = 0.5) -> "bpy.types.Material":
    """``M_PaperBomb`` from the four baked PNGs.  The ONLY material the card ever wears.

    ``maps`` is ``{"BC": path, "ORM": path, "N": path, "M": path}``.  ``M`` may be absent;
    it is loaded but not wired (see the module docstring).
    """
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    out = tree.nodes.new("ShaderNodeOutputMaterial")
    out.location = (700, 0)
    bsdf = tree.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (400, 0)
    tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    uv = tree.nodes.new("ShaderNodeUVMap")
    uv.uv_map = uv_map
    uv.location = (-900, 0)

    # The image DATABLOCK is named after the file, not after the material: the house QA
    # gate (pipeline.qa_check image_prefix) requires every texture datablock to start
    # with T_, and a buyer opening the .blend should see the shipped file names.
    bc = _tex(tree, _image(maps["BC"], Path(maps["BC"]).stem, data=False), (-620, 260))
    orm = _tex(tree, _image(maps["ORM"], Path(maps["ORM"]).stem, data=True), (-620, -40))
    nrm = _tex(tree, _image(maps["N"], Path(maps["N"]).stem, data=True), (-620, -360))
    for node in (bc, orm, nrm):
        tree.links.new(uv.outputs["UV"], node.inputs["Vector"])
    if maps.get("M"):
        # loaded so the .blend carries it and a buyer can see it; deliberately unwired
        mask = _tex(tree, _image(maps["M"], Path(maps["M"]).stem, data=True), (-620, -660))
        mask.label = "T_PaperBomb_M - fringe / scorch / ink mask, not wired (opaque master)"
        tree.links.new(uv.outputs["UV"], mask.inputs["Vector"])

    split = tree.nodes.new("ShaderNodeSeparateColor")
    split.location = (-340, -40)
    tree.links.new(orm.outputs["Color"], split.inputs["Color"])

    ao_mix = tree.nodes.new("ShaderNodeMix")
    ao_mix.data_type = "RGBA"
    ao_mix.blend_type = "MULTIPLY"
    ao_mix.inputs["Factor"].default_value = 1.0
    ao_mix.location = (0, 260)
    ao_mix.label = "AO into base colour, as a UE master does"
    tree.links.new(bc.outputs["Color"], ao_mix.inputs[6])
    tree.links.new(split.outputs["Red"], ao_mix.inputs[7])
    tree.links.new(ao_mix.outputs[2], bsdf.inputs["Base Color"])
    tree.links.new(split.outputs["Green"], bsdf.inputs["Roughness"])
    tree.links.new(split.outputs["Blue"], bsdf.inputs["Metallic"])

    # DirectX on disk -> OpenGL for Blender's Normal Map node.  One inversion, here.
    flip = tree.nodes.new("ShaderNodeSeparateColor")
    flip.location = (-340, -360)
    tree.links.new(nrm.outputs["Color"], flip.inputs["Color"])
    invert = tree.nodes.new("ShaderNodeMath")
    invert.operation = "SUBTRACT"
    invert.inputs[0].default_value = 1.0
    invert.location = (-160, -430)
    invert.label = "flip G: the map is DirectX, Blender wants OpenGL"
    tree.links.new(flip.outputs["Green"], invert.inputs[1])
    join = tree.nodes.new("ShaderNodeCombineColor")
    join.location = (20, -360)
    tree.links.new(flip.outputs["Red"], join.inputs["Red"])
    tree.links.new(invert.outputs["Value"], join.inputs["Green"])
    tree.links.new(flip.outputs["Blue"], join.inputs["Blue"])
    nmap = tree.nodes.new("ShaderNodeNormalMap")
    nmap.uv_map = uv_map
    nmap.location = (200, -360)
    tree.links.new(join.outputs["Color"], nmap.inputs["Color"])
    tree.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

    for key, value in (("IOR", 1.5), ("Specular IOR Level", specular)):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = value
    mat["ue_master"] = ("Opaque. BC sRGB; ORM linear (R AO, G roughness, B metallic); "
                        "N DirectX green, Flip Green OFF on import; M linear, not wired - "
                        "R is the torn-edge fibre fringe for a Masked variant.")
    return mat


def flat_emission(name: str, colour=(0.15, 0.162, 0.185), strength: float = 1.0):
    """A flat emissive material for the wireframe and LOD sheets."""
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*colour, 1.0)
    emit.inputs["Strength"].default_value = strength
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


__all__ = ["gallery_material", "flat_emission", "DATA_COLORSPACE"]
