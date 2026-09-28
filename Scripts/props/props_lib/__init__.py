"""props_lib - the shared library for the prop line (paper bomb, folding fan, smoke bomb).

Mirrors Scripts/shuriken/shuriken_lib: the build script for each prop holds only that
prop's spec and its report text, and everything reusable lives here.  Nothing is
imported eagerly, because several of these need Blender's bpy and a caller may only want
the numeric half.

    spec            build-to numbers for a flat printed prop: size, paper stock, curl,
                    creases, LOD tessellation and bands, sockets, collision, the pack's
                    LOD screen-size rule, and the franchise deny gate.  Pure Python.
    sheet           the GEOMETRY: an isometric deformation (centre line -> curl ->
                    dog-ear), a trimmed outline shared with the texture, a grid whose
                    corner clips and dog-ear crease fall on exact cell diagonals, and a
                    watertight front / back / rim shell with UV0 written from paper
                    coordinates.  numpy only - runs and is testable without bpy.
    atlas           front / back / rim island packing at a stated px/mm, chosen so the
                    artwork's raster and the texture are the SAME pixel grid.
    paperbomb_art   the paper bomb's printed artwork, drawn from scratch: aged paper,
                    the red rules and flourishes, the dry-brush ring, our flame emblem,
                    the seal boxes and every character typeset from MasaFont-Bold.
    geometry        bpy: SheetMesh -> objects, sockets, the containing collision hull.
    paper_material  M_PaperBomb, the one material, built from the baked maps.
    bake            the artwork into the atlas, a real Cycles AO bake, the four PNGs,
                    and the bake that verifies the transfer.
    measure         everything the report states, measured on what was built.
    render          the prop line's gallery rig, and the gates on its images.
    gallery         the six shots.

Generic helpers may be READ from shuriken_lib (gallery rig, world and 1600x900 framing,
bake helpers, measure) but shuriken_lib's behaviour is frozen: where a helper needed to
change, it was COPIED here with the reason on the constant - see ``render``'s docstring.
Scripts/pipeline/** is used exactly as it is.
"""

__version__ = "1.0.0"

__all__ = ["atlas", "bake", "gallery", "geometry", "measure", "paper_material",
           "paperbomb_art", "render", "sheet", "spec"]
