"""Quick HIGH-POLY preview (plain materials) - front at the reference crop + one 3/4.  Dev only (not a deliverable).
    blender -b work/tp_high.blend --factory-startup --python tp_preview.py -- <tag>"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import tp_render as R
WORK = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work"
tag = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "p"
def principled(m, base, metal, rough):
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
principled(bpy.data.materials["TP_Silver"], (0.62, 0.62, 0.63), 1.0, 0.32)
principled(bpy.data.materials["TP_Enamel"], (0.012, 0.016, 0.024), 0.0, 0.2)
principled(bpy.data.materials["TP_Pearl"], (0.75, 0.75, 0.78), 0.0, 0.3)
principled(bpy.data.materials["TP_Lacquer"], (0.02, 0.024, 0.032), 0.0, 0.3)
R.settings(24, (728, 680))
R.world_studio()
K = 0.687
zc = (105 - 304) * K
R.lights_sheet((0, 0, zc / 1000))
R.cam_front_ortho((505.5 - 506.0) * K, zc, 182 * K, (728, 680))
R.render(WORK + f"/prev_{tag}_front.png")
import math
R.cam_look("C34", (0.16 * math.sin(math.radians(40)), -0.16 * math.cos(math.radians(40)), zc / 1000 - 0.04), (0, 0, zc / 1000), lens=85)
bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 700, 700
R.render(WORK + f"/prev_{tag}_34.png")
# material-ID pass (flat emission) for checking the class layout
def emis(m, col):
    nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*col, 1); nt.links.new(e.outputs[0], o.inputs["Surface"])
emis(bpy.data.materials["TP_Silver"], (0.9, 0.3, 0.2)); emis(bpy.data.materials["TP_Enamel"], (0.1, 0.3, 1.0))
emis(bpy.data.materials["TP_Pearl"], (1, 1, 1)); emis(bpy.data.materials["TP_Lacquer"], (0.1, 0.8, 0.2))
bpy.context.scene.cycles.samples = 4
bpy.context.scene.view_settings.exposure = 0
R.cam_front_ortho((505.5 - 506.0) * K, zc, 182 * K, (728, 680))
R.render(WORK + f"/prev_{tag}_id.png")
