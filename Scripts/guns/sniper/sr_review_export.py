"""SR01 W4 review renders from the EXPORTED bytes (plain Python; renders via ONE headless Blender process running
sr_review_job.py, the W4 copy of gunlib/export_review_job.py with the scope added): SK_SR01.fbx (+ LOD1-3),
SM_SR01_Mag.fbx on the magazine bone, SM_Att_Scope_LongRange.fbx at its Mount on the rail, the shipped clips
(A_SR01_BoltCycle f14 = bolt back, A_SR01_BipodDeploy f36 = deployed) and the shipped textures; nothing from the
build blend. The SMG's smg_review_export.py is the template (SMG W4: studio rig for the realism views; blind pairs
composited on the panel's own fitted backdrop at the panel's native px).

    py -3 -B Scripts/guns/sniper/sr_review_export.py [--tag w4] [--samples 128] [--no-render] [--only set,realism,blind]

(a) review/<tag>/set/: right / left / top (ortho, 1x = 2560 px over 1100 mm), q34, deployed hero, bolt open (f14),
    scope close + eyepiece view, FP ~35 cm on the action, close-ups 3x (action right / left, forend + bipod, butt,
    magazine + well, muzzle), wireframe right.
(b) review/<tag>/realism/: fp_35cm, ads_eyepiece, tp_3m, hero_34, deployed_34 on the studio-HDRI rig.
(c) review/<tag>/blind/: the sheet's four panels (GR = sheet LEFT, GL = sheet RIGHT mirrored, TOP, Q34 through the
    solved camera scratch/w4/q34_camera.json) + 10 windows of the side panels. Ours: rendered at 3x the panel's px/mm,
    transparent, aligned to the traced silhouette (translation only, +-12 px), composited on the panel's fitted
    quadratic backdrop, reduced to native px with LANCZOS; both images then enlarged 2x with the same filter.
    pair_NN_A/B.png; ours = B on OURS_B, A elsewhere; key in review/<tag>/blind_key.json.
Writes gates/review_export.json (images made, poses read back).
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, GRIP, D, GATES, WORK, TRACE, CROPS  # noqa: E402

BL = "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
EXP = ROOT / "Exports" / "Guns" / "SR01"
OURS_B = {1, 3, 4, 7, 9, 10, 12, 14}
MOUNT_M = [float(v) for v in D["scope_attachment"]["mount_M"]]
# the SMG W4b r2 product set (smg_review_export.STUDIO): neutral interior HDRI low for ambient reflections, softboxes in
# the side and top faces' mirror directions, two edge strips and a weak key; the camera sees a flat sRGB 150 backdrop
STUDIO = {"rig": "studio", "hdri": "interior", "strength": 0.15, "saturation": 0.0, "k": 0.0,
          "bg_rgb": [150, 150, 150],
          "extra_lights": [
              {"name": "Flank", "mirror_n_M": "flank", "nudge_cam": [0.0, 0.55, 0.0], "dist": 1.3, "size": [1.2, 0.3],
               "energy": 2.5},
              {"name": "Top", "mirror_n_M": [0.0, 0.0, 1.0], "nudge_cam": [0.0, 0.1, 0.0], "dist": 1.3,
               "size": [1.4, 0.3], "energy": 7.0},
              {"name": "StripL", "dir_cam": [-0.9, 0.25, -0.45], "dist": 1.2, "size": [0.1, 1.4], "energy": 22.0},
              {"name": "StripR", "dir_cam": [0.9, 0.25, -0.45], "dist": 1.2, "size": [0.1, 1.4], "energy": 22.0},
              {"name": "Key", "dir_cam": [-0.5, 0.7, 0.5], "dist": 1.4, "size": [0.6, 0.6], "energy": 2.5}]}


def lit(cam):
    """the studio rig centred on the shot's own target (the solved Q34 camera: the gun's middle)."""
    return dict(STUDIO, target_M=list(cam.get("target_M", [550.0, 0.0, -40.0])))
WIN_MM = {"stock": (-10, 330, -185, 70), "action": (250, 560, -175, 115), "forend": (540, 900, -120, 60),
          "muzzle": (850, 1110, -70, 40), "scope": (250, 700, 0, 125)}


def look(eye, tgt, fov=None, res=(1600, 1000), ortho=None, up=None):
    d = {"type": "LOOK", "eye_M": list(eye), "target_M": list(tgt), "res": list(res)}
    if ortho:
        d["ortho_width_mm"] = ortho
    else:
        d["fov_deg"] = fov
    if up:
        d["up_M"] = list(up)
    return d


def side(xc, zc, w_mm, res, from_left=False):
    y = 2000.0 if from_left else -2000.0
    return look((xc, y, zc), (xc, 0.0, zc), res=res, ortho=w_mm)


BOLT_BACK = {"clip": "A_SR01_BoltCycle", "frame": 14}
DEPLOYED = {"clip": "A_SR01_BipodDeploy", "frame": 36}
ALL = ["gun", "mag", "scope"]


def set_shots(out):
    px = 2560 / 1200.0                                # px per mm at 1x (2560 px over a 1200 mm frame)
    S = [("right", side(550, -60, 1200, (2560, 1000))), ("left", side(550, -60, 1200, (2560, 1000), True)),
         ("top", look((550, 0, 2000), (550, 0, 0), res=(2560, 800), ortho=1200, up=(0, 1, 0))),
         ("q34", look((1180, -820, 300), (560, 0, -20), 30.0)),
         ("deployed_hero", look((1500, -1050, 80), (560, 0, -90), 36.0), DEPLOYED),
         ("bolt_open", look((420, -520, 160), (360, 0, 0), 30.0), BOLT_BACK),
         ("scope_close", look((330, -260, 150), (420, 0, 60), 34.0)),
         ("eyepiece_view", look((185, 0, 61.5), (700, 0, 61.5), 40.0)),
         ("fp_action", look((130, -140, 150), (420, -10, 0), 55.0))]
    for name, (x0, x1, z0, z1) in WIN_MM.items():     # close-ups at 3x
        w = x1 - x0
        res = (int(round(w * px * 3)), int(round((z1 - z0) * px * 3)))
        S.append((f"close_{name}_right", side((x0 + x1) / 2, (z0 + z1) / 2, w, res)))
    S.append(("close_action_left", side(405, -30, 310, (int(310 * px * 3), int(290 * px * 3)), True)))
    S.append(("close_mag_well", side(460, -95, 160, (int(160 * px * 3), int(130 * px * 3)))))
    shots = []
    for row in S:
        name, cam = row[0], row[1]
        pose = row[2] if len(row) > 2 else None
        sh = {"name": f"set_{name}", "out": str(out / f"{name}.png"), "camera": cam, "show": ALL, "lights": lit(cam)}
        if pose:
            sh["pose"] = pose
        shots.append(sh)
    shots.append({"name": "set_wire_right", "out": str(out / "wire_right.png"), "camera": side(550, -60, 1200, (2560, 1000)),
                  "show": ALL, "look": "wire", "lights": lit({})})
    return shots


def realism_shots(out):
    t = np.array([550.0, 0.0, -40.0])
    d = np.array([0.6, -0.75, 0.28])
    e3 = t + 3000.0 * d / np.linalg.norm(d)
    R = [("fp_35cm", look((130, -140, 150), (420, -10, 0), 55.0, (1920, 1080))),
         ("ads_eyepiece", look((185, 0, 61.5), (700, 0, 61.5), 40.0, (1920, 1080))),
         ("tp_3m", look(e3.tolist(), t.tolist(), 40.0, (1920, 1080))),
         ("hero_34", look((1180, -820, 300), (560, 0, -20), 30.0, (1920, 1080))),
         ("deployed_34", look((1500, -1050, 80), (560, 0, -90), 36.0, (1920, 1080)), DEPLOYED)]
    shots = []
    for row in R:
        sh = {"name": f"realism_{row[0]}", "out": str(out / f"{row[0]}.png"), "camera": row[1], "show": ALL,
              "lights": lit(row[1]), "samples": 512, "denoise": False}     # SMG W4b: the denoiser reads as plastic
        if len(row) > 2:
            sh["pose"] = row[2]
        shots.append(sh)
    return shots


# ------------------------------------------------------------------------------------------------ blind
def panels():
    P = {}
    for n in ("GR", "GL", "TOP"):
        o = json.loads((TRACE / f"{n}_outline.json").read_text())
        im = Image.open(CROPS / f"{n}.png").convert("RGB")
        P[n] = {"o": o, "im": im, "ppm": float(o["px_per_mm"])}
    P["Q34"] = {"im": Image.open(CROPS / "Q34.png").convert("RGB")}
    return P


def blind_shots(out, P):
    shots = []
    for n in ("GR", "GL"):
        W, H = P[n]["im"].size
        ppm, o = P[n]["ppm"], P[n]["o"]
        xc = (W / 2.0 - 0.5 - o["x_rear_px"]) / ppm
        zc = (o["bore_y_px"] - (H / 2.0 - 0.5)) / ppm
        shots.append({"name": f"blind_{n}", "out": str(out / f"{n}_3x.png"), "transparent": True,
                      "camera": side(xc, zc, W / ppm, (W * 3, H * 3), from_left=(n == "GL")), "show": ALL,
                      "lights": lit({"target_M": [xc, 0.0, zc]})})
    W, H = P["TOP"]["im"].size
    ppm = P["TOP"]["ppm"]
    # the TOP panel's px <-> mm map from its traced outline (u = muzzle-ward X, v = down = gun's right, -Y)
    sil = P["TOP"]["o"]["silhouette"]
    pxs = np.vstack([np.array(c, float) for c in sil["px"]])
    mms = np.vstack([np.array(c, float) for c in sil["mm"]])
    xc = float(np.mean(mms[:, 0] + ((W / 2.0 - 0.5) - pxs[:, 0]) / ppm))
    yc = float(np.mean(mms[:, 1] - ((H / 2.0 - 0.5) - pxs[:, 1]) / ppm))
    shots.append({"name": "blind_TOP", "out": str(out / "TOP_3x.png"), "transparent": True,
                  "camera": look((xc, yc, 2000), (xc, yc, 0), res=(W * 3, H * 3), ortho=W / ppm, up=(0, 1, 0)),
                  "show": ALL, "lights": lit({})})
    q = json.loads((WORK / "scratch" / "w4" / "q34_camera.json").read_text())
    shots.append({"name": "blind_Q34", "out": str(out / "Q34_3x.png"), "transparent": True, "ss": 3, "camera": q,
                  "show": ALL, "lights": lit({})})
    return shots


def backdrop(im, mask):
    """quadratic per-channel fit of the panel outside the (dilated) gun mask."""
    from PIL import ImageFilter
    a = np.asarray(im, float)
    H, W = mask.shape
    m = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(15))) > 0
    yy, xx = np.mgrid[0:H, 0:W]
    x, y = xx / W, yy / H
    A = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y, y * y * y], -1)
    sel = ~m
    sel[:2, :] = sel[-2:, :] = False
    sel[:, :2] = sel[:, -2:] = False
    out = np.zeros_like(a)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(A[sel], a[..., c][sel], rcond=None)
        out[..., c] = A @ coef
    return np.clip(out, 0, 255)


def compose(P, n, src, mirror):
    ref = P[n]["im"]
    W, H = ref.size
    ours = Image.open(src).convert("RGBA")
    if mirror:
        ours = ours.transpose(Image.FLIP_LEFT_RIGHT)
    small = ours.resize((W, H), Image.LANCZOS)
    alpha = np.asarray(small, float)[..., 3] / 255.0
    mask = np.array(Image.open(TRACE / f"{n}_silhouette.png").convert("L")) > 127
    mask[:2, :] = mask[-2:, :] = False
    mask[:, :2] = mask[:, -2:] = False
    best, bs = (0, 0), -1.0                                 # translation-only alignment to the traced silhouette
    for dy in range(-12, 13):
        for dx in range(-12, 13):
            a2 = np.roll(np.roll(alpha > 0.5, dy, 0), dx, 1)
            s = (a2 & mask).sum() / max((a2 | mask).sum(), 1)
            if s > bs:
                best, bs = (dy, dx), s
    rgba = np.roll(np.roll(np.asarray(small, float), best[0], 0), best[1], 1)
    bg = backdrop(ref, mask)
    al = rgba[..., 3:4] / 255.0
    comp = rgba[..., :3] * al + bg * (1 - al)
    return Image.fromarray(comp.astype(np.uint8)), {"shift_px": best, "iou_after_shift": round(float(bs), 4)}


def blind(P, src_dir, out, keyf):
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("pair_*.png"):
        f.unlink()
    pairs, info = [], {}
    for n in ("GR", "GL", "TOP", "Q34"):
        ours, inf = compose(P, n, src_dir / f"{n}_3x.png", n == "GL")
        ours.save(src_dir / f"{n}_native.png")
        info[n] = inf
        pairs.append((f"{n} full panel", P[n]["im"], ours))
        if n in ("GR", "GL"):
            o, ppm = P[n]["o"], P[n]["ppm"]
            for wn, (x0, x1, z0, z1) in WIN_MM.items():
                box = (int(o["x_rear_px"] + x0 * ppm), int(o["bore_y_px"] - z1 * ppm),
                       int(o["x_rear_px"] + x1 * ppm), int(o["bore_y_px"] - z0 * ppm))
                pairs.append((f"{n} window {wn}", P[n]["im"].crop(box), ours.crop(box)))
    key = {}
    for i, (label, ref, ours) in enumerate(pairs, 1):
        f = 2 if ref.size[0] > 300 else 4
        big = lambda im: im.resize((im.size[0] * f, im.size[1] * f), Image.LANCZOS)  # noqa: E731
        a, b = (big(ref), big(ours)) if i in OURS_B else (big(ours), big(ref))
        a.save(out / f"pair_{i:02d}_A.png")
        b.save(out / f"pair_{i:02d}_B.png")
        key[f"pair_{i:02d}"] = {"label": label, "ours": "B" if i in OURS_B else "A"}
    keyf.write_text(json.dumps({"pairs": key, "alignment": info}, indent=1))
    return len(pairs), info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="w4")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--only", default="set,realism,blind")
    a = ap.parse_args()
    only = set(a.only.split(","))
    R = WORK / "review" / a.tag
    jobd = WORK / "scratch" / "w4" / "review_job"
    jobd.mkdir(parents=True, exist_ok=True)
    P = panels()
    shots = []
    if "set" in only:
        shots += set_shots(R / "set")
    if "realism" in only:
        shots += realism_shots(R / "realism")
    if "blind" in only:
        shots += blind_shots(R / "blind_src", P)
    job = {"exports_dir": str(EXP), "tex_dir": str(EXP / "Textures"), "offset_M": GRIP.tolist(),
           "gun_lods": ["SK_SR01.fbx", "SK_SR01_LOD1.fbx", "SK_SR01_LOD2.fbx", "SK_SR01_LOD3.fbx"],
           "mag_fbx": "SM_SR01_Mag.fbx", "mag_lod_prefix": "SM_SR01_Mag_LOD", "mag_bone": "magazine",
           "scope_fbx": "SM_Att_Scope_LongRange.fbx", "scope_lod_prefix": "SM_Att_Scope_LongRange_LOD",
           "scope_origin_M": MOUNT_M, "clips": ["A_SR01_BoltCycle", "A_SR01_BipodDeploy"],
           "materials": {"M_SR01_Metal": "T_SR01_Metal", "M_SR01_Chassis": "T_SR01_Chassis", "M_SR01_Mag": "T_SR01_Mag",
                         "M_Att_Scope_Body": "T_Att_Scope_LongRange_Scope_Body",
                         "M_Att_Scope_Lens": "T_Att_Scope_LongRange_Scope_Lens"},
           "samples": a.samples, "result": str(jobd / f"result_{a.tag}.json"), "shots": shots}
    jf = jobd / f"job_{a.tag}.json"
    jf.write_text(json.dumps(job, indent=1))
    if not a.no_render and shots:
        log = jobd / f"job_{a.tag}.log"
        with open(log, "w") as fh:
            subprocess.run([BL, "-b", "--factory-startup", "--python", str(HERE / "sr_review_job.py"), "--",
                            "--job", str(jf)], stdout=fh, stderr=subprocess.STDOUT)
        txt = log.read_text(errors="replace")
        if "EXPORT_REVIEW_DONE" not in txt:
            print(txt[-3000:])
            raise SystemExit("review job failed")
    res = json.loads((jobd / f"result_{a.tag}.json").read_text())
    nb, info = (0, {})
    if "blind" in only:
        nb, info = blind(P, R / "blind_src", R / "blind", R / "blind_key.json")
    nimg = sum(len(list((R / d).glob("*.png"))) for d in ("set", "realism", "blind_src") if (R / d).exists())
    rec = {"stage": f"W4 review renders from the exported bytes ({a.tag})",
           "date": datetime.date.today().isoformat(), "images": nimg, "blind_pairs": nb,
           "blind_alignment": info, "gun_faces_per_lod": res["gun_faces"], "mag_faces": res["mag_faces"],
           "rest_bolt_M_mm": res["rest_bolt_M_mm"],
           "bolt_back_M_mm": next((s["bones_M_mm"].get("bolt") for s in res["shots"] if s["name"] == "set_bolt_open"),
                                  None),
           "sources": "Exports/Guns/SR01 (SK_SR01 + LOD1-3, SM_SR01_Mag, SM_Att_Scope_LongRange, 2 clips, Textures)"}
    (GATES / ("review_export.json" if a.tag == "w4" else f"review_export_{a.tag}.json")).write_text(
        json.dumps(rec, indent=1))
    print("[SR01-review] DONE", json.dumps({k: rec[k] for k in ("images", "blind_pairs")}), json.dumps(info))


if __name__ == "__main__":
    main()
