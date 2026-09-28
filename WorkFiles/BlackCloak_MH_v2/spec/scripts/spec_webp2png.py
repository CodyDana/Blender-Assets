"""Convert Jin_Cloak.webp to PNG copies (full + half size) in spec/out for viewing/measuring. Reads the reference only."""
import bpy, sys, os
src = r"C:/Users/Cody/Desktop/Blender_Projects/References/BlackCloak/Jin_Cloak.webp"
out = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/spec/out"
im = bpy.data.images.load(src)
print("SIZE", im.size[:], im.channels, im.colorspace_settings.name)
sc = bpy.context.scene
sc.render.image_settings.file_format = "PNG"
im.save_render(os.path.join(out, "spec_jin_full.png"), scene=sc)
im2 = im.copy(); im2.scale(im.size[0]//3, im.size[1]//3)
im2.save_render(os.path.join(out, "spec_jin_third.png"), scene=sc)
