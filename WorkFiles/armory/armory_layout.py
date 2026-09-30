"""Top-down layout of the armory gallery (v2, building stage 2026-09-27; r20 2026-09-28: 12.0 x 20.0 m interior) for
ARMORY_PLAN.md.

Planning aid only: writes ARMORY_LAYOUT.svg and ARMORY_LAYOUT.txt beside this script.
It draws the BUILD itself: every footprint comes from WorkFiles/armory/build/layout.json (written by
Scripts/armory/build_armory_kit.py: instance world bounding boxes, cases, openings, sun, cameras), so the drawing and the
kit cannot disagree. Rebuild the kit, then rerun this script.
Frame: metres; origin at the interior south-west corner at floor level, X across (0-12), Y along the axis (0-20,
north = +Y), Z up. The 4 m entrance is in the south wall; the rear dais (a lit flight to the +0.90 deck) is at the
north end. The room size is read from layout.json, nothing here assumes a length.
Earlier layouts: armory_layout_v2_8x12.py (the 8 x 12 m v2 table), armory_layout_v1_kura.py.
Run: "C:/Program Files/Blender Foundation/Blender 5.2/5.2/python/bin/python.exe" WorkFiles/armory/armory_layout.py
     [--layout <test copy>/layout.json --out <dir>]   (r20: draw a test copy without touching the live drawings)
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_A = sys.argv[1:]
LAYOUT = _A[_A.index("--layout") + 1] if "--layout" in _A else os.path.join(HERE, "build", "layout.json")
OUT_DIR = _A[_A.index("--out") + 1] if "--out" in _A else HERE
DATA = json.load(open(LAYOUT, encoding="utf-8"))
ROOM = DATA["room"]
W, L, T = ROOM["width_x"], ROOM["length_y"], 0.30
OP = DATA["openings"]
DOOR = OP["door_x"]

# what the user plans to show in each case (items are added later, one by one; the build keeps every case EMPTY)
CONTENT = {
    "1": "front-centre: smoke bombs, paper tags, kunai + tag, stars",
    "2": "mid-centre: folding fan",
    "3": "rear-centre: Snow Flower drawn + empty sheath",
    "4": "cloak on a full mannequin",
    "5": "small weapons: kunai (+ future tanto etc.)",
    "6": "kasa with attire (mannequin)",
    "7": "Snow Flower heels on tiers",
    "8": "shuriken assortment: six forms + spike",
    "10": "hero (table on the platform): Snow Flower sheathed",
    "G1": "growth slot (empty)", "G2": "growth slot (empty)", "G3": "growth slot (empty)",
    "G4": "growth slot (empty)", "G5": "growth slot (empty)",   # r19 b: the near cases of the rear tall pairs
}

# piece prefix -> (ascii char, svg fill, legend text); first match wins; None = not drawn
KINDS = [
    ("SM_AK_Case_", ("#", "#f3e6c8", "glass case on a black-lacquer plinth / hero table")),
    ("SM_AK_Platform", ("=", "#8a6a4a", "rear platform (wings and deck), top +0.90 (r20)")),
    ("SM_AK_Steps", ("s", "#a0825f", "steps: one even flight, 6 risers x 15 cm (0.35 m going) to the +0.90 deck, an LED nosing on every riser (r20 fix round)")),
    ("SM_AK_WallPanel_Lit", ("9", "#a68d69", "wide wall display bay (1.85 m, r20 round 3) over a dark dado (counter +0.85): lit cream back, two downlights at the head, empty")),
    ("SM_AK_RearAlcove", ("r", "#d9b36a", "rear alcove: top-lit dark back board, empty upright rack, tansu, lattice above")),
    ("SM_AK_RearScreen", ("p", "#6b5d4d", "dark patterned screen")),
    ("SM_AK_PaintingPanel", ("P", "#efe2c2", "painted panel (ink pine), 2.4 x 2.3 m, glowing border")),
    ("SM_AK_LanternPedestal", ("n", "#3a2e25", "slim newel post at the stair foot (0.85 m, 0.30 m top plate)")),
    ("SM_AK_H_NewelLantern", ("l", "#ffd98a", "small lantern on the newel (hero, 0.32 m, +0.87)")),
    ("SM_AK_Lantern", ("L", "#ffd98a", "paper floor lantern")),
    ("SM_AK_Vase_Plum_L", ("W", "#b0202a", "black vase, red plum branches")),
    ("SM_AK_Vase_Plum_S", ("v", "#b0202a", "sill vase, red plum branches (+2.64)")),
    ("SM_AK_SillCaddy", ("c", "#806040", "tea caddy on the sill")),
    ("SM_AK_Banner", ("B", "#111111", "black banner with the gold emblem")),
    ("SM_AK_Post_Heavy", ("o", "#1a1512", "heavy 30 cm post (platform front)")),
    ("SM_AK_Post_Jamb", ("o", "#1a1512", "45 cm jamb post with iron straps (f2: the vestibule posts at Y 1.02)")),
    ("SM_AK_Post_LED", ("o", "#1a1512", "post with LED edge lines")),
    ("SM_AK_EmblemDisc", ("e", "#c9a057", "the user's emblem on the top (6th) riser (f1; r20 fix round)")),
    ("SM_AK_EntryMat", (".", "#cdbb95", "woven rush runner")),
    ("SM_AK_EntryStep", ("_", "#3a2e25", "raised entry step beam")),
    ("SM_AK_Threshold", ("_", "#3a2e25", "threshold beam")),
    ("SM_AK_DoorLeaf", ("d", "#5b4636", "sliding door leaf, parked open")),
    ("SM_AK_SillLedge", None), ("SM_AK_Post_", None), ("SM_AK_Floor", None), ("SM_AK_Ceiling", None),
    ("SM_AK_Wall", None), ("SM_AK_Corner", None), ("SM_AK_Window", None), ("SM_AK_Ext_", None),
    ("SM_AK_Entrance", None),
]

# exterior stage (2026-09-27): the courtyard garden south of the entrance, drawn as a separate site plan (ARMORY_SITE.*)
SITE_KINDS = [
    ("SM_AKX_Court_Gravel", None), ("SM_AKX_Ground_Field", None), ("SM_AKX_Roof", None), ("SM_AKX_TreeLine", None),
    ("SM_AKX_Hills", None), ("SM_AKX_Mountains", None), ("SM_AKX_Facade", None), ("SM_AKX_Foundation", None),
    ("SM_AKX_RakeRing", ("o", "#d9d3c4", "raked rings round the moss mounds")),
    ("SM_AKX_MossMound", ("m", "#6f8a3a", "moss mound")),
    ("SM_AKX_Rock", ("R", "#8e8980", "rock")),
    ("SM_AKX_Shrub", ("h", "#3f5e1d", "clipped shrub (karikomi)")),
    ("SM_AKX_StoneLantern", ("T", "#b5b0a6", "stone lantern (toro)")),
    ("SM_AKX_Tsukubai", ("U", "#7d7244", "stone basin with bamboo spout (tsukubai)")),
    ("SM_AKX_Landing", ("=", "#a9a49a", "cut-granite landing")),
    ("SM_AKX_PathSlab", ("=", "#a9a49a", "ishidatami path strip")),
    ("SM_AKX_StepStone", ("s", "#8e8980", "stepping stone")),
    ("SM_AKX_Pine", ("P", "#2c4a1c", "Japanese black pine (trunk; pads spread about 2 m)")),
    ("SM_AKX_MapleRed", ("M", "#b3211a", "red maple (trunk)")),
    ("SM_AKX_MapleGreen", ("G", "#557a22", "green maple (trunk)")),
    ("SM_AKX_Gate", ("^", "#2b2320", "roofed gate, 2.38 m clear")),
    ("SM_AKX_Wall", ("#", "#d8cdb8", "plaster wall on a stone base, tiled coping")),
]
SITE = (-5.0, 17.0, -14.0, 17.0)   # X0, X1, Y0, Y1 of the site drawings


def site_kind(piece):
    for pre, k in SITE_KINDS:
        if piece.startswith(pre):
            return k
    return None


SITE_ITEMS = []
for inst in DATA["instances"]:
    k = site_kind(inst["piece"])
    if k is None:
        continue
    b = inst["bbox_min_max"]
    if inst["piece"].startswith(("SM_AKX_Pine", "SM_AKX_Maple")):   # trees: the trunk, not the canopy
        x, y = inst["loc"][0], inst["loc"][1]
        b = [x - 0.25, y - 0.25, 0, x + 0.25, y + 0.25, 0]
    SITE_ITEMS.append((inst["piece"], k, b[0], b[1], b[3], b[4]))


def kind(piece):
    for pre, k in KINDS:
        if piece.startswith(pre):
            return k
    return None


ITEMS = []   # (piece, kind, x0, y0, x1, y1)
for inst in DATA["instances"]:
    k = kind(inst["piece"])
    if k is None:
        continue
    b = inst["bbox_min_max"]
    ITEMS.append((inst["piece"], k, b[0], b[1], b[3], b[4]))
CASES = [(c["label"], c["type"], c["loc"][0], c["loc"][1]) for c in DATA["cases"]]
SUNS = [L for L in DATA["lights"] if L["type"] == "sun"]   # f2: the sun and the interior window fill
SUN = SUNS[0]
CAMS = DATA["cameras"]


def sun_patches(sun=None):
    """Floor footprint of the sun through each open window (the 4 corners of the clear opening projected along the
    sun's travel direction onto z = 0). Only the west wall faces the sun."""
    dx, dy, dz = (sun or SUN)["travel_dir"]
    closed = [tuple(w) for w in OP.get("west_closed_windows_y", [])]
    polys = []
    for (y0, y1) in OP["windows_y"]:
        if (y0, y1) in closed:
            continue
        pts = []
        for (y, z) in ((y0, OP["window_z"][0]), (y1, OP["window_z"][0]), (y1, OP["window_z"][1]),
                       (y0, OP["window_z"][1])):
            t = -z / dz
            pts.append((0.0 + dx * t, y + dy * t))
        polys.append(pts)
    return polys


def ascii_plan():
    cw, rh = 0.25, 0.50   # one char = 25 cm across, one row = 50 cm along the axis
    cols, rows = int(W / cw), int(L / rh)
    grid = [[" "] * cols for _ in range(rows)]

    def cell(x, y):
        c = min(cols - 1, max(0, int(x // cw)))
        r = min(rows - 1, max(0, rows - 1 - int(y // rh)))
        return r, c

    order = sorted(ITEMS, key=lambda it: (it[1][0] in "=", ), reverse=True)   # platform first, then the rest on top
    for piece, k, x0, y0, x1, y1 in order:
        r1, c0 = cell(x0 + 0.01, y0 + 0.01)
        r0, c1 = cell(x1 - 0.01, y1 - 0.01)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                grid[r][c] = k[0]
    for lab, _t, x, y in CASES:
        r, c = cell(x, y)
        for i, ch in enumerate(lab):
            if c + i < cols:
                grid[r][c + i] = ch
    closed = [tuple(w) for w in OP.get("west_closed_windows_y", [])]
    out = [f"            NORTH (painting wall)     interior {W:.1f} x {L:.1f} m; one char = 25 cm across, one row = 50 cm",
           "      X: 0m      2m      4m      6m      8m      10m     12m",
           "         +" + "-" * cols + f"+   Y {L:.1f}"]
    for r in range(rows):
        y_top = L - r * rh
        y_bot = y_top - rh
        win = [w for w in OP["windows_y"] if w[0] < y_top and w[1] > y_bot]
        lw = ("k" if tuple(win[0]) in closed else "w") if win else "|"
        rw = "w" if win else "|"
        label = f"{y_bot:4.1f}" if abs(y_bot % 2) < 1e-6 else "    "
        out.append(f"    {label} {lw}" + "".join(grid[r]) + f"{rw}")
    d0, d1 = int(DOOR[0] / cw), int(DOOR[1] / cw)
    out.append("         +" + "-" * d0 + " " * (d1 - d0) + "-" * (cols - d1) +
               f"+   Y 0.0  (entrance {DOOR[1]-DOOR[0]:.1f} m wide x {OP['door_z'][1]:.2f} m, X {DOOR[0]:.1f}-{DOOR[1]:.1f})")
    c1 = next(c for c in CAMS if c["name"] == "C1_EntryReveal")
    out.append(" " * (10 + (d0 + d1) // 2) + f"^ C1 at Y {c1['loc'][1]:.2f}, +{c1['loc'][2]:.2f}, {c1['lens_mm']} mm, "
               "looking north")
    out.append("")
    out.append("Key: # case (label = display number; G = empty growth slot), = rear platform +0.90, s steps,")
    out.append("9 wall bays (dado, lit cream back), r rear alcoves (empty upright racks), p dark screens, P painting, B banners,")
    out.append("L lanterns, W / v vases with plum branches (floor / sill), c sill caddies, o heavy / LED posts, . runner, _ step / threshold beams,")
    out.append("d sliding door leaves (parked open), w lattice windows (sill +2.65, 3.5 x 1.45 m in 4 m bays, r20 round 3) with a sill ledge,")
    out.append("e the user's emblem on the top riser; the two o at Y 1.0 are the 45 cm jamb posts (f2)."
               + (" k west window closed with a lit shoji pane." if OP.get("west_closed_windows_y") else ""))
    out.append("")
    out.append("Cases (EMPTY in the build; planned content):")
    for lab, t, x, y in CASES:
        c = next(cc for cc in DATA["cases"] if cc["label"] == lab)
        wd = c["width_depth_plinth_glass_m"]
        out.append(f"  {lab:>3} {t:<5} at X {x:5.2f}, Y {y:5.2f}, {wd[0]:.2f} x {wd[1]:.2f} m, plinth {wd[2]:.2f}, "
                   f"glass {wd[3]:.2f}: {CONTENT.get(lab, '')}")
    return "\n".join(out)


def svg_plan():
    S = 60   # px per metre
    pad_l, pad_t = 110, 120
    sx = lambda x: pad_l + x * S
    sy = lambda y: pad_t + (L - y) * S
    vw, vh = int(pad_l + (W + 0.6) * S + 620), int(pad_t + (L + 1.2) * S + 60)
    s = []
    a = s.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw}" height="{vh}" '
      'font-family="Segoe UI, Arial, sans-serif">')
    a('<title>Armory gallery layout, top-down</title>')
    a(f'<rect x="0" y="0" width="{vw}" height="{vh}" fill="#fbfaf7"/>')
    a(f'<rect x="{sx(-T)}" y="{sy(L+T)}" width="{(W+2*T)*S}" height="{(L+2*T)*S}" fill="#2b2320"/>')
    a(f'<rect x="{sx(0)}" y="{sy(L)}" width="{W*S}" height="{L*S}" fill="#5a4332"/>')
    a(f'<rect x="{sx(DOOR[0])}" y="{sy(0)}" width="{(DOOR[1]-DOOR[0])*S}" height="{T*S}" fill="#fbfaf7"/>')
    a(f'<text x="{sx(W/2)}" y="{sy(-T)+26}" font-size="18" text-anchor="middle" fill="#333">entrance '
      f'{DOOR[1]-DOOR[0]:.1f} x {OP["door_z"][1]:.2f} m</text>')
    closed = [tuple(w) for w in OP.get("west_closed_windows_y", [])]
    for y0, y1 in OP["windows_y"]:
        for x, wall in ((-T, "W"), (W, "E")):
            fill = "#e8d9b5" if (wall == "W" and (y0, y1) in closed) else "#9cc7e8"
            a(f'<rect x="{sx(x)}" y="{sy(y1)}" width="{T*S}" height="{(y1-y0)*S}" fill="{fill}"/>')
    for x in range(0, int(W) + 1):
        a(f'<line x1="{sx(x)}" y1="{sy(0)}" x2="{sx(x)}" y2="{sy(L)}" stroke="#7a6450" stroke-width="1" '
          'stroke-dasharray="3 6"/>')
    for y in range(0, int(L) + 1):
        a(f'<line x1="{sx(0)}" y1="{sy(y)}" x2="{sx(W)}" y2="{sy(y)}" stroke="#7a6450" stroke-width="1" '
          'stroke-dasharray="3 6"/>')
    for poly in [q for sun in SUNS for q in sun_patches(sun)]:
        pts = " ".join(f"{sx(max(0, min(W, x))):.1f},{sy(max(0, min(L, y))):.1f}" for x, y in poly)
        a(f'<polygon points="{pts}" fill="#f5c542" fill-opacity="0.30"/>')
    order = sorted(ITEMS, key=lambda it: (it[1][0] in "=", ), reverse=True)
    for piece, k, x0, y0, x1, y1 in order:
        a(f'<rect x="{sx(x0):.1f}" y="{sy(y1):.1f}" width="{(x1-x0)*S:.1f}" height="{(y1-y0)*S:.1f}" fill="{k[1]}" '
          'stroke="#1a1512" stroke-width="1.2" fill-opacity="0.95"/>')
    for lab, _t, x, y in CASES:
        a(f'<circle cx="{sx(x)}" cy="{sy(y)}" r="15" fill="#1f1f1f"/>')
        a(f'<text x="{sx(x)}" y="{sy(y)+6}" font-size="15" text-anchor="middle" fill="#ffffff" '
          f'font-weight="bold">{lab}</text>')
    for c in CAMS:
        if c["loc"][1] < -1.5:   # exterior cameras are drawn on the site plan
            continue
        (x, y, _z), (tx, ty, _tz) = c["loc"], c["look_at"]
        hd = math.atan2(tx - x, ty - y)
        px, py = sx(x), sy(y)
        left = (px + math.sin(hd - 0.45) * 50, py - math.cos(hd - 0.45) * 50)
        right = (px + math.sin(hd + 0.45) * 50, py - math.cos(hd + 0.45) * 50)
        a(f'<polygon points="{px:.1f},{py:.1f} {left[0]:.1f},{left[1]:.1f} {right[0]:.1f},{right[1]:.1f}" '
          'fill="#e04a3a" fill-opacity="0.45" stroke="#e04a3a" stroke-width="1.5"/>')
        a(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="#e04a3a"/>')
        a(f'<text x="{px+8:.1f}" y="{py+22:.1f}" font-size="15" fill="#ffb4a8" font-weight="bold">'
          f'{c["name"].split("_")[0]}</text>')
    for x in range(0, int(W) + 1, 2):
        a(f'<text x="{sx(x)}" y="{sy(L+T)-12}" font-size="16" text-anchor="middle" fill="#555">{x} m</text>')
    for y in range(0, int(L) + 1, 2):
        a(f'<text x="{sx(-T)-10}" y="{sy(y)+6}" font-size="16" text-anchor="end" fill="#555">Y {y} m</text>')
    a(f'<text x="{pad_l}" y="40" font-size="26" fill="#222" font-weight="bold">'
      f'Armory gallery - top-down, interior {W:.1f} x {L:.1f} m, 1 m grid</text>')
    a(f'<text x="{pad_l}" y="74" font-size="17" fill="#555">North (rear platform) at top. Drawn from build/layout.json '
      '(the kit as built). Cases are EMPTY; numbers are planned displays.</text>')
    lx, ly = sx(W) + 50, sy(L) + 10
    a(f'<text x="{lx}" y="{ly}" font-size="20" font-weight="bold" fill="#222">Key</text>')
    yy = ly + 30
    seen = set()
    for _pre, k in KINDS:
        if k is None or k[2] in seen:
            continue
        seen.add(k[2])
        a(f'<rect x="{lx}" y="{yy-13}" width="18" height="16" fill="{k[1]}" stroke="#1a1512"/>')
        a(f'<text x="{lx+26}" y="{yy}" font-size="15" fill="#222">{k[2]}</text>')
        yy += 24
    for text, colour in [("blue = lattice window 3.5 x 1.45 m, sill +2.65 (both long walls)", "#3b82b8"),
                         ("cream on the west wall = window closed with a lit shoji pane", "#8a6a2a"),
                         ("yellow = sun patches from the west windows: " + ", ".join(
                             f"{L['name']} {L['elev_deg']:.0f} deg up, heading {L['heading_deg_from_x_toward_minus_y']:.0f}"
                             for L in SUNS), "#a07a10")]:
        a(f'<text x="{lx}" y="{yy}" font-size="15" fill="{colour}">{text}</text>')
        yy += 24
    yy += 12
    a(f'<text x="{lx}" y="{yy}" font-size="20" font-weight="bold" fill="#222">Cases (planned content)</text>')
    yy += 26
    for lab, t, _x, _y in CASES:
        a(f'<text x="{lx}" y="{yy}" font-size="14" fill="#222">{lab} ({t}): {CONTENT.get(lab, "")}</text>')
        yy += 21
    yy += 12
    a(f'<text x="{lx}" y="{yy}" font-size="20" font-weight="bold" fill="#222">Cameras</text>')
    yy += 26
    for c in CAMS:
        a(f'<text x="{lx}" y="{yy}" font-size="14" fill="#c0392b">{c["name"]}: +{c["loc"][2]:.2f} m, '
          f'{c["lens_mm"]} mm</text>')
        yy += 21
    a('</svg>')
    return "\n".join(s)


def site_ascii():
    """The courtyard garden (one char = 50 cm, one row = 50 cm); the hall's south wall at the top."""
    X0, X1, Y0, _Y1 = SITE
    Y1 = 1.0
    cw = rh = 0.5
    cols, rows = int((X1 - X0) / cw), int((Y1 - Y0) / rh)
    grid = [[" "] * cols for _ in range(rows)]

    def cell(x, y):
        return (min(rows - 1, max(0, rows - 1 - int((y - Y0) // rh))), min(cols - 1, max(0, int((x - X0) // cw))))

    for r in range(rows):   # the hall (Y > -0.3), open at the entrance
        for c in range(cols):
            x, y = X0 + (c + 0.5) * cw, Y1 - (r + 0.5) * rh
            if -0.3 < y and -0.3 < x < W + 0.3:
                grid[r][c] = "|" if not (DOOR[0] < x < DOOR[1]) else " "
    for _p, k, x0, y0, x1, y1 in sorted(SITE_ITEMS, key=lambda it: 0 if it[1][0] == "o" else 1):
        r1, c0 = cell(x0 + 0.01, y0 + 0.01)
        r0, c1 = cell(x1 - 0.01, y1 - 0.01)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                grid[r][c] = k[0]
    ps = DATA.get("player_start")
    if ps:
        r, c = cell(ps["loc"][0], ps["loc"][1])
        grid[r][c] = "@"
    for cam in CAMS:
        if cam["loc"][1] < -1.5:
            r, c = cell(cam["loc"][0], cam["loc"][1])
            grid[r][c] = "C"
    out = [f"    COURTYARD south of the entrance, X {X0:.0f}..{X1:.0f} m (1 char = 50 cm); the hall is at the top",
           "         +" + "-" * cols + "+"]
    for r in range(rows):
        y = Y1 - r * rh - rh
        lab = f"{y:5.1f}" if abs(y % 2) < 1e-6 else "     "
        out.append(f"   {lab} |" + "".join(grid[r]) + "|")
    out.append("         +" + "-" * cols + "+")
    out.append("          X " + "".join(f"{int(X0 + i * cw):<4d}" if i % 4 == 0 else "" for i in range(cols)))
    out.append("")
    seen, keys = set(), []
    for _pre, k in SITE_KINDS:
        if k and k[2] not in seen:
            seen.add(k[2])
            keys.append(f"{k[0]} {k[2]}")
    out.append("Key: " + "; ".join(keys) + "; @ PlayerStart (facing the entrance); C camera CG_Garden; | the hall.")
    return "\n".join(out)


def site_svg():
    X0, X1, Y0, Y1 = SITE
    S = 36
    pad = 60
    sx = lambda x: pad + (x - X0) * S   # noqa: E731
    sy = lambda y: pad + 40 + (Y1 - y) * S   # noqa: E731
    vw, vh = int(2 * pad + (X1 - X0) * S + 420), int(pad + 80 + (Y1 - Y0) * S)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" width="{vw}" height="{vh}" '
         'font-family="Segoe UI, Arial, sans-serif">', '<title>Armory site plan, courtyard garden</title>',
         f'<rect x="0" y="0" width="{vw}" height="{vh}" fill="#fbfaf7"/>',
         f'<text x="{pad}" y="36" font-size="22" font-weight="bold" fill="#222">Armory site: the courtyard garden '
         'south of the entrance (1 m grid), drawn from build/layout.json</text>']
    a = s.append
    cx0, cx1, cy0, cy1 = DATA["exterior"]["courtyard_x0_x1_y0_y1"]
    a(f'<rect x="{sx(X0)}" y="{sy(Y1)}" width="{(X1-X0)*S}" height="{(Y1-Y0)*S}" fill="#8fa36a"/>')
    a(f'<rect x="{sx(cx0)}" y="{sy(cy1)}" width="{(cx1-cx0)*S}" height="{(cy1-cy0)*S}" fill="#ebe6da"/>')
    a(f'<rect x="{sx(-T)}" y="{sy(L+T)}" width="{(W+2*T)*S}" height="{(L+2*T)*S}" fill="#2b2320"/>')
    a(f'<rect x="{sx(0)}" y="{sy(L)}" width="{W*S}" height="{L*S}" fill="#5a4332"/>')
    a(f'<rect x="{sx(DOOR[0])}" y="{sy(0)}" width="{(DOOR[1]-DOOR[0])*S}" height="{T*S}" fill="#ebe6da"/>')
    a(f'<text x="{sx(W/2)}" y="{sy(L/2)}" font-size="20" text-anchor="middle" fill="#f3e6c8">the hall '
      f'{W:.0f} x {L:.0f} m (roof eaves 1 m out)</text>')
    for x in range(int(X0), int(X1) + 1):
        a(f'<line x1="{sx(x)}" y1="{sy(Y0)}" x2="{sx(x)}" y2="{sy(Y1)}" stroke="#5a5a4a" stroke-opacity="0.18"/>')
    for y in range(int(Y0), int(Y1) + 1):
        a(f'<line x1="{sx(X0)}" y1="{sy(y)}" x2="{sx(X1)}" y2="{sy(y)}" stroke="#5a5a4a" stroke-opacity="0.18"/>')
    for _p, k, x0, y0, x1, y1 in sorted(SITE_ITEMS, key=lambda it: 0 if it[1][0] == "o" else 1):
        a(f'<rect x="{sx(x0):.1f}" y="{sy(y1):.1f}" width="{(x1-x0)*S:.1f}" height="{(y1-y0)*S:.1f}" fill="{k[1]}" '
          'stroke="#1a1512" stroke-width="0.8"/>')
    ps = DATA.get("player_start")
    if ps:
        a(f'<circle cx="{sx(ps["loc"][0])}" cy="{sy(ps["loc"][1])}" r="9" fill="#2a7de1"/>')
        a(f'<text x="{sx(ps["loc"][0])+14}" y="{sy(ps["loc"][1])+5}" font-size="14" fill="#2a7de1">PlayerStart, '
          'facing the entrance</text>')
    for c in CAMS:
        if c["loc"][1] >= -1.5:
            continue
        (x, y, _z), (tx, ty, _tz) = c["loc"], c["look_at"]
        hd = math.atan2(tx - x, ty - y)
        px, py = sx(x), sy(y)
        l_ = (px + math.sin(hd - 0.5) * 60, py - math.cos(hd - 0.5) * 60)
        r_ = (px + math.sin(hd + 0.5) * 60, py - math.cos(hd + 0.5) * 60)
        a(f'<polygon points="{px:.1f},{py:.1f} {l_[0]:.1f},{l_[1]:.1f} {r_[0]:.1f},{r_[1]:.1f}" fill="#e04a3a" '
          'fill-opacity="0.45"/>')
        a(f'<text x="{px-10:.1f}" y="{py+22:.1f}" font-size="14" fill="#c0392b">{c["name"]}</text>')
    for x in range(int(X0) + 1, int(X1) + 1, 2):
        a(f'<text x="{sx(x)}" y="{sy(Y1)-8}" font-size="13" text-anchor="middle" fill="#555">{x}</text>')
    for y in range(int(Y0), int(Y1) + 1, 2):
        a(f'<text x="{sx(X0)-6}" y="{sy(y)+5}" font-size="13" text-anchor="end" fill="#555">{y}</text>')
    lx, yy = sx(X1) + 30, sy(Y1) + 10
    a(f'<text x="{lx}" y="{yy}" font-size="18" font-weight="bold" fill="#222">Key</text>')
    yy += 26
    seen = set()
    for _pre, k in SITE_KINDS:
        if k is None or k[2] in seen:
            continue
        seen.add(k[2])
        a(f'<rect x="{lx}" y="{yy-12}" width="16" height="14" fill="{k[1]}" stroke="#1a1512"/>')
        a(f'<text x="{lx+24}" y="{yy}" font-size="13" fill="#222">{k[2]}</text>')
        yy += 21
    for text in ("light = raked gravel courtyard", "green = lawn outside the walls",
                 "Tree lines, hills and mountains stand", "beyond this drawing (layout.json)."):
        a(f'<text x="{lx}" y="{yy}" font-size="13" fill="#555">{text}</text>')
        yy += 19
    a('</svg>')
    return "\n".join(s)


if __name__ == "__main__":
    site = site_ascii()
    with open(os.path.join(OUT_DIR, "ARMORY_SITE.txt"), "w", encoding="utf-8") as f:
        f.write(site + "\n")
    with open(os.path.join(OUT_DIR, "ARMORY_SITE.svg"), "w", encoding="utf-8") as f:
        f.write(site_svg() + "\n")
    print(site)
    txt = ascii_plan()
    with open(os.path.join(OUT_DIR, "ARMORY_LAYOUT.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n")
    with open(os.path.join(OUT_DIR, "ARMORY_LAYOUT.svg"), "w", encoding="utf-8") as f:
        f.write(svg_plan() + "\n")
    print(txt)
