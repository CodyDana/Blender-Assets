"""Compose our petal panels into the sheet's two-row layout and a reference | ours side-by-side; measure ours.

    py -3 -B Scripts/dojo/fx/compose_petal_sheet.py --renders WorkFiles/dojo/build/fx/renders/sheet_r0
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fx_common as fx  # noqa: E402
from measure_petal_ref import REF_PANELS, REF_ROW, REF_ROW2  # noqa: E402

ORDER = ["A", "B", "C", "D", "E", "F"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    a = ap.parse_args()
    rd = Path(a.renders)
    ref = Image.open(fx.PETAL_REF).convert("RGB")
    ours = Image.new("RGB", (1448, 390), (99, 97, 96))
    for i, k in enumerate(ORDER):
        x0, x1 = REF_PANELS[i]
        w = x1 - x0
        r1 = Image.open(rd / f"row1_{k}.png").convert("RGB")
        h1 = REF_ROW[1] - REF_ROW[0]
        ours.paste(r1.resize((w, h1), Image.LANCZOS), (x0, REF_ROW[0]))
        r2 = Image.open(rd / f"row2_{k}.png").convert("RGB")
        h2 = REF_ROW2[1] - REF_ROW2[0]
        ours.paste(r2.resize((w, h2), Image.LANCZOS), (x0, REF_ROW2[0]))
    d = ImageDraw.Draw(ours)
    for x0, _x1 in REF_PANELS[1:]:
        d.line([(x0 - 3, 8), (x0 - 3, 386)], fill=(150, 150, 150), width=1)
    d.line([(8, 229), (1440, 229)], fill=(150, 150, 150), width=1)
    ours_path = rd / "ours_sheet.png"
    ours.save(ours_path)
    top = ref.crop((0, 0, 1448, 390))
    sbs = Image.new("RGB", (1448, 390 * 2 + 30), (40, 40, 40))
    sbs.paste(top, (0, 0))
    sbs.paste(ours, (0, 420))
    dd = ImageDraw.Draw(sbs)
    dd.text((8, 395), "REFERENCE (top)  |  OURS (bottom): SM_DKF_Petal_A..F front+back (row 1), lying + edge-on (row 2)",
            fill=(230, 230, 230))
    sbs.save(rd / "SBS_petals_ref_vs_ours.png")
    spec = {"panels": REF_PANELS, "row": list(REF_ROW), "row2": list(REF_ROW2)}
    (rd / "panels.json").write_text(json.dumps(spec))
    subprocess.run([sys.executable, "-B", str(Path(__file__).parent / "measure_petal_ref.py"), "--image", str(ours_path),
                    "--panels", str(rd / "panels.json"), "--out", str(rd / "ours_measure.json")], check=True)


if __name__ == "__main__":
    main()
