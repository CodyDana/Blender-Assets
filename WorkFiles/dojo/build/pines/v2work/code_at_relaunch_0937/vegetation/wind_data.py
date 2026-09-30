"""Wind data from the branch hierarchy: element table, Pivot Painter 2 arrays, foliage vertex colours (numpy only).

TREE_BUILDING_STUDY.md 4.9 (stage e). One hierarchy, several encodings:
  * elements = trunk (level 0) -> scaffold limbs (1) -> sub-limbs (2) -> pads (last level); at most 4 levels;
  * PP2: T_*_PivotPos (16-bit half RGBA: RGB = pivot in Unreal cm (x, -y, z) * 100, A = parent index as
    "Int as float" = the integer's bits stored in the half) and T_*_XVector (8-bit RGBA: RGB = 0.5 + 0.5 * the
    element's X axis in Unreal space, A = X extent / 2048 cm); one texel per element, power-of-two size;
  * UV2 of every foliage vertex = the texel centre of its pad element (Blender UV convention; the FBX V flip and
    the image row order cancel, see ``texel_uv``);
  * vertex colour (ONE set, linear floats, exported as sRGB by the pipeline): R hierarchy weight 0 at the pad
    pivot -> 1 at the tips, G per-pad phase, B per-tuft phase, A unused (voxels overwrite it).
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from skeleton import arclength

PP2_EXTENT_CM = 2048.0


def _pow2(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


def elements(sk: Dict, ground_z: float = 0.0) -> List[Dict]:
    br = sk["branches"]
    out: List[Dict] = []
    elem_of_branch: Dict[int, int] = {}
    t = br[0].pts
    base_i = int(np.argmin(np.abs(t[:, 2] - ground_z)))
    pivot = t[base_i]
    top = t[-1]
    out.append({"id": 0, "name": "trunk", "kind": "trunk", "parent": 0, "level": 0, "pivot": pivot,
                "axis": (top - pivot) / np.linalg.norm(top - pivot), "extent": float(arclength(t[base_i:])[-1])})
    elem_of_branch[0] = 0
    for bi, b in enumerate(br):
        if b.kind != "limb":
            continue
        pe = elem_of_branch.get(b.parent, 0)
        ax = b.pts[-1] - b.pts[0]
        e = {"id": len(out), "name": f"limb_b{bi}", "kind": "limb", "parent": pe, "level": out[pe]["level"] + 1,
             "pivot": b.pts[0], "axis": ax / max(np.linalg.norm(ax), 1e-9), "extent": float(arclength(b.pts)[-1]),
             "branch": bi, "feeds_pad": b.pad}
        elem_of_branch[bi] = e["id"]
        out.append(e)
    pad_elem = {}
    for pi, env in enumerate(sk["envs"]):
        fb = sk["feed"].get(pi, 0)
        fpts = br[fb].pts
        j = int(np.argmin(((fpts - env.centre) ** 2).sum(1)))
        # pivot where the feeding branch enters the pad: the last node outside the envelope, else the nearest
        rho = env.rho(fpts)
        outside = np.nonzero(rho[: j + 1] >= 1.0)[0]
        piv = fpts[outside[-1]] if len(outside) else fpts[j]
        ax = env.centre - piv
        if np.linalg.norm(ax) < 1e-3:
            ax = np.array([0.0, 0.0, 1.0])
        pe = elem_of_branch.get(fb, 0)
        e = {"id": len(out), "name": f"pad{pi}", "kind": "pad", "parent": pe, "level": out[pe]["level"] + 1,
             "pivot": piv, "axis": ax / np.linalg.norm(ax), "extent": float(max(env.rx, env.ry)), "pad": pi,
             "centre": env.centre}
        pad_elem[pi] = e["id"]
        out.append(e)
    for e in out:
        e["pad_elem"] = pad_elem
    return out


def texel_uv(i: int, w: int, h: int):
    return ((i % w) + 0.5) / w, ((i // w) + 0.5) / h


def pp2_arrays(elems: List[Dict]) -> Dict:
    n = len(elems)
    w = 8 if n <= 64 else 16
    h = _pow2(max(1, int(np.ceil(n / w))))
    pos = np.zeros((h, w, 4), dtype=np.float32)
    xv = np.zeros((h, w, 4), dtype=np.float32)
    for e in elems:
        i = e["id"]
        row, col = i // w, i % w                      # Blender pixel rows run bottom-up, like UV v
        p = e["pivot"]
        pos[row, col, :3] = (100.0 * p[0], -100.0 * p[1], 100.0 * p[2])
        pos[row, col, 3] = np.uint16(e["parent"]).view(np.float16).astype(np.float32)
        a = e["axis"]
        xv[row, col, :3] = 0.5 + 0.5 * np.array([a[0], -a[1], a[2]])
        xv[row, col, 3] = min(1.0, 100.0 * e["extent"] / PP2_EXTENT_CM)
    return {"pivot_pos": pos, "xvector": xv, "w": w, "h": h}


def phase(ids: np.ndarray, salt: float) -> np.ndarray:
    x = np.sin(ids.astype(np.float64) * 12.9898 + salt * 78.233) * 43758.5453
    return x - np.floor(x)


def foliage_colours(P: np.ndarray, pad: np.ndarray, tuft: np.ndarray, elems: List[Dict]) -> np.ndarray:
    pad_elem = elems[0]["pad_elem"]
    col = np.zeros((len(P), 4), dtype=np.float32)
    for pi, ei in pad_elem.items():
        m = pad == pi
        if not m.any():
            continue
        e = elems[ei]
        d = np.linalg.norm(P[m] - e["pivot"], axis=1)
        reach = float(np.linalg.norm(e["pivot"] - e["centre"])) + e["extent"]
        col[m, 0] = np.clip(d / max(reach, 1e-3), 0.0, 1.0)
    col[:, 1] = phase(pad, 1.7)
    col[:, 2] = phase(tuft, 3.1)
    col[:, 3] = 1.0
    return col


def wind_json(asset: str, elems: List[Dict], pp2: Dict, tex_names: Dict, pad_tufts: Dict) -> Dict:
    def rec(e):
        p = e["pivot"]
        a = e["axis"]
        return {"id": e["id"], "name": e["name"], "kind": e["kind"], "parent": int(e["parent"]),
                "level": int(e["level"]), "pivot_blender_m": [round(float(v), 4) for v in p],
                "pivot_unreal_cm": [round(100 * float(p[0]), 2), round(-100 * float(p[1]), 2),
                                    round(100 * float(p[2]), 2)],
                "x_axis_unreal": [round(float(a[0]), 4), round(-float(a[1]), 4), round(float(a[2]), 4)],
                "extent_m": round(float(e["extent"]), 4),
                "texel_uv2_blender": [round(v, 6) for v in texel_uv(e["id"], pp2["w"], pp2["h"])],
                **({"pad": e["pad"], "tufts": int(pad_tufts.get(e["pad"], 0))} if e["kind"] == "pad" else {}),
                **({"branch": e["branch"]} if "branch" in e else {})}
    levels = max(e["level"] for e in elems) + 1
    return {
        "asset": asset,
        "route": "A (static Nanite + WPO); trunk mesh carries no WPO (niwaki are stiff, study 5.4)",
        "levels": levels,
        "levels_ok": levels <= 4,
        "elements": [rec(e) for e in elems],
        "pp2": {"texture_size": [pp2["w"], pp2["h"]], "pivot_pos": tex_names["pivot_pos"],
                "xvector": tex_names["xvector"], "uv_index": 2,
                "parent_index_encoding": "Int as float (uint16 bits stored in the half)",
                "xvector_alpha": f"extent_cm / {PP2_EXTENT_CM:g}",
                "unreal_space": "x_ue = 100 x, y_ue = -100 y, z_ue = 100 z (cm)"},
        "vertex_colour": {"R": "hierarchy weight (0 at the pad pivot -> 1 at the needle tips)",
                          "G": "per-pad phase", "B": "per-tuft phase", "A": "unused (Nanite voxels overwrite it)",
                          "authoring": "linear floats, exported colors_type=SRGB; import with Vertex Color "
                                       "Import Option = Replace (the static default Ignore drops them)"},
        "uv": {"0": "needle cell (overlap-free, tiling needle texture)", "1": "lightmap 0-1 no overlap",
               "2": "PP2 element index (texel centre)", "3": "U = canopy AO, V spare"},
    }
