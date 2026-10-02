from pathlib import Path
src = Path("landscape/verify/v10_ue_alley_own.py").read_text(encoding="utf-8")
def sw(a, b, n=1):
    global src
    assert src.count(a) == n, (a, src.count(a))
    src = src.replace(a, b)
hdr = '''# HALL + ARMORY VERIFIER (independent; I did not build this): the landscape verifier's v10 alley script with MY OWN
# targets for the extended hall (derived from interface.json site + the FBX audit, not from the builder's ha_ue_alley_own),
# 6-value target boxes (x0, x1, y0, y1, feet z min, feet z max) so the hall's hidden side strips and the extension's
# wall cavities are targets below the wall plate, a NEW flood lattice offset (X -0.96 / Y 23.04 / z +0.07), the launch
# grid offset (X -0.93 / Y 24.07) and the region north to the moved wall. The interior (inside the armory walls) is LEGAL.
'''
src = hdr + src
import re
src = re.sub(r"^VD = Path\(.*$", lambda m: 'VD = Path(r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/dojo/build/hall_armory/verify/json")', src, count=1, flags=re.M)
old_t = src[src.index("TARGETS = {"):src.index("def in_target")]
new_t = '''Z9 = 99.0
TARGETS = {"alley_behind_extension": (14.88, 29.12, 45.12, 47.0, -1.0, Z9),
           "extension_rear_roof": (14.1, 29.9, 34.42, 45.9, 5.0, Z9),
           "hall_upper_rear_half": (12.15, 31.85, 29.15, 34.0, 5.45, Z9),
           "north_wall_top_and_beyond": (-1.5, 45.5, 47.02, 52.0, -1.0, Z9),
           "ext_rear_cavity": (15.12, 28.88, 44.32, 44.88, -1.0, 5.3)}
for sd, f in (("W", lambda b: b), ("E", mx)):
    TARGETS[f"rear_yard_{sd}"] = f((-0.95, 14.88, 36.0, 47.0, -1.0, Z9))
    TARGETS[f"strip_behind_hall_{sd}"] = f((10.45, 14.88, 34.12, 36.0, -1.0, Z9))
    TARGETS[f"pocket_{sd}"] = f((7.12, 10.45, 32.3, 36.0, -1.0, Z9))
    TARGETS[f"corridor_north_slope_{sd}"] = f((7.12, 10.38, 31.12, 32.3, 2.5, Z9))
    TARGETS[f"outbuilding_north_roof_{sd}"] = f((-0.95, 7.12, 31.82, 36.0, 3.0, Z9))
    TARGETS[f"hall_side_strip_{sd}"] = f((13.12, 15.68, 24.12, 34.0, -1.0, 5.3))     # hall-local x -8.88..-6.32
    TARGETS[f"ext_side_cavity_{sd}"] = f((15.12, 15.68, 34.0, 44.88, -1.0, 5.3))


'''
src = src.replace(old_t, new_t)
sw('''def in_target(x, y, zf):
    for k, (x0, x1, y0, y1, z0) in TARGETS.items():
        if x0 <= x <= x1 and y0 <= y <= y1 and zf >= z0:''', '''def in_target(x, y, zf):
    for k, (x0, x1, y0, y1, z0, z9) in TARGETS.items():
        if x0 <= x <= x1 and y0 <= y <= y1 and z0 <= zf <= z9:''')
sw("return (round(44.0 - b[1], 3), round(44.0 - b[0], 3)) + tuple(b[2:])", "return (round(44.0 - b[1], 3), round(44.0 - b[0], 3)) + tuple(b[2:])")
sw('''    y = 24.0
    while y <= 36.9 + 1e-6:
        x = -1.0''', '''    y = 24.07
    while y <= 46.0 + 1e-6:
        x = -0.93''')
sw('def flood(mode, r=30.0, x0=-0.93, x1=44.97, y0=23.07, y1=36.97, zb0=0.11, zb1=18.11, dx=0.1, dz=0.15):',
   'def flood(mode, r=30.0, x0=-0.96, x1=44.94, y0=23.04, y1=48.94, zb0=0.07, zb1=18.07, dx=0.1, dz=0.15):')
sw('rep["B_flood_br_r30"] = flood("br", 30.0, x0=3.07, x1=40.97, y0=28.07, y1=36.97, zb0=0.11, zb1=7.61)',
   'rep["B_flood_br_r30"] = flood("br", 30.0, x0=-0.86, x1=44.84, y0=28.14, y1=48.84, zb0=0.12, zb1=9.12, dx=0.2, dz=0.2)')
sw('"launch_north_of_31_8": sorted([list(p) for p in launch if p[1] > 31.8])[:200]',
   '"launch_north_of_34": len([p for p in launch if p[1] > 34.0])')
sw('rep = {"verifier": "independent r9"', 'rep = {"verifier": "independent hall+armory v11"')
sw('unreal.log(f"V8F_ALLEY_DONE', 'unreal.log(f"VHA_ALLEY_DONE')
Path("hall_armory/verify/v11_ue_alley.py").write_text(src, encoding="utf-8")
print("ok")
