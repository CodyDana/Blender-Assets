"""AR-01 early-look crops in the ROUGH LOOK and the blind image pairs (plain Python; renders via headless Blender):

    py -3 -B Scripts/guns/rifle/rifle_early_look.py [--pairs early_blind2] [--key early_key2.json] [--tag ""]

Renders the built rifle (Assets/Guns/AR01.blend) at the two early-look cameras that rifle_closeups.py solves for the
close-ups c1 (receiver + selector, right) and c3 (front sight + muzzle) (scratch/q34/camera_c1.json / camera_c3.json,
orthographic), in the review-only ROUGH LOOK (gunlib.look via gunlib.render_job), composited on the panel's own fitted
backdrop at the reference crops' size and framing (review/early/ref_receiver.png / ref_frontsight.png are the panels
at 3x). Writes review/early/[tag_]ours_receiver.png / ours_frontsight.png and, with --pairs, the blind pairs
review/<pairs>/pair_01_A/B.png (ours = A) and pair_02_A/B.png (ours = B) with the key in review/<key>.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import SCRATCH, REVIEW  # noqa: E402

from gunlib import closeup as CU  # noqa: E402
import rifle_detail as RDT  # noqa: E402

SHOTS = (("c1", "receiver"), ("c3", "frontsight"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairs", default="")
    ap.add_argument("--key", default="early_key2.json")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    RDT.make_review_blend()                  # the build + the grip's checker bake source (shown by the normal map in game)
    K = RDT.kit()
    ss = K.ss
    out_dir = REVIEW / "early"
    out_dir.mkdir(parents=True, exist_ok=True)
    rdir = SCRATCH / "early_look"
    rdir.mkdir(parents=True, exist_ok=True)
    shots, meta = [], {}
    for key, name in SHOTS:
        camd = json.loads((SCRATCH / "q34" / f"camera_{key}.json").read_text())
        camd.setdefault("type", "ORTHO")
        P = K.panel(key)
        H, W = P.shape[:2]
        if list(camd["panel_px"]) != [W, H]:
            raise SystemExit(f"camera_{key}.json panel_px {camd['panel_px']} != panel {W}x{H}")
        _, _, _, bg = CU.fit_background(P)
        shots.append({"name": f"early_{name}", "camera": camd, "show": None, "poses": RDT.PANELS[key].get("poses", []),
                      "out": str(rdir / f"{name}.png"), "bg_rgb": [float(v) for v in bg.reshape(-1, 3).mean(0)],
                      "target_M": camd["image_centre_point_M"]})
        meta[name] = (P, bg)
    K.run_blender(shots, "render_early")
    pre = f"{a.tag}_" if a.tag else ""
    files = {}
    for key, name in SHOTS:
        P, bg = meta[name]
        rgba = np.asarray(Image.open(rdir / f"{name}.png").convert("RGBA"))
        ours = CU.composite_on(bg, rgba, ss)
        o = out_dir / f"{pre}ours_{name}.png"
        Image.fromarray(ours).save(o)
        ref = out_dir / f"ref_{name}.png"
        if not ref.exists():
            Image.fromarray(P.astype(np.uint8)).resize((P.shape[1] * ss, P.shape[0] * ss), Image.LANCZOS).save(ref)
        if Image.open(ref).size != Image.open(o).size:
            raise SystemExit(f"size mismatch {ref} {Image.open(ref).size} vs {o} {Image.open(o).size}")
        files[name] = (ref, o)
        print("[early] wrote", o, Image.open(o).size)
    if a.pairs:
        pd = REVIEW / a.pairs
        pd.mkdir(parents=True, exist_ok=True)
        ref1, our1 = files["receiver"]
        ref2, our2 = files["frontsight"]
        shutil.copyfile(our1, pd / "pair_01_A.png")
        shutil.copyfile(ref1, pd / "pair_01_B.png")
        shutil.copyfile(ref2, pd / "pair_02_A.png")
        shutil.copyfile(our2, pd / "pair_02_B.png")
        rel = lambda p: str(Path(p).resolve().relative_to(REVIEW.resolve())).replace("\\", "/")  # noqa: E731
        key = {"pair_01": {"subject": "receiver", "A": "ours", "B": "ref", "sources": {"A": rel(our1), "B": rel(ref1)},
                           "size": list(Image.open(our1).size)},
               "pair_02": {"subject": "frontsight", "A": "ref", "B": "ours", "sources": {"A": rel(ref2), "B": rel(our2)},
                           "size": list(Image.open(our2).size)},
               "look": "ROUGH LOOK (gunlib.look: worn blued steel, grained wood, panel backdrop); not the final textures",
               "cameras": {"pair_01": "scratch/q34/camera_c1.json", "pair_02": "scratch/q34/camera_c3.json"},
               "note": "same framing and size as the reference crops (the c1 / c3 panels at 3x)"}
        (REVIEW / a.key).write_text(json.dumps(key, indent=1))
        print("[early] pairs in", pd, "key", REVIEW / a.key)


if __name__ == "__main__":
    main()
