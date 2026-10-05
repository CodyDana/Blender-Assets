"""Gun QA additions (GUN_BUILDING_STUDY 4.9): tokenised gun deny list, B6a twin topology (inside Blender only for
b6a_topology).

The deny matcher splits names on separators, case changes and letter/digit changes and hits only on whole runs of
tokens (WorkFiles/studies/guns/repo_audit/deny_tokens_test.py is the prototype and its negative tests).
"""
from __future__ import annotations

import re
from typing import Dict, List

TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")
GUN_DENY = (
    "ak", "akm", "ak47", "ak74", "kalashnikov", "rpk", "pkm", "svd", "dragunov",
    "m4", "m4a1", "m16", "ar15", "armalite", "colt", "m249", "minimi", "m60",
    "ump", "mp5", "mp7", "hk", "heckler", "koch", "fn", "scar", "p90", "uzi", "galil", "famas", "steyr", "aug",
    "glock", "beretta", "sig", "sauer", "desert eagle", "deagle", "magnum research",
    "mossberg", "remington", "benelli", "barrett", "awm", "accuracy international", "magpul", "mlok", "m lok",
)


def tokens(name: str) -> List[str]:
    return [t.lower() for t in TOKEN_RE.findall(name)]


DENY_SEQS = [(term, [t for part in term.split() for t in tokens(part)]) for term in GUN_DENY]


def deny_hits(name: str) -> List[str]:
    tk = tokens(name)
    out = []
    for term, seq in DENY_SEQS:
        n = len(seq)
        if any(tk[i:i + n] == seq for i in range(len(tk) - n + 1)):
            out.append(term)
    return out


def b6a_topology(objs, name="SM_AR01_B6aCheck") -> Dict:
    """Join copies of the parts as the static twin would and run qa_check's topology + degenerate checks on the
    result (UV checks are reported as not applicable until stage 3 creates UVs)."""
    import bpy
    import bmesh
    import importlib
    Q = importlib.import_module("pipeline.qa_check")
    dg = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    for o in objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bm = bmesh.new()
    bm.from_mesh(me)
    checks = Q._topology_checks(ob, bm)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    bm.free()
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return {"object": name, "parts": len(objs), "triangles": tris, "checks": checks,
            "passed": all(c["passed"] for c in checks),
            "uv_checks": "n/a until stage 3 (no UVs yet); B6a re-runs with uv_no_overlap once UVs exist"}
