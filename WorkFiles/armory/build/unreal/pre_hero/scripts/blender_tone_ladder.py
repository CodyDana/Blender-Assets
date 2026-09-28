"""Blender half of the tone-ladder calibration (the Unreal half is ak_capture.py with AK_LADDER=1).

13 emission quads of radiance r_k = 0.18 * 2^k (k = -6..6), rendered with the review colour management of
render_armory.py golden (AgX, Medium High Contrast, exposure +0.8, no bloom), orthographic; the display value at each quad
centre is written out. Unreal gets emissive K * r_k (ak_common.K_LUX) through its own exposure + tonemapper, so the two
ladders give the display value both engines show for the SAME scene radiance: their horizontal offset (in stops) is the
exposure difference between the engines, independent of any light.
Run: blender -b --factory-startup --python blender_tone_ladder.py   -> WorkFiles/armory/build/unreal/tone_ladder_blender.json
"""
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ak_common as C  # noqa: E402

KS = list(range(-6, 7))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
for i, k in enumerate(KS):
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(i - 6, 0, 0))
    m = bpy.data.materials.new(f"e{k}")
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = 0.18 * 2.0 ** k
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    bpy.context.object.data.materials.append(m)
cd = bpy.data.cameras.new("c")
cd.type = "ORTHO"
cd.ortho_scale = 13.0
co = bpy.data.objects.new("c", cd)
sc.collection.objects.link(co)
co.location = (0, 0, 5)
sc.camera = co
w = bpy.data.worlds.new("w")
w.use_nodes = True
next(n for n in w.node_tree.nodes if n.type == "BACKGROUND").inputs["Strength"].default_value = 0.0
sc.world = w
sc.render.engine = "CYCLES"
sc.cycles.samples = 8
sc.cycles.use_denoising = False
sc.render.resolution_x, sc.render.resolution_y = 1300, 100
sc.view_settings.view_transform = "AgX"
sc.view_settings.look = "AgX - Medium High Contrast"
sc.view_settings.exposure = C.BLENDER_EXPOSURE_EV
p = C.OUT / "tone_ladder_blender.png"
sc.render.filepath = str(p)
bpy.ops.render.render(write_still=True)
img = bpy.data.images.load(str(p))
W, H = img.size
px = list(img.pixels[:])
rows = {}
for i, k in enumerate(KS):
    x, y = int((i + 0.5) * W / 13), H // 2
    j = (y * W + x) * 4
    r, g, b = px[j:j + 3]
    rows[str(k)] = {"radiance_blender": 0.18 * 2.0 ** k, "display": [round(r, 4), round(g, 4), round(b, 4)]}
C.write_json(C.OUT / "tone_ladder_blender.json", {"exposure_ev": C.BLENDER_EXPOSURE_EV, "look": sc.view_settings.look,
                                                  "ladder": rows})
print("LADDER", json.dumps(rows))
