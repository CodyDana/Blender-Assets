"""Hero pieces (user, 2026-09-27: "for full accuracy ... create the assets in blender", then "start developing them in
Blender"): detailed replacements for the block-built kit pieces, modelled from the user's per-piece reference sheets in
WorkFiles/armory/reference/<name>.png (prompts: WorkFiles/armory/HERO_REFERENCE_PROMPTS.md).

Each hero module is Scripts/armory/hero/hero_<group>.py and defines:
  MATERIALS = {name: (texture set or None, tile m or None, params)}   same format as build_armory_kit.MATERIALS; reuse
                                                                       the kit's M_AK_* names where they fit
  def pieces(G): -> list of G["Piece"] objects, each named EXACTLY like the scripted piece it replaces (same pivot,
                    footprint, facing and height, so layout.json, the lights and the walk check do not change)
A module may also define ENABLED = False to stay out of the build while it is being developed (preview_hero.py still
loads it). A module may add NEW pieces named SM_AK_H_* (things the block build never had, e.g. wall sconces) and place
them with instances() -> [(piece, x, y, z, rot_z)] in the kit frame. A new piece that carries a light (the newel
lanterns) adds it with lights() -> [light dicts in build_armory_kit.lights() format]; the kit's light table picks them
up through lights() below, so the light exists only where the piece does.

The kit build swaps every scripted piece for the hero piece of the same name (swap()). --no-hero on the kit command line
builds the scripted kit only (for before/after renders).

from_object() turns any Blender mesh object (modifiers applied: bevels, arrays, booleans, solidify ...) into a Piece
mesh part, so hero modules can model with the full bpy toolset and still go through the kit's one build path (UV1,
UCX, QA, pipeline export).
"""
import importlib
import os
import sys
from pathlib import Path

HERO_DIR = Path(__file__).resolve().parent / "hero"
G = {}
MODULES = []
MATERIALS = {}
SHARED = "hero_shared"     # hero_shared.py: overrides of the kit's own M_AK_* materials (darker timber, banner, mat ...)
NEW_PREFIX = "SM_AK_H_"   # a module may also add NEW pieces (e.g. wall sconces) named SM_AK_H_* and place them via instances()
ACTIVE = True             # build_armory_kit sets False for --no-hero


def setup(ns):
    global G
    G = ns


def load():
    """Import every hero module and merge its materials (called once by build_armory_kit at import)."""
    if not HERO_DIR.exists():
        return
    sys.path.insert(0, str(HERO_DIR))
    only = os.environ.get("ARMORY_HERO_ONLY")   # preview_hero.py: load just the module being developed
    for f in sorted(HERO_DIR.glob("hero_*.py"), key=lambda f: (f.stem == SHARED, f.stem)):
        if only and f.stem not in only.split(",") + [SHARED]:   # the shared-material overrides always come along
            continue
        m = importlib.import_module(f.stem)
        if only or os.environ.get("ARMORY_HERO_ALL") or getattr(m, "ENABLED", True):   # ALL: test-copy builds   # preview_hero.py develops a module before it is enabled
            MODULES.append(m)
            mats = getattr(m, "MATERIALS", {})
            # calibration pass 1: two modules defining the same material name silently merged (the later file won:
            # the cases wore the lantern's lacquer, the back wall the cases' brass); the names must be unique
            clash = sorted(k for k in mats if k in MATERIALS and MATERIALS[k] != mats[k])
            assert not clash, f"{f.stem} redefines hero materials of another module: {clash}"
            MATERIALS.update(mats)


def swap(pieces, enabled=True):
    """Replace scripted pieces by the hero piece of the same name. Returns (pieces, report)."""
    if not enabled:
        return pieces, {}
    hero = {}
    for m in MODULES:
        for p in m.pieces(G):
            assert p.name not in hero, f"two hero modules build {p.name}"
            hero[p.name] = (p, m.__name__)
    names = {p.name for p in pieces}
    unknown = sorted(n for n in set(hero) - names if not n.startswith(NEW_PREFIX))
    assert not unknown, f"hero pieces with no scripted counterpart (names must match the kit): {unknown}"
    report = {n: mod for n, (_p, mod) in hero.items()}
    new = [hero[n][0] for n in sorted(hero) if n not in names]   # SM_AK_H_* pieces the block build never had
    return [hero[p.name][0] if p.name in hero else p for p in pieces] + new, report


def instances():
    """Placements of the NEW hero pieces (SM_AK_H_*): each module's optional instances() -> [(piece, x, y, z, rot_z)],
    same frame as build_armory_kit.layout(). Empty for a --no-hero build."""
    if not ACTIVE:
        return []
    out = []
    for m in MODULES:
        for inst in getattr(m, "instances", lambda: [])():
            assert inst[0].startswith(NEW_PREFIX), f"{m.__name__}: instances() may only place new SM_AK_H_ pieces"
            out.append(inst)
    return out


def lights():
    """Light entries (build_armory_kit.lights() format) for the NEW hero pieces that carry a light (2026-09-28: the
    newel lanterns): each module's optional lights() -> [dict]. Empty for a --no-hero build, so a light exists only
    where its piece does."""
    if not ACTIVE:
        return []
    out = []
    for m in MODULES:
        out.extend(getattr(m, "lights", lambda: [])())
    return out


def from_object(piece, obj, remove=True):
    """Append obj's evaluated mesh (world transform, modifiers applied, UV0 = its active UV map, per-face material
    names, per-face smooth) to piece as one mesh part. Materials on obj must be named like MATERIALS keys."""
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = obj.matrix_world
    verts = [tuple(mw @ v.co) for v in me.vertices]
    uvl = me.uv_layers.active
    faces, uvs, mats, smooth = [], [], [], []
    slot_names = [s.material.name if s.material else None for s in obj.material_slots]
    for poly in me.polygons:
        faces.append(list(poly.vertices))
        uvs.append([tuple(uvl.data[li].uv) if uvl else (0.0, 0.0) for li in poly.loop_indices])
        name = slot_names[poly.material_index] if slot_names else None
        assert name, f"{obj.name}: face without a material"
        mats.append(name)
        smooth.append(poly.use_smooth)
    ev.to_mesh_clear()
    piece.mesh(verts, faces, uvs, mats, smooth=smooth)
    if remove:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0 and isinstance(data, bpy.types.Mesh):
            bpy.data.meshes.remove(data)
    return piece
