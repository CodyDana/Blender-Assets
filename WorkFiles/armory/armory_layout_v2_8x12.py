"""Top-down layout of the armory gallery (v2, follows reference/armory3_reference.png) for ARMORY_PLAN.md.

Planning aid only: writes ARMORY_LAYOUT.svg and ARMORY_LAYOUT.txt beside this script.
One data table drives both drawings, so they cannot disagree. Units are cm.
Frame: origin at the interior south-west corner at floor level, X across (0-800), Y along the
axis (0-1200, north = +Y), Z up. The door is in the south wall; the rear platform is at the north end.
The v1 kura layout is kept in armory_layout_v1_kura.py.
Run: py WorkFiles/armory/armory_layout.py
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
W, L, T = 800, 1200, 30  # interior width, interior length, wall thickness

# (label, char, x0, y0, x1, y1, fill)
RECTS = [
    ("Rear platform, top +60", "=", 0, 1030, 800, 1200, "#8a6a4a"),
    ("Steps, 4 risers x 15", "s", 200, 955, 600, 1030, "#a0825f"),
    ("Entry mat", ".", 325, 10, 475, 100, "#cdbb95"),
    ("Wall display panels, west (9)", "9", 0, 100, 25, 950, "#e6d3a8"),
    ("Wall display panels, east (9)", "9", 775, 100, 800, 950, "#e6d3a8"),
    ("Corner long-weapon rack", "r", 20, 1110, 140, 1195, "#e6d3a8"),
    ("Corner long-weapon rack", "r", 660, 1110, 780, 1195, "#e6d3a8"),
    ("Case 1 (L) 200x140", "#", 300, 200, 500, 340, "#f3e6c8"),
    ("Case 2 (M) 160x120", "#", 320, 480, 480, 600, "#f3e6c8"),
    ("Case 3 (L) 180x100", "#", 310, 740, 490, 840, "#f3e6c8"),
    ("Case 4 (Tall) 110x150", "#", 40, 220, 150, 370, "#f3e6c8"),
    ("Case 5 (S) 110x140", "#", 60, 600, 170, 740, "#f3e6c8"),
    ("Case 6 (Tall) 110x140", "#", 630, 600, 740, 740, "#f3e6c8"),
    ("Case 7 (S) 110x140", "#", 640, 330, 750, 470, "#f3e6c8"),
    ("Case 8 (S) 100x130", "#", 660, 150, 760, 280, "#f3e6c8"),
    ("Case 10 (hero) 200x70 on the platform", "#", 300, 1090, 500, 1160, "#f3e6c8"),
]
# (label, char, x, y)
POINTS = [
    ("1 Front-centre case: smoke bombs, paper tags, kunai + tag, stars", "1", 400, 270),
    ("2 Mid-centre case: folding fan (animated)", "2", 400, 540),
    ("3 Rear-centre case: Snow Flower drawn + empty sheath", "3", 400, 790),
    ("4 Cloak on a full mannequin", "4", 95, 295),
    ("5 Small weapons: kunai (+ future tanto etc.)", "5", 115, 670),
    ("6 Kasa with attire (mannequin)", "6", 685, 670),
    ("7 Snow Flower heels on tiers", "7", 695, 400),
    ("8 Shuriken assortment: six forms + spike", "8", 710, 215),
    ("10 Hero case: Snow Flower sheathed (drawn until the sheath exists)", "X", 400, 1125),
    ("Vase with plum branches", "W", 220, 1140),
    ("Vase with plum branches", "W", 580, 1140),
    ("Lantern", "L", 170, 990),
    ("Lantern", "L", 630, 990),
    ("Lantern", "L", 90, 60),
    ("Lantern", "L", 710, 60),
]
WINDOWS = [(525, 675), (825, 975)]  # high windows on both long walls, 150 wide, sill +350, head +440
DOOR = (325, 475)
PAINTING = (280, 520)  # original painting panel on the north wall, above the platform
# (id, x, y, heading_deg (0 = +Y, 90 = +X), label)
CAMERAS = [
    ("C1", 400, 40, 0, "entry reveal, +230, 24 mm (the armory3 view)"),
    ("C2", 400, 130, 0, "case 1 overhead, +220, 45 deg down, 35 mm"),
    ("C3", 400, 640, 0, "case 3 sword + sheath, 28 mm"),
    ("C5", 220, 620, 200, "cloak 3/4 from the north, 28 mm"),
    ("C6", 400, 400, 0, "fan fold, 85 mm"),
    ("C7", 540, 400, 90, "heels, 85 mm"),
    ("C8", 540, 560, 55, "kasa low 3/4, 50 mm"),
    ("C10", 400, 930, 0, "hero case 10, 40 mm"),
]


def ascii_plan():
    cw, rh = 25, 50  # one char = 25 cm across, one row = 50 cm along the axis
    cols, rows = W // cw, L // rh
    grid = [[" "] * cols for _ in range(rows)]

    def cell(x, y):
        c = min(cols - 1, max(0, int(x // cw)))
        r = min(rows - 1, max(0, rows - 1 - int(y // rh)))
        return r, c

    for _, ch, x0, y0, x1, y1, _f in RECTS:
        r1, c0 = cell(x0, y0 + 0.1)
        r0, c1 = cell(x1 - 0.1, y1 - 0.1)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                grid[r][c] = ch
    for _, ch, x, y in POINTS:
        r, c = cell(x, y)
        grid[r][c] = ch

    out = []
    out.append("            NORTH (painting wall)         one char = 25 cm across, one row = 50 cm along Y")
    out.append("      X: 0m      2m      4m      6m      8m")
    out.append("         +" + "-" * cols + "+   Y 12.0")
    for r in range(rows):
        y_top = L - r * rh
        y_bot = y_top - rh
        win = any(a < y_top and b > y_bot for a, b in WINDOWS)
        lw = "w" if win else "|"
        note = ""
        if y_bot == 1150:
            note = "  rear platform +60: X hero case 10, W vases, r corner racks"
        elif y_bot == 950:
            note = "  s steps (4 x 15 cm), L lanterns"
        elif y_bot == 800:
            note = "  w high windows (sill +350), 150 wide"
        elif y_bot == 0:
            note = "  . entry mat, L lanterns"
        label = f"{y_bot/100:4.1f}" if y_bot % 200 == 0 else "    "
        out.append(f"    {label} {lw}" + "".join(grid[r]) + f"{lw}{note}")
    door0, door1 = DOOR[0] // cw, DOOR[1] // cw
    bottom = "-" * door0 + " " * (door1 - door0) + "-" * (cols - door1)
    out.append("         +" + bottom + "+   Y 0.0  (door 1.5 m wide, X 3.25-4.75)")
    out.append(" " * (10 + (door0 + door1) // 2) + "^ C1 inside the door, +230, looking north")
    out.append("")
    out.append("Key: # glass case (number = display), 9 lit wall display panels, = rear platform,")
    out.append("s steps, r corner long-weapon racks, X hero case 10, W vase, L lantern, . entry mat.")
    out.append("1 bombs/tags/kunai/stars, 2 fan, 3 sword + sheath, 4 cloak, 5 small weapons, 6 kasa with attire,")
    out.append("7 heels, 8 shuriken assortment. Aisles between the side and centre cases are 130-150 cm.")
    return "\n".join(out)


def svg_plan():
    pad_l, pad_t = 180, 140
    sx = lambda x: pad_l + x
    sy = lambda y: pad_t + (L - y)
    vw, vh = 1760, 1560
    s = []
    a = s.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw//2}" height="{vh//2}" '
      'font-family="Segoe UI, Arial, sans-serif">')
    a('<title>Armory gallery layout v2, top-down</title>')
    a(f'<rect x="0" y="0" width="{vw}" height="{vh}" fill="#fbfaf7"/>')
    # walls and dark plank floor
    a(f'<rect x="{sx(-T)}" y="{sy(L+T)}" width="{W+2*T}" height="{L+2*T}" fill="#2b2320"/>')
    a(f'<rect x="{sx(0)}" y="{sy(L)}" width="{W}" height="{L}" fill="#5a4332"/>')
    # door gap
    a(f'<rect x="{sx(DOOR[0])}" y="{sy(0)}" width="{DOOR[1]-DOOR[0]}" height="{T}" fill="#fbfaf7"/>')
    a(f'<text x="{sx(400)}" y="{sy(-T)+26}" font-size="20" text-anchor="middle" fill="#333">door 150 x 200</text>')
    # windows
    for y0, y1 in WINDOWS:
        for x in (-T, W):
            a(f'<rect x="{sx(x)}" y="{sy(y1)}" width="{T}" height="{y1-y0}" fill="#9cc7e8"/>')
    # painting on the north wall
    a(f'<rect x="{sx(PAINTING[0])}" y="{sy(L)-8}" width="{PAINTING[1]-PAINTING[0]}" height="8" fill="#e8d9b5"/>')
    # 1 m grid
    for x in range(0, W + 1, 100):
        a(f'<line x1="{sx(x)}" y1="{sy(0)}" x2="{sx(x)}" y2="{sy(L)}" stroke="#7a6450" stroke-width="1" '
          'stroke-dasharray="3 6"/>')
    for y in range(0, L + 1, 100):
        a(f'<line x1="{sx(0)}" y1="{sy(y)}" x2="{sx(W)}" y2="{sy(y)}" stroke="#7a6450" stroke-width="1" '
          'stroke-dasharray="3 6"/>')
    # sun patches on the floor (east sun, 38 deg; tuned at G0)
    for y0, y1 in WINDOWS:
        a(f'<rect x="{sx(240)}" y="{sy(y1)}" width="120" height="{y1-y0}" fill="#f5c542" fill-opacity="0.25"/>')
    for label, _ch, x0, y0, x1, y1, fill in RECTS:
        a(f'<rect x="{sx(x0)}" y="{sy(y1)}" width="{x1-x0}" height="{y1-y0}" fill="{fill}" stroke="#1a1512" '
          'stroke-width="2" fill-opacity="0.95"/>')
    for label, ch, x, y in POINTS:
        a(f'<circle cx="{sx(x)}" cy="{sy(y)}" r="17" fill="#1f1f1f"/>')
        a(f'<text x="{sx(x)}" y="{sy(y)+7}" font-size="18" text-anchor="middle" fill="#ffffff" '
          f'font-weight="bold">{"10" if ch == "X" else ch}</text>')
    for cid, x, y, hd, label in CAMERAS:
        r = math.radians(hd)
        px, py = sx(x), sy(y)
        left = (px + math.sin(r - 0.45) * 60, py - math.cos(r - 0.45) * 60)
        right = (px + math.sin(r + 0.45) * 60, py - math.cos(r + 0.45) * 60)
        a(f'<polygon points="{px},{py} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}" '
          'fill="#e04a3a" fill-opacity="0.45" stroke="#e04a3a" stroke-width="1.5"/>')
        a(f'<circle cx="{px}" cy="{py}" r="7" fill="#e04a3a"/>')
        a(f'<text x="{px+10}" y="{py+26}" font-size="18" fill="#ffb4a8" font-weight="bold">{cid}</text>')
    for x in range(0, W + 1, 200):
        a(f'<text x="{sx(x)}" y="{sy(L+T)-14}" font-size="18" text-anchor="middle" fill="#555">{x//100} m</text>')
    for y in range(0, L + 1, 200):
        a(f'<text x="{sx(-T)-12}" y="{sy(y)+6}" font-size="18" text-anchor="end" fill="#555">Y {y//100} m</text>')
    a(f'<text x="{sx(400)}" y="44" font-size="28" text-anchor="middle" fill="#222" font-weight="bold">'
      'Armory gallery v2 (armory3) - top-down, interior 8.0 x 12.0 m, 1 m grid</text>')
    a(f'<text x="{sx(400)}" y="80" font-size="20" text-anchor="middle" fill="#555">North (rear platform) at top. '
      'Planning diagram only; every number is in ARMORY_PLAN.md.</text>')
    # legend
    lx, ly = sx(W) + 60, sy(L) + 20
    a(f'<text x="{lx}" y="{ly}" font-size="22" font-weight="bold" fill="#222">Key</text>')
    yy = ly + 34
    seen = set()
    for label, ch, _x, _y in POINTS:
        if label in seen:
            continue
        seen.add(label)
        a(f'<circle cx="{lx+14}" cy="{yy-7}" r="13" fill="#1f1f1f"/>')
        a(f'<text x="{lx+14}" y="{yy-1}" font-size="13" text-anchor="middle" fill="#fff" font-weight="bold">'
          f'{"10" if ch == "X" else ch}</text>')
        a(f'<text x="{lx+38}" y="{yy}" font-size="17" fill="#222">{label}</text>')
        yy += 30
    yy += 10
    for text, colour in [("pale = glass case on a black-lacquer plinth", "#8a6a2a"),
                         ("cream strip = lit wall display panels (9)", "#8a6a2a"),
                         ("blue = high window, sill +350", "#3b82b8"),
                         ("yellow = sun patch on the floor (tuned at G0)", "#a07a10")]:
        a(f'<text x="{lx}" y="{yy}" font-size="17" fill="{colour}">{text}</text>')
        yy += 28
    yy += 16
    a(f'<text x="{lx}" y="{yy}" font-size="22" font-weight="bold" fill="#222">Cameras</text>')
    yy += 30
    for cid, _x, _y, _h, label in CAMERAS:
        a(f'<text x="{lx}" y="{yy}" font-size="17" fill="#c0392b">{cid}: {label}</text>')
        yy += 26
    a('</svg>')
    return "\n".join(s)


if __name__ == "__main__":
    txt = ascii_plan()
    with open(os.path.join(HERE, "ARMORY_LAYOUT.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    with open(os.path.join(HERE, "ARMORY_LAYOUT.svg"), "w", encoding="utf-8") as f:
        f.write(svg_plan() + "\n")
    print(txt)
