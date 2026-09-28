"""The kunai's grip wrap (library 3.10): M_Kunai_Wrap, the two-slot bake, the preview material, T_Kunai_Lettering.

KUNAI_STUDY.md section 5, "Material setup, two slots": the steel is baked from M_Shuriken_Master into
T_Kunai_<Form>_BC / _ORM / _N (2048, UV tile u 0..1); the wrap is its own material, M_Kunai_Wrap, baked into
T_Kunai_Wrap_BC / _ORM / _N (1024, UV tile u 1..2), plus T_Kunai_Wrap_Natural_BC - the undyed option - and
T_Kunai_Lettering, a single-channel ink mask the wrap material samples through the lettering band's own UV rectangle,
shipped BLANK (no lettering is modelled, traced or textured; the user writes their own into it).

Library 3.10.1 (the plain kunai's review).  The tape's overlap is now GEOMETRY (kunai.author_wrap: a 9 mm-pitch helix
whose exposed edge stands one tape thickness proud, wound down onto the tang over the last 6 mm at both ends), because
a normal-map-only helix on a smooth 16-gon read as a moulded rubber / knurled grip: no overlap in the silhouette, a
sub-pixel sine weave that moired, and flat concentric end caps.  This material therefore carries only what geometry
cannot, and everything in it is aligned to the TAPE (kunai_spec.tape_phase, the same function the geometry uses):

M_Kunai_Wrap (the bake SOURCE; everything procedural in object space, so the bake carries it to every LOD's UVs):

    tape      the burnished crown along each turn's exposed edge (the hand rubs the ridges), the dirt line at the foot
              of the step, and loose fibres fraying along the edge - the relief itself is modelled
    weave     an irregular cotton weave, WEAVE[0] = 1.1 mm (11 texels at 10 px/mm), two thread families whose lines
              wander with a slow noise, plus a fine fibre fuzz (FUZZ): height into the normal map and value into the BC
    colour    dark dyed cotton, linear ~0.04 (DARK); the undyed option, linear ~0.40 (NATURAL, the "Dye" value node =
              1: T_Kunai_Wrap_Natural_BC); faded patches at 7 and 16 mm, lifted fibre flecks, hand grime in the middle
              of the grip (a little darker and less matte), the cut ends darker and fibrous
    roughness 0.90 (grime 0.78, burnished crowns 0.74); metallic 0
    band      the +Z lettering band is the same tape with BAND_CLEAN of the grime, its border feathered over
              BAND_FEATHER (4 mm along the grip, 2.5 mm of arc): no relief step and no rectangle in the BC, so ink
              applied through T_Kunai_Lettering follows the tape as it does on a real wrap

Object properties (``tag_wrap``, like the steel's): ``kunai_shift_m`` (the design frame's x in object space).  The wrap
is chiral (a helix): it is never mirrored, and its UV islands are unique.
"""
from __future__ import annotations

import contextlib
import math
import struct
import zlib
from pathlib import Path
from typing import Dict, Iterator

import bpy
import numpy as np

from pipeline.textures import DATA_COLORSPACE, image_pixels

from . import bake as B
from .kunai_spec import BAND_HALF_DEG, BAND_X0, BAND_X1, TAPE_RISE, WRAP_R, WRAP_X0, WRAP_X1
from .material import _Tree

WRAP_MATERIAL = "M_Kunai_Wrap"
SHIFT_PROP = "kunai_shift_m"             # object x of the design frame's origin is -shift: design x = object x + shift
DARK = (0.042, 0.039, 0.036)             # dark, faintly warm dyed cotton (linear): the study's "dark ~0.03"
NATURAL = (0.40, 0.355, 0.285)           # undyed cotton (linear): the study's "undyed ~0.40"
FIBRE = (0.150, 0.142, 0.126)            # lifted / broken fibres on the dark tape (linear)
FIBRE_NATURAL = (0.58, 0.545, 0.470)
ROUGHNESS = 0.90
GRIME_ROUGHNESS = 0.78
BURNISH_ROUGHNESS = 0.74                 # the ridges the hand rubs: flattened, dirt-polished cotton
TAPE_PITCH = 0.009                       # m: 10 mm tape wound at a 9 mm pitch (1 mm overlap) - kunai_spec.TAPE_PITCH
WEAVE = (0.00115, 0.000042)              # (period m, height m) of the cotton weave: 1.15 mm = 11 texels at 10 px/mm
WEAVE_ACROSS = 0.00094                   # ... and the other thread family's, so the two never make a square grid
WEAVE_WANDER = 2.6                       # rad: how far a thread line wanders (an irregular hand-woven tape)
SLUB = (330.0, 0.34)                     # (scale 1/m, amount) of thick / thin threads across the weave
FUZZ = (2800.0, 0.000026)                # (noise scale 1/m, height m) of the fibre fuzz on top of the weave
CREST = 0.075                            # phase width of the burnished crown along each tape edge
BAND_CLEAN = 0.60                        # the lettering band keeps this much of the grime, feathered over BAND_FEATHER
BAND_FEATHER = (0.004, 0.25)             # (m along x, rad around) - a soft border, never a panel edge
FRAY_REACH = 0.0016                      # m: loose fibres within this of each wrap end
FRAY_EDGE = 0.030                        # phase: loose fibres along each turn's exposed edge
STEEL_STEM = None                        # the steel maps take the pack's stem, T_Kunai_<Form>
WRAP_STEM = "T_Kunai_Wrap"
NATURAL_NAME = "T_Kunai_Wrap_Natural_BC"
LETTERING_NAME = "T_Kunai_Lettering"
INK = (0.62, 0.56, 0.44)                 # preview ink (linear): a worn light paint that reads on the dark tape
INK_ROUGHNESS = 0.62
SHEEN = 0.35                             # preview only: cloth sheen (Unreal: the Cloth shading model's fuzz)


def tag_wrap(obj, shift_mm: float) -> None:
    obj[SHIFT_PROP] = float(shift_mm * 0.001)


def _design_x(t: _Tree, x):
    return t.math("ADD", x, t.attribute(SHIFT_PROP))


def build_wrap_material():
    """Create (or rebuild in place) M_Kunai_Wrap and return it."""
    mat = bpy.data.materials.get(WRAP_MATERIAL) or bpy.data.materials.new(WRAP_MATERIAL)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    t = _Tree(tree)
    out = t.new("ShaderNodeOutputMaterial")
    out.location = (2400, 0)
    bsdf = t.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (2100, 0)
    # kept as defaults as well as linked: the FBX exporter reads default_value
    bsdf.inputs["Base Color"].default_value = (*DARK, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = ROUGHNESS
    t.link(bsdf.outputs["BSDF"], out.inputs["Surface"])
    dye = t.new("ShaderNodeValue")
    dye.name = "Dye"
    dye.label = "Dye (0 dark, 1 undyed)"
    dye.outputs[0].default_value = 0.0

    coord = t.new("ShaderNodeTexCoord")
    x_obj, y, z = t.separate(coord.outputs["Object"])
    xd = _design_x(t, x_obj)                                       # design x (m): 0 at the shoulder
    phi = t.math("ARCTAN2", y, z)                                  # 0 at +Z (the lettering face), toward +Y
    arc = t.math("MULTIPLY", phi, WRAP_R * 0.001)                  # m of arc on the 20 mm grip
    geom = t.new("ShaderNodeNewGeometry")
    nx, _ny, _nz = t.separate(geom.outputs["Normal"])
    cap = t.range(t.math("ABSOLUTE", nx), 0.6, 0.8)                # the two cut ends face +-X
    side = t.math("SUBTRACT", 1.0, cap)

    # --- the tape's helix.  The OVERLAP IS GEOMETRY from 3.10.1 (kunai.author_wrap, kunai_spec.tape_radius), so the
    # maps carry only what geometry cannot: the crown the hand burnishes, the dirt line at the foot of each step, the
    # loose fibres along the exposed edge, the weave and the fibre fuzz.  One phase function for both (kunai_spec).
    phase = t.math("ADD", t.math("DIVIDE", t.math("SUBTRACT", xd, WRAP_X0 * 0.001), TAPE_PITCH),
                   t.math("DIVIDE", phi, 2.0 * math.pi))
    f = t.math("FRACT", phase)                                     # 0 at a turn's exposed edge (the step's foot)
    crest = t.math("MULTIPLY", t.range(f, 0.0, 0.5 * CREST, smooth=True),
                   t.range(f, 2.0 * CREST, CREST, smooth=True))    # the ridge's crown, just past the step
    crevice = t.math("MAXIMUM", t.range(f, 0.965, 1.0, smooth=True), t.range(f, 0.02, 0.0, smooth=True))
    edge = t.math("MAXIMUM", crest, crevice)
    # --- an irregular hand-woven cotton weave: two thread families whose lines WANDER with a slow noise (3.10.1: the
    # 0.5 mm pure sine crosshatch of 3.10 was 5 texels per period - it moired in the map and read as machine knurling),
    # one across the tape and one along it, plus a fine fibre fuzz
    across = t.math("MULTIPLY", phase, TAPE_PITCH)                 # m across the tape, continuous over the turns
    weave_loc = t.combine(across, arc, 0.0)
    wander_a = t.math("MULTIPLY", t.math("SUBTRACT", t.noise(weave_loc, 220.0, 2.0, 0.5), 0.5), WEAVE_WANDER)
    wander_b = t.math("MULTIPLY", t.math("SUBTRACT", t.noise(weave_loc, 260.0, 2.0, 0.5, dims="4D", w=7.0), 0.5),
                      WEAVE_WANDER)
    thread_a = t.math("SINE", t.math("ADD", t.math("MULTIPLY", across, 2.0 * math.pi / WEAVE_ACROSS), wander_a))
    thread_b = t.math("SINE", t.math("ADD", t.math("MULTIPLY", arc, 2.0 * math.pi / WEAVE[0]), wander_b))
    # thick and thin threads (slubs): each family's amplitude is modulated by a slow noise, so no two lines are alike
    slub_a = t.math("MULTIPLY_ADD", t.math("SUBTRACT", t.noise(weave_loc, SLUB[0], 2.0, 0.6), 0.5), SLUB[1], 1.0)
    slub_b = t.math("MULTIPLY_ADD", t.math("SUBTRACT", t.noise(weave_loc, 0.8 * SLUB[0], 2.0, 0.6, dims="4D", w=3.0),
                                           0.5), SLUB[1], 1.0)
    weave = t.math("MULTIPLY", t.math("ADD", t.math("MULTIPLY", thread_a, slub_a),
                                      t.math("MULTIPLY", thread_b, slub_b)), 0.5)          # about -1 .. 1
    fuzz = t.math("SUBTRACT", t.noise(weave_loc, FUZZ[0], 4.0, 0.75), 0.5)
    # --- the lettering band: the same tape, a little cleaner, with a border feathered over millimetres (3.10.1: a hard
    # +-0.4 mm border baked a ridge and cut a clean rectangle out of the grime - the review's outlined panel)
    b = math.radians(BAND_HALF_DEG)
    fx, fp = BAND_FEATHER
    band = t.math("MULTIPLY", t.math("MULTIPLY",
                                     t.range(xd, (BAND_X0 * 0.001) - fx, (BAND_X0 * 0.001) + fx, smooth=True),
                                     t.range(xd, (BAND_X1 * 0.001) + fx, (BAND_X1 * 0.001) - fx, smooth=True)),
                  t.range(t.math("ABSOLUTE", phi), b + fp, b - fp, smooth=True))
    band = t.math("MULTIPLY", band, side)
    clean = t.math("MULTIPLY_ADD", band, BAND_CLEAN - 1.0, 1.0)
    height = t.math("MULTIPLY", t.math("ADD", t.math("MULTIPLY", weave, WEAVE[1]), t.math("MULTIPLY", fuzz, FUZZ[1])),
                    side)
    height = t.math("MULTIPLY_ADD", t.math("MULTIPLY", crest, side), 0.00006, height)    # the crown, softly rounded
    height = t.math("MULTIPLY_ADD", t.math("MULTIPLY", crevice, side), -0.00010, height)  # the dirt line at its foot
    # --- wear
    loc = t.combine(xd, arc, 0.0)
    fade = t.range(t.noise(loc, 150.0, 2.0, 0.5), 0.28, 0.72)                  # 7 mm dye / wear patches
    patch = t.range(t.noise(loc, 62.0, 2.0, 0.5), 0.3, 0.7)                    # 16 mm patches: whole turns worn lighter
    fibre = t.range(t.noise(loc, 2200.0, 3.0, 0.7), 0.68, 0.80)                # lifted fibre flecks
    mid = 0.5 * (WRAP_X0 + WRAP_X1) * 0.001
    grime = t.math("MULTIPLY", t.range(t.math("ABSOLUTE", t.math("SUBTRACT", xd, mid)), 0.040, 0.018, smooth=True),
                   t.range(t.noise(loc, 420.0, 3.0, 0.6), 0.35, 0.65))
    to_end = t.math("MINIMUM", t.math("SUBTRACT", WRAP_X1 * 0.001, xd), t.math("SUBTRACT", xd, WRAP_X0 * 0.001))
    # loose fibres: along every exposed tape edge - the crown of the step, where a wrap frays first - and at the cut ends
    fray_edge = t.math("MULTIPLY", t.math("MULTIPLY", t.range(f, TAPE_RISE - FRAY_EDGE, TAPE_RISE, smooth=True),
                                          t.range(f, TAPE_RISE + FRAY_EDGE, TAPE_RISE, smooth=True)),
                       t.range(t.noise(weave_loc, 3200.0, 3.0, 0.75), 0.52, 0.68))
    fray_end = t.math("MULTIPLY", t.range(to_end, FRAY_REACH, 0.0),
                      t.range(t.noise(loc, 5200.0, 3.0, 0.7), 0.50, 0.64))
    fray = t.math("MULTIPLY", t.math("MAXIMUM", fray_edge, fray_end), side)
    cap_fibre = t.math("MULTIPLY", cap, t.range(t.noise(t.combine(y, z, xd), 2600.0, 3.0, 0.7), 0.58, 0.74))
    height = t.math("MULTIPLY_ADD", t.math("MULTIPLY", fray, 1.0), 0.00004, height)

    def recipe(colour, grime_k, fleck):
        # value first: the crown is burnished lighter, the foot line darker, then the slow fade / patch variation
        k = t.math("MULTIPLY_ADD", t.math("MULTIPLY", crest, side), 0.30, 0.92)
        k = t.math("MULTIPLY", k, t.math("MULTIPLY_ADD", t.math("MULTIPLY", crevice, side), -0.50, 1.0))
        k = t.math("MULTIPLY", k, t.math("MULTIPLY_ADD", t.math("MULTIPLY", t.math("MULTIPLY", t.math(
            "SUBTRACT", fade, 0.5), clean), side), 0.55, 1.0))
        k = t.math("MULTIPLY", k, t.math("MULTIPLY_ADD", t.math("MULTIPLY", t.math("SUBTRACT", patch, 0.5), side),
                                         0.34, 1.0))
        k = t.math("MULTIPLY", k, t.math("MULTIPLY_ADD", t.math("MULTIPLY", t.math("MULTIPLY", grime, clean), side),
                                         -grime_k, 1.0))
        k = t.math("MULTIPLY", k, t.math("MULTIPLY_ADD", t.math("MULTIPLY", weave, side), 0.11, 1.0))
        k = t.math("MULTIPLY", k, t.math("MULTIPLY_ADD", cap, -0.28, 1.0))       # the cut ends sit in shadow
        c = t.scale_colour(colour, k)
        c = t.mix_rgb(t.math("MULTIPLY", t.math("MULTIPLY", fibre, t.math("MULTIPLY", clean, 0.45)), side), c, fleck)
        c = t.mix_rgb(t.math("MAXIMUM", fray, cap_fibre), c, fleck)
        return c

    dark_c = recipe(DARK, 0.22, FIBRE)
    natural_c = recipe(NATURAL, 0.40, FIBRE_NATURAL)
    base = t.mix_rgb(dye.outputs[0], dark_c, natural_c)
    t.link(base, bsdf.inputs["Base Color"])
    rough = t.math("MULTIPLY_ADD", t.math("SUBTRACT", fade, 0.5), 0.06, ROUGHNESS)
    rough = t.mix_f(t.math("MULTIPLY", grime, clean), rough, GRIME_ROUGHNESS)
    rough = t.mix_f(t.math("MULTIPLY", crest, side), rough, BURNISH_ROUGHNESS)   # rubbed ridges, a little less matte
    rough = t.math("MULTIPLY_ADD", t.math("MULTIPLY", crevice, side), 0.04, rough)
    rough = t.math("MULTIPLY_ADD", fray, 0.05, rough)
    t.link(t.math("MINIMUM", t.math("MAXIMUM", rough, 0.05), 1.0), bsdf.inputs["Roughness"])
    bump = t.new("ShaderNodeBump")
    bump.location = (1800, -600)
    bump.inputs["Strength"].default_value = 1.0
    bump.inputs["Distance"].default_value = 1.0
    t.link(height, bump.inputs["Height"])
    t.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def wrap_material():
    """M_Kunai_Wrap, built once per scene."""
    mat = bpy.data.materials.get(WRAP_MATERIAL)
    return mat if mat is not None else build_wrap_material()


# =========================================================================== the lettering mask


def write_gray_png(path: Path, pixels: np.ndarray) -> None:
    """An 8-bit single-channel (greyscale) PNG, rows top-down, no colour chunk: a data mask."""
    h, w = pixels.shape
    data = np.clip(np.rint(pixels * 255.0), 0, 255).astype(np.uint8)
    raw = b"".join(b"\x00" + data[r].tobytes() for r in range(h))

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(png)


def write_blank_lettering(path: Path, size=(1536, 256)) -> dict:
    write_gray_png(path, np.zeros((int(size[1]), int(size[0])), dtype=np.float32))
    return {"path": str(path), "size": [int(size[0]), int(size[1])], "content": "blank (all 0: no ink)",
            "format": "8-bit greyscale PNG, no colour chunk (a data mask)", "sha256": B._sha256(Path(path))}


# =========================================================================== bake


@contextlib.contextmanager
def _absorber(material) -> Iterator[None]:
    """Give ``material`` an active 8 x 8 image target, so the faces of the slot NOT being baked have somewhere to go
    (Cycles bakes every face of the object into its own material's active image)."""
    tree = material.node_tree
    image = bpy.data.images.new("__kunai_absorb", width=8, height=8, alpha=False, float_buffer=True, is_data=True)
    node = tree.nodes.new("ShaderNodeTexImage")
    node.name = "__kunai_absorb"
    node.image = image
    previous = tree.nodes.active
    for other in tree.nodes:
        other.select = False
    node.select = True
    tree.nodes.active = node
    try:
        yield
    finally:
        tree.nodes.remove(node)
        bpy.data.images.remove(image)
        if previous is not None:
            tree.nodes.active = previous


@contextlib.contextmanager
def _wrap_uv(obj) -> Iterator[str]:
    """A temporary UV layer, active for the bake, with the wrap tile (u 1..2) moved onto 0..1."""
    mesh = obj.data
    source = mesh.uv_layers[0]
    active, render = mesh.uv_layers.active_index, [i for i, uv in enumerate(mesh.uv_layers) if uv.active_render]
    layer = mesh.uv_layers.new(name="__kunai_wrap_bake")
    uv = np.empty(len(mesh.loops) * 2, dtype=np.float32)
    source.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    uv[:, 0] = uv[:, 0] - np.floor(uv[:, 0])
    layer.data.foreach_set("uv", uv.ravel())
    mesh.uv_layers.active = layer
    layer.active_render = True
    try:
        yield layer.name
    finally:
        mesh.uv_layers.remove(mesh.uv_layers["__kunai_wrap_bake"])
        mesh.uv_layers.active_index = active
        for i in render:
            mesh.uv_layers[i].active_render = True


def bake_kunai(geo, lod0, steel_material, out_dir, options) -> dict:
    """Both slots' maps + the natural BC + the blank lettering mask; returns the pack's textures dict (the steel maps
    under ``maps``, the wrap under ``wrap``)."""
    out_dir = Path(out_dir)
    wrap_mat = lod0.data.materials[1]
    steel_stem = B.texture_stem(lod0.name.replace("_LOD0", ""))
    with B._alone(lod0), _absorber(wrap_mat):
        steel = B._bake_form(lod0, steel_material, out_dir, int(geo.spec.steel_px), fill_unused=True, stem=steel_stem)
    with B._alone(lod0), _absorber(steel_material), _wrap_uv(lod0):
        wrap = B._bake_form(lod0, wrap_mat, out_dir, int(geo.spec.wrap_px), fill_unused=True, stem=WRAP_STEM)
        dye = wrap_mat.node_tree.nodes["Dye"]
        dye.outputs[0].default_value = 1.0
        try:
            natural_path = out_dir / f"{NATURAL_NAME}.png"
            image = B._new_image(NATURAL_NAME, int(geo.spec.wrap_px), data=False)
            try:
                B._bake_channel(lod0, wrap_mat, "Base Color", image)
                covered = B._coverage(lod0, wrap_mat, int(geo.spec.wrap_px))
                px = B._fill(image_pixels(image), covered)
                image.pixels.foreach_set(np.ascontiguousarray(px, dtype=np.float32).ravel())
                image.update()
                image.filepath_raw = str(natural_path)
                image.file_format = "PNG"
                image.save()
                natural_stats = B._stats(image_pixels(image))
            finally:
                bpy.data.images.remove(image)
        finally:
            dye.outputs[0].default_value = 0.0
    lettering = write_blank_lettering(out_dir / f"{LETTERING_NAME}.png", geo.spec.lettering_px)
    # a FROZEN kunai (a later build's --frozen-maps snapshot holds its maps): the wrap maps and the undyed BC are checked
    # against the snapshot within bake noise and its bytes ship, as pack.freeze_maps does for the steel maps (whose result
    # pack.bake_textures records); None when the snapshot has no kunai (this form's own build)
    frozen_dir = getattr(options, "frozen_maps", None)
    if frozen_dir:
        from .pack import freeze_maps
        wrap["frozen_maps"] = freeze_maps(wrap, Path(frozen_dir))
        natural = {"maps": {"BC": str(natural_path)}, "sha256": {"BC": B._sha256(natural_path)}}
        wrap["frozen_natural_bc"] = freeze_maps(natural, Path(frozen_dir))
    wrap["natural_bc"] = {"path": str(natural_path), "sha256": B._sha256(natural_path),
                          "stats_stored_srgb": natural_stats,
                          "what": "the undyed option: M_Kunai_Wrap with Dye = 1 (linear ~0.40 cotton), same ORM and N"}
    wrap["uv_tile"] = "u 1..2 (the bake read it through a temporary layer moved onto 0..1; Wrap addressing samples the "\
                      "same texels in the engine)"
    steel["wrap"] = wrap
    steel["lettering"] = lettering
    steel["lettering_uv"] = geo.layout.lettering()
    steel["slots"] = {"0": {"material": steel_material.name, "maps": steel["maps"]},
                      "1": {"material": wrap_mat.name, "maps": wrap["maps"], "natural_bc": str(natural_path),
                            "lettering_mask": lettering["path"]}}
    steel["unreal_import"]["Lettering"] = ("sRGB OFF, Compression Grayscale, Address Clamp, Power Of Two Mode Stretch "
                                           "to power of two AND Mip Gen Settings From Texture Group (1536 x 256 is not "
                                           "a power of two: Unreal imports it with MipGenSettings NoMipmaps, and the "
                                           "Stretch setting does not reset that - 3.10.1, measured twice in fresh "
                                           "processes; Scripts/shuriken/ue_import_textures.py sets and verifies both)")
    return steel


# =========================================================================== preview (render only)


def wrap_preview_material(textures: dict, lettering_path: str = None, ink=INK, name: str = "M_Preview_Baked_Wrap"):
    """A render-only material for slot 1 that reads the baked wrap maps and the lettering mask and nothing else:
    BC mixed toward ``ink`` by T_Kunai_Lettering sampled through the band's UV rectangle (remapped to 0..1, clamped,
    zero outside the band), ORM G -> roughness (ink: INK_ROUGHNESS), N (DirectX) -> normal.  With the shipped blank mask
    the ink term is exactly zero."""
    wrap = textures["wrap"]
    maps = wrap["maps"]
    rect = textures["lettering_uv"]["uv0_blender"]
    mat = B.preview_material(name, maps, uv_map=wrap["uv_map"])
    tree = mat.node_tree
    new, link = tree.nodes.new, tree.links.new
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    bc_link = bsdf.inputs["Base Color"].links[0]
    bc_out = bc_link.from_socket
    rough_link = bsdf.inputs["Roughness"].links[0]
    rough_out = rough_link.from_socket
    uv = new("ShaderNodeUVMap")
    uv.uv_map = wrap["uv_map"]
    mapping = new("ShaderNodeMapping")
    mapping.vector_type = "POINT"
    su, sv = 1.0 / (rect["u_max"] - rect["u_min"]), 1.0 / (rect["v_max"] - rect["v_min"])
    mapping.inputs["Location"].default_value = (-rect["u_min"] * su, -rect["v_min"] * sv, 0.0)
    mapping.inputs["Scale"].default_value = (su, sv, 1.0)
    link(uv.outputs["UV"], mapping.inputs["Vector"])
    tex = new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(lettering_path or textures["lettering"]["path"]), check_existing=False)
    tex.image.colorspace_settings.name = DATA_COLORSPACE
    tex.extension = "CLIP"
    tex.interpolation = "Linear"
    link(mapping.outputs["Vector"], tex.inputs["Vector"])
    sep = new("ShaderNodeSeparateXYZ")
    link(mapping.outputs["Vector"], sep.inputs["Vector"])

    def inside(socket):
        a = new("ShaderNodeMath")
        a.operation = "GREATER_THAN"
        a.inputs[1].default_value = 0.0
        link(socket, a.inputs[0])
        b = new("ShaderNodeMath")
        b.operation = "LESS_THAN"
        b.inputs[1].default_value = 1.0
        link(socket, b.inputs[0])
        m = new("ShaderNodeMath")
        m.operation = "MULTIPLY"
        link(a.outputs[0], m.inputs[0])
        link(b.outputs[0], m.inputs[1])
        return m.outputs[0]
    iu, iv = inside(sep.outputs["X"]), inside(sep.outputs["Y"])
    m1 = new("ShaderNodeMath")
    m1.operation = "MULTIPLY"
    link(iu, m1.inputs[0])
    link(iv, m1.inputs[1])
    ink_amount = new("ShaderNodeMath")
    ink_amount.operation = "MULTIPLY"
    link(m1.outputs[0], ink_amount.inputs[0])
    link(tex.outputs["Color"], ink_amount.inputs[1])
    mix = new("ShaderNodeMix")
    mix.data_type = "RGBA"
    link(ink_amount.outputs[0], mix.inputs["Factor"])
    link(bc_out, mix.inputs[6])
    mix.inputs[7].default_value = (*ink, 1.0)
    link(mix.outputs[2], bsdf.inputs["Base Color"])
    rmix = new("ShaderNodeMix")
    rmix.data_type = "FLOAT"
    link(ink_amount.outputs[0], rmix.inputs["Factor"])
    link(rough_out, rmix.inputs["A"])
    rmix.inputs["B"].default_value = INK_ROUGHNESS
    link(rmix.outputs["Result"], bsdf.inputs["Roughness"])
    # 3.10.1 (visual review): cloth catches a grazing sheen that a metal-workflow Principled does not - the gallery
    # renders show it, and the pack docs say to use Unreal's CLOTH shading model (fuzz) for the same read.  A shading
    # model, not a texture: the baked maps are untouched.
    for name, value in (("Sheen Weight", SHEEN), ("Sheen Roughness", 0.35)):
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
    if "Sheen Tint" in bsdf.inputs:
        bsdf.inputs["Sheen Tint"].default_value = (0.62, 0.60, 0.56, 1.0)
    return mat


__all__ = ["DARK", "LETTERING_NAME", "NATURAL", "NATURAL_NAME", "WRAP_MATERIAL", "WRAP_STEM", "bake_kunai",
           "build_wrap_material", "tag_wrap", "wrap_material", "wrap_preview_material", "write_blank_lettering",
           "write_gray_png"]
