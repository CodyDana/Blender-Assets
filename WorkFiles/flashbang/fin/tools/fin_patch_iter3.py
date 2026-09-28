"""Finalise patch, iteration 3: LOD1 ring / holes / cans closer to LOD0 (the LOD pop), LOD1 end face flattened."""
from pathlib import Path

S = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_spec.py")
s = S.read_text(encoding="utf-8")
a = "        LodQuality(8, 4, 1, 14, 1, 1, 48, 20, 16, 2, True, 6, 20, 6, 8, 6, 3, 5, True, (2500, 3600), 1, True),"
b = "        LodQuality(8, 4, 1, 18, 1, 1, 48, 20, 16, 2, True, 8, 24, 8, 8, 6, 3, 5, True, (2500, 3800), 1, True),"
assert a in s
s = s.replace(a, b)
s = s.replace("    cap_end_detail: int = 2   # FINALISE: 2 the notched end face + foot cut-outs, 1 rim + groove + disc with the foot\n                              # cut-outs only, 0 a flat end face",
              "    cap_end_detail: int = 2   # FINALISE: 2 the notched end face + foot cut-outs, 1 a flat end face with the foot\n                              # cut-outs (seen from the side), 0 a flat end face")
S.write_text(s, encoding="utf-8")

G = Path(r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/props/props_lib/flashbang_geom.py")
s = G.read_text(encoding="utf-8")
a = '''    if q.cap_end_detail == 1:
        # LOD1: the disc, groove and rim without the inner tabs; the foot cut-outs stay (seen from the side)
        inner = [b for b in bands if b[1] <= bands[-3][0] + 1e-9]
        r_g = bands[-3][0]
        bands = [(0.0, r_g - (bands[3][1] - bands[3][0]), bands[0][2], bands[0][2]),
                 (r_g - (bands[3][1] - bands[3][0]), r_g, bands[3][2], bands[3][2])] + bands[-2:]
        if not foot_notch:
            bands[-1] = (bands[-1][0], bands[-1][1], bands[-1][2], bands[-1][2])'''
b = '''    if q.cap_end_detail == 1:
        # LOD1 (>= 0.9 m, the end face is seen only from below): a flat end face; the foot cut-outs stay (the side)
        r_o = bands[-1][0]
        bands = [(0.0, r_o, 0.0, 0.0), bands[-1] if foot_notch else (bands[-1][0], bands[-1][1], 0.0, 0.0)]'''
assert a in s
s = s.replace(a, b)
G.write_text(s, encoding="utf-8")
print("iter3 patched")
