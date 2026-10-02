"""VERIFIER: snapshot DojoLab Content + Config + uproject (md5, size, mtime_ns) -> json; or diff two snapshots."""
import hashlib, json, os, sys
from pathlib import Path
P = Path("C:/Users/Cody/Documents/Unreal Projects/DojoLab")
if sys.argv[1] == "snap":
    out = {}
    for base in ("Content", "Config"):
        for dp, dn, fn in os.walk(P / base):
            for f in fn:
                p = Path(dp) / f
                st = p.stat()
                h = hashlib.md5()
                with open(p, "rb") as fh:
                    for b in iter(lambda: fh.read(1 << 22), b""):
                        h.update(b)
                out[str(p.relative_to(P)).replace("\\", "/")] = [h.hexdigest(), st.st_size, st.st_mtime_ns]
    st = (P / "DojoLab.uproject").stat()
    out["DojoLab.uproject"] = [hashlib.md5((P / "DojoLab.uproject").read_bytes()).hexdigest(), st.st_size, st.st_mtime_ns]
    Path(sys.argv[2]).write_text(json.dumps(out, indent=0), encoding="utf-8")
    print("files", len(out))
else:
    a, b = (json.loads(Path(x).read_text(encoding="utf-8")) for x in sys.argv[2:4])
    added = sorted(set(b) - set(a)); removed = sorted(set(a) - set(b))
    md5ch = sorted(k for k in set(a) & set(b) if a[k][0] != b[k][0])
    mtch = sorted(k for k in set(a) & set(b) if a[k][2] != b[k][2])
    r = {"a": sys.argv[2], "b": sys.argv[3], "n": [len(a), len(b)], "added": added, "removed": removed,
         "md5_changed": md5ch, "mtime_changed": mtch}
    print(json.dumps(r, indent=1))
