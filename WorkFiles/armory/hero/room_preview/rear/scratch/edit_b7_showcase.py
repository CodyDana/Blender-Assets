p = r'C:\Users\Cody\Desktop\Blender_Projects\Scripts\armory\hero\hero_rear_alcove.py'
s = open(p, encoding='utf-8').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)


rep('''    "M_AK_HShowcasePanel": ("HShowcasePanel", None, {"emit_image": True, "emit": 0.22, "unlit": True}),''',
    '''    # b7 (blind judge delta 5: from the entrance the b6 niches read as flat blank light boxes): 0.22 -> 0.12, so the
    # lit lining and the shelf read in front of it
    "M_AK_HShowcasePanel": ("HShowcasePanel", None, {"emit_image": True, "emit": 0.12, "unlit": True}),
    # b7 (judge delta 5): the niche's lining (side returns, floor, shelf top): a warm pale satin that the soffit spot
    # grades from bright at the head to shadow at the counter, so the recess depth reads
    "M_AK_HShowcaseLining": (None, 1.0, {"color": "#8C6A44", "rough": 0.55}),''')

rep('''SC_FR = 0.014                      # b4: the brass frame round the glazed front''',
    '''SC_FR = 0.030                      # b7 (judge delta 5: a dark frame): a 3 cm black lacquer frame (b4-b6: 1.4 cm brass)
SC_SHELF = 1.09                    # b7 (judge delta 5: a visible shelf): a fixed shelf board mid-height in the niche
LIN = "M_AK_HShowcaseLining"''')

rep('''    box(G, P, x0, x1, 0.02, 0.030, pz1 - 0.001, SC_HD, LE, grain=0)                         # glow line at the head''',
    '''    box(G, P, x0, x1, 0.02, 0.030, pz1 - 0.001, SC_HD, LE, grain=0)                         # glow line at the head
    # b7 (judge delta 5): the recess reads as a lit nook - the lining on both side returns and the floor, 1 cm inside
    # the stiles, from the back panel to behind the glazing, and a fixed shelf board with a thin brass nose
    box(G, P, x0, x0 + 0.01, 0.02, D - 0.04, SC_CT, SC_HD, LIN, grain=2)
    box(G, P, x1 - 0.01, x1, 0.02, D - 0.04, SC_CT, SC_HD, LIN, grain=2)
    box(G, P, x0, x1, 0.02, D - 0.04, SC_CT - 0.002, SC_CT + 0.004, LIN, grain=0)
    box(G, P, x0 + 0.01, x1 - 0.01, 0.02, D - 0.07, SC_SHELF - 0.022, SC_SHELF, LQ, bev=0.002, grain=0,
        front=("+z", LIN))
    box(G, P, x0 + 0.01, x1 - 0.01, D - 0.074, D - 0.066, SC_SHELF - 0.016, SC_SHELF - 0.006, BR, grain=0)''')

rep('''    # b4: the glazed front - a thin polished brass frame (sides, head, sill) round a clear pane 1.6 cm behind its face
    F_ = SC_FR
    box(G, P, x0, x0 + F_, D - 0.040, D - 0.002, SC_CT, SC_HD, BR, grain=2)
    box(G, P, x1 - F_, x1, D - 0.040, D - 0.002, SC_CT, SC_HD, BR, grain=2)
    box(G, P, x0, x1, D - 0.040, D - 0.002, SC_HD - F_, SC_HD, BR, grain=0)
    box(G, P, x0, x1, D - 0.040, D - 0.002, SC_CT, SC_CT + F_, BR, grain=0)''',
    '''    # b4: the glazed front round a clear pane 1.6 cm behind its face; b7 (judge delta 5): a 3 cm black lacquer frame
    # (sides, head, sill) with a thin brass line round the glass
    F_ = SC_FR
    box(G, P, x0, x0 + F_, D - 0.040, D - 0.002, SC_CT, SC_HD, LQ, bev=0.003, grain=2)
    box(G, P, x1 - F_, x1, D - 0.040, D - 0.002, SC_CT, SC_HD, LQ, bev=0.003, grain=2)
    box(G, P, x0, x1, D - 0.040, D - 0.002, SC_HD - F_, SC_HD, LQ, bev=0.003, grain=0)
    box(G, P, x0, x1, D - 0.040, D - 0.002, SC_CT, SC_CT + F_, LQ, bev=0.003, grain=0)
    for a0, a1, b0, b1, g in ((x0 + F_, x0 + F_ + 0.004, SC_CT + F_, SC_HD - F_, 2), (x1 - F_ - 0.004, x1 - F_, SC_CT + F_, SC_HD - F_, 2),
                              (x0 + F_, x1 - F_, SC_CT + F_, SC_CT + F_ + 0.004, 0), (x0 + F_, x1 - F_, SC_HD - F_ - 0.004, SC_HD - F_, 0)):
        box(G, P, a0, a1, D - 0.028, D - 0.012, b0, b1, BR, grain=g)''')

rep('''                    "shadows": True, "power_scale": 0.15, "aim"''',
    '''                    "shadows": True, "power_scale": 0.35, "aim"''')
open(p, 'w', encoding='utf-8').write(s)
print("ok")
