import bpy, math
from mathutils import Vector

scene=bpy.context.scene
def R(z): return 0.06390-0.02343*z

# ---- A) segments: seams repositioned to measured z=0.358 / 0.774 ----
m_blade=bpy.data.materials["Ea_ArtBlade"]
for nm in ("Ea_Seg1","Ea_Seg2","Ea_Seg3"):
    o=bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o,do_unlink=True)
SEGS=[("Ea_Seg1",-0.030,0.352),("Ea_Seg2",0.364,0.768),("Ea_Seg3",0.780,1.130)]
for nm,z0,z1 in SEGS:
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=R(z0), radius2=R(z1),
                                    depth=(z1-z0), location=(0,0,(z0+z1)/2))
    o=bpy.context.active_object; o.name=nm
    o.data.materials.append(m_blade)
    for p in o.data.polygons: p.use_smooth=(len(p.vertices)==4)
    b=o.modifiers.new("chamfer",'BEVEL'); b.width=0.004; b.segments=2
    b.angle_limit=math.radians(60); b.limit_method='ANGLE'

# ---- B) knot: wrapped-ribbon style, measured size (x ±0.034, z 1.127..1.194) ----
for nm in ("Ea_KnotStrap0","Ea_KnotStrap1","Ea_KnotTab"):
    o=bpy.data.objects.get(nm)
    if o: bpy.data.objects.remove(o,do_unlink=True)
bronze=bpy.data.materials["Ea_Bronze"]
def band(name, z, rotY, sx, sz):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0,0,z))
    s=bpy.context.active_object; s.name=name
    s.scale=(sx,0.052,sz)
    s.rotation_euler=(0,math.radians(rotY),0)
    s.data.materials.append(bronze)
    bv=s.modifiers.new("b",'BEVEL'); bv.width=0.004; bv.segments=2
    return s
band("Ea_KnotStrap0", 1.143,  18, 0.068, 0.026)   # lower wrap band
band("Ea_KnotStrap1", 1.170, -24, 0.062, 0.024)   # upper twist band
# pointed fold tab poking up-left
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.016, radius2=0.0, depth=0.045,
                                location=(-0.022,0,1.192), rotation=(0,math.radians(-35),0))
tab=bpy.context.active_object; tab.name="Ea_KnotTab"
tab.data.materials.append(bronze)

# ---- C) fan: shift left to the measured axis offset ----
fan=bpy.data.objects.get("Ea_Fan")
if fan: fan.location.x=-0.017

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
print("EA_VERIFY_FIX_OK")
