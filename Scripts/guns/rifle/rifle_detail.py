"""AR-01 detail pass: close-up panels, per-part cameras, traces and reference-vs-ours crops (plain Python; renders via
a headless Blender subprocess). Configures gunlib.detail.DetailKit with the rifle's sheet panels and detail parts.

    py -3 -B Scripts/guns/rifle/rifle_detail.py solve  [--parts selector,grip] [--force]
    py -3 -B Scripts/guns/rifle/rifle_detail.py trace  [--parts ...]
    py -3 -B Scripts/guns/rifle/rifle_detail.py render [--parts ...] [--tag before]
    py -3 -B Scripts/guns/rifle/rifle_detail.py all    [--parts ...] [--tag before] [--force]

Needs a current form build (Assets/Guns/AR01.blend + scratch/form_tris.npz: run_rifle.sh, or build_rifle.py --stage
form). Outputs: WorkFiles/guns/rifle/review/detail/<part>/ (solve_<panel>.png, trace_<panel>.png/.json,
ref_<panel>.png, [tag_]ours/pair/edges_<panel>.png, [tag_]crops.json), review/detail/_panels/ (panel solves),
scratch/detail/ (cameras, renders, job + log). Builders: solve_closeup_camera(part), trace_closeup(part),
render_part_crop(part) below are the per-part entry points.

Close-up panels (sheet px boxes, inclusive; found from the white separators): c1 RECEIVER AND SELECTOR (RIGHT),
c2 DUST COVER AND REAR SIGHT (TOP LEFT), c3 FRONT SIGHT AND MUZZLE (SIDE), c4 MAGAZINE (LEFT; true left, front edge
on the left), c5 MAGAZINE (FRONT), c6 PISTOL GRIP AND TRIGGER (LEFT; true left), c7 BUTT PLATE (END), plus the 3/4
FRONT RIGHT panel with its camera solved by rifle_q34.py (fixed here). Landmarks were read off 3x / 6x gridded zooms
(gunlib.closeup.grid_zoom); they are approximate (+-3 px) and the close-ups are stylised and not to scale, so each
part's camera is refined on the part's own window (the shape authority), never used for scale or position.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rifle_common import SHEET, SCRATCH, REVIEW, BLEND, GRIP  # noqa: E402

import gunlib  # noqa: E402
from gunlib.detail import DetailKit  # noqa: E402
import parts as PM  # noqa: E402

DETAIL_REVIEW = REVIEW / "detail"
DETAIL_SCRATCH = SCRATCH / "detail"


def _dir(yaw_deg, pitch_deg, side="right"):
    """Camera direction (target -> eye) for a side view turned by yaw (+ toward the muzzle) and pitch (+ = from
    above); side 'right' = from -Y, 'left' = from +Y."""
    y, p = math.radians(yaw_deg), math.radians(pitch_deg)
    s = -1.0 if side == "right" else 1.0
    return (math.sin(y) * math.cos(p), s * math.cos(y) * math.cos(p), math.sin(p))


MAG_OBJS = ["magazine", "magazine_floor_plate"]
BUTT_OBJS = ["buttstock", "butt_plate", "butt_screws", "stock_hardware", "sling_swivel_base", "sling_swivel_loop"]
RW = 21.8           # receiver wall outer face + rivet head (left / right)
# c1 draws the selector lever 13.25 deg front-down (parts/selector_trace.C1_TO_REST_DEG; between safe 0 and auto 16, in
# its 0-32 deg range): review renders at the c1 camera pose it there (the side and 3/4 views draw it up, at rest)
SEL_C1_POSE = {"objects": ["selector"], "pivot_M": [282.8, 0.0, -7.8], "axis_M": [0.0, 1.0, 0.0], "deg": 13.25}

PANELS = {
    "c1": {"box": (9, 629, 298, 991), "title": "c1 RECEIVER AND SELECTOR (RIGHT)", "model": "ortho", "poses": [SEL_C1_POSE],
           "from_dir": _dir(4.5, 5.5, "right"), "bound_deg": 4.0, "cut_sides": "left,right", "max_hole_px": 300,
           "landmarks": [
               ("selector boss centre", (87.0, 111.0), (282.8, -25.9, -7.8)),
               ("rivet (260, -4)", (43.0, 106.0), (260.0, -RW, -4.0)),
               ("rivet (250, -25)", (30.0, 146.0), (250.0, -RW, -25.0)),
               ("rivet (313, -25)", (143.0, 141.0), (313.0, -RW, -25.0)),
               ("trigger tip", (165.0, 200.0), (328.0, -3.0, -57.8)),
               ("guard front-bottom corner", (207.0, 207.0), (350.5, -5.0, -63.5)),
               ("mag catch pin", (226.0, 183.0), (362.0, -5.6, -50.0)),
               ("grip toe", (62.0, 340.0), (262.0, -14.0, -132.5))]},
    # c2 is labelled TOP LEFT but its handed features show the gun's RIGHT side from above and behind (the selector
    # lever lower left, the charging handle in the cover's lower edge, the handguard retainer lever on the rear sight
    # block): camera behind-right-above, muzzle toward the upper right
    "c2": {"box": (306, 629, 582, 991), "title": "c2 DUST COVER AND REAR SIGHT (TOP LEFT; shows the true right)",
           "model": "persp", "dist_mm": 450.0,
           "from_dir": (-0.55, -0.62, 0.56), "bound_deg": 20.0, "cut_sides": "left,right,bottom", "max_hole_px": 300,
           "thin_hole_px": 6.5, "close_px": 5,
           "landmarks": [
               ("notch plate top centre", (162.0, 70.0), (449.9, 0.0, 48.0)),
               ("leaf hinge, right end", (259.0, 65.0), (504.0, -21.75, 41.0)),
               ("rear sight block right front-bottom corner", (228.0, 140.0), (524.0, -21.75, 13.1)),
               ("right dimple centre", (133.0, 256.0), (397.0, -20.75, -17.0)),
               ("rivet right (413, -19)", (156.0, 246.0), (413.0, -RW, -19.0)),
               ("rivet right (379, -21)", (116.0, 273.0), (379.0, -RW, -21.0))]},
    "c3": {"box": (590, 629, 856, 991), "title": "c3 FRONT SIGHT AND MUZZLE (SIDE)", "model": "ortho",
           "from_dir": _dir(25.0, 10.0, "right"), "bound_deg": 4.0, "cut_sides": "left", "max_hole_px": 150, "close_px": 3,
           "landmarks": [
               ("ear top centre", (140.0, 37.0), (825.6, -10.7, 49.4)),
               ("lug bottom centre", (126.0, 222.0), (821.5, -5.0, -15.8)),
               ("brake bottom lip front", (245.0, 210.0), (880.0, -4.0, -9.0))]},
    "c4": {"box": (863, 629, 1025, 991), "title": "c4 MAGAZINE (LEFT)", "model": "ortho", "objects": MAG_OBJS,
           "from_dir": (0.0, 1.0, 0.0), "roll_deg": 0.0, "bound_deg": 30.0, "max_hole_px": 2000, "floor_rows": 16, "floor_dark": 80.0,
           "landmarks": [
               ("floor plate front corner (near)", (17.0, 287.0), (493.5, 14.5, -137.3)),
               ("floor plate rear corner (near)", (85.0, 343.0), (455.1, 14.5, -183.5)),
               ("body top front corner (near)", (42.0, 57.0), (424.6, 13.0, -12.0)),
               ("body top rear corner (near)", (127.0, 30.0), (369.7, 13.0, -12.0))]},
    "c5": {"box": (1032, 629, 1146, 991), "title": "c5 MAGAZINE (FRONT)", "model": "ortho", "objects": MAG_OBJS,
           "from_dir": (1.0, 0.0, 0.35), "bound_deg": 30.0, "max_hole_px": 2000, "floor_rows": 14, "floor_dark": 80.0,
           "landmarks": [
               ("floor plate rear corner (right side, image left)", (38.5, 340.0), (455.1, -14.5, -183.5)),
               ("floor plate rear corner (left side, image right)", (80.5, 340.0), (455.1, 14.5, -183.5)),
               ("body top front corner (right)", (40.0, 45.0), (424.6, -13.0, -12.0)),
               ("body top front corner (left)", (79.0, 45.0), (424.6, 13.0, -12.0))]},
    "c6": {"box": (1153, 629, 1379, 991), "title": "c6 PISTOL GRIP AND TRIGGER (LEFT)", "model": "ortho",
           "from_dir": (-0.05, 1.0, 0.05), "bound_deg": 10.0, "cut_sides": "top,left,right", "max_hole_px": 300, "thin_hole_px": 4.5, "close_px": 4, "floor_rows": 30,
           "landmarks": [
               ("rivet left (318, -26)", (45.0, 47.0), (318.0, RW, -26.0)),
               ("rivet left (254, -28)", (161.0, 53.0), (254.0, RW, -28.0)),
               ("rivet left (258, -7)", (159.0, 4.0), (258.0, RW, -7.0)),
               ("trigger tip", (34.0, 123.0), (328.0, 3.0, -57.8)),
               ("grip toe", (135.0, 293.0), (263.5, 12.0, -132.5)),
               ("grip heel", (212.0, 262.0), (226.6, 10.0, -117.2))]},
    "c7": {"box": (1387, 629, 1527, 991), "title": "c7 BUTT PLATE (END)", "model": "persp", "dist_mm": 350.0, "objects": BUTT_OBJS,
           "from_dir": (-1.0, 0.05, 0.0), "bound_deg": 15.0, "max_hole_px": 5000, "floor_rows": 4,
           "landmarks": [
               ("top screw centre", (70.5, 42.0), (0.2, 0.0, -10.0)),
               ("bottom screw centre", (70.5, 290.0), (7.4, 0.0, -87.5)),
               ("plate top end", (71.0, 21.0), (9.27, 0.0, -0.14)),
               ("plate bottom end", (71.0, 356.0), (14.25, 0.0, -109.91))]},
    "q34": {"box": (771, 322, 1528, 600), "title": "3/4 FRONT RIGHT", "fixed_camera": str(SCRATCH / "q34" / "camera.json"),
            "max_hole_px": 300},
}


# objects that frame a part's crop window when not all of its objects should (the cleaning rod runs 170 mm back)
WINDOW_OBJECTS = {"front_sight": ["front_sight_block", "front_sight_post"]}


def parts_cfg():
    out = {}
    for m in PM.MODULES:
        mod = PM.load(m)
        out[m] = {"objects": PM.objects_of(m), "panels": list(mod.CLOSEUPS)}
        if m in WINDOW_OBJECTS:
            out[m]["window_objects"] = WINDOW_OBJECTS[m]
    return out


REVIEW_BLEND = SCRATCH / "AR01_review.blend"      # the build + review-only bake sources (rifle_review_blend.py)


def make_review_blend():
    """(Re)write scratch/AR01_review.blend from the current Assets/Guns/AR01.blend."""
    import subprocess
    log = SCRATCH / "logs" / "review_blend.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run([gunlib.BLENDER, "-b", str(BLEND), "--factory-startup", "--python", str(HERE / "rifle_review_blend.py"),
                        "--", "--out", str(REVIEW_BLEND)], stdout=f, stderr=subprocess.STDOUT, check=False)
    txt = log.read_text(encoding="utf-8", errors="replace")
    if "Traceback" in txt or "[review_blend] DONE" not in txt:
        raise RuntimeError(f"review blend failed, see {log}")
    return REVIEW_BLEND


def render_blend():
    """The review blend when it is current (not older than the build), else the build itself."""
    if REVIEW_BLEND.exists() and REVIEW_BLEND.stat().st_mtime >= BLEND.stat().st_mtime:
        return REVIEW_BLEND
    return BLEND


def kit() -> DetailKit:
    return DetailKit({
        "sheet": str(SHEET), "panels": PANELS, "parts": parts_cfg(), "npz": str(SCRATCH / "form_tris.npz"),
        "blend": str(render_blend()), "offset_M": [float(v) for v in GRIP], "wood_slots": ["M_AR01_Furniture"],
        # spec finish butt_plate_lacquer_worn ('more bare than anywhere else'; sheet sample 78 vs the receiver's 60)
        "worn_steel_objects": ["butt_plate"],     # detail fix (user checklist 4): the screws are dark blued steel
        "review_dir": str(DETAIL_REVIEW), "scratch_dir": str(DETAIL_SCRATCH), "blender": gunlib.BLENDER,
        "ss": 3, "samples": 96, "env": 0.55, "light": 1.35})


_KIT = None


def _k():
    global _KIT
    if _KIT is None:
        _KIT = kit()
    return _KIT


# per-part entry points for the part builders
def solve_closeup_camera(part, force=False):
    return _k().solve_closeup_camera(part, force)


def trace_closeup(part):
    return _k().trace_closeup(part)


def render_part_crop(part, tag=""):
    return _k().render_part_crop(part, tag)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["solve", "trace", "render", "all", "panels"])
    ap.add_argument("--parts", default="")
    ap.add_argument("--tag", default="")
    ap.add_argument("--force", action="store_true", help="re-solve the part cameras")
    ap.add_argument("--force-panels", action="store_true", help="re-solve the panel cameras too")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    K = _k()
    parts = [p for p in a.parts.split(",") if p] or list(PM.MODULES)
    out = {"date": time.strftime("%Y-%m-%dT%H:%M:%S"), "parts": parts}
    t0 = time.time()
    if a.cmd in ("panels", "solve", "all"):
        keys = sorted({k for p in parts for k in K.cfg["parts"][p]["panels"]})
        out["panels"] = {}
        for k in keys:
            cam, rep = K.solve_panel(k, force=a.force_panels)
            out["panels"][k] = rep
            print("[detail] panel", k, json.dumps(rep)[:300])
    if a.cmd in ("solve", "all"):
        out["cameras"] = {}
        for p in parts:
            out["cameras"][p] = K.solve_closeup_camera(p, force=a.force)
            print("[detail] cameras", p, {k: v["part_camera"].get("iou_in_roi", v["part_camera"].get("iou_in_frame"))
                                          for k, v in out["cameras"][p].items()})
    if a.cmd in ("trace", "all"):
        out["traces"] = {p: K.trace_closeup(p) for p in parts}
    if a.cmd in ("render", "all"):
        K.cfg["blend"] = str(make_review_blend())          # with the review-only bake sources (grip checker field)
        out["crops"] = K.render_part_crop(parts, a.tag)
        for p, d in out["crops"].items():
            print("[detail] crops", p, {k: (v["silhouette_iou_window"], v["edges"]["f"]) for k, v in d.items()})
    out["seconds"] = round(time.time() - t0, 1)
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
    print("[detail] DONE", a.cmd, out["seconds"], "s")


if __name__ == "__main__":
    main()
