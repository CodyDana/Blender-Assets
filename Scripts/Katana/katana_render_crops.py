"""The design sheet's framing (KATANA_DESIGN_SHEET.png, 7000 x 6000 px = 1400 x 1200 sheet mm, 5 px per sheet mm),
shared by katana_render.py (our renders) and katana_compare.py (the sheet crops). Crops are sheet pixels
(x0, y0, x1, y1), top-left origin."""
SIDE_CROP = (300, 800, 5300, 1560)        # row 1 side view (1:1)
TOP_CROP = (300, 300, 5300, 700)          # row 1 top view (1:1)
END_CROP = (5600, 750, 6200, 1350)        # row 1 end view from the tip (1:1)
TSUKA2_CROP = (420, 4380, 3100, 4920)     # 4a tsuka wrap omote (2:1): sword z -84 at the crop centre
KISSAKI3_CROP = (3475, 4300, 4675, 5000)  # 4c kissaki omote (3:1)
