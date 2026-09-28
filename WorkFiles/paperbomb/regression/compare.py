"""Prove a later paper-bomb build is unchanged against a snapshot (plain Python).

    py WorkFiles/paperbomb/regression/compare.py --baseline post_paper_bomb
    py WorkFiles/paperbomb/regression/compare.py --baseline post_paper_bomb --against <other snapshot>

With no ``--against`` it compares the baseline to the LIVE tree, which is what you run
after a rebuild to answer the only question that matters: did anything move that I did
not mean to move?

THREE LEVELS, BECAUSE THEY FAIL DIFFERENTLY
-------------------------------------------
1.  BYTES.  Every file in SHA256SUMS.txt is re-hashed.  The build is deterministic in
    its seed, so the blend, the FBX, the sidecar, the four maps and every source file
    should be byte-identical.  A difference here is the headline.

2.  MEASUREMENTS.  The two reports are compared on the numbers a buyer or the engine
    would notice - triangle counts, screen sizes, bounds, mass, texel density, socket
    positions, the gate table - so a change that alters bytes can be read as "the LOD2
    count moved by four" instead of "the hash is different".

3.  RENDERS.  Cycles is not bit-reproducible (denoising and tile scheduling move the
    last bits), so the gallery images are compared statistically: mean absolute
    difference and the 99.9th percentile, per image.  Under about 0.01 mean is sampling
    noise; a real change to the art moves it by an order of magnitude.

Exit code 0 when everything matches, 1 when something did not.
"""
import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent

#: snapshot-relative path -> where it lives in the live tree
LIVE = {
    "PaperBomb.blend": PROJECT / "Assets" / "PaperBomb.blend",
    "paperbomb_report.json": PROJECT / "WorkFiles" / "paperbomb" / "paperbomb_report.json",
    "PAPERBOMB_REPORT.md": PROJECT / "WorkFiles" / "paperbomb" / "PAPERBOMB_REPORT.md",
}
LIVE_DIRS = {
    "export": PROJECT / "Exports" / "PaperBomb",
    "textures": PROJECT / "Exports" / "PaperBomb" / "Textures",
    "recolour": PROJECT / "Exports" / "PaperBomb" / "Textures" / "Recolour",
    "renders": PROJECT / "Renders" / "PaperBomb",
    "scripts": PROJECT / "Scripts" / "props",
}

MEASURED = ("lod_triangles", "lod_screen_sizes", "switch_distances_m", "bounds_radius_mm",
            "size_cm")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def live_path(rel: str) -> Path:
    if rel in LIVE:
        return LIVE[rel]
    head, _, tail = rel.partition("/")
    if head in LIVE_DIRS:
        return LIVE_DIRS[head] / tail
    return PROJECT / rel


def read_png_gray(path: Path):
    """Decode a PNG to a flat list of 0-255 luma samples, without PIL or numpy.

    Only what this project writes: 8-bit RGB or RGBA, no interlace.  Enough to say
    whether two renders are the same picture.
    """
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, idat, width, height, channels = 8, b"", 0, 0, 3
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            width, height, depth, colour = struct.unpack(">IIBB", payload[:10])
            if depth != 8 or colour not in (2, 6):
                return None
            channels = 3 if colour == 2 else 4
        elif tag == b"IDAT":
            idat += payload
        elif tag == b"IEND":
            break
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = width * channels
    out = []
    prev = bytearray(stride)
    at = 0
    for _ in range(height):
        f = raw[at]
        line = bytearray(raw[at + 1:at + 1 + stride])
        at += 1 + stride
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b = prev[i]
            c = prev[i - channels] if i >= channels else 0
            if f == 1:
                line[i] = (line[i] + a) & 0xFF
            elif f == 2:
                line[i] = (line[i] + b) & 0xFF
            elif f == 3:
                line[i] = (line[i] + (a + b) // 2) & 0xFF
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        for i in range(0, stride, channels):
            out.append((line[i] * 299 + line[i + 1] * 587 + line[i + 2] * 114) // 1000)
        prev = line
    return out


#: FBX fields Blender rewrites on every export even when nothing changed: the creation
#: timestamp, the document's own id, and the 64-bit object UIDs.  Measured on two
#: back-to-back exports of an unchanged scene: same length, 149 differing bytes out of
#: 95,916, every one of them inside one of these.
VOLATILE_FBX_FIELDS = {
    b"Hour", b"Minute", b"Second", b"Millisecond", b"CreationTime", b"CreationTimeStamp",
    b"DocumentL", b"NodeAttributeL", b"GeometryL", b"ModelL", b"MaterialL", b"VideoL",
    b"TextureL", b"AnimationStackL", b"AnimationLayerL", b"DocumentUrl", b"SrcDocumentUrl",
    b"FileId", b"Document", b"Creator",
}


def fbx_metadata_diff(a: Path, b: Path) -> dict:
    """Are two FBX files different only in the fields Blender rewrites every export?

    A regression harness has to be able to tell "the mesh changed" from "the clock did".
    Both files are compared byte for byte; each differing run is labelled with the
    nearest ASCII field name that precedes it, which in an FBX binary is the property
    that owns those bytes.  If every run belongs to a known-volatile field the answer is
    yes, and the evidence - the labels and the offsets - is in the result either way.
    """
    x, y = a.read_bytes(), b.read_bytes()
    out = {"same_length": len(x) == len(y), "bytes": [len(x), len(y)]}
    if len(x) != len(y):
        out["metadata_only"] = False
        out["reason"] = "the files are different lengths, so something real changed"
        return out
    diff = [i for i in range(len(x)) if x[i] != y[i]]
    out["differing_bytes"] = len(diff)
    if not diff:
        out["metadata_only"] = True
        return out
    runs = []
    start = prev = diff[0]
    for i in diff[1:]:
        if i != prev + 1:
            runs.append((start, prev))
            start = i
        prev = i
    runs.append((start, prev))

    # Everything after the Connections header is a list of object-UID PAIRS, and those
    # UIDs are the same ones that changed up in Objects - so a differing byte in there
    # is the same fact told twice, not a second fact.
    connections_at = x.find(b"\x0bConnections")

    def label(at: int) -> str:
        window = x[max(0, at - 64):at]
        best = None
        for field in VOLATILE_FBX_FIELDS:
            j = window.rfind(field)
            if j >= 0 and (best is None or j > best[0]):
                best = (j, field.decode("ascii"))
        if best:
            return best[1]
        if connections_at >= 0 and at > connections_at:
            return "Connections"
        return "?"

    labelled = [{"at": s, "length": e - s + 1, "field": label(s)} for s, e in runs]
    out["runs"] = labelled[:40]
    out["run_count"] = len(labelled)
    out["fields"] = sorted({r["field"] for r in labelled})
    out["metadata_only"] = all(r["field"] != "?" for r in labelled)
    out["note"] = ("metadata_only means every differing byte sits inside a field Blender "
                   "rewrites on every export - the clock and the object UIDs - so the "
                   "geometry is unchanged.  False means look closer.")
    return out


def compare_renders(a_dir: Path, b_dir: Path) -> dict:
    out = {}
    for src in sorted(a_dir.glob("*.png")):
        other = b_dir / src.name
        if not other.is_file():
            out[src.name] = {"missing": True}
            continue
        x, y = read_png_gray(src), read_png_gray(other)
        if x is None or y is None or len(x) != len(y):
            out[src.name] = {"undecodable_or_different_size": True}
            continue
        diff = sorted(abs(p - q) for p, q in zip(x, y))
        out[src.name] = {
            "mean_abs_diff_255": round(sum(diff) / len(diff), 4),
            "p999_abs_diff_255": diff[min(len(diff) - 1, int(len(diff) * 0.999))],
            "max_abs_diff_255": diff[-1],
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--against", default=None,
                    help="another snapshot; omitted means the live tree")
    ap.add_argument("--out", default=None)
    ap.add_argument("--skip-renders", action="store_true")
    args = ap.parse_args(argv)

    base = HERE / args.baseline
    if not base.is_dir():
        print(f"no snapshot at {base}")
        return 2
    other = (HERE / args.against) if args.against else None

    result = {"baseline": args.baseline, "against": args.against or "LIVE",
              "bytes": {"same": [], "different": [], "missing": []}}
    for line in (base / "SHA256SUMS.txt").read_text(encoding="utf8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        target = (other / rel) if other else live_path(rel)
        if not target.is_file():
            result["bytes"]["missing"].append(rel)
        elif sha256(target) == digest:
            result["bytes"]["same"].append(rel)
        else:
            result["bytes"]["different"].append(rel)

    fbx_rel = "export/SM_PaperBomb.fbx"
    if fbx_rel in result["bytes"]["different"]:
        target = (other / fbx_rel) if other else live_path(fbx_rel)
        result["fbx_diff"] = fbx_metadata_diff(base / fbx_rel, target)

    a_rep = json.loads((base / "paperbomb_report.json").read_text(encoding="utf8"))
    b_path = (other / "paperbomb_report.json") if other else LIVE["paperbomb_report.json"]
    b_rep = json.loads(b_path.read_text(encoding="utf8")) if b_path.is_file() else {}
    measured = {}
    for key in MEASURED:
        if a_rep.get(key) != b_rep.get(key):
            measured[key] = {"baseline": a_rep.get(key), "now": b_rep.get(key)}
    ga, gb = a_rep.get("gates") or {}, b_rep.get("gates") or {}
    gate_diff = {k: [ga.get(k), gb.get(k)] for k in set(ga) | set(gb) if ga.get(k) != gb.get(k)}
    sa = {s["name"]: s["position_mm"] for s in (a_rep.get("sockets") or [])}
    sb = {s["name"]: s["position_mm"] for s in (b_rep.get("sockets") or [])}
    socket_diff = {k: [sa.get(k), sb.get(k)] for k in set(sa) | set(sb) if sa.get(k) != sb.get(k)}
    result["measurements"] = {"changed": measured, "gates_changed": gate_diff,
                              "sockets_changed": socket_diff,
                              "gates_all_now": gb.get("_all")}

    if not args.skip_renders:
        b_dir = (other / "renders") if other else LIVE_DIRS["renders"]
        result["renders"] = compare_renders(base / "renders", b_dir)

    identical = (not result["bytes"]["different"] and not result["bytes"]["missing"]
                 and not measured and not gate_diff and not socket_diff)
    result["identical"] = bool(identical)
    text = json.dumps(result, indent=2)
    out = Path(args.out) if args.out else (HERE / f"compare_{args.baseline}_vs_"
                                           f"{args.against or 'live'}.json")
    out.write_text(text, encoding="utf8")
    print(f"bytes: {len(result['bytes']['same'])} identical, "
          f"{len(result['bytes']['different'])} different, "
          f"{len(result['bytes']['missing'])} missing")
    for rel in result["bytes"]["different"][:20]:
        print("   DIFFERENT " + rel)
    for rel in result["bytes"]["missing"][:20]:
        print("   MISSING   " + rel)
    if measured:
        print("measurements changed: " + json.dumps(measured))
    if gate_diff:
        print("gates changed: " + json.dumps(gate_diff))
    if socket_diff:
        print("sockets changed: " + json.dumps(socket_diff))
    if result.get("fbx_diff"):
        fd = result["fbx_diff"]
        print(f"   ...the FBX differs in {fd.get('differing_bytes')} bytes across "
              f"{fd.get('run_count')} runs, fields {fd.get('fields')}; "
              f"metadata only: {fd.get('metadata_only')}")
    if result.get("renders"):
        worst = max(result["renders"].items(),
                    key=lambda kv: kv[1].get("mean_abs_diff_255", 999))
        print(f"renders: worst mean abs diff {worst[1].get('mean_abs_diff_255')} / 255 "
              f"on {worst[0]}")
    print(("IDENTICAL" if identical else "CHANGED") + f"  -> {out}")
    return 0 if identical else 1


if __name__ == "__main__":
    sys.exit(main())
