"""Quick look-dev shots of exported Card Shop Kit FBX files, for comparing a build with its reference sheet.

    python Scripts/cardshop/cloud/bpy_run.py Scripts/cardshop/tools/csk_shot.py -- OUT.png FBX[@x,y,z[,rx,ry,rz]] ...
        [--view front|back|left|right|top|34|34back] [--res 1200x800] [--samples 24] [--margin 1.15]

Placement after ``@`` is in mm and degrees (the item's Seat frame: +X right, +Y away from the customer, +Z up).
The camera frames the bounds of every placed LOD0 mesh (LOD1/2 and UCX hulls are hidden); lights scale with the
scene. Materials are guessed from slot names (glass/pvc/film/acrylic clear, oak, metal, black ...) so shapes read;
this is a shape check, not the final look (that is the Unreal material pass). Cycles CPU: no GPU needed.
"""
import math
import sys

import bpy
from mathutils import Vector

VIEWS = {  # camera direction (from target to camera), ortho?
    "front": (Vector((0, -1, 0)), True), "back": (Vector((0, 1, 0)), True),
    "left": (Vector((-1, 0, 0)), True), "right": (Vector((1, 0, 0)), True),
    "top": (Vector((0, 0, 1)), True), "34": (Vector((0.75, -1.0, 0.65)), False),
    "34back": (Vector((-0.75, 1.0, 0.65)), False),
}
PALETTE = [  # keyword -> (rgb linear, roughness, metallic, transmission-ish alpha)
    (("glass", "pvc", "film", "acrylic", "clear", "window", "slabbody", "diffuser"), ((0.85, 0.92, 0.95), 0.05, 0.0, 0.25)),
    (("oak", "wood"), ((0.36, 0.22, 0.1), 0.55, 0.0, 1.0)),
    (("deck", "cream"), ((0.7, 0.62, 0.48), 0.5, 0.0, 1.0)),
    (("frame", "metal", "alu", "chrome", "steel", "wire"), ((0.75, 0.75, 0.77), 0.3, 1.0, 1.0)),
    (("black", "kick", "base", "rubber"), ((0.015, 0.015, 0.018), 0.5, 0.0, 1.0)),
    (("led", "emissive", "light"), ((1.0, 0.95, 0.85), 0.5, 0.0, 1.0)),
    (("board", "kraft", "carton"), ((0.45, 0.32, 0.18), 0.85, 0.0, 1.0)),
    (("white", "laminate", "plaster", "paper"), ((0.8, 0.8, 0.78), 0.6, 0.0, 1.0)),
    (("pack", "foil"), ((0.05, 0.1, 0.45), 0.25, 0.9, 1.0)),
    (("print", "card", "box", "sign", "poster"), ((0.2, 0.25, 0.5), 0.5, 0.0, 1.0)),
]


def parse(argv):
    a = argv[argv.index("--") + 1:]
    out = a.pop(0)
    opts, items = {}, []
    i = 0
    while i < len(a):
        if a[i].startswith("--"):
            opts[a[i][2:]] = a[i + 1]
            i += 2
        else:
            items.append(a[i])
            i += 1
    return out, items, opts


def material(name):
    low = name.lower()
    for keys, (rgb, rough, metal, alpha) in PALETTE:
        if any(k in low for k in keys):
            break
    else:
        rgb, rough, metal, alpha = (0.5, 0.5, 0.52), 0.5, 0.0, 1.0
    m = bpy.data.materials.new("_shot_" + name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Alpha"].default_value = alpha
    if any(k in low for k in ("led", "emissive")):
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = 4.0
    return m


def main():
    out, items, opts = parse(sys.argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    cache = {}
    shown = []
    for spec in items:
        path, _, tr = spec.partition("@")
        before = set(bpy.data.objects)
        bpy.ops.import_scene.fbx(filepath=path)
        new = [o for o in bpy.data.objects if o not in before]
        for o in new:
            if o.type == "MESH":
                if "_LOD1" in o.name or "_LOD2" in o.name or o.name.startswith("UCX_"):
                    o.hide_render = True
                else:
                    shown.append(o)
                    for sl in o.material_slots:
                        n = sl.material.name if sl.material else "none"
                        base = n.split(".")[0]
                        sl.material = cache.setdefault(base, material(base))
        if tr:
            v = [float(x) for x in tr.split(",")]
            for o in new:
                if o.parent is None:
                    o.location = Vector(v[:3]) * 0.001
                    if len(v) > 3:
                        o.rotation_euler = [math.radians(x) for x in v[3:6]]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in shown for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr, size = (lo + hi) / 2, hi - lo
    rad = max(size.length / 2, 0.01)
    # floor + lights scaled to the scene
    fl = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=rad * 20)
    bm.to_mesh(fl.data)
    fl.location = (ctr.x, ctr.y, lo.z - 0.0005)
    fl.data.materials.append(material("floor_grey"))
    sc.collection.objects.link(fl)
    for d, e in (((1.0, -1.2, 1.4), 1.0), ((-1.3, -0.4, 0.9), 0.45), ((0.2, 1.3, 1.0), 0.35)):
        L = bpy.data.objects.new("L", bpy.data.lights.new("L", "AREA"))
        L.location = ctr + Vector(d) * rad * 3
        L.data.size = rad * 2
        L.data.energy = e * 30 * (rad * 3) ** 2 * float(opts.get("light", "1"))
        L.rotation_euler = (ctr - L.location).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(L)
    sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.42, 0.42, 0.44, 1)
    sc.world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    # camera
    view = opts.get("view", "34")
    d, ortho = VIEWS[view]
    d = d.normalized()
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    w, h = (int(x) for x in opts.get("res", "1200x800").split("x"))
    sc.render.resolution_x, sc.render.resolution_y = w, h
    margin = float(opts.get("margin", "1.15"))
    cam.data.clip_start = rad * 0.01
    cam.data.clip_end = rad * 100
    if ortho:
        cam.data.type = "ORTHO"
        ax = [i for i in range(3) if abs(d[i]) < 0.5]            # the two axes the view sees
        sw, sh = size[ax[0]], size[ax[1]] if view != "top" else size[1]
        if view == "top":
            sw, sh = size.x, size.y
        else:
            sw, sh = (size.x if view in ("front", "back") else size.y), size.z
        cam.data.ortho_scale = max(sw, sh * w / h) * margin
        cam.location = ctr + d * rad * 4
    else:
        cam.data.lens = float(opts.get("lens", "50"))
        fov = 2 * math.atan(36 / 2 / cam.data.lens)
        cam.location = ctr + d * (rad * margin / math.sin(fov / 2 * min(1.0, h / w) + 1e-6))
    up = Vector((0, 1, 0)) if view == "top" else Vector((0, 0, 1))
    cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    if view == "top":
        cam.rotation_euler = (0.0, 0.0, 0.0)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = int(opts.get("samples", "24"))
    sc.view_settings.view_transform = "Standard"
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("CSK_SHOT saved", out)


if __name__ == "__main__":
    main()
