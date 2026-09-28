Retired from the build path on 2026-09-22 (rewind builder, round 1).

These are round 3's patch-based smoke bomb modules (strips laid as separate patches on a
sphere) and round 3's build script.  They are byte-identical to the round-3 snapshot in
WorkFiles/smokebomb/round3_2026-09-21/Scripts_props/ and nothing imports them any more:
Scripts/props/build_smoke_bomb.py now builds the ball as ONE wound tape from
props_lib.smokebomb_wind + smokebomb_tape + smokebomb_ball + smokebomb_look.

This folder is not a package on sys.path; kept only as the record of what was retired.
smokebomb_spec.py here is round 3's spec (props_lib/smokebomb_spec.py was rewritten).
