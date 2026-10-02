"""VERIFIER (hall + armory): CAM_Ref2Match (and the other shared views) final vs the landscape round's final capture.
Own door-box projection (pinhole from the layout camera), own noise mask from the builder's second capture of the same
final state (fix/caps/noise), own blob listing of every change outside the door box. Read-only; writes verify/json.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

B = Path(r"C:\Users\Cody\Desktop\Blender_Projects\WorkFiles\dojo\build")
OUTD = B / "hall_armory" / "verify" / "json"
OUTD.mkdir(parents=True, exist_ok=True)
L = json.loads((B / "showcase" / "layout_showcase.json").read_text(encoding="utf-8"))
CAMS = {c["name"]: c for c in L["cameras"]}
BEFORE = B / "landscape" / "fix" / "caps"
AFTER = B / "hall_armory" / "fix" / "caps" / "final"
NOISE = B / "hall_armory" / "fix" / "caps" / "noise"


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.int16)


def dilate(m, k):
    o = m.copy()
    for dy in range(-k, k + 1):
        for dx in range(-k, k + 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return o


def project(cam, pts, w, h):
    """pinhole, horizontal fov, world (x east, y north, z up)."""
    c = np.array(cam["loc"], float)
    f = np.array(cam["look_at"], float) - c
    f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    fx = (w / 2) / math.tan(math.radians(cam["hfov_deg"]) / 2)
    out = []
    for p in pts:
        d = np.array(p, float) - c
        z = d @ f
        out.append(((w / 2) + fx * (d @ r) / z, (h / 2) - fx * (d @ u) / z))
    return out


def door_box(cam, w, h, pad=12):
    # the three door openings (world X 19.12..24.88, sill +0.545, head +2.388) at the front face Y 23.88..24.12,
    # plus the inner side of the opening up to Y 26 (what can be seen through it)
    pts = [(x, y, z) for x in (19.12, 24.88) for y in (23.88, 24.12, 26.0) for z in (0.545, 2.388)]
    pp = project(cam, pts, w, h)
    xs, ys = [p[0] for p in pp], [p[1] for p in pp]
    return [max(0, int(min(xs)) - pad), max(0, int(min(ys)) - pad), min(w, int(max(xs)) + pad), min(h, int(max(ys)) + pad)]


def blobs(m, min_px=40, top=12):
    """4-connected components (numpy flood via labels by BFS on a downsampled grid of 4x4 blocks)."""
    hh, ww = m.shape
    bs = 4
    g = m[: hh // bs * bs, : ww // bs * bs].reshape(hh // bs, bs, ww // bs, bs).sum(axis=(1, 3))
    seen = np.zeros(g.shape, bool)
    res = []
    for (j, i) in zip(*np.nonzero(g)):
        if seen[j, i]:
            continue
        st, cells = [(j, i)], []
        seen[j, i] = True
        while st:
            a, b = st.pop()
            cells.append((a, b))
            for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                na, nb = a + da, b + db
                if 0 <= na < g.shape[0] and 0 <= nb < g.shape[1] and g[na, nb] and not seen[na, nb]:
                    seen[na, nb] = True
                    st.append((na, nb))
        px = int(sum(g[a, b] for a, b in cells))
        if px >= min_px:
            ys, xs = [c[0] for c in cells], [c[1] for c in cells]
            res.append({"px": px, "bbox_xyxy": [int(min(xs) * bs), int(min(ys) * bs), int((max(xs) + 1) * bs), int((max(ys) + 1) * bs)]})
    res.sort(key=lambda r: -r["px"])
    return res[:top], len(res)


def sky_mask(img):
    # sky = the connected bright-blue/orange region touching the top edge: rows above the first row where the top-edge
    # column run ends; simple: per column, pixels from the top until the first strong vertical gradient (> 40)
    lum = img.mean(axis=2)
    hh, ww = lum.shape
    m = np.zeros((hh, ww), bool)
    gy = np.abs(np.diff(lum, axis=0)) > 40
    first = np.where(gy.any(axis=0), gy.argmax(axis=0), hh)
    for x in range(ww):
        m[: first[x], x] = True
    return m


def analyse(name, thr=24):
    a, b = AFTER / f"{name}.png", BEFORE / f"{name}.png"
    if not a.exists() or not b.exists():
        return {"missing": [str(p) for p in (a, b) if not p.exists()]}
    A, Bf = load(a), load(b)
    if A.shape != Bf.shape:
        return {"shape_mismatch": [A.shape, Bf.shape]}
    hh, ww = A.shape[:2]
    d = np.abs(A - Bf).max(axis=2)
    out = {"size": [ww, hh], "mean_abs_diff": round(float(np.abs(A - Bf).mean()), 3)}
    nz = NOISE / f"{name}.png"
    noise = None
    if nz.exists():
        N = load(nz)
        noise = dilate(np.abs(A - N).max(axis=2) > thr, 3)
        out["live_noise_pct"] = round(100 * noise.mean(), 3)
    sky = sky_mask(A) & sky_mask(Bf)
    out["sky_pct"] = round(100 * sky.mean(), 2)
    cam = CAMS.get(name)
    box = door_box(cam, ww, hh) if cam else None
    out["door_box_xyxy"] = box
    inbox = np.zeros((hh, ww), bool)
    if box:
        inbox[box[1]:box[3], box[0]:box[2]] = True
    out["door_box_pct_of_frame"] = round(100 * inbox.mean(), 3)
    for t in (8, 16, 24, 48):
        ch = d > t
        below = ~sky
        o = ch & below & ~inbox
        rec = {"changed_frame_pct": round(100 * ch.mean(), 3),
               "changed_in_door_box_pct_of_box": round(100 * (ch & inbox).sum() / max(1, inbox.sum()), 2),
               "changed_outside_box_below_sky_pct_of_frame": round(100 * o.mean(), 4)}
        if noise is not None:
            st = ~noise
            rec["static_changed_outside_box_below_sky_pct_of_frame"] = round(100 * (o & st).mean(), 4)
            rec["static_changed_outside_box_below_sky_px"] = int((o & st).sum())
        out[f"thr{t}"] = rec
    o = (d > thr) & ~sky & ~inbox
    if noise is not None:
        o &= ~noise
    out["static_blobs_outside_box_thr24"], out["n_blobs"] = blobs(o)
    # region means (before / after) in the door box and in the rest
    lumA, lumB = A.mean(axis=2), Bf.mean(axis=2)
    out["door_box_mean_before_after"] = [round(float(lumB[inbox].mean()), 2), round(float(lumA[inbox].mean()), 2)] if box else None
    out["rest_mean_before_after"] = [round(float(lumB[~inbox].mean()), 2), round(float(lumA[~inbox].mean()), 2)]
    if name == "CAM_Ref2Match":
        # save a visual: red = static change outside the box, yellow = in the box, blue = live noise
        vis = (A.astype(np.float32) * 0.45).astype(np.uint8)
        ch = d > thr
        if noise is not None:
            vis[noise & ch] = (60, 90, 255)
        vis[ch & inbox] = (255, 220, 0)
        vis[o] = (255, 0, 0)
        if box:
            vis[box[1]:box[3], [box[0], box[2] - 1]] = (0, 255, 0)
            vis[[box[1], box[3] - 1], box[0]:box[2]] = (0, 255, 0)
        Image.fromarray(vis).save(OUTD.parent / "VDIFF_CAM_Ref2Match.png")
    return out


if __name__ == "__main__":
    names = sys.argv[1:] or ["CAM_Ref2Match", "CAM_HallVeranda", "CAM_PlayerEyeSand", "CAM_Overview", "CAM_LandscapeRef",
                             "CAM_FromGateOut", "CAM_PeaksOverHall", "CAM_Drum", "CAM_EastYard", "CAM_RiverRapids",
                             "CAM_StairPath", "CAM_TerraceWall", "CU_Lantern", "CU_SandEye", "CU_Training",
                             "CU_HallUpperRoof"]
    res = {n: analyse(n) for n in names}
    (OUTD / "courtyard_diff.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for n, r in res.items():
        t = r.get("thr24", {})
        print(n, r.get("size"), "box", r.get("door_box_xyxy"), "noise", r.get("live_noise_pct"),
              "chg", t.get("changed_frame_pct"), "out_box", t.get("changed_outside_box_below_sky_pct_of_frame"),
              "static_out", t.get("static_changed_outside_box_below_sky_pct_of_frame"), "blobs", r.get("n_blobs"))
