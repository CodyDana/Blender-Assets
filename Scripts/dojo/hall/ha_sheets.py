"""HALL + ARMORY round, DojoLab stage: comparison sheets and numbers on the -game HighResShot stills (plain Python).

usage: py -3 -B ha_sheets.py <caps dir> [<noise caps dir>]
FIX round (2026-10-01, judge delta 7): the before stills cannot be re-shot (they are the landscape fix round's level), and
live water / foam / cloud / wind / Niagara state differs between any two runs. With a second capture of the SAME
after-state taken in a separate run at another warm-up time (<noise caps dir>), every pixel that changes between the
two after runs (> 24 / 255, dilated 3 px) is live noise; the before / after numbers are then also given on the STATIC
pixels only ('*_static'), so a change there can only come from the build.
1. BEFORE_AFTER.jpg: the landscape fix round's final stills (landscape/fix/caps) | ours, same camera, for the courtyard
   and landscape cameras; per pair the luma difference: the share of pixels changed by > 24 / 255 over the whole frame
   and inside / outside the open-door band (the three centre door bays, projected for CAM_Ref2Match / PlayerEyeSand /
   HallVeranda by a box measured on the stills), and a DIFF_<cam>.png heat map. The sky and the drifting petals and
   cloud wisps are live (UDS clouds move with real time; Niagara), so they are reported separately (top 30 % rows).
2. ARMORY_vs_OURS_<view>.png + ARMORY_vs_OURS.jpg: the armory chat's own ArmoryLab r20 stills
   (WorkFiles/armory/build/unreal/captures, read only) | ours from the same camera (CAM_AK_*) or the hall equivalent;
   luma stats of both.
3. Interior stats for every CAM_AK_* / CAM_Armory* / CAM_DoorwayIn still.
out: <caps>/json/ha_sheets.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
BEFORE = ROOT / "WorkFiles/dojo/build/landscape/fix/caps"
AK = ROOT / "WorkFiles/armory/build/unreal/captures"
BA_CAMS = ["CAM_Ref2Match", "CAM_PlayerEyeSand", "CAM_HallVeranda", "CAM_LandscapeRef", "CAM_Overview",
           "CAM_FromGateOut", "CAM_EastYard", "CU_HallUpperRoof", "CAM_Drum", "CU_SandEye", "CU_Training",
           "CU_Lantern", "CAM_RiverRapids", "CAM_StairPath", "CAM_TerraceWall", "CAM_PeaksOverHall"]
PAIRS = [("entrance looking in", "C1_EntryReveal", "CAM_ArmoryEntry"),
         ("centre aisle (west aisle view)", "CW_WestAisle", "CAM_AK_CW_WestAisle"),
         ("centre aisle (case 3)", "C3_Case3", "CAM_AK_C3_Case3"),
         ("rear platform (hero)", "C10_Hero", "CAM_AK_C10_Hero"),
         ("case close-up (shuriken tray)", "C4_ShurikenTray", "CAM_AK_C4_ShurikenTray"),
         ("case close-up (case 1)", "C2_Case1", "CAM_AK_C2_Case1"),
         ("cloak case", "C5_CloakCase", "CAM_AK_C5_CloakCase"),
         ("from the platform (ceiling, lattice)", "CX_FromPlatform", "CAM_AK_CX_FromPlatform"),
         ("ceiling", "CX_FromPlatform", "CAM_ArmoryCeiling")]


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def stats(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    lm = luma(a)
    return {"size": [a.shape[1], a.shape[0]], "mean": round(float(lm.mean()), 1),
            "p10": round(float(np.percentile(lm, 10)), 1), "p50": round(float(np.percentile(lm, 50)), 1),
            "p90": round(float(np.percentile(lm, 90)), 1), "under40_pct": round(float((lm < 40).mean() * 100), 1),
            "clipped_pct": round(float((a.max(-1) >= 254).mean() * 100), 2)}


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, min(im.width, 12 + 7 * len(text)), 22), fill=(0, 0, 0))
    d.text((6, 5), text, fill=(255, 255, 0))
    return im


def pair_sheet(a_path, b_path, out, la, lb, w=960):
    A = Image.open(a_path).convert("RGB")
    B = Image.open(b_path).convert("RGB")
    A = A.resize((w, int(A.height * w / A.width)))
    B = B.resize((w, int(B.height * w / B.width)))
    S = Image.new("RGB", (2 * w + 10, max(A.height, B.height)), (20, 20, 20))
    S.paste(label(A, la), (0, 0))
    S.paste(label(B, lb), (w + 10, 0))
    S.save(out)
    return S


def door_box(cam, size):
    """the open-door band in the frame, measured on the stills (x0, y0, x1, y1 as fractions)"""
    return {"CAM_Ref2Match": (0.43, 0.43, 0.57, 0.53), "CAM_PlayerEyeSand": (0.40, 0.30, 0.60, 0.62),
            "CAM_HallVeranda": (0.30, 0.20, 0.75, 0.80)}.get(cam)


NOISE = None


def main():
    global NOISE
    caps = Path(sys.argv[1])
    NOISE = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    (caps / "json").mkdir(exist_ok=True)
    rep = {"before_after": {}, "armory_vs_ours": {}, "interior": {}}
    tiles = []
    for cam in BA_CAMS:
        a, b = BEFORE / f"{cam}.png", caps / f"{cam}.png"
        if not (a.exists() and b.exists()):
            continue
        A = np.asarray(Image.open(a).convert("RGB")).astype(np.float32)
        Bm = np.asarray(Image.open(b).convert("RGB")).astype(np.float32)
        if A.shape != Bm.shape:
            Bm = np.asarray(Image.open(b).convert("RGB").resize((A.shape[1], A.shape[0]))).astype(np.float32)
        d = np.abs(luma(A) - luma(Bm))
        ch = d > 24.0
        h, w = ch.shape
        top = int(h * 0.30)
        noise = None
        if NOISE is not None and (NOISE / f"{cam}.png").exists():
            N2 = np.asarray(Image.open(NOISE / f"{cam}.png").convert("RGB").resize((w, h))).astype(np.float32)
            nz = np.abs(luma(Bm) - luma(N2)) > 24.0
            pad = np.pad(nz, 3)
            noise = np.zeros_like(nz)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    noise |= pad[3 + dy:3 + dy + h, 3 + dx:3 + dx + w]
        r = {"changed_pct": round(float(ch.mean() * 100), 2), "changed_pct_top30_sky": round(float(ch[:top].mean() * 100), 2),
             "changed_pct_below_sky": round(float(ch[top:].mean() * 100), 2), "mean_abs_luma_diff": round(float(d.mean()), 2)}
        box = door_box(cam, (w, h))
        if box:
            x0, y0, x1, y1 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
            m = np.zeros_like(ch)
            m[y0:y1, x0:x1] = True
            r["door_box_px"] = [x0, y0, x1, y1]
            r["changed_pct_in_door_box"] = round(float(ch[m].mean() * 100), 2)
            r["changed_pct_outside_door_box_below_sky"] = round(float(ch[top:][~m[top:]].mean() * 100), 2)
        if noise is not None:
            st = ch & ~noise
            r["live_noise_pct"] = round(float(noise.mean() * 100), 2)
            r["changed_pct_static"] = round(float(st[~noise].mean() * 100), 3) if (~noise).any() else None
            r["changed_pct_static_below_sky"] = round(float(st[top:][~noise[top:]].mean() * 100), 3)
            if box:
                ms = m & ~noise
                r["changed_pct_static_in_door_box"] = round(float(st[ms].mean() * 100), 2) if ms.any() else None
                mo = (~m) & ~noise
                r["changed_pct_static_outside_door_box_below_sky"] = round(float(st[top:][mo[top:]].mean() * 100), 3)
        ys, xs = np.where(ch[top:])
        r["changed_bbox_below_sky_px"] = ([int(xs.min()), int(ys.min() + top), int(xs.max()), int(ys.max() + top)]
                                         if len(xs) else None)
        rep["before_after"][cam] = r
        heat = Image.fromarray(np.clip(d * 4, 0, 255).astype(np.uint8)).convert("RGB")
        if noise is not None:   # live-noise pixels shown in blue, build changes in white
            hv = np.asarray(heat).copy()
            hv[noise] = (np.array([40, 60, 160]) * 0.5 + hv[noise] * 0.5).astype(np.uint8)
            heat = Image.fromarray(hv)
        heat.save(caps / f"DIFF_{cam}.png")
        tw = 640
        for im, t in ((Image.open(a).convert("RGB"), f"BEFORE (landscape fix) {cam}"),
                      (Image.open(b).convert("RGB"), f"AFTER (hall + armory) {cam}"),
                      (heat, f"|luma diff| x4 {cam}: {r['changed_pct']} % > 24"
                             + (f", static {r['changed_pct_static']} % (blue = live noise)" if noise is not None else ""))):
            tiles.append(label(im.resize((tw, int(im.height * tw / im.width))), t))
    if tiles:
        rows = [tiles[i:i + 3] for i in range(0, len(tiles), 3)]
        H = sum(max(t.height for t in rw) + 6 for rw in rows)
        S = Image.new("RGB", (3 * 646, H), (20, 20, 20))
        y = 0
        for rw in rows:
            for k, t in enumerate(rw):
                S.paste(t, (k * 646, y))
            y += max(t.height for t in rw) + 6
        S.save(caps / "BEFORE_AFTER.jpg", quality=88)
    sheets = []
    for name, ak, ours in PAIRS:
        a, b = AK / f"{ak}.png", caps / f"{ours}.png"
        if not (a.exists() and b.exists()):
            continue
        tag = ours.replace("CAM_AK_", "").replace("CAM_", "")
        S = pair_sheet(a, b, caps / f"ARMORY_vs_OURS_{tag}.png", f"ARMORY (ArmoryLab r20, night) {ak}",
                       f"OURS (DojoLab hall, sunset) {ours}")
        sheets.append(S)
        rep["armory_vs_ours"][name] = {"armory": ak, "ours": ours, "armory_stats": stats(a), "ours_stats": stats(b)}
    if sheets:
        W = max(s.width for s in sheets)
        S = Image.new("RGB", (W, sum(s.height + 6 for s in sheets)), (20, 20, 20))
        y = 0
        for s in sheets:
            S.paste(s, (0, y))
            y += s.height + 6
        S.save(caps / "ARMORY_vs_OURS.jpg", quality=88)
    for p in sorted(caps.glob("*.png")):
        if p.stem.startswith(("CAM_AK_", "CAM_Armory", "CAM_DoorwayIn", "CAM_RearExtension")):
            rep["interior"][p.stem] = stats(p)
    (caps / "json" / "ha_sheets.json").write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print("HA_SHEETS", json.dumps({k: len(v) for k, v in rep.items()}))


main()
