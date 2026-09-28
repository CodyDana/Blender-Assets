import numpy as np, math
P = "C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/shuriken/photo_study/"
raw = np.load(P + "synthesis/juji_profile_raw.npy")
g, h8, h6 = raw[:, 0], raw[:, 1], raw[:, 2]
Rj = 48.5
for i in list(range(80, 260, 10)) + list(range(850, 1001, 10)):
    print("u/R %.3f u %.2f  h8 %.4f (mm %.3f)  h-u %.4f" % (g[i], g[i]*Rj, h8[i], h8[i]*Rj, h8[i]-g[i]))
