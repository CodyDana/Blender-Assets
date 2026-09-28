import sys; sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts'); sys.path.insert(0, r'C:/Users/Cody/Desktop/Blender_Projects/Scripts/SnowFlower/v4')
import numpy as np
import sfv4_assemble as A
from pipeline.qa_check import uv_overlap_sat
for LV in (0,1,2):
  L=A.build_low(LV)
  for part,mb in L.items():
      by={}
      for f,uv,isl in zip(mb.faces,mb.fuv,mb.fisl):
          for k in range(1,len(f)-1):
              by.setdefault(isl,[]).append([uv[0],uv[k],uv[k+1]])
      for isl,tris in by.items():
          n=uv_overlap_sat(np.array(tris,float)*0.001)
          if n: print(LV,part,isl,n)
