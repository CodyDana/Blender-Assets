import sys, numpy as np
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/flashbang/metrology")
from fb_lib import *
ref = load_srgb(); L = lum(ref)
def prof(label, arr): print(label, ' '.join(f"{v:.2f}" for v in arr))
prof("v1 ring bottom x240..246 y270..295", L[270:296, 240:247].mean(1))
prof("v1 ring left y185..195 x150..172", L[185:196, 150:173].mean(0))
prof("v1 ring right y185..195 x315..335", L[185:196, 315:336].mean(0))
prof("v1 ring top x200..206 y88..105", L[88:106, 200:207].mean(1))
prof("v2 ring y150..160 x560..590", L[150:161, 560:591].mean(0))
prof("v3 ring y160..170 x905..932", L[160:171, 905:933].mean(0))
prof("v4 ring y160..170 x972..995", L[160:171, 972:996].mean(0))
