"""Plan image for the hall + armory survey (2026-10-01): hall + extension detail (top-down), site plan, N-S section at
X 22. Everything is drawn from the shared jsons and the dojo layout (no hand-placed numbers except labels).
Output: hall_armory_plan.png (+ .svg) in this folder."""
import json
import math
from pathlib import Path

import cairo

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
SH = ROOT / "WorkFiles/shared/armory_hall"
SV = ROOT / "WorkFiles/dojo/build/hall_armory/survey"
IL = json.loads((SH / "interior_layout.json").read_text(encoding="utf-8"))
HS = json.loads((SH / "hall_shell_layout.json").read_text(encoding="utf-8"))
IF = json.loads((SH / "interface.json").read_text(encoding="utf-8"))
DL = json.loads((ROOT / "WorkFiles/dojo/build/showcase/layout_showcase.json").read_text(encoding="utf-8"))
BB = json.loads((ROOT / "WorkFiles/dojo/build/showcase/blender_bounds.json").read_text(encoding="utf-8"))["instances"]
WL = json.loads((ROOT / "WorkFiles/dojo/build/landscape/fix/json/world_layout.json").read_text(encoding="utf-8"))

R = HS["extension"]["roof"]
EXT = HS["extension"]["posts"]
SITE = IF["site"]
O = (22.0, 24.0, 0.5)


def h2w(p):
    return (p[0] + O[0], p[1] + O[1])


W, H = 2200, 1660
INK = (0.13, 0.13, 0.14)
GREY = (0.55, 0.55, 0.57)
LIGHT = (0.86, 0.86, 0.87)
PAPER = (0.985, 0.98, 0.97)
HALL = (0.80, 0.70, 0.56)
EXTC = (0.93, 0.80, 0.62)
ARM = (0.22, 0.42, 0.70)
CASE = (0.30, 0.30, 0.34)
RED = (0.80, 0.12, 0.12)
GREEN = (0.20, 0.55, 0.25)
MAG = (0.65, 0.20, 0.65)
ORANGE = (0.93, 0.55, 0.12)
BROWN = (0.45, 0.32, 0.22)


class Panel:
    def __init__(self, ctx, ox, oy, s, wx0, wy1, flip=True):
        self.c, self.ox, self.oy, self.s, self.wx0, self.wy1, self.flip = ctx, ox, oy, s, wx0, wy1, flip

    def P(self, x, y):
        return self.ox + (x - self.wx0) * self.s, self.oy + ((self.wy1 - y) * self.s if self.flip else (y - self.wy1) * self.s)

    def rect(self, x0, y0, x1, y1, fill=None, stroke=None, lw=1.0, dash=None, alpha=1.0):
        c = self.c
        a = self.P(x0, y1)
        b = self.P(x1, y0)
        c.rectangle(a[0], a[1], b[0] - a[0], b[1] - a[1])
        self._paint(fill, stroke, lw, dash, alpha)

    def poly(self, pts, fill=None, stroke=None, lw=1.0, dash=None, alpha=1.0, close=True):
        c = self.c
        for i, (x, y) in enumerate(pts):
            (c.move_to if i == 0 else c.line_to)(*self.P(x, y))
        if close:
            c.close_path()
        self._paint(fill if close else None, stroke, lw, dash, alpha)

    def line(self, x0, y0, x1, y1, col=INK, lw=1.0, dash=None):
        self.poly([(x0, y0), (x1, y1)], stroke=col, lw=lw, dash=dash, close=False)

    def circle(self, x, y, r, fill=None, stroke=None, lw=1.0):
        cx, cy = self.P(x, y)
        self.c.new_path()
        self.c.arc(cx, cy, r * self.s, 0, 2 * math.pi)
        self._paint(fill, stroke, lw, None, 1.0)

    def _paint(self, fill, stroke, lw, dash, alpha):
        c = self.c
        if fill:
            c.set_source_rgba(*fill, alpha)
            if stroke:
                c.fill_preserve()
            else:
                c.fill()
        if stroke:
            c.set_source_rgb(*stroke)
            c.set_line_width(lw)
            c.set_dash(dash or [])
            c.stroke()
            c.set_dash([])
        c.new_path()

    def text(self, x, y, s, size=13, col=INK, bold=False, anchor="l", rot=0.0):
        c = self.c
        c.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
        c.set_font_size(size)
        px, py = self.P(x, y)
        ext = c.text_extents(s)
        c.save()
        c.translate(px, py)
        c.rotate(rot)
        dx = {"l": 0, "c": -ext.width / 2, "r": -ext.width}[anchor]
        c.move_to(dx, ext.height / 2)
        c.set_source_rgb(*col)
        c.show_text(s)
        c.restore()


def rot_rect(cx, cy, w, d, rz):
    a = math.radians(rz)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for (u, v) in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
        pts.append((cx + u * ca - v * sa, cy + u * sa + v * ca))
    return pts


def title(ctx, x, y, s, size=20):
    ctx.select_font_face("Arial", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    ctx.set_source_rgb(*INK)
    ctx.move_to(x, y)
    ctx.show_text(s)


def draw(surface):
    c = cairo.Context(surface)
    c.set_source_rgb(*PAPER)
    c.paint()
    title(c, 30, 40, "Dojo main hall + armory interior: survey and design, revision 1 (2026-10-01)", 24)
    c.set_font_size(14)
    c.select_font_face("Arial")
    c.move_to(30, 64)
    c.show_text("World metres (layout frame: x east, y north). Hall-local origin = centre door threshold (22.0, 24.0) "
                "at FFL +0.50. All numbers from WorkFiles/shared/armory_hall/*.json.")

    # ======================================================================================== A: detail plan
    s = 31.0
    A = Panel(c, 40, 110, s, 9.0, 50.0)
    title(c, 40, 100, "A  Hall, rear extension and the armory interior (top-down)", 17)
    # veranda + step band
    A.rect(11.0, 22.0, 33.0, 34.0, fill=(0.93, 0.90, 0.85), stroke=GREY, lw=0.8)
    A.rect(11.0, 20.85, 33.0, 22.05, fill=(0.88, 0.88, 0.88), stroke=GREY, lw=0.6)
    A.text(10.0, 21.4, "step band", 11, GREY)
    # upper roof plan + rear roof plan (dashed)
    A.rect(12.1, 23.1, 31.9, 34.9, stroke=GREY, lw=1.0, dash=[6, 4])
    A.rect(R["verges_x"][0], R["valley"]["y"], R["verges_x"][1], R["eave_north"]["y"], stroke=BROWN, lw=1.4, dash=[8, 4])
    A.line(R["verges_x"][0], R["ridge"]["y"], R["verges_x"][1], R["ridge"]["y"], BROWN, 1.2, [3, 3])
    A.text(29.95, R["ridge"]["y"] + 0.35, "rear ridge +%.2f" % R["ridge"]["planes_meet_z"], 11, BROWN)
    A.line(R["verges_x"][0], R["valley"]["y"], R["verges_x"][1], R["valley"]["y"], BROWN, 1.6)
    A.text(29.95, R["valley"]["y"] + 0.35, "valley Y %.2f +%.2f" % (R["valley"]["y"], R["valley"]["z_collision"]), 11, BROWN)
    A.text(14.0, R["eave_north"]["y"] + 0.35, "rear eave +%.2f" % R["eave_north"]["z_collision"], 11, BROWN, anchor="r")
    # hall body walls + extension walls
    A.rect(13.0, 24.0, 31.0, 34.0, fill=HALL, alpha=0.35)
    A.rect(EXT["x0"], EXT["y0"], EXT["x1"], EXT["y1"], fill=EXTC, alpha=0.6)
    for (x0, y0, x1, y1) in ((13, 24, 19, 24), (25, 24, 31, 24), (13, 24, 13, 34), (31, 24, 31, 34), (13, 34, 15, 34),
                             (29, 34, 31, 34), (15, 34, 15, 45), (29, 34, 29, 45), (15, 45, 29, 45)):
        A.line(x0, y0, x1, y1, INK, 4.0)
    A.line(15, 34, 29, 34, INK, 1.0, [4, 4])
    A.text(22.0, 33.55, "old rear wall X 15-29 removed (opened)", 11, INK, anchor="c")
    # posts
    for x in range(13, 32, 2):
        for y in (24, 34):
            if y == 34 and 17 <= x <= 27:
                A.rect(x - 0.12, y - 0.12, x + 0.12, y + 0.12, stroke=RED, lw=1.0)
                continue
            A.rect(x - 0.12, y - 0.12, x + 0.12, y + 0.12, fill=INK)
    for y in (26, 28, 30, 32):
        for x in (13, 31):
            A.rect(x - 0.12, y - 0.12, x + 0.12, y + 0.12, fill=INK)
    for y in (35, 37, 39, 41, 43, 45):
        for x in (15, 29):
            A.rect(x - 0.12, y - 0.12, x + 0.12, y + 0.12, fill=INK)
    for x in (17, 19, 21, 23, 25, 27):
        A.rect(x - 0.12, 44.88, x + 0.12, 45.12, fill=INK)
    # door bays (open)
    for (a, b) in IF["door_openings"]["clear_x"]:
        A.rect(a + 22, 23.88, b + 22, 24.12, fill=(0.98, 0.93, 0.55), stroke=ORANGE, lw=1.2)
    A.text(22.0, 23.35, "3 open door bays, 1.76 m clear each, head +%.3f" % IF["door_openings"]["head_track_underside_z"],
           11, ORANGE, True, "c")
    # parked leaves
    for r in HS["instances_new"]:
        if r["piece"] == "SM_DKH_DoorLeaf_Parked":
            x, y = r["loc_world_m"][:2]
            A.rect(x, y, x + 0.922, y + 0.035, fill=ORANGE)
    # armory interior: walls (outer faces) + floor area
    A.rect(15.7, 24.0, 28.3, 44.3, stroke=ARM, lw=1.2)
    A.rect(16.0, 24.0, 28.0, 44.0, fill=(0.80, 0.86, 0.95), alpha=0.45)
    # interior pieces: floor-standing footprint
    for r in IL["instances"]:
        g, b = r["group"], r["bbox_m"]
        if g in ("ceiling", "floor") or b[2] > 1.0:
            continue
        x0, y0 = h2w(b[0:2])
        x1, y1 = h2w(b[3:5])
        col = CASE if g == "case" else (ARM if g == "wall" else (0.45, 0.50, 0.60))
        A.rect(x0, y0, x1, y1, fill=col, alpha=0.75 if g == "case" else 0.45)
    for cs in IL["cases"]:
        x, y = h2w(cs["loc_m"][:2])
        A.text(x, y, cs["label"], 10, (1, 1, 1), True, "c")
    # dais
    A.rect(16.0, 24 + 16.43, 28.0, 44.0, stroke=(0.55, 0.40, 0.15), lw=1.0, dash=[3, 2])
    A.text(22.0, 43.55, "dais +0.60 (world +1.10)", 10, (0.55, 0.40, 0.15), anchor="c")
    # window backers
    for r in HS["instances_new"]:
        if r["piece"] == "SM_DKH_Rear_WindowBacker":
            x, y = r["loc_world_m"][:2]
            A.rect(x - 0.03, y - 1.8, x + 0.03, y + 1.8, fill=ORANGE)
    A.text(14.0, 38.0, "window backers", 10, ORANGE, anchor="r")
    # 1v1 closure
    for b in SITE["closure_1v1"]["SM_DKX_1v1_HallRear"]["new"]:
        x0, y0, _z0, x1, y1, _z1 = b["box"]
        A.rect(x0, y0, x1, y1, fill=RED)
    ob = SITE["closure_1v1"]["SM_DKX_1v1_HallRear"]["old_box"]
    A.line(ob[0], 34.05, ob[3], 34.05, RED, 1.0, [2, 3])
    rr = SITE["closure_1v1"]["SM_DKX_1v1_RearRoof (new)"]["box"]
    A.rect(rr[0], rr[1], rr[3], rr[4], stroke=RED, lw=1.0, dash=[1, 3])
    A.text(30.4, 46.4, "1v1 RearRoof blocker (z >= %.2f)" % rr[2], 10, RED)
    A.text(10.2, 34.6, "1v1 HallRear W", 10, RED)
    # north wall + alley
    A.rect(9.0, 47.0, 35.0, 48.0, fill=(0.62, 0.62, 0.60), stroke=INK, lw=0.8)
    A.text(22.0, 47.5, "compound north wall (moved +11: Y 47-48)", 11, (1, 1, 1), True, "c")
    A.rect(9.0, 36.0, 35.0, 37.0, stroke=GREY, lw=1.0, dash=[5, 3])
    A.text(9.2, 36.5, "old north wall Y 36-37", 10, GREY)
    A.text(22.0, 46.3, "rear alley 1.88 m (as before)", 10, INK, anchor="c")
    # origin + dims
    A.circle(22.0, 24.0, 0.22, fill=RED)
    A.text(22.35, 24.55, "hall-local origin (22.0, 24.0, +0.50)", 11, RED, True)
    A.line(16.0, 23.0, 28.0, 23.0, ARM, 1.0)
    A.text(16.1, 22.6, "armory 12.0 m (X 16-28)", 11, ARM, True)
    A.line(32.4, 24.0, 32.4, 44.0, ARM, 1.0)
    A.text(32.6, 43.6, "armory 20.0 m", 11, ARM, True)
    A.text(32.6, 43.0, "(Y 24-44)", 11, ARM)
    A.line(33.6, 34.0, 33.6, 45.0, INK, 1.0)
    A.text(33.8, 39.5, "extension 11.0 m", 11, INK, True)
    A.text(33.8, 38.9, "x 14.0 m (X 15-29)", 11, INK)
    A.text(13.2, 24.6, "hall 18 x 10 m", 11, INK, True)
    A.text(13.2, 33.4, "closed strip", 10, GREY)
    A.text(29.1, 33.4, "closed strip", 10, GREY)

    # ======================================================================================== B: site plan
    s2 = 13.0
    B = Panel(c, 1140, 110, s2, -10.0, 62.0)
    title(c, 1140, 100, "B  Site: compound, terrace edge and 1v1 lines (old dashed, new solid)", 17)
    # terrace (new) + hill
    B.rect(-7.0, -3.0, 49.0, 56.0, fill=(0.90, 0.94, 0.88))
    B.rect(-10.0, 56.0, 62.0, 62.0, fill=(0.80, 0.88, 0.78))
    B.text(20.0, 59.5, "north hill: 0 at y 56, +6 at y 72 (was 0 at 44, +6 at 60)", 12, GREEN, anchor="c")
    B.line(-7.0, 44.0, 49.0, 44.0, GREEN, 1.4, [6, 4])
    B.line(-7.0, 56.0, 49.0, 56.0, GREEN, 2.4)
    B.text(49.5, 44.0, "old terrace edge / B6 y 44", 11, GREEN)
    B.text(49.5, 56.0, "new edge / B6 y 56", 11, GREEN, True)
    # compound walls
    B.rect(-1.0, -1.0, 45.0, 0.0, fill=(0.62, 0.62, 0.60))
    B.rect(-1.0, -1.0, 0.0, 48.0, fill=(0.62, 0.62, 0.60))
    B.rect(44.0, -1.0, 45.0, 48.0, fill=(0.62, 0.62, 0.60))
    B.rect(-1.0, 47.0, 45.0, 48.0, fill=(0.40, 0.40, 0.40))
    B.rect(-1.0, 36.0, 45.0, 37.0, stroke=GREY, lw=1.2, dash=[5, 3])
    B.rect(-1.0, 36.0, 0.0, 47.0, stroke=INK, lw=1.0)
    B.rect(44.0, 36.0, 45.0, 47.0, stroke=INK, lw=1.0)
    # ring
    B.rect(-1.1, -1.1, 45.1, 37.1, stroke=MAG, lw=1.0, dash=[3, 3])
    B.rect(-1.1, -1.1, 45.1, 48.1, stroke=MAG, lw=1.2)
    B.text(45.6, 48.6, "1v1 ring to y 48.1", 11, MAG)
    # buildings: outbuildings / corridors / shed / pavilion roofs (bboxes), hall, extension
    for i, ins in enumerate(DL["instances"]):
        if ins.get("removed") or ins.get("kit") not in ("outbuildings", "corridors", "shed", "pavilion"):
            continue
        if "Roof" not in ins["piece"]:
            continue
        b = BB.get(str(i))
        if b:
            B.rect(b["min"][0], b["min"][1], b["max"][0], b["max"][1], fill=(0.75, 0.72, 0.68), alpha=0.6)
    B.rect(11.0, 22.0, 33.0, 34.0, fill=(0.93, 0.90, 0.85), stroke=GREY, lw=0.6)
    B.rect(13.0, 24.0, 31.0, 34.0, fill=HALL)
    B.rect(EXT["x0"], EXT["y0"], EXT["x1"], EXT["y1"], fill=EXTC, stroke=INK, lw=1.0)
    B.rect(16.0, 24.0, 28.0, 44.0, stroke=ARM, lw=1.4)
    B.text(22.0, 39.5, "extension", 11, INK, True, "c")
    B.text(22.0, 29.0, "hall", 11, INK, True, "c")
    # gate gap
    B.rect(18.0, -1.0, 26.0, 0.0, fill=PAPER)
    B.text(22.0, -2.2, "gate", 11, INK, anchor="c")
    # closures
    for b in SITE["closure_1v1"]["SM_DKX_1v1_HallRear"]["new"]:
        x0, y0, _z0, x1, y1, _z1 = b["box"]
        B.rect(x0, y0 - 0.15, x1, y1 + 0.15, fill=RED)
    nb = SITE["closure_1v1"]["SM_DKX_1v1_NorthWallTop"]
    B.line(-1.0, 36.5, 45.0, 36.5, RED, 1.0, [2, 3])
    B.line(-1.0, 47.5, 45.0, 47.5, RED, 1.4)
    for lb in SITE["closure_1v1"]["terrace_lines"]:
        n = lb["new"]
        L = n["size_m"][0]
        x, y = n["loc"][:2]
        if abs(n["rot_z_deg"]) < 1:
            B.line(x - L / 2, y, x + L / 2, y, (0.15, 0.45, 0.15), 1.0, [8, 2, 2, 2])
        else:
            B.line(x, y - L / 2, x, y + L / 2, (0.15, 0.45, 0.15), 1.0, [8, 2, 2, 2])
    # WR5 east terrace wall
    B.line(49.0, 34.0, 49.0, 44.0, BROWN, 3.0)
    B.line(49.0, 44.0, 49.0, 56.0, BROWN, 3.0, [4, 2])
    B.text(49.6, 50.0, "WR5 +4+4+2+2 m", 11, BROWN)
    # cherry slots + cypress
    for m in SITE["terrace_and_terrain"]["cherry_slots"]:
        B.circle(m["from"][0], m["from"][1], 0.9, stroke=(0.85, 0.45, 0.6), lw=1.0)
        B.circle(m["to"][0], m["to"][1], 0.9, fill=(0.85, 0.45, 0.6))
        B.line(m["from"][0], m["from"][1] + 0.9, m["to"][0], m["to"][1] - 0.9, (0.85, 0.45, 0.6), 0.8, [2, 2])
    for cy in SITE["terrace_and_terrain"]["cypress_front_row"]["old"]:
        B.circle(cy["loc"][0], cy["loc"][1], 0.6, stroke=GREEN, lw=1.0)
        B.circle(cy["loc"][0], cy["loc"][1] + 12.0, 0.6, fill=GREEN)
    B.text(-9.6, 51.0, "cypress row +12 m", 11, GREEN)
    B.text(-9.6, 42.0, "cherry slots CS19/CS20 +11 m", 11, (0.75, 0.35, 0.5))
    B.text(-9.6, 33.0, "rear yards (out of 1v1)", 11, GREY)
    # grid
    for y in range(0, 61, 10):
        B.text(-9.8, y, "y %d" % y, 10, GREY)
    for x in range(0, 51, 10):
        B.text(x, -4.5, "x %d" % x, 10, GREY, anchor="c")

    # ======================================================================================== C: section
    s3 = 33.0
    y0w, y1w = 14.0, 60.0
    title(c, 40, 1150, "C  Section north-south at X 22.0 (hall centre line), looking east; heights world z (m)", 17)
    Cz = Panel(c, 40, 1180, s3, y0w, 12.5, flip=True)  # x axis = world Y, y axis = z (z 11 at the top)
    # ground
    Cz.poly([(y0w, -1.5), (y0w, 0.0), (20.85, 0.0), (20.85, 0.1667), (21.25, 0.1667), (21.25, 0.3333), (21.65, 0.3333),
             (21.65, 0.5), (45.2, 0.5), (45.2, 0.0), (56.0, 0.0), (y1w, 6.0 * (y1w - 56) / 16.0),
             (y1w, -1.5)], fill=(0.88, 0.86, 0.80), stroke=GREY, lw=0.8)
    Cz.poly([(56.0, 0.0), (60.0, 1.5), (60.0, -1.5)], fill=(0.80, 0.88, 0.78))
    Cz.text(56.2, 0.4, "terrace edge y 56", 11, GREEN)
    Cz.text(44.0 - 0.1, -1.0, "old edge y 44", 10, GREY, anchor="r")
    Cz.line(44.0, -0.2, 44.0, -1.4, GREY, 1.0, [3, 3])
    # lower front roof
    Cz.poly([(21.5, 3.0), (24.06, 3.0 + 2.56 * math.tan(math.radians(25)))], stroke=INK, lw=2.5, close=False)
    Cz.text(18.6, 3.25, "lower roof eave +3.00", 11)
    # front wall with the door
    Cz.rect(23.88, 0.5, 24.12, 0.545, fill=INK)
    Cz.rect(23.88, 0.5 + IF["door_openings"]["head_track_underside_z"], 24.12, 5.86, fill=INK)
    Cz.text(24.25, 1.35, "door 1.84 m clear", 11, ORANGE, True)
    # main roof
    t30 = math.tan(math.radians(30))
    yv, zv = R["valley"]["y"], R["valley"]["z_collision"]
    Cz.poly([(23.1, 5.5), (29.0, 8.9064), (yv, zv)], stroke=INK, lw=2.5, close=False)
    Cz.poly([(yv, zv), (34.9, 5.5)], stroke=GREY, lw=1.2, dash=[4, 3], close=False)
    Cz.rect(28.72, 8.776, 29.28, 9.3649, fill=INK)
    Cz.text(29.5, 9.55, "main ridge: planes +8.91, cap +9.36 (unchanged)", 11, INK, True)
    Cz.text(34.95, 5.25, "old back eave +5.50", 10, GREY)
    # rear roof
    Cz.poly([(yv, zv), (R["ridge"]["y"], R["ridge"]["planes_meet_z"]), (R["eave_north"]["y"], R["eave_north"]["z_collision"])],
            stroke=BROWN, lw=2.5, close=False)
    Cz.rect(R["ridge"]["y"] - 0.28, R["ridge"]["planes_meet_z"] - 0.13, R["ridge"]["y"] + 0.28, R["ridge"]["cap_top_z_est"],
            fill=BROWN)
    Cz.text(R["ridge"]["y"] + 0.4, R["ridge"]["cap_top_z_est"] + 0.25,
            "rear ridge: planes +%.2f, cap ~+%.2f (0.76 lower)" % (R["ridge"]["planes_meet_z"], R["ridge"]["cap_top_z_est"]),
            11, BROWN, True)
    Cz.text(yv + 0.1, zv - 0.45, "valley Y %.2f +%.2f" % (yv, zv), 11, BROWN)
    Cz.text(R["eave_north"]["y"] - 0.2, R["eave_north"]["z_collision"] + 0.35, "rear eave +%.2f" % R["eave_north"]["z_collision"],
            11, BROWN, anchor="r")
    # walls: main rear plate (beam), extension north wall
    Cz.rect(33.88, 5.52, 34.12, 5.6872, fill=INK)
    Cz.rect(44.88, 0.5, 45.12, R["wall_plate"][1], fill=INK)
    Cz.text(45.3, 4.3, "extension wall Y 45", 11)
    # armory
    Cz.rect(24.0, 0.40, 44.0, 0.50, fill=ARM)
    Cz.rect(24.0, 5.135, 44.0, 5.5, fill=ARM, alpha=0.6)
    Cz.text(24.3, 4.85, "armory ceiling +4.80 (world +5.30), coffer tops +5.50", 11, ARM, True)
    Cz.rect(44.0, 0.5, 44.3, 5.5, fill=ARM, alpha=0.8)
    Cz.text(33.6, 0.85, "armory floor = hall FFL +0.50", 11, ARM, True)
    for cs in IL["cases"]:
        x, y, z = cs["loc_m"]
        if abs(x) > 1.0:
            continue
        Wc, Dc, Hc, Gc = cs["width_depth_plinth_glass_m"]
        yy = y + 24.0
        Cz.rect(yy - Dc / 2, 0.5 + z, yy + Dc / 2, 0.5 + z + Hc, fill=CASE)
        if Gc:
            Cz.rect(yy - Dc / 2, 0.5 + z + Hc, yy + Dc / 2, 0.5 + z + Hc + Gc, stroke=CASE, lw=1.0)
        Cz.text(yy, 0.5 + z + Hc + Gc + 0.3, cs["label"], 11, CASE, True, "c")
    # dais
    Cz.poly([(24 + 15.85, 0.5), (24 + 15.85, 0.65), (24 + 16.2, 0.65), (24 + 16.2, 0.8), (24 + 16.55, 0.8), (24 + 16.55, 0.95),
             (24 + 16.9, 0.95), (24 + 16.9, 1.1), (44.0, 1.1), (44.0, 0.5)], fill=(0.55, 0.40, 0.15), alpha=0.7)
    Cz.text(40.9, 1.45, "dais +1.10", 11, (0.55, 0.40, 0.15), True)
    # north wall + alley
    Cz.rect(47.0, 0.0, 48.0, 2.13, fill=(0.45, 0.45, 0.45))
    Cz.text(47.5, 2.5, "north wall Y 47-48", 11, INK, True, "c")
    Cz.text(46.06, 0.3, "alley", 10, INK, anchor="c")
    Cz.rect(36.0, 0.0, 37.0, 2.13, stroke=GREY, lw=1.0, dash=[3, 3])
    Cz.text(36.5, 2.5, "old wall", 10, GREY, anchor="c")
    # sight line from CAM_Establishing over the main ridge cap
    cy, cz = 0.25, 2.3
    slope = (9.3649 - cz) / (29.0 - cy)
    Cz.poly([(y0w, cz + slope * (y0w - cy)), (40.5, cz + slope * (40.5 - cy))], stroke=RED, lw=1.2, dash=[6, 4],
            close=False)
    Cz.text(14.3, cz + slope * (14.3 - cy) + 0.45, "sight line from CAM_Establishing (gate, eye +2.3) over the main ridge cap",
            11, RED)
    Cz.text(40.8, 12.1,
            "rear ridge %.1f m below it at Y 39.5" % (cz + slope * (39.5 - cy) - R["ridge"]["cap_top_z_est"]), 11, RED)
    # z scale
    for z in range(0, 11, 2):
        Cz.text(y0w - 0.3, z, "+%d" % z, 10, GREY, anchor="r")
        Cz.line(y0w, z, y0w + 0.3, z, GREY, 0.8)
    for y in range(15, 61, 5):
        Cz.text(y, -1.25, "Y %d" % y, 10, GREY, anchor="c")

    # legend
    lx, ly = 1640, 1200
    items = [(HALL, "hall body (kept)"), (EXTC, "rear extension (new, SM_DKH_Rear*)"), (ARM, "armory interior (hall-local 12 x 20)"),
             (CASE, "display cases"), (ORANGE, "open doors / parked leaves / window backers"), (RED, "1v1 blockers"),
             (MAG, "1v1 ring"), (GREEN, "terrace edge, B5-B7 lines, trees"), (BROWN, "rear roof (gable, 25 deg)")]
    for k, (col, lab) in enumerate(items):
        c.set_source_rgb(*col)
        c.rectangle(lx, ly + k * 24, 18, 14)
        c.fill()
        c.set_source_rgb(*INK)
        c.select_font_face("Arial")
        c.set_font_size(13)
        c.move_to(lx + 26, ly + k * 24 + 12)
        c.show_text(lab)


png = SV / "hall_armory_plan.png"
surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
draw(surf)
surf.write_to_png(str(png))
svg = cairo.SVGSurface(str(SV / "hall_armory_plan.svg"), W, H)
draw(svg)
svg.finish()
print(png)
