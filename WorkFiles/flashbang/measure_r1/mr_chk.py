import numpy as np
d=np.load(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/measure_r1/mr_sweep.npz")
a=d["-90"]; print(a.shape, a[...,3].mean(), a[...,3].max(), np.argwhere(a[...,3]>128).min(0), np.argwhere(a[...,3]>128).max(0))
m=a[...,3]>128; print(a[m][:,:3].mean(0))
