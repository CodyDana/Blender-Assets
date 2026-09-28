"""Assemble verified nunchucks deliverables, preserving relative asset paths."""
from pathlib import Path
import json,hashlib,zipfile
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Exports/BlackNunchucks'
report=json.loads((OUT/'asset_report.json').read_text())
assert report['status']=='passed'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(ROOT/'Assets/BlackNunchucks.blend')==report['source_sha256']
counts=[report['lods'][str(i)]['triangles'] for i in range(3)]
recolor=json.loads((OUT/'recolor_parameters.json').read_text()) if (OUT/'recolor_parameters.json').is_file() else None
if recolor:
    assert recolor['source_after_sha256']==report['source_sha256']
    assert recolor['geometry_unchanged']
    engine=json.loads((OUT/'unreal_recolor_validation.json').read_text())
    assert engine['status']=='passed' and engine['fresh_process']
    assert engine['source_blend_sha256']==report['source_sha256']
    assert len(engine['gpu_mask_isolation']['tests'])==16
    for path,sha in engine['matching_source_sha256'].items(): assert digest(Path(path))==sha
    for path,sha in engine['native_asset_sha256'].items(): assert digest(OUT/path)==sha
    independent=json.loads((ROOT/'WorkFiles/BlackNunchucks/recolor_independent_qa.json').read_text())
    assert independent['status']=='passed' and independent['current_sha256']==report['source_sha256']
readme=f'''# Black Nunchucks

Reference-based Blender asset with black textured grips, brushed silver caps, two attachment eyes, and seven chain links. Handle proportions and displayed pose follow the supplied image. The surface grain and hidden construction are reconstructed rather than an exact copy of every photographed pixel. Scale assumes approximately 30 cm handles because the reference has no scale marker.

## Files

- `Assets/BlackNunchucks.blend` — editable scene, packed textures, three LODs, custom rig and presentation studio. LOD0 is visible; LOD1/2 are hidden. The studio is excluded from all model exports.
- `Exports/BlackNunchucks/SK_BlackNunchucks_LOD0.fbx` through `LOD2.fbx` — skeletal versions.
- `Exports/BlackNunchucks/SM_BlackNunchucks_LOD0.fbx` through `LOD2.fbx` — static versions with convex handle collision proxies.
- `Exports/BlackNunchucks/SM_BlackNunchucks_LOD0.glb` — textured, rigged LOD0 with embedded textures. The SM filename does not mean it lacks skinning.
- `Textures/BlackNunchucks/` — 4K BaseColor, DirectX Normal, OpenGL Normal companion, AO and packed ORM (R=AO, G=Roughness, B=Metallic), four RGBA part masks and neutral tint detail.
- `Exports/BlackNunchucks/UnrealDemo/` — native Unreal Engine 5.8 recolor materials, imported skeletal mesh and three LODs.
- `Exports/BlackNunchucks/Unreal_Recolor_Guide.md` — setup, saved color presets, runtime parameter changes and full reskins.
- `Renders/BlackNunchucks/Reference_Comparison.html` — local reference comparison with an opacity slider. Open in a browser after extracting the ZIP.
- `Scripts/BlackNunchucks/` — construction, baking, validation and packaging scripts.

## Mesh and rig

LOD triangle counts: **{counts[0]:,} / {counts[1]:,} / {counts[2]:,}**. Each file contains one LOD; assign additional LOD files manually in the target application. UV0 is the unique texture atlas; UV1 is a separate copy for lightmaps. Components remain separate in Blender and share one baked material.

The custom 10-bone rigid-part rig is `root → handle_L → chain_01 → … → chain_07 → handle_R`. Each component has normalized rigid weights. Select and unhide `Nunchucks_Rig` to pose it. There are no animation clips, IK controls, physical chain constraints or engine Physics Asset. Anchor attached objects using the handle bones; the scene origin is at floor level in the pictured pose.

## Unreal import

Use the skeletal FBX for posing or later animation, or the static FBX for a fixed prop. Files use metre-scale source geometry and the shared unit-aware FBX exporter. Leave import scale at 1. Import geometry and create the material separately; FBX materials are not the authoritative shading setup.

Connect BaseColor using sRGB. Treat ORM as linear data: R to Ambient Occlusion, G to Roughness, B to Metallic. Use `blacknunchucks_normal.png` with normal-map compression and **no additional green flip**. The `_normal_opengl` companion is for Blender and glTF. For static meshes use lightmap coordinate index 1. Collision hulls cover handles only; tune engine collision and constraints for your intended gameplay.

## Verification

Source meshes passed topology, applied-transform, UV and skin-weight checks. All six FBX files and the GLB were reimported in Blender and checked against the saved source for triangle counts, dimensions, UV statistics, material assignments, bones and weights. GLB retains embedded BaseColor, normal, metallic/roughness and occlusion maps. The real GLB is also rendered in `BlackNunchucks_ExportCheck.png`.

All 36 pairs among seven chain links and two eyes are free of triangle intersections at each LOD (108 checks). All eight intended connections remain interlocked. This required small pose and link-width adjustments relative to the image. Welds and the intentional eye anchoring inside caps are excluded from these clearance checks.

Reports and file hashes are included. Recolor material compilation, saved asset reload and dynamic parameter changes are checked in Unreal; see the included engine validation report for the exact scope and source hashes. **Physics, animation playback and a gameplay customization UI are not supplied or verified.**

## Recoloring in Unreal

Use `MI_BlackNunchucks_Default`, or create a Dynamic Material Instance from it for gameplay. Set `Amount_Grip_L` to 1 and `Color_Grip_L` to the desired color to change only the left grip. Every region has matching `Amount_` and `Color_` controls; Amount 0 restores the original texture. Caps, eyes, seven chain links, grips and weld seams are independent. Bright grip colors retain surface grain. Texture parameters support full skins using the same UV layout.

The optional Blender preview material mirrors these controls. FBX/GLB retain the simple original PBR material; use the native Unreal material or the provided setup script for runtime recoloring. See `Unreal_Recolor_Guide.md` for the complete parameter list and Blueprint steps.

## Regeneration

Run from the extracted root using Blender 5.2 and system Python. Claim `BlackNunchucks` with `Scripts/pipeline/lock.py` as agent `codex`, then run `build.py`, `resolve_chain.py`, `bake.py`, `finalize_names.py`, `add_recolor.py`, `export_validate.py`, and `render_export.py` in that order with Blender's background Python option. The included `WorkFiles/BlackNunchucks/chain_solution.json` is the fixed clearance solution used by `resolve_chain.py`. To recompute it, run `extract_chain_centers.py` inside the procedural Blender file, then run `optimize_chain.py` with system Python and the packages in `requirements-resolve.txt`. Run `unreal_recolor_setup.py` inside Unreal to create the native material and imports. Re-run the provided validation scripts before packaging. `package.py` runs under system Python. Release the asset lock when finished. GPU rendering uses Cycles OptiX; adjust the device in scripts for other hardware.
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
files=[ROOT/'Assets/BlackNunchucks.blend']
for folder in ['Exports/BlackNunchucks','Textures/BlackNunchucks','Scripts/BlackNunchucks','Scripts/pipeline','References/BlackNunchucks']:
    files += [p for p in (ROOT/folder).glob('*') if p.is_file() and p.suffix.lower() in {'.fbx','.glb','.png','.py','.json','.md','.txt'} and p.name!='package_manifest.json']
files += [p for p in (ROOT/'Renders/BlackNunchucks').glob('*') if p.name.startswith('BlackNunchucks_') or p.name=='Reference_Comparison.html']
files += [p for p in (OUT/'UnrealDemo').rglob('*') if p.is_file() and p.suffix.lower() in {'.uasset','.umap','.uproject','.ini','.json','.md'} and not any(v in p.relative_to(OUT/'UnrealDemo').parts for v in ['Saved','Intermediate','DerivedDataCache'])]
files += [p for p in (ROOT/'WorkFiles/BlackNunchucks').glob('*.json') if p.name in {'build_report.json','bake_report.json','chain_solution.json','chain_centers.json','chain_resolution_report.json','chain_final_qa_summary.json','export_render.json','silhouette_comparison.json','recolor_report.json','recolor_independent_qa.json'} or p.name.startswith('chain_final_allpairs_LOD')]
for lod in range(3):
    qa=json.loads((ROOT/f'WorkFiles/BlackNunchucks/chain_final_allpairs_LOD{lod}.json').read_text())
    assert qa['total_verified_triangle_intersection_pairs']==0
    assert qa['blend_sha256']==report['source_sha256']
    assert qa['all_intended_pairs_interlocked']
files=sorted(set(files))
manifest={str(p.relative_to(ROOT)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':digest(p)} for p in files}
manifestpath=OUT/'package_manifest.json';manifestpath.write_text(json.dumps(manifest,indent=2));files.append(manifestpath)
archive=ROOT/'Exports/BlackNunchucks_Package.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=5) as z:
    for p in files:z.write(p,str(p.relative_to(ROOT)))
    z.writestr('README.md',readme)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for p in files:
        assert hashlib.sha256(z.read(str(p.relative_to(ROOT)).replace('\\','/'))).hexdigest()==digest(p)
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'sha256':digest(archive),'entries':len(files)+1,'crc_and_hashes_verified':True},indent=2))
