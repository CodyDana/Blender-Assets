"""dev: LOW with its baked normal map but a flat grey diffuse material (checks the normal bake), front + 3/4."""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import tp_render as R
P = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot"
low = bpy.data.objects["SM_SnowFlower_Throat_TP_LOD0"]
nt = low.data.materials[0].node_tree
bs = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
for s in ("Base Color", "Roughness", "Metallic"):
    for l in list(bs.inputs[s].links): nt.links.remove(l)
bs.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1); bs.inputs["Roughness"].default_value = 1; bs.inputs["Metallic"].default_value = 0
for o in bpy.data.objects:
    if o.name.startswith("r1_"): o.hide_render = True
R.settings(24, (728, 680)); R.world_studio(); K = 0.687; zc = (105 - 304) * K
R.lights_sheet((0, 0, zc / 1000))
R.cam_front_ortho((505.5 - 506.0) * K, zc, 182 * K, (728, 680))
R.render(P + "/work/nm_front.png")
R.cam_look("C34", (0.3 * math.sin(math.radians(45)), -0.3 * math.cos(math.radians(45)), zc / 1000 - 0.05), (0, 0, zc / 1000), lens=85)
R.render(P + "/work/nm_34.png")
