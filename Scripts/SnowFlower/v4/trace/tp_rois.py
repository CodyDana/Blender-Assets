"""Trace pilot - element ownership ROIs for the sheath throat, drawn by hand on 12-16x zooms of the reference
(ref pixel coords: col, row).  LEFT half as seen in the front view (+X side of the sheath); the right half uses the
same ROI mirrored about the axis, but every edge inside an ROI comes from the reference's own pixels (classes), so
the right side is traced from its own pixels, not copied.  Order = paint order (back -> front).
Centre elements: the path starts ON the axis at the top, runs round the left side and ends ON the axis at the bottom."""
AXIS = 505.5
BLOSSOM_C = (505.8, 87.5)

ROIS = [
    ("sleeve", "pair", [(452, 126), (462, 126), (462, 172), (452, 172)]),
    ("t2",     "pair", [(436, 60), (452, 59), (459, 68), (461, 83), (446, 85), (436, 82)]),
    ("t1",     "pair", [(448, 40.5), (477, 39.5), (486, 44), (492, 50), (495, 62), (492, 71), (484, 77), (474, 79),
                        (460, 71), (451, 63), (448, 52)]),
    ("collar", "centre", [(505.5, 28.0), (470, 28.0), (470, 41.0), (477, 42.5), (490, 43.0), (505.5, 43.0)]),
    ("drop",   "centre", [(505.5, 113), (483, 116), (482, 124), (486, 136), (496, 158), (505.5, 170)]),
    ("lat",    "pair", [(429, 85), (447, 81), (476, 80), (486, 85), (491, 97), (492, 110), (489, 120), (472, 131),
                        (456, 141.5), (447, 143), (440, 122), (429, 92)]),
    ("lace",   "pair", [(462, 143), (482, 137), (490, 150), (500, 164), (500, 184), (462, 184)]),
    ("crestT", "centre", [(505.5, 33.5), (490, 38.5), (489, 50), (494, 61), (505.5, 62)]),
    ("crestB", "centre", [(505.5, 110), (493, 113), (494, 124), (499, 135), (505.5, 138)]),
    ("sprigU", "pair", "circle", (487.0, 66.0), 6.5),
    ("sprigL", "pair", "circle", (480.5, 99.0), 6.5),
]
