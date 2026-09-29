# C1 (40 mm, sensor 36, 1448 x 1086, shift_y -0.315, level at (6, -4.18, 3.39)) projection of rear landmarks
f = 40 / 36 * 1448; cy = 1086 / 2 - 0.315 * 1448
def px(X, Y, Z):
    D = Y + 4.18
    return round(724 + f * (X - 6) / D, 1), round(cy - f * (Z - 3.39) / D, 1)
def rows(L, stair, lip, heavy, deck_lant, table_c):
    return {
        "case1 plinth front L/R (anchor, Y 3.05)": (px(5.1, 3.05, 0.5)[0], px(6.9, 3.05, 0.5)[0]),
        "painting paper L/R (Y %.2f)" % (L - 0.08): (px(5.06, L - .08, 2)[0], px(6.94, L - .08, 2)[0]),
        "painting paper top/bottom Z 3.30/1.30": (px(6, L - .08, 3.30)[1], px(6, L - .08, 1.30)[1]),
        "heavy post centres X 3.30/8.70": (px(3.3, heavy - .15, 0)[0], px(8.7, heavy - .15, 0)[0]),
        "stair foot y / deck lip y": (px(6, stair, 0)[1], px(6, lip, 0.9)[1]),
        "flight width at foot X 3.80-8.20": (px(3.8, stair, 0)[0], px(8.2, stair, 0)[0]),
        "deck lantern centres": (px(3.5, deck_lant, 0.9)[0], px(8.5, deck_lant, 0.9)[0]),
        "stair-foot lantern centres": (px(3.625, stair + .175, .45)[0], px(8.375, stair + .175, .45)[0]),
        "rear alcove W X 1.2-3.0 (front)": (px(1.2, L - .6, 2)[0], px(3.0, L - .6, 2)[0]),
        "hero table front y (Z 0.9)": (px(6, table_c - .45, 0.9)[1],),
    }
for name, a in (("b9 (16 m)", (16.0, 12.30, 14.40, 13.33, 15.10, 15.35)), ("r20 (20 m)", (20.0, 15.50, 17.60, 16.53, 19.10, 19.35))):
    print(name)
    for k, v in rows(*a).items():
        print("  %-48s %s" % (k, v))
