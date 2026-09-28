import sys, types, numpy as np
sys.modules['bpy']=types.ModuleType('bpy')
src = open(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/blackhat_look.py", encoding="utf8").read()
i0 = src.index("def support_hull("); i1 = src.index("def obb_points(")
ns = {"np": np, "math": __import__("math")}
exec(src[i0:i1], ns)
P = np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/blackhat/UnrealVerify_indep_v1/truth_SM_BlackHat_LOD0_verts_cm.npy") * 10
body = P[(P[:, 2] > -0.5) & (np.hypot(P[:, 0], P[:, 1]) < 302)]
for base, cap in ((13, 50), (16, 50), (12, 50), (16, 64), (18, 64), (20, 80)):
    V, r = ns["support_hull"](body, base_azimuths=base, max_vertices=cap)
    print(base, cap, r["vertices"], r["gap_to_points_convex_hull_mm"], r["beyond_widest_radius_mm"])
