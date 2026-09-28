import bpy

scene=bpy.context.scene
m=bpy.data.materials["Kamish_Art"]; nt=m.node_tree
b=[n for n in nt.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled'][0]
tex=[n for n in nt.nodes if n.bl_idname=='ShaderNodeTexImage'][0]
tc=[n for n in nt.nodes if n.bl_idname=='ShaderNodeTexCoord'][0]

for l in list(nt.links):
    if l.to_node==b and l.to_socket.name in ("Emission Strength","Emission Color","Roughness","Normal"):
        nt.links.remove(l)
b.inputs["Emission Strength"].default_value=0.0
b.inputs["Metallic"].default_value=0.0
for k in ("Specular IOR Level","Specular"):
    if k in b.inputs:
        b.inputs[k].default_value=0.5
        break

def M(op,v=None):
    n=nt.nodes.new("ShaderNodeMath"); n.operation=op
    if v is not None: n.inputs[1].default_value=v
    return n

sc=nt.nodes.new("ShaderNodeSeparateColor"); nt.links.new(tex.outputs["Color"], sc.inputs["Color"])
red=M('SUBTRACT'); nt.links.new(sc.outputs["Red"], red.inputs[0]); nt.links.new(sc.outputs["Green"], red.inputs[1])
redc=M('MULTIPLY',2.2); nt.links.new(red.outputs[0], redc.inputs[0])
redm=M('MINIMUM',1.0); nt.links.new(redc.outputs[0], redm.inputs[0])
bw=nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(tex.outputs["Color"], bw.inputs["Color"])
darkmr=nt.nodes.new("ShaderNodeMapRange")
darkmr.inputs["From Min"].default_value=0.02; darkmr.inputs["From Max"].default_value=0.22
darkmr.inputs["To Min"].default_value=1.0;  darkmr.inputs["To Max"].default_value=0.0
nt.links.new(bw.outputs["Val"], darkmr.inputs["Value"])
noi=nt.nodes.new("ShaderNodeTexNoise"); noi.inputs["Scale"].default_value=70.0; noi.inputs["Detail"].default_value=5.0
nt.links.new(tc.outputs["Object"], noi.inputs["Vector"])
nsub=M('SUBTRACT',0.5); nt.links.new(noi.outputs["Fac"], nsub.inputs[0])
nmul=M('MULTIPLY',0.16); nt.links.new(nsub.outputs[0], nmul.inputs[0])
r1=M('MULTIPLY',0.30); nt.links.new(redm.outputs[0], r1.inputs[0])
r2=M('MULTIPLY',0.28); nt.links.new(darkmr.outputs["Result"], r2.inputs[0])
rb=M('SUBTRACT'); rb.inputs[0].default_value=0.52; nt.links.new(r1.outputs[0], rb.inputs[1])
rb2=M('SUBTRACT'); nt.links.new(rb.outputs[0], rb2.inputs[0]); nt.links.new(r2.outputs[0], rb2.inputs[1])
rb3=M('ADD'); nt.links.new(rb2.outputs[0], rb3.inputs[0]); nt.links.new(nmul.outputs[0], rb3.inputs[1])
rcl=nt.nodes.new("ShaderNodeClamp"); rcl.inputs["Min"].default_value=0.08; rcl.inputs["Max"].default_value=0.8
nt.links.new(rb3.outputs[0], rcl.inputs["Value"])
nt.links.new(rcl.outputs["Result"], b.inputs["Roughness"])
c1=M('MULTIPLY',0.45); nt.links.new(redm.outputs[0], c1.inputs[0])
c2=M('MULTIPLY',0.50); nt.links.new(darkmr.outputs["Result"], c2.inputs[0])
cs=M('ADD'); nt.links.new(c1.outputs[0], cs.inputs[0]); nt.links.new(c2.outputs[0], cs.inputs[1])
if "Coat Weight" in b.inputs:
    nt.links.new(cs.outputs[0], b.inputs["Coat Weight"])
    if "Coat Roughness" in b.inputs: b.inputs["Coat Roughness"].default_value=0.12
s1=M('MULTIPLY',0.12); nt.links.new(redm.outputs[0], s1.inputs[0])
if "Subsurface Weight" in b.inputs:
    nt.links.new(s1.outputs[0], b.inputs["Subsurface Weight"])
    b.inputs["Subsurface Radius"].default_value=(0.004,0.0012,0.001)
    if "Subsurface Scale" in b.inputs: b.inputs["Subsurface Scale"].default_value=0.015
nb=nt.nodes.new("ShaderNodeBump"); nb.inputs["Strength"].default_value=0.06; nb.inputs["Distance"].default_value=0.0003
nt.links.new(noi.outputs["Fac"], nb.inputs["Height"])
tb=nt.nodes.new("ShaderNodeBump"); tb.inputs["Strength"].default_value=0.30; tb.inputs["Distance"].default_value=0.0007
nt.links.new(bw.outputs["Val"], tb.inputs["Height"])
nt.links.new(nb.outputs["Normal"], tb.inputs["Normal"])
nt.links.new(tb.outputs["Normal"], b.inputs["Normal"])

k=bpy.data.objects.get("KKey"); k.data.energy=300; k.data.size=1.1
for l in bpy.data.lights:
    if l.type=='SUN': l.energy=1.4
scene.world.node_tree.nodes.get("Background").inputs["Strength"].default_value=0.45
scene.render.filepath=r"C:\Users\Cody\Desktop\Blender_Projects\kd_real_"
bpy.ops.wm.save_mainfile()
print("HYPERREAL_OK")
