The barrel is now wider in the middle. At the same head width as your photo it measures 790 px across the belly against the photo's 785 (+0.6%), and the length-to-belly ratio is 1.014, the same as the photo's. Every t5 check was re-run on the exported FBX and passes (table below). The skirt now matches the brief's numbers, but in the close-up it still reads as soft scallops, so the judge may still mark item 2 down. The per-side ±5 px test passes on the body but not on the skirt ears.

**One deviation from the brief.** The traced barrel profile used 0.534 as the lip radius. The lip's actual outermost radius is 0.547. With 0.534 the first t6 build came out with the body a constant 7 px per side (1.8%) too narrow. With 0.547 the wood shortens 75.4 mm per half (not 91.2) and the uniform scale is 1.1075 (not 1.133). The final size still matches the brief: length 1.554 m, belly 1.5325 m, lip outline 1.212 m. A side effect is that 78 tacks per row would leave the in-row spacing too wide, so I used 81. That gives spacing of 1.089 and 1.062 tack diameters (gaps 4.4 and 3.1 mm); the brief's 78 aimed for 1.094 and 1.068.

**Silhouette against the photo** (`t6/silhouette_widths.json`, now with a summary section):
- **Body, rows 290–700:** each side is within 0 to 4 px of the photo once each outline is centred on its own body.
- **Raw per-side numbers:** about +5 px on the left and −10 px on the right. The photo's body sits 7.6 px left of its own head centre, which our symmetric drum can't follow.
- **Skirt rows:** these are still outside ±5. The worst spots are the top-left ear at rows 210–260 (−27 to +21 px) and the bottom-right at rows 710–750 (about −15 px).

**Skirt** (design units; real is 1.1075× larger):

| Item | Built |
|---|---|
| Lobes | 21 slits per head, narrow 115–131 mm alternating with wide 234–259 mm |
| Ears | 3 per head (either side of the −Z seam and the lobe on +Z), lip 47–56 mm off the wood; the ear hems sit higher so they stand out steeply |
| Other lobes | lip 12–19 mm off the wood |
| Slits | 45.6–67.8 mm along the sheet; one side rides 4.8 mm over the other, overlap 3–6 mm, 4–8 mm apart at the hem |
| Lip curl | 90–120° in the lobe middles, 246–295° near the slits |
| Root | 5 mm tangential tuck instead of the 12 mm step; gold starts at least 17 mm (real) below the root |
| Self-intersections | none in the exported mesh |

**Gold colour.** Your judge's suggested change (hue +6°, saturation ×0.7, 12% darker) rendered far too pale, (215, 199, 171). I tuned it against the renders instead and settled on hue +7°, saturation ×1.25, value ×0.575, with the grain streaks in the gold replaced by low-frequency mottling. Results:
- Mid-gold at the sample points is (181, 153, 111) against the judge's (186, 158, 115).
- The gold band measured the same way on both images is (174, 147, 108) against the photo's (172, 146, 107).
- Both are within ±8 per channel.
- The texture gold is now a dark mustard, (83, 62, 4), so it may look darker and more saturated in Unreal than in these renders.

**Checks on the exported FBX:**

| Check | Result |
|---|---|
| qa_check | 0 hard fails on all pieces and LODs |
| Triangles, drum | 109,944 / 54,972 / 27,485 (LOD0/1/2) |
| Triangles, stand | 2,648 / 1,324 / 662 |
| Triangles, stick | 840 / 420 / 210 |
| Collision hulls | every vertex inside |
| Tacks | 81 per row, 47.3 mm, offset 0.5 pitch, rows 0.83 d apart, outlines overlap 0.105 d, 0 domes intersecting |
| Pale hide above the band | 1.94 d |
| Band to gold start | 0.56 d (0.49–0.63 with the wave) |
| Band to lowest hem | 2.36 d |
| Felt to barrel | −0.29 to +0.14 mm |
| Wood seat to barrel | 2.92–3.13 mm |
| Drum vertices within 2 mm of wood | 0 |
| Ring gap to barrel | 2.9 mm |
| Post tops | 4 mm below the barrel; 17.6 mm vertical gap up to the drum mesh |
| Sticks | both re-solved, 0.5 mm contact, feet 0.5 mm above the plinth |
| Stand | footprint 1.30 × 1.63 m, height 0.81 m; drum centre 1.394 m above the stand base |
| Pavilion | drum top at +3.166, 84 mm under the +3.25 eave (the brief estimated about +3.03) |

**Other things you should know:**
- The drum's UV1 needed 8° Smart UV charts on LOD0 and LOD2 (12° on LOD1), so its lightmap is split into small charts. The build now falls back to a lightmap pack if 5° still overlaps.
- The skirt adds about 1,400 triangles to the drum (98,944 → 109,944 at LOD0).

Nothing is committed, and the Taiko lock is untouched. I didn't refresh `showcase/DojoKit_Taiko/` or write the BUILD_NOTES entry. My backup of the t5 script versions is in the session scratchpad (`t5_backup/`).

Files are in C:/Users/Cody/Desktop/Blender_Projects:
- **Scripts changed** (in `Scripts/dojo/props/taiko/`): `build_taiko.py`, `taiko_uv.py`, `make_taiko_textures.py`
- **Built outputs:**
  - `Assets/Dojo/Taiko.blend`
  - `Exports/DojoKit/Props/taiko/SM_DKP_Taiko_{Drum,Stand,Stick}.fbx`
  - `Exports/DojoKit/Props/taiko/Textures/T_DKP_Taiko_{Collar,Lacquer}_{BC,N,ORM}.png`
- **Build reports** (`WorkFiles/dojo/build/props/taiko/`): `measure.json`, `qa_report.json`, `export_report.json`, `layout_taiko.json`, `textures_report.json`
- **Round folder** (`WorkFiles/dojo/build/props/taiko/t6/`):
  - Comparison sheets: `silhouette_overlay.png`, `compare_tacks.png`, `compare_skirt.png`
  - Renders: `drum_front_standing(_photo).png`, `closeup_tack_band(_photo).png`, `closeup_skirt(_photo).png`, `set_34.png`, `closeup_saddle.png`, `stand_end_elevation.png`, `saddle_felt.png`, `silhouette_ours_refcam.png`
  - Measurements: `measure_t6.json`, `silhouette_widths.json`, `gold_sample_drum_front_standing_photo.json`, `ucx_cover.txt`
  - Scripts: `render_t6.py`, `measure_t6.py`, `compose_t6.py`, `compose_t6_tacks.py`, `gold_sample.py`, and `run_all_t6.sh`, which runs the whole chain in order and stops if qa_check fails