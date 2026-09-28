import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img
P = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot"
ref = np.load(P + "/work/ref_full.npy")[20:190, 415:597]
r4 = tp_img.resize(ref, 4, kind='linear')[..., :3]
ours = tp_img.load(P + "/renders/front_throat_x4.png")[..., :3]
tp_img.save(P + "/work/sbs_ctx.png", np.concatenate([r4, ours], 1))
