"""AR-01 stage 7 'apply fixes': the stage record (plain Python). Collects the re-run stage 2-6 gate files, the review
renders' record and the fix-round rows into WorkFiles/guns/rifle/gates/review_fixes.json.

    py -3 -B Scripts/guns/rifle/rifle_fix_gates.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
W = ROOT / "WorkFiles" / "guns" / "rifle"
G = W / "gates"
EXP = ROOT / "Exports" / "Guns" / "AR01"


def j(p):
    return json.loads(Path(p).read_text())


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def find(gates, key):
    return next((g for g in gates if key in g["name"]), None)


def row(name, value, threshold, ok, src):
    return {"name": name, "value": value, "threshold": threshold, "pass": bool(ok), "source": src}


def main():
    stages = {k: j(G / f"{k}.json") for k in ("form", "uv_bake_paint", "game", "rig_export", "mag")}
    rows = []
    for k, d in stages.items():
        rows.append(row(f"stage file {k}.json", {"status": d.get("status"), "gates": len(d["gates"]),
                                                 "failed": d.get("failed")}, "status pass, failed []",
                        d.get("status") == "pass" and not d.get("failed"), f"gates/{k}.json"))
    f = stages["form"]["gates"]
    for key in ("L2 side IoU", "L2 top IoU", "L2 3/4 documented exception", "L2 per part", "B3 bolt sweep",
                "B3 mag_release sweep", "B3 selector sweep", "B4 sight picture", "G5 static intersections",
                "B8 LOD0 triangles, rifle", "MAGFIT F2", "MAGFIT F3", "MAGFIT F4"):
        g = find(f, key)
        if g:
            rows.append(row(g["name"], g["value"], g["threshold"], g["pass"], "gates/form.json"))
    u = stages["uv_bake_paint"]["gates"]
    for key in ("fill Metal", "fill Mag", "fill Furniture", "density Metal class A", "density Metal class B",
                "UV0 mirrored", "L5 colour", "realism-tex: no blown wear", "realism-tex: textured ADS",
                "stage-7 wear", "stage-7 finish"):
        for g in u:
            if key in g["name"]:
                rows.append(row(g["name"], g["value"], g["threshold"], g["pass"], "gates/uv_bake_paint.json"))
    for key in ("LOD1 rifle tris", "LOD2 rifle tris", "LOD-pop", "B3 at LOD1", "G5 at LOD1", "qa_check (twin"):
        for g in stages["game"]["gates"]:
            if key in g["name"]:
                rows.append(row(g["name"], g["value"], g["threshold"], g["pass"], "gates/game.json"))
    for key in ("clips read back", "bounds hold", "B4 sockets", "B1 skeleton"):
        g = find(stages["rig_export"]["gates"], key)
        if g:
            rows.append(row(g["name"], g["value"], g["threshold"], g["pass"], "gates/rig_export.json"))
    for g in stages["mag"]["gates"]:
        if g["name"][:2] in ("M1", "M2", "M3", "M4", "M5", "M6", "M7") or "Twin magazine" in g["name"]:
            rows.append(row(g["name"], g["value"], g["threshold"], g["pass"], "gates/mag.json"))
    # clips: the selector held at AUTO in the moving-bolt clips; ShellEject at the rear stop
    sk = j(EXP / "SK_AR01.skeletal.json")
    ne = {(n["clip"], n["name"]): n["frame"] for n in sk["notifies"]}
    rows.append(row("ShellEject notify at the carrier's rear stop (A_AR01_Fire)", ne.get(("A_AR01_Fire", "ShellEject")),
                    "frame 3 (bolt = full travel)", ne.get(("A_AR01_Fire", "ShellEject")) == 3, "SK_AR01.skeletal.json"))
    rig = j(W / "scratch" / "rig" / "rig_report.json")
    held = {}
    for c in ("A_AR01_Fire", "A_AR01_Charge", "A_AR01_Reload", "A_AR01_ReloadEmpty"):
        vals = rig["clips"][c]["values"]
        held[c] = sorted({round(v.get("selector", 0.0), 3) for v in vals.values()})
    rows.append(row("selector held at AUTO through the moving-bolt clips", held, "[16.0] in every clip",
                    all(v == [16.0] for v in held.values()), "scratch/rig/rig_report.json"))
    # review renders made from the CURRENT exported bytes
    rx = j(G / "review_export.json")
    cur = {str(p.relative_to(ROOT)).replace("\\", "/"): sha(p)
           for p in sorted(EXP.glob("*.fbx")) + sorted((EXP / "Textures").glob("*.png"))}
    recorded = rx.get("inputs_sha256", {})
    same = all(recorded.get(k) == v for k, v in cur.items()) and len(recorded) >= len(cur)
    rows.append(row("review renders (blind / realism / set) from the current exported bytes",
                    {"files": len(cur), "all_equal": same, "blind_pairs": rx.get("blind", {}).get("pairs"),
                     "realism_images": rx.get("realism", {}).get("images"), "set_images": rx.get("set", {}).get("images")},
                    "every input sha256 = the shipped file", same, "gates/review_export.json"))
    for doc in ("README.md", "MATERIALS_README.md"):
        rows.append(row(f"Exports/Guns/AR01/{doc}", (EXP / doc).exists(), "present", (EXP / doc).exists(),
                        "Exports/Guns/AR01"))
    out = {"stage": "7 apply fixes (resumed 2026-10-08)", "status": "pass" if all(r["pass"] for r in rows) else "fail",
           "failed": [r["name"] for r in rows if not r["pass"]], "gates": rows,
           "fix_log": "WorkFiles/guns/rifle/review/FIX_LOG.md",
           "not_judged_here": "the blind judge and the two realism judges run in the next review stage (target: at "
                              "most 1 single-judge fake call over the 4 realism views; blind reported, not blocking)"}
    (G / "review_fixes.json").write_text(json.dumps(out, indent=1, default=str))
    print(out["status"], out["failed"], len(rows))


if __name__ == "__main__":
    main()
