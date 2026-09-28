import bpy, math, sys
out = sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
bpy.ops.import_scene.fbx(filepath="C:/Users/Cody/Desktop/Blender_Projects/Exports/BlackCloak/BlackCloak.fbx", use_anim=False)
# colour the two suspect layers
cols={"Cloak_LongDrape":(0.8,0.2,0.2,1),"Cloak_RearMantle_2":(0.2,0.4,0.9,1),"Cloak_RightWingReturn":(0.2,0.8,0.3,1),"Cloak_WrappedCowl":(0.9,0.8,0.2,1)}
for o in sc.objects:
    if o.type=="MESH": o.color=cols.get(o.name,(0.55,0.55,0.58,1))
cd=bpy.data.cameras.new("c"); cd.type="ORTHO"; cd.ortho_scale=1.3
cam=bpy.data.objects.new("c",cd); sc.collection.objects.link(cam); sc.camera=cam
cam.location=(0,6,1.25); cam.rotation_euler=(math.radians(90),0,math.radians(180))
sc.render.engine="BLENDER_WORKBENCH"; sc.display.shading.light="STUDIO"; sc.display.shading.color_type="OBJECT"; sc.display.shading.show_cavity=True
sc.world=bpy.data.worlds.new("w"); sc.render.resolution_x=1000; sc.render.resolution_y=1000
sc.render.filepath=out; bpy.ops.render.render(write_still=True); print("OK")
