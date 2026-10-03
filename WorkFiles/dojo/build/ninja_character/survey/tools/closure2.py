"""DemoGame_1 -> DojoLab package closure from the package headers (import table = HARD, soft package list = SOFT), no editor.
Read-only on both projects. Writes one JSON."""
import hashlib, json, os, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from uimports import read, hard_packages

DEMO = r"C:\Users\Cody\Documents\Unreal Projects\DemoGame_1"
DOJO = r"C:\Users\Cody\Documents\Unreal Projects\DojoLab"
LFS = os.path.join(DEMO, ".git", "lfs", "objects")
PRIVATE = re.compile(r"PlayerFemale|Hiyuki|(^|/)2B(_|/|$)|_Private", re.I)
# owner rule 2026-10-02: NO jutsu voice-overs in DojoLab (or anywhere): the voice lines are never copied again. A jutsu
# data asset that still names one is copied only through the owner's sign-off (DojoLab's DA_Jutsu_* differ from
# DemoGame_1's since the voices_paper stage) and dj_ninja_setup.py step_novoice clears its StartVoice.
VOICE = re.compile(r"^/Game/Ninja/Audio/Voice/|SFX_Voice_", re.I)
MALE_ERA = "43fd6ce"
OVERRIDES = {  # package -> (LFS oid, why)
    "/Game/Ninja/Blueprints/BP_NinjaGasp": ("017e4018029f60d3c8099a0f23df67b7d97538432f79ea68f0d42b49aa15542b",
        "43fd6ce (= f9e6292): the male-era player; the working tree adds only the female catwalk walk tier (WalkAnimation A_Catwalk_Mocap, slowed WalkSpeeds)"),
    "/Game/Ninja/Blueprints/BP_NinjaVisual": ("5ea028e27eda24a366efd898d40ebb09b08ff23d0b12bd5d6fdd823a3d5a2f95",
        "43fd6ce: MetaHuman child actor = BP_MH_PlayerDefault + ABP_MH_NinjaBody, CloakMH tagged NinjaMHGarment; HEAD/working tree point at BP_MH_PlayerFemale (private, never copied)"),
}
FEATURE = [  # (regex, feature) - assets only the components the owner does not want now reference
    (r"^/Game/BareNinja_AnimSet/Animation/", "combat (UNinjaCombatComponent clips)"),
    (r"^/Game/Ninja/Animation/Combat/", "combat (throw clips)"),
    (r"^/Game/Ninja/Animation/Stance/", "stance (prone clips)"),
    (r"^/Game/Ninja/Animation/Loco/A_Loco_Evade", "air jump (front/back flip clips)"),
    (r"^/Game/Ninja/Animation/(Walk|Mocap)/", "catwalk (female, private reel) - never copied"),
    (r"^/Game/Ninja/Input/IA_(Attack|Block|Dodge|Kunai|Shunshin)", "combat input"),
    (r"^/Game/Ninja/Input/IA_LockOn", "lock-on input"),
    (r"^/Game/Ninja/Input/IA_FreeLook", "free-look input"),
    (r"^/Game/Ninja/Input/IA_Ninja(Crouch|Prone)", "stance input"),
]
ROOTS = ["/Game/Ninja/Blueprints/BP_NinjaGasp", "/Game/Ninja/Blueprints/BP_NinjaVisual", "/Game/Ninja/Input/IMC_NinjaGasp",
         "/Game/Ninja/Jutsu/DA_Jutsu_ShadowClone", "/Game/Ninja/Jutsu/DA_Jutsu_GreatFireball", "/Game/Ninja/Jutsu/DA_Jutsu_Summoning",
         "/Game/Ninja/Jutsu/DA_Jutsu_Chidori", "/Game/Ninja/Character/ABP_MH_NinjaBody", "/Game/Ninja/Character/Retarget/RTG_Manny_to_MH",
         "/Game/MetaHumans/MH_PlayerDefault/BP_MH_PlayerDefault", "/Game/Ninja/Cloak/SKM_BlackCloak_MH", "/Game/Ninja/Cloak/ABP_Cloak"]


def file_for(root, pkg):
    rel = pkg[len("/Game/"):]
    for ext in (".uasset", ".umap"):
        p = os.path.join(root, "Content", *rel.split("/")) + ext
        if os.path.isfile(p):
            return p
    return None


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def files_of(path):
    base = os.path.splitext(path)[0]
    return [path] + [base + e for e in (".uexp", ".ubulk", ".uptnl") if os.path.isfile(base + e)]


def feature_of(pkg):
    for rx, f in FEATURE:
        if re.search(rx, pkg):
            return f
    return None


def walk(skip_features):
    seen, parents, kinds = {}, defaultdict(set), {}
    todo = [(r, None, "root") for r in ROOTS]
    while todo:
        pkg, parent, kind = todo.pop()
        if parent:
            parents[pkg].add(parent)
            kinds[(parent, pkg)] = kind
        if pkg in seen:
            continue
        rec = {}
        seen[pkg] = rec
        if PRIVATE.search(pkg):
            rec["status"] = "PRIVATE_BLOCKED"; continue
        if VOICE.search(pkg):
            rec["status"] = "VOICE_BLOCKED"; continue
        feat = feature_of(pkg)
        if feat:
            rec["feature"] = feat
            if skip_features or "never copied" in feat:
                rec["status"] = "feature_not_ported"; continue
        if pkg in OVERRIDES:
            oid, why = OVERRIDES[pkg]
            src = os.path.join(LFS, oid[:2], oid[2:4], oid)
            rec["source"] = "git LFS blob of commit %s (%s)" % (MALE_ERA, why)
            rec["working_tree_file_sha256"] = sha(file_for(DEMO, pkg))
        else:
            src = file_for(DEMO, pkg)
            rec["source"] = "working tree"
        dst = file_for(DOJO, pkg)
        if not src:
            rec["status"] = "dojo_only" if dst else ("soft_missing_everywhere")
            continue
        info = read(src)
        hard = [h for h in hard_packages(info) if h != pkg]
        soft = sorted(set(info["soft_packages"]) - {pkg} - set(hard))
        rec["hard"] = [h for h in hard if h.startswith("/Game/")]
        rec["soft"] = [s for s in soft if s.startswith("/Game/")]
        rec["script_modules"] = sorted({h[len("/Script/"):] for h in hard if h.startswith("/Script/")})
        rec["plugin_content_hard"] = [h for h in hard if not h.startswith(("/Game/", "/Script/", "/Engine/"))]
        rec["plugin_content_soft"] = [s for s in soft if not s.startswith(("/Game/", "/Script/", "/Engine/"))]
        rec["engine_content"] = [h for h in hard + soft if h.startswith("/Engine/")]
        fl = files_of(src) if pkg not in OVERRIDES else [src]
        rec["files"] = [{"file": os.path.relpath(file_for(DEMO, pkg) if pkg in OVERRIDES else f, DEMO).replace("\\", "/"),
                         "sha256": sha(f), "bytes": os.path.getsize(f)} for f in fl]
        rec["sha256"] = rec["files"][0]["sha256"]
        rec["bytes"] = sum(x["bytes"] for x in rec["files"])
        if dst:
            rec["dojo_sha256"] = sha(dst)
            rec["status"] = "in_dojo_identical" if rec["dojo_sha256"] == rec["sha256"] else "in_dojo_DIFFERENT"
            continue  # DojoLab's own package: its references are already satisfied there
        rec["status"] = "copy"
        for h in rec["hard"]:
            todo.append((h, pkg, "hard"))
        for s in rec["soft"]:
            todo.append((s, pkg, "soft"))
    for pkg, rec in seen.items():
        rec["referenced_by"] = sorted("%s (%s)" % (p, kinds.get((p, pkg), "?")) for p in parents.get(pkg, ()))
    return seen


def hard_reach(P):
    seen, todo = set(), list(ROOTS)
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        r = P.get(p, {})
        if r.get("status") == "copy":
            todo += r.get("hard", [])
    return seen


def main():
    full = walk(skip_features=False)
    lean = walk(skip_features=True)
    hr = hard_reach(lean)
    for pkg, rec in full.items():
        rec["in_lean_closure"] = pkg in lean and lean[pkg].get("status") == "copy"
        rec["hard_reachable_lean"] = pkg in hr
        if rec.get("status") == "copy":
            rec["copy_class"] = ("core" if rec["in_lean_closure"] else "feature_only")
    out = {"roots": ROOTS, "overrides": {k: {"oid": v[0], "why": v[1]} for k, v in OVERRIDES.items()}, "packages": full}
    json.dump(out, open(sys.argv[1], "w"), indent=1)
    st = Counter(r["status"] for r in full.values())
    print("full statuses", dict(st))
    for cls in ("core", "feature_only"):
        ps = [p for p, r in full.items() if r.get("copy_class") == cls]
        print(cls, len(ps), "%.1f MB" % (sum(full[p]["bytes"] for p in ps) / 1e6),
              Counter("/".join(p.split("/")[:4]) for p in ps).most_common(30))
    core_soft_only = [p for p, r in full.items() if r.get("copy_class") == "core" and not r["hard_reachable_lean"]]
    print("core but only soft-reachable", len(core_soft_only), "%.1f MB" % (sum(full[p]["bytes"] for p in core_soft_only) / 1e6),
          Counter("/".join(p.split("/")[:4]) for p in core_soft_only).most_common(10))


if __name__ == "__main__":
    main()
