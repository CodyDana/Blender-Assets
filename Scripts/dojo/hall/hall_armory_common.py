"""HALL + ARMORY round (2026-10-01): shared Blender-side helpers for the composed check / render blend.

  append_kit(path, colls, into)    append every object of the named collections of a .blend (meshes + UCX children)
  place(asm, kit_obj, name, loc, rot_z)   a linked-data instance in the Assembly (the showcase's naming piece__NNNN)
  import_armory(kit, interior)     import the armory's interior FBXs (Exports/ArmoryKit, READ ONLY) as Kit objects named
                                   by piece with their UCX children; returns {piece: object}
  hall_local_to_world(p)           world = hall-local + (22.0, 24.0, 0.5)

The armory's files are only read (FBX import); nothing under Scripts/armory, Exports/ArmoryKit or WorkFiles/armory is
written.
"""
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HALL_ORIGIN = Vector((22.0, 24.0, 0.5))


def hall_local_to_world(p):
    return Vector(p) + HALL_ORIGIN


def mat_of(loc, rot_z):
    return Matrix.Translation(Vector(loc)) @ Matrix.Rotation(math.radians(rot_z), 4, "Z")


def append_kit(path, colls, into):
    """Append the objects of collections `colls` of the blend at `path`; link them into collection `into`. Returns
    {name: object} of the appended top-level (non-UCX) meshes."""
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c in colls]
    out = {}
    for c in dst.collections:
        if c is None:
            continue
        for o in list(c.objects):
            into.objects.link(o)
            if o.type == "MESH" and not o.name.startswith("UCX_"):
                out[o.name] = o
        bpy.data.collections.remove(c)
    return out


def remove_object_tree(o):
    for h in list(o.children):
        bpy.data.objects.remove(h, do_unlink=True)
    bpy.data.objects.remove(o, do_unlink=True)


def place(asm, kit_obj, name, loc, rot_z):
    o = bpy.data.objects.new(name, kit_obj.data)
    o.matrix_world = mat_of(loc, rot_z)
    asm.objects.link(o)
    return o


def import_armory(kit, interior):
    """Import every armory piece used in interior_layout.json (FBX, read-only) into `kit`. An FBX with LODs arrives as
    <piece>_LOD0.. under an empty: LOD0 is kept as <piece>, its UCX renamed to UCX_<piece>_NN. Returns
    ({piece: object}, report)."""
    got, rep = {}, {}
    for piece, info in sorted(interior["pieces"].items()):
        fbx = ROOT / info["fbx"]
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=str(fbx))
        new = [o for o in bpy.data.objects if o not in before]
        main = next((o for o in new if o.name == piece), None) or \
            next((o for o in new if o.name.startswith(piece + "_LOD0")), None)
        if main is None:
            rep[piece] = {"error": "no mesh", "objects": [o.name for o in new]}
            for o in new:
                bpy.data.objects.remove(o, do_unlink=True)
            continue
        ucx = [o for o in new if o.name.startswith("UCX_") and o.type == "MESH"
               and ("_LOD" not in o.name or "_LOD0_" in o.name)]
        keep = {main.name} | {u.name for u in ucx}
        imported_matrix = [[round(v, 5) for v in row] for row in main.matrix_world]
        for o in [main] + ucx:           # bake every import transform into the mesh: Kit objects sit at identity
            mw = o.matrix_world.copy()
            o.parent = None
            o.data = o.data.copy()
            o.data.transform(mw)
            o.matrix_world = Matrix.Identity(4)
        for o in new:
            if o.name not in keep:
                bpy.data.objects.remove(o, do_unlink=True)
        main.name = piece
        main.data.name = piece
        for i, u in enumerate(sorted(ucx, key=lambda q: q.name)):
            u.name = f"UCX_{piece}_{i:02d}"
            u.parent = main
            u.matrix_parent_inverse = Matrix.Identity(4)
        for o in [main] + ucx:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            kit.objects.link(o)
        bb = [main.matrix_world @ Vector(c) for c in main.bound_box]
        rep[piece] = {"ucx": len(ucx), "verts": len(main.data.vertices),
                      "bbox": [round(min(p[i] for p in bb), 4) for i in range(3)] +
                              [round(max(p[i] for p in bb), 4) for i in range(3)],
                      "imported_matrix": imported_matrix}
        got[piece] = main
    return got, rep
