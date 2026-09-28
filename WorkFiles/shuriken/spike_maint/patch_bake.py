"""One-off source patch (spike maintenance, library 3.8.1): non-square maps + unused-texel fill (bake.py),
a (width, height) texture size in measure.uv_coverage.  The square path is byte-for-byte the old code."""
from pathlib import Path

root = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\shuriken_lib")
s = ""
name = ""


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:80], s.count(old))
    s = s.replace(old, new)


# ---------------------------------------------------------------- measure.py
name = "measure.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''def uv_coverage(obj, texture_size: int = 2048) -> dict:
    """UV square coverage and area-weighted texel density."""''',
    '''def uv_coverage(obj, texture_size=2048) -> dict:
    """UV square coverage and area-weighted texel density.

    ``texture_size`` is an int (a square map) or, since 3.8.1, a (width, height) pair (the spike's 2048 x 512):
    the density is then sqrt(uv_area x width x height / world area), texels per metre on the map."""''')
rep('''    texels_per_m = math.sqrt(uv_area * (texture_size ** 2) / world_area)''',
    '''    if isinstance(texture_size, (tuple, list)):
        texels_per_m = math.sqrt(uv_area * texture_size[0] * texture_size[1] / world_area)
        texture_size = [int(texture_size[0]), int(texture_size[1])]
    else:
        texels_per_m = math.sqrt(uv_area * (texture_size ** 2) / world_area)''')
p.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------- bake.py
name = "bake.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''The ORM and N files have their PNG colour chunks (sRGB / gAMA / cHRM) stripped after the
write (``strip_colour_chunks``): Blender adds them to every PNG, and a data map must not
self-describe as sRGB.  The report records the chunk list of every map.
"""''', '''The ORM and N files have their PNG colour chunks (sRGB / gAMA / cHRM) stripped after the
write (``strip_colour_chunks``): Blender adds them to every PNG, and a data map must not
self-describe as sRGB.  The report records the chunk list of every map.

3.8.1 (spike maintenance): ``size`` may be a (width, height) pair - the spike's four 150 mm strips
bake to 2048 x 512 instead of filling 14 % of a 2048 square - and ``fill_unused`` gives every texel
outside the islands and their bake margin (found by baking a constant white coverage mask with the
same margin) the mean of the covered texels (BC, AO / roughness / metallic) or a flat normal, so
mips and wrap addressing never pull black - AO 0, roughness 0, metallic 0 - into the edge texels.
Both default to the old behaviour (square, no fill): the stars' maps are unchanged.
"""''')
rep('''def _new_image(name: str, size: int, data: bool) -> "bpy.types.Image":
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    image = bpy.data.images.new(name, width=size, height=size, alpha=False, float_buffer=data, is_data=data)''',
    '''def _new_image(name: str, size, data: bool) -> "bpy.types.Image":
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    width, height = (size, size) if isinstance(size, int) else (int(size[0]), int(size[1]))
    image = bpy.data.images.new(name, width=width, height=height, alpha=False, float_buffer=data, is_data=data)''')
rep('''def bake_form(lod0, material, out_dir: Path, size: int = TEXTURE_SIZE) -> dict:
    """Bake BC / ORM / N for ``lod0`` (UV0) and write them to ``out_dir``; return a report."""
    with _alone(lod0):
        return _bake_form(lod0, material, out_dir, size)


def _bake_form(lod0, material, out_dir: Path, size: int) -> dict:''', '''def _coverage(obj, material, size) -> np.ndarray:
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


def _bake_form(lod0, material, out_dir: Path, size, fill_unused: bool = False) -> dict:''')
rep('''        _bake(lod0, material, normal, "NORMAL", NORMAL_SAMPLES, normal_space="TANGENT",
              normal_r="POS_X", normal_g="POS_Y", normal_b="POS_Z")

        bc.filepath_raw = str(paths["BC"])
        bc.file_format = "PNG"
        bc.save()
        orm = np.empty((size, size, 4), dtype=np.float32)
        orm[..., 0] = image_pixels(ao)[..., 0]
        orm[..., 1] = image_pixels(rough)[..., 0]
        orm[..., 2] = image_pixels(metal)[..., 0]
        orm[..., 3] = 1.0
        write_png(orm, paths["ORM"], name=f"{stem}_ORM")
        n_gl = image_pixels(normal)''', '''        _bake(lod0, material, normal, "NORMAL", NORMAL_SAMPLES, normal_space="TANGENT",
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
            n_gl = _fill(n_gl, covered, (0.5, 0.5, 1.0))''')
rep('''            "size": [size, size],''', '''            "size": [width, height],
            "unused_texel_fill": fill_report,''')
p.write_text(s, encoding="utf-8")
print("patched measure.py, bake.py")
