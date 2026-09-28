"""PlayerBase: measure the orthographic base-colour silhouettes written by pb_conform.py.

    py -3 Scripts/MetaHuman/pb_silhouette_measure.py [player_base_dir]

Every *_Ortho_Front.png / *_Ortho_Side.png is 1200x1200 px over 240 cm (0.2 cm/px), camera centred on x=0 (front)
or y=0 (side) at z=95 cm; the background renders black (no geometry, base colour = 0). Front view: image right = +X.
Side view (camera on +X looking -X): image right = -Y, so the character's front (+Y) is on the image LEFT.

Writes silhouette_measure.json and fit overlays (target vs solved/posed MetaHuman) into the captures folder.
Measures come from rendered geometry, so they are independent of the CPU-side mesh data in the editor.
"""
import json
import os
import sys

from PIL import Image

BASE = sys.argv[1] if len(sys.argv) > 1 else r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_base"
CAP = os.path.join(BASE, "captures")
RES = 1200
S = 240.0 / RES           # cm per pixel
CZ = 95.0
THRESH = 4


def load_mask(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    assert (w, h) == (RES, RES), (path, im.size)
    px = im.load()
    return [[max(px[u, v]) > THRESH for u in range(w)] for v in range(h)]


def z_of(v):
    return CZ - (v + 0.5 - RES / 2) * S


def x_of(u):          # front view
    return (u + 0.5 - RES / 2) * S


def y_of_side(u):     # side view
    return -(u + 0.5 - RES / 2) * S


def runs(row):
    out, start = [], None
    for u, on in enumerate(row):
        if on and start is None:
            start = u
        elif not on and start is not None:
            out.append((start, u - 1))
            start = None
    if start is not None:
        out.append((start, len(row) - 1))
    return out


def rows_with(mask):
    return [v for v in range(RES) if any(mask[v])]


def run_at(row, u):
    for a, b in runs(row):
        if a <= u <= b:
            return a, b
    return None


def front_measures(mask):
    rs = rows_with(mask)
    top, bot = rs[0], rs[-1]
    ztop, zbot = z_of(top) + S / 2, z_of(bot) - S / 2
    h = ztop - zbot
    c = RES // 2
    out = {"top_z": round(ztop, 2), "sole_z": round(zbot, 2), "height": round(h, 2)}
    # crotch: lowest row where the centre column is filled
    crotch = None
    for v in range(bot, top, -1):
        if mask[v][c] and mask[v][c - 1]:
            crotch = v
            break
    out["crotch_height"] = round(z_of(crotch) - zbot, 2) if crotch else None

    def torso_width(v):
        r = run_at(mask[v], c)
        return None if r is None else (r[1] - r[0] + 1) * S

    def best(z0, z1, fn):
        cand = []
        for v in range(RES):
            z = z_of(v) - zbot
            if z0 <= z <= z1:
                w = torso_width(v)
                if w:
                    cand.append((w, z))
        return fn(cand) if cand else None

    hip = best(0.42 * h, 0.56 * h, max)
    waist = best(0.56 * h, 0.66 * h, min)
    neck = best(0.80 * h, 0.87 * h, min)
    head = best(h - 22.0, h, max)
    out["hip_breadth"], out["hip_breadth_at_z"] = (round(hip[0], 2), round(hip[1], 2)) if hip else (None, None)
    out["waist_breadth"], out["waist_breadth_at_z"] = (round(waist[0], 2), round(waist[1], 2)) if waist else (None, None)
    out["neck_breadth"] = round(neck[0], 2) if neck else None
    out["head_breadth_incl_ears"] = round(head[0], 2) if head else None
    # armpit: highest row (below the neck) where the torso run no longer touches the arm runs
    armpit = None
    for v in range(top, bot):
        z = z_of(v) - zbot
        if z > 0.83 * h:
            continue
        if len(runs(mask[v])) >= 3:
            armpit = v
            break
    if armpit is not None:
        out["armpit_height"] = round(z_of(armpit) - zbot, 2)
        tw = torso_width(armpit + 2)
        out["chest_breadth_at_armpit"] = round(tw, 2) if tw else None
        widths = []
        for v in range(top, armpit + 1):
            if z_of(v) - zbot < 0.80 * h:
                rr = runs(mask[v])
                widths.append((rr[-1][1] - rr[0][0] + 1) * S)
        out["shoulder_breadth_above_armpit"] = round(max(widths), 2) if widths else None
    xs = [u for v in range(RES) for u in range(RES) if mask[v][u]]
    out["x_extent"] = round((max(xs) - min(xs) + 1) * S, 2)
    return out


def side_measures(mask):
    rs = rows_with(mask)
    top, bot = rs[0], rs[-1]
    ztop, zbot = z_of(top) + S / 2, z_of(bot) - S / 2
    h = ztop - zbot
    out = {"top_z": round(ztop, 2), "height": round(h, 2)}
    prof = {}
    for v in range(top, bot + 1):
        z = z_of(v)
        if ztop - 36.0 <= z <= ztop - 12.0:
            rr = runs(mask[v])
            if rr:
                prof[v] = y_of_side(rr[0][0])  # front-most (+Y) point of the row
    vs = sorted(prof)
    best = None
    for i, v in enumerate(vs):
        up = [prof[k] for k in vs if v - 5 <= k < v]        # up to 1 cm above
        dn = [prof[k] for k in vs if v < k <= v + 5]        # up to 1 cm below
        if up and dn:
            drop = max(up) - max(dn)
            if best is None or drop > best[0]:
                best = (drop, z_of(v))
    if best:
        out["menton_z"] = round(best[1] - zbot, 2)
        out["head_height_top_to_chin"] = round(ztop - best[1], 2)
        out["chin_to_neck_profile_drop"] = round(best[0], 2)
    head_rows = [v for v in range(top, bot) if z_of(v) >= ztop - 22.0]
    ys = [y_of_side(u) for v in head_rows for u in range(RES) if mask[v][u]]
    out["head_depth_incl_nose"] = round(max(ys) - min(ys), 2) if ys else None
    # nose tip = front-most point of the head band
    out["nose_tip_y"] = round(max(ys), 2) if ys else None
    return out


def overlay(a, b, out_path):
    """red = only a (target), cyan = only b (MetaHuman), white = both."""
    im = Image.new("RGB", (RES, RES))
    px = im.load()
    both = only_a = only_b = 0
    for v in range(RES):
        ra, rb = a[v], b[v]
        for u in range(RES):
            if ra[u] and rb[u]:
                px[u, v] = (235, 235, 235)
                both += 1
            elif ra[u]:
                px[u, v] = (230, 40, 40)
                only_a += 1
            elif rb[u]:
                px[u, v] = (40, 210, 230)
                only_b += 1
    im.save(out_path)
    return {"iou": round(both / max(1, both + only_a + only_b), 4),
            "target_only_cm2": round(only_a * S * S, 1), "mh_only_cm2": round(only_b * S * S, 1),
            "overlay": out_path}


res = {"cm_per_px": S, "note": "measured on orthographic base-colour silhouettes (rendered geometry)"}
masks = {}
for prefix in ("target", "posed", "mh", "baseline"):
    for view in ("Front", "Side"):
        path = os.path.join(CAP, f"{prefix}_Ortho_{view}.png")
        if not os.path.isfile(path):
            continue
        m = load_mask(path)
        masks[(prefix, view)] = m
        res.setdefault(prefix, {})[view.lower()] = front_measures(m) if view == "Front" else side_measures(m)
for view in ("Front", "Side"):
    if ("target", view) in masks and ("posed", view) in masks:
        res[f"fit_target_vs_posed_{view.lower()}"] = overlay(
            masks[("target", view)], masks[("posed", view)], os.path.join(CAP, f"fit_overlay_{view}.png"))
out = os.path.join(BASE, "silhouette_measure.json")
with open(out, "w", encoding="utf-8") as fh:
    json.dump(res, fh, indent=1)
print(json.dumps(res, indent=1))
