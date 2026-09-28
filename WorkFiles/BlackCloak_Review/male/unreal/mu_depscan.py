# Crude read-only dependency closure over uasset name tables (strings "/Game/..." and other mount points).
import os, re, sys, json
CONTENT = r"C:/Users/Cody/Documents/Unreal Projects/DemoGame_1/Content"
seeds = sys.argv[1:]
pat = re.compile(rb"(/[A-Za-z0-9_]+(?:/[A-Za-z0-9_\-\. ]+)+)\x00")
seen = {}; other = set(); scripts = set(); missing = set()
todo = list(seeds)
def pkg_file(p):
    rel = p[len("/Game/"):]
    for ext in (".uasset", ".umap"):
        f = os.path.join(CONTENT, rel + ext)
        if os.path.exists(f): return f
    return None
while todo:
    p = todo.pop()
    if p in seen: continue
    f = pkg_file(p)
    if not f: missing.add(p); seen[p] = None; continue
    seen[p] = f
    data = open(f, "rb").read()
    for m in pat.finditer(data):
        s = m.group(1).decode("latin1")
        s = s.split(".")[0]
        if s.startswith("/Game/"):
            if s not in seen: todo.append(s)
        elif s.startswith("/Script/"): scripts.add(s)
        else: other.add(s)
files = {p: f for p, f in seen.items() if f}
tot = sum(os.path.getsize(f) for f in files.values())
out = {"seeds": seeds, "packages": sorted(files), "missing": sorted(missing), "script_modules": sorted(scripts),
       "other_mounts": sorted(other), "total_bytes": tot}
json.dump(out, open(sys.stdout.fileno(), "w", closefd=False), indent=1)
