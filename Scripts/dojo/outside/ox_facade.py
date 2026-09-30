"""ROUND 6 (2026-09-29) OUTSIDE track: the far town's impostor facade atlas, baked from this track's OWN town houses
(SM_DKX_House_A..E in Assets/Dojo/DojoOutside.blend, read only: nothing is saved).

Why: the round-5 final judge called the far town 'flat-shaded untextured boxes'. The far houses stay about 20 triangles
each (one merged Nanite mesh), but their walls now carry an albedo picture of the real house fronts and sides
(lattice fronts, base boards, posts, lit shoji, the eave's fascia and its occlusion) and their roofs the kawara tile
texture (M_DKX_FarKawara). That is the classic impostor trade: the detail lives in the texture, not the mesh.

How (headless Blender, Cycles): each house piece alone in an empty scene, lit ONLY by a uniform white world of strength
1.0 (no sun), View transform Standard, exposure 0. A fully open Lambert face then renders at exactly its albedo, and faces
under the eave or behind a post are darker by their own occlusion (baked AO, which is what an impostor wants). An
orthographic camera frames one wall from the ground (z 0) to the wall top (the roof plane at the wall line).

Tiles (4 x 2, 512 px each; the atlas is assembled by ox_facade_atlas.py with PIL):
  row 0  A front (two-storey machiya)  B front (one-storey, hip)  C front (two-storey kura, gable front)  D front (row house)
  row 1  E front (large two-storey)     B side (earthen plaster)   A side (cream plaster)                 E side (two-storey)

Run: blender -b --factory-startup Assets/Dojo/DojoOutside.blend --python Scripts/dojo/outside/ox_facade.py
Out: WorkFiles/dojo/build/round6/build/facade_tiles/<tile>.png + tiles.json
"""
import json
import math
from pathlib import Path

import bpy

ROOT = Path(bpy.data.filepath).resolve().parents[2]
OUT = ROOT / "WorkFiles" / "dojo" / "build" / "round6" / "build" / "facade_tiles"
OUT.mkdir(parents=True, exist_ok=True)
TN = math.tan(math.radians(25.0))
# (tile, piece, view 'front' | 'side', width m, height m (the wall top))
HOUSES = {"A": (7.2, 9.0, 5.2), "B": (10.0, 7.0, 3.1), "C": (5.6, 7.0, 5.0), "D": (14.0, 6.2, 3.6), "E": (11.0, 8.4, 5.6)}
TILES = [("A_front", "A", "front"), ("B_front", "B", "front"), ("C_front", "C", "front"), ("D_front", "D", "front"),
         ("E_front", "E", "front"), ("B_side", "B", "side"), ("A_side", "A", "side"), ("E_side", "E", "side")]


def main():
    src = {o.name: o for o in bpy.data.objects if o.name.startswith("SM_DKX_House_") and o.type == "MESH"}
    sc = bpy.data.scenes.new("FacadeBake")
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 96
    sc.cycles.use_denoising = True
    try:
        sc.cycles.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for dv in prefs.devices:
            dv.use = True
    except Exception:  # noqa: BLE001
        pass
    sc.cycles.max_bounces = 4
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("White")
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    sc.world = w
    cam_d = bpy.data.cameras.new("FacadeCam")
    cam_d.type = "ORTHO"
    cam = bpy.data.objects.new("FacadeCam", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam
    coll = bpy.data.collections.new("Bake")
    sc.collection.children.link(coll)
    rep = {}
    for tile, key, view in TILES:
        W, D, eave = HOUSES[key]
        z_wall = eave + 0.60 * TN
        for o in list(coll.objects):
            coll.objects.unlink(o)
        o = src[f"SM_DKX_House_{key}"]
        inst = bpy.data.objects.new(f"bake_{tile}", o.data)
        coll.objects.link(inst)
        width = W if view == "front" else D
        h = z_wall
        # aspect of the wall; the render keeps square pixels and ox_facade_atlas resamples it into the 512 tile
        rx = 1024
        ry = max(64, int(round(rx * h / width)))
        sc.render.resolution_x, sc.render.resolution_y = rx, ry
        sc.render.resolution_percentage = 100
        cam_d.ortho_scale = max(width, h)
        if view == "front":          # the front faces -Y (house_walls: y0 = -D/2 is the front)
            cam.location = (0.0, -40.0, h / 2)
            cam.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        else:                        # the +X side wall, seen from +X
            cam.location = (40.0, 0.0, h / 2)
            cam.rotation_euler = (math.radians(90.0), 0.0, math.radians(90.0))
        cam_d.clip_start, cam_d.clip_end = 0.1, 100.0
        path = OUT / f"{tile}.png"
        sc.render.filepath = str(path)
        bpy.ops.render.render(write_still=True, scene=sc.name)
        rep[tile] = {"piece": o.name, "view": view, "width_m": width, "height_m": round(h, 4), "px": [rx, ry],
                     "png": str(path)}
        print("TILE", tile, rep[tile], flush=True)
    (OUT / "tiles.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("FACADE_DONE", len(rep), flush=True)


main()
