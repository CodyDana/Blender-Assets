import sys; sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/measure_sword_indep")
from ms_lib import *
for n in sys.argv[sys.argv.index('--')+1:]:
    savepng(D+"look_ours_"+n+".png", over(load(D+"ours_"+n+".png")))
