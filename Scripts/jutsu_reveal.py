import bpy, math
from mathutils import Vector

scene=bpy.context.scene

# ---------- radial reveal on the ink material ----------
m=bpy.data.materials["Jutsu_Ink"]; nt=m.node_tree
for n in list(nt.nodes):
    if n.bl_idname in ('ShaderNodeMixShader','ShaderNodeBsdfTransparent','ShaderNodeValue',
                       'ShaderNodeTexCoord','ShaderNodeVectorMath','ShaderNodeMath','ShaderNodeMapRange'):
        nt.nodes.remove(n)
out=[n for n in nt.nodes if n.bl_idname=='ShaderNodeOutputMaterial'][0]
b=[n for n in nt.nodes if n.bl_idname=='ShaderNodeBsdfPrincipled'][0]
tc=nt.nodes.new("ShaderNodeTexCoord")
ln=nt.nodes.new("ShaderNodeVectorMath"); ln.operation='LENGTH'
nt.links.new(tc.outputs["Object"], ln.inputs[0])
front=nt.nodes.new("ShaderNodeValue"); front.name="Front"; front.label="Front"
# soft eased leading edge: alpha ramps 0->1 across a 0.22-wide smoothstep band behind the front
W=0.22
fsub=nt.nodes.new("ShaderNodeMath"); fsub.operation='SUBTRACT'; fsub.inputs[1].default_value=W
nt.links.new(front.outputs[0], fsub.inputs[0])
mr=nt.nodes.new("ShaderNodeMapRange")
mr.interpolation_type='SMOOTHSTEP'; mr.clamp=True
mr.inputs["To Min"].default_value=1.0; mr.inputs["To Max"].default_value=0.0
nt.links.new(ln.outputs["Value"], mr.inputs["Value"])
nt.links.new(fsub.outputs[0], mr.inputs["From Min"])
nt.links.new(front.outputs[0], mr.inputs["From Max"])
tr=nt.nodes.new("ShaderNodeBsdfTransparent")
mx=nt.nodes.new("ShaderNodeMixShader")
nt.links.new(mr.outputs["Result"], mx.inputs["Fac"])
nt.links.new(tr.outputs["BSDF"], mx.inputs[1])   # fac 0 -> hidden
nt.links.new(b.outputs["BSDF"], mx.inputs[2])    # fac 1 -> ink
for l in list(nt.links):
    if l.to_node==out and l.to_socket.name=="Surface": nt.links.remove(l)
nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])

# keyframe the wavefront: touch pause -> fast sweep -> hold complete
KEYS=[(1,0.0),(6,0.0),(14,0.35),(60,2.35),(78,2.35)]
for f,v in KEYS:
    front.outputs[0].default_value=v
    front.outputs[0].keyframe_insert("default_value", frame=f)
act=nt.animation_data.action
for layer in act.layers:
    for strip in layer.strips:
        for cb in strip.channelbags:
            for fc in cb.fcurves:
                for kp in fc.keyframe_points: kp.interpolation='BEZIER'

# ---------- animation render settings ----------
scene.frame_start=1; scene.frame_end=78
scene.render.fps=24
cam=bpy.data.objects["Cam"]
cam.data.lens=40
cam.location=(0.0,-3.0,2.35)
d=Vector((0,0.1,0))-Vector(cam.location)
cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=900; scene.render.resolution_y=600
scene.cycles.samples=48
scene.render.image_settings.media_type='IMAGE'
scene.render.image_settings.file_format='PNG'
scene.render.filepath=r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\jutsu_frames\f"
import os
os.makedirs(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\jutsu_frames", exist_ok=True)
bpy.ops.wm.save_mainfile()
print("REVEAL_RIGGED")
