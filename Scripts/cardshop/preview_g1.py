#!/usr/bin/env python
"""Preview render of the G1 set, built ONLY from the exported files: the FBX bytes, the .csk.json kit data and the
G1 textures. It re-imports every FBX (a round-trip check), then seats items with the same data the Unreal test map
uses: level grids for the showcase shelves and CONTAIN sockets for card-in-slab / card-in-top-loader / packs-in-box.
Print materials use the plain-texture path (front / back / label chosen by the UV0 tile), so a mis-mapped face
shows at once through the corner colours of the test pattern.

    blender -b --factory-startup --python Scripts/cardshop/preview_g1.py -- [--g1 DIR] [--out PNG] [--samples N]

Defaults: Exports/CardShopKit/G1, Renders/CardShopKit/G1/g1_preview.png. Cycles on the CPU (works without a GPU).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Matrix, Vector

PROJECT = Path(__file__).resolve().parents[2]
MM = 0.001


def args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--g1", default=str(PROJECT / "Exports" / "CardShopKit" / "G1"))
    ap.add_argument("--out", default=str(PROJECT / "Renders" / "CardShopKit" / "G1" / "g1_preview.png"))
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--res", default="1600x900")
    return ap.parse_args(argv)


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def import_item(g1: Path, name: str):
    """Import <name>.fbx; return its LOD0 render mesh (hulls and lower LODs removed)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(g1 / f"{name}.fbx"))
    new = [o for o in bpy.data.objects if o not in before]
    keep = None
    for o in new:
        if o.type == "MESH" and not o.name.startswith("UCX_") and not o.name.endswith(("_LOD1", "_LOD2")):
            keep = o
    for o in new:
        if o is not keep:
            bpy.data.objects.remove(o, do_unlink=True)
    keep.parent = None
    keep.matrix_world = Matrix.Identity(4)
    keep.name = f"T_{name}"
    keep.hide_render = True
    keep.hide_viewport = True
    return keep


def place(template, matrix):
    o = template.copy()
    bpy.context.scene.collection.objects.link(o)
    o.hide_render = False
    o.hide_viewport = False
    o.matrix_world = matrix
    return o


def frame(loc_mm, rot_deg=(0, 0, 0)) -> Matrix:
    return Matrix.Translation(Vector(loc_mm) * MM) @ Euler([math.radians(a) for a in rot_deg], "XYZ").to_matrix().to_4x4()


# ---------------------------------------------------------------------------------------------- materials

def img(path):
    return bpy.data.images.load(str(path), check_existing=True)


def print_material(name, front, back=None, label=None, other=(0.2, 0.2, 0.22), clearcoat=False):
    """Plain-texture path: tile (0,0) front, (1,0) back, (0,1) label, U<0 plain colour."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    bsdf = N["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.35
    if clearcoat:
        bsdf.inputs["Coat Weight"].default_value = 1.0
    uv = N.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(uv.outputs["UV"], sep.inputs[0])
    fr = N.new("ShaderNodeVectorMath")
    fr.operation = "FRACTION"
    L.new(uv.outputs["UV"], fr.inputs[0])

    def tex(path):
        t = N.new("ShaderNodeTexImage")
        t.image = img(path)
        L.new(fr.outputs[0], t.inputs["Vector"])
        return t.outputs["Color"]

    def step(src, edge):   # 1 when src >= edge
        c = N.new("ShaderNodeMath")
        c.operation = "GREATER_THAN"
        c.inputs[1].default_value = edge - 1e-4
        L.new(src, c.inputs[0])
        return c.outputs[0]

    def mix(fac, a, b):
        mx = N.new("ShaderNodeMix")
        mx.data_type = "RGBA"
        L.new(fac, mx.inputs["Factor"])
        if isinstance(a, tuple):
            mx.inputs["A"].default_value = (*a, 1)
        else:
            L.new(a, mx.inputs["A"])
        if isinstance(b, tuple):
            mx.inputs["B"].default_value = (*b, 1)
        else:
            L.new(b, mx.inputs["B"])
        return mx.outputs["Result"]

    col = tex(front)
    if back:
        col = mix(step(sep.outputs["X"], 1.0), col, tex(back))
    if label:
        col = mix(step(sep.outputs["Y"], 1.0), col, tex(label))
    neg = N.new("ShaderNodeMath")
    neg.operation = "LESS_THAN"
    neg.inputs[1].default_value = 0.0
    L.new(sep.outputs["X"], neg.inputs[0])
    col = mix(neg.outputs[0], col, other)
    L.new(col, bsdf.inputs["Base Color"])
    return m


def flat(name, rgb, rough=0.4, metal=0.0, alpha=None, transmission=None, emit=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if transmission is not None:
        b.inputs["Transmission Weight"].default_value = transmission
        b.inputs["IOR"].default_value = 1.5
    if alpha is not None:
        b.inputs["Alpha"].default_value = alpha
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 6.0
    return m


def assign(obj, table):
    for slot in obj.material_slots:
        base = slot.material.name.split(".")[0] if slot.material else ""
        if base in table:
            slot.link = "OBJECT"
            slot.material = table[base]


# ---------------------------------------------------------------------------------------------- scene

def main():
    a = args()
    g1 = Path(a.g1)
    tex = g1 / "Textures"
    clear()
    names = ["SM_CSK_Card_Std", "SM_CSK_TopLoader_35pt", "SM_CSK_Slab_Std", "SM_CSK_Slab_Std_Filled",
             "SM_CSK_Pack_Std_Sealed", "SM_CSK_Box_Booster_S", "SM_CSK_Box_Booster_S_Lid",
             "SM_CSK_Showcase_Full_1778", "SM_CSK_Showcase_Full_Glass_1778", "SM_CSK_Showcase_Full_Door_1778"]
    T = {n: import_item(g1, n) for n in names}
    K = {n: json.loads((g1 / f"{n}.csk.json").read_text(encoding="utf-8")) for n in names}
    mats = {
        "M_CSK_Card": print_material("P_Card", tex / "T_CSK_G1_CardFront_BC.png", tex / "T_CSK_G1_CardBack_BC.png",
                                     other=(0.93, 0.93, 0.9)),
        "M_CSK_Pack": print_material("P_Pack", tex / "T_CSK_G1_PackFront_BC.png", tex / "T_CSK_G1_PackBack_BC.png",
                                     other=(0.75, 0.75, 0.78)),
        "M_CSK_SlabBody": print_material("P_SlabBody", tex / "T_CSK_G1_Label_BC.png", None, None,
                                         other=(0.92, 0.93, 0.95)),
        "M_CSK_SlabFilled": print_material("P_SlabFilled", tex / "T_CSK_G1_CardFront_BC.png",
                                           tex / "T_CSK_G1_CardBack_BC.png", tex / "T_CSK_G1_Label_BC.png",
                                           other=(0.92, 0.93, 0.95), clearcoat=True),
        "M_CSK_BoxPrint": print_material("P_Box", tex / "T_CSK_G1_BoxDieline_BC.png", other=(0.8, 0.78, 0.72)),
        "M_CSK_SlabWindow": flat("P_Acrylic", (1, 1, 1), 0.03, transmission=1.0),
        "M_CSK_PVC": flat("P_PVC", (0.9, 0.95, 1.0), 0.08, transmission=1.0),
        "M_CSK_Glass": flat("P_Glass", (0.92, 1.0, 0.96), 0.02, transmission=1.0),
        "M_CSK_Board": flat("P_Board", (0.78, 0.72, 0.62), 0.8),
        "M_CSK_Frame": flat("P_Alu", (0.8, 0.8, 0.82), 0.3, 1.0),
        "M_CSK_Base": flat("P_Base", (0.04, 0.04, 0.045), 0.5),
        "M_CSK_LED": flat("P_LED", (1, 1, 1), 0.5, emit=(1.0, 0.95, 0.85)),
    }
    for t in T.values():
        assign(t, mats)
    # the slab label: the body material shows the label texture only on the label tile (0,1)
    sb = mats["M_CSK_SlabBody"]
    sep = next(n for n in sb.node_tree.nodes if n.bl_idname == "ShaderNodeSeparateXYZ")
    cmp = sb.node_tree.nodes.new("ShaderNodeMath")
    cmp.operation = "LESS_THAN"
    cmp.inputs[1].default_value = 1.0 - 1e-4
    sb.node_tree.links.new(sep.outputs["Y"], cmp.inputs[0])
    mx = sb.node_tree.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    bsdf = sb.node_tree.nodes["Principled BSDF"]
    old = bsdf.inputs["Base Color"].links[0].from_socket
    sb.node_tree.links.new(cmp.outputs[0], mx.inputs["Factor"])
    sb.node_tree.links.new(old, mx.inputs["A"])
    mx.inputs["B"].default_value = (0.92, 0.93, 0.95, 1)
    sb.node_tree.links.new(mx.outputs["Result"], bsdf.inputs["Base Color"])

    sc = K["SM_CSK_Showcase_Full_1778"]
    socks = {s["name"]: s for s in sc["sockets"]}
    place(T["SM_CSK_Showcase_Full_1778"], Matrix.Identity(4))
    place(T["SM_CSK_Showcase_Full_Glass_1778"], Matrix.Identity(4))
    for side, off in (("Door_L", 0.0), ("Door_R", 420.0)):       # the right door slid open to show the seating
        s = socks[side]
        place(T["SM_CSK_Showcase_Full_Door_1778"], frame((s["loc_mm"][0] - off, *s["loc_mm"][1:]), s["rot_deg"]))

    def grid(level, cls):
        lv = next(l for l in sc["levels"] if l["socket"] == level)
        g = next(x for x in lv["grids"] if x["class"] == cls)
        o = socks[level]["loc_mm"]
        (px, py), (fx, fy) = g["pitch_mm"], g["first_mm"]
        return [(o[0] + fx + c * px, o[1] + fy + r * py, o[2]) for r in range(g["rows"]) for c in range(g["cols"])]

    def contain(item, socket):
        s = next(x for x in K[item]["sockets"] if x["name"] == socket)
        return frame(s["loc_mm"], s["rot_deg"])

    placed = 0
    # S2: top-loaders with cards
    for p in grid("Level_S2", "CardProt")[:12]:
        m = frame(p)
        place(T["SM_CSK_TopLoader_35pt"], m)
        place(T["SM_CSK_Card_Std"], m @ contain("SM_CSK_TopLoader_35pt", "Card"))
        placed += 2
    # S1: empty slabs with cards (front row) and filled slabs (back row)
    s1 = grid("Level_S1", "Slab")
    cols = next(g for l in sc["levels"] if l["socket"] == "Level_S1" for g in l["grids"] if g["class"] == "Slab")["cols"]
    for i, p in enumerate(s1):
        m = frame(p)
        if i < cols:
            place(T["SM_CSK_Slab_Std"], m)
            place(T["SM_CSK_Card_Std"], m @ contain("SM_CSK_Slab_Std", "Card"))
            placed += 2
        else:
            place(T["SM_CSK_Slab_Std_Filled"], m)
            placed += 1
    # Deck: two booster boxes (lid folded back, 36 packs inside) + loose packs
    bx = grid("Level_Deck", "BoxS")
    for p in bx[:2]:
        m = frame(p)
        place(T["SM_CSK_Box_Booster_S"], m)
        lid = next(x for x in K["SM_CSK_Box_Booster_S"]["sockets"] if x["name"] == "Lid")
        place(T["SM_CSK_Box_Booster_S_Lid"], m @ frame(lid["loc_mm"], (-160.0, 0, 0)))
        for s in K["SM_CSK_Box_Booster_S"]["sockets"]:
            if s["name"].startswith("Pack_"):
                place(T["SM_CSK_Pack_Std_Sealed"], m @ frame(s["loc_mm"], s["rot_deg"]))
                placed += 1
    for p in grid("Level_Deck", "Pack")[14:22]:
        place(T["SM_CSK_Pack_Std_Sealed"], frame(p))
        placed += 1

    # hero row on a table in front: card front / card back / slab + card / filled slab / pack front / pack back
    HX = 3000.0                    # the hero row sits apart from the case, on its own table
    table = bpy.data.meshes.new("Table")
    table.from_pydata([(2.35, -0.25, 0.0), (3.65, -0.25, 0.0), (3.65, 0.25, 0.0), (2.35, 0.25, 0.0)], [],
                      [(0, 1, 2, 3)])
    tob = bpy.data.objects.new("Table", table)
    tob.data.materials.append(flat("P_Table", (0.35, 0.3, 0.26), 0.6))
    bpy.context.scene.collection.objects.link(tob)
    hero = [("SM_CSK_Card_Std", 0), ("SM_CSK_Card_Std", 180), ("SM_CSK_Slab_Std", 0), ("SM_CSK_Slab_Std_Filled", 0),
            ("SM_CSK_Pack_Std_Sealed", 0), ("SM_CSK_Pack_Std_Sealed", 180), ("SM_CSK_TopLoader_35pt", 0)]
    for i, (n, flip) in enumerate(hero):
        x = HX - 540.0 + i * 180.0
        m = frame((x, 0.0, 0.0)) @ frame((0, 0, 0), (0, flip, 0)) @ \
            (frame((0, 0, -K[n]["render_aabb_mm"][1][2])) if flip else Matrix.Identity(4))
        place(T[n], m)
        if n == "SM_CSK_Slab_Std":
            place(T["SM_CSK_Card_Std"], m @ contain(n, "Card"))
        if n == "SM_CSK_TopLoader_35pt":
            place(T["SM_CSK_Card_Std"], m @ contain(n, "Card"))

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = a.samples
    try:
        scene.cycles.use_denoising = True
    except Exception:  # noqa: BLE001
        pass
    rx, ry = (int(v) for v in a.res.split("x"))
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.57, 0.6, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    scene.world = world
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-30))
    scene.collection.objects.link(sun)
    area = bpy.data.objects.new("Key", bpy.data.lights.new("Key", "AREA"))
    area.data.energy = 400
    area.data.size = 2.0
    area.location = (0.8, -2.2, 2.2)
    area.rotation_euler = (math.radians(55), 0, math.radians(20))
    scene.collection.objects.link(area)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shots = {"overview": ((-1.05, -2.05, 1.35), (68, 0, -24), 28),
             "hero": ((3.0, -0.62, 0.72), (41, 0, 0), 45),
             "inside": ((0.55, -0.95, 0.62), (78, 0, 18), 24)}
    written = []
    for shot, (loc, rot, lens) in shots.items():
        cam = bpy.data.objects.new(f"Cam_{shot}", bpy.data.cameras.new(f"Cam_{shot}"))
        cam.data.lens = lens
        cam.location = loc
        cam.rotation_euler = tuple(math.radians(v) for v in rot)
        scene.collection.objects.link(cam)
        scene.camera = cam
        path = out.with_name(f"{out.stem}_{shot}{out.suffix}")
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        written.append(path.name)
    print(f"CSK_G1_PREVIEW {out.parent} {written} placed={placed}")


if __name__ == "__main__":
    main()
