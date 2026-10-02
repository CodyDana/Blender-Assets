# VERIFIER: manifest sha256 vs Exports (read-only)
import json, hashlib, os, sys
R = r"C:/Users/Cody/Desktop/Blender_Projects"
UE = r"C:/Users/Cody/Documents/Unreal Projects"
m = json.load(open(R + "/WorkFiles/shared/armory_hall/manifest.json"))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()
out = {"fbx": {}, "item_fbx": {}, "site": {}, "textures_png": {}, "textures_uasset": {}, "lfs_pointer": []}
bad = []
for sec, key in (("fbx", "fbx"), ("item_fbx", "item_fbx"), ("site_fbx_dojolab_only", "site")):
    for n, e in m[sec].items():
        p = os.path.join(R, e["path"])
        if not os.path.exists(p):
            out[key][n] = "MISSING"; bad.append((sec, n, "missing")); continue
        s = sha(p)
        sz = os.path.getsize(p)
        if sz < 300: out["lfs_pointer"].append(n)
        ok = s == e["sha256"] and (e.get("bytes") in (None, sz))
        out[key][n] = {"ok": ok, "sha": s[:12], "want": e["sha256"][:12], "bytes": sz}
        if not ok: bad.append((sec, n, s[:12], e["sha256"][:12]))
for n, e in m["textures"].items():
    if "png" in e:
        p = os.path.join(R, e["png"])
        ok = os.path.exists(p) and sha(p) == e["png_sha256"]
        out["textures_png"][n] = ok
        if not ok: bad.append(("tex_png", n))
    if "armorylab_uasset_sha256" in e:
        # find the DojoLab copy
        hits = []
        for root in (UE + "/DojoLab/Content/ArmoryKit", UE + "/DojoLab/Content/NinjaPack"):
            for dp, dn, fn in os.walk(root):
                if n + ".uasset" in fn: hits.append(os.path.join(dp, n + ".uasset"))
        ok = bool(hits) and all(sha(h) == e["armorylab_uasset_sha256"] for h in hits)
        out["textures_uasset"][n] = {"ok": ok, "copies": len(hits)}
        if not ok: bad.append(("tex_uasset", n, len(hits)))
# shell FBX listed in hall_shell_layout
hs = json.load(open(R + "/WorkFiles/shared/armory_hall/hall_shell_layout.json"))
out["n_fbx"] = len(m["fbx"]); out["bad"] = bad
json.dump(out, open(R + "/WorkFiles/dojo/build/hall_armory/verify/sha_check.json", "w"), indent=1)
print("fbx", len(m["fbx"]), "item", len(m["item_fbx"]), "site", len(m["site_fbx_dojolab_only"]), "tex", len(m["textures"]))
print("bad", bad); print("lfs_pointer", out["lfs_pointer"])
print("hall_shell keys", list(hs.keys()))
