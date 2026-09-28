import numpy as np, math, json
P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
N = json.load(open(P + "synthesis/synthesis_numbers.json"))["juji"]
cont = np.load(P + "juji/contour/contour_refined.npy").astype(float)
cen = np.array([694.10, 651.11]); sc = 662.45 / N["model_mm_per_photo_R"]
q = cont - cen; q[:, 1] = -q[:, 1]
a = math.radians(-1.70); c, s = math.cos(a), math.sin(a)
m = np.stack([c * q[:, 0] - s * q[:, 1], s * q[:, 0] + c * q[:, 1]], 1) / sc
r = np.hypot(m[:, 0], m[:, 1]); th = np.degrees(np.arctan2(m[:, 1], m[:, 0])) % 360
for d in (45, 135, 225, 315):
    sel = np.abs(((th - d + 180) % 360) - 180) < 20
    print("crotch %3d deg: photo nearest %.2f mm (model 7.57)" % (d, r[sel].min()))
for d in (0, 90, 180, 270):
    sel = np.abs(((th - d + 180) % 360) - 180) < 3
    print("tip %3d deg: photo physical tip r %.2f mm (model apex 48.50)" % (d, r[sel].max()))
