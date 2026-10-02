"""Bump manifest.json after a change to this folder or to the files it lists (SYNC.md section 7). Plain Python 3.

    py -3 -B WorkFiles/shared/armory_hall/tools/bump_manifest.py --chat armory --summary "what changed and why" \
        [--files interior_layout.json,lights_design.json] [--interface-changed] [--retire SM_AK_Old --retire ...]
        [--correction "rev N: ..."] [--sync-all]
    py -3 -B WorkFiles/shared/armory_hall/tools/bump_manifest.py --record-sync ArmoryLab      # after a sync passed
    py -3 -B WorkFiles/shared/armory_hall/tools/bump_manifest.py --dry-run --chat dojo --summary x   # show, write nothing

Refuses unless this agent holds the ArmoryHall lock (py -3 -B Scripts/pipeline/lock.py claim ArmoryHall --agent claude).

What a bump does (one write of manifest.json, revision + 1):
  * rebuilds the asset lists from the layouts and recomputes every sha256:
      fbx            every interior piece (Exports/ArmoryKit) and every shell piece (Exports/DojoKit/Hall, + sidecar)
      item_fbx       the interior items' FBX
      materials      ArmoryLab's .uasset of every material instance the interior slots use and their masters
      textures       the armory textures those instances use: PNG + ArmoryLab .uasset
      shell_textures every texture shell_materials.json lists (PNG)
      shell_master_graph  graph_sha256 of shell_masters.json, which must equal the live dojo graph code
                     (tools/master_snapshot.py; a stale snapshot stops the bump: run master_snapshot.py --write first)
      site_fbx_dojolab_only   re-hashed in place (DojoLab-only 1v1 pieces)
      shared_files   the sha256 of SYNC.md, the layout jsons, shell_materials.json and the tools (an edit without a bump
                     is then caught by check_sync.py)
  * name stability (SYNC.md 9): a mesh name that was listed and is no longer used must be passed with --retire (it then
    goes to 'retired' with this revision); otherwise the bump stops. 'names_ever' keeps every name ever listed.
  * appends the change line {rev, date, chat, summary, files, recomputed, shared_files_changed, shared_files_added,
    first_recorded, sync_needed[, corrections]} (never edits older lines). A shared file or asset section recorded for
    the first time is listed as added / first recorded, not as changed. --correction "<text>" records a correction of an
    older line in the new line.
  * sync_needed_rev (rev 4, SYNC.md 3): per project, the last revision that changed something its Unreal sync reads.
    A bump that changes only ahcommon.NO_SYNC_FILES leaves it; tools/ue_armorylab_shell.py moves ArmoryLab's; any other
    changed shared file, FBX / texture / material entry, the shell master graph or --interface-changed moves both;
    the DojoLab-only site pieces move DojoLab's. --sync-all moves both regardless. check_sync.py reads it.
--record-sync <DojoLab|ArmoryLab> only sets last_synced[<project>] = the current revision (bookkeeping, no bump).
"""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ahcommon as A  # noqa: E402


def compute(M, S):
    I, H = S["interior_layout"], S["hall_shell_layout"]
    SM = S.get("shell_materials")
    AMAT = A.jload(A.ARMORY_BUILD / "unreal" / "materials.json")
    AIMP = A.jload(A.ARMORY_BUILD / "unreal" / "import.json")
    out = copy.deepcopy(M)
    old_fbx = M.get("fbx", {})
    fbx, missing = {}, []
    for p in sorted(I["pieces"]):
        f = A.EXPORTS_AK / f"{p}.fbx"
        if not f.exists():
            missing.append(A.rel(f) if f.is_absolute() else str(f))
            continue
        rec = dict(old_fbx.get(p, {}))
        rec.update({"path": f"Exports/ArmoryKit/{p}.fbx", "sha256": A.sha256(f), "bytes": f.stat().st_size,
                    "owner": "armory", "ue_mesh": f"/Game/ArmoryKit/Meshes/{p}"})
        fbx[p] = rec
    used_shell = {i["piece"] for i in A.placed_shell(H)}
    shell_names = list(H["pieces_existing"]) + [p for p in H["pieces_new"] if p not in H["pieces_existing"]]
    for p in shell_names:
        f = A.EXPORTS_HALL / f"{p}.fbx"
        if not f.exists():
            missing.append(f"Exports/DojoKit/Hall/{p}.fbx")
            continue
        rec = dict(old_fbx.get(p, {}))
        rec.update({"path": f"Exports/DojoKit/Hall/{p}.fbx", "sha256": A.sha256(f), "bytes": f.stat().st_size,
                    "owner": "dojo", "ue_mesh": f"/Game/DojoKit/Hall/Meshes/{p}", "placed": p in used_shell})
        sc = f.with_suffix(".sockets.json")
        if sc.exists():
            rec["sidecar_sha256"] = A.sha256(sc)
        fbx[p] = rec
    out["fbx"] = fbx
    out["item_fbx"] = {it["name"]: {"path": it["fbx"], "sha256": A.sha256(A.ROOT / it["fbx"]), "ue_mesh": it["ue_asset"]}
                       for it in I["items"]}
    mi_used = sorted({mi for p in I["pieces"].values() for mi in p["slots"]})
    masters = sorted({AMAT["instances"][mi]["master"] for mi in mi_used if mi in AMAT["instances"]})
    assets = {}
    for m in mi_used + masters:
        ua = A.ARMORYLAB / "Content/ArmoryKit/Materials" / f"{m}.uasset"
        assets[m] = {"armorylab_uasset": f"ArmoryLab/Content/ArmoryKit/Materials/{m}.uasset",
                     "sha256": A.sha256(ua) if ua.exists() else None, "kind": "master" if m in masters else "instance",
                     "master": AMAT["instances"].get(m, {}).get("master")}
        if not ua.exists():
            missing.append(assets[m]["armorylab_uasset"])
    out["materials"] = dict(M.get("materials", {}), masters=masters, instances=mi_used, assets=assets)
    tex = {}
    for t in sorted({t for mi in mi_used for t in AMAT["instances"].get(mi, {}).get("textures", {}).values()}):
        rec = {}
        png = A.EXPORTS_AK / "Textures" / f"{t}.png"
        if png.exists():
            rec["png"], rec["png_sha256"] = f"Exports/ArmoryKit/Textures/{t}.png", A.sha256(png)
        ua = A.ARMORYLAB / "Content/ArmoryKit/Textures" / f"{t}.uasset"
        if ua.exists():
            rec["armorylab_uasset_sha256"] = A.sha256(ua)
        if not rec:
            rec["missing"] = True
            missing.append(f"texture {t}")
        tex[t] = rec
    out["textures"] = tex
    if SM:
        out["shell_textures"] = {t: {"png": r["png"], "sha256": A.sha256(A.ROOT / r["png"]), "ue_path": r["ue_path"]}
                                 for t, r in SM["textures"].items()}
    import master_snapshot as MS  # noqa: PLC0415
    live = MS.build()
    snap = A.jload(MS.OUT) if MS.OUT.exists() else None
    if snap is None or snap.get("graph_sha256") != live["graph_sha256"]:
        missing.append("shell_masters.json is missing or stale against the dojo's graph code: "
                       "py -3 -B WorkFiles/shared/armory_hall/tools/master_snapshot.py --write")
    out["shell_master_graph"] = {"snapshot": "shell_masters.json", "graph_sha256": live["graph_sha256"],
                                 "masters": sorted(live["masters"]), "sources": live["sources"],
                                 "code_members": len(live["code"])}
    for k, r in out.get("site_fbx_dojolab_only", {}).items():
        f = A.ROOT / r["path"]
        if f.exists():
            r["sha256"], r["bytes"] = A.sha256(f), f.stat().st_size
    drift = [p for p in I["pieces"] if AIMP["meshes"].get(p, {}).get("sha256") not in (None, fbx.get(p, {}).get("sha256"))]
    out.setdefault("checks", {})["armorylab_import_sha_drift"] = drift
    out["shared_files"] = {n: A.sha256(A.SH / n) for n in A.SHARED_FILES if (A.SH / n).exists()}
    return out, missing


def main():
    ap = argparse.ArgumentParser(description="bump manifest.json (SYNC.md 7)")
    ap.add_argument("--chat", choices=["armory", "dojo"])
    ap.add_argument("--summary")
    ap.add_argument("--files", default="", help="comma list of the changed files (shared + exports)")
    ap.add_argument("--interface-changed", action="store_true")
    ap.add_argument("--retire", action="append", default=[], help="a mesh name that is no longer used (SYNC.md 9)")
    ap.add_argument("--record-sync", choices=["DojoLab", "ArmoryLab"])
    ap.add_argument("--correction", action="append", default=[],
                    help="a correction of an older change line, recorded in this bump's line (older lines are never edited)")
    ap.add_argument("--sync-all", action="store_true", help="this revision needs both projects re-synced, whatever changed")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--agent", default="claude")
    a = ap.parse_args()
    if not a.dry_run and not A.lock_held(a.agent):
        print("STOP: claim the lock first: py -3 -B Scripts/pipeline/lock.py claim ArmoryHall --agent claude")
        return 1
    M = A.jload(A.SH / "manifest.json")
    if a.record_sync:
        M.setdefault("last_synced", {})[a.record_sync] = M["revision"]
        if not a.dry_run:
            A.jdump(A.SH / "manifest.json", M)
        print(f"last_synced.{a.record_sync} = {M['revision']}")
        return 0
    if not (a.chat and a.summary):
        ap.error("--chat and --summary are required for a bump")
    S = A.shared()
    new, missing = compute(M, S)
    if missing:
        print("STOP: missing files:", missing[:20])
        return 1
    # name stability
    ever = set(M.get("names_ever") or M.get("fbx", {}).keys())
    retired = {r["name"] if isinstance(r, dict) else r for r in M.get("retired", [])}
    gone = sorted(n for n in ever if n not in new["fbx"] and n not in retired)
    bad = [n for n in gone if n not in a.retire]
    if bad:
        print("STOP: mesh names in use have disappeared (SYNC.md 9):", bad, "-> keep the name, or pass --retire <name> "
              "when the owner agreed to retire it")
        return 1
    rev = int(M["revision"]) + 1
    new["retired"] = list(M.get("retired", [])) + [{"name": n, "rev": rev, "date": A.today(), "chat": a.chat}
                                                   for n in gone]
    new["names_ever"] = sorted(ever | set(new["fbx"]))
    changed = {}
    first = []
    for sec in ("fbx", "item_fbx", "textures", "shell_textures", "site_fbx_dojolab_only"):
        if sec not in M and sec in new:
            first.append(sec)
            continue
        o, n = M.get(sec, {}), new.get(sec, {})
        ch = sorted(k for k in set(o) | set(n) if json.dumps(o.get(k), sort_keys=True) != json.dumps(n.get(k), sort_keys=True))
        if ch:
            changed[sec] = ch
    ma, na = M.get("materials", {}).get("assets", {}), new["materials"]["assets"]
    chm = sorted(k for k in set(ma) | set(na) if json.dumps(ma.get(k), sort_keys=True) != json.dumps(na.get(k), sort_keys=True))
    if chm:
        changed["materials"] = chm
    if "shell_master_graph" not in M:
        first.append("shell_master_graph")
    elif M["shell_master_graph"].get("graph_sha256") != new["shell_master_graph"]["graph_sha256"]:
        changed["shell_master_graph"] = ["graph_sha256"]
    of, nf = M.get("shared_files", {}), new["shared_files"]
    shf = sorted(k for k in set(of) & set(nf) if of[k] != nf[k])       # changed: recorded before and now different
    added = sorted(set(nf) - set(of))                                    # recorded for the first time
    gone_files = sorted(set(of) - set(nf))
    need = set(A.PROJECTS) if (a.sync_all or a.interface_changed or gone_files or any(
        changed.get(s) for s in ("fbx", "item_fbx", "materials", "textures", "shell_textures", "shell_master_graph"))) else set()
    if changed.get("site_fbx_dojolab_only"):
        need.add("DojoLab")
    for f in shf:
        if f in A.ARMORYLAB_ONLY_FILES:
            need.add("ArmoryLab")
        elif f not in A.NO_SYNC_FILES:
            need |= set(A.PROJECTS)
    prev = M.get("sync_needed_rev") or {p: int(M["revision"]) for p in A.PROJECTS}   # before rev 4: every rev needed both
    sync_needed_rev = {p: (rev if p in need else int(prev.get(p, M["revision"]))) for p in A.PROJECTS}
    summary = ("INTERFACE CHANGED: " if a.interface_changed else "") + a.summary
    files = [f for f in a.files.split(",") if f] or sorted(set(shf) | set(added) | set(gone_files)
                                                           | {f"{s}:{k}" for s, ks in changed.items() for k in ks})
    new["revision"], new["date"], new["chat"] = rev, A.today(), a.chat
    line = {"rev": rev, "date": A.today(), "chat": a.chat, "summary": summary, "files": files,
            "recomputed": {k: len(v) for k, v in changed.items()}, "shared_files_changed": shf,
            "shared_files_added": added, "first_recorded": sorted(first), "sync_needed": sorted(need)}
    if gone_files:
        line["shared_files_removed"] = gone_files
    if a.correction:
        line["corrections"] = list(a.correction)
    new["change_log"] = list(M.get("change_log", [])) + [line]
    new["sync_needed_rev"] = dict(sync_needed_rev, rule="per project, the last revision that changed what its Unreal "
                                  "sync reads (SYNC.md 3); check_sync.py: synced revision >= this = synced")
    print(f"revision {M['revision']} -> {rev}; asset entries changed: { {k: v for k, v in changed.items()} }; "
          f"shared files changed: {shf}; added: {added}; first recorded: {first}; retired now: {gone}; "
          f"sync needed: {sorted(need)} -> sync_needed_rev {sync_needed_rev}")
    if a.dry_run:
        print("dry run: nothing written")
        return 0
    order = ["revision", "date", "chat", "lock", "change_log", "last_synced", "sync_needed_rev", "shared_files", "fbx",
             "item_fbx", "names_ever", "retired", "pending_fbx", "materials", "textures", "shell_textures",
             "shell_master_graph", "checks", "site_fbx_dojolab_only"]
    new = {k: new[k] for k in order if k in new} | {k: v for k, v in new.items() if k not in order}
    A.jdump(A.SH / "manifest.json", new)
    print(f"manifest.json WRITTEN: revision {rev}. Next: release the lock, sync your project, record the sync "
          f"(--record-sync), tell the owner 'armory_hall revision {rev} is waiting for the other chat'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
