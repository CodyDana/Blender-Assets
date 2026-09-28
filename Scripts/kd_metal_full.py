import bpy

ZONES={"Kamish_Art_L":(0.875,0.905),"Kamish_Art_R":(0.80,0.68)}
for mn,(y0,y1) in ZONES.items():
    m=bpy.data.materials[mn]; nt=m.node_tree
    b=[n for n in nt.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled'][0]
    tex=[n for n in nt.nodes if n.bl_idname=='ShaderNodeTexImage'][0]
    # skip if already applied
    if any(n.bl_idname=='ShaderNodeHueSaturation' for n in nt.nodes):
        print(mn,"already metal"); continue
    # blade-zone MapRange: fed by a SeparateXYZ.Y
    zf=None
    for l in nt.links:
        if l.from_socket.name=="Y" and l.from_node.bl_idname=='ShaderNodeSeparateXYZ' and l.to_node.bl_idname=='ShaderNodeMapRange':
            zf=l.to_node
    zf.inputs["From Min"].default_value=y0
    zf.inputs["From Max"].default_value=y1
    # deep crimson metallic recolor
    hsv=nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value=1.35
    hsv.inputs["Value"].default_value=0.55
    nt.links.new(tex.outputs["Color"], hsv.inputs["Color"])
    fix=nt.nodes.new("ShaderNodeMix"); fix.data_type='RGBA'
    fix.inputs[0].default_value=0.60
    fix.inputs[7].default_value=(0.28,0.022,0.032,1.0)
    nt.links.new(hsv.outputs["Color"], fix.inputs[6])
    mixc=nt.nodes.new("ShaderNodeMix"); mixc.data_type='RGBA'
    nt.links.new(tex.outputs["Color"], mixc.inputs[6])
    nt.links.new(fix.outputs[2], mixc.inputs[7])
    nt.links.new(zf.outputs["Result"], mixc.inputs[0])
    for l in list(nt.links):
        if l.to_node==b and l.to_socket.name=="Base Color":
            nt.links.remove(l)
    nt.links.new(mixc.outputs[2], b.inputs["Base Color"])
    met=nt.nodes.new("ShaderNodeMath"); met.operation='MULTIPLY'; met.inputs[1].default_value=0.92
    nt.links.new(zf.outputs["Result"], met.inputs[0])
    nt.links.new(met.outputs[0], b.inputs["Metallic"])
    print(mn,"metal applied")
bpy.ops.wm.save_mainfile()
print("METAL_FULL_OK")
