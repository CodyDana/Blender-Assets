"""Package the verified reference revision and keep evidence synchronized."""
from pathlib import Path
import json,shutil,hashlib,zipfile
ROOT=Path(r'C:\Users\Cody\Desktop\Blender_Projects');OUT=ROOT/'Exports/BlackCloak';R=ROOT/'Renders/BlackCloak/ReferenceRevision'
report=json.loads((OUT/'asset_report.json').read_text())
assert report['status']=='roundtrip_passed'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'Assets/BlackCloak.blend'
assert digest(source)==report['editable_blend_sha256']
mapping={'Revision_Front.png':'BlackCloak_Front.png','Revision_ThreeQuarter.png':'BlackCloak_ThreeQuarter.png',
         'Revision_Back.png':'BlackCloak_Back.png','Revision_Collar.png':'BlackCloak_Collar.png',
         'Reimported_GLB_Front.png':'Export_GLB_Front.png','Reimported_LOD1_Front.png':'Export_LOD1_Front.png','Reimported_LOD2_Front.png':'Export_LOD2_Front.png'}
for src,dst in mapping.items():
    assert (R/src).is_file()
    shutil.copy2(R/src,OUT/'Previews'/dst)
    shutil.copy2(R/src,ROOT/'Renders/BlackCloak'/dst)
(OUT/'Reference').mkdir(exist_ok=True)
shutil.copy2(ROOT/'References/BlackCloak/blackcloak.png',OUT/'Reference/blackcloak.png')
notes=(ROOT/'WorkFiles/BlackCloak/REVISION_2_REVIEW.md').read_text(encoding='utf-8')
notes=notes.replace('../../Assets/BlackCloak.blend','BlackCloak.blend').replace('../../Exports/BlackCloak_Package.zip','../BlackCloak_Package.zip').replace('../../Exports/BlackCloak/COMPARE.html','COMPARE.html').replace('../../Exports/BlackCloak/asset_report.json','asset_report.json').replace('../../Renders/BlackCloak/ReferenceRevision/Revision_Front.png','Previews/BlackCloak_Front.png').replace('../../Renders/BlackCloak/ReferenceRevision/Reimported_GLB_Front.png','Previews/Export_GLB_Front.png')
(OUT/'REVISION_NOTES.md').write_text(notes,encoding='utf-8')
shutil.copy2(ROOT/'WorkFiles/BlackCloak/reference_landmarks_review.md',OUT/'REFERENCE_LANDMARKS.md')
counts={k:v['triangles'] for k,v in report['lods'].items()}
readme=f'''# Black cloak — reference revision 2

Separate black cloak rebuilt from the supplied front reference. The asymmetric wings, diagonal front leaf, upper overlaps, gathered left fall and continuous scarf collar replace the original procedural layout. Exact small wrinkles and hidden construction are not claimed; see COMPARE.html and REVISION_NOTES.md.

## Files

- BlackCloak.blend: editable source in the ZIP; workspace copy is Assets/BlackCloak.blend. Contains separate cloth pieces, continuous cowl, ring/pin/loop, editable subdivision and thickness, packed textures and a studio excluded from exports.
- BlackCloak.glb: embedded materials/textures, static geometry.
- BlackCloak.fbx and _LOD1/_LOD2: static mesh files.
- BlackCloak_Skeletal.fbx and LODs: the existing shared 152-bone skeleton with rigid attachment weights. Collar follows neck01, clasp clavicle.R, other fabric spine01. This is not simulated or animated cloth.
- Textures: 2K base color, roughness, OpenGL normal and DirectX normal.
- Previews: actual saved-source and reimported-export renders.
- authoring_pin_weights.csv: pin groups indexed to the editable Blender cages, not FBX vertices.
- asset_report.json: file hashes, mesh counts and round-trip checks.

## Scale and LODs

Meters, Z-up, ground-based origin. Approximately {report['dimensions_m'][0]:.3f} m wide, {report['dimensions_m'][1]:.3f} m deep and {report['dimensions_m'][2]:.3f} m tall. Character movement fit has not been validated.

| LOD | Triangles | Intended use |
| --- | ---: | --- |
| 0 | {counts['0']:,} | Closest view |
| 1 | {counts['1']:,} | Reduced detail |
| 2 | {counts['2']:,} | Distance; visible fold simplification close up |

Reduction is per part, weighted toward cloth interiors and performed before thickness. Transition distances and performance require testing in the intended game.

## Materials and UVs

The authoring shader uses meter UVs with a 0.128 m fabric repeat. Exported UV0 already includes that repeat scale; use texture tiling 1.0. UV0 intentionally tiles and is not a unique bake atlas. UV1 is a separate smart-projected layout inside 0–1; engine lightmap validation remains pending.

For Unreal use BaseColor as sRGB, Roughness as linear data, and the DirectX normal as a normal texture with green flip OFF. OpenGL normals are for Blender/glTF. Cloth is opaque/nonmetallic; the clasp has a separate dark steel material. FBX material assignment can require manual setup. No baked AO/ORM atlas is supplied, so this is not full house-pipeline/Fab approval.

## Validation and remaining integration

All six FBXs and the GLB were reimported. Triangle totals, UV channels, loose/degenerate geometry and optional rig structure were checked; LOD counts strictly descend. GLB and both reduced FBXs were rendered for material/silhouette comparison. The source and package are recorded by hashes.

Unreal collision, Chaos cloth, layer collision, cloth painting, character fit and animation tests remain unfinished. Use the open authoring surfaces as a starting point for a simulation mesh rather than the thickened render mesh. The back is an interpretation because only a front reference exists.

The character, hair and default clothing assets were not modified.
'''
if (OUT/'Unreal/BlackCloakRecolor.uproject').is_file():
    recolor_intro='''## Recolor in Unreal

The included `Unreal/BlackCloakRecolor.uproject` contains `M_Cloak_Recolor`, four color instances, and static/skeletal meshes with cloth-only assignments. Open or duplicate a supplied `MI_Cloak_*` instance and change **CloakColor**. The clasp and leather stay separate. See [RECOLOR.md](RECOLOR.md) for migration and runtime color changes, and [RECOLOR.html](RECOLOR.html) for preset previews.

'''
    readme=readme.replace('## Files\n',recolor_intro+'## Files\n',1)
(OUT/'README.md').write_text(readme,encoding='utf-8')
(OUT/'COMPARE.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Black cloak — reference comparison</title><style>body{margin:0;background:#f4f3f0;color:#242424;font:16px/1.5 system-ui}main{max-width:1000px;margin:32px auto;padding:20px}h1{font-size:26px;margin-bottom:8px}p{max-width:850px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0;background:white;padding:12px}img{width:100%;height:auto;display:block}figcaption{font-weight:600;padding:8px 0}a{color:#174c83}@media(max-width:600px){.pair{gap:8px}figure{padding:4px}main{padding:8px}}</style><main><h1>Black cloak: reference and revised model</h1><p>Left: the supplied reference. Right: an actual render of the saved Blender asset. Major contours and panel boundaries were reconstructed from image landmarks. Fine wrinkles, fabric response and unseen surfaces are not exact matches.</p><div class="pair"><figure><figcaption>Supplied reference</figcaption><img src="Reference/blackcloak.png" alt="Original black cloak reference"></figure><figure><figcaption>Revised Blender model</figcaption><img src="Previews/BlackCloak_Front.png" alt="Actual revised cloak render"></figure></div><p><a href="Previews/BlackCloak_Collar.png">Collar close-up</a> · <a href="Previews/BlackCloak_ThreeQuarter.png">Three-quarter</a> · <a href="Previews/BlackCloak_Back.png">Back</a> · <a href="Previews/Export_GLB_Front.png">Reimported GLB</a></p></main></html>''',encoding='utf-8')
report['revision']=2
report['visual_review']={'status':'reference_driven_revision_reviewed_not_exact','notes':'Major landmark/panel reconstruction; fine wrinkles and fabric still approximate. Rear interpreted.','source_renders':[v for k,v in mapping.items() if k.startswith('Revision')],'export_renders':[v for k,v in mapping.items() if k.startswith('Reimported')]}
report['files']={str(p.relative_to(OUT)).replace('\\','/'):digest(p) for p in OUT.rglob('*') if p.is_file() and p.name!='asset_report.json'}
(OUT/'asset_report.json').write_text(json.dumps(report,indent=2))
archive=ROOT/'Exports/BlackCloak_Package.zip';backup=ROOT/'Backups/BlackCloak_Package_before_reference_revision.zip'
if archive.exists() and not backup.exists():shutil.copy2(archive,backup)
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    z.write(source,'BlackCloak.blend')
    for p in sorted(OUT.rglob('*')):
        if p.is_file():z.write(p,str(p.relative_to(OUT)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert hashlib.sha256(z.read('BlackCloak.blend')).hexdigest()==digest(source)
    for p in [OUT/'BlackCloak.glb',OUT/'BlackCloak.fbx',OUT/'asset_report.json']:
        assert hashlib.sha256(z.read(p.name)).hexdigest()==digest(p)
(ROOT/'WorkFiles/BlackCloak/revision2_package_validation.json').write_text(json.dumps({'zip':str(archive),'bytes':archive.stat().st_size,'sha256':digest(archive),'source_sha256':digest(source),'zip_crc_passed':True,'source_glb_fbx_report_match_disk':True},indent=2))
print('REVISION_2_PACKAGED_AND_VERIFIED',archive.stat().st_size)
