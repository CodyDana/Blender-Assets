"""``<name>.csk.json``: the kit data file written next to each FBX after export (CARDSHOP_KIT_SPEC.md 4.2).

The pipeline sidecar (``.sockets.json``) is never edited. This file records the SHA-256 of the FBX and of its
sidecar, the item class and data, and for fixtures the level grids. Every grid slot also gets its Unreal-space
transform (``slots_ue``), computed with ``pipeline.helpers.ue_socket_transform`` exactly as a real socket at that
place would be, so the Unreal side reads transforms instead of re-deriving the axis conversion.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Dict, Optional

from mathutils import Euler, Matrix, Vector

from pipeline.helpers import SOCKET_CORRECTION, ue_socket_transform

from . import fit
from .spec import MM, SPEC_VERSION


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def socket_matrix(loc_mm, rot_deg) -> Matrix:
    """The matrix ``helpers.make_socket`` gives an Empty authored at (loc, rot): intended frame @ correction."""
    basis = Matrix.Translation(Vector(loc_mm) * MM) @ Euler([math.radians(a) for a in rot_deg], "XYZ").to_matrix().to_4x4()
    return basis @ SOCKET_CORRECTION


def ue_slot(loc_mm, rot_deg=(0.0, 0.0, 0.0)) -> Dict:
    t = ue_socket_transform(socket_matrix(loc_mm, rot_deg))
    r = t["rotation_deg"]
    return {"loc_cm": t["location_cm"], "rot": [r["roll"], r["pitch"], r["yaw"]]}


def write_csk_json(item, fbx_path: str, sidecar_path: Optional[str], lod_info: Dict, aabb_mm) -> str:
    socket_locs = {s.name: s.loc for s in item.sockets}
    payload = {
        "spec": SPEC_VERSION,
        "fbx": Path(fbx_path).name,
        "fbx_sha256": sha256(fbx_path),
        "sockets_json": Path(sidecar_path).name if sidecar_path else None,
        "sockets_sha256": sha256(sidecar_path) if sidecar_path else None,
        "class": item.cls,
        "pivot": "Seat: bottom-centre, +X right, +Y away from the customer, +Z up",
        "render_aabb_mm": [list(map(fit._r, aabb_mm[0])), list(map(fit._r, aabb_mm[1]))],
        "lods": lod_info,
        "sockets": [{"name": s.name, "kind": s.kind, "loc_mm": list(map(fit._r, s.loc)), "rot_deg": list(s.rot)}
                    for s in item.sockets],
    }
    data = json.loads(json.dumps(item.data))
    for level in data.get("levels", []):
        lvl = socket_locs[level["socket"]]
        for grid in level["grids"]:
            grid["slots_ue"] = [ue_slot(p) for p in fit.grid_slots(lvl, grid)]
    payload.update(data)
    out = str(Path(fbx_path).with_suffix(".csk.json"))
    Path(out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return out


def verify_hashes(csk_json: str) -> Dict:
    """The G3 hash check: the .csk.json still describes the exact exported bytes."""
    p = Path(csk_json)
    d = json.loads(p.read_text(encoding="utf-8"))
    fbx = p.with_name(d["fbx"])
    ok_fbx = fbx.is_file() and sha256(fbx) == d["fbx_sha256"]
    ok_side = True
    if d.get("sockets_json"):
        side = p.with_name(d["sockets_json"])
        ok_side = side.is_file() and sha256(side) == d["sockets_sha256"]
    return {"test": "csk_hashes", "item": d["fbx"], "passed": ok_fbx and ok_side, "fbx": ok_fbx, "sidecar": ok_side}
