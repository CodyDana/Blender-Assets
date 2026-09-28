import bpy, numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Vector
hp = bpy.data.objects["TP_Throat_HIGH"]; dg = bpy.context.evaluated_depsgraph_get(); bh = BVHTree.FromObject(hp, dg)
for row in (60, 100, 130):
    z = (row - 304) * 0.687 / 1000
    loc, n, i, d = bh.ray_cast(Vector((0.012, -0.2, z)), Vector((0, 1, 0)))
    m = hp.data.materials[hp.data.polygons[i].material_index].name
    print("row", row, "first hit y mm", round(loc.y * 1000, 2), m)
