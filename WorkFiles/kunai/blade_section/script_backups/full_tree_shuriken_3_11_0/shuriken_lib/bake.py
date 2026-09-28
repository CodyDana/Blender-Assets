"""Texture bake: M_Shuriken_Master -> T_Shuriken_<Form>_BC / _ORM / _N on LOD0's UV0.

Why (visual review, material honesty): the blackened coat, the worn steel at the points,
the bright ground bevels, the grind and the scratches were Cycles-only procedural
shading, and the FBX carries one slot with Principled scalars - so the gallery showed a
finish no buyer would receive.  This module writes that finish into the three maps study
4 names, and the gallery beauty shots are rendered from those maps ONLY
(``preview_material``), never from the procedural source.

Maps (study 4 "Material setup"): BC is sRGB base colour; ORM is linear, AO in R,
roughness in G, metallic in B; N is a tangent-space normal map in DirectX convention
(green flipped from Blender's OpenGL bake).  2048 px per form (study 4: author at 2K), 16 px
padding with the EXTEND margin (ASSET_GUIDELINES 4 / study 3.4).  LOD1..n share the maps:
their UV0 comes from LOD0's islands (shuriken_lib.uv).

How: each scalar channel is baked as EMIT with the Principled input's source socket
wired into a temporary Emission shader, which bakes the value itself (a DIFFUSE colour
bake of a metal is ~0, because Cycles weights the diffuse lobe by 1 - metallic).  AO and
the tangent-space normal (which carries the material's bump) are native Cycles bakes.
Everything temporary is removed again and the material's links are restored exactly.

The ORM and N files have their PNG colour chunks (sRGB / gAMA / cHRM) stripped after the
write (``strip_colour_chunks``): Blender adds them to every PNG, and a data map must not
self-describe as sRGB.  The report records the chunk list of every map.

3.8.1 (spike maintenance): ``size`` may be a (width, height) pair - the spike's four 150 mm strips
bake to 2048 x 512 instead of filling 14 % of a 2048 square - and ``fill_unused`` gives every texel
outside the islands and their bake margin (found by baking a constant white coverage mask with the
same margin) the mean of the covered texels (BC, AO / roughness / metallic) or a flat normal, so
mips and wrap addressing never pull black - AO 0, roughness 0, metallic 0 - into the edge texels.
Both default to the old behaviour (square, no fill): the stars' maps are unchanged.
"""
from __future__ import annotations

import contextlib
import hashlib
from pathlib import Path
from typing import Dict, Iterator

import bpy
import numpy as np

from pipeline.helpers import selection
from pipeline.textures import DATA_COLORSPACE, image_pixels, write_png

TEXTURE_SIZE = 2048
BAKE_MARGIN = 16
EMIT_SAMPLES = 16
AO_SAMPLES = 64
NORMAL_SAMPLES = 16
MAP_SUFFIXES = ("BC", "ORM", "N")


def texture_stem(mesh_name: str) -> str:
    """``SM_Shuriken_EightPoint`` -> ``T_Shuriken_EightPoint`` (study 4 naming)."""
    return "T_" + (mesh_name[len("SM_"):] if mesh_name.startswith("SM_") else mesh_name)


def texture_paths(out_dir: Path, mesh_name: str) -> Dict[str, Path]:
    stem = texture_stem(mesh_name)
    return {suffix: Path(out_dir) / f"{stem}_{suffix}.png" for suffix in MAP_SUFFIXES}


BAKE_DEVICE = {"device": None}


def _bake_device(scene) -> str:
    """Bake on the GPU (OPTIX) when there is one: the knife-grind pass's material (two-cell micro-
    scratch families, flecks, cavity grime) took ~2-3 min per form to bake on the CPU."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for device in prefs.devices:
            device.use = (device.type == "OPTIX")
        if any(device.use for device in prefs.devices):
            scene.cycles.device = "GPU"
            return "GPU (OPTIX)"
    except Exception as exc:                                   # pragma: no cover
        print(f"[bake] OPTIX unavailable, baking on the CPU: {exc}")
    scene.cycles.device = "CPU"
    return "CPU"


@contextlib.contextmanager
def _bake_scene(samples: int) -> Iterator[None]:
    scene = bpy.context.scene
    bake = scene.render.bake
    saved = (scene.render.engine, scene.cycles.samples, scene.cycles.use_denoising, bake.margin,
             bake.margin_type, bake.use_clear, bake.use_selected_to_active, bake.target)
    saved_device = scene.cycles.device
    scene.render.engine = "CYCLES"
    BAKE_DEVICE["device"] = _bake_device(scene)
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    bake.margin = BAKE_MARGIN
    bake.margin_type = "EXTEND"
    bake.use_clear = True
    bake.use_selected_to_active = False
    bake.target = "IMAGE_TEXTURES"
    try:
        yield
    finally:
        (scene.render.engine, scene.cycles.samples, scene.cycles.use_denoising, bake.margin,
         bake.margin_type, bake.use_clear, bake.use_selected_to_active, bake.target) = saved
        scene.cycles.device = saved_device


def _new_image(name: str, size, data: bool) -> "bpy.types.Image":
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    width, height = (size, size) if isinstance(size, int) else (int(size[0]), int(size[1]))
    image = bpy.data.images.new(name, width=width, height=height, alpha=False, float_buffer=data, is_data=data)
    image.colorspace_settings.name = DATA_COLORSPACE if data else "sRGB"
    return image


def _bake(obj, material, image, bake_type: str, samples: int, **kwargs) -> None:
    tree = material.node_tree
    node = tree.nodes.new("ShaderNodeTexImage")
    node.name = "__shuriken_bake_target"
    node.image = image
    previous = tree.nodes.active
    for other in tree.nodes:
        other.select = False
    node.select = True
    tree.nodes.active = node
    try:
        with _bake_scene(samples), selection([obj], obj):
            result = bpy.ops.object.bake(type=bake_type, margin=BAKE_MARGIN, margin_type="EXTEND",
                                         use_clear=True, use_selected_to_active=False, **kwargs)
        if "FINISHED" not in result:
            raise RuntimeError(f"{bake_type} bake of {obj.name} failed: {result}")
    finally:
        tree.nodes.remove(node)
        if previous is not None:
            tree.nodes.active = previous


def _bake_channel(obj, material, input_name: str, image, samples: int = EMIT_SAMPLES) -> None:
    """Bake the value feeding the Principled ``input_name`` through a temporary Emission."""
    tree = material.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
    surface_link = output.inputs["Surface"].links[0]
    surface_from = surface_link.from_socket
    socket = bsdf.inputs[input_name]
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.name = "__shuriken_bake_emit"
    emission.inputs["Strength"].default_value = 1.0
    if socket.links:
        tree.links.new(socket.links[0].from_socket, emission.inputs["Color"])
    else:
        value = socket.default_value
        emission.inputs["Color"].default_value = (tuple(value)[:3] + (1.0,)) if hasattr(value, "__len__") \
            else (value, value, value, 1.0)
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    try:
        _bake(obj, material, image, "EMIT", samples)
    finally:
        tree.links.new(surface_from, output.inputs["Surface"])
        tree.nodes.remove(emission)


def _stats(pixels: np.ndarray) -> dict:
    rgb = pixels[..., :3]
    return {"mean": [round(float(v), 4) for v in rgb.reshape(-1, 3).mean(axis=0)],
            "min": [round(float(v), 4) for v in rgb.reshape(-1, 3).min(axis=0)],
            "max": [round(float(v), 4) for v in rgb.reshape(-1, 3).max(axis=0)]}


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COLOUR_CHUNKS = (b"sRGB", b"gAMA", b"cHRM", b"iCCP")


def png_chunks(path: Path) -> list:
    """Chunk type names of a PNG file, in order."""
    data = Path(path).read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path} is not a PNG")
    names, pos = [], len(PNG_SIGNATURE)
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        names.append(data[pos + 4:pos + 8].decode("latin-1"))
        pos += 12 + length
    return names


def strip_colour_chunks(path: Path) -> list:
    """Remove the sRGB / gAMA / cHRM / iCCP chunks from a PNG in place; return what was removed.

    Blender's PNG writer adds an sRGB colour description to every file, Non-Color tag or not,
    so the ORM and normal maps self-described as sRGB to any tool that honours PNG colour
    chunks (Unreal ignores them; other DCCs and previewers do not).  Data maps carry no colour
    chunk after this; the pixel data is untouched (chunks are copied byte for byte with their
    CRCs, so the file stays valid).
    """
    path = Path(path)
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"{path} is not a PNG")
    out, removed, pos = [PNG_SIGNATURE], [], len(PNG_SIGNATURE)
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind = data[pos + 4:pos + 8]
        end = pos + 12 + length
        if kind in COLOUR_CHUNKS:
            removed.append(kind.decode("latin-1"))
        else:
            out.append(data[pos:end])
        pos = end
    if removed:
        path.write_bytes(b"".join(out))
    return removed


@contextlib.contextmanager
def _alone(obj) -> Iterator[None]:
    """Hide every other object from render: the UCX hull encloses LOD0, and every form's LODs
    sit at the origin, so an AO bake would otherwise be occluded by all of them."""
    saved = {other.name: other.hide_render for other in bpy.data.objects}
    for other in bpy.data.objects:
        other.hide_render = other is not obj
    try:
        yield
    finally:
        for name, value in saved.items():
            other = bpy.data.objects.get(name)
            if other is not None:
                other.hide_render = value


def _coverage(obj, material, size) -> np.ndarray:
    """(h, w) bool: texels an island or its BAKE_MARGIN EXTEND margin writes (a constant white EMIT bake)."""
    image = _new_image("__shuriken_coverage", size, data=True)
    tree = material.node_tree
    output = next(n for n in tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output)
    surface_from = output.inputs["Surface"].links[0].from_socket
    emission = tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    emission.inputs["Strength"].default_value = 1.0
    tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    try:
        _bake(obj, material, image, "EMIT", 1)
        return image_pixels(image)[..., 0] > 0.5
    finally:
        tree.links.new(surface_from, output.inputs["Surface"])
        tree.nodes.remove(emission)
        bpy.data.images.remove(image)


def _fill(pixels: np.ndarray, covered: np.ndarray, value=None) -> np.ndarray:
    """``pixels`` with every uncovered texel set to ``value`` (default: the covered texels' mean), alpha kept."""
    out = pixels.copy()
    fill = pixels[covered][:, :3].mean(axis=0) if value is None else np.asarray(value, dtype=np.float32)
    out[~covered, :3] = fill
    return out


def bake_form(lod0, material, out_dir: Path, size=TEXTURE_SIZE, fill_unused: bool = False) -> dict:
    """Bake BC / ORM / N for ``lod0`` (UV0) and write them to ``out_dir``; return a report.

    ``size``: an int (square maps, the pack's default) or (width, height); ``fill_unused``: see the docstring."""
    with _alone(lod0):
        return _bake_form(lod0, material, out_dir, size, fill_unused)


def _bake_form(lod0, material, out_dir: Path, size, fill_unused: bool = False, stem=None) -> dict:
    """``stem`` (3.10, the kunai's second material slot): the maps' name stem; None = T_<form> from LOD0's name."""
    if stem is None:
        paths = texture_paths(out_dir, lod0.name.replace("_LOD0", ""))
        stem = texture_stem(lod0.name.replace("_LOD0", ""))
    else:
        paths = {suffix: Path(out_dir) / f"{stem}_{suffix}.png" for suffix in MAP_SUFFIXES}
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    made = []
    try:
        bc = _new_image(f"{stem}_BC", size, data=False)
        rough = _new_image(f"{stem}_R", size, data=True)
        metal = _new_image(f"{stem}_M", size, data=True)
        ao = _new_image(f"{stem}_AO", size, data=True)
        normal = _new_image(f"{stem}_N_GL", size, data=True)
        made += [bc, rough, metal, ao, normal]
        _bake_channel(lod0, material, "Base Color", bc)
        _bake_channel(lod0, material, "Roughness", rough)
        _bake_channel(lod0, material, "Metallic", metal)
        _bake(lod0, material, ao, "AO", AO_SAMPLES)
        _bake(lod0, material, normal, "NORMAL", NORMAL_SAMPLES, normal_space="TANGENT",
              normal_r="POS_X", normal_g="POS_Y", normal_b="POS_Z")
        width, height = (size, size) if isinstance(size, int) else (int(size[0]), int(size[1]))
        fill_report = None
        covered = _coverage(lod0, material, size) if fill_unused else None

        if covered is None:
            bc.filepath_raw = str(paths["BC"])
            bc.file_format = "PNG"
            bc.save()
        else:
            bc_px = _fill(image_pixels(bc), covered)
            bc.pixels.foreach_set(np.ascontiguousarray(bc_px, dtype=np.float32).ravel())
            bc.update()
            bc.filepath_raw = str(paths["BC"])
            bc.file_format = "PNG"
            bc.save()
            fill_report = {"covered_fraction": round(float(covered.mean()), 5),
                           "filled_texels": int((~covered).sum()),
                           "BC_fill_stored": [round(float(v), 4) for v in bc_px[~covered][0, :3]] if (~covered).any() else None,
                           "method": ("texels outside every island + its BAKE_MARGIN EXTEND margin (a constant white "
                                      "EMIT coverage bake with the same margin) set to the covered texels' mean; N to "
                                      "a flat (0.5, 0.5, 1.0)")}
        orm = np.empty((height, width, 4), dtype=np.float32)
        orm[..., 0] = image_pixels(ao)[..., 0]
        orm[..., 1] = image_pixels(rough)[..., 0]
        orm[..., 2] = image_pixels(metal)[..., 0]
        orm[..., 3] = 1.0
        if covered is not None:
            orm = _fill(orm, covered)
            fill_report["ORM_fill"] = [round(float(v), 4) for v in orm[~covered][0, :3]] if (~covered).any() else None
        write_png(orm, paths["ORM"], name=f"{stem}_ORM")
        n_gl = image_pixels(normal)
        if covered is not None:
            n_gl = _fill(n_gl, covered, (0.5, 0.5, 1.0))
        n_dx = n_gl.copy()
        n_dx[..., 1] = 1.0 - n_dx[..., 1]          # OpenGL -> DirectX (study 4: green flipped)
        n_dx[..., 3] = 1.0
        write_png(n_dx, paths["N"], name=f"{stem}_N")
        stripped = {suffix: strip_colour_chunks(paths[suffix]) for suffix in ("ORM", "N")}
        chunks = {suffix: png_chunks(path) for suffix, path in paths.items()}

        def condensed(names: list) -> list:
            out: list = []
            for name in names:
                if out and out[-1][0] == name:
                    out[-1][1] += 1
                else:
                    out.append([name, 1])
            return [name if count == 1 else f"{name} x{count}" for name, count in out]

        report = {
            "png_chunks": {suffix: condensed(names) for suffix, names in chunks.items()},
            "colour_chunks_stripped": stripped,
            "data_maps_without_colour_chunks": bool(all(
                not any(c in ("sRGB", "gAMA", "cHRM", "iCCP") for c in chunks[suffix]) for suffix in ("ORM", "N"))),
            "size": [width, height],
            "unused_texel_fill": fill_report,
            "margin_px": BAKE_MARGIN,
            "margin_type": "EXTEND",
            "uv_map": lod0.data.uv_layers[0].name,
            "source_material": material.name,
            "maps": {suffix: str(path) for suffix, path in paths.items()},
            "sha256": {suffix: _sha256(path) for suffix, path in paths.items()},
            "colour_spaces": {"BC": "sRGB", "ORM": "linear (Non-Color): R AO, G roughness, B metallic",
                              "N": "linear (Non-Color), tangent space MikkTSpace, DirectX (green flipped)"},
            "unreal_import": {"BC": "sRGB ON, Compression Default",
                              "ORM": "sRGB OFF, Compression Masks (no alpha) - Unreal's importer does NOT detect "
                                     "this; a plain import decodes roughness 0.32 as 0.08 (mirror steel)",
                              "N": "sRGB OFF, Compression Normalmap, Flip Green Channel OFF (DirectX on disk); "
                                   "the importer auto-detects the _N suffix",
                              "helper": "Scripts/shuriken/ue_import_textures.py sets and verifies these flags"},
            "stats": {"BC_stored_srgb": _stats(image_pixels(bc)),
                             "AO": _stats(image_pixels(ao))["mean"][0],
                             "roughness": _stats(image_pixels(rough))["mean"][0],
                             "metallic": _stats(image_pixels(metal))["mean"][0]},
            "samples": {"emit": EMIT_SAMPLES, "ao": AO_SAMPLES, "normal": NORMAL_SAMPLES},
            "device": BAKE_DEVICE["device"],
            "isolation": "every other object hidden from render during the bake (hull, other LODs, other forms)",
        }
    finally:
        for image in made:
            bpy.data.images.remove(image)
    return report


def preview_material(name: str, maps: Dict[str, str], uv_map: str = "UVMap"):
    """A render-only material that reads the baked maps and nothing else.

    BC (sRGB) -> Base Color, ORM G -> Roughness, ORM B -> Metallic, N (DirectX) -> green
    flipped back to OpenGL -> Normal Map (tangent, UV0) -> Normal.  AO is not used: Cycles
    computes occlusion itself; Unreal uses the R channel for indirect light only.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    new, link = tree.nodes.new, tree.links.new
    out = new("ShaderNodeOutputMaterial")
    bsdf = new("ShaderNodeBsdfPrincipled")
    link(bsdf.outputs["BSDF"], out.inputs["Surface"])
    uv = new("ShaderNodeUVMap")
    uv.uv_map = uv_map

    def image_node(path: str, colour: str):
        node = new("ShaderNodeTexImage")
        node.image = bpy.data.images.load(path, check_existing=False)
        node.image.colorspace_settings.name = colour
        node.interpolation = "Linear"
        link(uv.outputs["UV"], node.inputs["Vector"])
        return node

    bc = image_node(maps["BC"], "sRGB")
    link(bc.outputs["Color"], bsdf.inputs["Base Color"])
    orm = image_node(maps["ORM"], DATA_COLORSPACE)
    split = new("ShaderNodeSeparateColor")
    link(orm.outputs["Color"], split.inputs["Color"])
    link(split.outputs["Green"], bsdf.inputs["Roughness"])
    link(split.outputs["Blue"], bsdf.inputs["Metallic"])
    nrm = image_node(maps["N"], DATA_COLORSPACE)
    nsplit = new("ShaderNodeSeparateColor")
    link(nrm.outputs["Color"], nsplit.inputs["Color"])
    flip = new("ShaderNodeMath")
    flip.operation = "SUBTRACT"
    flip.inputs[0].default_value = 1.0
    link(nsplit.outputs["Green"], flip.inputs[1])
    ncombine = new("ShaderNodeCombineColor")
    link(nsplit.outputs["Red"], ncombine.inputs["Red"])
    link(flip.outputs["Value"], ncombine.inputs["Green"])
    link(nsplit.outputs["Blue"], ncombine.inputs["Blue"])
    nmap = new("ShaderNodeNormalMap")
    nmap.space = "TANGENT"
    nmap.uv_map = uv_map
    link(ncombine.outputs["Color"], nmap.inputs["Color"])
    link(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


__all__ = ["COLOUR_CHUNKS", "MAP_SUFFIXES", "TEXTURE_SIZE", "bake_form", "png_chunks", "preview_material",
           "strip_colour_chunks", "texture_paths", "texture_stem"]
