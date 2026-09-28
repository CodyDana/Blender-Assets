import json, sys
from pathlib import Path
import numpy as np
P = Path("C:/Users/Cody/Desktop/Blender_Projects")
sys.path.insert(0, str(P / "Scripts/unreal/materials/maps")); sys.dont_write_bytecode = True
import np_twin as tw, recolour_common as rc
D = json.loads((P / "WorkFiles/materials/build/dump_f2.json").read_text())["instances"]
d = D["MI_SmokeBomb_Cloth"]; p = {**d["scalar"], **d["vector"]}
d16, _, _ = rc.png_read(P / "Exports/SmokeBomb/Textures/Recolour/T_SmokeBomb_Detail16.png")
vals, cnts = np.unique(d16, return_counts=True); cov = d16 != vals[np.argmax(cnts)]
dd = d16[cov] / 65535.0
for h in ["FFFFFF", "B01010", "808080"]:
    c = tw.s2l(np.array([int(h[i:i+2], 16) for i in (0, 2, 4)]) / 255.0)
    g, ce, info = tw.fabric_scalar(p, dd, c)
    m = ce.max() * g
    lev = rc.q8_srgb(m)
    print(h, info["C_hi"], "E", round(info["E"], 4), "Mean/E", round(p["Detail Mean"] / info["E"], 4),
          "frac>=0.85 %.4f >=0.9 %.4f >=0.94 %.4f >=0.949 %.5f" % ((m >= 0.85).mean(), (m >= 0.9).mean(), (m >= 0.94).mean(), (m >= 0.949).mean()),
          "levels>=0.85:", np.unique(lev[m >= 0.85]).size, "top levels share", {int(k): round(float((lev == k).mean()), 4) for k in range(240, 250)})
