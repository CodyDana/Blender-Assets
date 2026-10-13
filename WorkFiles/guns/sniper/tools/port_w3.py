"""SR01 W3: sniper-side copy of gunlib.drivers.rig_verify (read-only use of Scripts/guns/gunlib): relative imports made
absolute, a runner on sr_gun.CFG, and the B4 row reads the scope's Sight (the gun has none: no iron sights; plan 5 A4
replaces B4) instead of a gun Sight socket."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
src = ROOT / "Scripts/guns/gunlib/drivers/rig_verify.py"
dst = ROOT / "Scripts/guns/sniper/sr_rig_verify.py"
s = src.read_text(encoding="utf-8")
rep = [
    ('"""Rig + export gates on the EXPORTED bytes', '"""SR01 port (tools/port_w3.py; do not edit by hand) of gunlib.drivers.rig_verify. Rig + export gates on the EXPORTED bytes'),
    ("from .. import game as GM\nfrom .. import gateutil as GU\nfrom .. import qa_gun\nfrom .. import rig as RG\n",
     "import sys\n_H = Path(__file__).resolve()\nsys.path[:0] = [str(_H.parent), str(_H.parents[1]), str(_H.parents[2])]\nfrom gunlib import game as GM\nfrom gunlib import gateutil as GU\nfrom gunlib import qa_gun\nfrom gunlib import rig as RG\n"),
    ('    sg = next(s for s in side["sockets"] if s["name"] == "Sight")\n',
     '    sg = {"location_mm": "none on the gun (no iron sights): the scope attachment carries Sight (plan 5)"}\n'),
    ('                      f"{ns} sockets on their spec bones; Muzzle <= 0.5 mm and <= 0.05 deg off the bore; sight picture "\n                      "<= 0.5 px (55 deg ADS, 0.25 m eye relief, 2560 x 1440)",',
     '                      f"{ns} sockets on their spec bones; Muzzle <= 0.5 mm and <= 0.05 deg off the bore; sight line = "\n                      "the scope\'s A4 (Sight Z 57.6 +-0.2, parallel <= 0.05 deg; gates/scope_form.json)",'),
]
rep.append(("""                E = np.eye(4)
                E[:3, 3] = heads[pb.name]
                E = E @ bas.get(pb.name, np.eye(4))
""", """                E = _chain(pb.name, bas, heads, expect_bones)      # SR01: parents composed (ext under leg)
"""))
rep.append(("gate = GU.gate\n", """gate = GU.gate


def _chain(name, bas, heads, parents):
    \"\"\"SR01 port: the bone's expected armature-space pose matrix with its parents composed (identity rests):
    world_b = world_parent @ T(h_b) B_b T(-h_b); pose = world_b @ T(h_b). gunlib's flat form (T(h_b) B_b) is the same
    for bones whose parents do not move (every AR-01 / SMG bone); the bipod extensions ride the rotated legs.\"\"\"
    def T(h):
        M = np.eye(4)
        M[:3, 3] = h
        return M
    chain = []
    n = name
    while n is not None:
        chain.append(n)
        n = parents.get(n)
    W = np.eye(4)
    for b in reversed(chain):
        W = W @ T(heads[b]) @ bas.get(b, np.eye(4)) @ T(-heads[b])
    return W @ T(heads[name])
"""))
for a, b in rep:
    assert a in s, a[:70]
    s = s.replace(a, b)
s = s.replace("from pathlib import Path\n\nimport numpy as np\n", "from pathlib import Path\n\nimport numpy as np\n", 1)
s += '\n\nif __name__ == "__main__":\n    from sr_gun import CFG\n    main(CFG)\n'
dst.write_text(s, encoding="utf-8")
print("ported", src.name, "->", dst.name)
