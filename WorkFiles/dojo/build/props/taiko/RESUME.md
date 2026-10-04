# Taiko: paused 2026-10-04 (resume here)

On the user's request this is paused and on the todo list. The work: match the taiko to `References/Dojo/taiko_tacks_ref_user.webp`, then prepare it for Fab.

**Done:**
- tacks: two rows, uniform, offset half a pitch, glossy black;
- barrel bulge: traced, PASS in round 6;
- collar proportions: PASS in round 6;
- felt-lined tapered saddles;
- traced upper skirt;
- ring-handle plate, rivets and washer outline;
- drum LOD0 cut to about 59k triangles.
The stand research is in `stand/STAND_STUDY.md`.

**Open at the pause:** see `judge_r7/VERDICT_r7.md`.
- ring and pivot sit too high; metal too matte;
- lower-left skirt;
- tack rows still slightly short of the photo's nesting;
- wood grain: out of scope so far, ask the user.

**Fix round t8 was interrupted mid-build.** Its scripts are in `t8/`, and the build state on disk may be partial. Start by rebuilding from the current `Scripts/dojo/props/taiko/*.py` and re-measuring before anything else. Note that the pre-round-8 scripts are not separately backed up: `t8/_t7_scripts/` holds the t7 script copies.

**Next:**
1. Run fix rounds t8-t9 with the judge, using the workflow script `taiko-round7.js` pattern.
2. Re-fit the stand and judge it.
3. Fab prep: TaikoDrumSet UE project, captures, `WorkFiles/taiko_fab/FAB_LISTING.md`, a refresh of `showcase/DojoKit_Taiko/`, and a review against `FAB_PUBLISHING_STUDY.md`.

**State:** all changes are uncommitted in the main checkout (taiko scripts, `Assets/Dojo/Taiko.blend`, `Exports/DojoKit/Props/taiko/*`). The lock "Taiko" is held by the claude cardshop-worktree session.
