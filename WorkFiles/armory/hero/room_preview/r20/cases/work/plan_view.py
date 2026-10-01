"""r20 cases: a top-down plan view of the test copy (orthographic, cut at +2.90: the camera's near clip hides the
ceiling, the upper walls and the roof). Workbench, then annotated by plan_annotate.py.
Run: blender -b --factory-startup <dir>/ArmoryKit_preview.blend --python plan_view.py -- <out.png>"""
import sys
import bpy

out = sys.argv[sys.argv.index("--") + 1]
sc = bpy.context.scene
X0, X1, Y0, Y1, PPM = -0.5, 12.5, -1.0, 20.5, 80
cd = bpy.data.cameras.new("Plan")
cd.type = "ORTHO"
cd.ortho_scale = max(X1 - X0, Y1 - Y0)
cd.clip_start, cd.clip_end = 0.01, 20.0
co = bpy.data.objects.new("Plan", cd)
sc.collection.objects.link(co)
co.location = ((X0 + X1) / 2, (Y0 + Y1) / 2, 2.90)
co.rotation_euler = (0.0, 0.0, 0.0)
sc.camera = co
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading
sh.light = "STUDIO"
sh.color_type = "TEXTURE"
sh.show_shadows = False
sh.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = int((X1 - X0) * PPM), int((Y1 - Y0) * PPM)
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "Standard"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("rendered", out)
