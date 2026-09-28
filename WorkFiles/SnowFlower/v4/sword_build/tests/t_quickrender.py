import sys, bpy, math
from mathutils import Vector, Euler
argv=sys.argv[sys.argv.index('--')+1:]
out, cx, cz, scale, w, h = argv[0], float(argv[1]), float(argv[2]), float(argv[3]), int(argv[4]), int(argv[5])
view = argv[6] if len(argv)>6 else 'front'
sc=bpy.context.scene
sc.render.engine='BLENDER_WORKBENCH'
sc.display.shading.light='STUDIO'; sc.display.shading.color_type='OBJECT' if False else 'MATERIAL'
sc.display.shading.show_cavity=True
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
cam.data.type='ORTHO'; cam.data.ortho_scale=scale; cam.data.clip_start=0.001; cam.data.clip_end=10
if view=='front':
    cam.location=(cx,-2,cz); cam.rotation_euler=Euler((math.pi/2,0,0)); cam.rotation_euler.rotate_axis('Z',math.pi)
elif view=='side':
    cam.location=(2,0,cz); cam.rotation_euler=Euler((math.pi/2,0,math.pi/2)); cam.rotation_euler.rotate_axis('Z',math.pi)
    cam.location.y=cx
sc.render.resolution_x=w; sc.render.resolution_y=h
sc.render.filepath=out
bpy.ops.render.render(write_still=True)
