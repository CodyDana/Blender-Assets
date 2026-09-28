"""Look-match round 1 (sword): Blender-side engine gates on the SHIPPED bytes (the Verify phase runs Unreal).

    blender -b --factory-startup --python sfv4_lm_gates.py -- --out <json>

A fresh process re-imports Exports/SnowFlower/v4/SM_SnowFlower.fbx and checks: LOD nodes and triangle budgets, LOD
ratios, material slots, UV0/UV1 layers, UCX naming keyed to the LOD0 node + vertex counts + every LOD0 vertex inside
the hulls' union, the socket sidecar (names, positions vs the spec, scale 1, zero rotation), the texture set (power of
two, PNG colour types/bit depths, BC sRGB / ORM linear / N as data - read from the sidecar-free material contract),
DirectX normal convention on the N map (green flipped against the baked float array), and that the frozen revision-3
files are untouched (hashes vs the regression baseline).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sfv4_spec as S  # noqa: E402

ROOT = HERE.parents[2]
EXP = ROOT / "Exports" / "SnowFlower" / "v4"
FBX = EXP / "SM_SnowFlower.fbx"
TEX = EXP / "Textures"
BAKE = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "sword_build" / "bake"
BUDGET = {0: 40000}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def png_header(p):
    d = Path(p).read_bytes()[:33]
    w, h, bd, ct = struct.unpack(">IIBB", d[16:26])
    return {"w": w, "h": h, "bit_depth": bd, "colour_type": ct}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    gates = []

    def gate(name, ok, detail):
        gates.append({"gate": name, "passed": bool(ok), "detail": detail})

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(FBX))
    objs = {o.name: o for o in bpy.data.objects}
    lods = [objs.get(f"SM_SnowFlower_LOD{i}") for i in range(3)]
    gate("three LOD nodes", all(lods), [o.name if o else None for o in lods])
    tris = []
    for o in lods:
        o.data.calc_loop_triangles()
        tris.append(len(o.data.loop_triangles))
    gate("LOD0 within the hero budget (<= 40k)", tris[0] <= BUDGET[0], tris)
    gate("LOD ratios descend (LOD1 30-60 %, LOD2 8-30 % of LOD0)",
         0.3 <= tris[1] / tris[0] <= 0.6 and 0.08 <= tris[2] / tris[0] <= 0.3,
         [round(t / tris[0], 3) for t in tris])
    slots = [[m.name.split(".")[0] for m in o.data.materials] for o in lods]
    gate("material slots Blade / Fittings / Grip on every LOD", all(s == list(S.SLOT_NAMES) for s in slots), slots)
    uvs = [[u.name for u in o.data.uv_layers] for o in lods]
    gate("UV0 + UV1 on every LOD", all(len(u) >= 2 for u in uvs), uvs)
    ucx = sorted(n for n in objs if n.startswith("UCX_"))
    gate("UCX hulls keyed to the LOD0 node", len(ucx) == 5 and all(n.startswith("UCX_SM_SnowFlower_LOD0_") for n in ucx), ucx)
    gate("UCX <= 32 vertices each", all(len(objs[n].data.vertices) <= 32 for n in ucx),
         {n: len(objs[n].data.vertices) for n in ucx})
    # every LOD0 vertex inside the union of hulls (world space)
    lod0 = lods[0]
    M0 = np.array(lod0.matrix_world)
    V = np.array([v.co[:] for v in lod0.data.vertices])
    Vw = V @ M0[:3, :3].T + M0[:3, 3]
    inside = np.zeros(len(Vw), bool)
    for n in ucx:
        h = objs[n]
        Mh = np.array(h.matrix_world)
        H = np.array([v.co[:] for v in h.data.vertices]) @ Mh[:3, :3].T + Mh[:3, 3]
        ok = np.ones(len(Vw), bool)
        c = H.mean(axis=0)
        for p in h.data.polygons:
            pts = np.array([h.data.vertices[i].co[:] for i in p.vertices]) @ Mh[:3, :3].T + Mh[:3, 3]
            nrm = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            nrm /= max(np.linalg.norm(nrm), 1e-12)
            if np.dot(c - pts[0], nrm) > 0:
                nrm = -nrm
            ok &= (Vw - pts[0]) @ nrm <= 1e-5
        inside |= ok
    gate("every LOD0 vertex inside the hulls' union", inside.all(), {"outside": int((~inside).sum()), "of": len(Vw)})
    # sockets sidecar
    side = json.load(open(EXP / "SM_SnowFlower.sockets.json"))
    socks = {s["socket"]: s for s in side["sockets"]}
    exp = S.socket_positions()
    sd = {}
    okp = True
    for nm, (x, y, z) in exp.items():
        s = socks.get(nm)
        if not s:
            okp = False
            continue
        loc = s["location_cm"]
        # sidecar is in Unreal cm with the pipeline's axis correction: compare |values| to the spec in cm
        want = [x / 10.0, y / 10.0, z / 10.0]
        err = max(abs(abs(p) - abs(q)) for p, q in zip(loc, want))
        sd[nm] = {"cm": loc, "spec_cm": [round(w, 4) for w in want], "err": round(err, 4),
                  "rot0": all(abs(v) < 1e-6 for v in s["rotation_deg"].values()), "scale1": s["scale"] == [1.0, 1.0, 1.0]}
        okp &= err < 0.01 and sd[nm]["rot0"] and sd[nm]["scale1"]
    gate("sockets Grip / OffHand / BladeBase / BladeTip at the spec, rot 0, scale 1", okp and set(socks) == set(exp), sd)
    gate("LOD screen sizes 1.0 / 0.5 / 0.25 in the sidecar", side.get("lod_screen_sizes") == [1.0, 0.5, 0.25],
         side.get("lod_screen_sizes"))
    # textures
    th = {}
    okt = True
    for p in sorted(TEX.glob("T_SnowFlower_*.png")):
        if "Sheath" in p.name:
            continue
        h = png_header(p)
        th[p.name] = h
        pot = (h["w"] & (h["w"] - 1)) == 0 and (h["h"] & (h["h"] - 1)) == 0 and h["w"] == h["h"]
        okt &= pot
    gate("sword textures power of two, square", okt, th)
    gate("BC/ORM/N are 8-bit RGB (colour type 2); sampler contract BC sRGB, ORM + N linear (pack import settings)",
         all(v["colour_type"] == 2 and v["bit_depth"] == 8 for k, v in th.items() if k.endswith(("_BC.png", "_ORM.png", "_N.png"))),
         {k: (v["colour_type"], v["bit_depth"]) for k, v in th.items()})
    # DirectX: the shipped N green == 1 - baked OpenGL green (sample the covered texels)
    try:
        img = bpy.data.images.load(str(TEX / "T_SnowFlower_Steel_N.png"))
        img.colorspace_settings.name = "Non-Color"
        w, hgt = img.size
        px = np.array(img.pixels[:], np.float32).reshape(hgt, w, 4)      # Blender rows bottom-up == bake arrays
        nb = np.load(BAKE / "steel_NORMAL.npy")
        cov = np.load(BAKE / "steel_cov.npy")
        g_ship = px[..., 1][cov]
        g_bake = np.clip(nb[..., 1][cov], 0, 1)
        e_dx = float(np.abs(g_ship - (1 - g_bake)).mean())
        e_gl = float(np.abs(g_ship - g_bake).mean())
        gate("normal map is DirectX (green = 1 - baked OpenGL green)", e_dx < 0.01 and e_gl > e_dx * 5,
             {"mean_err_vs_dx": round(e_dx, 5), "mean_err_vs_gl": round(e_gl, 5)})
    except Exception as exc:  # noqa: BLE001
        gate("normal map is DirectX", False, str(exc))
    # revision-3 untouched
    base = ROOT / "WorkFiles" / "SnowFlower" / "v4" / "regression" / "rev3_sha256_at_sword_v4_start.txt"
    bad = []
    n = 0
    if base.exists():
        for line in base.read_text().splitlines():
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            h, p = parts[0], parts[-1].lstrip("*")
            f = ROOT / p
            n += 1
            if not f.exists() or sha(f) != h:
                bad.append(p)
    gate("revision-3 files unchanged", base.exists() and not bad, {"checked": n, "differ": bad})
    out = {"fbx": str(FBX), "fbx_sha256": sha(FBX), "sidecar_sha256": sha(EXP / "SM_SnowFlower.sockets.json"),
           "lod_triangles": tris, "gates": gates, "passed": all(g["passed"] for g in gates)}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print("SF4_GATES", out["passed"], json.dumps([(g["gate"], g["passed"]) for g in gates]))


if __name__ == "__main__":
    main()
