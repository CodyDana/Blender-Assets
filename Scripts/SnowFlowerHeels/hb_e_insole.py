"""Stage E2: the printed insole (base colour in the insole's planar UV), placed from view A.

    blender -b --factory-startup --python Scripts/SnowFlowerHeels/hb_e_insole.py

The print traces are projected through the reference camera onto the insole; the emblem is then anchored on the heel
seat midline (our heel seat sits lower in the reference camera than the reference's, see the build report), keeping
the reference's relative layout. Planar UV: U = (u + 30) / 290, V = (v + 50) / 145 (2048 x 1024, 7 px/mm).
"""
import json
import math
import sys
from pathlib import Path

import bpy  # noqa: F401
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hb_camera as HC  # noqa: E402
import hb_common as C  # noqa: E402
import hb_geo as G  # noqa: E402
import metro_png as png  # noqa: E402
from hb_e_textures import petal_mask  # noqa: E402

W, H = 2048, 1024
U0, US, V0, VS = -30.0, 290.0, -50.0, 145.0


def to_px(uv_mm):
    u, v = uv_mm[..., 0], uv_mm[..., 1]
    x = (u - U0) / US * W
    y = (1.0 - (v - V0) / VS) * H
    return np.stack([x, y], -1)


def srgb2lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def hexc(h):
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])


def main():
    body = np.load(C.CACHE / "body_r.npz")
    surf = G.Surf(body["insole_v"], body["insole_t"].tolist())
    camd = json.loads((C.CACHE / "camera.json").read_text())
    cam = HC.Cam(camd["az"], camd["el"], camd["s"], camd["tx"], camd["ty"], camd.get("roll", 0.0))
    tr = C.load_json(C.SPEC)["traces"]
    # plane through the heel-seat part of the insole for rays that miss
    iv = body["insole_v"]
    sel = iv[(iv[:, 0] > -25) & (iv[:, 0] < 60)]
    cen = sel.mean(0)
    _, _, vt = np.linalg.svd(sel - cen)
    pn = vt[2]

    def proj(xy):
        xy = np.asarray(xy, float).reshape(-1, 2)
        out = []
        for q in xy:
            o, d = cam.ray(q)
            h = surf.hits(o, d, max_hits=1)
            if h:
                out.append(h[0][0])
            else:
                t = np.dot(cen - o, pn) / np.dot(d, pn)
                out.append(o + d * t)
        return np.array(out)[:, :2]

    em = proj(tr["A.insole_emblem"]["pts"])
    emi = proj(tr["A.insole_emblem_inner"]["pts"])
    stem = proj(tr["A.insole_branch_stem"]["pts"])
    b1 = proj(tr["A.insole_blossom_1"]["pts"])[0]
    b2 = proj(tr["A.insole_blossom_2"]["pts"])[0]
    buds = proj(tr["A.insole_buds"]["pts"])
    # anchor: emblem blunt end -> (-17, 6), tip direction along +u (the insole midline), reference scale kept
    a, tip = em[0], em[2]
    L = np.linalg.norm(tip - a)
    target_a = np.array([-17.0, 6.0])
    ang = math.atan2(tip[1] - a[1], tip[0] - a[0])
    rot = -ang + math.atan2(0.02, 1.0)
    scale = 40.0 / L                       # emblem 40 mm long (155 px at ~3.9 px/mm)
    Rm = np.array([[math.cos(rot), -math.sin(rot)], [math.sin(rot), math.cos(rot)]]) * scale

    def T(p):
        return (np.asarray(p, float) - a) @ Rm.T + target_a
    em, emi = T(em), T(emi)
    # the branch: laid out in IMAGE space along its own chord, mapped onto the insole midline from the emblem tip
    # (u 24) to the throat (u 125); sideways offsets keep the reference's wiggle at 1/3.9 mm per px
    simg = np.array(tr["A.insole_branch_stem"]["pts"], float)
    c0, c1 = simg[0], simg[-1]
    ax_i = (c1 - c0) / np.linalg.norm(c1 - c0)
    nx_i = np.array([-ax_i[1], ax_i[0]])
    Lc = np.linalg.norm(c1 - c0)
    u_a, u_b = em[2][0] + 1.0, 125.0

    def Bmap(pimg):
        p = np.asarray(pimg, float).reshape(-1, 2)
        along = (p - c0) @ ax_i / Lc
        side = (p - c0) @ nx_i / 3.9
        return np.column_stack([u_a + along * (u_b - u_a), em[2][1] + side * 0.9])
    stem = Bmap(simg)
    buds = Bmap(tr["A.insole_buds"]["pts"])
    b1 = Bmap(tr["A.insole_blossom_1"]["pts"])[0]
    b2 = Bmap(tr["A.insole_blossom_2"]["pts"])[0]
    print("INSOLE emblem", em.round(1).tolist(), "blossoms", b1.round(1), b2.round(1))

    # ---- paint (linear colour, then encode sRGB)
    ground = srgb2lin(hexc("#232120"))
    band = srgb2lin(hexc("#4c4a48"))
    img = np.zeros((H, W, 3)) + ground
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    # lighter satin centre band along the midline (v ~ 5..9 mm, following the outline centre)
    vmid = 7.0
    vpx = to_px(np.array([[0.0, vmid]]))[0, 1]
    half = 14.0 / VS * H
    f = np.exp(-0.5 * ((yy - vpx) / half) ** 2) * 0.8
    img = img * (1 - f[..., None]) + band * f[..., None]
    # mild mottling
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 1, (H // 8, W // 8))
    noise = np.kron(noise, np.ones((8, 8)))
    img *= (1 + 0.05 * noise)[..., None]

    silver = srgb2lin(hexc("#c9c2bc"))
    emb_ground = srgb2lin(hexc("#2a2420"))
    pearl = srgb2lin(hexc("#8a8380"))

    def fill_poly(poly_mm, col, alpha=1.0):
        P = to_px(np.asarray(poly_mm))
        x0, y0 = np.floor(P.min(0)).astype(int) - 2
        x1, y1 = np.ceil(P.max(0)).astype(int) + 2
        sub = np.stack([xx[y0:y1, x0:x1].ravel(), yy[y0:y1, x0:x1].ravel()], 1)
        sd = C.poly_sdf2(sub, P).reshape(y1 - y0, x1 - x0)
        a_ = np.clip(0.5 - sd, 0, 1) * alpha
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a_[..., None]) + col * a_[..., None]

    def line(pts_mm, width_mm, col):
        P = to_px(np.asarray(pts_mm))
        wpx = width_mm / US * W
        for p, q in zip(P[:-1], P[1:]):
            n = int(np.linalg.norm(q - p) / 1.0) + 1
            for t in np.linspace(0, 1, n):
                c = p + (q - p) * t
                x0, y0 = int(c[0] - wpx - 2), int(c[1] - wpx - 2)
                x1, y1 = int(c[0] + wpx + 3), int(c[1] + wpx + 3)
                d = np.hypot(xx[y0:y1, x0:x1] - c[0], yy[y0:y1, x0:x1] - c[1])
                a_ = np.clip(wpx / 2 - d + 0.5, 0, 1)
                img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a_[..., None]) + col * a_[..., None]

    def loop(poly_mm, width_mm, col):
        P = np.vstack([poly_mm, poly_mm[:1]])
        line(P, width_mm, col)

    # emblem: dark kite ground, silver outer and inner kite, spine and chevrons
    fill_poly(em, emb_ground)
    loop(em, 0.9, silver)
    loop(emi, 0.6, silver)
    line([0.5 * (em[0] + em[3]) * 0 + em[0], em[2]], 0.5, silver)
    ax = em[2] - em[0]
    Lx = np.linalg.norm(ax)
    ax /= Lx
    nx = np.array([-ax[1], ax[0]])
    for k in range(1, 6):
        c = em[0] + ax * Lx * (0.2 + 0.12 * k)
        wch = 5.5 * (1 - 0.13 * k)
        line([c - nx * wch - ax * 2.2, c, c + nx * wch - ax * 2.2], 0.45, silver)
    # branch, twigs, buds, blossoms
    stem_s = C.catmull(stem, 6)
    line(stem_s, 0.9, pearl * 1.1)
    for bpt in buds:
        j = np.argmin(np.linalg.norm(stem_s - bpt, axis=1))
        line([stem_s[j], bpt], 0.5, pearl)
        P = to_px(bpt[None])[0]
        r = 1.6 / US * W
        d = np.hypot(xx - P[0], yy - P[1])
        m = np.clip(r - d + 0.5, 0, 1)
        img[:] = img * (1 - m[..., None]) + pearl * 1.25 * m[..., None]
    for c, dpx in ((b1, 48), (b2, 55)):
        Rmm = 0.5 * dpx / cam.s * scale / (1.0 / cam.s) / cam.s if False else 0.5 * dpx / 3.88
        P = to_px(c[None])[0]
        Rpx = Rmm / US * W
        m, rel = petal_mask(H, W, P[0], P[1], Rpx, 0.3)
        col = pearl * (0.85 + 0.5 * rel[..., None])
        img[:] = img * (1 - m[..., None]) + col * m[..., None]
        d = np.hypot(xx - P[0], yy - P[1])
        mc = np.clip(Rpx * 0.16 - d + 0.5, 0, 1)
        img[:] = img * (1 - mc[..., None]) + silver * mc[..., None]
    enc = np.where(img <= 0.0031308, img * 12.92, 1.055 * np.clip(img, 0, 1) ** (1 / 2.4) - 0.055)
    out = C.R1 / "tex"
    out.mkdir(parents=True, exist_ok=True)
    png.write(str(out / "insole_print.png"), (np.clip(enc, 0, 1) * 255 + 0.5).astype(np.uint8))
    (out / "insole_uv.json").write_text(json.dumps({"U0": U0, "US": US, "V0": V0, "VS": VS, "size": [W, H],
                                                    "emblem_mm": em.tolist()}, indent=1))
    print("INSOLE_OK")


main()
