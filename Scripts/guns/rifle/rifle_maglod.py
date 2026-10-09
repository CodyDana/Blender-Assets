"""AR-01 magazine LOD1-3 (headless Blender; imported by rifle_mag.py, stage 6, and rifle_game.py, stage 4).

ONE recipe for the magazine's LODs, so the static twin's merged magazine at LOD n is the shipped SM_AR01_Mag_LOD n
(stage-7 fix round, tech review: the twin carried the part generator's coarse levels, 6666 / 6666 / 4430 / 108
triangles, while SM_AR01_Mag ships 6666 / 1998 / 648 / 248; twin LOD1 / LOD2 were 53.8 % / 23.9 % of LOD0 against the
~45 % / ~15 % targets, and its LOD3 magazine was up to 18 mm off the shipped one). Each LOD0 magazine part (closed
solid) is collapse-decimated to its share of LOD_TARGETS[lv], UV0 interpolated (the LOD0 maps stay valid), weighted
normals sharp at 35 deg, UV fold-overs relaxed. Blender's collapse decimation is deterministic, so the same LOD0 parts
give the same LODs in both stages (stage 6 gates it: rifle_mag 'twin_mag_equal').
"""
from __future__ import annotations

import bpy

LOD_TARGETS = {1: 2000, 2: 650, 3: 250}     # plan 3.3: ~1,750 / ~580 / 200-300 (LOD1 a little richer: the pressed ribs)
UVFIX = {}


def lod_mag_objects(lv):
    cn = "AR01_Parts" if lv == 0 else f"AR01_LOD{lv}"
    return [o for o in bpy.data.collections[cn].objects if o.type == "MESH" and o.data.materials
            and o.data.materials[0].name == "M_AR01_Mag"]


def decimated_parts(lv, src=None, suffix=None):
    """LOD lv of the magazine parts (copies linked to the scene collection, named <part>_dec<lv> or <part><suffix>)."""
    from gunlib import bl
    from gunlib import lodfix
    src = lod_mag_objects(0) if src is None else src
    total = sum(len(o.data.polygons) for o in src)
    out = []
    for o in src:
        c = o.copy()
        c.data = o.data.copy()
        c.name = f"{o.name}_dec{lv}" if suffix is None else f"{o.name}{suffix}"
        bpy.context.scene.collection.objects.link(c)
        md = c.modifiers.new("dec", "DECIMATE")
        md.decimate_type = "COLLAPSE"
        md.ratio = LOD_TARGETS[lv] / float(total)
        md.use_collapse_triangulate = True
        bl.apply_modifiers(c)
        bl.finish(c)
        bl.weighted_normals(c, keep_sharp=True, sharp_deg=35.0)
        UVFIX.setdefault(lv, {})[o.name] = lodfix.relax_uv_foldovers(c)
        out.append(c)
    return out
