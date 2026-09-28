"""fp_labdiff A_FIT B_FIT OUT.png: label renders of two fits; print which passes gained/lost front pixels; paint changed pixels."""
import sys, importlib.util
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import write_png
from props_lib import smokebomb_wind as W
def load(p):
    s = importlib.util.spec_from_file_location("f" + str(abs(hash(p))), p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
labs = []
for f in sys.argv[1:3]:
    wd = W.reference_winding(load(f))
    lab = W.render_labels(wd, "front", size=627)
    names = np.array(wd.names + ["bg"])
    labs.append(names[np.where(lab["pass_"] >= 0, lab["pass_"], len(wd.names))])
a, b = labs
ch = a != b
print("changed px", int(ch.sum()))
from collections import Counter
c = Counter(zip(a[ch], b[ch]))
for (x, y), n in c.most_common(25):
    print(f"{x:5s} -> {y:5s} {n}")
img = np.ones((627, 627, 3)) * 0.8
img[ch] = (1, 0, 0)
img[a == "bg"] = 1
write_png(sys.argv[3], img)
for p in sorted(set(b.ravel()) - {"bg"}):
    print(p, int((a == p).sum()), "->", int((b == p).sum()))
