# SR-01 final realism judging (2026-10-16, read-only)

Images: the five renders in `review/r2/realism/` (fp_35cm, ads_eyepiece, tp_3m, hero_34, deployed_34). hero_34 and deployed_34 are re-renders from the final exports.
Judges: A and B ran as two separate Opus 5.5 subagents in parallel. Each saw only the five images, never the other judge's answer and never the earlier r2 verdicts.
Raw output: `review/r2/judges_final/realism_A.json` and `realism_B.json`.
Process note: the orchestrating session read the earlier r2 verdicts while the judges were running. The judges never saw them, so their independence holds.

## Verdicts (confidence 0-100 that the image is CG)

| Image | A | B | Earlier r2 (A / B) |
|---|---|---|---|
| fp_35cm | CG 93 | CG 93 | 90 / 90 |
| ads_eyepiece | CG 72 | CG 85 | 85 / 80 |
| tp_3m | CG 97 | CG 96 | 97 / 95 |
| hero_34 | CG 95 | CG 92 | 93 / 92 |
| deployed_34 | CG 96 | CG 93 | 92 / 92 |

Both judges call all 5 images CG; neither mistakes any of them for a photo. No image has become harder to call since the earlier r2 round. The only drop is ads_eyepiece for A (72), because that frame is almost entirely defocused.

## Remaining tells, merged A+B and ranked

Each count is the number of (judge, image) mentions. The maximum is 10 for a tell that could apply to every image.

| # | Tell | Part | Count | Class |
|---|---|---|---|---|
| 1 | Seamless grey studio backdrop: two blown elliptical light pools with a dark dome (tp_3m), a hard wall/floor seam (deployed_34, ads_eyepiece), and soft, directionless lighting | backdrop / lights | 10 | render rig |
| 2 | Olive paint is perfectly clean and uniform with a fine procedural noise: no edge wear, dust or handling marks, and the same tone on every panel | stock / chassis | 8 | material |
| 3 | Stepped, blocky rectangular shadow/reflection patches on the floor | floor | 6 | render rig |
| 4 | Faceted shading kinks and a notched, irregular ridge along the forend top edge and at the chassis-to-receiver step (hero_34 at about x1000-1060, y400-430) | stock forend / chassis | 4 | **geometry** |
| 5 | Weak contact shadows: the rifle floats, and the bipod feet and butt don't press into the floor | floor contact | 4 | render rig |
| 6 | Sterile scope: no markings, maker text, serials or magnification numbers; dial numerals tiny | scope tube / turrets | 4 | material |
| 7 | Even monochrome path-tracer grain and a too-even, Gaussian-like defocus | whole frame / DOF | 4 | render rig |
| 8 | Eyepiece shows no sight picture, reticle or exit pupil, only a black disc with one round grey highlight (2 tells from each judge) | scope eyepiece | 2 | render rig |
| 9 | Bolt is mirror chrome with no machining marks, oil film or carbon | bolt body | 3 | material |
| 10 | Cheek riser and buttpad read as primitive boxes with hard, boolean-like joins | buttstock | 3 | **geometry** |
| 11 | Objective lens shows a pure black interior with one clean crescent highlight and no coating tint | scope objective | 2 | render rig (could also be the lens material) |
| 12 | Bolt knob is a plain sphere on a cylinder: no taper or texture | bolt handle | 2 | **geometry** |
| 13 | Magazine is a plain box with two lines and no baseplate or follower detail | magazine | 2 | **geometry** |
| 14 | Grip stipple reads as bump-only noise that stops abruptly at clean edges | pistol grip | 2 | material |
| 15 | Lower bipod legs are bright, clean, ribbed chrome | bipod legs | 2 | material |
| 16 | Bipod legs are plain cylinders with no lock hardware or springs | bipod | 1 | geometry |
| 17 | Barrel is a perfect cylinder with a can-like muzzle device and no crown detail | barrel / muzzle | 1 | geometry |
| 18 | Eyepiece rim has no visible rubber eyecup ridge | eyepiece | 1 | geometry |
| 19 | Barrel reflection shows no micro-scratches or dust | barrel | 1 | material (B tagged it render rig) |

## Hand-off for the gun chat, by fix type

- **Render rig only (no re-export needed). Biggest win, about half of all mentions:**
  - Replace the cyc and its two hot spots with an HDRI or a proper cove studio.
  - Fix the stepped floor shadows. They persist in all three wide shots, including the re-rendered hero_34 and deployed_34. Likely causes are the shadow-catcher or denoiser, or too few samples.
  - Add contact occlusion under the feet and butt.
  - Use more samples or a denoiser on the defocused areas.
  - Render a real sight picture with a reticle for ADS, and add coating tint and reflections to the objective glass.
- **Material / paint (texture work, re-export of the textures):**
  - Edge wear, dust and roughness variation on the olive chassis.
  - Dull the chrome bolt and bipod legs and give them machining marks.
  - Generic scope markings (no brands).
  - A moulded stipple on the grip instead of bump-only noise.
- **Geometry (needs a generator change):**
  - The faceted shading and the notched ridge on the forend top edge and at the chassis-to-receiver step. This is the only geometry tell carried over from the earlier round.
  - Boxy cheek riser and buttpad.
  - Tapered or textured bolt knob.
  - Magazine baseplate detail.
  - Lower priority: bipod lock hardware, muzzle crown, eyecup ridge.

## Changes since the earlier r2 verdicts (cheaper model, pre-fix renders)

- **Gone:** the wobbly, jagged lower handguard edge near the muzzle in deployed_34, which both earlier judges cited, is no longer mentioned. The fix appears to have worked.
- **Still there:** the notched forend top edge in hero_34 (both judges, then and now), the stepped floor shadows (all three wide shots), the clean uniform paint, the absent eyepiece optics and the cyc light pools.
- **Newly named** (more likely the stricter judges than a regression): the mirror-chrome bipod legs, the sphere bolt knob, the plain box magazine, the boxy cheek riser and buttpad, the sterile scope markings, and weak contact shadows (the earlier A mentioned this once).
- **Not re-checked:** the earlier rounds also judged scope_close, close_action_right and close_stock_right, citing the faceted turret knurl, the faceted trigger, and specks near the magazine catch. Those images are not in the final set, so these tells were not re-judged.
- **Verdicts:** confidence is flat to slightly higher; every image is still called CG.

## Note on tell 6 (owner)

Maker text, serials and brand marks are NOT allowed on any shipped asset (IP rules; only generic marks such as safety letters, rail numbers and the approved turret ticks/numerals). Ignore that part of tell 6; at most add more generic magnification/turret graduations.
