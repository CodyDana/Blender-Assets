"""AR-01 detail pass: blind image pairs per detail part from a tagged crop render (plain Python):

    py -3 -B Scripts/guns/rifle/rifle_detail.py render --tag r3          # crops first (ROUGH LOOK, review blend)
    py -3 -B Scripts/guns/rifle/rifle_detail_blind.py --tag r3 [--parts selector,grip]

For each part, its primary authority panel's crop pair: review/detail_blind/<part>_<tag>/A.png = reference, B.png = ours
(identical window and size; the order is fixed so the key is trivial, the judge does not see it), key in
review/detail/<part>/key_<tag>.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import REVIEW  # noqa: E402

PRIMARY = {"selector": "c1", "trigger_guard": "c1", "front_sight": "c3", "muzzle_brake": "c3", "rear_sight": "c2",
           "receiver_right": "c1", "grip": "c6", "magazine": "c4", "butt_plate": "c7"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--parts", default="")
    a = ap.parse_args()
    parts = [p for p in a.parts.split(",") if p] or list(PRIMARY)
    out = {}
    for part in parts:
        k = PRIMARY[part]
        d = REVIEW / "detail" / part
        ref, ours = d / f"ref_{k}.png", d / f"{a.tag}_ours_{k}.png"
        if not (ref.exists() and ours.exists()):
            raise SystemExit(f"missing crops for {part}: {ref.name} / {ours.name}")
        if Image.open(ref).size != Image.open(ours).size:
            raise SystemExit(f"size mismatch {part}")
        bd = REVIEW / "detail_blind" / f"{part}_{a.tag}"
        bd.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ref, bd / "A.png")
        shutil.copyfile(ours, bd / "B.png")
        key = {"part": part, "panel": k, "A": "reference", "B": "ours", "tag": a.tag,
               "sources": {"A": f"detail/{part}/{ref.name}", "B": f"detail/{part}/{ours.name}"},
               "size": list(Image.open(ref).size),
               "look": "ROUGH LOOK; integrated build (all parts' latest rounds); standard kit window",
               "crops_json": f"detail/{part}/{a.tag}_crops.json"}
        (d / f"key_{a.tag}.json").write_text(json.dumps(key, indent=1))
        out[part] = str(bd)
        print("[blind]", part, k, bd)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
