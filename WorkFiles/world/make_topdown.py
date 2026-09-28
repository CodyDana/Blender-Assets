"""Draws DOJO_ARENA_TOPDOWN.svg from the numbers in DOJO_ARENA_SPEC.md.

World frame (metres): origin = inside south-west corner of the compound at courtyard level,
X east (0-44), Y north (0-36). The perimeter wall is 1 m thick OUTSIDE that box.
Re-run:  py WorkFiles/world/make_topdown.py   (writes the SVG next to this file)
Rasterize: msedge --headless --screenshot (see DOJO_ARENA_SPEC.md, section 10).
"""
import math, os

HERE = os.path.dirname(os.path.abspath(__file__))
S = 24.0                      # px per metre
X_MIN, Y_MAX = -7.0, 41.0     # world window
OX, OY = 40.0, 96.0           # map origin on the canvas
W, H = 2000, 1330

def px(x): return OX + (x - X_MIN) * S
def py_(y): return OY + (Y_MAX - y) * S

out = []
def add(s): out.append(s)

def rect(x0, y0, x1, y1, fill, stroke="none", sw=1, extra=""):
    add(f'<rect x="{px(x0):.1f}" y="{py_(y1):.1f}" width="{(x1-x0)*S:.1f}" height="{(y1-y0)*S:.1f}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')

def poly(pts, fill, stroke="none", sw=1, extra=""):
    p = " ".join(f"{px(x):.1f},{py_(y):.1f}" for x, y in pts)
    add(f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>')

def line(x0, y0, x1, y1, stroke, sw=1, extra=""):
    add(f'<line x1="{px(x0):.1f}" y1="{py_(y0):.1f}" x2="{px(x1):.1f}" y2="{py_(y1):.1f}" '
        f'stroke="{stroke}" stroke-width="{sw}" {extra}/>')

def circle(x, y, r, fill, stroke="none", sw=1, extra=""):
    add(f'<circle cx="{px(x):.1f}" cy="{py_(y):.1f}" r="{r*S:.1f}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{sw}" {extra}/>')

def text(x, y, s, size=14, fill="#222", anchor="middle", weight="normal", extra=""):
    add(f'<text x="{px(x):.1f}" y="{py_(y):.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
        f'font-weight="{weight}" {extra}>{s}</text>')

def label(x, y, lines, size=13, weight="bold", fill="#1d1d1d", halo=True):
    """Multi-line label centred on (x, y) with a white halo for legibility."""
    n = len(lines)
    for i, s in enumerate(lines):
        yy = y + (n - 1) * 0.5 * (size + 2) / S - i * (size + 2) / S
        st = 'stroke="#ffffff" stroke-width="3.5" paint-order="stroke" stroke-linejoin="round"' if halo else ""
        text(x, yy - size * 0.35 / S, s, size, fill, "middle", weight if i == 0 else "normal", st)

def arrow(pts, colour, num=None, sw=3.2):
    d = "M " + " L ".join(f"{px(x):.1f} {py_(y):.1f}" for x, y in pts)
    add(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{sw}" stroke-linecap="round" '
        f'stroke-linejoin="round" marker-end="url(#ah_{colour[1:]})"/>')
    if num is not None:
        x, y = pts[0]
        circle(x, y, 0.55, "#ffffff", colour, 2.2)
        text(x, y - 0.22, str(num), 13, colour, "middle", "bold")

# ---------------------------------------------------------------- palette
C = dict(
    outside="#dfe3d6", gravel="#d8d2c4", sand="#f2e9d6", path="#bfb8ab", step="#a9a397",
    wall="#b69a70", wallcap="#6e6a64", roof_lo="#8d949b", roof_hi="#646b73", roof_out="#7b838b",
    roof_mod="#a9adb1", engawa="#c9a67a", tree="#5e7a45", props="#8a6a45", climb="#e07b18",
    p1="#1f5fbf", p2="#c62828", oob="#c62828", br="#7b3fb5", water="#8fb3c7", modern="#4f7f86",
)
ARROWS = [C["climb"], C["br"], C["p1"], C["p2"], "#333333"]

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    f'font-family="Segoe UI, Arial, sans-serif">')
add("<defs>")
for c in ARROWS:
    add(f'<marker id="ah_{c[1:]}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="4.2" markerHeight="4.2" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>')
add('<pattern id="hatchOOB" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    f'<rect width="10" height="10" fill="none"/><line x1="0" y1="0" x2="0" y2="10" stroke="{C["oob"]}" '
    'stroke-width="2.2" stroke-opacity="0.55"/></pattern>')
add('<pattern id="hatchOut" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    '<line x1="0" y1="0" x2="0" y2="14" stroke="#b9bfae" stroke-width="1.2"/></pattern>')
add('<pattern id="rake" width="12" height="6" patternUnits="userSpaceOnUse">'
    '<line x1="0" y1="3" x2="12" y2="3" stroke="#e2d6bb" stroke-width="1"/></pattern>')
add('<pattern id="corrug" width="6" height="6" patternUnits="userSpaceOnUse">'
    '<line x1="3" y1="0" x2="3" y2="6" stroke="#8c9196" stroke-width="1.3"/></pattern>')
add('<pattern id="tiles" width="8" height="8" patternUnits="userSpaceOnUse">'
    '<line x1="4" y1="0" x2="4" y2="8" stroke="#000" stroke-opacity="0.13" stroke-width="1"/></pattern>')
add('<pattern id="tilesH" width="8" height="8" patternUnits="userSpaceOnUse">'
    '<line x1="0" y1="4" x2="8" y2="4" stroke="#000" stroke-opacity="0.13" stroke-width="1"/></pattern>')
add("</defs>")
add(f'<rect width="{W}" height="{H}" fill="#fbfaf7"/>')

# ---------------------------------------------------------------- title
add(f'<text x="40" y="42" font-size="30" font-weight="bold" fill="#1d1d1d">Dojo Courtyard Arena: top-down plan</text>')
add(f'<text x="40" y="72" font-size="16" fill="#444">1v1 duel arena, later a named location on the battle-royale map. '
    f'North is up. Grid squares are 2 m. Heights (+) are metres above the courtyard floor.</text>')

# ---------------------------------------------------------------- outside + ground
rect(X_MIN, -9, 51, Y_MAX, C["outside"])
rect(X_MIN, -9, 51, Y_MAX, "url(#hatchOut)")
label(-4.0, 19.5, ["OUTSIDE", "(out of bounds", "in the 1v1)"], 12, fill="#5b6152")
label(48.0, 19.5, ["OUTSIDE", "(out of bounds", "in the 1v1)"], 12, fill="#5b6152")
rect(0, 0, 44, 36, C["gravel"])
# fight floor + rake + stone path + step band
rect(8, 2, 36, 19, C["sand"], "#b9ab8a", 1.5)
rect(8, 2, 36, 19, "url(#rake)")
rect(21, 0, 23, 21.4, C["path"], "#9a9488", 1)
for yy in range(1, 21):
    line(21, yy, 23, yy, "#9a9488", 0.8)
rect(10.5, 21.4, 33.5, 22.0, C["step"], "#8e897e", 1)

# grid (2 m faint, 10 m stronger) over the compound
for gx in range(0, 45, 2):
    line(gx, 0, gx, 36, "#000", 0.5 if gx % 10 else 0.9, 'stroke-opacity="0.10"')
for gy in range(0, 37, 2):
    line(0, gy, 44, gy, "#000", 0.5 if gy % 10 else 0.9, 'stroke-opacity="0.10"')

# rear alley + pockets (out of bounds in the 1v1, open in BR)
for (a, b, c, d) in [(10.5, 34, 33.5, 36), (7.6, 32.5, 10.5, 36), (33.5, 32.5, 36.4, 36)]:
    rect(a, b, c, d, "#e9dada")
    rect(a, b, c, d, "url(#hatchOOB)")
label(22, 35.35, ["rear alley: closed in the 1v1 (fences), open in BR"], 11, "normal", "#8b1c1c")

# ---------------------------------------------------------------- trees (canopies drawn late, trunks here)
# ---------------------------------------------------------------- perimeter wall
for (a, b, c, d) in [(-1, -1, 20, 0), (24, -1, 45, 0), (-1, 36, 45, 37), (-1, -1, 0, 37), (44, -1, 45, 37)]:
    rect(a, b, c, d, C["wall"], "#7d6746", 1.2)
line(-0.5, -0.5, 20, -0.5, C["wallcap"], 1.4); line(24, -0.5, 44.5, -0.5, C["wallcap"], 1.4)
line(-0.5, 36.5, 44.5, 36.5, C["wallcap"], 1.4)
line(-0.5, -0.5, -0.5, 36.5, C["wallcap"], 1.4); line(44.5, -0.5, 44.5, 36.5, C["wallcap"], 1.4)
# BR-only openings in the wall
for (a, b, c, d) in [(21.5, 36, 22.5, 37), (-1, 14, 0, 15), (44, 14, 45, 15)]:
    rect(a, b, c, d, C["br"], "#4a2370", 1)
text(22, 37.9, "rear wicket gate (BR only)", 12, C["br"], "middle", "bold")
text(-1.4, 14.0, "side wicket", 11, C["br"], "end", "bold"); text(-1.4, 13.35, "(BR only)", 11, C["br"], "end")
text(45.4, 14.0, "side wicket", 11, C["br"], "start", "bold"); text(45.4, 13.35, "(BR only)", 11, C["br"], "start")
# wall labels
text(6.5, -0.72, "PERIMETER WALL  top +2.0, walkable strip 1.0 m", 11, "#3b2f1d", "middle", "bold")
text(34, -0.72, "PERIMETER WALL  top +2.0", 11, "#3b2f1d", "middle", "bold")
add(f'<text x="{px(-0.43):.1f}" y="{py_(8):.1f}" font-size="11" fill="#3b2f1d" font-weight="bold" '
    f'transform="rotate(-90 {px(-0.43):.1f} {py_(8):.1f})" text-anchor="middle">WALL TOP +2.0 (walkable)</text>')
add(f'<text x="{px(44.57):.1f}" y="{py_(8):.1f}" font-size="11" fill="#3b2f1d" font-weight="bold" '
    f'transform="rotate(90 {px(44.57):.1f} {py_(8):.1f})" text-anchor="middle">WALL TOP +2.0 (walkable)</text>')
text(30, 36.35, "north wall top: out of bounds in the 1v1 (hidden behind the hall)", 10.5, "#8b1c1c")

# ---------------------------------------------------------------- ground props (under roofs first)
# cisterns (climb props)
for x0 in (11.0, 31.8):
    rect(x0, 20.1, x0 + 1.2, 21.3, C["climb"], "#8a4508", 1.2)
# stone lanterns
for x in (19, 25):
    circle(x, 20.4, 0.38, "#9d9b96", "#555", 1.2)
# racks, posts, dummies
for (a, b, c, d) in [(2, 8.6, 4, 9.2), (40, 8.6, 42, 9.2)]:
    rect(a, b, c, d, C["props"], "#4d3a24", 1)
for (x, y) in [(6, 7), (6, 13), (38, 7), (38, 13)]:
    rect(x - 0.15, y - 0.15, x + 0.15, y + 0.15, C["props"], "#4d3a24", 1)
for (x, y) in [(3, 12.3), (41, 12.3)]:
    circle(x, y, 0.3, C["props"], "#4d3a24", 1)
# vending machine (modern, climb prop) + crates
rect(12.0, 0.0, 13.0, 0.8, C["modern"], "#2d4a4e", 1.2)
rect(3.0, 5.1, 4.1, 6.2, C["climb"], "#8a4508", 1.2)
rect(37.2, 2.5, 38.3, 3.6, C["climb"], "#8a4508", 1.2)
# well
circle(41, 22, 0.75, C["water"], "#4d6d80", 1.5)

# ---------------------------------------------------------------- buildings (roof plan)
def gable_roof(x0, y0, x1, y1, ridge_along_x, fill, oob_side=None):
    rect(x0, y0, x1, y1, fill, "#3f444a", 1.4)
    rect(x0, y0, x1, y1, "url(#tiles)" if ridge_along_x else "url(#tilesH)")
    if ridge_along_x:
        ym = (y0 + y1) / 2
        if oob_side == "north":
            rect(x0, ym, x1, y1, "url(#hatchOOB)")
        line(x0, ym, x1, ym, "#2b2f33", 2.2)
    else:
        xm = (x0 + x1) / 2
        line(xm, y0, xm, y1, "#2b2f33", 2.2)

# storehouse (NW) and residence (NE): walls built into the perimeter wall, eaves +3.25
gable_roof(0, 27.4, 7.6, 36, True, C["roof_out"], "north")
gable_roof(36.4, 27.4, 44, 36, True, C["roof_out"], "north")
# covered corridors: roof +3.0 eave, ridge +3.7, north side walled
gable_roof(7.6, 29.5, 10.5, 32.5, True, C["roof_mod"], "north")
gable_roof(33.5, 29.5, 36.4, 32.5, True, C["roof_mod"], "north")

# hall: lower roof (mokoshi) then upper roof
rect(10.5, 21.5, 33.5, 34, C["roof_lo"], "#3f444a", 1.6)
rect(10.5, 21.5, 33.5, 34, "url(#tilesH)")
poly([(12.1, 23.1), (31.9, 23.1), (31.9, 34.9), (12.1, 34.9)], C["roof_hi"], "#2b2f33", 1.8)
# upper roof hips and ridge (hip-and-gable read from above)
for (a, b) in [((12.1, 23.1), (17.5, 29)), ((31.9, 23.1), (26.5, 29)), ((12.1, 34.9), (17.5, 29)),
               ((31.9, 34.9), (26.5, 29))]:
    line(a[0], a[1], b[0], b[1], "#23272b", 1.8)
line(17.5, 29, 26.5, 29, "#1b1e21", 3.2)
# 1v1: rear half of the upper roof out of bounds, ridge blocker
poly([(12.1, 34.9), (31.9, 34.9), (26.5, 29), (17.5, 29)], "url(#hatchOOB)")
poly([(12.1, 29), (17.5, 29), (12.1, 34.9)], "url(#hatchOOB)")
poly([(31.9, 29), (26.5, 29), (31.9, 34.9)], "url(#hatchOOB)")
line(12.1, 29, 31.9, 29, C["oob"], 2.4, 'stroke-dasharray="9 6"')
# hall walls and engawa edge under the roofs (dashed)
rect(13, 24, 31, 34, "none", "#f4f4f4", 1.2, 'stroke-dasharray="6 5"')
rect(11, 22, 33, 34, "none", "#e8d2b0", 1.2, 'stroke-dasharray="3 5"')
# AC condensers on the lower roof (modern climb props)
for x0 in (15.0, 27.8):
    rect(x0, 22.0, x0 + 1.2, 24.0, C["modern"], "#1f3a3e", 1.2)
    text(x0 + 0.6, 22.35, "AC", 10, "#ffffff", "middle", "bold")

# gatehouse (roof straddles the south wall)
gable_roof(18, -2.5, 26, 2.5, True, C["roof_out"])
# SW training shed (corrugated steel lean-to)
rect(0, 0, 6, 5, "#b9bcbf", "#5d6166", 1.4)
rect(0, 0, 6, 5, "url(#corrug)")
# SE drum pavilion (pyramid roof)
poly([(38.4, 0.4), (43.6, 0.4), (43.6, 5.6), (38.4, 5.6)], C["roof_out"], "#3f444a", 1.4)
for (a, b) in [(38.4, 0.4), (43.6, 0.4), (43.6, 5.6), (38.4, 5.6)]:
    line(a, b, 41, 3, "#2b2f33", 1.4)
circle(41, 3, 0.7, "none", "#fff", 1.2, 'stroke-dasharray="3 3"')

# ---------------------------------------------------------------- trees (canopy)
for (x, y, r) in [(3.5, 16, 3.2), (40.5, 16, 3.2)]:
    circle(x, y, r, C["tree"], "#3c5129", 1.2, 'fill-opacity="0.55"')
    circle(x, y, 0.3, "#4a3524")
for (x, y, r) in [(-4.3, 31, 2.6), (48.3, 31, 2.6), (-4.3, 3, 2.4), (48.3, 5, 2.4), (8, 39.3, 2.2), (36, 39.3, 2.2)]:
    circle(x, y, r, C["tree"], "#3c5129", 1, 'fill-opacity="0.35"')

# modern bits outside: power pole + lines, street lamp
circle(48.0, -2.8, 0.35, "#5b4a3a", "#2c241c", 1.2)
line(48.0, -2.8, 51, -2.8, "#333", 1.2, 'stroke-dasharray="2 3"')
line(48.0, -2.8, 44.5, 30, "#333", 1.0, 'stroke-dasharray="2 3"')
text(48.0, -4.0, "power pole", 11, "#333"); text(48.0, -4.6, "+ overhead wires", 11, "#333")
circle(16.5, -3.0, 0.3, C["modern"], "#1f3a3e", 1.2); circle(27.5, -3.0, 0.3, C["modern"], "#1f3a3e", 1.2)
text(22, -3.9, "approach road (BR) / street lamps", 11, "#333")
text(22, -4.6, "MAIN GATE (closed in the 1v1)", 12, C["br"], "middle", "bold")

# ---------------------------------------------------------------- spawns + dimensions
for (x, dx, col, name) in [(14.5, 1, C["p1"], "P1"), (29.5, -1, C["p2"], "P2")]:
    circle(x, 10.5, 0.85, col, "#ffffff", 2.2)
    text(x, 10.5 - 0.2, name, 14, "#ffffff", "middle", "bold")
    arrow([(x + dx * 1.0, 10.5), (x + dx * 2.6, 10.5)], col, None, 3.0)
line(14.5, 8.9, 29.5, 8.9, "#333", 1.2)
for x in (14.5, 29.5):
    line(x, 8.6, x, 9.2, "#333", 1.2)
label(22, 8.35, ["spawns 15 m apart, facing each other"], 12, "normal")
# fight floor dims
line(8, 2.7, 36, 2.7, "#6b5b3a", 1.1); line(8, 2.4, 8, 3.0, "#6b5b3a", 1.1); line(36, 2.4, 36, 3.0, "#6b5b3a", 1.1)
label(29.5, 2.7, ["28 m"], 12, "bold", "#6b5b3a")
line(36.6, 2, 36.6, 19, "#6b5b3a", 1.1)
label(36.7, 15.0, ["17 m"], 12, "bold", "#6b5b3a")
# compound dims (outside)
line(-1, -6.3, 45, -6.3, "#333", 1.0); line(-1, -6.0, -1, -6.6, "#333", 1.0); line(45, -6.0, 45, -6.6, "#333", 1.0)
label(32.0, -6.3, ["46 m over the walls (44 m inside)"], 12, "normal")
line(-6.3, -1, -6.3, 37, "#333", 1.0)
add(f'<text x="{px(-6.55):.1f}" y="{py_(18):.1f}" font-size="12" fill="#333" '
    f'transform="rotate(-90 {px(-6.55):.1f} {py_(18):.1f})" text-anchor="middle">38 m over the walls (36 m inside)</text>')

# ---------------------------------------------------------------- zone labels
label(22, 14.8, ["FIGHT FLOOR", "raked sand, dead flat, no props", "28 x 17 m"], 16)
label(22, 26.3, ["DOJO HALL", "upper roof: eave +5.5, ridge +8.3", "floor +0.5 (closed in the 1v1)"], 14, fill="#ffffff", halo=False)
label(22, 32.0, ["rear slope: out of bounds in the 1v1"], 11, "normal", "#ffd9d9", halo=False)
label(22, 22.5, ["LOWER ROOF: eave +3.0, meets hall wall at +4.17"], 11, "bold", "#ffffff", halo=False)
label(22, 28.35, ["ridge blocker (1v1)"], 10.5, "normal", "#ffc2c2", halo=False)
label(3.8, 30.4, ["STOREHOUSE", "eave +3.25", "ridge +5.25"], 12, fill="#ffffff", halo=False)
label(40.2, 30.4, ["RESIDENCE /", "WASH HOUSE", "eave +3.25"], 12, fill="#ffffff", halo=False)
label(9.05, 33.9, ["corridor", "roof +3.0"], 10.5, "normal")
label(34.95, 33.9, ["corridor", "roof +3.0"], 10.5, "normal")
label(3.0, 2.9, ["TRAINING SHED", "steel lean-to", "+3.0 at wall", "+2.5 at front"], 11)
label(41.0, 7.0, ["DRUM PAVILION", "plinth +1.0, eave +3.25"], 11)
label(22, 1.6, ["GATEHOUSE  eave +3.25"], 11, "bold", "#ffffff", halo=False)
label(3.5, 20.0, ["tree (bought)"], 11, "normal")
label(40.5, 20.0, ["tree (bought)"], 11, "normal")
label(3.0, 10.0, ["weapon rack"], 10.5, "normal")
label(41.0, 10.0, ["weapon rack"], 10.5, "normal")
label(8.3, 13.7, ["posts"], 10.5, "normal")
label(35.7, 13.7, ["posts"], 10.5, "normal")
label(41.0, 23.5, ["well"], 10.5, "normal")
label(22, 20.4, ["stone lanterns"], 10.5, "normal")
label(9.8, 0.9, ["vending machine"], 10.5, "normal")
label(22, 18.0, ["stone path (flush)"], 10.5, "normal", "#5d574c")
label(5.5, 23.8, ["WEST YARD", "gravel, low cover only"], 11, "bold", "#5d574c")
label(38.5, 25.2, ["EAST YARD", "gravel, low cover only"], 11, "bold", "#5d574c")

# ---------------------------------------------------------------- climb routes
R = C["climb"]
arrow([(8.4, 11.2), (-0.3, 11.2)], R, 1)                       # ground -> west wall top
arrow([(35.6, 11.2), (44.3, 11.2)], R, 1)                      # ground -> east wall top
arrow([(-0.5, 22.5), (-0.5, 26.8), (1.8, 28.2)], R, 2)         # wall top -> storehouse roof
arrow([(44.5, 22.5), (44.5, 26.8), (42.2, 28.2)], R, 2)        # wall top -> residence roof
arrow([(5.6, 29.0), (9.0, 30.4), (11.3, 29.8)], R, 3)          # storehouse -> corridor -> hall lower roof
arrow([(38.4, 29.0), (35.0, 30.4), (32.7, 29.8)], R, 3)
arrow([(11.6, 18.6), (11.6, 20.6), (11.6, 22.6)], R, 4)        # ground -> cistern -> lower roof
arrow([(32.4, 18.6), (32.4, 20.6), (32.4, 22.6)], R, 4)
arrow([(15.6, 20.2), (15.6, 23.0), (15.6, 24.9)], R, 5)        # lower roof -> AC -> upper roof
arrow([(28.4, 20.2), (28.4, 23.0), (28.4, 24.9)], R, 5)
arrow([(15.6, -0.5), (18.4, -0.5)], R, 6)                      # south wall top -> gatehouse roof
arrow([(28.4, -0.5), (25.6, -0.5)], R, 6)
arrow([(3.55, 8.0), (3.55, 5.65), (3.55, 4.1)], R, 7)          # crates -> shed roof
arrow([(35.9, 4.9), (37.75, 3.05), (39.4, 3.05)], R, 7)        # crates -> pavilion eave
arrow([(12.5, 2.2), (12.5, 0.4), (12.5, -0.5)], R, 8)          # vending machine -> wall top

# boundary line (1v1): outer edge of the wall
rect(-1, -1, 45, 37, "none", C["oob"], 2.6, 'stroke-dasharray="14 7"')
text(-1.0, -1.7, "1v1 boundary: invisible wall on the OUTER edge of the wall top", 12, C["oob"], "start", "bold")

# north arrow + scale bar
nx, ny = px(-5.2), py_(39.3)
add(f'<g transform="translate({nx:.1f},{ny:.1f})"><circle r="26" fill="#ffffff" stroke="#333" stroke-width="1.5"/>'
    f'<path d="M0,-21 L8,8 L0,3 L-8,8 z" fill="#1d1d1d"/><text y="22" font-size="13" text-anchor="middle" '
    f'font-weight="bold" fill="#1d1d1d">N</text></g>')
sx0, sy0 = px(-6.0), py_(-8.2)
for i in range(5):
    add(f'<rect x="{sx0 + i*2*S:.1f}" y="{sy0:.1f}" width="{2*S:.1f}" height="9" '
        f'fill="{"#1d1d1d" if i % 2 == 0 else "#ffffff"}" stroke="#1d1d1d" stroke-width="1"/>')
for i, lab in [(0, "0"), (5, "10 m")]:
    add(f'<text x="{sx0 + i*2*S:.1f}" y="{sy0 - 4:.1f}" font-size="12" text-anchor="middle" fill="#1d1d1d">{lab}</text>')
add(f'<text x="{sx0 + 5*2*S + 12:.1f}" y="{sy0 + 9:.1f}" font-size="12" fill="#1d1d1d">scale 1 : 200 at 100 %  (24 px = 1 m)</text>')

# ---------------------------------------------------------------- legend panel
LX, LY = 1450, 96
add(f'<rect x="{LX}" y="{LY}" width="520" height="1200" fill="#ffffff" stroke="#c9c5bc" stroke-width="1.2"/>')
yy = LY + 34
def lh(s):
    global yy
    add(f'<text x="{LX+18}" y="{yy}" font-size="17" font-weight="bold" fill="#1d1d1d">{s}</text>'); yy += 26
def lrow(fill, s, pat=None, stroke="#555", kind="rect"):
    global yy
    if kind == "rect":
        add(f'<rect x="{LX+18}" y="{yy-14}" width="34" height="18" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        if pat:
            add(f'<rect x="{LX+18}" y="{yy-14}" width="34" height="18" fill="url(#{pat})"/>')
    elif kind == "circle":
        add(f'<circle cx="{LX+35}" cy="{yy-5}" r="9" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
    elif kind == "dash":
        add(f'<line x1="{LX+18}" y1="{yy-5}" x2="{LX+52}" y2="{yy-5}" stroke="{fill}" stroke-width="2.6" stroke-dasharray="9 5"/>')
    elif kind == "arrow":
        add(f'<line x1="{LX+18}" y1="{yy-5}" x2="{LX+48}" y2="{yy-5}" stroke="{fill}" stroke-width="3" marker-end="url(#ah_{fill[1:]})"/>')
    add(f'<text x="{LX+64}" y="{yy}" font-size="14" fill="#222">{s}</text>'); yy += 25
def ltxt(s, size=13, col="#333", bold=False):
    global yy
    add(f'<text x="{LX+18}" y="{yy}" font-size="{size}" fill="{col}" font-weight="{"bold" if bold else "normal"}">{s}</text>'); yy += size + 6

lh("Zones")
lrow(C["sand"], "Fight floor: raked sand, flat, empty", "rake")
lrow(C["gravel"], "Yards: gravel, low cover only (under 1.25 m)")
lrow(C["path"], "Stone path, flush with the ground")
lrow(C["wall"], "Perimeter wall, top +2.0 (walkable)")
lrow(C["roof_hi"], "Hall upper roof (25 deg, walkable front)", "tilesH")
lrow(C["roof_lo"], "Hall lower roof over the veranda (25 deg)", "tilesH")
lrow(C["roof_out"], "Outbuilding roofs (25 deg, walkable front)", "tiles")
lrow("#b9bcbf", "Steel lean-to roof (modern touch)", "corrug")
lrow("#e9dada", "Out of bounds in the 1v1 (open in BR)", "hatchOOB")
lrow(C["oob"], "1v1 boundary / blockers (invisible)", kind="dash")
lrow(C["br"], "Openings used only in the battle royale")
lrow(C["tree"], "Trees (bought assets)", kind="circle", stroke="#3c5129")
lrow(C["climb"], "Climb props: cistern, crates (+1.25)")
lrow(C["modern"], "Modern props: vending machine, AC units")
lrow(C["p1"], "Player 1 spawn (faces east)", kind="circle", stroke="#fff")
lrow(C["p2"], "Player 2 spawn (faces west)", kind="circle", stroke="#fff")
yy += 8
lh("Climb routes (every required climb 2.0 m or less)")
routes = [
    "1  Ground to wall top: one mantle of 2.0 m",
    "2  Wall top +2.0 to storehouse / residence eave +3.25",
    "3  Outbuilding roof, corridor roof +3.0, hall lower roof",
    "4  Ground, cistern +1.25, lower-roof eave +3.0 (1.75)",
    "5  Lower roof, AC unit top +4.75, upper eave +5.5 (0.75)",
    "6  South wall top +2.0 to gatehouse eave +3.25",
    "7  Crates +1.25 to shed edge +2.5 / pavilion eave +3.25",
    "8  Vending machine top +1.75, step to the wall top +2.0",
]
for r in routes:
    add(f'<circle cx="{LX+30}" cy="{yy-5}" r="10" fill="#fff" stroke="{R}" stroke-width="2"/>'
        f'<text x="{LX+30}" y="{yy}" font-size="12" font-weight="bold" fill="{R}" text-anchor="middle">{r[0]}</text>')
    add(f'<text x="{LX+50}" y="{yy}" font-size="13.5" fill="#222">{r[3:]}</text>'); yy += 24
yy += 8
lh("Heights (metres above the courtyard)")
for s in ["Veranda (engawa) and hall floor +0.5, two 0.25 steps",
          "Wall top +2.0; gate opening 4.0 wide x 3.5 high",
          "Lower roof eave +3.0, rising to +4.17 at the hall wall",
          "Upper roof eave +5.5, ridge +8.3 (crest tiles to +8.7)",
          "Storehouse / residence eave +3.25, ridge +5.25",
          "Gatehouse eave +3.25, ridge +4.4; pavilion apex +4.5",
          "Clear headroom under every walked roof: 2.5 m or more"]:
    ltxt(s, 13.5)
yy += 6
lh("Numbers these come from")
for s in ["GASP mantle reaches about 2.75 m (unmeasured here),",
          "so required climbs stop at 2.0 m. Steps stay at 0.25 m",
          "(engine step limit 0.45 m). Walk-on ledges are 1.0 m deep",
          "(capsule 0.70 m wide). Roofs 25 deg (walkable to 44.8).",
          "Lock-on reaches 20 m, lets go at 28 m. Spawns 15 m apart.",
          "Full derivation: DOJO_ARENA_SPEC.md, section 3."]:
    ltxt(s, 12.5, "#444")
add("</svg>")

path = os.path.join(HERE, "DOJO_ARENA_TOPDOWN.svg")
with open(path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(path)
