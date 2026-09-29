#!/usr/bin/env python
"""Build the Card Shop Kit G1 standards-spike meshes (CARDSHOP_KIT_SPEC.md 7.1 P1): geometry, UVs, LODs, UCX hulls,
sockets, qa_check, export through Scripts/pipeline, the .csk.json kit data, and the kit's own fit / seat / stack /
hash / deny checks.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup \
        --python Scripts/cardshop/build_csk.py -- [--items card,slab,...] [--out DIR] [--report FILE] [--no-save]

Defaults: all G1 items, ``Exports/CardShopKit/G1/``, ``WorkFiles/cardshop/g1/build_report.json``, and the source
scene saved to ``Assets/CardShopKit/CSK_G1.blend`` (the CardShopKit lock must be held; ``--no-save`` skips it).
Exit code 0 only when every check passes; the report lists each check.

HOUSE rules kept: export only through ``pipeline.export_fbx``; ``qa_check`` on every mesh before export; sockets
only through ``helpers.make_socket``; the pipeline is used unedited.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
for p in (PROJECT / "Scripts", PROJECT / "Scripts" / "cardshop"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import bpy  # noqa: E402

from pipeline import VERSION as PIPELINE_VERSION  # noqa: E402
from pipeline.export_fbx import export_fbx  # noqa: E402
from pipeline.helpers import make_lod_group, make_socket  # noqa: E402
from pipeline.qa_check import qa_check  # noqa: E402

from csk_lib import fit, geom, mesh, slots  # noqa: E402
from csk_lib import spec as S  # noqa: E402

LIB_VERSION = "g1-1.0.0"
DEFAULT_OUT = PROJECT / "Exports" / "CardShopKit" / "G1"
DEFAULT_REPORT = PROJECT / "WorkFiles" / "cardshop" / "g1" / "build_report.json"
BLEND = PROJECT / "Assets" / "CardShopKit" / "CSK_G1.blend"
T0 = time.time()


def log(*a):
    print(f"[csk {time.time() - T0:6.1f}s]", *a, flush=True)


def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for item in list(block):
            block.remove(item)
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0


def build_item(item: geom.Item) -> dict:
    """Create the LOD objects, hulls and sockets of ``item`` in its own collection. Returns the handles."""
    coll = bpy.data.collections.new(item.name)
    bpy.context.scene.collection.children.link(coll)
    lods = list(item.lods)
    if len(lods) > 1:            # the LOD0-only rule (spec section 3): measure LOD0 first
        probe = mesh.to_object(f"__probe_{item.name}", lods[0].builder, item.materials, item.projections,
                               bevel_mm=lods[0].bevel_mm, collection=coll, ops=lods[0].ops,
                               bevel_segments=lods[0].bevel_segments, bevel_first=lods[0].bevel_first)
        if mesh.triangles(probe) <= S.LOD0_ONLY_MAX_TRIS:
            lods = lods[:1]
            item.data.setdefault("notes", []).append(
                f"LOD0 only: {mesh.triangles(probe)} tris <= {S.LOD0_ONLY_MAX_TRIS} (spec section 3 rule)")
        me = probe.data
        bpy.data.objects.remove(probe, do_unlink=True)
        bpy.data.meshes.remove(me)
    multi = len(lods) > 1
    objs = []
    for i, lod in enumerate(lods):
        name = f"{item.name}_LOD{i}" if multi else item.name
        obj = mesh.to_object(name, lod.builder, item.materials, item.projections, bevel_mm=lod.bevel_mm,
                             collection=coll, ops=lod.ops, bevel_segments=lod.bevel_segments,
                             bevel_first=lod.bevel_first)
        objs.append(obj)
    lod0 = objs[0]
    for k, (mn, mx) in enumerate(item.hulls):
        mesh.box_hull(lod0, k, mn, mx)
    for s in item.sockets:
        make_socket(lod0, s.name, tuple(v * S.MM for v in s.loc), tuple(math.radians(a) for a in s.rot))
    group = make_lod_group(item.name, objs) if multi else None
    log(f"built {item.name}: LOD tris {[mesh.triangles(o) for o in objs]}")
    return {"item": item, "objs": objs, "group": group}


def item_aabb(objs) -> tuple:
    """Render bounds over every LOD (the fit test uses render bounds, spec 4.2)."""
    boxes = [mesh.aabb_mm(o) for o in objs]
    mn = tuple(min(b[0][i] for b in boxes) for i in range(3))
    mx = tuple(max(b[1][i] for b in boxes) for i in range(3))
    return mn, mx


def stage_qa(built, report) -> bool:
    ok_all = True
    rep = {}
    for h in built:
        item, objs = h["item"], h["objs"]
        r = qa_check([o.name for o in objs], budget_tris=item.budget, require_uv1=True, require_ucx=True,
                     overlap_method="sat")
        failed = [c for c in r["checks"] if not c["passed"]]
        tris = [mesh.triangles(o) for o in objs]
        lod_rule = (len(objs) == 1) == (tris[0] <= S.LOD0_ONLY_MAX_TRIS)
        winding = sum(mesh.check_outward(o) for o in objs) if item.name.endswith(("_Glass_1778", "_Lid", "_Door_1778")) else 0
        uv_degenerate = {o.name: [mesh.degenerate_uv_faces(o, "UVMap"), mesh.degenerate_uv_faces(o, "Lightmap")]
                         for o in objs}
        uv_ok = all(sum(v) == 0 for v in uv_degenerate.values())
        rep[item.name] = {"passed": r["passed"] and lod_rule and winding == 0 and uv_ok, "checks": len(r["checks"]),
                          "uv_degenerate_faces": uv_degenerate,
                          "failed": [{"name": c["name"], "object": c["object"], "detail": c["detail"]}
                                     for c in failed],
                          "triangles": tris, "budget_lod0": item.budget,
                          "lod_rule": {"passed": lod_rule, "rule": f"LOD0 only iff <= {S.LOD0_ONLY_MAX_TRIS} tris"},
                          "winding_errors": winding}
        ok = rep[item.name]["passed"]
        ok_all &= ok
        log(f"qa_check {item.name}: {'PASS' if ok else 'FAIL'} tris={tris}"
            + ("" if ok else f" failed={[c['name'] + '@' + c['object'] for c in failed]} lod_rule={lod_rule}"
                            f" winding={winding} uv_degenerate={uv_degenerate}"))
    report["qa"] = {"passed": ok_all, "per_item": rep}
    return ok_all


def stage_export(built, out: Path, report) -> bool:
    out.mkdir(parents=True, exist_ok=True)
    rep = {}
    ok_all = True
    for h in built:
        item, objs, group = h["item"], h["objs"], h["group"]
        fbx = out / f"{item.name}.fbx"
        aabb = item_aabb(objs)
        radius = S.bounds_radius(tuple(aabb[1][i] - aabb[0][i] for i in range(3)))
        kwargs = {}
        sizes = None
        if group is not None:
            sizes = S.screen_sizes(radius, len(objs))
            kwargs["lod_screen_sizes"] = sizes
        r = export_fbx(str(fbx), [(group or objs[0]).name], kind="static", **kwargs)
        lod_info = {"count": len(objs), "triangles": [mesh.triangles(o) for o in objs],
                    "screen_sizes": r["lod_screen_sizes"], "class": S.lod_class(radius).name,
                    "bounds_radius_mm": round(radius, 3)}
        csk = slots.write_csk_json(item, str(fbx), r["sidecar"], lod_info, aabb)
        rep[item.name] = {"fbx": fbx.name, "bytes": fbx.stat().st_size, "sha256": slots.sha256(fbx),
                          "sidecar": Path(r["sidecar"]).name if r["sidecar"] else None,
                          "csk_json": Path(csk).name, "warnings": r["warnings"], "lods": lod_info,
                          "sockets": len(r["sockets"])}
        log(f"exported {fbx.name} ({fbx.stat().st_size} B, LODs {lod_info['triangles']}, sizes {sizes})")
    report["export"] = rep
    return ok_all


def stage_kit_checks(built, out: Path, report) -> bool:
    """qa_csk: contain fit, level grids + hull test, stacks, socket counts, .csk.json hashes, deny scan."""
    by_name = {h["item"].name: h for h in built}
    aabb = {n: item_aabb(h["objs"]) for n, h in by_name.items()}
    by_class = {}
    for n, h in by_name.items():
        c = h["item"].cls
        if c and not n.endswith("_Filled"):
            by_class.setdefault(c, n)
    results = []
    # contain fits
    for n, h in by_name.items():
        item = h["item"]
        socks = {s.name: s for s in item.sockets}
        for key, c in item.data.get("contain", {}).items():
            names = c.get("sockets") or [c["socket"]]
            cav = (tuple(c["cavity_mm"][0]), tuple(c["cavity_mm"][1]))
            for acc in c["accepts"]:
                it = by_class.get(acc)
                if not it:
                    continue
                results += fit.check_contain(n, cav, [(sn, socks[sn].loc, socks[sn].rot) for sn in names], it, aabb[it])
    # level grids against every hull of the fixture and its glass
    for n, h in by_name.items():
        item = h["item"]
        if "levels" not in item.data:
            continue
        socks = {s.name: s for s in item.sockets}
        hulls = list(item.hulls)
        glass = by_name.get(item.data.get("glass", ""))
        if glass:
            hulls += list(glass["item"].hulls)
        tested = 0
        for level in item.data["levels"]:
            for grid in level["grids"]:
                it = by_class.get(grid["class"])
                if not it:
                    continue
                tested += 1
                results += fit.check_level(n, level, socks[level["socket"]].loc, grid, it, aabb[it], hulls)
                st = by_name[it]["item"].data.get("stack")
                if st:
                    results.append(dict(fit.check_stack(it, aabb[it], st, level["clear_h_mm"]),
                                        level=level["socket"], fixture=n))
        n_sock = len(item.sockets)
        results.append({"test": "fixture_socket_count", "item": n, "passed": n_sock <= 40, "sockets": n_sock,
                        "limit": 40, "grids_tested": tested})
    # hashes
    for n in by_name:
        csk = out / f"{n}.csk.json"
        if csk.exists():
            results.append(slots.verify_hashes(str(csk)))
    # deny scan: object, material and socket names + every .csk.json string
    texts = [o.name for o in bpy.data.objects] + [m.name for m in bpy.data.materials]
    texts += [json.dumps(json.loads(p.read_text(encoding="utf-8"))) for p in out.glob("*.csk.json")]
    hits = sorted({hit for t in texts for hit in S.deny_hits(t)})
    results.append({"test": "deny_scan", "passed": not hits, "hits": hits, "strings": len(texts)})
    ok = all(r["passed"] for r in results)
    fails = [r for r in results if not r["passed"]]
    report["kit_checks"] = {"passed": ok, "count": len(results), "failed": fails[:40],
                            "summary": _summary(results)}
    log(f"kit checks: {'PASS' if ok else 'FAIL'} ({len(results) - len(fails)}/{len(results)})")
    for f in fails[:12]:
        log("  FAIL", json.dumps(f)[:300])
    return ok


def _summary(results):
    s = {}
    for r in results:
        k = r["test"]
        s.setdefault(k, [0, 0])
        s[k][0] += 1
        s[k][1] += bool(r["passed"])
    return {k: f"{v[1]}/{v[0]}" for k, v in sorted(s.items())}


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default=",".join(geom.ALL_ITEMS))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--report", default=str(DEFAULT_REPORT))
    ap.add_argument("--blend", default=str(BLEND))
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--agent", default="claude")
    return ap.parse_args(argv)


def main() -> int:
    args = parse_args()
    report = {"lib": LIB_VERSION, "spec": S.SPEC_VERSION, "pipeline": PIPELINE_VERSION,
              "blender": bpy.app.version_string, "items": args.items.split(","), "passed": False}
    code = 1
    try:
        if not args.no_save:
            from pipeline.lock import assert_owner
            assert_owner("CardShopKit", args.agent)
        reset_scene()
        built = [build_item(geom.ALL_ITEMS[k]()) for k in args.items.split(",")]
        ok = stage_qa(built, report)
        if ok:
            stage_export(built, Path(args.out), report)
            ok = stage_kit_checks(built, Path(args.out), report)
        if not args.no_save:
            Path(args.blend).parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.wm.save_as_mainfile(filepath=str(args.blend), compress=True)
            report["blend"] = str(Path(args.blend).relative_to(PROJECT)) if PROJECT in Path(args.blend).parents \
                else str(args.blend)
        report["passed"] = bool(ok)
        code = 0 if ok else 1
    except Exception:  # noqa: BLE001
        report["error"] = traceback.format_exc()
        log(report["error"])
    report["seconds"] = round(time.time() - T0, 1)
    rp = Path(args.report)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"CSK_BUILD {'PASSED' if report['passed'] else 'FAILED'} report={rp}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
