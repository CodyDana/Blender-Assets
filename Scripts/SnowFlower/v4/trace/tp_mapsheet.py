import sys, os; sys.path.insert(0, os.path.dirname(__file__))
import numpy as np, tp_img
T = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/Textures"
ims = [tp_img.resize(tp_img.load(T + f"/T_Throat_TP_{k}.png")[..., :3], 0.25, kind='linear') for k in ("BC", "N", "AO", "Rough")]
tp_img.save(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/SnowFlower/v4/trace_pilot/work/maps_sheet.png", np.concatenate([np.concatenate(ims[:2], 1), np.concatenate(ims[2:], 1)], 0))
