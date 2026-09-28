"""The pack-materials lock: one owner at a time may EDIT or BUILD the shared materials (2026-09-27).

Several chats share this folder and the validation project.  A build run by one chat while another is half-way
through editing np_masters.py / material_spec.json deleted a master (see np_preflight.py).  So:

  * ``run_build.sh`` takes this lock for the whole run and releases it on exit;
  * a chat that is about to EDIT anything in Scripts/unreal/materials/ takes it first and releases it when its edits
    are finished and built:  ``py -3 -B np_lock.py claim <owner>`` ... ``py -3 -B np_lock.py release <owner>``.

Owners must be distinct per chat (every chat is agent "claude" in the asset locks), e.g. "snowflower-chat",
"paperbomb-chat", "run_build:<tag>".  The record lives in WorkFiles/locks/packmaterials.json via Scripts/pipeline/lock.py.
A holder whose process is gone (pid not alive) is taken over automatically; a live holder is never overridden.

    py -3 -B np_lock.py claim <owner> [--pid N]   exit 0 = held by you; exit 2 = held by someone else (prints who)
    py -3 -B np_lock.py release <owner>
    py -3 -B np_lock.py status
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "pipeline"))
import lock  # noqa: E402

ASSET = "PackMaterials"


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd = argv[0]
    if cmd == "status":
        print(json.dumps(lock.status(ASSET), indent=1))
        return 0
    owner = argv[1] if len(argv) > 1 else None
    if not owner:
        print("give an owner name")
        return 1
    pid = int(argv[argv.index("--pid") + 1]) if "--pid" in argv else None
    if cmd == "claim":
        cur = lock.status(ASSET)
        if cur and cur.get("agent") != owner:
            if cur.get("pid_alive") is False:
                rec = lock.claim(ASSET, owner, pid=pid, force=True)
                print(f"took over the materials lock from {cur.get('agent')} (its process {cur.get('pid')} is gone)")
                return 0
            print(f"MATERIALS LOCK HELD by '{cur.get('agent')}' since {cur.get('since')} (pid {cur.get('pid')}, "
                  f"alive={cur.get('pid_alive')}). Wait for it to finish; never force a live holder.")
            return 2
        lock.claim(ASSET, owner, pid=pid)
        print(f"materials lock held by {owner}")
        return 0
    if cmd == "release":
        cur = lock.status(ASSET)
        if cur and cur.get("agent") == owner:
            lock.release(ASSET, owner)
            print(f"materials lock released by {owner}")
        else:
            print(f"not released: holder is {cur.get('agent') if cur else 'nobody'}")
        return 0
    print(f"unknown command {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
