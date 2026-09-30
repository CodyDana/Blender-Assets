"""Swatch sheet + numbers for the shared dojo material library (py -3: Pillow + numpy).

Per material row: the reference crops (studio model sheets, then the sunset establishing view), shapes A and B under
the studio rig, the same under sunset, and the albedo tiled 3 x 3 (the seam / repetition proof).
Numbers (measure, don't eyeball): per-channel medians of the object pixels (alpha > 0.98) of the studio renders vs
the median of the studio reference crops, CIE76 dE (sRGB D65 -> Lab), luminance p50 ratio; the same for sunset vs
dojo1_reference2's crops where the sheet shows the material.

  py -3 Scripts/dojo/materials/compose_swatches.py --round r1
Writes WorkFiles/dojo/build/materials/SWATCH_SHEET_<round>.png (+ per-row PNGs in renders/<round>/rows/) and
numbers_<round>.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import ref_crops  # noqa: E402

WORK = ROOT / "WorkFiles" / "dojo" / "build" / "materials"
TEX = ROOT / "Exports" / "DojoKit" / "Materials" / "Textures"
ARGS = sys.argv[1:]
ROUND = ARGS[ARGS.index("--round") + 1] if "--round" in ARGS else "r1"
RND = WORK / "renders" / ROUND
C = 200          # cell size
ORDER = ["TimberDark", "TimberAged", "Granite", "GraniteRubble", "Iron", "Rope", "PlasterCream", "PlasterEarth",
         "RoofTile", "Lacquer", "GlassAmber", "VendingPanel"]
STUDIO_BG = (170, 170, 170)
SUNSET_BG_TOP, SUNSET_BG_BOT = (104, 96, 118), (206, 140, 96)


def font(sz):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


F_B, F_S = font(17), font(12)


def srgb_to_lab(c):
    c = np.asarray(c, float) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = M @ lin / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def de76(a, b):
    return float(np.linalg.norm(srgb_to_lab(a) - srgb_to_lab(b)))


def lum(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def fit(im, w, h, bg=(40, 40, 40)):
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    r = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    out = Image.new("RGB", (w, h), bg)
    out.paste(r, ((w - r.width) // 2, (h - r.height) // 2))
    return out


def over(im, light):
    im = im.convert("RGBA")
    if light == "studio":
        bg = Image.new("RGBA", im.size, STUDIO_BG + (255,))
    else:
        t = np.linspace(0, 1, im.height)[:, None]
        g = (np.array(SUNSET_BG_TOP)[None, :] * (1 - t) + np.array(SUNSET_BG_BOT)[None, :] * t).astype(np.uint8)
        bg = Image.fromarray(np.repeat(g[:, None, :], im.width, 1)).convert("RGBA")
    bg.alpha_composite(im)
    return bg.convert("RGB")


def obj_pixels(path):
    a = np.asarray(Image.open(path).convert("RGBA")).astype(float)
    m = a[..., 3] > 250
    return a[..., :3][m]


def tiled(set_name):
    p = TEX / f"T_DJ_{set_name}_BC.png"
    im = Image.open(p).convert("RGB")
    t = im.resize((C // 3 * 1 + 1, C // 3 * 1 + 1), Image.LANCZOS) if False else im.resize((C // 3, C // 3), Image.LANCZOS)
    out = Image.new("RGB", (C, C), (40, 40, 40))
    for i in range(3):
        for j in range(3):
            out.paste(t, (i * (C // 3), j * (C // 3)))
    return out


def main():
    refm = json.loads((WORK / "ref_medians.json").read_text())
    texrep = json.loads((WORK / "textures_report.json").read_text())
    shapes = json.loads((RND / "shapes.json").read_text()) if (RND / "shapes.json").exists() else {}
    rows, numbers = [], {"round": ROUND}
    for key in ORDER:
        if not (RND / f"{key}_A_studio.png").exists():
            continue
        crops = refm.get(key, [])
        st = [c for c in crops if c["light"] == "studio"]
        su = [c for c in crops if c["light"] == "sunset"]
        n = {}
        if st:
            ref_med = np.median(np.array([c["median_srgb"] for c in st]), 0)
            px = np.concatenate([obj_pixels(RND / f"{key}_{w}_studio.png") for w in ("A", "B")
                                 if (RND / f"{key}_{w}_studio.png").exists()])
            r_med = np.median(px, 0)
            n["studio"] = {"ref_median": [int(round(x)) for x in ref_med], "render_median": [int(round(x)) for x in r_med],
                           "dE76": round(de76(ref_med, r_med), 1),
                           "lum_ratio": round(lum(r_med) / max(lum(ref_med), 1e-6), 3),
                           "ref_crops": [f'{c["sheet"]} {c["note"]} {c["median_srgb"]}' for c in st]}
        if su:
            ref_med = np.median(np.array([c["median_srgb"] for c in su]), 0)
            px = np.concatenate([obj_pixels(RND / f"{key}_{w}_sunset.png") for w in ("A", "B")
                                 if (RND / f"{key}_{w}_sunset.png").exists()])
            r_med = np.median(px, 0)
            n["sunset"] = {"ref_median": [int(round(x)) for x in ref_med], "render_median": [int(round(x)) for x in r_med],
                           "dE76": round(de76(ref_med, r_med), 1),
                           "lum_ratio": round(lum(r_med) / max(lum(ref_med), 1e-6), 3)}
        if key in ("GlassAmber", "VendingPanel"):
            # emissive: compare only the glowing pixels (luminance > 90) so frames / muntins do not decide it
            def glow(px):
                L = 0.2126 * px[:, 0] + 0.7152 * px[:, 1] + 0.0722 * px[:, 2]
                g = px[L > 90]
                return np.median(g, 0) if len(g) else np.array([0, 0, 0]), float((L > 90).mean())
            rp = np.concatenate([np.asarray(Image.open(WORK / "refcrops" / c["file"]).convert("RGB")).reshape(-1, 3)
                                 .astype(float) for c in st])
            op = np.concatenate([obj_pixels(RND / f"{key}_{w}_studio.png") for w in ("A", "B")])
            (rg, rf), (og, of) = glow(rp), glow(op)
            hue = lambda c: float(np.degrees(np.arctan2(np.sqrt(3) * (c[1] - c[2]), 2 * c[0] - c[1] - c[2])) % 360)
            n["glow"] = {"ref_median": [int(round(x)) for x in rg], "render_median": [int(round(x)) for x in og],
                         "dE76": round(de76(rg, og), 1), "ref_hue_deg": round(hue(rg), 1),
                         "render_hue_deg": round(hue(og), 1), "ref_glow_share": round(rf, 3),
                         "render_glow_share": round(of, 3)}
        setname = key
        tr = texrep.get(setname, {})
        n["albedo_median"] = tr.get("median_srgb")
        n["seam_rank_bc"] = tr.get("seam_rank_bc")
        if key.startswith("Timber"):
            e = texrep.get(key + "End", {})
            n["end_vs_face_lum_p50"] = round(e["lum_p10_p50_p90"][1] / tr["lum_p10_p50_p90"][1], 3) if e else None
        if key == "Iron":
            n["metal"] = {k: tr.get(k) for k in ("metal_share_ge_0.95", "metal_share_zero", "metal_share_partial")}
        n["texel"] = shapes.get(key, {}).get("texel")
        n["wear_G_area_share"] = shapes.get(key, {}).get("wear_G_area_share")
        numbers[key] = n
        # ---- row image
        ncols = 1 + 3 + 4 + 1 + 1
        row = Image.new("RGB", (220 + (ncols - 1) * (C + 6), C + 34), (28, 28, 30))
        d = ImageDraw.Draw(row)
        d.text((8, 6), key, font=F_B, fill=(235, 235, 235))
        y = 32
        if "studio" in n:
            s = n["studio"]
            for line in (f"studio ref  {tuple(s['ref_median'])}", f"studio ours {tuple(s['render_median'])}",
                         f"dE76 {s['dE76']}   lum x{s['lum_ratio']}"):
                d.text((8, y), line, font=F_S, fill=(210, 210, 210))
                y += 16
        if "sunset" in n:
            s = n["sunset"]
            for line in (f"sunset ref  {tuple(s['ref_median'])}", f"sunset ours {tuple(s['render_median'])}",
                         f"dE76 {s['dE76']}   lum x{s['lum_ratio']}"):
                d.text((8, y), line, font=F_S, fill=(230, 200, 170))
                y += 16
        if "glow" in n:
            gl = n["glow"]
            for line in (f"glow ref  {tuple(gl['ref_median'])} h{gl['ref_hue_deg']}",
                         f"glow ours {tuple(gl['render_median'])} h{gl['render_hue_deg']}", f"glow dE76 {gl['dE76']}"):
                d.text((8, y), line, font=F_S, fill=(255, 210, 140))
                y += 16
        if n.get("end_vs_face_lum_p50"):
            d.text((8, y), f"end/face lum {n['end_vs_face_lum_p50']}", font=F_S, fill=(210, 210, 210))
            y += 16
        if key == "Iron":
            m = n["metal"]
            d.text((8, y), f"metal>=.95 {m['metal_share_ge_0.95']}  0: {m['metal_share_zero']}", font=F_S,
                   fill=(210, 210, 210))
            y += 16
            d.text((8, y), f"partial {m['metal_share_partial']}", font=F_S, fill=(210, 210, 210))
        x = 220
        heads = []
        for c in st[:3]:
            row.paste(fit(Image.open(WORK / "refcrops" / c["file"]), C, C), (x, 30))
            heads.append((x, "REF " + c["note"][:26]))
            x += C + 6
        x = 220 + 3 * (C + 6)
        for light in ("studio", "sunset"):
            for w in ("A", "B"):
                p = RND / f"{key}_{w}_{light}.png"
                if p.exists():
                    row.paste(fit(over(Image.open(p), light), C, C), (x, 30))
                    heads.append((x, f"ours {w} {light}"))
                x += C + 6
        row.paste(tiled(setname), (x, 30))
        heads.append((x, "albedo 3x3 tiles"))
        x += C + 6
        for c in su[:1]:
            row.paste(fit(Image.open(WORK / "refcrops" / c["file"]), C, C), (x, 30))
            heads.append((x, "REF sunset " + c["note"][:18]))
        for hx, t in heads:
            d.text((hx + 2, 10), t, font=F_S, fill=(255, 220, 120) if t.startswith("REF") else (170, 220, 255))
        (RND / "rows").mkdir(exist_ok=True)
        row.save(RND / "rows" / f"row_{key}.png")
        rows.append(row)
    W = max(r.width for r in rows)
    sheet = Image.new("RGB", (W, sum(r.height + 4 for r in rows) + 40), (18, 18, 20))
    ImageDraw.Draw(sheet).text((10, 10), f"Dojo shared material library - swatch sheet {ROUND} (references are "
                                          f"AI-generated modelling sheets; left: REF crops, right: ours)",
                               font=F_B, fill=(240, 240, 240))
    y = 40
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 4
    out = WORK / f"SWATCH_SHEET_{ROUND}.png"
    sheet.save(out)
    (WORK / f"numbers_{ROUND}.json").write_text(json.dumps(numbers, indent=1), encoding="utf-8")
    for k, v in numbers.items():
        if isinstance(v, dict):
            print(k, {kk: (vv if kk not in ("studio", "sunset", "glow") else
                           (vv["ref_median"], vv["render_median"], vv["dE76"], vv.get("lum_ratio")))
                      for kk, vv in v.items() if kk in ("studio", "sunset", "glow", "end_vs_face_lum_p50")})
    print(out)


if __name__ == "__main__":
    _ = ref_crops
    main()
