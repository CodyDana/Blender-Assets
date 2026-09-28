import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import bpy, numpy as np, sv2_imgmetrics as M
p = "C:/Users/Cody/Desktop/Blender_Projects/Exports/Garments/BlackCloak_MH_v2/Textures/T_BlackCloakV2_Fray_BCA.png"
img = bpy.data.images.load(p); img.colorspace_settings.name = "Non-Color"; w, h = img.size
a = np.empty(w*h*4, np.float32); img.pixels.foreach_get(a); a = a.reshape(h, w, 4)[::-1]
rgb = M.s2l(a[..., :3]) * 3.0; al = a[..., 3:4]
comp = M.l2s(np.clip(rgb*al + (1-al)*np.array([0.55, 0.62, 0.7]), 0, 1))*255
M.save("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_MH_v2/surface/crops/sv2_fray_preview_x2crop.png", np.repeat(np.repeat(comp[:, :640], 2, 0), 2, 1))
print("ok")
