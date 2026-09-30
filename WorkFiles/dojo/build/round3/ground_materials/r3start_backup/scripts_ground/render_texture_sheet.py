"""Texture sheet renders for kit 2: every ground material as a flat 3 x 3 tiled swatch (orthographic, top down: proves
the tiles are seamless) and a close-up from a 1.7 m eye height, on a grey background under a neutral side light.

Uses the real materials from Assets/Dojo/DojoGround.blend (the same BC/N/ORM + macro maps Unreal gets). Each swatch is
a 12 x 12 m plane = 3 x 3 tiles of 4 m; the sand edge swatch is a field corner (raked field + the 0.5 m edge strip,
mapped exactly as SM_DKG_SandField_13x17) so the rake phase match and the ridge-end caps show.
Writes <out>/sheet_tiles/<Material>_{flat,eye}.png; compare_ground.py --sheet composes TEXTURE_SHEET.png.

Run: blender -b --factory-startup Assets/Dojo/DojoGround.blend --python Scripts/dojo/ground/render_texture_sheet.py --
     [--out DIR] [--samples 32] [--px 640]
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = Path(arg("--out", str(ROOT / "WorkFiles" / "dojo" / "build" / "ground" / "renders" / "f1"))) / "sheet_tiles"
PX = int(arg("--px", "640"))
MATS = ["M_DKG_SandRaked", "M_DKG_SandEdge", "M_DKG_Granite", "M_DKG_GraniteHewn", "M_DKG_Gravel", "M_DKG_GravelCoarse",
        "M_DKG_Soil", "M_DKG_EdgeTimber"]


def mesh_obj(name, quads, origin):
    """quads: list of (4 corner (x, y) tuples, material, uv function)."""
    me = bpy.data.meshes.new(name)
    verts, faces, uvs, mats = [], [], [], []
    for corners, mat, fn in quads:
        base = len(verts)
        verts += [(x, y, 0.0) for x, y in corners]
        faces.append(tuple(range(base, base + 4)))
        uvs.append([fn(x, y) for x, y in corners])
        if mat not in mats:
            mats.append(mat)
    me.from_pydata(verts, [], faces)
    uvl = me.uv_layers.new(name="UV0")
    for poly, fuv in zip(me.polygons, uvs):
        for li, uv in zip(poly.loop_indices, fuv):
            uvl.data[li].uv = uv
    ca = me.color_attributes.new("Wear", "FLOAT_COLOR", "CORNER")
    for d in ca.data:
        d.color = (1, 1, 1, 1)
    for m in mats:
        me.materials.append(bpy.data.materials[m])
    for poly, (_, mat, _) in zip(me.polygons, quads):
        poly.material_index = mats.index(mat)
    o = bpy.data.objects.new(name, me)
    o.location = origin
    bpy.context.scene.collection.objects.link(o)
    return o


def main():
    sc = bpy.context.scene
    for c in list(sc.collection.children):   # hide the kit and the assembly
        c.hide_render = True
    T = 4.0
    origins = {}
    for i, m in enumerate(MATS):
        ox = 1000.0 + 64.0 * i          # far from the compound, on the 4 m grid (world-aligned sets stay in phase)
        origins[m] = Vector((ox, -1000.0, 0.0))
        sq = [(0, 0), (12, 0), (12, 12), (0, 12)]
        if m == "M_DKG_SandEdge":
            yc = 6.0   # a crest on the swatch centre line, as the field piece
            quads = [([(0, 0), (11.5, 0), (11.5, 12), (0, 12)], "M_DKG_SandRaked", lambda x, y: ((x - 11.5) / T, (y - yc) / T)),
                     ([(11.5, 0), (12, 0), (12, 12), (11.5, 12)], m, lambda x, y: (-(y - yc) / T, (x - 11.5) / 0.5))]
        else:
            quads = [(sq, m, lambda x, y: (x / T, y / T))]
        mesh_obj(f"Swatch_{m}", quads, origins[m])
    w = bpy.data.worlds.new("Grey")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.18, 0.18, 0.18, 1)
    bg.inputs["Strength"].default_value = 1.0
    sc.world = w
    sd = bpy.data.lights.new("SheetSun", "SUN")
    sd.energy = 3.0
    sd.angle = math.radians(1.0)
    sun = bpy.data.objects.new("SheetSun", sd)
    # 40 deg up, travelling toward +Y-ish and -X: grazes ACROSS the rake lines (which run along X)
    sun.rotation_euler = Vector((-0.25, 0.70, -0.64)).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(sun)
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        sc.cycles.device = "GPU"
    except Exception as exc:  # noqa: BLE001
        print("GPU setup failed:", exc)
    sc.cycles.samples = int(arg("--samples", "32"))
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "None"
    sc.render.resolution_x = sc.render.resolution_y = PX
    OUT.mkdir(parents=True, exist_ok=True)
    for m in MATS:
        o = origins[m]
        cd = bpy.data.cameras.new(f"Flat_{m}")
        cd.type = "ORTHO"
        cd.ortho_scale = 12.0
        cam = bpy.data.objects.new(f"Flat_{m}", cd)
        cam.location = o + Vector((6.0, 6.0, 20.0))
        cam.rotation_euler = (0, 0, 0)
        sc.collection.objects.link(cam)
        sc.camera = cam
        sc.render.filepath = str(OUT / f"{m}_flat.png")
        bpy.ops.render.render(write_still=True)
        cd2 = bpy.data.cameras.new(f"Eye_{m}")
        cd2.lens = 35.0
        cd2.clip_end = 500
        cam2 = bpy.data.objects.new(f"Eye_{m}", cd2)
        # eye 1.7 m over the swatch, looking 2.4 m ahead (35 deg down); the edge swatch looks at the strip
        eye = o + (Vector((10.6, 3.6, 1.7)) if m == "M_DKG_SandEdge" else Vector((6.0, 3.0, 1.7)))
        tgt = o + (Vector((11.8, 5.6, 0.0)) if m == "M_DKG_SandEdge" else Vector((6.0, 5.4, 0.0)))
        cam2.location = eye
        cam2.rotation_euler = (tgt - eye).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(cam2)
        sc.camera = cam2
        sc.render.filepath = str(OUT / f"{m}_eye.png")
        bpy.ops.render.render(write_still=True)
        print("sheet", m, flush=True)


main()
