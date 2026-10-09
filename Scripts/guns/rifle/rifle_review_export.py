"""AR-01 review renders from the EXPORTED bytes (plain Python; renders via headless Blender, gunlib/export_review_job.py):
SK_AR01.fbx (+ LOD1-3), SM_AR01_Mag.fbx on the magazine bone, the shipped clips and the shipped textures; nothing from
the build blend.

    py -3 -B Scripts/guns/rifle/rifle_review_export.py [--only blind,realism,set] [--samples 128] [--no-render]

(a) Blind design test (RIFLE_BUILD_PLAN 9 L7): 12 pairs = both sides (LEFT panel = true right, RIGHT panel = true
    left), top, the 3/4 view (solved camera scratch/q34/camera.json), the 7 close-ups c1-c7 (panel cameras
    scratch/detail/cameras/panel_cK.json) and one seated mag/well crop of the side panel. Ours is rendered at 3x the
    panel with a transparent film, composited onto the panel's own fitted studio backdrop, reduced to the panel's native
    pixels and enlarged with the same LANCZOS filter as the reference crop, so both images carry the same resolution
    (a judge decides on design, not on sharpness). review/blind/pair_NN_A.png / _B.png (ours = B on pairs 1, 2, 4, 7,
    8, 11, A elsewhere), the key in review/blind_key.json, our native 3x composites in review/blind_src/.
(b) Realism set review/realism/ (fp_35cm, ads_55deg, tp_3m, hero_34: the cameras of rifle_texrender.realism_shots) and
    the review set review/set/ (receiver right / left 3x, brake + front sight 3x, magazine 2x, reload at MagRockStart,
    bolt at full rearward travel (A_AR01_Charge at its ChargeRear notify), LOD strip, wireframe, third person 8 m).
    1x = 2560 px across the 880 mm gun (2.91 px/mm); 3x = 8.73 px/mm; 2x = 5.82 px/mm.
Writes gates/review_export.json (counts of images made and the framing checks).
"""
from __future__ import annotations

import argparse
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
from rifle_common import ROOT, SPEC, GRIP, SCRATCH, TRACE, REVIEW, GATES, SHEET  # noqa: E402

import gunlib  # noqa: E402
from gunlib import compare as C  # noqa: E402
from gunlib import closeup as CU  # noqa: E402

EXP = ROOT / "Exports" / "Guns" / "AR01"
TEXD = EXP / "Textures"
JOBD = SCRATCH / "export_review"
BLIND = REVIEW / "blind"
BSRC = REVIEW / "blind_src"
REAL = REVIEW / "realism"
SETD = REVIEW / "set"
KEYF = REVIEW / "blind_key.json"
SS = 3
SIDE_ROWS = 238                 # side panels: rows above the 0-90 cm ruler (its line is at panel row 250)
OURS_B = {1, 2, 4, 7, 8, 11}    # pairs where ours is image B (fixed irregular order)
PX1 = 2560.0 / 880.0            # 1x review scale (px / mm)

SEL_C1 = {"bone": "selector", "pivot_M": [282.8, 0.0, -7.8], "axis_M": [0.0, 1.0, 0.0], "deg": 13.25}


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sheet_rgb():
    return np.asarray(Image.open(SHEET).convert("RGB")).astype(float)


def panel(box):
    x0, y0, x1, y1 = box
    return sheet_rgb()[y0:y1 + 1, x0:x1 + 1]


# ------------------------------------------------------------------------------------------------ cameras
def frame_camera(view, fit=(0.0, 0.0, 0.0, 0.0), unmirror=False):
    """ORTHO camera JSON reproducing a trace panel's px <-> mm map (gunlib.compare.PanelFrame) after the silhouette
    gate's similarity fit (scale, rot deg, tx, ty about the panel centre). Side panels map (X, Z), the top (X, Y).
    unmirror: the RIGHT panel's frame is in the MIRRORED crop; the camera then looks from +Y (the true left) and its
    image is the unmirrored panel."""
    fr, j = C.load_trace(TRACE, view)
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
            "panel_px": [W, H], "source": f"trace/{view}_outline.json frame + gate fit {list(fit)}"
                                          + (" (unmirrored: view from +Y)" if unmirror else "")}


def ortho_look(centre_M, view_dir, width_mm, height_mm, pxmm, up=(0.0, 0.0, 1.0)):
    """Orthographic LOOK camera: view_dir = direction the camera looks along (M)."""
    c = np.asarray(centre_M, float)
    d = np.asarray(view_dir, float) / np.linalg.norm(view_dir)
    return {"type": "LOOK", "eye_M": (c - 1500.0 * d).tolist(), "target_M": c.tolist(), "ortho_width_mm": width_mm,
            "res": [int(round(width_mm * pxmm)), int(round(height_mm * pxmm))], "up_M": list(up),
            "px_per_mm": pxmm}


def persp_look(eye, tgt, fov, res):
    return {"type": "LOOK", "eye_M": [float(v) for v in eye], "target_M": [float(v) for v in tgt], "fov_deg": fov,
            "res": list(res)}


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def l5_params():
    d = json.loads((SCRATCH / "game" / "l5.json").read_text())
    f = d["fit"]
    return {"k": float(f["light_scale"]), "env": float(f["rig"]["world_env"]),
            "key_elev_deg": float(f["rig"]["key_elev_deg"])}


def form_fits():
    v = json.loads((GATES / "form.json").read_text())["details"]["silhouette"]["views"]
    return {"LEFT": tuple(v["side"]["fit_params_s_rotdeg_tx_ty"]), "TOP": tuple(v["top"]["fit_params_s_rotdeg_tx_ty"]),
            "RIGHT": tuple(v["left_vs_RIGHT_panel"]["fit_params_s_rotdeg_tx_ty"])}


# ------------------------------------------------------------------------------------------------ blind
def detail_panels():
    import rifle_detail as RDT
    return RDT.PANELS


def blind_shots(samples):
    P = detail_panels()
    fits = form_fits()
    L5 = l5_params()
    shots, meta = [], {}

    def add(n, subject, box, cam, lights, crop_rows=None, **kw):
        out = JOBD / "blind" / f"pair_{n:02d}.png"
        shots.append(dict({"name": f"pair_{n:02d}", "out": str(out), "camera": cam, "ss": SS, "transparent": True,
                           "lights": lights, "samples": samples}, **kw))
        meta[n] = {"subject": subject, "box": list(box), "render": str(out), "crop_rows": crop_rows, "camera": cam}

    def l5(side):
        return dict(L5, rig="l5", side=side, bg_rgb=[126, 126, 126])

    def rough(box, target):
        _, _, _, bg = CU.fit_background(panel(box))
        return {"rig": "rough", "bg_rgb": [float(v) for v in bg.reshape(-1, 3).mean(0)], "env": 0.55, "k": 1.35,
                "dist_m": 1.1, "target_M": list(target)}

    jl = json.loads((TRACE / "LEFT_outline.json").read_text())
    jr = json.loads((TRACE / "RIGHT_outline.json").read_text())
    jt = json.loads((TRACE / "TOP_outline.json").read_text())
    add(1, "side, true right (LEFT-labelled panel)", jl["panel_box_sheet_px"], frame_camera("LEFT", fits["LEFT"]),
        l5("right"), SIDE_ROWS)
    add(2, "side, true left (RIGHT-labelled panel)", jr["panel_box_sheet_px"],
        frame_camera("RIGHT", fits["RIGHT"], unmirror=True), l5("left"), SIDE_ROWS)
    add(3, "top (TOP panel)", jt["panel_box_sheet_px"], frame_camera("TOP", fits["TOP"]), l5("top"))
    q = json.loads((SCRATCH / "q34" / "camera.json").read_text())
    q = dict(q, type="PERSP", panel_px=[758, 279])
    add(4, "3/4 front right (solved camera)", P["q34"]["box"], q, rough(P["q34"]["box"], (450.0, 0.0, -20.0)))
    tgt = {"c1": (300.0, 0.0, -40.0), "c2": (450.0, 0.0, 20.0), "c3": (830.0, 0.0, 10.0), "c4": (440.0, 0.0, -95.0),
           "c5": (440.0, 0.0, -95.0), "c6": (270.0, 0.0, -80.0), "c7": (8.0, 0.0, -55.0)}
    for n, k in zip((5, 6, 7, 8, 9, 10, 11), ("c1", "c2", "c3", "c4", "c5", "c6", "c7")):
        cam = json.loads((SCRATCH / "detail" / "cameras" / f"panel_{k}.json").read_text())["camera"]
        kw = {}
        if k == "c1":
            kw["pose"] = {"hinges": [SEL_C1]}      # c1 draws the lever 13.25 deg front-down (rifle_detail SEL_C1_POSE)
        if k in ("c4", "c5"):
            kw["show"] = ["mag"]                   # the magazine panels show the magazine alone
        if k == "c7":
            # the butt-plate panel shows the stock end only: clip everything forward of the stock (X > 240 mm in M),
            # the stock's own taper keeps the cut section hidden behind the plate
            fwd = np.array(cam["R_rows_cam_axes_in_M"][2], float)
            cen = np.array(cam["centre_M_mm"], float)
            kw["clip_end_m"] = float((240.0 - cen[0]) / fwd[0]) / 1000.0
        add(n, P[k]["title"], P[k]["box"], cam, rough(P[k]["box"], tgt[k]), **kw)
    return shots, meta


def mag_well_window():
    j = json.loads((TRACE / "LEFT_outline.json").read_text())
    M = np.vstack([np.array(r["px"]) for r in j["magazine"]])
    x0, y0 = int(M[:, 0].min()) - 30, int(M[:, 1].min()) - 45
    x1, y1 = int(M[:, 0].max()) + 30, SIDE_ROWS
    return x0, y0, x1, y1


def iou_mask(alpha, ref):
    a, b = alpha > 0.5, ref.astype(bool)
    return float((a & b).sum() / max((a | b).sum(), 1))


def ref_masks():
    """Reference silhouettes at panel px for the framing check (trace rings for the sides and top, the 3/4 solve's
    mask, the detail kit's panel masks for the close-ups)."""
    out = {}
    frL, jL = C.load_trace(TRACE, "LEFT")
    out[1] = C.rings_mask([r["px"] for r in jL["silhouette"]], frL.shape)
    frR, jR = C.load_trace(TRACE, "RIGHT")
    out[2] = C.rings_mask([r["px"] for r in jR["silhouette"]], frR.shape)[:, ::-1]
    frT, jT = C.load_trace(TRACE, "TOP")
    out[3] = C.rings_mask([r["px"] for r in jT["silhouette"]], frT.shape)
    out[4] = np.load(SCRATCH / "q34" / "mask_raw.npy")
    try:
        import rifle_detail as RDT
        kit = RDT.kit()
        for n, k in zip((5, 6, 7, 8, 9, 10, 11), ("c1", "c2", "c3", "c4", "c5", "c6", "c7")):
            out[n] = kit.mask(k)
    except Exception as ex:  # noqa: BLE001
        print("[review_export] close-up masks unavailable:", ex)
    return out


def make_blind(meta):
    BLIND.mkdir(parents=True, exist_ok=True)
    BSRC.mkdir(parents=True, exist_ok=True)
    for p in BLIND.glob("pair_*.png"):
        p.unlink()
    masks = ref_masks()
    key, checks, side_small = {}, {}, None
    for n in range(1, 12):
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
        _, _, _, bg = CU.fit_background(Pc)
        ours3 = CU.composite_on(bg, rgba[:rows * SS], SS)
        Image.fromarray(ours3).save(BSRC / f"ours_native3x_{n:02d}.png")
        ours1 = np.asarray(Image.fromarray(ours3).resize((W, rows), Image.BOX))
        if n == 1:
            side_small = (Pc, ours1)
        ref_img = Image.fromarray(np.clip(Pc, 0, 255).astype(np.uint8)).resize((W * SS, rows * SS), Image.LANCZOS)
        our_img = Image.fromarray(ours1).resize((W * SS, rows * SS), Image.LANCZOS)
        key[n] = _write_pair(n, ref_img, our_img, m, f"panel {m['box']} rows 0-{rows} at 3x")
    # pair 12: the seated magazine and its well, a window of the side panel at 6x
    x0, y0, x1, y1 = mag_well_window()
    Pc, ours1 = side_small
    rc = Image.fromarray(np.clip(Pc[y0:y1, x0:x1], 0, 255).astype(np.uint8))
    oc = Image.fromarray(ours1[y0:y1, x0:x1])
    sz = ((x1 - x0) * 6, (y1 - y0) * 6)
    m12 = {"subject": "seated magazine + magazine well (window of the LEFT-labelled side panel)",
           "box": meta[1]["box"], "render": meta[1]["render"], "camera": meta[1]["camera"]}
    key[12] = _write_pair(12, rc.resize(sz, Image.LANCZOS), oc.resize(sz, Image.LANCZOS), m12,
                          f"side panel window x {x0}-{x1}, y {y0}-{y1} (panel px) at 6x")
    Image.fromarray(np.asarray(Image.open(BSRC / "ours_native3x_01.png"))[y0 * SS:y1 * SS, x0 * SS:x1 * SS]).save(
        BSRC / "ours_native3x_12.png")
    return key, checks


def _write_pair(n, ref_img, our_img, m, framing):
    ours_is = "B" if n in OURS_B else "A"
    ref_is = "A" if ours_is == "B" else "B"
    assert ref_img.size == our_img.size
    (our_img if ours_is == "A" else ref_img).convert("RGB").save(BLIND / f"pair_{n:02d}_A.png")
    (our_img if ours_is == "B" else ref_img).convert("RGB").save(BLIND / f"pair_{n:02d}_B.png")
    cam = m["camera"]
    return {"subject": m["subject"], "ours": ours_is, "reference": ref_is, "size": list(ref_img.size),
            "framing": framing, "sheet_box_px": m["box"],
            "camera": cam.get("source") or ("PERSP solved" if cam["type"] == "PERSP" else "ORTHO solved"),
            "our_native_3x": rel(BSRC / f"ours_native3x_{n:02d}.png")}


def contact_pairs(key):
    tiles = []
    for n in range(1, 13):
        a = Image.open(BLIND / f"pair_{n:02d}_A.png").convert("RGB")
        b = Image.open(BLIND / f"pair_{n:02d}_B.png").convert("RGB")
        h = 300
        a = a.resize((max(1, int(a.width * h / a.height)), h), Image.LANCZOS)
        b = b.resize((max(1, int(b.width * h / b.height)), h), Image.LANCZOS)
        t = Image.new("RGB", (a.width + b.width + 10, h + 22), (255, 255, 255))
        t.paste(a, (0, 22))
        t.paste(b, (a.width + 10, 22))
        k = key[f"pair_{n:02d}"]
        ImageDraw.Draw(t).text((4, 4), f"{n:02d} {k['subject'][:60]}  A={'ours' if k['ours'] == 'A' else 'ref'}  "
                                       f"B={'ours' if k['ours'] == 'B' else 'ref'}", fill=(0, 0, 0))
        tiles.append(t)
    Wd = max(t.width for t in tiles)
    out = Image.new("RGB", (Wd, sum(t.height + 6 for t in tiles)), (255, 255, 255))
    y = 0
    for t in tiles:
        out.paste(t, (0, y))
        y += t.height + 6
    if out.height > 4000:
        out = out.resize((int(out.width * 4000 / out.height), 4000), Image.LANCZOS)
    out.save(BSRC / "key_contact_UNBLINDED.png")


# ------------------------------------------------------------------------------------------------ realism + set
def sight():
    soc = {s["socket"]: s for s in SPEC.sockets["rifle"]}["Sight"]
    p = math.radians(soc["unreal_rotation_deg"]["pitch"])
    d = np.array([math.cos(p), 0.0, math.sin(p)])
    return np.array(soc["M_mm"], float), d, np.array(SPEC.key["sight_line"]["post_tip_M"], float)


def rough_l(target, dist=1.1, bg=(126, 126, 126), env=0.55, k=1.35):
    return {"rig": "rough", "bg_rgb": list(bg), "env": env, "k": k, "dist_m": dist, "target_M": [float(v) for v in target]}


def l5_l(target, dist=None, fill=0.0, bg=(126, 126, 126)):
    """Stage-7 fix round (craft review item 7: the set and the realism views were lit by the near 'rough' rig, env
    0.55 x 1.35 with lights at 1.1 m, under which the black lacquer read grey and the walnut orange; receiver / background
    0.88 against the sheet's 0.53): the L5 PHYSICAL rig the colour was calibrated on (scratch/game/l5.json fit: key
    overhead tipped toward the camera, rim behind, grey world 0.2 x k), centred on the shot's target. `dist` is
    ignored (kept for the call sites); `fill` adds a weak low fill from the camera side (the open-port views)."""
    return dict(l5_params(), rig="l5", bg_rgb=list(bg), target_M=[float(v) for v in target], fill=float(fill))


def realism_shots(samples):
    s, d, post = sight()
    fp_eye = np.array([350.0, 0.0, 0.0]) + 350.0 * unit([-0.93, 0.22, 0.30])
    hero_t = np.array([450.0, 0.0, -20.0])
    S = [("fp_35cm", persp_look(fp_eye, (620.0, 0.0, 10.0), 70.0, (1600, 900)), l5_l((620.0, 0.0, 10.0)),
          "first person: eye 35 cm from the receiver, behind / left / above (right-handed hold), 70 deg FOV"),
         ("ads_55deg", persp_look(s - 250.0 * d, s + 1000.0 * d, 55.0, (2560, 1440)), l5_l(post),
          "ADS: eye 0.25 m behind the Sight socket on its line (forward = the socket pitch), 55 deg FOV"),
         ("tp_3m", persp_look(hero_t + 3000.0 * unit([-0.45, -0.85, 0.28]), hero_t, 60.0, (1600, 900)),
          l5_l(hero_t), "third person: camera 3 m from the gun, right side, 60 deg FOV"),
         ("hero_34", persp_look(hero_t + 1500.0 * unit([0.55, -0.78, 0.30]), hero_t, 38.0, (1600, 900)),
          l5_l(hero_t), "hero 3/4 front right, 1.5 m, 38 deg FOV")]
    return [{"name": n, "out": str(REAL / f"{n}.png"), "camera": c, "lights": L, "samples": samples, "note": note}
            for n, c, L, note in S]


def set_shots(samples):
    px3, px2 = 3 * PX1, 2 * PX1
    sk = json.loads((EXP / "SK_AR01.skeletal.json").read_text())
    socks = {s_["name"]: s_ for s_ in sk["sockets"]}
    rock = socks["MagRockStart"]
    rock_pose = {"mag_socket": {"location_B_mm": rock["location_mm"], "matrix_rows": rock["matrix"]}}
    notif = {(n_["clip"], n_["name"]): n_["frame"] for n_ in sk["notifies"]}
    charge_rear = notif[("A_AR01_Charge", "ChargeRear")]
    bolt_pose = {"clip": "A_AR01_Charge", "frame": charge_rear}
    R, Lf = (0.0, 1.0, 0.0), (0.0, -1.0, 0.0)           # look +Y = from the right side; -Y = from the left
    rec_c = (385.0, 0.0, -25.0)
    well_c = (425.0, 0.0, -70.0)
    mag_c = (432.0, 0.0, -98.0)
    full_c = (440.0, 0.0, -40.0)
    S = []

    def add(name, cam, note, target, dist=1.1, fill=0.0, **kw):
        S.append(dict({"name": name, "out": str(SETD / f"{name}.png"), "camera": cam, "samples": samples,
                       "lights": l5_l(target, dist, fill), "note": note}, **kw))

    add("receiver_right_3x", ortho_look(rec_c, R, 320, 210, px3), "receiver, true right, ortho 3x", rec_c)
    add("receiver_left_3x", ortho_look(rec_c, Lf, 320, 210, px3), "receiver, true left, ortho 3x", rec_c)
    add("brake_front_sight_right_3x", ortho_look((822.0, 0.0, 12.0), R, 140, 100, px3),
        "front sight block + muzzle brake, true right, ortho 3x", (822.0, 0.0, 12.0))
    add("brake_front_sight_left_3x", ortho_look((822.0, 0.0, 12.0), Lf, 140, 100, px3),
        "front sight block + muzzle brake, true left, ortho 3x", (822.0, 0.0, 12.0))
    add("brake_front_sight_34_3x", persp_look((960.0, -150.0, 60.0), (840.0, 0.0, 0.0), 32.0, (1600, 1100)),
        "front sight + brake, 3/4 front right (slant cut and port), perspective", (840.0, 0.0, 0.0))
    add("mag_left_2x", ortho_look(mag_c, Lf, 160, 200, px2), "SM_AR01_Mag alone (seated pose), true left, ortho 2x",
        mag_c, show=["mag"])
    add("mag_front_2x", ortho_look(mag_c, (-1.0, 0.0, 0.0), 110, 200, px2), "SM_AR01_Mag alone, from the front, ortho 2x",
        mag_c, show=["mag"])
    add("mag_34_2x", persp_look((600.0, -260.0, 20.0), mag_c, 30.0, (1200, 1400)),
        "SM_AR01_Mag alone, 3/4 front right from above (feed lips, lugs)", mag_c, show=["mag"])
    add("reload_magrockstart_right_3x", ortho_look(well_c, R, 240, 230, px3),
        "reload: SM_AR01_Mag at the MagRockStart socket (front lug hooked, base swung forward), true right, ortho 3x",
        well_c, pose=rock_pose)
    add("reload_magrockstart_fp", persp_look((240.0, 230.0, 150.0), (430.0, 0.0, -60.0), 45.0, (1600, 1000)),
        "reload at MagRockStart seen from the shooter's side (left, above, behind)", (430.0, 0.0, -60.0),
        pose=rock_pose)
    add("reload_magrockstart_34_below", persp_look((580.0, -300.0, -170.0), (430.0, 0.0, -45.0), 34.0, (1600, 1100)),
        "reload at MagRockStart from front right below (front lug in the trunnion recess)", (430.0, 0.0, -45.0),
        pose=rock_pose)
    add("bolt_rear_right_3x", ortho_look(rec_c, R, 320, 210, px3),
        "bolt carrier + charging handle at full rearward travel (A_AR01_Charge frame %d ChargeRear), ortho 3x"
        % charge_rear, rec_c, pose=bolt_pose, fill=15.0)
    add("bolt_rear_34_above", persp_look((470.0, -260.0, 210.0), (400.0, 0.0, 15.0), 34.0, (1600, 1100)),
        "bolt at full rearward travel, open ejection port from right above", (400.0, 0.0, 15.0), pose=bolt_pose,
        fill=15.0)
    for lv in range(4):
        add(f"lod/lod{lv}_side", ortho_look(full_c, R, 920, 330, 1600 / 920.0),
            f"SK_AR01 LOD{lv} + SM_AR01_Mag LOD{lv}, true right, ortho", full_c, lod=lv, mag_lod=lv)
        add(f"lod/lod{lv}_side_wire", ortho_look(full_c, R, 920, 330, 1600 / 920.0),
            f"SK_AR01 LOD{lv} + mag LOD{lv} wireframe", full_c, lod=lv, mag_lod=lv, look="wire",
            samples=min(samples, 48))
    add("wireframe_lod0_side", ortho_look(full_c, R, 920, 330, PX1), "SK_AR01 LOD0 + mag LOD0 wireframe, 1x",
        full_c, look="wire", samples=min(samples, 48))
    add("wireframe_receiver_3x", ortho_look(rec_c, R, 320, 210, px3), "LOD0 wireframe, receiver 3x", rec_c,
        look="wire", samples=min(samples, 48))
    add("wireframe_34", persp_look((450.0, 0.0, -20.0) + 1500.0 * unit([0.55, -0.78, 0.30]), (450.0, 0.0, -20.0), 38.0,
                                   (1600, 900)), "LOD0 wireframe, hero 3/4", (450.0, 0.0, -20.0), dist=1.6,
        look="wire", samples=min(samples, 48))
    hero_t = np.array([450.0, 0.0, -20.0])
    add("tp_8m", persp_look(hero_t + 8000.0 * unit([-0.45, -0.85, 0.28]), hero_t, 60.0, (1600, 900)),
        "third person: camera 8 m from the gun, 60 deg FOV (RIFLE_BUILD_PLAN 9 review set)", hero_t, dist=3.2)
    return S


def lod_strips():
    sk = json.loads((EXP / "SK_AR01.skeletal.json").read_text())
    tris = sk.get("lod_triangles", {})
    names = ["SK_AR01", "SK_AR01_LOD1", "SK_AR01_LOD2", "SK_AR01_LOD3"]
    for suffix, out in (("", "lod_strip.png"), ("_wire", "lod_strip_wire.png")):
        ims = [Image.open(SETD / "lod" / f"lod{k}_side{suffix}.png").convert("RGB") for k in range(4)]
        Wd, Hd = ims[0].size
        S = Image.new("RGB", (Wd, (Hd + 34) * 4), (255, 255, 255))
        fnt = CU._font(22)
        for k, im in enumerate(ims):
            S.paste(im, (0, k * (Hd + 34) + 34))
            lab = f"LOD{k}: {names[k]} {tris.get(names[k], '?')} tris + SM_AR01_Mag_LOD{k}"
            ImageDraw.Draw(S).text((6, k * (Hd + 34) + 5), lab, fill=(0, 0, 0), font=fnt)
        S.save(SETD / out)


def contact(paths, out, cols=2, w=800):
    ims = []
    for p, label in paths:
        im = Image.open(p).convert("RGB")
        im = im.resize((w, max(1, int(im.height * w / im.width))), Image.LANCZOS)
        ImageDraw.Draw(im).rectangle((0, 0, w, 16), fill=(0, 0, 0))
        ImageDraw.Draw(im).text((4, 2), label[:120], fill=(255, 255, 255))
        ims.append(im)
    rows = [ims[i:i + cols] for i in range(0, len(ims), cols)]
    H = sum(max(i.height for i in r) for r in rows)
    S = Image.new("RGB", (w * cols, H), (40, 40, 40))
    y = 0
    for r in rows:
        for j, im in enumerate(r):
            S.paste(im, (j * w, y))
        y += max(i.height for i in r)
    S.save(out)


# ------------------------------------------------------------------------------------------------ run
def run_job(name, shots, samples):
    JOBD.mkdir(parents=True, exist_ok=True)
    job = {"exports_dir": str(EXP), "tex_dir": str(TEXD), "offset_M": [float(v) for v in GRIP],
           "gun_lods": ["SK_AR01.fbx", "SK_AR01_LOD1.fbx", "SK_AR01_LOD2.fbx", "SK_AR01_LOD3.fbx"],
           "mag_fbx": "SM_AR01_Mag.fbx", "mag_lod_prefix": "SM_AR01_Mag_LOD", "mag_bone": "magazine",
           "clips": ["A_AR01_Charge", "A_AR01_ReloadEmpty"],
           "materials": {"M_AR01_Metal": "T_AR01_Metal", "M_AR01_Furniture": "T_AR01_Furniture",
                         "M_AR01_Mag": "T_AR01_Mag"},
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="blind,realism,set")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--tag", default="", help="trial renders: review/realism_<tag>, review/set_<tag>; no gate file")
    a = ap.parse_args()
    only = set(a.only.split(","))
    gp = GATES / "review_export.json"
    if a.tag:
        global REAL, SETD
        REAL, SETD = REVIEW / f"realism_{a.tag}", REVIEW / f"set_{a.tag}"
        gp = SCRATCH / "export_review" / f"review_export_{a.tag}.json"
    res = json.loads(gp.read_text()) if gp.exists() else {}
    res.update({"stage": "7 review renders from the exported bytes", "date": __import__("datetime").date.today().isoformat(),
                "inputs_sha256": {rel(p): sha(p) for p in sorted(EXP.glob("*.fbx")) + sorted(TEXD.glob("*.png"))}})
    if "blind" in only:
        shots, meta = blind_shots(a.samples)
        rr = None if a.no_render else run_job("blind", shots, a.samples)
        key, checks = make_blind(meta)
        keyj = {f"pair_{n:02d}": v for n, v in key.items()}
        keyj["_about"] = {
            "folder": "WorkFiles/guns/rifle/review/blind (images only; this key lives outside it)",
            "rule": "ours = B on pairs 1, 2, 4, 7, 8, 11; ours = A on 3, 5, 6, 9, 10, 12",
            "ours_source": "the EXPORTED bytes: SK_AR01.fbx + SM_AR01_Mag.fbx (seated on the magazine bone) with "
                           "game materials from Exports/Guns/AR01/Textures (BC sRGB, ORM linear, N DirectX); Cycles",
            "resolution": "ours rendered at 3x the panel with a transparent film, composited on the panel's fitted "
                          "studio backdrop, reduced to the panel's native px (box) and enlarged with the same LANCZOS "
                          "filter as the reference (3x; pair 12 6x): both images carry the panel's resolution",
            "lights": "sides / top: the L5 physical rig (scratch/game/l5.json fit, mirrored for the true left); 3/4 "
                      "and close-ups: the detail kit's rough_lights rig (env 0.55, k 1.35) on the panel's backdrop",
            "poses": "c1: selector 13.25 deg front-down as the close-up draws it (rifle_detail SEL_C1_POSE); "
                     "c4 / c5: magazine alone; c7: everything forward of the stock clipped by the camera",
            "crops": "side panels: rows 0-%d (above the 0-90 cm ruler)" % SIDE_ROWS}
        KEYF.write_text(json.dumps(keyj, indent=1))
        contact_pairs(keyj)
        res["blind"] = {"pairs": 12, "images": len(list(BLIND.glob("pair_*.png"))), "framing_checks": checks,
                        "key": rel(KEYF), "unblinded_contact": rel(BSRC / "key_contact_UNBLINDED.png")}
    if "realism" in only:
        REAL.mkdir(parents=True, exist_ok=True)
        sh = realism_shots(a.samples)
        rr = None if a.no_render else run_job("realism", sh, a.samples)
        contact([(s_["out"], s_["name"] + ": " + s_["note"]) for s_ in sh], REAL / "contact.png")
        (REAL / "shots.json").write_text(json.dumps({"source": "EXPORTED bytes (SK_AR01 + SM_AR01_Mag + shipped "
                                                               "textures)", "shots": [dict(s_, out=rel(s_["out"]))
                                                                                      for s_ in sh]}, indent=1))
        res["realism"] = {"images": len(sh), "files": [rel(s_["out"]) for s_ in sh]}
    if "set" in only:
        SETD.mkdir(parents=True, exist_ok=True)
        sh = set_shots(a.samples)
        rr = None if a.no_render else run_job("set", sh, a.samples)
        lod_strips()
        main_imgs = [s_ for s_ in sh if not s_["name"].startswith("lod/")]
        contact([(s_["out"], s_["name"] + ": " + s_["note"]) for s_ in main_imgs] +
                [(SETD / "lod_strip.png", "LOD strip"), (SETD / "lod_strip_wire.png", "LOD strip wireframe")],
                SETD / "contact.png", cols=3, w=640)
        rec = {}
        if rr:
            byname = {r["name"]: r for r in rr["shots"]}
            rb = rr.get("rest_bolt_M_mm")
            bb = byname["bolt_rear_right_3x"]["bones_M_mm"].get("bolt")
            rec = {"bolt_rest_M_mm": rb, "bolt_rear_M_mm": bb,
                   "bolt_travel_mm": round(float(np.linalg.norm(np.array(bb) - np.array(rb))), 3) if rb and bb else None,
                   "mag_at_MagRockStart": {"M_mm": byname["reload_magrockstart_right_3x"]["mag_M_mm"],
                                           "pitch_deg": byname["reload_magrockstart_right_3x"]["mag_pitch_deg"]},
                   "mag_seated_M_mm": byname["receiver_right_3x"]["mag_M_mm"],
                   "lod_faces": rr.get("gun_faces"), "mag_lod_faces": rr.get("mag_faces")}
        (SETD / "shots.json").write_text(json.dumps({"source": "EXPORTED bytes", "scale": "1x = %.3f px/mm" % PX1,
                                                     "poses": rec, "shots": [dict(s_, out=rel(s_["out"]))
                                                                            for s_ in sh]}, indent=1))
        n_main = len(main_imgs) + 2
        res["set"] = {"images": n_main, "lod_frames": 8, "files": [rel(s_["out"]) for s_ in main_imgs] +
                      [rel(SETD / "lod_strip.png"), rel(SETD / "lod_strip_wire.png")], "poses": rec}
    gp.write_text(json.dumps(res, indent=1))
    print(json.dumps({k: (v if k != "inputs_sha256" else len(v)) for k, v in res.items()}, indent=1)[:4000])


if __name__ == "__main__":
    main()
