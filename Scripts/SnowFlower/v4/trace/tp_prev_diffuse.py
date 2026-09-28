import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
import tp_render as R
WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
for m in bpy.data.materials:
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1); b.inputs["Metallic"].default_value = 0; b.inputs["Roughness"].default_value = 1
R.settings(16, (728, 680)); R.world_studio(); K = 0.687; zc = (105 - 304) * K
R.lights_sheet((0, 0, zc / 1000))
R.cam_front_ortho((505.5 - 506.0) * K, zc, 182 * K, (728, 680))
R.render(WORK + "/prev_diffuse_front.png")
R.cam_look("C34", (0.3 * math.sin(math.radians(45)), -0.3 * math.cos(math.radians(45)), zc / 1000 - 0.05), (0, 0, zc / 1000), lens=85)
R.render(WORK + "/prev_diffuse_34.png")
