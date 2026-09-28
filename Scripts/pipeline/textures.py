"""Texture utilities: Cycles AO bake, ORM packing, DirectX normal flip.

Images written by these functions are data maps; load them back with
``load_data_image`` so they carry the ``Non-Color`` colorspace tag (PNG has no
colorspace metadata and Blender would otherwise tag them sRGB). ``image.pixels``
are raw stored values, so channel maths here is done on the stored bytes.
"""
from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Iterator, List, Optional, Tuple, Union

_PACKAGE_PARENT = str(Path(__file__).resolve().parents[1])
if _PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, _PACKAGE_PARENT)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

from pipeline.helpers import selection  # noqa: E402

DATA_COLORSPACE = "Non-Color"
BAKE_MARGIN_TYPE = "EXTEND"  # study 3.4: "Margin to Extend" (5.2 defaults to ADJACENT_FACES)
PathLike = Union[str, Path]


# --------------------------------------------------------------------------- basics

def is_power_of_two(image: Union["bpy.types.Image", Tuple[int, int], int]) -> bool:
    """True when the image (or (w, h) tuple, or int) has power-of-two dimensions."""
    if isinstance(image, int):
        sizes = (image,)
    elif isinstance(image, (tuple, list)):
        sizes = tuple(int(v) for v in image)
    else:
        sizes = tuple(int(v) for v in image.size)
    return all(size > 0 and (size & (size - 1)) == 0 for size in sizes)


def image_pixels(image: "bpy.types.Image") -> np.ndarray:
    """Return the stored pixels of ``image`` as a float32 array of shape (h, w, 4)."""
    width, height = image.size
    if width == 0 or height == 0:
        raise ValueError(f"Image {image.name!r} has no pixel data (missing file?)")
    buffer = np.empty(width * height * 4, dtype=np.float32)
    image.pixels.foreach_get(buffer)
    return buffer.reshape(height, width, 4)


def write_png(pixels: np.ndarray, out_path: PathLike, name: Optional[str] = None, alpha: bool = False) -> str:
    """Write an (h, w, 4) float array in 0-1 as an 8-bit PNG and return the path.

    A temporary image datablock is used and removed afterwards.
    """
    pixels = np.asarray(pixels, dtype=np.float32)
    if pixels.ndim != 3 or pixels.shape[2] != 4:
        raise ValueError("pixels must have shape (h, w, 4)")
    height, width = pixels.shape[:2]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image = bpy.data.images.new(name or out_path.stem, width=width, height=height, alpha=alpha,
                                float_buffer=False, is_data=True)
    try:
        image.colorspace_settings.name = DATA_COLORSPACE
        image.pixels.foreach_set(np.clip(pixels, 0.0, 1.0).ravel())
        image.filepath_raw = str(out_path)
        image.file_format = "PNG"
        image.save()
    finally:
        bpy.data.images.remove(image)
    return str(out_path)


def load_data_image(path: PathLike, name: Optional[str] = None) -> "bpy.types.Image":
    """Load (or reuse) an image from disk tagged ``Non-Color`` for normal/ORM/mask use."""
    image = bpy.data.images.load(str(path), check_existing=True)
    image.colorspace_settings.name = DATA_COLORSPACE
    if name and image.name != name:
        image.name = name
    image.reload()
    return image


# --------------------------------------------------------------------------- AO bake

@contextlib.contextmanager
def _bake_settings(samples: int, margin: int, margin_type: str = BAKE_MARGIN_TYPE) -> Iterator[None]:
    scene = bpy.context.scene
    previous = (scene.render.engine, scene.cycles.samples, scene.render.bake.margin,
                scene.render.bake.use_clear, scene.render.bake.use_selected_to_active,
                scene.render.bake.target, scene.render.bake.margin_type)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.render.bake.margin = margin
    # Study 3.4 asks for "Margin to Extend"; Blender 5.2 defaults to ADJACENT_FACES,
    # whose bleed follows UV adjacency and shows as seam artefacts at 8/16 px padding.
    scene.render.bake.margin_type = margin_type
    scene.render.bake.use_clear = True
    scene.render.bake.use_selected_to_active = False
    scene.render.bake.target = "IMAGE_TEXTURES"
    temp_world = None
    if scene.world is None:
        temp_world = bpy.data.worlds.new("__bake_world")
        scene.world = temp_world
    try:
        yield
    finally:
        (scene.render.engine, scene.cycles.samples, scene.render.bake.margin,
         scene.render.bake.use_clear, scene.render.bake.use_selected_to_active,
         scene.render.bake.target, scene.render.bake.margin_type) = previous
        if temp_world is not None:
            scene.world = None
            bpy.data.worlds.remove(temp_world)


def bake_ao(obj: "bpy.types.Object", image_name: str, size: int = 2048, samples: int = 64,
            margin: int = 16, margin_type: str = BAKE_MARGIN_TYPE) -> "bpy.types.Image":
    """Bake Cycles ambient occlusion of ``obj`` onto its active UV map into a new image.

    A temporary image node is added to every material of ``obj`` (a temporary
    material is created when it has none) and removed afterwards, restoring the
    previously active node. ``margin_type`` defaults to ``EXTEND`` as study 3.4
    requires. The returned image is in memory, tagged Non-Color; save or pack it.
    """
    if obj.type != "MESH":
        raise ValueError(f"{obj.name!r} is not a mesh")
    if not obj.data.uv_layers:
        raise ValueError(f"{obj.name!r} has no UV map to bake to")
    if not is_power_of_two((size, size)):
        raise ValueError(f"size {size} is not a power of two")
    existing = bpy.data.images.get(image_name)
    if existing is not None:
        bpy.data.images.remove(existing)
    image = bpy.data.images.new(image_name, width=size, height=size, alpha=False, is_data=True)
    image.colorspace_settings.name = DATA_COLORSPACE

    temp_material = None
    if not any(slot.material for slot in obj.material_slots):
        temp_material = bpy.data.materials.new("__bake_ao_material")
        obj.data.materials.append(temp_material)
    materials = []
    for slot in obj.material_slots:
        if slot.material is not None and slot.material not in materials:
            materials.append(slot.material)
    temp_nodes: List[Tuple["bpy.types.Material", "bpy.types.Node", Optional["bpy.types.Node"]]] = []
    for material in materials:
        if material.node_tree is None:
            material.use_nodes = True
        tree = material.node_tree
        previous_active = tree.nodes.active
        node = tree.nodes.new("ShaderNodeTexImage")
        node.name = "__bake_ao_target"
        node.image = image
        for other in tree.nodes:
            other.select = False
        node.select = True
        tree.nodes.active = node
        temp_nodes.append((material, node, previous_active))
    try:
        with _bake_settings(samples, margin, margin_type):
            with selection([obj], obj):
                result = bpy.ops.object.bake(type="AO", margin=margin, margin_type=margin_type,
                                             use_clear=True, use_selected_to_active=False)
        if "FINISHED" not in result:
            raise RuntimeError(f"AO bake failed on {obj.name!r}: {result}")
    finally:
        for material, node, previous_active in temp_nodes:
            material.node_tree.nodes.remove(node)
            if previous_active is not None:
                material.node_tree.nodes.active = previous_active
        if temp_material is not None:
            index = obj.data.materials.find(temp_material.name)
            if index >= 0:
                obj.data.materials.pop(index=index)
            bpy.data.materials.remove(temp_material)
    return image


# --------------------------------------------------------------------------- packing

def pack_orm(ao_img: "bpy.types.Image", rough_img: "bpy.types.Image", metal_img: Optional["bpy.types.Image"],
             out_path: PathLike, metal_default: float = 0.0) -> str:
    """Write an 8-bit PNG with R = AO, G = roughness, B = metallic (from the R channel of each source).

    ``metal_img`` may be None, in which case B is filled with ``metal_default``.
    All images must share one power-of-two size. Returns ``out_path``; load it
    back with ``load_data_image`` so it is tagged Non-Color.
    """
    sources = [("ao", ao_img), ("roughness", rough_img)] + ([("metallic", metal_img)] if metal_img else [])
    sizes = {name: tuple(image.size) for name, image in sources}
    if len(set(sizes.values())) != 1:
        raise ValueError(f"ORM inputs differ in size: {sizes}")
    if not is_power_of_two(ao_img):
        raise ValueError(f"ORM input size {sizes['ao']} is not a power of two")
    ao = image_pixels(ao_img)
    rough = image_pixels(rough_img)
    height, width = ao.shape[:2]
    packed = np.empty((height, width, 4), dtype=np.float32)
    packed[..., 0] = ao[..., 0]
    packed[..., 1] = rough[..., 0]
    packed[..., 2] = image_pixels(metal_img)[..., 0] if metal_img else float(np.clip(metal_default, 0.0, 1.0))
    packed[..., 3] = 1.0
    return write_png(packed, out_path, name=Path(out_path).stem)


def flip_normal_green(in_path: PathLike, out_path: PathLike) -> str:
    """Write a copy of the normal map at ``in_path`` with G inverted (OpenGL -> DirectX).

    Returns ``out_path``. Temporary image datablocks are removed; load the result
    with ``load_data_image``.
    """
    in_path = Path(in_path)
    if not in_path.is_file():
        raise FileNotFoundError(str(in_path))
    source = bpy.data.images.load(str(in_path), check_existing=False)
    try:
        source.colorspace_settings.name = DATA_COLORSPACE
        pixels = image_pixels(source)
        has_alpha = bool(source.alpha_mode != "NONE" and source.depth in (32, 64, 128))
    finally:
        bpy.data.images.remove(source)
    pixels[..., 1] = 1.0 - pixels[..., 1]
    return write_png(pixels, out_path, name=Path(out_path).stem, alpha=has_alpha)


__all__ = [
    "DATA_COLORSPACE", "bake_ao", "flip_normal_green", "image_pixels", "is_power_of_two",
    "load_data_image", "pack_orm", "write_png",
]
