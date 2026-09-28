import bpy

for mn in ("Kamish_Art_L","Kamish_Art_R"):
    m=bpy.data.materials[mn]; nt=m.node_tree
    b=[n for n in nt.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled'][0]
    tex=[n for n in nt.nodes if n.bl_idname=='ShaderNodeTexImage'][0]
    sepxyz=[n for n in nt.nodes if n.bl_idname=='ShaderNodeSeparateXYZ'][-1]
    # the blade-zone MapRange is the one fed by SeparateXYZ.Y
    zf=None
    for l in nt.links:
        if l.from_node==sepxyz and l.from_socket.name=="Y" and l.to_node.bl_idname=='ShaderNodeMapRange':
            zf=l.to_node; break
    # deep metallic crimson recolor inside the blade zone
    hsv=nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value=1.35
    hsv.inputs["Value"].default_value=0.55
    nt.links.new(tex.outputs["Color"], hsv.inputs["Color"])
    mixc=nt.nodes.new("ShaderNodeMix"); mixc.data_type='RGBA'
    nt.links.new(tex.outputs["Color"], mixc.inputs[6])
    nt.links.new(hsv.outputs["Color"], mixc.inputs[7])
    nt.links.new(zf.outputs["Result"], mixc.inputs[0])
    # replace base color link
    for l in list(nt.links):
        if l.to_node==b and l.to_socket.name=="Base Color":
            nt.links.remove(l)
    nt.links.new(mixc.outputs[2], b.inputs["Base Color"])
    # metallic in the blade zone
    met=nt.nodes.new("ShaderNodeMath"); met.operation='MULTIPLY'; met.inputs[1].default_value=0.92
    nt.links.new(zf.outputs["Result"], met.inputs[0])
    nt.links.new(met.outputs[0], b.inputs["Metallic"])
bpy.ops.wm.save_mainfile()
print("METAL_OK")
