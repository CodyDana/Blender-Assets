"""Parse an ASCII FBX written by Unreal's StaticMeshExporterFBX: per polygon-vertex position (mm, Blender frame), UV0,
normal, tangent (the render data). Prints the corners whose tangent is zero or equals the normal."""
import re, sys, json
import numpy as np
from pathlib import Path


def arr(txt, key):
    m = re.search(key + r":\s*\*\d+\s*\{\s*a:\s*([^}]*)\}", txt)
    return np.array([float(x) for x in m.group(1).replace("\n", "").split(",") if x.strip()]) if m else None


def parse(path):
    t = Path(path).read_text(errors="ignore")
    geo = t[t.index("Geometry:"):]
    V = arr(geo, "Vertices").reshape(-1, 3)
    PVI = arr(geo, "PolygonVertexIndex").astype(np.int64)
    idx = np.where(PVI < 0, -PVI - 1, PVI)
    N = arr(geo[geo.index("LayerElementNormal"):], "Normals").reshape(-1, 3)
    T = arr(geo[geo.index("LayerElementTangent"):], "Tangents").reshape(-1, 3)
    uvs = geo[geo.index("LayerElementUV"):]
    UV = arr(uvs, "UV").reshape(-1, 2)
    UVI = arr(uvs, "UVIndex").astype(np.int64)
    return V, idx, N, T, UV[UVI]


if __name__ == "__main__":
    out = {}
    for p in sys.argv[1:]:
        V, idx, N, T, UV = parse(p)
        P = V[idx]
        tl = np.linalg.norm(T, axis=1)
        zero = np.nonzero(tl < 0.5)[0]
        same = np.nonzero(np.linalg.norm(T - N, axis=1) < 1.0 / 255 * 4)[0]
        rec = {"corners": int(len(idx)), "zero_tangent": int(len(zero)), "tangent_eq_normal": int(len(same)),
               "zero_pos_cm": np.round(P[zero[:12]], 4).tolist(), "zero_uv": np.round(UV[zero[:12]], 7).tolist()}
        out[Path(p).stem] = rec
        print(Path(p).stem, {k: v for k, v in rec.items() if not k.startswith("zero_")})
    Path("ar_fbxa_ntb.json").write_text(json.dumps(out, indent=1))
