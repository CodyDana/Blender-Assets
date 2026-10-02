"""Minimal binary FBX reader for the armory_hall sync tools (plain Python 3 + numpy, no Blender / Unreal).

Reads what the envelope check needs from a Scripts/pipeline export: every mesh (render, LOD and UCX hull) as world
vertices of the PIECE's local frame in metres, +X east / +Y north / +Z up (the frame the layout jsons use).

How the frame is derived (measured, not assumed): the file's GlobalSettings give the up / front / coord axes and the
unit scale; each Model's Lcl Translation / Rotation (XYZ Euler, degrees) / Scaling is applied with its parent chain;
the result is converted to Z-up metres. The tools' self-test compares the result with the bbox the build recorded
(hall_shell_layout.json pieces_new[*].bbox_local_m) and refuses to judge a file whose frame does not reproduce it.
"""
import struct
import zlib
from pathlib import Path

import numpy as np


def _read_node(f, ver):
    if ver >= 7500:
        end, nprops, plen = struct.unpack("<QQQ", f.read(24))
    else:
        end, nprops, plen = struct.unpack("<III", f.read(12))
    nlen = f.read(1)[0]
    name = f.read(nlen).decode("ascii", "replace")
    if end == 0:
        return None
    props = []
    for _ in range(nprops):
        t = f.read(1)
        if t == b"Y":
            props.append(struct.unpack("<h", f.read(2))[0])
        elif t == b"C":
            props.append(bool(f.read(1)[0]))
        elif t == b"I":
            props.append(struct.unpack("<i", f.read(4))[0])
        elif t == b"F":
            props.append(struct.unpack("<f", f.read(4))[0])
        elif t == b"D":
            props.append(struct.unpack("<d", f.read(8))[0])
        elif t == b"L":
            props.append(struct.unpack("<q", f.read(8))[0])
        elif t in (b"S", b"R"):
            n = struct.unpack("<I", f.read(4))[0]
            raw = f.read(n)
            props.append(raw.decode("utf-8", "replace") if t == b"S" else raw)
        elif t in (b"f", b"d", b"l", b"i", b"b"):
            n, enc, clen = struct.unpack("<III", f.read(12))
            raw = f.read(clen)
            if enc == 1:
                raw = zlib.decompress(raw)
            dt = {b"f": "<f4", b"d": "<f8", b"l": "<i8", b"i": "<i4", b"b": "u1"}[t]
            props.append(np.frombuffer(raw, dtype=dt, count=n))
        else:
            raise ValueError(f"unknown FBX property type {t!r}")
    children = []
    while f.tell() < end:
        c = _read_node(f, ver)
        if c is None:
            break
        children.append(c)
    f.seek(end)
    return {"name": name, "props": props, "children": children}


def read(path):
    data = Path(path).read_bytes()
    if not data.startswith(b"Kaydara FBX Binary"):
        raise ValueError(f"{path}: not a binary FBX")
    import io
    f = io.BytesIO(data)
    f.seek(23)
    ver = struct.unpack("<I", f.read(4))[0]
    top = []
    while True:
        n = _read_node(f, ver)
        if n is None:
            break
        top.append(n)
    return ver, top


def _child(node, name):
    for c in node["children"]:
        if c["name"] == name:
            return c
    return None


def _p70(node):
    out = {}
    p = _child(node, "Properties70")
    if p:
        for c in p["children"]:
            if c["name"] == "P":
                out[c["props"][0]] = c["props"][4:]
    return out


def _euler_xyz(deg):
    rx, ry, rz = np.radians(deg)
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    X = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Y = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Z = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Z @ Y @ X   # FBX eEulerXYZ: R = Rz * Ry * Rx (applied X first)


def meshes(path):
    """{model name: (N, 3) vertices in metres, Z-up, piece-local frame}; also returns the file's axis info."""
    _ver, top = read(path)
    by = {n["name"]: n for n in top}
    gs = _p70(by["GlobalSettings"])
    unit = float(gs.get("UnitScaleFactor", [1.0])[0]) / 100.0          # file units -> metres
    up_ax, up_s = int(gs.get("UpAxis", [1])[0]), int(gs.get("UpAxisSign", [1])[0])
    fr_ax, fr_s = int(gs.get("FrontAxis", [2])[0]), int(gs.get("FrontAxisSign", [1])[0])
    co_ax, co_s = int(gs.get("CoordAxis", [0])[0]), int(gs.get("CoordAxisSign", [1])[0])
    # file basis -> Z-up right-handed (X = coord, Y = -front (parity), Z = up), the convention Blender's importer uses
    B = np.zeros((3, 3))
    B[0, co_ax] = co_s
    B[2, up_ax] = up_s
    B[1, fr_ax] = fr_s
    if np.linalg.det(B) < 0:
        B[1] *= -1
    objs = by["Objects"]
    geo, mdl = {}, {}
    for o in objs["children"]:
        uid = o["props"][0]
        nm = o["props"][1].split("\x00")[0]
        if o["name"] == "Geometry":
            v = _child(o, "Vertices")
            if v is not None:
                geo[uid] = np.asarray(v["props"][0], float).reshape(-1, 3)
        elif o["name"] == "Model":
            p = _p70(o)
            T = np.array(p.get("Lcl Translation", [0, 0, 0]), float)
            R = np.array(p.get("Lcl Rotation", [0, 0, 0]), float)
            S = np.array(p.get("Lcl Scaling", [1, 1, 1]), float)
            pre = np.array(p.get("PreRotation", [0, 0, 0]), float)
            M = np.eye(4)
            M[:3, :3] = _euler_xyz(pre) @ _euler_xyz(R) @ np.diag(S)
            M[:3, 3] = T
            mdl[uid] = {"name": nm, "M": M, "parent": None, "geo": None}
    for c in by["Connections"]["children"]:
        if c["props"][0] != "OO":
            continue
        a, b = c["props"][1], c["props"][2]
        if a in geo and b in mdl:
            mdl[b]["geo"] = a
        elif a in mdl and b in mdl:
            mdl[a]["parent"] = b
    out = {}
    for uid, m in mdl.items():
        if m["geo"] is None:
            continue
        M, q = m["M"], m["parent"]
        while q is not None:
            M = mdl[q]["M"] @ M
            q = mdl[q]["parent"]
        v = geo[m["geo"]]
        w = v @ M[:3, :3].T + M[:3, 3]
        out[m["name"]] = (w @ B.T) * unit
    return out, {"unit_m": unit, "up": (up_ax, up_s), "front": (fr_ax, fr_s), "coord": (co_ax, co_s)}


def bbox(path):
    ms, _ = meshes(path)
    allv = np.vstack(list(ms.values()))
    return [round(float(x), 4) for x in list(allv.min(0)) + list(allv.max(0))]
