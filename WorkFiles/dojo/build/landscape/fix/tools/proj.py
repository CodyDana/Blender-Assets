"""Project level-frame points (m) into a showcase camera (layout_showcase.json): proj(cam, pts, wh) -> pixels."""
import json, math
import numpy as np
L = json.load(open(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build\showcase\layout_showcase.json"))
CAMS = {c["name"]: c for c in L["cameras"]}

def proj(name, pts, wh=None):
    c = CAMS[name]
    o = np.array(c["loc"], float); f = np.array(c["look_at"], float) - o; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    W, H = wh or c["out_wh"]
    k = (W / 2) / math.tan(math.radians(c["hfov_deg"]) / 2)
    P = np.atleast_2d(np.asarray(pts, float)) - o
    z = P @ f
    return np.c_[W / 2 + k * (P @ r) / z, H / 2 - k * (P @ u) / z, z]

if __name__ == "__main__":
    import sys
    print(proj(sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3]) if len(sys.argv) > 3 else None))
