import bpy

base=bpy.data.materials["Kamish_Art"]

def make_zone_variant(name, ob_name, y_from, y_to):
    """y_from->y_to maps 0->1 blade factor (handles either direction)."""
    old=bpy.data.materials.get(name)
    m=base.copy(); m.name=name
    nt=m.node_tree
    b=[n for n in nt.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled'][0]
    tc=[n for n in nt.nodes if n.bl_idname=='ShaderNodeTexCoord'][0]
    # locate existing chain ends by following links into the Principled inputs
    def src(sock):
        for l in nt.links:
            if l.to_node==b and l.to_socket.name==sock: return l.from_node,l
        return None,None
    s1,l_sss=src("Subsurface Weight")
    rcl,l_r =src("Roughness")
    cs,l_c  =src("Coat Weight")
    redm=[l.from_node for l in nt.links if l.to_node==s1][0]
    # blade zone factor from local Y
    sep=nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs["Vector"])
    zf=nt.nodes.new("ShaderNodeMapRange")
    zf.inputs["From Min"].default_value=y_from; zf.inputs["From Max"].default_value=y_to
    zf.inputs["To Min"].default_value=0.0; zf.inputs["To Max"].default_value=1.0
    zf.clamp=True
    nt.links.new(sep.outputs["Y"], zf.inputs["Value"])
    def M(op,v=None):
        n=nt.nodes.new("ShaderNodeMath"); n.operation=op
        if v is not None: n.inputs[1].default_value=v
        return n
    br=M('MULTIPLY'); nt.links.new(zf.outputs["Result"], br.inputs[0]); nt.links.new(redm.outputs[0], br.inputs[1])
    inv=M('SUBTRACT'); inv.inputs[0].default_value=1.0
    invl=nt.links.new(zf.outputs["Result"], inv.inputs[1])
    # SSS off on blade
    nt.links.remove(l_sss)
    sm=M('MULTIPLY'); nt.links.new(s1.outputs[0], sm.inputs[0]); nt.links.new(inv.outputs[0], sm.inputs[1])
    nt.links.new(sm.outputs[0], b.inputs["Subsurface Weight"])
    # roughness -> hard 0.14 on blade red
    nt.links.remove(l_r)
    ibr=M('SUBTRACT'); ibr.inputs[0].default_value=1.0; nt.links.new(br.outputs[0], ibr.inputs[1])
    ra=M('MULTIPLY'); nt.links.new(rcl.outputs["Result"], ra.inputs[0]); nt.links.new(ibr.outputs[0], ra.inputs[1])
    rb=M('MULTIPLY',0.14); nt.links.new(br.outputs[0], rb.inputs[0])
    rs=M('ADD'); nt.links.new(ra.outputs[0], rs.inputs[0]); nt.links.new(rb.outputs[0], rs.inputs[1])
    nt.links.new(rs.outputs[0], b.inputs["Roughness"])
    # coat polish on blade red
    nt.links.remove(l_c)
    ca=M('MULTIPLY',0.38); nt.links.new(br.outputs[0], ca.inputs[0])
    cadd=M('ADD'); nt.links.new(cs.outputs[0], cadd.inputs[0]); nt.links.new(ca.outputs[0], cadd.inputs[1])
    ccl=nt.nodes.new("ShaderNodeClamp"); ccl.inputs["Min"].default_value=0.0; ccl.inputs["Max"].default_value=1.0
    nt.links.new(cadd.outputs[0], ccl.inputs["Value"])
    nt.links.new(ccl.outputs["Result"], b.inputs["Coat Weight"])
    # brighter spec on blade red
    sp=M('MULTIPLY',0.30); nt.links.new(br.outputs[0], sp.inputs[0])
    spa=M('ADD',0.25); nt.links.new(sp.outputs[0], spa.inputs[0])
    for k in ("Specular IOR Level","Specular"):
        if k in b.inputs:
            nt.links.new(spa.outputs[0], b.inputs[k]); break
    ob=bpy.data.objects[ob_name]
    ob.data.materials.clear(); ob.data.materials.append(m)
    if old: old.name=name+"_old"
    return m

make_zone_variant("Kamish_Art_L","Kamish_L", 0.86, 0.97)   # L blade above the guard
make_zone_variant("Kamish_Art_R","Kamish_R", 0.80, 0.68)   # R blade below the guard (inverted)
bpy.ops.wm.save_mainfile()
print("ZONES_OK")
