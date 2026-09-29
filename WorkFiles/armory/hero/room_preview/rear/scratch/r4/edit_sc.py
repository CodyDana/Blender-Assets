p = r'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero\hero_rear_alcove.py'
s = open(p, encoding='utf-8').read()


def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, (old[:70], s.count(old))
    s = s.replace(old, new)


rep('''SC_W, SC_D, SC_H = 0.70, 0.55, 1.96
SC_CT, SC_HD = 0.75, 1.76          # counter top; underside of the head band
SC_ST = 0.07                       # the side stiles
SC_BACK_Y = 15.945                 # the back face: 5 cm clear of the north wall's upper base rail (Y 15.95-16.0)
SC_X = (1.19, 11.51)               # instance x (rot 180: the piece spans x - 0.70 .. x): X 0.49-1.19 / 10.81-11.51''',
    '''# b4 (blind judge delta 4: from the entrance the b3 units read as tall, over-bright white slots, "lit doorways, not
# glazed cases"; reference 2's are modest dim niches): shorter and wider - 0.80 wide, the opening 0.66 x 0.72 m (+1.65
# to +2.37 on the deck; was 0.56 x 1.00), a 15 cm head band (top +2.52, now under the sill ledge's +2.549), a glazed
# front in a thin polished brass frame, the panel at under half the emission, no LED edge lines down the sides. The
# east unit is the mirror of the west (b3 had it 10 cm further in): X 0.39-1.19 / 10.81-11.61
SC_W, SC_D, SC_H = 0.80, 0.55, 1.62
SC_CT, SC_HD = 0.75, 1.47          # counter top; underside of the head band
SC_ST = 0.07                       # the side stiles
SC_BACK_Y = 15.945                 # the back face: 5 cm clear of the north wall's upper base rail (Y 15.95-16.0)
SC_X = (1.19, 11.61)               # instance x (rot 180: the piece spans x - 0.80 .. x): X 0.39-1.19 / 10.81-11.61
SC_FR = 0.014                      # b4: the brass frame round the glazed front''')
rep('''    box(G, P, x0, x0 + 0.012, 0.02, 0.032, SC_CT, pz1, LE, grain=2)
    box(G, P, x1 - 0.012, x1, 0.02, 0.032, SC_CT, pz1, LE, grain=2)
    box(G, P, x0, x1, 0.02, 0.036, pz1 - 0.001, SC_HD, LE, grain=0)                         # glow line at the head
    # the thin dark-bronze reveal round the front of the opening (sides and head)
    box(G, P, x0, x0 + 0.010, 0.40, D - 0.004, SC_CT, SC_HD, BZ, grain=2)
    box(G, P, x1 - 0.010, x1, 0.40, D - 0.004, SC_CT, SC_HD, BZ, grain=2)
    box(G, P, x0, x1, 0.40, D - 0.004, SC_HD - 0.010, SC_HD, BZ, grain=0)''',
    '''    box(G, P, x0, x1, 0.02, 0.030, pz1 - 0.001, SC_HD, LE, grain=0)                         # glow line at the head
    # b4: the glazed front - a thin polished brass frame (sides, head, sill) round a clear pane 1.6 cm behind its face
    F_ = SC_FR
    box(G, P, x0, x0 + F_, D - 0.040, D - 0.002, SC_CT, SC_HD, BR, grain=2)
    box(G, P, x1 - F_, x1, D - 0.040, D - 0.002, SC_CT, SC_HD, BR, grain=2)
    box(G, P, x0, x1, D - 0.040, D - 0.002, SC_HD - F_, SC_HD, BR, grain=0)
    box(G, P, x0, x1, D - 0.040, D - 0.002, SC_CT, SC_CT + F_, BR, grain=0)
    box(G, P, x0 + F_ - 0.004, x1 - F_ + 0.004, D - 0.022, D - 0.016, SC_CT + F_ - 0.004, SC_HD - F_ + 0.004, GLS,
        grain=0)''')
rep('''LITS = "M_AK_HShowcasePanel"''', '''LITS = "M_AK_HShowcasePanel"
GLS = "M_AK_HCaseGlass"            # b4: the hall cases' clear glass (hero_cases)''')
rep('''    "M_AK_HShowcasePanel": ("HShowcasePanel", None, {"emit_image": True, "emit": 0.90, "unlit": True}),''',
    '''    # b4 (blind judge delta 4: over-bright white slots from the entrance): 0.90 -> 0.40
    "M_AK_HShowcasePanel": ("HShowcasePanel", None, {"emit_image": True, "emit": 0.40, "unlit": True}),''')
rep('''"shadows": True, "power_scale": 0.5, "aim"''', '''"shadows": True, "power_scale": 0.25, "aim"''')
open(p, 'w', encoding='utf-8').write(s)

p = r'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero\tex_rear_alcove.py'
s = open(p, encoding='utf-8').read()
rep('''def showcase(w=512, h=1024, seed=471):''', '''def showcase(w=512, h=512, seed=471):''')
rep('''    x0, x1, z0, z1 = 0.08, 0.62, 0.75, 1.75
    vx0, vx1, vz0, vz1 = 0.082, 0.618, 0.752, 1.728   # inside the side glow lines, under the head line''',
    '''    # b4: the 0.64 x 0.71 m panel of the shorter, wider unit (x 0.08..0.72, z 0.75..1.46)
    x0, x1, z0, z1 = 0.08, 0.72, 0.75, 1.46
    vx0, vx1, vz0, vz1 = 0.082, 0.718, 0.752, 1.438   # inside the frame, under the head line''')
rep('''    hot = np.exp(-(((x - 0.35) / 0.16) ** 2 + ((z - vz1) / 0.22) ** 2))''',
    '''    hot = np.exp(-(((x - 0.40) / 0.16) ** 2 + ((z - vz1) / 0.22) ** 2))''')
open(p, 'w', encoding='utf-8').write(s)
print('ok')
