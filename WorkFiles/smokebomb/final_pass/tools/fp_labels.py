"""fp_labels FIT.py OUT.png [size]: front label render of a fit module, beside the original and the reference."""
import sys, importlib.util
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/rewind/wind/tools")
import numpy as np
from wd_png import write_png, read_png
from props_lib import smokebomb_wind as W
def load(p):
    s = importlib.util.spec_from_file_location("f" + str(abs(hash(p))), p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
size = int(sys.argv[3]) if len(sys.argv) > 3 else 627
rng = np.random.default_rng(7); pal = rng.uniform(0.2, 1.0, (40, 3)); pal[0] = (1.0, 1.0, 0.3)
def img(fitpath):
    wd = W.reference_winding(load(fitpath))
    lab = W.render_labels(wd, "front", size=size)
    pas = lab["pass_"]; v = lab["v"]
    out = np.ones((size, size, 3))
    has = pas >= 0
    out[has] = pal[pas[has]] * (0.75 + 0.25 * np.nan_to_num(1 - np.abs(v[has])))[:, None]
    e = np.zeros(pas.shape, bool)
    s = lab["sample"]
    far = lambda a, b: np.abs(a - b) > 30
    e[:, 1:] |= far(s[:, 1:], s[:, :-1]); e[1:] |= far(s[1:], s[:-1])
    out[e & has] = 0
    return out, (pas == 0).sum()
a, ca = img(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/smokebomb/final_pass/orig_start/props_lib/smokebomb_wind_fit.py")
b, cb = img(sys.argv[1])
ref = read_png(r"C:/Users/Cody/Desktop/Blender_Projects/References/SmokeBomb/smokebomb.png")[..., :3] / 255.0
ref = np.clip(ref[::1254 // size, ::1254 // size][:size, :size] * 2, 0, 1)
write_png(sys.argv[2], np.concatenate([ref, a, b], 1))
print("core px orig", ca, "new", cb)
