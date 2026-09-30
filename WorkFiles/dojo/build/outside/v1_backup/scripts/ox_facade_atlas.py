"""ROUND 6 (2026-09-29) OUTSIDE track: assemble the far town's facade atlas T_DKX_FarFacade_{BC,ORM,N} (2048 x 1024,
4 x 2 tiles of 512 px) from the tiles ox_facade.py baked off this track's own town houses (SM_DKX_House_A..E).

  BC   sRGB albedo (the Standard-view bake: open faces at their albedo, eaves / reveals darker by their own occlusion);
       the top 2 % of each tile (the roof edge and a sky sliver over the gable-front kura) is cut and the rest stretched
  ORM  linear: R AO 1.0 (the AO is already in BC), G roughness 0.85, B metallic 0
  N    flat DirectX tangent normal (128, 128, 255)
Tile order (row-major, u to the right, v up in UV = row 1 at the bottom of the image in Unreal's V-down space is
handled by the builder, which maps each tile's image rectangle directly): see TILES; build_outside.FAR_TILES reads the
same table from tiles_atlas.json.

Run: py -3 Scripts/dojo/outside/ox_facade_atlas.py
Out: Exports/DojoKit/Outside/Textures/T_DKX_FarFacade_{BC,ORM,N}.png, WorkFiles/dojo/build/round6/build/facade_tiles/
     tiles_atlas.json
"""
import json
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
TILES_DIR = ROOT / "WorkFiles" / "dojo" / "build" / "round6" / "build" / "facade_tiles"
OUT = ROOT / "Exports" / "DojoKit" / "Outside" / "Textures"
TILES = ["A_front", "B_front", "C_front", "D_front", "E_front", "B_side", "A_side", "E_side"]
T, COLS = 512, 4
W, H = T * COLS, T * 2


def main():
    bc = Image.new("RGB", (W, H))
    table = {}
    for i, name in enumerate(TILES):
        im = Image.open(TILES_DIR / f"{name}.png").convert("RGB")
        w, h = im.size
        im = im.crop((0, int(round(h * 0.02)), w, h))                 # drop the roof edge / sky sliver at the top
        im = im.resize((T, T), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.6))
        cx, cy = (i % COLS) * T, (i // COLS) * T
        bc.paste(im, (cx, cy))
        # UV rectangle (u0, v0, u1, v1) with v measured UP from the image bottom (Blender / FBX UV convention);
        # a 3 px inset keeps mips of the neighbours out
        e = 3.0
        table[name] = [round((cx + e) / W, 5), round(1.0 - (cy + T - e) / H, 5), round((cx + T - e) / W, 5),
                       round(1.0 - (cy + e) / H, 5)]
    OUT.mkdir(parents=True, exist_ok=True)
    bc.save(OUT / "T_DKX_FarFacade_BC.png")
    Image.new("RGB", (W, H), (255, int(round(0.85 * 255)), 0)).save(OUT / "T_DKX_FarFacade_ORM.png")
    Image.new("RGB", (W, H), (128, 128, 255)).save(OUT / "T_DKX_FarFacade_N.png")
    (TILES_DIR / "tiles_atlas.json").write_text(json.dumps({"size": [W, H], "tiles": table}, indent=1), encoding="utf-8")
    print("ATLAS", W, H, table)


if __name__ == "__main__":
    main()
