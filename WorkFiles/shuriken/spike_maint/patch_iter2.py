"""Iteration 2 patch (spike maintenance, 3.8.1): the speck / pit damping on a bar's SIDE faces (+-Y) only.

Measured (spike_maint scratch builds smA / smB, coat_interior_metrics + render dark_dots): damping the specks on all
four faces (x0.35 or x0.60) also strips the top-view coat's fine dark texture (0.0003 / 0.0008 against the stars'
0.0025-0.0034 and the reference's 0.0028); damping only the +-Y faces keeps it (0.0032) and clears the hero side face
(0 dots / 10k px at 30 %)."""
from pathlib import Path

root = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken")
s = ""
name = ""


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:90], s.count(old))
    s = s.replace(old, new)


name = "material.py"
p = root / "shuriken_lib" / name
s = p.read_text(encoding="utf-8")
rep('''    specks      (3.8.1) the dirt specks and the pits at BAR_SPECK_SCALE / BAR_PIT_SCALE of the plate forms':
                on the hero's side face - seen nearly face-on at ~10 px/mm, where a star's plate is
                foreshortened to half - the 0.12-0.3 mm specks (50 % darker) rendered as round 2 px black
                pepper (8.3 dots / 10k px against the stars' plates' 0.03-0.08 and the reference's 0.74).
                A bar is C4 and seen from every side in the game, so the damping is on all four faces''',
    '''    specks      (3.8.1) on the bar's SIDE faces (the +-Y pair, ``side``) the dirt specks and the pits are at
                BAR_SPECK_SCALE / BAR_PIT_SCALE of the plate forms'.  The hero sees a side face nearly
                face-on at ~10 px/mm (a star's plate is foreshortened to half), where the 0.12-0.3 mm
                specks (50 % darker) rendered as round 2 px black pepper: 8.3 dots / 10k px against the
                stars' plates' 0.03-0.08 and the reference's 0.74 (the review named the pits; damping the
                pits alone moved it to 7.6).  The +-Z faces keep the stars' specks: the same specks, seen in
                the top view at 6.9 px/mm, ARE the coat's fine dark texture there (0.0030, stars 0.0025-
                0.0034, reference 0.0028), and damping all four faces cut it to 0.0003 (x0.35) / 0.0008
                (x0.60).  The faces of a C4 bar differ only in how much sub-millimetre dirt they carry''')
rep('''BAR_PIT_SCALE = 0.33                   # 3.8.1: a bar's pits at a third of the plate forms' (colour, roughness, bump)
BAR_SPECK_SCALE = 0.35                 # 3.8.1: a bar's dirt specks darken at this fraction of the plate forms' SPECK''',
    '''BAR_PIT_SCALE = 0.33                   # 3.8.1: a bar's SIDE-face pits at a third of the plate forms' (colour, roughness, bump)
BAR_SPECK_SCALE = 0.35                 # 3.8.1: a bar's SIDE-face dirt specks darken at this fraction of SPECK["darken"]''')
rep('''    pit_k = t.mix_f(mode, 1.0, BAR_PIT_SCALE)                                 # 1 exactly on the plate forms''',
    '''    pit_k = t.mix_f(side, 1.0, BAR_PIT_SCALE)          # a bar's +-Y faces only; 1 exactly on the plate forms''')
rep('''    specks = t.math("MULTIPLY", specks, t.mix_f(mode, 1.0, BAR_SPECK_SCALE))    # 1 exactly on the plate forms''',
    '''    specks = t.math("MULTIPLY", specks, t.mix_f(side, 1.0, BAR_SPECK_SCALE))    # +-Y faces; 1 on the plate forms''')
p.write_text(s, encoding="utf-8")

name = "build_spike.py"
p = root / name
s = p.read_text(encoding="utf-8")
rep('''        "specks_and_pits": ("3.8.1: the dirt specks at BAR_SPECK_SCALE (0.35) and the pits at BAR_PIT_SCALE (0.33) of the "
                            "stars'. The hero sees a bar's side face nearly face-on at ~10 px/mm (a star's plate is "
                            "foreshortened to half), where the 0.12-0.3 mm specks read as round 2 px black pepper: 8.3 "
                            "dots / 10k px at 30 % darker, now 0.0 (stars' plates 0.03-0.08, the reference 0.74). The "
                            "review named the pits; a dot-by-dot look showed round BC dots (the specks), and damping the "
                            "pits alone moved 8.3 to 7.6. All four faces get the damping: a C4 bar is seen from every "
                            "side in the game."),''',
    '''        "specks_and_pits": ("3.8.1: on the two SIDE faces (+-Y) the dirt specks at BAR_SPECK_SCALE (0.35) and the pits "
                            "at BAR_PIT_SCALE (0.33) of the stars'. The hero sees a side face nearly face-on at ~10 "
                            "px/mm (a star's plate is foreshortened to half), where the 0.12-0.3 mm specks read as round "
                            "2 px black pepper: 8.3 dots / 10k px at 30 % darker, now 0.0 (stars' plates 0.03-0.08, the "
                            "reference 0.74). The review named the pits; a dot-by-dot look showed round colour dots (the "
                            "specks), and damping the pits alone moved 8.3 to 7.6. The +-Z faces keep the stars' specks: "
                            "seen from above at 6.9 px/mm they ARE the coat's fine dark texture (0.0032; stars "
                            "0.0025-0.0034, reference 0.0028), which damping all four faces cut to 0.0003-0.0008 "
                            "(spike_maint scratch builds smA / smB)."),''')
p.write_text(s, encoding="utf-8")
print("iteration 2 patched")
