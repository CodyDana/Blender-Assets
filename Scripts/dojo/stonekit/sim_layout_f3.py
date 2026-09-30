"""Stone kit f3: the flat layout stage (STONE_BUILDING_STUDY 4.1 stage b, 6.4 staged round 1) outside Blender.

Lays the terrace wall's body stones exactly as build_wall.py f3 does (Scripts/stone/stone_layout.coursed_fitted on the
f3 course table, straight module lohi with teeth, the per-stone joint inset, the kit's corner rounding), draws them flat
next to the traced reference at one scale (the J1 view) and measures SG3 / SG4 / SG5 / SG6 / SG7 with
Scripts/stone/stone_measure.py, so the layout can be gated before any 3D stone is built.

Run: py -3 Scripts/dojo/stonekit/sim_layout_f3.py [--seeds 3,5,7] [--out <dir>] [--h 3] [--L 4]
Out: <out>/sim_layout_<L>m_H<h>_s<seed>.json (stone_layout/1), <out>/sim_flat.png, printed stats
"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "stone"))
import stone_layout as SL  # noqa: E402
import stone_measure as SM  # noqa: E402

# the f3 numbers (build_wall.py): kept in step by hand; build_wall imports the same stone_layout function
COPE_H = 0.34
BURY = 0.40
TOOTH = 0.18
JOINT = (0.0065, 0.0085)          # half joint per stone (sk_shared.lay_measured f3)
KEEP = (0.14, 0.22)               # Chaikin keep (sk_shared.pillow_stone_v2 f3), 2 rounds


def course_table(base=0.34, grow=0.030):
    pat = [1.0, 0.86, 1.14, 0.92, 1.08, 0.88, 1.12, 0.96]
    out, s, k = [COPE_H], COPE_H, 0
    while s < 7.0:
        s += (base + grow * s) * pat[k % len(pat)]
        out.append(round(s, 4))
        k += 1
    return out


def tooth(k):
    return TOOTH if k % 2 == 0 else -TOOTH


def lay(L, h, seed, courses, **kw):
    def lohi(k, sa, sb):
        o = tooth(k)
        return (o, o), (L + o, L + o)
    st = SL.coursed_fitted(courses, COPE_H, h + BURY, lohi, [0.0, float(L)], seed, **kw)
    rng = random.Random(seed * 31 + 7)
    out = []
    for s in st:
        poly = SL.convex_hull(s["poly"])
        inner = SL.inset_convex(poly, rng.uniform(*JOINT))
        if inner is None:
            continue
        keep = rng.uniform(*KEEP)
        rounded = SL.chaikin(inner, 2, keep)
        out.append({"poly": rounded, "kind": s["kind"], "raw": s["poly"]})
    return out, (st[0].get("junctions") if st else 0)


def flat_png(trace, layouts, out, L):
    from PIL import Image, ImageDraw
    ppm = trace["scale"]["px_per_m"]
    k = 230.0
    W = int(k * (L + 0.6)) + 60
    H = 900
    im = Image.new("RGB", (560 + W * len(layouts), H), (250, 250, 248))
    d = ImageDraw.Draw(im)
    x0, y0, _, _ = trace["crop_box_px"]
    for s in trace["stones"]:
        pts = [(20 + (x - x0) / ppm * k, 60 + (y - y0) / ppm * k) for x, y in s["poly"]]
        d.polygon(pts, outline=(30, 30, 30), fill=(205, 205, 198) if s["zone"] == "body" else (190, 205, 222))
    d.text((20, 20), "reference trace (32 px/m)", fill=(0, 0, 0))
    for i, (name, stones) in enumerate(layouts):
        ox = 560 + i * W
        d.rectangle((ox, 60, ox + int(k * L), 60 + int(k * COPE_H)), fill=(190, 205, 222), outline=(30, 30, 30))
        for s in stones:
            pts = [(ox + (a + 0.0) * k, 60 + (-z) * k) for a, z in s["poly"]]
            if max(p[1] for p in pts) > H - 5:
                continue
            d.polygon(pts, outline=(30, 30, 30), fill=(205, 205, 198))
        d.text((ox, 20), name, fill=(0, 0, 0))
    im.save(out)


def main(argv):
    def arg(n, dflt):
        return argv[argv.index(n) + 1] if n in argv else dflt
    seeds = [int(x) for x in arg("--seeds", "3,5,7").split(",")]
    h = int(arg("--h", "3"))
    L = int(arg("--L", "4"))
    outd = Path(arg("--out", str(ROOT / "WorkFiles" / "dojo" / "build" / "stonekit" / "renders" / "f3" / "layout")))
    outd.mkdir(parents=True, exist_ok=True)
    courses = course_table()
    trace = json.loads((ROOT / "References" / "Dojo" / "trace_terrace_lower.json").read_text(encoding="utf-8"))
    rs = SM.trace_shapes(trace)
    rb = rs["zones"]["body"]
    ref_join = SM.joint_stats([s["poly"] for s in trace["stones"] if s["zone"] == "body"], y_down=True,
                              tol=2.5 / trace["scale"]["px_per_m"], scale=1.0 / trace["scale"]["px_per_m"])
    print("REF  upright %.2f tall %.2f hw %s areaCV %s  %s" % (rb["upright_share"], rb["tall_share_hw_gt_1.2"],
                                                              rb["aspect_hw"], rb["area_cv"], ref_join))
    lays = []
    allst = {}
    for sd in seeds:
        st, nj = lay(L, h, sd, courses)
        rec = SL.layout_json(f"sim_Wall_{L}m_H{h}_s{sd}", {"body": {"stones": st, "z_top": -COPE_H, "z_bot": -(h + BURY)}})
        (outd / f"sim_layout_{L}m_H{h}_s{sd}.json").write_text(json.dumps(rec), encoding="utf-8")
        ls = SM.layout_shapes(rec)["zones"]["body"]
        js = SM.joint_stats([s["poly"] for s in st], y_down=False, tol=0.035)
        allst[sd] = {"shapes": ls, "joints": js, "y_junctions": nj}
        print("s%-3d n %3d upright %.2f tall %.2f long %.2f hw %s areaCV %s w %s h %s  Y %d  %s" % (
            sd, ls["n"], ls["upright_share"], ls["tall_share_hw_gt_1.2"], ls["long_share_w_gt_1.6h"],
            ls["aspect_hw"], ls["area_cv"], ls["width_m"]["median"], ls["height_m"]["median"], nj, js))
        lays.append((f"seed {sd}", st))
    flat_png(trace, lays, outd / "sim_flat.png", L)
    (outd / "sim_stats.json").write_text(json.dumps({"reference": {"shapes": rb, "joints": ref_join},
                                                     "ours": allst, "courses": courses}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
