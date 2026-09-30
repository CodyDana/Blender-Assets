"""numpy arrays -> Blender mesh objects (UV layers, one colour attribute, custom normals). Blender only."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import bpy
import numpy as np


def make_mesh(name: str, V: np.ndarray, faces: Sequence[np.ndarray], uvs: Optional[Dict[str, Sequence[np.ndarray]]] = None,
              colour: Optional[np.ndarray] = None, colour_name: str = "Color", normals: Optional[np.ndarray] = None,
              smooth: bool = True, collection: Optional["bpy.types.Collection"] = None) -> "bpy.types.Object":
    """``faces`` is a list of (F, k) int arrays (k = 3 or 4, any mix of arrays); every UV layer is a list of
    (F, k, 2) arrays in the same order. UV layers are created in dict order (index 0, 1, 2, 3)."""
    V = np.asarray(V, dtype=np.float32)
    loops = np.concatenate([np.asarray(f, dtype=np.int64).ravel() for f in faces])
    sizes = np.concatenate([np.full(len(f), np.asarray(f).shape[1], dtype=np.int64) for f in faces])
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(len(loops))
    me.loops.foreach_set("vertex_index", loops.astype(np.int32))
    me.polygons.add(len(sizes))
    me.polygons.foreach_set("loop_start", starts.astype(np.int32))
    me.update(calc_edges=True)
    if uvs:
        for uv_name, parts in uvs.items():
            flat = np.concatenate([np.asarray(p, dtype=np.float32).reshape(-1, 2) for p in parts])
            if len(flat) != len(loops):
                raise ValueError(f"{name}: UV layer {uv_name} has {len(flat)} loops, mesh has {len(loops)}")
            layer = me.uv_layers.new(name=uv_name)
            layer.data.foreach_set("uv", flat.ravel())
    if colour is not None:
        attr = me.color_attributes.new(colour_name, "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", np.asarray(colour, dtype=np.float32).ravel())
        me.color_attributes.active_color = attr
        me.color_attributes.render_color_index = 0
    me.polygons.foreach_set("use_smooth", np.full(len(sizes), smooth, dtype=bool))
    if normals is not None:
        n = np.asarray(normals, dtype=np.float32)
        me.normals_split_custom_set_from_vertices(n)
    me.update()
    obj = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def mesh_arrays(obj: "bpy.types.Object"):
    me = obj.data
    V = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    me.calc_loop_triangles()
    T = np.empty(len(me.loop_triangles) * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", T)
    return V.astype(np.float64), T.reshape(-1, 3)
