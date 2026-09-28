import math, numpy as np, runpy, sys
src=open("fanstudy_fold_xsec.py").read().split("res={}")[0]
src=src.replace("            if seg_x(segs[x][2],segs[x][3],segs[y][2],segs[y][3]): cross+=1",
 "            if seg_x(segs[x][2],segs[x][3],segs[y][2],segs[y][3]): cross+=1; HITS.append((segs[x][:2],segs[y][:2]))")
g={"HITS":[]}; exec(src,g)
for th in (15,10,6):
    g["HITS"].clear(); o=g["run"]("converging",87.0,math.radians(th)); print(th, o["cross"], g["HITS"][:8])
