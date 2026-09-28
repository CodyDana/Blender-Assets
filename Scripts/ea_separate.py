import bpy, math
from mathutils import Vector

scene=bpy.context.scene

def newmat(name, base, metallic, rough):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes=True
    b=m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value=(*base,1)
    b.inputs["Metallic"].default_value=metallic
    b.inputs["Roughness"].default_value=rough
    return m

# ---- distinct part materials ----
m_handle=newmat("Ea_HandleGold",(0.42,0.30,0.10),1.0,0.45)   # darker, rougher grip gold
m_navy  =newmat("Ea_Navy",(0.030,0.045,0.16),0.15,0.35)      # dark navy ball (as in the art)
m_bronze=newmat("Ea_Bronze",(0.30,0.18,0.06),1.0,0.40)       # dark bronze knot
m_fit   =newmat("Ea_DarkFit",(0.05,0.045,0.05),0.85,0.35)    # near-black fittings/seams

def assign(name, mat):
    o=bpy.data.objects.get(name)
    if o:
        o.data.materials.clear(); o.data.materials.append(mat)
        return True
    return False
assign("Ea_Handle", m_handle)
assign("Ea_Ball", m_navy)
assign("Ea_KnotStrap0", m_bronze)
assign("Ea_KnotStrap1", m_bronze)
# fins + fan keep the painted Ea_ArtGold; FanCollar keeps procedural Ea_Gold

def link_scene(o):
    scene.collection.objects.link(o)

# ---- junction fittings so parts read as assembled ----
for nm in ("Ea_SocketRing","Ea_HandleCap","Ea_NeckRing"):
    o=bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o, do_unlink=True)

# 1) drill socket: dark ring where the blade enters the guard
bpy.ops.mesh.primitive_torus_add(major_radius=0.064, minor_radius=0.013, location=(0,0,0.19))
sr=bpy.context.active_object; sr.name="Ea_SocketRing"
sr.scale=(1.0,0.58,1.0)
for p in sr.data.polygons: p.use_smooth=True
sr.data.materials.append(m_fit)

# 2) washer cap where the handle meets the guard underside
bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.030, depth=0.022, location=(0,0,-0.262))
hc=bpy.context.active_object; hc.name="Ea_HandleCap"
for p in hc.data.polygons: p.use_smooth=(len(p.vertices)==4)
hc.data.materials.append(m_fit)

# 3) neck ring between handle end and the navy ball
bpy.ops.mesh.primitive_torus_add(major_radius=0.0165, minor_radius=0.0045, location=(0,0,-0.466))
nr=bpy.context.active_object; nr.name="Ea_NeckRing"
for p in nr.data.polygons: p.use_smooth=True
nr.data.materials.append(m_fit)

# ---- renders ----
cam=bpy.data.objects["Cam"]
old_loc=tuple(cam.location); old_rot=tuple(cam.rotation_euler)
scene.render.filepath=r"C:\Users\Cody\Desktop\Blender_Projects\Renders\ea_preview.png"
bpy.ops.render.render(write_still=True)
cam.location=(-3.55,0.0,0.30)
d=Vector((0,0,0.29))-Vector(cam.location); cam.rotation_euler=d.to_track_quat('-Z','Y').to_euler()
scene.render.filepath=r"C:\Users\Cody\Desktop\Blender_Projects\Renders\ea_side.png"
bpy.ops.render.render(write_still=True)
cam.location=old_loc; cam.rotation_euler=old_rot
bpy.ops.wm.save_mainfile()
print("EA_SEPARATED_OK")
