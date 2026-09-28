#!/usr/bin/env python
"""props_lib.bake - the artwork and the geometry into T_PaperBomb_BC / _ORM / _N / _M.

TWO KINDS OF CHANNEL, AND WHY THEY ARE MADE DIFFERENTLY
-------------------------------------------------------
A bake exists to move information from a place where it is easy to author into a place
where the GPU can sample it.  There are two sorts of information in these maps and they
need different machinery, so this module is honest about which is which.

**Geometric.**  Ambient occlusion is a property of the MESH - the dog-ear's crease, the
rim, the curl - and cannot be computed from the artwork.  It is a real Cycles AO bake on
the LOD0 shell into UV0, through ``pipeline.textures.bake_ao``, and it is the only thing
in these four maps that needs a ray tracer.

**Painted.**  Base colour, roughness, the relief that becomes the normal map and the
three masks all come out of ``paperbomb_art`` as float rasters in CARD MILLIMETRES.
``props_lib.atlas`` is built so that the atlas IS that raster's pixel grid: same px/mm,
integer offset, no rotation, no mirroring on the front.  Pushing those rasters through
Cycles would resample a 1:1 mapping - it would cost minutes and could only lose
sharpness on 0.5 mm brush strokes that are already at the map's Nyquist limit.  So they
are TRANSFERRED, exactly, by ``atlas.compose``.

That is a claim, not a hope, so it is verified rather than asserted: ``verify_transfer``
runs a Cycles EMIT bake of the finished material's base colour back through the mesh's
own UVs and compares it with the transferred BC.  If the UV layout, the island origins,
the row order or the V flip were wrong anywhere, that comparison would show it.  The
measured agreement is in the build report.

SUPERSAMPLING
-------------
The art is drawn at 2x and box-filtered down (``ArtConfig.supersample``), which is what
gives the brush edges and the typeset strokes their anti-aliasing.  A bake would have
had to do this with samples; doing it in the art module is exact and repeatable.

FILE FORMAT
-----------
Eight-bit PNG.  BC is written sRGB-encoded; ORM, N and M are written as linear data and
have their PNG sRGB / gAMA / cHRM chunks STRIPPED afterwards, because Blender writes
those chunks on every PNG and a data map must not describe itself as sRGB.  All four are
2048 square, so Unreal gives them a mip chain - but the gate is set anyway, because a
non-power-of-two PNG silently imports with NoMipmaps and does not stream at all.
"""
from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

from . import atlas as A

MAP_SUFFIXES = ("BC", "ORM", "N", "M")
AO_SAMPLES = 192
BAKE_MARGIN = 16


# ===========================================================================
# PNG
# ===========================================================================

def _chunk(tag: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def write_png(path, arr: np.ndarray, bits: int = 8) -> str:
    """Write ``arr`` (H, W) or (H, W, 3), 0..1 floats, ROW 0 AT THE TOP.

    No colour chunks are written at all, so a data map never claims to be sRGB and a
    colour map is interpreted as sRGB by default, which is what every tool assumes.
    """
    a = np.asarray(arr, np.float64)
    if a.ndim == 2:
        a = a[:, :, None]
    h, w, c = a.shape
    if c not in (1, 3):
        raise ValueError(f"write_png wants 1 or 3 channels, got {c}")
    maxv = (1 << bits) - 1
    q = np.clip(np.rint(a * maxv), 0, maxv).astype(">u2" if bits == 16 else "u1")
    raw = bytearray()
    row_bytes = q[0].tobytes()
    for y in range(h):
        raw.append(0)
        raw += q[y].tobytes()
    ihdr = struct.pack(">IIBBBBB", w, h, bits, 0 if c == 1 else 2, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + _chunk(b"IEND", b""))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(blob)
    return str(path)


def png_chunks(path) -> list:
    data = Path(path).read_bytes()
    out, i = [], 8
    while i < len(data):
        length = struct.unpack(">I", data[i:i + 4])[0]
        out.append(data[i + 4:i + 8].decode("ascii", "replace"))
        i += 12 + length
    return out


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(x, np.float64), 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


# ===========================================================================
# The art
# ===========================================================================

#: How much of the print shows through the back.  The art module's own default is 0.20;
#: at 0.32 the big centre character is legible from behind as a ghost without ever
#: approaching ink values, which is what 80 g/m2 kozo actually does when you hold it up.
#: Study open question 6, answered by looking at the back render.
SHOW_THROUGH = 0.32


def draw_art(spec, plan: A.AtlasPlan, seed: int = 20260919, supersample: int = 2,
             show_through: float = SHOW_THROUGH, ink_floor: str | None = None):
    """Draw both faces at the atlas's own pixel grid, inside the guide-access guard.

    ``ink_floor`` is the one named flag REFERENCE_SPEC row 1 hangs on: ``"reference"``
    (the default) matches the guide's measured paper and ink, ``"floored"`` keeps the
    60/255 non-metal albedo floor the first build wrote down.  Nothing else changes.
    """
    from . import paperbomb_art as art

    cfg = art.ArtConfig(ppmm=plan.ppmm, seed=seed, supersample=supersample,
                        pad_mm=plan.pad_mm, show_through=show_through,
                        ink_floor=ink_floor or art.DEFAULT_INK_FLOOR)
    with art.no_guide_access() as guard:
        front = art.build_front(cfg)
        back = art.build_back(cfg, front=front)
    provenance = art.art_provenance(guard.opened)
    want = plan.raster
    fitted = [_fit_raster(front, want), _fit_raster(back, want)]
    provenance["raster_fit"] = {"wanted": list(want), "front": fitted[0], "back": fitted[1]}
    return cfg, front, back, provenance


def _fit_raster(art_obj, want) -> Dict[str, object]:
    """Edge-extend (or trim) an art raster to the atlas plan's exact size.

    The art module draws at ``ppmm * supersample`` and box-filters down by integer
    division, so a supersampled pass can land one pixel short: 72.476 mm x 25.846 px/mm
    rounds to 1873, and 1873 // 2 is 936 against the plan's 937.  The CARD ORIGIN is
    unaffected - the padding is 32.0 px at 2x, exactly 16.0 after the halving - so the
    fix is to extend the FAR edge, which is padding the bake bleeds into and nothing
    samples.  Changing ``pad_mm`` to make both passes land would have put the card
    origin at 16.154 px and thrown away the exact integer offset the atlas is built on.
    """
    import numpy as np
    from dataclasses import fields

    want_w, want_h = int(want[0]), int(want[1])
    got = (int(art_obj.width), int(art_obj.height))
    if got == (want_w, want_h):
        return {"changed": False, "from": list(got)}
    dw, dh = want_w - got[0], want_h - got[1]
    if abs(dw) > 2 or abs(dh) > 2:
        raise RuntimeError(f"the art raster is {got}, the atlas plan wants {(want_w, want_h)} "
                           "- more than a rounding pixel apart")
    for f in fields(art_obj):
        value = getattr(art_obj, f.name)
        if not isinstance(value, np.ndarray) or value.ndim < 2:
            continue
        # ONLY rasters.  ``outline_mm`` is an (N, 2) POLYLINE in card millimetres and
        # was being padded to the atlas size here - silently, because nothing read it
        # afterwards until the edge-band gate did, and then it failed with "too many
        # values to unpack".  Shape, not type, is what tells the two apart.
        if value.shape[:2] != (got[1], got[0]):
            continue
        a = value[:want_h, :want_w]
        if a.shape[0] < want_h:
            a = np.concatenate([a, np.repeat(a[-1:], want_h - a.shape[0], axis=0)], axis=0)
        if a.shape[1] < want_w:
            a = np.concatenate([a, np.repeat(a[:, -1:], want_w - a.shape[1], axis=1)], axis=1)
        setattr(art_obj, f.name, np.ascontiguousarray(a))

    def _extend(a):
        a = a[:want_h, :want_w]
        if a.shape[0] < want_h:
            a = np.concatenate([a, np.repeat(a[-1:], want_h - a.shape[0], axis=0)], axis=0)
        if a.shape[1] < want_w:
            a = np.concatenate([a, np.repeat(a[:, -1:], want_w - a.shape[1], axis=1)], axis=1)
        return np.ascontiguousarray(a)

    # the two Ink layers are objects, not dataclass array fields, so the loop above
    # never reached them and they stayed a pixel narrower than everything else
    for name in ("ink_black", "ink_red"):
        layer = getattr(art_obj, name, None)
        if layer is not None:
            layer.a = _extend(layer.a)
            layer.d = _extend(layer.d)
    art_obj.width, art_obj.height = want_w, want_h
    return {"changed": True, "from": list(got), "to": [want_w, want_h],
            "method": "edge-extended on the far edge; the card origin is untouched"}


# ===========================================================================
# The transfer
# ===========================================================================

def transfer(plan: A.AtlasPlan, front, back, spec, cfg=None) -> Dict[str, np.ndarray]:
    """Every painted channel into atlas-sized float arrays, row 0 at the top."""
    from .paperbomb_art import palette_for

    pal = palette_for(cfg)
    rim_rgb = A.rim_gradient(pal.paper_edge, pal.paper, plan.size,
                             plan.size - plan.rim_x0)
    base = A.compose(plan, front.base_colour, back.base_colour, rim_rgb)

    rough = A.compose(plan, front.roughness, back.roughness, pal.rough_paper_edge)

    # the normal is computed PER ISLAND, so no gradient is ever taken across the seam
    # between the front island and the back island
    n_front = A.tangent_normal(front.relief, plan.ppmm)
    n_back = A.tangent_normal(back.relief, plan.ppmm)
    normal = A.compose(plan, n_front, n_back, np.array([0.5, 0.5, 1.0], np.float32))

    mask_front = np.stack([front.fringe, front.scorch, front.ink_mask], axis=-1)
    mask_back = np.stack([back.fringe, back.scorch, back.ink_mask], axis=-1)
    mask = A.compose(plan, mask_front, mask_back, np.array([0.0, 0.0, 0.0], np.float32))

    return {"base": base.astype(np.float32), "rough": rough.astype(np.float32),
            "normal": normal.astype(np.float32), "mask": mask.astype(np.float32)}


# ===========================================================================
# The AO bake
# ===========================================================================

def bake_ao_map(obj, size: int, samples: int = AO_SAMPLES) -> Tuple[np.ndarray, Dict[str, object]]:
    """A real Cycles AO bake of ``obj`` on UV0, returned row 0 at the top.

    ``obj`` is baked ALONE.  The other LODs sit exactly on top of it - that is what a LOD
    is - and Cycles traces occlusion against everything visible, so the first run of this
    came back with a mean of 0.354 and a minimum of 0.0: the card was measuring how
    occluded it is by two copies of itself.  Everything else in the scene is hidden from
    the renderer for the duration and restored afterwards.

    Texels the bake never reached (outside every island and its 16 px margin - mostly the
    rim's column) are filled with the mean of the texels it did, so a mip chain can never
    pull AO = 0 into an edge texel and darken the card's border.
    """
    import bpy
    from pipeline.textures import bake_ao, image_pixels

    scene = bpy.context.scene
    saved_engine = scene.render.engine
    hidden = [(o, o.hide_render) for o in bpy.data.objects if o is not obj]
    try:
        for other, _was in hidden:
            other.hide_render = True
        image = bake_ao(obj, "__paperbomb_ao", size=size, samples=samples,
                        margin=BAKE_MARGIN)
        px = image_pixels(image)[..., 0]
        # Blender images are bottom-up; every array in props_lib is top-down
        out = np.ascontiguousarray(px[::-1]).astype(np.float32)
        bpy.data.images.remove(image)
    finally:
        for other, was in hidden:
            other.hide_render = was
        scene.render.engine = saved_engine

    reached = out > 1e-6
    fill = float(out[reached].mean()) if reached.any() else 1.0
    filled = np.where(reached, out, np.float32(fill))
    info = {
        "baked_alone": True,
        "samples": samples,
        "texels_reached": int(reached.sum()),
        "reached_fraction": round(float(reached.mean()), 4),
        "reached_mean": round(fill, 5),
        "reached_min": round(float(out[reached].min()) if reached.any() else -1.0, 5),
        "reached_p01": round(float(np.percentile(out[reached], 1)) if reached.any() else -1.0, 5),
        "unreached_filled_with": round(fill, 5),
    }
    return filled.astype(np.float32), info


# ===========================================================================
# Writing the four maps
# ===========================================================================

def write_maps(out_dir, stem: str, channels: Dict[str, np.ndarray],
               ao: np.ndarray) -> Dict[str, object]:
    """Pack and write BC / ORM / N / M, and report what was written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, str] = {}

    bc = linear_to_srgb(channels["base"])
    paths["BC"] = write_png(out_dir / f"{stem}_BC.png", bc)

    orm = np.zeros(channels["rough"].shape + (3,), np.float32)
    orm[..., 0] = ao
    orm[..., 1] = channels["rough"]
    orm[..., 2] = 0.0                                   # paper is not a metal, anywhere
    paths["ORM"] = write_png(out_dir / f"{stem}_ORM.png", orm)

    paths["N"] = write_png(out_dir / f"{stem}_N.png", channels["normal"])
    paths["M"] = write_png(out_dir / f"{stem}_M.png", channels["mask"])

    report: Dict[str, object] = {"paths": paths, "sha256": {}, "stats": {}, "chunks": {}}
    for key, path in paths.items():
        report["sha256"][key] = sha256(path)
        report["chunks"][key] = png_chunks(path)
    for key, arr in (("BC", bc), ("ORM", orm), ("N", channels["normal"]),
                     ("M", channels["mask"])):
        a = np.asarray(arr, np.float64)
        report["stats"][key] = {
            "size": [int(a.shape[1]), int(a.shape[0])],
            "min": round(float(a.min()), 5), "max": round(float(a.max()), 5),
            "mean": round(float(a.mean()), 5),
            "p50": round(float(np.percentile(a, 50)), 5),
            "p99": round(float(np.percentile(a, 99)), 5),
        }
    report["colour_chunks_present"] = {k: [c for c in v if c in ("sRGB", "gAMA", "cHRM")]
                                       for k, v in report["chunks"].items()}
    report["power_of_two"] = all(
        (s & (s - 1)) == 0 for st in report["stats"].values() for s in st["size"])
    return report


# ===========================================================================
# The verification bake
# ===========================================================================

def _float_image(name: str, arr: np.ndarray) -> "object":
    """A Blender float image from a top-down numpy array, tagged Non-Color."""
    import bpy

    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    a = np.asarray(arr, np.float32)
    if a.ndim == 2:
        a = np.repeat(a[:, :, None], 3, axis=2)
    h, w = a.shape[:2]
    image = bpy.data.images.new(name, width=w, height=h, alpha=False,
                                float_buffer=True, is_data=True)
    image.colorspace_settings.name = "Non-Color"
    rgba = np.ones((h, w, 4), np.float32)
    rgba[:, :, :3] = a[:, :, :3]
    image.pixels.foreach_set(np.ascontiguousarray(rgba[::-1]).ravel())   # Blender is bottom-up
    return image


def verify_transfer(obj, plan: A.AtlasPlan, spec, front_linear: np.ndarray,
                    transferred: np.ndarray, samples: int = 4) -> Dict[str, object]:
    """Prove the transfer with a REAL Cycles bake through a different UV mapping.

    A bake that read the atlas through UV0 and wrote it back through UV0 would be the
    identity and would prove nothing.  This one samples the front art raster through a
    temporary second UV layer in CARD coordinates and bakes it onto UV0, which is a
    genuinely different mapping, and then compares the result with what ``transfer``
    put in the atlas.  A wrong island origin, a wrong V flip, a stale UV layer, a raster
    that is not the plan's size or a mirrored front would all show up here as a large
    difference; the expected difference is zero, because the two grids are aligned by
    construction and the texture is sampled Closest.

    Runs on a TEMPORARY copy of the mesh, so nothing that ships is touched.
    """
    import bpy
    from pipeline.helpers import selection
    from pipeline.textures import image_pixels

    scene = bpy.context.scene
    saved = (scene.render.engine, scene.cycles.samples, scene.render.bake.margin,
             scene.render.bake.margin_type, scene.render.bake.use_clear,
             scene.render.bake.use_selected_to_active, scene.render.bake.target)
    temp = obj.copy()
    temp.data = obj.data.copy()
    temp.name = "__paperbomb_bake_check"
    for parent in obj.users_collection:
        parent.objects.link(temp)
    src = _float_image("__paperbomb_front_src", front_linear)
    dst = bpy.data.images.new("__paperbomb_bake_dst", width=plan.size, height=plan.size,
                              alpha=False, float_buffer=True, is_data=True)
    dst.colorspace_settings.name = "Non-Color"
    mat = bpy.data.materials.new("__paperbomb_bake_check")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()
    out = tree.nodes.new("ShaderNodeOutputMaterial")
    emit = tree.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = src
    tex.interpolation = "Closest"
    tex.extension = "EXTEND"
    uvn = tree.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "CardUV"
    tree.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    tree.links.new(tex.outputs["Color"], emit.inputs["Color"])
    tree.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    target = tree.nodes.new("ShaderNodeTexImage")
    target.image = dst
    for node in tree.nodes:
        node.select = False
    target.select = True
    tree.nodes.active = target

    try:
        mesh = temp.data
        card = mesh.uv_layers.new(name="CardUV")
        rw, rh = plan.raster
        base_uv = mesh.uv_layers[0]
        # every loop's CARD coordinate, recovered from its atlas UV (the front island is
        # an affine of it, so this inverts exactly)
        ox, oy = plan.front_origin
        for i in range(len(mesh.loops)):
            au, av = base_uv.data[i].uv
            px = au * plan.size - ox
            py = (1.0 - av) * plan.size - oy
            card.data[i].uv = ((ox + px) / rw, 1.0 - (oy + py) / rh)
        mesh.uv_layers.active_index = 0                 # bake TARGET is UV0

        front_faces = [p.index for p in mesh.polygons]
        del front_faces
        mesh.materials.clear()
        mesh.materials.append(mat)

        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.render.bake.margin = 0
        scene.render.bake.margin_type = "EXTEND"
        scene.render.bake.use_clear = True
        scene.render.bake.use_selected_to_active = False
        scene.render.bake.target = "IMAGE_TEXTURES"
        with selection([temp], temp):
            result = bpy.ops.object.bake(type="EMIT", margin=0, margin_type="EXTEND",
                                         use_clear=True, use_selected_to_active=False)
        if "FINISHED" not in result:
            raise RuntimeError(f"verification bake failed: {result}")
        baked = np.ascontiguousarray(image_pixels(dst)[..., :3][::-1]).astype(np.float64)
    finally:
        (scene.render.engine, scene.cycles.samples, scene.render.bake.margin,
         scene.render.bake.margin_type, scene.render.bake.use_clear,
         scene.render.bake.use_selected_to_active, scene.render.bake.target) = saved
        bpy.data.objects.remove(temp, do_unlink=True)
        bpy.data.materials.remove(mat)
        bpy.data.images.remove(src)
        bpy.data.images.remove(dst)

    # only the FRONT island is meaningful: the back skin samples the front raster here
    ox, oy = plan.front_origin
    cw, ch = plan.card_px
    x0, x1 = int(ox) + 4, int(ox + cw) - 4
    y0, y1 = int(oy) + 4, int(oy + ch) - 4
    got = baked[y0:y1, x0:x1]
    want = np.asarray(transferred, np.float64)[y0:y1, x0:x1]
    covered = got.sum(axis=-1) > 1e-6
    diff = np.abs(got - want).max(axis=-1)[covered]
    return {
        "method": ("Cycles EMIT bake of the front art sampled through a temporary CardUV "
                   "layer onto UV0, on a throwaway copy of LOD0"),
        "front_island_texels_compared": int(covered.sum()),
        "coverage_fraction": round(float(covered.mean()), 4),
        "max_abs_linear_diff": round(float(diff.max()) if diff.size else -1.0, 6),
        "p999_abs_linear_diff": round(float(np.percentile(diff, 99.9)) if diff.size else -1.0, 6),
        "mean_abs_linear_diff": round(float(diff.mean()) if diff.size else -1.0, 8),
    }


__all__ = ["MAP_SUFFIXES", "draw_art", "transfer", "bake_ao_map", "write_maps",
           "verify_transfer", "write_png", "png_chunks", "sha256", "linear_to_srgb"]
