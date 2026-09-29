import bpy
for m in bpy.data.materials:
    if m.name.startswith("M_AK_HCaseGlass"):
        for n in m.node_tree.nodes:
            if n.type == "MATH" and n.operation == "MULTIPLY":
                n.inputs[1].default_value = 0.0
bpy.ops.wm.save_as_mainfile(filepath=bpy.path.abspath("//../scratch/norefl/test.blend"))
