"""pd_geodiag_seam_overlay.py -- draw the projected head/body neck seam (92-vertex ring of the body dump) on the UE
front captures, to show where the conform-session shoulder slivers sit. Python 3.12 + PIL (no numpy).
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(r"C:/Users/Cody/Desktop/Blender_Projects")
OBJ = ROOT / "WorkFiles/MetaHuman/player_base/faces/mesh_dump/FaceC_Body.obj"
OUT = ROOT / "WorkFiles/MetaHuman/player_default/geodiag"
V, F = [], []
for line in open(OBJ):
    if line.startswith("v "):
        V.append(tuple(map(float, line.split()[1:4])))
    elif line.startswith("f "):
        F.append(tuple(int(t) - 1 for t in line.split()[1:4]))
cnt = {}
for a, b, c in F:
    for e in ((a, b), (b, c), (c, a)):
        k = (min(e), max(e))
        cnt[k] = cnt.get(k, 0) + 1
bedges = [k for k, n in cnt.items() if n == 1]
adj = {}
for a, b in bedges:
    adj.setdefault(a, []).append(b)
    adj.setdefault(b, []).append(a)
start = bedges[0][0]
ring, prev, cur = [start], None, start
while True:
    nxt = [n for n in adj[cur] if n != prev and n not in ring]
    if not nxt:
        break
    prev, cur = cur, nxt[0]
    ring.append(cur)
FC = (0.0, 5.959721088409424, 173.6)
f = 500.0 / math.tan(math.radians(15))


def proj(p):          # UE front camera: at FC + (0,70,0), looking -Y, image right = +X
    d = FC[1] + 70 - p[1]
    return 500 + f * p[0] / d, 600 - f * (p[2] - FC[2]) / d


tiles = []
for cap, lab in ((ROOT / "WorkFiles/MetaHuman/player_base/captures/mh_Face_Front.png", "mh_Face_Front (conform session)"),
                 (ROOT / "WorkFiles/MetaHuman/player_base/faces/captures/FaceC_Face_Front.png", "FaceC_Face_Front (reloaded)")):
    im = Image.open(cap).convert("RGB")
    d = ImageDraw.Draw(im)
    pts = [proj(V[i]) for i in ring] + [proj(V[ring[0]])]
    d.line(pts, fill=(0, 255, 0), width=1)
    for side, box in (("L", (0, 960, 260, 1160)), ("R", (740, 960, 1000, 1160))):
        c = im.crop(box).resize((520, 400), Image.NEAREST)
        t = Image.new("RGB", (520, 420), (255, 255, 255))
        t.paste(c, (0, 20))
        ImageDraw.Draw(t).text((3, 3), f"{lab} {side}  green = head/body seam", fill=(0, 0, 0))
        tiles.append(t)
out = Image.new("RGB", (2 * 526, 2 * 426), (255, 255, 255))
for i, t in enumerate(tiles):
    out.paste(t, ((i % 2) * 526, (i // 2) * 426))
out.save(OUT / "sheet_shoulder_seam.png")
print("ring", len(ring), "saved")
