"""Gun deny list: tokenised matcher prototype + negative tests (GUN_BUILDING_STUDY 4.9, review finding R3).

Why tokens and not \\b: in Python regex '_' and digits are word characters, so r'\\bak\\b' misses SM_AK47,
T_UMP45_BC and MI_M4A1_Metal. Names are split on '_', '-', spaces, case changes and letter/digit changes, and a deny
term (itself tokenised: 'm4' -> ['m', '4'], 'desert eagle' -> ['desert', 'eagle']) hits only as a run of whole
consecutive tokens. Our own codes (AR01, SMG01, HP01...) never form a deny run.

Also shows the qa_check DENY_WORDS quirk (side finding, not fixed here: Scripts/pipeline is out of scope):
'(?<![A-Za-z0-9])ea(?![a-z])' is compiled with re.IGNORECASE, so the lookahead rejects uppercase letters too and
SM_EaBlade does NOT hit, although the comment in qa_check.py says it should.

Run: py -3 -B WorkFiles/studies/guns/repo_audit/deny_tokens_test.py   (exit 0 = all expectations met)
"""
import re
import sys

TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")

# Asset-name scan only (prose like fastener sizes is not scanned; write sizes as "4 mm thread").
GUN_DENY = (
    "ak", "akm", "ak47", "ak74", "kalashnikov", "rpk", "pkm", "svd", "dragunov",
    "m4", "m4a1", "m16", "ar15", "armalite", "colt", "m249", "minimi", "m60",
    "ump", "mp5", "mp7", "hk", "heckler", "koch", "fn", "scar", "p90", "uzi", "galil", "famas", "steyr", "aug",
    "glock", "beretta", "sig", "sauer", "desert eagle", "deagle", "magnum research",
    "mossberg", "remington", "benelli", "barrett", "awm", "accuracy international", "magpul", "mlok", "m lok",
)


def tokens(name: str):
    return [t.lower() for t in TOKEN_RE.findall(name)]


DENY_SEQS = [(term, [t for part in term.split() for t in tokens(part)]) for term in GUN_DENY]


def hits(name: str):
    tk = tokens(name)
    found = []
    for term, seq in DENY_SEQS:
        n = len(seq)
        if any(tk[i:i + n] == seq for i in range(len(tk) - n + 1)):
            found.append(term)
    return found


MUST_HIT = ["SM_AK47", "T_UMP45_BC", "SK_M4A1", "SM_AR15", "SM_AR-15", "MI_M4A1_Metal", "SK_Glock17", "SM_Mp5",
            "T_DesertEagle_BC", "SM_AKMag", "SM_AWM01"]
MUST_PASS = ["Bump", "Pump", "SM_Mag_Break", "SupportHand", "SM_AR01", "SK_SMG01", "SM_HP01", "SM_CB01", "SM_SR01",
             "SM_LR01", "T_AR01_Metal_BC", "SM_Att_Scope_Red", "MagDraw", "SM_Shotgun_Pump", "A_AR01_Charge",
             "SK_AR01_Skeleton", "SM_Stake", "Sigil", "T_AR01_Masks"]


def main() -> int:
    bad = 0
    for name in MUST_HIT:
        h = hits(name)
        print(f"hit  {name:22s} {h}")
        bad += not h
    for name in MUST_PASS:
        h = hits(name)
        print(f"pass {name:22s} {h}")
        bad += bool(h)
    qa_ea = re.compile(r"(?<![A-Za-z0-9])ea(?![a-z])", re.IGNORECASE)
    for name in ("SM_EA2", "SM_EaBlade", "SM_Sea_Blade", "SM_Feather"):
        print(f"qa_check 'ea' rule on {name}: {bool(qa_ea.search(name))}")
    print("FAILURES:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
