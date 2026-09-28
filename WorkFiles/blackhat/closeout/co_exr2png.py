import bpy, sys
a = sys.argv[sys.argv.index("--") + 1:]
im = bpy.data.images.load(a[0]); sc = bpy.context.scene; sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
im.save_render(a[1], scene=sc)
