"""crop the reference: pbt_crop.py x0 y0 x1 y1 scale out.png  (nearest-neighbour; bicubic if 'cubic' arg)"""
import os, sys
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props"); sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from props_lib import trace as T
import xt_io
x0, y0, x1, y1, s = map(int, sys.argv[1:6]); out = sys.argv[6]
src = T.read_source()
a = src.rgb[y0:y1, x0:x1]
xt_io.write(out, a, s)
