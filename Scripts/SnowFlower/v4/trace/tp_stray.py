import bpy, numpy as np
o = bpy.data.objects["TP_Throat_HIGH"]; me = o.data
V = np.zeros(len(me.vertices) * 3); me.vertices.foreach_get("co", V); V = V.reshape(-1, 3) * 1000
print("bbox mm", V.min(0).round(1), V.max(0).round(1))
sel = (V[:, 0] < -52) | (V[:, 0] > 52) | (V[:, 1] < -45) | (V[:, 1] > 45)
print("stray verts", sel.sum(), V[sel][:10].round(1))
