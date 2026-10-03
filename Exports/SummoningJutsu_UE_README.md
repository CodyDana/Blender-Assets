# SummoningJutsu — Unreal Import Notes

## Files
- `SM_SummoningJutsu.fbx` — 4×4m decal plane (2 tris), UVs 0–1, origin at seal center.
- `T_SummoningJutsu_D.png` — 4096² RGBA. RGB = ink color, Alpha = seal coverage.

## Import
1. Import FBX (default settings; no skeleton). Scale is correct (metric, cm).
2. Import the texture. **sRGB: ON** (it's color). Compression: Default or UI.
3. Material `M_SummoningJutsu`: BaseColor = texture RGB; Opacity/OpacityMask = texture Alpha.
   - Blend Mode **Masked** (crisp, cheap, shadows correct) or **Translucent** if you want the
     soft reveal edge to fade smoothly.
   - Roughness constant 0.9, Specular 0.2.
4. No collision on purpose — it's a floor decal. Alternatively use UE's Decal Actor with a Decal
   Domain material instead of the plane.

## Reveal animation: done in Unreal (2026-10-02)
The Blender file no longer animates: its outward reveal was removed at the user's request, and the seal is always fully
shown. The user animates the reveal in Unreal. One way to build it in the material graph, for reference:
1. `TexCoord` → subtract (0.5, 0.5) → `Length` → gives radial distance `r` in UV space
   (0 at center, 0.5 at plane edge; the seal's outer spokes end ≈ 0.475).
2. Scalar Parameter `Front` (0 → 0.55 over the effect duration).
3. Soft eased edge: `alpha_reveal = smoothstep(Front, Front - 0.055, r)`
   (0.055 UV ≈ the 0.22m band from the Blender version).
4. Final Opacity = texture Alpha × alpha_reveal.
5. Drive `Front` from a Timeline / Sequencer / Niagara user param.
   Ease-out curve recommended: fast start, decelerating finish (~2.4s total).

## Suggested extras in-engine
- Emissive boost during the reveal frontier: `frontier = smoothstep(Front-0.02, Front, r) *
  (1 - smoothstep(Front, Front+0.02, r))` → add orange/red emissive for a "burning-in" edge.
- Spawn a dust/smoke Niagara burst at the center when `Front` starts.
