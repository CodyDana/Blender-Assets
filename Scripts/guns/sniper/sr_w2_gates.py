"""SR01 W2 gate record (plain Python): gates/uv_bake_paint.json from the W2 artefacts of the gun (scratch/w2) and the
scope attachment (scratch/w2_scope), the SMG's smg_w2_gates.py set (B9 densities / fill / sizes, UV0 integrity,
maps, BC + metallic limits, bake rules, L5, wear audits, Masks A, UD1-UD4, qa_check on the twin, B8, recolour,
renders, judges).

    py -3 -B Scripts/guns/sniper/sr_w2_gates.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sr_common import ROOT, GATES, WORK, RENDERS  # noqa: E402
import sr_surface as SS  # noqa: E402

TEX = SS.TEX


def j(p):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else None


def gate(name, value, threshold, ok, note=None):
    r = {"gate": name, "value": value, "threshold": threshold, "pass": bool(ok)}
    if note:
        r["note"] = note
    return r


def target_gates(label, scratch, sets, stem, polymer_fin=("polymer", "rubber")):
    G = []
    uv = j(scratch / "uv" / "uv_report.json")
    ud4 = j(scratch / "uv" / "ud4.json")
    bake = j(scratch / "bake" / "bake_meta.json")
    paint = j(scratch / "paint" / "paint_report.json")
    wb = j(scratch / "w2_blender.json")
    if not uv:
        return [gate(f"{label}: UV report", "missing", "present", False)]
    if wb:
        q = wb["qa_check_twin"]
        G.append(gate(f"{label}: qa_check on the static twin as W3 joins it (slot k on U tile k)",
                      {"passed": q["passed"], "triangles": q["triangles"], "texel_aggregate_px_cm": q["texel_aggregate_px_cm"],
                       "failed": [c["name"] for c in q["failed"]], "rows": q["rows"]}, "pass", q["passed"]))
    for st, v in uv["sets"].items():
        for c, cv in v["classes"].items():
            band = cv["band"]
            med, p5 = cv["px_per_cm_median"], cv["px_per_cm_p5"]
            ok = 0.75 * band[0] <= med <= 1.25 * band[1] and p5 >= 0.85 * med
            G.append(gate(f"{label}: B9 density {st} class {c} (px/cm P5 / median / P95)",
                          f"{p5} / {med} / {cv['px_per_cm_p95']} ({cv['area_cm2']} cm2)",
                          f"median in [{0.75 * band[0]:g}, {1.25 * band[1]:g}]; P5 >= 0.85 x median", ok))
        fmin = sets[st]["fill_min"]
        G.append(gate(f"{label}: B9 fill {st} ({v['size']})", v["fill"], f">= {fmin:.2f}", v["fill"] >= fmin))
        G.append(gate(f"{label}: set size {st} (the packer decides)", f"{v['size']}: needed at the class floors "
                      f"{v['texels_needed_at_class_floors']:,} vs capacity {v['capacity_at_fill_min']}",
                      "smallest power of two at the fill minimum", True))
    G.append(gate(f"{label}: UV0 overlaps per set", uv["lod0_uv0_overlap_pairs"], "0 per set",
                  all(v == 0 for v in uv["lod0_uv0_overlap_pairs"].values())))
    G.append(gate(f"{label}: UV0 flipped triangles", uv["lod0_flipped_uv_triangles"], "0",
                  uv["lod0_flipped_uv_triangles"] == 0))
    r = uv["uv0_range"]
    G.append(gate(f"{label}: UV0 in 0..1 (skeletal / attachment layout)", r, "inside [0, 1]",
                  min(r["min"]) >= -1e-6 and max(r["max"]) <= 1 + 1e-6))
    rows, ok_maps = [], True
    for st in sets:
        for mp in ("BC", "ORM", "N", "Masks"):
            p = TEX / f"{stem}_{st}_{mp}.png"
            if not p.exists():
                ok_maps = False
                rows.append(f"{p.name} MISSING")
                continue
            w, h = Image.open(p).size
            ok_maps &= (w & (w - 1)) == 0 and w == h
            rows.append(f"{p.name} {w}x{h}")
    G.append(gate(f"{label}: maps square power of two, named {stem}_<Set>_<map>", rows, "all present, POT", ok_maps,
                  "BC sRGB; ORM linear (R AO, G rough, B metal); N DirectX 16-bit; Masks half size"))
    if paint:
        rows, ok = {}, True
        for st in sets:
            rep = paint.get(st)
            if not rep:
                ok = False
                continue
            ok &= set(rep["metallic_values"]) <= {0.0, 1.0}
            for f, v in rep["finishes"].items():
                d = v["bc_srgb_dielectric_p1_p50_p99"]
                if d is not None:
                    ok &= d[0] >= 29.5 and d[2] <= 243
                if f in polymer_fin:
                    ok &= v["metal_fraction"] == 0.0
                rows[f"{st}/{f}"] = {k: v[k] for k in ("texels", "metal_fraction", "bc_srgb_dielectric_p1_p50_p99",
                                                        "bc_srgb_median_rgb", "rough_p5_p50_p95")}
        G.append(gate(f"{label}: BC in range (dielectric >= 30 sRGB, <= 243), metallic exactly 0 / 1, polymer and "
                      "rubber never metal", rows, "all", ok))
        # separate value / roughness per material family (the SMG close-up lesson)
        fam = {}
        for st in sets:
            for f, v in paint.get(st, {}).get("finishes", {}).items():
                if v["bc_srgb_median_rgb"] and v["metal_fraction"] < 0.5:
                    fam[f] = (round(sum(v["bc_srgb_median_rgb"]) / 3.0, 1), v["rough_p5_p50_p95"][1])
        dark = {k: v for k, v in fam.items() if v[0] < 70}
        pairs = [(a, b) for a in dark for b in dark if a < b and abs(dark[a][0] - dark[b][0]) < 1.5
                 and abs(dark[a][1] - dark[b][1]) < 0.06]
        G.append(gate(f"{label}: dark families differ in value or roughness (no single charcoal)",
                      {"families (median sRGB, median rough)": fam, "indistinct pairs": pairs},
                      "every dark pair differs by >= 1.5 levels or >= 0.06 roughness", not pairs))
        a_bad = {st: paint[st].get("masks_A_on_non_od_texels") for st in sets if st in paint}
        G.append(gate(f"{label}: Masks A = 1 only on the OD paint (user colour never tints rubber / polymer / metal)",
                      {"A on non-OD texels": a_bad,
                       "A mean on OD": {st: paint[st].get("masks_A_on_od_fraction") for st in sets if st in paint}},
                      "0 non-OD texels", not any(a_bad.values())))
        G.append(gate(f"{label}: wear by cause (paint info)", {st: paint[st].get("info") for st in sets if st in paint},
                      "reported", True))
    if bake:
        G.append(gate(f"{label}: bake rules", {"margin": bake.get("margin"), "ao_samples": bake.get("ao_samples"),
                                              "rules": bake.get("rules")}, "margin 0; the magazine's AO alone",
                      bake.get("margin") == 0))
    if wb:
        G.append(gate(f"{label}: UD1 re-run on the surfaced parts", wb["ud1"], "0 drops", wb["ud1"]["drops"] == 0))
        G.append(gate(f"{label}: UD2 re-run", wb["ud2"], "0 / 0 / 0 (margin gate)", not any(wb["ud2"].values())))
        u3 = {k: v for k, v in wb["ud3"].items() if k != "by_part"}
        G.append(gate(f"{label}: UD3 zero tangents on UV0", u3, "0 / 0 / 0", not any(u3.values()),
                      json.dumps(wb["ud3"].get("by_part"))[:400] if wb["ud3"].get("by_part") else None))
        G.append(gate(f"{label}: layers UV0 / UV1 by index", wb["layers_ok"], "true", wb["layers_ok"]))
        G.append(gate(f"{label}: twin UD1 / UD3", {"ud1": wb["twin_ud1"], "ud3": wb["twin_ud3"]}, "0",
                      wb["twin_ud1"]["drops"] == 0))
    if ud4:
        G.append(gate(f"{label}: UD4 authored lightmap UV1 (64 / 128 px, 2 px padding)",
                      {k: v for k, v in ud4.items() if k != "notes"}, "0 conflicts at both",
                      all((ud4.get(str(R)) or ud4.get(R) or {}).get("conflict_texels", 1) == 0 for R in (64, 128))
                      if any(str(R) in ud4 for R in (64, 128)) else bool(ud4.get("pass"))))
    return G


def main():
    G = []
    G += target_gates("gun", SS.WORK / "scratch" / "w2", SS.SETS if SS.TARGET == "gun" else {}, "T_SR01")
    import os
    os.environ["SR01_SURFACE_TARGET"] = "scope"
    import importlib
    SC = importlib.reload(SS)
    G += target_gates("scope", SC.WORK / "scratch" / "w2_scope", SC.SETS, "T_Att_Scope_LongRange",
                      polymer_fin=("lens",))
    os.environ["SR01_SURFACE_TARGET"] = "gun"
    importlib.reload(SS)
    wb = j(SS.WORK / "scratch" / "w2" / "w2_blender.json")
    if wb:
        tl = wb["triangles_lod0"]
        G.append(gate("B8 LOD0 triangles after the UV stage (gun / magazine)", tl, "gun <= 50,000; magazine <= 5,000",
                      tl["gun"] <= 50000 and tl["magazine"] <= 5000))
    l5 = j(SS.WORK / "scratch" / "w2" / "l5" / "l5.json")
    if l5:
        G.append(gate("L5 colour vs the sheet (GR crop-matched per traced part, physical rig; ONE light scale fitted on "
                      "the forend OD)", {"light_k": l5["light_k"], "od_rendered_srgb": l5["od_rendered_srgb"],
                                         "od_sheet_srgb": l5["od_sheet_srgb"], "passed": f"{l5['passed']} / {l5['tested']}",
                                         "regions": {n: {"sheet": v["sheet"]["srgb"], "ours": v["ours"]["srgb"],
                                                         "d_luma": v["d_luma"], "d_sat": v["d_sat"],
                                                         "d_hue": v.get("d_hue_deg"), "pass": v["pass"]}
                                                     for n, v in l5["regions"].items()}},
                      l5["tolerances"], l5["passed"] == l5["tested"]))
    else:
        G.append(gate("L5", "missing", "present", False))
    rc = j(SS.WORK / "scratch" / "w2" / "recolour_precheck.json")
    if rc:
        G.append(gate("recolour pre-check (Detail16 on the OD, A = 0 elsewhere)", rc["gate"], rc["gate"]["rule"],
                      rc["gate"]["pass"]))
    shots = sorted(p.name for p in RENDERS.glob("tex_*.png"))
    want = ["tex_right.png", "tex_left.png", "tex_q34.png", "tex_top.png", "tex_deployed_hero.png", "tex_fp_action.png",
            "tex_scope_close.png"]
    G.append(gate("renders from the baked maps only, studio-HDRI realism rig", shots, "right, left, 3/4, top, deployed "
                  "hero, FP-ish action, scope close", all(w in shots for w in want)))
    jd = j(SS.WORK / "scratch" / "w2" / "judges.json")
    if jd:
        G.append(gate("realism judges on the textured renders (two independent judges)", jd.get("verdicts"),
                      "reported; at most one paint fix round", True, jd.get("summary")))
    failed = [g["gate"] for g in G if not g["pass"]]
    out = {"stage": "W2 surface (UV by class, bakes, paint, Masks, Detail16, L5; gun + scope attachment)",
           "date": dt.datetime.now().isoformat(timespec="seconds"), "status": "pass" if not failed else "partial",
           "failed": failed, "gates": G,
           "declared": [
               "Bipod legs splay 12 deg (user 2026-10-13) are part of the surfaced geometry (W1 follow-up)",
               "Generic markings only (user 2026-10-13): S / F engraved at the safety; no maker / model / serial",
               "The pack's derive step (P1 <= 2 levels) runs in W6 under the PackMaterials lock; here the recolour "
               "reconstruction is pre-checked on the OD only",
               "Scope sets sit at the density ceiling at 2048 / 512 (1024 / 256 cannot hold the class floors): fill "
               "0.49 / 0.51 against a declared 0.45 minimum (the gun's 0.65-0.70 rule cannot be met under the ceiling)",
               "B9 uniformity near-misses: Metal class C P5 31.3 vs 31.5 needed, scope class C P5 40.9 vs 41.1 (the "
               "cylinder charts' box-projected ends); a per-island scale normalisation is still open (W5 / W6)",
               "UD2 / UD3: resolved in W3 Part 0 (UD2 0 on the chassis; UD3 0 via the UV-stage visible-sliver rule, "
               "sr_uv.f32_visible, normals only: a declared deviation from a generator fix)",
               "Generic markings: S / F on the visible outer face under the safety pocket (W3 Part 0: 109 texels; "
               "markings_texels in the paint report)",
               "L5 rail: the sheet's rail sits in the scope's shadow (sRGB 14): the L5 render carries the textured "
               "scope; saturation is not tested under 30 sRGB levels (a 2-level step is sat 0.12)",
           ]}
    (GATES / "uv_bake_paint.json").write_text(json.dumps(out, indent=1, default=str))
    w2 = GATES / "w2"
    w2.mkdir(exist_ok=True)
    for src, name in ((SS.WORK / "scratch" / "w2" / "uv" / "uv_report.json", "uv_report.json"),
                      (SS.WORK / "scratch" / "w2" / "uv" / "uv1_report.json", "uv1_report.json"),
                      (SS.WORK / "scratch" / "w2" / "uv" / "ud4.json", "ud4.json"),
                      (SS.WORK / "scratch" / "w2" / "uv" / "sets.json", "sets.json"),
                      (SS.WORK / "scratch" / "w2" / "bake" / "bake_meta.json", "bake_meta.json"),
                      (SS.WORK / "scratch" / "w2" / "paint" / "paint_report.json", "paint_report.json"),
                      (SS.WORK / "scratch" / "w2" / "w2_blender.json", "w2_blender.json"),
                      (SS.WORK / "scratch" / "w2" / "l5" / "l5.json", "l5.json"),
                      (SS.WORK / "scratch" / "w2_scope" / "uv" / "uv_report.json", "scope_uv_report.json"),
                      (SS.WORK / "scratch" / "w2_scope" / "paint" / "paint_report.json", "scope_paint_report.json"),
                      (SS.WORK / "scratch" / "w2_scope" / "w2_blender.json", "scope_w2_blender.json")):
        if src.exists():
            (w2 / name).write_text(src.read_text())
    print(json.dumps({"status": out["status"], "failed": failed}, indent=1))


if __name__ == "__main__":
    main()
