"""One-off source patch (spike maintenance, library 3.8.1): optional hooks in hooks.py, their use in pack.py."""
from pathlib import Path

root = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken\shuriken_lib")
s = ""
name = ""


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:80], s.count(old))
    s = s.replace(old, new)


# ---------------------------------------------------------------- hooks.py
name = "hooks.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''    consistency_class                 "plate" (default) or "bar": which like-with-like rule render.pack_consistency
                                      applies to the form's gallery statistics
''', '''    consistency_class                 "plate" (default) or "bar": which like-with-like rule render.pack_consistency
                                      applies to the form's gallery statistics

Optional since 3.8.1 (spike maintenance; again the defaults are the old code paths):

    texture_size(default)             the baked maps' size: an int (square) or (width, height); default the pack's
    fill_unused_texels                True: after the bake, texels outside every island + bake margin get the
                                      covered texels' mean (no black for mips / wrap to pull in); default False
    lod_deviation_headline()          which lod_deviation figure is the report's lod_surface_deviation_mm
                                      ("lod0_vertices_to_lod", the default, or "two_sided")
    bounds_radius(lod0)               the radius (m) lod_switching turns into switch distances, or None (default:
                                      the largest vertex distance from the origin)
    surface_snapshot(obj)             the form's own lod_surfaces entry, or None (default: measure.surface_snapshot)
    noun / outline_wording            report wording ("star" / "outline (un-ground plate)" by default)
''')
rep('''    # ------------------------------------------------------------------ optional
    consistency_class = "plate"
''', '''    # ------------------------------------------------------------------ optional
    consistency_class = "plate"
    noun = "star"
    outline_wording = "outline (un-ground plate)"
    fill_unused_texels = False

    def texture_size(self, default):
        return default

    def lod_deviation_headline(self) -> str:
        return "lod0_vertices_to_lod"

    def bounds_radius(self, lod0):
        return None

    def surface_snapshot(self, obj):
        return None
''')
p.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------- pack.py
name = "pack.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''def lod_switching(spec: RadialStarSpec, lod0) -> dict:
    """Screen sizes as camera distances, so the thresholds can be judged in metres."""
    co = vertices_of(lod0)
    radius = float(max(math.sqrt(x * x + y * y + z * z) for x, y, z in co))
    sizes = list(spec.lod_screen_sizes[:len(spec.lods)])
    return {''', '''def lod_switching(spec: RadialStarSpec, lod0, radius: Optional[float] = None) -> dict:
    """Screen sizes as camera distances, so the thresholds can be judged in metres.

    ``radius`` (m, 3.8.1): the form's own bounds radius (the spike: Unreal's bounds sphere about the bounding-box
    centre, which its screen sizes are built from); None = the largest vertex distance from the origin, which is
    the same figure for every form whose origin is its bounding-box centre."""
    co = vertices_of(lod0)
    from_origin = float(max(math.sqrt(x * x + y * y + z * z) for x, y, z in co))
    extra = {}
    if radius is None:
        radius = from_origin
    else:
        extra = {"bounds_radius_definition": "the form's bounds_radius hook (Unreal's bounds sphere, bbox centre)",
                 "bounds_radius_from_origin_mm": round(from_origin / MM, 4)}
    sizes = list(spec.lod_screen_sizes[:len(spec.lods)])
    return {**extra,''')
rep('''    report["lod_switching"] = lod_switching(spec, lod0)''',
    '''    report["lod_switching"] = lod_switching(spec, lod0, geo.bounds_radius(lod0))''')
rep('''    report["lod_surfaces"] = {obj.name: surface_snapshot(obj, n) for obj in lod_objects}
    deviations = {obj.name: lod_deviation(lod0, obj, split_radius=geo.split_radius()) for obj in lod_objects[1:]}
    report["lod_surface_deviation_mm"] = {name: d["lod0_vertices_to_lod"] for name, d in deviations.items()}''',
    '''    report["lod_surfaces"] = {obj.name: (geo.surface_snapshot(obj) or surface_snapshot(obj, n)) for obj in lod_objects}
    deviations = {obj.name: lod_deviation(lod0, obj, split_radius=geo.split_radius()) for obj in lod_objects[1:]}
    headline = geo.lod_deviation_headline()
    report["lod_surface_deviation_mm"] = {name: d[headline] for name, d in deviations.items()}
    if headline != "lod0_vertices_to_lod":
        report["lod_surface_deviation_metric"] = headline''')
rep('''    report["uv"] = uv_coverage(lod0, texture_size=options.texel_map)
    report["lod_uv"] = {obj.name: uv_coverage(obj, texture_size=options.texel_map) for obj in lod_objects[1:]}''',
    '''    texel_map = geo.texture_size(options.texel_map)      # 3.8.1: an int, or a form's (width, height)
    report["uv"] = uv_coverage(lod0, texture_size=texel_map)
    report["lod_uv"] = {obj.name: uv_coverage(obj, texture_size=texel_map) for obj in lod_objects[1:]}''')
rep('''    report["uv_consistency"] = {
        "method": "LOD1..n UV0 from LOD0's island maps (shuriken_lib.uv); one texture set for every LOD",
        "overlap_pairs": overlaps,''', '''    report["uv_consistency"] = {
        "method": "LOD1..n UV0 from LOD0's island maps (shuriken_lib.uv); one texture set for every LOD",
        "island_map_deviation_px_at_2048": {name: (t.get("island_map_deviation") or {}).get("max_px_at_2048")
                                            for name, t in report["uv_transfer"].items()},
        "island_map_deviation_note": ("information: per-loop distance of every LODn UV from the affine map of its "
                                      "LOD0 island (uv.transfer_uvs island_map_deviation)"),
        "overlap_pairs": overlaps,''')
rep('''        "source": ("the finished (knife-ground) LOD0 mesh volume x 7.85 g/cm3 - SHURIKEN_STUDY.md 4, Physics: set "
                   "an explicit Mass in KG override"),''', '''        "source": (("the finished (knife-ground) LOD0 mesh volume x 7.85 g/cm3" if geo.noun == "star" else
                    f"the finished {geo.noun} (LOD0 mesh volume) x 7.85 g/cm3")
                   + " - SHURIKEN_STUDY.md 4, Physics: set an explicit Mass in KG override"),''')
rep('''                    "throws the star, and say so in the Fab description."),''',
    '''                    f"throws the {geo.noun}, and say so in the Fab description."),''')
rep('''                 "far a hull-volume mass at steel density would overstate the star. It is NOT Unreal's own "''',
    '''                 f"far a hull-volume mass at steel density would overstate the {geo.noun}. It is NOT Unreal's own "''')
rep('''    report["textures"] = bake_form(fb.lod_objects[0], fb.material, Path(options.texture_dir),
                                   size=options.texture_size)''', '''    geo = fb.geometry
    report["textures"] = bake_form(fb.lod_objects[0], fb.material, Path(options.texture_dir),
                                   size=geo.texture_size(options.texture_size) if geo is not None else options.texture_size,
                                   fill_unused=bool(getattr(geo, "fill_unused_texels", False)))''')
rep('''    report["mass_check"] = {
        "evaluated_on": "outline (un-ground plate)",''', '''    report["mass_check"] = {
        "evaluated_on": getattr(fb.geometry, "outline_wording", "outline (un-ground plate)"),''')
p.write_text(s, encoding="utf-8")
print("patched hooks.py, pack.py")
