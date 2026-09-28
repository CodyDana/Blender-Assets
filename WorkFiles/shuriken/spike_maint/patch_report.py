"""One-off source patch (spike maintenance, 3.8.1): bar-worded measured.mass_gate (bar.py) and the spike's
report text (build_spike.py: physics figure, LOD1 note, style / gate / gap text)."""
from pathlib import Path

P = Path(r"C:\Users\Cody\Desktop\Blender_Projects\Scripts\shuriken")
s = ""
name = ""


def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:90], s.count(old))
    s = s.replace(old, new)


# ---------------------------------------------------------------- bar.py
name = "bar.py"
p = P / "shuriken_lib" / name
s = p.read_text(encoding="utf-8")
rep('''    masses = mass_figures(volume, plain["volume_mm3"] * MM ** 3, spec)''',
    '''    masses = mass_figures(volume, plain["volume_mm3"] * MM ** 3, spec)
    # 3.8.1 (geometry review): bar wording - the plate text ('outline x thickness', 'knife grind') does not apply
    masses["mass_gate"]["evaluated_on"] = ("the UN-GROUND bar: the same outline authored with square arrises and a "
                                           "sharp point (no arris round, no tip flat)")
    masses["mass_gate"]["why"] = ("the study mass gate proves the OUTLINE proportions match a real sourced object; the "
                                  "arris round and the tip flat are finishes, so the finished mass is reported, not gated")
    masses["grind_removes_note"] = "grind_removes_g on a bar = what the arris round takes off, less what the tip flat adds"''')
p.write_text(s, encoding="utf-8")

# ---------------------------------------------------------------- build_spike.py
name = "build_spike.py"
p = P / name
s = p.read_text(encoding="utf-8")
rep('''Style on a bar (the pack's restyled look, the same material read): the point is the cutting part,''',
    '''Maintenance 3.8.1 (after the spike's visual, geometry and Unreal reviews): the hero lamps follow the bar's
fitted camera distance and the bar is placed for the stars' lens shift (the backdrop matched the stars' only
there), the side faces lost their pepper (dirt specks and pits damped in bar mode), no polished line across
the shoulder, a satin-bright arris round with analytic normals (one worn edge line, no groove), a
deterministic 2048 x 512 UV layout (16 px gaps, 8 px border, every LOD on its island's exact map, the empty
texels filled), end-on section insets in the LOD strip, bar-worded report fields, one physics figure.

Style on a bar (the pack's restyled look, the same material read): the point is the cutting part,''')
rep('''    physics_mass_kg=0.037,          # study 4, Physics (the report's override is the finished mass)''',
    '''    physics_mass_kg=0.037,          # study 4, Physics table (reference only; the override is the finished mass)''')
start = s.index('''    report["lod_choice"] = {''')
end = s.index('''def _form():''')
s = s[:start] + '''    report["lod_choice"] = {
        "lod0": _LOD0.note, "lod1": _LOD1.note, "lod2": _LOD2.note,
        "bands": [list(lod.band) for lod in SPEC.lods],
        "why_so_few": ("study 2.5: 'at 1:25 the silhouette is nearly all straight line, so the triangles belong at the "
                       "point' - the faces and the rounds are single planar strips; the vertices sit at the point, "
                       "the tip flat and the two run-outs. Nothing is padded to reach a star's band."),
        "screen_sizes": (f"{report.get('lod_screen_sizes')} = the pack's 1.0 / 0.10 / 0.035 scaled by Unreal's bounds "
                         f"radius {UE_BOUNDS_RADIUS_MM:.3f} / 50 mm, so the switches stay at ~0.89 m and ~2.54 m"),
        "lod1_value": ("LOD1 (60 tris, the 2-chord round) is visually equal to LOD2 (28 tris) over its whole screen-size "
                       "range: at its 0.889 m switch a 1080p pixel covers 0.93 mm, so the 0.3 mm round is ~0.3 px wide "
                       "(it reaches 1 px only inside ~0.29 m), and plan and side silhouettes are identical on every LOD. "
                       "Three LODs are kept for the pack's uniform chain (same sidecar layout, screen-size scheme and "
                       "Unreal gates on every form); the 32 extra triangles are the whole cost. Shipping LOD1 as the "
                       "square-arris mesh, or two LODs, is the alternative if a buyer's budget asks for it."),
    }
    report["gallery"] = GALLERY
    report["style_on_a_bar"] = {
        "material": "M_Shuriken_Master, bar mode (shuriken_wear_axis = 1): the pack recipe, only its inputs switched",
        "coat": "the four faces, the tail facets and the butt: satin coat linear ~0.10, metallic 1.0, roughness 0.34, "
                "smears, dirt-filled clustered micro-scratches laid in each face's own plane, near-invisible pits, "
                "two sub-pixel rust specks (top face toward the point, bottom face toward the butt)",
        "specks_and_pits": ("3.8.1: the dirt specks at BAR_SPECK_SCALE (0.35) and the pits at BAR_PIT_SCALE (0.33) of the "
                            "stars'. The hero sees a bar's side face nearly face-on at ~10 px/mm (a star's plate is "
                            "foreshortened to half), where the 0.12-0.3 mm specks read as round 2 px black pepper: 8.3 "
                            "dots / 10k px at 30 % darker, now 0.0 (stars' plates 0.03-0.08, the reference 0.74). The "
                            "review named the pits; a dot-by-dot look showed round BC dots (the specks), and damping the "
                            "pits alone moved 8.3 to 7.6. All four faces get the damping: a C4 bar is seen from every "
                            "side in the game."),
        "arrises": ("0.3 mm round (4 chords at LOD0 with analytic arc normals: tangent-continuous with both faces), worn "
                    "satin-bright steel (BAR_ROUND_ROUGHNESS 0.46; polished, its middle mirrored the dark sky and the "
                    "camera-facing arris read as two lines with a dark groove: profile peaks 0.85 / 0.71 around a 0.33 "
                    "dip, now 0.89 / 0.68 around 0.54, the top face's own value); a worn polished band on the faces "
                    "along it that widens from 0.08 mm at the butt to 0.30 mm toward the point, nicks chipped into the "
                    "faces along it, more of them toward the point"),
        "point": ("ground bare steel, the stars' two-finish grind: polished along the four ridges (the point's cutting "
                  "edges, the pack's 0.7 mm band) and over the last 10 mm to the 0.15 mm tip flat, satin toward the "
                  "grind line. The brief asked for 'its four facets polished'; polished over the full 25 mm they "
                  "rendered as a white arrowhead (WorkFiles/shuriken/spike/iteration/polished_*), the look the pass-2 "
                  "review rejected on the stars' tips, so the point carries the same grind polish as a star's point "
                  "(the visual review endorsed this). 3.8.1: the shoulder (the face-to-facet edge at x = 125 mm, a "
                  "173 deg edge, not a cutting edge) is no longer a grind line: no worn band or nicks across it, so "
                  "the faces end in a plain change of finish, coat to satin grind, not a white frame"),
        "wear": "along the long axis toward the point (nick density, the arris band, the tip polish), not by radius",
        "gallery": ("hero: the object is turned 40 deg about Z and slid on the floor (the hero only) so its framing needs "
                    "the anchor forms' lens shift, and the hero lamps are scaled about the origin by the fitted camera "
                    "distance / 0.2157 m (sizes x s, power x s^2: same directions, solid angles and radiance) - the "
                    "camera, world and floor are unchanged, and the backdrop now matches the stars' at every fixed "
                    "frame point; top view unturned at the pack's common scale; LOD strip stacked, each LOD with an "
                    "end-on x5 section of its butt end showing the 4 / 2 / 0-chord round"),
        "gate_adaptations": [
            "hero_plate / top_plate: a bar reads its COAT pixels (up-facing coat faces, what a star's plate is); the "
            "whole object is reported beside it (render_gates.*.whole_object)",
            "pack_consistency: the spike's coat pixels against PACK_COAT_ANCHOR (the anchor forms' own plate pixels); "
            "its whole-object figures are information (pack_consistency.bar_whole_object)",
            "3.8.1: the spike's hero SIDE FACES (mask red, not ground) against PACK_WALL_ANCHOR (the anchor forms' hero "
            "wall p50, 0.2678) within 0.05 (pack_consistency.bar_walls_vs_wall_anchor), and render gate hero_bar_walls: "
            "isolated dark dots on the side faces <= 1.0 per 10k px at 30 % darker than the local median",
            "3.8.1, every form: the hero backdrop at 12 fixed frame points within the anchor forms' range +- 0.05 "
            "(pack_consistency.backdrop)",
        ],
    }
    report["texture_layout"] = {
        "maps": "T_Shuriken_Spike_BC / _ORM / _N at 2048 x 512 (the stars' are 2048 x 2048)",
        "why": ("four 150 mm strips filled 14 % of a 2048 square; at the same texel density (~135 px/cm) they fill 55 % "
                "of 2048 x 512 (a quarter of the memory). Non-square power-of-two maps import, mip and stream normally "
                "in Unreal"),
        "layout": ("shuriken_lib.bar.bar_uv_layout: deterministic, no packer; every side strip reserves the full "
                   "+-3 mm section, 16 px between islands, 8 px to the border; texels outside the islands + the 16 px "
                   "bake margin carry the covered texels' mean (BC, ORM) and a flat normal, so mips and wrap never pull "
                   "black into the edge texels"),
    }
    physics = report.get("physics") or {}
    exact = physics.get("mass_kg_override_exact")
    if exact is not None:
        physics["mass_kg_override"] = round(exact, 4)
        physics["decision"] = (f"ONE figure: {round(exact, 4)} kg, the finished LOD0 (the pack rule since the knife-grind "
                               "pass: the physics override is the finished mass). The study 4 table's 0.037 kg is the "
                               "sourced object's typical mass, listed for reference only; the outline is 35.3 g (1.7 g "
                               "under the sourced 37 g, inside the gate, see mass_check_spike.choice). Stated to 0.1 g "
                               "because rounding to the gram (0.035) would drop 0.3 g. Set it on the StaticMeshComponent's "
                               "Body Instance in the throwing Blueprint and state 35.3 g in the Fab description: the "
                               "sidecar has no mass field (Scripts/pipeline; adding one is a pipeline feature, not a bug "
                               "this maintenance may fix)")
    gaps = []
    for gap in report["known_gaps"]:
        if gap.startswith("LOD0 UV coverage is") or gap.startswith("Physics: the Mass in KG override") \\
                or gap.startswith("The baked maps are 2048 px per form") or gap.startswith("Knife grind (style pass 2)"):
            continue
        gaps.append(gap)
    uv = report.get("uv") or {}
    gaps = [
        "The Unreal side has no M_Shuriken_Master / MI_Shuriken_Blackened asset yet (pack-wide): the validation import "
        "runs with import_materials=False, so the slot binds to WorldGridMaterial until the pack's material is built "
        "and the three maps are assigned.",
    ] + gaps + [
        f"UV: a deterministic layout on 2048 x 512 maps covers {uv.get('uv_square_coverage', 0) * 100:.1f} % at "
        f"{uv.get('px_per_cm', 0):.1f} px/cm (see texture_layout); the pack atlas pass may still re-pack every form.",
        f"Physics: the Mass in KG override ({physics.get('mass_kg_override')} kg, the finished LOD0; study 4 table "
        f"{SPEC.physics_mass_kg} kg for reference) is recorded here only; it has to be set on the component in the "
        "throwing Blueprint (see physics.applies / physics.decision).",
        "Tail taper (20 mm to 3 mm) is the study's ESTIMATE, kept (see mass_check_spike.choice); the 0.3 mm arris round "
        "and the grip distance are modelling estimates. No flight or cord hole (antique spikes sometimes carry one).",
        "The spike's LOD bands are its own (ceilings 150 / 100 / 48, no floor): study 4's 1,200-2,500 table is for stars; "
        "LOD1 is visually equal to LOD2 over its range (lod_choice.lod1_value).",
        "Pack consistency compares the spike like with like: its coat pixels (up-facing faces) against the anchor forms' "
        "plate pixels, its hero side faces against their walls; its whole-object hero statistics are reported, not "
        "gated (about half of a bar's hero silhouette is side face mirroring the floor).",
        "The LOD0 body faces and arris-round chords are single strips (smallest triangle angle ~0.06 deg, face aspect up "
        "to ~920): long, not degenerate; qa_check passes and Unreal keeps every triangle with Remove Degenerates on.",
    ]
    report["known_gaps"] = gaps


''' + s[end:]
p.write_text(s, encoding="utf-8")
print("patched bar.py measure wording and build_spike.py annotate")
