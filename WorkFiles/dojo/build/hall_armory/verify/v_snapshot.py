# VERIFIER: snapshot of DojoLab's Content / Config / uproject (size + mtime for all, md5 for L_Dojo, configs, uproject)
import hashlib, json, os, sys
P = r"C:/Users/Cody/Documents/Unreal Projects/DojoLab"
out = {"files": {}, "md5": {}}
for sub in ("Content", "Config", "Plugins"):
    for dp, dn, fn in os.walk(os.path.join(P, sub)):
        for f in fn:
            p = os.path.join(dp, f); st = os.stat(p)
            out["files"][os.path.relpath(p, P)] = [st.st_size, int(st.st_mtime)]
for rel in ["Content/Dojo/Maps/L_Dojo.umap", "DojoLab.uproject", "Saved/Config/WindowsEditor/GameUserSettings.ini"] + \
           [os.path.join("Config", f) for f in os.listdir(os.path.join(P, "Config")) if f.endswith(".ini")]:
    p = os.path.join(P, rel)
    if os.path.exists(p):
        out["md5"][rel] = hashlib.md5(open(p, "rb").read()).hexdigest()
json.dump(out, open(sys.argv[1], "w"), indent=0)
print(len(out["files"]), out["md5"])
