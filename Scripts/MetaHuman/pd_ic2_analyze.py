"""pd_ic2_analyze.py -- offline analysis of the pd_ic2_verify.py captures + mesh dumps (no Unreal).

  py Scripts/MetaHuman/pd_ic2_analyze.py images        (Pillow)   -> ic2_image_metrics.json, sheets/*.png, raw RGB
  "<blender>/python.exe" Scripts/MetaHuman/pd_ic2_analyze.py numpy  (numpy) -> ic2_numeric.json (line metric via
      pd_r2_linemetric.py with its SCRATCH redirected to this checker's scratch folder; mesh displacement + neck seam)
Outputs under WorkFiles/MetaHuman/player_default/integrity_check_r2/.
"""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

ROOT = Path("C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/MetaHuman/player_default")
IC = ROOT / "integrity_check_r2"
CAP = IC / "captures"
FIX = ROOT / "captures"
SHEETS = IC / "sheets"
MESH = IC / "mesh"
RAW = Path(r"C:/Users/Cody/AppData/Local/Temp/claude/C--Users-Cody-Desktop-Blender-Projects/"
           r"196b90e6-f654-4528-8611-24c12e60d4b5/scratchpad/ic2_raw")
sys.path.insert(0, r"C:/Users/Cody/Desktop/Blender_Projects/Scripts/MetaHuman")

SUFFIX = {"studio": "", "ambient": "_ambient", "rimspec0": "_rimspec0", "norim": "_norim", "base": "_base",
          "eval": "_eval", "bounce": "_bounce", "headlight": "_headlight"}
LINE_SETS = {  # label -> {view: {rig: capture}}
    "PD fresh": {"JawClose": {r: f"ic2_pd_{r}_JawClose.png" for r in ("studio", "ambient", "eval", "bounce", "headlight")},
                 "Face_ThreeQuarter": {r: f"ic2_pd_{r}_Face_ThreeQuarter.png"
                                       for r in ("studio", "ambient", "eval", "bounce", "headlight")}},
    "FaceC fresh": {"JawClose": {r: f"ic2_facec_{r}_JawClose.png" for r in ("studio", "ambient", "headlight")},
                    "Face_ThreeQuarter": {r: f"ic2_facec_{r}_Face_ThreeQuarter.png" for r in ("studio", "ambient", "headlight")}},
    "Kelvin fresh": {"JawClose": {r: f"ic2_kelvin_{r}_JawClose.png" for r in ("studio", "ambient")},
                     "Face_ThreeQuarter": {r: f"ic2_kelvin_{r}_Face_ThreeQuarter.png" for r in ("studio", "ambient")}},
}


# ================================================================== images (Pillow) =================================
def images():
    from PIL import Image, ImageChops, ImageDraw, ImageStat
    SHEETS.mkdir(parents=True, exist_ok=True)
    M: dict = {}

    def load(p):
        return Image.open(p).convert("RGB")

    def diff_stats(a, b):
        d = ImageChops.difference(a, b)
        mean = sum(ImageStat.Stat(d).mean) / 3.0
        ch = d.split()
        mx = ImageChops.lighter(ImageChops.lighter(ch[0], ch[1]), ch[2])
        big = mx.point(lambda v: 255 if v > 24 else 0)
        return {"mean_abs_diff": round(mean, 3), "frac_px_maxdiff_gt24": round(ImageStat.Stat(big).mean[0] / 255.0, 5)}

    # 1) fresh vs the fixer's verify-2 captures (after_ = saved PD, before_ = FaceC dup)
    cmp = {}
    for p in sorted(CAP.glob("ic2_pd_*.png")):
        variant, view = p.stem[len("ic2_pd_"):].split("_", 1)
        if variant in SUFFIX:
            f = FIX / f"after_{view}{SUFFIX[variant]}.png"
            if f.exists():
                cmp[p.stem] = {"fixer": f.name, **diff_stats(load(p), load(f))}
    for p in sorted(CAP.glob("ic2_facec_*.png")):
        variant, view = p.stem[len("ic2_facec_"):].split("_", 1)
        if variant in SUFFIX:
            f = FIX / f"before_{view}{SUFFIX[variant]}.png"
            if f.exists():
                cmp[p.stem] = {"fixer": f.name, **diff_stats(load(p), load(f))}
    # control: PD vs FaceC for the same view (how big a real change is)
    for view in ("JawClose", "Face_ThreeQuarter", "JawRamus"):
        a, b = CAP / f"ic2_pd_studio_{view}.png", CAP / f"ic2_facec_studio_{view}.png"
        if a.exists() and b.exists():
            cmp[f"CONTROL_pd_vs_facec_studio_{view}"] = diff_stats(load(a), load(b))
    M["fresh_vs_fixer"] = cmp

    # 2) chroma see-through: green NOT connected to the border = background seen through the body
    def enclosed(im):
        w, h = im.size
        px = im.load()
        g = bytearray(w * h)
        for y in range(h):
            for x in range(w):
                r, gg, b = px[x, y]
                if gg > 90 and gg > r + 50 and gg > b + 50:
                    g[y * w + x] = 1
        seen = bytearray(w * h)
        q = deque()
        for x in range(w):
            for y in (0, h - 1):
                i = y * w + x
                if g[i] and not seen[i]:
                    seen[i] = 1
                    q.append(i)
        for y in range(h):
            for x in (0, w - 1):
                i = y * w + x
                if g[i] and not seen[i]:
                    seen[i] = 1
                    q.append(i)
        while q:
            i = q.popleft()
            x, y = i % w, i // w
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w and 0 <= ny < h:
                    j = ny * w + nx
                    if g[j] and not seen[j]:
                        seen[j] = 1
                        q.append(j)
        comps, total = [], 0
        done = bytearray(w * h)
        for i in range(w * h):
            if g[i] and not seen[i] and not done[i]:
                n, x0, y0, x1, y1 = 0, 10 ** 9, 10 ** 9, -1, -1
                q.append(i)
                done[i] = 1
                while q:
                    k = q.popleft()
                    n += 1
                    x, y = k % w, k // w
                    x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)
                    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                        if 0 <= nx < w and 0 <= ny < h:
                            j = ny * w + nx
                            if g[j] and not seen[j] and not done[j]:
                                done[j] = 1
                                q.append(j)
                total += n
                comps.append({"px": n, "bbox": [x0, y0, x1, y1]})
        comps.sort(key=lambda c: -c["px"])
        return {"green_px": sum(g), "enclosed_green_px": total, "components": comps[:6]}

    M["chroma_seethrough"] = {p.stem: enclosed(load(p)) for p in sorted(CAP.glob("ic2_*_chroma_*.png"))}

    # 3) near-black share (max RGB < 16): 3/4 jaw band + whole JawClose frame
    def near_black(im, box=None):
        if box:
            im = im.crop(box)
        ch = im.split()
        m = ImageChops.lighter(ImageChops.lighter(ch[0], ch[1]), ch[2]).point(lambda v: 255 if v < 16 else 0)
        return round(ImageStat.Stat(m).mean[0] / 255.0, 5)

    jaw = {}
    for p in sorted(CAP.glob("ic2_*_Face_ThreeQuarter.png")):
        jaw[p.stem] = {"near_black_jawband_330_820_900_1020": near_black(load(p), (330, 820, 900, 1020))}
    for p in sorted(CAP.glob("ic2_*_JawClose.png")):
        jaw[p.stem] = {"near_black_frame": near_black(load(p))}
    M["jaw_near_black"] = jaw

    # 4) ear glint: near-white px (min RGB >= 150), left 600 px of EarR
    def white_count(im, box=None):
        if box:
            im = im.crop(box)
        ch = im.split()
        m = ImageChops.darker(ImageChops.darker(ch[0], ch[1]), ch[2]).point(lambda v: 255 if v >= 150 else 0)
        return int(round(ImageStat.Stat(m).mean[0] / 255.0 * im.size[0] * im.size[1]))

    M["ear_white_px"] = {p.stem: white_count(load(p), (0, 0, 600, 1200)) for p in sorted(CAP.glob("ic2_*_EarR.png"))}

    # 5) hair crown luma of probes / captures (median in the crown box of Face_Front)
    def crown(im):
        vals = sorted(0.299 * r + 0.587 * g + 0.114 * b for x in range(400, 601, 25) for y in range(275, 336, 15)
                      for (r, g, b) in [im.getpixel((x, y))])
        return round(vals[len(vals) // 2], 1)

    M["crown_luma"] = {p.name: crown(load(p)) for p in sorted(CAP.glob("*Face_Front*.png"))
                       if "chroma" not in p.name and "base" not in p.name}
    M["crown_luma"]["FIXER after_Face_Front.png"] = crown(load(FIX / "after_Face_Front.png"))

    # 6) raw RGB for the numpy line metric
    import pd_r2_linemetric as LM
    LM.SCRATCH = RAW
    pngs = [str(CAP / f) for s in LINE_SETS.values() for v in s.values() for f in v.values() if (CAP / f).exists()]
    LM.convert(pngs)
    M["line_metric_inputs"] = len(pngs)

    # 7) sheets
    def sheet(name, items, scale=0.4, cols=None, box=None, title=""):
        ims = []
        for lab, p in items:
            if not Path(p).exists():
                continue
            im = load(Path(p))
            if box:
                im = im.crop(box)
            im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
            ims.append((lab, im))
        if not ims:
            return None
        cols = cols or len(ims)
        w = max(i.width for _, i in ims)
        h = max(i.height for _, i in ims) + 18
        rows = (len(ims) + cols - 1) // cols
        top = 22 if title else 0
        s = Image.new("RGB", (w * cols, h * rows + top), (25, 25, 25))
        d = ImageDraw.Draw(s)
        if title:
            d.text((4, 5), title, fill=(255, 255, 255))
        for k, (lab, im) in enumerate(ims):
            x, y = (k % cols) * w, top + (k // cols) * h
            s.paste(im, (x, y + 18))
            d.text((x + 3, y + 3), lab, fill=(255, 255, 120))
        out = SHEETS / name
        s.save(out)
        return str(out)

    def c(n):
        return CAP / f"{n}.png"

    S = {}
    S["fresh_vs_fixer"] = sheet("ic2_fresh_vs_fixer.png", [
        ("FRESH pd studio Face_Front", c("ic2_pd_studio_Face_Front")), ("FIXER after_Face_Front", FIX / "after_Face_Front.png"),
        ("FRESH pd studio Face_ThreeQuarter", c("ic2_pd_studio_Face_ThreeQuarter")),
        ("FIXER after_Face_ThreeQuarter", FIX / "after_Face_ThreeQuarter.png"),
        ("FRESH pd studio JawClose", c("ic2_pd_studio_JawClose")), ("FIXER after_JawClose", FIX / "after_JawClose.png"),
        ("FRESH facec studio JawClose", c("ic2_facec_studio_JawClose")), ("FIXER before_JawClose", FIX / "before_JawClose.png")],
        scale=0.3, cols=8, title="fresh integrity-check r2 captures vs the fixer's verify-2 captures (same rig/cameras)")
    S["jaw"] = sheet("ic2_jaw.png", [(n.replace("ic2_", ""), c(n)) for n in (
        "ic2_facec_studio_Face_ThreeQuarter", "ic2_pd_studio_Face_ThreeQuarter", "ic2_kelvin_studio_Face_ThreeQuarter",
        "ic2_facec_ambient_Face_ThreeQuarter", "ic2_pd_ambient_Face_ThreeQuarter", "ic2_kelvin_ambient_Face_ThreeQuarter",
        "ic2_facec_studio_JawClose", "ic2_pd_studio_JawClose", "ic2_kelvin_studio_JawClose",
        "ic2_facec_ambient_JawClose", "ic2_pd_ambient_JawClose", "ic2_kelvin_ambient_JawClose",
        "ic2_facec_headlight_JawClose", "ic2_pd_headlight_JawClose", "ic2_pd_base_JawClose")],
        scale=0.33, cols=3, title="jaw: FaceC dup (before) | MH_PlayerDefault | Epic Kelvin (grooms hidden); studio / ambient / headlight")
    S["jaw_zoom"] = sheet("ic2_jaw_zoom_34.png", [(n.replace("ic2_", ""), c(n)) for n in (
        "ic2_facec_studio_Face_ThreeQuarter", "ic2_pd_studio_Face_ThreeQuarter", "ic2_kelvin_studio_Face_ThreeQuarter",
        "ic2_facec_ambient_Face_ThreeQuarter", "ic2_pd_ambient_Face_ThreeQuarter", "ic2_kelvin_ambient_Face_ThreeQuarter")],
        scale=0.8, cols=3, box=(450, 520, 950, 1000), title="3/4 view zoom on the ramus (x450-950, y520-1000)")
    S["ramus"] = sheet("ic2_ramus.png", [(n.replace("ic2_", ""), c(n)) for n in (
        "ic2_facec_studio_JawRamus", "ic2_pd_studio_JawRamus", "ic2_kelvin_studio_JawRamus",
        "ic2_facec_ambient_JawRamus", "ic2_pd_ambient_JawRamus", "ic2_kelvin_ambient_JawRamus")],
        scale=0.3, cols=3, title="JawRamus camera: FaceC | PD | Kelvin")
    S["ear"] = sheet("ic2_ear.png", [(n.replace("ic2_", ""), c(n)) for n in (
        "ic2_pd_studio_EarR", "ic2_pd_rimspec0_EarR", "ic2_pd_norim_EarR", "ic2_pd_ambient_EarR", "ic2_pd_base_EarR",
        "ic2_pd_studio_EarRSide")], scale=0.33, cols=6, title="image-left ear: studio | rim spec 0 | no rim | ambient | base | side")
    S["shoulders"] = sheet("ic2_shoulders_chroma.png", [(n.replace("ic2_", ""), c(n)) for n in (
        "ic2_pd_chroma_Shoulders_Front", "ic2_pd_chroma_Shoulders_High", "ic2_pd_chroma_ShoulderL_TQ",
        "ic2_pd_chroma_ShoulderR_TQ", "ic2_pd_chroma_Shoulders_Back", "ic2_pd_chroma_Body_Front",
        "ic2_pd_chroma_Body_Back", "ic2_pd_studio_ShoulderL_TQ", "ic2_pd_studio_ShoulderR_TQ")],
        scale=0.3, cols=9, title="chroma (green = background): green inside the body would be see-through")
    S["identity"] = sheet("ic2_identity.png", [(n.replace("ic2_", ""), c(n)) for n in (
        "ic2_pd_studio_Face_Front", "ic2_pd_studio_Face_ThreeQuarter", "ic2_pd_studio_Face_Profile",
        "ic2_pd_ambient_Face_Front", "ic2_pd_studio_Eyes", "ic2_pd_studio_Head_Top", "ic2_pd_studio_Head_Back34",
        "ic2_pd_studio_Head_Back_Far", "ic2_pd_norim_Head_Back_Far", "ic2_pd_studio_Body_Front", "ic2_pd_studio_Body_Side",
        "ic2_pd_studio_Body_Back")], scale=0.3, cols=6, title="MH_PlayerDefault identity, fresh session")
    S["hair_probe"] = sheet("ic2_hair_probe.png", [(p.stem, p) for p in sorted(CAP.glob("ic2_probe_*.png"))],
                            scale=0.35, title="hair probe on the fresh load: first probe | hair drawn")
    M["sheets"] = S
    (IC / "ic2_image_metrics.json").write_text(json.dumps(M, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in M.items() if k != "chroma_seethrough"}, indent=1)[:9000])
    print(json.dumps({k: {"green": v["green_px"], "enclosed": v["enclosed_green_px"], "comps": v["components"][:2]}
                      for k, v in M["chroma_seethrough"].items()}, indent=1))


# ================================================================== numpy (Blender's Python) =========================
def numeric():
    import numpy as np
    import pd_r2_linemetric as LM
    LM.SCRATCH = RAW
    out: dict = {}
    # ---- line metric (same metric + ROIs as the fixer's r2_line_summary.json) ----
    pairs = []
    for s in LINE_SETS.values():
        for view, rigs in s.items():
            for f in rigs.values():
                if (RAW / (f + ".rgb")).exists():
                    pairs.append(f"{view}={CAP / f}")
                    if view == "JawClose" and "studio" in f or view == "JawClose" and "ambient" in f:
                        pairs.append(f"JawClose_ctl={CAP / f}")
    tmp = IC / "ic2_line_raw.json"
    # measure() keys results by file name; control ROIs would overwrite -> run twice
    LM.measure(str(tmp), [p for p in pairs if not p.startswith("JawClose_ctl")])
    raw = json.loads(tmp.read_text(encoding="utf-8"))
    LM.measure(str(IC / "ic2_line_raw_ctl.json"), [p for p in pairs if p.startswith("JawClose_ctl")])
    ctl = json.loads((IC / "ic2_line_raw_ctl.json").read_text(encoding="utf-8"))

    def seg(trace, lo, hi):
        d = [t[2] for t in trace if lo <= t[0] <= hi]
        return round(sum(d) / len(d), 1) if d else None

    lines = {}
    for label, views in LINE_SETS.items():
        for view, rigs in views.items():
            for rig, f in rigs.items():
                r = raw.get(f)
                if r is None:
                    continue
                row = {"all": r["depth_mean"]}
                if view == "JawClose":
                    row["upper_ramus_250_400"] = seg(r["trace"], 250, 400)
                    row["lower_ramus_420_530"] = seg(r["trace"], 420, 530)
                    if f in ctl:
                        row["cheek_control"] = ctl[f]["depth_mean"]
                else:
                    row["rows_740_805_below_ear"] = seg(r["trace"], 740, 805)
                    row["rows_810_890_jaw_angle"] = seg(r["trace"], 810, 890)
                lines.setdefault(label, {}).setdefault(view, {})[rig] = row
    fx = json.loads((ROOT / "r2_line_summary.json").read_text(encoding="utf-8"))["sets"]
    out["line_metric"] = lines
    out["line_metric_fixer"] = {k: {v: {r: {kk: vv for kk, vv in row.items() if kk != "file"} for r, row in rigs.items()}
                                    for v, rigs in views.items()} for k, views in fx.items()}

    # ---- mesh: PD face vs FaceC face / repro / PlayerBase; neck seam ----
    def obj(name):
        vs, fs = [], []
        with open(MESH / f"{name}.obj", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("v "):
                    vs.append([float(x) for x in line.split()[1:4]])
                elif line.startswith("f "):
                    fs.append([int(x) - 1 for x in line.split()[1:4]])
        return np.array(vs), np.array(fs, dtype=np.int64)

    pdv, pdf = obj("ic2_PD_Face")
    fcv, fcf = obj("ic2_FaceC_Face")
    rpv, rpf = obj("ic2_Repro_Face")
    pbv, pbf = obj("ic2_PlayerBase_Face")
    bdv, bdf = obj("ic2_PD_Body")
    m: dict = {"face_verts": len(pdv), "face_tris": len(pdf), "tris_identical_pd_facec": bool(np.array_equal(pdf, fcf))}
    # connected components of the Face mesh (head skin, eyes, lashes, teeth, ...): per-component displacement
    parent = np.arange(len(pdv))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for t in pdf:
        ra, rb, rc = find(t[0]), find(t[1]), find(t[2])
        parent[rb] = ra
        parent[find(rc)] = ra
    roots = np.array([find(i) for i in range(len(pdv))])
    dall = np.linalg.norm(pdv - fcv, axis=1)
    drep = np.linalg.norm(rpv - pdv, axis=1)
    comps = []
    for r in np.unique(roots):
        idx = np.where(roots == r)[0]
        comps.append({"first_index": int(idx.min()), "n_verts": int(len(idx)),
                      "centroid": [round(float(x), 2) for x in pdv[idx].mean(axis=0)],
                      "max_move_vs_facec_cm": round(float(dall[idx].max()), 4),
                      "max_diff_repro_vs_pd_cm": round(float(drep[idx].max()), 5)})
    comps.sort(key=lambda c: c["first_index"])
    m["components"] = comps
    head = np.where(roots == roots[0])[0]
    m["head_skin_component_n_verts"] = int(len(head))
    m["head_skin_is_first_block"] = bool(head.max() == len(head) - 1)
    m["repro_vs_pd_head_skin_max_cm"] = round(float(drep[head].max()), 6)
    m["pd_vs_facec_all_sections_max_cm"] = round(float(dall.max()), 4)
    # from here on: HEAD SKIN only (the component that contains vertex 0)
    pdv_all, fcv_all = pdv, fcv
    keep = np.zeros(len(pdv), bool)
    keep[head] = True
    remap = -np.ones(len(pdv), np.int64)
    remap[head] = np.arange(len(head))
    tri_keep = keep[pdf].all(axis=1)
    pdv, fcv, rpv, pbv = pdv[head], fcv[head], rpv[head], pbv[head]
    pdf = remap[pdf[tri_keep]]
    fcf = remap[fcf[keep[fcf].all(axis=1)]]
    d = np.linalg.norm(pdv - fcv, axis=1)
    i = int(d.argmax())
    m["pd_vs_facec"] = {"max_cm": round(float(d.max()), 4), "max_at": [round(float(x), 2) for x in pdv[i]],
                        "p99_cm": round(float(np.percentile(d, 99)), 4), "n_gt_1mm": int((d > 0.1).sum()),
                        "n_gt_0.1mm": int((d > 0.01).sum())}
    mv = d > 0.01
    if mv.any():
        m["pd_vs_facec"]["moved_gt_0.1mm_z_range"] = [round(float(pdv[mv, 2].min()), 2), round(float(pdv[mv, 2].max()), 2)]
        m["pd_vs_facec"]["moved_gt_0.1mm_x_range"] = [round(float(pdv[mv, 0].min()), 2), round(float(pdv[mv, 0].max()), 2)]
        m["pd_vs_facec"]["moved_gt_0.1mm_y_range"] = [round(float(pdv[mv, 1].min()), 2), round(float(pdv[mv, 1].max()), 2)]
    for zc in (146.0, 150.0, 155.0, 160.0):
        sel = pdv[:, 2] < zc
        m["pd_vs_facec"][f"max_below_z{int(zc)}_cm"] = round(float(d[sel].max()), 5) if sel.any() else None
    # symmetry of the change (left/right max)
    m["pd_vs_facec"]["max_x_pos_side"] = round(float(d[pdv[:, 0] > 0].max()), 4)
    m["pd_vs_facec"]["max_x_neg_side"] = round(float(d[pdv[:, 0] < 0].max()), 4)
    # signed lateral move at the jaw angle region: |x| change (inward = negative)
    box = (pdv[:, 2] > 158) & (pdv[:, 2] < 172) & (np.abs(pdv[:, 0]) > 4)
    if box.any():
        dx_in = (np.abs(pdv[box, 0]) - np.abs(fcv[box, 0]))
        m["pd_vs_facec"]["jaw_side_abs_x_change_cm_min_max"] = [round(float(dx_in.min()), 4), round(float(dx_in.max()), 4)]
    dr = np.linalg.norm(rpv - pdv, axis=1)
    m["repro_vs_pd"] = {"max_cm": round(float(dr.max()), 6)}
    dp = np.linalg.norm(pdv - pbv, axis=1)
    m["pd_vs_playerbase_face"] = {"max_cm": round(float(dp.max()), 3), "p50_cm": round(float(np.median(dp)), 3)}

    # neck seam: boundary loops of the face mesh; the lowest loop against the body mesh
    def boundary_loops(v, f):
        e = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
        u, cnt = np.unique(e, axis=0, return_counts=True)
        b = u[cnt == 1]
        adj: dict = {}
        for a, c in b:
            adj.setdefault(int(a), []).append(int(c))
            adj.setdefault(int(c), []).append(int(a))
        seen, loops = set(), []
        for s in adj:
            if s in seen:
                continue
            comp, st = [], [s]
            seen.add(s)
            while st:
                k = st.pop()
                comp.append(k)
                for n in adj[k]:
                    if n not in seen:
                        seen.add(n)
                        st.append(n)
            loops.append(comp)
        return loops

    def seam(v, f, body):
        loops = boundary_loops(v, f)
        loops.sort(key=lambda L: float(v[L, 2].mean()))
        L = loops[0]
        pts = v[L]
        dist = np.array([np.linalg.norm(body - p, axis=1).min() for p in pts])
        return {"n_loops": len(loops), "seam_loop_verts": len(L), "seam_z_range": [round(float(pts[:, 2].min()), 2),
                                                                                   round(float(pts[:, 2].max()), 2)],
                "gap_to_body_max_cm": round(float(dist.max()), 5), "gap_mean_cm": round(float(dist.mean()), 5)}, L

    s_pd, Lpd = seam(pdv, pdf, bdv)
    s_fc, Lfc = seam(fcv, fcf, bdv)
    m["neck_seam_pd"] = s_pd
    m["neck_seam_facec_vs_same_body"] = s_fc
    m["neck_seam_loop_same_indices"] = sorted(Lpd) == sorted(Lfc)
    m["neck_seam_loop_moved_max_cm"] = round(float(d[Lpd].max()), 6)
    out["mesh"] = m
    (IC / "ic2_numeric.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1)[:12000])


if __name__ == "__main__":
    {"images": images, "numpy": numeric}[sys.argv[1]]()
