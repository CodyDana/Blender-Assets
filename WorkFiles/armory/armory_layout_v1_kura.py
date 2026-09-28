"""Top-down layout of the armory (kura direction, single storey) for ARMORY_PLAN.md.

Planning aid only: writes ARMORY_LAYOUT.svg and ARMORY_LAYOUT.txt beside this script.
One data table drives both drawings, so they cannot disagree. Units are cm.
Frame: origin at the interior south-west corner at grade, X across (0-800), Y along the
axis (0-1200, north = +Y), Z up. The door is in the south wall; the sword is at the north end.
Run: py WorkFiles/armory/armory_layout.py
"""
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
W, L, T = 800, 1200, 30  # interior width, interior length, wall thickness

# (label, char, x0, y0, x1, y1, fill)
RECTS = [
    ("Doma (earth floor, grade 0)", ".", 0, 0, 800, 200, "#e8dcc4"),
    ("Airing platform 100x400x30 (top +80)", ":", 350, 300, 450, 700, "#f1e6cf"),
    ("Sanctum dais 300x100x25", "#", 250, 1100, 550, 1200, "#e9c9a8"),
    ("Tansu (dressing)", "t", 0, 900, 45, 990, "#d8c7aa"),
    ("Tansu (dressing)", "t", 755, 900, 800, 990, "#d8c7aa"),
    ("Step stone", "o", 362, 125, 438, 175, "#c9c3b8"),
    ("Cloak dais 100x100x25", "_", 0, 300, 100, 400, "#e9c9a8"),
    ("Fan plinth 60x60x90", "_", 710, 320, 770, 380, "#e9c9a8"),
    ("Heels plinth 60x50x75 + tiers", "_", 710, 525, 770, 575, "#e9c9a8"),
    ("Wall rail, kunai pegs (W)", "R", 0, 700, 12, 900, "#b5835a"),
    ("Wall rail, tag hooks + growth (E)", "R", 788, 700, 800, 900, "#b5835a"),
]
# (label, char, x, y)
POINTS = [
    ("P1 shuriken tray on bundai", "1", 400, 400),
    ("P2 kunai kake", "2", 400, 540),
    ("P3 sanbo, smoke-bomb trio", "3", 400, 670),
    ("P4 fuda stand, paper tags", "4", 400, 320),
    ("Cloak on form post", "C", 50, 350),
    ("Kasa on head-form post", "K", 60, 550),
    ("Fan stand (skeletal fan)", "F", 740, 350),
    ("Heels on red-cloth tiers", "H", 740, 550),
    ("Target post: kunai + tag pairing, embedded stars", "T", 120, 100),
    ("Snow Flower sword (upright)", "W", 340, 1150),
    ("Snow Flower sheath (upright)", "S", 460, 1150),
    ("Andon lantern", "a", 200, 1060),
]
GROWTH = [("W", 250), ("W", 450), ("W", 650), ("W", 1050), ("E", 250), ("E", 450), ("E", 650), ("E", 1050)]
WINDOWS = [(355, 445), (655, 745)]  # high windows on both long walls, sill +350, head +440
DOOR = (325, 475)
LINES = [("Lintel beam, underside +300", "=", 900), ("Step-up beam to plank floor +50", "-", 200)]
# (id, x, y, heading_deg (0 = +Y, 90 = +X), label)
CAMERAS = [
    ("C1", 400, -250, 0, "doors-open reveal, 35 mm"),
    ("C2", 400, 850, 180, "kit overhead, +420, 35 mm"),
    ("C3", 400, 710, 0, "sword + sheath, 50 mm, 4.4 m"),
    ("C4", 400, 250, 0, "platform macros, 100 mm"),
    ("C5", 560, 350, 270, "cloak, 50 mm"),
    ("C6", 630, 350, 90, "fan fold, 85 mm"),
    ("C7", 630, 550, 90, "heels, 85 mm"),
    ("C8", 170, 520, 270, "kasa low 3/4, 50 mm"),
    ("C10", 200, 160, 235, "target macro, 100 mm, 1 m"),
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
        if ch == ".":
            continue
        r1, c0 = cell(x0, y0 + 0.1)
        r0, c1 = cell(x1 - 0.1, y1 - 0.1)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                grid[r][c] = ch
    for _, ch, y in LINES:
        r, _c = cell(0, y)
        for c in range(cols):
            if grid[r][c] == " ":
                grid[r][c] = ch
    for side, y in GROWTH:
        r, c = cell(5 if side == "W" else W - 5, y)
        grid[r][c] = "g"
    for _, ch, x, y in POINTS:
        r, c = cell(x, y)
        grid[r][c] = ch

    out = []
    out.append("            NORTH (gable wall)            one char = 25 cm across, one row = 50 cm along Y")
    out.append("      X: 0m      2m      4m      6m      8m")
    out.append("         +" + "-" * cols + "+   Y 12.0")
    for r in range(rows):
        y_top = L - r * rh
        y_bot = y_top - rh
        win = any(a < y_top and b > y_bot for a, b in WINDOWS)
        lw = "w" if win else "|"
        note = ""
        if y_bot == 1100:
            note = "  sanctum: W sword, S sheath, # dais"
        elif y_bot == 900:
            note = "  = lintel beam (underside +300)"
        elif y_bot == 700 and False:
            note = ""
        elif y_bot == 650:
            note = "  w high windows (sill +350)"
        elif y_bot == 200:
            note = "  - step-up to the plank floor (+50)"
        elif y_bot == 0:
            note = "  doma, earth floor at grade"
        label = f"{y_bot/100:4.1f}" if y_bot % 200 == 0 else "    "
        out.append(f"    {label} {lw}" + "".join(grid[r]) + f"{lw}{note}")
    door0, door1 = DOOR[0] // cw, DOOR[1] // cw
    bottom = "-" * door0 + " " * (door1 - door0) + "-" * (cols - door1)
    out.append("         +" + bottom + "+   Y 0.0  (door 1.5 m wide, X 3.25-4.75)")
    out.append(" " * (10 + (door0 + door1) // 2) + "^ C1 at Y -2.5, looking north")
    out.append("")
    out.append("Key: 1 shuriken tray, 2 kunai kake, 3 smoke-bomb sanbo, 4 tag fuda stand (all on the")
    out.append(":: airing platform); C cloak, K kasa, F fan, H heels, T target post, W sword, S sheath,")
    out.append("a andon, t tansu, R wall rail, g free growth bay, _ dais or plinth, o step stone.")
    return "\n".join(out)


def svg_plan():
    pad_l, pad_t = 260, 140
    sx = lambda x: pad_l + x
    sy = lambda y: pad_t + (L - y)
    vw, vh = 1560, 1760
    s = []
    a = s.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw//2}" height="{vh//2}" '
      'font-family="Segoe UI, Arial, sans-serif">')
    a('<title>Armory layout, kura direction, top-down</title>')
    a(f'<rect x="0" y="0" width="{vw}" height="{vh}" fill="#fbfaf7"/>')
    # walls
    a(f'<rect x="{sx(-T)}" y="{sy(L+T)}" width="{W+2*T}" height="{L+2*T}" fill="#8b857c"/>')
    a(f'<rect x="{sx(0)}" y="{sy(L)}" width="{W}" height="{L}" fill="#f6f1e6"/>')
    # door gap
    a(f'<rect x="{sx(DOOR[0])}" y="{sy(0)}" width="{DOOR[1]-DOOR[0]}" height="{T}" fill="#fbfaf7"/>')
    a(f'<text x="{sx(400)}" y="{sy(-T)+26}" font-size="20" text-anchor="middle" fill="#333">door 150 x 200</text>')
    # windows
    for y0, y1 in WINDOWS:
        for x in (-T, W):
            a(f'<rect x="{sx(x)}" y="{sy(y1)}" width="{T}" height="{y1-y0}" fill="#9cc7e8"/>')
    # 1 m grid
    for x in range(0, W + 1, 100):
        a(f'<line x1="{sx(x)}" y1="{sy(0)}" x2="{sx(x)}" y2="{sy(L)}" stroke="#d9d2c3" stroke-width="1"/>')
    for y in range(0, L + 1, 100):
        a(f'<line x1="{sx(0)}" y1="{sy(y)}" x2="{sx(W)}" y2="{sy(y)}" stroke="#d9d2c3" stroke-width="1"/>')
    for label, _ch, x0, y0, x1, y1, fill in RECTS:
        a(f'<rect x="{sx(x0)}" y="{sy(y1)}" width="{x1-x0}" height="{y1-y0}" fill="{fill}" stroke="#7a6a55" '
          'stroke-width="1.5" fill-opacity="0.9"/>')
    # truss lines (every 200 cm) dashed, lines
    for y in range(200, L, 200):
        a(f'<line x1="{sx(0)}" y1="{sy(y)}" x2="{sx(W)}" y2="{sy(y)}" stroke="#b9ad98" stroke-width="1.5" '
          'stroke-dasharray="4 10"/>')
    for label, _ch, y in LINES:
        a(f'<line x1="{sx(0)}" y1="{sy(y)}" x2="{sx(W)}" y2="{sy(y)}" stroke="#5b3f26" stroke-width="7"/>')
        a(f'<text x="{sx(W)+50}" y="{sy(y)+7}" font-size="20" fill="#333">{label}</text>')
    # sun shafts from east windows onto the platform
    for y0, y1 in WINDOWS:
        yc = (y0 + y1) / 2
        a(f'<polygon points="{sx(W)},{sy(y0)} {sx(W)},{sy(y1)} {sx(345)},{sy(y1)} {sx(345)},{sy(y0)}" '
          'fill="#f5c542" fill-opacity="0.18"/>')
        a(f'<text x="{sx(520)}" y="{sy(yc)+6}" font-size="16" fill="#a07a10" text-anchor="start">sun shaft, 38 deg</text>')
    # growth bays
    for side, y in GROWTH:
        x = 18 if side == "W" else W - 18
        a(f'<circle cx="{sx(x)}" cy="{sy(y)}" r="14" fill="none" stroke="#3a7d44" stroke-width="3" stroke-dasharray="5 4"/>')
        a(f'<text x="{sx(x)}" y="{sy(y)+6}" font-size="16" text-anchor="middle" fill="#3a7d44">g</text>')
    for label, ch, x, y in POINTS:
        a(f'<circle cx="{sx(x)}" cy="{sy(y)}" r="17" fill="#1f1f1f"/>')
        a(f'<text x="{sx(x)}" y="{sy(y)+7}" font-size="20" text-anchor="middle" fill="#ffffff" '
          f'font-weight="bold">{ch}</text>')
    for cid, x, y, hd, label in CAMERAS:
        r = math.radians(hd)
        dx, dy = math.sin(r), math.cos(r)
        px, py = sx(x), sy(y)
        tip = (px + dx * 34, py - dy * 34)
        left = (px + math.sin(r - 0.45) * 60, py - math.cos(r - 0.45) * 60)
        right = (px + math.sin(r + 0.45) * 60, py - math.cos(r + 0.45) * 60)
        a(f'<polygon points="{px},{py} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}" '
          'fill="#c0392b" fill-opacity="0.35" stroke="#c0392b" stroke-width="1.5"/>')
        a(f'<circle cx="{px}" cy="{py}" r="7" fill="#c0392b"/>')
        a(f'<text x="{px+10}" y="{py+26}" font-size="18" fill="#c0392b" font-weight="bold">{cid}</text>')
    # axis scale labels
    for x in range(0, W + 1, 200):
        a(f'<text x="{sx(x)}" y="{sy(L+T)-14}" font-size="18" text-anchor="middle" fill="#555">{x//100} m</text>')
    for y in range(0, L + 1, 200):
        a(f'<text x="{sx(-T)-12}" y="{sy(y)+6}" font-size="18" text-anchor="end" fill="#555">Y {y//100} m</text>')
    a(f'<text x="{sx(400)}" y="44" font-size="28" text-anchor="middle" fill="#222" font-weight="bold">'
      'Armory (kura, single storey) - top-down, interior 8.0 x 12.0 m, 1 m grid</text>')
    a(f'<text x="{sx(400)}" y="80" font-size="20" text-anchor="middle" fill="#555">North (sword) at top. '
      'Planning diagram only; every number is in ARMORY_PLAN.md.</text>')
    # legend
    lx, ly = sx(W) + 50, sy(L) + 20
    a(f'<text x="{lx}" y="{ly}" font-size="22" font-weight="bold" fill="#222">Key</text>')
    yy = ly + 34
    for label, ch, _x, _y in POINTS:
        a(f'<circle cx="{lx+14}" cy="{yy-7}" r="13" fill="#1f1f1f"/>')
        a(f'<text x="{lx+14}" y="{yy-1}" font-size="16" text-anchor="middle" fill="#fff" font-weight="bold">{ch}</text>')
        a(f'<text x="{lx+38}" y="{yy}" font-size="18" fill="#222">{label}</text>')
        yy += 32
    yy += 10
    a(f'<text x="{lx}" y="{yy}" font-size="18" fill="#3a7d44">g = free growth bay (8 marked + platform segments)</text>')
    yy += 30
    a(f'<text x="{lx}" y="{yy}" font-size="18" fill="#3b82b8">blue = high barred window, sill +350</text>')
    yy += 30
    a(f'<text x="{lx}" y="{yy}" font-size="18" fill="#7a6a55">dashed = roof truss every 2 m</text>')
    yy += 40
    a(f'<text x="{lx}" y="{yy}" font-size="22" font-weight="bold" fill="#222">Cameras</text>')
    yy += 32
    for cid, _x, _y, _h, label in CAMERAS:
        a(f'<text x="{lx}" y="{yy}" font-size="18" fill="#c0392b">{cid}: {label}</text>')
        yy += 28
    a('</svg>')
    return "\n".join(s)


if __name__ == "__main__":
    txt = ascii_plan()
    with open(os.path.join(HERE, "ARMORY_LAYOUT.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    with open(os.path.join(HERE, "ARMORY_LAYOUT.svg"), "w", encoding="utf-8") as f:
        f.write(svg_plan() + "\n")
    print(txt)
