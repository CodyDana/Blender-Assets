"""Round 3: old (r3start_backup) vs new texture contact sheet + speckle / colour metrics. System Python (PIL, numpy).
  py -3 Scripts/dojo/materials/r3/compare_tex_r3.py"""
import colorsys, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects")
OUT = ROOT / "WorkFiles/dojo/build/round3/ground_materials"
BK = OUT / "r3start_backup"
SETS = [("lib", "T_DJ_TimberDark"), ("lib", "T_DJ_TimberAged"), ("lib", "T_DJ_Granite"), ("lib", "T_DJ_RoofTile"),
        ("lib", "T_DJ_PlasterCream"), ("lib", "T_DJ_PlasterEarth"), ("lib", "T_DJ_Lacquer"),
        ("ground", "T_DKG_SandRaked"), ("ground", "T_DKG_Gravel"), ("ground", "T_DKG_GravelCoarse")]


def gblur(a, s):
    h, w = a.shape
    fy, fx = np.fft.fftfreq(h)[:, None], np.fft.fftfreq(w)[None, :]
    return np.real(np.fft.ifft2(np.fft.fft2(a) * np.exp(-2 * (np.pi * s) ** 2 * (fx * fx + fy * fy))))


def stats(a):
    L = a @ np.array([0.2126, 0.7152, 0.0722])
    m = np.median(a.reshape(-1, 3), 0)
    h, s, v = colorsys.rgb_to_hsv(*m)
    return {"median_srgb": [int(round(x * 255)) for x in m], "hue": round(h * 360, 1), "sat": round(s, 3),
            "hp_std_rel_3px": round(float((L - gblur(L, 3)).std() / L.mean()), 4),
            "mid_std_rel_3_40px": round(float((gblur(L, 3) - gblur(L, 40)).std() / L.mean()), 4),
            "low_std_rel_40px": round(float((gblur(L, 40) - L.mean()).std() / L.mean()), 4)}


def main():
    res, tiles = {}, []
    for kit, stem in SETS:
        new = (ROOT / ("Exports/DojoKit/Materials/Textures" if kit == "lib" else "Exports/DojoKit/Ground/Textures")
               / f"{stem}_BC.png")
        old = BK / ("tex_lib" if kit == "lib" else "tex_ground") / f"{stem}_BC.png"
        r = {}
        row = []
        for tag, pth in (("r2", old), ("r3", new)):
            im = Image.open(pth).convert("RGB")
            a = np.asarray(im, dtype=np.float64) / 255.0
            r[tag] = stats(a)
            w = im.size[0]
            row.append(im.resize((384, 384 * im.size[1] // w), Image.LANCZOS))
            row.append(im.crop((0, 0, w // 8, w // 8)).resize((384, 384), Image.NEAREST))   # 0.5 m close-up
        res[stem] = r
        tiles.append((stem, row, r))
    W, H = 4 * 392 + 260, len(tiles) * 400 + 30
    sheet = Image.new("RGB", (W, H), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), "round 3 textures: r2 tile | r2 0.5 m corner | r3 tile | r3 0.5 m corner", fill=(230, 230, 230))
    for i, (stem, row, r) in enumerate(tiles):
        y = 30 + i * 400
        d.text((8, y + 4), stem, fill=(255, 220, 150))
        for k, tag in enumerate(("r2", "r3")):
            s = r[tag]
            d.text((8, y + 24 + 70 * k), f"{tag} {s['median_srgb']} h{s['hue']} s{s['sat']}\n hp {s['hp_std_rel_3px']} "
                                          f"mid {s['mid_std_rel_3_40px']}\n low {s['low_std_rel_40px']}", fill=(220, 220, 220))
        for k, t in enumerate(row):
            sheet.paste(t.crop((0, 0, 384, 384)), (260 + k * 392, y))
    sheet.save(OUT / "TEXTURES_R2_vs_R3.png")
    (OUT / "texture_metrics_r2_vs_r3.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


main()
