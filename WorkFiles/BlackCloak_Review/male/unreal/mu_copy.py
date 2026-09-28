import json, os, hashlib, shutil, glob
SRC = r"C:/Users/Cody/Documents/Unreal Projects/DemoGame_1/Content"
DST = r"C:/Users/Cody/Desktop/Blender_Projects/WorkFiles/BlackCloak_Review/unreal/CloakReview/Content"
d = json.load(open("mu_deps.json"))
rows = []
for p in d["packages"]:
    rel = p[len("/Game/"):]
    for f in glob.glob(os.path.join(SRC, rel) + ".*"):
        stem_ok = os.path.splitext(os.path.basename(f))[0] == os.path.basename(rel)
        if not stem_ok: continue
        r = os.path.relpath(f, SRC).replace("\\", "/")
        h = hashlib.sha256(open(f, "rb").read()).hexdigest()
        out = os.path.join(DST, r)
        if os.path.exists(out):
            h2 = hashlib.sha256(open(out, "rb").read()).hexdigest()
            if h2 != h: raise SystemExit("EXISTS WITH DIFFERENT CONTENT: " + out)
        else:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copy2(f, out)
            h2 = hashlib.sha256(open(out, "rb").read()).hexdigest()
        assert h == h2
        rows.append({"package": p, "file": r, "bytes": os.path.getsize(f), "sha256": h})
json.dump({"source_content": SRC, "dest_content": DST, "files": rows}, open("mu_copied_assets.json", "w"), indent=1)
print(len(rows), sum(r["bytes"] for r in rows) / 1e6, "MB")
for r in rows:
    if "Ninja" in r["file"] or "BodyMesh" in r["file"] or "PHYS" in r["file"]: print(r["sha256"][:16], r["file"])
