"""SMG01 W4 review renders from the EXPORTED bytes (plain Python; renders via headless Blender,
gunlib/export_review_job.py): SK_SMG01.fbx (+ LOD1-3), SM_SMG01_Mag.fbx on the magazine bone, the shipped clips
(A_SMG01_Charge, A_SMG01_Reload, A_SMG01_StockFold) and the shipped textures; nothing from the build blend.
The AR-01's rifle_review_export.py is the template (RIFLE_REPORT 10 lessons: physical light, clips that move the bolt
hold the selector at a firing position, the magazine on its bone).

    py -3 -B Scripts/guns/smg/smg_review_export.py [--only blind,realism,set] [--samples 128] [--no-render]

(a) Blind design test (SMG_BUILD_PLAN 14.1 L7, >= 12 pairs, reported not blocking): the four sheet panels (LEFT side,
    RIGHT side as drawn, TOP, the 3/4 FRONT (LEFT) through the solved camera scratch/q34/camera_form.json) and eleven
    windows of those panels (receiver, grip / trigger / selector, magazine + well, front end, rear sight, port side,
    stock, top rail, top front, 3/4 front, 3/4 grip + magazine). Ours is rendered at 3x the panel with a transparent
    film, composited on the panel's own fitted studio backdrop, reduced to the panel's native px and enlarged with the
    same LANCZOS filter as the reference crop (both carry the panel's resolution: a judge decides on design, not
    sharpness). review/blind/pair_NN_A.png / _B.png; ours = B on pairs in OURS_B (fixed irregular order), A elsewhere;
    the key in review/blind_key.json; our native 3x composites + the unblinded contact in review/blind_src/.
(b) Realism set review/realism/ (fp_35cm, ads_55deg (eye 0.25 m behind the Sight socket on the sight line, 55 deg),
    tp_3m, hero_34 = the early-realism cameras, + hero_34_folded = the L7 folded-stock hero) and the review set
    review/set/ (receiver both sides 3x, grip / trigger / selector 3x both sides, front end 3x, sights 3x, magazine
    2x, stock extended + folded, reload poses, bolt at full travel, LOD strip, wireframe).
    1x = 2560 px across the 625 mm gun (4.096 px/mm); 2x = 8.19 px/mm; 3x = 12.29 px/mm.
Light: the L5 physical rig the colour was calibrated on (scratch/l5/l5.json fit: k 1.3432, key 70 deg, world 0.2),
centred on each shot's target; the 3/4 panel pairs use the rough rig on the panel's fitted backdrop (AR-01 method).
(W4 resume) the realism views review/realism/<name>.png use the photographic STUDIO rig (gunlib export_review_job
'studio'); their L5 versions are in review/realism/l5/.
Writes gates/review_export.json (counts of images made, poses read back and the framing checks).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from smg_common import ROOT, GRIP, SCRATCH, TRACE, REVIEW, GATES, SHEET, WORK, socket  # noqa: E402

import gunlib  # noqa: E402
from gunlib import compare as C  # noqa: E402
from gunlib import closeup as CU  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "SMG01"
TEXD = EXP / "Textures"
JOBD = SCRATCH / "export_review"
BLIND = REVIEW / "blind"
BSRC = REVIEW / "blind_src"
REAL = REVIEW / "realism"
SETD = REVIEW / "set"
KEYF = REVIEW / "blind_key.json"
SS = 3
SIDE_ROWS = 470                 # side panels: rows above the 0-70 cm ruler (its ticks start near panel row 488)
OURS_B = {1, 2, 4, 7, 8, 11, 13, 14}   # pairs where ours is image B (fixed irregular order); A elsewhere
PX1 = 2560.0 / 625.0            # 1x review scale (px / mm)
Q34_BOX = tuple(json.loads((WORK / "smg_measured.json").read_text())["panels_sheet_px_x0_y0_x1_y1_inclusive"]
                ["Q34_FRONT_LEFT"])
CLIPS = ["A_SMG01_Charge", "A_SMG01_Reload", "A_SMG01_StockFold"]


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


_SHEET = None


def sheet_rgb():
    global _SHEET
    if _SHEET is None:
        _SHEET = np.asarray(Image.open(SHEET).convert("RGB")).astype(float)
    return _SHEET


def panel(box):
    x0, y0, x1, y1 = box
    return sheet_rgb()[y0:y1 + 1, x0:x1 + 1]


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# ------------------------------------------------------------------------------------------------ cameras
def frame_camera(view, fit=(0.0, 0.0, 0.0, 0.0), unmirror=False):
    """ORTHO camera JSON reproducing a trace panel's px <-> mm map (gunlib.compare.PanelFrame) after the silhouette
    gate's similarity fit (scale, rot deg, tx, ty about the panel centre). Side panels map (X, Z), the top (X, Y).
    unmirror: the RIGHT panel's frame is in the MIRRORED crop; the camera then looks from -Y (the true right) and its
    image is the panel as drawn (muzzle to the right)."""
    fr, _j = C.load_trace(TRACE, view)
    H, W = fr.shape
    ds, rdeg, tx, ty = fit
    c = np.array([W / 2.0, H / 2.0])
    r = math.radians(rdeg)
    Rr = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    k = (1.0 + ds) * fr.s
    e, f = Rr @ fr.u, Rr @ fr.n
    A0 = c + (1.0 + ds) * Rr @ (fr.p0 - c) + np.array([tx, ty])
    if unmirror:
        e, f = np.array([-e[0], e[1]]), np.array([-f[0], f[1]])
        A0 = np.array([W - 1.0 - A0[0], A0[1]])
    a0 = np.array([1.0, 0.0, 0.0])
    a1 = np.array([0.0, 1.0, 0.0]) if view == "TOP" else np.array([0.0, 0.0, 1.0])
    rgt = e[0] * a0 + f[0] * a1
    upv = -e[1] * a0 - f[1] * a1
    rgt, upv = rgt / np.linalg.norm(rgt), upv / np.linalg.norm(upv)
    fwd = np.cross(upv, rgt)
    cpx = np.array([W / 2.0 - 0.5, H / 2.0 - 0.5])
    Q = np.linalg.solve(np.c_[e, f], (cpx - A0) / k)
    centre = Q[0] * a0 + Q[1] * a1
    return {"type": "ORTHO", "R_rows_right_up_fwd_M": [rgt.tolist(), upv.tolist(), fwd.tolist()],
            "image_centre_point_M": centre.tolist(), "px_per_mm": float(k), "ortho_width_mm": float(W / k),
            "panel_px": [W, H], "source": f"trace/{view}_outline.json frame + gate fit {[round(v, 4) for v in fit]}"
                                          + (" (unmirrored: view from -Y, the panel as drawn)" if unmirror else "")}


def ortho_look(centre_M, view_dir, width_mm, height_mm, pxmm, up=(0.0, 0.0, 1.0)):
    """Orthographic camera (ORTHO JSON, explicit axes): view_dir = direction the camera looks along (M); image up =
    `up` projected off view_dir."""
    c = np.asarray(centre_M, float)
    d = unit(view_dir)
    u = np.asarray(up, float)
    u = unit(u - d * float(u @ d))
    rgt = np.cross(d, u)
    W, H = int(round(width_mm * pxmm)), int(round(height_mm * pxmm))
    return {"type": "ORTHO", "R_rows_right_up_fwd_M": [rgt.tolist(), u.tolist(), d.tolist()],
            "image_centre_point_M": c.tolist(), "ortho_width_mm": float(width_mm), "panel_px": [W, H],
            "px_per_mm": float(pxmm)}


def persp_look(eye, tgt, fov, res):
    return {"type": "LOOK", "eye_M": [float(v) for v in eye], "target_M": [float(v) for v in tgt], "fov_deg": fov,
            "res": list(res)}


def l5_params():
    d = json.loads((SCRATCH / "l5" / "l5.json").read_text())
    f = d["fit"]
    return {"k": float(f["light_scale"]), "env": float(f["rig"]["world_env"]),
            "key_elev_deg": float(f["rig"]["key_elev_deg"])}


def l5_l(target, fill=0.0, bg=(126, 126, 126)):
    return dict(l5_params(), rig="l5", bg_rgb=list(bg), target_M=[float(v) for v in target], fill=float(fill))


# (W4 resume) the realism views' studio rig (gunlib export_review_job 'studio'): Blender's bundled studio.exr (CC0),
# saturation 0, strength 0.6, + the rough rig's softboxes at k 0.3 (0.85 x 0.35: the W2 texrender's rough light scaled)
# (W4b close-up r1, spec R46) the bundled interior.exr (CC0, Poly Haven hotel_room: window light with structure) at
# strength 0.45 + the softboxes at k 0.12. The R45 rig (studio.exr 0.6 + k 0.3) lit the black polymer to sRGB 80-85 on
# the hero's receiver side, twice the L5 calibration's exposure (41; the sheet's own receiver 63-64): the judges read
# "mid-grey clay, not black polymer". Measured on hero_34 with the r1 maps: receiver side 42, stock 61, magazine 51
# (studio.exr 0.32 / k 0.16 tried: 62 / 74 / 48, flatter; courtyard 0.35: 42 / 59 / 46, less structure)
STUDIO = {"rig": "studio", "hdri": "interior", "strength": 0.45, "saturation": 0.0, "k": 0.12,
          "bg_rgb": [126, 126, 126]}


def form_fits():
    v = json.loads((GATES / "form.json").read_text())["details"]["silhouette"]["views"]
    return {k: tuple(v[k]["fit_params_s_rotdeg_tx_ty"]) for k in ("LEFT", "RIGHT", "TOP")}


def q34_camera():
    q = json.loads((SCRATCH / "q34" / "camera_form.json").read_text())
    W, H = Q34_BOX[2] - Q34_BOX[0] + 1, Q34_BOX[3] - Q34_BOX[1] + 1
    return dict(q, type="PERSP", panel_px=[W, H], source="scratch/q34/camera_form.json (solved, W1 form)")


# ------------------------------------------------------------------------------------------------ blind
PANEL = {}


def blind_shots(samples):
    fits = form_fits()
    shots, meta = [], {}

    def add(n, subject, box, cam, lights, crop_rows=None, **kw):
        out = JOBD / "blind" / f"panel_{n:02d}.png"
        shots.append(dict({"name": f"panel_{n:02d}", "out": str(out), "camera": cam, "ss": SS, "transparent": True,
                           "lights": lights, "samples": samples}, **kw))
        meta[n] = {"subject": subject, "box": list(box), "render": str(out), "crop_rows": crop_rows, "camera": cam}

    def rough(box, target):
        _, _, _, bg = CU.fit_background(panel(box))
        return {"rig": "rough", "bg_rgb": [float(v) for v in bg.reshape(-1, 3).mean(0)], "env": 0.55, "k": 1.35,
                "dist_m": 1.1, "target_M": list(target)}

    jl = json.loads((TRACE / "LEFT_outline.json").read_text())
    jr = json.loads((TRACE / "RIGHT_outline.json").read_text())
    jt = json.loads((TRACE / "TOP_outline.json").read_text())
    add(1, "LEFT SIDE VIEW panel", jl["panel_box_sheet_px"], frame_camera("LEFT", fits["LEFT"]),
        l5_l((330.0, 0.0, -40.0)), SIDE_ROWS)
    add(2, "RIGHT SIDE VIEW panel (as drawn)", jr["panel_box_sheet_px"],
        frame_camera("RIGHT", fits["RIGHT"], unmirror=True), l5_l((330.0, 0.0, -40.0)), SIDE_ROWS)
    add(3, "TOP VIEW panel", jt["panel_box_sheet_px"], frame_camera("TOP", fits["TOP"]), l5_l((330.0, 0.0, 0.0)))
    add(4, "3/4 FRONT VIEW (LEFT) panel (solved camera)", Q34_BOX, q34_camera(),
        rough(Q34_BOX, (380.0, 0.0, -40.0)))
    return shots, meta


# windows of the panels for pairs 5-15: (pair, subject, source panel pair, window in M mm or panel px)
WINDOWS = [
    (5, "LEFT: receiver, charging knob, vents", 1, ("XZ", 380.0, 570.0, -45.0, 85.0)),
    (6, "LEFT: grip, trigger, guard, selector", 1, ("XZ", 265.0, 410.0, -165.0, -10.0)),
    (7, "LEFT: magazine + magazine well, release paddle", 1, ("XZ", 385.0, 485.0, -240.0, -25.0)),
    (8, "LEFT: front end (muzzle device, front sight, lower rail)", 1, ("XZ", 520.0, 632.0, -50.0, 88.0)),
    (9, "LEFT: rear sight, end block, hinge", 1, ("XZ", 225.0, 335.0, -45.0, 88.0)),
    (10, "RIGHT: receiver port side (ejection port, vents)", 2, ("XZ", 380.0, 570.0, -45.0, 85.0)),
    (11, "RIGHT: stock + hinge + butt pad", 2, ("XZ", -5.0, 280.0, -95.0, 40.0)),
    (12, "TOP: receiver + top rail", 3, ("XY", 280.0, 570.0, -50.0, 50.0)),
    (13, "TOP: front end + charging knob", 3, ("XY", 480.0, 632.0, -60.0, 60.0)),
    (14, "3/4 FRONT (LEFT): muzzle, front sight, receiver front", 4, ("PX", 0, 50, 330, 300)),
    (15, "3/4 FRONT (LEFT): grip, trigger, magazine", 4, ("PX", 150, 240, 440, 515)),
]


def window_px(src, win, W):
    kind = win[0]
    if kind == "PX":
        return tuple(int(v) for v in win[1:])
    view = {1: "LEFT", 2: "RIGHT", 3: "TOP"}[src]
    fr, _ = C.load_trace(TRACE, view)
    x0m, x1m, a0, a1 = win[1:]
    corners = fr.px(np.array([[x0m, a0], [x1m, a0], [x0m, a1], [x1m, a1]], float))
    if view == "RIGHT":                       # the frame is the mirrored crop; the pair shows the panel as drawn
        corners[:, 0] = W - 1.0 - corners[:, 0]
    x0, y0 = np.floor(corners.min(0)).astype(int)
    x1, y1 = np.ceil(corners.max(0)).astype(int)
    return int(max(x0, 0)), int(max(y0, 0)), int(x1), int(y1)


def iou_mask(alpha, ref):
    a, b = alpha > 0.5, ref.astype(bool)
    return float((a & b).sum() / max((a | b).sum(), 1))


def ref_masks():
    out = {}
    frL, jL = C.load_trace(TRACE, "LEFT")
    out[1] = C.rings_mask([r["px"] for r in jL["silhouette"]], frL.shape)
    frR, jR = C.load_trace(TRACE, "RIGHT")
    out[2] = C.rings_mask([r["px"] for r in jR["silhouette"]], frR.shape)[:, ::-1]
    frT, jT = C.load_trace(TRACE, "TOP")
    out[3] = C.rings_mask([r["px"] for r in jT["silhouette"]], frT.shape)
    try:
        import smg_q34 as Q
        out[4], _ = Q.ref_mask()
    except Exception as ex:  # noqa: BLE001
        print("[review_export] 3/4 mask unavailable:", ex)
    return out


def _write_pair(n, ref_img, our_img, subject, box, cam, framing, native):
    ours_is = "B" if n in OURS_B else "A"
    ref_is = "A" if ours_is == "B" else "B"
    assert ref_img.size == our_img.size
    (our_img if ours_is == "A" else ref_img).convert("RGB").save(BLIND / f"pair_{n:02d}_A.png")
    (our_img if ours_is == "B" else ref_img).convert("RGB").save(BLIND / f"pair_{n:02d}_B.png")
    return {"subject": subject, "ours": ours_is, "reference": ref_is, "size": list(ref_img.size),
            "framing": framing, "sheet_box_px": list(box),
            "camera": cam.get("source") or ("PERSP solved" if cam["type"] == "PERSP" else "ORTHO"),
            "our_native_3x": rel(native)}


def make_blind(meta):
    BLIND.mkdir(parents=True, exist_ok=True)
    BSRC.mkdir(parents=True, exist_ok=True)
    for p in BLIND.glob("pair_*.png"):
        p.unlink()
    masks = ref_masks()
    key, checks, small = {}, {}, {}
    for n in range(1, 5):
        m = meta[n]
        P = panel(m["box"])
        rgba = np.asarray(Image.open(m["render"]).convert("RGBA"))
        H, W = P.shape[:2]
        assert rgba.shape[:2] == (H * SS, W * SS), (n, rgba.shape, P.shape)
        alpha_small = CU.downscale(np.repeat(rgba[:, :, 3:4], 3, 2).astype(np.uint8), SS)[:, :, 0] / 255.0
        if n in masks:
            checks[f"pair_{n:02d}"] = {"silhouette_iou_vs_reference": round(iou_mask(alpha_small, masks[n]), 4)}
        rows = m["crop_rows"] or H
        Pc = P[:rows]
        _, _, _, bg = CU.fit_background(P)
        ours3 = CU.composite_on(bg[:rows], rgba[:rows * SS], SS)
        Image.fromarray(ours3).save(BSRC / f"ours_native3x_{n:02d}.png")
        ours1 = np.asarray(Image.fromarray(ours3).resize((W, rows), Image.BOX))
        small[n] = (Pc, ours1, ours3, W)
        ref_img = Image.fromarray(np.clip(Pc, 0, 255).astype(np.uint8)).resize((W * SS, rows * SS), Image.LANCZOS)
        our_img = Image.fromarray(ours1).resize((W * SS, rows * SS), Image.LANCZOS)
        key[n] = _write_pair(n, ref_img, our_img, m["subject"], m["box"], m["camera"],
                             f"panel {m['box']} rows 0-{rows} at 3x", BSRC / f"ours_native3x_{n:02d}.png")
    for n, subject, src, win in WINDOWS:
        Pc, ours1, ours3, W = small[src]
        x0, y0, x1, y1 = window_px(src, win, W)
        y1, x1 = min(y1, Pc.shape[0]), min(x1, Pc.shape[1])
        k = max(3, int(round(1100.0 / max(x1 - x0, y1 - y0))))
        rc = Image.fromarray(np.clip(Pc[y0:y1, x0:x1], 0, 255).astype(np.uint8))
        oc = Image.fromarray(ours1[y0:y1, x0:x1])
        sz = ((x1 - x0) * k, (y1 - y0) * k)
        nat = BSRC / f"ours_native3x_{n:02d}.png"
        Image.fromarray(ours3[y0 * SS:y1 * SS, x0 * SS:x1 * SS]).save(nat)
        key[n] = _write_pair(n, rc.resize(sz, Image.LANCZOS), oc.resize(sz, Image.LANCZOS), subject,
                             meta[src]["box"], meta[src]["camera"],
                             f"window x {x0}-{x1}, y {y0}-{y1} (panel px) of pair {src:02d}'s panel at {k}x", nat)
    return key, checks


def contact_pairs(key):
    tiles = []
    n_pairs = len([k for k in key if k.startswith("pair_")])
    for n in range(1, n_pairs + 1):
        a = Image.open(BLIND / f"pair_{n:02d}_A.png").convert("RGB")
        b = Image.open(BLIND / f"pair_{n:02d}_B.png").convert("RGB")
        h = 300
        a = a.resize((max(1, int(a.width * h / a.height)), h), Image.LANCZOS)
        b = b.resize((max(1, int(b.width * h / b.height)), h), Image.LANCZOS)
        t = Image.new("RGB", (a.width + b.width + 10, h + 22), (255, 255, 255))
        t.paste(a, (0, 22))
        t.paste(b, (a.width + 10, 22))
        kk = key[f"pair_{n:02d}"]
        ImageDraw.Draw(t).text((4, 4), f"{n:02d} {kk['subject'][:60]}  A={'ours' if kk['ours'] == 'A' else 'ref'}  "
                                       f"B={'ours' if kk['ours'] == 'B' else 'ref'}", fill=(0, 0, 0))
        tiles.append(t)
    Wd = max(t.width for t in tiles)
    out = Image.new("RGB", (Wd, sum(t.height + 6 for t in tiles)), (255, 255, 255))
    y = 0
    for t in tiles:
        out.paste(t, (0, y))
        y += t.height + 6
    if out.height > 5000:
        out = out.resize((int(out.width * 5000 / out.height), 5000), Image.LANCZOS)
    out.save(BSRC / "key_contact_UNBLINDED.png")


# ------------------------------------------------------------------------------------------------ realism + set
def sights():
    s = np.array(socket("Sight")["M_mm"], float)
    post = np.array(socket("SightFront")["M_mm"], float)
    return s, post


def realism_shots(samples):
    s, post = sights()
    ads_eye = s - 250.0 * unit(post - s)
    fp_r = np.array([360.0, 0.0, 10.0])
    fp_t = np.array([620.0, 0.0, 10.0])
    hero_t = np.array([380.0, 0.0, -30.0])
    fold_t = np.array([330.0, -20.0, -30.0])
    S = [("fp_35cm", persp_look(fp_r + 350.0 * unit([-0.93, 0.22, 0.30]), fp_t, 70.0, (1600, 900)), l5_l(fp_t), {},
          "first person: eye 35 cm from the receiver, behind / left / above (right-handed hold), 70 deg FOV"),
         ("ads_55deg", persp_look(ads_eye, post, 55.0, (2560, 1440)), l5_l(post), {},
          "ADS: eye 0.25 m behind the Sight socket on the sight line to SightFront, 55 deg FOV"),
         ("tp_3m", persp_look(hero_t + 3000.0 * unit([-0.45, -0.85, 0.28]), hero_t, 60.0, (1600, 900)),
          l5_l(hero_t), {}, "third person: camera 3 m from the gun, right side, 60 deg FOV"),
         ("hero_34", persp_look(hero_t + 1500.0 * unit([0.55, 0.78, 0.30]), hero_t, 38.0, (1600, 900)),
          l5_l(hero_t), {}, "hero 3/4 front left (the sheet's 3/4 side), 1.5 m, 38 deg FOV"),
         ("hero_34_folded", persp_look(fold_t + 1500.0 * unit([0.55, -0.78, 0.30]), fold_t, 38.0, (1600, 900)),
          l5_l(fold_t), {"pose": {"clip": "A_SMG01_StockFold", "frame": 24}},
          "hero 3/4 front right, stock folded (A_SMG01_StockFold last frame, StockLocked), 1.5 m, 38 deg FOV")]
    # (W4 resume) the judges' views under the photographic studio rig (gunlib export_review_job 'studio': the bundled
    # studio HDRI made neutral for light and reflections + the rough rig's softboxes at 0.3; the camera sees the same
    # grey 126 backdrop); the L5 colour-calibration rig's versions beside them in realism/l5/ (the W3-W4 look). Under
    # the flat grey world of L5 a dark rough finish has nothing to reflect (with the paint near-uniform too, spec R45:
    # the maps 1.8-3.5 sRGB levels off a constant clay), which the judges called "one flat matte clay"
    dist = {"fp_35cm": 1.1, "ads_55deg": 1.1, "tp_3m": 3.2, "hero_34": 1.6, "hero_34_folded": 1.6}
    out = []
    for n, c, L, kw, note in S:
        st = dict(STUDIO, target_M=L["target_M"], dist_m=dist[n])
        out.append(dict({"name": n, "out": str(REAL / f"{n}.png"), "camera": c, "lights": st, "samples": samples,
                         "note": note + " [studio rig]"}, **kw))
        out.append(dict({"name": n + "_l5", "out": str(REAL / "l5" / f"{n}.png"), "camera": c, "lights": L,
                         "samples": samples, "note": note + " [L5 calibration rig]"}, **kw))
    return out


def set_shots(samples):
    px3, px2 = 3 * PX1, 2 * PX1
    sk = json.loads((EXP / "SK_SMG01.skeletal.json").read_text())
    socks = {s_["name"]: s_ for s_ in sk["sockets"]}
    notif = {(n_["clip"], n_["name"]): n_["frame"] for n_ in sk["notifies"]}
    charge_rear = notif[("A_SMG01_Charge", "ChargeRear")]
    mag_out = notif[("A_SMG01_Reload", "MagOut")]
    bolt_pose = {"clip": "A_SMG01_Charge", "frame": charge_rear}
    fold_pose = {"clip": "A_SMG01_StockFold", "frame": 24}
    ins = socks["MagInsertStart"]
    ins_pose = {"mag_socket": {"location_B_mm": ins["location_mm"], "matrix_rows": ins["matrix"]}}
    out_pose = {"clip": "A_SMG01_Reload", "frame": mag_out}
    Lf, Rt = (0.0, -1.0, 0.0), (0.0, 1.0, 0.0)        # look -Y = from the gun's LEFT (+Y); +Y = from the right
    rec_c = (405.0, 0.0, 10.0)
    grip_c = (340.0, 0.0, -80.0)
    front_c = (577.0, 0.0, 15.0)
    mag_c = (440.0, 0.0, -118.0)       # (W4 resume) the seated magazine spans Z -231 .. ~-8: the frame holds the lips
    well_c = (435.0, 0.0, -150.0)      # reload frames: the well and the whole magazine at MagOut (bottom ~ Z -300)
    full_c = (312.0, 0.0, -80.0)       # full-gun side frames: Z -250 .. +90 (the magazine bottom is at Z -231)
    FULL_H = 340.0
    rake = math.radians(8.27)          # the Mag socket's rake: the magazine axis points down and forward
    mag_axis = (math.sin(rake), 0.0, -math.cos(rake))
    stock_c = (135.0, 0.0, -25.0)
    S = []

    def add(name, cam, note, target, fill=0.0, **kw):
        S.append(dict({"name": name, "out": str(SETD / f"{name}.png"), "camera": cam, "samples": samples,
                       "lights": l5_l(target, fill), "note": note}, **kw))

    add("receiver_left_3x", ortho_look(rec_c, Lf, 340, 160, px3), "receiver, true left (knob side), ortho 3x", rec_c)
    add("receiver_right_3x", ortho_look(rec_c, Rt, 340, 160, px3), "receiver, true right (port side), ortho 3x",
        rec_c)
    add("grip_trigger_selector_left_3x", ortho_look(grip_c, Lf, 160, 180, px3),
        "grip, trigger, guard, selector, paddle: true left, ortho 3x", grip_c)
    add("grip_trigger_selector_right_3x", ortho_look(grip_c, Rt, 160, 180, px3),
        "grip, trigger, guard, selector: true right, ortho 3x", grip_c)
    add("grip_trigger_selector_34_low", persp_look((300.0, 330.0, -150.0), (345.0, 0.0, -65.0), 32.0, (1600, 1100)),
        "grip / trigger / selector from the left, low (thumb's view)", (345.0, 0.0, -65.0))
    add("front_end_left_3x", ortho_look(front_c, Lf, 125, 140, px3),
        "front end: muzzle device, front sight, lower rail, true left, ortho 3x", front_c)
    add("front_end_right_3x", ortho_look(front_c, Rt, 125, 140, px3), "front end, true right, ortho 3x", front_c)
    add("front_end_34", persp_look((760.0, 210.0, 90.0), (585.0, 0.0, 10.0), 30.0, (1600, 1100)),
        "front end 3/4 front left (muzzle device slots, front sight ears)", (585.0, 0.0, 10.0))
    add("sight_rear_left_3x", ortho_look((299.0, 0.0, 55.0), Lf, 75, 60, px3), "rear sight (up), true left, 3x",
        (299.0, 0.0, 55.0))
    add("sight_front_left_3x", ortho_look((542.0, 0.0, 55.0), Lf, 75, 60, px3), "front sight (up), true left, 3x",
        (542.0, 0.0, 55.0))
    add("sight_rear_34", persp_look((205.0, 120.0, 135.0), (299.0, 0.0, 62.0), 30.0, (1600, 1100)),
        "rear sight from left rear above (aperture, windage drum)", (299.0, 0.0, 62.0))
    add("sight_front_34", persp_look((640.0, 120.0, 130.0), (542.0, 0.0, 62.0), 30.0, (1600, 1100)),
        "front sight from front left above (post between the ears)", (542.0, 0.0, 62.0))
    add("mag_left_2x", ortho_look(mag_c, Lf, 120, 270, px2), "SM_SMG01_Mag alone (seated pose), true left, ortho 2x",
        mag_c, show=["mag"])
    add("mag_front_2x", ortho_look(mag_c, (-1.0, 0.0, 0.0), 80, 270, px2), "SM_SMG01_Mag alone, from the front, 2x",
        mag_c, show=["mag"])
    add("mag_34_top", persp_look((560.0, 200.0, 60.0), (436.0, 0.0, -80.0), 34.0, (1200, 1400)),
        "SM_SMG01_Mag alone, 3/4 front left from above (feed lips, follower, catch notch)", (436.0, 0.0, -80.0),
        show=["mag"])
    add("mag_top_3x", ortho_look((424.0, 0.0, -6.0), mag_axis, 60, 40, px3, up=(0.0, 1.0, 0.0)),
        "SM_SMG01_Mag alone, seated, looking down its axis (feed lips, follower), muzzle image-right, ortho 3x",
        (424.0, 0.0, -6.0), show=["mag"])
    add("stock_extended_right_2x", ortho_look(stock_c, Rt, 290, 150, px2),
        "stock extended (bind pose), true right, ortho 2x", stock_c)
    add("stock_extended_34_rear", persp_look((-120.0, -330.0, 120.0), (170.0, 0.0, -10.0), 40.0, (1600, 1100)),
        "stock extended, 3/4 right rear (hinge, latch button, butt pad)", (170.0, 0.0, -10.0))
    fold_c = (435.0, 0.0, -75.0)
    add("stock_folded_right_1x", ortho_look(fold_c, Rt, 430, 330, PX1),
        "stock folded (A_SMG01_StockFold frame 24, StockLocked), true right, ortho 1x", fold_c, pose=fold_pose)
    add("stock_folded_top_1x", ortho_look((435.0, -25.0, 0.0), (0.0, 0.0, -1.0), 430, 185, PX1, up=(0.0, -1.0, 0.0)),
        "stock folded, top (the TOP panel's orientation: muzzle left, gun left image-down), ortho 1x",
        (435.0, -25.0, 0.0), pose=fold_pose)
    add("stock_folded_latch_3x", ortho_look((300.0, -40.0, 0.0), Rt, 170, 130, px3),
        "folded stock at the port catch / latch, true right, ortho 3x", (300.0, -40.0, 0.0), pose=fold_pose)
    add("reload_magout_left_2x", ortho_look(well_c, Lf, 200, 340, px2),
        "reload: A_SMG01_Reload frame %d (MagOut), paddle pressed, magazine leaving the well, true left, 2x" % mag_out,
        well_c, pose=out_pose)
    add("reload_insertstart_left_2x", ortho_look(well_c, Lf, 200, 340, px2),
        "reload: SM_SMG01_Mag at the MagInsertStart socket (straight path below the well), true left, 2x", well_c,
        pose=ins_pose)
    add("reload_insertstart_fp", persp_look((250.0, 260.0, 120.0), (430.0, 0.0, -100.0), 45.0, (1600, 1000)),
        "reload at MagInsertStart seen from the shooter's side (left, above, behind)", (430.0, 0.0, -100.0),
        pose=ins_pose)
    add("bolt_rear_left_3x", ortho_look(rec_c, Lf, 340, 160, px3),
        "bolt + charging handle at full travel (A_SMG01_Charge frame %d ChargeRear), true left, 3x" % charge_rear,
        rec_c, pose=bolt_pose)
    add("bolt_rear_right_3x", ortho_look(rec_c, Rt, 340, 160, px3),
        "bolt at full travel, open ejection port, true right, 3x", rec_c, pose=bolt_pose, fill=15.0)
    add("bolt_rear_34_above", persp_look((470.0, -250.0, 190.0), (430.0, 0.0, 15.0), 34.0, (1600, 1100)),
        "bolt at full travel, ejection port from right above", (430.0, 0.0, 15.0), pose=bolt_pose, fill=15.0)
    for lv in range(4):
        add(f"lod/lod{lv}_side", ortho_look(full_c, Lf, 660, FULL_H, 1600 / 660.0),
            f"SK_SMG01 LOD{lv} + SM_SMG01_Mag LOD{lv}, true left, ortho", full_c, lod=lv, mag_lod=lv)
        add(f"lod/lod{lv}_side_wire", ortho_look(full_c, Lf, 660, FULL_H, 1600 / 660.0),
            f"SK_SMG01 LOD{lv} + mag LOD{lv} wireframe", full_c, lod=lv, mag_lod=lv, look="wire",
            samples=min(samples, 48))
    add("wireframe_lod0_side", ortho_look(full_c, Lf, 660, FULL_H, PX1), "SK_SMG01 LOD0 + mag LOD0 wireframe, 1x",
        full_c, look="wire", samples=min(samples, 48))
    add("wireframe_receiver_3x", ortho_look(rec_c, Lf, 340, 160, px3), "LOD0 wireframe, receiver 3x", rec_c,
        look="wire", samples=min(samples, 48))
    hero_t = np.array([380.0, 0.0, -30.0])
    add("wireframe_34", persp_look(hero_t + 1500.0 * unit([0.55, 0.78, 0.30]), hero_t, 38.0, (1600, 900)),
        "LOD0 wireframe, hero 3/4", hero_t, look="wire", samples=min(samples, 48))
    return S


def lod_strips():
    sk = json.loads((EXP / "SK_SMG01.skeletal.json").read_text())
    tris = sk.get("lod_triangles", {})
    names = ["SK_SMG01", "SK_SMG01_LOD1", "SK_SMG01_LOD2", "SK_SMG01_LOD3"]
    for suffix, out in (("", "lod_strip.png"), ("_wire", "lod_strip_wire.png")):
        ims = [Image.open(SETD / "lod" / f"lod{k}_side{suffix}.png").convert("RGB") for k in range(4)]
        Wd, Hd = ims[0].size
        S = Image.new("RGB", (Wd, (Hd + 34) * 4), (255, 255, 255))
        fnt = CU._font(22)
        for k, im in enumerate(ims):
            S.paste(im, (0, k * (Hd + 34) + 34))
            lab = f"LOD{k}: {names[k]} {tris.get(names[k], '?')} tris + SM_SMG01_Mag_LOD{k}"
            ImageDraw.Draw(S).text((6, k * (Hd + 34) + 5), lab, fill=(0, 0, 0), font=fnt)
        S.save(SETD / out)


# shots framed to hold the WHOLE subject (the close-ups crop on purpose): border pixels off the 126 grey film
# (the reload frames crop the gun at the sides on purpose: only their bottom edge is checked, for the magazine)
WHOLE = ["tp_3m", "hero_34", "hero_34_folded", "mag_left_2x", "mag_front_2x", "mag_top_3x",
         "stock_folded_right_1x", "stock_folded_top_1x", "reload_magout_left_2x", "reload_insertstart_left_2x",
         "wireframe_lod0_side", "wireframe_34"] + [f"lod/lod{k}_side{w}" for k in range(4) for w in ("", "_wire")]
BOTTOM_ONLY = {"reload_magout_left_2x", "reload_insertstart_left_2x"}


def border_hits(path, bg=126, tol=10, bottom_only=False):
    """Pixels on the image border that differ from the film grey by more than tol (subject cut by the frame)."""
    a = np.asarray(Image.open(path).convert("RGB")).astype(int)
    b = a[-1] if bottom_only else np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    return int((np.abs(b - bg).max(1) > tol).sum())


def contact(paths, out, cols=2, w=800, aspect=0.625):
    """Contact sheet: every image letterboxed into the same cell (w x w*aspect) under an 18 px caption bar."""
    ch = int(round(w * aspect))
    cells = []
    for p, label in paths:
        im = Image.open(p).convert("RGB")
        im.thumbnail((w, ch), Image.LANCZOS)
        cell = Image.new("RGB", (w, ch + 18), (40, 40, 40))
        cell.paste(im, ((w - im.width) // 2, 18 + (ch - im.height) // 2))
        ImageDraw.Draw(cell).text((4, 3), label[:118], fill=(255, 255, 255))
        cells.append(cell)
    rows = (len(cells) + cols - 1) // cols
    S = Image.new("RGB", (w * cols, (ch + 18) * rows), (40, 40, 40))
    for k, c in enumerate(cells):
        S.paste(c, ((k % cols) * w, (k // cols) * (ch + 18)))
    S.save(out)


# ------------------------------------------------------------------------------------------------ run
def mag_socket_rel():
    """The Mag socket's rotation relative to the magazine bone (SK_SMG01.skeletal.json): SM_SMG01_Mag attaches with
    zero relative transform on the SOCKET, which carries the 8.27 deg rake; the magazine bone itself is unrotated in
    the exported skeleton (read back: bone pitch 0.0 deg), so the socket's armature-space 3x3 is its relative one."""
    sk = json.loads((EXP / "SK_SMG01.skeletal.json").read_text())
    s_ = {x["name"]: x for x in sk["sockets"]}["Mag"]
    assert s_["bone"] == "magazine"
    return s_["matrix"]


def run_job(name, shots, samples):
    JOBD.mkdir(parents=True, exist_ok=True)
    job = {"exports_dir": str(EXP), "tex_dir": str(TEXD), "offset_M": [float(v) for v in GRIP],
           "gun_lods": ["SK_SMG01.fbx", "SK_SMG01_LOD1.fbx", "SK_SMG01_LOD2.fbx", "SK_SMG01_LOD3.fbx"],
           "mag_fbx": "SM_SMG01_Mag.fbx", "mag_lod_prefix": "SM_SMG01_Mag_LOD", "mag_bone": "magazine",
           "mag_socket_rel_rows": mag_socket_rel(), "clips": CLIPS,
           "materials": {"M_SMG01_Metal": "T_SMG01_Metal", "M_SMG01_Furniture": "T_SMG01_Furniture",
                         "M_SMG01_Mag": "T_SMG01_Mag"},
           "samples": samples, "result": str(JOBD / f"{name}_result.json"), "shots": shots}
    jp = JOBD / f"{name}_job.json"
    jp.write_text(json.dumps(job, indent=1))
    log = JOBD / f"{name}.log"
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", "--factory-startup", "--python",
                        str(ROOT / "Scripts" / "guns" / "gunlib" / "export_review_job.py"), "--", "--job", str(jp)],
                       stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or "EXPORT_REVIEW_DONE" not in txt:
        raise SystemExit(f"export review render failed, see {log}")
    return json.loads((JOBD / f"{name}_result.json").read_text())


SET_GROUPS = {   # the role's review set (SMG_BUILD_PLAN 15 W4): group -> minimum images, name prefixes
    "receiver both sides 3x": (2, ["receiver_left_3x", "receiver_right_3x"]),
    "grip / trigger / selector 3x": (2, ["grip_trigger_selector_left_3x", "grip_trigger_selector_right_3x"]),
    "front end 3x": (2, ["front_end_left_3x", "front_end_right_3x"]),
    "sights 3x": (2, ["sight_rear_left_3x", "sight_front_left_3x"]),
    "magazine 2x": (2, ["mag_left_2x", "mag_front_2x"]),
    "stock folded and extended": (2, ["stock_extended_right_2x", "stock_folded_right_1x"]),
    "reload pose": (2, ["reload_magout_left_2x", "reload_insertstart_left_2x"]),
    "bolt at full travel": (2, ["bolt_rear_left_3x", "bolt_rear_right_3x"]),
    "LOD strip": (2, ["lod_strip", "lod_strip_wire"]),
    "wireframe": (1, ["wireframe_lod0_side"])}
REALISM_REQ = ["fp_35cm", "ads_55deg", "tp_3m", "hero_34"]


def stage_gates(res):
    """Stage result with counts: inputs = the W3-gated exported bytes, every required image present and non-empty,
    whole-subject frames not cut, poses read back from the shipped clips, blind pairs >= 12 with an irregular key."""
    G = []

    def gate(name, value, threshold, ok):
        G.append({"name": name, "value": value, "threshold": threshold, "pass": bool(ok)})

    rec = {}
    for f in ("rig_export", "mag"):
        rec.update({k: v["sha256"] for k, v in json.loads((GATES / f"{f}.json").read_text())["files"].items()
                    if k.endswith(".fbx") and not k.endswith("(input)")})
    ins = res.get("inputs_sha256", {})
    fbx = {k: v for k, v in ins.items() if k.endswith(".fbx")}
    mism = sorted(k for k, v in fbx.items() if k in rec and rec[k] != v)
    unrec = sorted(k for k in fbx if k not in rec)
    gate("R0 inputs = the W3-gated exported bytes (sha256 vs rig_export.json + mag.json)",
         {"fbx": len(fbx), "matched": len(fbx) - len(mism) - len(unrec), "mismatched": mism, "unrecorded": unrec,
          "textures_hashed": len(ins) - len(fbx)}, "0 mismatched, 0 unrecorded", not mism and not unrec)

    def present(paths):
        bad = [rel(Path(ROOT / q)) for q in paths if not (ROOT / q).exists() or (ROOT / q).stat().st_size < 10000]
        return len(paths) - len(bad), bad

    rf = res.get("realism", {}).get("files", [])
    n, bad = present(rf)
    miss = [r for r in REALISM_REQ if not any(f.endswith(f"/{r}.png") for f in rf)]
    gate("R1 realism set (fp_35cm, ads 55 deg / 0.25 m, tp_3m, hero_34)", {"images": n, "missing_required": miss,
         "empty_or_absent": bad}, ">= 4 images, the 4 required present", n >= 4 and not miss and not bad)
    sf = res.get("set", {}).get("files", [])
    n, bad = present(sf)
    groups = {}
    for g, (k, req) in SET_GROUPS.items():
        groups[g] = sum(1 for r in req if any(f.endswith(f"/{r}.png") for f in sf))
    short = [g for g, (k, req) in SET_GROUPS.items() if groups[g] < k]
    gate("R2 review set (receiver, grip / trigger / selector, front end, sights, magazine, stock, reload, bolt, LOD "
         "strip, wireframe)", {"images": n, "groups": groups, "short": short, "empty_or_absent": bad},
         "every group at its minimum, no empty image", not short and not bad)
    bh = dict(res.get("set", {}).get("border_hits_whole_frames", {}),
              **res.get("realism", {}).get("border_hits_whole_frames", {}))
    cut = {k: v for k, v in bh.items() if v > 5}
    gate("R3 whole-subject frames not cut by the frame (border px off the film grey > 10 levels)",
         {"frames": len(bh), "cut": cut, "max_px": max(bh.values()) if bh else None}, "<= 5 px on every frame",
         bh and not cut)
    po = res.get("set", {}).get("poses", {})
    ok = (po.get("bolt_travel_mm") or 0) > 60 and abs((po.get("mag_seated_pitch_deg") or 0) + 8.27) < 0.05         and po.get("mag_at_MagOut_M_mm") and po.get("lod_faces") and len(po["lod_faces"]) == 4
    gate("R4 poses read back from the shipped clips / sockets (bolt travel, mag rake, MagOut, LOD faces)",
         {k: po.get(k) for k in ("bolt_travel_mm", "mag_seated_pitch_deg", "mag_at_MagOut_M_mm",
                                 "mag_at_MagInsertStart_M_mm", "lod_faces")},
         "bolt travel > 60 mm; rake -8.27 +- 0.05 deg; 4 LOD face counts", ok)
    bl = res.get("blind", {})
    key = json.loads(KEYF.read_text()) if KEYF.exists() else {}
    pk = {k: v for k, v in key.items() if k.startswith("pair_")}
    nb = sum(1 for v in pk.values() if v["ours"] == "B")
    imgs = sorted(BLIND.glob("pair_*.png"))
    same = all(Image.open(BLIND / f"{k}_A.png").size == Image.open(BLIND / f"{k}_B.png").size for k in pk)
    gate("R5 blind pairs (side / top / 3/4 crops vs ours at matched framing; key outside the folder)",
         {"pairs": len(pk), "images": len(imgs), "ours_B": nb, "ours_A": len(pk) - nb, "A_B_same_size": same,
          "framing_iou_panels": {k: v["silhouette_iou_vs_reference"] for k, v in bl.get("framing_checks", {}).items()}},
         ">= 12 pairs, 2 images each, ours on both sides, equal sizes",
         len(pk) >= 12 and len(imgs) == 2 * len(pk) and 0 < nb < len(pk) and same)
    failed = [g["name"].split(" ")[0] for g in G if not g["pass"]]
    return {"gates": G, "status": "pass" if not failed else "fail", "failed": failed,
            "note": "reported, not blocking: the blind result (judges) and the realism judges' verdicts belong to "
                    "the W4 review; this file gates the renders themselves"}


def main():
    global REAL, SETD
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="blind,realism,set")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--names", default="", help="set/realism: render only these shot names (trial)")
    ap.add_argument("--tag", default="", help="trial renders: review/realism_<tag>, review/set_<tag>; no gate file")
    a = ap.parse_args()
    only = set(a.only.split(","))
    gp = GATES / "review_export.json"
    if a.tag:
        REAL, SETD = REVIEW / f"realism_{a.tag}", REVIEW / f"set_{a.tag}"
        gp = JOBD / f"review_export_{a.tag}.json"
        JOBD.mkdir(parents=True, exist_ok=True)
    names = set(n for n in a.names.split(",") if n)
    res = json.loads(gp.read_text()) if gp.exists() else {}
    res.update({"stage": "W4 review renders from the exported bytes", "date": datetime.date.today().isoformat(),
                "inputs_sha256": {rel(p): sha(p) for p in sorted(EXP.glob("*.fbx")) + sorted(TEXD.glob("*.png"))}})
    if "blind" in only:
        shots, meta = blind_shots(a.samples)
        if not a.no_render:
            run_job("blind", shots, a.samples)
        key, checks = make_blind(meta)
        keyj = {f"pair_{n:02d}": v for n, v in sorted(key.items())}
        keyj["_about"] = {
            "folder": "WorkFiles/guns/smg/review/blind (images only; this key lives outside it)",
            "rule": "ours = B on pairs %s; ours = A on the others" % sorted(OURS_B),
            "ours_source": "the EXPORTED bytes: SK_SMG01.fbx + SM_SMG01_Mag.fbx (seated on the magazine bone) with "
                           "game materials from Exports/Guns/SMG01/Textures (BC sRGB, ORM linear, N DirectX); Cycles",
            "resolution": "ours rendered at 3x the panel with a transparent film, composited on the panel's fitted "
                          "studio backdrop, reduced to the panel's native px and enlarged with the same LANCZOS "
                          "filter as the reference (panels 3x; windows k x, longest side ~1100 px): both images carry "
                          "the panel's resolution",
            "lights": "sides / top: the L5 physical rig (scratch/l5/l5.json fit); 3/4: the rough rig (env 0.55, "
                      "k 1.35) on the panel's backdrop",
            "crops": "side panels: rows 0-%d (above the 0-70 cm ruler)" % SIDE_ROWS,
            "note": "the 3/4 panel is reported-only for form (spec R39: the panel itself is inconsistent, body "
                    "landmarks 6.8 px RMS); pairs 4, 14, 15 carry that camera"}
        KEYF.write_text(json.dumps(keyj, indent=1))
        contact_pairs(keyj)
        n_pairs = len(key)
        res["blind"] = {"pairs": n_pairs, "images": len(list(BLIND.glob("pair_*.png"))), "framing_checks": checks,
                        "key": rel(KEYF), "unblinded_contact": rel(BSRC / "key_contact_UNBLINDED.png")}
    if "realism" in only:
        REAL.mkdir(parents=True, exist_ok=True)
        sh = realism_shots(a.samples)
        if names:
            sh = [s_ for s_ in sh if s_["name"] in names]
        if not a.no_render:
            run_job("realism", sh, a.samples)
        contact([(s_["out"], s_["name"] + ": " + s_["note"]) for s_ in sh if not s_["name"].endswith("_l5")],
                REAL / "contact.png")
        if any(s_["name"].endswith("_l5") for s_ in sh):
            contact([(s_["out"], s_["name"] + ": " + s_["note"]) for s_ in sh if s_["name"].endswith("_l5")],
                    REAL / "l5" / "contact.png")
        (REAL / "shots.json").write_text(json.dumps({"source": "EXPORTED bytes (SK_SMG01 + SM_SMG01_Mag + shipped "
                                                               "textures + shipped clips)",
                                                     "shots": [dict(s_, out=rel(s_["out"])) for s_ in sh]}, indent=1))
        res["realism"] = {"images": len(sh), "files": [rel(s_["out"]) for s_ in sh],
                          "border_hits_whole_frames": {s_["name"]: border_hits(s_["out"]) for s_ in sh
                                                       if s_["name"] in WHOLE}}
    if "set" in only:
        SETD.mkdir(parents=True, exist_ok=True)
        sh = set_shots(a.samples)
        if names:
            sh = [s_ for s_ in sh if s_["name"] in names]
        rr = None if a.no_render else run_job("set", sh, a.samples)
        if rr is None and (JOBD / "set_result.json").exists():
            rr = json.loads((JOBD / "set_result.json").read_text())     # contact / gate refresh after a render
        if not names:
            lod_strips()
        main_imgs = [s_ for s_ in sh if not s_["name"].startswith("lod/")]
        extra = [(SETD / "lod_strip.png", "LOD strip"), (SETD / "lod_strip_wire.png", "LOD strip wireframe")] \
            if not names else []
        contact([(s_["out"], s_["name"] + ": " + s_["note"]) for s_ in main_imgs] + extra, SETD / "contact.png",
                cols=3, w=640)
        rec = {}
        if rr and not names:
            byname = {r["name"]: r for r in rr["shots"]}
            rb = rr.get("rest_bolt_M_mm")
            bb = byname["bolt_rear_left_3x"]["bones_M_mm"].get("bolt")
            rec = {"bolt_rest_M_mm": rb, "bolt_rear_M_mm": bb,
                   "bolt_travel_mm": round(float(np.linalg.norm(np.array(bb) - np.array(rb))), 3) if rb and bb else None,
                   "selector_at_ChargeRear_M_mm": byname["bolt_rear_left_3x"]["bones_M_mm"].get("selector"),
                   "mag_seated_M_mm": byname["receiver_left_3x"]["mag_M_mm"],
                   "mag_seated_pitch_deg": byname["receiver_left_3x"]["mag_pitch_deg"],
                   "mag_at_MagOut_M_mm": byname["reload_magout_left_2x"]["mag_M_mm"],
                   "mag_at_MagInsertStart_M_mm": byname["reload_insertstart_left_2x"]["mag_M_mm"],
                   "lod_faces": rr.get("gun_faces"), "mag_lod_faces": rr.get("mag_faces")}
        (SETD / "shots.json").write_text(json.dumps({"source": "EXPORTED bytes", "scale": "1x = %.3f px/mm" % PX1,
                                                     "poses": rec, "shots": [dict(s_, out=rel(s_["out"]))
                                                                            for s_ in sh]}, indent=1))
        if not names:
            res["set"] = {"images": len(main_imgs) + 2, "lod_frames": 8,
                          "files": [rel(s_["out"]) for s_ in main_imgs] +
                          [rel(SETD / "lod_strip.png"), rel(SETD / "lod_strip_wire.png")], "poses": rec,
                          "border_hits_whole_frames": {s_["name"]: border_hits(s_["out"],
                                                                               bottom_only=s_["name"] in BOTTOM_ONLY)
                                                       for s_ in sh if s_["name"] in WHOLE}}
    if not a.tag and not names:
        res.update(stage_gates(res))
    gp.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: (v if k != "inputs_sha256" else len(v)) for k, v in res.items()}, indent=1)[:4000])


if __name__ == "__main__":
    main()
