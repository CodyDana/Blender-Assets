import re
H = r'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero'
K = r'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\build_armory_kit.py'


def edit(p, pairs):
    s = open(p, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (p, old[:70])
        s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)


edit(H + r'\hero_rear_alcove.py', [
    ('''SC_W, SC_D, SC_H = 0.80, 0.55, 1.62
SC_CT, SC_HD = 0.75, 1.47          # counter top; underside of the head band''',
     '''# b8 (C1 against reference 2, 2x zoom: its corner niche is a tall recess, ~0.5 : 1, the b7 unit read square and low):
# 0.70 wide, the counter at +0.62 on the deck (+1.52 world, 10 cm under the rack tansu's top), the opening 0.56 x
# 1.00 m to +1.62 (+2.52), the 15 cm head band to +2.67. The sill ledge (X 0-0.335) stays 15.5 cm clear in plan.
SC_W, SC_D, SC_H = 0.70, 0.55, 1.77
SC_CT, SC_HD = 0.62, 1.62          # counter top; underside of the head band'''),
    ('''SC_X = (1.19, 11.61)               # instance x (rot 180: the piece spans x - 0.80 .. x): X 0.39-1.19 / 10.81-11.61''',
     '''SC_X = (1.19, 11.51)               # instance x (rot 180: the piece spans x - 0.70 .. x): X 0.49-1.19 / 10.81-11.51'''),
    ('''SC_SHELF = 1.09 ''', '''SC_SHELF = 1.12 '''),
])
edit(H + r'\tex_rear_alcove.py', [
    ('''    x0, x1, z0, z1 = 0.08, 0.72, 0.75, 1.46
    vx0, vx1, vz0, vz1 = 0.082, 0.718, 0.752, 1.438   # inside the frame, under the head line''',
     '''    # b8: the 0.54 x 0.99 m panel of the taller unit (x 0.08..0.62, z 0.62..1.61)
    x0, x1, z0, z1 = 0.08, 0.62, 0.62, 1.61
    vx0, vx1, vz0, vz1 = 0.082, 0.618, 0.622, 1.588   # inside the frame, under the head line'''),
    ('''    hot = np.exp(-(((x - 0.40) / 0.16) ** 2 + ((z - vz1) / 0.22) ** 2))''',
     '''    hot = np.exp(-(((x - 0.35) / 0.16) ** 2 + ((z - vz1) / 0.22) ** 2))'''),
])
edit(H + r'\hero_backwall.py', [
    ('''        riser(b, W, -0.02 + GO * k, 0.15 * k, 0.15 * (k + 1), not top, LD if top else GO * (k + 1) + 0.005,''',
     '''        # b8: the +0.75 tread in the polished deck finish ("landing": reference 2's pale lit band under the deck riser)
        riser(b, W, -0.02 + GO * k, 0.15 * k, 0.15 * (k + 1), "landing" if top else True,
              LD if top else GO * (k + 1) + 0.005,'''),
    ('''    riser(b, W, GO - 0.02, CZ - 0.001, LAND_Z, False, 2 * GO + 0.005)                    # recessed riser, tread +0.75''',
     '''    riser(b, W, GO - 0.02, CZ - 0.001, LAND_Z, "landing", 2 * GO + 0.005)                # recessed riser, pale tread +0.75'''),
])
edit(K, [
    ('''LANTERN_M, LANTERN_S = 0.80, 0.65''', '''LANTERN_M, LANTERN_S = 0.90, 0.65   # b8: M 0.80 -> 0.90 (b7 read ~30 x 40 px in C1; reference 2's ~28 x 56)'''),
    ('''            (3.50, 15.10, DECK_Z, LANTERN_M), (8.50, 15.10, DECK_Z, LANTERN_M),''',
     '''            (3.50, 15.10, DECK_Z, LANTERN_M), (8.50, 15.10, DECK_Z, LANTERN_M),   # b8: X 3.293-3.707 / 8.293-8.707'''),
])
print("ok")
