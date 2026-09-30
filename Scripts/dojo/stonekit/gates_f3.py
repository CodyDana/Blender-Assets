"""Stone kit f3 (gates_f2.py on the f3 renders and layouts, plus SG5 / SG6 from stone_measure.joint_stats). From f2
(round 2, after STONE_BUILDING_STUDY.md): the study's measured gates (6.2) for the terrace wall, with
the shared measurer Scripts/stone/stone_measure.py (numpy + PIL; no bpy).

  layout   SG3 (area CV, cap / body height), SG4 (aspect, upright share), SG7 (grading), SG9 (crown / corner-radius
           CV): the traced reference References/Dojo/trace_terrace_lower.json against our flat layout records
           WorkFiles/dojo/build/stonekit/wall/layout_Wall_4m_*.json (sk_shared.lay_measured). Sizes in metres are
           reported, not gated: the trace's scale is 32 +- 6 px/m (study 6.1: +-20 %), so the scale-free ratios gate.
  image    SG8 (dark-joint fraction), SG10 (p90/p50), SG11 (hue / sat / R/B), SG12 (moss share): the reference close
           crop against renders/f2/gate_stone_faces.png (the daylight test rig, render_f2.py --what gate)
  tech     SG17 from the build reports (qa hard fails, verts/tris, texel) and the fresh-process FBX verify
Also draws gate_layout_flat.png (the traced reference outlines | our Wall_4m_H3 outlines, flat, the J1 view) and
GATES_f2.png (the table).
Run: py -3 Scripts/dojo/stonekit/gates_f2.py
Out: WorkFiles/dojo/build/stonekit/f2_gates.json, renders/f2/gate_layout_flat.png, renders/f2/GATES_f2.png
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Scripts" / "stone"))
import stone_measure as SM  # noqa: E402

SK = ROOT / "WorkFiles" / "dojo" / "build" / "stonekit"
F2 = SK / "renders" / "f3"
TRACE = ROOT / "References" / "Dojo" / "trace_terrace_lower.json"
REF_CLOSE = F2 / "refcrops" / "ref_close_stone_faces.png"
OUR_CLOSE = F2 / "gate_stone_faces.png"
OUR_BOX = (0, 0, 1170, 910)            # the close gate view is all wall face (framed to the reference crop)


def font(sz):
    for f in ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            continue
    return ImageFont.load_default()


def flat_sheet(trace, layout, out):
    """J1-style flat line drawings at one scale (m): the traced reference stones | our layout's stones."""
    ppm = trace["scale"]["px_per_m"]
    k = 260.0                            # px per m on the sheet
    H = 760
    im = Image.new("RGB", (2 * 1100 + 60, H + 60), (250, 250, 248))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = trace["crop_box_px"]
    for s in trace["stones"]:
        col = (40, 120, 200) if s["zone"] == "cap" else (40, 40, 40)
        pts = [(20 + (x - x0) / ppm * k, 50 + (y - y0) / ppm * k) for x, y in s["poly"]]
        d.polygon(pts, outline=col, fill=(215, 215, 210) if s["zone"] == "body" else (200, 215, 230))
    d.text((20, 12), "reference trace (terrace wall, dojo_landscape_ref.png, 32 px/m)", fill=(0, 0, 0), font=font(22))
    ox = 1120
    for zn, zd in layout["zones"].items():
        for s in zd["stones"]:
            pts = [(ox + (a - 0.2) * k, 50 + (-z) * k) for a, z in s["poly"]]
            if max(p[1] for p in pts) > H + 40 or max(p[0] for p in pts) > ox + 1100:
                continue
            d.polygon(pts, outline=(40, 120, 200) if zn == "cap" else (40, 40, 40),
                      fill=(200, 215, 230) if zn == "cap" else (215, 215, 210))
    d.text((ox, 12), "ours: Wall_4m_H3 layout (face coordinates), same scale", fill=(0, 0, 0), font=font(22))
    im.save(out)


def table(G, out):
    rows = []
    for grp, gs in G.items():
        for k, v in gs.items():
            rows.append((grp, k, "PASS" if v.get("pass") else ("n/a" if v.get("pass") is None else "FAIL"),
                         json.dumps({kk: vv for kk, vv in v.items() if kk != "pass"})[:150]))
    im = Image.new("RGB", (1900, 60 + 34 * len(rows)), (250, 250, 248))
    d = ImageDraw.Draw(im)
    d.text((14, 12), "Dojo stone kit f3: STONE_BUILDING_STUDY 6.2 gates (measured, stone_measure.py)",
           fill=(0, 0, 0), font=font(24))
    for i, (grp, k, st, det) in enumerate(rows):
        y = 56 + 34 * i
        d.text((14, y), grp, fill=(60, 60, 60), font=font(18))
        d.text((170, y), k, fill=(0, 0, 0), font=font(18))
        d.text((520, y), st, fill=(0, 140, 0) if st == "PASS" else ((180, 0, 0) if st == "FAIL" else (90, 90, 90)),
               font=font(18))
        d.text((600, y), det, fill=(50, 50, 50), font=font(15))
    im.save(out)


def main():
    trace = json.loads(TRACE.read_text(encoding="utf-8"))
    rs = SM.trace_shapes(trace)
    ref_j = SM.joint_stats([s_["poly"] for s_ in trace["stones"] if s_["zone"] == "body"], y_down=True,
                           tol=2.5 / trace["scale"]["px_per_m"], scale=1.0 / trace["scale"]["px_per_m"], bed_tol=0.2)
    out = {"trace": str(TRACE.relative_to(ROOT)), "reference_shapes": rs, "layouts": {}, "gates": {}}
    for f in sorted((SK / "wall").glob("layout_Wall_*.json")):
        ls = SM.layout_shapes(json.loads(f.read_text(encoding="utf-8")))
        out["layouts"][f.stem] = ls
        gk = "layout_" + f.stem.replace("layout_", "")
        out["gates"][gk] = SM.gates(ref_shapes=rs, our_shapes=ls, zone="body", which=["SG3", "SG4", "SG7", "SG9"])
        # f3: SG5 (coursing) / SG6 (interlock) on the built outlines vs the trace, bed tolerance 0.2 x the median
        # height (the trace's +-1.5 px on ~9 px stones: the study's tolerance floor)
        body = [s_["poly"] for s_ in json.loads(f.read_text(encoding="utf-8"))["zones"]["body"]["stones"]]
        ours_j = SM.joint_stats(body, y_down=False, tol=0.035, bed_tol=0.2)
        out["layouts"][f.stem]["joints"] = ours_j
        bc_r, bc_o = ref_j["bed_continuity"], ours_j["bed_continuity"]
        out["gates"][gk]["SG5_bed_continuity"] = {"pass": bc_o <= bc_r * 1.15, "ours": bc_o, "ref": bc_r,
                                                  "rule": "share of side-by-side pairs on one bed <= ref + 15 %"}
        out["gates"][gk]["SG6_four_way_per_m2"] = {"pass": None, "ours": ours_j["four_way_per_m2"],
                                                   "ref": ref_j["four_way_per_m2"],
                                                   "note": "reported: the trace's 4-way count is not reliable at "
                                                           "~9 px stones (bounding-box heads)"}
    ri = SM.measure_image(REF_CLOSE)
    oi = SM.measure_image(OUR_CLOSE, OUR_BOX) if OUR_CLOSE.exists() else None
    out["reference_image"], out["ours_image"] = ri, oi
    if oi:
        out["gates"]["image_daylight"] = SM.gates(ref_img=ri, our_img=oi, which=["SG8", "SG10", "SG11", "SG12"])
    # SG17 technical
    tech = {}
    qa = {}
    for tr in ("wall", "stairs"):
        p = SK / tr / "qa_report.json"
        if p.exists():
            qa.update(json.loads(p.read_text(encoding="utf-8")))
    hard = sum(len(v.get("hard_fails", [])) for v in qa.values())
    tech["SG17_qa_hard_fails"] = {"pass": hard == 0, "pieces": len(qa), "hard_fails": hard}
    ver = SK / "fbx_verify_f3.json"
    if ver.exists():
        v = json.loads(ver.read_text(encoding="utf-8"))
        tech["SG17_fbx_reimport"] = {"pass": not v.get("not_ok"), "files": v.get("files"), "not_ok": v.get("not_ok")}
    m = SK / "f3_measure.json"
    if m.exists():
        mm = json.loads(m.read_text(encoding="utf-8"))
        if "verts_per_tri" in mm:
            vt = mm["verts_per_tri"]
            tech["SG17_verts_per_tri"] = {"pass": vt["max"] <= 1.0, **vt, "target": "<= 1.0 (study 4.14, proposed)"}
        if "walkability" in mm:
            tech["SG17_walkability"] = mm["walkability"]
    out["gates"]["technical"] = tech
    (SK / "f3_gates.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    lay = SK / "wall" / "layout_Wall_4m_H3.json"
    if lay.exists():
        flat_sheet(trace, json.loads(lay.read_text(encoding="utf-8")), F2 / "gate_layout_flat.png")
    table(out["gates"], F2 / "GATES_f3.png")
    for g, gs in out["gates"].items():
        for k, v in gs.items():
            print(g, k, v.get("pass"))


if __name__ == "__main__":
    main()
