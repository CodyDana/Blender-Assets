"""SHOWCASE_SHEET_R4.png: DojoLab round 4 (the remaining buildings, 2026-09-29) captures on one sheet, with
dojo1_reference2. The round-3 camera set plus the round-4 close-ups (storehouse, residence, corridor, shed + vending,
pavilion + taiko, hall and gate ridges).

Run: py -3 WorkFiles/dojo/build/unreal/round4/make_sheet_r4.py [capture_dir] [tag]
In:  <capture_dir>/CAM_*.png + CU_*.png (dj_sc_capture.py with DJ_CAPTURE_DIR)
Out: <capture_dir>/SHOWCASE_SHEET_R4[_<tag>].png
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\Users\Cody\Desktop\Blender_Projects")
HERE = Path(__file__).resolve().parent
CAP = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "r4"
TAG = sys.argv[2] if len(sys.argv) > 2 else ""
REF2 = ROOT / "References" / "Dojo" / "dojo1_reference2.png"
TILES = [
    ("REF", "dojo1_reference2 (look reference)"),
    ("CAM_Establishing", "Establishing: in the gateway toward the hall"),
    ("CAM_EstablishingRef2", "Ref 2 elevated framing (3.1 m)"),
    ("CAM_PlayerEyeSand", "Player eye on the raked sand"),
    ("CAM_Overview", "Overview from above the gate"),
    ("CU_R4_StorehouseFront", "R4: storehouse (NW) from the courtyard"),
    ("CU_R4_ResidenceFront", "R4: residence (NE) from the courtyard"),
    ("CU_R4_CorridorOpen", "R4: west corridor, open side"),
    ("CU_R4_ShedVending", "R4: training shed + vending machine"),
    ("CU_R4_PavilionTaiko", "R4: drum pavilion with the taiko"),
    ("CU_R4_RidgeHall", "R4: hall ridge close (noshi + onigawara)"),
    ("CU_R4_RidgeGate", "R4: gate ridge close (noshi + onigawara)"),
    ("CAM_HallVeranda", "Hall: step band, central stair, veranda"),
    ("CAM_HallRoofClimb", "Routes 4-5: eave landing, lower roof, AC"),
    ("CAM_GateFromCourtyard", "Gate from the courtyard"),
    ("CAM_GateFromStreet", "Gate from the street"),
    ("CAM_Drum", "Taiko under the pavilion"),
    ("CAM_EastYard", "East yard: well, residence"),
    ("CAM_VendingShed", "Vending machine / shed corner"),
    ("CAM_WallTop", "West wall top"),
    ("CAM_WallCorner", "SE wall corner from outside"),
    ("CU_SandEye", "Close: raked sand at eye level"),
    ("CU_PathStepBand", "Close: slab path + step band"),
    ("CU_WallFooting", "Close: wall footing, dressed course, cap"),
    ("CU_GateFront", "Close: gate front from the street"),
    ("CU_HallUpperRoof", "Close: hall upper roof, ridges"),
    ("CU_Lantern", "Close: tall stone lantern"),
    ("CU_Taiko", "Close: taiko, sticks, stand"),
    ("CU_Training", "Close: makiwara, rack, wooden dummy"),
]


def fit(img, w, h):
    s = min(w / img.width, h / img.height)
    return img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)


def main():
    tw, th, pad, lab = 640, 360, 14, 30
    cols = 5
    rows = (len(TILES) + cols - 1) // cols
    W = cols * tw + (cols + 1) * pad
    head = 64
    H = head + rows * (th + lab + pad) + pad
    sheet = Image.new("RGB", (W, H), (24, 24, 26))
    d = ImageDraw.Draw(sheet)
    f_big = ImageFont.truetype("arialbd.ttf", 28)
    f = ImageFont.truetype("arial.ttf", 17)
    title = ("DojoLab L_Dojo - round 4 (2026-09-29): storehouse, residence, corridors, shed and pavilion replace the "
             "grey-box; round-4 ridges on the hall and gate; UE 5.8 offscreen captures (Lumen, 96 frames)")
    if TAG:
        title += f" [{TAG}]"
    d.text((pad, 16), title, font=f_big, fill=(235, 235, 235))
    for k, (name, text) in enumerate(TILES):
        r, c = divmod(k, cols)
        x = pad + c * (tw + pad)
        y = head + r * (th + lab + pad)
        path = REF2 if name == "REF" else CAP / f"{name}.png"
        if not path.exists():
            d.text((x + 10, y + th // 2), f"missing {name}", font=f, fill=(255, 90, 90))
            continue
        t = fit(Image.open(path).convert("RGB"), tw, th)
        sheet.paste(t, (x + (tw - t.width) // 2, y + (th - t.height) // 2))
        d.text((x + 2, y + th + 5), (name if name != "REF" else "REFERENCE") + " - " + text, font=f, fill=(220, 220, 220))
    out = CAP / (f"SHOWCASE_SHEET_R4_{TAG}.png" if TAG else "SHOWCASE_SHEET_R4.png")
    sheet.save(out, optimize=True)
    print("SHEET", out, sheet.size)


main()
