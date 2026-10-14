"""SR01 W2 judge fix round (one round): finish values and paint parameters edited in Scripts/guns/sniper.
Judges (two, independent, scratch/w2/judges.json): every black one charcoal; no paint micro-texture; no edge-driven
wear (draped blotches on the barrel / grip / butt instead); mirror-chrome bolt; primitive ball knob."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
S = ROOT / "Scripts" / "guns" / "sniper"


def edit(path, pairs):
    p = S / path
    s = p.read_text(encoding="utf-8")
    for a, b in pairs:
        if b in s and a not in s:
            continue                                  # already applied
        assert s.count(a) == 1, (path, a[:80])
        s = s.replace(a, b)
    p.write_text(s, encoding="utf-8")
    print("edited", path)


edit("sr_surface.py", [
    ('    "anod": {"metal": 0, "srgb": (50, 51, 54), "rough": (0.46, 0.58), "wear_srgb": (176, 178, 182)},',
     '    # (W2 judge fix round: "every black one charcoal") a cool blue-grey satin with a sheen: lighter, bluer, smoother\n'
     '    "anod": {"metal": 0, "srgb": (56, 58, 65), "rough": (0.34, 0.44), "wear_srgb": (176, 178, 184)},'),
    ('    "phos": {"metal": 0, "srgb": (56, 55, 53), "rough": (0.70, 0.80), "oiled": (0.55, 0.64),',
     '    # (fix round) a warmer, dead-flat crystalline grey (rougher than every other dark family)\n'
     '    "phos": {"metal": 0, "srgb": (62, 60, 56), "rough": (0.76, 0.86), "oiled": (0.62, 0.70),'),
    ('    "polymer": {"metal": 0, "srgb": (44, 44, 46), "rough": (0.52, 0.62), "rough_hand": 0.44},',
     '    "polymer": {"metal": 0, "srgb": (44, 44, 46), "rough": (0.56, 0.66), "rough_hand": 0.46},'),
    ('    "rubber": {"metal": 0, "srgb": (38, 38, 40), "rough": (0.82, 0.92)},',
     '    "rubber": {"metal": 0, "srgb": (38, 38, 40), "rough": (0.88, 0.96)},'),
    ('    "scope_anod": {"metal": 0, "srgb": (34, 34, 36), "rough": (0.40, 0.52), "wear_srgb": (170, 172, 176)},\n'
     '    "lens": {"metal": 0, "srgb": (14, 18, 24), "rough": (0.05, 0.08)},',
     '    # (fix round) a deeper gloss-black anodize (the scope\'s own sheen, not the rail\'s satin)\n'
     '    "scope_anod": {"metal": 0, "srgb": (30, 30, 33), "rough": (0.24, 0.34), "wear_srgb": (170, 172, 176)},\n'
     '    "lens": {"metal": 0, "srgb": (18, 16, 30), "rough": (0.03, 0.05)},          # a coated (violet) glossy black'),
    ('    "od": {"metal": 0, "srgb": (84, 85, 72), "rough": (0.58, 0.68), "rub_srgb": (104, 104, 92)},',
     '    "od": {"metal": 0, "srgb": (84, 85, 72), "rough": (0.56, 0.68), "rub_srgb": (120, 120, 106)},'),
])

edit("sr_paint.py", [
    ('        peel = PT.chunked(PT.fbm3, Pk, 0.85, 2, 131)                  # ceramic orange peel',
     '        peel = PT.chunked(PT.fbm3, Pk, 0.65, 2, 131)                  # ceramic orange peel'),
    ('        var = 1.0 + 0.035 * (v_lo[k] - 0.5) + 0.02 * (peel - 0.5) + 0.02 * (grain - 0.5)\n'
     '        col = base[None, :] * var[:, None]\n'
     '        r0, r1 = F["rough"]\n'
     '        r = r0 + (r1 - r0) * (0.45 + 0.25 * (v_lo[k] - 0.5) + 0.3 * (grain - 0.5)) + 0.04 * (peel - 0.5)\n'
     '        hh = 0.006 * (peel - 0.5) * 2.0 + 0.0025 * (grain - 0.5) * 2.0',
     '        # (W2 judge fix round) the peel visible in the normal map (+-14 um at 0.65 mm) and in the sheen (+-0.08 rough\n'
     '        # on its crests / valleys); the low-frequency colour / roughness clouds down to a trace (they read as blotches)\n'
     '        var = 1.0 + 0.012 * (v_lo[k] - 0.5) + 0.03 * (peel - 0.5) + 0.025 * (grain - 0.5)\n'
     '        col = base[None, :] * var[:, None]\n'
     '        r0, r1 = F["rough"]\n'
     '        r = r0 + (r1 - r0) * (0.45 + 0.08 * (v_lo[k] - 0.5) + 0.3 * (grain - 0.5)) + 0.16 * (peel - 0.5)\n'
     '        hh = 0.014 * (peel - 0.5) * 2.0 + 0.003 * (grain - 0.5) * 2.0'),
    ('        rb_w = 0.25 + 0.55 * PT.chunked(PT.fbm3, Pk, 6.0, 2, 134)\n'
     '        rub = PT.smoothstep(rb_w, rb_w * 0.25, dist_e[k]) * edge_fine[k] * expo[k] * \\\n'
     '            (0.35 + 0.65 * np.maximum(cz[k], pol)) * (0.5 + 0.5 * PT.smoothstep(0.3, 0.7, along[k]))\n'
     '        rub = np.clip(rub, 0, 1).astype(np.float32)\n'
     '        a_r = (0.75 * rub)[:, None]',
     '        # (fix round) every exposed edge rubbed (the judges saw none): wider, stronger, the broad edge field too\n'
     '        rb_w = 0.45 + 0.75 * PT.chunked(PT.fbm3, Pk, 6.0, 2, 134)\n'
     '        rub = PT.smoothstep(rb_w, rb_w * 0.2, dist_e[k]) * np.maximum(edge_fine[k], 0.6 * edge_broad[k]) * expo[k] * \\\n'
     '            (0.55 + 0.45 * np.maximum(cz[k], pol)) * (0.6 + 0.4 * PT.smoothstep(0.3, 0.7, along[k]))\n'
     '        rub = np.clip(1.3 * rub, 0, 1).astype(np.float32)\n'
     '        a_r = (0.9 * rub)[:, None]'),
    ('        width = (0.25 + 1.1 * wear * PT.chunked(PT.fbm3, Pk, 3.0, 2, 142)) * (0.5 + 0.5 * expo[k])\n'
     '        chip = (dist_e[k] < width) & (cfield > 0.86 - 0.22 * wear) & (edge_fine[k] > 0.2) & (expo[k] > 0.35)',
     '        width = (0.35 + 1.5 * wear * PT.chunked(PT.fbm3, Pk, 3.0, 2, 142)) * (0.5 + 0.5 * expo[k])\n'
     '        chip = (dist_e[k] < width) & (cfield > 0.82 - 0.26 * wear) & (edge_fine[k] > 0.2) & (expo[k] > 0.35)'),
    ('        col = col * (1.0 + 0.45 * rub)[:, None]\n        r = r - 0.10 * rub',
     '        col = col * (1.0 + 0.9 * rub)[:, None]                 # (fix round) crests rub to a lighter satin\n'
     '        r = r - 0.12 * rub'),
    ('        wl = (dist_e[k] < 0.22 + 0.25 * az[k]) & (dash > 0.86 - 0.18 * az[k]) & (edge_fine[k] > 0.35) & \\\n'
     '            (expo[k] > 0.5) & (az[k] > 0.15)',
     '        wl = (dist_e[k] < 0.25 + 0.30 * az[k]) & (dash > 0.82 - 0.22 * az[k]) & (edge_fine[k] > 0.35) & \\\n'
     '            (expo[k] > 0.5) & (az[k] > 0.10)'),
    ('        oil = PT.smoothstep(0.45, 0.75, PT.chunked(PT.fbm3, Pk, 12.0, 3, 61)) * (0.3 + 0.7 * oily)\n'
     '        o0, o1 = F["oiled"]\n'
     '        r = r * (1 - oil) + (o0 + (o1 - o0) * v_mid[k]) * oil\n'
     '        col *= (1.0 - 0.06 * oil)[:, None]',
     '        # (fix round: "a draped blotch on the barrel") a faint, broad oiled sheen only, no colour step\n'
     '        oil = 0.35 * PT.smoothstep(0.35, 0.85, PT.chunked(PT.fbm3, Pk, 40.0, 2, 61)) * (0.3 + 0.7 * oily)\n'
     '        o0, o1 = F["oiled"]\n'
     '        r = r * (1 - oil) + (o0 + (o1 - o0) * v_mid[k]) * oil'),
    ('        col = lin(F["srgb"])[None, :] * (1.0 + 0.06 * (v_mid[k] - 0.5) + 0.05 * (cry - 0.5))[:, None]',
     '        col = lin(F["srgb"])[None, :] * (1.0 + 0.02 * (v_mid[k] - 0.5) + 0.07 * (cry - 0.5))[:, None]'),
    ('        r = r0 + (r1 - r0) * (0.4 + 0.6 * lines) + 0.10 * streak',
     '        r = r0 + (r1 - r0) * (0.2 + 0.8 * lines) + 0.06 * streak'),
    ('        col *= (1.0 - 0.22 * streak)[:, None]                                    # oil / carbon streaks',
     '        col *= (1.0 - 0.12 * streak)[:, None]                                    # oil / carbon streaks'),
    ('    hz = zone_field(P, SS.POLISH) * (0.55 + 0.45 * PT.chunked(PT.fbm3, P, 6.0, 3, 70))',
     '    hz = zone_field(P, SS.POLISH) * (0.85 + 0.15 * PT.chunked(PT.fbm3, P, 6.0, 3, 70))   # (fix round: no mottle)'),
    ('        col = lin(F["srgb"])[None, :] * (1.0 + 0.04 * (v_lo[k] - 0.5) + 0.06 * (fine - 0.5))[:, None]',
     '        col = lin(F["srgb"])[None, :] * (1.0 + 0.015 * (v_lo[k] - 0.5) + 0.06 * (fine - 0.5))[:, None]'),
])
